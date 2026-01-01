"""Tests for utils/cache.py."""

import json
from unittest.mock import MagicMock, patch

import pytest

from utils.cache import (
    ensure_cache_dir,
    get_project_description,
    load_projects_cache,
    save_projects_cache,
    update_project_cache,
)


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Provide a mock cache directory."""
    return tmp_path / "cache" / "projects.json"


class TestEnsureCacheDir:
    """Tests for ensure_cache_dir()."""

    def test_creates_cache_dir(self):
        """Test that cache directory is created."""
        with patch("utils.cache.CACHE_DIR") as mock_dir:
            mock_dir.mkdir = MagicMock()
            ensure_cache_dir()
            mock_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestLoadProjectsCache:
    """Tests for load_projects_cache()."""

    @patch("utils.cache.PROJECTS_CACHE_FILE")
    def test_loads_from_file(self, mock_file, tmp_path):
        """Test loading projects from existing cache file."""
        cache_file = tmp_path / "projects.json"
        cache_file.write_text('{"project1": "Description 1", "project2": "Description 2"}')
        mock_file.exists.return_value = True
        mock_file.__str__ = lambda x: str(cache_file)

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                '{"project1": "Description 1", "project2": "Description 2"}'
            )
            result = load_projects_cache()
            assert result == {
                "project1": "Description 1",
                "project2": "Description 2",
            }

    @patch("utils.cache.PROJECTS_CACHE_FILE")
    def test_missing_file_returns_empty_dict(self, mock_file):
        """Test that missing cache file returns empty dict."""
        mock_file.exists.return_value = False
        result = load_projects_cache()
        assert result == {}

    @patch("utils.cache.PROJECTS_CACHE_FILE")
    def test_json_decode_error_returns_empty_dict(self, mock_file):
        """Test that JSON decode error returns empty dict."""
        mock_file.exists.return_value = True
        with patch("builtins.open", create=True) as mock_open:
            mock_open.side_effect = json.JSONDecodeError("test", "test", 0)
            result = load_projects_cache()
            assert result == {}


class TestSaveProjectsCache:
    """Tests for save_projects_cache()."""

    @patch("utils.cache.ensure_cache_dir")
    @patch("utils.cache.PROJECTS_CACHE_FILE")
    def test_saves_to_json(self, mock_file, mock_ensure):
        """Test saving projects to cache file."""
        projects = {"project1": "Description 1", "project2": "Description 2"}

        with patch("builtins.open", create=True) as mock_open:
            mock_file_handler = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file_handler

            save_projects_cache(projects)

            mock_ensure.assert_called_once()
            mock_open.assert_called_once_with(mock_file, "w", encoding="utf-8")


class TestUpdateProjectCache:
    """Tests for update_project_cache()."""

    @patch("utils.cache.load_projects_cache")
    @patch("utils.cache.save_projects_cache")
    def test_updates_single_project(self, mock_save, mock_load):
        """Test updating a single project in cache."""
        mock_load.return_value = {"project1": "Description 1"}

        update_project_cache("project2", "New Description")

        mock_load.assert_called_once()
        mock_save.assert_called_once_with(
            {"project1": "Description 1", "project2": "New Description"}
        )


class TestGetProjectDescription:
    """Tests for get_project_description()."""

    @patch("utils.cache.load_projects_cache")
    def test_retrieves_existing_project(self, mock_load):
        """Test retrieving description for existing project."""
        mock_load.return_value = {
            "project1": "Description 1",
            "project2": "Description 2",
        }

        result = get_project_description("project1")
        assert result == "Description 1"

    @patch("utils.cache.load_projects_cache")
    def test_missing_project_returns_none(self, mock_load):
        """Test that missing project returns None."""
        mock_load.return_value = {"project1": "Description 1"}

        result = get_project_description("nonexistent")
        assert result is None
