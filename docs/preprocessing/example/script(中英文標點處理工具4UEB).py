"""Convert punctuation according to the former 37d9a6 preprocessing rules."""

import re


C2E_PUNCTUATION = {
    "——": "⠐⠠⠤",
    "──": "⠐⠠⠤",
    "（": "(",
    "）": ")",
    "「": "⠠⠦",
    "」": "⠠⠴",
    "‘": "⠠⠦",
    "’": "⠠⠴",
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
    "—": "⠠⠤",
    "─": "⠠⠤",
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
    "──",
    "——",
    "─",
    "—",
    "(",
    "[",
}
RIGHT_PUNCTUATION = PUNCTUATION - LEFT_PUNCTUATION
MULTI_CHARACTER_PUNCTUATION = tuple(
    sorted(
        (punctuation for punctuation in PUNCTUATION if len(punctuation) > 1),
        key=len,
        reverse=True,
    )
)
TOKEN_PATTERN = re.compile(
    "|".join(map(re.escape, MULTI_CHARACTER_PUNCTUATION)) + r"|[\s\S]"
)


def _find_text(tokens: list[str]) -> str | None:
    return next(
        (
            token
            for token in tokens
            if token not in PUNCTUATION and not token.isspace()
        ),
        None,
    )


def _classify_character(character: str | None) -> str | None:
    if character is None:
        return None
    return "EN" if character.isascii() and character.isalnum() else "ZH"


def _map_punctuation(token: str, mode: str | None) -> str:
    if mode == "EN":
        return C2E_PUNCTUATION.get(token, token)
    if mode == "ZH":
        return E2C_PUNCTUATION.get(token, token)
    return token


def main(text: str) -> str:
    tokens = TOKEN_PATTERN.findall(text)
    result: list[str] = []

    for position, token in enumerate(tokens):
        if token not in PUNCTUATION:
            result.append(token)
        elif token in LEFT_PUNCTUATION:
            result.append(_map_punctuation(token, _classify_character(_find_text(tokens[position + 1 :]))))
        elif token in RIGHT_PUNCTUATION:
            result.append(_map_punctuation(token, _classify_character(_find_text(tokens[:position][::-1]))))
        else:
            result.append(token)

    return "".join(result)
