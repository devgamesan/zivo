from dataclasses import dataclass, field

import pytest

from plain.models import CreatePathRequest, RenameRequest, TrashDeleteRequest
from plain.services import LiveFileMutationService


@dataclass
class StubFileOperationAdapter:
    trashed_paths: list[str] = field(default_factory=list)
    failing_paths: set[str] = field(default_factory=set)
    moved_paths: list[tuple[str, str]] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    created_directories: list[str] = field(default_factory=list)

    def path_exists(self, path: str) -> bool:
        return False

    def paths_are_same(self, source: str, destination: str) -> bool:
        return source == destination

    def remove_path(self, path: str) -> None:
        raise NotImplementedError

    def copy_path(self, source: str, destination: str) -> None:
        raise NotImplementedError

    def move_path(self, source: str, destination: str) -> None:
        if source in self.failing_paths or destination in self.failing_paths:
            raise OSError("rename failed")
        self.moved_paths.append((source, destination))

    def generate_renamed_path(self, destination: str) -> str:
        raise NotImplementedError

    def create_file(self, path: str) -> None:
        if path in self.failing_paths:
            raise OSError("file creation failed")
        self.created_files.append(path)

    def create_directory(self, path: str) -> None:
        if path in self.failing_paths:
            raise OSError("directory creation failed")
        self.created_directories.append(path)

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


def test_file_mutation_service_renames_single_path() -> None:
    adapter = StubFileOperationAdapter()
    service = LiveFileMutationService(adapter=adapter)

    result = service.execute(
        RenameRequest(source_path="/tmp/plain/docs", new_name="docs-old")
    )

    assert adapter.moved_paths == [("/tmp/plain/docs", "/tmp/plain/docs-old")]
    assert result.path == "/tmp/plain/docs-old"
    assert result.message == "Renamed to docs-old"


def test_file_mutation_service_raises_rename_error() -> None:
    adapter = StubFileOperationAdapter(failing_paths={"/tmp/plain/docs-old"})
    service = LiveFileMutationService(adapter=adapter)

    with pytest.raises(OSError, match="rename failed"):
        service.execute(RenameRequest(source_path="/tmp/plain/docs", new_name="docs-old"))


def test_file_mutation_service_creates_file() -> None:
    adapter = StubFileOperationAdapter()
    service = LiveFileMutationService(adapter=adapter)

    result = service.execute(
        CreatePathRequest(parent_dir="/tmp/plain", name="README.md", kind="file")
    )

    assert adapter.created_files == ["/tmp/plain/README.md"]
    assert result.path == "/tmp/plain/README.md"
    assert result.message == "Created file README.md"


def test_file_mutation_service_creates_directory() -> None:
    adapter = StubFileOperationAdapter()
    service = LiveFileMutationService(adapter=adapter)

    result = service.execute(CreatePathRequest(parent_dir="/tmp/plain", name="docs", kind="dir"))

    assert adapter.created_directories == ["/tmp/plain/docs"]
    assert result.path == "/tmp/plain/docs"
    assert result.message == "Created directory docs"


def test_file_mutation_service_raises_create_file_error() -> None:
    adapter = StubFileOperationAdapter(failing_paths={"/tmp/plain/README.md"})
    service = LiveFileMutationService(adapter=adapter)

    with pytest.raises(OSError, match="file creation failed"):
        service.execute(CreatePathRequest(parent_dir="/tmp/plain", name="README.md", kind="file"))


def test_file_mutation_service_raises_create_directory_error() -> None:
    adapter = StubFileOperationAdapter(failing_paths={"/tmp/plain/docs"})
    service = LiveFileMutationService(adapter=adapter)

    with pytest.raises(OSError, match="directory creation failed"):
        service.execute(CreatePathRequest(parent_dir="/tmp/plain", name="docs", kind="dir"))


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
