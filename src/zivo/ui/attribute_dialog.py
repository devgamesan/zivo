"""Read-only attribute dialog widget."""

from rich.text import Text
from textual.containers import Container
from textual.widgets import Static

from zivo.models import AttributeDialogState


class AttributeDialog(Container):
    """Simple overlay used to inspect file or directory attributes."""

    def __init__(
        self,
        state: AttributeDialogState | None,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.state = state

    def compose(self):
        yield Static("", id="attribute-dialog-title")
        yield Static("", id="attribute-dialog-lines")
        yield Static("", id="attribute-dialog-options")

    def on_mount(self) -> None:
        self.set_state(self.state)

    def set_state(self, state: AttributeDialogState | None) -> None:
        """Update dialog content and visibility."""

        self.state = state
        self.display = state is not None
        if state is None:
            self.query_one("#attribute-dialog-title", Static).update("")
            self.query_one("#attribute-dialog-lines", Static).update("")
            self.query_one("#attribute-dialog-options", Static).update("")
            return

        self.query_one("#attribute-dialog-title", Static).update(state.title)
        self.query_one("#attribute-dialog-lines", Static).update(self._render_lines(state.lines))
        self.query_one("#attribute-dialog-options", Static).update(
            f"Actions: {' | '.join(state.options)}"
        )

    @staticmethod
    def _render_lines(lines: tuple[str, ...]) -> Text:
        rendered = Text()
        for index, line in enumerate(lines):
            rendered.append(line)
            if index < len(lines) - 1:
                rendered.append("\n")
        return rendered
