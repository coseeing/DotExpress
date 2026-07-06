from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from translate import TranslationResult


class RuntimeUnavailableError(RuntimeError):
    pass


class BrailleTextTranslator(Protocol):
    def translate(
        self,
        text: str,
        *,
        table: str,
        raw: str,
        single_token: bool = False,
    ) -> TranslationResult: ...


class MathSegmentTranslator(Protocol):
    def translate(self, source: str, *, braille_code: str) -> TranslationResult: ...


@dataclass
class TranslationRuntime:
    text_translator: BrailleTextTranslator
    math_translator: MathSegmentTranslator
    close_callbacks: tuple[Callable[[], None], ...] = ()
    _closed: bool = field(default=False, init=False, repr=False)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for callback in reversed(self.close_callbacks):
            callback()
