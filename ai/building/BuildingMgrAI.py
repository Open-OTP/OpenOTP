from dna.dnaparser import DNAStorage

from ai.DistributedObjectAI import DistributedObjectAI
from .DistributedBuildingAI import DistributedBuildingAI


class BuildingMgrAI:
    def __init__(self, air, branch_id: int):
        self.air = air
        self.branch_id = branch_id
        self.buildings = {}
        self.startup()
        print(self.buildings)

    def startup(self):
        dna_store = self.dna_storage

        for block in dna_store.blocks:
            building_type = dna_store.block_building_types[block]

            if building_type == 'hq':
                self.new_hq_building(block)
            elif building_type == 'gagshop':
                self.new_gagshop_building(block)
            elif building_type == 'petshop':
                # TODO
                pass
            elif building_type == 'kartshop':
                # TODO
                pass
            elif building_type == 'animbldg':
                # TODO
                pass
            else:
                self.new_building(block)

    def new_building(self, block):
        exterior_zone = self.dna_storage.block_zones[block]
        bldg = DistributedBuildingAI(self.air)
        bldg.block = block
        bldg.exteriorZoneId = exterior_zone
        bldg.interiorZoneId = (exterior_zone - exterior_zone % 100) + 500 + block
        bldg.generate_with_required(self.branch_id)
        bldg.request('Toon')
        self.buildings[block] = bldg

    def new_hq_building(self, block):
        interiorZoneId = self.branch_id - self.branch_id % 100 + 500 + block

        bldg = HQBuildingAI(self.air, self.branch_id, interiorZoneId, block)
        self.buildings[block] = bldg

    def new_gagshop_building(self, block):
        interiorZoneId = self.branch_id - self.branch_id % 100 + 500 + block

        bldg = GagshopBuildingAI(self.air, self.branch_id, interiorZoneId, block)
        self.buildings[block] = bldg

    @property
    def dna_storage(self) -> DNAStorage:
        return self.air.dna_storage[self.branch_id]


from .DistributedDoorAI import DistributedDoorAI
from . import DoorTypes


class HQBuildingAI:
    def __init__(self, air, exteriorZone, interiorZone, blockNumber):
        self.air = air
        self.exteriorZone = exteriorZone
        self.interiorZone = interiorZone
        self.setup(blockNumber)

    def cleanup(self):
        for npc in self.npcs:
            npc.requestDelete()

        del self.npcs
        self.door0.requestDelete()
        del self.door0
        self.door1.requestDelete()
        del self.door1
        self.insideDoor0.requestDelete()
        del self.insideDoor0
        self.insideDoor1.requestDelete()
        del self.insideDoor1
        # self.interior.requestDelete()
        # del self.interior

    def setup(self, blockNumber):
        # self.interior = DistributedHQInteriorAI(blockNumber, self.air, self.interiorZone)
        # self.npcs = NPCToons.createNpcsInZone(self.air, self.interiorZone)
        self.npcs = []
        # self.interior.generateWithRequired(self.interiorZone)
        door0 = DistributedDoorAI(self.air, blockNumber, DoorTypes.EXT_HQ, doorIndex=0)
        door1 = DistributedDoorAI(self.air, blockNumber, DoorTypes.EXT_HQ, doorIndex=1)
        insideDoor0 = DistributedDoorAI(self.air, blockNumber, DoorTypes.INT_HQ, doorIndex=0)
        insideDoor1 = DistributedDoorAI(self.air, blockNumber, DoorTypes.INT_HQ, doorIndex=1)
        door0.setOtherDoor(insideDoor0)
        insideDoor0.setOtherDoor(door0)
        door1.setOtherDoor(insideDoor1)
        insideDoor1.setOtherDoor(door1)
        door0.zoneId = self.exteriorZone
        door1.zoneId = self.exteriorZone
        insideDoor0.zoneId = self.interiorZone
        insideDoor1.zoneId = self.interiorZone
        door0.generate_with_required(self.exteriorZone)
        door1.generate_with_required(self.exteriorZone)
        insideDoor0.generate_with_required(self.interiorZone)
        insideDoor1.generate_with_required(self.interiorZone)
        self.door0 = door0
        self.door1 = door1
        self.insideDoor0 = insideDoor0
        self.insideDoor1 = insideDoor1


class GagshopBuildingAI:

    def __init__(self, air, exteriorZone, interiorZone, blockNumber):
        self.air = air
        self.exteriorZone = exteriorZone
        self.interiorZone = interiorZone
        self.setup(blockNumber)

    def cleanup(self):
        for npc in self.npcs:
            npc.requestDelete()

        del self.npcs
        self.door.requestDelete()
        del self.door
        self.insideDoor.requestDelete()
        del self.insideDoor
        self.interior.requestDelete()
        del self.interior

    def setup(self, blockNumber):
        self.interior = DistributedGagshopInteriorAI(self.air, blockNumber, self.interiorZone)
        # self.npcs = NPCToons.createNpcsInZone(self.air, self.interiorZone)
        self.npcs = []
        self.interior.generate_with_required(self.interiorZone)
        door = DistributedDoorAI(self.air, blockNumber, DoorTypes.EXT_STANDARD)
        insideDoor = DistributedDoorAI(self.air, blockNumber, DoorTypes.INT_STANDARD)
        door.setOtherDoor(insideDoor)
        insideDoor.setOtherDoor(door)
        door.zoneId = self.exteriorZone
        insideDoor.zoneId = self.interiorZone
        door.generate_with_required(self.exteriorZone)
        insideDoor.generate_with_required(self.interiorZone)
        self.door = door
        self.insideDoor = insideDoor


class DistributedGagshopInteriorAI(DistributedObjectAI):
    def __init__(self, air, block, zoneId):
        DistributedObjectAI.__init__(self, air)
        self.block = block
        self.zoneId = zoneId

    def getZoneIdAndBlock(self):
        r = [self.zoneId, self.block]
        return r
