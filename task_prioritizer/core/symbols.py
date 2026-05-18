"""Symbol selection and output formatting. Pure logic."""

from __future__ import annotations

from ..config import Config


def get_impact_symbol(score: float) -> str:
    star = Config.SYMBOLS['star']
    if score > Config.THRESHOLD_IMPACT_3STAR:
        return star * 3
    elif score > Config.THRESHOLD_IMPACT_2STAR:
        return star * 2
    elif score > Config.THRESHOLD_IMPACT_1STAR:
        return star
    return ""


def get_urgency_symbol(score: float) -> str:
    if score >= Config.THRESHOLD_URGENCY_HIGH:
        return Config.SYMBOLS['urgency_high']
    return Config.SYMBOLS['urgency_low']


def get_execution_symbol(score: float) -> str:
    if score >= Config.THRESHOLD_EXECUTION_HIGH:
        return Config.SYMBOLS['execution_high']
    return Config.SYMBOLS['execution_low']


def get_surprise_symbol(rating: float) -> str:
    if rating >= Config.THRESHOLD_SURPRISE:
        return Config.SYMBOLS['surprise']
    return ""


def get_planned_symbol(rating: float) -> str:
    if rating >= Config.THRESHOLD_PLANNED:
        return Config.SYMBOLS['planned_yes']
    return Config.SYMBOLS['planned_no']


def get_recurrent_symbol(rating: float) -> str:
    if rating >= Config.THRESHOLD_RECURRENT:
        return Config.SYMBOLS['recurrent']
    return ""


def format_output(impact_sym: str, surprise_sym: str, planned_sym: str, recurrent_sym: str,
                  tags: str, text: str) -> str:
    # Format: Impact - Surprise/Recurrent - Planned
    # Example: ⭐️⭐️⭐️-🎁🔁-🗓️
    # Example: --🗓️
    final_prefix = f"{impact_sym}-{surprise_sym}{recurrent_sym}-{planned_sym}"

    if tags:
        return f"{final_prefix}{tags} {text}"
    return f"{final_prefix} {text}"
