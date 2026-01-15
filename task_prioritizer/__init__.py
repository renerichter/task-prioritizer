from typing import TYPE_CHECKING

from .config import Config, get_config, load_profile, is_first_run, mark_welcomed

_MAIN_EXPORTS = [
    "parse_task",
    "get_time_score",
    "compute_impact",
    "compute_urgency",
    "compute_execution",
    "get_impact_symbol",
    "get_urgency_symbol",
    "get_execution_symbol",
    "get_surprise_symbol",
    "get_planned_symbol",
    "format_output",
    "parse_ratings",
    "run_with_ratings",
    "copy_to_clipboard",
    "colorize_output",
]
_MAIN_EXPORTS_SET = set(_MAIN_EXPORTS)

if TYPE_CHECKING:
    from . import main as _main  # noqa: F401

__version__ = "2.1.0"
__all__ = [
    "Config",
    "get_config",
    "load_profile",
    "is_first_run",
    "mark_welcomed",
    *_MAIN_EXPORTS,
]


def __getattr__(name):
    if name in _MAIN_EXPORTS_SET:
        from . import main as _main
        return getattr(_main, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
