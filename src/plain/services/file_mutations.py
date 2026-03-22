"""Rename and create filesystem mutation service."""

from dataclasses import dataclass, field
from pathlib import Path
from time import sleep
from typing import Mapping, Protocol

from plain.adapters import FileOperationAdapter, LocalFileOperationAdapter
from plain.models import CreatePathRequest, FileMutationResult, RenameRequest


class FileMutationService(Protocol):
    """Boundary for asynchronous rename/create operations."""

    def execute(
        self,
        request: RenameRequest | CreatePathRequest,
    ) -> FileMutationResult: ...


@dataclass(frozen=True)
class LiveFileMutationService:
    """Execute rename/create operations on the local filesystem."""

    adapter: FileOperationAdapter = field(default_factory=LocalFileOperationAdapter)

    def execute(
        self,
        request: RenameRequest | CreatePathRequest,
    ) -> FileMutationResult:
        if isinstance(request, RenameRequest):
            return self._execute_rename(request)
        return self._execute_create(request)

    def _execute_rename(self, request: RenameRequest) -> FileMutationResult:
        source_path = Path(request.source_path).expanduser().resolve()
        destination_path = source_path.parent / request.new_name
        self.adapter.move_path(str(source_path), str(destination_path))
        return FileMutationResult(
            path=str(destination_path),
            message=f"Renamed to {request.new_name}",
        )

    def _execute_create(self, request: CreatePathRequest) -> FileMutationResult:
        target_path = Path(request.parent_dir).expanduser().resolve() / request.name
        if request.kind == "file":
            self.adapter.create_file(str(target_path))
            message = f"Created file {request.name}"
        else:
            self.adapter.create_directory(str(target_path))
            message = f"Created directory {request.name}"
        return FileMutationResult(path=str(target_path), message=message)


@dataclass(frozen=True)
class FakeFileMutationService:
    """Deterministic file-mutation service used by tests."""

    results: Mapping[RenameRequest | CreatePathRequest, FileMutationResult] = field(
        default_factory=dict
    )
    failure_messages: Mapping[RenameRequest | CreatePathRequest, str] = field(default_factory=dict)
    default_delay_seconds: float = 0.0

    def execute(
        self,
        request: RenameRequest | CreatePathRequest,
    ) -> FileMutationResult:
        if self.default_delay_seconds > 0:
            sleep(self.default_delay_seconds)

        if request in self.failure_messages:
            raise OSError(self.failure_messages[request])

        result = self.results.get(request)
        if result is not None:
            return result

        if isinstance(request, RenameRequest):
            source_path = Path(request.source_path).expanduser().resolve()
            return FileMutationResult(
                path=str(source_path.parent / request.new_name),
                message=f"Renamed to {request.new_name}",
            )

        target_path = Path(request.parent_dir).expanduser().resolve() / request.name
        message = (
            f"Created file {request.name}"
            if request.kind == "file"
            else f"Created directory {request.name}"
        )
        return FileMutationResult(path=str(target_path), message=message)
