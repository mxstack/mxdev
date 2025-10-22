from . import common

import os
import re
import subprocess


logger = common.logger


class MercurialError(common.WCError):
    pass


class MercurialWorkingCopy(common.BaseWorkingCopy):
    def __init__(self, source):
        self.hg_executable = common.which("hg")
        source.setdefault("branch", "default")
        source.setdefault("rev")
        super().__init__(source)

    def hg_clone(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        url = self.source["url"]

        if os.path.exists(path):
            self.output((logger.info, f"Skipped cloning of existing package {name!r}."))
            return
        rev = self.get_rev()
        self.output((logger.info, f"Cloned {name!r} with mercurial."))
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        cmd = subprocess.Popen(
            [
                self.hg_executable,
                "clone",
                "--updaterev",
                rev,
                "--quiet",
                "--noninteractive",
                url,
                path,
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise MercurialError(f"hg clone for {name!r} failed.\n{stderr}")
        if kwargs.get("verbose", False):
            return stdout

    def get_rev(self):
        branch = self.source["branch"]
        rev = self.source["rev"]

        if branch != "default":
            if rev:
                raise ValueError("'branch' and 'rev' parameters cannot be used simultanously")
            else:
                rev = branch
        else:
            rev = rev or "default"

        if self.source.get("newest_tag", "").lower() in ["1", "true", "yes"]:
            rev = self._get_newest_tag() or rev
        return rev

    def _update_to_rev(self, rev):
        path = self.source["path"]
        name = self.source["name"]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        cmd = subprocess.Popen(
            [self.hg_executable, "checkout", rev, "-c"],
            cwd=path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode:
            raise MercurialError(f"hg update for {name!r} failed.\n{stderr}")
        self.output((logger.info, f"Switched {name!r} to {rev}."))
        return stdout

    def _get_tags(self):
        path = self.source["path"]
        name = self.source["name"]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        try:
            cmd = subprocess.Popen(
                [self.hg_executable, "tags"],
                cwd=path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError:
            return []
        stdout, stderr = cmd.communicate()
        if cmd.returncode:
            raise MercurialError(f"hg update for {name!r} failed.\n{stderr}")

        tag_line_re = re.compile(r"([^\s]+)[\s]*.*")

        def get_tag_name(line):
            matched = tag_line_re.match(line)
            if matched:
                return matched.groups()[0]

        tags = (get_tag_name(line) for line in stdout.split("\n"))
        return [tag for tag in tags if tag and tag != "tip"]

    def _get_newest_tag(self):
        mask = self.source.get("newest_tag_prefix", self.source.get("newest_tag_mask", ""))
        name = self.source["name"]
        tags = self._get_tags()
        if mask:
            tags = [t for t in tags if t.startswith(mask)]
        tags = common.version_sorted(tags, reverse=True)
        if not tags:
            return None
        newest_tag = tags[0]
        self.output(
            (
                logger.info,
                f"Picked newest tag for {name!r} from Mercurial: {newest_tag!r}.",
            )
        )
        return newest_tag

    def hg_pull(self, **kwargs):
        # NOTE: we don't include the branch here as we just want to update
        # to the head of whatever branch the developer is working on
        # However the 'rev' parameter works differently and forces revision
        name = self.source["name"]
        path = self.source["path"]
        self.output((logger.info, f"Updated {name!r} with mercurial."))
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        cmd = subprocess.Popen(
            [self.hg_executable, "pull", "-u"],
            cwd=path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            # hg v2.1 pull returns non-zero return code in case of
            # no remote changes.
            if "no changes found" not in stdout:
                raise MercurialError(f"hg pull for {name!r} failed.\n{stderr}")
        # to find newest_tag hg pull is needed before
        rev = self.get_rev()
        if rev:
            stdout += self._update_to_rev(rev)
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
                raise MercurialError(
                    "Source URL for existing package {!r} differs. " "Expected {!r}.".format(name, self.source["url"])
                )
        else:
            return self.hg_clone(**kwargs)

    def matches(self):
        name = self.source["name"]
        path = self.source["path"]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        cmd = subprocess.Popen(
            [self.hg_executable, "showconfig", "paths.default"],
            cwd=path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise MercurialError(f"hg showconfig for {name!r} failed.\n{stderr}")
        # now check that the working branch is the same
        return bytes(self.source["url"] + "\n", "utf-8") == stdout

    def status(self, **kwargs):
        path = self.source["path"]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        cmd = subprocess.Popen(
            [self.hg_executable, "status"],
            cwd=path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        status = stdout and "dirty" or "clean"
        if status == "clean":
            cmd = subprocess.Popen(
                [self.hg_executable, "outgoing"],
                cwd=path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            outgoing_stdout, stderr = cmd.communicate()
            stdout += b"\n" + outgoing_stdout
            if cmd.returncode == 0:
                status = "ahead"
        if kwargs.get("verbose", False):
            return status, stdout
        return status

    def update(self, **kwargs):
        name = self.source["name"]
        if not self.matches():
            raise MercurialError(f"Can't update package {name!r} because its URL doesn't match.")
        if self.status() != "clean" and not kwargs.get("force", False):
            raise MercurialError(f"Can't update package {name!r} because it's dirty.")
        return self.hg_pull(**kwargs)
