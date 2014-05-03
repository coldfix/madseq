# test utilities
import unittest

from decimal import Decimal

from pydicti import dicti

# tested module
import madseq


class Test_ElementTransform(unittest.TestCase):

    def test_replace_with_parent(self):
        init_l = Decimal('1.5')
        base = madseq.Element('BASE', 'DRIFT', dicti(l=init_l, k=2))
        elem = madseq.Element(None, 'BASE', dicti(), base)
        transformer = madseq.ElementTransform({})
        tpl, el, l = transformer.slice(elem, 0, 0)
        self.assertEqual(l, init_l)


class Test_rescale_makethin(unittest.TestCase):

    def test_sbend(self):
        sbend = madseq.Element(None,
                               'SBEND', dicti(angle=3.14, hgap=1, L=3.5))
        scaled = madseq.rescale_makethin(sbend, 0.5)
        self.assertEqual(scaled['KNL'], [1.57])
        self.assertEqual(scaled.get('angle'), None)
        self.assertEqual(scaled.get('hgap'), None)
        self.assertEqual(scaled.type, 'multipole')

    def test_quadrupole(self):
        quad = madseq.Element(None, 'QUADRUPOLE', dicti(K1=3, L=2.5))
        scaled = madseq.rescale_makethin(quad, 0.5)
        self.assertEqual(scaled['KNL'], [0, 7.5])
        self.assertEqual(scaled.get('K1'), None)
        self.assertEqual(scaled.type, 'multipole')


class Test_rescale_thick(unittest.TestCase):

    def test_sbend(self):
        pi = 3.14
        el = madseq.Element(None, 'SBEND', {'angle': pi, 'L': 1})
        scaled = madseq.rescale_thick(el, 0.5)
        self.assertEqual(scaled['angle'], pi/2)
        self.assertEqual(scaled.type, 'SBEND')


if __name__ == '__main__':
    unittest.main()
