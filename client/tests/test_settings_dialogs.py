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

    class Sizer(_Widget):
        pass

    class BoxSizer(Sizer):
        pass

    class GridBagSizer(Sizer):
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
    wx.Sizer = Sizer
    wx.BoxSizer = BoxSizer
    wx.GridBagSizer = GridBagSizer
    wx.ListCtrl = ListCtrl
    wx.Accessible = Accessible

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
    wx.ALL = 0x0010
    wx.EXPAND = 0x0020
    wx.VERTICAL = 0x0001
    wx.HORIZONTAL = 0x0002
    wx.ALIGN_RIGHT = 0x0200
    wx.ALIGN_CENTER = 0x0100

    sys.modules["wx"] = wx


_install_stub_modules()
import wx

from settings_dialogs import (
    MultiCategorySettingsDialog,
    SettingsPanel,
    SettingsPanelAccessible,
)


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


if __name__ == "__main__":
    unittest.main()
