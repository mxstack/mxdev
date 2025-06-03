from . import common

import functools
import os
import re
import subprocess
import sys
import typing


logger = common.logger
GIT_CLONE_DEPTH = os.getenv("GIT_CLONE_DEPTH")


class GitError(common.WCError):
    pass


class GitWorkingCopy(common.BaseWorkingCopy):
    """The git working copy.

    Now supports git 1.5 and 1.6+ in a single codebase.
    """

    # TODO: make this configurable? It might not make sense however, as we
    # should make master and a lot of other conventional stuff configurable
    _upstream_name = "origin"

    def __init__(self, source: typing.Dict[str, str]):
        self.git_executable = common.which("git")
        if "rev" in source and "revision" in source:
            raise ValueError(
                "The source definition of '%s' contains "
                "duplicate revision options." % source["name"]
            )
        # 'rev' is canonical
        if "revision" in source:
            source["rev"] = source["revision"]
            del source["revision"]
        if "rev" in source:
            # drop default value for branch if rev is specified
            if source.get("branch") == "main":
                del source["branch"]
            elif "branch" in source:
                logger.error(
                    "Cannot specify both branch (%s) and rev/revision "
                    "(%s) in source for %s",
                    source["branch"],
                    source["rev"],
                    source["name"],
                )
                sys.exit(1)
        super().__init__(source)

    @functools.lru_cache(maxsize=4096)
    def git_version(self) -> typing.Tuple[int, ...]:
        cmd = self.run_git(["--version"])
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            logger.error("Could not determine git version")
            logger.error(f"'git --version' output was:\n{stdout}\n{stderr}")
            sys.exit(1)

        m = re.search(r"git version (\d+)\.(\d+)(\.\d+)?(\.\d+)?", stdout)
        if m is None:
            logger.error("Unable to parse git version output")
            logger.error(f"'git --version' output was:\n{stdout}\n{stderr}")
            sys.exit(1)
        version = m.groups()

        if version[3] is not None:
            version = (
                int(version[0]),
                int(version[1]),
                int(version[2][1:]),
                int(version[3][1:]),
            )
        elif version[2] is not None:
            version = (int(version[0]), int(version[1]), int(version[2][1:]))
        else:
            version = (int(version[0]), int(version[1]))
        if version < (1, 5):
            logger.error(
                "Git version %s is unsupported, please upgrade",
                ".".join([str(v) for v in version]),
            )
            sys.exit(1)
        return version

    @property
    def _remote_branch_prefix(self):
        if self.git_version() < (1, 6, 3):
            return self._upstream_name
        return "remotes/%s" % self._upstream_name

    def run_git(self, commands: typing.List[str], **kwargs) -> subprocess.Popen:
        commands.insert(0, self.git_executable)
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
        # This should ease things up when multiple processes are trying to send
        # back to the main one large chunks of output
        kwargs["bufsize"] = -1
        kwargs["universal_newlines"] = True
        return subprocess.Popen(commands, **kwargs)

    def git_merge_rbranch(
        self, stdout_in: str, stderr_in: str, accept_missing: bool = False
    ) -> typing.Tuple[str, str]:
        path = self.source["path"]
        branch = self.source.get("branch", "master")

        cmd = self.run_git(["branch", "-a"], cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("'git branch -a' failed.\n%s" % stderr)
        stdout_in += stdout
        stderr_in += stderr
        if not re.search(r"^(\*| ) %s$" % re.escape(branch), stdout, re.M):
            # The branch is not local.  We should not have reached
            # this, unless no branch was specified and we guess wrong
            # that it should be master.
            if accept_missing:
                logger.info("No such branch %r", branch)
                return (stdout_in, stderr_in)
            logger.error("No such branch %r", branch)
            sys.exit(1)

        rbp = self._remote_branch_prefix
        cmd = self.run_git(["merge", f"{rbp}/{branch}"], cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError(
                f"git merge of remote branch 'origin/{branch}' failed.\n{stderr}"
            )
        return stdout_in + stdout, stderr_in + stderr

    def git_checkout(self, **kwargs) -> typing.Union[str, None]:
        name = self.source["name"]
        path = str(self.source["path"])
        url = self.source["url"]
        if os.path.exists(path):
            self.output(
                (logger.info, "Skipped cloning of existing package '%s'." % name)
            )
            return None
        msg = "Cloned '%s' with git" % name
        if "branch" in self.source:
            msg += " using branch '%s'" % self.source["branch"]
        msg += " from '%s'." % url
        self.output((logger.info, msg))
        args = ["clone", "--quiet"]
        update_git_submodules = self.source.get("submodules", kwargs["submodules"])
        if update_git_submodules == "recursive":
            args.append("--recurse-submodules")
        if "depth" in self.source or GIT_CLONE_DEPTH:
            args.extend(["--depth", self.source.get("depth", GIT_CLONE_DEPTH)])
        if "branch" in self.source:
            args.extend(["-b", self.source["branch"]])
        args.extend([url, path])
        cmd = self.run_git(args)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError(f"git cloning of '{name}' failed.\n{stderr}")
        if "rev" in self.source:
            stdout, stderr = self.git_switch_branch(stdout, stderr)
        if "pushurl" in self.source:
            stdout, stderr = self.git_set_pushurl(stdout, stderr)

        if update_git_submodules in ["always", "checkout"]:
            stdout, stderr, initialized = self.git_init_submodules(stdout, stderr)
            # Update only new submodules that we just registered. this is for safety reasons
            # as git submodule update on modified submodules may cause code loss
            for submodule in initialized:
                stdout, stderr = self.git_update_submodules(
                    stdout, stderr, submodule=submodule
                )
                self.output(
                    (
                        logger.info,
                        "Initialized '%s' submodule at '%s' with git."
                        % (name, submodule),
                    )
                )

        if kwargs.get("verbose", False):
            return stdout
        return None

    def git_switch_branch(
        self, stdout_in: str, stderr_in: str, accept_missing: bool = False
    ) -> typing.Tuple[str, str]:
        """Switch branches.

        If accept_missing is True, we do not switch the branch if it
        is not there.  Useful for switching back to master.
        """
        path = self.source["path"]
        branch = self.source.get("branch", "master")
        rbp = self._remote_branch_prefix
        cmd = self.run_git(["branch", "-a"], cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("'git branch -a' failed.\n%s" % stderr)
        stdout_in += stdout
        stderr_in += stderr
        if "rev" in self.source:
            # A tag or revision was specified instead of a branch
            argv = ["checkout", self.source["rev"]]
            self.output((logger.info, "Switching to rev '%s'." % self.source["rev"]))
        elif re.search(r"^(\*| ) %s$" % re.escape(branch), stdout, re.M):
            # the branch is local, normal checkout will work
            argv = ["checkout", branch]
            self.output((logger.info, f"Switching to branch '{branch}'."))
        elif re.search(
            "^  " + re.escape(rbp) + r"\/" + re.escape(branch) + "$", stdout, re.M
        ):
            # the branch is not local, normal checkout won't work here
            rbranch = f"{rbp}/{branch}"
            argv = ["checkout", "-b", branch, rbranch]
            self.output((logger.info, f"Switching to remote branch '{branch}'."))
        elif accept_missing:
            self.output((logger.info, f"No such branch {branch}"))
            return (stdout_in + stdout, stderr_in + stderr)
        else:
            self.output((logger.error, f"No such branch {branch}"))
            sys.exit(1)
        # runs the checkout with predetermined arguments
        cmd = self.run_git(argv, cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError(f"git checkout of branch '{branch}' failed.\n{stderr}")
        return (stdout_in + stdout, stderr_in + stderr)

    def git_update(self, **kwargs) -> typing.Union[str, None]:
        name = self.source["name"]
        path = self.source["path"]
        self.output((logger.info, "Updated '%s' with git." % name))
        # First we fetch.  This should always be possible.
        argv = ["fetch"]
        update_git_submodules = self.source.get("submodules", kwargs["submodules"])
        if update_git_submodules == "recursive":
            argv.append("--recurse-submodules")
        cmd = self.run_git(argv, cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError(f"git fetch of '{name}' failed.\n{stderr}")
        if "rev" in self.source:
            stdout, stderr = self.git_switch_branch(stdout, stderr)
        elif "branch" in self.source:
            stdout, stderr = self.git_switch_branch(stdout, stderr)
            stdout, stderr = self.git_merge_rbranch(stdout, stderr)
        else:
            # We may have specified a branch previously but not
            # anymore.  In that case, we want to revert to master.
            stdout, stderr = self.git_switch_branch(stdout, stderr, accept_missing=True)
            stdout, stderr = self.git_merge_rbranch(stdout, stderr, accept_missing=True)

        update_git_submodules = self.source.get("submodules", kwargs["submodules"])
        if update_git_submodules in ["always", "recursive"]:
            stdout, stderr, initialized = self.git_init_submodules(stdout, stderr)
            # Update only new submodules that we just registered. this is for safety reasons
            # as git submodule update on modified subomdules may cause code loss
            for submodule in initialized:
                stdout, stderr = self.git_update_submodules(
                    stdout,
                    stderr,
                    submodule=submodule,
                    recursive=update_git_submodules == "recursive",
                )
                self.output(
                    (
                        logger.info,
                        "Initialized '%s' submodule at '%s' with git."
                        % (name, submodule),
                    )
                )

        if kwargs.get("verbose", False):
            return stdout
        return None

    def checkout(self, **kwargs) -> typing.Union[str, None]:
        name = self.source["name"]
        path = self.source["path"]
        update = self.should_update(**kwargs)
        if not os.path.exists(path):
            return self.git_checkout(**kwargs)

        if update:
            return self.update(**kwargs)
        elif self.matches():
            self.output(
                (logger.info, "Skipped checkout of existing package '%s'." % name)
            )
        else:
            self.output(
                (
                    logger.warning,
                    "Checkout URL for existing package '%s' differs. Expected '%s'."
                    % (name, self.source["url"]),
                )
            )
        return None

    def status(self, **kwargs) -> typing.Union[typing.Tuple[str, str], str]:
        path = self.source["path"]
        cmd = self.run_git(["status", "-s", "-b"], cwd=path)
        stdout, stderr = cmd.communicate()
        lines = stdout.strip().split("\n")
        if len(lines) == 1:
            if "ahead" in lines[0]:
                status = "ahead"
            else:
                status = "clean"
        else:
            status = "dirty"
        if kwargs.get("verbose", False):
            return status, stdout
        return status

    def matches(self) -> bool:
        name = self.source["name"]
        path = self.source["path"]
        # This is the old matching code: it does not work on 1.5 due to the
        # lack of the -v switch
        cmd = self.run_git(["remote", "show", "-n", self._upstream_name], cwd=path)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError(f"git remote of '{name}' failed.\n{stderr}")
        return self.source["url"] in stdout.split()

    def update(self, **kwargs) -> typing.Union[str, None]:
        name = self.source["name"]
        if not self.matches():
            self.output(
                (
                    logger.warning,
                    "Can't update package '%s' because its URL doesn't match." % name,
                )
            )
        if self.status() != "clean" and not kwargs.get("force", False):
            raise GitError("Can't update package '%s' because it's dirty." % name)
        return self.git_update(**kwargs)

    def git_set_pushurl(self, stdout_in, stderr_in) -> typing.Tuple[str, str]:
        cmd = self.run_git(
            [
                "config",
                "remote.%s.pushurl" % self._upstream_name,
                self.source["pushurl"],
            ],
            cwd=self.source["path"],
        )
        stdout, stderr = cmd.communicate()

        if cmd.returncode != 0:
            raise GitError(
                "git config remote.%s.pushurl %s \nfailed.\n"
                % (self._upstream_name, self.source["pushurl"])
            )
        return (stdout_in + stdout, stderr_in + stderr)

    def git_init_submodules(
        self, stdout_in, stderr_in
    ) -> typing.Tuple[str, str, typing.List]:
        cmd = self.run_git(["submodule", "init"], cwd=self.source["path"])
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git submodule init failed.\n")
        output = stdout
        if not output:
            output = stderr
        initialized_submodules = re.findall(r'\s+[\'"](.*?)[\'"]\s+\(.+\)', output)
        return (stdout_in + stdout, stderr_in + stderr, initialized_submodules)

    def git_update_submodules(
        self, stdout_in, stderr_in, submodule="all", recursive: bool = False
    ) -> typing.Tuple[str, str]:
        params = ["submodule", "update"]
        if recursive:
            params.append("--init")
            params.append("--recursive")

        if submodule != "all":
            params.append(submodule)

        cmd = self.run_git(params, cwd=self.source["path"])
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitError("git submodule update failed.\n")
        return (stdout_in + stdout, stderr_in + stderr)
