import logging
import sys


def test_logger_exists():
    """Test that logger is created."""
    from mxdev.logging import logger

    assert logger is not None
    assert logger.name == "mxdev"


def test_setup_logger_info():
    """Test setup_logger with INFO level."""
    from mxdev.logging import setup_logger

    # Clear any existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    setup_logger(logging.INFO)

    assert root.level == logging.INFO
    assert len(root.handlers) > 0

    handler = root.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.level == logging.INFO
    assert handler.stream == sys.stdout


def test_setup_logger_warning():
    """Test setup_logger with WARNING level."""
    from mxdev.logging import setup_logger

    # Clear any existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    setup_logger(logging.WARNING)

    assert root.level == logging.WARNING
    assert len(root.handlers) > 0

    handler = root.handlers[0]
    assert handler.level == logging.WARNING


def test_setup_logger_debug():
    """Test setup_logger with DEBUG level sets formatter."""
    from mxdev.logging import setup_logger

    # Clear any existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    setup_logger(logging.DEBUG)

    assert root.level == logging.DEBUG
    assert len(root.handlers) > 0

    handler = root.handlers[0]
    assert handler.level == logging.DEBUG
    # DEBUG level should have a formatter set
    assert handler.formatter is not None
    assert "%(asctime)s" in handler.formatter._fmt


def test_setup_logger_error():
    """Test setup_logger with ERROR level."""
    from mxdev.logging import setup_logger

    # Clear any existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    setup_logger(logging.ERROR)

    assert root.level == logging.ERROR
    assert len(root.handlers) > 0

    handler = root.handlers[0]
    assert handler.level == logging.ERROR


def test_setup_logger_no_formatter_for_info():
    """Test that INFO level does not have formatter."""
    from mxdev.logging import setup_logger

    # Clear any existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    setup_logger(logging.INFO)

    handler = root.handlers[0]
    # Non-DEBUG levels should not have a formatter or have default formatter
    # The code only sets formatter for DEBUG
    if handler.formatter:
        # If a formatter exists, it shouldn't be the DEBUG formatter
        assert "%(asctime)s" not in handler.formatter._fmt or handler.formatter._fmt is None
