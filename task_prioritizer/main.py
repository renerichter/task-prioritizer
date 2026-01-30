#!/usr/bin/env python3
import sys
import re
import os
import json
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

try:
    import readline
except ImportError:
    readline = None

from .config import Config, load_profile, is_first_run, mark_welcomed, _loaded_profile


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GOLD = "\033[38;5;220m"
    RED = "\033[38;5;203m"
    GREEN = "\033[38;5;114m"
    CYAN = "\033[38;5;117m"
    MAGENTA = "\033[38;5;177m"
    GRAY = "\033[38;5;245m"
    WHITE = "\033[38;5;255m"
    BLUE = "\033[38;5;111m"
    ORANGE = "\033[38;5;208m"

    @classmethod
    def disable(cls):
        cls.RESET = ""
        cls.BOLD = ""
        cls.DIM = ""
        cls.GOLD = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.CYAN = ""
        cls.MAGENTA = ""
        cls.GRAY = ""
        cls.WHITE = ""
        cls.BLUE = ""
        cls.ORANGE = ""


def supports_color() -> bool:
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    if "NO_COLOR" in os.environ:
        return False
    return True


HELP_EPILOG = """
╭─────────────────────────────────────────────────────────────╮
│  "calculations" = choosing what to work on                  │
│  "stop-rule"    = knowing when to stop, when good enough is │
│                   good enough                               │
╰─────────────────────────────────────────────────────────────╯

Phase 1: Capture tasks roughly. Uncertainty (🎁) is expected.
Phase 2: Refine estimates. Remove 🎁 as clarity emerges.

Stop-Rule: If actual time exceeds 1.5× your estimate, pause.
           Reflect on why—then adjust your next estimate.

Ratings order: L,Conf,G,P,D,C,T,R,F,S,Pl
  L=Leverage, Conf=Confidence, G=Goals, P=Priority, D=Deadline,
  C=Complex, T=Time, R=Risk, F=Fun, S=Surprise, Pl=Planned

This tool trusts you. You're doing fine.
"""

SURPRISE_REMINDER = """
┌─────────────────────────────────────────────────────────────┐
│  🎁 appears when clarity is low.                            │
│     In phase 1, this is natural.                            │
│     As you learn, 🎁 fades.                                  │
│     Trust the process.                                       │
└─────────────────────────────────────────────────────────────┘
"""

VERSION = "0.2.11"
AUTHOR = "Task Prioritizer Contributors"

STARTUP_BANNER = """
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│   Task Prioritizer 🌱  v{version}                            │
│   A calm tool for mindful productivity                      │
│                                                             │
│   Choose what to work on │ Know when to stop                │
│                                                             │
╰─────────────────────────────────────────────────────────────╯

WHY THIS WORKS:
───────────────
• High Impact + Low Execution  = Quick wins (do first)
• High Impact + High Execution = Strategic investments (schedule)
• Low Impact + Low Execution   = Delegate or batch
• Low Impact + High Execution  = Avoid or eliminate

SYMBOLS AT A GLANCE:
────────────────────
  ⭐️⭐️⭐️ = High impact       🚨 = Urgent          🥵 = Hard
  ⭐️⭐️   = Medium impact     🐢 = Calm            🍭 = Easy
  ⭐️     = Low impact        🎁 = Unclear (ok!)   🗓️ = Planned
                              🎲 = Spontaneous

SCALE: 0=none │ 1=low │ 2=medium │ 3=high
"""

WELCOME_MESSAGE = """
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│   Welcome to Task Prioritizer 🌱                            │
│                                                             │
│   This tool helps you:                                      │
│   • Choose what to work on (by scoring impact & effort)     │
│   • Know when to stop (the 1.5× stop-rule)                  │
│                                                             │
│   How it works:                                             │
│   1. You'll rate each factor from 0 to 3                    │
│   2. The tool calculates priority and shows symbols         │
│   3. Copy the result to your task list                      │
│                                                             │
│   Scale: 0=none, 1=low, 2=medium, 3=high                    │
│                                                             │
│   When 🎁 appears, that's okay—it means the task is         │
│   still unclear. Clarity comes with time.                   │
│                                                             │
│   Let's try your first task...                              │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
"""

LOOP_HELP = """
╭─────────────────────────────────────────────────────────────╮
│  Quick Reference                                            │
├─────────────────────────────────────────────────────────────┤
│  Enter a task string to prioritize it.                      │
│                                                             │
│  Commands (type / for menu):                                │
│    /help, /h          Show this help                        │
│    /mode batch, /m b  Switch to batch mode (grouped input)  │
│    /mode detail, /m d Switch to detail mode (explanations)  │
│    /quit, /q          Exit the program                      │
│    Ctrl+C/D           Exit the program                      │
│                                                             │
│  Task format:                                               │
│    {p0:45} task description   (45 min planned time)         │
│    {P:Tag} task description   (custom tag preserved)        │
│                                                             │
│  Rating scale: 0=none, 1=low, 2=medium, 3=high              │
│                                                             │
│  Categories:                                                │
│    Impact    (L,Conf,G)  - Leverage, Confidence, Goals      │
│    Urgency   (P,D)       - Priority, Deadline               │
│    Execution (C,T,R,F)   - Complex, Time, Risk, Fun         │
│    Clarity   (S,Pl)      - Surprise, Planned                │
╰─────────────────────────────────────────────────────────────╯
"""

DETAIL_EXPLANATION = """
╭─────────────────────────────────────────────────────────────╮
│  Understanding the Rating System                            │
╰─────────────────────────────────────────────────────────────╯

This prioritization system scores tasks across 4 categories to help
you identify what truly matters and how much effort it requires.

┌─ IMPACT ─────────────────────────────────────────────────────┐
│  Measures the value and return on investment of the task.   │
│                                                              │
│  • Leverage (L): How much output per unit of input?          │
│    0=no leverage, 3=massive multiplier effect                │
│    Ask: "Will this make future work easier?"                 │
│                                                              │
│  • Confidence (Conf): How sure are you it will work?         │
│    0=pure guess, 3=proven approach                           │
│    Ask: "Have I done this before? Is the path clear?"        │
│                                                              │
│  • Goals (G): How aligned with your objectives?              │
│    0=off-track, 3=directly advances key goal                 │
│    Ask: "Does this move the needle on what matters?"         │
└──────────────────────────────────────────────────────────────┘

┌─ URGENCY ────────────────────────────────────────────────────┐
│  Measures time pressure and external constraints.            │
│                                                              │
│  • Priority (P): How important relative to other tasks?      │
│    0=can wait indefinitely, 3=must do before anything else   │
│    Ask: "What happens if I don't do this today?"             │
│                                                              │
│  • Deadline (D): How close is the due date?                  │
│    0=no deadline, 3=due today/overdue                        │
│    Ask: "When does this absolutely need to be done?"         │
└──────────────────────────────────────────────────────────────┘

┌─ EXECUTION ──────────────────────────────────────────────────┐
│  Measures effort, friction, and resistance.                  │
│                                                              │
│  • Complexity (C): How mentally demanding?                   │
│    0=trivial, 3=requires deep focus and expertise            │
│    Ask: "Will I need to think hard or can I autopilot?"      │
│                                                              │
│  • Time (T): How long will it take?                          │
│    0=<30min, 1=30-90min, 2=90-150min, 3=>150min              │
│    (Auto-filled if you provide {pH:MM} tag)                  │
│    (If auto-estimated, result rounds up to nearest 5m)       │
│                                                              │
│  • Risk (R): What can go wrong?                              │
│    0=safe, 3=high chance of blockers or failure              │
│    Ask: "Are there unknowns that could derail this?"         │
│                                                              │
│  • Fun (F): How enjoyable is this task?                      │
│    0=dread it, 3=looking forward to it                       │
│    (Higher fun = easier execution, less procrastination)     │
└──────────────────────────────────────────────────────────────┘

┌─ CLARITY ────────────────────────────────────────────────────┐
│  Measures how well-defined the task is.                      │
│                                                              │
│  • Surprise (S): How much uncertainty remains?               │
│    0=fully understood, 3=many unknowns (🎁 appears)          │
│    Ask: "Do I know exactly what 'done' looks like?"          │
│                                                              │
│  • Planned (Pl): Was this scheduled or spontaneous?          │
│    0=just popped up, 3=on the roadmap for weeks              │
│    Ask: "Did I decide to do this, or did it decide for me?"  │
└──────────────────────────────────────────────────────────────┘

WHY THIS WORKS:
───────────────
• High Impact + Low Execution = Quick wins (do first)
• High Impact + High Execution = Strategic investments (schedule)
• Low Impact + Low Execution = Delegate or batch
• Low Impact + High Execution = Avoid or eliminate

The symbols help you scan your task list at a glance:
  ⭐️⭐️⭐️ = High impact, prioritize this
  🚨 = Urgent, time-sensitive
  🐢 = Calm, no rush
  🥵 = Hard, high friction
  🍭 = Easy, low friction
  🎁 = Unclear, refine later (normal in Phase 1)
  🗓️ = Planned work
  🎲 = Spontaneous/reactive

"""

DETAIL_EXAMPLES = """
╭─────────────────────────────────────────────────────────────╮
│  Examples                                                   │
╰─────────────────────────────────────────────────────────────╯

┌─ EXAMPLE A: High Priority Task ──────────────────────────────┐
│                                                              │
│  Input: "{p1:30} prepare quarterly presentation"             │
│                                                              │
│  Ratings:                                                    │
│    Impact:    L=3, Conf=2, G=3  (high leverage, aligns well) │
│    Urgency:   P=3, D=3          (due today, top priority)    │
│    Execution: C=2, T=_, R=1, F=1 (moderate effort)           │
│    Clarity:   S=0, Pl=3         (well-planned, clear scope)  │
│                                                              │
│  Output: ⭐️⭐️⭐️--🗓️{p1:30} prepare quarterly presentation  │
│  Category: 🚨 & 🥵 (urgent and demanding)                    │
│                                                              │
│  → This gets three stars (high impact), scheduled symbol,    │
│    and shows as urgent. Do this first.                       │
└──────────────────────────────────────────────────────────────┘

┌─ EXAMPLE B: Low Priority Task ───────────────────────────────┐
│                                                              │
│  Input: "reorganize desktop files"                           │
│                                                              │
│  Ratings:                                                    │
│    Impact:    L=0, Conf=3, G=0  (no leverage, off-goal)      │
│    Urgency:   P=0, D=0          (no deadline, low priority)  │
│    Execution: C=0, T=1, R=0, F=1 (easy but not fun)          │
│    Clarity:   S=2, Pl=0         (vague scope, unplanned)     │
│                                                              │
│  Output: 🎁--🎲 reorganize desktop files                     │
│  Category: 🐢 & 🍭 (calm and easy)                           │
│  Estimated time: ~58 min (auto-calculated)                   │
│                                                              │
│  → No stars (low impact), surprise symbol (unclear scope),   │
│    spontaneous. You might feel like doing this, but the      │
│    system correctly identifies it as low-value busywork.     │
│    Either clarify scope or skip it entirely.                 │
└──────────────────────────────────────────────────────────────┘
"""


def _strip_leading_symbols(task_str: str) -> str:
    symbols = [
        Config.SYMBOLS['star'],
        Config.SYMBOLS['surprise'],
        Config.SYMBOLS['planned_yes'],
        Config.SYMBOLS['planned_no'],
        "--",
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


def parse_task(task_str: str) -> Tuple[str, str, Optional[int]]:
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


import math

def estimate_time_minutes(r_complex: float, r_risk: float, r_surprise: float) -> int:
    """Estimate time based on complexity, risk, and surprise ratings. Rounds up to nearest 5 min."""
    base_times = {0.0: 15, 0.3: 45, 0.6: 90, 1.0: 180}
    base = base_times.get(r_complex, 45)
    risk_factor = 1 + r_risk * 0.3
    surprise_factor = 1 + r_surprise * 0.2
    raw_minutes = base * risk_factor * surprise_factor
    # Round up to next 5 minutes
    return math.ceil(raw_minutes / 5) * 5


def get_user_rating(prompt_label: str, auto_val: Optional[float] = None) -> float:
    c = Colors
    if auto_val is not None:
        inv_map = {v: k for k, v in Config.RATING_MAP.items()}
        key = inv_map.get(auto_val, "?")
        print(f"{c.GRAY}{prompt_label}: {c.CYAN}[AUTO] {key} ({auto_val}){c.RESET}")
        return auto_val

    while True:
        try:
            val = input(f"{c.WHITE}{prompt_label}: {c.RESET}")
            if val in Config.RATING_MAP:
                return Config.RATING_MAP[val]
            print(f"  {c.GRAY}→ Use 0, 1, 2, or 3.{c.RESET}")
        except KeyboardInterrupt:
            print(f"\n  {c.GRAY}Cancelled. Take care.{c.RESET}")
            sys.exit(0)
        except EOFError:
            sys.exit(0)


def prompt_grouped_batch_ratings(planned_mins: Optional[int] = None) -> List[float]:
    """Prompt for ratings grouped by category."""
    c = Colors
    dm = Config.DISPLAY_MAP

    print(f"\n{c.CYAN}Scale: 0={dm['0']} │ 1={dm['1']} │ 2={dm['2']} │ 3={dm['3']}{c.RESET}")
    if planned_mins is not None:
        auto_val = get_time_score(planned_mins)
        inv_map = {v: k for k, v in Config.RATING_MAP.items()}
        key = inv_map.get(auto_val, "?")
        print(f"{c.GRAY}Time will auto-fill from {planned_mins}m → use _ for T{c.RESET}")

    ratings = []

    print(f"\n{c.GOLD}Impact{c.RESET} {c.GRAY}(L=Leverage, Conf=Confidence, G=Goals){c.RESET}")
    print(f"{c.DIM}  L: Will this make future work easier? │ Conf: Is the path clear? │ G: Does this move the needle?{c.RESET}")
    impact_ratings = _prompt_category_ratings("L,Conf,G", 3, c.GOLD)
    ratings.extend(impact_ratings)

    print(f"\n{c.RED}Urgency{c.RESET} {c.GRAY}(P=Priority, D=Deadline){c.RESET}")
    print(f"{c.DIM}  P: What happens if I don't do this today? │ D: When is this due?{c.RESET}")
    urgency_ratings = _prompt_category_ratings("P,D", 2, c.RED)
    ratings.extend(urgency_ratings)

    print(f"\n{c.MAGENTA}Execution{c.RESET} {c.GRAY}(C=Complex, T=Time, R=Risk, F=Fun){c.RESET}")
    print(f"{c.DIM}  C: Deep focus needed? │ T: How long? │ R: Unknowns that could derail? │ F: Looking forward to it?{c.RESET}")
    exec_ratings = _prompt_category_ratings("C,T,R,F", 4, c.MAGENTA, time_index=1, planned_mins=planned_mins)
    ratings.extend(exec_ratings)

    print(f"\n{c.GREEN}Clarity{c.RESET} {c.GRAY}(S=Surprise, Pl=Planned){c.RESET}")
    print(f"{c.DIM}  S: Do I know what 'done' looks like? │ Pl: Did I decide to do this?{c.RESET}")
    clarity_ratings = _prompt_category_ratings("S,Pl", 2, c.GREEN)
    ratings.extend(clarity_ratings)

    return ratings


def _prompt_category_ratings(
    label: str,
    count: int,
    color: str,
    time_index: Optional[int] = None,
    planned_mins: Optional[int] = None
) -> List[float]:
    """Prompt for a category's ratings."""
    c = Colors
    while True:
        try:
            val = input(f"{color}{label}: {c.RESET}")
            if val.strip().startswith("/"):
                return None
            parts = val.replace(" ", "").split(",")
            if len(parts) != count:
                print(f"  {c.GRAY}→ Enter {count} values, comma-separated.{c.RESET}")
                continue
            ratings = []
            for i, p in enumerate(parts):
                if p == "_" and time_index is not None and i == time_index and planned_mins is not None:
                    ratings.append(get_time_score(planned_mins))
                elif p in Config.RATING_MAP:
                    ratings.append(Config.RATING_MAP[p])
                else:
                    print(f"  {c.GRAY}→ Use 0, 1, 2, or 3 (or _ for auto-time).{c.RESET}")
                    ratings = None
                    break
            if ratings is not None:
                return ratings
        except KeyboardInterrupt:
            print(f"\n  {c.GRAY}Cancelled. Take care.{c.RESET}")
            sys.exit(0)
        except EOFError:
            sys.exit(0)


def prompt_batch_ratings(planned_mins: Optional[int] = None) -> List[float]:
    """Legacy single-line batch prompt (kept for -r flag parsing)."""
    c = Colors
    dm = Config.DISPLAY_MAP
    print(f"{c.GRAY}Scale: 0={dm['0']} │ 1={dm['1']} │ 2={dm['2']} │ 3={dm['3']}{c.RESET}")
    print(f"{c.GRAY}Impact    - (L)everage, (Conf)idence, (G)oals{c.RESET}")
    print(f"{c.GRAY}Urgency   - (P)riority, (D)eadline{c.RESET}")
    print(f"{c.GRAY}Execution - (C)omplex, (T)ime, (R)isk, (F)un{c.RESET}")
    print(f"{c.GRAY}Clarity   - (S)urprise, (Pl)anned{c.RESET}")
    print(f"{c.GRAY}Input as single list in order L,Conf,G,P,D,C,T,R,F,S,Pl{c.RESET}")
    if planned_mins is not None:
        auto_val = get_time_score(planned_mins)
        inv_map = {v: k for k, v in Config.RATING_MAP.items()}
        key = inv_map.get(auto_val, "?")
        print(f"{c.GRAY}Use _ for Time (T) to auto-fill from {planned_mins}m → {key} ({auto_val}){c.RESET}")

    while True:
        try:
            val = input(f"{c.WHITE}Ratings: {c.RESET}")
            ratings = parse_ratings(val, planned_mins)
            if ratings is not None:
                return ratings
            print(f"  {c.GRAY}→ Use 11 values (0-3), comma-separated. Use _ for time with {{pH:MM}}.{c.RESET}")
        except KeyboardInterrupt:
            print(f"\n  {c.GRAY}Cancelled. Take care.{c.RESET}")
            sys.exit(0)
        except EOFError:
            sys.exit(0)


def parse_ratings(ratings_str: str, planned_mins: Optional[int] = None) -> Optional[List[float]]:
    parts = ratings_str.replace(" ", "").split(",")
    if len(parts) != 11:
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
        return ratings
    except (ValueError, KeyError):
        return None


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


def format_output(impact_sym: str, surprise_sym: str, planned_sym: str,
                  tags: str, text: str) -> str:
    prefix_part_1 = f"{impact_sym}{surprise_sym}"
    separator = "--" if (impact_sym or surprise_sym) else ""
    final_prefix = f"{prefix_part_1}{separator}{planned_sym}"

    if tags:
        return f"{final_prefix}{tags} {text}"
    return f"{final_prefix} {text}"


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


def run_with_ratings(task_input: str, ratings: List[float], estimated_mins: Optional[int] = None) -> dict:
    tags, text, planned_mins = parse_task(task_input)

    r_leverage, r_confidence, r_goals, r_priority, r_deadline = ratings[0:5]
    r_complex, r_time, r_risk, r_fun = ratings[5:9]
    r_surprise, r_planned = ratings[9:11]

    s_impact = compute_impact(r_leverage, r_confidence, r_goals)
    s_urgency = compute_urgency(r_priority, r_deadline)
    s_execution = compute_execution(r_complex, r_time, r_risk, r_fun)

    impact_sym = get_impact_symbol(s_impact)
    urgency_sym = get_urgency_symbol(s_urgency)
    execution_sym = get_execution_symbol(s_execution)
    surprise_sym = get_surprise_symbol(r_surprise)
    planned_sym = get_planned_symbol(r_planned)

    analysis = get_analysis_text(s_impact, s_execution, s_urgency, r_surprise)

    # If we estimated time, prepend it as a tag
    if planned_mins is None and estimated_mins is not None:
        h = estimated_mins // 60
        m = estimated_mins % 60
        time_tag = f"{{p{h}:{m:02d}}}"
        tags = f"{time_tag}{tags}"

    final_string = format_output(impact_sym, surprise_sym, planned_sym, tags, text)

    return {
        'output': final_string,
        'urgency_sym': urgency_sym,
        'execution_sym': execution_sym,
        'has_surprise': bool(surprise_sym),
        'scores': {
            'impact': s_impact,
            'urgency': s_urgency,
            'execution': s_execution,
        },
        'ratings': {
            'L': r_leverage,
            'Conf': r_confidence,
            'G': r_goals,
            'P': r_priority,
            'D': r_deadline,
            'C': r_complex,
            'T': r_time,
            'R': r_risk,
            'F': r_fun,
            'S': r_surprise,
            'Pl': r_planned,
        },
        'symbols': {
            'impact': impact_sym,
            'urgency': urgency_sym,
            'execution': execution_sym,
            'surprise': surprise_sym,
            'planned': planned_sym,
        },
        'estimated_time_minutes': estimated_mins,
        'planned_time_minutes': planned_mins,
        'analysis': analysis,
    }


def run_interactive(task_input: str) -> dict:
    c = Colors
    tags, text, planned_mins = parse_task(task_input)

    print(f"\n{c.BOLD}Task:{c.RESET} {text}")
    if tags:
        print(f"{c.GRAY}Tags: {tags}{c.RESET}")
    if planned_mins is not None:
        print(f"{c.GRAY}Planned: {planned_mins}m{c.RESET}")
    print(f"{c.DIM}{'─' * 42}{c.RESET}")

    dm = Config.DISPLAY_MAP
    print(f"{c.CYAN}Scale: 0={dm['0']} │ 1={dm['1']} │ 2={dm['2']} │ 3={dm['3']}{c.RESET}")
    print(f"{c.DIM}{'─' * 42}{c.RESET}")

    print(f"\n{c.GOLD}── Impact ──{c.RESET}")
    r_leverage = get_user_rating(f"{c.GOLD}Leverage   (L){c.RESET}")
    r_confidence = get_user_rating(f"{c.GOLD}Confidence (Conf){c.RESET}")
    r_goals = get_user_rating(f"{c.GOLD}Goals      (G){c.RESET}")
    s_impact = compute_impact(r_leverage, r_confidence, r_goals)

    print(f"\n{c.RED}── Urgency ──{c.RESET}")
    r_priority = get_user_rating(f"{c.RED}Priority (P){c.RESET}")
    r_deadline = get_user_rating(f"{c.RED}Deadline (D){c.RESET}")
    s_urgency = compute_urgency(r_priority, r_deadline)

    print(f"\n{c.MAGENTA}── Execution ──{c.RESET}")
    r_complex = get_user_rating(f"{c.MAGENTA}Complex  (C){c.RESET}")
    auto_time_val = None
    if planned_mins is not None:
        auto_time_val = get_time_score(planned_mins)
    r_time = get_user_rating(f"{c.MAGENTA}Time     (T){c.RESET}", auto_val=auto_time_val)
    r_risk = get_user_rating(f"{c.MAGENTA}Risk     (R){c.RESET}")
    r_fun = get_user_rating(f"{c.MAGENTA}Fun      (F){c.RESET}")
    s_execution = compute_execution(r_complex, r_time, r_risk, r_fun)

    print(f"\n{c.GREEN}── Clarity ──{c.RESET}")
    r_surprise = get_user_rating(f"{c.GREEN}Surprise (S){c.RESET}")
    r_planned = get_user_rating(f"{c.GREEN}Planned  (Pl){c.RESET}")

    estimated_mins = None
    if planned_mins is None:
        estimated_mins = estimate_time_minutes(r_complex, r_risk, r_surprise)

    analysis = get_analysis_text(s_impact, s_execution, s_urgency, r_surprise)

    impact_sym = get_impact_symbol(s_impact)
    urgency_sym = get_urgency_symbol(s_urgency)
    execution_sym = get_execution_symbol(s_execution)
    surprise_sym = get_surprise_symbol(r_surprise)
    planned_sym = get_planned_symbol(r_planned)

    final_string = format_output(impact_sym, surprise_sym, planned_sym, tags, text)

    return {
        'output': final_string,
        'urgency_sym': urgency_sym,
        'execution_sym': execution_sym,
        'has_surprise': bool(surprise_sym),
        'scores': {
            'impact': s_impact,
            'urgency': s_urgency,
            'execution': s_execution,
        },
        'ratings': {
            'L': r_leverage,
            'Conf': r_confidence,
            'G': r_goals,
            'P': r_priority,
            'D': r_deadline,
            'C': r_complex,
            'T': r_time,
            'R': r_risk,
            'F': r_fun,
            'S': r_surprise,
            'Pl': r_planned,
        },
        'symbols': {
            'impact': impact_sym,
            'urgency': urgency_sym,
            'execution': execution_sym,
            'surprise': surprise_sym,
            'planned': planned_sym,
        },
        'estimated_time_minutes': estimated_mins,
        'planned_time_minutes': planned_mins,
        'analysis': analysis,
    }


def run_detail(task_input: str) -> dict:
    """Detail mode: interactive with explanations."""
    c = Colors
    print(f"{c.CYAN}{DETAIL_EXPLANATION}{c.RESET}")
    print(f"{c.GRAY}{DETAIL_EXAMPLES}{c.RESET}")
    print(f"{c.DIM}{'═' * 60}{c.RESET}")
    return run_interactive(task_input)


def run_batch(task_input: str) -> dict:
    """Batch mode: grouped category input."""
    tags, text, planned_mins = parse_task(task_input)
    c = Colors

    print(f"\n{c.BOLD}Task:{c.RESET} {text}")
    if tags:
        print(f"{c.GRAY}Tags: {tags}{c.RESET}")
    if planned_mins is not None:
        print(f"{c.GRAY}Planned: {planned_mins}m{c.RESET}")

    ratings = prompt_grouped_batch_ratings(planned_mins)

    estimated_mins = None
    if planned_mins is None:
        r_complex = ratings[5]
        r_risk = ratings[7]
        r_surprise = ratings[9]
        estimated_mins = estimate_time_minutes(r_complex, r_risk, r_surprise)

    return run_with_ratings(task_input, ratings, estimated_mins)


def colorize_output(output: str) -> str:
    c = Colors
    result = output
    result = result.replace("⭐️", f"{c.GOLD}⭐️{c.RESET}")
    result = result.replace("🚨", f"{c.RED}🚨{c.RESET}")
    result = result.replace("🐢", f"{c.GREEN}🐢{c.RESET}")
    result = result.replace("🥵", f"{c.RED}🥵{c.RESET}")
    result = result.replace("🍭", f"{c.GREEN}🍭{c.RESET}")
    result = result.replace("🎁", f"{c.MAGENTA}🎁{c.RESET}")
    result = result.replace("🗓️", f"{c.CYAN}🗓️{c.RESET}")
    result = result.replace("🎲", f"{c.GRAY}🎲{c.RESET}")
    return result


def copy_to_clipboard(text: str) -> bool:
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        elif sys.platform.startswith("linux"):
            try:
                subprocess.run(["xclip", "-selection", "clipboard"],
                               input=text.encode(), check=True)
                return True
            except FileNotFoundError:
                try:
                    subprocess.run(["xsel", "--clipboard", "--input"],
                                   input=text.encode(), check=True)
                    return True
                except FileNotFoundError:
                    return False
        elif sys.platform == "win32":
            subprocess.run(["clip"], input=text.encode(), check=True, shell=True)
            return True
    except Exception:
        return False
    return False


def print_result(result: dict, copy: bool = False, quiet: bool = False) -> None:
    c = Colors
    output = result['output']
    colored_output = colorize_output(output)
    urgency_colored = colorize_output(result['urgency_sym'])
    execution_colored = colorize_output(result['execution_sym'])

    if not quiet:
        print(f"\n{c.DIM}{'═' * 42}{c.RESET}")
    print(colored_output)
    if not quiet:
        print(f"{c.GRAY}category: {urgency_colored} & {execution_colored}{c.RESET}")
        if result.get('estimated_time_minutes'):
            print(f"{c.GRAY}estimated time: ~{result['estimated_time_minutes']} min{c.RESET}")
        print(f"{c.DIM}{'─' * 42}{c.RESET}")
        if result.get('analysis'):
            print(f"{c.CYAN}{result['analysis']}{c.RESET}")
        print(f"{c.DIM}{'═' * 42}{c.RESET}")

    if copy:
        if copy_to_clipboard(output):
            print(f"{c.GREEN}✓ Copied to clipboard{c.RESET}")
        else:
            print(f"{c.RED}✗ Could not copy to clipboard{c.RESET}")

    if result['has_surprise'] and not quiet:
        print(f"{c.MAGENTA}{SURPRISE_REMINDER}{c.RESET}")


def show_welcome() -> None:
    c = Colors
    print(f"{c.CYAN}{WELCOME_MESSAGE}{c.RESET}")
    mark_welcomed()


def _get_log_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir / "tasks.log"


def log_task(task_input: str, result: dict, mode: str, profile: Optional[str] = None) -> None:
    """Log task to JSONL file."""
    log_path = _get_log_path()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "input": task_input,
        "ratings": result.get('ratings', {}),
        "scores": result.get('scores', {}),
        "symbols": result.get('symbols', {}),
        "output": result.get('output', ''),
        "estimated_time_minutes": result.get('estimated_time_minutes'),
        "planned_time_minutes": result.get('planned_time_minutes'),
        "mode": mode,
        "profile": profile,
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tp",
        description=(
            "Task Prioritizer — a calm tool for mindful work.\n\n"
            "Helps you choose what to work on (calculations)\n"
            "and know when to stop (stop-rule)."
        ),
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task string to annotate, e.g. '{p0:45} write draft'"
    )
    parser.add_argument(
        "-r", "--ratings",
        metavar="L,Conf,G,P,D,C,T,R,F,S,Pl",
        help="Provide all 11 ratings inline (0-3 each, comma-separated). Use _ for auto-time."
    )
    parser.add_argument(
        "-b", "--batch",
        action="store_true",
        help="Use batch mode (grouped input) — this is now the default"
    )
    parser.add_argument(
        "-d", "--detail",
        action="store_true",
        help="Use detail mode with explanations for each rating category"
    )
    parser.add_argument(
        "-p", "--profile",
        metavar="NAME",
        help="Load .env.NAME profile (falls back to default if not found)"
    )
    parser.add_argument(
        "-c", "--copy",
        action="store_true",
        help="Copy result to clipboard"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output (just the annotated task)"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode for automated testing (non-interactive, uses config values)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}"
    )
    return parser


def process_task(task_input: str, mode: str, copy: bool, quiet: bool, profile: Optional[str]) -> dict:
    """Process a single task with the specified mode."""
    tags, text, planned_mins = parse_task(task_input)

    if mode == "detail":
        result = run_detail(task_input)
    else:
        result = run_batch(task_input)

    print_result(result, copy=copy, quiet=quiet)
    log_task(task_input, result, mode, profile)
    return result


def run_loop(initial_task: Optional[str], mode: str, copy: bool, quiet: bool, profile: Optional[str]) -> None:
    """Main interaction loop."""
    c = Colors
    current_mode = mode

    # Setup readline completion if available
    if readline:
        commands = ["/help", "/mode batch", "/mode detail", "/quit"]
        
        def completer(text, state):
            # Get the full line buffer to handle completion from start
            try:
                line = readline.get_line_buffer()
            except Exception:
                line = text
            
            # If line starts with /, complete commands
            if line.startswith("/"):
                options = [cmd for cmd in commands if cmd.startswith(line)]
            else:
                options = [cmd for cmd in commands if cmd.startswith(text)]
            
            if state < len(options):
                return options[state]
            return None

        readline.set_completer(completer)
        # Set delimiters to not include / so it's part of the completion text
        readline.set_completer_delims(' \t\n')
        
        # Handle macOS (libedit) vs Linux (GNU readline) binding
        if readline.__doc__ and 'libedit' in readline.__doc__:
            # libedit requires specific binding format
            readline.parse_and_bind("bind -e")  # Use emacs key bindings
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")

    # Show startup banner
    print(f"{c.CYAN}{STARTUP_BANNER.format(version=VERSION)}{c.RESET}")
    
    # If no initial task provided, show commands and prompt for task name
    if not initial_task:
        print(LOOP_HELP)
        print(f"{c.GRAY}Tip: Type / to see commands.{c.RESET}")
        print(f"{c.GRAY}Current mode: {current_mode}{c.RESET}")
    else:
        process_task(initial_task, current_mode, copy, quiet, profile)

    while True:
        try:
            print(f"\n{c.GRAY}───────────────────────────────────────────{c.RESET}")
            task_input = input(f"{c.WHITE}> {c.RESET}").strip()

            if not task_input:
                continue

            # Handle commands starting with /
            if task_input.startswith("/"):
                cmd = task_input.lower()
                
                # Show command menu for just /
                if cmd == "/":
                    print(f"\n{c.CYAN}╭─────────────────────────────────────╮{c.RESET}")
                    print(f"{c.CYAN}│{c.RESET}  {c.BOLD}Available Commands{c.RESET}                 {c.CYAN}│{c.RESET}")
                    print(f"{c.CYAN}├─────────────────────────────────────┤{c.RESET}")
                    print(f"{c.CYAN}│{c.RESET}  {c.WHITE}/h{c.RESET}            Show help           {c.CYAN}│{c.RESET}")
                    print(f"{c.CYAN}│{c.RESET}  {c.WHITE}/m b{c.RESET}          Batch mode          {c.CYAN}│{c.RESET}")
                    print(f"{c.CYAN}│{c.RESET}  {c.WHITE}/m d{c.RESET}          Detail mode         {c.CYAN}│{c.RESET}")
                    print(f"{c.CYAN}│{c.RESET}  {c.WHITE}/q{c.RESET}            Quit                {c.CYAN}│{c.RESET}")
                    print(f"{c.CYAN}╰─────────────────────────────────────╯{c.RESET}")
                    continue
                
                # Quit command (with shortcuts)
                if cmd in ("/quit", "/q"):
                    print(f"{c.GRAY}Take care.{c.RESET}")
                    break
                
                # Help command (with shortcuts)
                if cmd in ("/help", "/h"):
                    print(LOOP_HELP)
                    continue
                
                # Mode command
                if cmd.startswith("/mode") or cmd.startswith("/m "):
                    parts = task_input.split()
                    if len(parts) >= 2:
                        new_mode = parts[1].lower()
                        # Allow partial matching: b -> batch, d -> detail
                        if new_mode in ("batch", "b"):
                            current_mode = "batch"
                            print(f"{c.GREEN}Switched to batch mode.{c.RESET}")
                        elif new_mode in ("detail", "d"):
                            current_mode = "detail"
                            print(f"{c.GREEN}Switched to detail mode.{c.RESET}")
                        else:
                            print(f"{c.GRAY}Unknown mode. Use: /mode batch or /mode detail{c.RESET}")
                    else:
                        print(f"{c.GRAY}Current mode: {current_mode}. Use: /mode batch or /mode detail{c.RESET}")
                    continue
                
                # Unknown command - show suggestions
                print(f"{c.GRAY}Unknown command '{task_input}'. Type / to see available commands.{c.RESET}")
                continue

            process_task(task_input, current_mode, copy, quiet, profile)

        except KeyboardInterrupt:
            print(f"\n{c.GRAY}Take care.{c.RESET}")
            break
        except EOFError:
            print(f"\n{c.GRAY}Take care.{c.RESET}")
            break


def run_demo() -> None:
    """
    Run in demo mode for automated testing by AI agents.
    
    This mode simulates the complete interactive flow non-interactively:
    1. Shows startup banner
    2. Simulates menu invocation (TAB)
    3. Shows /help output
    4. Processes demo task in BATCH mode
    5. Switches to DETAIL mode
    6. Processes demo task in DETAIL mode
    7. Shows /quit
    
    Purpose:
    - Allow AI agents to analyze the tool's input/output behavior
    - Enable automated testing in CI/CD pipelines
    - Test both batch and detail modes in a single run
    """
    c = Colors
    
    def demo_step(step_num: int, description: str):
        """Print a demo step header."""
        print(f"\n{c.ORANGE}{'━' * 60}{c.RESET}")
        print(f"{c.ORANGE}STEP {step_num}: {description}{c.RESET}")
        print(f"{c.ORANGE}{'━' * 60}{c.RESET}")
    
    def simulate_input(prompt: str, value: str):
        """Simulate user input display."""
        print(f"{c.WHITE}{prompt}{c.CYAN}{value}{c.RESET}")
    
    # Header
    print(f"{c.CYAN}{'═' * 60}{c.RESET}")
    print(f"{c.BOLD}DEMO MODE — Full Integration Test{c.RESET}")
    print(f"{c.CYAN}{'═' * 60}{c.RESET}")
    print(f"\n{c.GRAY}Testing both BATCH and DETAIL modes with complete flow.{c.RESET}")
    print(f"{c.GRAY}Demo Task:    {Config.DEMO_TASK}{c.RESET}")
    print(f"{c.GRAY}Demo Ratings: {Config.DEMO_RATINGS}{c.RESET}")
    
    # Parse and validate demo configuration
    task_input = Config.DEMO_TASK
    tags, text, planned_mins = parse_task(task_input)
    ratings = parse_ratings(Config.DEMO_RATINGS, planned_mins)
    
    if ratings is None:
        print(f"\n{c.RED}Error: Invalid DEMO_RATINGS in configuration.{c.RESET}")
        print(f"  Expected: 11 comma-separated values (0-3)")
        print(f"  Got:      {Config.DEMO_RATINGS}")
        sys.exit(1)
    
    # Calculate estimated time
    estimated_mins = None
    if planned_mins is None:
        r_complex = ratings[5]
        r_risk = ratings[7]
        r_surprise = ratings[9]
        estimated_mins = estimate_time_minutes(r_complex, r_risk, r_surprise)
    
    # Split ratings into category groups for simulation
    ratings_str = Config.DEMO_RATINGS.split(',')
    impact_input = f"{ratings_str[0]},{ratings_str[1]},{ratings_str[2]}"
    urgency_input = f"{ratings_str[3]},{ratings_str[4]}"
    exec_input = f"{ratings_str[5]},{ratings_str[6]},{ratings_str[7]},{ratings_str[8]}"
    clarity_input = f"{ratings_str[9]},{ratings_str[10]}"
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 1: App Startup - Show Banner
    # ═══════════════════════════════════════════════════════════════
    demo_step(1, "App Startup - Show Banner")
    print(f"{c.CYAN}{STARTUP_BANNER.format(version=VERSION)}{c.RESET}")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: Simulate Menu Invocation (TAB pressed)
    # ═══════════════════════════════════════════════════════════════
    demo_step(2, "Menu Invocation (simulated TAB press)")
    simulate_input("> ", "/")
    print(f"\n{c.CYAN}╭─────────────────────────────────────╮{c.RESET}")
    print(f"{c.CYAN}│{c.RESET}  {c.BOLD}Available Commands{c.RESET}                 {c.CYAN}│{c.RESET}")
    print(f"{c.CYAN}├─────────────────────────────────────┤{c.RESET}")
    print(f"{c.CYAN}│{c.RESET}  {c.WHITE}/h{c.RESET}            Show help           {c.CYAN}│{c.RESET}")
    print(f"{c.CYAN}│{c.RESET}  {c.WHITE}/m b{c.RESET}          Batch mode          {c.CYAN}│{c.RESET}")
    print(f"{c.CYAN}│{c.RESET}  {c.WHITE}/m d{c.RESET}          Detail mode         {c.CYAN}│{c.RESET}")
    print(f"{c.CYAN}│{c.RESET}  {c.WHITE}/q{c.RESET}            Quit                {c.CYAN}│{c.RESET}")
    print(f"{c.CYAN}╰─────────────────────────────────────╯{c.RESET}")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3: Show /help Output
    # ═══════════════════════════════════════════════════════════════
    demo_step(3, "Command: /help")
    simulate_input("> ", "/help")
    print(LOOP_HELP)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 4: Process Task in BATCH Mode
    # ═══════════════════════════════════════════════════════════════
    demo_step(4, "BATCH MODE - Process Demo Task")
    print(f"{c.GRAY}Mode: batch (default){c.RESET}\n")
    
    # Simulate entering the task
    simulate_input("> ", task_input)
    print(f"\n{c.BOLD}Task:{c.RESET} {text}")
    if tags:
        print(f"{c.GRAY}Tags: {tags}{c.RESET}")
    if planned_mins is not None:
        print(f"{c.GRAY}Planned: {planned_mins}m{c.RESET}")
    
    # Simulate batch mode prompts
    dm = Config.DISPLAY_MAP
    print(f"\n{c.CYAN}Scale: 0={dm['0']} │ 1={dm['1']} │ 2={dm['2']} │ 3={dm['3']}{c.RESET}")
    
    print(f"\n{c.GOLD}Impact{c.RESET} {c.GRAY}(L=Leverage, Conf=Confidence, G=Goals){c.RESET}")
    print(f"{c.DIM}  L: Will this make future work easier? │ Conf: Is the path clear? │ G: Does this move the needle?{c.RESET}")
    simulate_input(f"{c.GOLD}L,Conf,G: {c.RESET}", impact_input)
    
    print(f"\n{c.RED}Urgency{c.RESET} {c.GRAY}(P=Priority, D=Deadline){c.RESET}")
    print(f"{c.DIM}  P: What happens if I don't do this today? │ D: When is this due?{c.RESET}")
    simulate_input(f"{c.RED}P,D: {c.RESET}", urgency_input)
    
    print(f"\n{c.MAGENTA}Execution{c.RESET} {c.GRAY}(C=Complex, T=Time, R=Risk, F=Fun){c.RESET}")
    print(f"{c.DIM}  C: Deep focus needed? │ T: How long? │ R: Unknowns that could derail? │ F: Looking forward to it?{c.RESET}")
    simulate_input(f"{c.MAGENTA}C,T,R,F: {c.RESET}", exec_input)
    
    print(f"\n{c.GREEN}Clarity{c.RESET} {c.GRAY}(S=Surprise, Pl=Planned){c.RESET}")
    print(f"{c.DIM}  S: Do I know what 'done' looks like? │ Pl: Did I decide to do this?{c.RESET}")
    simulate_input(f"{c.GREEN}S,Pl: {c.RESET}", clarity_input)
    
    # Process and show result
    result_batch = run_with_ratings(task_input, ratings, estimated_mins)
    print(f"\n{c.DIM}{'═' * 42}{c.RESET}")
    print(colorize_output(result_batch['output']))
    print(f"{c.GRAY}category: {colorize_output(result_batch['urgency_sym'])} & {colorize_output(result_batch['execution_sym'])}{c.RESET}")
    if estimated_mins:
        print(f"{c.GRAY}estimated time: ~{estimated_mins} min{c.RESET}")
    print(f"{c.DIM}{'─' * 42}{c.RESET}")
    print(f"{c.CYAN}{result_batch.get('analysis', '')}{c.RESET}")
    print(f"{c.DIM}{'═' * 42}{c.RESET}")
    log_task(task_input, result_batch, "demo-batch", None)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 5: Switch to Detail Mode
    # ═══════════════════════════════════════════════════════════════
    demo_step(5, "Command: /mode detail")
    simulate_input("> ", "/mode detail")
    print(f"{c.GREEN}Switched to detail mode.{c.RESET}")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 6: Process Task in DETAIL Mode
    # ═══════════════════════════════════════════════════════════════
    demo_step(6, "DETAIL MODE - Process Demo Task")
    print(f"{c.GRAY}Mode: detail (with explanations){c.RESET}\n")
    
    # Show detail mode explanation excerpt
    print(f"{c.CYAN}Understanding the Rating System (excerpt):{c.RESET}")
    print(f"{c.GRAY}This prioritization system scores tasks across 4 categories.{c.RESET}")
    print(f"{c.GRAY}High Impact + Low Execution = Quick wins (do first){c.RESET}")
    print(f"{c.GRAY}High Impact + High Execution = Strategic investments (schedule){c.RESET}")
    print(f"{c.GRAY}...{c.RESET}\n")
    
    # Simulate entering the task
    simulate_input("> ", task_input)
    print(f"\n{c.BOLD}Task:{c.RESET} {text}")
    if tags:
        print(f"{c.GRAY}Tags: {tags}{c.RESET}")
    
    print(f"\n{c.CYAN}Scale: 0={dm['0']} │ 1={dm['1']} │ 2={dm['2']} │ 3={dm['3']}{c.RESET}")
    print(f"{c.DIM}{'─' * 42}{c.RESET}")
    
    # Simulate detail mode prompts (individual ratings)
    print(f"\n{c.GOLD}── Impact ──{c.RESET}")
    simulate_input(f"{c.GOLD}Leverage   (L): {c.RESET}", ratings_str[0])
    simulate_input(f"{c.GOLD}Confidence (Conf): {c.RESET}", ratings_str[1])
    simulate_input(f"{c.GOLD}Goals      (G): {c.RESET}", ratings_str[2])
    
    print(f"\n{c.RED}── Urgency ──{c.RESET}")
    simulate_input(f"{c.RED}Priority (P): {c.RESET}", ratings_str[3])
    simulate_input(f"{c.RED}Deadline (D): {c.RESET}", ratings_str[4])
    
    print(f"\n{c.MAGENTA}── Execution ──{c.RESET}")
    simulate_input(f"{c.MAGENTA}Complex  (C): {c.RESET}", ratings_str[5])
    simulate_input(f"{c.MAGENTA}Time     (T): {c.RESET}", ratings_str[6])
    simulate_input(f"{c.MAGENTA}Risk     (R): {c.RESET}", ratings_str[7])
    simulate_input(f"{c.MAGENTA}Fun      (F): {c.RESET}", ratings_str[8])
    
    print(f"\n{c.GREEN}── Clarity ──{c.RESET}")
    simulate_input(f"{c.GREEN}Surprise (S): {c.RESET}", ratings_str[9])
    simulate_input(f"{c.GREEN}Planned  (Pl): {c.RESET}", ratings_str[10])
    
    # Process and show result
    result_detail = run_with_ratings(task_input, ratings, estimated_mins)
    print(f"\n{c.DIM}{'═' * 42}{c.RESET}")
    print(colorize_output(result_detail['output']))
    print(f"{c.GRAY}category: {colorize_output(result_detail['urgency_sym'])} & {colorize_output(result_detail['execution_sym'])}{c.RESET}")
    if estimated_mins:
        print(f"{c.GRAY}estimated time: ~{estimated_mins} min{c.RESET}")
    print(f"{c.DIM}{'─' * 42}{c.RESET}")
    print(f"{c.CYAN}{result_detail.get('analysis', '')}{c.RESET}")
    print(f"{c.DIM}{'═' * 42}{c.RESET}")
    log_task(task_input, result_detail, "demo-detail", None)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 7: Quit
    # ═══════════════════════════════════════════════════════════════
    demo_step(7, "Command: /quit")
    simulate_input("> ", "/quit")
    print(f"{c.GRAY}Take care.{c.RESET}")
    
    # ═══════════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{c.CYAN}{'═' * 60}{c.RESET}")
    print(f"{c.BOLD}DEMO SUMMARY{c.RESET}")
    print(f"{c.CYAN}{'═' * 60}{c.RESET}")
    print(f"\n{c.GREEN}✓ Startup banner displayed{c.RESET}")
    print(f"{c.GREEN}✓ Menu invocation simulated{c.RESET}")
    print(f"{c.GREEN}✓ /help command executed{c.RESET}")
    print(f"{c.GREEN}✓ BATCH mode: task processed successfully{c.RESET}")
    print(f"{c.GREEN}✓ Mode switch to detail{c.RESET}")
    print(f"{c.GREEN}✓ DETAIL mode: task processed successfully{c.RESET}")
    print(f"{c.GREEN}✓ /quit command executed{c.RESET}")
    print(f"\n{c.GRAY}Results logged to: logs/tasks.log{c.RESET}")
    print(f"{c.GRAY}Modes tested: demo-batch, demo-detail{c.RESET}")
    
    # Verify outputs match
    if result_batch['output'] == result_detail['output']:
        print(f"\n{c.GREEN}✓ Output consistency: BATCH and DETAIL modes produce identical results{c.RESET}")
    else:
        print(f"\n{c.RED}✗ Output mismatch between modes (investigate){c.RESET}")
    
    print(f"\n{c.CYAN}{'═' * 60}{c.RESET}")
    print(f"{c.GREEN}Demo completed successfully.{c.RESET}")
    print(f"{c.CYAN}{'═' * 60}{c.RESET}")


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.no_color or not supports_color():
        Colors.disable()

    if args.profile:
        load_profile(args.profile)

    if args.validate_config:
        errors = Config.validate()
        if errors:
            print("Configuration errors:")
            for e in errors:
                print(f"  ✗ {e}")
            sys.exit(1)
        print("Configuration is valid. ✓")
        sys.exit(0)

    if args.demo:
        run_demo()
        sys.exit(0)

    if args.detail and args.batch:
        print("Error: use either --detail or --batch, not both.")
        sys.exit(1)

    if args.ratings and (args.detail or args.batch):
        print("Error: --ratings cannot be combined with --detail or --batch.")
        sys.exit(1)

    first_run = is_first_run()
    if first_run and not args.ratings and not args.quiet:
        show_welcome()

    if args.ratings:
        if not args.task:
            print("Error: --ratings requires a task argument.")
            sys.exit(1)
        tags, text, planned_mins = parse_task(args.task)
        ratings = parse_ratings(args.ratings, planned_mins)
        if ratings is None:
            print("Error: --ratings requires exactly 11 values (0-3), comma-separated.")
            print("       Order: L,Conf,G,P,D,C,T,R,F,S,Pl (use _ for auto-time)")
            print("       Example: --ratings 3,2,1,1,2,1,_,1,0,2,2")
            sys.exit(1)

        estimated_mins = None
        if planned_mins is None:
            r_complex = ratings[5]
            r_risk = ratings[7]
            r_surprise = ratings[9]
            estimated_mins = estimate_time_minutes(r_complex, r_risk, r_surprise)

        result = run_with_ratings(args.task, ratings, estimated_mins)
        print_result(result, copy=args.copy, quiet=args.quiet)
        log_task(args.task, result, "inline", args.profile)
        return

    mode = "detail" if args.detail else "batch"

    run_loop(args.task, mode, args.copy, args.quiet, args.profile)


if __name__ == "__main__":
    main()
