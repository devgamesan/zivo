from plain.state import (
    BeginFilterInput,
    CancelFilterInput,
    ClearSelection,
    ConfirmFilterInput,
    SetCursorPath,
    SetFilterQuery,
    SetSort,
    SetUiMode,
    ToggleSelection,
    ToggleSelectionAndAdvance,
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


def test_begin_filter_input_switches_mode_without_mutating_query() -> None:
    state = build_initial_app_state()

    next_state = reduce_app_state(state, BeginFilterInput())

    assert next_state.ui_mode == "FILTER"
    assert next_state.filter == state.filter


def test_confirm_filter_input_returns_to_browsing() -> None:
    state = build_initial_app_state()
    state = reduce_app_state(state, SetUiMode("FILTER"))

    next_state = reduce_app_state(state, ConfirmFilterInput())

    assert next_state.ui_mode == "BROWSING"


def test_cancel_filter_input_clears_query_and_recursive_flag() -> None:
    state = build_initial_app_state()
    state = reduce_app_state(state, SetUiMode("FILTER"))
    state = reduce_app_state(state, SetFilterQuery("readme"))

    next_state = reduce_app_state(state, CancelFilterInput())

    assert next_state.ui_mode == "BROWSING"
    assert next_state.filter.query == ""
    assert next_state.filter.active is False
    assert next_state.filter.recursive is False


def test_toggle_selection_and_advance_moves_cursor_to_next_visible_entry() -> None:
    state = build_initial_app_state()
    current_path = "/home/tadashi/develop/plain/docs"
    visible_paths = (
        "/home/tadashi/develop/plain/docs",
        "/home/tadashi/develop/plain/src",
        "/home/tadashi/develop/plain/tests",
        "/home/tadashi/develop/plain/README.md",
        "/home/tadashi/develop/plain/pyproject.toml",
    )

    next_state = reduce_app_state(
        state,
        ToggleSelectionAndAdvance(path=current_path, visible_paths=visible_paths),
    )

    assert next_state.current_pane.selected_paths == frozenset({current_path})
    assert next_state.current_pane.cursor_path == "/home/tadashi/develop/plain/src"
