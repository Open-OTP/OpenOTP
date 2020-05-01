import time

from direct.distributed.ClockDelta import globalClockDelta

from .DistributedObjectAI import DistributedObjectAI
from . import OTPGlobals


class TimeManagerAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.disconnect_codes = {}
        self.exception_info = {}

    def requestServerTime(self, context):
        avId = self.air.current_av_sender
        if not avId:
            return

        self.send_update_to_avatar(avId, 'serverTime', [context, globalClockDelta.getRealNetworkTime(bits=32), int(time.time())])

    def setDisconnectReason(self, disconnectCode):
        avId = self.air.current_av_sender
        if not avId:
            return

        self.disconnect_codes[avId] = disconnectCode
        # self.air.writeServerEvent('disconnect-reason', avId=avId,
        #                           reason=OTPGlobals.DisconnectReasons.get(disconnectCode, 'unknown'))

    def setExceptionInfo(self, info):
        avId = self.air.current_av_sender
        if not avId:
            return

        self.exception_info[avId] = info
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
        sender = self.air.current_av_sender
        self.send_update_to_sender('checkAvOnDistrictResult', [context, avId, 1])
