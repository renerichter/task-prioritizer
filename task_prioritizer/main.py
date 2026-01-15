#!/usr/bin/env python3
import sys
import re
import argparse
import subprocess
from typing import Optional, Tuple, List

from .config import Config, load_profile, is_first_run, mark_welcomed


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


def supports_color() -> bool:
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    if "NO_COLOR" in os.environ:
        return False
    return True


import os


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

Ratings order for --ratings: L,Conf,G,P,D,C,T,R,F,S,Pl
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


def prompt_batch_ratings(planned_mins: Optional[int] = None) -> List[float]:
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


def run_with_ratings(task_input: str, ratings: List[float]) -> dict:
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
            'surprise': r_surprise,
            'planned': r_planned,
        }
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
    print(f"{c.GRAY}Scale: 0={dm['0']} │ 1={dm['1']} │ 2={dm['2']} │ 3={dm['3']}{c.RESET}")
    print(f"{c.DIM}{'─' * 42}{c.RESET}")

    r_leverage = get_user_rating("Impact  → Leverage   (L)")
    r_confidence = get_user_rating("Impact  → Confidence (Conf)")
    r_goals = get_user_rating("Impact  → Goals       (G)")
    s_impact = compute_impact(r_leverage, r_confidence, r_goals)

    r_priority = get_user_rating("Urgency → Priority (P)")
    r_deadline = get_user_rating("Urgency → Deadline (D)")
    s_urgency = compute_urgency(r_priority, r_deadline)

    r_complex = get_user_rating("Execution → Complex  (C)")
    auto_time_val = None
    if planned_mins is not None:
        auto_time_val = get_time_score(planned_mins)
    r_time = get_user_rating("Execution → Time     (T)", auto_val=auto_time_val)
    r_risk = get_user_rating("Execution → Risk     (R)")
    r_fun = get_user_rating("Execution → Fun      (F)")
    s_execution = compute_execution(r_complex, r_time, r_risk, r_fun)

    r_surprise = get_user_rating("Clarity → Surprise (S)")
    r_planned = get_user_rating("Clarity → Planned  (Pl)")

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
            'surprise': r_surprise,
            'planned': r_planned,
        }
    }


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
        help="Prompt for all ratings in one guided input line"
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
        "--version",
        action="version",
        version="%(prog)s 2.1.0"
    )
    return parser


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

    if not args.task:
        parser.print_help()
        sys.exit(0)

    if args.batch and args.ratings:
        print("Error: use either --batch or --ratings, not both.")
        sys.exit(1)

    first_run = is_first_run()
    if first_run and not args.ratings and not args.quiet:
        show_welcome()

    tags, text, planned_mins = parse_task(args.task)

    if args.ratings:
        ratings = parse_ratings(args.ratings, planned_mins)
        if ratings is None:
            print("Error: --ratings requires exactly 11 values (0-3), comma-separated.")
            print("       Order: L,Conf,G,P,D,C,T,R,F,S,Pl (use _ for auto-time)")
            print("       Example: --ratings 3,2,1,1,2,1,_,1,0,2,2")
            sys.exit(1)
        result = run_with_ratings(args.task, ratings)
    elif args.batch:
        ratings = prompt_batch_ratings(planned_mins)
        result = run_with_ratings(args.task, ratings)
    else:
        result = run_interactive(args.task)

    print_result(result, copy=args.copy, quiet=args.quiet)


if __name__ == "__main__":
    main()
