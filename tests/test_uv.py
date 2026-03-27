from pathlib import Path

import pytest
import tomlkit

from mxdev.state import State
from mxdev.uv import UvPyprojectUpdater


class MockConfig:
    def __init__(self, packages=None, settings=None):
        self.packages = packages or {}
        self.settings = settings or {}


def test_hook_skips_when_pyproject_toml_missing(mocker):
    hook = UvPyprojectUpdater()
    state = State(MockConfig())
    mocker.patch("mxdev.uv.Path.exists", return_value=False)
    mock_logger = mocker.patch("mxdev.uv.logger")
    hook.write(state)
    mock_logger.debug.assert_called_with("[%s] pyproject.toml not found, skipping.", "uv")


def test_hook_skips_when_uv_managed_is_false_or_missing(mocker, tmp_path):
    # Test skipping logic when [tool.uv] is missing or managed != true
    hook = UvPyprojectUpdater()
    state = State(MockConfig())

    # Mock pyproject.toml without tool.uv.managed
    doc = tomlkit.document()
    doc.add("project", tomlkit.table())

    mocker.patch("mxdev.uv.Path.exists", return_value=True)
    mocker.patch("mxdev.uv.Path.open", mocker.mock_open(read_data=tomlkit.dumps(doc)))
    mock_logger = mocker.patch("mxdev.uv.logger")

    hook.write(state)
    mock_logger.debug.assert_called_with(
        "[%s] Project not explicitly managed by uv ([tool.uv] managed=true missing), skipping.", "uv"
    )


def test_hook_executes_when_uv_managed_is_true(mocker, tmp_path):
    # Test that updates proceed when managed = true is present
    hook = UvPyprojectUpdater()

    packages = {"pkg1": {"target": "sources", "install-mode": "editable"}}
    state = State(MockConfig(packages=packages))

    # Mock pyproject.toml with tool.uv.managed = true
    initial_toml = """
[tool.uv]
managed = true
"""
    doc = tomlkit.parse(initial_toml)

    mocker.patch("mxdev.uv.Path.exists", return_value=True)

    # We need a proper mock for pathlib.Path.open that returns our doc and captures the write
    mock_file = mocker.mock_open(read_data=initial_toml)
    mocker.patch("mxdev.uv.Path.open", mock_file)

    mock_logger = mocker.patch("mxdev.uv.logger")

    hook.write(state)
    mock_logger.info.assert_any_call("[%s] Updating pyproject.toml...", "uv")
    mock_logger.info.assert_any_call("[%s] Successfully updated pyproject.toml", "uv")


# Additional test cases to migrate from the old tests
def test_update_pyproject_creates_tool_uv_sources():
    hook = UvPyprojectUpdater()
    doc = tomlkit.document()
    packages = {"pkg1": {"target": "sources", "install-mode": "editable"}}
    state = State(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)

    assert "tool" in doc
    assert "uv" in doc["tool"]
    assert "sources" in doc["tool"]["uv"]
    sources = doc["tool"]["uv"]["sources"]
    assert "pkg1" in sources
    assert sources["pkg1"]["path"] == "sources/pkg1"
    assert sources["pkg1"]["editable"] is True


def test_update_pyproject_respects_install_modes():
    hook = UvPyprojectUpdater()
    doc = tomlkit.document()
    packages = {
        "editable-pkg": {"target": "sources", "install-mode": "editable"},
        "fixed-pkg": {"target": "sources", "install-mode": "fixed"},
        "skip-pkg": {"target": "sources", "install-mode": "skip"},
    }
    state = State(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)
    sources = doc["tool"]["uv"]["sources"]
    assert sources["editable-pkg"]["editable"] is True
    assert sources["fixed-pkg"]["editable"] is False
    assert "skip-pkg" not in sources


def test_update_pyproject_adds_dependencies():
    hook = UvPyprojectUpdater()
    doc = tomlkit.document()
    packages = {"pkg1": {"target": "sources", "install-mode": "editable"}}
    state = State(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)
    deps = doc["project"]["dependencies"]
    assert "pkg1" in deps
