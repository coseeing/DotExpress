# 無法讀取的字典（F-6）設計

## 目標

任務 F-6 修正 F-W12（`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`「新發現」）：字典資料夾中只要有任一字典檔讀不到，選「字典管理」就完全沒反應，不會開視窗，也沒有訊息。最常見的原因是 Excel 把 CSV 存成 Big5（cp950）：在繁體中文 Windows 上，「另存新檔 -> CSV（逗號分隔）」寫出的是 Big5，所以用 Excel 存一次，使用者就再也打不開字典管理。被 ACL 拒絕讀取、被其他程式以不共用讀取的方式開著、或不是有效 CSV 的檔案，也會造成同樣的結果。

使用者的決定（2026-10-10，HANDOFF 第 5.3 節第 2 項；本文不重新提問）：

- **U1.** 讀不到的字典，條目數量欄顯示「無法讀取」（"Unreadable"）。其他字典照常顯示數量。使用者選取讀不到的字典時，對話框說明原因，例如「不是 UTF-8，請另存為 CSV UTF-8」。
- **U2.** 不自動偵測、也不讀取 Big5。猜編碼可能猜錯，而且在編輯器按確定之後，會默默把使用者的檔案改寫成 UTF-8。

本任務完成後：

- 字典管理一定打得開。每份字典分別讀取；讀取失敗的顯示為 `無法讀取`，失敗原因寫進 `gui.log`。在對話框內新增、刪除、重新命名、匯入之後，清單也保持正確。
- 選取讀不到的字典時，清單下方會出現一個有標籤的唯讀文字欄位，說明原因和處理方式。在 Tab 順序中它緊接在清單之後。對這份字典按「編輯」時，會在錯誤訊息框中顯示同樣的原因，並且留在對話框中；按下時會先重新讀檔，所以使用者在這期間修好的檔案可以正常開啟。
- 匯入會先讀完整個檔案再複製。不是 UTF-8 或不是有效 CSV 的檔案，會以同樣的原因文字拒絕匯入。目前的做法是顯示會誤導的表頭訊息（小的 Big5 檔），或默默匯入一個讀不到的檔案（前 8 KiB 全是 ASCII 的 Big5 檔）。
- 刪除、重新命名、匯出對讀不到的字典照常運作，行為不變。轉譯不變。

新的使用者可見字串：7 個（msgid 357 -> 364），在 `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` 翻譯，並重新產生 `.pot` 與 `.mo`。

非目標：讀取或轉換 Big5（U2）、依原因區分的轉譯錯誤訊息、「開啟字典資料夾」命令、即時更新筆數、`wx.MessageBox` 按鈕的語言（F-W9，任務 F-7）、沒有表頭或空白的 CSV 檔（仍算 0 筆），以及 HANDOFF 第 6 節的其他項目。

## 現況（2026-10-10 於 `fix/f6-unreadable-dictionaries` 驗證，HEAD `e46ff26`，Windows 11 26200，NTFS）

`$PY` 是 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`（Python 3.13，wxPython 4.2.5 msw）。`$SP` 是本 session 的 scratchpad。本規格依據的原型在 `$SP\f6\`（`probe.py`、`today.py`、`proto.py`、`drive2.py`、`sizes.py`；不 commit），只對 `%TEMP%` 中的 scratch 複本執行。

基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 1307 tests`、`FAILED (errors=1, skipped=7)`。唯一的 error 是 F-W6（`test_case_only_rename_still_renames`）。原始碼 msgid：357 個（`dotexpress.po` 含標頭共 358 行 `msgid`）。

### 讀取字典檔的地方

| 讀取者 | 使用者 | 遇到壞檔時 |
| --- | --- | --- |
| `load_dictionary_rows` / `load_dictionary_entries`（`client/dictionaries/entries.py:68-109`，tab）：`open(encoding="utf-8-sig", newline="")`、`csv.DictReader`、讀每一列 | 字典管理的條目數量欄（`dialog.py:578-582`）、字典條目編輯器（`DictionaryEntryListModel.load`，`entry_list_model.py:66-68`） | 拋出例外 |
| `validate_dictionary_csv`（`client/dictionaries/manager.py:41-47`，4 個空白）：同樣的 `open`，**只讀表頭** | 匯入（`import_dictionary`，`manager.py:62-72`） | 只有第一個解碼區塊中的內容會引發例外 |
| `LoadedDictionaryRules.from_paths`（`client/conversion/text/dictionary_rules.py:136-200`） | 轉譯，在 worker 執行緒上 | 拋出例外；被包成 `ConversionStageError("translation", ...)` 攔下 |

`DictionaryManagementDialog.__init__`（`dialog.py:503-520`）呼叫 `refresh_dictionaries`，它先設定 `self._dictionary_names`，再呼叫 `_load_dictionary_counts`，後者是對每個名稱的 dict comprehension。只要有一個例外，建構子就結束。`on_open_dictionary_management`（`gui.py:995-1006`）沒有攔截。packaged build 以 `--noconsole` 建置（`client/DotExpress.spec:36`），沒有設定 `sys.excepthook`，而 wxPython 會把事件處理器的例外印到 `sys.stderr`，在 packaged build 中它是 `None`。所以畫面上什麼都沒有，log 也沒有記錄。

### 量測（`probe.py`、`today.py`）

Windows 上的 Python 3.13：

| 檔案 | `load_dictionary_entries` | `validate_dictionary_csv`（匯入） | 目前的轉譯訊息（zh-TW） |
| --- | --- | --- | --- |
| Big5，第 2 列有中文 | `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte` | 同樣的 `UnicodeDecodeError` | `轉譯失敗：'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte` |
| Big5，前 16 KiB 是 ASCII 列，之後才有中文 | `UnicodeDecodeError`（在後面某個區塊的位置 325） | **通過**；匯入會複製檔案 | 同類 |
| 有 BOM 的 UTF-16 | `UnicodeDecodeError`（byte 0xff，位置 0） | 相同 | 同類 |
| 欄位長度超過 131,072 字元（實務上是超過 128 KiB 的檔案中有一個沒關閉的 `"`） | `_csv.Error: field larger than field limit (131072)` | 通過（只讀表頭） | `轉譯失敗：field larger than field limit (131072)` |
| 欄位中有 NUL；小檔案中有未結束的引號；零散的引號 | 可以載入（Python 3.11 起不再拋出例外） | 通過 | 規則可載入 |
| 空檔案；表頭沒有 `text`/`braille`/`type` | 0 筆 | `ValueError`（表頭訊息） | `轉譯失敗：CSV must contain header row.` / `...columns: text, braille, type` |
| 被其他程序以 share none 開著 | `PermissionError [Errno 13]`，**`winerror` 為 None** | 相同 | - |
| 被以 share read 或 read+write 開著 | 可以載入 | - | - |
| ACL 拒絕讀取（`icacls /deny %USERNAME%:(R)`） | `PermissionError [Errno 13]`，`winerror` 為 None | 相同 | `轉譯失敗：[Errno 13] Permission denied: '...'` |

`open()` 經過 C runtime，它把 `ERROR_SHARING_VIOLATION`（32）與 `ERROR_ACCESS_DENIED`（5）都對應到 `EACCES`，而且不設定 `winerror`。**以讀取方式開啟時，無法分辨「檔案被使用中」和「沒有讀取權限」。**（重新命名與刪除走 Win32，會分別回報 `[WinError 32]` 與 `[WinError 5]`。）

對這些檔案的其他操作（目前的程式碼，不需要修改）：

| 操作 | Big5 | 以 share none 開著 | ACL 拒絕讀取 |
| --- | --- | --- | --- |
| 重新命名（`Path.rename`） | 可以 | `[WinError 32]` -> `儲存字典失敗：...` | `[WinError 5]` -> `儲存字典失敗：...` |
| 刪除（`unlink`） | 可以 | `[WinError 32]` -> `無法刪除字典：...` | 可以 |
| 匯出（`shutil.copyfile`） | 可以，位元組相同 | `[Errno 13]` -> `匯出字典失敗：...` | `[Errno 13]` -> `匯出字典失敗：...` |

### 交接文件要求查清的事項（第 5.1 節）

- **(a) 選了讀不到的字典時轉譯**，不是靜默失敗。worker 會攔下錯誤（`conversion/output.py:66-80`），由 `ConversionPresenter._on_job_failure` 顯示錯誤訊息框：`轉譯失敗：'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte`（Big5），或 `轉譯失敗：[Errno 13] Permission denied: '<完整路徑>'`（被拒或被鎖）。內容是原始的 Python 錯誤文字。只有當文字含有一般文字段落時才會讀字典；只有數學的文字轉譯時不會讀。
- **(b) 匯入 Big5 字典。** 會先出現名稱對話框。接著：
  - 前 8 KiB 內有中文（常見情況）：`UnicodeDecodeError` 是 `ValueError`，所以 `DictionaryManagementPresenter.import_from_file` 顯示 `匯入的檔案必須包含 text、braille 與 type 表頭。`，這是錯的。檔案不會被複製。
  - 前 8 KiB 全是 ASCII：表頭檢查通過，檔案被複製。接著對話框的重新整理在按鈕的事件處理器中拋出例外（`today.py`）：`_dictionary_names` 已經有新名稱，但 virtual list 仍是舊的項目數和舊的筆數，所以清單是錯的：在 `today.py` 中顯示 `alpha` / `1` 和 `big5` / `0`，`default` 被截掉。畫面上沒有任何訊息。下次開字典管理就沒反應。
  - 若表頭那一行就超過 CSV 欄位長度上限，會拋出 `csv.Error`，presenter 沒有攔截（理論上）。
- **(c) 刪除、重新命名、匯出。** 目前都用不到，因為對話框打不開。若檔案是在對話框開著時才變壞，它們的行為如上表，而且之後每次成功的重新命名、刪除、新增或匯入，都會像 (b) 一樣把清單弄壞。按「編輯」會關閉對話框，接著 `DictionaryEntriesDialog` 在建構子中拋出例外：什麼都沒開，也沒有訊息。F-6 之後，刪除、重新命名、匯出維持目前的行為（D7）；之後的重新整理不再失敗（D2）；「編輯」會說明問題（D5）。
- **洩漏（次要）。** 拋出例外的建構子會留下一個隱藏、從未銷毀的 `wx.Dialog`（`today.py`：`wx.GetTopLevelWindows()` 仍列出 `字典管理`）。它是主視窗的子視窗，會跟著主視窗一起銷毀。

### 無障礙量測（`proto.py`、`drive2.py`、`sizes.py`；wx 4.2.5 msw）

- 有 `wx.TE_READONLY`、**沒有** `wx.TE_MULTILINE` 的 `wx.TextCtrl` 會被 Tab 跳過。wxMSW 的 `wxTextCtrl::AcceptsFocusFromKeyboard` 不讓唯讀的單行控制項從鍵盤取得焦點。用 `wx.TE_MULTILINE | wx.TE_READONLY` 時，它是清單之後的下一個 Tab 停留點。
- 緊接在文字控制項之前建立的 `wx.StaticText` 會成為它的無障礙名稱。UIA 回報該 Edit 為 `name='無法讀取的原因：'`，值是原因文字。
- 隱藏的控制項不在 UIA 樹中，也不在 Tab 順序中。
- 原型中 57 字元的原因在對話框寬度下換成 2 行（`EM_GETLINECOUNT` = 2）。`ChangeValue` 再 `SelectAll()` 之後，透過 UIA `SetFocus` 取得焦點時，選取範圍 `EM_GETSEL` = `(0, 57)` 仍保留。NVDA 的行為（已知的 NVDA 行為，本文沒有量測；由第 52 項確認）：編輯框取得焦點時若沒有選取文字，NVDA 讀插入點所在的那一行，也就是換行後的第一行；若有選取文字，則讀出選取的內容。
- 對話框高度（`sizes.py`，wx 邏輯像素；螢幕縮放 125 %）：若在 `SetSizerAndFit` 之前就隱藏這一列，對話框維持目前大小，顯示這一列時清單會少掉這一列的高度（預設兩行高的欄位時，154 -> 88 px）。若 fit 時這一列是顯示的，則改為對話框變高同樣的量。

## 決策

**D1. 由一個 helper 模組分類並描述讀取錯誤：`client/dictionaries/read_problems.py`（新檔，tab，不 import wx）。**

```python
class DictionaryReadProblem(Enum):
	NOT_UTF8 = "not_utf8"        # UnicodeDecodeError
	CANNOT_OPEN = "cannot_open"  # PermissionError: in use, or no permission (not distinguishable)
	INVALID_CSV = "invalid_csv"  # csv.Error
	OTHER = "other"              # anything else, including other OSErrors

def classify_dictionary_read_error(error: Exception) -> DictionaryReadProblem
def describe_dictionary_read_error(error: Exception) -> str            # the reason, translated at call time
def describe_unreadable_dictionary(name: str, error: Exception) -> str # headline + "\n\n" + reason
def log_dictionary_read_error(path: Path, error: Exception) -> None    # D8

@dataclass(frozen=True)
class DictionaryCount:
	entries: int = 0
	error: Exception | None = None   # None: readable

def read_dictionary_count(path: Path) -> DictionaryCount
```

- 分類順序：`UnicodeDecodeError` 最先（它是 `ValueError`），然後 `PermissionError`，然後 `csv.Error`，其餘為 `OTHER`。
- `read_dictionary_count` 回傳 `DictionaryCount(len(load_dictionary_entries(path)))`。遇到任何 `Exception` 時呼叫 `log_dictionary_read_error(path, error)`，並回傳 `DictionaryCount(error=error)`。它計算的正是編輯器顯示的列，與 F-4 之後相同。
- `CANNOT_OPEN` 只有一個合併的原因，因為兩種情況無法分辨（見現況）。用 `CreateFileW` 逐一判斷原因，只會為一個已經同時提到兩種原因的訊息，多出 Windows 專用的程式碼。
- 原因文字從不提 Big5。其他任何編碼的檔案都得到同樣的建議（U2）。

**D2. 條目數量欄（U1）。** `DictionaryManagementDialog` 保留 `_dictionary_counts: dict[str, int]` 記錄讀得到的字典，並新增 `_dictionary_read_errors: dict[str, Exception]`。`_load_dictionary_counts` 透過 `read_dictionary_count` 填入兩者，不會因為任何檔案而拋出例外。`_get_item_text(item, 1)` 對 `_dictionary_read_errors` 中的名稱回傳 `_("Unreadable")`，其餘照舊回傳數量。筆數在這些時候讀取：對話框開啟時、在對話框內每次成功新增、刪除、重新命名或匯入之後（`refresh_dictionaries`，呼叫處不變），以及按「編輯」時讀取選取的那一份（D5）。不會輪詢。`_resize_columns` 以 `_("Entries")` 與 `_("Unreadable")` 中較寬者決定數量欄的寬度；兩者在 zh-TW 都是四個字，所以出貨語言中沒有變化。

**D3. 原因列（U1「選取後再說明原因」）。** `_build_ui` 在清單之後、動作按鈕之前建立（建立順序就是 Tab 順序，也決定無障礙名稱）：

```python
self.read_problem_label = wx.StaticText(self, label=_("Why this dictionary cannot be read:"))
self.read_problem_ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, <about three text lines>))
```

兩者加入主 sizer、位於清單下方（標籤用 `LEFT | RIGHT`，欄位用 `EXPAND | LEFT | RIGHT | BOTTOM`，邊距 12），並在 `finalize_dialog_layout` 之前隱藏，所以對話框維持目前的大小。`_update_read_problem()` 在 `refresh_dictionaries` 結尾和 `_on_selection_changed` 中執行：

- 若選取的字典（`_get_selected_name()`）有讀取錯誤：`read_problem_ctrl.ChangeValue(describe_dictionary_read_error(error))`，接著 `SelectAll()`，顯示標籤與欄位，再 `Layout()`。
- 否則：`ChangeValue("")`，隱藏兩者，再 `Layout()`。

理由與無障礙：

- **NVDA 的路徑。** 選取該列時，NVDA 讀出清單項目和它的數量欄，內容是 `無法讀取`。按一次 Tab 到達欄位，NVDA 讀出標籤 `無法讀取的原因：`、角色（編輯、多行、唯讀），而且因為文字已選取，會讀出完整的原因，不只是換行後的第一行。Shift+Tab 回到清單。欄位唯讀，不接受輸入。`ChangeValue` 不會送出文字事件。
- **所有字典都讀得到時，什麼都不變。** 這一列是隱藏的，不在 Tab 順序和 UIA 樹中，也不占空間。對話框大小和目前相同。
- **選取時不自動朗讀。** wxPython 沒有 live region 或 UIA notification 的呼叫方式。選取時數量欄已經說 `無法讀取`，按「編輯」也會用訊息框說明（D5）。用 ctypes 送 UIA notification，會為一個只差一個按鍵的提示加入新的平台程式碼。
- 不採用：
  - 唯讀的單行欄位：Tab 會跳過它（已量測）。
  - `StaticText`：無法取得焦點，NVDA 使用者必須用物件導覽才讀得到。
  - 狀態列：這個對話框沒有狀態列。
  - 永遠顯示的一列：每個使用者都多一個空白的 Tab 停留點。
  - 選取時跳出訊息框：會打斷使用者用方向鍵瀏覽清單。

**D4. 字串與用詞。** 見「使用者可見字串」。原因都是完整的句子，所以在欄位中、在「編輯」的訊息框中，以及匯入時接在 `匯入字典失敗：` 之後，讀起來都一樣。`INVALID_CSV` 與 `OTHER` 會附上 Python 的錯誤文字，做法和既有的 `Failed to ...: {error}` 訊息相同（F-3 D6）。

**D5. 對讀不到的字典按「編輯」時留在對話框。** `_on_edit`：

1. 沒有選取：直接返回（不變）。
2. 用 `read_dictionary_count` 重新讀取選取的字典，結果存回兩個 dict。重新整理清單並呼叫 `_update_read_problem()`。
3. 若有錯誤：`self.show_error(describe_unreadable_dictionary(name, error))`（既有的 view 方法：`wx.MessageBox(..., _("Error"), wx.OK | wx.ICON_ERROR)`）後返回。對話框保持開啟，選取不變，`edit_dictionary_name` 仍為 `None`。
4. 否則：與目前相同，`edit_dictionary_name = name; EndModal(wx.ID_EDIT)`。

因為會重新讀取，使用者在對話框開著時把檔案重新存成 CSV UTF-8（或關掉佔用的程式），下次按「編輯」就能開啟，筆數也會更新。讀不到的字典，「編輯」按鈕仍然啟用（`get_action_availability` 不變）。若把它停用，鍵盤使用者就聽不到說明。

**D6. 編輯器仍可能讀不到檔案（競態），所以 `on_open_dictionary_management` 保護編輯器的建立。** 若檔案在 D5 的檢查和 `DictionaryEntriesDialog` 建構子之間變壞，建構子會拋出例外。事件處理器攔下 `Exception`，呼叫 `log_dictionary_read_error(dictionary_path, error)`，並顯示 `wx.MessageBox(describe_unreadable_dictionary(edit_name, error), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)`。這時字典管理對話框已經關閉（與目前相同），使用者可以再開一次。編輯器的建構順序不變：建到一半的隱藏對話框仍是主視窗的子視窗（見現況「洩漏」）。這個保護在 `gui.py` 多了一處 `wx.MessageBox` 呼叫，F-7 計數時必須包含它。

**D7. 讀不到的字典，刪除、重新命名、匯出不變。** 它們仍然啟用，沿用 presenter 既有的程式碼與訊息（見現況的表格）。它們是使用者的出路：匯出會原封不動地複製位元組，可以在別處用 Excel 修好再匯入；刪除可以移除壞掉的那份。每次操作之後，`refresh_dictionaries` 不再失敗（D2），所以清單和原因列都正確。預設字典仍然不能刪除或重新命名。若 `default.csv` 本身讀不到，使用者要直接修正該檔，原因文字會說明做法。

**D8. 記錄 log。** D1、D5、D6 中每次讀取失敗，都以 `ERROR` 寫到既有的 `dotexpress.gui` logger（`get_logger("dotexpress.gui", "gui.log")`，F-3 與 F-5 已用來記錄 UI 錯誤的檔案）：

- `UnicodeDecodeError`、`csv.Error` 或任何 `OSError`：一行，不附 traceback：`Cannot read dictionary "%s": %s: %s`，依序是 `path.name`、例外型別名稱和錯誤文字。這些失敗是預期中的，來自使用者的資料，訊息已經完整描述。
- 其他任何例外：`Unexpected error while reading dictionary "%s"`，附 `exc_info=error`（traceback），與 F-3 M-3 對非 `OSError` 存檔錯誤的做法相同。

在 packaged build 中，log 位於 `<DotExpress.exe 所在資料夾>\log\gui.log`（frozen 時 `app_paths.get_application_root` 回傳執行檔所在資料夾；`log.get_logger` 在第一筆記錄時才建立檔案）。UI 不指向它，也不需要新字串。log 文字不翻譯。一直讀不到的字典，每次重新整理、每次按「編輯」都會再記一次；每次使用對話框只有幾行（見風險）。

**D9. 匯入會先讀完整個檔案再複製。** `validate_dictionary_csv`（`manager.py`，4 個空白）讀表頭，照舊檢查（缺欄位時仍拋出同樣的 `ValueError`），然後在同一個 `with` 區塊中讀過每一列。它讀檔的方式與 `load_dictionary_rows` 完全相同（相同的 `open` 參數、相同的 `DictReader`），所以匯入接受的檔案，也一定能計算筆數和編輯。`DictionaryManagementPresenter.import_from_file` 在 `except ValueError` **之前**加入（因為 `UnicodeDecodeError` 是 `ValueError`）：

```python
except (UnicodeDecodeError, csv.Error) as exc:
	view.show_error(_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc)))
	return None
```

表頭錯誤、不合法的名稱和 `OSError`（包括來源檔被使用中或被拒）維持目前的訊息。驗證失敗時不複製任何檔案，與目前相同。匯入不寫 log：使用者已經看到原因，也沒有任何東西被改動。

**D10. 轉譯不變。** 選了讀不到的字典時，轉譯照舊顯示 `轉譯失敗：<Python 錯誤>`（發現 a）。更友善的轉譯訊息列為後續（待決問題 O5）。

**D11. 翻譯檔。** 七個新 msgid：`dialog.py`（2）、`dictionaries/read_problems.py`（5）。用 `scripts\generate-pot.bat` 重新產生，把 `POT-Creation-Date` 固定為 `2026-10-10 12:00+0800`，執行 `msgmerge --update --backup=none locales\zh_TW\LC_MESSAGES\dotexpress.po locales\dotexpress.pot`，填入 msgstr，並移除 `msgmerge` 加上的 `fuzzy` 旗標。`msgmerge` 可能把 `Dictionary "{name}" cannot be read.` 誤配到 `Dictionary "{name}" already exists.`，把 `The file cannot be read: {error}` 誤配到其他 `...: {error}` 項目；每個新項目都要檢查。用 `msgfmt --check -o locales\zh_TW\LC_MESSAGES\dotexpress.mo locales\zh_TW\LC_MESSAGES\dotexpress.po` 建置。`msgfmt --check --statistics` 必須回報 364 個已翻譯、0 個 fuzzy、0 個未翻譯。本機已安裝 `msgfmt` 0.23。若沒有，改用腳本建置 `.mo`，但要先證明它對目前的 `.po` 產生逐位元組相同的結果（AGENTS.md）。

## 各路徑的行為，修改前後

| 路徑 | 修改前 | 修改後 |
| --- | --- | --- |
| 開啟字典管理，所有檔案都讀得到 | 對話框，顯示筆數 | 相同；原因列隱藏 |
| 開啟字典管理，有一個檔案讀不到（任何原因） | 沒反應（F-W12） | 對話框開啟；該列顯示 `無法讀取`；其他列顯示筆數；每個讀不到的檔案在 `gui.log` 記一行 |
| 選取讀不到的字典 | - | 清單下方出現原因列，顯示原因並已選取文字；Tab 可到達 |
| 選取讀得到的字典 | - | 原因列隱藏 |
| 編輯，讀不到的字典 | -（對話框打不開；若檔案在開著時才變壞：對話框關閉，什麼都沒開，沒有訊息） | 錯誤訊息框 `無法讀取字典「name」。` + 原因；對話框保持開啟；寫入 log |
| 編輯，對話框開著時檔案已修好 | - | 筆數更新；開啟編輯器 |
| 編輯，檔案在檢查和開啟編輯器之間變壞 | 沒有訊息 | 主視窗顯示錯誤訊息框（D6）；寫入 log |
| 刪除／重新命名／匯出讀不到的字典 | 用不到（或之後清單壞掉） | 既有行為與訊息；之後清單正確 |
| 有其他檔案讀不到時新增／匯入／重新命名／刪除 | 清單壞掉，沒有訊息 | 清單正確；那個檔案仍顯示 `無法讀取` |
| 匯入 Big5（前 8 KiB 內有中文） | `匯入的檔案必須包含 text、braille 與 type 表頭。` | `匯入字典失敗：檔案不是以 UTF-8 儲存。...`；不複製 |
| 匯入 Big5（前 8 KiB 全是 ASCII） | 被複製；清單壞掉；之後對話框打不開 | 以同樣的訊息拒絕；不複製 |
| 匯入有欄位超過 CSV 上限的檔案 | 被複製（表頭通過） | `匯入字典失敗：檔案不是有效的 CSV 檔案。...`；不複製 |
| 匯入缺少必要表頭的檔案；名稱不合法；來源被使用中或不存在 | 既有訊息 | 相同 |
| 選了讀不到的字典時轉譯 | `轉譯失敗：<Python 錯誤>` | 相同 |
| 空白或沒有表頭的字典 | 筆數 0；轉譯以表頭訊息失敗 | 相同 |

## 各檔案的設計

### `client/dictionaries/read_problems.py`（新檔，tab）

D1、D8。模組 docstring："Why a dictionary file cannot be read, in words the user can act on (F-6). Nothing here imports wx."。模組層級 `logger = get_logger("dotexpress.gui", "gui.log")`。

### `client/dialog.py`（tab）

- import `read_dictionary_count`、`describe_dictionary_read_error`、`describe_unreadable_dictionary`；若 `load_dictionary_entries` 不再有其他用途，就不再在此 import。
- `DictionaryManagementDialog.__init__`：`self._dictionary_read_errors: dict[str, Exception] = {}`。
- `_build_ui`：原因列（D3），在 `finalize_dialog_layout` 之前隱藏。
- `_get_item_text`、`_load_dictionary_counts`（D2）、`_store_count(name, count)`、`_update_read_problem()`（D3），`refresh_dictionaries` 與 `_on_selection_changed` 呼叫它，`_resize_columns`（D2）、`_on_edit`（D5）。
- 不修改：`DictionaryEntriesDialog`、`localize_standard_buttons`、view 方法（沿用 `show_error`）。

### `client/gui.py`（tab）

`on_open_dictionary_management`：D6 的編輯器保護。import `describe_unreadable_dictionary`、`log_dictionary_read_error`。

### `client/dictionaries/manager.py`（4 個空白）

`validate_dictionary_csv` 讀過每一列（D9）。Docstring："Raise ValueError if a header is missing; reading every row raises what reading the dictionary later would (UnicodeDecodeError, csv.Error, OSError)."

### `client/dictionaries/presenter.py`（tab）

`import_from_file`：D9 的 `except (UnicodeDecodeError, csv.Error)` 分支，放在 `except ValueError` 之前。

### `client/locales/`

`dotexpress.pot`、`zh_TW/LC_MESSAGES/dotexpress.po`、`zh_TW/LC_MESSAGES/dotexpress.mo`（D11）。

### 測試與 stub

只有當 `speech_dialog_stubs` 缺少新對話框程式碼需要的東西時，才修改 `client/tests/wx_stub.py`（`TE_MULTILINE`、`TE_READONLY`、`StaticText`、`TextCtrl` 由 `AutoSubmoduleModule` 自動產生；由 plan 確認）。新增 `client/tests/test_dictionary_read_problems.py`（tab，與其他字典測試相同）。

### 不修改

`dictionaries/entries.py`、`dictionaries/entry_list_model.py`、`dictionaries/actions.py`、`dictionaries/name_prompt.py`、`conversion/`（D10）、`ui/conversion_presenter.py`、`settings/`、字典檔格式、`client/dictionary/`、`client/braille/`。

## 保持不變的部分

- 每個字典檔的位元組：F-6 只讀取，不轉換、不修復、不改寫任何檔案（U2）。
- 讀得到的字典的筆數（編輯器顯示的列，F-4）。
- 所有字典都讀得到時，按鈕的啟用狀態、按鈕順序、對話框大小與 Tab 順序。
- 每個既有的訊息與標題，以及匯入時缺少表頭、名稱不合法、`OSError` 的訊息。
- 轉譯、字典條目編輯器，以及刪除、重新命名、匯出。
- 兩個 fixture 的 sha256（`translation_golden.json` `e67d95a1...`、`dictionary_entries_trace.json` `f493da52...`）。

## 使用者可見字串

新 msgid（357 -> 364）：

| msgid | msgstr（zh_TW） | 位置 |
| --- | --- | --- |
| `Unreadable` | `無法讀取` | 條目數量欄（`dialog.py`） |
| `Why this dictionary cannot be read:` | `無法讀取的原因：` | 原因欄位的標籤（`dialog.py`） |
| `Dictionary "{name}" cannot be read.` | `無法讀取字典「{name}」。` | 「編輯」錯誤訊息框的第一句（`read_problems.py`） |
| `The file is not saved as UTF-8. Save it again in the "CSV UTF-8 (Comma delimited)" format, for example with Save As in Excel.` | `檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。` | 原因 `NOT_UTF8` |
| `The file cannot be opened. It may be in use by another program, or you may not have permission to read it. Close the other program and try again.` | `無法開啟檔案。檔案可能正被其他程式使用，或您沒有讀取權限。請關閉其他程式後再試一次。` | 原因 `CANNOT_OPEN` |
| `The file is not a valid CSV file. Check for a quotation mark that is not closed. Details: {error}` | `檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：{error}` | 原因 `INVALID_CSV` |
| `The file cannot be read: {error}` | `無法讀取檔案：{error}` | 原因 `OTHER` |

沿用：`Error`（`錯誤`）作為兩個錯誤訊息框的標題；匯入時用 `Failed to import dictionary: {error}`（`匯入字典失敗：{error}`）。`CSV UTF-8` 與 `Excel` 在 zh-TW 中保持原樣（是 Excel 顯示的產品與格式名稱）。`NOT_UTF8` 原因中的格式名稱是 Excel「另存新檔」對話框中列出的名稱：英文版 Excel 是 `CSV UTF-8 (Comma delimited)`，繁體中文版是 `CSV UTF-8 (逗號分隔)`。含 `{error}` 的訊息會由 `xgettext` 加上 `#, python-brace-format`。

「編輯」訊息框在 zh-TW 中的內容：

```
無法讀取字典「big5」。

檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。
```

## 測試計畫

TDD：每個步驟先寫新測試，並因所述原因失敗，再由程式碼讓它們通過。測試檔沿用各自的縮排：`test_dictionary_management_dialog.py`、`test_dictionary_presenter.py` 與新檔用 tab；`test_dictionary_manager.py`、`test_gui_document_flows.py` 與 `test_i18n.py` 用 4 個空白。

**一定要隔離 log。** `read_problems` 被 import 時，會綁定一個寫到 `client/log/gui.log` 的 `FileHandler`。每個可能讓它寫 log 的測試模組，都必須在 `setUpModule` 中呼叫 `unittest.addModuleCleanup(isolate_file_logs("dotexpress.gui"))`，做法同 `test_gui_document_flows.py`。這適用於新的 read-problems 測試和 `test_dictionary_management_dialog.py`；`test_gui_document_flows.py` 已經有。log 斷言用 `self.assertLogs("dotexpress.gui", level="ERROR")`，並檢查 `record.exc_info`。

測試資料在暫存目錄中建立：Big5 用 `"...".encode("cp950")`；晚出現 Big5 的檔案（約 16 KiB 的 ASCII 列，然後一列中文）；欄位超長的檔案（`"x" * 140000`）；UTF-16。`PermissionError` 用 `patch.object(read_problems, "load_dictionary_entries", side_effect=PermissionError(13, "Permission denied"))` 注入。只在 Windows 執行的測試使用 `windows_file_handles.hold_open(self, path, 0)`（share none）。測試絕不碰 `client/dictionary/`、`client/workspace/`、`client/config.json` 或 `client/log/`。

### R. 讀取問題（`client/tests/test_dictionary_read_problems.py`，新檔）

1. `test_classifies_each_error`（subTest）：真實的 Big5 `UnicodeDecodeError` -> `NOT_UTF8`；`PermissionError` -> `CANNOT_OPEN`；`csv.Error` -> `INVALID_CSV`；`FileNotFoundError`、`OSError(22, ...)`、`RuntimeError` -> `OTHER`。
2. `test_describes_each_problem`：文字等於 `read_problems._(<msgid>)`，msgid 含 `{error}` 時再以 `error` 格式化。透過模組自己的 `_` 比對，讓測試在翻譯步驟前後都成立。
3. `test_unreadable_dictionary_message_has_headline_and_reason`。
4. `test_count_of_readable_and_missing_files`（subTest：UTF-8、有 BOM 的 UTF-8、F-4 的 `DICT_BADBOPO` 算 1 筆、不存在的檔案算 0 筆）：沒有錯誤，`assertNoLogs`。
5. `test_count_of_unreadable_file_returns_the_error_and_logs_one_line`（subTest：Big5、晚出現的 Big5、UTF-16、欄位超長、注入的 `PermissionError`）：`entries == 0`、錯誤型別正確、一筆指名該檔的 `ERROR` 記錄、`exc_info` 為 `None`。
6. `test_unexpected_error_is_logged_with_traceback`：`RuntimeError("injected")` -> 記錄帶 `exc_info`。
7. 只在 Windows：`test_file_held_open_without_sharing_cannot_be_opened`：`hold_open(..., 0)` -> `CANNOT_OPEN`。
8. `test_module_does_not_import_wx`。

### M. 字典管理對話框（`client/tests/test_dictionary_management_dialog.py`）

`_make_dialog` 加上 `_dictionary_read_errors = {}`、假的 `read_problem_label` 與 `read_problem_ctrl` 物件（記錄 `Show`、`ChangeValue`、`SelectAll`）、`Layout = Mock()` 與 `show_error = Mock()`。

1. `test_unreadable_dictionary_shows_unreadable_and_the_others_their_counts`。紅燈：`UnicodeDecodeError`。
2. `test_refresh_after_an_action_keeps_names_counts_and_item_count_consistent`：`_on_import_clicked` 之後出現晚出現 Big5 的檔案。紅燈。
3. `test_each_unreadable_dictionary_is_logged`。
4. `test_selecting_an_unreadable_dictionary_shows_the_reason`：`ChangeValue(reason)`、`SelectAll`、兩者顯示、`Layout`。
5. `test_selecting_a_readable_dictionary_hides_the_reason`：值為空、兩者隱藏。
6. `test_refresh_shows_the_reason_for_the_preferred_selection`。
7. `test_edit_on_an_unreadable_dictionary_shows_the_error_and_stays_open`：`show_error(describe_unreadable_dictionary(...))`、沒有 `EndModal`、`edit_dictionary_name` 仍為 `None`。
8. `test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count`。
9. `test_edit_on_a_dictionary_that_became_unreadable_stays_open`：重新整理時讀得到，按「編輯」前寫入 Big5。
10. `test_unreadable_dictionaries_keep_delete_rename_and_export_enabled`（非預設名稱；預設字典的刪除與重新命名仍停用）。
11. `test_count_column_fits_the_unreadable_label`。
12. 只在 Windows：`test_dictionary_held_open_without_sharing_is_unreadable_with_the_cannot_open_reason`。

不修改、仍通過：檔案中所有既有測試，包括 `test_only_explicit_edit_handler_sets_edit_result`（檔案不存在：讀得到，0 筆）。

### P. 匯入（`test_dictionary_manager.py`、`test_dictionary_presenter.py`）

1. Manager：`test_validate_reads_every_row`（subTest：晚出現的 Big5 -> `UnicodeDecodeError`；欄位超長 -> `csv.Error`）。紅燈：目前會通過。`test_import_dictionary_refuses_a_late_big5_file_and_copies_nothing`。紅燈：目前會被複製。
2. Presenter：`test_import_big5_shows_the_not_utf8_reason`（預期 `("error", _("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(<該錯誤>)))`；不複製）。紅燈：目前是表頭訊息。`test_import_late_big5_is_refused`。紅燈：目前會匯入。`test_import_invalid_csv_shows_the_reason`。紅燈：目前會匯入。
3. 不修改、仍通過：`test_import_without_headers_shows_header_error`、`test_import_invalid_name_shows_header_error`、`test_import_missing_source_shows_import_error` 及其他。

### G. 主視窗（`client/tests/test_gui_document_flows.py`，類別 `DictionaryManagementFrameTest`）

1. `test_editor_that_cannot_read_its_dictionary_shows_the_reason`：`editor_class.side_effect = <Big5 UnicodeDecodeError>`；事件處理器正常返回；一次 `MessageBox(describe_unreadable_dictionary("alpha", error), _("Error"), OK | ICON_ERROR, parent=frame)`；一行不帶 `exc_info` 的 log。紅燈：例外往外拋。
2. `test_editor_failure_that_is_unexpected_is_logged_with_its_traceback`：`RuntimeError`。

### I. 翻譯檔（`client/tests/test_i18n.py`）

1. `test_unreadable_dictionary_strings_are_translated`：`i18n.load_translation()` 把七個 msgid 對應到上面的 zh-TW 文字。

### 數量

新測試：R 8、M 12、P 5（manager 2、presenter 3）、G 2、I 1，共 28 個（3 個只在 Windows 執行的測試在 POSIX 上跳過）。Windows 上預期：`Ran 1335`、`FAILED (errors=1, skipped=7)`，只有 F-W6。plan 可以調整數量與 subTest 的切法；紅燈／綠燈的意圖必須遵守。

## 遷移步驟（每步一個綠燈 commit，先紅燈）

1. `fix: open Dictionary Management when a dictionary cannot be read (F-6)`：D1、D2、D8。R 1-8 與 M 1-3、10、11、12。從這一步起，原因文字已作為英文 msgid 存在。
2. `fix: explain why a dictionary cannot be read (F-6)`：D3、D5、D6。M 4-9、G 1-2。
3. `fix: refuse importing a dictionary that cannot be read (F-6)`：D9。P 1-2。
4. `chore: translate the unreadable-dictionary strings (F-6)`：D11、I 1；`.pot`、`.po` 與 `.mo`。

每個 commit 結尾加上 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`，只 stage 明確的路徑。

## 驗收標準

在 Windows 上，從 `client/` 以 `$PY` 執行。

1. 完整測試：除了 F-W6 之外沒有 failure 或 error；`Ran` = 1307 + 新測試數。
2. 重點測試：`$PY -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_gui_document_flows tests.test_i18n tests.test_dictionary_entries -v` 通過；只在 Windows 執行的測試有執行（沒有被跳過）。
3. 翻譯檔：以 `$PY -I` 對 `_`/`N_` 做 AST 掃描，得到 364 個原始碼 msgid；`msgfmt --check --statistics` 回報 364 個已翻譯、0 個 fuzzy、0 個未翻譯；`.mo` 會翻譯七個新 msgid；`scripts\generate-pot.bat` 執行兩次，除了 `POT-Creation-Date` 之外輸出相同。
4. 兩個 fixture 的 sha256 不變。
5. 應用程式資料未被動到：`client/dictionary/`、`client/workspace/`、`client/log/` 下每個檔案與 `client/config.json` 的 sha256，在測試前後相同（spec session 已把起始清單記在 `$SP\f6\userdata-before.txt`）。特別是沒有任何測試寫入 `client/log/gui.log`。
6. `git diff main --stat` 只動到 `client/dictionaries/read_problems.py`、`client/dialog.py`、`client/gui.py`、`client/dictionaries/manager.py`、`client/dictionaries/presenter.py`、三個 locale 檔、上面列出的測試檔（需要時加上 `wx_stub.py`），以及 spec、plan 與 history 檔。
7. 突變檢查（plan）：每個突變至少被一個測試抓到：
   - `_load_dictionary_counts` 沒有逐檔攔截；
   - 讀不到的檔案被算成 `0`；
   - 分類順序把 `ValueError`/`OTHER` 放在 `UnicodeDecodeError` 之前；
   - 沒有 log，或 `UnicodeDecodeError` 帶 traceback；
   - 非預期錯誤沒有 traceback；
   - 選取讀得到的字典時原因列沒有隱藏，或沒有 `SelectAll`；
   - 「編輯」沒有重新讀取；
   - 對讀不到的字典按「編輯」時關閉對話框；
   - 主視窗沒有編輯器保護；
   - `validate_dictionary_csv` 只讀表頭；
   - presenter 的新分支放在 `except ValueError` 之後。
8. 下方的 packaged GUI 驗證，結果放在實作的 history 資料夾。

## Windows 驗證（packaged build）

建置方式同 F-5：把主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面，執行 `scripts\build-dotexpress.bat`。在 `client\build\DotExpress\PYZ-00.toc` 中確認 `dialog.py`、`gui.py` 與 `dictionaries\read_problems.py` 來自要驗證的 checkout。把 `client\dist\DotExpress.exe` 複製到 `D:\dxtest\N-f6\`。每個項目在新的 `D:\dxtest\auto<N>-f6` 資料夾執行；只結束 exe 位於該資料夾下的程序（`dx.kill_under`）。腳本沿用 `docs/superpowers/history/2026-10-09-03-windows-verification/auto/`（`dx.py`、`docs.py`、`dicts.py`）與 `.../2026-10-10-01-f5-save-failure-handling/auto/f5gui.py`，不修改它們。新腳本、helper `f6gui.py` 與 share none 的鎖檔程式 `lockx.py`（`CreateFileW(GENERIC_READ, share 0)`；`lock.py` 只支援 `r` 與 `rw`）放在 `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/`。它們在 pywinauto venv（`$SP\uia`）中執行。測試檔由腳本產生到項目資料夾：`big5.csv`（`text,braille,type` + `臺北,⠞⠺,Braille`，cp950）、`big5_late.csv`（16 KiB 的 ASCII 列，然後一列 cp950）與 `badquote.csv`（UTF-8，第 2 列有一個沒關閉的 `"`，之後有超過 128 KiB 的列）。每個項目前後記錄每個檔案的 sha256。

`f6gui.py` 透過 `dicts.mgr_items` 讀清單各列，並把對話框的 `Edit` 子視窗和它之前的 `Static` 當作原因列讀取。它也透過 UIA 記錄 Edit 是否存在、名稱與值，以及 `EM_GETSEL`。錯誤訊息框用 `f5gui.dismiss` 讀取並關閉（UIA task dialog）。只有在 `set_focus()` 成功後才送按鍵給 DotExpress 視窗；前景被其他程式占走時，重跑該次（HANDOFF 第 2 節）。

| # | 步驟 | F-6 之後的預期 | 之前（N-f5b） |
| --- | --- | --- | --- |
| 42 | 先啟動一次再關閉；把 `big5.csv` 放進 `dictionary\`；啟動；開啟字典管理 | 對話框開啟；列為 `big5` / `無法讀取`、`default` / `0`；沒有原因列（對話框中沒有 `Edit`）；`log\gui.log` 有一行 `[ERROR] Cannot read dictionary "big5.csv": UnicodeDecodeError: 'utf-8' codec can't decode byte ...`，沒有 `Traceback`；`big5.csv` 位元組不變 | 沒反應（F-W12） |
| 43 | 同 42；選取 `big5`；再選取 `default` | `big5`：標籤 `無法讀取的原因：`，有該名稱的 Edit，內容為 `NOT_UTF8` 的 zh-TW 文字，`EM_GETSEL` = 全部文字；`default`：這一列消失 | - |
| 44 | 同 43，選取 `big5`；按「編輯」 | 錯誤訊息框 `錯誤`：`無法讀取字典「big5」。` + 空行 + `NOT_UTF8` 文字；按確定後 `字典管理` 仍開著，沒有 `自訂字典管理器`；log 多一行。接著用腳本把 `big5.csv` 改寫成 UTF-8，再按「編輯」：編輯器開啟，有 `臺北` 這一列；按取消後再開字典管理，筆數為 `1` | - |
| 45 | Tab 順序：選取 `big5`、焦點在清單上時按 Tab，再按 Shift+Tab；選取 `default` 時按 Tab | `big5`：焦點移到原因 Edit，再回到清單；`default`：焦點移到 `新增` | - |
| 46 | `icacls dictionary\big5.csv /deny %USERNAME%:(W)`（F-W12 最初的重現方式，含 SYNCHRONIZE）；開啟；選取；編輯；匯出到 `D:\dxtest\auto46-f6\out.csv`；還原 ACL | 該列 `無法讀取`；原因為 `CANNOT_OPEN` 文字；編輯：顯示該文字的訊息框；匯出：既有的 `匯出字典失敗：[Errno 13] Permission denied: ...`；對話框仍可使用 | 沒反應 |
| 47 | `lockx.py` 以 share none 開著 `dictionary\alpha.csv`（用「新增」建立的可讀字典）；開啟；選取 `alpha`；解除鎖定；按「編輯」 | `alpha` / `無法讀取`，原因 `CANNOT_OPEN`；解除後按「編輯」開啟編輯器（重新讀取） | 沒反應 |
| 48 | 從字典資料夾外匯入 `big5.csv`，名稱 `b1`；匯入 `big5_late.csv`，名稱 `b2` | 兩者：先出現名稱對話框，再出現 `匯入字典失敗：檔案不是以 UTF-8 儲存。...`；`dictionary\` 中沒有 `b1.csv` 或 `b2.csv`；清單不變 | `b1`：`匯入的檔案必須包含 text、braille 與 type 表頭。`；`b2`：被複製、清單錯誤、下次開啟沒反應 |
| 49 | 把 `badquote.csv` 放進 `dictionary\`；開啟；選取它；再把同一個檔案匯入為 `bq2` | 該列 `無法讀取`；原因 `檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：field larger than field limit (131072)`；匯入：`匯入字典失敗：` + 同樣的原因；不複製 | 沒反應／匯入會複製檔案 |
| 50 | 有 `big5.csv` 時：把 `big5` 重新命名為 `big5x`；把 `big5x` 匯出成檔案；刪除 `big5x` | 重新命名：清單顯示 `big5x` / `無法讀取`，已選取，顯示原因列；匯出：輸出位元組與來源相同；刪除：確認後該列消失；沒有錯誤訊息框 | 用不到 |
| 51 | 有 `big5.csv` 時：在設定中選擇 `big5` 字典（`dicts.set_dictionary`）；在輸入框輸入 `臺北`；轉譯 | `轉譯失敗：'utf-8' codec can't decode byte 0xbb ...`（不變，D10） | 相同 |
| 52（手動，使用者） | 使用 NVDA：在有 `big5.csv` 時開啟字典管理；用方向鍵移到 `big5`；Tab；Shift+Tab；按「編輯」 | 記錄 NVDA 讀出的內容。預期：讀出該列與 `無法讀取`；按 Tab 時讀出標籤 `無法讀取的原因`、角色和**完整**的原因；Shift+Tab 回到清單；錯誤訊息框以對話框的方式讀出。若 NVDA 只讀第一行，請回報（D3 的選取做法可能需要調整） | - |

## 與 F-7 的關係

F-7（F-W9、M-7、M-5）會修改 `localize_standard_buttons` 和 `wx.MessageBox` 的呼叫處。F-6 沒有在 `dialog.py` 新增訊息框：「編輯」沿用 `show_error`。F-6 在 `gui.py` 新增一處 `wx.MessageBox` 呼叫（D6），F-7 的 helper 也必須涵蓋它；正式程式碼中 `wx.MessageBox` 的呼叫數變成 20。字典管理的「關閉」按鈕仍經過 `localize_standard_buttons`，不變。

## 風險

- **NVDA 可能只讀出部分原因**（低）。文字已全部選取（以 `EM_GETSEL` 量測），而 NVDA 在取得焦點時會讀出選取的文字。NVDA 實際讀出的內容只由第 52 項確認。即使失敗，「編輯」的訊息框也會讀出完整文字。
- **log 數量**（低）。每次開啟對話框、每次重新整理、每次按「編輯」，每個讀不到的檔案各記一行。使用者偶爾才開對話框；每行很短，也沒有 traceback。
- **匯入會拒絕以前接受的檔案**（低，刻意的）。只拒絕匯入後無法計算筆數或編輯的檔案（同一個讀取方式）。以前的「成功」只留下壞掉的字典和打不開的對話框。
- **匯入會讀兩次檔案**（驗證，然後複製）。字典是小文字檔；兩次讀取之間檔案被改動，是與目前相同的競態。
- **顯示原因列時清單變小**（低）。清單少掉這一列的高度（原型中兩行高的欄位為 66 個邏輯 px，三行時更多）。對話框可以調整大小；所有字典都讀得到時則完全不變。
- **`CANNOT_OPEN` 同時提到兩種可能原因**（低）。不額外呼叫 Win32 就無法分辨（已量測）。文字請使用者兩種處理方式都試試。
- **讀完筆數之後檔案才變壞**（低）。由「編輯」時的重新讀取（D5）或主視窗的保護（D6）攔下。刪除、重新命名、匯出各自回報錯誤。

## 待決問題

沒有會擋住進度的問題。U1 與 U2 由使用者決定，以下各項是在其範圍內補足細節，每一項都是保守的預設。

- **O1. 原因的呈現方式。** 清單下方一個有標籤的多行唯讀欄位，只在選取讀不到的字典時出現，文字已選取；另外在按「編輯」時用訊息框說明。選取時不自動朗讀（D3、D5）。**Decided by orchestrator with the recommended default; user may override before merge.**
- **O2. 「被使用中」與「沒有權限」用同一個訊息**（D1）。**Decided by orchestrator with the recommended default; user may override before merge.**
- **O3. 匯入先讀完整個檔案，以原因文字拒絕非 UTF-8 與無效 CSV 的檔案**（D9）。這改變了一個訊息（前 8 KiB 內有中文的 Big5：表頭訊息改為原因），並拒絕前 8 KiB 全是 ASCII 的 Big5 檔（以前會匯入成壞掉的字典）。替代方案：匯入維持不變，拿掉遷移步驟 3；這樣匯入的檔案之後會顯示為 `無法讀取` 並附原因。**Decided by orchestrator with the recommended default; user may override before merge.**
- **O4. 讀不到的字典，刪除、重新命名、匯出與編輯仍然啟用**（D5、D7）。**Decided by orchestrator with the recommended default; user may override before merge.**
- **O5. 轉譯不變**（D10），仍顯示原始的 Python 錯誤。後續：把來自所選字典的 `UnicodeDecodeError` 或 `PermissionError` 對應到 `Dictionary "{name}" cannot be read.` 與原因。**Decided by orchestrator with the recommended default; user may override before merge.**
- **O6. log**：預期中的錯誤（解碼、CSV、`OSError`）記一行 `ERROR`，其他錯誤附 traceback，寫在 `gui.log`（D8）。**Decided by orchestrator with the recommended default; user may override before merge.**
- **O7. 對話框維持目前大小；顯示原因列時從清單借空間**（D3）。**Decided by orchestrator with the recommended default; user may override before merge.**
- **O8. 空白或沒有表頭的 CSV 檔仍算 0 筆**（讀得到），不變。**Decided by orchestrator with the recommended default; user may override before merge.**

## 範圍外／後續

- O5：讀不到字典時更友善的轉譯錯誤。
- 「開啟字典資料夾」命令，讓使用者能從 app 找到並修正壞掉的 `default.csv`。
- 沒有表頭、空白或引號沒關閉的檔案，載入後列數變少或被合併（O8）。小檔案中沒關閉的引號會讓後面的內容變成一筆很長的條目。
- `on_open_dictionary_management` 仍會讓 `ensure_default_dictionary` 的 `OSError`（字典資料夾無法寫入）靜默地往外拋。
- 建構失敗時留下的隱藏、建到一半的 `DictionaryEntriesDialog`（見現況「洩漏」）。
- 新增的 `wx.MessageBox` 呼叫的 F-W9 問題：F-7。
