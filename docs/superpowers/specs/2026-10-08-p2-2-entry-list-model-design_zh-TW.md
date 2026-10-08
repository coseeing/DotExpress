# 字典項目清單模型（P2-2）設計

## 目標

把字典項目編輯器的資料邏輯從 wx 對話框移到不依賴 wx 的模型，讓它不必替元件做 stub 就能測試。這是 `storage/refactor.md`（6.3 節）的路線圖任務 P2-2，涵蓋發現 S-4（`SpeechSymbolsDialog` 把 model 與 view 揉在一起；相對 CWD 的預設路徑）。

具體而言：

- 新增不依賴 wx 的模組 `client/dictionaries/entry_list_model.py`，內含 `DictionaryEntryListModel`：完整項目清單、篩選文字、可見（篩選後）清單、重複判斷、新增／取代／刪除、每次變更後應顯示的選取、虛擬清單的儲存格文字，以及透過 `dictionaries/entries.py` 的載入／儲存。
- 編輯器對話框成為 Supervising Controller：它擁有元件、從元件讀取篩選文字與選取列、呼叫模型，並呈現模型回傳的結果（`SetItemCount`、`Refresh`、`Select`、`Focus`、按鈕狀態、訊息框）。
- 對話框在獨立、純機械式的最後一步更名 `SpeechSymbolsDialog` -> `DictionaryEntriesDialog`（決策 D7）。
- `dictionary_path` 改為必填建構參數（移除 `Path("data") / "dictionary.csv"` 預設值；決策 D6）。

這是保持行為不變的重構。每個字串、訊息、訊息順序、清單控制項呼叫順序、選取、焦點、按鈕狀態與儲存的 CSV 位元組都不變。msgid 不變（353）。P1-5 的黃金測試資料 `client/tests/fixtures/translation_golden.json`（sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`）不變。

規劃後修正：plan `docs/superpowers/plans/2026-10-08-p2-2-entry-list-model.md`（「Spec Corrections and Refinements」一節）修正了一項事實（`load_dictionary_entries` 仍留在 `dialog.py` 的匯入中）、釐清 Q3，並細化了測試計畫；這些變更已併入下文。

## 現況（2026-10-08 於 `refactor/p2-2-entry-list-model` 驗證，HEAD `33dc34d`，已合併 P0-*、P1-* 與 P2-1）

縮排：`dialog.py`、`gui.py` 與 `dictionaries/*.py` 用 tab；`tests/test_speech_symbols_dialog.py`、`tests/test_dialog_validation.py`、`tests/test_gui_document_flows.py` 與 `tests/wx_stub.py` 用 4 個空白；`tests/test_dictionary_entries.py` 用 tab。

基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 889 tests`、`FAILED (failures=1, skipped=9)`；失敗的是 P2-5 的 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。shuffle harness（`$SP/shuffle_harness.py`，種子 0-19）每個種子都得到 `ran=889 failures=1 errors=0 skipped=9`。msgid 掃描（`$SP/msgid_scan.py client`）：353。`tests.test_speech_symbols_dialog` 有 21 個測試。（`$PY` = `$SP/venv/bin/python`，`$SP` = 本工作階段的 scratchpad。）

### 類別（`client/dialog.py`）

| 項目 | 行 | 說明 |
| --- | --- | --- |
| `AddSymbolDialog` | 62-156 | 強制回應的「新增／編輯字典項目」對話框；在自己的 `_on_ok` 以 `validate_dictionary_entry` 驗證；會去除文字與點字前後空白。本任務不更動。 |
| `CallbackVirtualListCtrl` | 313-326 | `OnGetItemText(item, column)` 呼叫回呼函式的 `wx.ListCtrl`。不更動。 |
| `DictionaryEntryListCtrl` | 329 | `CallbackVirtualListCtrl` 的別名；任何地方都沒有使用（不處理，見「不在範圍內」）。 |
| `SpeechSymbolsDialog` | 332-570 | 編輯器（標題 "Custom Dictionary Manager" / 自訂字典管理器）。 |

### 建構（`__init__` 335-343）

1. `super().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)`：讀取任何東西之前原生對話框就已存在。
2. `self.dictionary_path = Path(dictionary_path) if dictionary_path else Path("data") / "dictionary.csv"`：預設值相對於 CWD；唯一的實際呼叫端一定會傳路徑。
3. `self.entries = load_dictionary_entries(self.dictionary_path)`（經由 `_load_entries`）；`self.filtered_entries = list(self.entries)`。解碼／CSV／OS 錯誤會從建構子拋出（步驟 1 的原生對話框不會被銷毀；見怪異行為 Q8）。
4. `_build_ui()`，接著 `filter_entries()`（篩選框為空、尚無選取：顯示全部列，若有列則選取並聚焦第 0 列），再呼叫一次 `_update_button_states()`。

### 版面（`_build_ui` 345-391），依建立（= Tab）順序

靜態文字 "Filter by:"（篩選條件：）；篩選 `wx.TextCtrl`，繫結 `EVT_TEXT` -> `_on_filter_changed`；靜態文字 "Dictionary entries"（字典項目）；`CallbackVirtualListCtrl(self, self._get_item_text, style=LC_REPORT | BORDER_SUNKEN | LC_SINGLE_SEL | LC_VIRTUAL)`，欄位 `(0, "Source Text", 200)`、`(1, "Braille", 230)`、`(2, "Type", 120)`（來源文字／點字／類型），繫結 `EVT_LIST_ITEM_SELECTED` 與 `EVT_LIST_ITEM_DESELECTED` -> `_on_selection_changed`，以及 `EVT_LIST_ITEM_ACTIVATED` -> `_on_item_activated`；按鈕 "Add"、"Edit"、"Delete"（新增／編輯／刪除）繫結 `_on_add_clicked`、`_on_edit_clicked`、`_on_remove_clicked`；`CreateButtonSizer(wx.OK | wx.CANCEL)`，以 `localize_standard_buttons` 在地化，只有確定按鈕（`FindWindowById(wx.ID_OK)`）有處理函式 `_on_ok`；`finalize_dialog_layout`。靜態文字為其後的控制項提供螢幕報讀器讀出的名稱，所以建立順序很重要。

### 儲存格文字（`_get_item_text` 396-404）

`filtered_entries` 的第 `item` 列：欄 0 `text`、欄 1 `braille`、欄 2 `ENTRY_TYPE_LABELS.get(entry_type, entry_type)`（標籤在匯入 `dictionaries.entries` 時翻譯）；其他欄拋出 `ValueError(f"Unknown column: {column}")`；列使用一般的 list 索引。

### 篩選與選取（`_entry_matches_filter` 406-408、`filter_entries` 410-440、442-478）

- 比對：`filter.casefold()` 是 `text.casefold()` 或 `braille.casefold()` 的子字串；從不比對類型。用 casefold 而非 lower：`STRASSE` 會符合 `Straße`。
- `filter_entries(filter_text=None, preferred_entry=None, fallback_index=0)`：
  1. `previous_entry = preferred_entry or self._get_selected_entry()`：選取的項目是在任何變更之前，從清單控制項對照**舊的**可見清單讀出。（`DictionaryEntry` 是一般 dataclass，永遠為真值。）
  2. `filter_text` 預設為篩選框的值；非空的篩選依完整清單順序保留符合的項目，空的篩選顯示全部。空白篩選是字面比對（`" "` 只保留含空白的項目）。
  3. `SetItemCount(len(visible))`、`Refresh()`。
  4. 結果為空：若有選取列則取消第一個選取列（`Select(index, False)`），更新按鈕，結束。
  5. 否則 `index = min(fallback_index, len - 1)`；若 `previous_entry` 不是 `None` 且與某個可見項目**相等**（`list.index`，dataclass 相等），以第一個相等的可見項目為準。接著 `_select_index(index)`：若有選取列先取消、`Select(index)`、`Focus(index)`、更新按鈕。
- `_on_filter_changed`：`filter_entries(self.filter_ctrl.GetValue())`，然後 `event.Skip()`。
- `_get_selected_index`：`GetFirstSelected()`；`NOT_FOUND`、負數或 `>= len(visible)` 時為 `None`。
- 按鈕：恰在有列被選取時啟用「編輯」與「刪除」（`_update_button_states`），每次清單變更後以及每個 `SELECTED`/`DESELECTED` 事件（之後 Skip）時更新。

### 新增／編輯／刪除（483-559）

- **新增**（`_on_add_clicked`）：開啟 `AddSymbolDialog(self, None)`（`_open_entry_dialog`）；不是 `ID_OK` 就什麼都不做。若**完整**清單（含被篩掉的項目）中有任何項目的 `text` 完全相同（區分大小寫，不看點字與類型）：`wx.MessageBox('Source text "{identifier}" already exists.', "Error", wx.OK | wx.ICON_ERROR, parent=self)`（來源文字「…」已存在。／錯誤）並結束；使用者輸入的項目遺失，不會重新開啟對話框。否則附加到完整清單尾端；若篩選框非空且新項目不符合，`filter_ctrl.ChangeValue("")`（不觸發 `EVT_TEXT`）；接著 `filter_entries(filter_text, preferred_entry=new_entry)`：新項目被選取並聚焦。
- **編輯**（`_on_edit_clicked` 與 `_on_item_activated`，都走 `_edit_selected`）：無選取則什麼都不做（不開啟項目對話框）。開啟 `AddSymbolDialog(self, current_entry)`；不是 `ID_OK` 就什麼都不做。對每個**其他**項目做重複檢查，以**同一物件**（`entry is not current_entry`）排除自己：同樣的訊息框，什麼都不變。否則在完整清單中以**同一物件**找到該項目並取代（位置不變），然後 `filter_entries(篩選框的值, preferred_entry=updated, fallback_index=visible_index)`。篩選**不會**清除：編輯後不再符合的項目會消失，改選取相同可見索引（夾在範圍內）的列，清單為空則不選取。
- **刪除**（`_on_remove_clicked`）：無選取則什麼都不做。不確認。`self.entries.remove(current_entry)`：移除完整清單中第一個**相等**的項目（檔案有完全相同的列時，不一定是被選取的那個物件）。然後 `filter_entries(篩選框的值, fallback_index=visible_index)`；`previous_entry` 是被移除的項目（控制項中仍被選取），所以若仍有相等的重複項目可見就選它，否則選相同可見索引（夾在範圍內）。
- `_normalize_type`（558-559）沒有呼叫者。

### 確定／取消（561-570）

- 確定：`save_dictionary_entries(self.dictionary_path, self.entries)`：完整清單、依清單順序，即使沒有任何變更也寫入。`IOError`（= `OSError`）：`wx.MessageBox("Failed to save: {error}", "Error", wx.OK | wx.ICON_ERROR, parent=self)`（儲存失敗：…／錯誤），不 `Skip`，對話框保留編輯內容繼續開著。其他例外從處理函式拋出（不 `Skip`）。成功：`event.Skip()`，wx 以 `ID_OK` 關閉對話框。
- 取消、Esc 與關閉鈕使用 wx 預設處理（`ID_CANCEL`）：不寫入任何東西，編輯被捨棄，不確認。
- 鍵盤：沒有自己的加速鍵或按鍵處理。在列上按 Enter（或雙擊）會觸發 activate -> 編輯。Tab 順序即建立順序。

### 項目讀寫（`client/dictionaries/entries.py`，不更動）

`DictionaryEntry(text, braille, entry_type="General")` 是可變的 `@dataclass`（以值比較相等，不可雜湊）。`load_dictionary_entries(path)`：檔案不存在 -> `[]`；以 `encoding="utf-8"` 的 `csv.DictReader` 讀取；去除 `text` 與 `braille` 前後空白，未知類型正規化為 `General`，略過文字為空的列以及點字不是有效注音序列的 `Bopomofo` 列；重複的列會保留。`save_dictionary_entries(path, entries)`：建立上層目錄，以 `"w"` 開檔（先截斷），寫入 `text,braille,type` 標頭與各列。

### 呼叫端

- `gui.py:82` 匯入 `SpeechSymbolsDialog`；`gui.on_open_dictionary_management`（935-945）以 P0-6 presenter 開啟 `DictionaryManagementDialog`；收到 `ID_EDIT` 時建立 `self._dictionary_presenter.dictionary_path(edit_name)`，並執行 `with SpeechSymbolsDialog(self, dictionary_path=...) as editor: editor.ShowModal()`，忽略結果。沒有其他地方建構編輯器。
- 測試：`tests/test_speech_symbols_dialog.py`（21 個測試；以 `object.__new__` 建立對話框，並直接操作 `entries`、`filtered_entries`、`filter_entries`、`_get_item_text`、`_open_entry_dialog`、`_edit_selected`、`_save_entries`）；`tests/test_dialog_validation.py`（為 context manager 測試匯入它）；`tests/test_gui_document_flows.py`（patch `gui.SpeechSymbolsDialog`、斷言關鍵字呼叫，以及第 1054 行的「保留名稱」guard）；`tests/wx_stub.py`（`_GUI_DIALOG_NAMES` 為 gui scope 的假 `dialog` 模組逐一建立 stub 類別；speech stub 設定檔 `speech_dialog_stubs`/`load_speech_dialog`/`SPEECH_DIALOG_MODULE_NAME` 與 `tests/test_dictionary_management_dialog.py`、`tests/test_wx_stub.py` 共用）。
- `test_speech_symbols_dialog` 的 stub scope 會驅逐在 scope 內首次匯入的 `dictionaries` 底下模組（`evict_speech_roots`）。

## 設計

### 決策摘要

- **D1 用模型，不用 presenter。** 由對話框擁有的可變模型；對話框仍是 controller，保留所有 `_()` 字串與 `wx.MessageBox` 呼叫。沒有 `View` protocol，也沒有觀察者回呼：對話框是唯一的變更者，所以每個模型呼叫都回傳 view 該呈現的內容（`EntryListUpdate`）。這就是 S-4 建議的 MVP Supervising Controller。不採用 P0-6 式的 presenter：每個動作的流程只有 3-6 行，而搬移訊息會移動它們在 `.pot` 中的位置，並讓介面加倍。
- **D2 選取由 view 擁有。** 清單控制項仍是選取列的唯一真相來源（方向鍵會在沒有任何模型呼叫下改變選取，而且 wx 不保證虛擬清單會送出 `DESELECTED` 事件）。對話框在每個動作發生時讀取 `GetFirstSelected()`，把可見索引傳給模型，與現在完全相同。
- **D3 篩選文字由模型擁有。** 只由 `apply_filter`（從 `EVT_TEXT` 與建構時呼叫）以及 `add`（會清除它）設定。不變式：每個處理函式結束後 `model.filter_text == filter_ctrl.GetValue()`。現在對話框在每個處理函式重新讀取篩選框；只要每次使用者編輯都有 `EVT_TEXT` 送到 `_on_filter_changed`，兩者就相等，而唯一的程式化變更（新增時的 `ChangeValue("")`）由模型同步反映（見「風險」）。
- **D4 比較規則不變，並明文寫下。** 以相等還原選取（第一個相等的可見項目）；以同一物件取代；移除第一個相等的項目；重複檢查比對完全相同的 `text`，並以同一物件排除自己。改變其中任何一條都會改變含相同列的檔案的行為，所以模型保留它們並寫在 docstring。
- **D5 訊息留在 `dialog.py`。** 模型沒有 `_()`，也不匯入 `i18n`（它使用 `dictionaries.entries` 的 `ENTRY_TYPE_LABELS`）。重複時拋出 `DuplicateEntryError(identifier)`；由對話框格式化既有的 msgid。沒有 msgid 或 `.pot` 位置移到新檔案。
- **D6 `dictionary_path` 改為必填。** `__init__(self, parent, dictionary_path)`，存成 `Path(dictionary_path)`。參數名稱與位置不變，所以 `gui.py` 的關鍵字呼叫不變。使用者看不到：唯一的呼叫端一定傳路徑。移除 S-4 指出的相對 CWD 寫入目標。
- **D7 更名** `SpeechSymbolsDialog` -> `DictionaryEntriesDialog`。"Speech symbols" 是沿襲自 NVDA 的名稱，與 DotExpress 無關；標題是 "Custom Dictionary Manager"，模型叫 `DictionaryEntryListModel`，而且類別名稱使用者看不到。成本：約 40 行機械式修改（`dialog.py`、`gui.py` 2 處、`tests/test_dialog_validation.py` 2 處、`tests/test_gui_document_flows.py` 2 處、`tests/wx_stub.py` 2 處、對話框測試模組），作為獨立的最後一個提交，必要時可整個捨棄而不影響重構。測試模組以 `git mv` 更名為 `tests/test_dictionary_entries_dialog.py`，其中的 `SpeechSymbolsDialog*Test` 類別改為 `DictionaryEntriesDialog*Test`。不保留舊名稱的別名（沒有外部使用者）。不更名：`AddSymbolDialog`（不在路線圖這一列；後續處理），以及 wx_stub 設定檔名稱 `speech_dialog_stubs`、`load_speech_dialog`、`SPEECH_DIALOG_MODULE_NAME`、`SPEECH_RESTORE_ROOTS`、`evict_speech_roots`（與另外兩個測試模組共用的測試基礎設施名稱；只更新提到測試模組名稱的那行註解）。歷史文件（`docs/refactor/*.md`、較早的 spec）保留舊名稱。`.pot`/`.po` 影響：無。xgettext 只記錄 `檔案:行號` 參照，從不記錄類別名稱；msgid 不變（353）；`client/locales` 中的 `#: dialog.py:NNN` 註解本來就是過時的行號，會在下次執行 `scripts\generate-pot.bat` 時更新，所以本任務 `client/locales` 沒有差異。

### `client/dictionaries/entry_list_model.py`（tab，無 wx，無 i18n）

```python
class DuplicateEntryError(ValueError):
	"""Another entry already has this source text; nothing was changed."""
	def __init__(self, identifier: str) -> None:
		super().__init__(identifier)
		self.identifier = identifier


@dataclass(frozen=True)
class EntryListUpdate:
	selection: int | None          # 要選取並聚焦的可見列；None：清除選取
	filter_cleared: bool = False   # 僅 add：新項目不符合，篩選被重設為 ""


class DictionaryEntryListModel:
	def __init__(self, entries: Iterable[DictionaryEntry] = ()) -> None  # 篩選 ""，全部可見
	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel               # load_dictionary_entries(path)；錯誤直接拋出
	def save(self, path: Path) -> None                                   # save_dictionary_entries(path, 完整清單)；錯誤直接拋出

	entries: tuple[DictionaryEntry, ...]          # property，依檔案順序的完整清單（快照）
	visible_entries: tuple[DictionaryEntry, ...]  # property
	filter_text: str                              # property
	visible_count: int                            # property

	def visible_entry(self, index: int | None) -> DictionaryEntry | None   # index 為 None、< 0 或 >= visible_count 時為 None
	def cell_text(self, row: int, column: int) -> str                     # 與現在的 _get_item_text 完全相同
	@staticmethod
	def matches(entry: DictionaryEntry, filter_text: str) -> bool        # text 或 braille 的 casefold 子字串
	def source_text_exists(self, text: str, exclude_entry: DictionaryEntry | None = None) -> bool

	def apply_filter(self, filter_text: str, selected_index: int | None = None) -> EntryListUpdate
	def add(self, entry: DictionaryEntry) -> EntryListUpdate
	def replace(self, visible_index: int, entry: DictionaryEntry) -> EntryListUpdate
	def remove(self, visible_index: int) -> EntryListUpdate
```

語意（每一條都是現有程式碼的逐行轉寫）：

- `_refilter()`：有 `filter` 時 `visible = [e for e in entries if matches(e, filter)]`，否則 `list(entries)`。
- `_selection_after(preferred, fallback_index)`：沒有可見項目時為 `None`；否則 `min(fallback_index, n - 1)`，若 `preferred` 不是 `None` 且有相等的可見項目，改為 `visible.index(preferred)`。
- `apply_filter(text, selected_index)`：在變更**之前**從可見清單取得 `preferred = visible_entry(selected_index)`；設定 `filter = text`；`_refilter()`；`EntryListUpdate(_selection_after(preferred, 0))`。
- `add(entry)`：`source_text_exists(entry.text)` -> `raise DuplicateEntryError(entry.text)`，什麼都不變；附加；`cleared = bool(filter) and not matches(entry, filter)`；若 cleared，`filter = ""`；`_refilter()`；`EntryListUpdate(_selection_after(entry, 0), filter_cleared=cleared)`。
- `replace(i, entry)`：`current = visible[i]`（`i < 0` 或 `i >= visible_count` 時 `IndexError`；不使用負數索引）；`source_text_exists(entry.text, exclude_entry=current)` -> `DuplicateEntryError`，什麼都不變；取代完整清單中 `is current` 的項目；`_refilter()`；`EntryListUpdate(_selection_after(entry, i))`。
- `remove(i)`：`current = visible[i]`（同樣的範圍檢查）；`entries.remove(current)`（第一個相等的）；`_refilter()`；`EntryListUpdate(_selection_after(current, i))`。
- `cell_text(row, column)`：`visible[row]` 用一般索引（與現在相同；wx 從不傳負數列）；欄 0/1/2 與現在相同；其他欄 `ValueError(f"Unknown column: {column}")`。
- `source_text_exists(text, exclude_entry)`：`any(e.text == text and e is not exclude_entry for e in entries)`。
- `save(path)` 直接傳入內部 list（與現在相同的走訪順序與位元組）。
- `replace` 與 `remove` 經由私有的 `_visible_at(i)` 讀取 `visible[i]`，超出範圍時拋出 `IndexError("visible index out of range: N")`。docstring 寫明 D4 的比較規則；模組 docstring 以標題（「Custom Dictionary Manager」）稱呼對話框，因此步驟 4 的更名不會動到模型。

允許的匯入：`__future__`、`collections.abc`、`dataclasses`、`pathlib`、`dictionaries.entries`。模型測試中的 AST guard 禁止 `wx`、`gui`、`dialog`、`ui`、`settings` 與 `i18n`。

### 變更後的對話框

`DictionaryEntriesDialog(ContextManagedDialog, wx.Dialog)`（步驟 4 之前仍叫 `SpeechSymbolsDialog`）。保留的屬性名稱：`dictionary_path`、`filter_ctrl`、`list_ctrl`、`add_button`、`edit_button`、`remove_button`；新增私有的 `_model`。移除：`entries`、`filtered_entries`、`_load_entries`、`_get_item_text`、`_entry_matches_filter`、`_identifier_exists`、`_normalize_type`、`_save_entries`、`preferred_entry`/`fallback_index` 參數，以及不再使用的匯入（`List`、`save_dictionary_entries`、`normalize_entry_type`）。`load_dictionary_entries` 仍保留匯入：`DictionaryManagementDialog._load_dictionary_counts` 仍呼叫它來顯示每個字典的項目數。`dialog.py` 新增 `from dictionaries.entry_list_model import DictionaryEntryListModel, DuplicateEntryError, EntryListUpdate`。

- `__init__(parent, dictionary_path)`：`super().__init__`（相同參數）-> `self.dictionary_path = Path(dictionary_path)` -> `self._model = DictionaryEntryListModel.load(self.dictionary_path)` -> `_build_ui()`（完全相同；清單回呼為 `self._model.cell_text`）-> `_render(self._model.apply_filter(self.filter_ctrl.GetValue(), self._get_selected_index()))` -> `_update_button_states()`。
- `_render(update)`：`SetItemCount(model.visible_count)`、`Refresh()`；`selection is None` -> `_clear_selection()`、`_update_button_states()`；否則 `_select_index(selection)`（不變）。
- `_on_filter_changed(event)`：`_render(model.apply_filter(filter_ctrl.GetValue(), _get_selected_index()))`、`event.Skip()`。
- 新增：`entry = _open_entry_dialog()`；`None` -> return；`try: update = model.add(entry)` / `except DuplicateEntryError as error:` 以 `identifier=error.identifier` 顯示相同的 `MessageBox`，return（兩個重複訊息框都經由同一個私有輔助方法 `_show_duplicate_error(identifier)`：msgid、文字、標題、旗標與 parent 相同，同一檔案中由兩個原始碼位置變為一個，msgid 集合不變）；`if update.filter_cleared: filter_ctrl.ChangeValue("")`；`_render(update)`。wx 呼叫順序不變：訊息框在任何變更之前；`ChangeValue` 在 `SetItemCount` 之前。
- 編輯：`index = _get_selected_index()`、`current = model.visible_entry(index)`；`index is None or current is None`（保留兩段式判斷）-> 在開啟項目對話框前 return；`updated = _open_entry_dialog(current)`；`None` -> return；`model.replace(index, updated)`，重複處理相同；`_render(update)`。
- 刪除：`index = _get_selected_index()`；`None` -> return；`_render(model.remove(index))`。
- 確定：`try: self._model.save(self.dictionary_path)` / `except IOError as exc:` 相同的訊息框，return；`event.Skip()`。
- `_update_button_states`、`_get_selected_index` 與 `_select_index`（範圍改為 `model.visible_count`）、`_clear_selection`、`_on_selection_changed`、`_on_item_activated`、`_open_entry_dialog`：不變。

`gui.py` 只在步驟 4 變更（匯入與建構子名稱）。它不匯入模型。

### stub scope 下的測試

- 對話框測試在模組層級、於 `wx_stub.load_speech_dialog()` **之前**匯入 `dictionaries.entry_list_model`（就像現在對 `dictionaries.entries` 的做法），讓該模組不是在 scope 內首次匯入、不會被驅逐，對話框與測試共用同一個 `DuplicateEntryError`/`DictionaryEntryListModel` 類別。
- `test_dialog_validation`（隔離 `dialog`、不驅逐）與 `test_dialog_display`（全部驅逐）經由 `dialog` 匯入模型；模型不持有任何 stub 參照，所以 `StubScope._check_leaks` 不會報錯。gui scope 使用假的 `dialog` 模組，從不匯入模型。
- 模型測試是一般的 `unittest`，沒有 stub scope。

## 保持不變的部分

- 所有使用者看得到的字串（英文與 zh_TW）、標題、標籤、欄寬、清單樣式、按鈕組合、建立／Tab 順序，以及每個靜態文字所命名的控制項。
- 每個動作：是否開啟項目對話框及帶入哪個項目、訊息框文字／標題／旗標／parent 以及它相對清單變更的先後、`ChangeValue` 或 `SetValue`、`SetItemCount`/`Refresh`/`Select`/`Focus` 的呼叫序列、選取與聚焦的列、編輯／刪除的啟用狀態、篩選框的值。
- D4 的比較規則、跨隱藏項目的重複檢查、完整清單順序、每次確定都儲存完整清單（即使未變更）、`OSError` 訊息且對話框保持開啟、其他例外照樣拋出、取消不寫入。
- `AddSymbolDialog`、`CallbackVirtualListCtrl`、`DictionaryManagementDialog`、`dictionaries/entries.py`、`client/locales`、`scripts/`、`client/conversion`、`client/translation`：沒有差異。

## 測試計畫

先做特性測試。A 部分在任何產品程式碼變更之前提交，之後除了步驟 3 的 C 部分新增內容與步驟 4 的機械式更名（只改類別與模組名稱）外不再修改。A 部分在現有程式碼上不可能是紅的，所以用一個拋棄式的 mutant runner（不提交）對 `client/` 的副本套用 15 個單點破壞，證明每一個都會讓 A 部分失敗：以 `lower()` 取代 `casefold()`；比對類型欄；在重新篩選後才讀取先前選取；以同一物件而非相等還原選取；編輯以相等（第一個相等者）而非同一物件取代；刪除以同一物件而非第一個相等者；重複檢查不分大小寫；重複檢查只看可見項目；重複檢查不排除自己；新項目符合篩選時仍清除篩選；編輯時清除篩選；以 `SetValue("")` 取代 `ChangeValue("")`；fallback 索引未夾在範圍內；只儲存可見清單；儲存失敗後仍 `Skip()`。

### A. 對話框特性測試（步驟 1，`tests/test_speech_symbols_dialog.py`）

1. 測試模組內的**黑箱 harness**。它只透過 wx 介面驅動對話框，因此重構後不需修改：
   - `object.__new__(DialogClass)`；patch stub 基底的 `__init__`（只擷取一次並存為 `_NATIVE_DIALOG_BASE`，讓兩個 harness 永遠不會在已 patch 的 `wx` 上查找 `Dialog`）以記錄 `(title, style)`；替換模組的 `wx`、`CallbackVirtualListCtrl` 與 `AddSymbolDialog`；對話框實例取得 `CreateButtonSizer`、`FindWindowById`、`SetSizerAndFit`、`GetParent`、`CentreOnParent`、`Centre` 與 `Destroy`。`wx` 命名空間以互異 2 的冪為旗標、`NOT_FOUND = -1`，並有會記錄的 `TextCtrl`/`Button`/`StaticText`/sizer 與 `MessageBox`。假清單擷取儲存格回呼、維護 `GetFirstSelected` 狀態、在項目數縮減到選取列以下時丟掉選取（與 P2-2 之前的假物件相同），且程式設定的 `Select` 不送出事件；把 `AddSymbolDialog` 換成照腳本行動的假物件（記錄開啟時帶入的項目；`ShowModal` 回傳 `ID_OK` 或 `ID_CANCEL`；`get_entry` 回傳腳本指定的項目）；然後執行真正的 `__init__(parent, dictionary_path=<暫存 CSV>)`。「基底 `__init__` 在讀檔之前」的證明方式是在 patch 過的基底 `__init__` 內寫入 CSV：列有出現，表示檔案是之後才讀取的。
   - 動作經由擷取到的繫結進行：`type_filter(text)`（設定值、觸發 `EVT_TEXT`）、`select(i)`（設定選取、觸發 `SELECTED`）、`click("Add"|"Edit"|"Delete")`（依標籤找按鈕）、`activate()`、`press_ok()`（回傳是否呼叫了 `Skip`）。
   - 觀察：一份依呼叫順序記錄的紀錄，內容為基底 `__init__`（title、style）、`StaticText` 標籤、`TextCtrl`、`ListCtrl`（style）、`InsertColumn`、每個 `Bind`、`Button` 標籤、`CreateButtonSizer`、確定／取消的 `SetLabel`、`SetSizerAndFit`、`CentreOnParent`、`SetItemCount`、`Refresh`、`Select(index, on)`、`Focus`、`Enable(label, state)`、`ChangeValue`、`SetValue`（與 wx 相同，也會觸發 `EVT_TEXT`）、`MessageBox(message, caption, flags)`、`AddSymbolDialog(entry)` 以及每個事件的 `Skip`（訊息框與項目對話框的 parent 另外保存）；經由擷取的儲存格回呼取得的可見列、選取／聚焦列、篩選值、確定後的 CSV 位元組。harness 從不讀取對話框的資料屬性。
2. 既有的 17 個對話框測試（篩選、build-UI 與變更類別）改寫到 harness 上，斷言不變；`CallbackVirtualListCtrlTest`、兩個載入測試與隔離測試（共 4 個）維持原樣（逐位元組相同）。改寫的測試保留名稱與斷言，改以觀察結果表達：`filtered_entries` 變成經由儲存格回呼讀出的可見列，`entries` 變成清除篩選後的列（或儲存的 CSV），`list_ctrl.selected` 變成假清單的選取。有兩處準備步驟改變：篩選測試類別經由項目對話框新增 Beta（`Needle`、Bopomofo），因為真正的載入器會丟掉點字不是注音的 Bopomofo 列（舊測試繞過了載入器）；刪除測試經由項目對話框新增 Alpine，而不是附加到 `entries`。
3. 新增特性測試：建構（基底 `__init__` 在讀檔之前；標題／樣式；建立順序與欄位表；初始紀錄 `SetItemCount(n)`、`Refresh`、`Select(0)`、`Focus(0)`；空檔案與不存在的檔案：數量 0、按鈕停用；無效 UTF-8 檔案從建構子拋出 `UnicodeDecodeError`）；儲存格回呼（三欄、zh_TW 類型標籤、未知欄 `ValueError`）；篩選（casefold `STRASSE`/`Straße`、字面空白、不比對類型、以相等保留選取且相同列時選第一個、fallback 到 0、結果為空（使用假清單時 `SetItemCount(0)` 已丟掉選取，所以紀錄是 `SetItemCount(0)`、`Refresh`、`Enable(Edit, False)`、`Enable(Delete, False)`，沒有 `Select(i, False)`）、完整紀錄）；新增（取消不做事；與隱藏項目重複；大小寫不同的文字被接受；精確訊息 `來源文字「Alpha」已存在。`、標題 `錯誤`、`OK | ICON_ERROR`、parent；附加在尾端；符合的篩選保留；不符合的篩選在 `SetItemCount` 前以 `ChangeValue("")` 清除）；編輯（按鈕與 activate；無選取不開啟；相同文字被接受；重複被拒；相同列時以同一物件取代；篩選保留；fallback 夾在範圍內；結果為空）；刪除（不確認；最近的列；最後一列；相同列時移除第一個相等者，可由儲存的 CSV 順序看出）；確定（依序儲存完整清單；未變更的字典以正規化形式重寫，丟掉載入時略過的列；建立上層目錄；路徑是目錄時的 `OSError`：訊息 `儲存失敗：{exc}` 由拋出的錯誤組成（其文字在 Linux 與 Windows 不同）、不 `Skip`、編輯保留且之後的確定可成功；寫入器拋出的非 `OSError` 不 `Skip` 並往外拋）；只有確定有處理函式；確定／取消標籤已在地化。固定 Q1-Q8 的測試標上 `# KNOWN BUG (P2-2 spec, Qn)`（見「保留的怪異行為」）。
4. **黃金軌跡** `tests/fixtures/dictionary_entries_trace.json`：測試模組中的確定性產生器（`random.Random(seed)`，40 個序列、每個 25 個動作：篩選、選取或取消選取、以確定／取消／重複結束的新增／編輯、activate、刪除、最後按確定），使用會強迫碰撞的小字母表（`a`、`A`、`ab`、`Ab`、`Straße`、`STRASSE`、空點字、三種類型；初始 CSV 含相同列（`a`）、前後有空白的欄位（` Ab `、` SS `）、會被略過的空文字列、會被略過的無效 Bopomofo 列、`Straße`/`STRASSE`、空點字與未知類型）。動作種類的權重為篩選 2、選取 2、取消選取 1、新增 2、編輯 1、activate 1、刪除 1；新增／編輯／activate 有 20% 取消；30% 的項目使用新的 `n<i>` 文字，其餘會碰撞。選取會從目前的可見清單挑一列（清單為空時改為取消選取），所以產生器需要實際運作的編輯器：重播測試驅動測試資料中記錄的動作，產生器只用來寫出測試資料。每個序列有 27 步（開啟、25 個動作、最後的確定）；每一步保存動作、自上一步以來的呼叫紀錄與狀態（`rows`、`selected`、`focused`、`edit`、`delete`、`filter`；`rows` 與上一步相同時省略），最後的確定步驟另外加上儲存的 CSV。每行一個精簡的 JSON 步驟，UTF-8。測試資料在步驟 1 由未修改的程式碼產生一次（300,540 位元組，低於 300 KiB 的目標；sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`，也寫在提交訊息中），之後不在 repo 中重新產生。在 1,000 個動作中，軌跡開啟項目對話框 331 次（87 次照腳本取消）、顯示 76 次重複訊息框，並有 38 次由新增清除篩選。重播測試逐步比對。

### B. 模型（步驟 2，新增 `tests/test_dictionary_entry_list_model.py`，tab，無 wx，無 stub scope）

先寫測試（紅：模組不存在）。涵蓋每個方法以及 D4 的每條規則（含相同列的情況）；`visible_entry` 邊界（`None`、-1、count）；`replace`/`remove` 對 -1 與 count 拋出 `IndexError` 且不變更任何東西；`DuplicateEntryError` 是帶 `identifier` 的 `ValueError` 且狀態不變；有不符合的篩選時 `add` 回傳 `filter_cleared=True` 且 `filter_text == ""`；回傳的 tuple 是快照；載入不存在的檔案得到空模型；`save`/`load` 往返；篩選中 `save` 仍寫完整清單；`cell_text` 各欄與未知類型的標籤 fallback；AST 匯入 guard。

### C. 遷移（步驟 3）

A 部分不變，且必須維持綠燈（包括黃金軌跡重播）。新增：一個測試確認 `dictionary_path` 沒有預設值（`inspect.signature`），一個測試確認對話框的 `_model` 是從 `dictionary_path` 載入的 `DictionaryEntryListModel`（類別 `SpeechSymbolsDialogModelTest`，附加在 A 部分的模組中）。模組開頭新增兩個匯入：`inspect` 與 `DictionaryEntryListModel`（在 `wx_stub.load_speech_dialog()` 之前匯入；步驟 1 時模型模組還不存在），因此步驟 3 對測試模組的 `git diff` 只有新增。

### D. 更名（步驟 4）

只有機械式修改；`git diff -M` 顯示測試模組為更名。`tests/test_gui_document_flows.py` 的保留名稱 guard 與 `_GUI_DIALOG_NAMES` 改為 `DictionaryEntriesDialog`。在 `gui.py` 的 `from dialog import (...)`、`test_dialog_validation` 的匯入區塊與 `_GUI_DIALOG_NAMES` 中，`DictionaryEntriesDialog` 移到 `DictionaryManagementDialog` 之前以保持排序；`CONTEXT_MANAGED_DIALOGS` 維持原順序。wx_stub 中提到測試模組名稱的註解也一併更新（`tests/wx_stub.py` 變更 2 行）。保留不改：私有模組名稱 `_speech_symbols_dialog_under_test`，以及 `test_gui_document_flows` 中的測試方法 `test_edit_result_opens_speech_symbols_for_presenter_path`（小寫；AC6 的 grep 區分大小寫）。沒有新測試。

新增 84 個測試（889 -> 973）：步驟 1 新增 43 個（對話框模組由 21 個變為 64 個：保留 4、改寫 17、新增 43：建構 7、儲存格文字 2、篩選 8、新增 6、編輯 8、刪除 5、確定 5、軌跡 2）；步驟 2 新增 39 個（模型模組）；步驟 3 新增 2 個（C 部分）；步驟 4 不新增。完整測試必須為 973 個、`failures=1`、`skipped=9`。

## 遷移步驟（每一步一個綠燈提交）

1. `test: characterize dictionary entries editor`（A 部分、黃金軌跡測試資料）。
2. `refactor: add wx-free dictionary entry list model`（B 部分；模組尚未被使用）。
3. `refactor: use DictionaryEntryListModel in the entries editor`（對話框委派；`dictionary_path` 必填；移除無用的 `_normalize_type` 與未使用的匯入；C 部分）。
4. `refactor: rename SpeechSymbolsDialog to DictionaryEntriesDialog`（D 部分）。

## 驗收條件

1. Linux 上的路線圖驗證（使用更名後的模組）：`cd client && $PY -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog -v` 通過（105 個測試）。
2. 以下也全綠：`tests.test_dialog_validation tests.test_dialog_display tests.test_dictionary_entries tests.test_dictionary_management_dialog tests.test_dictionary_presenter tests.test_gui_document_flows tests.test_wx_stub tests.test_removed_dead_code tests.test_i18n tests.test_translation_golden`。
3. 完整測試：973 個測試（889 + 84）、`failures=1`（只有 P2-5）、`errors=0`、`skipped=9`。shuffle harness 種子 0-19：每個種子都是同一個失敗。`test_dictionary_entries_dialog`、`test_dictionary_entry_list_model`、`test_dialog_validation`、`test_dialog_display` 與 `test_dictionary_management_dialog` 單獨執行，以及各自與 `test_dictionary_entry_list_model` 配對的兩種順序都通過。
4. `git diff main -- client/tests/fixtures/translation_golden.json` 為空（sha256 `e67d95a1...1ccd`）；軌跡測試資料在步驟 1 與步驟 4 之間逐位元組相同，且步驟 4 之後由重構後的編輯器重新產生的軌跡（以 `write_trace_fixture` 寫到暫存路徑）與提交的測試資料逐位元組相同。
5. msgid 掃描：353；`git diff main --stat -- client/locales scripts client/dictionaries/entries.py client/conversion client/translation` 為空。
6. `grep -rn "SpeechSymbols" client --include=*.py` 沒有輸出（保留的 wx_stub 設定檔名稱是小寫 `speech_*`／`SPEECH_*`）；`grep -rn "filtered_entries\|_identifier_exists\|_normalize_type\|Path(\"data\")" client/dialog.py` 沒有輸出。
7. `client/dictionaries/entry_list_model.py` 通過 AST guard。

## 風險

- **篩選文字同步（D3）。** 若真實 wx 有某條路徑在沒有 `EVT_TEXT` 的情況下改變篩選框，模型會用過時的文字篩選，而現在的程式碼會重新讀取篩選框。wx 對輸入、貼上、剪下、復原與 IME 確認都會送出 `EVT_TEXT`，而 client 中除了新增之外沒有任何地方對這個框呼叫 `SetValue`/`ChangeValue`。列入 Windows 驗證。若在 Windows 上不成立的備案：把 `filter_ctrl.GetValue()` 傳入 `add`/`replace`/`remove`（只是 API 變更）。
- **可見清單在 `ChangeValue` 之前就已更新。** 新增時，`ChangeValue("")` 執行時模型已重新篩選，而現在的程式碼是在它之後才變更可見清單。若 `ChangeValue` 內部重繪，會以舊的項目數讀取較長的清單。新增只會讓可見清單變長，所以不會讀到範圍外；而且 wx 在那裡不會同步重繪。
- **相等或同一物件。** 軌跡與 mutant 固定了每條規則；「修正」其中任何一條的模型都會讓 A 部分失敗。
- **stub scope 的類別同一性。** 由在 scope 之前匯入模型（見「stub scope 下的測試」）以及 shuffle 執行涵蓋。
- **更名遺漏。** 漏改 `_GUI_DIALOG_NAMES` 會讓 `gui` 在 gui scope 中匯入失敗（很明顯）。PyInstaller 追蹤靜態匯入；沒有 `.spec` 檔案提到這個類別（grep）。
- **真實 wx。** 這裡的一切只用 stub 檢查過。

## 保留的怪異行為（固定住，不修正）

1. **Q1 UTF-8 BOM 造成資料遺失。** 以 BOM 儲存的字典 CSV（例如 Excel 的「CSV UTF-8」）開啟後是空的（標頭被讀成 U+FEFF 加上 `text`），按確定會把它覆寫成只剩標頭。既有問題；與 P1-6 的 BOM 發現有關。由一個 A 部分的測試固定。建議另開修正任務：在 `load_dictionary_entries`（以及規則載入器）以 `utf-8-sig` 讀取。
2. **Q2** 確定一定會重寫檔案，悄悄丟掉載入時略過的列（文字為空、無效注音）以及被去除的空白。
3. **Q3** 儲存先截斷再寫入；寫到一半出錯會留下被截斷的檔案（沒有暫存檔 + 取代）。已驗證：檔案保留標頭與出錯那列之前的每一列（寫入器出錯時已寫出它們）；第一列是單獨的 surrogate 時只留下標頭，測試就是這樣固定的（第二列在磁碟上遺失）。
4. **Q4** 檔案中有相同來源文字時，任一列都無法在不改文字的情況下編輯（另一列算重複），而刪除會移除第一個相等的列，不一定是被選取的那列。
5. **Q5** 刪除不確認；取消不詢問就捨棄編輯。
6. **Q6** 新增／編輯時重複會丟掉使用者輸入的內容（不重新開啟項目對話框）。
7. **Q7** 儲存時的非 `OSError`（例如單獨 surrogate 造成的 `UnicodeEncodeError`）會逸出確定的處理函式。
8. **Q8** 載入錯誤在原生對話框建立後才從建構子逸出；`gui` 收到未處理的例外，對話框從未被銷毀。

固定這些行為的測試都標上 `# KNOWN BUG (P2-2 spec, Qn)`（修正屬於另一個任務）：Q1 `test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header`；Q2 `test_unchanged_dictionary_is_rewritten_in_normalized_form`；Q3 與 Q7 `test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file`；Q4 `test_identical_rows_edit_replaces_the_selected_row_but_cannot_keep_its_text` 與 `test_identical_rows_delete_removes_the_first_equal_row`；Q5 `test_delete_has_no_confirmation_and_selects_the_row_now_at_that_index` 與 `test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized`（取消沒有處理函式）；Q6 新增與編輯的兩個重複測試；Q8 `test_invalid_utf8_raises_from_the_constructor_after_the_native_dialog`。

## Windows 驗證待辦

- 打包版、zh_TW、搭配 NVDA：字典管理 -> 編輯開啟編輯器時第 1 列被選取並被讀出；在篩選框輸入時保留選取的項目；新增不符合的項目會清除篩選並選取它；編輯、在列上按 Enter、刪除（選取現在位於同一索引的列）；重複訊息；確定會儲存、取消會捨棄。在篩選框貼上、剪下與復原會更新清單（D3）。
- 對未變更的字典，把確定寫出的 CSV 與 `main` 逐位元組比對。
- 確認真實虛擬清單上 `SetItemCount` 對被選取列的影響（結果為空的分支；前後是同一條程式路徑）。
- PyInstaller 經由 `dialog.py` 中的靜態匯入收進 `dictionaries/entry_list_model.py`（閱讀確認，未實際執行）。
- 不需要螢幕截圖（沒有視覺變化）。

## 不在範圍內

- 修正 Q1-Q8（Q1 是資料遺失錯誤，應該另開任務）。
- 更名 `AddSymbolDialog`、wx_stub 的 speech 設定檔名稱，或移除未使用的 `DictionaryEntryListCtrl` 別名。
- 讓 `DictionaryEntry` 變成 frozen／可雜湊；修改 `dictionaries/entries.py`。
- 把訊息搬到 presenter；為這個對話框定義 View protocol。
- 對 `DictionaryManagementDialog` 或 P0-6 presenter 的任何變更。
