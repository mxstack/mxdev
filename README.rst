========================================================================
Mixed development source packages on top of stable constraints using pip
========================================================================

``mxdev`` [mɪks dɛv] is a utility that makes it easy to work with Python projects containing lots of packages, of which you only want to develop some.

It builds on top of the idea to have stable version constraints and then develop from a VCS on top of it.

As part of above use-case sometimes versions of the stable constraints need an override with a different (i.e. newer) version.

Other software following the same idea are `mr.developer <https://pypi.org/project/mr.developer/>`_  for Python's ``zc.buildout`` or `mrs-developer <https://www.npmjs.com/package/mrs-developer>`_ for NPM packages.

**mxdev 2.0 needs pip version 22 at minimum to work properly**


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

Create an INI file, like `mx.ini` in `configparser.ExtendedInterpolation <https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation>`_ syntax.


Main section ``[settings]``
---------------------------

The **main section** must be called ``[settings]``, even if kept empty.
In the main sections the input and output files are defined.

``requirements-in``
    Main requirements file to start with. This can be an URL too.

    If given an empty value mxdev will only generate output from the information given in INI file itself.

    Default: ``requirements.txt``

``requirements-out``
    Output of the combined requirements including development sources to be used later with ``pip install``. Default: ``requirements-mxdev.txt``

``constraints-out``
    Output of the combined constraints. Default: ``constraints-mxdev.txt``

``default-target``
    Target directory for sources from VCS. Default: ``./sources``

``default-install-mode``
    Default for ``install-mode`` on section, read there for details
    Allowed values: ``direct`` or ``skip``
    Default: ``direct``

``default-update``
    Default for ``update`` on section, read there for details
    Allowed values: ``yes`` or ``no``
    Default: ``yes``

``threads``
    Number of threads to fetch sources in parallel with.
    Speeds up fetching from VCS.
    Default: ``4``

``offline``
    Do not fetch any sources.
    Handy if working offline.
    Default: ``False``

``version-overrides``
    Override package versions which already defined in a dependent constraints file.
    I.e. an upstream *constraints.txt* contains already ``somefancypackage==2.0.3``.
    Given, for some reason (like with my further developed sources), we need version 3.0.0 of above package.
    Then in this section this can be defined as:

    .. code-block:: ini

        [settings]
        version-overrides =
            somefancypackage==3.0.0
            otherpackage==33.12.1

    It is possible to add as many overrides as needed.
    When writing the *constraints-out*, the new version will be taken into account.
    If there is a source-section defined for the same package, the source will be used and entries here are ignored.

``ignores``
    Ignore packages which are already defined in a dependent constraints file.
    No new version will be provided.
    This is specifically handy if a package is going to be installed editable from local file system (like ``-e .``), but was already pinned in an upstream constraints-file.

    This can be defined as:

    .. code-block:: ini

        [settings]
        ignores =
            somefancypackage
            otherpackage

Additional, custom variables can be defined as ``key = value`` pair.
Those can be referenced in other values as ``${settings:key}`` and will be expanded there.


Subsequent package source sections
----------------------------------

All other sections are defining the sources to be used.

``[PACKAGENAME]``
    The section name is the package name.

``url = URL``
    The checkout URL of the repository.

    The URL is required.

``pushurl = URL``
    Optional a writable URL for pushes can be specified.

    If the ``pushurl`` is set after initial checkout it is not applied.
    To apply it remove the repository and checkout again.

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
    Default to default target directory configured in main section ``[settings]`` ``default-target =`` value.

``install-mode``
    There are different modes of pip installation:

    ``skip``
        Do not install with pip, just clone/update the repository.

    ``direct``
        Install the package using ``pip -e PACKAGEPATH``.
        Dependencies are resolved immediately.


    Defaults to default mode configured in main section ``[settings]`` ``default-install-mode =`` value.

``submodules``
    There are 3 different options

    ``always``
        (default) git submodules will always be checked out, the will be updated if already present

    ``checkout``
        submodules get only fetched during checkout, existing submodules stay untouched

    ``recursive``
        fetches submodules recursively, results in ``git clone --recurse-submodules on`` checkout
        and ``submodule update --init --recursive`` on update

Usage
=====

Run ``mxdev`` (for more options run ``mxdev --help``).

Mxdev will

1. **read** the configuration from ``mx.ini``,
2. **fetch** the packages defined in the config file and
3. **write** a requirements and constraints file.

Now, use the generated requirements and constraints files with i.e. ``pip install -r requirements-mxdev.txt``.


Example Configuration
=====================

Example ``mx.ini``
------------------

This looks like so:

.. code-block:: ini

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


Examples at GitHub
------------------

- `"new" plone.org backend <https://github.com/plone/plone.org/tree/main/backend>`_
- (add more)


Extending
=========

Functionality of mxdev can be extended by hooks.
This is useful to generate additional scripts or files or automate any other setup steps related to mxdev's domain.

Extension configuration settings end up in the ``mx.ini`` file.
They can be added globally to the ``settings`` section, as dedicated config sections or package specific.
To avoid naming conflicts, all hook related settings and config sections must be prefixed with a namespace.

It is recommended to use the package name containing the hook as namespace.

This looks like so:

.. code-block:: ini

    [settings]
    myextension-global_setting = 1

    [myextension-section]
    setting = value

    [foo.bar]
    myextension-package_setting = 1

The extension is implemented as subclass of ``mxdev.Hook``:

.. code-block:: python

    from mxdev import Hook
    from mxdev import State

    class MyExtension(Hook):

        namespace = None
        """The namespace for this hook."""

        def read(self, state: State) -> None:
            """Gets executed after mxdev read operation."""

        def write(self, state: State) -> None:
            """Gets executed after mxdev write operation."""

The default settings section from the INI file is available at ``state.configuration.settings``.
The package configuration is available at ``state.configuration.packages``.
Hook related config sections are available at ``state.configuration.hooks``.

The hook must be registered as entry point in the ``setup.py`` or ``setup.cfg`` of your package:

.. code-block:: python

    setup(
        name='myextension',
        ...
        entry_points={
            'mxdev': [
                'hook = myextension:MyExtension',
            ]
        }
    )


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
    The configuration is read from a file ``mx.ini`` in *ExtendedInterpolation* INI syntax (YAML would be nice, but the package must have as less dependencies as possible to other packages).

Trivia
    Mx (generally pronounced like mix [mɪks], or [məks] in the UK) is meant to be a gender-neutral alternative to the titles Mr. and Ms. but also associates with mix.


Misc
====

The VCS related code is taken from `mr.developer`.
Thanks to Florian Schulze and Contributors.
