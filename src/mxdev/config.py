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


def parse_multiline_list(value: str) -> list[str]:
    """Parse a multiline configuration value into a list of non-empty strings.

    Handles multiline format where items are separated by newlines:
        value = "
            item1
            item2
            item3"

    Returns a list of non-empty, stripped strings.
    """
    if not value:
        return []

    # Split by newlines and strip whitespace
    items = [line.strip() for line in value.strip().splitlines()]
    # Filter out empty lines
    return [item for item in items if item]


class Configuration:
    settings: dict[str, str]
    overrides: dict[str, str]
    ignore_keys: list[str]
    packages: dict[str, dict[str, str]]
    hooks: dict[str, dict[str, str]]

    def __init__(
        self,
        mxini: str,
        override_args: dict = {},
        hooks: list["Hook"] = [],
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

        # Set default for smart-threading (process HTTPS packages serially to avoid
        # overlapping credential prompts)
        settings.setdefault("smart-threading", "true")

        mode = settings.get("default-install-mode", "editable")

        # Handle deprecated "direct" mode
        if mode == "direct":
            logger.warning(
                "install-mode 'direct' is deprecated and will be removed in a future version. "
                "Please use 'editable' instead."
            )
            mode = "editable"
            settings["default-install-mode"] = "editable"

        if mode not in ["editable", "fixed", "skip"]:
            raise ValueError(
                "default-install-mode must be one of 'editable', 'fixed', or 'skip' "
                "('direct' is deprecated, use 'editable')"
            )

        default_use = to_bool(settings.get("default-use", True))
        raw_overrides = settings.get("version-overrides", "").strip()
        self.overrides = {}
        for line in raw_overrides.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = Requirement(line)
            except Exception:
                logger.error(f"Can not parse override: {line}")
                continue
            self.overrides[parsed.name] = line

        raw_ignores = settings.get("ignores", "").strip()
        self.ignore_keys = []
        for line in raw_ignores.split("\n"):
            line = line.strip()
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
            # Use package["target"] not 'target' variable to respect per-package target setting (#53)
            package.setdefault("path", os.path.join(package["target"], name))
            if not package.get("url"):
                raise ValueError(f"Section {name} has no URL set!")

            # Special handling for pushurl to support multiple values
            if "pushurl" in package:
                pushurls = parse_multiline_list(package["pushurl"])
                if len(pushurls) > 1:
                    # Store as list for multiple pushurls
                    package["pushurls"] = pushurls
                    # Keep first one in "pushurl" for backward compatibility
                    package["pushurl"] = pushurls[0]
                # If single pushurl, leave as-is (no change to existing behavior)

            # Handle deprecated "direct" mode for per-package install-mode
            pkg_mode = package.get("install-mode")
            if pkg_mode == "direct":
                logger.warning(
                    f"install-mode 'direct' is deprecated and will be removed in a future version. "
                    f"Please use 'editable' instead (package: {name})."
                )
                package["install-mode"] = "editable"
                pkg_mode = "editable"

            if pkg_mode not in ["editable", "fixed", "skip"]:
                raise ValueError(
                    f"install-mode in [{name}] must be one of 'editable', 'fixed', or 'skip' "
                    f"('direct' is deprecated, use 'editable')"
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
    def package_keys(self) -> list[str]:
        return [k.lower() for k in self.packages]

    @property
    def override_keys(self) -> list[str]:
        return [k.lower() for k in self.overrides]
