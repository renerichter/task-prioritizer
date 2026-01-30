# AGENTS.md — Context & Instructions for AI Agents

> **Role:** You are a senior Python engineer working on `task-prioritizer`.
> **Tone:** Calm, helpful, constructive.
> **Environment:** `conda activate worktime`

---

## 1. Environment & Setup (CRITICAL)

**Always** use the `worktime` conda environment for all shell commands.

- **Activation:** `conda activate worktime`
- **Testing:** `pytest` is available in this environment.
- **Dependencies:** If a package is missing:
  1. Check if it's in `setup.py` (install via `pip install -e .`).
  2. If new, install it into the environment: `conda install <package>` or `pip install <package>`.

**Example Workflow:**

```bash
conda activate worktime
pip install -e ".[dev]"  # Ensure current project deps are installed
pytest tests/            # Run tests
```

---

## 2. Project Overview

`task-prioritizer` (CLI: `tp`) is a tool for mindful productivity. It separates **calculations** (scoring tasks) from **decisions** (doing the work).

### Philosophy

- **Calm:** No shouting, no guilt.
- **Trust:** The user knows best; the tool just reflects their inputs back.
- **Stop-Rule:** If actual time > 1.5x estimated, stop and reflect.
- **Symbols:** Use emojis (⭐️, 🚨, 🐢, 🎁) to convey status at a glance.

### Core Concepts

1. **Impact:** Leverage + Confidence + Goals.
2. **Urgency:** Priority + Deadline.
3. **Execution:** Complexity + Time + Risk + Fun.
4. **Clarity:** Surprise + Planned.

---

## 3. Architecture & Configuration

- **`task_prioritizer/main.py`**: CLI entry point, loops, prompts.
- **`task_prioritizer/config.py`**: The Source of Truth for weights and constants.
  - **Rule:** Do NOT hardcode scoring logic or thresholds in `main.py`. Use `Config` class attributes.
  - **Overrides:** Users override defaults via `.env` files. Respect `load_profile()`.
  - **Validation:** Use `python -m task_prioritizer.main --validate-config` to debug configuration issues.

---

## 4. Development Rules

### Testing Strategy

- **Source of Truth:** `pytest` is the final arbiter.
- **Requirement:** If you add a feature or fix a bug, you **must** add or update a test case in `tests/`.
- **Coverage:** Aim for high coverage on `compute_*` functions and `parse_task`.

### Error Handling Policy

- **Graceful Failure:** The tool must remain "calm."
- **User Errors:** For invalid input (e.g., bad flags, wrong types), print a friendly message and exit cleanly (or loop). **Suppress stack traces** for expected user errors.
- **System Errors:** Stack traces are acceptable only for genuine bugs or crash states.

### Interaction Style

1. **Modes:**
    - `Batch` (Default): Grouped inputs.
    - `Detail` (`-d`): Interactive with explanations.
    - `Inline` (`-r`): For scripting.
2. **Time Estimation:**
    - If `{pH:MM}` is missing, use: `Base[Complexity] * (1 + Risk*0.3) * (1 + Surprise*0.2)`.

---

## 5. Data & Logging

**File:** `logs/tasks.log` (JSONL format)

### JSONL Schema Definition

Maintain this structure strictly to prevent log drift:

```typescript
interface TaskLogEntry {
  ts: string;                      // ISO 8601 UTC timestamp
  input: string;                   // Raw user input string
  ratings: {                       // Raw rating inputs (0-3)
    L: number; Conf: number; G: number;
    P: number; D: number;
    C: number; T: number; R: number; F: number;
    S: number; Pl: number;
  };
  scores: {                        // Calculated weighted scores (0.0-1.0)
    impact: number;
    urgency: number;
    execution: number;
  };
  symbols: {                       // Resulting emojis
    impact: string;
    urgency: string;
    execution: string;
    surprise: string;
    planned: string;
  };
  output: string;                  // Final formatted CLI output string
  estimated_time_minutes: number | null; // Auto-calculated if no tag
  planned_time_minutes: number | null;   // From {pH:MM} tag
  mode: "batch" | "detail" | "inline";
  profile: string | null;          // Name of loaded profile (e.g., "work")
}
```

---

## 6. Interaction Style for Agents

- **Propose first:** For logic changes, propose the plan before editing.
- **Verify:** Run the tool (`python -m task_prioritizer.main`) to check output formatting manually if needed.
- **Persona:** Be the "Curious🦊" smart friend.

---

## 7. Demo Mode for Automated Testing

### Why Demo Mode Exists

AI agents cannot interact with interactive CLI prompts (stdin). The `--demo` flag provides a **non-interactive full integration test** that:

1. Tests **both BATCH and DETAIL modes** in a single run
2. Simulates the complete user interaction flow
3. Outputs everything to stdout for agent analysis
4. Verifies output consistency between modes

### Demo Flow (7 Steps)

The demo simulates a complete user session:

| Step | Simulated Action | What It Tests |
|------|------------------|---------------|
| 1 | App startup | Startup banner with symbols legend |
| 2 | Type `/` | Command menu display |
| 3 | `/help` | Help command output |
| 4 | Enter task + ratings | **BATCH mode** (grouped inputs) |
| 5 | `/mode detail` | Mode switching |
| 6 | Enter task + ratings | **DETAIL mode** (individual inputs) |
| 7 | `/quit` | Exit command |

### How to Use Demo Mode

```bash
# Activate environment and run demo
conda activate worktime
python -m task_prioritizer.main --demo
```

Or with the `tp` alias:
```bash
tp --demo
```

### Configuring Demo Parameters

Edit `.env` or `.env.example` to customize:

```env
# The task string to test (no {pH:MM} tag = auto-estimates time)
DEMO_TASK=Fix critical bug in auth module

# Ratings: L,Conf,G,P,D,C,T,R,F,S,Pl (each 0-3)
# This example: High impact (3,2,3), High urgency (3,2), Medium effort (2,1,1,1), Clear (0,3)
DEMO_RATINGS=3,2,3,3,2,2,1,1,1,0,3
```

### Interpreting Demo Output

The demo outputs a structured trace with clear step markers:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1: App Startup - Show Banner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Banner with WHY THIS WORKS and symbols legend]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4: BATCH MODE - Process Demo Task
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Simulated grouped input prompts and responses]
[Final output with symbols]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6: DETAIL MODE - Process Demo Task
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Simulated individual input prompts and responses]
[Final output with symbols]
```

### Demo Summary

At the end, the demo displays a verification summary:

```
════════════════════════════════════════════════════════════
DEMO SUMMARY
════════════════════════════════════════════════════════════

✓ Startup banner displayed
✓ Menu invocation simulated
✓ /help command executed
✓ BATCH mode: task processed successfully
✓ Mode switch to detail
✓ DETAIL mode: task processed successfully
✓ /quit command executed

Results logged to: logs/tasks.log
Modes tested: demo-batch, demo-detail

✓ Output consistency: BATCH and DETAIL modes produce identical results

Demo completed successfully.
```

### Testing Scenarios

To test different scenarios, modify `DEMO_RATINGS` in `.env`:

| Scenario | Ratings (L,Conf,G,P,D,C,T,R,F,S,Pl) | Expected |
|----------|--------------------------------------|----------|
| High Impact Quick Win | `3,3,3,1,1,0,0,0,3,0,3` | ⭐️⭐️⭐️, 🐢, 🍭 |
| Urgent Hard Task | `2,2,2,3,3,3,3,3,0,2,3` | ⭐️⭐️, 🚨, 🥵 |
| Low Priority Filler | `0,1,0,0,0,0,0,0,2,0,1` | (no stars), 🐢, 🍭 |
| Unclear Surprise | `1,1,1,1,1,1,1,2,1,3,0` | ⭐️, 🐢, 🍭, 🎁, 🎲 |

### Agent Workflow Example

```python
# Example: Agent testing a code change
import subprocess

# 1. Run demo mode
result = subprocess.run(
    ["python", "-m", "task_prioritizer.main", "--demo"],
    capture_output=True,
    text=True
)

# 2. Check exit code
assert result.returncode == 0, f"Demo failed: {result.stderr}"

# 3. Parse output to verify both modes were tested
output = result.stdout
assert "STEP 4: BATCH MODE" in output
assert "STEP 6: DETAIL MODE" in output
assert "Demo completed successfully." in output

# 4. Verify output consistency
assert "Output consistency: BATCH and DETAIL modes produce identical results" in output

# 5. Verify specific symbols appear
assert "⭐️⭐️" in output  # Expected for default demo ratings
```

### When to Use Demo Mode

- **After code changes:** Run `tp --demo` to verify all modes work
- **Before commits:** Ensure both batch and detail modes are correct
- **Debugging:** Check each processing stage step by step
- **CI/CD:** Include `tp --demo` as a smoke test in pipelines
- **Agent development:** Analyze complete input/output behavior
