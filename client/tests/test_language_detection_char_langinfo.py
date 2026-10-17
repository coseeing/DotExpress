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


# Combining marks used by the Taiwanese romanization dictionaries (F-16).
TONE_MARKS = ("\u0300", "\u0302", "\u0304", "\u030b", "\u030c", "\u030d", "\u0358")
# Marks outside U+0300-036F: an enclosing mark (no block) and a Kana-block mark.
OTHER_MARKS = ("\u20dd", "\u3099")


def _code_point(char):
    return f"U+{ord(char):04X}"


class CombiningMarkLanguageTest(unittest.TestCase):
    """F-16: a combining mark stays in the language of the text it follows."""

    def setUp(self):
        self.detector = LanguageDetector(["en", "zh_TW", "ja"], default_lang="zh_TW", charset_maps=DEFAULT_CHARSET_MAPS)

    def _detect(self, text):
        return _flatten(self.detector.add_detected_language_commands([text]))

    def test_romanized_syllables_after_chinese_stay_in_one_latin_piece(self):
        self.assertEqual(
            self._detect("白 pa\u030dh-tsi\u030dt"),
            ["白 ", "en", "pa\u030dh-tsi\u030dt"],
        )

    def test_mark_after_latin_following_chinese_stays_in_the_latin_piece(self):
        for mark in TONE_MARKS + OTHER_MARKS:
            with self.subTest(mark=_code_point(mark)):
                self.assertEqual(self._detect(f"白 a{mark}b中"), ["白 ", "en", f"a{mark}b", "zh_TW", "中"])
                self.assertEqual(self._detect(f"白 a{mark}中"), ["白 ", "en", f"a{mark}", "zh_TW", "中"])

    def test_mark_after_chinese_stays_in_the_chinese_piece(self):
        for mark in TONE_MARKS + OTHER_MARKS:
            with self.subTest(mark=_code_point(mark)):
                self.assertEqual(self._detect(f"a白{mark}中"), ["en", "a", "zh_TW", f"白{mark}中"])
                self.assertEqual(self._detect(f"a白{mark}b"), ["en", "a", "zh_TW", f"白{mark}", "en", "b"])

    def test_leading_mark_does_not_switch_language(self):
        for mark in TONE_MARKS + OTHER_MARKS:
            with self.subTest(mark=_code_point(mark)):
                self.assertEqual(self._detect(f"{mark}白"), [mark, "白"])
                self.assertEqual(self._detect(f"{mark}ab"), ["en", mark, "ab"])

    def test_punctuation_and_format_characters_keep_the_previous_behavior(self):
        # Pinned before F-16: only marks changed; these block-less characters
        # (quotes, dash, ellipsis, zero width space) still follow the old rule.
        for char in ("\u201c", "\u201d", "\u2014", "\u2026", "\u200b"):
            with self.subTest(char=_code_point(char)):
                self.assertEqual(self._detect(f"中{char}ab{char}文"), [f"中{char}", "en", "ab", "zh_TW", f"{char}文"])
                self.assertEqual(self._detect(f"ab{char}中{char}cd"), ["en", f"ab{char}", "zh_TW", "中", "en", f"{char}cd"])
                self.assertEqual(self._detect(f"{char}ab中"), ["en", char, "ab", "zh_TW", "中"])


if __name__ == "__main__":
    unittest.main()
