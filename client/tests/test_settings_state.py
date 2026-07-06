import unittest

from settings.state import DotExpressSettingsSnapshot
from settings.translation import TranslationSettings
from settings.view import ViewSettings


class SettingsSnapshotTest(unittest.TestCase):
    def test_create_copies_translation_table_mapping(self) -> None:
        source_tables = {"default": "zh-tw.ctb", "math": "UEB"}
        snapshot = DotExpressSettingsSnapshot.create(
            TranslationSettings("unicode", 40, "default"),
            source_tables,
            ViewSettings(12, "light", "simbraille"),
        )

        source_tables["default"] = "en-ueb-g1.ctb"

        self.assertEqual(snapshot.translation_tables["default"], "zh-tw.ctb")
