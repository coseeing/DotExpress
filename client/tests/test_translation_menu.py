import unittest

from ui.translation_menu import get_translation_menu_items


class TranslationMenuTest(unittest.TestCase):
    def test_items_have_stable_keys_labels_and_order(self) -> None:
        self.assertEqual(
            get_translation_menu_items(),
            [
                ("convert", "Convert"),
                ("dual_view", "Dual View"),
                ("text_processing", "Text Processing"),
                ("dictionaries", "Dictionary Management..."),
                ("settings", "Settings"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
