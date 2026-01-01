"""Test markdown utility functions."""

from utils.markdown_utils import (
    extract_commits_from_markdown,
    format_date,
    format_header,
    has_section,
    is_valid_filename,
    validate_markdown_syntax,
)


def test_validate_markdown_syntax_valid():
    """Test validating correct markdown syntax."""
    content = """
# Header

Some text with `inline code`.

```
code block
```
"""
    errors = validate_markdown_syntax(content)
    assert errors == []


def test_validate_markdown_syntax_unclosed_code_block():
    """Test detecting unclosed code block."""
    content = """
# Header

```
unclosed code block
"""
    errors = validate_markdown_syntax(content)
    assert "Unclosed code block detected" in errors


def test_validate_markdown_syntax_unclosed_inline_code():
    """Test detecting unclosed inline code."""
    content = """
# Header

Text with `unclosed inline code.
"""
    errors = validate_markdown_syntax(content)
    assert "Unclosed inline code detected" in errors


def test_validate_markdown_syntax_multiple_unclosed():
    """Test detecting multiple unclosed code blocks."""
    content = """
```
block 1
```

```
block 2

```
inline `code
"""
    errors = validate_markdown_syntax(content)
    assert "Unclosed code block detected" in errors
    assert "Unclosed inline code detected" in errors


def test_extract_commits_from_markdown():
    """Test extracting commit count from markdown."""
    content = """
## Repositories Worked On

- `~/code/test-repo` (42 commits)
"""
    count = extract_commits_from_markdown(content, "test-repo")
    assert count == 42


def test_extract_commits_from_markdown_no_match():
    """Test extracting when no match found."""
    content = """
## Repositories Worked On

- `~/code/other-repo` (42 commits)
"""
    count = extract_commits_from_markdown(content, "test-repo")
    assert count == 0


def test_extract_commits_from_markdown_multiple_matches():
    """Test extracting when multiple matches found (returns first)."""
    content = """
## test-repo

- `~/code/test-repo` (42 commits)
- `~/code/test-repo` (10 commits)
"""
    count = extract_commits_from_markdown(content, "test-repo")
    assert count == 42


def test_has_section_true():
    """Test checking if section exists (positive case)."""
    content = """
## Summary

This is a summary.
"""
    assert has_section(content, "Summary") is True


def test_has_section_false():
    """Test checking if section exists (negative case)."""
    content = """
## Introduction

This is an intro.
"""
    assert has_section(content, "Summary") is False


def test_has_section_partial_match():
    """Test section matching requires exact match."""
    content = """
## Summary of Work

This is a summary.
"""
    assert has_section(content, "Summary") is False


def test_is_valid_filename_true():
    """Test validating correct filename format."""
    assert is_valid_filename("2025/12/31.md") is True


def test_is_valid_filename_false_no_extension():
    """Test validating filename without extension."""
    assert is_valid_filename("2025/12/31") is False


def test_is_valid_filename_false_wrong_format():
    """Test validating filename with wrong format."""
    assert is_valid_filename("2025-12-31.md") is False
    assert is_valid_filename("12/31/2025.md") is False
    assert is_valid_filename("2025/31.md") is False


def test_format_header_hours():
    """Test formatting header with hours."""
    header = format_header("2025-12-31", 8.5, 4500)

    assert "December 31, 2025" in header
    assert "8.5 hours" in header
    assert "~4,500 lines" in header


def test_format_header_minutes():
    """Test formatting header with minutes (< 1 hour)."""
    header = format_header("2025-12-31", 0.5, 200)

    assert "December 31, 2025" in header
    assert "30 minutes" in header
    assert "~200 lines" in header


def test_format_header_less_than_1000_loc():
    """Test formatting header with LOC < 1000."""
    header = format_header("2025-12-31", 5.0, 500)

    assert "~500 lines" in header
    assert "~500 lines" not in header.replace("~500", "")


def test_format_header_large_loc():
    """Test formatting header with large LOC."""
    header = format_header("2025-12-31", 12.0, 1000000)

    assert "~1,000,000 lines" in header


def test_format_date_valid():
    """Test formatting date from ISO format."""
    result = format_date("2025-12-31")
    assert result == "December 31, 2025"


def test_format_date_invalid():
    """Test formatting invalid date (returns as-is)."""
    result = format_date("invalid-date")
    assert result == "invalid-date"


def test_format_date_different_dates():
    """Test formatting various dates."""
    assert format_date("2025-01-15") == "January 15, 2025"
    assert format_date("2024-07-04") == "July 04, 2024"
    assert format_date("2023-12-25") == "December 25, 2023"


def test_format_header_auto_generated_text():
    """Test header includes auto-generated text."""
    header = format_header("2025-12-31", 5.0, 500)

    assert "Auto-generated by journal automation" in header
