from __future__ import annotations

import os
from pathlib import Path

from translate import TranslationResult


BRAILLE_UNICODE_PATTERNS_START = 0x2800


class LiblouisTextTranslator:
    def __init__(self, *, helper, tables_dir: str | Path):
        self._helper = helper
        self._tables_dir = str(tables_dir)

    def close(self) -> None:
        self._helper.terminate()

    def translate(
        self,
        text: str,
        *,
        table: str,
        raw: str,
        single_token: bool = False,
    ) -> TranslationResult:
        table_path = os.path.join(self._tables_dir, table)
        cells, braille_to_raw, raw_to_braille, _cursor = self._helper.translate(
            [table_path],
            text,
            mode=4,
        )
        braille = [
            chr(cell + BRAILLE_UNICODE_PATTERNS_START)
            for cell in cells
        ]
        if single_token:
            if not raw:
                return TranslationResult([], [], [], [])
            return TranslationResult(
                [raw],
                braille,
                [0] * len(braille),
                [0],
            )
        return TranslationResult(
            list(text),
            braille,
            braille_to_raw,
            raw_to_braille,
        )
