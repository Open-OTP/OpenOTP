from lark import Lark

import time
t1 = time.time()

with open('dna.lark', 'r') as f:
    dc_parser = Lark(f, start='dna', debug=False, parser='lalr')
    with open('test.dna', 'r') as f2:
        tree = dc_parser.parse(f2.read(),)


print(time.time() - t1)
