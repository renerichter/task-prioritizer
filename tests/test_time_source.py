"""Phase 4.7 — TimeSource interface + clockipy adapter."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from task_prioritizer.ingest.clockipy_source import ClockipyTimeSource
from task_prioritizer.ingest.manual_source import ManualTimeSource
from task_prioritizer.ingest.time_source import TimeSource

# ---------------------------------------------------------------------------
# Interface protocol
# ---------------------------------------------------------------------------


def test_time_source_protocol_methods_exist():
    """The protocol must declare is_available and get_actual_minutes_for."""
    assert hasattr(TimeSource, "is_available")
    assert hasattr(TimeSource, "get_actual_minutes_for")


# ---------------------------------------------------------------------------
# ManualTimeSource (in-memory, used in tests / fallback)
# ---------------------------------------------------------------------------


def test_manual_source_is_always_available():
    src = ManualTimeSource()
    assert src.is_available() is True


def test_manual_source_returns_recorded_minutes():
    src = ManualTimeSource({"write draft": [60, 45]})
    assert src.get_actual_minutes_for("write draft") == [60, 45]


def test_manual_source_unknown_text_returns_empty_list():
    src = ManualTimeSource()
    assert src.get_actual_minutes_for("nothing") == []


def test_manual_source_record_appends():
    src = ManualTimeSource()
    src.record("task A", 30)
    src.record("task A", 15)
    assert src.get_actual_minutes_for("task A") == [30, 15]


# ---------------------------------------------------------------------------
# ClockipyTimeSource (adapter)
# ---------------------------------------------------------------------------


def test_clockipy_source_unavailable_when_no_client():
    src = ClockipyTimeSource(client=None)
    assert src.is_available() is False
    assert src.get_actual_minutes_for("anything") == []


def test_clockipy_source_aggregates_matching_entries():
    fake_client = MagicMock()
    fake_client.get_time_entries.return_value = [
        {"description": "write draft", "duration_minutes": 60},
        {"description": "write draft", "duration_minutes": 45},
        {"description": "unrelated", "duration_minutes": 999},
    ]
    src = ClockipyTimeSource(client=fake_client)
    assert src.is_available() is True
    result = src.get_actual_minutes_for(
        "write draft",
        since=date.today() - timedelta(days=30),
        until=date.today(),
    )
    assert sorted(result) == [45, 60]


def test_clockipy_source_substring_match_case_insensitive():
    fake_client = MagicMock()
    fake_client.get_time_entries.return_value = [
        {"description": "Write Draft for Q4", "duration_minutes": 30},
        {"description": "draft revisions", "duration_minutes": 20},
    ]
    src = ClockipyTimeSource(client=fake_client)
    result = src.get_actual_minutes_for("draft")
    assert sorted(result) == [20, 30]


def test_clockipy_source_handles_iso_duration_format():
    """Clockify returns durations as ISO 8601 strings like 'PT1H30M'."""
    fake_client = MagicMock()
    fake_client.get_time_entries.return_value = [
        {"description": "deep work", "timeInterval": {"duration": "PT1H30M"}},
        {"description": "deep work", "timeInterval": {"duration": "PT45M"}},
    ]
    src = ClockipyTimeSource(client=fake_client)
    result = src.get_actual_minutes_for("deep work")
    assert sorted(result) == [45, 90]


def test_clockipy_source_swallows_client_errors_returns_empty():
    fake_client = MagicMock()
    fake_client.get_time_entries.side_effect = RuntimeError("network down")
    src = ClockipyTimeSource(client=fake_client)
    assert src.get_actual_minutes_for("x") == []


# ---------------------------------------------------------------------------
# Live test (gated)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_clockipy_live_integration():
    """Only runs when the user opts into live tests via -m live."""
    try:
        import clockipy  # noqa: F401
    except ImportError:
        pytest.skip("clockipy not installed")
    pytest.skip("requires live Clockify credentials; manual run only")
