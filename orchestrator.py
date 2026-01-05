#!/usr/bin/env python3
"""Orchestrator - Coordinates all agents for journal automation."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from agents.content_generation import ContentGenerationAgent
from agents.git_analysis import GitAnalysisAgent
from config import get_config
from opencode_client import OpenCodeClient
from utils.git_utils import push_to_remote, stage_and_commit
from utils.opencode_utils import ensure_opencode_running


class FactCheckingAgent:
    """Placeholder for FactCheckingAgent."""

    def __init__(self):
        """Initialize FactCheckingAgent with config and OpenCode client."""
        self.config = get_config()
        self.client = OpenCodeClient(base_url=self.config["scheduling"]["opencode_url"])

    def verify_facts(self, content: str, git_data: dict) -> dict:
        """Verify facts in generated content."""
        print("\n🔍 Fact Checking Agent: Verifying facts")

        result = {"status": "pending", "findings": []}

        try:
            prompt = f"""You are a fact checker. Review the following journal entry for factual accuracy based on the git commit data.

Git Data:
{json.dumps(git_data, indent=2)}

Generated Content:
{content}

Check for:
1. Factual inconsistencies (e.g., wrong commit counts, incorrect repo names)
2. Misrepresented commit messages
3. Inaccurate time estimates
4. Missing important commits

Respond in JSON format:
{{
  "status": "verified" or "issues_found",
  "findings": [
    {{"type": "error" | "warning", "issue": "description"}}
  ]
}}

If no issues found, return empty findings array."""

            response = self.client.chat(
                message=prompt,
                model=self.config["opencode"]["model"],
                provider=self.config["opencode"]["provider"],
            )

            content_text = response.get("content", "{}")

            try:
                fact_check_data = json.loads(content_text)
                result.update(fact_check_data)
            except json.JSONDecodeError:
                result["status"] = "error"
                result["findings"] = [
                    {"type": "error", "issue": "Failed to parse fact check response"}
                ]

            print(f"  ✓ Fact check complete: {result['status']}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            result["status"] = "failed"
            result["findings"] = [{"type": "error", "issue": str(e)}]

        return result


class QualityAssuranceAgent:
    """Placeholder for QualityAssuranceAgent."""

    def __init__(self):
        """Initialize QualityAssuranceAgent with config and OpenCode client."""
        self.config = get_config()
        self.client = OpenCodeClient(base_url=self.config["scheduling"]["opencode_url"])

    def check_quality(self, content: str, git_data: dict) -> dict:
        """Check quality of generated content."""
        print("\n✅ Quality Assurance Agent: Checking quality")

        result = {"status": "pending", "checks": {}}

        try:
            prompt = f"""You are a quality assurance reviewer. Evaluate the following journal entry.

Git Data:
{json.dumps(git_data, indent=2)}

Generated Content (first 2000 chars):
{content[:2000]}

Evaluate on:
1. Readability and clarity (score 1-10)
2. Completeness (missing sections?) (score 1-10)
3. Accuracy relative to git data (score 1-10)
4. Overall quality (score 1-10)

Respond in JSON format:
{{
  "status": "passed" or "needs_improvement",
  "checks": {{
    "readability": {{"score": 8, "notes": "notes"}},
    "completeness": {{"score": 9, "notes": "notes"}},
    "accuracy": {{"score": 10, "notes": "notes"}},
    "overall_quality": {{"score": 9, "notes": "notes"}}
  }},
  "recommendations": ["optional improvement suggestions"]
}}

Minimum passing score: 7"""

            response = self.client.chat(
                message=prompt,
                model=self.config["opencode"]["model"],
                provider=self.config["opencode"]["provider"],
            )

            content_text = response.get("content", "{}")

            try:
                qa_data = json.loads(content_text)
                result.update(qa_data)
            except json.JSONDecodeError:
                result["status"] = "error"
                result["checks"] = {
                    "overall_quality": {
                        "score": 0,
                        "notes": "Failed to parse QA response",
                    }
                }

            print(f"  ✓ QA complete: {result['status']}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            result["status"] = "failed"
            result["checks"] = {"overall_quality": {"score": 0, "notes": str(e)}}

        return result


class Orchestrator:
    """Main orchestrator that coordinates all agents."""

    def __init__(self):
        """Initialize Orchestrator with config and all sub-agents."""
        self.config = get_config()
        self.git_agent = GitAnalysisAgent()
        self.content_agent = ContentGenerationAgent()
        self.fact_check_agent = FactCheckingAgent()
        self.qa_agent = QualityAssuranceAgent()
        self.opencode_client = OpenCodeClient(base_url=self.config["scheduling"]["opencode_url"])
        self.journal_dir = Path(self.config["general"]["journal_directory"])

    def run_day(self, date: str) -> dict[str, Any]:
        """Run all agents for a specific day.

        Args:
            date: Date string in format YYYY-MM-DD

        Returns:
            dict: Summary of what happened
        """
        print(f"\n{'=' * 60}")
        print(f"🚀 Orchestrator: Processing {date}")
        print(f"{'=' * 60}")

        summary = {
            "date": date,
            "is_work_day": False,
            "stages": {},
            "final_status": "skipped",
            "errors": [],
        }

        try:
            print("  [DEBUG] Ensuring OpenCode is running...")
            ensure_opencode_running(self.config["scheduling"]["opencode_url"])
            print("  [DEBUG] OpenCode is running")

            summary["stages"]["git_analysis"] = self._run_git_analysis(date, summary)

            if not summary["stages"]["git_analysis"]["is_work_day"]:
                print(f"\n⏭️  No work detected for {date}")
                summary["final_status"] = "no_work"
                return summary

            summary["is_work_day"] = True

            git_data = summary["stages"]["git_analysis"]["data"]

            summary["stages"]["content_generation"] = self._run_content_generation(
                git_data, summary
            )

            if summary["stages"]["content_generation"]["status"] != "complete":
                self._handle_failure("content_generation", summary)
                return summary

            content_result = summary["stages"]["content_generation"]
            content = content_result["full_markdown"]
            entry_path = self._get_entry_path(date)

            summary["stages"]["fact_checking"] = self._run_fact_checking(content, git_data, summary)

            summary["stages"]["quality_assurance"] = self._run_quality_assurance(
                content, git_data, summary
            )

            qa_passed = self._evaluate_qa_result(summary["stages"]["quality_assurance"])

            if qa_passed:
                self._commit_final_entry(date, entry_path, summary)
                summary["final_status"] = "success"
                print(f"\n✅ Successfully processed {date}")
            else:
                summary["final_status"] = "quality_check_failed"
                error_msg = "Quality check failed - needs improvement"
                summary["errors"].append(error_msg)
                self._send_notification(f"Journal QA Failed: {error_msg}")

            return summary

        except Exception as e:
            error_msg = f"Orchestrator failed: {str(e)}"
            summary["final_status"] = "error"
            summary["errors"].append(error_msg)
            self._send_notification(error_msg)
            return summary

    def _run_git_analysis(self, date: str, summary: dict) -> dict:
        """Run GitAnalysisAgent and commit results."""
        result = {"status": "pending", "is_work_day": False, "data": None}

        for attempt in range(self.config["opencode"]["max_retries"]):
            try:
                git_data = self.git_agent.analyze_day(date)
                result["data"] = git_data
                result["is_work_day"] = git_data["is_work_day"]
                result["status"] = "complete"

                data_file = self.journal_dir / "tmp" / f"{date}_git_data.json"
                data_file.parent.mkdir(parents=True, exist_ok=True)
                data_file.write_text(json.dumps(git_data, indent=2))

                if self.config["quality"]["commit_as_they_go"]:
                    stage_and_commit(self.journal_dir, data_file, f"git-analysis: Data for {date}")
                    print("  ✓ Committed git_data.json")

                return result

            except Exception as e:
                print(f"  ⚠️  Git analysis attempt {attempt + 1} failed: {e}")
                if attempt == self.config["opencode"]["max_retries"] - 1:
                    decision = self._get_opencode_decision(
                        f"Git analysis failed after {attempt + 1} attempts: {str(e)}. What should we do?",
                        ["retry", "abort", "skip_day"],
                    )

                    if decision == "retry":
                        continue
                    elif decision == "skip_day":
                        result["status"] = "skipped"
                        return result
                    else:
                        result["status"] = "failed"
                        result["error"] = str(e)
                        summary["errors"].append(str(e))
                        return result

        result["status"] = "failed"
        result["error"] = "Max retries exceeded"
        summary["errors"].append(result["error"])
        return result

    def _run_content_generation(self, git_data: dict, summary: dict) -> dict:
        """Run ContentGenerationAgent and commit results."""
        result = {"status": "pending", "full_markdown": ""}

        for attempt in range(self.config["opencode"]["max_retries"]):
            try:
                content_result = self.content_agent.generate_entry(git_data)
                result.update(content_result)

                if result["status"] == "complete":
                    entry_path = self._get_entry_path(git_data["date"])
                    entry_path.parent.mkdir(parents=True, exist_ok=True)
                    entry_path.write_text(result["full_markdown"])

                    if self.config["quality"]["commit_as_they_go"]:
                        stage_and_commit(
                            self.journal_dir,
                            entry_path,
                            f"draft: Journal entry for {git_data['date']}",
                        )
                        print("  ✓ Committed content.md")

                return result

            except Exception as e:
                print(f"  ⚠️  Content generation attempt {attempt + 1} failed: {e}")
                if attempt == self.config["opencode"]["max_retries"] - 1:
                    decision = self._get_opencode_decision(
                        f"Content generation failed after {attempt + 1} attempts: {str(e)}. What should we do?",
                        ["retry", "abort", "use_fallback"],
                    )

                    if decision == "retry":
                        continue
                    elif decision == "use_fallback":
                        result["status"] = "fallback"
                        result["full_markdown"] = self._generate_fallback_content(git_data)
                        return result
                    else:
                        result["status"] = "failed"
                        result["error"] = str(e)
                        summary["errors"].append(str(e))
                        return result

        result["status"] = "failed"
        result["error"] = "Max retries exceeded"
        summary["errors"].append(result["error"])
        return result

    def _run_parallel_checks(self, content: str, git_data: dict, summary: dict) -> tuple:
        """Run fact checking and QA in parallel using threading."""
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as executor:
            fact_check_future = executor.submit(
                self.fact_check_agent.verify_facts, content, git_data
            )
            qa_future = executor.submit(self.qa_agent.check_quality, content, git_data)

            return fact_check_future.result(), qa_future.result()

    def _run_fact_checking(self, content: str, git_data: dict, summary: dict) -> dict:
        """Run FactCheckingAgent."""
        if not self.config["quality"]["parallel_agents"]:
            return self.fact_check_agent.verify_facts(content, git_data)

        result = {"status": "pending"}

        try:
            fact_check_result, _ = self._run_parallel_checks(content, git_data, summary)
            result.update(fact_check_result)
            return result
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            return result

    def _run_quality_assurance(self, content: str, git_data: dict, summary: dict) -> dict:
        """Run QualityAssuranceAgent."""
        if not self.config["quality"]["parallel_agents"]:
            return self.qa_agent.check_quality(content, git_data)

        result = {"status": "pending"}

        try:
            _, qa_result = self._run_parallel_checks(content, git_data, summary)
            result.update(qa_result)
            return result
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            return result

    def _evaluate_qa_result(self, qa_result: dict) -> bool:
        """Evaluate QA result and decide if content passes."""
        if qa_result["status"] == "failed":
            return False

        checks = qa_result.get("checks", {})
        overall_quality = checks.get("overall_quality", {}).get("score", 0)

        if overall_quality >= 7:
            return True

        return (
            self._get_opencode_decision(
                f"QA score is {overall_quality}/10. Should we accept this entry?",
                ["accept", "reject", "retry"],
            )
            == "accept"
        )

    def _commit_final_entry(self, date: str, entry_path: Path, summary: dict):
        """Commit final journal entry."""
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            commit_message = f"journal: Add entry for {date_obj.strftime('%B %d, %Y')}"

            success = stage_and_commit(self.journal_dir, entry_path, commit_message)

            if success:
                summary["commit_hash"] = "committed"
                print("  ✓ Final entry committed")

                # Push to remote if configured
                if self.config["scheduling"].get("auto_push", False):
                    push_success = push_to_remote(self.journal_dir)
                    if push_success:
                        print("  ✓ Pushed to remote")
                    else:
                        print("  ⚠️  Failed to push to remote")
            else:
                print("  ⚠️  Failed to commit final entry")

        except Exception as e:
            print(f"  ⚠️  Commit error: {e}")
            summary["errors"].append(f"Commit error: {str(e)}")

    def _get_entry_path(self, date: str) -> Path:
        """Get path for journal entry."""
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        return self.journal_dir / date_obj.strftime("%Y/%m/%d.md")

    def _get_opencode_decision(self, situation: str, options: list[str]) -> str:
        """Get decision from OpenCode LLM.

        Args:
            situation: Description of the situation
            options: List of valid options

        Returns:
            Selected option or fallback to first option
        """
        try:
            prompt = f"""You are an orchestrator for a journal automation system.

Situation: {situation}

Available options: {", ".join(options)}

Choose the best option. Respond ONLY with the option name, no additional commentary."""

            response = self.opencode_client.chat(
                message=prompt,
                model=self.config["opencode"]["model"],
                provider=self.config["opencode"]["provider"],
            )

            decision = response.get("content", "").strip().lower()

            if decision in options:
                return decision

            print(f"⚠️  Invalid decision '{decision}', using default: {options[0]}")
            return options[0]

        except Exception as e:
            print(f"⚠️  Failed to get OpenCode decision: {e}, using default: {options[0]}")
            return options[0]

    def _generate_fallback_content(self, git_data: dict) -> str:
        """Generate fallback content when generation fails."""
        lines = [
            f"# {git_data['date']}",
            "",
            f"**Hours:** ~{git_data['estimated_hours']:.1f}",
            f"**Lines Changed:** +{git_data['total_loc_added']:,}/-{git_data['total_loc_deleted']:,}",
            "",
            "## Summary",
            f"Automated generation failed. {git_data['total_commits']} commits across {len(git_data['repos'])} repos.",
            "",
            "## Repositories",
        ]

        for repo_name, repo_data in git_data["repos"].items():
            lines.append(f"- `{repo_name}` ({repo_data['commits']} commits)")

        lines.append("")
        lines.append("## Commits")

        for repo_name, repo_data in git_data["repos"].items():
            lines.append(f"\n### {repo_name}")
            for msg in repo_data["commit_messages"][:5]:
                lines.append(f"- {msg}")

        return "\n".join(lines)

    def _handle_failure(self, stage: str, summary: dict):
        """Handle agent failure."""
        error_msg = f"{stage} failed"
        summary["errors"].append(error_msg)
        self._send_notification(f"Journal {stage} Failed")

    def _send_notification(self, message: str):
        """Send desktop notification on failure."""
        try:
            import subprocess

            subprocess.run(
                ["notify-send", "Journal Automation Error", message],
                check=False,
                capture_output=True,
            )
            print(f"🔔 Sent notification: {message}")
        except FileNotFoundError:
            print("⚠️  notify-send not available, skipping notification")
        except Exception as e:
            print(f"⚠️  Failed to send notification: {e}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Journal Automation Orchestrator")
    parser.add_argument(
        "date",
        nargs="?",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date to process (YYYY-MM-DD, default: today)",
    )

    args = parser.parse_args()

    orchestrator = Orchestrator()
    summary = orchestrator.run_day(args.date)

    print(f"\n{'=' * 60}")
    print(f"Summary for {args.date}:")
    print(f"{'=' * 60}")
    print(f"Status: {summary['final_status']}")
    print(f"Is work day: {summary['is_work_day']}")
    print(f"Errors: {len(summary['errors'])}")

    if summary["errors"]:
        print("\nErrors:")
        for error in summary["errors"]:
            print(f"  - {error}")

    sys.exit(0 if summary["final_status"] in ["success", "no_work", "skipped"] else 1)


if __name__ == "__main__":
    main()
