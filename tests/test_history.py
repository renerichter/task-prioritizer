"""Phase 4.6 — SQLite history store."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from task_prioritizer.persistence import history


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch) -> Path:
    p = tmp_path / "history.db"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("TASK_PRIORITIZER_HISTORY_DB", str(p))
    return p


def _sample_result() -> dict:
    return {
        "output": "⭐️⭐️--🗓️ test",
        "urgency_sym": "🚨",
        "execution_sym": "🍭",
        "has_surprise": False,
        "scores": {"impact": 0.7, "urgency": 0.9, "execution": 0.2},
        "ratings": {
            "L": 1.0, "Conf": 1.0, "G": 0.3,
            "P": 1.0, "D": 1.0,
            "C": 0.0, "T": 0.0, "R": 0.3, "F": 1.0,
            "S": 0.0, "Pl": 1.0, "Rec": 0.0,
        },
        "symbols": {
            "impact": "⭐️⭐️", "urgency": "🚨", "execution": "🍭",
            "surprise": "", "planned": "🗓️", "recurrent": "",
        },
        "estimated_time_minutes": 30,
        "planned_time_minutes": None,
        "analysis": "Quick win.",
        "quadrant": "urgent_simple",
        "quadrant_recommendation": "Do now.",
    }


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def test_get_db_path_uses_xdg_data_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.delenv("TASK_PRIORITIZER_HISTORY_DB", raising=False)
    p = history.get_db_path()
    assert p == tmp_path / "task-prioritizer" / "history.db"


def test_get_db_path_explicit_override(tmp_path, monkeypatch):
    override = tmp_path / "custom.db"
    monkeypatch.setenv("TASK_PRIORITIZER_HISTORY_DB", str(override))
    assert history.get_db_path() == override


def test_get_db_path_falls_back_to_home_local_share(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("TASK_PRIORITIZER_HISTORY_DB", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    p = history.get_db_path()
    assert p == tmp_path / ".local" / "share" / "task-prioritizer" / "history.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_init_db_creates_tables(db_path):
    conn = history.init_db(db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur}
    assert "tasks" in tables
    assert "actuals" in tables
    assert "schema_version" in tables
    conn.close()


def test_init_db_is_idempotent(db_path):
    history.init_db(db_path).close()
    # Second call must not raise.
    conn = history.init_db(db_path)
    conn.close()


def test_schema_version_is_recorded(db_path):
    conn = history.init_db(db_path)
    cur = conn.execute("SELECT version FROM schema_version")
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == history.SCHEMA_VERSION
    conn.close()


# ---------------------------------------------------------------------------
# record_task / record_actual
# ---------------------------------------------------------------------------


def test_record_task_returns_id_and_persists_fields(db_path):
    history.init_db(db_path).close()
    task_id = history.record_task(
        task_input="{p0:30} test task",
        result=_sample_result(),
        mode="batch",
        profile=None,
        db_path=db_path,
    )
    assert isinstance(task_id, int) and task_id > 0
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT input, mode, quadrant, rating_l, score_impact, estimated_minutes "
            "FROM tasks WHERE id = ?", (task_id,)
        )
        row = cur.fetchone()
    assert row[0] == "{p0:30} test task"
    assert row[1] == "batch"
    assert row[2] == "urgent_simple"
    assert row[3] == 1.0
    assert row[4] == pytest.approx(0.7)
    assert row[5] == 30


def test_record_actual_links_to_task(db_path):
    history.init_db(db_path).close()
    task_id = history.record_task(
        task_input="foo", result=_sample_result(), mode="batch", profile=None,
        db_path=db_path,
    )
    actual_id = history.record_actual(task_id, 45, source="manual", db_path=db_path)
    assert actual_id > 0
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT task_id, actual_minutes, source FROM actuals WHERE id = ?",
            (actual_id,)
        )
        row = cur.fetchone()
    assert row == (task_id, 45, "manual")


def test_record_actual_rejects_unknown_task(db_path):
    history.init_db(db_path).close()
    with pytest.raises(ValueError, match="unknown task_id"):
        history.record_actual(99999, 30, db_path=db_path)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def test_recent_tasks_returns_in_reverse_chronological_order(db_path):
    history.init_db(db_path).close()
    for i in range(3):
        r = _sample_result()
        r["output"] = f"task-{i}"
        history.record_task(f"input-{i}", r, "batch", None, db_path=db_path)
    rows = history.recent_tasks(limit=10, db_path=db_path)
    assert len(rows) == 3
    assert rows[0]["input"] == "input-2"
    assert rows[-1]["input"] == "input-0"


def test_tasks_with_actuals_for_estimate_suggester(db_path):
    history.init_db(db_path).close()
    tid = history.record_task("write draft", _sample_result(), "batch", None, db_path=db_path)
    history.record_actual(tid, 60, db_path=db_path)
    history.record_actual(tid, 45, db_path=db_path)
    rows = history.tasks_with_actuals(db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["input"] == "write draft"
    assert sorted(rows[0]["actual_minutes"]) == [45, 60]


# ---------------------------------------------------------------------------
# JSONL migration
# ---------------------------------------------------------------------------


def test_migrate_from_jsonl_inserts_rows(tmp_path, db_path):
    jsonl = tmp_path / "tasks.log"
    rows = [
        {
            "ts": datetime.now(UTC).isoformat(),
            "input": "old task one",
            "ratings": _sample_result()["ratings"],
            "scores": _sample_result()["scores"],
            "symbols": _sample_result()["symbols"],
            "output": "out1",
            "estimated_time_minutes": 30,
            "planned_time_minutes": None,
            "mode": "batch", "profile": None,
            "analysis": "ok", "quadrant": "calm_simple",
        },
        {
            "ts": datetime.now(UTC).isoformat(),
            "input": "old task two",
            "ratings": _sample_result()["ratings"],
            "scores": _sample_result()["scores"],
            "symbols": _sample_result()["symbols"],
            "output": "out2",
            "estimated_time_minutes": 60,
            "planned_time_minutes": 60,
            "mode": "detail", "profile": "work",
            "analysis": "ok", "quadrant": "urgent_complex",
        },
    ]
    jsonl.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    history.init_db(db_path).close()
    n = history.migrate_from_jsonl(jsonl, db_path=db_path)
    assert n == 2
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert count == 2


def test_migrate_from_jsonl_is_idempotent_per_row(tmp_path, db_path):
    jsonl = tmp_path / "tasks.log"
    row = {
        "ts": "2025-01-01T00:00:00+00:00",
        "input": "same task",
        "ratings": _sample_result()["ratings"],
        "scores": _sample_result()["scores"],
        "symbols": _sample_result()["symbols"],
        "output": "out",
        "estimated_time_minutes": None,
        "planned_time_minutes": None,
        "mode": "batch", "profile": None,
        "analysis": "", "quadrant": "calm_simple",
    }
    jsonl.write_text(json.dumps(row) + "\n", encoding="utf-8")
    history.init_db(db_path).close()
    assert history.migrate_from_jsonl(jsonl, db_path=db_path) == 1
    # Re-run: should not re-insert.
    assert history.migrate_from_jsonl(jsonl, db_path=db_path) == 0
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert count == 1


def test_migrate_from_jsonl_handles_missing_file_gracefully(tmp_path, db_path):
    history.init_db(db_path).close()
    n = history.migrate_from_jsonl(tmp_path / "nonexistent.log", db_path=db_path)
    assert n == 0
