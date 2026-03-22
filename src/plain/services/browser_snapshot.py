"""Snapshot loading services for three-pane browser state."""

from dataclasses import dataclass, field
from pathlib import PurePath
from time import sleep
from typing import Mapping, Protocol

from plain.state.models import AppState, BrowserSnapshot, PaneState, build_initial_app_state


class BrowserSnapshotLoader(Protocol):
    """Boundary for loading pane snapshots outside the reducer."""

    def load_browser_snapshot(
        self,
        path: str,
        cursor_path: str | None = None,
    ) -> BrowserSnapshot: ...


@dataclass(frozen=True)
class FakeBrowserSnapshotLoader:
    """Deterministic loader used until real filesystem adapters arrive."""

    snapshots: Mapping[str, BrowserSnapshot] = field(default_factory=dict)
    failure_messages: Mapping[str, str] = field(default_factory=dict)
    default_delay_seconds: float = 0.0
    per_path_delay_seconds: Mapping[str, float] = field(default_factory=dict)

    def load_browser_snapshot(
        self,
        path: str,
        cursor_path: str | None = None,
    ) -> BrowserSnapshot:
        delay = self.per_path_delay_seconds.get(path, self.default_delay_seconds)
        if delay > 0:
            sleep(delay)

        if path in self.failure_messages:
            raise OSError(self.failure_messages[path])

        snapshot = self.snapshots.get(path)
        if snapshot is not None:
            return snapshot

        return _build_fallback_snapshot(path, cursor_path)


def snapshot_from_app_state(state: AppState) -> BrowserSnapshot:
    """Convert reducer state into a loader response payload."""

    return BrowserSnapshot(
        current_path=state.current_path,
        parent_pane=state.parent_pane,
        current_pane=state.current_pane,
        child_pane=state.child_pane,
    )


def _build_fallback_snapshot(path: str, cursor_path: str | None) -> BrowserSnapshot:
    initial_state = build_initial_app_state()
    if path == initial_state.current_path:
        return snapshot_from_app_state(initial_state)

    parent_path = str(PurePath(path).parent)
    cursor = cursor_path if cursor_path is not None else None

    return BrowserSnapshot(
        current_path=path,
        parent_pane=PaneState(directory_path=parent_path, entries=()),
        current_pane=PaneState(directory_path=path, entries=(), cursor_path=cursor),
        child_pane=PaneState(directory_path=path, entries=()),
    )
