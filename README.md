# Task Prioritizer

A calm CLI tool for choosing what to work on and knowing when to stop.

---

## What This Tool Does

**Two things, clearly separated:**

| Concept | Question it answers |
|---------|---------------------|
| **Calculations** | *What should I work on?* — Scores tasks by impact, urgency, and effort to surface the best next action. |
| **Stop-Rule** | *When should I stop?* — If actual time exceeds 1.5× your estimate, pause and reflect. Good enough is good enough. |

---

## Quick Start (< 2 minutes)

### 1. Install

```bash
pip install -e .
```

### 2. Add the `tp` function to your shell

Add this to your `~/.zshrc` (or `~/.bashrc`):

```bash
# Task Prioritizer — annotate tasks with priority symbols
# Usage:
#   tp                                   # enter loop, no task
#   tp "your task"                       # batch mode (default, grouped input)
#   tp "task" -d                         # detail mode (with explanations)
#   tp "task" -r 3,2,1,0,2,1,0,1,0,2,2   # inline ratings (no prompts)
#   tp "task" -c                         # copy result to clipboard
#   tp "task" -p work                    # use "work" profile
#   tp "task" -q                         # quiet mode (output only)
#
# Ratings order: L,Conf,G,P,D,C,T,R,F,S,Pl
#   L=Leverage, Conf=Confidence, G=Goals, P=Priority, D=Deadline,
#   C=Complex, T=Time, R=Risk, F=Fun, S=Surprise, Pl=Planned
#
# Use _ for auto-time when task has {pH:MM} tag:
#   tp "{p0:45} task" -r 3,2,1,0,2,1,_,0,1,0,2
#
# In-loop commands:
#   /help        Show quick reference
#   /mode batch  Switch to batch mode
#   /mode detail Switch to detail mode
#   /quit        Exit
tp() {
    python -m task_prioritizer.main "$@"
}
```

Then reload your shell:

```bash
source ~/.zshrc
```

### 3. Run it

```bash
# Enter the task loop (no task argument)
tp

# Batch mode (default) with a task
tp "write a first draft"

# Detail mode (with explanations)
tp "fix bug" -d

# Inline ratings (no prompts)
tp "fix bug" -r 2,1,2,0,1,0,0,0,0,3,3

# With clipboard copy
tp "review PR" -r 2,1,1,1,1,0,0,1,0,2,2 -c
```

---

## Usage

```bash
tp ["<task string>"] [options]
```

If no task is provided, the tool enters an interactive loop where you can input tasks one after another.

### Task String Format

```
{pH:MM}{tags...} task description
```

- `{p0:45}` — Planned time: 0 hours, 45 minutes (auto-fills Time score)
- `{P:Web}` — Custom tag (preserved in output)
- Multiple tags are allowed: `{p1:00}{P:Code}{priority:high}`

### Examples

```bash
# Batch mode (default)
tp "quick email"
tp "{p0:30} review PR"
tp "{p1:00}{P:Writing} write blog post"

# Detail mode (with explanations)
tp "important task" -d

# Inline ratings (skip all prompts)
tp "important task" -r 3,3,1,0,2,1,0,0,0,3,3
tp "{p0:45} fix bug" -r 2,1,2,1,1,0,_,0,1,0,3 -c  # _ = auto-time

# With profile
tp "work meeting" -p work
tp "grocery list" -p personal
```

---

## CLI Flags

| Flag | Short | Purpose |
|------|-------|---------|
| `--ratings` | `-r` | Provide all 11 ratings inline (skip prompts) |
| `--batch` | `-b` | Explicitly use batch mode (default behavior) |
| `--detail` | `-d` | Use detail mode with explanations for each category |
| `--profile` | `-p` | Load a named configuration profile |
| `--copy` | `-c` | Copy result to clipboard |
| `--quiet` | `-q` | Minimal output (just the annotated task) |
| `--no-color` | | Disable colored output |
| `--validate-config` | | Check configuration and exit |
| `--demo` | | Run in demo mode for automated testing |
| `--help` | `-h` | Show help |
| `--version` | | Show version |

---

## Modes

### Batch Mode (Default)

Prompts for ratings grouped by category:

```
Impact (L,Conf,G):    2,3,1
Urgency (P,D):        1,2
Execution (C,T,R,F):  1,_,0,2
Clarity (S,Pl):       0,3
```

Use `_` for Time when your task has a `{pH:MM}` tag — the tool will auto-calculate.

### Detail Mode (`-d`)

Same as batch mode, but with detailed explanations of each category and parameter before you start rating. Includes two worked examples to help you understand the system.

---

## Loop Commands

When running in the interactive loop (no `-r` flag), you can use these commands:

| Command | Action |
|---------|--------|
| `/help` | Show quick reference (non-destructive) |
| `/mode batch` | Switch to batch mode |
| `/mode detail` | Switch to detail mode (restarts input) |
| `/quit` | Exit the program |
| `Ctrl+C` / `Ctrl+D` | Exit the program |

---

## The Rating Scale

When prompted, enter a number from 0 to 3:

| Input | Score | Meaning |
|-------|-------|---------|
| 0 | 0.0 | None / Minimal |
| 1 | 0.3 | Low |
| 2 | 0.6 | Medium |
| 3 | 1.0 | High / Maximum |

### Ratings Order (for `-r` flag)

```
L,Conf,G,P,D,C,T,R,F,S,Pl
```

| Code | Factor | Category |
|------|--------|----------|
| L | Leverage | Impact |
| Conf | Confidence | Impact |
| G | Goals | Impact |
| P | Priority | Urgency |
| D | Deadline | Urgency |
| C | Complex | Execution |
| T | Time | Execution |
| R | Risk | Execution |
| F | Fun | Execution |
| S | Surprise | Clarity |
| Pl | Planned | Clarity |

---

## Time Estimation

If no `{pH:MM}` tag is provided, the tool estimates time based on:

```
estimated_time = BASE_TIME[complexity] × (1 + risk × 0.3) × (1 + surprise × 0.2)
```

Where BASE_TIME is:
- Complexity 0: 15 min
- Complexity 1: 45 min
- Complexity 2: 90 min
- Complexity 3: 180 min

The estimated time is shown in the output and logged.

---

## Output Symbols

### Impact (stars)

| Symbol | Meaning |
|--------|---------|
| ⭐️⭐️⭐️ | High impact (score > 0.75) |
| ⭐️⭐️ | Medium impact (score > 0.50) |
| ⭐️ | Low impact (score > 0.25) |
| *(none)* | Minimal impact |

### Urgency & Effort (category line)

| Symbol | Meaning |
|--------|---------|
| 🚨 | Urgent (score ≥ 0.5) |
| 🐢 | Calm / Not urgent |
| 🥵 | Hard / High friction (score ≥ 0.5) |
| 🍭 | Easy / Low friction |

### Clarity

| Symbol | Meaning |
|--------|---------|
| 🎁 | Surprise / Unclear (score ≥ 0.5) — expected in Phase 1 |
| 🗓️ | Planned (score ≥ 0.5) |
| 🎲 | Spontaneous / Unplanned |

---

## Logging

All tasks are logged to `logs/tasks.log` as JSONL (one JSON object per line):

```jsonc
{
  "ts": "2026-01-30T14:32:01+00:00",
  "input": "{p0:45} fix bug",
  "ratings": {"L": 1.0, "Conf": 0.6, "G": 0.3, ...},
  "scores": {"impact": 0.65, "urgency": 0.15, "execution": 0.42},
  "symbols": {"impact": "⭐️⭐️", "urgency": "🐢", ...},
  "output": "⭐️⭐️--🗓️{p0:45} fix bug",
  "estimated_time_minutes": null,
  "planned_time_minutes": 45,
  "mode": "batch",
  "profile": null
}
```

---

## Profiles

Create different configurations for different contexts.

### Setup

Create profile files in your project or home directory:

```bash
# Project-level profiles
.env.work
.env.personal

# Or in ~/.config/task-prioritizer/
~/.config/task-prioritizer/work.env
~/.config/task-prioritizer/personal.env
```

### Usage

```bash
tp "meeting prep" -p work
tp "weekend project" -p personal
```

If the profile doesn't exist, the default configuration is used.

### Example Profile (`.env.work`)

```env
# Work profile: higher weight on deadlines
WEIGHT_URGENCY_PRIORITY=0.3
WEIGHT_URGENCY_DEADLINE=0.7
```

---

## Phases

**Phase 1: Capture**
- Rough estimates are fine
- 🎁 (surprise) is expected and okay
- Focus on getting tasks visible

**Phase 2: Refine**
- Improve estimates based on experience
- Remove 🎁 as clarity emerges
- Trust your growing intuition

---

## Stop-Rule

> If actual time exceeds 1.5× your estimate, **stop and reflect**.

Ask yourself:
- What caused the overrun?
- Was the task more complex than expected?
- Did scope creep happen?

Then: adjust your next estimate. Learning happens here.

---

## Configuration

All weights and thresholds live in `.env`. Copy from `.env.example`:

```bash
cp .env.example .env
```

Edit values without touching code. Run `tp --validate-config` to check.

---

## First Run

On your first use, the tool shows a friendly welcome message explaining how it works. This appears once and is then remembered.

---

## Colors

Output uses colors for visual hierarchy:
- ⭐️ Stars in gold
- 🚨 Urgent in red
- 🐢 Calm in green
- 🎁 Surprise in magenta
- Category headings use distinct colors (Impact=gold, Urgency=red, Execution=magenta, Clarity=green)

Disable with `--no-color` or by setting `NO_COLOR=1` in your environment.

---

## Philosophy

This tool is designed to feel calm and trustworthy:

- **No judgment** — all inputs are valid
- **No guilt** — 🎁 is fine in early phases
- **No rush** — take time to think
- **No magic** — the math is simple and visible

You're doing fine. Trust the process.

---

## Demo Mode

The `--demo` flag runs a **full integration test** of both input modes (batch and detail) in a completely non-interactive way. This is useful for:

- **AI Agent Analysis:** Allows AI agents to analyze the tool's input/output behavior without needing to interact with stdin
- **CI/CD Testing:** Automated testing in pipelines where interactive input isn't possible
- **Debugging:** Verification that all modes work correctly
- **Development:** Quick sanity check after code changes

### Usage

```bash
tp --demo
```

### What Demo Mode Tests

The demo runs through a complete simulated user session:

| Step | Action | Purpose |
|------|--------|---------|
| 1 | Show startup banner | Verify welcome screen with symbols legend |
| 2 | Simulate menu (/) | Test command menu display |
| 3 | Execute /help | Test help command output |
| 4 | Process task in **BATCH** mode | Test grouped input flow |
| 5 | Switch to detail mode | Test /mode command |
| 6 | Process task in **DETAIL** mode | Test individual input flow |
| 7 | Execute /quit | Test exit command |

### Configuration

The demo mode uses pre-configured values that can be customized via `.env`:

```env
# Demo task (without timing tag for auto-estimation)
DEMO_TASK=Demo task for automated testing

# Demo ratings: L,Conf,G,P,D,C,T,R,F,S,Pl (each 0-3)
DEMO_RATINGS=2,2,2,1,1,1,1,1,2,1,2
```

### Summary Output

At the end, demo mode displays a summary with checkmarks:

```
✓ Startup banner displayed
✓ Menu invocation simulated
✓ /help command executed
✓ BATCH mode: task processed successfully
✓ Mode switch to detail
✓ DETAIL mode: task processed successfully
✓ /quit command executed

✓ Output consistency: BATCH and DETAIL modes produce identical results
```

This confirms all components are working correctly and both modes produce consistent results.

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=task_prioritizer --cov-report=term-missing
```

---

## License

MIT

---

## Ideas for Improvements

1.  **Configurable Archetypes:** (Implemented) Move hardcoded summary strings to configuration to allow custom vocabulary (e.g., "Low Hanging Fruit" instead of "Quick Win").
2.  **Persistence:** A lightweight task store (JSON/SQLite) to save prioritized tasks, enabling a `tp list` command and "marking done" workflow.
3.  **Review Mode:** A `tp review` command to reflect on yesterday's tasks ("Did this take longer than expected?").
4.  **Integrations:** Export output to Todoist, Notion, or GitHub Issues.
5.  **Stop-Rule Enforcer:** A timer mode that notifies you when you exceed the 1.5x estimate.
