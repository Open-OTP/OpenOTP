
class DistributedObjectAI:
    do_id = None

    def __init__(self, air):
        self.air = air
        self.dclass = air.dc_file.namespace[self.__class__.__name__[:-2]]

    def GetPuppetConnectionChannel(self, doId):
        return doId + (1 << 32)

    def GetAccountConnectionChannel(self, doId):
        return doId + (3 << 32)

    def GetAccountIDFromChannelCode(self, channel):
        return channel >> 32

    def GetAvatarIDFromChannelCode(self, channel):
        return channel & 0xffffffff

    def send_update(self, field_name, args):
        dg = self.dclass.ai_format_update(field_name, self.do_id, self.do_id, self.air.our_channel, args)
        self.air.send(dg)

    def send_update_to_channel(self, channel, field_name, args):
        dg = self.dclass.ai_format_update(field_name, self.do_id, channel, self.air.our_channel, args)
        self.air.send(dg)
