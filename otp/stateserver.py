from otp import config

import asyncio


from otp.messagedirector import MDUpstreamProtocol, DownstreamMessageDirector
from dc.util import Datagram
from otp.constants import STATESERVERS_CHANNEL
from otp.messagetypes import *
from otp.messagedirector import MDParticipant
from otp.networking import ChannelAllocator
from otp.constants import *
from dc.objects import MolecularField

from otp.zone import *


class DistributedObject(MDParticipant):
    def __init__(self, state_server, sender, do_id, parent_id, zone_id, dclass, required, ram, owner_channel=None, db=False):
        MDParticipant.__init__(self, state_server)
        self.sender = sender
        self.do_id = do_id
        self.parent_id = 0
        self.zone_id = 0
        self.dclass = dclass
        self.required = required
        self.ram = ram
        self.db = db

        self.ai_channel = None
        self.owner_channel = owner_channel

        self.ai_explicitly_set = False
        self.parent_synced = False
        self.next_context = 0
        self.zone_objects = {}

        if self.dclass:
            self.service.log.debug(f'Generating new object {do_id} with dclass {self.dclass.name} in location {parent_id} {zone_id}')

        self.handle_location_change(parent_id, zone_id, sender)
        self.subscribe_channel(do_id)

    def append_required_data(self, dg, client_only, also_owner):
        dg.add_uint32(self.do_id)
        dg.add_uint32(self.parent_id)
        dg.add_uint32(self.zone_id)
        if not self.dclass:
            print('dclass is none for object id', self.do_id)
            return

        dg.add_uint16(self.dclass.number)
        for field in self.dclass.inherited_fields:
            if isinstance(field, MolecularField):
                continue

            if not field.is_required:
                continue

            if not client_only or field.is_broadcast or 'clrecv' in field.keywords or (also_owner and field.is_ownrecv):
                self.service.log.debug(f'Packing field {field.name} for {self.do_id}')
                dg.add_bytes(self.required[field.name])

    def append_other_data(self, dg, client_only, also_owner):
        if client_only:
            fields_dg = Datagram()

            count = 0
            for field_name, raw_data in self.ram.items():
                field = self.dclass.fields_by_name[field_name]
                if field.is_broadcast or 'clrecv' in field.keywords or (also_owner and field.is_ownrecv):
                    fields_dg.add_uint16(field.number)
                    fields_dg.add_bytes(raw_data)
                    count += 1

            dg.add_uint16(count)
            if count:
                dg.add_bytes(fields_dg.get_message().tobytes())

        else:
            dg.add_uint16(len(self.ram))
            for field_name, raw_data in self.ram.items():
                field = self.dclass.fields_by_name[field_name]
                dg.add_uint16(field.number)
                dg.add_bytes(raw_data)

    def send_interest_entry(self, location, context):
        pass

    def send_location_entry(self, location):
        dg = Datagram()
        dg.add_server_header([location], self.do_id, STATESERVER_OBJECT_ENTERZONE_WITH_REQUIRED_OTHER)
        dg.add_uint8(bool(self.ram))
        self.append_required_data(dg, True, False)
        if self.ram:
            self.append_other_data(dg, True, False)
        self.service.send_datagram(dg)

    def send_ai_entry(self, location):
        dg = Datagram()
        dg.add_server_header([location], self.do_id, STATESERVER_OBJECT_ENTER_AI_RECV)
        self.append_required_data(dg, False, False)

        if self.ram:
            self.append_other_data(dg, False, False)

        self.service.send_datagram(dg)

    def send_owner_entry(self, location):
        dg = Datagram()
        dg.add_server_header([location], self.do_id, STATESERVER_OBJECT_ENTER_OWNER_RECV)
        self.append_required_data(dg, False, True)

        if self.ram:
            self.append_other_data(dg, True, True)

        self.service.send_datagram(dg)

    def handle_location_change(self, new_parent, new_zone, sender):
        old_parent = self.parent_id
        old_zone = self.zone_id

        targets = list()

        if self.ai_channel is not None:
            targets.append(self.ai_channel)

        if self.owner_channel is not None:
            targets.append(self.owner_channel)

        if new_parent == self.do_id:
            raise Exception('Object cannot be parented to itself.\n')

        if new_parent != old_parent:
            if old_parent:
                self.unsubscribe_channel(parent_to_children(old_parent))
                targets.append(old_parent)
                targets.append(location_as_channel(old_parent, old_zone))

            self.parent_id = new_parent
            self.zone_id = new_zone

            if new_parent:
                self.subscribe_channel(parent_to_children(new_parent))

                if not self.ai_explicitly_set:
                    new_ai_channel = self.service.resolve_ai_channel(new_parent)
                    if new_ai_channel != self.ai_channel:
                        self.ai_channel = new_ai_channel
                        self.send_ai_entry(new_ai_channel)

                targets.append(new_parent)

        elif new_zone != old_zone:
            self.zone_id = new_zone

            targets.append(self.parent_id)
            targets.append(location_as_channel(self.parent_id, new_zone))
        else:
            # Not changing zones.
            return

        dg = Datagram()
        dg.add_server_header(targets, sender, STATESERVER_OBJECT_CHANGE_ZONE)
        dg.add_uint32(self.do_id)
        dg.add_uint32(new_parent)
        dg.add_uint32(new_zone)
        dg.add_uint32(old_parent)
        dg.add_uint32(old_zone)

        self.service.send_datagram(dg)

        self.parent_synced = False

        if new_parent:
            self.send_location_entry(location_as_channel(new_parent, new_zone))

    def handle_ai_change(self, new_ai, sender, channel_is_explicit):
        pass

    def annihilate(self, sender, notify_parent=False):
        targets = set()

        if self.parent_id:
            targets.add(location_as_channel(self.parent_id, self.zone_id))

            if notify_parent:
                dg = Datagram()
                dg.add_server_header([self.parent_id], sender, STATESERVER_OBJECT_CHANGE_ZONE)
                dg.add_uint32(self.do_id)
                dg.add_uint32(0)  # New parent
                dg.add_uint32(0)  # new zone
                dg.add_uint32(self.parent_id)   # old parent
                dg.add_uint32(self.zone_id)  # old zone
                self.service.send_datagram(dg)

        if self.owner_channel:
            targets.add(self.owner_channel)
        if self.ai_channel:
            targets.add(self.ai_channel)

        dg = Datagram()
        dg.add_server_header([self.parent_id], sender, STATESERVER_OBJECT_DELETE_RAM)
        dg.add_uint32(self.do_id)
        self.service.send_datagram(dg)

        self.delete_children(sender)

        del self.service.objects[self.do_id]

        self.service.remove_participant(self)

        if self.db:
            self.service.database_objects.remove(self.do_id)

        self.service.log.debug(f'Object {self.do_id} has been deleted.')

    def delete_children(self, sender):
        pass

    def handle_one_update(self, dgi, sender):
        field_id = dgi.get_uint16()
        field = self.dclass.dcfile().fields[field_id]()
        data = field.unpack_bytes(dgi)
        self.save_field(field, data)

        targets = list()

        if field.is_broadcast:
            targets.append(location_as_channel(self.parent_id, self.zone_id))
        if field.is_airecv and self.ai_channel and self.ai_channel != sender:
            targets.append(self.ai_channel)
        if field.is_ownrecv and self.owner_channel and self.owner_channel != sender:
            targets.append(self.owner_channel)

        if targets:
            dg = Datagram()
            dg.add_server_header(targets, sender, STATESERVER_OBJECT_UPDATE_FIELD)
            dg.add_uint32(self.do_id)
            dg.add_uint16(field_id)
            dg.add_bytes(data)
            self.service.send_datagram(dg)

    def save_field(self, field, data):
        if field.is_required:
            self.required[field.name] = data
        else:
            self.ram[field.name] = data

        if self.db and 'db' in field.keywords:
            dg = Datagram()
            dg.add_server_header([DBSERVERS_CHANNEL], self.do_id, DBSERVER_SET_STORED_VALUES)
            dg.add_uint32(self.do_id)
            dg.add_uint16(1)
            dg.add_uint16(field.number)
            dg.add_bytes(data)
            self.service.send_datagram(dg)
            self.service.log.debug(f'Object {self.do_id} saved value {data} for field {field.name} to database.')

    def handle_one_get(self, dg, field_id, subfield=False):
        field = self.dclass.dcfile().fields[field_id]()

        if isinstance(field, MolecularField):
            if not subfield:
                dg.add_uint16(field_id)
            for field in field.subfields:
                self.handle_one_get(dg, field.number, subfield)

        if field.name in self.required:
            dg.append_data(self.required[field.name])
        elif field.name in self.ram:
            dg.append_data(self.ram[field.name])

    def handle_datagram(self, dg, dgi):
        sender = dgi.get_channel()
        msgtype = dgi.get_uint16()
        self.service.log.debug(f'Distributed Object {self.do_id} received msgtype {MSG_TO_NAME_DICT[msgtype]} from {sender}')

        if msgtype == STATESERVER_OBJECT_DELETE_RAM:
            do_id = dgi.get_uint32()
            if do_id == self.do_id or do_id == self.parent_id:
                self.annihilate(sender)
                return
        elif msgtype == STATESERVER_OBJECT_UPDATE_FIELD:
            if self.do_id != dgi.get_uint32():
                return
            self.handle_one_update(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_UPDATE_FIELD_MULTIPLE:
            if self.do_id != dgi.get_uint32():
                return

            field_count = dgi.get_uint16()
            for i in range(field_count):
                self.handle_one_update(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_SET_ZONE:
            new_parent = dgi.get_uint32()
            new_zone = dgi.get_uint32()
            print('GOT SET ZONE', self.do_id, new_parent, new_zone)
            self.handle_location_change(new_parent, new_zone, sender)
        elif msgtype == STATESERVER_OBJECT_CHANGE_ZONE:
            child_id = dgi.get_uint32()
            new_parent = dgi.get_uint32()
            new_zone = dgi.get_uint32()
            old_parent = dgi.get_uint32()
            old_zone = dgi.get_uint32()

            if new_parent == self.do_id:
                if old_parent == self.do_id:
                    if new_zone == old_zone:
                        return

                    children = self.zone_objects[old_zone]
                    children.remove(child_id)

                    if not len(children):
                        del self.zone_objects[old_zone]

                if new_zone not in self.zone_objects:
                    self.zone_objects[new_zone] = set()

                self.zone_objects[new_zone].add(child_id)
            elif old_parent == self.do_id:
                children = self.zone_objects[old_zone]
                children.remove(child_id)

                if not len(children):
                    del self.zone_objects[old_zone]
            else:
                self.service.log.debug(f'Received changing location from {child_id} for {old_parent} but my id is {self.do_id}')
        elif msgtype == STATESERVER_QUERY_ZONE_OBJECT_ALL:
            self.handle_query_zone(dgi, sender)
        elif msgtype == STATESERVER_QUERY_OBJECT_ALL:
            self.handle_query_all(dgi, sender)

    def handle_query_all(self, dgi, sender):
        other = dgi.get_uint8()
        context = dgi.get_uint32()

        print('got query all', other, context)

        resp = Datagram()
        resp.add_server_header([sender], self.do_id, STATESERVER_QUERY_OBJECT_ALL_RESP)
        resp.add_uint32(self.do_id)
        resp.add_uint16(context)
        self.append_required_data(resp, False, True)
        self.service.send_datagram(resp)

    def handle_query_zone(self, dgi, sender):
        # STATESERVER_QUERY_ZONE_OBJECT_ALL_DONE
        handle = dgi.get_uint16()
        context_id = dgi.get_uint32()
        parent_id = dgi.get_uint32()
        print('HANDLE_QUERY', handle, context_id, parent_id, self.do_id)

        if parent_id != self.do_id:
            return

        num_zones = dgi.remaining() // 4

        zones = []

        for i in range(num_zones):
            zones.append(dgi.get_uint32())

        object_ids = []

        for zone in zones:
            if zone not in self.zone_objects:
                continue

            object_ids.extend(self.zone_objects[zone])

        resp = Datagram()
        resp.add_server_header([sender], self.do_id, STATESERVER_QUERY_ZONE_OBJECT_ALL_DONE)
        resp.add_uint16(handle)
        resp.add_uint32(context_id)

        if not len(object_ids):
            self.service.send_datagram(resp)
            return

        self.send_location_entry(sender)

        for do_id in object_ids:
            self.service.objects[do_id].send_location_entry(sender)

        self.service.send_datagram(resp)


class StateServerProtocol(MDUpstreamProtocol):
    def handle_datagram(self, dg, dgi):
        sender = dgi.get_channel()
        msgtype = dgi.get_uint16()
        self.service.log.debug(f'State server directly received msgtype {MSG_TO_NAME_DICT[msgtype]} from {sender}.')

        if msgtype == STATESERVER_OBJECT_GENERATE_WITH_REQUIRED:
            self.handle_generate(dgi, sender, False)
        elif msgtype == STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER:
            self.handle_generate(dgi, sender, True)
        elif msgtype == STATESERVER_OBJECT_CREATE_WITH_REQUIRED_CONTEXT:  # DBSS msg
            self.handle_db_generate(dgi, sender, False)
        elif msgtype == STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT:  # DBSS msg
            self.handle_db_generate(dgi, sender, True)
        elif msgtype == STATESERVER_ADD_AI_RECV:
            self.handle_add_ai(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_SET_OWNER_RECV:
            self.handle_set_owner(dgi, sender)
        elif msgtype == DBSERVER_GET_STORED_VALUES_RESP:
            self.activate_callback(dgi)

    def handle_db_generate(self, dgi, sender, other=False):
        do_id = dgi.get_uint32()

        if do_id in self.service.queries or do_id in self.service.database_objects:
            self.service.log.debug(f'Got duplicate activate request for object {do_id} from {sender}')
            return

        parent_id = dgi.get_uint32()
        zone_id = dgi.get_uint32()
        owner_channel = dgi.get_channel()
        number = dgi.get_uint16()

        other_data = []

        state_server = self.service

        if other:
            field_count = dgi.get_uint16()

            for i in range(field_count):
                field_number = dgi.get_uint16()
                field = state_server.dc_file.fields[field_number]()
                data = field.unpack_bytes(dgi)
                other_data.append((field_number, data))

        dclass = state_server.dc_file.classes[number]

        query = Datagram()
        query.add_server_header([DBSERVERS_CHANNEL], STATESERVERS_CHANNEL, DBSERVER_GET_STORED_VALUES)
        query.add_uint32(1)
        query.add_uint32(do_id)

        pos = query.tell()
        query.add_uint16(0)
        count = 0
        for field in dclass:
            if not isinstance(field, MolecularField) and 'db' in field.keywords:
                if field.name == 'DcObjectType':
                    continue
                query.add_uint16(field.number)
                count += 1
        query.seek(pos)
        query.add_uint16(count)

        self.service.log.debug(f'Querying {count} fields for {dclass.name} {do_id}. Other data: {other_data}')

        self.service.queries[do_id] = (parent_id, zone_id, owner_channel, number, other_data)
        self.service.send_datagram(query)

    def activate_callback(self, dgi):
        context = dgi.get_uint32()
        do_id = dgi.get_uint32()

        state_server = self.service

        parent_id, zone_id, owner_channel, number, other_data = state_server.queries[do_id]
        dclass = state_server.dc_file.classes[number]

        del state_server.queries[do_id]

        required = {}
        ram = {}

        count = dgi.get_uint16()
        self.service.log.debug(f'Unpacking {count} fields for activate. do_id: {do_id}')

        for i in range(count):
            field_number = dgi.get_uint16()
            field = state_server.dc_file.fields[field_number]()
            self.service.log.debug(f'Unpacking {field.name}...')

            if field.is_required:
                required[field.name] = field.unpack_bytes(dgi)
            else:
                ram[field.name] = field.unpack_bytes(dgi)

        for field_number, data in other_data:
            field = state_server.dc_file.fields[field_number]()
            if field.is_required:
                required[field.name] = data
            else:
                ram[field.name] = data

            if 'db' in field.keywords:
                dg = Datagram()
                dg.add_server_header([DBSERVERS_CHANNEL], do_id, DBSERVER_SET_STORED_VALUES)
                dg.add_uint32(do_id)
                dg.add_uint16(1)
                dg.add_uint16(field.number)
                dg.add_bytes(data)
                self.service.send_datagram(dg)

        self.service.log.debug(f'Activating {do_id} with required:{required}\nram:{ram}\n')

        obj = DistributedObject(state_server, STATESERVERS_CHANNEL, do_id, parent_id, zone_id, dclass, required, ram,
                                owner_channel=owner_channel, db=True)
        state_server.database_objects.add(do_id)
        state_server.objects[do_id] = obj
        obj.send_owner_entry(owner_channel)

    def handle_add_ai(self, dgi, sender):
        object_id = dgi.get_uint32()
        ai_channel = dgi.get_channel()
        state_server = self.service
        obj = state_server.objects[object_id]
        obj.ai_channel = ai_channel
        obj.ai_explicitly_set = True
        print('AI SET FOR', object_id, 'TO', ai_channel)
        obj.send_ai_entry(ai_channel)

    def handle_set_owner(self, dgi, sender):
        object_id = dgi.get_uint32()
        owner_channel = dgi.get_channel()
        state_server = self.service
        obj = state_server.objects[object_id]
        obj.owner_channel = owner_channel
        obj.send_owner_entry(owner_channel)

    def handle_generate(self, dgi, sender, other=False):
        parent_id = dgi.get_uint32()
        zone_id = dgi.get_uint32()
        number = dgi.get_uint16()
        do_id = dgi.get_uint32()

        state_server = self.service

        if do_id in state_server.objects:
            self.service.log.debug(f'Received duplicate generate for object {do_id}')
            return

        if number > len(state_server.dc_file.classes):
            self.service.log.debug(f'Received create for unknown dclass with class id {number}')
            return

        dclass = state_server.dc_file.classes[number]

        required = {}
        ram = {}

        for field in dclass.inherited_fields:
            if field.is_required:
                required[field.name] = field.unpack_bytes(dgi)

        if other:
            num_optional_fields = dgi.get_uint16()

            for i in range(num_optional_fields):
                field_number = dgi.get_uint16()

                field = dclass.fields[field_number]

                if 'ram' not in field.keywords:
                    self.service.log.debug(f'Received non-RAM field {field.name} within an OTHER section.\n')
                    field.unpack_bytes(dgi)
                    continue
                else:
                    ram[field.name] = field.unpack_bytes(dgi)

        obj = DistributedObject(state_server, sender, do_id, parent_id, zone_id, dclass, required, ram)
        state_server.objects[do_id] = obj


from dc.parser import parse_dc_file


class StateServer(DownstreamMessageDirector, ChannelAllocator):
    upstream_protocol = StateServerProtocol
    service_channels = []
    root_object_id = 4618

    min_channel = 100000000
    max_channel = 399999999

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)
        ChannelAllocator.__init__(self)

        self.dc_file = parse_dc_file('toon.dc')

        self.loop.set_exception_handler(self._on_exception)

        self.objects = dict()
        self.database_objects = set()
        self.queries = {}

    def _on_exception(self, loop, context):
        print('err', context)

    async def run(self):
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        await self.route()

    def on_upstream_connect(self):
        self.subscribe_channel(self._client, STATESERVERS_CHANNEL)
        self.objects[self.root_object_id] = DistributedObject(self, STATESERVERS_CHANNEL, self.root_object_id,
                                                              0, 2, self.dc_file.namespace['DistributedDirectory'],
                                                              None, None)

    def resolve_ai_channel(self, parent_id):
        ai_channel = None

        while ai_channel is None:
            try:
                obj = self.objects[parent_id]
            except KeyError:
                return None
            parent_id = obj.parent_id
            ai_channel = obj.ai_channel

        return ai_channel


async def main():
    loop = asyncio.get_running_loop()
    service = StateServer(loop)
    await service.run()

if __name__ == '__main__':
    asyncio.run(main(), debug=True)
