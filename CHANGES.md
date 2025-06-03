## Changes

## 4.1.0 (2025-06-03)

- Support environment variable `GIT_CLONE_DEPTH` for setting a default git depth for all checkouts.  Useful for CI.
  [maurits]

- Fix #47: Do not add packages with capital names uncommented at the bottom ignore list when checked out.
  [petschki]

## 4.0.3 (2024-05-17)

- Fix #45: Packages with capital names do not get ignored when checked out.
  [jensens]


## 4.0.2 (2024-03-13)

- Fix #42: deprecated use of `pkg_resoures` to load entry points and parse requirements.
  This enables mxdev to work on Python 3.12, where `pkg_resources` is no longer installed by default in virtual_envs.
  [jensens]

## 4.0.1 (2024-03-01)

- Fix specifying out a revision (#40)
  [pbauer]

### 4.0.0 (2024-02-28)

- Breaking: Remove `--pre` on sources from generated `requirements-mxdev.txt`.
  Usually it is not needed any longer, at least withy pip 23.x.
  This is a breaking change if you rely on the `--pre` option being present in the generated file.
  Now the `--pre` option should be added to `pip install` when the generated file is used.
  This change enables the use of the generated file with the alternative pip replacement `uv`.
  [jensens]

- Breaking: Drop official support for Python 3.7 (it is end of life).
  [jensens]

- Document `mx.ini` sections `vcs` setting.
  [jensens]

### 3.1.0 (2023-12-10)

- Feature: Provide `directory` default setting [rnix]
- Feature: Include other INI config files [jensens]

### 3.0.0 (2023-05-08)

- Removed leftover print [jensens]

### 3.0.0b3 (2023-04-23)

- Fix usage of `--install-option='pre'` and use `--pre` option in requirements files instead.
  The install options are deprecated in pip 23 which Plone switched to recently.
  More info:
  https://github.com/pypa/pip/issues/11358
  https://discuss.python.org/t/passing-command-line-arguments-to-pip-install-after-install-options-deprecation/22981/6
  [thet, fredvd]

- Fix reading sections from the config parser without defaults if the section contains a setting that also exists as default.
  [rnix]

- Do not write constraints out to the file if no constraints are defined.
  [rnix]

- Add the `main-package` option to the settings.
  [rnix]

### 3.0.0b2 (2023-02-07)

- In this package, use `pyproject.toml` and markdown for README et al.
  [jensens]

- Add `use` option to sources, and `default-use` to the settings.
  `default-use` is true by default.
  When false, the source is not checked out, and the version for this package is not overridden.
  [maurits]


### 3.0.0b1 (2022-11-21)

- Do not use `libvcs`, but recycled and updated (type hints, tests) `mr.developer` VCS code.
  Code for GIT is tested well, code for SVN, Mercurial, Bazaar and DARCS needs contributors with knowledge in this area.
  Additional options, like `pushurl`, ... (see README) were added.
  `pip` style VCS URLs are not supported any longer.
  [jensens, rnix, zworkb]

- Config parser options are now considered case-sensitive.
  [rnix]

- Do not fail `mxdev` run if `requirements.txt` is missing.
  [rnix]

- Add flag to only fetch repositories and skip generating files.
  [rnix]

- Add flag to skip fetching of repositories.
  [rnix]

- Add support for custom hooks.
  [rnix]

- Rename `sources.ini` to `mx.ini` in the documentation.
  [rnix]

- Introduce state object and pass it to read/fetch/write.
  State object contains all required runtime data.
  [rnix]


### 2.0.0 (2022-01-31)

- Depend on pip 22, where interdependency mode is no longer needed.
  Remove all interdependency-related code.
  [jensens]

- Better error message if the requirements-in file does not exist.
  [jensens]

- Better last message with the full pip command.
  [jensens]

- Allow empty `requirements-in` configuration.
  [jensens]

### 1.1.0 (2021-12-29)

- Feature: Ignore existing constraints.
  New setting `ignores` with a list of packages (one per line) to ignore constraints without providing a version.
  [jensens]


### 1.0.1 (2021-12-21)

- Fix: If a developed package depends on another developed package the dependent package was ignored *sometimes* (!?).
  Instead, the last release was taken.
  Solution: Install it with the `--pre` option in order to allow the other non-final/in-development *release*.
  [jensens]


### 1.0.0 (2021-12-12)

- Defaults for "outfiles" are `*-mxdev.txt` now.
  [jensens]


### 1.0.0b4 (2021-12-07)

- Fix interdependency mode.
  [jensens]


### 1.0.0b3 (2021-12-07)

- Fix: Do not apply override disabling on requirements.
  [jensens]


### 1.0.0b2 (2021-12-07)

- Add feature: version overrides.
  [jensens]


### 1.0.0b1 (2021-12-04)

- Add `-s` or `--silent` option.
  [jensens]

- Beautified output.
  [jensens]

- Fixed missing CR if `*.txt` does not end with a newline.
  [jensens]


### 1.0.0a9 (2021-12-01)

- Added auto correction for pip URLs, so that GitHub or GitLab URLs can be used as copied in `sources.ini`.
  [zworkb]


### 1.0.0a8 (2021-11-30)

- Added interdependency handling to avoid manual dependency order resolution.
  [jensens, gogobd]

- Added skip mode to exclude packages from installation (clone/update only).
  [jensens, gogobd]

- Removed position feature.
  [jensens, gogobd]


### 1.0.0a7 (2021-11-30)

- Removed Workaround for libvcs and depend on libvcs>=0.10.1.
  [jensens]


### 1.0.0a6 (2021-11-30)

- Workaround for libvcs bug https://github.com/vcs-python/libvcs/issues/295
  [jensens, gogobd]


### 1.0.0a5 (2021-11-30)

- Workaround for libvcs bug https://github.com/vcs-python/libvcs/issues/293
  [jensens, gogobd]


### 1.0.0a4 (2021-11-29)

- Fix: editable can be configured to be processed before or after initial requirements.
  [jensens]


### 1.0.0a3 (2021-11-23)

- Fix #1: Re-run of pip vanishes committed changes
  [jensens]


### 1.0.0a2 (2021-11-21)

- Fix/simplify packaging.
  [jensens]

- Implement subdirectory editable install
  [jensens]

- Implement package extras
  [jensens]


### 1.0.0a1 (2021-11-21)

- Initial work.
  [jensens]
