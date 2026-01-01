"""Test configuration management."""

from pathlib import Path
import tempfile
import json


def test_default_config_structure():
    """Test that default config has all required sections."""
    from config import DEFAULT_CONFIG

    assert "general" in DEFAULT_CONFIG
    assert "scheduling" in DEFAULT_CONFIG
    assert "git" in DEFAULT_CONFIG
    assert "opencode" in DEFAULT_CONFIG
    assert "quality" in DEFAULT_CONFIG


def test_config_save_and_load():
    """Test that config can be saved and loaded correctly."""
    from config import load_config, save_config

    # Create a test config
    test_config = {
        "general": {
            "author_name": "Test User",
            "author_email": "test@example.com",
        }
    }

    # Save to a temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = Path(f.name)
        json.dump(test_config, f)

    # Load and verify
    with open(temp_path, "r") as f:
        loaded = json.load(f)

    assert loaded == test_config
    temp_path.unlink()


def test_get_config():
    """Test that get_config returns a valid configuration."""
    from config import get_config

    config = get_config()
    assert isinstance(config, dict)
    assert "general" in config
    assert "author_name" in config["general"]
