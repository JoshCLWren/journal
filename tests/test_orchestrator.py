"""Tests for orchestrator.py (root level)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator import FactCheckingAgent, Orchestrator, QualityAssuranceAgent


@pytest.fixture
def mock_config():
    """Mock configuration for orchestrator."""
    return {
        "general": {
            "journal_directory": "/tmp/test_journal",
            "author_name": "Test User",
            "author_email": "test@example.com",
        },
        "scheduling": {
            "auto_push": False,
            "opencode_url": "http://127.0.0.1:4096",
        },
        "opencode": {
            "model": "glm-4.7-free",
            "provider": "opencode",
        },
        "quality": {
            "min_commits_for_section": 3,
            "require_human_approval": False,
            "parallel_agents": False,
            "commit_as_they_go": False,
        },
    }


@pytest.fixture
def sample_git_data():
    """Sample git data for testing."""
    return {
        "date": "2025-12-31",
        "total_commits": 10,
        "total_loc_added": 500,
        "total_loc_deleted": 100,
        "estimated_hours": 4.5,
        "is_work_day": True,
        "repos": {
            "test-repo": {
                "commits": 10,
                "commit_messages": ["feat: add feature", "fix: bug"],
                "loc_added": 500,
                "loc_deleted": 100,
            }
        },
    }


class TestFactCheckingAgent:
    """Test FactCheckingAgent class."""

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_init(self, mock_client, mock_get_config, mock_config):
        """Test FactCheckingAgent initialization."""
        mock_get_config.return_value = mock_config
        agent = FactCheckingAgent()

        assert agent.config == mock_config
        mock_client.assert_called_once_with(base_url="http://127.0.0.1:4096")

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_verify_facts_success(self, mock_client, mock_get_config, mock_config, sample_git_data):
        """Test verify_facts with successful verification."""
        mock_get_config.return_value = mock_config

        mock_client_instance = MagicMock()
        mock_client_instance.chat.return_value = {
            "content": json.dumps(
                {
                    "status": "verified",
                    "findings": [],
                }
            )
        }
        mock_client.return_value = mock_client_instance

        agent = FactCheckingAgent()
        content = "# Test Entry\n\nSummary of commits"

        result = agent.verify_facts(content, sample_git_data)

        assert result["status"] == "verified"
        assert result["findings"] == []

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_verify_facts_with_issues(
        self, mock_client, mock_get_config, mock_config, sample_git_data
    ):
        """Test verify_facts with issues found."""
        mock_get_config.return_value = mock_config

        mock_client_instance = MagicMock()
        mock_client_instance.chat.return_value = {
            "content": json.dumps(
                {
                    "status": "issues_found",
                    "findings": [
                        {"type": "error", "issue": "Wrong commit count"},
                        {"type": "warning", "issue": "Missing repo"},
                    ],
                }
            )
        }
        mock_client.return_value = mock_client_instance

        agent = FactCheckingAgent()
        content = "# Test Entry"

        result = agent.verify_facts(content, sample_git_data)

        assert result["status"] == "issues_found"
        assert len(result["findings"]) == 2

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_verify_facts_invalid_json(
        self, mock_client, mock_get_config, mock_config, sample_git_data
    ):
        """Test verify_facts with invalid JSON response."""
        mock_get_config.return_value = mock_config

        mock_client_instance = MagicMock()
        mock_client_instance.chat.return_value = {
            "content": "invalid json",
        }
        mock_client.return_value = mock_client_instance

        agent = FactCheckingAgent()
        content = "# Test Entry"

        result = agent.verify_facts(content, sample_git_data)

        assert result["status"] == "error"
        assert "Failed to parse fact check response" in result["findings"][0]["issue"]

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_verify_facts_exception(
        self, mock_client, mock_get_config, mock_config, sample_git_data
    ):
        """Test verify_facts with exception."""
        mock_get_config.return_value = mock_config

        mock_client_instance = MagicMock()
        mock_client_instance.chat.side_effect = Exception("API error")
        mock_client.return_value = mock_client_instance

        agent = FactCheckingAgent()
        content = "# Test Entry"

        result = agent.verify_facts(content, sample_git_data)

        assert result["status"] == "failed"
        assert "API error" in result["findings"][0]["issue"]


class TestQualityAssuranceAgent:
    """Test QualityAssuranceAgent class."""

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_init(self, mock_client, mock_get_config, mock_config):
        """Test QualityAssuranceAgent initialization."""
        mock_get_config.return_value = mock_config
        agent = QualityAssuranceAgent()

        assert agent.config == mock_config
        mock_client.assert_called_once_with(base_url="http://127.0.0.1:4096")

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_check_quality_passed(self, mock_client, mock_get_config, mock_config, sample_git_data):
        """Test check_quality with passing result."""
        mock_get_config.return_value = mock_config

        mock_client_instance = MagicMock()
        mock_client_instance.chat.return_value = {
            "content": json.dumps(
                {
                    "status": "passed",
                    "checks": {
                        "readability": {"score": 8, "notes": "Clear and concise"},
                        "completeness": {"score": 9, "notes": "Complete"},
                        "accuracy": {"score": 10, "notes": "Accurate"},
                        "overall_quality": {"score": 9, "notes": "Good quality"},
                    },
                    "recommendations": [],
                }
            )
        }
        mock_client.return_value = mock_client_instance

        agent = QualityAssuranceAgent()
        content = "# Test Entry\n\nComplete entry with all sections"

        result = agent.check_quality(content, sample_git_data)

        assert result["status"] == "passed"
        assert result["checks"]["overall_quality"]["score"] == 9

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_check_quality_needs_improvement(
        self, mock_client, mock_get_config, mock_config, sample_git_data
    ):
        """Test check_quality with needs_improvement result."""
        mock_get_config.return_value = mock_config

        mock_client_instance = MagicMock()
        mock_client_instance.chat.return_value = {
            "content": json.dumps(
                {
                    "status": "needs_improvement",
                    "checks": {
                        "readability": {"score": 5, "notes": "Hard to follow"},
                        "completeness": {"score": 6, "notes": "Missing sections"},
                        "accuracy": {"score": 8, "notes": "Mostly accurate"},
                        "overall_quality": {"score": 6, "notes": "Needs work"},
                    },
                    "recommendations": ["Add summary section", "Improve readability"],
                }
            )
        }
        mock_client.return_value = mock_client_instance

        agent = QualityAssuranceAgent()
        content = "# Test Entry"

        result = agent.check_quality(content, sample_git_data)

        assert result["status"] == "needs_improvement"
        assert result["checks"]["overall_quality"]["score"] == 6
        assert len(result["recommendations"]) == 2

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_check_quality_invalid_json(
        self, mock_client, mock_get_config, mock_config, sample_git_data
    ):
        """Test check_quality with invalid JSON response."""
        mock_get_config.return_value = mock_config

        mock_client_instance = MagicMock()
        mock_client_instance.chat.return_value = {
            "content": "invalid json",
        }
        mock_client.return_value = mock_client_instance

        agent = QualityAssuranceAgent()
        content = "# Test Entry"

        result = agent.check_quality(content, sample_git_data)

        assert result["status"] == "error"
        assert result["checks"]["overall_quality"]["score"] == 0

    @patch("orchestrator.get_config")
    @patch("orchestrator.OpenCodeClient")
    def test_check_quality_exception(
        self, mock_client, mock_get_config, mock_config, sample_git_data
    ):
        """Test check_quality with exception."""
        mock_get_config.return_value = mock_config

        mock_client_instance = MagicMock()
        mock_client_instance.chat.side_effect = Exception("API error")
        mock_client.return_value = mock_client_instance

        agent = QualityAssuranceAgent()
        content = "# Test Entry"

        result = agent.check_quality(content, sample_git_data)

        assert result["status"] == "failed"
        assert "API error" in result["checks"]["overall_quality"]["notes"]


class TestOrchestrator:
    """Test Orchestrator class."""

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    def test_init(self, mock_client, mock_content, mock_git, mock_get_config, mock_config):
        """Test Orchestrator initialization."""
        mock_get_config.return_value = mock_config

        orchestrator = Orchestrator()

        assert orchestrator.config == mock_config
        assert orchestrator.journal_dir == Path("/tmp/test_journal")
        mock_git.assert_called_once()
        mock_content.assert_called_once()
        assert mock_client.call_count == 3  # One for each agent

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    @patch("orchestrator.ensure_opencode_running")
    def test_run_day_no_work(
        self, mock_ensure, mock_client, mock_content, mock_git, mock_get_config, mock_config
    ):
        """Test run_day when no work detected."""
        mock_get_config.return_value = mock_config

        mock_git_agent = MagicMock()
        mock_git_agent.analyze_day.return_value = {
            "is_work_day": False,
            "date": "2025-12-31",
        }
        mock_git.return_value = mock_git_agent

        orchestrator = Orchestrator()
        result = orchestrator.run_day("2025-12-31")

        assert result["final_status"] == "no_work"
        assert result["is_work_day"] is False

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    @patch("orchestrator.ensure_opencode_running")
    @patch("orchestrator.stage_and_commit")
    def test_run_day_success(
        self,
        mock_stage_commit,
        mock_ensure,
        mock_client,
        mock_content,
        mock_git,
        mock_get_config,
        mock_config,
        sample_git_data,
        tmp_path,
    ):
        """Test run_day with successful execution."""
        mock_config["quality"]["commit_as_they_go"] = True
        mock_config["general"]["journal_directory"] = str(tmp_path)
        mock_get_config.return_value = mock_config

        sample_git_data["is_work_day"] = True

        mock_git_agent = MagicMock()
        mock_git_agent.analyze_day.return_value = sample_git_data
        mock_git.return_value = mock_git_agent

        mock_content_agent = MagicMock()
        mock_content_agent.generate_entry.return_value = {
            "status": "complete",
            "full_markdown": "# 2025-12-31\n\nTest entry",
        }
        mock_content.return_value = mock_content_agent

        mock_stage_commit.return_value = True

        mock_opencode_instance = MagicMock()

        def mock_chat_side_effect(*args, **kwargs):
            """Side effect to return appropriate JSON based on call context."""
            prompt = kwargs.get("message", args[0] if args else "")
            if "fact checker" in prompt.lower():
                return {
                    "content": json.dumps(
                        {
                            "status": "verified",
                            "findings": [],
                        }
                    )
                }
            elif "quality assurance" in prompt.lower():
                return {
                    "content": json.dumps(
                        {
                            "status": "passed",
                            "checks": {
                                "readability": {"score": 8, "notes": "Good"},
                                "completeness": {"score": 9, "notes": "Complete"},
                                "accuracy": {"score": 10, "notes": "Accurate"},
                                "overall_quality": {"score": 9, "notes": "Good"},
                            },
                            "recommendations": [],
                        }
                    )
                }
            return {"content": "{}"}

        mock_opencode_instance.chat.side_effect = mock_chat_side_effect
        mock_client.return_value = mock_opencode_instance

        orchestrator = Orchestrator()
        result = orchestrator.run_day("2025-12-31")

        assert result["final_status"] == "success"
        assert result["is_work_day"] is True

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    @patch("orchestrator.ensure_opencode_running")
    def test_run_day_exception(
        self, mock_ensure, mock_client, mock_content, mock_git, mock_get_config, mock_config
    ):
        """Test run_day with exception."""
        mock_get_config.return_value = mock_config

        mock_git_agent = MagicMock()
        mock_git_agent.analyze_day.side_effect = Exception("Test error")
        mock_git.return_value = mock_git_agent

        mock_opencode_instance = MagicMock()
        mock_opencode_instance.chat.return_value = {"content": "abort"}
        mock_client.return_value = mock_opencode_instance

        orchestrator = Orchestrator()
        result = orchestrator.run_day("2025-12-31")

        assert result["final_status"] == "error" or result["final_status"] == "no_work"

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    @patch("orchestrator.ensure_opencode_running")
    @patch("orchestrator.stage_and_commit")
    def test_generate_fallback_content(
        self,
        mock_stage_commit,
        mock_ensure,
        mock_client,
        mock_content,
        mock_git,
        mock_get_config,
        mock_config,
        sample_git_data,
        tmp_path,
    ):
        """Test _generate_fallback_content method."""
        mock_config["quality"]["commit_as_they_go"] = False
        mock_config["general"]["journal_directory"] = str(tmp_path)
        mock_get_config.return_value = mock_config

        sample_git_data["is_work_day"] = True

        mock_git_agent = MagicMock()
        mock_git_agent.analyze_day.return_value = sample_git_data
        mock_git.return_value = mock_git_agent

        mock_content_agent = MagicMock()
        mock_content_agent.generate_entry.side_effect = Exception("Generation failed")
        mock_content.return_value = mock_content_agent

        mock_opencode_instance = MagicMock()
        mock_opencode_instance.chat.return_value = {"content": "use_fallback"}
        mock_client.return_value = mock_opencode_instance

        orchestrator = Orchestrator()
        result = orchestrator.run_day("2025-12-31")

        assert result["stages"]["content_generation"]["status"] == "fallback"
        content = result["stages"]["content_generation"]["full_markdown"]
        assert "# 2025-12-31" in content
        assert "Automated generation failed" in content

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    @patch("orchestrator.ensure_opencode_running")
    @patch("orchestrator.stage_and_commit")
    def test_get_opencode_decision(
        self,
        mock_stage_commit,
        mock_ensure,
        mock_client,
        mock_content,
        mock_git,
        mock_get_config,
        mock_config,
        sample_git_data,
        tmp_path,
    ):
        """Test _get_opencode_decision method."""
        mock_config["quality"]["commit_as_they_go"] = False
        mock_config["general"]["journal_directory"] = str(tmp_path)
        mock_get_config.return_value = mock_config

        mock_git_agent = MagicMock()
        mock_git_agent.analyze_day.return_value = sample_git_data
        mock_git.return_value = mock_git_agent

        mock_content_agent = MagicMock()
        mock_content_agent.generate_entry.return_value = {
            "status": "complete",
            "full_markdown": "# Test",
        }
        mock_content.return_value = mock_content_agent

        mock_opencode_instance = MagicMock()
        mock_opencode_instance.chat.return_value = {"content": "retry"}
        mock_client.return_value = mock_opencode_instance

        orchestrator = Orchestrator()

        mock_content_agent.generate_entry.side_effect = Exception("Failed")
        orchestrator.run_day("2025-12-31")

        mock_opencode_instance.chat.assert_called()

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    @patch("orchestrator.ensure_opencode_running")
    @patch("orchestrator.stage_and_commit")
    def test_evaluate_qa_result_passing(
        self,
        mock_stage_commit,
        mock_ensure,
        mock_client,
        mock_content,
        mock_git,
        mock_get_config,
        mock_config,
        sample_git_data,
        tmp_path,
    ):
        """Test _evaluate_qa_result with passing score."""
        mock_config["quality"]["commit_as_they_go"] = False
        mock_config["general"]["journal_directory"] = str(tmp_path)
        mock_get_config.return_value = mock_config

        sample_git_data["is_work_day"] = True

        mock_git_agent = MagicMock()
        mock_git_agent.analyze_day.return_value = sample_git_data
        mock_git.return_value = mock_git_agent

        mock_content_agent = MagicMock()
        mock_content_agent.generate_entry.return_value = {
            "status": "complete",
            "full_markdown": "# Test",
        }
        mock_content.return_value = mock_content_agent

        mock_opencode_instance = MagicMock()

        def mock_chat_side_effect(*args, **kwargs):
            """Side effect to return appropriate JSON based on call context."""
            prompt = kwargs.get("message", args[0] if args else "")
            if "fact checker" in prompt.lower():
                return {
                    "content": json.dumps(
                        {
                            "status": "verified",
                            "findings": [],
                        }
                    )
                }
            elif "quality assurance" in prompt.lower():
                return {
                    "content": json.dumps(
                        {
                            "status": "passed",
                            "checks": {
                                "overall_quality": {"score": 8, "notes": "Good"},
                            },
                        }
                    )
                }
            return {"content": "{}"}

        mock_opencode_instance.chat.side_effect = mock_chat_side_effect
        mock_client.return_value = mock_opencode_instance

        orchestrator = Orchestrator()

        result = orchestrator.run_day("2025-12-31")

        assert result["final_status"] == "success"

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    @patch("orchestrator.ensure_opencode_running")
    @patch("orchestrator.stage_and_commit")
    def test_evaluate_qa_result_failing(
        self,
        mock_stage_commit,
        mock_ensure,
        mock_client,
        mock_content,
        mock_git,
        mock_get_config,
        mock_config,
        sample_git_data,
        tmp_path,
    ):
        """Test _evaluate_qa_result with failing score."""
        mock_config["quality"]["commit_as_they_go"] = False
        mock_config["general"]["journal_directory"] = str(tmp_path)
        mock_get_config.return_value = mock_config

        sample_git_data["is_work_day"] = True

        mock_git_agent = MagicMock()
        mock_git_agent.analyze_day.return_value = sample_git_data
        mock_git.return_value = mock_git_agent

        mock_content_agent = MagicMock()
        mock_content_agent.generate_entry.return_value = {
            "status": "complete",
            "full_markdown": "# Test",
        }
        mock_content.return_value = mock_content_agent

        mock_opencode_instance = MagicMock()

        def mock_chat_side_effect(*args, **kwargs):
            """Side effect to return appropriate JSON based on call context."""
            prompt = kwargs.get("message", args[0] if args else "")
            if "fact checker" in prompt.lower():
                return {
                    "content": json.dumps(
                        {
                            "status": "verified",
                            "findings": [],
                        }
                    )
                }
            elif "quality assurance" in prompt.lower():
                return {
                    "content": json.dumps(
                        {
                            "status": "passed",
                            "checks": {
                                "overall_quality": {"score": 5, "notes": "Needs work"},
                            },
                        }
                    )
                }
            elif "qa score" in prompt.lower():
                return {"content": "reject"}
            return {"content": "{}"}

        mock_opencode_instance.chat.side_effect = mock_chat_side_effect
        mock_client.return_value = mock_opencode_instance

        orchestrator = Orchestrator()

        result = orchestrator.run_day("2025-12-31")

        assert result["final_status"] == "quality_check_failed"

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    @patch("orchestrator.ensure_opencode_running")
    def test_send_notification(
        self, mock_ensure, mock_client, mock_content, mock_git, mock_get_config, mock_config
    ):
        """Test _send_notification method."""
        mock_get_config.return_value = mock_config

        mock_git_agent = MagicMock()
        mock_git_agent.analyze_day.return_value = {
            "is_work_day": False,
            "date": "2025-12-31",
        }
        mock_git.return_value = mock_git_agent

        orchestrator = Orchestrator()

        with patch("subprocess.run") as mock_run:
            orchestrator._send_notification("Test notification")
            mock_run.assert_called_once()

        with patch("subprocess.run", side_effect=FileNotFoundError):
            orchestrator._send_notification("Test notification")

    @patch("orchestrator.get_config")
    @patch("orchestrator.GitAnalysisAgent")
    @patch("orchestrator.ContentGenerationAgent")
    @patch("orchestrator.OpenCodeClient")
    @patch("orchestrator.ensure_opencode_running")
    def test_get_entry_path(
        self, mock_ensure, mock_client, mock_content, mock_git, mock_get_config, mock_config
    ):
        """Test _get_entry_path method."""
        mock_get_config.return_value = mock_config

        mock_git_agent = MagicMock()
        mock_git_agent.analyze_day.return_value = {
            "is_work_day": False,
            "date": "2025-12-31",
        }
        mock_git.return_value = mock_git_agent

        orchestrator = Orchestrator()

        path = orchestrator._get_entry_path("2025-12-31")
        assert path == Path("/tmp/test_journal/2025/12/31.md")

        path = orchestrator._get_entry_path("2026-01-01")
        assert path == Path("/tmp/test_journal/2026/01/01.md")
