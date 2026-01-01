#!/usr/bin/env python3
"""Git Analysis Agent - Extracts commit data from repositories."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.git_utils import (
    get_commits_by_date,
    calculate_loc_changes,
    categorize_commit,
    extract_task_id,
    get_repo_description,
    is_work_day,
)
from config import get_config


class GitAnalysisAgent:
    """Analyzes git repositories to extract daily commit data."""

    def __init__(self):
        self.config = get_config()
        self.code_dir = Path(self.config["general"]["code_directory"])
        self.journal_dir = Path(self.config["general"]["journal_directory"])
        self.author_name = self.config["general"]["author_name"]

    def analyze_day(self, date: str) -> Dict:
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

        for repo_name in repos:
            repo_path = self.code_dir / repo_name

            if not self._should_scan_repo(repo_name):
                continue

            if not is_work_day(repo_path, date, self.author_name):
                continue

            print(f"  📁 {repo_name}")

            commits = get_commits_by_date(repo_path, date, self.author_name)
            if not commits:
                continue

            loc_added, loc_deleted = calculate_loc_changes(
                repo_path, date, self.author_name
            )

            commits_by_category = self._categorize_commits(commits)
            top_features = self._extract_top_features(commits)

            repo_data = {
                "commits": len(commits),
                "loc_added": loc_added,
                "loc_deleted": loc_deleted,
                "commits_by_category": commits_by_category,
                "top_features": top_features,
                "first_commit": commits[0]["timestamp"],
                "last_commit": commits[-1]["timestamp"],
                "commit_messages": [c["message"] for c in commits],
            }

            repo_results[repo_name] = repo_data

            results["total_commits"] += len(commits)
            results["total_loc_added"] += loc_added
            results["total_loc_deleted"] += loc_deleted

        results["repos"] = repo_results
        results["is_work_day"] = results["total_commits"] > 0

        if results["is_work_day"]:
            results["estimated_hours"] = self._estimate_hours(repo_results)

        print(
            f"  ✓ Found {results['total_commits']} commits across {len(repo_results)} repos"
        )
        print(
            f"  ✓ ~{results['total_loc_added']:,} lines added, ~{results['total_loc_deleted']:,} deleted"
        )
        print(f"  ✓ Estimated: {results['estimated_hours']:.1f} hours")

        return results

    def _get_all_repos(self) -> List[str]:
        """Get list of all repositories to scan."""
        exclude_repos = self.config["git"]["exclude_repos"]
        exclude_patterns = self.config["git"]["exclude_patterns"]

        all_dirs = [
            d.name
            for d in self.code_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
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

    def _categorize_commits(self, commits: List[Dict]) -> Dict[str, int]:
        """Categorize commits by type."""
        categories = {}

        for commit in commits:
            category = categorize_commit(commit["message"])
            categories[category] = categories.get(category, 0) + 1

        return categories

    def _extract_top_features(self, commits: List[Dict]) -> List[str]:
        """Extract top features from commit messages."""
        messages = [c["message"] for c in commits]

        # Filter out minor commits
        minor_prefixes = ["chore:", "style:", "fix:", "merge:"]
        significant_messages = [
            m
            for m in messages
            if not any(m.lower().startswith(p) for p in minor_prefixes)
        ]

        # Extract unique features (first 60 chars)
        features = []
        seen = set()

        for msg in significant_messages[:10]:  # Top 10 significant commits
            feature = msg[:60] + "..." if len(msg) > 60 else msg
            feature_key = msg[:30]  # De-dupe by first 30 chars

            if feature_key not in seen:
                seen.add(feature_key)
                features.append(msg)

        return features[:5]  # Return top 5

    def _estimate_hours(self, repo_results: Dict[str, Dict]) -> float:
        """Estimate hours worked based on commit timestamps."""
        all_timestamps = []

        for repo_data in repo_results.values():
            if "first_commit" in repo_data and "last_commit" in repo_data:
                all_timestamps.append(repo_data["first_commit"])
                all_timestamps.append(repo_data["last_commit"])

        if not all_timestamps:
            return 0.0

        # Find earliest and latest
        timestamps_sorted = sorted(all_timestamps)
        first = datetime.fromisoformat(timestamps_sorted[0])
        last = datetime.fromisoformat(timestamps_sorted[-1])

        # Calculate span in hours
        span_hours = (last - first).total_seconds() / 3600

        # Apply adjustment factor (based on December patterns: ~12-15 commits/hour)
        total_commits = sum(r["commits"] for r in repo_results.values())
        if span_hours > 0:
            commits_per_hour = total_commits / span_hours
            # If commits/hour is very high (>20), they're probably working faster
            # If commits/hour is very low (<5), they're probably doing other work
            adjustment = (
                max(0.5, min(2.0, 10 / commits_per_hour))
                if commits_per_hour > 0
                else 1.0
            )
            return span_hours * adjustment

        return span_hours


if __name__ == "__main__":
    # Test with December 31, 2025
    agent = GitAnalysisAgent()
    result = agent.analyze_day("2025-12-31")
    print(json.dumps(result, indent=2))
