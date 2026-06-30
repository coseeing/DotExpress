from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from name_validation import normalize_base_name


@dataclass(frozen=True)
class ImportedDocument:
    name: str
    markdown_text: str


def validate_source(path: Path | str, extension: str) -> Path:
    source = Path(path)
    if source.suffix.casefold() != extension.casefold():
        raise ValueError(f"Source document must use the {extension} extension.")
    return source


def source_name(path: Path) -> str:
    return normalize_base_name(path.stem)
