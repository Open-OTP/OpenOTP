DEFAULT_TOON = {
    # From DistAvatarAI
    "setName": ('Toon',),

    # From DistPlayerAI
    "setAccountName": ('',),
    "setFriendsList": ([],),
    "setDISLId": (0,),
    "setPreviousAccess": (2,),
    "setAccess": (2,),
    "setAsGM": (False,),

    "setDNAString": ('t\x1b\x01\x01\x01\x12\x05\x0c\x05\x03\x05\x10\x00\x12\x11',),
    "setGM": (False,),
    "setMaxBankMoney": (1000,),
    "setBankMoney": (0,),
    "setMaxMoney": (0,),
    "setMoney": (0,),
    "setMaxHp": (15,),
    "setHp": (15,),
    "setBattleId": (0,),
    "setExperience": (b'\x00\x00' * 7,),
    "setMaxCarry": (20,),
    "setTrackAccess": ([0, 0, 0, 0, 1, 1, 0],),
    "setTrackProgress": (0, 0,),
    "setTrackBonusLevel": ([0, 0, 0, 0, 0, 0, 0],),
    "setInventory": (b'\x00' * 49,),
    "setMaxNPCFriends": (8,),
    "setNPCFriendsDict": ([],),
    "setDefaultShard": (0,),
    "setDefaultZone": (2000,),
    "setShtickerBook": (b'',),
    "setZonesVisited": ([],),
    "setHoodsVisited": ([],),
    "setInterface": (b'',),
    "setLastHood": (0,),
    "setTutorialAck": (1,),
    "setMaxClothes": (0,),
    "setClothesTopsList": ([],),
    "setClothesBottomsList": ([],),
    "setMaxAccessories": (0,),
    "setHatList": ([],),
    "setGlassesList": ([],),
    "setBackpackList": ([],),
    "setShoesList": ([],),
    "setHat": (0, 0, 0,),
    "setGlasses": (0, 0, 0,),
    "setBackpack": (0, 0, 0,),
    "setShoes": (0, 0, 0,),
    "setGardenSpecials": ([],),
    "setEmoteAccess": ([1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],),
    "setCustomMessages": ([],),
    "setResistanceMessages": ([],),
    "setPetTrickPhrases": ([],),
    "setCatalogSchedule": (0, 0,),
    "setCatalog": (b'', b'', b'',),
    "setMailboxContents": (b'',),
    "setDeliverySchedule": (b'',),
    "setGiftSchedule": (b'',),
    "setAwardMailboxContents": (b'',),
    "setAwardSchedule": (b'',),
    "setAwardNotify": (0,),
    "setCatalogNotify": (0, 0,),
    "setSpeedChatStyleIndex": (1,),
    "setTeleportAccess": ([],),
    "setCogStatus": ([0] * 32,),
    "setCogCount": ([0] * 32,),
    "setCogRadar": ([0] * 4,),
    "setBuildingRadar": ([0] * 4,),
    "setCogLevels": ([0] * 4,),
    "setCogTypes": ([0] * 4,),
    "setCogParts": ([0] * 4,),
    "setCogMerits": ([0] * 4,),
    "setHouseId": (0,),
    "setQuests": ([],),
    "setQuestHistory": ([],),
    "setRewardHistory": (0, [],),
    "setQuestCarryLimit": (1,),
    "setCheesyEffect": (0, 0, 0,),
    "setPosIndex": (0,),
    "setFishCollection": ([], [], [],),
    "setMaxFishTank": (20,),
    "setFishTank": ([], [], [],),
    "setFishingRod": (0,),
    "setFishingTrophies": ([],),
    "setFlowerCollection": ([], [],),
    "setFlowerBasket": ([], [],),
    "setMaxFlowerBasket": (20,),
    "setGardenTrophies": ([],),
    "setShovel": (0,),
    "setShovelSkill": (0,),
    "setWateringCan": (0,),
    "setWateringCanSkill": (0,),
    "setPetId": (0,),
    "setPetTutorialDone": (0,),
    "setFishBingoTutorialDone": (0,),
    "setFishBingoMarkTutorialDone": (0,),
    "setKartBodyType": (-1,),
    "setKartBodyColor": (-1,),
    "setKartAccessoryColor": (-1,),
    "setKartEngineBlockType": (-1,),
    "setKartSpoilerType": (-1,),
    "setKartFrontWheelWellType": (-1,),
    "setKartBackWheelWellType": (-1,),
    "setKartRimType": (-1,),
    "setKartDecalType": (-1,),
    "setTickets": (200,),
    "setKartingHistory": ([0] * 16,),
    "setKartingTrophies": ([0] * 33,),
    "setKartingPersonalBest": ([0] * 6,),
    "setKartingPersonalBest2": ([0] * 12,),
    "setKartAccessoriesOwned": ([0] * 16,),
    "setCogSummonsEarned": ([0] * 32,),
    "setGardenStarted": (0,),
    "setGolfHistory": ([0] * 18,),
    "setPackedGolfHoleBest": ([0] * 18,),
    "setGolfCourseBest": ([0] * 3,),
    "setPinkSlips": (0,),
    "setNametagStyle": (0,),
}


def getPuppetChannel(avatarId: int) -> int:
    """Returns the channel for the associated avatar id."""
    return avatarId + (1001 << 32)


def getAccountChannel(dislId: int) -> int:
    """Returns the channel for the associated DISL id."""
    return dislId + (1003 << 32)


def getClientSenderChannel(dislId: int, avatarId: int) -> int:
    """
    Returns the channel for the associated DISL id and avatar id.
    This is the sender channel the client agent will use for authenticated clients.
    """
    return dislId << 32 | avatarId


def getAccountIDFromChannel(sender: int) -> int:
    """Returns the account/disl id from a client agent sender channel."""
    return sender >> 32


def getAvatarIDFromChannel(sender: int) -> int:
    """Returns the avatar id (if present) from a client agent sender channel."""
    return sender & 0xFFFFFFFF
