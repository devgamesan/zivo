"""Pure reducer for AppState transitions."""

from dataclasses import replace
from pathlib import Path

from plain.models import PasteRequest, PasteSummary

from .actions import (
    Action,
    BeginFilterInput,
    BrowserSnapshotFailed,
    BrowserSnapshotLoaded,
    CancelFilterInput,
    CancelPasteConflict,
    ChildPaneSnapshotFailed,
    ChildPaneSnapshotLoaded,
    ClearSelection,
    ClipboardPasteCompleted,
    ClipboardPasteFailed,
    ClipboardPasteNeedsResolution,
    ConfirmFilterInput,
    CopyTargets,
    CutTargets,
    EnterCursorDirectory,
    GoToParentDirectory,
    InitializeState,
    MoveCursor,
    PasteClipboard,
    ReloadDirectory,
    RequestBrowserSnapshot,
    ResolvePasteConflict,
    SetCursorPath,
    SetFilterQuery,
    SetFilterRecursive,
    SetNotification,
    SetSort,
    SetUiMode,
    ToggleSelection,
    ToggleSelectionAndAdvance,
)
from .effects import (
    Effect,
    LoadBrowserSnapshotEffect,
    LoadChildPaneSnapshotEffect,
    ReduceResult,
    RunClipboardPasteEffect,
)
from .models import (
    AppState,
    ClipboardState,
    DirectoryEntryState,
    NotificationState,
    PaneState,
    PasteConflictState,
)


def reduce_app_state(state: AppState, action: Action) -> ReduceResult:
    """Return a new state after applying a reducer action."""

    def done(next_state: AppState, *effects: Effect) -> ReduceResult:
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
        next_state = replace(
            state,
            current_pane=replace(state.current_pane, cursor_path=cursor_path),
            notification=None,
        )
        return _sync_child_pane(next_state, cursor_path)

    if isinstance(action, SetCursorPath):
        if action.path is not None and action.path not in _current_entry_paths(state):
            return done(state)
        next_state = replace(
            state,
            current_pane=replace(state.current_pane, cursor_path=action.path),
            notification=None,
        )
        return _sync_child_pane(next_state, action.path)

    if isinstance(action, EnterCursorDirectory):
        entry = _current_entry_for_path(state, state.current_pane.cursor_path)
        if entry is None or entry.kind != "dir":
            return done(state)
        return reduce_app_state(
            state,
            RequestBrowserSnapshot(entry.path, blocking=True),
        )

    if isinstance(action, GoToParentDirectory):
        parent_path = str(Path(state.current_path).parent)
        return reduce_app_state(
            state,
            RequestBrowserSnapshot(
                parent_path,
                cursor_path=state.current_path,
                blocking=True,
            ),
        )

    if isinstance(action, ReloadDirectory):
        return reduce_app_state(
            state,
            RequestBrowserSnapshot(
                state.current_path,
                cursor_path=state.current_pane.cursor_path,
                blocking=True,
            ),
        )

    if isinstance(action, ToggleSelection):
        if action.path not in _current_entry_paths(state):
            return done(state)
        selected_paths = set(
            _normalize_selected_paths(
                state.current_pane.selected_paths,
                state.current_pane.entries,
            )
        )
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
        selected_paths = set(
            _normalize_selected_paths(
                state.current_pane.selected_paths,
                state.current_pane.entries,
            )
        )
        if action.path in selected_paths:
            selected_paths.remove(action.path)
        else:
            selected_paths.add(action.path)
        cursor_path = _move_cursor(action.path, action.visible_paths, 1)
        next_state = replace(
            state,
            current_pane=replace(
                state.current_pane,
                cursor_path=cursor_path,
                selected_paths=frozenset(selected_paths),
            ),
            notification=None,
        )
        return _sync_child_pane(next_state, cursor_path)

    if isinstance(action, ClearSelection):
        return done(
            replace(
                state,
                current_pane=replace(state.current_pane, selected_paths=frozenset()),
            )
        )

    if isinstance(action, CopyTargets):
        if not action.paths:
            return done(
                replace(
                    state,
                    notification=NotificationState(level="warning", message="Nothing to copy"),
                )
            )
        return done(
            replace(
                state,
                clipboard=ClipboardState(mode="copy", paths=action.paths),
                notification=NotificationState(
                    level="info",
                    message=_format_clipboard_message("Copied", action.paths),
                ),
            )
        )

    if isinstance(action, CutTargets):
        if not action.paths:
            return done(
                replace(
                    state,
                    notification=NotificationState(level="warning", message="Nothing to cut"),
                )
            )
        return done(
            replace(
                state,
                clipboard=ClipboardState(mode="cut", paths=action.paths),
                notification=NotificationState(
                    level="info",
                    message=_format_clipboard_message("Cut", action.paths),
                ),
            )
        )

    if isinstance(action, PasteClipboard):
        if state.clipboard.mode == "none" or not state.clipboard.paths:
            return done(
                replace(
                    state,
                    notification=NotificationState(level="warning", message="Clipboard is empty"),
                )
            )

        request = PasteRequest(
            mode=state.clipboard.mode,
            source_paths=state.clipboard.paths,
            destination_dir=state.current_pane.directory_path,
        )
        return _run_paste_request(state, request)

    if isinstance(action, ResolvePasteConflict):
        if state.paste_conflict is None:
            return done(state)
        request = replace(
            state.paste_conflict.request,
            conflict_resolution=action.resolution,
        )
        return _run_paste_request(
            replace(
                state,
                paste_conflict=None,
                ui_mode="BROWSING",
                notification=None,
            ),
            request,
        )

    if isinstance(action, CancelPasteConflict):
        return done(
            replace(
                state,
                paste_conflict=None,
                ui_mode="BROWSING",
                notification=NotificationState(level="warning", message="Paste cancelled"),
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
            pending_child_pane_request_id=None,
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
        selected_paths = frozenset()
        if action.snapshot.current_path == state.current_path:
            selected_paths = _normalize_selected_paths(
                state.current_pane.selected_paths,
                action.snapshot.current_pane.entries,
            )
        return done(
            replace(
                state,
                current_path=action.snapshot.current_path,
                parent_pane=action.snapshot.parent_pane,
                current_pane=replace(
                    action.snapshot.current_pane,
                    selected_paths=selected_paths,
                ),
                child_pane=action.snapshot.child_pane,
                notification=state.post_reload_notification,
                post_reload_notification=None,
                pending_browser_snapshot_request_id=None,
                pending_child_pane_request_id=None,
                ui_mode="BROWSING" if action.blocking else state.ui_mode,
            )
        )

    if isinstance(action, BrowserSnapshotFailed):
        if action.request_id != state.pending_browser_snapshot_request_id:
            return done(state)
        return done(
            replace(
                state,
                notification=NotificationState(level="error", message=action.message),
                post_reload_notification=None,
                pending_browser_snapshot_request_id=None,
                pending_child_pane_request_id=None,
                ui_mode="BROWSING" if action.blocking else state.ui_mode,
            )
        )

    if isinstance(action, ChildPaneSnapshotLoaded):
        if action.request_id != state.pending_child_pane_request_id:
            return done(state)
        return done(
            replace(
                state,
                child_pane=action.pane,
                notification=None,
                pending_child_pane_request_id=None,
            )
        )

    if isinstance(action, ChildPaneSnapshotFailed):
        if action.request_id != state.pending_child_pane_request_id:
            return done(state)
        return done(
            replace(
                state,
                child_pane=PaneState(directory_path=state.current_path, entries=()),
                notification=NotificationState(level="error", message=action.message),
                pending_child_pane_request_id=None,
            )
        )

    if isinstance(action, ClipboardPasteNeedsResolution):
        if action.request_id != state.pending_paste_request_id or not action.conflicts:
            return done(state)
        return done(
            replace(
                state,
                paste_conflict=PasteConflictState(
                    request=action.request,
                    conflicts=action.conflicts,
                    first_conflict=action.conflicts[0],
                ),
                pending_paste_request_id=None,
                ui_mode="CONFIRM",
            )
        )

    if isinstance(action, ClipboardPasteCompleted):
        if action.request_id != state.pending_paste_request_id:
            return done(state)

        next_clipboard = state.clipboard
        if state.clipboard.mode == "cut" and action.summary.success_count > 0:
            next_clipboard = ClipboardState()

        next_state = replace(
            state,
            clipboard=next_clipboard,
            notification=None,
            paste_conflict=None,
            post_reload_notification=_notification_for_paste_summary(action.summary),
            pending_paste_request_id=None,
            ui_mode="BROWSING",
        )
        return _request_snapshot_refresh(next_state)

    if isinstance(action, ClipboardPasteFailed):
        if action.request_id != state.pending_paste_request_id:
            return done(state)
        return done(
            replace(
                state,
                notification=NotificationState(level="error", message=action.message),
                paste_conflict=None,
                pending_paste_request_id=None,
                ui_mode="BROWSING",
            )
        )

    return done(state)


def _current_entry_paths(state: AppState) -> set[str]:
    return {entry.path for entry in state.current_pane.entries}


def _normalize_selected_paths(
    selected_paths: frozenset[str],
    entries: tuple[DirectoryEntryState, ...],
) -> frozenset[str]:
    entry_paths = {entry.path for entry in entries}
    return frozenset(path for path in selected_paths if path in entry_paths)


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


def _run_paste_request(state: AppState, request: PasteRequest) -> ReduceResult:
    request_id = state.next_request_id
    next_state = replace(
        state,
        notification=None,
        paste_conflict=None,
        pending_paste_request_id=request_id,
        next_request_id=request_id + 1,
        ui_mode="BUSY",
    )
    return ReduceResult(
        state=next_state,
        effects=(RunClipboardPasteEffect(request_id=request_id, request=request),),
    )


def _request_snapshot_refresh(state: AppState) -> ReduceResult:
    request_id = state.next_request_id
    next_state = replace(
        state,
        pending_browser_snapshot_request_id=request_id,
        pending_child_pane_request_id=None,
        next_request_id=request_id + 1,
    )
    return ReduceResult(
        state=next_state,
        effects=(
            LoadBrowserSnapshotEffect(
                request_id=request_id,
                path=state.current_path,
                cursor_path=state.current_pane.cursor_path,
                blocking=False,
            ),
        ),
    )


def _sync_child_pane(state: AppState, cursor_path: str | None) -> ReduceResult:
    entry = _current_entry_for_path(state, cursor_path)
    if entry is None or entry.kind != "dir":
        return ReduceResult(
            state=replace(
                state,
                child_pane=PaneState(directory_path=state.current_path, entries=()),
                pending_child_pane_request_id=None,
            )
        )

    if (
        entry.path == state.child_pane.directory_path
        and state.pending_child_pane_request_id is None
    ):
        return ReduceResult(state=state)

    request_id = state.next_request_id
    next_state = replace(
        state,
        pending_child_pane_request_id=request_id,
        next_request_id=request_id + 1,
    )
    return ReduceResult(
        state=next_state,
        effects=(
            LoadChildPaneSnapshotEffect(
                request_id=request_id,
                current_path=state.current_path,
                cursor_path=entry.path,
            ),
        ),
    )


def _current_entry_for_path(
    state: AppState,
    path: str | None,
) -> DirectoryEntryState | None:
    if path is None:
        return None
    for entry in state.current_pane.entries:
        if entry.path == path:
            return entry
    return None


def _format_clipboard_message(prefix: str, paths: tuple[str, ...]) -> str:
    noun = "item" if len(paths) == 1 else "items"
    return f"{prefix} {len(paths)} {noun} to clipboard"


def _notification_for_paste_summary(summary: PasteSummary) -> NotificationState:
    verb = "Copied" if summary.mode == "copy" else "Moved"
    if summary.failure_count and summary.success_count:
        return NotificationState(
            level="warning",
            message=(
                f"{verb} {summary.success_count}/{summary.total_count} items"
                f" with {summary.failure_count} failure(s)"
            ),
        )
    if summary.failure_count and not summary.success_count and not summary.skipped_count:
        return NotificationState(
            level="error",
            message=f"Failed to {summary.mode} {summary.total_count} item(s)",
        )
    if summary.skipped_count and not summary.success_count and not summary.failure_count:
        return NotificationState(
            level="info",
            message=f"Skipped {summary.skipped_count} conflicting item(s)",
        )
    message = f"{verb} {summary.success_count} item(s)"
    if summary.skipped_count:
        message += f", skipped {summary.skipped_count}"
    return NotificationState(level="info", message=message)
