from dataclasses import dataclass

from config import (
    DEFAULT_BRAILLE_FONT,
    DEFAULT_VIEW_FONT_SIZE,
    DEFAULT_VIEW_SCHEME,
    get_braille_font,
    get_view_font_size,
    get_view_scheme,
    set_view_settings,
)

VIEW_FONT_SIZE_MIN = 8
VIEW_FONT_SIZE_MAX = 48
VIEW_SCHEME_KEYS = ("light", "dark")
BRAILLE_FONT_KEYS = ("default", "simbraille")


@dataclass(frozen=True)
class ViewSettings:
    font_size: int
    scheme: str
    braille_font: str


def normalize_view_settings(settings: ViewSettings) -> ViewSettings:
    return ViewSettings(
        font_size=max(VIEW_FONT_SIZE_MIN, min(VIEW_FONT_SIZE_MAX, settings.font_size)),
        scheme=settings.scheme if settings.scheme in VIEW_SCHEME_KEYS else DEFAULT_VIEW_SCHEME,
        braille_font=(
            settings.braille_font
            if settings.braille_font in BRAILLE_FONT_KEYS
            else DEFAULT_BRAILLE_FONT
        ),
    )


def load_view_settings() -> ViewSettings:
    return normalize_view_settings(
        ViewSettings(
            get_view_font_size(DEFAULT_VIEW_FONT_SIZE),
            get_view_scheme(DEFAULT_VIEW_SCHEME),
            get_braille_font(DEFAULT_BRAILLE_FONT),
        )
    )


def save_view_settings(settings: ViewSettings) -> None:
    normalized = normalize_view_settings(settings)
    set_view_settings(
        normalized.font_size,
        normalized.scheme,
        normalized.braille_font,
    )