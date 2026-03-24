"""OS adapter for launching default applications and terminals."""

import platform
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

CommandRunner = Callable[[Sequence[str], str | None], None]
CommandAvailability = Callable[[str], str | None]
SystemNameResolver = Callable[[], str]


class ExternalLaunchAdapter(Protocol):
    """Boundary for external process launches."""

    def open_with_default_app(self, path: str) -> None: ...

    def open_terminal(self, path: str) -> None: ...


@dataclass(frozen=True)
class LocalExternalLaunchAdapter:
    """Launch applications and terminals via OS-specific commands."""

    system_name_resolver: SystemNameResolver = platform.system
    command_available: CommandAvailability = shutil.which
    command_runner: CommandRunner = field(default_factory=lambda: _run_detached_command)

    def open_with_default_app(self, path: str) -> None:
        resolved_path = _resolve_existing_path(path)
        candidates = self._default_app_candidates(str(resolved_path))
        self._run_first_available(candidates, context=f"open {resolved_path}")

    def open_terminal(self, path: str) -> None:
        resolved_path = _resolve_directory_path(path)
        candidates = self._terminal_candidates(str(resolved_path))
        self._run_first_available(
            candidates,
            context=f"open terminal in {resolved_path}",
            cwd=str(resolved_path),
        )

    def _run_first_available(
        self,
        candidates: tuple[tuple[str, ...], ...],
        *,
        context: str,
        cwd: str | None = None,
    ) -> None:
        available_candidates = [
            command for command in candidates if self.command_available(command[0]) is not None
        ]
        if not available_candidates:
            raise OSError(f"No supported command found to {context}")

        errors: list[str] = []
        for command in available_candidates:
            try:
                self.command_runner(command, cwd)
                return
            except OSError as error:
                errors.append(str(error) or f"{command[0]} failed")

        raise OSError(errors[-1] if errors else f"Failed to {context}")

    def _default_app_candidates(self, path: str) -> tuple[tuple[str, ...], ...]:
        system_name = self.system_name_resolver()
        if system_name == "Linux":
            return (("xdg-open", path),)
        if system_name == "Darwin":
            return (("open", path),)
        if system_name == "Windows":
            return (("cmd", "/c", "start", "", path),)
        raise OSError(f"Unsupported operating system: {system_name}")

    def _terminal_candidates(self, path: str) -> tuple[tuple[str, ...], ...]:
        system_name = self.system_name_resolver()
        if system_name == "Linux":
            return (
                ("konsole",),
                ("gnome-terminal",),
                ("xfce4-terminal",),
                ("xterm",),
                ("x-terminal-emulator",),
            )
        if system_name == "Darwin":
            return (("open", "-a", "Terminal", path),)
        if system_name == "Windows":
            escaped_path = path.replace("'", "''")
            powershell_command = f"Set-Location -LiteralPath '{escaped_path}'"
            return (
                ("cmd", "/c", "start", "", "wt", "-d", path),
                (
                    "cmd",
                    "/c",
                    "start",
                    "",
                    "powershell",
                    "-NoExit",
                    "-Command",
                    powershell_command,
                ),
            )
        raise OSError(f"Unsupported operating system: {system_name}")


def _run_detached_command(command: Sequence[str], cwd: str | None) -> None:
    subprocess.Popen(
        list(command),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=cwd,
        start_new_session=True,
    )


def _resolve_existing_path(path: str) -> Path:
    resolved_path = Path(path).expanduser().resolve()
    if not resolved_path.exists():
        raise OSError(f"Not found: {resolved_path}")
    return resolved_path


def _resolve_directory_path(path: str) -> Path:
    resolved_path = _resolve_existing_path(path)
    if not resolved_path.is_dir():
        raise OSError(f"Not a directory: {resolved_path}")
    return resolved_path
