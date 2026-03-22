"""Keyboard dispatcher that normalizes Textual input into reducer actions."""

from .actions import (
    Action,
    BeginFilterInput,
    CancelFilterInput,
    CancelPasteConflict,
    ClearSelection,
    ConfirmFilterInput,
    CopyTargets,
    CutTargets,
    EnterCursorDirectory,
    GoToParentDirectory,
    MoveCursor,
    PasteClipboard,
    ReloadDirectory,
    ResolvePasteConflict,
    SetFilterQuery,
    SetFilterRecursive,
    SetNotification,
    SetUiMode,
    ToggleSelectionAndAdvance,
)
from .models import AppState, DirectoryEntryState, NotificationState
from .selectors import select_target_paths, select_visible_current_entry_states

DispatchedActions = tuple[Action, ...]

BROWSING_KEYMAP = {
    "up": "cursor_up",
    "down": "cursor_down",
    "space": "toggle_selection",
    "escape": "clear_selection",
    "ctrl+f": "begin_filter",
    "left": "go_to_parent",
    "backspace": "go_to_parent",
    "ctrl+h": "go_to_parent",
    "f5": "reload_directory",
    "right": "enter_or_open",
    "enter": "enter_or_open",
    "y": "copy_targets",
    "x": "cut_targets",
    "p": "paste_clipboard",
}

CONFLICT_KEYMAP = {
    "escape": "cancel_conflict",
    "o": "overwrite",
    "s": "skip",
    "r": "rename",
}


def iter_bound_keys() -> tuple[str, ...]:
    """Return the keys that should be installed as app bindings."""

    return tuple(dict.fromkeys((*BROWSING_KEYMAP.keys(), *CONFLICT_KEYMAP.keys())))


def dispatch_key_input(
    state: AppState,
    *,
    key: str,
    character: str | None = None,
) -> DispatchedActions:
    """Return reducer actions for the current mode and key press."""

    if state.ui_mode == "FILTER":
        return _dispatch_filter_input(state, key=key, character=character)

    if state.ui_mode == "CONFIRM":
        return _dispatch_confirm_input(key)

    if state.ui_mode == "BUSY":
        return _warn("Input ignored while processing")

    if state.ui_mode in {"RENAME", "CREATE"}:
        return _dispatch_unwired_input_mode(state.ui_mode, key)

    return _dispatch_browsing_input(state, key)


def _dispatch_browsing_input(state: AppState, key: str) -> DispatchedActions:
    visible_paths = _visible_paths(state)
    cursor_entry = _current_entry(state)
    target_paths = select_target_paths(state)

    if key == "up":
        return _supported(MoveCursor(delta=-1, visible_paths=visible_paths))

    if key == "down":
        return _supported(MoveCursor(delta=1, visible_paths=visible_paths))

    if key == "space" and state.current_pane.cursor_path is not None:
        return _supported(
            ToggleSelectionAndAdvance(
                path=state.current_pane.cursor_path,
                visible_paths=visible_paths,
            )
        )

    if key == "escape":
        return _supported(ClearSelection())

    if key == "ctrl+f":
        return _supported(BeginFilterInput())

    if key == "y":
        return _supported(CopyTargets(target_paths))

    if key == "x":
        return _supported(CutTargets(target_paths))

    if key == "p":
        return _supported(PasteClipboard())

    if key in {"left", "backspace", "ctrl+h"}:
        return _supported(GoToParentDirectory())

    if key == "f5":
        return _supported(ReloadDirectory())

    if key in {"right", "enter"}:
        if cursor_entry is not None and cursor_entry.kind == "dir":
            return _supported(EnterCursorDirectory())
        return _warn("Opening files is not implemented yet")

    return ()


def _dispatch_filter_input(
    state: AppState,
    *,
    key: str,
    character: str | None,
) -> DispatchedActions:
    if key == "escape":
        return _supported(CancelFilterInput())

    if key == "enter":
        return _supported(ConfirmFilterInput())

    if key == "backspace":
        next_query = state.filter.query[:-1]
        return _supported(SetFilterQuery(next_query, active=bool(next_query)))

    if key == "space":
        return _supported(SetFilterRecursive(not state.filter.recursive))

    if character and character.isprintable() and not character.isspace():
        return _supported(SetFilterQuery(f"{state.filter.query}{character}", active=True))

    return _warn("This key is unavailable while editing the filter")


def _dispatch_confirm_input(key: str) -> DispatchedActions:
    if key == "escape":
        return _supported(CancelPasteConflict())

    if key == "o":
        return _supported(ResolvePasteConflict("overwrite"))

    if key == "s":
        return _supported(ResolvePasteConflict("skip"))

    if key == "r":
        return _supported(ResolvePasteConflict("rename"))

    return _warn("Use o, s, r, or Esc while resolving paste conflicts")


def _dispatch_unwired_input_mode(mode: str, key: str) -> DispatchedActions:
    if key == "escape":
        return _supported(SetUiMode("BROWSING"))
    return _warn(f"Input handling for {mode} mode is not implemented yet")


def _visible_paths(state: AppState) -> tuple[str, ...]:
    return tuple(entry.path for entry in select_visible_current_entry_states(state))


def _current_entry(state: AppState) -> DirectoryEntryState | None:
    cursor_path = state.current_pane.cursor_path
    for entry in state.current_pane.entries:
        if entry.path == cursor_path:
            return entry
    return None


def _supported(*actions: Action) -> DispatchedActions:
    return (SetNotification(None), *actions)


def _warn(message: str) -> DispatchedActions:
    return (SetNotification(NotificationState(level="warning", message=message)),)
