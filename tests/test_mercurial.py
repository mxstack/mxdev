from unittest.mock import patch
from utils import Process

import os
import pytest


class TestMercurial:
    @pytest.mark.skip("Needs rewrite")
    def testUpdateWithoutRevisionPin(self, develop, src, tempdir):
        from mxdev.vcs.commands import CmdCheckout
        from mxdev.vcs.commands import CmdUpdate

        repository = tempdir["repository"]
        os.mkdir(repository)
        process = Process(cwd=repository)
        process.check_call(f"hg init {repository}")

        foo = repository["foo"]
        foo.create_file("foo")
        process.check_call(f"hg add {foo}", echo=False)
        process.check_call(f"hg commit {foo} -m foo -u test", echo=False)
        bar = repository["bar"]
        bar.create_file("bar")
        process.check_call(f"hg add {bar}", echo=False)
        process.check_call(f"hg commit {bar} -m bar -u test", echo=False)
        develop.sources = {
            "egg": dict(
                kind="hg",
                name="egg",
                url=f"{repository}",
                path=os.path.join(src, "egg"),
            )
        }
        _log = patch("mxdev.vcs.mercurial.logger")
        log = _log.__enter__()
        try:
            CmdCheckout(develop)(develop.parser.parse_args(["co", "egg"]))
            assert set(os.listdir(os.path.join(src, "egg"))) == {".hg", "bar", "foo"}
            CmdUpdate(develop)(develop.parser.parse_args(["up", "egg"]))
            assert set(os.listdir(os.path.join(src, "egg"))) == {".hg", "bar", "foo"}
            assert log.method_calls == [
                ("info", ("Cloned 'egg' with mercurial.",), {}),
                ("info", ("Updated 'egg' with mercurial.",), {}),
                ("info", ("Switched 'egg' to default.",), {}),
            ]
        finally:
            _log.__exit__(None, None, None)

    @pytest.mark.skip("Needs rewrite")
    def testUpdateWithRevisionPin(self, develop, src, tempdir):
        from mxdev.vcs.commands import CmdCheckout
        from mxdev.vcs.commands import CmdUpdate

        repository = tempdir["repository"]
        os.mkdir(repository)
        process = Process(cwd=repository)
        lines = process.check_call(f"hg init {repository}")
        foo = repository["foo"]
        foo.create_file("foo")
        lines = process.check_call(f"hg add {foo}", echo=False)

        # create branch for testing
        lines = process.check_call("hg branch test", echo=False)

        lines = process.check_call(f"hg commit {foo} -m foo -u test", echo=False)

        # get comitted rev
        lines = process.check_call(f"hg log {foo}", echo=False)

        try:
            # XXX older version
            rev = lines[0].split()[1].split(b":")[1]
        except Exception:
            rev = lines[0].split()[1]

        # return to default branch
        lines = process.check_call("hg branch default", echo=False)

        bar = repository["bar"]
        bar.create_file("bar")
        lines = process.check_call(f"hg add {bar}", echo=False)
        lines = process.check_call(f"hg commit {bar} -m bar -u test", echo=False)

        # check rev
        develop.sources = {
            "egg": dict(
                kind="hg",
                name="egg",
                rev=rev,
                url=f"{repository}",
                path=os.path.join(src, "egg"),
            )
        }
        CmdCheckout(develop)(develop.parser.parse_args(["co", "egg"]))
        assert set(os.listdir(os.path.join(src, "egg"))) == {".hg", "foo"}
        CmdUpdate(develop)(develop.parser.parse_args(["up", "egg"]))
        assert set(os.listdir(os.path.join(src, "egg"))) == {".hg", "foo"}

        # check branch
        develop.sources = {
            "egg": dict(
                kind="hg",
                name="egg",
                branch="test",
                url=f"{repository}",
                path=os.path.join(src, "egg"),
            )
        }
        CmdCheckout(develop)(develop.parser.parse_args(["co", "egg"]))
        assert set(os.listdir(os.path.join(src, "egg"))) == {".hg", "foo"}
        CmdUpdate(develop)(develop.parser.parse_args(["up", "egg"]))
        assert set(os.listdir(os.path.join(src, "egg"))) == {".hg", "foo"}

        # we can't use both rev and branch
        with pytest.raises(SystemExit):
            develop.sources = {
                "egg": dict(
                    kind="hg",
                    name="egg",
                    branch="test",
                    rev=rev,
                    url=f"{repository}",
                    path=os.path.join(src, "egg-failed"),
                )
            }
            CmdCheckout(develop)(develop.parser.parse_args(["co", "egg"]))
