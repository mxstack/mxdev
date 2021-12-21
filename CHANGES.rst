Changes
=======

1.0.1 (2021-12-21)
------------------

- Fix: If a developed package depends on another developed package the dependent package was ignored *sometimes* (!?).
  Instead the last release was taken.
  Solution: Install it with the `--pre` option in order allow the other non-final/in-development *release*.
  [jensens]


1.0.0 (2021-12-12)
------------------

- Defaults for "outfiles" are ``*-mxdev.txt`` now.
  [jensens]


1.0.0b4 (2021-12-07)
--------------------

- Fix interdependency mode.
  [jensens]


1.0.0b3 (2021-12-07)
--------------------

- Fix: Do not apply override disabling on requirements.
  [jensens]


1.0.0b2 (2021-12-07)
--------------------

- Add feature: version overrides.
  [jensens]


1.0.0b1 (2021-12-04)
--------------------

- Add ``-s`` or ``--silent`` option.
  [jensens]

- Beautified output.
  [jensens]

- Fixed missing CR if ``*.txt`` does not end with newline.
  [jensens]


1.0.0a9 (2021-12-01)
--------------------

- Added auto correction for pip URLs, so that GitHub or Gitlab URLs can be used as copied in `sources.ini`.
  [zworkb]


1.0.0a8 (2021-11-30)
--------------------

- Added interdependency handling to avoid manual dependency order resolution.
  [jensens, gogobd]

- Added skip mode to exclude packages from installation (clone/update only).
  [jensens, gogobd]

- Removed position feature.
  [jensens, gogobd]


1.0.0a7 (2021-11-30)
--------------------

- Removed Workaround for libvcs and depend on libvcs>=0.10.1.
  [jensens]


1.0.0a6 (2021-11-30)
--------------------

- Workaround for libvcs bug https://github.com/vcs-python/libvcs/issues/295
  [jensens, gogobd]


1.0.0a5 (2021-11-30)
--------------------

- Workaround for libvcs bug https://github.com/vcs-python/libvcs/issues/293
  [jensens, gogobd]


1.0.0a4 (2021-11-29)
--------------------

- Fix: editable can be configured to be processed before or after initial requirements.
  [jensens]


1.0.0a3 (2021-11-23)
--------------------

- Fix #1: Re-run of pip vanishes committed changes
  [jensens]


1.0.0a2 (2021-11-21)
--------------------

- Fix/simplify packaging.
  [jensens]

- Implement subdirectory editable install
  [jensens]

- Implement package extras
  [jensens]


1.0.0a1 (2021-11-21)
--------------------

- Initial work.
  [jensens]
