import unittest

from action_menu import (
    build_actions_button_label,
    get_actions_menu_position,
    get_dictionary_action_labels,
    get_document_action_labels,
    get_document_import_format_labels,
    get_document_export_format_labels,
)


class ActionMenuTest(unittest.TestCase):
    def test_build_actions_button_label_appends_dropdown_arrow(self) -> None:
        self.assertEqual(build_actions_button_label("動作"), "動作 ▼")

    def test_get_actions_menu_position_places_menu_below_button(self) -> None:
        self.assertEqual(get_actions_menu_position((120, 32)), (0, 32))

    def test_get_dictionary_action_labels_returns_requested_order(self) -> None:
        self.assertEqual(
            get_dictionary_action_labels(),
            ["Edit", "Delete", "Rename", "Add", "Import", "Export"],
        )

    def test_get_document_action_labels_returns_requested_order(self) -> None:
        self.assertEqual(
            get_document_action_labels(),
            ["Open", "Delete", "Delete All", "Add", "Rename", "Import", "Export", "Batch Import", "Batch Export"],
        )

    def test_get_document_import_format_labels_returns_requested_order(self) -> None:
        self.assertEqual(get_document_import_format_labels(), ["DEP", "TXT"])

    def test_get_document_export_format_labels_returns_requested_order(self) -> None:
        self.assertEqual(get_document_export_format_labels(), ["DEP", "BRL"])


if __name__ == "__main__":
    unittest.main()
