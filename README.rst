========================================================================
Mixed development source packages on top of stable constraints using pip
========================================================================

``mxdev`` [mɪks dɛv] is a utility that makes it easy to work with Python projects containing lots of packages, of which you only want to develop some.

It builds on top of the idea to have stable version constraints and then develop from a VCS on top of it.

As part of above use-case sometimes versions of the stable constraints need an override with a different (i.e. newer) version.

Other software following the same idea are `mr.developer <https://pypi.org/project/mr.developer/>`_  for Python's ``zc.buildout`` or `mrs-developer <https://www.npmjs.com/package/mrs-developer>`_ for NPM packages.

Overview
========

mxdev procedure is:

1. Configuration is read,
2. Requirements and constraints (given in configuration) are read.
3. Sources from VCS are fetched into a target directory,
4. Modified constraints (handled packages commented, overridden versions replaced) and  requirements (handled packages as editable from sources) are written.

mxdev will **not** run *pip* for you!

Configuration
=============

Given a ``requirements.txt`` (or similar named) file which itself references a ``constraints.txt`` file inside.

Create an INI file, like `sources.ini` in `configparser.ExtendedInterpolation <https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation>`_ syntax.

Main section ``[settings]``
---------------------------

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

``default-install-mode``
    Default for ``install-mode`` on section, read there for details
    Allowed values: ``direct``, ``interdependency``, ``skip``
    Default: ``interdependency``

``version-overrides``
    Override package versions which already defined in a dependent constraints file.
    I.e. an upstream *constraints.txt* contains already ``somefancypackage==2.0.3``.
    For some reason (like with my further developed sources) we need version 3.0.0 of above package.
    Then in this section this can be defined as:

    .. code-block:: INI

        [settings]
        version-overrides =
            somefancypackage==3.0.0
            otherpackage==33.12.1

    It is possible to add as many overrides as needed.
    When writing the *constraints-out*, the new version will be taken into account.
    If there is a source-section defined for the same package, the source will be used and entries here are ignored.

Additional, custom variables can be defined as ``key = value`` pair.
Those can be referenced in other values as ``${settings:key}`` and will be expanded there.


Subsequent package source sections
----------------------------------

All other sections are defining the sources to be used.

``[PACKAGENAME]``
    The section name is the package name.

``url = URL``
    the URL to the source in VCS and must follow the `pip install editable <https://pip.pypa.io/en/stable/cli/pip_install/#local-project-installs>`_ format.

    Attention, this differs from the format one copies from Github/Gitlab, etc.
    For convienince *mxdev* applies auto-correction for this common cases:

    - ``ssh://`` -> ``git+ssh://``
    - ``git@`` -> ``git+ssh://git@``
    - ``https://`` t-> ``git+https://``

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
    Default to ``target`` directory configured in main section ``[settings]`` ``default-target =`` value.

``install-mode``
    There are different modes of pip installation:

    ``skip``
        Do not install with pip, just clone/update the repository.

    ``direct``
        Install the package using ``pip -e PACKAGEPATH``.
        Dependencies are resolved immediately.

    ``interdependency``
        Pre-install the packages first using ``pip -e PACKAGEPATH --install-option="--no-deps"``.
        After all packages are pre-installed, install them again with dependencies using ``pip -e PACKAGEPATH``.
        This helps if one develops many package with dependencies between those packages.
        With *direct* the order of the packages matters, so a developer would need to do manual dependency management.
        With *interdependency* mode this is circumevented by pre-installing all this packages without dependencies first.

    Defaults to ``install-dependencies`` configured in main section ``[settings]`` ``default-install-mode =`` value.

Usage
=====

Run ``mxdev -c sources.ini``.

Now use the generated requirements and constrainst files with ``pip install -r NEW_REQUIREMENTS_FILENAME.txt``.

For more options run ``mxdev --help``.


Example Configuration
=====================

Example ``sources.ini``
-----------------------

This looks like so:

.. code-block:: INI

    [settings]
    requirements-in = requirements.txt
    requirements-out = requirements-mxdev.txt
    contraints-out = constraints-mxdev.txt

    version-overrides =
        baz.baaz = 1.9.32

    # custom variables
    github = git+ssh://git@github.com/
    mygit = git+ssh://git@git.kup.tirol/

    [foo.bar]
    url = ${settings:github}orga/foo.bar.git
    branch = fix99
    extras = test,baz

    [kup.fancyproject]
    url = ${settings:mygit}kcustomers/fancycorp/kup.fancyproject.git
    branch = fix99
    extras = test,baz
    mode = direct

Examples at Github
------------------

- `"new" plone.org backend <https://github.com/plone/plone.org/tree/main/backend>`_
- (add more)


Rationale
=========

Problem
    There is a constraint file like ``-c constraints.txt`` with a package ``foo.bar`` with a version pin.
    Then it is not possible to install this package in a requirements file editable like ``-r requirements.txt`` with ``-e git+ssh://git@github.com/orga/foo.bar.git@fix-99``.
    Neither it is possible to override inherited version constraints with custom ones.

Idea
    A pre-processor fetches (as this can be an URL) and expands all ``-c SOMEOTHER_FILE_OR_URL`` and ``-r SOMEOTHER_FILE_OR_URL`` files into one, filtering out all packages given in a configuration file.
    For each of those packages a ``-e ...`` entry is generated instead and written to a new ``TARGET.txt``.
    Same is true for version overrides: a new entry is written to the resulting constraints file while the original version is disabled.
    The configuration is read from a file ``sources.ini`` in *ExtendedInterpolation* INI syntax (YAML would be nice, but the package must have as less dependencies as possible to other packages).

Trivia
    Mx (generally pronounced like mix [mɪks], or [məks] in the UK) is meant to be a gender-neutral alternative to the titles Mr. and Ms. but also associates with mix.
