"""Tests for opencode_client.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from opencode_client import OpenCodeClient


@pytest.fixture
def mock_response():
    """Mock requests.Response object."""
    response = MagicMock()
    response.headers = {"Content-Type": "application/json"}
    return response


class TestOpenCodeClientInit:
    """Test OpenCodeClient initialization."""

    def test_init_default_url(self):
        """Test initialization with default URL."""
        client = OpenCodeClient()
        assert client.base_url == "http://127.0.0.1:4096"
        assert client.session_id is None

    def test_init_custom_url(self):
        """Test initialization with custom URL."""
        client = OpenCodeClient(base_url="http://example.com:8080")
        assert client.base_url == "http://example.com:8080"
        assert client.session_id is None


class TestOpenCodeClientHealth:
    """Test OpenCodeClient.health method."""

    @patch("opencode_client.requests.get")
    def test_health_success(self, mock_get):
        """Test health check success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"healthy": True, "version": "1.0.0"}
        mock_get.return_value = mock_response

        client = OpenCodeClient()
        result = client.health()

        assert result["healthy"] is True
        assert result["version"] == "1.0.0"
        mock_get.assert_called_once_with("http://127.0.0.1:4096/global/health")

    @patch("opencode_client.requests.get")
    def test_health_custom_url(self, mock_get):
        """Test health check with custom URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"healthy": True}
        mock_get.return_value = mock_response

        client = OpenCodeClient(base_url="http://example.com:8080")
        client.health()

        mock_get.assert_called_once_with("http://example.com:8080/global/health")

    @patch("opencode_client.requests.get")
    def test_health_connection_error(self, mock_get):
        """Test health check with connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        client = OpenCodeClient()

        with pytest.raises(requests.exceptions.ConnectionError):
            client.health()

    @patch("opencode_client.requests.get")
    def test_health_http_error(self, mock_get):
        """Test health check with HTTP error."""
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        client = OpenCodeClient()

        with pytest.raises(requests.exceptions.HTTPError):
            client.health()


class TestOpenCodeClientCreateSession:
    """Test OpenCodeClient.create_session method."""

    @patch("opencode_client.requests.post")
    def test_create_session_success(self, mock_post):
        """Test session creation success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "session-123"}
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        session_id = client.create_session()

        assert session_id == "session-123"
        assert client.session_id == "session-123"
        mock_post.assert_called_once_with("http://127.0.0.1:4096/session", json={})

    @patch("opencode_client.requests.post")
    def test_create_session_custom_url(self, mock_post):
        """Test session creation with custom URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "session-456"}
        mock_post.return_value = mock_response

        client = OpenCodeClient(base_url="http://example.com:8080")
        client.create_session()

        mock_post.assert_called_once_with("http://example.com:8080/session", json={})

    @patch("opencode_client.requests.post")
    def test_create_session_error(self, mock_post):
        """Test session creation with error."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        client = OpenCodeClient()

        with pytest.raises(requests.exceptions.ConnectionError):
            client.create_session()


class TestOpenCodeClientChat:
    """Test OpenCodeClient.chat method."""

    @patch("opencode_client.requests.post")
    def test_chat_success(self, mock_post):
        """Test chat with successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "Hello"}]}',
            b'{"parts": [{"type": "text", "text": " world"}]}',
            b'{"finish": "stop"}',
        ]
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"
        result = client.chat("Hello, world!")

        assert result["content"] == "Hello world"
        assert result["data"]["finish"] == "stop"

    @patch("opencode_client.requests.post")
    def test_chat_creates_session(self, mock_post):
        """Test chat creates session if not exists."""
        mock_session_response = MagicMock()
        mock_session_response.status_code = 200
        mock_session_response.json.return_value = {"id": "new-session"}

        mock_chat_response = MagicMock()
        mock_chat_response.status_code = 200
        mock_chat_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "Response"}]}',
            b'{"finish": "stop"}',
        ]

        mock_post.side_effect = [mock_session_response, mock_chat_response]

        client = OpenCodeClient()
        result = client.chat("Test message")

        assert client.session_id == "new-session"
        assert result["content"] == "Response"
        assert mock_post.call_count == 2

    @patch("opencode_client.requests.post")
    def test_chat_with_custom_model(self, mock_post):
        """Test chat with custom model and provider."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "AI response"}]}',
            b'{"finish": "stop"}',
        ]
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"
        result = client.chat("Test message", model="gpt-4", provider="openai")

        assert result["content"] == "AI response"
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["model"]["providerID"] == "openai"
        assert payload["model"]["modelID"] == "gpt-4"

    @patch("opencode_client.requests.post")
    def test_chat_connection_error(self, mock_post):
        """Test chat with connection error."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        client = OpenCodeClient()
        client.session_id = "test-session"

        with pytest.raises(requests.exceptions.ConnectionError):
            client.chat("Test message")

    @patch("opencode_client.requests.post")
    def test_chat_empty_response(self, mock_post):
        """Test chat with empty response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = []
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"
        result = client.chat("Test message")

        assert result["content"] == ""
        assert result["data"] == {}

    @patch("opencode_client.requests.post")
    def test_chat_malformed_json(self, mock_post):
        """Test chat with malformed JSON in response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "Valid"}]}',
            b"invalid json",
            b'{"finish": "stop"}',
        ]
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"

        with pytest.raises(json.JSONDecodeError):
            client.chat("Test message")


class TestOpenCodeClientChatStream:
    """Test OpenCodeClient.chat_stream method."""

    @patch("opencode_client.requests.post")
    def test_chat_stream_success(self, mock_post):
        """Test chat_stream with successful streaming."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "Hello"}]}',
            b'{"parts": [{"type": "text", "text": " world"}]}',
            b'{"parts": [{"type": "text", "text": "!"}]}',
        ]
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"

        chunks = list(client.chat_stream("Stream test"))
        assert chunks == ["Hello", " world", "!"]

    @patch("opencode_client.requests.post")
    def test_chat_stream_creates_session(self, mock_post):
        """Test chat_stream creates session if not exists."""
        mock_session_response = MagicMock()
        mock_session_response.status_code = 200
        mock_session_response.json.return_value = {"id": "new-session"}

        mock_stream_response = MagicMock()
        mock_stream_response.status_code = 200
        mock_stream_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "Streamed"}]}',
        ]

        mock_post.side_effect = [mock_session_response, mock_stream_response]

        client = OpenCodeClient()

        chunks = list(client.chat_stream("Test"))
        assert chunks == ["Streamed"]
        assert client.session_id == "new-session"

    @patch("opencode_client.requests.post")
    def test_chat_stream_with_custom_model(self, mock_post):
        """Test chat_stream with custom model and provider."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "AI"}]}',
        ]
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"

        chunks = list(client.chat_stream("Test", model="claude-3", provider="anthropic"))
        assert chunks == ["AI"]

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["model"]["providerID"] == "anthropic"
        assert payload["model"]["modelID"] == "claude-3"

    @patch("opencode_client.requests.post")
    def test_chat_stream_empty_lines(self, mock_post):
        """Test chat_stream handles empty lines."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "Start"}]}',
            b"",
            b'{"parts": [{"type": "text", "text": "End"}]}',
        ]
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"

        chunks = list(client.chat_stream("Test"))
        assert chunks == ["Start", "End"]

    @patch("opencode_client.requests.post")
    def test_chat_stream_non_text_parts(self, mock_post):
        """Test chat_stream ignores non-text parts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"parts": [{"type": "image", "data": "..."}]}',
            b'{"parts": [{"type": "text", "text": "Text only"}]}',
        ]
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"

        chunks = list(client.chat_stream("Test"))
        assert chunks == ["Text only"]

    @patch("opencode_client.requests.post")
    def test_chat_stream_connection_error(self, mock_post):
        """Test chat_stream with connection error."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Failed")

        client = OpenCodeClient()
        client.session_id = "test-session"

        with pytest.raises(requests.exceptions.ConnectionError):
            list(client.chat_stream("Test"))

    @patch("opencode_client.requests.post")
    def test_chat_stream_malformed_json(self, mock_post):
        """Test chat_stream with malformed JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "Valid"}]}',
            b"invalid json",
        ]
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"

        with pytest.raises(json.JSONDecodeError):
            list(client.chat_stream("Test"))

    @patch("opencode_client.requests.post")
    def test_chat_stream_iterator(self, mock_post):
        """Test chat_stream is a proper iterator."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"parts": [{"type": "text", "text": "Chunk1"}]}',
            b'{"parts": [{"type": "text", "text": "Chunk2"}]}',
        ]
        mock_post.return_value = mock_response

        client = OpenCodeClient()
        client.session_id = "test-session"

        stream = client.chat_stream("Test")
        assert hasattr(stream, "__iter__")
        assert hasattr(stream, "__next__")

        first = next(stream)
        assert first == "Chunk1"

        second = next(stream)
        assert second == "Chunk2"
