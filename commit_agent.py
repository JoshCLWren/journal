#!/usr/bin/env python3
"""Commit Agent for staging and committing journal entries."""

import logging
from datetime import datetime
from pathlib import Path

from config import get_config

logger = logging.getLogger(__name__)


class CommitAgent:
    """Agent responsible for staging and committing journal entries."""

    def __init__(self):
        """Initialize CommitAgent with config."""
        config = get_config()
        self.journal_repo = Path(config["general"]["journal_directory"]).expanduser()

    def commit_entry(self, date: datetime, entry_path: Path) -> dict:
        """Stage and commit a journal entry.

        Args:
            date: The date of the entry
            entry_path: Path to the entry file

        Returns:
            dict: {
                'success': bool,
                'commit_hash': str or None,
                'message': str,
                'error': str or None
            }
        """
        try:
            if not entry_path.exists():
                return {
                    "success": False,
                    "commit_hash": None,
                    "message": "",
                    "error": f"Entry file not found: {entry_path}",
                }

            logger.info(f"Staging and committing entry: {entry_path}")

            try:
                from utils.git_utils import stage_and_commit

                success = stage_and_commit(
                    repo_path=self.journal_repo,
                    file_path=entry_path,
                    message=self._generate_commit_message(date),
                )
                return {
                    "success": success,
                    "commit_hash": None,
                    "message": self._generate_commit_message(date),
                    "error": None,
                }
            except ImportError:
                logger.warning(
                    "git_utils.stage_and_commit not available, using direct git commands"
                )
                return self._commit_with_git_commands(date, entry_path)

        except Exception as e:
            logger.error(f"Error committing entry: {e}", exc_info=True)
            return {
                "success": False,
                "commit_hash": None,
                "message": "",
                "error": str(e),
            }

    def _commit_with_git_commands(self, date: datetime, entry_path: Path) -> dict:
        """Commit using direct git commands.

        Args:
            date: The date of the entry
            entry_path: Path to the entry file

        Returns:
            dict: Commit result
        """
        import subprocess

        try:
            commit_message = self._generate_commit_message(date)

            subprocess.run(
                ["git", "add", str(entry_path)],
                cwd=self.journal_repo,
                check=True,
                capture_output=True,
                text=True,
            )

            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.journal_repo,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "commit_hash": None,
                    "message": "",
                    "error": f"Git commit failed: {result.stderr}",
                }

            commit_hash = result.stdout.strip().split()[1] if " " in result.stdout else None

            return {
                "success": True,
                "commit_hash": commit_hash,
                "message": commit_message,
                "error": None,
            }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "commit_hash": None,
                "message": "",
                "error": f"Git command failed: {e.stderr}",
            }
        except Exception as e:
            return {
                "success": False,
                "commit_hash": None,
                "message": "",
                "error": str(e),
            }

    def _generate_commit_message(self, date: datetime) -> str:
        """Generate a professional commit message for a journal entry.

        Args:
            date: The date of the entry

        Returns:
            str: Commit message
        """
        date_str = date.strftime("%B %d, %Y")
        return f"Add journal entry for {date_str}"


def main():
    """Main entry point for testing."""
    from datetime import datetime
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    date = datetime.now()
    entry_path = Path.home() / "code" / "journal" / date.strftime("%Y/%m/%d.md")

    agent = CommitAgent()
    result = agent.commit_entry(date, entry_path)

    print(f"Success: {result['success']}")
    if result["success"]:
        print(f"Commit: {result['commit_hash']}")
        print(f"Message: {result['message']}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
