# test utilities
import unittest

from decimal import Decimal

from pydicti import odicti

# tested module
import madseq
from madseq import format_value


pi = madseq.Identifier('pi')


class Test_Value(unittest.TestCase):

    def test_argument(self):
        val = madseq.Value(1, ':=')
        self.assertEqual(val.argument, ':=1')

    def _check_parse(self, expr, expected):
        value = madseq.Value.parse(expr)
        self.assertEqual(type(value), type(expected))
        self.assertEqual(value, expected)

    def test_parse(self):
        self._check_parse('-2', -2)
        self._check_parse('0.72e-1', Decimal('0.072'))
        self._check_parse('  "d * r /sa" ', 'd * r /sa')
        self._check_parse(' { 1.2, 3 } ', madseq.Array([Decimal('1.2'), 3]))
        self._check_parse('foo', madseq.Identifier('foo'))
        self._check_parse('foo*bar', madseq.Composed('foo*bar'))


class Test_Array(unittest.TestCase):

    def test_parse(self):
        # TODO: empty array
        parse = madseq.Array.parse
        self.assertEqual(parse(' {0.1e1 , 2, 3.3}').value,
                         [Decimal('1.0'), 2, Decimal('3.3')])
        self.assertRaises(ValueError, parse, " drsa")

    def test_expr(self):
        a = madseq.Array([1,2.2])
        self.assertEqual(a.expr, '{1,2.2}')


class Test_Symbolic(unittest.TestCase):

    def _test_composed_expr(self, composed, expr):
        self.assertEqual(composed.expr, expr)
        self.assertEqual(composed.safe_expr, '(' + expr + ')')

    def test_add(self):
        self._test_composed_expr(pi + 2, "pi + 2")
        self._test_composed_expr(12.1 + pi, "12.1 + pi")

    def test_sub(self):
        self._test_composed_expr(pi - 12.1, "pi - 12.1")
        self._test_composed_expr(1 - pi, "1 - pi")

    def test_mul(self):
        self._test_composed_expr(12.1 * pi, "12.1 * pi")
        self._test_composed_expr(pi * 12.1, "pi * 12.1")

    def test_div(self):
        self._test_composed_expr(pi / 1, "pi / 1")
        self._test_composed_expr(1 / pi, "1 / pi")

    def test_chained_composition(self):
        self._test_composed_expr((1 + pi) / 2, "(1 + pi) / 2")


class test_format_value(unittest.TestCase):

    """Test :func:`format_value` for standard types."""

    def test_Decimal(self):
        self.assertEqual(format_value(Decimal('1.2e-1')), '0.12')

    def test_str(self):
        self.assertEqual(format_value(" foo bar "), '" foo bar "')

    def test_float(self):
        self.assertEqual(format_value(-1.2), '-1.2')

    def test_int(self):
        self.assertEqual(format_value(-13), '-13')

    def test_tuple(self):
        self.assertEqual(format_value((1.1, 2)), '{1.1,2}')

    def test_list(self):
        self.assertEqual(format_value([1.1, 2]), '{1.1,2}')

    def test_unknown(self):
        self.assertRaises(TypeError, format_value, set())


class test_parsing(unittest.TestCase):

    def test_parse_number(self):
        parse_number = madseq.parse_number
        self.assertEqual(parse_number('-13'), -13)
        self.assertEqual(parse_number('1.2e1'), Decimal('12.0'))
        self.assertTrue(isinstance(parse_number('1.2e1'), Decimal))
        self.assertRaises(ValueError, parse_number, 'x')
        self.assertRaises(ValueError, parse_number, '1.2 x')

    def test_parse_string(self):
        parse_string = madseq.parse_string
        self.assertEqual(parse_string(' " foo bar " '), " foo bar ")
        self.assertRaises(ValueError, parse_string, 'x " foo * bar "')
        self.assertRaises(ValueError, parse_string, '" foo * bar')

    def test_parse_args(self):
        parse_args = madseq.parse_args
        self.assertEqual(parse_args(''),
                         odicti())
        self.assertEqual(parse_args(', a := 3'),
                         odicti([('a', 3)]))
        self.assertEqual(parse_args(', a =3, crd := pi'),
                         odicti([('a', 3), ('crd', pi)]))


if __name__ == '__main__':
    unittest.main()
