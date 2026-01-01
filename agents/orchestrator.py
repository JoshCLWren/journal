#!/usr/bin/env python3
"""Orchestrator Agent - Coordinates the journal generation workflow."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.git_analysis import GitAnalysisAgent
from agents.content_generation import ContentGenerationAgent
from commit_agent import CommitAgent
from config import get_config

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Orchestrates the journal entry generation workflow."""

    def __init__(self):
        self.git_agent = GitAnalysisAgent()
        self.content_agent = ContentGenerationAgent()
        self.commit_agent = CommitAgent()
        config = get_config()
        self.journal_dir = Path(config["general"]["journal_directory"]).expanduser()

    def run_day(self, date: datetime) -> Dict:
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

            # Step 1: Analyze git data
            git_data = self.git_agent.analyze_day(date.strftime("%Y-%m-%d"))

            if not git_data["is_work_day"]:
                logger.info("No commits on this date, skipping entry generation")
                return {
                    "status": "skipped",
                    "entry_path": None,
                    "commit_hash": None,
                    "error": None,
                }

            # Step 2: Generate content
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

            # Step 3: Write entry to disk
            entry_path = self._write_entry(date, content_result["full_markdown"])

            # Step 4: Commit to git
            commit_result = self.commit_agent.commit_entry(date, entry_path)

            if not commit_result["success"]:
                logger.warning(f"Commit failed: {commit_result.get('error')}")

            return {
                "status": "success",
                "entry_path": entry_path,
                "commit_hash": commit_result.get("commit_hash"),
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
