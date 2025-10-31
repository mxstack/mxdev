from .config import Configuration
from .config import to_bool
from .hooks import load_hooks
from .hooks import read_hooks
from .hooks import write_hooks
from .logging import logger
from .logging import setup_logger
from .processing import fetch
from .processing import read
from .processing import write
from .state import State


try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown (not installed)"

import argparse
import logging
import sys


parser = argparse.ArgumentParser(
    description="Make it easy to work with Python projects containing lots "
    "of packages, of which you only want to develop some.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "-c",
    "--configuration",
    help="configuration file in INI format",
    type=str,
    default="mx.ini",
)
parser.add_argument(
    "-n",
    "--no-fetch",
    help="Skip VCS checkout/update; regenerate files from existing sources (error if missing)",
    action="store_true",
)
parser.add_argument("-f", "--fetch-only", help="Only perform VCS operations; skip file generation", action="store_true")
parser.add_argument(
    "-o",
    "--offline",
    help="Work offline; skip VCS and HTTP fetches; use cached files (tolerate missing)",
    action="store_true",
)
parser.add_argument(
    "-t",
    "--threads",
    help="Number of threads to fetch sources in parallel with",
    type=int,
)
parser.add_argument("-s", "--silent", help="Reduce verbosity", action="store_true")
parser.add_argument("-v", "--verbose", help="Increase verbosity", action="store_true")
parser.add_argument(
    "--version",
    action="version",
    version=f"%(prog)s {__version__}",
)


def supports_unicode() -> bool:
    """Check if stdout supports Unicode/emoji encoding.

    Returns True if the console encoding can handle Unicode emojis,
    False otherwise (e.g., cp1252 on Windows).
    """
    try:
        encoding = sys.stdout.encoding
        if not encoding:
            return False
        # Test if the encoding can handle the cake emoji
        "🎂".encode(encoding)
        return True
    except (AttributeError, UnicodeEncodeError, LookupError):
        return False


def main() -> None:
    args = parser.parse_args()
    loglevel = logging.INFO
    if not args.silent and args.verbose:
        loglevel = logging.INFO
    elif not args.verbose and args.silent:
        loglevel = logging.WARNING
    setup_logger(loglevel)
    logger.info("#" * 79)
    hooks = load_hooks()
    logger.info("# Load configuration")
    override_args = {}
    if args.offline:
        override_args["offline"] = True
    if args.threads:
        override_args["threads"] = args.threads
    configuration = Configuration(
        mxini=args.configuration,
        override_args=override_args,
        hooks=hooks,
    )
    state = State(configuration=configuration)
    logger.info("#" * 79)
    logger.info("# Read infiles")
    read(state)
    if not args.fetch_only:
        read_hooks(state, hooks)
    # Skip fetch if --no-fetch flag is set OR if offline mode is enabled
    offline = to_bool(state.configuration.settings.get("offline", False))
    if not args.no_fetch and not offline:
        fetch(state)
    if args.fetch_only:
        return
    write(state)
    write_hooks(state, hooks)
    out_requirements = state.configuration.out_requirements
    # Use emoji only if console encoding supports it (avoid cp1252 errors on Windows)
    prefix = "🎂 " if supports_unicode() else ""
    logger.info(f"{prefix}You are now ready for: pip install -r {out_requirements}")
    logger.info("   (path to pip may vary dependent on your installation method)")
