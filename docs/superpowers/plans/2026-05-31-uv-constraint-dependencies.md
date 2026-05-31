# Native uv constraint-dependencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the mxdev uv hook write the fully-resolved constraints (incl. external HTTP/`-c` chains) into `[tool.uv] constraint-dependencies` in `pyproject.toml`, so `uv sync` honors them.

**Architecture:** No new fetch logic. The read phase already resolves the whole `-c`/`-r` chain into `state.constraints` (a list of strings, with provenance comment headers and `# ... -> mxdev disabled` markers). A new pure function `_constraints_to_uv()` turns those lines into an ordered list of `("comment"|"entry", text)` items, preserving source order and comments. `_update_pyproject()` builds a tomlkit multiline array from that (managed marker + comments + entries) and replaces `[tool.uv] constraint-dependencies`. Default-on when `[tool.uv] managed = true`, switchable off via mx.ini `uv-constraint-dependencies = false`.

**Tech Stack:** Python 3.10+, tomlkit (uv extra), `packaging.requirements.Requirement`, pytest.

**Spec:** [docs/superpowers/specs/2026-05-31-uv-constraint-dependencies-design.md](../specs/2026-05-31-uv-constraint-dependencies-design.md). The tomlkit array-comment approach was de-risked via spike (standalone comment lines round-trip byte-identically in tomlkit 0.15.0).

---

## File Structure

- **Modify** `src/mxdev/uv.py`
  - Add module-level pure function `_constraints_to_uv(constraints: list[str]) -> list[tuple[str, str]]`.
  - Add `from mxdev.config import to_bool` import.
  - Extend `UvPyprojectUpdater._update_pyproject()`: read opt-out setting, compute constraint items, adjust the early-return guard, write/replace/remove `[tool.uv] constraint-dependencies`.
- **Modify** `tests/test_uv.py` — add unit tests for `_constraints_to_uv` and integration tests for the hook.
- **Modify** `README.md` — document `constraint-dependencies` + opt-out under the uv section; add attribution in the "Misc" section.
- **Modify** `CHANGES.md` — add entry under the `5.3.3 (unreleased)` section.

---

## Task 1: Pure function `_constraints_to_uv`

**Files:**
- Modify: `src/mxdev/uv.py`
- Test: `tests/test_uv.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/test_uv.py`:

```python
from mxdev.uv import _constraints_to_uv


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_uv.py::test_constraints_to_uv_filters_and_preserves_order tests/test_uv.py::test_constraints_to_uv_empty_input -v`
Expected: FAIL with `ImportError: cannot import name '_constraints_to_uv'`

- [ ] **Step 3: Write minimal implementation**

In `src/mxdev/uv.py`, add this module-level function after the `logger = logging.getLogger("mxdev")` line (around line 15), before the class:

```python
def _constraints_to_uv(constraints: list[str]) -> list[tuple[str, str]]:
    """Turn resolved constraint lines into ordered uv array items.

    Mirrors ``constraints-mxdev.txt`` into TOML-array form: specifier lines
    become ``("entry", specifier)`` and comment lines become
    ``("comment", text)``, preserving source order. Decorative ``####`` rules,
    blank lines, and non-PEP-508 lines (e.g. ``--hash``) are dropped.
    """
    from packaging.requirements import Requirement

    items: list[tuple[str, str]] = []
    for raw in constraints:
        stripped = raw.strip()
        if not stripped:
            continue
        # Decorative full-width rule (line consisting only of '#').
        if set(stripped) == {"#"}:
            continue
        if stripped.startswith("#"):
            items.append(("comment", stripped.lstrip("#").strip()))
            continue
        try:
            Requirement(stripped)
        except Exception:
            logger.debug("[uv] Skipping non-PEP-508 constraint line: %s", stripped)
            continue
        items.append(("entry", stripped))
    return items
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_uv.py::test_constraints_to_uv_filters_and_preserves_order tests/test_uv.py::test_constraints_to_uv_empty_input -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mxdev/uv.py tests/test_uv.py
git commit -m "Add _constraints_to_uv: turn resolved constraints into uv array items"
```

---

## Task 2: Write `constraint-dependencies` in the hook

**Files:**
- Modify: `src/mxdev/uv.py` (top import + `_update_pyproject`)
- Test: `tests/test_uv.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/test_uv.py`:

```python
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
    mx_ini = (
        "[settings]\n[pkg1]\nurl = https://example.com/pkg1.git\n"
        "target = sources\ninstall-mode = editable\n"
    )
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_uv.py -k "constraint_dependencies or opt_out or replaces_existing or stale_managed" -v`
Expected: FAIL — e.g. `test_writes_constraint_dependencies` fails because `constraint-dependencies` is never written (KeyError / assertion on missing key).

- [ ] **Step 3: Add the `to_bool` import**

In `src/mxdev/uv.py`, change the top imports. Current lines 1-3:

```python
from mxdev.hooks import Hook
from mxdev.state import State
from pathlib import Path
```

to:

```python
from mxdev.config import to_bool
from mxdev.hooks import Hook
from mxdev.state import State
from pathlib import Path
```

- [ ] **Step 4: Extend `_update_pyproject`**

Replace the body of `_update_pyproject` (currently `src/mxdev/uv.py:99-156`). The new full method:

```python
    def _update_pyproject(self, doc: "tomlkit.TOMLDocument", state: State) -> None:
        """Modify the pyproject.toml document based on mxdev state."""
        import tomlkit

        packages = state.configuration.packages
        overrides = state.configuration.overrides
        settings = state.configuration.settings

        write_constraints = to_bool(settings.get("uv-constraint-dependencies", "true"))
        constraint_items = _constraints_to_uv(state.constraints) if write_constraints else []

        if not packages and not overrides and not constraint_items:
            # Nothing to add. The only reason to continue is to drop a stale
            # mxdev-managed constraint-dependencies array when the feature is on.
            uv_table = doc.get("tool", {}).get("uv")
            if not write_constraints or uv_table is None or "constraint-dependencies" not in uv_table:
                return

        if "tool" not in doc:
            doc.add("tool", tomlkit.table())
        if "uv" not in doc["tool"]:
            doc["tool"]["uv"] = tomlkit.table()

        # 1. Update [tool.uv.sources]
        if packages:
            if "sources" not in doc["tool"]["uv"]:
                doc["tool"]["uv"]["sources"] = tomlkit.table()

            uv_sources = doc["tool"]["uv"]["sources"]

            for pkg_name, pkg_data in packages.items():
                install_mode = pkg_data.get("install-mode", "editable")

                if install_mode == "skip":
                    continue

                target_dir = Path(pkg_data.get("target", "sources"))
                package_path = target_dir / pkg_name
                subdirectory = pkg_data.get("subdirectory", "")
                if subdirectory:
                    package_path = package_path / subdirectory

                try:
                    if package_path.is_absolute():
                        rel_path = package_path.relative_to(Path.cwd()).as_posix()
                    else:
                        rel_path = package_path.as_posix()
                except ValueError:
                    rel_path = package_path.as_posix()

                source_table = tomlkit.inline_table()
                source_table.append("path", rel_path)

                if install_mode == "editable":
                    source_table.append("editable", True)
                elif install_mode == "fixed":
                    source_table.append("editable", False)

                uv_sources[pkg_name] = source_table

        # 2. Update [tool.uv] override-dependencies from version-overrides
        if overrides:
            override_array = tomlkit.array()
            override_array.extend(overrides.values())
            override_array.multiline(True)
            doc["tool"]["uv"]["override-dependencies"] = override_array

        # 3. Update [tool.uv] constraint-dependencies from resolved constraints
        if write_constraints:
            if constraint_items:
                constraint_array = tomlkit.array()
                constraint_array.multiline(True)
                constraint_array.add_line(comment="managed by mxdev - do not edit")
                for kind, text in constraint_items:
                    if kind == "comment":
                        constraint_array.add_line(comment=text)
                    else:
                        constraint_array.add_line(text)
                doc["tool"]["uv"]["constraint-dependencies"] = constraint_array
            elif "constraint-dependencies" in doc["tool"]["uv"]:
                # Resolved set is empty: drop a stale mxdev-managed array.
                del doc["tool"]["uv"]["constraint-dependencies"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_uv.py -v`
Expected: PASS (all tests, including the pre-existing ones, e.g. `test_update_pyproject_no_overrides_no_packages_skips` still passes because with empty constraints + no uv changes the file is untouched).

- [ ] **Step 6: Commit**

```bash
git add src/mxdev/uv.py tests/test_uv.py
git commit -m "uv hook: write resolved constraints to [tool.uv] constraint-dependencies"
```

---

## Task 3: End-to-end test through `read()` + hook

**Files:**
- Test: `tests/test_uv.py`

- [ ] **Step 1: Write the failing test**

This verifies the real data flow: `read()` resolves a local `-c` chain into `state.constraints`, then the hook writes them. Uses a local file chain (no network) to stay deterministic. Add to the end of `tests/test_uv.py`:

```python
def test_end_to_end_constraint_chain(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # constraints chain: requirements.txt -> -c constraints.txt
    (tmp_path / "constraints.txt").write_text("Zope==6.0\nAccessControl==7.3\n")
    (tmp_path / "requirements.txt").write_text("-c constraints.txt\n")

    mx_ini = (
        "[settings]\nrequirements-in = requirements.txt\n"
        "version-overrides =\n    AccessControl==7.4\n"
    )
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
```

- [ ] **Step 2: Run test to verify it fails (or passes meaningfully)**

Run: `.venv/bin/pytest tests/test_uv.py::test_end_to_end_constraint_chain -v`
Expected: PASS if Tasks 1-2 are implemented correctly. If it FAILS, the most likely cause is the override-disabled line not being filtered — inspect `state.constraints` and confirm the `# ... -> mxdev disabled (override)` line is treated as a comment (Task 1) and that `AccessControl==7.3` is therefore absent from `cdeps`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_uv.py
git commit -m "Add end-to-end test for uv constraint-dependencies from -c chain"
```

---

## Task 4: Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document `constraint-dependencies` under the uv section**

In `README.md`, find this passage (around line 331):

```markdown
This allows you to seamlessly use `uv sync` or `uv run` with the packages mxdev has checked out for you, without needing to use `requirements-mxdev.txt`.
```

Immediately AFTER that line, insert:

````markdown

The fully resolved constraints — including external `-c`/`-r` chains such as Plone
release constraints (`-c https://dist.plone.org/release/6.2.0rc1/constraints.txt`) — are
written to `[tool.uv] constraint-dependencies`. uv itself cannot follow `-c URL` includes,
so mxdev expands the whole chain and inlines the pins, preserving source order and the
`# begin/end constraints from: ...` provenance comments. Packages developed from source or
replaced via `version-overrides` are kept as `# ... -> mxdev disabled` comments (they are
provided through `[tool.uv.sources]` / `override-dependencies` instead):

```toml
[tool.uv]
constraint-dependencies = [
    # managed by mxdev - do not edit
    # begin constraints from: https://dist.plone.org/release/6.2.0rc1/constraints.txt
    "Zope==6.0",
    "AccessControl==7.3",
    # end constraints from: https://dist.plone.org/release/6.2.0rc1/constraints.txt
]
```

mxdev owns this array completely and rewrites it on every run. To turn it off, set in
`mx.ini`:

```ini
[settings]
uv-constraint-dependencies = false
```
````

- [ ] **Step 2: Add attribution in the "Misc" section**

In `README.md`, find the end of the "Misc" section:

```markdown
The VCS-related code is taken from `mr.developer`.
Thanks to Florian Schulze and Contributors.
```

Immediately AFTER those two lines, insert:

```markdown

The approach of importing pip constraints into `[tool.uv] constraint-dependencies` was
inspired by Maik Derstappen's [uv-import-constraint-dependencies](https://github.com/derico-de/uv-import-constraint-dependencies).
Thanks to Maik for the idea and his blessing to adopt it natively.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Document uv constraint-dependencies and add attribution"
```

---

## Task 5: Changelog

**Files:**
- Modify: `CHANGES.md`

- [ ] **Step 1: Add the changelog entry**

In `CHANGES.md`, find:

```markdown
## 5.3.3 (unreleased)

<!-- Add future changes here -->
```

Replace the `<!-- Add future changes here -->` line with:

```markdown
- The uv hook now writes the fully resolved constraints (including external `-c`/`-r`
  chains like Plone release constraints) into `[tool.uv] constraint-dependencies`, so
  `uv sync` honors them. Source order and provenance comments are preserved; the array is
  fully managed by mxdev. Disable via `uv-constraint-dependencies = false` in `[settings]`.
  Inspired by Maik Derstappen's `uv-import-constraint-dependencies`. [jensens]
```

- [ ] **Step 2: Commit**

```bash
git add CHANGES.md
git commit -m "Update CHANGES.md for uv constraint-dependencies"
```

---

## Task 6: Lint and full test suite

- [ ] **Step 1: Run the linter**

Run: `uvx --with tox-uv tox -e lint`
Expected: all hooks pass. If ruff/isort reformat `src/mxdev/uv.py` or `tests/test_uv.py`, stage and commit:

```bash
git add -A
git commit -m "Apply lint formatting"
```

- [ ] **Step 2: Run the full test suite**

Run: `.venv/bin/pytest -v`
Expected: all tests pass (the pre-existing uv tests plus the 8 new ones).

- [ ] **Step 3: Done**

No commit needed if the suite is green and nothing changed.

---

## Self-Review Notes

- **Spec coverage:** Component 1 (`_constraints_to_uv`) → Task 1. Component 2 (write/replace/remove array, managed marker) → Task 2. Opt-out setting → Task 2 + Task 4 docs. Source order + provenance + disabled markers → Tasks 1 & 3 assertions. tomlkit risk → idempotency test (Task 2) + spike (already done). Docs & attribution → Tasks 4 & 5. Tests section of spec → Tasks 1-3.
- **Passthrough (no dedup/sort):** enforced by `_constraints_to_uv` preserving order and not deduping; covered by the `test_constraints_to_uv_filters_and_preserves_order` ordering assertion.
- **Type consistency:** `_constraints_to_uv` returns `list[tuple[str, str]]` with the literal kinds `"comment"`/`"entry"`, consumed identically in `_update_pyproject` and asserted identically in tests.
- **Guard logic note:** When there is nothing to add, `_update_pyproject` returns early **unless** the feature is on and a stale `constraint-dependencies` array exists in an existing `[tool.uv]` table — that single path proceeds to the removal branch. `test_update_pyproject_no_overrides_no_packages_skips` (no stale array) returns early and stays untouched; `test_empty_constraints_removes_stale_managed_array` reaches the removal branch via a configured package (so `nothing_to_write` is already False).
