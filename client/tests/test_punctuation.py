import unittest

from conversion.preprocessing.literal_braille import (
    LiteralBrailleToken,
    TextToken,
    is_unicode_braille,
    preprocess_punctuation,
)


class PunctuationProcessingTest(unittest.TestCase):
    def render(self, text: str) -> str:
        return "".join(
            token.braille_text if isinstance(token, LiteralBrailleToken) else token.text
            for token in preprocess_punctuation(text)
        )

    def test_converts_parentheses_around_english_text_to_ascii(self) -> None:
        self.assertEqual(self.render("（ABC）"), "(ABC)")

    def test_converts_parentheses_around_chinese_text_to_fullwidth(self) -> None:
        self.assertEqual(self.render("(中文)"), "（中文）")

    def test_converts_chinese_punctuation_adjacent_to_english_text(self) -> None:
        self.assertEqual(self.render("ABC，DEF。"), "ABC,DEF.")

    def test_converts_chinese_quotes_and_dash_to_ueb_braille_punctuation(self) -> None:
        self.assertEqual(self.render("「ABC」ABC—DEF"), "⠠⠦ABC⠠⠴ABC⠠⠤DEF")

    def test_converts_double_em_dash_as_one_longest_match_token(self) -> None:
        self.assertEqual(self.render("——ABC"), "⠐⠠⠤ABC")

    def test_converts_double_box_drawing_dash_as_one_longest_match_token(self) -> None:
        self.assertEqual(self.render("──ABC"), "⠐⠠⠤ABC")

    def test_skips_spaces_when_finding_neighboring_text(self) -> None:
        self.assertEqual(self.render("（  ABC  ）"), "(  ABC  )")

    def test_keeps_punctuation_without_a_neighbor_unchanged(self) -> None:
        self.assertEqual(self.render("（）"), "（）")

    def test_keeps_unmapped_ascii_quotes_unchanged(self) -> None:
        self.assertEqual(self.render('"ABC"'), '"ABC"')

    def test_separates_literal_braille_from_normalized_text(self) -> None:
        self.assertEqual(
            preprocess_punctuation("（ABC）「DEF」"),
            (
                TextToken("(ABC)"),
                LiteralBrailleToken("「", "⠠⠦"),
                TextToken("DEF"),
                LiteralBrailleToken("」", "⠠⠴"),
            ),
        )

    def test_detects_only_complete_unicode_braille_mapping_outputs(self) -> None:
        self.assertTrue(is_unicode_braille("⠐⠠⠤"))
        self.assertFalse(is_unicode_braille("⠠A"))
        self.assertFalse(is_unicode_braille(""))


if __name__ == "__main__":
    unittest.main()
