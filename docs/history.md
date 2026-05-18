# History & Storage

Task-prioritizer dual-writes every scored task to:

1. **JSONL** (`tasks.log`) — canonical, append-only audit log.
2. **SQLite** (`tasks.db`) — query store for trends and the estimate suggester.

JSONL is the source of truth. SQLite is rebuildable from it.

## Paths

| Store | Env var | Default |
|-------|---------|---------|
| JSONL | `TASK_PRIORITIZER_LOG_PATH` | `$XDG_DATA_HOME/task-prioritizer/tasks.log` (falls back to `~/.local/share/task-prioritizer/tasks.log`) |
| SQLite | `TASK_PRIORITIZER_HISTORY_DB` | `$XDG_DATA_HOME/task-prioritizer/tasks.db` (same fallback) |

## Schema (v1)

```sql
CREATE TABLE tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  input TEXT NOT NULL,
  mode TEXT NOT NULL,
  profile TEXT,
  -- 12 raw ratings
  rating_L REAL, rating_Conf REAL, rating_G REAL,
  rating_P REAL, rating_D REAL,
  rating_C REAL, rating_T REAL, rating_R REAL, rating_F REAL,
  rating_S REAL, rating_Pl REAL, rating_Rec REAL,
  -- 3 scores
  score_impact REAL, score_urgency REAL, score_execution REAL,
  -- time + quadrant
  estimated_minutes INTEGER,
  planned_minutes INTEGER,
  quadrant TEXT,
  UNIQUE(ts, input)
);

CREATE TABLE actuals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  ts TEXT NOT NULL,
  minutes INTEGER NOT NULL,
  source TEXT
);

CREATE TABLE schema_version (
  version INTEGER PRIMARY KEY
);
```

`UNIQUE(ts, input)` makes the JSONL → SQLite migration **idempotent**:
re-running `migrate_from_jsonl()` never duplicates rows.

## Public API

```python
from task_prioritizer.persistence import history

history.init_db()                     # idempotent
task_id = history.record_task(...)    # called automatically by log_task
history.record_actual(task_id, minutes, source="clockify")
history.recent_tasks(limit=20)        # list[dict]
history.tasks_with_actuals()          # → used by estimate_suggester
history.migrate_from_jsonl()          # one-shot rebuild
```

## Dual-Write Behavior

`log_task()` in `persistence/log.py`:

1. Appends JSON line to `tasks.log`. Failure → traceback (canonical store must not silently fail).
2. Calls `history.record_task()`. Failure → stderr warning, no traceback (query store is rebuildable).

This is by design: never break the user's flow over a corrupt SQLite
file. The JSONL is always recoverable.

## Estimate Suggester

`core/estimate_suggester.py:suggest_estimate(text)`:

- Tokenizes `text` (lowercase, drops `{…}` tags, stop words, words <3 chars).
- Loads `history.tasks_with_actuals()`.
- Keeps candidates with Jaccard similarity ≥ 0.30.
- Returns median actual minutes (rounded to nearest 5), plus a
  proof bundle (`similar_tasks` + `explanation`).
- Returns `None` when no usable history exists.

This is **deterministic** — no LLM, no fuzzy match library.

## Migrating Old Logs

```bash
python -c "from task_prioritizer.persistence.history import migrate_from_jsonl; print(migrate_from_jsonl())"
```

Prints the number of rows inserted.
