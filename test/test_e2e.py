# test utilities
import unittest

from decimal import Decimal
from inspect import cleandoc
if str is bytes:
    from io import BytesIO as StringIO
else:
    from io import StringIO

from pydicti import odicti

# tested module
import madseq


class Test_IntegrationTests(unittest.TestCase):

    """
    'Almost' end-to-end tests.
    """

    maxDiff = 2000

    def _check(self, input_text, slicing, output_text):

        input_file = cleandoc(input_text).splitlines()
        output_file = StringIO()

        node_transform = madseq.SequenceTransform(slicing or [])

        madseq.Document.parse(input_file).transform(node_transform).dump(output_file, 'madx')

        self.assertEqual(output_file.getvalue().splitlines(),
                         cleandoc(output_text).splitlines())


    def test_simple_template(self):

        self._check(
            r"""
            qp: quadrupole, l=1, k1=2;

            seq: sequence, refer=centre;
            qp;
            qp, l=2;
            endsequence;
            """,

            None,

            """
            qp: quadrupole, l=1, k1=2;

            seq: sequence, refer=centre, L=3;
            qp, at=0.5;
            qp, l=2, at=2;
            endsequence;
            """)

    def test_deep_template(self):

        self._check(
            r"""
            qq: quadrupole, l=1;
            qp: qq, k1=2;

            seq: sequence, refer=centre;
            qp;
            qp, l=2;
            endsequence;
            """,

            None,

            """
            qq: quadrupole, l=1;
            qp: qq, k1=2;

            seq: sequence, refer=centre, L=3;
            qp, at=0.5;
            qp, l=2, at=2;
            endsequence;
            """)

    def test_simple_slice_thick(self):

        self._check(
            r"""
            qq: quadrupole, l=1;
            qp: qq, k1=2;

            seq: sequence, refer=centre;
            q1: qp;
            q2: qp, l=2;
            endsequence;
            """,

            [{'name': 'q2',
              'slice': 2},
             {'type': 'quadrupole',
              'slice': 4}],

            """
            qq: quadrupole, l=1;
            qp: qq, k1=2;

            seq: sequence, refer=centre, L=3;
            q1..0: qp, L=0.25, at=0.125;
            q1..1: qp, L=0.25, at=0.375;
            q1..2: qp, L=0.25, at=0.625;
            q1..3: qp, L=0.25, at=0.875;
            q2..0: qp, L=1, at=1.5;
            q2..1: qp, L=1, at=2.5;
            endsequence;
            """)

    def test_makethin(self):

        self._check(
            r"""
            qq: quadrupole, l=1;
            qp: qq, k1=2;

            seq: sequence, refer=centre;
            q1: qp;
            q2: qp, l=2;
            endsequence;
            """,

            [{'name': 'q2',
              'slice': 2,
              'makethin': True},
             {'type': 'quadrupole',
              'slice': 4,
              'makethin': True,
              'style': 'loop'}],

            """
            qq: quadrupole, l=1;
            qp: qq, k1=2;

            seq: sequence, refer=centre, L=3;
            i = 0;
            while (i < 4) {
            multipole, KNL={0,0.5}, lrad=0.25, at=0 + ((i + 0.5) * 0.25);
            i = i + 1;
            }
            q2..0: multipole, KNL={0,2}, lrad=1, at=1.5;
            q2..1: multipole, KNL={0,2}, lrad=1, at=2.5;
            endsequence;
            """)

    def test_make_template(self):

        self._check(
            r"""
            seq: sequence, refer=centre;
            qp: quadrupole, k1=2, l=1;
            endsequence;
            """,

            [{'name': 'qp',
              'slice': 4,
              'makethin': True,
              'template': True}],

            """
            ! Template elements for seq:
            qp: multipole, KNL={0,0.5}, lrad=0.25;

            seq: sequence, refer=centre, L=1;
            qp, at=0.125;
            qp, at=0.375;
            qp, at=0.625;
            qp, at=0.875;
            endsequence;
            """)


if __name__ == '__main__':
    unittest.main()
