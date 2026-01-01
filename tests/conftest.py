"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test files."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    return {
        "general": {
            "author_name": "Test User",
            "author_email": "test@example.com",
            "code_directory": "/tmp/test_code",
            "journal_directory": "/tmp/test_journal",
        },
        "git": {
            "exclude_repos": ["test-exclude"],
            "exclude_patterns": ["test-pattern"],
        },
        "quality": {
            "min_commits_for_section": 3,
            "require_human_approval": False,
        },
    }


@pytest.fixture
def sample_commits():
    """Provide sample commit data for testing."""
    return [
        {
            "hash": "abc123",
            "author": "Test User",
            "email": "test@example.com",
            "date": "2025-12-31T12:00:00",
            "message": "feat: add new feature",
            "repo": "test-repo",
        },
        {
            "hash": "def456",
            "author": "Test User",
            "email": "test@example.com",
            "date": "2025-12-31T14:00:00",
            "message": "fix: correct bug",
            "repo": "test-repo",
        },
    ]
