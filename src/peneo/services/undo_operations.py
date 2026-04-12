"""Undo execution service for reversible file operations."""

from dataclasses import dataclass, field
from time import sleep
from typing import Mapping, Protocol

from peneo.adapters import FileOperationAdapter, LocalFileOperationAdapter
from peneo.models import (
    UndoDeletePathStep,
    UndoEntry,
    UndoMovePathStep,
    UndoRestoreTrashStep,
    UndoResult,
)

from .trash_operations import TrashService, resolve_trash_service


class UndoService(Protocol):
    """Boundary for undo execution."""

    def execute(self, entry: UndoEntry) -> UndoResult: ...


@dataclass(frozen=True)
class LiveUndoService:
    """Execute an undo entry against the local filesystem."""

    adapter: FileOperationAdapter = field(default_factory=LocalFileOperationAdapter)
    trash_service: TrashService = field(default_factory=resolve_trash_service)

    def execute(self, entry: UndoEntry) -> UndoResult:
        if entry.kind == "paste_copy":
            return self._undo_copy(entry)
        if entry.kind == "paste_cut":
            return self._undo_move(entry, message_prefix="Undid move")
        if entry.kind == "trash_delete":
            return self._undo_trash(entry)
        return self._undo_move(entry, message_prefix="Undid rename")

    def _undo_copy(self, entry: UndoEntry) -> UndoResult:
        removed_paths: list[str] = []
        failures: list[str] = []
        steps = sorted(
            (
                step for step in entry.steps if isinstance(step, UndoDeletePathStep)
            ),
            key=lambda step: step.path.count("/"),
            reverse=True,
        )
        for step in steps:
            try:
                self.adapter.remove_path(step.path)
            except OSError as error:
                failures.append(str(error) or f"Failed to remove {step.path}")
            else:
                removed_paths.append(step.path)
        return _result_from_changes(
            success_count=len(removed_paths),
            total_count=len(steps),
            singular_message="Undid copied item",
            plural_message="Undid copied items",
            path=None,
            removed_paths=tuple(removed_paths),
            failures=failures,
        )

    def _undo_move(self, entry: UndoEntry, *, message_prefix: str) -> UndoResult:
        restored_paths: list[str] = []
        failures: list[str] = []
        steps = tuple(step for step in entry.steps if isinstance(step, UndoMovePathStep))
        for step in reversed(steps):
            try:
                self.adapter.move_path(step.source_path, step.destination_path)
            except OSError as error:
                failures.append(str(error) or f"Failed to move {step.source_path}")
            else:
                restored_paths.append(step.destination_path)
        return _result_from_changes(
            success_count=len(restored_paths),
            total_count=len(steps),
            singular_message=message_prefix,
            plural_message=message_prefix,
            path=restored_paths[0] if restored_paths else None,
            failures=failures,
        )

    def _undo_trash(self, entry: UndoEntry) -> UndoResult:
        restored_paths: list[str] = []
        failures: list[str] = []
        steps = tuple(step for step in entry.steps if isinstance(step, UndoRestoreTrashStep))
        for step in steps:
            try:
                restored_paths.append(self.trash_service.restore(step.record))
            except OSError as error:
                failures.append(str(error) or f"Failed to restore {step.record.original_path}")
        return _result_from_changes(
            success_count=len(restored_paths),
            total_count=len(steps),
            singular_message="Restored trashed item",
            plural_message="Restored trashed items",
            path=restored_paths[0] if restored_paths else None,
            failures=failures,
        )


@dataclass(frozen=True)
class FakeUndoService:
    """Deterministic undo service used by tests."""

    results: Mapping[UndoEntry, UndoResult] = field(default_factory=dict)
    failure_messages: Mapping[UndoEntry, str] = field(default_factory=dict)
    default_delay_seconds: float = 0.0

    def execute(self, entry: UndoEntry) -> UndoResult:
        if self.default_delay_seconds > 0:
            sleep(self.default_delay_seconds)
        if entry in self.failure_messages:
            raise OSError(self.failure_messages[entry])
        result = self.results.get(entry)
        if result is not None:
            return result
        return UndoResult(
            path=None,
            message=f"Undid {entry.kind}",
        )


def _result_from_changes(
    *,
    success_count: int,
    total_count: int,
    singular_message: str,
    plural_message: str,
    path: str | None,
    removed_paths: tuple[str, ...] = (),
    failures: list[str],
) -> UndoResult:
    if success_count == 0:
        if failures:
            raise OSError(failures[0])
        raise OSError("Nothing to undo")
    if failures:
        return UndoResult(
            path=path,
            message=f"{singular_message} {success_count}/{total_count} item(s)",
            level="warning",
            removed_paths=removed_paths,
        )
    noun = singular_message if success_count == 1 else plural_message
    return UndoResult(
        path=path,
        message=noun if success_count == 1 else f"{noun} ({success_count} items)",
        removed_paths=removed_paths,
    )
