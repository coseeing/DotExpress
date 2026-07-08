from __future__ import annotations

from dataclasses import dataclass

from documents.formats import (
    ALL_SUPPORTED_FILTER_INDEX,
    ALL_SUPPORTED_FILTER_KEY,
    build_import_wildcard as build_format_wildcard,
    get_import_filter_labels as get_format_import_filter_labels,
    get_importable_formats,
)


@dataclass(frozen=True)
class ImportFilter:
    key: str
    label: str
    pattern: str


def get_import_filters() -> tuple[ImportFilter, ...]:
    importable_formats = get_importable_formats()
    labels = get_format_import_filter_labels()
    filters = tuple(
        ImportFilter(descriptor.key, descriptor.wildcard_label, f"*{descriptor.extension}")
        for descriptor in importable_formats
    )
    all_patterns = ";".join(f"*{descriptor.extension}" for descriptor in importable_formats)
    return filters + (ImportFilter(ALL_SUPPORTED_FILTER_KEY, labels[-1], all_patterns),)


def build_import_wildcard(translate=lambda value: value) -> str:
    return build_format_wildcard(translate)


def get_import_filter_labels() -> list[str]:
    return list(get_format_import_filter_labels())


def get_import_wildcard_text() -> str:
    return build_import_wildcard()


def get_default_import_filter_index() -> int:
    return ALL_SUPPORTED_FILTER_INDEX
