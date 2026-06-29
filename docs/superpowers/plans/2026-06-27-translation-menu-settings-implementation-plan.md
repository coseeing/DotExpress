# Translation Menu and Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將主視窗的 `Conversion` 控制列改為鍵盤可操作的 `Translation` 選單，並以獨立的轉譯設定與字典管理對話框取代原本的內嵌控制項。

**Architecture:** 以小型 `TranslationSettings` 資料物件作為執行期設定邊界，讓主視窗不再依賴已移除的 wx 控制項取得轉譯參數。兩個新對話框留在既有 `client/dialog.py`，主視窗負責設定持久化與字典檔案操作；字典管理對話框只負責清單、按鈕狀態和呼叫注入的動作，避免複製既有管理邏輯。

**Tech Stack:** Python 3、wxPython、`unittest`、gettext、既有 `config.py` 與 `dictionaries` 模組

---

## 檔案配置

- Create: `client/translation/__init__.py` — 將 `translation` 定義為獨立套件。
- Create: `client/translation/settings.py` — 定義 immutable `TranslationSettings`，以及載入、正規化與持久化函式。
- Create: `client/ui/translation_menu.py` — 定義固定且可單元測試的 Translation 選單項目順序。
- Create: `client/tests/test_translation_settings.py` — 驗證設定載入、fallback、範圍限制與一次提交。
- Create: `client/tests/test_translation_menu.py` — 驗證四個選單項目的 key、label 與順序。
- Modify: `client/dialog.py` — 新增 `TranslationSettingsDialog` 與 `DictionaryManagementDialog`。
- Modify: `client/gui.py` — 移除 Conversion 列，建立 Translation 選單，串接兩個新對話框，並讓轉換流程改讀 `TranslationSettings`。
- Modify: `client/ui/section_navigation.py` — 從 F6 區塊順序移除 `CONVERSION_SECTION`。
- Modify: `client/tests/test_section_navigation.py` — 更新四個可見區塊的循環預期。
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` — 新增與修正 Translation 選單及對話框的台灣繁體中文翻譯。
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` — 重新編譯 gettext catalog。
- Reference: `docs/superpowers/specs/2026-06-27-translation-menu-settings-design_zh-TW.md`

### Task 1: 建立轉譯設定狀態邊界

**Files:**
- Create: `client/translation/__init__.py`
- Create: `client/translation/settings.py`
- Create: `client/tests/test_translation_settings.py`
- Reference: `client/config.py`

- [ ] **Step 1: 寫入設定載入與正規化的失敗測試**

```python
# client/tests/test_translation_settings.py
import unittest
from unittest.mock import patch

from translation.settings import (
    DEFAULT_TRANSLATION_SETTINGS,
    TranslationSettings,
    load_translation_settings,
    save_translation_settings,
)


class TranslationSettingsTest(unittest.TestCase):
    @patch("translation.settings.get_selected_dictionary", return_value="missing")
    @patch("translation.settings.get_conversion_width", return_value=999)
    @patch("translation.settings.get_output_mode", return_value="invalid")
    def test_load_normalizes_invalid_config(
        self,
        _get_output_mode,
        _get_conversion_width,
        _get_selected_dictionary,
    ) -> None:
        settings = load_translation_settings(["default", "math"])

        self.assertEqual(
            settings,
            TranslationSettings(
                output_mode=DEFAULT_TRANSLATION_SETTINGS.output_mode,
                width=200,
                selected_dictionary="default",
            ),
        )

    @patch("translation.settings.get_selected_dictionary", return_value="math")
    @patch("translation.settings.get_conversion_width", return_value=52)
    @patch("translation.settings.get_output_mode", return_value="ascii")
    def test_load_keeps_valid_config(
        self,
        _get_output_mode,
        _get_conversion_width,
        _get_selected_dictionary,
    ) -> None:
        self.assertEqual(
            load_translation_settings(["default", "math"]),
            TranslationSettings("ascii", 52, "math"),
        )

    @patch("translation.settings.set_selected_dictionary")
    @patch("translation.settings.set_conversion_width")
    @patch("translation.settings.set_output_mode")
    def test_save_persists_one_complete_settings_value(
        self,
        set_output_mode,
        set_conversion_width,
        set_selected_dictionary,
    ) -> None:
        settings = TranslationSettings("ascii", 64, "math")

        save_translation_settings(settings)

        set_output_mode.assert_called_once_with("ascii")
        set_conversion_width.assert_called_once_with(64)
        set_selected_dictionary.assert_called_once_with("math")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試，確認因模組尚未存在而失敗**

Run: `cd client && python3 -m unittest tests.test_translation_settings -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'translation'`.

- [ ] **Step 3: 建立套件與最小設定實作**

```python
# client/translation/__init__.py
"""Translation UI state helpers."""
```

```python
# client/translation/settings.py
from dataclasses import dataclass

from config import (
    DEFAULT_CONVERSION_WIDTH,
    DEFAULT_OUTPUT_MODE,
    get_conversion_width,
    get_output_mode,
    get_selected_dictionary,
    set_conversion_width,
    set_output_mode,
    set_selected_dictionary,
)
from dictionaries.actions import resolve_dictionary_selection


MIN_WIDTH = 10
MAX_WIDTH = 200
OUTPUT_MODES = ("unicode", "ascii")


@dataclass(frozen=True)
class TranslationSettings:
    output_mode: str
    width: int
    selected_dictionary: str


DEFAULT_TRANSLATION_SETTINGS = TranslationSettings(
    output_mode=DEFAULT_OUTPUT_MODE,
    width=DEFAULT_CONVERSION_WIDTH,
    selected_dictionary="default",
)


def normalize_translation_settings(
    settings: TranslationSettings,
    dictionary_names: list[str],
) -> TranslationSettings:
    output_mode = (
        settings.output_mode
        if settings.output_mode in OUTPUT_MODES
        else DEFAULT_TRANSLATION_SETTINGS.output_mode
    )
    width = max(MIN_WIDTH, min(MAX_WIDTH, settings.width))
    selected_dictionary = resolve_dictionary_selection(
        dictionary_names,
        settings.selected_dictionary,
    )
    return TranslationSettings(output_mode, width, selected_dictionary)


def load_translation_settings(dictionary_names: list[str]) -> TranslationSettings:
    return normalize_translation_settings(
        TranslationSettings(
            output_mode=get_output_mode(DEFAULT_OUTPUT_MODE),
            width=get_conversion_width(DEFAULT_CONVERSION_WIDTH),
            selected_dictionary=get_selected_dictionary("default"),
        ),
        dictionary_names,
    )


def save_translation_settings(settings: TranslationSettings) -> None:
    set_output_mode(settings.output_mode)
    set_conversion_width(settings.width)
    set_selected_dictionary(settings.selected_dictionary)
```

- [ ] **Step 4: 執行設定與既有 config 測試**

Run: `cd client && python3 -m unittest tests.test_translation_settings tests.test_config -v`

Expected: PASS.

- [ ] **Step 5: 提交設定邊界**

```bash
git add client/translation client/tests/test_translation_settings.py
git commit -m "refactor: add translation settings state"
```

### Task 2: 定義 Translation 選單規格

**Files:**
- Create: `client/ui/translation_menu.py`
- Create: `client/tests/test_translation_menu.py`

- [ ] **Step 1: 寫入選單順序的失敗測試**

```python
# client/tests/test_translation_menu.py
import unittest

from ui.translation_menu import get_translation_menu_items


class TranslationMenuTest(unittest.TestCase):
    def test_menu_contains_four_commands_in_required_order(self) -> None:
        self.assertEqual(
            get_translation_menu_items(),
            [
                ("convert", "Convert"),
                ("settings", "Translation Settings..."),
                ("tables", "Translation Tables Setting..."),
                ("dictionaries", "Dictionary Management..."),
            ],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試，確認因模組尚未存在而失敗**

Run: `cd client && python3 -m unittest tests.test_translation_menu -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'ui.translation_menu'`.

- [ ] **Step 3: 實作固定選單描述**

```python
# client/ui/translation_menu.py
from __future__ import annotations


def get_translation_menu_items() -> list[tuple[str, str]]:
    return [
        ("convert", "Convert"),
        ("settings", "Translation Settings..."),
        ("tables", "Translation Tables Setting..."),
        ("dictionaries", "Dictionary Management..."),
    ]
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd client && python3 -m unittest tests.test_translation_menu -v`

Expected: PASS.

- [ ] **Step 5: 提交選單規格**

```bash
git add client/ui/translation_menu.py client/tests/test_translation_menu.py
git commit -m "feat: define translation menu commands"
```

### Task 3: 新增 Translation Settings 對話框

**Files:**
- Modify: `client/dialog.py`
- Reference: `client/translation/settings.py`

- [ ] **Step 1: 在 `client/dialog.py` 匯入設定型別**

```python
from translation.settings import MAX_WIDTH, MIN_WIDTH, TranslationSettings
```

- [ ] **Step 2: 在 `TranslationTableDialog` 前新增設定對話框**

```python
class TranslationSettingsDialog(wx.Dialog):
    """Edits a temporary copy of translation settings."""

    def __init__(
        self,
        parent: wx.Window | None,
        settings: TranslationSettings,
        dictionary_names: list[str],
    ):
        super().__init__(parent, title=_("Translation Settings"))
        self._output_modes = [("unicode", _("Unicode")), ("ascii", _("ASCII"))]
        self._dictionary_names = list(dictionary_names)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(3, 2, 8, 8)

        grid.Add(wx.StaticText(self, label=_("Braille Type")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.output_choice = wx.Choice(
            self,
            choices=[label for _key, label in self._output_modes],
        )
        grid.Add(self.output_choice, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label=_("Width")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.width_spin = wx.SpinCtrl(
            self,
            min=MIN_WIDTH,
            max=MAX_WIDTH,
            initial=settings.width,
        )
        grid.Add(self.width_spin, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label=_("Dictionary")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.dictionary_choice = wx.Choice(self, choices=self._dictionary_names)
        grid.Add(self.dictionary_choice, 1, wx.EXPAND)
        grid.AddGrowableCol(1, 1)

        self._select_output_mode(settings.output_mode)
        self._select_dictionary(settings.selected_dictionary)
        main_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons:
            main_sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.SetSizerAndFit(main_sizer)

    def _select_output_mode(self, output_mode: str) -> None:
        keys = [key for key, _label in self._output_modes]
        self.output_choice.SetSelection(keys.index(output_mode))

    def _select_dictionary(self, dictionary_name: str) -> None:
        self.dictionary_choice.SetSelection(
            self._dictionary_names.index(dictionary_name)
        )

    def get_settings(self) -> TranslationSettings:
        output_index = self.output_choice.GetSelection()
        dictionary_index = self.dictionary_choice.GetSelection()
        return TranslationSettings(
            output_mode=self._output_modes[output_index][0],
            width=self.width_spin.GetValue(),
            selected_dictionary=self._dictionary_names[dictionary_index],
        )

    def __enter__(self) -> "TranslationSettingsDialog":
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:
        self.Destroy()
```

- [ ] **Step 3: 執行語法與 import 檢查**

Run: `python3 -m py_compile client/dialog.py client/translation/settings.py`

Expected: exit code 0.

- [ ] **Step 4: 在 Windows 手動建立對話框，確認初值與暫存行為**

Run: `cd client && python gui.py`

Expected:

- 對話框依目前設定顯示 `Braille Type`、`Width`、`Dictionary`。
- 修改欄位後按 `Cancel` 不會提交值。
- `Tab` 可依序走訪三個欄位及 `OK`、`Cancel`。

- [ ] **Step 5: 提交設定對話框**

```bash
git add client/dialog.py
git commit -m "feat: add translation settings dialog"
```

### Task 4: 新增 Dictionary Management 對話框

**Files:**
- Modify: `client/dialog.py`
- Reference: `client/dictionaries/actions.py`

- [ ] **Step 1: 在 `client/dialog.py` 新增 callback 型別 import**

```python
from collections.abc import Callable
from dictionaries.actions import get_action_availability
```

- [ ] **Step 2: 在 `TranslationSettingsDialog` 前新增字典管理對話框**

```python
class DictionaryManagementDialog(wx.Dialog):
    """Lists dictionaries and delegates immediate lifecycle actions."""

    def __init__(
        self,
        parent: wx.Window | None,
        dictionary_names: list[str],
        selected_name: str,
        on_add: Callable[[wx.Window], str | None],
        on_delete: Callable[[wx.Window, str], str | None],
        on_rename: Callable[[wx.Window, str], str | None],
        on_import: Callable[[wx.Window], str | None],
        on_export: Callable[[wx.Window, str], None],
    ):
        super().__init__(
            parent,
            title=_("Dictionary Management"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._dictionary_names = list(dictionary_names)
        self._selected_name = selected_name
        self._on_add = on_add
        self._on_delete = on_delete
        self._on_rename = on_rename
        self._on_import = on_import
        self._on_export = on_export
        self.edit_dictionary_name: str | None = None
        self._build_ui()
        self.refresh_dictionaries(dictionary_names, selected_name)

    def _build_ui(self) -> None:
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.list_ctrl = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL,
        )
        self.list_ctrl.InsertColumn(0, _("Dictionary"), width=360)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit)
        main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 12)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.add_button = wx.Button(self, label=_("Add"))
        self.delete_button = wx.Button(self, label=_("Delete"))
        self.rename_button = wx.Button(self, label=_("Rename"))
        self.edit_button = wx.Button(self, label=_("Edit"))
        self.import_button = wx.Button(self, label=_("Import"))
        self.export_button = wx.Button(self, label=_("Export"))
        for button in (
            self.add_button,
            self.delete_button,
            self.rename_button,
            self.edit_button,
            self.import_button,
            self.export_button,
        ):
            button_sizer.Add(button, 0, wx.RIGHT, 8)
        main_sizer.Add(button_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        close_button = self.CreateButtonSizer(wx.CLOSE)
        if close_button:
            main_sizer.Add(close_button, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.add_button.Bind(wx.EVT_BUTTON, self._add)
        self.delete_button.Bind(wx.EVT_BUTTON, self._delete)
        self.rename_button.Bind(wx.EVT_BUTTON, self._rename)
        self.edit_button.Bind(wx.EVT_BUTTON, self._on_edit)
        self.import_button.Bind(wx.EVT_BUTTON, self._import)
        self.export_button.Bind(wx.EVT_BUTTON, self._export)
        self.Bind(wx.EVT_BUTTON, lambda _event: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)
        self.SetSizer(main_sizer)
        self.SetMinSize((650, 400))

    def refresh_dictionaries(
        self,
        dictionary_names: list[str],
        preferred_name: str | None,
    ) -> None:
        self._dictionary_names = list(dictionary_names)
        self.list_ctrl.DeleteAllItems()
        for name in self._dictionary_names:
            self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), name)
        if self._dictionary_names:
            selected = (
                preferred_name
                if preferred_name in self._dictionary_names
                else self._dictionary_names[0]
            )
            index = self._dictionary_names.index(selected)
            self.list_ctrl.Select(index)
            self.list_ctrl.Focus(index)
        self._update_button_states()

    def _get_selected_name(self) -> str | None:
        index = self.list_ctrl.GetFirstSelected()
        if index == wx.NOT_FOUND:
            return None
        return self._dictionary_names[index]

    def _update_button_states(self) -> None:
        selected_name = self._get_selected_name() or ""
        availability = get_action_availability(
            self._dictionary_names,
            selected_name,
        )
        self.edit_button.Enable(availability.edit)
        self.delete_button.Enable(availability.delete)
        self.rename_button.Enable(availability.rename)
        self.export_button.Enable(availability.export)

    def _refresh_after(self, preferred_name: str | None) -> None:
        if preferred_name is None:
            return
        parent = self.GetParent()
        names = parent.get_dictionary_names_for_dialog()
        self.refresh_dictionaries(names, preferred_name)

    def _add(self, _event: wx.CommandEvent) -> None:
        self._refresh_after(self._on_add(self))

    def _delete(self, _event: wx.CommandEvent) -> None:
        selected = self._get_selected_name()
        if selected is not None:
            self._refresh_after(self._on_delete(self, selected))

    def _rename(self, _event: wx.CommandEvent) -> None:
        selected = self._get_selected_name()
        if selected is not None:
            self._refresh_after(self._on_rename(self, selected))

    def _import(self, _event: wx.CommandEvent) -> None:
        self._refresh_after(self._on_import(self))

    def _export(self, _event: wx.CommandEvent) -> None:
        selected = self._get_selected_name()
        if selected is not None:
            self._on_export(self, selected)

    def _on_edit(self, _event: wx.Event) -> None:
        selected = self._get_selected_name()
        if selected is None:
            return
        self.edit_dictionary_name = selected
        self.EndModal(wx.ID_EDIT)

    def _on_selection_changed(self, event: wx.ListEvent) -> None:
        self._update_button_states()
        event.Skip()

    def __enter__(self) -> "DictionaryManagementDialog":
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:
        self.Destroy()
```

- [ ] **Step 3: 執行語法檢查**

Run: `python3 -m py_compile client/dialog.py`

Expected: exit code 0.

- [ ] **Step 4: 在 Windows 手動驗證清單與按鈕狀態**

Run: `cd client && python gui.py`

Expected:

- list view 顯示全部現有字典。
- 按鈕順序為 Add、Delete、Rename、Edit、Import、Export。
- 選取 `default` 時 Delete、Rename 停用，Edit、Export 可用。
- 無選取項目時 Delete、Rename、Edit、Export 全部停用。
- 雙擊項目與按 Edit 都以 `wx.ID_EDIT` 關閉管理對話框。

- [ ] **Step 5: 提交字典管理對話框**

```bash
git add client/dialog.py
git commit -m "feat: add dictionary management dialog"
```

### Task 5: 將主視窗 Conversion 列改為 Translation 選單

**Files:**
- Modify: `client/gui.py`
- Reference: `client/dialog.py`
- Reference: `client/ui/translation_menu.py`

- [ ] **Step 1: 更新 imports**

移除 `build_actions_button_label`、`get_actions_menu_position`、`get_dictionary_action_labels` 與 `CONVERSION_SECTION` imports，新增：

```python
from translation.settings import (
    TranslationSettings,
    load_translation_settings,
    normalize_translation_settings,
    save_translation_settings,
)
from ui.translation_menu import get_translation_menu_items
from dialog import (
    DictionaryManagementDialog,
    DictionaryNameDialog,
    DocumentNameDialog,
    FileIssuesDialog,
    InvalidWorkspaceFilesDialog,
    SpeechSymbolsDialog,
    TranslationSettingsDialog,
    TranslationTableDialog,
)
```

- [ ] **Step 2: 讓初始化載入執行期轉譯設定**

在 `_initialize_state()` 中以字典名稱清單建立狀態：

```python
self._dictionary_names = list_dictionary_names(self.dictionary_dir)
self.translation_settings = load_translation_settings(self._dictionary_names)
```

從 `_initialize_state()` 回傳值移除 `output_mode` 與 `width`；保留 view 相關設定。

- [ ] **Step 3: 移除 Conversion 列及其控制項初始化**

將 `_create_main_layout()` 改為只建立內容區：

```python
def _create_main_layout(self, initial_settings: dict[str, str | int]) -> None:
    panel = wx.Panel(self)
    vbox = wx.BoxSizer(wx.VERTICAL)
    content_box = wx.BoxSizer(wx.HORIZONTAL)
    content_box.Add(
        self._create_document_list(panel),
        0,
        wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM,
        8,
    )
    content_box.Add(
        self._create_editor_area(panel, int(initial_settings["font_size"])),
        1,
        wx.EXPAND | wx.TOP | wx.RIGHT | wx.BOTTOM,
        8,
    )
    vbox.Add(content_box, 1, wx.EXPAND)
    panel.SetSizer(vbox)
```

完整刪除 `_create_conversion_controls()`，並從 `_apply_initial_settings()` 與 `_bind_events()` 移除所有 `table_btn`、`output_choice`、`width_spin`、`dictionary_choice`、`actions_btn`、`convert_btn` 的設定與 binding。

- [ ] **Step 4: 建立 Translation 選單並綁定四個 handler**

```python
def _create_menu_bar(self) -> wx.MenuBar:
    menu_bar = wx.MenuBar()
    translation_menu = wx.Menu()
    handlers = {
        "convert": self.on_convert,
        "settings": self.on_open_translation_settings,
        "tables": self.on_open_table_dialog,
        "dictionaries": self.on_open_dictionary_management,
    }
    for key, label in get_translation_menu_items():
        item = translation_menu.Append(wx.ID_ANY, _(label))
        self.Bind(wx.EVT_MENU, handlers[key], item)
    menu_bar.Append(translation_menu, _("Translation"))

    help_menu = wx.Menu()
    website_item = help_menu.Append(wx.ID_ANY, _("Coseeing Website"))
    self.Bind(wx.EVT_MENU, self.on_open_coseeing_website, website_item)
    about_item = help_menu.Append(wx.ID_ABOUT, _("About"))
    self.Bind(wx.EVT_MENU, self.on_about, about_item)
    menu_bar.Append(help_menu, _("Help"))
    return menu_bar
```

- [ ] **Step 5: 新增設定對話框的 OK/Cancel 流程**

```python
def on_open_translation_settings(self, _event) -> None:
    self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
    with TranslationSettingsDialog(
        self,
        self.translation_settings,
        self._dictionary_names,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:
            return
        self.translation_settings = normalize_translation_settings(
            dialog.get_settings(),
            self._dictionary_names,
        )
        save_translation_settings(self.translation_settings)
```

這一步只在 `wx.ID_OK` 分支指派與儲存，確保 `Cancel` 不改變執行期或持久化狀態。

- [ ] **Step 6: 將字典 refresh 改為不依賴 Choice 控制項**

```python
def _refresh_dictionary_names(self, preferred_name: str | None = None) -> str:
    ensure_default_dictionary(self.dictionary_dir)
    self._dictionary_names = list_dictionary_names(self.dictionary_dir)
    selected_name = resolve_dictionary_selection(
        self._dictionary_names,
        preferred_name,
    )
    self.translation_settings = TranslationSettings(
        output_mode=self.translation_settings.output_mode,
        width=self.translation_settings.width,
        selected_dictionary=selected_name,
    )
    set_selected_dictionary(selected_name)
    return selected_name

def get_dictionary_names_for_dialog(self) -> list[str]:
    return list(self._dictionary_names)

def _get_selected_dictionary_path(self) -> Path:
    return dictionary_path_for_name(
        self.translation_settings.selected_dictionary,
        self.dictionary_dir,
    )
```

刪除 `_set_output_mode_selection()`、`_get_selected_output_mode()`、`_refresh_dictionary_choice()`、`_get_selected_dictionary_name()`、`on_output_mode_change()`、`on_width_change()`、`on_dictionary_change()` 與 `on_open_dictionary_actions()`。

- [ ] **Step 7: 將既有字典動作改為可由管理對話框呼叫**

將目前 `on_add_dictionary()`、`on_delete_dictionary()`、`on_rename_dictionary()`、`on_import_dictionary()`、`on_export_dictionary()` 的函式內容分別移到下列新簽章；檔案操作與錯誤分支維持原程式碼，不另複製一份。套用以下明確替換：

| 原本來源 | 新簽章 | 參數來源替換 | 成功回傳 |
|---|---|---|---|
| `on_add_dictionary()` | `add_dictionary(self, parent: wx.Window) -> str \| None` | `DictionaryNameDialog(self)` → `DictionaryNameDialog(parent)` | `return self._refresh_dictionary_names(path.stem)` |
| `on_delete_dictionary()` | `delete_dictionary_from_dialog(self, parent: wx.Window, selected_name: str) -> str \| None` | `_get_selected_dictionary_name()` → `selected_name`；MessageBox parent → `parent` | `return self._refresh_dictionary_names(preferred_name)` |
| `on_rename_dictionary()` | `rename_dictionary_from_dialog(self, parent: wx.Window, selected_name: str) -> str \| None` | `_get_selected_dictionary_name()` → `selected_name`；`DictionaryNameDialog(self)` → `DictionaryNameDialog(parent)` | `return self._refresh_dictionary_names(path.stem)` |
| `on_import_dictionary()` | `import_dictionary_from_dialog(self, parent: wx.Window) -> str \| None` | `wx.FileDialog(self, ...)` 與 `DictionaryNameDialog(self)` 的 parent → `parent` | `return self._refresh_dictionary_names(path.stem)` |
| `on_export_dictionary()` | `export_dictionary_from_dialog(self, parent: wx.Window, selected_name: str) -> None` | `_get_selected_dictionary_name()` → `selected_name`；`wx.FileDialog(self, ...)` 的 parent → `parent` | 正常結束回傳 `None` |

Add、Delete、Rename、Import 的取消與所有 error branch 都明確 `return None`。所有 `wx.MessageBox(..., parent=self)` 改為 `parent=parent`；`_show_file_error()` 增加 `parent: wx.Window` 參數，並由這些函式傳入。完成移動後刪除五個舊 handler，確保只有一份字典檔案操作流程。

- [ ] **Step 8: 串接字典管理與 Edit 結束流程**

```python
def on_open_dictionary_management(self, _event) -> None:
    selected_name = self._refresh_dictionary_names(
        self.translation_settings.selected_dictionary
    )
    with DictionaryManagementDialog(
        self,
        self._dictionary_names,
        selected_name,
        self.add_dictionary,
        self.delete_dictionary_from_dialog,
        self.rename_dictionary_from_dialog,
        self.import_dictionary_from_dialog,
        self.export_dictionary_from_dialog,
    ) as dialog:
        result = dialog.ShowModal()
        edit_name = dialog.edit_dictionary_name

    if result != wx.ID_EDIT or edit_name is None:
        return
    dictionary_path = dictionary_path_for_name(edit_name, self.dictionary_dir)
    with SpeechSymbolsDialog(self, dictionary_path=dictionary_path) as editor:
        editor.ShowModal()
```

`SpeechSymbolsDialog` 必須在 `with DictionaryManagementDialog(...)` 區塊結束後才建立，藉此保證管理對話框已關閉；編輯器關閉後不重新開啟管理對話框。

- [ ] **Step 9: 讓同步與非同步轉換統一讀取執行期設定**

```python
def _convert_text_for_output(self, raw_text: str) -> str:
    if raw_text == "":
        return ""
    table_file = language_map_translate_table.get("default")
    if not table_file:
        raise ValueError(_("Please select a translation table first."))
    settings = self.translation_settings
    return convert_text_for_output(
        self._build_conversion_request(
            raw_text,
            table_file,
            settings.output_mode,
            settings.width,
            self._get_selected_dictionary_path(),
        )
    )

def on_convert(self, _event):
    if self._convert_thread and self._convert_thread.is_alive():
        return
    table_file = language_map_translate_table.get("default")
    if not table_file:
        wx.MessageBox(
            _("Please select a translation table first."),
            _("Info"),
            wx.OK | wx.ICON_INFORMATION,
            parent=self,
        )
        return
    settings = self.translation_settings
    self._start_conversion(
        table_file,
        self.input_txt.GetValue(),
        settings.width,
        settings.output_mode,
        self._get_selected_dictionary_path(),
    )
```

移除原本依賴 `output_choice` 是否選取的錯誤分支；`TranslationSettings` 保證 output mode 永遠有效。

- [ ] **Step 10: 更新 busy state**

```python
def _set_conversion_busy(self, busy: bool):
    self.GetMenuBar().EnableTop(0, not busy)
    for control in (self.document_list, self.input_txt):
        control.Enable(not busy)
```

這會在轉換期間停用整個 Translation 選單，同時保留既有 document list 與 source text 的 busy 行為。

- [ ] **Step 11: 執行靜態與既有核心測試**

Run:

```bash
python3 -m py_compile client/gui.py client/dialog.py
cd client && python3 -m unittest \
  tests.test_translation_settings \
  tests.test_translation_menu \
  tests.test_dictionary_actions \
  tests.test_dictionary_manager \
  tests.test_config -v
```

Expected: all tests PASS.

- [ ] **Step 12: 在 Windows 驗證主流程**

Run: `cd client && python gui.py`

Expected:

- 主視窗不再顯示 Conversion 列。
- `Alt` 可進入 Translation 與 Help 選單。
- Translation 四個項目順序與 spec 相同。
- 選單 Convert 與來源文字區的 `Ctrl+Enter` 都可轉換。
- Translation Settings 按 Cancel 不生效，按 OK 後下一次轉換使用新值。
- Translation Tables Setting 仍沿用既有 OK/Cancel 行為。
- Dictionary Management 的 Add/Delete/Rename/Import/Export 立即更新 list view。
- Edit 先關閉管理對話框，再開啟字典條目編輯器；關閉編輯器後停在主視窗。

- [ ] **Step 13: 提交主視窗整合**

```bash
git add client/gui.py
git commit -m "feat: move translation controls to menu"
```

### Task 6: 更新 F6 / Shift+F6 可見區塊循環

**Files:**
- Modify: `client/ui/section_navigation.py`
- Modify: `client/tests/test_section_navigation.py`
- Modify: `client/gui.py`

- [ ] **Step 1: 將測試改成四個可見區塊**

```python
# client/tests/test_section_navigation.py
import unittest

from ui.section_navigation import (
    BRAILLE_RESULT_SECTION,
    DOCUMENT_LIST_SECTION,
    SOURCE_TEXT_SECTION,
    VIEW_SECTION,
    get_adjacent_section,
)


class SectionNavigationTest(unittest.TestCase):
    def test_get_adjacent_section_moves_forward(self) -> None:
        self.assertEqual(
            get_adjacent_section(DOCUMENT_LIST_SECTION, step=1),
            VIEW_SECTION,
        )

    def test_get_adjacent_section_wraps_forward(self) -> None:
        self.assertEqual(
            get_adjacent_section(BRAILLE_RESULT_SECTION, step=1),
            DOCUMENT_LIST_SECTION,
        )

    def test_get_adjacent_section_moves_backward(self) -> None:
        self.assertEqual(
            get_adjacent_section(BRAILLE_RESULT_SECTION, step=-1),
            SOURCE_TEXT_SECTION,
        )

    def test_get_adjacent_section_wraps_backward(self) -> None:
        self.assertEqual(
            get_adjacent_section(DOCUMENT_LIST_SECTION, step=-1),
            BRAILLE_RESULT_SECTION,
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認舊順序會失敗**

Run: `cd client && python3 -m unittest tests.test_section_navigation -v`

Expected: FAIL because the current order still includes `CONVERSION_SECTION`.

- [ ] **Step 3: 移除 Conversion 區塊常數與順序項目**

```python
# client/ui/section_navigation.py
DOCUMENT_LIST_SECTION = "document_list"
VIEW_SECTION = "view"
SOURCE_TEXT_SECTION = "source_text"
BRAILLE_RESULT_SECTION = "braille_result"

SECTION_ORDER = [
    DOCUMENT_LIST_SECTION,
    VIEW_SECTION,
    SOURCE_TEXT_SECTION,
    BRAILLE_RESULT_SECTION,
]


def get_adjacent_section(current_section: str, step: int) -> str:
    index = SECTION_ORDER.index(current_section)
    return SECTION_ORDER[(index + step) % len(SECTION_ORDER)]
```

- [ ] **Step 4: 更新 BrailleFrame 的 focus 對照與無目前焦點 fallback**

`_get_section_controls()` 僅保留四個可見區塊，並把 `on_char_hook()` 的 fallback 改為：

```python
if current_section is None:
    target_section = (
        DOCUMENT_LIST_SECTION if step > 0 else BRAILLE_RESULT_SECTION
    )
else:
    target_section = get_adjacent_section(current_section, step)
```

- [ ] **Step 5: 執行導覽與快捷鍵測試**

Run:

```bash
cd client && python3 -m unittest \
  tests.test_section_navigation \
  tests.test_input_shortcuts -v
```

Expected: PASS.

- [ ] **Step 6: 在 Windows 手動驗證焦點循環**

Run: `cd client && python gui.py`

Expected:

- F6：Document List → View → Source Text → Braille Result → Document List。
- Shift+F6 以相反順序循環。
- 循環中沒有不可見或空白的焦點停點。
- Alt 仍可獨立進入原生選單列。

- [ ] **Step 7: 提交導覽更新**

```bash
git add client/ui/section_navigation.py client/tests/test_section_navigation.py client/gui.py
git commit -m "fix: update section navigation for translation menu"
```

### Task 7: 更新台灣繁體中文本地化

**Files:**
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`
- Reference: `scripts/generate_pot.bat`

- [ ] **Step 1: 重新產生 POT 並合併 zh_TW catalog**

在 Windows 執行：

```bat
scripts\generate_pot.bat
```

Expected: 新增 `Translation`、`Translation Settings...`、`Dictionary Management...` 等 msgid，且既有未使用字串被標記為 obsolete，而不是手動刪除歷史翻譯。

- [ ] **Step 2: 設定台灣慣用翻譯**

```po
msgid "Translation"
msgstr "轉譯"

msgid "Translation Settings..."
msgstr "轉譯設定..."

msgid "Translation Settings"
msgstr "轉譯設定"

msgid "Translation Tables Setting..."
msgstr "轉譯表設定..."

msgid "Dictionary Management..."
msgstr "字典管理..."

msgid "Dictionary Management"
msgstr "字典管理"

msgid "Braille Type"
msgstr "點字類型"

msgid "Width"
msgstr "寬度"

msgid "Dictionary"
msgstr "字典"

msgid "Convert"
msgstr "執行轉換"
```

保留既有 Add、Delete、Rename、Edit、Import、Export 翻譯；確認其顯示分別為「新增、刪除、重新命名、編輯、匯入、匯出」。

- [ ] **Step 3: 編譯 catalog**

Run:

```bash
msgfmt client/locales/zh_TW/LC_MESSAGES/dotexpress.po \
  -o client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
```

Expected: exit code 0 and `.mo` timestamp updated.

- [ ] **Step 4: 驗證 PO 格式**

Run: `msgfmt --check client/locales/zh_TW/LC_MESSAGES/dotexpress.po -o /tmp/dotexpress.mo`

Expected: exit code 0 with no duplicate msgid or format-string errors.

- [ ] **Step 5: 在 zh_TW 環境手動確認所有新字串**

Run: `cd client && TEXT2BRAILLE_LANG=zh_TW python gui.py`

Expected:

- 頂層顯示「轉譯」。
- 四個項目顯示「執行轉換、轉譯設定...、轉譯表設定...、字典管理...」。
- 兩個新對話框的標題、欄位、按鈕皆無未翻譯英文。

- [ ] **Step 6: 提交本地化**

```bash
git add \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "feat: localize translation menu dialogs"
```

### Task 8: 完整迴歸驗證與文件同步

**Files:**
- Modify only if behavior changed during implementation:
  `docs/superpowers/specs/2026-06-27-translation-menu-settings-design.md`
- Modify only if behavior changed during implementation:
  `docs/superpowers/specs/2026-06-27-translation-menu-settings-design_zh-TW.md`

- [ ] **Step 1: 搜尋已移除控制項的殘留參照**

Run:

```bash
rg -n \
  "table_btn|output_choice|width_spin|dictionary_choice|actions_btn|convert_btn|CONVERSION_SECTION|_create_conversion_controls|on_open_dictionary_actions" \
  client/gui.py client/ui client/tests
```

Expected: no matches；若 `output_choice` 或 `width_spin` 出現在 `client/dialog.py`，那是新設定對話框的合法參照。

- [ ] **Step 2: 執行全套 client unittest**

Run: `cd client && python3 -m unittest discover -s tests -v`

Expected: all runnable tests PASS；非 Windows 環境因 `liblouis` / `WINFUNCTYPE` 而 skip 的項目需在 handoff 中逐項註明，不可當成通過。

- [ ] **Step 3: 執行 pytest-style client tests**

Run: `cd client && python3 -m pytest tests -q`

Expected: all runnable tests PASS, with only known platform skips.

- [ ] **Step 4: 執行最後 Windows UI smoke test**

Run: `cd client && python gui.py`

Expected:

- 主視窗版面、四個 Translation commands、兩個新對話框皆符合 spec。
- OK/Cancel、字典立即操作、Edit 返回主視窗、Ctrl+Enter、F6/Shift+F6 皆符合前述驗收條件。
- 轉換中 Translation 選單、document list、source text 會停用；完成或失敗後恢復。

- [ ] **Step 5: 對照 spec 確認沒有行為漂移**

逐項核對：

- Translation 選單恰好四個項目且順序正確。
- Translation Settings 只管理點字類型、寬度、選取字典。
- Translation Tables Setting 繼續使用 `TranslationTableDialog`。
- Dictionary Management 是 list view 加六個立即動作。
- Edit 關閉管理對話框後才開啟 `SpeechSymbolsDialog`，關閉後停在主視窗。
- 不修改 CSV、轉譯表或轉換輸出格式。
- 不新增 MVP、MVVM 或 command class hierarchy。

若實作沒有改變已核准行為，不修改 spec；若發現必須改變，先停止 implementation 並回到 brainstorming 取得決策。

- [ ] **Step 6: 建立最終驗證提交**

只有在測試或 spec 同步產生檔案變更時才提交：

```bash
git add client/tests docs/superpowers/specs
git commit -m "test: verify translation menu workflows"
```
