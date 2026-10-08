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
from .options import (
    BRAILLE_FONT_OPTIONS,
    VIEW_FONT_SIZE_RANGE,
    VIEW_SCHEME_OPTIONS,
    normalize_option_value,
)


@dataclass(frozen=True)
class ViewSettings:
    font_size: int
    scheme: str
    braille_font: str


def normalize_view_settings(settings: ViewSettings) -> ViewSettings:
    return ViewSettings(
        font_size=VIEW_FONT_SIZE_RANGE.clamp(settings.font_size),
        scheme=normalize_option_value(VIEW_SCHEME_OPTIONS, settings.scheme, DEFAULT_VIEW_SCHEME),
        braille_font=normalize_option_value(
            BRAILLE_FONT_OPTIONS,
            settings.braille_font,
            DEFAULT_BRAILLE_FONT,
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