"""Test git utility functions."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from utils.git_utils import (
    calculate_loc_changes,
    categorize_commit,
    extract_task_id,
    get_commits_by_date,
    get_repo_description,
    is_work_day,
    run_git_command,
    stage_and_commit,
)


@pytest.fixture
def mock_repo_path():
    """Provide a mock repository path."""
    return Path("/tmp/test/repo")


def test_run_git_command(mock_repo_path):
    """Test running a git command."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="test output")

        result = run_git_command(mock_repo_path, "status")

        mock_run.assert_called_once()
        assert result == "test output"


def test_get_commits_by_date(mock_repo_path):
    """Test getting commits by date."""
    git_output = """abc123|2025-12-31 10:00:00 +0000|feat: add feature
def456|2025-12-31 11:00:00 +0000|fix: fix bug"""

    with patch("utils.git_utils.run_git_command") as mock_run:
        mock_run.return_value = git_output

        commits = get_commits_by_date(mock_repo_path, "2025-12-31", "Test User")

        assert len(commits) == 2
        assert commits[0]["hash"] == "abc123"
        assert commits[0]["message"] == "feat: add feature"
        assert commits[1]["hash"] == "def456"


def test_get_commits_by_date_empty(mock_repo_path):
    """Test getting commits when none exist."""
    with patch("utils.git_utils.run_git_command") as mock_run:
        mock_run.return_value = ""

        commits = get_commits_by_date(mock_repo_path, "2025-12-31", "Test User")

        assert commits == []


def test_calculate_loc_changes(mock_repo_path):
    """Test calculating lines of code changes."""
    git_output = """10\t5\tpath/to/file.py
20\t0\tpath/to/another.py
0\t15\tpath/to/deleted.py"""

    with patch("utils.git_utils.run_git_command") as mock_run:
        mock_run.return_value = git_output

        added, deleted = calculate_loc_changes(mock_repo_path, "2025-12-31", "Test User")

        assert added == 30
        assert deleted == 20


def test_calculate_loc_changes_empty(mock_repo_path):
    """Test calculating LOC changes when no changes."""
    with patch("utils.git_utils.run_git_command") as mock_run:
        mock_run.return_value = ""

        added, deleted = calculate_loc_changes(mock_repo_path, "2025-12-31", "Test User")

        assert added == 0
        assert deleted == 0


def test_categorize_commit_feat():
    """Test categorizing a feature commit."""
    assert categorize_commit("feat: add new feature") == "feat"


def test_categorize_commit_fix():
    """Test categorizing a fix commit."""
    assert categorize_commit("fix: correct bug") == "fix"


def test_categorize_commit_refactor():
    """Test categorizing a refactor commit."""
    assert categorize_commit("refactor: improve code") == "refactor"


def test_categorize_commit_docs():
    """Test categorizing a docs commit."""
    assert categorize_commit("docs: update readme") == "docs"


def test_categorize_commit_test():
    """Test categorizing a test commit."""
    assert categorize_commit("test: add tests") == "test"


def test_categorize_commit_chore():
    """Test categorizing a chore commit."""
    assert categorize_commit("chore: update deps") == "chore"


def test_categorize_commit_perfect():
    """Test categorizing a perf commit."""
    assert categorize_commit("perf: optimize queries") == "perf"


def test_categorize_commit_style():
    """Test categorizing a style commit."""
    assert categorize_commit("style: format code") == "style"


def test_categorize_commit_build():
    """Test categorizing a build commit."""
    assert categorize_commit("build: update build") == "build"


def test_categorize_commit_ci():
    """Test categorizing a CI commit."""
    assert categorize_commit("ci: update workflow") == "ci"


def test_categorize_commit_revert():
    """Test categorizing a revert commit."""
    assert categorize_commit("revert: revert previous") == "revert"


def test_categorize_commit_other():
    """Test categorizing a commit with no recognized prefix."""
    assert categorize_commit("random commit message") == "other"


def test_categorize_commit_case_insensitive():
    """Test categorization is case-insensitive."""
    assert categorize_commit("FEAT: add feature") == "feat"
    assert categorize_commit("Fix: bug") == "fix"


def test_extract_task_id():
    """Test extracting task ID from commit message."""
    assert extract_task_id("feat(TASK-123): add feature") == "TASK-123"


def test_extract_task_id_underscore():
    """Test extracting task ID with underscore."""
    assert extract_task_id("feat(TASK_456): add feature") == "TASK_456"


def test_extract_task_id_no_id():
    """Test extracting task ID when none exists."""
    assert extract_task_id("feat: add feature") is None


def test_get_repo_description_with_readme():
    """Test extracting description from README."""
    with TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        readme_path = repo_path / "README.md"
        readme_path.write_text("This is a test repository")

        desc = get_repo_description(repo_path)
        assert desc == "This is a test repository"


def test_get_repo_description_with_header():
    """Test extracting description from README with header."""
    with TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        readme_path = repo_path / "README.md"
        readme_path.write_text("# Test Repo\n\nThis is a description.")

        desc = get_repo_description(repo_path)
        assert desc == "This is a description."


def test_get_repo_description_no_readme():
    """Test extracting description when no README exists."""
    with TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        desc = get_repo_description(repo_path)
        assert desc is None


def test_get_repo_description_multiple_readmes():
    """Test extracting description prefers README.md."""
    with TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / "README.md").write_text("Main description")
        (repo_path / "readme.md").write_text("Other description")

        desc = get_repo_description(repo_path)
        assert desc == "Main description"


def test_is_work_day_with_commits():
    """Test checking if it's a work day with commits."""
    mock_repo_path = Path("/tmp/test/repo")

    with patch("utils.git_utils.get_commits_by_date") as mock_get:
        mock_get.return_value = [
            {"hash": "abc123", "timestamp": "2025-12-31 10:00:00", "message": "test"}
        ]

        result = is_work_day(mock_repo_path, "2025-12-31", "Test User")
        assert result is True


def test_is_work_day_no_commits():
    """Test checking if it's a work day with no commits."""
    mock_repo_path = Path("/tmp/test/repo")

    with patch("utils.git_utils.get_commits_by_date") as mock_get:
        mock_get.return_value = []

        result = is_work_day(mock_repo_path, "2025-12-31", "Test User")
        assert result is False


def test_stage_and_commit_success(mock_repo_path):
    """Test staging and committing a file successfully."""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("test content")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = stage_and_commit(mock_repo_path, test_file, "test commit")

            assert result is True


def test_stage_and_commit_failure(mock_repo_path):
    """Test staging and committing when git fails."""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("test content")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            result = stage_and_commit(mock_repo_path, test_file, "test commit")

            assert result is False


def test_stage_and_commit_exception(mock_repo_path):
    """Test staging and committing when an exception occurs."""
    test_file = Path("/tmp/test.md")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Unexpected error")

        result = stage_and_commit(mock_repo_path, test_file, "test commit")

        assert result is False
