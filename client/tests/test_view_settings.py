import tempfile
import unittest
from pathlib import Path

import config
from settings.view import (
    ViewSettings,
    load_view_settings,
    normalize_view_settings,
    save_view_settings,
)


class ViewSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_path = config.CONFIG_PATH
        self.temp_dir = tempfile.TemporaryDirectory()
        config.CONFIG_PATH = str(Path(self.temp_dir.name) / "config.json")

    def tearDown(self) -> None:
        config.CONFIG_PATH = self.original_path
        self.temp_dir.cleanup()

    def test_normalize_clamps_font_and_replaces_unknown_choices(self) -> None:
        self.assertEqual(
            normalize_view_settings(ViewSettings(999, "unknown", "unknown")),
            ViewSettings(48, "light", "simbraille"),
        )

    def test_save_and_load_round_trip_as_one_value(self) -> None:
        expected = ViewSettings(18, "dark", "default")
        save_view_settings(expected)
        self.assertEqual(load_view_settings(), expected)


if __name__ == "__main__":
    unittest.main()
