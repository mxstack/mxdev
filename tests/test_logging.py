import io
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


def test_emoji_logging_with_cp1252_encoding(capsys, caplog):
    """Test that logging emojis with cp1252 encoding raises UnicodeEncodeError.

    This reproduces the Windows CI error where the console uses cp1252 encoding
    which cannot handle Unicode emojis like 🎂.

    Error from Windows CI:
    UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f382'
    in position 0: character maps to <undefined>
    """
    from mxdev.logging import logger

    # Clear any existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    # Create a stream with cp1252 encoding (simulating Windows console)
    # Use errors='strict' to ensure it raises on unencodable characters
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict", line_buffering=True)

    # Set up handler with the cp1252 stream
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # This is the exact emoji from main.py:81 that causes the issue
    emoji_message = "🎂 You are now ready for: pip install -r requirements-mxdev.txt"

    # When logging fails due to encoding, Python's logging module catches
    # the error and prints it to stderr via handleError(), but doesn't raise
    logger.info(emoji_message)

    # Capture stderr to check for the encoding error
    captured = capsys.readouterr()

    # Verify the UnicodeEncodeError was logged to stderr
    assert "UnicodeEncodeError" in captured.err
    assert "charmap" in captured.err or "cp1252" in captured.err
    assert "\\U0001f382" in captured.err or "U0001f382" in captured.err
    assert emoji_message in captured.err

    # Clean up
    root.handlers.clear()
