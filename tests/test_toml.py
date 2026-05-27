import pytest
from mxdev.config import read_toml, Configuration
from pathlib import Path
import os

def test_read_toml_basic(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[tool.mxdev.settings]
threads = 10
requirements-in = "reqs.txt"

[tool.mxdev.packages.pkg1]
url = "https://example.com/pkg1.git"
branch = "dev"

[tool.mxdev.hooks.myhook]
enabled = "true"
""", encoding="utf-8")
    
    wrapper = read_toml(pyproject)
    assert wrapper["settings"]["threads"] == "10"
    assert wrapper["pkg1"]["url"] == "https://example.com/pkg1.git"
    assert wrapper["pkg1"]["branch"] == "dev"
    assert wrapper["myhook"]["enabled"] == "true"
    assert "pkg1" in wrapper.sections()
    assert "myhook" in wrapper.sections()

def test_read_toml_no_section(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.other]\nkey = 'val'", encoding="utf-8")
    
    wrapper = read_toml(pyproject)
    assert dict(wrapper["settings"].items()) == {}
    assert wrapper.sections() == []

def test_configuration_toml(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[tool.mxdev.settings]
requirements-in = "requirements-in.txt"

[tool.mxdev.packages.pkg1]
url = "https://example.com/pkg1.git"
""", encoding="utf-8")
    
    # We need to be in the directory or provide absolute path
    config = Configuration(str(pyproject))
    assert config.infile == "requirements-in.txt"
    assert "pkg1" in config.packages
    assert config.packages["pkg1"]["url"] == "https://example.com/pkg1.git"

def test_read_toml_types_to_strings(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[tool.mxdev.settings]
threads = 10
offline = true

[tool.mxdev.packages.pkg1]
url = "https://example.com/pkg1.git"
use = false
""", encoding="utf-8")
    
    wrapper = read_toml(pyproject)
    assert wrapper["settings"]["threads"] == "10"
    assert wrapper["settings"]["offline"] == "True"  # TOML bool becomes Python bool then str()
    assert wrapper["pkg1"]["use"] == "False"

def test_read_toml_no_parser(monkeypatch):
    import sys
    # Mock both tomllib and tomli being missing
    with patch.dict(sys.modules, {'tomllib': None, 'tomli': None}):
        # We need to reload mxdev.config to apply the mock if it was already imported
        # but read_toml imports them inside the function, so it should work.
        with pytest.raises(ImportError) as excinfo:
            read_toml("any.toml")
        assert "pip install mxdev[toml]" in str(excinfo.value)

from unittest.mock import patch
