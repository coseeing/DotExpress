from __future__ import annotations

from collections.abc import Callable

from translate import TranslationResult


class MathCATMathTranslator:
    def __init__(self, *, translate_math: Callable[..., str]):
        self._translate_math = translate_math

    def translate(self, source: str, *, braille_code: str) -> TranslationResult:
        braille = list(
            self._translate_math(source, braille_code=braille_code)
        )
        if not source:
            return TranslationResult([], [], [], [])
        return TranslationResult(
            [source],
            braille,
            [0] * len(braille),
            [0],
        )
