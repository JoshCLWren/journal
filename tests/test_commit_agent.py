"""Test Commit Agent."""

import subprocess
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from commit_agent import CommitAgent


@pytest.fixture
def mock_config():
    """Provide a mock configuration."""
    return {
        "general": {
            "journal_directory": "/tmp/test_journal",
        },
        "scheduling": {
            "auto_push": False,
        },
    }


@pytest.fixture
def agent(mock_config):
    """Create CommitAgent with mocked config."""
    with patch("commit_agent.get_config", return_value=mock_config):
        with patch("commit_agent.Path") as mock_path:
            mock_path.return_value = Path("/tmp/test_journal")
            mock_path.expanduser.return_value = Path("/tmp/test_journal")
            agent = CommitAgent()
            yield agent


@pytest.fixture
def temp_entry_file():
    """Create a temporary entry file."""
    with TemporaryDirectory() as tmpdir:
        entry_path = Path(tmpdir) / "2025" / "12" / "31.md"
        entry_path.parent.mkdir(parents=True)
        entry_path.write_text("# December 31, 2025\n## Summary\nTest content.")
        yield entry_path


def test_commit_agent_init(agent):
    """Test CommitAgent initialization."""
    assert agent.journal_repo is not None
    assert agent.auto_push is False


def test_commit_entry_success(agent, temp_entry_file):
    """Test committing entry successfully."""
    with patch("commit_agent.stage_and_commit", return_value=True):
        result = agent.commit_entry(datetime(2025, 12, 31), temp_entry_file)

    assert result["success"] is True
    assert result["commit_hash"] is not None
    assert result["error"] is None


def test_commit_entry_file_not_found(agent):
    """Test committing non-existent file."""
    non_existent = Path("/tmp/nonexistent.md")

    result = agent.commit_entry(datetime(2025, 12, 31), non_existent)

    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_commit_entry_git_command_failure(agent, temp_entry_file):
    """Test committing when git commands fail."""
    with patch("commit_agent.stage_and_commit", side_effect=ImportError("No module")):
        with patch("subprocess.run") as mock_run:
            # Stage succeeds
            mock_run.return_value = MagicMock(returncode=0)

            # But commit fails
            commit_call = MagicMock(returncode=1, stderr="Commit failed")
            mock_run.side_effect = [
                MagicMock(returncode=0),  # stage
                commit_call,  # commit
            ]

            result = agent.commit_entry(datetime(2025, 12, 31), temp_entry_file)

    assert result["success"] is False


def test_commit_entry_exception(agent, temp_entry_file):
    """Test committing when an exception occurs."""
    with patch("commit_agent.stage_and_commit", side_effect=Exception("Unexpected error")):
        result = agent.commit_entry(datetime(2025, 12, 31), temp_entry_file)

    assert result["success"] is False
    assert "Unexpected error" in result["error"]


def test_generate_commit_message(agent):
    """Test commit message generation."""
    date = datetime(2025, 12, 31)

    message = agent._generate_commit_message(date)

    assert "December" in message
    assert "31" in message
    assert "2025" in message


def test_generate_commit_message_january(agent):
    """Test commit message for January date."""
    date = datetime(2025, 1, 15)

    message = agent._generate_commit_message(date)

    assert "January" in message
    assert "15" in message


def test_commit_with_git_commands_success(agent, temp_entry_file):
    """Test committing using direct git commands."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="abc123 Add journal entry for December 31, 2025"
        )

        result = agent._commit_with_git_commands(datetime(2025, 12, 31), temp_entry_file)

    assert result["success"] is True
    assert result["commit_hash"] == "abc123"


def test_commit_with_git_commands_stage_failure(agent, temp_entry_file):
    """Test git commit when staging fails."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git add", stderr="Add failed")

        result = agent._commit_with_git_commands(datetime(2025, 12, 31), temp_entry_file)

    assert result["success"] is False


def test_commit_with_git_commands_commit_failure(agent, temp_entry_file):
    """Test git commit when committing fails."""
    with patch("subprocess.run") as mock_run:
        # Stage succeeds
        stage_result = MagicMock(returncode=0)
        # Commit fails
        commit_result = MagicMock(returncode=1, stderr="Commit failed")
        mock_run.side_effect = [stage_result, commit_result]

        result = agent._commit_with_git_commands(datetime(2025, 12, 31), temp_entry_file)

    assert result["success"] is False
    assert "Git commit failed" in result["error"] or "Git command failed" in result["error"]


def test_commit_entry_with_auto_push_enabled(agent, temp_entry_file):
    """Test committing with auto-push enabled."""
    agent.auto_push = True

    with (
        patch("commit_agent.stage_and_commit", return_value=True),
        patch.object(agent, "_push_changes", return_value={"success": True}),
    ):
        result = agent.commit_entry(datetime(2025, 12, 31), temp_entry_file)

    assert result["success"] is True


def test_commit_entry_auto_push_fails(agent, temp_entry_file):
    """Test committing when auto-push fails."""
    agent.auto_push = True

    with (
        patch("commit_agent.stage_and_commit", return_value=True),
        patch.object(
            agent, "_push_changes", return_value={"success": False, "error": "Push failed"}
        ),
    ):
        result = agent.commit_entry(datetime(2025, 12, 31), temp_entry_file)

    # Commit should still succeed even if push fails
    assert result["success"] is True


def test_push_changes_success(agent):
    """Test pushing changes successfully."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        result = agent._push_changes()

    assert result["success"] is True
    assert result["error"] is None


def test_push_changes_failure(agent):
    """Test pushing changes when it fails."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Push failed")

        result = agent._push_changes()

    assert result["success"] is False
    assert result["error"] is not None


def test_push_changes_exception(agent):
    """Test pushing changes when an exception occurs."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Network error")

        result = agent._push_changes()

    assert result["success"] is False


def test_commit_entry_leap_year(agent, temp_entry_file):
    """Test committing entry for leap year date."""
    with TemporaryDirectory() as tmpdir:
        entry_path = Path(tmpdir) / "2024" / "02" / "29.md"
        entry_path.parent.mkdir(parents=True)
        entry_path.write_text("# February 29, 2024\n## Summary\nTest.")

        with patch("commit_agent.stage_and_commit", return_value=True):
            result = agent.commit_entry(datetime(2024, 2, 29), entry_path)

    assert result["success"] is True


def test_commit_entry_single_digit_day(agent):
    """Test committing entry for single-digit day."""
    with TemporaryDirectory() as tmpdir:
        entry_path = Path(tmpdir) / "2025" / "01" / "5.md"
        entry_path.parent.mkdir(parents=True)
        entry_path.write_text("# January 5, 2025\n## Summary\nTest.")

        with patch("utils.git_utils.stage_and_commit", return_value=True):
            result = agent.commit_entry(datetime(2025, 1, 5), entry_path)

    assert result["success"] is True


def test_commit_entry_commit_message_format(agent):
    """Test that commit message has correct format."""
    date = datetime(2025, 12, 31)
    message = agent._generate_commit_message(date)

    assert message.startswith("Add journal entry for")
    assert "2025" in message


def test_commit_with_git_commands_calls_add(agent, temp_entry_file):
    """Test that git add is called correctly."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123 Test message")

        agent._commit_with_git_commands(datetime(2025, 12, 31), temp_entry_file)

    # Check that git add was called
    calls = [str(call[0]) for call in mock_run.call_args_list]
    assert any("git add" in call for call in calls)


def test_commit_with_git_commands_calls_commit(agent, temp_entry_file):
    """Test that git commit is called correctly."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123 Test message")

        agent._commit_with_git_commands(datetime(2025, 12, 31), temp_entry_file)

    # Check that git commit was called
    calls = [str(call[0]) for call in mock_run.call_args_list]
    assert any("git commit" in call for call in calls)


def test_push_changes_logs_info(agent):
    """Test that push_changes logs information."""
    with patch("subprocess.run") as mock_run, patch("commit_agent.logger") as mock_logger:
        mock_run.return_value = MagicMock(returncode=0)

        agent._push_changes()

        mock_logger.info.assert_called()
        log_calls = [str(call[0]) for call in mock_logger.info.call_args_list]
        assert any("pushing" in call.lower() for call in log_calls)


def test_commit_entry_logs_error(agent):
    """Test that commit_entry logs errors."""
    non_existent = Path("/tmp/nonexistent.md")

    with patch("commit_agent.logger") as mock_logger:
        _ = agent.commit_entry(datetime(2025, 12, 31), non_existent)

    mock_logger.error.assert_called()
