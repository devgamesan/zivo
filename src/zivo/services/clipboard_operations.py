"""Clipboard-backed file operation service."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from time import sleep
from typing import Mapping, Protocol

from zivo.adapters import FileOperationAdapter, LocalFileOperationAdapter
from zivo.models import (
    PasteAppliedChange,
    PasteConflict,
    PasteConflictPrompt,
    PasteExecutionResult,
    PasteFailure,
    PasteRequest,
    PasteSummary,
)


class ClipboardOperationService(Protocol):
    """Boundary for asynchronous clipboard operations."""

    def execute_paste(
        self,
        request: PasteRequest,
    ) -> PasteConflictPrompt | PasteExecutionResult: ...


@dataclass(frozen=True)
class LiveClipboardOperationService:
    """Execute clipboard operations on the local filesystem."""

    adapter: FileOperationAdapter = field(default_factory=LocalFileOperationAdapter)

    def execute_paste(
        self,
        request: PasteRequest,
    ) -> PasteConflictPrompt | PasteExecutionResult:
        conflicts = self._collect_conflicts(request)
        if conflicts and request.conflict_resolution is None:
            return PasteConflictPrompt(request=request, conflicts=conflicts)

        success_count = 0
        skipped_count = 0
        overwrote_count = 0
        failures: list[PasteFailure] = []
        applied_changes: list[PasteAppliedChange] = []

        for source_path in request.source_paths:
            destination_path = self._destination_for_source(source_path, request.destination_dir)
            conflict = self._is_conflict(source_path, destination_path)

            if conflict:
                resolution = request.conflict_resolution
                if resolution == "skip":
                    skipped_count += 1
                    continue
                if resolution == "rename":
                    destination_path = self.adapter.generate_renamed_path(destination_path)
                elif resolution == "overwrite":
                    if self.adapter.paths_are_same(source_path, destination_path):
                        failures.append(
                            PasteFailure(
                                source_path=source_path,
                                destination_path=destination_path,
                                message="Source and destination are the same path",
                            )
                        )
                        continue
                    self.adapter.remove_path(destination_path)
                    overwrote_count += 1

            try:
                if request.mode == "copy":
                    self.adapter.copy_path(source_path, destination_path)
                else:
                    self.adapter.move_path(source_path, destination_path)
            except OSError as error:
                failures.append(
                    PasteFailure(
                        source_path=source_path,
                        destination_path=destination_path,
                        message=str(error) or "Paste failed",
                    )
                )
            else:
                success_count += 1
                applied_changes.append(
                    PasteAppliedChange(
                        source_path=source_path,
                        destination_path=destination_path,
                    )
                )

        return PasteExecutionResult(
            summary=PasteSummary(
                mode=request.mode,
                destination_dir=request.destination_dir,
                total_count=len(request.source_paths),
                success_count=success_count,
                skipped_count=skipped_count,
                failures=tuple(failures),
                conflict_resolution=request.conflict_resolution,
                overwrote_count=overwrote_count,
            )
            ,
            applied_changes=tuple(applied_changes),
        )

    def _collect_conflicts(self, request: PasteRequest) -> tuple[PasteConflict, ...]:
        conflicts: list[PasteConflict] = []
        for source_path in request.source_paths:
            destination_path = self._destination_for_source(source_path, request.destination_dir)
            if self._is_conflict(source_path, destination_path):
                conflicts.append(
                    PasteConflict(
                        source_path=source_path,
                        destination_path=destination_path,
                    )
                )
        return tuple(conflicts)

    def _is_conflict(self, source_path: str, destination_path: str) -> bool:
        return self.adapter.path_exists(destination_path) or self.adapter.paths_are_same(
            source_path,
            destination_path,
        )

    @staticmethod
    def _destination_for_source(source_path: str, destination_dir: str) -> str:
        return str(_absolute_entry_path(destination_dir) / Path(source_path).name)


@dataclass(frozen=True)
class FakeClipboardOperationService:
    """Deterministic clipboard-operation service used by tests."""

    results: Mapping[PasteRequest, PasteConflictPrompt | PasteExecutionResult] = field(
        default_factory=dict
    )
    failure_messages: Mapping[PasteRequest, str] = field(default_factory=dict)
    default_delay_seconds: float = 0.0

    def execute_paste(
        self,
        request: PasteRequest,
    ) -> PasteConflictPrompt | PasteExecutionResult:
        if self.default_delay_seconds > 0:
            sleep(self.default_delay_seconds)

        if request in self.failure_messages:
            raise OSError(self.failure_messages[request])

        result = self.results.get(request)
        if result is None:
            return PasteExecutionResult(
                summary=PasteSummary(
                    mode=request.mode,
                    destination_dir=request.destination_dir,
                    total_count=len(request.source_paths),
                    success_count=len(request.source_paths),
                    skipped_count=0,
                    failures=(),
                    conflict_resolution=request.conflict_resolution,
                ),
                applied_changes=tuple(
                    PasteAppliedChange(
                        source_path=source_path,
                        destination_path=self._destination_for_source(
                            source_path,
                            request.destination_dir,
                        ),
                    )
                    for source_path in request.source_paths
                ),
            )
        return result


def _absolute_entry_path(path: str) -> Path:
    return Path(os.path.abspath(os.path.expanduser(path)))
