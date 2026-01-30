import os
from pathlib import Path
from typing import Dict, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

_loaded_profile: Optional[str] = None


def get_loaded_profile() -> Optional[str]:
    return _loaded_profile


def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _get_home_config_dir() -> Path:
    return Path.home() / ".config" / "task-prioritizer"


def _find_env_file(profile: Optional[str] = None) -> Path:
    project_root = _get_project_root()
    home_config = _get_home_config_dir()

    if profile:
        profile_file = project_root / f".env.{profile}"
        if profile_file.exists():
            return profile_file
        home_profile = home_config / f"{profile}.env"
        if home_profile.exists():
            return home_profile

    default_env = project_root / ".env"
    if default_env.exists():
        return default_env
    home_default = home_config / "default.env"
    if home_default.exists():
        return home_default

    return default_env


def is_first_run() -> bool:
    marker = _get_home_config_dir() / ".welcomed"
    return not marker.exists()


def mark_welcomed() -> None:
    config_dir = _get_home_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    marker = config_dir / ".welcomed"
    marker.touch()


def load_profile(profile: Optional[str] = None) -> None:
    global _loaded_profile
    env_path = _find_env_file(profile)
    if load_dotenv and env_path.exists():
        load_dotenv(env_path, override=True)
    _loaded_profile = profile
    Config.reload()


def _get_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _get_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


class Config:
    RATING_MAP: Dict[str, float] = {}
    DISPLAY_MAP: Dict[str, str] = {}
    WEIGHTS: Dict[str, Dict[str, float]] = {}
    TIME_THRESHOLDS: Dict[str, int] = {}
    THRESHOLD_IMPACT_3STAR: float = 0.75
    THRESHOLD_IMPACT_2STAR: float = 0.50
    THRESHOLD_IMPACT_1STAR: float = 0.25
    THRESHOLD_URGENCY_HIGH: float = 0.5
    THRESHOLD_EXECUTION_HIGH: float = 0.5
    THRESHOLD_SURPRISE: float = 0.5
    THRESHOLD_PLANNED: float = 0.5
    STOP_RULE_FACTOR: float = 1.5
    SYMBOLS: Dict[str, str] = {}
    ARCHETYPES: Dict[str, str] = {}
    # Demo mode configuration
    DEMO_TASK: str = "Demo task for automated testing"
    DEMO_RATINGS: str = "2,2,2,1,1,1,1,1,2,1,2"  # L,Conf,G,P,D,C,T,R,F,S,Pl

    @classmethod
    def reload(cls) -> None:
        cls.RATING_MAP = {
            '0': _get_float('RATING_0', 0.0),
            '1': _get_float('RATING_1', 0.3),
            '2': _get_float('RATING_2', 0.6),
            '3': _get_float('RATING_3', 1.0),
        }
        cls.DISPLAY_MAP = {k: str(v) for k, v in cls.RATING_MAP.items()}
        cls.WEIGHTS = {
            'impact': {
                'leverage': _get_float('WEIGHT_IMPACT_LEVERAGE', 0.5),
                'confidence': _get_float('WEIGHT_IMPACT_CONFIDENCE', 0.25),
                'goals': _get_float('WEIGHT_IMPACT_GOALS', 0.25),
            },
            'urgency': {
                'priority': _get_float('WEIGHT_URGENCY_PRIORITY', 0.5),
                'deadline': _get_float('WEIGHT_URGENCY_DEADLINE', 0.5),
            },
            'execution': {
                'complex': _get_float('WEIGHT_EXECUTION_COMPLEX', 0.4),
                'time': _get_float('WEIGHT_EXECUTION_TIME', 0.3),
                'risk': _get_float('WEIGHT_EXECUTION_RISK', 0.2),
                'fun': _get_float('WEIGHT_EXECUTION_FUN', 0.1),
            },
        }
        cls.TIME_THRESHOLDS = {
            'low': _get_int('TIME_THRESHOLD_LOW', 30),
            'med': _get_int('TIME_THRESHOLD_MED', 90),
            'high': _get_int('TIME_THRESHOLD_HIGH', 150),
        }
        cls.THRESHOLD_IMPACT_3STAR = _get_float('THRESHOLD_IMPACT_3STAR', 0.75)
        cls.THRESHOLD_IMPACT_2STAR = _get_float('THRESHOLD_IMPACT_2STAR', 0.50)
        cls.THRESHOLD_IMPACT_1STAR = _get_float('THRESHOLD_IMPACT_1STAR', 0.25)
        cls.THRESHOLD_URGENCY_HIGH = _get_float('THRESHOLD_URGENCY_HIGH', 0.5)
        cls.THRESHOLD_EXECUTION_HIGH = _get_float('THRESHOLD_EXECUTION_HIGH', 0.5)
        cls.THRESHOLD_SURPRISE = _get_float('THRESHOLD_SURPRISE', 0.5)
        cls.THRESHOLD_PLANNED = _get_float('THRESHOLD_PLANNED', 0.5)
        cls.STOP_RULE_FACTOR = _get_float('STOP_RULE_FACTOR', 1.5)
        cls.SYMBOLS = {
            'urgency_high': '🚨',
            'urgency_low': '🐢',
            'execution_high': '🥵',
            'execution_low': '🍭',
            'planned_yes': '🗓️',
            'planned_no': '🎲',
            'surprise': '🎁',
            'star': '⭐️',
        }
        cls.ARCHETYPES = {
            'quick_win': os.environ.get('ARCHETYPE_QUICK_WIN', "High leverage for low friction—a pure Quick Win."),
            'big_bet': os.environ.get('ARCHETYPE_BIG_BET', "High value, but demanding. Schedule deep work for this."),
            'filler': os.environ.get('ARCHETYPE_FILLER', "Easy, but low leverage. Good for low-energy blocks."),
            'slog': os.environ.get('ARCHETYPE_SLOG', "Hard work for little return. Can you eliminate or automate?"),
        }
        # Demo mode configuration (for automated testing by agents)
        cls.DEMO_TASK = os.environ.get('DEMO_TASK', "Demo task for automated testing")
        cls.DEMO_RATINGS = os.environ.get('DEMO_RATINGS', "2,2,2,1,1,1,1,1,2,1,2")

    @classmethod
    def validate(cls) -> list:
        errors = []
        impact_sum = (
            cls.WEIGHTS['impact']['leverage'] +
            cls.WEIGHTS['impact']['confidence'] +
            cls.WEIGHTS['impact']['goals']
        )
        if abs(impact_sum - 1.0) > 0.01:
            errors.append(f"Impact weights must sum to 1.0, got {impact_sum:.2f}")
        urgency_sum = cls.WEIGHTS['urgency']['priority'] + cls.WEIGHTS['urgency']['deadline']
        if abs(urgency_sum - 1.0) > 0.01:
            errors.append(f"Urgency weights must sum to 1.0, got {urgency_sum:.2f}")
        exec_sum = sum(cls.WEIGHTS['execution'].values())
        if abs(exec_sum - 1.0) > 0.01:
            errors.append(f"Execution weights must sum to 1.0, got {exec_sum:.2f}")
        return errors


load_profile(None)


def get_config() -> type:
    return Config
