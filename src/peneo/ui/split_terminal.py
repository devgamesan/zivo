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

    def compose(self) -> ComposeResult:
        yield Static("", id="split-terminal-title")
        yield Static("", id="split-terminal-status")
        with VerticalScroll(id="split-terminal-scroll"):
            yield Static("", id="split-terminal-body")

    def on_mount(self) -> None:
        self.set_state(self.state)

    def on_resize(self, _event: events.Resize) -> None:
        if self.state.visible:
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
            rendered = _render_terminal_output(
                self.state.body,
                columns=columns,
                rows=rows,
                focused=self.state.focused,
            )
        body.update(rendered)


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


def _render_terminal_output(
    output: str,
    *,
    columns: int,
    rows: int,
    focused: bool,
) -> Text:
    screen = Screen(columns, rows)
    stream = pyte.Stream(screen, strict=False)
    stream.feed(output)
    return _screen_to_text(screen, focused=focused)


def _screen_to_text(screen: Screen, *, focused: bool) -> Text:
    text = Text()
    for row in range(screen.lines):
        if row:
            text.append("\n")
        text.append_text(_screen_row_text(screen, row, focused=focused))
    return text


def _screen_row_text(screen: Screen, row: int, *, focused: bool) -> Text:
    row_buffer = screen.buffer[row]
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
