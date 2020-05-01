from otp.util import getPuppetChannel, getAccountChannel


class DistributedObjectAI:
    QUIET_ZONE = 1
    do_id = None

    def __init__(self, air):
        self.air = air
        self.dclass = air.dc_file.namespace[self.__class__.__name__[:-2]]
        self._location = (0, 0)

    def generate_with_required(self, zone_id):
        self.air.generate_with_required(self, self.air.district.do_id, zone_id)

    def send_update(self, field_name, args):
        dg = self.dclass.ai_format_update(field_name, self.do_id, self.do_id, self.air.our_channel, args)
        self.air.send(dg)

    def send_update_to_channel(self, channel, field_name, args):
        dg = self.dclass.ai_format_update(field_name, self.do_id, channel, self.air.our_channel, args)
        self.air.send(dg)

    def send_update_to_sender(self, field_name, args):
        self.send_update_to_channel(self.air.current_sender, field_name, args)

    def send_update_to_avatar(self, av_id, field_name, args):
        self.send_update_to_channel(getPuppetChannel(av_id), field_name, args)

    def send_update_to_account(self, disl_id, field_name, args):
        self.send_update_to_channel(getAccountChannel(disl_id), field_name, args)

    @property
    def location(self):
        return self._location

    @property
    def parent_id(self):
        return self._location[0]

    @property
    def zone_id(self):
        return self._location[1]

    @location.setter
    def location(self, location):
        if location == self._location:
            return
        parent_id, zone_id = location
        old_parent_id, old_zone_id = self._location
        self._location = location

        self.air.store_location(self.do_id, old_parent_id, old_zone_id, parent_id, zone_id)

        if zone_id != DistributedObjectAI.QUIET_ZONE:
            self.handle_logical_zone_change(old_zone_id, zone_id)

    def handle_logical_zone_change(self, old_zone: int, new_zone: int):
        pass

    def generate(self):
        pass

    def announce_generate(self):
        pass

    def delete(self):
        pass

    def request_delete(self):
        # TODO
        pass

    def uniqueName(self, name):
        return f'{name}={self.do_id}'

    requestDelete = request_delete
    sendUpdate = send_update
    generateWithRequired = generate_with_required
