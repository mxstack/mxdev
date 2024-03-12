from .including import read_with_included
from .logging import logger
from packaging.requirements import Requirement

import os
import typing


if typing.TYPE_CHECKING:
    from .hooks import Hook


def to_bool(value):
    if not isinstance(value, str):
        return bool(value)
    return value.lower() in ("true", "on", "yes", "1")


class Configuration:
    settings: typing.Dict[str, str]
    overrides: typing.Dict[str, str]
    ignore_keys: typing.List[str]
    packages: typing.Dict[str, typing.Dict[str, str]]
    hooks: typing.Dict[str, typing.Dict[str, str]]

    def __init__(
        self,
        mxini: str,
        override_args: typing.Dict = {},
        hooks: typing.List["Hook"] = [],
    ) -> None:
        logger.debug("Read configuration")
        data = read_with_included(mxini)

        settings = self.settings = dict(data["settings"].items())

        logger.debug(f"infile={self.infile}")
        logger.debug(f"out_requirements={self.out_requirements}")
        logger.debug(f"out_constraints={self.out_constraints}")

        if override_args.get("offline"):
            settings["offline"] = "true"

        if override_args.get("threads"):
            settings["threads"] = str(override_args.get("threads"))
        else:
            settings["threads"] = "4"

        mode = settings.get("default-install-mode", "direct")
        if mode not in ["direct", "skip"]:
            raise ValueError("default-install-mode must be one of 'direct' or 'skip'")

        default_use = to_bool(settings.get("default-use", True))
        raw_overrides = settings.get("version-overrides", "").strip()
        self.overrides = {}
        for line in raw_overrides.split("\n"):
            try:
                parsed = Requirement(line)
            except Exception:
                logger.error(f"Can not parse override: {line}")
                continue
            self.overrides[parsed.name] = line

        raw_ignores = settings.get("ignores", "").strip()
        self.ignore_keys = []
        for line in raw_ignores.split("\n"):
            line.strip()
            if line:
                self.ignore_keys.append(line)

        def is_ns_member(name) -> bool:
            for hook in hooks:
                if name.startswith(hook.namespace):
                    return True
            return False

        self.hooks = {}
        self.packages = {}
        target = settings.get("default-target", "sources")
        for name in data.sections():
            if is_ns_member(name):
                logger.debug(f"Section '{name}' belongs to hook")
                self.hooks[name] = self._read_section(data, name)
                continue
            logger.debug(f"Section '{name}' belongs to package")
            package = self._read_section(data, name)
            if not to_bool(package.get("use", default_use)):
                continue
            self.packages[name] = package
            if settings.get("offline", False):
                package.setdefault("offline", True)
            # XXX: name should not be necessary in WorkingCopies
            package["name"] = name
            # XXX:
            #  * include update
            package.setdefault("branch", "main")
            package.setdefault("extras", "")
            package.setdefault("subdirectory", "")
            package.setdefault("target", target)
            package.setdefault("install-mode", mode)
            package.setdefault("vcs", "git")
            # XXX: path should not be necessary in WorkingCopies
            package.setdefault("path", os.path.join(target, name))
            if not package.get("url"):
                raise ValueError(f"Section {name} has no URL set!")
            if package.get("install-mode") not in ["direct", "skip"]:
                raise ValueError(
                    f"install-mode in [{name}] must be one of 'direct' or 'skip'"
                )

            # repo_dir = os.path.abspath(f"{package['target']}/{name}")
            # pip_url = autocorrect_pip_url(f"{package['url']}@{package['branch']}")
            # logger.debug(f"pip_url={pip_url} -> repo_dir={repo_dir}")
            # repo = create_project_from_pip_url(pip_url=pip_url, repo_dir=repo_dir)

            logger.debug(f"config data={self.packages[name]}")

    def _read_section(self, data, name):
        # read section without defaults.
        section_keys = data._sections[name].keys()
        section = data[name]
        return {k: section[k] for k in section_keys}

    @property
    def infile(self) -> str:
        return self.settings.get("requirements-in", "requirements.txt")

    @property
    def out_requirements(self) -> str:
        return self.settings.get("requirements-out", "requirements-mxdev.txt")

    @property
    def out_constraints(self) -> str:
        return self.settings.get("constraints-out", "constraints-mxdev.txt")

    @property
    def package_keys(self) -> typing.List[str]:
        return [k.lower() for k in self.packages]

    @property
    def override_keys(self) -> typing.List[str]:
        return [k.lower() for k in self.overrides]
