from ai.DistributedNodeAI import DistributedNodeAI


class DistributedNPCToonBaseAI(DistributedNodeAI):
    def __init__(self, air, npcId, name=None):
        DistributedNodeAI.__init__(self, air, name)

        self.npcId = npcId
        self.hq = False
        self.name = name
        self.dna = ''
        self.index = 0

    def getName(self):
        return self.name

    def getDNAString(self):
        return self.dna

    def getPositionIndex(self):
        return self.index

    def d_setAnimState(self, animName, playRate):
        timestamp = globalClockDelta.getRealNetworkTime()
        self.sendUpdate('setAnimState', [animName, playRate, timestamp])

    def setPageNumber(self, paragraph, pageNumber, timestamp):
        pass

    def avatarEnter(self):
        sender = self.air.currentAvatarSender
        self.sendUpdateToAvatar(sender, 'freeAvatar', [])


class DistributedNPCToonAI(DistributedNPCToonBaseAI):
    def setMovieDone(self):
        pass

    def chooseQuest(self, choice):
        pass

    def chooseTrack(self, choice):
        pass


class DistributedNPCSpecialQuestGiverAI(DistributedNPCToonBaseAI):
    def setMovieDone(self):
        pass

    def chooseQuest(self, choice):
        pass

    def chooseTrack(self, choice):
        pass


class DistributedNPCClerkAI(DistributedNPCToonBaseAI):
    def setInventory(self, inventory, money, done):
        pass


class DistributedNPCTailorAI(DistributedNPCToonBaseAI):
    def setDNA(self, dna, finished, which):
        pass


class DistributedNPCFishermanAI(DistributedNPCToonBaseAI):
    def completeSale(self, sell: bool):
        pass


class DistributedNPCPartyPersonAI(DistributedNPCToonBaseAI):
    def answer(self, plan: bool):
        pass


class DistributedNPCPetclerkAI(DistributedNPCToonBaseAI):
    def petAdopted(self, whichPet, nameIndex):
        pass

    def petReturned(self):
        pass

    def fishSold(self):
        pass

    def transactionDone(self):
        pass


class DistributedNPCKartClerkAI(DistributedNPCToonBaseAI):
    def buyKart(self, kart):
        pass

    def buyAccessory(self, accessory):
        pass

    def transactionDone(self):
        pass


class DistributedNPCFlippyInToonHallAI(DistributedNPCToonAI):
    pass


class DistributedNPCScientistAI(DistributedNPCToonBaseAI):
    pass
