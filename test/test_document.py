# test utilities
import unittest

from decimal import Decimal

# tested module
import madseq


class Test_Document(unittest.TestCase):

    def test_parse_line(self):

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


if __name__ == '__main__':
    unittest.main()
