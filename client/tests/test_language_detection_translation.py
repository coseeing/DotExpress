import ctypes
import unittest
from typing import Iterable

if not hasattr(ctypes, "WINFUNCTYPE"):
	raise unittest.SkipTest("liblouis bindings require WINFUNCTYPE on this platform")

try:
	from braille import liblouis  # noqa: F401
except Exception as exc:
	raise unittest.SkipTest(f"liblouis bindings unavailable: {exc}") from exc

from adapters.translation.provider import create_default_text_translator
from config import DEFAULT_CHARSET_MAPS
from languageDetection import LanguageDetector
from translate import TranslationResult


TABLE = "zh-tw.ctb"
TEXT = "我們 Coseeing 透過開發創新工具，讓視障者看見更多資訊和可能；透過舉辦推廣活動，讓大眾看見障礙者面臨的實際挑戰和需求。希望以多元的形式與持續的行動，讓所有人都能共同看見這精采的世界以及獨特的彼此"


class LanguageDetectionTranslationTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		# The production text-translation factory (liblouis via louis_helper).
		cls.translator = create_default_text_translator()

	@classmethod
	def tearDownClass(cls) -> None:
		cls.translator.close()

	def _merge_sequence(self, sequence: Iterable[object]) -> TranslationResult:
		translations = [
			self.translator.translate(item, table=TABLE, raw=item)
			for item in sequence
			if isinstance(item, str)
		]
		self.assertTrue(translations, "No translatable text segments were found.")
		return TranslationResult.concat(translations)

	def test_language_detection_translation_consistency(self) -> None:
		before = [TEXT]
		detector = LanguageDetector(["en", "zh_TW", "ja"], default_lang="zh_TW", charset_maps=DEFAULT_CHARSET_MAPS)
		after = list(detector.add_detected_language_commands(before))

		before_merged = self._merge_sequence(before)
		after_merged = self._merge_sequence(after)

		self.assertEqual(before_merged, after_merged)


if __name__ == "__main__":
	unittest.main()
