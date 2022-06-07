import logging
import sys


logger = logging.getLogger("mxdev")


def setup_logger(level: int) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    if level == logging.DEBUG:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
    root.addHandler(handler)
