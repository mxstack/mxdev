from .utils import Process

import os
import pytest


@pytest.fixture
def tempdir(tmp_path):
    cwd = os.getcwd()
    try:
        wd = tmp_path / "testdir"
        wd.mkdir()
        yield wd
    finally:
        os.chdir(cwd)


@pytest.fixture
def src(tempdir):
    base = tempdir / "src"
    os.mkdir(base)
    return base


@pytest.fixture
def mkgitrepo(tempdir):
    from .utils import GitRepo

    def _mkgitrepo(name):
        repository = GitRepo(tempdir / name)
        repository.init()
        repository.setup_user()
        return repository

    return _mkgitrepo


@pytest.fixture
def git_allow_file_protocol():
    """
    Allow file protocol
    This is needed for the submodule to be added from a local path
    """
    from .utils import GitRepo

    shell = Process()
    file_allow = (
        shell.check_call("git config --global --get protocol.file.allow")[0]
        .decode("utf8")
        .strip()
    )
    shell.check_call(f"git config --global protocol.file.allow always")
    yield file_allow
    shell.check_call(f"git config --global protocol.file.allow {file_allow}")


@pytest.fixture
def develop(src):
    from mxdev.tests.utils import MockDevelop

    develop = MockDevelop()
    develop.sources_dir = src
    return develop


@pytest.fixture
def httpretty():
    import httpretty

    httpretty.enable()
    yield httpretty
    httpretty.disable()
    httpretty.reset()
