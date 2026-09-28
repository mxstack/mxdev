import pathlib
import pytest


def test_optional_includes_and_precedence(tmp_path):
    from mxdev.including import read_with_included

    (tmp_path / "required.ini").write_text("[settings]\nvalue = required\n")
    (tmp_path / "nested.ini").write_text("[settings]\nnested = yes\n")
    (tmp_path / "custom.ini").write_text(
        "[settings]\ninclude = nested.ini\ninclude-optional = absent.ini\nvalue = optional\nmain = optional\n"
    )
    main = tmp_path / "mx.ini"
    main.write_text(
        "[settings]\ninclude = required.ini\ninclude-optional =\n    missing.ini\n    custom.ini\nmain = main\n"
    )
    cfg = read_with_included(main)
    assert cfg["settings"]["value"] == "optional"
    assert cfg["settings"]["main"] == "main"
    assert cfg["settings"]["nested"] == "yes"


def test_optional_include_preserves_required_nested_failure(tmp_path):
    from mxdev.including import read_with_included

    main = tmp_path / "mx.ini"
    main.write_text("[settings]\ninclude-optional = custom.ini\n")
    (tmp_path / "custom.ini").write_text("[settings]\ninclude = missing.ini\n")
    with pytest.raises(FileNotFoundError):
        read_with_included(main)


@pytest.mark.parametrize("directive", ["include", "include-optional"])
@pytest.mark.parametrize("status", [404, 403, 500])
def test_include_http_errors(tmp_path, httpretty, directive, status):
    from mxdev.including import read_with_included
    from urllib.error import HTTPError

    url = "http://example.com/custom.ini"
    httpretty.register_uri(httpretty.GET, url, status=status)
    main = tmp_path / "mx.ini"
    main.write_text(f"[settings]\n{directive} = {url}\nvalue = main\n")
    if directive == "include-optional" and status == 404:
        assert read_with_included(main)["settings"]["value"] == "main"
    else:
        with pytest.raises(HTTPError) as exc:
            read_with_included(main)
        assert exc.value.code == status


@pytest.mark.parametrize("directive", ["include", "include-optional"])
def test_http_relative_include(tmp_path, httpretty, directive):
    from mxdev.including import read_with_included

    url = "http://example.com/config/mx.ini"
    httpretty.register_uri(httpretty.GET, url, body=f"[settings]\n{directive} = custom.ini\n")
    httpretty.register_uri(httpretty.GET, "http://example.com/config/custom.ini", body="[settings]\ncustom = yes\n")
    assert read_with_included(url)["settings"]["custom"] == "yes"


def test_optional_include_connection_error(tmp_path, monkeypatch):
    from mxdev.including import read_with_included
    from urllib.error import URLError

    main = tmp_path / "mx.ini"
    main.write_text("[settings]\ninclude-optional = https://example.com/custom.ini\n")

    def fail(url):
        raise URLError("Connection failed")

    monkeypatch.setattr("mxdev.including.request.urlopen", fail)
    with pytest.raises(URLError, match="Connection failed"):
        read_with_included(main)


def test_optional_include_invalid_ini(tmp_path):
    from configparser import MissingSectionHeaderError
    from mxdev.including import read_with_included

    main = tmp_path / "mx.ini"
    main.write_text("[settings]\ninclude-optional = custom.ini\n")
    (tmp_path / "custom.ini").write_text("invalid ini\n")
    with pytest.raises(MissingSectionHeaderError):
        read_with_included(main)


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


def test_resolve_dependencies_windows_path(tmp_path):
    """Test that Windows absolute paths with drive letters are handled correctly.

    On Windows, paths like 'D:\\path\\to\\file.ini' should be treated as
    file paths, not URLs (even though urlparse() interprets 'D:' as a scheme).
    """
    from mxdev.including import resolve_dependencies

    # Create a test file with no includes
    test_file = tmp_path / "test_config.ini"
    test_file.write_text("[settings]\ntest = value\n")

    # Test with the actual path (on Windows this would be like D:\...\test_config.ini)
    file_list = resolve_dependencies(str(test_file), str(tmp_path))
    assert len(file_list) == 1
    assert file_list[0] == test_file
