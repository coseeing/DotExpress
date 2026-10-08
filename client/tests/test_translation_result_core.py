import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from conversion.wrapping import merge_translation_results
from languageDetection.unicode_blocks import build_language_blocks
from translate import TranslationResult


FIELDS = ("raw", "braille", "braille_to_raw_pos", "raw_to_braille_pos")
PUNCTUATION = {
    "LEFT_PUNCT_HALF": set("([{"),
    "RIGHT_PUNCT_HALF": set(")]}"),
    "MIDDLE_SENTENCE_PUNCT_HALF": set(",;:%"),
    "END_SENTENCE_PUNCT_HALF": set(".!?"),
    "LEFT_PUNCT_FULL": set("\u2018\u201c\u300c\u300e\u3008\u300a\u3010\u3014\u3016\uff08"),
    "RIGHT_PUNCT_FULL": set("\u2019\u201d\u300d\u300f\u3009\u300b\u3011\u3015\u3017\uff09"),
    "MIDDLE_SENTENCE_PUNCT_FULL": set("\uff0c\uff1b\uff1a\u3001\uff05"),
    "END_SENTENCE_PUNCT_FULL": set("\u3002\uff01\uff1f"),
}
for _kind in ("LEFT_PUNCT", "RIGHT_PUNCT", "MIDDLE_SENTENCE_PUNCT", "END_SENTENCE_PUNCT"):
    PUNCTUATION[_kind] = PUNCTUATION[f"{_kind}_HALF"] | PUNCTUATION[f"{_kind}_FULL"]


def lists_of(result) -> tuple[list, ...]:
    return tuple(getattr(result, name) for name in FIELDS)


class TranslationResultCoreTest(unittest.TestCase):
    def test_import_does_not_import_liblouis_helper(self) -> None:
        script = """
import sys
import translate
assert "braille.louis_helper" not in sys.modules, "braille.louis_helper was imported"
assert "braille.liblouis" not in sys.modules, "braille.liblouis was imported"
assert hasattr(translate, "TranslationResult")
assert not hasattr(translate, "translate")
assert not hasattr(translate, "translate_as_single_token")
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_addition_offsets_both_position_arrays(self) -> None:
        left = TranslationResult(["a"], ["⠁"], [0], [0])
        right = TranslationResult(["b"], ["⠃"], [0], [0])

        result = left + right

        self.assertEqual(result.raw, ["a", "b"])
        self.assertEqual(result.braille, ["⠁", "⠃"])
        self.assertEqual(result.braille_to_raw_pos, [0, 1])
        self.assertEqual(result.raw_to_braille_pos, [0, 1])

    def test_empty_result_has_empty_mapping(self) -> None:
        result = TranslationResult([], [], [], [])

        self.assertEqual(result.raw, [])
        self.assertEqual(result.braille, [])
        self.assertEqual(result.braille_to_raw_pos, [])
        self.assertEqual(result.raw_to_braille_pos, [])

    def test_addition_offsets_multi_token_results_without_aliasing(self) -> None:
        left = TranslationResult(["a", "b"], ["⠁", "⠃", "⠀"], [0, 1, 1], [0, 1])
        right = TranslationResult(["c"], ["⠉", "⠀"], [0, 0], [0])

        result = left + right

        self.assertEqual(
            lists_of(result),
            (["a", "b", "c"], ["⠁", "⠃", "⠀", "⠉", "⠀"], [0, 1, 1, 2, 2], [0, 1, 3]),
        )
        for name in FIELDS:
            self.assertIsNot(getattr(result, name), getattr(left, name), name)
            self.assertIsNot(getattr(result, name), getattr(right, name), name)
        with self.assertRaisesRegex(TypeError, "^not TranslateResult object$"):
            left + "x"

    def test_punctuation_sets_keep_their_members(self) -> None:
        result = TranslationResult([], [], [], [])

        self.assertEqual(len(PUNCTUATION), 12)
        for name, expected in PUNCTUATION.items():
            with self.subTest(name=name):
                self.assertEqual(set(getattr(result, name)), expected)

    def test_language_blocks_match_the_cjk_block_table(self) -> None:
        result = TranslationResult([], [], [], [])

        self.assertEqual(
            {language: list(blocks) for language, blocks in result.lang_blocks.items()},
            build_language_blocks({"ja", "zh", "ko"}),
        )


class SharedConstantsTest(unittest.TestCase):
    def test_instance_holds_only_its_data_fields(self) -> None:
        result = TranslationResult([], [], [], [])

        self.assertEqual(sorted(vars(result)), sorted(FIELDS))

    def test_construction_does_not_build_language_blocks(self) -> None:
        with patch("translate.build_language_blocks", side_effect=AssertionError("built per instance")) as build:
            TranslationResult([], [], [], [])

        build.assert_not_called()

    def test_shared_constants_are_immutable(self) -> None:
        for name in PUNCTUATION:
            with self.subTest(name=name):
                self.assertIsInstance(getattr(TranslationResult, name), frozenset)
        with self.assertRaises(TypeError):
            TranslationResult.lang_blocks["ja"] = ()


class EqualityTest(unittest.TestCase):
    def test_comparing_with_another_type_is_not_equal(self) -> None:
        result = TranslationResult(["a"], ["⠁"], [0], [0])

        self.assertFalse(result == object())
        self.assertTrue(result != "x")
        self.assertIs(result.__eq__(42), NotImplemented)

    def test_results_with_equal_lists_compare_equal(self) -> None:
        self.assertEqual(
            TranslationResult(["a"], ["⠁"], [0], [0]),
            TranslationResult(["a"], ["⠁"], [0], [0]),
        )
        self.assertNotEqual(
            TranslationResult(["a"], ["⠁"], [0], [0]),
            TranslationResult(["b"], ["⠁"], [0], [0]),
        )

    def test_results_are_unhashable(self) -> None:
        with self.assertRaises(TypeError):
            hash(TranslationResult([], [], [], []))


class MergeTranslationResultsTest(unittest.TestCase):
    def test_merging_nothing_gives_an_empty_result(self) -> None:
        for translations in ([], None):
            with self.subTest(translations=translations):
                merged = merge_translation_results(translations)

                self.assertIsInstance(merged, TranslationResult)
                self.assertEqual(lists_of(merged), ([], [], [], []))

    def test_merging_one_result_copies_its_lists(self) -> None:
        source = TranslationResult(["a", "b"], ["⠁", "⠃", "⠀"], [0, 1, 1], [0, 1])

        merged = merge_translation_results([source])

        self.assertIsNot(merged, source)
        self.assertEqual(lists_of(merged), lists_of(source))
        for name in FIELDS:
            self.assertIsNot(getattr(merged, name), getattr(source, name), name)

    def test_post_processing_the_merged_result_leaves_one_input_unchanged(self) -> None:
        source = TranslationResult(["中"], ["⠁", "⠂", "⠀"], [0, 0, 0], [0])

        merged = merge_translation_results([source])
        merged.reclean_braille_endspace()

        self.assertEqual(merged.braille, ["⠁", "⠂"])
        self.assertEqual(lists_of(source), (["中"], ["⠁", "⠂", "⠀"], [0, 0, 0], [0]))

    def test_mutating_the_merged_result_leaves_every_input_unchanged(self) -> None:
        first = TranslationResult(["中"], ["⠁", "⠂", "⠀"], [0, 0, 0], [0])
        second = TranslationResult(["文", "字"], ["⠃", "⠀", "⠉"], [0, 0, 1], [0, 2])

        merged = merge_translation_results([first, second])
        merged.reclean_braille_endspace()
        for name in FIELDS:
            getattr(merged, name).append("changed")

        self.assertEqual(
            [lists_of(first), lists_of(second)],
            [(["中"], ["⠁", "⠂", "⠀"], [0, 0, 0], [0]), (["文", "字"], ["⠃", "⠀", "⠉"], [0, 0, 1], [0, 2])],
        )

    def test_merging_three_results_offsets_every_position(self) -> None:
        results = [
            TranslationResult(["a"], ["⠁"], [0], [0]),
            TranslationResult(["b", "c"], ["⠃", "⠉", "⠀"], [0, 1, 1], [0, 1]),
            TranslationResult(["d"], ["⠙", "⠀"], [0, 0], [0]),
        ]

        merged = merge_translation_results(results)

        self.assertEqual(
            lists_of(merged),
            (
                ["a", "b", "c", "d"],
                ["⠁", "⠃", "⠉", "⠀", "⠙", "⠀"],
                [0, 1, 2, 2, 3, 3],
                [0, 1, 2, 4],
            ),
        )

    def test_merging_a_non_result_raises_type_error(self) -> None:
        results = [TranslationResult(["a"], ["⠁"], [0], [0]), object()]

        with self.assertRaisesRegex(TypeError, "^not TranslateResult object$"):
            merge_translation_results(results)


class LinearMergeTest(unittest.TestCase):
    def results(self, count: int, tokens: int) -> list[TranslationResult]:
        return [
            TranslationResult(
                [f"t{index * tokens + offset}" for offset in range(tokens)],
                ["⠁", "⠀"] * tokens,
                [offset for offset in range(tokens) for _cell in range(2)],
                [2 * offset for offset in range(tokens)],
            )
            for index in range(count)
        ]

    def test_merge_builds_exactly_one_result(self) -> None:
        results = self.results(500, 1)
        original_init = TranslationResult.__init__
        constructed = []

        def counting_init(result, *args, **kwargs):
            constructed.append(result)
            original_init(result, *args, **kwargs)

        with patch.object(TranslationResult, "__init__", counting_init):
            merged = merge_translation_results(results)

        self.assertEqual(len(constructed), 1)
        self.assertIs(constructed[0], merged)
        self.assertEqual(len(merged.raw), 500)

    def test_merge_never_adds_pairwise(self) -> None:
        results = self.results(500, 1)

        with patch.object(TranslationResult, "__add__", side_effect=AssertionError("pairwise merge")) as add:
            merged = merge_translation_results(results)

        add.assert_not_called()
        self.assertEqual(len(merged.raw), 500)

    def test_merging_twenty_thousand_results_takes_linear_time(self) -> None:
        results = self.results(20_000, 10)
        total = 20_000 * 10

        started = time.perf_counter()
        merged = merge_translation_results(results)
        elapsed = time.perf_counter() - started

        self.assertEqual(
            lists_of(merged),
            (
                [f"t{index}" for index in range(total)],
                ["⠁", "⠀"] * total,
                [index for index in range(total) for _cell in range(2)],
                [2 * index for index in range(total)],
            ),
        )
        self.assertLess(elapsed, 5.0)

if __name__ == "__main__":
    unittest.main()
