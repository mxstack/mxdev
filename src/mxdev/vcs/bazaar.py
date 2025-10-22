from . import common

import os
import subprocess


logger = common.logger


class BazaarError(common.WCError):
    pass


class BazaarWorkingCopy(common.BaseWorkingCopy):
    def __init__(self, source):
        super().__init__(source)
        self.bzr_executable = common.which("bzr")

    def bzr_branch(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        url = self.source["url"]
        if os.path.exists(path):
            self.output((logger.info, f"Skipped branching existing package {name!r}."))
            return
        self.output((logger.info, f"Branched {name!r} with bazaar."))
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        cmd = subprocess.Popen(
            [self.bzr_executable, "branch", "--quiet", url, path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise BazaarError(f"bzr branch for {name!r} failed.\n{stderr}")
        if kwargs.get("verbose", False):
            return stdout

    def bzr_pull(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        url = self.source["url"]
        self.output((logger.info, f"Updated {name!r} with bazaar."))
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        cmd = subprocess.Popen(
            [self.bzr_executable, "pull", url],
            cwd=path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise BazaarError(f"bzr pull for {name!r} failed.\n{stderr}")
        if kwargs.get("verbose", False):
            return stdout

    def checkout(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        update = self.should_update(**kwargs)
        if os.path.exists(path):
            if update:
                self.update(**kwargs)
            elif self.matches():
                self.output((logger.info, f"Skipped checkout of existing package {name!r}."))
            else:
                raise BazaarError(
                    "Source URL for existing package {!r} differs. " "Expected {!r}.".format(name, self.source["url"])
                )
        else:
            return self.bzr_branch(**kwargs)

    def matches(self):
        name = self.source["name"]
        path = self.source["path"]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        cmd = subprocess.Popen(
            [self.bzr_executable, "info"],
            cwd=path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise BazaarError(f"bzr info for {name!r} failed.\n{stderr}")
        return self.source["url"] in stdout.split()

    def status(self, **kwargs):
        path = self.source["path"]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        cmd = subprocess.Popen(
            [self.bzr_executable, "status"],
            cwd=path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        status = stdout and "dirty" or "clean"
        if kwargs.get("verbose", False):
            return status, stdout
        return status

    def update(self, **kwargs):
        name = self.source["name"]
        if not self.matches():
            raise BazaarError(f"Can't update package {name!r} because its URL doesn't match.")
        if self.status() != "clean" and not kwargs.get("force", False):
            raise BazaarError(f"Can't update package {name!r} because it's dirty.")
        return self.bzr_pull(**kwargs)
