from . import common
from urllib.parse import urlparse
from urllib.parse import urlunparse

import getpass
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as etree


logger = common.logger


class SVNError(common.WCError):
    pass


class SVNAuthorizationError(SVNError):
    pass


class SVNCertificateError(SVNError):
    pass


class SVNCertificateRejectedError(SVNError):
    pass


_svn_version_warning = False


class SVNWorkingCopy(common.BaseWorkingCopy):
    _svn_info_cache: dict = {}
    _svn_auth_cache: dict = {}
    _svn_cert_cache: dict = {}

    @classmethod
    def _clear_caches(klass):
        klass._svn_info_cache.clear()
        klass._svn_auth_cache.clear()
        klass._svn_cert_cache.clear()

    def _normalized_url_rev(self):
        url = urlparse(self.source["url"])
        rev = None
        if "@" in url[2]:
            path, rev = url[2].split("@", 1)
            url = list(url)
            url[2] = path
        if "rev" in self.source and "revision" in self.source:
            raise ValueError(
                "The source definition of '{}' contains duplicate revision options.".format(self.source["name"])
            )
        if rev is not None and ("rev" in self.source or "revision" in self.source):
            raise ValueError(
                "The url of '{}' contains a revision and there is an additional revision option.".format(
                    self.source["name"]
                )
            )
        elif rev is None:
            rev = self.source.get("revision", self.source.get("rev"))
        return urlunparse(url), rev

    def __init__(self, *args, **kwargs):
        common.BaseWorkingCopy.__init__(self, *args, **kwargs)
        self.svn_executable = common.which("svn")
        self._svn_check_version()

    def _svn_check_version(self):
        global _svn_version_warning
        try:
            cmd = subprocess.Popen(
                [self.svn_executable, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError:
            if getattr(sys.exc_info()[1], "errno", None) == 2:
                logger.error("Couldn't find 'svn' executable on your PATH.")
                sys.exit(1)
            raise
        stdout, stderr = cmd.communicate()
        lines = stdout.split(b"\n")
        version = None
        if len(lines):
            version = re.search(r"(\d+)\.(\d+)(\.\d+)?", lines[0])
            if version is not None:
                version = version.groups()
                if len(version) == 3:
                    version = (int(version[0]), int(version[1]), int(version[2][1:]))
                else:
                    version = (int(version[0]), int(version[1]))
        if (cmd.returncode != 0) or (version is None):
            logger.error("Couldn't determine the version of 'svn' command.")
            logger.error(
                "Subversion output:\n{}\n{}".format(*stdout.decode("utf8")),
                stderr.decode("utf8"),
            )
            sys.exit(1)
        if (version < (1, 5)) and not _svn_version_warning:
            logger.warning(
                "The installed 'svn' command is too old. Expected 1.5 or newer, got {}.".format(
                    ".".join([str(x) for x in version])
                )
            )
            _svn_version_warning = True

    def _svn_auth_get(self, url):
        for root in self._svn_auth_cache:
            if url.startswith(root):
                return self._svn_auth_cache[root]

    def _svn_accept_invalid_cert_get(self, url):
        for root in self._svn_cert_cache:
            if url.startswith(root):
                return self._svn_cert_cache[root]

    def _svn_error_wrapper(self, f, **kwargs):
        count = 4
        while count:
            count = count - 1
            try:
                return f(**kwargs)
            except SVNAuthorizationError:
                lines = sys.exc_info()[1].args[0].split("\n")
                root = lines[-1].split("(")[-1].strip(")")
                before = self._svn_auth_cache.get(root)
                common.output_lock.acquire()
                common.input_lock.acquire()
                after = self._svn_auth_cache.get(root)
                if before != after:
                    count = count + 1
                    common.input_lock.release()
                    common.output_lock.release()
                    continue
                print("Authorization needed for '{}' at '{}'".format(self.source["name"], self.source["url"]))
                user = input("Username: ")
                passwd = getpass.getpass("Password: ")
                self._svn_auth_cache[root] = dict(
                    user=user,
                    passwd=passwd,
                )
                common.input_lock.release()
                common.output_lock.release()
            except SVNCertificateError:
                lines = sys.exc_info()[1].args[0].split("\n")
                root = lines[-1].split("(")[-1].strip(")")
                before = self._svn_cert_cache.get(root)
                common.output_lock.acquire()
                common.input_lock.acquire()
                after = self._svn_cert_cache.get(root)
                if before != after:
                    count = count + 1
                    common.input_lock.release()
                    common.output_lock.release()
                    continue
                print("\n".join(lines[:-1]))
                while 1:
                    answer = input("(R)eject or accept (t)emporarily? ")
                    if answer.lower() in ["r", "t"]:
                        break
                    else:
                        print("Invalid answer, type 'r' for reject or 't' for temporarily.")
                if answer == "r":
                    self._svn_cert_cache[root] = False
                else:
                    self._svn_cert_cache[root] = True
                count = count + 1
                common.input_lock.release()
                common.output_lock.release()

    def _svn_checkout(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        url = self.source["url"]
        args = [self.svn_executable, "checkout", url, path]
        stdout, stderr, returncode = self._svn_communicate(args, url, **kwargs)
        if returncode != 0:
            raise SVNError("Subversion checkout for '{}' failed.\n{}".format(name, stderr.decode("utf8")))
        if kwargs.get("verbose", False):
            return stdout.decode("utf8")

    def _svn_communicate(self, args, url, **kwargs):
        auth = self._svn_auth_get(url)
        if auth is not None:
            args[2:2] = ["--username", auth["user"], "--password", auth["passwd"]]
        if not kwargs.get("verbose", False):
            args[2:2] = ["--quiet"]
        accept_invalid_cert = self._svn_accept_invalid_cert_get(url)
        if "always_accept_server_certificate" in kwargs:
            if kwargs["always_accept_server_certificate"]:
                accept_invalid_cert = True
        if accept_invalid_cert is True:
            args[2:2] = ["--trust-server-cert"]
        elif accept_invalid_cert is False:
            raise SVNCertificateRejectedError("Server certificate rejected by user.")
        args[2:2] = ["--no-auth-cache"]
        interactive_args = args[:]
        args[2:2] = ["--non-interactive"]
        cmd = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            lines = stderr.strip().split(b"\n")
            if "authorization failed" in lines[-1] or "Could not authenticate to server" in lines[-1]:
                raise SVNAuthorizationError(stderr.strip())
            if "Server certificate verification failed: issuer is not trusted" in lines[-1]:
                cmd = subprocess.Popen(
                    interactive_args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = cmd.communicate("t")
                raise SVNCertificateError(stderr.strip())
        return stdout, stderr, cmd.returncode

    def _svn_info(self):
        name = self.source["name"]
        if name in self._svn_info_cache:
            return self._svn_info_cache[name]
        path = self.source["path"]
        cmd = subprocess.Popen(
            [self.svn_executable, "info", "--non-interactive", "--xml", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise SVNError("Subversion info for '{}' failed.\n{}".format(name, stderr.decode("utf8")))
        info = etree.fromstring(stdout)
        result = {}
        entry = info.find("entry")
        if entry is not None:
            rev = entry.attrib.get("revision")
            if rev is not None:
                result["revision"] = rev
            info_url = entry.find("url")
            if info_url is not None:
                result["url"] = info_url.text
        entry = info.find("entry")
        if entry is not None:
            root = entry.find("root")
            if root is not None:
                result["root"] = root.text
        self._svn_info_cache[name] = result
        return result

    def _svn_switch(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        url, rev = self._normalized_url_rev()
        args = [self.svn_executable, "switch", url, path]
        if rev is not None and not rev.startswith(">"):
            args.insert(2, f"-r{rev}")
        stdout, stderr, returncode = self._svn_communicate(args, url, **kwargs)
        if returncode != 0:
            raise SVNError("Subversion switch of '{}' failed.\n{}".format(name, stderr.decode("utf8")))
        if kwargs.get("verbose", False):
            return stdout.decode("utf8")

    def _svn_update(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        url, rev = self._normalized_url_rev()
        args = [self.svn_executable, "update", path]
        if rev is not None and not rev.startswith(">"):
            args.insert(2, f"-r{rev}")
        stdout, stderr, returncode = self._svn_communicate(args, url, **kwargs)
        if returncode != 0:
            raise SVNError("Subversion update of '{}' failed.\n{}".format(name, stderr.decode("utf8")))
        if kwargs.get("verbose", False):
            return stdout.decode("utf8")

    def svn_checkout(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        if os.path.exists(path):
            self.output((logger.info, f"Skipped checkout of existing package '{name}'."))
            return
        self.output((logger.info, f"Checked out '{name}' with subversion."))
        return self._svn_error_wrapper(self._svn_checkout, **kwargs)

    def svn_switch(self, **kwargs):
        name = self.source["name"]
        self.output((logger.info, f"Switched '{name}' with subversion."))
        return self._svn_error_wrapper(self._svn_switch, **kwargs)

    def svn_update(self, **kwargs):
        name = self.source["name"]
        self.output((logger.info, f"Updated '{name}' with subversion."))
        return self._svn_error_wrapper(self._svn_update, **kwargs)

    def checkout(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        update = self.should_update(**kwargs)
        if os.path.exists(path):
            matches = self.matches()
            if matches:
                if update:
                    self.update(**kwargs)
                else:
                    self.output(
                        (
                            logger.info,
                            f"Skipped checkout of existing package '{name}'.",
                        )
                    )
            else:
                if self.status() == "clean":
                    return self.svn_switch(**kwargs)
                else:
                    url = self._svn_info().get("url", "")
                    if url:
                        msg = f"The current checkout of '{name}' is from '{url}'."
                        msg += "\nCan't switch package to '{}' because it's dirty.".format(self.source["url"])
                    else:
                        msg = "Can't switch package '{}' to '{}' because it's dirty.".format(name, self.source["url"])
                    raise SVNError(msg)
        else:
            return self.svn_checkout(**kwargs)

    def matches(self):
        info = self._svn_info()
        url, rev = self._normalized_url_rev()
        if url.endswith("/"):
            url = url[:-1]
        if rev is None:
            rev = info.get("revision")
        if rev.startswith(">="):
            return (info.get("url") == url) and (int(info.get("revision")) >= int(rev[2:]))
        elif rev.startswith(">"):
            return (info.get("url") == url) and (int(info.get("revision")) > int(rev[1:]))
        else:
            return (info.get("url") == url) and (info.get("revision") == rev)

    def status(self, **kwargs):
        name = self.source["name"]
        path = self.source["path"]
        cmd = subprocess.Popen(
            [self.svn_executable, "status", "--xml", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise SVNError(f"Subversion status for '{name}' failed.\n{stderr.decode()}")
        info = etree.fromstring(stdout)
        clean = True
        for target in info.findall("target"):
            for entry in target.findall("entry"):
                status = entry.find("wc-status")
                if status is not None and status.get("item") != "external":
                    clean = False
                    break
        status = "clean" if clean else "dirty"
        if kwargs.get("verbose", False):
            cmd = subprocess.Popen(
                [self.svn_executable, "status", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = cmd.communicate()
            if cmd.returncode != 0:
                raise SVNError(f"Subversion status for '{name}' failed.\n{stderr.decode('utf8')}")
            return status, stdout.decode("utf8")
        return status

    def update(self, **kwargs):
        name = self.source["name"]
        force = kwargs.get("force", False)
        status = self.status()
        if not self.matches():
            if force or status == "clean":
                return self.svn_switch(**kwargs)
            else:
                raise SVNError(f"Can't switch package '{name}' because it's dirty.")
        if status != "clean" and not force:
            raise SVNError(f"Can't update package '{name}' because it's dirty.")
        return self.svn_update(**kwargs)
