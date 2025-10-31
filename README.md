# Mixed development source packages on top of stable constraints using pip

*mxdev* [mɪks dɛv] is a utility that makes it easy to work with Python projects containing lots of packages, of which you only want to develop some.

It builds on top of the idea to have stable version constraints and then develop from a VCS on top of it.

As part of the above use-case sometimes versions of the stable constraints need an override with a different (i.e. newer) version.
Other software follow the same idea are [mr.developer](https://pypi.org/project/mr.developer)  for Python's *zc.buildout* or [mrs-developer](https://www.npmjs.com/package/mrs-developer) for NPM packages.

**[Star us on Github](https://github.com/mxstack/mxdev)**


## Overview

mxdev procedure is:

1. Configuration is read,
2. Requirements and constraints (given in the configuration) are read.
3. Sources from VCS are fetched into a target directory,
4. Modified constraints (handled packages commented, overridden versions replaced) and requirements (handled packages as editable from sources) are written.

mxdev will **not** run *pip* for you!

## Installation

```bash
pip install mxdev
```

**mxdev >=4.0 needs pip version 23 at minimum to work properly**

## Quick Start

1. **Create `mx.ini`** configuration file:

```ini
[settings]
requirements-in = requirements.txt
requirements-out = requirements-mxdev.txt
constraints-out = constraints-mxdev.txt

# Custom variables for reuse
github = git+ssh://git@github.com/

[mypackage]
url = ${settings:github}myorg/mypackage.git
branch = main
extras = test
```

2. **Run mxdev** to fetch sources and generate files:

```bash
mxdev
```

3. **Install with pip** using the generated files:

```bash
pip install -r requirements-mxdev.txt
```

For more examples see the [example/](https://github.com/mxstack/mxdev/tree/main/example) directory.

## Configuration

Configuration is done in an INI file (default: `mx.ini`) using [configparser.ExtendedInterpolation](https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation) syntax.

### Settings Section `[settings]`

The **main section** must be called `[settings]`, even if kept empty.

#### I/O Settings

| Option | Description | Default |
|--------|-------------|---------|
| `requirements-in` | Input requirements file (can be URL). Empty value = generate from INI only | `requirements.txt` |
| `requirements-out` | Output requirements with development sources as `-e` entries | `requirements-mxdev.txt` |
| `constraints-out` | Output constraints (developed packages commented out) | `constraints-mxdev.txt` |

#### Behavior Settings

| Option | Description | Default |
|--------|-------------|---------|
| `default-target` | Target directory for VCS checkouts | `./sources` |
| `threads` | Number of parallel threads for fetching sources | `4` |
| `smart-threading` | Process HTTPS packages serially to avoid overlapping credential prompts (see below) | `True` |
| `offline` | Skip all VCS and HTTP fetches; use cached HTTP content from `.mxdev_cache/` (see below) | `False` |
| `default-install-mode` | Default `install-mode` for packages: `editable`, `fixed`, or `skip` (see below) | `editable` |
| `default-update` | Default update behavior: `yes` or `no` | `yes` |
| `default-use` | Default use behavior (when false, sources not checked out) | `True` |

##### Smart Threading

When `smart-threading` is enabled (default), mxdev uses a two-phase approach to prevent credential prompts from overlapping:

1. **Phase 1**: HTTPS packages **without `pushurl`** are processed serially (one at a time) to ensure clean, visible credential prompts
2. **Phase 2**: Remaining packages (SSH, local, HTTPS with `pushurl`) are processed in parallel for speed

**Optimization**: HTTPS URLs with `pushurl` defined are assumed to be read-only/public and processed in parallel, since the `pushurl` indicates authenticated write access is separate.

This solves the problem where parallel git operations would cause multiple credential prompts to overlap, making it confusing which package needs credentials.

**When to disable**: Set `smart-threading = false` if you have git credential helpers configured (e.g., credential cache, credential store) and never see prompts.

##### Offline Mode and HTTP Caching

When `offline` mode is enabled (or via `-o/--offline` flag), mxdev operates without any network access:

1. **HTTP Caching**: HTTP-referenced requirements/constraints files are automatically cached in `.mxdev_cache/` during online mode
2. **Offline Usage**: In offline mode, mxdev reads from the cache instead of fetching from the network
3. **Cache Miss**: If a referenced HTTP file is not in the cache, mxdev will error and prompt you to run in online mode first

**Example workflow:**
```bash
# First run in online mode to populate cache
mxdev

# Subsequent runs can be offline (e.g., on airplane, restricted network)
mxdev -o

# Cache persists across runs, enabling true offline development
```

**Cache location**: `.mxdev_cache/` (automatically added to `.gitignore`)

**When to use offline mode**:
- Working without internet access (airplanes, restricted networks)
- Testing configuration changes without re-fetching
- Faster iterations when VCS sources are already checked out

**Note**: Offline mode tolerates missing source directories (logs warnings), while non-offline mode treats missing sources as fatal errors.

#### Package Overrides

##### `version-overrides`

Override package versions which are already defined in a dependent constraints file.
I.e. an upstream *constraints.txt* contains already `somefancypackage==2.0.3`.
Given that, for some reason (like with my further developed sources), we need version 3.0.0 of the above package.

Then in this section, this can be defined as:

```INI
[settings]
version-overrides =
    somefancypackage==3.0.0
    otherpackage==33.12.1
```

It is possible to add as many overrides as needed.
When writing the *constraints-out*, the new version will be taken into account.
If there is a source section defined for the same package, the source will be used and entries here are ignored.

Note: When using [uv](https://pypi.org/project/uv/) pip install the version overrides here are not needed, since it [supports overrides natively](https://github.com/astral-sh/uv?tab=readme-ov-file#dependency-overrides).
With uv it is recommended to create an `overrides.txt` file with the version overrides and use `uv pip install --override overrides.txt [..]` to install the packages.


##### `ignores`

Ignore packages that are already defined in a dependent constraints file.
No new version will be provided.
This is specifically handy if a package is going to be installed editable from local file system (like `-e .`), but was already pinned in an upstream constraints file.

This can be defined as:

```INI
[settings]
ignores =
    somefancypackage
    otherpackage
```

##### `main-package`

mxdev can handle one Python package as main package directly via ini config.
If defined, it will be added as last entry in the resulting requirements out file.

This can be defined as:

```INI
[settings]
main-package = -e .[test]
```

If the main package is defined in a dependent constraint file, its name must be added to `ignores`.

#### Advanced Settings

##### `include`

Include one or more other INI files.

The included file is read before the main file, so the main file overrides included settings.
Included files may include other files.
Innermost inclusions are read first.

If an included file is an HTTP-URL, it is loaded from there.

If the included file is a relative path, it is loaded relative to the parent's directory or URL.

Default: empty

##### `directory`

mxdev provides a default setting containing the current working directory which can be used inside package or custom sections:

```INI
[sectionname]
param = ${settings:directory}/some/path
```

##### Custom Variables

Additionally, custom variables can be defined as `key = value` pair.
Those can be referenced in other values as `${settings:key}` and will be expanded there.

```INI
[settings]
github = git+ssh://git@github.com/
gitlab = git+ssh://git@gitlab.com/
```

### Package Source Sections

Sections other than `[settings]` can define:
- **Package sources**: `[PACKAGENAME]` - VCS sources to checkout and develop
- **Hook configuration**: `[hookname-section]` - Settings for mxdev extensions (see [EXTENDING.md](https://github.com/mxstack/mxdev/blob/main/EXTENDING.md))

For package sources, the section name is the package name: `[PACKAGENAME]`

#### Basic Package Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `url` | **required** | VCS checkout URL | — |
| `vcs` | optional | Version control system: `git`, `fs`, `svn`, `gitsvn`, `hg`, `bzr`, `darcs` | `git` |
| `branch` | optional | Branch name or tag to checkout | `main` |
| `extras` | optional | Comma-separated package extras (e.g., `test,dev`) | empty |
| `subdirectory` | optional | Path to Python package when not in repository root | empty |
| `target` | optional | Custom target directory (overrides `default-target`) | `default-target` |
| `pushurl` | optional | Writable URL(s) for pushes. Supports single URL or multiline list for pushing to multiple remotes. Not applied after initial checkout. | — |

**VCS Support Status:**
- `git` (stable, tested)
- `fs` (stable, tested) - local directory pseudo-VCS
- `svn`, `gitsvn`, `hg`, `bzr`, `darcs` (unstable, tests need rewrite)

#### Installation Options

| Option | Description | Default |
|--------|-------------|---------|
| `install-mode` | `editable`: Install with `-e` (development mode)<br>`fixed`: Install without `-e` (production/Docker)<br>`skip`: Only clone, don't install<br>⚠️ `direct` is deprecated, use `editable` | `default-install-mode` |
| `use` | When `false`, source is not checked out and version not overridden | `default-use` |

#### Git-Specific Options

| Option | Description | Default |
|--------|-------------|---------|
| `depth` | Git clone depth (shallow clone). Set `GIT_CLONE_DEPTH=1` env var for global default | full clone |
| `submodules` | Submodule handling: `always`, `checkout`, `recursive` (see below) | `always` |

##### Git Submodule Modes

- **`always`** (default): Git submodules will always be checked out, updated if already present
- **`checkout`**: Submodules only fetched during checkout, existing submodules stay untouched
- **`recursive`**: Fetches submodules recursively, results in `git clone --recurse-submodules` on checkout and `submodule update --init --recursive` on update

##### Multiple Push URLs

You can configure a package to push to multiple remotes (e.g., mirroring to GitHub and GitLab):

```ini
[my-package]
url = https://github.com/org/repo.git
pushurl =
    git@github.com:org/repo.git
    git@gitlab.com:org/repo.git
    git@bitbucket.org:org/repo.git
```

When you run `git push` in the checked-out repository, Git will push to all configured pushurls sequentially.

**Note:** Multiple pushurls only work with the `git` VCS type. This mirrors Git's native behavior where a remote can have multiple push URLs.

### Usage

Run `mxdev` (for more options run `mxdev --help`).

Mxdev will

1. **read** the configuration from `mx.ini`,
2. **fetch** the packages defined in the config file and
3. **write** a requirements and constraints file.

Now, use the generated requirements and constraints files with i.e. `pip install -r requirements-mxdev.txt`.

## Example Configuration

### Example `mx.ini`

This looks like so:

```INI
[settings]
requirements-in = requirements.txt
requirements-out = requirements-mxdev.txt
constraints-out = constraints-mxdev.txt

version-overrides =
    baz.baaz==1.9.32

ignores =
    my.ignoredpackage

# custom variables
github = git+ssh://git@github.com/
mygit = git+ssh://git@git.kup.tirol/

[foo.bar]
url = ${settings:github}orga/foo.bar.git
branch = fix99
extras = test,baz

[kup.fancyproject]
url = ${settings:mygit}customers/fancycorp/kup.fancyproject.git
branch = fix99
extras = test,baz
```

### More Examples

For comprehensive examples demonstrating all features, see the [example/](https://github.com/mxstack/mxdev/tree/main/example) directory.

### Real-World Examples

- ["new" plone.org backend](https://github.com/plone/plone.org/tree/main/backend)
- [Conestack](https://github.com/conestack/conestack/)


## Extending

The functionality of mxdev can be extended by hooks.
This is useful to generate additional scripts or files or automate any other setup steps related to mxdev's domain.

See [EXTENDING.md](https://github.com/mxstack/mxdev/blob/main/EXTENDING.md) for complete documentation on creating mxdev extensions.

## Rationale

### Problem

There is a constraint file like `-c constraints.txt` with a package `foo.bar` with a version pin.
Then it is not possible to install this package in a requirements file editable like `-r requirements.txt` with `-e git+ssh://git@github.com/orga/foo.bar.git@fix-99`.
Neither it is possible to override inherited version constraints with custom ones.

### Idea
A pre-processor fetches (as this can be an URL) and expands all `-c SOMEOTHER_FILE_OR_URL` and `-r SOMEOTHER_FILE_OR_URL` files into one, filtering out all packages given in a configuration file.
For each of those packages, a `-e ...` entry is generated instead and written to a new `TARGET.txt`.
Same is true for version overrides: a new entry is written to the resulting constraints file while the original version is disabled.
The configuration is read from a file `mx.ini` in *ExtendedInterpolation* INI syntax (YAML would be nice, but the package must have as less dependencies as possible to other packages).

### Trivia
Mx (generally pronounced like mix [mɪks], or [məks] in the UK) is meant to be a gender-neutral alternative to the titles Mr. and Ms. but also associates with the word "mix".

## Misc

The VCS-related code is taken from `mr.developer`.
Thanks to Florian Schulze and Contributors.

