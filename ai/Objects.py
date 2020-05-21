import time

from .DistributedObjectAI import DistributedObjectAI
from ai.toon.DistributedToonAI import DistributedToonAI
from typing import List, Optional, Dict
from dataslots import with_slots
from dataclasses import dataclass

from dc.util import Datagram
from otp.util import getPuppetChannel
from otp.messagetypes import CLIENT_FRIEND_ONLINE


class DistributedDistrictAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.name = ''
        self.available = False

    def d_setName(self, name):
        self.sendUpdate('setName', [name])

    def b_setName(self, name):
        self.name = name
        self.d_setName(name)

    def getName(self):
        return self.name

    def d_setAvailable(self, available):
        self.sendUpdate('setAvailable', [available])

    def b_setAvailable(self, available):
        self.available = available
        self.d_setAvailable(available)

    def getAvailable(self):
        return self.available


class ToontownDistrictAI(DistributedDistrictAI):
    def __init__(self, air):
        DistributedDistrictAI.__init__(self, air)
        self.ahnnLog = False

    def allowAHNNLog(self, ahnnLog):
        self.ahnnLog = ahnnLog

    def d_allowAHNNLog(self, ahnnLog):
        self.sendUpdate('allowAHNNLog', [ahnnLog])

    def b_allowAHNNLog(self, ahnnLog):
        self.allowAHNNLog(ahnnLog)
        self.d_allowAHNNLog(ahnnLog)

    def allowAHNNLog(self):
        return self.ahnnLog

    def handleChildArrive(self, obj, zoneId):
        if isinstance(obj, DistributedToonAI):
            obj.sendUpdate('arrivedOnDistrict', [self.do_id, ])


class ToontownDistrictStatsAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.toontownDistrictId = 0
        self.avatarCount = 0
        self.newAvatarCount = 0

    def settoontownDistrictId(self, toontownDistrictId):
        self.toontownDistrictId = toontownDistrictId

    def d_settoontownDistrictId(self, toontownDistrictId):
        self.sendUpdate('settoontownDistrictId', [toontownDistrictId])

    def b_settoontownDistrictId(self, toontownDistrictId):
        self.settoontownDistrictId(toontownDistrictId)
        self.d_settoontownDistrictId(toontownDistrictId)

    def gettoontownDistrictId(self):
        return self.toontownDistrictId

    def setAvatarCount(self, avatarCount):
        self.avatarCount = avatarCount

    def d_setAvatarCount(self, avatarCount):
        self.sendUpdate('setAvatarCount', [avatarCount])

    def b_setAvatarCount(self, avatarCount):
        self.setAvatarCount(avatarCount)
        self.d_setAvatarCount(avatarCount)

    def getAvatarCount(self):
        return self.avatarCount

    def setNewAvatarCount(self, newAvatarCount):
        self.newAvatarCount = newAvatarCount

    def d_setNewAvatarCount(self, newAvatarCount):
        self.sendUpdate('setNewAvatarCount', [newAvatarCount])

    def b_setNewAvatarCount(self, newAvatarCount):
        self.setNewAvatarCount(newAvatarCount)
        self.d_setNewAvatarCount(newAvatarCount)

    def getNewAvatarCount(self):
        return self.newAvatarCount


class DistributedInGameNewsMgrAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.latest_issue = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(1379606399))

    def getLatestIssueStr(self):
        return self.latest_issue


@with_slots
@dataclass
class WeeklyHoliday:
    holidayId: int
    weekday: int

    def __iter__(self):
        yield self.holidayId
        yield self.weekday


@with_slots
@dataclass
class YearlyHoliday:
    holidayId: int
    startMonth: int
    startDay: int
    endMonth: int
    endDay: int

    def __iter__(self):
        yield self.holidayId
        yield (self.startMonth, self.startDay)
        yield (self.endMonth, self.endDay)


@with_slots
@dataclass
class OncelyHoliday:
    holidayId: int
    startMonth: int
    startDay: int
    endMonth: int
    endDay: int

    def __iter__(self):
        yield self.holidayId
        yield (self.startMonth, self.startDay)
        yield (self.endMonth, self.endDay)


@with_slots
@dataclass
class MultipleStartDate:
    startYear: int
    startMonth: int
    startDay: int
    endYear: int
    endMonth: int
    endDay: int

    def __iter__(self):
        yield (self.startYear, self.startMonth, self.startDay)
        yield (self.endYear, self.endMonth, self.endDay)


class MultipleStartHoliday:
    __slots__ = 'holidayId', 'times'

    def __init__(self, holidayId: int, times: List[MultipleStartDate]):
        self.holidayId = holidayId
        self.times = [tuple(date) for date in times]

    def __iter__(self):
        yield self.holidayId
        yield self.times

from ai.HolidayGlobals import *


class NewsManagerAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.weeklyHolidays: List[WeeklyHoliday] = []
        self.yearlyHolidays: List[YearlyHoliday] = []
        self.oncelyHolidays: List[OncelyHoliday] = []
        self.multipleStartHolidays: List[MultipleStartHoliday] = []
        self.relativeHolidays = []
        self.holidayIds: List[int] = []

        self.holidays = [
            SillyMeterHolidayAI(self.air)
        ]

    def announceGenerate(self):
        for holiday in self.holidays:
            holiday.start()

    def getWeeklyCalendarHolidays(self):
        return [tuple(holiday) for holiday in self.weeklyHolidays]

    def getYearlyCalendarHolidays(self):
        return [tuple(holiday) for holiday in self.yearlyHolidays]

    def getOncelyCalendarHolidays(self):
        return [tuple(holiday) for holiday in self.oncelyHolidays]

    def getMultipleStartHolidays(self):
        return [tuple(holiday) for holiday in self.multipleStartHolidays]

    # TODO: figure out how relative holidays work
    def getRelativelyCalendarHolidays(self):
        return []

    def d_setHolidayIdList(self):
        self.sendUpdate('setHolidayIdList', [self.holidayIds])


class HolidayBaseAI:
    holidayId = None

    def __init__(self, air):
        self.air = air

    def start(self):
        self.air.newsManager.holidayIds.append(self.holidayId)
        self.air.newsManager.d_setHolidayIdList()

    def stop(self):
        self.air.newsManager.holidayIds.remove(self.holidayId)
        self.air.newsManager.d_setHolidayIdList()


from otp.constants import *


class DistributedPhaseEventMgrAI(DistributedObjectAI):
    def getNumPhases(self):
        raise NotImplementedError

    def getDates(self):
        raise NotImplementedError

    def getCurPhase(self):
        raise NotImplementedError

    def getIsRunning(self):
        return False


class DistributedSillyMeterMgrAI(DistributedPhaseEventMgrAI):
    def getNumPhases(self):
        return 15

    def getDates(self):
        return []

    def getCurPhase(self):
        return 11

    def getIsRunning(self):
        return 1


class SillyMeterHolidayAI(HolidayBaseAI):
    holidayId = SILLYMETER_HOLIDAY

    def start(self):
        super().start()
        self.air.sillyMgr = DistributedSillyMeterMgrAI(self.air)
        self.air.sillyMgr.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

    def stop(self):
        super().stop()
        self.air.sillyMgr.requestDelete()
        del self.air.sillyMgr


from .DistributedObjectGlobalAI import DistributedObjectGlobalAI


class FriendRequest:
    CANCELLED = -1
    INACTIVE = 0
    FRIEND_QUERY = 1
    FRIEND_CONSIDERING = 2

    def __init__(self, avId, requestedId, state):
        self.avId = avId
        self.requestedId = requestedId
        self.state = state

    @property
    def cancelled(self):
        return self.state == FriendRequest.CANCELLED

    def isRequestedId(self, avId):
        return avId == self.requestedId


class InviteeResponse:
    NOT_AVAILABLE = 0
    ASKING = 1
    ALREADY_FRIENDS = 2
    SELF_FRIEND = 3
    IGNORED = 4
    NO_NEW_FRIENDS = 6
    NO = 10
    TOO_MANY_FRIENDS = 13


MAX_FRIENDS = 50
MAX_PLAYER_FRIENDS = 300


class FriendManagerAI(DistributedObjectGlobalAI):
    do_id = OTP_DO_ID_FRIEND_MANAGER

    def __init__(self, air):
        DistributedObjectGlobalAI.__init__(self, air)
        self.requests: Dict[int, FriendRequest] = {}
        self._context = 0

    @property
    def next_context(self):
        self._context = (self._context + 1) & 0xFFFFFFFF
        return self._context

    def friendQuery(self, requested):
        avId = self.air.currentAvatarSender
        if requested not in self.air.doTable:
            return
        av = self.air.doTable.get(avId)
        if not av:
            return
        context = self.next_context
        self.requests[context] = FriendRequest(avId, requested, FriendRequest.FRIEND_QUERY)
        self.sendUpdateToAvatar(requested, 'inviteeFriendQuery', [avId, av.getName(), av.getDNAString(), context])

    def cancelFriendQuery(self, context):
        avId = self.air.currentAvatarSender
        if avId not in self.air.doTable:
            return

        request = self.requests.get(context)
        if not request or avId != request.avId:
            return
        request.state = FriendRequest.CANCELLED
        self.sendUpdateToAvatar(request.requestedId, 'inviteeCancelFriendQuery', [context])

    def inviteeFriendConsidering(self, response, context):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)
        if not av:
            return

        request = self.requests.get(context)
        if not request:
            return

        if not request.isRequestedId(avId):
            return

        if request.state != FriendRequest.FRIEND_QUERY:
            return

        if response != InviteeResponse.ASKING:
            request.state = FriendRequest.CANCELLED
            del self.requests[context]
        else:
            request.state = FriendRequest.FRIEND_CONSIDERING

        self.sendUpdateToAvatar(request.avId, 'friendConsidering', [response, context])

    def inviteeFriendResponse(self, response, context):
        avId = self.air.currentAvatarSender
        requested = self.air.doTable.get(avId)
        if not requested:
            return

        request = self.requests.get(context)
        if not request:
            return

        if not request.isRequestedId(avId):
            return

        if request.state != FriendRequest.FRIEND_CONSIDERING:
            return

        self.sendUpdateToAvatar(request.avId, 'friendResponse', [response, context])

        if response == 1:
            requester = self.air.doTable.get(request.avId)

            if not (requested and requester):
                # Likely they logged off just before a response was sent. RIP.
                return

            requested.extendFriendsList(requester.do_id, False)
            requester.extendFriendsList(requested.do_id, False)

            requested.d_setFriendsList(requested.getFriendsList())
            requester.d_setFriendsList(requester.getFriendsList())

            taskMgr.doMethodLater(1, self.sendFriendOnline, f'send-online-{requested.do_id}-{requester.do_id}',
                                  extraArgs=[requested.do_id, requester.do_id])
            taskMgr.doMethodLater(1, self.sendFriendOnline, f'send-online-{requester.do_id}-{requested.do_id}',
                                  extraArgs=[requester.do_id, requested.do_id])

    def sendFriendOnline(self, avId, otherAvId):
        # Need this delay so that `setFriendsList` is set first to avoid
        # the online whisper message.
        dg = Datagram()
        dg.add_server_header([getPuppetChannel(avId)], self.air.ourChannel, CLIENT_FRIEND_ONLINE)
        dg.add_uint32(otherAvId)
        self.air.send(dg)
