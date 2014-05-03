# test utilities
import unittest

from decimal import Decimal

from pydicti import dicti

# tested module
import madseq


class TestUtils(unittest.TestCase):

    def test_none_checked(self):
        tostr = madseq.none_checked(str)
        self.assertEqual(tostr(None), None)
        self.assertEqual(tostr(1), '1')

    def test_stri(self):
        stri = madseq.stri
        self.assertEqual(stri("HeLLo"), "helLO")
        self.assertEqual("HeLLo", stri("helLO"))
        self.assertNotEqual(stri("HeLLo"), "WOrld")
        self.assertNotEqual("HeLLo", stri("WOrld"))
        s = "HEllO wORld"
        self.assertEqual('%s' % (stri(s),), s)

    def test_Re(self):
        Re = madseq.Re
        r1 = Re('hello')
        r2 = Re(r1, 'world')
        self.assertTrue(r1.search(' helloworld '))
        self.assertFalse(r1.search('yelloworld'))
        self.assertTrue(r2.match('helloworld anything'))
        self.assertFalse(r2.match(' helloworld anything'))

class test_Parse(unittest.TestCase):

    def test_Number(self):
        parse = madseq.parse_number
        self.assertEqual(parse('-13'), -13)
        self.assertEqual(parse('1.2e1'), Decimal('12.0'))

    def test_Document_parse_line(self):

        parse = madseq.Document.parse_line
        Element = madseq.Element

        self.assertEqual(list(parse(' \t ')),
                         [''])

        self.assertEqual(list(parse(' \t ! a comment; ! ')),
                         ['! a comment; ! '])

        self.assertEqual(list(parse(' use, z=23.23e2; k: z; !')),
                         ['!',
                          Element(None, 'use', {'z': Decimal('23.23e2')}),
                          Element('k', 'z', {})])

    def test_Symbolic(self):

        i = madseq.parse_number('-13')
        f = madseq.parse_number('12.')
        s = madseq.Symbolic.parse('pi')

        self.assertEqual(str(f + s), "12 + pi")
        self.assertEqual(str(s - f), "pi - 12")
        self.assertEqual(str(i + f * s), "-13 + (12 * pi)")
        self.assertEqual(str(s / s), "pi / pi")



class test_regex(unittest.TestCase):

    def setUp(self):
        name = self._testMethodName.split('_', 1)[1]
        reg = str(getattr(madseq.regex, name)).lstrip('^').rstrip('$')
        self.r = madseq.Re('^', reg , '$')

    def test_number(self):
        self.assertTrue(self.r.match('23'))
        self.assertTrue(self.r.match('23.0'))
        self.assertTrue(self.r.match('-1e+1'))
        self.assertTrue(self.r.match('+2e-3'))
        self.assertFalse(self.r.match(''))
        self.assertFalse(self.r.match('e.'))
        self.assertFalse(self.r.match('.e'))

    def test_thingy(self):
        self.assertTrue(self.r.match('unseparated'))
        self.assertTrue(self.r.match('23'))
        self.assertTrue(self.r.match('23.0'))
        self.assertTrue(self.r.match('-1e+1'))
        self.assertTrue(self.r.match('+2e-3'))
        self.assertFalse(self.r.match('e;'))
        self.assertFalse(self.r.match('e,'))
        self.assertFalse(self.r.match(' e'))
        self.assertFalse(self.r.match('e!'))
        self.assertTrue(self.r.match('"a.1"'))

    def test_identifier(self):
        self.assertTrue(self.r.match('a'))
        self.assertTrue(self.r.match('a1'))
        self.assertTrue(self.r.match('a.1'))
        self.assertFalse(self.r.match(''))
        self.assertFalse(self.r.match('1a'))

    def test_string(self):
        self.assertTrue(self.r.match('"hello world"'))
        self.assertTrue(self.r.match('"hello !,; world"'))
        self.assertFalse(self.r.match('"foo" bar"'))
        self.assertFalse(self.r.match('foo" bar"'))
        self.assertFalse(self.r.match(''))

    def test_param(self):
        self.assertTrue(self.r.match('unseparated'))
        self.assertTrue(self.r.match('23'))
        self.assertTrue(self.r.match('23.0'))
        self.assertTrue(self.r.match('-1e+1'))
        self.assertTrue(self.r.match('+2e-3'))
        self.assertTrue(self.r.match('"hello world"'))
        self.assertFalse(self.r.match('"foo" bar"'))
        self.assertFalse(self.r.match('foo" bar"'))
        self.assertFalse(self.r.match(''))
        self.assertFalse(self.r.match('e;'))
        self.assertFalse(self.r.match('e,'))
        self.assertFalse(self.r.match(' e'))
        self.assertFalse(self.r.match('e!'))

    def test_cmd(self):
        pass

    def test_arg(self):
        pass
    def test_comment_split(self):
        pass
    def test_is_string(self):
        pass
    def test_is_identifier(self):
        pass



class TestElement(unittest.TestCase):

    def test_parse_format_identity(self):
        mad = "name: type, a=97, b=98, c=99, d=100, e=101;"
        el = madseq.Element.parse(mad)
        self.assertEqual(str(mad), mad)
        self.assertEqual(el.c, 99)
        self.assertEqual(el.E, 101)


class TestElementTransform(unittest.TestCase):

    def test_replace_with_parent(self):
        base = madseq.Element('BASE', 'DRIFT', dicti(l=1.5))
        elem = madseq.Element(None, 'BASE', dicti())
        transformer = madseq.ElementTransform({})

        tpl, el, l = transformer.replace(elem, 0, 0, base)
        self.assertEqual(l, 1.5)


class TestMakethin(unittest.TestCase):

    def test_rescale_makethin_sbend(self):
        sbend = madseq.Element(None,
                               'SBEND', dicti(angle=3.14, hgap=1, L=3.5))
        scaled = madseq.rescale_makethin(sbend, 0.5)
        self.assertEqual(scaled.KNL, [1.57])
        self.assertEqual(scaled.get('angle'), None)
        self.assertEqual(scaled.get('hgap'), None)
        self.assertEqual(scaled.type, 'multipole')

    def test_rescale_makethin_quadrupole(self):
        quad = madseq.Element(None, 'QUADRUPOLE', dicti(K1=3, L=2.5))
        scaled = madseq.rescale_makethin(quad, 0.5)
        self.assertEqual(scaled.KNL, [0, 7.5])
        self.assertEqual(scaled.get('K1'), None)
        self.assertEqual(scaled.type, 'multipole')

    def test_rescale_thick(self):
        pi = 3.14
        el = madseq.Element(None, 'SBEND', {'angle': pi, 'L': 1})
        scaled = madseq.rescale_thick(el, 0.5)
        self.assertEqual(scaled.angle, pi/2)
        self.assertEqual(scaled.type, 'SBEND')


class TestSlice(unittest.TestCase):
    pass

class TestFile(unittest.TestCase):
    pass

class TestJson(unittest.TestCase):
    pass

# execute tests if this file is invoked directly:
if __name__ == '__main__':
    unittest.main()

