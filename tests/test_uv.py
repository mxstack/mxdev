from mxdev.config import Configuration
from mxdev.state import State
from mxdev.uv import _constraints_to_uv
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


def test_update_pyproject_writes_version_overrides(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    mx_ini = """
[settings]
version-overrides =
    baz.baaz==1.9.32
    somepackage==3.0.0

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

    hook.write(state)

    doc = tomlkit.parse((tmp_path / "pyproject.toml").read_text())
    overrides = doc["tool"]["uv"]["override-dependencies"]
    assert list(overrides) == ["baz.baaz==1.9.32", "somepackage==3.0.0"]


def test_update_pyproject_replaces_existing_version_overrides(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    mx_ini = """
[settings]
version-overrides =
    newpkg==2.0.0
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
override-dependencies = ["stalepkg==0.1.0"]
"""
    (tmp_path / "pyproject.toml").write_text(initial_toml.strip())

    hook.write(state)

    doc = tomlkit.parse((tmp_path / "pyproject.toml").read_text())
    overrides = doc["tool"]["uv"]["override-dependencies"]
    assert list(overrides) == ["newpkg==2.0.0"]


def test_update_pyproject_no_overrides_no_packages_skips(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    (tmp_path / "mx.ini").write_text("[settings]")
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
    assert "override-dependencies" not in doc["tool"]["uv"]
    assert "sources" not in doc["tool"]["uv"]


def test_update_pyproject_overrides_only_no_packages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()

    mx_ini = """
[settings]
version-overrides =
    onlyoverride==1.0.0
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
    assert list(doc["tool"]["uv"]["override-dependencies"]) == ["onlyoverride==1.0.0"]
    assert "sources" not in doc["tool"]["uv"]


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


def test_constraints_to_uv_filters_and_preserves_order():
    constraints = [
        "#" * 79 + "\n",
        "# begin constraints from: https://example.com/a.txt\n",
        "\n",
        "Zope==6.0\n",
        "# AccessControl==7.3 -> mxdev disabled (source)\n",
        'backports.tarfile==1.2.0 ; python_version < "3.12"\n',
        "--hash=sha256:deadbeef\n",
        "# end constraints from: https://example.com/a.txt\n",
        "#" * 79 + "\n",
    ]
    result = _constraints_to_uv(constraints)
    assert result == [
        ("comment", "begin constraints from: https://example.com/a.txt"),
        ("entry", "Zope==6.0"),
        ("comment", "AccessControl==7.3 -> mxdev disabled (source)"),
        ("entry", 'backports.tarfile==1.2.0 ; python_version < "3.12"'),
        ("comment", "end constraints from: https://example.com/a.txt"),
    ]


def test_constraints_to_uv_empty_input():
    assert _constraints_to_uv([]) == []
    assert _constraints_to_uv(["\n", "#" * 79 + "\n", "   \n"]) == []


def test_writes_constraint_dependencies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()
    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)
    state.constraints = [
        "# begin constraints from: https://example.com/a.txt\n",
        "Zope==6.0\n",
        "# AccessControl==7.3 -> mxdev disabled (source)\n",
        "# end constraints from: https://example.com/a.txt\n",
    ]

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\ndependencies = []\n\n[tool.uv]\nmanaged = true\n'
    )

    hook.write(state)

    content = (tmp_path / "pyproject.toml").read_text()
    assert "# managed by mxdev - do not edit" in content
    assert "# begin constraints from: https://example.com/a.txt" in content
    assert "# AccessControl==7.3 -> mxdev disabled (source)" in content
    doc = tomlkit.parse(content)
    assert list(doc["tool"]["uv"]["constraint-dependencies"]) == ["Zope==6.0"]


def test_opt_out_disables_constraint_dependencies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()
    (tmp_path / "mx.ini").write_text("[settings]\nuv-constraint-dependencies = false\n")
    config = Configuration("mx.ini")
    state = State(config)
    state.constraints = ["Zope==6.0\n"]

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\ndependencies = []\n\n[tool.uv]\nmanaged = true\n'
    )

    hook.write(state)

    doc = tomlkit.parse((tmp_path / "pyproject.toml").read_text())
    assert "constraint-dependencies" not in doc["tool"]["uv"]


def test_replaces_existing_constraint_dependencies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()
    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)
    state.constraints = ["Zope==6.0\n"]

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\ndependencies = []\n\n'
        "[tool.uv]\nmanaged = true\n"
        'constraint-dependencies = [\n    "OldPin==0.0.1",\n]\n'
    )

    hook.write(state)

    content = (tmp_path / "pyproject.toml").read_text()
    assert "OldPin" not in content
    doc = tomlkit.parse(content)
    assert list(doc["tool"]["uv"]["constraint-dependencies"]) == ["Zope==6.0"]


def test_constraint_dependencies_idempotency(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()
    (tmp_path / "mx.ini").write_text("[settings]")
    config = Configuration("mx.ini")
    state = State(config)
    state.constraints = [
        "# begin constraints from: https://example.com/a.txt\n",
        "Zope==6.0\n",
        "AccessControl==7.3\n",
        "# end constraints from: https://example.com/a.txt\n",
    ]

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\ndependencies = []\n\n[tool.uv]\nmanaged = true\n'
    )

    hook.write(state)
    first = (tmp_path / "pyproject.toml").read_text()
    hook.write(state)
    second = (tmp_path / "pyproject.toml").read_text()
    assert first == second


def test_empty_constraints_removes_stale_managed_array(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hook = UvPyprojectUpdater()
    # A package ensures _update_pyproject does not early-return.
    mx_ini = "[settings]\n[pkg1]\nurl = https://example.com/pkg1.git\n" "target = sources\ninstall-mode = editable\n"
    (tmp_path / "mx.ini").write_text(mx_ini)
    config = Configuration("mx.ini")
    state = State(config)
    state.constraints = []  # nothing resolved

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\ndependencies = []\n\n'
        "[tool.uv]\nmanaged = true\n"
        'constraint-dependencies = [\n    "StalePin==9.9.9",\n]\n'
    )

    hook.write(state)

    doc = tomlkit.parse((tmp_path / "pyproject.toml").read_text())
    assert "constraint-dependencies" not in doc["tool"]["uv"]


def test_end_to_end_constraint_chain(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # constraints chain: requirements.txt -> -c constraints.txt
    (tmp_path / "constraints.txt").write_text("Zope==6.0\nAccessControl==7.3\n")
    (tmp_path / "requirements.txt").write_text("-c constraints.txt\n")

    mx_ini = "[settings]\nrequirements-in = requirements.txt\n" "version-overrides =\n    AccessControl==7.4\n"
    (tmp_path / "mx.ini").write_text(mx_ini)

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\ndependencies = []\n\n[tool.uv]\nmanaged = true\n'
    )

    from mxdev.processing import read

    config = Configuration("mx.ini")
    state = State(config)
    read(state)  # populates state.constraints from the chain

    hook = UvPyprojectUpdater()
    hook.write(state)

    content = (tmp_path / "pyproject.toml").read_text()
    assert "# begin constraints from: constraints.txt" in content
    doc = tomlkit.parse(content)
    cdeps = list(doc["tool"]["uv"]["constraint-dependencies"])
    # Zope is constrained; AccessControl is overridden -> commented out by read(),
    # so it must NOT appear as an active constraint entry.
    assert "Zope==6.0" in cdeps
    assert "AccessControl==7.3" not in cdeps
    # The override itself is carried by override-dependencies.
    assert list(doc["tool"]["uv"]["override-dependencies"]) == ["AccessControl==7.4"]


def _write_mx_ini_packages(tmp_path, *names):
    lines = ["[settings]"]
    for name in names:
        lines.append(f"[{name}]")
        lines.append(f"url = https://example.com/{name}.git")
        lines.append("target = sources")
        lines.append("install-mode = editable")
    (tmp_path / "mx.ini").write_text("\n".join(lines) + "\n")


def _run_hook(tmp_path):
    config = Configuration("mx.ini")
    state = State(config)
    UvPyprojectUpdater().write(state)
    return tomlkit.parse((tmp_path / "pyproject.toml").read_text())


def test_drops_source_when_package_removed_from_mx_ini(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "backend"\ndependencies = []\n\n[tool.uv]\nmanaged = true\n'
    )

    # Phase 1: two packages -> both written to [tool.uv.sources]
    _write_mx_ini_packages(tmp_path, "addon-a", "addon-b")
    doc = _run_hook(tmp_path)
    assert "addon-a" in doc["tool"]["uv"]["sources"]
    assert "addon-b" in doc["tool"]["uv"]["sources"]

    # Phase 2: addon-b removed from mx.ini -> must be removed from pyproject.toml
    _write_mx_ini_packages(tmp_path, "addon-a")
    doc = _run_hook(tmp_path)
    assert "addon-a" in doc["tool"]["uv"]["sources"]
    assert "addon-b" not in doc["tool"]["uv"]["sources"]


def test_preserves_foreign_sources_when_reconciling(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # A hand-written, non-mxdev source must never be touched.
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "backend"\ndependencies = []\n\n'
        "[tool.uv]\nmanaged = true\n\n"
        "[tool.uv.sources]\n"
        'my-fork = { git = "https://github.com/me/my-fork.git", branch = "main" }\n'
    )

    _write_mx_ini_packages(tmp_path, "addon-a")
    doc = _run_hook(tmp_path)
    assert "addon-a" in doc["tool"]["uv"]["sources"]
    assert "my-fork" in doc["tool"]["uv"]["sources"]

    # Drop addon-a: it goes away, the foreign source stays.
    (tmp_path / "mx.ini").write_text("[settings]\n")
    doc = _run_hook(tmp_path)
    assert "addon-a" not in doc["tool"]["uv"]["sources"]
    assert "my-fork" in doc["tool"]["uv"]["sources"]


def test_skip_install_mode_removes_existing_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "backend"\ndependencies = []\n\n[tool.uv]\nmanaged = true\n'
    )

    _write_mx_ini_packages(tmp_path, "addon-a")
    doc = _run_hook(tmp_path)
    assert "addon-a" in doc["tool"]["uv"]["sources"]

    # Switch addon-a to skip -> its source must be removed.
    (tmp_path / "mx.ini").write_text(
        "[settings]\n[addon-a]\nurl = https://example.com/addon-a.git\n" "target = sources\ninstall-mode = skip\n"
    )
    doc = _run_hook(tmp_path)
    assert "addon-a" not in doc["tool"]["uv"].get("sources", {})


def test_source_reconcile_idempotency(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "backend"\ndependencies = []\n\n[tool.uv]\nmanaged = true\n'
    )
    _write_mx_ini_packages(tmp_path, "addon-a", "addon-b")

    UvPyprojectUpdater().write(State(Configuration("mx.ini")))
    first = (tmp_path / "pyproject.toml").read_text()
    UvPyprojectUpdater().write(State(Configuration("mx.ini")))
    second = (tmp_path / "pyproject.toml").read_text()
    assert first == second
