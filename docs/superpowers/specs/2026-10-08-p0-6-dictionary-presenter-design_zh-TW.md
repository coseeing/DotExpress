# 字典管理 Presenter（P0-6）設計

## 目標

把字典管理工作流從 `BrailleFrame` 搬到新模組 `client/dictionaries/presenter.py` 的 `DictionaryManagementPresenter`，它不依賴 wx、可單元測試。這是 roadmap 任務 P0-6（`storage/refactor.md` 第 6.1 節），處理 S-3（工作流散在 Frame 與 Dialog 兩邊、`on_duplicate`/`prompt_name` lambda 各寫三次、字典清單有兩個真相來源）與 I-1（`DictionaryManagementDialog` 要求 5 個位置回呼）。

完成後：

- `client/gui.py` 不再有五個 frame 回呼（`add_dictionary`、`delete_dictionary_from_dialog`、`rename_dictionary_from_dialog`、`import_dictionary_from_dialog`、`export_dictionary_from_dialog`）與 `_prompt_for_dictionary_name`。邏輯移到 presenter；只有 wx 呼叫留在 wx 程式碼中，位於一個小型 view protocol 後面。
- `DictionaryManagementDialog` 改收一個 `actions` 物件，取代 `dictionary_dir` 加五個回呼。
- 只有 presenter 的清單會列出字典目錄。移除 frame 的 `self._dictionary_names` 與 dialog 的 `_refresh_from_disk`。

對使用者的影響：無。每個對話框、訊息框、字串、標題、圖示、按鈕旗標、父視窗、提示與訊息的順序、檔案操作、清單選取與設定寫入都與現在完全相同。沒有 msgid 變動，因此不動 `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` 與 `.mo`。版面不變，不需要截圖。

## 方法與基準（2026-10-08 於 `refactor/p0-6-dictionary-presenter`、HEAD `70aae6b` 驗證，P0-1 至 P0-5 已合併）

1. 閱讀 `client/gui.py`（frame 狀態 294-300、563-609，工作流 1234-1438）、`client/dialog.py`（`DictionaryNameDialog` 191-239、`DictionaryManagementDialog` 650-845）、`client/dictionaries/` 下每個模組、`client/translation/dictionary_state.py`、`client/settings/translation.py`、`client/config.py`（`set_selected_dictionary`）、`client/shared/name_validation.py` 與 `scripts/generate-pot.bat`。
2. 以 grep 找出相關名稱的每個呼叫端與測試（`DictionaryManagementDialog`、`_dictionary_names`、`_refresh_dictionary_names`、`get_dictionary_names_for_dialog`、`_set_active_dictionary`、`_get_csv_wildcard`、`CSV_WILDCARD`、`prompt_dictionary_name_until_success`、`plan_dictionary_state_*`）。
3. 執行測試（venv Python，於 `client/`）：
   - `python -m unittest discover -s tests`：`Ran 482 tests`、`FAILED (failures=1, skipped=7)`。唯一失敗是已知的 P2-5 案例 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。
   - 各模組：`test_dictionary_management_dialog` 8、`test_dictionary_manager` 11、`test_dictionary_actions` 6、`test_translation_dictionary_state` 6、`test_dictionary_name_prompt` 4、`test_gui_document_flows` 61、`test_dictionary_entries` 8、`test_speech_symbols_dialog` 21、`test_settings_dialogs` 27，全部 `OK`。
   - roadmap 指令去掉尚不存在的 presenter 模組（`tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_actions tests.test_translation_dictionary_state tests.test_dictionary_name_prompt tests.test_gui_document_flows`）：`Ran 96 tests`、`OK`。

`storage/refactor.md` 的行號早於 P0-1 至 P0-5；上面的行號是目前的。

## 現況

### 誰擁有什麼

- `BrailleFrame._initialize_state`（294-300）設定 `self.dictionary_dir`、呼叫 `ensure_default_dictionary`、設定 `self._dictionary_names = list_dictionary_names(...)`、從 config 載入 `self.translation_settings`（以這份清單正規化 `selected_dictionary`）、載入點字表，接著再呼叫一次 `_refresh_dictionary_names(selected)`（第二次列目錄，結果未使用）。
- `_refresh_dictionary_names(preferred)`（563-567）呼叫 `ensure_default_dictionary`，從磁碟就地重填 `self._dictionary_names[:]`，回傳 `resolve_management_selection(names, preferred)`。
- `get_dictionary_names_for_dialog()`（569-571）以目前作用中的名稱 refresh 後回傳副本。呼叫端：`get_settings_snapshot`、`apply_settings_from_dialog`、`on_open_settings`（1181），以及新增、重新命名、匯入回呼（只為了 refresh 的副作用）。
- **作用中**字典是 `self.translation_settings.selected_dictionary`。只有兩處會改它：`apply_settings_from_dialog`（設定對話框，儲存三個翻譯設定）與 `_set_active_dictionary(name)`（600-606，建立新的 `TranslationSettings` 並呼叫 `config.set_selected_dictionary(name)`，寫一次 config）。後者只由刪除與重新命名呼叫。
- `DictionaryManagementDialog` 自己保存 `_dictionary_names`（建構時傳入的副本）、`dictionary_dir`（用於項目數與 `_refresh_from_disk`；每次動作成功後都重新列目錄）、`_selected_name`、`_dictionary_counts` 與 `edit_dictionary_name`。選取一列只更新 `_selected_name` 與按鈕狀態（`get_action_availability`），從不改變作用中字典。

所以名稱清單在兩處從磁碟讀取（frame 與 dialog），而 frame 另外保留一份快取清單，刪除流程把它當成「刪除前的名稱」。

### 流程清單（本變更必須完全保留的行為）

以下所有訊息框與對話框的父視窗都是管理對話框：dialog 以 `self` 作為 `parent` 傳入，每個回呼都用 `dialog_parent = parent or self`。「Info 框」指 `wx.MessageBox(msg, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=...)`。「Error 框」指 `wx.MessageBox(msg, _("Error"), wx.OK | wx.ICON_ERROR, parent=...)`（重複名稱 lambda 與 `_show_file_error`（以 `message.format(error=exc)` 格式化）產生的呼叫完全相同）。「名稱提示（title, initial）」指 `DictionaryNameDialog(parent, initial_name=initial)`、`SetTitle(title)`、`ShowModal()`；非 `wx.ID_OK` 即取消，否則回傳 `get_dictionary_name()`（已 strip）。`DictionaryNameDialog._on_ok` 已用 `normalize_dictionary_name` 驗證並自行顯示已在地化的 Info 框，因此下面大多數 `ValueError` 路徑只有在名稱通過對話框檢查、之後才失敗時會走到。

「名稱迴圈」指 `prompt_dictionary_name_until_success(initial, prompt_name, on_submit, on_duplicate)`：提示；取消回傳 `None`；`on_submit(name)`；遇到 `FileExistsError` 顯示 Error 框 `_('Dictionary "{name}" already exists.').format(name=name.strip())`，並以使用者輸入的名稱為初值再次提示。其他例外會離開迴圈。

**開啟**（`on_open_dictionary_management`，1234-1254）。以作用中名稱 refresh，以 modal 方式開啟管理對話框，傳入 refresh 後的清單與解析後的選取。關閉後：若結果是 `wx.ID_EDIT` 且 `edit_dictionary_name` 有值，以 modal 開啟 `SpeechSymbolsDialog(self, dictionary_path=<dir>/<name>.csv)`。之後不會重新開啟管理對話框。關閉：不做事。

**新增**（按鈕永遠啟用）。
1. 名稱迴圈：標題 `_("Add Dictionary")`、初值 `""`、送出 `create_dictionary(dir, name)`。
2. `ValueError`：Info 框顯示 `str(exc)`（來自 `normalize_base_name` 的未翻譯英文，例如 `Name 'default' is reserved.`），回傳 `None`。
3. `FileExistsError` 以外的 `OSError` **不攔截**，會從按鈕 handler 拋出。
4. 取消：回傳 `None`。
5. 成功：refresh（透過 `get_dictionary_names_for_dialog`），回傳 `plan_dictionary_state_after_add(active, names, path.stem).management_selected_name`。即使規劃出的 `active_selected_name` 不同，也從不改變作用中字典。

**刪除**（按鈕只在選取非預設字典時啟用）。
1. 若 `is_default_dictionary(name)`：Info 框 `_("The default dictionary cannot be deleted.")`，回傳 `None`。
2. 確認：`wx.MessageBox(_('Do you want to delete dictionary "{name}"?').format(name=name), _("Confirm Delete Dictionary"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=...)`。非 `wx.YES`：回傳 `None`。
3. 記下 `previous_names`（frame 的快取清單）與作用中名稱。
4. `delete_dictionary(dir, name)`。`OSError`：Error 框 `_("Failed to delete dictionary: {error}")`，回傳 `None`（不 refresh、不改設定）。`ValueError`（只會發生在像 `" default"` 這種步驟 1 沒擋到、但 `delete_dictionary` strip 後變成 `default` 的檔名）**不攔截**。
5. refresh，以 `plan_dictionary_state_after_delete(active, name, previous_names)` 規劃。若規劃出的作用中名稱與目前不同，呼叫 `_set_active_dictionary(planned)`（更新 `translation_settings` 並寫入 config）。回傳規劃的管理選取。

**重新命名**（按鈕只在選取非預設字典時啟用）。
1. 若 `is_default_dictionary(name)`：靜默回傳 `None`（無訊息）。
2. 名稱迴圈：標題 `_("Rename Dictionary")`、初值為選取的名稱、送出 `rename_dictionary_after_name_prompt(dir, selected, new)`（strip 後同名：不做檔案操作，回傳既有路徑；只改大小寫：會改名）。
3. `ValueError`：Info 框 `str(exc)`，回傳 `None`。`OSError`：Error 框 `_("Failed to save dictionary: {error}")`，回傳 `None`。（`FileExistsError` 由迴圈處理，不會到這裡。）
4. 取消：回傳 `None`。
5. 成功：讀取作用中名稱，以 `path.stem` refresh，以 `plan_dictionary_state_after_rename(active, selected, path.stem, names)` 規劃（舊程式碼在這裡透過 `get_dictionary_names_for_dialog` 又 refresh 一次）。若規劃出的作用中名稱不同，呼叫 `_set_active_dictionary(planned)`。回傳規劃的管理選取。

**匯入**（按鈕永遠啟用）。
1. `wx.FileDialog(parent, _("Import Dictionary"), wildcard=_("CSV files (*.csv)|*.csv"), style=wx.FD_OPEN)`。非 `wx.ID_OK`：回傳 `None`。檔案對話框在下一步之前就已銷毀。
2. 名稱迴圈：標題 `_("Add Dictionary")`（原文如此，不是 "Import"）、初值為來源檔名主幹、送出 `import_dictionary(dir, source, name)`。目的地是否存在的檢查在 CSV 驗證之前，因此即使檔案無效，重複名稱也會再次提示。
3. **任何** `ValueError`（缺少欄位標頭、名稱無效，或讀取來源時的 `UnicodeDecodeError`）：Error 框 `_("Imported file must contain text, braille, and type headers.")`，回傳 `None`。`OSError`（例如來源檔消失）：Error 框 `_("Failed to import dictionary: {error}")`，回傳 `None`。
4. 取消：回傳 `None`。
5. 成功：同新增步驟 5。從不改變作用中字典。

**匯出**（清單非空時啟用）。
1. 若 frame 的快取清單為空，直接返回（無 UI）。
2. `wx.FileDialog(parent, _("Export Dictionary"), defaultFile=f"{name}.csv", wildcard=_("CSV files (*.csv)|*.csv"), style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)`。非 `wx.ID_OK`：返回。
3. `export_dictionary(dir, name, destination)`。`OSError`：Error 框 `_("Failed to export dictionary: {error}")`。
4. 一律回傳 `None`；匯出後 dialog 從不 refresh。

**編輯**（清單非空時啟用）。dialog 設定 `edit_dictionary_name` 並以 `wx.ID_EDIT` 結束 modal（見「開啟」）。

**動作後的 dialog refresh。** 新增、刪除、重新命名與匯入的回呼回傳名稱（非 `None`）時，dialog 呼叫 `_refresh_from_disk(name)`：重新列目錄（不呼叫 `ensure_default_dictionary`）、重新載入項目數、`SetItemCount`、`Refresh`、選取並聚焦 `resolve_dictionary_selection(names, name)`、調整欄寬、更新按鈕狀態。回傳 `None` 時清單維持原狀。

**選取／啟用。** 字典管理內沒有「啟用」動作。作用中字典在設定對話框選擇（`TranslationSettingsPanel`，名稱來自 `get_dictionary_names_for_dialog`），由 `apply_settings_from_dialog` 儲存；或如上所述由刪除與重新命名隱性改變。

### 重複與耦合（S-3、I-1）

- 重複名稱的 Error 框 lambda 寫了三次（新增、重新命名、匯入），`prompt_name` lambda 也是三次。
- `DictionaryManagementDialog.__init__` 有 9 個參數：parent、名稱、選取、目錄與 5 個位置回呼。
- frame 的快取清單與 dialog 的目錄列舉是兩個真相來源。它們今天一致，只因為 frame 在每個成功回呼內、就在 dialog 重新列目錄之前先 refresh。
- 沒有任何測試涵蓋這五個回呼或 `on_open_dictionary_management`。它們呼叫的純函式（`manager`、`name_prompt`、`actions`、`translation.dictionary_state`）有測試。

## 設計

### 決策：presenter 擁有名稱清單與工作流；dialog 是被動 view

考慮過的方案：

1. **由 frame 建立五個 callable 組成的 `DictionaryManagementActions` dataclass。** 解決位置參數簽名（I-1），但工作流、lambda 與第二份清單仍留在 `gui.py`。不採用為主要設計。dialog 仍只收一個以 protocol 定型的 actions 物件，因此未來新增動作（例如「複製」）是加一個方法，而不是加建構子參數。
2. **依 S-3 建議，presenter 回傳 `DictionaryStateUpdate` 讓 frame 套用。** 不採用。這會讓「套用 update 再呼叫 `_set_active_dictionary`」的步驟留在 frame 重複出現。presenter 透過注入的回呼自行套用 update，只回傳 dialog 需要的東西：要選取的名稱。
3. **依 S-3 建議，presenter 擁有作用中名稱（「持有 `active_name`」）。** 不採用。設定對話框也會改 `translation_settings.selected_dictionary`，第二份副本會製造新的雙真相來源問題。presenter 透過 `get_active_name()` 讀取、透過 `set_active_name(name)` 修改；frame 把它們接到 `translation_settings` 與 `_set_active_dictionary`。
4. **在 `gui.py` 另寫一個 wx view adapter 類別。** 不採用。每個提示與訊息框的父視窗都是管理對話框，dialog 本身就是自然的 view。讓 dialog 實作 view protocol，frame 的接線只需一行，父視窗也維持相同。
5. **採用：** `client/dictionaries/presenter.py` 的 `DictionaryManagementPresenter` 擁有目錄列舉、名稱清單與五個流程。它在呼叫當下以 `from i18n import _` 建立每個對使用者的字串，只透過 `DictionaryManagementView` protocol 與使用者互動。`DictionaryManagementDialog` 以上述完全相同的 wx 呼叫實作該 protocol，並以 presenter 作為 `actions`。

### `client/dictionaries/presenter.py`

使用 tab 縮排，與 `dictionaries/name_prompt.py`、`dictionaries/actions.py` 一致。只 import 標準函式庫、`i18n._`、`dictionaries.manager`、`dictionaries.actions`、`dictionaries.name_prompt` 與 `translation.dictionary_state`。不得 import `wx`（由測試把關）。manager 函式以名稱 import 進模組，測試可在 presenter 模組上 patch 它們注入錯誤。以下名稱確定意圖；plan 只能調整拼寫。

```python
class DictionaryManagementView(Protocol):
	def prompt_dictionary_name(self, title: str, initial_name: str) -> str | None: ...
	def show_info(self, message: str) -> None: ...
	def show_error(self, message: str) -> None: ...
	def confirm(self, message: str, caption: str) -> bool: ...
	def choose_import_path(self, title: str) -> Path | None: ...
	def choose_export_path(self, title: str, default_file: str) -> Path | None: ...


class DictionaryManagementActions(Protocol):
	@property
	def dictionary_names(self) -> list[str]: ...
	def dictionary_path(self, name: str) -> Path: ...
	def add(self, view: DictionaryManagementView) -> str | None: ...
	def delete(self, view: DictionaryManagementView, name: str) -> str | None: ...
	def rename(self, view: DictionaryManagementView, name: str) -> str | None: ...
	def import_from_file(self, view: DictionaryManagementView) -> str | None: ...
	def export_to_file(self, view: DictionaryManagementView, name: str) -> None: ...


class DictionaryManagementPresenter:  # 滿足 DictionaryManagementActions
	def __init__(self, dictionary_dir: Path, *, get_active_name: Callable[[], str],
	             set_active_name: Callable[[str], None]) -> None: ...  # 不做 I/O
	dictionary_dir: Path                      # 唯讀
	dictionary_names -> list[str]             # 唯一清單的副本
	def refresh(self, preferred_name: str | None = None) -> str: ...
	def dictionary_path(self, name: str) -> Path: ...
	# add / delete / rename / import_from_file / export_to_file 同 protocol
```

- `refresh(preferred)`：`ensure_default_dictionary(dir)`，以 `list_dictionary_names(dir)` 取代清單，回傳 `resolve_management_selection(list, preferred)`。即今天的 `_refresh_dictionary_names`。
- `dictionary_names` 每次回傳新 list，frame 與 dialog 都無法改動 presenter 的清單。
- `dictionary_path(name)` 即 `dictionary_path_for_name(name, dir)`。
- 一個私有 helper 執行名稱迴圈：`prompt_dictionary_name_until_success(initial, prompt_name=lambda n: view.prompt_dictionary_name(title, n), on_submit=submit, on_duplicate=lambda n: view.show_error(_('Dictionary "{name}" already exists.').format(name=n.strip())))`。取代各三份的 lambda。
- 五個流程逐步依照流程清單，對應如下：Info 框對應 `view.show_info(msg)`，Error 框對應 `view.show_error(msg)`（檔案錯誤先格式化為 `_("Failed to ... {error}").format(error=exc)`），確認框對應 `view.confirm(msg, _("Confirm Delete Dictionary"))`，檔案對話框對應 `choose_import_path(_("Import Dictionary"))` 與 `choose_export_path(_("Export Dictionary"), f"{name}.csv")`，「refresh」對應 `self.refresh(...)`，「frame 的快取清單」對應 presenter 的清單，「作用中名稱」對應 `get_active_name()`，`_set_active_dictionary` 對應 `set_active_name`。
- 流程清單中的例外特性維持原樣：新增不攔截 `OSError`；刪除不攔截 `ValueError`；匯入把所有 `ValueError` 都對應到標頭訊息；以預設名稱重新命名時無訊息回傳 `None`；新增與匯入從不改變作用中字典。每一項都由 presenter 測試釘住，並列於後續工作。
- refresh 時機：新增、匯入或重新命名成功後，presenter 恰好 refresh 一次（重新命名用 `path.stem`，新增與匯入用作用中名稱）；刪除成功後以被刪的名稱 refresh 一次。舊的重新命名、新增與匯入路徑會在中間沒有任何變動的情況下第二次列目錄；去掉這次多餘的列舉無法被觀察到。

### `DictionaryManagementDialog`（`client/dialog.py`）

- 建構子：`DictionaryManagementDialog(parent, actions: DictionaryManagementActions, selected_name: str)`。保存 `self._actions`，以 `self.refresh_dictionaries(actions.dictionary_names, selected_name)` 初始化清單。移除 `dictionary_dir` 與五個回呼的參數及屬性。
- `_load_dictionary_counts` 改讀 `load_dictionary_entries(self._actions.dictionary_path(name))`。項目數仍是 dialog 的職責（顯示資料，不是清單本身）。
- dialog 繪製的清單（`self._dictionary_names`）只從 `actions.dictionary_names` 取得快照。`_refresh_from_disk` 改為呼叫 `self.refresh_dictionaries(self._actions.dictionary_names, preferred)` 的 helper。`dialog.py` 不再 import `list_dictionary_names`。
- 按鈕 handler 以相同的選取檢查與「只有非 `None` 結果才 refresh」規則呼叫 `self._actions.add(self)`、`delete(self, selected)`、`rename(self, selected)`、`import_from_file(self)`、`export_to_file(self, selected)`。匯出從不 refresh。編輯、關閉、選取與欄寬不變。
- dialog 以流程清單中完全相同的 wx 呼叫實作 `DictionaryManagementView`，父視窗為 `self`：
  - `prompt_dictionary_name`：搬移今天 `gui._prompt_for_dictionary_name` 的內容。
  - `show_info`、`show_error`：Info 框與 Error 框。
  - `confirm`：`wx.MessageBox(message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self) == wx.YES`。
  - `choose_import_path`、`choose_export_path`：兩個 `wx.FileDialog` 區塊，回傳 `Path(GetPath())` 或 `None`。
- CSV 篩選字串隨檔案對話框搬移：`dialog.py` 新增 `CSV_WILDCARD = "CSV files (*.csv)|*.csv"`，並在呼叫當下翻譯，與現在的 `gui._get_csv_wildcard` 相同。msgid 仍可透過 `gui.py` 既有的 `N_("CSV files (*.csv)|*.csv")` 標記擷取；本變更不動該標記。

### `BrailleFrame`（`client/gui.py`）

- `_initialize_state`：設定 `self.dictionary_dir` 後，建立 `self._dictionary_presenter = DictionaryManagementPresenter(self.dictionary_dir, get_active_name=lambda: self.translation_settings.selected_dictionary, set_active_name=self._set_active_dictionary)`，呼叫 `refresh()`，再以 `self._dictionary_presenter.dictionary_names` 載入翻譯設定。去掉第二次未使用的列舉。
- `get_dictionary_names_for_dialog()` 保留名稱與契約：`refresh(active)` 後回傳 `dictionary_names`。呼叫端不變。
- `on_open_dictionary_management`：`selected = self._dictionary_presenter.refresh(active)`，接著 `DictionaryManagementDialog(self, self._dictionary_presenter, selected)`。編輯分支使用 `self._dictionary_presenter.dictionary_path(edit_name)`。`SpeechSymbolsDialog` 部分不變（歸 S-4/P1）。
- `_set_active_dictionary` 原封不動留在 frame，作為 presenter 的 `set_active_name`。
- 移除：`_dictionary_names`、`_refresh_dictionary_names`、五個回呼、`_prompt_for_dictionary_name`、`CSV_WILDCARD`、`_get_csv_wildcard`，以及因此不再使用的 import（`create_dictionary`、`delete_dictionary`、`export_dictionary`、`import_dictionary`、`list_dictionary_names`、`ensure_default_dictionary`、`is_default_dictionary`、`prompt_dictionary_name_until_success`、`rename_dictionary_after_name_prompt`、`plan_dictionary_state_after_*`、`resolve_management_selection`、`DictionaryNameDialog`）。`self.dictionary_dir`、`_get_selected_dictionary_path` 與 `_show_file_error` 保留（其他功能使用）。
- 不改 `_MENU_TRANSLATION_MARKERS`。

### 字串與在地化

每個字串保留完全相同的 msgid，且仍在顯示當下經過 `_()`。字串從 `gui.py` 移到 `dictionaries/presenter.py`（訊息、標題、對話框標題）與 `dialog.py`（`_("Info")`、`_("Error")`、CSV 篩選字串）。`scripts/generate-pot.bat` 會收集 `client/` 下除 `tests/` 外的每個 `*.py`，兩個檔案都會被掃描。在 Windows 重新產生範本時只有 `#:` 位置註解會變，本任務不要求重新產生。`.po` 與 `.mo` 不動。

### Commit 順序

每個 commit 都讓完整測試維持基準結果，外加它新增的測試。

1. `test:` + `feat:` 先寫測試的 presenter。逐流程撰寫 `tests/test_dictionary_presenter.py`（refresh 與名稱、新增、刪除、重新命名、匯入、匯出），每段先紅，再實作 `dictionaries/presenter.py` 對應部分。可為一或多個 commit；此時 app 尚未使用 presenter。
2. `refactor: route dictionary management through presenter`。必須是單一 commit，因為 dialog 建構子與其唯一呼叫端要一起改：先更新或新增 dialog 測試（actions 接線、view 方法），再讓 `DictionaryManagementDialog` 改用新建構子與 view 方法，`BrailleFrame` 建立並傳入 presenter，連同下述 `test_gui_document_flows` 的修改。
3. `refactor: remove dead dictionary callbacks from gui`。若步驟 2 尚未移除，刪除舊回呼、`_prompt_for_dictionary_name`、CSV 篩選字串 helper 與未使用的 import。不影響行為。

## 測試策略

### 新增：`client/tests/test_dictionary_presenter.py`（先寫）

純 `unittest`，不用 wx、不用 stub。以真實的 `tempfile.TemporaryDirectory` 作為 `dictionary_dir`。`FakeView` 依序把每個呼叫記錄成 tuple（`("prompt", title, initial)`、`("info", msg)`、`("error", msg)`、`("confirm", msg, caption)`、`("choose_import", title)`、`("choose_export", title, default_file)`），並從預先排好的佇列回答。作用中名稱放在 `get_active_name` 背後的單元素 list；`set_active_name` 是 `Mock`。預期字串以 `i18n._` 建立（catalog 固定為 zh_TW，英文字面值不會相符）。每個測試都斷言**完整的** `view.calls`、回傳值、磁碟上的檔案、`dictionary_names` 與 `set_active_name` 的呼叫。錯誤注入使用 `patch.object(presenter_module, "<manager 函式>", side_effect=PermissionError("denied"))`。

最少案例：

- 模組：`presenter.py` 不 import `wx`（以 AST 檢查 import）。
- `refresh`：缺少時建立 `default.csv`、以不分大小寫排序列出、回傳偏好名稱或退回 `default`；`dictionary_names` 回傳副本。
- `dictionary_path`。
- 新增：成功（以 `""` 提示 `Add Dictionary`、建立檔案、回傳新名稱、清單更新、未呼叫 `set_active_name`）；取消（無檔案、無訊息）；先重複再成功（以 strip 後名稱顯示 Error 框，以輸入名稱再次提示）；`ValueError`（保留名稱：Info 框 `str(exc)`，回傳 `None`）；`create_dictionary` 的 `OSError` 會拋出。
- 刪除：預設字典（只有 Info 框、無確認）；拒絕確認（檔案保留）；成功刪除非作用中名稱（作用中不變、未呼叫 `set_active_name`、回傳 `default`）；成功刪除作用中名稱（以規劃的退回名稱呼叫 `set_active_name`，例如從 `[alpha, beta, default]` 刪除 `beta` 會啟用 `alpha`）；`OSError`（先確認，再 Error 框 `Failed to delete dictionary: ...`，回傳 `None`，清單與作用中不變）；`" default"` 檔名的 `ValueError` 會拋出。
- 重新命名：預設字典（無 view 呼叫、`None`）；取消；成功（非作用中）；成功（作用中，`set_active_name(new)`）；同名（不改檔、不呼叫 `set_active_name`、回傳原名）；只改大小寫（會改名）；先重複再成功；`ValueError`（Info 框 `str(exc)`）；`rename_dictionary_after_name_prompt` 的 `OSError`（Error 框 `Failed to save dictionary: ...`）。
- 匯入：取消檔案對話框（不提示）；成功（以來源主幹提示 `Add Dictionary`、複製檔案、未呼叫 `set_active_name`）；先重複再成功；缺少標頭（標頭訊息的 Error 框）；fake view 回傳的無效名稱（同樣是標頭訊息）；來源檔不存在（`FileNotFoundError`：Error 框 `Failed to import dictionary: ...`）；取消名稱提示。
- 匯出：清單為空（無 view 呼叫）；取消；成功（以 `<name>.csv` 呼叫 `choose_export`、複製檔案）；`OSError`（Error 框 `Failed to export dictionary: ...`）。

### 修改：`client/tests/test_dictionary_management_dialog.py`

`_make_dialog` 改設定假的 `_actions`（名稱、`dictionary_path`、記錄動作呼叫），取代 `dictionary_dir`。既有測試保留原斷言。磁碟 refresh 測試改為「動作後的 refresh 從 `actions.dictionary_names` 取名稱，而非磁碟」（假物件回傳磁碟上不存在的名稱）。新增測試：

- 新增、刪除、重新命名、匯入各自以 `(dialog[, selected])` 呼叫動作，並以回傳名稱 refresh；`None` 結果不動清單；刪除、重新命名、匯出在沒有選取時不做事；匯出從不 refresh。
- 每個 view 方法恰好發出流程清單中的 wx 呼叫（訊息、標題、旗標、`parent=dialog`；檔案對話框標題、篩選字串、`defaultFile`、style），並在載入的 dialog 模組上 patch `wx.MessageBox`、`wx.FileDialog` 與 `DictionaryNameDialog`。取消路徑回傳 `None` 或 `False`。

本模組繼續使用 `wx_stub.load_speech_dialog()`。若旗標比較需要不同的值，plan 可以在 `speech_dialog_stubs()` 加入明確常數（`YES`、`YES_NO`、`NO_DEFAULT`、`ICON_WARNING`、`ICON_INFORMATION`、`ID_OK`、`FD_OPEN`、`FD_SAVE`、`FD_OVERWRITE_PROMPT`），前提是 `test_speech_symbols_dialog` 不改也仍通過。

### 修改：`client/tests/test_gui_document_flows.py`

- `_initialize_state_with_loaded_tables` 會 patch `gui.ensure_default_dictionary` 與 `gui.list_dictionary_names`（之後 `gui` 上不再有），並 mock `_refresh_dictionary_names`。改為 patch `gui.DictionaryManagementPresenter`（`dictionary_names` 為 `["default"]` 的 mock），或 patch presenter 模組上的這兩個函式。斷言不變。
- 移除設定 `frame._dictionary_names` 的行；這些測試本來就 mock `get_dictionary_names_for_dialog`。
- 新增：`on_open_dictionary_management` 以 `(frame, frame._dictionary_presenter, <refresh 後的選取>)` 建立 dialog；`wx.ID_EDIT` 且有名稱時以 `presenter.dictionary_path(name)` 開啟 `SpeechSymbolsDialog`；其他結果不開任何東西。`get_dictionary_names_for_dialog` 以作用中名稱 refresh 並回傳 presenter 的名稱。`_initialize_state` 建立的 presenter 會回呼 `_set_active_dictionary`，後者恰好寫一次 `set_selected_dictionary`。

### 不變的安全網

`test_dictionary_manager`、`test_dictionary_actions`、`test_translation_dictionary_state`、`test_dictionary_name_prompt`、`test_dictionary_entries`、`test_speech_symbols_dialog`、`test_settings_dialogs`、`test_i18n`（其重複翻譯設定掃描也涵蓋新模組）不修改也必須通過。

## 驗收條件

1. `client/dictionaries/presenter.py` 存在、不 import `wx`，並定義 `DictionaryManagementPresenter`、`DictionaryManagementView` 與 `DictionaryManagementActions`。
2. 在 `client/` 中 `tests/` 以外：`prompt_dictionary_name_until_success(` 恰好被呼叫一次（在 presenter），msgid `Dictionary "{name}" already exists.` 恰好出現一次。
3. `client/gui.py` 不含 `_dictionary_names`、`_refresh_dictionary_names`、`add_dictionary`、`delete_dictionary_from_dialog`、`rename_dictionary_from_dialog`、`import_dictionary_from_dialog`、`export_dictionary_from_dialog`、`_prompt_for_dictionary_name`、`_get_csv_wildcard`。
4. `DictionaryManagementDialog.__init__` 接收 `(parent, actions, selected_name)`。`client/dialog.py` 不呼叫 `list_dictionary_names`。
5. `client/` 中 `tests/` 以外傳給 `_()`/`N_()` 的 msgid 集合前後完全相同（以 AST 掃描檢查，因為 Linux 機器沒有安裝 `xgettext`）。`.po` 與 `.mo` 不變。
6. 於 `client/`：`python -m unittest tests.test_dictionary_presenter tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_actions tests.test_translation_dictionary_state tests.test_dictionary_name_prompt tests.test_gui_document_flows -v` 通過。
7. 於 `client/` 執行 `python -m unittest discover -s tests`：482 加上新測試，`failures=1`（只有 P2-5 案例），`skipped=7`，無 error。
8. Windows 手動檢查（Linux 機器無法執行，必須回報為未執行）：開啟字典管理，逐一操作新增（含重複名稱）、重新命名（作用中與非作用中）、刪除（作用中與非作用中，之後確認設定顯示退回的字典）、匯入（有效檔案、無標頭檔案）、匯出與編輯。每個提示、訊息與清單選取都與目前版本一致。

## 範圍外

- `SpeechSymbolsDialog` 與項目清單 model（S-4，P1）。
- `SettingsPanel` 的 `owner` 協定（I-2，P2）與設定對話框的字典選擇。
- 搬移 `translation/dictionary_state.py` 或與 `dictionaries/actions.py` 合併。
- 修改下列任何例外特性、任何字串，或匯入使用的 "Add Dictionary" 標題。
- 其他 `gui.py` 抽取（S-1 第 1、2、4、5 點）與 `config.py`（S-5）。

## 已知問題／後續工作

此處刻意保留，並由測試釘住，讓之後的修改成為有意識的決定：

- 新增不攔截 `create_dictionary` 的非 `FileExistsError` `OSError`，磁碟錯誤會從按鈕 handler 拋出，沒有訊息框。
- 刪除不攔截 `delete_dictionary` 的 `ValueError`（只有外部建立、主幹 strip 後為 `default` 的檔案才會發生）。
- 匯入對每個 `ValueError` 都顯示標頭訊息，包括名稱無效或檔案無法解碼。
- 新增與重新命名顯示的 `normalize_base_name` 錯誤是未翻譯的英文。
- 新增與匯入忽略規劃出的 `active_selected_name`，因此這些流程從不修正或儲存檔案已遺失的作用中字典。

## 風險

- **訊息的父視窗或順序跑掉。** 以 presenter 測試的完整序列斷言，以及 dialog view 方法測試中對 `parent=dialog` 與精確參數的斷言來降低。
- **字串在 import 時而非呼叫時翻譯。** presenter 與 dialog view 方法中的所有 `_()` 都在呼叫當下執行，與現在相同。於 plan 中檢查；`test_i18n` 持續把關共用 catalog。
- **`test_gui_document_flows` 的 patch 目標。** patch 一個 `gui` 已不再 import 的名稱會拋出 `AttributeError`。plan 在移除 import 的同一個 commit 中更新 `_initialize_state_with_loaded_tables`。
- **speech stub 的常數。** 在 speech stub 下，`dialog.py` 使用新的 `wx` 名稱會得到自動子模組。若測試需要不同的旗標值，在 `speech_dialog_stubs()` 加入常數，且不改變 `test_speech_symbols_dialog` 的結果。
- **僅能在 Windows 驗證。** Linux 機器沒有安裝 wxPython，這裡無法操作真正的對話框。驗收第 8 點是 Windows 上的手動步驟，在有人實際執行前必須回報為未執行。
