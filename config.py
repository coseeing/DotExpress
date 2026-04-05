import json
import os
from typing import Optional


DEFAULT_FALLBACK = "zh_TW"
LANG_ENV = "TEXT2BRAILLE_LANG"
CONFIG_PATH = os.path.expanduser("~/.text2braille/config.json")

CONVERSION_SECTION = "conversion"
VIEW_SECTION = "view"
TRANSLATION_TABLES_KEY = "translation_tables"
OUTPUT_MODE_KEY = "output_mode"
WIDTH_KEY = "width"
SELECTED_DICTIONARY_KEY = "selected_dictionary"
FONT_SIZE_KEY = "font_size"
SCHEME_KEY = "scheme"
BRAILLE_FONT_KEY = "braille_font"

DEFAULT_TRANSLATION_TABLES = {
    "default": "zh-tw.ctb",
    "en": "en-ueb-g1.ctb",
    "zh": "zh-tw.ctb",
    "ja": "ja-rokutenkanji.utb",
}
DEFAULT_OUTPUT_MODE = "unicode"
DEFAULT_CONVERSION_WIDTH = 40
DEFAULT_VIEW_FONT_SIZE = 12
DEFAULT_VIEW_SCHEME = "light"
DEFAULT_BRAILLE_FONT = "default"

_runtime_lang: Optional[str] = None


def _load_from_file() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _save_to_file(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
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


def _set_section_value(section: str, key: str, value: object) -> None:
    data = _load_from_file()
    section_data = _get_section(data, section).copy()
    section_data[key] = value
    data[section] = section_data
    _save_to_file(data)


def _get_dict_setting(section: str, key: str, default: dict) -> dict:
    data = _load_from_file()
    section_data = _get_section(data, section)
    value = section_data.get(key)
    if not isinstance(value, dict):
        return default.copy()
    merged = default.copy()
    for name, table in value.items():
        if isinstance(name, str) and isinstance(table, str):
            merged[name] = table
    return merged


def get_lang() -> str:
    if _runtime_lang:
        return _runtime_lang
    lang = os.getenv(LANG_ENV)
    if lang:
        return lang
    data = _load_from_file()
    lang = data.get("language")
    return lang or DEFAULT_FALLBACK


def set_lang(lang: str, persist: bool = False) -> None:
    global _runtime_lang
    _runtime_lang = lang
    if persist:
        data = _load_from_file()
        data["language"] = lang
        _save_to_file(data)


def get_translation_tables() -> dict:
    return _get_dict_setting(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, DEFAULT_TRANSLATION_TABLES)


def set_translation_tables(tables: dict[str, str]) -> None:
    _set_section_value(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, dict(tables))


def get_output_mode(default: str = DEFAULT_OUTPUT_MODE) -> str:
    data = _load_from_file()
    value = _get_section(data, CONVERSION_SECTION).get(OUTPUT_MODE_KEY)
    return value if isinstance(value, str) else default


def set_output_mode(output_mode: str) -> None:
    _set_section_value(CONVERSION_SECTION, OUTPUT_MODE_KEY, output_mode)


def get_conversion_width(default: int = DEFAULT_CONVERSION_WIDTH) -> int:
    data = _load_from_file()
    width = _coerce_int(_get_section(data, CONVERSION_SECTION).get(WIDTH_KEY))
    return width if width is not None else default


def set_conversion_width(width: int) -> None:
    _set_section_value(CONVERSION_SECTION, WIDTH_KEY, width)


def get_selected_dictionary(default: str = "default") -> str:
    data = _load_from_file()
    value = _get_section(data, CONVERSION_SECTION).get(SELECTED_DICTIONARY_KEY)
    return value if isinstance(value, str) else default


def set_selected_dictionary(dictionary_name: str) -> None:
    _set_section_value(CONVERSION_SECTION, SELECTED_DICTIONARY_KEY, dictionary_name)


def get_view_font_size(default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
    data = _load_from_file()
    font_size = _coerce_int(_get_section(data, VIEW_SECTION).get(FONT_SIZE_KEY))
    return font_size if font_size is not None else default


def set_view_font_size(font_size: int) -> None:
    _set_section_value(VIEW_SECTION, FONT_SIZE_KEY, font_size)


def get_view_scheme(default: str = DEFAULT_VIEW_SCHEME) -> str:
    data = _load_from_file()
    value = _get_section(data, VIEW_SECTION).get(SCHEME_KEY)
    return value if isinstance(value, str) else default


def set_view_scheme(scheme: str) -> None:
    _set_section_value(VIEW_SECTION, SCHEME_KEY, scheme)


def get_braille_font(default: str = DEFAULT_BRAILLE_FONT) -> str:
    data = _load_from_file()
    value = _get_section(data, VIEW_SECTION).get(BRAILLE_FONT_KEY)
    return value if isinstance(value, str) else default


def set_braille_font(braille_font: str) -> None:
    _set_section_value(VIEW_SECTION, BRAILLE_FONT_KEY, braille_font)
