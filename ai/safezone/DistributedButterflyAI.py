from ai.DistributedObjectAI import DistributedObjectAI
from ai.safezone import ButterflyGlobals

from direct.fsm.FSM import FSM

import random


class DistributedButterflyAI(DistributedObjectAI, FSM):
    defaultTransitions = {
        'Off': ['Flying', 'Landed'],
        'Flying': ['Landed'],
        'Landed': ['Flying']
    }

    def __init__(self, air, playground, area, ownerId):
        DistributedObjectAI.__init__(self, air)
        FSM.__init__(self, 'DistributedButterflyAI')
        self.playground = playground
        self.area = area
        self.ownerId = ownerId
        self.stateIndex = ButterflyGlobals.OFF
        self.curPos, self.curIndex, self.destPos, self.destIndex, self.time = ButterflyGlobals.getFirstRoute(self.playground, self.area, self.ownerId)

    def delete(self):
        ButterflyGlobals.recycleIndex(self.curIndex, self.playground, self.area, self.ownerId)
        ButterflyGlobals.recycleIndex(self.destIndex, self.playground, self.area, self.ownerId)
        self.request('Off')
        DistributedObjectAI.delete(self)

    def getArea(self):
        return self.playground, self.area

    def getState(self):
        return self.stateIndex, self.curIndex, self.destIndex, self.time, globalClockDelta.getRealNetworkTime()

    def start(self):
        self.request('Flying')

    def avatarEnter(self):
        if self.state == 'Landed':
            self.__ready()

    def enterOff(self):
        self.stateIndex = ButterflyGlobals.OFF

    def exitOff(self):
        pass

    def enterFlying(self):
        self.stateIndex = ButterflyGlobals.FLYING
        ButterflyGlobals.recycleIndex(self.curIndex, self.playground, self.area, self.ownerId)
        self.sendUpdate('setState', self.getState())
        taskMgr.doMethodLater(self.time, self.__handleArrival, self.uniqueName('butter-flying'))

    def exitFlying(self):
        taskMgr.remove(self.uniqueName('butter-flying'))

    def __handleArrival(self, task):
        self.curPos = self.destPos
        self.curIndex = self.destIndex
        self.request('Landed')
        return task.done

    def enterLanded(self):
        self.stateIndex = ButterflyGlobals.LANDED
        self.time = random.random() * ButterflyGlobals.MAX_LANDED_TIME
        self.sendUpdate('setState', self.getState())
        taskMgr.doMethodLater(self.time, self.__ready, self.uniqueName('butter-ready'))

    def exitLanded(self):
        taskMgr.remove(self.uniqueName('butter-ready'))

    def __ready(self, task=None):
        self.destPos, self.destIndex, self.time = ButterflyGlobals.getNextPos(self.curPos, self.playground, self.area, self.ownerId)
        self.request('Flying')
        if task:
            return task.done
