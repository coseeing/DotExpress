from __future__ import annotations

MAX_NAME_LENGTH = 16
INVALID_NAME_CHARS = {".", "/", "\\"}


def normalize_base_name(name: str, *, reserved_names: set[str] | None = None) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValueError("Name cannot be empty.")
    if len(normalized) > MAX_NAME_LENGTH:
        raise ValueError(f"Name cannot exceed {MAX_NAME_LENGTH} characters.")
    if any(char in normalized for char in INVALID_NAME_CHARS):
        raise ValueError("Name contains invalid characters.")
    if reserved_names and normalized.casefold() in {reserved.casefold() for reserved in reserved_names}:
        raise ValueError(f"Name '{normalized}' is reserved.")
    return normalized
