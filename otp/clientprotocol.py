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
from otp.networking import OTPProtocol, DatagramFuture
from otp.zone import *
from otp.constants import *
from otp.util import *


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


class ClientProtocol(OTPProtocol, MDParticipant):
    LOGIN_MSG_TYPE = CLIENT_LOGIN
    FORWARDED_MSG_TYPES = [CLIENT_FRIEND_ONLINE, CLIENT_FRIEND_OFFLINE, CLIENT_GET_FRIEND_LIST_RESP]

    def __init__(self, service):
        OTPProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

        self.state: int = ClientState.NEW
        self.channel: int = service.new_channel_id()
        self.alloc_channel = self.channel
        self.subscribe_channel(self.channel)

        self.interests: List[Interest] = []
        self.visible_objects: Dict[int, ObjectInfo] = {}
        self.owned_objects: Dict[int, ObjectInfo] = {}

        self.uberdogs: List[int] = []

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
        self.transport.write(len(resp).to_bytes(2, byteorder='little'))
        self.transport.write(resp.bytes())
        self.transport.close()
        self.service.log.debug(f'Booted client {self.channel} with index {booted_index} and text: "{booted_text}"')

    def connection_lost(self, exc):
        self.service.log.debug(f'Connection lost to client {self.channel}')
        OTPProtocol.connection_lost(self, exc)

        if self.avatar_id:
            self.delete_avatar_ram()

        self.service.remove_participant(self)

    def connection_made(self, transport):
        OTPProtocol.connection_made(self, transport)
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
            if msgtype == LOGIN_MSG_TYPE:
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
        resp.add_bytes(dgi.remaining_bytes())
        self.service.send_datagram(resp)

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

    def receive_create_avatar(self, dgi):
        raise NotImplementedError

    def receive_set_avatar(self, dgi):
        raise NotImplementedError

    def receive_get_avatars(self, dgi):
        raise NotImplementedError

    def receive_set_wishname(self, dgi):
        raise NotImplementedError

    def receive_set_name_pattern(self, dgi):
        raise NotImplementedError

    def receive_delete_avatar(self, dgi):
        raise NotImplementedError

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

    async def do_login(self):
        raise NotImplementedError

    def receive_login(self, dgi):
        raise NotImplementedError

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
                else:
                    self.service.log.debug(f'Got update for unknown object {do_id}.')
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
        elif msgtype in FORWARDED_MSG_TYPES:
            dg = Datagram()
            dg.add_uint16(msgtype)
            dg.add_bytes(dgi.remaining_bytes())
            self.send_datagram(dg)
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
        resp.add_bytes(dgi.remaining_bytes())

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
        resp.add_bytes(dgi.remaining_bytes())
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
            dg.add_bytes(dgi.remaining_bytes())
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
        return do_id in self.visible_objects or do_id in self.owned_objects or do_id in self.uberdogs

    def queue_pending(self, do_id, dgi, pos):
        if do_id in self.pending_objects:
            dgi.seek(pos)
            dg = Datagram()
            dg.add_bytes(dgi.remaining_bytes())
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
        resp.add_bytes(dgi.remaining_bytes())
        self.send_datagram(resp)

    def send_go_get_lost(self, booted_index, booted_text):
        resp = Datagram()
        resp.add_uint16(CLIENT_GO_GET_LOST)
        resp.add_uint16(booted_index)
        resp.add_string16(booted_text.encode('utf-8'))
        self.send_datagram(resp)

    def annihilate(self):
        self.service.upstream.unsubscribe_all(self)
