from mxdev.config import Configuration
from mxdev.state import State
from mxdev.uv import UvPyprojectUpdater

import pytest
import sys
import tomlkit


def test_hook_skips_when_pyproject_toml_missing(mocker, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()
    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)
    mock_logger = mocker.patch("mxdev.uv.logger")
    hook.write(state)
    mock_logger.debug.assert_called_with("[%s] pyproject.toml not found, skipping.", "uv")


def test_hook_skips_when_uv_managed_is_false_or_missing(mocker, tmp_path, monkeypatch):
    # Test skipping logic when [tool.uv] is missing or managed != true
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()
    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)

    # Mock pyproject.toml without tool.uv.managed
    doc = tomlkit.document()
    doc.add("project", tomlkit.table())
    (tmp_path / "pyproject.toml").write_text(tomlkit.dumps(doc))

    mock_logger = mocker.patch("mxdev.uv.logger")

    # Store initial content
    initial_content = (tmp_path / "pyproject.toml").read_text()

    hook.write(state)
    mock_logger.debug.assert_called_with(
        "[%s] Project not explicitly managed by uv ([tool.uv] managed=true missing), skipping.",
        "uv",
    )

    # Verify the file was not modified
    assert (tmp_path / "pyproject.toml").read_text() == initial_content


def test_hook_skips_when_uv_managed_is_false(mocker, tmp_path, monkeypatch):
    # Test skipping logic when [tool.uv] managed is explicitly false
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()
    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)

    # Mock pyproject.toml with tool.uv.managed = false
    initial_toml = """
[tool.uv]
managed = false
"""
    (tmp_path / "pyproject.toml").write_text(initial_toml.strip())

    mock_logger = mocker.patch("mxdev.uv.logger")

    # Store initial content
    initial_content = (tmp_path / "pyproject.toml").read_text()

    hook.write(state)
    mock_logger.debug.assert_called_with(
        "[%s] Project not explicitly managed by uv ([tool.uv] managed=true missing), skipping.",
        "uv",
    )

    # Verify the file was not modified
    assert (tmp_path / "pyproject.toml").read_text() == initial_content


def test_hook_executes_when_uv_managed_is_true(mocker, tmp_path, monkeypatch):
    # Test that updates proceed when managed = true is present
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    mx_ini = """
[settings]
[pkg1]
url = https://example.com/pkg1.git
target = sources
install-mode = editable
"""
    (tmp_path / "mx.ini").write_text(mx_ini.strip())
    config = Configuration("mx.ini")
    state = State(config)

    # Mock pyproject.toml with tool.uv.managed = true
    initial_toml = """
[project]
name = "test"
dependencies = []

[tool.uv]
managed = true
"""
    (tmp_path / "pyproject.toml").write_text(initial_toml.strip())

    mock_logger = mocker.patch("mxdev.uv.logger")
    hook.write(state)
    mock_logger.info.assert_any_call("[%s] Updating pyproject.toml...", "uv")
    mock_logger.info.assert_any_call("[%s] Successfully updated pyproject.toml", "uv")

    # Verify the file was actually written correctly
    doc = tomlkit.parse((tmp_path / "pyproject.toml").read_text())
    assert "tool" in doc
    assert "uv" in doc["tool"]
    assert "sources" in doc["tool"]["uv"]
    assert "pkg1" in doc["tool"]["uv"]["sources"]
    assert doc["tool"]["uv"]["sources"]["pkg1"]["path"] == "sources/pkg1"
    assert doc["tool"]["uv"]["sources"]["pkg1"]["editable"] is True


def test_update_pyproject_respects_install_modes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    mx_ini = """
[settings]
[editable-pkg]
url = https://example.com/e.git
target = sources
install-mode = editable

[fixed-pkg]
url = https://example.com/f.git
target = sources
install-mode = fixed

[skip-pkg]
url = https://example.com/s.git
target = sources
install-mode = skip
"""
    (tmp_path / "mx.ini").write_text(mx_ini.strip())
    config = Configuration("mx.ini")
    state = State(config)

    initial_toml = """
[project]
name = "test"
dependencies = []

[tool.uv]
managed = true
"""
    (tmp_path / "pyproject.toml").write_text(initial_toml.strip())

    hook.write(state)

    doc = tomlkit.parse((tmp_path / "pyproject.toml").read_text())
    sources = doc["tool"]["uv"]["sources"]
    assert sources["editable-pkg"]["editable"] is True
    assert sources["fixed-pkg"]["editable"] is False
    assert "skip-pkg" not in sources


def test_update_pyproject_idempotency(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    mx_ini = """
[settings]
[pkg1]
url = https://example.com/pkg1.git
target = sources
install-mode = editable
"""
    (tmp_path / "mx.ini").write_text(mx_ini.strip())
    config = Configuration("mx.ini")
    state = State(config)

    initial_toml = """
[project]
name = "test"
dependencies = []

[tool.uv]
managed = true
"""
    (tmp_path / "pyproject.toml").write_text(initial_toml.strip())

    # Run first time
    hook.write(state)
    content_after_first = (tmp_path / "pyproject.toml").read_text()

    # Run second time
    hook.write(state)
    content_after_second = (tmp_path / "pyproject.toml").read_text()

    assert content_after_first == content_after_second


def test_update_pyproject_with_subdirectory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    mx_ini = """
[settings]
[pkg1]
url = https://example.com/pkg1.git
target = sources
subdirectory = sub/dir
install-mode = editable
"""
    (tmp_path / "mx.ini").write_text(mx_ini.strip())
    config = Configuration("mx.ini")
    state = State(config)

    initial_toml = """
[project]
name = "test"
dependencies = []

[tool.uv]
managed = true
"""
    (tmp_path / "pyproject.toml").write_text(initial_toml.strip())

    hook.write(state)

    doc = tomlkit.parse((tmp_path / "pyproject.toml").read_text())
    assert doc["tool"]["uv"]["sources"]["pkg1"]["path"] == "sources/pkg1/sub/dir"


def test_hook_handles_oserror_on_read(mocker, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)

    # Mock pyproject.toml with tool.uv.managed = true
    initial_toml = """
[project]
name = "test"

[tool.uv]
managed = true
"""
    (tmp_path / "pyproject.toml").write_text(initial_toml.strip())

    mock_logger = mocker.patch("mxdev.uv.logger")
    mocker.patch("pathlib.Path.open", side_effect=OSError("denied"))

    hook.write(state)

    mock_logger.error.assert_called_with("[%s] Failed to read pyproject.toml: %s", "uv", mocker.ANY)


def test_hook_handles_oserror_on_write(mocker, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)

    initial_toml = """
[project]
name = "test"

[tool.uv]
managed = true
"""
    (tmp_path / "pyproject.toml").write_text(initial_toml.strip())

    mock_logger = mocker.patch("mxdev.uv.logger")
    mocker.patch("os.replace", side_effect=OSError("write denied"))

    hook.write(state)

    mock_logger.error.assert_called_with("[%s] Failed to write pyproject.toml: %s", "uv", mocker.ANY)

    # Ensure no .tmp files are left behind
    assert len(list(tmp_path.glob("*.tmp"))) == 0


def test_hook_raises_runtime_error_if_tomlkit_missing(mocker, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)

    (tmp_path / "pyproject.toml").write_text("[tool.uv]\nmanaged = true\n")

    mocker.patch.dict(sys.modules, {"tomlkit": None})
    # Also need to make the import fail
    import builtins

    orig_import = builtins.__import__

    def fake_import(name, *args, **kw):
        if name == "tomlkit":
            raise ImportError("No module named 'tomlkit'")
        return orig_import(name, *args, **kw)

    mocker.patch("builtins.__import__", side_effect=fake_import)

    with pytest.raises(RuntimeError) as excinfo:
        hook.write(state)

    assert "tomlkit is required for the uv hook" in str(excinfo.value)


def test_hook_does_not_require_tomlkit_if_not_uv_managed(mocker, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)

    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

    mocker.patch.dict(sys.modules, {"tomlkit": None})
    import builtins

    orig_import = builtins.__import__

    def fake_import(name, *args, **kw):
        if name == "tomlkit":
            raise ImportError("No module named 'tomlkit'")
        return orig_import(name, *args, **kw)

    mocker.patch("builtins.__import__", side_effect=fake_import)

    # Should not raise any error, even though tomlkit import is mocked to fail
    hook.write(state)
