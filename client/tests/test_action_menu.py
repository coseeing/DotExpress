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

    def test_document_menu_labels_and_actions_in_order(self) -> None:
        self.assertEqual(
            [(item.label, item.action, item.kind) for item in get_document_menu_descriptors()],
            [
                ("Open", "open", "command"),
                ("Delete", "delete", "command"),
                ("Delete All", "delete_all", "command"),
                ("Add", "add", "command"),
                ("Rename", "rename", "command"),
                ("Import", "import", "command"),
                ("Export", "export", "submenu"),
                ("Export All", "export_all", "submenu"),
            ],
        )

    def test_document_menu_actions_are_unique(self) -> None:
        actions = [item.action for item in get_document_menu_descriptors()]
        self.assertEqual(len(actions), len(set(actions)))
        self.assertNotIn("", actions)

    def test_document_menu_enabled_when_uses_known_rules(self) -> None:
        self.assertEqual(
            [(item.action, item.enabled_when) for item in get_document_menu_descriptors()],
            [
                ("open", "has_selection"),
                ("delete", "has_selection"),
                ("delete_all", "has_documents"),
                ("add", "always"),
                ("rename", "has_selection"),
                ("import", "always"),
                ("export", "has_selection"),
                ("export_all", "has_documents"),
            ],
        )

    def test_document_menu_enabled_state_follows_descriptor_order(self) -> None:
        for has_selection in (False, True):
            for has_documents in (False, True):
                with self.subTest(has_selection=has_selection, has_documents=has_documents):
                    state = get_document_menu_enabled_state(has_selection=has_selection, has_documents=has_documents)
                    self.assertEqual(list(state), [item.action for item in get_document_menu_descriptors()])

    def test_document_menu_enabled_state_without_selection_or_documents(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=False, has_documents=False),
            {
                "open": False,
                "delete": False,
                "delete_all": False,
                "add": True,
                "rename": False,
                "import": True,
                "export": False,
                "export_all": False,
            },
        )

    def test_document_menu_enabled_state_with_selection_and_documents(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=True, has_documents=True),
            {
                "open": True,
                "delete": True,
                "delete_all": True,
                "add": True,
                "rename": True,
                "import": True,
                "export": True,
                "export_all": True,
            },
        )

    def test_document_menu_enabled_state_with_selection_but_no_documents(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=True, has_documents=False),
            {
                "open": True,
                "delete": True,
                "delete_all": False,
                "add": True,
                "rename": True,
                "import": True,
                "export": True,
                "export_all": False,
            },
        )

    def test_document_menu_enabled_state_with_documents_but_no_selection(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=False, has_documents=True),
            {
                "open": False,
                "delete": False,
                "delete_all": True,
                "add": True,
                "rename": False,
                "import": True,
                "export": False,
                "export_all": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
