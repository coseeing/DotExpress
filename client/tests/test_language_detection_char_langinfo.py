import unittest
from unittest.mock import patch

from languageDetection import LangChangeCommand, LanguageDetector
from languageDetection import SINGLETONS


class CharacterLanguageInfoTest(unittest.TestCase):
    def test_mongolian_uses_base_language_code(self):
        self.assertEqual(SINGLETONS["Mongolian"], "mn")

    def test_character_language_map_forces_language_and_preserves_character(self):
        detector = LanguageDetector(
            ["en", "zh_TW", "ja_JP"],
            char_langinfo={"￥": "ja_JP"},
        )

        with patch("languageDetection.config.get_lang", return_value="en"):
            sequence = list(detector.add_detected_language_commands(["a￥b中"]))

        self.assertEqual(
            [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence],
            ["a", "ja_JP", "￥", "en", "b", "zh_TW", "中"],
        )

    def test_leading_braille_uses_language_of_first_detectable_text(self):
        detector = LanguageDetector(["en", "zh_TW"])

        with patch("languageDetection.config.get_lang", return_value="en"):
            sequence = list(detector.add_detected_language_commands(["⠁⠃中"]))

        self.assertEqual(
            [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence],
            ["zh_TW", "⠁⠃", "中"],
        )

    def test_leading_non_detecting_text_without_detectable_followup_keeps_current_language(self):
        detector = LanguageDetector(["en", "zh_TW"])

        with patch("languageDetection.config.get_lang", return_value="en"):
            sequence = list(detector.add_detected_language_commands(["⠁⠃ "]))

        self.assertEqual(sequence, ["⠁⠃ "])

    def test_charset_map_is_loaded_from_config(self):
        detector = LanguageDetector(["en", "zh_TW", "ja_JP"])

        with patch("languageDetection.config.get_lang", return_value="en"), patch(
            "languageDetection.config.get_charset_maps",
            return_value={
                "latinCharactersLanguage": "en",
                "CJKCharactersLanguage": "ja",
                "arabicCharactersLanguage": "ar",
            },
        ):
            sequence = list(detector.add_detected_language_commands(["A中"]))

        self.assertEqual(
            [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence],
            ["A", "ja_JP", "中"],
        )


if __name__ == "__main__":
    unittest.main()
