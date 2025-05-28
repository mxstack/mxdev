# Mixed development source packages on top of stable constraints using pip

*mxdev* [mɪks dɛv] is a utility that makes it easy to work with Python projects containing lots of packages, of which you only want to develop some.

It builds on top of the idea to have stable version constraints and then develop from a VCS on top of it.

As part of the above use-case sometimes versions of the stable constraints need an override with a different (i.e. newer) version.
Other software follow the same idea are [mr.developer](https://pypi.org/project/mr.developer)  for Python's *zc.buildout* or [mrs-developer](https://www.npmjs.com/package/mrs-developer) for NPM packages.

**[Star us on Github](https://github.com/mxstack/mxdev)**


### Overview

mxdev procedure is:

1. Configuration is read,
2. Requirements and constraints (given in the configuration) are read.
3. Sources from VCS are fetched into a target directory,
4. Modified constraints (handled packages commented, overridden versions replaced) and requirements (handled packages as editable from sources) are written.

mxdev will **not** run *pip* for you!


### Configuration

Given a `requirements.txt` (or similar named) file which itself references a `constraints.txt` file inside.

Create an INI file, like `mx.ini` in [configparser.ExtendedInterpolation](https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation) syntax.


### Main section `[settings]`

The **main section** must be called `[settings]`, even if kept empty.
In the main sections the input and output files are defined.

#### `requirements-in`

Main requirements file to start with. This can be an URL too.

If given an empty value mxdev will only generate output from the information given in INI file itself.

Default: `requirements.txt`

#### `requirements-out`

Output of the combined requirements including development sources to be used later with `pip install`.
Default: `requirements-mxdev.txt`

#### `constraints-out`

Output of the combined constraints.

Default: `constraints-mxdev.txt`

#### `include`

Include one or more other INI files.

The included file is read before the main file, so the main file overrides included settings.
Included files may include other files.
Innermost inclusions are read first.

If an included file is an HTTP-URL, it is loaded from there.

If the included file is a relative path, it is loaded relative to the parents directory or URL.

The feature utilizes the [ConfigParser feature to read multiple files at once](https://docs.python.org/3/library/configparser.html#configparser.ConfigParser.read).

Default: empty

#### `default-target`

Target directory for sources from VCS. Default: `./sources`

#### `default-install-mode`

Default for `install-mode` on section, read there for details
Allowed values: `direct` or `skip`

Default: `direct`

#### `default-update`
Default for `update` on section, read there for details

Allowed values: `yes` or `no`

Default: `yes`

#### `threads`

Number of threads to fetch sources in parallel with.
Speeds up fetching from VCS.

Default: `4`

#### `offline`

Do not fetch any sources.
Handy if working offline.

Default: `False`

#### `version-overrides`

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

Note: When using [uv](https://pypi.org/project/uv/) pip install the version overrides here are not needed, since it [supports overrides nativly](https://github.com/astral-sh/uv?tab=readme-ov-file#dependency-overrides).
With uv it is recommended to create an `overrides.txt` file with the version overrides and use `uv pip install --overrides overrides.txt [..]` to install the packages.


#### `ignores`

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

#### `default-use`

True by default.  When false, the source is not checked out,
and the version for this package is not overridden.
Additionally, custom variables can be defined as `key = value` pair.
Those can be referenced in other values as `${settings:key}` and will be expanded there.

#### `main-package`

mxdev can handle one Python package as main package directly via ini config.
If defined, it will be added as last entry in the resulting requirements out file.

This can be defined as:

```INI
[settings]
main-package = -e .[test]
```

If the main package is defined in a dependent constraint file, it's name must be added to `ignores`.

### Default settings

mxdev provides default settings which can be used inside package or custom
sections.

#### `directory`

Contains the current working directory and can be used like this

```INI
[sectionname]
param = ${settings:directory}/some/path
```

### Subsequent package source sections

All other sections are defining the sources to be used.

#### `[PACKAGENAME]`

The section name is the package name.

#### `url = URL`

The checkout URL of the repository.

The URL is required.

#### `pushurl = URL`

Optional a writable URL for pushes can be specified.

If the `pushurl` is set after initial checkout it is not applied.
To apply it remove the repository and checkout again.

#### `vcs = VCS`

The version control system to use.

Supported are:
- `git` (stable, tested)
- `fs` (stable, tested) - in fact no vcs, but points to a local directory.
  This can be achieved without mxdev by using `-e PATH` in the requirements input file.
- `svn` (unstable, test needs rewrite)
- `gitsvn` (unstable, test needs rewrite)
- `hg` (unstable, test needs rewrite)
- `bzr` (unstable, test needs rewrite)
- `darcs` (unstable, test needs rewrite)

Defaults to `git`.

#### `branch = BRANCHNAME_OR_TAG`

The branch name or tag to checkout.

Defaults to `main`.

#### `extras = EXTRA1,EXTRA2`

Package extras to install. Default empty.

#### `subdirectory = SUBPATH`

For specifying the path to the Python package, when it is not in the root of the VCS directory.

Default empty.

#### `target`

The target directory for source from this section.

Default to default target directory configured in the main section `[settings]` `default-target =` value.

#### `install-mode`

There are different modes of pip installation

##### `skip`

Do not install with pip, just clone/update the repository

##### `direct`

Install the package using `pip -e PACKAGEPATH`.
Dependencies are resolved immediately

Defaults to default mode configured in main section `[settings]` `default-install-mode =` value.

#### `use`

True by default, unless `default-use` in the general settings is false.
When false, the source is not checked out,
and the version for this package is not overridden.

#### `depth`

For `git` only.
This is used to set the git clone depth.
This is not set by default: you get a full clone.
You can set environment variable `GIT_CLONE_DEPTH=1` to set a default git depth for all checkouts.  This is useful for CI.

#### `submodules`

There are 3 different options:

##### `always`

(default) git submodules will always be checked out, they will be updated if already presen

##### `checkout`

submodules get only fetched during checkout, existing submodules stay untouche

##### `recursive`

Fetches submodules recursively, results in `git clone --recurse-submodules on` checkout and `submodule update --init --recursive` on update.

### Usage

Run `mxdev` (for more options run `mxdev --help`).

Mxdev will

1. **read** the configuration from `mx.ini`,
2. **fetch** the packages defined in the config file and
3. **write** a requirements and constraints file.

Now, use the generated requirements and constraints files with i.e. `pip install -r requirements-mxdev.txt`.

**mxdev >=4.0 needs pip version 23 at minimum to work properly**

## Example Configuration

### Example `mx.ini`

This looks like so:

```INI
[settings]
requirements-in = requirements.txt
requirements-out = requirements-mxdev.txt
contraints-out = constraints-mxdev.txt

version-overrides =
    baz.baaz = 1.9.32

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

### Examples at GitHub

- ["new" plone.org backend](https://github.com/plone/plone.org/tree/main/backend)
- [Conestack](https://github.com/conestack/conestack/)
- (add more)


## Extending

The functionality of mxdev can be extended by hooks.
This is useful to generate additional scripts or files or automate any other setup steps related to mxdev's domain.

Extension configuration settings end up in the `mx.ini` file.
They can be added globally to the `settings` section, as dedicated config sections or package specific.
To avoid naming conflicts, all hook-related settings and config sections must be prefixed with a namespace.

It is recommended to use the package name containing the hook as a namespace.

This looks like so:

```INI
[settings]
myextension-global_setting = 1

[myextension-section]
setting = value

[foo.bar]
myextension-package_setting = 1
```
The extension is implemented as a subclass of `mxdev.Hook`:

```Python

from mxdev import Hook
from mxdev import State

class MyExtension(Hook):

    namespace = None
    """The namespace for this hook."""

    def read(self, state: State) -> None:
        """Gets executed after mxdev read operation."""

    def write(self, state: State) -> None:
        """Gets executed after mxdev write operation."""
```

The default settings section from the INI file is available at `state.configuration.settings`.
The package configuration is available at `state.configuration.packages`.
Hook-related config sections are available at `state.configuration.hooks`.

The hook must be registered as an entry point in the `pyproject.toml` of your package:

```TOML
[project.entry-points.mxdev]
hook = "myextension:MyExtension"
```

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
