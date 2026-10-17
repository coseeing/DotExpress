"""F-16: dictionary rows with combining tone marks match after a language switch."""
import csv
import ctypes
import tempfile
import unittest
from pathlib import Path


if not hasattr(ctypes, "WINFUNCTYPE"):
	raise unittest.SkipTest("liblouis bindings require WINFUNCTYPE on this platform")

# Probe through the helper: it adds the bundled DLL's directory first. A bare
# braille.liblouis import loads System32's older liblouis.dll on Windows 11 (W-1).
try:
	from braille import louis_helper  # noqa: F401
except Exception as exc:
	raise unittest.SkipTest(f"liblouis bindings unavailable: {exc}") from exc

from adapters.translation.provider import build_default_translation_runtime
from config import DEFAULT_CHARSET_MAPS, DEFAULT_TRANSLATION_TABLES
from conversion.service import ConversionRequest, convert_text_with_alignment


CLIENT_DIR = Path(__file__).resolve().parents[1]
# Taiwanese romanization rows: "a\u030d" is "a" + U+030D COMBINING VERTICAL LINE ABOVE.
ROWS = (
	("pa\u030dh", "\u280f\u2801\u2814"),
	("pa\u030dp", "\u280f\u2829\u2814"),
	("Po\u030dh", "\u280f\u2815\u2814"),
)
# What liblouis writes for a lone U+030D ("\x030d").
LONE_MARK_BRAILLE = "\u2804\u2873\u282d\u2834\u2812\u2834\u2819\u2804"


class CombiningMarkDictionaryConversionTest(unittest.TestCase):
	def setUp(self) -> None:
		tmpdir = tempfile.TemporaryDirectory()
		self.addCleanup(tmpdir.cleanup)
		self.dictionary_path = Path(tmpdir.name) / "default.csv"
		with self.dictionary_path.open("w", newline="", encoding="utf-8") as f:
			writer = csv.writer(f)
			writer.writerow(["text", "braille", "type"])
			for text, braille in ROWS:
				writer.writerow([text, braille, "Braille"])
		self.runtime = build_default_translation_runtime()
		self.addCleanup(self.runtime.close)

	def _convert(self, text: str) -> list[str]:
		output = convert_text_with_alignment(
			ConversionRequest(
				raw_text=text,
				output_mode="unicode",
				width=40,
				dictionary_path=self.dictionary_path,
				data_dir=CLIENT_DIR / "data",
				translation_tables={**DEFAULT_TRANSLATION_TABLES, "en": "en-ueb-g2.ctb"},
				lang="zh_TW",
				charset_maps=dict(DEFAULT_CHARSET_MAPS),
			),
			runtime=self.runtime,
		)
		# Each display line is padded with blank cells (U+2800) to the width.
		return [line.rstrip("\u2800") for line in output.display_text.split("\n")]

	def test_rows_match_without_a_previous_language_switch(self) -> None:
		lines = self._convert("\n".join(text for text, _ in ROWS))

		self.assertEqual(lines[:3], [braille for _, braille in ROWS])
		self.assertNotIn(LONE_MARK_BRAILLE, "".join(lines))

	def test_rows_match_after_chinese_text(self) -> None:
		lines = self._convert("\u767d\n" + "\n".join(text for text, _ in ROWS))

		self.assertEqual(lines[1:4], [braille for _, braille in ROWS])
		self.assertNotIn(LONE_MARK_BRAILLE, "".join(lines))


if __name__ == "__main__":
	unittest.main()
