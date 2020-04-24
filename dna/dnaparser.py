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

        start = self.suit_points[edge.start]
        end = self.suit_points[edge.end]

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
                self.discover_connections(self.suit_points[edge.end], graph_id)

    def get_suit_path(self, start_point: DNASuitPoint, end_point: DNASuitPoint, min_length: int, max_length: int) -> List[int]:
        if start_point.graph_id != end_point.graph_id:
            return []

        path = []
        return self.get_suit_path_breadth_first(path, start_point, end_point, min_length, max_length)

    def get_suit_path_breadth_first(self, path, start_point, end_point, min_length, max_length) -> List[int]:
        path.append(start_point.index)

        path_size = 1
        if min_length - 1 > 1:
            v10 = min_length - 2
            path_size = min_length - 1
            while True:
                self.generate_next_suit_path_chain(path)
                v10 -= 1
                if not v10:
                    break

        if path_size < max_length:
            while True:
                path_size += 1
                if self.consider_next_suit_path_chain(path, end_point):
                    return path
                if path_size > max_length:
                    break

        return path

    def generate_next_suit_path_chain(self, path: List[int]):
        start_index = path[-1]

        for edge in self.suit_edges[start_index]:
            end_point = self.suit_points[edge.end]
            if edge.end == start_index:
                continue

            if edge.end in path:
                continue

            if end_point.point_type == SuitPointType.FRONT_DOOR_POINT:
                continue

            if end_point.point_type == SuitPointType.SIDE_DOOR_POINT:
                continue

            path.append(edge.end)
            return

    def consider_next_suit_path_chain(self, path: List[int], end_point: DNASuitPoint):
        start_index = path[-1]

        for edge in self.suit_edges[start_index]:
            if edge.end == start_index:
                continue

            if edge.end in path:
                continue

            if edge.end == end_point.index:
                path.append(edge.end)
                return True

            if end_point.point_type == SuitPointType.FRONT_DOOR_POINT:
                continue

            if end_point.point_type == SuitPointType.SIDE_DOOR_POINT:
                continue

            path.append(edge.end)
            return False


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

        x, y, z = x.value, y.value, z.value

        point_type = SuitPointType[point_type]
        point = DNASuitPoint(index, point_type, Point3(x, y, z), landmark_index)
        return point

    def suit_edge(self, args):
        _, a, b = args
        suit_edge = DNASuitEdge(a, b, -1)
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


def traverse(node, storage: DNAStorage):
    if isinstance(node, DNAGroup):
        storage.groups[node.name] = node
    if isinstance(node, DNASuitEdge):
        if node.start not in storage.suit_edges:
            storage.suit_edges[node.start] = list()
        storage.suit_edges[node.start].append(node)
    elif isinstance(node, DNASuitPoint):
        storage.suit_points.append(node)
        storage.suit_point_map[node.index] = node
    elif isinstance(node, DNALandmarkBuilding):
        block = int(node.name.split(':')[0][2:])
        zone_id = int(node.vis_group.name.split(':')[0])
        storage.blocks.append(block)
        storage.block_zones[block] = zone_id
        storage.block_building_types[block] = node.building_type

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

