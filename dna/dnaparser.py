from lark import Lark, Tree, Transformer, Discard

from panda3d.core import Vec3, Point3, VBase4

from .objects import *


# Using deque for O(1) popping from the left.
from collections import deque


from typing import List, Dict, Union
from weakref import WeakValueDictionary


class DNAError(Exception):
    pass


class DNAStorage:
    def __init__(self):
        self.groups: Dict[str, DNAGroup] = dict()
        self.visgroups: List[DNAVisGroup] = list()

        self.suit_points: List[DNASuitPoint] = list()
        self.suit_point_map: Dict[int, DNASuitPoint] = dict()
        self.suit_edges: Dict[int, List[DNASuitEdge]] = dict()
        self.battle_cells: List[DNABattleCell] = list()
        self.blocks: List[int] = list()
        self.block_zones: Dict[int, int] = dict()
        self.block_building_types: Dict[int, str] = dict()
        self.block_doors: Dict[int, str] = dict()

    def get_suit_edge(self, start_index: int, end_index: int) -> Union[None, DNASuitEdge]:
        if start_index not in self.suit_edges:
            return None

        for edge in self.suit_edges[start_index]:
            if edge.end == end_index:
                return edge

        return None

    def get_suit_edge_travel_time(self, start_index: int, end_index: int, walk_speed: float) -> float:
        edge = self.get_suit_edge(start_index, end_index)

        start = self.suit_point_map[edge.start]
        end = self.suit_point_map[edge.end]

        return (start.pos - end.pos).length() / walk_speed

    def get_suit_edge_zone(self, start_index: int, end_index: int) -> Union[int, None]:
        edge = self.get_suit_edge(start_index, end_index)
        return edge.zone_id if edge else None

    def get_adjacent_points(self, start_index: int) -> List[int]:
        if start_index not in self.suit_edges:
            return []

        return [edge.end for edge in self.suit_edges[start_index]]

    def discover_continuity(self) -> int:
        graph_id = 0

        for suit_point in self.suit_points:
            if not suit_point.graph_id:
                graph_id += 1
                self.discover_connections(suit_point, graph_id)

        return graph_id

    def discover_connections(self, suit_point: DNASuitPoint, graph_id: int):
        if suit_point.graph_id:
            if suit_point.graph_id != graph_id:
                print('DNAStorage: %s is connected to the graph only one-way.' % suit_point)
        else:
            suit_point.graph_id = graph_id
            for edge in self.suit_edges[suit_point.index]:
                self.discover_connections(self.suit_point_map[edge.end], graph_id)

    def get_suit_path(self, start_point: DNASuitPoint, end_point: DNASuitPoint, min_length: int, max_length: int) -> List[int]:
        if start_point.graph_id != end_point.graph_id:
            return []

        path = self.get_suit_path_breadth_first(start_point, end_point, min_length, max_length)

        if path is None:
            return []

        while len(path) < min_length:
            start = path[-1]
            min_length -= len(path)
            max_length -= len(path)
            for adj in self.get_adjacent_points(start):
                subpath = self.get_suit_path_breadth_first(self.suit_point_map[adj], end_point, min_length, max_length)
                path.extend(subpath)
                break

        return path

    def get_suit_path_breadth_first(self, start_point: DNASuitPoint, end_point: DNASuitPoint, min_length: int, max_length: int):
        considering = deque()
        visited = set()

        considering.append([start_point.index])
        visited.add(start_point.index)

        while considering:
            path = considering.popleft()
            start_point_index = path[-1]

            if len(path) >= max_length:
                return

            for point in self.get_adjacent_points(start_point_index):
                # We have already visited this suit point.
                if point in visited:
                    continue

                # Check for our end point.
                if point == end_point.index:
                    return path + [point]

                visited.add(point)

                # Check for a non-door point.
                if self.suit_point_map[point].point_type == SuitPointType.STREET_POINT:
                    considering.append(path + [point])


# TODO: make AI specific Transformer with discarded nodes for load speed up
class DNATransformer(Transformer):
    def __init__(self):
        Transformer.__init__(self, visit_tokens=True)

    def dna(self, args):
        group = DNAGroup('root')
        group.children = args
        return group

    def group(self, args):
        _, name = args[0], args[1].value
        group = DNAGroup(name)

        for child in args[2:]:
            child.set_parent(group)
            group.children.append(child)

        return group

    def visgroup(self, args):
        args = deque(args)
        kw = args.popleft()
        name = args.popleft().value
        visgroup = DNAVisGroup(name)

        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                if child.data == 'vis':
                    visgroup.visibles = child.children
            else:
                if hasattr(child, 'set_parent'):
                    child.set_parent(visgroup)

                if isinstance(child, DNABattleCell):
                    visgroup.battle_cells.append(child)
                elif isinstance(child, DNASuitEdge):
                    child.zone_id = int(visgroup.name)
                    visgroup.suit_edges.append(child)

                visgroup.children.append(child)

        return visgroup

    def node(self, args):
        args = deque(args)
        kw = args.popleft()
        name = args.popleft().value

        node = DNANode(name)

        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                setattr(node, child.data, child.children[0])
            else:
                child.set_parent(node)
                node.children.append(child)

        return node

    def landmark(self, args):
        args = deque(args)
        kw = args.popleft()
        name = args.popleft().value

        landmark = DNALandmarkBuilding(name)

        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                setattr(landmark, child.data, child.children[0])
            elif isinstance(child, DNADoor):
                landmark.door = child
            else:
                child.set_parent(landmark)
                landmark.children.append(child)

        return landmark

    def anim_building(self, args):
        args = deque(args)
        kw = args.popleft()
        name = args.popleft().value

        landmark = DNAAnimBuilding(name)

        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                setattr(landmark, child.data, child.children[0])
            elif isinstance(child, DNADoor):
                landmark.door = child
            else:
                child.set_parent(landmark)
                landmark.children.append(child)

        return landmark

    def flatbuilding(self, args):
        args = deque(args)
        kw = args.popleft()
        name = args.popleft().value

        flat_bldg = DNAFlatBuilding(name)

        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                setattr(flat_bldg, child.data, child.children[0])
            else:
                if isinstance(child, DNAFlatDoor):
                    flat_bldg.has_door = True

                child.set_parent(flat_bldg)
                flat_bldg.children.append(child)

        return flat_bldg

    def title(self, args):
        return Tree('title', [args[1].value])

    def buildingtype(self, args):
        return Tree('building_type', [args[1].value])

    def door(self, args):
        args = deque(args)
        kw = args.popleft()

        door = DNADoor('door')

        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                setattr(door, child.data, child.children[0])
            else:
                child.set_parent(door)
                door.children.append(child)

        return door

    def sign(self, args):
        args = deque(args)
        kw = args.popleft()

        sign = DNASign()

        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                setattr(sign, child.data, child.children[0])
            else:
                child.set_parent(sign)
                sign.children.append(child)

        return sign

    def baseline(self, args):
        args = deque(args)
        kw = args.popleft()

        baseline = DNASignBaseline()

        letters = []

        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                if child.data == 'text':
                    letters.append(child.children[0])
                else:
                    setattr(baseline, child.data, child.children[0])
            else:
                child.set_parent(baseline)
                baseline.children.append(child)

        if letters:
            text = DNASignText()
            text.letters = ''.join(letters)

            baseline.children.append(text)

        return baseline

    def graphic(self, args):
        args = deque(args)
        kw = args.popleft()

        graphic = DNASignGraphic('graphic')

        while args:
            child = args.popleft()

            if child.data == 'color':
                graphic.use_parent_color = False

            setattr(graphic, child.data, child.children[0])

        return graphic

    def text(self, args):
        kw1, kw2, letter = args

        return Tree('text', [letter])

    def stomp(self, args):
        return Tree('stomp', [args[1].value])

    def stumble(self, args):
        return Tree('stumble', [args[1].value])

    def kern(self, args):
        return Tree('kern', [args[1].value])

    def wiggle(self, args):
        return Tree('wiggle', [args[1].value])

    def anim(self, args):
        return Tree('anim', [args[1].value])

    def interactive_prop(self, args):
        args = deque(args)
        kw = args.popleft()
        name = args.popleft().value

        prop = DNAInteractiveProp(name)

        while args:
            child = args.popleft()

            setattr(prop, child.data, child.children[0])

        return prop

    def anim_prop(self, args):
        args = deque(args)
        kw = args.popleft()
        name = args.popleft().value

        prop = DNAAnimProp(name)

        while args:
            child = args.popleft()

            setattr(prop, child.data, child.children[0])

        return prop

    def cell_id(self, args):
        return Tree('cell_id', [int(args[1].value)])

    def prop(self, args):
        args = deque(args)
        kw = args.popleft()
        name = args.popleft().value

        prop = DNAProp(name)

        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                setattr(prop, child.data, child.children[0])
            else:
                child.set_parent(prop)
                prop.children.append(child)

        return prop

    def wall(self, args):
        args = deque(args)
        kw = args.popleft()

        wall = DNAWall('windows')
        while args:
            child = args.popleft()

            if isinstance(child, Tree):
                if child.data in {'code', 'color', 'height'}:
                    setattr(wall, child.data, child.children[0])
            else:
                child.set_parent(wall)
                wall.children.append(child)

        return wall

    def flat_door(self, args):
        args = deque(args)
        kw = args.popleft()

        door = DNAFlatDoor('windows')
        while args:
            child = args.popleft()

            if child.data in {'code', 'color'}:
                setattr(door, child.data, child.children[0])

        return door

    def windows(self, args):
        args = deque(args)
        kw = args.popleft()

        windows = DNAWindows('windows')
        while args:
            child = args.popleft()

            if child.data in {'code', 'color', 'count'}:
                setattr(windows, child.data, child.children[0])

        return windows

    def cornice(self, args):
        args = deque(args)
        kw = args.popleft()

        cornice = DNACornice('cornice')
        while args:
            child = args.popleft()

            if child.data in {'code', 'color'}:
                setattr(cornice, child.data, child.children[0])

        return cornice

    def street(self, args):
        args = deque(args)
        _, name = args.popleft(), args.popleft().value

        street = DNAStreet(name)

        texture_count = 0
        color_count = 0

        while args:
            child = args.popleft()
            if child.data in {'code', 'pos', 'hpr'}:
                setattr(street, child.data, child.children[0])
            elif child.data == 'texture':
                street.textures[texture_count] = child.children[0]
                texture_count += 1
            elif child.data == 'color':
                street.textures[color_count] = child.children[0]
                color_count += 1

        return street

    def scale(self, args):
        return Tree('scale', [args[1]])

    def count(self, args):
        return Tree('count', [int(args[1].value)])

    def texture(self, args):
        return Tree('texture', [args[1].value])

    def code(self, args):
        return Tree('code', [args[1].value])

    def vis(self, args):
        return Tree('vis', [int(token.value.split(':')[0]) for token in args[1:]])

    def battle_cell(self, args):
        for i in range(1, len(args)):
            args[i] = args[i].value
        width, height, x, y, z = args[1:]
        return DNABattleCell(width, height, Point3(x, y, z))

    def store_suit_point(self, args):
        if len(args) < 7:
            _, index, point_type, x, y, z = args
            landmark_index = -1
        else:
            _, index, point_type, x, y, z, landmark_index = args

        index = index.value
        x, y, z = x.value, y.value, z.value

        point_type = SuitPointType[point_type]
        point = DNASuitPoint(index, point_type, Point3(x, y, z), landmark_index)
        return point

    def suit_edge(self, args):
        _, a, b = args
        suit_edge = DNASuitEdge(a.value, b.value, -1)
        return suit_edge

    def width(self, args):
        return Tree('width', [args[1].value])

    def height(self, args):
        return Tree('height', [args[1].value])

    def color(self, args):
        return Tree('color', [args[1]])

    def pos(self, args):
        return Tree('pos', [args[1]])

    def hpr(self, args):
        return Tree('hpr', [args[1]])

    def nhpr(self, args):
        return Tree('hpr', [args[1]])

    def char(self, args):
        return args[0].value

    def vec4(self, args):
        return VBase4(*(token.value for token in args))

    def vec3(self, args):
        return Vec3(*(token.value for token in args))

    def FLOAT_LITERAL(self, token):
        token.value = float(token.value)
        return token

    def INT_LITERAL(self, token):
        token.value = int(token.value)
        return token

    def STRING_LITERAL(self, token):
        token.value = token[1:-1]
        return token

    def UNSIGNED_INT_LITERAL(self, token):
        token.value = int(token.value)
        return token

    def ZERO_LITERAL(self, token):
        token.value = 0
        return token


def traverse(node, storage: DNAStorage):
    if isinstance(node, DNAGroup):
        storage.groups[node.name] = node
    if isinstance(node, DNASuitEdge):
        storage.suit_edges.setdefault(node.start, []).append(node)
    elif isinstance(node, DNASuitPoint):
        storage.suit_points.append(node)
        storage.suit_point_map[node.index] = node
    elif isinstance(node, DNALandmarkBuilding):
        block = int(node.name.split(':')[0][2:])
        zone_id = int(node.vis_group.name.split(':')[0])
        storage.blocks.append(block)
        storage.block_zones[block] = zone_id
        storage.block_building_types[block] = node.building_type
    elif isinstance(node, DNAVisGroup):
        storage.visgroups.append(node)

    if hasattr(node, 'children'):
        for child in node.children:
            if hasattr(child, 'set_parent'):
                child.set_parent(node)
            traverse(child, storage)


with open('dna/dna.lark', 'r') as f:
    dc_parser = Lark(f, start='dna', debug=False, parser='lalr')


def load_dna_file(dna_path):
    transformer = DNATransformer()

    with open(dna_path, 'r') as f2:
        tree = transformer.transform(dc_parser.parse(f2.read(),))

    storage = DNAStorage()
    traverse(tree, storage)

    return tree, storage


# tree, storage = load_dna_file('dna/toontown_central_2100.dna')
#
# # a = storage.suit_point_map[241]
# # b = storage.suit_point_map[379]
# # b2 = storage.suit_point_map[242]
#
# path = [431, 180, 181, 187, 188, 385, 383, 198, 199, 206, 209, 212, 220, 221, 222, 226, 228, 230, 231, 232, 238, 240, 241, 379, 242, 243, 251, 252, 253, 244, 245, 380, 246, 247, 239, 233, 234, 229, 227, 223, 224, 214, 215, 208,
#  207, 200, 201, 382, 384, 189, 190, 182, 183, 184, 436, 433, 178, 167, 166, 165, 162, 163, 155, 156, 147, 146, 145, 339, 140, 141, 131, 439, 332, 133, 123, 386, 388, 392, 391, 119, 109, 110, 107, 106, 105, 397, 97, 98, 87, 88,
#  402, 79, 80, 404, 406, 71, 67, 409, 410, 413, 503, 504, 505, 506, 54, 46, 47, 40, 272, 41, 35, 36, 32, 27, 29, 20, 22, 23, 262, 426, 9, 425, 423, 420, 421, 424, 11, 6, 427, 261, 17, 18, 19, 24, 25, 26, 31, 33, 34, 37, 419, 418,
#  438, 45, 51, 494, 495, 498, 500, 412, 408, 72, 69, 407, 405, 76, 77, 78, 401, 85, 86, 95, 96, 396, 100, 113, 111, 112, 118, 390, 389, 387, 122, 127, 128, 331, 440, 130, 138, 139, 338, 150, 149, 148, 153, 154, 160, 161, 168, 170,
#  172, 430, 431, 180, 181, 187, 188, 385, 383]
#
# sll = SuitLegList(path, storage)
# print('t', sll.get_start_time(60))