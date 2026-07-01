import unittest

from dual_view.model import build_dual_view_model


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

	def test_builds_one_item_per_source_character(self):
		model = build_dual_view_model([self.result("ab", "⠁⠃", [0, 1])])

		self.assertEqual([item.raw_char for item in model.segments[0].items], ["a", "b"])
		self.assertEqual([item.braille_text for item in model.segments[0].items], ["⠁", "⠃"])

	def test_preserves_segment_boundaries(self):
		model = build_dual_view_model([
			self.result("a", "⠁", [0]),
			self.result("b", "⠃", [0]),
		])

		self.assertEqual(len(model.segments), 2)
		self.assertEqual([segment.source_text for segment in model.segments], ["a", "b"])

	def test_supports_multiple_and_empty_braille_ranges(self):
		model = build_dual_view_model([self.result("abc", "⠁⠂⠉", [0, 2, 2])])

		items = model.segments[0].items
		self.assertEqual(items[0].braille_text, "⠁⠂")
		self.assertEqual(items[1].braille_text, "")
		self.assertEqual(items[2].braille_text, "⠉")

	def test_keeps_spaces_and_newlines_as_source_items(self):
		model = build_dual_view_model([self.result("a \nb", "⠁⠀⠃", [0, 1, 2, 2])])

		self.assertEqual([item.raw_char for item in model.segments[0].items], ["a", " ", "\n", "b"])
		self.assertTrue(model.segments[0].items[1].is_space)
		self.assertTrue(model.segments[0].items[2].is_newline)

	def test_expands_an_atomic_multi_character_token_into_character_items(self):
		atomic = TranslationResult(["word"], list("⠺⠕⠗⠙"), [0, 0, 0, 0], [0])

		model = build_dual_view_model([atomic])

		self.assertEqual([item.raw_char for item in model.segments[0].items], list("word"))
		self.assertEqual(
			[item.braille_text for item in model.segments[0].items],
			["⠺⠕⠗⠙", "", "", ""],
		)

	def test_empty_results_produce_empty_document(self):
		self.assertEqual(build_dual_view_model([]).segments, ())


if __name__ == "__main__":
	unittest.main()
