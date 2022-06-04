import os
import pytest
import tempfile
import pathlib


@pytest.fixture
def tempdir():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tempdir:
        tempdir = pathlib.Path(tempdir).resolve()
        os.chdir(tempdir)
        try:
            yield tempdir
        finally:
            os.chdir(cwd)


@pytest.fixture
def src(tempdir):
    base = tempdir / "src"
    os.mkdir(base)
    return base


@pytest.fixture
def mkgitrepo(tempdir):
    from mxdev.tests.utils import GitRepo

    def mkgitrepo(name):
        repository = GitRepo(tempdir / name)
        repository.init()
        repository.setup_user()
        return repository

    return mkgitrepo


@pytest.fixture
def develop(src):
    from mxdev.tests.utils import MockDevelop

    develop = MockDevelop()
    develop.sources_dir = src
    return develop
