from logging import getLogger
from logging import Logger

import pytest


logger: Logger = getLogger("schas")


def test_schas(caplog, tmpdir):
    logger.warning(f"oops {tmpdir}")

    print("asdsad")
