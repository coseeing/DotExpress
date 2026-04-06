from __future__ import annotations


def build_actions_button_label(base_label: str) -> str:
    return f"{base_label} ▼"


def get_actions_menu_position(button_size: tuple[int, int]) -> tuple[int, int]:
    return (0, button_size[1])


def get_dictionary_action_labels() -> list[str]:
    return ["Edit", "Delete", "Rename", "Add", "Import", "Export"]


def get_document_action_labels() -> list[str]:
    return ["Open", "Delete", "Delete All", "Add", "Rename", "Import", "Export", "Batch Import", "Batch Export"]


def get_document_import_format_labels() -> list[str]:
    return ["DEP", "TXT"]


def get_document_export_format_labels() -> list[str]:
    return ["DEP", "BRL"]
