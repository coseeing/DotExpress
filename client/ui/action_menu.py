from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentMenuItem:
    kind: str
    label: str
    action: str = ""
    formats: tuple[tuple[str, str], ...] = ()


DOCUMENT_MENU_ITEMS: tuple[DocumentMenuItem, ...] = (
    DocumentMenuItem("command", "Open", "open"),
    DocumentMenuItem("command", "Delete", "delete"),
    DocumentMenuItem("command", "Delete All", "delete_all"),
    DocumentMenuItem("command", "Add", "add"),
    DocumentMenuItem("command", "Rename", "rename"),
    DocumentMenuItem("command", "Import", "import"),
    DocumentMenuItem(
        "submenu",
        "Export",
        "export",
        (("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML")),
    ),
    DocumentMenuItem(
        "submenu",
        "Export All",
        "export_all",
        (("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML")),
    ),
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
