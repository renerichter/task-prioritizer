"""Manual / in-memory TimeSource used as fallback and in tests."""

from __future__ import annotations

from datetime import date


class ManualTimeSource:
    def __init__(self, data: dict[str, list[int]] | None = None) -> None:
        self._data: dict[str, list[int]] = dict(data) if data else {}

    def is_available(self) -> bool:
        return True

    def record(self, task_text: str, minutes: int) -> None:
        self._data.setdefault(task_text, []).append(minutes)

    def get_actual_minutes_for(
        self,
        task_text: str,
        since: date | None = None,
        until: date | None = None,
    ) -> list[int]:
        return list(self._data.get(task_text, []))
