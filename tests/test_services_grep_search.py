import pytest

from peneo.services import InvalidGrepSearchQueryError, LiveGrepSearchService


def test_live_grep_search_service_matches_file_contents_recursively(tmp_path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    docs = root / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("TODO: update docs\n", encoding="utf-8")
    (docs / "guide.txt").write_text("guide\n", encoding="utf-8")

    service = LiveGrepSearchService()

    results = service.search(str(root), "todo", show_hidden=False)

    assert [result.display_label for result in results] == ["docs/README.md:1: TODO: update docs"]


def test_live_grep_search_service_skips_hidden_paths_when_disabled(tmp_path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    hidden_dir = root / ".secret"
    hidden_dir.mkdir()
    (hidden_dir / "README.md").write_text("TODO: hidden\n", encoding="utf-8")

    service = LiveGrepSearchService()

    hidden_off = service.search(str(root), "todo", show_hidden=False)
    hidden_on = service.search(str(root), "todo", show_hidden=True)

    assert hidden_off == ()
    assert [result.display_path for result in hidden_on] == [".secret/README.md"]


def test_live_grep_search_service_supports_regex_queries_with_re_prefix(tmp_path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").write_text("TODO: readme\n", encoding="utf-8")
    (root / "guide.txt").write_text("guide\n", encoding="utf-8")

    service = LiveGrepSearchService()

    results = service.search(str(root), r"re:TODO: .*", show_hidden=False)

    assert [result.display_path for result in results] == ["README.md"]


def test_live_grep_search_service_raises_invalid_query_for_bad_regex(tmp_path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    service = LiveGrepSearchService()

    with pytest.raises(InvalidGrepSearchQueryError):
        service.search(str(root), "re:[", show_hidden=False)
