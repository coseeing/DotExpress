from __future__ import annotations


def build_actions_button_label(base_label: str) -> str:
    return f"{base_label} ▼"


def get_actions_menu_position(button_size: tuple[int, int]) -> tuple[int, int]:
    return (0, button_size[1])


def get_document_menu_items() -> list[tuple[str, str] | tuple[str, str, list[str]]]:
    return [
        ("command", "Open"),
        ("command", "Delete"),
        ("command", "Delete All"),
        ("command", "Add"),
        ("command", "Rename"),
        ("submenu", "Import", get_document_import_format_labels()),
        ("submenu", "Export", get_document_export_format_labels()),
        ("submenu", "Export All", get_document_export_format_labels()),
    ]


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


def get_document_import_format_labels() -> list[str]:
    return ["DEP", "TXT"]


def get_document_export_format_labels() -> list[str]:
    return ["DEP", "BRL"]
