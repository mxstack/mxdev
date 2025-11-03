"""Additional tests for git.py to increase coverage to >90%."""

from unittest.mock import Mock
from unittest.mock import patch

import pytest


def test_git_error_class():
    """Test GitError exception class."""
    from mxdev.vcs.common import WCError
    from mxdev.vcs.git import GitError

    assert issubclass(GitError, WCError)


def test_git_working_copy_duplicate_rev_and_revision():
    """Test GitWorkingCopy raises error when both rev and revision are specified."""
    from mxdev.vcs.git import GitWorkingCopy

    source = {
        "name": "test-package",
        "url": "https://github.com/test/repo.git",
        "path": "/tmp/test",
        "rev": "abc123",
        "revision": "def456",
    }

    with pytest.raises(ValueError, match="duplicate revision options"):
        GitWorkingCopy(source)


def test_git_working_copy_revision_converted_to_rev():
    """Test that 'revision' is converted to 'rev'."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "revision": "abc123",
        }

        wc = GitWorkingCopy(source)
        assert "rev" in wc.source
        assert wc.source["rev"] == "abc123"
        assert "revision" not in wc.source


def test_git_working_copy_rev_removes_default_branch():
    """Test that specifying rev removes default branch 'main'."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "rev": "abc123",
            "branch": "main",
        }

        wc = GitWorkingCopy(source)
        assert "branch" not in wc.source


def test_git_working_copy_rev_with_non_main_branch_errors():
    """Test that specifying both rev and non-main branch causes exit."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "rev": "abc123",
            "branch": "develop",
        }

        with pytest.raises(SystemExit):
            GitWorkingCopy(source)


def test_git_version_returncode_error():
    """Test git_version handles git --version failure."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("error", "error message")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(SystemExit):
                wc.git_version()


def test_git_version_parse_error():
    """Test git_version handles unparseable version output."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("invalid version output", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(SystemExit):
                wc.git_version()


def test_git_version_too_old():
    """Test git_version exits on git < 1.5."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("git version 1.4.0", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(SystemExit):
                wc.git_version()


def test_git_version_parsing_two_parts():
    """Test git_version parses version with 2 parts."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("git version 2.5", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            version = wc.git_version()
            assert version == (2, 5)


def test_git_version_parsing_four_parts():
    """Test git_version parses version with 4 parts."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("git version 2.30.1.2", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            version = wc.git_version()
            assert version == (2, 30, 1, 2)


def test_remote_branch_prefix_old_git():
    """Test _remote_branch_prefix for git < 1.6.3."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        with patch.object(wc, "git_version", return_value=(1, 5, 0)):
            assert wc._remote_branch_prefix == "origin"


def test_remote_branch_prefix_new_git():
    """Test _remote_branch_prefix for git >= 1.6.3."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        with patch.object(wc, "git_version", return_value=(2, 30, 0)):
            assert wc._remote_branch_prefix == "remotes/origin"


def test_git_merge_rbranch_failure():
    """Test git_merge_rbranch handles git branch failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "branch command failed")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(GitError, match="git branch -a"):
                wc.git_merge_rbranch("", "")


def test_git_merge_rbranch_missing_branch_accept():
    """Test git_merge_rbranch with missing branch and accept_missing=True."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "branch": "nonexistent",
        }

        wc = GitWorkingCopy(source)

        # Mock git branch -a to return branches without our target branch
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("* main\n  develop\n", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            stdout, stderr = wc.git_merge_rbranch("", "", accept_missing=True)
            assert stdout == "* main\n  develop\n"


def test_git_merge_rbranch_missing_branch_no_accept():
    """Test git_merge_rbranch with missing branch and accept_missing=False."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "branch": "nonexistent",
        }

        wc = GitWorkingCopy(source)

        # Mock git branch -a to return branches without our target branch
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("* main\n  develop\n", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(SystemExit):
                wc.git_merge_rbranch("", "", accept_missing=False)


def test_git_merge_rbranch_merge_failure():
    """Test git_merge_rbranch handles merge failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "branch": "main",
        }

        wc = GitWorkingCopy(source)

        def mock_run_git_side_effect(commands, **kwargs):
            mock_proc = Mock()
            if "branch" in commands:
                mock_proc.returncode = 0
                mock_proc.communicate.return_value = ("* main\n", "")
            else:  # merge command
                mock_proc.returncode = 1
                mock_proc.communicate.return_value = ("", "merge conflict")
            return mock_proc

        with patch.object(wc, "run_git", side_effect=mock_run_git_side_effect):
            with patch.object(wc, "git_version", return_value=(2, 30, 0)):
                with pytest.raises(GitError, match="git merge"):
                    wc.git_merge_rbranch("", "")


def test_git_checkout_existing_path(tmp_path):
    """Test git_checkout when path already exists."""
    from mxdev.vcs.git import GitWorkingCopy

    test_dir = tmp_path / "test-package"
    test_dir.mkdir()

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": str(test_dir),
        }

        wc = GitWorkingCopy(source)
        result = wc.git_checkout(submodules="never")

        # Should return None when path exists
        assert result is None


def test_git_checkout_clone_failure():
    """Test git_checkout handles clone failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/nonexistent/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "clone failed")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(GitError, match="git cloning"):
                wc.git_checkout(submodules="never")


def test_git_checkout_with_depth():
    """Test git_checkout with depth parameter."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test-depth",
            "depth": "1",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("cloned", "")

        with patch.object(wc, "run_git", return_value=mock_process) as mock_run:
            wc.git_checkout(submodules="never")

            # Verify --depth was included in clone command
            call_args = mock_run.call_args[0][0]
            assert "--depth" in call_args
            assert "1" in call_args


def test_git_checkout_with_git_clone_depth_env():
    """Test git_checkout uses GIT_CLONE_DEPTH environment variable."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.git.GIT_CLONE_DEPTH", "5"):
        with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
            source = {
                "name": "test-package",
                "url": "https://github.com/test/repo.git",
                "path": "/tmp/test-env-depth",
            }

            wc = GitWorkingCopy(source)

            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = ("cloned", "")

            with patch.object(wc, "run_git", return_value=mock_process) as mock_run:
                wc.git_checkout(submodules="never")

                # Verify --depth with env value was included
                call_args = mock_run.call_args[0][0]
                assert "--depth" in call_args
                assert "5" in call_args


def test_git_checkout_with_pushurl():
    """Test git_checkout with pushurl."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test-pushurl",
            "pushurl": "git@github.com:test/repo.git",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            with patch.object(wc, "git_set_pushurl", return_value=("", "")) as mock_pushurl:
                wc.git_checkout(submodules="never")
                # Verify git_set_pushurl was called
                mock_pushurl.assert_called_once()


def test_git_set_pushurl_failure():
    """Test git_set_pushurl handles failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "pushurl": "git@github.com:test/repo.git",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "config failed")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(GitError, match="git config"):
                wc.git_set_pushurl("", "")


def test_git_init_submodules_failure():
    """Test git_init_submodules handles failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "submodule init failed")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(GitError, match="git submodule init"):
                wc.git_init_submodules("", "")


def test_git_init_submodules_stderr_output():
    """Test git_init_submodules parses stderr when stdout is empty."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            "",
            "Submodule 'vendor/libs' (https://github.com/vendor/libs.git) registered",
        )

        with patch.object(wc, "run_git", return_value=mock_process):
            stdout, stderr, initialized = wc.git_init_submodules("", "")
            assert "vendor/libs" in initialized


def test_git_update_submodules_failure():
    """Test git_update_submodules handles failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "submodule update failed")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(GitError, match="git submodule update"):
                wc.git_update_submodules("", "")


def test_git_update_submodules_recursive():
    """Test git_update_submodules with recursive flag."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("updated", "")

        with patch.object(wc, "run_git", return_value=mock_process) as mock_run:
            wc.git_update_submodules("", "", recursive=True)

            # Verify recursive flags were included
            call_args = mock_run.call_args[0][0]
            assert "--init" in call_args
            assert "--recursive" in call_args


def test_git_update_submodules_specific():
    """Test git_update_submodules for a specific submodule."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("updated", "")

        with patch.object(wc, "run_git", return_value=mock_process) as mock_run:
            wc.git_update_submodules("", "", submodule="vendor/libs")

            # Verify specific submodule was included
            call_args = mock_run.call_args[0][0]
            assert "vendor/libs" in call_args


def test_checkout_path_not_exist():
    """Test checkout when path doesn't exist."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/nonexistent/test",
        }

        wc = GitWorkingCopy(source)

        with patch.object(wc, "git_checkout", return_value="checkout output") as mock_checkout:
            result = wc.checkout(submodules="never")

            # Should call git_checkout
            mock_checkout.assert_called_once()
            assert result == "checkout output"


def test_checkout_update_needed():
    """Test checkout when update is needed."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        with patch("os.path.exists", return_value=True):
            with patch.object(wc, "should_update", return_value=True):
                with patch.object(wc, "update", return_value="update output") as mock_update:
                    result = wc.checkout()

                    mock_update.assert_called_once()
                    assert result == "update output"


def test_checkout_no_update_doesnt_match():
    """Test checkout when no update and doesn't match."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        with patch("os.path.exists", return_value=True):
            with patch.object(wc, "should_update", return_value=False):
                with patch.object(wc, "matches", return_value=False):
                    result = wc.checkout()

                    # Should return None and log warning
                    assert result is None


def test_matches_failure():
    """Test matches() handles git remote failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "remote show failed")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(GitError, match="git remote"):
                wc.matches()


def test_update_not_matching():
    """Test update when URL doesn't match."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        with patch.object(wc, "matches", return_value=False):
            with patch.object(wc, "status", return_value="clean"):
                with patch.object(wc, "git_update", return_value="updated") as mock_git_update:
                    result = wc.update()

                    # Should still call git_update even if not matching
                    mock_git_update.assert_called_once()


def test_update_dirty_no_force():
    """Test update with dirty status and no force."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        with patch.object(wc, "matches", return_value=True):
            with patch.object(wc, "status", return_value="dirty"):
                with pytest.raises(GitError, match="dirty"):
                    wc.update()


def test_update_dirty_with_force():
    """Test update with dirty status and force=True."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        with patch.object(wc, "matches", return_value=True):
            with patch.object(wc, "status", return_value="dirty"):
                with patch.object(wc, "git_update", return_value="updated") as mock_git_update:
                    result = wc.update(force=True)

                    # Should call git_update when forced
                    mock_git_update.assert_called_once()


def test_git_update_fetch_failure():
    """Test git_update handles fetch failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "fetch failed")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(GitError, match="git fetch"):
                wc.git_update(submodules="never")


def test_status_clean():
    """Test status() returns clean."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("## main...origin/main", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            status = wc.status()
            assert status == "clean"


def test_status_ahead():
    """Test status() returns ahead."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("## main...origin/main [ahead 2]", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            status = wc.status()
            assert status == "ahead"


def test_status_dirty():
    """Test status() returns dirty."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("## main\n M file.txt", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            status = wc.status()
            assert status == "dirty"


def test_status_verbose():
    """Test status() with verbose=True."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        output = "## main\n M file.txt"
        mock_process.communicate.return_value = (output, "")

        with patch.object(wc, "run_git", return_value=mock_process):
            status, stdout = wc.status(verbose=True)
            assert status == "dirty"
            assert stdout == output


def test_git_switch_branch_failure():
    """Test git_switch_branch handles branch -a failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "branch command failed")

        with patch.object(wc, "run_git", return_value=mock_process):
            with patch.object(wc, "git_version", return_value=(2, 30, 0)):
                with pytest.raises(GitError, match="git branch -a"):
                    wc.git_switch_branch("", "")


def test_git_switch_branch_missing_no_accept():
    """Test git_switch_branch with missing branch and accept_missing=False."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "branch": "nonexistent",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("* main\n", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            with pytest.raises(SystemExit):
                wc.git_switch_branch("", "", accept_missing=False)


def test_git_switch_branch_missing_accept():
    """Test git_switch_branch with missing branch and accept_missing=True."""
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "branch": "nonexistent",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("* main\n", "")

        with patch.object(wc, "run_git", return_value=mock_process):
            with patch.object(wc, "git_version", return_value=(2, 30, 0)):
                stdout, stderr = wc.git_switch_branch("", "", accept_missing=True)
                # Should return without error
                assert "main" in stdout


def test_git_switch_branch_checkout_failure():
    """Test git_switch_branch handles checkout failure."""
    from mxdev.vcs.git import GitError
    from mxdev.vcs.git import GitWorkingCopy

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "branch": "develop",
        }

        wc = GitWorkingCopy(source)

        def mock_run_git_side_effect(commands, **kwargs):
            mock_proc = Mock()
            if "branch" in commands:
                mock_proc.returncode = 0
                mock_proc.communicate.return_value = ("* main\n  develop\n", "")
            else:  # checkout command
                mock_proc.returncode = 1
                mock_proc.communicate.return_value = ("", "checkout failed")
            return mock_proc

        with patch.object(wc, "run_git", side_effect=mock_run_git_side_effect):
            with patch.object(wc, "git_version", return_value=(2, 30, 0)):
                with pytest.raises(GitError, match="git checkout"):
                    wc.git_switch_branch("", "")


def test_smart_threading_separates_https_with_pushurl():
    """Test smart threading correctly separates HTTPS packages based on pushurl.

    HTTPS URLs with pushurl should go to parallel queue (other_packages).
    HTTPS URLs without pushurl should go to serial queue (https_packages).
    """
    from mxdev.vcs.common import WorkingCopies

    sources = {
        "https-no-pushurl": {
            "name": "https-no-pushurl",
            "url": "https://github.com/org/repo1.git",
            "path": "/tmp/repo1",
        },
        "https-with-pushurl": {
            "name": "https-with-pushurl",
            "url": "https://github.com/org/repo2.git",
            "path": "/tmp/repo2",
            "pushurl": "git@github.com:org/repo2.git",
        },
        "ssh-url": {
            "name": "ssh-url",
            "url": "git@github.com:org/repo3.git",
            "path": "/tmp/repo3",
        },
        "fs-url": {
            "name": "fs-url",
            "url": "/local/path/repo4",
            "path": "/tmp/repo4",
        },
    }

    wc = WorkingCopies(sources=sources, threads=4, smart_threading=True)
    packages = ["https-no-pushurl", "https-with-pushurl", "ssh-url", "fs-url"]

    https_pkgs, other_pkgs = wc._separate_https_packages(packages)

    # Only HTTPS without pushurl should be in serial queue
    assert https_pkgs == ["https-no-pushurl"]

    # HTTPS with pushurl, SSH, and fs should be in parallel queue
    assert set(other_pkgs) == {"https-with-pushurl", "ssh-url", "fs-url"}


def test_git_set_pushurl_multiple():
    """Test git_set_pushurl with multiple URLs."""
    from mxdev.vcs.git import GitWorkingCopy
    from unittest.mock import Mock
    from unittest.mock import patch

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": "/tmp/test",
            "pushurls": [
                "git@github.com:test/repo.git",
                "git@gitlab.com:test/repo.git",
            ],
            "pushurl": "git@github.com:test/repo.git",
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"output", b"")

        with patch.object(wc, "run_git", return_value=mock_process) as mock_git:
            stdout, stderr = wc.git_set_pushurl(b"", b"")

            # Should be called twice
            assert mock_git.call_count == 2

            # First call: without --add
            first_call_args = mock_git.call_args_list[0][0][0]
            assert first_call_args == [
                "config",
                "remote.origin.pushurl",
                "git@github.com:test/repo.git",
            ]

            # Second call: with --add
            second_call_args = mock_git.call_args_list[1][0][0]
            assert second_call_args == [
                "config",
                "--add",
                "remote.origin.pushurl",
                "git@gitlab.com:test/repo.git",
            ]


def test_git_checkout_with_multiple_pushurls(tempdir):
    """Test git_checkout with multiple pushurls."""
    from mxdev.vcs.git import GitWorkingCopy
    from unittest.mock import Mock
    from unittest.mock import patch

    with patch("mxdev.vcs.common.which", return_value="/usr/bin/git"):
        source = {
            "name": "test-package",
            "url": "https://github.com/test/repo.git",
            "path": str(tempdir / "test-multi-pushurl"),
            "pushurls": [
                "git@github.com:test/repo.git",
                "git@gitlab.com:test/repo.git",
                "git@bitbucket.org:test/repo.git",
            ],
            "pushurl": "git@github.com:test/repo.git",  # First one for compat
        }

        wc = GitWorkingCopy(source)

        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")

        with patch.object(wc, "run_git", return_value=mock_process) as mock_git:
            with patch("os.path.exists", return_value=False):
                wc.git_checkout(submodules="never")

                # Verify git config was called 3 times for pushurls
                config_calls = [call for call in mock_git.call_args_list if "config" in call[0][0]]

                # Should have 3 config calls for the 3 pushurls
                pushurl_config_calls = [call for call in config_calls if "pushurl" in " ".join(call[0][0])]
                assert len(pushurl_config_calls) == 3

                # First call should be without --add
                assert "--add" not in pushurl_config_calls[0][0][0]
                assert "git@github.com:test/repo.git" in pushurl_config_calls[0][0][0]

                # Second and third calls should have --add
                assert "--add" in pushurl_config_calls[1][0][0]
                assert "git@gitlab.com:test/repo.git" in pushurl_config_calls[1][0][0]

                assert "--add" in pushurl_config_calls[2][0][0]
                assert "git@bitbucket.org:test/repo.git" in pushurl_config_calls[2][0][0]
