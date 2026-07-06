from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import Mock, patch


def _install_stub_modules() -> None:
    wx = sys.modules.get("wx", types.ModuleType("wx"))

    class _Widget:
        def __init__(self, *args, **kwargs):
            self.parent = args[0] if args else None
            self.label = kwargs.get("label", "")
            self.name = ""
            self.bound_events = {}
            self.sizer = None
            self.min_size = None
            self.size = kwargs.get("size")
            self.focused = False
            self.visible = True

        def __getattr__(self, _name):
            def _method(*args, **kwargs):
                return None

            return _method

        def Bind(self, event, handler):
            self.bound_events[event] = handler

        def SetName(self, name):
            self.name = name

        def GetName(self):
            return self.name

        def SetLabel(self, label):
            self.label = label

        def SetSizer(self, sizer):
            self.sizer = sizer

        def SetMinSize(self, size):
            self.min_size = size

        def SetSize(self, size):
            self.size = size

        def Show(self):
            self.visible = True

        def Hide(self):
            self.visible = False

        def SetFocus(self):
            self.focused = True

        def HasFocus(self):
            return self.focused

    class Window(_Widget):
        @staticmethod
        def FindFocus():
            return None

    class Panel(Window):
        pass

    class Dialog(Window):
        pass

    class Frame(Window):
        pass

    class StaticText(Window):
        pass

    class Button(Window):
        pass

    class Choice(Window):
        def GetSelection(self):
            return -1

        def SetSelection(self, index):
            pass

        def AppendItems(self, items):
            pass

        def Append(self, item):
            pass

        def Disable(self):
            pass

        def Enable(self, state=True):
            pass

    class SpinCtrl(Window):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._value = kwargs.get("initial", 0)

        def GetValue(self):
            return self._value

        def SetValue(self, value):
            self._value = value

    class Sizer(_Widget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.children = []

        def Add(self, *args, **kwargs):
            self.children.append((args, kwargs))

    class BoxSizer(Sizer):
        pass

    class GridBagSizer(Sizer):
        def AddGrowableRow(self, idx, proportion=1):
            pass

        def AddGrowableCol(self, idx, proportion=1):
            pass

    class FlexGridSizer(Sizer):
        def AddGrowableCol(self, idx, proportion=1):
            pass

    class ListCtrl(Window):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.style = kwargs.get("style", 0)
            self.columns = []
            self.items = []
            self.selected_index = -1
            self.focused_index = -1

        @property
        def ItemCount(self):
            return len(self.items)

        def InsertColumn(self, index, label):
            self.columns.insert(index, label)

        def Append(self, item):
            self.items.append(item)

        def Select(self, index):
            self.selected_index = index

        def GetFirstSelected(self):
            return self.selected_index

        def Focus(self, index):
            self.focused_index = index
            self.focused = True

        def GetItemCount(self):
            return len(self.items)

        def GetItemText(self, index):
            return self.items[index][0]

    class Accessible(_Widget):
        def __init__(self, window=None):
            self.Window = window

    wx.Window = Window
    wx.Panel = Panel
    wx.Dialog = Dialog
    wx.Frame = Frame
    wx.StaticText = StaticText
    wx.Button = Button
    wx.Choice = Choice
    wx.SpinCtrl = SpinCtrl
    wx.Sizer = Sizer
    wx.BoxSizer = BoxSizer
    wx.GridBagSizer = GridBagSizer
    wx.FlexGridSizer = FlexGridSizer
    wx.ListCtrl = ListCtrl
    wx.Accessible = Accessible

    braille = types.ModuleType("braille")
    braille_tables = types.ModuleType("braille.tables")
    braille_tables.listTables = lambda: []
    braille.tables = braille_tables
    sys.modules["braille"] = braille
    sys.modules["braille.tables"] = braille_tables

    wx_lib = types.ModuleType("wx.lib")
    wx_lib_scrolledpanel = types.ModuleType("wx.lib.scrolledpanel")

    class ScrolledPanel(Panel):
        pass

    wx_lib_scrolledpanel.ScrolledPanel = ScrolledPanel
    wx.lib = wx_lib
    wx_lib.scrolledpanel = wx_lib_scrolledpanel
    sys.modules["wx.lib"] = wx_lib
    sys.modules["wx.lib.scrolledpanel"] = wx_lib_scrolledpanel

    wx.CallAfter = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    wx.DefaultPosition = (0, 0)
    wx.DefaultSize = (0, 0)
    wx.__path__ = []
    wx.__getattr__ = lambda name: type(name, (), {})

    wx.ID_OK = 5100
    wx.ID_CANCEL = 5101
    wx.ID_APPLY = 5102
    wx.ID_ANY = -1
    wx.OK = 0x0004
    wx.ICON_ERROR = 0x0200
    wx.APPLY = 5102
    wx.RESIZE_BORDER = 0x0040
    wx.DEFAULT_DIALOG_STYLE = 0x0010
    wx.BORDER_SUNKEN = 0x0008
    wx.LC_SINGLE_SEL = 0x0020
    wx.LC_REPORT = 0x0010
    wx.LC_NO_HEADER = 0x4000
    wx.ACC_OK = 0
    wx.ROLE_SYSTEM_PROPERTYPAGE = 38
    wx.EVT_LIST_ITEM_FOCUSED = 100
    wx.EVT_LIST_ITEM_SELECTED = 101
    wx.EVT_CHAR_HOOK = 102
    wx.EVT_CLOSE = 103
    wx.EVT_BUTTON = 104
    wx.NOT_FOUND = -1
    wx.ALL = 0x0010
    wx.EXPAND = 0x0020
    wx.VERTICAL = 0x0001
    wx.HORIZONTAL = 0x0002
    wx.ALIGN_RIGHT = 0x0200
    wx.ALIGN_CENTER = 0x0100
    wx.ALIGN_CENTER_VERTICAL = 0x0200
    wx.LEFT = 0x0040
    wx.RIGHT = 0x0080
    wx.TOP = 0x0100
    wx.BOTTOM = 0x0200
    wx.SP_WRAP = 0x0001
    wx.SP_ARROW_KEYS = 0x0002
    wx.EVT_SPINCTRL = 110
    wx.EVT_TEXT = 111
    wx.WXK_TAB = 9

    class PyDeadObjectError(RuntimeError):
        pass

    wx.PyDeadObjectError = PyDeadObjectError
    wx.MessageBox = Mock()

    sys.modules["wx"] = wx


_install_stub_modules()
import wx

from settings_dialogs import (
    MultiCategorySettingsDialog,
    SettingsPanel,
    SettingsPanelAccessible,
)

from settings_state import DotExpressSettingsSnapshot
from translation.settings import TranslationSettings
from view_settings import ViewSettings


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
    from settings_dialogs import DotExpressSettingsDialog

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
        import settings_dialogs

        saved_modules = {
            name: sys.modules.get(name)
            for name in ("wx", "wx.lib", "wx.lib.scrolledpanel")
        }
        for name in saved_modules:
            sys.modules.pop(name, None)
        _install_stub_modules()
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
            with patch.object(settings_dialogs, "wx", fresh_wx):
                with patch.object(
                    settings_dialogs,
                    "ScrolledPanel",
                    fresh_wx.lib.scrolledpanel.ScrolledPanel,
                ):
                    with patch("settings_dialogs._", side_effect=lambda text: text):
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
        from settings_dialogs import TranslationSettingsPanel

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
        from settings_dialogs import TranslationTablesPanel

        panel = object.__new__(TranslationTablesPanel)
        panel._selected_file_name = Mock(
            side_effect=lambda key: "" if key == "default" else "UEB"
        )
        self.assertFalse(panel.is_valid())

    def test_tables_panel_validation_points_to_missing_required_control(self) -> None:
        from settings_dialogs import TranslationTablesPanel

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

        with patch("settings_dialogs._", side_effect=lambda text: text):
            message, focus_control = panel.validation_error()

        self.assertEqual(
            message,
            "Please select a value for Default Translation Table.",
        )
        self.assertIs(focus_control, default_choice)


class ViewSettingsPanelTest(unittest.TestCase):
    def test_view_panel_tracks_font_size_dirty_state(self) -> None:
        from settings_dialogs import ViewSettingsPanel

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
        from settings_dialogs import TranslationTablesPanel

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

        with patch("settings_dialogs._", side_effect=lambda text: text):
            with patch("settings_dialogs.wx.MessageBox") as message_box:
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
        from settings_dialogs import DotExpressSettingsDialog

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
        from settings_dialogs import DotExpressSettingsDialog

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
        from settings_dialogs import DotExpressSettingsDialog, ViewSettingsPanel

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
        from settings_dialogs import DotExpressSettingsDialog

        dialog = object.__new__(DotExpressSettingsDialog)
        dialog.title_template = "DotExpress 設定：{category}"

        self.assertEqual(dialog._format_title("轉譯"), "DotExpress 設定：轉譯")


if __name__ == "__main__":
    unittest.main()
