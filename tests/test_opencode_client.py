"""Test OpenCode Client."""

import json
from unittest.mock import Mock, patch

import pytest
import requests


@pytest.fixture
def mock_response():
    """Provide a mock HTTP response."""
    response = Mock()
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def client():
    """Create OpenCodeClient instance."""
    from opencode_client import OpenCodeClient

    return OpenCodeClient(base_url="http://127.0.0.1:4096")


def test_client_init():
    """Test client initialization."""
    from opencode_client import OpenCodeClient

    client = OpenCodeClient(base_url="http://localhost:8080")

    assert client.base_url == "http://localhost:8080"
    assert client.session_id is None


def test_health(client, mock_response):
    """Test health check."""
    mock_response.json.return_value = {"healthy": True, "version": "1.0.0"}

    with patch("requests.get", return_value=mock_response) as mock_get:
        result = client.health()

        mock_get.assert_called_once_with("http://127.0.0.1:4096/global/health")
        assert result["healthy"] is True
        assert result["version"] == "1.0.0"


def test_health_error(client, mock_response):
    """Test health check with error."""
    mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(requests.HTTPError):
            client.health()


def test_create_session(client, mock_response):
    """Test session creation."""
    mock_response.json.return_value = {"id": "session-123"}

    with patch("requests.post", return_value=mock_response) as mock_post:
        session_id = client.create_session()

        assert session_id == "session-123"
        assert client.session_id == "session-123"
        mock_post.assert_called_once_with("http://127.0.0.1:4096/session", json={})


def test_create_session_error(client, mock_response):
    """Test session creation with error."""
    mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(requests.HTTPError):
            client.create_session()


def test_chat_with_existing_session(client, mock_response):
    """Test chat with existing session."""
    client.session_id = "existing-session"

    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Hello "}]',
        b'{"parts": [{"type": "text", "text": "world"}]}',
        b'{"finish": "stop"}',
    ]

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = client.chat("Say hello", model="test-model", provider="test-provider")

        assert result["content"] == "Hello world"
        assert result["data"]["finish"] == "stop"

        # Check POST was called correctly
        call_args = mock_post.call_args
        assert "existing-session" in call_args[0][0]


def test_chat_creates_session(client, mock_response):
    """Test chat creates session if none exists."""
    # First call: create session
    session_response = Mock()
    session_response.json.return_value = {"id": "new-session"}

    # Second call: chat
    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Response"}]}',
        b'{"finish": "stop"}',
    ]

    with patch("requests.post", side_effect=[session_response, mock_response]):
        result = client.chat("Test message")

        assert client.session_id == "new-session"
        assert result["content"] == "Response"


def test_chat_default_parameters(client, mock_response):
    """Test chat with default parameters."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Response"}]}',
        b'{"finish": "stop"}',
    ]

    with patch("requests.post", return_value=mock_response) as mock_post:
        client.chat("Test")

        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert payload["model"]["providerID"] == "opencode"
        assert payload["model"]["modelID"] == "glm-4.7-free"
        assert payload["parts"][0]["text"] == "Test"


def test_chat_stream(client, mock_response):
    """Test chat streaming."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Hello "}]',
        b'{"parts": [{"type": "text", "text": "world"}]}',
    ]

    with patch("requests.post", return_value=mock_response):
        chunks = list(client.chat_stream("Test message"))

        assert len(chunks) == 2
        assert chunks[0] == "Hello "
        assert chunks[1] == "world"


def test_chat_stream_no_session(client, mock_response):
    """Test chat streaming creates session if needed."""
    session_response = Mock()
    session_response.json.return_value = {"id": "new-session"}

    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Chunk"}]}',
    ]

    with patch("requests.post", side_effect=[session_response, mock_response]):
        chunks = list(client.chat_stream("Test"))

        assert client.session_id == "new-session"
        assert len(chunks) == 1


def test_chat_empty_response(client, mock_response):
    """Test chat with empty response."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [b'{"finish": "stop"}']

    with patch("requests.post", return_value=mock_response):
        result = client.chat("Test")

        assert result["content"] == ""


def test_chat_multipart_response(client, mock_response):
    """Test chat with multiple parts in response."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Part 1"}, {"type": "text", "text": " Part 2"}]}',
        b'{"finish": "stop"}',
    ]

    with patch("requests.post", return_value=mock_response):
        result = client.chat("Test")

        assert result["content"] == "Part 1 Part 2"


def test_chat_non_text_part(client, mock_response):
    """Test chat with non-text parts (should be ignored)."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "other", "data": "ignored"}, {"type": "text", "text": "Text"}]}',
        b'{"finish": "stop"}',
    ]

    with patch("requests.post", return_value=mock_response):
        result = client.chat("Test")

        assert result["content"] == "Text"


def test_chat_connection_error(client, mock_response):
    """Test chat with connection error."""
    client.session_id = "test-session"
    mock_response.raise_for_status.side_effect = requests.ConnectionError("Connection failed")

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(requests.ConnectionError):
            client.chat("Test")


def test_chat_timeout(client, mock_response):
    """Test chat with timeout."""
    client.session_id = "test-session"
    mock_response.raise_for_status.side_effect = requests.Timeout("Request timed out")

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(requests.Timeout):
            client.chat("Test")


def test_chat_json_decode_error(client, mock_response):
    """Test chat with invalid JSON in response."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [
        b"invalid json",
    ]

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(json.JSONDecodeError):
            list(client.chat_stream("Test"))


def test_chat_empty_lines(client, mock_response):
    """Test chat with empty lines in response."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [
        b"",
        b'{"parts": [{"type": "text", "text": "Text"}]}',
        b"",
        b'{"finish": "stop"}',
    ]

    with patch("requests.post", return_value=mock_response):
        result = client.chat("Test")

        # Empty lines should be filtered
        assert result["content"] == "Text"


def test_client_custom_base_url():
    """Test client with custom base URL."""
    from opencode_client import OpenCodeClient

    client = OpenCodeClient(base_url="http://custom.url:9999")

    assert client.base_url == "http://custom.url:9999"


def test_chat_long_message(client, mock_response):
    """Test chat with long message."""
    client.session_id = "test-session"

    long_message = "A" * 10000
    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Response"}]}',
        b'{"finish": "stop"}',
    ]

    with patch("requests.post", return_value=mock_response) as mock_post:
        client.chat(long_message)

        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert len(payload["parts"][0]["text"]) == 10000


def test_chat_unicode(client, mock_response):
    """Test chat with unicode characters."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Hello \\u00e9\\u00f1"}]}',
        b'{"finish": "stop"}',
    ]

    with patch("requests.post", return_value=mock_response):
        result = client.chat("Test")

        assert "é" in result["content"] or "ñ" in result["content"]


def test_chat_without_finish(client, mock_response):
    """Test chat response without finish marker."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Partial"}]}',
    ]

    with patch("requests.post", return_value=mock_response):
        result = client.chat("Test")

        assert result["content"] == "Partial"
        assert result["data"] == {}


def test_health_different_base_url():
    """Test health with different base URL."""
    from opencode_client import OpenCodeClient

    client = OpenCodeClient(base_url="http://other.url:8080")
    mock_response = Mock()
    mock_response.json.return_value = {"healthy": True}

    with patch("requests.get", return_value=mock_response) as mock_get:
        client.health()

        mock_get.assert_called_once_with("http://other.url:8080/global/health")


def test_create_session_updates_id(client, mock_response):
    """Test that create_session updates session_id."""
    assert client.session_id is None

    mock_response.json.return_value = {"id": "session-456"}

    with patch("requests.post", return_value=mock_response):
        client.create_session()

    assert client.session_id == "session-456"


def test_chat_stream_generator(client, mock_response):
    """Test that chat_stream returns an iterator."""
    client.session_id = "test-session"
    mock_response.iter_lines.return_value = [
        b'{"parts": [{"type": "text", "text": "Chunk 1"}]}',
        b'{"parts": [{"type": "text", "text": "Chunk 2"}]}',
    ]

    with patch("requests.post", return_value=mock_response):
        result = client.chat_stream("Test")

        # Should return a generator
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__") or hasattr(result, "send")
