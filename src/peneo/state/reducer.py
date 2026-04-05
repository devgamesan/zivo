"""Pure reducer for AppState transitions."""

from dataclasses import replace

from .actions import (
    Action,
    DirectorySizesFailed,
    DirectorySizesLoaded,
    InitializeState,
    SetNotification,
    SetUiMode,
)
from .effects import ReduceResult
from .models import AppState
from .reducer_common import done
from .reducer_mutations import handle_mutation_action
from .reducer_navigation import handle_navigation_action
from .reducer_palette import handle_palette_action
from .reducer_terminal_config import handle_terminal_config_action
from .selectors import select_visible_current_entry_states


def reduce_app_state(state: AppState, action: Action) -> ReduceResult:
    """Return a new state after applying a reducer action."""

    if isinstance(action, InitializeState):
        return done(action.state)

    if isinstance(action, SetUiMode):
        return _finalize_reduce_result(state, action, done(replace(state, ui_mode=action.mode)))

    if isinstance(action, SetNotification):
        return _finalize_reduce_result(
            state,
            action,
            done(replace(state, notification=action.notification)),
        )

    for handler in (
        handle_navigation_action,
        handle_mutation_action,
        handle_palette_action,
        handle_terminal_config_action,
    ):
        result = handler(state, action, reduce_app_state)
        if result is not None:
            return _finalize_reduce_result(state, action, result)

    return _finalize_reduce_result(state, action, done(state))


def _finalize_reduce_result(
    previous_state: AppState,
    action: Action,
    result: ReduceResult,
) -> ReduceResult:
    result = _finalize_current_pane_delta(previous_state, result)
    if isinstance(action, (DirectorySizesLoaded, DirectorySizesFailed)):
        return result
    if result.state == previous_state:
        return result
    return ReduceResult(
        state=_clear_transient_deltas(result.state),
        effects=result.effects,
    )


def _finalize_current_pane_delta(
    previous_state: AppState,
    result: ReduceResult,
) -> ReduceResult:
    next_state = result.state
    if next_state == previous_state:
        return result

    changed_paths = _select_current_pane_changed_paths(previous_state, next_state)
    if changed_paths:
        next_state = replace(
            next_state,
            current_pane_delta=replace(
                next_state.current_pane_delta,
                changed_paths=changed_paths,
                revision=next_state.current_pane_delta.revision + 1,
            ),
        )
    elif next_state.current_pane_delta.changed_paths:
        next_state = replace(
            next_state,
            current_pane_delta=replace(next_state.current_pane_delta, changed_paths=()),
        )

    return ReduceResult(state=next_state, effects=result.effects)


def _select_current_pane_changed_paths(
    previous_state: AppState,
    next_state: AppState,
) -> tuple[str, ...]:
    if previous_state.sort.field == "size" or next_state.sort.field == "size":
        return ()

    previous_visible_entries = select_visible_current_entry_states(previous_state)
    next_visible_entries = select_visible_current_entry_states(next_state)
    previous_visible_paths = tuple(entry.path for entry in previous_visible_entries)
    next_visible_paths = tuple(entry.path for entry in next_visible_entries)
    if previous_visible_paths != next_visible_paths:
        return ()

    previous_selected_paths = previous_state.current_pane.selected_paths
    next_selected_paths = next_state.current_pane.selected_paths
    previous_cut_paths = _select_cut_paths(previous_state)
    next_cut_paths = _select_cut_paths(next_state)
    return tuple(
        path
        for path in next_visible_paths
        if (path in previous_selected_paths) != (path in next_selected_paths)
        or (path in previous_cut_paths) != (path in next_cut_paths)
    )


def _select_cut_paths(state: AppState) -> frozenset[str]:
    if state.clipboard.mode != "cut":
        return frozenset()
    return frozenset(state.clipboard.paths)


def _clear_transient_deltas(state: AppState) -> AppState:
    if not state.directory_size_delta.changed_paths:
        return state
    return replace(
        state,
        directory_size_delta=replace(state.directory_size_delta, changed_paths=()),
    )
