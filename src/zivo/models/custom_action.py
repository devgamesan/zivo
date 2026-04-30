"""Models for configured custom command palette actions."""

from dataclasses import dataclass
from pathlib import Path
from string import Formatter

from .config import CustomActionConfig, CustomActionMode
from .shell_command import ShellCommandResult

_VALID_PLACEHOLDERS = frozenset(
    {"cwd", "cwd_basename", "file", "name", "stem", "ext", "selection"}
)


class CustomActionExpansionError(ValueError):
    """Raised when a configured custom action cannot be expanded safely."""


@dataclass(frozen=True)
class CustomActionContext:
    """Filesystem context used to match and expand a custom action."""

    cwd: str
    focused_file: str | None = None
    selection: tuple[str, ...] = ()


@dataclass(frozen=True)
class CustomActionExecutionRequest:
    """Resolved custom action command ready for execution."""

    name: str
    command: tuple[str, ...]
    cwd: str
    mode: CustomActionMode


@dataclass(frozen=True)
class CustomActionResult:
    """Result payload for a completed custom action."""

    name: str
    result: ShellCommandResult | None = None


def custom_action_matches(action: CustomActionConfig, context: CustomActionContext) -> bool:
    """Return whether an action is available for the current browser context."""

    if action.when == "always":
        return True
    if action.when == "single_file":
        if context.focused_file is None:
            return False
        return _matches_extensions(action, context.focused_file)
    if action.when == "selection":
        return bool(context.selection)
    return False


def expand_custom_action(
    action: CustomActionConfig,
    context: CustomActionContext,
) -> CustomActionExecutionRequest:
    """Expand placeholders in a custom action into a concrete argv request."""

    values = _placeholder_values(context)
    command: list[str] = []
    for part in action.command:
        if "{selection}" in part:
            if part != "{selection}":
                raise CustomActionExpansionError(
                    "{selection} must be a standalone command argument"
                )
            if not context.selection:
                raise CustomActionExpansionError("{selection} requires at least one target")
            command.extend(context.selection)
            continue
        command.append(_format_template(part, values))

    cwd_template = action.cwd or "{cwd}"
    if "{selection}" in cwd_template:
        raise CustomActionExpansionError("{selection} cannot be used in cwd")
    cwd = _format_template(cwd_template, values)
    return CustomActionExecutionRequest(
        name=action.name,
        command=tuple(command),
        cwd=cwd,
        mode=action.mode,
    )


def _matches_extensions(action: CustomActionConfig, path: str) -> bool:
    if not action.extensions:
        return True
    suffix = Path(path).suffix.casefold()
    if suffix.startswith("."):
        suffix = suffix[1:]
    return suffix in action.extensions


def _placeholder_values(context: CustomActionContext) -> dict[str, str]:
    cwd = str(Path(context.cwd).expanduser().resolve(strict=False))
    file_path = context.focused_file
    file = Path(file_path) if file_path is not None else None
    return {
        "cwd": cwd,
        "cwd_basename": Path(cwd).name,
        "file": str(file) if file is not None else "",
        "name": file.name if file is not None else "",
        "stem": file.stem if file is not None else "",
        "ext": file.suffix[1:] if file is not None and file.suffix.startswith(".") else "",
    }


def _format_template(template: str, values: dict[str, str]) -> str:
    for _literal, field_name, _format_spec, _conversion in Formatter().parse(template):
        if field_name is None:
            continue
        root_name = field_name.split(".", 1)[0].split("[", 1)[0]
        if root_name not in _VALID_PLACEHOLDERS:
            raise CustomActionExpansionError(f"Unknown custom action variable: {field_name}")
        if root_name == "selection":
            raise CustomActionExpansionError("{selection} must be a standalone command argument")
        if root_name == "file" and not values["file"]:
            raise CustomActionExpansionError("{file} requires a focused file")
    try:
        return template.format(**values)
    except (IndexError, KeyError, ValueError) as error:
        raise CustomActionExpansionError(str(error) or "Failed to expand command") from error
