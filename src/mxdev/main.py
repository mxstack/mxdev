from .config import Configuration
from .hooks import load_hooks
from .hooks import read_hooks
from .hooks import write_hooks
from .logging import logger
from .logging import setup_logger
from .processing import fetch
from .processing import read
from .processing import write
from .state import State

import argparse
import logging


parser = argparse.ArgumentParser(
    description="Make it easy to work with Python projects containing lots "
    "of packages, of which you only want to develop some.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "-c",
    "--configuration",
    help="configuration file in INI format",
    nargs="?",
    type=argparse.FileType("r"),
    required=True,
)
parser.add_argument(
    "-n", "--no-fetch", help="Do not fetch sources", action="store_true"
)
parser.add_argument(
    "-o", "--only-fetch", help="Only fetch sources", action="store_true"
)
parser.add_argument("-s", "--silent", help="Reduce verbosity", action="store_true")
parser.add_argument("-v", "--verbose", help="Increase verbosity", action="store_true")


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
    configuration = Configuration(tio=args.configuration, hooks=hooks)
    state = State(configuration=configuration)
    logger.info("#" * 79)
    logger.info("# Read infiles")
    read(state)
    if not args.only_fetch:
        read_hooks(state, hooks)
    if not args.no_fetch:
        fetch(state)
    if args.only_fetch:
        return
    write(state)
    write_hooks(state, hooks)
    out_requirements = state.configuration.out_requirements
    logger.info(f"🎂 You are now ready for: pip install -r {out_requirements}")
    logger.info("   (path to pip may vary dependent on your installation method)")
