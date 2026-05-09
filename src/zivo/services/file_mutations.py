"""Rename and create filesystem mutation service."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from time import sleep
from typing import Mapping, Protocol

from zivo.adapters import FileOperationAdapter, LocalFileOperationAdapter
from zivo.models import (
    ChmodRequest,
    CreatePathRequest,
    CreateSymlinkRequest,
    DeleteRequest,
    FileMutationResult,
    RecursiveChmodRequest,
    RenameRequest,
)
from zivo.services.trash_operations import TrashService, resolve_trash_service

FileMutationRequest = (
    RenameRequest
    | CreatePathRequest
    | CreateSymlinkRequest
    | DeleteRequest
    | ChmodRequest
    | RecursiveChmodRequest
)


class FileMutationService(Protocol):
    """Boundary for asynchronous rename/create/delete operations."""

    def execute(
        self,
        request: FileMutationRequest,
    ) -> FileMutationResult: ...


@dataclass(frozen=True)
class LiveFileMutationService:
    """Execute rename/create/delete operations on the local filesystem."""

    adapter: FileOperationAdapter = field(default_factory=LocalFileOperationAdapter)
    trash_service: TrashService = field(default_factory=resolve_trash_service)

    def execute(
        self,
        request: FileMutationRequest,
    ) -> FileMutationResult:
        if isinstance(request, RenameRequest):
            return self._execute_rename(request)
        if isinstance(request, CreateSymlinkRequest):
            return self._execute_symlink(request)
        if isinstance(request, DeleteRequest):
            return self._execute_delete(request)
        if isinstance(request, ChmodRequest):
            return self._execute_chmod(request)
        if isinstance(request, RecursiveChmodRequest):
            return self._execute_recursive_chmod(request)
        return self._execute_create(request)

    def _execute_rename(self, request: RenameRequest) -> FileMutationResult:
        source_path = _absolute_entry_path(request.source_path)
        destination_path = source_path.parent / request.new_name
        self.adapter.move_path(str(source_path), str(destination_path))
        return FileMutationResult(
            path=str(destination_path),
            message=f"Renamed to {request.new_name}",
            operation="rename",
            source_path=str(source_path),
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

    def _execute_symlink(self, request: CreateSymlinkRequest) -> FileMutationResult:
        source_path = _absolute_entry_path(request.source_path)
        destination_path = _absolute_entry_path(request.destination_path)
        self.adapter.create_symlink(
            str(source_path),
            str(destination_path),
            overwrite=request.overwrite,
        )
        return FileMutationResult(
            path=str(destination_path),
            message=f"Created symlink {destination_path.name}",
            operation="symlink",
            source_path=str(source_path),
        )

    def _execute_delete(self, request: DeleteRequest) -> FileMutationResult:
        removed_paths: list[str] = []
        failures: list[tuple[str, str]] = []
        trash_records = []

        for path in request.paths:
            try:
                if request.mode == "trash":
                    trash_record = self.trash_service.capture_restorable_trash(
                        path,
                        lambda current_path=path: self.adapter.send_to_trash(current_path),
                    )
                    if trash_record is not None:
                        trash_records.append(trash_record)
                else:
                    self.adapter.remove_path(path)
            except OSError as error:
                fallback_message = "Trash failed" if request.mode == "trash" else "Delete failed"
                failures.append((path, str(error) or fallback_message))
            else:
                removed_paths.append(path)

        if not removed_paths:
            if len(failures) == 1:
                failed_path = Path(failures[0][0]).name
                if request.mode == "trash":
                    raise OSError(f"Failed to trash {failed_path}: {failures[0][1]}")
                raise OSError(f"Failed to permanently delete {failed_path}: {failures[0][1]}")
            if request.mode == "trash":
                raise OSError(f"Failed to trash {len(failures)} items")
            raise OSError(f"Failed to permanently delete {len(failures)} items")

        if failures:
            message = (
                f"Trashed {len(removed_paths)}/{len(request.paths)} items"
                f" with {len(failures)} failure(s)"
                if request.mode == "trash"
                else (
                    f"Deleted {len(removed_paths)}/{len(request.paths)} items permanently"
                    f" with {len(failures)} failure(s)"
                )
            )
            return FileMutationResult(
                path=None,
                message=message,
                level="warning",
                removed_paths=tuple(removed_paths),
                operation="delete",
                delete_mode=request.mode,
                trash_records=tuple(trash_records),
            )

        noun = "item" if len(removed_paths) == 1 else "items"
        message = (
            f"Trashed {len(removed_paths)} {noun}"
            if request.mode == "trash"
            else f"Deleted {len(removed_paths)} {noun} permanently"
        )
        return FileMutationResult(
            path=None,
            message=message,
            removed_paths=tuple(removed_paths),
            operation="delete",
            delete_mode=request.mode,
            trash_records=tuple(trash_records),
        )

    def _execute_chmod(self, request: ChmodRequest) -> FileMutationResult:
        target_path = _absolute_entry_path(request.path)
        self.adapter.change_permissions(str(target_path), request.mode)
        return FileMutationResult(
            path=str(target_path),
            message=f"Changed permissions to {request.mode:03o}",
            operation="chmod",
        )

    def _execute_recursive_chmod(self, request: RecursiveChmodRequest) -> FileMutationResult:
        changed_paths: list[str] = []
        failures: list[tuple[str, str]] = []

        for target_path in _iter_recursive_chmod_targets(request.paths):
            try:
                self.adapter.change_permissions(str(target_path), request.mode)
            except OSError as error:
                failures.append((str(target_path), str(error) or "Permission change failed"))
            else:
                changed_paths.append(str(target_path))

        if not changed_paths:
            if len(failures) == 1:
                failed_name = Path(failures[0][0]).name
                raise OSError(f"Failed to change permissions for {failed_name}: {failures[0][1]}")
            if failures:
                raise OSError(f"Failed to change permissions for {len(failures)} items")
            raise OSError("No files matched recursive permissions change")

        if failures:
            return FileMutationResult(
                path=None,
                message=(
                    f"Changed permissions to {request.mode:03o} for "
                    f"{len(changed_paths)}/{len(changed_paths) + len(failures)} items "
                    f"with {len(failures)} failure(s)"
                ),
                level="warning",
                operation="chmod",
            )

        noun = "item" if len(changed_paths) == 1 else "items"
        return FileMutationResult(
            path=str(_absolute_entry_path(request.paths[0])) if request.paths else None,
            message=f"Changed permissions to {request.mode:03o} for {len(changed_paths)} {noun}",
            operation="chmod",
        )


@dataclass(frozen=True)
class FakeFileMutationService:
    """Deterministic file-mutation service used by tests."""

    results: Mapping[
        FileMutationRequest,
        FileMutationResult,
    ] = field(default_factory=dict)
    failure_messages: Mapping[
        FileMutationRequest,
        str,
    ] = field(default_factory=dict)
    default_delay_seconds: float = 0.0

    def execute(
        self,
        request: FileMutationRequest,
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
                operation="rename",
                source_path=str(source_path),
            )

        if isinstance(request, CreateSymlinkRequest):
            destination_path = _absolute_entry_path(request.destination_path)
            return FileMutationResult(
                path=str(destination_path),
                message=f"Created symlink {destination_path.name}",
                operation="symlink",
                source_path=str(_absolute_entry_path(request.source_path)),
            )

        if isinstance(request, DeleteRequest):
            noun = "item" if len(request.paths) == 1 else "items"
            message = (
                f"Trashed {len(request.paths)} {noun}"
                if request.mode == "trash"
                else f"Deleted {len(request.paths)} {noun} permanently"
            )
            return FileMutationResult(
                path=None,
                message=message,
                removed_paths=request.paths,
                operation="delete",
                delete_mode=request.mode,
            )

        if isinstance(request, ChmodRequest):
            target_path = _absolute_entry_path(request.path)
            return FileMutationResult(
                path=str(target_path),
                message=f"Changed permissions to {request.mode:03o}",
                operation="chmod",
            )

        if isinstance(request, RecursiveChmodRequest):
            noun = "item" if len(request.paths) == 1 else "items"
            return FileMutationResult(
                path=str(_absolute_entry_path(request.paths[0])) if request.paths else None,
                message=(
                    f"Changed permissions to {request.mode:03o} "
                    f"for {len(request.paths)} {noun}"
                ),
                operation="chmod",
            )

        target_path = _absolute_entry_path(request.parent_dir) / request.name
        message = (
            f"Created file {request.name}"
            if request.kind == "file"
            else f"Created directory {request.name}"
        )
        return FileMutationResult(path=str(target_path), message=message, operation="create")


def _absolute_entry_path(path: str) -> Path:
    return Path(os.path.abspath(os.path.expanduser(path)))


def _iter_recursive_chmod_targets(paths: tuple[str, ...]) -> tuple[Path, ...]:
    targets: list[Path] = []
    for path in paths:
        root = _absolute_entry_path(path)
        if root.is_symlink():
            continue
        targets.append(root)
        if root.is_dir():
            for current_root, dirnames, filenames in os.walk(root, followlinks=False):
                current_path = Path(current_root)
                dirnames[:] = [
                    dirname
                    for dirname in dirnames
                    if not (current_path / dirname).is_symlink()
                ]
                for dirname in dirnames:
                    targets.append(current_path / dirname)
                for filename in filenames:
                    child = current_path / filename
                    if not child.is_symlink():
                        targets.append(child)
    return tuple(targets)
