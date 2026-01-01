"""Tests for FactCheckingAgent."""

from unittest.mock import MagicMock, patch

import pytest

from agents.fact_checking import FactCheckingAgent


@pytest.fixture
def fact_checking_agent():
    """Create a FactCheckingAgent instance for testing."""
    return FactCheckingAgent()


@pytest.fixture
def sample_git_data():
    """Sample git data for testing."""
    return {
        "date": "2025-12-31",
        "is_work_day": True,
        "total_commits": 43,
        "total_loc_added": 1200,
        "total_loc_deleted": 200,
        "estimated_hours": 8.0,
        "repos": {
            "comic-pile": {
                "commits": 43,
                "loc_added": 1200,
                "loc_deleted": 200,
                "commits_by_category": {"feat": 25, "fix": 10, "refactor": 5, "docs": 3},
                "top_features": ["feat(TASK-102): Add Staleness Awareness UI"],
            }
        },
    }


@pytest.fixture
def valid_markdown():
    """Valid markdown content for testing."""
    return """## 2025-12-31 (8.0 hours, 1400 LOC)

## Summary
Test summary.

## Repositories Worked On
- `~/code/comic-pile` (43 commits)

- **Total: 43 commits**

## comic-pile
**Staleness Awareness**
- feat: Add Staleness Awareness UI
- fix: Update cache logic

---
## Projects Legend
### comic-pile
Test project description."""


class TestFactCheckingAgent:
    """Test suite for FactCheckingAgent."""

    @patch("agents.fact_checking.get_config")
    @patch("agents.fact_checking.OpenCodeClient")
    def test_init(self, mock_opencode, mock_get_config):
        """Test FactCheckingAgent initialization."""
        mock_get_config.return_value = {"scheduling": {"opencode_url": "http://localhost:4096"}}

        FactCheckingAgent()

        mock_opencode.assert_called_once_with(base_url="http://localhost:4096")

    @patch("agents.fact_checking.get_config")
    @patch("agents.fact_checking.OpenCodeClient")
    def test_check_entry_valid(
        self, mock_opencode, mock_get_config, sample_git_data, valid_markdown
    ):
        """Test check_entry with valid content."""
        mock_get_config.return_value = {
            "scheduling": {"opencode_url": "http://localhost:4096"},
            "opencode": {"model": "test-model", "provider": "test-provider"},
        }

        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "content": "Overall Assessment: EXCELLENT. All checks passed."
        }
        mock_opencode.return_value = mock_client

        fact_checking_agent = FactCheckingAgent()

        result = fact_checking_agent.check_entry(sample_git_data, valid_markdown)

        assert result["status"] == "pass"
        assert len(result["errors"]) == 0
        assert "reasoning" in result
        assert "checks" in result

    @patch("agents.fact_checking.get_config")
    @patch("agents.fact_checking.OpenCodeClient")
    def test_check_entry_error_handling(self, mock_opencode, mock_get_config, sample_git_data):
        """Test check_entry error handling."""
        mock_get_config.return_value = {
            "scheduling": {"opencode_url": "http://localhost:4096"},
            "opencode": {"model": "test-model", "provider": "test-provider"},
        }

        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("API error")
        mock_opencode.return_value = mock_client

        fact_checking_agent = FactCheckingAgent()

        result = fact_checking_agent.check_entry(sample_git_data, "markdown")

        assert result["status"] == "fail"
        assert len(result["errors"]) > 0

    def test_check_accuracy_valid(self, fact_checking_agent, sample_git_data, valid_markdown):
        """Test _check_accuracy with accurate data."""
        result = fact_checking_agent._check_accuracy(sample_git_data, valid_markdown)

        assert result["passed"] is True
        assert len(result["issues"]) == 0

    def test_check_accuracy_commit_count_mismatch(self, fact_checking_agent, sample_git_data):
        """Test _check_accuracy detects commit count mismatch."""
        markdown = """## Repositories Worked On
- `~/code/comic-pile` (10 commits)
- **Total: 10 commits**"""

        result = fact_checking_agent._check_accuracy(sample_git_data, markdown)

        assert result["passed"] is False
        assert len(result["issues"]) > 0
        assert "commit count mismatch" in result["issues"][0].lower()

    def test_check_accuracy_missing_commit_count(self, fact_checking_agent, sample_git_data):
        """Test _check_accuracy detects missing commit count."""
        markdown = """## Repositories Worked On
- `~/code/comic-pile`
- **Total: 43 commits**"""

        result = fact_checking_agent._check_accuracy(sample_git_data, markdown)

        assert result["passed"] is False
        assert len(result["issues"]) > 0

    def test_check_completeness_valid(self, fact_checking_agent, sample_git_data, valid_markdown):
        """Test _check_completeness with complete content."""
        result = fact_checking_agent._check_completeness(sample_git_data, valid_markdown)

        assert result["passed"] is True

    def test_check_completeness_missing_section(self, fact_checking_agent, sample_git_data):
        """Test _check_completeness detects missing repo section."""
        markdown = """## Summary
Test summary.
## Repositories Worked On
- `~/code/comic-pile` (43 commits)"""

        result = fact_checking_agent._check_completeness(sample_git_data, markdown)

        assert result["passed"] is False
        assert len(result["issues"]) > 0
        assert "Missing section header" in result["issues"][0]

    def test_check_consistency_valid(self, fact_checking_agent, sample_git_data, valid_markdown):
        """Test _check_consistency with consistent data."""
        result = fact_checking_agent._check_consistency(sample_git_data, valid_markdown)

        assert result["passed"] is True

    def test_check_consistency_loc_mismatch(self, fact_checking_agent, sample_git_data):
        """Test _check_consistency detects LOC mismatch."""
        markdown = "Total LOC: 10000 lines of code"

        result = fact_checking_agent._check_consistency(sample_git_data, markdown)

        assert result["passed"] is False
        assert len(result["issues"]) > 0
        assert "LOC inconsistency" in result["issues"][0]

    def test_check_consistency_date_missing(self, fact_checking_agent, sample_git_data):
        """Test _check_consistency detects missing date."""
        markdown = "Test content without date 2025-01-01"

        result = fact_checking_agent._check_consistency(sample_git_data, markdown)

        assert result["passed"] is False
        assert "not found in markdown" in result["issues"][0]

    def test_check_duplicates_valid(self, fact_checking_agent, valid_markdown):
        """Test _check_duplicates with unique content."""
        result = fact_checking_agent._check_duplicates(valid_markdown)

        assert result["passed"] is True

    def test_check_duplicates_sections(self, fact_checking_agent):
        """Test _check_duplicates detects duplicate sections."""
        markdown = """## Summary
Test.
## Summary
Duplicate section."""

        result = fact_checking_agent._check_duplicates(markdown)

        assert result["passed"] is False
        assert len(result["issues"]) > 0
        assert "Duplicate section" in result["issues"][0]

    def test_check_duplicates_commits(self, fact_checking_agent):
        """Test _check_duplicates detects duplicate commits."""
        markdown = """## Summary
- feat: add feature
- feat: add feature"""

        result = fact_checking_agent._check_duplicates(markdown)

        assert result["passed"] is False
        assert len(result["issues"]) > 0
        assert "Duplicate commit" in result["issues"][0]

    def test_check_anomalies_valid(self, fact_checking_agent, sample_git_data, valid_markdown):
        """Test _check_anomalies with normal data."""
        result = fact_checking_agent._check_anomalies(sample_git_data, valid_markdown)

        assert result["passed"] is True

    def test_check_anomalies_zero_loc(self, fact_checking_agent):
        """Test _check_anomalies detects zero LOC with commits."""
        git_data = {"repos": {"test-repo": {"commits": 10, "loc_added": 0}}}

        result = fact_checking_agent._check_anomalies(git_data, "test")

        assert len(result["issues"]) > 0
        assert "0 LOC added" in result["issues"][0]

    def test_check_anomalies_low_loc_ratio(self, fact_checking_agent):
        """Test _check_anomalies detects low LOC/commit ratio."""
        git_data = {"repos": {"test-repo": {"commits": 10, "loc_added": 20}}}

        result = fact_checking_agent._check_anomalies(git_data, "test")

        assert len(result["issues"]) > 0
        assert "low LOC/commit ratio" in result["issues"][0]

    def test_check_anomalies_many_sections(self, fact_checking_agent):
        """Test _check_anomalies detects too many sections."""
        markdown = "\n".join([f"## Section {i}" for i in range(25)])

        result = fact_checking_agent._check_anomalies({}, markdown)

        assert len(result["issues"]) > 0
        assert "Unusually many sections" in result["issues"][0]

    @patch("agents.fact_checking.get_config")
    @patch("agents.fact_checking.OpenCodeClient")
    def test_generate_llm_analysis(self, mock_opencode, mock_get_config, sample_git_data):
        """Test _generate_llm_analysis."""
        mock_get_config.return_value = {
            "scheduling": {"opencode_url": "http://localhost:4096"},
            "opencode": {"model": "test-model", "provider": "test-provider"},
        }

        mock_client = MagicMock()
        mock_client.chat.return_value = {"content": "Overall Assessment: GOOD. All checks passed."}
        mock_opencode.return_value = mock_client

        fact_checking_agent = FactCheckingAgent()

        checks = {
            "accuracy": {"passed": True, "issues": []},
            "completeness": {"passed": True, "issues": []},
        }

        result = fact_checking_agent._generate_llm_analysis(
            sample_git_data, "markdown content", checks
        )

        assert "Overall Assessment" in result

    @patch("agents.fact_checking.get_config")
    @patch("agents.fact_checking.OpenCodeClient")
    def test_generate_llm_analysis_error(self, mock_opencode, mock_get_config, sample_git_data):
        """Test _generate_llm_analysis error handling."""
        mock_get_config.return_value = {
            "scheduling": {"opencode_url": "http://localhost:4096"},
            "opencode": {"model": "test-model", "provider": "test-provider"},
        }

        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("API error")
        mock_opencode.return_value = mock_client

        fact_checking_agent = FactCheckingAgent()

        checks = {"accuracy": {"passed": True, "issues": []}}

        result = fact_checking_agent._generate_llm_analysis(
            sample_git_data, "markdown content", checks
        )

        assert "LLM analysis failed" in result

    def test_compile_results_pass(self, fact_checking_agent):
        """Test _compile_results with all checks passing."""
        result = {
            "status": "pass",
            "errors": [],
            "warnings": [],
            "corrections": [],
            "checks": {
                "accuracy": {"passed": True, "issues": []},
                "completeness": {"passed": True, "issues": []},
            },
        }

        fact_checking_agent._compile_results(result)

        assert result["status"] == "pass"

    def test_compile_results_fail(self, fact_checking_agent):
        """Test _compile_results with errors."""
        result = {
            "status": "pass",
            "errors": [],
            "warnings": [],
            "corrections": [],
            "checks": {
                "accuracy": {"passed": False, "issues": ["Test error"], "corrections": []},
            },
        }

        fact_checking_agent._compile_results(result)

        assert result["status"] == "fail"
        assert len(result["errors"]) > 0

    def test_compile_results_warnings(self, fact_checking_agent):
        """Test _compile_results with warnings."""
        result = {
            "status": "pass",
            "errors": [],
            "warnings": [],
            "corrections": [],
            "checks": {
                "accuracy": {"passed": True, "issues": [], "warnings": ["Test warning"]},
            },
        }

        fact_checking_agent._compile_results(result)

        assert result["status"] == "pass_with_warnings"
        assert len(result["warnings"]) > 0
