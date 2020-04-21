from otp import config
from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol
from dc.parser import parse_dc_file
from otp.constants import *
from otp.messagetypes import *

from dc.util import Datagram

import asyncio


class UberdogProtocol(MDUpstreamProtocol):
    def __init__(self, service):
        MDUpstreamProtocol.__init__(self, service)

        self.subscribe_channel(self.service.GLOBAL_ID)

    def receive_datagram(self, dg):
        self.service.log.debug(f'Received datagram: {dg.get_message().tobytes()}')
        MDUpstreamProtocol.receive_datagram(self, dg)

    def handle_datagram(self, dg, dgi):
        sender = dgi.get_channel()
        msgtype = dgi.get_uint16()
        self.service.log.debug(f'Got message type {MSG_TO_NAME_DICT[msgtype]} from {sender}.')

        if msgtype == STATESERVER_OBJECT_UPDATE_FIELD:
            do_id = dgi.get_uint32()
            if do_id != self.service.GLOBAL_ID:
                self.service.log.debug(f'Got field update for unknown object {do_id}.')
                return
            self.service.receive_update(sender, dgi)


class Uberdog(DownstreamMessageDirector):
    upstream_protocol = UberdogProtocol
    GLOBAL_ID = None

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)

        self.dc = parse_dc_file('toon.dc')

        self.dclass = self.dc.namespace[self.__class__.__name__[:-2]]

        self.last_sender = None

    async def run(self):
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        await self.route()

    def on_upstream_connect(self):
        self.subscribe_channel(self._client, self.GLOBAL_ID)
        self.log.debug('Uberdog online')

        dg = self.dclass.ai_format_generate(self, self.GLOBAL_ID, OTP_DO_ID_TOONTOWN, OTP_ZONE_ID_MANAGEMENT,
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
        field = self.dc.fields[field_number]()
        self.log.debug(f'Receiving field update for field {field.name} from {sender}.')
        field.receive_update(self, dgi)


class CentralLoggerUD(Uberdog):
    GLOBAL_ID = OTP_DO_ID_CENTRAL_LOGGER

    def sendMessage(self, category, event_str, target_disl_id, target_do_id):
        self.log.debug(f'category:{category}, disl_id: {target_disl_id}, do_id: {target_do_id}, event::{event_str}')


class FriendManagerUD(Uberdog):
    GLOBAL_ID = OTP_DO_ID_FRIEND_MANAGER

    def friendQuery(self, todo0):
        pass

    def cancelFriendQuery(self, todo0):
        pass

    def inviteeFriendConsidering(self, todo0):
        pass

    def inviteeFriendResponse(self, todo0):
        pass

    def inviteeAcknowledgeCancel(self, todo0):
        pass

    def requestSecret(self, todo0):
        pass

    def submitSecret(self, todo0):
        pass


async def main():
    loop = asyncio.get_running_loop()
    central_logger = CentralLoggerUD(loop)
    friend_manager = FriendManagerUD(loop)

    uberdog_tasks = [
        asyncio.create_task(central_logger.run()),
        asyncio.create_task(friend_manager.run()),
    ]

    await asyncio.gather(*uberdog_tasks)

if __name__ == '__main__':
    asyncio.run(main())
