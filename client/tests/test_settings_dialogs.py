from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from tests import wx_stub

_SCOPE = wx_stub.StubScope(wx_stub.settings_dialog_stubs(), isolate=("settings.dialogs",))
with _SCOPE.loading():
    import wx

    from settings.dialogs import (
        MultiCategorySettingsDialog,
        SettingsPanel,
        SettingsPanelAccessible,
    )

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate

import config
import i18n
from settings.state import DotExpressSettingsSnapshot
from settings.translation import TranslationSettings
from settings.view import ViewSettings


class FakeChoice:
    def __init__(self, selection):
        self._selection = selection

    def GetSelection(self):
        return self._selection


class FakeSpin:
    def __init__(self, value):
        self._value = value

    def GetValue(self):
        return self._value


class FakeListCtrl:
    def __init__(self, selected_index=-1):
        self.selected_index = selected_index
        self.focused_index = -1
        self.selected_calls = []

    def GetFirstSelected(self):
        return self.selected_index

    def Select(self, index):
        self.selected_index = index
        self.selected_calls.append(index)

    def Focus(self, index):
        self.focused_index = index


class FakeListEvent:
    def __init__(self, index):
        self._index = index

    def GetIndex(self):
        return self._index


def make_snapshot(font_size=40):
    return DotExpressSettingsSnapshot.create(
        translation=TranslationSettings("unicode", 40, "default"),
        translation_tables={},
        view=ViewSettings(font_size, "light", "default"),
    )


def make_dialog_without_wx_constructor():
    from settings.dialogs import DotExpressSettingsDialog

    dialog = object.__new__(DotExpressSettingsDialog)
    dialog.base_title = "DotExpress Settings"
    dialog.title_template = "DotExpress Settings: {category}"
    dialog.snapshot = make_snapshot()
    dialog.commit = Mock()
    dialog.select_category = Mock()
    dialog.Destroy = Mock()
    dialog.panel_instances = {}
    return dialog


class SettingsPanelAccessibleTest(unittest.TestCase):
    def test_exposes_property_page_role_and_description(self) -> None:
        panel = Mock(panel_description="View settings")
        accessible = SettingsPanelAccessible(panel)
        self.assertEqual(
            accessible.GetRole(0),
            (wx.ACC_OK, wx.ROLE_SYSTEM_PROPERTYPAGE),
        )
        self.assertEqual(
            accessible.GetDescription(0),
            (wx.ACC_OK, "View settings"),
        )


class SettingsPanelTest(unittest.TestCase):
    def test_uses_title_for_accessible_label(self) -> None:
        from settings.dialogs import SettingsPanel

        class TestPanel(SettingsPanel):
            title = "Translation"

            def make_settings(self) -> None:
                return None

            def on_save(self, snapshot):
                return snapshot

            def load_snapshot(self, snapshot) -> None:
                return None

        panel = TestPanel(None, Mock())

        self.assertEqual(panel.label, "Translation")


class TextProcessingDialogTest(unittest.TestCase):
    def make_dialog(self):
        from settings.dialogs import TextProcessingDialog

        dialog = object.__new__(TextProcessingDialog)
        dialog.script_path = Path("dictionary/preprocessing.py")
        dialog.editor = Mock()
        dialog.Destroy = Mock()
        return dialog

    def test_initial_size_title_and_accessible_editor_name(self) -> None:
        from settings.dialogs import TextProcessingDialog

        with (
            patch(
                "settings.dialogs.load_preprocessing_script",
                return_value="def main(text):\n    return text\n",
            ),
            patch("settings.dialogs._", side_effect=lambda text: text),
        ):
            dialog = TextProcessingDialog(
                None,
                script_path=Path("dictionary/preprocessing.py"),
            )

        self.assertEqual(dialog.size, (720, 440))
        self.assertEqual(dialog.title, "Text Processing")
        self.assertEqual(dialog.editor.GetName(), "Text Processing Python Code")

    def test_apply_saves_editor_source(self) -> None:
        dialog = self.make_dialog()
        dialog.editor.GetValue.return_value = "def main(text):\n    return text\n"
        with patch("settings.dialogs.save_preprocessing_script") as save:
            self.assertTrue(dialog.on_apply())
        save.assert_called_once_with(dialog.script_path, dialog.editor.GetValue.return_value)

    def test_apply_failure_keeps_dialog_open_and_focuses_editor(self) -> None:
        dialog = self.make_dialog()
        dialog.editor.GetValue.return_value = "def main(:\n"
        with (
            patch(
                "settings.dialogs.save_preprocessing_script",
                side_effect=SyntaxError("invalid syntax"),
            ),
            patch("settings.dialogs.wx.MessageBox") as message_box,
        ):
            self.assertFalse(dialog.on_apply())
        dialog.Destroy.assert_not_called()
        dialog.editor.SetFocus.assert_called_once_with()
        message_box.assert_called_once()

    def test_ok_destroys_only_after_successful_apply(self) -> None:
        dialog = self.make_dialog()
        dialog.on_apply = Mock(return_value=True)
        dialog._destroy = Mock()
        dialog.on_ok()
        dialog._destroy.assert_called_once_with()

    def test_cancel_does_not_save(self) -> None:
        dialog = self.make_dialog()
        dialog._destroy = Mock()
        with patch("settings.dialogs.save_preprocessing_script") as save:
            dialog.on_cancel()
        save.assert_not_called()
        dialog._destroy.assert_called_once_with()

    def test_show_singleton_reuses_live_dialog(self) -> None:
        from settings.dialogs import TextProcessingDialog

        existing = Mock()
        original = TextProcessingDialog._instance
        TextProcessingDialog._instance = existing
        try:
            result = TextProcessingDialog.show_singleton(
                parent=Mock(),
                script_path=Path("dictionary/preprocessing.py"),
            )
        finally:
            TextProcessingDialog._instance = original

        self.assertIs(result, existing)
        existing.Iconize.assert_called_once_with(False)
        existing.Raise.assert_called_once_with()
        existing.SetFocus.assert_called_once_with()

    def test_show_singleton_reraises_unexpected_existing_dialog_error(self) -> None:
        from settings.dialogs import TextProcessingDialog

        existing = Mock()
        existing.Iconize.side_effect = RuntimeError("unexpected")
        original = TextProcessingDialog._instance
        TextProcessingDialog._instance = existing
        try:
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                TextProcessingDialog.show_singleton(
                    parent=Mock(),
                    script_path=Path("dictionary/preprocessing.py"),
                )
            self.assertIs(TextProcessingDialog._instance, existing)
        finally:
            TextProcessingDialog._instance = original


class MultiCategorySettingsDialogTest(unittest.TestCase):
    def test_rejects_initial_category_outside_registered_categories(self) -> None:
        class RegisteredPanel(SettingsPanel):
            pass

        class UnregisteredPanel(SettingsPanel):
            pass

        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog.category_classes = [RegisteredPanel]
        with self.assertRaises(ValueError):
            dialog._get_initial_category_index(UnregisteredPanel)

    def test_category_change_deactivates_old_panel_and_activates_new_panel(self) -> None:
        old_panel = Mock()
        new_panel = Mock()
        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog.current_panel = old_panel
        dialog._get_category_panel = Mock(return_value=new_panel)
        dialog._layout_container = Mock()
        dialog._after_category_change = Mock()

        dialog._change_category(1)

        old_panel.on_panel_deactivated.assert_called_once_with()
        new_panel.on_panel_activated.assert_called_once_with()
        dialog._after_category_change.assert_called_once_with(new_panel)

    def test_category_cycle_wraps_in_both_directions(self) -> None:
        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog.category_classes = [Mock, Mock, Mock]
        self.assertEqual(dialog._cycled_category_index(2, 1), 0)
        self.assertEqual(dialog._cycled_category_index(0, -1), 2)

    def test_current_category_index_uses_first_selected_list_ctrl_api(self) -> None:
        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog.category_list = FakeListCtrl(selected_index=2)

        self.assertEqual(dialog._current_category_index(), 2)

    def test_category_selected_uses_event_index(self) -> None:
        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog._change_category = Mock()

        dialog._on_category_selected(FakeListEvent(1))

        dialog._change_category.assert_called_once_with(1)

    def test_category_selected_ignores_duplicate_events_for_active_category(self) -> None:
        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog._active_category_index = 1
        dialog._change_category = Mock()

        dialog._on_category_selected(FakeListEvent(1))

        dialog._change_category.assert_not_called()

    def test_layout_uses_headerless_list_ctrl_and_explicit_categories_name(self) -> None:
        import settings.dialogs as dialogs_module

        saved_modules = {
            name: sys.modules.get(name)
            for name in ("wx", "wx.lib", "wx.lib.scrolledpanel")
        }
        for name in saved_modules:
            sys.modules.pop(name, None)
        sys.modules.update(wx_stub.settings_dialog_stubs())
        fresh_wx = sys.modules["wx"]

        class DummyCategory:
            title = "Translation"

        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog.initial_category = None
        dialog.category_classes = [DummyCategory]
        dialog.panel_instances = {}
        dialog.current_panel = None
        dialog._active_category_index = None
        dialog.Bind = Mock()
        dialog.SetSizer = Mock()
        dialog._change_category = Mock()

        try:
            with patch.object(dialogs_module, "wx", fresh_wx):
                with patch.object(
                    dialogs_module,
                    "ScrolledPanel",
                    fresh_wx.lib.scrolledpanel.ScrolledPanel,
                ):
                    with patch("settings.dialogs._", side_effect=lambda text: text):
                        dialog._build_layout()

            self.assertEqual(dialog.category_label.label, "&Categories:")
            self.assertEqual(dialog.category_list.GetName(), "Categories")
            self.assertTrue(dialog.category_list.style & fresh_wx.LC_NO_HEADER)
            self.assertEqual(dialog.category_list.min_size, (150, 10))
            self.assertEqual(dialog.category_list.selected_index, 0)
            self.assertEqual(dialog.category_list.focused_index, 0)
            dialog._change_category.assert_called_once_with(0)
        finally:
            for name, module in saved_modules.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module


class TranslationSettingsPanelTest(unittest.TestCase):
    def test_translation_panel_collects_controls_without_mutating_baseline(self) -> None:
        from settings.dialogs import TranslationSettingsPanel

        baseline = make_snapshot()
        panel = object.__new__(TranslationSettingsPanel)
        panel.output_choice = FakeChoice(1)
        panel.width_spin = FakeSpin(52)
        panel.dictionary_choice = FakeChoice(1)
        panel.dictionary_names = ["default", "math"]

        result = panel.on_save(baseline)

        self.assertEqual(result.translation, TranslationSettings("ascii", 52, "math"))
        self.assertEqual(baseline.translation, TranslationSettings("unicode", 40, "default"))


class TranslationTablesPanelTest(unittest.TestCase):
    def test_tables_panel_requires_default_and_math(self) -> None:
        from settings.dialogs import TranslationTablesPanel

        panel = object.__new__(TranslationTablesPanel)
        panel._selected_file_name = Mock(
            side_effect=lambda key: "" if key == "default" else "UEB"
        )
        self.assertFalse(panel.is_valid())

    def test_tables_panel_validation_points_to_missing_required_control(self) -> None:
        from settings.dialogs import TranslationTablesPanel

        default_choice = Mock()
        math_choice = Mock()
        panel = object.__new__(TranslationTablesPanel)
        panel._choice_controls = {
            "default": default_choice,
            "math": math_choice,
        }
        panel._selected_file_name = Mock(
            side_effect=lambda key: "" if key == "default" else "UEB"
        )

        with patch("settings.dialogs._", side_effect=lambda text: text):
            message, focus_control = panel.validation_error()

        self.assertEqual(
            message,
            "Please select a value for Default Translation Table.",
        )
        self.assertIs(focus_control, default_choice)


class ViewSettingsPanelTest(unittest.TestCase):
    def test_view_panel_tracks_font_size_dirty_state(self) -> None:
        from settings.dialogs import ViewSettingsPanel

        panel = object.__new__(ViewSettingsPanel)
        panel.font_size_dirty = False
        panel._on_font_size_changed(None)
        self.assertTrue(panel.font_size_dirty)


class DotExpressSettingsDialogFlowTest(unittest.TestCase):
    def test_apply_validates_all_panels_before_commit(self) -> None:
        dialog = make_dialog_without_wx_constructor()
        invalid = Mock(
            is_valid=Mock(return_value=False),
            validation_error=Mock(return_value=None),
        )
        valid = Mock(
            is_valid=Mock(return_value=True),
            validation_error=Mock(return_value=None),
        )
        dialog.panel_instances = {0: valid, 1: invalid}

        dialog.on_apply()

        dialog.commit.assert_not_called()
        valid.on_save.assert_not_called()

    def test_apply_shows_message_and_focuses_missing_required_translation_table(self) -> None:
        from settings.dialogs import TranslationTablesPanel

        dialog = make_dialog_without_wx_constructor()
        default_choice = Mock()
        panel = object.__new__(TranslationTablesPanel)
        panel._choice_controls = {
            "default": default_choice,
            "math": Mock(),
        }
        panel._selected_file_name = Mock(
            side_effect=lambda key: "" if key == "default" else "UEB"
        )
        dialog.panel_instances = {1: panel}

        with patch("settings.dialogs._", side_effect=lambda text: text):
            with patch("settings.dialogs.wx.MessageBox") as message_box:
                result = dialog.on_apply()

        self.assertFalse(result)
        dialog.select_category.assert_called_once_with(TranslationTablesPanel)
        message_box.assert_called_once_with(
            "Please select a value for Default Translation Table.",
            "DotExpress Settings",
            wx.OK | wx.ICON_ERROR,
            dialog,
        )
        default_choice.SetFocus.assert_called_once_with()
        dialog.commit.assert_not_called()

    def test_successful_apply_reloads_normalized_baseline(self) -> None:
        dialog = make_dialog_without_wx_constructor()
        committed = make_snapshot(font_size=18)
        dialog.commit = Mock(return_value=committed)
        panel = Mock(
            is_valid=Mock(return_value=True),
            validation_error=Mock(return_value=None),
        )
        panel.on_save.return_value = committed
        dialog.panel_instances = {0: panel}

        dialog.on_apply()

        self.assertEqual(dialog.snapshot, committed)
        panel.load_snapshot.assert_called_once_with(committed)

    def test_show_singleton_reraises_unexpected_existing_dialog_errors(self) -> None:
        from settings.dialogs import DotExpressSettingsDialog

        class TestDialog(DotExpressSettingsDialog):
            category_classes = DotExpressSettingsDialog.category_classes
            _instance = None

            def __init__(self, *args, **kwargs):
                self.shown = False

            def Show(self):
                self.shown = True

        TestDialog._instance = Mock(
            Iconize=Mock(),
            Raise=Mock(side_effect=ValueError("boom")),
            SetFocus=Mock(),
            select_category=Mock(),
        )

        with self.assertRaisesRegex(ValueError, "boom"):
            TestDialog.show_singleton(
                parent=None,
                snapshot=make_snapshot(),
                dictionary_names=["default"],
                commit=Mock(),
            )

    def test_sync_open_font_size_updates_snapshot_before_view_panel_exists(self) -> None:
        from settings.dialogs import DotExpressSettingsDialog

        dialog = make_dialog_without_wx_constructor()
        dialog.snapshot = make_snapshot(font_size=12)
        dialog.panel_instances = {}
        original_instance = DotExpressSettingsDialog._instance
        DotExpressSettingsDialog._instance = dialog
        try:
            DotExpressSettingsDialog.sync_open_font_size(20)
        finally:
            DotExpressSettingsDialog._instance = original_instance

        self.assertEqual(dialog.snapshot.view.font_size, 20)

    def test_sync_open_font_size_keeps_dirty_view_panel_draft(self) -> None:
        from settings.dialogs import DotExpressSettingsDialog, ViewSettingsPanel

        dialog = make_dialog_without_wx_constructor()
        dialog.snapshot = make_snapshot(font_size=12)
        view_panel = object.__new__(ViewSettingsPanel)
        view_panel.font_size_dirty = True
        view_panel.font_size_spin = Mock()
        dialog.panel_instances = {2: view_panel}
        original_instance = DotExpressSettingsDialog._instance
        DotExpressSettingsDialog._instance = dialog
        try:
            DotExpressSettingsDialog.sync_open_font_size(20)
        finally:
            DotExpressSettingsDialog._instance = original_instance

        self.assertEqual(dialog.snapshot.view.font_size, 12)
        view_panel.font_size_spin.SetValue.assert_not_called()

    def test_title_format_uses_localizable_template(self) -> None:
        from settings.dialogs import DotExpressSettingsDialog

        dialog = object.__new__(DotExpressSettingsDialog)
        dialog.title_template = "DotExpress 設定：{category}"

        self.assertEqual(dialog._format_title("轉譯"), "DotExpress 設定：轉譯")


def dead_window_errors():
    return (
        wx.PyDeadObjectError("dead"),
        RuntimeError("Wrapped C/C++ object of type Dialog"),
        RuntimeError("the window has been deleted"),
        RuntimeError("window already deleted"),
        RuntimeError("Window Destroyed"),
        ReferenceError("weakly-referenced object has been deleted"),
    )


class _SingletonCharacterization:
    """``show_singleton`` and ``_destroy`` of one singleton settings dialog (P2-1 characterization)."""

    def dialog_class(self):
        raise NotImplementedError

    def show_kwargs(self) -> dict:
        raise NotImplementedError

    def expected_init_kwargs(self, kwargs: dict) -> dict:
        """The keyword arguments ``show_singleton`` passes to the constructor for ``kwargs``."""
        return kwargs

    def show(self, **overrides):
        return self.dialog_class().show_singleton(**{**self.show_kwargs(), **overrides})

    def slot(self, value):
        return patch.object(self.dialog_class(), "_instance", value)

    def recording_constructor(self, events, error=None):
        dialog_class = self.dialog_class()

        def fake_init(dialog, *args, **kwargs):
            events.append(("init", args, kwargs))
            if error is not None:
                raise error

        def fake_show(dialog):
            events.append(("Show", dialog_class._instance is dialog))

        return patch.multiple(dialog_class, __init__=fake_init, Show=fake_show)

    def test_show_singleton_builds_forwards_and_shows_a_new_dialog(self) -> None:
        dialog_class = self.dialog_class()
        events = []
        with self.slot(None), self.recording_constructor(events):
            result = self.show()
            self.assertIs(dialog_class._instance, result)

        self.assertIs(type(result), dialog_class)
        kwargs = self.show_kwargs()
        parent = kwargs.pop("parent")
        self.assertEqual(events, [("init", (parent,), self.expected_init_kwargs(kwargs)), ("Show", True)])

    def test_show_singleton_raises_the_live_dialog_in_order(self) -> None:
        existing = Mock()
        events = []
        with self.slot(existing), self.recording_constructor(events):
            result = self.show()
            self.assertIs(self.dialog_class()._instance, existing)

        self.assertIs(result, existing)
        self.assertEqual(existing.mock_calls, [call.Iconize(False), call.Raise(), call.SetFocus()])
        self.assertEqual(events, [])

    def test_show_singleton_rebuilds_after_a_dead_window_error(self) -> None:
        dialog_class = self.dialog_class()
        for error in dead_window_errors():
            with self.subTest(error=repr(error)):
                existing = Mock()
                existing.Iconize.side_effect = error
                events = []
                with self.slot(existing), self.recording_constructor(events):
                    result = self.show()
                    self.assertIs(dialog_class._instance, result)

                self.assertIsNot(result, existing)
                self.assertEqual(existing.mock_calls, [call.Iconize(False)])
                self.assertEqual([event[0] for event in events], ["init", "Show"])

    def test_show_singleton_reraises_a_live_window_error_and_keeps_the_slot(self) -> None:
        dialog_class = self.dialog_class()
        for error in (ReferenceError("weakly-referenced object no longer exists"), RuntimeError("unexpected")):
            with self.subTest(error=repr(error)):
                existing = Mock()
                existing.Iconize.side_effect = error
                events = []
                with self.slot(existing), self.recording_constructor(events):
                    with self.assertRaises(type(error)) as caught:
                        self.show()
                    self.assertIs(dialog_class._instance, existing)

                self.assertIs(caught.exception, error)
                self.assertEqual(events, [])

    def test_show_singleton_propagates_other_exceptions_and_keeps_the_slot(self) -> None:
        dialog_class = self.dialog_class()
        existing = Mock()
        existing.Raise.side_effect = KeyError("boom")
        events = []
        with self.slot(existing), self.recording_constructor(events):
            with self.assertRaises(KeyError):
                self.show()
            self.assertIs(dialog_class._instance, existing)

        self.assertEqual(existing.mock_calls, [call.Iconize(False), call.Raise()])
        self.assertEqual(events, [])

    def test_constructor_failure_leaves_the_slot_empty(self) -> None:
        dialog_class = self.dialog_class()
        events = []
        with self.slot(None), self.recording_constructor(events, error=OSError("unreadable")):
            with self.assertRaises(OSError):
                self.show()
            self.assertIsNone(dialog_class._instance)

        self.assertEqual([event[0] for event in events], ["init"])

    def test_destroy_clears_its_own_slot_and_destroys(self) -> None:
        dialog_class = self.dialog_class()
        dialog = object.__new__(dialog_class)
        dialog.Destroy = Mock()
        with self.slot(dialog):
            dialog._destroy()
            self.assertIsNone(dialog_class._instance)

        dialog.Destroy.assert_called_once_with()

    def test_destroy_keeps_another_dialog_in_the_slot(self) -> None:
        dialog_class = self.dialog_class()
        dialog = object.__new__(dialog_class)
        dialog.Destroy = Mock()
        other = Mock()
        with self.slot(other):
            dialog._destroy()
            self.assertIs(dialog_class._instance, other)

        dialog.Destroy.assert_called_once_with()
        self.assertEqual(other.mock_calls, [])


class TextProcessingSingletonTest(_SingletonCharacterization, unittest.TestCase):
    def dialog_class(self):
        from settings.dialogs import TextProcessingDialog

        return TextProcessingDialog

    def show_kwargs(self) -> dict:
        return {"parent": "parent-window", "script_path": "dictionary/preprocessing.py"}


class DotExpressSettingsSingletonTest(_SingletonCharacterization, unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = make_snapshot()
        self.commit = Mock()

    def dialog_class(self):
        from settings.dialogs import DotExpressSettingsDialog

        return DotExpressSettingsDialog

    def show_kwargs(self) -> dict:
        return {
            "parent": "parent-window",
            "snapshot": self.snapshot,
            "dictionary_names": ["default", "math"],
            "commit": self.commit,
        }

    def expected_init_kwargs(self, kwargs: dict) -> dict:
        return {**kwargs, "initial_category": None}

    def test_show_singleton_forwards_the_initial_category_to_a_new_dialog(self) -> None:
        dialog_class = self.dialog_class()
        category = dialog_class.category_classes[1]
        events = []
        with self.slot(None), self.recording_constructor(events):
            self.show(initial_category=category)

        kwargs = self.show_kwargs()
        parent = kwargs.pop("parent")
        self.assertEqual(events, [("init", (parent,), {**kwargs, "initial_category": category}), ("Show", True)])

    def test_show_singleton_selects_the_initial_category_before_raising(self) -> None:
        category = self.dialog_class().category_classes[2]
        existing = Mock()
        with self.slot(existing):
            result = self.show(initial_category=category)

        self.assertIs(result, existing)
        self.assertEqual(
            existing.mock_calls,
            [call.Iconize(False), call.select_category(category), call.Raise(), call.SetFocus()],
        )

    def test_show_singleton_rejects_an_unregistered_category_before_reading_the_slot(self) -> None:
        dialog_class = self.dialog_class()
        existing = Mock()
        events = []
        with self.slot(existing), self.recording_constructor(events):
            with self.assertRaisesRegex(ValueError, "^initial_category is not registered$"):
                self.show(initial_category=object())
            self.assertIs(dialog_class._instance, existing)

        self.assertEqual(existing.mock_calls, [])
        self.assertEqual(events, [])


class SingletonSlotIndependenceTest(unittest.TestCase):
    def test_the_two_singleton_dialogs_keep_separate_slots(self) -> None:
        from settings.dialogs import DotExpressSettingsDialog, TextProcessingDialog

        text_dialog = Mock()
        settings_dialog = object.__new__(DotExpressSettingsDialog)
        settings_dialog.Destroy = Mock()
        with (
            patch.object(TextProcessingDialog, "_instance", text_dialog),
            patch.object(DotExpressSettingsDialog, "_instance", settings_dialog),
        ):
            self.assertIs(
                TextProcessingDialog.show_singleton(parent=None, script_path="dictionary/preprocessing.py"),
                text_dialog,
            )
            settings_dialog._destroy()
            self.assertIsNone(DotExpressSettingsDialog._instance)
            self.assertIs(TextProcessingDialog._instance, text_dialog)

        settings_dialog.Destroy.assert_called_once_with()


# --- P2-3 characterization: the option lists as the settings panels show them.
# The panels are built for real under the settings stub scope and read the real
# zh_TW catalog. settings.dialogs._ is never patched here (P2-3 spec, Test Plan):
# the labels must be what a user sees, not what a patched _ returns.


class RecordingChoice:
    """``wx.Choice`` stand-in that keeps its items, selection and enabled state."""

    def __init__(self, parent=None, choices=()):
        self.items = list(choices)
        self.selection = -1
        self.enabled = True

    def AppendItems(self, items):
        self.items.extend(items)

    def GetSelection(self):
        return self.selection

    def SetSelection(self, index):
        self.selection = index

    def Disable(self):
        self.enabled = False


class RecordingSpin:
    """``wx.SpinCtrl`` stand-in that keeps its range and value."""

    def __init__(self, parent=None, min=0, max=100, initial=0):
        self.minimum = min
        self.maximum = max
        self.value = initial

    def GetValue(self):
        return self.value

    def SetValue(self, value):
        self.value = value

    def Bind(self, event, handler):
        pass


def fake_table(file_name, display_name, output=True):
    return SimpleNamespace(fileName=file_name, displayName=display_name, output=output)


# English display names are what a source run gets from braille/tables/__tables.py;
# the zhcn-g2 name is already translated, as in a packaged run (P2-3 spec D6).
FAKE_TABLES = (
    fake_table("zh-tw.ctb", "Chinese (Taiwan, Mandarin)"),
    fake_table("zhcn-g2.ctb", "中文 (中國) 漢語雙拚盲文"),
    fake_table("en-ueb-g1.ctb", "Unified English Braille Code grade 1"),
    fake_table("en-GB-g2.ctb", "English (U.K.) grade 2"),
    fake_table("ja-kantenji.utb", "Japanese (Kantenji) literary braille"),
    fake_table("eo-g1.ctb", "Esperanto grade 1"),
    fake_table("unicode-braille.utb", "Unicode braille", output=False),
)
ENGLISH_TABLE_NAMES = {"zhcn-g2.ctb": "Chinese (China, Mandarin) Double-phonic Braille System"}

TABLE_ROW_LABELS = ["預設轉譯表", "英文轉譯表", "中文轉譯表", "日文轉譯表", "數學轉譯表"]
# What each row lists for FAKE_TABLES: translated, sorted by the lower-cased name,
# "None selected" first in the en/zh/ja rows only, math as is.
FAKE_TABLE_ROWS = [
    ["世界文一級", "中文 (中國) 漢語雙拚盲文", "中文 (台灣) 注音", "日文 (漢點字) 書寫", "英文 (英國) 二級", "英文統一一級"],
    ["未選擇", "英文 (英國) 二級", "英文統一一級"],
    ["未選擇", "中文 (中國) 漢語雙拚盲文", "中文 (台灣) 注音"],
    ["未選擇", "日文 (漢點字) 書寫"],
    ["UEB", "Nemeth"],
]


def build_panel(
    panel_name,
    *,
    translation=TranslationSettings("unicode", 40, "default"),
    tables=None,
    view=ViewSettings(12, "light", "simbraille"),
    table_list=FAKE_TABLES,
    owner=None,
):
    """Build a real settings panel with recording choices and spins and a fake ``listTables``.

    ``owner`` (for example a dialog) replaces the default owner; the snapshot arguments are then unused.
    """
    module = sys.modules["settings.dialogs"]
    if owner is None:
        snapshot = DotExpressSettingsSnapshot.create(
            translation=translation,
            translation_tables={} if tables is None else tables,
            view=view,
        )
        owner = SimpleNamespace(snapshot=snapshot, dictionary_names=["default", "math"])
    with (
        patch.multiple(module.wx, Choice=RecordingChoice, SpinCtrl=RecordingSpin),
        patch.object(module, "listTables", Mock(return_value=list(table_list))),
    ):
        return getattr(module, panel_name)(None, owner)


def grid_rows(panel):
    """The panel's (label, control) rows, in layout order."""
    (grid, *_rest), _kwargs = panel.sizer.children[0]
    widgets = [args[0] for args, _kwargs in grid.children]
    return [(widgets[index].label, widgets[index + 1]) for index in range(0, len(widgets), 2)]


def translation_snapshot(output_mode="unicode", width=40):
    return DotExpressSettingsSnapshot.create(
        translation=TranslationSettings(output_mode, width, "default"),
        translation_tables={},
        view=ViewSettings(12, "light", "simbraille"),
    )


def view_snapshot(font_size=12, scheme="light", braille_font="simbraille"):
    return DotExpressSettingsSnapshot.create(
        translation=TranslationSettings("unicode", 40, "default"),
        translation_tables={},
        view=ViewSettings(font_size, scheme, braille_font),
    )


def tables_snapshot(tables):
    return DotExpressSettingsSnapshot.create(
        translation=TranslationSettings("unicode", 40, "default"),
        translation_tables=tables,
        view=ViewSettings(12, "light", "simbraille"),
    )


class TranslationPanelOptionsTest(unittest.TestCase):
    def test_rows_and_output_mode_choices_show_the_translated_labels_in_order(self) -> None:
        panel = build_panel("TranslationSettingsPanel")

        rows = grid_rows(panel)
        self.assertEqual([label for label, _control in rows], ["點字類型", "寬度", "字典"])
        self.assertEqual([control for _label, control in rows], [panel.output_choice, panel.width_spin, panel.dictionary_choice])
        self.assertEqual(panel.output_choice.items, ["Unicode", "ASCII"])
        self.assertEqual(panel.output_choice.items, [i18n._("Unicode"), i18n._("ASCII")])

    def test_stored_output_mode_selects_its_index_and_unknown_selects_the_first(self) -> None:
        for output_mode, expected in (("unicode", 0), ("ascii", 1), ("braille", 0), ("ASCII", 0), ("", 0)):
            with self.subTest(output_mode=output_mode):
                panel = build_panel(
                    "TranslationSettingsPanel",
                    translation=TranslationSettings(output_mode, 40, "default"),
                )
                self.assertEqual(panel.output_choice.selection, expected)

    def test_save_maps_each_selection_to_its_value_and_out_of_range_to_the_first(self) -> None:
        baseline = translation_snapshot()
        panel = build_panel("TranslationSettingsPanel")
        for selection, expected in ((0, "unicode"), (1, "ascii"), (-1, "unicode"), (2, "unicode")):
            with self.subTest(selection=selection):
                panel.output_choice.SetSelection(selection)
                self.assertEqual(panel.on_save(baseline).translation.output_mode, expected)

    def test_width_spin_range_and_initial_value_are_clamped(self) -> None:
        for width, expected in ((5, 10), (10, 10), (40, 40), (200, 200), (500, 200)):
            with self.subTest(width=width):
                panel = build_panel(
                    "TranslationSettingsPanel",
                    translation=TranslationSettings("unicode", width, "default"),
                )
                spin = panel.width_spin
                self.assertEqual((spin.minimum, spin.maximum, spin.value), (10, 200, expected))
                self.assertEqual(panel.on_save(translation_snapshot()).translation.width, expected)

    def test_load_snapshot_reselects_the_output_mode_and_clamps_the_width(self) -> None:
        panel = build_panel("TranslationSettingsPanel")

        panel.load_snapshot(translation_snapshot("ascii", 500))
        self.assertEqual((panel.output_choice.selection, panel.width_spin.value), (1, 200))

        panel.load_snapshot(translation_snapshot("braille", 5))
        self.assertEqual((panel.output_choice.selection, panel.width_spin.value), (0, 10))

        panel.load_snapshot(translation_snapshot("unicode", 64))
        self.assertEqual((panel.output_choice.selection, panel.width_spin.value), (0, 64))


class ViewPanelOptionsTest(unittest.TestCase):
    def test_rows_and_choices_show_the_translated_labels_in_order(self) -> None:
        panel = build_panel("ViewSettingsPanel")

        rows = grid_rows(panel)
        self.assertEqual([label for label, _control in rows], ["字型大小", "配色", "點字字型"])
        self.assertEqual(
            [control for _label, control in rows],
            [panel.font_size_spin, panel.scheme_choice, panel.braille_font_choice],
        )
        self.assertEqual(panel.scheme_choice.items, ["淺色", "深色"])
        self.assertEqual(panel.scheme_choice.items, [i18n._("Light"), i18n._("Dark")])
        self.assertEqual(panel.braille_font_choice.items, ["預設", "SimBraille"])
        self.assertEqual(panel.braille_font_choice.items, [i18n._("Default"), i18n._("SimBraille")])

    def test_stored_values_select_their_index_and_unknown_values_select_the_first(self) -> None:
        for scheme, braille_font, expected in (
            ("light", "default", (0, 0)),
            ("dark", "simbraille", (1, 1)),
            ("dark", "default", (1, 0)),
            ("sepia", "serif", (0, 0)),
            ("Dark", "SimBraille", (0, 0)),
        ):
            with self.subTest(scheme=scheme, braille_font=braille_font):
                panel = build_panel("ViewSettingsPanel", view=ViewSettings(12, scheme, braille_font))
                self.assertEqual(
                    (panel.scheme_choice.selection, panel.braille_font_choice.selection),
                    expected,
                )

    def test_save_maps_out_of_range_selections_to_the_first_option(self) -> None:
        # KNOWN QUIRK (P2-3 spec, K1): -1 and past-the-end save the first option,
        # "default", not config.DEFAULT_BRAILLE_FONT ("simbraille").
        self.assertEqual(config.DEFAULT_BRAILLE_FONT, "simbraille")
        baseline = view_snapshot()
        panel = build_panel("ViewSettingsPanel")
        for selection, expected in (
            (0, ("light", "default")),
            (1, ("dark", "simbraille")),
            (-1, ("light", "default")),
            (2, ("light", "default")),
        ):
            with self.subTest(selection=selection):
                panel.scheme_choice.SetSelection(selection)
                panel.braille_font_choice.SetSelection(selection)
                view = panel.on_save(baseline).view
                self.assertEqual((view.scheme, view.braille_font), expected)

    def test_font_size_spin_range_and_initial_value_are_clamped(self) -> None:
        for font_size, expected in ((5, 8), (8, 8), (12, 12), (48, 48), (99, 48)):
            with self.subTest(font_size=font_size):
                panel = build_panel("ViewSettingsPanel", view=ViewSettings(font_size, "light", "default"))
                spin = panel.font_size_spin
                self.assertEqual((spin.minimum, spin.maximum, spin.value), (8, 48, expected))
                self.assertEqual(panel.on_save(view_snapshot()).view.font_size, expected)

    def test_load_snapshot_reselects_both_choices_and_clamps_the_font_size(self) -> None:
        panel = build_panel("ViewSettingsPanel")

        panel.load_snapshot(view_snapshot(99, "dark", "default"))
        self.assertEqual(
            (panel.font_size_spin.value, panel.scheme_choice.selection, panel.braille_font_choice.selection),
            (48, 1, 0),
        )

        panel.load_snapshot(view_snapshot(5, "sepia", "simbraille"))
        self.assertEqual(
            (panel.font_size_spin.value, panel.scheme_choice.selection, panel.braille_font_choice.selection),
            (8, 0, 1),
        )


class TranslationTablesPanelOptionsTest(unittest.TestCase):
    STORED = {
        "default": "zh-tw.ctb",
        "en": "en-GB-g2.ctb",
        "zh": "",
        "ja": "ja-kantenji.utb",
        "math": "Nemeth",
    }

    def test_rows_show_the_translated_field_labels_in_order(self) -> None:
        panel = build_panel("TranslationTablesPanel")

        rows = grid_rows(panel)
        self.assertEqual([label for label, _control in rows], TABLE_ROW_LABELS)
        self.assertEqual(
            TABLE_ROW_LABELS,
            [
                i18n._("Default Translation Table"),
                i18n._("English Translation Table"),
                i18n._("Chinese Translation Table"),
                i18n._("Japanese Translation Table"),
                i18n._("Math Translation Table"),
            ],
        )

    def test_each_row_lists_its_tables_sorted_by_translated_name(self) -> None:
        # KNOWN QUIRK (P2-3 spec, K4): the prefix is a plain startswith on the
        # lower-cased file name, so "zh" also takes zhcn-g2 and "en" takes en-GB-g2.
        panel = build_panel("TranslationTablesPanel")

        self.assertEqual([control.items for _label, control in grid_rows(panel)], FAKE_TABLE_ROWS)
        self.assertEqual([control.enabled for _label, control in grid_rows(panel)], [True] * 5)

    def test_source_run_and_packaged_display_names_give_the_same_rows(self) -> None:
        english = [
            fake_table(table.fileName, ENGLISH_TABLE_NAMES.get(table.fileName, table.displayName), table.output)
            for table in FAKE_TABLES
        ]
        packaged = [fake_table(table.fileName, i18n._(table.displayName), table.output) for table in english]
        self.assertNotEqual([table.displayName for table in english], [table.displayName for table in packaged])

        for table_list in (english, packaged):
            with self.subTest(first=table_list[0].displayName):
                panel = build_panel("TranslationTablesPanel", table_list=table_list)
                self.assertEqual([control.items for _label, control in grid_rows(panel)], FAKE_TABLE_ROWS)

    def test_stored_file_names_select_their_rows_and_save_in_field_order(self) -> None:
        panel = build_panel("TranslationTablesPanel", tables=self.STORED)

        self.assertEqual([control.selection for _label, control in grid_rows(panel)], [2, 1, 0, 1, 1])
        saved = panel.on_save(tables_snapshot({})).translation_tables
        self.assertEqual(saved, self.STORED)
        self.assertEqual(list(saved), ["default", "en", "zh", "ja", "math"])
        self.assertTrue(panel.is_valid())
        self.assertIsNone(panel.validation_error())

    def test_unknown_or_missing_file_names_select_the_first_option(self) -> None:
        # KNOWN QUIRK (P2-3 spec, K2): an unknown stored value silently selects
        # index 0, and saving then stores that option.
        panel = build_panel(
            "TranslationTablesPanel",
            tables={"default": "missing.ctb", "en": "zh-tw.ctb", "math": "Braille"},
        )

        self.assertEqual([control.selection for _label, control in grid_rows(panel)], [0, 0, 0, 0, 0])
        self.assertEqual(
            panel.on_save(tables_snapshot({})).translation_tables,
            {"default": "eo-g1.ctb", "en": "", "zh": "", "ja": "", "math": "UEB"},
        )

    def test_load_snapshot_reselects_every_row(self) -> None:
        panel = build_panel("TranslationTablesPanel")
        self.assertEqual([control.selection for _label, control in grid_rows(panel)], [0, 0, 0, 0, 0])

        panel.load_snapshot(tables_snapshot(self.STORED))

        self.assertEqual([control.selection for _label, control in grid_rows(panel)], [2, 1, 0, 1, 1])

    def test_without_tables_the_default_row_is_disabled_and_reported_first(self) -> None:
        panel = build_panel("TranslationTablesPanel", tables=self.STORED, table_list=())

        rows = grid_rows(panel)
        self.assertEqual(
            [(control.items, control.enabled, control.selection) for _label, control in rows],
            [
                ([], False, -1),
                (["未選擇"], True, 0),
                (["未選擇"], True, 0),
                (["未選擇"], True, 0),
                (["UEB", "Nemeth"], True, 1),
            ],
        )
        self.assertFalse(panel.is_valid())
        self.assertEqual(panel.validation_error(), ("請先選擇預設轉譯表。", rows[0][1]))
        self.assertEqual(
            panel.on_save(tables_snapshot({})).translation_tables,
            {"default": "", "en": "", "zh": "", "ja": "", "math": "Nemeth"},
        )

    def test_validation_checks_the_required_rows_in_field_order(self) -> None:
        panel = build_panel("TranslationTablesPanel", tables=self.STORED)
        rows = grid_rows(panel)
        default_choice, math_choice = rows[0][1], rows[4][1]

        math_choice.SetSelection(-1)
        self.assertFalse(panel.is_valid())
        self.assertEqual(panel.validation_error(), ("請先選擇數學轉譯表。", math_choice))

        default_choice.SetSelection(-1)
        self.assertEqual(panel.validation_error(), ("請先選擇預設轉譯表。", default_choice))

        for _label, control in rows[1:4]:
            control.SetSelection(-1)
        default_choice.SetSelection(0)
        math_choice.SetSelection(1)
        self.assertTrue(panel.is_valid())
        self.assertIsNone(panel.validation_error())
        self.assertEqual(
            panel.on_save(tables_snapshot({})).translation_tables,
            {"default": "eo-g1.ctb", "en": "", "zh": "", "ja": "", "math": "Nemeth"},
        )


def _tables_module_entries():
    """(file name, display msgid, output) of every addTable call, read without importing __tables.py."""
    path = Path(__file__).resolve().parents[1] / "braille" / "tables" / "__tables.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    entries = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "addTable":
            file_name, display = node.args[0], node.args[1]
            assert isinstance(display, ast.Call) and display.func.id == "_", ast.dump(display)
            output = all(
                not (keyword.arg == "output" and keyword.value.value is False)
                for keyword in node.keywords
            )
            entries.append((file_name.value, display.args[0].value, output))
    return entries


class TableDisplayNameGuardTest(unittest.TestCase):
    """Why settings.dialogs translates table names again (P2-3 spec D6). Kept permanently.

    __tables.py looks for its catalog in braille/locales, which only the packaged
    build has: a source run gets English display names, a packaged run zh_TW ones.
    The dialog's _() must give the same names either way.
    """

    def test_translating_a_table_name_twice_changes_nothing(self) -> None:
        entries = _tables_module_entries()
        self.assertEqual(len(entries), 198)
        self.assertEqual(sum(output for _file_name, _name, output in entries), 196)

        not_idempotent = [
            name for _file_name, name, _output in entries if i18n._(i18n._(name)) != i18n._(name)
        ]
        self.assertEqual(not_idempotent, [])

    def test_sorted_output_names_are_the_same_from_english_or_translated_names(self) -> None:
        names = [name for _file_name, name, output in _tables_module_entries() if output]
        from_english = sorted((i18n._(name) for name in names), key=str.lower)
        from_translated = sorted((i18n._(i18n._(name)) for name in names), key=str.lower)

        self.assertEqual(from_english, from_translated)
        self.assertEqual(from_english[:3], ["世界文一級", "中國通用盲文 (簡體中文字)", "中庫德文一級"])



# --- P2-4 characterization: a font size changed in the main window (Ctrl+wheel)
# reaching the open settings dialog. The View panel is the real panel, built with
# the dialog as its owner. The dialog goes into its slot with patch.object only.


def sync_open_dialog_font_size(dialog_class, font_size):
    """Pass a font size to the open dialog of ``dialog_class`` the way the main window does."""
    dialog_class.sync_open_font_size(font_size)


class FontSizeSyncCharacterizationTest(unittest.TestCase):
    def setUp(self) -> None:
        from settings.dialogs import DotExpressSettingsDialog

        self.dialog_class = DotExpressSettingsDialog
        self.dialog = make_dialog_without_wx_constructor()
        self.dialog.snapshot = view_snapshot(12, "light", "simbraille")

    def open_dialog(self):
        return patch.object(self.dialog_class, "_instance", self.dialog)

    def sync(self, font_size) -> None:
        sync_open_dialog_font_size(self.dialog_class, font_size)

    def add_view_panel(self, index=2):
        panel = build_panel("ViewSettingsPanel", owner=self.dialog)
        self.dialog.panel_instances[index] = panel
        return panel

    def test_without_an_open_dialog_nothing_happens(self) -> None:
        with patch.object(self.dialog_class, "_instance", None):
            self.sync(20)

        self.assertEqual(self.dialog.snapshot, view_snapshot(12, "light", "simbraille"))

    def test_without_a_view_panel_only_the_snapshot_font_size_changes(self) -> None:
        with self.open_dialog():
            self.sync(20)

        self.assertEqual(self.dialog.snapshot, view_snapshot(20, "light", "simbraille"))
        self.assertEqual(self.dialog.panel_instances, {})
        panel = build_panel("ViewSettingsPanel", owner=self.dialog)
        self.assertEqual(
            (panel.font_size_spin.value, panel.scheme_choice.selection, panel.braille_font_choice.selection),
            (20, 0, 1),
        )

    def test_sizes_are_clamped_to_the_spin_range(self) -> None:
        for font_size, expected in ((99, 48), (49, 48), (48, 48), (8, 8), (7, 8), (3, 8)):
            with self.subTest(font_size=font_size):
                self.dialog.snapshot = view_snapshot(12, "light", "simbraille")
                self.dialog.panel_instances = {}
                with self.open_dialog():
                    self.sync(font_size)
                self.assertEqual(self.dialog.snapshot.view, ViewSettings(expected, "light", "simbraille"))

                self.dialog.snapshot = view_snapshot(12, "light", "simbraille")
                panel = self.add_view_panel()
                with self.open_dialog():
                    self.sync(font_size)
                self.assertEqual((panel.font_size_spin.value, self.dialog.snapshot.view.font_size), (expected, expected))

    def test_a_clean_view_panel_shows_the_size_and_keeps_the_other_drafts(self) -> None:
        panel = self.add_view_panel()
        panel.scheme_choice.SetSelection(1)  # a draft: Dark, not applied yet

        with self.open_dialog():
            self.sync(20)

        self.assertEqual(panel.font_size_spin.value, 20)
        self.assertFalse(panel.font_size_dirty)
        self.assertEqual(self.dialog.snapshot, view_snapshot(20, "light", "simbraille"))
        self.assertEqual((panel.scheme_choice.selection, panel.braille_font_choice.selection), (1, 1))
        self.assertEqual(panel.on_save(self.dialog.snapshot).view, ViewSettings(20, "dark", "simbraille"))

    def test_a_pending_edit_blocks_the_sync_until_the_snapshot_is_reloaded(self) -> None:
        panel = self.add_view_panel()
        panel.font_size_spin.SetValue(30)
        panel._on_font_size_changed(None)  # bound to EVT_SPINCTRL and EVT_TEXT

        with self.open_dialog():
            self.sync(20)

        # KNOWN QUIRK (P2-4 spec, 2): the pending edit wins, and the snapshot keeps 12 too.
        self.assertEqual(panel.font_size_spin.value, 30)
        self.assertTrue(panel.font_size_dirty)
        self.assertEqual(self.dialog.snapshot, view_snapshot(12, "light", "simbraille"))

        panel.load_snapshot(self.dialog.snapshot)  # what Apply does after the commit
        self.assertFalse(panel.font_size_dirty)
        with self.open_dialog():
            self.sync(20)

        self.assertEqual(panel.font_size_spin.value, 20)
        self.assertEqual(self.dialog.snapshot, view_snapshot(20, "light", "simbraille"))

    def test_a_view_panel_subclass_under_any_index_is_found(self) -> None:
        from settings.dialogs import ViewSettingsPanel

        class CustomViewPanel(ViewSettingsPanel):
            pass

        panel = object.__new__(CustomViewPanel)
        panel.font_size_dirty = False
        panel.font_size_spin = RecordingSpin(initial=12)
        other = Mock()
        self.dialog.panel_instances = {0: panel, 1: other}

        with self.open_dialog():
            self.sync(20)

        self.assertEqual(panel.font_size_spin.value, 20)
        self.assertEqual(self.dialog.snapshot.view.font_size, 20)
        self.assertEqual(other.mock_calls, [])

    def test_a_spin_that_reports_its_own_change_still_follows_the_next_step(self) -> None:
        panel = self.add_view_panel()
        spin = panel.font_size_spin

        def set_value_and_report(value):
            RecordingSpin.SetValue(spin, value)
            panel._on_font_size_changed(None)  # a platform whose SetValue emits EVT_TEXT

        spin.SetValue = set_value_and_report
        with self.open_dialog():
            self.sync(13)
            self.sync(14)

        self.assertEqual(spin.value, 14)
        self.assertFalse(panel.font_size_dirty)
        self.assertEqual(self.dialog.snapshot.view.font_size, 14)

    def test_apply_without_visiting_the_view_panel_commits_the_synced_size(self) -> None:
        self.dialog.commit = Mock(side_effect=lambda snapshot: snapshot)

        with self.open_dialog():
            self.sync(20)
            self.assertTrue(self.dialog.on_apply())

        self.dialog.commit.assert_called_once_with(view_snapshot(20, "light", "simbraille"))


if __name__ == "__main__":
    unittest.main()
