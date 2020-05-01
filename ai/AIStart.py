from otp import config

import asyncio

from direct.directnotify import DirectNotify
from direct.showbase import Messenger, BulletinBoard, EventManager, JobManager
from direct.task import Task
from direct.interval.IntervalGlobal import ivalMgr


from panda3d.core import GraphicsEngine, ClockObject, TrueClock, PandaNode
from otp.messagetypes import *
from dc.util import Datagram
from otp.constants import *
from otp.zone import *

import time


from .DistributedObjectAI import DistributedObjectAI
from .TimeManagerAI import TimeManagerAI

directNotify = DirectNotify.DirectNotify()


OTP_ZONE_ID_OLD_QUIET_ZONE = 1
OTP_ZONE_ID_MANAGEMENT = 2
OTP_ZONE_ID_DISTRICTS = 3
OTP_ZONE_ID_DISTRICTS_STATS = 4
OTP_ZONE_ID_ELEMENTS = 5


OTP_DO_ID_TOONTOWN = 4618

from dna.dnaparser import load_dna_file
from dna.dnaparser import DNAStorage, DNAGroup


class DistributedDirectoryAI(DistributedObjectAI):
    do_id = OTP_DO_ID_TOONTOWN


class ToontownDistrictAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.name = 'ToonTown'
        self.available = True
        self.ahnnLog = False

    def getName(self):
        return self.name

    def getAvailable(self):
        return self.available

    def allowAHNNLog(self):
        return self.ahnnLog


class ToontownDistrictStatsAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.district_id = 0
        self.avatar_count = 0
        self.new_avatar_count = 0

    def gettoontownDistrictId(self):
        return self.district_id

    def getAvatarCount(self):
        return self.avatar_count

    def getNewAvatarCount(self):
        return self.new_avatar_count


class DistributedInGameNewsMgrAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.latest_issue = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(1379606399))

    def getLatestIssueStr(self):
        return self.latest_issue


class NewsManagerAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

    def getWeeklyCalendarHolidays(self):
        return []

    def getYearlyCalendarHolidays(self):
        return []

    def getOncelyCalendarHolidays(self):
        return []

    def getRelativelyCalendarHolidays(self):
        return []

    def getMultipleStartHolidays(self):
        return []


class AIBase:
    AISleep = 0.04

    def __init__(self):
        self.eventMgr = EventManager.EventManager()
        self.messenger = Messenger.Messenger()
        self.bboard = BulletinBoard.BulletinBoard()
        self.taskMgr = Task.TaskManager()

        self.graphicsEngine = GraphicsEngine()

        globalClock = ClockObject.get_global_clock()
        self.trueClock = TrueClock.get_global_ptr()
        globalClock.set_real_time(self.trueClock.get_short_time())
        globalClock.set_average_frame_rate_interval(30.0)
        globalClock.tick()
        self.taskMgr.globalClock = globalClock

        self._setup()

        self.air = AIRepository()

    def _setup(self):
        self.taskMgr.add(self._reset_prev_transform, 'resetPrevTransform', priority=-51)
        self.taskMgr.add(self._ival_loop, 'ivalLoop', priority=20)
        self.taskMgr.add(self._ig_loop, 'igLoop', priority=50)
        self.eventMgr.restart()

    def _reset_prev_transform(self, state):
        PandaNode.resetAllPrevTransform()
        return Task.cont

    def _ival_loop(self, state):
        ivalMgr.step()
        return Task.cont

    def _ig_loop(self, state):
        self.graphicsEngine.renderFrame()
        return Task.cont

    def run(self):
        self.air.run()
        self.start_read_poll_task()
        self.taskMgr.run()

    def stop(self):
        self.taskMgr.stop()

    def start_read_poll_task(self):
        self.taskMgr.add(self.air.read_until_empty, 'readPoll', priority=-30)


from otp.networking import ToontownProtocol


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


from panda3d.core import UniqueIdAllocator
from dc.parser import parse_dc_file
import queue

from typing import Dict


class AIRepository:
    def __init__(self):
        self.connection = None
        self.queue = queue.Queue()

        base_channel = 4000000

        max_channels = 1000000
        self.channel_allocator = UniqueIdAllocator(base_channel, base_channel + max_channels - 1)

        self._registered_channels = set()

        self.__contextCounter = 0
        self.__callbacks = {}

        self.our_channel = self.allocate_channel()

        self.do_table: Dict[int, DistributedObjectAI] = {}
        self.zone_table: Dict[int, set] = {}
        self.parent_table: Dict[int, set] = {}

        self.dc_file = parse_dc_file('toon.dc')

        self.current_sender = None
        self.loop = None
        self.net_thread = None

        self.dna_storage: Dict[int, DNAStorage] = {}
        self.dna_map: Dict[int, DNAGroup] = {}

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
        self.create_objects()
        self.loop.run_forever()

    def _on_connect(self):
        self.connection = AIProtocol(self)
        return self.connection

    def read_until_empty(self, task):
        while True:
            try:
                dg = self.queue.get(timeout=0.05)
            except queue.Empty:
                break
            else:
                self.handle_datagram(dg)

        return task.cont

    def handle_datagram(self, dg):
        dgi = dg.iterator()

        recipient_count = dgi.get_uint8()
        recipients = [dgi.get_channel() for _ in range(recipient_count)]
        self.current_sender = dgi.get_channel()
        msg_type = dgi.get_uint16()

        if msg_type == STATESERVER_OBJECT_ENTER_AI_RECV:
            if self.current_sender == self.our_channel:
                return
            self.handle_obj_entry(dgi)
        elif msg_type == STATESERVER_OBJECT_DELETE_RAM:
            pass
        elif msg_type == STATESERVER_OBJECT_LEAVING_AI_INTEREST:
            pass
        elif msg_type == STATESERVER_OBJECT_CHANGE_ZONE:
            self.handle_change_zone(dgi)
        elif msg_type == STATESERVER_OBJECT_UPDATE_FIELD:
            if self.current_sender == self.our_channel:
                return
            self.handle_update_field(dgi)
        else:
            print('Unhandled msg type: ', msg_type)

    def handle_change_zone(self, dgi):
        do_id = dgi.get_uint32()
        new_parent = dgi.get_uint32()
        new_zone = dgi.get_uint32()

        # Should we only change location if the old location matches?
        old_parent = dgi.get_uint32()
        old_zone = dgi.get_uint32()

        self.do_table[do_id].location = (new_parent, new_zone)
        self.store_location(do_id, old_parent, old_zone, new_parent, new_zone)

    def store_location(self, do_id, old_parent, old_zone, new_parent, new_zone):
        if not do_id:
            return

        if old_zone and old_zone in self.zone_table and do_id in self.zone_table[old_zone]:
            self.zone_table[old_zone].remove(do_id)

        if old_parent and old_parent in self.parent_table and do_id in self.parent_table[old_parent]:
            self.parent_table[old_parent].remove(do_id)

        if new_zone:
            if new_zone not in self.zone_table:
                self.zone_table[new_zone] = set()

            self.zone_table[new_zone].add(do_id)

        if new_parent:
            if new_parent not in self.parent_table:
                self.parent_table[new_parent] = set()

            self.parent_table[new_parent].add(do_id)

    def send_location(self, do_id, old_parent: int, old_zone: int, new_parent: int, new_zone: int):
        dg = Datagram()
        dg.add_server_header([do_id], self.our_channel, STATESERVER_OBJECT_CHANGE_ZONE)
        dg.add_uint32(do_id)
        dg.add_uint32(new_parent)
        dg.add_uint32(new_zone)
        dg.add_uint32(old_parent)
        dg.add_uint32(old_zone)
        self.send(dg)

    @staticmethod
    def is_client_channel(channel):
        return config['ClientAgent.MIN_CHANNEL'] <= channel <= config['ClientAgent.MAX_CHANNEL']

    def set_interest(self, client_channel, handle, context, parent_id, zones):
        dg = Datagram()
        dg.add_server_header([client_channel], self.our_channel, CLIENT_AGENT_SET_INTEREST)
        dg.add_uint16(handle)
        dg.add_uint32(context)
        dg.add_uint32(parent_id)
        for zone in zones:
            dg.add_uint32(zone)
        self.send(dg)

    def remove_interest(self, client_channel, handle, context, parent_id, zones):
        dg = Datagram()
        dg.add_server_header([client_channel], self.our_channel, CLIENT_AGENT_REMOVE_INTEREST)
        dg.add_uint16(handle)
        dg.add_uint32(context)
        self.send(dg)

    def handle_update_field(self, dgi):
        do_id = dgi.get_uint32()
        field_number = dgi.get_uint16()

        # TODO: security check here for client senders.

        field = self.dc_file.fields[field_number]()

        self.current_sender = self.current_sender
        do = self.do_table[do_id]
        field.receive_update(do, dgi)

    @property
    def current_av_sender(self):
        return getAvatarIDFromChannel(self.current_sender)

    def handle_obj_entry(self, dgi):
        do_id = dgi.get_uint32()
        parent_id = dgi.get_uint32()
        zone_id = dgi.get_uint32()
        dc_id = dgi.get_uint16()

        dclass = self.dc_file.classes[dc_id]

        if do_id in self.do_table:
            return

        if dclass.name == 'DistributedToon':
            from .DistributedToon import DistributedToonAI

            obj = DistributedToonAI(self)
            obj.do_id = do_id
            obj.location = (parent_id, zone_id)
            dclass.receive_update_all_required(obj, dgi)
            self.do_table[obj.do_id] = obj
            self.store_location(do_id, 0, 0, parent_id, zone_id)

            obj.send_update('arrivedOnDistrict', [self.district.do_id, ])
        else:
            print('unknown object entry: %s' % dclass.name)

    def context(self):
        self.__contextCounter = (self.__contextCounter + 1) & 0xFFFFFFFF
        return self.__contextCounter

    def allocate_channel(self):
        return self.channel_allocator.allocate()

    def deallocate_channel(self, channel):
        self.channel_allocator.free(channel)

    def register_for_channel(self, channel):
        if channel in self._registered_channels:
            return
        self._registered_channels.add(channel)

        dg = Datagram()
        dg.add_server_control_header(CONTROL_SET_CHANNEL)
        dg.add_channel(channel)
        self.send(dg)

    def unregister_for_channel(self, channel):
        if channel not in self._registered_channels:
            return
        self._registered_channels.remove(channel)

        dg = Datagram()
        dg.add_server_control_header(CONTROL_REMOVE_CHANNEL)
        dg.add_channel(channel)
        self.send(dg)

    def send(self, dg):
        self.connection.send_datagram(dg)

    def generate_with_required(self, do, parent_id, zone_id, optional=()):
        do_id = self.allocate_channel()
        self.generate_with_required_and_id(do, do_id, parent_id, zone_id, optional)

    def generate_with_required_and_id(self, do, do_id, parent_id, zone_id, optional=()):
        do.do_id = do_id
        self.do_table[do_id] = do
        dg = do.dclass.ai_format_generate(do, do_id, parent_id, zone_id, STATESERVERS_CHANNEL, self.our_channel, optional)
        self.send(dg)

        do.location = (parent_id, zone_id)
        do.generate()
        do.announce_generate()

    def create_objects(self):
        self.register_for_channel(self.our_channel)

        self.district = ToontownDistrictAI(self)
        self.generate_with_required(self.district, OTP_DO_ID_TOONTOWN, OTP_ZONE_ID_DISTRICTS)

        post_remove = Datagram()
        post_remove.add_server_control_header(CONTROL_ADD_POST_REMOVE)
        post_remove.add_server_header([STATESERVERS_CHANNEL, ], self.our_channel, STATESERVER_SHARD_REST)
        post_remove.add_channel(self.our_channel)
        self.send(post_remove)

        dg = Datagram()
        dg.add_server_header([STATESERVERS_CHANNEL], self.our_channel, STATESERVER_ADD_AI_RECV)
        dg.add_uint32(self.district.do_id)
        dg.add_channel(self.our_channel)
        self.send(dg)

        stats = ToontownDistrictStatsAI(self)
        self.generate_with_required(stats, OTP_DO_ID_TOONTOWN, OTP_ZONE_ID_DISTRICTS_STATS)

        dg = Datagram()
        dg.add_server_header([STATESERVERS_CHANNEL], self.our_channel, STATESERVER_ADD_AI_RECV)
        dg.add_uint32(stats.do_id)
        dg.add_channel(self.our_channel)
        self.send(dg)

        time_mgr = TimeManagerAI(self)
        self.generate_with_required(time_mgr, self.district.do_id, OTP_ZONE_ID_MANAGEMENT)

        ingame_news = DistributedInGameNewsMgrAI(self)
        self.generate_with_required(ingame_news, self.district.do_id, OTP_ZONE_ID_MANAGEMENT)

        news_mgr = NewsManagerAI(self)
        self.generate_with_required(news_mgr, self.district.do_id, OTP_ZONE_ID_MANAGEMENT)

        time_mgr = TimeManagerAI(self)
        self.generate_with_required(time_mgr, self.district.do_id, OTP_ZONE_ID_MANAGEMENT)

        self.load_zones()

    def load_zones(self):
        from ai.hood.HoodDataAI import TTHoodDataAI

        self.hoods = [
            TTHoodDataAI(self)
        ]

        for hood in self.hoods:
            hood.active = True

    def load_dna_file(self, path: str):
        root, storage = load_dna_file(path)
        return root, storage


def main():
    print('running main')
    import builtins
    builtins.simbase = AIBase()
    builtins.taskMgr = simbase.taskMgr
    simbase.run()


if __name__ == '__main__':
    main()
