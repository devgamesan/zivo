"""One-line input widget for contextual text input modes."""

from rich.text import Text
from textual.widgets import Static

from zivo.models import InputBarState


class InputBar(Static):
    """Compact input line shown near the active interaction context."""

    def __init__(
        self,
        state: InputBarState | None,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(self.format_state(state), id=id, classes=classes)
        self.state = state
        self.display = state is not None

    @staticmethod
    def format_state(state: InputBarState | None) -> Text | str:
        """Build the visible input line."""

        if state is None:
            return ""
        text = Text()
        text.append(f"[{state.mode_label}] ", style="bold reverse")
        text.append(state.prompt, style="bold")
        if not state.value:
            text.append("_", style="reverse")
        else:
            pos = state.cursor_pos
            before = state.value[:pos]
            at_cursor = state.value[pos] if pos < len(state.value) else None
            after = state.value[pos + 1 :]
            text.append(before, style="underline")
            if at_cursor is not None:
                text.append(at_cursor, style="reverse underline")
                text.append(after, style="underline")
            else:
                text.append("_", style="reverse")
        text.append(f"  {state.hint}", style="dim")
        return text

    def set_state(self, state: InputBarState | None) -> None:
        """Update the rendered input line."""

        if state == self.state:
            return

        self.state = state
        self.display = state is not None
        self.update(self.format_state(state))
