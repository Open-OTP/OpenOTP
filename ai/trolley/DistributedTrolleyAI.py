from ai.DistributedObjectAI import DistributedObjectAI
from direct.fsm.FSM import FSM

from . import createMinigame


TROLLEY_ENTER_TIME = 2.0
TROLLEY_EXIT_TIME = 5.0
TROLLEY_COUNTDOWN_TIME = 10.0
TOON_BOARD_TIME = 1.0
TOON_EXIT_TIME = 1.0


class DistributedTrolleyAI(DistributedObjectAI, FSM):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        FSM.__init__(self, self.__class__.__name__)

        self.boardable = False
        self.seats = [0, 0, 0, 0]
        self.lastBoardTime: float = 0.0

    def getAvailableSeat(self):
        try:
            return self.seats.index(0)
        except ValueError:
            return None

    def getSeatIndex(self, avId):
        try:
            return self.seats.index(avId)
        except ValueError:
            return None

    @property
    def empty(self):
        return self.seats.count(0) == 4

    @property
    def full(self):
        return not self.seats.count(0)

    def announceGenerate(self):
        self.demand('Entering')

    def d_setState(self, state):
        self.sendUpdate('setState', [state, globalClockDelta.getRealNetworkTime()])

    def enterOff(self):
        self.boardable = False

        for i in range(4):
            taskMgr.remove(self.uniqueName(f'clearEmpty-{i}'))

    def enterEntering(self):
        self.d_setState('entering')
        self.seats = [0, 0, 0, 0]
        taskMgr.doMethodLater(TROLLEY_ENTER_TIME, lambda task: self.demand('WaitEmpty'),
                              self.uniqueName('entering-timer'))

    def enterWaitEmpty(self):
        self.boardable = True
        self.d_setState('waitEmpty')

    def exitWaitEmpty(self):
        self.boardable = False

    def enterWaitCountdown(self):
        self.boardable = True
        self.d_setState('waitCountdown')
        taskMgr.doMethodLater(TROLLEY_COUNTDOWN_TIME, self.postCountdown, self.uniqueName('countdown-timer'))

    def postCountdown(self, task):
        if self.empty:
            self.demand('WaitEmpty')
        else:
            self.demand('AllAboard')
        return task.done

    def exitWaitCountdown(self):
        self.boardable = False
        taskMgr.remove(self.uniqueName('countdown-timer'))

    def enterAllAboard(self):
        self.boardable = False
        elapsedTime = globalClock.getRealTime() - self.lastBoardTime
        waitTime = max(TOON_BOARD_TIME - elapsedTime, 0)
        taskMgr.doMethodLater(waitTime, self.leave, self.uniqueName('waitForAllAboard'))

    def leave(self, task):
        print('leave', self.seats, self.empty)
        if self.empty:
            self.demand('WaitEmpty')
        else:
            self.demand('Leaving')

    def exitAllAboard(self):
        taskMgr.remove(self.uniqueName('waitForAllAboard'))

    def enterLeaving(self):
        self.d_setState('leaving')
        self.boardable = False
        taskMgr.doMethodLater(TROLLEY_EXIT_TIME, self.trolleyLeft, self.uniqueName('leaving-timer'))

    def trolleyLeft(self, task):
        players = [avId for avId in self.seats if avId]
        print('trolleyLeft', players)

        if players:
            minigameZone, minigameId = createMinigame(self.air, players, [], self.zoneId)

            for player in players:
                self.sendUpdateToAvatar(player, 'setMinigameZone', [minigameZone, minigameId])
                self.clearFillSlot(self.seats.index(player))

        self.demand('Entering')

    def exitLeaving(self):
        taskMgr.remove(self.uniqueName('leaving-timer'))

    def fillSeat(self, avId):
        seatIndex = self.getAvailableSeat()
        self.seats[seatIndex] = avId
        self.acceptOnce(self.air.getAvatarExitEvent(avId), self.__handleUnexpectedExit, extraArgs=[avId])
        self.lastBoardTime = globalClock.getRealTime()
        self.sendUpdate(f'fillSlot{seatIndex}', [avId])

    def clearFillSlot(self, index):
        avId = self.seats[index]

        if not avId:
            return

        self.sendUpdate(f'fillSlot{index}', [0])
        self.ignore(self.air.getAvatarExitEvent(avId))

    def clearEmptySlot(self, index):
        self.sendUpdate(f'emptySlot{index}', [0, globalClockDelta.getRealNetworkTime()])

    def __handleUnexpectedExit(self, avId):
        seatIndex = self.getSeatIndex(avId)

        if seatIndex is None:
            return

        self.clearFillSlot(seatIndex)
        self.clearEmptySlot(seatIndex)

        if self.empty and self.state != 'Leaving':
            self.demand('WaitEmpty')

    def requestBoard(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)
        if not av:
            return

        if av.hp <= 0 or self.full or not self.boardable:
            self.sendUpdateToAvatar(avId, 'rejectBoard', [avId])
            return

        # TODO
        # if not ToontownAccessAI.canAccess(avId, self.zoneId, 'DistributedTrolleyAI.requestBoard'):

        self.fillSeat(avId)

        if self.state == 'WaitEmpty':
            self.demand('WaitCountdown')

    def requestExit(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)
        if not av or not self.boardable:
            return

        seatIndex = self.getSeatIndex(avId)

        if seatIndex is None:
            return

        self.sendUpdate(f'emptySlot{seatIndex}', [avId, globalClockDelta.getRealNetworkTime()])
        taskMgr.doMethodLater(TOON_EXIT_TIME, lambda task: self.clearEmptySlot(seatIndex),
                              self.uniqueName(f'clearEmpty-{seatIndex}'))

        if self.empty:
            self.demand('WaitEmpty')
