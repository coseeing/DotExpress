import unittest

from config import DEFAULT_CHARSET_MAPS
from languageDetection import LangChangeCommand, LanguageDetector
from languageDetection import SINGLETONS


def _flatten(sequence):
    return [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence]


class CharacterLanguageInfoTest(unittest.TestCase):
    def test_mongolian_uses_base_language_code(self):
        self.assertEqual(SINGLETONS["Mongolian"], "mn")

    def test_character_language_map_forces_language_and_preserves_character(self):
        detector = LanguageDetector(
            ["en", "zh_TW", "ja_JP"],
            default_lang="en",
            charset_maps=DEFAULT_CHARSET_MAPS,
            char_langinfo={"￥": "ja_JP"},
        )

        sequence = list(detector.add_detected_language_commands(["a￥b中"]))

        self.assertEqual(
            [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence],
            ["a", "ja_JP", "￥", "en", "b", "zh_TW", "中"],
        )

    def test_leading_braille_uses_language_of_first_detectable_text(self):
        detector = LanguageDetector(["en", "zh_TW"], default_lang="en", charset_maps=DEFAULT_CHARSET_MAPS)

        sequence = list(detector.add_detected_language_commands(["⠁⠃中"]))

        self.assertEqual(
            [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence],
            ["zh_TW", "⠁⠃", "中"],
        )

    def test_leading_non_detecting_text_without_detectable_followup_keeps_current_language(self):
        detector = LanguageDetector(["en", "zh_TW"], default_lang="en", charset_maps=DEFAULT_CHARSET_MAPS)

        sequence = list(detector.add_detected_language_commands(["⠁⠃ "]))

        self.assertEqual(sequence, ["⠁⠃ "])

    def test_charset_map_comes_from_constructor(self):
        detector = LanguageDetector(
            ["en", "zh_TW", "ja_JP"],
            default_lang="en",
            charset_maps={
                "latinCharactersLanguage": "en",
                "CJKCharactersLanguage": "ja",
                "arabicCharactersLanguage": "ar",
            },
        )

        sequence = list(detector.add_detected_language_commands(["A中"]))

        self.assertEqual(
            [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence],
            ["A", "ja_JP", "中"],
        )

    def test_preferred_full_language_comes_from_current_language(self):
        detector = LanguageDetector(["en", "zh"], default_lang="zh_HK", charset_maps=DEFAULT_CHARSET_MAPS)

        sequence = list(detector.add_detected_language_commands([LangChangeCommand("en"), "中"]))

        self.assertEqual(_flatten(sequence), ["en", "zh_HK", "中"])

    def test_current_language_decides_leading_language_command(self):
        for lang, expected in (
            ("en", ["Hello ", "zh", "中文 "]),
            ("zh_TW", ["en", "Hello ", "zh_TW", "中文 "]),
        ):
            with self.subTest(lang=lang):
                detector = LanguageDetector(["en", "zh", "ja"], default_lang=lang, charset_maps=DEFAULT_CHARSET_MAPS)

                sequence = list(detector.add_detected_language_commands(["Hello 中文 "]))

                self.assertEqual(_flatten(sequence), expected)

    def test_empty_charset_map_value_is_used_as_is(self):
        detector = LanguageDetector(
            ["en", "zh_TW"],
            default_lang="en",
            charset_maps={
                "latinCharactersLanguage": "en",
                "CJKCharactersLanguage": "",
                "arabicCharactersLanguage": "ar",
            },
        )

        sequence = list(detector.add_detected_language_commands(["A中"]))

        self.assertEqual(_flatten(sequence), ["A", "", "中"])

    def test_missing_charset_map_entry_falls_back_to_first_block_language(self):
        detector = LanguageDetector(["en", "zh_TW"], default_lang="zh_TW", charset_maps={})

        sequence = list(detector.add_detected_language_commands(["中A"]))

        self.assertEqual(_flatten(sequence), ["中", "en", "A"])

    def test_detector_keeps_its_own_copy_of_charset_maps(self):
        charset_maps = dict(DEFAULT_CHARSET_MAPS)
        detector = LanguageDetector(["en", "zh_TW"], default_lang="en", charset_maps=charset_maps)

        charset_maps["CJKCharactersLanguage"] = "ja"

        self.assertEqual(detector.charset_maps, DEFAULT_CHARSET_MAPS)
        self.assertIsNot(detector.charset_maps, charset_maps)

    def test_language_and_charset_maps_are_required(self):
        with self.assertRaises(TypeError):
            LanguageDetector(["en"])


if __name__ == "__main__":
    unittest.main()
