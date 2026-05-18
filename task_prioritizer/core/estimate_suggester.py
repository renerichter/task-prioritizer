"""Pattern-matched estimate suggester.

Given a task text, find historical tasks with recorded actuals whose
tokens overlap significantly, then return the median actual minutes plus
a proof bundle (similar tasks, similarity scores). Deterministic — no
LLM, no fuzzy heuristics.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from ..persistence import history

_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "for", "to", "of", "in", "on",
    "at", "by", "with", "from", "is", "are", "was", "were", "be", "been",
    "being", "this", "that", "it", "as", "if", "do", "did", "will",
    "would", "should", "could", "can", "may", "my", "your", "our",
    "their", "i", "you", "we", "they", "he", "she",
})

# Strip {…} curly-brace tags (planned-time tag, project tag, etc.) before
# tokenizing. They are structural, not semantic.
_TAG_RE = re.compile(r"\{[^}]+\}")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")

_SIMILARITY_THRESHOLD = 0.30
_MAX_DATAPOINT_AGE_DAYS = 365  # not enforced yet; future tightening


@dataclass(frozen=True)
class SuggestResult:
    estimate_minutes: int
    datapoint_count: int
    similar_tasks: list[dict] = field(default_factory=list)
    explanation: str = ""


def tokenize(text: str) -> set[str]:
    """Lowercase, drop tags + short / stop words, return alphanumeric token set."""
    cleaned = _TAG_RE.sub(" ", text or "").lower()
    tokens: set[str] = set()
    for m in _WORD_RE.finditer(cleaned):
        word = m.group(0)
        if len(word) < 3 or word in _STOP_WORDS:
            continue
        tokens.add(word)
    return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _round_to_5(value: float) -> int:
    return round(value / 5.0) * 5


def suggest_estimate(
    task_text: str,
    db_path: Path | None = None,
    threshold: float = _SIMILARITY_THRESHOLD,
) -> SuggestResult | None:
    """Return a SuggestResult or None when no usable history exists."""
    query_tokens = tokenize(task_text)
    if not query_tokens:
        return None

    candidates = history.tasks_with_actuals(db_path=db_path)
    if not candidates:
        return None

    matched: list[dict] = []
    all_actuals: list[int] = []
    for row in candidates:
        cand_tokens = tokenize(row.get("input", ""))
        sim = _jaccard(query_tokens, cand_tokens)
        if sim < threshold:
            continue
        actuals = row.get("actual_minutes", []) or []
        if not actuals:
            continue
        median_for_task = statistics.median(actuals)
        matched.append({
            "input": row["input"],
            "median_actual": median_for_task,
            "similarity": round(sim, 3),
            "samples": list(actuals),
        })
        all_actuals.extend(actuals)

    if not all_actuals:
        return None

    estimate = _round_to_5(statistics.median(all_actuals))
    sample_lines = ", ".join(
        f"{m['input']!r} (~{int(m['median_actual'])}m, sim={m['similarity']})"
        for m in matched
    )
    explanation = (
        f"Suggested ~{estimate} min based on {len(all_actuals)} historical "
        f"actual(s) across {len(matched)} similar task(s): {sample_lines}."
    )
    return SuggestResult(
        estimate_minutes=estimate,
        datapoint_count=len(all_actuals),
        similar_tasks=matched,
        explanation=explanation,
    )
