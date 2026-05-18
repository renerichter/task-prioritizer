"""Phase 4.8 — Pattern-matched estimate suggester."""

from __future__ import annotations

from pathlib import Path

import pytest

from task_prioritizer.core.estimate_suggester import (
    SuggestResult,
    suggest_estimate,
    tokenize,
)
from task_prioritizer.persistence import history


@pytest.fixture
def db(tmp_path) -> Path:
    p = tmp_path / "h.db"
    history.init_db(p).close()
    return p


def _result_for(text: str) -> dict:
    return {
        "output": text, "urgency_sym": "🐢", "execution_sym": "🍭",
        "scores": {"impact": 0.5, "urgency": 0.5, "execution": 0.5},
        "ratings": {"L": 0.3, "Conf": 0.3, "G": 0.3, "P": 0.3, "D": 0.3,
                    "C": 0.3, "T": 0.3, "R": 0.3, "F": 0.3,
                    "S": 0.0, "Pl": 1.0, "Rec": 0.0},
        "symbols": {}, "analysis": "", "quadrant": "calm_simple",
        "estimated_time_minutes": None, "planned_time_minutes": None,
    }


def _record(db, text, actuals):
    tid = history.record_task(text, _result_for(text), "batch", None, db_path=db)
    for m in actuals:
        history.record_actual(tid, m, db_path=db)
    return tid


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------


def test_tokenize_lowercases_and_splits():
    assert tokenize("Write Q4 Draft") == {"write", "draft"}  # 'q4' too short


def test_tokenize_drops_punctuation_and_short_words():
    assert tokenize("fix: API bug! in the auth module.") == {
        "fix", "api", "bug", "auth", "module",
    }


def test_tokenize_drops_curly_brace_tags():
    assert "p1" not in tokenize("{p1:30} write report")
    assert "p" not in tokenize("{p0:45} review pr")
    assert "write" in tokenize("{p1:30} write report")


def test_tokenize_drops_common_stop_words():
    tokens = tokenize("review the pr for the new feature")
    assert "the" not in tokens
    assert "for" not in tokens
    assert "review" in tokens
    assert "feature" in tokens


# ---------------------------------------------------------------------------
# Suggestion logic
# ---------------------------------------------------------------------------


def test_suggest_returns_none_when_no_history(db):
    assert suggest_estimate("any task", db_path=db) is None


def test_suggest_returns_none_when_no_similar_task(db):
    _record(db, "wash car", [30])
    _record(db, "buy groceries", [20])
    assert suggest_estimate("write code", db_path=db) is None


def test_suggest_single_similar_task_returns_its_median(db):
    _record(db, "write quarterly report draft", [60, 90])
    result = suggest_estimate("write the quarterly report", db_path=db)
    assert isinstance(result, SuggestResult)
    assert result.estimate_minutes == 75  # median of 60, 90
    assert result.datapoint_count == 2
    assert len(result.similar_tasks) == 1
    assert "quarterly" in result.similar_tasks[0]["input"]


def test_suggest_multiple_similar_returns_median_across_all(db):
    _record(db, "fix bug in auth module", [30])
    _record(db, "fix auth bug login", [45])
    _record(db, "auth bug fix session", [60])
    result = suggest_estimate("fix bug auth", db_path=db)
    assert result is not None
    # All three actuals: [30, 45, 60] → median 45
    assert result.estimate_minutes == 45
    assert result.datapoint_count == 3
    assert len(result.similar_tasks) == 3


def test_suggest_includes_similarity_proof(db):
    _record(db, "write report", [60])
    result = suggest_estimate("write report", db_path=db)
    assert result is not None
    assert "explanation" in result.__dict__ or hasattr(result, "explanation")
    assert "60" in result.explanation
    assert "write" in result.explanation.lower() or "report" in result.explanation.lower()


def test_suggest_ignores_tasks_without_actuals(db):
    history.record_task("write report without actual", _result_for("x"), "batch", None, db_path=db)
    assert suggest_estimate("write report", db_path=db) is None


def test_suggest_uses_jaccard_threshold(db):
    # 1 token shared out of many → low similarity
    _record(db, "completely different unrelated topic", [120])
    # No overlap with the query "write report"
    assert suggest_estimate("write report", db_path=db) is None


def test_suggest_rounds_to_nearest_5_minutes(db):
    _record(db, "write report", [33])
    _record(db, "write report draft", [38])
    result = suggest_estimate("write report", db_path=db)
    assert result is not None
    assert result.estimate_minutes % 5 == 0
