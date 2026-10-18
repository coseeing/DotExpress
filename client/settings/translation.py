from __future__ import annotations

from dataclasses import dataclass

from config import (
    ConfigSaveProblem,
    ConfigStore,
    DEFAULT_CONVERSION_WIDTH,
    DEFAULT_OUTPUT_MODE,
)
from conversion.preprocessing.user_script import NO_PROCESSING_SCRIPT_NAME
from dictionaries.actions import resolve_dictionary_selection
from text_scripts.manager import resolve_selected_script
from .options import CONVERSION_WIDTH_RANGE, OUTPUT_MODE_OPTIONS, normalize_option_value


@dataclass(frozen=True)
class TranslationSettings:
    output_mode: str
    width: int
    selected_dictionary: str
    # The text-processing script (F-18 D3); No Processing skips the script stage.
    selected_script: str = NO_PROCESSING_SCRIPT_NAME


DEFAULT_TRANSLATION_SETTINGS = TranslationSettings(
    output_mode=DEFAULT_OUTPUT_MODE,
    width=DEFAULT_CONVERSION_WIDTH,
    selected_dictionary="default",
    selected_script=NO_PROCESSING_SCRIPT_NAME,
)


def _normalize_output_mode(output_mode: str) -> str:
    return normalize_option_value(
        OUTPUT_MODE_OPTIONS,
        output_mode,
        DEFAULT_TRANSLATION_SETTINGS.output_mode,
    )


def _normalize_width(width: int) -> int:
    return CONVERSION_WIDTH_RANGE.clamp(width)


def normalize_translation_settings(
    settings: TranslationSettings,
    dictionary_names: list[str],
    script_names: list[str],
) -> TranslationSettings:
    return TranslationSettings(
        output_mode=_normalize_output_mode(settings.output_mode),
        width=_normalize_width(settings.width),
        selected_dictionary=resolve_dictionary_selection(
            dictionary_names,
            settings.selected_dictionary,
        ),
        selected_script=resolve_selected_script(script_names, settings.selected_script),
    )


def load_translation_settings(
    store: ConfigStore,
    dictionary_names: list[str],
    script_names: list[str],
) -> TranslationSettings:
    settings = TranslationSettings(
        output_mode=store.get_output_mode(DEFAULT_OUTPUT_MODE),
        width=store.get_conversion_width(DEFAULT_CONVERSION_WIDTH),
        selected_dictionary=store.get_selected_dictionary(DEFAULT_TRANSLATION_SETTINGS.selected_dictionary),
        selected_script=store.get_selected_script(DEFAULT_TRANSLATION_SETTINGS.selected_script),
    )
    return normalize_translation_settings(settings, dictionary_names, script_names)


def save_translation_settings(store: ConfigStore, settings: TranslationSettings) -> ConfigSaveProblem | None:
    """Save the four settings, each one even if another fails; the first problem, or ``None`` (F-12 D6)."""
    problems = (
        store.set_output_mode(settings.output_mode),
        store.set_conversion_width(settings.width),
        store.set_selected_dictionary(settings.selected_dictionary),
        store.set_selected_script(settings.selected_script),
    )
    return next((problem for problem in problems if problem is not None), None)

