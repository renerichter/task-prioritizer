"""Decision-Matrix: classify (urgency × execution) into FAQ quadrants.

FAQ Decision-Matrix:
                 🚨 urgent          🐢 calm
    🍭 simple    do now             add to schedule
    🥵 complex   break down & prio  trash OR spare-time
"""

from __future__ import annotations

from ..config import Config

QUADRANTS: dict[str, str] = {
    "urgent_simple": "Do now — urgent and simple.",
    "urgent_complex": "Break down and schedule with priority — urgent and complex.",
    "calm_simple": "Add to schedule — non-urgent and simple.",
    "calm_complex": "Trash or do in spare-time — non-urgent and complex.",
}


def classify_quadrant(urgency_symbol: str, execution_symbol: str) -> str:
    """Map (urgency_symbol, execution_symbol) → quadrant key.

    Uses canonical FAQ symbols 🚨/🐢 and 🍭/🥵 read from Config.SYMBOLS.
    """
    urgent = urgency_symbol == Config.SYMBOLS["urgency_high"]
    complex_ = execution_symbol == Config.SYMBOLS["execution_high"]
    if urgent and not complex_:
        return "urgent_simple"
    if urgent and complex_:
        return "urgent_complex"
    if not urgent and not complex_:
        return "calm_simple"
    return "calm_complex"


def quadrant_recommendation(quadrant_key: str) -> str:
    """Return the human-readable recommendation for a quadrant."""
    return QUADRANTS.get(quadrant_key, "")
