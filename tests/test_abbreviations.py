"""Phase 4.4 — Abbreviations loader + lookup.

Tests are written first (TDD). The vocabulary is hand-curated from
``Templates_FAQ.md``; this module must NEVER read the Dropbox file at
runtime. The committed file under ``docs/`` is the only source of truth.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from task_prioritizer import abbreviations as ab

# ---------------------------------------------------------------------------
# Loader basics
# ---------------------------------------------------------------------------


def test_default_source_file_exists_in_repo():
    """The committed TOML lives under docs/ and must be packaged with the project."""
    path = ab.default_source_path()
    assert path.exists(), f"abbreviations source missing: {path}"
    assert path.suffix == ".toml"
    # Must live somewhere inside the repo, never under Dropbox.
    assert "Dropbox" not in str(path)


def test_load_returns_expected_top_level_sections():
    data = ab.load()
    assert isinstance(data, dict)
    for key in ("version", "prefixes", "general", "projects", "meetings"):
        assert key in data, f"missing section: {key}"
    assert data["version"] == 1


def test_load_caches_and_returns_same_dict():
    a = ab.load()
    b = ab.load()
    assert a is b  # cached, no repeated disk reads


def test_load_accepts_explicit_path(tmp_path: Path):
    custom = tmp_path / "custom.toml"
    custom.write_text(
        'version = 1\n'
        '[prefixes]\nX = "experiment"\n'
        '[general]\nFoo = "Bar"\n'
        '[projects]\n'
        '[meetings]\n',
        encoding="utf-8",
    )
    data = ab.load(custom)
    assert data["general"]["Foo"] == "Bar"
    assert data["prefixes"]["X"] == "experiment"


# ---------------------------------------------------------------------------
# Lookup / expand
# ---------------------------------------------------------------------------


def test_lookup_known_project_returns_section_and_expansion():
    entry = ab.lookup("Web")
    assert entry is not None
    assert entry["section"] == "projects"
    assert entry["code"] == "Web"
    assert "WebApp" in entry["expansion"]


def test_lookup_known_meeting_returns_meeting_section():
    entry = ab.lookup("JF")
    assert entry is not None
    assert entry["section"] == "meetings"
    assert "Jour" in entry["expansion"]


def test_lookup_known_general_returns_general_section():
    entry = ab.lookup("Lrn")
    assert entry is not None
    assert entry["section"] == "general"
    assert entry["expansion"] == "Learn"


def test_lookup_unknown_returns_none():
    assert ab.lookup("ZzzNotReal") is None


def test_lookup_is_case_sensitive():
    """Matches the source vocabulary exactly; ratings/tags are case-significant."""
    assert ab.lookup("web") is None  # vs "Web"


# ---------------------------------------------------------------------------
# Tag-string expansion
# ---------------------------------------------------------------------------


def test_expand_tag_with_project_prefix():
    out = ab.expand_tag("P:Web")
    assert out is not None
    assert "Project" in out
    assert "WebApp" in out


def test_expand_tag_with_meeting_prefix():
    out = ab.expand_tag("M:Rnd")
    assert out is not None
    assert "Meeting" in out
    assert "random" in out.lower() or "Random" in out


def test_expand_tag_general_bare_code():
    assert ab.expand_tag("Lrn") == "Learn"


def test_expand_tag_unknown_returns_none():
    assert ab.expand_tag("P:Nope") is None
    assert ab.expand_tag("Nope") is None


def test_expand_tag_strips_curly_braces():
    """Accept {P:Web} or P:Web equivalently."""
    assert ab.expand_tag("{P:Web}") == ab.expand_tag("P:Web")


def test_expand_tag_ignores_planned_time_pH_MM():
    """{p1:30} is structured time, not an abbreviation; return None gracefully."""
    assert ab.expand_tag("p1:30") is None
    assert ab.expand_tag("{p0:45}") is None


# ---------------------------------------------------------------------------
# Listing / rendering for /abbr command
# ---------------------------------------------------------------------------


def test_list_all_groups_by_section():
    listing = ab.list_all()
    assert "projects" in listing
    assert "meetings" in listing
    assert "general" in listing
    assert "prefixes" in listing
    # Each section is a list of (code, expansion) tuples or dicts
    assert any(code == "Web" for code, _ in listing["projects"])
    assert any(code == "Rnd" for code, _ in listing["meetings"])


def test_render_lines_for_abbr_command_returns_human_readable():
    lines = ab.render_lines()
    assert isinstance(lines, list)
    assert all(isinstance(s, str) for s in lines)
    joined = "\n".join(lines)
    # Must mention the canonical sections.
    assert "Projects" in joined
    assert "Meetings" in joined
    assert "Web" in joined
    assert "Rnd" in joined


# ---------------------------------------------------------------------------
# Anti-coupling guarantees
# ---------------------------------------------------------------------------


def test_module_source_does_not_reference_dropbox():
    """Architectural guard: never read the FAQ live."""
    src = Path(ab.__file__).read_text(encoding="utf-8")
    assert "Dropbox" not in src
    assert "CHECK24" not in src
    assert "Templates_FAQ" not in src or "derived from" in src  # comment-only mention OK


def test_committed_toml_does_not_reference_dropbox():
    text = ab.default_source_path().read_text(encoding="utf-8")
    assert "Dropbox" not in text
    assert "CHECK24" not in text


# ---------------------------------------------------------------------------
# Reload (for tests / config swap)
# ---------------------------------------------------------------------------


def test_reload_picks_up_changes(tmp_path: Path):
    custom = tmp_path / "v.toml"
    custom.write_text(
        'version = 1\n'
        '[prefixes]\n'
        '[general]\nAaa = "first"\n'
        '[projects]\n'
        '[meetings]\n',
        encoding="utf-8",
    )
    ab.load(custom)
    assert ab.lookup("Aaa")["expansion"] == "first"

    custom.write_text(
        'version = 1\n'
        '[prefixes]\n'
        '[general]\nAaa = "second"\n'
        '[projects]\n'
        '[meetings]\n',
        encoding="utf-8",
    )
    ab.reload(custom)
    assert ab.lookup("Aaa")["expansion"] == "second"


@pytest.fixture(autouse=True)
def _restore_default_cache():
    """Each test starts with the packaged default loaded (not a tmp path)."""
    ab.reload()
    yield
    ab.reload()
