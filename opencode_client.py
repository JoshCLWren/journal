#!/usr/bin/env python3
"""OpenCode client for interacting with OpenCode LLM server."""

import json
from collections.abc import Iterator
from typing import Any

import requests


class OpenCodeClient:
    """Client for interacting with OpenCode LLM server."""

    def __init__(self, base_url: str = "http://127.0.0.1:4096"):
        """Initialize OpenCode client with base URL.

        Args:
            base_url: URL of the OpenCode server
        """
        self.base_url = base_url
        self.session_id: str | None = None

    def health(self) -> dict[str, Any]:
        """Check if OpenCode server is healthy.

        Returns:
            Server health status information
        """
        r = requests.get(f"{self.base_url}/global/health")
        r.raise_for_status()
        return r.json()

    def create_session(self) -> str | None:
        """Create a new session with the OpenCode server.

        Returns:
            Session ID if successful, None otherwise
        """
        r = requests.post(f"{self.base_url}/session", json={})
        r.raise_for_status()
        self.session_id = r.json()["id"]
        return self.session_id

    def chat(
        self,
        message: str,
        model: str = "glm-4.7-free",
        provider: str = "opencode",
        timeout: int = 600,
    ) -> dict[str, Any]:
        """Send a message to the OpenCode LLM.

        Args:
            message: Message to send
            model: Model ID to use
            provider: Provider ID to use
            timeout: Request timeout in seconds (default: 600 = 10 minutes)

        Returns:
            Dictionary with 'content' and 'data' keys
        """
        if not self.session_id:
            self.create_session()

        payload = {
            "model": {"providerID": provider, "modelID": model},
            "parts": [{"type": "text", "text": message}],
        }

        r = requests.post(
            f"{self.base_url}/session/{self.session_id}/message",
            json=payload,
            stream=True,
            timeout=timeout,
        )
        r.raise_for_status()

        full_response = ""
        for line in r.iter_lines():
            if line:
                data = json.loads(line)
                if "parts" in data:
                    for part in data["parts"]:
                        if part.get("type") == "text":
                            text = part.get("text", "")
                            full_response += text
                elif data.get("finish") == "stop":
                    return {"content": full_response, "data": data}

        return {"content": full_response, "data": {}}

    def chat_stream(
        self,
        message: str,
        model: str = "glm-4.7-free",
        provider: str = "opencode",
        timeout: int = 600,
    ) -> Iterator[str]:
        """Send a message and stream response.

        Args:
            message: Message to send
            model: Model ID to use
            provider: Provider ID to use
            timeout: Request timeout in seconds (default: 600 = 10 minutes)

        Yields:
            Text chunks as they arrive
        """
        if not self.session_id:
            self.create_session()

        payload = {
            "model": {"providerID": provider, "modelID": model},
            "parts": [{"type": "text", "text": message}],
        }

        r = requests.post(
            f"{self.base_url}/session/{self.session_id}/message",
            json=payload,
            stream=True,
            timeout=timeout,
        )
        r.raise_for_status()

        for line in r.iter_lines():
            if line:
                data = json.loads(line)
                if "parts" in data:
                    for part in data["parts"]:
                        if part.get("type") == "text":
                            yield part.get("text", "")


def main():
    """Test OpenCode client functionality."""
    client = OpenCodeClient()

    print("Checking health...")
    health = client.health()
    print(f"Healthy: {health.get('healthy')}, Version: {health.get('version')}")

    response = client.chat("Explain what GLM-4.7 is in 3 sentences")
    print(f"\nResponse: {response['content']}")


if __name__ == "__main__":
    main()
