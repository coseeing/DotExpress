from dataclasses import dataclass

from config import (
    ConfigSaveProblem,
    ConfigStore,
    DEFAULT_BRAILLE_FONT,
    DEFAULT_VIEW_FONT_SIZE,
    DEFAULT_VIEW_SCHEME,
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


def load_view_settings(store: ConfigStore) -> ViewSettings:
    return normalize_view_settings(
        ViewSettings(
            store.get_view_font_size(DEFAULT_VIEW_FONT_SIZE),
            store.get_view_scheme(DEFAULT_VIEW_SCHEME),
            store.get_braille_font(DEFAULT_BRAILLE_FONT),
        )
    )


def save_view_settings(store: ConfigStore, settings: ViewSettings) -> ConfigSaveProblem | None:
    normalized = normalize_view_settings(settings)
    return store.set_view_settings(
        normalized.font_size,
        normalized.scheme,
        normalized.braille_font,
    )