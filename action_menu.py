from __future__ import annotations


def build_actions_button_label(base_label: str) -> str:
    return f"{base_label} ▼"


def get_actions_menu_position(button_size: tuple[int, int]) -> tuple[int, int]:
    return (0, button_size[1])


def get_dictionary_action_labels() -> list[str]:
    return ["Edit", "Delete", "Add", "Import", "Export"]


def get_document_action_labels() -> list[str]:
    return ["Open", "Delete", "Add", "Import", "Rename", "Export"]
