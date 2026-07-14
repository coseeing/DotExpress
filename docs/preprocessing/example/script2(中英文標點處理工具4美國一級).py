"""US Grade 1 punctuation preprocessing for DotExpress Text Processing."""

import re


C2E_PUNCTUATION = {
    "—": "--",
    "─": "--",
    "（": "(",
    "）": ")",
    "「": "'",
    "」": "'",
    "‘": "'",
    "’": "'",
    "『": '"',
    "“": '"',
    "”": '"',
    "【": "[",
    "】": "]",
    "〔": "[",
    "〕": "]",
    "《": "'",
    "》": "'",
    "〈": "'",
    "〉": "'",
    "！": "!",
    "，": ",",
    "、": ",",
    "。": ".",
    "；": ";",
    "：": ":",
    "？": "?",
    "…": "...",
}

E2C_PUNCTUATION = {
    "(": "（",
    ")": "）",
    "[": "【",
    "]": "】",
    "!": "！",
    ",": "，",
    ".": "。",
    ";": "；",
    ":": "：",
    "?": "？",
}

PUNCTUATION = set(C2E_PUNCTUATION) | set(E2C_PUNCTUATION)
LEFT_PUNCTUATION = {
    "（",
    "「",
    "‘",
    "『",
    "“",
    "【",
    "〔",
    "《",
    "〈",
    "─",
    "—",
    "(",
    "[",
}
RIGHT_PUNCTUATION = PUNCTUATION - LEFT_PUNCTUATION


def _find_next_text(text: str, position: int) -> str | None:
    for character in text[position + 1 :]:
        if character not in PUNCTUATION and not character.isspace():
            return character
    return None


def _find_previous_text(text: str, position: int) -> str | None:
    for character in reversed(text[:position]):
        if character not in PUNCTUATION and not character.isspace():
            return character
    return None


def _character_type(character: str | None) -> str | None:
    if character is None:
        return None
    return "EN" if re.match(r"[A-Za-z0-9]", character) else "ZH"


def _convert_punctuation(character: str, mode: str | None) -> str:
    if mode == "EN":
        return C2E_PUNCTUATION.get(character, character)
    if mode == "ZH":
        return E2C_PUNCTUATION.get(character, character)
    return character


def _preprocess_text(text: str) -> str:
    for source, replacement in {
        "（,’": "（⠠⠄",
        "（、'": "（⠠⠄",
        "(,'": "（⠠⠄",
    }.items():
        text = text.replace(source, replacement)
    return text


def _process_punctuation(text: str) -> str:
    result: list[str] = []

    for position, character in enumerate(text):
        if character not in PUNCTUATION:
            result.append(character)
        elif character in LEFT_PUNCTUATION:
            result.append(
                _convert_punctuation(
                    character,
                    _character_type(_find_next_text(text, position)),
                )
            )
        elif character in RIGHT_PUNCTUATION:
            result.append(
                _convert_punctuation(
                    character,
                    _character_type(_find_previous_text(text, position)),
                )
            )
        else:
            result.append(character)

    return "".join(result)


def main(text: str) -> str:
    return _process_punctuation(_preprocess_text(text))
