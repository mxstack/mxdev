import pathlib
import pytest


def test_resolve_dependencies_files():
    from mxdev.including import resolve_dependencies

    base = pathlib.Path(__file__).parent / "data"
    file_list = resolve_dependencies(base / "file01.ini", base)
    assert len(file_list) == 4
    assert file_list[0].name == "file03.ini"
    assert file_list[1].name == "file02.ini"
    assert file_list[2].name == "file04.ini"
    assert file_list[3].name == "file01.ini"


def test_resolve_dependencies_http(tmp_path):
    from mxdev.including import resolve_dependencies

    base = pathlib.Path(__file__).parent / "data"
    file_list = resolve_dependencies(base / "file_with_http_include01.ini", tmp_path)


def test_resolve_dependencies_filenotfound(tmp_path):
    from mxdev.including import resolve_dependencies

    base = pathlib.Path(__file__).parent / "data"
    with pytest.raises(FileNotFoundError):
        resolve_dependencies(base / "file__not_found.ini", tmp_path)
