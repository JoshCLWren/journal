"""Test cache management utilities."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from utils.cache import (
    ensure_cache_dir,
    get_project_description,
    load_projects_cache,
    save_projects_cache,
    update_project_cache,
)


@pytest.fixture
def temp_cache_dir():
    """Provide a temporary cache directory."""
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir)
        yield cache_path


def test_ensure_cache_dir(temp_cache_dir):
    """Test that cache directory is created."""
    cache_dir = temp_cache_dir / "cache"

    with patch("utils.cache.CACHE_DIR", cache_dir):
        ensure_cache_dir()

    assert cache_dir.exists()
    assert cache_dir.is_dir()


def test_load_projects_cache_empty(temp_cache_dir):
    """Test loading projects cache when file doesn't exist."""
    cache_file = temp_cache_dir / "projects.json"

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        cache = load_projects_cache()

    assert cache == {}


def test_save_and_load_projects_cache(temp_cache_dir):
    """Test saving and loading projects cache."""
    cache_file = temp_cache_dir / "projects.json"

    projects = {
        "test-repo": "Test repository description",
        "another-repo": "Another project",
    }

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        save_projects_cache(projects)
        assert cache_file.exists()

        loaded = load_projects_cache()
        assert loaded == projects


def test_save_projects_cache_in_existing_dir(temp_cache_dir):
    """Test that save works in existing directory."""
    cache_file = temp_cache_dir / "projects.json"

    projects = {"test": "description"}

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        save_projects_cache(projects)

    assert cache_file.exists()


def test_update_project_cache(temp_cache_dir):
    """Test updating single project in cache."""
    cache_file = temp_cache_dir / "projects.json"

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        save_projects_cache({"existing": "Existing project"})
        update_project_cache("new-repo", "New project description")

        cache = load_projects_cache()
        assert "existing" in cache
        assert "new-repo" in cache
        assert cache["new-repo"] == "New project description"


def test_update_project_cache_existing(temp_cache_dir):
    """Test updating existing project in cache."""
    cache_file = temp_cache_dir / "projects.json"

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        save_projects_cache({"test-repo": "Old description"})
        update_project_cache("test-repo", "New description")

        cache = load_projects_cache()
        assert cache["test-repo"] == "New description"


def test_get_project_description(temp_cache_dir):
    """Test getting project description from cache."""
    cache_file = temp_cache_dir / "projects.json"

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        save_projects_cache({"test-repo": "Test description"})

        desc = get_project_description("test-repo")
        assert desc == "Test description"


def test_get_project_description_not_found(temp_cache_dir):
    """Test getting description for non-existent project."""
    cache_file = temp_cache_dir / "projects.json"

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        save_projects_cache({})

        desc = get_project_description("non-existent")
        assert desc is None


def test_load_projects_cache_invalid_json(temp_cache_dir):
    """Test loading projects cache with invalid JSON."""
    cache_file = temp_cache_dir / "projects.json"
    cache_file.write_text("invalid json")

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        cache = load_projects_cache()
        assert cache == {}


def test_load_projects_cache_read_error(temp_cache_dir):
    """Test loading projects cache with read error."""
    cache_file = temp_cache_dir / "projects.json"
    cache_file.write_bytes(b"\x00\x01\x02")

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        cache = load_projects_cache()
        assert cache == {}


def test_save_projects_cache_valid_json(temp_cache_dir):
    """Test that saved cache is valid JSON."""
    cache_file = temp_cache_dir / "projects.json"
    projects = {"test": "description"}

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        save_projects_cache(projects)

        with open(cache_file) as f:
            loaded = json.load(f)

        assert loaded == projects


def test_ensure_cache_dir_idempotent(temp_cache_dir):
    """Test that ensure_cache_dir is idempotent."""
    cache_dir = temp_cache_dir / "cache"

    with patch("utils.cache.CACHE_DIR", cache_dir):
        ensure_cache_dir()
        ensure_cache_dir()
        ensure_cache_dir()

    assert cache_dir.exists()


def test_update_multiple_projects(temp_cache_dir):
    """Test updating multiple projects sequentially."""
    cache_file = temp_cache_dir / "projects.json"

    with patch("utils.cache.PROJECTS_CACHE_FILE", cache_file):
        save_projects_cache({})

        update_project_cache("repo1", "Description 1")
        update_project_cache("repo2", "Description 2")
        update_project_cache("repo3", "Description 3")

        cache = load_projects_cache()
        assert len(cache) == 3
        assert cache["repo1"] == "Description 1"
        assert cache["repo2"] == "Description 2"
        assert cache["repo3"] == "Description 3"
