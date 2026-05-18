"""Phase 4.5 — Decision-Matrix quadrant emission + stop-rule scaffold."""

from __future__ import annotations

import pytest

from task_prioritizer.config import Config
from task_prioritizer.core.decision_matrix import (
    QUADRANTS,
    classify_quadrant,
    quadrant_recommendation,
)
from task_prioritizer.core.stop_rule import StopRuleResult, check_stop_rule
from task_prioritizer.main import run_with_ratings

# ---------------------------------------------------------------------------
# Quadrant classification (urgency × execution)
# ---------------------------------------------------------------------------


def test_quadrants_contain_four_canonical_keys():
    assert set(QUADRANTS.keys()) == {
        "urgent_simple",
        "urgent_complex",
        "calm_simple",
        "calm_complex",
    }


def test_classify_urgent_simple():
    # High urgency, low execution → 🚨 & 🍭 → "do now"
    q = classify_quadrant(urgency_symbol="🚨", execution_symbol="🍭")
    assert q == "urgent_simple"


def test_classify_urgent_complex():
    q = classify_quadrant(urgency_symbol="🚨", execution_symbol="🥵")
    assert q == "urgent_complex"


def test_classify_calm_simple():
    q = classify_quadrant(urgency_symbol="🐢", execution_symbol="🍭")
    assert q == "calm_simple"


def test_classify_calm_complex():
    q = classify_quadrant(urgency_symbol="🐢", execution_symbol="🥵")
    assert q == "calm_complex"


def test_recommendations_match_faq():
    """The four FAQ recommendations must be preserved verbatim in spirit."""
    assert "do now" in quadrant_recommendation("urgent_simple").lower()
    assert "break down" in quadrant_recommendation("urgent_complex").lower()
    assert "schedule" in quadrant_recommendation("calm_simple").lower()
    rec_complex = quadrant_recommendation("calm_complex").lower()
    assert "trash" in rec_complex or "spare" in rec_complex


# ---------------------------------------------------------------------------
# Integration: run_with_ratings emits quadrant fields
# ---------------------------------------------------------------------------


def test_run_with_ratings_emits_quadrant_key():
    # ratings: L,Conf,G,P,D,C,T,R,F,S,Pl,Rec — all medium-high
    ratings = [
        Config.RATING_MAP["3"], Config.RATING_MAP["3"], Config.RATING_MAP["3"],  # impact
        Config.RATING_MAP["3"], Config.RATING_MAP["3"],                          # urgency high
        Config.RATING_MAP["0"], Config.RATING_MAP["0"], Config.RATING_MAP["0"], Config.RATING_MAP["3"],  # execution low (easy + fun)
        Config.RATING_MAP["0"], Config.RATING_MAP["3"], Config.RATING_MAP["0"],  # clarity
    ]
    result = run_with_ratings("test task", ratings)
    assert "quadrant" in result
    assert result["quadrant"] == "urgent_simple"
    assert "quadrant_recommendation" in result
    assert "do now" in result["quadrant_recommendation"].lower()


def test_run_with_ratings_urgent_complex_quadrant():
    ratings = [
        Config.RATING_MAP["3"], Config.RATING_MAP["3"], Config.RATING_MAP["3"],
        Config.RATING_MAP["3"], Config.RATING_MAP["3"],
        Config.RATING_MAP["3"], Config.RATING_MAP["3"], Config.RATING_MAP["3"], Config.RATING_MAP["0"],
        Config.RATING_MAP["0"], Config.RATING_MAP["3"], Config.RATING_MAP["0"],
    ]
    result = run_with_ratings("hard urgent", ratings)
    assert result["quadrant"] == "urgent_complex"


def test_run_with_ratings_calm_simple_quadrant():
    ratings = [
        Config.RATING_MAP["0"], Config.RATING_MAP["0"], Config.RATING_MAP["0"],
        Config.RATING_MAP["0"], Config.RATING_MAP["0"],
        Config.RATING_MAP["0"], Config.RATING_MAP["0"], Config.RATING_MAP["0"], Config.RATING_MAP["3"],
        Config.RATING_MAP["0"], Config.RATING_MAP["0"], Config.RATING_MAP["0"],
    ]
    result = run_with_ratings("filler", ratings)
    assert result["quadrant"] == "calm_simple"


# ---------------------------------------------------------------------------
# Stop-rule
# ---------------------------------------------------------------------------


def test_stop_rule_not_triggered_under_threshold():
    out = check_stop_rule(estimated_minutes=60, actual_minutes=80)
    assert out is None  # 80 / 60 = 1.33 < 1.5


def test_stop_rule_triggered_at_threshold():
    out = check_stop_rule(estimated_minutes=60, actual_minutes=90)
    assert isinstance(out, StopRuleResult)
    assert out.triggered is True
    assert out.ratio == pytest.approx(1.5)


def test_stop_rule_triggered_over_threshold():
    out = check_stop_rule(estimated_minutes=60, actual_minutes=120)
    assert isinstance(out, StopRuleResult)
    assert out.triggered is True
    assert out.ratio == pytest.approx(2.0)
    assert "stop" in out.message.lower() or "reflect" in out.message.lower()


def test_stop_rule_handles_zero_estimate():
    """No estimate → cannot compute ratio; return None (calm tool, no crash)."""
    assert check_stop_rule(estimated_minutes=0, actual_minutes=120) is None
    assert check_stop_rule(estimated_minutes=None, actual_minutes=120) is None


def test_stop_rule_handles_missing_actual():
    assert check_stop_rule(estimated_minutes=60, actual_minutes=None) is None


def test_stop_rule_respects_config_factor(monkeypatch):
    monkeypatch.setattr(Config, "STOP_RULE_FACTOR", 2.0)
    # ratio 1.5 should NOT trigger when factor is 2.0
    out = check_stop_rule(estimated_minutes=60, actual_minutes=90)
    assert out is None
    # ratio 2.0 should trigger
    out = check_stop_rule(estimated_minutes=60, actual_minutes=120)
    assert out is not None and out.triggered
