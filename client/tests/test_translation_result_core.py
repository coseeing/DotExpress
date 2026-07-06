import importlib
import sys
import unittest


class TranslationResultCoreTest(unittest.TestCase):
    def test_import_does_not_import_liblouis_helper(self) -> None:
        sys.modules.pop("translate", None)
        sys.modules.pop("braille.louis_helper", None)
        sys.modules.pop("braille.liblouis", None)

        module = importlib.import_module("translate")

        self.assertNotIn("braille.louis_helper", sys.modules)
        self.assertNotIn("braille.liblouis", sys.modules)
        self.assertTrue(hasattr(module, "TranslationResult"))
        self.assertFalse(hasattr(module, "translate"))
        self.assertFalse(hasattr(module, "translate_as_single_token"))

    def test_addition_offsets_both_position_arrays(self) -> None:
        from translate import TranslationResult

        left = TranslationResult(["a"], ["⠁"], [0], [0])
        right = TranslationResult(["b"], ["⠃"], [0], [0])

        result = left + right

        self.assertEqual(result.raw, ["a", "b"])
        self.assertEqual(result.braille, ["⠁", "⠃"])
        self.assertEqual(result.braille_to_raw_pos, [0, 1])
        self.assertEqual(result.raw_to_braille_pos, [0, 1])

    def test_empty_result_has_empty_mapping(self) -> None:
        from translate import TranslationResult

        result = TranslationResult([], [], [], [])

        self.assertEqual(result.raw, [])
        self.assertEqual(result.braille, [])
        self.assertEqual(result.braille_to_raw_pos, [])
        self.assertEqual(result.raw_to_braille_pos, [])


if __name__ == "__main__":
    unittest.main()
