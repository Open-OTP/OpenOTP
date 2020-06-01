import random
from enum import IntEnum, Enum
from typing import Tuple, NamedTuple

from itertools import islice


class SuitDept(IntEnum):
    def __new__(cls, value, char):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.char = char
        return obj

    CORPORATE = 0, 'c'
    LAW = 1, 'l'
    MONEY = 2, 'm'
    SELL = 3, 's'




class SuitHeads(Enum):
    def __new__(cls, value):
        index = len(cls.__members__)
        obj = object.__new__(cls)
        obj._value_ = value
        obj.index = index
        return obj

    def __int__(self):
        return self.index

    @classmethod
    def at(cls, i: int) -> 'SuitHeads':
        try:
            return next(islice(cls.__members__.values(), i, None))
        except StopIteration:
            raise IndexError

    FLUNKY = 'f'
    PENCIL_PUSHER = 'p'
    YESMAN = 'ym'
    MICROMANAGER = 'mm'
    DOWNSIZER = 'ds'
    HEAD_HUNTER = 'hh'
    CORPORATE_RAIDER = 'cr'
    THE_BIG_CHEESE = 'tbc'

    BOTTOM_FEEDER = 'bf'
    BLOODSUCKER = 'b'
    DOUBLE_TALKER = 'dt'
    AMBULANCE_CHASER = 'ac'
    BACK_STABBER = 'bs'
    SPIN_DOCTOR = 'sd'
    LEGAL_EAGLE = 'le'
    BIG_WIG = 'bw'

    SHORT_CHANGE = 'sc'
    PENNY_PINCHER = 'pp'
    TIGHTWAD = 'tw'
    BEAN_COUNTER = 'bc'
    NUMBER_CRUNCHER = 'nc'
    MONEY_BAGS = 'mb'
    LOAN_SHARK = 'ls'
    ROBBER_BARON = 'rb'

    COLD_CALLER = 'cc'
    TELEMARKETER = 'tm'
    NAME_DROPPER = 'nd'
    GLAD_HANDER = 'gh'
    MOVER_SHAKER = 'ms'
    TWO_FACE = 'tf'
    MINGLER = 'm'
    MR_HOLLYWOOD = 'mh'


class SuitAttackInfo(NamedTuple):
    name: str
    damages: Tuple[int, ...]
    accuracies: Tuple[int, ...]
    frequencies: Tuple[int, ...]


class SuitAttribute(NamedTuple):
    level: int
    hps: Tuple[int, ...]
    defenses: Tuple[int, ...]
    attacks: Tuple[SuitAttackInfo, ...]


SuitAttributes = {
    SuitHeads.FLUNKY: SuitAttribute(
        level=0, hps=(6, 12, 20, 30, 42), defenses=(2, 5, 10, 12, 15),
        attacks=(
            SuitAttackInfo('PoundKey', damages=(2, 2, 3, 4, 6), accuracies=(75, 75, 80, 80, 90), frequencies=(30, 35, 40, 45, 50)),
            SuitAttackInfo('Shred', damages=(3, 4, 5, 6, 7), accuracies=(50, 55, 60, 65, 70), frequencies=(10, 15, 20, 25, 30)),
            SuitAttackInfo('ClipOnTie', damages=(1, 1, 2, 2, 3), accuracies=(75, 80, 85, 90, 95), frequencies=(60, 50, 40, 30, 20)),
        )
    ),


    SuitHeads.PENCIL_PUSHER: SuitAttribute(
        level=1, hps=(12, 20, 30, 42, 56), defenses=(5, 10, 15, 20, 25),
        attacks=(
            SuitAttackInfo('FountainPen', damages=(2, 3, 4, 6, 9), accuracies=(75, 75, 75, 75, 75), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('RubOut', damages=(4, 5, 6, 8, 12), accuracies=(75, 75, 75, 75, 75), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('FingerWag', damages=(1, 2, 2, 3, 4), accuracies=(75, 75, 75, 75, 75), frequencies=(35, 30, 25, 20, 15)),
            SuitAttackInfo('WriteOff', damages=(4, 6, 8, 10, 12), accuracies=(75, 75, 75, 75, 75), frequencies=(5, 10, 15, 20, 25)),
            SuitAttackInfo('FillWithLead', damages=(3, 4, 5, 6, 7), accuracies=(75, 75, 75, 75, 75), frequencies=(20, 20, 20, 20, 20)),
        )
    ),


    SuitHeads.YESMAN: SuitAttribute(
        level=2, hps=(20, 30, 42, 56, 72), defenses=(10, 15, 20, 25, 30),
        attacks=(
            SuitAttackInfo('RubberStamp', damages=(2, 2, 3, 3, 4), accuracies=(75, 75, 75, 75, 75), frequencies=(35, 35, 35, 35, 35)),
            SuitAttackInfo('RazzleDazzle', damages=(1, 1, 1, 1, 1), accuracies=(50, 50, 50, 50, 50), frequencies=(25, 20, 15, 10, 5)),
            SuitAttackInfo('Synergy', damages=(4, 5, 6, 7, 8), accuracies=(50, 60, 70, 80, 90), frequencies=(5, 10, 15, 20, 25)),
            SuitAttackInfo('TeeOff', damages=(3, 3, 4, 4, 5), accuracies=(50, 60, 70, 80, 90), frequencies=(35, 35, 35, 35, 35)),
        )
    ),


    SuitHeads.MICROMANAGER: SuitAttribute(
        level=3, hps=(30, 42, 56, 72, 90), defenses=(15, 20, 25, 30, 35),
        attacks=(
            SuitAttackInfo('Demotion', damages=(6, 8, 12, 15, 18), accuracies=(50, 60, 70, 80, 90), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('FingerWag', damages=(4, 6, 9, 12, 15), accuracies=(50, 60, 70, 80, 90), frequencies=(10, 10, 10, 10, 10)),
            SuitAttackInfo('FountainPen', damages=(3, 4, 6, 8, 10), accuracies=(50, 60, 70, 80, 90), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('BrainStorm', damages=(4, 6, 9, 12, 15), accuracies=(5, 5, 5, 5, 5), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('BuzzWord', damages=(4, 6, 9, 12, 15), accuracies=(50, 60, 70, 80, 90), frequencies=(20, 20, 20, 20, 20)),
        )
    ),


    SuitHeads.DOWNSIZER: SuitAttribute(
        level=4, hps=(42, 56, 72, 90, 110), defenses=(20, 25, 30, 35, 40),
        attacks=(
            SuitAttackInfo('Canned', damages=(5, 6, 8, 10, 12), accuracies=(60, 75, 80, 85, 90), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('Downsize', damages=(8, 9, 11, 13, 15), accuracies=(50, 65, 70, 75, 80), frequencies=(35, 35, 35, 35, 35)),
            SuitAttackInfo('PinkSlip', damages=(4, 5, 6, 7, 8), accuracies=(60, 65, 75, 80, 85), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('Sacked', damages=(5, 6, 7, 8, 9), accuracies=(50, 50, 50, 50, 50), frequencies=(15, 15, 15, 15, 15)),
        )
    ),


    SuitHeads.HEAD_HUNTER: SuitAttribute(
        level=5, hps=(56, 72, 90, 110, 132), defenses=(25, 30, 35, 40, 45),
        attacks=(
            SuitAttackInfo('FountainPen', damages=(5, 6, 8, 10, 12), accuracies=(60, 75, 80, 85, 90), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('GlowerPower', damages=(7, 8, 10, 12, 13), accuracies=(50, 60, 70, 80, 90), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('HalfWindsor', damages=(8, 10, 12, 14, 16), accuracies=(60, 65, 70, 75, 80), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('HeadShrink', damages=(10, 12, 15, 18, 21), accuracies=(65, 75, 80, 85, 95), frequencies=(35, 35, 35, 35, 35)),
            SuitAttackInfo('Rolodex', damages=(6, 7, 8, 9, 10), accuracies=(60, 65, 70, 75, 80), frequencies=(10, 10, 10, 10, 10)),
        )
    ),


    SuitHeads.CORPORATE_RAIDER: SuitAttribute(
        level=6, hps=(72, 90, 110, 132, 156), defenses=(30, 35, 40, 45, 50),
        attacks=(
            SuitAttackInfo('Canned', damages=(6, 7, 8, 9, 10), accuracies=(60, 75, 80, 85, 90), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('EvilEye', damages=(12, 15, 18, 21, 24), accuracies=(60, 70, 75, 80, 90), frequencies=(35, 35, 35, 35, 35)),
            SuitAttackInfo('PlayHardball', damages=(7, 8, 12, 15, 16), accuracies=(60, 65, 70, 75, 80), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('PowerTie', damages=(10, 12, 14, 16, 18), accuracies=(65, 75, 80, 85, 95), frequencies=(15, 15, 15, 15, 15)),
        )
    ),


    SuitHeads.THE_BIG_CHEESE: SuitAttribute(
        level=7, hps=(90, 110, 132, 156, 200), defenses=(35, 40, 45, 50, 55),
        attacks=(
            SuitAttackInfo('CigarSmoke', damages=(10, 12, 15, 18, 20), accuracies=(55, 65, 75, 85, 95), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('FloodTheMarket', damages=(14, 16, 18, 20, 22), accuracies=(70, 75, 85, 90, 95), frequencies=(10, 10, 10, 10, 10)),
            SuitAttackInfo('SongAndDance', damages=(14, 15, 17, 19, 20), accuracies=(60, 65, 70, 75, 80), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('TeeOff', damages=(8, 11, 14, 17, 20), accuracies=(55, 65, 70, 75, 80), frequencies=(50, 50, 50, 50, 50)),
        )
    ),


    SuitHeads.BOTTOM_FEEDER: SuitAttribute(
        level=0, hps=(6, 12, 20, 30, 42), defenses=(2, 5, 10, 12, 15),
        attacks=(
            SuitAttackInfo('RubberStamp', damages=(2, 3, 4, 5, 6), accuracies=(75, 80, 85, 90, 95), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('Shred', damages=(2, 4, 6, 8, 10), accuracies=(50, 55, 60, 65, 70), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('Watercooler', damages=(3, 4, 5, 6, 7), accuracies=(95, 95, 95, 95, 95), frequencies=(10, 10, 10, 10, 10)),
            SuitAttackInfo('PickPocket', damages=(1, 1, 2, 2, 3), accuracies=(25, 30, 35, 40, 45), frequencies=(50, 50, 50, 50, 50)),
        )
    ),


    SuitHeads.BLOODSUCKER: SuitAttribute(
        level=1, hps=(12, 20, 30, 42, 56), defenses=(5, 10, 15, 20, 25),
        attacks=(
            SuitAttackInfo('EvictionNotice', damages=(1, 2, 3, 3, 4), accuracies=(75, 75, 75, 75, 75), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('RedTape', damages=(2, 3, 4, 6, 9), accuracies=(75, 75, 75, 75, 75), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('Withdrawal', damages=(6, 8, 10, 12, 14), accuracies=(95, 95, 95, 95, 95), frequencies=(10, 10, 10, 10, 10)),
            SuitAttackInfo('Liquidate', damages=(2, 3, 4, 6, 9), accuracies=(50, 60, 70, 80, 90), frequencies=(50, 50, 50, 50, 50)),
        )
    ),


    SuitHeads.DOUBLE_TALKER: SuitAttribute(
        level=2, hps=(20, 30, 42, 56, 72), defenses=(10, 15, 20, 25, 30),
        attacks=(
            SuitAttackInfo('RubberStamp', damages=(1, 1, 1, 1, 1), accuracies=(50, 60, 70, 80, 90), frequencies=(5, 5, 5, 5, 5)),
            SuitAttackInfo('BounceCheck', damages=(1, 1, 1, 1, 1), accuracies=(50, 60, 70, 80, 90), frequencies=(5, 5, 5, 5, 5)),
            SuitAttackInfo('BuzzWord', damages=(1, 2, 3, 5, 6), accuracies=(50, 60, 70, 80, 90), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('DoubleTalk', damages=(6, 6, 9, 13, 18), accuracies=(50, 60, 70, 80, 90), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('Jargon', damages=(3, 4, 6, 9, 12), accuracies=(50, 60, 70, 80, 90), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('MumboJumbo', damages=(3, 4, 6, 9, 12), accuracies=(50, 60, 70, 80, 90), frequencies=(20, 20, 20, 20, 20)),
        )
    ),


    SuitHeads.AMBULANCE_CHASER: SuitAttribute(
        level=3, hps=(30, 42, 56, 72, 90), defenses=(15, 20, 25, 30, 35),
        attacks=(
            SuitAttackInfo('Shake', damages=(4, 6, 9, 12, 15), accuracies=(75, 75, 75, 75, 75), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('RedTape', damages=(6, 8, 12, 15, 19), accuracies=(75, 75, 75, 75, 75), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('Rolodex', damages=(3, 4, 5, 6, 7), accuracies=(75, 75, 75, 75, 75), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('HangUp', damages=(2, 3, 4, 5, 6), accuracies=(75, 75, 75, 75, 75), frequencies=(35, 35, 35, 35, 35)),
        )
    ),


    SuitHeads.BACK_STABBER: SuitAttribute(
        level=4, hps=(42, 56, 72, 90, 110), defenses=(20, 25, 30, 35, 40),
        attacks=(
            SuitAttackInfo('GuiltTrip', damages=(8, 11, 13, 15, 18), accuracies=(60, 75, 80, 85, 90), frequencies=(40, 40, 40, 40, 40)),
            SuitAttackInfo('RestrainingOrder', damages=(6, 7, 9, 11, 13), accuracies=(50, 65, 70, 75, 90), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('FingerWag', damages=(5, 6, 7, 8, 9), accuracies=(50, 55, 65, 75, 80), frequencies=(35, 35, 35, 35, 35)),
        )
    ),


    SuitHeads.SPIN_DOCTOR: SuitAttribute(
        level=5, hps=(56, 72, 90, 110, 132), defenses=(25, 30, 35, 40, 45),
        attacks=(
            SuitAttackInfo('ParadigmShift', damages=(9, 10, 13, 16, 17), accuracies=(60, 75, 80, 85, 90), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('Quake', damages=(8, 10, 12, 14, 16), accuracies=(60, 65, 70, 75, 80), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('Spin', damages=(10, 12, 15, 18, 20), accuracies=(70, 75, 80, 85, 90), frequencies=(35, 35, 35, 35, 35)),
            SuitAttackInfo('WriteOff', damages=(6, 7, 8, 9, 10), accuracies=(60, 65, 75, 85, 90), frequencies=(15, 15, 15, 15, 15)),
        )
    ),


    SuitHeads.LEGAL_EAGLE: SuitAttribute(
        level=6, hps=(72, 90, 110, 132, 156), defenses=(30, 35, 40, 45, 50),
        attacks=(
            SuitAttackInfo('EvilEye', damages=(10, 11, 13, 15, 16), accuracies=(60, 75, 80, 85, 90), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('Jargon', damages=(7, 9, 11, 13, 15), accuracies=(60, 70, 75, 80, 90), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('Legalese', damages=(11, 13, 16, 19, 21), accuracies=(55, 65, 75, 85, 95), frequencies=(35, 35, 35, 35, 35)),
            SuitAttackInfo('PeckingOrder', damages=(12, 15, 17, 19, 22), accuracies=(70, 75, 80, 85, 95), frequencies=(30, 30, 30, 30, 30)),
        )
    ),


    SuitHeads.BIG_WIG: SuitAttribute(
        level=7, hps=(90, 110, 132, 156, 200), defenses=(35, 40, 45, 50, 55),
        attacks=(
            SuitAttackInfo('PowerTrip', damages=(10, 11, 13, 15, 16), accuracies=(75, 80, 85, 90, 95), frequencies=(50, 50, 50, 50, 50)),
            SuitAttackInfo('ThrowBook', damages=(13, 15, 17, 19, 21), accuracies=(80, 85, 85, 85, 90), frequencies=(50, 50, 50, 50, 50)),
        )
    ),


    SuitHeads.SHORT_CHANGE: SuitAttribute(
        level=0, hps=(6, 12, 20, 30, 42), defenses=(2, 5, 10, 12, 15),
        attacks=(
            SuitAttackInfo('Watercooler', damages=(2, 2, 3, 4, 6), accuracies=(50, 50, 50, 50, 50), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('BounceCheck', damages=(3, 5, 7, 9, 11), accuracies=(75, 80, 85, 90, 95), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('ClipOnTie', damages=(1, 1, 2, 2, 3), accuracies=(50, 50, 50, 50, 50), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('PickPocket', damages=(2, 2, 3, 4, 6), accuracies=(95, 95, 95, 95, 95), frequencies=(40, 40, 40, 40, 40)),
        )
    ),


    SuitHeads.PENNY_PINCHER: SuitAttribute(
        level=1, hps=(12, 20, 30, 42, 56), defenses=(5, 10, 15, 20, 25),
        attacks=(
            SuitAttackInfo('BounceCheck', damages=(4, 5, 6, 8, 12), accuracies=(75, 75, 75, 75, 75), frequencies=(45, 45, 45, 45, 45)),
            SuitAttackInfo('FreezeAssets', damages=(2, 3, 4, 6, 9), accuracies=(75, 75, 75, 75, 75), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('FingerWag', damages=(1, 2, 3, 4, 6), accuracies=(50, 50, 50, 50, 50), frequencies=(35, 35, 35, 35, 35)),
        )
    ),


    SuitHeads.TIGHTWAD: SuitAttribute(
        level=2, hps=(20, 30, 42, 56, 72), defenses=(10, 15, 20, 25, 30),
        attacks=(
            SuitAttackInfo('Fired', damages=(3, 4, 5, 5, 6), accuracies=(75, 75, 75, 75, 75), frequencies=(75, 5, 5, 5, 5)),
            SuitAttackInfo('GlowerPower', damages=(3, 4, 6, 9, 12), accuracies=(95, 95, 95, 95, 95), frequencies=(10, 15, 20, 25, 30)),
            SuitAttackInfo('FingerWag', damages=(3, 3, 4, 4, 5), accuracies=(75, 75, 75, 75, 75), frequencies=(5, 70, 5, 5, 5)),
            SuitAttackInfo('FreezeAssets', damages=(3, 4, 6, 9, 12), accuracies=(75, 75, 75, 75, 75), frequencies=(5, 5, 65, 5, 30)),
            SuitAttackInfo('BounceCheck', damages=(5, 6, 9, 13, 18), accuracies=(75, 75, 75, 75, 75), frequencies=(5, 5, 5, 60, 30)),
        )
    ),


    SuitHeads.BEAN_COUNTER: SuitAttribute(
        level=3, hps=(30, 42, 56, 72, 90), defenses=(15, 20, 25, 30, 35),
        attacks=(
            SuitAttackInfo('Audit', damages=(4, 6, 9, 12, 15), accuracies=(95, 95, 95, 95, 95), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('Calculate', damages=(4, 6, 9, 12, 15), accuracies=(75, 75, 75, 75, 75), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('Tabulate', damages=(4, 6, 9, 12, 15), accuracies=(75, 75, 75, 75, 75), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('WriteOff', damages=(4, 6, 9, 12, 15), accuracies=(95, 95, 95, 95, 95), frequencies=(30, 30, 30, 30, 30)),
        )
    ),


    SuitHeads.NUMBER_CRUNCHER: SuitAttribute(
        level=4, hps=(42, 56, 72, 90, 110), defenses=(20, 25, 30, 35, 40),
        attacks=(
            SuitAttackInfo('Audit', damages=(5, 6, 8, 10, 12), accuracies=(60, 75, 80, 85, 90), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('Calculate', damages=(6, 7, 9, 11, 13), accuracies=(50, 65, 70, 75, 80), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('Crunch', damages=(8, 9, 11, 13, 15), accuracies=(60, 65, 75, 80, 85), frequencies=(35, 35, 35, 35, 35)),
            SuitAttackInfo('Tabulate', damages=(5, 6, 7, 8, 9), accuracies=(50, 50, 50, 50, 50), frequencies=(20, 20, 20, 20, 20)),
        )
    ),


    SuitHeads.MONEY_BAGS: SuitAttribute(
        level=5, hps=(56, 72, 90, 110, 132), defenses=(25, 30, 35, 40, 45),
        attacks=(
            SuitAttackInfo('Liquidate', damages=(10, 12, 14, 16, 18), accuracies=(60, 75, 80, 85, 90), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('MarketCrash', damages=(8, 10, 12, 14, 16), accuracies=(60, 65, 70, 75, 80), frequencies=(45, 45, 45, 45, 45)),
            SuitAttackInfo('PowerTie', damages=(6, 7, 8, 9, 10), accuracies=(60, 65, 75, 85, 90), frequencies=(25, 25, 25, 25, 25)),
        )
    ),


    SuitHeads.LOAN_SHARK: SuitAttribute(
        level=6, hps=(72, 90, 110, 132, 156), defenses=(30, 35, 40, 45, 50),
        attacks=(
            SuitAttackInfo('Bite', damages=(10, 11, 13, 15, 16), accuracies=(60, 75, 80, 85, 90), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('Chomp', damages=(12, 15, 18, 21, 24), accuracies=(60, 70, 75, 80, 90), frequencies=(35, 35, 35, 35, 35)),
            SuitAttackInfo('PlayHardball', damages=(9, 11, 12, 13, 15), accuracies=(55, 65, 75, 85, 95), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('WriteOff', damages=(6, 8, 10, 12, 14), accuracies=(70, 75, 80, 85, 95), frequencies=(15, 15, 15, 15, 15)),
        )
    ),


    SuitHeads.ROBBER_BARON: SuitAttribute(
        level=7, hps=(90, 110, 132, 156, 200), defenses=(35, 40, 45, 50, 55),
        attacks=(
            SuitAttackInfo('PowerTrip', damages=(11, 14, 16, 18, 21), accuracies=(60, 65, 70, 75, 80), frequencies=(50, 50, 50, 50, 50)),
            SuitAttackInfo('TeeOff', damages=(10, 12, 14, 16, 18), accuracies=(60, 65, 75, 85, 90), frequencies=(50, 50, 50, 50, 50)),
        )
    ),


    SuitHeads.COLD_CALLER: SuitAttribute(
        level=0, hps=(6, 12, 20, 30, 42), defenses=(2, 5, 10, 12, 15),
        attacks=(
            SuitAttackInfo('FreezeAssets', damages=(1, 1, 1, 1, 1), accuracies=(90, 90, 90, 90, 90), frequencies=(5, 10, 15, 20, 25)),
            SuitAttackInfo('PoundKey', damages=(2, 2, 3, 4, 5), accuracies=(75, 80, 85, 90, 95), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('DoubleTalk', damages=(2, 3, 4, 6, 8), accuracies=(50, 55, 60, 65, 70), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('HotAir', damages=(3, 4, 6, 8, 10), accuracies=(50, 50, 50, 50, 50), frequencies=(45, 40, 35, 30, 25)),
        )
    ),


    SuitHeads.TELEMARKETER: SuitAttribute(
        level=1, hps=(12, 20, 30, 42, 56), defenses=(5, 10, 15, 20, 25),
        attacks=(
            SuitAttackInfo('ClipOnTie', damages=(2, 2, 3, 3, 4), accuracies=(75, 75, 75, 75, 75), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('PickPocket', damages=(1, 1, 1, 1, 1), accuracies=(75, 75, 75, 75, 75), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('Rolodex', damages=(4, 6, 7, 9, 12), accuracies=(50, 50, 50, 50, 50), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('DoubleTalk', damages=(4, 6, 7, 9, 12), accuracies=(75, 80, 85, 90, 95), frequencies=(40, 40, 40, 40, 40)),
        )
    ),


    SuitHeads.NAME_DROPPER: SuitAttribute(
        level=2, hps=(20, 30, 42, 56, 72), defenses=(10, 15, 20, 25, 30),
        attacks=(
            SuitAttackInfo('RazzleDazzle', damages=(4, 5, 6, 9, 12), accuracies=(75, 80, 85, 90, 95), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('Rolodex', damages=(5, 6, 7, 10, 14), accuracies=(95, 95, 95, 95, 95), frequencies=(40, 40, 40, 40, 40)),
            SuitAttackInfo('Synergy', damages=(3, 4, 6, 9, 12), accuracies=(50, 50, 50, 50, 50), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('PickPocket', damages=(2, 2, 2, 2, 2), accuracies=(95, 95, 95, 95, 95), frequencies=(15, 15, 15, 15, 15)),
        )
    ),


    SuitHeads.GLAD_HANDER: SuitAttribute(
        level=3, hps=(30, 42, 56, 72, 90), defenses=(15, 20, 25, 30, 35),
        attacks=(
            SuitAttackInfo('RubberStamp', damages=(4, 3, 3, 2, 1), accuracies=(90, 70, 50, 30, 10), frequencies=(40, 30, 20, 10, 5)),
            SuitAttackInfo('FountainPen', damages=(3, 3, 2, 1, 1), accuracies=(70, 60, 50, 40, 30), frequencies=(40, 30, 20, 10, 5)),
            SuitAttackInfo('Filibuster', damages=(4, 6, 9, 12, 15), accuracies=(30, 40, 50, 60, 70), frequencies=(10, 20, 30, 40, 45)),
            SuitAttackInfo('Schmooze', damages=(5, 7, 11, 15, 20), accuracies=(55, 65, 75, 85, 95), frequencies=(10, 20, 30, 40, 45)),
        )
    ),


    SuitHeads.MOVER_SHAKER: SuitAttribute(
        level=4, hps=(42, 56, 72, 90, 110), defenses=(20, 25, 30, 35, 40),
        attacks=(
            SuitAttackInfo('BrainStorm', damages=(5, 6, 8, 10, 12), accuracies=(60, 75, 80, 85, 90), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('HalfWindsor', damages=(6, 9, 11, 13, 16), accuracies=(50, 65, 70, 75, 80), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('Quake', damages=(9, 12, 15, 18, 21), accuracies=(60, 65, 75, 80, 85), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('Shake', damages=(6, 8, 10, 12, 14), accuracies=(70, 75, 80, 85, 90), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('Tremor', damages=(5, 6, 7, 8, 9), accuracies=(50, 50, 50, 50, 50), frequencies=(20, 20, 20, 20, 20)),
        )
    ),


    SuitHeads.TWO_FACE: SuitAttribute(
        level=5, hps=(56, 72, 90, 110, 132), defenses=(25, 30, 35, 40, 45),
        attacks=(
            SuitAttackInfo('EvilEye', damages=(10, 12, 14, 16, 18), accuracies=(60, 75, 80, 85, 90), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('HangUp', damages=(7, 8, 10, 12, 13), accuracies=(50, 60, 70, 80, 90), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('RazzleDazzle', damages=(8, 10, 12, 14, 16), accuracies=(60, 65, 70, 75, 80), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('RedTape', damages=(6, 7, 8, 9, 10), accuracies=(60, 65, 75, 85, 90), frequencies=(25, 25, 25, 25, 25)),
        )
    ),


    SuitHeads.MINGLER: SuitAttribute(
        level=6, hps=(72, 90, 110, 132, 156), defenses=(30, 35, 40, 45, 50),
        attacks=(
            SuitAttackInfo('BuzzWord', damages=(10, 11, 13, 15, 16), accuracies=(60, 75, 80, 85, 90), frequencies=(20, 20, 20, 20, 20)),
            SuitAttackInfo('ParadigmShift', damages=(12, 15, 18, 21, 24), accuracies=(60, 70, 75, 80, 90), frequencies=(25, 25, 25, 25, 25)),
            SuitAttackInfo('PowerTrip', damages=(10, 13, 14, 15, 18), accuracies=(60, 65, 70, 75, 80), frequencies=(15, 15, 15, 15, 15)),
            SuitAttackInfo('Schmooze', damages=(7, 8, 12, 15, 16), accuracies=(55, 65, 75, 85, 95), frequencies=(30, 30, 30, 30, 30)),
            SuitAttackInfo('TeeOff', damages=(8, 9, 10, 11, 12), accuracies=(70, 75, 80, 85, 95), frequencies=(10, 10, 10, 10, 10)),
        )
    ),


    SuitHeads.MR_HOLLYWOOD: SuitAttribute(
        level=7, hps=(90, 110, 132, 156, 200), defenses=(35, 40, 45, 50, 55),
        attacks=(
            SuitAttackInfo('PowerTrip', damages=(10, 12, 15, 18, 20), accuracies=(55, 65, 75, 85, 95), frequencies=(50, 50, 50, 50, 50)),
            SuitAttackInfo('RazzleDazzle', damages=(8, 11, 14, 17, 20), accuracies=(70, 75, 85, 90, 95), frequencies=(50, 50, 50, 50, 50)),
        )
    ),
}


def getActualFromRelativeLevel(head: SuitHeads, relLevel: int):
    return SuitAttributes[head].level + relLevel


def pickFromFreqList(freqList):
    randNum = random.randint(0, 99)
    count = 0
    index = 0
    level = None
    for f in freqList:
        count = count + f
        if randNum < count:
            level = index
            break
        index = index + 1

    return level


GROUP_ATTACKS = {
    'GuiltTrip',
    'ParadigmShift',
    'PowerTrip',
    'Quake',
    'Shake',
    'Synergy',
    'Tremor',
}

def suitAttackAffectsGroup(attackName):
    return attackName in GROUP_ATTACKS
