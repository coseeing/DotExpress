from conversion.alignment import TranslationResult


def merge_translation_results(translations):
    return TranslationResult.concat(translations or ())


def wrap_translation_results(translations, width: int) -> tuple[str, str]:
    translation_result = merge_translation_results(translations)
    translation_result.reclean_braille_endspace()
    translation_result.bind_word_tokens()
    translation_result.reclean_token()
    return translation_result.wrap(width)
