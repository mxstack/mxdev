import doctest
import mxdev.vcs.cvs
import unittest


def test_suite():
    return unittest.TestSuite([doctest.DocTestSuite(mxdev.vcs.cvs)])
