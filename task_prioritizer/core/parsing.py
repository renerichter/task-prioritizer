"""Task-string and ratings parsing. Pure logic."""

from __future__ import annotations

import re

from ..config import Config
from .scoring import get_time_score


def _strip_leading_symbols(task_str: str) -> str:
    symbols = [
        Config.SYMBOLS['star'],
        Config.SYMBOLS['surprise'],
        Config.SYMBOLS['planned_yes'],
        Config.SYMBOLS['planned_no'],
        Config.SYMBOLS['recurrent'],
        "--",
        "-",
    ]
    cleaned = task_str.lstrip()
    changed = True
    while cleaned and changed:
        changed = False
        for token in symbols:
            if cleaned.startswith(token):
                cleaned = cleaned[len(token):].lstrip()
                changed = True
                break
    return cleaned


def parse_task(task_str: str) -> tuple[str, str, int | None]:
    task_str = _strip_leading_symbols(task_str)
    tag_pattern = re.compile(r'^(\s*\{[^}]+\})+')
    match = tag_pattern.match(task_str)

    existing_tags = ""
    clean_text = task_str

    if match:
        existing_tags = match.group(0).strip()
        clean_text = task_str[match.end():].strip()

    time_pattern = re.compile(r'\{p(\d+):(\d{2})\}')
    time_match = time_pattern.search(task_str)

    planned_minutes = None
    if time_match:
        h = int(time_match.group(1))
        m = int(time_match.group(2))
        planned_minutes = h * 60 + m

    return existing_tags, clean_text, planned_minutes


def parse_ratings(ratings_str: str, planned_mins: int | None = None) -> list[float] | None:
    parts = ratings_str.replace(" ", "").split(",")
    if len(parts) not in (11, 12):
        return None
    try:
        ratings = []
        for i, p in enumerate(parts):
            if p == "_" and i == 6 and planned_mins is not None:
                ratings.append(get_time_score(planned_mins))
            elif p in Config.RATING_MAP:
                ratings.append(Config.RATING_MAP[p])
            else:
                return None
        if len(ratings) == 11:
            ratings.append(0.0)
        return ratings
    except (ValueError, KeyError):
        return None
