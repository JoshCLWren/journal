#!/usr/bin/env python3
"""Quality Assurance Agent - Validates and commits journal entries."""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from opencode_client import OpenCodeClient
from utils.markdown_utils import validate_markdown_syntax


class QualityAssuranceAgent:
    """Validates journal entry quality and handles file creation and git operations."""

    def __init__(self):
        """Initialize QualityAssuranceAgent with config and OpenCode client."""
        self.config = get_config()
        self.client = OpenCodeClient(base_url=self.config["scheduling"]["opencode_url"])

    def validate_and_commit(self, content: str, git_data: dict, date: str) -> dict:
        """Validate content quality and commit to journal if approved."""
        print(f"\n✅ Quality Assurance Agent: Validating entry for {date}")

        result = {
            "status": "fail",
            "issues": [],
            "suggestions": [],
            "overall_score": 0,
            "file_path": "",
            "committed": False,
            "reasoning": "",
        }

        try:
            # Step 1: Validate Markdown syntax
            print("  → Validating Markdown syntax...")
            syntax_errors = validate_markdown_syntax(content)
            if syntax_errors:
                result["issues"].extend([f"Syntax: {err}" for err in syntax_errors])

            # Step 2: Review content quality using OpenCode
            print("  → Reviewing content quality...")
            quality_report = self._review_quality(content, git_data, date)

            # Step 3: Check cross-references
            print("  → Validating cross-references...")
            ref_issues = self._check_cross_references(content, git_data)
            if ref_issues:
                result["issues"].extend(ref_issues)

            # Step 4: Determine overall status
            result["reasoning"] = quality_report.get("reasoning", "")
            result["suggestions"] = quality_report.get("suggestions", [])
            result["overall_score"] = quality_report.get("score", 0)

            # Determine pass/fail based on quality threshold
            min_score = 70
            critical_issues = any("critical" in issue.lower() for issue in result["issues"])

            if result["overall_score"] >= min_score and not critical_issues:
                result["status"] = "pass"
                print(f"  ✓ Quality check passed (Score: {result['overall_score']}/100)")

                # Step 5: Create file
                print("  → Creating journal entry file...")
                result["file_path"] = self._create_journal_file(content, date)

                # Step 6: Commit if auto_commit enabled
                if self.config["scheduling"]["auto_commit"]:
                    print("  → Staging and committing...")
                    result["committed"] = self._commit_file(result["file_path"], date)
                    if result["committed"]:
                        print("  ✓ File committed successfully")
                    else:
                        print("  ✗ Commit failed (file created but not committed)")
                else:
                    print("  → Auto-commit disabled, file created but not committed")

            else:
                result["status"] = "fail"
                print(f"  ✗ Quality check failed (Score: {result['overall_score']}/100)")
                if result["issues"]:
                    print(f"  Issues: {', '.join(result['issues'][:3])}")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            result["status"] = "fail"
            result["reasoning"] = f"Validation error: {str(e)}"

        return result

    def _review_quality(self, content: str, git_data: dict, date: str) -> dict:
        """Use OpenCode LLM to review content quality."""
        prompt = f"""You are a quality assurance specialist validating a coding journal entry.

## Context
- Date: {date}
- Git data summary: 
  - Total commits: {git_data.get("total_commits", 0)}
  - Repositories: {", ".join(git_data.get("repos", {}).keys())}
  - Work day: {git_data.get("is_work_day", False)}

## Journal Entry Content
{content[:8000]}

## Task
Evaluate the quality on a scale of 0-100 considering:
1. Structure and Format (markdown, headers, consistency)
2. Content Quality (clear, technical, accurate)
3. Readability (professional, logical flow)
4. Completeness (all repos covered, no major omissions)
5. Accuracy (commits, hours, LOC estimates)
6. Value (useful for future reference)

## Output Format
Respond with ONLY valid JSON:
{{
  "score": 0-100,
  "reasoning": "Brief explanation of the score",
  "suggestions": ["specific improvement 1", "specific improvement 2"],
  "strengths": ["what was done well"]
}}

If score < 70, include critical issues in reasoning."""

        try:
            response = self.client.chat(
                message=prompt,
                model=self.config["opencode"]["model"],
                provider=self.config["opencode"]["provider"],
            )

            content_text = response.get("content", "{}")

            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", content_text)
            if json_match:
                content_text = json_match.group(0)

            review = json.loads(content_text)

            return {
                "score": review.get("score", 70),
                "reasoning": review.get("reasoning", ""),
                "suggestions": review.get("suggestions", []),
                "strengths": review.get("strengths", []),
            }

        except (json.JSONDecodeError, KeyError) as e:
            print(f"  ! Could not parse quality review: {e}")
            return {
                "score": 70,
                "reasoning": "Could not parse LLM review, passing with default score",
                "suggestions": [],
                "strengths": [],
            }

    def _check_cross_references(self, content: str, git_data: dict) -> list:
        """Check that projects in legend match git data."""
        issues = []

        # Extract repos from git_data
        git_repos = set(git_data.get("repos", {}).keys())

        # Extract repos from content (look for repo mentions)
        content_repos = set()
        for repo_name in git_repos:
            if repo_name in content:
                content_repos.add(repo_name)

        # Check if all git repos with significant commits are mentioned
        min_commits = self.config["quality"]["min_commits_for_section"]
        for repo_name, repo_data in git_data.get("repos", {}).items():
            if repo_data.get("commits", 0) >= min_commits:
                if repo_name not in content_repos:
                    issues.append(
                        f"Missing reference to repo with {repo_data['commits']} commits: {repo_name}"
                    )

        # Check for broken references (mentioned repos not in git_data)
        legend_pattern = r"###\s+([^\n]+)"
        legend_repos = set(re.findall(legend_pattern, content))
        for repo in legend_repos:
            repo_clean = repo.strip().replace("~/code/", "")
            if repo_clean not in git_repos:
                issues.append(f"Project in legend not in git data: {repo_clean}")

        return issues

    def _create_journal_file(self, content: str, date: str) -> str:
        """Create the journal file with proper directory structure."""
        journal_dir = Path(self.config["general"]["journal_directory"])

        # Parse date
        try:
            from datetime import datetime

            dt = datetime.strptime(date, "%Y-%m-%d")
            year = dt.strftime("%Y")
            month = dt.strftime("%m")
            day = dt.strftime("%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date}") from None

        # Create directory structure YYYY/MM/
        target_dir = journal_dir / year / month
        target_dir.mkdir(parents=True, exist_ok=True)

        # Write file to YYYY/MM/DD.md
        file_path = target_dir / f"{day}.md"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Set file permissions to 644 (rw-r--r--)
        os.chmod(file_path, 0o644)

        return str(file_path.relative_to(journal_dir))

    def _commit_file(self, file_path: str, date: str) -> bool:
        """Stage and commit the file using git."""
        from utils.git_utils import stage_and_commit

        journal_dir = Path(self.config["general"]["journal_directory"])
        full_file_path = journal_dir / file_path

        commit_message = f"docs: add journal entry for {date}"

        return stage_and_commit(journal_dir, full_file_path, commit_message)


if __name__ == "__main__":
    # Test with sample data
    agent = QualityAssuranceAgent()

    sample_content = """# December 31, 2025

**Work Summary:** ~12.5 hours, ~4800 lines - Auto-generated by journal automation

## Summary
Focused on comic-pile improvements, adding Staleness Awareness UI and performance optimizations. intensive work day with significant feature additions.

## Repositories Worked On

- `~/code/comic-pile` (43 commits)

- **Total: 43 commits**

## comic-pile

**Staleness Awareness**
- feat(TASK-102): Add Staleness Awareness UI
- feat: Display staleness indicators on comic cards
- fix: Correct staleness calculation logic

**Performance**
- refactor: Optimize database queries for large collections
- perf: Add caching for frequently accessed data

---

## Projects Legend

### comic-pile
Comic collection management application with features for tracking, organizing, and discovering comics.
"""

    sample_git_data = {
        "date": "2025-12-31",
        "is_work_day": True,
        "total_commits": 43,
        "total_loc_added": 4000,
        "total_loc_deleted": 800,
        "estimated_hours": 12.5,
        "repos": {
            "comic-pile": {
                "commits": 43,
                "commits_by_category": {
                    "feat": 25,
                    "fix": 10,
                    "refactor": 5,
                    "docs": 3,
                },
                "top_features": ["feat(TASK-102): Add Staleness Awareness UI"],
            }
        },
    }

    result = agent.validate_and_commit(sample_content, sample_git_data, "2025-12-31")
    print(json.dumps(result, indent=2))
