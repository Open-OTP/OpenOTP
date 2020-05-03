from otp.messagetypes import *
from dc.util import Datagram
from otp.constants import *
from otp.zone import *
from otp.util import *

from panda3d.core import UniqueIdAllocator
from dc.parser import parse_dc_file
import queue

from typing import Dict

from otp.networking import ToontownProtocol


from dna.dnaparser import load_dna_file
from dna.dnaparser import DNAStorage, DNAGroup

import asyncio


class AIProtocol(ToontownProtocol):
    def connection_made(self, transport):
        ToontownProtocol.connection_made(self, transport)

    def connection_lost(self, exc):
        raise Exception('AI CONNECTION LOST', exc)

    def receive_datagram(self, dg):
        self.service.queue.put_nowait(dg)

    def send_datagram(self, data: Datagram):
        loop = self.service.loop
        loop.call_soon_threadsafe(self.outgoing_q.put_nowait, data.get_message().tobytes())


class AIRepository:
    def __init__(self):
        self.connection = None
        self.queue = queue.Queue()

        base_channel = 4000000

        max_channels = 1000000
        self.channelAllocator = UniqueIdAllocator(base_channel, base_channel + max_channels - 1)

        self._registedChannels = set()

        self.__contextCounter = 0
        self.__callbacks = {}

        self.ourChannel = self.allocateChannel()

        self.doTable: Dict[int, DistributedObjectAI] = {}
        self.zoneTable: Dict[int, set] = {}
        self.parentTable: Dict[int, set] = {}

        self.dcFile = parse_dc_file('toon.dc')

        self.currentSender = None
        self.loop = None
        self.net_thread = None
        self.hoods = None

    def run(self):
        from threading import Thread
        self.net_thread = Thread(target=self.__event_loop)
        self.net_thread.start()

    def _on_net_except(self, loop, context):
        print('Error on networking thread: %s' % context['message'])
        self.loop.stop()
        simbase.stop()

    def __event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.set_exception_handler(self._on_net_except)
        self.loop.run_until_complete(self.loop.create_connection(self._on_connect, '127.0.0.1', 46668))
        self.createObjects()
        self.loop.run_forever()

    def _on_connect(self):
        self.connection = AIProtocol(self)
        return self.connection

    def readUntilEmpty(self, task):
        while True:
            try:
                dg = self.queue.get(timeout=0.05)
            except queue.Empty:
                break
            else:
                self.handleDatagram(dg)

        return task.cont

    def handleDatagram(self, dg):
        dgi = dg.iterator()

        recipient_count = dgi.get_uint8()
        recipients = [dgi.get_channel() for _ in range(recipient_count)]
        self.currentSender = dgi.get_channel()
        msg_type = dgi.get_uint16()

        if msg_type == STATESERVER_OBJECT_ENTER_AI_RECV:
            if self.currentSender == self.ourChannel:
                return
            self.handleObjEntry(dgi)
        elif msg_type == STATESERVER_OBJECT_DELETE_RAM:
            pass
        elif msg_type == STATESERVER_OBJECT_LEAVING_AI_INTEREST:
            pass
        elif msg_type == STATESERVER_OBJECT_CHANGE_ZONE:
            self.handleChangeZone(dgi)
        elif msg_type == STATESERVER_OBJECT_UPDATE_FIELD:
            if self.currentSender == self.ourChannel:
                return
            self.handleUpdateField(dgi)
        else:
            print('Unhandled msg type: ', msg_type)

    def handleChangeZone(self, dgi):
        do_id = dgi.get_uint32()
        new_parent = dgi.get_uint32()
        new_zone = dgi.get_uint32()

        # Should we only change location if the old location matches?
        old_parent = dgi.get_uint32()
        old_zone = dgi.get_uint32()

        self.doTable[do_id].location = (new_parent, new_zone)
        self.storeLocation(do_id, old_parent, old_zone, new_parent, new_zone)

    def storeLocation(self, do_id, old_parent, old_zone, new_parent, new_zone):
        if not do_id:
            return

        if old_zone and old_zone in self.zoneTable and do_id in self.zoneTable[old_zone]:
            self.zoneTable[old_zone].remove(do_id)

        if old_parent and old_parent in self.parentTable and do_id in self.parentTable[old_parent]:
            self.parentTable[old_parent].remove(do_id)

        if new_zone:
            if new_zone not in self.zoneTable:
                self.zoneTable[new_zone] = set()

            self.zoneTable[new_zone].add(do_id)

        if new_parent:
            if new_parent not in self.parentTable:
                self.parentTable[new_parent] = set()

            self.parentTable[new_parent].add(do_id)

    def sendLocation(self, do_id, old_parent: int, old_zone: int, new_parent: int, new_zone: int):
        dg = Datagram()
        dg.add_server_header([do_id], self.ourChannel, STATESERVER_OBJECT_CHANGE_ZONE)
        dg.add_uint32(do_id)
        dg.add_uint32(new_parent)
        dg.add_uint32(new_zone)
        dg.add_uint32(old_parent)
        dg.add_uint32(old_zone)
        self.send(dg)

    @staticmethod
    def isClientChannel(channel):
        return config['ClientAgent.MIN_CHANNEL'] <= channel <= config['ClientAgent.MAX_CHANNEL']

    def setInterest(self, client_channel, handle, context, parent_id, zones):
        dg = Datagram()
        dg.add_server_header([client_channel], self.ourChannel, CLIENT_AGENT_SET_INTEREST)
        dg.add_uint16(handle)
        dg.add_uint32(context)
        dg.add_uint32(parent_id)
        for zone in zones:
            dg.add_uint32(zone)
        self.send(dg)

    def removeInterest(self, client_channel, handle, context, parent_id, zones):
        dg = Datagram()
        dg.add_server_header([client_channel], self.ourChannel, CLIENT_AGENT_REMOVE_INTEREST)
        dg.add_uint16(handle)
        dg.add_uint32(context)
        self.send(dg)

    def handleUpdateField(self, dgi):
        do_id = dgi.get_uint32()
        field_number = dgi.get_uint16()

        # TODO: security check here for client senders.

        field = self.dcFile.fields[field_number]()

        self.currentSender = self.currentSender
        do = self.doTable[do_id]
        field.receive_update(do, dgi)

    @property
    def currentAvatarSender(self):
        return getAvatarIDFromChannel(self.currentSender)

    def handleObjEntry(self, dgi):
        do_id = dgi.get_uint32()
        parent_id = dgi.get_uint32()
        zone_id = dgi.get_uint32()
        dc_id = dgi.get_uint16()

        dclass = self.dcFile.classes[dc_id]

        if do_id in self.doTable:
            return

        if dclass.name == 'DistributedToon':
            from .DistributedToon import DistributedToonAI

            obj = DistributedToonAI(self)
            obj.do_id = do_id
            obj.location = (parent_id, zone_id)
            dclass.receive_update_all_required(obj, dgi)
            self.doTable[obj.do_id] = obj
            self.storeLocation(do_id, 0, 0, parent_id, zone_id)

            obj.sendUpdate('arrivedOnDistrict', [self.district.do_id, ])
        else:
            print('unknown object entry: %s' % dclass.name)

    def context(self):
        self.__contextCounter = (self.__contextCounter + 1) & 0xFFFFFFFF
        return self.__contextCounter

    def allocateChannel(self):
        return self.channelAllocator.allocate()

    def deallocateChannel(self, channel):
        self.channelAllocator.free(channel)

    def registerForChannel(self, channel):
        if channel in self._registedChannels:
            return
        self._registedChannels.add(channel)

        dg = Datagram()
        dg.add_server_control_header(CONTROL_SET_CHANNEL)
        dg.add_channel(channel)
        self.send(dg)

    def unregisterForChannel(self, channel):
        if channel not in self._registedChannels:
            return
        self._registedChannels.remove(channel)

        dg = Datagram()
        dg.add_server_control_header(CONTROL_REMOVE_CHANNEL)
        dg.add_channel(channel)
        self.send(dg)

    def send(self, dg):
        self.connection.send_datagram(dg)

    def generateWithRequired(self, do, parent_id, zone_id, optional=()):
        do_id = self.allocateChannel()
        self.generateWithRequiredAndId(do, do_id, parent_id, zone_id, optional)

    def generateWithRequiredAndId(self, do, do_id, parent_id, zone_id, optional=()):
        do.do_id = do_id
        self.doTable[do_id] = do
        dg = do.dclass.ai_format_generate(do, do_id, parent_id, zone_id, STATESERVERS_CHANNEL, self.ourChannel, optional)
        self.send(dg)

        do.location = (parent_id, zone_id)
        do.generate()
        do.announce_generate()

    def createObjects(self):
        self.registerForChannel(self.ourChannel)

        from .Objects import ToontownDistrictAI, ToontownDistrictStatsAI, DistributedInGameNewsMgrAI, NewsManagerAI
        from .TimeManagerAI import TimeManagerAI

        self.district = ToontownDistrictAI(self)
        self.generateWithRequired(self.district, OTP_DO_ID_TOONTOWN, OTP_ZONE_ID_DISTRICTS)

        post_remove = Datagram()
        post_remove.add_server_control_header(CONTROL_ADD_POST_REMOVE)
        post_remove.add_server_header([STATESERVERS_CHANNEL, ], self.ourChannel, STATESERVER_SHARD_REST)
        post_remove.add_channel(self.ourChannel)
        self.send(post_remove)

        dg = Datagram()
        dg.add_server_header([STATESERVERS_CHANNEL], self.ourChannel, STATESERVER_ADD_AI_RECV)
        dg.add_uint32(self.district.do_id)
        dg.add_channel(self.ourChannel)
        self.send(dg)

        stats = ToontownDistrictStatsAI(self)
        self.generateWithRequired(stats, OTP_DO_ID_TOONTOWN, OTP_ZONE_ID_DISTRICTS_STATS)

        dg = Datagram()
        dg.add_server_header([STATESERVERS_CHANNEL], self.ourChannel, STATESERVER_ADD_AI_RECV)
        dg.add_uint32(stats.do_id)
        dg.add_channel(self.ourChannel)
        self.send(dg)

        time_mgr = TimeManagerAI(self)
        self.generateWithRequired(time_mgr, self.district.do_id, OTP_ZONE_ID_MANAGEMENT)

        ingame_news = DistributedInGameNewsMgrAI(self)
        self.generateWithRequired(ingame_news, self.district.do_id, OTP_ZONE_ID_MANAGEMENT)

        news_mgr = NewsManagerAI(self)
        self.generateWithRequired(news_mgr, self.district.do_id, OTP_ZONE_ID_MANAGEMENT)

        self.loadZones()

    def loadZones(self):
        from ai.hood.HoodDataAI import TTHoodAI

        self.hoods = [
            TTHoodAI(self)
        ]

        for hood in self.hoods:
            hood.startup()
