from ai.DistributedObjectAI import DistributedObjectAI
from typing import Optional, List
import random


class DistributedTreasureAI(DistributedObjectAI):
    def __init__(self, air, treasurePlanner, x, y, z):
        DistributedObjectAI.__init__(self, air)
        self.treasurePlanner = treasurePlanner
        self.pos = (x, y, z)

    def getPosition(self):
        return self.pos

    def requestGrab(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable[avId]
        if not av:
            return
        self.treasurePlanner.grabAttempt(av, self)

    def validAvatar(self, av):
        return True

    def d_setGrab(self, avId):
        self.sendUpdate('setGrab', [avId])

    def d_setReject(self):
        self.sendUpdate('setReject', [])


class TreasurePlanner:
    treasureClass = DistributedTreasureAI
    spawnPoints = []

    def __init__(self, zoneId, callback=lambda _: None):
        self.zoneId = zoneId
        self.treasures: List[Optional[DistributedTreasureAI]] = [None for _ in range(len(self.spawnPoints))]
        self.lastRequestId = 0
        self.callback = callback
        self.deleteTaskNames = set()

    @property
    def numTreasures(self):
        return sum(1 for _ in filter(None.__ne__, self.treasures))

    def placeAllTreasures(self):
        for i in range(len(self.treasures)):
            self.placeTreasure(i)

    def placeTreasure(self, index):
        treasure = self.treasureClass(simbase.air, self, *self.spawnPoints[index])
        treasure.generateWithRequired(self.zoneId)
        self.treasures[index] = treasure

    def grabAttempt(self, av, treasure: DistributedTreasureAI):
        index = self.treasures.index(treasure)
        avId = av.do_id

        if treasure.validAvatar(av):
            self.treasures[index] = None
            self.callback(avId)
            treasure.d_setGrab(avId)
            self.deleteTreasureSoon(treasure)
        else:
            treasure.d_setReject()

    def deleteTreasureSoon(self, treasure):
        taskName = treasure.uniqueName('deletingTreasure')
        taskMgr.doMethodLater(5, self.__deleteTreasureNow, taskName, extraArgs=(treasure, taskName))
        self.deleteTaskNames.add(taskName)

    def __deleteTreasureNow(self, treasure, taskName):
        treasure.requestDelete()
        self.deleteTaskNames.remove(taskName)

    def deleteAllTreasures(self):
        for taskName in self.deleteTaskNames:
            taskMgr.remove(taskName)
        self.deleteTaskNames = set()

        for treasure in filter(None.__ne__, self.treasures):
            treasure.requestDelete()
        self.treasures = [None for _ in range(len(self.spawnPoints))]


class RegenTreasurePlanner(TreasurePlanner):
    spawnInterval = 20
    maxTreasures = 0
    healAmount = 1

    def __init__(self, zoneId, callback=lambda _: None):
        super().__init__(zoneId, callback)
        self.taskName = f'{self.__class__.__name__}-{zoneId}'

    def placeRandomTreasure(self):
        indexes = [i for i, treasure in enumerate(self.treasures) if treasure is None]
        if not indexes:
            return None

        index = random.choice(indexes)
        self.placeTreasure(index)

    def start(self):
        for i in range(self.maxTreasures):
            self.placeRandomTreasure()
        taskMgr.doMethodLater(self.spawnInterval, self.upkeep, self.taskName)

    def upkeep(self, task):
        if self.numTreasures < self.maxTreasures:
            self.placeRandomTreasure()
        taskMgr.doMethodLater(self.spawnInterval, self.upkeep, self.taskName)
        return task.done

    def stop(self):
        taskMgr.remove(self.taskName)


class DistributedSZTreasureAI(DistributedTreasureAI):
    def __init__(self, air, treasurePlanner: RegenTreasurePlanner, x, y, z):
        DistributedTreasureAI.__init__(self, air, treasurePlanner, x, y, z)
        self.healAmount = treasurePlanner.healAmount

    def validAvatar(self, av):
        return 0 < av.hp < av.maxHp

    def d_setGrab(self, avId):
        DistributedTreasureAI.d_setGrab(self, avId)
        av = self.air.doTable[avId]
        # TODO
        # if simbase.air.holidayManager.currentHolidays.has_key(ToontownGlobals.VALENTINES_DAY):
        #    av.toonUp(self.healAmount * 2)
        av.toonUp(self.healAmount)


class DistributedTTTreasureAI(DistributedSZTreasureAI):
    pass


class DistributedDDTreasureAI(DistributedSZTreasureAI):
    pass


class DistributedDGTreasureAI(DistributedSZTreasureAI):
    pass


class DistributedMMTreasureAI(DistributedSZTreasureAI):
    pass


class DistributedBRTreasureAI(DistributedSZTreasureAI):
    pass


class DistributedDLTreasureAI(DistributedSZTreasureAI):
    pass


class DistributedOZTreasureAI(DistributedSZTreasureAI):
    pass


class DistributedTagTreasureAI(DistributedTreasureAI):
    pass


class TTTreasurePlanner(RegenTreasurePlanner):
    treasureClass = DistributedTTTreasureAI
    spawnInterval, maxTreasures, healAmount = 20, 5, 3

    spawnPoints = (
        (-59.9, -6.9, 0.84),
        (-90.6, -3.0, -0.75),
        (27.1, -93.5, 2.5),
        (94.2, 33.5, 4),
        (35.4, 43.1, 4),
        (67.1, 105.5, 2.5),
        (-99.15, -87.3407, 0.52499),
        (1.60586, -119.492, 3.025),
        (43.2026, -76.287, 3.025),
        (129.137, -61.9039, 2.525),
        (92.99, -158.399, 3.025),
        (111.749, -8.59927, 4.57466),
        (41.999, -30.2923, 4.025),
        (31.0649, -43.9149, 4.025),
        (10.0156, 105.218, 2.525),
        (46.9667, 169.143, 3.025),
        (100.68, 93.9896, 2.525),
        (129.285, 58.6107, 2.525),
        (-28.6272, 85.9833, 0.525),
        (-114.613, 86.1727, 0.525),
        (-132.528, 31.255, 0.025))


class DDTreasurePlanner(RegenTreasurePlanner):
    treasureClass = DistributedDDTreasureAI
    spawnInterval, maxTreasures, healAmount = 20, 2, 10

    spawnPoints = (
        (52.907200000000003, -23.476800000000001, -12.308),
        (35.3827, -51.919600000000003, -12.308),
        (17.4252, -57.310699999999997, -12.308),
        (-0.71605399999999997, -68.5, -12.308),
        (-29.0169, -66.8887, -12.308),
        (-63.491999999999997, -64.219099999999997, -12.308),
        (-72.2423, -58.368600000000001, -12.308),
        (-97.9602, -42.890500000000003, -12.308),
        (-102.215, -34.151899999999998, -12.308),
        (-102.97799999999999, -4.0906500000000001, -12.308),
        (-101.30500000000001, 30.645399999999999, -12.308),
        (-45.062100000000001, -21.008800000000001, -12.308),
        (-11.404299999999999, -29.081600000000002, -12.308),
        (2.33548, -7.7172200000000002, -12.308),
        (-8.6430000000000007, 33.989100000000001, -12.308),
        (-53.223999999999997, 18.129300000000001, -12.308),
        (-99.722499999999997, -8.1297999999999995, -12.308),
        (-100.45699999999999, 28.350999999999999, -12.308),
        (-76.794600000000003, 4.2119900000000001, -12.308),
        (-64.913700000000006, 37.576500000000003, -12.308),
        (-17.607500000000002, 102.13500000000001, -12.308),
        (-23.411200000000001, 127.777, -12.308),
        (-11.3513, 128.99100000000001, -12.308),
        (-14.1068, 83.204300000000003, -12.308),
        (53.268500000000003, 24.358499999999999, -12.308),
        (41.419699999999999, 4.3538399999999999, -12.308))


class DGTreasurePlanner(RegenTreasurePlanner):
    treasureClass = DistributedDGTreasureAI
    spawnInterval, maxTreasures, healAmount = 15, 2, 10

    spawnPoints = (
        (-49, 156, 0.0),
        (-59, 50, 0.0),
        (19, 16, 0.0),
        (76, 38, 1.1000000000000001),
        (102, 121, 0.0),
        (69, 123, 0.0),
        (49, 105, 0.0),
        (24, 156, 0.0),
        (-27, 127, 0.0),
        (-56, 105, 0.0),
        (-40, 113, 0.0),
        (25, 114, 0.0),
        (-6, 84, 0.0),
        (19, 96, 0.0),
        (0, 114, 0.0),
        (-78, 157, 10.0),
        (-33.399999999999999, 218.19999999999999, 10.0),
        (57, 205, 10.0),
        (32, 77, 0.0),
        (-102, 101, 0.0))


class MMTreasurePlanner(RegenTreasurePlanner):
    treasureClass = DistributedMMTreasureAI
    spawnInterval, maxTreasures, healAmount = 20, 2, 10

    spawnPoints = (
        (118, -39, 3.2999999999999998),
        (118, 1, 3.2999999999999998),
        (112, -22, 0.80000000000000004),
        (108, -74, -4.5),
        (110, -65, -4.5),
        (102, 23.5, -4.5),
        (60, -115, 6.5),
        (-5, -115, 6.5),
        (-64, -77, 6.5),
        (-77, -44, 6.5),
        (-76, 3, 6.5),
        (44, 76, 6.5),
        (136, -96, -13.5),
        (85, -6.7000000000000002, -13.5),
        (60, -95, -14.5),
        (72, 60, -13.5),
        (-55, -23, -14.5),
        (-21, 47, -14.5),
        (-24, -75, -14.5)
    )


class BRTreasurePlanner(RegenTreasurePlanner):
    treasureClass = DistributedBRTreasureAI
    spawnInterval, maxTreasures, healAmount = 20, 2, 12

    spawnPoints = (
        (-108, 46, 6.2000000000000002),
        (-111, 74, 6.2000000000000002),
        (-126, 81, 6.2000000000000002),
        (-74, -75, 3.0),
        (-136, -51, 3.0),
        (-20, 35, 6.2000000000000002),
        (-55, 109, 6.2000000000000002),
        (58, -57, 6.2000000000000002),
        (-42, -134, 6.2000000000000002),
        (-68, -148, 6.2000000000000002),
        (-1, -62, 6.2000000000000002),
        (25, 2, 6.2000000000000002),
        (-133, 53, 6.2000000000000002),
        (-99, 86, 6.2000000000000002),
        (30, 63, 6.2000000000000002),
        (-147, 3, 6.2000000000000002),
        (-135, -102, 6.2000000000000002),
        (35, -98, 6.2000000000000002)
    )


class DLTreasurePlanner(RegenTreasurePlanner):
    treasureClass = DistributedDLTreasureAI
    spawnInterval, maxTreasures, healAmount = 20, 2, 12

    spawnPoints = (
        (86, 69, -17.399999999999999),
        (34, -48, -16.399999999999999),
        (87, -70, -17.5),
        (-98, 99, 0.0),
        (51, 100, 0.0),
        (-45, -12, -15.0),
        (9, 8, -15.0),
        (-24, 64, -17.199999999999999),
        (-100, -99, 0.0),
        (21, -101, 0.0),
        (88, -17, -15.0),
        (32, 70, -17.399999999999999),
        (53, 35, -15.800000000000001),
        (2, -30, -15.5),
        (-40, -56, -16.800000000000001),
        (-28, 18, -15.0),
        (-34, -88, 0.0)
    )


class OZTreasurePlanner(RegenTreasurePlanner):
    treasureClass = DistributedOZTreasureAI
    spawnInterval, maxTreasures, healAmount = 20, 5, 3

    spawnPoints = (
        (-156.90000000000001, -118.90000000000001, 0.025000000000000001),
        (-35.600000000000001, 86.0, 1.25),
        (116.8, 10.800000000000001, 0.104),
        (-35, 145.69999999999999, 0.025000000000000001),
        (-198.80000000000001, -45.100000000000001, 0.025000000000000001),
        (-47.100000000000001, -25.5, 0.80900000000000005),
        (59.149999999999999, 34.799999999999997, 1.7669999999999999),
        (-81.019999999999996, -72.200000000000003, 0.025999999999999999),
        (-167.90000000000001, 124.5, 0.025000000000000001),
        (-226.69999999999999, -27.600000000000001, 0.025000000000000001),
        (-16.0, -108.90000000000001, 0.025000000000000001),
        (18.0, 58.5, 5.9189999999999996),
        (91.400000000000006, 127.8, 0.025000000000000001),
        (-86.5, -75.900000000000006, 0.025000000000000001),
        (-48.750999999999998, -32.299999999999997, 1.143)
    )


class TagTreasurePlanner(RegenTreasurePlanner):
    treasureClass = DistributedTagTreasureAI
    spawnInterval, maxTreasures, healAmount = 3, 4, 0

    spawnPoints = (
        (0, 0, 0.1),
        (5, 20, 0.1),
        (0, 40, 0.1),
        (-5, -20, 0.1),
        (0, -40, 0.1),
        (20, 0, 0.1),
        (40, 5, 0.1),
        (-20, -5, 0.1),
        (-40, 0, 0.1),
        (22, 20, 0.1),
        (-20, 22, 0.1),
        (20, -20, 0.1),
        (-25, -20, 0.1),
        (20, 40, 0.1),
        (20, -44, 0.1),
        (-24, 40, 0.1),
        (-20, -40, 0.1))
