import unittest

from conversion.text import char_maps, dictionary_rules, pipeline


class RemovedDeadCodeTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
