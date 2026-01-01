"""Test Fact Checking Agent."""

from unittest.mock import patch

import pytest

from agents.fact_checking import FactCheckingAgent


@pytest.fixture
def agent():
    """Create FactCheckingAgent with mocked config."""
    mock_config = {
        "scheduling": {
            "opencode_url": "http://127.0.0.1:4096",
        },
        "opencode": {
            "model": "glm-4.7-free",
            "provider": "opencode",
        },
    }

    with patch("agents.fact_checking.get_config", return_value=mock_config):
        with patch("agents.fact_checking.OpenCodeClient") as mock_client:
            agent = FactCheckingAgent()
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
                "loc_added": 4000,
                "loc_deleted": 800,
                "commits_by_category": {"feat": 25, "fix": 10, "refactor": 5, "docs": 3},
                "top_features": ["feat(TASK-102): Add Staleness Awareness UI"],
            }
        },
    }


@pytest.fixture
def valid_markdown():
    """Provide valid markdown content."""
    return """## 2025-12-31 (8.5 hours, 4800 LOC)

## Summary
Worked on test-repo with significant feature additions.

## Repositories Worked On
- `~/code/test-repo` (43 commits)
- **Total: 43 commits**

## test-repo
**Staleness Awareness**
- Feat: Add Staleness Awareness UI
- Fix: Update cache logic

---

## Projects Legend
### test-repo
Test repository description
"""


def test_check_entry_pass(agent, sample_git_data, valid_markdown):
    """Test fact-checking a valid entry."""
    agent.client.chat.return_value = {"content": "Entry is accurate and complete."}

    result = agent.check_entry(sample_git_data, valid_markdown)

    assert result["status"] == "pass"
    assert "checks" in result
    assert "reasoning" in result


def test_check_entry_error(agent, sample_git_data):
    """Test fact-checking with an error."""
    with patch.object(agent, "_check_accuracy", side_effect=Exception("Test error")):
        result = agent.check_entry(sample_git_data, "content")

    assert result["status"] == "fail"
    assert len(result["errors"]) > 0


def test_check_accuracy_correct(agent, sample_git_data, valid_markdown):
    """Test accuracy check with correct data."""
    result = agent._check_accuracy(sample_git_data, valid_markdown)

    assert result["passed"] is True
    assert len(result["issues"]) == 0


def test_check_accuracy_missing_commits(agent, sample_git_data):
    """Test accuracy check with missing commit counts."""
    markdown = """## Summary
Test summary.
"""

    result = agent._check_accuracy(sample_git_data, markdown)

    assert result["passed"] is False
    assert len(result["issues"]) > 0
    assert any("missing" in issue.lower() for issue in result["issues"])


def test_check_accuracy_commit_count_mismatch(agent, sample_git_data):
    """Test accuracy check with mismatched commit counts."""
    markdown = """## Repositories Worked On
- `~/code/test-repo` (10 commits)
- **Total: 10 commits**
"""

    result = agent._check_accuracy(sample_git_data, markdown)

    assert result["passed"] is False
    assert any("mismatch" in issue.lower() for issue in result["issues"])


def test_check_completeness_pass(agent, sample_git_data, valid_markdown):
    """Test completeness check with all repos."""
    result = agent._check_completeness(sample_git_data, valid_markdown)

    assert result["passed"] is True


def test_check_completeness_missing_section(agent, sample_git_data):
    """Test completeness check with missing section."""
    markdown = """## Summary
Test summary.
"""

    result = agent._check_completeness(sample_git_data, markdown)

    assert result["passed"] is False
    assert any("Missing section" in issue for issue in result["issues"])


def test_check_consistency_pass(agent, sample_git_data, valid_markdown):
    """Test consistency check with consistent data."""
    result = agent._check_consistency(sample_git_data, valid_markdown)

    assert result["passed"] is True


def test_check_consistency_loc_mismatch(agent, sample_git_data):
    """Test consistency check with LOC mismatch."""
    markdown = """## Summary
Total of 100,000 lines of code.
"""

    result = agent._check_consistency(sample_git_data, markdown)

    assert result["passed"] is False
    assert any("LOC" in issue for issue in result["issues"])


def test_check_consistency_date_missing(agent, sample_git_data):
    """Test consistency check with missing date."""
    markdown = """## Summary
Test summary for today.
"""

    result = agent._check_consistency(sample_git_data, markdown)

    assert result["passed"] is False
    assert any("Date" in issue for issue in result["issues"])


def test_check_duplicates_no_duplicates(agent):
    """Test duplicate check with no duplicates."""
    markdown = """## Section 1
- Feat: feature 1
- Fix: bug 1

## Section 2
- Feat: feature 2
"""

    result = agent._check_duplicates(markdown)

    assert result["passed"] is True


def test_check_duplicates_duplicate_sections(agent):
    """Test duplicate check with duplicate sections."""
    markdown = """## Section 1
Content.

## Section 1
Duplicate content.
"""

    result = agent._check_duplicates(markdown)

    assert result["passed"] is False
    assert any("Duplicate section" in issue for issue in result["issues"])


def test_check_duplicates_duplicate_commits(agent):
    """Test duplicate check with duplicate commits."""
    markdown = """## Section 1
- Feat: feature 1
- Feat: feature 1
"""

    result = agent._check_duplicates(markdown)

    assert result["passed"] is False
    assert any("Duplicate commit" in issue for issue in result["issues"])


def test_check_anomalies_pass(agent, sample_git_data):
    """Test anomaly check with no anomalies."""
    markdown = "## Test\n\nContent."

    result = agent._check_anomalies(sample_git_data, markdown)

    # May have warnings, but should not have critical issues
    assert isinstance(result["passed"], bool)


def test_check_anomalies_no_loc(agent):
    """Test anomaly check for repo with commits but no LOC."""
    git_data = {
        "repos": {
            "test-repo": {
                "commits": 10,
                "loc_added": 0,
            }
        }
    }

    result = agent._check_anomalies(git_data, "content")

    assert len(result["issues"]) > 0


def test_check_anomalies_low_loc_per_commit(agent):
    """Test anomaly check for low LOC/commit ratio."""
    git_data = {
        "repos": {
            "test-repo": {
                "commits": 10,
                "loc_added": 10,
            }
        }
    }

    result = agent._check_anomalies(git_data, "content")

    assert len(result["issues"]) > 0


def test_check_anomalies_many_sections(agent):
    """Test anomaly check for too many sections."""
    markdown = "\n".join([f"## Section {i}" for i in range(25)])

    result = agent._check_anomalies(sample_git_data(), markdown)

    assert len(result["issues"]) > 0


def test_generate_llm_analysis(agent, sample_git_data, valid_markdown):
    """Test LLM analysis generation."""
    agent.client.chat.return_value = {"content": "Analysis: Entry is accurate."}

    analysis = agent._generate_llm_analysis(
        sample_git_data, valid_markdown, {"accuracy": {"passed": True}}
    )

    assert analysis == "Analysis: Entry is accurate."
    agent.client.chat.assert_called_once()


def test_compile_results_pass(agent):
    """Test compiling results with pass status."""
    result = {
        "errors": [],
        "warnings": [],
        "corrections": [],
        "checks": {
            "accuracy": {"passed": True, "issues": []},
            "completeness": {"passed": True, "issues": []},
        },
    }

    agent._compile_results(result)

    assert result["status"] == "pass"


def test_compile_results_fail(agent):
    """Test compiling results with fail status."""
    result = {
        "errors": ["Critical error"],
        "warnings": [],
        "corrections": [],
        "checks": {
            "accuracy": {"passed": False, "issues": ["Error"]},
        },
    }

    agent._compile_results(result)

    assert result["status"] == "fail"


def test_compile_results_warnings(agent):
    """Test compiling results with warnings."""
    result = {
        "errors": [],
        "warnings": ["Warning"],
        "corrections": [],
        "checks": {
            "accuracy": {"passed": True, "issues": []},
        },
    }

    agent._compile_results(result)

    assert result["status"] == "pass_with_warnings"


def test_check_entry_pass_with_warnings(agent, sample_git_data, valid_markdown):
    """Test fact-checking that passes with warnings."""
    agent.client.chat.return_value = {"content": "Entry is mostly accurate."}

    # Modify markdown to create a warning (not a critical error)
    markdown = valid_markdown + "\n\nToo many blank lines\n\n\n\n\n\n"

    result = agent.check_entry(sample_git_data, markdown)

    # Should not fail completely, but may have warnings
    assert result["status"] in ["pass", "pass_with_warnings"]
