from __future__ import annotations

import errno
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

from conversion.math_braille_codes import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES  # noqa: F401  (re-exported)
from log import get_logger
from shared.atomic_write import write_bytes_atomically, write_text_atomically

logger = get_logger("dotexpress.config", "config.log", level=logging.WARNING)

DEFAULT_FALLBACK = "zh_TW"
LANG_ENV = "TEXT2BRAILLE_LANG"

CONVERSION_SECTION = "conversion"
VIEW_SECTION = "view"
CLIENT_SECTION = "client"
TRANSLATION_TABLES_KEY = "translation_tables"
OUTPUT_MODE_KEY = "output_mode"
WIDTH_KEY = "width"
SELECTED_DICTIONARY_KEY = "selected_dictionary"
# The text-processing script; "no-processing" is No Processing (F-18 D3).
SELECTED_SCRIPT_KEY = "selected_script"
FONT_SIZE_KEY = "font_size"
SCHEME_KEY = "scheme"
BRAILLE_FONT_KEY = "braille_font"
CLIENT_ID_KEY = "id"

DEFAULT_TRANSLATION_TABLES = {
    "default": "zh-tw.ctb",
    "en": "en-ueb-g1.ctb",
    "zh": "zh-tw.ctb",
    "ja": "ja-rokutenkanji.utb",
    "math": DEFAULT_MATH_BRAILLE_TABLE,
}
DEFAULT_OUTPUT_MODE = "unicode"
DEFAULT_CONVERSION_WIDTH = 40
DEFAULT_VIEW_FONT_SIZE = 12
DEFAULT_VIEW_SCHEME = "light"
DEFAULT_BRAILLE_FONT = "simbraille"
DEFAULT_CHARSET_MAPS = {
    "latinCharactersLanguage": "en",
    "CJKCharactersLanguage": "zh",
    "arabicCharactersLanguage": "ar",
}

_runtime_lang: Optional[str] = None

# Config path -> signature of the last load failure that was logged for it.
_logged_load_failures: dict[str, str] = {}
# Config path -> signature of the read error of the last save that was skipped for it (F-8).
_logged_skipped_saves: dict[str, str] = {}


def _signature(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


class ConfigSaveProblemKind(Enum):
    UNREADABLE = "unreadable"  # config.json exists but could not be read, so it is kept
    BACKUP_FAILED = "backup_failed"  # damaged, and config.json.bak could not be written first
    WRITE_FAILED = "write_failed"


@dataclass(frozen=True)
class ConfigSaveProblem:
    """Why a setting did not reach config.json (F-12 D6); the change still applies in memory."""

    kind: ConfigSaveProblemKind
    error: BaseException
    path: Path
    backup_path: Path | None = None  # BACKUP_FAILED only


# Windows: access denied, sharing violation, lock violation.
_ACCESS_WINERRORS = (5, 32, 33)


def is_access_error(error: BaseException) -> bool:
    """Whether ``error`` means the file is held by another program or may not be used (F-12 review M-2)."""
    if isinstance(error, PermissionError):
        return True
    if not isinstance(error, OSError):
        return False
    return getattr(error, "winerror", None) in _ACCESS_WINERRORS or error.errno in (errno.EACCES, errno.EPERM)


class _UnreadableConfig(dict):
    """The empty settings ``_load`` returns for a config.json it could not use (F-8).

    ``error`` is why: an ``OSError`` if the file could not be read, anything else if it
    was read but is not a JSON object. ``_save`` keeps the file accordingly.
    """

    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error


def _log_current_exception(level: int, message: str, *args: object, exc_info: object = True) -> None:
    try:
        logger.log(level, message, *args, exc_info=exc_info)
    except OSError:
        # A delay=True FileHandler opens its file inside emit() and raises if
        # log/ is missing or unwritable. Config I/O must never raise, so a
        # diagnostic that cannot be written is dropped.
        pass


def _coerce_int(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _get_section(data: dict, section: str) -> dict:
    value = data.get(section)
    return value if isinstance(value, dict) else {}


class ConfigStore:
    """config.json at one path. Each getter re-reads the file; nothing is cached.

    The file is written through a synced temporary file: a failed save leaves it as it
    was (F-8). It is read as UTF-8 with or without a BOM; a file that is not a JSON
    object counts as damaged and gives the defaults. A setting changed after a failed
    load never silently discards the file: one that could not be read is not written
    (the change lasts for this session), and a damaged one is first copied to
    ``config.json.bak``.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> dict:
        path = str(self._path)
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError(f"config.json does not hold a JSON object ({type(data).__name__})")
        except FileNotFoundError:
            _logged_load_failures.pop(path, None)
            _logged_skipped_saves.pop(path, None)
            return {}
        except Exception as error:
            signature = _signature(error)
            if _logged_load_failures.get(path) != signature:
                _logged_load_failures[path] = signature
                _log_current_exception(
                    logging.WARNING,
                    "Failed to read config file %s; using defaults",
                    path,
                )
            return _UnreadableConfig(error)
        _logged_load_failures.pop(path, None)
        _logged_skipped_saves.pop(path, None)
        return data

    def _skip_save_of_unreadable_file(self, error: OSError) -> None:
        """The file exists but could not be read: keep it, log once per distinct error."""
        path = str(self._path)
        signature = _signature(error)
        if _logged_skipped_saves.get(path) != signature:
            _logged_skipped_saves[path] = signature
            _log_current_exception(
                logging.WARNING,
                "Config file %s was not saved because it could not be read",
                path,
                exc_info=error,
            )

    def _backup_unreadable(self) -> None:
        """Copy the damaged file's bytes to config.json.bak, replacing an older one."""
        content = self._path.read_bytes()
        write_bytes_atomically(self._path.with_name(f"{self._path.name}.bak"), lambda stream: stream.write(content))

    def _save(self, data: dict) -> ConfigSaveProblem | None:
        """Write ``data``; ``None`` if it was written, else why not (logged as before, F-8 D11)."""
        path = str(self._path)
        if isinstance(data, _UnreadableConfig) and isinstance(data.error, OSError):
            self._skip_save_of_unreadable_file(data.error)
            return ConfigSaveProblem(ConfigSaveProblemKind.UNREADABLE, data.error, self._path)
        if isinstance(data, _UnreadableConfig):
            try:
                self._backup_unreadable()
            except Exception as error:
                _log_current_exception(logging.ERROR, "Failed to save config file %s", path)
                return ConfigSaveProblem(
                    ConfigSaveProblemKind.BACKUP_FAILED,
                    error,
                    self._path,
                    self._path.with_name(f"{self._path.name}.bak"),
                )
        try:
            if not os.path.exists(path):
                data = {
                    "language_detection": {
                        "charset_maps": DEFAULT_CHARSET_MAPS.copy(),
                    },
                    **data,
                }
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write_text_atomically(
                path,
                lambda stream: json.dump(data, stream, ensure_ascii=False, indent=2),
                encoding="utf-8",
                newline=None,
            )
        except Exception as error:
            _log_current_exception(logging.ERROR, "Failed to save config file %s", path)
            return ConfigSaveProblem(ConfigSaveProblemKind.WRITE_FAILED, error, self._path)
        return None

    def _set_section_value(self, section: str, key: str, value: object) -> ConfigSaveProblem | None:
        data = self._load()
        section_data = _get_section(data, section).copy()
        section_data[key] = value
        data[section] = section_data
        return self._save(data)

    def _get_dict_setting(self, section: str, key: str, default: dict) -> dict:
        data = self._load()
        section_data = _get_section(data, section)
        value = section_data.get(key)
        if not isinstance(value, dict):
            return default.copy()
        merged = default.copy()
        for name, table in value.items():
            if isinstance(name, str) and isinstance(table, str):
                merged[name] = table
        return merged

    def get_lang(self) -> str:
        if _runtime_lang:
            return _runtime_lang
        lang = os.getenv(LANG_ENV)
        if lang:
            return lang
        data = self._load()
        lang = data.get("language")
        return lang or DEFAULT_FALLBACK

    def get_charset_maps(self) -> dict[str, str]:
        return self._get_dict_setting(
            "language_detection",
            "charset_maps",
            DEFAULT_CHARSET_MAPS,
        )

    def set_lang(self, lang: str, persist: bool = False) -> None:
        global _runtime_lang
        _runtime_lang = lang
        if persist:
            data = self._load()
            data["language"] = lang
            self._save(data)

    def get_translation_tables(self) -> dict:
        return self._get_dict_setting(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, DEFAULT_TRANSLATION_TABLES)

    def set_translation_tables(self, tables: dict[str, str]) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, dict(tables))

    def get_output_mode(self, default: str = DEFAULT_OUTPUT_MODE) -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(OUTPUT_MODE_KEY)
        return value if isinstance(value, str) else default

    def set_output_mode(self, output_mode: str) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, OUTPUT_MODE_KEY, output_mode)

    def get_conversion_width(self, default: int = DEFAULT_CONVERSION_WIDTH) -> int:
        data = self._load()
        width = _coerce_int(_get_section(data, CONVERSION_SECTION).get(WIDTH_KEY))
        return width if width is not None else default

    def set_conversion_width(self, width: int) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, WIDTH_KEY, width)

    def get_selected_dictionary(self, default: str = "default") -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(SELECTED_DICTIONARY_KEY)
        return value if isinstance(value, str) else default

    def set_selected_dictionary(self, dictionary_name: str) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, SELECTED_DICTIONARY_KEY, dictionary_name)

    def get_selected_script(self, default: str = "no-processing") -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(SELECTED_SCRIPT_KEY)
        return value if isinstance(value, str) else default

    def set_selected_script(self, script_name: str) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, SELECTED_SCRIPT_KEY, script_name)

    def get_view_font_size(self, default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
        data = self._load()
        font_size = _coerce_int(_get_section(data, VIEW_SECTION).get(FONT_SIZE_KEY))
        return font_size if font_size is not None else default

    def get_view_scheme(self, default: str = DEFAULT_VIEW_SCHEME) -> str:
        data = self._load()
        value = _get_section(data, VIEW_SECTION).get(SCHEME_KEY)
        return value if isinstance(value, str) else default

    def get_braille_font(self, default: str = DEFAULT_BRAILLE_FONT) -> str:
        data = self._load()
        value = _get_section(data, VIEW_SECTION).get(BRAILLE_FONT_KEY)
        return value if isinstance(value, str) else default

    def set_view_settings(self, font_size: int, scheme: str, braille_font: str) -> ConfigSaveProblem | None:
        data = self._load()
        section_data = _get_section(data, VIEW_SECTION).copy()
        section_data.update(
            {
                FONT_SIZE_KEY: font_size,
                SCHEME_KEY: scheme,
                BRAILLE_FONT_KEY: braille_font,
            }
        )
        data[VIEW_SECTION] = section_data
        return self._save(data)

    def get_or_create_client_id(self) -> str:
        data = self._load()
        value = _get_section(data, CLIENT_SECTION).get(CLIENT_ID_KEY)
        if isinstance(value, str) and value:
            return value
        client_id = str(uuid4())
        section_data = _get_section(data, CLIENT_SECTION).copy()
        section_data[CLIENT_ID_KEY] = client_id
        data[CLIENT_SECTION] = section_data
        # Not a setting the user changed, and saved on a background thread: a problem is only
        # logged (F-12 D6).
        self._save(data)
        return client_id
