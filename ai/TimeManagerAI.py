import time

from direct.directnotify import DirectNotifyGlobal
from direct.distributed.ClockDelta import globalClockDelta

from .DistributedObjectAI import DistributedObjectAI
from . import OTPGlobals


class TimeManagerAI(DistributedObjectAI):
    notify = DirectNotifyGlobal.directNotify.newCategory('TimeManagerAI')

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.avId2disconnectcode = {}
        self.avId2exceptioninfo = {}

    def requestServerTime(self, context):
        avId = self.air.getAvatarIdFromSender()
        if not avId:
            return

        self.sendUpdateToAvatarId(avId, 'serverTime',
                                  [context, globalClockDelta.getRealNetworkTime(bits=32), int(time.time())])

    def setDisconnectReason(self, disconnectCode):
        avId = self.air.getAvatarIdFromSender()
        if not avId:
            return

        self.avId2disconnectcode[avId] = disconnectCode
        self.air.writeServerEvent('disconnect-reason', avId=avId,
                                  reason=OTPGlobals.DisconnectReasons.get(disconnectCode, 'unknown'))

    def setExceptionInfo(self, info):
        avId = self.air.getAvatarIdFromSender()
        if not avId:
            return

        self.avId2exceptioninfo[avId] = info
        self.air.writeServerEvent('client-exception', avId=avId, info=info)

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
        pass  # TODO
