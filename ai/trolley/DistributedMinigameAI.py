from ai.DistributedObjectAI import DistributedObjectAI
from direct.fsm.FSM import FSM

from ai.ToonBarrier import ToonBarrier

from typing import Optional, List, Dict
from enum import IntEnum


from . import PurchaseState, Purchaser, INVENTORY_PENDING, PurchaseManagerAI, incZoneRef, decZoneRef


class ParticipantState(IntEnum):
    EXITED = 0
    EXPECTED = 1
    JOINED = 2
    READY = 3


latencyTolerance = 10.0
MaxLoadTime = 40.0
rulesDuration = 16
JellybeanTrolleyHolidayScoreMultiplier = 2
DifficultyOverrideMult = int(1 << 16)
NoDifficultyOverride = 2147483647
NoTrolleyZoneOverride = -1

JOIN_TIMEOUT = 40.0 + latencyTolerance
READY_TIMEOUT = MaxLoadTime + rulesDuration + latencyTolerance
EXIT_TIMEOUT = 20.0 + latencyTolerance


class DistributedMinigameAI(DistributedObjectAI, FSM):
    MINIGAME_ID = None

    def __init__(self, air, participants, trolleyZone):
        DistributedObjectAI.__init__(self, air)
        FSM.__init__(self, self.__class__.__name__)

        self.participants: List[int] = participants
        # TODO
        self.newbies: List[int] = []
        self.trolleyZone: int = trolleyZone
        self.startingVotes: List[int] = [0 for _ in range(len(participants))]
        self.stateDict: Dict[int, ParticipantState] = {participant: ParticipantState.EXPECTED for participant in participants}
        self.scoreDict: Dict[int, int] = {}
        self.metagameRound = -1
        self.normalExit = True
        self.difficultyOverrides = NoDifficultyOverride, NoTrolleyZoneOverride

        self.__barrier: Optional[ToonBarrier] = None

        self.gameStartTime = 0.0

    def getParticipants(self):
        return self.participants

    def getTrolleyZone(self):
        return self.trolleyZone

    def getMetagameRound(self):
        return self.metagameRound

    def getDifficultyOverrides(self):
        return self.difficultyOverrides

    def getStartingVotes(self):
        return self.startingVotes

    def announceGenerate(self):
        incZoneRef(self.zoneId)
        self.demand('WaitForJoin')

    def enterWaitForJoin(self):
        for avId in self.participants:
            self.acceptOnce(self.air.getAvatarExitEvent(avId), self.handleExitedAvatar, extraArgs=[avId])

        self.__barrier = ToonBarrier(self.uniqueName('wait-join'), self.participants, JOIN_TIMEOUT, self.allJoined, self.timeout)

    def setAvatarJoined(self):
        print('set av join', self.state)
        if self.state != 'WaitForJoin':
            return

        avId = self.air.currentAvatarSender

        if avId not in self.participants:
            return

        self.stateDict[avId] = ParticipantState.JOINED
        self.__barrier.clear(avId)

    def allJoined(self, avIds):
        print('alljoined!', avIds)
        self.demand('WaitForReady')

    def exitWaitForJoin(self):
        self.__barrier.cleanup()
        self.__barrier = None

    def enterWaitForReady(self):
        self.__barrier = ToonBarrier(self.uniqueName('wait-ready'), self.participants, JOIN_TIMEOUT, self.allReady, self.timeout)
        self.sendUpdate('setGameReady', [])
        for avId, state in self.stateDict.items():
            if self.stateDict[avId] == ParticipantState.READY:
                self.__barrier.clear(avId)

    def allReady(self, avIds):
        print('allready', avIds)
        self.demand('GameBegin')

    def setAvatarReady(self):
        print('setavatarready', self.state)
        if self.state != 'WaitForJoin' and self.state != 'WaitForReady':
            return

        avId = self.air.currentAvatarSender

        if avId not in self.participants:
            return

        self.stateDict[avId] = ParticipantState.READY
        self.__barrier.clear(avId)

    def enterGameBegin(self):
        self.gameStartTime = globalClock.getRealTime()
        self.sendUpdate('setGameStart', [globalClockDelta.localToNetworkTime(self.gameStartTime)])
        self.onGameStart()

    def onGameStart(self):
        raise NotImplementedError

    def enterWaitForExit(self):
        self.__barrier = ToonBarrier(self.uniqueName('wait-exit'), self.participants, JOIN_TIMEOUT, self.allExited, self.timeout)
        self.sendUpdate('setGameExit', [])
        for avId, state in self.stateDict.items():
            if self.stateDict[avId] == ParticipantState.EXITED:
                self.__barrier.clear(avId)

    def setAvatarExited(self):
        if self.state != 'WaitForExit':
            return

        avId = self.air.currentAvatarSender

        self.stateDict[avId] = ParticipantState.EXITED
        self.__barrier.clear(avId)

    def allExited(self, avIds):
        self.demand('Cleanup')

    def handleExitedAvatar(self, avId):
        self.stateDict[avId] = ParticipantState.EXITED
        self.abort()

    def timeout(self):
        self.abort()

    def abort(self):
        self.normalExit = False
        self.sendUpdate('setGameAbort', [])
        self.demand('Cleanup')

    def enterCleanup(self):
        purchasers = []

        for participant in self.participants:
            av = self.air.doTable.get(participant)
            if not participant:
                purchasers.append(Purchaser(participant, state=PurchaseState.NO_CLIENT))
            elif av is None:
                purchasers.append(Purchaser(participant, state=PurchaseState.DISCONNECTED))
            else:
                state = PurchaseState.WAITING
                newbie = av in self.newbies
                if newbie:
                    state = PurchaseState.EXIT

                score = int(self.scoreDict.get(participant, 0) + 0.5)
                score = max(min(score, 255), 1)

                prevMoney = av.money
                av.addMoney(score)

                purchasers.append(Purchaser(participant, score, prevMoney, state=state, newbie=newbie,
                                            inventoryState=INVENTORY_PENDING))

        while len(purchasers) < 4:
            purchasers.append(Purchaser(avId=0, state=PurchaseState.NO_CLIENT))

        if len(self.participants) > len(self.newbies):
            pm = PurchaseManagerAI.PurchaseManagerAI(self.air, purchasers, self.MINIGAME_ID, self.trolleyZone, self.metagameRound)
            pm.generateWithRequired(self.zoneId)

        self.requestDelete()

    def delete(self):
        decZoneRef(self.zoneId)
        DistributedObjectAI.delete(self)
