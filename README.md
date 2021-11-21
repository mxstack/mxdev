# Mixed development source packages on top of stable constraints using pip

`mxdev` is a utility that makes it easy to work with Python projects containing lots of packages, of which you only want to develop some.

It builds on top of the idea to have stable version constraints and then develop on top of it.

Other software following the same idea are [mr.developer](https://pypi.org/project/mr.developer/) for Python's ``zc.buildout`` or [mrs-developer](https://www.npmjs.com/package/mrs-developer) for NPM packages.

## Rationale

Problem:
    There is a constraint file like `-c constraints.txt` with a package `foo.bar` with a version pin.
    Then it is not possible to install this package in a requirements file editable like `-r requirements.txt` with `-e -e git+ssh://git@github.com/orga/foo.bar.git@fix-99#egg=foo.bar`.

Idea:
    A pre-processor fetches (as this can be an URL) and expands all `-c SOMEOTHER_FILE_OR_URL` and `-r SOMEOTHER_FILE_OR_URL` files into one, filtering out all packages given in a configuration file.
    For each of those packages a `-e ...` entry is generated instead and written to a new `TARGET.txt`.

The configuration is written in a file `dev.ini` in [configparser.ExtendedInterpolation](https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation) INI syntax (YAML would be nice, but the package must not have any dependencies to other package)

This looks like so:

```INI
[settings]
infile =requirements.txt
outfile = requirements-dev.txt

# github = git+https://github.com/
github = git+ssh://git@github.com/

[foo.bar]
url = ${settings:github}orga/foo.bar.git
branch = fix99
extras = test,baz
```

## Trivia

Mx (generally pronounced like mix [mɪks], or [məks] in the UK) is meant to be a gender-neutral alternative to the titles Mr. and Ms.
