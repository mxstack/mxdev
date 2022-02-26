from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from pkg_resources import iter_entry_points
from libvcs.shortcuts import create_repo_from_pip_url
from urllib import parse
from urllib import request

import argparse
import configparser
import logging
import os
import pkg_resources
import sys
import typing


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
parser.add_argument("-n", "--no-fetch", help="Do not fetch sources", action="store_true")
parser.add_argument("-s", "--silent", help="Reduce verbosity", action="store_true")
parser.add_argument("-v", "--verbose", help="Increase verbosity", action="store_true")


def setup_logger(level):
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
    def __init__(self, tio: typing.TextIO) -> None:
        logger.debug("Read configuration")
        ini = configparser.ConfigParser(
            default_section="settings",
            interpolation=configparser.ExtendedInterpolation(),
        )
        ini.read_file(tio)
        self.infile: str = ini["settings"].get("requirements-in", "requirements.txt")
        logger.debug(f"infile={self.infile}")
        self.out_requirements: str = ini["settings"].get(
            "requirements-out", "requirements-mxdev.txt"
        )
        logger.debug(f"out_requirements={self.out_requirements}")
        self.out_constraints: str = ini["settings"].get(
            "constraints-out", "constraints-mxdev.txt"
        )
        logger.debug(f"out_constraints={self.out_constraints}")
        target: str = ini["settings"].get("default-target", "sources")
        mode: str = ini["settings"].get("default-install-mode", "direct")
        if mode not in ["direct", "skip"]:
            raise ValueError("default-install-mode must be one of 'direct' or 'skip'")
        raw_overrides = ini["settings"].get("version-overrides", "").strip()
        self.overrides: typing.Dict[str, str] = {}
        for line in raw_overrides.split("\n"):
            try:
                parsed = pkg_resources.Requirement.parse(line)
            except Exception:
                logger.error(f"Can not parse override: {line}")
                continue
            self.overrides[parsed.key] = line
        raw_ignores = ini["settings"].get("ignores", "").strip()
        self.ignore_keys: typing.List[str] = []
        for line in raw_ignores.split("\n"):
            line.strip()
            if line:
                self.ignore_keys.append(line)

        self.packages: typing.Dict[str, typing.Dict[str, str]] = {}
        for name in ini.sections():
            section = ini[name]
            logger.debug(f"config section={name}")
            url = section.get("url")
            if not url:
                raise ValueError(f"Section {name} has no URL set!")
            pmode = section.get("install-mode", mode)
            if pmode not in ["direct", "skip"]:
                raise ValueError(
                    f"install-mode in [{name}] must be one of 'direct' or 'skip'"
                )
            self.packages[name] = {
                "url": url,
                "branch": section.get("branch", "main"),
                "extras": section.get("extras", ""),
                "subdir": section.get("subdirectory", ""),
                "target": section.get("target", target),
                "mode": pmode,
            }
            logger.debug(f"config data={self.packages[name]}")

    @property
    def package_keys(self) -> typing.List[str]:
        return [k.lower() for k in self.packages]

    @property
    def override_keys(self) -> typing.List[str]:
        return [k.lower() for k in self.overrides]


@dataclass
class State:
    configuration: Configuration
    requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    annotations: dict = field(default_factory=dict)


class Hook:
    """Entry point for hooking into mxdev."""

    order = 0

    def read(state: State) -> None:
        """Gets executed after mxdev read operation."""

    def write(state: State) -> None:
        """Gets executed after mxdev write operation."""


def load_hooks() -> list:
    return sorted(
        [ep.load() for ep in iter_entry_points('mxdev') if ep.name == 'hook'],
        key=lambda x: x.order
    )


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
        return read(
            line.split(" ")[1].strip(),
            package_keys=package_keys,
            override_keys=override_keys,
            ignore_keys=ignore_keys,
            variety="c",
        )
    elif line.startswith("-r"):
        return read(
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


def read(state: State, variety: str = "r") -> None:
    cfg = state.configuration
    file_or_url = cfg.infile
    package_keys = cfg.package_keys
    override_keys = cfg.override_keys
    ignore_keys = cfg.ignore_keys
    requirements = state.requirements
    constraints = state.constraints
    if not file_or_url.strip():
        logger.info("mxdev is configured to run without input requirements!")
        return
    logger.info(f"Read [{variety}]: {file_or_url}")
    parsed = parse.urlparse(file_or_url)
    variety_verbose = "requirements" if variety == "r" else "constraints"

    if not parsed.scheme:
        requirements_in_file = Path(file_or_url)
        if not requirements_in_file.exists():
            logger.error(
                f"Can not read {variety_verbose} file '{file_or_url}', it does not exist."
            )
            exit(1)
        if not requirements_in_file.is_file():
            logger.error(
                f"Can not read {variety_verbose} file '{file_or_url}', it is not a file."
            )
            exit(1)
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
        package: dict = packages[name]
        repo_dir: str = os.path.abspath(f"{package['target']}/{name}")
        pip_url: str = autocorrect_pip_url(f"{package['url']}@{package['branch']}")
        logger.debug(f"pip_url={pip_url} -> repo_dir={repo_dir}")
        repo = create_repo_from_pip_url(pip_url=pip_url, repo_dir=repo_dir)
        repo.update_repo()


def write_dev_sources(fio, packages: typing.Dict[str, typing.Dict[str, typing.Any]]):
    fio.write("\n" + "#" * 79 + "\n")
    fio.write("# mxdev development sources\n")
    for name in packages:
        package = packages[name]
        if package["mode"] == "skip":
            continue
        extras = f"[{package['extras']}]" if package["extras"] else ""
        subdir = f"/{package['subdir']}" if package["subdir"] else ""
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


def main() -> None:
    args = parser.parse_args()
    loglevel = logging.INFO
    if not args.silent and args.verbose:
        loglevel = logging.INFO
    elif not args.verbose and args.silent:
        loglevel = logging.WARNING
    setup_logger(loglevel)
    logger.info("#" * 79)
    logger.info("# Read infiles")
    state = State(configuration=Configuration(args.configuration))
    hooks = load_hooks()
    read(state)
    for hook in hooks:
        hook.read(state)
    if not args.no_fetch:
        fetch(state)
    write(state)
    for hook in hooks:
        hook.write(state)
    out_requirements = state.configuration.out_requirements
    logger.info(f"🎂 You are now ready for: pip install -r {out_requirements}")
    logger.info("   (path to pip may vary dependent on your installation method)")


if __name__ == "__main__":  # pragma: no cover
    main()
