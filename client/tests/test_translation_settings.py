import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import config
from settings.translation import (
    DEFAULT_TRANSLATION_SETTINGS,
    TranslationSettings,
    load_translation_settings,
    normalize_translation_settings,
    save_translation_settings,
)


class TranslationSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.store = config.ConfigStore(Path(self._tmpdir.name) / "config.json")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _write_config(self, conversion: dict[str, object]) -> None:
        with open(self.store.path, "w", encoding="utf-8") as f:
            json.dump({"conversion": conversion}, f)

    def test_save_calls_every_setter_and_returns_the_first_problem(self) -> None:
        # F-12 (D6): the frame shows the first problem; a failed setter does not stop the others.
        store = Mock(spec=config.ConfigStore)
        first, second = object(), object()
        store.set_output_mode.return_value = None
        store.set_conversion_width.return_value = first
        store.set_selected_dictionary.return_value = second
        store.set_selected_script.return_value = None

        problem = save_translation_settings(store, TranslationSettings("ascii", 52, "alpha", "upper"))

        self.assertIs(problem, first)
        store.set_output_mode.assert_called_once_with("ascii")
        store.set_conversion_width.assert_called_once_with(52)
        store.set_selected_dictionary.assert_called_once_with("alpha")
        store.set_selected_script.assert_called_once_with("upper")

    def test_save_returns_the_script_problem_when_it_is_the_only_one(self) -> None:
        # F-18 (D3): the fourth setting is saved and reported like the others.
        store = Mock(spec=config.ConfigStore)
        problem = object()
        store.set_output_mode.return_value = None
        store.set_conversion_width.return_value = None
        store.set_selected_dictionary.return_value = None
        store.set_selected_script.return_value = problem

        self.assertIs(save_translation_settings(store, TranslationSettings("ascii", 52, "alpha")), problem)
        store.set_selected_script.assert_called_once_with("no-processing")

    def test_save_returns_none_when_every_setter_saves(self) -> None:
        self.assertIsNone(save_translation_settings(self.store, TranslationSettings("ascii", 52, "alpha")))

    def test_load_normalizes_invalid_config(self) -> None:
        self._write_config(
            {
                config.OUTPUT_MODE_KEY: "invalid",
                config.WIDTH_KEY: 999,
                config.SELECTED_DICTIONARY_KEY: "missing",
                config.SELECTED_SCRIPT_KEY: "gone",
            }
        )

        settings = load_translation_settings(self.store, ["default", "math"], ["no-processing", "upper"])

        self.assertEqual(
            settings,
            TranslationSettings(
                output_mode=DEFAULT_TRANSLATION_SETTINGS.output_mode,
                width=200,
                selected_dictionary="default",
                selected_script="no-processing",
            ),
        )

    def test_load_keeps_valid_config(self) -> None:
        self._write_config(
            {
                config.OUTPUT_MODE_KEY: "ascii",
                config.WIDTH_KEY: 52,
                config.SELECTED_DICTIONARY_KEY: "math",
                config.SELECTED_SCRIPT_KEY: "upper",
            }
        )

        self.assertEqual(
            load_translation_settings(self.store, ["default", "math"], ["no-processing", "upper"]),
            TranslationSettings("ascii", 52, "math", "upper"),
        )

    def test_a_config_without_a_script_selects_no_processing(self) -> None:
        # F-18 (D-A): every user starts with No Processing.
        self._write_config({config.SELECTED_DICTIONARY_KEY: "math"})

        self.assertEqual(
            load_translation_settings(self.store, ["default", "math"], ["no-processing", "upper"]).selected_script,
            "no-processing",
        )
        self.assertEqual(DEFAULT_TRANSLATION_SETTINGS.selected_script, "no-processing")
        self.assertEqual(TranslationSettings("unicode", 40, "default").selected_script, "no-processing")

    def test_save_persists_one_complete_settings_value(self) -> None:
        settings = TranslationSettings("ascii", 64, "math", "upper")

        save_translation_settings(self.store, settings)

        with open(self.store.path, "r", encoding="utf-8") as f:
            self.assertEqual(
                json.load(f),
                {
                    "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                    "conversion": {
                        config.OUTPUT_MODE_KEY: "ascii",
                        config.WIDTH_KEY: 64,
                        config.SELECTED_DICTIONARY_KEY: "math",
                        config.SELECTED_SCRIPT_KEY: "upper",
                    },
                },
            )


class TranslationSettingsNormalizeTest(unittest.TestCase):
    """P2-3 characterization: what normalization keeps and replaces."""

    def normalize(self, output_mode="unicode", width=40):
        return normalize_translation_settings(
            TranslationSettings(output_mode, width, "default"),
            ["default"],
            ["no-processing"],
        )

    def test_every_output_mode_is_kept_and_unknown_modes_become_the_default(self) -> None:
        for output_mode in ("unicode", "ascii"):
            with self.subTest(output_mode=output_mode):
                self.assertEqual(self.normalize(output_mode).output_mode, output_mode)
        self.assertEqual(config.DEFAULT_OUTPUT_MODE, "unicode")
        for output_mode in ("", "UNICODE", "braille", "default"):
            with self.subTest(output_mode=output_mode):
                self.assertEqual(self.normalize(output_mode).output_mode, "unicode")

    def test_a_script_that_is_not_listed_becomes_no_processing(self) -> None:
        # F-18 (D3): a script deleted or renamed outside the app.
        for script, expected in (("upper", "upper"), ("gone", "no-processing"), ("Upper", "no-processing")):
            with self.subTest(script=script):
                settings = normalize_translation_settings(
                    TranslationSettings("unicode", 40, "default", script),
                    ["default"],
                    ["no-processing", "upper"],
                )
                self.assertEqual(settings.selected_script, expected)

    def test_width_is_clamped_at_both_ends(self) -> None:
        for width, expected in ((-5, 10), (9, 10), (10, 10), (40, 40), (200, 200), (201, 200)):
            with self.subTest(width=width):
                self.assertEqual(self.normalize(width=width).width, expected)


if __name__ == "__main__":
    unittest.main()
