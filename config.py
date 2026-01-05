#!/usr/bin/env python3
"""Configuration management for journal automation."""

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "general": {
        "author_name": "Josh Wren",
        "author_email": "joshisplutar@gmail.com",
        "code_directory": str(Path.home() / "code"),
        "journal_directory": str(Path.home() / "code" / "journal"),
        "log_file": str(
            Path.home() / ".local" / "share" / "journal-automation" / "logs" / "journal.log"
        ),
    },
    "scheduling": {
        "auto_commit": True,
        "auto_push": False,
        "time_to_check": "23:59",
        "opencode_url": "http://127.0.0.1:4096",
    },
    "git": {
        "exclude_repos": [
            "journal",
            "december-2025-work",
        ],
        "exclude_patterns": [
            "work-agent",
            "task-",
        ],
    },
    "opencode": {
        "model": "glm-4.7-free",
        "provider": "opencode",
        "max_workers": 5,
        "fallback_enabled": True,
    },
    "quality": {
        "min_commits_for_section": 3,
        "require_human_approval": False,
        "parallel_agents": True,
        "commit_as_they_go": True,
    },
}

CONFIG_PATH = Path.home() / ".journalrc"


def load_config() -> dict:
    """Load configuration from file, using defaults if missing."""
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    with open(CONFIG_PATH) as f:
        user_config = json.load(f)

    # Merge with defaults
    merged = DEFAULT_CONFIG.copy()
    for section, values in user_config.items():
        if section in merged:
            merged[section].update(values)
        else:
            merged[section] = values

    return merged


def save_config(config: dict) -> None:
    """Save configuration to file."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_config() -> dict:
    """Get current configuration."""
    return load_config()
