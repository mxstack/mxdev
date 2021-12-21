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
parser.add_argument("-v", "--verbose", help="Increase verbosity", action="store_true")
parser.add_argument("-s", "--silent", help="Reduce verbosity", action="store_true")


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
        mode: str = ini["settings"].get("default-install-mode", "interdependency")
        if mode not in ["direct", "interdependency", "skip"]:
            raise ValueError(
                "default-install-mode must be one of 'direct', 'interdependency' or 'skip'"
            )
        raw_overrides = ini["settings"].get("version-overrides", "").strip()
        self.overrides: typing.Dict[str, str] = {}
        for line in raw_overrides.split("\n"):
            try:
                parsed = pkg_resources.Requirement.parse(line)
            except Exception:
                logger.error(f"Can not parse override: {line}")
                continue
            self.overrides[parsed.key] = line

        self.packages: typing.Dict[str, typing.Dict[str, str]] = {}
        for name in ini.sections():
            section = ini[name]
            logger.debug(f"config section={name}")
            url = section.get("url")
            if not url:
                raise ValueError(f"Section {name} has no URL set!")
            pmode = section.get("install-mode", mode)
            if pmode not in ["direct", "interdependency", "skip"]:
                raise ValueError(
                    "install-mode in [{name}] must be one of 'direct', 'interdependency' or 'skip'"
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


def process_line(
    line: str,
    package_keys: typing.List[str],
    override_keys: typing.List[str],
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
            variety="c",
        )
    elif line.startswith("-r"):
        return read(
            line.split(" ")[1].strip(),
            package_keys=package_keys,
            override_keys=override_keys,
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
    if variety == "c":
        return [], [line]
    return [line], []


def process_io(
    fio: typing.IO,
    requirements: typing.List[str],
    constraints: typing.List[str],
    package_keys: typing.List[str],
    override_keys: typing.List[str],
    variety: str,
) -> None:
    for line in fio:
        new_requirements, new_constraints = process_line(
            line, package_keys, override_keys, variety
        )
        requirements += new_requirements
        constraints += new_constraints


def read(
    file_or_url: str,
    package_keys: typing.List[str],
    override_keys: typing.List[str],
    variety: str = "r",
) -> typing.Tuple[typing.List[str], typing.List[str]]:

    requirements: typing.List[str] = []
    constraints: typing.List[str] = []
    logger.info(f"Read [{variety}]: {file_or_url}")
    parsed = parse.urlparse(file_or_url)

    if not parsed.scheme:
        with open(file_or_url, "r") as fio:
            process_io(
                fio, requirements, constraints, package_keys, override_keys, variety
            )
    else:
        with request.urlopen(file_or_url) as fio:
            process_io(
                fio, requirements, constraints, package_keys, override_keys, variety
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


def autocorrect_pip_url(pip_url: str) -> str:
    """
    do some autocorrection for pip urls, especially urls copy/pasted
    from github as e.g. git@github.com:bluedynamics/mxdev.git
    which should be git+ssh://git@github.com/bluedynamics/mxdev.git

    when no correction necessary, return the original
    """
    if pip_url.startswith("git@"):
        return f"git+ssh://{pip_url.replace(':', '/')}"
    elif pip_url.startswith("ssh://"):
        return f"git+{pip_url}"
    elif pip_url.startswith("https://"):
        return f"git+{pip_url}"

    return pip_url


def fetch(packages) -> None:
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


def write_dev_sources(fio, packages, nodeps: bool):
    fio.write("\n" + "#" * 79 + "\n")
    fio.write("# mxdev development sources\n")
    if nodeps:
        fio.write("# install without dependencies (interdependency mode)\n\n")
    else:
        fio.write("# install with dependencies\n\n")
    for name in packages:
        package = packages[name]
        if package["mode"] == "skip" or (nodeps and package["mode"] == "direct"):
            continue
        extras = f"[{package['extras']}]" if package["extras"] else ""
        subdir = f"/{package['subdir']}" if package["subdir"] else ""
        install_options = (
            ' --install-option="--no-deps"'
            if nodeps and package["mode"] == "interdependency"
            else ' --install-option="--pre"'
        )
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


def write(
    requirements: typing.List[str],
    constraints: typing.List[str],
    cfg: Configuration,
):
    logger.info("#" * 79)
    logger.info("# Write outfiles")
    logger.info(f"Write [r]: {cfg.out_requirements}")
    with open(cfg.out_requirements, "w") as fio:
        fio.write("#" * 79 + "\n")
        fio.write("# mxdev combined constraints\n")
        fio.write(f"-c {cfg.out_constraints}\n\n")
        write_dev_sources(fio, cfg.packages, True)
        write_dev_sources(fio, cfg.packages, False)
        fio.writelines(requirements)

    logger.info(f"Write [c]: {cfg.out_constraints}")
    with open(cfg.out_constraints, "w") as fio:
        fio.writelines(constraints)
        if cfg.overrides:
            write_dev_overrides(fio, cfg.overrides, cfg.package_keys)


def main() -> None:
    args = parser.parse_args()
    loglevel = logging.INFO
    if not args.silent and args.verbose:
        loglevel = logging.INFO
    elif not args.verbose and args.silent:
        loglevel = logging.WARNING
    setup_logger(loglevel)
    cfg = Configuration(args.configuration)
    logger.info("#" * 79)
    logger.info("# Read infiles")
    requirements, constraints = read(cfg.infile, cfg.package_keys, cfg.override_keys)
    fetch(cfg.packages)
    write(requirements, constraints, cfg)
    logger.info("🎂 Ready for pip! 🎂")


if __name__ == "__main__":  # pragma: no cover
    main()
