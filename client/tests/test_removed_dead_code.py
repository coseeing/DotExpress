import importlib.util
import unittest

from conversion.text import char_maps, dictionary_rules, pipeline
from languageDetection import LanguageDetector


class RemovedDeadCodeTest(unittest.TestCase):
    def test_dictionary_import_flow_module_is_removed(self) -> None:
        self.assertIsNone(importlib.util.find_spec("dictionaries.import_flow"))
        self.assertIsNotNone(importlib.util.find_spec("dictionaries.name_prompt"))

    def test_dead_conversion_text_helpers_are_removed(self) -> None:
        for module, name in (
            (dictionary_rules, "translate__mapping_string"),
            (char_maps, "preprocess_bopomofo_characters"),
            (char_maps, "map_braille_to_ascii"),
            (pipeline, "apply_plain_text_rules"),
        ):
            with self.subTest(name=f"{module.__name__}.{name}"):
                self.assertFalse(hasattr(module, name))
        self.assertTrue(hasattr(char_maps, "translate__mapping_char"))
        self.assertTrue(hasattr(dictionary_rules, "apply_dictionary"))

    def test_dead_language_detection_method_is_removed(self) -> None:
        self.assertFalse(hasattr(LanguageDetector, "process_for_spelling"))
        self.assertTrue(hasattr(LanguageDetector, "add_detected_language_commands"))
        self.assertTrue(hasattr(LanguageDetector, "find_language_for_charset"))


if __name__ == "__main__":
    unittest.main()
