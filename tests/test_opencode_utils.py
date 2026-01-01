"""Tests for utils/opencode_utils.py."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from utils.opencode_utils import (
    check_opencode_client,
    ensure_opencode_running,
    get_opencode_client_path,
    is_opencode_running,
    start_opencode_server,
)


class TestIsOpenCodeRunning:
    """Tests for is_opencode_running()."""

    @patch("subprocess.run")
    def test_running_server(self, mock_run):
        """Test detection of running OpenCode server."""
        mock_run.return_value = MagicMock(returncode=0)
        result = is_opencode_running("http://127.0.0.1:4096")
        assert result is True
        mock_run.assert_called_once_with(
            ["curl", "-s", "http://127.0.0.1:4096/global/health"],
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch("subprocess.run")
    def test_not_running_server(self, mock_run):
        """Test detection when server is not running."""
        mock_run.return_value = MagicMock(returncode=1)
        result = is_opencode_running("http://127.0.0.1:4096")
        assert result is False

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired("curl", 5))
    def test_timeout_returns_false(self, mock_run):
        """Test that timeout returns False."""
        result = is_opencode_running("http://127.0.0.1:4096")
        assert result is False

    @patch("subprocess.run", side_effect=FileNotFoundError("curl not found"))
    def test_curl_not_found_returns_false(self, mock_run):
        """Test that missing curl returns False."""
        result = is_opencode_running("http://127.0.0.1:4096")
        assert result is False


class TestStartOpenCodeServer:
    """Tests for start_opencode_server()."""

    @patch("utils.opencode_utils.is_opencode_running")
    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_successful_start(self, mock_popen, mock_run, mock_check):
        """Test successful OpenCode server start."""
        mock_run.return_value = MagicMock(returncode=0, stdout="/usr/bin/opencode")
        mock_popen.return_value = MagicMock()
        mock_check.return_value = True

        result = start_opencode_server()
        assert result is True
        mock_popen.assert_called_once()

    @patch("subprocess.run")
    def test_opencode_not_found(self, mock_run):
        """Test when opencode command is not found."""
        mock_run.return_value = MagicMock(returncode=1)

        result = start_opencode_server()
        assert result is False

    @patch("utils.opencode_utils.is_opencode_running", return_value=False)
    @patch("subprocess.run")
    @patch("subprocess.Popen")
    @patch("time.sleep")
    def test_server_fails_to_start(self, mock_sleep, mock_popen, mock_run, mock_check):
        """Test when server fails to start."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_popen.return_value = MagicMock()

        result = start_opencode_server()
        assert result is False

    @patch("utils.opencode_utils.is_opencode_running")
    @patch("subprocess.run")
    @patch("subprocess.Popen", side_effect=Exception("start error"))
    def test_exception_during_start(self, mock_popen, mock_run, mock_check):
        """Test exception during server start."""
        mock_run.return_value = MagicMock(returncode=0)

        result = start_opencode_server()
        assert result is False


class TestEnsureOpenCodeRunning:
    """Tests for ensure_opencode_running()."""

    @patch("utils.opencode_utils.is_opencode_running", return_value=True)
    def test_already_running(self, mock_check):
        """Test when server is already running."""
        result = ensure_opencode_running()
        assert result is True
        mock_check.assert_called_once()

    @patch("utils.opencode_utils.start_opencode_server", return_value=True)
    @patch("utils.opencode_utils.is_opencode_running", return_value=False)
    def test_starts_server(self, mock_check, mock_start):
        """Test starting server when not running."""
        result = ensure_opencode_running()
        assert result is True
        mock_start.assert_called_once()

    @patch("utils.opencode_utils.start_opencode_server", return_value=False)
    @patch("utils.opencode_utils.is_opencode_running", return_value=False)
    def test_server_start_fails(self, mock_check, mock_start):
        """Test when server start fails."""
        result = ensure_opencode_running()
        assert result is False

    @patch("utils.opencode_utils.start_opencode_server")
    @patch("utils.opencode_utils.is_opencode_running", return_value=False)
    def test_custom_url(self, mock_check, mock_start, capsys):
        """Test ensure_opencode_running with custom URL."""
        mock_start.return_value = True
        ensure_opencode_running("http://custom:8080")
        captured = capsys.readouterr()
        assert "Starting OpenCode server" in captured.out


class TestGetOpenCodeClientPath:
    """Tests for get_opencode_client_path()."""

    def test_returns_path_to_client(self):
        """Test that correct path to client is returned."""
        result = get_opencode_client_path()
        assert isinstance(result, Path)
        assert result.name == "opencode_client.py"

    def test_path_is_absolute(self):
        """Test that returned path is absolute."""
        result = get_opencode_client_path()
        assert result.is_absolute()


class TestCheckOpenCodeClient:
    """Tests for check_opencode_client()."""

    @patch("utils.opencode_utils.get_opencode_client_path")
    def test_client_exists(self, mock_path):
        """Test when client file exists."""
        mock_path.return_value = MagicMock(exists=lambda: True)
        result = check_opencode_client()
        assert result is True

    @patch("utils.opencode_utils.get_opencode_client_path")
    def test_client_missing(self, mock_path):
        """Test when client file does not exist."""
        mock_path.return_value = MagicMock(exists=lambda: False)
        result = check_opencode_client()
        assert result is False

    @patch("utils.opencode_utils.get_opencode_client_path")
    def test_client_path_format(self, mock_path, capsys):
        """Test that error message includes client path."""
        mock_path.return_value = Path("/custom/path/to/opencode_client.py")
        result = check_opencode_client()
        assert result is False
        captured = capsys.readouterr()
        assert "opencode_client.py" in captured.out
