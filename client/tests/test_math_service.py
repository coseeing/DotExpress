import unittest

from conversion.math_service import (
    MathConversionError,
    latex_to_mathml,
    translate_math_segment,
)


class MathServiceTest(unittest.TestCase):
    def test_latex_to_mathml_normalizes_vec_output(self) -> None:
        self.assertIn("<mo>⇀</mo>", latex_to_mathml(r"\vec{x}"))

    def test_latex_to_mathml_normalizes_embedded_newlines_before_conversion(self) -> None:
        mathml = latex_to_mathml("\\left\\{\n\\begin{aligned}\na&=b\\\\\nc&=d\n\\end{aligned}\n\\right.")
        self.assertIn("<mi>a</mi><mi>&amp;</mi><mo>=</mo><mi>b</mi>", mathml)
        self.assertIn("<mi>c</mi><mi>&amp;</mi><mo>=</mo><mi>d</mi>", mathml)

    def test_latex_to_mathml_escapes_bare_ampersands(self) -> None:
        self.assertIn("<mi>a</mi><mi>&amp;</mi><mi>b</mi>", latex_to_mathml("a&b"))

    def test_translate_math_segment_raises_math_conversion_error_for_latex_failure(self) -> None:
        with self.assertRaises(MathConversionError):
            translate_math_segment(r"\frac{2}{")


if __name__ == "__main__":
    unittest.main()
