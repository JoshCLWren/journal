"""Tests for GitAnalysisAgent."""

from unittest.mock import patch

import pytest

from agents.git_analysis import GitAnalysisAgent


@pytest.fixture
def git_agent():
    """Create a GitAnalysisAgent instance for testing."""
    return GitAnalysisAgent()


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "general": {
            "author_name": "Test User",
            "author_email": "test@example.com",
            "code_directory": "/tmp/test_code",
            "journal_directory": "/tmp/test_journal",
        },
        "git": {
            "exclude_repos": ["journal", "test-exclude"],
            "exclude_patterns": ["test-pattern"],
        },
    }


class TestGitAnalysisAgent:
    """Test suite for GitAnalysisAgent."""

    @patch("agents.git_analysis.get_config")
    def test_init(self, mock_get_config, mock_config):
        """Test GitAnalysisAgent initialization."""
        mock_get_config.return_value = mock_config

        agent = GitAnalysisAgent()

        assert agent.config == mock_config
        assert agent.author_name == "Test User"
        assert str(agent.code_dir) == "/tmp/test_code"
        assert str(agent.journal_dir) == "/tmp/test_journal"

    @patch("agents.git_analysis.get_config")
    @patch("agents.git_analysis.is_work_day")
    @patch("agents.git_analysis.get_commits_by_date")
    @patch("agents.git_analysis.calculate_loc_changes")
    def test_analyze_day_no_commits(
        self,
        mock_calculate_loc,
        mock_get_commits,
        mock_is_work_day,
        mock_get_config,
        mock_config,
        git_agent,
    ):
        """Test analyze_day when no commits are found."""
        mock_get_config.return_value = mock_config
        mock_is_work_day.return_value = False
        mock_get_commits.return_value = []

        with patch.object(git_agent, "_get_all_repos", return_value=["test-repo"]):
            result = git_agent.analyze_day("2025-12-31")

        assert result["date"] == "2025-12-31"
        assert result["is_work_day"] is False
        assert result["total_commits"] == 0
        assert result["total_loc_added"] == 0
        assert result["total_loc_deleted"] == 0
        assert result["estimated_hours"] == 0.0
        assert result["repos"] == {}

    @patch("agents.git_analysis.get_config")
    @patch("agents.git_analysis.is_work_day")
    @patch("agents.git_analysis.get_commits_by_date")
    @patch("agents.git_analysis.calculate_loc_changes_for_hashes")
    def test_analyze_day_with_commits(
        self,
        mock_calculate_loc,
        mock_get_commits,
        mock_is_work_day,
        mock_get_config,
        mock_config,
    ):
        """Test analyze_day with commits."""
        mock_get_config.return_value = mock_config
        mock_is_work_day.return_value = True

        sample_commits = [
            {"hash": "abc123", "timestamp": "2025-12-31T10:00:00", "message": "feat: new feature"},
            {"hash": "def456", "timestamp": "2025-12-31T14:00:00", "message": "fix: bug fix"},
        ]

        mock_get_commits.return_value = sample_commits
        mock_calculate_loc.return_value = (100, 20)

        with patch("agents.git_analysis.get_config", return_value=mock_config):
            agent = GitAnalysisAgent()
            with patch.object(agent, "_get_all_repos", return_value=["test-repo"]):
                with patch.object(agent, "_should_scan_repo", return_value=True):
                    result = agent.analyze_day("2025-12-31")

        assert result["date"] == "2025-12-31"
        assert result["is_work_day"] is True
        assert result["total_commits"] == 2
        assert result["total_loc_added"] == 100
        assert result["total_loc_deleted"] == 20
        assert "test-repo" in result["repos"]
        assert result["repos"]["test-repo"]["commits"] == 2
        assert result["repos"]["test-repo"]["loc_added"] == 100
        assert result["repos"]["test-repo"]["loc_deleted"] == 20
        assert result["estimated_hours"] > 0

    @patch("agents.git_analysis.get_config")
    @patch("agents.git_analysis.is_work_day")
    @patch("agents.git_analysis.get_commits_by_date")
    @patch("agents.git_analysis.calculate_loc_changes_for_hashes")
    def test_analyze_day_multiple_repos(
        self,
        mock_calculate_loc,
        mock_get_commits,
        mock_is_work_day,
        mock_get_config,
        mock_config,
    ):
        """Test analyze_day with multiple repositories."""
        mock_get_config.return_value = mock_config
        mock_is_work_day.return_value = True

        def mock_get_commits_side_effect(repo_path, date, author):
            repo_name = str(repo_path).split("/")[-1]
            if repo_name == "repo1":
                return [
                    {
                        "hash": "abc123",
                        "timestamp": "2025-12-31T10:00:00",
                        "message": "feat: feature1",
                    }
                ]
            elif repo_name == "repo2":
                return [
                    {"hash": "def456", "timestamp": "2025-12-31T12:00:00", "message": "fix: fix1"},
                    {
                        "hash": "ghi789",
                        "timestamp": "2025-12-31T14:00:00",
                        "message": "feat: feature2",
                    },
                ]
            return []

        mock_get_commits.side_effect = mock_get_commits_side_effect
        mock_calculate_loc.return_value = (50, 10)

        with patch("agents.git_analysis.get_config", return_value=mock_config):
            agent = GitAnalysisAgent()
            with patch.object(agent, "_get_all_repos", return_value=["repo1", "repo2"]):
                with patch.object(agent, "_should_scan_repo", return_value=True):
                    result = agent.analyze_day("2025-12-31")

        assert result["total_commits"] == 3
        assert len(result["repos"]) == 2
        assert result["repos"]["repo1"]["commits"] == 1
        assert result["repos"]["repo2"]["commits"] == 2

    @patch("agents.git_analysis.get_config")
    def test_should_scan_repo_excludes_journal(self, mock_get_config, mock_config, git_agent):
        """Test _should_scan_repo excludes journal directory."""
        mock_get_config.return_value = mock_config

        assert git_agent._should_scan_repo("journal") is False

    @patch("agents.git_analysis.get_config")
    @patch("pathlib.Path.exists")
    def test_should_scan_repo_non_git_directory(
        self, mock_exists, mock_get_config, mock_config, git_agent
    ):
        """Test _should_scan_repo returns False for non-git directories."""
        mock_get_config.return_value = mock_config
        mock_exists.return_value = False

        assert git_agent._should_scan_repo("non-git-repo") is False

    def test_categorize_commits(self, git_agent):
        """Test _categorize_commits groups commits by type."""
        commits = [
            {"message": "feat: new feature"},
            {"message": "fix: bug fix"},
            {"message": "feat: another feature"},
            {"message": "chore: update deps"},
            {"message": "refactor: improve code"},
        ]

        result = git_agent._categorize_commits(commits)

        assert result["feat"] == 2
        assert result["fix"] == 1
        assert result["chore"] == 1
        assert result["refactor"] == 1

    def test_extract_top_features(self, git_agent):
        """Test _extract_top_filters significant commits."""
        commits = [
            {"message": "feat: major feature 1"},
            {"message": "feat: major feature 2"},
            {"message": "fix: bug fix"},
            {"message": "chore: minor update"},
            {"message": "style: formatting"},
            {"message": "feat: major feature 3"},
        ]

        result = git_agent._extract_top_features(commits)

        assert len(result) <= 5
        assert "feat: major feature 1" in result
        assert "feat: major feature 2" in result
        assert not any("chore:" in msg for msg in result)
        assert not any("style:" in msg for msg in result)

    def test_extract_top_features_deduplication(self, git_agent):
        """Test _extract_top_features deduplicates similar commits."""
        commits = [
            {"message": "feat: add user authentication system with OAuth support"},
            {"message": "feat: add user authentication system with social login"},
            {"message": "fix: authentication bug"},
        ]

        result = git_agent._extract_top_features(commits)

        assert len(result) <= 5
        assert len(result) >= 1

    def test_estimate_hours(self, git_agent):
        """Test _estimate_hours calculates work hours."""
        repo_results = {
            "repo1": {
                "first_commit": "2025-12-31T09:00:00",
                "last_commit": "2025-12-31T17:00:00",
                "commits": 10,
            }
        }

        result = git_agent._estimate_hours(repo_results)

        assert result > 0
        assert result < 24

    def test_estimate_hours_no_timestamps(self, git_agent):
        """Test _estimate_hours with no timestamps."""
        repo_results = {"repo1": {}}

        result = git_agent._estimate_hours(repo_results)

        assert result == 0.0

    def test_estimate_hours_multiple_repos(self, git_agent):
        """Test _estimate_hours across multiple repos."""
        repo_results = {
            "repo1": {
                "first_commit": "2025-12-31T09:00:00",
                "last_commit": "2025-12-31T12:00:00",
                "commits": 5,
            },
            "repo2": {
                "first_commit": "2025-12-31T13:00:00",
                "last_commit": "2025-12-31T17:00:00",
                "commits": 8,
            },
        }

        result = git_agent._estimate_hours(repo_results)

        assert result > 0
        assert result <= 20

    @patch("agents.git_analysis.get_config")
    def test_get_all_repos_filters_excluded(self, mock_get_config, temp_dir):
        """Test _get_all_repos filters excluded repos and patterns."""
        mock_config = {
            "general": {
                "author_name": "Test User",
                "author_email": "test@example.com",
                "code_directory": str(temp_dir),
                "journal_directory": "/tmp/test_journal",
            },
            "git": {
                "exclude_repos": ["journal", "test-exclude"],
                "exclude_patterns": ["temp"],
            },
        }
        mock_get_config.return_value = mock_config

        (temp_dir / "repo1").mkdir()
        (temp_dir / "repo1" / ".git").mkdir()
        (temp_dir / "temp-repo").mkdir()
        (temp_dir / "temp-repo" / ".git").mkdir()
        (temp_dir / "journal").mkdir()
        (temp_dir / "journal" / ".git").mkdir()

        agent = GitAnalysisAgent()
        result = agent._get_all_repos()

        assert "repo1" in result
        assert "temp-repo" not in result
        assert "journal" not in result
