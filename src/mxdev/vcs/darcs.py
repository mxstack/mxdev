from . import common

import os
import subprocess
import typing


logger = common.logger


class DarcsError(common.WCError):
    pass


class DarcsWorkingCopy(common.BaseWorkingCopy):
    def __init__(self, source: typing.Dict[str, typing.Any]):
        super().__init__(source)
        self.darcs_executable = common.which("darcs")

    def darcs_checkout(self, **kwargs) -> typing.Union[str, None]:
        name = self.source["name"]
        path = self.source["path"]
        url = self.source["url"]
        if os.path.exists(path):
            self.output((logger.info, "Skipped getting of existing package '{name}'."))
            return None
        self.output((logger.info, f"Getting '{name}' with darcs."))
        cmd = subprocess.Popen(
            [self.darcs_executable, "get", "--quiet", "--lazy", url, path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise DarcsError(f"darcs get for '{name}' failed.\n{stderr.decode('utf8')}")
        if kwargs.get("verbose", False):
            return stdout.decode("utf8")
        return None

    def darcs_update(self, **kwargs) -> typing.Union[str, None]:
        name = self.source["name"]
        path = self.source["path"]
        self.output((logger.info, "Updating '%s' with darcs." % name))
        cmd = subprocess.Popen(
            [self.darcs_executable, "pull", "-a"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise DarcsError(
                f"darcs pull for '{name}' failed.\n{stderr.decode('utf8')}"
            )
        if kwargs.get("verbose", False):
            return stdout.decode("utf8")
        return None

    def checkout(self, **kwargs) -> typing.Union[str, None]:
        name = self.source["name"]
        path = self.source["path"]
        update = self.should_update(**kwargs)
        if not os.path.exists(path):
            return self.darcs_checkout(**kwargs)
        if update:
            self.update(**kwargs)
            return None
        if self.matches():
            self.output(
                (logger.info, f"Skipped checkout of existing package '{name}'.")
            )
            return None
        raise DarcsError(
            f"Checkout URL for existing package '{name}' differs. Expected '{self.source['url']}'."
        )

    def _darcs_related_repositories(self) -> typing.Generator:
        name = self.source["name"]
        path = self.source["path"]
        repos = os.path.join(path, "_darcs", "prefs", "repos")
        if os.path.exists(repos):
            for line in open(repos).readlines():
                yield line.strip()
        else:
            cmd = subprocess.Popen(
                [self.darcs_executable, "show", "repo"],
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = cmd.communicate()
            if cmd.returncode != 0:
                self.output(
                    (
                        logger.info,
                        f"darcs info for '{name}' failed.\n{stderr.decode('utf8')}",
                    )
                )
                return

            lines = stdout.decode("utf8").splitlines()
            for line in lines:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if k == "Default Remote":
                    yield v
                elif k == "Cache":
                    for cache in v.split(", "):
                        if cache.startswith("repo:"):
                            yield cache[5:]

    def matches(self) -> bool:
        return self.source["url"] in self._darcs_related_repositories()

    def status(self, **kwargs) -> typing.Union[str, typing.Tuple[str, str]]:
        path = self.source["path"]
        cmd = subprocess.Popen(
            [self.darcs_executable, "whatsnew"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        lines = stdout.decode("utf8").strip().split("\n")
        if "No changes" in lines[-1]:
            status = "clean"
        else:
            status = "dirty"
        if kwargs.get("verbose", False):
            return status, stdout.decode("utf8")
        return status

    def update(self, **kwargs) -> typing.Union[str, None]:
        name = self.source["name"]
        if not self.matches():
            raise DarcsError(
                "Can't update package '%s' because it's URL doesn't match." % name
            )
        if self.status() != "clean" and not kwargs.get("force", False):
            raise DarcsError("Can't update package '%s' because it's dirty." % name)
        return self.darcs_update(**kwargs)
