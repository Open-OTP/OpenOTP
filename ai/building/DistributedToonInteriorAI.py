from ai.DistributedObjectAI import DistributedObjectAI


from direct.distributed.ClockDelta import globalClockDelta
from direct.fsm.FSM import FSM

import pickle


class DistributedToonInteriorAI(DistributedObjectAI, FSM):
    defaultTransitions = {
            'Toon': ['BeingTakenOver'],
            'BeingTakenOver': [],
            'Off': [],
        }

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        FSM.__init__(self, self.__class__.__name__)

        self.block = 0
        self.zoneId = 0

        #self.npcs = NPCToons.createNpcsInZone(self.air, self.zoneId)
        self.npcs = []

        self.demand('Toon')

    def delete(self):
        self.ignoreAll()
        for npc in self.npcs:
            npc.requestDelete()

        DistributedObjectAI.delete(self)

    def getZoneIdAndBlock(self):
        return [self.zoneId, self.block]

    def getToonData(self):
        return pickle.dumps({}, protocol=1)

    def getState(self):
        state = self.state[0].lower() + self.state[1:]
        return [state, globalClockDelta.getRealNetworkTime()]

    def d_setState(self, state):
        state = self.state[0].lower() + self.state[1:]
        self.sendUpdate('setState', [state, globalClockDelta.getRealNetworkTime()])

    def b_setState(self, state):
        self.request(state)
        self.d_setState(state)

    def enterOff(self):
        pass

    def exitOff(self):
        pass

    def enterToon(self):
        pass

    def exitToon(self):
        pass

    def enterBeingTakenOver(self):
        pass

    def exitBeingTakenOver(self):
        pass
