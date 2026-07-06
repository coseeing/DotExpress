from translate import TranslationResult


def build_character_fallback(source: str) -> TranslationResult:
    braille = [
        "\n" if char == "\n" else "⠀" if char == " " else "⣿"
        for char in source
    ]
    positions = list(range(len(source)))
    return TranslationResult(
        list(source),
        braille,
        positions.copy(),
        positions.copy(),
    )


class FallbackTextTranslator:
    def translate(
        self,
        text: str,
        *,
        table: str,
        raw: str,
        single_token: bool = False,
    ) -> TranslationResult:
        return build_character_fallback(raw)


class FallbackMathTranslator:
    def translate(self, source: str, *, braille_code: str) -> TranslationResult:
        return build_character_fallback(source)
