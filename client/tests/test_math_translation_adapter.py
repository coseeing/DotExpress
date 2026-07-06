import unittest
from unittest.mock import Mock

from adapters.translation.mathcat import MathCATMathTranslator


class MathCATMathTranslatorTest(unittest.TestCase):
    def test_returns_current_single_token_mapping(self) -> None:
        translate_math = Mock(return_value="⠼⠁⠬⠃")
        adapter = MathCATMathTranslator(translate_math=translate_math)

        result = adapter.translate("1+2", braille_code="Nemeth")

        translate_math.assert_called_once_with("1+2", braille_code="Nemeth")
        self.assertEqual(result.raw, ["1+2"])
        self.assertEqual(result.braille, list("⠼⠁⠬⠃"))
        self.assertEqual(result.raw_to_braille_pos, [0])
        self.assertEqual(result.braille_to_raw_pos, [0, 0, 0, 0])

    def test_empty_math_has_empty_mapping(self) -> None:
        adapter = MathCATMathTranslator(translate_math=Mock(return_value=""))

        result = adapter.translate("", braille_code="UEB")

        self.assertEqual(result.raw, [])
        self.assertEqual(result.braille, [])
        self.assertEqual(result.raw_to_braille_pos, [])
        self.assertEqual(result.braille_to_raw_pos, [])


if __name__ == "__main__":
    unittest.main()
