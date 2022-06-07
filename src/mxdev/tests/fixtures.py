import os
import pathlib
import pytest
import sys
import tempfile


@pytest.fixture
def tempdir():
    cwd = os.getcwd()
    try:
        kwargs = {"ignore_cleanup_errors": True} if sys.version_info >= (3, 10) else {}
        with tempfile.TemporaryDirectory(**kwargs) as tempdir:
            tempdir = pathlib.Path(tempdir).resolve()
            os.chdir(tempdir)
            yield tempdir
    except PermissionError:
        # happens on Windows on Python < 3.10
        pass
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
