# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mxdev** is a Python utility that enables managing Python projects with multiple interdependent packages where only a subset needs to be developed locally. It operates as a preprocessor that orchestrates VCS checkouts and generates combined requirements/constraints files for pip installation.

**Key principle:** mxdev does NOT run pip - it prepares requirements and constraints files for pip to use.

## Development Commands

### Installation
```bash
# Install development environment with all dependencies
make install

# This creates a virtual environment in .venv/ and installs:
# - mxdev in editable mode
# - All test dependencies
# - All development tools

# Activate the virtual environment
source .venv/bin/activate
```

### Testing
```bash
# IMPORTANT: Tests must run from the activated virtual environment
source .venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_git.py

# Run specific test function
pytest tests/test_git.py::test_function_name

# Run tests with verbose output
pytest -v

# Or use the Makefile (automatically uses venv)
make test
```

### Coverage

Coverage is automatically collected when running tests via tox or CI.

#### Local Coverage Reporting

```bash
# Run tests with coverage
source .venv/bin/activate
coverage run -m pytest

# View terminal report with missing lines
coverage report --show-missing

# Generate and view HTML coverage report
coverage html
open htmlcov/index.html  # macOS
# or: xdg-open htmlcov/index.html  # Linux
# or: start htmlcov/index.html  # Windows

# Or use Makefile shortcuts (defined in include.mk)
make coverage          # Run tests + combine + show terminal report
make coverage-html     # Run tests + combine + open HTML report
```

**Note:** Coverage targets are defined in [include.mk](include.mk), which is included by the mxmake-generated Makefile and preserved during mxmake updates.

#### CI Coverage

Coverage is automatically collected and combined from all matrix test runs in GitHub Actions:

**Process:**
1. Each test job (Python 3.8-3.14, Ubuntu/Windows/macOS) uploads its `.coverage.*` file as an artifact
2. A dedicated `coverage` job downloads all artifacts
3. Coverage is combined using `coverage combine`
4. Reports are generated:
   - Terminal report added to GitHub Actions summary
   - HTML report uploaded as downloadable artifact
5. CI fails if combined coverage falls below 35% (baseline threshold)

**To view coverage from CI:**
1. Go to Actions tab in GitHub
2. Click on the workflow run
3. Scroll down to Artifacts section
4. Download the `html-coverage-report` artifact
5. Unzip and open `htmlcov/index.html` in a browser

**To adjust coverage threshold:**
Edit `.github/workflows/tests.yaml` and change the `--fail-under=35` value in the "Fail if coverage is below threshold" step.

**Note:** The threshold is currently set to 35% as a baseline. This should be gradually increased as test coverage improves.

#### Coverage Configuration

Coverage settings are in `pyproject.toml` under `[tool.coverage.*]` sections:
- **`[tool.coverage.run]`**: Source paths, branch coverage, parallel mode, file patterns
- **`[tool.coverage.paths]`**: Path mapping for combining coverage across environments
- **`[tool.coverage.report]`**: Excluded lines, precision, display options
- **`[tool.coverage.html]`**: HTML output directory

Key settings:
- `parallel = true` - Allows multiple test runs without overwriting data
- `relative_files = true` - Required for combining coverage across different OSes
- `branch = true` - Measures branch coverage (not just line coverage)
- Excludes: tests/, _version.py, defensive code patterns
```

### Code Quality
```bash
# Run all pre-commit hooks (using uvx with tox-uv)
uvx --with tox-uv tox -e lint

# Run type checking
mypy src/mxdev

# Run flake8
flake8 src/mxdev

# Sort imports
isort src/mxdev
```

### Testing Multiple Python Versions (using uvx tox with uv)
```bash
# Run tests on all supported Python versions (Python 3.8-3.14)
# This uses uvx to run tox with tox-uv plugin for much faster testing (10-100x speedup)
uvx --with tox-uv tox

# Run on specific Python version
uvx --with tox-uv tox -e py311

# Run multiple environments in parallel
uvx --with tox-uv tox -p auto

# Run with extra pytest arguments
uvx --with tox-uv tox -e py312 -- -v -k test_git

# Use a specific Python version with uvx (uv will auto-install if needed)
uvx --python 3.11 --with tox-uv tox -e py311
```

**Note:**
- This project uses `uvx tox` instead of globally installed tox - no installation required!
- tox configuration is defined in [pyproject.toml](pyproject.toml) under `[tool.tox]`
- The `tox-uv` plugin provides 10-100x speedup over traditional pip/virtualenv
- You can create a shell alias for convenience: `alias tox='uvx --with tox-uv tox'`

### Running mxdev
```bash
# Default: reads mx.ini, fetches sources, generates requirements/constraints
mxdev

# Custom config file
mxdev -c custom.ini

# Skip fetching (useful for offline work)
mxdev -n

# Fetch only (don't generate output files)
mxdev -f

# Offline mode (no VCS operations)
mxdev -o

# Control parallelism
mxdev -t 8  # Use 8 threads for fetching

# Verbose output
mxdev -v

# Silent mode
mxdev -s
```

## Architecture

### Core Workflow (Read → Fetch → Write)

The codebase follows a three-phase pipeline:

1. **Read Phase** ([processing.py:read](src/mxdev/processing.py))
   - Parses `mx.ini` configuration
   - Recursively reads requirements and constraints files
   - Supports both local files and HTTP(S) URLs
   - Calls `read_hooks()` for extensibility

2. **Fetch Phase** ([processing.py:fetch](src/mxdev/processing.py))
   - Checks out VCS sources into target directories
   - Uses multi-threaded queue-based workers for parallel operations
   - Supports Git, SVN, Mercurial, Bazaar, Darcs, and local filesystem
   - Controlled by `threads` setting (default: 4)

3. **Write Phase** ([processing.py:write](src/mxdev/processing.py))
   - Generates modified requirements file (packages from source as `-e`)
   - Generates modified constraints file (developed packages commented out)
   - Applies version overrides
   - Calls `write_hooks()` for extensibility

### Key Modules

**[main.py](src/mxdev/main.py)** - CLI entry point
- Argument parsing and validation
- Orchestrates read → fetch → write workflow

**[config.py](src/mxdev/config.py)** - Configuration management
- `Configuration` class: parses INI files with `ExtendedInterpolation`
- Main sections: `[settings]`, package sections, hook sections
- Validates install-mode, version overrides, and package settings

**[state.py](src/mxdev/state.py)** - Application state container
- Immutable dataclass holding `Configuration`, `requirements`, `constraints`
- Passed through the entire pipeline

**[processing.py](src/mxdev/processing.py)** - Core business logic
- `process_line()`: Handles individual requirement lines, comments out developed packages
- `resolve_dependencies()`: Recursively processes `-c` and `-r` references
- File/URL resolution with proper path handling

**[vcs/](src/mxdev/vcs/)** - VCS abstraction layer
- `BaseWorkingCopy`: Abstract base class with `checkout()`, `update()`, `status()`, `matches()`
- `WorkingCopies`: Orchestrates multiple VCS operations with threading
- Entry points-based plugin system for VCS types
- **Git** (production stable): Full support including submodules, shallow clones, branch/tag checkout
- **fs** (stable): Local filesystem pseudo-VCS
- **svn, hg, bzr, darcs** (unstable): Legacy VCS support

**[hooks.py](src/mxdev/hooks.py)** - Extensibility system
- `Hook` base class with `namespace`, `read(state)`, `write(state)` methods
- Loaded via `[project.entry-points.mxdev]` in `pyproject.toml`
- Settings isolated by namespace to avoid conflicts

**[including.py](src/mxdev/including.py)** - Recursive INI inclusion
- `read_with_included()`: Handles `include` directive in `[settings]`
- Supports local files and HTTP(S) URLs
- Relative path resolution from parent file/URL

### Design Patterns

- **Abstract Base Class**: VCS abstraction with pluggable implementations
- **Factory/Registry**: Entry points for VCS types and hooks
- **Producer-Consumer**: Queue-based threading for parallel VCS operations
- **Immutable State**: `State` dataclass prevents mutation bugs
- **Dependency Injection**: Configuration and hooks passed through state

### Important Constraints

1. **Minimal dependencies**: Only `packaging` at runtime - no requests, no YAML parsers
2. **Standard library first**: Uses `configparser`, `urllib`, `threading` instead of third-party libs
3. **No pip invocation**: mxdev generates files; users run pip separately
4. **Backward compatibility**: Supports Python 3.8+ with version detection for Git commands

## Configuration System

mxdev uses INI files with `configparser.ExtendedInterpolation` syntax.

### Variable Expansion
```ini
[settings]
github = git+ssh://git@github.com/

[mypackage]
url = ${settings:github}org/mypackage.git
```

### Common Patterns

**Develop multiple packages with version overrides:**
```ini
[settings]
requirements-in = requirements.txt
requirements-out = requirements-mxdev.txt
constraints-out = constraints-mxdev.txt
version-overrides =
    somepackage==3.0.0
ignores =
    main-package-name
main-package = -e .[test]

[package1]
url = git+https://github.com/org/package1.git
branch = feature-branch
extras = test

[package2]
url = git+https://github.com/org/package2.git
branch = main
install-mode = skip
```

**Using includes for shared configurations:**
```ini
[settings]
include = https://example.com/shared.ini

# Settings here override included settings
```

### Git-Specific Features

**Shallow clones** (faster checkouts):
```ini
[package]
url = ...
depth = 1
```

Or set globally:
```bash
export GIT_CLONE_DEPTH=1
```

**Submodule handling:**
- `always` (default): Always checkout/update submodules
- `checkout`: Only fetch during initial checkout
- `recursive`: Use `--recurse-submodules` for nested submodules

## Testing Infrastructure

### Test Organization
- Tests are colocated with source: `tests/`
- Fixtures in [conftest.py](tests/conftest.py)
- Test utilities in [utils.py](tests/utils.py)

### Key Fixtures
- `tempdir`: Temporary working directory
- `mkgitrepo`: Factory for creating test Git repositories
- `develop`: MockDevelop instance for simulating development environments
- `httpretty`: HTTP mocking for URL-based tests

### Test Coverage Areas
- [test_git.py](tests/test_git.py): Git VCS operations
- [test_git_submodules.py](tests/test_git_submodules.py): Comprehensive submodule scenarios
- [test_including.py](tests/test_including.py): INI file inclusion
- [test_common.py](tests/test_common.py): VCS abstraction utilities

### Writing Tests

When adding VCS functionality, follow existing patterns:
1. Use `mkgitrepo` fixture to create test repositories
2. Create a `develop` instance with mock configuration
3. Test both initial checkout and update scenarios
4. Verify output in requirements/constraints files

## Extensibility via Hooks

To create a mxdev extension:

1. **Create a Hook subclass:**
```python
from mxdev import Hook, State

class MyExtension(Hook):
    namespace = "myext"  # Prefix for all settings

    def read(self, state: State) -> None:
        """Called after read phase."""
        # Access config: state.configuration.settings
        # Access packages: state.configuration.packages
        # Access hook config: state.configuration.hooks

    def write(self, state: State) -> None:
        """Called after write phase."""
        # Generate additional files, scripts, etc.
```

2. **Register as entry point in pyproject.toml:**
```toml
[project.entry-points.mxdev]
myext = "mypackage:MyExtension"
```

3. **Add namespaced config to mx.ini:**
```ini
[settings]
myext-global_setting = value

[myext-section]
specific_setting = value

[somepackage]
myext-package_setting = value
```

## Code Style

- **Formatting**: Black-compatible (max line length: 120)
- **Import sorting**: isort with `force_alphabetical_sort = true`, `force_single_line = true`
- **Type hints**: Use throughout (Python 3.8+ compatible)
- **Path handling**: Prefer `pathlib.Path` over `os.path` for path operations
  - Use `pathlib.Path().as_posix()` for cross-platform path comparison
  - Use `/` operator for path joining: `Path("dir") / "file.txt"`
  - Only use `os.path.join()` in production code where needed for compatibility
- **Logging**: Use `logger = logging.getLogger("mxdev")` from [logging.py](src/mxdev/logging.py)
- **Docstrings**: Document public APIs and complex logic

## CI/CD (GitHub Actions)

The project uses GitHub Actions for continuous integration, configured in [.github/workflows/tests.yaml](.github/workflows/tests.yaml).

### Workflow Overview

**Lint Job:**
- Runs on: `ubuntu-latest`
- Uses: `uvx --with tox-uv tox -e lint`
- Executes pre-commit hooks

**Test Job:**
- **Matrix testing** across:
  - Python versions: 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14
  - Operating systems: Ubuntu, Windows, macOS
  - Total: 21 combinations (7 Python × 3 OS)
- Uses: `uvx --with tox-uv tox -e py{version}`
- Leverages `astral-sh/setup-uv@v7` action for uv installation

### Key Features

- **No pip caching needed**: uv handles caching automatically and efficiently
- **Fast execution**: uv's parallel installation and caching dramatically speeds up CI
- **Python auto-installation**: `uv python install` automatically downloads required Python versions
- **Unified tooling**: Same `uvx --with tox-uv tox` command used locally and in CI

### Modifying CI Workflow

When adding new Python versions:
1. Add to `python-config` matrix in [.github/workflows/tests.yaml](.github/workflows/tests.yaml)
2. Add corresponding environment to `env_list` in [pyproject.toml](pyproject.toml) `[tool.tox]` section
3. Update `requires-python` and classifiers in [pyproject.toml](pyproject.toml) if needed

## Common Development Scenarios

### Adding a new VCS type

1. Create module in [src/mxdev/vcs/](src/mxdev/vcs/) (e.g., `newvcs.py`)
2. Subclass `BaseWorkingCopy` from [vcs/common.py](src/mxdev/vcs/common.py)
3. Implement: `checkout()`, `status()`, `matches()`, `update()`
4. Register in [pyproject.toml](pyproject.toml) under `[project.entry-points."mxdev.workingcopytypes"]`
5. Add tests following [test_git.py](tests/test_git.py) pattern

### Modifying requirements/constraints processing

The core logic is in [processing.py](src/mxdev/processing.py):
- `process_line()`: Handles line-by-line processing
- Look for `# -> mxdev disabled` comments - this is how packages are marked as developed from source
- Version overrides are applied during constraint processing
- Ignore lists prevent certain packages from appearing in output

### Adding configuration options

1. Add default in `SETTINGS_DEFAULTS` in [config.py](src/mxdev/config.py)
2. Access via `configuration.settings` dictionary
3. Document in README.md under appropriate section
4. Add validation if needed in `Configuration.__post_init__()`

## Build System

mxdev uses **Hatchling** as its build backend with the following plugins:

### hatch-vcs (Automatic Versioning)
- **Version source**: Git tags
- **No manual version bumps** needed in code
- Version is automatically derived from git tags during build
- Development versions get format: `4.1.1.dev3+g1234abc`
- Tags must follow format: `vX.Y.Z` (e.g., `v4.2.0`)

### hatch-fancy-pypi-readme (Multi-file README)
- Concatenates multiple markdown files for PyPI long description
- Combines: README.md + CONTRIBUTING.md + CHANGES.md + LICENSE.md
- Adds section headers and separators automatically

### Package Discovery
- Source layout: `src/mxdev/`
- Auto-generated version file: `src/mxdev/_version.py` (in .gitignore)
- Uses `.gitignore` for file inclusion (no MANIFEST.in needed)
- **PEP 420 namespace packages**: `src/mxdev/vcs/` has no `__init__.py` (implicit namespace package)

### Building Locally

```bash
# Clean build artifacts
rm -rf dist/ build/

# Build (requires git tags to determine version)
uv tool run --from build pyproject-build

# Or with python -m build
python -m build

# Check package quality
uv tool run --from twine twine check dist/*
```

**Important:** The version comes from git tags. If building from a commit without a tag, you'll get a development version like `4.1.1.dev3+g1234abc`.

## Release Process

**See [RELEASE.md](RELEASE.md) for complete release documentation.**

Quick summary:

1. Update [CHANGES.md](CHANGES.md) with release notes
2. Commit and push to main
3. Create GitHub Release with tag `vX.Y.Z`
4. GitHub Actions automatically builds and publishes to PyPI

**Key points:**
- ✅ Version automatically set from git tag (no manual edit needed)
- ✅ GitHub Actions handles building and publishing
- ✅ All tests must pass before publishing
- ✅ See [RELEASE.md](RELEASE.md) for detailed workflow

## Development Workflow Best Practices

**CRITICAL: Always follow these steps before pushing code:**

### Pre-Push Checklist

1. **Always run linting before push**
   ```bash
   uvx --with tox-uv tox -e lint
   ```
   - This runs black, mypy, and other code quality checks
   - Fix any issues before committing
   - Commit formatting changes separately if needed

2. **Always update CHANGES.md**
   - Add entry under "## X.X.X (unreleased)" section
   - Format: `- Fix #XX: Description. [author]`
   - Create unreleased section if it doesn't exist
   - Include issue number when applicable

3. **Run relevant tests locally**
   ```bash
   source .venv/bin/activate
   pytest tests/test_*.py -v
   ```

4. **Check CI status before marking PR ready**
   ```bash
   gh pr checks <PR_NUMBER>
   ```
   - Wait for all checks to pass
   - Address any failures before requesting review

### Example Workflow

```bash
# 1. Make changes to code
# 2. Run linting
uvx --with tox-uv tox -e lint

# 3. Fix any linting issues and commit if changes were made
git add .
git commit -m "Run black formatter"

# 4. Run tests
source .venv/bin/activate
pytest -v

# 5. Update CHANGES.md
# Edit CHANGES.md to add entry

# 6. Commit everything
git add .
git commit -m "Fix issue description"

# 7. Push
git push

# 8. Check CI
gh pr checks <PR_NUMBER>

# 9. When green, mark PR ready for review
```

## Git Workflow

- Main branch: `main`
- Create feature branches from `main`
- Create pull requests for all changes
- Ensure tests pass before merging
- Always lint before pushing (see Pre-Push Checklist above)
- Always update CHANGES.md for user-facing changes

## Requirements

- **Python**: 3.8+
- **pip**: 23+ (required for proper operation)
- **Runtime dependencies**: Only `packaging`
- **VCS tools**: Install git, svn, hg, bzr, darcs as needed for VCS operations
