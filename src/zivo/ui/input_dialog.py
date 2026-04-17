"""Overlay dialog for rename/create text input."""

from rich.text import Text
from textual.containers import Container
from textual.widgets import Static

from zivo.models import InputDialogState


class InputDialog(Container):
    """Overlay dialog for rename and create text input."""

    def __init__(
        self,
        state: InputDialogState | None,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.state = state

    def compose(self):
        yield Static("", id="input-dialog-title")
        yield Static("", id="input-dialog-value")
        yield Static("", id="input-dialog-hint")

    def on_mount(self) -> None:
        self.set_state(self.state)

    def set_state(self, state: InputDialogState | None) -> None:
        """Update dialog content and visibility."""

        self.state = state
        self.display = state is not None
        if state is None:
            self.query_one("#input-dialog-title", Static).update("")
            self.query_one("#input-dialog-value", Static).update("")
            self.query_one("#input-dialog-hint", Static).update("")
            return

        self.query_one("#input-dialog-title", Static).update(state.title)
        self.query_one("#input-dialog-value", Static).update(
            self._render_input(state.prompt, state.value)
        )
        self.query_one("#input-dialog-hint", Static).update(f"  {state.hint}")

    @staticmethod
    def _render_input(prompt: str, value: str) -> Text:
        text = Text()
        text.append(prompt, style="bold")
        text.append(value or "_", style="underline")
        return text
