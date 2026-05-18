"""Minimal Ollama HTTP client (Phase 4.10).

Only what the verifier needs: ``generate(prompt, model, …) -> str``.
No streaming, no chat history, no embeddings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e4b"
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> OllamaConfig:
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL),
            model=os.getenv("TASK_PRIORITIZER_LLM_MODEL", DEFAULT_MODEL),
            timeout=float(os.getenv("TASK_PRIORITIZER_LLM_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)),
        )


class OllamaClient:
    def __init__(self, config: OllamaConfig | None = None, http: httpx.Client | None = None):
        self.config = config or OllamaConfig.from_env()
        self._http = http  # injectable for tests

    def _client(self) -> httpx.Client:
        return self._http or httpx.Client(timeout=self.config.timeout)

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        client = self._client()
        try:
            resp = client.post(f"{self.config.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("response", "")).strip()
        finally:
            if self._http is None:
                client.close()

    def is_available(self) -> bool:
        try:
            client = self._client()
            try:
                r = client.get(f"{self.config.base_url}/api/tags")
                return r.status_code == 200
            finally:
                if self._http is None:
                    client.close()
        except Exception:
            return False
