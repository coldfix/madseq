# test utilities
import unittest

from pydicti import dicti

# tested module
import madseq



class Test_Element(unittest.TestCase):

    def test_parse_format_identity(self):
        mad = "name: type, a=97, b=98, c=99, d=100, e=101;"
        el = madseq.Element.parse(mad)
        self.assertEqual(str(mad), mad)
        self.assertEqual(el['c'], 99)
        self.assertEqual(el['E'], 101)

    def test_deep_lookup(self):
        el0 = madseq.Element(None, None, dicti(a='a0', b='b0', c='c0'))
        el1 = madseq.Element(None, None, dicti(a='a1', b='b1', d='d1'), el0)
        el2 = madseq.Element(None, None, dicti(a='a2'), el1)
        self.assertEqual(el2['a'], 'a2')
        self.assertEqual(el2['b'], 'b1')
        self.assertEqual(el2['c'], 'c0')
        self.assertEqual(el2['d'], 'd1')


if __name__ == '__main__':
    unittest.main()
