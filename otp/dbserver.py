from otp import config

import asyncio


import datetime


from otp.networking import ChannelAllocator
from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol
from otp.messagetypes import *
from otp.constants import *
from .exceptions import *

from dc.objects import MolecularField


class DBServerProtocol(MDUpstreamProtocol):
    def handle_datagram(self, dg, dgi):
        sender = dgi.get_channel()
        msg_id = dgi.get_uint16()
        print('got dg', sender, msg_id)

        if msg_id == DBSERVER_CREATE_STORED_OBJECT:
            self.handle_create_object(sender, dgi)
        elif msg_id == DBSERVER_DELETE_STORED_OBJECT:
            pass
        elif msg_id == DBSERVER_GET_STORED_VALUES:
            self.handle_get_stored_values(sender, dgi)
        elif msg_id == DBSERVER_SET_STORED_VALUES:
            self.handle_set_stored_values(sender, dgi)
        elif DBSERVER_ACCOUNT_QUERY:
            self.handle_account_query(sender, dgi)

    def handle_create_object(self, sender, dgi):
        context = dgi.get_uint32()

        dclass_id = dgi.get_uint16()
        dclass = self.service.dc.classes[dclass_id]

        coro = None

        if dclass.name == 'DistributedToon':
            disl_id = dgi.get_uint32()
            pos = dgi.get_uint8()
            field_count = dgi.get_uint16()

            fields = []
            for i in range(field_count):
                f = self.service.dc.fields[dgi.get_uint16()]()
                fields.append((f.name, f.unpack_bytes(dgi)))

            coro = self.service.create_toon(sender, context, dclass, disl_id, pos, fields)
        else:
            print('Unhandled creation for dclass %s' % dclass.name)
            return

        self.service.loop.create_task(coro)

    def handle_get_stored_values(self, sender, dgi):
        context = dgi.get_uint32()
        do_id = dgi.get_uint32()
        field_count = dgi.get_uint16()
        field_names = [self.service.dc.fields[dgi.get_uint16()]() for _ in range(field_count)]

        self.service.loop.create_task(self.service.get_stored_values(sender, context, do_id, field_names))

    def handle_set_stored_values(self, sender, dgi):
        do_id = dgi.get_uint32()
        field_count = dgi.get_uint16()
        fields = []
        for i in range(field_count):
            f = self.service.dc.fields[dgi.get_uint16()]()
            fields.append((f.name, f.unpack_bytes(dgi)))

        self.service.loop.create_task(self.service.set_stored_values(do_id, fields))

    def handle_account_query(self, sender, dgi):
        do_id = dgi.get_uint32()
        self.service.loop.create_task(self.service.query_account(sender, do_id))


from dc.parser import parse_dc_file
from otp.dbbackend import SQLBackend, OTPCreateFailed
from dc.util import Datagram


class DBServer(DownstreamMessageDirector):
    upstream_protocol = DBServerProtocol

    min_channel = 100000000
    max_channel = 200000000

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)

        self.pool = None

        self.dc = parse_dc_file('toon.dc')

        self.backend = SQLBackend(self)

        self.operations = {}

    async def run(self):
        await self.backend.setup()
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        await self.route()

    async def create_object(self, sender, context, dclass, fields):
        try:
            do_id = await self.backend.create_object(dclass, fields)
        except OTPCreateFailed as e:
            print('creation failed', e)
            do_id = 0

        dg = Datagram()
        dg.add_server_header([sender], DBSERVERS_CHANNEL, DBSERVER_CREATE_STORED_OBJECT_RESP)
        dg.add_uint32(context)
        dg.add_uint8(do_id == 0)
        dg.add_uint32(do_id)
        self.send_datagram(dg)

    async def create_toon(self, sender, context, dclass, disl_id, pos, fields):
        try:
            do_id = await self.backend.create_object(dclass, fields)
            account = await self.backend.query_object_fields(disl_id, ['ACCOUNT_AV_SET'], 'Account')
            temp = Datagram()
            temp.add_bytes(account['ACCOUNT_AV_SET'])
            av_set = self.dc.namespace['Account']['ACCOUNT_AV_SET'].unpack_value(temp.iterator())
            print(do_id, disl_id, pos, av_set)
            av_set[pos] = do_id
            temp.seek(0)
            self.dc.namespace['Account']['ACCOUNT_AV_SET'].pack_value(temp, av_set)
            await self.backend.set_field(disl_id, 'ACCOUNT_AV_SET', temp.get_message().tobytes(), 'Account')
        except OTPCreateFailed as e:
            print('creation failed', e)
            do_id = 0

        dg = Datagram()
        dg.add_server_header([sender], DBSERVERS_CHANNEL, DBSERVER_CREATE_STORED_OBJECT_RESP)
        dg.add_uint32(context)
        dg.add_uint8(do_id == 0)
        dg.add_uint32(do_id)
        self.send_datagram(dg)

    async def get_stored_values(self, sender, context, do_id, fields):
        try:
            field_dict = await self.backend.query_object_fields(do_id, [field.name for field in fields])
        except OTPQueryNotFound:
            field_dict = None

        self.log.debug(f'Received query request from {sender} with context {context} for do_id: {do_id}.')

        dg = Datagram()
        dg.add_server_header([sender], DBSERVERS_CHANNEL, DBSERVER_GET_STORED_VALUES_RESP)
        dg.add_uint32(context)
        dg.add_uint32(do_id)
        pos = dg.tell()
        dg.add_uint16(0)

        if field_dict is None:
            print('object not found... %s' % do_id, sender, context)
            self.send_datagram(dg)
            return

        counter = 0
        for field in fields:
            if field.name not in field_dict:
                continue
            if field_dict[field.name] is None:
                continue
            dg.add_uint16(field.number)
            dg.add_bytes(field_dict[field.name])
            counter += 1

        dg.seek(pos)
        dg.add_uint16(counter)
        self.send_datagram(dg)

    async def set_stored_values(self, do_id, fields):
        self.log.debug(f'Setting stored values for {do_id}: {fields}')
        await self.backend.set_fields(do_id, fields)

    def on_upstream_connect(self):
        self.subscribe_channel(self._client, DBSERVERS_CHANNEL)

    async def query_account(self, sender, do_id):
        dclass = self.dc.namespace['Account']
        toon_dclass = self.dc.namespace['DistributedToon']
        field_dict = await self.backend.query_object_all(do_id, dclass.name)

        temp = Datagram()
        temp.add_bytes(field_dict['ACCOUNT_AV_SET'])
        av_ids = dclass['ACCOUNT_AV_SET'].unpack_value(temp.iterator())

        dg = Datagram()
        dg.add_server_header([sender], DBSERVERS_CHANNEL, DBSERVER_ACCOUNT_QUERY_RESP)
        dg.add_bytes(field_dict['ACCOUNT_AV_SET_DEL'])
        av_count = sum((1 if av_id else 0 for av_id in av_ids))
        self.log.debug(f'Account query for {do_id} from {sender}: {field_dict}')
        dg.add_uint16(av_count)  # Av count
        for av_id in av_ids:
            if not av_id:
                continue
            toon_fields = await self.backend.query_object_fields(av_id, ['setName', 'WishNameState', 'WishName', 'setDNAString'], 'DistributedToon')

            wish_name = toon_fields['WishName']

            temp = Datagram()
            temp.add_bytes(toon_fields['WishNameState'])
            name_state = toon_dclass['WishNameState'].unpack_value(temp.iterator())

            dg.add_uint32(av_id)
            dg.add_bytes(toon_fields['setName'])

            pending_name = b'\x00\x00'
            approved_name = b'\x00\x00'
            rejected_name = b'\x00\x00'

            if name_state == 'APPROVED':
                approved_name = wish_name
            elif name_state == 'REJECTED':
                rejected_name = wish_name
            else:
                pending_name = wish_name

            dg.add_bytes(pending_name)
            dg.add_bytes(approved_name)
            dg.add_bytes(rejected_name)
            dg.add_bytes(toon_fields['setDNAString'])
            dg.add_uint8(av_ids.index(av_id))

        self.send_datagram(dg)


async def main():
    loop = asyncio.get_running_loop()
    db_server = DBServer(loop)
    await db_server.run()

if __name__ == '__main__':
    asyncio.run(main())