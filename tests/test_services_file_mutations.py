from dataclasses import dataclass, field

import pytest

from plain.models import TrashDeleteRequest
from plain.services import LiveFileMutationService


@dataclass
class StubFileOperationAdapter:
    trashed_paths: list[str] = field(default_factory=list)
    failing_paths: set[str] = field(default_factory=set)

    def path_exists(self, path: str) -> bool:
        return False

    def paths_are_same(self, source: str, destination: str) -> bool:
        return source == destination

    def remove_path(self, path: str) -> None:
        raise NotImplementedError

    def copy_path(self, source: str, destination: str) -> None:
        raise NotImplementedError

    def move_path(self, source: str, destination: str) -> None:
        raise NotImplementedError

    def generate_renamed_path(self, destination: str) -> str:
        raise NotImplementedError

    def create_file(self, path: str) -> None:
        raise NotImplementedError

    def create_directory(self, path: str) -> None:
        raise NotImplementedError

    def send_to_trash(self, path: str) -> None:
        if path in self.failing_paths:
            raise OSError("permission denied")
        self.trashed_paths.append(path)


def test_file_mutation_service_trashes_single_path() -> None:
    adapter = StubFileOperationAdapter()
    service = LiveFileMutationService(adapter=adapter)

    result = service.execute(
        TrashDeleteRequest(paths=("/tmp/plain/docs",))
    )

    assert adapter.trashed_paths == ["/tmp/plain/docs"]
    assert result.message == "Trashed 1 item"
    assert result.removed_paths == ("/tmp/plain/docs",)


def test_file_mutation_service_reports_partial_delete_failures() -> None:
    adapter = StubFileOperationAdapter(failing_paths={"/tmp/plain/src"})
    service = LiveFileMutationService(adapter=adapter)

    result = service.execute(
        TrashDeleteRequest(paths=("/tmp/plain/docs", "/tmp/plain/src"))
    )

    assert adapter.trashed_paths == ["/tmp/plain/docs"]
    assert result.level == "warning"
    assert result.removed_paths == ("/tmp/plain/docs",)


def test_file_mutation_service_raises_when_all_deletes_fail() -> None:
    adapter = StubFileOperationAdapter(failing_paths={"/tmp/plain/docs"})
    service = LiveFileMutationService(adapter=adapter)

    with pytest.raises(OSError, match="Failed to trash docs"):
        service.execute(TrashDeleteRequest(paths=("/tmp/plain/docs",)))
