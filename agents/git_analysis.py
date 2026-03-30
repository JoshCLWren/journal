#!/usr/bin/env python3
"""Git Analysis Agent - Extracts commit data from repositories."""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from utils.git_utils import (
    calculate_loc_changes_for_hashes,
    categorize_commit,
    get_commits_by_date,
)


class GitAnalysisAgent:
    """Analyzes git repositories to extract daily commit data."""

    def __init__(self):
        """Initialize GitAnalysisAgent with config and repository paths."""
        self.config = get_config()
        self.code_dir = Path(self.config["general"]["code_directory"])
        self.journal_dir = Path(self.config["general"]["journal_directory"])
        self.author_name = self.config["general"]["author_name"]

    def analyze_day(self, date: str) -> dict:
        """Analyze all repositories for a specific date."""
        print(f"\n📊 Git Analysis Agent: Analyzing {date}")

        repos = self._get_all_repos()
        results = {
            "date": date,
            "is_work_day": False,
            "total_commits": 0,
            "total_loc_added": 0,
            "total_loc_deleted": 0,
            "estimated_hours": 0.0,
            "repos": {},
        }

        repo_results = {}
        seen_commit_hashes = set()
        hash_to_repo = {}

        for repo_name in repos:
            repo_path = self.code_dir / repo_name

            if not self._should_scan_repo(repo_name):
                continue

            commits = get_commits_by_date(repo_path, date, self.author_name)
            if not commits:
                continue

            unique_commits = []
            for commit in commits:
                if commit["hash"] not in seen_commit_hashes:
                    seen_commit_hashes.add(commit["hash"])
                    hash_to_repo[commit["hash"]] = repo_name
                    unique_commits.append(commit)

            print(f"    Total: {len(commits)}, Unique: {len(unique_commits)}")

            commits_by_category = self._categorize_commits(unique_commits)
            top_features = self._extract_top_features(unique_commits)

            # Skip repos with no unique commits
            if not unique_commits:
                continue

            unique_hashes = [c["hash"] for c in unique_commits]
            loc_added, loc_deleted = calculate_loc_changes_for_hashes(repo_path, unique_hashes)

            # Sort unique commits by timestamp to get correct first/last
            sorted_commits = sorted(unique_commits, key=lambda c: c["timestamp"])

            repo_data = {
                "commits": len(unique_commits),
                "commits_total": len(commits),
                "loc_added": loc_added,
                "loc_deleted": loc_deleted,
                "commits_by_category": commits_by_category,
                "top_features": top_features,
                "first_commit": sorted_commits[0]["timestamp"],
                "last_commit": sorted_commits[-1]["timestamp"],
                "commit_messages": [c["message"] for c in unique_commits],
                "commit_hashes": unique_hashes,
            }

            repo_results[repo_name] = repo_data

        results["repos"] = repo_results

        results["total_commits"] = len(seen_commit_hashes)
        results["is_work_day"] = results["total_commits"] > 0

        if results["is_work_day"]:
            for repo_data in repo_results.values():
                results["total_loc_added"] += repo_data["loc_added"]
                results["total_loc_deleted"] += repo_data["loc_deleted"]
            results["estimated_hours"] = self._estimate_hours(repo_results)

        print(
            f"  ✓ Found {results['total_commits']} unique commits across {len(repo_results)} repos"
        )
        print(
            f"  ✓ ~{results['total_loc_added']:,} lines added, ~{results['total_loc_deleted']:,} deleted"
        )
        print(f"  ✓ Estimated: {results['estimated_hours']:.1f} hours")

        return results

    def _get_all_repos(self) -> list[str]:
        """Get list of all repositories to scan."""
        exclude_repos = self.config["git"]["exclude_repos"]
        exclude_patterns = self.config["git"]["exclude_patterns"]

        all_dirs = [
            d.name for d in self.code_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

        filtered_dirs = []
        for dir_name in all_dirs:
            # Skip excluded repos
            if dir_name in exclude_repos:
                continue

            # Skip repos matching exclude patterns
            if any(pattern in dir_name for pattern in exclude_patterns):
                continue

            # Check if it's a git repo
            if (self.code_dir / dir_name / ".git").exists():
                filtered_dirs.append(dir_name)

        return filtered_dirs

    def _should_scan_repo(self, repo_name: str) -> bool:
        """Check if repo should be scanned."""
        # Skip journal directory itself
        if repo_name == "journal":
            return False

        # Skip non-git directories
        if not (self.code_dir / repo_name / ".git").exists():
            return False

        return True

    def _categorize_commits(self, commits: list[dict]) -> dict[str, int]:
        """Categorize commits by type."""
        categories = {}

        for commit in commits:
            category = categorize_commit(commit["message"])
            categories[category] = categories.get(category, 0) + 1

        return categories

    def _extract_top_features(self, commits: list[dict]) -> list[str]:
        """Extract top features from commit messages."""
        messages = [c["message"] for c in commits]

        # Filter out minor commits
        minor_prefixes = ["chore:", "style:", "fix:", "merge:"]
        significant_messages = [
            m for m in messages if not any(m.lower().startswith(p) for p in minor_prefixes)
        ]

        # Extract unique features (first 60 chars)
        features = []
        seen = set()

        for msg in significant_messages[:10]:  # Top 10 significant commits
            feature_key = msg[:30]  # De-dupe by first 30 chars

            if feature_key not in seen:
                seen.add(feature_key)
                features.append(msg)

        return features[:5]  # Return top 5

    def _estimate_hours(self, repo_results: dict[str, dict]) -> float:
        """Estimate actual active hours by merging commit timestamps across all repos."""
        # Collect all commit timestamps across all repos
        all_timestamps = []
        for _repo_name, repo_data in repo_results.items():
            if "commits" not in repo_data or repo_data["commits"] == 0:
                continue

            # Add minimum time for repos with few commits
            if repo_data["commits"] <= 2:
                all_timestamps.append((repo_data["first_commit"], 0.25))  # 15 min minimum
                continue

            all_timestamps.append((repo_data["first_commit"], repo_data["last_commit"]))

        if not all_timestamps:
            return 0.0

        # Convert to datetime objects and sort by start time
        sessions = []
        for start_str, end_data in all_timestamps:
            if isinstance(end_data, str):
                start = datetime.fromisoformat(start_str)
                end = datetime.fromisoformat(end_data)
                duration_hours = (end - start).total_seconds() / 3600
                sessions.append((start, end, duration_hours))
            else:
                # It's a minimum time entry (start_str, min_hours)
                sessions.append((datetime.fromisoformat(start_str), None, end_data))

        # Sort by start time
        sessions.sort(key=lambda x: x[0])

        # Merge overlapping or nearby sessions (gap < 2 hours = same session)
        merged_sessions = []
        gap_threshold_hours = 2.0

        for start, end, duration in sessions:
            if end is None:
                # Minimum time entry - just add the duration
                merged_sessions.append(duration)
            else:
                if not merged_sessions or isinstance(merged_sessions[-1], float):
                    # Start new session
                    merged_sessions.append([start, end])
                else:
                    last_start, last_end = merged_sessions[-1]
                    gap = (start - last_end).total_seconds() / 3600

                    if gap < gap_threshold_hours:
                        # Merge with previous session
                        merged_sessions[-1][1] = max(merged_sessions[-1][1], end)
                    else:
                        # Start new session
                        merged_sessions.append([start, end])

        # Calculate total hours
        total_hours = 0.0
        for session in merged_sessions:
            if isinstance(session, float):
                total_hours += session
            else:
                start, end = session
                session_hours = (end - start).total_seconds() / 3600
                # Cap individual sessions at 8 hours (realistic max continuous work)
                total_hours += min(session_hours, 8.0)

        return round(total_hours, 1)


if __name__ == "__main__":
    # Test with December 31, 2025
    agent = GitAnalysisAgent()
    result = agent.analyze_day("2025-12-31")
    print(json.dumps(result, indent=2))
