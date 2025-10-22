from . import common
from .svn import SVNWorkingCopy

import subprocess


logger = common.logger


class GitSVNError(common.WCError):
    pass


class GitSVNWorkingCopy(SVNWorkingCopy):
    def __init__(self, source):
        super().__init__(source)
        self.gitify_executable = common.which("gitify")

    def gitify_init(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        self.output((logger.info, f"Gitified '{name}'."))
        cmd = subprocess.Popen(
            [self.gitify_executable, "init"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitSVNError(f"gitify init for '{name}' failed.\n{stdout}")
        if kwargs.get("verbose", False):
            return stdout

    def svn_checkout(self, **kwargs):
        super().svn_checkout(**kwargs)
        return self.gitify_init(**kwargs)

    def svn_switch(self, **kwargs):
        super().svn_switch(**kwargs)
        return self.gitify_init(**kwargs)

    def svn_update(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        self.output((logger.info, f"Updated '{name}' with gitify."))
        cmd = subprocess.Popen(
            [self.gitify_executable, "update"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitSVNError(f"gitify update for '{name}' failed.\n{stdout}")
        if kwargs.get("verbose", False):
            return stdout

    def status(self, **kwargs):
        svn_status = super().status(**kwargs)
        if svn_status == "clean":
            return common.get_workingcopytypes()["git"](self.source).status(**kwargs)
        if kwargs.get("verbose", False):
            return svn_status, ""
        return svn_status
