#!/usr/bin/env python3
"""Main CLI entry point for journal automation."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path


from config import get_config
from utils.opencode_utils import ensure_opencode_running
from utils.logging_utils import setup_logging


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Journal automation CLI - Generate and validate journal entries"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # generate command
    generate_parser = subparsers.add_parser(
        "generate", help="Run full automation for a date"
    )
    generate_parser.add_argument(
        "--date", type=str, help="Date in YYYY-MM-DD format (default: today)"
    )

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate existing entry")
    validate_parser.add_argument(
        "--file", type=str, required=True, help="Path to entry file (YYYY/MM/DD.md)"
    )

    # run command
    run_parser = subparsers.add_parser("run", help="Run orchestrator (for cron)")
    run_parser.add_argument(
        "--date", type=str, help="Date in YYYY-MM-DD format (default: today)"
    )

    # status command
    status_parser = subparsers.add_parser(
        "status", help="Check if entry exists and its status"
    )
    status_parser.add_argument(
        "--date", type=str, help="Date in YYYY-MM-DD format (default: today)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    log_dir = Path.home() / ".local" / "share" / "journal-automation" / "logs"
    setup_logging(log_dir)

    logger = logging.getLogger(__name__)

    try:
        # Ensure OpenCode server is running
        logger.info("Checking OpenCode server status")
        opencode_available = ensure_opencode_running()
        if not opencode_available:
            logger.warning(
                "OpenCode server not available. Some features may be limited."
            )
        else:
            logger.info("OpenCode server is running")

        # Execute command
        if args.command == "generate":
            cmd_generate(args, logger)
        elif args.command == "validate":
            cmd_validate(args, logger)
        elif args.command == "run":
            cmd_run(args, logger)
        elif args.command == "status":
            cmd_status(args, logger)
        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def cmd_generate(args, logger):
    """Generate journal entry for a date.

    Args:
        args: Parsed command line arguments
        logger: Logger instance
    """
    date = parse_date(args.date) if args.date else datetime.now()

    logger.info(f"Generating journal entry for {date.strftime('%Y-%m-%d')}")

    from agents.orchestrator import OrchestratorAgent

    orchestrator = OrchestratorAgent()
    result = orchestrator.run_day(date)

    if result["status"] == "success":
        logger.info(f"✓ Entry generated successfully: {result['entry_path']}")
        if result.get("commit_hash"):
            logger.info(f"✓ Committed: {result['commit_hash']}")
    else:
        logger.error(f"✗ Generation failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


def cmd_validate(args, logger):
    """Validate existing journal entry.

    Args:
        args: Parsed command line arguments
        logger: Logger instance
    """
    entry_path = Path(args.file)

    if not entry_path.exists():
        logger.error(f"Entry file not found: {entry_path}")
        sys.exit(1)

    logger.info(f"Validating entry: {entry_path}")

    from agents.validator import ValidationAgent

    validator = ValidationAgent()
    result = validator.validate_entry(entry_path)

    if result["valid"]:
        logger.info("✓ Entry is valid")
    else:
        logger.warning(f"✗ Entry has issues:")
        for issue in result["issues"]:
            logger.warning(f"  - {issue}")
        sys.exit(1)


def cmd_run(args, logger):
    """Run orchestrator for a date (for cron).

    Args:
        args: Parsed command line arguments
        logger: Logger instance
    """
    date = parse_date(args.date) if args.date else datetime.now()

    logger.info(f"Running orchestrator for {date.strftime('%Y-%m-%d')}")

    from agents.orchestrator import OrchestratorAgent

    orchestrator = OrchestratorAgent()
    result = orchestrator.run_day(date)

    if result["status"] == "success":
        logger.info(f"✓ Orchestrator completed: {result['entry_path']}")
    elif result["status"] == "skipped":
        logger.info("ℹ No commits on this date, entry skipped")
    else:
        logger.error(f"✗ Orchestrator failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


def cmd_status(args, logger):
    """Check entry status for a date.

    Args:
        args: Parsed command line arguments
        logger: Logger instance
    """
    date = parse_date(args.date) if args.date else datetime.now()

    config = get_config()
    journal_dir = Path(config["general"]["journal_directory"]).expanduser()
    entry_path = journal_dir / date.strftime("%Y/%m/%d.md")

    if entry_path.exists():
        logger.info(f"✓ Entry exists: {entry_path}")

        # Check if committed
        import subprocess

        result = subprocess.run(
            ["git", "status", "--porcelain", str(entry_path)],
            cwd=journal_dir,
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            logger.info("  Status: Modified (uncommitted changes)")
        else:
            logger.info("  Status: Committed")
    else:
        logger.info(f"✗ Entry does not exist for {date.strftime('%Y-%m-%d')}")


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format.

    Args:
        date_str: Date string

    Returns:
        datetime: Parsed date

    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")


if __name__ == "__main__":
    main()
