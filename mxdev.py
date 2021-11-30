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

# TEMPORARY LIBVCS PATCHES

# 1) until https://github.com/vcs-python/libvcs/issues/293 is fixed

from libvcs.base import BaseRepo

_old_libvcs_base_init = BaseRepo.__init__

def _new_libvcs_base_init(self, *args, **kwargs):
    _old_libvcs_base_init(self, *args, **kwargs)
    if "rev" in kwargs:
        self.rev = kwargs["rev"]

BaseRepo.__init__ = _new_libvcs_base_init

# 2) until https://github.com/vcs-python/libvcs/issues/295 is fixed

from libvcs import exc
import re

def _new_libvcs_update_repo(self):
    self.ensure_dir()

    if not os.path.isdir(os.path.join(self.path, '.git')):
        self.obtain()
        self.update_repo()
        return

    # Get requested revision or tag
    url, git_tag = self.url, getattr(self, 'rev', None)

    if not git_tag:
        self.debug("No git revision set, defaulting to origin/master")
        symref = self.run(['symbolic-ref', '--short', 'HEAD'])
        if symref:
            git_tag = symref.rstrip()
        else:
            git_tag = 'origin/master'
    self.debug("git_tag: %s" % git_tag)

    self.info("Updating to '%s'." % git_tag)

    # Get head sha
    try:
        head_sha = self.run(['rev-list', '--max-count=1', 'HEAD'])
    except exc.CommandError:
        self.error("Failed to get the hash for HEAD")
        return

    self.debug("head_sha: %s" % head_sha)

    # If a remote ref is asked for, which can possibly move around,
    # we must always do a fetch and checkout.
    show_ref_output = self.run(['show-ref', git_tag], check_returncode=False)
    self.debug("show_ref_output: %s" % show_ref_output)
    is_remote_ref = "remotes" in show_ref_output
    self.debug("is_remote_ref: %s" % is_remote_ref)

    # show-ref output is in the form "<sha> refs/remotes/<remote>/<tag>"
    # we must strip the remote from the tag.
    git_remote_name = self.get_current_remote_name()

    if "refs/remotes/%s" % git_tag in show_ref_output:
        m = re.match(
            r'^[0-9a-f]{40} refs/remotes/'
            r'(?P<git_remote_name>[^/]+)/'
            r'(?P<git_tag>.+)$',
            show_ref_output,
            re.MULTILINE,
        )
        git_remote_name = m.group('git_remote_name')
        git_tag = m.group('git_tag')
    self.debug("git_remote_name: %s" % git_remote_name)
    self.debug("git_tag: %s" % git_tag)

    # This will fail if the tag does not exist (it probably has not
    # been fetched yet).
    try:
        error_code = 0
        tag_sha = self.run(
            [
                'rev-list',
                '--max-count=1',
                git_remote_name + '/' + git_tag if is_remote_ref else git_tag,
            ]
        )
    except exc.CommandError as e:
        error_code = e.returncode
        tag_sha = ""
    self.debug("tag_sha: %s" % tag_sha)
    # Is the hash checkout out what we want?
    somethings_up = (error_code, is_remote_ref, tag_sha != head_sha)
    if all(not x for x in somethings_up):
        self.info("Already up-to-date.")
        return

    try:
        process = self.run(['fetch'], log_in_real_time=True)
    except exc.CommandError:
        self.error("Failed to fetch repository '%s'" % url)
        return

    if is_remote_ref:
        # Check if stash is needed
        try:
            process = self.run(['status', '--porcelain'])
        except exc.CommandError:
            self.error("Failed to get the status")
            return
        need_stash = len(process) > 0

        # If not in clean state, stash changes in order to be able
        # to be able to perform git pull --rebase
        if need_stash:
            # If Git < 1.7.6, uses --quiet --all
            git_stash_save_options = '--quiet'
            try:
                process = self.run(['stash', 'save', git_stash_save_options])
            except exc.CommandError:
                self.error("Failed to stash changes")

        # checkout remote branch
        try:
            process = self.run(['checkout', git_tag])
        except exc.CommandError:
            self.error("Failed to checkout tag: '%s'" % git_tag)
            return

        # Pull changes from the remote branch
        try:
            process = self.run(['rebase', git_remote_name + '/' + git_tag])
        except exc.CommandError as e:
            if 'invalid_upstream' in str(e):
                self.error(e)
            else:
                # Rebase failed: Restore previous state.
                self.run(['rebase', '--abort'])
                if need_stash:
                    self.run(['stash', 'pop', '--index', '--quiet'])

                self.error(
                    "\nFailed to rebase in: '%s'.\n"
                    "You will have to resolve the conflicts manually" % self.path
                )
                return

        if need_stash:
            try:
                process = self.run(['stash', 'pop', '--index', '--quiet'])
            except exc.CommandError:
                # Stash pop --index failed: Try again dropping the index
                self.run(['reset', '--hard', '--quiet'])
                try:
                    process = self.run(['stash', 'pop', '--quiet'])
                except exc.CommandError:
                    # Stash pop failed: Restore previous state.
                    self.run(['reset', '--hard', '--quiet', head_sha])
                    self.run(['stash', 'pop', '--index', '--quiet'])
                    self.error(
                        "\nFailed to rebase in: '%s'.\n"
                        "You will have to resolve the "
                        "conflicts manually" % self.path
                    )
                    return

    else:
        try:
            process = self.run(['checkout', git_tag])
        except exc.CommandError:
            self.error("Failed to checkout tag: '%s'" % git_tag)
            return

    cmd = ['submodule', 'update', '--recursive', '--init']
    self.run(cmd, log_in_real_time=True)

from libvcs.git import GitRepo

GitRepo.update_repo = _new_libvcs_update_repo

# END OF PATCH


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
            "requirements-out", "requirements-dev.txt"
        )
        logger.debug(f"out_requirements={self.out_requirements}")
        self.out_constraints: str = ini["settings"].get(
            "constraints-out", "constraints-dev.txt"
        )
        logger.debug(f"out_constraints={self.out_constraints}")
        target: str = ini["settings"].get("default-target", "sources")
        position: str = ini["settings"].get("default-position", "before")
        self.packages = {}
        for name in ini.sections():
            logger.debug(f"config section={name}")
            url = ini[name].get("url")
            if not url:
                raise ValueError(f"Section {name} has no URL set!")
            self.packages[name] = {
                "url": url,
                "branch": ini[name].get("branch", "main"),
                "extras": ini[name].get("extras", ""),
                "subdir": ini[name].get("subdirectory", ""),
                "target": ini[name].get("target", target),
                "position": ini[name].get("position", position),
            }
            logger.debug(f"config data={self.packages[name]}")

    @property
    def keys(self) -> typing.List[str]:
        return [k.lower() for k in self.packages]


def process_line(
    line: str, package_keys: typing.List[str], variety: str
) -> typing.Tuple[typing.List[str], typing.List[str]]:
    if isinstance(line, bytes):
        line = line.decode("utf8")
    logger.debug(f"Process Line [{variety}]: {line.strip()}")
    if line.startswith("-c"):
        return read(line.split(" ")[1].strip(), package_keys=package_keys, variety="c")
    elif line.startswith("-r"):
        return read(line.split(" ")[1].strip(), package_keys=package_keys, variety="r")
    try:
        parsed = pkg_resources.Requirement.parse(line)
    except Exception:
        pass
    else:
        if parsed.key in package_keys:
            line = f"# mxdev disabled: {line}"
    if variety == "c":
        return [], [line]
    return [line], []


def process_io(
    fio: typing.IO,
    requirements: typing.List[str],
    constraints: typing.List[str],
    package_keys: typing.List[str],
    variety: str,
) -> None:
    for line in fio:
        new_requirements, new_constraints = process_line(line, package_keys, variety)
        requirements += new_requirements
        constraints += new_constraints


def read(
    file_or_url: str,
    package_keys: typing.List[str],
    variety: str = "r",
) -> typing.Tuple[typing.List[str], typing.List[str]]:

    requirements: typing.List[str] = []
    constraints: typing.List[str] = []
    logger.info(f"Read [{variety}]: {file_or_url}")
    parsed = parse.urlparse(file_or_url)

    if not parsed.scheme:
        with open(file_or_url, "r") as fio:
            process_io(fio, requirements, constraints, package_keys, variety)
    else:
        with request.urlopen(file_or_url) as fio:
            process_io(fio, requirements, constraints, package_keys, variety)

    if requirements and variety == "r":
        requirements = (
            [
                "#" * 79 + "\n",
                f"# begin requirements from: {file_or_url}\n\n",
            ]
            + requirements
            + ["", f"# end requirements from: {file_or_url}\n", "#" * 79 + "\n"]
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


def fetch(packages) -> None:
    logger.info("#" * 79)
    logger.info("# Fetch sources from VCS")

    for name in packages:
        logger.info(f"Fetch or update {name}")
        package: dict = packages[name]
        repo_dir: str = os.path.abspath(f"{package['target']}/{name}")
        pip_url: str = f"{package['url']}@{package['branch']}"
        logger.debug(f"pip_url={pip_url} -> repo_dir={repo_dir}")
        repo = create_repo_from_pip_url(pip_url=pip_url, repo_dir=repo_dir)
        repo.update_repo()

def write_dev_sources(fio, packages, position):
    fio.write("\n" + "#" * 79 + "\n")
    fio.write(f"# mxdev development sources {position}:\n\n")
    for name in packages:
        package = packages[name]
        if package["position"] != position:
            continue
        extras = f"[{package['extras']}]" if package["extras"] else ""
        subdir = f"/{package['subdir']}" if package["subdir"] else ""
        editable = f"""-e ./{package['target']}/{name}{subdir}{extras}\n"""
        logger.debug(f"-> {editable.strip()}")
        fio.write(editable)
    fio.write("\n")


def write(
    requirements: typing.List[str],
    requirements_filename: str,
    constraints: typing.List[str],
    constraints_filename: str,
    packages,
):
    logger.info("#" * 79)
    logger.info("# Write outfiles")
    logger.info(f"write {requirements_filename}")
    with open(requirements_filename, "w") as fio:
        fio.write("#" * 79 + "\n")
        fio.write("# mxdev combined constraints\n")
        fio.write(f"-c {constraints_filename}\n\n")
        write_dev_sources(fio, packages, "before")
        fio.writelines(requirements)
        write_dev_sources(fio, packages, "after")

    logger.info(f"write {constraints_filename}")
    with open(constraints_filename, "w") as fio:
        fio.writelines(constraints)


def main() -> None:
    args = parser.parse_args()
    setup_logger(logging.DEBUG if args.verbose else logging.INFO)
    cfg = Configuration(args.configuration)
    logger.info("#" * 79)
    logger.info("# Read infiles")
    requirements, constraints = read(cfg.infile, cfg.keys)
    fetch(cfg.packages)
    write(
        requirements,
        cfg.out_requirements,
        constraints,
        cfg.out_constraints,
        cfg.packages,
    )
    logger.info("🎂 Ready for pip! 🎂")


if __name__ == "__main__":  # pragma: no cover
    main()
