import importlib.util
import unittest

from conversion.text import char_maps, dictionary_rules, pipeline
from languageDetection import LanguageDetector
from ui import action_menu, import_dialog


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

    def test_dead_ui_helpers_are_removed(self) -> None:
        for name in (
            "build_actions_button_label",
            "get_actions_menu_position",
            "get_dictionary_action_labels",
            "get_document_action_labels",
            "get_document_export_format_keys",
            "get_document_export_format_labels",
            "get_document_menu_items",
        ):
            with self.subTest(name=f"ui.action_menu.{name}"):
                self.assertFalse(hasattr(action_menu, name))
        for name in (
            "get_default_import_filter_index",
            "get_import_filter_labels",
            "get_import_wildcard_text",
        ):
            with self.subTest(name=f"ui.import_dialog.{name}"):
                self.assertFalse(hasattr(import_dialog, name))
        for module, name in (
            (action_menu, "get_document_menu_descriptors"),
            (action_menu, "get_document_menu_enabled_state"),
            (import_dialog, "get_import_filters"),
            (import_dialog, "build_import_wildcard"),
            (import_dialog, "ALL_SUPPORTED_FILTER_INDEX"),
        ):
            with self.subTest(live=f"{module.__name__}.{name}"):
                self.assertTrue(hasattr(module, name))


if __name__ == "__main__":
    unittest.main()
