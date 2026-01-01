"""Tests for main.py CLI entry point."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from main import cmd_generate, cmd_run, cmd_status, cmd_validate, main, parse_date


class TestMain:
    """Test main CLI entry point."""

    @patch("main.setup_logging")
    @patch("main.ensure_opencode_running")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_no_command(self, mock_parse_args, mock_ensure, mock_setup):
        """Test main with no command."""
        mock_parse_args.return_value = MagicMock(command=None)
        mock_setup.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("main.setup_logging")
    @patch("main.ensure_opencode_running")
    @patch("main.cmd_generate")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_generate_command(self, mock_parse_args, mock_cmd_gen, mock_ensure, mock_setup):
        """Test main with generate command."""
        mock_args = MagicMock(command="generate", date=None)
        mock_parse_args.return_value = mock_args
        mock_setup.return_value = None
        mock_ensure.return_value = True

        main()

        mock_cmd_gen.assert_called_once()

    @patch("main.setup_logging")
    @patch("main.ensure_opencode_running")
    @patch("main.cmd_validate")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_validate_command(self, mock_parse_args, mock_cmd_val, mock_ensure, mock_setup):
        """Test main with validate command."""
        mock_args = MagicMock(command="validate", file="2025/12/31.md")
        mock_parse_args.return_value = mock_args
        mock_setup.return_value = None
        mock_ensure.return_value = True

        main()

        mock_cmd_val.assert_called_once()

    @patch("main.setup_logging")
    @patch("main.ensure_opencode_running")
    @patch("main.cmd_run")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_run_command(self, mock_parse_args, mock_cmd_run, mock_ensure, mock_setup):
        """Test main with run command."""
        mock_args = MagicMock(command="run", date=None)
        mock_parse_args.return_value = mock_args
        mock_setup.return_value = None
        mock_ensure.return_value = True

        main()

        mock_cmd_run.assert_called_once()

    @patch("main.setup_logging")
    @patch("main.ensure_opencode_running")
    @patch("main.cmd_status")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_status_command(self, mock_parse_args, mock_cmd_status, mock_ensure, mock_setup):
        """Test main with status command."""
        mock_args = MagicMock(command="status", date=None)
        mock_parse_args.return_value = mock_args
        mock_setup.return_value = None
        mock_ensure.return_value = True

        main()

        mock_cmd_status.assert_called_once()

    @patch("main.setup_logging")
    @patch("main.ensure_opencode_running")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_keyboard_interrupt(self, mock_parse_args, mock_ensure, mock_setup):
        """Test main with KeyboardInterrupt."""
        mock_args = MagicMock(command="generate", date=None)
        mock_parse_args.return_value = mock_args
        mock_setup.return_value = None
        mock_ensure.return_value = True

        with patch("main.cmd_generate", side_effect=KeyboardInterrupt()):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 130


class TestCmdGenerate:
    """Test cmd_generate function."""

    @patch("main.parse_date")
    def test_cmd_generate_success(self, mock_parse_date):
        """Test cmd_generate success."""
        mock_args = MagicMock(command="generate", date="2025-12-31")
        mock_logger = MagicMock()
        test_date = datetime(2025, 12, 31)
        mock_parse_date.return_value = test_date

        with patch("agents.orchestrator.OrchestratorAgent") as mock_orchestrator:
            mock_orch_instance = MagicMock()
            mock_orch_instance.run_day.return_value = {
                "status": "success",
                "entry_path": "/tmp/journal/2025/12/31.md",
                "commit_hash": "abc123",
            }
            mock_orchestrator.return_value = mock_orch_instance

            cmd_generate(mock_args, mock_logger)

            mock_logger.info.assert_any_call("Generating journal entry for 2025-12-31")
            mock_logger.info.assert_any_call(
                "✓ Entry generated successfully: /tmp/journal/2025/12/31.md"
            )
            mock_logger.info.assert_any_call("✓ Committed: abc123")

    @patch("main.parse_date")
    def test_cmd_generate_no_date(self, mock_parse_date):
        """Test cmd_generate without date argument."""
        mock_args = MagicMock(command="generate", date=None)
        mock_logger = MagicMock()
        mock_parse_date.return_value = datetime(2025, 12, 31)

        with patch("agents.orchestrator.OrchestratorAgent") as mock_orchestrator:
            mock_orch_instance = MagicMock()
            mock_orch_instance.run_day.return_value = {
                "status": "success",
                "entry_path": "/tmp/journal/2025/12/31.md",
            }
            mock_orchestrator.return_value = mock_orch_instance

            cmd_generate(mock_args, mock_logger)

            mock_parse_date.assert_not_called()

    @patch("main.parse_date")
    def test_cmd_generate_failure(self, mock_parse_date):
        """Test cmd_generate failure."""
        mock_args = MagicMock(command="generate", date="2025-12-31")
        mock_logger = MagicMock()
        mock_parse_date.return_value = datetime(2025, 12, 31)

        with patch("agents.orchestrator.OrchestratorAgent") as mock_orchestrator:
            mock_orch_instance = MagicMock()
            mock_orch_instance.run_day.return_value = {
                "status": "failed",
                "error": "Test error",
            }
            mock_orchestrator.return_value = mock_orch_instance

            with pytest.raises(SystemExit) as exc_info:
                cmd_generate(mock_args, mock_logger)

            assert exc_info.value.code == 1
            mock_logger.error.assert_called()


class TestCmdValidate:
    """Test cmd_validate function."""

    def test_cmd_validate_success(self, tmp_path):
        """Test cmd_validate success."""
        entry_path = tmp_path / "2025" / "12" / "31.md"
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        entry_path.write_text("# Test Entry")

        mock_args = MagicMock(file=str(entry_path))
        mock_logger = MagicMock()

        with patch("agents.validator.ValidationAgent") as mock_validator:
            mock_val_instance = MagicMock()
            mock_val_instance.validate_entry.return_value = {"valid": True, "issues": []}
            mock_validator.return_value = mock_val_instance

            cmd_validate(mock_args, mock_logger)

            mock_logger.info.assert_called_with("✓ Entry is valid")

    def test_cmd_validate_file_not_found(self, tmp_path):
        """Test cmd_validate with non-existent file."""
        entry_path = tmp_path / "nonexistent.md"
        mock_args = MagicMock(file=str(entry_path))
        mock_logger = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            cmd_validate(mock_args, mock_logger)

        assert exc_info.value.code == 1
        mock_logger.error.assert_called()

    def test_cmd_validate_with_issues(self, tmp_path):
        """Test cmd_validate with validation issues."""
        entry_path = tmp_path / "2025" / "12" / "31.md"
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        entry_path.write_text("# Test")

        mock_args = MagicMock(file=str(entry_path))
        mock_logger = MagicMock()

        with patch("agents.validator.ValidationAgent") as mock_validator:
            mock_val_instance = MagicMock()
            mock_val_instance.validate_entry.return_value = {
                "valid": False,
                "issues": ["Missing summary section", "No commits listed"],
            }
            mock_validator.return_value = mock_val_instance

            with pytest.raises(SystemExit) as exc_info:
                cmd_validate(mock_args, mock_logger)

            assert exc_info.value.code == 1
            mock_logger.warning.assert_called()


class TestCmdRun:
    """Test cmd_run function."""

    @patch("main.parse_date")
    def test_cmd_run_success(self, mock_parse_date):
        """Test cmd_run success."""
        mock_args = MagicMock(command="run", date="2025-12-31")
        mock_logger = MagicMock()
        mock_parse_date.return_value = datetime(2025, 12, 31)

        with patch("agents.orchestrator.OrchestratorAgent") as mock_orchestrator:
            mock_orch_instance = MagicMock()
            mock_orch_instance.run_day.return_value = {
                "status": "success",
                "entry_path": "/tmp/journal/2025/12/31.md",
            }
            mock_orchestrator.return_value = mock_orch_instance

            cmd_run(mock_args, mock_logger)

            mock_logger.info.assert_any_call("Running orchestrator for 2025-12-31")
            mock_logger.info.assert_any_call("✓ Orchestrator completed: /tmp/journal/2025/12/31.md")

    @patch("main.parse_date")
    def test_cmd_run_skipped(self, mock_parse_date):
        """Test cmd_run when skipped (no work day)."""
        mock_args = MagicMock(command="run", date="2025-12-31")
        mock_logger = MagicMock()
        mock_parse_date.return_value = datetime(2025, 12, 31)

        with patch("agents.orchestrator.OrchestratorAgent") as mock_orchestrator:
            mock_orch_instance = MagicMock()
            mock_orch_instance.run_day.return_value = {
                "status": "skipped",
            }
            mock_orchestrator.return_value = mock_orch_instance

            cmd_run(mock_args, mock_logger)

            mock_logger.info.assert_any_call("ℹ No commits on this date, entry skipped")

    @patch("main.parse_date")
    def test_cmd_run_failure(self, mock_parse_date):
        """Test cmd_run failure."""
        mock_args = MagicMock(command="run", date="2025-12-31")
        mock_logger = MagicMock()
        mock_parse_date.return_value = datetime(2025, 12, 31)

        with patch("agents.orchestrator.OrchestratorAgent") as mock_orchestrator:
            mock_orch_instance = MagicMock()
            mock_orch_instance.run_day.return_value = {
                "status": "failed",
                "error": "Orchestrator error",
            }
            mock_orchestrator.return_value = mock_orch_instance

            with pytest.raises(SystemExit) as exc_info:
                cmd_run(mock_args, mock_logger)

            assert exc_info.value.code == 1


class TestCmdStatus:
    """Test cmd_status function."""

    @patch("main.get_config")
    @patch("subprocess.run")
    def test_cmd_status_entry_exists_committed(self, mock_run, mock_get_config, tmp_path):
        """Test cmd_status with existing committed entry."""
        journal_dir = tmp_path / "journal"
        journal_dir.mkdir(parents=True)
        entry_path = journal_dir / "2025" / "12" / "31.md"
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        entry_path.write_text("# Test Entry")

        mock_args = MagicMock(date="2025-12-31")
        mock_logger = MagicMock()

        mock_config = {
            "general": {
                "journal_directory": str(journal_dir),
            }
        }
        mock_get_config.return_value = mock_config
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        cmd_status(mock_args, mock_logger)

        mock_logger.info.assert_any_call(f"✓ Entry exists: {entry_path}")
        mock_logger.info.assert_any_call("  Status: Committed")

    @patch("main.get_config")
    @patch("subprocess.run")
    def test_cmd_status_entry_exists_modified(self, mock_run, mock_get_config, tmp_path):
        """Test cmd_status with existing modified entry."""
        journal_dir = tmp_path / "journal"
        journal_dir.mkdir(parents=True)
        entry_path = journal_dir / "2025" / "12" / "31.md"
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        entry_path.write_text("# Test Entry")

        mock_args = MagicMock(date="2025-12-31")
        mock_logger = MagicMock()

        mock_config = {
            "general": {
                "journal_directory": str(journal_dir),
            }
        }
        mock_get_config.return_value = mock_config
        mock_run.return_value = MagicMock(stdout=" M 2025/12/31.md", stderr="", returncode=0)

        cmd_status(mock_args, mock_logger)

        mock_logger.info.assert_any_call(f"✓ Entry exists: {entry_path}")
        mock_logger.info.assert_any_call("  Status: Modified (uncommitted changes)")

    @patch("main.get_config")
    def test_cmd_status_entry_not_exists(self, mock_get_config, tmp_path):
        """Test cmd_status with non-existent entry."""
        journal_dir = tmp_path / "journal"
        journal_dir.mkdir(parents=True)

        mock_args = MagicMock(date="2025-12-31")
        mock_logger = MagicMock()

        mock_config = {
            "general": {
                "journal_directory": str(journal_dir),
            }
        }
        mock_get_config.return_value = mock_config

        cmd_status(mock_args, mock_logger)

        mock_logger.info.assert_called_with("✗ Entry does not exist for 2025-12-31")

    @patch("main.get_config")
    @patch("main.parse_date")
    def test_cmd_status_no_date(self, mock_parse_date, mock_get_config, tmp_path):
        """Test cmd_status without date argument."""
        journal_dir = tmp_path / "journal"
        journal_dir.mkdir(parents=True)

        mock_args = MagicMock(date=None)
        mock_logger = MagicMock()

        mock_config = {
            "general": {
                "journal_directory": str(journal_dir),
            }
        }
        mock_get_config.return_value = mock_config
        mock_parse_date.return_value = datetime(2025, 12, 31)

        cmd_status(mock_args, mock_logger)

        mock_parse_date.assert_not_called()


class TestParseDate:
    """Test parse_date function."""

    def test_parse_date_valid(self):
        """Test parse_date with valid format."""
        result = parse_date("2025-12-31")
        assert result == datetime(2025, 12, 31)

    def test_parse_date_january_first(self):
        """Test parse_date with January 1st."""
        result = parse_date("2026-01-01")
        assert result == datetime(2026, 1, 1)

    def test_parse_date_invalid_format(self):
        """Test parse_date with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            parse_date("12/31/2025")

        assert "Invalid date format" in str(exc_info.value)

    def test_parse_date_invalid_date(self):
        """Test parse_date with invalid date."""
        with pytest.raises(ValueError) as exc_info:
            parse_date("2025-13-01")

        assert "Invalid date format" in str(exc_info.value)
