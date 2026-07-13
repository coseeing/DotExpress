import unittest

from ui.action_menu import (
    get_document_export_format_labels,
    get_document_menu_enabled_state,
    get_document_menu_items,
)


class ActionMenuTest(unittest.TestCase):
    def test_export_submenus_use_descriptive_formats_in_order(self) -> None:
        items = get_document_menu_items()

        self.assertEqual(
            next(item for item in items if item[1] == "Export"),
            ("submenu", "Export", ["Package DEP", "Braille BRL", "Dual View HTML"]),
        )
        self.assertEqual(
            next(item for item in items if item[1] == "Export All"),
            ("submenu", "Export All", ["Package DEP", "Braille BRL", "Dual View HTML"]),
        )
        self.assertEqual(
            get_document_export_format_labels(),
            ["Package DEP", "Braille BRL", "Dual View HTML"],
        )

    def test_document_menu_enabled_state_without_selection_or_documents(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=False, has_documents=False),
            {
                "Open": False,
                "Delete": False,
                "Delete All": False,
                "Add": True,
                "Rename": False,
                "Import": True,
                "Export": False,
                "Export All": False,
            },
        )

    def test_document_menu_enabled_state_with_selection_and_documents(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=True, has_documents=True),
            {
                "Open": True,
                "Delete": True,
                "Delete All": True,
                "Add": True,
                "Rename": True,
                "Import": True,
                "Export": True,
                "Export All": True,
            },
        )

    def test_document_menu_enabled_state_with_selection_but_no_documents(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=True, has_documents=False),
            {
                "Open": True,
                "Delete": True,
                "Delete All": False,
                "Add": True,
                "Rename": True,
                "Import": True,
                "Export": True,
                "Export All": False,
            },
        )

    def test_document_menu_enabled_state_with_documents_but_no_selection(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=False, has_documents=True),
            {
                "Open": False,
                "Delete": False,
                "Delete All": True,
                "Add": True,
                "Rename": False,
                "Import": True,
                "Export": False,
                "Export All": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
