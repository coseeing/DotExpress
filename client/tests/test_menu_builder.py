import ast
import unittest
from pathlib import Path
from unittest.mock import Mock, call

from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, RecordedItem, fake_translate
from ui.action_menu import DocumentMenuItem, get_document_menu_descriptors
from ui.menu_builder import apply_document_menu_state, build_document_menu

MENU_BUILDER_PATH = Path(__file__).resolve().parents[1] / "ui" / "menu_builder.py"
DOCUMENT_ACTIONS = ("open", "delete", "delete_all", "add", "rename", "import", "export", "export_all")


class MenuBuilderTest(unittest.TestCase):
    def _build(self, handlers, descriptors=None, recorder=None):
        recorder = recorder or MenuRecorder()
        menu = recorder.new_menu()
        kwargs = {} if descriptors is None else {"descriptors": descriptors}
        items = build_document_menu(
            menu,
            handlers,
            translate=fake_translate,
            new_menu=recorder.new_menu,
            menu_event="EVT_MENU",
            item_id=-1,
            **kwargs,
        )
        return recorder, items

    def _handlers(self):
        calls = Mock()
        return calls, {action: getattr(calls, action) for action in DOCUMENT_ACTIONS}

    def test_default_descriptors_build_today_menu_log(self) -> None:
        _calls, handlers = self._handlers()

        recorder, _items = self._build(handlers)

        self.assertEqual(recorder.log, DOCUMENT_MENU_BUILD_LOG)

    def test_handlers_receive_event_or_casefolded_format_key(self) -> None:
        calls, handlers = self._handlers()
        recorder, _items = self._build(handlers)
        event = object()
        expected = [getattr(call, action)(event) for action in DOCUMENT_ACTIONS[:6]]
        expected += [call.export(key) for key in ("dep", "brl", "html")]
        expected += [call.export_all(key) for key in ("dep", "brl", "html")]

        self.assertEqual(len(recorder.binds), len(expected))
        for (menu_name, item_name, handler), expected_call in zip(recorder.binds, expected):
            with self.subTest(item=item_name):
                calls.reset_mock()
                handler(event)
                self.assertEqual(menu_name, "menu0")
                self.assertEqual(calls.mock_calls, [expected_call])

    def test_command_handlers_are_bound_as_given(self) -> None:
        _calls, handlers = self._handlers()

        recorder, _items = self._build(handlers)

        self.assertEqual(
            [handler for _menu, _item, handler in recorder.binds[:6]],
            [handlers[action] for action in DOCUMENT_ACTIONS[:6]],
        )

    def test_returns_top_level_items_by_action(self) -> None:
        _calls, handlers = self._handlers()

        _recorder, items = self._build(handlers)

        self.assertEqual(list(items), list(DOCUMENT_ACTIONS))
        self.assertTrue(all(isinstance(item, RecordedItem) for item in items.values()))
        self.assertEqual(
            [item.name for item in items.values()],
            [
                "menu0:T[Open]",
                "menu0:T[Delete]",
                "menu0:T[Delete All]",
                "menu0:T[Add]",
                "menu0:T[Rename]",
                "menu0:T[Import]",
                "menu0:T[Export]",
                "menu0:T[Export All]",
            ],
        )

    def test_missing_handler_raises_before_any_menu_call(self) -> None:
        recorder = MenuRecorder()
        _calls, handlers = self._handlers()
        del handlers["rename"]

        with self.assertRaisesRegex(ValueError, r"missing \['rename'\], extra \[\]"):
            self._build(handlers, recorder=recorder)

        self.assertEqual(recorder.log, [("new", "menu0")])

    def test_extra_handler_raises_before_any_menu_call(self) -> None:
        recorder = MenuRecorder()
        _calls, handlers = self._handlers()
        handlers["print"] = Mock()

        with self.assertRaisesRegex(ValueError, r"missing \[\], extra \['print'\]"):
            self._build(handlers, recorder=recorder)

        self.assertEqual(recorder.log, [("new", "menu0")])

    def test_custom_descriptors_build_and_bind_in_order(self) -> None:
        descriptors = (
            DocumentMenuItem(kind="submenu", label="Save As", action="save_as", enabled_when="always", formats=(("TxT", "Text"),)),
            DocumentMenuItem(kind="command", label="Close", action="close", enabled_when="has_selection"),
        )
        calls = Mock()
        handlers = {"save_as": calls.save_as, "close": calls.close}

        recorder, items = self._build(handlers, descriptors)

        self.assertEqual(
            recorder.log,
            [
                ("new", "menu0"),
                ("new", "menu1"),
                ("menu0", "AppendSubMenu", "menu1", "T[Save As]"),
                ("menu1", "Append", -1, "T[Text]"),
                ("menu0", "Append", -1, "T[Close]"),
                ("menu0", "Bind", "EVT_MENU", "menu1:T[Text]"),
                ("menu0", "Bind", "EVT_MENU", "menu0:T[Close]"),
            ],
        )
        self.assertEqual(list(items), ["save_as", "close"])
        recorder.binds[0][2]("event")
        recorder.binds[1][2]("event")
        self.assertEqual(calls.mock_calls, [call.save_as("txt"), call.close("event")])

    def test_default_descriptors_are_the_action_menu_descriptors(self) -> None:
        _calls, handlers = self._handlers()

        default_recorder, _items = self._build(handlers)
        explicit_recorder, _items = self._build(handlers, get_document_menu_descriptors())

        self.assertEqual(default_recorder.log, explicit_recorder.log)

    def test_apply_state_enables_in_given_order(self) -> None:
        log = []
        items = {name: RecordedItem(log, name) for name in ("a", "b", "c")}

        apply_document_menu_state(items, {"c": True, "a": False})

        self.assertEqual(log, [("Enable", "c", True), ("Enable", "a", False)])

    def test_apply_state_rejects_unknown_action(self) -> None:
        items = {"a": RecordedItem([], "a")}

        with self.assertRaises(KeyError):
            apply_document_menu_state(items, {"a": True, "missing": False})

    def test_menu_builder_does_not_import_wx(self) -> None:
        tree = ast.parse(MENU_BUILDER_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])

        self.assertNotIn("wx", imported)
        self.assertNotIn("gui", imported)


if __name__ == "__main__":
    unittest.main()
