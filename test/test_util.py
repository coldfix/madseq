# test utilities
import unittest

# tested module
import madseq


class Test_none_checked(unittest.TestCase):

    def test_tostr(self):
        tostr = madseq.none_checked(str)
        self.assertEqual(tostr(None), None)
        self.assertEqual(tostr(1), '1')


class Test_stri(unittest.TestCase):

    def test_comparison(self):
        stri = madseq.stri
        self.assertEqual(stri("HeLLo"), "helLO")
        self.assertEqual("HeLLo", stri("helLO"))
        self.assertNotEqual(stri("HeLLo"), "WOrld")
        self.assertNotEqual("HeLLo", stri("WOrld"))

    def test___str__(self):
        stri = madseq.stri
        s = "HEllO wORld"
        self.assertEqual('%s' % (stri(s),), s)


class Test_Re(unittest.TestCase):

    def test_Re(self):
        r1 = madseq.Re('hello')
        r2 = madseq.Re(r1, 'world')
        self.assertEqual(str(r1), 'hello')
        self.assertEqual(str(r2), 'helloworld')
        self.assertTrue(r1.search(' helloworld '))
        self.assertFalse(r1.search('yelloworld'))
        self.assertTrue(r2.match('helloworld anything'))
        self.assertFalse(r2.match(' helloworld anything'))


if __name__ == '__main__':
    unittest.main()
