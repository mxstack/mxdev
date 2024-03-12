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
def which(name_root: str, default: typing.Union[str, None] = None) -> str:
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


def version_sorted(inp: typing.List, *args, **kwargs) -> typing.List:
    """
    Sorts components versions, it means that numeric parts of version
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
    def __init__(self, source: typing.Dict[str, typing.Any]):
        self._output: typing.List[typing.Tuple[typing.Any, str]] = []
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
                raise ValueError("Unknown value for 'update': %s" % update)
        return update

    @abc.abstractmethod
    def checkout(self, **kwargs) -> typing.Union[str, None]: ...

    @abc.abstractmethod
    def status(self, **kwargs) -> typing.Union[typing.Tuple[str, str], str]: ...

    @abc.abstractmethod
    def matches(self) -> bool: ...

    @abc.abstractmethod
    def update(self, **kwargs) -> typing.Union[str, None]: ...


def yesno(
    question: str, default: bool = True, all: bool = True
) -> typing.Union[str, bool]:
    if default:
        question = "%s [Yes/no" % question
        answers: typing.Dict[typing.Union[str, bool], typing.Tuple] = {
            False: ("n", "no"),
            True: ("", "y", "yes"),
        }
    else:
        question = "%s [yes/No" % question
        answers = {
            False: ("", "n", "no"),
            True: ("y", "yes"),
        }
    if all:
        answers["all"] = ("a", "all")
        question = "%s/all] " % question
    else:
        question = "%s] " % question
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

_workingcopytypes: typing.Dict[str, typing.Type[BaseWorkingCopy]] = {}


def get_workingcopytypes() -> typing.Dict[str, typing.Type[BaseWorkingCopy]]:
    if _workingcopytypes:
        return _workingcopytypes
    group = "mxdev.workingcopytypes"
    addons: dict[str, typing.Type[BaseWorkingCopy]] = {}
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
    def __init__(self, sources: typing.Dict[str, typing.Dict], threads=5):
        self.sources = sources
        self.threads = threads
        self.errors = False
        self.workingcopytypes = get_workingcopytypes()

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
        the_queue: queue.Queue = queue.Queue()
        if "update" in kwargs and not isinstance(kwargs["update"], bool):
            if kwargs["update"].lower() in ("true", "yes", "on", "force"):
                if kwargs["update"].lower() == "force":
                    kwargs["force"] = True
                kwargs["update"] = True
            elif kwargs["update"].lower() in ("false", "no", "off"):
                kwargs["update"] = False
            else:
                logger.error(
                    "Unknown value '%s' for always-checkout option." % kwargs["update"]
                )
                sys.exit(1)
        kwargs.setdefault("submodules", "always")
        # XXX: submodules is git related, move to GitWorkingCopy
        if kwargs["submodules"] not in ["always", "never", "checkout", "recursive"]:
            logger.error(
                "Unknown value '%s' for update-git-submodules option."
                % kwargs["submodules"]
            )
            sys.exit(1)
        for name in packages:
            kw = kwargs.copy()
            if name not in self.sources:
                logger.error("Checkout failed. No source defined for '%s'." % name)
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
                answer = yesno(
                    "Do you want to update it anyway?", default=False, all=True
                )
                if answer:
                    kw["force"] = True
                    if answer == "all":
                        kwargs["force"] = True
                else:
                    logger.info("Skipped update of '%s'." % name)
                    continue
            logger.info("Queued '%s' for checkout.", name)
            the_queue.put_nowait((wc, wc.checkout, kw))
        self.process(the_queue)

    def matches(self, source: typing.Dict[str, str]) -> bool:
        name = source["name"]
        if name not in self.sources:
            logger.error("Checkout failed. No source defined for '%s'." % name)
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

    def status(
        self, source: typing.Dict[str, str], **kwargs
    ) -> typing.Union[str, typing.Tuple[str, str]]:
        name = source["name"]
        if name not in self.sources:
            logger.error("Status failed. No source defined for '%s'." % name)
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
                logger.error("Unknown repository type '%s'." % vcs)
                sys.exit(1)
            return wc.status(**kwargs)
        except WCError:
            logger.exception("Can not get status!")
            sys.exit(1)

    def update(self, packages: typing.Iterable[str], **kwargs) -> None:
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
                print_stderr("The package '%s' is dirty." % name)
                answer = yesno(
                    "Do you want to update it anyway?", default=False, all=True
                )
                if answer:
                    kw["force"] = True
                    if answer == "all":
                        kwargs["force"] = True
                else:
                    logger.info("Skipped update of '%s'." % name)
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
                if (
                    kwargs.get("verbose", False)
                    and output is not None
                    and output.strip()
                ):
                    if isinstance(output, bytes):
                        output = output.decode("utf8")
                    print(output)
