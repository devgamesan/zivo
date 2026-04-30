"""Custom action matching, expansion, and background execution."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from time import sleep
from typing import Mapping, Protocol

from zivo.models import (
    CustomActionExecutionRequest,
    CustomActionResult,
    ShellCommandResult,
)


class CustomActionService(Protocol):
    """Boundary for running resolved custom actions."""

    def execute(self, request: CustomActionExecutionRequest) -> CustomActionResult: ...


@dataclass(frozen=True)
class LiveCustomActionService:
    """Run non-interactive custom actions without a shell."""

    extra_env: Mapping[str, str] = field(default_factory=dict)

    def execute(self, request: CustomActionExecutionRequest) -> CustomActionResult:
        cwd = Path(request.cwd).expanduser().resolve(strict=False)
        if not cwd.is_dir():
            raise OSError(f"Custom action requires a directory: {cwd}")

        env = dict(os.environ)
        env.update(self.extra_env)
        completed = subprocess.run(
            list(request.command),
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return CustomActionResult(
            name=request.name,
            result=ShellCommandResult(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            ),
        )


@dataclass(frozen=True)
class FakeCustomActionService:
    """Deterministic custom action runner for tests."""

    results: Mapping[tuple[str, tuple[str, ...], str], ShellCommandResult] = field(
        default_factory=dict
    )
    failure_messages: Mapping[tuple[str, tuple[str, ...], str], str] = field(
        default_factory=dict
    )
    default_delay_seconds: float = 0.0
    executed_requests: list[CustomActionExecutionRequest] = field(default_factory=list)

    def execute(self, request: CustomActionExecutionRequest) -> CustomActionResult:
        if self.default_delay_seconds > 0:
            sleep(self.default_delay_seconds)
        self.executed_requests.append(request)
        key = (request.name, request.command, request.cwd)
        if key in self.failure_messages:
            raise OSError(self.failure_messages[key])
        return CustomActionResult(
            name=request.name,
            result=self.results.get(key, ShellCommandResult(exit_code=0)),
        )
