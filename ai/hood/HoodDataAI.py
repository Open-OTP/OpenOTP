from ai.ToontownGlobals import *
from typing import List, Dict, Union
from ai.DistributedObjectAI import DistributedObjectAI
from dna.dnaparser import load_dna_file, DNAStorage
from dna.objects import DNAGroup
from ai.toon import NPCToons

DNA_MAP = {
    DonaldsDock: 'donalds_dock_sz.dna',
    BarnacleBoulevard: 'donalds_dock_1100.dna',
    SeaweedStreet: 'donalds_dock_1200.dna',
    LighthouseLane: 'donalds_dock_1300.dna',
    ToontownCentral: 'toontown_central_sz.dna',
    SillyStreet: 'toontown_central_2100.dna',
    LoopyLane: 'toontown_central_2200.dna',
    PunchlinePlace: 'toontown_central_2300.dna',
    TheBrrrgh: 'the_burrrgh_sz.dna',
    WalrusWay: 'the_burrrgh_3100.dna',
    SleetStreet: 'the_burrrgh_3200.dna',
    PolarPlace: 'the_burrrgh_3300.dna',
    MinniesMelodyland: 'minnies_melody_land_sz.dna',
    AltoAvenue: 'minnies_melody_land_4100.dna',
    BaritoneBoulevard: 'minnies_melody_land_4200.dna',
    TenorTerrace: 'minnies_melody_land_4300.dna',
}


class PlaceAI:
    def __init__(self, air, zone_id):
        self.air = air
        self.zone_id: int = zone_id

        self._active = False
        # self.doTable: Dict[int, DistributedObjectAI] = {}
        self.storage: Union[DNAStorage, None] = None
        self.dna: Union[DNAGroup, None] = None

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, active: bool):
        if self._active == active:
            return

        self._active = active

        if active:
            self.create()
        else:
            self.cleanup()

    def create(self):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError


from ai.building.DistributedHQInteriorAI import DistributedHQInteriorAI
from ai.building.DistributedDoorAI import DistributedDoorAI
from ai.building import DoorTypes


class HQBuildingAI(object):
    __slots__ = 'interior', 'door0', 'door1', 'insideDoor0', 'insideDoor1', 'npcs'

    def __init__(self, air, exteriorZone, interiorZone, block):
        self.interior = DistributedHQInteriorAI(block, air, interiorZone)
        self.interior.generateWithRequired(interiorZone)
        
        door0 = DistributedDoorAI(air, block, DoorTypes.EXT_HQ, doorIndex=0)
        door0.zoneId = exteriorZone
        
        door1 = DistributedDoorAI(air, block, DoorTypes.EXT_HQ, doorIndex=1)
        door1.zoneId = exteriorZone

        insideDoor0 = DistributedDoorAI(air, block, DoorTypes.INT_HQ, doorIndex=0)
        insideDoor0.zoneId = interiorZone
        
        insideDoor1 = DistributedDoorAI(air, block, DoorTypes.INT_HQ, doorIndex=1)
        insideDoor1.zoneId = interiorZone

        door0.setOtherDoor(insideDoor0)
        door1.setOtherDoor(insideDoor1)
        insideDoor0.setOtherDoor(door0)
        insideDoor1.setOtherDoor(door1)

        door0.generateWithRequired(exteriorZone)
        door1.generateWithRequired(exteriorZone)
        insideDoor0.generateWithRequired(interiorZone)
        insideDoor1.generateWithRequired(interiorZone)
        
        self.door0 = door0
        self.door1 = door1
        self.insideDoor0 = insideDoor0
        self.insideDoor1 = insideDoor1

        # TODO
        self.npcs = NPCToons.createNpcsInZone(air, interiorZone)

    def delete(self):
        for npc in self.npcs:
            npc.requestDelete()
        self.door0.requestDelete()
        self.door1.requestDelete()
        self.insideDoor0.requestDelete()
        self.insideDoor1.requestDelete()
        self.interior.requestDelete()


class GagshopBuildingAI(object):
    __slots__ = 'interior', 'door', 'insideDoor', 'npcs'

    def __init__(self, air, exteriorZone, interiorZone, block):
        self.interior = DistributedGagshopInteriorAI(air, block, interiorZone)
        self.interior.generateWithRequired(interiorZone)

        door = DistributedDoorAI(air, block, DoorTypes.EXT_STANDARD)
        door.zoneId = exteriorZone

        insideDoor = DistributedDoorAI(air, block, DoorTypes.INT_STANDARD)
        insideDoor.zoneId = interiorZone

        door.setOtherDoor(insideDoor)
        insideDoor.setOtherDoor(door)

        door.generateWithRequired(exteriorZone)
        insideDoor.generateWithRequired(interiorZone)
        self.door = door
        self.insideDoor = insideDoor

        self.npcs = NPCToons.createNpcsInZone(air, interiorZone)

    def cleanup(self):
        for npc in self.npcs:
            npc.requestDelete()

        self.door.requestDelete()
        self.insideDoor.requestDelete()
        self.interior.requestDelete()


class DistributedGagshopInteriorAI(DistributedObjectAI):
    def __init__(self, air, block, zoneId):
        DistributedObjectAI.__init__(self, air)
        self.block = block
        self.zoneId = zoneId

    def getZoneIdAndBlock(self):
        r = [self.zoneId, self.block]
        return r


from ai.building.DistributedBuildingAI import DistributedBuildingAI


class SafeZoneAI(PlaceAI):
    def __init__(self, air, zone_id):
        PlaceAI.__init__(self, air, zone_id)
        self.buildings: Dict[int, object] = {}
        self.hq: Union[HQBuildingAI, None] = None
        self.gagShop: Union[GagshopBuildingAI, None] = None

    @staticmethod
    def getInteriorZone(zoneId, block):
        return zoneId - zoneId % 100 + 500 + block

    def create(self):
        self.dna, self.storage = load_dna_file('dna/' + DNA_MAP[self.zone_id])

        for block in self.storage.blocks:
            building_type = self.storage.block_building_types[block]
            interiorZone = self.getInteriorZone(self.zone_id, block)
            exteriorZone = self.storage.block_zones.get(block, self.zone_id)

            if building_type == 'hq':
                self.buildings[block] = HQBuildingAI(self.air, exteriorZone, interiorZone, block)
            elif building_type == 'gagshop':
                self.buildings[block] = GagshopBuildingAI(self.air, exteriorZone, interiorZone, block)
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
                bldg = DistributedBuildingAI(self.air)
                bldg.block = block
                bldg.exteriorZoneId = exteriorZone
                bldg.interiorZoneId = self.getInteriorZone(exteriorZone, block)
                bldg.generateWithRequired(self.zone_id)
                bldg.request('Toon')
                self.buildings[block] = bldg

        for visgroup in self.storage.visgroups:
            zone = int(visgroup.name.split(':')[0])

            self.air.vismap[zone] = tuple(visgroup.visibles)


class StreetAI(SafeZoneAI):
    def __init__(self, air, zone_id):
        SafeZoneAI.__init__(self, air, zone_id)

    def create(self):
        super().create()

        # TODO: suits


class PlaygroundAI(SafeZoneAI):
    def __init__(self, air, zone_id):
        SafeZoneAI.__init__(self, air, zone_id)
        self.npcs = []

    def create(self):
        super().create()

        self.npcs = NPCToons.createNpcsInZone(self.air, self.zone_id)
        # TODO: trolley, butterflys, disney npc


class HoodAI:
    zoneId = None

    def __init__(self, air):
        self.playground = PlaygroundAI(air, self.zoneId)
        self.streets: List[StreetAI] = [StreetAI(air, branchId) for branchId in HoodHierarchy[self.zoneId]]

    def startup(self):
        self.playground.active = True
        for street in self.streets:
            street.active = True

    def shutdown(self):
        self.playground.active = False
        for street in self.streets:
            street.active = False


class DDHoodAI(HoodAI):
    zoneId = DonaldsDock


class TTHoodAI(HoodAI):
    zoneId = ToontownCentral


class BRHoodAI(HoodAI):
    zoneId = TheBrrrgh


class MMHoodAI(HoodAI):
    zoneId = MinniesMelodyland
