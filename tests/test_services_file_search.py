from peneo.services import LiveFileSearchService


def test_live_file_search_service_matches_files_recursively(tmp_path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    docs = root / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("readme\n", encoding="utf-8")
    (docs / "guide.txt").write_text("guide\n", encoding="utf-8")

    service = LiveFileSearchService()

    results = service.search(str(root), "read", show_hidden=False)

    assert [result.display_path for result in results] == ["docs/README.md"]


def test_live_file_search_service_skips_hidden_paths_when_disabled(tmp_path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    hidden_dir = root / ".secret"
    hidden_dir.mkdir()
    (hidden_dir / "README.md").write_text("secret\n", encoding="utf-8")

    service = LiveFileSearchService()

    hidden_off = service.search(str(root), "read", show_hidden=False)
    hidden_on = service.search(str(root), "read", show_hidden=True)

    assert hidden_off == ()
    assert [result.display_path for result in hidden_on] == [".secret/README.md"]


def test_live_file_search_service_matches_case_insensitively_and_ignores_directories(
    tmp_path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "Readings").mkdir()
    (root / "README.MD").write_text("upper\n", encoding="utf-8")

    service = LiveFileSearchService()

    results = service.search(str(root), "read", show_hidden=False)

    assert [result.display_path for result in results] == ["README.MD"]
