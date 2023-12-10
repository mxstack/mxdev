# pylint: disable=redefined-outer-name
from logging import getLogger
from logging import Logger
from mxdev.tests.utils import vcs_checkout
from mxdev.tests.utils import vcs_status
from mxdev.tests.utils import vcs_update
from struct import pack
from unittest.mock import patch

import os
import pytest


logger: Logger = getLogger("vcs_test_git")


def create_default_content(repository) -> str:
    # Create default content and branches in a repository.
    # Return a revision number.
    repository.add_file("foo", msg="Initial")
    # create branch for testing
    repository("git checkout -b test", echo=False)
    repository.add_file("foo2")
    # get comitted rev
    lines = repository("git log", echo=False)
    rev = lines[0].split()[1]
    # return to default branch
    repository("git checkout master", echo=False)
    repository.add_file("bar")
    # Return revision of one of the commits, the one that adds the
    # foo2 file.
    return rev.decode("utf8")


def test_update_with_revision_pin_rev(mkgitrepo, src):
    repository = mkgitrepo("repository")
    rev = create_default_content(repository)
    path = src / "egg"
    # check rev
    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            rev=rev,
            url=str(repository.base),
            path=str(path),
        )
    }

    packages = ["egg"]
    verbose = False

    assert not os.path.exists(path)
    vcs_checkout(sources, packages, verbose)
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo", path / "foo2"}

    vcs_checkout(sources, packages, verbose)
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo", path / "foo2"}

    vcs_update(sources, packages, verbose)
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo", path / "foo2"}


def test_update_with_revision_pin_branch(mkgitrepo, src):
    repository = mkgitrepo("repository")
    rev = create_default_content(repository)
    # check branch
    packages = ["egg"]
    verbose = False
    path = src / "egg"
    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            branch="test",
            url=str(repository.base),
            path=str(path),
        )
    }
    vcs_checkout(sources, packages, verbose)
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo", path / "foo2"}
    vcs_update(sources, packages, verbose)
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo", path / "foo2"}
    states = vcs_status(sources)

    # switch implicitly to master branch
    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            branch="master",
            url=str(repository.base),
            path=str(path),
        )
    }
    vcs_update(sources, packages, verbose)
    assert {x for x in path.iterdir()} == {path / ".git", path / "bar", path / "foo"}

    # Switch to specific revision, then switch back to master branch.
    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            rev=rev,
            url=str(repository.base),
            path=str(path),
        )
    }
    vcs_update(sources, packages, verbose)

    assert {x for x in path.iterdir()} == {path / ".git", path / "foo", path / "foo2"}
    sources = {
        "egg": dict(vcs="git", name="egg", url=str(repository.base), path=str(path))
    }
    vcs_update(sources, packages, verbose)

    assert {x for x in path.iterdir()} == {path / ".git", path / "bar", path / "foo"}

    vcs_status(sources)
    # we can't use both rev and branch
    with pytest.raises(SystemExit):
        sources = {
            "egg": dict(
                vcs="git",
                name="egg",
                branch="test",
                rev=rev,
                url=str(repository.base),
                path=src / "egg-failed",
            )
        }
        vcs_checkout(sources, packages, verbose)


def test_update_without_revision_pin(mkgitrepo, src, capsys, caplog):
    repository = mkgitrepo("repository")
    repository.add_file("foo")
    repository.add_file("bar")
    repository.add_branch("develop")
    packages = ["egg"]
    path = src / "egg"

    sources = {"egg": dict(vcs="git", name="egg", url=repository.url, path=str(path))}
    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, packages, verbose=False)
        assert {x for x in path.iterdir()} == {
            path / ".git",
            path / "bar",
            path / "foo",
        }
        captured = capsys.readouterr()
        assert captured.out.startswith("Initialized empty Git repository in")
        vcs_update(sources, packages, verbose=False)

        assert {x for x in path.iterdir()} == {
            path / ".git",
            path / "bar",
            path / "foo",
        }
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % repository.url,), {}),
            ("info", ("Updated 'egg' with git.",), {}),
            ("info", ("Switching to remote branch 'master'.",), {}),
        ]
        captured = capsys.readouterr()
        assert captured.err == ""
        status = vcs_status(sources, verbose=True)
        captured = capsys.readouterr()
        assert status == {"egg": ("clean", "## master...origin/master\n")}


def test_update_verbose(mkgitrepo, src, capsys):
    repository = mkgitrepo("repository")
    repository.add_file("foo")
    repository.add_file("bar")
    repository.add_branch("develop")
    path = src / "egg"
    sources = {"egg": dict(vcs="git", name="egg", url=repository.url, path=str(path))}
    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, ["egg"], verbose=False)
        assert {x for x in path.iterdir()} == {
            path / ".git",
            path / "bar",
            path / "foo",
        }
        captured = capsys.readouterr()
        assert captured.out.startswith("Initialized empty Git repository in")
        vcs_update(sources, ["egg"], verbose=True)
        assert {x for x in path.iterdir()} == {
            path / ".git",
            path / "bar",
            path / "foo",
        }
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % repository.url,), {}),
            ("info", ("Updated 'egg' with git.",), {}),
            ("info", ("Switching to remote branch 'master'.",), {}),
        ]
        captured = capsys.readouterr()
        # git output varies between versions...
        assert "Already up to date" in captured.out.replace("-", " ")
        status = vcs_status(sources, verbose=True)
        assert status == {"egg": ("clean", "## master...origin/master\n")}
