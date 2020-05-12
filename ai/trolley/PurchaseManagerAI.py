from ai.DistributedObjectAI import DistributedObjectAI
from ai.toon.DistributedToonAI import Inventory


from typing import List, Optional

from . import createMinigame, Purchaser, PurchaseState, INVENTORY_PENDING, INVENTORY_DONE


PURCHASE_COUNTDOWN_TIME = 120


class PurchaseManagerAI(DistributedObjectAI):
    def __init__(self, air, purchasers, minigameId, trolleyZone, metagameRound):
        DistributedObjectAI.__init__(self, air)

        self.purchasers: List[Purchaser] = purchasers
        self.minigameId = minigameId
        self.trolleyZone = trolleyZone
        self.metagameRound = metagameRound

        self.receivingButtons = True
        self.shuttingDown = False

    def getPurchaser(self, avId) -> Optional[Purchaser]:
        for purchaser in self.purchasers:
            if purchaser.avId == avId:
                return purchaser
        else:
            return None

    def anyUndecided(self) -> bool:
        for purchaser in self.purchasers:
            if purchaser.state == PurchaseState.WAITING:
                return True
        return False

    def anyInventoryPending(self) -> bool:
        for purchaser in self.purchasers:
            if purchaser.inventoryState == INVENTORY_PENDING:
                return True
        return False

    def getPlayerIds(self):
        return [purchaser.avId for purchaser in self.purchasers]

    def getNewbieIds(self):
        return [purchaser.avId for purchaser in self.purchasers if purchaser.newbie]

    def getMinigamePoints(self):
        return [purchaser.score for purchaser in self.purchasers]

    def getPlayerMoney(self):
        return [purchaser.money for purchaser in self.purchasers]

    def getPlayerStates(self):
        return [purchaser.state for purchaser in self.purchasers]

    def getVotesArray(self):
        return [purchaser.votes for purchaser in self.purchasers]

    def getCountdown(self):
        return globalClockDelta.getRealNetworkTime()

    def getMetagameRound(self):
        return self.metagameRound

    def announceGenerate(self):
        for purchaser in self.purchasers:
            avId = purchaser.avId
            if avId:
                self.acceptOnce(self.air.getAvatarExitEvent(avId), self.__handleUnexpectedExit, extraArgs=[avId])

        self.startCountdown()

    def startCountdown(self):
        taskMgr.doMethodLater(PURCHASE_COUNTDOWN_TIME, self.timesUp, self.uniqueName('timeout'))

    def d_setPlayerStates(self):
        self.sendUpdate('setPlayerStates', self.getPlayerStates())

    def timesUp(self, task=None):
        taskMgr.remove(self.uniqueName('timeout'))

        for purchaser in self.purchasers:
            if purchaser.state == PurchaseState.WAITING:
                purchaser.state = PurchaseState.EXIT

        self.d_setPlayerStates()
        self.receivingButtons = False
        self.sendUpdate('setPurchaseExit', [])

    def requestExit(self):
        avId = self.air.currentAvatarSender
        self.requestState(avId, PurchaseState.EXIT)

    def requestPlayAgain(self):
        avId = self.air.currentAvatarSender
        self.requestState(avId, PurchaseState.PLAY_AGAIN)

    def requestState(self, avId, state):
        purchaser = self.getPurchaser(avId)
        if purchaser is None:
            return

        av = self.air.doTable.get(avId)
        if not av:
            if purchaser:
                purchaser.state = PurchaseState.DISCONNECTED
                purchaser.inventoryState = INVENTORY_DONE
                self.ignore(self.air.getAvatarExitEvent(avId))
                self.d_setPlayerStates()
            return

        if purchaser.state != PurchaseState.PLAY_AGAIN and purchaser.state != PurchaseState.WAITING:
            return

        if not self.receivingButtons:
            return

        purchaser.state = state
        self.d_setPlayerStates()

        if not self.anyUndecided():
            self.timesUp()

    def setInventory(self, blob, newMoney, done):
        avId = self.air.currentAvatarSender

        av = self.air.doTable.get(avId)
        if not av:
            return

        purchaser = self.getPurchaser(avId)
        if purchaser is None:
            return

        newInventory = Inventory.fromBytes(blob)
        newInventory.toon = av
        currentMoney = av.getMoney()

        if not av.inventory.validatePurchase(newInventory, currentMoney, newMoney):
            # Invalid purchase. Send updates to revert the changes on their end.
            print('INVALID PURCHASE', blob, newMoney)
            av.d_setInventory(av.inventory.makeNetString())
            av.d_setMoney(currentMoney)
            return

        av.inventory = newInventory
        av.money = newMoney

        print(purchaser)

        if not done:
            return

        if purchaser.inventoryState == INVENTORY_DONE:
            return

        av.d_setInventory(av.inventory.makeNetString())
        av.d_setMoney(newMoney)

        purchaser.inventoryState = INVENTORY_DONE
        print('ok', self.anyInventoryPending())

        if not self.anyInventoryPending() and not self.shuttingDown:
            self.shutdown()

    def __handleUnexpectedExit(self, avId):
        purchaser = self.getPurchaser(avId)

        if purchaser is None:
            return

        if self.receivingButtons:
            purchaser.state = PurchaseState.DISCONNECTED
            purchaser.inventoryState = INVENTORY_DONE
            self.d_setPlayerStates()

            if not self.anyUndecided():
                self.timesUp()

            if not self.anyInventoryPending() and not self.shuttingDown:
                self.shutdown()

    def shutdown(self):
        self.shuttingDown = True

        players = [purchaser.avId for purchaser in self.purchasers if purchaser.avId and purchaser.state == PurchaseState.PLAY_AGAIN]
        print('shutdown', self.purchasers, players, self.trolleyZone, self.zoneId)

        if players:
            newbies = []
            createMinigame(self.air, players, newbies, self.trolleyZone, zone=self.zoneId)
        else:
            # TODO: release zone if not ref count == 0 (newbie purchase managers may continue to hold zone)
            pass

        self.requestDelete()
        self.ignoreAll()


class NewbiePurchaseManagerAI(PurchaseManagerAI):
    def __init__(self, air, ownedNewbieId, purchasers, minigameId, trolleyZone, metagameRound):
        PurchaseManagerAI.__init__(self, air, purchasers, minigameId, trolleyZone, metagameRound)

        self.ownedNewbieId = ownedNewbieId

    def getOwnedNewbieId(self):
        return self.ownedNewbieId
