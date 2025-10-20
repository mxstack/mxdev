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
