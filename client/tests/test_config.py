import json
import tempfile
import unittest
import gettext
from pathlib import Path
from uuid import UUID

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
            "math": "UEB",
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

    def test_translation_tables_default_includes_math_table(self) -> None:
        tables = config.get_translation_tables()

        self.assertEqual(tables["math"], "UEB")

    def test_selected_dictionary_roundtrip_under_conversion_section(self) -> None:
        config.set_selected_dictionary("math")

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "conversion": {
                    "selected_dictionary": "math",
                }
            },
        )
        self.assertEqual(config.get_selected_dictionary("default"), "math")

    def test_braille_font_setting_is_persisted_under_view_section(self) -> None:
        config.set_braille_font("simbraille")

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "view": {
                    "braille_font": "simbraille",
                }
            },
        )
        self.assertEqual(config.get_braille_font("default"), "simbraille")

    def test_braille_font_defaults_to_simbraille_when_config_is_missing(self) -> None:
        self.assertEqual(config.get_braille_font(), "simbraille")

    def test_client_id_is_generated_and_persisted_under_client_section(self) -> None:
        client_id = config.get_or_create_client_id()

        UUID(client_id)
        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data, {"client": {"id": client_id}})
        self.assertEqual(config.get_or_create_client_id(), client_id)

    def test_existing_client_id_is_reused(self) -> None:
        expected_client_id = "existing-client-id"
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"client": {"id": expected_client_id}}, f)

        self.assertEqual(config.get_or_create_client_id(), expected_client_id)

    def test_client_id_generation_preserves_unrelated_config_values(self) -> None:
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"view": {"font_size": 18}}, f)

        client_id = config.get_or_create_client_id()

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["view"], {"font_size": 18})
        self.assertEqual(data["client"], {"id": client_id})

    def test_zh_tw_catalog_keeps_runtime_wildcard_translations_active(self) -> None:
        with open(
            Path(__file__).resolve().parents[1]
            / "locales"
            / "zh_TW"
            / "LC_MESSAGES"
            / "dotexpress.mo",
            "rb",
        ) as mo_file:
            translation = gettext.GNUTranslations(mo_file)

        self.assertEqual(
            translation.gettext("CSV files (*.csv)|*.csv"),
            "CSV 檔案 (*.csv)|*.csv",
        )
        self.assertEqual(
            translation.gettext("DotExpress files (*.dep)|*.dep"),
            "DotExpress 檔案 (*.dep)|*.dep",
        )
        self.assertEqual(
            translation.gettext("Text files (*.txt)|*.txt"),
            "文字檔 (*.txt)|*.txt",
        )
        self.assertEqual(
            translation.gettext("PDF files (*.pdf)|*.pdf"),
            "PDF 檔案 (*.pdf)|*.pdf",
        )
        self.assertEqual(
            translation.gettext("Word documents (*.docx)|*.docx"),
            "Word 文件 (*.docx)|*.docx",
        )
        self.assertEqual(
            translation.gettext("EPUB books (*.epub)|*.epub"),
            "EPUB 電子書 (*.epub)|*.epub",
        )
        self.assertEqual(
            translation.gettext("Braille files (*.brl)|*.brl"),
            "點字檔 (*.brl)|*.brl",
        )
        self.assertEqual(
            translation.gettext("All Supported Files"),
            "所有支援的檔案",
        )

    def test_zh_tw_catalog_keeps_dictionary_entry_type_translations_active(self) -> None:
        with open(
            Path(__file__).resolve().parents[1]
            / "locales"
            / "zh_TW"
            / "LC_MESSAGES"
            / "dotexpress.mo",
            "rb",
        ) as mo_file:
            translation = gettext.GNUTranslations(mo_file)

        self.assertEqual(translation.gettext("General"), "一般")
        self.assertEqual(translation.gettext("Bopomofo"), "注音")
        self.assertEqual(translation.gettext("Unicode Braille"), "Unicode 點字")


if __name__ == "__main__":
    unittest.main()
