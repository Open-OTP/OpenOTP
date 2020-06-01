from direct.showbase.DirectObject import DirectObject
from typing import List


class ToonBarrier(DirectObject):
    def __init__(self, uniqueName, avIds, timeout, doneFunc, timeoutFunc=None, extraArgs=None):
        self.uniqueName = f'{uniqueName}-barrier'
        self.timeoutName = f'{uniqueName}-timeout'
        self.avIds: List[int] = avIds[:]
        self.pending: List[int] = avIds[:]

        if not avIds:
            if doneFunc:
                doneFunc([])
            return

        self.doneFunc = doneFunc
        self.timeoutFunc = timeoutFunc
        self.extraArgs = extraArgs

        self.active = True

        self.task = taskMgr.doMethodLater(timeout, self.__timerExpired, self.timeoutName)

        for avId in avIds:
            event = simbase.air.getAvatarExitEvent(avId)
            self.acceptOnce(event, self.__handleUnexpectedExit, extraArgs=[avId])

        self.timedOut = False

    def stopTimeout(self):
        self.task = None
        taskMgr.remove(self.timeoutName)

    def resetTimeout(self, timeout):
        self.timedOut = False
        self.task = taskMgr.doMethodLater(timeout, self.__timerExpired, self.timeoutName)

    def __handleUnexpectedExit(self, avId):
        if avId not in self.avIds:
            return
        self.avIds.remove(avId)
        if avId in self.pending:
            self.clear(avId)

    def __timerExpired(self, task):
        self.timedOut = True
        if self.timeoutFunc:
            self.timeoutFunc(self.pending[:])
        self._done()
        return task.done

    def unclear(self, avId):
        if avId in self.avIds and avId not in self.pending:
            self.pending.append(avId)

    def clear(self, avId):
        if avId not in self.pending:
            return

        self.pending.remove(avId)

        if not self.pending:
            self._done()

    def _done(self):
        self.cleanup()
        if self.doneFunc is not None:
            if self.extraArgs is not None:
                self.doneFunc(self.avIds[:], *self.extraArgs)
            else:
                self.doneFunc(self.avIds[:])

    def cleanup(self):
        self.task = None
        if self.active:
            taskMgr.remove(self.timeoutName)
            self.active = False
        self.ignoreAll()
