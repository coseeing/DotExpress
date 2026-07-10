import unittest

from adapters.translation.fallback import FallbackTextTranslator
from dual_view.model import DualViewSegment, build_dual_view_model


class TranslationResult:
	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
		self.raw = raw
		self.braille = braille
		self.braille_to_raw_pos = braille_to_raw_pos
		self.raw_to_braille_pos = raw_to_braille_pos


class DualViewModelTest(unittest.TestCase):
	def result(self, raw, braille, raw_positions):
		return TranslationResult(
			list(raw),
			list(braille),
			[0] * len(braille),
			raw_positions,
		)

	def text_segment(self, raw, braille, raw_positions):
		return DualViewSegment(
			result=self.result(raw, braille, raw_positions),
			source_kind="text",
		)

	def test_builds_one_item_per_raw_element(self):
		model = build_dual_view_model([self.text_segment("ab", "⠁⠃", [0, 1])])

		self.assertEqual([item.raw_text for item in model.segments[0].items], ["a", "b"])
		self.assertEqual([item.braille_text for item in model.segments[0].items], ["⠁", "⠃"])

	def test_preserves_segment_boundaries(self):
		model = build_dual_view_model([
			self.text_segment("a", "⠁", [0]),
			self.text_segment("b", "⠃", [0]),
		])

		self.assertEqual(len(model.segments), 2)
		self.assertEqual([segment.source_text for segment in model.segments], ["a", "b"])

	def test_supports_multiple_and_empty_braille_ranges(self):
		model = build_dual_view_model([self.text_segment("abc", "⠁⠂⠉", [0, 2, 2])])

		items = model.segments[0].items
		self.assertEqual(items[0].braille_text, "⠁⠂")
		self.assertEqual(items[1].braille_text, "")
		self.assertEqual(items[2].braille_text, "⠉")

	def test_keeps_spaces_and_newlines_as_source_items(self):
		model = build_dual_view_model([self.text_segment("a \nb", "⠁⠀⠃", [0, 1, 2, 2])])

		self.assertEqual([item.raw_text for item in model.segments[0].items], ["a", " ", "\n", "b"])
		self.assertTrue(model.segments[0].items[1].is_space)
		self.assertTrue(model.segments[0].items[2].is_newline)

	def test_atomic_token_stays_one_card(self):
		model = build_dual_view_model([
			DualViewSegment(
				result=TranslationResult(["word"], list("⠺⠕⠗⠙"), [0, 0, 0, 0], [0]),
				source_kind="text",
			),
		])

		self.assertEqual(len(model.segments[0].items), 1)
		self.assertEqual(model.segments[0].items[0].raw_text, "word")
		self.assertEqual(model.segments[0].items[0].braille_text, "⠺⠕⠗⠙")

	def test_empty_results_produce_empty_document(self):
		self.assertEqual(build_dual_view_model([]).segments, ())

	def test_multi_character_raw_element_renders_as_one_card(self):
		model = build_dual_view_model([
			DualViewSegment(
				result=TranslationResult(["我們", "這", "一家"], ["b1", "b2", "b3"], [0, 0, 0], [0, 1, 2]),
				source_kind="text",
			),
		])

		self.assertEqual(len(model.segments[0].items), 3)
		self.assertEqual([item.raw_text for item in model.segments[0].items], ["我們", "這", "一家"])
		self.assertEqual([item.braille_text for item in model.segments[0].items], ["b1", "b2", "b3"])

	def test_single_space_is_space_card(self):
		model = build_dual_view_model([self.text_segment(" ", "⠀", [0])])

		self.assertEqual(len(model.segments[0].items), 1)
		item = model.segments[0].items[0]
		self.assertEqual(item.raw_text, " ")
		self.assertTrue(item.is_space)

	def test_single_newline_is_break(self):
		model = build_dual_view_model([self.text_segment("\n", "", [0])])

		self.assertEqual(len(model.segments[0].items), 1)
		item = model.segments[0].items[0]
		self.assertEqual(item.raw_text, "\n")
		self.assertTrue(item.is_newline)

	def test_multi_char_with_embedded_space_stays_one_card(self):
		model = build_dual_view_model([
			DualViewSegment(
				result=TranslationResult(["我們 這 一家"], list("b1"), [0, 0], [0]),
				source_kind="text",
			),
		])

		self.assertEqual(len(model.segments[0].items), 1)
		self.assertEqual(model.segments[0].items[0].raw_text, "我們 這 一家")
		self.assertFalse(model.segments[0].items[0].is_space)

	def test_invalid_range_still_raises_value_error(self):
		dangling = self.text_segment("xy", "⠁⠃", [0, 99])

		with self.assertRaises(ValueError):
			build_dual_view_model([dangling])

	def test_unknown_source_kind_raises_value_error(self):
		segment = DualViewSegment(
			result=self.result("a", "⠁", [0]),
			source_kind="unknown",
		)

		with self.assertRaisesRegex(ValueError, "source_kind"):
			build_dual_view_model([segment])

	def test_fallback_character_mapping_builds_dual_view_segments(self) -> None:
		result = FallbackTextTranslator().translate(
			"ignored",
			table="zh-tw.ctb",
			raw="我 們",
		)

		model = build_dual_view_model([
			DualViewSegment(result=result, source_kind="text"),
		])

		self.assertEqual(
			[
				(item.raw_text, item.braille_text)
				for item in model.segments[0].items
			],
			[("我", "⣿"), (" ", "⠀"), ("們", "⣿")],
		)


if __name__ == "__main__":
	unittest.main()
