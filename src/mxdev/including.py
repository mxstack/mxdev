from .logging import logger
from configparser import ConfigParser
from configparser import ExtendedInterpolation
from pathlib import Path
from urllib import parse
from urllib import request
from urllib.error import HTTPError

import os
import tempfile


def resolve_dependencies(
    file_or_url: str | Path,
    tmpdir: str,
    http_parent=None,
    optional: bool = False,
) -> list[Path]:
    """Resolve dependencies of a file or url

    Return included paths before their parent, so parent settings take precedence.

    Follow "include" and "include-optional" under the "[settings]" section.
    If optional, skip a missing file or HTTP 404 for this input only.
    """
    if isinstance(file_or_url, str):
        if http_parent:
            file_or_url = parse.urljoin(http_parent, file_or_url)
        parsed = parse.urlparse(str(file_or_url))
        # Check if it's a real URL scheme (not a Windows drive letter)
        # Windows drive letters are single characters, URL schemes are longer
        is_url = parsed.scheme and len(parsed.scheme) > 1
        if is_url:
            try:
                with request.urlopen(str(file_or_url)) as fio:
                    with tempfile.NamedTemporaryFile(
                        suffix=".ini",
                        dir=str(tmpdir),
                        delete=False,
                    ) as tf:
                        tf.write(fio.read())
                        file = Path(tf.name)
            except HTTPError as e:
                if optional and e.code == 404:
                    logger.info("Skipping missing optional include: %s", file_or_url)
                    return []
                logger.error("Error %s for URL: %s", e.code, e.url)
                raise
            http_parent = parse.urljoin(str(file_or_url), ".")
        else:
            file = Path(file_or_url)
    else:
        file = file_or_url
    cfg = ConfigParser()
    try:
        with file.open() as fio:
            cfg.read_file(fio)
    except FileNotFoundError:
        if not optional:
            raise
        logger.info("Skipping missing optional include: %s", file_or_url)
        return []
    if "settings" not in cfg:
        return [file]
    file_list = []
    for directive in ("include", "include-optional"):
        for include in cfg["settings"].get(directive, "").splitlines():
            include = include.strip()
            if not include:
                continue
            # Check if it's a real URL scheme (not a Windows drive letter)
            parsed_include = parse.urlparse(include)
            is_include_url = parsed_include.scheme and len(parsed_include.scheme) > 1
            if http_parent or is_include_url:
                file_list += resolve_dependencies(
                    file_or_url=include,
                    tmpdir=tmpdir,
                    http_parent=http_parent,
                    optional=directive == "include-optional",
                )
            else:
                file_list += resolve_dependencies(
                    file_or_url=file.parent / include,
                    tmpdir=tmpdir,
                    optional=directive == "include-optional",
                )

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
        resolved = resolve_dependencies(
            file_or_url=file_or_url,
            tmpdir=tmpdir,
        )
        cfg.read(resolved)
    return cfg
