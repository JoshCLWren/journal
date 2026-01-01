#!/usr/bin/env python3
import requests
import json
from typing import Optional, Iterator, Dict, Any


class OpenCodeClient:
    def __init__(self, base_url: str = "http://127.0.0.1:4096"):
        self.base_url = base_url
        self.session_id: Optional[str] = None

    def health(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/global/health")
        r.raise_for_status()
        return r.json()

    def create_session(self) -> Optional[str]:
        r = requests.post(f"{self.base_url}/session", json={})
        r.raise_for_status()
        self.session_id = r.json()["id"]
        return self.session_id

    def chat(
        self, message: str, model: str = "glm-4.7-free", provider: str = "opencode"
    ) -> Dict[str, Any]:
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
        self, message: str, model: str = "glm-4.7-free", provider: str = "opencode"
    ) -> Iterator[str]:
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
    client = OpenCodeClient()

    print("Checking health...")
    health = client.health()
    print(f"Healthy: {health.get('healthy')}, Version: {health.get('version')}")

    response = client.chat("Explain what GLM-4.7 is in 3 sentences")
    print(f"\nResponse: {response['content']}")


if __name__ == "__main__":
    main()
