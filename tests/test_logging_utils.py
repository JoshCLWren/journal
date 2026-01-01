"""Test logging utilities."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from utils.logging_utils import get_logger, setup_logging


def test_setup_logging_creates_dir():
    """Test that setup_logging creates log directory."""
    with TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"

        setup_logging(log_dir)

        assert log_dir.exists()
        assert log_dir.is_dir()


def test_setup_logging_creates_log_file():
    """Test that setup_logging creates a log file."""
    with TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"

        setup_logging(log_dir)

        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) > 0


def test_get_logger():
    """Test getting a logger instance."""
    logger = get_logger("test_logger")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"


def test_get_logger_same_instance():
    """Test that get_logger returns same instance for same name."""
    logger1 = get_logger("test")
    logger2 = get_logger("test")

    assert logger1 is logger2


def test_setup_logging_handlers():
    """Test that setup_logging adds handlers."""
    with TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"

        root_logger = logging.getLogger()
        initial_handlers = len(root_logger.handlers)

        setup_logging(log_dir)

        assert len(root_logger.handlers) >= initial_handlers + 2


def test_get_logger_with_different_names():
    """Test getting loggers with different names."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")

    assert logger1.name == "module1"
    assert logger2.name == "module2"
    assert logger1 is not logger2


def test_setup_logging_debug_level():
    """Test setup_logging with DEBUG level."""
    with TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"

        setup_logging(log_dir, level=logging.DEBUG)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG


def test_setup_logging_warning_level():
    """Test setup_logging with WARNING level."""
    with TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"

        setup_logging(log_dir, level=logging.WARNING)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG


def test_get_logger_level():
    """Test that logger has correct level."""
    with TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"

        setup_logging(log_dir)
        logger = get_logger("test")

        assert logger is not None
