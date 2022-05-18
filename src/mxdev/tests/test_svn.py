from mxdev.tests.utils import Process
from unittest.mock import patch

import os
import pytest


class TestSVN:
    @pytest.fixture(autouse=True)
    def clear_svn_caches(self):
        from mxdev.vcs.svn import SVNWorkingCopy

        SVNWorkingCopy._clear_caches()

    @pytest.mark.skip("Needs rewrite")
    def testUpdateWithoutRevisionPin(self, develop, src, tempdir):
        from mxdev.vcs.commands import CmdCheckout
        from mxdev.vcs.commands import CmdUpdate

        process = Process()
        repository = tempdir["repository"]
        process.check_call("svnadmin create %s" % repository)
        checkout = tempdir["checkout"]
        process.check_call(f"svn checkout file://{repository} {checkout}", echo=False)
        foo = checkout["foo"]
        foo.create_file("foo")
        process.check_call("svn add %s" % foo, echo=False)
        process.check_call("svn commit %s -m foo" % foo, echo=False)
        bar = checkout["bar"]
        bar.create_file("bar")
        process.check_call("svn add %s" % bar, echo=False)
        process.check_call("svn commit %s -m bar" % bar, echo=False)
        develop.sources = {
            "egg": dict(
                kind="svn", name="egg", url="file://%s" % repository, path=src["egg"]
            )
        }
        _log = patch("mxdev.vcs.svn.logger")
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(["co", "egg"]))
            assert set(os.listdir(src["egg"])) == {".svn", "bar", "foo"}
            CmdUpdate(develop)(develop.parser.parse_args(["up", "egg"]))
            assert set(os.listdir(src["egg"])) == {".svn", "bar", "foo"}
            assert log.method_calls == [
                ("info", ("Checked out 'egg' with subversion.",), {}),
                ("info", ("Updated 'egg' with subversion.",), {}),
            ]
        finally:
            _log.__exit__(None, None, None)

    @pytest.mark.skip("Needs rewrite")
    def testUpdateWithRevisionPin(self, develop, src, tempdir):
        from mxdev.vcs.commands import CmdCheckout
        from mxdev.vcs.commands import CmdUpdate

        process = Process()
        repository = tempdir["repository"]
        process.check_call("svnadmin create %s" % repository)
        checkout = tempdir["checkout"]
        process.check_call(f"svn checkout file://{repository} {checkout}", echo=False)
        foo = checkout["foo"]
        foo.create_file("foo")
        process.check_call("svn add %s" % foo, echo=False)
        process.check_call("svn commit %s -m foo" % foo, echo=False)
        bar = checkout["bar"]
        bar.create_file("bar")
        process.check_call("svn add %s" % bar, echo=False)
        process.check_call("svn commit %s -m bar" % bar, echo=False)
        develop.sources = {
            "egg": dict(
                kind="svn", name="egg", url="file://%s@1" % repository, path=src["egg"]
            )
        }
        CmdCheckout(develop)(develop.parser.parse_args(["co", "egg"]))
        assert set(os.listdir(src["egg"])) == {".svn", "foo"}
        CmdUpdate(develop)(develop.parser.parse_args(["up", "egg"]))
        assert set(os.listdir(src["egg"])) == {".svn", "foo"}
