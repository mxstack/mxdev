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


def test_resolve_dependencies_http(tmp_path, httpretty):
    from mxdev.including import resolve_dependencies

    base = pathlib.Path(__file__).parent / "data"
    with open(base / "file_with_http_include02.ini") as fio:
        httpretty.register_uri(
            httpretty.GET,
            "http://www.example.com/file_with_http_include02.ini",
            fio.read(),
            status=200,
        )
    with open(base / "file_with_http_include03.ini") as fio:
        httpretty.register_uri(
            httpretty.GET,
            "http://www.example.com/file_with_http_include03.ini",
            fio.read(),
            status=200,
        )
    file_list = resolve_dependencies(base / "file_with_http_include01.ini", tmp_path)
    assert len(file_list) == 4


def test_resolve_dependencies_filenotfound(tmp_path):
    from mxdev.including import resolve_dependencies

    base = pathlib.Path(__file__).parent / "data"
    with pytest.raises(FileNotFoundError):
        resolve_dependencies(base / "file__not_found.ini", tmp_path)


def test_read_with_included():
    from mxdev.including import read_with_included

    base = pathlib.Path(__file__).parent / "data"
    cfg = read_with_included(base / "file01.ini")
    assert cfg["settings"]["test"] == "1"
    assert cfg["settings"]["unique_1"] == "1"
    assert cfg["settings"]["unique_2"] == "2"
    assert cfg["settings"]["unique_3"] == "3"
    assert cfg["settings"]["unique_4"] == "4"
