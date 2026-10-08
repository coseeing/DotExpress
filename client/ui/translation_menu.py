from __future__ import annotations

from i18n import N_


def get_translation_menu_items() -> list[tuple[str, str]]:
    return [
        ("convert", N_("Convert")),
        ("dual_view", N_("Dual View")),
        ("text_processing", N_("Text Processing")),
        ("dictionaries", N_("Dictionary Management...")),
        ("settings", N_("Settings")),
    ]
