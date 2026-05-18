"""SQLite history store for tasks + actual time entries.

Schema is denormalized for query simplicity (one row per task with all 12
ratings as columns) but ``actuals`` is a separate one-to-many table so a
task can accumulate multiple time-tracking sessions. JSONL remains the
append-only audit log; this DB is the queryable analytical store and is
the basis for the estimate-suggester (Phase 4.8) and stop-rule lookups.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    input TEXT NOT NULL,
    output TEXT NOT NULL,
    mode TEXT,
    profile TEXT,
    analysis TEXT,
    quadrant TEXT,

    rating_l    REAL, rating_conf REAL, rating_g    REAL,
    rating_p    REAL, rating_d    REAL,
    rating_c    REAL, rating_t    REAL, rating_r    REAL, rating_f REAL,
    rating_s    REAL, rating_pl   REAL, rating_rec  REAL,

    score_impact    REAL,
    score_urgency   REAL,
    score_execution REAL,

    estimated_minutes INTEGER,
    planned_minutes   INTEGER,

    UNIQUE(ts, input)
);

CREATE TABLE IF NOT EXISTS actuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    actual_minutes INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_ts        ON tasks(ts);
CREATE INDEX IF NOT EXISTS idx_tasks_quadrant  ON tasks(quadrant);
CREATE INDEX IF NOT EXISTS idx_actuals_task    ON actuals(task_id);
"""


# ---------------------------------------------------------------------------
# Path / connection
# ---------------------------------------------------------------------------


def get_db_path() -> Path:
    override = os.environ.get("TASK_PRIORITIZER_HISTORY_DB")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "task-prioritizer" / "history.db"


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path if db_path is not None else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Create schema if missing; idempotent."""
    conn = _connect(db_path)
    conn.executescript(_SCHEMA_SQL)
    cur = conn.execute("SELECT COUNT(*) FROM schema_version")
    if cur.fetchone()[0] == 0:
        conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Inserts
# ---------------------------------------------------------------------------


def _task_row_from_result(
    task_input: str, result: dict, mode: str, profile: str | None, ts: str | None = None
) -> dict[str, Any]:
    ratings = result.get("ratings", {})
    scores = result.get("scores", {})
    return {
        "ts": ts or datetime.now(UTC).isoformat(),
        "input": task_input,
        "output": result.get("output", ""),
        "mode": mode,
        "profile": profile,
        "analysis": result.get("analysis", ""),
        "quadrant": result.get("quadrant", ""),
        "rating_l": ratings.get("L"),
        "rating_conf": ratings.get("Conf"),
        "rating_g": ratings.get("G"),
        "rating_p": ratings.get("P"),
        "rating_d": ratings.get("D"),
        "rating_c": ratings.get("C"),
        "rating_t": ratings.get("T"),
        "rating_r": ratings.get("R"),
        "rating_f": ratings.get("F"),
        "rating_s": ratings.get("S"),
        "rating_pl": ratings.get("Pl"),
        "rating_rec": ratings.get("Rec"),
        "score_impact": scores.get("impact"),
        "score_urgency": scores.get("urgency"),
        "score_execution": scores.get("execution"),
        "estimated_minutes": result.get("estimated_time_minutes"),
        "planned_minutes": result.get("planned_time_minutes"),
    }


_INSERT_TASK_SQL = """
INSERT OR IGNORE INTO tasks (
    ts, input, output, mode, profile, analysis, quadrant,
    rating_l, rating_conf, rating_g, rating_p, rating_d,
    rating_c, rating_t, rating_r, rating_f,
    rating_s, rating_pl, rating_rec,
    score_impact, score_urgency, score_execution,
    estimated_minutes, planned_minutes
) VALUES (
    :ts, :input, :output, :mode, :profile, :analysis, :quadrant,
    :rating_l, :rating_conf, :rating_g, :rating_p, :rating_d,
    :rating_c, :rating_t, :rating_r, :rating_f,
    :rating_s, :rating_pl, :rating_rec,
    :score_impact, :score_urgency, :score_execution,
    :estimated_minutes, :planned_minutes
)
"""


def record_task(
    task_input: str,
    result: dict,
    mode: str,
    profile: str | None,
    db_path: Path | None = None,
    ts: str | None = None,
) -> int:
    """Insert a task row; return its id. Returns existing id on UNIQUE conflict."""
    row = _task_row_from_result(task_input, result, mode, profile, ts=ts)
    with closing(init_db(db_path)) as conn:
        cur = conn.execute(_INSERT_TASK_SQL, row)
        conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        # Conflict path: fetch existing id.
        existing = conn.execute(
            "SELECT id FROM tasks WHERE ts = ? AND input = ?", (row["ts"], row["input"])
        ).fetchone()
        return existing[0] if existing else 0


def record_actual(
    task_id: int,
    actual_minutes: int,
    source: str = "manual",
    db_path: Path | None = None,
    recorded_at: str | None = None,
) -> int:
    with closing(init_db(db_path)) as conn:
        exists = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not exists:
            raise ValueError(f"unknown task_id: {task_id}")
        cur = conn.execute(
            "INSERT INTO actuals (task_id, actual_minutes, source, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (task_id, actual_minutes, source, recorded_at or datetime.now(UTC).isoformat()),
        )
        conn.commit()
        return cur.lastrowid or 0


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def recent_tasks(limit: int = 20, db_path: Path | None = None) -> list[dict]:
    with closing(init_db(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM tasks ORDER BY ts DESC, id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]


def tasks_with_actuals(db_path: Path | None = None) -> list[dict]:
    """Return tasks that have at least one actual time entry."""
    with closing(init_db(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT t.id, t.input, t.output, t.estimated_minutes, t.planned_minutes
            FROM tasks t
            WHERE EXISTS (SELECT 1 FROM actuals a WHERE a.task_id = t.id)
            ORDER BY t.ts DESC
            """
        ).fetchall()
        out: list[dict] = []
        for r in rows:
            d = dict(r)
            actuals = conn.execute(
                "SELECT actual_minutes FROM actuals WHERE task_id = ? ORDER BY recorded_at",
                (d["id"],),
            ).fetchall()
            d["actual_minutes"] = [a[0] for a in actuals]
            out.append(d)
        return out


# ---------------------------------------------------------------------------
# JSONL migration
# ---------------------------------------------------------------------------


def migrate_from_jsonl(jsonl_path: Path, db_path: Path | None = None) -> int:
    """Read a JSONL log and insert each row into the SQLite store.

    Returns the count of newly inserted rows (skips duplicates via the
    UNIQUE(ts, input) constraint). Missing files are not an error.
    """
    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists():
        return 0
    inserted = 0
    with closing(init_db(db_path)) as conn:
        with open(jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                row = _task_row_from_result(
                    entry.get("input", ""),
                    {
                        "output": entry.get("output", ""),
                        "ratings": entry.get("ratings", {}),
                        "scores": entry.get("scores", {}),
                        "analysis": entry.get("analysis", ""),
                        "quadrant": entry.get("quadrant", ""),
                        "estimated_time_minutes": entry.get("estimated_time_minutes"),
                        "planned_time_minutes": entry.get("planned_time_minutes"),
                    },
                    entry.get("mode", ""),
                    entry.get("profile"),
                    ts=entry.get("ts"),
                )
                cur = conn.execute(_INSERT_TASK_SQL, row)
                if cur.lastrowid and cur.rowcount > 0:
                    inserted += 1
        conn.commit()
    return inserted
