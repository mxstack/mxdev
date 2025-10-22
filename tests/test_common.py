from mxdev import vcs
from mxdev.vcs import common

import logging
import os
import pytest
import queue


def test_print_stderr(mocker):
    write_ = mocker.patch("sys.stderr.write")
    flush_ = mocker.patch("sys.stderr.flush")
    common.print_stderr("message")
    assert write_.call_count == 2
    assert flush_.call_count == 1


def test_version_sorted():
    expected = ["version-1-0-1", "version-1-0-2", "version-1-0-10"]
    actual = common.version_sorted(["version-1-0-10", "version-1-0-2", "version-1-0-1"])
    assert expected == actual


def test_BaseWorkingCopy():
    with pytest.raises(TypeError):
        common.BaseWorkingCopy(source={})

    class TestWorkingCopy(common.BaseWorkingCopy):
        def checkout(self, **kwargs) -> str | None:  # type: ignore
            ...

        def status(self, **kwargs) -> tuple[str, str] | str:  # type: ignore
            ...

        def matches(self) -> bool:  # type: ignore
            ...

        def update(self, **kwargs) -> str | None:  # type: ignore
            ...

    bwc = TestWorkingCopy(source=dict(url="https://tld.com/repo.git"))
    assert bwc._output == []
    bwc.output("foo")
    assert bwc._output == ["foo"]

    assert bwc.should_update(offline=True) is False
    assert bwc.should_update(update="true") is True
    assert bwc.should_update(update="yes") is True
    assert bwc.should_update(update="false") is False
    assert bwc.should_update(update="no") is False
    with pytest.raises(ValueError):
        bwc.should_update(update="maybe")

    bwc = TestWorkingCopy(source=dict(url="https://tld.com/repo.git", update="false"))
    assert bwc.should_update(update="true") is False


class Input:
    def __init__(self):
        self.question = ""
        self.answer = ""

    def __call__(self, question):
        self.question = question
        answer = self.answer
        if answer == "invalid":
            self.answer = ""
        return answer


def test_yesno(mocker):
    input_ = mocker.patch("mxdev.vcs.common.input", new_callable=Input)
    print_stderr = mocker.patch("mxdev.vcs.common.print_stderr")

    common.yesno(question="Really?")
    assert input_.question == "Really? [Yes/no/all] "

    common.yesno(question="Really?", all=False)
    assert input_.question == "Really? [Yes/no] "

    assert common.yesno(question="") is True
    assert common.yesno(question="", default=False) is False

    input_.answer = "y"
    assert common.yesno(question="") is True
    input_.answer = "yes"
    assert common.yesno(question="") is True

    input_.answer = "n"
    assert common.yesno(question="") is False
    input_.answer = "no"
    assert common.yesno(question="") is False

    input_.answer = "a"
    assert common.yesno(question="") == "all"
    input_.answer = "all"
    assert common.yesno(question="") == "all"

    input_.answer = "invalid"
    common.yesno(question="")
    print_stderr.assert_called_with("You have to answer with y, yes, n, no, a or all.")

    input_.answer = "invalid"
    common.yesno(question="", all=False)
    print_stderr.assert_called_with("You have to answer with y, yes, n or no.")


def test_get_workingcopytypes():
    assert common._workingcopytypes == dict()
    workingcopytypes = common.get_workingcopytypes()
    assert workingcopytypes == {
        "bzr": vcs.bazaar.BazaarWorkingCopy,
        "darcs": vcs.darcs.DarcsWorkingCopy,
        "fs": vcs.filesystem.FilesystemWorkingCopy,
        "git": vcs.git.GitWorkingCopy,
        "gitsvn": vcs.gitsvn.GitSVNWorkingCopy,
        "hg": vcs.mercurial.MercurialWorkingCopy,
        "svn": vcs.svn.SVNWorkingCopy,
    }
    assert workingcopytypes is common._workingcopytypes


def test_WorkingCopies_process(mocker, caplog):
    exit = mocker.patch("sys.exit")
    worker = mocker.patch("mxdev.vcs.common.worker")

    wc = common.WorkingCopies(sources={}, threads=1)
    wc.process(queue.Queue())
    assert worker.call_count == 1

    wc.threads = 5
    wc.process(queue.Queue())
    assert worker.call_count == 6

    wc.threads = 2
    wc.errors = True
    wc.process(queue.Queue())
    assert exit.call_count == 1
    assert caplog.messages == ["There have been errors, see messages above."]


def test_WorkingCopies_checkout(mocker, caplog, tmpdir):
    caplog.set_level(logging.INFO)

    class SysExit(Exception): ...

    class Exit:
        def __call__(self, code):
            raise SysExit(code)

    mocker.patch("sys.exit", new_callable=Exit)

    class TestWorkingCopy(common.BaseWorkingCopy):
        package_status = "clean"

        def checkout(self, **kwargs) -> str | None:
            common.logger.info(f"Checkout called with: {kwargs}")
            return None

        def status(self, **kwargs) -> tuple[str, str] | str:
            return self.package_status

        def matches(self) -> bool:  # type: ignore
            ...

        def update(self, **kwargs) -> str | None:  # type: ignore
            ...

    class WCT(dict):
        def __init__(self):
            self["wct"] = TestWorkingCopy

    mocker.patch("mxdev.vcs.common._workingcopytypes", new_callable=WCT)

    wc = common.WorkingCopies(sources={})

    with pytest.raises(SysExit):
        wc.checkout(packages=[], update="invalid")
    assert caplog.messages == ["Unknown value 'invalid' for always-checkout option."]
    caplog.clear()

    with pytest.raises(SysExit):
        wc.checkout(packages=[], submodules="invalid")
    assert caplog.messages == ["Unknown value 'invalid' for update-git-submodules option."]
    caplog.clear()

    with pytest.raises(SysExit):
        wc.checkout(packages=["invalid"])
    assert caplog.messages == ["Checkout failed. No source defined for 'invalid'."]
    caplog.clear()

    wc = common.WorkingCopies(sources=dict(package=dict(vcs="invalid")))
    wc.checkout(packages=["package"])
    assert caplog.messages == ["Unregistered repository type invalid"]
    caplog.clear()

    wc = common.WorkingCopies(
        sources=dict(package=dict(vcs="wct", path=tmpdir.join("package").strpath)),
        threads=1,
    )
    wc.checkout(packages=["package"], update=True)
    assert caplog.messages == [
        "Queued 'package' for checkout.",
        "Checkout called with: {'update': True, 'submodules': 'always'}",
    ]
    caplog.clear()

    package_dir = tmpdir.mkdir("package_dir")
    os.symlink(package_dir.strpath, tmpdir.join("package").strpath, target_is_directory=True)
    wc.checkout(packages=["package"], update=True)
    assert caplog.messages == ["Skipped update of linked 'package'."]
    caplog.clear()
    tmpdir.join("package").remove()
    package_dir.remove()

    input_ = mocker.patch("mxdev.vcs.common.input", new_callable=Input)
    print_stderr = mocker.patch("mxdev.vcs.common.print_stderr")

    TestWorkingCopy.package_status = "dirty"
    package_dir = tmpdir.mkdir("package")
    wc.checkout(packages=["package"], update=True)
    print_stderr.assert_called_with("The package 'package' is dirty.")
    assert caplog.messages == ["Skipped update of 'package'."]
    caplog.clear()

    wc.checkout(packages=["package"], update="force")
    print_stderr.assert_called_with("The package 'package' is dirty.")
    assert caplog.messages == [
        "Queued 'package' for checkout.",
        "Checkout called with: {'update': True, 'force': True, 'submodules': 'always'}",
    ]
    caplog.clear()


def test_which_windows(mocker):
    """Test which() on Windows platform."""
    mocker.patch("platform.system", return_value="Windows")
    mocker.patch.dict("os.environ", {"PATHEXT": ".COM;.EXE;.BAT", "PATH": "/fake/path"})
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.access", return_value=False)

    # Test with default value
    result = common.which("test", default="/default/test")
    assert result == "/default/test"

    # Test without default - should exit
    exit_mock = mocker.patch("sys.exit")
    common.which("test")
    exit_mock.assert_called_once_with(1)


@pytest.mark.skipif(os.name == "nt", reason="Unix-specific test")
def test_which_unix(mocker):
    """Test which() on Unix platform."""
    mocker.patch("platform.system", return_value="Linux")
    mocker.patch("os.pathsep", ":")
    mocker.patch.dict("os.environ", {"PATH": "/usr/bin:/bin"}, clear=True)

    def exists_side_effect(path):
        return path == "/usr/bin/python"

    def access_side_effect(path, mode):
        return path == "/usr/bin/python"

    mocker.patch("os.path.exists", side_effect=exists_side_effect)
    mocker.patch("os.access", side_effect=access_side_effect)

    result = common.which("python")
    assert result == "/usr/bin/python"


def test_get_workingcopytypes_duplicate_error(mocker, caplog):
    """Test get_workingcopytypes() with duplicate entry."""

    class FakeEntryPoint:
        name = "duplicate"
        value = "fake.module:FakeClass"

        def load(self):
            return "FakeWorkingCopy"

    # Save the original workingcopytypes
    original_wct = common._workingcopytypes.copy()

    try:
        exit_mock = mocker.patch("sys.exit")
        mocker.patch(
            "mxdev.vcs.common.load_eps_by_group",
            return_value=[FakeEntryPoint(), FakeEntryPoint()],
        )
        common._workingcopytypes.clear()

        common.get_workingcopytypes()
        exit_mock.assert_called_once_with(1)
    finally:
        # Restore the original workingcopytypes
        common._workingcopytypes.clear()
        common._workingcopytypes.update(original_wct)


def test_WorkingCopies_matches(mocker, caplog):
    """Test WorkingCopies.matches() method."""

    class TestWorkingCopy(common.BaseWorkingCopy):
        def checkout(self, **kwargs):
            return None

        def status(self, **kwargs):
            return "clean"

        def matches(self):
            return True

        def update(self, **kwargs):
            return None

    exit_mock = mocker.patch("sys.exit")
    mocker.patch("mxdev.vcs.common._workingcopytypes", {"test": TestWorkingCopy})

    wc = common.WorkingCopies(sources={"package": {"vcs": "test", "name": "package", "url": "test://url"}})

    # Test successful match
    result = wc.matches({"name": "package"})
    assert result is True

    # Test with missing source
    try:
        wc.matches({"name": "missing"})
    except KeyError:
        pass  # Expected - sys.exit() is mocked so code continues
    exit_mock.assert_called_with(1)
    assert "Checkout failed. No source defined for 'missing'." in caplog.text
    caplog.clear()
    exit_mock.reset_mock()

    # Test with unregistered VCS type
    wc.sources = {"package": {"vcs": "unknown", "name": "package"}}
    try:
        wc.matches({"name": "package"})
    except TypeError:
        pass  # Expected - sys.exit() is mocked so code continues
    exit_mock.assert_called_with(1)
    assert "Unregistered repository type unknown" in caplog.text
    caplog.clear()
    exit_mock.reset_mock()

    # Test with WCError exception
    class ErrorWorkingCopy(TestWorkingCopy):
        def matches(self):
            raise common.WCError("Test error")

    wc.workingcopytypes = {"test": ErrorWorkingCopy}
    wc.sources = {"package": {"vcs": "test", "name": "package"}}
    try:
        wc.matches({"name": "package"})
    except (TypeError, common.WCError):
        pass  # Expected - WCError is raised
    assert "Can not get matches!" in caplog.text
    exit_mock.assert_called_with(1)


def test_WorkingCopies_status(mocker, caplog):
    """Test WorkingCopies.status() method."""

    class TestWorkingCopy(common.BaseWorkingCopy):
        def checkout(self, **kwargs):
            return None

        def status(self, **kwargs):
            return "clean"

        def matches(self):
            return True

        def update(self, **kwargs):
            return None

    exit_mock = mocker.patch("sys.exit")
    mocker.patch("mxdev.vcs.common._workingcopytypes", {"test": TestWorkingCopy})

    wc = common.WorkingCopies(sources={"package": {"vcs": "test", "name": "package", "url": "test://url"}})

    # Test successful status
    result = wc.status({"name": "package"})
    assert result == "clean"

    # Test with missing source
    try:
        wc.status({"name": "missing"})
    except KeyError:
        pass  # Expected - sys.exit() is mocked so code continues
    exit_mock.assert_called_with(1)
    assert "Status failed. No source defined for 'missing'." in caplog.text
    caplog.clear()
    exit_mock.reset_mock()

    # Test with unregistered VCS type
    wc.sources = {"package": {"vcs": "unknown", "name": "package"}}
    try:
        wc.status({"name": "package"})
    except TypeError:
        pass  # Expected - sys.exit() is mocked so code continues
    assert "Unregistered repository type unknown" in caplog.text
    exit_mock.assert_called_with(1)
    caplog.clear()
    exit_mock.reset_mock()

    # Test with WCError exception
    class ErrorWorkingCopy(TestWorkingCopy):
        def status(self, **kwargs):
            raise common.WCError("Test error")

    wc.workingcopytypes = {"test": ErrorWorkingCopy}
    wc.sources = {"package": {"vcs": "test", "name": "package"}}
    try:
        wc.status({"name": "package"})
    except (TypeError, common.WCError):
        pass  # Expected - WCError is raised
    assert "Can not get status!" in caplog.text
    exit_mock.assert_called_with(1)


def test_WorkingCopies_update(mocker, caplog, tmp_path):
    """Test WorkingCopies.update() method."""
    caplog.set_level(logging.INFO)

    class TestWorkingCopy(common.BaseWorkingCopy):
        package_status = "clean"

        def checkout(self, **kwargs):
            return None

        def status(self, **kwargs):
            return self.package_status

        def matches(self):
            return True

        def update(self, **kwargs):
            common.logger.info(f"Update called with: {kwargs}")
            return None

    exit_mock = mocker.patch("sys.exit")
    mocker.patch("mxdev.vcs.common._workingcopytypes", {"test": TestWorkingCopy})

    package_dir = tmp_path / "package"
    package_dir.mkdir()
    wc = common.WorkingCopies(
        sources={"package": {"vcs": "test", "name": "package", "path": str(package_dir)}},
        threads=1,
    )

    # Test clean update
    wc.update(packages=["package"])
    assert "Queued 'package' for update." in caplog.text
    assert "Update called with:" in caplog.text
    caplog.clear()

    # Test with missing package - should skip
    wc.update(packages=["missing"])
    assert "missing" not in caplog.text
    caplog.clear()

    # Test with unregistered VCS type
    wc.sources = {"package": {"vcs": "unknown", "name": "package", "path": str(package_dir)}}
    try:
        wc.update(packages=["package"])
    except TypeError:
        # Expected - sys.exit() is mocked so code continues and tries to call None
        pass
    exit_mock.assert_called_with(1)
    assert "Unregistered repository type unknown" in caplog.text
    caplog.clear()
    exit_mock.reset_mock()

    # Test dirty package with user declining update
    input_mock = mocker.patch("mxdev.vcs.common.input", new_callable=Input)
    input_mock.answer = "n"
    print_stderr = mocker.patch("mxdev.vcs.common.print_stderr")

    TestWorkingCopy.package_status = "dirty"
    wc.sources = {"package": {"vcs": "test", "name": "package", "path": str(package_dir)}}
    wc.update(packages=["package"])
    print_stderr.assert_called_with("The package 'package' is dirty.")
    assert "Skipped update of 'package'." in caplog.text
    caplog.clear()

    # Test dirty package with user accepting update
    input_mock.answer = "y"
    wc.update(packages=["package"])
    assert "Queued 'package' for update." in caplog.text
    assert "'force': True" in caplog.text
    caplog.clear()

    # Test dirty package with 'all' answer
    input_mock.answer = "all"
    wc.update(packages=["package"])
    assert "Queued 'package' for update." in caplog.text
    caplog.clear()


def test_worker_with_error(mocker, caplog):
    """Test worker() function with WCError exception."""

    class TestWorkingCopy(common.BaseWorkingCopy):
        def checkout(self, **kwargs):
            raise common.WCError("Test error")

        def status(self, **kwargs):
            return "clean"

        def matches(self):
            return True

        def update(self, **kwargs):
            return None

    wc = TestWorkingCopy(source={"url": "test://url"})
    wc.output((logging.error, "Error message"))

    working_copies = common.WorkingCopies(sources={})
    test_queue = queue.Queue()
    test_queue.put((wc, wc.checkout, {}))

    common.worker(working_copies, test_queue)

    assert working_copies.errors is True
    assert "Can not execute action!" in caplog.text


def test_worker_with_bytes_output(mocker):
    """Test worker() function with bytes output."""

    class TestWorkingCopy(common.BaseWorkingCopy):
        def checkout(self, **kwargs):
            return b"bytes output"

        def status(self, **kwargs):
            return "clean"

        def matches(self):
            return True

        def update(self, **kwargs):
            return None

    wc = TestWorkingCopy(source={"url": "test://url"})

    working_copies = common.WorkingCopies(sources={})
    test_queue = queue.Queue()
    test_queue.put((wc, wc.checkout, {"verbose": True}))

    print_mock = mocker.patch("builtins.print")
    common.worker(working_copies, test_queue)

    print_mock.assert_called_once_with("bytes output")


def test_worker_errors_flag(mocker):
    """Test worker() respects the errors flag."""
    working_copies = common.WorkingCopies(sources={})
    working_copies.errors = True
    test_queue = queue.Queue()

    # Should return immediately without processing queue
    common.worker(working_copies, test_queue)
    assert test_queue.qsize() == 0  # Queue should not be modified
