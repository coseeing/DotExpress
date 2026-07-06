import unittest
from unittest.mock import patch


class TranslationTablesTest(unittest.TestCase):
    @patch("settings.translation_tables.config.get_translation_tables")
    def test_load_translation_tables_returns_copy(self, get_translation_tables) -> None:
        stored_tables = {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb"}
        get_translation_tables.return_value = stored_tables

        from settings.translation_tables import load_translation_tables

        loaded_tables = load_translation_tables()

        self.assertEqual(loaded_tables, stored_tables)
        self.assertIsNot(loaded_tables, stored_tables)

        loaded_tables["en"] = "changed"

        self.assertEqual(stored_tables["en"], "en-ueb-g1.ctb")

    @patch("settings.translation_tables.config.set_translation_tables")
    def test_save_translation_tables_passes_copy(self, set_translation_tables) -> None:
        tables = {"default": "zh-tw.ctb", "math": "UEB"}

        from settings.translation_tables import save_translation_tables

        save_translation_tables(tables)
        tables["math"] = "Nemeth"

        set_translation_tables.assert_called_once()
        passed_tables = set_translation_tables.call_args.args[0]
        self.assertEqual(passed_tables, {"default": "zh-tw.ctb", "math": "UEB"})
        self.assertIsNot(passed_tables, tables)


if __name__ == "__main__":
    unittest.main()
