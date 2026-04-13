import logging
from pathlib import Path

from zivo.models import LoggingConfig
from zivo.services.logging import configure_file_logging, resolve_default_log_path


def test_resolve_default_log_path_uses_config_directory() -> None:
    path = resolve_default_log_path("/tmp/zivo/config.toml")

    assert path == Path("/tmp/zivo/zivo.log")


def test_configure_file_logging_writes_error_entries(tmp_path) -> None:
    config = LoggingConfig(enabled=True)
    result = configure_file_logging(
        config=config,
        config_path=str(tmp_path / "config.toml"),
        logger_name="zivo.test..logging",
    )

    logger = logging.getLogger("zivo.test..logging")
    logger.error("test failure")
    for handler in logger.handlers:
        handler.flush()

    assert result.enabled is True
    assert Path(result.path).exists()
    assert "test failure" in Path(result.path).read_text(encoding="utf-8")


def test_configure_file_logging_uses_explicit_path(tmp_path) -> None:
    explicit_path = tmp_path / "logs" / "custom.log"
    result = configure_file_logging(
        config=LoggingConfig(enabled=True, path=str(explicit_path)),
        config_path=str(tmp_path / "config.toml"),
        logger_name="zivo.test..explicit",
    )

    assert result.enabled is True
    assert result.path == str(explicit_path)
    assert explicit_path.exists()


def test_configure_file_logging_returns_warning_when_file_setup_fails(
    monkeypatch,
    tmp_path,
) -> None:
    def raise_os_error(*_args, **_kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(logging, "FileHandler", raise_os_error)

    result = configure_file_logging(
        config=LoggingConfig(enabled=True),
        config_path=str(tmp_path / "config.toml"),
        logger_name="zivo.test..failure",
    )

    assert result.enabled is False
    assert "permission denied" in result.warning
