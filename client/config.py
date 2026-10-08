from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app_paths import get_config_path
from conversion.math_braille_codes import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES  # noqa: F401  (re-exported)
from log import get_logger

logger = get_logger("dotexpress.config", "config.log", level=logging.WARNING)

DEFAULT_FALLBACK = "zh_TW"
LANG_ENV = "TEXT2BRAILLE_LANG"
CONFIG_PATH = str(get_config_path())

CONVERSION_SECTION = "conversion"
VIEW_SECTION = "view"
CLIENT_SECTION = "client"
TRANSLATION_TABLES_KEY = "translation_tables"
OUTPUT_MODE_KEY = "output_mode"
WIDTH_KEY = "width"
SELECTED_DICTIONARY_KEY = "selected_dictionary"
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


def _log_current_exception(level: int, message: str, *args: object) -> None:
    try:
        logger.log(level, message, *args, exc_info=True)
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
    """config.json at one path. Each getter re-reads the file; nothing is cached."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> dict:
        path = str(self._path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            _logged_load_failures.pop(path, None)
            return {}
        except Exception as error:
            signature = f"{type(error).__name__}: {error}"
            if _logged_load_failures.get(path) != signature:
                _logged_load_failures[path] = signature
                _log_current_exception(
                    logging.WARNING,
                    "Failed to read config file %s; using defaults",
                    path,
                )
            return {}
        _logged_load_failures.pop(path, None)
        return data

    def _save(self, data: dict) -> None:
        path = str(self._path)
        try:
            if not os.path.exists(path):
                data = {
                    "language_detection": {
                        "charset_maps": DEFAULT_CHARSET_MAPS.copy(),
                    },
                    **data,
                }
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            _log_current_exception(logging.ERROR, "Failed to save config file %s", path)

    def _set_section_value(self, section: str, key: str, value: object) -> None:
        data = self._load()
        section_data = _get_section(data, section).copy()
        section_data[key] = value
        data[section] = section_data
        self._save(data)

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

    def set_translation_tables(self, tables: dict[str, str]) -> None:
        self._set_section_value(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, dict(tables))

    def get_output_mode(self, default: str = DEFAULT_OUTPUT_MODE) -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(OUTPUT_MODE_KEY)
        return value if isinstance(value, str) else default

    def set_output_mode(self, output_mode: str) -> None:
        self._set_section_value(CONVERSION_SECTION, OUTPUT_MODE_KEY, output_mode)

    def get_conversion_width(self, default: int = DEFAULT_CONVERSION_WIDTH) -> int:
        data = self._load()
        width = _coerce_int(_get_section(data, CONVERSION_SECTION).get(WIDTH_KEY))
        return width if width is not None else default

    def set_conversion_width(self, width: int) -> None:
        self._set_section_value(CONVERSION_SECTION, WIDTH_KEY, width)

    def get_selected_dictionary(self, default: str = "default") -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(SELECTED_DICTIONARY_KEY)
        return value if isinstance(value, str) else default

    def set_selected_dictionary(self, dictionary_name: str) -> None:
        self._set_section_value(CONVERSION_SECTION, SELECTED_DICTIONARY_KEY, dictionary_name)

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

    def set_view_settings(self, font_size: int, scheme: str, braille_font: str) -> None:
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
        self._save(data)

    def get_or_create_client_id(self) -> str:
        data = self._load()
        value = _get_section(data, CLIENT_SECTION).get(CLIENT_ID_KEY)
        if isinstance(value, str) and value:
            return value
        client_id = str(uuid4())
        section_data = _get_section(data, CLIENT_SECTION).copy()
        section_data[CLIENT_ID_KEY] = client_id
        data[CLIENT_SECTION] = section_data
        self._save(data)
        return client_id


# Module-level API kept until P2-6 step 4: each call reads CONFIG_PATH and
# delegates to a ConfigStore built for that call.


def get_lang() -> str:
    return ConfigStore(CONFIG_PATH).get_lang()


def get_charset_maps() -> dict[str, str]:
    return ConfigStore(CONFIG_PATH).get_charset_maps()


def set_lang(lang: str, persist: bool = False) -> None:
    ConfigStore(CONFIG_PATH).set_lang(lang, persist)


def get_translation_tables() -> dict:
    return ConfigStore(CONFIG_PATH).get_translation_tables()


def set_translation_tables(tables: dict[str, str]) -> None:
    ConfigStore(CONFIG_PATH).set_translation_tables(tables)


def get_output_mode(default: str = DEFAULT_OUTPUT_MODE) -> str:
    return ConfigStore(CONFIG_PATH).get_output_mode(default)


def set_output_mode(output_mode: str) -> None:
    ConfigStore(CONFIG_PATH).set_output_mode(output_mode)


def get_conversion_width(default: int = DEFAULT_CONVERSION_WIDTH) -> int:
    return ConfigStore(CONFIG_PATH).get_conversion_width(default)


def set_conversion_width(width: int) -> None:
    ConfigStore(CONFIG_PATH).set_conversion_width(width)


def get_selected_dictionary(default: str = "default") -> str:
    return ConfigStore(CONFIG_PATH).get_selected_dictionary(default)


def set_selected_dictionary(dictionary_name: str) -> None:
    ConfigStore(CONFIG_PATH).set_selected_dictionary(dictionary_name)


def get_view_font_size(default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
    return ConfigStore(CONFIG_PATH).get_view_font_size(default)


def get_view_scheme(default: str = DEFAULT_VIEW_SCHEME) -> str:
    return ConfigStore(CONFIG_PATH).get_view_scheme(default)


def get_braille_font(default: str = DEFAULT_BRAILLE_FONT) -> str:
    return ConfigStore(CONFIG_PATH).get_braille_font(default)


def set_view_settings(font_size: int, scheme: str, braille_font: str) -> None:
    ConfigStore(CONFIG_PATH).set_view_settings(font_size, scheme, braille_font)


def get_or_create_client_id() -> str:
    return ConfigStore(CONFIG_PATH).get_or_create_client_id()
