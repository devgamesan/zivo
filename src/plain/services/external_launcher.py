"""External application and terminal launch services."""

from dataclasses import dataclass, field
from time import sleep
from typing import Mapping, Protocol

from plain.adapters import ExternalLaunchAdapter, LocalExternalLaunchAdapter
from plain.models import ExternalLaunchRequest


class ExternalLaunchService(Protocol):
    """Boundary for asynchronous external process launches."""

    def execute(self, request: ExternalLaunchRequest) -> None: ...


@dataclass(frozen=True)
class LiveExternalLaunchService:
    """Launch files and terminals through the OS adapter."""

    adapter: ExternalLaunchAdapter = field(default_factory=LocalExternalLaunchAdapter)

    def execute(self, request: ExternalLaunchRequest) -> None:
        if request.kind == "open_file":
            try:
                self.adapter.open_with_default_app(request.path)
            except OSError as error:
                raise OSError(_format_open_error(request.path, str(error))) from error
            return

        try:
            self.adapter.open_terminal(request.path)
        except OSError as error:
            raise OSError(_format_terminal_error(request.path, str(error))) from error


@dataclass(frozen=True)
class FakeExternalLaunchService:
    """Deterministic external launcher used by tests."""

    failure_messages: Mapping[ExternalLaunchRequest, str] = field(default_factory=dict)
    default_delay_seconds: float = 0.0
    executed_requests: list[ExternalLaunchRequest] = field(default_factory=list)

    def execute(self, request: ExternalLaunchRequest) -> None:
        if self.default_delay_seconds > 0:
            sleep(self.default_delay_seconds)

        self.executed_requests.append(request)
        if request in self.failure_messages:
            raise OSError(self.failure_messages[request])


def _format_open_error(path: str, detail: str) -> str:
    return f"Failed to open {path}: {detail}"


def _format_terminal_error(path: str, detail: str) -> str:
    return f"Failed to open terminal in {path}: {detail}"
