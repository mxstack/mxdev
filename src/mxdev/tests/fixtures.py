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
def develop(src):
    from mxdev.tests.utils import MockDevelop

    develop = MockDevelop()
    develop.sources_dir = src
    return develop
