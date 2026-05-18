"""Stop-rule: when actual time exceeds estimated × STOP_RULE_FACTOR, pause.

Returns a structured ``StopRuleResult`` so the CLI/TUI layer decides how
to surface it (Phase 4.6 will hook this into the history-driven flow).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Config


@dataclass(frozen=True)
class StopRuleResult:
    triggered: bool
    ratio: float
    factor: float
    estimated_minutes: int
    actual_minutes: int
    message: str


def check_stop_rule(
    estimated_minutes: int | None,
    actual_minutes: int | None,
    factor: float | None = None,
) -> StopRuleResult | None:
    """Compare actual vs estimated; return a result iff the threshold is met.

    Returns ``None`` (no trigger, no error) when the comparison is not
    meaningful — e.g. no estimate, no actual, or zero estimate. The tool
    stays calm: missing data is not a failure.
    """
    if not estimated_minutes or not actual_minutes:
        return None
    if estimated_minutes <= 0:
        return None
    factor = factor if factor is not None else Config.STOP_RULE_FACTOR
    ratio = actual_minutes / estimated_minutes
    if ratio < factor:
        return None
    message = (
        f"Stop and reflect — actual {actual_minutes}m is {ratio:.2f}× your "
        f"estimate of {estimated_minutes}m (threshold {factor:.2f}×). "
        f"Why did it take longer? What would have fit?"
    )
    return StopRuleResult(
        triggered=True,
        ratio=ratio,
        factor=factor,
        estimated_minutes=estimated_minutes,
        actual_minutes=actual_minutes,
        message=message,
    )
