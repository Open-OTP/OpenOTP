import time

from .DistributedObjectAI import DistributedObjectAI


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
