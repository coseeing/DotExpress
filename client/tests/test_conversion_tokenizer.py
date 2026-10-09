import unittest

from conversion import tokenizer
from translate import TranslationResult


def word_tokens(text: str) -> list[str]:
    units = list(text)
    return ["".join(units[start:end]) for start, end in tokenizer.word_token_spans(units)]


class ContractedTokenSpansTest(unittest.TestCase):
    def test_characters_with_one_braille_start_form_one_span(self) -> None:
        self.assertEqual(
            tokenizer.contracted_token_spans([0, 2, 3, 3, 3, 4, 5, 6, 7, 7]),
            [(0, 1), (1, 2), (2, 5), (5, 6), (6, 7), (7, 8), (8, 10)],
        )

    def test_no_positions_give_no_spans(self) -> None:
        self.assertEqual(tokenizer.contracted_token_spans([]), [])


class WordTokenSpansTest(unittest.TestCase):
    def test_ascii_letters_and_digits_form_one_token(self) -> None:
        self.assertEqual(word_tokens("Cos 2026 a1"), ["Cos", " ", "2026", " ", "a1"])

    def test_each_cjk_character_is_its_own_token(self) -> None:
        self.assertEqual(word_tokens("我們かな한글"), ["我", "們", "か", "な", "한", "글"])

    def test_a_newline_is_its_own_token(self) -> None:
        self.assertEqual(word_tokens("a\n\nb"), ["a", "\n", "\n", "b"])

    def test_a_trailing_punctuation_chain_joins_the_previous_word(self) -> None:
        self.assertEqual(word_tokens("共視。」"), ["共", "視。」"])
        self.assertEqual(word_tokens("Hello,."), ["Hello,."])

    def test_a_leading_punctuation_chain_joins_the_next_word(self) -> None:
        self.assertEqual(word_tokens("「「嶼我"), ["「「嶼", "我"])
        self.assertEqual(word_tokens("(one)"), ["(one)"])

    def test_a_leading_mark_before_a_space_or_newline_stays_alone(self) -> None:
        self.assertEqual(word_tokens("「 我"), ["「", " ", "我"])
        self.assertEqual(word_tokens("「　我"), ["「", "　", "我"])
        self.assertEqual(word_tokens("「\n我"), ["「", "\n", "我"])
        self.assertEqual(word_tokens("我「"), ["我", "「"])

    def test_an_em_dash_leads_the_next_word(self) -> None:
        self.assertEqual(word_tokens("——破折"), ["——破", "折"])

    def test_without_language_blocks_cjk_characters_take_no_punctuation(self) -> None:
        units = list("「嶼」")
        self.assertEqual(tokenizer.word_token_spans(units, {}), [(0, 1), (1, 2), (2, 3)])


class SeparatorPositionsTest(unittest.TestCase):
    def test_a_separator_goes_between_closing_and_opening_marks(self) -> None:
        tokens = ["我」", "「共", "）", "（", "乙", "]", "["]
        self.assertEqual(list(tokenizer.iter_separator_positions(tokens)), [1, 3, 6])

    def test_empty_tokens_and_other_pairs_get_no_separator(self) -> None:
        self.assertEqual(list(tokenizer.iter_separator_positions(["」", "", "「", "「", "」"])), [])
        self.assertEqual(list(tokenizer.iter_separator_positions([])), [])
        self.assertEqual(list(tokenizer.iter_separator_positions(["」"])), [])


class SharedConstantsTest(unittest.TestCase):
    def test_translation_result_exposes_the_tokenizer_constants(self) -> None:
        names = (
            "LEFT_PUNCT_HALF", "RIGHT_PUNCT_HALF", "MIDDLE_SENTENCE_PUNCT_HALF", "END_SENTENCE_PUNCT_HALF",
            "LEFT_PUNCT_FULL", "RIGHT_PUNCT_FULL", "MIDDLE_SENTENCE_PUNCT_FULL", "END_SENTENCE_PUNCT_FULL",
            "LEFT_PUNCT", "RIGHT_PUNCT", "MIDDLE_SENTENCE_PUNCT", "END_SENTENCE_PUNCT",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(TranslationResult, name), getattr(tokenizer, name))
        self.assertIs(TranslationResult.lang_blocks, tokenizer.CJK_LANGUAGE_BLOCKS)

    def test_hoisted_sets_keep_their_members(self) -> None:
        self.assertEqual(tokenizer.ASCII_ALNUM, frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
        self.assertEqual(
            tokenizer.TRAIL_PUNCT,
            tokenizer.RIGHT_PUNCT | tokenizer.MIDDLE_SENTENCE_PUNCT | tokenizer.END_SENTENCE_PUNCT,
        )
        self.assertEqual(tokenizer.LEAD_PUNCT, tokenizer.LEFT_PUNCT | {"—"})


if __name__ == "__main__":
    unittest.main()
