========================================================================
Mixed development source packages on top of stable constraints using pip
========================================================================

``mxdev`` [mɪks dɛv] is a utility that makes it easy to work with Python projects containing lots of packages, of which you only want to develop some.

It builds on top of the idea to have stable version constraints and then develop from a VCS on top of it.

Other software following the same idea are `mr.developer <https://pypi.org/project/mr.developer/>`_  for Python's ``zc.buildout`` or `mrs-developer <https://www.npmjs.com/package/mrs-developer>`_ for NPM packages.

Overview
========

mxdev procedure is:

1. Configuration is read,
2. Requirements and constraints (given in configuration) are read.
3. Sources from VCS are fetched into a target directory,
4. Modified constraints (handled packages commented)/ requirements (handled packages as editable from sources) are written.

mxdev will **not** run pip for you!

Configuration
=============

Given a ``requirements.txt`` (or similar named) file which itself references a ``constraints.txt`` file inside.

Create an INI file, like `sources.ini` in `configparser.ExtendedInterpolation <https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation>`_ syntax.

The **main section** must be called ``[settings]``, even if kept empty.
In the main sections the input and output files are defined.

``requirements-in``
    Main requirements file to start with. This can be an URL too. Default: ``requirements.txt``


``requirements-out``
    Output of the combined requirements including development sources to be used later with ``pip install``. Default: ``requirements-dev.txt``

``constraints-out``
    Output of the combined constraints. Default: ``constraints-dev.txt``

``default-target``
    Target directory for sources from VCS. Default: ``./sources``

``default-position``
    Default position of ``pip install -e`` for sources from VCS in ``requirements-out``.
    Install ``before`` or ``after`` requirements was processed.
    Default: ``after``.

Additional, custom variables can be defined as ``key = value`` pair.
Those can be referenced in other values as ``${settings:key}`` and will be expanded there.

**Subsequent sections** are defining the sources.

``[PACKAGENAME]``
    The section name is the package name.

``url = URL``
    the URL to the source in VCS and must follow the `pip install editable <https://pip.pypa.io/en/stable/cli/pip_install/#local-project-installs>`_ format.
    Attention, this differs from the format one copies from Github/Gitlab, etc.
    The URL is required.

``branch = BRANCHNAME_OR_TAG``
    the branch name or tag to checkout.
    Defaults to `main`.

``extras = EXTRA1,EXTRA2``
     Package extras to install. Default empty.

``subdirectory = SUBPATH``
      For specifying the path to the Python package, when it is not in the root of the VCS directory.
      Default empty.

``target``
    Target directory for source from this section.
    Default to target directory configured in main section ``[settings]`` ``default-target =`` value.

``position``
    Position of ``pip install -e`` for this source in ``requirements-out``.
    Install ``before`` or ``after`` requirements was processed.
    Default to position configured in main section ``[settings]`` ``default-position =`` value.

Usage
=====

Run ``mxdev -c sources.ini``.

Now use the generated requirements and constrainst files with ``pip install -r NEW_REQUIREMENTS_FILENAME.txt``.


Example Configuration
=====================

This looks like so:

.. code-block:: INI

    [settings]
    requirements-in = requirements-infile.txt
    requirements-out = requirements-outfile.txt
    contraints-out = constraints-outfile.txt

    # custom variables
    github = git+ssh://git@github.com/

    [foo.bar]
    url = ${settings:github}orga/foo.bar.git
    branch = fix99
    extras = test,baz

Rationale
=========

Problem
    There is a constraint file like ``-c constraints.txt`` with a package ``foo.bar`` with a version pin.
    Then it is not possible to install this package in a requirements file editable like ``-r requirements.txt`` with ``-e git+ssh://git@github.com/orga/foo.bar.git@fix-99``.

Idea
    A pre-processor fetches (as this can be an URL) and expands all ``-c SOMEOTHER_FILE_OR_URL`` and ``-r SOMEOTHER_FILE_OR_URL`` files into one, filtering out all packages given in a configuration file.
    For each of those packages a ``-e ...`` entry is generated instead and written to a new ``TARGET.txt``.
    The configuration is written in a file ``sources.ini`` in ExtendedInterpolation INI syntax (YAML would be nice, but the package must have as less dependencies as possible to other packages).

Trivia
    Mx (generally pronounced like mix [mɪks], or [məks] in the UK) is meant to be a gender-neutral alternative to the titles Mr. and Ms. but also associates with mix.
