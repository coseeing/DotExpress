from __future__ import annotations

from pathlib import Path
import ctypes
import sys

SIMBRAILLE_FACE_NAME = "SimBraille"
FR_PRIVATE = 0x10


def get_simbraille_font_path(base_dir: Path) -> Path:
    return Path(base_dir) / "data" / "SimBraille.ttf"


def _get_windows_add_font_resource_ex():
    return ctypes.windll.gdi32.AddFontResourceExW


def register_private_font_for_windows(
    font_path: Path | str,
    *,
    platform: str | None = None,
    add_font_resource_ex=None,
) -> bool:
    current_platform = platform or sys.platform
    path = Path(font_path)
    if current_platform != "win32" or not path.exists():
        return False
    loader = add_font_resource_ex or _get_windows_add_font_resource_ex()
    try:
        return bool(loader(str(path), FR_PRIVATE, None))
    except Exception:
        return False
