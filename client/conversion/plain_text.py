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
