from dataclasses import dataclass, field

import pytest

from plain.adapters import LocalExternalLaunchAdapter
from plain.models import ExternalLaunchRequest
from plain.services import LiveExternalLaunchService


@dataclass
class StubCommandRunner:
    executed: list[tuple[tuple[str, ...], str | None]] = field(default_factory=list)
    failing_commands: set[str] = field(default_factory=set)

    def __call__(self, command: tuple[str, ...], cwd: str | None) -> None:
        self.executed.append((command, cwd))
        if command[0] in self.failing_commands:
            raise OSError(f"{command[0]} failed")


def test_local_external_launch_adapter_uses_xdg_open_on_linux(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("plain\n", encoding="utf-8")
    runner = StubCommandRunner()
    adapter = LocalExternalLaunchAdapter(
        system_name_resolver=lambda: "Linux",
        command_available=lambda command: command if command == "xdg-open" else None,
        command_runner=runner,
    )

    adapter.open_with_default_app(str(readme))

    assert runner.executed == [(("xdg-open", str(readme.resolve())), None)]


def test_local_external_launch_adapter_falls_back_terminal_command_on_linux(tmp_path) -> None:
    runner = StubCommandRunner(failing_commands={"konsole"})
    adapter = LocalExternalLaunchAdapter(
        system_name_resolver=lambda: "Linux",
        command_available=lambda command: (
            command if command in {"konsole", "gnome-terminal"} else None
        ),
        command_runner=runner,
    )

    adapter.open_terminal(str(tmp_path))

    assert runner.executed == [
        (("konsole",), str(tmp_path)),
        (("gnome-terminal",), str(tmp_path)),
    ]


def test_local_external_launch_adapter_uses_open_on_macos(tmp_path) -> None:
    runner = StubCommandRunner()
    adapter = LocalExternalLaunchAdapter(
        system_name_resolver=lambda: "Darwin",
        command_available=lambda command: command if command == "open" else None,
        command_runner=runner,
    )

    adapter.open_terminal(str(tmp_path))

    assert runner.executed == [
        (("open", "-a", "Terminal", str(tmp_path.resolve())), str(tmp_path))
    ]


def test_live_external_launch_service_formats_open_error(tmp_path) -> None:
    missing = tmp_path / "missing.txt"
    adapter = LocalExternalLaunchAdapter(
        system_name_resolver=lambda: "Linux",
        command_available=lambda command: command if command == "xdg-open" else None,
        command_runner=StubCommandRunner(),
    )
    service = LiveExternalLaunchService(adapter=adapter)

    with pytest.raises(OSError, match=f"Failed to open {missing.resolve()}: Not found: "):
        service.execute(ExternalLaunchRequest(kind="open_file", path=str(missing)))


def test_live_external_launch_service_formats_terminal_error_for_file(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("plain\n", encoding="utf-8")
    adapter = LocalExternalLaunchAdapter(
        system_name_resolver=lambda: "Linux",
        command_available=lambda command: command if command == "konsole" else None,
        command_runner=StubCommandRunner(),
    )
    service = LiveExternalLaunchService(adapter=adapter)

    with pytest.raises(
        OSError,
        match=f"Failed to open terminal in {readme.resolve()}: Not a directory: ",
    ):
        service.execute(ExternalLaunchRequest(kind="open_terminal", path=str(readme)))
