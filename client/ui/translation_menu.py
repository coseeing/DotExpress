from __future__ import annotations


def get_translation_menu_items() -> list[tuple[str, str]]:
    return [
        ("convert", "Convert"),
        ("dual_view", "Dual View"),
        ("settings", "Translation Settings..."),
        ("tables", "Translation Tables Setting..."),
        ("dictionaries", "Dictionary Management..."),
    ]
