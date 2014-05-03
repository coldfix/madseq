# test utilities
import unittest

from decimal import Decimal

from pydicti import odicti

# tested module
import madseq


class Test_ElementTransform(unittest.TestCase):

    def test_replace_with_parent(self):
        init_l = Decimal('1.5')
        base = madseq.Element('BASE', 'DRIFT', odicti(l=init_l, k=2))
        elem = madseq.Element(None, 'BASE', odicti(), base)
        transformer = madseq.ElementTransform({})
        tpl, el, l = transformer.slice(elem, 0, 0)
        self.assertEqual(l, init_l)


class Test_rescale_makethin(unittest.TestCase):

    def test_sbend(self):
        l = 3.5
        pi = 3.14
        ratio = 0.3
        sbend = madseq.Element(None, 'SBEND', odicti(angle=pi, hgap=1, L=l))
        scaled = madseq.rescale_makethin(sbend, ratio)
        self.assertEqual(scaled['KNL'], [pi*ratio])
        self.assertEqual(scaled['lrad'], l)  # CHECK
        self.assertEqual(scaled.get('angle'), None)
        self.assertEqual(scaled.get('hgap'), None)
        self.assertEqual(scaled.type, 'multipole')

    def test_quadrupole(self):
        l = 3.5
        pi = 3.14
        ratio = 0.47
        quad = madseq.Element(None, 'QUADRUPOLE', odicti(K1=pi, L=l))
        scaled = madseq.rescale_makethin(quad, ratio)
        self.assertEqual(scaled['KNL'], [0, pi*l])
        self.assertEqual(scaled['lrad'], l)  # CHECK
        self.assertEqual(scaled.get('K1'), None)
        self.assertEqual(scaled.type, 'multipole')

    def test_solenoid(self):
        l = 3.5
        pi = 3.14
        ratio = 0.79
        sol = madseq.Element(None, 'solenoid', odicti(Ks=pi, L=l))
        scaled = madseq.rescale_makethin(sol, ratio)
        self.assertEqual(scaled['ksi'], pi*ratio)
        self.assertEqual(scaled['lrad'], l*ratio)  # CHECK
        self.assertEqual(scaled.get('Ks'), None)
        self.assertEqual(scaled.type, 'solenoid')


class Test_rescale_thick(unittest.TestCase):

    def test_sbend(self):
        l = 1.3
        pi = 3.14
        ratio = 0.2
        el = madseq.Element('foo', 'SBEND', odicti(angle=pi, L=l))
        scaled = madseq.rescale_thick(el, ratio)
        # check that the original element was not modified:
        self.assertFalse(scaled is el)
        self.assertEqual(el['angle'], pi)
        self.assertEqual(el['l'], l)
        # check that the scaled element is scaled correctly:
        self.assertEqual(scaled['angle'], pi * ratio)
        self.assertEqual(scaled['l'], l * ratio)
        self.assertEqual(scaled.type, 'SBEND')
        self.assertEqual(scaled.name, 'foo')

    def test_arbitrary(self):
        l = 1.3
        pi = 3.14
        ratio = 0.2
        el = madseq.Element('foo', 'arbitrary', odicti(angle=pi, L=l))
        scaled = madseq.rescale_thick(el, ratio)
        # check that the original element was not modified:
        self.assertFalse(scaled is el)
        self.assertEqual(el['angle'], pi)
        self.assertEqual(el['l'], l)
        # check that the scaled element is scaled correctly:
        self.assertEqual(scaled['angle'], pi)   # don't scale unknown fields!
        self.assertEqual(scaled['l'], l * ratio)
        self.assertEqual(scaled.type, 'arbitrary')
        self.assertEqual(scaled.name, 'foo')



if __name__ == '__main__':
    unittest.main()
