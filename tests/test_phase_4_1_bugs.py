"""Regression tests for Phase 4.1 bug-fix sweep.

These tests pin down the four bugs surfaced by the deep-qa audit:

1. .env.example schema drift (declared keys do not match Config.WEIGHTS).
2. _get_log_path() is repo-relative, breaks for installed `tp` binaries.
3. log_task swallows every exception silently.
4. log_task never persists the `analysis` field; Rec missing in older entries.

Written red-first per project AGENTS.md TDD mandate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from task_prioritizer.config import Config
from task_prioritizer.main import _get_log_path, log_task

# ---------------------------------------------------------------------------
# Bug 1: .env.example must match Config schema
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


# Every config key consumed by config.py. Keep in sync with Config.reload().
KNOWN_CONFIG_KEYS = {
    "RATING_0", "RATING_1", "RATING_2", "RATING_3",
    "WEIGHT_IMPACT_LEVERAGE", "WEIGHT_IMPACT_CONFIDENCE", "WEIGHT_IMPACT_GOALS",
    "WEIGHT_URGENCY_PRIORITY", "WEIGHT_URGENCY_DEADLINE",
    "WEIGHT_EXECUTION_COMPLEX", "WEIGHT_EXECUTION_TIME",
    "WEIGHT_EXECUTION_RISK", "WEIGHT_EXECUTION_FUN",
    "TIME_THRESHOLD_LOW", "TIME_THRESHOLD_MED", "TIME_THRESHOLD_HIGH",
    "THRESHOLD_IMPACT_3STAR", "THRESHOLD_IMPACT_2STAR", "THRESHOLD_IMPACT_1STAR",
    "THRESHOLD_URGENCY_HIGH", "THRESHOLD_EXECUTION_HIGH",
    "THRESHOLD_SURPRISE", "THRESHOLD_PLANNED", "THRESHOLD_RECURRENT",
    "STOP_RULE_FACTOR",
    "ARCHETYPE_QUICK_WIN", "ARCHETYPE_BIG_BET",
    "ARCHETYPE_FILLER", "ARCHETYPE_SLOG",
    "DEMO_TASK", "DEMO_RATINGS",
}


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def test_env_example_keys_are_all_known():
    """Every key in .env.example must be consumed by config.py.
    Unknown keys mean copy-paste produces a silently-broken config."""
    example = _project_root() / ".env.example"
    assert example.exists(), ".env.example missing"
    declared = set(_parse_env_file(example))
    unknown = declared - KNOWN_CONFIG_KEYS
    assert not unknown, (
        f".env.example declares unknown keys (not consumed by Config): {sorted(unknown)}. "
        "Either fix the example or wire the key into config.py."
    )


def test_env_example_impact_weights_are_complete():
    """If .env.example overrides any IMPACT weight, it must override all 3
    so the visible weight set is internally coherent."""
    declared = set(_parse_env_file(_project_root() / ".env.example"))
    impact_keys = {"WEIGHT_IMPACT_LEVERAGE", "WEIGHT_IMPACT_CONFIDENCE", "WEIGHT_IMPACT_GOALS"}
    if declared & impact_keys:
        missing = impact_keys - declared
        assert not missing, f".env.example impact weights incomplete: missing {sorted(missing)}"


def test_env_example_loads_into_valid_config(monkeypatch):
    """Copying .env.example should produce a Config that passes validate()."""
    example = _project_root() / ".env.example"

    for k in list(os.environ):
        if k.startswith(("WEIGHT_", "RATING_", "THRESHOLD_", "TIME_",
                         "STOP_RULE_", "DEMO_", "ARCHETYPE_")):
            monkeypatch.delenv(k, raising=False)

    for k, v in _parse_env_file(example).items():
        monkeypatch.setenv(k, v)

    Config.reload()
    errors = Config.validate()
    assert errors == [], f".env.example produces invalid Config: {errors}"


# ---------------------------------------------------------------------------
# Bug 2: log path must respect XDG, not repo location
# ---------------------------------------------------------------------------


def test_log_path_respects_explicit_override(monkeypatch, tmp_path):
    monkeypatch.setenv("TASK_PRIORITIZER_LOG_PATH", str(tmp_path / "custom.log"))
    assert _get_log_path() == tmp_path / "custom.log"


def test_log_path_uses_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.delenv("TASK_PRIORITIZER_LOG_PATH", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    path = _get_log_path()
    assert path == tmp_path / "task-prioritizer" / "tasks.log"
    assert path.parent.is_dir()


def test_log_path_falls_back_to_local_share(monkeypatch, tmp_path):
    monkeypatch.delenv("TASK_PRIORITIZER_LOG_PATH", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    path = _get_log_path()
    assert path == tmp_path / ".local" / "share" / "task-prioritizer" / "tasks.log"
    assert path.parent.is_dir()


# ---------------------------------------------------------------------------
# Bug 3 + 4: log_task must persist analysis + Rec, and not silently lose data
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_log(monkeypatch, tmp_path):
    log = tmp_path / "tasks.log"
    monkeypatch.setenv("TASK_PRIORITIZER_LOG_PATH", str(log))
    return log


def _sample_result() -> dict:
    return {
        "output": "⭐️-- task",
        "urgency_sym": "🐢",
        "execution_sym": "🍭",
        "has_surprise": False,
        "scores": {"impact": 0.5, "urgency": 0.3, "execution": 0.2},
        "ratings": {
            "L": 0.6, "Conf": 0.6, "G": 0.3,
            "P": 0.3, "D": 0.3,
            "C": 0.3, "T": 0.0, "R": 0.0, "F": 0.0,
            "S": 0.0, "Pl": 0.6, "Rec": 0.0,
        },
        "symbols": {
            "impact": "⭐️", "urgency": "🐢", "execution": "🍭",
            "surprise": "", "planned": "🗓️", "recurrent": "",
        },
        "estimated_time_minutes": 30,
        "planned_time_minutes": None,
        "analysis": "Easy, but low leverage. Good for low-energy blocks.",
    }


def test_log_task_persists_analysis_field(isolated_log):
    log_task("sample", _sample_result(), mode="inline", profile=None)
    entry = json.loads(isolated_log.read_text().strip())
    assert "analysis" in entry, "analysis must be persisted (AGENTS.md schema)"
    assert entry["analysis"].startswith("Easy")


def test_log_task_persists_rec_rating(isolated_log):
    log_task("sample", _sample_result(), mode="inline", profile=None)
    entry = json.loads(isolated_log.read_text().strip())
    assert "Rec" in entry["ratings"], "Rec rating must be present per AGENTS.md schema"


def test_log_task_surfaces_write_failures(monkeypatch, capsys, tmp_path):
    """Silent `except Exception: pass` is a data-loss footgun. Write failures
    must reach stderr so the user can react (skill: 'graceful, never silent')."""
    bad_path = tmp_path / "does" / "not" / "exist" / "and-parent-is-file.log"
    # Make the parent a file, so mkdir(parents=True) cannot create it.
    (tmp_path / "does").write_text("not a dir")
    monkeypatch.setenv("TASK_PRIORITIZER_LOG_PATH", str(bad_path))

    log_task("sample", _sample_result(), mode="inline", profile=None)
    captured = capsys.readouterr()
    assert "log" in (captured.err.lower() + captured.out.lower()), \
        "log_task must announce write failure, not swallow silently"
