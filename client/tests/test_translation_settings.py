import unittest
from unittest.mock import patch

from settings.translation import (
    DEFAULT_TRANSLATION_SETTINGS,
    TranslationSettings,
    load_translation_settings,
    save_translation_settings,
)


class TranslationSettingsTest(unittest.TestCase):
    @patch("settings.translation.get_selected_dictionary", return_value="missing")
    @patch("settings.translation.get_conversion_width", return_value=999)
    @patch("settings.translation.get_output_mode", return_value="invalid")
    def test_load_normalizes_invalid_config(
        self,
        _get_output_mode,
        _get_conversion_width,
        _get_selected_dictionary,
    ) -> None:
        settings = load_translation_settings(["default", "math"])

        self.assertEqual(
            settings,
            TranslationSettings(
                output_mode=DEFAULT_TRANSLATION_SETTINGS.output_mode,
                width=200,
                selected_dictionary="default",
            ),
        )

    @patch("settings.translation.get_selected_dictionary", return_value="math")
    @patch("settings.translation.get_conversion_width", return_value=52)
    @patch("settings.translation.get_output_mode", return_value="ascii")
    def test_load_keeps_valid_config(
        self,
        _get_output_mode,
        _get_conversion_width,
        _get_selected_dictionary,
    ) -> None:
        self.assertEqual(
            load_translation_settings(["default", "math"]),
            TranslationSettings("ascii", 52, "math"),
        )

    @patch("settings.translation.set_selected_dictionary")
    @patch("settings.translation.set_conversion_width")
    @patch("settings.translation.set_output_mode")
    def test_save_persists_one_complete_settings_value(
        self,
        set_output_mode,
        set_conversion_width,
        set_selected_dictionary,
    ) -> None:
        settings = TranslationSettings("ascii", 64, "math")

        save_translation_settings(settings)

        set_output_mode.assert_called_once_with("ascii")
        set_conversion_width.assert_called_once_with(64)
        set_selected_dictionary.assert_called_once_with("math")


if __name__ == "__main__":
    unittest.main()
