from lark import Transformer, Tree


class ParTransformer(Transformer):
    def __init__(self, filename):
        Transformer.__init__(self, visit_tokens=False)
        self.filename = filename

    def par(self, args):
        entries = []
        sections = []

        for arg in args:
            if isinstance(arg, ParSection):
                sections.append(arg)
            else:
                entries.append(arg)

        entries = dict(entries)
        sections = dict(((section.name, section) for section in sections))

        parf = ParFile(self.filename, entries, sections)

        return Tree('par', [parf])

    def section(self, args):
        section_name = args.pop(0).value[1:-1]
        sections = args

        return ParSection(section_name, sections)

    def entry(self, args):
        key = args.pop(0).value

        if len(args):
            value = args.pop(0).value
        else:
            value = None

        return key, value


from lark import Lark


def parse_par_file(fp, debug=False):
    with open('par/par.lark', 'r') as lark_f:
        transformer = ParTransformer(fp)
        dc_parser = Lark(lark_f, start='par', debug=debug, parser='lalr', lexer='contextual', transformer=transformer)
        with open(fp, 'r') as f2:
            tree = dc_parser.parse(f2.read(),)
            return tree.children[0]


class ParFile:
    def __init__(self, name: str, entries: dict, sections: dict):
        self.name = name
        self.entries = entries
        self.sections = sections

    def __getitem__(self, key):
        if key in self.sections:
            return self.sections[key]

        if '.' in key:
            first, rest = key.split('.', 1)
            return self.sections[first][rest]

        return self.entries[key]

    def __repr__(self):
        return f'ParFile({self.name} {self.entries} {self.sections})'


class ParSection:
    def __init__(self, name: str, entries):
        self.name = name
        self.entries = dict(entries)

    def __getitem__(self, key):
        return self.entries[key]

    def __repr__(self):
        return f'ParSection(name={self.name} entries={self.entries})'


def pack_uint8(n: int):
    return bytes(n & 0xFF)


def pack_uint16(n: int):
    return bytes((n & 0xFF, (n >> 8) & 0xFF))


def pack_uint32(n: int):
    return bytes((n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF, (n >> 24) & 0xFF))


def pack_uint64(n: int):
    return bytes((n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF, (n >> 24) & 0xFF, (n >> 32) & 0xFF,
                  (n >> 40) & 0xFF, (n >> 48) & 0xFF, (n >> 56) & 0xFF))


def get_signed_int(number: int, bits: int):
    mask = (1 << bits) - 1
    if number & (1 << (bits - 1)):
        return number | ~mask
    else:
        return number & mask
