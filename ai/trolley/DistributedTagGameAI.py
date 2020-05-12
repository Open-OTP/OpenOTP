from .DistributedMinigameAI import DistributedMinigameAI

from . import TagGameId

import random


class DistributedTagGameAI(DistributedMinigameAI):
    MINIGAME_ID = TagGameId
    DURATION = 10
    TAG_COOLDOWN = 2

    def __init__(self, air, participants, trolleyZone):
        DistributedMinigameAI.__init__(self, air, participants, trolleyZone)

        self.it = 0
        self.canTag = True

    def b_setIt(self, avId):
        self.it = avId
        self.sendUpdate('setIt', [avId])

    def onGameStart(self):
        self.b_setIt(random.choice(self.participants))
        taskMgr.doMethodLater(self.DURATION, self.timesUp, self.uniqueName('timer'))

    def exitGameBegin(self):
        taskMgr.remove(self.uniqueName('timer'))
        taskMgr.remove(self.uniqueName('tag-cooldown'))

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
