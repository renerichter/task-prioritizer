# Textual TUI (`tp-tui`)

A single-screen Textual app for users who prefer a keyboard-driven UI
over a prompt loop.

## Run

```bash
pip install -e ".[tui]"
tp-tui
```

## Screen Layout

```
┌─ Task Prioritizer · calm prioritization ─┐
│ Task (e.g. '{p0:45} write draft'):       │
│ [ Input ▏                              ] │
├──────────────────────────────────────────┤
│ Ratings — each 0=none, 1=low, …, 3=high  │
│ Leverage(L)[0]  Confidence(Conf)[0]  …   │
│ Priority(P)[0]  Deadline(D)[0]       …   │
│ Complex(C)[0]   Time(T)[0]           …   │
│ Surprise(S)[0]  Planned(Pl)[0]       …   │
├──────────────────────────────────────────┤
│ [Score]   [Suggest estimate]             │
├──────────────────────────────────────────┤
│ ⭐️⭐️ write draft 🚨 🍭                    │
│ category: 🚨 & 🍭                          │
│ → Schedule a focused block.              │
└─ q quit · ctrl+enter score ──────────────┘
```

## Keys

| Key | Action |
|-----|--------|
| `Tab` / `Shift-Tab` | Navigate inputs |
| `Ctrl-Enter` | Score the current task |
| `q` | Quit |
| `Ctrl-C` | Quit |

## Buttons

- **Score** — collects the 12 rating fields, runs `run_with_ratings()`,
  displays the formatted result, and dual-writes to JSONL + SQLite via
  `log_task()`.
- **Suggest estimate** — calls `core.estimate_suggester.suggest_estimate()`
  against your history and shows the proof bundle (similar tasks +
  median minutes).

## Architecture Notes

- All scoring routes through the same `core/*` functions as the CLI —
  no logic duplication.
- Results are written with `mode="tui"` so you can filter by source in
  the JSONL log.
- Smoke-tested via `textual.pilot.Pilot` (async); see
  `tests/test_tui_app.py`.

## Roadmap

- Multi-task table view backed by `persistence/history.recent_tasks()`.
- Stop-rule indicator (highlights tasks past 1.5× estimate).
- Inline `/discuss` button when `TASK_PRIORITIZER_LLM_ENABLED=1`.
