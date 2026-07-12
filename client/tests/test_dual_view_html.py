import unittest
from unittest.mock import Mock

from dual_view.html import render_dual_view_html
from dual_view.model import DualViewSegment, build_dual_view_model


class TranslationResult:
	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
		self.raw = raw
		self.braille = braille
		self.braille_to_raw_pos = braille_to_raw_pos
		self.raw_to_braille_pos = raw_to_braille_pos


class DualViewHtmlTest(unittest.TestCase):
	def render(self, raw, braille, positions, *, source_kind="text"):
		result = TranslationResult(list(raw), list(braille), [0] * len(braille), positions)
		return render_dual_view_html(build_dual_view_model([
			DualViewSegment(result=result, source_kind=source_kind),
		]))

	def test_renders_source_text_from_raw_text(self):
		output = self.render("a", "⠁", [0])

		self.assertIn('<span class="source">a</span>', output)
		self.assertIn('<span class="braille">⠁</span>', output)

	def test_embedded_source_text_is_escaped_for_text_items(self):
		output = self.render("<", "⠣", [0])

		self.assertIn("&lt;", output)
		self.assertNotIn('<span class="source"><</span>', output)

	def test_escapes_metadata(self):
		output = self.render("<", "⠣", [0])

		self.assertIn("&lt;", output)
		self.assertIn("&quot;raw_index&quot;", output)

	def test_omits_non_newline_whitespace_but_keeps_newline_break(self):
		output = self.render([" ", "  ", "\t", "\n"], "⠀⠀⠀", [0, 1, 2, 3])

		self.assertNotIn('class="cell space"', output)
		self.assertIn('class="line-break"', output)

	def test_math_item_renders_mathml_in_source_area(self):
		fake_mathml = "<math><mi>x</mi></math>"
		result = TranslationResult(list("x"), list("⠭"), [0], [0])
		output = render_dual_view_html(build_dual_view_model(
			[DualViewSegment(result=result, source_kind="math")],
			mathml_converter=lambda _: fake_mathml,
		))

		self.assertIn(fake_mathml, output)

	def test_generated_mathml_is_not_escaped_as_visible_text(self):
		fake_mathml = "<math><mi>x</mi></math>"
		result = TranslationResult(list("x"), list("⠭"), [0], [0])
		output = render_dual_view_html(build_dual_view_model(
			[DualViewSegment(result=result, source_kind="math")],
			mathml_converter=lambda _: fake_mathml,
		))

		self.assertIn(fake_mathml, output)
		self.assertNotIn("&lt;math", output)

	def test_flattens_result_items_without_segment_sections(self):
		first = TranslationResult(["a", "  ", "\n"], ["⠁", "⠀", "⠀"], [0, 0, 0], [0, 1, 2])
		second = TranslationResult(["b"], ["⠃"], [0], [0])
		output = render_dual_view_html(build_dual_view_model([
			DualViewSegment(result=first, source_kind="text"),
			DualViewSegment(result=second, source_kind="text"),
		]))

		self.assertNotIn('<section class="segment">', output)
		self.assertEqual(output.count('class="cell"'), 2)
		self.assertLess(output.index('<span class="source">a</span>'), output.index('<span class="source">b</span>'))
		self.assertIn('class="line-break"', output)

	def test_aria_label_is_absent(self):
		output = self.render("a", "⠁", [0])

		self.assertNotIn("aria-label", output)

	def test_role_region_is_absent(self):
		output = self.render("a", "⠁", [0])

		self.assertNotIn('role="region"', output)

	def test_renders_empty_state(self):
		output = render_dual_view_html(
			build_dual_view_model([]),
			empty_message="此文件沒有可顯示的轉換資料。",
		)

		self.assertIn("此文件沒有可顯示的轉換資料。", output)


if __name__ == "__main__":
	unittest.main()
