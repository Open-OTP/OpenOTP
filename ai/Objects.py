import time

from .DistributedObjectAI import DistributedObjectAI
from ai.toon.DistributedToonAI import DistributedToonAI


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

    def handleChildArrive(self, obj, zoneId):
        if isinstance(obj, DistributedToonAI):
            obj.sendUpdate('arrivedOnDistrict', [self.do_id, ])


class ToontownDistrictStatsAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.districtId = 0
        self.avatarCount = 0
        self.newAvatarCount = 0

    def gettoontownDistrictId(self):
        return self.districtId

    def getAvatarCount(self):
        return self.avatarCount

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
