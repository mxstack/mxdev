from configparser import ConfigParser
from configparser import ExtendedInterpolation
from pathlib import Path
from urllib import parse
from urllib import request

import os
import tempfile


def resolve_dependencies(
    file_or_url: str | Path,
    tmpdir: str,
    http_parent=None,
) -> list[Path]:
    """Resolve dependencies of a file or url

    The result is a list of Path objects, starting with the
    given file_or_url and followed by all file_or_urls referenced from it.

    The file_or_url is assumed to be a ini file or url to such, with an option key "include"
    under the "[settings]" section.
    """
    if isinstance(file_or_url, str):
        if http_parent:
            file_or_url = parse.urljoin(http_parent, file_or_url)
        parsed = parse.urlparse(str(file_or_url))
        # Check if it's a real URL scheme (not a Windows drive letter)
        # Windows drive letters are single characters, URL schemes are longer
        is_url = parsed.scheme and len(parsed.scheme) > 1
        if is_url:
            with request.urlopen(str(file_or_url)) as fio:
                tf = tempfile.NamedTemporaryFile(
                    suffix=".ini",
                    dir=str(tmpdir),
                    delete=False,
                )
                tf.write(fio.read())
                tf.flush()
                file = Path(tf.name)
            parts = list(parsed)
            parts[2] = str(Path(parts[2]).parent)
            http_parent = parse.urlunparse(parts)
        else:
            file = Path(file_or_url)
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
        # Check if it's a real URL scheme (not a Windows drive letter)
        parsed_include = parse.urlparse(include)
        is_include_url = parsed_include.scheme and len(parsed_include.scheme) > 1
        if http_parent or is_include_url:
            file_list += resolve_dependencies(include, tmpdir, http_parent)
        else:
            file_list += resolve_dependencies(file.parent / include, tmpdir)

    file_list.append(file)
    return file_list


def read_with_included(file_or_url: str | Path) -> ConfigParser:
    """Read a file or url and include all referenced files,

    Parse the result as a ConfigParser and return it.
    """
    cfg = ConfigParser(
        default_section="settings",
        interpolation=ExtendedInterpolation(),
    )
    cfg.optionxform = str  # type: ignore
    cfg["settings"]["directory"] = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        resolved = resolve_dependencies(file_or_url, tmpdir)
        cfg.read(resolved)
    return cfg
