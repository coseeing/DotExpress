import unittest

from config import DEFAULT_CHARSET_MAPS
from languageDetection import LanguageDetector


class UnicodeBrailleLanguageDetectionTest(unittest.TestCase):
    def test_unicode_braille_keeps_current_language(self) -> None:
        detector = LanguageDetector(["en", "zh_TW", "ja"], default_lang="zh_TW", charset_maps=DEFAULT_CHARSET_MAPS)

        sequence = list(detector.add_detected_language_commands(["a⠚⠚b"]))

        self.assertEqual(
            [item for item in sequence if isinstance(item, str)],
            ["a⠚⠚b"],
        )


if __name__ == "__main__":
    unittest.main()
