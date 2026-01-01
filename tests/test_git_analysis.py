"""Test Git Analysis Agent."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from agents.git_analysis import GitAnalysisAgent


@pytest.fixture
def mock_config():
    """Provide a mock configuration."""
    return {
        "general": {
            "author_name": "Test User",
            "author_email": "test@example.com",
            "code_directory": "/tmp/test_code",
            "journal_directory": "/tmp/test_journal",
        },
        "git": {
            "exclude_repos": ["journal", "excluded-repo"],
            "exclude_patterns": ["task-", "work-"],
        },
    }


@pytest.fixture
def temp_code_dir():
    """Provide a temporary code directory with repos."""
    with TemporaryDirectory() as tmpdir:
        code_dir = Path(tmpdir)

        # Create mock git repos
        repo1 = code_dir / "repo1"
        repo2 = code_dir / "repo2"
        excluded = code_dir / "excluded-repo"

        for repo in [repo1, repo2, excluded]:
            repo.mkdir()
            (repo / ".git").mkdir()

        yield code_dir


@pytest.fixture
def agent(mock_config, temp_code_dir):
    """Create GitAnalysisAgent with mocked config."""
    with patch("agents.git_analysis.get_config", return_value=mock_config):
        with patch("agents.git_analysis.Path", lambda *args, **kwargs: Path(*args, **kwargs)):
            agent = GitAnalysisAgent()
            agent.code_dir = temp_code_dir
            agent.journal_dir = Path(mock_config["general"]["journal_directory"])
            agent.author_name = mock_config["general"]["author_name"]
            yield agent


def test_git_analysis_agent_init(agent):
    """Test agent initialization."""
    assert agent.author_name == "Test User"
    assert agent.code_dir.is_dir()


def test_analyze_day_no_commits(agent):
    """Test analyzing a day with no commits."""
    with patch("agents.git_analysis.is_work_day", return_value=False):
        result = agent.analyze_day("2025-12-31")

        assert result["date"] == "2025-12-31"
        assert result["is_work_day"] is False
        assert result["total_commits"] == 0


def test_analyze_day_with_commits(agent):
    """Test analyzing a day with commits."""
    mock_commits = [
        {"hash": "abc123", "timestamp": "2025-12-31 10:00:00", "message": "feat: add feature"},
        {"hash": "def456", "timestamp": "2025-12-31 11:00:00", "message": "fix: fix bug"},
    ]

    with (
        patch("agents.git_analysis.is_work_day", return_value=True),
        patch("agents.git_analysis.get_commits_by_date", return_value=mock_commits),
        patch("agents.git_analysis.calculate_loc_changes", return_value=(100, 20)),
    ):
        result = agent.analyze_day("2025-12-31")

        assert result["is_work_day"] is True
        assert result["total_commits"] == 2
        assert result["total_loc_added"] == 100
        assert result["total_loc_deleted"] == 20


def test_get_all_repos(agent, temp_code_dir):
    """Test getting all repositories."""
    repos = agent._get_all_repos()

    # Should include repo1 and repo2, but not excluded-repo or directories without .git
    assert "repo1" in repos
    assert "repo2" in repos
    assert "excluded-repo" not in repos


def test_should_scan_repo(agent):
    """Test repo scanning filter."""
    assert agent._should_scan_repo("repo1") is True
    assert agent._should_scan_repo("journal") is False


def test_categorize_commits(agent):
    """Test categorizing commits by type."""
    commits = [
        {"message": "feat: add feature"},
        {"message": "feat: another feature"},
        {"message": "fix: fix bug"},
        {"message": "chore: update deps"},
    ]

    categories = agent._categorize_commits(commits)

    assert categories.get("feat") == 2
    assert categories.get("fix") == 1
    assert categories.get("chore") == 1


def test_extract_top_features(agent):
    """Test extracting top features from commits."""
    commits = [
        {"message": "feat(TASK-1): add feature 1"},
        {"message": "feat(TASK-2): add feature 2"},
        {"message": "chore: update deps"},
        {"message": "fix: minor bug"},
        {
            "message": "feat: feature 3 is very long and should be truncated when displayed in the journal entry because it exceeds the character limit"
        },
    ]

    features = agent._extract_top_features(commits)

    assert len(features) <= 5
    assert any("TASK-1" in f for f in features)
    # chore and fix should be filtered out
    assert not any("chore" in f for f in features)


def test_estimate_hours_no_timestamps(agent):
    """Test hour estimation with no timestamps."""
    repo_results = {}

    hours = agent._estimate_hours(repo_results)

    assert hours == 0.0


def test_estimate_hours_with_timestamps(agent):
    """Test hour estimation with timestamps."""
    repo_results = {
        "repo1": {
            "first_commit": "2025-12-31 09:00:00",
            "last_commit": "2025-12-31 17:00:00",
            "commits": 10,
        }
    }

    hours = agent._estimate_hours(repo_results)

    assert hours > 0
    assert hours < 24  # Should be less than 24 hours


def test_estimate_hours_high_commits_per_hour(agent):
    """Test hour estimation with high commits per hour."""
    repo_results = {
        "repo1": {
            "first_commit": "2025-12-31 09:00:00",
            "last_commit": "2025-12-31 10:00:00",
            "commits": 30,  # High rate
        }
    }

    hours = agent._estimate_hours(repo_results)

    # Should adjust for high commit rate
    assert hours > 0


def test_estimate_hours_low_commits_per_hour(agent):
    """Test hour estimation with low commits per hour."""
    repo_results = {
        "repo1": {
            "first_commit": "2025-12-31 09:00:00",
            "last_commit": "2025-12-31 17:00:00",
            "commits": 5,  # Low rate
        }
    }

    hours = agent._estimate_hours(repo_results)

    # Should adjust for low commit rate
    assert hours > 0


def test_analyze_day_multiple_repos(agent):
    """Test analyzing multiple repositories."""
    mock_commits = [
        {"hash": "abc123", "timestamp": "2025-12-31 10:00:00", "message": "feat: add feature"},
    ]

    with (
        patch("agents.git_analysis.is_work_day", return_value=True),
        patch("agents.git_analysis.get_commits_by_date", return_value=mock_commits),
        patch("agents.git_analysis.calculate_loc_changes", return_value=(50, 10)),
    ):
        result = agent.analyze_day("2025-12-31")

        assert "repos" in result
        assert result["total_commits"] >= 0


def test_exclude_patterns(agent, temp_code_dir):
    """Test that exclude patterns work correctly."""
    # Create a repo that matches exclude pattern
    task_repo = temp_code_dir / "task-123"
    task_repo.mkdir()
    (task_repo / ".git").mkdir()

    repos = agent._get_all_repos()

    assert "task-123" not in repos
    assert "repo1" in repos


def test_extract_top_features_de_duplicates(agent):
    """Test that feature extraction removes duplicates."""
    commits = [
        {"message": "feat(TASK-1): add feature"},
        {"message": "feat(TASK-1): add feature"},
        {"message": "feat(TASK-2): another feature"},
    ]

    features = agent._extract_top_features(commits)

    # Should not have duplicate features
    assert len(features) == 2
    assert len(set(features)) == len(features)


def test_analyze_day_commits_data_includes_messages(agent):
    """Test that commit messages are included in results."""
    mock_commits = [
        {"hash": "abc123", "timestamp": "2025-12-31 10:00:00", "message": "feat: add feature"},
        {"hash": "def456", "timestamp": "2025-12-31 11:00:00", "message": "fix: fix bug"},
    ]

    with (
        patch("agents.git_analysis.is_work_day", return_value=True),
        patch("agents.git_analysis.get_commits_by_date", return_value=mock_commits),
        patch("agents.git_analysis.calculate_loc_changes", return_value=(100, 20)),
    ):
        result = agent.analyze_day("2025-12-31")

        for _repo_name, repo_data in result["repos"].items():
            assert "commit_messages" in repo_data
            assert len(repo_data["commit_messages"]) > 0
