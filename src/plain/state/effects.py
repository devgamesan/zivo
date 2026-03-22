"""Pure effect descriptions emitted by the reducer."""

from dataclasses import dataclass

from .models import AppState


@dataclass(frozen=True)
class LoadBrowserSnapshotEffect:
    """Request a browser snapshot load outside the reducer."""

    request_id: int
    path: str
    cursor_path: str | None = None
    blocking: bool = False


Effect = LoadBrowserSnapshotEffect


@dataclass(frozen=True)
class ReduceResult:
    """State transition result plus side effects to run externally."""

    state: AppState
    effects: tuple[Effect, ...] = ()
