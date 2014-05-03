# test utilities
import unittest

from decimal import Decimal

# tested module
import madseq


class Test_Symbolic(unittest.TestCase):

    def test_compose(self):
        i = -13
        f = Decimal('12.0')
        s = madseq.Identifier('pi')
        self.assertEqual((f + s).value, "12 + pi")
        self.assertEqual((s - f).value, "pi - 12")
        self.assertEqual((i + f * s).value, "-13 + (12 * pi)")
        self.assertEqual((s / s).value, "pi / pi")



class test_parsing(unittest.TestCase):

    def test_parse_number(self):
        parse = madseq.parse_number
        self.assertEqual(parse('-13'), -13)
        self.assertEqual(parse('1.2e1'), Decimal('12.0'))


if __name__ == '__main__':
    unittest.main()
