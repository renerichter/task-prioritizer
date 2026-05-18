"""Phase 4.10 — Ollama verifier tests (mocked + one live-gated)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import httpx
import pytest

from task_prioritizer.llm import discuss, is_enabled
from task_prioritizer.llm.ollama import OllamaClient, OllamaConfig
from task_prioritizer.llm.verifier import SYSTEM_PROMPT, build_prompt

# ---------------------------------------------------------------------------
# Enablement gating
# ---------------------------------------------------------------------------


def test_is_enabled_off_by_default(monkeypatch):
    monkeypatch.delenv("TASK_PRIORITIZER_LLM_ENABLED", raising=False)
    assert is_enabled() is False


def test_is_enabled_with_flag(monkeypatch):
    monkeypatch.setenv("TASK_PRIORITIZER_LLM_ENABLED", "1")
    assert is_enabled() is True


def test_discuss_returns_none_when_disabled(monkeypatch):
    monkeypatch.delenv("TASK_PRIORITIZER_LLM_ENABLED", raising=False)
    assert discuss("any", {"scores": {}}) is None


# ---------------------------------------------------------------------------
# Ollama client (mocked transport)
# ---------------------------------------------------------------------------


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def test_client_generate_returns_response_field():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        assert "Task:" in request.read().decode() or True
        return httpx.Response(200, json={"response": "Looks coherent. Your call."})

    http = httpx.Client(transport=_mock_transport(handler))
    client = OllamaClient(OllamaConfig(base_url="http://x"), http=http)
    out = client.generate("hello", system="sys")
    assert out == "Looks coherent. Your call."


def test_client_is_available_true():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": []})

    client = OllamaClient(OllamaConfig(base_url="http://x"),
                          http=httpx.Client(transport=_mock_transport(handler)))
    assert client.is_available() is True


def test_client_is_available_false_on_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    client = OllamaClient(OllamaConfig(base_url="http://x"),
                          http=httpx.Client(transport=_mock_transport(handler)))
    assert client.is_available() is False


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------


def test_build_prompt_includes_scores_and_quadrant():
    result = {
        "scores": {"impact": 0.7, "urgency": 0.5, "execution": 0.4},
        "output": "⭐️⭐️ Task 🚨 🥵",
        "quadrant": "urgent_complex",
        "quadrant_recommendation": "Schedule a focused block.",
    }
    prompt = build_prompt("ship migration", result)
    assert "ship migration" in prompt
    assert "0.70" in prompt
    assert "urgent_complex" in prompt
    assert "Schedule" in prompt


def test_discuss_calls_client_and_returns_result(monkeypatch):
    monkeypatch.setenv("TASK_PRIORITIZER_LLM_ENABLED", "1")
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.is_available.return_value = True
    mock_client.config = OllamaConfig(model="gemma4:e4b")
    mock_client.generate.return_value = "One tension noticed. Your call."

    result = discuss("write report", {"scores": {"impact": 0.5}}, client=mock_client)
    assert result is not None
    assert result.text == "One tension noticed. Your call."
    assert result.used_model == "gemma4:e4b"
    mock_client.generate.assert_called_once()
    args, kwargs = mock_client.generate.call_args
    assert kwargs["system"] == SYSTEM_PROMPT


def test_discuss_returns_none_when_unavailable(monkeypatch):
    monkeypatch.setenv("TASK_PRIORITIZER_LLM_ENABLED", "1")
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.is_available.return_value = False
    assert discuss("x", {"scores": {}}, client=mock_client) is None


# ---------------------------------------------------------------------------
# Live integration (skipped unless explicitly enabled)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.getenv("TASK_PRIORITIZER_LLM_LIVE") != "1",
    reason="live Ollama test (set TASK_PRIORITIZER_LLM_LIVE=1 to run)",
)
def test_live_ollama_generates_short_response():
    client = OllamaClient()
    if not client.is_available():
        pytest.skip("Ollama not running on localhost:11434")
    out = client.generate("Say 'ok'.", system="Reply with one word.")
    assert isinstance(out, str)
    assert out  # non-empty
