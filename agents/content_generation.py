#!/usr/bin/env python3
"""Content Generation Agent - Creates Markdown journal entries using OpenCode."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from opencode_client import OpenCodeClient


class ContentGenerationAgent:
    """Generates journal entry content using OpenCode LLM."""

    def __init__(self):
        """Initialize ContentGenerationAgent with config and OpenCode client."""
        self.config = get_config()
        self.client = OpenCodeClient(base_url=self.config["scheduling"]["opencode_url"])

    def generate_entry(self, git_data: dict) -> dict:
        """Generate complete journal entry from git analysis data."""
        print(f"\n✍️  Content Generation Agent: Generating entry for {git_data['date']}")

        result = {
            "header": "",
            "summary": "",
            "repositories_section": "",
            "project_sections": {},
            "activity_summary": "",
            "projects_legend": "",
            "full_markdown": "",
            "status": "pending",
        }

        try:
            # Generate header
            result["header"] = self._generate_header(git_data)

            # Generate summary section
            result["summary"] = self._generate_summary(git_data)

            # Generate repositories section
            result["repositories_section"] = self._generate_repositories_section(git_data)

            # Generate project sections
            result["project_sections"] = self._generate_project_sections(git_data)

            # Generate activity summary
            result["activity_summary"] = self._generate_activity_summary(git_data)

            # Generate projects legend
            result["projects_legend"] = self._generate_projects_legend(git_data)

            # Assemble full markdown
            result["full_markdown"] = self._assemble_full_markdown(result, git_data)

            result["status"] = "complete"
            print("  ✓ Content generation complete")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    def _generate_header(self, git_data: dict) -> str:
        """Generate journal entry header."""
        from utils.markdown_utils import format_header

        hours = git_data["estimated_hours"]
        loc = git_data["total_loc_added"] + git_data["total_loc_deleted"]

        return format_header(git_data["date"], hours, loc)

    def _generate_summary(self, git_data: dict) -> str:
        """Generate high-level summary using OpenCode."""
        if not git_data["is_work_day"]:
            return "No development activity on this date."

        prompt = f"""You are analyzing a day of development work.

Commit Data:
{json.dumps(git_data, indent=2)}

Generate a 2-3 sentence summary of the day's work that captures:
1. Primary focus areas (top repos, major features)
2. Scale of work (intensive, light, moderate) based on commit count ({git_data["total_commits"]})
3. Key accomplishments or launches

Style: Concise, professional, similar to existing journal entries.

Respond ONLY with the summary text, no additional commentary."""

        response = self.client.chat(
            message=prompt,
            model=self.config["opencode"]["model"],
            provider=self.config["opencode"]["provider"],
        )

        return response.get("content", "").strip()

    def _generate_repositories_section(self, git_data: dict) -> str:
        """Generate repositories section."""
        lines = ["## Repositories Worked On", ""]

        for repo_name, repo_data in git_data["repos"].items():
            lines.append(f"- `~/code/{repo_name}` ({repo_data['commits']} commits)")

        total = sum(r["commits"] for r in git_data["repos"].values())
        lines.append("")
        lines.append(f"- **Total: {total} commits**")
        lines.append("")

        return "\n".join(lines)

    def _generate_project_sections(self, git_data: dict) -> dict:
        """Generate sections for each project using OpenCode."""
        sections = {}

        min_commits = self.config["quality"]["min_commits_for_section"]

        for repo_name, repo_data in git_data["repos"].items():
            if repo_data["commits"] < min_commits:
                continue

            prompt = f"""You are analyzing commits for repository: {repo_name}

Commits by category:
{json.dumps(repo_data["commits_by_category"], indent=2)}

Top features (commit messages):
{json.dumps(repo_data["top_features"], indent=2)}

Create a journal section for this repository with:
1. Descriptive section header (e.g., "## {repo_name}")
2. Group commits by logical themes (not just categories)
3. Use commit prefixes (Feat, Fix, Refactor, etc.)
4. Filter out minor commits (chore, style, minor fixes)
5. Preserve original commit messages exactly

Format: Bullet list matching existing journal style.

Example format:
## Repo-Name

**Theme 1**
- Feat: specific feature
- Fix: specific bug fix

**Theme 2**
- Refactor: code improvement

Respond ONLY with the markdown section, no additional commentary."""

            response = self.client.chat(
                message=prompt,
                model=self.config["opencode"]["model"],
                provider=self.config["opencode"]["provider"],
            )

            sections[repo_name] = response.get("content", "").strip()

        return sections

    def _generate_activity_summary(
        self, git_data: dict, generated_sections: dict | None = None
    ) -> str:
        """Generate summary of activities."""
        if not git_data["is_work_day"]:
            return ""

        prompt = f"""Based on the generated journal entry content, create a "Summary of Activity" section that:

1. Recaps top accomplishments in 5-8 numbered points
2. Identifies major features launched
3. Notes significant bug fixes or refactors
4. Provides context for what was accomplished

Generated Entry So Far:
{json.dumps(generated_sections if generated_sections is not None else {}, indent=2)}

Git Data Summary:
- Total commits: {git_data["total_commits"]}
- Top repos: {", ".join(sorted(git_data["repos"].keys(), key=lambda x: git_data["repos"][x]["commits"], reverse=True)[:3])}

Style: Professional, action-oriented, matches existing journal entries.

Respond ONLY with the markdown section starting with "## Summary of Activity", no additional commentary."""

        response = self.client.chat(
            message=prompt,
            model=self.config["opencode"]["model"],
            provider=self.config["opencode"]["provider"],
        )

        return response.get("content", "").strip()

    def _generate_projects_legend(self, git_data: dict) -> str:
        """Generate projects legend section."""
        from utils.cache import load_projects_cache

        cached_projects = load_projects_cache()

        # Get descriptions for all mentioned repos
        mentioned_repos = list(git_data["repos"].keys())

        prompt = f"""Review and update these project descriptions:

{json.dumps(cached_projects, indent=2)}

Mentioned in today's journal entry: {", ".join(mentioned_repos)}

For each mentioned project:
1. Keep existing descriptions if accurate
2. Suggest updates if description seems outdated
3. Add new projects if missing

Respond with updated projects in JSON format: {{"repo_name": "description", ...}}

If no updates needed, return existing cache as-is."""

        response = self.client.chat(
            message=prompt,
            model=self.config["opencode"]["model"],
            provider=self.config["opencode"]["provider"],
        )

        content = response.get("content", "{}")

        try:
            updated_projects = json.loads(content)

            # Update cache
            from utils.cache import save_projects_cache

            save_projects_cache(updated_projects)

            # Generate markdown legend
            lines = ["---", "", "## Projects Legend", ""]

            for repo_name, description in sorted(updated_projects.items()):
                lines.append(f"### {repo_name}")
                lines.append(f"{description}")
                lines.append("")

            return "\n".join(lines)

        except json.JSONDecodeError:
            # Fallback to simple listing
            lines = ["---", "", "## Projects Legend", ""]
            for repo_name in mentioned_repos:
                desc = cached_projects.get(repo_name, "See repo README for details")
                lines.append(f"### {repo_name}")
                lines.append(desc)
                lines.append("")

            return "\n".join(lines)

    def _assemble_full_markdown(self, result: dict, git_data: dict) -> str:
        """Assemble all sections into complete markdown."""
        sections = []

        sections.append(result["header"])
        sections.append("")
        sections.append("## Summary")
        sections.append(result["summary"])
        sections.append("")
        sections.append(result["repositories_section"])

        # Add project sections
        for _repo_name, section in result["project_sections"].items():
            sections.append(section)
            sections.append("")

        # Add activity summary (needs project sections as context)
        activity_summary = self._generate_activity_summary(git_data, result["project_sections"])
        if activity_summary:
            sections.append(activity_summary)
            sections.append("")

        sections.append(result["projects_legend"])

        return "\n".join(sections)


if __name__ == "__main__":
    # Test with sample data
    agent = ContentGenerationAgent()

    sample_data = {
        "date": "2025-12-31",
        "is_work_day": True,
        "total_commits": 174,
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

    result = agent.generate_entry(sample_data)
    print(result["full_markdown"])
