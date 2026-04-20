import os
from typing import Iterable, Sequence, Tuple

import louisHelper
from languageDetection import LangChangeCommand, LanguageDetector

from translate import translate, TranslationResult


def _merge_sequence(sequence: Iterable[object]) -> TranslationResult:
	translations = [
		translate("zh-tw.ctb", item)
		for item in sequence
		if isinstance(item, str)
	]
	assert translations, "No translatable text segments were found."
	merged = translations[0]
	for segment in translations[1:]:
		merged = merged + segment
	return merged


def test_language_detection_translation_consistency() -> None:
	before = [
		"我們 Coseeing 透過開發創新工具，讓視障者看見更多資訊和可能；透過舉辦推廣活動，讓大眾看見障礙者面臨的實際挑戰和需求。希望以多元的形式與持續的行動，讓所有人都能共同看見這精采的世界以及獨特的彼此"
	]
	detector = LanguageDetector(["en", "zh_TW", "ja"])
	after = list(detector.add_detected_language_commands(before))

	before_merged = _merge_sequence(before)
	after_merged = _merge_sequence(after)

	assert before_merged == after_merged
