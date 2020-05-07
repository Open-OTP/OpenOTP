from ai.DistributedObjectAI import DistributedObjectAI

from dataclasses import dataclass
from dataslots import with_slots
from typing import List, Tuple, Dict

from ai.ToontownGlobals import *
from panda3d.core import Point3

from direct.task import Task


@with_slots
@dataclass
class SuitHoodInfo:
    zoneId: int
    minSuits: int
    maxSuits: int
    minSuitBldgs: int
    maxSuitBldgs: int
    buildingWeight: int
    maxBattleSuits: int
    joinChances: Tuple[int]
    deptChances: Tuple[int]
    levels: Tuple[int]
    buildingDifficulties: Tuple[int]


SUIT_HOOD_INFO = {
    SillyStreet: SuitHoodInfo(zoneId=SillyStreet, minSuits=5, maxSuits=15, minSuitBldgs=0, maxSuitBldgs=5, buildingWeight=20,
                              maxBattleSuits=3, joinChances=(1, 5, 10, 40, 60, 80), deptChances=(25, 25, 25, 25),
                              levels=(1, 2, 3), buildingDifficulties=()),
    LoopyLane: SuitHoodInfo(zoneId=SillyStreet, minSuits=3, maxSuits=10, minSuitBldgs=0, maxSuitBldgs=5,
                            buildingWeight=15, maxBattleSuits=3, joinChances=(1, 5, 10, 40, 60, 80),
                            deptChances=(10, 70, 10, 10), levels=(1, 2, 3), buildingDifficulties=()),
    PunchlinePlace: SuitHoodInfo(zoneId=PunchlinePlace, minSuits=3, maxSuits=10, minSuitBldgs=0, maxSuitBldgs=5,
                                 buildingWeight=15, maxBattleSuits=3, joinChances=(1, 5, 10, 40, 60, 80),
                                 deptChances=(10, 10, 40, 40), levels=(1, 2, 3), buildingDifficulties=()),
}

from dna.objects import DNASuitPoint, SuitPointType, SuitLegType, FROM_SKY, SUIT_WALK_SPEED
import random
from typing import Optional

from ai.suit.DistributedSuitAI import DistributedSuitAI, SuitDNA, SuitDept, suitHeadTypes


UPKEEP_DELAY = 10
ADJUST_DELAY = 300
PATH_COLLISION_BUFFER = 5

MIN_PATH_LEN = 40
MAX_PATH_LEN = 300
MAX_SUIT_TYPES = 6


def pickFromFreqList(freqList):
    randNum = random.randint(0, 99)
    count = 0
    index = 0
    level = None
    for f in freqList:
        count = count + f
        if randNum < count:
            level = index
            break
        index = index + 1

    return level


class DistributedSuitPlannerAI(DistributedObjectAI):
    def __init__(self, air, place):
        DistributedObjectAI.__init__(self, air)
        self.place = place
        self.zoneId = self.place.zone_id
        self.info: SuitHoodInfo = SUIT_HOOD_INFO[place.zone_id]
        self.battleMgr: BattleManagerAI = BattleManagerAI(self.air)

        self.zone2battlePos: Dict[int, Point3] = {}

        for visGroup in self.storage.visgroups:
            zoneId = int(visGroup.name)
            if not visGroup.battle_cells:
                print('zone has no battle cells: %d' % zoneId)
                continue

            self.zone2battlePos[zoneId] = visGroup.battle_cells[0].pos

            if len(visGroup.battle_cells) > 1:
                print('Multiple battle cells for zoneId: %d' % zoneId)

        self.streetPoints: List[DNASuitPoint] = []
        self.frontDoorPoints: List[DNASuitPoint] = []
        self.sideDoorPoints: List[DNASuitPoint] = []
        self.cogHQDoorPoints: List[DNASuitPoint] = []

        for suitPoint in self.storage.suit_points:
            if suitPoint.point_type == SuitPointType.STREET_POINT:
                self.streetPoints.append(suitPoint)
            elif suitPoint.point_type == SuitPointType.FRONT_DOOR_POINT:
                self.frontDoorPoints.append(suitPoint)
            elif suitPoint.point_type == SuitPointType.SIDE_DOOR_POINT:
                self.sideDoorPoints.append(suitPoint)
            elif suitPoint.point_type == SuitPointType.COGHQ_IN_POINT or suitPoint.point_type == SuitPointType.COGHQ_OUT_POINT:
                self.cogHQDoorPoints.append(suitPoint)

        self.suits: List[DistributedSuitAI] = []
        self.baseNumSuits = (self.info.maxSuits + self.info.minSuits) // 2
        self.popAdjustment = 0
        self.numFlyInSuits = 0

    def getZoneId(self):
        return self.zoneId

    def genPath(self, startPoint, endPoint, minPathLen, maxPathLen):
        return self.storage.get_suit_path(startPoint, endPoint, minPathLen, maxPathLen)

    @property
    def dna(self):
        return self.place.dna

    @property
    def storage(self):
        return self.place.storage

    def startup(self):
        self.upkeep()
        self.adjust()

    def createNewSuit(self):
        streetPoints = list(range(len(self.streetPoints)))
        random.shuffle(streetPoints)

        startPoint = None

        while startPoint is None and streetPoints:
            point = self.streetPoints[streetPoints.pop()]

            if not self.pointCollision(point.index, None, FROM_SKY):
                startPoint = point

        if startPoint is None:
            print('start pt is none')
            return False

        suit = DistributedSuitAI(self.air, self)
        print(suit.getSPDoId())
        suit.startPoint = startPoint
        suit.flyInSuit = 1

        if not self.chooseDestination(suit, FROM_SKY):
            print('failed to choose destination')
            suit.delete()
            return False

        level = random.choice(self.info.levels)
        tiers = range(max(level - 4, 0), min(level, MAX_SUIT_TYPES))
        tier = random.choice(tiers)
        department = pickFromFreqList(self.info.deptChances)
        name = suitHeadTypes[department * 8 + tier]
        print('generated suit:', name, level, suit.path)
        suit.dna = SuitDNA(type='s', name=name, dept=SuitDept(department).char)
        suit.level = level
        suit.initializePath()
        suit.generateWithRequired(suit.zoneId)
        suit.moveToNextLeg(None)
        self.suits.append(suit)
        self.numFlyInSuits += 1
        return True

    def upkeep(self, task=None):
        desired = self.baseNumSuits + self.popAdjustment
        desired = min(desired, self.info.maxSuits)
        deficit = (desired - self.numFlyInSuits + 3) / 4
        while deficit > 0:
            if not self.createNewSuit():
                break
            deficit -= 1

        t = random.random() * 2.0 + UPKEEP_DELAY
        taskMgr.doMethodLater(t, self.upkeep, self.uniqueName('upkeep-suits'))

    def adjust(self, task=None):
        if self.info.maxSuits == 0:
            return Task.done

        adjustment = random.choice((-2, -1, -1, 0, 0, 0, 1, 1, 2))
        self.popAdjustment += adjustment

        desired = self.baseNumSuits + self.popAdjustment

        if desired < self.info.minSuits:
            self.popAdjustment = self.info.minSuits - self.baseNumSuits
        elif desired > self.info.maxSuits:
            self.popAdjustment = self.info.maxSuits - self.baseNumSuits

        t = random.random() * 2.0 + ADJUST_DELAY
        taskMgr.doMethodLater(t, self.upkeep, self.uniqueName('adjust-suits'))

    def pointCollision(self, point: int, adjacentPoint: Optional[int], elapsedTime):
        for suit in self.suits:
            if suit.pointInMyPath(point, elapsedTime, PATH_COLLISION_BUFFER):
                return True

        if adjacentPoint is not None:
            return self.battleCollision(point, adjacentPoint)
        else:
            adjacentPoints = self.storage.get_adjacent_points(point)

            for adjacentPoint in adjacentPoints:
                if self.battleCollision(point, adjacentPoint):
                    return True

        return False

    def battleCollision(self, point: int, adjacentPoint: int):
        zone = self.storage.get_suit_edge_zone(point, adjacentPoint)
        return self.battleMgr.cellHasBattle(zone)

    def pathCollision(self, path: List[int], elapsedTime):
        i = 0
        pointIndex, adjacentPointIndex = path[i], path[i + 1]
        point = self.storage.suit_point_map[pointIndex]

        while point.point_type == SuitPointType.FRONT_DOOR_POINT or point.point_type == SuitPointType.SIDE_DOOR_POINT:
            i += 1
            elapsedTime += self.storage.get_suit_edge_travel_time(pointIndex, adjacentPointIndex, SUIT_WALK_SPEED)
            pointIndex, adjacentPointIndex = path[i], path[i + 1]
            point = self.storage.suit_point_map[pointIndex]

        return self.pointCollision(pointIndex, adjacentPointIndex, elapsedTime)

    def chooseDestination(self, suit: DistributedSuitAI, startTime):
        streetPoints = list(range(len(self.streetPoints)))
        random.shuffle(streetPoints)

        retries = 0
        while streetPoints and retries < 50:
            endPoint = self.streetPoints[streetPoints.pop()]

            path = self.genPath(suit.startPoint, endPoint, MIN_PATH_LEN, MAX_PATH_LEN)

            if path and not self.pathCollision(path, startTime):
                suit.endPoint = endPoint
                print('CHOSEN PATH:', suit.startPoint, endPoint, path)
                suit.path = path
                return 1

            retries += 1

    def removeSuit(self, suit: DistributedSuitAI):
        suit.requestDelete()
        self.suits.remove(suit)
        if suit.flyInSuit:
            self.numFlyInSuits -= 1


class BattleManagerAI:
    BATTLE_CONSTRUCTOR = None
    __slots__ = 'air', 'cell2Battle'

    def __init__(self, air):
        self.air = air
        self.cell2Battle: Dict[int, object] = {}

    def newBattle(self, suit, toonId, cellId, zoneId, pos):
        pass

    def requestBattleAddSuit(self, cellId, suit):
        pass

    def cellHasBattle(self, cellId):
        return cellId in self.cell2Battle
