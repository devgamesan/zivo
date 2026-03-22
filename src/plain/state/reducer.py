"""Pure reducer for AppState transitions."""

from dataclasses import replace

from .actions import (
    Action,
    BeginFilterInput,
    CancelFilterInput,
    ClearSelection,
    ConfirmFilterInput,
    InitializeState,
    MoveCursor,
    SetCursorPath,
    SetFilterQuery,
    SetFilterRecursive,
    SetSort,
    SetStatusMessage,
    SetUiMode,
    ToggleSelection,
    ToggleSelectionAndAdvance,
)
from .models import AppState


def reduce_app_state(state: AppState, action: Action) -> AppState:
    """Return a new state after applying a reducer action."""

    if isinstance(action, InitializeState):
        return action.state

    if isinstance(action, SetUiMode):
        return replace(state, ui_mode=action.mode)

    if isinstance(action, BeginFilterInput):
        return replace(state, ui_mode="FILTER", status_message=None)

    if isinstance(action, ConfirmFilterInput):
        return replace(state, ui_mode="BROWSING", status_message=None)

    if isinstance(action, CancelFilterInput):
        return replace(
            state,
            ui_mode="BROWSING",
            filter=replace(state.filter, query="", recursive=False, active=False),
            status_message=None,
        )

    if isinstance(action, MoveCursor):
        cursor_path = _move_cursor(
            state.current_pane.cursor_path,
            action.visible_paths,
            action.delta,
        )
        return replace(
            state,
            current_pane=replace(state.current_pane, cursor_path=cursor_path),
        )

    if isinstance(action, SetCursorPath):
        if action.path is not None and action.path not in _current_entry_paths(state):
            return state
        return replace(
            state,
            current_pane=replace(state.current_pane, cursor_path=action.path),
        )

    if isinstance(action, ToggleSelection):
        if action.path not in _current_entry_paths(state):
            return state
        selected_paths = set(state.current_pane.selected_paths)
        if action.path in selected_paths:
            selected_paths.remove(action.path)
        else:
            selected_paths.add(action.path)
        return replace(
            state,
            current_pane=replace(
                state.current_pane,
                selected_paths=frozenset(selected_paths),
            ),
        )

    if isinstance(action, ToggleSelectionAndAdvance):
        if action.path not in _current_entry_paths(state):
            return state
        selected_paths = set(state.current_pane.selected_paths)
        if action.path in selected_paths:
            selected_paths.remove(action.path)
        else:
            selected_paths.add(action.path)
        cursor_path = _move_cursor(action.path, action.visible_paths, 1)
        return replace(
            state,
            current_pane=replace(
                state.current_pane,
                cursor_path=cursor_path,
                selected_paths=frozenset(selected_paths),
            ),
        )

    if isinstance(action, ClearSelection):
        return replace(
            state,
            current_pane=replace(state.current_pane, selected_paths=frozenset()),
        )

    if isinstance(action, SetFilterQuery):
        active = bool(action.query) if action.active is None else action.active
        return replace(
            state,
            filter=replace(state.filter, query=action.query, active=active),
        )

    if isinstance(action, SetFilterRecursive):
        return replace(
            state,
            filter=replace(state.filter, recursive=action.recursive),
        )

    if isinstance(action, SetSort):
        directories_first = state.sort.directories_first
        if action.directories_first is not None:
            directories_first = action.directories_first
        return replace(
            state,
            sort=replace(
                state.sort,
                field=action.field,
                descending=action.descending,
                directories_first=directories_first,
            ),
        )

    if isinstance(action, SetStatusMessage):
        return replace(state, status_message=action.message)

    return state


def _current_entry_paths(state: AppState) -> set[str]:
    return {entry.path for entry in state.current_pane.entries}


def _move_cursor(
    current_path: str | None,
    visible_paths: tuple[str, ...],
    delta: int,
) -> str | None:
    if not visible_paths:
        return None

    if current_path in visible_paths:
        current_index = visible_paths.index(current_path)
    else:
        current_index = 0

    next_index = max(0, min(len(visible_paths) - 1, current_index + delta))
    return visible_paths[next_index]
