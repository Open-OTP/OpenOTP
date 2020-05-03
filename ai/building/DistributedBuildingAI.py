from ai.DistributedObjectAI import DistributedObjectAI
from direct.distributed.ClockDelta import globalClockDelta

from .DistributedToonInteriorAI import DistributedToonInteriorAI
from .DistributedDoorAI import DistributedDoorAI


from direct.fsm.FSM import FSM

from . import DoorTypes


class DistributedBuildingAI(DistributedObjectAI, FSM):
    defaultTransitions = {
            'Off': ['WaitForVictors', 'BecomingToon', 'Toon', 'ClearOutToonInterior', 'BecomingSuit', 'Suit'],
            'WaitForVictors': ['BecomingToon'],
            'BecomingToon': ['Toon', ],
            'Toon': ['ClearOutToonInterior'],
            'ClearOutToonInterior': ['BecomingSuit'],
            'BecomingSuit': ['Suit'],
            'Suit': ['WaitForVictors', 'BecomingToon'],
    }

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        FSM.__init__(self, 'DistributedBuildingAI')

        self.block = 0
        self.track = 'c'
        self.difficulty = 1
        self.numFloors = 1
        self.interiorZoneId = 0
        self.exteriorZoneId = 0

        self.door = None
        self.insideDoor = None
        self.interior = None

    def getBlock(self):
        return [self.block, self.interiorZoneId]

    def getSuitData(self):
        return ord(self.track), self.difficulty, self.numFloors

    def d_setState(self, state):
        state = state[0].lower() + state[1:]
        self.sendUpdate('setState', [state, globalClockDelta.getRealNetworkTime()])

    def getState(self):
        state = self.state[0].lower() + self.state[1:]
        return [state, globalClockDelta.getRealNetworkTime()]

    def enterToon(self):
        self.d_setState('toon')

        # if simbase.config.GetBool('want-new-toonhall', 1) and ZoneUtil.getCanonicalZoneId(interiorZoneId) == ToonHall:
        #     self.interior = DistributedToonHallInteriorAI.DistributedToonHallInteriorAI(self.block, self.air,
        #                                                                                 interiorZoneId, self)
        # else:
        self.interior = DistributedToonInteriorAI(self.air)
        self.interior.block = self.block
        self.interior.zoneId = self.interiorZoneId
        self.interior.generateWithRequired(self.interiorZoneId)

        door = DistributedDoorAI(self.air, self.block, DoorTypes.EXT_STANDARD)
        door.zoneId = self.exteriorZoneId

        insideDoor = DistributedDoorAI(self.air, self.block, DoorTypes.INT_STANDARD)
        insideDoor.zoneId = self.interiorZoneId

        door.setOtherDoor(insideDoor)
        insideDoor.setOtherDoor(door)

        door.generateWithRequired(self.exteriorZoneId)
        insideDoor.generateWithRequired(self.interiorZoneId)

        self.door = door
        self.insideDoor = insideDoor

        # self.becameSuitTime = 0
        # self.knockKnock = DistributedKnockKnockDoorAI.DistributedKnockKnockDoorAI(self.air, self.block)
        # self.knockKnock.generateWithRequired(exteriorZoneId)
        # self.air.writeServerEvent('building-toon', self.doId, '%s|%s' % (self.zoneId, self.block))
