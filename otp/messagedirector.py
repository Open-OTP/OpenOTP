import uvloop
uvloop.install()

from otp.networking import ToontownProtocol, MDParticipant, Service, UpstreamServer, DownstreamClient
from dc.messagetypes import *
from dc.util import Datagram
from asyncio import Queue
import asyncio
import par


from typing import Dict, Set, List


class MDProtocol(ToontownProtocol, MDParticipant):
    def __init__(self, service):
        ToontownProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

    def connection_made(self, transport):
        ToontownProtocol.connection_made(self, transport)

    def connection_lost(self, exc):
        ToontownProtocol.connection_lost(self, exc)
        self.service.remove_participant(self)

    def receive_datagram(self, dg):
        dgi = dg.iterator()

        recipient_count = dgi.get_uint8()
        if recipient_count == 1 and dgi.get_channel() == CONTROL_MESSAGE:
            # Control message.
            msg_type = dgi.get_uint16()

            if msg_type == CONTROL_SET_CHANNEL:
                channel = dgi.get_channel()
                self.subscribe_channel(channel)
            elif msg_type == CONTROL_REMOVE_CHANNEL:
                channel = dgi.get_channel()
                self.unsubscribe_channel(channel)
            elif msg_type == CONTROL_ADD_RANGE:
                low = dgi.get_channel()
                high = dgi.get_channel()
                for channel in range(low, high, 1):
                    self.channels.add(channel)
            elif msg_type == CONTROL_REMOVE_RANGE:
                low = dgi.get_channel()
                high = dgi.get_channel()
                for channel in range(low, high, 1):
                    if channel in self.channels:
                        self.channels.remove(channel)
            elif msg_type == CONTROL_ADD_POST_REMOVE:
                sender = dgi.get_channel()
                post_dg = Datagram()
                post_dg.add_bytes(dgi.get_bytes(dgi.remaining()))
                if sender not in self.service.post_removes:
                    self.service.post_removes[sender] = list()
                self.service.post_removes[sender].append(post_dg)
            elif msg_type == CONTROL_CLEAR_POST_REMOVE:
                sender = dgi.get_channel()
                if sender in self.service.post_removes:
                    del self.service.post_removes[sender]
        else:
            self.service.q.put_nowait((None, dg))

    def handle_datagram(self, dg, dgi):
        self.send_datagram(dg)


class MessageDirector(Service):
    def __init__(self):
        Service.__init__(self)
        self.participants: Set[MDParticipant] = set()
        self.channel_subscriptions: Dict[int, Set[MDParticipant]] = {}
        self.q = Queue()

    def subscribe_channel(self, participant: MDParticipant, channel: int):
        if channel not in participant.channels:
            participant.channels.add(channel)

        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()

        if participant not in self.channel_subscriptions[channel]:
            self.channel_subscriptions[channel].add(participant)

    def unsubscribe_channel(self, participant: MDParticipant, channel: int):
        if channel in participant.channels:
            participant.channels.remove(channel)

        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].remove(participant)

    def unsubscribe_all(self, participant: MDParticipant):
        while participant.channels:
            channel = participant.channels.pop()
            self.unsubscribe_channel(participant, channel)

    def add_participant(self, participant: MDParticipant):
        self.participants.add(participant)

    def remove_participant(self, participant: MDParticipant):
        self.unsubscribe_all(participant)
        self.participants.remove(participant)

    def process_datagram(self, participant: MDParticipant, dg: Datagram):
        dgi = dg.iterator()

        recipient_count = dgi.get_uint8()
        recipients = (dgi.get_channel() for _ in range(recipient_count))

        receiving_participants = {p for c in recipients if c in self.channel_subscriptions for p in self.channel_subscriptions[c]}

        if participant is not None and participant in receiving_participants:
            receiving_participants.remove(participant)

        pos = dgi.tell()

        for participant in receiving_participants:
            _dgi = dg.iterator()
            _dgi.seek(pos)
            participant.handle_datagram(dg, _dgi)

    async def route(self):
        while True:
            participant, dg = await self.q.get()
            self.process_datagram(participant, dg)


class MasterMessageDirector(MessageDirector, UpstreamServer):
    downstream_protocol = MDProtocol

    def __init__(self, loop):
        MessageDirector.__init__(self)
        UpstreamServer.__init__(self, loop)
        self.post_removes: Dict[int, List[Datagram]] = {}
        self.loop.set_exception_handler(self._on_exception)

    def _on_exception(self, loop, context):
        print('err', context)

    async def run(self):
        self.loop.create_task(self.route())
        await self.listen('127.0.0.1', int(config['MessageDirector']['PORT']))


class MDUpstreamProtocol(ToontownProtocol, MDParticipant):
    def __init__(self, service):
        ToontownProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

    def connection_made(self, transport):
        ToontownProtocol.connection_made(self, transport)
        self.service.on_upstream_connect()

    def connection_lost(self, exc):
        ToontownProtocol.connection_lost(self, exc)
        raise Exception('lost upsteam connection!', exc)

    def subscribe_channel(self, channel):
        dg = Datagram()
        dg.add_uint8(1)
        dg.add_channel(CONTROL_MESSAGE)
        dg.add_uint16(CONTROL_SET_CHANNEL)
        dg.add_channel(channel)
        self.send_datagram(dg)

    def unsubscribe_channel(self, channel):
        dg = Datagram()
        dg.add_uint8(1)
        dg.add_channel(CONTROL_MESSAGE)
        dg.add_uint16(CONTROL_REMOVE_CHANNEL)
        dg.add_channel(channel)
        self.send_datagram(dg)

    def receive_datagram(self, dg):
        self.service.q.put_nowait((None, dg))

    def handle_datagram(self, dg, dgi):
        raise NotImplementedError


class DownstreamMessageDirector(MessageDirector, DownstreamClient):
    upstream_protocol = MDUpstreamProtocol

    def __init__(self, loop):
        MessageDirector.__init__(self)
        DownstreamClient.__init__(self, loop)

    async def run(self):
        raise NotImplementedError

    def subscribe_channel(self, participant, channel):
        subscribe_upstream = channel not in self.channel_subscriptions
        MessageDirector.subscribe_channel(self, participant, channel)

        if subscribe_upstream:
            self._client.subscribe_channel(channel)

    def unsubscribe_channel(self, participant, channel):
        MessageDirector.unsubscribe_channel(self, participant, channel)

        if len(self.channel_subscriptions[channel]) == 0:
            self._client.unsubscribe_channel(channel)

    def process_datagram(self, participant, dg):
        MessageDirector.process_datagram(self, participant, dg)

        if participant is not None:
            # send upstream
            self._client.send_datagram(dg)

    def send_datagram(self, dg: Datagram):
        self._client.send_datagram(dg)


async def main():
    loop = asyncio.get_running_loop()
    service = MasterMessageDirector(loop)
    print('awaiting message director run..')
    await service.run()

if __name__ == '__main__':
    asyncio.run(main())
