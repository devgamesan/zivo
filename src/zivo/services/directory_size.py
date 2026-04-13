"""Recursive directory-size services."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from zivo.adapters import DirectorySizeCancelled, DirectorySizeReader, LocalFilesystemAdapter


class DirectorySizeService(Protocol):
    """Boundary for recursive directory-size calculations."""

    def calculate_sizes(
        self,
        paths: tuple[str, ...],
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, str], ...]]: ...


@dataclass(frozen=True)
class LiveDirectorySizeService:
    """Calculate recursive directory sizes against the local filesystem."""

    filesystem: DirectorySizeReader = field(default_factory=LocalFilesystemAdapter)

    def calculate_sizes(
        self,
        paths: tuple[str, ...],
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, str], ...]]:
        results: list[tuple[str, int]] = []
        failures: list[tuple[str, str]] = []
        for path in paths:
            if is_cancelled is not None and is_cancelled():
                return (), ()
            try:
                total_size = self.filesystem.calculate_directory_size(
                    path,
                    is_cancelled=is_cancelled,
                )
            except DirectorySizeCancelled:
                return (), ()
            except OSError as error:
                failures.append((path, str(error) or error.__class__.__name__))
                continue
            results.append((path, total_size))
        return tuple(results), tuple(failures)


@dataclass
class FakeDirectorySizeService:
    """Deterministic directory-size service used by tests."""

    results_by_paths: dict[
        tuple[str, ...],
        tuple[tuple[str, int], ...],
    ] = field(default_factory=dict)
    failures_by_paths: dict[
        tuple[str, ...],
        tuple[tuple[str, str], ...],
    ] = field(default_factory=dict)
    failure_messages: dict[tuple[str, ...], str] = field(default_factory=dict)
    executed_requests: list[tuple[str, ...]] = field(default_factory=list)

    def calculate_sizes(
        self,
        paths: tuple[str, ...],
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, str], ...]]:
        self.executed_requests.append(paths)
        if is_cancelled is not None and is_cancelled():
            return (), ()
        if paths in self.failure_messages:
            raise OSError(self.failure_messages[paths])
        return (
            self.results_by_paths.get(paths, ()),
            self.failures_by_paths.get(paths, ()),
        )
