import unittest

from ui.action_menu import (
    get_document_menu_enabled_state,
    get_document_menu_descriptors,
    get_document_menu_items,
)


class ActionMenuTest(unittest.TestCase):
    def test_document_menu_items_match_required_order_and_formats(self) -> None:
        self.assertEqual(
            get_document_menu_items(),
            [
                ("command", "Open"),
                ("command", "Dual View"),
                ("command", "Delete"),
                ("command", "Delete All"),
                ("command", "Add"),
                ("command", "Rename"),
                ("command", "Import"),
                ("submenu", "Export", ["DEP", "BRL"]),
                ("submenu", "Export All", ["DEP", "BRL"]),
            ],
        )

    def test_document_menu_descriptors_include_action_keys(self) -> None:
        self.assertEqual(
            [item.action for item in get_document_menu_descriptors()],
            ["open", "dual_view", "delete", "delete_all", "add", "rename", "import", "export", "export_all"],
        )

    def test_document_menu_enabled_state_without_selection_or_documents(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=False, has_documents=False),
            {
                "Open": False,
                "Dual View": True,
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
                "Dual View": True,
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
                "Dual View": True,
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
                "Dual View": True,
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
