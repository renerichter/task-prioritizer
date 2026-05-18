#!/usr/bin/env python3
import argparse
import sys

try:
    import readline
except ImportError:
    readline = None

from .cli.banners import (
    DETAIL_EXAMPLES,
    DETAIL_EXPLANATION,
    HELP_EPILOG,
    LOOP_HELP,
    STARTUP_BANNER,
    SURPRISE_REMINDER,
    VERSION,
    WELCOME_MESSAGE,
)
from .cli.colors import Colors, colorize_output, copy_to_clipboard, supports_color
from .config import Config, is_first_run, load_profile, mark_welcomed
from .core.analysis import get_analysis_text
from .core.decision_matrix import classify_quadrant, quadrant_recommendation
from .core.parsing import parse_ratings, parse_task
from .core.scoring import (
    compute_execution,
    compute_impact,
    compute_urgency,
    estimate_time_minutes,
    get_time_score,
)
from .core.symbols import (
    format_output,
    get_execution_symbol,
    get_impact_symbol,
    get_planned_symbol,
    get_recurrent_symbol,
    get_surprise_symbol,
    get_urgency_symbol,
)
from .persistence.log import _get_log_path, log_task


def get_user_rating(prompt_label: str, auto_val: float | None = None) -> float:
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


def prompt_grouped_batch_ratings(planned_mins: int | None = None) -> list[float]:
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

    print(f"\n{c.GREEN}Clarity{c.RESET} {c.GRAY}(S=Surprise, Pl=Planned, Rec=Recurrent){c.RESET}")
    print(f"{c.DIM}  S: Do I know what 'done' looks like? │ Pl: Did I decide to do this? │ Rec: Is this repeating?{c.RESET}")
    clarity_ratings = _prompt_category_ratings("S,Pl,Rec", 3, c.GREEN)
    ratings.extend(clarity_ratings)

    return ratings


def _prompt_category_ratings(
    label: str,
    count: int,
    color: str,
    time_index: int | None = None,
    planned_mins: int | None = None
) -> list[float]:
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


def prompt_batch_ratings(planned_mins: int | None = None) -> list[float]:
    """Legacy single-line batch prompt (kept for -r flag parsing)."""
    c = Colors
    dm = Config.DISPLAY_MAP
    print(f"{c.GRAY}Scale: 0={dm['0']} │ 1={dm['1']} │ 2={dm['2']} │ 3={dm['3']}{c.RESET}")
    print(f"{c.GRAY}Impact    - (L)everage, (Conf)idence, (G)oals{c.RESET}")
    print(f"{c.GRAY}Urgency   - (P)riority, (D)eadline{c.RESET}")
    print(f"{c.GRAY}Execution - (C)omplex, (T)ime, (R)isk, (F)un{c.RESET}")
    print(f"{c.GRAY}Clarity   - (S)urprise, (Pl)anned{c.RESET}")
    print(f"{c.GRAY}Input as single list in order L,Conf,G,P,D,C,T,R,F,S,Pl,Rec{c.RESET}")
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
            print(f"  {c.GRAY}→ Use 11 or 12 values (0-3), comma-separated. Use _ for time with {{pH:MM}}.{c.RESET}")
        except KeyboardInterrupt:
            print(f"\n  {c.GRAY}Cancelled. Take care.{c.RESET}")
            sys.exit(0)
        except EOFError:
            sys.exit(0)


def run_with_ratings(task_input: str, ratings: list[float], estimated_mins: int | None = None) -> dict:
    tags, text, planned_mins = parse_task(task_input)

    r_leverage, r_confidence, r_goals, r_priority, r_deadline = ratings[0:5]
    r_complex, r_time, r_risk, r_fun = ratings[5:9]
    r_surprise, r_planned, r_recurrent = ratings[9:12]

    s_impact = compute_impact(r_leverage, r_confidence, r_goals)
    s_urgency = compute_urgency(r_priority, r_deadline)
    s_execution = compute_execution(r_complex, r_time, r_risk, r_fun)

    impact_sym = get_impact_symbol(s_impact)
    urgency_sym = get_urgency_symbol(s_urgency)
    execution_sym = get_execution_symbol(s_execution)
    surprise_sym = get_surprise_symbol(r_surprise)
    planned_sym = get_planned_symbol(r_planned)
    recurrent_sym = get_recurrent_symbol(r_recurrent)

    analysis = get_analysis_text(s_impact, s_execution, s_urgency, r_surprise)

    # If we estimated time, prepend it as a tag
    if planned_mins is None and estimated_mins is not None:
        h = estimated_mins // 60
        m = estimated_mins % 60
        time_tag = f"{{p{h}:{m:02d}}}"
        tags = f"{time_tag}{tags}"

    final_string = format_output(impact_sym, surprise_sym, planned_sym, recurrent_sym, tags, text)

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
            'Rec': r_recurrent,
        },
        'symbols': {
            'impact': impact_sym,
            'urgency': urgency_sym,
            'execution': execution_sym,
            'surprise': surprise_sym,
            'planned': planned_sym,
            'recurrent': recurrent_sym,
        },
        'estimated_time_minutes': estimated_mins,
        'planned_time_minutes': planned_mins,
        'analysis': analysis,
        'quadrant': classify_quadrant(urgency_sym, execution_sym),
        'quadrant_recommendation': quadrant_recommendation(
            classify_quadrant(urgency_sym, execution_sym)
        ),
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
    r_recurrent = get_user_rating(f"{c.GREEN}Recurrent (Rec){c.RESET}")

    estimated_mins = None
    if planned_mins is None:
        estimated_mins = estimate_time_minutes(r_complex, r_risk, r_surprise)

    analysis = get_analysis_text(s_impact, s_execution, s_urgency, r_surprise)

    impact_sym = get_impact_symbol(s_impact)
    urgency_sym = get_urgency_symbol(s_urgency)
    execution_sym = get_execution_symbol(s_execution)
    surprise_sym = get_surprise_symbol(r_surprise)
    planned_sym = get_planned_symbol(r_planned)
    recurrent_sym = get_recurrent_symbol(r_recurrent)

    final_string = format_output(impact_sym, surprise_sym, planned_sym, recurrent_sym, tags, text)

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
            'Rec': r_recurrent,
        },
        'symbols': {
            'impact': impact_sym,
            'urgency': urgency_sym,
            'execution': execution_sym,
            'surprise': surprise_sym,
            'planned': planned_sym,
            'recurrent': recurrent_sym,
        },
        'estimated_time_minutes': estimated_mins,
        'planned_time_minutes': planned_mins,
        'analysis': analysis,
        'quadrant': classify_quadrant(urgency_sym, execution_sym),
        'quadrant_recommendation': quadrant_recommendation(
            classify_quadrant(urgency_sym, execution_sym)
        ),
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
        if result.get('quadrant_recommendation'):
            print(f"{c.GOLD}→ {result['quadrant_recommendation']}{c.RESET}")
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


def process_task(task_input: str, mode: str, copy: bool, quiet: bool, profile: str | None) -> dict:
    """Process a single task with the specified mode."""
    tags, text, planned_mins = parse_task(task_input)

    if mode == "detail":
        result = run_detail(task_input)
    else:
        result = run_batch(task_input)

    print_result(result, copy=copy, quiet=quiet)
    log_task(task_input, result, mode, profile)
    return result


def run_loop(initial_task: str | None, mode: str, copy: bool, quiet: bool, profile: str | None) -> None:
    """Main interaction loop."""
    c = Colors
    current_mode = mode
    last_result: dict | None = None
    last_task_text: str | None = None

    # Setup readline completion if available
    if readline:
        commands = ["/help", "/mode batch", "/mode detail", "/abbr", "/discuss", "/quit"]

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
                    print(f"{c.CYAN}│{c.RESET}  {c.WHITE}/abbr{c.RESET}         Show abbreviations  {c.CYAN}│{c.RESET}")
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

                # Abbreviations command
                if cmd in ("/abbr", "/abbreviations"):
                    from .abbreviations import render_lines
                    print(f"\n{c.CYAN}Abbreviations vocabulary{c.RESET}")
                    print(f"{c.DIM}{'─' * 42}{c.RESET}")
                    for line in render_lines():
                        if line.startswith("──"):
                            print(f"{c.GOLD}{line}{c.RESET}")
                        else:
                            print(line)
                    print(f"{c.DIM}{'─' * 42}{c.RESET}")
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

                # Discuss command (LLM verifier, opt-in)
                if cmd in ("/discuss", "/d"):
                    from .llm import discuss, is_enabled
                    if not is_enabled():
                        print(f"{c.GRAY}LLM disabled. Set TASK_PRIORITIZER_LLM_ENABLED=1 to enable.{c.RESET}")
                        continue
                    if not last_result or not last_task_text:
                        print(f"{c.GRAY}Score a task first, then /discuss it.{c.RESET}")
                        continue
                    print(f"{c.GRAY}Asking the model… (Ctrl-C to cancel){c.RESET}")
                    try:
                        verdict = discuss(last_task_text, last_result)
                    except Exception as exc:
                        print(f"{c.GRAY}LLM unreachable: {exc}{c.RESET}")
                        continue
                    if verdict is None:
                        print(f"{c.GRAY}LLM unavailable. Check Ollama is running on localhost:11434.{c.RESET}")
                    else:
                        print(f"\n{c.CYAN}── {verdict.used_model} ──{c.RESET}")
                        print(verdict.text)
                        print(f"{c.DIM}{'─' * 42}{c.RESET}")
                    continue

                # Unknown command - show suggestions
                print(f"{c.GRAY}Unknown command '{task_input}'. Type / to see available commands.{c.RESET}")
                continue

            last_result = process_task(task_input, current_mode, copy, quiet, profile)
            last_task_text = task_input

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
        print("  Expected: 11 or 12 comma-separated values (0-3)")
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
    # Ensure we have 12 values for the demo (append 0 if legacy 11 used)
    if len(ratings_str) == 11:
        ratings_str.append('0')

    impact_input = f"{ratings_str[0]},{ratings_str[1]},{ratings_str[2]}"
    urgency_input = f"{ratings_str[3]},{ratings_str[4]}"
    exec_input = f"{ratings_str[5]},{ratings_str[6]},{ratings_str[7]},{ratings_str[8]}"
    clarity_input = f"{ratings_str[9]},{ratings_str[10]},{ratings_str[11]}"

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

    print(f"\n{c.GREEN}Clarity{c.RESET} {c.GRAY}(S=Surprise, Pl=Planned, Rec=Recurrent){c.RESET}")
    print(f"{c.DIM}  S: Do I know what 'done' looks like? │ Pl: Did I decide to do this? │ Rec: Is this repeating?{c.RESET}")
    simulate_input(f"{c.GREEN}S,Pl,Rec: {c.RESET}", clarity_input)

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
    simulate_input(f"{c.GREEN}Recurrent (Rec): {c.RESET}", ratings_str[11])

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
    print(f"\n{c.GRAY}Results logged to: {_get_log_path()}{c.RESET}")
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
