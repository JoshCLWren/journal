#!/usr/bin/env python3
"""Backfill missed journal entries."""

import subprocess
import sys
from datetime import datetime, timedelta

dates_to_run = ["2026-01-02", "2026-01-03", "2026-01-04"]

for date_str in dates_to_run:
    print(f"\n{'=' * 60}")
    print(f"Running for {date_str}")
    print("=" * 60)

    result = subprocess.run(
        ["python3", "main.py", "run", "--date", date_str],
        cwd="/home/josh/code/journal",
        capture_output=True,
        text=True,
        timeout=300,  # 5 minutes max per date
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode == 0:
        print(f"✓ Success for {date_str}")
    else:
        print(f"✗ Failed for {date_str} (exit code: {result.returncode})")
