from plain.models import CreatePathRequest, RenameRequest
from plain.services import LiveFileMutationService


def test_file_mutation_service_renames_path(tmp_path) -> None:
    source = tmp_path / "docs"
    source.mkdir()

    service = LiveFileMutationService()

    result = service.execute(RenameRequest(source_path=str(source), new_name="manuals"))

    assert result.path == str(tmp_path / "manuals")
    assert (tmp_path / "manuals").is_dir()
    assert source.exists() is False


def test_file_mutation_service_creates_file(tmp_path) -> None:
    service = LiveFileMutationService()

    result = service.execute(
        CreatePathRequest(
            parent_dir=str(tmp_path),
            name="notes.txt",
            kind="file",
        )
    )

    assert result.path == str(tmp_path / "notes.txt")
    assert (tmp_path / "notes.txt").is_file()


def test_file_mutation_service_creates_directory(tmp_path) -> None:
    service = LiveFileMutationService()

    result = service.execute(
        CreatePathRequest(
            parent_dir=str(tmp_path),
            name="drafts",
            kind="dir",
        )
    )

    assert result.path == str(tmp_path / "drafts")
    assert (tmp_path / "drafts").is_dir()
