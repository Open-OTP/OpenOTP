

ZONE_BITS = 16


def location_as_channel(parent_id, zone):
    return (parent_id << ZONE_BITS) | zone


def parent_to_children(parent_id):
    return (1 << ZONE_BITS) | parent_id