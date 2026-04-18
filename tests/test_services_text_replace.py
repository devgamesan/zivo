from pathlib import Path

import pytest

from zivo.models import TextReplaceRequest
from zivo.services.text_replace import (
    InvalidTextReplaceQueryError,
    LiveTextReplaceService,
)


def test_live_text_replace_service_previews_and_applies_plain_text(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text("todo item\ntodo again\n", encoding="utf-8")
    service = LiveTextReplaceService()
    request = TextReplaceRequest(
        paths=(str(target),),
        find_text="todo",
        replace_text="done",
    )

    preview = service.preview(request)

    assert preview.total_match_count == 2
    assert preview.changed_entries[0].first_match_line_number == 1
    assert preview.changed_entries[0].first_match_before == "todo item"
    assert preview.changed_entries[0].first_match_after == "done item"
    assert "--- " in preview.diff_text
    assert "+++ " in preview.diff_text

    result = service.apply(request)

    assert result.changed_paths == (str(target),)
    assert result.total_match_count == 2
    assert target.read_text(encoding="utf-8") == "done item\ndone again\n"


def test_live_text_replace_service_rejects_invalid_regex(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text("todo item\n", encoding="utf-8")
    service = LiveTextReplaceService()

    with pytest.raises(InvalidTextReplaceQueryError):
        service.preview(
            TextReplaceRequest(
                paths=(str(target),),
                find_text="re:(",
                replace_text="done",
            )
        )
