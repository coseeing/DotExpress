from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from documents.formats import get_exportable_formats

EnabledWhen = Literal["always", "has_selection", "has_documents"]


@dataclass(frozen=True)
class DocumentMenuItem:
    kind: str
    label: str
    action: str
    enabled_when: EnabledWhen
    formats: tuple[tuple[str, str], ...] = ()


_EXPORT_FORMATS: tuple[tuple[str, str], ...] = tuple(
    (descriptor.key, descriptor.export_label) for descriptor in get_exportable_formats()
)

DOCUMENT_MENU_ITEMS: tuple[DocumentMenuItem, ...] = (
    DocumentMenuItem(kind="command", label="Open", action="open", enabled_when="has_selection"),
    DocumentMenuItem(kind="command", label="Delete", action="delete", enabled_when="has_selection"),
    DocumentMenuItem(kind="command", label="Delete All", action="delete_all", enabled_when="has_documents"),
    DocumentMenuItem(kind="command", label="Add", action="add", enabled_when="always"),
    DocumentMenuItem(kind="command", label="Rename", action="rename", enabled_when="has_selection"),
    DocumentMenuItem(kind="command", label="Import", action="import", enabled_when="always"),
    DocumentMenuItem(
        kind="submenu",
        label="Export",
        action="export",
        enabled_when="has_selection",
        formats=_EXPORT_FORMATS,
    ),
    DocumentMenuItem(
        kind="submenu",
        label="Export All",
        action="export_all",
        enabled_when="has_documents",
        formats=_EXPORT_FORMATS,
    ),
)


def get_document_menu_descriptors() -> tuple[DocumentMenuItem, ...]:
    return DOCUMENT_MENU_ITEMS


def get_document_menu_enabled_state(*, has_selection: bool, has_documents: bool) -> dict[str, bool]:
    conditions = {"always": True, "has_selection": has_selection, "has_documents": has_documents}
    return {item.action: conditions[item.enabled_when] for item in DOCUMENT_MENU_ITEMS}
