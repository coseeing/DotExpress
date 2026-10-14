import errno
import json
import logging
import os
import tempfile
import unittest
import gettext
import inspect
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import config
from tests.file_log_isolation import isolate_file_logs
from tests.full_disk import full_disk


def setUpModule() -> None:
    # A test that makes config.py log outside assertLogs must not append to the real
    # log/config.log (F-8); assertLogs still captures the records.
    unittest.addModuleCleanup(isolate_file_logs("dotexpress.config"))


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.store = config.ConfigStore(Path(self._tmpdir.name) / "config.json")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_view_settings_are_persisted_under_view_section(self) -> None:
        self.store.set_view_settings(18, "dark", "simbraille")

        with open(self.store.path, "r", encoding="utf-8") as f:
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
        self.assertEqual(self.store.get_view_font_size(), 18)
        self.assertEqual(self.store.get_view_scheme(), "dark")
        self.assertEqual(self.store.get_braille_font("default"), "simbraille")

    def test_conversion_settings_roundtrip_under_conversion_section(self) -> None:
        tables = {
            "default": "zh-tw.ctb",
            "en": "en-ueb-g1.ctb",
            "zh": "zh-tw.ctb",
            "ja": "ja-rokutenkanji.utb",
            "math": "UEB",
        }

        self.store.set_translation_tables(tables)
        self.store.set_output_mode("ascii")
        self.store.set_conversion_width(52)

        with open(self.store.path, "r", encoding="utf-8") as f:
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
        self.assertEqual(self.store.get_translation_tables(), tables)
        self.assertEqual(self.store.get_output_mode(), "ascii")
        self.assertEqual(self.store.get_conversion_width(), 52)

    def test_translation_tables_default_includes_math_table(self) -> None:
        tables = self.store.get_translation_tables()

        self.assertEqual(tables["math"], "UEB")

    def test_new_config_file_contains_language_detection_defaults(self) -> None:
        self.store.set_output_mode("unicode")

        with open(self.store.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data["language_detection"]["charset_maps"],
            config.DEFAULT_CHARSET_MAPS,
        )

    def test_charset_maps_read_from_config_with_defaults_for_missing_values(self) -> None:
        with open(self.store.path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "language_detection": {
                        "charset_maps": {"arabicCharactersLanguage": "fa"}
                    }
                },
                f,
            )

        charset_maps = self.store.get_charset_maps()

        self.assertEqual(charset_maps["arabicCharactersLanguage"], "fa")
        self.assertEqual(charset_maps["CJKCharactersLanguage"], "zh")

    def test_selected_dictionary_roundtrip_under_conversion_section(self) -> None:
        self.store.set_selected_dictionary("math")

        with open(self.store.path, "r", encoding="utf-8") as f:
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
        self.assertEqual(self.store.get_selected_dictionary("default"), "math")

    def test_view_settings_write_braille_font_and_keep_other_sections(self) -> None:
        with open(self.store.path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "conversion": {"width": 52},
                    "view": {"font_size": 20, "custom": "kept"},
                },
                f,
            )

        self.store.set_view_settings(14, "light", "default")

        with open(self.store.path, "r", encoding="utf-8") as f:
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
        self.assertEqual(self.store.get_braille_font(), "default")

    def test_unused_single_view_setters_are_removed(self) -> None:
        for name in ("set_view_font_size", "set_view_scheme", "set_braille_font"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(config, name))
                self.assertFalse(hasattr(config.ConfigStore, name))

    def test_braille_font_defaults_to_simbraille_when_config_is_missing(self) -> None:
        self.assertEqual(self.store.get_braille_font(), "simbraille")

    def test_client_id_is_generated_and_persisted_under_client_section(self) -> None:
        client_id = self.store.get_or_create_client_id()

        UUID(client_id)
        with open(self.store.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data,
            {
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                "client": {"id": client_id},
            },
        )
        self.assertEqual(self.store.get_or_create_client_id(), client_id)

    def test_existing_client_id_is_reused(self) -> None:
        expected_client_id = "existing-client-id"
        with open(self.store.path, "w", encoding="utf-8") as f:
            json.dump({"client": {"id": expected_client_id}}, f)

        self.assertEqual(self.store.get_or_create_client_id(), expected_client_id)

    def test_client_id_generation_preserves_unrelated_config_values(self) -> None:
        with open(self.store.path, "w", encoding="utf-8") as f:
            json.dump({"view": {"font_size": 18}}, f)

        client_id = self.store.get_or_create_client_id()

        with open(self.store.path, "r", encoding="utf-8") as f:
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
        self._tmpdir = tempfile.TemporaryDirectory()
        self._blocker = Path(self._tmpdir.name) / "blocker"
        self._blocker.write_text("not a directory", encoding="utf-8")
        self.store = config.ConfigStore(self._blocker / "nested" / "config.json")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_save_failure_is_logged_and_not_raised(self) -> None:
        with self.assertLogs("dotexpress.config", level="ERROR") as captured:
            self.store.set_output_mode("ascii")

        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.levelno, logging.ERROR)
        self.assertIsNotNone(record.exc_info)
        self.assertIn(str(self.store.path), record.getMessage())
        self.assertFalse(self.store.path.exists())
        self.assertTrue(self._blocker.is_file())

    def test_every_save_failure_is_logged(self) -> None:
        with self.assertLogs("dotexpress.config", level="ERROR") as captured:
            self.store.set_output_mode("ascii")
            self.store.set_conversion_width(52)

        self.assertEqual(len(captured.records), 2)

    def test_save_failure_log_does_not_contain_config_data(self) -> None:
        with self.assertLogs("dotexpress.config", level="ERROR") as captured:
            client_id = self.store.get_or_create_client_id()

        UUID(client_id)
        self.assertNotIn(client_id, "\n".join(captured.output))

    def test_save_failure_does_not_raise_when_log_file_cannot_be_opened(self) -> None:
        missing_log = Path(self._tmpdir.name) / "missing-log-dir" / "config.log"
        handler = logging.FileHandler(missing_log, encoding="utf-8", delay=True)
        unopenable = logging.Logger("dotexpress.config.unopenable")
        unopenable.addHandler(handler)

        try:
            with patch.object(config, "logger", unopenable):
                self.store.set_output_mode("ascii")
        finally:
            handler.close()

        self.assertFalse(missing_log.parent.exists())
        self.assertFalse(self.store.path.exists())


class ConfigLoadFailureLoggingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.store = config.ConfigStore(Path(self._tmpdir.name) / "config.json")
        config._logged_load_failures.clear()

    def tearDown(self) -> None:
        config._logged_load_failures.clear()
        self._tmpdir.cleanup()

    def _write_raw(self, content: bytes) -> None:
        with open(self.store.path, "wb") as f:
            f.write(content)

    def _warnings(self, captured) -> list[logging.LogRecord]:
        return [r for r in captured.records if r.levelno == logging.WARNING]

    def test_corrupt_file_is_logged_once_and_defaults_are_returned(self) -> None:
        self._write_raw(b"{not json")

        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            output_mode = self.store.get_output_mode()
            width = self.store.get_conversion_width()

        self.assertEqual(output_mode, config.DEFAULT_OUTPUT_MODE)
        self.assertEqual(width, config.DEFAULT_CONVERSION_WIDTH)
        warnings = self._warnings(captured)
        self.assertEqual(len(warnings), 1)
        self.assertIn(str(self.store.path), warnings[0].getMessage())
        self.assertIn("using defaults", warnings[0].getMessage())
        self.assertIsNotNone(warnings[0].exc_info)

    def test_warning_is_emitted_again_after_recovery(self) -> None:
        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            self._write_raw(b"{not json")
            self.store.get_output_mode()
            self._write_raw(b'{"conversion": {"output_mode": "ascii"}}')
            self.assertEqual(self.store.get_output_mode(), "ascii")
            self._write_raw(b"{not json")
            self.store.get_output_mode()

        self.assertEqual(len(self._warnings(captured)), 2)

    def test_different_failure_on_same_path_is_logged_again(self) -> None:
        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            self._write_raw(b"{not json")
            self.store.get_output_mode()
            self._write_raw(b"\xff\xfe\x00")
            self.store.get_output_mode()

        self.assertEqual(len(self._warnings(captured)), 2)

    def test_corrupt_files_at_different_paths_are_each_logged(self) -> None:
        other_path = str(Path(self._tmpdir.name) / "other.json")
        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            self._write_raw(b"{not json")
            self.store.get_output_mode()
            self.store = config.ConfigStore(other_path)
            self._write_raw(b"{not json")
            self.store.get_output_mode()

        self.assertEqual(len(self._warnings(captured)), 2)

    def test_missing_file_is_not_logged(self) -> None:
        with patch.object(config, "logger") as logger:
            self.assertEqual(self.store.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
            self.assertEqual(self.store.get_charset_maps(), config.DEFAULT_CHARSET_MAPS)

        self.assertEqual(logger.mock_calls, [])

    def test_load_failure_does_not_raise_when_log_file_cannot_be_opened(self) -> None:
        self._write_raw(b"{not json")
        missing_log = Path(self._tmpdir.name) / "missing-log-dir" / "config.log"
        handler = logging.FileHandler(missing_log, encoding="utf-8", delay=True)
        unopenable = logging.Logger("dotexpress.config.unopenable")
        unopenable.addHandler(handler)

        try:
            with patch.object(config, "logger", unopenable):
                self.assertEqual(self.store.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
        finally:
            handler.close()

        self.assertFalse(missing_log.parent.exists())


def make_store(path: Path):
    """The config API bound to ``path``.

    P2-6: the module-level functions in step 1, ``config.ConfigStore`` from step 2 on.
    """
    return config.ConfigStore(path)


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


class ConfigStoreTest(unittest.TestCase):
    """P2-6 part B: ``config.ConfigStore`` owns one config file path."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.directory = Path(temp_dir.name)
        config._logged_load_failures.clear()
        self.addCleanup(config._logged_load_failures.clear)

    def test_constructor_does_no_io_and_logs_nothing(self) -> None:
        with patch.object(config, "logger") as logger:
            config.ConfigStore(self.directory / "missing" / "config.json")

        self.assertEqual(logger.mock_calls, [])
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_path_is_a_path_for_str_and_path_input(self) -> None:
        for given in (str(self.directory / "config.json"), self.directory / "config.json"):
            with self.subTest(given=type(given).__name__):
                store = config.ConfigStore(given)

                self.assertIsInstance(store.path, Path)
                self.assertEqual(store.path, Path(given))

    def test_two_stores_on_one_corrupt_file_log_one_warning(self) -> None:
        path = self.directory / "config.json"
        path.write_bytes(b"{not json")

        first = config.ConfigStore(path)
        second = config.ConfigStore(str(path))

        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            first.get_output_mode()
            second.get_conversion_width()

        self.assertEqual(len(captured.records), 1)
        self.assertIn(str(path), captured.records[0].getMessage())

    def test_stores_on_two_corrupt_files_log_one_warning_each(self) -> None:
        paths = [self.directory / "first.json", self.directory / "second.json"]
        for path in paths:
            path.write_bytes(b"{not json")

        stores = [config.ConfigStore(path) for path in paths]

        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            for store in stores:
                store.get_output_mode()
                store.get_output_mode()

        self.assertEqual(len(captured.records), 2)
        for record, path in zip(captured.records, paths):
            self.assertIn(str(path), record.getMessage())

    def _apply_setters(self, target) -> None:
        target.set_output_mode("ascii")
        target.set_conversion_width(52)
        target.set_selected_dictionary("點字")
        target.set_translation_tables({"default": "en-ueb-g1.ctb"})
        target.set_view_settings(18, "dark", "default")
        target.set_lang("en", persist=True)

    def test_store_writes_the_documented_config_bytes(self) -> None:
        self.addCleanup(setattr, config, "_runtime_lang", config._runtime_lang)
        store_path = self.directory / "store" / "config.json"

        self._apply_setters(config.ConfigStore(store_path))

        expected = {
            "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
            "conversion": {
                "output_mode": "ascii",
                "width": 52,
                "selected_dictionary": "點字",
                "translation_tables": {"default": "en-ueb-g1.ctb"},
            },
            "view": {"font_size": 18, "scheme": "dark", "braille_font": "default"},
            "language": "en",
        }
        self.assertEqual(
            store_path.read_text(encoding="utf-8"),
            json.dumps(expected, ensure_ascii=False, indent=2),
        )


GOOD_CONFIG = b'{"view": {"font_size": 20}, "conversion": {"width": 30}}'


class ConfigDataSafetyTest(unittest.TestCase):
    """F-8 (D9-D11): config.json is written atomically and an unusable one is never silently discarded."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.directory = Path(temp_dir.name)
        self.path = self.directory / "config.json"
        self.backup = self.directory / "config.json.bak"
        self.store = config.ConfigStore(self.path)
        config._logged_load_failures.clear()
        self.addCleanup(config._logged_load_failures.clear)
        config._logged_skipped_saves.clear()
        self.addCleanup(config._logged_skipped_saves.clear)

    def _listing(self) -> list[str]:
        return sorted(os.listdir(self.directory))

    def _open_denying_reads(self):
        """``open`` that refuses to read config.json, as if it were locked or denied."""
        real_open = open

        def open_denying_reads(file, mode="r", *args, **kwargs):
            if os.fspath(file) == str(self.path) and "r" in mode:
                raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(file))
            return real_open(file, mode, *args, **kwargs)

        return open_denying_reads

    def _saved(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _backup_bytes(self) -> bytes | None:
        return self.backup.read_bytes() if self.backup.exists() else None

    # --- atomic save (D9) --------------------------------------------------

    def test_save_installs_through_a_synced_temporary_file(self) -> None:
        with patch("os.fsync", wraps=os.fsync) as fsync:
            self.store.set_output_mode("ascii")
            self.store.set_conversion_width(52)

        self.assertEqual(fsync.call_count, 2)
        self.assertEqual(self._listing(), ["config.json"])
        self.assertEqual(self._saved()["conversion"], {"output_mode": "ascii", "width": 52})

    def test_save_failure_keeps_the_previous_file(self) -> None:
        self.path.write_bytes(GOOD_CONFIG)

        with full_disk(self.directory, after=10), self.assertLogs("dotexpress.config", level="ERROR") as captured:
            self.store.set_output_mode("ascii")

        self.assertEqual(self.path.read_bytes(), GOOD_CONFIG)
        self.assertEqual(self._listing(), ["config.json"])
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].getMessage(), f"Failed to save config file {self.path}")

    @unittest.skipUnless(os.name == "nt", "Windows line ends")
    def test_saved_bytes_use_crlf_on_windows(self) -> None:
        self.store.set_view_settings(18, "dark", "default")

        expected = {
            "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
            "view": {"font_size": 18, "scheme": "dark", "braille_font": "default"},
        }
        self.assertEqual(
            self.path.read_bytes(),
            json.dumps(expected, ensure_ascii=False, indent=2).replace("\n", "\r\n").encode("utf-8"),
        )

    # --- load (D10) --------------------------------------------------------

    def test_a_utf8_bom_is_read(self) -> None:
        # Older Notepad writes "UTF-8" with a BOM.
        self.path.write_bytes(b"\xef\xbb\xbf" + GOOD_CONFIG)

        with patch.object(config, "logger") as logger:
            self.assertEqual(self.store.get_view_font_size(), 20)
            self.assertEqual(self.store.get_conversion_width(), 30)

        self.assertEqual(logger.mock_calls, [])

    def test_json_that_is_not_an_object_gives_defaults_and_one_warning(self) -> None:
        # Before, every getter raised AttributeError, and the app did not start.
        for content, type_name in ((b"null", "NoneType"), (b"[1, 2]", "list"), (b'"text"', "str"), (b"3", "int")):
            with self.subTest(content=content):
                self.path.write_bytes(content)

                with self.assertLogs("dotexpress.config", level="WARNING") as captured:
                    self.assertEqual(self.store.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
                    self.assertEqual(self.store.get_view_font_size(), config.DEFAULT_VIEW_FONT_SIZE)

                self.assertEqual(len(captured.records), 1)
                self.assertEqual(captured.records[0].getMessage(), f"Failed to read config file {self.path}; using defaults")
                self.assertEqual(
                    str(captured.records[0].exc_info[1]),
                    f"config.json does not hold a JSON object ({type_name})",
                )

    # --- save after a failed load (D11) ------------------------------------

    def test_a_change_after_a_damaged_load_keeps_a_backup(self) -> None:
        cases = (
            ("truncated JSON", b'{"view": {"font_size": 2'),
            ("cp950 bytes", '{"language": "臺灣"}'.encode("cp950")),
            ("a list", b"[1, 2]"),
        )
        for label, content in cases:
            with self.subTest(label):
                self.path.write_bytes(content)
                self.backup.unlink(missing_ok=True)

                with self.assertLogs("dotexpress.config", level="WARNING"):
                    self.store.set_output_mode("ascii")

                self.assertEqual(self._backup_bytes(), content)
                self.assertEqual(self._saved(), {"conversion": {"output_mode": "ascii"}})
                self.assertEqual(self._listing(), ["config.json", "config.json.bak"])

    def test_a_second_backup_replaces_the_first(self) -> None:
        for content in (b"{first", b"[second"):
            self.path.write_bytes(content)
            with self.assertLogs("dotexpress.config", level="WARNING"):
                self.store.set_output_mode("ascii")

        self.assertEqual(self._backup_bytes(), b"[second")
        self.assertEqual(self._listing(), ["config.json", "config.json.bak"])

    def test_a_change_after_an_unreadable_load_does_not_write(self) -> None:
        # Locked or denied: the file still holds the user's settings, so it is kept.
        self.path.write_bytes(GOOD_CONFIG)

        with (
            patch("builtins.open", self._open_denying_reads()),
            self.assertLogs("dotexpress.config", level="WARNING") as captured,
        ):
            self.store.set_output_mode("ascii")
            self.store.set_conversion_width(52)

        self.assertEqual(self.path.read_bytes(), GOOD_CONFIG)
        self.assertEqual(self._listing(), ["config.json"])
        refusals = [record for record in captured.records if "was not saved" in record.getMessage()]
        self.assertEqual(
            [(record.levelno, record.getMessage()) for record in refusals],
            [(logging.WARNING, f"Config file {self.path} was not saved because it could not be read")],
        )

    def test_a_good_load_logs_the_next_refused_save_again(self) -> None:
        # F-8a review M-3: once the file was read successfully, the same read error is
        # new again, and the next refused save is logged once more.
        self.path.write_bytes(GOOD_CONFIG)

        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            with patch("builtins.open", self._open_denying_reads()):
                self.store.set_output_mode("ascii")
            self.assertEqual(self.store.get_conversion_width(), 30)
            with patch("builtins.open", self._open_denying_reads()):
                self.store.set_conversion_width(52)

        self.assertEqual(self.path.read_bytes(), GOOD_CONFIG)
        self.assertEqual(self._listing(), ["config.json"])
        refusals = [record for record in captured.records if "was not saved" in record.getMessage()]
        self.assertEqual(
            [(record.levelno, record.getMessage()) for record in refusals],
            [(logging.WARNING, f"Config file {self.path} was not saved because it could not be read")] * 2,
        )

    def test_a_failed_backup_prevents_the_write(self) -> None:
        self.path.write_bytes(b"{damaged")

        with (
            patch("config.write_bytes_atomically", side_effect=OSError(errno.ENOSPC, "injected"), create=True),
            self.assertLogs("dotexpress.config", level="WARNING") as captured,
        ):
            self.store.set_output_mode("ascii")

        self.assertEqual(self.path.read_bytes(), b"{damaged")
        self.assertEqual(self._listing(), ["config.json"])
        errors = [record for record in captured.records if record.levelno == logging.ERROR]
        self.assertEqual([record.getMessage() for record in errors], [f"Failed to save config file {self.path}"])
        self.assertEqual(str(errors[0].exc_info[1]), f"[Errno {errno.ENOSPC}] injected")

    def test_a_missing_file_is_created_without_backup(self) -> None:
        self.store.set_output_mode("ascii")

        self.assertEqual(self._listing(), ["config.json"])
        self.assertEqual(
            self._saved(),
            {
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                "conversion": {"output_mode": "ascii"},
            },
        )

    def test_a_good_file_is_updated_without_backup(self) -> None:
        self.path.write_bytes(GOOD_CONFIG)

        self.store.set_output_mode("ascii")

        self.assertEqual(self._listing(), ["config.json"])
        self.assertEqual(self._saved(), {"view": {"font_size": 20}, "conversion": {"width": 30, "output_mode": "ascii"}})


class ConfigSaveProblemTest(unittest.TestCase):
    """F-12 (D6): a save that does not reach config.json returns why; the F-8 rules stay."""

    SETTERS = (
        ("set_output_mode", ("ascii",)),
        ("set_conversion_width", (52,)),
        ("set_selected_dictionary", ("alpha",)),
        ("set_translation_tables", ({"default": "zh-tw.ctb"},)),
        ("set_view_settings", (18, "dark", "default")),
    )

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.directory = Path(temp_dir.name)
        self.path = self.directory / "config.json"
        self.backup = self.directory / "config.json.bak"
        self.store = config.ConfigStore(self.path)
        for logged in (config._logged_load_failures, config._logged_skipped_saves):
            logged.clear()
            self.addCleanup(logged.clear)

    def _problem(self):
        return config.ConfigSaveProblem

    def _kind(self, name: str):
        return getattr(config.ConfigSaveProblemKind, name)

    def test_every_setter_returns_none_when_the_save_works(self) -> None:
        for name, args in self.SETTERS:
            with self.subTest(name):
                self.assertIsNone(getattr(self.store, name)(*args))

        self.assertEqual(self._saved_keys(), ["conversion", "language_detection", "view"])

    def _saved_keys(self) -> list[str]:
        return sorted(json.loads(self.path.read_text(encoding="utf-8")))

    def test_a_file_that_cannot_be_read_is_unreadable(self) -> None:
        # A folder at config.json: opening it for reading fails, as for a locked file.
        self.path.mkdir()

        with self.assertLogs("dotexpress.config", level="WARNING"):
            problems = [getattr(self.store, name)(*args) for name, args in self.SETTERS]

        for (name, _args), problem in zip(self.SETTERS, problems):
            with self.subTest(name):
                self.assertIsInstance(problem, self._problem())
                self.assertIs(problem.kind, self._kind("UNREADABLE"))
                self.assertIsInstance(problem.error, OSError)
                self.assertEqual(problem.path, self.path)
                self.assertIsNone(problem.backup_path)
        self.assertTrue(self.path.is_dir())

    def test_a_damaged_file_whose_backup_fails_is_backup_failed(self) -> None:
        self.path.write_bytes(b"{")
        self.backup.mkdir()

        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            problem = self.store.set_output_mode("ascii")

        self.assertIs(problem.kind, self._kind("BACKUP_FAILED"))
        self.assertIsInstance(problem.error, OSError)
        self.assertEqual((problem.path, problem.backup_path), (self.path, self.backup))
        self.assertEqual(self.path.read_bytes(), b"{")
        errors = [record.getMessage() for record in captured.records if record.levelno == logging.ERROR]
        self.assertEqual(errors, [f"Failed to save config file {self.path}"])
        # The box gives a reason without the error's text (F-14 D7); the log keeps the error.
        (error_record,) = [record for record in captured.records if record.levelno == logging.ERROR]
        self.assertIs(error_record.exc_info[1], problem.error)

    def test_a_write_that_fails_is_write_failed(self) -> None:
        error = OSError(errno.ENOSPC, "injected")

        with patch("os.replace", side_effect=error), self.assertLogs("dotexpress.config", level="ERROR") as captured:
            problem = self.store.set_view_settings(18, "dark", "default")

        self.assertEqual(problem, self._problem()(self._kind("WRITE_FAILED"), error, self.path))
        self.assertFalse(self.path.exists())
        self.assertEqual([record.getMessage() for record in captured.records], [f"Failed to save config file {self.path}"])

    def test_the_client_id_and_the_language_ignore_a_failed_save(self) -> None:
        # Not settings the user changed; the client id is saved on a background thread.
        self.path.mkdir()

        with self.assertLogs("dotexpress.config", level="WARNING"), patch.object(config, "_runtime_lang", None):
            client_id = self.store.get_or_create_client_id()
            language = self.store.set_lang("en", persist=True)

        self.assertEqual(str(UUID(client_id)), client_id)
        self.assertIsNone(language)


class ConfigModuleShapeTest(unittest.TestCase):
    """P2-6: config IO lives on ``ConfigStore``; the module holds no path and no IO functions."""

    def test_config_io_lives_only_on_the_store(self) -> None:
        own_functions = [
            name
            for name, value in vars(config).items()
            if inspect.isfunction(value) and value.__module__ == config.__name__
        ]

        self.assertEqual([name for name in own_functions if name.startswith(("get_", "set_"))], [])
        self.assertEqual([name for name in vars(config) if "PATH" in name], [])


if __name__ == "__main__":
    unittest.main()
