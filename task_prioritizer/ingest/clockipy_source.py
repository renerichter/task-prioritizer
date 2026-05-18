"""Clockipy adapter for TimeSource.

Decoupled from the actual ``clockipy`` package: takes any client object
that exposes ``get_time_entries(start_date, end_date) -> list[dict]``.
That signature matches ``clockipy.api.client.ClockifyClient`` but does
not import it, so tests can pass a mock and the adapter degrades to
``is_available() == False`` when no client is provided.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

_ISO_DURATION = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")


def _parse_iso_duration_to_minutes(iso: str) -> int:
    m = _ISO_DURATION.match(iso or "")
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 60 + mins + (1 if s >= 30 else 0)


def _entry_duration_minutes(entry: dict[str, Any]) -> int:
    if "duration_minutes" in entry:
        return int(entry["duration_minutes"])
    interval = entry.get("timeInterval", {})
    iso = interval.get("duration", "")
    return _parse_iso_duration_to_minutes(iso)


def _entry_description(entry: dict[str, Any]) -> str:
    return str(entry.get("description") or "")


class ClockipyTimeSource:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def is_available(self) -> bool:
        return self._client is not None

    def get_actual_minutes_for(
        self,
        task_text: str,
        since: date | None = None,
        until: date | None = None,
    ) -> list[int]:
        if not self.is_available():
            return []
        since = since or (date.today() - timedelta(days=90))
        until = until or date.today()
        try:
            entries = self._client.get_time_entries(since, until)
        except Exception:
            return []
        needle = task_text.lower()
        out: list[int] = []
        for entry in entries or []:
            if needle in _entry_description(entry).lower():
                minutes = _entry_duration_minutes(entry)
                if minutes > 0:
                    out.append(minutes)
        return out
