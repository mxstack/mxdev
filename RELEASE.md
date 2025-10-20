# Release Process

This document describes the release process for mxdev.

## Overview

mxdev uses **automated versioning from git tags** via `hatch-vcs`. The version number is automatically derived from git tags during build time, eliminating the need for manual version bumps in code.

## Release Workflow

### Prerequisites

- Commit access to the repository
- PyPI publishing permissions (handled via GitHub Actions)
- All tests passing on main branch

### Step-by-Step Release Process

#### 1. Ensure main branch is ready

```bash
# Make sure you're on main and up to date
git checkout main
git pull origin main

# Verify all tests pass
uvx --with tox-uv tox

# Check current status
git status  # Should be clean
```

#### 2. Review changes since last release

```bash
# See what's changed since last tag
git log $(git describe --tags --abbrev=0)..HEAD --oneline

# Or view in GitHub
# https://github.com/mxstack/mxdev/compare/v4.1.0...main
```

#### 3. Update CHANGES.md

Edit [CHANGES.md](CHANGES.md) to finalize the release notes:

**Before release:**
```markdown
## 4.1.1 (unreleased)

- Modernize release method with hatchling. See RELEASE.md [jensens]
- Modernize tox setup. [jensens]
- Modernize Github workflows. [jensens]
```

**After editing (change `unreleased` to release date and add new unreleased section):**
```markdown
## Changes

## 4.1.2 (unreleased)

<!-- Add future changes here -->


## 4.1.1 (2025-10-20)

- Modernize release method with hatchling. See RELEASE.md [jensens]
- Modernize tox setup. [jensens]
- Modernize Github workflows. [jensens]
```

**Important notes:**
- The version number in CHANGES.md is **manual** (you edit it)
- The package version comes **automatically** from the git tag via hatch-vcs
- Keep the format: `## X.Y.Z (YYYY-MM-DD)` for released versions
- Add `[author]` at the end of each change entry

Commit the changes:

```bash
git add CHANGES.md
git commit -m "Prepare release 4.1.1"
git push origin main
```

#### 4. Create GitHub Release

1. Go to https://github.com/mxstack/mxdev/releases/new
2. Click "Choose a tag" and type the new version: `v4.2.0` (with `v` prefix!)
3. Click "Create new tag: v4.2.0 on publish"
4. Set release title: `v4.2.0` or `Version 4.2.0`
5. Copy relevant section from CHANGES.md into release description
6. Click "Publish release"

**The GitHub Actions workflow will automatically:**
- Run all tests across Python 3.8-3.12 on Ubuntu, Windows, macOS
- Build the package with version `4.2.0` (from the tag)
- Publish to PyPI if tests pass

#### 5. Monitor the release

1. Watch the GitHub Actions workflow: https://github.com/mxstack/mxdev/actions
2. Verify tests pass (usually ~5-10 minutes)
3. Check PyPI once published: https://pypi.org/project/mxdev/

#### 6. Post-release steps (Optional)

After the release is published on PyPI, you may want to:

1. **Update CHANGES.md** to add a new unreleased section for future changes (if not done in step 3):
   ```bash
   # Edit CHANGES.md to add:
   # ## X.Y.Z (unreleased)
   #
   # <!-- Add future changes here -->

   git add CHANGES.md
   git commit -m "Start development of next version"
   git push origin main
   ```

2. **Announce the release** (optional):
   - Post on relevant mailing lists or forums
   - Update documentation if needed
   - Notify users of significant changes

## Version Numbering

mxdev follows [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `4.2.1`)
- **MAJOR**: Breaking changes, incompatible API changes
- **MINOR**: New features, backwards-compatible
- **PATCH**: Bug fixes, backwards-compatible

### Version Format in Git Tags

- Git tags: `vMAJOR.MINOR.PATCH` (e.g., `v4.2.0`)
- Package version: `MAJOR.MINOR.PATCH` (e.g., `4.2.0`)

The `v` prefix in tags is **required** and automatically stripped by hatch-vcs.

## Development Versions

Between releases, development builds automatically get versions like:

```
4.2.0.dev3+g1234abc
```

Where:
- `4.2.0` = Next release version (from last tag)
- `dev3` = 3 commits since last tag
- `g1234abc` = Git commit hash

This happens automatically via `hatch-vcs` - no manual intervention needed.

## Emergency Hotfix Release

For urgent fixes to a released version:

1. Create a branch from the tag:
   ```bash
   git checkout -b hotfix-4.2.1 v4.2.0
   ```

2. Make and commit the fix:
   ```bash
   # Make changes
   git add .
   git commit -m "Fix critical bug X"
   git push origin hotfix-4.2.1
   ```

3. Create pull request to main

4. After merge, follow normal release process with version `v4.2.1`

## Testing a Release (TestPyPI)

To test the release process without publishing to production PyPI:

### 1. Build locally from a tag

```bash
# Create a test tag
git tag v4.2.0-rc1

# Build the package
python -m build

# Check the version in built artifacts
unzip -p dist/mxdev-*.whl mxdev/_version.py
# Should show: __version__ = "4.2.0rc1"

# Clean up test tag
git tag -d v4.2.0-rc1
```

### 2. Upload to TestPyPI (maintainers only)

```bash
# Install twine if needed
pip install twine

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ mxdev
```

## Release Checklist

Use this checklist for each release:

- [ ] All tests passing on main branch
- [ ] CHANGES.md updated with release date (changed from `unreleased`)
- [ ] New unreleased section added to CHANGES.md (for next version)
- [ ] Changes committed and pushed to main
- [ ] GitHub release created with correct tag (format: `vX.Y.Z`)
- [ ] GitHub Actions workflow completed successfully
- [ ] Package visible on PyPI with correct version
- [ ] Release announced (if applicable)

## Troubleshooting

### Build fails with "version not found"

**Cause:** Building outside of a git repository or without tags.

**Solution:** Ensure you're in a git checkout with tags fetched:
```bash
git fetch --tags
python -m build
```

### Version is wrong in built package

**Cause:** Uncommitted changes or wrong tag checked out.

**Solution:** Ensure clean checkout at the tagged commit:
```bash
git checkout v4.2.0
git status  # Should show "HEAD detached at v4.2.0"
python -m build
```

### CI fails to publish to PyPI

**Cause:** Usually authentication issues or PyPI permissions.

**Solution:**
1. Check GitHub Actions workflow logs
2. Verify PyPI trusted publisher configuration
3. Contact repository maintainers

### README doesn't render correctly on PyPI

**Cause:** Markdown formatting issue or missing files.

**Solution:**
1. Test locally: `python -m build && twine check dist/*`
2. Upload to TestPyPI first
3. Fix formatting in README.md, CONTRIBUTING.md, CHANGES.md, or LICENSE.md

## Maintainer Notes

### PyPI Trusted Publisher Setup

This project uses GitHub Actions OIDC for PyPI publishing (no API tokens needed).

Configuration in PyPI:
- Publisher: GitHub
- Owner: mxstack
- Repository: mxdev
- Workflow: release.yaml
- Environment: release

### GitHub Release Environment

The `release` environment in GitHub requires:
- Approval from maintainers (optional, can be configured)
- Runs only on release events

## Changelog Management

mxdev uses a **manual changelog** approach where version numbers and dates in CHANGES.md are updated by hand.

### Format

The changelog follows this simple format:

```markdown
## Changes

## X.Y.Z (unreleased)

- Description of change [author]


## X.Y.Z (YYYY-MM-DD)

- Description of change [author]
- Another change [author]
```

### Key Points

- **Version in CHANGES.md**: Manual - you edit the version number and date
- **Package version**: Automatic - comes from git tag via hatch-vcs
- **During development**: Changes are added under `(unreleased)`
- **Before release**: Change `(unreleased)` to the actual date
- **After release**: Add new `(unreleased)` section for next version

### Why This Works

With hatch-vcs, the package version is determined by git tags at build time. This means:
- You maintain a human-readable changelog in CHANGES.md
- The build system automatically gets the correct version from tags
- No need to keep version numbers in sync between files

### Alternative Tools

For larger teams or to avoid merge conflicts, consider using:
- **Scriv**: Fragment-based changelog management
- **Towncrier**: Popular in the Python ecosystem
- **git-cliff**: Generate from commit messages

See the project's issue tracker or maintainers if you'd like to adopt automated changelog tools.

## Alternative: Manual Release (Not Recommended)

For emergency situations where GitHub Actions is unavailable:

```bash
# 1. Checkout the tag
git checkout v4.2.0

# 2. Build
python -m build

# 3. Upload (requires PyPI credentials)
twine upload dist/*
```

**Note:** This bypasses CI checks and is not recommended for normal releases.

## Version Management Tools

### Checking current version

```bash
# From git tags
git describe --tags

# From installed package
python -c "import mxdev; print(mxdev.__version__)"

# From built package
python -m build
unzip -p dist/mxdev-*.whl mxdev/_version.py
```

### Listing all releases

```bash
# Git tags
git tag --list 'v*' --sort=-version:refname | head

# PyPI releases
pip index versions mxdev
```

## Further Reading

- [Semantic Versioning](https://semver.org/)
- [hatch-vcs Documentation](https://github.com/ofek/hatch-vcs)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [Python Packaging Guide](https://packaging.python.org/)
