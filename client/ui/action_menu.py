from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentMenuItem:
    kind: str
    label: str
    action: str = ""
    formats: tuple[str, ...] = ()


DOCUMENT_MENU_ITEMS: tuple[DocumentMenuItem, ...] = (
    DocumentMenuItem("command", "Open", "open"),
    DocumentMenuItem("command", "Delete", "delete"),
    DocumentMenuItem("command", "Delete All", "delete_all"),
    DocumentMenuItem("command", "Add", "add"),
    DocumentMenuItem("command", "Rename", "rename"),
    DocumentMenuItem("command", "Import", "import"),
    DocumentMenuItem("submenu", "Export", "export", ("DEP", "BRL")),
    DocumentMenuItem("submenu", "Export All", "export_all", ("DEP", "BRL")),
)


def build_actions_button_label(base_label: str) -> str:
    return f"{base_label} ▼"


def get_actions_menu_position(button_size: tuple[int, int]) -> tuple[int, int]:
    return (0, button_size[1])


def get_document_menu_items() -> list[tuple[str, str] | tuple[str, str, list[str]]]:
    items: list[tuple[str, str] | tuple[str, str, list[str]]] = []
    for item in DOCUMENT_MENU_ITEMS:
        if item.kind == "submenu":
            items.append((item.kind, item.label, list(item.formats)))
        else:
            items.append((item.kind, item.label))
    return items


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


def get_dictionary_action_labels() -> list[str]:
    return ["Edit", "Delete", "Rename", "Add", "Import", "Export"]


def get_document_action_labels() -> list[str]:
    return [item[1] for item in get_document_menu_items()]


def get_document_export_format_labels() -> list[str]:
    return ["DEP", "BRL"]
