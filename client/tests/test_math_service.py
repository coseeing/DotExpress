import unittest
from unittest.mock import Mock

from conversion.math_service import (
    MathConversionError,
    latex_to_mathml,
    mathml_to_nemeth_braille,
    translate_math_segment,
)
from tests.file_log_isolation import isolate_file_logs


def setUpModule() -> None:
    unittest.addModuleCleanup(isolate_file_logs("dotexpress.math"))


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
            translate_math_segment(r"\frac{2}{", language="zh_TW", mathcat=Mock())

    def test_translate_math_segment_forwards_language_to_mathcat(self) -> None:
        adapter = Mock()
        adapter.get_braille_for_mathml.return_value = "\u283c\u2801"

        braille = translate_math_segment("1", braille_code="Nemeth", language="en", mathcat=adapter)

        self.assertEqual(braille, "\u283c\u2801")
        adapter.get_braille_for_mathml.assert_called_once_with(
            latex_to_mathml("1"),
            braille_code="Nemeth",
            language="en",
        )

    def test_mathml_to_nemeth_braille_uses_the_given_adapter(self) -> None:
        adapter = Mock()
        adapter.get_braille_for_mathml.return_value = "\u283c\u2803"

        braille = mathml_to_nemeth_braille("<math/>", braille_code="UEB", language="zh_TW", mathcat=adapter)

        self.assertEqual(braille, "\u283c\u2803")
        adapter.get_braille_for_mathml.assert_called_once_with(
            "<math/>",
            braille_code="UEB",
            language="zh_TW",
        )


if __name__ == "__main__":
    unittest.main()
