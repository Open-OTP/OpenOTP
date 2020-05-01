from ai.ToontownGlobals import *
from typing import Dict
from ai.DistributedObjectAI import DistributedObjectAI


class HoodDataAI:
    def __init__(self, air, zone_id, hood_id):
        self.air = air
        self.zone_id = zone_id
        self.hood_id = hood_id

        self._active = False
        self.do_table: Dict[int, DistributedObjectAI] = {}

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        if self._active == active:
            return

        self._active = active

        if active:
            self.create_objects()
        else:
            self.cleanup()

    def create_objects(self):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError


from ai.building import BuildingMgrAI


class TTHoodDataAI(HoodDataAI):
    def __init__(self, air):
        super().__init__(air, ToontownCentral, ToontownCentral)

        self.bldgMgr = None

    def create_objects(self):
        root, storage = self.air.load_dna_file('dna/toontown_central_sz.dna')
        self.air.dna_storage[self.hood_id] = storage
        self.air.dna_map[self.hood_id] = root
        self.bldgMgr = BuildingMgrAI.BuildingMgrAI(self.air, self.hood_id)

    def cleanup(self):
        pass
