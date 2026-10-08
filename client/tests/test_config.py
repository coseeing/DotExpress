import json
import logging
import os
import tempfile
import unittest
import gettext
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import config


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config_path = config.CONFIG_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")

    def tearDown(self) -> None:
        config.CONFIG_PATH = self._original_config_path
        self._tmpdir.cleanup()

    def test_view_settings_are_persisted_under_view_section(self) -> None:
        config.set_view_settings(18, "dark", "simbraille")

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                "view": {
                    "font_size": 18,
                    "scheme": "dark",
                    "braille_font": "simbraille",
                }
            },
        )
        self.assertEqual(config.get_view_font_size(), 18)
        self.assertEqual(config.get_view_scheme(), "dark")
        self.assertEqual(config.get_braille_font("default"), "simbraille")

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
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
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

    def test_new_config_file_contains_language_detection_defaults(self) -> None:
        config.set_output_mode("unicode")

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data["language_detection"]["charset_maps"],
            config.DEFAULT_CHARSET_MAPS,
        )

    def test_charset_maps_read_from_config_with_defaults_for_missing_values(self) -> None:
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "language_detection": {
                        "charset_maps": {"arabicCharactersLanguage": "fa"}
                    }
                },
                f,
            )

        charset_maps = config.get_charset_maps()

        self.assertEqual(charset_maps["arabicCharactersLanguage"], "fa")
        self.assertEqual(charset_maps["CJKCharactersLanguage"], "zh")

    def test_selected_dictionary_roundtrip_under_conversion_section(self) -> None:
        config.set_selected_dictionary("math")

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                "conversion": {
                    "selected_dictionary": "math",
                }
            },
        )
        self.assertEqual(config.get_selected_dictionary("default"), "math")

    def test_view_settings_write_braille_font_and_keep_other_sections(self) -> None:
        with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "conversion": {"width": 52},
                    "view": {"font_size": 20, "custom": "kept"},
                },
                f,
            )

        config.set_view_settings(14, "light", "default")

        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "conversion": {"width": 52},
                "view": {
                    "font_size": 14,
                    "custom": "kept",
                    "scheme": "light",
                    "braille_font": "default",
                },
            },
        )
        self.assertEqual(config.get_braille_font(), "default")

    def test_unused_single_view_setters_are_removed(self) -> None:
        for name in ("set_view_font_size", "set_view_scheme", "set_braille_font"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(config, name))

    def test_braille_font_defaults_to_simbraille_when_config_is_missing(self) -> None:
        self.assertEqual(config.get_braille_font(), "simbraille")

    def test_client_id_is_generated_and_persisted_under_client_section(self) -> None:
        client_id = config.get_or_create_client_id()

        UUID(client_id)
        with open(config.CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                "client": {"id": client_id},
            },
        )
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

    def test_zh_tw_catalog_contains_application_data_and_dual_view_errors(self) -> None:
        with open(
            Path(__file__).resolve().parents[1]
            / "locales"
            / "zh_TW"
            / "LC_MESSAGES"
            / "dotexpress.mo",
            "rb",
        ) as mo_file:
            translation = gettext.GNUTranslations(mo_file)

        self.assertEqual(translation.gettext("Startup Error"), "啟動錯誤")
        self.assertEqual(
            translation.gettext(
                "DotExpress cannot write to its application data directory:\n"
                "{path}\n\nChoose a writable installation or execution location.\n\n{error}"
            ),
            "DotExpress 無法寫入應用程式資料目錄：\n"
            "{path}\n\n請選擇可寫入的安裝或執行位置。\n\n{error}",
        )
        self.assertEqual(
            translation.gettext("Failed to open dual view: {error}"),
            "無法開啟雙視檢視：{error}",
        )


class ConfigSaveFailureLoggingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config_path = config.CONFIG_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        self._blocker = Path(self._tmpdir.name) / "blocker"
        self._blocker.write_text("not a directory", encoding="utf-8")
        config.CONFIG_PATH = str(self._blocker / "nested" / "config.json")

    def tearDown(self) -> None:
        config.CONFIG_PATH = self._original_config_path
        self._tmpdir.cleanup()

    def test_save_failure_is_logged_and_not_raised(self) -> None:
        with self.assertLogs("dotexpress.config", level="ERROR") as captured:
            config.set_output_mode("ascii")

        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.levelno, logging.ERROR)
        self.assertIsNotNone(record.exc_info)
        self.assertIn(config.CONFIG_PATH, record.getMessage())
        self.assertFalse(Path(config.CONFIG_PATH).exists())
        self.assertTrue(self._blocker.is_file())

    def test_every_save_failure_is_logged(self) -> None:
        with self.assertLogs("dotexpress.config", level="ERROR") as captured:
            config.set_output_mode("ascii")
            config.set_conversion_width(52)

        self.assertEqual(len(captured.records), 2)

    def test_save_failure_log_does_not_contain_config_data(self) -> None:
        with self.assertLogs("dotexpress.config", level="ERROR") as captured:
            client_id = config.get_or_create_client_id()

        UUID(client_id)
        self.assertNotIn(client_id, "\n".join(captured.output))

    def test_save_failure_does_not_raise_when_log_file_cannot_be_opened(self) -> None:
        missing_log = Path(self._tmpdir.name) / "missing-log-dir" / "config.log"
        handler = logging.FileHandler(missing_log, encoding="utf-8", delay=True)
        unopenable = logging.Logger("dotexpress.config.unopenable")
        unopenable.addHandler(handler)

        try:
            with patch.object(config, "logger", unopenable):
                config.set_output_mode("ascii")
        finally:
            handler.close()

        self.assertFalse(missing_log.parent.exists())
        self.assertFalse(Path(config.CONFIG_PATH).exists())


class ConfigLoadFailureLoggingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config_path = config.CONFIG_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        config.CONFIG_PATH = str(Path(self._tmpdir.name) / "config.json")
        config._logged_load_failures.clear()

    def tearDown(self) -> None:
        config.CONFIG_PATH = self._original_config_path
        config._logged_load_failures.clear()
        self._tmpdir.cleanup()

    def _write_raw(self, content: bytes) -> None:
        with open(config.CONFIG_PATH, "wb") as f:
            f.write(content)

    def _warnings(self, captured) -> list[logging.LogRecord]:
        return [r for r in captured.records if r.levelno == logging.WARNING]

    def test_corrupt_file_is_logged_once_and_defaults_are_returned(self) -> None:
        self._write_raw(b"{not json")

        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            output_mode = config.get_output_mode()
            width = config.get_conversion_width()

        self.assertEqual(output_mode, config.DEFAULT_OUTPUT_MODE)
        self.assertEqual(width, config.DEFAULT_CONVERSION_WIDTH)
        warnings = self._warnings(captured)
        self.assertEqual(len(warnings), 1)
        self.assertIn(config.CONFIG_PATH, warnings[0].getMessage())
        self.assertIn("using defaults", warnings[0].getMessage())
        self.assertIsNotNone(warnings[0].exc_info)

    def test_warning_is_emitted_again_after_recovery(self) -> None:
        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            self._write_raw(b"{not json")
            config.get_output_mode()
            self._write_raw(b'{"conversion": {"output_mode": "ascii"}}')
            self.assertEqual(config.get_output_mode(), "ascii")
            self._write_raw(b"{not json")
            config.get_output_mode()

        self.assertEqual(len(self._warnings(captured)), 2)

    def test_different_failure_on_same_path_is_logged_again(self) -> None:
        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            self._write_raw(b"{not json")
            config.get_output_mode()
            self._write_raw(b"\xff\xfe\x00")
            config.get_output_mode()

        self.assertEqual(len(self._warnings(captured)), 2)

    def test_corrupt_files_at_different_paths_are_each_logged(self) -> None:
        other_path = str(Path(self._tmpdir.name) / "other.json")
        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            self._write_raw(b"{not json")
            config.get_output_mode()
            config.CONFIG_PATH = other_path
            self._write_raw(b"{not json")
            config.get_output_mode()

        self.assertEqual(len(self._warnings(captured)), 2)

    def test_missing_file_is_not_logged(self) -> None:
        with patch.object(config, "logger") as logger:
            self.assertEqual(config.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
            self.assertEqual(config.get_charset_maps(), config.DEFAULT_CHARSET_MAPS)

        self.assertEqual(logger.mock_calls, [])

    def test_load_failure_does_not_raise_when_log_file_cannot_be_opened(self) -> None:
        self._write_raw(b"{not json")
        missing_log = Path(self._tmpdir.name) / "missing-log-dir" / "config.log"
        handler = logging.FileHandler(missing_log, encoding="utf-8", delay=True)
        unopenable = logging.Logger("dotexpress.config.unopenable")
        unopenable.addHandler(handler)

        try:
            with patch.object(config, "logger", unopenable):
                self.assertEqual(config.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
        finally:
            handler.close()

        self.assertFalse(missing_log.parent.exists())


class _ConfigFunctionsAtPath:
    """The module-level config functions, each run with ``config.CONFIG_PATH`` set to one path."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def __getattr__(self, name: str):
        function = getattr(config, name)

        def call(*args, **kwargs):
            with patch.object(config, "CONFIG_PATH", str(self.path)):
                return function(*args, **kwargs)

        return call


def make_store(path: Path):
    """The config API bound to ``path``.

    P2-6: the module-level functions today, ``config.ConfigStore`` from step 2 on.
    """
    return _ConfigFunctionsAtPath(path)


class ConfigLanguageOverrideCharacterizationTest(unittest.TestCase):
    """P2-6 characterization: where ``get_lang`` finds the language, and what ``set_lang`` writes."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.path = Path(temp_dir.name) / "config.json"
        self.store = make_store(self.path)
        self.addCleanup(setattr, config, "_runtime_lang", config._runtime_lang)
        config._runtime_lang = None
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop(config.LANG_ENV, None)

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_language_comes_from_the_environment_then_the_file_then_the_fallback(self) -> None:
        self.assertEqual(self.store.get_lang(), "zh_TW")
        self.path.write_text(json.dumps({"language": "en"}), encoding="utf-8")
        self.assertEqual(self.store.get_lang(), "en")
        os.environ[config.LANG_ENV] = "ko"
        self.assertEqual(self.store.get_lang(), "ko")

    def test_runtime_override_wins_without_writing_the_file(self) -> None:
        self.path.write_text(json.dumps({"language": "en"}), encoding="utf-8")
        os.environ[config.LANG_ENV] = "ko"

        self.store.set_lang("ja")

        self.assertEqual(self.store.get_lang(), "ja")
        self.assertEqual(config._runtime_lang, "ja")
        self.assertEqual(self.read(), {"language": "en"})

    def test_persisted_override_writes_the_top_level_language_with_first_save_defaults(self) -> None:
        self.store.set_lang("en", persist=True)

        self.assertEqual(
            self.read(),
            {
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                "language": "en",
            },
        )
        config._runtime_lang = None
        self.assertEqual(self.store.get_lang(), "en")


if __name__ == "__main__":
    unittest.main()
