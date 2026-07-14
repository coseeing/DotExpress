def is_unicode_braille(text: str) -> bool:
    return bool(text) and all("\u2800" <= character <= "\u28ff" for character in text)


def build_literal_translation_result(source_text: str, braille_text: str):
    from translate import TranslationResult

    braille = list(braille_text)
    return TranslationResult(
        [source_text],
        braille,
        [0] * len(braille),
        [0],
    )
