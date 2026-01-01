"""Tests for commit_agent.py."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from commit_agent import CommitAgent


@pytest.fixture
def mock_config():
    """Mock configuration for CommitAgent."""
    return {
        "general": {
            "journal_directory": "/tmp/test_journal",
            "author_name": "Test User",
            "author_email": "test@example.com",
        },
        "scheduling": {"auto_push": False, "opencode_url": "http://127.0.0.1:4096"},
    }


@pytest.fixture
def sample_entry_path(tmp_path):
    """Create a sample journal entry file."""
    entry_file = tmp_path / "2025" / "12" / "31.md"
    entry_file.parent.mkdir(parents=True, exist_ok=True)
    entry_file.write_text("# Test Entry\n\nThis is a test entry.")
    return entry_file


class TestCommitAgentInit:
    """Test CommitAgent initialization."""

    @patch("commit_agent.get_config")
    def test_init_with_config(self, mock_get_config, mock_config):
        """Test initialization with default config."""
        mock_get_config.return_value = mock_config
        agent = CommitAgent()

        assert agent.journal_repo == Path("/tmp/test_journal").expanduser()
        assert agent.auto_push is False

    @patch("commit_agent.get_config")
    def test_init_with_auto_push(self, mock_get_config, mock_config):
        """Test initialization with auto_push enabled."""
        mock_config["scheduling"]["auto_push"] = True
        mock_get_config.return_value = mock_config
        agent = CommitAgent()

        assert agent.auto_push is True


class TestCommitAgentCommitEntry:
    """Test CommitAgent.commit_entry method."""

    @patch("commit_agent.get_config")
    def test_commit_entry_file_not_found(self, mock_get_config, mock_config, tmp_path):
        """Test commit_entry when file doesn't exist."""
        mock_get_config.return_value = mock_config
        agent = CommitAgent()

        non_existent_path = tmp_path / "nonexistent.md"
        date = datetime(2025, 12, 31)
        result = agent.commit_entry(date, non_existent_path)

        assert result["success"] is False
        assert result["commit_hash"] is None
        assert result["message"] == ""
        assert "not found" in result["error"]

    @patch("commit_agent.get_config")
    @patch("utils.git_utils.stage_and_commit")
    def test_commit_entry_success_with_utils(
        self, mock_stage_and_commit, mock_get_config, mock_config, sample_entry_path
    ):
        """Test commit_entry success using git_utils."""
        mock_get_config.return_value = mock_config
        mock_stage_and_commit.return_value = True
        agent = CommitAgent()

        date = datetime(2025, 12, 31)
        result = agent.commit_entry(date, sample_entry_path)

        assert result["success"] is True
        assert result["commit_hash"] is None
        assert "Add journal entry for December 31, 2025" in result["message"]
        assert result["error"] is None

        mock_stage_and_commit.assert_called_once()

    @patch("commit_agent.get_config")
    @patch("utils.git_utils.stage_and_commit")
    def test_commit_entry_failure_with_utils(
        self, mock_stage_and_commit, mock_get_config, mock_config, sample_entry_path
    ):
        """Test commit_entry failure using git_utils."""
        mock_get_config.return_value = mock_config
        mock_stage_and_commit.return_value = False
        agent = CommitAgent()

        date = datetime(2025, 12, 31)
        result = agent.commit_entry(date, sample_entry_path)

        assert result["success"] is False
        assert result["error"] is None

    @patch("commit_agent.get_config")
    @patch("utils.git_utils.stage_and_commit", side_effect=Exception("Git utility error"))
    def test_commit_entry_import_error(self, mock_get_config, mock_config, sample_entry_path):
        """Test commit_entry handles import error."""
        mock_get_config.return_value = mock_config
        agent = CommitAgent()
        date = datetime(2025, 12, 31)

        result = agent.commit_entry(date, sample_entry_path)

        assert result["success"] is False
        assert "Git utility error" in result["error"]


class TestCommitAgentCommitWithGitCommands:
    """Test CommitAgent._commit_with_git_commands method."""

    @patch("commit_agent.get_config")
    @patch("subprocess.run")
    def test_commit_with_git_commands_success(
        self, mock_run, mock_get_config, mock_config, sample_entry_path
    ):
        """Test _commit_with_git_commands success."""
        mock_get_config.return_value = mock_config

        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(
                returncode=0,
                stdout="master abc123 Commit message\n",
                stderr="",
            ),
        ]

        agent = CommitAgent()
        date = datetime(2025, 12, 31)
        result = agent._commit_with_git_commands(date, sample_entry_path)

        assert result["success"] is True
        assert result["commit_hash"] == "abc123"
        assert "Add journal entry for December 31, 2025" in result["message"]
        assert result["error"] is None

        assert mock_run.call_count == 2

    @patch("commit_agent.get_config")
    @patch("subprocess.run")
    def test_commit_with_git_commands_commit_failure(
        self, mock_run, mock_get_config, mock_config, sample_entry_path
    ):
        """Test _commit_with_git_commands when commit fails."""
        mock_get_config.return_value = mock_config

        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(
                returncode=1,
                stdout="",
                stderr="Commit failed: nothing to commit",
            ),
        ]

        agent = CommitAgent()
        date = datetime(2025, 12, 31)
        result = agent._commit_with_git_commands(date, sample_entry_path)

        assert result["success"] is False
        assert result["commit_hash"] is None
        assert "Git commit failed" in result["error"]

    @patch("commit_agent.get_config")
    @patch("subprocess.run")
    def test_commit_with_git_commands_with_auto_push(
        self, mock_run, mock_get_config, mock_config, sample_entry_path
    ):
        """Test _commit_with_git_commands with auto_push enabled."""
        mock_config["scheduling"]["auto_push"] = True
        mock_get_config.return_value = mock_config

        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout="[abc123] Commit\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        agent = CommitAgent()
        date = datetime(2025, 12, 31)
        result = agent._commit_with_git_commands(date, sample_entry_path)

        assert result["success"] is True
        assert mock_run.call_count == 3

    @patch("commit_agent.get_config")
    @patch("subprocess.run")
    def test_commit_with_git_commands_subprocess_error(
        self, mock_run, mock_get_config, mock_config
    ):
        """Test _commit_with_git_commands with CalledProcessError."""
        mock_get_config.return_value = mock_config

        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr="Git command failed")

        agent = CommitAgent()
        date = datetime(2025, 12, 31)
        entry_path = Path("/tmp/test.md")

        result = agent._commit_with_git_commands(date, entry_path)

        assert result["success"] is False
        assert "Git command failed" in result["error"]


class TestCommitAgentGenerateCommitMessage:
    """Test CommitAgent._generate_commit_message method."""

    @patch("commit_agent.get_config")
    def test_generate_commit_message(self, mock_get_config, mock_config):
        """Test commit message generation."""
        mock_get_config.return_value = mock_config
        agent = CommitAgent()

        date = datetime(2025, 12, 31)
        message = agent._generate_commit_message(date)

        assert message == "Add journal entry for December 31, 2025"

    @patch("commit_agent.get_config")
    def test_generate_commit_message_january_first(self, mock_get_config, mock_config):
        """Test commit message for January 1st."""
        mock_get_config.return_value = mock_config
        agent = CommitAgent()

        date = datetime(2026, 1, 1)
        message = agent._generate_commit_message(date)

        assert message == "Add journal entry for January 01, 2026"


class TestCommitAgentPushChanges:
    """Test CommitAgent._push_changes method."""

    @patch("commit_agent.get_config")
    @patch("subprocess.run")
    def test_push_changes_success(self, mock_run, mock_get_config, mock_config):
        """Test _push_changes success."""
        mock_get_config.return_value = mock_config
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        agent = CommitAgent()
        result = agent._push_changes()

        assert result["success"] is True
        assert result["error"] is None

    @patch("commit_agent.get_config")
    @patch("subprocess.run")
    def test_push_changes_failure(self, mock_run, mock_get_config, mock_config):
        """Test _push_changes failure."""
        mock_get_config.return_value = mock_config
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Push failed")

        agent = CommitAgent()
        result = agent._push_changes()

        assert result["success"] is False
        assert result["error"] == "Push failed"

    @patch("commit_agent.get_config")
    @patch("subprocess.run")
    def test_push_changes_exception(self, mock_run, mock_get_config, mock_config):
        """Test _push_changes with exception."""
        mock_get_config.return_value = mock_config
        mock_run.side_effect = Exception("Network error")

        agent = CommitAgent()
        result = agent._push_changes()

        assert result["success"] is False
        assert "Network error" in result["error"]
