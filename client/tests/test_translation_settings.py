import json
import tempfile
import unittest
from pathlib import Path

import config
from settings.translation import (
    DEFAULT_TRANSLATION_SETTINGS,
    TranslationSettings,
    load_translation_settings,
    save_translation_settings,
)


class TranslationSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config_path = config.CONFIG_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")

    def tearDown(self) -> None:
        config.CONFIG_PATH = self._original_config_path
        self._tmpdir.cleanup()

    def _write_config(self, conversion: dict[str, object]) -> None:
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"conversion": conversion}, f)

    def test_load_normalizes_invalid_config(self) -> None:
        self._write_config(
            {
                config.OUTPUT_MODE_KEY: "invalid",
                config.WIDTH_KEY: 999,
                config.SELECTED_DICTIONARY_KEY: "missing",
            }
        )

        settings = load_translation_settings(["default", "math"])

        self.assertEqual(
            settings,
            TranslationSettings(
                output_mode=DEFAULT_TRANSLATION_SETTINGS.output_mode,
                width=200,
                selected_dictionary="default",
            ),
        )

    def test_load_keeps_valid_config(self) -> None:
        self._write_config(
            {
                config.OUTPUT_MODE_KEY: "ascii",
                config.WIDTH_KEY: 52,
                config.SELECTED_DICTIONARY_KEY: "math",
            }
        )

        self.assertEqual(
            load_translation_settings(["default", "math"]),
            TranslationSettings("ascii", 52, "math"),
        )

    def test_save_persists_one_complete_settings_value(self) -> None:
        settings = TranslationSettings("ascii", 64, "math")

        save_translation_settings(settings)

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            self.assertEqual(
                json.load(f),
                {
                    "conversion": {
                        config.OUTPUT_MODE_KEY: "ascii",
                        config.WIDTH_KEY: 64,
                        config.SELECTED_DICTIONARY_KEY: "math",
                    }
                },
            )


if __name__ == "__main__":
    unittest.main()
