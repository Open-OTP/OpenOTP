from otp import config
import asyncio

from dc.parser import parse_dc_file
from dc.util import Datagram

from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol, UpstreamServer
from otp.networking import ChannelAllocator
from .clientprotocol import ClientProtocol


class ClientAgentProtocol(MDUpstreamProtocol):
    def handle_datagram(self, dg, dgi):
        sender = dgi.get_channel()
        msgtype = dgi.get_uint16()

        print('unhandled', msgtype)


class ClientAgent(DownstreamMessageDirector, UpstreamServer, ChannelAllocator):
    downstream_protocol = ClientProtocol
    upstream_protocol = ClientAgentProtocol

    min_channel = config['ClientAgent.MIN_CHANNEL']
    max_channel = config['ClientAgent.MAX_CHANNEL']

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)
        UpstreamServer.__init__(self, loop)
        ChannelAllocator.__init__(self)

        self.dc_file = parse_dc_file('toon.dc')
        self.dc_hash = self.dc_file.hash

        self.avatars_field = self.dc_file.namespace['Account']['ACCOUNT_AV_SET']

        self.loop.set_exception_handler(self._on_exception)

        self._context = 0

        self.log.debug(f'DC Hash is {self.dc_hash}')

        self.name_parts = {}
        self.name_categories = {}

        self.listen_task = None

    def _on_exception(self, loop, context):
        print('err', context)

    async def run(self):
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        self.listen_task = self.loop.create_task(self.listen(config['ClientAgent.HOST'], config['ClientAgent.PORT']))
        await self.route()

    def on_upstream_connect(self):
        pass

    def context(self):
        self._context = (self._context + 1) & 0xFFFFFFFF
        return self._context


async def main():
    loop = asyncio.get_running_loop()
    service = ClientAgent(loop)
    await service.run()


if __name__ == '__main__':
    asyncio.run(main(), debug=True)
