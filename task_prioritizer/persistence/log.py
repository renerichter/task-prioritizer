"""JSONL task log: path resolution and append-only write."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def _get_log_path() -> Path:
    """Resolve the JSONL log path with portable precedence.

    Order:
      1. ``TASK_PRIORITIZER_LOG_PATH`` (explicit override).
      2. ``$XDG_DATA_HOME/task-prioritizer/tasks.log``.
      3. ``$HOME/.local/share/task-prioritizer/tasks.log``.

    The parent directory is created if missing. We deliberately do *not*
    fall back to a repo-relative path so that ``tp`` installed globally
    writes to a stable, user-owned location regardless of cwd.
    """
    override = os.environ.get("TASK_PRIORITIZER_LOG_PATH")
    if override:
        path = Path(override).expanduser()
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
        path = base / "task-prioritizer" / "tasks.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log_task(task_input: str, result: dict, mode: str, profile: str | None = None) -> None:
    """Log task to JSONL file.

    Failures are reported on stderr rather than silently swallowed; losing
    a row without notice would undermine the history features that depend
    on this log.
    """
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "input": task_input,
        "ratings": result.get('ratings', {}),
        "scores": result.get('scores', {}),
        "symbols": result.get('symbols', {}),
        "output": result.get('output', ''),
        "estimated_time_minutes": result.get('estimated_time_minutes'),
        "planned_time_minutes": result.get('planned_time_minutes'),
        "mode": mode,
        "profile": profile,
        "analysis": result.get('analysis', ''),
        "quadrant": result.get('quadrant', ''),
    }
    try:
        log_path = _get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(
            f"warning: could not append task to log ({exc.__class__.__name__}: {exc})",
            file=sys.stderr,
        )

    # Dual-write to SQLite history store (Phase 4.6). Failures are
    # reported but never block the JSONL write above.
    try:
        from . import history
        history.record_task(task_input, result, mode, profile, ts=entry["ts"])
    except Exception as exc:  # pragma: no cover - defensive
        print(
            f"warning: could not write history db ({exc.__class__.__name__}: {exc})",
            file=sys.stderr,
        )
