from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

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
        panel.CHOICE_SPECS = [
            ("default", "Default Translation Table", None),
            ("en", "English Translation Table", "en"),
            ("zh", "Chinese Translation Table", "zh"),
            ("ja", "Japanese Translation Table", "ja"),
            ("math", "Math Translation Table", None),
        ]
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
        panel.CHOICE_SPECS = [
            ("default", "Default Translation Table", None),
            ("en", "English Translation Table", "en"),
            ("zh", "Chinese Translation Table", "zh"),
            ("ja", "Japanese Translation Table", "ja"),
            ("math", "Math Translation Table", None),
        ]
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


if __name__ == "__main__":
    unittest.main()
