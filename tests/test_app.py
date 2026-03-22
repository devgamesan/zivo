import asyncio

import pytest
from textual.css.query import NoMatches
from textual.widgets import DataTable, Label, ListView

from plain import create_app
from plain.services import FakeBrowserSnapshotLoader
from plain.state import (
    BrowserSnapshot,
    DirectoryEntryState,
    PaneState,
    RequestBrowserSnapshot,
    SetUiMode,
    reduce_app_state,
)
from plain.ui import StatusBar


def _build_snapshot(path: str, current_entries: tuple[DirectoryEntryState, ...]) -> BrowserSnapshot:
    return BrowserSnapshot(
        current_path=path,
        parent_pane=PaneState(directory_path="/tmp", entries=()),
        current_pane=PaneState(
            directory_path=path,
            entries=current_entries,
            cursor_path=current_entries[0].path if current_entries else None,
        ),
        child_pane=PaneState(directory_path=path, entries=()),
    )


async def _wait_for_status_bar(app, timeout: float = 0.5) -> StatusBar:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            return app.query_one("#status-bar", StatusBar)
        except NoMatches:
            if asyncio.get_running_loop().time() >= deadline:
                raise
            await asyncio.sleep(0.01)


def test_create_app_returns_plain_app() -> None:
    app = create_app()

    assert app.title == "Plain"
    assert app.sub_title == "Three-pane shell"


@pytest.mark.asyncio
async def test_app_renders_three_pane_shell() -> None:
    app = create_app()

    async with app.run_test():
        parent_list = app.query_one("#parent-pane-list", ListView)
        current_table = app.query_one("#current-pane-table", DataTable)
        child_list = app.query_one("#child-pane-list", ListView)
        status_bar = await _wait_for_status_bar(app)
        parent_entries = [str(item.query_one(Label).renderable) for item in parent_list.children]
        child_entries = [str(item.query_one(Label).renderable) for item in child_list.children]
        headers = [str(column.label) for column in current_table.ordered_columns]

        assert parent_entries == ["develop", "downloads", "notes.txt"]
        assert headers == ["種別", "名前", "サイズ", "更新日時"]
        assert current_table.row_count == 5
        assert child_entries == ["spec_mvp.md", "notes.md", "wireframes"]
        assert str(status_bar.renderable) == (
            "/home/tadashi/develop/plain | 5 items | 0 selected | "
            "sort: name asc | filter: none"
        )


@pytest.mark.asyncio
async def test_app_can_start_in_narrow_headless_mode() -> None:
    app = create_app()

    async with app.run_test(size=(72, 20)):
        assert app.query_one("#body")


@pytest.mark.asyncio
async def test_app_keyboard_input_updates_selection_and_cursor() -> None:
    app = create_app()

    async with app.run_test() as pilot:
        await pilot.press("space")

        status_bar = await _wait_for_status_bar(app)

        assert app.app_state.current_pane.selected_paths == {
            "/home/tadashi/develop/plain/docs"
        }
        assert app.app_state.current_pane.cursor_path == "/home/tadashi/develop/plain/src"
        assert str(status_bar.renderable) == (
            "/home/tadashi/develop/plain | 5 items | 1 selected | "
            "sort: name asc | filter: none"
        )


@pytest.mark.asyncio
async def test_app_keyboard_input_handles_filter_mode() -> None:
    app = create_app()

    async with app.run_test() as pilot:
        await pilot.press("ctrl+f", "r", "e", "a", "d", "enter")

        status_bar = await _wait_for_status_bar(app)

        assert app.app_state.ui_mode == "BROWSING"
        assert app.app_state.filter.query == "read"
        assert app.app_state.filter.active is True
        assert str(status_bar.renderable) == (
            "/home/tadashi/develop/plain | 1 items | 0 selected | "
            "sort: name asc | filter: read"
        )


@pytest.mark.asyncio
async def test_app_keyboard_input_shows_busy_warning() -> None:
    app = create_app()

    async with app.run_test() as pilot:
        app._app_state = reduce_app_state(app.app_state, SetUiMode("BUSY")).state
        await pilot.press("x")

        status_bar = await _wait_for_status_bar(app)

        assert str(status_bar.renderable) == (
            "/home/tadashi/develop/plain | 5 items | 0 selected | "
            "sort: name asc | filter: none | warning: 処理中のため入力を無視しました"
        )


@pytest.mark.asyncio
async def test_app_background_snapshot_keeps_keyboard_responsive() -> None:
    snapshot = _build_snapshot(
        "/tmp/loaded",
        (
            DirectoryEntryState("/tmp/loaded/after.txt", "after.txt", "file", size_bytes=123),
        ),
    )
    loader = FakeBrowserSnapshotLoader(
        snapshots={"/tmp/loaded": snapshot},
        default_delay_seconds=0.2,
    )
    app = create_app(snapshot_loader=loader)

    async with app.run_test() as pilot:
        await app.dispatch_actions((RequestBrowserSnapshot("/tmp/loaded"),))
        await pilot.press("space")

        assert app.app_state.current_path == "/home/tadashi/develop/plain"
        assert "/home/tadashi/develop/plain/docs" in app.app_state.current_pane.selected_paths

        await asyncio.sleep(0.25)

        status_bar = await _wait_for_status_bar(app)

        assert app.app_state.current_path == "/tmp/loaded"
        assert str(status_bar.renderable) == (
            "/tmp/loaded | 1 items | 0 selected | sort: name asc | filter: none"
        )


@pytest.mark.asyncio
async def test_app_background_snapshot_failure_shows_error() -> None:
    loader = FakeBrowserSnapshotLoader(
        failure_messages={"/tmp/fail": "permission denied"},
        default_delay_seconds=0.01,
    )
    app = create_app(snapshot_loader=loader)

    async with app.run_test():
        await app.dispatch_actions((RequestBrowserSnapshot("/tmp/fail"),))
        await asyncio.sleep(0.05)

        status_bar = await _wait_for_status_bar(app)

        assert app.app_state.current_path == "/home/tadashi/develop/plain"
        assert str(status_bar.renderable) == (
            "/home/tadashi/develop/plain | 5 items | 0 selected | "
            "sort: name asc | filter: none | error: permission denied"
        )
