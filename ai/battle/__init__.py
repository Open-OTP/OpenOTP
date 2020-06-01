from typing import List, Optional, Dict, NamedTuple, Union, Tuple, Generator

from direct.fsm.FSM import FSM
from itertools import islice

from ai.DistributedObjectAI import DistributedObjectAI
from ai.ToonBarrier import ToonBarrier
from ai.suit.DistributedSuitAI import DistributedSuitBaseAI


FACEOFF_TAUNT_T = 3.5
FACEOFF_LOOK_AT_PROP_T = 6
CLIENT_INPUT_TIMEOUT = 20.0
SERVER_BUFFER_TIME = 2.0
SERVER_INPUT_TIMEOUT = CLIENT_INPUT_TIMEOUT + SERVER_BUFFER_TIME

import random


from ai.toon.NPCToons import getSOSCard, SOSCard



from .BattleGlobals import *
from ai.TimeManagerAI import DisconnectCloseWindow


from dataslots import with_slots
from dataclasses import dataclass, field



NO_ID = -1
NO_ATTACK = -1


@with_slots
@dataclass
class ToonAttack(object):
    avId: int
    track: Union[int, Tracks] = NO_ATTACK
    level: int = -1
    target: int = -1
    hps: List[int] = field(default_factory=list)
    accBonus: int = 0
    hpBonus: int = 0
    kbBonuses: List[int] = field(default_factory=list)
    suitsDiedFlag: int = 0
    suitsRevivedFlag: int = 0
    _battle: Optional['DistributedBattleBaseAI'] = None


    @property
    def affectsGroup(self) -> bool:
        track, level = self.track, self.level

        if track in {Tracks.NPCSOS, Tracks.PETSOS, Tracks.SOUND}:
            return True

        if track in {Tracks.HEAL, Tracks.LURE}:
            return level in {1, 3, 5}

        if MIN_TRACK_INDEX <= track <= MAX_TRACK_INDEX:
            return level == 6

        return False

    @property
    def hit(self) -> bool:
        return not self.accBonus and self.track != Tracks.NO_ATTACK

    @property
    def actualTrack(self) -> Tracks:
        if self.track == Tracks.NPCSOS:
            return getSOSCard(self.target).track
        else:
            return self.track

    @property
    def actualTrackLevel(self) -> Tuple[Tracks, int]:
        if self.track == Tracks.NPCSOS:
            card = getSOSCard(self.target)
            return card.track, card.level
        else:
            return self.track, self.level

    @property
    def sosCardDamage(self) -> int:
        return getSOSCard(self.target).damage

    @property
    def damage(self) -> int:
        for dmg in self.hps:
            if dmg > 0:
                return dmg
        else:
            return 0

    def __iter__(self):
        if self.avId != -1:
            yield self._battle.activeToons.index(self.avId)
        else:
            yield self.avId

        yield self.track
        yield self.level

        if self.target != -1:
            if self.track == Tracks.HEAL:
                yield self._battle.activeToons.index(self.target)
            else:
                yield self._battle.suitIndex(self.target)
        else:
            # Group attack
            yield self.target

        yield self.hps
        yield self.accBonus
        yield self.hpBonus
        yield self.kbBonuses
        yield self.suitsDiedFlag
        yield self.suitsRevivedFlag
        self._battle = None

    def __call__(self, battle):
        self._battle = battle
        return self


@with_slots
@dataclass
class SuitAttack(object):
    suitId: int = NO_ID
    attackId: int = NO_ATTACK
    target: int = -1
    hps: List[int] = field(default_factory=list)
    toonsDiedFlag: int = 0
    unused: int = 0
    tauntId: int = 0
    _battle: Optional['DistributedBattleBaseAI'] = None

    @property
    def hit(self) -> bool:
        return any(self.hps)

    @property
    def damage(self) -> int:
        for dmg in self.hps:
            if dmg > 0:
                return dmg
        else:
            return 0

    def __iter__(self):
        if self.suitId != -1:
            yield self._battle.suitIndex(self.suitId)
        else:
            yield self.suitId
        yield self.attackId
        yield self.target
        yield self.hps
        yield self.toonsDiedFlag
        yield self.unused
        yield self.tauntId
        self._battle = None

    def __call__(self, battle):
        self._battle = battle
        return self


class BattleExperience(NamedTuple):
    toonId: int
    originalExp: List[int]
    earnedExp: List[int]
    origQuests: List[int]
    recoveredItems: List[int]
    missedItems: List[int]
    origMerits: List[int]
    earnedMerits: List[int]
    suitParts: List[int]


from panda3d.core import Point3, Vec3


class Point3H(object):
    __slots__ = 'point', 'h'

    def __init__(self, x: float, y: float, z: float, h: int):
        self.point: Point3 = Point3(x, y, z)
        self.h: int = h

    def __iter__(self):
        yield from self.point
        yield self.h


SUIT_POINTS = (
    (Point3H(0, 5, 0, 179),),
    (Point3H(2, 5.3, 0, 170), Point3H(-2, 5.3, 0, 180)),
    (Point3H(4, 5.2, 0, 170), Point3H(0, 6, 0, 179), Point3H(-4, 5.2, 0, 190)),
    (Point3H(6, 4.4, 0, 160), Point3H(2, 6.3, 0, 170), Point3H(-2, 6.3, 0, 190), Point3H(-6, 4.4, 0, 200))
)

SUIT_PENDING_POINTS = (
    Point3H(-4, 8.2, 0, 190),
    Point3H(0, 9, 0, 179),
    Point3H(4, 8.2, 0, 170),
    Point3H(8, 3.2, 0, 160)
)


TOON_POINTS = (
    (Point3H(0, -6, 0, 0),),
    (Point3H(1.5, -6.5, 0, 5), Point3H(-1.5, -6.5, 0, -5)),
    (Point3H(3, -6.75, 0, 5), Point3H(0, -7, 0, 0), Point3H(-3, -6.75, 0, -5)),
    (Point3H(4.5, -7, 0, 10), Point3H(1.5, -7.5, 0, 5), Point3H(-1.5, -7.5, 0, -5), Point3H(-4.5, -7, 0, -10))
)

TOON_PENDING_POINTS = (
    Point3H(-3, -8, 0, -5),
    Point3H(0, -9, 0, 0),
    Point3H(3, -8, 0, 5),
    Point3H(5.5, -5.5, 0, 20)
)


SUIT_SPEED = 4.8
TOON_SPEED = 8.0

UBER_INDEX = 6


KBBONUS_TGT_LURED = 1


def calcFaceoffTime(center: Point3, suitpos: Point3) -> float:
    facing = Vec3(center - suitpos)
    facing.normalize()
    suitdest = Point3(center - Point3(facing * 6.0))
    dist = Vec3(suitdest - suitpos).length()
    return dist / SUIT_SPEED


def calcSuitMoveTime(pos0: Point3, pos1: Point3) -> float:
    dist = Vec3(pos0 - pos1).length()
    return dist / SUIT_SPEED


def calcToonMoveTime(pos0: Point3, pos1: Point3) -> float:
    dist = Vec3(pos0 - pos1).length()
    return dist / TOON_SPEED


from ai.suit.SuitGlobals import SuitAttributes, pickFromFreqList, suitAttackAffectsGroup


NO_TRAP = -1
TRAP_CONFLICT = -2

TOON_ATTACK_TIME = 12.0
SUIT_ATTACK_TIME = 12.0


class SuitTrap(NamedTuple):
    level: int
    attackerId: int
    damage: int


from dataclasses import dataclass

@dataclass
class LurerInfo(object):
    level: int
    availLureId: int
    credit: int


@dataclass
class LuredSuitInfo(object):
    currRounds: int
    maxRounds: int
    wakeChance: int
    lurerDict: Dict[int, LurerInfo]


@dataclass
class SuccessfulLure(object):
    toonId: int
    level: int
    acc: int
    damage: int = -1


AttackExpPerTrack = [0, 10, 20, 30, 40, 50, 60]
AccuracyBonuses = [0, 20, 40, 60]
NumRoundsLured = [2, 2, 3, 3, 4, 4, 15]
DamageBonuses = [0, 20, 20, 20]

from ai.toon import NPCToons


class BattleCalculator:
    def __init__(self, battle: 'DistributedBattleBaseAI'):
        self.battle: DistributedBattleBaseAI = battle
        self.tutorial = self.battle.tutorial

        self.toonAttackOrder: List[int] = []
        self.toonsHit = False
        self.cogsMiss = False
        self.kbBonuses = [{}, {}, {}, {}]
        self.hpBonuses = [{}, {}, {}, {}]
        self.toonHPAdjusts: Dict[int, int] = {}

        self.traps: Dict[int, SuitTrap] = {}
        self.luredSuits: Dict[int, LuredSuitInfo] = {}
        self.successfulLures: Dict[int, SuccessfulLure] = {}
        self.delayUnlures: List[int] = []

        self.creditLevel = 0

        self.suitAttackers: Dict[int, Dict[int, int]] = {}
        self.trainTrapTriggered = False

    def calculateRound(self):
        longest = max(len(self.battle.activeToons), len(self.battle.activeSuits))
        for attack in self.battle.activeToonAttacks:
            attack.hps = [-1] * longest
            attack.kbBonuses = [-1] * longest

        for suitAttack in self.battle.suitAttacks:
            suitAttack.hps = [-1] * len(self.battle.activeToons)

        self._initRound()

        for suit in self.battle.activeSuits:
            if suit.generated:
                suit.d_setHP()

        self._calculateToonAttacks()
        self._updateLureTimeouts()
        self._calculateSuitAttacks()
        self.toonsHit = False
        self.cogsMiss = False

    def _calculateSuitAttacks(self):
        for i in range(len(self.battle.suitAttacks)):
            if i >= len(self.battle.activeSuits):
                break

            suit = self.battle.activeSuits[i]
            suitId = suit.do_id
            attack = self.battle.suitAttacks[i]
            attack.suitId = suitId
            if not self._suitCanAttack(suit):
                continue

            if self.battle.pendingSuits.count(suit) or self.battle.joiningSuits.count(suit):
                continue

            attack.attackId = suit.pickSuitAttack()
            attack.target = self._calcSuitTarget(attack)
            if attack.target == -1:
                attack = SuitAttack()
                self.battle.suitAttacks[i] = attack

            self._calcSuitAtkHp(attack, suit)

            targets = self._createSuitAtkTargetList(attack, suit)
            allTargetsDead = True
            for toonId in targets:
                if self._getToonHp(toonId) > 0:
                    allTargetsDead = False
                    break

            if allTargetsDead:
                self.battle.suitAttacks[i] = SuitAttack()

            if attack.hit:
                self._applySuitAttackDamages(attack)

    def _applySuitAttackDamages(self, attack):
        for i, toonId in enumerate(self.battle.activeToons):
            damage = attack.hps[i]
            if damage <= 0:
                continue

            hp = self._getToonHp(toonId)
            if hp - damage <= 0:
                self.toonLeftBattle(toonId)
                attack.toonsDiedFlag = attack.toonsDiedFlag | 1 << i

            self.toonHPAdjusts[toonId] -= damage

    def toonLeftBattle(self, toonId):
        # if toonId in self.toonSkillPtsGained:
        #     del self.toonSkillPtsGained[toonId]

        self._clearTrapCreator(toonId)
        self._clearLurer(toonId)

    def _calcSuitAtkHp(self, attack: SuitAttack, suit):
        targetList = self._createSuitAtkTargetList(attack, suit)

        for targetId in targetList:
            targetIndex = self.battle.activeToons.index(targetId)
            attack.hps[targetIndex] = suit.testSuitAttackHit(attack.attackId)

    def _createSuitAtkTargetList(self, attack: SuitAttack, suit):
        if attack.attackId == NO_ATTACK:
            return []

        attackInfo = suit.attributes.attacks[attack.attackId]

        if suitAttackAffectsGroup(attackInfo.name):
            return self.battle.activeToons[:]
        else:
            return [self.battle.activeToons[attack.target]]

    def _calcSuitTarget(self, attack: SuitAttack) -> int:
        suitId = attack.suitId

        if suitId in self.suitAttackers and random.randint(0, 99) < 75:
            totalDamage = sum(self.suitAttackers[suitId].values())

            dmgs = []

            for toonId in self.suitAttackers[suitId]:
                dmgs.append(self.suitAttackers[suitId][toonId] / totalDamage * 100)

            dmgIndex = pickFromFreqList(dmgs)
            if dmgIndex is None:
                return self._pickRandomToonIndex()

            toonId = list(self.suitAttackers[suitId].keys())[dmgIndex]

            if toonId == -1 or toonId not in self.battle.activeToons:
                return -1
            return self.battle.activeToons.index(toonId)
        else:
            return self._pickRandomToonIndex()

    def _pickRandomToonIndex(self):
        liveToons = list(filter(lambda tid: not self._isToonDead(tid), self.battle.activeToons))
        if not liveToons:
            return -1
        else:
            return self.battle.activeToons.index(random.choice(liveToons))

    def _suitCanAttack(self, suit):
        if suit.getHP() <= 0 or self._isSuitLured(suit.do_id) or suit.reviveCheckAndClear():
            return False
        else:
            return True

    def _updateLureTimeouts(self):
        noLongerLured = []

        for suitId in self.luredSuits:
            luredSuit = self.luredSuits[suitId]
            luredSuit.currRounds += 1

            if luredSuit.currRounds <= luredSuit.maxRounds or (luredSuit.currRounds > 0 and random.randint(0, 99) < luredSuit.wakeChance):
                noLongerLured.append(suitId)

        for suitId in noLongerLured:
            del self.luredSuits[suitId]

    def _initRound(self):
        self.toonAttackOrder.clear()
        self.toonAttackOrder.extend((attack.avId for attack in self.getToonAttacks(Tracks.PETSOS)))
        self.toonAttackOrder.extend((attack.avId for attack in self.getToonAttacks(Tracks.FIRE)))

        for track in range(Tracks.HEAL, Tracks.DROP + 1):
            track = Tracks(track)
            attacks = self.getToonAttacks(track)
            if track == Tracks.TRAP:
                attacks.sort(key=lambda atk: atk.track == Tracks.NPCSOS)

            self.toonAttackOrder.extend((attack.avId for attack in attacks))

        self.toonsHit = False
        self.cogsMiss = False

        for attack in self.battle.activeToonAttacks:
            if attack.track == Tracks.NPCSOS:
                sosCard = NPCToons.getSOSCard(attack.target)
                if sosCard.track == Tracks.NPC_COGS_MISS:
                    self.cogsMiss = True
                elif sosCard.track == Tracks.NPC_TOONS_HIT:
                    self.toonsHit = True

        self.toonHPAdjusts = {avId: 0 for avId in self.battle.activeToons}

    def _calculateToonAttacks(self):
        self.kbBonuses = [{}, {}, {}, {}]

        self.creditLevel = max((suit.actualLevel for suit in self.battle.activeSuits))

        for i, toonId in enumerate(self.toonAttackOrder):
            if self._isToonDead(toonId):
                continue

            attack = self.battle.toonAttacks[toonId]
            track = attack.actualTrack

            if track not in {Tracks.NO_ATTACK, Tracks.PETSOS, Tracks.NPCSOS}:
                self._calcToonAtkDamage(toonId)

                self._handleKnockbackBonus(attack, i)
                self._handleSameTrackBonus(attack, i)

                lastAttack = i == len(self.toonAttackOrder) - 1

                if attack.hit and attack.actualTrack in {Tracks.THROW, Tracks.SQUIRT, Tracks.SOUND}:
                    if lastAttack:
                        self._clearLuredSuitsByAttack(attack)
                    else:
                        self._addLuredSuitsDelayed(attack)

                if lastAttack:
                    self._clearLuredSuitsDelayed()

        self._processKnockbackBonuses()
        self._processSameTrackBonuses()
        self._postProcessToonAttacks()

    def _postProcessToonAttacks(self):

        lastTrack = -1
        lastAttacks = []

        for toonId in self.toonAttackOrder:
            if toonId == -1:
                continue

            attack = self.battle.toonAttacks[toonId]
            actualTrack, level = attack.actualTrackLevel

            if actualTrack not in {Tracks.HEAL, Tracks.SOS, Tracks.NO_ATTACK, Tracks.NPCSOS, Tracks.PETSOS}:
                targets = self._createToonAtkTargetList(attack)
                allTargetsDead = True

                for suitId in targets:
                    damage = attack.damage
                    suit = simbase.air.doTable[suitId]
                    suitIndex = self.battle.suitIndex(suitId)

                    if damage > 0:
                        self._rememberToonAttack(suitId, attack.avId, damage)

                    if actualTrack == Tracks.TRAP and suitId in self.traps:
                        trapInfo = self.traps[suitId]

                    targetDead = suit.getHP() <= 0

                    if targetDead:
                        if actualTrack != Tracks.LURE:
                            for prevAttack in lastAttacks:
                                self._clearTargetDied(suitId, prevAttack, attack)
                    else:
                        allTargetsDead = False

                    if suitId in self.successfulLures and actualTrack == Tracks.LURE:
                        lureInfo = self.successfulLures[suitId]
                        lurerId = lureInfo.toonId
                        lureAttack = self.battle.toonAttacks[lurerId]
                        if suitId in self.traps:
                            if self.traps[suitId].level == UBER_INDEX:
                                self.trainTrapTriggered = True

                            del self.traps[suitId]

                        lureAttack.kbBonuses[suitIndex] = KBBONUS_TGT_LURED
                        lureAttack.hps[suitIndex] = lureInfo.damage
                    elif self._isSuitLured(suitId) and actualTrack == Tracks.DROP:
                        attack.kbBonuses[suitIndex] = 0

                    if targetDead and actualTrack != lastTrack:
                        attack.hps[suitIndex] = 0
                        attack.kbBonuses[suitIndex] = -1

                if allTargetsDead and actualTrack != lastTrack:
                    self._clearToonAttack(toonId)

            damagesDone = self._applyToonAttackDamages(toonId)
            self._applyToonAttackDamages(toonId, hpbonus=True)
            if actualTrack not in {Tracks.LURE, Tracks.SOUND, Tracks.DROP}:
                self._applyToonAttackDamages(toonId, kbbonus=True)

            if lastTrack != actualTrack:
                lastAttacks.clear()
                lastTrack = actualTrack
            lastAttacks.append(attack)
            if actualTrack not in {Tracks.PETSOS, Tracks.TRAP, Tracks.LURE} and level < self.creditLevel:
                if actualTrack == Tracks.HEAL and damagesDone != 0:
                    self._addAttackExp(attack)
                else:
                    self._addAttackExp(attack)

        if self.trainTrapTriggered:
            for suit in self.battle.activeSuits:
                suitId = suit.do_id
                if suitId in self.traps:
                    del self.traps[suitId]

    def _applyToonAttackDamages(self, toonId: int, hpbonus=False, kbbonus=False):
        totalDamages = 0
        attack = self.battle.toonAttacks[toonId]
        track = attack.actualTrack
        targetToons = track == Tracks.HEAL or track == Tracks.PETSOS
        if track not in {Tracks.NO_ATTACK, Tracks.SOS, Tracks.NPCSOS, Tracks.TRAP}:
            if targetToons:
                targets = self.battle.activeToons
            else:
                targets = self.battle.activeSuitIds

            for i, targetId in enumerate(targets):
                if hpbonus:
                    if targetId in self._createToonAtkTargetList(attack):
                        damageDone = attack.hpBonus
                    else:
                        damageDone = 0
                elif kbbonus:
                    if targetId in self._createToonAtkTargetList(attack):
                        damageDone = attack.kbBonuses[i]
                    else:
                        damageDone = 0
                else:
                    damageDone = attack.hps[i]

                if damageDone <= 0:
                    continue

                if targetToons:
                    toonHp = self._getToonHp(targetId)
                    toonMaxHp = simbase.air.doTable[toonId].maxHp
                    if toonHp + damageDone > toonMaxHp:
                        damageDone = toonMaxHp - toonHp
                        attack.hps[i] = damageDone
                    self.toonHPAdjusts[targetId] += damageDone
                    totalDamages += damageDone
                    continue

                suit = simbase.air.doTable[targetId]
                suit.hp = suit.hp - damageDone
                totalDamages += damageDone

                if suit.hp <= 0:
                    if suit.revives:
                        suit.revives -= 1
                        suit.hp = suit.maxHP
                        attack.suitsRevivedFlag = attack.suitsRevivedFlag | 1 << i
                        suit.revivedFlag = True
                    else:
                        self.suitLeftBattle(targetId)
                        attack.suitsDiedFlag = attack.suitsDiedFlag | 1 << i

        return totalDamages

    def _clearTargetDied(self, suitId: int, lastAttack: ToonAttack, attack: ToonAttack):
        position = self.battle.suitIndex(suitId)
        if lastAttack.actualTrack == attack.actualTrack and lastAttack.suitsDiedFlag & 1 << position and attack.hit:
            lastAttack.suitsDiedFlag = lastAttack.suitsDiedFlag ^ 1 << position
            self.suitLeftBattle(suitId)
            attack.suitsDiedFlag = attack.suitsDiedFlag | 1 << position

    def suitLeftBattle(self, suitId):
        if self._isSuitLured(suitId):
            del self.luredSuits[suitId]
        if suitId in self.suitAttackers:
            del self.suitAttackers[suitId]
        if suitId in self.traps:
            del self.traps[suitId]

    def _rememberToonAttack(self, suitId, toonId, damage):
        if suitId not in self.suitAttackers:
            self.suitAttackers[suitId] = {toonId: damage}
        else:
            if toonId not in self.suitAttackers[suitId]:
                self.suitAttackers[suitId][toonId] = damage
            elif self.suitAttackers[suitId][toonId] <= damage:
                self.suitAttackers[suitId][toonId] = damage

    def _processSameTrackBonuses(self):
        targetIndex = 0
        for bonusDict in self.hpBonuses:
            for track in bonusDict:
                numDmgs = len(bonusDict[track])
                if numDmgs <= 1:
                    continue
                totalDmg = sum(map(lambda f: f[1], bonusDict[track]))
                lastAttackIndex = bonusDict[track][numDmgs - 1][0]
                toonId = self.toonAttackOrder[lastAttackIndex]
                attack = self.battle.toonAttacks[toonId]

                attack.hpBonus = math.ceil(totalDmg * (DamageBonuses[numDmgs - 1] * 0.01))

            targetIndex += 1

        self.hpBonuses = [{}, {}, {}, {}]

    def _processKnockbackBonuses(self):
        targetIndex = 0
        for bonusDict in self.kbBonuses:
            for track in bonusDict:
                numDmgs = len(bonusDict[track])
                if not numDmgs:
                    continue
                totalDmg = sum(map(lambda f: f[1], bonusDict[track]))

                lastAttackIndex = bonusDict[track][numDmgs - 1][0]
                toonId = self.toonAttackOrder[lastAttackIndex]
                attack = self.battle.toonAttacks[toonId]

                attack.kbBonuses[targetIndex] = totalDmg * 0.5

            targetIndex += 1

        self.kbBonuses = [{}, {}, {}, {}]

    def _clearLuredSuitsDelayed(self):
        for suitId in self.delayUnlures:
            if self._isSuitLured(suitId):
                del self.luredSuits[suitId]

        self.delayUnlures.clear()

    def _clearLuredSuitsByAttack(self, attack):
        targets = self._createToonAtkTargetList(attack)

        for suitId in targets:
            if self._isSuitLured(suitId):
                del self.luredSuits[suitId]

    def _handleSameTrackBonus(self, attack, attackIndex):
        track = attack.actualTrack

        if attack.damage and track not in {Tracks.LURE, Tracks.HEAL, Tracks.PETSOS}:
            targets = self._createToonAtkTargetList(attack)

            for suitId in targets:
                suitIndex = self.battle.suitIndex(suitId)

                if track in self.hpBonuses[suitIndex]:
                    self.hpBonuses[suitIndex][track].append([attackIndex, attack.damage])
                else:
                    self.hpBonuses[suitIndex][track] = [[attackIndex, attack.damage]]

    def _handleKnockbackBonus(self, attack, attackIndex):
        track = attack.actualTrack
        if attack.damage and track in {Tracks.THROW, Tracks.SQUIRT}:
            targets = self._createToonAtkTargetList(attack)

            for suitId in targets:
                if self._isSuitLured(suitId):
                    suitIndex = self.battle.suitIndex(suitId)

                    if track in self.kbBonuses[suitIndex]:
                        self.kbBonuses[suitIndex][track].append([attackIndex, attack.damage])
                    else:
                        self.kbBonuses[suitIndex][track] = [[attackIndex, attack.damage]]

    def _calcToonAtkDamage(self, toonId: int):
        attack = self.battle.toonAttacks[toonId]
        targets = self._createToonAtkTargetList(attack)
        hit, acc = self._calcToonAtkHit(attack, targets)
        actualTrack, actualLevel = attack.actualTrack
        toon = simbase.air.doTable[toonId]

        if not hit and actualTrack != Tracks.HEAL:
            return

        lureDidDmg = False
        validTargetAvailable = False
        luredIntoTrap = False
        currLureId = -1
        targetLured = False

        for targetId in targets:
            attackDamage = 0

            if actualTrack == Tracks.HEAL or actualTrack == Tracks.PETSOS:
                if not self._isToonDead(targetId):
                    validTargetAvailable = True
            else:
                if not self._isSuitDead(targetId):
                    validTargetAvailable = True

            target = simbase.air.doTable[targetId]

            if actualTrack == Tracks.LURE:

                trapInfo = self.traps.get(targetId)

                if trapInfo is not None and trapInfo.level != TRAP_CONFLICT:
                    attackDamage = trapInfo.damage

                    if trapInfo.attackerId:
                        self._addAttackExp(self.battle.toonAttacks[trapInfo.attackerId])

                    self._clearTrapCreator(trapInfo, targetId)

                    lureDidDmg = True
                    luredIntoTrap = True
                    targetLured = True
                elif not self._isSuitLured(targetId, prevRound=True):
                    rounds = NumRoundsLured[actualLevel]
                    wakeupChance = 100 - (acc * 2)
                    currLureId = self._addLuredSuitInfo(targetId, -1, rounds, wakeupChance, toonId, actualLevel,
                                                        lureId=currLureId,
                                                        npc=attack.track == Tracks.NPCSOS)
                    targetLured = True

                if targetLured and (targetId not in self.successfulLures or self.successfulLures[targetId].level < actualLevel):
                    self.successfulLures[targetId] = SuccessfulLure(toonId, actualLevel, acc)
            else:
                if actualTrack == Tracks.TRAP:
                    npcDamage = 0 if attack.track != Tracks.NPCSOS else attack.sosCardDamage

                    if actualLevel == UBER_INDEX:
                        # TODO: train trap
                        pass
                    else:
                        self._addSuitTrap(targetId, actualLevel, toonId, npcDamage)
                elif self._isSuitLured(targetId) and actualTrack == Tracks.SOUND:
                    index = self.battle.activeSuits.index(target)
                    attack.kbBonuses[index] = 0

                if attack.track == Tracks.NPCSOS and not lureDidDmg:
                    attackDamage = attack.sosCardDamage
                elif attack.track == Tracks.PETSOS:
                    # TODO
                    attackDamage = 0
                elif attack.track == Tracks.FIRE:
                    if toon.pinkSlips:
                        toon.b_setPinkSlips(toon.pinkSlips - 1)
                        target.skeleRevives = 0
                        attackDamage = target.getHP()
                else:
                    organic = toon.propHasOrganicBonus(actualTrack, actualLevel)
                    propBonus = False
                    attackDamage = getGagTrack(actualTrack).getDamage(actualLevel, toon.experience[actualTrack], organicBonus=organic,
                                                                      propBonus=propBonus)

            if not luredIntoTrap and actualTrack == Tracks.LURE:
                result = -1
            elif actualTrack != Tracks.TRAP:
                result = attackDamage
                if actualTrack == Tracks.HEAL and not hit:
                    result *= 0.2
            else:
                result = 0

            if result or actualTrack == Tracks.PETSOS:
                if actualTrack == Tracks.HEAL or actualTrack == Tracks.PETSOS:
                    if targetId not in self.battle.activeToons:
                        continue
                    targetIndex = self.battle.activeToons.index(targetId)
                else:
                    targetIndex = self.battle.activeSuits.index(target)

                if actualTrack == Tracks.HEAL:
                    # Split toon-up
                    result = result // len(targets)

                if targetId in self.successfulLures and actualTrack == Tracks.LURE:
                    self.successfulLures[targetId].damage = result
                else:
                    attack.hps[targetIndex] = result

                if result > 0 and actualTrack not in {Tracks.HEAL, Tracks.DROP, Tracks.PETSOS}:
                    for toonId, lurerInfo in self._getLurerInfos(targetId):
                        if lurerInfo.credit:
                            # self.__addAttackExp(attack, track=attackTrack, level=currInfo[1], attackerId=currInfo[0])
                            self._clearLurer(toonId, lureId=lurerInfo.availLureId)

        if lureDidDmg and actualLevel < self.creditLevel:
            self._addAttackExp(attack)

        if not validTargetAvailable:
            index = self.toonAttackOrder.index(toonId)
            if index == 0:
                prevTrack = Tracks.NO_ATTACK
            else:
                prevToonId = self.toonAttackOrder[index - 1]
                prevTrack = self.battle.toonAttacks[prevToonId].actualTrack

            if prevTrack != actualTrack:
                self._clearToonAttack(toonId)

    def _addLuredSuitsDelayed(self, attack, ignoreDamageCheck=False):
        targets = self._createToonAtkTargetList(attack)
        for suitId in targets:
            suitIndex = self.battle.suitIndex(suitId)

            if self._isSuitLured(suitId) and suitId not in self.delayUnlures and (ignoreDamageCheck or attack.hps[suitIndex] > 0):
                self.delayUnlures.append(suitId)

    def _clearToonAttack(self, toonId):
        attack = self.battle.toonAttacks[toonId]
        longest = max(len(self.battle.activeToons), len(self.battle.activeSuits))
        for i in range(longest):
            attack.hps.append(-1)
            attack.kbBonuses.append(-1)

    def _clearTrapCreator(self, creatorId, suitId=None):
        if suitId is None:
            for suitId in self.traps:
                if creatorId == self.traps[suitId].attackerId:
                    self.traps[suitId].attackerId = 0
        elif suitId in self.traps:
            self.traps[suitId].attackerId = 0

    def _addLuredSuitInfo(self, suitId, currRounds, maxRounds, wakeChance, lurer, lureLvl, lureId=-1, npc=False):
        if lureId == -1:
            availLureId = self.__findAvailLureId(lurer)
        else:
            availLureId = lureId

        if not npc and lureLvl < self.creditLevel:
            credit = True
        else:
            credit = False

        if suitId in self.luredSuits:
            lureInfo = self.luredSuits[suitId]
            if lurer not in lureInfo.lurerDict:
                lureInfo.maxRounds += maxRounds

                if wakeChance < lureInfo.wakeChance:
                    lureInfo.wakeChance = wakeChance
                lureInfo.lurerDict[lurer] = LurerInfo(lureLvl, availLureId, credit)
        else:
            self.luredSuits[suitId] = LuredSuitInfo(currRounds, maxRounds, wakeChance,
                                                    lurerDict={lurer: LurerInfo(lureLvl, availLureId, credit)})

        return availLureId

    def _getLurerInfos(self, targetId: int) -> Generator[Tuple[int, LurerInfo], None, None]:
        luredSuit = self.luredSuits.get(targetId)
        if luredSuit:
            for toonId, lurerInfo in luredSuit.lurerDict.items():
                yield toonId, lurerInfo

    def _clearLurer(self, lurerId, lureId=-1):
        for suitId in self.luredSuits:
            lurerDict = self.luredSuits[suitId].lurerDict
            for toonId in lurerDict:
                if toonId == lurerId and (lureId == -1 or lureId == lurerDict[toonId].availLureId):
                    del lurerDict[lurerId]

    def __findAvailLureId(self, lurerId):
        lureIds = []

        for suitId in self.luredSuits:
            lurerDict = self.luredSuits[suitId].lurerDict

            for toonId in lurerDict:
                availLureId = lurerDict[toonId].availLureId
                if toonId == lurerId and availLureId not in lureIds:
                    lureIds.append(availLureId)

        lureIds.sort()
        currId = 1
        for currLureId in lureIds:
            if currLureId != currId:
                return currId
            currId += 1

        return currId

    def _addSuitTrap(self, suitId, trapLvl, attackerId, npcDamage=0):
        if not npcDamage:
            if suitId in self.traps:
                self.traps[suitId].level = TRAP_CONFLICT
            else:
                toon = simbase.air.doTable[attackerId]
                exp = toon.experience[Tracks.TRAP]
                organic = toon.propHasOrganicBonus(Tracks.TRAP, trapLvl)
                propBonus = False # TODO: street prop bonus
                damage = getGagTrack(Tracks.TRAP).getDamage(trapLvl, exp, organicBonus=organic, propBonus=propBonus)
                credited = trapLvl < self.creditLevel
                self.traps[suitId] = SuitTrap(trapLvl, attackerId=attackerId if credited else 0, damage=damage)
        else:
            if suitId in self.traps and self.traps[suitId].level == TRAP_CONFLICT:
                self.traps[suitId] = SuitTrap(trapLvl, attackerId=0, damage=npcDamage)
            elif not self._isSuitLured(suitId):
                self.traps[suitId] = SuitTrap(trapLvl, attackerId=0, damage=npcDamage)
            else:
                return

    def _addSuitGroupTrap(self, suitId, trapLvl, attackerId, allSuits):
        pass

    def _addAttackExp(self, attack: ToonAttack):
        #TODO
        pass

    def _createToonAtkTargetList(self, attack: ToonAttack) -> List[int]:
        actualTrack, actualLevel = attack.actualTrackLevel

        if actualTrack == Tracks.NPCSOS:
            return []

        if not attack.affectsGroup:
            # Single target on toon or suit.
            return [attack.target]
        elif actualTrack == Tracks.PETSOS:
            # Doodles heal all toons.
            return self.battle.activeToons[:]
        elif actualTrack == Tracks.HEAL:
            if attack.track == Tracks.NPCSOS:
                # SOS Heal heals all toons.
                return self.battle.activeToons[:]
            else:
                # Heal all toons except the healer.
                return [toonId for toonId in self.battle.activeToons if toonId != attack.avId]
        else:
            # Group attack against suits.
            return self.battle.activeSuitIds

    def _calcToonAtkHit(self, attack: ToonAttack, targets: List[int]) -> Tuple[bool, int]:
        if not targets:
            return False, 0
        if self.battle.tutorial:
            return True, 95
        if self.toonsHit:
            return True, 95

        actualTrack, actualLevel = attack.actualTrackLevel

        if actualTrack == Tracks.NPCSOS:
            return True, 95

        if actualTrack == Tracks.FIRE:
            return True, 95

        if actualTrack == Tracks.TRAP:
            return True, 100

        allLured = all((self._isSuitLured(suitId) for suitId in targets))

        if actualTrack == Tracks.DROP and allLured:
            attack.accBonus = True
            return False, 0

        if actualTrack == Tracks.PETSOS:
            # TODO: PET TRICKS
            return False, 0

        tgtDef = 0
        numLured = 0

        if actualTrack != Tracks.HEAL:
            tgtDef = min((self._getTargetDefense(suitId, actualTrack) for suitId in targets))
            numLured = sum((self._isSuitLured(suitId) for suitId in targets))

        expAccBonus = self._getToonExpAccBonus(attack.avId, actualTrack)

        for otherAttackerId in self.toonAttackOrder:
            if otherAttackerId == attack.avId:
                continue

            nextAttack = self.battle.toonAttacks[otherAttackerId]

            if nextAttack.actualTrack == actualTrack and attack.target == nextAttack.target:
                expAccBonus = max(self._getToonExpAccBonus(nextAttack.avId, actualTrack), expAccBonus)

        randChoice = random.randint(0, 99) if attack.track != Tracks.NPCSOS else 0

        propAcc = AvPropAccuracy[actualTrack][actualLevel]

        if actualTrack == Tracks.LURE:
            if self._toonCheckGagBonus(attack.avId, actualTrack, actualLevel):
                propAcc = AvLureBonusAccuracy[actualLevel]

        attackAcc = propAcc + expAccBonus + tgtDef

        attackIndex = self.toonAttackOrder.index(attack.avId)
        if attackIndex > 0 and actualTrack != Tracks.HEAL:
            prevAttackAvId = self.toonAttackOrder[attackIndex - 1]
            prevAttack = self.battle.toonAttacks[prevAttackAvId]
            lureAffected = actualTrack == Tracks.LURE and ((not attack.affectsGroup and attack.target in self.successfulLures) or attack.affectsGroup)

            if prevAttack.actualTrack == actualTrack and (prevAttack.target == attack.target or lureAffected):
                attack.accBonus = prevAttack.accBonus
            return not attack.accBonus, attackAcc

        acc = attackAcc + self._calcToonAccBonus(attack, attackIndex)

        if actualTrack != Tracks.HEAL and actualTrack != Tracks.LURE:
            if allLured:
                return True, 100
            else:
                luredRatio = float(numLured) / float(len(targets))
                acc += luredRatio * 100

        acc = min(acc, 95)

        # Did the attack hit?
        hit = randChoice < acc

        attack.accBonus = not hit

        return hit, attackAcc

    def _calcToonAccBonus(self, attack: ToonAttack, attackIndex: int) -> int:
        actualTrack, level = attack.actualTrackLevel

        numPrevHits = 0

        for prevAttackIndex in range(attackIndex -1, -1, -1):
            prevAvId = self.toonAttackOrder[prevAttackIndex]
            prevAttack = self.battle.toonAttacks[prevAvId]
            prevActualTrack, prevLevel = prevAttack.actualTrackLevel
            if not prevAttack.hit:
                continue

            if prevActualTrack == actualTrack:
                continue

            if prevAttack.affectsGroup or attack.affectsGroup or attack.target == prevAttack.target:
                # Is this attack affecting our target?
                numPrevHits += 1

        return AccuracyBonuses[numPrevHits]

    def _toonCheckGagBonus(self, toonId: int, track: Tracks, level: int):
        # TODO: check for track bonus from trees
        return False

    def _getToonExpAccBonus(self, toonId: int, track: Tracks):
        toon = simbase.air.doTable.get(toonId)
        if toon is None:
            return 0

        expLevel = toon.experience.getExpLevel(track)
        expAccBonus = AttackExpPerTrack[expLevel]

        if track == Tracks.HEAL:
            expAccBonus *= 0.5

        return expAccBonus

    def _getTargetDefense(self, suitId, track: Tracks) -> int:
        if track == Tracks.HEAL:
            return 0
        else:
            suit = simbase.air.doTable[suitId]
            name = suit.dna.name
            return -SuitAttributes[name].defenses[suit.level]

    def _isSuitLured(self, suitId: int, prevRound=False) -> bool:
        if prevRound:
            return suitId in self.luredSuits and self.luredSuits[suitId].currRounds != -1
        else:
            return suitId in self.luredSuits

    def _isToonDead(self, toonId: int) -> bool:
        return self._getToonHp(toonId) <= 0

    def _isSuitDead(self, suitId: int) -> bool:
        suit = simbase.air.doTable[suitId]
        return suit.getHP() <= 0

    def _getToonHp(self, toonId: int) -> int:
        try:
            return simbase.air.doTable[toonId].hp + self.toonHPAdjusts[toonId]
        except KeyError:
            return 0

    def getToonAttacks(self, wantedTrack: Tracks) -> List[ToonAttack]:
        foundAttacks: List[ToonAttack] = []

        for attack in self.battle.activeToonAttacks:
            track = attack.track

            if wantedTrack != Tracks.NPCSOS and track == Tracks.NPCSOS:
                track = NPCToons.getSOSCard(attack.track).track

            if wantedTrack == Tracks.FIRE and track == Tracks.FIRE:
                canFire = True

                for otherAttack in foundAttacks:
                    if attack.target == otherAttack.target:
                        canFire = False

                if not canFire:
                    continue

            if track != wantedTrack:
                continue

            foundAttacks.append(attack)

        foundAttacks.sort(key=lambda atk: atk.level)

        return foundAttacks


MAX_JOIN_T = 20.0

from direct.directnotify import DirectNotifyGlobal


def test():
    yield 5
    yield from ToonAttack(-1)(None)



class DistributedBattleBaseAI(DistributedObjectAI, FSM):
    notify = DirectNotifyGlobal.directNotify.newCategory('DistributedBattleBaseAI')
    notify.setDebug(1)

    def __init__(self, air, finishCallback=None):
        DistributedObjectAI.__init__(self, air)
        FSM.__init__(self, self.__class__.__name__)
        self.finishCallback = finishCallback

        self.joinable = False
        self.runnable = False

        self.suits: List[DistributedSuitBaseAI] = []
        self.pendingSuits: List[DistributedSuitBaseAI] = []
        self.joiningSuits: List[DistributedSuitBaseAI] = []
        self.activeSuits: List[DistributedSuitBaseAI] = []
        self.luredSuits: List[DistributedSuitBaseAI] = []

        self.toons: List[int] = []
        self.joiningToons: List[int] = []
        self.pendingToons: List[int] = []
        self.activeToons: List[int] = []
        self.runningToons: List[int] = []

        self.exitedToons = []

        self.toonAttacks: Dict[int, ToonAttack] = {}
        self.suitAttacks: List[SuitAttack] = [SuitAttack(), SuitAttack(), SuitAttack(), SuitAttack()]

        self.levelDoId = 0
        self.battleCellId = 0
        self.pos = (0, 0, 0)
        self.initialSuitPos = (0, 0, 0)

        self.movieActive = False

        self.suitGone = False
        self.toonGone = False
        self.needAdjust = False
        self._adjustBarrier: Optional[ToonBarrier] = None
        self.adjustingSuits: List[DistributedSuitBaseAI] = []
        self.adjustingToons: List[int] = []

        self._barrier: Optional[ToonBarrier] = None

        self.tutorial = False

        self.bossBattle = False

        self.maxSuits = 4

        self.battleCalc = BattleCalculator(self)

        self.avatarExitEvents: List[str] = []
        self.joinBarriers: Dict[int, ToonBarrier] = {}
        self.numSuitsEver = 0

        self.battleExperience: List[BattleExperience] = []

    def getLevelDoId(self):
        return self.levelDoId

    def getBattleCellId(self):
        return self.battleCellId

    def getInteractivePropTrackBonus(self):
        return -1

    def getPosition(self):
        return self.pos

    def getZoneId(self):
        return self.zoneId

    def getInitialSuitPos(self):
        return self.initialSuitPos

    def getSuitTrap(self, suit: DistributedSuitBaseAI) -> int:
        # Gets suit trap for movie
        trap = self.battleCalc.traps.get(suit.do_id, None)
        if trap is None:
            return 9

        if trap.level == NO_TRAP or trap.level == TRAP_CONFLICT:
            return 9
        else:
            return trap.level

    def getMembers(self):
        suitIds = [suit.do_id for suit in self.suits]
        joiningSuits = ''.join(map(str, [suitIds.index(suit.do_id) for suit in self.joiningSuits]))
        pendingSuits = ''.join(map(str, [suitIds.index(suit.do_id) for suit in self.pendingSuits]))
        activeSuits = ''.join(map(str, [suitIds.index(suit.do_id) for suit in self.activeSuits]))
        luredSuits = ''.join(map(str, [suitIds.index(suit.do_id) for suit in self.luredSuits]))
        suitTraps = ''.join(map(str, [self.getSuitTrap(suit) for suit in self.suits]))

        toonIds = self.toons
        joiningToons = ''.join(map(str, [toonIds.index(toonId) for toonId in self.joiningToons]))
        pendingToons = ''.join(map(str, [toonIds.index(toonId) for toonId in self.pendingToons]))
        activeToons = ''.join(map(str, [toonIds.index(toonId) for toonId in self.activeToons]))
        runningToons = ''.join(map(str, [toonIds.index(toonId) for toonId in self.runningToons]))

        time = globalClockDelta.getRealNetworkTime()

        return suitIds, joiningSuits, pendingSuits, activeSuits, luredSuits, suitTraps, \
               toonIds, joiningToons, pendingToons, activeToons, runningToons,\
               time

    @property
    def activeToonAttacks(self) -> List[ToonAttack]:
        return [self.toonAttacks[toon] for toon in self.activeToons]

    @property
    def activeSuitIds(self) -> List[int]:
        return [suit.do_id for suit in self.activeSuits]

    def suitIndex(self, suitId: int) -> int:
        for i, suit in enumerate(self.activeSuits):
            if suit.do_id == suitId:
                return i
        else:
            raise IndexError

    def getMovie(self):
        # Use a generator here to avoid putting all 71 parameters in a list every time.
        yield self.movieActive
        yield self.activeToons
        yield self.activeSuitIds
        for i in range(4):
            if i > len(self.activeToons) - 1:
                yield from ToonAttack(-1)(self)
            else:
                avId = self.activeToons[i]
                if avId not in self.toonAttacks:
                    yield from ToonAttack(-1)(self)
                else:
                    yield from self.toonAttacks[avId](self)

        for suitAttack in self.suitAttacks:
            yield from suitAttack(self)

    def getBossBattle(self):
        return self.bossBattle

    def getState(self):
        return [self.state, globalClockDelta.getRealNetworkTime()]

    def getBattleExperience(self):
        deathList = []
        uberList = []
        helpfulToonsList = []

        for i in range(4):
            if i > len(self.battleExperience) - 1:
                yield from BattleExperience(-1, [], [], [], [], [], [], [], [])
            else:
                yield from self.battleExperience[i]

        yield deathList
        yield uberList
        yield helpfulToonsList

    def d_setMovie(self):
        self.sendUpdate('setMovie', self.getMovie())

    def d_setMembers(self):
        self.sendUpdate('setMembers', self.getMembers())

    def d_setState(self, state):
        self.sendUpdate('setState', [state, globalClockDelta.getRealNetworkTime()])

    def d_adjust(self):
        self.sendUpdate('adjust', [globalClockDelta.getRealNetworkTime()])

    @property
    def adjusting(self):
        return self._adjustBarrier is not None

    def _requestAdjust(self):
        if self.state != 'WaitForJoin' and self.state != 'WaitForInput':
            return

        if self._adjustBarrier is not None:
            return

        if not self.needAdjust:
            return

        self.d_adjust()

        self.adjustingSuits = self.pendingSuits[:]
        self.adjustingToons = self.pendingToons[:]
        self._adjustBarrier = ToonBarrier(self.uniqueName('adjust'), self.toons,
                                          self._estimateAdjustTime() + SERVER_BUFFER_TIME, self._serverAdjustDone)

    def adjustDone(self):
        toonId = self.air.currentAvatarSender

        if not self.adjusting:
            return

        if toonId not in self.toons:
            return

        self._adjustBarrier.clear(toonId)

    def _serverAdjustDone(self, avIds):
        self.pendingSuits = list(filter(lambda s: s not in self.adjustingSuits, self.pendingSuits))
        self.activeSuits.extend(self.adjustingSuits)
        self.adjustingSuits.clear()

        self.pendingToons = list(filter(lambda t: t not in self.adjustingToons, self.adjustingToons))

        for toon in self.adjustingToons:
            if toon not in self.activeToons:
                self.activeToons.append(toon)
                self.sendEarnedExperience(toon)

        self.adjustingToons.clear()

        # self.__addTrainTrapForNewSuits()
        self.d_setMembers()

        self._adjustBarrier = None

        if self.state == 'WaitForInput':
            self._barrier.resetTimeout(SERVER_INPUT_TIMEOUT)
        elif self.state == 'WaitForJoin':
            self.demand('WaitForInput')

        if self.needAdjust:
            self.notify.debug('__adjustDone() - need to adjust again')
            self._requestAdjust()

    def sendEarnedExperience(self, toonId):
        pass

    def _estimateAdjustTime(self):
        self.needAdjust = False
        adjustTime = 0
        if len(self.pendingSuits) and self.suitGone:
            self.suitGone = False
            pos0 = SUIT_PENDING_POINTS[0].point
            pos1 = SUIT_POINTS[0][0].point
            adjustTime = calcSuitMoveTime(pos0, pos1)
        if len(self.pendingToons) or self.toonGone:
            self.toonGone = False
            if not adjustTime:
                pos0 = TOON_PENDING_POINTS[0].point
                pos1 = TOON_POINTS[0][0].point
                adjustTime = calcToonMoveTime(pos0, pos1)
        return adjustTime

    def enterFaceOff(self):
        pass

    def exitFaceOff(self):
        pass

    def enterWaitForJoin(self):
        if len(self.activeSuits):
            self.demand('WaitForInput')
        else:
            self.runnable = True
            self._requestAdjust()

    def enterWaitForInput(self):
        self.d_setState('WaitForInput')
        self.joinable = True
        self.runnable = True
        self._requestAdjust()

        self._barrier = ToonBarrier(self.uniqueName('wait-input'), self.activeToons, SERVER_INPUT_TIMEOUT, self._serverInputDone)

    def requestAttack(self, track, level, target):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)
        if not av:
            return

        if self.state != 'WaitForInput':
            return

        if avId not in self.activeToons:
            return

        if track == Tracks.SOS:
            # Friend SOS
            self.toonAttacks[avId] = ToonAttack(avId, track=Tracks.SOS, target=target)
        elif track == Tracks.NPCSOS:
            if target not in av.npcFriends:
                return

            if self.checkNPCCollision(target):
                self.toonAttacks[avId] = ToonAttack(avId, track=Tracks.PASS)
            else:
                self.toonAttacks[avId] = ToonAttack(avId, track=Tracks.NPCSOS, target=target)
        elif track == Tracks.PETSOS:
            # TODO
            return
        elif track == Tracks.UN_ATTACK:
            self.toonAttacks[avId] = ToonAttack(avId, track=Tracks.UN_ATTACK)
            self._barrier.unclear(avId)
        elif track == Tracks.PASS:
            self.toonAttacks[avId] = ToonAttack(avId, track=Tracks.PASS)
        elif track == Tracks.FIRE:
            self.toonAttacks[avId] = ToonAttack(avId, track=Tracks.FIRE, target=target)
        else:
            if not MIN_TRACK_INDEX <= track <= MAX_TRACK_INDEX:
                return

            if not MIN_LEVEL_INDEX <= level <= MAX_LEVEL_INDEX:
                return

            if not av.inventory.get(track, level):
                self.toonAttacks[avId] = ToonAttack(avId)
                return

            if track == Tracks.HEAL and (target in self.runningToons or len(self.activeToons) < 2):
                # Prevent self-heal.
                self.toonAttacks[avId] = ToonAttack(avId, track=Tracks.UN_ATTACK)
                self._barrier.unclear(avId)
                return

            attack = ToonAttack(avId, track=Tracks(track), level=level, target=target)

            if target == -1 and not attack.affectsGroup:
                return

            self.toonAttacks[avId] = attack

        self.d_setChosenToonAttacks()
        self._barrier.clear(avId)

    def d_setChosenToonAttacks(self):
        self.sendUpdate('setChosenToonAttacks', self.getChosenToonAttacks())

    def getChosenToonAttacks(self):
        if not self.toonAttacks:
            return [], [], [], []

        attacks = (self.toonAttacks[toon](self) for toon in self.activeToons if toon in self.toonAttacks)

        ids, tracks, levels, targets = islice(zip(*attacks), 4)
        return ids, tracks, levels, targets

    def checkNPCCollision(self, npcId):
        for attack in self.toonAttacks.values():
            if attack.track == Tracks.NPCSOS and attack.target == npcId:
                return True
        return False

    def _serverInputDone(self, avIds):
        if self.adjusting:
            delay = max(globalClock.getFrameTime() - self._barrier.task.wakeTime, 0.8)
            taskMgr.doMethodLater(delay, self._serverInputDone, self.uniqueName('input-delay'), extraArgs=[avIds, ])
        else:
            self.demand('PlayMovie')

    def exitWaitForInput(self):
        taskMgr.remove(self.uniqueName('wait-input'))
        taskMgr.remove(self.uniqueName('input-delay'))

    def enterPlayMovie(self):
        self.joinable = True
        self.runnable = False

        for toonId in self.activeToons:
            if toonId not in self.toonAttacks:
                self.toonAttacks[toonId] = ToonAttack(toonId, Tracks.NO_ATTACK)
            elif self.toonAttacks[toonId].track == Tracks.PASS or self.toonAttacks[toonId].track == Tracks.UN_ATTACK:
                self.toonAttacks[toonId] = ToonAttack(toonId, Tracks.NO_ATTACK)

        self.battleCalc.calculateRound()

        for toonId in self.activeToons:
            self.sendEarnedExperience(toonId)
            toon = self.air.doTable.get(toonId)
            # TODO

        self.movieActive = True
        self.d_setMovie()

        numNPCAttacks = sum([1 for atk in self.toonAttacks.values() if atk.track == Tracks.NPCSOS])
        movieTime = TOON_ATTACK_TIME * (len(self.activeToons) + numNPCAttacks) + SUIT_ATTACK_TIME * len(self.activeSuits) + SERVER_BUFFER_TIME
        self._barrier = ToonBarrier(self.uniqueName('wait-movie'), self.activeToons, movieTime, self._serverMovieDone)
        self.d_setState('PlayMovie')

    def exitPlayMovie(self):
        self.movieActive = False
        taskMgr.remove(self.uniqueName('wait-movie'))

    def movieDone(self):
        senderId = self.air.currentAvatarSender
        if senderId not in self.toons:
            return

        if self.state != 'PlayMovie':
            return

        if self._barrier is not None and self._barrier.active:
            self._barrier.clear(senderId)

    def _serverMovieDone(self, avIds):
        deltaHps: Dict[int, int] = {toonId: 0 for toonId in self.activeToons}
        deadSuits: List[DistributedSuitBaseAI] = []
        deadToons = []

        for toonId in self.activeToons + self.exitedToons:
            attack = self.toonAttacks.get(toonId)
            toon = self.air.doTable[toonId]
            if attack is None:
                continue

            if attack.track == Tracks.NO_ATTACK:
                continue

            # TODO: use up NPC card
            if attack.track == Tracks.NPCSOS:
                pass
            elif attack.actualTrack.isGagTrack():
                toon.inventory.use(attack.actualTrack, attack.level)

            if attack.actualTrack == Tracks.HEAL:
                if attack.affectsGroup:
                    for i in range(len(attack.hps)):
                        currId = self.activeToons[i]
                        deltaHps[currId] += attack.hps[i]
                else:
                    targetId = attack.target
                    index = self.activeToons.index(targetId)
                    deltaHps[targetId] += attack.hps[index]
            else:
                if attack.affectsGroup:
                    for i, suit in enumerate(self.activeSuits):
                        if attack.suitsDiedFlag & 1 << i and suit not in deadSuits:
                            deadSuits.append(suit)
                else:
                    suit = self.getSuit(attack.target)
                    index = self.activeSuits.index(suit)
                    if attack.suitsDiedFlag & 1 << index and suit not in deadSuits:
                        deadSuits.append(suit)

        for suit in deadSuits:
            self._removeSuit(suit)
            suit.resume()

        for i in range(4):
            attack = self.suitAttacks[i]
            if attack.attackId == NO_ATTACK:
                continue

            suitId = attack.suitId
            suit = self.getSuit(suitId)
            if suit is None:
                continue

            attackInfo = suit.attributes.attacks[attack.attackId]
            if suitAttackAffectsGroup(attackInfo.name):
                for j, toonId in enumerate(self.activeToons):
                    toon = self.air.doTable.get(toonId)
                    if not toon:
                        continue

                    deltaHps[toonId] -= attack.hps[j]
            else:
                targetIndex = attack.target
                if not 0 <= targetIndex < len(self.activeToons):
                    continue
                toonId = self.activeToons[targetIndex]
                deltaHps[toonId] -= attack.hps[targetIndex]

        for toonId in self.activeToons:
            toon = self.air.doTable.get(toonId)
            if not toon:
                continue

            deltaHp = deltaHps[toonId]

            if deltaHp > 0:
                toon.toonUp(deltaHp, quietly=True)
            else:
                toon.takeDamage(abs(deltaHp), quietly=True)

            if toon.hp <= 0:
                toon.inventory.zero(killUber=True)
                deadToons.append(toon)

        for toon in deadToons:
            self._removeToon(toon.do_id)

        self.clearAttacks()
        self.d_setMovie()
        self.d_setChosenToonAttacks()
        lastActiveSuitDied = not len(self.activeSuits) and not len(self.pendingSuits)
        self.localMovieDone(deadToons, deadSuits, lastActiveSuitDied)

    def localMovieDone(self, deadToons, deadSuits, lastActiveSuitDied):
        pass

    def _removeSuit(self, suit: DistributedSuitBaseAI):
        for sublist in (self.suits, self.joiningSuits, self.pendingSuits,
                        self.adjustingSuits, self.activeSuits, self.luredSuits):
            try:
                sublist.remove(suit)
            except ValueError:
                continue
        self.suitGone = True

    def clearAttacks(self):
        self.toonAttacks.clear()
        self.suitAttacks = [SuitAttack(), SuitAttack(), SuitAttack(), SuitAttack()]

    def getSuit(self, suitId: int) -> Optional[DistributedSuitBaseAI]:
        for suit in self.suits:
            if suit.do_id == suitId:
                return suit
        return None

    def toonRequestJoin(self, x, y, z):
        toonId = self.air.currentAvatarSender
        self.signupToon(toonId, x, y, z)

    def signupToon(self, toonId, x, y, z):
        if toonId in self.toons:
            return
        if self.toonCanJoin():
            toon = self.air.doTable.get(toonId)
            if toon is not None:
                self.addToon(toon)
                self.d_setMembers()
        else:
            self.sendUpdateToAvatar(toonId, 'denyLocalToonJoin', [])

    def addToon(self, toon, joining=True):
        # toon.stopToonUp()
        toonId = toon.do_id
        event = self.air.getAvatarExitEvent(toonId)
        self.avatarExitEvents.append(event)
        self.accept(event, self.__handleUnexpectedExit, extraArgs=[toonId])
        if self.do_id is not None:
            toon.b_setBattleId(self.do_id)

        self.toons.append(toonId)
        if joining:
            self.joiningToons.append(toonId)

            toPendingTime = MAX_JOIN_T + SERVER_BUFFER_TIME
            self.joinBarriers[toonId] = ToonBarrier('to-pending-av-%d' % toonId, self.toons, toPendingTime, self._serverToonJoinDone,
                                                    extraArgs=[toonId, ])

    def _serverToonJoinDone(self, avIds, joinedToonId):
        barrier = self.joinBarriers[joinedToonId]

        if barrier.active:
            barrier.cleanup()

        del self.joinBarriers[joinedToonId]
        self._makeToonPending(joinedToonId)

    def _makeToonPending(self, toonId):
        if toonId in self.toons:
            self.joiningToons.remove(toonId)
            self.pendingToons.append(toonId)

        self.d_setMembers()
        self.needAdjust = True
        self._requestAdjust()

    def __handleUnexpectedExit(self, avId):
        disconnectCode = self.air.getAvatarDisconnectReason(avId)
        userAborted = disconnectCode == DisconnectCloseWindow
        self._removeToon(avId, userAborted)

    def _removeToon(self, toonId, userAborted=False):
        if toonId not in self.toons:
            return
        self.battleCalc.toonLeftBattle(toonId)
        self._removeAvatarTasks(toonId)
        self.toons.remove(toonId)

        if self.state == 'PlayMovie':
            self.exitedToons.append(toonId)

        if toonId in self.joiningToons:
            self.joiningToons.remove(toonId)

            if toonId in self.joinBarriers:
                self.joinBarriers[toonId].cleanup()
                del self.joinBarriers[toonId]

        if toonId in self.pendingToons:
            self.pendingToons.remove(toonId)
        if toonId in self.activeToons:
            position = self.activeToons.index(toonId)

            for suitAttack in self.suitAttacks:
                if position < len(suitAttack.hps):
                    del suitAttack.hps[position]

                    targetIndex = suitAttack.target
                    if targetIndex == position:
                        suitAttack.target = -1
                    elif targetIndex > position:
                        suitAttack.target = targetIndex - 1

            self.activeToons.remove(toonId)

        if toonId in self.runningToons:
            self.runningToons.remove(toonId)

        if toonId in self.adjustingToons:
            self.adjustingToons.remove(toonId)

        # TODO
        # if self.pets.has_key(toonId):
        #     self.pets[toonId].requestDelete()
        #     del self.pets[toonId]

        if self._barrier is not None and self._barrier.active:
            self._barrier.clear(toonId)

        event = self.air.getAvatarExitEvent(toonId)
        self.avatarExitEvents.remove(event)
        self.ignore(event)

        toon = self.air.doTable.get(toonId)

        if toon:
            toon.b_setBattleId(0)

        # TODO
        # if not userAborted:
        #     toon = self.getToon(toonId)
        #     if toon != None:
        #         toon.hpOwnedByBattle = 0
        #         toon.d_setHp(toon.hp)
        #         toon.d_setInventory(toon.inventory.makeNetString())
        #         self.air.cogPageManager.toonEncounteredCogs(toon, self.suitsEncountered, self.getTaskZoneId())
        # else:
        #     if len(self.suits) > 0 and not self.streetBattle:
        #         self.notify.info('toon %d aborted non-street battle; clearing inventory and hp.' % toonId)
        #         toon = DistributedToonAI.DistributedToonAI(self.air)
        #         toon.doId = toonId
        #         empty = InventoryBase.InventoryBase(toon)
        #         toon.b_setInventory(empty.makeNetString())
        #         toon.b_setHp(0)
        #         db = DatabaseObject.DatabaseObject(self.air, toonId)
        #         db.storeObject(toon, ['setInventory', 'setHp'])
        #         self.notify.info('killing mem leak from temporary DistributedToonAI %d' % toonId)
        #         toon.deleteDummy()

        self.d_setMembers()

        if self.toons:
            self.needAdjust = True
            self._requestAdjust()

    def _removeAvatarTasks(self, toonId):
        taskName = self.uniqueName('to-pending-av-%d' % toonId)
        taskMgr.remove(taskName)

    def suitCanJoin(self):
        return len(self.suits) < self.maxSuits and self.joinable

    def toonCanJoin(self):
        return len(self.toons) < 4 and self.joinable

    def joinDone(self, joiningDoId):
        senderId = self.air.currentAvatarSender

        barrier = self.joinBarriers.get(joiningDoId)
        if barrier is not None:
            barrier.clear(senderId)

    def suitRequestJoin(self, suit):
        if self.suitCanJoin():
            self.addSuit(suit)
            self.d_setMembers()
            suit.prepareToJoinBattle()
            return 1

    def addSuit(self, suit, joining=True):
        self.suits.append(suit)
        self.numSuitsEver += 1
        if joining:
            self.joiningSuits.append(suit)
            toPendingTime = MAX_JOIN_T + SERVER_BUFFER_TIME
            suitId = suit.do_id
            self.joinBarriers[suitId] = ToonBarrier('to-pending-av-%d' % suitId, self.toons, toPendingTime, self._serverSuitJoinDone,
                                                    extraArgs=[suitId, ])

    def _serverSuitJoinDone(self, avIds, suitId):
        barrier = self.joinBarriers[suitId]
        if barrier.active:
            barrier.cleanup()

        del self.joinBarriers[suitId]
        self._makeSuitPending(suitId)

    def _makeSuitPending(self, suitId):
        suit = self.getSuit(suitId)
        if suit is not None:
            self.joiningSuits.remove(suit)
            self.pendingSuits.append(suit)

        self.d_setMembers()
        self.needAdjust = True
        self._requestAdjust()


from direct.task import Task


class DistributedBattleAI(DistributedBattleBaseAI):

    def __init__(self, air, pos, suit, toonId, zoneId, finishCallback=None):
        DistributedBattleBaseAI.__init__(self, air, finishCallback)
        self.zoneId = zoneId

        self.initialSuitPos = suit.confrontPos
        self.initialToonPos = suit.confrontPos
        self.faceoffTask: str = self.uniqueName('faceoff-timeout', useDoId=False)

        self.pos = pos
        self.initialAvId = toonId
        self.initialSuit = suit

        toon = self.air.doTable[toonId]
        self.addToon(toon, joining=False)
        self.addSuit(self.initialSuit, joining=False)

        self.demand('FaceOff')

    def generate(self):
        DistributedBattleBaseAI.generate(self)

        toon = self.air.doTable.get(self.initialAvId)
        if toon:
            toon.b_setBattleId(self.do_id)

    def enterFaceOff(self):
        self.joinable = True
        self.runnable = False
        self.suits[0].prepareToJoinBattle()

        timeForFaceoff = calcFaceoffTime(self.pos, self.initialSuitPos) + FACEOFF_TAUNT_T + SERVER_BUFFER_TIME
        # if self.interactivePropTrackBonus >= 0:
        #     timeForFaceoff += FACEOFF_LOOK_AT_PROP_T
        taskMgr.doMethodLater(timeForFaceoff, self.handleFaceOffDone, self.faceoffTask)

    def exitFaceOff(self):
        taskMgr.remove(self.faceoffTask)

    def faceOffDone(self):
        avId = self.air.currentAvatarSender

        if avId not in self.toons:
            return

        if self.state != 'FaceOff':
            return

        taskMgr.remove(self.faceoffTask)

        self.handleFaceOffDone()

    def handleFaceOffDone(self, task=None):
        self.activeSuits.append(self.suits[0])
        if len(self.toons) == 0:
            self.demand('Resume')
        else:
            if self.initialAvId == self.toons[0]:
                self.activeToons.append(self.toons[0])
                # self.sendEarnedExperience(self.toons[0])
        self.d_setMembers()
        self.demand('WaitForInput')

        return Task.done

    def localMovieDone(self, deadToons, deadSuits, lastActiveSuitDied):
        if not self.toons:
            self.d_setMembers()
            self.demand('Resume')
        else:
            if not self.suits:
                # for toonId in self.activeToons:
                #     toon = self.getToon(toonId)
                #     if toon:
                #         self.toonItems[toonId] = self.air.questManager.recoverItems(toon, self.suitsKilled, self.zoneId)
                #         if toonId in self.helpfulToons:
                #             self.toonMerits[toonId] = self.air.promotionMgr.recoverMerits(toon, self.suitsKilled, self.zoneId)

                self.d_setMembers()
                # self.d_setBattleExperience()
                self.demand('Reward')
            else:
                self.d_setMembers()
                if len(deadSuits) and not lastActiveSuitDied or len(deadToons):
                    self.needAdjust = True
                self.demand('WaitForJoin')
