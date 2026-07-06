from __future__ import annotations

import gettext
from pathlib import Path
import sys

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from settings_state import DotExpressSettingsSnapshot


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path


LOCALE_DOMAIN = "dotexpress"
LOCALE_LANGUAGES = ["zh_TW"]
_translation = gettext.translation(
    LOCALE_DOMAIN,
    localedir=str(resource_path("locales")),
    languages=LOCALE_LANGUAGES,
    fallback=True,
)
_ = _translation.gettext


class SettingsPanelAccessible(wx.Accessible):
    def __init__(self, window=None):
        super().__init__(window)
        self.Window = window

    def GetRole(self, child_id):
        return (wx.ACC_OK, wx.ROLE_SYSTEM_PROPERTYPAGE)

    def GetDescription(self, child_id):
        return (wx.ACC_OK, self.Window.panel_description)


class SettingsPanel(wx.Panel):
    title = ""
    panel_description = ""

    def __init__(self, parent, owner):
        super().__init__(parent)
        self.owner = owner
        self.make_settings()
        self.SetName(self.title.replace("&", ""))
        self.SetAccessible(SettingsPanelAccessible(self))

    def make_settings(self) -> None:
        raise NotImplementedError

    def on_panel_activated(self) -> None:
        self.Show()

    def on_panel_deactivated(self) -> None:
        self.Hide()

    def is_valid(self) -> bool:
        return True

    def on_save(
        self,
        snapshot: DotExpressSettingsSnapshot,
    ) -> DotExpressSettingsSnapshot:
        raise NotImplementedError

    def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
        raise NotImplementedError

    def on_discard(self) -> None:
        pass


class SettingsDialog(wx.Dialog):
    INITIAL_SIZE = (720, 440)
    MIN_SIZE = (520, 300)

    def __init__(self, parent, *, title: str):
        super().__init__(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.Bind(wx.EVT_CLOSE, self._on_window_close)

    def _on_window_close(self, event) -> None:
        self.on_cancel()

    def on_ok(self, event=None) -> None:
        pass

    def on_cancel(self, event=None) -> None:
        pass

    def on_apply(self, event=None) -> None:
        pass


class MultiCategorySettingsDialog(SettingsDialog):
    category_classes: list[type[SettingsPanel]] = []

    def __init__(self, parent, *, title, initial_category=None):
        self.initial_category = initial_category
        self.panel_instances: dict[int, SettingsPanel] = {}
        self.current_panel: SettingsPanel | None = None
        super().__init__(parent, title=title)
        self._build_layout()
        self.SetMinSize(self.MIN_SIZE)
        self.SetSize(self.INITIAL_SIZE)
        self.CentreOnParent()

    def _get_initial_category_index(self, initial_category) -> int:
        if initial_category is None:
            return 0
        if initial_category not in self.category_classes:
            raise ValueError("initial_category is not registered")
        return self.category_classes.index(initial_category)

    def _cycled_category_index(self, current_index: int, step: int) -> int:
        return (current_index + step) % len(self.category_classes)

    def _get_category_panel(self, index: int) -> SettingsPanel:
        panel = self.panel_instances.get(index)
        if panel is None:
            panel = self.category_classes[index](self.content_panel, self)
            self._content_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
            self.panel_instances[index] = panel
        return panel

    def _current_category_index(self) -> int:
        selection = self.category_list.GetSelection()
        if selection < 0:
            return 0
        return selection

    def _change_category(self, index: int) -> None:
        if self.current_panel is not None:
            self.current_panel.on_panel_deactivated()
        panel = self._get_category_panel(index)
        panel.on_panel_activated()
        self._layout_container.SetupScrolling(scroll_x=False, scroll_y=True)
        self._layout_container.Layout()
        self._after_category_change(panel)
        self.current_panel = panel

    def _after_category_change(self, panel: SettingsPanel) -> None:
        pass

    def _build_layout(self) -> None:
        sizer = wx.GridBagSizer(vgap=5, hgap=5)
        label = wx.StaticText(self, label=_("Categories:"))
        sizer.Add(label, pos=(0, 0), span=(1, 2), flag=wx.ALL, border=5)

        self.category_list = wx.ListCtrl(
            self,
            style=wx.LC_SINGLE_SEL | wx.LC_REPORT | wx.BORDER_SUNKEN,
        )
        self.category_list.InsertColumn(0, _("Category"))
        self.category_list.SetMinSize((150, 10))
        for category_class in self.category_classes:
            self.category_list.Append((category_class.title.replace("&", ""),))
        sizer.Add(
            self.category_list,
            pos=(1, 0),
            flag=wx.EXPAND | wx.ALL,
            border=5,
        )

        self.content_panel = ScrolledPanel(
            self,
            style=wx.BORDER_SUNKEN,
        )
        self._layout_container = self.content_panel
        self._content_sizer = wx.BoxSizer(wx.VERTICAL)
        self.content_panel.SetSizer(self._content_sizer)
        sizer.Add(
            self.content_panel,
            pos=(1, 1),
            flag=wx.EXPAND | wx.ALL,
            border=5,
        )

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(self, wx.ID_OK, _("OK"))
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        cancel_button = wx.Button(self, wx.ID_CANCEL, _("Cancel"))
        cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        apply_button = wx.Button(self, wx.ID_APPLY, _("Apply"))
        apply_button.Bind(wx.EVT_BUTTON, self.on_apply)
        button_sizer.Add(ok_button, flag=wx.ALL, border=5)
        button_sizer.Add(cancel_button, flag=wx.ALL, border=5)
        button_sizer.Add(apply_button, flag=wx.ALL, border=5)
        sizer.Add(
            button_sizer,
            pos=(2, 0),
            span=(1, 2),
            flag=wx.ALIGN_RIGHT | wx.ALL,
            border=5,
        )

        sizer.AddGrowableRow(1)
        sizer.AddGrowableCol(0, proportion=1)
        sizer.AddGrowableCol(1, proportion=3)
        self.SetSizer(sizer)

        self.category_list.Bind(
            wx.EVT_LIST_ITEM_SELECTED,
            self._on_category_selected,
        )
        self.category_list.Bind(
            wx.EVT_LIST_ITEM_FOCUSED,
            self._on_category_selected,
        )
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        initial_index = self._get_initial_category_index(self.initial_category)
        self.category_list.SetSelection(initial_index)
        self.category_list.Focus(initial_index)
        self._change_category(initial_index)

    def _on_category_selected(self, event) -> None:
        index = event.GetSelection()
        if index < 0:
            return
        self._change_category(index)

    def _on_char_hook(self, event) -> None:
        if event.ControlDown() and event.GetKeyCode() == wx.WXK_TAB:
            step = -1 if event.ShiftDown() else 1
            next_index = self._cycled_category_index(
                self._current_category_index(),
                step,
            )
            self.category_list.SetSelection(next_index)
            self.category_list.Focus(next_index)
            self._change_category(next_index)
            return
        event.Skip()
