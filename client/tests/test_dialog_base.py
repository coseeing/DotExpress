import ast
import dataclasses
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from shared.name_validation import NameValidationError
from tests import wx_stub
from ui import dialog_base
from ui.dialog_base import (
    ContextManagedDialog,
    NameDialogBase,
    NameDialogMessages,
    SingletonDialogMixin,
)

DIALOG_BASE_PATH = Path(__file__).resolve().parents[1] / "ui" / "dialog_base.py"


class PlainDialog:
    """Like the ``wx.Dialog`` of the dialog-validation, speech and display stubs."""


class MaskingDialog(wx_stub.RecordingWidget):
    """Like the ``wx.Dialog`` of the settings stubs: missing attributes become no-ops."""


DIALOG_BASES = (PlainDialog, MaskingDialog)

TEST_MESSAGES = NameDialogMessages(
    empty="P2-1 test: empty",
    too_long="P2-1 test: too long",
    invalid="P2-1 test: invalid",
    reserved="P2-1 test: {name} is reserved",
    reserved_name="default",
)


def name_dialog_class(base, normalizer):
    class FakeNameDialog(NameDialogBase, base):
        normalize_name = staticmethod(normalizer)
        name_messages = TEST_MESSAGES

        def _show_name_error(self, message: str) -> None:
            self.events.append(("error", message))

    return FakeNameDialog


def make_name_dialog(base, normalizer, text: str):
    dialog = name_dialog_class(base, normalizer)()
    dialog.events = []
    dialog.name_ctrl = Mock()
    dialog.name_ctrl.GetValue.return_value = text
    dialog.name_ctrl.SetValue.side_effect = lambda value: dialog.events.append(("SetValue", value))
    dialog.name_ctrl.SetFocus.side_effect = lambda: dialog.events.append(("SetFocus",))
    return dialog


def raising(error):
    def normalizer(name: str) -> str:
        raise error

    return normalizer


def singleton_class(base, dead_types=()):
    class FakeSingleton(SingletonDialogMixin, base):
        _instance = None
        dead_window_error_types = dead_types

    return FakeSingleton


class DeadWindowError(Exception):
    pass


class ContextManagedDialogTest(unittest.TestCase):
    def test_with_returns_the_dialog_and_destroys_it_once(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = type("Combined", (ContextManagedDialog, base), {})()
                dialog.Destroy = Mock()
                with dialog as entered:
                    self.assertIs(entered, dialog)
                    dialog.Destroy.assert_not_called()
                dialog.Destroy.assert_called_once_with()
                self.assertIsNone(dialog.__exit__(None, None, None))

    def test_with_destroys_the_dialog_and_propagates_an_exception(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = type("Combined", (ContextManagedDialog, base), {})()
                dialog.Destroy = Mock()
                error = RuntimeError("boom")
                with self.assertRaises(RuntimeError) as caught:
                    with dialog:
                        raise error
                self.assertIs(caught.exception, error)
                dialog.Destroy.assert_called_once_with()


class MixinShapeTest(unittest.TestCase):
    def test_mixins_have_no_constructor_slots_or_metaclass_and_go_first(self) -> None:
        for mixin in (ContextManagedDialog, NameDialogBase, SingletonDialogMixin):
            with self.subTest(mixin=mixin.__name__):
                self.assertIs(type(mixin), type)
                for name in ("__init__", "__new__", "__slots__"):
                    self.assertNotIn(name, vars(mixin))
                for base in DIALOG_BASES:
                    combined = type("Combined", (mixin, base), {})
                    self.assertEqual(combined.__mro__[1], mixin)
                    self.assertLess(combined.__mro__.index(mixin), combined.__mro__.index(base))


class NameDialogMessagesTest(unittest.TestCase):
    def test_message_for_each_code_is_translated(self) -> None:
        messages = NameDialogMessages(
            empty="Please enter the dictionary name.",
            too_long="Dictionary name must be 1 to 32 characters.",
            invalid="Dictionary name is not a valid Windows file name.",
            reserved='Dictionary name "{name}" is reserved.',
            reserved_name="default",
        )

        self.assertEqual(messages.message_for("empty"), "請輸入字典名稱。")
        self.assertEqual(messages.message_for("too_long"), "字典名稱長度需為 1 到 32 個字元。")
        self.assertEqual(messages.message_for("invalid"), "字典名稱不是有效的 Windows 檔名。")
        self.assertEqual(messages.message_for("reserved"), "字典名稱「default」為保留名稱。")

    def test_reserved_without_a_reserved_message_and_unknown_codes_are_invalid(self) -> None:
        messages = NameDialogMessages(empty="e", too_long="t", invalid="i")

        self.assertIsNone(messages.reserved)
        self.assertEqual(messages.reserved_name, "")
        self.assertEqual(messages.message_for("reserved"), "i")
        self.assertEqual(messages.message_for("something_else"), "i")

    def test_messages_are_translated_when_shown_then_formatted(self) -> None:
        translations = {"P2-1 test: {name} is reserved": "{name} reserved (translated)"}
        with patch.object(dialog_base, "_", side_effect=lambda text: translations.get(text, text.upper())) as translate:
            self.assertEqual(TEST_MESSAGES.message_for("reserved"), "default reserved (translated)")
            self.assertEqual(TEST_MESSAGES.message_for("empty"), "P2-1 TEST: EMPTY")

        self.assertEqual(translate.call_args_list, [call("P2-1 test: {name} is reserved"), call("P2-1 test: empty")])

    def test_messages_are_frozen(self) -> None:
        with self.assertRaises(dataclasses.FrozenInstanceError):
            TEST_MESSAGES.empty = "changed"


class NameDialogBaseTest(unittest.TestCase):
    def test_validate_name_maps_each_typed_code_to_its_message(self) -> None:
        cases = (
            ("empty", "P2-1 test: empty"),
            ("too_long", "P2-1 test: too long"),
            ("invalid", "P2-1 test: invalid"),
            ("reserved", "P2-1 test: default is reserved"),
        )
        for base in DIALOG_BASES:
            for code, message in cases:
                with self.subTest(base=base.__name__, code=code):
                    dialog = make_name_dialog(base, raising(NameValidationError(code, "English")), "x")
                    self.assertEqual(dialog._validate_name("x"), message)

    def test_a_plain_value_error_is_reported_as_invalid(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = make_name_dialog(base, raising(ValueError("Name cannot exceed 32 characters.")), "x")
                self.assertEqual(dialog._validate_name("x"), "P2-1 test: invalid")

    def test_other_exceptions_propagate(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = make_name_dialog(base, raising(TypeError("bug")), "x")
                with self.assertRaisesRegex(TypeError, "^bug$"):
                    dialog._validate_name("x")

    def test_a_valid_name_has_no_message_and_the_normalizer_sees_the_raw_text(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                seen = []

                def normalizer(name: str) -> str:
                    seen.append(name)
                    return name.strip()

                dialog = make_name_dialog(base, normalizer, " name　")
                self.assertIsNone(dialog._validate_name(" name　"))
                self.assertEqual(seen, [" name　"])

    def test_on_ok_shows_the_error_then_focuses_and_does_not_skip(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = make_name_dialog(base, raising(NameValidationError("empty", "English")), "")
                event = Mock()
                dialog._on_ok(event)
                self.assertEqual(dialog.events, [("error", "P2-1 test: empty"), ("SetFocus",)])
                event.Skip.assert_not_called()

    def test_on_ok_writes_back_the_normalized_name_then_skips(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = make_name_dialog(base, str.strip, " name ")
                event = Mock()
                event.Skip.side_effect = lambda: dialog.events.append(("Skip",))
                dialog._on_ok(event)
                self.assertEqual(dialog.events, [("SetValue", "name"), ("Skip",)])

    def test_hooks_must_be_provided_by_the_subclass(self) -> None:
        with self.assertRaises(NotImplementedError):
            NameDialogBase.normalize_name("name")
        with self.assertRaises(NotImplementedError):
            NameDialogBase._show_name_error(object(), "message")


class SingletonDialogMixinTest(unittest.TestCase):
    def test_raise_existing_returns_none_for_an_empty_slot(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                self.assertIsNone(singleton_class(base)._raise_existing())

    def test_raise_existing_raises_the_open_dialog_in_order(self) -> None:
        for base in DIALOG_BASES:
            for prepare, expected in (
                (None, [call.Iconize(False), call.Raise(), call.SetFocus()]),
                (lambda dialog: dialog.prepare(), [call.Iconize(False), call.prepare(), call.Raise(), call.SetFocus()]),
            ):
                with self.subTest(base=base.__name__, prepare=prepare is not None):
                    dialog_class = singleton_class(base)
                    existing = Mock()
                    dialog_class._instance = existing
                    self.assertIs(dialog_class._raise_existing(prepare), existing)
                    self.assertIs(dialog_class._instance, existing)
                    self.assertEqual(existing.mock_calls, expected)

    def test_raise_existing_clears_the_slot_after_a_dead_window_error(self) -> None:
        errors = (
            DeadWindowError("no phrase needed"),
            RuntimeError("WRAPPED C/C++ OBJECT of type Dialog"),
            RuntimeError("window has been deleted"),
            ReferenceError("already deleted"),
            RuntimeError("destroyed"),
        )
        for base in DIALOG_BASES:
            for error in errors:
                with self.subTest(base=base.__name__, error=repr(error)):
                    dialog_class = singleton_class(base, (DeadWindowError,))
                    existing = Mock()
                    existing.Raise.side_effect = error
                    dialog_class._instance = existing
                    self.assertIsNone(dialog_class._raise_existing())
                    self.assertIsNone(dialog_class._instance)

    def test_raise_existing_reraises_other_errors_and_keeps_the_slot(self) -> None:
        errors = (
            RuntimeError("unexpected"),
            ReferenceError("weakly-referenced object no longer exists"),
            DeadWindowError("not registered as dead"),
            KeyError("other"),
        )
        for base in DIALOG_BASES:
            for error in errors:
                with self.subTest(base=base.__name__, error=repr(error)):
                    dialog_class = singleton_class(base)
                    existing = Mock()
                    existing.Iconize.side_effect = error
                    dialog_class._instance = existing
                    with self.assertRaises(type(error)) as caught:
                        dialog_class._raise_existing()
                    self.assertIs(caught.exception, error)
                    self.assertIs(dialog_class._instance, existing)

    def test_is_destroyed_window_error(self) -> None:
        dialog_class = singleton_class(PlainDialog, (DeadWindowError,))
        cases = (
            (DeadWindowError(), True),
            (RuntimeError("Has Been Deleted"), True),
            (ReferenceError("wrapped C/C++ object"), True),
            (RuntimeError("other"), False),
            (ReferenceError(""), False),
            (ValueError("destroyed"), False),
        )
        for error, expected in cases:
            with self.subTest(error=repr(error)):
                self.assertIs(dialog_class._is_destroyed_window_error(error), expected)

    def test_show_new_sets_the_slot_before_showing(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog_class = singleton_class(base)
                dialog = dialog_class()
                shown = []
                dialog.Show = lambda: shown.append(dialog_class.__dict__["_instance"] is dialog)
                self.assertIs(dialog_class._show_new(dialog), dialog)
                self.assertIs(dialog_class._instance, dialog)
                self.assertEqual(shown, [True])

    def test_a_subclass_without_its_own_slot_does_not_see_the_parent_dialog(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                parent_class = singleton_class(base)
                existing = Mock()
                parent_class._instance = existing
                child_class = type("Child", (parent_class,), {})

                self.assertIsNone(child_class._raise_existing())
                self.assertEqual(existing.mock_calls, [])
                child = child_class()
                child.Show = Mock()
                child_class._show_new(child)
                self.assertIs(child_class.__dict__["_instance"], child)
                self.assertIs(parent_class._instance, existing)

    def test_destroy_clears_only_its_own_class_slot(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                parent_class = singleton_class(base)
                child_class = type("Child", (parent_class,), {"_instance": None})
                parent_dialog = parent_class()
                parent_dialog.Destroy = Mock()
                child = child_class()
                child.Destroy = Mock()
                parent_class._instance = parent_dialog
                child_class._instance = child

                child._destroy()
                self.assertIsNone(child_class._instance)
                self.assertIs(parent_class._instance, parent_dialog)
                child.Destroy.assert_called_once_with()

                other = child_class()
                other.Destroy = Mock()
                child_class._instance = child
                other._destroy()
                self.assertIs(child_class._instance, child)
                other.Destroy.assert_called_once_with()
                parent_dialog.Destroy.assert_not_called()

    def test_open_instance_returns_the_slot_without_touching_the_dialog(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog_class = singleton_class(base)
                self.assertIsNone(dialog_class.open_instance())
                existing = Mock()
                dialog_class._instance = existing
                self.assertIs(dialog_class.open_instance(), existing)
                self.assertIs(dialog_class._instance, existing)
                self.assertEqual(existing.mock_calls, [])

    def test_open_instance_of_a_subclass_without_its_own_slot_is_none(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                parent_class = singleton_class(base)
                existing = Mock()
                parent_class._instance = existing
                child_class = type("Child", (parent_class,), {})

                self.assertIsNone(child_class.open_instance())
                self.assertIs(parent_class.open_instance(), existing)
                self.assertEqual(existing.mock_calls, [])

    def test_open_instance_is_none_after_destroy(self) -> None:
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog_class = singleton_class(base)
                dialog = dialog_class()
                dialog.Show = Mock()
                dialog.Destroy = Mock()
                dialog_class._show_new(dialog)
                self.assertIs(dialog_class.open_instance(), dialog)

                dialog._destroy()
                self.assertIsNone(dialog_class.open_instance())


class DialogBaseImportTest(unittest.TestCase):
    def test_module_imports_only_the_standard_library_i18n_and_name_validation(self) -> None:
        tree = ast.parse(DIALOG_BASE_PATH.read_text(encoding="utf-8"), filename=str(DIALOG_BASE_PATH))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add("." * node.level + (node.module or ""))

        self.assertEqual(imported, {"__future__", "dataclasses", "typing", "i18n", "shared.name_validation"})
        self.assertEqual({name.split(".")[0] for name in imported} & {"wx", "gui", "dialog", "settings"}, set())


if __name__ == "__main__":
    unittest.main()
