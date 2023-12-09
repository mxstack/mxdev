from configparser import ConfigParser
from urllib import request
from urllib import parse

import pathlib
import tempfile


def resolve_dependencies(
    file_or_url: str | pathlib.Path, tmpdir: tempfile.TemporaryDirectory, http_parent=None,
) -> list[pathlib.Path]:
    """Resolve dependencies of a file or url

    The result is a list of pathlib.Path objects, starting with the
    given file_or_url and followed by all file_or_urls referenced from it.

    The file_or_url is assumed to be a ini file or url to such, with an option key "include"
    under the "[settings]" section.
    """
    if isinstance(file_or_url, str):
        if http_parent:
            file_or_url = parse.urljoin(http_parent, file_or_url)
        parsed = parse.urlparse(file_or_url)
        if parsed.scheme:
            with request.urlopen(file_or_url) as fio:
                tf = tempfile.NamedTemporaryFile(suffix=".ini", dir=tmpdir)
                tf.write(fio.read())
                tf.flush()
                file = pathlib.Path(tf.name)
            parts = list(parsed.parts)
            parts[2] = str(pathlib.Path(parts[2]).parent)
            http_parent = parse.urlunparse(parsed.parts)
        else:
            file = pathlib.Path(file)
    else:
        file = file_or_url
    if not file.exists():
        raise FileNotFoundError(file)
    cfg = ConfigParser()
    cfg.read(file)
    if not ("settings" in cfg and "include" in cfg["settings"]):
        return [file]
    file_list = []
    for include in cfg["settings"]["include"].split("\n"):
        include = include.strip()
        if not include:
            continue
        if http_parent or parse.urlparse(include).scheme:
            file_list += resolve_dependencies(include, tmpdir, http_parent)
        else:
            file_list += resolve_dependencies(file.parent / include, tmpdir)

    file_list.append(file)
    return file_list


def read_with_included(file_or_url: str | pathlib.Path) -> ConfigParser:
    """Read a file or url and include all referenced files,

    Parse the result as a ConfigParser and return it.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        resolved = resolve_dependencies(file_or_url, tmpdir)
        cfg = ConfigParser()
        cfg.read(resolved)
        return cfg
