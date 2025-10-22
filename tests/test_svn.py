from unittest.mock import patch
from utils import Process

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
        process.check_call(f"svnadmin create {repository}")
        checkout = tempdir["checkout"]
        process.check_call(f"svn checkout file://{repository} {checkout}", echo=False)
        foo = checkout["foo"]
        foo.create_file("foo")
        process.check_call(f"svn add {foo}", echo=False)
        process.check_call(f"svn commit {foo} -m foo", echo=False)
        bar = checkout["bar"]
        bar.create_file("bar")
        process.check_call(f"svn add {bar}", echo=False)
        process.check_call(f"svn commit {bar} -m bar", echo=False)
        develop.sources = {"egg": dict(kind="svn", name="egg", url=f"file://{repository}", path=src["egg"])}
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
        process.check_call(f"svnadmin create {repository}")
        checkout = tempdir["checkout"]
        process.check_call(f"svn checkout file://{repository} {checkout}", echo=False)
        foo = checkout["foo"]
        foo.create_file("foo")
        process.check_call(f"svn add {foo}", echo=False)
        process.check_call(f"svn commit {foo} -m foo", echo=False)
        bar = checkout["bar"]
        bar.create_file("bar")
        process.check_call(f"svn add {bar}", echo=False)
        process.check_call(f"svn commit {bar} -m bar", echo=False)
        develop.sources = {"egg": dict(kind="svn", name="egg", url=f"file://{repository}@1", path=src["egg"])}
        CmdCheckout(develop)(develop.parser.parse_args(["co", "egg"]))
        assert set(os.listdir(src["egg"])) == {".svn", "foo"}
        CmdUpdate(develop)(develop.parser.parse_args(["up", "egg"]))
        assert set(os.listdir(src["egg"])) == {".svn", "foo"}
