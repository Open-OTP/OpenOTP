from otp.messagetypes import *
from dc.util import Datagram
from otp.constants import *
from otp.zone import *
from otp.util import *

from panda3d.core import UniqueIdAllocator
from dc.parser import parse_dc_file
import queue

from typing import Dict, Tuple

from otp.networking import ToontownProtocol

from dna.objects import DNAVisGroup
from threading import Thread, Event

import asyncio

from . import AIZoneData

from .ToontownGlobals import DynamicZonesBegin, DynamicZonesEnd


class AIProtocol(ToontownProtocol):
    def connection_made(self, transport):
        ToontownProtocol.connection_made(self, transport)
        self.service.connected.set()

    def connection_lost(self, exc):
        raise Exception('AI CONNECTION LOST', exc)

    def receive_datagram(self, dg):
        self.service.queue.put_nowait(dg)

    def send_datagram(self, data: Datagram):
        loop = self.service.loop
        loop.call_soon_threadsafe(self.outgoing_q.put_nowait, data.bytes())


class AIRepository:
    def __init__(self):
        self.connection = None
        self.queue = queue.Queue()

        base_channel = 4000000

        max_channels = 1000000
        self.minChannel = base_channel
        self.maxChannel = base_channel + max_channels
        self.channelAllocator = UniqueIdAllocator(self.minChannel, self.maxChannel)
        self.zoneAllocator = UniqueIdAllocator(DynamicZonesBegin, DynamicZonesEnd)

        self._registedChannels = set()

        self.__contextCounter = 0
        self.__callbacks = {}

        self.ourChannel = self.allocateChannel()

        self.doTable: Dict[int, 'DistributedObjectAI'] = {}
        self.zoneTable: Dict[int, set] = {}
        self.parentTable: Dict[int, set] = {}

        self.dcFile = parse_dc_file('toon.dc')

        self.currentSender = None
        self.loop = None
        self.net_thread = None
        self.hoods = None

        self.zoneDataStore = AIZoneData.AIZoneDataStore()

        self.vismap: Dict[int, Tuple[int]] = {}

        self.connected = Event()

    def run(self):
        self.net_thread = Thread(target=self.__event_loop)
        self.net_thread.start()
        self.connected.wait()
        self.createObjects()

    def _on_net_except(self, loop, context):
        print('Error on networking thread: %s' % context['message'])
        self.loop.stop()
        simbase.stop()

    def __event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.set_exception_handler(self._on_net_except)
        self.loop.run_until_complete(self.loop.create_connection(self._on_connect, '127.0.0.1', 46668))
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
            self.handleObjExit(dgi)
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

    def storeLocation(self, doId, oldParent, oldZone, newParent, newZone):
        if not doId:
            return

        obj = self.doTable.get(doId)
        oldParentObj = self.doTable.get(oldParent)
        newParentObj = self.doTable.get(newParent)

        if oldParent != newParent and oldParentObj:
            oldParentObj.handleChildLeave(obj, oldZone)

        if oldParent and oldParent in self.parentTable and doId in self.parentTable[oldParent]:
            self.parentTable[oldParent].remove(doId)

        if oldZone != newZone and oldParentObj:
            oldParentObj.handleChildLeaveZone(obj, oldZone)

        if oldZone and oldZone in self.zoneTable and doId in self.zoneTable[oldZone]:
            self.zoneTable[oldZone].remove(doId)

        if newZone:
            self.zoneTable.setdefault(newZone, set())
            self.zoneTable[newZone].add(doId)

        if newParent:
            self.parentTable.setdefault(newParent, set())
            self.parentTable[newParent].add(doId)

        if newParent != oldParent and newParentObj:
            newParentObj.handleChildArrive(obj, newZone)

        if newZone != oldZone and newParentObj:
            newParentObj.handleChildArriveZone(obj, newZone)

    def sendLocation(self, do_id, old_parent: int, old_zone: int, new_parent: int, new_zone: int):
        dg = Datagram()
        dg.add_server_header([do_id], self.ourChannel, STATESERVER_OBJECT_SET_ZONE)
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

    def removeInterest(self, client_channel, handle, context):
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
        try:
            field.receive_update(do, dgi)
        except Exception as e:
            print(f'failed to handle field update: <{field}> from {self.currentAvatarSender}')
            import traceback
            traceback.print_exc()
            dgi.seek(0)
            print('datagram:', dgi.remaining_bytes())

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
            # This is a response from a generate by us.
            do = self.doTable[do_id]
            do.queueUpdates = False
            while do.updateQueue:
                dg = do.updateQueue.popleft()
                self.send(dg)
            return

        if dclass.name == 'DistributedToon':
            from .toon.DistributedToonAI import DistributedToonAI
            obj = DistributedToonAI(self)
            # Don't queue updates as this object was generated by the stateserver.
            obj.queueUpdates = False
            obj.do_id = do_id
            obj.parentId = parent_id
            obj.zoneId = zone_id
            dclass.receive_update_all_required(obj, dgi)
            self.doTable[obj.do_id] = obj
            self.storeLocation(do_id, 0, 0, parent_id, zone_id)
        else:
            print('unknown object entry: %s' % dclass.name)

    def handleObjExit(self, dgi):
        doId = dgi.get_uint32()

        try:
            do = self.doTable.pop(doId)
        except KeyError:
            print(f'Received delete for unknown object: {doId}!')
            return

        do.delete()

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
        do.announceGenerate()

    def createObjects(self):
        self.registerForChannel(self.ourChannel)

        from .Objects import ToontownDistrictAI, ToontownDistrictStatsAI, DistributedInGameNewsMgrAI, NewsManagerAI, FriendManagerAI
        from .TimeManagerAI import TimeManagerAI

        self.district = ToontownDistrictAI(self)
        self.district.name = 'Nutty River'
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
        stats.settoontownDistrictId(self.district.do_id)
        self.generateWithRequired(stats, OTP_DO_ID_TOONTOWN, OTP_ZONE_ID_DISTRICTS_STATS)

        dg = Datagram()
        dg.add_server_header([STATESERVERS_CHANNEL], self.ourChannel, STATESERVER_ADD_AI_RECV)
        dg.add_uint32(stats.do_id)
        dg.add_channel(self.ourChannel)
        self.send(dg)

        self.timeManager = TimeManagerAI(self)
        self.timeManager.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.ingameNewsMgr = DistributedInGameNewsMgrAI(self)
        self.ingameNewsMgr.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.newsManager = NewsManagerAI(self)
        self.newsManager.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.friendManager = FriendManagerAI(self)
        self.friendManager.generateGlobalObject(OTP_ZONE_ID_MANAGEMENT)

        self.loadZones()

        self.district.b_setAvailable(True)

    def loadZones(self):
        from ai.hood.HoodDataAI import DDHoodAI, TTHoodAI, BRHoodAI, MMHoodAI, DGHoodAI, DLHoodAI

        self.hoods = [
            DDHoodAI(self),
            TTHoodAI(self),
            BRHoodAI(self),
            MMHoodAI(self),
            DGHoodAI(self),
            DLHoodAI(self)
        ]

        for hood in self.hoods:
            print(f'{hood.__class__.__name__} starting up...')
            hood.startup()

        print('All zones loaded.')

    def requestDelete(self, do):
        dg = Datagram()
        dg.add_server_header([do.do_id], self.ourChannel, STATESERVER_OBJECT_DELETE_RAM)
        dg.add_uint32(do.do_id)
        self.send(dg)

    @staticmethod
    def getAvatarExitEvent(avId):
        return 'do-deleted-%d' % avId

    def allocateZone(self):
        return self.zoneAllocator.allocate()

    def deallocateZone(self, zone):
        self.zoneAllocator.free(zone)

    def getAvatarDisconnectReason(self, avId):
        return self.timeManager.disconnectCodes.get(avId)
