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
