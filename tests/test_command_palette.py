"""Tests for the command palette widget."""

from peneo.models import CommandPaletteItemViewState, CommandPaletteViewState
from peneo.ui.command_palette import CommandPalette


def test_truncation_with_multibyte_text() -> None:
    """マルチバイト文字を含むラベルが表示幅に基づいて切り詰められること"""
    # 文字数は短いが表示幅が長いラベル
    label = "file_" + "日本語" * 30 + "_description.txt"
    # len(label) = 111, cell_len(label) = 201

    state = CommandPaletteViewState(
        title="Test",
        query="test",
        items=(
            CommandPaletteItemViewState(
                label=label,
                shortcut=None,
                enabled=True,
                selected=False,
            ),
        ),
        empty_message="No results",
        has_more_items=False,
    )

    palette = CommandPalette(state)
    rendered = palette._render_items(state)

    # 切り詰められていることを確認
    rendered_text = str(rendered)
    assert len(rendered_text) < len(label), "ラベルは切り詰められている必要があります"
    # 切り詰めマーカーが含まれていることを確認
    assert "…" in rendered_text or "~" in rendered_text, "切り詰めマーカーが含まれている必要があります"


def test_no_truncation_for_short_labels() -> None:
    """短いラベルは切り詰められないこと"""
    label = "検索結果.txt"  # 短い日本語ファイル名

    state = CommandPaletteViewState(
        title="Test",
        query="test",
        items=(
            CommandPaletteItemViewState(
                label=label,
                shortcut=None,
                enabled=True,
                selected=False,
            ),
        ),
        empty_message="No results",
        has_more_items=False,
    )

    palette = CommandPalette(state)
    rendered = palette._render_items(state)

    # 完全なラベルが含まれていることを確認
    rendered_text = str(rendered)
    assert label in rendered_text, "短いラベルはそのまま表示される必要があります"


def test_truncation_with_ascii_text() -> None:
    """ASCII テキストも正しく切り詰められること"""
    # 120 文字を超える ASCII ラベル
    label = "a" * 200

    state = CommandPaletteViewState(
        title="Test",
        query="test",
        items=(
            CommandPaletteItemViewState(
                label=label,
                shortcut=None,
                enabled=True,
                selected=False,
            ),
        ),
        empty_message="No results",
        has_more_items=False,
    )

    palette = CommandPalette(state)
    rendered = palette._render_items(state)

    # 切り詰められていることを確認
    rendered_text = str(rendered)
    assert len(rendered_text) < len(label), "長い ASCII ラベルは切り詰められている必要があります"
    assert "…" in rendered_text or "~" in rendered_text, "切り詰めマーカーが含まれている必要があります"


def test_no_truncation_for_short_ascii_labels() -> None:
    """短い ASCII ラベルは切り詰められないこと"""
    label = "search_result.txt"  # 短い ASCII ファイル名

    state = CommandPaletteViewState(
        title="Test",
        query="test",
        items=(
            CommandPaletteItemViewState(
                label=label,
                shortcut=None,
                enabled=True,
                selected=False,
            ),
        ),
        empty_message="No results",
        has_more_items=False,
    )

    palette = CommandPalette(state)
    rendered = palette._render_items(state)

    # 完全なラベルが含まれていることを確認
    rendered_text = str(rendered)
    assert label in rendered_text, "短い ASCII ラベルはそのまま表示される必要があります"
