import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import config
from settings.view import (
    ViewSettings,
    load_view_settings,
    normalize_view_settings,
    save_view_settings,
)


class ViewSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = config.ConfigStore(Path(self.temp_dir.name) / "config.json")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_returns_what_the_store_returns(self) -> None:
        # F-12 (D6): the save problem, or None.
        store = Mock(spec=config.ConfigStore)
        problem = object()
        store.set_view_settings.return_value = problem

        self.assertIs(save_view_settings(store, ViewSettings(18, "dark", "default")), problem)
        self.assertIsNone(save_view_settings(self.store, ViewSettings(18, "dark", "default")))

    def test_normalize_clamps_font_and_replaces_unknown_choices(self) -> None:
        self.assertEqual(
            normalize_view_settings(ViewSettings(999, "unknown", "unknown")),
            ViewSettings(48, "light", "simbraille"),
        )

    def test_save_and_load_round_trip_as_one_value(self) -> None:
        expected = ViewSettings(18, "dark", "default")
        save_view_settings(self.store, expected)
        self.assertEqual(load_view_settings(self.store), expected)


class ViewSettingsNormalizeTest(unittest.TestCase):
    """P2-3 characterization: what normalization keeps and replaces."""

    def test_every_scheme_and_braille_font_is_kept(self) -> None:
        for scheme in ("light", "dark"):
            for braille_font in ("default", "simbraille"):
                with self.subTest(scheme=scheme, braille_font=braille_font):
                    self.assertEqual(
                        normalize_view_settings(ViewSettings(12, scheme, braille_font)),
                        ViewSettings(12, scheme, braille_font),
                    )

    def test_unknown_values_become_the_config_defaults(self) -> None:
        self.assertEqual((config.DEFAULT_VIEW_SCHEME, config.DEFAULT_BRAILLE_FONT), ("light", "simbraille"))
        for scheme, braille_font in (("Dark", "Default"), ("sepia", "serif"), ("", "")):
            with self.subTest(scheme=scheme, braille_font=braille_font):
                self.assertEqual(
                    normalize_view_settings(ViewSettings(12, scheme, braille_font)),
                    ViewSettings(12, "light", "simbraille"),
                )
        self.assertEqual(
            normalize_view_settings(ViewSettings(12, "dark", "unknown")),
            ViewSettings(12, "dark", "simbraille"),
        )

    def test_font_size_is_clamped_at_both_ends(self) -> None:
        for font_size, expected in ((-1, 8), (7, 8), (8, 8), (12, 12), (48, 48), (49, 48)):
            with self.subTest(font_size=font_size):
                self.assertEqual(
                    normalize_view_settings(ViewSettings(font_size, "light", "default")).font_size,
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
