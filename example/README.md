# mxdev Example Configuration

This directory contains example configuration files that demonstrate various mxdev features.

## Files

- **example.ini** - Main mxdev configuration file demonstrating various features
- **requirements-infile.txt** - Example input requirements file
- **constraints-infile.txt** - Example input constraints file

## Running the Example

To use this example configuration:

```bash
# From the example directory
cd example

# Run mxdev with the example configuration
mxdev -c example.ini

# This will:
# 1. Read requirements-infile.txt and constraints-infile.txt
# 2. Fetch source repositories defined in example.ini
# 3. Generate requirements-outfile.txt and constraints-outfile.txt
#
# Note: The example uses placeholder repositories that don't exist.
# Replace them with real repositories to actually run it.
```

## Features Demonstrated

### Settings Section

The `[settings]` section demonstrates:

- **Input/Output files**: Custom names for requirements and constraints
- **main-package**: Defining the main package being developed
- **version-overrides**: Overriding specific package versions from upstream constraints
- **ignores**: Excluding packages from constraints (e.g., your main package)
- **default-target**: Custom directory for checked out sources
- **threads**: Parallel fetching for faster checkouts
- **Variable substitution**: Reusable variables like `${settings:github}`

### Package Sections

Different package configurations showcase:

1. **foo.bar** - Basic package with branch and extras
2. **plone.behavior** - Shallow clone with `depth=1` (useful for CI)
3. **package.with.submodules** - Git submodules with `submodules=recursive`
4. **package.not.in.root** - Package in subdirectory using `subdirectory`
5. **package.skip.install** - Clone only, skip pip install with `install-mode=skip`
6. **package.custom.location** - Custom target directory with `target`

## Git-Specific Features

### Shallow Clones (depth)

```ini
[plone.behavior]
url = ${settings:github}plone/plone.behavior.git
depth = 1  # Only fetch latest commit
```

Or set globally via environment variable:
```bash
export GIT_CLONE_DEPTH=1
```

### Submodules

```ini
[package.with.submodules]
url = ${settings:github}orga/package.with.submodules.git
submodules = recursive  # Options: always (default), checkout, recursive
```

### Subdirectories

For monorepos where the Python package is not in the repository root:

```ini
[package.not.in.root]
url = ${settings:github}orga/monorepo.git
subdirectory = packages/mypackage
```

## Installation Modes

### Skip Installation

Just clone the repository, don't install with pip (useful for configuration repositories):

```ini
[package.skip.install]
url = ${settings:github}orga/config-only.git
install-mode = skip
```

### Direct Installation (default)

Install package with `pip install -e PACKAGEPATH`:

```ini
[foo.bar]
url = ${settings:github}orga/foo.bar.git
# install-mode = direct  # This is the default
```

## Version Overrides

Override versions from upstream constraints files:

```ini
[settings]
version-overrides =
    baz.baaz==1.9.32
    somepackage==3.0.0
```

**Note**: If using [uv](https://pypi.org/project/uv/), use its native override support instead:

```bash
# Create overrides.txt with version overrides
uv pip install --override overrides.txt -r requirements-mxdev.txt
```

## Ignoring Packages

Exclude packages from constraints (useful for your main package):

```ini
[settings]
ignores =
    my.mainpackage
    package.to.ignore
```

## Custom Variables

Define reusable variables in the settings section:

```ini
[settings]
github = git+ssh://git@github.com/
gitlab = git+ssh://git@gitlab.com/

[foo]
url = ${settings:github}orga/foo.git

[bar]
url = ${settings:gitlab}company/bar.git
```

## Real-World Examples

For real production examples, see:

- [plone.org backend](https://github.com/plone/plone.org/tree/main/backend)
- [Conestack](https://github.com/conestack/conestack/)

## Additional Resources

See the main [README.md](../README.md) for complete documentation of all configuration options.
