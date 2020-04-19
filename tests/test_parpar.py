from par import parparser
import unittest

TEST_CONFIG = """
[General]
float1=3.55
float2=.10
float3=7.
int_test=25932
hex_test=0xFFF
binary_test=0b1111111
str_test=Test**5t9854g32r2
"""


class TestParPar(unittest.TestCase):
    def test1(self):
        conf = parparser.parse_par(TEST_CONFIG)
        self.assertEqual(conf['General.float1'], 3.55)
        self.assertEqual(conf['General.float2'], 0.1)
        self.assertEqual(conf['General.float3'], 7.0)
        self.assertEqual(conf['General.int_test'], 25932)
        self.assertEqual(conf['General.hex_test'], 0xFFF)
        self.assertEqual(conf['General.binary_test'], 0b1111111)


if __name__ == '__main__':
    unittest.main()
