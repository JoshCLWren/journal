#!/usr/bin/env python3
"""Orchestrator Agent - Coordinates the journal generation workflow."""

import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.content_generation import ContentGenerationAgent
from agents.fact_checking import FactCheckingAgent
from agents.git_analysis import GitAnalysisAgent
from agents.quality_assurance import QualityAssuranceAgent
from agents.validator import ValidationAgent
from commit_agent import CommitAgent
from config import get_config

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Orchestrates the journal entry generation workflow."""

    def __init__(self):
        """Initialize OrchestratorAgent with sub-agents and config."""
        self.git_agent = GitAnalysisAgent()
        self.content_agent = ContentGenerationAgent()
        self.fact_checking_agent = FactCheckingAgent()
        self.quality_assurance_agent = QualityAssuranceAgent()
        self.validation_agent = ValidationAgent()
        self.commit_agent = CommitAgent()
        config = get_config()
        self.journal_dir = Path(config["general"]["journal_directory"]).expanduser()

    def run_day(self, date: datetime) -> dict:
        """Run full workflow for a specific day.

        Args:
            date: Date to generate entry for

        Returns:
            dict: {
                'status': 'success' | 'skipped' | 'failed',
                'entry_path': Path or None,
                'commit_hash': str or None,
                'error': str or None
            }
        """
        try:
            logger.info(f"Starting orchestrator for {date.strftime('%Y-%m-%d')}")

            # Step 1: Git Analysis - Extract commit data
            git_data = self.git_agent.analyze_day(date.strftime("%Y-%m-%d"))

            if not git_data["is_work_day"]:
                logger.info("No commits on this date, skipping entry generation")
                return {
                    "status": "skipped",
                    "entry_path": None,
                    "commit_hash": None,
                    "error": None,
                }

            # Step 2: Content Generation - Create draft entry
            content_result = self.content_agent.generate_entry(git_data)

            if content_result["status"] != "complete":
                error = content_result.get("error", "Content generation failed")
                logger.error(f"Content generation failed: {error}")
                return {
                    "status": "failed",
                    "entry_path": None,
                    "commit_hash": None,
                    "error": error,
                }

            markdown_content = content_result["full_markdown"]

            # Step 3: Fact Checking - Validate accuracy
            fact_check_result = self.fact_checking_agent.check_entry(git_data, markdown_content)

            if fact_check_result["status"] == "fail":
                error = "; ".join(fact_check_result.get("errors", ["Fact checking failed"]))
                logger.error(f"Fact checking failed: {error}")
                return {
                    "status": "failed",
                    "entry_path": None,
                    "commit_hash": None,
                    "error": f"Fact-checking failed: {error}",
                }

            # Step 4: Quality Assurance - Ensure quality standards
            qa_result = self.quality_assurance_agent.validate_and_commit(
                markdown_content, git_data, date.strftime("%Y-%m-%d")
            )

            if qa_result["status"] != "pass":
                error = "; ".join(qa_result.get("issues", ["Quality assurance failed"]))
                logger.error(f"Quality assurance failed: {error}")
                return {
                    "status": "failed",
                    "entry_path": None,
                    "commit_hash": None,
                    "error": f"Quality assurance failed: {error}",
                }

            entry_path = self.journal_dir / qa_result["file_path"]

            # Step 5: Validation Agent - Final verification
            validation_result = self.validation_agent.validate_entry(entry_path)

            if not validation_result["valid"]:
                error = "; ".join(validation_result.get("issues", ["Validation failed"]))
                logger.error(f"Validation failed: {error}")
                return {
                    "status": "failed",
                    "entry_path": entry_path,
                    "commit_hash": None,
                    "error": f"Validation failed: {error}",
                }

            # Step 6: Commit (if not already committed by QA agent)
            commit_hash = None
            if not qa_result.get("committed", False):
                commit_result = self.commit_agent.commit_entry(date, entry_path)
                if commit_result.get("success"):
                    commit_hash = commit_result.get("commit_hash")
                else:
                    logger.warning(f"Commit failed: {commit_result.get('error')}")
            else:
                commit_hash = "committed_by_qa_agent"
                logger.info("Entry already committed by Quality Assurance agent")

            return {
                "status": "success",
                "entry_path": entry_path,
                "commit_hash": commit_hash,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Orchestrator failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "entry_path": None,
                "commit_hash": None,
                "error": str(e),
            }

    def _write_entry(self, date: datetime, content: str) -> Path:
        """Write journal entry to disk.

        Args:
            date: Date of entry
            content: Markdown content

        Returns:
            Path: Path to written entry file
        """
        year_month = date.strftime("%Y/%m")
        entry_file = date.strftime("%d.md")
        entry_path = self.journal_dir / year_month / entry_file

        entry_path.parent.mkdir(parents=True, exist_ok=True)

        with open(entry_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Entry written to: {entry_path}")
        return entry_path


if __name__ == "__main__":
    from datetime import datetime

    logging.basicConfig(level=logging.INFO)

    orchestrator = OrchestratorAgent()
    result = orchestrator.run_day(datetime.now())

    print(f"Status: {result['status']}")
    if result["entry_path"]:
        print(f"Entry: {result['entry_path']}")
    if result["commit_hash"]:
        print(f"Commit: {result['commit_hash']}")
    if result["error"]:
        print(f"Error: {result['error']}")
