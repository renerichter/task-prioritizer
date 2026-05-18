"""Calm LLM verifier (Phase 4.10).

Given a task + computed ratings/symbols, ask the model to challenge the
prioritization *calmly* — never to override it. The user remains the
decision-maker; the LLM is a sparring partner. Output is bounded to
≤120 words and structured as plain prose.

Opt-in: only invoked when the user types ``/discuss`` (CLI) or hits the
Discuss button (TUI). Disabled by default; will fail closed when Ollama
is unreachable or ``TASK_PRIORITIZER_LLM_ENABLED`` is not "1".
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .ollama import OllamaClient

SYSTEM_PROMPT = (
    "You are a calm sparring partner for a single-developer prioritization tool. "
    "Your role is to gently challenge the user's ratings — never override them. "
    "Be concise (≤120 words). No emojis. No exclamation marks. "
    "If the ratings look coherent, say so plainly. "
    "If you notice a tension (e.g. high Confidence but high Risk, or planned but unclear), "
    "name it in one sentence and ask one question. End with: 'Your call.'"
)


@dataclass(frozen=True)
class VerifierResult:
    text: str
    used_model: str


def is_enabled() -> bool:
    return os.getenv("TASK_PRIORITIZER_LLM_ENABLED", "0") == "1"


def build_prompt(task_text: str, result: dict) -> str:
    scores = result.get("scores", {})
    return (
        f"Task: {task_text}\n"
        f"Computed scores → impact={scores.get('impact', 0):.2f}, "
        f"urgency={scores.get('urgency', 0):.2f}, "
        f"execution={scores.get('execution', 0):.2f}.\n"
        f"Output line: {result.get('output', '')}\n"
        f"Quadrant: {result.get('quadrant', '')}.\n"
        f"Recommendation: {result.get('quadrant_recommendation', '')}.\n"
        "Briefly: do these ratings hold together? One tension + one question, or affirm."
    )


def discuss(task_text: str, result: dict, client: OllamaClient | None = None) -> VerifierResult | None:
    """Return None when disabled or unavailable; otherwise a VerifierResult."""
    if not is_enabled():
        return None
    client = client or OllamaClient()
    if not client.is_available():
        return None
    prompt = build_prompt(task_text, result)
    text = client.generate(prompt, system=SYSTEM_PROMPT)
    return VerifierResult(text=text, used_model=client.config.model)
