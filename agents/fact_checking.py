#!/usr/bin/env python3
"""Fact Checking Agent - Validates journal entry accuracy and completeness."""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from opencode_client import OpenCodeClient
from config import get_config


class FactCheckingAgent:
    """Validates journal entries against git data using OpenCode LLM."""

    def __init__(self):
        self.config = get_config()
        self.client = OpenCodeClient(base_url=self.config["scheduling"]["opencode_url"])

    def check_entry(self, git_data: Dict, markdown_content: str) -> Dict:
        """Perform comprehensive fact-checking on generated journal entry."""
        print(f"\n🔍 Fact Checking Agent: Validating {git_data['date']}")

        result = {
            "status": "pass",
            "errors": [],
            "warnings": [],
            "corrections": [],
            "reasoning": "",
            "checks": {},
        }

        try:
            result["checks"]["accuracy"] = self._check_accuracy(
                git_data, markdown_content
            )
            result["checks"]["completeness"] = self._check_completeness(
                git_data, markdown_content
            )
            result["checks"]["consistency"] = self._check_consistency(
                git_data, markdown_content
            )
            result["checks"]["duplicates"] = self._check_duplicates(markdown_content)
            result["checks"]["anomalies"] = self._check_anomalies(
                git_data, markdown_content
            )

            result["reasoning"] = self._generate_llm_analysis(
                git_data, markdown_content, result["checks"]
            )

            self._compile_results(result)

            status_icon = "✓" if result["status"] == "pass" else "✗"
            print(f"  {status_icon} Fact-check complete: {result['status']}")
            if result["errors"]:
                print(f"  ✗ {len(result['errors'])} error(s) found")
            if result["warnings"]:
                print(f"  ⚠ {len(result['warnings'])} warning(s) found")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            result["status"] = "fail"
            result["errors"].append(f"Fact-checking failed: {str(e)}")
            result["reasoning"] = f"Critical error during analysis: {str(e)}"

        return result

    def _check_accuracy(self, git_data: Dict, markdown_content: str) -> Dict:
        """Check accuracy of commit counts and data."""
        check_result = {"passed": True, "issues": [], "corrections": []}

        repos = git_data.get("repos", {})

        for repo_name, repo_data in repos.items():
            expected_commits = repo_data.get("commits", 0)

            pattern = rf"`~/code/{re.escape(repo_name)}`\s*\(\s*(\d+)\s*commits?\s*\)"
            matches = re.findall(pattern, markdown_content)

            if not matches and expected_commits > 0:
                check_result["passed"] = False
                check_result["issues"].append(
                    f"Repo {repo_name}: Commit count missing from markdown"
                )
                check_result["corrections"].append(
                    f"Add commit count for {repo_name}: {expected_commits} commits"
                )

            for match in matches:
                actual_commits = int(match)
                if actual_commits != expected_commits:
                    check_result["passed"] = False
                    check_result["issues"].append(
                        f"Repo {repo_name}: Commit count mismatch (expected {expected_commits}, found {actual_commits})"
                    )
                    check_result["corrections"].append(
                        f"Update {repo_name} commit count to {expected_commits}"
                    )

        total_pattern = r"- \*\*Total:\s*(\d+)\s*commits?\*\*"
        total_match = re.search(total_pattern, markdown_content)

        if total_match:
            actual_total = int(total_match.group(1))
            expected_total = git_data.get("total_commits", 0)

            if actual_total != expected_total:
                check_result["passed"] = False
                check_result["issues"].append(
                    f"Total commits mismatch (expected {expected_total}, found {actual_total})"
                )
                check_result["corrections"].append(
                    f"Update total commit count to {expected_total}"
                )

        return check_result

    def _check_completeness(self, git_data: Dict, markdown_content: str) -> Dict:
        """Check completeness - all repos with commits are included."""
        check_result = {"passed": True, "issues": [], "corrections": []}

        repos = git_data.get("repos", {})

        for repo_name, repo_data in repos.items():
            if repo_data.get("commits", 0) > 0:
                repo_pattern = rf"##\s*{re.escape(repo_name)}"
                if not re.search(repo_pattern, markdown_content):
                    check_result["passed"] = False
                    check_result["issues"].append(
                        f"Repo {repo_name}: Missing section header"
                    )
                    check_result["corrections"].append(
                        f"Add section for {repo_name} with {repo_data['commits']} commits"
                    )

        return check_result

    def _check_consistency(self, git_data: Dict, markdown_content: str) -> Dict:
        """Check consistency of LOC, timestamps, and data."""
        check_result = {"passed": True, "issues": [], "corrections": []}

        loc_added = git_data.get("total_loc_added", 0)
        loc_deleted = git_data.get("total_loc_deleted", 0)
        total_loc = loc_added + loc_deleted

        loc_pattern = r"(?:LOC|lines|lines of code)[:\s]*(\d+(?:,\d+)*)"
        loc_matches = re.findall(loc_pattern, markdown_content, re.IGNORECASE)

        for match in loc_matches:
            found_loc = int(match.replace(",", ""))
            if abs(found_loc - total_loc) > total_loc * 0.2:
                check_result["passed"] = False
                check_result["issues"].append(
                    f"LOC inconsistency: Expected ~{total_loc:,}, found {found_loc:,}"
                )

        date_pattern = r"(\d{4}-\d{2}-\d{2})"
        dates_in_markdown = set(re.findall(date_pattern, markdown_content))

        expected_date = git_data.get("date", "")
        if expected_date and expected_date not in dates_in_markdown:
            check_result["passed"] = False
            check_result["issues"].append(f"Date {expected_date} not found in markdown")

        return check_result

    def _check_duplicates(self, markdown_content: str) -> Dict:
        """Check for duplicate sections, entries, or commits."""
        check_result = {"passed": True, "issues": [], "corrections": []}

        lines = markdown_content.split("\n")
        section_headers = []
        commit_messages = []

        for line in lines:
            if line.startswith("## "):
                header = line.strip()
                if header in section_headers:
                    check_result["passed"] = False
                    check_result["issues"].append(f"Duplicate section header: {header}")
                    check_result["corrections"].append(
                        f"Remove duplicate section: {header}"
                    )
                section_headers.append(header)

            commit_match = re.match(
                r"^\s*-\s*(feat|fix|refactor|chore|docs|style|test|perf):\s*(.+)", line
            )
            if commit_match:
                commit_text = commit_match.group(2).strip()
                if commit_text in commit_messages:
                    check_result["passed"] = False
                    check_result["issues"].append(f"Duplicate commit: {commit_text}")
                    check_result["corrections"].append(
                        f"Remove duplicate commit entry: {commit_text}"
                    )
                commit_messages.append(commit_text)

        return check_result

    def _check_anomalies(self, git_data: Dict, markdown_content: str) -> Dict:
        """Check for anomalies in data or formatting."""
        check_result = {"passed": True, "issues": [], "corrections": []}

        repos = git_data.get("repos", {})

        for repo_name, repo_data in repos.items():
            commits = repo_data.get("commits", 0)
            loc_added = repo_data.get("loc_added", 0)

            if commits > 0 and loc_added == 0:
                check_result["issues"].append(
                    f"Repo {repo_name}: Has {commits} commits but 0 LOC added - may be deletions only"
                )

            if loc_added > 0 and loc_added / commits < 5:
                check_result["issues"].append(
                    f"Repo {repo_name}: Very low LOC/commit ratio ({loc_added}/{commits} = {loc_added / commits:.1f})"
                )

        section_pattern = r"##\s+(.+?)(?:\n|$)"
        sections = re.findall(section_pattern, markdown_content)

        if len(sections) > 20:
            check_result["issues"].append(f"Unusually many sections: {len(sections)}")

        empty_lines_count = markdown_content.count("\n\n")
        total_lines = len(markdown_content.split("\n"))
        if empty_lines_count / total_lines > 0.3:
            check_result["issues"].append("Excessive blank lines detected")

        return check_result

    def _generate_llm_analysis(
        self, git_data: Dict, markdown_content: str, checks: Dict
    ) -> str:
        """Use OpenCode LLM to provide intelligent analysis and reasoning."""
        prompt = f"""You are a fact-checking expert analyzing a journal entry for development work.

Git Analysis Data:
{json.dumps(git_data, indent=2)}

Generated Markdown Content:
{markdown_content[:3000]}

Automated Checks Results:
{json.dumps(checks, indent=2)}

Provide a comprehensive analysis that includes:

1. **Overall Assessment**: Is the journal entry accurate, complete, and consistent? Rate as EXCELLENT, GOOD, NEEDS IMPROVEMENT, or FAILED.

2. **Specific Issues Found**: For each failed check, explain what's wrong and why it matters.

3. **Data Integrity**: Verify that:
   - All repositories with commits are mentioned
   - Commit counts match the git data
   - LOC numbers are consistent
   - No duplicate entries exist

4. **Quality Assessment**: 
   - Are commit messages accurately represented?
   - Is the scale of work (intensity) reflected appropriately?
   - Are sections properly organized?

5. **Recommendations**: What corrections are needed, if any?

Format your response as a concise analysis paragraph (200-300 words) that a human can review.

Respond ONLY with the analysis paragraph, no additional commentary or formatting."""

        try:
            response = self.client.chat(
                message=prompt,
                model=self.config["opencode"]["model"],
                provider=self.config["opencode"]["provider"],
            )
            return response.get("content", "").strip()
        except Exception as e:
            return f"LLM analysis failed: {str(e)}"

    def _compile_results(self, result: Dict) -> None:
        """Compile all check results into final output."""
        checks = result.get("checks", {})

        for check_name, check_result in checks.items():
            result["errors"].extend(
                [f"[{check_name}] {issue}" for issue in check_result.get("issues", [])]
            )
            result["warnings"].extend(
                [
                    f"[{check_name}] {issue}"
                    for issue in check_result.get("warnings", [])
                    if "warnings" in check_result
                ]
            )
            result["corrections"].extend(check_result.get("corrections", []))

        if result["errors"]:
            result["status"] = "fail"
        elif result["warnings"] or any(
            not c.get("passed", True) for c in checks.values()
        ):
            result["status"] = "pass_with_warnings"
        else:
            result["status"] = "pass"


if __name__ == "__main__":
    agent = FactCheckingAgent()

    sample_git_data = {
        "date": "2025-12-31",
        "is_work_day": True,
        "total_commits": 174,
        "total_loc_added": 4000,
        "total_loc_deleted": 800,
        "estimated_hours": 12.5,
        "repos": {
            "comic-pile": {
                "commits": 43,
                "loc_added": 1200,
                "loc_deleted": 200,
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

    sample_markdown = """## 2025-12-31 (12.5 hours, 4800 LOC)

## Summary
Worked on comic-pile and other projects.

## Repositories Worked On
- `~/code/comic-pile` (43 commits)
- **Total: 43 commits**

## comic-pile
**Staleness Awareness**
- Feat: Add Staleness Awareness UI
- Fix: Update cache logic
"""

    result = agent.check_entry(sample_git_data, sample_markdown)
    print(json.dumps(result, indent=2))
