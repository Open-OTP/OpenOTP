from otp import config

from direct.directnotify import DirectNotify
from direct.showbase import Messenger, BulletinBoard, EventManager
from direct.task import Task
from direct.interval.IntervalGlobal import ivalMgr


from panda3d.core import GraphicsEngine, ClockObject, TrueClock, PandaNode

directNotify = DirectNotify.DirectNotify()

from .AIRepository import AIRepository


class AIBase:
    AISleep = 0.04

    def __init__(self):
        self.eventMgr = EventManager.EventManager()
        self.messenger = Messenger.Messenger()
        self.bboard = BulletinBoard.BulletinBoard()
        self.taskMgr = Task.TaskManager()

        self.graphicsEngine = GraphicsEngine()

        globalClock = ClockObject.get_global_clock()
        self.trueClock = TrueClock.get_global_ptr()
        globalClock.set_real_time(self.trueClock.get_short_time())
        globalClock.set_average_frame_rate_interval(30.0)
        globalClock.tick()
        self.taskMgr.globalClock = globalClock

        self._setup()

        self.air = AIRepository()

    def _setup(self):
        self.taskMgr.add(self._reset_prev_transform, 'resetPrevTransform', priority=-51)
        self.taskMgr.add(self._ival_loop, 'ivalLoop', priority=20)
        self.taskMgr.add(self._ig_loop, 'igLoop', priority=50)
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
    simbase.run()


if __name__ == '__main__':
    main()
