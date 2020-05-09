from otp import config

from direct.directnotify import DirectNotify
from direct.showbase import Messenger, BulletinBoard, EventManager
from direct.task import Task
from direct.interval.IntervalGlobal import ivalMgr


from panda3d.core import GraphicsEngine, ClockObject, TrueClock, PandaNode, NodePath

directNotify = DirectNotify.DirectNotify()

from .AIRepository import AIRepository
import builtins
import time


from direct.showbase.DirectObject import DirectObject
import math
from numpy import int16

NetworkTimeBits = 16
NetworkTimePrecision = 100.0
NetworkTimeMask = ((1 << NetworkTimeBits) - 1)
NetworkTimeTopBits = (32 - NetworkTimeBits)


class TTClockDelta(DirectObject):
    def __init__(self):
        self.globalClock = ClockObject.getGlobalClock()
        self.delta = 0
        self.accept('resetClock', self.__resetClock)

    def __resetClock(self, timeDelta):
        # print('adjusting timebase by %f seconds' % timeDelta))
        self.delta += timeDelta

    def resynchronize(self, localTime, networkTime):
        newDelta = (float(localTime) - (float(networkTime) / NetworkTimePrecision))
        change = (newDelta - self.delta)
        self.delta = newDelta
        return self.networkToLocalTime(self.localToNetworkTime(change), 0.0)

    def networkToLocalTime(self, networkTime, now=None):
        if now is None:
            now = self.globalClock.getRealTime()

        if self.globalClock.getMode() == ClockObject.MNonRealTime:
            return now

        ntime = int(math.floor((((now - self.delta) * NetworkTimePrecision) + 0.5)))
        diff = self.__signExtend((networkTime - ntime))
        return now + (float(diff) / NetworkTimePrecision)

    def localToNetworkTime(self, localTime, bits=16):
        ntime = int(math.floor((((localTime - self.delta) * NetworkTimePrecision) + 0.5)))
        if bits == 16:
            return self.__signExtend(ntime)
        else:
            return ntime

    def getRealNetworkTime(self, *args, bits=16, **kwargs):
        return self.localToNetworkTime(self.globalClock.getRealTime(), bits)

    def getFrameNetworkTime(self):
        return self.localToNetworkTime(self.globalClock.getFrameTime())

    def localElapsedTime(self, networkTime):
        now = self.globalClock.getFrameTime()
        dt = (now - self.networkToLocalTime(networkTime, now))
        if dt >= 0.0:
            return dt

        # print(('negative clock delta: %.3f' % dt))
        return 0.0

    def __signExtend(self, networkTime):
        return (int16(networkTime & NetworkTimeMask) << NetworkTimeTopBits) >> NetworkTimeTopBits


class AIBase:
    AISleep = 0.01

    def __init__(self):
        self.eventMgr = EventManager.EventManager()
        self.messenger = Messenger.Messenger()
        self.bboard = BulletinBoard.BulletinBoard()
        self.taskMgr = Task.TaskManager()

        self.graphicsEngine = GraphicsEngine()

        globalClock = ClockObject.getGlobalClock()
        self.trueClock = TrueClock.getGlobalPtr()
        globalClock.setRealTime(self.trueClock.getShortTime())
        globalClock.setAverageFrameRateInterval(30.0)
        globalClock.tick()
        self.taskMgr.globalClock = globalClock
        builtins.globalClock = globalClock
        builtins.globalClockDelta = TTClockDelta()

        self.hidden = NodePath('hidden')

        self._setup()

        self.air = AIRepository()

    def _setup(self):
        self.taskMgr.add(self._reset_prev_transform, 'resetPrevTransform', priority=-51)
        self.taskMgr.add(self._ival_loop, 'ivalLoop', priority=20)
        self.taskMgr.add(self._ig_loop, 'igLoop', priority=50)
        self.taskMgr.add(self.__sleep, 'aiSleep', priority=55)
        self.eventMgr.restart()

    def _reset_prev_transform(self, state):
        PandaNode.resetAllPrevTransform()
        return Task.cont

    def _ival_loop(self, state):
        ivalMgr.step()
        return Task.cont

    def _ig_loop(self, state):
        self.graphicsEngine.renderFrame()
        return Task.cont

    def __sleep(self, task):
        time.sleep(self.AISleep)
        return Task.cont

    def run(self):
        self.air.run()
        self.start_read_poll_task()
        self.taskMgr.run()

    def stop(self):
        self.taskMgr.stop()

    def start_read_poll_task(self):
        self.taskMgr.add(self.air.readUntilEmpty, 'readPoll', priority=-30)


def main():
    print('running main')
    import builtins
    builtins.simbase = AIBase()
    builtins.taskMgr = simbase.taskMgr
    builtins.messenger = simbase.messenger
    simbase.run()


if __name__ == '__main__':
    main()
