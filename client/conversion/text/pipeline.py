from pathlib import Path
from typing import Callable

from adapters.translation.contracts import TranslationRuntime
from .char_maps import map_characters
from .dictionary_rules import apply_dictionary, split_bracket_segments


def preprocess_source_text(
    text: str,
    *,
    data_dir: Path,
    map_char: Callable[..., str] = map_characters,
) -> str:
    return map_char(
        text,
        dictionary_path=data_dir / "BopomofoChar2Braille.csv",
        from_field="Bopomofo",
        to_field="Braille",
    )


def apply_plain_text_rules(
    text: str,
    *,
    dictionary_path: Path,
    bopomofo_path: Path,
    processing: Callable[[str], str],
) -> dict[str, str]:
    return apply_dictionary(
        text,
        dictionary_path=dictionary_path,
        bopomofo_path=bopomofo_path,
        processing=processing,
    )


def translate_plain_text_segment(
    table_file: str,
    text: str,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
    *,
    runtime: TranslationRuntime,
):
    from text.zhuyin import normalize_zhuyin_sequence
    from languageDetection import LangChangeCommand, LanguageDetector

    language = [key for key, value in translation_tables.items() if key not in {"default", "math"} and value != ""]
    language_detector = LanguageDetector(language)
    sequence = list(language_detector.add_detected_language_commands([text]))

    translate_table = translation_tables["default"]
    translations = []
    for item in sequence:
        if isinstance(item, str):
            result = apply_dictionary(
                item,
                dictionary_path=dictionary_path,
                bopomofo_path=bopomofo_path,
                processing=normalize_zhuyin_sequence,
            )
            raw_segments = split_bracket_segments(result["raw"])
            replacement_segments = split_bracket_segments(result["replacement"])

            for raw_segment, replacement_segment in zip(raw_segments, replacement_segments):
                if raw_segment["atomic"] != replacement_segment["atomic"]:
                    raise ValueError("atomic not match")
                translations.append(
                    runtime.text_translator.translate(
                        replacement_segment["text"],
                        table=translate_table,
                        raw=raw_segment["text"],
                        single_token=replacement_segment["atomic"],
                    )
                )
        elif isinstance(item, LangChangeCommand):
            previous_translate_table = translate_table
            lang = item.lang.split("_")[0]
            try:
                translate_table = translation_tables[lang]
                if translate_table == "":
                    translate_table = translation_tables["default"]
            except KeyError:
                translate_table = translation_tables["default"]
            if translate_table != previous_translate_table:
                raw = translations[-1].raw if translations else None
                if raw and not raw[-1].isspace():
                    translations.append(
                        runtime.text_translator.translate(
                            " ",
                            table=previous_translate_table,
                            raw=" ",
                        )
                    )

    assert translations, "No translatable text segments were found."
    return translations
