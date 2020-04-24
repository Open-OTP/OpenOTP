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

    def __init__(self, index, point_type, pos, landmark_index=-1):
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

    def __init__(self, start, end, zone_id):
        self.start = start
        self.end = end
        self.zone_id = zone_id


class DNABattleCell:
    __slots__ = 'width', 'height', 'pos'

    def __init__(self, width, height, pos):
        self.width = width
        self.height = height
        self.pos = pos
