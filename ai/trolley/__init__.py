from typing import List, Optional

from enum import IntEnum


class PurchaseState(IntEnum):
    NO_CLIENT = 0
    WAITING = 1
    PLAY_AGAIN = 2
    EXIT = 3
    DISCONNECTED = 4


PURCHASE_COUNTDOWN_TIME = 120

INVENTORY_PENDING = 0
INVENTORY_DONE = 1


from dataslots import with_slots
from dataclasses import dataclass

@with_slots
@dataclass
class Purchaser:
    avId: int
    score: int = 0
    money: int = 0
    state: int = PurchaseState.NO_CLIENT
    votes: int = 0
    newbie: bool = False
    inventoryState: int = INVENTORY_DONE


NoPreviousGameId = 0
RaceGameId = 1
CannonGameId = 2
TagGameId = 3
PatternGameId = 4
RingGameId = 5
MazeGameId = 6
TugOfWarGameId = 7
CatchGameId = 8
DivingGameId = 9
TargetGameId = 10
PairingGameId = 11
VineGameId = 12
IceGameId = 13
CogThiefGameId = 14
TwoDGameId = 15
PhotoGameId = 16
TravelGameId = 100


MinigamePlayerMatrix = {
    1: (CannonGameId, RingGameId, MazeGameId, TugOfWarGameId, CatchGameId, DivingGameId, TargetGameId, PairingGameId,
        VineGameId, CogThiefGameId, TwoDGameId),
    2: (CannonGameId, PatternGameId, RingGameId, TagGameId, MazeGameId, TugOfWarGameId, CatchGameId, DivingGameId,
        TargetGameId, PairingGameId, VineGameId, IceGameId, CogThiefGameId, TwoDGameId),
    3: (CannonGameId, PatternGameId, RingGameId, TagGameId, RaceGameId, MazeGameId, TugOfWarGameId, CatchGameId,
        DivingGameId, TargetGameId, PairingGameId, VineGameId, IceGameId, CogThiefGameId, TwoDGameId),
    4: (CannonGameId, PatternGameId, RingGameId, TagGameId, RaceGameId, MazeGameId, TugOfWarGameId, CatchGameId,
        DivingGameId, TargetGameId, PairingGameId, VineGameId, IceGameId, CogThiefGameId, TwoDGameId)
}


def createMinigame(air, players: List[int], newbies: List[int], trolleyZone: int, zone: Optional[int] = None):
    if zone is None:
        zone = acquireZone()

    from . import DistributedTagGameAI
    mg = DistributedTagGameAI.DistributedTagGameAI(air, players, trolleyZone)
    mg.newbies = newbies
    mg.generateWithRequired(zone)

    return zone, mg.MINIGAME_ID


MINIGAME_ZONES = {}


def acquireZone():
    zone = simbase.air.allocateZone()
    MINIGAME_ZONES[zone] = 1
    return zone


def incZoneRef(zoneId):
    MINIGAME_ZONES[zoneId] += 1


def decZoneRef(zoneId):
    MINIGAME_ZONES[zoneId] -= 1
    if MINIGAME_ZONES[zoneId] <= 0:
        simbase.air.deallocateZone(zoneId)
        del MINIGAME_ZONES[zoneId]
