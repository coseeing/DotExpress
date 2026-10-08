import unittest

from documents.formats import get_exportable_formats
from ui.action_menu import (
    get_document_menu_descriptors,
    get_document_menu_enabled_state,
)


class ActionMenuTest(unittest.TestCase):
    def test_export_submenus_use_descriptive_formats_in_order(self) -> None:
        items = {item.label: item for item in get_document_menu_descriptors()}
        expected_formats = (("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))

        for label, action in (("Export", "export"), ("Export All", "export_all")):
            with self.subTest(label=label):
                item = items[label]
                self.assertEqual(item.kind, "submenu")
                self.assertEqual(item.action, action)
                self.assertEqual(item.formats, expected_formats)

    def test_export_submenus_follow_the_format_registry(self) -> None:
        registry_formats = tuple((descriptor.key, descriptor.export_label) for descriptor in get_exportable_formats())
        submenus = [item for item in get_document_menu_descriptors() if item.kind == "submenu"]

        self.assertEqual([item.action for item in submenus], ["export", "export_all"])
        for item in submenus:
            with self.subTest(action=item.action):
                self.assertEqual(item.formats, registry_formats)

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
