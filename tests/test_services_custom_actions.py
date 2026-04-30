from zivo.models import (
    CustomActionConfig,
    CustomActionContext,
    CustomActionExpansionError,
    custom_action_matches,
    expand_custom_action,
)


def test_custom_action_matches_single_file_by_extension() -> None:
    action = CustomActionConfig(
        name="Optimize PNG",
        command=("oxipng", "{file}"),
        when="single_file",
        extensions=("png",),
    )

    assert custom_action_matches(
        action,
        CustomActionContext(
            cwd="/tmp/project",
            focused_file="/tmp/project/image.png",
        ),
    )
    assert not custom_action_matches(
        action,
        CustomActionContext(
            cwd="/tmp/project",
            focused_file="/tmp/project/notes.txt",
        ),
    )


def test_expand_custom_action_expands_file_and_cwd_placeholders() -> None:
    action = CustomActionConfig(
        name="Describe file",
        command=("tool", "{name}", "{stem}", "{ext}", "{cwd_basename}"),
        when="single_file",
        cwd="{cwd}",
    )

    request = expand_custom_action(
        action,
        CustomActionContext(
            cwd="/tmp/project",
            focused_file="/tmp/project/report.md",
        ),
    )

    assert request.command == ("tool", "report.md", "report", "md", "project")
    assert request.cwd == "/tmp/project"


def test_expand_custom_action_expands_selection_as_multiple_arguments() -> None:
    action = CustomActionConfig(
        name="Archive selection",
        command=("tar", "-czf", "{cwd_basename}.tar.gz", "{selection}"),
        when="selection",
    )

    request = expand_custom_action(
        action,
        CustomActionContext(
            cwd="/tmp/project",
            selection=("/tmp/project/a.txt", "/tmp/project/b.txt"),
        ),
    )

    assert request.command == (
        "tar",
        "-czf",
        "project.tar.gz",
        "/tmp/project/a.txt",
        "/tmp/project/b.txt",
    )


def test_expand_custom_action_rejects_embedded_selection() -> None:
    action = CustomActionConfig(
        name="Bad selection",
        command=("echo", "files={selection}"),
        when="selection",
    )

    try:
        expand_custom_action(
            action,
            CustomActionContext(cwd="/tmp/project", selection=("/tmp/project/a.txt",)),
        )
    except CustomActionExpansionError as error:
        assert "{selection} must be a standalone command argument" in str(error)
    else:
        raise AssertionError("expected CustomActionExpansionError")
