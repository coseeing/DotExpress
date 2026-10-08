from __future__ import annotations

from collections.abc import Callable

from translate import TranslationResult


class MathCATMathTranslator:
    def __init__(
        self,
        *,
        translate_math: Callable[..., str],
        close: Callable[[], None] | None = None,
    ):
        self._translate_math = translate_math
        self._close = close

    def close(self) -> None:
        if self._close is not None:
            self._close()

    def translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult:
        braille = list(
            self._translate_math(source, braille_code=braille_code, language=language)
        )
        if not source:
            return TranslationResult([], [], [], [])
        return TranslationResult(
            [source],
            braille,
            [0] * len(braille),
            [0],
        )
