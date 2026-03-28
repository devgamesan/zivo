"""Generate deterministic README screenshots for Peneo."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Awaitable, Callable

from textual.css.query import NoMatches
from textual.pilot import Pilot
from textual.widgets import DataTable

from peneo import create_app
from peneo.models import (
    PasteConflict,
    PasteConflictPrompt,
    PasteExecutionResult,
    PasteRequest,
    PasteSummary,
)
from peneo.services import FakeClipboardOperationService, FakeSplitTerminalService
from peneo.ui import AttributeDialog, ConflictDialog

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "docs" / "resources" / "capture-fixtures" / "readme-screenshots"
PROJECT_ROOT = FIXTURE_ROOT / "project"
OUTPUT_DIR = REPO_ROOT / "docs" / "resources"
FIXED_TIMESTAMP = datetime(2024, 12, 20, 12, 0, 0).timestamp()
VIEWPORT_SIZE = (132, 40)
SCREENSHOT_SIZE = "1629,1026"
SCREENSHOT_THEME = "tokyo-night"


@dataclass(frozen=True)
class CaptureSpec:
    """One README screenshot to generate."""

    output_name: str
    runner: Callable[[], Awaitable[None]]


def get_capture_output_names() -> tuple[str, ...]:
    """Return the ordered README screenshot output names."""

    return tuple(spec.output_name for spec in _build_capture_specs())


async def generate_readme_screenshots() -> None:
    """Render all README screenshots into docs/resources."""

    _ensure_fixture_exists()
    _ensure_browser_renderer_available()
    _set_fixed_mtimes(FIXTURE_ROOT)

    for spec in _build_capture_specs():
        await spec.runner()


def _build_capture_specs() -> tuple[CaptureSpec, ...]:
    return (
        CaptureSpec("screen1.png", _capture_overview),
        CaptureSpec("screen-split-terminal.png", _capture_split_terminal),
        CaptureSpec("screen-multi-select.png", _capture_multi_select),
        CaptureSpec("screen-command-palette.png", _capture_command_palette),
        CaptureSpec("screen-filter.png", _capture_filter),
        CaptureSpec("screen-attributes.png", _capture_attributes),
    )


def _ensure_fixture_exists() -> None:
    required_paths = (
        FIXTURE_ROOT / "archive",
        PROJECT_ROOT,
        PROJECT_ROOT / "assets",
        PROJECT_ROOT / "docs",
        PROJECT_ROOT / "src",
    )
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing README screenshot fixtures: {', '.join(missing)}")


def _ensure_browser_renderer_available() -> None:
    if _find_browser_command() is None:
        raise RuntimeError(
            "A headless Chrome-compatible browser is required to generate PNG screenshots"
        )


def _set_fixed_mtimes(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        os.utime(path, (FIXED_TIMESTAMP, FIXED_TIMESTAMP), follow_symlinks=False)
    os.utime(root, (FIXED_TIMESTAMP, FIXED_TIMESTAMP), follow_symlinks=False)


async def _capture_overview() -> None:
    app = create_app(initial_path=PROJECT_ROOT)
    await _capture_app(app=app, output_name="screen1.png")


async def _capture_split_terminal() -> None:
    split_terminal_service = FakeSplitTerminalService()
    app = create_app(
        initial_path=PROJECT_ROOT,
        split_terminal_service=split_terminal_service,
    )

    async def setup(app, pilot: Pilot) -> None:
        await pilot.press("ctrl+t")
        await _wait_for(lambda: len(split_terminal_service.sessions) == 1, "split terminal start")
        split_terminal_service.sessions[0].emit_output(
            "$ ls -l\r\n"
            "total 20\r\n"
            "drwxr-xr-x 3 demo demo 4096 Dec 20 12:00 assets\r\n"
            "drwxr-xr-x 2 demo demo 4096 Dec 20 12:00 docs\r\n"
            "-rw-r--r-- 1 demo demo   76 Dec 20 12:00 guide.md\r\n"
            "-rw-r--r-- 1 demo demo   82 Dec 20 12:00 notes.txt\r\n"
            "-rw-r--r-- 1 demo demo   92 Dec 20 12:00 tasks.json\r\n"
        )
        await asyncio.sleep(0.1)

    await _capture_app(app=app, output_name="screen-split-terminal.png", setup=setup)


async def _capture_multi_select() -> None:
    selected_paths = (
        str(PROJECT_ROOT / "guide.md"),
        str(PROJECT_ROOT / "notes.txt"),
    )
    initial_request = PasteRequest(
        mode="copy",
        source_paths=selected_paths,
        destination_dir=str(PROJECT_ROOT),
    )
    rename_request = PasteRequest(
        mode="copy",
        source_paths=selected_paths,
        destination_dir=str(PROJECT_ROOT),
        conflict_resolution="rename",
    )
    clipboard_service = FakeClipboardOperationService(
        results={
            initial_request: PasteConflictPrompt(
                request=initial_request,
                conflicts=tuple(
                    PasteConflict(source_path=path, destination_path=path)
                    for path in selected_paths
                ),
            ),
            rename_request: PasteExecutionResult(
                summary=PasteSummary(
                    mode="copy",
                    destination_dir=str(PROJECT_ROOT),
                    total_count=len(selected_paths),
                    success_count=len(selected_paths),
                    skipped_count=0,
                    failures=(),
                    conflict_resolution="rename",
                )
            ),
        }
    )
    app = create_app(initial_path=PROJECT_ROOT, clipboard_service=clipboard_service)

    async def setup(app, pilot: Pilot) -> None:
        await pilot.press("down", "down", "down")
        await pilot.press("space")
        await pilot.press("space")
        await pilot.press("y", "p")
        await _wait_for_dialog(app, ConflictDialog, "#conflict-dialog")

    await _capture_app(app=app, output_name="screen-multi-select.png", setup=setup)


async def _capture_command_palette() -> None:
    app = create_app(initial_path=PROJECT_ROOT)

    async def setup(app, pilot: Pilot) -> None:
        await pilot.press(":")
        await _wait_for(lambda: app.app_state.ui_mode == "PALETTE", "command palette")
        await asyncio.sleep(0.05)

    await _capture_app(app=app, output_name="screen-command-palette.png", setup=setup)


async def _capture_filter() -> None:
    app = create_app(initial_path=PROJECT_ROOT)

    async def setup(app, pilot: Pilot) -> None:
        await pilot.press("/")
        await pilot.press("g", "u", "i", "d", "e")
        await _wait_for_row_count(app, 1)

    await _capture_app(app=app, output_name="screen-filter.png", setup=setup)


async def _capture_attributes() -> None:
    app = create_app(initial_path=PROJECT_ROOT)

    async def setup(app, pilot: Pilot) -> None:
        await pilot.press("down", "down", "down")
        await pilot.press(":")
        await pilot.press("a", "t", "t", "r")
        await pilot.press("enter")
        await _wait_for_dialog(app, AttributeDialog, "#attribute-dialog")

    await _capture_app(app=app, output_name="screen-attributes.png", setup=setup)


async def _capture_app(
    *,
    app,
    output_name: str,
    setup: Callable[[object, Pilot], Awaitable[None]] | None = None,
) -> None:
    with TemporaryDirectory() as temp_dir:
        app.theme = SCREENSHOT_THEME
        async with app.run_test(size=VIEWPORT_SIZE) as pilot:
            await _wait_for_snapshot_loaded(app, str(PROJECT_ROOT))
            if setup is not None:
                await setup(app, pilot)
            await asyncio.sleep(0.1)
            svg_path = Path(
                app.save_screenshot(
                    filename=output_name.removesuffix(".png") + ".svg",
                    path=temp_dir,
                )
            )

        destination = OUTPUT_DIR / output_name
        _render_svg_with_browser(svg_path, destination)


def _find_browser_command() -> str | None:
    for candidate in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
    ):
        resolved = shutil.which(candidate)
        if resolved is not None:
            return resolved
    return None


def _render_svg_with_browser(svg_path: Path, destination: Path) -> None:
    browser = _find_browser_command()
    if browser is None:
        raise RuntimeError("No headless browser available for README screenshot generation")

    result = subprocess.run(
        [
            browser,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={SCREENSHOT_SIZE}",
            f"--screenshot={destination}",
            svg_path.resolve().as_uri(),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to render SVG with browser: "
            + (result.stderr.strip() or result.stdout.strip() or "unknown error")
        )


async def _wait_for_snapshot_loaded(app, expected_path: str, timeout: float = 3.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        if (
            app.app_state.current_path == expected_path
            and app.app_state.pending_browser_snapshot_request_id is None
            and app.app_state.current_pane.entries
        ):
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise RuntimeError(f"snapshot did not finish for {expected_path}")
        await asyncio.sleep(0.01)


async def _wait_for_row_count(app, expected_count: int, timeout: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            table = app.query_one("#current-pane-table", DataTable)
        except NoMatches:
            table = None
        if table is not None and table.row_count == expected_count:
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise RuntimeError(f"row_count did not become {expected_count}")
        await asyncio.sleep(0.01)


async def _wait_for_dialog(app, widget_type, selector: str, timeout: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            widget = app.query_one(selector, widget_type)
        except NoMatches:
            widget = None
        if widget is not None and widget.display:
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise RuntimeError(f"{selector} did not become visible")
        await asyncio.sleep(0.01)


async def _wait_for(
    predicate: Callable[[], bool],
    description: str,
    timeout: float = 1.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        if predicate():
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise RuntimeError(f"Timed out waiting for {description}")
        await asyncio.sleep(0.01)
