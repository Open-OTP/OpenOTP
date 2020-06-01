from .DistributedMinigameAI import DistributedMinigameAI

from . import TagGameId

import random

from ai.hood.Treasures import TagTreasurePlanner
from typing import Optional


class DistributedTagGameAI(DistributedMinigameAI):
    MINIGAME_ID = TagGameId
    DURATION = 60
    TAG_COOLDOWN = 2

    def __init__(self, air, participants, trolleyZone):
        DistributedMinigameAI.__init__(self, air, participants, trolleyZone)

        self.it: int = 0
        self.canTag: bool = True
        self.treasurePlanner: Optional[TagTreasurePlanner] = None

    def b_setIt(self, avId):
        self.it = avId
        self.sendUpdate('setIt', [avId])

    def onGameStart(self):
        self.b_setIt(random.choice(self.participants))
        taskMgr.doMethodLater(self.DURATION, self.timesUp, self.uniqueName('timer'))

        self.treasurePlanner = TagTreasurePlanner(self.zoneId, callback=self.treasureGrabCallback)
        for i in range(4):
            self.treasurePlanner.placeRandomTreasure()
        self.treasurePlanner.start()

    def treasureGrabCallback(self, avId):
        if avId not in self.participants:
            return

        if avId == self.it:
            return

        if avId in self.scoreDict:
            self.scoreDict[avId] += 2
        else:
            self.scoreDict[avId] = 2

        self.d_setTreasureScore()

    def d_setTreasureScore(self):
        self.sendUpdate('setTreasureScore', [(self.scoreDict.get(avId, 0) for avId in self.participants),])

    def exitGameBegin(self):
        taskMgr.remove(self.uniqueName('timer'))
        taskMgr.remove(self.uniqueName('tag-cooldown'))
        self.treasurePlanner.stop()
        self.treasurePlanner.deleteAllTreasures()
        self.treasurePlanner = None

    def timesUp(self, task):
        self.demand('Cleanup')

    def tag(self, taggedId):
        senderId = self.air.currentAvatarSender

        sender = self.air.doTable[senderId]
        if not sender:
            return

        if not self.canTag:
            return

        if self.it == senderId:
            self.b_setIt(taggedId)

        self.canTag = False
        taskMgr.doMethodLater(self.TAG_COOLDOWN, self.enableTag, self.uniqueName('tag-cooldown'))

    def enableTag(self, task):
        self.canTag = True
        return task.done
