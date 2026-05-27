# Design: pyproject.toml Support for mxdev

**Date**: 2026-05-20
**Status**: Approved

## Goal
Add support for `pyproject.toml` as a configuration source for `mxdev` to align with modern Python tooling standards (PEP 518).

## Brutally Honest Findings & Critique

1.  **The "Standardization" Trap**: By adding TOML support, we are satisfying a superficial desire for "modernity" while losing the features that actually make `mxdev` unique: recursive includes and variable interpolation. Users will likely start in TOML because it's "cleaner," only to hit a wall the moment they need to share configurations across repositories.
2.  **Architectural Debt**: We are implementing a "translation layer" because the core of `mxdev` is so heavily coupled to `ConfigParser` that a proper refactor to a format-agnostic state model would be a major undertaking. We are essentially faking an INI file from a TOML file.
3.  **Fragmented Ecosystem**: We are creating two classes of `mxdev` projects: "Simple" (TOML) and "Advanced" (INI). This adds cognitive load for maintainers who now have to troubleshoot two different configuration schemas.
4.  **Auto-discovery Hazards**: While auto-discovery is convenient, it can lead to "ghost configurations" where `mxdev` behaves unexpectedly because it found settings in a `pyproject.toml` that the user didn't explicitly point it to.

## Design

### 1. Configuration Structure
Configuration will live in the `[tool.mxdev]` namespace:

```toml
[tool.mxdev.settings]
requirements-in = "requirements.txt"
threads = 8

[tool.mxdev.packages.package1]
url = "https://github.com/org/package1.git"

[tool.mxdev.hooks.myhook]
setting = "value"
```

### 2. Auto-Discovery Logic
Priority order:
1.  Explicit `-c / --configuration` flag.
2.  `mx.ini` (default).
3.  `pyproject.toml` (if `mx.ini` is missing and `[tool.mxdev]` is present).

### 3. Implementation Details
- **Parser**: Use `tomllib` (Python 3.11+) or `tomli` (Python 3.10).
- **Dependency**: Add `toml` extra to `pyproject.toml`.
- **Normalization**: The TOML loader will return a dictionary structured like `ConfigParser._sections` to ensure compatibility with the existing `Configuration` class.

### 4. Constraints
- No interpolation (`${var}`).
- No `include` directive.
- Static manifests only.

## Testing Strategy

Brutally honest: Testing this logic requires mocking the filesystem and Python version environments, which is always more fragile than it looks. We need to ensure that the "Priority Order" isn't just a suggestion, but a strictly enforced rule.

### 1. Unit Tests (`tests/test_toml.py`)
- **Structure Parsing**: Verify `tool.mxdev.settings`, `tool.mxdev.packages`, and `tool.mxdev.hooks` correctly map to the internal dictionary format.
- **Dependency Handling**: Mock `ImportError` for both `tomllib` and `tomli` to verify the helpful error message.
- **Normalization**: Ensure all values are converted to strings (as `ConfigParser` would do) to prevent type errors in the rest of the pipeline.

### 2. Integration Tests (`tests/test_config_discovery.py`)
- **Case: Only mx.ini**: Verify it loads `mx.ini`.
- **Case: Only pyproject.toml**: Verify it auto-discovers and loads `pyproject.toml`.
- **Case: Both exist**: Verify it picks `mx.ini` and ignores `pyproject.toml`.
- **Case: Both exist + Explicit flag**: `mxdev -c pyproject.toml` must ignore `mx.ini`.
- **Case: pyproject.toml without tool.mxdev**: Verify it does NOT load it and errors out if `mx.ini` is also missing.
- **Case: Missing all**: Verify it retains its original error behavior (looking for `mx.ini`).

### 3. Regression Tests
- Ensure existing `tests/test_config.py` still passes without modifications, confirming we haven't broken the legacy INI path.

## Success Criteria
- `mxdev` runs successfully using only a `pyproject.toml` file.
- `mxdev -c pyproject.toml` works as expected.
- Clear error message when `tomli` is missing on Python 3.10.
- Existing `mx.ini` projects are unaffected.
