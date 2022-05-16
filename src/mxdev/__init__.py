from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from pkg_resources import iter_entry_points
from urllib import parse
from urllib import request

import argparse
import configparser
import logging
import os
import pkg_resources
import sys
import typing


try:
    # libvcs 0.12+
    from libvcs.shortcuts import create_project_from_pip_url
except ImportError:
    # BBB for libvcs 0.11-
    from libvcs.shortcuts import create_repo_from_pip_url as create_project_from_pip_url


logger = logging.getLogger("mxdev")


parser = argparse.ArgumentParser(
    description="Make it easy to work with Python projects containing lots "
    "of packages, of which you only want to develop some.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "-c",
    "--configuration",
    help="configuration file in INI format",
    nargs="?",
    type=argparse.FileType("r"),
    required=True,
)
parser.add_argument(
    "-n", "--no-fetch", help="Do not fetch sources", action="store_true"
)
parser.add_argument(
    "-o", "--only-fetch", help="Only fetch sources", action="store_true"
)
parser.add_argument("-s", "--silent", help="Reduce verbosity", action="store_true")
parser.add_argument("-v", "--verbose", help="Increase verbosity", action="store_true")


def setup_logger(level: int) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    if level == logging.DEBUG:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
    root.addHandler(handler)


class Configuration:
    settings: typing.Dict[str, str]
    overrides: typing.Dict[str, str]
    ignore_keys: typing.List[str]
    packages: typing.Dict[str, typing.Dict[str, str]]
    hooks: typing.Dict[str, typing.Dict[str, str]]

    def __init__(self, tio: typing.TextIO, hooks: typing.List["Hook"]) -> None:
        logger.debug("Read configuration")
        data = configparser.ConfigParser(
            default_section="settings",
            interpolation=configparser.ExtendedInterpolation(),
        )
        data.optionxform = str  # type: ignore
        data.read_file(tio)
        settings = self.settings = dict(data["settings"].items())

        logger.debug(f"infile={self.infile}")
        logger.debug(f"out_requirements={self.out_requirements}")
        logger.debug(f"out_constraints={self.out_constraints}")

        mode = settings.get("default-install-mode", "direct")
        if mode not in ["direct", "skip"]:
            raise ValueError("default-install-mode must be one of 'direct' or 'skip'")

        raw_overrides = settings.get("version-overrides", "").strip()
        self.overrides = {}
        for line in raw_overrides.split("\n"):
            try:
                parsed = pkg_resources.Requirement.parse(line)
            except Exception:
                logger.error(f"Can not parse override: {line}")
                continue
            self.overrides[parsed.key] = line

        raw_ignores = settings.get("ignores", "").strip()
        self.ignore_keys = []
        for line in raw_ignores.split("\n"):
            line.strip()
            if line:
                self.ignore_keys.append(line)

        def is_ns_member(name):
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
            package = self.packages[name] = self._read_section(data, name)
            package.setdefault("branch", "main")
            package.setdefault("extras", "")
            package.setdefault("subdirectory", "")
            package.setdefault("target", target)
            package.setdefault("install-mode", mode)
            if not package.get("url"):
                raise ValueError(f"Section {name} has no URL set!")
            if package.get("install-mode") not in ["direct", "skip"]:
                raise ValueError(
                    f"install-mode in [{name}] must be one of 'direct' or 'skip'"
                )
            logger.debug(f"config data={self.packages[name]}")

    def _read_section(self, data, name):
        # read section without defaults.
        defaults = data.defaults()
        return dict([(k, v) for k, v in data[name].items() if k not in defaults])

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


@dataclass
class State:
    configuration: Configuration
    requirements: typing.List[str] = field(default_factory=list)
    constraints: typing.List[str] = field(default_factory=list)


class Hook:
    """Entry point for hooking into mxdev."""

    namespace: str
    """The namespace for this hook."""

    def read(self, state: State) -> None:
        """Gets executed after mxdev read operation."""

    def write(self, state: State) -> None:
        """Gets executed after mxdev write operation."""


def load_hooks() -> list:
    return [ep.load()() for ep in iter_entry_points("mxdev") if ep.name == "hook"]


def process_line(
    line: str,
    package_keys: typing.List[str],
    override_keys: typing.List[str],
    ignore_keys: typing.List[str],
    variety: str,
) -> typing.Tuple[typing.List[str], typing.List[str]]:
    if isinstance(line, bytes):
        line = line.decode("utf8")
    logger.debug(f"Process Line [{variety}]: {line.strip()}")
    if line.startswith("-c"):
        return resolve_dependencies(
            line.split(" ")[1].strip(),
            package_keys=package_keys,
            override_keys=override_keys,
            ignore_keys=ignore_keys,
            variety="c",
        )
    elif line.startswith("-r"):
        return resolve_dependencies(
            line.split(" ")[1].strip(),
            package_keys=package_keys,
            override_keys=override_keys,
            ignore_keys=ignore_keys,
            variety="r",
        )
    try:
        parsed = pkg_resources.Requirement.parse(line)
    except Exception:
        pass
    else:
        if parsed.key in package_keys:
            line = f"# {line.strip()} -> mxdev disabled (source)\n"
        if variety == "c" and parsed.key in override_keys:
            line = f"# {line.strip()} -> mxdev disabled (override)\n"
        if variety == "c" and parsed.key in ignore_keys:
            line = f"# {line.strip()} -> mxdev disabled (ignore)\n"
    if variety == "c":
        return [], [line]
    return [line], []


def process_io(
    fio: typing.IO,
    requirements: typing.List[str],
    constraints: typing.List[str],
    package_keys: typing.List[str],
    override_keys: typing.List[str],
    ignore_keys: typing.List[str],
    variety: str,
) -> None:
    for line in fio:
        new_requirements, new_constraints = process_line(
            line, package_keys, override_keys, ignore_keys, variety
        )
        requirements += new_requirements
        constraints += new_constraints


def resolve_dependencies(
    file_or_url: str,
    package_keys: typing.List[str],
    override_keys: typing.List[str],
    ignore_keys: typing.List[str],
    variety: str = "r",
) -> typing.Tuple[typing.List[str], typing.List[str]]:
    requirements: typing.List[str] = []
    constraints: typing.List[str] = []
    if not file_or_url.strip():
        logger.info("mxdev is configured to run without input requirements!")
        return ([], [])
    logger.info(f"Read [{variety}]: {file_or_url}")
    parsed = parse.urlparse(file_or_url)
    variety_verbose = "requirements" if variety == "r" else "constraints"

    if not parsed.scheme:
        requirements_in_file = Path(file_or_url)
        if requirements_in_file.exists():
            with requirements_in_file.open("r") as fio:
                process_io(
                    fio,
                    requirements,
                    constraints,
                    package_keys,
                    override_keys,
                    ignore_keys,
                    variety,
                )
        else:
            logger.info(
                f"Can not read {variety_verbose} file '{file_or_url}', it does not exist. Empty file assumed."
            )
    else:
        with request.urlopen(file_or_url) as fio:
            process_io(
                fio,
                requirements,
                constraints,
                package_keys,
                override_keys,
                ignore_keys,
                variety,
            )

    if requirements and variety == "r":
        requirements = (
            [
                "#" * 79 + "\n",
                f"# begin requirements from: {file_or_url}\n\n",
            ]
            + requirements
            + ["\n", f"# end requirements from: {file_or_url}\n", "#" * 79 + "\n"]
        )
    if constraints and variety == "c":
        constraints = (
            [
                "#" * 79 + "\n",
                f"# begin constraints from: {file_or_url}\n",
                "\n",
            ]
            + constraints
            + ["\n", f"# end constraints from: {file_or_url}\n", "#" * 79 + "\n\n"]
        )
    return (requirements, constraints)


def read(state: State, variety: str = "r") -> None:
    cfg = state.configuration
    state.requirements, state.constraints = resolve_dependencies(
        file_or_url=cfg.infile,
        package_keys=cfg.package_keys,
        override_keys=cfg.override_keys,
        ignore_keys=cfg.ignore_keys,
    )


def autocorrect_pip_url(pip_url: str) -> str:
    """So some autocorrection for pip urls, especially urls copy/pasted
    from github as e.g. git@github.com:bluedynamics/mxdev.git
    which should be git+ssh://git@github.com/bluedynamics/mxdev.git.

    If no correction necessary, return the original value.
    """
    if pip_url.startswith("git@"):
        return f"git+ssh://{pip_url.replace(':', '/')}"
    elif pip_url.startswith("ssh://"):
        return f"git+{pip_url}"
    elif pip_url.startswith("https://"):
        return f"git+{pip_url}"
    return pip_url


def fetch(state: State) -> None:
    packages = state.configuration.packages
    logger.info("#" * 79)
    if not packages:
        logger.info("# No sources configured!")
        return
    logger.info("# Fetch sources from VCS")
    for name in packages:
        logger.info(f"Fetch or update {name}")
        package = packages[name]
        repo_dir = os.path.abspath(f"{package['target']}/{name}")
        pip_url = autocorrect_pip_url(f"{package['url']}@{package['branch']}")
        logger.debug(f"pip_url={pip_url} -> repo_dir={repo_dir}")
        repo = create_project_from_pip_url(pip_url=pip_url, repo_dir=repo_dir)
        repo.update_repo()


def write_dev_sources(fio, packages: typing.Dict[str, typing.Dict[str, typing.Any]]):
    fio.write("\n" + "#" * 79 + "\n")
    fio.write("# mxdev development sources\n")
    for name in packages:
        package = packages[name]
        if package["install-mode"] == "skip":
            continue
        extras = f"[{package['extras']}]" if package["extras"] else ""
        subdir = f"/{package['subdirectory']}" if package["subdirectory"] else ""
        install_options = ' --install-option="--pre"'
        editable = (
            f"""-e ./{package['target']}/{name}{subdir}{extras}{install_options}\n"""
        )
        logger.debug(f"-> {editable.strip()}")
        fio.write(editable)
    fio.write("\n")


def write_dev_overrides(
    fio, overrides: typing.Dict[str, str], package_keys: typing.List[str]
):
    fio.write("\n" + "#" * 79 + "\n")
    fio.write("# mxdev constraint overrides\n")
    for pkg, line in overrides.items():
        if pkg in package_keys:
            fio.write(
                f"# {line} IGNORE mxdev constraint override. Source override wins!\n"
            )
        else:
            fio.write(f"{line}\n")
    fio.write("\n")


def write(state: State) -> None:
    requirements = state.requirements
    constraints = state.constraints
    cfg = state.configuration
    logger.info("#" * 79)
    logger.info("# Write outfiles")
    logger.info(f"Write [c]: {cfg.out_constraints}")
    with open(cfg.out_constraints, "w") as fio:
        fio.writelines(constraints)
        if cfg.overrides:
            write_dev_overrides(fio, cfg.overrides, cfg.package_keys)
    logger.info(f"Write [r]: {cfg.out_requirements}")
    with open(cfg.out_requirements, "w") as fio:
        fio.write("#" * 79 + "\n")
        fio.write("# mxdev combined constraints\n")
        fio.write(f"-c {cfg.out_constraints}\n\n")
        write_dev_sources(fio, cfg.packages)
        fio.writelines(requirements)


def read_hooks(state: State, hooks: typing.List[Hook]) -> None:
    for hook in hooks:
        hook.read(state)


def write_hooks(state: State, hooks: typing.List[Hook]) -> None:
    for hook in hooks:
        hook.write(state)


def main() -> None:
    args = parser.parse_args()
    loglevel = logging.INFO
    if not args.silent and args.verbose:
        loglevel = logging.INFO
    elif not args.verbose and args.silent:
        loglevel = logging.WARNING
    setup_logger(loglevel)
    logger.info("#" * 79)
    hooks = load_hooks()
    logger.info("# Load configuration")
    configuration = Configuration(tio=args.configuration, hooks=hooks)
    state = State(configuration=configuration)
    logger.info("#" * 79)
    logger.info("# Read infiles")
    read(state)
    if not args.only_fetch:
        read_hooks(state, hooks)
    if not args.no_fetch:
        fetch(state)
    if args.only_fetch:
        return
    write(state)
    write_hooks(state, hooks)
    out_requirements = state.configuration.out_requirements
    logger.info(f"🎂 You are now ready for: pip install -r {out_requirements}")
    logger.info("   (path to pip may vary dependent on your installation method)")


if __name__ == "__main__":  # pragma: no cover
    main()
