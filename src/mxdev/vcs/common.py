from ..entry_points import load_eps_by_group

import abc
import logging
import os
import platform
import queue
import re
import sys
import threading
import typing


logger = logging.getLogger("mxdev")


def print_stderr(s: str):
    sys.stderr.write(s)
    sys.stderr.write("\n")
    sys.stderr.flush()


# taken from
# http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(name_root: str, default: str | None = None) -> str:
    if platform.system() == "Windows":
        # http://www.voidspace.org.uk/python/articles/command_line.shtml#pathext
        pathext = os.environ["PATHEXT"]
        # example: ['.py', '.pyc', '.pyo', '.pyw', '.COM', '.EXE', '.BAT', '.CMD']
        names = [name_root + ext for ext in pathext.split(";")]
    else:
        names = [name_root]

    for name in names:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, name)
            if os.path.exists(exe_file) and os.access(exe_file, os.X_OK):
                return exe_file

    if default is not None:
        return default

    logger.error("Cannot find executable %s in PATH", name_root)
    sys.exit(1)


def version_sorted(inp: list, *args, **kwargs) -> list:
    """Sorts components versions, it means that numeric parts of version
    treats as numeric and string as string.

    Eg.: version-1-0-1 < version-1-0-2 < version-1-0-10
    """
    num_reg = re.compile(r"([0-9]+)")

    def int_str(val):
        try:
            return int(val)
        except ValueError:
            return val

    def split_item(item):
        return tuple(int_str(j) for j in num_reg.split(item))

    def join_item(item):
        return "".join([str(j) for j in item])

    output = [split_item(i) for i in inp]
    return [join_item(i) for i in sorted(output, *args, **kwargs)]


class WCError(Exception):
    """A working copy error."""


class BaseWorkingCopy(abc.ABC):
    def __init__(self, source: dict[str, typing.Any]):
        self._output: list[tuple[typing.Any, str]] = []
        self.output = self._output.append
        self.source = source

    def should_update(self, **kwargs) -> bool:
        offline = kwargs.get("offline", False)
        if offline:
            return False
        update = self.source.get("update", kwargs.get("update", False))
        if not isinstance(update, bool):
            if update.lower() in ("true", "yes"):
                update = True
            elif update.lower() in ("false", "no"):
                update = False
            else:
                raise ValueError(f"Unknown value for 'update': {update}")
        return update

    @abc.abstractmethod
    def checkout(self, **kwargs) -> str | None: ...

    @abc.abstractmethod
    def status(self, **kwargs) -> tuple[str, str] | str: ...

    @abc.abstractmethod
    def matches(self) -> bool: ...

    @abc.abstractmethod
    def update(self, **kwargs) -> str | None: ...


def yesno(question: str, default: bool = True, all: bool = True) -> str | bool:
    if default:
        question = f"{question} [Yes/no"
        answers: dict[str | bool, tuple] = {
            False: ("n", "no"),
            True: ("", "y", "yes"),
        }
    else:
        question = f"{question} [yes/No"
        answers = {
            False: ("", "n", "no"),
            True: ("y", "yes"),
        }
    if all:
        answers["all"] = ("a", "all")
        question = f"{question}/all] "
    else:
        question = f"{question}] "
    while 1:
        answer = input(question).lower()
        for option in answers:
            if answer in answers[option]:
                return option
        if all:
            print_stderr("You have to answer with y, yes, n, no, a or all.")
        else:
            print_stderr("You have to answer with y, yes, n or no.")


# XXX: one lock, one name
input_lock = output_lock = threading.RLock()

_workingcopytypes: dict[str, type[BaseWorkingCopy]] = {}


def get_workingcopytypes() -> dict[str, type[BaseWorkingCopy]]:
    if _workingcopytypes:
        return _workingcopytypes
    group = "mxdev.workingcopytypes"
    addons: dict[str, type[BaseWorkingCopy]] = {}
    for entrypoint in load_eps_by_group(group):
        key = entrypoint.name
        workingcopytype = entrypoint.load()
        if key in addons:
            logger.error(
                f"Duplicate workingcopy types registration '{key}' at "
                f"{entrypoint.value} can not override {addons[key]}"
            )
            sys.exit(1)
        addons[key] = workingcopytype
    _workingcopytypes.update(addons)
    return _workingcopytypes


class WorkingCopies:
    def __init__(
        self,
        sources: dict[str, dict],
        threads=5,
        smart_threading=True,
    ):
        self.sources = sources
        self.threads = threads
        self.smart_threading = smart_threading
        self.errors = False
        self.workingcopytypes = get_workingcopytypes()

    def _separate_https_packages(self, packages: list[str]) -> tuple[list[str], list[str]]:
        """Separate HTTPS packages from others for smart threading.

        HTTPS packages WITH pushurl are safe for parallel processing
        (pushurl implies the https url is read-only/public).

        Returns (https_packages, other_packages)
        """
        https_packages = []
        other_packages = []

        for name in packages:
            if name not in self.sources:
                other_packages.append(name)
                continue
            source = self.sources[name]
            url = source.get("url", "")
            has_pushurl = "pushurl" in source

            if url.startswith("https://") and not has_pushurl:
                # HTTPS without pushurl: may need credentials, process serially
                https_packages.append(name)
            else:
                # SSH, fs, or HTTPS with pushurl: safe for parallel
                other_packages.append(name)

        return https_packages, other_packages

    def process(self, the_queue: queue.Queue) -> None:
        if self.threads < 2:
            worker(self, the_queue)
            return
        threads = []

        for _ in range(self.threads):
            thread = threading.Thread(target=worker, args=(self, the_queue))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

        if self.errors:
            logger.error("There have been errors, see messages above.")
            sys.exit(1)

    def checkout(self, packages: typing.Iterable[str], **kwargs) -> None:
        # Smart threading: process HTTPS packages serially to avoid overlapping prompts
        packages_list = list(packages)
        if self.smart_threading and self.threads > 1:
            https_pkgs, other_pkgs = self._separate_https_packages(packages_list)
            if https_pkgs and other_pkgs:
                logger.info(
                    "Smart threading: processing %d HTTPS package(s) serially...",
                    len(https_pkgs),
                )
                # Save original thread count and process HTTPS packages serially
                original_threads = self.threads
                self.threads = 1
                self._checkout_impl(https_pkgs, **kwargs)
                self.threads = original_threads
                # Process remaining packages in parallel
                logger.info(
                    "Smart threading: processing %d other package(s) in parallel...",
                    len(other_pkgs),
                )
                self._checkout_impl(other_pkgs, **kwargs)
                return
            elif https_pkgs:
                logger.info(
                    "Smart threading: processing %d HTTPS package(s) serially...",
                    len(https_pkgs),
                )
                original_threads = self.threads
                self.threads = 1
                self._checkout_impl(packages_list, **kwargs)
                self.threads = original_threads
                return

        # Normal processing (smart_threading disabled or threads=1)
        self._checkout_impl(packages_list, **kwargs)

    def _checkout_impl(self, packages: list[str], **kwargs) -> None:
        """Internal implementation of checkout logic."""
        the_queue: queue.Queue = queue.Queue()
        if "update" in kwargs and not isinstance(kwargs["update"], bool):
            if kwargs["update"].lower() in ("true", "yes", "on", "force"):
                if kwargs["update"].lower() == "force":
                    kwargs["force"] = True
                kwargs["update"] = True
            elif kwargs["update"].lower() in ("false", "no", "off"):
                kwargs["update"] = False
            else:
                logger.error("Unknown value '{}' for always-checkout option.".format(kwargs["update"]))
                sys.exit(1)
        kwargs.setdefault("submodules", "always")
        # XXX: submodules is git related, move to GitWorkingCopy
        if kwargs["submodules"] not in ["always", "never", "checkout", "recursive"]:
            logger.error("Unknown value '{}' for update-git-submodules option.".format(kwargs["submodules"]))
            sys.exit(1)
        for name in packages:
            kw = kwargs.copy()
            if name not in self.sources:
                logger.error(f"Checkout failed. No source defined for '{name}'.")
                sys.exit(1)
            source = self.sources[name]
            vcs = source["vcs"]
            wc_class = self.workingcopytypes.get(vcs)
            if not wc_class:
                logger.error(f"Unregistered repository type {vcs}")
                continue
            wc = wc_class(source)
            update = wc.should_update(**kwargs)
            if not os.path.exists(source["path"]):
                pass
            elif os.path.islink(source["path"]):
                logger.info(f"Skipped update of linked '{name}'.")
                continue
            elif update and not kw.get("force", False) and wc.status() != "clean":
                print_stderr(f"The package '{name}' is dirty.")
                answer = yesno("Do you want to update it anyway?", default=False, all=True)
                if answer:
                    kw["force"] = True
                    if answer == "all":
                        kwargs["force"] = True
                else:
                    logger.info(f"Skipped update of '{name}'.")
                    continue
            logger.info("Queued '%s' for checkout.", name)
            the_queue.put_nowait((wc, wc.checkout, kw))
        self.process(the_queue)

    def matches(self, source: dict[str, str]) -> bool:
        name = source["name"]
        if name not in self.sources:
            logger.error(f"Checkout failed. No source defined for '{name}'.")
            sys.exit(1)
        source = self.sources[name]
        try:
            vcs = source["vcs"]
            wc_class = self.workingcopytypes.get(vcs)
            if not wc_class:
                logger.error(f"Unregistered repository type {vcs}")
                sys.exit(1)
            wc = wc_class(source)
            if wc is None:
                logger.error(f"Unknown repository type '{vcs}'.")
                sys.exit(1)
            return wc.matches()
        except WCError:
            logger.exception("Can not get matches!")
            sys.exit(1)

    def status(self, source: dict[str, str], **kwargs) -> str | tuple[str, str]:
        name = source["name"]
        if name not in self.sources:
            logger.error(f"Status failed. No source defined for '{name}'.")
            sys.exit(1)
        source = self.sources[name]
        try:
            vcs = source["vcs"]
            wc_class = self.workingcopytypes.get(vcs)
            if not wc_class:
                logger.error(f"Unregistered repository type {vcs}")
                sys.exit(1)
            wc = wc_class(source)
            if wc is None:
                logger.error(f"Unknown repository type '{vcs}'.")
                sys.exit(1)
            return wc.status(**kwargs)
        except WCError:
            logger.exception("Can not get status!")
            sys.exit(1)

    def update(self, packages: typing.Iterable[str], **kwargs) -> None:
        # Check for offline mode early - skip all updates if offline
        offline = kwargs.get("offline", False)
        if offline:
            logger.info("Skipped updates (offline mode)")
            return

        # Smart threading: process HTTPS packages serially to avoid overlapping prompts
        packages_list = list(packages)
        if self.smart_threading and self.threads > 1:
            https_pkgs, other_pkgs = self._separate_https_packages(packages_list)
            if https_pkgs and other_pkgs:
                logger.info(
                    "Smart threading: updating %d HTTPS package(s) serially...",
                    len(https_pkgs),
                )
                # Save original thread count and process HTTPS packages serially
                original_threads = self.threads
                self.threads = 1
                self._update_impl(https_pkgs, **kwargs)
                self.threads = original_threads
                # Process remaining packages in parallel
                logger.info(
                    "Smart threading: updating %d other package(s) in parallel...",
                    len(other_pkgs),
                )
                self._update_impl(other_pkgs, **kwargs)
                return
            elif https_pkgs:
                logger.info(
                    "Smart threading: updating %d HTTPS package(s) serially...",
                    len(https_pkgs),
                )
                original_threads = self.threads
                self.threads = 1
                self._update_impl(packages_list, **kwargs)
                self.threads = original_threads
                return

        # Normal processing (smart_threading disabled or threads=1)
        self._update_impl(packages_list, **kwargs)

    def _update_impl(self, packages: list[str], **kwargs) -> None:
        """Internal implementation of update logic."""
        the_queue: queue.Queue = queue.Queue()
        for name in packages:
            kw = kwargs.copy()
            if name not in self.sources:
                continue
            source = self.sources[name]
            vcs = source["vcs"]
            wc_class = self.workingcopytypes.get(vcs)
            if not wc_class:
                logger.error(f"Unregistered repository type {vcs}")
                sys.exit(1)
            wc = wc_class(source)
            if wc.status() != "clean" and not kw.get("force", False):
                print_stderr(f"The package '{name}' is dirty.")
                answer = yesno("Do you want to update it anyway?", default=False, all=True)
                if answer:
                    kw["force"] = True
                    if answer == "all":
                        kwargs["force"] = True
                else:
                    logger.info(f"Skipped update of '{name}'.")
                    continue
            logger.info("Queued '%s' for update.", name)
            the_queue.put_nowait((wc, wc.update, kw))
        self.process(the_queue)


def worker(working_copies: WorkingCopies, the_queue: queue.Queue) -> None:
    while True:
        if working_copies.errors:
            return
        try:
            wc, action, kwargs = the_queue.get_nowait()
        except queue.Empty:
            return
        try:
            output = action(**kwargs)
        except WCError:
            with output_lock:
                for lvl, msg in wc._output:
                    lvl(msg)
                logger.exception("Can not execute action!")
                working_copies.errors = True
        else:
            with output_lock:
                for lvl, msg in wc._output:
                    lvl(msg)
                if kwargs.get("verbose", False) and output is not None and output.strip():
                    if isinstance(output, bytes):
                        output = output.decode("utf8")
                    print(output)
