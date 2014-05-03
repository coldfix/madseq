# test utilities
import unittest

# tested module
import madseq


class Test_regex(unittest.TestCase):

    """Test the functionality of the madseq.regex parsing expressions."""

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
        self.assertTrue(self.r.match('"foo bar"'))
        self.assertTrue(self.r.match('"foo !,; bar"'))
        self.assertFalse(self.r.match('"foo" bar"'))
        self.assertFalse(self.r.match('foo" bar"'))
        self.assertFalse(self.r.match(''))

    def test_param(self):
        self.assertTrue(self.r.match('unseparated'))
        self.assertTrue(self.r.match('23'))
        self.assertTrue(self.r.match('23.0'))
        self.assertTrue(self.r.match('-1e+1'))
        self.assertTrue(self.r.match('+2e-3'))
        self.assertTrue(self.r.match('"foo bar"'))
        self.assertFalse(self.r.match('"foo" bar"'))
        self.assertFalse(self.r.match('foo" bar"'))
        self.assertFalse(self.r.match(''))
        self.assertFalse(self.r.match('e;'))
        self.assertFalse(self.r.match('e,'))
        self.assertFalse(self.r.match(' e'))
        self.assertFalse(self.r.match('e!'))

    def test_cmd(self):
        # TODO: command without arguments or name
        self.assertTrue(self.r.match('sbend, l=1;'))
        self.assertTrue(self.r.match('s: sbend;'))
        self.assertTrue(self.r.match('multipole, l=0, knl={0, 1.2e3};'))
        self.assertTrue(self.r.match('quadrupole, k1=(alpha+PI)*4.2e1;'))
        self.assertTrue(self.r.match('quadrupole, plain;'))
        self.assertFalse(self.r.match(';'))
        self.assertFalse(self.r.match('xxx'))
        self.assertFalse(self.r.match('xxx:;'))
        self.assertFalse(self.r.match('xxx: 3;'))
        self.assertFalse(self.r.match('xxx| foo, bla;'))

    def test_arg(self):
        # TODO: plain word parameters (without value)
        # TODO: spaces in thingy expressions
        self.assertEqual(self.r.match(', par=val').groups(),
                         ('par', '=', 'val'))
        self.assertEqual(self.r.match(', par := 3.2 ').groups(),
                         ('par', ':=', '3.2'))
        self.assertEqual(self.r.match(', par := (a+b)*c ').groups(),
                         ('par', ':=', '(a+b)*c'))

    def test_comment_split(self):
        self.assertEqual(self.r.match(' text ! comment ! bla').groups(),
                         (' text ', '! comment ! bla'))

    def test_is_string(self):
        self.assertEqual(self.r.match('  " foo * bar"').groups(),
                         (' foo * bar',))

    def test_is_identifier(self):
        self.assertEqual(self.r.match(' some0alpha1 ').groups(),
                         ('some0alpha1',))


if __name__ == '__main__':
    unittest.main()
