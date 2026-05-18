"""Deterministic analysis text generator."""

from __future__ import annotations

from ..config import Config


def get_analysis_text(s_impact: float, s_execution: float, s_urgency: float, r_surprise: float) -> str:
    """
    Generates a deterministic summary sentence based on scores.
    Logic: [Prefix: Clarity] + [Core: Impact vs Execution] + [Suffix: Urgency]
    """
    # 1. Prefix: Clarity
    prefix = ""
    if r_surprise >= Config.THRESHOLD_SURPRISE:
        prefix = "Scope is unclear (🎁). "

    # 2. Core: Archetype (Impact vs Execution)
    # Thresholds: Impact 0.5 (medium), Execution 0.5 (medium)
    high_impact = s_impact > 0.5
    high_execution = s_execution > 0.5

    if high_impact and not high_execution:
        core = Config.ARCHETYPES['quick_win']
    elif high_impact and high_execution:
        core = Config.ARCHETYPES['big_bet']
    elif not high_impact and not high_execution:
        core = Config.ARCHETYPES['filler']
    else:  # Low impact, high execution
        core = Config.ARCHETYPES['slog']

    # 3. Suffix: Urgency
    suffix = ""
    if s_urgency >= Config.THRESHOLD_URGENCY_HIGH:
        suffix = " Critical priority."

    return f"{prefix}{core}{suffix}"
