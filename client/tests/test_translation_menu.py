import unittest

from ui.translation_menu import get_translation_menu_items


class TranslationMenuTest(unittest.TestCase):
    def test_menu_items_match_required_fixed_order(self) -> None:
        self.assertEqual(
            get_translation_menu_items(),
            [
                ("convert", "Convert"),
                ("settings", "Translation Settings..."),
                ("tables", "Translation Tables Setting..."),
                ("dictionaries", "Dictionary Management..."),
            ],
        )


if __name__ == "__main__":
    unittest.main()
