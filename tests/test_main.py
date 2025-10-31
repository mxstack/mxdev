from unittest.mock import MagicMock
from unittest.mock import patch


def test_parser_defaults():
    """Test argument parser with default values."""
    from mxdev.main import parser

    args = parser.parse_args([])
    assert args.configuration == "mx.ini"
    assert args.no_fetch is False
    assert args.fetch_only is False
    assert args.offline is False
    assert args.threads is None
    assert args.silent is False
    assert args.verbose is False


def test_parser_configuration():
    """Test argument parser with configuration file."""
    from mxdev.main import parser

    args = parser.parse_args(["-c", "custom.ini"])
    assert args.configuration == "custom.ini"

    args = parser.parse_args(["--configuration", "another.ini"])
    assert args.configuration == "another.ini"


def test_parser_no_fetch():
    """Test argument parser with --no-fetch flag."""
    from mxdev.main import parser

    args = parser.parse_args(["--no-fetch"])
    assert args.no_fetch is True

    args = parser.parse_args(["-n"])
    assert args.no_fetch is True


def test_parser_fetch_only():
    """Test argument parser with --fetch-only flag."""
    from mxdev.main import parser

    args = parser.parse_args(["--fetch-only"])
    assert args.fetch_only is True

    args = parser.parse_args(["-f"])
    assert args.fetch_only is True


def test_parser_offline():
    """Test argument parser with --offline flag."""
    from mxdev.main import parser

    args = parser.parse_args(["--offline"])
    assert args.offline is True

    args = parser.parse_args(["-o"])
    assert args.offline is True


def test_parser_threads():
    """Test argument parser with --threads flag."""
    from mxdev.main import parser

    args = parser.parse_args(["--threads", "8"])
    assert args.threads == 8

    args = parser.parse_args(["-t", "16"])
    assert args.threads == 16


def test_parser_silent():
    """Test argument parser with --silent flag."""
    from mxdev.main import parser

    args = parser.parse_args(["--silent"])
    assert args.silent is True

    args = parser.parse_args(["-s"])
    assert args.silent is True


def test_parser_verbose():
    """Test argument parser with --verbose flag."""
    from mxdev.main import parser

    args = parser.parse_args(["--verbose"])
    assert args.verbose is True

    args = parser.parse_args(["-v"])
    assert args.verbose is True


def test_parser_version(capsys):
    """Test --version prints version and exits."""
    from mxdev.main import __version__
    from mxdev.main import parser

    import pytest

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])

    # Verify clean exit
    assert exc_info.value.code == 0

    # Verify output contains version string
    captured = capsys.readouterr()
    assert __version__ in captured.out
    assert "." in captured.out  # Version has dots (X.Y.Z)


def test_version_format():
    """Test version format is valid."""
    from mxdev.main import __version__

    # Version should not be the fallback
    assert __version__ != "unknown (not installed)"

    # Version should contain dots (semantic versioning)
    assert "." in __version__

    # Version should be a string
    assert isinstance(__version__, str)


def test_supports_unicode_with_utf8():
    """Test supports_unicode returns True for UTF-8 encoding."""
    from mxdev.main import supports_unicode

    # Mock stdout with UTF-8 encoding
    mock_stdout = MagicMock()
    mock_stdout.encoding = "utf-8"

    with patch("sys.stdout", mock_stdout):
        assert supports_unicode() is True


def test_supports_unicode_with_cp1252():
    """Test supports_unicode returns False for cp1252 encoding."""
    from mxdev.main import supports_unicode

    # Mock stdout with cp1252 encoding
    mock_stdout = MagicMock()
    mock_stdout.encoding = "cp1252"

    with patch("sys.stdout", mock_stdout):
        assert supports_unicode() is False


def test_supports_unicode_with_no_encoding():
    """Test supports_unicode returns False when encoding is None."""
    from mxdev.main import supports_unicode

    # Mock stdout with no encoding
    mock_stdout = MagicMock()
    mock_stdout.encoding = None

    with patch("sys.stdout", mock_stdout):
        assert supports_unicode() is False


def test_supports_unicode_with_ascii():
    """Test supports_unicode returns False for ASCII encoding."""
    from mxdev.main import supports_unicode

    # Mock stdout with ASCII encoding
    mock_stdout = MagicMock()
    mock_stdout.encoding = "ascii"

    with patch("sys.stdout", mock_stdout):
        assert supports_unicode() is False


def test_supports_unicode_with_latin1():
    """Test supports_unicode returns False for latin-1 encoding."""
    from mxdev.main import supports_unicode

    # Mock stdout with latin-1 encoding
    mock_stdout = MagicMock()
    mock_stdout.encoding = "latin-1"

    with patch("sys.stdout", mock_stdout):
        assert supports_unicode() is False


def test_main_default_behavior(tmp_path, monkeypatch):
    """Test main() function with default arguments."""
    import logging

    # Create a minimal mx.ini file
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
constraints-out = constraints-out.txt
"""
    )

    # Create empty requirements file
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("")

    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Mock command line arguments
    test_args = ["-c", str(config_file)]

    import sys

    main_module = sys.modules["mxdev.main"]

    with (
        patch("sys.argv", ["mxdev"] + test_args),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "read") as mock_read,
        patch.object(main_module, "read_hooks") as mock_read_hooks,
        patch.object(main_module, "fetch") as mock_fetch,
        patch.object(main_module, "write") as mock_write,
        patch.object(main_module, "write_hooks") as mock_write_hooks,
        patch.object(main_module, "setup_logger") as mock_setup_logger,
    ):
        main_module.main()

        # Verify logger was set up with INFO level (default)
        mock_setup_logger.assert_called_once_with(logging.INFO)

        # Verify all processing functions were called
        assert mock_read.called
        assert mock_read_hooks.called
        assert mock_fetch.called
        assert mock_write.called
        assert mock_write_hooks.called


def test_main_verbose_flag(tmp_path, monkeypatch):
    """Test main() with --verbose flag sets INFO log level."""
    import logging

    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
"""
    )
    (tmp_path / "requirements.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    test_args = ["-c", str(config_file), "--verbose"]

    import sys

    main_module = sys.modules["mxdev.main"]

    with (
        patch("sys.argv", ["mxdev"] + test_args),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "read"),
        patch.object(main_module, "read_hooks"),
        patch.object(main_module, "fetch"),
        patch.object(main_module, "write"),
        patch.object(main_module, "write_hooks"),
        patch.object(main_module, "setup_logger") as mock_setup_logger,
    ):
        main_module.main()

        # Verify logger was set up with INFO level when verbose flag is used
        mock_setup_logger.assert_called_once_with(logging.INFO)


def test_main_silent_flag(tmp_path, monkeypatch):
    """Test main() with --silent flag sets WARNING log level."""
    import logging

    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
"""
    )
    (tmp_path / "requirements.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    test_args = ["-c", str(config_file), "--silent"]

    import sys

    main_module = sys.modules["mxdev.main"]

    with (
        patch("sys.argv", ["mxdev"] + test_args),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "read"),
        patch.object(main_module, "read_hooks"),
        patch.object(main_module, "fetch"),
        patch.object(main_module, "write"),
        patch.object(main_module, "write_hooks"),
        patch.object(main_module, "setup_logger") as mock_setup_logger,
    ):
        main_module.main()

        # Verify logger was set up with WARNING level when silent flag is used
        mock_setup_logger.assert_called_once_with(logging.WARNING)


def test_main_offline_flag(tmp_path, monkeypatch):
    """Test main() with --offline flag skips fetch."""

    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
"""
    )
    (tmp_path / "requirements.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    test_args = ["-c", str(config_file), "--offline"]

    import sys

    main_module = sys.modules["mxdev.main"]

    with (
        patch("sys.argv", ["mxdev"] + test_args),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "read"),
        patch.object(main_module, "read_hooks"),
        patch.object(main_module, "fetch") as mock_fetch,
        patch.object(main_module, "write"),
        patch.object(main_module, "write_hooks"),
        patch.object(main_module, "setup_logger"),
    ):
        main_module.main()

        # Verify fetch was NOT called when offline flag is used
        assert not mock_fetch.called


def test_main_threads_flag(tmp_path, monkeypatch):
    """Test main() with --threads flag passes value to Configuration."""
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
"""
    )
    (tmp_path / "requirements.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    test_args = ["-c", str(config_file), "--threads", "8"]

    import sys

    main_module = sys.modules["mxdev.main"]

    with (
        patch("sys.argv", ["mxdev"] + test_args),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "Configuration") as mock_config,
        patch.object(main_module, "read"),
        patch.object(main_module, "read_hooks"),
        patch.object(main_module, "fetch"),
        patch.object(main_module, "write"),
        patch.object(main_module, "write_hooks"),
        patch.object(main_module, "setup_logger"),
    ):
        main_module.main()

        # Verify Configuration was called with threads override
        mock_config.assert_called_once()
        call_kwargs = mock_config.call_args[1]
        assert "override_args" in call_kwargs
        assert call_kwargs["override_args"]["threads"] == 8


def test_main_no_fetch_flag(tmp_path, monkeypatch):
    """Test main() with --no-fetch flag skips fetch."""
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
"""
    )
    (tmp_path / "requirements.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    test_args = ["-c", str(config_file), "--no-fetch"]

    import sys

    main_module = sys.modules["mxdev.main"]

    with (
        patch("sys.argv", ["mxdev"] + test_args),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "read"),
        patch.object(main_module, "read_hooks"),
        patch.object(main_module, "fetch") as mock_fetch,
        patch.object(main_module, "write"),
        patch.object(main_module, "write_hooks"),
        patch.object(main_module, "setup_logger"),
    ):
        main_module.main()

        # Verify fetch was NOT called when no-fetch flag is used
        assert not mock_fetch.called


def test_main_fetch_only_flag(tmp_path, monkeypatch):
    """Test main() with --fetch-only flag skips write and hooks."""
    config_file = tmp_path / "mx.ini"
    config_file.write_text(
        """[settings]
requirements-in = requirements.txt
requirements-out = requirements-out.txt
"""
    )
    (tmp_path / "requirements.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    test_args = ["-c", str(config_file), "--fetch-only"]

    import sys

    main_module = sys.modules["mxdev.main"]

    with (
        patch("sys.argv", ["mxdev"] + test_args),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "read"),
        patch.object(main_module, "read_hooks") as mock_read_hooks,
        patch.object(main_module, "fetch"),
        patch.object(main_module, "write") as mock_write,
        patch.object(main_module, "write_hooks") as mock_write_hooks,
        patch.object(main_module, "setup_logger"),
    ):
        main_module.main()

        # Verify read_hooks was NOT called
        assert not mock_read_hooks.called
        # Verify write and write_hooks were NOT called
        assert not mock_write.called
        assert not mock_write_hooks.called
