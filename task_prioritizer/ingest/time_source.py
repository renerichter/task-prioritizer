"""TimeSource protocol: any backend that can report minutes spent on a task."""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable


@runtime_checkable
class TimeSource(Protocol):
    """A pluggable backend for retrieving actual time spent on tasks."""

    def is_available(self) -> bool:
        """Return True if this source can serve queries right now."""
        ...

    def get_actual_minutes_for(
        self,
        task_text: str,
        since: date | None = None,
        until: date | None = None,
    ) -> list[int]:
        """Return all matching session durations (in minutes) for ``task_text``."""
        ...
