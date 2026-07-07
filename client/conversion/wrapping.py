from pathlib import Path
from typing import Callable

from adapters.translation.contracts import TranslationRuntime


def merge_translation_results(translations):
    from translate import TranslationResult

    if not translations:
        return TranslationResult([], [], [], [])
    merged = TranslationResult([], [], [], [])
    for segment in translations:
        merged = merged + segment
    return merged


def wrap_translation_results(translations, width: int) -> tuple[str, str]:
    translation_result = merge_translation_results(translations)
    translation_result.reclean_braille_endspace()
    translation_result.bind_word_tokens()
    translation_result.reclean_token()
    return translation_result.wrap(width)


def translate_and_wrap_both(
    *,
    table_file: str,
    text: str,
    width: int,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
    runtime: TranslationRuntime,
    translate_with_language: Callable[..., object],
) -> tuple[str, str]:
    translation_result = translate_with_language(
        table_file,
        text,
        dictionary_path,
        translation_tables,
        bopomofo_path,
        runtime=runtime,
    )
    translation_result.reclean_braille_endspace()
    translation_result.bind_word_tokens()
    translation_result.reclean_token()
    braille_wrapped, text_wrapped = translation_result.wrap(width)
    return braille_wrapped, text_wrapped
