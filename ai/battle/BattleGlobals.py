from enum import IntEnum
from typing import NamedTuple, List, Tuple, Union
import math


MIN_TRACK_INDEX = 0
MAX_TRACK_INDEX = 6
MIN_LEVEL_INDEX = 0
MAX_LEVEL_INDEX = 6


class Tracks(IntEnum):
    UN_ATTACK = -2
    NO_ATTACK = -1

    HEAL = 0
    TRAP = 1
    LURE = 2
    SOUND = 3
    THROW = 4
    SQUIRT = 5
    DROP = 6

    NPC_RESTOCK_GAGS = 7
    NPC_TOONS_HIT = 8
    NPC_COGS_MISS = 9

    PASS = 98
    SOS = 99
    NPCSOS = 97
    PETSOS = 96
    FIRE = 100

    def isGagTrack(self):
        return 0 <= self.value <= 6


NUM_TRACKS = 7
UBER_INDEX = 6
NUM_PROPS = 7


regMaxSkill = 10000
UberSkill = 500
MaxSkill = UberSkill + regMaxSkill


class GagTrack(NamedTuple):
    index: int
    levels: Tuple[int, ...]
    carryLimits: Tuple[Tuple[int, ...], ...]
    damages: Tuple[Tuple[int, int], ...]

    def getDamage(self, level: int, exp: int, organicBonus=False, propBonus=False) -> int:
        if self.index == Tracks.LURE:
            return 0

        minDamage, maxDamage = self.damages[level]
        minExperience = self.levels[level]
        if level == UBER_INDEX:
            maxExperience = MaxSkill
        else:
            maxExperience = self.levels[level + 1]

        exp = min(exp, maxExperience)
        expPerHp = float(maxExperience - minExperience + 1) / float(maxDamage - maxDamage + 1)
        damage = math.floor((exp - minExperience) / expPerHp) + minDamage

        if organicBonus or propBonus:
            damage += GagTrack.getDamageBonus(damage)

        return damage

    @staticmethod
    def getDamageBonus(normal: int) -> int:
        if not normal:
            return 0

        return max(int(normal * 0.1), 1)

    @property
    def unpaidMaxSkill(self) -> int:
        if self.index in {Tracks.THROW, Tracks.SQUIRT}:
            return self.levels[4] - 1
        else:
            return self.levels[1] - 1


GagTracks = (
    GagTrack(
        Tracks.HEAL,
        levels=(0, 20, 200, 800, 2000, 6000, 10000),
        carryLimits=(
            (10, 0, 0, 0, 0, 0, 0),
            (10, 5, 0, 0, 0, 0, 0),
            (15, 10, 5, 0, 0, 0, 0),
            (20, 15, 10, 5, 0, 0, 0),
            (25, 20, 15, 10, 3, 0, 0),
            (30, 25, 20, 15, 7, 3, 0),
            (30, 25, 20, 15, 7, 3, 1)
        ),
        damages=(
            (8, 10),
            (15, 18),
            (25, 30),
            (40, 45),
            (60, 70),
            (90, 120),
            (210, 210),
        )
    ),
    GagTrack(
        Tracks.TRAP,
        levels=(0, 20, 100, 800, 2000, 6000, 10000),
        carryLimits=(
            (5, 0, 0, 0, 0, 0, 0),
            (7, 3, 0, 0, 0, 0, 0),
            (10, 7, 3, 0, 0, 0, 0),
            (15, 10, 7, 3, 0, 0, 0),
            (15, 15, 10, 5, 3, 0, 0),
            (20, 15, 15, 10, 5, 2, 0),
            (20, 15, 15, 10, 5, 2, 1)
        ),
        damages=(
            (10, 12),
            (18, 20),
            (30, 35),
            (45, 50),
            (60, 70),
            (90, 180),
            (195, 195),
        ),
    ),
    GagTrack(
        Tracks.LURE,
        levels=(0, 20, 100, 800, 2000, 6000, 10000),
        carryLimits=(
            (10, 0, 0, 0, 0, 0, 0),
            (10, 5, 0, 0, 0, 0, 0),
            (15, 10, 5, 0, 0, 0, 0),
            (20, 15, 10, 5, 0, 0, 0),
            (25, 20, 15, 10, 3, 0, 0),
            (30, 25, 20, 15, 7, 3, 0),
            (30, 25, 20, 15, 7, 3, 1)
        ),
        damages=(
            (0, 0),
            (0, 0),
            (0, 0),
            (0, 0),
            (0, 0),
            (0, 0),
            (0, 0),
        ),
    ),
    GagTrack(
        Tracks.SOUND,
        levels=(0, 40, 200, 1000, 2500, 7500, 10000),
        carryLimits=(
            (10, 0, 0, 0, 0, 0, 0),
            (10, 5, 0, 0, 0, 0, 0),
            (15, 10, 5, 0, 0, 0, 0),
            (20, 15, 10, 5, 0, 0, 0),
            (25, 20, 15, 10, 3, 0, 0),
            (30, 25, 20, 15, 7, 3, 0),
            (30, 25, 20, 15, 7, 3, 1)
        ),
        damages=(
            (3, 4),
            (5, 7),
            (9, 11),
            (14, 16),
            (19, 21),
            (25, 50),
            (90, 90),
        ),
    ),
    GagTrack(
        Tracks.THROW,
        levels=(0, 10, 50, 400, 2000, 6000, 10000),
        carryLimits=(
            (10, 0, 0, 0, 0, 0, 0),
            (10, 5, 0, 0, 0, 0, 0),
            (15, 10, 5, 0, 0, 0, 0),
            (20, 15, 10, 5, 0, 0, 0),
            (25, 20, 15, 10, 3, 0, 0),
            (30, 25, 20, 15, 7, 3, 0),
            (30, 25, 20, 15, 7, 3, 1)
        ),
        damages=(
            (4, 6),
            (8, 10),
            (14, 17),
            (24, 27),
            (36, 40),
            (48, 100),
            (120, 120),
        ),
    ),
    GagTrack(
        Tracks.SQUIRT,
        levels=(0, 10, 50, 400, 2000, 6000, 10000),
        carryLimits=(
            (10, 0, 0, 0, 0, 0, 0),
            (10, 5, 0, 0, 0, 0, 0),
            (15, 10, 5, 0, 0, 0, 0),
            (20, 15, 10, 5, 0, 0, 0),
            (25, 20, 15, 10, 3, 0, 0),
            (30, 25, 20, 15, 7, 3, 0),
            (30, 25, 20, 15, 7, 3, 1)
        ),
        damages=(
            (3, 4),
            (6, 8),
            (10, 12),
            (18, 21),
            (27, 30),
            (36, 80),
            (105, 105)
        ),
    ),
    GagTrack(
        Tracks.DROP,
        levels=(0, 20, 100, 500, 2000, 6000, 10000),
        carryLimits=(
            (10, 0, 0, 0, 0, 0, 0),
            (10, 5, 0, 0, 0, 0, 0),
            (15, 10, 5, 0, 0, 0, 0),
            (20, 15, 10, 5, 0, 0, 0),
            (25, 20, 15, 10, 3, 0, 0),
            (30, 25, 20, 15, 7, 3, 0),
            (30, 25, 20, 15, 7, 3, 1)
        ),
        damages=(
            (10, 10),
            (18, 18),
            (30, 30),
            (45, 45),
            (60, 60),
            (85, 170),
            (180, 180)
        ),
    ),
)


def getGagTrack(index: Union[int, Tracks]) -> GagTrack:
    return GagTracks[index]


AvPropAccuracy = (
    (70, 70, 70, 70, 70, 70, 100),
    (0, 0, 0, 0, 0, 0, 0),
    (50, 50, 60, 60, 70, 70, 90),
    (95, 95, 95, 95, 95, 95, 95),
    (75, 75, 75, 75, 75, 75, 75),
    (95, 95, 95, 95, 95, 95, 95),
    (50, 50, 50, 50, 50, 50, 50)
)


AvLureBonusAccuracy = (60, 60, 70, 70, 80, 80, 100)


ExperienceCap = 200
