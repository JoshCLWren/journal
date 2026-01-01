"""Tests for ValidationAgent."""

from pathlib import Path

import pytest

from agents.validator import ValidationAgent


@pytest.fixture
def validation_agent():
    """Create a ValidationAgent instance for testing."""
    return ValidationAgent()


@pytest.fixture
def valid_entry_path(temp_dir):
    """Create a valid journal entry file for testing."""
    content = """# December 31, 2025

**Work Summary:** ~8.0 hours, ~1400 lines

## Summary
Test summary.

## Repositories Worked On
- `~/code/test-repo` (10 commits)

## Projects Legend
### test-repo
Test description."""

    year_dir = temp_dir / "2025" / "12"
    year_dir.mkdir(parents=True)
    entry_file = year_dir / "31.md"

    with open(entry_file, "w") as f:
        f.write(content)

    return entry_file


@pytest.fixture
def invalid_entry_path(temp_dir):
    """Create an invalid journal entry file for testing."""
    content = """Missing header section.

## Repositories Worked On
- `~/code/test-repo` (10 commits)"""

    year_dir = temp_dir / "2025" / "12"
    year_dir.mkdir(parents=True)
    entry_file = year_dir / "31.md"

    with open(entry_file, "w") as f:
        f.write(content)

    return entry_file


@pytest.fixture
def date_mismatch_path(temp_dir):
    """Create an entry with date mismatch for testing."""
    content = """# January 01, 2026

## Summary
Test.

## Repositories Worked On
- `~/code/test-repo` (10 commits)

## Projects Legend
### test-repo
Test description."""

    year_dir = temp_dir / "2025" / "12"
    year_dir.mkdir(parents=True)
    entry_file = year_dir / "31.md"

    with open(entry_file, "w") as f:
        f.write(content)

    return entry_file


@pytest.fixture
def formatting_issues_path(temp_dir):
    """Create an entry with formatting issues for testing."""
    content = """# December 31, 2025   

## Summary
Test.   

## Repositories Worked On
- `~/code/test-repo` (10 commits)

## Projects Legend
### test-repo
Test description."""

    year_dir = temp_dir / "2025" / "12"
    year_dir.mkdir(parents=True)
    entry_file = year_dir / "31.md"

    with open(entry_file, "w") as f:
        f.write(content)

    return entry_file


class TestValidationAgent:
    """Test suite for ValidationAgent."""

    def test_init(self, validation_agent):
        """Test ValidationAgent initialization."""
        assert validation_agent is not None

    def test_validate_entry_valid(self, validation_agent, valid_entry_path):
        """Test validate_entry with valid content."""
        result = validation_agent.validate_entry(valid_entry_path)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_validate_entry_invalid(self, validation_agent, invalid_entry_path):
        """Test validate_entry with invalid content."""
        result = validation_agent.validate_entry(invalid_entry_path)

        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert any("header" in issue.lower() for issue in result["issues"])

    def test_validate_entry_file_not_found(self, validation_agent, temp_dir):
        """Test validate_entry with non-existent file."""
        non_existent = temp_dir / "nonexistent.md"

        result = validation_agent.validate_entry(non_existent)

        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert "Failed to read" in result["issues"][0]

    def test_validate_entry_missing_summary_section(self, validation_agent, temp_dir):
        """Test validate_entry detects missing Summary section."""
        content = """# December 31, 2025

## Repositories Worked On
- `~/code/test-repo` (10 commits)

## Projects Legend
### test-repo
Test description."""

        year_dir = temp_dir / "2025" / "12"
        year_dir.mkdir(parents=True)
        entry_file = year_dir / "31.md"

        with open(entry_file, "w") as f:
            f.write(content)

        result = validation_agent.validate_entry(entry_file)

        assert result["valid"] is False
        assert any("Summary" in issue for issue in result["issues"])

    def test_validate_entry_missing_repositories_section(self, validation_agent, temp_dir):
        """Test validate_entry detects missing Repositories section."""
        content = """# December 31, 2025

## Summary
Test summary.

## Projects Legend
### test-repo
Test description."""

        year_dir = temp_dir / "2025" / "12"
        year_dir.mkdir(parents=True)
        entry_file = year_dir / "31.md"

        with open(entry_file, "w") as f:
            f.write(content)

        result = validation_agent.validate_entry(entry_file)

        assert result["valid"] is False
        assert any("Repositories" in issue for issue in result["issues"])

    def test_validate_entry_missing_projects_legend_warning(self, validation_agent, temp_dir):
        """Test validate_entry warns about missing Projects Legend."""
        content = """# December 31, 2025

## Summary
Test.

## Repositories Worked On
- `~/code/test-repo` (10 commits)"""

        year_dir = temp_dir / "2025" / "12"
        year_dir.mkdir(parents=True)
        entry_file = year_dir / "31.md"

        with open(entry_file, "w") as f:
            f.write(content)

        result = validation_agent.validate_entry(entry_file)

        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("Projects Legend" in warning for warning in result["warnings"])

    def test_validate_entry_date_mismatch(self, validation_agent, date_mismatch_path):
        """Test validate_entry detects date mismatch."""
        result = validation_agent.validate_entry(date_mismatch_path)

        assert result["valid"] is False
        assert any("Date mismatch" in issue for issue in result["issues"])

    def test_validate_entry_formatting_issues(self, validation_agent, formatting_issues_path):
        """Test validate_entry detects formatting issues."""
        result = validation_agent.validate_entry(formatting_issues_path)

        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("trailing whitespace" in warning.lower() for warning in result["warnings"])

    def test_has_header_valid(self, validation_agent):
        """Test _has_header with valid header."""
        content = "# December 31, 2025"

        result = validation_agent._has_header(content)

        assert result is True

    def test_has_header_invalid(self, validation_agent):
        """Test _has_header with invalid header."""
        content = "No header here"

        result = validation_agent._has_header(content)

        assert result is False

    def test_has_header_wrong_format(self, validation_agent):
        """Test _has_header with wrong format."""
        content = "# 2025-12-31"

        result = validation_agent._has_header(content)

        assert result is False

    def test_has_section_true(self, validation_agent):
        """Test _has_section when section exists."""
        content = """# December 31, 2025

## Summary
Test content."""

        result = validation_agent._has_section(content, "## Summary")

        assert result is True

    def test_has_section_false(self, validation_agent):
        """Test _has_section when section doesn't exist."""
        content = """# December 31, 2025

## Repositories
Test content."""

        result = validation_agent._has_section(content, "## Summary")

        assert result is False

    def test_check_markdown_formatting_trailing_whitespace(self, validation_agent):
        """Test _check_markdown_formatting detects trailing whitespace."""
        issues = []
        warnings = []

        content = "# Header   \n\n## Summary  \nTest."

        validation_agent._check_markdown_formatting(content, issues, warnings)

        assert len(warnings) > 0
        assert any("Trailing whitespace" in warning for warning in warnings)

    def test_check_markdown_formatting_empty_lines_before_headers(self, validation_agent):
        """Test _check_markdown_formatting detects missing empty lines."""
        issues = []
        warnings = []

        content = "# Header\n## Summary\nTest."

        validation_agent._check_markdown_formatting(content, issues, warnings)

        assert len(warnings) > 0
        assert any("empty line before" in warning for warning in warnings)

    def test_check_markdown_formatting_clean(self, validation_agent):
        """Test _check_markdown_formatting with clean content."""
        issues = []
        warnings = []

        content = """# December 31, 2025

## Summary

Test content.

## Repositories

More content."""

        validation_agent._check_markdown_formatting(content, issues, warnings)

        assert len(warnings) == 0

    def test_check_date_consistency_valid(self, validation_agent, valid_entry_path):
        """Test _check_date_consistency with matching dates."""
        content = """# December 31, 2025

## Summary
Test."""

        issues = []
        validation_agent._check_date_consistency(valid_entry_path, content, issues)

        assert len(issues) == 0

    def test_check_date_consistency_mismatch(self, validation_agent, date_mismatch_path):
        """Test _check_date_consistency with mismatched dates."""
        content = """# January 01, 2026

## Summary
Test."""

        issues = []
        validation_agent._check_date_consistency(date_mismatch_path, content, issues)

        assert len(issues) > 0
        assert any("Date mismatch" in issue for issue in issues)

    def test_check_date_consistency_invalid_path_format(self, validation_agent):
        """Test _check_date_consistency with invalid path format."""
        content = "# December 31, 2025"

        issues = []
        invalid_path = Path("/tmp/invalid/path.md")
        validation_agent._check_date_consistency(invalid_path, content, issues)

        assert len(issues) == 0

    def test_check_date_consistency_missing_header_date(self, validation_agent, temp_dir):
        """Test _check_date_consistency with missing date in header."""
        year_dir = temp_dir / "2025" / "12"
        year_dir.mkdir(parents=True)
        entry_file = year_dir / "31.md"

        content = "# No Date Here"

        issues = []
        validation_agent._check_date_consistency(entry_file, content, issues)

        assert len(issues) == 0
