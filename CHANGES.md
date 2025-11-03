## Changes

## 5.1.0

- Feature: Git repositories can now specify multiple push URLs using multiline syntax in the `pushurl` configuration option. This enables pushing to multiple remotes (e.g., GitHub + GitLab mirrors) automatically. Syntax follows the same multiline pattern as `version-overrides` and `ignores`. Example: `pushurl =` followed by indented URLs on separate lines. When `git push` is run in the checked-out repository, it will push to all configured pushurls sequentially, mirroring Git's native multi-pushurl behavior. Backward compatible with single pushurl strings.
  [jensens, 2025-11-03]
- Feature: Added `--version` command-line option to display the current mxdev version. The version is automatically derived from git tags via hatch-vcs during build. Example: `mxdev --version` outputs "mxdev 5.1.0" for releases or "mxdev 5.1.1.dev27+g62877d7" for development versions.
  [jensens, 2025-11-03]

## 5.0.2 (2025-10-23)

- Fix #70: HTTP-referenced requirements/constraints files are now properly cached and respected in offline mode. Previously, offline mode only skipped VCS operations but still fetched HTTP URLs. Now mxdev caches all HTTP content in `.mxdev_cache/` during online mode and reuses it during offline mode, enabling true offline operation. This fixes the inconsistent behavior where `-o/--offline` didn't prevent all network activity.
  [jensens]
- Improvement: Enhanced help text for `-n/--no-fetch`, `-f/--fetch-only`, and `-o/--offline` command-line options to better explain their differences and when to use each one.
  [jensens]

## 5.0.1 (2025-10-23)

- Fix #65: Check source directories exist before writing to requirements-mxdev.txt. In **offline mode**: missing sources log WARNING and are written as comments (expected behavior). In **non-offline mode**: missing sources log ERROR and mxdev exits with RuntimeError (fatal error indicating checkout failure). This fixes mxmake two-stage installation workflow and prevents silent failures when sources fail to check out.
  [jensens]
- Fix: Configuration parsing no longer logs "Can not parse override:" errors when `version-overrides` is empty. Empty lines in `version-overrides` and `ignores` are now properly skipped during parsing. Also fixed bug where `ignores` lines were not properly stripped of whitespace.
  [jensens]
- Fix: Three tests that were accidentally marked as skipped during PR #66 merge are now fixed and passing: `test_resolve_dependencies_simple_file` (fixed assertion to check line contents), `test_write_output_with_ignores` (fixed to use read() for proper ignore processing), and `test_write_relative_constraints_path_different_dirs` (fixed to include constraints content).
  [jensens]
- Chore: Improved test coverage for main.py from 42% to 100%. Added comprehensive tests for the main() function covering all CLI argument combinations (--verbose, --silent, --offline, --threads, --no-fetch, --fetch-only), ensuring robust testing of the entry point and all code paths.
  [jensens]
- Chore: Updated test fixture data versions to resolve Dependabot security alerts. Updated urllib3 from 1.26.9 to 2.5.0 and requests from 2.28.0 to 2.32.4 in test data files. These are test fixtures only and were never actual dependencies or security risks. Resolves GitHub Dependabot alerts #1-7.
  [jensens]
- Performance: Smart threading now processes HTTPS URLs with `pushurl` in parallel. When a package defines both an HTTPS `url` and a `pushurl` (typically SSH), the HTTPS URL is assumed to be read-only/public and won't prompt for credentials, making it safe for parallel processing. This improves checkout performance for the common pattern of public repos with separate push URLs.
  [jensens]
- Fix: Add 'synchronize' event to pull_request workflow triggers. This ensures CI runs when PRs are updated with new commits (e.g., after rebasing or pushing new changes), not just when opened or reopened.
  [jensens]
- Chore: Optimize GitHub Actions to prevent duplicate workflow runs on pull requests. Restrict `push` trigger to only run on `main` branch, so PRs only trigger via `pull_request` event. This reduces CI resource usage by 50% for PR workflows.
  [jensens]
- Fix: `process_line()` now correctly comments out packages in `override_keys` and `ignore_keys` for both requirements and constraints files. Previously, these settings only applied to constraints files (variety="c"). Now they work for requirements files (variety="r") as well, with the message "-> mxdev disabled (version override)" for override_keys in requirements.
  [jensens]

## 5.0.0 (2025-10-22)

- **Breaking**: Drop support for Python 3.8 and 3.9. Minimum required version is now Python 3.10.
  [jensens]
- **Breaking**: Modernize type hints to use Python 3.10+ syntax (PEP 604: `X | Y` instead of `Union[X, Y]`)
- Use built-in generic types (`list`, `dict`, `tuple`) instead of `typing.List`, `typing.Dict`, `typing.Tuple`
  [jensens]
- Chore: Replace black with ruff for faster linting and formatting. Configure ruff with line-length=120 and appropriate rule selections. Keep isort for import sorting with plone profile and force-alphabetical-sort. This modernizes the tooling stack for better Python 3.10+ support and faster CI runs.
  [jensens]
- Feature: #54: Add `fixed` install mode for non-editable installations to support production and Docker deployments. The new `editable` mode replaces `direct` as the default (same behavior, clearer naming). The `direct` mode is now deprecated but still works with a warning. Install modes: `editable` (with `-e`, for development), `fixed` (without `-e`, for production/Docker), `skip` (clone only).
  [jensens]
- Fix #35: Add `smart-threading` configuration option to prevent overlapping credential prompts when using HTTPS URLs. When enabled (default), HTTPS packages are processed serially first to ensure clean credential prompts, then other packages are processed in parallel for speed. Can be disabled with `smart-threading = false` if you have credential helpers configured.
  [jensens]
- Fix #34: The `offline` configuration setting and `--offline` CLI flag are now properly respected to prevent VCS fetch/update operations. Previously, setting `offline = true` in mx.ini or using the `--offline` CLI flag was ignored, and VCS operations still occurred.
  [jensens]
- Fix #46: Git tags in branch option are now correctly detected and handled during updates. Previously, updating from one tag to another failed because tags were incorrectly treated as branches.
  [jensens]
- Fix #22 and #25: Constraints file path in requirements-out is now correctly calculated as a relative path from the requirements file's directory. This allows requirements and constraints files to be in different directories. Previously, the path was written from the config file's perspective, causing pip to fail when looking for the constraints file. On Windows, paths are now normalized to use forward slashes for pip compatibility.
  [jensens]
- Fix #53: Per-package target setting now correctly overrides default-target when constructing checkout paths.
  [jensens]
- Fix #55: UnicodeEncodeError on Windows when logging emoji. The emoji is now conditionally displayed only when the console encoding supports it (UTF-8), avoiding errors on Windows cp1252 encoding.
  [jensens]

## 4.1.1 (2025-10-20)

- Modernize release method with hatchling. See RELEASE.md [jensens]
- Modernize tox setup. [jensens]
- Modernize Github workflows. [jensens]
- Enhance test coverage [jensens]
- Fix Makefile. [jensens]


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
