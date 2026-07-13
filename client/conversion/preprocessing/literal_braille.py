from dataclasses import dataclass
from collections.abc import Iterable

from .punctuation import PunctuationMapping, TextToken, tokenize_punctuation


@dataclass(frozen=True)
class LiteralBrailleToken:
    source_text: str
    braille_text: str


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


def _append_text_token(tokens: list[TextToken | LiteralBrailleToken], text: str) -> None:
    if not text:
        return
    if tokens and isinstance(tokens[-1], TextToken):
        previous = tokens[-1]
        tokens[-1] = TextToken(previous.text + text)
        return
    tokens.append(TextToken(text))


def split_literal_braille(
    tokens: Iterable[TextToken | PunctuationMapping],
) -> tuple[TextToken | LiteralBrailleToken, ...]:
    result: list[TextToken | LiteralBrailleToken] = []
    for token in tokens:
        if isinstance(token, TextToken):
            _append_text_token(result, token.text)
        elif is_unicode_braille(token.mapped_text):
            result.append(LiteralBrailleToken(token.source_text, token.mapped_text))
        else:
            _append_text_token(result, token.mapped_text)
    return tuple(result)


def preprocess_punctuation(text: str) -> tuple[TextToken | LiteralBrailleToken, ...]:
    return split_literal_braille(tokenize_punctuation(text))
