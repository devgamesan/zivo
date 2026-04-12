"""Theme helpers shared across configuration, reducers, and selectors."""

from pygments.styles import get_all_styles
from textual.theme import BUILTIN_THEMES

DEFAULT_APP_THEME = "textual-dark"
SUPPORTED_APP_THEMES = tuple(sorted(BUILTIN_THEMES))
SUPPORTED_APP_THEME_DISPLAY = ", ".join(SUPPORTED_APP_THEMES)
AUTO_PREVIEW_SYNTAX_THEME = "auto"
SUPPORTED_PREVIEW_SYNTAX_STYLES = tuple(sorted(get_all_styles()))
SUPPORTED_PREVIEW_SYNTAX_THEMES = (
    AUTO_PREVIEW_SYNTAX_THEME,
    *SUPPORTED_PREVIEW_SYNTAX_STYLES,
)
SUPPORTED_PREVIEW_SYNTAX_THEME_DISPLAY = (
    "auto or a supported Pygments style "
    "(for example: one-dark, xcode, nord, gruvbox-dark)"
)

_LIGHT_PREVIEW_SYNTAX_THEME = "friendly"
_DARK_PREVIEW_SYNTAX_THEME = "monokai"


def preview_syntax_theme_for_app_theme(app_theme: str, configured_style: str) -> str:
    """Return the preview syntax theme for the active Textual theme and config."""

    if (
        configured_style != AUTO_PREVIEW_SYNTAX_THEME
        and configured_style in SUPPORTED_PREVIEW_SYNTAX_STYLES
    ):
        return configured_style

    theme = BUILTIN_THEMES.get(app_theme, BUILTIN_THEMES[DEFAULT_APP_THEME])
    return _DARK_PREVIEW_SYNTAX_THEME if theme.dark else _LIGHT_PREVIEW_SYNTAX_THEME
