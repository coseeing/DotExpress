import json
import os
from typing import Optional


# Single source of truth for language setting
DEFAULT_FALLBACK = "zh_TW"
LANG_ENV = "TEXT2BRAILLE_LANG"
CONFIG_PATH = os.path.expanduser("~/.text2braille/config.json")

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
        # Silently ignore persistence errors to avoid breaking runtime behavior
        pass


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

