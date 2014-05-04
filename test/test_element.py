# test utilities
import unittest

from pydicti import odicti

# tested module
import madseq


class Test_Element(unittest.TestCase):

    def test_parse(self):
        mad = "name: type, a=97, b=98, c=99, d=100, e=101;"
        el = madseq.Element.parse(mad)
        self.assertEqual(el['c'], 99)
        self.assertEqual(el['E'], 101)

    def test_format(self):
        el = madseq.Element('foo', 'bar', odicti([('a', 1), ('b', 2)]))
        self.assertEqual(str(el),
                         'foo: bar, a=1, b=2;')

    def test_parse_format_identity(self):
        mad = "name: type, a=97, b=98, c=99, d=100, e=101;"
        el = madseq.Element.parse(mad)
        self.assertEqual(str(mad), mad)

    def test_base_type(self):
        el0 = madseq.Element(None, 'a', None)
        el1 = madseq.Element(None, 'b', None, el0)
        el2 = madseq.Element(None, 'c', None, el1)
        self.assertEqual(el0.base_type, 'a')
        self.assertEqual(el1.base_type, 'a')
        self.assertEqual(el2.base_type, 'a')

    def test_all_args(self):
        el0 = madseq.Element(None, None, odicti(a='a0', b='b0', c='c0'))
        el1 = madseq.Element(None, None, odicti(a='a1', b='b1', d='d1'), el0)
        el2 = madseq.Element(None, None, odicti(a='a2'), el1)
        self.assertEqual(el2.all_args,
                         odicti([('c', 'c0'), ('b', 'b1'),
                                 ('d', 'd1'), ('a', 'a2')]))

    def test_copy(self):
        el = madseq.Element(None, None, odicti(a=1))
        copy = el.copy()
        self.assertFalse(el is copy)
        self.assertFalse(el.args is copy.args)
        self.assertEqual(el, copy)
        self.assertEqual(el.args, copy.args)

    def test_contains(self):
        el = madseq.Element(None, None, odicti(a=1))
        self.assertTrue('a' in el)
        self.assertFalse('b' in el)

    def test_delitem(self):
        el0 = madseq.Element(None, None, odicti(a=1))
        el1 = madseq.Element(None, None, odicti(b=2, c=3), el0)
        def delitem(d, key):
            del d[key]
        self.assertRaises(KeyError, delitem, el1, 'a')
        del el1['b']
        self.assertEqual(el1.args, odicti(c=3))

    def test_getitem(self):
        el0 = madseq.Element(None, None, odicti(a='a0', b='b0', c='c0'))
        el1 = madseq.Element(None, None, odicti(a='a1', b='b1', d='d1'), el0)
        el2 = madseq.Element(None, None, odicti(a='a2'), el1)
        self.assertEqual(el2['a'], 'a2')
        self.assertEqual(el2['b'], 'b1')
        self.assertEqual(el2['c'], 'c0')
        self.assertEqual(el2['d'], 'd1')

    def test_setitem(self):
        el0 = madseq.Element(None, None, odicti(a=1))
        el1 = madseq.Element(None, None, odicti(), el0)
        el1['a'] = 2
        self.assertEqual(el1['a'], 2)
        self.assertEqual(el0['a'], 1)

    def test_get(self):
        el0 = madseq.Element(None, None, odicti(a=1))
        el1 = madseq.Element(None, None, odicti(b=2, c=3), el0)
        self.assertEqual(el1.get('a', 9), 1)
        self.assertEqual(el1.get('b', 9), 2)
        self.assertEqual(el1.get('c', 9), 3)
        self.assertEqual(el1.get('x', 9), 9)
        self.assertEqual(el1.get('x'), None)

    def test_pop(self):
        el0 = madseq.Element(None, None, odicti(a=1))
        el1 = madseq.Element(None, None, odicti(b=2, c=3), el0)
        self.assertRaises(KeyError, el1.pop, 'x')
        self.assertEqual(el1.pop('x', 3), 3)

        self.assertEqual(el1.pop('a'), 1)
        self.assertEqual(el0['a'], 1)       # el0 must not be modified!

        self.assertEqual(el1.pop('b'), 2)
        self.assertEqual(el1.args, odicti(c=3))

    def test_eq(self):
        el0 = madseq.Element('a', 'b', odicti(c=1))
        self.assertEqual(el0, madseq.Element('a', 'b', odicti(c=1)))
        self.assertNotEqual(el0, madseq.Element('x', 'b', odicti(c=1)))
        self.assertNotEqual(el0, madseq.Element('a', 'x', odicti(c=1)))
        self.assertNotEqual(el0, madseq.Element('a', 'b', odicti(x=1)))
        self.assertNotEqual(el0, madseq.Element('a', 'b', odicti(c=2)))


class Test_Sequence(unittest.TestCase):

    def test_detect(self):

        input_elements = [
            madseq.Element(None, 'outer', None),
            madseq.Element('seq', 'sequence', odicti(l=1)),
            madseq.Element(None, 'inner', odicti(k=2)),
            madseq.Element(None, 'endsequence', odicti()),
            madseq.Element(None, 'outer', None)
        ]

        s = list(madseq.Sequence.detect(input_elements))
        seq = s[1]

        self.assertTrue(s[0] is input_elements[0])
        self.assertTrue(seq.head is input_elements[1])
        self.assertEqual(len(seq.body), 1)
        self.assertTrue(seq.body[0] is input_elements[2])
        self.assertTrue(seq.tail is input_elements[3])
        self.assertTrue(s[2] is input_elements[4])

        self.assertEqual(seq.name, 'seq')
        self.assertEqual(str(seq), ("seq: sequence, l=1;\n"
                                    "inner, k=2;\n"
                                    "endsequence;"))


if __name__ == '__main__':
    unittest.main()
