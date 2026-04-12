"""Theme helpers shared across configuration, reducers, and selectors."""

from textual.theme import BUILTIN_THEMES

DEFAULT_APP_THEME = "textual-dark"
SUPPORTED_APP_THEMES = tuple(sorted(BUILTIN_THEMES))
SUPPORTED_APP_THEME_DISPLAY = ", ".join(SUPPORTED_APP_THEMES)

_LIGHT_PREVIEW_SYNTAX_THEME = "friendly"
_DARK_PREVIEW_SYNTAX_THEME = "monokai"


def preview_syntax_theme_for_app_theme(app_theme: str) -> str:
    """Return the preview syntax theme that matches the active Textual theme."""

    theme = BUILTIN_THEMES.get(app_theme, BUILTIN_THEMES[DEFAULT_APP_THEME])
    return _DARK_PREVIEW_SYNTAX_THEME if theme.dark else _LIGHT_PREVIEW_SYNTAX_THEME
