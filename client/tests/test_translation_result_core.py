import subprocess
import sys
import unittest

from translate import TranslationResult


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


if __name__ == "__main__":
    unittest.main()
