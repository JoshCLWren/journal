#!/usr/bin/env python3
"""OpenCode utility functions for journal automation."""

import subprocess
import sys
from pathlib import Path

OPENCODE_DEFAULT_URL = "http://127.0.0.1:4096"


def is_opencode_running(url: str = OPENCODE_DEFAULT_URL) -> bool:
    """Check if OpenCode server is running."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"{url}/global/health"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_opencode_server() -> bool:
    """Start OpenCode server in background."""
    try:
        # Check if opencode command exists
        result = subprocess.run(
            ["which", "opencode"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(
                "❌ OpenCode command not found. Install with: curl -sSL https://opencode.ai/install.sh | sh"
            )
            return False

        # Start opencode server in background
        subprocess.Popen(
            ["opencode", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for it to start
        import time

        for i in range(10):
            if is_opencode_running():
                print("✓ OpenCode server started")
                return True
            time.sleep(0.5)

        print("❌ OpenCode server failed to start")
        return False
    except Exception as e:
        print(f"❌ Failed to start OpenCode: {e}")
        return False


def ensure_opencode_running(url: str = OPENCODE_DEFAULT_URL) -> bool:
    """Ensure OpenCode server is running, starting if needed."""
    if is_opencode_running(url):
        print("✓ OpenCode server already running")
        return True

    print("⏳ Starting OpenCode server...")
    return start_opencode_server()


def get_opencode_client_path() -> Path:
    """Get path to OpenCode client."""
    return Path(__file__).parent.parent / "opencode_client.py"


def check_opencode_client() -> bool:
    """Check if OpenCode client file exists."""
    client_path = get_opencode_client_path()
    if not client_path.exists():
        print(f"❌ OpenCode client not found at {client_path}")
        return False
    return True
