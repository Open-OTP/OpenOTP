from .DistributedNodeAI import DistributedNodeAI

from panda3d.direct import CDistributedSmoothNodeBase


from typing import Optional


class DistributedSmoothNodeAI(DistributedNodeAI):
    def __init__(self, air, name=None):
        DistributedNodeAI.__init__(self, air, name)
        self.cnode: Optional[CDistributedSmoothNodeBase] = None

    def generate(self):
        DistributedNodeAI.generate(self)
        self.cnode = CDistributedSmoothNodeBase()
        self.cnode.setClockDelta(globalClockDelta)
        self.cnode.setRepository(self.air, 1, self.air.ourChannel)

    def delete(self):
        self.cnode = None
        DistributedNodeAI.delete(self)

    def setSmH(self, h, t=None):
        self.setH(h)

    def setSmZ(self, z, t=None):
        self.setZ(z)

    def setSmXY(self, x, y, t=None):
        self.setX(x)
        self.setY(y)

    def setSmXZ(self, x, z, t=None):
        self.setX(x)
        self.setZ(z)

    def setSmPos(self, x, y, z, t=None):
        self.setPos(x, y, z)

    def setSmHpr(self, h, p, r, t=None):
        self.setHpr(h, p, r)

    def setSmXYH(self, x, y, h, t=None):
        self.setX(x)
        self.setY(y)
        self.setH(h)

    def setSmXYZH(self, x, y, z, h, t=None):
        self.setPos(x, y, z)
        self.setH(h)

    def setSmPosHpr(self, x, y, z, h, p, r, t=None):
        self.setPosHpr(x, y, z, h, p, r)

    def setSmPosHprL(self, l, x, y, z, h, p, r, t=None):
        self.setPosHpr(x, y, z, h, p, r)

    setComponentX = DistributedNodeAI.setX
    setComponentY = DistributedNodeAI.setY
    setComponentZ = DistributedNodeAI.setZ
    setComponentH = DistributedNodeAI.setH
    setComponentP = DistributedNodeAI.setP
    setComponentR = DistributedNodeAI.setR
