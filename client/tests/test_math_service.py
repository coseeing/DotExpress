import unittest
from unittest.mock import patch

from conversion.math_service import (
    MathConversionError,
    latex_to_mathml,
    translate_math_segment,
)


class MathServiceTest(unittest.TestCase):
    def test_latex_to_mathml_normalizes_vec_output(self) -> None:
        with patch("conversion.math_service._convert_latex_to_mathml", return_value="<math><mi>⇀</mi></math>"):
            self.assertEqual(
                latex_to_mathml(r"\vec{x}"),
                "<math><mo>⇀</mo></math>",
            )

    def test_translate_math_segment_calls_mathml_and_mathcat_in_order(self) -> None:
        with patch("conversion.math_service.latex_to_mathml", return_value="<math><mi>x</mi></math>") as latex_mock:
            with patch("conversion.math_service.mathml_to_nemeth_braille", return_value="⠭") as braille_mock:
                self.assertEqual(translate_math_segment("x", braille_code="UEB"), "⠭")
        latex_mock.assert_called_once_with("x")
        braille_mock.assert_called_once_with("<math><mi>x</mi></math>", braille_code="UEB")

    def test_translate_math_segment_raises_math_conversion_error_for_latex_failure(self) -> None:
        with patch("conversion.math_service.latex_to_mathml", side_effect=ValueError("bad latex")):
            with self.assertRaisesRegex(MathConversionError, "bad latex"):
                translate_math_segment(r"\bad")

    def test_translate_math_segment_logs_latex_and_mathml_on_braille_failure(self) -> None:
        with patch("conversion.math_service.latex_to_mathml", return_value="<math><mfrac/></math>"):
            with patch("conversion.math_service.mathml_to_nemeth_braille", side_effect=ValueError("braille boom")):
                with patch("conversion.math_service.logger") as logger_mock:
                    with self.assertRaisesRegex(MathConversionError, "braille boom"):
                        translate_math_segment(r"\frac{2}{3}")

        logger_mock.exception.assert_called_once()
        args = logger_mock.exception.call_args[0]
        self.assertIn(r"\frac{2}{3}", args)
        self.assertIn("<math><mfrac/></math>", args)
        self.assertIn("mathml_to_nemeth_braille", args)


if __name__ == "__main__":
    unittest.main()
