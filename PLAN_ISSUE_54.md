# Plan to Solve Issue #54: Add Non-Editable Install Mode

## Problem Summary
Currently, mxdev always installs local packages as **editable** (with `-e` prefix) in the generated requirements file. This is ideal for development but problematic for deployment/Docker containers where packages should be installed to site-packages as standard packages.

**Current behavior:**
```
-e ./sources/iaem.mediaarchive
```

**Desired behavior for deployment:**
```
./sources/iaem.mediaarchive
```

## Solution
Update `install-mode` configuration with clearer naming and add non-editable mode:

**New install modes:**
- `editable` (default): Install as editable with `-e` prefix (development) - **NEW NAME**
- `fixed`: Install as standard package without `-e` (deployment) - **NEW MODE**
- `direct`: Deprecated alias for `editable` (backward compatibility) - **DEPRECATED**
- `skip`: Don't install at all (existing)

## TDD Implementation Steps

### Step 1: Write Failing Tests First 🔴

Following Test-Driven Development, we write tests that define the desired behavior before implementing any code.

#### 1.1 Add Test Data Files ([tests/data/config_samples/](tests/data/config_samples/))

Create test configuration files first:

**config_editable_mode.ini:**
```ini
[settings]
default-install-mode = editable

[example.package]
url = git+https://github.com/example/package.git
```

**config_fixed_mode.ini:**
```ini
[settings]
default-install-mode = fixed

[example.package]
url = git+https://github.com/example/package.git
```

**config_deprecated_direct.ini:**
```ini
[settings]
default-install-mode = direct  # Should log deprecation warning

[example.package]
url = git+https://github.com/example/package.git
```

**config_package_direct.ini:**
```ini
[settings]
default-install-mode = editable

[example.package]
url = git+https://github.com/example/package.git
install-mode = direct  # Should log deprecation warning
```

**Update config_invalid_mode.ini:**
```ini
[settings]
default-install-mode = invalid-mode  # Should raise error mentioning valid modes

[example.package]
url = git+https://github.com/example/package.git
```

#### 1.2 Add Configuration Tests ([tests/test_config.py](tests/test_config.py))

Add tests that will initially FAIL:

```python
def test_configuration_editable_install_mode():
    """Test Configuration with editable install-mode (new default)."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_editable_mode.ini"))

    # Test that editable mode works
    pkg = config.packages["example.package"]
    assert pkg["install-mode"] == "editable"

    # Test that it's the default (when not specified)
    config2 = Configuration(str(base / "config_minimal.ini"))
    pkg2 = config2.packages["example.package"]
    assert pkg2["install-mode"] == "editable"


def test_configuration_fixed_install_mode():
    """Test Configuration with fixed install-mode (new non-editable mode)."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_fixed_mode.ini"))

    # Test that fixed mode works
    pkg = config.packages["example.package"]
    assert pkg["install-mode"] == "fixed"


def test_configuration_direct_mode_deprecated(caplog):
    """Test that 'direct' mode shows deprecation warning but still works."""
    from mxdev.config import Configuration
    import logging

    base = pathlib.Path(__file__).parent / "data" / "config_samples"

    # Test default-install-mode deprecation
    with caplog.at_level(logging.WARNING):
        config = Configuration(str(base / "config_deprecated_direct.ini"))

    # Verify deprecation warning is logged
    assert "install-mode 'direct' is deprecated" in caplog.text
    assert "use 'editable' instead" in caplog.text

    # Verify it's treated as 'editable' internally
    pkg = config.packages["example.package"]
    assert pkg["install-mode"] == "editable"

    # Test per-package level deprecation
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        config2 = Configuration(str(base / "config_package_direct.ini"))

    assert "install-mode 'direct' in package" in caplog.text


def test_configuration_invalid_install_mode_new_message():
    """Test that error messages mention new mode names."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"

    # Test invalid default-install-mode
    with pytest.raises(ValueError, match="must be one of 'editable', 'fixed', or 'skip'"):
        Configuration(str(base / "config_invalid_mode.ini"))
```

**Update existing tests:**
```python
# Update test_configuration_invalid_default_install_mode()
def test_configuration_invalid_default_install_mode():
    """Test Configuration with invalid default-install-mode."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    with pytest.raises(ValueError, match="default-install-mode must be one of 'editable', 'fixed', or 'skip'"):
        Configuration(str(base / "config_invalid_mode.ini"))


# Update test_configuration_invalid_package_install_mode()
def test_configuration_invalid_package_install_mode():
    """Test Configuration with invalid package install-mode."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    with pytest.raises(ValueError, match="install-mode in .* must be one of 'editable', 'fixed', or 'skip'"):
        Configuration(str(base / "config_package_invalid_mode.ini"))


# Update test_configuration_minimal() to verify new default
def test_configuration_minimal():
    """Test Configuration with minimal settings."""
    from mxdev.config import Configuration

    base = pathlib.Path(__file__).parent / "data" / "config_samples"
    config = Configuration(str(base / "config_minimal.ini"))

    pkg = config.packages["example.package"]
    assert pkg["install-mode"] == "editable"  # Changed from "direct" to "editable"
```

#### 1.3 Add Processing Tests ([tests/test_processing.py](tests/test_processing.py))

Update and add tests that will initially FAIL:

```python
def test_write_dev_sources(tmp_path):
    """Test write_dev_sources() creates correct output for different install modes."""
    from mxdev.processing import write_dev_sources

    packages = {
        "editable.package": {
            "target": "sources",
            "extras": "",
            "subdirectory": "",
            "install-mode": "editable",  # Should output: -e ./sources/editable.package
        },
        "fixed.package": {
            "target": "sources",
            "extras": "",
            "subdirectory": "",
            "install-mode": "fixed",  # Should output: ./sources/fixed.package (no -e)
        },
        "skip.package": {
            "target": "sources",
            "extras": "",
            "subdirectory": "",
            "install-mode": "skip",  # Should not appear in output
        },
        "extras.package": {
            "target": "sources",
            "extras": "test,docs",
            "subdirectory": "packages/core",
            "install-mode": "fixed",  # Test fixed mode with extras and subdirectory
        },
    }

    outfile = tmp_path / "requirements.txt"
    with open(outfile, "w") as fio:
        write_dev_sources(fio, packages)

    content = outfile.read_text()

    # Verify editable mode includes -e prefix
    assert "-e ./sources/editable.package\n" in content

    # Verify fixed mode does NOT include -e prefix
    assert "./sources/fixed.package\n" in content
    assert "-e ./sources/fixed.package" not in content

    # Verify skip mode is not in output
    assert "skip.package" not in content

    # Verify fixed mode with extras and subdirectory
    assert "./sources/extras.package/packages/core[test,docs]\n" in content
    assert "-e ./sources/extras.package" not in content
```

### Step 2: Run Tests to Verify They Fail 🔴

Run pytest to confirm tests fail (Red phase):

```bash
source .venv/bin/activate
pytest tests/test_config.py::test_configuration_editable_install_mode -v
pytest tests/test_config.py::test_configuration_fixed_install_mode -v
pytest tests/test_config.py::test_configuration_direct_mode_deprecated -v
pytest tests/test_processing.py::test_write_dev_sources -v
```

Expected: All new tests should FAIL because the implementation doesn't exist yet.

### Step 3: Implement Configuration Changes 🟢

Now implement the code to make tests pass.

#### 3.1 Update Configuration Validation ([config.py](src/mxdev/config.py))
**Files:** `src/mxdev/config.py` lines 54-55, 111-113

Add deprecation handling and new validation:

**Changes:**
```python
# Line 53-55: Update default-install-mode validation with deprecation
mode = settings.get("default-install-mode", "editable")  # Changed default from "direct"

# Handle deprecated "direct" mode
if mode == "direct":
    logger.warning(
        "install-mode 'direct' is deprecated and will be removed in a future version. "
        "Please use 'editable' instead."
    )
    mode = "editable"  # Treat as editable internally

if mode not in ["editable", "fixed", "skip"]:
    raise ValueError(
        "default-install-mode must be one of 'editable', 'fixed', or 'skip' "
        "('direct' is deprecated, use 'editable')"
    )

# Line 104: Set package install-mode
package.setdefault("install-mode", mode)

# Line 111-113: Update per-package install-mode validation with deprecation
pkg_mode = package.get("install-mode")

# Handle deprecated "direct" mode at package level
if pkg_mode == "direct":
    logger.warning(
        f"install-mode 'direct' in package [{name}] is deprecated and will be removed "
        "in a future version. Please use 'editable' instead."
    )
    package["install-mode"] = "editable"  # Normalize internally

if package.get("install-mode") not in ["editable", "fixed", "skip"]:
    raise ValueError(
        f"install-mode in [{name}] must be one of 'editable', 'fixed', or 'skip' "
        "('direct' is deprecated, use 'editable')"
    )
```

#### 3.2 Update Processing Logic ([processing.py](src/mxdev/processing.py))
**Files:** `src/mxdev/processing.py` lines 213-227

Modify `write_dev_sources()` function to handle the new modes:

**Changes:**
```python
def write_dev_sources(fio, packages: typing.Dict[str, typing.Dict[str, typing.Any]]):
    """Create requirements configuration for fetched source packages."""
    if not packages:
        return
    fio.write("#" * 79 + "\n")
    fio.write("# mxdev development sources\n")
    for name, package in packages.items():
        if package["install-mode"] == "skip":
            continue
        extras = f"[{package['extras']}]" if package["extras"] else ""
        subdir = f"/{package['subdirectory']}" if package["subdirectory"] else ""

        # Add -e prefix only for 'editable' mode (not for 'fixed')
        prefix = "-e " if package["install-mode"] == "editable" else ""
        install_line = f"""{prefix}./{package['target']}/{name}{subdir}{extras}\n"""

        logger.debug(f"-> {install_line.strip()}")
        fio.write(install_line)
    fio.write("\n\n")
```

### Step 4: Run Tests to Verify They Pass 🟢

Run pytest again to confirm all tests now pass (Green phase):

```bash
source .venv/bin/activate
pytest tests/test_config.py::test_configuration_editable_install_mode -v
pytest tests/test_config.py::test_configuration_fixed_install_mode -v
pytest tests/test_config.py::test_configuration_direct_mode_deprecated -v
pytest tests/test_processing.py::test_write_dev_sources -v

# Run all tests to ensure nothing broke
pytest tests/test_config.py -v
pytest tests/test_processing.py -v
```

Expected: All tests should PASS now.

### Step 5: Update Documentation

Once tests pass, update user-facing documentation:

#### README.md
**Location:** Lines 89 and 223

Update the tables describing install-mode:

```markdown
| `default-install-mode` | Default `install-mode` for packages: `editable`, `fixed`, or `skip` | `editable` |
```

```markdown
| `install-mode` | `editable`: Install as editable with `pip install -e PACKAGEPATH` (development)<br>`fixed`: Install as regular package with `pip install PACKAGEPATH` (deployment)<br>`skip`: Only clone, don't install<br><br>**Note:** `direct` is deprecated, use `editable` | `default-install-mode` |
```

**Add a Migration/Deprecation Notice section:**
```markdown
### Deprecation Notice

**`install-mode = direct` is deprecated** and will be removed in a future version. Please update your configuration to use `install-mode = editable` instead. The behavior is identical - only the name has changed for clarity.

```ini
# Old (deprecated)
[settings]
default-install-mode = direct

# New (recommended)
[settings]
default-install-mode = editable
```

mxdev will log a warning when deprecated mode names are used.
```

#### CLAUDE.md
**Location:** Line 215

Update description:
```markdown
- Validates install-mode (`editable`, `fixed`, or `skip`; `direct` deprecated), version overrides, and package settings
```

**Location:** Line 289-294

Update example showing new modes:
```ini
[package1]
url = git+https://github.com/org/package1.git
branch = feature-branch
extras = test
install-mode = editable  # For development (with -e)

[package2]
url = git+https://github.com/org/package2.git
branch = main
install-mode = fixed  # For deployment/production (without -e)

[package3]
url = git+https://github.com/org/package3.git
install-mode = skip  # Clone only, don't install
```

### Step 6: Update CHANGES.md

Add entry:
```markdown
- Fix #54: Add `fixed` install-mode option for non-editable installations. Packages with `install-mode = fixed` are installed as regular packages without the `-e` (editable) flag, making them suitable for deployment/production builds where packages should be installed to site-packages.

  **Breaking change (naming only):** Renamed `direct` to `editable` for clarity. The `direct` mode name is still supported but deprecated and will be removed in a future version. Update your configs to use `install-mode = editable` instead of `install-mode = direct`. A deprecation warning is logged when the old name is used.

  [jensens]
```

### Step 7: Update Example Configs (Optional)

**example/mx.ini** - Update any references to show new naming:
```ini
[settings]
default-install-mode = editable  # Development (was: direct)

[some.package]
install-mode = fixed  # For production deployment
```

## Testing Strategy

### Manual Testing
1. Create test config with `install-mode = fixed`
2. Run mxdev
3. Verify generated requirements file has packages without `-e` prefix
4. Test that `pip install -r requirements-mxdev.txt` installs to site-packages
5. Test deprecated `install-mode = direct` shows warning but works

### Automated Testing
1. Unit tests for config validation (all modes including deprecated)
2. Unit tests for deprecation warnings
3. Unit tests for processing output (editable vs fixed)
4. Integration test verifying end-to-end behavior

## Backward Compatibility

✅ **Fully backward compatible**
- `direct` mode continues to work (with deprecation warning)
- Existing configs work unchanged
- Default behavior unchanged (still installs as editable)
- Migration path is clear and documented

## Deprecation Timeline

**Current Release:**
- Add `editable` and `fixed` modes
- Make `direct` deprecated alias for `editable`
- Log warning when `direct` is used
- Update all documentation

**Future Release (e.g., 5.0.0):**
- Remove support for `direct` mode
- Raise error if `direct` is used

## Files to Modify

1. `src/mxdev/config.py` (validation + deprecation logic)
2. `src/mxdev/processing.py` (output generation)
3. `README.md` (user documentation + migration guide)
4. `CLAUDE.md` (developer documentation)
5. `tests/test_config.py` (configuration tests + deprecation tests)
6. `tests/test_processing.py` (processing tests)
7. `CHANGES.md` (changelog with breaking change notice)
8. `tests/data/config_samples/` (test fixtures)
9. `example/mx.ini` (if exists - update examples)

## Summary of Changes

| Old Mode | New Mode | Behavior | Status |
|----------|----------|----------|--------|
| `direct` | `editable` | Install with `-e` flag | Deprecated alias |
| N/A | `fixed` | Install without `-e` flag | **NEW** |
| `skip` | `skip` | Don't install | Unchanged |

**Default:** `editable` (same behavior as old `direct`, just clearer name)
