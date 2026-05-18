# Abbreviations Vocabulary

A hand-curated cheat-sheet of project-specific shorthands you can use
in task strings. Surfaces via `/abbr` in the CLI.

## File

`docs/abbreviations.toml` — flat TOML, edited by hand, loaded via
`tomllib` (zero deps).

## Structure

```toml
[meta]
description = "Personal task-vocabulary shortcuts."

[categories.tooling]
title = "Tooling shortcuts"
items = [
  { tag = "rfc", meaning = "request for comments" },
  { tag = "pr",  meaning = "pull request" },
]

[categories.life]
title = "Personal"
items = [
  { tag = "errand", meaning = "out-of-house task" },
]
```

## Lookup API

```python
from task_prioritizer.abbreviations import lookup, expand_tag, render_lines

lookup("pr")        # → "pull request" | None
expand_tag("pr")    # → "pr (pull request)" | "pr"
render_lines()      # → list[str] for /abbr display
```

## Architectural Guard

Two tests in `tests/test_abbreviations.py` forbid the substrings
`"Dropbox"` and `"CHECK24"` from appearing in either the module or the
TOML. The vocabulary may grow freely, but it must never embed the
maintainer's employer or storage-vendor specifics. This keeps the
project shareable without leakage.

## Adding a New Abbreviation

1. Edit `docs/abbreviations.toml`.
2. Append to an existing `[categories.<name>].items` list, or define a
   new category section.
3. Run the suite: `pytest tests/test_abbreviations.py -q`.
4. Verify in the CLI: `tp` → `/abbr`.

The loader caches by mtime; restart `tp` to pick up edits.
