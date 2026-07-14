from __future__ import annotations


def get_translation_menu_items() -> list[tuple[str, str]]:
    return [
        ("convert", "Convert"),
        ("dual_view", "Dual View"),
        ("text_processing", "Text Processing"),
        ("dictionaries", "Dictionary Management..."),
        ("settings", "Settings"),
    ]
