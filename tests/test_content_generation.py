"""Test Content Generation Agent."""

import json
from unittest.mock import patch

import pytest

from agents.content_generation import ContentGenerationAgent


@pytest.fixture
def agent():
    """Create ContentGenerationAgent with mocked config."""
    mock_config = {
        "scheduling": {
            "opencode_url": "http://127.0.0.1:4096",
        },
        "opencode": {
            "model": "glm-4.7-free",
            "provider": "opencode",
        },
        "quality": {
            "min_commits_for_section": 3,
        },
    }

    with patch("agents.content_generation.get_config", return_value=mock_config):
        with patch("agents.content_generation.OpenCodeClient") as mock_client:
            agent = ContentGenerationAgent()
            agent.client = mock_client.return_value
            yield agent


@pytest.fixture
def sample_git_data():
    """Provide sample git data for testing."""
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
                "commits_by_category": {
                    "feat": 25,
                    "fix": 10,
                    "refactor": 5,
                    "docs": 3,
                },
                "top_features": [
                    "feat(TASK-102): Add Staleness Awareness UI",
                    "feat: Display staleness indicators",
                ],
                "first_commit": "2025-12-31 09:00:00",
                "last_commit": "2025-12-31 17:00:00",
                "commit_messages": [
                    "feat(TASK-102): Add Staleness Awareness UI",
                    "feat: Display staleness indicators",
                ],
            }
        },
    }


def test_generate_entry_success(agent, sample_git_data):
    """Test successful entry generation."""
    agent.client.chat.return_value = {"content": "Generated content"}

    with patch("agents.content_generation.load_projects_cache", return_value={}):
        result = agent.generate_entry(sample_git_data)

    assert result["status"] == "complete"
    assert "header" in result
    assert "summary" in result
    assert "repositories_section" in result
    assert "full_markdown" in result


def test_generate_entry_no_work_day(agent):
    """Test entry generation for non-work day."""
    git_data = {
        "date": "2025-12-31",
        "is_work_day": False,
        "total_commits": 0,
        "total_loc_added": 0,
        "total_loc_deleted": 0,
        "estimated_hours": 0.0,
        "repos": {},
    }

    with patch("agents.content_generation.load_projects_cache", return_value={}):
        result = agent.generate_entry(git_data)

    assert result["status"] == "complete"
    assert result["summary"] == "No development activity on this date."


def test_generate_entry_error(agent, sample_git_data):
    """Test entry generation with error."""
    agent.client.chat.side_effect = Exception("LLM error")

    result = agent.generate_entry(sample_git_data)

    assert result["status"] == "failed"
    assert "error" in result


def test_generate_header(agent):
    """Test header generation."""
    git_data = {
        "date": "2025-12-31",
        "estimated_hours": 8.5,
        "total_loc_added": 4000,
        "total_loc_deleted": 800,
    }

    with patch("agents.content_generation.format_header") as mock_format:
        mock_format.return_value = "Header content"

        header = agent._generate_header(git_data)

        assert header == "Header content"
        mock_format.assert_called_once_with("2025-12-31", 8.5, 4800)


def test_generate_summary(agent, sample_git_data):
    """Test summary generation."""
    agent.client.chat.return_value = {"content": "Test summary"}

    summary = agent._generate_summary(sample_git_data)

    assert summary == "Test summary"
    agent.client.chat.assert_called_once()


def test_generate_repositories_section(agent, sample_git_data):
    """Test repositories section generation."""
    section = agent._generate_repositories_section(sample_git_data)

    assert "## Repositories Worked On" in section
    assert "test-repo" in section
    assert "43 commits" in section
    assert "Total:" in section


def test_generate_repositories_section_empty(agent):
    """Test repositories section with no repos."""
    git_data = {"date": "2025-12-31", "repos": {}}

    section = agent._generate_repositories_section(git_data)

    assert "## Repositories Worked On" in section


def test_generate_project_sections(agent, sample_git_data):
    """Test project sections generation."""
    agent.client.chat.return_value = {"content": "## test-repo\n\n- Feat: feature"}

    sections = agent._generate_project_sections(sample_git_data)

    assert "test-repo" in sections
    assert len(sections) == 1


def test_generate_project_sections_below_threshold(agent, sample_git_data):
    """Test project sections with commits below threshold."""
    git_data = {
        "repos": {
            "small-repo": {
                "commits": 2,
                "commits_by_category": {"feat": 1, "fix": 1},
                "top_features": ["feat: feature"],
            }
        }
    }

    sections = agent._generate_project_sections(git_data)

    assert len(sections) == 0


def test_generate_activity_summary(agent, sample_git_data):
    """Test activity summary generation."""
    agent.client.chat.return_value = {
        "content": "## Summary of Activity\n\n1. Added feature\n2. Fixed bug"
    }

    summary = agent._generate_activity_summary(sample_git_data)

    assert "Summary of Activity" in summary
    agent.client.chat.assert_called_once()


def test_generate_activity_summary_no_work_day(agent):
    """Test activity summary for non-work day."""
    git_data = {"date": "2025-12-31", "is_work_day": False}

    summary = agent._generate_activity_summary(git_data)

    assert summary == ""


def test_generate_projects_legend(agent, sample_git_data):
    """Test projects legend generation."""
    agent.client.chat.return_value = {
        "content": json.dumps({"test-repo": "Test repository description"})
    }

    with patch("agents.content_generation.save_projects_cache"):
        legend = agent._generate_projects_legend(sample_git_data)

    assert "## Projects Legend" in legend
    assert "test-repo" in legend


def test_generate_projects_legend_invalid_json(agent, sample_git_data):
    """Test projects legend with invalid JSON response."""
    agent.client.chat.return_value = {"content": "invalid json"}

    with patch("agents.content_generation.load_projects_cache", return_value={}):
        legend = agent._generate_projects_legend(sample_git_data)

    assert "## Projects Legend" in legend


def test_assemble_full_markdown(agent, sample_git_data):
    """Test assembling full markdown."""
    agent.client.chat.return_value = {"content": "Generated content"}

    with patch("agents.content_generation.load_projects_cache", return_value={}):
        result = agent.generate_entry(sample_git_data)

    assert result["full_markdown"] != ""
    assert "## Summary" in result["full_markdown"]
    assert "## Repositories Worked On" in result["full_markdown"]


def test_generate_entry_multiple_repos(agent):
    """Test entry generation with multiple repos."""
    git_data = {
        "date": "2025-12-31",
        "is_work_day": True,
        "total_commits": 50,
        "total_loc_added": 5000,
        "total_loc_deleted": 1000,
        "estimated_hours": 8.0,
        "repos": {
            "repo1": {
                "commits": 25,
                "commits_by_category": {"feat": 20, "fix": 5},
                "top_features": ["feat: feature1"],
                "first_commit": "2025-12-31 09:00:00",
                "last_commit": "2025-12-31 12:00:00",
                "commit_messages": ["feat: feature1"],
            },
            "repo2": {
                "commits": 25,
                "commits_by_category": {"feat": 15, "fix": 10},
                "top_features": ["feat: feature2"],
                "first_commit": "2025-12-31 13:00:00",
                "last_commit": "2025-12-31 17:00:00",
                "commit_messages": ["feat: feature2"],
            },
        },
    }

    agent.client.chat.return_value = {"content": "Generated content"}

    with patch("agents.content_generation.load_projects_cache", return_value={}):
        result = agent.generate_entry(git_data)

    assert result["status"] == "complete"
    assert "repo1" in result["project_sections"]
    assert "repo2" in result["project_sections"]


def test_generate_header_minutes(agent):
    """Test header generation with minutes instead of hours."""
    git_data = {
        "date": "2025-12-31",
        "estimated_hours": 0.5,
        "total_loc_added": 100,
        "total_loc_deleted": 20,
    }

    with patch("agents.content_generation.format_header") as mock_format:
        mock_format.return_value = "Header"

        agent._generate_header(git_data)

        mock_format.assert_called_once_with("2025-12-31", 0.5, 120)
