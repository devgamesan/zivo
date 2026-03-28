from peneo.readme_screenshots import FIXTURE_ROOT, PROJECT_ROOT, get_capture_output_names


def test_readme_screenshot_outputs_are_stable() -> None:
    assert get_capture_output_names() == (
        "screen1.png",
        "screen-split-terminal.png",
        "screen-multi-select.png",
        "screen-command-palette.png",
        "screen-filter.png",
        "screen-attributes.png",
    )


def test_readme_screenshot_fixture_paths_live_under_repo() -> None:
    assert PROJECT_ROOT.is_relative_to(FIXTURE_ROOT)
