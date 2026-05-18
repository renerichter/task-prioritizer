"""Textual TUI app for task prioritizer.

Single-screen entry experience: type a task, fill the 12 ratings, see
the prioritization output. Pure presentation layer — all scoring goes
through ``core.*`` and the result is rendered with the same symbols as
the CLI. Designed to be testable via ``textual.pilot.Pilot``.
"""

from __future__ import annotations

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Static

from ..core.estimate_suggester import suggest_estimate
from ..core.parsing import parse_ratings, parse_task
from ..core.scoring import estimate_time_minutes
from ..core.stop_rule import check_stop_rule  # noqa: F401  (exposed for tests)
from ..main import run_with_ratings
from ..persistence.log import log_task

_RATING_LABELS = [
    ("L", "Leverage"),
    ("Conf", "Confidence"),
    ("G", "Goals"),
    ("P", "Priority"),
    ("D", "Deadline"),
    ("C", "Complex"),
    ("T", "Time"),
    ("R", "Risk"),
    ("F", "Fun"),
    ("S", "Surprise"),
    ("Pl", "Planned"),
    ("Rec", "Recurrent"),
]

# Rating grid is 3 rows × 4 columns.
_GRID_COLS = 4
_GRID_ROWS = 3

_HELP_TEXT = """\
[b]Task Prioritizer — Keyboard Reference[/b]

[b]Navigation[/b]
  Arrow keys    Move between rating inputs (grid-aware)
  Tab / S-Tab   Move to next / previous focusable widget
  Enter         Activate focused button

[b]Actions[/b]
  Ctrl+Enter    Score the current task
  q             Quit

[b]Ratings (0-3)[/b]
  0 = none / not applicable
  1 = low
  2 = medium
  3 = high

[b]Workflow[/b]
  1. Type a task description (supports {p0:45} prefix for planned minutes)
  2. Fill in the 12 rating dimensions using arrow keys to navigate
  3. Press Ctrl+Enter or click [Score] to see the prioritization result
  4. [Suggest estimate] uses history to guess time needed

Press Escape or ? to close this help.
"""


class HelpScreen(ModalScreen[None]):
    """Full-screen help overlay, dismissed with Escape or ?."""

    BINDINGS = [
        Binding("escape", "dismiss_help", "Close", show=False),
        Binding("question_mark", "dismiss_help", "Close", show=False),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-box {
        width: 72;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: round $accent;
        background: $surface;
        overflow-y: auto;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Static(_HELP_TEXT)
            yield Button("Close", id="help-close", variant="primary")

    def action_dismiss_help(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#help-close")
    def _close_pressed(self) -> None:
        self.dismiss(None)


class TaskPrioritizerApp(App):
    """Minimal but complete TUI."""

    CSS = """
    Screen { layout: vertical; }
    #task-box  { height: auto; padding: 1; border: round $accent; }
    #ratings   { height: auto; padding: 1; }
    #ratings Input { width: 10; }
    #ratings Static { width: 14; content-align: right middle; }
    #result    { height: auto; padding: 1; border: round $success; }
    .row       { height: 3; }
    """

    TITLE = "Task Prioritizer"
    SUB_TITLE = "calm prioritization"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+enter", "score", "Score", priority=True),
        Binding("question_mark", "show_help", "? Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="task-box"):
            yield Static("Task (e.g. '{p0:45} write draft'):")
            yield Input(placeholder="Type a task and press Tab…", id="task-input")
        with Vertical(id="ratings"):
            yield Static("Ratings — each 0=none, 1=low, 2=medium, 3=high  (arrow keys to navigate)")
            for i in range(0, len(_RATING_LABELS), 4):
                with Horizontal(classes="row"):
                    for code, name in _RATING_LABELS[i : i + 4]:
                        yield Static(f"{name} ({code}):")
                        yield Input(value="0", id=f"r-{code}", max_length=1)
        with Horizontal():
            yield Button("Score", id="score-btn", variant="primary")
            yield Button("Suggest estimate", id="suggest-btn")
        yield Static("", id="result")
        yield Footer()

    # --- key handling for grid navigation ---

    def _rating_ids(self) -> list[str]:
        """Ordered list of rating input IDs matching the grid layout."""
        return [f"r-{code}" for code, _ in _RATING_LABELS]

    def _focused_rating_index(self) -> int | None:
        """Return index into _RATING_LABELS of the currently focused rating, or None."""
        focused = self.focused
        if focused is None:
            return None
        fid = focused.id
        if fid is None or not fid.startswith("r-"):
            return None
        ids = self._rating_ids()
        try:
            return ids.index(fid)
        except ValueError:
            return None

    def on_key(self, event) -> None:
        """Intercept arrow keys for grid-aware navigation among rating inputs."""
        idx = self._focused_rating_index()
        if idx is None:
            # Not in a rating input — also handle Up/Down for task-input → first rating
            if event.key == "down" and self.focused and getattr(self.focused, "id", None) == "task-input":
                ids = self._rating_ids()
                self.query_one(f"#{ids[0]}", Input).focus()
                event.prevent_default()
                event.stop()
            return

        _row, col = divmod(idx, _GRID_COLS)
        target: int | None = None

        if event.key == "right":
            if col < _GRID_COLS - 1 and idx + 1 < len(_RATING_LABELS):
                target = idx + 1
            elif idx + 1 < len(_RATING_LABELS):
                # Wrap to next row
                target = idx + 1
        elif event.key == "left":
            if col > 0:
                target = idx - 1
            elif idx > 0:
                # Wrap to previous row
                target = idx - 1
        elif event.key == "down":
            below = idx + _GRID_COLS
            if below < len(_RATING_LABELS):
                target = below
            else:
                # Move focus to Score button
                self.query_one("#score-btn", Button).focus()
                event.prevent_default()
                event.stop()
                return
        elif event.key == "up":
            above = idx - _GRID_COLS
            if above >= 0:
                target = above
            else:
                # Move focus to task input
                self.query_one("#task-input", Input).focus()
                event.prevent_default()
                event.stop()
                return

        if target is not None:
            ids = self._rating_ids()
            self.query_one(f"#{ids[target]}", Input).focus()
            event.prevent_default()
            event.stop()

    # --- actions ---

    def action_score(self) -> None:
        self._score()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    @on(Button.Pressed, "#score-btn")
    def _score_pressed(self) -> None:
        self._score()

    @on(Button.Pressed, "#suggest-btn")
    def _suggest_pressed(self) -> None:
        text = self.query_one("#task-input", Input).value
        if not text.strip():
            self.query_one("#result", Static).update(
                "[yellow]Type a task first.[/]"
            )
            return
        suggestion = suggest_estimate(text)
        target = self.query_one("#result", Static)
        if suggestion is None:
            target.update("[dim]No similar history yet. Estimate manually.[/]")
        else:
            target.update(suggestion.explanation)

    # --- internals ---

    def _gather_ratings_string(self) -> str:
        values = [
            self.query_one(f"#r-{code}", Input).value.strip() or "0"
            for code, _ in _RATING_LABELS
        ]
        return ",".join(values)

    def _score(self) -> None:
        text = self.query_one("#task-input", Input).value
        result_widget = self.query_one("#result", Static)
        if not text.strip():
            result_widget.update("[yellow]Type a task first.[/]")
            return
        _, _, planned_mins = parse_task(text)
        ratings = parse_ratings(self._gather_ratings_string(), planned_mins)
        if ratings is None:
            result_widget.update("[red]Ratings must be 0-3 each (12 values).[/]")
            return
        estimated_mins = None
        if planned_mins is None:
            estimated_mins = estimate_time_minutes(ratings[5], ratings[7], ratings[9])
        result = run_with_ratings(text, ratings, estimated_mins)
        result_widget.update(self._format_result(result))
        log_task(text, result, "tui", None)

    def _format_result(self, result: dict) -> str:
        lines = [
            f"[bold]{result['output']}[/]",
            f"[dim]category:[/] {result['urgency_sym']} & {result['execution_sym']}",
        ]
        if result.get("estimated_time_minutes"):
            lines.append(f"[dim]estimated:[/] ~{result['estimated_time_minutes']} min")
        if result.get("analysis"):
            lines.append(f"[cyan]{result['analysis']}[/]")
        if result.get("quadrant_recommendation"):
            lines.append(f"[yellow]→ {result['quadrant_recommendation']}[/]")
        return "\n".join(lines)


def run() -> None:
    """Entry point for ``tp-tui`` console script."""
    TaskPrioritizerApp().run()
