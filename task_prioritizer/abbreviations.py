"""Abbreviations vocabulary: load + lookup + expand.

Source of truth is ``docs/abbreviations.toml`` (committed in-repo). The
vocabulary was hand-curated once from the user's personal Templates FAQ
and copied into this repository. Nothing in this module reads that FAQ
at runtime — that would couple the tool to an external sync folder.
Update the TOML by hand when terms change.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SOURCE = _REPO_ROOT / "docs" / "abbreviations.toml"

# Module-level cache. ``None`` means "not loaded yet".
_cache: dict[str, Any] | None = None
_cache_source: Path | None = None

_SECTION_TO_PREFIX_LABEL = {
    "projects": "Project",
    "meetings": "Meeting",
}


def default_source_path() -> Path:
    """Return the path to the committed abbreviations TOML."""
    return _DEFAULT_SOURCE


def load(path: Path | None = None) -> dict[str, Any]:
    """Load the abbreviations file (cached).

    With no argument: return the existing cache (loaded from any source),
    or load the packaged default if none is cached.

    With an explicit path: load that file, replacing the cache.
    """
    global _cache, _cache_source
    if path is None:
        if _cache is not None:
            return _cache
        src = _DEFAULT_SOURCE
    else:
        src = Path(path)
        if _cache is not None and _cache_source == src:
            return _cache
    with open(src, "rb") as fh:
        data = tomllib.load(fh)
    for section in ("prefixes", "general", "projects", "meetings"):
        data.setdefault(section, {})
    _cache = data
    _cache_source = src
    return _cache


def reload(path: Path | None = None) -> dict[str, Any]:
    """Drop the cache and load fresh. Useful in tests."""
    global _cache, _cache_source
    _cache = None
    _cache_source = None
    return load(path)


def lookup(code: str) -> dict[str, str] | None:
    """Find an abbreviation across general/projects/meetings.

    Returns ``{"section": ..., "code": ..., "expansion": ...}`` or ``None``.
    Case-sensitive on purpose: the source vocabulary is.
    """
    data = load()
    for section in ("general", "projects", "meetings"):
        if code in data[section]:
            return {
                "section": section,
                "code": code,
                "expansion": data[section][code],
            }
    return None


def expand_tag(tag: str) -> str | None:
    """Expand a tag like ``P:Web``, ``{P:Web}``, or ``Lrn`` to readable text.

    Returns ``None`` for unknown codes and for structural tags such as
    ``p1:30`` (planned time is handled by the parser, not the vocabulary).
    """
    cleaned = tag.strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        cleaned = cleaned[1:-1]

    if ":" in cleaned:
        prefix, _, code = cleaned.partition(":")
        # Planned time tags look like p1:30 — never abbreviations.
        if prefix == "p":
            return None
        label = _SECTION_TO_PREFIX_LABEL.get(_prefix_to_section(prefix))
        if label is None:
            return None
        section = _prefix_to_section(prefix)
        expansion = load().get(section, {}).get(code)
        if expansion is None:
            return None
        return f"{label}: {expansion}"

    # Bare code: only general-section entries qualify.
    expansion = load().get("general", {}).get(cleaned)
    return expansion if expansion is not None else None


def _prefix_to_section(prefix: str) -> str | None:
    if prefix == "P":
        return "projects"
    if prefix == "M":
        return "meetings"
    return None


def list_all() -> dict[str, list[tuple[str, str]]]:
    """Group abbreviations by section as ``[(code, expansion), ...]``."""
    data = load()
    out: dict[str, list[tuple[str, str]]] = {}
    for section in ("prefixes", "general", "projects", "meetings"):
        out[section] = sorted(data[section].items())
    return out


def render_lines() -> list[str]:
    """Human-readable lines for the ``/abbr`` command."""
    grouped = list_all()
    lines: list[str] = []
    titles = {
        "prefixes": "Prefixes",
        "general": "General Tags",
        "projects": "Projects",
        "meetings": "Meetings",
    }
    for section in ("prefixes", "general", "projects", "meetings"):
        items = grouped[section]
        if not items:
            continue
        lines.append(f"── {titles[section]} ──")
        for code, expansion in items:
            lines.append(f"  {code:<6} {expansion}")
        lines.append("")
    # Drop trailing blank for cleaner output.
    if lines and lines[-1] == "":
        lines.pop()
    return lines
