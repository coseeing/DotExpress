def get_public_error_message(error: Exception) -> str:
    message = str(error)
    if not message:
        return "An unknown error occurred."
    if "Can't translate: tables" in message and "inbuf" in message:
        return "The selected translation table could not translate this text."
    return message
