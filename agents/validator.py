#!/usr/bin/env python3
"""Validation Agent - Validates journal entry structure and content."""

import logging
import re
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config

logger = logging.getLogger(__name__)


class ValidationAgent:
    """Validates journal entries for structure and content."""

    def __init__(self):
        pass

    def validate_entry(self, entry_path: Path) -> Dict:
        """Validate a journal entry.

        Args:
            entry_path: Path to the entry file

        Returns:
            dict: {
                'valid': bool,
                'issues': List[str],
                'warnings': List[str]
            }
        """
        issues = []
        warnings = []

        try:
            with open(entry_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check required sections
            if not self._has_header(content):
                issues.append("Missing or invalid header section")

            if not self._has_section(content, "## Summary"):
                issues.append("Missing Summary section")

            if not self._has_section(content, "## Repositories Worked On"):
                issues.append("Missing Repositories Worked On section")

            if not self._has_section(content, "## Projects Legend"):
                warnings.append("Missing Projects Legend section")

            # Check markdown formatting
            self._check_markdown_formatting(content, issues, warnings)

            # Check date consistency
            self._check_date_consistency(entry_path, content, issues)

        except Exception as e:
            issues.append(f"Failed to read entry: {e}")

        return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}

    def _has_header(self, content: str) -> bool:
        """Check if content has valid header.

        Args:
            content: Entry content

        Returns:
            bool: True if valid header found
        """
        # Header format: # Month DD, YYYY
        header_pattern = r"^# [A-Z][a-z]+ \d{1,2}, \d{4}"
        return bool(re.search(header_pattern, content, re.MULTILINE))

    def _has_section(self, content: str, section_title: str) -> bool:
        """Check if content has a specific section.

        Args:
            content: Entry content
            section_title: Section title to look for

        Returns:
            bool: True if section found
        """
        return section_title in content

    def _check_markdown_formatting(
        self, content: str, issues: List[str], warnings: List[str]
    ):
        """Check markdown formatting issues.

        Args:
            content: Entry content
            issues: List to append critical issues to
            warnings: List to append warnings to
        """
        # Check for trailing whitespace
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if line != line.rstrip():
                warnings.append(f"Line {i}: Trailing whitespace")

        # Check for empty lines before headers
        for i, line in enumerate(lines[1:], 2):
            if line.startswith("##") and not lines[i - 2].strip() == "":
                warnings.append(f"Line {i}: Header should have empty line before it")

    def _check_date_consistency(
        self, entry_path: Path, content: str, issues: List[str]
    ):
        """Check if date in filename matches date in header.

        Args:
            entry_path: Path to entry file
            content: Entry content
            issues: List to append issues to
        """
        # Extract date from filename (YYYY/MM/DD.md)
        match = re.search(r"(\d{4})/(\d{2})/(\d{2})\.md$", str(entry_path))
        if not match:
            return

        year, month, day = match.groups()
        expected_date = f"{year}-{month}-{day}"

        # Extract date from header
        header_pattern = r"# [A-Z][a-z]+ (\d{1,2}), (\d{4})"
        header_match = re.search(header_pattern, content)

        if header_match:
            header_day, header_year = header_match.groups()
            if header_year != year or header_day.zfill(2) != day:
                issues.append(
                    f"Date mismatch: filename={expected_date}, header=Month {header_day}, {header_year}"
                )


if __name__ == "__main__":
    from datetime import datetime

    logging.basicConfig(level=logging.INFO)

    validator = ValidationAgent()

    # Test with today's date
    date = datetime.now()
    journal_dir = Path.home() / "code" / "journal"
    entry_path = journal_dir / date.strftime("%Y/%m/%d.md")

    if entry_path.exists():
        result = validator.validate_entry(entry_path)
        print(f"Valid: {result['valid']}")
        if result["issues"]:
            print("Issues:")
            for issue in result["issues"]:
                print(f"  - {issue}")
        if result["warnings"]:
            print("Warnings:")
            for warning in result["warnings"]:
                print(f"  - {warning}")
    else:
        print(f"Entry not found: {entry_path}")
