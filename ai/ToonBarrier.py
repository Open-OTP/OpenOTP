from direct.showbase.DirectObject import DirectObject


class ToonBarrier(DirectObject):
    def __init__(self, uniqueName, avIds, timeout, doneFunc, timeoutFunc=None):
        self.uniqueName = f'{uniqueName}-barrier'
        self.timeoutName = f'{uniqueName}-timeout'
        self.avIds = avIds[:]
        self.pending = avIds[:]

        if not avIds:
            if doneFunc:
                doneFunc()
            return

        self.doneFunc = doneFunc
        self.timeoutFunc = timeoutFunc

        self.active = True

        taskMgr.doMethodLater(timeout, self.__timerExpired, self.timeoutName)

        for avId in avIds:
            event = simbase.air.getAvatarExitEvent(avId)
            self.acceptOnce(event, self.__handleUnexpectedExit, extraArgs=[avId])

    def __handleUnexpectedExit(self, avId):
        if avId not in self.avIds:
            return
        self.avIds.remove(avId)
        if avId in self.pending:
            self.clear(avId)

    def __timerExpired(self, task):
        self.cleanup()
        if self.timeoutFunc:
            self.timeoutFunc(self.pending[:])
        if self.doneFunc:
            self.doneFunc(self.avIds[:])
        return task.done

    def clear(self, avId):
        if avId not in self.pending:
            return

        self.pending.remove(avId)

        if not self.pending:
            self.cleanup()

            self.doneFunc(self.avIds[:])

    def cleanup(self):
        if self.active:
            taskMgr.remove(self.timeoutName)
            self.active = False
        self.ignoreAll()
