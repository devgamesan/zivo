"""Shared models for external application and terminal launches."""

from dataclasses import dataclass
from typing import Literal

ExternalLaunchKind = Literal["open_file", "open_terminal"]


@dataclass(frozen=True)
class ExternalLaunchRequest:
    """A request to launch an external process for a path."""

    kind: ExternalLaunchKind
    path: str
