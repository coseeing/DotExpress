import json
import tempfile
import unittest
from pathlib import Path

import config


class ConfigSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config_path = config.CONFIG_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")

    def tearDown(self) -> None:
        config.CONFIG_PATH = self._original_config_path
        self._tmpdir.cleanup()

    def test_view_settings_are_persisted_under_view_section(self) -> None:
        config.set_view_font_size(18)
        config.set_view_scheme("dark")

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "view": {
                    "font_size": 18,
                    "scheme": "dark",
                }
            },
        )
        self.assertEqual(config.get_view_font_size(), 18)
        self.assertEqual(config.get_view_scheme(), "dark")

    def test_conversion_settings_roundtrip_under_conversion_section(self) -> None:
        tables = {
            "default": "zh-tw.ctb",
            "en": "en-ueb-g1.ctb",
            "zh": "zh-tw.ctb",
            "ja": "ja-rokutenkanji.utb",
        }

        config.set_translation_tables(tables)
        config.set_output_mode("ascii")
        config.set_conversion_width(52)

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "conversion": {
                    "translation_tables": tables,
                    "output_mode": "ascii",
                    "width": 52,
                }
            },
        )
        self.assertEqual(config.get_translation_tables(), tables)
        self.assertEqual(config.get_output_mode(), "ascii")
        self.assertEqual(config.get_conversion_width(), 52)


if __name__ == "__main__":
    unittest.main()
