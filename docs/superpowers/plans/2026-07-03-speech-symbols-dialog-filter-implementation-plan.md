# 語音符號對話框篩選功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `SpeechSymbolsDialog` 加入針對 `Source Text` 與 `Braille` 的即時、不分大小寫篩選，並以 virtual list 支援數百到上千筆字典條目。

**Architecture:** `self.entries` 保持完整且可儲存的資料來源，`self.filtered_entries` 只保存目前可見條目的物件參照。新增一個小型 virtual `wx.ListCtrl` 子類，透過 callback 向對話框取得欄位文字；所有新增、編輯、刪除和選取操作先從可見條目解析回完整資料，再重新套用篩選。

**Tech Stack:** Python 3、wxPython `wx.ListCtrl` virtual mode、`unittest`、gettext

---

## 檔案配置

- Create: `client/tests/test_speech_symbols_dialog.py` — 以輕量 fake controls 驗證 virtual list 文字、篩選、選取、按鈕狀態與 CRUD 流程。
- Modify: `client/dialog.py:396` — 新增 virtual list、篩選控制項、篩選資料模型與篩選狀態下的 CRUD 整合。
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po:998` — 加入 `Filter by:` 的台灣繁體中文翻譯。
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` — 編譯更新後的 gettext catalog。
- Reference: `docs/superpowers/specs/2026-07-03-speech-symbols-dialog-filter-design_zh-TW.md`
- Reference: `include/nvda/source/gui/settingsDialogs.py:6720` — NVDA `SpeechSymbolsDialog` 的 virtual list 與 `filter()` 互動模式。

### Task 1: 建立 virtual list 與篩選核心

**Files:**
- Create: `client/tests/test_speech_symbols_dialog.py`
- Modify: `client/dialog.py:396`
- Reference: `include/nvda/source/gui/settingsDialogs.py:6720`

- [ ] **Step 1: 建立對話框邏輯測試所需的受控 fake controls**

```python
# client/tests/test_speech_symbols_dialog.py
import sys
import types
import unittest


if "wx" not in sys.modules:
    wx_stub = types.ModuleType("wx")
    wx_stub.Dialog = type("Dialog", (), {})
    wx_stub.ListCtrl = type("ListCtrl", (), {})
    wx_stub.Window = type("Window", (), {})
    wx_stub.CommandEvent = type("CommandEvent", (), {})
    wx_stub.ListEvent = type("ListEvent", (), {})
    wx_stub.NOT_FOUND = -1
    sys.modules["wx"] = wx_stub

from dialog import (
    DictionaryEntry,
    DictionaryEntryListCtrl,
    SpeechSymbolsDialog,
)


class _FakeListCtrl:
    def __init__(self) -> None:
        self.item_count = 0
        self.selected = -1
        self.focused = -1
        self.refresh_count = 0

    def GetFirstSelected(self) -> int:
        return self.selected

    def SetItemCount(self, count: int) -> None:
        self.item_count = count
        if self.selected >= count:
            self.selected = -1

    def GetItemCount(self) -> int:
        return self.item_count

    def Select(self, index: int, on: bool = True) -> None:
        if on:
            self.selected = index
        elif self.selected == index:
            self.selected = -1

    def Focus(self, index: int) -> None:
        self.focused = index

    def Refresh(self) -> None:
        self.refresh_count += 1


class _FakeTextCtrl:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def GetValue(self) -> str:
        return self.value

    def ChangeValue(self, value: str) -> None:
        self.value = value


class _FakeButton:
    def __init__(self) -> None:
        self.enabled = True

    def Enable(self, enabled: bool = True) -> None:
        self.enabled = enabled


class _FakeEvent:
    def __init__(self) -> None:
        self.skipped = False

    def Skip(self) -> None:
        self.skipped = True


def _make_dialog(entries: list[DictionaryEntry]) -> SpeechSymbolsDialog:
    dialog = object.__new__(SpeechSymbolsDialog)
    dialog.entries = list(entries)
    dialog.filtered_entries = list(entries)
    dialog.filter_ctrl = _FakeTextCtrl()
    dialog.list_ctrl = _FakeListCtrl()
    dialog.list_ctrl.SetItemCount(len(entries))
    dialog.edit_button = _FakeButton()
    dialog.remove_button = _FakeButton()
    if entries:
        dialog.list_ctrl.Select(0)
    dialog._update_button_states()
    return dialog
```

- [ ] **Step 2: 寫入 virtual list 欄位與基本篩選的失敗測試**

```python
# Append to client/tests/test_speech_symbols_dialog.py
class DictionaryEntryListCtrlTest(unittest.TestCase):
    def test_get_item_text_delegates_to_callback(self) -> None:
        control = object.__new__(DictionaryEntryListCtrl)
        control._get_item_text = lambda item, column: f"{item}:{column}"

        self.assertEqual(control.OnGetItemText(4, 2), "4:2")


class SpeechSymbolsDialogFilterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.alpha = DictionaryEntry("Alpha", "⠁", "General")
        self.beta = DictionaryEntry("Beta", "Needle", "Bopomofo")
        self.dialog = _make_dialog([self.alpha, self.beta])

    def test_empty_filter_shows_all_entries(self) -> None:
        self.dialog.filter_entries("")

        self.assertEqual(self.dialog.filtered_entries, [self.alpha, self.beta])
        self.assertEqual(self.dialog.list_ctrl.item_count, 2)

    def test_filter_matches_source_text_case_insensitively(self) -> None:
        self.dialog.filter_entries("ALP")

        self.assertEqual(self.dialog.filtered_entries, [self.alpha])

    def test_filter_matches_braille_case_insensitively(self) -> None:
        self.dialog.filter_entries("NEED")

        self.assertEqual(self.dialog.filtered_entries, [self.beta])

    def test_filter_does_not_match_entry_type(self) -> None:
        self.dialog.filter_entries("bopomofo")

        self.assertEqual(self.dialog.filtered_entries, [])

    def test_item_text_uses_visible_entry_and_localized_type_label(self) -> None:
        self.dialog.filtered_entries = [self.beta]

        self.assertEqual(self.dialog._get_item_text(0, 0), "Beta")
        self.assertEqual(self.dialog._get_item_text(0, 1), "Needle")
        self.assertEqual(self.dialog._get_item_text(0, 2), "注音")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 執行測試，確認缺少 virtual list 與篩選 API**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog -v`

Expected: FAIL because `DictionaryEntryListCtrl`, `filter_entries`, and `_get_item_text` do not exist.

- [ ] **Step 4: 新增 virtual list 子類與篩選資料模型**

```python
# client/dialog.py, immediately before SpeechSymbolsDialog
class DictionaryEntryListCtrl(wx.ListCtrl):
	"""Virtual list that asks its owner for visible dictionary cell text."""

	def __init__(
		self,
		parent: wx.Window,
		get_item_text: Callable[[int, int], str],
		**kwargs,
	):
		super().__init__(parent, **kwargs)
		self._get_item_text = get_item_text

	def OnGetItemText(self, item: int, column: int) -> str:
		return self._get_item_text(item, column)
```

```python
# client/dialog.py, replace SpeechSymbolsDialog.__init__ initialization tail
self.dictionary_path = Path(dictionary_path) if dictionary_path else (Path("data") / "dictionary.csv")
self.entries: List[DictionaryEntry] = self._load_entries()
self.filtered_entries: List[DictionaryEntry] = list(self.entries)
self._build_ui()
self.filter_entries()
```

```python
# client/dialog.py, in SpeechSymbolsDialog._build_ui before the list label
filter_label = wx.StaticText(self, label=_("Filter by:"))
main_sizer.Add(filter_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
self.filter_ctrl = wx.TextCtrl(self)
self.filter_ctrl.Bind(wx.EVT_TEXT, self._on_filter_changed)
main_sizer.Add(self.filter_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
```

```python
# client/dialog.py, replace list_ctrl construction; retain existing columns and list event bindings
self.list_ctrl = DictionaryEntryListCtrl(
	self,
	self._get_item_text,
	style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL,
)
```

```python
# client/dialog.py, replace _populate_list with these methods
def _get_item_text(self, item: int, column: int) -> str:
	entry = self.filtered_entries[item]
	if column == 0:
		return entry.text
	if column == 1:
		return entry.braille
	if column == 2:
		return ENTRY_TYPE_LABELS.get(entry.entry_type, entry.entry_type)
	raise ValueError(f"Unknown column: {column}")

def _entry_matches_filter(self, entry: DictionaryEntry, filter_text: str) -> bool:
	normalized_filter = filter_text.casefold()
	return normalized_filter in entry.text.casefold() or normalized_filter in entry.braille.casefold()

def filter_entries(
	self,
	filter_text: str | None = None,
	preferred_entry: DictionaryEntry | None = None,
	fallback_index: int = 0,
) -> None:
	previous_entry = preferred_entry or self._get_selected_entry()
	if filter_text is None:
		filter_text = self.filter_ctrl.GetValue()

	if filter_text:
		self.filtered_entries = [
			entry for entry in self.entries if self._entry_matches_filter(entry, filter_text)
		]
	else:
		self.filtered_entries = list(self.entries)

	self.list_ctrl.SetItemCount(len(self.filtered_entries))
	self.list_ctrl.Refresh()
	if not self.filtered_entries:
		self._clear_selection()
		self._update_button_states()
		return

	new_index = min(fallback_index, len(self.filtered_entries) - 1)
	if previous_entry is not None:
		try:
			new_index = self.filtered_entries.index(previous_entry)
		except ValueError:
			pass
	self._select_index(new_index)

def _on_filter_changed(self, event: wx.CommandEvent) -> None:
	self.filter_entries(self.filter_ctrl.GetValue())
	event.Skip()
```

- [ ] **Step 5: 改成以可見資料筆數與可見條目處理選取**

```python
# client/dialog.py, replace the existing selection helper block
def _update_button_states(self) -> None:
	has_selection = self._get_selected_index() is not None
	self.edit_button.Enable(has_selection)
	self.remove_button.Enable(has_selection)

def _get_selected_index(self) -> int | None:
	index = self.list_ctrl.GetFirstSelected()
	if index == wx.NOT_FOUND or index < 0 or index >= len(self.filtered_entries):
		return None
	return index

def _get_selected_entry(self) -> DictionaryEntry | None:
	index = self._get_selected_index()
	return self.filtered_entries[index] if index is not None else None

def _clear_selection(self) -> None:
	index = self.list_ctrl.GetFirstSelected()
	if index != wx.NOT_FOUND:
		self.list_ctrl.Select(index, False)

def _select_index(self, index: int) -> None:
	if index < 0 or index >= len(self.filtered_entries):
		self._clear_selection()
		self._update_button_states()
		return
	self._clear_selection()
	self.list_ctrl.Select(index)
	self.list_ctrl.Focus(index)
	self._update_button_states()
```

- [ ] **Step 6: 執行基本篩選測試**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog -v`

Expected: PASS.

- [ ] **Step 7: 提交 virtual list 與篩選核心**

```bash
git add client/dialog.py client/tests/test_speech_symbols_dialog.py
git commit -m "feat: add virtual dictionary entry filtering"
```

### Task 2: 完成選取狀態與篩選事件行為

**Files:**
- Modify: `client/tests/test_speech_symbols_dialog.py`
- Modify: `client/dialog.py:396`

- [ ] **Step 1: 寫入選取保留、回落、空結果與事件傳遞測試**

```python
# Append to SpeechSymbolsDialogFilterTest in client/tests/test_speech_symbols_dialog.py
def test_filter_preserves_selected_entry_when_it_remains_visible(self) -> None:
    self.dialog.list_ctrl.Select(1)

    self.dialog.filter_entries("e")

    self.assertIs(self.dialog.filtered_entries[self.dialog.list_ctrl.selected], self.beta)
    self.assertTrue(self.dialog.edit_button.enabled)
    self.assertTrue(self.dialog.remove_button.enabled)

def test_filter_falls_back_to_first_entry_when_selection_is_hidden(self) -> None:
    self.dialog.list_ctrl.Select(1)

    self.dialog.filter_entries("alp")

    self.assertEqual(self.dialog.list_ctrl.selected, 0)
    self.assertIs(self.dialog.filtered_entries[0], self.alpha)

def test_empty_result_clears_selection_and_disables_edit_and_delete(self) -> None:
    self.dialog.filter_entries("missing")

    self.assertEqual(self.dialog.list_ctrl.selected, -1)
    self.assertFalse(self.dialog.edit_button.enabled)
    self.assertFalse(self.dialog.remove_button.enabled)

def test_filter_event_applies_current_text_and_is_skipped(self) -> None:
    self.dialog.filter_ctrl.ChangeValue("alp")
    event = _FakeEvent()

    self.dialog._on_filter_changed(event)

    self.assertEqual(self.dialog.filtered_entries, [self.alpha])
    self.assertTrue(event.skipped)
```

- [ ] **Step 2: 執行新增測試，確認選取或事件邏輯的差異會被捕捉**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog.SpeechSymbolsDialogFilterTest -v`

Expected: PASS if Task 1 implementation exactly follows the plan; otherwise FAIL at the mismatched selection or event behavior.

- [ ] **Step 3: 修正 Task 1 實作，使所有選取與空結果測試通過**

確認 `filter_entries()` 的順序必須是：

```python
previous_entry = preferred_entry or self._get_selected_entry()
# Rebuild self.filtered_entries.
self.list_ctrl.SetItemCount(len(self.filtered_entries))
self.list_ctrl.Refresh()
# Empty list clears selection and updates buttons.
# Non-empty list restores previous_entry or selects fallback_index.
```

不要在空結果時顯示 `wx.MessageBox`，也不要以 `self.entries` 的索引直接選取 virtual list。

- [ ] **Step 4: 執行篩選測試與既有對話框驗證測試**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog tests.test_dialog_validation -v`

Expected: PASS.

- [ ] **Step 5: 提交選取與事件行為**

```bash
git add client/dialog.py client/tests/test_speech_symbols_dialog.py
git commit -m "fix: preserve filtered dictionary selection"
```

### Task 3: 整合篩選狀態下的新增、編輯與刪除

**Files:**
- Modify: `client/tests/test_speech_symbols_dialog.py`
- Modify: `client/dialog.py:506`

- [ ] **Step 1: 寫入新增符合與不符合篩選條件的失敗測試**

```python
# Append to client/tests/test_speech_symbols_dialog.py
class SpeechSymbolsDialogMutationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.alpha = DictionaryEntry("Alpha", "⠁", "General")
        self.beta = DictionaryEntry("Beta", "⠃", "General")
        self.dialog = _make_dialog([self.alpha, self.beta])

    def test_add_matching_entry_keeps_filter_and_selects_new_entry(self) -> None:
        self.dialog.filter_ctrl.ChangeValue("alp")
        self.dialog.filter_entries("alp")
        added = DictionaryEntry("Alphabet", "⠁⠃", "General")
        self.dialog._open_entry_dialog = lambda _entry=None: added

        self.dialog._on_add_clicked(None)

        self.assertEqual(self.dialog.filter_ctrl.GetValue(), "alp")
        self.assertEqual(self.dialog.filtered_entries, [self.alpha, added])
        self.assertIs(
            self.dialog.filtered_entries[self.dialog.list_ctrl.selected],
            added,
        )

    def test_add_nonmatching_entry_clears_filter_and_selects_new_entry(self) -> None:
        self.dialog.filter_ctrl.ChangeValue("alp")
        self.dialog.filter_entries("alp")
        added = DictionaryEntry("Gamma", "⠛", "General")
        self.dialog._open_entry_dialog = lambda _entry=None: added

        self.dialog._on_add_clicked(None)

        self.assertEqual(self.dialog.filter_ctrl.GetValue(), "")
        self.assertEqual(self.dialog.filtered_entries, [self.alpha, self.beta, added])
        self.assertIs(
            self.dialog.filtered_entries[self.dialog.list_ctrl.selected],
            added,
        )
```

- [ ] **Step 2: 執行新增測試，確認舊 `_populate_list()` 流程失敗**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog.SpeechSymbolsDialogMutationTest -v`

Expected: FAIL because `_on_add_clicked()` still calls `_populate_list()` and selects by the full-list index.

- [ ] **Step 3: 改寫新增流程，依新條目是否符合篩選決定是否清空條件**

```python
# client/dialog.py, replace the successful append tail of _on_add_clicked
self.entries.append(new_entry)
filter_text = self.filter_ctrl.GetValue()
if filter_text and not self._entry_matches_filter(new_entry, filter_text):
	self.filter_ctrl.ChangeValue("")
	filter_text = ""
self.filter_entries(filter_text, preferred_entry=new_entry)
```

- [ ] **Step 4: 執行新增流程測試**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog.SpeechSymbolsDialogMutationTest -v`

Expected: PASS.

- [ ] **Step 5: 寫入篩選狀態下編輯與刪除的失敗測試**

```python
# Append to SpeechSymbolsDialogMutationTest in client/tests/test_speech_symbols_dialog.py
def test_edit_visible_entry_updates_full_list_and_preserves_selection(self) -> None:
    self.dialog.filter_ctrl.ChangeValue("bet")
    self.dialog.filter_entries("bet")
    updated = DictionaryEntry("Better", "⠃⠑", "General")
    self.dialog._open_entry_dialog = lambda _entry=None: updated

    self.dialog._edit_selected()

    self.assertEqual(self.dialog.entries, [self.alpha, updated])
    self.assertEqual(self.dialog.filtered_entries, [updated])
    self.assertIs(self.dialog.filtered_entries[self.dialog.list_ctrl.selected], updated)

def test_edit_entry_that_stops_matching_removes_it_from_visible_list(self) -> None:
    self.dialog.filter_ctrl.ChangeValue("bet")
    self.dialog.filter_entries("bet")
    updated = DictionaryEntry("Gamma", "⠛", "General")
    self.dialog._open_entry_dialog = lambda _entry=None: updated

    self.dialog._edit_selected()

    self.assertEqual(self.dialog.entries, [self.alpha, updated])
    self.assertEqual(self.dialog.filtered_entries, [])
    self.assertEqual(self.dialog.list_ctrl.selected, -1)
    self.assertFalse(self.dialog.edit_button.enabled)
    self.assertFalse(self.dialog.remove_button.enabled)

def test_delete_filtered_entry_selects_nearest_remaining_entry(self) -> None:
    alpine = DictionaryEntry("Alpine", "⠁⠇", "General")
    self.dialog.entries.append(alpine)
    self.dialog.filter_ctrl.ChangeValue("a")
    self.dialog.filter_entries("a")
    self.dialog.list_ctrl.Select(1)

    self.dialog._on_remove_clicked(None)

    self.assertEqual(self.dialog.entries, [self.alpha, alpine])
    self.assertEqual(self.dialog.filtered_entries, [self.alpha, alpine])
    self.assertEqual(self.dialog.list_ctrl.selected, 1)
    self.assertIs(self.dialog.filtered_entries[1], alpine)
```

- [ ] **Step 6: 執行編輯與刪除測試，確認完整清單索引假設失敗**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog.SpeechSymbolsDialogMutationTest -v`

Expected: FAIL because editing and deletion still use a visible index directly against `self.entries`.

- [ ] **Step 7: 以可見條目物件改寫編輯、重複檢查與刪除流程**

```python
# client/dialog.py, replace _edit_selected
def _edit_selected(self) -> None:
	visible_index = self._get_selected_index()
	current_entry = self._get_selected_entry()
	if visible_index is None or current_entry is None:
		return
	updated_entry = self._open_entry_dialog(current_entry)
	if updated_entry is None:
		return
	if self._identifier_exists(updated_entry.text, exclude_entry=current_entry):
		wx.MessageBox(
			_('Source text "{identifier}" already exists.').format(identifier=updated_entry.text),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
			parent=self,
		)
		return
	full_index = next(
		index for index, entry in enumerate(self.entries) if entry is current_entry
	)
	self.entries[full_index] = updated_entry
	self.filter_entries(
		self.filter_ctrl.GetValue(),
		preferred_entry=updated_entry,
		fallback_index=visible_index,
	)
```

```python
# client/dialog.py, replace _on_remove_clicked
def _on_remove_clicked(self, _event: wx.CommandEvent) -> None:
	visible_index = self._get_selected_index()
	current_entry = self._get_selected_entry()
	if visible_index is None or current_entry is None:
		return
	self.entries.remove(current_entry)
	self.filter_entries(
		self.filter_ctrl.GetValue(),
		fallback_index=visible_index,
	)
```

```python
# client/dialog.py, replace _identifier_exists
def _identifier_exists(
	self,
	identifier: str,
	exclude_entry: DictionaryEntry | None = None,
) -> bool:
	return any(
		entry.text == identifier and entry is not exclude_entry
		for entry in self.entries
	)
```

- [ ] **Step 8: 執行完整對話框測試**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog tests.test_dialog_validation -v`

Expected: PASS.

- [ ] **Step 9: 提交篩選狀態下的 CRUD 整合**

```bash
git add client/dialog.py client/tests/test_speech_symbols_dialog.py
git commit -m "feat: support filtered dictionary editing"
```

### Task 4: 驗證儲存完整資料與既有驗證回歸

**Files:**
- Modify: `client/tests/test_speech_symbols_dialog.py`
- Verify: `client/dialog.py`

- [ ] **Step 1: 寫入儲存不受目前篩選結果影響的測試**

```python
# Add imports at the top of client/tests/test_speech_symbols_dialog.py
import csv
import tempfile
from pathlib import Path
```

```python
# Append to SpeechSymbolsDialogMutationTest
def test_save_writes_all_entries_not_only_filtered_entries(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "dictionary.csv"
        self.dialog.dictionary_path = path
        self.dialog.filter_entries("alp")

        self.dialog._save_entries()

        with path.open("r", newline="", encoding="utf-8") as fp:
            rows = list(csv.DictReader(fp))
    self.assertEqual(
        rows,
        [
            {"text": "Alpha", "braille": "⠁", "type": "General"},
            {"text": "Beta", "braille": "⠃", "type": "General"},
        ],
    )
```

- [ ] **Step 2: 寫入重複來源文字在篩選狀態下仍會被拒絕的測試**

```python
# Add import at the top of client/tests/test_speech_symbols_dialog.py
from unittest.mock import patch
```

```python
# Append to SpeechSymbolsDialogMutationTest
@patch("dialog.wx.MessageBox")
def test_edit_rejects_duplicate_source_text_outside_filter(
    self,
    message_box,
) -> None:
    self.dialog.filter_ctrl.ChangeValue("bet")
    self.dialog.filter_entries("bet")
    self.dialog._open_entry_dialog = lambda _entry=None: DictionaryEntry(
        "Alpha",
        "⠃",
        "General",
    )

    self.dialog._edit_selected()

    self.assertEqual(self.dialog.entries, [self.alpha, self.beta])
    message_box.assert_called_once()
```

- [ ] **Step 3: 執行儲存與重複檢查測試**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog -v`

Expected: PASS. `_save_entries()` 已正確走訪 `self.entries`，因此儲存測試不需修改產品程式碼；若失敗，不可改成儲存 `self.filtered_entries`。

- [ ] **Step 4: 執行字典與對話框相關回歸測試**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog tests.test_dialog_validation tests.test_dictionary_actions tests.test_dictionary_manager tests.test_dictionary_import_flow -v`

Expected: PASS.

- [ ] **Step 5: 提交儲存與回歸測試**

```bash
git add client/tests/test_speech_symbols_dialog.py
git commit -m "test: cover filtered dictionary persistence"
```

### Task 5: 加入台灣繁中翻譯並完成驗證

**Files:**
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po:998`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`
- Verify: `client/dialog.py`
- Verify: `client/tests/test_speech_symbols_dialog.py`

- [ ] **Step 1: 在 gettext catalog 加入篩選欄位翻譯**

```po
# client/locales/zh_TW/LC_MESSAGES/dotexpress.po
#: dialog.py
msgid "Filter by:"
msgstr "篩選條件："
```

- [ ] **Step 2: 驗證 PO 語法**

Run: `msgfmt --check --check-format -o /tmp/dotexpress.mo client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

Expected: exit code 0 with no errors.

- [ ] **Step 3: 重新編譯應用程式使用的 MO 檔**

Run: `msgfmt -o client/locales/zh_TW/LC_MESSAGES/dotexpress.mo client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

Expected: exit code 0 and an updated `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`.

- [ ] **Step 4: 執行聚焦與完整 client 測試**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog tests.test_dialog_validation tests.test_dictionary_actions tests.test_dictionary_manager tests.test_dictionary_import_flow -v`

Expected: PASS.

Run: `cd client && python3 -m unittest discover -s tests -v`

Expected: PASS, except any pre-existing platform-specific skips documented by the suite.

- [ ] **Step 5: 在可使用 wxPython 的桌面環境進行人工檢查**

Run: `cd client && python3 gui.py`

Expected:

- 開啟字典編輯對話框後，清單上方顯示「篩選條件：」輸入框。
- 輸入來源文字或點字片段時清單即時更新；輸入 `Type` 名稱不會構成符合結果。
- 零筆結果時 `Edit` 與 `Delete` 停用，且沒有額外提示。
- 新增符合條件的項目會保留篩選並選取新項目。
- 新增不符合條件的項目會清空篩選並選取新項目。
- 篩選狀態下編輯、刪除及按 OK 儲存後，未顯示的條目仍存在。

- [ ] **Step 6: 提交翻譯與編譯 catalog**

```bash
git add client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "feat: translate dictionary filter control"
```

- [ ] **Step 7: 檢查最終變更範圍**

Run: `git status --short`

Expected: 本計畫涉及的檔案沒有未提交變更；使用者原有的其他 worktree 變更保持不動。

Run: `git log --oneline -5`

Expected: 最上方包含本計畫建立的四個 scoped commits。
