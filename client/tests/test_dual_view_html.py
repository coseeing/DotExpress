import unittest

from dual_view.html import render_dual_view_html
from dual_view.model import DualViewSegment, build_dual_view_model


class TranslationResult:
	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
		self.raw = raw
		self.braille = braille
		self.braille_to_raw_pos = braille_to_raw_pos
		self.raw_to_braille_pos = raw_to_braille_pos


class DualViewHtmlTest(unittest.TestCase):
	def render(self, raw, braille, positions):
		result = TranslationResult(list(raw), list(braille), [0] * len(braille), positions)
		return render_dual_view_html(build_dual_view_model([
			DualViewSegment(result=result, source_kind="text"),
		]))

	def test_renders_source_above_braille(self):
		output = self.render("a", "⠁", [0])

		self.assertIn('<span class="source">a</span>', output)
		self.assertIn('<span class="braille">⠁</span>', output)

	def test_escapes_source_and_metadata(self):
		output = self.render("<", "⠣", [0])

		self.assertIn("&lt;", output)
		self.assertIn("&quot;raw_index&quot;", output)
		self.assertNotIn('<span class="source"><</span>', output)

	def test_renders_space_and_newline_semantics(self):
		output = self.render(" \n", "⠀", [0, 1])

		self.assertIn('class="cell space"', output)
		self.assertIn('class="line-break"', output)

	def test_renders_empty_state(self):
		output = render_dual_view_html(
			build_dual_view_model([]),
			empty_message="此文件沒有可顯示的轉換資料。",
			segment_label="轉譯區段",
		)

		self.assertIn("此文件沒有可顯示的轉換資料。", output)

	def test_renders_localized_segment_label(self):
		result = TranslationResult(list("a"), list("⠁"), [0], [0])
		output = render_dual_view_html(
			build_dual_view_model([DualViewSegment(result=result, source_kind="text")]),
			empty_message="此文件沒有可顯示的轉換資料。",
			segment_label="轉譯區段",
		)

		self.assertIn('aria-label="轉譯區段"', output)


if __name__ == "__main__":
	unittest.main()
