"""Rename and create filesystem mutation service."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from time import sleep
from typing import Mapping, Protocol

from peneo.adapters import FileOperationAdapter, LocalFileOperationAdapter
from peneo.models import CreatePathRequest, FileMutationResult, RenameRequest, TrashDeleteRequest


class FileMutationService(Protocol):
    """Boundary for asynchronous rename/create/delete operations."""

    def execute(
        self,
        request: RenameRequest | CreatePathRequest | TrashDeleteRequest,
    ) -> FileMutationResult: ...


@dataclass(frozen=True)
class LiveFileMutationService:
    """Execute rename/create/delete operations on the local filesystem."""

    adapter: FileOperationAdapter = field(default_factory=LocalFileOperationAdapter)

    def execute(
        self,
        request: RenameRequest | CreatePathRequest | TrashDeleteRequest,
    ) -> FileMutationResult:
        if isinstance(request, RenameRequest):
            return self._execute_rename(request)
        if isinstance(request, TrashDeleteRequest):
            return self._execute_delete(request)
        return self._execute_create(request)

    def _execute_rename(self, request: RenameRequest) -> FileMutationResult:
        source_path = _absolute_entry_path(request.source_path)
        destination_path = source_path.parent / request.new_name
        self.adapter.move_path(str(source_path), str(destination_path))
        return FileMutationResult(
            path=str(destination_path),
            message=f"Renamed to {request.new_name}",
        )

    def _execute_create(self, request: CreatePathRequest) -> FileMutationResult:
        target_path = _absolute_entry_path(request.parent_dir) / request.name
        if request.kind == "file":
            self.adapter.create_file(str(target_path))
            message = f"Created file {request.name}"
        else:
            self.adapter.create_directory(str(target_path))
            message = f"Created directory {request.name}"
        return FileMutationResult(path=str(target_path), message=message)

    def _execute_delete(self, request: TrashDeleteRequest) -> FileMutationResult:
        removed_paths: list[str] = []
        failures: list[tuple[str, str]] = []

        for path in request.paths:
            try:
                self.adapter.send_to_trash(path)
            except OSError as error:
                failures.append((path, str(error) or "Trash failed"))
            else:
                removed_paths.append(path)

        if not removed_paths:
            if len(failures) == 1:
                failed_path = Path(failures[0][0]).name
                raise OSError(f"Failed to trash {failed_path}: {failures[0][1]}")
            raise OSError(f"Failed to trash {len(failures)} items")

        if failures:
            return FileMutationResult(
                path=None,
                message=(
                    f"Trashed {len(removed_paths)}/{len(request.paths)} items"
                    f" with {len(failures)} failure(s)"
                ),
                level="warning",
                removed_paths=tuple(removed_paths),
            )

        noun = "item" if len(removed_paths) == 1 else "items"
        return FileMutationResult(
            path=None,
            message=f"Trashed {len(removed_paths)} {noun}",
            removed_paths=tuple(removed_paths),
        )


@dataclass(frozen=True)
class FakeFileMutationService:
    """Deterministic file-mutation service used by tests."""

    results: Mapping[
        RenameRequest | CreatePathRequest | TrashDeleteRequest, FileMutationResult
    ] = field(default_factory=dict)
    failure_messages: Mapping[
        RenameRequest | CreatePathRequest | TrashDeleteRequest, str
    ] = field(default_factory=dict)
    default_delay_seconds: float = 0.0

    def execute(
        self,
        request: RenameRequest | CreatePathRequest | TrashDeleteRequest,
    ) -> FileMutationResult:
        if self.default_delay_seconds > 0:
            sleep(self.default_delay_seconds)

        if request in self.failure_messages:
            raise OSError(self.failure_messages[request])

        result = self.results.get(request)
        if result is not None:
            return result

        if isinstance(request, RenameRequest):
            source_path = _absolute_entry_path(request.source_path)
            return FileMutationResult(
                path=str(source_path.parent / request.new_name),
                message=f"Renamed to {request.new_name}",
            )

        if isinstance(request, TrashDeleteRequest):
            noun = "item" if len(request.paths) == 1 else "items"
            return FileMutationResult(
                path=None,
                message=f"Trashed {len(request.paths)} {noun}",
                removed_paths=request.paths,
            )

        target_path = _absolute_entry_path(request.parent_dir) / request.name
        message = (
            f"Created file {request.name}"
            if request.kind == "file"
            else f"Created directory {request.name}"
        )
        return FileMutationResult(path=str(target_path), message=message)


def _absolute_entry_path(path: str) -> Path:
    return Path(os.path.abspath(os.path.expanduser(path)))
