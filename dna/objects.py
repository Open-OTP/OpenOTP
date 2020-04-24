from typing import List

from panda3d.core import PandaNode, Vec3, Point3, VBase3, VBase4


class DNAGroup:
    __slots__ = 'name', 'children', 'parent', 'vis_group'

    def __init__(self, name):
        self.name = name
        self.children: List[DNAGroup] = []
        self.parent = None
        self.vis_group = None

    def num_children(self):
        return len(self.children)

    def add(self, child):
        self.children.append(child)

    def remove(self, child):
        self.children.remove(child)

    def at(self, index):
        return self.children[index]

    def set_parent(self, parent):
        self.parent = parent
        if not self.vis_group:
            self.vis_group = parent.vis_group

    def clear_parent(self):
        self.parent = None
        self.vis_group = None

    def traverse(self, nodePath, dnaStorage):
        node = PandaNode(self.name)
        nodePath = nodePath.attachNewNode(node, 0)
        for child in self.children:
            child.traverse(nodePath, dnaStorage)


class DNAVisGroup(DNAGroup):
    __slots__ = 'visibles', 'suit_edges', 'battle_cells'

    def __init__(self, name):
        DNAGroup.__init__(self, name)
        self.visibles: List[int] = []
        self.suit_edges = []
        self.battle_cells = []
        self.vis_group = self


class DNANode(DNAGroup):
    __slots__ = 'pos', 'hpr', 'scale'

    def __init__(self, name):
        DNAGroup.__init__(self, name)
        self.pos = Point3()
        self.hpr = VBase3()
        self.scale = VBase3(1)

    def traverse(self, parent, storage):
        node = PandaNode(self.name)
        nodepath = parent.attachNewNode(node, 0)
        nodepath.setPosHprScale(self.pos, self.hpr, self.scale)
        for child in self.children:
            child.traverse(nodepath, storage)


class DNAStreet(DNANode):
    __slots__ = 'code', 'textures', 'colors'

    def __init__(self, name):
        DNANode.__init__(self, name)
        self.code = ''
        self.textures = [None, None, None]
        self.colors = [VBase3(1, 1, 1), VBase3(1, 1, 1), VBase3(1, 1, 1)]

    def street_texture(self):
        return self.textures[0]

    def sidewalk_texture(self):
        return self.textures[1]

    def curb_texture(self):
        return self.textures[2]

    def __str__(self):
        return f'<DNAStreet code:{self.code} textures:{self.textures} colors:{self.colors}>'


class DNACornice(DNAGroup):
    __slots__ = 'code', 'color'

    def __init__(self, name):
        DNAGroup.__init__(self, name)

        self.code = ''
        self.color = VBase4(1)


class DNAWindows(DNAGroup):
    __slots__ = 'code', 'color', 'count'

    def __init__(self, name):
        DNAGroup.__init__(self, name)

        self.code = ''
        self.color = VBase4(1)
        self.count = 1


class DNADoor(DNAGroup):
    __slots__ = 'code', 'color'

    def __init__(self, name):
        DNAGroup.__init__(self, name)
        self.code = ''
        self.color = VBase4(1, 1, 1, 1)


class DNAFlatDoor(DNAGroup):
    pass


class DNAWall(DNANode):
    __slots__ = 'code', 'height', 'color'

    def __init__(self, name):
        DNANode.__init__(self, name)
        self.code = ''
        self.height = 10
        self.color = VBase4(1, 1, 1, 1)


class DNAProp(DNANode):
    __slots__ = 'code', 'color'

    def __init__(self, name):
        DNANode.__init__(self, name)
        self.code = ''
        self.color = VBase4(1, 1, 1, 1)


class DNASignGraphic(DNANode):
    __slots__ = 'code', 'color', 'width', 'height', 'use_parent_color'

    def __init__(self, name):
        DNANode.__init__(self, name)
        self.code = ''
        self.color = VBase4(1, 1, 1, 1)
        self.width = 0
        self.height = 0
        self.use_parent_color = True


class DNASignBaseline(DNANode):

    def __init__(self):
        DNANode.__init__(self, 'baseline')
        self.code = ''
        self.color = VBase4(1, 1, 1, 1)
        self.font = None
        self.flags = ''
        self.indent = 0.0
        self.kern = 0.0
        self.wiggle = 0.0
        self.stumble = 0.0
        self.stomp = 0.0
        self.width = 0
        self.height = 0


class DNASignText(DNANode):
    __slots__ = 'letters'

    def __init__(self):
        DNANode.__init__(self, '')
        self.letters = ''


class DNASign(DNANode):
    __slots__ = 'code', 'color'

    def __init__(self):
        DNANode.__init__(self, 'sign')
        self.code = ''
        self.color = VBase4(1, 1, 1, 1)


class DNAFlatBuilding(DNANode):
    currentWallHeight = 0
    __slots__ = 'width', 'has_door'

    def __init__(self, name):
        DNANode.__init__(self, name)
        self.width = 1
        self.has_door = False


class DNALandmarkBuilding(DNANode):
    __slots__ = 'code', 'wall_color', 'title', 'article', 'building_type', 'door'

    def __init__(self, name):
        DNANode.__init__(self, name)
        self.code = ''
        self.wall_color = VBase4(1, 1, 1, 1)
        self.title = ''
        self.article = ''
        self.building_type = ''
        self.door = None


class DNAAnimProp(DNAProp):
    __slots__ = 'anim'

    def __init__(self, name):
        DNAProp.__init__(self, name)
        self.anim = ''


class DNAInteractiveProp(DNAAnimProp):
    __slots__ = 'cell_id'

    def __init__(self, name):
        DNAAnimProp.__init__(self, name)
        self.cell_id = -1


from enum import IntEnum


class SuitPointType(IntEnum):
    STREET_POINT = 0
    FRONT_DOOR_POINT = 1
    SIDE_DOOR_POINT = 2
    COGHQ_IN_POINT = 3
    COGHQ_OUT_POINT = 4


class DNASuitPoint:
    __slots__ = 'index', 'point_type', 'pos', 'landmark_index', 'graph_id'

    def __init__(self, index: int, point_type: int, pos: Point3, landmark_index=-1):
        self.index = index
        self.point_type = point_type
        self.pos = pos
        self.graph_id = 0
        self.landmark_index = landmark_index

    def terminal(self):
        return self.point_type <= 2

    def __str__(self):
        return f'<DNASuitPoint index:{self.index} point_type:{self.point_type} pos:{self.pos} landmark: {self.landmark_index}>'


class DNASuitEdge:
    __slots__ = 'start', 'end', 'zone_id'

    def __init__(self, start: int, end: int, zone_id: int):
        self.start = start
        self.end = end
        self.zone_id = zone_id


class DNABattleCell:
    __slots__ = 'width', 'height', 'pos'

    def __init__(self, width: float, height: float, pos: Point3):
        self.width = width
        self.height = height
        self.pos = pos


class SuitLegType(IntEnum):
    TWalkFromStreet = 0
    TWalkToStreet = 1
    TWalk = 2
    TFromSky = 3
    TToSky = 4
    TFromSuitBuilding = 5
    TToSuitBuilding = 6
    TToToonBuilding = 7
    TFromCoghq = 8
    TToCoghq = 9
    TOff = 10


class SuitLeg:
    __slots__ = 'leg_type', 'start_time', 'leg_time', 'zone_id', 'block', 'point_a', 'point_b', 'pos_a', 'pos_b'

    def __init__(self, leg_type: int, start_time: float, leg_time: float, zone_id: int, block: int, point_a: DNASuitPoint, point_b: DNASuitPoint):
        self.leg_type = leg_type
        self.start_time = start_time
        self.leg_time = leg_time
        self.zone_id = zone_id
        self.block = block
        self.point_a: int = point_a.index
        self.point_b: int = point_b.index
        self.pos_a: Point3 = point_a.pos
        self.pos_b: Point3 = point_b.pos

    def get_pos_at_time(self, time: float) -> Point3:
        if self.leg_type in {SuitLegType.TFromSky, SuitLegType.TFromSuitBuilding, SuitLegType.TFromCoghq}:
            return Point3(self.pos_a)

        elif self.leg_type in {SuitLegType.TToSky, SuitLegType.TToSuitBuilding, SuitLegType.TToToonBuilding,
                               SuitLegType.TToCoghq, SuitLegType.TOff}:
            return Point3(self.pos_b)

        else:
            if time >= 0.0:
                if time > self.leg_time:
                    return Point3(self.pos_a)
                else:
                    delta = self.pos_b - self.pos_a
                    t = time / self.leg_time
                    pos = self.pos_a + (delta * t)
                    return Point3(pos)
            else:
                return Point3(self.pos_a)


FROM_SKY = 6.5
TO_SKY = 6.5
VICTORY_DANCE = 9.08
FROM_SUIT_BUILDING = 2.0
TO_SUIT_BUILDING = 2.5
TO_TOON_BUILDING = 2.5
SUIT_WALK_SPEED = 4.8


from .dnaparser import DNAStorage


class SuitLegList:
    __slots__ = 'legs'

    def __init__(self, path: List[int], storage: DNAStorage):
        self.legs: List[SuitLeg] = []

        # Create the first suit leg.
        leg_type = SuitLegType.TFromSky

        a = storage.suit_point_map[path[0]]
        b = storage.suit_point_map[path[1]]

        if a.point_type == SuitPointType.SIDE_DOOR_POINT:
            leg_type = SuitLegType.TFromSuitBuilding

        start_time = 0.0
        zone_id = storage.get_suit_edge_zone(a.index, b.index)

        leg_time = get_leg_time(a, b, leg_type)

        block = b.landmark_index
        if not block:
            block = a.landmark_index

        self.legs.append(SuitLeg(leg_type, start_time, leg_time, zone_id, block, a, b))

        start_time += leg_time

        # Create the middle suit legs.
        i = 0
        while i < len(path) - 1:
            a = storage.suit_point_map[path[i]]
            b = storage.suit_point_map[path[i + 1]]

            if a.point_type in {SuitPointType.FRONT_DOOR_POINT, SuitPointType.SIDE_DOOR_POINT}:
                leg_type = SuitLegType.TWalkToStreet
            elif b.point_type in {SuitPointType.FRONT_DOOR_POINT, SuitPointType.SIDE_DOOR_POINT}:
                leg_type = SuitLegType.TWalkFromStreet
            else:
                leg_type = SuitLegType.TWalk

            leg_time = get_leg_time(a, b, leg_type)

            zone_id = storage.get_suit_edge_zone(a.index, b.index)

            block = b.landmark_index
            if block == -1:
                block = a.landmark_index

            if a.point_type == SuitPointType.COGHQ_OUT_POINT:
                # We're going out of a Cog HQ door, so we'll need to insert a door
                # leg before the move:
                self.legs.append(SuitLeg(SuitLegType.TFromCoghq, start_time, FROM_SUIT_BUILDING, zone_id, block, a, b))
                start_time += FROM_SUIT_BUILDING

            self.legs.append(SuitLeg(leg_type, start_time, leg_time, zone_id, block, a, b))
            start_time += leg_time

            if b.point_type == SuitPointType.COGHQ_IN_POINT:
                # We're going into a Cog HQ door, so we'll need to insert a door leg
                # after the move:
                self.legs.append(SuitLeg(SuitLegType.TToCoghq, start_time, TO_SUIT_BUILDING, zone_id, block, a, b))
                start_time += TO_SUIT_BUILDING

            i += 1

        # Create the last suit leg.
        b = storage.suit_point_map[path[-1]]
        a = storage.suit_point_map[path[-2]]

        if b.point_type != SuitPointType.FRONTDOORPOINT:
            if b.point_type == SuitPointType.SIDEDOORPOINT:
                leg_type = SuitLegType.TToSuitBuilding
            else:
                leg_type = SuitLegType.TToSky
        else:
            leg_type = SuitLegType.TToToonBuilding

        if leg_type == SuitLegType.TToSky:
            leg_time = TO_SKY
        elif leg_type == SuitLegType.TToSuitBuilding:
            leg_time = TO_SUIT_BUILDING
        elif leg_type == SuitLegType.TToToonBuilding:
            leg_time = TO_TOON_BUILDING
        else:
            leg_time = 0.0

        zone_id = storage.get_suit_edge_zone(a.index, b.index)

        block = b.landmark_index
        if block == -1:
            block = a.landmark_index

        self.legs.append(SuitLeg(leg_type, start_time, leg_time, zone_id, block, a, b))
        start_time += leg_time

        # Finally, disable the suit.
        self.legs.append(SuitLeg(SuitLegType.TOff, start_time, 0.0, zone_id, block, a, b))

    def get_zone_id(self, i):
        return self[i].zone_id

    def get_type(self, i):
        return self[i].leg_type

    def get_start_time(self, i):
        return self[i].start_time

    def get_block_number(self, i):
        return self[i].block

    def get_leg_index_at_time(self, time, current_leg):
        i = current_leg
        while i + 1 < len(self.legs) and self.get_start_time(i + 1) < time:
            i += 1

        return i

    def is_point_in_range(self, point_index, start_time, end_time):
        leg = self.get_leg_index_at_time(start_time, 0)
        time = start_time
        while time < end_time:
            if leg >= len(self.legs):
                return False
            if self[leg].point_a == point_index or self[leg].point_b == point_index:
                return True
            time += self.get_start_time(leg)
            leg += 1

        return False

    def __getitem__(self, i):
        return self.legs[i]


def get_leg_time(a, b, leg_type):
    if leg_type in (SuitLegType.TWalk, SuitLegType.TWalkFromStreet, SuitLegType.TWalkToStreet):
        return (a.pos - b.pos).length() / SUIT_WALK_SPEED
    elif leg_type == SuitLegType.TFromSky:
        return FROM_SKY
    elif leg_type == SuitLegType.TToSky:
        return TO_SKY
    elif leg_type == SuitLegType.TFromSuitBuilding:
        return FROM_SUIT_BUILDING
    elif leg_type == SuitLegType.TToSuitBuilding:
        return TO_SUIT_BUILDING
    elif leg_type == SuitLegType.TToToonBuilding:
        return TO_TOON_BUILDING
    else:
        return TO_TOON_BUILDING

