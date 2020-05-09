import time

from .DistributedObjectAI import DistributedObjectAI
from ai.toon.DistributedToonAI import DistributedToonAI
from typing import List, Optional
from dataslots import with_slots
from dataclasses import dataclass


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
