from i18n import N_


def get_public_error_message(error: Exception) -> str:
    """The text of ``error``; a msgid for an empty text and for liblouis' "Can't translate".

    ``format_conversion_error`` translates the result (F-12 D2).
    """
    message = str(error)
    if not message:
        return N_("An unknown error occurred.")
    if "Can't translate: tables" in message and "inbuf" in message:
        return N_("The selected translation table could not translate this text.")
    return message
