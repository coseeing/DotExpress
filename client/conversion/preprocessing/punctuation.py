from dataclasses import dataclass
import re
from collections.abc import Iterable


@dataclass(frozen=True)
class TextToken:
    text: str


@dataclass(frozen=True)
class PunctuationMapping:
    source_text: str
    mapped_text: str


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


def _find_text(tokens: Iterable[str]) -> str | None:
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


def tokenize_punctuation(text: str) -> tuple[TextToken | PunctuationMapping, ...]:
    tokens = TOKEN_PATTERN.findall(text)
    result: list[TextToken | PunctuationMapping] = []

    for position, token in enumerate(tokens):
        if token not in PUNCTUATION:
            result.append(TextToken(token))
            continue

        if token in LEFT_PUNCTUATION:
            mode = _classify_character(_find_text(tokens[position + 1 :]))
        elif token in RIGHT_PUNCTUATION:
            mode = _classify_character(_find_text(reversed(tokens[:position])))
        else:
            result.append(TextToken(token))
            continue

        result.append(PunctuationMapping(token, _map_punctuation(token, mode)))

    return tuple(result)
