from asyncio import Queue
from dc.util import Datagram
import logging
import traceback


import asyncio
import struct


from asyncio import Future
from typing import List


class Service:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)
        fh = logging.FileHandler('logs/' + self.__class__.__name__ + '.log')
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('(%(name)s::%(asctime)s): %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        self.log.addHandler(fh)
        self.log.addHandler(ch)

    async def run(self):
        raise NotImplementedError

    def add_participant(self, participant):
        raise NotImplementedError

    def subscribe_channel(self, participant, channel):
        raise NotImplementedError

    def unsubscribe_channel(self, participant, channel):
        raise NotImplementedError


class UpstreamServer:
    SERVER_SSL_CONTEXT = None
    downstream_protocol = None

    def __init__(self, loop):
        self.loop = loop
        self._server = None
        self._clients = set()

    async def listen(self, host: str, port: int):
        if self.downstream_protocol is None:
            raise Exception('PROTOCOL NOT DEFINED!')

        self.log.debug(f'Listening on {host}:{port}')

        self._server = await self.loop.create_server(self.new_client, host, port, ssl=self.SERVER_SSL_CONTEXT,
                                                     start_serving=False)

        async with self._server:
            await self._server.serve_forever()
            self._clients.clear()

    def new_client(self):
        client = self.downstream_protocol(self)
        self._clients.add(client)
        return client


class DownstreamClient:
    CLIENT_SSL_CONTEXT = None
    upstream_protocol = None

    def __init__(self, loop):
        self.loop = loop
        self._client = None

    async def connect(self, host: str, port: int):
        await self.loop.create_connection(self.on_connect, host, port)

    def on_connect(self):
        self._client = self.upstream_protocol(self)
        return self._client


class DatagramFuture(Future):
    def __init__(self, loop, msg_id, sender=None, context=None):
        Future.__init__(self, loop=loop)

        self.future_msg_id = msg_id
        self.future_sender = sender
        self.context = context


class ToontownProtocol(asyncio.Protocol):
    def __init__(self, service):
        asyncio.Protocol.__init__(self)
        self.service = service
        self.expected = 0
        self.buf = bytearray()
        self.transport = None
        self.outgoing_q = Queue()
        self.incoming_q = Queue()
        self.tasks: List[asyncio.Task] = []
        self.futures: List[DatagramFuture] = []

    def connection_made(self, transport):
        # name = transport.get_extra_info('peername')
        self.transport = transport
        self.tasks.append(self.service.loop.create_task(self.handle_datagrams()))
        self.tasks.append(self.service.loop.create_task(self.transport_datagrams()))

    def connection_lost(self, exc):
        for task in self.tasks:
            task.cancel()

    def data_received(self, data: bytes):
        self.buf.extend(data)

    def send_datagram(self, data: Datagram):
        self.outgoing_q.put_nowait(data.bytes())

    async def transport_datagrams(self):
        while True:
            data: bytes = await self.outgoing_q.get()
            self.transport.write(len(data).to_bytes(2, byteorder='little'))
            self.transport.write(data)

    async def handle_datagrams(self):
        # TODO: run this tight loop in a seperate process, maybe proccess pool for CA and MD
        expected = 0

        while True:
            if expected:
                if len(self.buf) < expected:
                    await asyncio.sleep(0.01)
                    continue
                else:
                    try:
                        dg = Datagram()
                        dg.add_bytes(self.buf[:expected])
                        self.receive_datagram(dg)
                        del self.buf[:expected]
                        expected = 0
                        continue
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        continue
            elif len(self.buf) > 2:
                expected = struct.unpack('H', self.buf[:2])[0]
                del self.buf[:2]
                continue
            else:
                await asyncio.sleep(0.01)

    def receive_datagram(self, data: bytes):
        raise NotImplementedError

    def check_futures(self, dgi, msg_id, sender):
        for f in self.futures[:]:
            if msg_id != f.future_msg_id:
                continue

            if f.future_sender is not None and sender != f.future_sender:
                continue

            f.set_result((sender, dgi))
            self.futures.remove(f)


class MDParticipant:
    def __init__(self, service: Service):
        self.channels = set()
        self.service = service
        self.service.add_participant(self)

    def subscribe_channel(self, channel):
        self.service.subscribe_channel(self, channel)

    def unsubscribe_channel(self, channel):
        self.service.unsubscribe_channel(self, channel)


class ChannelAllocator:
    min_channel = None
    max_channel = None

    def __init__(self):
        self._used_channels = set()
        self._freed_channels = set()
        self._next_channel = self.min_channel

    def new_channel_id(self):
        channel = self._next_channel
        self._next_channel += 1

        if channel in self._used_channels:
            if self._next_channel > self.max_channel:
                if len(self._used_channels) >= self.max_channel - self.min_channel:
                    raise OverflowError
                self._next_channel = self.min_channel
            return self.new_channel_id()
        else:
            self._used_channels.add(channel)
            return channel

    def free_channel_id(self, channel):
        self._freed_channels.add(channel)
