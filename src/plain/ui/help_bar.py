"""One-line help widget."""

from textual.widgets import Static

from plain.models import HelpBarState


class HelpBar(Static):
    """Compact help line shown above the status bar."""

    def __init__(
        self,
        state: HelpBarState,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(state.text, id=id, classes=classes)
        self.state = state

    def set_state(self, state: HelpBarState) -> None:
        """Update the rendered help line."""

        if state == self.state:
            return
        self.state = state
        self.update(state.text)
