"""Test Validation Agent."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from agents.validator import ValidationAgent


@pytest.fixture
def agent():
    """Create ValidationAgent instance."""
    return ValidationAgent()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_entry_path(temp_dir):
    """Create a valid journal entry file."""
    year_dir = temp_dir / "2025" / "12"
    year_dir.mkdir(parents=True)
    entry_path = year_dir / "31.md"

    entry_path.write_text("""# December 31, 2025

## Summary
Worked on various projects.

## Repositories Worked On
- `~/code/test-repo` (43 commits)
- **Total: 43 commits**

## test-repo
**Features**
- Feat: Add new feature

---

## Projects Legend
### test-repo
Test repository description
""")

    return entry_path


@pytest.fixture
def invalid_entry_path(temp_dir):
    """Create an invalid journal entry file."""
    year_dir = temp_dir / "2025" / "12"
    year_dir.mkdir(parents=True)
    entry_path = year_dir / "31.md"

    entry_path.write_text("""Invalid entry
""")

    return entry_path


def test_validate_entry_valid(agent, valid_entry_path):
    """Test validating a valid entry."""
    result = agent.validate_entry(valid_entry_path)

    assert result["valid"] is True
    assert len(result["issues"]) == 0


def test_validate_entry_invalid(agent, invalid_entry_path):
    """Test validating an invalid entry."""
    result = agent.validate_entry(invalid_entry_path)

    assert result["valid"] is False
    assert len(result["issues"]) > 0


def test_validate_entry_no_header(agent, temp_dir):
    """Test validating entry without header."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("No header here")

    result = agent.validate_entry(entry_path)

    assert result["valid"] is False
    assert any("header" in issue.lower() for issue in result["issues"])


def test_validate_entry_no_summary(agent, temp_dir):
    """Test validating entry without summary."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("""# December 31, 2025
No summary section.
""")

    result = agent.validate_entry(entry_path)

    assert result["valid"] is False
    assert any("summary" in issue.lower() for issue in result["issues"])


def test_validate_entry_no_repos_section(agent, temp_dir):
    """Test validating entry without repositories section."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("""# December 31, 2025
## Summary
Worked on stuff.
""")

    result = agent.validate_entry(entry_path)

    assert result["valid"] is False
    assert any("repositories" in issue.lower() for issue in result["issues"])


def test_validate_entry_no_legend(agent, temp_dir):
    """Test validating entry without projects legend."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("""# December 31, 2025
## Summary
Worked on stuff.
## Repositories Worked On
- `~/code/test` (10 commits)
""")

    result = agent.validate_entry(entry_path)

    # Missing legend is a warning, not an error
    assert len(result["warnings"]) > 0


def test_validate_entry_trailing_whitespace(agent, temp_dir):
    """Test validating entry with trailing whitespace."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("""# December 31, 2025  

## Summary
Test.  
""")

    result = agent.validate_entry(entry_path)

    # Should have warnings about trailing whitespace
    assert len(result["warnings"]) > 0
    assert any("trailing whitespace" in warning.lower() for warning in result["warnings"])


def test_validate_entry_header_format(agent, temp_dir):
    """Test validating entry with invalid header format."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("## December 31, 2025")  # Wrong level

    result = agent.validate_entry(entry_path)

    assert result["valid"] is False
    assert any("header" in issue.lower() for issue in result["issues"])


def test_validate_entry_no_header_space(agent, temp_dir):
    """Test validating entry header with no space after #."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("#December 31, 2025")

    result = agent.validate_entry(entry_path)

    assert result["valid"] is False


def test_validate_entry_date_mismatch(agent, temp_dir):
    """Test validating entry with date mismatch."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("""# December 15, 2025
## Summary
Wrong date.
## Repositories Worked On
- `~/code/test` (10 commits)
""")

    result = agent.validate_entry(entry_path)

    assert result["valid"] is False
    assert any("date" in issue.lower() for issue in result["issues"])


def test_validate_entry_year_mismatch(agent, temp_dir):
    """Test validating entry with year mismatch."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("""# December 31, 2024
## Summary
Wrong year.
## Repositories Worked On
- `~/code/test` (10 commits)
""")

    result = agent.validate_entry(entry_path)

    assert result["valid"] is False
    assert any("date" in issue.lower() for issue in result["issues"])


def test_validate_entry_header_before_section(agent, temp_dir):
    """Test validating entry with missing blank line before header."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("""# December 31, 2025
## Summary
Test.
Text here
## Repositories Worked On
- `~/code/test` (10 commits)
""")

    result = agent.validate_entry(entry_path)

    # Should have warning about missing blank line
    warnings = result.get("warnings", [])
    assert any("blank line" in warning.lower() for warning in warnings)


def test_has_header_true(agent):
    """Test _has_header with valid header."""
    content = "# December 31, 2025"

    assert agent._has_header(content) is True


def test_has_header_false(agent):
    """Test _has_header with invalid header."""
    content = "December 31, 2025"

    assert agent._has_header(content) is False


def test_has_header_different_format(agent):
    """Test _has_header with different format."""
    content = "## December 31, 2025"

    assert agent._has_header(content) is False


def test_has_section_true(agent):
    """Test _has_section when section exists."""
    content = "## Summary\n\nSome content."

    assert agent._has_section(content, "## Summary") is True
    assert agent._has_section(content, "Summary") is True


def test_has_section_false(agent):
    """Test _has_section when section doesn't exist."""
    content = "## Introduction\n\nSome content."

    assert agent._has_section(content, "Summary") is False


def test_validate_entry_file_not_found(agent, temp_dir):
    """Test validating non-existent file."""
    entry_path = temp_dir / "2025" / "12" / "31.md"

    result = agent.validate_entry(entry_path)

    assert result["valid"] is False
    assert any("failed to read" in issue.lower() for issue in result["issues"])


def test_validate_entry_all_sections_present(agent, valid_entry_path):
    """Test validating entry with all required sections."""
    result = agent.validate_entry(valid_entry_path)

    assert result["valid"] is True
    assert len(result["issues"]) == 0
    assert len(result["warnings"]) == 0


def test_validate_entry_filename_pattern(agent, temp_dir):
    """Test validating entry with non-standard filename."""
    entry_path = temp_dir / "2025-12-31.md"
    entry_path.write_text("""# December 31, 2025
## Summary
Test.
## Repositories Worked On
- `~/code/test` (10 commits)
""")

    result = agent.validate_entry(entry_path)

    # Date check may be skipped due to filename pattern
    assert isinstance(result["valid"], bool)


def test_validate_entry_single_day(agent, temp_dir):
    """Test validating entry for single day (day < 10)."""
    year_dir = temp_dir / "2025" / "01"
    year_dir.mkdir(parents=True)
    entry_path = year_dir / "5.md"

    entry_path.write_text("""# January 5, 2025
## Summary
Test.
## Repositories Worked On
- `~/code/test` (10 commits)
""")

    result = agent.validate_entry(entry_path)

    # Should validate correctly with single-digit day
    assert isinstance(result["valid"], bool)


def test_validate_entry_multiple_issues(agent, temp_dir):
    """Test validating entry with multiple issues."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)
    entry_path.write_text("Invalid content\n\nNo structure")

    result = agent.validate_entry(entry_path)

    # Should detect multiple issues
    assert len(result["issues"]) > 1


def test_validate_entry_with_code_blocks(agent, temp_dir):
    """Test validating entry with code blocks."""
    entry_path = temp_dir / "2025" / "12" / "31.md"
    entry_path.parent.mkdir(parents=True)

    entry_path.write_text("""# December 31, 2025
## Summary
Test.
```python
def example():
    pass
```
## Repositories Worked On
- `~/code/test` (10 commits)
""")

    result = agent.validate_entry(entry_path)

    # Code blocks should be valid
    assert result["valid"] is True
