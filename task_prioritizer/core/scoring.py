"""Scoring functions and time estimation. Pure logic, no I/O."""

from __future__ import annotations

import math

from ..config import Config


def get_time_score(minutes: int) -> float:
    thresholds = Config.TIME_THRESHOLDS
    rating_map = Config.RATING_MAP
    if minutes <= thresholds['low']:
        return rating_map['0']
    elif minutes <= thresholds['med']:
        return rating_map['1']
    elif minutes <= thresholds['high']:
        return rating_map['2']
    else:
        return rating_map['3']


def estimate_time_minutes(r_complex: float, r_risk: float, r_surprise: float) -> int:
    """Estimate time based on complexity, risk, and surprise ratings. Rounds up to nearest 5 min."""
    base_times = {0.0: 15, 0.3: 45, 0.6: 90, 1.0: 180}
    base = base_times.get(r_complex, 45)
    risk_factor = 1 + r_risk * 0.3
    surprise_factor = 1 + r_surprise * 0.2
    raw_minutes = base * risk_factor * surprise_factor
    # Round up to next 5 minutes
    return math.ceil(raw_minutes / 5) * 5


def compute_impact(r_leverage: float, r_confidence: float, r_goals: float) -> float:
    w = Config.WEIGHTS['impact']
    return (r_leverage * w['leverage'] +
            r_confidence * w['confidence'] +
            r_goals * w['goals'])


def compute_urgency(r_priority: float, r_deadline: float) -> float:
    w = Config.WEIGHTS['urgency']
    return r_priority * w['priority'] + r_deadline * w['deadline']


def compute_execution(r_complex: float, r_time: float, r_risk: float, r_fun: float) -> float:
    w = Config.WEIGHTS['execution']
    return (r_complex * w['complex'] +
            r_time * w['time'] +
            r_risk * w['risk'] +
            r_fun * w['fun'])
