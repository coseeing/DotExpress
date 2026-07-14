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
