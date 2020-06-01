import time


from .DistributedObjectAI import DistributedObjectAI
from . import OTPGlobals


DisconnectUnknown = 0
DisconnectBookExit = 1
DisconnectCloseWindow = 2
DisconnectPythonError = 3
DisconnectSwitchShards = 4
DisconnectGraphicsError = 5


class TimeManagerAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.disconnectCodes = {}
        self.exceptionInfo = {}

    def requestServerTime(self, context):
        avId = self.air.currentAvatarSender
        if not avId:
            return

        self.sendUpdateToAvatar(avId, 'serverTime', [context, globalClockDelta.getRealNetworkTime(bits=32), int(time.time())])

    def setDisconnectReason(self, disconnectCode):
        avId = self.air.currentAvatarSender
        if not avId:
            return

        self.disconnectCodes[avId] = disconnectCode
        # self.air.writeServerEvent('disconnect-reason', avId=avId,
        #                           reason=OTPGlobals.DisconnectReasons.get(disconnectCode, 'unknown'))

    def setExceptionInfo(self, info):
        avId = self.air.currentAvatarSender
        if not avId:
            return

        self.exceptionInfo[avId] = info
        # self.air.writeServerEvent('client-exception', avId=avId, info=info)

    def setSignature(self, signature, fileHash, pyc):
        pass  # TODO

    def setFrameRate(self, fps, deviation, numAvs, locationCode, timeInLocation, timeInGame, gameOptionsCode, vendorId,
                     deviceId, processMemory, pageFileUsage, physicalMemory, pageFaultCount, osInfo, cpuSpeed,
                     numCpuCores, numLogicalCpus, apiName):
        pass  # TODO

    def setCpuInfo(self, info, cacheStatus):
        pass  # TODO

    def checkForGarbageLeaks(self, wantReply):
        pass  # TODO

    def setClientGarbageLeak(self, num, description):
        pass  # TODO

    def checkAvOnDistrict(self, context, avId):
        sender = self.air.currentAvatarSender
        self.sendUpdateToAvatar(sender, 'checkAvOnDistrictResult', [context, avId, 1])
