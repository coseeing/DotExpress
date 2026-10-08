from __future__ import annotations

from dataclasses import dataclass

from documents.formats import get_exportable_formats


@dataclass(frozen=True)
class DocumentMenuItem:
    kind: str
    label: str
    action: str = ""
    formats: tuple[tuple[str, str], ...] = ()


_EXPORT_FORMATS: tuple[tuple[str, str], ...] = tuple(
    (descriptor.key, descriptor.export_label) for descriptor in get_exportable_formats()
)

DOCUMENT_MENU_ITEMS: tuple[DocumentMenuItem, ...] = (
    DocumentMenuItem("command", "Open", "open"),
    DocumentMenuItem("command", "Delete", "delete"),
    DocumentMenuItem("command", "Delete All", "delete_all"),
    DocumentMenuItem("command", "Add", "add"),
    DocumentMenuItem("command", "Rename", "rename"),
    DocumentMenuItem("command", "Import", "import"),
    DocumentMenuItem("submenu", "Export", "export", _EXPORT_FORMATS),
    DocumentMenuItem("submenu", "Export All", "export_all", _EXPORT_FORMATS),
)


def get_document_menu_descriptors() -> tuple[DocumentMenuItem, ...]:
    return DOCUMENT_MENU_ITEMS


def get_document_menu_enabled_state(*, has_selection: bool, has_documents: bool) -> dict[str, bool]:
    return {
        "Open": has_selection,
        "Delete": has_selection,
        "Delete All": has_documents,
        "Add": True,
        "Rename": has_selection,
        "Import": True,
        "Export": has_selection,
        "Export All": has_documents,
    }
