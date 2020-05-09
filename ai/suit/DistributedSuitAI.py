from ai.DistributedObjectAI import DistributedObjectAI

from dataclasses import dataclass
from dataslots import with_slots

from direct.task.Task import Task


# TODO: use enums here
suitHeadTypes = ['f', 'p', 'ym', 'mm', 'ds', 'hh', 'cr', 'tbc',
                 'bf', 'b', 'dt', 'ac', 'bs', 'sd', 'le', 'bw',
                 'sc', 'pp', 'tw', 'bc', 'nc', 'mb', 'ls', 'rb',
                 'cc', 'tm', 'nd', 'gh', 'ms', 'tf', 'm', 'mh']


from enum import IntEnum


class SuitDept(IntEnum):
    def __new__(cls, value, char):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.char = char
        return obj

    CORPORATE = 0, 'c'
    LAW = 1, 'l'
    MONEY = 2, 'm'
    SELL = 3, 's'


@with_slots
@dataclass
class SuitDNA:
    type: str = 's'
    name: str = 'f'
    dept: str = 'c'

    def makeNetString(self) -> bytes:
        if self.type == 's':
            return ''.join((self.type, self.name.ljust(3, '\x00'), self.dept)).encode('ascii')
        elif self.type == 'b':
            return ''.join((self.type, self.dept)).encode('ascii')
        else:
            raise ValueError(f'Unknown suit dna type: {self.type}')


class DistributedSuitBaseAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.dna = SuitDNA()
        self.level = 1
        self.skelecog = False
        self.revives = 0
        self.hp = 6

    def getDNAString(self):
        return self.dna.makeNetString()

    def getLevelDist(self):
        return self.level

    def getSkelecog(self):
        return self.skelecog

    def getSkeleRevives(self):
        return self.revives

    def getHP(self):
        return self.hp

    def d_setBrushOff(self, index):
        self.sendUpdate('setBrushOff', [index])


from dna.objects import SuitLegList, DNASuitPoint
from typing import Optional, List
from ai.suit import DistributedSuitPlannerAI


UPDATE_TIMESTAMP_INTERVAL = 60.0


class DistributedSuitAI(DistributedSuitBaseAI):
    def __init__(self, air, suitPlanner):
        DistributedSuitBaseAI.__init__(self, air)
        self.suitPlanner = suitPlanner

        self.pathState = 0
        self.pathPositionIndex = 0
        self.pathPositionTimestamp = 0
        self.pathStartTime = 0
        self.startPoint: Optional[DNASuitPoint] = None
        self.endPoint: Optional[DNASuitPoint] = None
        self.legList: Optional[SuitLegList] = None
        self.path: Optional[List[int]] = None
        self.currentLeg = 0
        self.legType = 0

    def getSPDoId(self):
        if self.suitPlanner:
            return self.suitPlanner.do_id
        else:
            return 0

    def getPathEndpoints(self):
        return self.startPoint.index, self.endPoint.index, \
               DistributedSuitPlannerAI.MIN_PATH_LEN, DistributedSuitPlannerAI.MAX_PATH_LEN

    def getPathState(self):
        return self.pathState

    def b_setPathPosition(self, pathPositionIndex, ts):
        self.pathPositionIndex = pathPositionIndex
        self.pathPositionTimestamp = ts
        self.sendUpdate('setPathPosition', self.getPathPosition())

    def getPathPosition(self):
        return self.pathPositionIndex, globalClockDelta.localToNetworkTime(self.pathPositionTimestamp)

    def requestBattle(self, x, y, z, h, p, r):
        self.sendUpdateToAvatar(self.air.currentAvatarSender, 'denyBattle', [])
        self.sendUpdate('setBrushOff', [0])

    def pointInMyPath(self, point, elapsed, collisionBuffer=5):
        if self.pathState != 1:
            return 0
        if not self.suitPlanner:
            return
        then = globalClock.getFrameTime() + elapsed
        elapsed = then - self.pathStartTime
        return self.legList.is_point_in_range(point, elapsed - collisionBuffer, elapsed + collisionBuffer)

    def initializePath(self):
        self.legList = SuitLegList(self.path, self.suitPlanner.storage)
        self.pathStartTime = globalClock.getFrameTime()
        self.pathPositionIndex = 0
        self.pathState = 1
        self.currentLeg = 0
        self.zoneId = self.legList.get_zone_id(0)
        self.legType = self.legList.get_type(0)

    def resync(self):
        self.b_setPathPosition(self.currentLeg, self.pathStartTime + self.legList.get_start_time(self.currentLeg))

    def moveToNextLeg(self, task=None):
        now = globalClock.getFrameTime()
        elapsed = now - self.pathStartTime
        nextLeg = self.legList.get_leg_index_at_time(elapsed, 0)  # self.currentLeg)
        numLegs = len(self.legList)
        if self.currentLeg != nextLeg:
            self.currentLeg = nextLeg
            self.__beginLegType(self.legList.get_type(nextLeg))
            zoneId = self.legList.get_zone_id(nextLeg)
            self.__enterZone(zoneId)
            if 1:
                leg = self.legList[nextLeg]
                pos = leg.get_pos_at_time(elapsed - leg.start_time)
                self.sendUpdate('debugSuitPosition', [elapsed, nextLeg, pos[0], pos[1], globalClockDelta.localToNetworkTime(now)])
        if now - self.pathPositionTimestamp > UPDATE_TIMESTAMP_INTERVAL:
            self.resync()
        if self.pathState != 1:
            return Task.done
        nextLeg += 1
        while nextLeg + 1 < numLegs and self.legList.get_zone_id(nextLeg) == self.zoneId and self.legList.get_type(nextLeg) == self.legType:
            nextLeg += 1

        if nextLeg < numLegs:
            nextTime = self.legList.get_start_time(nextLeg)
            delay = nextTime - elapsed
            taskMgr.doMethodLater(delay, self.moveToNextLeg, self.uniqueName('move'))
        else:
            # if self.attemptingTakeover:
            #     self.startTakeOver()
            self.requestRemoval()
        return Task.done

    def requestRemoval(self):
        if self.suitPlanner is not None:
            self.suitPlanner.removeSuit(self)
        else:
            self.requestDelete()

    def __beginLegType(self, legType):
        self.legType = legType

    def __enterZone(self, zoneId):
        if zoneId != self.zoneId:
            # print('suit zone change', self.zoneId, '->', zoneId)
            #self.suitPlanner.zoneChange(self, self.zoneId, zoneId)
            self.sendSetZone(zoneId)
            self.zoneId = zoneId
            # if self.pathState == 1:
            #     self.suitPlanner.checkForBattle(zoneId, self)
