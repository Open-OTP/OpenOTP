from otp.util import getPuppetChannel, getAccountChannel


from . import AIRepository


class DistributedObjectAI:
    QUIET_ZONE = 1
    do_id = None

    def __init__(self, air: AIRepository.AIRepository):
        self.air = air
        self.dclass = air.dcFile.namespace[self.__class__.__name__[:-2]]
        self.zoneId = 0
        self.parentId = 0

    def generateWithRequired(self, zone_id):
        self.zoneId = zone_id
        self.air.generateWithRequired(self, self.air.district.do_id, zone_id)

    def sendUpdate(self, field_name, args):
        dg = self.dclass.ai_format_update(field_name, self.do_id, self.do_id, self.air.ourChannel, args)
        self.air.send(dg)

    def sendUpdateToChannel(self, channel, field_name, args):
        dg = self.dclass.ai_format_update(field_name, self.do_id, channel, self.air.ourChannel, args)
        self.air.send(dg)

    def sendUpdateToSender(self, field_name, args):
        self.sendUpdateToChannel(self.air.currentSender, field_name, args)

    def sendUpdateToAvatar(self, av_id, field_name, args):
        self.sendUpdateToChannel(getPuppetChannel(av_id), field_name, args)

    def sendUpdateToAccount(self, disl_id, field_name, args):
        self.sendUpdateToChannel(getAccountChannel(disl_id), field_name, args)

    @property
    def location(self):
        return self.parentId, self.zoneId

    @location.setter
    def location(self, location):
        if location == self.location:
            return
        parent_id, zone_id = location
        old_parent_id, old_zone_id = self.location
        self.parentId = parent_id
        self.zoneId = zone_id

        self.air.storeLocation(self.do_id, old_parent_id, old_zone_id, parent_id, zone_id)

        if zone_id != DistributedObjectAI.QUIET_ZONE:
            self.handeLogicalZoneChange(old_zone_id, zone_id)

    def handeLogicalZoneChange(self, old_zone: int, new_zone: int):
        pass

    def generate(self):
        pass

    def announce_generate(self):
        pass

    def delete(self):
        pass

    def requestDelete(self):
        # TODO
        pass

    def uniqueName(self, name):
        return f'{name}={self.do_id}'
