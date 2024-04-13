from mxdev.tests.utils import GitRepo
from mxdev.tests.utils import vcs_checkout
from mxdev.tests.utils import vcs_update
from unittest.mock import patch

import os
import pytest


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_checkout_with_submodule(mkgitrepo, src, caplog, git_allow_file_protocol):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a' in itith
    """

    submodule_name = "submodule_a"
    submodule_a = mkgitrepo(submodule_name)
    submodule_a.add_file("foo")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule_a, submodule_name)

    sources = {"egg": dict(vcs="git", name="egg", url=egg.url, path=src / "egg")}
    with patch("mxdev.vcs.git.logger") as log:
        # CmdCheckout(develop)(develop.parser.parse_args(["co", "egg"]))
        vcs_checkout(sources, ["egg"], verbose=True)
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {".git", "foo"}
        assert (
            log.method_calls
            == log.method_calls
            == [
                ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {}),
                (
                    "info",
                    ("Initialized 'egg' submodule at '%s' with git." % submodule_name,),
                    {},
                ),
            ]
        )


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_checkout_with_two_submodules(mkgitrepo, src, git_allow_file_protocol):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a'
    and a submodule 'submodule_b' in it.
    """

    submodule_name = "submodule_a"
    submodule = mkgitrepo(submodule_name)
    submodule_b_name = "submodule_b"
    submodule_b = mkgitrepo(submodule_b_name)

    submodule.add_file("foo")
    submodule_b.add_file("foo_b")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule, submodule_name)
    egg.add_submodule(submodule_b, submodule_b_name)

    sources = {"egg": dict(vcs="git", name="egg", url=egg.url, path=src / "egg")}

    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, ["egg"], verbose=False)
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            "submodule_b",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {".git", "foo"}
        assert set(os.listdir(src / "egg" / submodule_b_name)) == {
            ".git",
            "foo_b",
        }
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {}),
            (
                "info",
                ("Initialized 'egg' submodule at '%s' with git." % submodule_name,),
                {},
            ),
            (
                "info",
                ("Initialized 'egg' submodule at '%s' with git." % submodule_b_name,),
                {},
            ),
        ]


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_checkout_with_two_submodules_recursive(
    mkgitrepo, src, git_allow_file_protocol
):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a'
    and a submodule 'submodule_b' in it.
    but this time we test it with the "recursive" option
    """

    submodule_name = "submodule_a"
    submodule = mkgitrepo(submodule_name)
    submodule_b_name = "submodule_b"
    submodule_b = mkgitrepo(submodule_b_name)

    submodule.add_file("foo")
    submodule_b.add_file("foo_b")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule, submodule_name)
    egg.add_submodule(submodule_b, submodule_b_name)

    sources = {"egg": dict(vcs="git", name="egg", url=egg.url, path=src / "egg")}

    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, ["egg"], verbose=False, update_git_submodules="recursive")
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            "submodule_b",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {".git", "foo"}
        assert set(os.listdir(src / "egg" / submodule_b_name)) == {
            ".git",
            "foo_b",
        }
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {}),
        ]


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_update_with_submodule(mkgitrepo, src, git_allow_file_protocol):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it.
    Add a new 'submodule_b' to 'egg' and check it succesfully initializes.
    """
    submodule_name = "submodule_a"
    submodule = mkgitrepo(submodule_name)
    submodule.add_file("foo")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule, submodule_name)

    sources = {"egg": dict(vcs="git", name="egg", url=egg.url, path=src / "egg")}
    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, ["egg"], verbose=False)
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {".git", "foo"}
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {}),
            (
                "info",
                ("Initialized 'egg' submodule at '%s' with git." % submodule_name,),
                {},
            ),
        ]

    submodule_b_name = "submodule_b"
    submodule_b = mkgitrepo(submodule_b_name)
    submodule_b.add_file("foo_b")
    egg.add_submodule(submodule_b, submodule_b_name)

    with patch("mxdev.vcs.git.logger") as log:
        vcs_update(sources, ["egg"], verbose=False)
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            "submodule_b",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_b_name)) == {
            ".git",
            "foo_b",
        }
        assert log.method_calls == [
            ("info", ("Updated 'egg' with git.",), {}),
            ("info", ("Switching to branch 'master'.",), {}),
            (
                "info",
                ("Initialized 'egg' submodule at '%s' with git." % submodule_b_name,),
                {},
            ),
        ]


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_update_with_submodule_recursive(mkgitrepo, src, git_allow_file_protocol):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it.
    Add a new 'submodule_b' to 'egg' and check it succesfully initializes.
    """
    submodule_name = "submodule_a"
    submodule = mkgitrepo(submodule_name)
    submodule.add_file("foo")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule, submodule_name)

    sources = {"egg": dict(vcs="git", name="egg", url=egg.url, path=src / "egg")}
    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, ["egg"], verbose=False, update_git_submodules="recursive")
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {".git", "foo"}
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {}),
        ]

    submodule_b_name = "submodule_b"
    submodule_b = mkgitrepo(submodule_b_name)
    submodule_b.add_file("foo_b")
    egg.add_submodule(submodule_b, submodule_b_name)

    with patch("mxdev.vcs.git.logger") as log:
        vcs_update(sources, ["egg"], verbose=False, update_git_submodules="recursive")
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            "submodule_b",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_b_name)) == {
            ".git",
            "foo_b",
        }
        assert log.method_calls == [
            ("info", (f"Updated 'egg' with git.",)),
            ("info", (f"Switching to branch 'master'.",)),
            (
                "info",
                (f"Initialized 'egg' submodule at '{submodule_b_name}' with git.",),
            ),
        ]


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_checkout_with_submodules_option_never(mkgitrepo, src, git_allow_file_protocol):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it
    without initializing the submodule, restricted by global 'never'
    """

    submodule_name = "submodule_a"
    submodule_a = mkgitrepo(submodule_name)
    submodule_a.add_file("foo")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule_a, submodule_name)

    # develop.update_git_submodules = "never"
    sources = {"egg": dict(vcs="git", name="egg", url=egg.url, path=src / "egg")}
    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, ["egg"], verbose=False, update_git_submodules="never")
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == set()
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {})
        ]


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_checkout_with_submodules_option_never_source_always(
    mkgitrepo, src, git_allow_file_protocol
):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it
    and a module 'egg2' with the same submodule, initializing only the submodule
    on egg that has the 'always' option
    """

    submodule_name = "submodule_a"
    submodule_a = mkgitrepo(submodule_name)
    submodule_a.add_file("foo")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule_a, submodule_name)

    egg2 = mkgitrepo("egg2")
    egg2.add_file("bar")
    egg2.add_submodule(submodule_a, submodule_name)

    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            url=egg.url,
            path=src / "egg",
            submodules="always",
        ),
        "egg2": dict(vcs="git", name="egg2", url=egg2.url, path=src / "egg2"),
    }
    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(
            sources, ["egg", "egg2"], verbose=False, update_git_submodules="never"
        )
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {"foo", ".git"}
        assert set(os.listdir(src / "egg2")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg2" / submodule_name)) == set()

        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {}),
            (
                "info",
                ("Initialized 'egg' submodule at '%s' with git." % submodule_name,),
                {},
            ),
            ("info", ("Cloned 'egg2' with git from '%s'." % egg2.url,), {}),
        ]


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_checkout_with_submodules_option_always_source_never(
    mkgitrepo, src, git_allow_file_protocol
):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it
    and a module 'egg2' with the same submodule, not initializing the submodule
    on egg2 that has the 'never' option

    """

    submodule_name = "submodule_a"
    submodule_a = mkgitrepo(submodule_name)
    submodule_a.add_file("foo")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule_a, submodule_name)

    egg2 = mkgitrepo("egg2")
    egg2.add_file("bar")
    egg2.add_submodule(submodule_a, submodule_name)

    sources = {
        "egg": dict(vcs="git", name="egg", url=egg.url, path=src / "egg"),
        "egg2": dict(
            vcs="git",
            name="egg2",
            url=egg2.url,
            path=src / "egg2",
            submodules="never",
        ),
    }
    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, ["egg", "egg2"], verbose=False)
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {"foo", ".git"}
        assert set(os.listdir(src / "egg2")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg2" / submodule_name)) == set()

        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {}),
            (
                "info",
                ("Initialized 'egg' submodule at '%s' with git." % submodule_name,),
                {},
            ),
            ("info", ("Cloned 'egg2' with git from '%s'." % egg2.url,), {}),
        ]


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_update_with_submodule_checkout(mkgitrepo, src, git_allow_file_protocol):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it.
    Add a new 'submodule_b' to 'egg' and check it doesn't get initialized.
    """

    submodule_name = "submodule_a"
    submodule = mkgitrepo(submodule_name)
    submodule.add_file("foo")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule, submodule_name)

    sources = {
        "egg": dict(
            vcs="git",
            name="egg",
            url=egg.url,
            path=src / "egg",
            submodules="checkout",
        )
    }
    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, ["egg"], verbose=False)
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {".git", "foo"}
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {}),
            (
                "info",
                ("Initialized 'egg' submodule at '%s' with git." % submodule_name,),
                {},
            ),
        ]

    submodule_b_name = "submodule_b"
    submodule_b = mkgitrepo(submodule_b_name)
    submodule_b.add_file("foo_b")
    egg.add_submodule(submodule_b, submodule_b_name)

    with patch("mxdev.vcs.git.logger") as log:
        vcs_update(sources, ["egg"], verbose=False)
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            "submodule_b",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_b_name)) == set()
        assert log.method_calls == [
            ("info", ("Updated 'egg' with git.",), {}),
            ("info", ("Switching to branch 'master'.",), {}),
        ]


@pytest.mark.skipif(
    condition=os.name == "nt", reason="submodules seem not to work on windows"
)
def test_update_with_submodule_dont_update_previous_submodules(
    mkgitrepo, src, git_allow_file_protocol
):
    """
    Tests the checkout of a module 'egg' with a submodule 'submodule_a' in it.
    Commits changes in the detached submodule, and checks update didn't break
    the changes.
    """

    submodule_name = "submodule_a"
    submodule = mkgitrepo(submodule_name)
    submodule.add_file("foo")
    egg = mkgitrepo("egg")
    egg.add_file("bar")
    egg.add_submodule(submodule, submodule_name)

    sources = {"egg": dict(vcs="git", name="egg", url=egg.url, path=src / "egg")}
    with patch("mxdev.vcs.git.logger") as log:
        vcs_checkout(sources, ["egg"], verbose=False)
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {".git", "foo"}
        assert log.method_calls == [
            ("info", ("Cloned 'egg' with git from '%s'." % egg.url,), {}),
            (
                "info",
                ("Initialized 'egg' submodule at '%s' with git." % submodule_name,),
                {},
            ),
        ]

    repo = GitRepo(src / "egg" / submodule_name)
    repo.setup_user()
    repo.add_file("newfile")

    with patch("mxdev.vcs.git.logger") as log:
        vcs_update(sources, ["egg"], verbose=False, force=True)
        assert set(os.listdir(src / "egg")) == {
            "submodule_a",
            ".git",
            "bar",
            ".gitmodules",
        }
        assert set(os.listdir(src / "egg" / submodule_name)) == {
            ".git",
            "foo",
            "newfile",
        }
        assert log.method_calls == [
            ("info", ("Updated 'egg' with git.",), {}),
            ("info", ("Switching to branch 'master'.",), {}),
        ]
