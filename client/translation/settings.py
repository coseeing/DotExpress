from __future__ import annotations

from dataclasses import dataclass

from config import (
    DEFAULT_CONVERSION_WIDTH,
    DEFAULT_OUTPUT_MODE,
    get_conversion_width,
    get_output_mode,
    get_selected_dictionary,
    set_conversion_width,
    set_output_mode,
    set_selected_dictionary,
)
from dictionaries.actions import resolve_dictionary_selection


MIN_CONVERSION_WIDTH = 10
MAX_CONVERSION_WIDTH = 200
SUPPORTED_OUTPUT_MODES = ("unicode", "ascii")


@dataclass(frozen=True)
class TranslationSettings:
    output_mode: str
    width: int
    selected_dictionary: str


DEFAULT_TRANSLATION_SETTINGS = TranslationSettings(
    output_mode=DEFAULT_OUTPUT_MODE,
    width=DEFAULT_CONVERSION_WIDTH,
    selected_dictionary="default",
)


def _normalize_output_mode(output_mode: str) -> str:
    if output_mode in SUPPORTED_OUTPUT_MODES:
        return output_mode
    return DEFAULT_TRANSLATION_SETTINGS.output_mode


def _normalize_width(width: int) -> int:
    return max(MIN_CONVERSION_WIDTH, min(MAX_CONVERSION_WIDTH, width))


def normalize_translation_settings(
    settings: TranslationSettings,
    dictionary_names: list[str],
) -> TranslationSettings:
    return TranslationSettings(
        output_mode=_normalize_output_mode(settings.output_mode),
        width=_normalize_width(settings.width),
        selected_dictionary=resolve_dictionary_selection(
            dictionary_names,
            settings.selected_dictionary,
        ),
    )


def load_translation_settings(dictionary_names: list[str]) -> TranslationSettings:
    settings = TranslationSettings(
        output_mode=get_output_mode(DEFAULT_OUTPUT_MODE),
        width=get_conversion_width(DEFAULT_CONVERSION_WIDTH),
        selected_dictionary=get_selected_dictionary(DEFAULT_TRANSLATION_SETTINGS.selected_dictionary),
    )
    return normalize_translation_settings(settings, dictionary_names)


def save_translation_settings(settings: TranslationSettings) -> None:
    set_output_mode(settings.output_mode)
    set_conversion_width(settings.width)
    set_selected_dictionary(settings.selected_dictionary)

