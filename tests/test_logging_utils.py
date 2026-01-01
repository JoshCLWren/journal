"""Tests for utils/logging_utils.py."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.logging_utils import get_logger, setup_logging


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration between tests."""
    yield
    logging.getLogger().handlers.clear()


class TestSetupLogging:
    """Tests for setup_logging()."""

    def test_creates_log_directory(self, tmp_path):
        """Test that log directory is created."""
        setup_logging(tmp_path)
        assert tmp_path.exists()
        assert tmp_path.is_dir()

    @patch("logging.FileHandler")
    def test_creates_file_handler(self, mock_handler, tmp_path):
        """Test that file handler is created."""
        mock_file_handler = MagicMock()
        mock_handler.return_value = mock_file_handler

        setup_logging(tmp_path)

        mock_handler.assert_called_once()
        call_args = mock_handler.call_args[0]
        assert isinstance(call_args[0], Path)
        assert call_args[0].parent == tmp_path

    def test_sets_up_console_handler(self, tmp_path):
        """Test that console handler is created."""
        setup_logging(tmp_path)

        root_logger = logging.getLogger()
        handlers = root_logger.handlers
        assert len(handlers) >= 1

        console_handlers = [h for h in handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) > 0

    def test_sets_logging_level(self, tmp_path):
        """Test that logging level is configured."""
        setup_logging(tmp_path, level=logging.DEBUG)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_default_logging_level(self, tmp_path):
        """Test default logging level is INFO."""
        setup_logging(tmp_path)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_file_handler_level(self, tmp_path):
        """Test that file handler is set to DEBUG."""
        setup_logging(tmp_path)

        root_logger = logging.getLogger()
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) > 0
        assert file_handlers[0].level == logging.DEBUG

    def test_console_handler_level(self, tmp_path):
        """Test that console handler is created with level parameter."""
        setup_logging(tmp_path, level=logging.WARNING)

        root_logger = logging.getLogger()
        console_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) > 0


class TestGetLogger:
    """Tests for get_logger()."""

    def test_get_logger_by_name(self):
        """Test retrieving logger by name."""
        logger = get_logger("test.logger")
        assert logger.name == "test.logger"

    def test_get_logger_returns_logging_instance(self):
        """Test that get_logger returns logging.Logger instance."""
        logger = get_logger("test.logger")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_same_instance(self):
        """Test that get_logger returns same instance for same name."""
        logger1 = get_logger("test.logger")
        logger2 = get_logger("test.logger")
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test that get_logger returns different instances for different names."""
        logger1 = get_logger("test.logger1")
        logger2 = get_logger("test.logger2")
        assert logger1 is not logger2
        assert logger1.name == "test.logger1"
        assert logger2.name == "test.logger2"

    def test_get_logger_without_setup(self):
        """Test get_logger works without prior setup_logging call."""
        logger = get_logger("standalone.logger")
        assert logger.name == "standalone.logger"
