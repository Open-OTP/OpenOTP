from ai.DistributedObjectAI import DistributedObjectAI

from panda3d.core import NodePath


class DistributedNodeAI(DistributedObjectAI, NodePath):
    def __init__(self, air, name=None):
        DistributedObjectAI.__init__(self, air)
        if name is None:
            name = self.__class__.__name__

        NodePath.__init__(self, name)

    def setParent(self, token):
        if token:
            self.parentMgr.requestReparent(self, token)

    def d_setParent(self, token):
        self.sendUpdate('setParentStr' if type(token) == str else 'setParent', [token])

    def b_setParent(self, token):
        self.setParent(token)
        self.d_setParent(token)

    def delete(self):
        if not self.isEmpty():
            self.removeNode()

        DistributedObjectAI.delete(self)

