#!/usr/bin/env python3
"""Git utility functions for journal automation."""

import re
import subprocess
from pathlib import Path


def run_git_command(repo_path: Path, *args: str) -> str:
    """Run a git command and return stdout."""
    cmd = ["git", "-C", str(repo_path)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.stdout


def get_commits_by_date(
    repo_path: Path,
    date: str,
    author_name: str,
) -> list[dict]:
    """Get all commits for a specific date by author."""
    start = f"{date} 00:00:00"
    end = f"{date} 23:59:59"

    output = run_git_command(
        repo_path,
        "log",
        f"--since={start}",
        f"--until={end}",
        f"--author={author_name}",
        "--pretty=format:%H|%ai|%s",
    )

    commits = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        hash_id, timestamp, message = line.split("|", 2)
        commits.append(
            {
                "hash": hash_id,
                "timestamp": timestamp,
                "message": message,
            }
        )

    return commits


def calculate_loc_changes(repo_path: Path, date: str, author_name: str) -> tuple[int, int]:
    """Calculate lines added and deleted for a date."""
    start = f"{date} 00:00:00"
    end = f"{date} 23:59:59"

    output = run_git_command(
        repo_path,
        "log",
        f"--since={start}",
        f"--until={end}",
        f"--author={author_name}",
        "--numstat",
        "--pretty=tformat:",
    )

    added = 0
    deleted = 0
    for line in output.strip().split("\n"):
        if not line or line.startswith(" "):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            deleted += int(parts[1])

    return added, deleted


def calculate_loc_changes_for_hashes(repo_path: Path, commit_hashes: list[str]) -> tuple[int, int]:
    """Calculate lines added and deleted for specific commit hashes."""
    if not commit_hashes:
        return 0, 0

    added = 0
    deleted = 0

    output = run_git_command(
        repo_path,
        "show",
        "--numstat",
        "--pretty=tformat:",
        *commit_hashes,
    )

    for line in output.strip().split("\n"):
        if not line or line.startswith(" "):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            deleted += int(parts[1])

    return added, deleted


def categorize_commit(message: str) -> str:
    """Categorize a commit by its prefix."""
    prefix_match = re.match(
        r"^(feat|fix|refactor|docs|test|chore|perf|style|build|ci|revert)",
        message.lower(),
    )

    if prefix_match:
        return prefix_match.group(1)
    return "other"


def extract_task_id(message: str) -> str | None:
    """Extract TASK-ID from commit message."""
    task_match = re.search(r"TASK[-_]?\d+", message)
    return task_match.group(0) if task_match else None


def get_repo_description(repo_path: Path) -> str | None:
    """Extract description from repo README."""
    for readme_name in ["README.md", "readme.md", "README.rst"]:
        readme_path = repo_path / readme_name
        if readme_path.exists():
            try:
                with open(readme_path, encoding="utf-8") as f:
                    content = f.read()
                    # Extract first paragraph or sentence
                    first_line = content.split("\n")[0]
                    if first_line and not first_line.startswith("#"):
                        return first_line.strip()
                    # If starts with header, find first real paragraph
                    lines = content.split("\n")
                    for line in lines:
                        if line and not line.startswith("#"):
                            return line.strip()
                    return None
            except Exception:
                return None
    return None


def is_work_day(repo_path: Path, date: str, author_name: str) -> bool:
    """Check if a date has any commits."""
    commits = get_commits_by_date(repo_path, date, author_name)
    return len(commits) > 0


def stage_and_commit(repo_path: Path, file_path: Path, message: str) -> bool:
    """Stage and commit a file to git."""
    try:
        # Stage the file
        subprocess.run(
            ["git", "-C", str(repo_path), "add", str(file_path)],
            check=True,
            capture_output=True,
        )

        # Commit
        result = subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", message],
            check=False,
            capture_output=True,
            text=True,
        )

        return result.returncode == 0
    except Exception:
        return False
