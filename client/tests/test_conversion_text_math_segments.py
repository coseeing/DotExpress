import unittest

from conversion.text.math_segments import parse_inline_math_segments, segment_needs_boundary_space


class ConversionTextMathSegmentsTest(unittest.TestCase):
    def test_parse_inline_math_segments_splits_multiple_math_ranges(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("計算$1+2$和$3+4$"),
            [
                {"type": "text", "text": "計算"},
                {"type": "math", "text": "1+2"},
                {"type": "text", "text": "和"},
                {"type": "math", "text": "3+4"},
            ],
        )

    def test_parse_inline_math_segments_keeps_escaped_dollar_inside_math(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("$1+\\$2$"),
            [{"type": "math", "text": "1+\\$2"}],
        )

    def test_parse_inline_math_segments_treats_unmatched_opening_dollar_as_text(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("計算$1+2"),
            [{"type": "text", "text": "計算$1+2"}],
        )

    def test_parse_inline_math_segments_keeps_escaped_dollar_outside_math(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("價格\\$100"),
            [{"type": "text", "text": "價格\\$100"}],
        )

    def test_segment_needs_boundary_space_requires_spacing_between_text_and_math(self) -> None:
        self.assertTrue(
            segment_needs_boundary_space(
                {"type": "text", "text": "計算"},
                {"type": "math", "text": "1+2"},
            )
        )

    def test_segment_needs_boundary_space_skips_spacing_when_text_already_has_whitespace(self) -> None:
        self.assertFalse(
            segment_needs_boundary_space(
                {"type": "text", "text": "計算 "},
                {"type": "math", "text": "1+2"},
            )
        )

    def test_segment_needs_boundary_space_skips_spacing_between_plain_text_segments(self) -> None:
        self.assertFalse(
            segment_needs_boundary_space(
                {"type": "text", "text": "計算"},
                {"type": "text", "text": "的值"},
            )
        )


if __name__ == "__main__":
    unittest.main()

