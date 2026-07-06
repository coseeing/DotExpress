from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import Mock


def _install_stub_modules() -> None:
    wx = sys.modules.get("wx", types.ModuleType("wx"))

    class _Widget:
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, _name):
            def _method(*args, **kwargs):
                return None

            return _method

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
        def GetValue(self):
            return 0

        def SetValue(self, value):
            pass

        def Bind(self, event, handler):
            pass

    class Sizer(_Widget):
        pass

    class BoxSizer(Sizer):
        pass

    class GridBagSizer(Sizer):
        pass

    class FlexGridSizer(Sizer):
        def AddGrowableCol(self, idx, proportion=1):
            pass

    class ListCtrl(Window):
        def GetSelection(self):
            return -1

        def GetItemCount(self):
            return 0

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
    wx.APPLY = 5102
    wx.RESIZE_BORDER = 0x0040
    wx.DEFAULT_DIALOG_STYLE = 0x0010
    wx.BORDER_SUNKEN = 0x0008
    wx.LC_SINGLE_SEL = 0x0020
    wx.LC_REPORT = 0x0010
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


def make_snapshot(font_size=40):
    return DotExpressSettingsSnapshot.create(
        translation=TranslationSettings("unicode", 40, "default"),
        translation_tables={},
        view=ViewSettings(font_size, "light", "default"),
    )


def make_dialog_without_wx_constructor():
    from settings_dialogs import DotExpressSettingsDialog

    dialog = object.__new__(DotExpressSettingsDialog)
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
        invalid = Mock(is_valid=Mock(return_value=False))
        valid = Mock(is_valid=Mock(return_value=True))
        dialog.panel_instances = {0: valid, 1: invalid}

        dialog.on_apply()

        dialog.commit.assert_not_called()
        valid.on_save.assert_not_called()

    def test_successful_apply_reloads_normalized_baseline(self) -> None:
        dialog = make_dialog_without_wx_constructor()
        committed = make_snapshot(font_size=18)
        dialog.commit = Mock(return_value=committed)
        panel = Mock(is_valid=Mock(return_value=True))
        panel.on_save.return_value = committed
        dialog.panel_instances = {0: panel}

        dialog.on_apply()

        self.assertEqual(dialog.snapshot, committed)
        panel.load_snapshot.assert_called_once_with(committed)


if __name__ == "__main__":
    unittest.main()
