import time
import json
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Union, Dict, Tuple


from Crypto.Cipher import AES
from dataslots import with_slots
from dc.objects import MolecularField
from dc.util import Datagram

from otp import config
from otp.messagedirector import MDParticipant
from otp.messagetypes import *
from otp.networking import ToontownProtocol, DatagramFuture
from otp.zone import *
from otp.constants import *
from otp.util import *


class NamePart(IntEnum):
    BOY_TITLE = 0
    GIRL_TITLE = 1
    NEUTRAL_TITLE = 2
    BOY_FIRST = 3
    GIRL_FIRST = 4
    NEUTRAL_FIRST = 5
    CAP_PREFIX = 6
    LAST_PREFIX = 7
    LAST_SUFFIX = 8


@with_slots
@dataclass
class PotentialAvatar:
    do_id: int
    name: str
    wish_name: str
    approved_name: str
    rejected_name: str
    dna_string: str
    index: int


class ClientState(IntEnum):
    NEW = 0
    ANONYMOUS = 1
    AUTHENTICATED = 2
    AVATAR_CHOOSER = 3
    CREATING_AVATAR = 4
    SETTING_AVATAR = 5
    PLAY_GAME = 6


class ClientDisconnect(IntEnum):
    INTERNAL_ERROR = 1
    RELOGGED = 100
    CHAT_ERROR = 120
    LOGIN_ERROR = 122
    OUTDATED_CLIENT = 127
    ADMIN_KICK = 151
    ACCOUNT_SUSPENDED = 152
    SHARD_DISCONNECT = 153
    PERIOD_EXPIRED = 288
    PERIOD_EXPIRED2 = 349


@with_slots
@dataclass
class PendingObject:
    do_id: int
    dc_id: int
    parent_id: int
    zone_id: int
    datagrams: list


class Interest:
    def __init__(self, client, handle, context, parent_id, zones):
        self.client = client
        self.handle = handle
        self.context = context
        self.parent_id = parent_id
        self.zones = zones
        self.done = False
        self.ai = False
        self.pending_objects: List[int] = []


OTP_DO_ID_TOONTOWN = 4618


@with_slots
@dataclass
class ObjectInfo:
    do_id: int
    dc_id: int
    parent_id: int
    zone_id: int


CLIENTAGENT_SECRET = bytes.fromhex(config['General.LOGIN_SECRET'])


@with_slots
@dataclass
class DISLAccount:
    username: bytes
    disl_id: int
    access: bytes
    account_type: bytes
    create_friends_with_chat: bytes
    chat_code_creation_rule: bytes
    whitelist_chat_enabled: bytes


class ClientProtocol(ToontownProtocol, MDParticipant):
    def __init__(self, service):
        ToontownProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

        self.state: int = ClientState.NEW
        self.channel: int = service.new_channel_id()
        self.alloc_channel = self.channel
        self.subscribe_channel(self.channel)

        self.interests: List[Interest] = []
        self.visible_objects: Dict[int, ObjectInfo] = {}
        self.owned_objects: Dict[int, ObjectInfo] = {}

        self.account: Union[DISLAccount, None] = None
        self.avatar_id: int = 0
        self.created_av_id: int = 0
        self.wanted_name: str = ''
        self.potential_avatar = None
        self.potential_avatars: List[PotentialAvatar] = []
        self.avs_deleted: List[Tuple[int, int]] = []
        self.pending_objects: Dict[int, PendingObject] = {}

    def disconnect(self, booted_index, booted_text):
        for task in self.tasks:
            task.cancel()
        del self.tasks[:]
        resp = Datagram()
        resp.add_uint16(CLIENT_GO_GET_LOST)
        resp.add_uint16(booted_index)
        resp.add_string16(booted_text.encode('utf-8'))
        self.transport.write(resp.get_length().to_bytes(2, byteorder='little'))
        self.transport.write(resp.get_message().tobytes())
        self.transport.close()
        self.service.log.debug(f'Booted client {self.channel} with index {booted_index} and text: "{booted_text}"')

    def connection_lost(self, exc):
        self.service.log.debug(f'Connection lost to client {self.channel}')
        ToontownProtocol.connection_lost(self, exc)

        if self.avatar_id:
            self.delete_avatar_ram()

        self.service.remove_participant(self)

    def connection_made(self, transport):
        ToontownProtocol.connection_made(self, transport)
        self.subscribe_channel(CLIENTS_CHANNEL)

    def delete_avatar_ram(self):
        dg = Datagram()
        dg.add_server_header([self.avatar_id], self.channel, STATESERVER_OBJECT_DELETE_RAM)
        dg.add_uint32(self.avatar_id)
        self.service.send_datagram(dg)

    def receive_datagram(self, dg):
        dgi = dg.iterator()
        msgtype = dgi.get_uint16()

        if msgtype != CLIENT_OBJECT_UPDATE_FIELD:
            self.service.log.debug(f'Got message type {MSG_TO_NAME_DICT[msgtype]} from client {self.channel}')

        if msgtype == CLIENT_HEARTBEAT:
            self.send_datagram(dg)
            return

        if msgtype == CLIENT_DISCONNECT:
            return

        if self.state == ClientState.NEW:
            if msgtype == CLIENT_LOGIN_TOONTOWN:
                self.receive_login(dgi)
                self.state = ClientState.AUTHENTICATED
            elif msgtype == CLIENT_LOGIN_3:
                self.receive_login(dgi)
                self.state = ClientState.AUTHENTICATED
            else:
                self.service.log.debug(f'Unexpected message type during handshake {msgtype}.')
        elif self.state == ClientState.AUTHENTICATED:
            if msgtype == CLIENT_GET_AVATARS:
                self.receive_get_avatars(dgi)
            elif msgtype == CLIENT_ADD_INTEREST:
                self.receive_add_interest(dgi)
            elif msgtype == CLIENT_REMOVE_INTEREST:
                self.receive_remove_interest(dgi)
            else:
                self.service.log.debug(f'Unexpected message type during post authentication {msgtype}.')
        elif self.state == ClientState.AVATAR_CHOOSER:
            if msgtype == CLIENT_CREATE_AVATAR:
                self.receive_create_avatar(dgi)
            elif msgtype == CLIENT_SET_AVATAR:
                self.receive_set_avatar(dgi)
            elif msgtype == CLIENT_SET_WISHNAME:
                self.receive_set_wishname(dgi)
            elif msgtype == CLIENT_REMOVE_INTEREST:
                self.receive_remove_interest(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                do_id = dgi.get_uint32()
                if do_id == OTP_DO_ID_CENTRAL_LOGGER:
                    self.receive_update_field(dgi, do_id)
                else:
                    self.service.log.debug(f'Unexpected field update for do_id {do_id} during avatar chooser.')
            elif msgtype == CLIENT_DELETE_AVATAR:
                self.receive_delete_avatar(dgi)
            else:
                self.service.log.debug(f'Unexpected message type during avatar chooser {msgtype}.')
        elif self.state == ClientState.CREATING_AVATAR:
            if msgtype == CLIENT_SET_AVATAR:
                self.receive_set_avatar(dgi)
            elif msgtype == CLIENT_SET_WISHNAME:
                self.receive_set_wishname(dgi)
            elif msgtype == CLIENT_SET_NAME_PATTERN:
                self.receive_set_name_pattern(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                do_id = dgi.get_uint32()
                if do_id == OTP_DO_ID_CENTRAL_LOGGER:
                    self.receive_update_field(dgi, do_id)
                else:
                    self.service.log.debug(f'Unexpected field update for do_id {do_id} during avatar creation.')
            else:
                self.service.log.debug(f'Unexpected message type during avatar creation {msgtype}.')
        else:
            if msgtype == CLIENT_ADD_INTEREST:
                self.receive_add_interest(dgi)
            elif msgtype == CLIENT_REMOVE_INTEREST:
                self.receive_remove_interest(dgi)
            elif msgtype == CLIENT_GET_FRIEND_LIST:
                self.receive_get_friend_list(dgi)
            elif msgtype == CLIENT_OBJECT_LOCATION:
                self.receive_client_location(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                self.receive_update_field(dgi)
            elif msgtype == CLIENT_SET_AVATAR:
                self.receive_set_avatar(dgi)
            else:
                self.service.log.debug(f'Unhandled msg type {msgtype} in state {self.state}')

    def receive_update_field(self, dgi, do_id=None):
        if do_id is None:
            do_id = dgi.get_uint32()

        field_number = dgi.get_uint16()

        field = self.service.dc_file.fields[field_number]()

        sendable = False

        if field.is_ownsend and do_id in self.owned_objects:
            sendable = True
        elif field.is_clsend:
            sendable = True

        if not sendable:
            self.disconnect(ClientDisconnect.INTERNAL_ERROR, 'Tried to send nonsendable field to object.')
            self.service.log.warn(f'Client {self.channel} tried to update {do_id} with nonsendable field {field.name}. '
                                  f'DCField keywords: {field.keywords}')
            return

        pos = dgi.tell()
        field.unpack_bytes(dgi)
        dgi.seek(pos)

        resp = Datagram()
        resp.add_server_header([do_id], self.channel, STATESERVER_OBJECT_UPDATE_FIELD)
        resp.add_uint32(do_id)
        resp.add_uint16(field_number)
        resp.add_bytes(dgi.get_remaining())
        self.service.send_datagram(resp)

        if field.name == 'setTalk':
            # TODO: filtering
            resp = Datagram()
            resp.add_uint16(CLIENT_OBJECT_UPDATE_FIELD)
            resp.add_uint32(do_id)
            resp.add_uint16(field_number)
            resp.add_bytes(dgi.get_remaining())
            self.send_datagram(resp)

    def receive_client_location(self, dgi):
        do_id = dgi.get_uint32()
        parent_id = dgi.get_uint32()
        zone_id = dgi.get_uint32()

        self.service.log.debug(f'Client {self.channel} is setting their location to {parent_id} {zone_id}')

        if do_id in self.owned_objects:
            self.owned_objects[do_id].zone_id = zone_id
            self.owned_objects[do_id].parent_id = parent_id
            dg = Datagram()
            dg.add_server_header([do_id], self.channel, STATESERVER_OBJECT_SET_ZONE)
            dg.add_uint32(parent_id)
            dg.add_uint32(zone_id)
            self.service.send_datagram(dg)
        else:
            self.service.log.debug(f'Client {self.channel} tried setting location for unowned object {do_id}!')

    def receive_get_friend_list(self, dgi):
        self.service.log.debug(f'Friend list query received from {self.channel}')
        error = 0

        count = 0

        # Friend Structure
        # uint32 do_id
        # string name
        # string dna_string
        # uint32 pet_id

        resp = Datagram()
        resp.add_uint16(CLIENT_GET_FRIEND_LIST_RESP)
        resp.add_uint8(error)
        resp.add_uint16(count)

        self.send_datagram(resp)

    def receive_set_avatar(self, dgi):
        av_id = dgi.get_uint32()

        self.service.log.debug(f'client {self.channel} is setting their avatar to {av_id}')

        if not av_id:
            if self.avatar_id:
                # Client is logging out of their avatar.
                self.delete_avatar_ram()
                self.owned_objects.clear()
                self.visible_objects.clear()

                self.unsubscribe_channel(getClientSenderChannel(self.account.disl_id, self.avatar_id))
                self.unsubscribe_channel(getPuppetChannel(self.avatar_id))
                self.channel = getClientSenderChannel(self.account.disl_id, 0)
                self.subscribe_channel(self.channel)

                self.state = ClientState.AUTHENTICATED
                self.avatar_id = 0
                return
            else:
                # Do nothing.
                return
        elif self.state == ClientState.PLAY_GAME:
            self.service.log.debug(f'Client {self.channel} tried to set their avatar {av_id} while avatar is already set to {self.avatar_id}.')
            return

        pot_av = None

        for pa in self.potential_avatars:
            if pa and pa.do_id == av_id:
                pot_av = pa
                break

        if pot_av is None:
            self.disconnect(ClientDisconnect.INTERNAL_ERROR, 'Could not find avatar on account.')
            return

        self.avatar_id = av_id
        self.created_av_id = 0

        self.state = ClientState.SETTING_AVATAR

        self.channel = getClientSenderChannel(self.account.disl_id, self.avatar_id)
        self.subscribe_channel(self.channel)
        self.subscribe_channel(getPuppetChannel(self.avatar_id))

        dclass = self.service.dc_file.namespace['DistributedToon']

        access = 2 if self.account.access == b'FULL' else 1

        # These Fields are REQUIRED but not stored in db.
        other_fields = [
            (dclass['setAccess'], (access,)),
            (dclass['setPreviousAccess'], (access,)),
            (dclass['setAsGM'], (False,)),
            (dclass['setBattleId'], (0,))
        ]

        if pot_av.approved_name:
            other_fields.append((dclass['setName'], (pot_av.approved_name,)))
            pot_av.approved_name = ''

        dg = Datagram()
        dg.add_server_header([STATESERVERS_CHANNEL], self.channel, STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT)
        dg.add_uint32(av_id)
        dg.add_uint32(0)
        dg.add_uint32(0)
        dg.add_channel(self.channel)
        dg.add_uint16(dclass.number)
        dg.add_uint16(len(other_fields))

        for f, arg in other_fields:
            dg.add_uint16(f.number)
            f.pack_value(dg, arg)

        self.service.send_datagram(dg)

    def receive_create_avatar(self, dgi):
        _ = dgi.get_uint16()
        dna = dgi.get_blob16()
        pos = dgi.get_uint8()
        self.service.log.debug(f'Client {self.channel} requesting avatar creation with dna {dna} and pos {pos}.')

        if not 0 <= pos < 6 or self.potential_avatars[pos] is not None:
            self.service.log.debug(f'Client {self.channel} tried creating avatar in invalid position.')
            return

        self.potential_avatar = PotentialAvatar(do_id=0, name='Toon', wish_name='', approved_name='',
                                                      rejected_name='', dna_string=dna, index=pos)

        dclass = self.service.dc_file.namespace['DistributedToon']

        dg = Datagram()
        dg.add_server_header([DBSERVERS_CHANNEL], self.channel, DBSERVER_CREATE_STORED_OBJECT)
        dg.add_uint32(0)
        dg.add_uint16(dclass.number)
        dg.add_uint32(self.account.disl_id)
        dg.add_uint8(pos)
        pos = dg.tell()
        dg.add_uint16(0)

        default_toon = dict(DEFAULT_TOON)
        default_toon['setDNAString'] = (dna,)
        default_toon['setDISLid'] = (self.account.disl_id,)
        default_toon['WishName'] = ('',)
        default_toon['WishNameState'] = ('CLOSED',)

        count = 0
        for field in dclass.inherited_fields:
            if not isinstance(field, MolecularField) and field.is_db:
                if field.name == 'DcObjectType':
                    continue
                dg.add_uint16(field.number)
                field.pack_value(dg, default_toon[field.name])
                count += 1

        dg.seek(pos)
        dg.add_uint16(count)

        self.state = ClientState.CREATING_AVATAR

        self.service.send_datagram(dg)

        self.tasks.append(self.service.loop.create_task(self.created_avatar()))

    async def created_avatar(self):
        f = DatagramFuture(self.service.loop, DBSERVER_CREATE_STORED_OBJECT_RESP)
        self.futures.append(f)
        sender, dgi = await f
        context = dgi.get_uint32()
        return_code = dgi.get_uint8()
        av_id = dgi.get_uint32()

        av = self.potential_avatar
        av.do_id = av_id
        self.potential_avatars[av.index] = av
        self.potential_avatar = None

        resp = Datagram()
        resp.add_uint16(CLIENT_CREATE_AVATAR_RESP)
        resp.add_uint16(0)  # Context
        resp.add_uint8(return_code)  # Return Code
        resp.add_uint32(av_id)  # av_id
        self.send_datagram(resp)

        self.created_av_id = av_id

        self.service.log.debug(f'New avatar {av_id} created for client {self.channel}.')

    def receive_set_wishname(self, dgi):
        av_id = dgi.get_uint32()
        name = dgi.get_string16()

        av = self.get_potential_avatar(av_id)

        self.service.log.debug(f'Received wishname request from {self.channel} for avatar {av_id} for name "{name}".')

        pending = name.encode('utf-8')
        approved = b''
        rejected = b''

        failed = False

        resp = Datagram()
        resp.add_uint16(CLIENT_SET_WISHNAME_RESP)
        resp.add_uint32(av_id)
        resp.add_uint16(failed)
        resp.add_string16(pending)
        resp.add_string16(approved)
        resp.add_string16(rejected)

        self.send_datagram(resp)

        if av_id and av:
            dclass = self.service.dc_file.namespace['DistributedToon']
            wishname_field = dclass['WishName']
            wishname_state_field = dclass['WishNameState']

            resp = Datagram()
            resp.add_server_header([DBSERVERS_CHANNEL], self.channel, DBSERVER_SET_STORED_VALUES)
            resp.add_uint32(av_id)
            resp.add_uint16(2)
            resp.add_uint16(wishname_state_field.number)
            wishname_state_field.pack_value(resp, ('PENDING',))
            resp.add_uint16(wishname_field.number)
            wishname_field.pack_value(resp, (name,))
            self.service.send_datagram(resp)

    def receive_set_name_pattern(self, dgi):
        av_id = dgi.get_uint32()

        self.service.log.debug(f'Got name pattern request for av_id {av_id}.')

        title_index, title_flag = dgi.get_int16(), dgi.get_int16()
        first_index, first_flag = dgi.get_int16(), dgi.get_int16()
        last_prefix_index, last_prefix_flag = dgi.get_int16(), dgi.get_int16()
        last_suffix_index, last_suffix_flag = dgi.get_int16(), dgi.get_int16()

        resp = Datagram()
        resp.add_uint16(CLIENT_SET_NAME_PATTERN_ANSWER)
        resp.add_uint32(av_id)

        if av_id != self.created_av_id:
            resp.add_uint8(1)
            self.send_datagram(resp)
            return

        if first_index <= 0 and last_prefix_index <= 0 and last_suffix_index <= 0:
            self.service.log.debug(f'Received request for empty name for {av_id}.')
            resp.add_uint8(2)
            self.send_datagram(resp)
            return

        if (last_prefix_index <= 0 <= last_suffix_index) or (last_suffix_index <= 0 <= last_prefix_index):
            self.service.log.debug(f'Received request for invalid last name for {av_id}.')
            resp.add_uint8(3)
            self.send_datagram(resp)
            return

        try:
            title = self.get_name_part(title_index, title_flag, {NamePart.BOY_TITLE, NamePart.GIRL_TITLE, NamePart.NEUTRAL_TITLE})
            first = self.get_name_part(first_index, first_flag, {NamePart.BOY_FIRST, NamePart.GIRL_FIRST, NamePart.NEUTRAL_FIRST})
            last_prefix = self.get_name_part(last_prefix_index, last_prefix_flag, {NamePart.CAP_PREFIX, NamePart.LAST_PREFIX})
            last_suffix = self.get_name_part(last_suffix_index, last_suffix_flag, {NamePart.LAST_SUFFIX})
        except KeyError as e:
            resp.add_uint8(4)
            self.send_datagram(resp)
            self.service.log.debug(f'Received invalid index for name part. {e.args}')
            return

        name = f'{title}{" " if title else ""}{first}{" " if first else ""}{last_prefix}{last_suffix}'

        for pot_av in self.potential_avatars:
            if pot_av and pot_av.do_id == av_id:
                pot_av.approved_name = name
                break

        resp.add_uint8(0)
        self.send_datagram(resp)

    def get_name_part(self, index, flag, categories):
        if index >= 0:
            if self.service.name_categories[index] not in categories:
                self.service.log.debug(f'Received invalid index for pattern name: {index}. Expected categories: {categories}')
                return

            title = self.service.name_parts[index]
            return title.capitalize() if flag else title
        else:
            return ''

    def receive_delete_avatar(self, dgi):
        av_id = dgi.get_uint32()

        av = self.get_potential_avatar(av_id)

        if not av:
            return

        self.potential_avatars[av.index] = None
        avatars = [pot_av.do_id if pot_av else 0 for pot_av in self.potential_avatars]
        self.avs_deleted.append((av_id, int(time.time())))

        field = self.service.dc_file.namespace['Account']['ACCOUNT_AV_SET']
        del_field = self.service.dc_file.namespace['Account']['ACCOUNT_AV_SET_DEL']

        dg = Datagram()
        dg.add_server_header([DBSERVERS_CHANNEL], self.channel, DBSERVER_SET_STORED_VALUES)
        dg.add_uint32(self.account.disl_id)
        dg.add_uint16(2)
        dg.add_uint16(field.number)
        field.pack_value(dg, avatars)
        dg.add_uint16(del_field.number)
        del_field.pack_value(dg, self.avs_deleted)
        self.service.send_datagram(dg)

        resp = Datagram()
        resp.add_uint16(CLIENT_DELETE_AVATAR_RESP)
        resp.add_uint8(0)  # Return code

        av_count = sum((1 if pot_av else 0 for pot_av in self.potential_avatars))
        dg.add_uint16(av_count)

        for pot_av in self.potential_avatars:
            if not pot_av:
                continue
            dg.add_uint32(pot_av.do_id)
            dg.add_string16(pot_av.name.encode('utf-8'))
            dg.add_string16(pot_av.wish_name.encode('utf-8'))
            dg.add_string16(pot_av.approved_name.encode('utf-8'))
            dg.add_string16(pot_av.rejected_name.encode('utf-8'))
            dg.add_string16(pot_av.dna_string.encode('utf-8'))
            dg.add_uint8(pot_av.index)

        self.send_datagram(resp)

    def receive_remove_interest(self, dgi, ai=False):
        handle = dgi.get_uint16()

        if dgi.remaining():
            context = dgi.get_uint32()
        else:
            context = None

        interest = None

        for _interest in self.interests:
            if _interest.handle == handle:
                interest = _interest
                break

        if not interest:
            self.service.log.debug(f'Got unexpected interest removal from client {self.channel} for interest handle '
                                   f'{handle} with context {context}')
            return

        self.service.log.debug(f'Got remove interest request from client {self.channel} for interest handle '
                               f'{handle} with context {context}')

        parent_id = interest.parent_id

        uninterested_zones = []

        for zone in interest.zones:
            if len(self.lookup_interest(parent_id, zone)) == 1:
                uninterested_zones.append(zone)

        to_remove = []

        for do_id in self.visible_objects:
            do = self.visible_objects[do_id]
            if do.parent_id == parent_id and do.zone_id in uninterested_zones:
                self.service.log.debug(f'Object {do_id} killed by interest remove.')
                self.send_remove_object(do_id)

                to_remove.append(do_id)

        for do_id in to_remove:
            del self.visible_objects[do_id]

        for zone in uninterested_zones:
            self.unsubscribe_channel(location_as_channel(parent_id, zone))

        self.interests.remove(interest)

        if not ai:
            resp = Datagram()
            resp.add_uint16(CLIENT_DONE_INTEREST_RESP)
            resp.add_uint16(handle)
            resp.add_uint32(context)
            self.send_datagram(resp)

    def receive_get_avatars(self, dgi):
        query = Datagram()
        query.add_server_header([DBSERVERS_CHANNEL, ], self.channel, DBSERVER_ACCOUNT_QUERY)

        disl_id = self.account.disl_id
        query.add_uint32(disl_id)
        field_number = self.service.avatars_field.number
        query.add_uint16(field_number)
        self.service.send_datagram(query)

        self.tasks.append(self.service.loop.create_task(self.do_login()))

    async def do_login(self):
        f = DatagramFuture(self.service.loop, DBSERVER_ACCOUNT_QUERY_RESP)
        self.futures.append(f)
        sender, dgi = await f

        av_del_field = self.service.dc_file.namespace['Account']['ACCOUNT_AV_SET_DEL']
        self.service.log.debug('Begin unpack of deleted avatars.')
        try:
            self.avs_deleted = av_del_field.unpack_value(dgi)
        except Exception:
            import traceback
            traceback.print_exc()
            return
        self.service.log.debug(f'Avatars deleted list for {self.account.username}: {self.avs_deleted}')

        pos = dgi.tell()

        avatar_info = [None] * 6

        for i in range(dgi.get_uint16()):
            pot_av = PotentialAvatar(do_id=dgi.get_uint32(), name=dgi.get_string16(), wish_name=dgi.get_string16(),
                                     approved_name=dgi.get_string16(), rejected_name=dgi.get_string16(),
                                     dna_string=dgi.get_blob16(), index=dgi.get_uint8())

            avatar_info[pot_av.index] = pot_av

        self.potential_avatars = avatar_info

        self.state = ClientState.AVATAR_CHOOSER

        resp = Datagram()
        resp.add_uint16(CLIENT_GET_AVATARS_RESP)
        dgi.seek(pos)
        resp.add_uint8(0)  # Return code
        resp.add_bytes(dgi.get_remaining())
        self.send_datagram(resp)

    def receive_login(self, dgi):
        play_token = dgi.get_string16()
        server_version = dgi.get_string16()
        hash_val = dgi.get_uint32()
        want_magic_words = dgi.get_string16()

        self.service.log.debug(f'play_token:{play_token}, server_version:{server_version}, hash_val:{hash_val}, '
                               f'want_magic_words:{want_magic_words}')

        try:
            play_token = bytes.fromhex(play_token)
            nonce, tag, play_token = play_token[:16], play_token[16:32], play_token[32:]
            cipher = AES.new(CLIENTAGENT_SECRET, AES.MODE_EAX, nonce)
            data = cipher.decrypt_and_verify(play_token, tag)
            self.service.log.debug(f'Login token data:{data}')
            data = json.loads(data)
            for key in list(data.keys()):
                value = data[key]
                if type(value) == str:
                    data[key] = value.encode('utf-8')
            self.account = DISLAccount(**data)
        except ValueError as e:
            self.disconnect(ClientDisconnect.LOGIN_ERROR, 'Invalid token')
            return

        self.channel = getClientSenderChannel(self.account.disl_id, 0)
        self.subscribe_channel(self.channel)
        self.subscribe_channel(getAccountChannel(self.account.disl_id))

        resp = Datagram()
        resp.add_uint16(CLIENT_LOGIN_3_RESP) #CLIENT_LOGIN_TOONTOWN_RESP)

        return_code = 0  # -13 == period expired
        resp.add_uint8(return_code)

        error_string = b'' # 'Bad DC Version Compare'
        resp.add_string16(error_string)

        resp.add_uint32(self.account.disl_id)
        resp.add_string16(self.account.username)
        account_name_approved = True
        resp.add_uint8(account_name_approved)
        resp.add_string16(self.account.whitelist_chat_enabled)
        resp.add_string16(self.account.create_friends_with_chat)
        resp.add_string16(self.account.chat_code_creation_rule)

        t = time.time() * 10e6
        usecs = int(t % 10e6)
        secs = int(t / 10e6)
        resp.add_uint32(secs)
        resp.add_uint32(usecs)

        resp.add_string16(self.account.access)
        resp.add_string16(self.account.whitelist_chat_enabled)

        last_logged_in = time.strftime('%c')  # time.strftime('%c')
        resp.add_string16(last_logged_in.encode('utf-8'))

        account_days = 0
        resp.add_int32(account_days)
        resp.add_string16(self.account.account_type)
        resp.add_string16(self.account.username)

        self.send_datagram(resp)

    def receive_add_interest(self, dgi, ai=False):
        handle = dgi.get_uint16()
        context_id = dgi.get_uint32()
        parent_id = dgi.get_uint32()

        num_zones = dgi.remaining() // 4

        zones = []

        for i in range(num_zones):
            zones.append(dgi.get_uint32())

        self.service.log.debug(f'Client {self.channel} is requesting interest with handle {handle} and context {context_id} '
                               f'for location {parent_id} {zones}')

        if self.state <= ClientState.AUTHENTICATED and parent_id != 4618:
            self.service.log.debug(f'Client {self.channel} requested unexpected interest in state {self.state}. Ignoring.')
            return

        previous_interest = None

        for _interest in self.interests:
            if _interest.handle == handle:
                previous_interest = _interest
                break

        if previous_interest is None:
            interest = Interest(self.channel, handle, context_id, parent_id, zones)
            self.interests.append(interest)
        else:
            self.service.log.debug(f'Altering interest {handle} (done: {previous_interest.done}): {previous_interest.zones} -> {zones}')
            self.interests.remove(previous_interest)

            if previous_interest.parent_id != parent_id:
                killed_zones = previous_interest.zones
            else:
                killed_zones = set(previous_interest.zones).difference(set(zones))

            for _interest in self.interests:
                killed_zones = killed_zones.difference(set(_interest.zones))
                if not killed_zones:
                    break

            self.service.log.debug(f'Zones killed by altering interest: {killed_zones}')

            if killed_zones:
                for do_id in list(self.visible_objects.keys()):
                    obj = self.visible_objects[do_id]
                    if obj.parent_id == parent_id and obj.zone_id in killed_zones:
                        self.service.log.debug(f'Object {obj.do_id}, location ({obj.parent_id}, {obj.zone_id}), killed by altered interest: {zones}')
                        self.send_remove_object(obj.do_id)
                        del self.visible_objects[do_id]

            for zone in killed_zones:
                self.unsubscribe_channel(location_as_channel(previous_interest.parent_id, zone))

            interest = Interest(self.channel, handle, context_id, parent_id, zones)
            self.interests.append(interest)

            for do_id in list(self.pending_objects.keys()):
                if not self.pending_object_needed(do_id):
                    del self.pending_objects[do_id]

        interest.ai = ai

        if not zones:
            interest.done = True
            if not ai:
                resp = Datagram()
                resp.add_uint16(CLIENT_DONE_INTEREST_RESP)
                resp.add_uint16(handle)
                resp.add_uint32(context_id)
                self.send_datagram(resp)
                return

        query_request = Datagram()
        query_request.add_server_header([parent_id], self.channel, STATESERVER_QUERY_ZONE_OBJECT_ALL)
        query_request.add_uint16(handle)
        query_request.add_uint32(context_id)
        query_request.add_uint32(parent_id)

        for zone in zones:
            query_request.add_uint32(zone)
            self.subscribe_channel(location_as_channel(parent_id, zone))

        self.service.send_datagram(query_request)

    def handle_datagram(self, dg, dgi):
        pos = dgi.tell()
        sender = dgi.get_channel()

        if sender == self.channel:
            return

        msgtype = dgi.get_uint16()

        self.check_futures(dgi, msgtype, sender)

        if msgtype == STATESERVER_OBJECT_ENTERZONE_WITH_REQUIRED_OTHER:
            self.handle_object_entrance(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_ENTER_OWNER_RECV:
            self.handle_owned_object_entrance(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_CHANGE_ZONE:
            do_id = dgi.get_uint32()

            if self.queue_pending(do_id, dgi, pos):
                self.service.log.debug(f'Queued location change for pending object {do_id}.')
                return

            self.handle_location_change(dgi, sender, do_id)
        elif msgtype == STATESERVER_QUERY_ZONE_OBJECT_ALL_DONE:
            self.handle_interest_done(dgi)
        elif msgtype == STATESERVER_OBJECT_UPDATE_FIELD:
            do_id = dgi.get_uint32()

            if not self.object_exists(do_id):
                queued = self.queue_pending(do_id, dgi, pos)
                if queued:
                    self.service.log.debug(f'Queued field update for pending object {do_id}.')
                return

            self.handle_update_field(dgi, sender, do_id)
        elif msgtype == STATESERVER_OBJECT_DELETE_RAM:
            do_id = dgi.get_uint32()

            if do_id == self.avatar_id:
                if sender == self.account.disl_id << 32:
                    self.disconnect(ClientDisconnect.RELOGGED, 'redundant login')
                else:
                    self.disconnect(ClientDisconnect.SHARD_DISCONNECT, 'district reset')
            elif not self.object_exists(do_id):
                self.service.log.debug(f'Queued deletion for pending object {do_id}.')
                self.queue_pending(do_id, dgi, pos)
                return
            else:
                self.send_remove_object(do_id)
                del self.visible_objects[do_id]
        elif msgtype == CLIENT_AGENT_SET_INTEREST:
            self.receive_add_interest(dgi, ai=True)
        elif msgtype == CLIENT_AGENT_REMOVE_INTEREST:
            self.receive_remove_interest(dgi, ai=True)
        else:
           self.service.log.debug(f'Client {self.channel} received unhandled upstream msg {msgtype}.')

    def handle_update_field(self, dgi, sender, do_id):
        if sender == self.channel:
            return

        if not self.object_exists(do_id):
            self.service.log.debug(f'Got field update for unknown object {do_id}')

        pos = dgi.tell()

        field_number = dgi.get_uint16()
        field = self.service.dc_file.fields[field_number]()

        resp = Datagram()
        resp.add_uint16(CLIENT_OBJECT_UPDATE_FIELD)
        resp.add_uint32(do_id)
        resp.add_uint16(field_number)
        resp.add_bytes(dgi.get_remaining())

        self.send_datagram(resp)

    def handle_owned_object_entrance(self, dgi, sender):
        do_id = dgi.get_uint32()
        parent_id = dgi.get_uint32()
        zone_id = dgi.get_uint32()
        dc_id = dgi.get_uint16()

        self.owned_objects[do_id] = ObjectInfo(do_id, dc_id, parent_id, zone_id)

        resp = Datagram()
        resp.add_uint16(CLIENT_GET_AVATAR_DETAILS_RESP)
        resp.add_uint32(self.avatar_id)
        resp.add_uint8(0)  # Return code
        resp.add_bytes(dgi.get_remaining())
        self.send_datagram(resp)

    def handle_location_change(self, dgi, sender, do_id):
        new_parent = dgi.get_uint32()
        new_zone = dgi.get_uint32()
        old_parent = dgi.get_uint32()
        old_zone = dgi.get_uint32()
        self.service.log.debug(f'Handle location change for {do_id}: ({old_parent} {old_zone}) -> ({new_parent} {new_zone})')

        disable = True

        for interest in self.interests:
            if interest.parent_id == new_parent and new_zone in interest.zones:
                disable = False
                break

        visible = do_id in self.visible_objects
        owned = do_id in self.owned_objects

        if not visible and not owned:
            self.service.log.debug(f'Got location change for unknown object {do_id}')
            return

        if visible:
            self.visible_objects[do_id].parent_id = new_parent
            self.visible_objects[do_id].zone_id = new_zone

        if owned:
            self.owned_objects[do_id].parent_id = new_parent
            self.owned_objects[do_id].zone_id = new_zone

        if disable and visible:
            if owned:
                self.send_object_location(do_id, new_parent, new_zone)
                return
            self.service.log.debug(f'Got location change and object is no longer visible. Disabling {do_id}')
            self.send_remove_object(do_id)
            del self.visible_objects[do_id]
        else:
            self.send_object_location(do_id, new_parent, new_zone)

    def send_remove_object(self, do_id):
        self.service.log.debug(f'Sending removal of {do_id}.')
        resp = Datagram()
        resp.add_uint16(CLIENT_OBJECT_DISABLE)
        resp.add_uint32(do_id)
        self.send_datagram(resp)

    def send_object_location(self, do_id, new_parent, new_zone):
        resp = Datagram()
        resp.add_uint16(CLIENT_OBJECT_LOCATION)
        resp.add_uint32(do_id)
        resp.add_uint32(new_parent)
        resp.add_uint32(new_zone)
        self.send_datagram(resp)

    def handle_interest_done(self, dgi):
        handle = dgi.get_uint16()
        context = dgi.get_uint32()
        self.service.log.debug(f'sending interest done for handle {handle} context {context}')

        interest = None

        for _interest in self.interests:
            if _interest.handle == handle and _interest.context == context:
                interest = _interest
                break

        if not interest:
            self.service.log.debug(f'Got interest done for unknown interest: {handle} {context}')
            return

        if interest.done:
            self.service.log.debug('Received duplicate interest done...')
            return

        interest.done = True

        pending = [self.pending_objects.pop(do_id) for do_id in interest.pending_objects if do_id in self.pending_objects]
        # Need this sorting.
        pending.sort(key=lambda p: p.dc_id)
        del interest.pending_objects[:]

        self.service.log.debug(f'Replaying datagrams for {[p.do_id for p in pending]}')

        for pending_object in pending:
            for datagram in pending_object.datagrams:
                self.handle_datagram(datagram, datagram.iterator())

        if not interest.ai:
            resp = Datagram()
            resp.add_uint16(CLIENT_DONE_INTEREST_RESP)
            resp.add_uint16(handle)
            resp.add_uint32(context)
            self.send_datagram(resp)

    def lookup_interest(self, parent_id, zone_id):
        return [interest for interest in self.interests if interest.parent_id == parent_id and zone_id in interest.zones]

    def handle_object_entrance(self, dgi, sender):
        # Before msgtype and sender
        pos = dgi.tell() - 10
        has_other = dgi.get_uint8()
        do_id = dgi.get_uint32()
        parent_id = dgi.get_uint32()
        zone_id = dgi.get_uint32()
        dc_id = dgi.get_uint16()

        pending_interests = list(self.get_pending_interests(parent_id, zone_id))

        if len(pending_interests):
            self.service.log.debug(f'Queueing object generate for {do_id} in ({parent_id} {zone_id}) {do_id in self.visible_objects}')
            pending_object = PendingObject(do_id, dc_id, parent_id, zone_id, datagrams=[])
            dg = Datagram()
            dgi.seek(pos)
            dg.add_bytes(dgi.get_remaining())
            pending_object.datagrams.append(dg)
            self.pending_objects[do_id] = pending_object

            for interest in pending_interests:
                interest.pending_objects.append(do_id)
            return

        if self.object_exists(do_id):
            return

        self.visible_objects[do_id] = ObjectInfo(do_id, dc_id, parent_id, zone_id)

        self.send_object_entrance(parent_id, zone_id, dc_id, do_id, dgi, has_other)

    def get_pending_interests(self, parent_id, zone_id):
        for interest in self.interests:
            if not interest.done and interest.parent_id == parent_id and zone_id in interest.zones:
                yield interest

    def object_exists(self, do_id):
        return do_id in self.visible_objects or do_id in self.owned_objects

    def queue_pending(self, do_id, dgi, pos):
        if do_id in self.pending_objects:
            dgi.seek(pos)
            dg = Datagram()
            dg.add_bytes(dgi.get_remaining())
            self.pending_objects[do_id].datagrams.append(dg)
            return True
        return False

    def pending_object_needed(self, do_id):
        for interest in self.interests:
            if do_id in interest.pending_objects:
                return True

        return False

    def send_object_entrance(self, parent_id, zone_id, dc_id, do_id, dgi, has_other):
        resp = Datagram()
        resp.add_uint16(CLIENT_CREATE_OBJECT_REQUIRED_OTHER if has_other else CLIENT_CREATE_OBJECT_REQUIRED)
        resp.add_uint32(parent_id)
        resp.add_uint32(zone_id)
        resp.add_uint16(dc_id)
        resp.add_uint32(do_id)
        resp.add_bytes(dgi.get_remaining())
        self.send_datagram(resp)

    def get_potential_avatar(self, av_id):
        for pot_av in self.potential_avatars:
            if pot_av and pot_av.do_id == av_id:
                return pot_av

    def send_go_get_lost(self, booted_index, booted_text):
        resp = Datagram()
        resp.add_uint16(CLIENT_GO_GET_LOST)
        resp.add_uint16(booted_index)
        resp.add_string16(booted_text.encode('utf-8'))
        self.send_datagram(resp)

    def annihilate(self):
        self.service.upstream.unsubscribe_all(self)
