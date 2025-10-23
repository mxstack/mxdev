from .logging import logger
from .state import State
from .vcs.common import WorkingCopies
from packaging.requirements import Requirement
from pathlib import Path
from urllib import parse
from urllib import request
from urllib.error import URLError

import hashlib
import os
import typing


def _get_cache_key(url: str) -> str:
    """Generate a deterministic cache key from a URL.

    Uses SHA256 hash of the URL, truncated to 16 hex characters for readability
    while maintaining low collision probability.

    Args:
        url: The URL to generate a cache key for

    Returns:
        16-character hex string (cache key)

    """
    hash_obj = hashlib.sha256(url.encode("utf-8"))
    return hash_obj.hexdigest()[:16]


def _cache_http_content(url: str, content: str, cache_dir: Path) -> None:
    """Cache HTTP content to disk.

    Args:
        url: The URL being cached
        content: The content to cache
        cache_dir: Directory to store cache files

    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = _get_cache_key(url)

    # Write content
    cache_file = cache_dir / cache_key
    cache_file.write_text(content, encoding="utf-8")

    # Write URL metadata for debugging
    url_file = cache_dir / f"{cache_key}.url"
    url_file.write_text(url, encoding="utf-8")

    logger.debug(f"Cached {url} to {cache_file}")


def _read_from_cache(url: str, cache_dir: Path) -> str | None:
    """Read cached HTTP content from disk.

    Args:
        url: The URL to look up in cache
        cache_dir: Directory containing cache files

    Returns:
        Cached content if found, None otherwise

    """
    if not cache_dir.exists():
        return None

    cache_key = _get_cache_key(url)
    cache_file = cache_dir / cache_key

    if cache_file.exists():
        logger.debug(f"Cache hit for {url} from {cache_file}")
        return cache_file.read_text(encoding="utf-8")

    return None


def process_line(
    line: str,
    package_keys: list[str],
    override_keys: list[str],
    ignore_keys: list[str],
    variety: str,
    offline: bool = False,
    cache_dir: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Take line from a constraints or requirements file and process it recursively.

    The line is taken as is unless one of the following cases matches:

    is a constraint or requirements file reference (as file or http(s))
        trigger resolving/recursive processing (open/download) the reference
        and process it.

    is in package_keys, override_keys or ignore_keys
        prefix the line as comment with reason appended

    returns tuple of requirements and constraints
    """
    if isinstance(line, bytes):
        line = line.decode("utf8")
    logger.debug(f"Process Line [{variety}]: {line.strip()}")
    if line.startswith("-c"):
        return resolve_dependencies(
            line.split(" ")[1].strip(),
            package_keys=package_keys,
            override_keys=override_keys,
            ignore_keys=ignore_keys,
            variety="c",
            offline=offline,
            cache_dir=cache_dir,
        )
    elif line.startswith("-r"):
        return resolve_dependencies(
            line.split(" ")[1].strip(),
            package_keys=package_keys,
            override_keys=override_keys,
            ignore_keys=ignore_keys,
            variety="r",
            offline=offline,
            cache_dir=cache_dir,
        )
    try:
        parsed = Requirement(line)
    except Exception:
        pass
    else:
        parsed_name_lower = parsed.name.lower()
        if parsed_name_lower in [k.lower() for k in package_keys]:
            line = f"# {line.strip()} -> mxdev disabled (source)\n"
        if parsed_name_lower in [k.lower() for k in override_keys]:
            if variety == "c":
                line = f"# {line.strip()} -> mxdev disabled (override)\n"
            else:
                line = f"# {line.strip()} -> mxdev disabled (version override)\n"
        if parsed_name_lower in [k.lower() for k in ignore_keys]:
            line = f"# {line.strip()} -> mxdev disabled (ignore)\n"
    if variety == "c":
        return [], [line]
    return [line], []


def process_io(
    fio: typing.IO,
    requirements: list[str],
    constraints: list[str],
    package_keys: list[str],
    override_keys: list[str],
    ignore_keys: list[str],
    variety: str,
    offline: bool = False,
    cache_dir: Path | None = None,
) -> None:
    """Read lines from an open file and trigger processing of each line

    each line is processed and the result appendend to given requirements
    and constraint lists.
    """
    for line in fio:
        new_requirements, new_constraints = process_line(
            line, package_keys, override_keys, ignore_keys, variety, offline, cache_dir
        )
        requirements += new_requirements
        constraints += new_constraints


def resolve_dependencies(
    file_or_url: str,
    package_keys: list[str],
    override_keys: list[str],
    ignore_keys: list[str],
    variety: str = "r",
    offline: bool = False,
    cache_dir: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Takes a file or url, loads it and trigger to recursivly processes its content.

    Args:
        file_or_url: Path to local file or HTTP(S) URL
        package_keys: List of package names being developed from source
        override_keys: List of package names with version overrides
        ignore_keys: List of package names to ignore
        variety: "r" for requirements, "c" for constraints
        offline: If True, use cached HTTP content and don't make network requests
        cache_dir: Directory for caching HTTP content (default: ./.mxdev_cache)

    Returns:
        Tuple of (requirements, constraints) as lists of strings

    """
    requirements: list[str] = []
    constraints: list[str] = []
    if not file_or_url.strip():
        logger.info("mxdev is configured to run without input requirements!")
        return ([], [])
    logger.info(f"Read [{variety}]: {file_or_url}")
    parsed = parse.urlparse(file_or_url)
    variety_verbose = "requirements" if variety == "r" else "constraints"
    # Check if it's a real URL scheme (not a Windows drive letter)
    # Windows drive letters are single characters, URL schemes are longer
    is_url = parsed.scheme and len(parsed.scheme) > 1

    # Default cache directory
    if cache_dir is None:
        cache_dir = Path(".mxdev_cache")

    if not is_url:
        requirements_in_file = Path(file_or_url)
        if requirements_in_file.exists():
            with requirements_in_file.open("r") as fio:
                process_io(
                    fio,
                    requirements,
                    constraints,
                    package_keys,
                    override_keys,
                    ignore_keys,
                    variety,
                    offline,
                    cache_dir,
                )
        else:
            logger.info(
                f"Can not read {variety_verbose} file '{file_or_url}', " "it does not exist. Empty file assumed."
            )
    else:
        # HTTP(S) URL handling with caching
        content: str
        if offline:
            # Offline mode: try to read from cache
            cached_content = _read_from_cache(file_or_url, cache_dir)
            if cached_content is None:
                raise RuntimeError(
                    f"Offline mode: HTTP reference '{file_or_url}' not found in cache. "
                    f"Run mxdev in online mode first to populate the cache at {cache_dir}"
                )
            content = cached_content
            logger.info(f"Using cached content for {file_or_url}")
        else:
            # Online mode: fetch from HTTP and cache it
            try:
                with request.urlopen(file_or_url) as fio:
                    content = fio.read().decode("utf-8")
                # Cache the content for future offline use
                _cache_http_content(file_or_url, content, cache_dir)
            except URLError as e:
                raise Exception(f"Failed to fetch '{file_or_url}': {e}")

        # Process the content (either from cache or fresh from HTTP)
        from io import StringIO

        with StringIO(content) as fio:
            process_io(
                fio,
                requirements,
                constraints,
                package_keys,
                override_keys,
                ignore_keys,
                variety,
                offline,
                cache_dir,
            )

    if requirements and variety == "r":
        requirements = (
            [
                "#" * 79 + "\n",
                f"# begin requirements from: {file_or_url}\n\n",
            ]
            + requirements
            + ["\n", f"# end requirements from: {file_or_url}\n", "#" * 79 + "\n"]
        )
    if constraints and variety == "c":
        constraints = (
            [
                "#" * 79 + "\n",
                f"# begin constraints from: {file_or_url}\n",
                "\n",
            ]
            + constraints
            + ["\n", f"# end constraints from: {file_or_url}\n", "#" * 79 + "\n\n"]
        )
    return (requirements, constraints)


def read(state: State) -> None:
    """Start reading and recursive processing of a requirements file

    The result is stored on the state object
    """
    from .config import to_bool

    cfg = state.configuration
    offline = to_bool(cfg.settings.get("offline", False))
    state.requirements, state.constraints = resolve_dependencies(
        file_or_url=cfg.infile,
        package_keys=cfg.package_keys,
        override_keys=cfg.override_keys,
        ignore_keys=cfg.ignore_keys,
        offline=offline,
    )


def fetch(state: State) -> None:
    """Fetch all configured sources from a VCS."""
    from .config import to_bool

    packages = state.configuration.packages
    logger.info("#" * 79)
    if not packages:
        logger.info("# No sources configured!")
        return

    logger.info("# Fetch sources from VCS")
    smart_threading = to_bool(state.configuration.settings.get("smart-threading", True))
    workingcopies = WorkingCopies(
        packages,
        threads=int(state.configuration.settings["threads"]),
        smart_threading=smart_threading,
    )
    # Pass offline setting from configuration instead of hardcoding False
    offline = to_bool(state.configuration.settings.get("offline", False))
    workingcopies.checkout(
        sorted(packages),
        verbose=False,
        update=True,
        submodules="always",
        always_accept_server_certificate=True,
        offline=offline,
    )


def write_dev_sources(fio, packages: dict[str, dict[str, typing.Any]], state: State):
    """Create requirements configuration for fetched source packages."""
    if not packages:
        return

    # Check if we're in offline mode or no-fetch mode
    from .config import to_bool

    offline_mode = to_bool(state.configuration.settings.get("offline", False))
    missing_sources = []  # Track missing sources for error handling

    fio.write("#" * 79 + "\n")
    fio.write("# mxdev development sources\n")

    for name, package in packages.items():
        if package["install-mode"] == "skip":
            continue

        # Check if source directory exists
        source_path = Path(package["path"])

        extras = f"[{package['extras']}]" if package["extras"] else ""
        subdir = f"/{package['subdirectory']}" if package["subdirectory"] else ""

        # Add -e prefix only for 'editable' mode (not for 'fixed')
        prefix = "-e " if package["install-mode"] == "editable" else ""
        install_line = f"""{prefix}./{package['target']}/{name}{subdir}{extras}"""

        if not source_path.exists():
            # Source not checked out yet - write as comment
            missing_sources.append(name)

            if offline_mode:
                # In offline mode, missing sources are expected - log as WARNING
                reason = (
                    f"Source directory does not exist: {source_path} (package: {name}). "
                    f"This is expected in offline mode. Run mxdev without -n and --offline flags to fetch sources."
                )
                logger.warning(reason)
            else:
                # In non-offline mode, missing sources are a fatal error - log as ERROR
                reason = (
                    f"Source directory does not exist: {source_path} (package: {name}). "
                    f"This indicates a failure in the checkout process. "
                    f"Run mxdev without -n flag to fetch sources."
                )
                logger.error(reason)

            fio.write(f"# {install_line}  # mxdev: source not checked out\n")
        else:
            # Source exists - write normally
            logger.debug(f"-> {install_line}")
            fio.write(f"{install_line}\n")

    fio.write("\n\n")

    # In non-offline mode, missing sources are a fatal error
    if not offline_mode and missing_sources:
        raise RuntimeError(
            f"Source directories missing for packages: {', '.join(missing_sources)}. "
            f"This indicates a failure in the checkout process. "
            f"Run mxdev without -n flag to fetch sources."
        )


def write_dev_overrides(fio, overrides: dict[str, str], package_keys: list[str]):
    """Create requirements configuration for overridden packages."""
    fio.write("#" * 79 + "\n")
    fio.write("# mxdev constraint overrides\n")
    for pkg, line in overrides.items():
        if pkg.lower() in [k.lower() for k in package_keys]:
            fio.write(f"# {line} IGNORE mxdev constraint override. Source override wins!\n")
        else:
            fio.write(f"{line}\n")
    fio.write("\n\n")


def write_main_package(fio, settings: dict[str, str]):
    """Write main package if configured."""
    main_package = settings.get("main-package")
    if main_package:
        fio.write("#" * 79 + "\n")
        fio.write("# main package\n")
        fio.write(f"{main_package}\n")


def write(state: State) -> None:
    """Write the requirements and constraints file according to information
    on the state
    """
    requirements = state.requirements
    constraints = state.constraints
    cfg = state.configuration
    logger.info("#" * 79)
    logger.info("# Write outfiles")
    if constraints or cfg.overrides:
        logger.info(f"Write [c]: {cfg.out_constraints}")
        with open(cfg.out_constraints, "w") as fio:
            fio.writelines(constraints)
            if cfg.overrides:
                write_dev_overrides(fio, cfg.overrides, cfg.package_keys)
    else:
        logger.info("No constraints, skip writing constraints file")
    logger.info(f"Write [r]: {cfg.out_requirements}")
    with open(cfg.out_requirements, "w") as fio:
        if constraints or cfg.overrides:
            # Calculate relative path from requirements-out directory to constraints-out file
            # This ensures pip can find the constraints file regardless of where requirements
            # and constraints files are located
            req_path = Path(cfg.out_requirements)
            const_path = Path(cfg.out_constraints)

            # Calculate relative path from requirements directory to constraints file
            try:
                constraints_ref = os.path.relpath(const_path, req_path.parent)
                # Convert backslashes to forward slashes for pip compatibility
                # pip expects forward slashes even on Windows
                constraints_ref = constraints_ref.replace("\\", "/")
            except ValueError:
                # On Windows, relpath can fail if paths are on different drives
                # In that case, use absolute path with forward slashes
                constraints_ref = str(const_path.absolute()).replace("\\", "/")

            fio.write("#" * 79 + "\n")
            fio.write("# mxdev combined constraints\n")
            fio.write(f"-c {constraints_ref}\n\n")
        write_dev_sources(fio, cfg.packages, state)
        fio.writelines(requirements)
        write_main_package(fio, cfg.settings)
