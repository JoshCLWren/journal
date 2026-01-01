"""Test Main CLI entry point."""

import argparse
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from main import cmd_generate, cmd_run, cmd_status, cmd_validate, main, parse_date


@pytest.fixture
def mock_args():
    """Provide mock command-line arguments."""
    return argparse.Namespace()


@pytest.fixture
def temp_journal_dir():
    """Provide a temporary journal directory."""
    with TemporaryDirectory() as tmpdir:
        journal_dir = Path(tmpdir)
        yield journal_dir


def test_parse_date_valid():
    """Test parsing valid date."""
    result = parse_date("2025-12-31")

    assert isinstance(result, datetime)
    assert result.year == 2025
    assert result.month == 12
    assert result.day == 31


def test_parse_date_invalid():
    """Test parsing invalid date."""
    with pytest.raises(ValueError, match="Invalid date format"):
        parse_date("invalid-date")


def test_parse_date_wrong_format():
    """Test parsing date with wrong format."""
    with pytest.raises(ValueError, match="Invalid date format"):
        parse_date("12/31/2025")


def test_cmd_generate_success(temp_journal_dir, capsys):
    """Test generate command success."""
    date = datetime(2025, 12, 31)

    mock_result = {
        "status": "success",
        "entry_path": "/tmp/test/2025/12/31.md",
        "commit_hash": "abc123",
    }

    mock_args = MagicMock(date=None)

    with (
        patch("main.parse_date", return_value=date),
        patch("main.OrchestratorAgent") as mock_orchestrator,
        patch("main.Path"),
    ):
        mock_agent = MagicMock()
        mock_agent.run_day.return_value = mock_result
        mock_orchestrator.return_value = mock_agent

        mock_logger = MagicMock()
        cmd_generate(mock_args, mock_logger)

    mock_agent.run_day.assert_called_once()


def test_cmd_generate_failure(temp_journal_dir):
    """Test generate command with failure."""
    date = datetime(2025, 12, 31)

    mock_result = {
        "status": "failed",
        "error": "Test error",
    }

    mock_args = MagicMock(date=None)

    with (
        patch("main.parse_date", return_value=date),
        patch("main.OrchestratorAgent") as mock_orchestrator,
    ):
        mock_agent = MagicMock()
        mock_agent.run_day.return_value = mock_result
        mock_orchestrator.return_value = mock_agent

        mock_logger = MagicMock()

        with pytest.raises(SystemExit):
            cmd_generate(mock_args, mock_logger)


def test_cmd_generate_with_date():
    """Test generate command with specific date."""
    date_str = "2025-06-15"
    date = datetime(2025, 6, 15)

    mock_args = MagicMock(date=date_str)

    with (
        patch("main.parse_date", return_value=date),
        patch("main.OrchestratorAgent") as mock_orchestrator,
    ):
        mock_agent = MagicMock()
        mock_agent.run_day.return_value = {
            "status": "success",
            "entry_path": "/tmp/test/2025/06/15.md",
            "commit_hash": "abc123",
        }
        mock_orchestrator.return_value = mock_agent

        mock_logger = MagicMock()
        cmd_generate(mock_args, mock_logger)

        mock_agent.run_day.assert_called_once_with(date)


def test_cmd_validate_file_exists(temp_journal_dir):
    """Test validate command with existing file."""
    entry_path = temp_journal_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text(
        "# December 31, 2025\n## Summary\nTest.\n## Repositories Worked On\n- test (10 commits)"
    )

    mock_args = MagicMock(file=str(entry_path))

    with patch("main.ValidationAgent") as mock_validator:
        mock_agent = MagicMock()
        mock_agent.validate_entry.return_value = {"valid": True, "issues": [], "warnings": []}
        mock_validator.return_value = mock_agent

        mock_logger = MagicMock()
        cmd_validate(mock_args, mock_logger)

        mock_agent.validate_entry.assert_called_once_with(entry_path)


def test_cmd_validate_file_not_found(temp_journal_dir):
    """Test validate command with non-existent file."""
    non_existent = temp_journal_dir / "nonexistent.md"

    mock_args = MagicMock(file=str(non_existent))

    with pytest.raises(SystemExit):
        mock_logger = MagicMock()
        cmd_validate(mock_args, mock_logger)


def test_cmd_validate_invalid_entry(temp_journal_dir):
    """Test validate command with invalid entry."""
    entry_path = temp_journal_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("Invalid entry")

    mock_args = MagicMock(file=str(entry_path))

    with patch("main.ValidationAgent") as mock_validator:
        mock_agent = MagicMock()
        mock_agent.validate_entry.return_value = {
            "valid": False,
            "issues": ["Missing header"],
            "warnings": [],
        }
        mock_validator.return_value = mock_agent

        mock_logger = MagicMock()

        with pytest.raises(SystemExit):
            cmd_validate(mock_args, mock_logger)


def test_cmd_run_success():
    """Test run command success."""
    date = datetime(2025, 12, 31)
    mock_args = MagicMock(date=None)

    with (
        patch("main.parse_date", return_value=date),
        patch("main.OrchestratorAgent") as mock_orchestrator,
    ):
        mock_agent = MagicMock()
        mock_agent.run_day.return_value = {
            "status": "success",
            "entry_path": "/tmp/test/2025/12/31.md",
            "commit_hash": "abc123",
        }
        mock_orchestrator.return_value = mock_agent

        mock_logger = MagicMock()
        cmd_run(mock_args, mock_logger)

        mock_agent.run_day.assert_called_once()


def test_cmd_run_skipped():
    """Test run command when entry is skipped (no commits)."""
    date = datetime(2025, 12, 31)
    mock_args = MagicMock(date=None)

    with (
        patch("main.parse_date", return_value=date),
        patch("main.OrchestratorAgent") as mock_orchestrator,
    ):
        mock_agent = MagicMock()
        mock_agent.run_day.return_value = {
            "status": "skipped",
            "entry_path": None,
            "commit_hash": None,
            "error": None,
        }
        mock_orchestrator.return_value = mock_agent

        mock_logger = MagicMock()
        cmd_run(mock_args, mock_logger)

        mock_logger.info.assert_called()


def test_cmd_run_failure():
    """Test run command when orchestrator fails."""
    date = datetime(2025, 12, 31)
    mock_args = MagicMock(date=None)

    with (
        patch("main.parse_date", return_value=date),
        patch("main.OrchestratorAgent") as mock_orchestrator,
    ):
        mock_agent = MagicMock()
        mock_agent.run_day.return_value = {
            "status": "failed",
            "error": "Test error",
        }
        mock_orchestrator.return_value = mock_agent

        mock_logger = MagicMock()

        with pytest.raises(SystemExit):
            cmd_run(mock_args, mock_logger)


def test_cmd_status_exists(temp_journal_dir):
    """Test status command when entry exists."""
    entry_path = temp_journal_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("# December 31, 2025\n## Summary\nTest.")

    with (
        patch("main.get_config") as mock_config,
        patch("main.Path") as mock_path,
        patch("subprocess.run") as mock_run,
    ):
        mock_config.return_value = {"general": {"journal_directory": str(temp_journal_dir)}}
        mock_path.return_value = temp_journal_dir
        mock_path.expanduser.return_value = temp_journal_dir
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        mock_args = MagicMock(date=None)
        mock_logger = MagicMock()
        cmd_status(mock_args, mock_logger)

        mock_logger.info.assert_called()


def test_cmd_status_not_exists(temp_journal_dir):
    """Test status command when entry doesn't exist."""
    _ = temp_journal_dir / "2025" / "12" / "31.md"

    with patch("main.get_config") as mock_config, patch("main.Path") as mock_path:
        mock_config.return_value = {"general": {"journal_directory": str(temp_journal_dir)}}
        mock_path.return_value = temp_journal_dir
        mock_path.expanduser.return_value = temp_journal_dir
        mock_path.side_effect = lambda *args, **kwargs: Path(*args, **kwargs)

        mock_args = MagicMock(date=None)
        mock_logger = MagicMock()
        cmd_status(mock_args, mock_logger)

        mock_logger.info.assert_called()


def test_main_no_command(capsys):
    """Test main with no command (shows help)."""
    with patch("sys.argv", ["main"]):
        with pytest.raises(SystemExit):
            main()


def test_main_keyboard_interrupt():
    """Test main with keyboard interrupt."""
    with (
        patch("sys.argv", ["main", "generate"]),
        patch("main.parse_date", side_effect=KeyboardInterrupt()),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 130


def test_main_exception():
    """Test main with general exception."""
    with (
        patch("sys.argv", ["main", "generate"]),
        patch("main.parse_date", side_effect=Exception("Test error")),
        patch("main.ensure_opencode_running", return_value=True),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


def test_main_opencode_not_available():
    """Test main when OpenCode is not available."""
    with (
        patch("sys.argv", ["main", "generate"]),
        patch("main.ensure_opencode_running", return_value=False),
        patch("main.parse_date", return_value=datetime(2025, 12, 31)),
        patch("main.OrchestratorAgent") as mock_orchestrator,
    ):
        mock_agent = MagicMock()
        mock_agent.run_day.return_value = {
            "status": "success",
            "entry_path": "/tmp/test.md",
            "commit_hash": "abc123",
        }
        mock_orchestrator.return_value = mock_agent

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should continue despite OpenCode not being available
        assert exc_info.value.code != 1


def test_cmd_generate_leap_year():
    """Test generate command for leap year date."""
    date = datetime(2024, 2, 29)
    mock_args = MagicMock(date="2024-02-29")

    with (
        patch("main.parse_date", return_value=date),
        patch("main.OrchestratorAgent") as mock_orchestrator,
    ):
        mock_agent = MagicMock()
        mock_agent.run_day.return_value = {
            "status": "success",
            "entry_path": "/tmp/test/2024/02/29.md",
            "commit_hash": "abc123",
        }
        mock_orchestrator.return_value = mock_agent

        mock_logger = MagicMock()
        cmd_generate(mock_args, mock_logger)


def test_cmd_status_modified(temp_journal_dir):
    """Test status command when entry has uncommitted changes."""
    entry_path = temp_journal_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("# December 31, 2025\n## Summary\nTest.")

    with (
        patch("main.get_config") as mock_config,
        patch("main.Path") as mock_path,
        patch("subprocess.run") as mock_run,
    ):
        mock_config.return_value = {"general": {"journal_directory": str(temp_journal_dir)}}
        mock_path.return_value = temp_journal_dir
        mock_path.expanduser.return_value = temp_journal_dir
        mock_run.return_value = MagicMock(stdout="M 2025/12/31.md", returncode=0)

        mock_args = MagicMock(date=None)
        mock_logger = MagicMock()
        cmd_status(mock_args, mock_logger)

        mock_logger.info.assert_called()
        # Check that it logged about modified status
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert len(log_calls) >= 2  # At least entry exists and status


def test_parse_date_edge_cases():
    """Test parsing edge case dates."""
    # First day of year
    date1 = parse_date("2025-01-01")
    assert date1.month == 1
    assert date1.day == 1

    # Last day of year
    date2 = parse_date("2025-12-31")
    assert date2.month == 12
    assert date2.day == 31


def test_cmd_validate_warning_only(temp_journal_dir):
    """Test validate command with warnings but valid entry."""
    entry_path = temp_journal_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text(
        "# December 31, 2025\n## Summary\nTest.\n## Repositories Worked On\n- test (10 commits)"
    )

    mock_args = MagicMock(file=str(entry_path))

    with patch("main.ValidationAgent") as mock_validator:
        mock_agent = MagicMock()
        mock_agent.validate_entry.return_value = {
            "valid": True,
            "issues": [],
            "warnings": ["Minor warning"],
        }
        mock_validator.return_value = mock_agent

        mock_logger = MagicMock()
        cmd_validate(mock_args, mock_logger)

        # Should not exit with warnings
        mock_logger.info.assert_called()
