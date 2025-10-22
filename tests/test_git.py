# pylint: disable=redefined-outer-name
from logging import getLogger
from logging import Logger
from unittest.mock import patch
from utils import vcs_checkout
from utils import vcs_status
from utils import vcs_update

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
    sources = {"egg": dict(vcs="git", name="egg", url=str(repository.base), path=str(path))}
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
            ("info", (f"Cloned 'egg' with git from '{repository.url}'.",), {}),
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
            ("info", (f"Cloned 'egg' with git from '{repository.url}'.",), {}),
            ("info", ("Updated 'egg' with git.",), {}),
            ("info", ("Switching to remote branch 'master'.",), {}),
        ]
        captured = capsys.readouterr()
        # git output varies between versions...
        assert "Already up to date" in captured.out.replace("-", " ")
        status = vcs_status(sources, verbose=True)
        assert status == {"egg": ("clean", "## master...origin/master\n")}


def test_update_git_tag_to_new_tag(mkgitrepo, src):
    """Test that updating from one git tag to another works correctly.

    This test reproduces issue #46: changing the branch option from one tag
    to another tag should update the checkout to the new tag.

    Regression in v4.x - worked in v2.x
    """
    repository = mkgitrepo("repository")
    # Create initial content and tag it as 1.0.0
    repository.add_file("foo", msg="Initial")
    repository("git tag 1.0.0", echo=False)

    # Create more content and tag as 2.0.0
    repository.add_file("bar", msg="Second")
    repository("git tag 2.0.0", echo=False)

    path = src / "egg"

    # Initial checkout with tag 1.0.0
    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            branch="1.0.0",  # This is actually a tag, not a branch
            url=str(repository.base),
            path=str(path),
        )
    }
    packages = ["egg"]
    verbose = False

    # Checkout at tag 1.0.0
    vcs_checkout(sources, packages, verbose)
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo"}

    # Verify we're at tag 1.0.0
    result = repository.process.check_call(f"git -C {path} describe --tags", echo=False)
    current_tag = result[0].decode("utf8").strip()
    assert current_tag == "1.0.0"

    # Now update the sources to use tag 2.0.0
    sources["egg"]["branch"] = "2.0.0"

    # Update should switch to tag 2.0.0
    # BUG: This will fail because the code treats tags as branches
    vcs_update(sources, packages, verbose)

    # After update, we should have both foo and bar (tag 2.0.0)
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo", path / "bar"}

    # Verify we're now at tag 2.0.0
    result = repository.process.check_call(f"git -C {path} describe --tags", echo=False)
    current_tag = result[0].decode("utf8").strip()
    assert current_tag == "2.0.0"


def test_offline_prevents_vcs_operations(mkgitrepo, src):
    """Test that offline mode prevents VCS fetch/update operations.

    This test reproduces issue #34: offline setting should prevent VCS operations
    but is currently being ignored.

    When offline=True is set (either in config or via CLI --offline flag),
    mxdev should NOT perform any VCS operations (no fetch, no update).
    """
    repository = mkgitrepo("repository")
    path = src / "egg"

    # Create initial content
    repository.add_file("foo", msg="Initial")

    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            url=str(repository.base),
            path=str(path),
        )
    }
    packages = ["egg"]
    verbose = False

    # Initial checkout (not offline)
    vcs_checkout(sources, packages, verbose, offline=False)
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo"}

    # Add new content to remote repository
    repository.add_file("bar", msg="Second")

    # Try to update with offline=True
    # BUG: This should NOT fetch/update anything, but currently it does
    # because offline parameter is ignored
    vcs_update(sources, packages, verbose, offline=True)

    # After offline update, should still have only initial content (foo)
    # The "bar" file should NOT be present because offline prevented the update
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo"}

    # Now update with offline=False to verify update works when not offline
    vcs_update(sources, packages, verbose, offline=False)

    # After normal update, should have both files
    assert {x for x in path.iterdir()} == {path / ".git", path / "foo", path / "bar"}
