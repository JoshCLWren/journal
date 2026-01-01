"""Test OpenCode utility functions."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from utils.opencode_utils import (
    OPENCODE_DEFAULT_URL,
    check_opencode_client,
    ensure_opencode_running,
    get_opencode_client_path,
    is_opencode_running,
    start_opencode_server,
)


def test_is_opencode_running_true():
    """Test checking if OpenCode is running (positive case)."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        result = is_opencode_running()

        assert result is True
        mock_run.assert_called_once()


def test_is_opencode_running_false():
    """Test checking if OpenCode is running (negative case)."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)

        result = is_opencode_running()

        assert result is False


def test_is_opencode_running_timeout():
    """Test checking if OpenCode is running on timeout."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("curl", 5)

        result = is_opencode_running()

        assert result is False


def test_is_opencode_running_file_not_found():
    """Test checking if OpenCode is running when curl not found."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()

        result = is_opencode_running()

        assert result is False


def test_is_opencode_running_custom_url():
    """Test checking OpenCode with custom URL."""
    custom_url = "http://localhost:8080"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        result = is_opencode_running(custom_url)

        assert result is True
        args = mock_run.call_args[0][0]
        assert custom_url in args


def test_start_opencode_server_not_installed():
    """Test starting OpenCode when not installed."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)

        result = start_opencode_server()

        assert result is False


def test_start_opencode_server_success():
    """Test starting OpenCode server successfully."""
    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
        patch("utils.opencode_utils.is_opencode_running") as mock_check,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="/usr/bin/opencode")
        mock_popen.return_value = MagicMock()
        mock_check.return_value = True

        result = start_opencode_server()

        assert result is True


def test_start_opencode_server_fails_to_start():
    """Test starting OpenCode when server fails to start."""
    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
        patch("utils.opencode_utils.is_opencode_running") as mock_check,
        patch("time.sleep"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        mock_popen.return_value = MagicMock()
        mock_check.return_value = False

        result = start_opencode_server()

        assert result is False


def test_ensure_opencode_running_already_running():
    """Test ensuring OpenCode is running when it already is."""
    with patch("utils.opencode_utils.is_opencode_running") as mock_check:
        mock_check.return_value = True

        result = ensure_opencode_running()

        assert result is True


def test_ensure_opencode_running_starts():
    """Test ensuring OpenCode is running when it needs to start."""
    with (
        patch("utils.opencode_utils.is_opencode_running") as mock_check,
        patch("utils.opencode_utils.start_opencode_server") as mock_start,
    ):
        mock_check.return_value = False
        mock_start.return_value = True

        result = ensure_opencode_running()

        assert result is True
        mock_start.assert_called_once()


def test_ensure_opencode_running_fails():
    """Test ensuring OpenCode is running when start fails."""
    with (
        patch("utils.opencode_utils.is_opencode_running") as mock_check,
        patch("utils.opencode_utils.start_opencode_server") as mock_start,
    ):
        mock_check.return_value = False
        mock_start.return_value = False

        result = ensure_opencode_running()

        assert result is False


def test_get_opencode_client_path():
    """Test getting OpenCode client path."""
    path = get_opencode_client_path()

    assert isinstance(path, Path)
    assert path.name == "opencode_client.py"


def test_check_opencode_client_exists():
    """Test checking if OpenCode client exists (positive case)."""
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True

        result = check_opencode_client()

        assert result is True


def test_check_opencode_client_not_exists():
    """Test checking if OpenCode client exists (negative case)."""
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = False

        result = check_opencode_client()

        assert result is False


def test_opencode_default_url():
    """Test that default URL is correct."""
    assert OPENCODE_DEFAULT_URL == "http://127.0.0.1:4096"


def test_is_opencode_running_correct_endpoint():
    """Test that health check uses correct endpoint."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        is_opencode_running()

        args = mock_run.call_args[0][0]
        assert "/global/health" in args


def test_start_opencode_server_uses_popen():
    """Test that start_opencode_server uses Popen correctly."""
    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
        patch("utils.opencode_utils.is_opencode_running") as mock_check,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        mock_popen.return_value = MagicMock()
        mock_check.return_value = True

        start_opencode_server()

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "opencode" in args
        assert "serve" in args


def test_ensure_opencode_running_custom_url():
    """Test ensure_opencode_running with custom URL."""
    custom_url = "http://localhost:8080"

    with (
        patch("utils.opencode_utils.is_opencode_running") as mock_check,
        patch("utils.opencode_utils.start_opencode_server") as _mock_start,
    ):
        mock_check.return_value = True

        result = ensure_opencode_running(custom_url)

        assert result is True
        mock_check.assert_called_with(custom_url)
