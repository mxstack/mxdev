import os
from unittest.mock import patch
from mxdev.main import main
import pytest

def test_discovery_mx_ini_exists(tmp_path, monkeypatch):
    """If mx.ini exists, it should be preferred over pyproject.toml."""
    mxini = tmp_path / "mx.ini"
    mxini.write_text("[settings]\nrequirements-in = mx-reqs.txt", encoding="utf-8")
    
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.mxdev.settings]\nrequirements-in = toml-reqs.txt", encoding="utf-8")
    
    monkeypatch.chdir(tmp_path)
    
    import sys
    main_module = sys.modules["mxdev.main"]
    
    with (
        patch("sys.argv", ["mxdev"]),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "Configuration") as mock_config,
        patch.object(main_module, "read"),
        patch.object(main_module, "write"),
        patch.object(main_module, "setup_logger"),
    ):
        main()
        # Should pick mx.ini
        mock_config.assert_called_once()
        assert mock_config.call_args[1]["mxini"] == "mx.ini"

def test_discovery_pyproject_fallback(tmp_path, monkeypatch):
    """If mx.ini is missing, it should fallback to pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.mxdev.settings]\nrequirements-in = toml-reqs.txt", encoding="utf-8")
    
    monkeypatch.chdir(tmp_path)
    
    import sys
    main_module = sys.modules["mxdev.main"]
    
    with (
        patch("sys.argv", ["mxdev"]),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "Configuration") as mock_config,
        patch.object(main_module, "read"),
        patch.object(main_module, "write"),
        patch.object(main_module, "setup_logger"),
    ):
        main()
        # Should pick pyproject.toml
        mock_config.assert_called_once()
        assert mock_config.call_args[1]["mxini"] == "pyproject.toml"

def test_discovery_explicit_flag(tmp_path, monkeypatch):
    """Explicit flag should override discovery."""
    mxini = tmp_path / "mx.ini"
    mxini.write_text("[settings]", encoding="utf-8")
    
    custom = tmp_path / "custom.toml"
    custom.write_text("[tool.mxdev.settings]", encoding="utf-8")
    
    monkeypatch.chdir(tmp_path)
    
    import sys
    main_module = sys.modules["mxdev.main"]
    
    with (
        patch("sys.argv", ["mxdev", "-c", "custom.toml"]),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "Configuration") as mock_config,
        patch.object(main_module, "read"),
        patch.object(main_module, "write"),
        patch.object(main_module, "setup_logger"),
    ):
        main()
        # Should pick custom.toml
        mock_config.assert_called_once()
        assert mock_config.call_args[1]["mxini"] == "custom.toml"

def test_discovery_no_config(tmp_path, monkeypatch):
    """If no config found, fallback to mx.ini default (to trigger existing error behavior)."""
    monkeypatch.chdir(tmp_path)
    
    import sys
    main_module = sys.modules["mxdev.main"]
    
    with (
        patch("sys.argv", ["mxdev"]),
        patch.object(main_module, "load_hooks", return_value=[]),
        patch.object(main_module, "Configuration") as mock_config,
        patch.object(main_module, "read"),
        patch.object(main_module, "write"),
        patch.object(main_module, "setup_logger"),
    ):
        main()
        mock_config.assert_called_once()
        assert mock_config.call_args[1]["mxini"] == "mx.ini"
