# Changelog

## 0.3.1 — 2026-05

### Added
- **Textual TUI** (`tp-tui` console script) — single-screen keyboard UI. See [docs/tui.md](docs/tui.md).
- **`/discuss` command** — opt-in local LLM verifier via Ollama (`gemma4:e4b`). See [docs/llm.md](docs/llm.md).
- **`/abbr` command** — surfaces vocabulary cheat-sheet from `docs/abbreviations.toml`. See [docs/abbreviations.md](docs/abbreviations.md).
- **SQLite history store** (`tasks.db`) — dual-written alongside JSONL. See [docs/history.md](docs/history.md).
- **Estimate suggester** (`core.estimate_suggester.suggest_estimate`) — Jaccard-token matcher over history.
- **Decision-matrix recommendations** — each result includes a quadrant + calm sentence (`core/decision_matrix.py`).
- **Stop-rule scaffold** — `check_stop_rule()` + `StopRuleResult` ready for surfacing.
- **Clockipy adapter** — `ingest/clockipy_source.py`; decoupled from the `clockipy` package itself.
- **`tp-tui`** console script entry point.

### Changed
- **Modular refactor**: monolithic `main.py` (1448 lines) split into `core/`, `cli/`, `tui/`, `persistence/`, `ingest/`, `llm/`. Public re-exports in `main.py` preserved for backward compatibility. See [docs/architecture.md](docs/architecture.md).
- **PEP-621 packaging**: `pyproject.toml` with `[project.optional-dependencies]` (`dev`, `tui`, `llm`, `all`); `requires-python = ">=3.12"`.
- **Abbreviations format**: TOML (not YAML) — zero-dependency via stdlib `tomllib`.

### Internal
- 205 tests passing (16 test files); ruff clean.
- Architectural anti-coupling guards forbid `"Dropbox"` and `"CHECK24"` in the abbreviations module/TOML.
- `RUF001/002/003` suppressed in `pyproject.toml` for intentional Unicode (`×`, curly quotes) in docstrings.

### Deviations from initial plan
- `io/` renamed to `cli/` (would shadow Python's stdlib `io` module).
- Abbreviations stored as TOML, not YAML, to avoid an external dependency.

## 2.1.x and earlier
See `git log` for pre-2.2 history.
