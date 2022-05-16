import unittest
import doctest
import mxdev.vcs.cvs


def test_suite():
    return unittest.TestSuite([doctest.DocTestSuite(mxdev.vcs.cvs)])
