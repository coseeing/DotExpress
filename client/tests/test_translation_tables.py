import json
import tempfile
import unittest
from pathlib import Path

import config
from settings.translation_tables import load_translation_tables, save_translation_tables


class TranslationTablesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config_path = config.CONFIG_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")

    def tearDown(self) -> None:
        config.CONFIG_PATH = self._original_config_path
        self._tmpdir.cleanup()

    def test_load_translation_tables_returns_copy(self) -> None:
        stored_tables = {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb"}
        config.set_translation_tables(stored_tables)

        loaded_tables = load_translation_tables()

        self.assertEqual(loaded_tables["default"], "zh-tw.ctb")
        self.assertEqual(loaded_tables["en"], "en-ueb-g1.ctb")
        self.assertEqual(loaded_tables["math"], "UEB")
        self.assertIsNot(loaded_tables, stored_tables)

        loaded_tables["en"] = "changed"

        self.assertEqual(stored_tables["en"], "en-ueb-g1.ctb")
        self.assertEqual(config.get_translation_tables()["en"], "en-ueb-g1.ctb")

    def test_save_translation_tables_passes_copy(self) -> None:
        tables = {"default": "zh-tw.ctb", "math": "UEB"}

        save_translation_tables(tables)
        tables["math"] = "Nemeth"

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(
            data["conversion"]["translation_tables"],
            {"default": "zh-tw.ctb", "math": "UEB"},
        )


if __name__ == "__main__":
    unittest.main()
