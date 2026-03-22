"""Application assembly for Plain."""

from collections.abc import Sequence

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal

from plain.models import ThreePaneShellData
from plain.state import (
    Action,
    AppState,
    build_initial_app_state,
    dispatch_key_input,
    reduce_app_state,
    select_shell_data,
)
from plain.ui import MainPane, SidePane, StatusBar


class PlainApp(App[None]):
    """Minimal three-pane shell used as the initial UI skeleton."""

    TITLE = "Plain"
    SUB_TITLE = "Three-pane shell"
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
        layout: horizontal;
    }

    .pane {
        height: 1fr;
        min-width: 24;
        border: round $surface;
        background: $boost;
    }

    .side-pane {
        width: 1fr;
    }

    .main-pane {
        width: 2fr;
        min-width: 40;
    }

    .pane-title {
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
        text-style: bold;
    }

    .pane-list,
    .pane-table {
        height: 1fr;
    }

    .pane-entry {
        padding: 0 1;
    }

    #status-bar {
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._app_state: AppState = build_initial_app_state()

    @property
    def app_state(self) -> AppState:
        """Expose the reducer-managed state for tests and integrations."""

        return self._app_state

    def compose(self) -> ComposeResult:
        shell = select_shell_data(self._app_state)
        yield self._build_body(shell)
        yield StatusBar(shell.status, id="status-bar")

    async def on_key(self, event: events.Key) -> None:
        """Normalize keyboard input into reducer actions."""

        actions = dispatch_key_input(
            self._app_state,
            key=event.key,
            character=event.character,
        )
        if not actions:
            return

        event.stop()
        event.prevent_default()

        if self._apply_actions(actions):
            await self._refresh_shell()

    def _build_body(self, shell: ThreePaneShellData) -> Horizontal:
        return Horizontal(
            SidePane(
                "親ディレクトリ",
                shell.parent_entries,
                id="parent-pane",
                classes="pane side-pane",
            ),
            MainPane(
                "カレントディレクトリ",
                shell.current_entries,
                id="current-pane",
                classes="pane main-pane",
            ),
            SidePane(
                "子ディレクトリ",
                shell.child_entries,
                id="child-pane",
                classes="pane side-pane",
            ),
            id="body",
        )

    def _apply_actions(self, actions: Sequence[Action]) -> bool:
        state = self._app_state
        changed = False

        for action in actions:
            next_state = reduce_app_state(state, action)
            if next_state != state:
                changed = True
            state = next_state

        self._app_state = state
        return changed

    async def _refresh_shell(self) -> None:
        shell = select_shell_data(self._app_state)
        await self.query_one("#body").remove()
        await self.query_one("#status-bar").remove()
        await self.mount(self._build_body(shell))
        await self.mount(StatusBar(shell.status, id="status-bar"))


def create_app() -> PlainApp:
    """Create the application instance."""
    return PlainApp()
