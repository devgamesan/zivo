from pathlib import Path

from peneo.services.config import AppConfigLoader, resolve_config_path


def test_resolve_config_path_uses_xdg_directory(tmp_path) -> None:
    path = resolve_config_path(
        system_name_resolver=lambda: "Linux",
        environment_variable=lambda name: str(tmp_path) if name == "XDG_CONFIG_HOME" else None,
        home_directory_resolver=lambda: Path("/unused-home"),
    )

    assert path == tmp_path / "peneo" / "config.toml"


def test_loader_creates_default_config_when_missing(tmp_path) -> None:
    config_path = tmp_path / "config.toml"

    result = AppConfigLoader(config_path_resolver=lambda: config_path).load()

    assert result.created is True
    assert result.config.display.show_hidden_files is False
    assert config_path.exists()
    assert 'default_sort_field = "name"' in config_path.read_text(encoding="utf-8")


def test_loader_reads_valid_config_values(tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
        [terminal]
        linux = ["konsole --working-directory {path}"]

        [display]
        show_hidden_files = true
        default_sort_field = "modified"
        default_sort_descending = true
        directories_first = false

        [behavior]
        confirm_delete = false
        paste_conflict_action = "rename"
        """,
        encoding="utf-8",
    )

    result = AppConfigLoader(config_path_resolver=lambda: config_path).load()

    assert result.created is False
    assert result.warnings == ()
    assert result.config.terminal.linux == ("konsole --working-directory {path}",)
    assert result.config.display.show_hidden_files is True
    assert result.config.display.default_sort_field == "modified"
    assert result.config.display.default_sort_descending is True
    assert result.config.display.directories_first is False
    assert result.config.behavior.confirm_delete is False
    assert result.config.behavior.paste_conflict_action == "rename"


def test_loader_keeps_valid_values_and_warns_for_invalid_entries(tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
        [terminal]
        linux = ["konsole --working-directory {path}", "{broken"]

        [display]
        show_hidden_files = true
        default_sort_field = "invalid"

        [behavior]
        confirm_delete = "yes"
        paste_conflict_action = "explode"
        """,
        encoding="utf-8",
    )

    result = AppConfigLoader(config_path_resolver=lambda: config_path).load()

    assert result.config.terminal.linux == ("konsole --working-directory {path}",)
    assert result.config.display.show_hidden_files is True
    assert result.config.display.default_sort_field == "name"
    assert result.config.behavior.confirm_delete is True
    assert result.config.behavior.paste_conflict_action == "prompt"
    assert len(result.warnings) == 4
