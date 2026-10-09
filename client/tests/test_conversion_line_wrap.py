import copy
import unittest

from conversion import line_wrap, tokenizer
from tests import legacy_translation_result as legacy


BLANK = chr(0x2800)
# The WrapTest fixtures of tests/test_translation_result.py: (tokens, braille, raw_to_braille_pos).
WRAP_CASES = (
    (["「嶼我共視是一個關心數位無障礙」", "\n", "「嶼我共視是一個關心數位無障礙」"], [BLANK] * 40, [0, 20, 20]),
    (["「嶼我共視 是個關心數位無障礙」", "\n", "「嶼我共視 是個關心數位無障礙」"], ["⠁"] * 38, [0, 19, 19]),
    (["「嶼我」", "『共視』"], ["⠁"] * 8, [0, 4]),
    (["Coseeing is a community dedicated to an", " ", "I see"], [BLANK] * 46, [0, 40, 41]),
    (["Coseeing is a community dedicated to an", " ", "I see"], [BLANK] * 45, [0, 39, 40]),
    ([" ", " ", " ", "Coseeing is a community dedicated to", " ", "I see"], [BLANK] * 45, [0, 1, 2, 3, 40, 41]),
    (["中。", "\n", "\n", "文", " ", "字"], ["⠁", "⠂", BLANK, BLANK, "⠃", BLANK, "⠄"], [0, 2, 3, 4, 5, 6]),
)


class WrapTokensTest(unittest.TestCase):
    def test_wrap_tokens_matches_the_pre_split_wrap(self) -> None:
        for index, (tokens, braille, raw_to_braille_pos) in enumerate(WRAP_CASES):
            for width in (1, 2, 5, 10, 39, 40, 41):
                with self.subTest(case=index, width=width):
                    oracle = legacy.TranslationResult(list(tokens), list(braille), [0] * len(braille), list(raw_to_braille_pos))
                    self.assertEqual(
                        line_wrap.wrap_tokens(tokens, braille, raw_to_braille_pos, width),
                        oracle.wrap(width),
                    )

    def test_a_full_width_closing_mark_gets_a_separator(self) -> None:
        self.assertEqual(
            line_wrap.wrap_tokens(["「嶼我」", "『共視』"], ["⠁"] * 8, [0, 4], 40),
            ("⠁⠁⠁⠁⠀⠁⠁⠁⠁" + BLANK * 31, "「嶼我」 『共視』"),
        )

    def test_wrap_tokens_does_not_mutate_its_inputs(self) -> None:
        for tokens, braille, raw_to_braille_pos in WRAP_CASES:
            arguments = (list(tokens), list(braille), list(raw_to_braille_pos))
            before = copy.deepcopy(arguments)

            line_wrap.wrap_tokens(*arguments, 10)

            self.assertEqual(arguments, before)

    def test_separator_and_space_sets(self) -> None:
        self.assertEqual(line_wrap.SEPARATED_AFTER_PUNCT, tokenizer.RIGHT_PUNCT_FULL | tokenizer.END_SENTENCE_PUNCT_FULL)
        self.assertIsInstance(line_wrap.SEPARATED_AFTER_PUNCT, frozenset)
        self.assertEqual(line_wrap.SPACE_ONLY, frozenset(" "))


if __name__ == "__main__":
    unittest.main()
