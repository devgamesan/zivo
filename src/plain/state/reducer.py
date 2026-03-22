"""Pure reducer for AppState transitions."""

from dataclasses import replace

from .actions import (
    Action,
    BeginFilterInput,
    BrowserSnapshotFailed,
    BrowserSnapshotLoaded,
    CancelFilterInput,
    ClearSelection,
    ConfirmFilterInput,
    InitializeState,
    MoveCursor,
    RequestBrowserSnapshot,
    SetCursorPath,
    SetFilterQuery,
    SetFilterRecursive,
    SetNotification,
    SetSort,
    SetUiMode,
    ToggleSelection,
    ToggleSelectionAndAdvance,
)
from .effects import LoadBrowserSnapshotEffect, ReduceResult
from .models import AppState, NotificationState


def reduce_app_state(state: AppState, action: Action) -> ReduceResult:
    """Return a new state after applying a reducer action."""

    def done(next_state: AppState, *effects: LoadBrowserSnapshotEffect) -> ReduceResult:
        return ReduceResult(state=next_state, effects=effects)

    if isinstance(action, InitializeState):
        return done(action.state)

    if isinstance(action, SetUiMode):
        return done(replace(state, ui_mode=action.mode))

    if isinstance(action, BeginFilterInput):
        return done(replace(state, ui_mode="FILTER", notification=None))

    if isinstance(action, ConfirmFilterInput):
        return done(replace(state, ui_mode="BROWSING", notification=None))

    if isinstance(action, CancelFilterInput):
        return done(
            replace(
                state,
                ui_mode="BROWSING",
                filter=replace(state.filter, query="", recursive=False, active=False),
                notification=None,
            )
        )

    if isinstance(action, MoveCursor):
        cursor_path = _move_cursor(
            state.current_pane.cursor_path,
            action.visible_paths,
            action.delta,
        )
        return done(
            replace(
                state,
                current_pane=replace(state.current_pane, cursor_path=cursor_path),
            )
        )

    if isinstance(action, SetCursorPath):
        if action.path is not None and action.path not in _current_entry_paths(state):
            return done(state)
        return done(
            replace(
                state,
                current_pane=replace(state.current_pane, cursor_path=action.path),
            )
        )

    if isinstance(action, ToggleSelection):
        if action.path not in _current_entry_paths(state):
            return done(state)
        selected_paths = set(state.current_pane.selected_paths)
        if action.path in selected_paths:
            selected_paths.remove(action.path)
        else:
            selected_paths.add(action.path)
        return done(
            replace(
                state,
                current_pane=replace(
                    state.current_pane,
                    selected_paths=frozenset(selected_paths),
                ),
            )
        )

    if isinstance(action, ToggleSelectionAndAdvance):
        if action.path not in _current_entry_paths(state):
            return done(state)
        selected_paths = set(state.current_pane.selected_paths)
        if action.path in selected_paths:
            selected_paths.remove(action.path)
        else:
            selected_paths.add(action.path)
        cursor_path = _move_cursor(action.path, action.visible_paths, 1)
        return done(
            replace(
                state,
                current_pane=replace(
                    state.current_pane,
                    cursor_path=cursor_path,
                    selected_paths=frozenset(selected_paths),
                ),
            )
        )

    if isinstance(action, ClearSelection):
        return done(
            replace(
                state,
                current_pane=replace(state.current_pane, selected_paths=frozenset()),
            )
        )

    if isinstance(action, SetFilterQuery):
        active = bool(action.query) if action.active is None else action.active
        return done(
            replace(
                state,
                filter=replace(state.filter, query=action.query, active=active),
            )
        )

    if isinstance(action, SetFilterRecursive):
        return done(
            replace(
                state,
                filter=replace(state.filter, recursive=action.recursive),
            )
        )

    if isinstance(action, SetSort):
        directories_first = state.sort.directories_first
        if action.directories_first is not None:
            directories_first = action.directories_first
        return done(
            replace(
                state,
                sort=replace(
                    state.sort,
                    field=action.field,
                    descending=action.descending,
                    directories_first=directories_first,
                ),
            )
        )

    if isinstance(action, SetNotification):
        return done(replace(state, notification=action.notification))

    if isinstance(action, RequestBrowserSnapshot):
        request_id = state.next_request_id
        next_state = replace(
            state,
            notification=None,
            pending_browser_snapshot_request_id=request_id,
            next_request_id=request_id + 1,
            ui_mode="BUSY" if action.blocking else state.ui_mode,
        )
        return done(
            next_state,
            LoadBrowserSnapshotEffect(
                request_id=request_id,
                path=action.path,
                cursor_path=action.cursor_path,
                blocking=action.blocking,
            ),
        )

    if isinstance(action, BrowserSnapshotLoaded):
        if action.request_id != state.pending_browser_snapshot_request_id:
            return done(state)

        next_state = replace(
            state,
            current_path=action.snapshot.current_path,
            parent_pane=action.snapshot.parent_pane,
            current_pane=action.snapshot.current_pane,
            child_pane=action.snapshot.child_pane,
            notification=None,
            pending_browser_snapshot_request_id=None,
            ui_mode="BROWSING" if action.blocking else state.ui_mode,
        )
        return done(next_state)

    if isinstance(action, BrowserSnapshotFailed):
        if action.request_id != state.pending_browser_snapshot_request_id:
            return done(state)

        next_state = replace(
            state,
            notification=NotificationState(level="error", message=action.message),
            pending_browser_snapshot_request_id=None,
            ui_mode="BROWSING" if action.blocking else state.ui_mode,
        )
        return done(next_state)

    return done(state)


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
