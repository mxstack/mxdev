from .config import Configuration  # noqa
from .hooks import Hook  # noqa
from .hooks import load_hooks  # noqa
from .hooks import read_hooks  # noqa
from .logging import setup_logger  # noqa
from .main import main
from .processing import read  # noqa
from .state import State  # noqa


if __name__ == "__main__":  # pragma: no cover
    main()
