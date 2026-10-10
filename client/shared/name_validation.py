from __future__ import annotations

from typing import Literal

MAX_NAME_LENGTH = 32
WINDOWS_INVALID_CHARS = set('<>:"/\\|?*')
WINDOWS_RESERVED_DEVICE_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}
WINDOWS_RESERVED_DEVICE_NAMES_CASEFOLDED = {name.casefold() for name in WINDOWS_RESERVED_DEVICE_NAMES}

NameValidationCode = Literal["empty", "invalid", "too_long", "reserved"]


class NameValidationError(ValueError):
    """``normalize_base_name`` rejected a name: ``code`` says why, ``str(error)`` is the English message."""

    def __init__(self, code: NameValidationCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _is_surrogate(char: str) -> bool:
    # A surrogate code point (a lone one, or half of a pair left as two code points)
    # cannot be encoded as UTF-8, so a package or file holding the name cannot be written.
    return 0xD800 <= ord(char) <= 0xDFFF


def _is_windows_reserved_device_name(name: str) -> bool:
    root_name = name.split(".", 1)[0]
    return root_name.casefold() in WINDOWS_RESERVED_DEVICE_NAMES_CASEFOLDED


def _is_windows_legal_name(name: str) -> bool:
    if name in {".", ".."}:
        return False
    if name.endswith(".") or name.endswith(" "):
        return False
    if any(ord(char) < 32 for char in name):
        return False
    if any(char in WINDOWS_INVALID_CHARS for char in name):
        return False
    if _is_windows_reserved_device_name(name):
        return False
    return True


def normalize_base_name(name: str, *, reserved_names: set[str] | None = None) -> str:
    if not name or not name.strip():
        raise NameValidationError("empty", "Name cannot be empty.")
    if any(ord(char) < 32 or _is_surrogate(char) for char in name):
        raise NameValidationError("invalid", "Name contains invalid characters.")
    if name.endswith((" ", ".")):
        raise NameValidationError("invalid", "Name cannot end with a period or space.")
    normalized = name.strip()
    if len(normalized) > MAX_NAME_LENGTH:
        raise NameValidationError("too_long", f"Name cannot exceed {MAX_NAME_LENGTH} characters.")
    if not _is_windows_legal_name(normalized):
        raise NameValidationError("invalid", "Name contains invalid characters.")
    if reserved_names and normalized.casefold() in {reserved.casefold() for reserved in reserved_names}:
        raise NameValidationError("reserved", f"Name '{normalized}' is reserved.")
    return normalized
