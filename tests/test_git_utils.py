"""Tests for utils/git_utils.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

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


class TestRunGitCommand:
    """Tests for run_git_command()."""

    @patch("subprocess.run")
    def test_runs_git_command_successfully(self, mock_run):
        """Test running git command returns stdout."""
        mock_run.return_value = MagicMock(stdout="git output")
        result = run_git_command(Path("/repo"), "status")
        assert result == "git output"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_git_command_error(self, mock_run):
        """Test that git command errors are handled."""
        mock_run.return_value = MagicMock(stdout="", stderr="error")
        result = run_git_command(Path("/repo"), "status")
        assert result == ""


class TestGetCommitsByDate:
    """Tests for get_commits_by_date()."""

    @patch("utils.git_utils.run_git_command")
    def test_parses_commits_correctly(self, mock_run):
        """Test parsing git log output into commit dicts."""
        mock_run.return_value = """abc123|2025-12-31 12:00:00 +0000|feat: add feature
def456|2025-12-31 14:00:00 +0000|fix: fix bug"""

        result = get_commits_by_date(Path("/repo"), "2025-12-31", "Test User")

        assert len(result) == 2
        assert result[0]["hash"] == "abc123"
        assert result[0]["timestamp"] == "2025-12-31 12:00:00 +0000"
        assert result[0]["message"] == "feat: add feature"
        assert result[1]["hash"] == "def456"
        assert result[1]["message"] == "fix: fix bug"

    @patch("utils.git_utils.run_git_command")
    def test_empty_output_returns_empty_list(self, mock_run):
        """Test empty git log output returns empty list."""
        mock_run.return_value = ""
        result = get_commits_by_date(Path("/repo"), "2025-12-31", "Test User")
        assert result == []


class TestCalculateLocChanges:
    """Tests for calculate_loc_changes()."""

    @patch("utils.git_utils.run_git_command")
    def test_calculates_loc_changes(self, mock_run):
        """Test parsing --numstat output."""
        mock_run.return_value = """10	5	file1.py
20	10	file2.py"""

        added, deleted = calculate_loc_changes(Path("/repo"), "2025-12-31", "Test User")

        assert added == 30
        assert deleted == 15

    @patch("utils.git_utils.run_git_command")
    def test_ignores_binary_files(self, mock_run):
        """Test that binary file entries are skipped."""
        mock_run.return_value = """10	5	file1.py
-	-	binary.png
20	10	file2.py"""

        added, deleted = calculate_loc_changes(Path("/repo"), "2025-12-31", "Test User")

        assert added == 30
        assert deleted == 15

    @patch("utils.git_utils.run_git_command")
    def test_empty_numstat_returns_zero(self, mock_run):
        """Test empty --numstat output returns zero."""
        mock_run.return_value = ""
        added, deleted = calculate_loc_changes(Path("/repo"), "2025-12-31", "Test User")

        assert added == 0
        assert deleted == 0


class TestCategorizeCommit:
    """Tests for categorize_commit()."""

    def test_categorizes_feat(self):
        """Test feat prefix categorization."""
        assert categorize_commit("feat: add new feature") == "feat"
        assert categorize_commit("FEAT: new feature") == "feat"

    def test_categorizes_fix(self):
        """Test fix prefix categorization."""
        assert categorize_commit("fix: resolve bug") == "fix"
        assert categorize_commit("Fix: fix bug") == "fix"

    def test_categorizes_refactor(self):
        """Test refactor prefix categorization."""
        assert categorize_commit("refactor: improve code") == "refactor"

    def test_categorizes_docs(self):
        """Test docs prefix categorization."""
        assert categorize_commit("docs: update readme") == "docs"

    def test_categorizes_test(self):
        """Test test prefix categorization."""
        assert categorize_commit("test: add tests") == "test"

    def test_categorizes_chore(self):
        """Test chore prefix categorization."""
        assert categorize_commit("chore: update dependencies") == "chore"

    def test_categorizes_perf(self):
        """Test perf prefix categorization."""
        assert categorize_commit("perf: optimize performance") == "perf"

    def test_categorizes_style(self):
        """Test style prefix categorization."""
        assert categorize_commit("style: format code") == "style"

    def test_categorizes_build(self):
        """Test build prefix categorization."""
        assert categorize_commit("build: update build") == "build"

    def test_categorizes_ci(self):
        """Test ci prefix categorization."""
        assert categorize_commit("ci: update workflow") == "ci"

    def test_categorizes_revert(self):
        """Test revert prefix categorization."""
        assert categorize_commit("revert: undo change") == "revert"

    def test_categorizes_other(self):
        """Test uncategorized messages return 'other'."""
        assert categorize_commit("random commit message") == "other"
        assert categorize_commit("just a message") == "other"


class TestExtractTaskId:
    """Tests for extract_task_id()."""

    def test_extracts_task_id(self):
        """Test extracting TASK-ID from commit message."""
        assert extract_task_id("TASK-123: add feature") == "TASK-123"
        assert extract_task_id("TASK_456: another task") == "TASK_456"

    def test_no_task_id_returns_none(self):
        """Test that messages without TASK-ID return None."""
        assert extract_task_id("just a commit") is None
        assert extract_task_id("feature: add something") is None


class TestGetRepoDescription:
    """Tests for get_repo_description()."""

    def test_reads_readme_md(self, tmp_path):
        """Test reading description from README.md."""
        readme = tmp_path / "README.md"
        readme.write_text("This is a test repository description.")
        result = get_repo_description(tmp_path)
        assert result == "This is a test repository description."

    def test_reads_readme_lowercase(self, tmp_path):
        """Test reading description from readme.md."""
        readme = tmp_path / "readme.md"
        readme.write_text("Lowercase readme description.")
        result = get_repo_description(tmp_path)
        assert result == "Lowercase readme description."

    def test_reads_readme_rst(self, tmp_path):
        """Test reading description from README.rst."""
        readme = tmp_path / "README.rst"
        readme.write_text("RST readme description.")
        result = get_repo_description(tmp_path)
        assert result == "RST readme description."

    def test_skips_header_line(self, tmp_path):
        """Test skipping header line to find description."""
        readme = tmp_path / "README.md"
        readme.write_text("# Project Title\n\nThis is the real description.")
        result = get_repo_description(tmp_path)
        assert result == "This is the real description."

    def test_no_readme_returns_none(self, tmp_path):
        """Test that missing README returns None."""
        result = get_repo_description(tmp_path)
        assert result is None


class TestIsWorkDay:
    """Tests for is_work_day()."""

    @patch("utils.git_utils.get_commits_by_date")
    def test_returns_true_for_commits(self, mock_get):
        """Test that date with commits is a work day."""
        mock_get.return_value = [{"hash": "abc123", "message": "test"}]
        result = is_work_day(Path("/repo"), "2025-12-31", "Test User")
        assert result is True

    @patch("utils.git_utils.get_commits_by_date")
    def test_returns_false_for_no_commits(self, mock_get):
        """Test that date without commits is not a work day."""
        mock_get.return_value = []
        result = is_work_day(Path("/repo"), "2025-12-31", "Test User")
        assert result is False


class TestStageAndCommit:
    """Tests for stage_and_commit()."""

    @patch("subprocess.run")
    def test_successful_stage_and_commit(self, mock_run):
        """Test successful staging and committing."""
        mock_run.return_value = MagicMock(returncode=0)
        result = stage_and_commit(Path("/repo"), Path("/repo/file.md"), "test commit")
        assert result is True
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_failed_commit_returns_false(self, mock_run):
        """Test that failed commit returns False."""
        mock_run.return_value = MagicMock(returncode=1)
        result = stage_and_commit(Path("/repo"), Path("/repo/file.md"), "test commit")
        assert result is False

    @patch("subprocess.run", side_effect=Exception("error"))
    def test_exception_returns_false(self, mock_run):
        """Test that exceptions return False."""
        result = stage_and_commit(Path("/repo"), Path("/repo/file.md"), "test commit")
        assert result is False
