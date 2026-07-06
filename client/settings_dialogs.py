from __future__ import annotations

import gettext
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import sys

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from braille.tables import listTables
from settings_state import DotExpressSettingsSnapshot
from translation.settings import (
    MAX_CONVERSION_WIDTH,
    MIN_CONVERSION_WIDTH,
    TranslationSettings,
)
from view_settings import (
    VIEW_FONT_SIZE_MAX,
    VIEW_FONT_SIZE_MIN,
    ViewSettings,
    normalize_view_settings,
)


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


@dataclass(frozen=True)
class TableOption:
    file_name: str
    display_name: str


_OUTPUT_MODES: list[tuple[str, str]] = [
    ("unicode", _("Unicode")),
    ("ascii", _("ASCII")),
]

_VIEW_SCHEME_OPTIONS: list[tuple[str, str]] = [
    ("light", _("Light")),
    ("dark", _("Dark")),
]

_BRAILLE_FONT_OPTIONS: list[tuple[str, str]] = [
    ("default", _("Default")),
    ("simbraille", _("SimBraille")),
]


class TranslationSettingsPanel(SettingsPanel):
    title = _("Translation")
    panel_description = _(
        "Translation output mode, width, and dictionary options"
    )

    def make_settings(self) -> None:
        self.dictionary_names = list(self.owner.dictionary_names)
        settings = self.owner.snapshot.translation
        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        output_label = wx.StaticText(self, label=_("Braille Type"))
        self.output_choice = wx.Choice(
            self,
            choices=[label for _key, label in _OUTPUT_MODES],
        )
        grid.Add(output_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.output_choice, 1, wx.EXPAND)

        width_label = wx.StaticText(self, label=_("Width"))
        self.width_spin = wx.SpinCtrl(
            self,
            min=MIN_CONVERSION_WIDTH,
            max=MAX_CONVERSION_WIDTH,
            initial=max(
                MIN_CONVERSION_WIDTH,
                min(MAX_CONVERSION_WIDTH, settings.width),
            ),
        )
        grid.Add(width_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.width_spin, 1, wx.EXPAND)

        dictionary_label = wx.StaticText(self, label=_("Dictionary"))
        self.dictionary_choice = wx.Choice(self, choices=self.dictionary_names)
        grid.Add(dictionary_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.dictionary_choice, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(sizer)
        self._select_output_mode(settings.output_mode)
        self._select_dictionary(settings.selected_dictionary)

    def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
        settings = snapshot.translation
        self.width_spin.SetValue(
            max(
                MIN_CONVERSION_WIDTH,
                min(MAX_CONVERSION_WIDTH, settings.width),
            )
        )
        self._select_output_mode(settings.output_mode)
        self._select_dictionary(settings.selected_dictionary)

    def on_save(self, snapshot: DotExpressSettingsSnapshot) -> DotExpressSettingsSnapshot:
        value = TranslationSettings(
            output_mode=self._selected_output_mode(),
            width=self.width_spin.GetValue(),
            selected_dictionary=self._selected_dictionary(),
        )
        return snapshot.with_translation(value)

    def _selected_output_mode(self) -> str:
        index = self.output_choice.GetSelection()
        if index < 0 or index >= len(_OUTPUT_MODES):
            return _OUTPUT_MODES[0][0]
        return _OUTPUT_MODES[index][0]

    def _selected_dictionary(self) -> str:
        if not self.dictionary_names:
            return ""
        index = self.dictionary_choice.GetSelection()
        if index < 0 or index >= len(self.dictionary_names):
            return self.dictionary_names[0]
        return self.dictionary_names[index]

    def _select_output_mode(self, output_mode: str) -> None:
        index = next(
            (idx for idx, (key, _label) in enumerate(_OUTPUT_MODES) if key == output_mode),
            0,
        )
        self.output_choice.SetSelection(index)

    def _select_dictionary(self, dictionary_name: str) -> None:
        if not self.dictionary_names:
            self.dictionary_choice.SetSelection(wx.NOT_FOUND)
            self.dictionary_choice.Disable()
            return
        index = next(
            (idx for idx, name in enumerate(self.dictionary_names) if name == dictionary_name),
            0,
        )
        self.dictionary_choice.SetSelection(index)


class TranslationTablesPanel(SettingsPanel):
    title = _("Translation Tables")
    panel_description = _(
        "Translation table mappings for different languages"
    )

    CHOICE_SPECS: list[tuple[str, str, str | None]] = [
        ("default", _("Default Translation Table"), None),
        ("en", _("English Translation Table"), "en"),
        ("zh", _("Chinese Translation Table"), "zh"),
        ("ja", _("Japanese Translation Table"), "ja"),
        ("math", _("Math Translation Table"), None),
    ]

    def make_settings(self) -> None:
        self.table_options = self._load_table_options()
        self._choice_controls: dict[str, wx.Choice] = {}
        self._options_by_key: dict[str, list[TableOption]] = {}
        language_map = self.owner.snapshot.translation_tables
        grid = wx.FlexGridSizer(len(self.CHOICE_SPECS), 2, 8, 8)
        grid.AddGrowableCol(1, 1)
        for key, label, lang_code in self.CHOICE_SPECS:
            static_lbl = wx.StaticText(self, label=label)
            options = self._options_for_key(key, lang_code)
            if key not in {"default", "math"}:
                options = [TableOption(file_name="", display_name=_("None selected"))] + options
            choice = wx.Choice(self)
            choice.AppendItems([option.display_name for option in options])
            self._choice_controls[key] = choice
            self._options_by_key[key] = options
            grid.Add(static_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            grid.Add(choice, 1, wx.EXPAND)
            if not options:
                choice.Disable()
            self._select_choice_value(key, language_map.get(key))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(sizer)

    def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
        language_map = snapshot.translation_tables
        for key, _label, _lang in self.CHOICE_SPECS:
            self._select_choice_value(key, language_map.get(key))

    def is_valid(self) -> bool:
        return bool(
            self._selected_file_name("default")
            and self._selected_file_name("math")
        )

    def on_save(self, snapshot: DotExpressSettingsSnapshot) -> DotExpressSettingsSnapshot:
        values = {
            key: self._selected_file_name(key)
            for key, _label, _lang in self.CHOICE_SPECS
        }
        return snapshot.with_translation_tables(values)

    def _selected_file_name(self, key: str) -> str:
        option = self._get_selected_option(key)
        return option.file_name if option else ""

    def _get_selected_option(self, key: str) -> TableOption | None:
        choice = self._choice_controls.get(key)
        if not choice:
            return None
        selection = choice.GetSelection()
        if selection == wx.NOT_FOUND:
            return None
        options = self._options_by_key.get(key, [])
        if selection >= len(options):
            return None
        return options[selection]

    def _select_choice_value(self, key: str, file_name: str | None) -> None:
        choice = self._choice_controls[key]
        options = self._options_by_key[key]
        if not options:
            choice.SetSelection(wx.NOT_FOUND)
            return
        index = next(
            (idx for idx, option in enumerate(options) if option.file_name == file_name),
            None,
        )
        if index is None:
            index = 0
        choice.SetSelection(index)

    def _options_for_lang(self, lang_code: str | None) -> list[TableOption]:
        if lang_code is None:
            return self.table_options
        prefix = lang_code.lower()
        return [
            option
            for option in self.table_options
            if option.file_name.lower().startswith(prefix)
        ]

    def _options_for_key(self, key: str, lang_code: str | None) -> list[TableOption]:
        if key == "math":
            return [
                TableOption(file_name="UEB", display_name="UEB"),
                TableOption(file_name="Nemeth", display_name="Nemeth"),
            ]
        return self._options_for_lang(lang_code)

    def _load_table_options(self) -> list[TableOption]:
        tables = [table for table in listTables() if getattr(table, "output", False)]
        options = [
            TableOption(file_name=table.fileName, display_name=_(table.displayName))
            for table in tables
        ]
        return sorted(options, key=lambda option: option.display_name.lower())


class ViewSettingsPanel(SettingsPanel):
    title = _("View")
    panel_description = _(
        "Font, font size, and color scheme for the main window input and output areas"
    )

    def make_settings(self) -> None:
        self.font_size_dirty = False
        view = self.owner.snapshot.view
        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        font_size_label = wx.StaticText(self, label=_("Font Size"))
        self.font_size_spin = wx.SpinCtrl(
            self,
            min=VIEW_FONT_SIZE_MIN,
            max=VIEW_FONT_SIZE_MAX,
            initial=max(
                VIEW_FONT_SIZE_MIN,
                min(VIEW_FONT_SIZE_MAX, view.font_size),
            ),
        )
        grid.Add(font_size_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.font_size_spin, 1, wx.EXPAND)

        scheme_label = wx.StaticText(self, label=_("Scheme"))
        self.scheme_choice = wx.Choice(
            self,
            choices=[label for _key, label in _VIEW_SCHEME_OPTIONS],
        )
        grid.Add(scheme_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.scheme_choice, 1, wx.EXPAND)

        braille_font_label = wx.StaticText(self, label=_("Braille Font"))
        self.braille_font_choice = wx.Choice(
            self,
            choices=[label for _key, label in _BRAILLE_FONT_OPTIONS],
        )
        grid.Add(braille_font_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.braille_font_choice, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(sizer)
        self.font_size_spin.Bind(wx.EVT_SPINCTRL, self._on_font_size_changed)
        self.font_size_spin.Bind(wx.EVT_TEXT, self._on_font_size_changed)
        self._select_scheme(view.scheme)
        self._select_braille_font(view.braille_font)

    def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
        view = snapshot.view
        self.font_size_spin.SetValue(
            max(
                VIEW_FONT_SIZE_MIN,
                min(VIEW_FONT_SIZE_MAX, view.font_size),
            )
        )
        self._select_scheme(view.scheme)
        self._select_braille_font(view.braille_font)
        self.font_size_dirty = False

    def on_save(self, snapshot: DotExpressSettingsSnapshot) -> DotExpressSettingsSnapshot:
        value = normalize_view_settings(
            ViewSettings(
                self.font_size_spin.GetValue(),
                self._selected_scheme(),
                self._selected_braille_font(),
            )
        )
        return snapshot.with_view(value)

    def _on_font_size_changed(self, _event) -> None:
        self.font_size_dirty = True

    def _selected_scheme(self) -> str:
        index = self.scheme_choice.GetSelection()
        if index < 0 or index >= len(_VIEW_SCHEME_OPTIONS):
            return _VIEW_SCHEME_OPTIONS[0][0]
        return _VIEW_SCHEME_OPTIONS[index][0]

    def _selected_braille_font(self) -> str:
        index = self.braille_font_choice.GetSelection()
        if index < 0 or index >= len(_BRAILLE_FONT_OPTIONS):
            return _BRAILLE_FONT_OPTIONS[0][0]
        return _BRAILLE_FONT_OPTIONS[index][0]

    def _select_scheme(self, scheme: str) -> None:
        index = next(
            (idx for idx, (key, _label) in enumerate(_VIEW_SCHEME_OPTIONS) if key == scheme),
            0,
        )
        self.scheme_choice.SetSelection(index)

    def _select_braille_font(self, braille_font: str) -> None:
        index = next(
            (idx for idx, (key, _label) in enumerate(_BRAILLE_FONT_OPTIONS) if key == braille_font),
            0,
        )
        self.braille_font_choice.SetSelection(index)


CommitSettings = Callable[
    [DotExpressSettingsSnapshot],
    DotExpressSettingsSnapshot,
]


class DotExpressSettingsDialog(MultiCategorySettingsDialog):
    base_title = _("DotExpress Settings")
    category_classes = [
        TranslationSettingsPanel,
        TranslationTablesPanel,
        ViewSettingsPanel,
    ]
    _instance: "DotExpressSettingsDialog | None" = None

    def __init__(
        self,
        parent,
        *,
        snapshot: DotExpressSettingsSnapshot,
        dictionary_names: list[str],
        commit: CommitSettings,
        initial_category=None,
    ) -> None:
        self.snapshot = snapshot.copied()
        self.dictionary_names = list(dictionary_names)
        self.commit = commit
        super().__init__(
            parent,
            title=f"{self.base_title}: {self.category_classes[0].title}",
            initial_category=initial_category,
        )

    def _after_category_change(self, panel: SettingsPanel) -> None:
        self.SetTitle(f"{self.base_title}: {panel.title}")

    def _collect(self) -> DotExpressSettingsSnapshot | None:
        panels = list(self.panel_instances.values())
        for panel in panels:
            if not panel.is_valid():
                self.select_category(type(panel))
                panel.SetFocus()
                return None
        candidate = self.snapshot.copied()
        for panel in panels:
            candidate = panel.on_save(candidate)
        return candidate

    def on_apply(self, event=None) -> bool:
        candidate = self._collect()
        if candidate is None:
            return False
        self.snapshot = self.commit(candidate).copied()
        for panel in self.panel_instances.values():
            panel.load_snapshot(self.snapshot)
        return True

    def on_ok(self, event=None) -> None:
        if self.on_apply():
            self._destroy()

    def on_cancel(self, event=None) -> None:
        for panel in self.panel_instances.values():
            panel.on_discard()
        self._destroy()

    def _destroy(self) -> None:
        if DotExpressSettingsDialog._instance is self:
            DotExpressSettingsDialog._instance = None
        self.Destroy()

    def select_category(self, category_class) -> None:
        index = self.category_classes.index(category_class)
        self.category_list.SetSelection(index)
        self.category_list.Focus(index)
        self._change_category(index)

    @classmethod
    def show_singleton(
        cls,
        *,
        parent,
        snapshot: DotExpressSettingsSnapshot,
        dictionary_names: list[str],
        commit: CommitSettings,
        initial_category=None,
    ) -> "DotExpressSettingsDialog":
        if initial_category is not None and initial_category not in cls.category_classes:
            raise ValueError("initial_category is not registered")
        instance = cls._instance
        if instance is not None:
            try:
                instance.Iconize(False)
                if initial_category is not None:
                    instance.select_category(initial_category)
                instance.Raise()
                instance.SetFocus()
                return instance
            except Exception:
                cls._instance = None
        instance = cls(
            parent,
            snapshot=snapshot,
            dictionary_names=dictionary_names,
            commit=commit,
            initial_category=initial_category,
        )
        cls._instance = instance
        instance.Show()
        return instance

    @classmethod
    def sync_open_font_size(cls, font_size: int) -> None:
        instance = cls._instance
        if instance is None:
            return
        view_panel = None
        for panel in instance.panel_instances.values():
            if isinstance(panel, ViewSettingsPanel):
                view_panel = panel
                break
        if view_panel is None:
            return
        if getattr(view_panel, "font_size_dirty", False):
            return
        view_panel.font_size_spin.SetValue(
            max(
                VIEW_FONT_SIZE_MIN,
                min(VIEW_FONT_SIZE_MAX, font_size),
            )
        )
        instance.snapshot = instance.snapshot.with_view(
            normalize_view_settings(
                ViewSettings(
                    font_size,
                    instance.snapshot.view.scheme,
                    instance.snapshot.view.braille_font,
                )
            )
        )
