#!/usr/bin/env python3
"""Cache management for projects legend and other data."""

import json
from pathlib import Path
from typing import Dict, Optional

CACHE_DIR = Path.home() / ".local" / "share" / "journal-automation" / "cache"
PROJECTS_CACHE_FILE = CACHE_DIR / "projects.json"


def ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_projects_cache() -> Dict[str, str]:
    """Load projects legend from cache."""
    if not PROJECTS_CACHE_FILE.exists():
        return {}

    try:
        with open(PROJECTS_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_projects_cache(projects: Dict[str, str]) -> None:
    """Save projects legend to cache."""
    ensure_cache_dir()
    with open(PROJECTS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)


def update_project_cache(repo_name: str, description: str) -> None:
    """Update single project in cache."""
    projects = load_projects_cache()
    projects[repo_name] = description
    save_projects_cache(projects)


def get_project_description(repo_name: str) -> Optional[str]:
    """Get project description from cache."""
    projects = load_projects_cache()
    return projects.get(repo_name)
