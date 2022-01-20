from otp import config
from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol
from dc.parser import parse_dc_file
from otp.constants import *
from otp.messagetypes import *
from otp.util import *
from otp.networking import DatagramFuture

from dc.util import Datagram

import asyncio


class UberdogProtocol(MDUpstreamProtocol):
    def __init__(self, service):
        MDUpstreamProtocol.__init__(self, service)

        self.subscribe_channel(self.service.GLOBAL_ID)

    def receive_datagram(self, dg):
        self.service.log.debug(f'Received datagram: {dg.bytes()}')
        MDUpstreamProtocol.receive_datagram(self, dg)

    def handle_datagram(self, dg, dgi):
        sender = dgi.get_channel()
        msgtype = dgi.get_uint16()
        self.service.log.debug(f'Got message type {MSG_TO_NAME_DICT[msgtype]} from {sender}.')

        if self.check_futures(dgi, msgtype, sender):
            self.service.log.debug(f'Future handled datagram')
            return

        if msgtype == STATESERVER_OBJECT_UPDATE_FIELD:
            do_id = dgi.get_uint32()
            if do_id != self.service.GLOBAL_ID:
                self.service.log.debug(f'Got field update for unknown object {do_id}.')
                return
            self.service.receive_update(sender, dgi)

    def check_futures(self, dgi, msg_id, sender):
        pos = dgi.tell()
        for i in range(len(self.futures)):
            future = self.futures[i]
            if future.future_msg_id == msg_id and future.future_sender == sender:
                if not future.context:
                    self.futures.remove(future)
                    future.set_result((sender, dgi))
                    return True
                else:
                    context = dgi.get_uint32()
                    dgi.seek(pos)
                    if future.context == context:
                        self.futures.remove(future)
                        future.set_result((sender, dgi))
                        return True
        else:
            return False


class Uberdog(DownstreamMessageDirector):
    upstream_protocol = UberdogProtocol
    GLOBAL_ID = None
    GAME_ID = OTP_DO_ID_COMMON

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)

        self.dclass = dc.namespace[self.__class__.__name__[:-2]]

        self.last_sender = None

    async def run(self):
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        await self.route()

    def on_upstream_connect(self):
        self.subscribe_channel(self._client, self.GLOBAL_ID)
        self.log.debug('Uberdog online')

        dg = self.dclass.ai_format_generate(self, self.GLOBAL_ID, self.GAME_ID, OTP_ZONE_ID_MANAGEMENT,
                                            STATESERVERS_CHANNEL, self.GLOBAL_ID, optional_fields=None)
        self.send_datagram(dg)

        dg = Datagram()
        dg.add_server_control_header(CONTROL_ADD_POST_REMOVE)
        dg.add_server_header([self.GLOBAL_ID], self.GLOBAL_ID, STATESERVER_OBJECT_DELETE_RAM)
        dg.add_uint32(self.GLOBAL_ID)
        self.send_datagram(dg)

    def receive_update(self, sender, dgi):
        self.last_sender = sender
        field_number = dgi.get_uint16()
        field = dc.fields[field_number]()
        self.log.debug(f'Receiving field update for field {field.name} from {sender}.')
        field.receive_update(self, dgi)

    def register_future(self, msg_type, sender, context):
        f = DatagramFuture(self.loop, msg_type, sender, context)
        self._client.futures.append(f)
        return f

    async def query_location(self, avId, context):
        dg = Datagram()
        dg.add_server_header([STATESERVERS_CHANNEL], self.GLOBAL_ID, STATESERVER_OBJECT_LOCATE)
        dg.add_uint32(context)
        dg.add_uint32(avId)
        self.send_datagram(dg)

        f = self.register_future(STATESERVER_OBJECT_LOCATE_RESP, avId, context)

        try:
            sender, dgi = await asyncio.wait_for(f, timeout=10, loop=self.loop)
        except TimeoutError:
            return None, None
        dgi.get_uint32(), dgi.get_uint32()
        success = dgi.get_uint8()
        if not success:
            return None, None
        parent_id, zone_id = dgi.get_uint32(), dgi.get_uint32()

        return parent_id, zone_id

