from .DistributedObjectAI import DistributedObjectAI


class DistributedObjectGlobalAI(DistributedObjectAI):
    def announceGenerate(self):
        DistributedObjectAI.announceGenerate(self)
        self.air.registerForChannel(self.do_id)

    def generateGlobalObject(self, zone_id=2):
        if not self.do_id:
            raise Exception('do_id not set for global object')
        self.air.doTable[self.do_id] = self
        self.location = (self.parentId, zone_id)
        self.queueUpdates = False
        self.generate()
        self.announceGenerate()

    def delete(self):
        self.air.unregisterForChannel(self.do_id)
        DistributedObjectAI.delete(self)
