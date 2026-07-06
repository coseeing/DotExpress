import unittest

from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator


class TranslationFallbackTest(unittest.TestCase):
    def assert_character_fallback(self, result, source: str, expected: str) -> None:
        self.assertEqual(result.raw, list(source))
        self.assertEqual(result.braille, list(expected))
        self.assertEqual(result.raw_to_braille_pos, list(range(len(source))))
        self.assertEqual(result.braille_to_raw_pos, list(range(len(source))))

    def test_text_maps_characters_spaces_and_newlines(self) -> None:
        result = FallbackTextTranslator().translate(
            "ignored replacement",
            table="zh-tw.ctb",
            raw="我 們\n1+2",
        )

        self.assert_character_fallback(result, "我 們\n1+2", "⣿⠀⣿\n⣿⣿⣿")

    def test_text_uses_raw_when_replacement_length_differs(self) -> None:
        result = FallbackTextTranslator().translate(
            "long replacement",
            table="zh-tw.ctb",
            raw="字",
        )

        self.assert_character_fallback(result, "字", "⣿")

    def test_atomic_text_keeps_character_mapping(self) -> None:
        result = FallbackTextTranslator().translate(
            "replacement",
            table="zh-tw.ctb",
            raw="原文",
            single_token=True,
        )

        self.assert_character_fallback(result, "原文", "⣿⣿")

    def test_math_uses_same_character_contract(self) -> None:
        result = FallbackMathTranslator().translate("1 + 2", braille_code="Nemeth")

        self.assert_character_fallback(result, "1 + 2", "⣿⠀⣿⠀⣿")

    def test_empty_source_returns_empty_result(self) -> None:
        result = FallbackMathTranslator().translate("", braille_code="Nemeth")

        self.assert_character_fallback(result, "", "")


if __name__ == "__main__":
    unittest.main()
