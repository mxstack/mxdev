# pylint: disable=redefined-outer-name
from logging import Logger, getLogger
from typing import Any, Dict
from mxdev.tests.utils import Process
from unittest.mock import patch

from mxdev.vcs.common import WorkingCopies
from .fixtures import src, mkgitrepo, tempdir

import os
import pytest
import shutil


logger: Logger = getLogger("vcs_test_git")


def create_default_content(repository):
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
    return rev


def vcs_checkout(sources, packages, verbose, update_git_submodules:str = "always", always_accept_server_certificate:bool = True):
    workingcopies = WorkingCopies(sources=sources, threads=1)
    workingcopies.checkout(sorted(packages),
                            verbose=verbose,
                            submodules=update_git_submodules,
                            always_accept_server_certificate=always_accept_server_certificate)


def vcs_update(sources: Dict[str, Any], packages, verbose, update_git_submodules:str = "always", always_accept_server_certificate:bool = True):
    workingcopies = WorkingCopies(sources=sources, threads=1)
    workingcopies.update(sorted(packages),
                            verbose=verbose,
                            submodules=update_git_submodules,
                            always_accept_server_certificate=always_accept_server_certificate)


def vcs_status(sources: Dict[str, Any], verbose=False):
    workingcopies = WorkingCopies(sources=sources, threads=1)
    res = {}
    for k in sources:
        res[k] = workingcopies.status(sources[k], verbose=verbose)

    return res


def test_update_with_revision_pin(mkgitrepo, src):
    repository = mkgitrepo("repository")
    rev = create_default_content(repository)

    # check rev
    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            rev=rev,
            url="%s" % repository.base,
            path=src["egg"],
        )
    }

    packages = ['egg']
    verbose = False

    assert not os.path.exists(src['egg'])
    vcs_checkout(sources, packages, verbose)
    assert set(os.listdir(src['egg'])) == set(('.git', 'foo', 'foo2'))

    vcs_checkout(sources, packages, verbose)
    assert set(os.listdir(src["egg"])) == {".git", "foo", "foo2"}
    vcs_update(sources, packages, verbose)
    assert set(os.listdir(src["egg"])) == {".git", "foo", "foo2"}

    shutil.rmtree(src["egg"])

    # check branch
    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            branch="test",
            url="%s" % repository.base,
            path=src["egg"],
        )
    }
    vcs_checkout(sources, packages, verbose)
    assert set(os.listdir(src["egg"])) == {".git", "foo", "foo2"}
    vcs_update(sources, packages, verbose)
    assert set(os.listdir(src["egg"])) == {".git", "foo", "foo2"}
    states = vcs_status(sources)

    # switch implicitly to master branch
    sources = {
        "egg": dict(
            vcs="git", name="egg", 
            branch="master", 
            url="%s" % repository.base, path=src["egg"]
        )
    }
    vcs_update(sources, packages, verbose)
    assert set(os.listdir(src["egg"])) == {".git", "bar", "foo"}

    # Switch to specific revision, then switch back to master branch.
    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            rev=rev,
            url="%s" % repository.base,
            path=src["egg"],
        )
    }
    vcs_update(sources, packages, verbose)

    assert set(os.listdir(src["egg"])) == {".git", "foo", "foo2"}
    sources = {
        "egg": dict(
            vcs="git", name="egg", url="%s" % repository.base, path=src["egg"]
        )
    }
    vcs_update(sources, packages, verbose)

    assert set(os.listdir(src["egg"])) == {".git", "bar", "foo"}

    vcs_status(sources)
    # we can't use both rev and branch
    with pytest.raises(SystemExit):
        sources = {
            "egg": dict(
                vcs="git",
                name="egg",
                branch="test",
                rev=rev,
                url="%s" % repository.base,
                path=src["egg-failed"],
            )
        }
        vcs_checkout(sources, packages, verbose)


def test_update_without_revision_pin(mkgitrepo, src, capsys):
    repository = mkgitrepo("repository")
    repository.add_file("foo")
    repository.add_file("bar")
    repository.add_branch("develop")
    packages = ['egg']

    sources = {
        "egg": dict(vcs="git", name="egg", url=repository.url, path=src["egg"])
    }
    _log = patch("mxdev.vcs.git.logger")
    log = _log.__enter__()
    try:
        vcs_checkout(sources, packages, verbose=False)
        assert set(os.listdir(src["egg"])) == {".git", "bar", "foo"}
        captured = capsys.readouterr()
        assert captured.out.startswith("Initialized empty Git repository in")
        vcs_update(sources, packages, verbose=False)

        assert set(os.listdir(src["egg"])) == {".git", "bar", "foo"}
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % repository.url,), {}),
            ("info", ("Updated 'egg' with git.",), {}),
            ("info", ("Switching to remote branch 'remotes/origin/master'.",), {}),
        ]
        captured = capsys.readouterr()
        assert captured.out == ""
        status = vcs_status(sources, verbose=True)
        captured = capsys.readouterr()
        assert status == {'egg': ('clean', '## master...origin/master\n')}

    finally:
        _log.__exit__(None, None, None)


def test_update_verbose(mkgitrepo, src, capsys):
    repository = mkgitrepo("repository")
    repository.add_file("foo")
    repository.add_file("bar")
    repository.add_branch("develop")
    sources = {
        "egg": dict(vcs="git", name="egg", url=repository.url, path=src["egg"])
    }
    _log = patch("mxdev.vcs.git.logger")
    log = _log.__enter__()
    try:
        vcs_checkout(sources, ["egg"], verbose=False)
        assert set(os.listdir(src["egg"])) == {".git", "bar", "foo"}
        captured = capsys.readouterr()
        assert captured.out.startswith("Initialized empty Git repository in")
        vcs_update(sources, ["egg"], verbose=True)
        assert set(os.listdir(src["egg"])) == {".git", "bar", "foo"}
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % repository.url,), {}),
            ("info", ("Updated 'egg' with git.",), {}),
            ("info", ("Switching to remote branch 'remotes/origin/master'.",), {}),
        ]
        captured = capsys.readouterr()
        older = "* develop\n  remotes/origin/HEAD -> origin/develop\n  remotes/origin/develop\n  remotes/origin/master\nBranch master set up to track remote branch master from origin.\n  develop\n* master\n  remotes/origin/HEAD -> origin/develop\n  remotes/origin/develop\n  remotes/origin/master\nAlready up-to-date.\n\n"
        newer = "* develop\n  remotes/origin/HEAD -> origin/develop\n  remotes/origin/develop\n  remotes/origin/master\nBranch 'master' set up to track remote branch 'master' from 'origin'.\n  develop\n* master\n  remotes/origin/HEAD -> origin/develop\n  remotes/origin/develop\n  remotes/origin/master\nAlready up to date.\n\n"
        # git output varies between versions...
        assert captured.out in [older, newer]
        status = vcs_status(sources, verbose=True)
        assert status == {'egg': ('clean', '## master...origin/master\n')}

    finally:
        _log.__exit__(None, None, None)
