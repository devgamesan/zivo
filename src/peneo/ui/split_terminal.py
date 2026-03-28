"""Split-terminal widget."""

import pyte
from pyte.screens import Char, Screen
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.geometry import Size
from textual.widgets import Static

from peneo.models import SplitTerminalViewState


class SplitTerminalPane(Static):
    """Embedded split-terminal output pane."""

    DEFAULT_COLUMNS = 80
    DEFAULT_ROWS = 8

    DEFAULT_STATE = SplitTerminalViewState(
        visible=False,
        title="Split Terminal",
        status="closed",
        body="",
        focused=False,
    )

    def __init__(
        self,
        state: SplitTerminalViewState,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.can_focus = True
        self.state = state
        self._screen: Screen | None = None
        self._stream: pyte.Stream | None = None
        self._synced_body: str = ""
        self._screen_columns = self.DEFAULT_COLUMNS
        self._screen_rows = self.DEFAULT_ROWS

    def compose(self) -> ComposeResult:
        yield Static("", id="split-terminal-title")
        yield Static("", id="split-terminal-status")
        with VerticalScroll(id="split-terminal-scroll"):
            yield Static("", id="split-terminal-body")

    def on_mount(self) -> None:
        self.set_state(self.state)

    def on_resize(self, _event: events.Resize) -> None:
        if self.state.visible:
            self._screen_columns = 0
            self._render_body()

    def terminal_dimensions(self) -> tuple[int, int]:
        """Return the PTY size that best matches the visible body area."""

        try:
            scroll = self.query_one("#split-terminal-scroll", VerticalScroll)
        except Exception:
            return (self.DEFAULT_COLUMNS, self.DEFAULT_ROWS)

        size: Size = scroll.content_region.size
        columns = size.width or scroll.size.width or self.DEFAULT_COLUMNS
        rows = size.height or scroll.size.height or self.DEFAULT_ROWS
        return (max(20, columns), max(2, rows))

    def set_state(self, state: SplitTerminalViewState) -> None:
        """Update visibility and rendered terminal content."""

        self.state = state
        self.display = state.visible
        self.set_class(state.visible, "-visible")
        self.set_class(state.focused, "-focused")

        title = self.query_one("#split-terminal-title", Static)
        status = self.query_one("#split-terminal-status", Static)

        title.update(state.title)
        status.update(f"Status: {state.status}")
        self._render_body()

    def _render_body(self) -> None:
        body = self.query_one("#split-terminal-body", Static)
        rendered = Text("")
        if self.state.visible:
            columns, rows = self.terminal_dimensions()
            self._sync_terminal_screen(self.state.body, columns=columns, rows=rows)
            if self._screen is not None:
                rendered = _screen_to_text(self._screen, focused=self.state.focused)
        else:
            self._reset_terminal_screen()
        body.update(rendered)

    def _sync_terminal_screen(self, body: str, *, columns: int, rows: int) -> None:
        if (
            self._screen is None
            or self._stream is None
            or columns != self._screen_columns
            or rows != self._screen_rows
            or len(body) < len(self._synced_body)
            or not body.startswith(self._synced_body)
        ):
            self._reset_terminal_screen(columns=columns, rows=rows)
            if self._stream is not None and body:
                self._stream.feed(body)
                self._synced_body = body
            return

        delta = body[len(self._synced_body) :]
        if delta and self._stream is not None:
            self._stream.feed(delta)
            self._synced_body = body

    def _reset_terminal_screen(
        self,
        *,
        columns: int | None = None,
        rows: int | None = None,
    ) -> None:
        self._screen_columns = columns or self.DEFAULT_COLUMNS
        self._screen_rows = rows or self.DEFAULT_ROWS
        self._screen = Screen(self._screen_columns, self._screen_rows)
        self._stream = pyte.Stream(self._screen, strict=False)
        self._synced_body = ""


_DEFAULT_CHAR = Char(" ")
_TERMINAL_COLOR_MAP = {
    "black": "black",
    "red": "red",
    "green": "green",
    "brown": "yellow",
    "blue": "blue",
    "magenta": "magenta",
    "cyan": "cyan",
    "white": "white",
    "brightblack": "bright_black",
    "brightred": "bright_red",
    "brightgreen": "bright_green",
    "brightyellow": "bright_yellow",
    "brightblue": "bright_blue",
    "brightmagenta": "bright_magenta",
    "brightcyan": "bright_cyan",
    "brightwhite": "bright_white",
}


def _screen_to_text(screen: Screen, *, focused: bool) -> Text:
    text = Text()
    for row in range(screen.lines):
        if row:
            text.append("\n")
        text.append_text(_screen_row_text(screen, row, focused=focused))
    return text


def _screen_row_text(screen: Screen, row: int, *, focused: bool) -> Text:
    row_buffer = screen.buffer.get(row, {})
    cursor_x = -1
    if focused and not screen.cursor.hidden and row == screen.cursor.y:
        cursor_x = screen.cursor.x
    visible_columns = [index for index, char in row_buffer.items() if char.data != " "]
    if cursor_x >= 0:
        visible_columns.append(cursor_x)
    max_column = max(visible_columns, default=-1)

    row_text = Text()
    for column in range(max_column + 1):
        char = row_buffer.get(column, _DEFAULT_CHAR)
        style = _terminal_style(char, is_cursor=column == cursor_x)
        row_text.append(char.data or " ", style=style)
    return row_text


def _terminal_style(char: Char, *, is_cursor: bool) -> str | None:
    fg = char.bg if char.reverse else char.fg
    bg = char.fg if char.reverse else char.bg
    tokens: list[str] = []
    color = _TERMINAL_COLOR_MAP.get(fg)
    if color is not None:
        tokens.append(color)
    background = _TERMINAL_COLOR_MAP.get(bg)
    if background is not None:
        tokens.append(f"on {background}")
    if char.bold:
        tokens.append("bold")
    if char.italics:
        tokens.append("italic")
    if char.underscore:
        tokens.append("underline")
    if char.strikethrough:
        tokens.append("strike")
    if is_cursor:
        tokens.append("reverse")
    return " ".join(tokens) or None
