"""Tests for ContentGenerationAgent."""

from unittest.mock import MagicMock, patch

import pytest

from agents.content_generation import ContentGenerationAgent


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "scheduling": {"opencode_url": "http://localhost:4096"},
        "quality": {"min_commits_for_section": 3},
        "opencode": {"model": "test-model", "provider": "test-provider"},
    }


class TestContentGenerationAgent:
    """Test suite for ContentGenerationAgent."""

    @patch("agents.content_generation.get_config")
    @patch("agents.content_generation.OpenCodeClient")
    def test_init(self, mock_opencode, mock_get_config):
        """Test ContentGenerationAgent initialization."""
        mock_get_config.return_value = {"scheduling": {"opencode_url": "http://localhost:4096"}}

        ContentGenerationAgent()

        mock_opencode.assert_called_once_with(base_url="http://localhost:4096")

    @patch("agents.content_generation.get_config")
    @patch("agents.content_generation.OpenCodeClient")
    def test_generate_entry_no_work_day(self, mock_opencode, mock_get_config, mock_config):
        """Test generate_entry when not a work day."""
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.chat.side_effect = [
            {"content": "No development activity on this date."},
            {"content": ""},
            {"content": ""},
            {"content": "{}"},
        ]
        mock_opencode.return_value = mock_client

        agent = ContentGenerationAgent()

        git_data = {
            "date": "2025-12-31",
            "is_work_day": False,
            "total_commits": 0,
            "total_loc_added": 0,
            "total_loc_deleted": 0,
            "estimated_hours": 0.0,
            "repos": {},
        }

        result = agent.generate_entry(git_data)

        assert result["status"] == "complete"
        assert "No development activity" in result["summary"]

    @patch("agents.content_generation.get_config")
    @patch("agents.content_generation.OpenCodeClient")
    def test_generate_entry_error_handling(self, mock_opencode, mock_get_config, mock_config):
        """Test generate_entry error handling."""
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("API error")
        mock_opencode.return_value = mock_client

        agent = ContentGenerationAgent()

        git_data = {
            "date": "2025-12-31",
            "is_work_day": True,
            "total_commits": 10,
            "total_loc_added": 1000,
            "total_loc_deleted": 200,
            "estimated_hours": 5.0,
            "repos": {},
        }

        result = agent.generate_entry(git_data)

        assert result["status"] == "failed"
        assert "error" in result

    @patch("agents.content_generation.get_config")
    def test_generate_repositories_section(self, mock_get_config, mock_config):
        """Test _generate_repositories_section."""
        mock_get_config.return_value = mock_config
        agent = ContentGenerationAgent()

        git_data = {
            "repos": {
                "repo1": {"commits": 5},
                "repo2": {"commits": 10},
                "repo3": {"commits": 3},
            }
        }

        result = agent._generate_repositories_section(git_data)

        assert "## Repositories Worked On" in result
        assert "`~/code/repo1`" in result
        assert "`~/code/repo2`" in result
        assert "`~/code/repo3`" in result
        assert "Total: 18 commits" in result

    def test_generate_activity_summary_no_work_day(self, mock_config):
        """Test _generate_activity_summary when not a work day."""
        git_data = {"is_work_day": False}

        with patch("agents.content_generation.get_config", return_value=mock_config):
            with patch("agents.content_generation.OpenCodeClient"):
                agent = ContentGenerationAgent()
                result = agent._generate_activity_summary(git_data, {})

        assert result == ""
