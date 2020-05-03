from ai.DistributedObjectAI import DistributedObjectAI


import pickle

from dataclasses import dataclass
from dataslots import with_slots
from typing import List



@with_slots
@dataclass
class ToonPlatoonEntry:
    avId: int
    name: str
    score: int


class DistributedHQInteriorAI(DistributedObjectAI):
    def __init__(self, block, air, zoneId):
        DistributedObjectAI.__init__(self, air)
        self.block = block
        self.zoneId = zoneId
        self.tutorial = 0

    def getZoneIdAndBlock(self):
        return [self.zoneId, self.block]

    def getLeaderBoard(self):
        return pickle.dumps([(), (), ()], protocol=1)

    def getTutorial(self):
        return self.tutorial
