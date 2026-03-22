from plain.state import (
    ClearSelection,
    SetCursorPath,
    SetFilterQuery,
    SetSort,
    SetUiMode,
    ToggleSelection,
    build_initial_app_state,
    reduce_app_state,
)


def test_set_ui_mode_updates_only_mode() -> None:
    state = build_initial_app_state()

    next_state = reduce_app_state(state, SetUiMode("FILTER"))

    assert next_state.ui_mode == "FILTER"
    assert next_state.current_pane == state.current_pane
    assert next_state.filter == state.filter


def test_toggle_selection_uses_absolute_paths() -> None:
    state = build_initial_app_state()
    path = "/home/tadashi/develop/plain/README.md"

    selected_state = reduce_app_state(state, ToggleSelection(path))
    cleared_state = reduce_app_state(selected_state, ToggleSelection(path))

    assert selected_state.current_pane.selected_paths == frozenset({path})
    assert cleared_state.current_pane.selected_paths == frozenset()


def test_clear_selection_empties_selection() -> None:
    state = build_initial_app_state()
    selected_state = reduce_app_state(
        state,
        ToggleSelection("/home/tadashi/develop/plain/README.md"),
    )

    next_state = reduce_app_state(selected_state, ClearSelection())

    assert next_state.current_pane.selected_paths == frozenset()


def test_set_filter_query_returns_new_state_without_mutating_input() -> None:
    state = build_initial_app_state()

    next_state = reduce_app_state(state, SetFilterQuery("readme"))

    assert next_state.filter.query == "readme"
    assert next_state.filter.active is True
    assert state.filter.query == ""
    assert state.filter.active is False


def test_set_sort_returns_new_state_without_mutating_input() -> None:
    state = build_initial_app_state()

    next_state = reduce_app_state(
        state,
        SetSort(field="modified", descending=True, directories_first=False),
    )

    assert next_state.sort.field == "modified"
    assert next_state.sort.descending is True
    assert next_state.sort.directories_first is False
    assert state.sort.field == "name"
    assert state.sort.descending is False
    assert state.sort.directories_first is True


def test_set_cursor_path_ignores_unknown_path() -> None:
    state = build_initial_app_state()

    next_state = reduce_app_state(state, SetCursorPath("/missing"))

    assert next_state == state
