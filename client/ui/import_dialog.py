from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportFilter:
    key: str
    label: str
    pattern: str


IMPORT_FILTERS: tuple[ImportFilter, ...] = (
    ImportFilter("dep", "DEP", "*.dep"),
    ImportFilter("docx", "DOCX", "*.docx"),
    ImportFilter("epub", "EPUB", "*.epub"),
    ImportFilter("pdf", "PDF", "*.pdf"),
    ImportFilter("txt", "TXT", "*.txt"),
    ImportFilter("all", "All Supported Files", "*.dep;*.docx;*.epub;*.pdf;*.txt"),
)

ALL_SUPPORTED_FILTER_INDEX = len(IMPORT_FILTERS) - 1


def get_import_filters() -> tuple[ImportFilter, ...]:
    return IMPORT_FILTERS


def build_import_wildcard(translate=lambda value: value) -> str:
    parts: list[str] = []
    for item in IMPORT_FILTERS:
        parts.extend((f"{translate(item.label)} ({item.pattern})", item.pattern))
    return "|".join(parts)


def get_import_filter_labels() -> list[str]:
    return [item.label for item in IMPORT_FILTERS]


def get_import_wildcard_text() -> str:
    return build_import_wildcard()


def get_default_import_filter_index() -> int:
    return ALL_SUPPORTED_FILTER_INDEX
