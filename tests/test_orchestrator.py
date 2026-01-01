"""Test Orchestrator Agent."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from agents.orchestrator import OrchestratorAgent


@pytest.fixture
def mock_config():
    """Provide a mock configuration."""
    return {
        "general": {
            "journal_directory": "/tmp/test_journal",
        },
    }


@pytest.fixture
def agent(mock_config):
    """Create OrchestratorAgent with mocked dependencies."""
    with patch("agents.orchestrator.get_config", return_value=mock_config):
        with (
            patch("agents.orchestrator.GitAnalysisAgent") as mock_git,
            patch("agents.orchestrator.ContentGenerationAgent") as mock_content,
            patch("agents.orchestrator.CommitAgent") as mock_commit,
        ):
            agent = OrchestratorAgent()
            agent.git_agent = mock_git.return_value
            agent.content_agent = mock_content.return_value
            agent.commit_agent = mock_commit.return_value
            yield agent


@pytest.fixture
def temp_journal_dir():
    """Provide a temporary journal directory."""
    with TemporaryDirectory() as tmpdir:
        journal_dir = Path(tmpdir) / "2025" / "12"
        journal_dir.mkdir(parents=True)
        yield Path(tmpdir)


@pytest.fixture
def sample_git_data():
    """Provide sample git analysis data."""
    return {
        "date": "2025-12-31",
        "is_work_day": True,
        "total_commits": 43,
        "total_loc_added": 4000,
        "total_loc_deleted": 800,
        "estimated_hours": 8.5,
        "repos": {
            "test-repo": {
                "commits": 43,
                "loc_added": 4000,
                "loc_deleted": 800,
                "commits_by_category": {"feat": 25, "fix": 10},
                "top_features": ["feat: feature"],
            }
        },
    }


def test_run_day_success(agent, sample_git_data, temp_journal_dir):
    """Test running orchestrator successfully."""
    agent.git_agent.analyze_day.return_value = sample_git_data
    agent.content_agent.generate_entry.return_value = {
        "status": "complete",
        "full_markdown": "# December 31, 2025\n## Summary\nTest.",
    }
    agent.commit_agent.commit_entry.return_value = {
        "success": True,
        "commit_hash": "abc123",
    }
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    result = agent.run_day(date)

    assert result["status"] == "success"
    assert result["entry_path"] is not None
    assert result["commit_hash"] == "abc123"
    assert result["error"] is None


def test_run_day_no_work_day(agent, temp_journal_dir):
    """Test running orchestrator with no work day."""
    git_data = {
        "date": "2025-12-31",
        "is_work_day": False,
        "total_commits": 0,
        "repos": {},
    }

    agent.git_agent.analyze_day.return_value = git_data
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    result = agent.run_day(date)

    assert result["status"] == "skipped"
    assert result["entry_path"] is None
    assert result["commit_hash"] is None


def test_run_day_content_generation_failed(agent, sample_git_data, temp_journal_dir):
    """Test running orchestrator with failed content generation."""
    agent.git_agent.analyze_day.return_value = sample_git_data
    agent.content_agent.generate_entry.return_value = {
        "status": "failed",
        "error": "LLM error",
    }
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    result = agent.run_day(date)

    assert result["status"] == "failed"
    assert result["error"] == "LLM error"


def test_run_day_exception(agent, temp_journal_dir):
    """Test running orchestrator with an exception."""
    agent.git_agent.analyze_day.side_effect = Exception("Test error")
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    result = agent.run_day(date)

    assert result["status"] == "failed"
    assert "Test error" in result["error"]


def test_run_day_commit_failed(agent, sample_git_data, temp_journal_dir):
    """Test running orchestrator when commit fails."""
    agent.git_agent.analyze_day.return_value = sample_git_data
    agent.content_agent.generate_entry.return_value = {
        "status": "complete",
        "full_markdown": "# December 31, 2025\n## Summary\nTest.",
    }
    agent.commit_agent.commit_entry.return_value = {
        "success": False,
        "error": "Git error",
    }
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    result = agent.run_day(date)

    # Entry should still be created even if commit fails
    assert result["status"] == "success"
    assert result["entry_path"] is not None
    assert result["commit_hash"] is None


def test_write_entry(agent, temp_journal_dir):
    """Test writing entry to disk."""
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    content = "# December 31, 2025\n## Summary\nTest content."

    entry_path = agent._write_entry(date, content)

    assert entry_path.exists()
    assert entry_path.name == "31.md"

    written_content = entry_path.read_text()
    assert written_content == content


def test_write_entry_creates_directory(agent, temp_journal_dir):
    """Test that write_entry creates parent directories."""
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 1, 15)
    content = "# January 15, 2025"

    # Ensure directory doesn't exist
    year_month_dir = temp_journal_dir / "2025" / "01"
    assert not year_month_dir.exists()

    entry_path = agent._write_entry(date, content)

    # Directory should now exist
    assert year_month_dir.exists()
    assert entry_path.exists()


def test_write_entry_correct_path(agent, temp_journal_dir):
    """Test that entry is written to correct path."""
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 6, 15)
    content = "# June 15, 2025"

    entry_path = agent._write_entry(date, content)

    expected_path = temp_journal_dir / "2025" / "06" / "15.md"
    assert entry_path == expected_path


def test_run_day_calls_git_agent(agent, sample_git_data, temp_journal_dir):
    """Test that run_day calls git analysis agent."""
    agent.git_agent.analyze_day.return_value = sample_git_data
    agent.content_agent.generate_entry.return_value = {
        "status": "complete",
        "full_markdown": "# Test",
    }
    agent.commit_agent.commit_entry.return_value = {"success": True}
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    agent.run_day(date)

    agent.git_agent.analyze_day.assert_called_once_with("2025-12-31")


def test_run_day_calls_content_agent(agent, sample_git_data, temp_journal_dir):
    """Test that run_day calls content generation agent."""
    agent.git_agent.analyze_day.return_value = sample_git_data
    agent.content_agent.generate_entry.return_value = {
        "status": "complete",
        "full_markdown": "# Test",
    }
    agent.commit_agent.commit_entry.return_value = {"success": True}
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    agent.run_day(date)

    agent.content_agent.generate_entry.assert_called_once_with(sample_git_data)


def test_run_day_calls_commit_agent(agent, sample_git_data, temp_journal_dir):
    """Test that run_day calls commit agent."""
    agent.git_agent.analyze_day.return_value = sample_git_data
    agent.content_agent.generate_entry.return_value = {
        "status": "complete",
        "full_markdown": "# Test",
    }
    agent.commit_agent.commit_entry.return_value = {"success": True}
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    agent.run_day(date)

    agent.commit_agent.commit_entry.assert_called_once()


def test_run_day_with_multiple_repos(agent, temp_journal_dir):
    """Test running orchestrator with multiple repos."""
    git_data = {
        "date": "2025-12-31",
        "is_work_day": True,
        "total_commits": 100,
        "total_loc_added": 10000,
        "total_loc_deleted": 2000,
        "estimated_hours": 10.0,
        "repos": {
            "repo1": {"commits": 50, "loc_added": 5000, "loc_deleted": 1000},
            "repo2": {"commits": 50, "loc_added": 5000, "loc_deleted": 1000},
        },
    }

    agent.git_agent.analyze_day.return_value = git_data
    agent.content_agent.generate_entry.return_value = {
        "status": "complete",
        "full_markdown": "# Test",
    }
    agent.commit_agent.commit_entry.return_value = {"success": True}
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    result = agent.run_day(date)

    assert result["status"] == "success"


def test_run_day_leap_year(agent, temp_journal_dir):
    """Test running orchestrator for leap year date."""
    git_data = {
        "date": "2024-02-29",
        "is_work_day": True,
        "total_commits": 10,
        "repos": {"test": {"commits": 10}},
    }

    agent.git_agent.analyze_day.return_value = git_data
    agent.content_agent.generate_entry.return_value = {
        "status": "complete",
        "full_markdown": "# Test",
    }
    agent.commit_agent.commit_entry.return_value = {"success": True}
    agent.journal_dir = temp_journal_dir

    date = datetime(2024, 2, 29)
    result = agent.run_day(date)

    assert result["status"] == "success"


def test_write_entry_overwrites_existing(agent, temp_journal_dir):
    """Test that write_entry overwrites existing file."""
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)

    # Write initial content
    agent._write_entry(date, "Original content")

    # Overwrite with new content
    new_content = "Updated content"
    entry_path = agent._write_entry(date, new_content)

    written_content = entry_path.read_text()
    assert written_content == new_content


def test_run_day_date_format(agent, sample_git_data, temp_journal_dir):
    """Test that date is formatted correctly when passed to agents."""
    agent.git_agent.analyze_day.return_value = sample_git_data
    agent.content_agent.generate_entry.return_value = {
        "status": "complete",
        "full_markdown": "# Test",
    }
    agent.commit_agent.commit_entry.return_value = {"success": True}
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 1, 5)  # Single-digit month and day
    agent.run_day(date)

    agent.git_agent.analyze_day.assert_called_once_with("2025-01-05")


def test_write_entry_encoding(agent, temp_journal_dir):
    """Test that write_entry writes with UTF-8 encoding."""
    agent.journal_dir = temp_journal_dir

    date = datetime(2025, 12, 31)
    content = "# December 31, 2025\nTest with unicode: ñ, é, 中文"

    entry_path = agent._write_entry(date, content)

    written_content = entry_path.read_text(encoding="utf-8")
    assert written_content == content
