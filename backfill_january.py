#!/usr/bin/env python3
"""Backfill missing journal entries for January 2026."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import OrchestratorAgent


def main():
    """Backfill missing entries for January 2026."""
    # January 2026
    year = 2026
    month = 1

    # Get all days in January
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month, 31)

    # Journal directory
    journal_dir = Path.home() / "code" / "journal"

    orchestrator = OrchestratorAgent()

    print(f"Backfilling journal entries for {year}-{month:02d}")
    print("=" * 60)

    current_date = start_date
    success_count = 0
    skip_count = 0
    fail_count = 0

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        entry_path = journal_dir / current_date.strftime("%Y/%m/%d.md")

        # Check if entry already exists
        if entry_path.exists():
            print(f"✓ {date_str}: Entry already exists, skipping")
            skip_count += 1
        else:
            print(f"\nProcessing {date_str}...")
            result = orchestrator.run_day(current_date)

            if result["status"] == "success":
                print(f"  ✓ Entry created: {result.get('entry_path')}")
                success_count += 1
            elif result["status"] == "no_work":
                print("  ℹ No work on this date")
                skip_count += 1
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                fail_count += 1

        current_date += timedelta(days=1)

    print("\n" + "=" * 60)
    print("Backfill complete:")
    print(f"  - Created: {success_count}")
    print(f"  - Skipped: {skip_count}")
    print(f"  - Failed: {fail_count}")


if __name__ == "__main__":
    main()
