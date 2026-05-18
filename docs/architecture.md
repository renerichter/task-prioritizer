# Architecture

Task-prioritizer is a single-developer tool. The architecture optimizes for
**readability**, **testability**, and **calm evolution**, not for scale.

## Module Layout

```
task_prioritizer/
├── main.py              CLI entry point, prompts, run_loop, run_demo
├── config.py            Source of truth for weights, thresholds, profiles
├── abbreviations.py     Hand-curated vocabulary loader (TOML)
│
├── core/                Pure logic — no I/O, no network, no filesystem
│   ├── scoring.py             weighted impact/urgency/execution math
│   ├── symbols.py             score → emoji mapping
│   ├── parsing.py             {p…} tag + rating-string parser
│   ├── analysis.py            deterministic archetype text
│   ├── decision_matrix.py     quadrant classifier + recommendations
│   ├── stop_rule.py           StopRuleResult, check_stop_rule()
│   └── estimate_suggester.py  Jaccard-token suggester over history
│
├── cli/                 Presentation layer (terminal-only)
│   ├── colors.py              ANSI constants
│   └── banners.py             welcome + help text
│
├── tui/                 Textual app (`tp-tui` console script)
│   └── app.py                 TaskPrioritizerApp
│
├── persistence/         Storage adapters
│   ├── log.py                 JSONL audit log (canonical)
│   └── history.py             SQLite store (denormalized tasks + actuals)
│
├── ingest/              External time-data sources
│   ├── time_source.py         TimeSource Protocol
│   ├── manual_source.py       in-memory ManualTimeSource
│   └── clockipy_source.py     Clockify adapter (decoupled, dict-shape tolerant)
│
└── llm/                 Opt-in local LLM verifier
    ├── ollama.py              minimal HTTP client
    └── verifier.py            `discuss()` — sparring partner prompt
```

## Design Decisions

### `cli/` instead of `io/`
`io` would shadow Python's stdlib module. We use `cli/` for terminal
presentation; the TUI lives in `tui/`.

### TOML for abbreviations
Zero-dependency via `tomllib` (Python 3.11+). Editing the vocabulary is a
flat-file change — no migrations, no schema. See
[`docs/abbreviations.toml`](abbreviations.toml).

### Architectural anti-coupling guards
Tests in `tests/test_abbreviations.py` forbid the strings `"Dropbox"` and
`"CHECK24"` from appearing in the abbreviations module or TOML file.
Vocabulary may grow, but must never reference the maintainer's
employer-specific or vendor-specific paths.

### Dual-write storage
`log_task()` writes to JSONL (canonical, append-only audit log) **and**
SQLite (`tasks.db` for queries). SQLite failures are logged to stderr
and never block the user.

### History schema (v1)
- `tasks` — one row per scored task, denormalized: 12 rating columns,
  3 score columns, estimated/planned minutes, quadrant, profile, mode.
- `actuals` — one-to-many time records per task (multi-session tracking).
- `schema_version` — single-row meta-table for future migrations.
- `UNIQUE(ts, input)` — idempotent JSONL → SQLite migration.

### TimeSource Protocol
`ingest/time_source.py` defines a 2-method Protocol:
`is_available()` + `get_actual_minutes_for(text, since, until)`. The
Clockify adapter (`clockipy_source.py`) accepts any client object with a
`get_time_entries(start, end)` method — it does **not import**
`clockipy`, so tests inject `MagicMock` and the adapter degrades to
`is_available() = False` when no client is wired.

### LLM is opt-in and fail-closed
`/discuss` requires `TASK_PRIORITIZER_LLM_ENABLED=1` **and** a reachable
Ollama instance. Either missing → calm message, no traceback. See
[llm.md](llm.md).

### Stop-rule deferred surfacing
`check_stop_rule()` and `StopRuleResult` are implemented and tested. The
UI surface for "you've gone past 1.5× — pause and reflect" will land
with richer time tracking; the underlying logic is already in place.

## Test Strategy

- `pytest` is the final arbiter.
- 205 tests across 16 files; coverage focuses on `core/*` and
  `persistence/history.py`.
- TUI: smoke tests via `textual.pilot.Pilot` (async).
- LLM: transport-mocked via `httpx.MockTransport`; one
  `TASK_PRIORITIZER_LLM_LIVE=1`-gated integration test.
- Clockipy: one `clockipy not installed` skip until the package is added
  to dev deps; the adapter itself is fully tested via `MagicMock`.

## Vision Alignment

The tool **mirrors** the user's inputs back at them with structure — it
does **not** decide. Every automated suggestion (estimate, LLM verdict,
quadrant rec) is framed as input to the user's call, never as an
override.
