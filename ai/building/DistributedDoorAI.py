from direct.fsm.FSM import FSM

INWARD_SWING = 0
OUTWARD_SWING = 1

LEFT_DOOR = 1 << 0
RIGHT_DOOR = 1 << 1


DEFAULT_SWING = (OUTWARD_SWING | LEFT_DOOR) | (INWARD_SWING | RIGHT_DOOR)


from ai.DistributedObjectAI import DistributedObjectAI
from direct.distributed.ClockDelta import globalClockDelta


UNLOCKED = 0
TALK_TO_TOM = 1
DEFEAT_FLUNKY_HQ = 2
TALK_TO_HQ = 3
WRONG_DOOR_HQ = 4
GO_TO_PLAYGROUND = 5
DEFEAT_FLUNKY_TOM = 6
TALK_TO_HQ_TOM = 7
SUIT_APPROACHING = 8
BUILDING_TAKEOVER = 9
SB_DISGUISE_INCOMPLETE = 10
CB_DISGUISE_INCOMPLETE = 11
LB_DISGUISE_INCOMPLETE = 12
BB_DISGUISE_INCOMPLETE = 13


class DistributedDoorAI(DistributedObjectAI):
    def __init__(self, air, block, doorType, doorIndex=0, swing=DEFAULT_SWING):
        DistributedObjectAI.__init__(self, air)

        self.block = block
        self.doorType = doorType
        self.doorIndex = doorIndex
        self.swing = swing
        self.doorLock = UNLOCKED

        self.otherDoor = None

        self.doorFSM = DoorFSM(self.air, self, field='setState')
        self.exitDoorFSM = DoorFSM(self.air, self, field='setExitDoorState')

    def setZoneIdAndBlock(self, zoneId, block):
        self.zoneId = zoneId
        self.block = block

    def getZoneIdAndBlock(self):
        return [self.zoneId, self.block]

    def setState(self, state, ts=0):
        self.doorFSM.request(state)

    def getState(self):
        return [self.doorFSM.state.lower(), globalClockDelta.getRealNetworkTime()]

    def setExitDoorState(self, state, ts=0):
        self.exitDoorFSM.request(state)

    def getExitDoorState(self):
        return [self.exitDoorFSM.state.lower(), globalClockDelta.getRealNetworkTime()]

    def getDoorType(self):
        return self.doorType

    def getDoorIndex(self):
        return self.doorIndex

    def getSwing(self):
        return self.swing

    def setDoorLock(self, lock):
        self.doorLock = lock

    def setOtherDoor(self, door):
        self.otherDoor = door

    def generate(self):
        DistributedObjectAI.generate(self)
        self.doorFSM.task = self.uniqueName('door-task')
        self.exitDoorFSM.task = self.uniqueName('exit-door-task')

    def requestEnter(self):
        avId = self.air.current_av_sender

        if self.doorLock:
            self.send_update_to_avatar(avId, 'rejectEnter', [self.doorLock])
            return

        self.handleEnter(avId)

    def handleEnter(self, avId):
        if avId not in self.doorFSM.queue:
            self.doorFSM.queue.append(avId)
            self.send_update('avatarEnter', [avId])

        self.doorFSM.openDoor()

        self.send_update_to_avatar(avId, 'setOtherZoneIdAndDoId', [self.otherDoor.zoneId, self.otherDoor.do_id])

    def requestExit(self):
        avId = self.air.current_av_sender
        self.send_update('avatarExit', [avId])

        self.handleExit(avId)

    def handleExit(self, avId):
        if avId in self.doorFSM.queue:
            self.doorFSM.queue.remove(avId)
        elif avId not in self.exitDoorFSM.queue:
            self.exitDoorFSM.queue.append(avId)
            self.exitDoorFSM.openDoor()

    def delete(self):
        self.doorFSM.demand('Off')
        self.exitDoorFSM.demand('Off')

        del self.block
        del self.swing
        del self.doorType
        del self.doorIndex
        del self.doorLock

        del self.doorFSM
        del self.exitDoorFSM

        del self.otherDoor

        DistributedObjectAI.delete(self)

    def d_suitEnter(self, suitId):
        if suitId not in self.doorFSM.queue:
            self.doorFSM.queue.append(suitId)
            self.send_update('suitEnter', [suitId])

        self.doorFSM.openDoor()


class DoorFSM(FSM):
    ANIMATION_DURATION = 1.0
    CLOSING_DURATION = 2.0

    def __init__(self, air, door, field):
        FSM.__init__(self, self.__class__.__name__)
        self.air = air
        self.door = door
        self.field = field
        self.task = None
        self.defaultTransitions = {
            'Off': ['Closing', 'Closed', 'Opening', 'Open'],
            'Closing': ['Closed', 'Opening'],
            'Closed': ['Opening'],
            'Opening': ['Open'],
            'Open': ['Closing', 'Open']
        }

        self.queue = []

    def enterOff(self):
        if self.task:
            taskMgr.remove(self.task)
        del self.queue[:]

    def enterOpening(self):
        self.d_setState('Opening')
        taskMgr.doMethodLater(self.ANIMATION_DURATION, self.doneOpening, self.task)

    def doneOpening(self, task):
        self.request('Open')
        return task.done

    def exitOpening(self):
        self.cleanupTask()

    def enterOpen(self):
        self.d_setState('Open')
        del self.queue[:]
        taskMgr.doMethodLater(self.ANIMATION_DURATION, self.doneOpen, self.task)

    def doneOpen(self, task):
        self.request('Closing')
        return task.done

    def exitOpen(self):
        self.cleanupTask()

    def enterClosing(self):
        self.d_setState('Closing')
        taskMgr.doMethodLater(self.CLOSING_DURATION, self.doneClosing, self.task)

    def doneClosing(self, task):
        self.request('Closed')
        return task.done

    def exitClosing(self):
        self.cleanupTask()

    def enterClosed(self):
        self.d_setState('Closed')

    def exitClosed(self):
        pass

    def openDoor(self):
        if self.state == 'Open':
            self.request('Open')
        elif self.state != 'Opening':
            self.request('Opening')

    def isOpen(self):
        return self.state in ('Open', 'Opening')

    def isClosed(self):
        return not self.isOpen()

    def cleanupTask(self):
        if self.task:
            taskMgr.remove(self.task)

    def d_setState(self, state):
        self.door.sendUpdate(self.field, [state.lower(), globalClockDelta.getRealNetworkTime()])

