import pytest


def test_filesystem_error_exists():
    """Test FilesystemError exception class exists."""
    from mxdev.vcs.common import WCError
    from mxdev.vcs.filesystem import FilesystemError

    # Should be a subclass of WCError
    assert issubclass(FilesystemError, WCError)


def test_filesystem_working_copy_class_exists():
    """Test FilesystemWorkingCopy class exists."""
    from mxdev.vcs.common import BaseWorkingCopy
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    # Should be a subclass of BaseWorkingCopy
    assert issubclass(FilesystemWorkingCopy, BaseWorkingCopy)


def test_checkout_path_exists_and_matches(tmp_path):
    """Test checkout when path exists and matches."""
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    # Create a directory that matches
    test_dir = tmp_path / "my-package"
    test_dir.mkdir()

    source = {
        "name": "my-package",
        "path": str(test_dir),
        "url": "my-package",
    }

    wc = FilesystemWorkingCopy(source)
    result = wc.checkout()

    # Should return empty string
    assert result == ""


def test_checkout_path_exists_but_doesnt_match(tmp_path):
    """Test checkout when path exists but doesn't match expected name."""
    from mxdev.vcs.filesystem import FilesystemError
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    # Create a directory with different name than expected
    test_dir = tmp_path / "actual-name"
    test_dir.mkdir()

    source = {
        "name": "my-package",
        "path": str(test_dir),
        "url": "expected-name",  # Different from actual directory name
    }

    wc = FilesystemWorkingCopy(source)

    with pytest.raises(FilesystemError, match="Directory name for existing package .* differs"):
        wc.checkout()


def test_checkout_path_doesnt_exist(tmp_path):
    """Test checkout when path doesn't exist."""
    from mxdev.vcs.filesystem import FilesystemError
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    # Don't create the directory
    test_dir = tmp_path / "nonexistent"

    source = {
        "name": "my-package",
        "path": str(test_dir),
        "url": "my-package",
    }

    wc = FilesystemWorkingCopy(source)

    with pytest.raises(FilesystemError, match="Directory .* for package .* doesn't exist"):
        wc.checkout()


def test_matches_returns_true(tmp_path):
    """Test matches() returns True when path basename matches URL."""
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    test_dir = tmp_path / "my-package"
    test_dir.mkdir()

    source = {
        "name": "my-package",
        "path": str(test_dir),
        "url": "my-package",
    }

    wc = FilesystemWorkingCopy(source)
    assert wc.matches() is True


def test_matches_returns_false(tmp_path):
    """Test matches() returns False when path basename doesn't match URL."""
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    test_dir = tmp_path / "actual-dir"
    test_dir.mkdir()

    source = {
        "name": "my-package",
        "path": str(test_dir),
        "url": "expected-dir",
    }

    wc = FilesystemWorkingCopy(source)
    assert wc.matches() is False


def test_status_verbose():
    """Test status() with verbose=True."""
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    source = {
        "name": "my-package",
        "path": "/some/path",
        "url": "my-package",
    }

    wc = FilesystemWorkingCopy(source)
    status, msg = wc.status(verbose=True)

    assert status == "clean"
    assert msg == ""


def test_status_not_verbose():
    """Test status() with verbose=False (default)."""
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    source = {
        "name": "my-package",
        "path": "/some/path",
        "url": "my-package",
    }

    wc = FilesystemWorkingCopy(source)
    result = wc.status(verbose=False)

    assert result == "clean"


def test_status_default():
    """Test status() without verbose parameter (defaults to False)."""
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    source = {
        "name": "my-package",
        "path": "/some/path",
        "url": "my-package",
    }

    wc = FilesystemWorkingCopy(source)
    result = wc.status()

    assert result == "clean"


def test_update_when_matches(tmp_path):
    """Test update() when path matches."""
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    test_dir = tmp_path / "my-package"
    test_dir.mkdir()

    source = {
        "name": "my-package",
        "path": str(test_dir),
        "url": "my-package",
    }

    wc = FilesystemWorkingCopy(source)
    result = wc.update()

    assert result == ""


def test_update_when_doesnt_match(tmp_path):
    """Test update() when path doesn't match raises error."""
    from mxdev.vcs.filesystem import FilesystemError
    from mxdev.vcs.filesystem import FilesystemWorkingCopy

    test_dir = tmp_path / "actual-name"
    test_dir.mkdir()

    source = {
        "name": "my-package",
        "path": str(test_dir),
        "url": "expected-name",
    }

    wc = FilesystemWorkingCopy(source)

    with pytest.raises(FilesystemError, match="Directory name for existing package .* differs"):
        wc.update()


def test_logger_exists():
    """Test that logger is imported from common."""
    from mxdev.vcs.common import logger as common_logger
    from mxdev.vcs.filesystem import logger

    # Should be the same logger instance
    assert logger is common_logger
