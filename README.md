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
#   tp "your task"                    # interactive mode
#   tp "task" -b                         # batch mode (guided single-line input)
#   tp "task" -r 3,2,1,0,2,1,0,1,0,2,2  # batch mode (all ratings inline)
#   tp "task" -c                      # copy result to clipboard
#   tp "task" -p work                 # use "work" profile
#   tp "task" -q                      # quiet mode (output only)
#
# Ratings order: L,Conf,G,P,D,C,T,R,F,S,Pl
#   L=Leverage, Conf=Confidence, G=Goals, P=Priority, D=Deadline,
#   C=Complex, T=Time, R=Risk, F=Fun, S=Surprise, Pl=Planned
#
# Use _ for auto-time when task has {pH:MM} tag:
#   tp "{p0:45} task" -r 3,2,1,0,2,1,_,0,1,0,2
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
# Interactive mode
tp "write a first draft"

# Batch mode (guided)
tp "fix bug" -b

# Batch mode (no prompts)
tp "fix bug" -r 2,1,2,0,1,0,0,0,0,3,3

# With clipboard copy
tp "review PR" -r 2,1,1,1,1,0,0,1,0,2,2 -c
```

---

## Usage

```bash
tp "<task string>" [options]
```

### Task String Format

```
{pH:MM}{tags...} task description
```

- `{p0:45}` — Planned time: 0 hours, 45 minutes (auto-fills Time score)
- `{P:Web}` — Custom tag (preserved in output)
- Multiple tags are allowed: `{p1:00}{P:Code}{priority:high}`

### Examples

```bash
# Interactive
tp "quick email"
tp "{p0:30} review PR"
tp "{p1:00}{P:Writing} write blog post"

# Batch mode (skip all prompts)
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
| `--batch` | `-b` | Prompt once for all ratings with a guided list |
| `--profile` | `-p` | Load a named configuration profile |
| `--copy` | `-c` | Copy result to clipboard |
| `--quiet` | `-q` | Minimal output (just the annotated task) |
| `--no-color` | | Disable colored output |
| `--validate-config` | | Check configuration and exit |
| `--help` | `-h` | Show help |
| `--version` | | Show version |

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

Use `_` for Time when your task has a `{pH:MM}` tag — the tool will auto-calculate.

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
