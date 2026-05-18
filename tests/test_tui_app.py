"""Phase 4.9 — Textual TUI smoke tests via Pilot (async)."""

from __future__ import annotations

import pytest

from task_prioritizer.tui.app import HelpScreen, TaskPrioritizerApp


@pytest.mark.asyncio
async def test_app_boots_and_renders_header():
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Header widget exists
        assert app.query("Header")
        # All 12 rating inputs are mounted
        rating_inputs = app.query("#ratings Input")
        assert len(rating_inputs) == 12


@pytest.mark.asyncio
async def test_app_quits_cleanly_with_q():
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        await pilot.pause()
    # If we reach here, the app exited cleanly.
    assert True


@pytest.mark.asyncio
async def test_score_requires_task_text():
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app._score()
        await pilot.pause()
        result = app.query_one("#result").content
        # Static.renderable returns the rendered Text; coerce to str
        assert "Type a task first" in str(result)


@pytest.mark.asyncio
async def test_score_with_valid_input_produces_output(tmp_path, monkeypatch):
    monkeypatch.setenv("TASK_PRIORITIZER_LOG_PATH", str(tmp_path / "tasks.log"))
    monkeypatch.setenv("TASK_PRIORITIZER_HISTORY_DB", str(tmp_path / "h.db"))
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#task-input").value = "{p1:30} write report"
        # Set a few non-zero ratings
        app.query_one("#r-L").value = "3"
        app.query_one("#r-Conf").value = "2"
        app.query_one("#r-G").value = "3"
        app._score()
        await pilot.pause()
        rendered = str(app.query_one("#result").content)
        assert "write report" in rendered


@pytest.mark.asyncio
async def test_arrow_right_moves_between_rating_inputs():
    """Right arrow in first rating input should move focus to second."""
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Focus the first rating input
        app.query_one("#r-L").focus()
        await pilot.pause()
        assert app.focused.id == "r-L"
        # Press right arrow
        await pilot.press("right")
        await pilot.pause()
        assert app.focused.id == "r-Conf"


@pytest.mark.asyncio
async def test_arrow_down_moves_to_next_row():
    """Down arrow should jump to same column in next row."""
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#r-L").focus()
        await pilot.pause()
        # Down from row 0, col 0 → row 1, col 0 = "D" (Deadline)
        await pilot.press("down")
        await pilot.pause()
        assert app.focused.id == "r-D"


@pytest.mark.asyncio
async def test_arrow_up_from_rating_to_task_input():
    """Up arrow from first row should move to task input."""
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#r-L").focus()
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        assert app.focused.id == "task-input"


@pytest.mark.asyncio
async def test_arrow_down_from_task_input_to_first_rating():
    """Down arrow from task input should move to first rating."""
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#task-input").focus()
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        assert app.focused.id == "r-L"


@pytest.mark.asyncio
async def test_arrow_down_from_last_row_focuses_score_button():
    """Down arrow from last rating row should move to Score button."""
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Last row starts at index 8: F, S, Pl, Rec
        app.query_one("#r-F").focus()
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        assert app.focused.id == "score-btn"


@pytest.mark.asyncio
async def test_help_screen_opens_and_closes():
    """? key should open help, Escape should close it."""
    app = TaskPrioritizerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Focus the Score button (not an Input) so ? key isn't captured
        app.query_one("#score-btn").focus()
        await pilot.pause()
        await pilot.press("question_mark")
        await pilot.pause()
        # Help screen should be on the stack
        assert isinstance(app.screen, HelpScreen)
        # Dismiss with escape
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, HelpScreen)
