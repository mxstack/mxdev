from mxdev.vcs.common import WorkingCopies
from subprocess import PIPE
from subprocess import Popen
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Union

import os
import sys
import threading


def tee(process, filter_func):
    """Read lines from process.stdout and echo them to sys.stdout.

    Returns a list of lines read. Lines are not newline terminated.

    The 'filter_func' is a callable which is invoked for every line,
    receiving the line as argument. If the filter_func returns True, the
    line is echoed to sys.stdout.
    """
    # We simply use readline here, more fancy IPC is not warranted
    # in the context of this package.
    lines = []
    while True:
        line = process.stdout.readline()
        if line:
            stripped_line = line.rstrip()
            if filter_func(stripped_line):
                sys.stdout.write(line.decode("utf8"))
            lines.append(stripped_line)
        elif process.poll() is not None:
            break
    return lines


def tee2(process, filter_func):
    """Read lines from process.stderr and echo them to sys.stderr.

    The 'filter_func' is a callable which is invoked for every line,
    receiving the line as argument. If the filter_func returns True, the
    line is echoed to sys.stderr.
    """
    while True:
        line = process.stderr.readline()
        if line:
            stripped_line = line.rstrip()
            if filter_func(stripped_line):
                sys.stderr.write(line.decode("utf8"))
        elif process.poll() is not None:
            break


class background_thread:
    """Context manager to start and stop a background thread."""

    def __init__(self, target, args):
        self.target = target
        self.args = args

    def __enter__(self):
        self._t = threading.Thread(target=self.target, args=self.args)
        self._t.start()
        return self._t

    def __exit__(self, *ignored):
        self._t.join()


def popen(cmd, echo=True, echo2=True, env=None, cwd=None):
    """Run 'cmd' and return a two-tuple of exit code and lines read.

    If 'echo' is True, the stdout stream is echoed to sys.stdout.
    If 'echo2' is True, the stderr stream is echoed to sys.stderr.

    The 'echo' and 'echo2' arguments may also be callables, in which
    case they are used as tee filters.

    The 'env' argument allows to pass a dict replacing os.environ.

    if 'cwd' is not None, current directory will be changed to cwd before execution.
    """
    if not callable(echo):
        if echo:
            echo = On()
        else:
            echo = Off()

    if not callable(echo2):
        if echo2:
            echo2 = On()
        else:
            echo2 = Off()

    process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, env=env, cwd=cwd)

    bt = background_thread(tee2, (process, echo2))
    bt.__enter__()
    try:
        lines = tee(process, echo)
    finally:
        bt.__exit__(None, None, None)
    return process.returncode, lines


class On:
    """A tee filter printing all lines."""

    def __call__(self, line):
        return True


class Off:
    """A tee filter suppressing all lines."""

    def __call__(self, line):
        return False


class Process:
    """Process related functions using the tee module."""

    def __init__(self, quiet: bool = False, env=None, cwd: Union[str, None] = None):
        self.quiet = quiet
        self.env = env
        self.cwd = cwd

    def popen(self, cmd, echo=True, echo2=True, cwd=None):
        # env *replaces* os.environ
        if self.quiet:
            echo = echo2 = False
        return popen(cmd, echo, echo2, env=self.env, cwd=self.cwd or cwd)

    def check_call(self, cmd, **kw):
        rc, lines = self.popen(cmd, **kw)
        assert rc == 0
        return lines


class GitRepo:
    def __init__(self, base: str):
        self.base = base
        self.url = f"file:///{base}"
        self.process = Process(cwd=base)

    def __call__(self, cmd, **kw):
        return self.process.check_call(cmd, **kw)

    def init(self):
        os.mkdir(self.base)
        self("git init -b master")

    def setup_user(self):
        self('git config user.email "florian.schulze@gmx.net"')
        self('git config user.name "Florian Schulze"')

    def add_file(self, fname, msg=None):
        repo_file = self.base / fname
        with open(repo_file, "w") as fio:
            fio.write(fname)
        self("git add %s" % repo_file, echo=False)
        if msg is None:
            msg = fname
        self(f"git commit {repo_file} -m {msg}", echo=False)

    def add_submodule(self, submodule: "GitRepo", submodule_name: str):
        assert isinstance(submodule, GitRepo)
        assert isinstance(submodule_name, str)

        self(f"git submodule add {submodule.url}")
        self("git add .gitmodules")
        self(f"git add {submodule_name}")
        self(f"git commit -m 'Add submodule {submodule_name}'")

    def add_branch(self, bname: str, msg: Union[str, None] = None):
        self(f"git checkout -b {bname}")


def vcs_checkout(
    sources: Dict[str, Any],
    packages: Iterable[str],
    verbose,
    update_git_submodules: str = "always",
    always_accept_server_certificate: bool = True,
    **kw,
):
    workingcopies = WorkingCopies(sources=sources, threads=1)
    workingcopies.checkout(
        sorted(packages),
        verbose=verbose,
        submodules=update_git_submodules,
        always_accept_server_certificate=always_accept_server_certificate,
        **kw,
    )


def vcs_update(
    sources: Dict[str, Any],
    packages: Iterable[str],
    verbose,
    update_git_submodules: str = "always",
    always_accept_server_certificate: bool = True,
    **kw,
):
    workingcopies = WorkingCopies(sources=sources, threads=1)
    workingcopies.update(
        sorted(packages),
        verbose=verbose,
        submodules=update_git_submodules,
        always_accept_server_certificate=always_accept_server_certificate,
        **kw,
    )


def vcs_status(sources: Dict[str, Any], verbose=False):
    workingcopies = WorkingCopies(sources=sources, threads=1)
    res = {}
    for k in sources:
        res[k] = workingcopies.status(sources[k], verbose=verbose)

    return res
