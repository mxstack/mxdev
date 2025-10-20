import pathlib
import pytest
from unittest.mock import patch, MagicMock
import logging


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


def test_main_loglevel_default(tmp_path):
    """Test main function sets default log level."""
    from mxdev.main import main

    # Create a minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in =
""")

    with patch('sys.argv', ['mxdev', '-c', str(config_file)]):
        with patch('mxdev.main.setup_logger') as mock_setup:
            with patch('mxdev.main.load_hooks', return_value=[]):
                with patch('mxdev.main.read'):
                    with patch('mxdev.main.fetch'):
                        with patch('mxdev.main.write'):
                            with patch('mxdev.main.write_hooks'):
                                main()
                                mock_setup.assert_called_once_with(logging.INFO)


def test_main_loglevel_verbose(tmp_path):
    """Test main function with verbose flag."""
    from mxdev.main import main

    # Create a minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in =
""")

    with patch('sys.argv', ['mxdev', '-c', str(config_file), '--verbose']):
        with patch('mxdev.main.setup_logger') as mock_setup:
            with patch('mxdev.main.load_hooks', return_value=[]):
                with patch('mxdev.main.read'):
                    with patch('mxdev.main.fetch'):
                        with patch('mxdev.main.write'):
                            with patch('mxdev.main.write_hooks'):
                                main()
                                mock_setup.assert_called_once_with(logging.INFO)


def test_main_loglevel_silent(tmp_path):
    """Test main function with silent flag."""
    from mxdev.main import main

    # Create a minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in =
""")

    with patch('sys.argv', ['mxdev', '-c', str(config_file), '--silent']):
        with patch('mxdev.main.setup_logger') as mock_setup:
            with patch('mxdev.main.load_hooks', return_value=[]):
                with patch('mxdev.main.read'):
                    with patch('mxdev.main.fetch'):
                        with patch('mxdev.main.write'):
                            with patch('mxdev.main.write_hooks'):
                                main()
                                mock_setup.assert_called_once_with(logging.WARNING)


def test_main_offline_override(tmp_path):
    """Test main function applies offline override."""
    from mxdev.main import main

    # Create a minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in =
""")

    with patch('sys.argv', ['mxdev', '-c', str(config_file), '--offline']):
        with patch('mxdev.main.setup_logger'):
            with patch('mxdev.main.load_hooks', return_value=[]):
                with patch('mxdev.main.Configuration') as mock_config_class:
                    mock_config = MagicMock()
                    mock_config.out_requirements = "requirements-mxdev.txt"
                    mock_config_class.return_value = mock_config

                    with patch('mxdev.main.read'):
                        with patch('mxdev.main.fetch'):
                            with patch('mxdev.main.write'):
                                with patch('mxdev.main.write_hooks'):
                                    main()

                                    # Check that Configuration was called with offline=True
                                    call_kwargs = mock_config_class.call_args[1]
                                    assert call_kwargs['override_args']['offline'] is True


def test_main_threads_override(tmp_path):
    """Test main function applies threads override."""
    from mxdev.main import main

    # Create a minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in =
""")

    with patch('sys.argv', ['mxdev', '-c', str(config_file), '--threads', '16']):
        with patch('mxdev.main.setup_logger'):
            with patch('mxdev.main.load_hooks', return_value=[]):
                with patch('mxdev.main.Configuration') as mock_config_class:
                    mock_config = MagicMock()
                    mock_config.out_requirements = "requirements-mxdev.txt"
                    mock_config_class.return_value = mock_config

                    with patch('mxdev.main.read'):
                        with patch('mxdev.main.fetch'):
                            with patch('mxdev.main.write'):
                                with patch('mxdev.main.write_hooks'):
                                    main()

                                    # Check that Configuration was called with threads=16
                                    call_kwargs = mock_config_class.call_args[1]
                                    assert call_kwargs['override_args']['threads'] == 16


def test_main_no_fetch(tmp_path):
    """Test main function with --no-fetch skips fetch."""
    from mxdev.main import main

    # Create a minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in =
""")

    with patch('sys.argv', ['mxdev', '-c', str(config_file), '--no-fetch']):
        with patch('mxdev.main.setup_logger'):
            with patch('mxdev.main.load_hooks', return_value=[]):
                with patch('mxdev.main.read'):
                    with patch('mxdev.main.fetch') as mock_fetch:
                        with patch('mxdev.main.write'):
                            with patch('mxdev.main.write_hooks'):
                                with patch('mxdev.main.read_hooks'):
                                    main()
                                    # fetch should not be called
                                    mock_fetch.assert_not_called()


def test_main_fetch_only(tmp_path):
    """Test main function with --fetch-only skips write."""
    from mxdev.main import main

    # Create a minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in =
""")

    with patch('sys.argv', ['mxdev', '-c', str(config_file), '--fetch-only']):
        with patch('mxdev.main.setup_logger'):
            with patch('mxdev.main.load_hooks', return_value=[]):
                with patch('mxdev.main.read'):
                    with patch('mxdev.main.fetch'):
                        with patch('mxdev.main.write') as mock_write:
                            with patch('mxdev.main.write_hooks') as mock_write_hooks:
                                with patch('mxdev.main.read_hooks') as mock_read_hooks:
                                    main()
                                    # write and write_hooks should not be called
                                    mock_write.assert_not_called()
                                    mock_write_hooks.assert_not_called()
                                    # read_hooks should not be called with fetch-only
                                    mock_read_hooks.assert_not_called()


def test_main_calls_hooks(tmp_path):
    """Test main function calls hooks correctly."""
    from mxdev.main import main

    # Create a minimal config
    config_file = tmp_path / "mx.ini"
    config_file.write_text("""[settings]
requirements-in =
""")

    mock_hook = MagicMock()

    with patch('sys.argv', ['mxdev', '-c', str(config_file)]):
        with patch('mxdev.main.setup_logger'):
            with patch('mxdev.main.load_hooks', return_value=[mock_hook]):
                with patch('mxdev.main.read'):
                    with patch('mxdev.main.fetch'):
                        with patch('mxdev.main.write'):
                            with patch('mxdev.main.write_hooks') as mock_write_hooks:
                                with patch('mxdev.main.read_hooks') as mock_read_hooks:
                                    main()
                                    # Hooks should be called with state and hooks list
                                    assert mock_read_hooks.called
                                    assert mock_write_hooks.called
