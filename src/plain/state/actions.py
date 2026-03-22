"""Reducer actions for app state transitions."""

from dataclasses import dataclass

from .models import AppState, SortField, UiMode


@dataclass(frozen=True)
class InitializeState:
    """Replace the entire app state."""

    state: AppState


@dataclass(frozen=True)
class SetUiMode:
    """Change the current UI mode."""

    mode: UiMode


@dataclass(frozen=True)
class MoveCursor:
    """Move the cursor within a caller-provided visible path list."""

    delta: int
    visible_paths: tuple[str, ...]


@dataclass(frozen=True)
class SetCursorPath:
    """Set the current pane cursor to a specific absolute path."""

    path: str | None


@dataclass(frozen=True)
class ToggleSelection:
    """Toggle selection for an entry in the current pane."""

    path: str


@dataclass(frozen=True)
class ClearSelection:
    """Clear all selections in the current pane."""


@dataclass(frozen=True)
class SetFilterQuery:
    """Update the active filter query."""

    query: str
    active: bool | None = None


@dataclass(frozen=True)
class SetFilterRecursive:
    """Toggle recursive filtering mode."""

    recursive: bool


@dataclass(frozen=True)
class SetSort:
    """Update sort settings."""

    field: SortField
    descending: bool
    directories_first: bool | None = None


@dataclass(frozen=True)
class SetStatusMessage:
    """Update the transient status line message."""

    message: str | None


Action = (
    InitializeState
    | SetUiMode
    | MoveCursor
    | SetCursorPath
    | ToggleSelection
    | ClearSelection
    | SetFilterQuery
    | SetFilterRecursive
    | SetSort
    | SetStatusMessage
)
