from pathlib import Path

from adapters.translation.contracts import TranslationRuntime


def build_literal_translation_result(text: str):
    from translate import TranslationResult

    braille = list(text)
    return TranslationResult([text], braille, [0] * len(braille), [0])


def get_public_error_message(error: Exception) -> str:
    message = str(error)
    if not message:
        return "An unknown error occurred."
    if "Can't translate: tables" in message and "inbuf" in message:
        return "The selected translation table could not translate this text."
    return message


def translate_plain_text_segment(
    table_file: str,
    text: str,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
    *,
    runtime: TranslationRuntime,
):
    from Bopomofo import normalize_zhuyin_sequence
    from languageDetection import LangChangeCommand, LanguageDetector
    from utils import apply_dictionary, split_bracket_segments

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
