# 匯出協調器與轉換 Presenter（P1-4）設計

## 目標

把轉換狀態機與匯出鏈從 `BrailleFrame` 移到兩個不依賴 wx 的模組。本任務是 `storage/refactor.md`（6.2 節）路線圖的 P1-4，涵蓋 3.1 節 S-1 的第 2 點（`ExportCoordinator`）與第 4 點（`ConversionPresenter`），以及 I-3（3.4 節，`ConversionCompletionPolicy`）。另外完成 P0 階段審查指派給本任務的兩項清理：M-9（`_show_file_error` 未使用的 `parent` 參數），以及 `gui` 中殘留未使用的 `ConversionStageError` import（M-3，P1-3 不在範圍內）。

具體來說：

- **`conversion/presenter.py`（新檔，不依賴 wx）。** `ConversionPresenter` 擁有 `ConversionJobRunner`、「converting」對話框的計時器、忙碌狀態的切換、錯誤訊息、手動轉換與匯出轉換的完成處理，以及手動轉換後寫入 dual view 快取（透過 `DocumentController`）。它透過一個小的 `ConversionView` protocol 與 frame 溝通。執行緒相關的依賴（`call_after`、`call_later`、`thread_factory`、`converter`）皆以注入方式提供。
- **`documents/export_coordinator.py`（新檔，不依賴 wx）。** `ExportCoordinator` 負責單一匯出（選擇路徑、修正副檔名、文件為 pending 時先轉換、寫檔、回報）與「全部匯出」鏈（選擇資料夾、檢查衝突、接著每個 UI 回合經由 `call_after` 處理一份文件，最後一個摘要）。它透過 `ExportView` protocol 與 frame 溝通，並經由 presenter 啟動轉換。
- **I-3：完成狀態由 presenter 保存。** 從 `conversion/jobs.py` 刪除 `ConversionCompletionPolicy` 與 `ConversionJobRequest`。runner 接收單純的 `ConversionRequest`，回傳 `ConversionJobSuccess(job_id, conversion_output)` 或 `ConversionJobFailure(job_id, error)`。不再有任何 UI 相關資料進入 worker 執行緒。presenter 以 job id 為鍵保存作用中 job 的完成處理。
- **`BrailleFrame` 只保留 wx 程式碼：** 選單 handler 的「先儲存」防護、對話框、訊息框、忙碌狀態的控制項切換，以及 `ConvertingDialog` 視窗。它以幾個小的 public 方法實作兩個 view protocol。

這是保持行為不變的重構。每個流程的效果順序**包含非同步順序**（點擊當下的 UI 回合、worker、之後每一個 `CallAfter`/`CallLater` 回合各發生什麼）、訊息、標題與圖示、忙碌狀態切換、快取寫入，以及重入行為（包含下方列出的既有缺陷）都不變。沒有任何使用者可見字串改變；不新增也不刪除 msgid；`client/locales/` 下不修改任何檔案。

本規格已納入實作計畫（`docs/superpowers/plans/2026-10-08-p1-4-export-conversion-presenters.md` 的「Spec Corrections and Refinements」一節）的修正與細化：被搬移的 GUI 測試分屬兩個類別，消失的測試行是 27 行（第 4 步 12 行、第 7 步 15 行），不是 22 個；搬移後的全部匯出 registry 測試斷言 `get_format` 被讀取三次；驗收條件 6 以 AST 比對檢查，而不是 `git diff`；驗收條件 10 的固定 seed 打亂執行要與基準已知的順序失敗比對；特性測試案例 9 拆成兩個測試（共 19 個），案例 10 匯出的是未開啟的文件；事件記錄不帶函式名稱；預期字串都經過 `_`；第 4 步暫時的 `_start_export_conversion` 以模組函式 `missing_default_table_message` 檢查點字表；`test_export_conversion_with_default_table_starts_background_conversion` 在第 4 步刪除；每個重構步驟都先有紅燈測試；每個 import 在不再使用它的那一步離開 `gui`；harness 細節；以及「保持不變的部分」中的三項內部行為說明。

## 現況（2026-10-08 於 `refactor/p1-4-export-conversion-presenters` 驗證，HEAD `d6e4663`，已合併 P0-1..P0-6 與 P1-1..P1-3）

基準：`cd client && python -m unittest discover -s tests -p "test_*.py"` 執行 696 個測試，`failures=1`（已知的 P2-5 測試），`skipped=9`。`tests.test_conversion_jobs tests.test_gui_document_flows` 執行 133 個測試，`OK (skipped=2)`。以 AST 掃描 `client/`（排除 tests）中 `_()`/`N_()` 的字串常值，共 353 個 msgid。

縮排：`gui.py`、`conversion/jobs.py` 與 `tests/test_conversion_jobs.py` 使用 tab。`documents/*.py`、`conversion/output.py` 與 `tests/test_gui_document_flows.py` 使用 4 空白。新模組與新測試檔使用 4 空白（AGENTS.md）；修改既有檔案時沿用該檔風格。

### `conversion/jobs.py`（119 行）

- `ConversionCompletionPolicy` 14-19：`on_success`、`on_error`（UI 回呼）、`update_output`、`show_success`（UI 旗標）。`ConversionJobRequest` 22-25 包裝一個 `ConversionRequest` 與一個 policy。`ConversionJobSuccess` 28-32 與 `ConversionJobFailure` 35-39 把 policy 帶回來。worker 從不讀取它（I-3）。
- `ConversionJobRunner` 46-119：`start(request)` 遞增 `_job_id`，建立 `thread_factory(target=_run_job, args=(job_id, request), daemon=True)`，啟動它並回傳 id。`_run_job` 呼叫 `converter(request.conversion_request, runtime=...)`；遇到 `ConversionStageError` 時呼叫 `call_after(_deliver_failure, ...)`，否則 `call_after(_deliver_success, ...)`。其他例外會逸出執行緒，什麼都不會遞送。`_deliver_*`（UI 執行緒）丟棄 `job_id` 不是最新的結果（過期），否則在呼叫 `on_success`/`on_failure` **之前**先設 `_thread = None`，因此在完成處理內 `is_running()` 為 `False`。`is_running()` 為 `_thread is not None and _thread.is_alive()`；`active_job_id` 為最新的 id。
- `convert_text_with_alignment` 把前處理、翻譯、換行與 ASCII 對應中的每個 `Exception` 包成 `ConversionStageError`，stage 為 `text_processing`、`translation` 或 `ascii`（`conversion/output.py` 50-89）。空白來源會回傳 `ConversionOutput("", ())`，但仍在 worker 中執行。

### 轉換狀態機（`gui.py`）

| 部分 | 位置 | 目前行為 |
| --- | --- | --- |
| 接線 | `_initialize_conversion_state` 222-230 | `ConversionJobRunner(runtime=self.translation_runtime, on_success=self._finish_conversion_success, on_failure=self._finish_conversion_failure, call_after=wx.CallAfter)`（真的 `threading.Thread`、真的 converter）；`_convert_dialog = None`；`_convert_dialog_timer = None`。由 `__init__` 在 `_create_main_layout` 之後、`_bind_events` 之前呼叫。 |
| 請求 | `_build_conversion_request` 544-554 | `ConversionRequest(raw_text, output_mode, width, dictionary_path, data_dir=resource_path("data"), translation_tables=self.translation_tables.copy(), lang=get_lang(), charset_maps=get_charset_maps())`。語言與字元集對應每次請求時讀取。 |
| 轉換指令 | `on_convert` 1124-1144（「翻譯 > 轉換」，以及原文編輯器中的 Ctrl+Enter，經 `on_input_text_key_down` 953-957） | 若 `runner.is_running()`：靜默返回。若 `_missing_default_table_message()`（1034-1037；`translation_tables.get("default")` 為假值）不是 `None`：`wx.MessageBox(message, _("Info"), wx.OK \| wx.ICON_INFORMATION, parent=self)` 後返回。否則 `_start_conversion(input_txt.GetValue(), settings.width, settings.output_mode, _get_selected_dictionary_path())`。不會先儲存。 |
| 啟動 | `_start_conversion` 1171-1202 | `_set_conversion_busy(True)`；`_close_converting_dialog()`；建立 policy；`job_id = runner.start(ConversionJobRequest(_build_conversion_request(...), policy))`；`self._convert_dialog_timer = wx.CallLater(2000, self._show_converting_dialog, job_id)`。先前的計時器會被覆蓋，不會被停止。 |
| 忙碌 | `_set_conversion_busy` 1161-1169 | 對 `_("File")` 與 `_("Translation")`：`menu_bar.FindMenu(label)`，找到時 `EnableTop(index, not busy)`。接著 `document_list.Enable(not busy)`、`input_txt.Enable(not busy)`。「說明」選單、點字結果編輯器、frame 的 char hook 與 Dual View 視窗仍可使用。 |
| 轉換中對話框 | `_show_converting_dialog` 1204-1213、`_close_converting_dialog` 1215-1221、`ConvertingDialog` 120-134 | 計時器回呼：`job_id != runner.active_job_id`、`runner.is_running()` 為假，或對話框已存在時返回；否則 `ConvertingDialog(self)`（標題 "Info"、文字 "converting"、沒有關閉鈕、置頂、否決關閉）、`Show()`、`Raise()`。關閉：若有對話框，先清除屬性，再 `Unbind(wx.EVT_CLOSE)`、`Destroy()`。 |
| 完成 | `_complete_conversion` 1223-1274 | 停止並清除計時器；關閉對話框；`_set_conversion_busy(False)`。**錯誤：** 有 `policy.on_error` 就呼叫 `on_error(message)`，否則 `wx.MessageBox(message, _("Error"), wx.OK \| wx.ICON_ERROR, parent=self)`；返回。**成功：** `braille = output.display_text`。若 `update_output`：`output_txt.SetValue(braille)`、`output_txt.SetFocus()`；若有開啟的文件：若它在清單中，以 `Document(name, input_txt.GetValue(), braille)` 取代；接著 `set_dual_view_results(open_name, output.dual_view_segments)`（即使名稱不在清單中）；接著 `_refresh_dual_view()`（沒有開啟文件時也會呼叫）。之後若有 `policy.on_success` 就呼叫 `on_success(braille)`。之後若 `show_success`，`wx.MessageBox(_("Conversion completed."), _("Info"), wx.OK \| wx.ICON_INFORMATION, parent=self)`。`display_text=` 參數只有測試使用。 |
| 成功／失敗轉接 | `_finish_conversion_success` 1276-1277、`_finish_conversion_failure` 1279-1292 | 失敗訊息依 stage 選範本：`"ascii"`：`_("ASCII conversion failed: {error}")`，`"text_processing"`：`_("Text processing failed: {error}")`，其他：`_("Translation failed: {error}")`；`{error}` 為 `_(get_public_error_message(error.error))`（空訊息："An unknown error occurred."；liblouis 的 "Can't translate: tables ... inbuf"："The selected translation table could not translate this text."；其他為 `str(error)`）。 |
| 關閉 | `_on_close` 1146-1159 | 若 `runner.is_running()` 且 `evt.CanVeto()`：`Veto()` 後返回（不儲存）。接著先儲存（失敗時盡可能否決）；`_close_converting_dialog()`；銷毀 Dual View 視窗；`Skip()`。計時器不會被停止。 |

實際只存在兩種 policy 形狀：**手動**（`ConversionCompletionPolicy()`：沒有回呼，`update_output=True`，`show_success=True`）與**匯出**（`on_success` 與 `on_error` 皆有設定，`update_output=False`，`show_success=False`）。

### 匯出鏈（`gui.py`）

| 流程 | 位置 | 目前行為 |
| --- | --- | --- |
| 匯出選單 | `on_export_document` 912-919 | 沒有選取文件：返回。先儲存（失敗則中止）。重新讀取選取的文件（讀不到則沿用儲存前讀到的）。`_export_document_with_dialog(document, key)`。 |
| 點字結果編輯器中的 Ctrl+S | `on_output_text_key_down` 959-968 | 儲存成功且有開啟文件時：`_export_document_with_dialog(開啟的文件, get_format("brl").key)`。之後一律 `output_txt.SetFocus()`；不呼叫 `Skip()`。 |
| 單一匯出 | `_export_document_with_dialog` 575-610 | `descriptor = get_format(key)`；`default_file = name + extension`；`wildcard = build_export_wildcard(descriptor, _)`；`wx.FileDialog(self, _("Export Document"), defaultFile=..., wildcard=..., style=wx.FD_SAVE \| wx.FD_OVERWRITE_PROMPT)`；取消：返回。若 `path.suffix.casefold() != extension`：`path.with_suffix(extension)`。若 `document.braille is None`：`_start_export_conversion(document, path, key, on_success=lambda braille: _continue_single_export(Document(name, text, braille), path, key), on_error=lambda message: wx.MessageBox(message, _("Error"), wx.OK \| wx.ICON_ERROR, parent=self))`；返回。否則 `_continue_single_export(document, path, key)`。 |
| 匯出轉換 | `_start_export_conversion` 1039-1067 | 缺少預設點字表：有 `on_missing_table` 就呼叫它，否則呼叫 `on_error(message)`；回傳 `False`（不設忙碌、不開執行緒）。否則 `_start_conversion(document.text, settings.width, settings.output_mode, 字典路徑, on_success, on_error, update_output=False, show_success=False)`；回傳 `True`（沒人使用）。`destination_path` 與 `format_key` 沒有使用。 |
| 寫檔與回報 | `_continue_single_export` 1021-1032、`_write_export_document` 1014-1019 | `get_format(key)`；不可匯出或沒有 writer：`ValueError('Unsupported export format: "<key>".')`（不攔截）。`writer(path, document, ExportContext(dual_view_results=controller.get_dual_view_results(document.name)))`。`OSError`：`_show_file_error(_("Failed to export document: {error}"), exc)` 後返回。成功：`wx.MessageBox(_("The document was exported successfully."), _("Export Complete"), wx.OK \| wx.ICON_INFORMATION, parent=self)`。 |
| 全部匯出選單 | `on_export_all_documents` 921-935 | 沒有文件：返回。先儲存。`wx.DirDialog(self, _("Export All Documents"))`；取消：返回。`suffix = get_format(key).extension`；`documents = controller.documents_snapshot()`；`conflicts` = 已 `exists()` 的目標路徑；若有衝突且 `_confirm_overwrite_all(conflicts)`（565-573：`wx.MessageBox(<覆寫訊息>, _("Confirm Overwrite"), wx.YES_NO \| wx.ICON_WARNING, parent=self) == wx.YES`）為假：返回。`_export_next_document(documents, folder, key, ExportBatchResult())`。 |
| 鏈的一步 | `_export_next_document` 1069-1112 | 清單為空：`_show_export_all_result(result)` 後返回。否則 `get_format(key)`（每步一次）、第一份文件、目標 `folder / (name + extension)`。`continue_batch()` = `wx.CallAfter(_export_next_document, rest, folder, key, result)`。`write_document(doc)`：`_write_export_document`；`OSError`：`add_failure(name, str(exc))`，否則 `add_success(name)`；接著 `continue_batch()`。已有點字：`write_document(document)` 後返回。否則 `conversion_failed(message)` = `add_failure(name, message)` + `continue_batch()`，並 `_start_export_conversion(..., on_success=lambda braille: write_document(Document(name, text, braille)), on_error=conversion_failed, on_missing_table=conversion_failed)`。 |
| 摘要 | `_show_export_all_result` 1114-1122 | `wx.MessageBox(_(result.summary_template).format(**result.summary_values), _(result.summary_title), wx.OK \| (全部成功時 wx.ICON_INFORMATION，否則 wx.ICON_WARNING), parent=self)`。 |

### 目前的非同步順序

- **手動轉換。** 點擊回合：檢查、設忙碌、關閉對話框、建立請求、啟動執行緒、設定 2 秒計時器。worker：轉換、`CallAfter`。計時器回合（只有 2 秒後仍在執行時）：顯示一次對話框。遞送回合：停止計時器、關閉對話框、解除忙碌、設定輸出並取得焦點、更新文件與快取、重新整理 Dual View、顯示 "Conversion completed." 訊息框。
- **單一匯出，pending 文件。** 選單回合：儲存、檔案對話框、設忙碌、啟動轉換。遞送回合：停止計時器、關閉對話框、解除忙碌、寫檔、顯示 "Export Complete" 訊息框（或錯誤框）。點字結果編輯器、快取與 Dual View 都不會被動到。
- **全部匯出。** 選單回合：儲存、資料夾對話框、衝突檢查，接著**第一步**在同一回合同步執行。之後每一步都在各自的 `CallAfter` 回合執行。已有點字的文件在該步的回合寫檔。pending 文件在該步的回合啟動轉換，在遞送回合寫檔，再排入下一步。只有轉換執行時才是忙碌狀態，因此步與步之間 UI 是可用的。摘要框只出現一次，在處理空清單那一步的回合。

### 目前的重入行為

| 轉換執行中的進入點 | 能否觸發？ | 效果 |
| --- | --- | --- |
| 轉換（選單、Ctrl+Enter） | 否：「翻譯」選單與原文編輯器已停用；`on_convert` 也會檢查 `is_running()` | — |
| 「檔案」選單（匯出、全部匯出、匯入……）、文件清單（F2、Delete、啟動、右鍵選單） | 否：已停用 | — |
| 點字結果編輯器中的 Ctrl+S | **可以** | 先儲存，再匯出開啟的文件。已有點字：同步寫檔，顯示 "Export Complete"；執行中的 job 繼續。pending：**不經任何 `is_running()` 檢查就啟動第二個 job**；再次設忙碌、關閉對話框、設定新計時器（舊的沒有被停止，之後觸發也不做事）。第一個 job 的結果被當成過期丟棄；若它是手動轉換，輸出永遠不會更新，也沒有任何訊息（既有缺陷 2）。 |
| Ctrl+Tab / Ctrl+Shift+Tab（frame char hook） | **可以** | 儲存並開啟另一份文件。手動 job 完成時，它的點字與原文編輯器文字會寫入**當時**開啟的文件，快取也寫在那個名稱下（既有缺陷 1）。 |
| Ctrl+O（frame char hook） | **可以** | 執行匯入流程；只匯入一個檔案時會開啟它，效果同 Ctrl+Tab。 |
| 關閉視窗 | 執行中且 `CanVeto()` 時否決 | 無法否決時：儲存、關閉對話框、銷毀檢視器。 |
| 全部匯出的步與步之間（沒有 job 執行） | 全部可用 | 在空檔中啟動的轉換會被下一份 pending 文件的匯出轉換取代（當成過期丟棄，沒有訊息）。也可以再啟動一次全部匯出，兩條鏈交錯執行。 |

### 目前涉及的測試

- `tests/test_conversion_jobs.py`（4 個測試）：成功、stage 失敗、過期成功與過期失敗，使用 `FakeThread`（記錄 target 與 args；`start()` 只標記為存活；由測試呼叫 `run()`）與同步的 `call_after`。
- `tests/test_gui_document_flows.py` 的 `GuiDocumentFlowsTest` 與其子類別 `BrailleAppLifecycleTest`：22 個測試以 `Mock` runner 與 `Mock` 的忙碌／對話框方法驅動 frame 內部：`_write_export_document`（4）、`_export_next_document`（5，把 `gui.wx.CallAfter` patch 成同步執行）、`_start_conversion`（1）、`_complete_conversion` / `_finish_conversion_*`（7）、`on_convert`（2）、`_start_export_conversion`（1）、`_missing_default_table_message`（1）、缺少點字表時的 `_export_document_with_dialog`（1）。其中只有五個定義在 `GuiDocumentFlowsTest`（`test_write_export_document_*` 三個、`test_write_html_export_document_passes_cached_dual_view_results`、`test_export_next_document_uses_registry_extension`）；`BrailleAppLifecycleTest` 繼承它，所以這五個會跑兩次，其餘 17 個定義在 `BrailleAppLifecycleTest`。搬移它們會移除 27 個測試行：第 4 步 12 行、第 7 步 15 行。`DocumentMenuAndExportCharacterizationTest`（P1-2）有 5 個匯出測試：對話框標題／wildcard（patch `gui._`）、副檔名修正、真實 writer 的位元組、全部匯出 HTML 快取、Ctrl+S。`DocumentWorkspaceFlowsCharacterizationTest._make_workspace_frame` 為 `_on_close` 設定 `_conversion_runner` 與 `_close_converting_dialog` 的 mock。
- **目前沒有涵蓋：** 真正的 runner 接到 frame；轉換中對話框與其計時器；忙碌狀態的控制項呼叫；全部匯出鏈的非同步順序（所有測試都同步執行 `CallAfter`，看不到每一步的回合邊界）；全部匯出的衝突確認與資料夾取消；上表的重入情境；`ascii` 與未知 stage 的錯誤訊息對應，以及公開錯誤文字。
- wx stub 遮蔽（`tests/wx_stub.py`）：在 stub frame 上，任何不存在的實例屬性都是 no-op 函式，因此測試必須明確設定 presenter 與 coordinator。

## 設計

兩個 view protocol 只是 `typing.Protocol` 型別標註。frame 以一般方法實作，測試使用小型的記錄用假物件，與 `dictionaries/presenter.py` 的 `DictionaryManagementView` 相同做法。沒有 view 基底類別，也沒有 MVP 框架（refactor.md 第 7 節第 4 點）。

### `conversion/jobs.py`（I-3）

- 刪除 `ConversionCompletionPolicy` 與 `ConversionJobRequest`。
- `ConversionJobSuccess(job_id: int, conversion_output: ConversionOutput)` 與 `ConversionJobFailure(job_id: int, error: ConversionStageError)`（frozen dataclass，沒有 policy 欄位）。
- `ConversionJobRunner.start(request: ConversionRequest) -> int`；`_run_job(job_id, request)` 呼叫 `converter(request, runtime=...)`。
- 其他全部不變：job id、`daemon=True`、過期過濾、在回呼前先設 `_thread = None`、`is_running()`、`active_job_id`、非 `ConversionStageError` 例外逸出。runner 仍是唯一的執行緒程式碼（refactor.md 第 7 節第 2 點：不引入通用 task framework）。

不採用改名方案（`ConversionCompletionContext`）：那樣 UI 回呼仍會經過 worker，正是 I-3 指出的問題，而且 presenter 本來就需要保存這份狀態。

### `ConversionPresenter`（`conversion/presenter.py`，新檔，不 import wx）

```python
CONVERTING_DIALOG_DELAY_MS = 2000

class Timer(Protocol):
    def Stop(self) -> object: ...          # wx.CallLater 的回傳值

CallAfter = Callable[..., object]          # wx.CallAfter
CallLater = Callable[..., Timer]           # wx.CallLater(ms, fn, *args)

class ConversionView(Protocol):
    def get_source_text(self) -> str: ...
    def set_conversion_busy(self, busy: bool) -> None: ...
    def show_converting_dialog(self) -> None: ...      # 可重複呼叫
    def close_converting_dialog(self) -> None: ...     # 可重複呼叫
    def show_conversion_output(self, text: str) -> None: ...   # 先設值，再取得焦點
    def refresh_dual_view(self) -> None: ...
    def show_info(self, message: str, caption: str) -> None: ...
    def show_error(self, message: str, caption: str) -> None: ...

def missing_default_table_message(translation_tables: Mapping[str, object]) -> str | None: ...
def format_conversion_error(error: ConversionStageError) -> str: ...

class ConversionPresenter:
    def __init__(
        self,
        view: ConversionView,
        documents: DocumentController,
        *,
        runtime: TranslationRuntime,
        build_request: Callable[[str], ConversionRequest],
        get_translation_tables: Callable[[], Mapping[str, object]],
        call_after: CallAfter,
        call_later: CallLater,
        thread_factory: ThreadFactory = threading.Thread,
        converter: Callable[..., ConversionOutput] = convert_text_with_alignment,
    ) -> None: ...
    def is_running(self) -> bool: ...
    def missing_table_message(self) -> str | None: ...
    def convert(self) -> None: ...
    def convert_for_export(self, raw_text: str, *, on_success: Callable[[str], None], on_error: Callable[[str], None]) -> None: ...
```

presenter 自行建立 `ConversionJobRunner(runtime=..., on_success=self._on_job_success, on_failure=self._on_job_failure, call_after=call_after, converter=converter, thread_factory=thread_factory)`。它在呼叫當下以 `i18n` 的 `_` 建立所有使用者可見字串，與 `dictionaries/presenter.py` 相同。

逐步行為（與今日順序相同）：

- `missing_default_table_message(tables)`：`tables.get("default")` 為真值時回傳 `None`，否則回傳 `_("Please select a translation table first.")`。`missing_table_message()` 對 `get_translation_tables()` 套用它（在呼叫當下讀取，因為 `apply_settings_from_dialog` 會換掉整個 dict）。
- `format_conversion_error(error)`：stage 範本表與 `_(get_public_error_message(error.error))`，與今日 `_finish_conversion_failure` 完全相同。
- `convert()`：若 `is_running()`：返回。若 `missing_table_message()` 不是 `None`：`view.show_info(message, _("Info"))` 後返回。`raw_text = view.get_source_text()`；`_start(raw_text, export=None)`。
- `convert_for_export(raw_text, on_success, on_error)`：`_start(raw_text, export=_ExportCallbacks(on_success, on_error))`。不檢查是否執行中，也不檢查點字表（coordinator 會先檢查點字表，與今日相同；缺少執行中檢查是既有缺陷 2，予以保留）。
- `_start(raw_text, export)`：`view.set_conversion_busy(True)`；`view.close_converting_dialog()`；`request = build_request(raw_text)`；`job_id = runner.start(request)`；`self._active = _ActiveJob(job_id, export)`；`self._timer = call_later(CONVERTING_DIALOG_DELAY_MS, self._show_converting_dialog, job_id)`（覆蓋先前的計時器而不停止它，與今日相同）。
- `_show_converting_dialog(job_id)`：若 `job_id != runner.active_job_id` 或 `runner.is_running()` 為假則返回；否則 `view.show_converting_dialog()`（若對話框已存在，frame 會直接返回）。
- `_on_job_success(result)` / `_on_job_failure(result)`：若 `self._active` 的 `job_id` 等於 `result.job_id` 就取出並清除（runner 已經丟棄過期結果；不相符時防禦性地忽略）。接著 `_finish`。
- `_finish(job, output | error_message)`：若有計時器就 `Stop()` 並清除；`view.close_converting_dialog()`；`view.set_conversion_busy(False)`。**錯誤：** 匯出：`job.export.on_error(message)`；手動：`view.show_error(message, _("Error"))`；返回。**成功：** `braille = output.display_text`。手動：`view.show_conversion_output(braille)`；`open_name = documents.open_document_name`；若有 `open_name`：`document = documents.get_document(open_name)`；不是 `None` 時 `documents.replace_document(Document(document.name, view.get_source_text(), braille))`；`documents.set_dual_view_results(open_name, output.dual_view_segments)`；接著 `view.refresh_dual_view()`；接著 `view.show_info(_("Conversion completed."), _("Info"))`。匯出：只呼叫 `job.export.on_success(braille)`。

兩種形狀的完成處理（`_ActiveJob(job_id, export: _ExportCallbacks | None)`，`None` 代表手動）取代四個欄位的 policy。因為實際只存在上述兩種形狀，兩者完全等價。`_ActiveJob` 與 `_ExportCallbacks` 是 private 的 frozen dataclass。

`call_after` 的契約：它必須延後執行（如同 `wx.CallAfter`），因此 `self._active` 一定在任何遞送之前存好。測試用的 thread factory 不可以在 `start()` 內執行 target（現有的 `FakeThread` 不會）。

### `ExportCoordinator`（`documents/export_coordinator.py`，新檔，不 import wx）

```python
class ExportView(Protocol):
    def choose_export_path(self, default_file: str, descriptor: DocumentFormatDescriptor) -> Path | None: ...
    def choose_export_directory(self) -> Path | None: ...
    def confirm_overwrite_all(self, conflicts: list[Path]) -> bool: ...
    def show_info(self, message: str, caption: str) -> None: ...
    def show_warning(self, message: str, caption: str) -> None: ...
    def show_error(self, message: str, caption: str) -> None: ...

class ExportConversions(Protocol):            # 由 ConversionPresenter 滿足
    def missing_table_message(self) -> str | None: ...
    def convert_for_export(self, raw_text: str, *, on_success: Callable[[str], None], on_error: Callable[[str], None]) -> None: ...

class ExportCoordinator:
    def __init__(self, view: ExportView, documents: DocumentController, conversions: ExportConversions, *, call_after: CallAfter) -> None: ...
    def export_document(self, document: Document, format_key: str) -> None: ...
    def export_all(self, format_key: str) -> None: ...
    def write_document(self, destination_path: Path, document: Document, format_key: str) -> None: ...
```

view 擁有它自己對話框的文字（檔案對話框標題與 wildcard、資料夾對話框標題、覆寫確認問題），因此這些 msgid 留在 `gui.py`，P1-2 那個 patch `gui._` 的 wildcard 測試仍然有效。coordinator 擁有結果訊息。

- `write_document`：`_write_export_document` 的本體，快取經由 `documents.get_dual_view_results(document.name)` 讀取。不可匯出格式的 `ValueError` 向外拋出。
- `export_document(document, key)`：`descriptor = get_format(key)`；`path = view.choose_export_path(f"{document.name}{descriptor.extension}", descriptor)`；`None`：返回。依今日方式修正副檔名。若 `document.braille is None`：`message = conversions.missing_table_message()`；不是 `None` 時 `view.show_error(message, _("Error"))` 後返回；否則 `conversions.convert_for_export(document.text, on_success=lambda braille: self._write_single(Document(document.name, document.text, braille), path, key), on_error=lambda message: view.show_error(message, _("Error")))` 後返回。否則 `_write_single(document, path, key)`。
- `_write_single`：`write_document`；`OSError`：`view.show_error(_("Failed to export document: {error}").format(error=exc), _("Error"))` 後返回；成功：`view.show_info(_("The document was exported successfully."), _("Export Complete"))`。
- `export_all(key)`：`folder = view.choose_export_directory()`；`None`：返回。`suffix = get_format(key).extension`；`documents_to_export = documents.documents_snapshot()`；衝突判斷同今日；`if conflicts and not view.confirm_overwrite_all(conflicts)`：返回。`_export_next(documents_to_export, folder, key, ExportBatchResult())`。
- `_export_next`：`_export_next_document` 的本體，`continue_batch` 改為 `call_after(self._export_next, rest, folder, key, result)`，pending 文件先 `conversions.missing_table_message()` 再 `conversions.convert_for_export(document.text, on_success=..., on_error=conversion_failed)`（缺少點字表：`conversion_failed(message)`），最後 `_show_batch_result(result)`。
- `_show_batch_result`：`message = _(result.summary_template).format(**result.summary_values)`；`caption = _(result.summary_title)`；全部成功時 `view.show_info`，否則 `view.show_warning`。

「先儲存」防護、選取查詢與 `has_documents` 留在 frame 的選單 handler（它們屬於 P1-3 的文件流程），因此 coordinator 的進入點正好是今日進入 `_export_document_with_dialog` 與全部匯出資料夾對話框的位置。

### `BrailleFrame`（`gui.py`）

- `_initialize_conversion_state()`：`self._convert_dialog = None`；`self._conversion_presenter = ConversionPresenter(self, self._document_controller, runtime=self.translation_runtime, build_request=self._build_conversion_request_for_text, get_translation_tables=lambda: self.translation_tables, call_after=wx.CallAfter, call_later=wx.CallLater)`；`self._export_coordinator = ExportCoordinator(self, self._document_controller, self._conversion_presenter, call_after=wx.CallAfter)`。在 `__init__` 中的位置不變。
- 新增 `_build_conversion_request_for_text(raw_text)`：`settings = self.translation_settings`；`return self._build_conversion_request(raw_text, settings.output_mode, settings.width, self._get_selected_dictionary_path())`。`_build_conversion_request` 不變（其測試保留）。
- `on_convert(_evt)`：`self._conversion_presenter.convert()`。
- `on_export_document`、`on_export_all_documents`、`on_output_text_key_down`：防護與先儲存不變；最後的呼叫改為 `self._export_coordinator.export_document(document, key)` / `self._export_coordinator.export_all(key)`。
- `_on_close`：改用 `self._conversion_presenter.is_running()` 與 `self.close_converting_dialog()`；其餘不變。
- view 方法（public、精簡、只含 wx）：`get_source_text`（`input_txt.GetValue()`）、`set_conversion_busy`（`_set_conversion_busy` 的本體，包含依翻譯後標題 `FindMenu`）、`show_converting_dialog`（`_show_converting_dialog` 在 job 檢查之後的本體）、`close_converting_dialog`（`_close_converting_dialog` 的本體）、`show_conversion_output`（先 `SetValue` 再 `SetFocus`）、`refresh_dual_view`（呼叫 `_refresh_dual_view()`，其他流程與測試繼續使用後者）、`show_info` / `show_warning` / `show_error`（`wx.MessageBox(message, caption, wx.OK | wx.ICON_INFORMATION / ICON_WARNING / ICON_ERROR, parent=self)`）、`choose_export_path`（`_export_document_with_dialog` 中檔案對話框的部分：wildcard 經 `build_export_wildcard(descriptor, _)`，標題、style 與 `defaultFile` 相同）、`choose_export_directory`（`on_export_all_documents` 中 `wx.DirDialog` 的部分）、`confirm_overwrite_all`（`_confirm_overwrite_all` 改名，本體相同）。
- 刪除：`_set_conversion_busy`、`_start_conversion`、`_show_converting_dialog`、`_close_converting_dialog`、`_complete_conversion`、`_finish_conversion_success`、`_finish_conversion_failure`、`_missing_default_table_message`、`_start_export_conversion`、`_export_document_with_dialog`、`_continue_single_export`、`_write_export_document`、`_export_next_document`、`_show_export_all_result`、`_confirm_overwrite_all`，以及 `_conversion_runner` 與 `_convert_dialog_timer` 屬性。
- 從 `gui` 移除的 import（在不再使用它的那一步移除）：`conversion.jobs`（全部名稱）、`ConversionOutput`、`ConversionStageError`、`get_public_error_message`、`ExportContext`、`ExportBatchResult`。`ConversionRequest`（`_build_conversion_request` 的型別標註）、`get_format`（Ctrl+S）與 `build_export_wildcard` 保留。
- M-9：`_show_file_error(self, message, error)` 移除未使用的 `parent` 參數（沒有呼叫者傳入）。
- `ConvertingDialog` 留在 `gui.py`。

### 字串

msgid 隨呼叫點移動：`Please select a translation table first.`、`Conversion completed.` 與三個失敗範本移到 `conversion/presenter.py`；`Failed to export document: {error}`、`The document was exported successfully.`、`Export Complete` 移到 `documents/export_coordinator.py`；`Info` 與 `Error` 新模組也會使用，同時仍留在 `gui.py`（`ConvertingDialog` 標題與 `_show_file_error`）。`scripts/generate-pot.bat` 會抽取 `tests` 以外的所有 `client/**/*.py`，因此 msgid 集合不變（353），只有下次重新產生 `.pot` 時 `#:` 參照會改變。不修改 `.po`/`.mo`。

### 遷移步驟（每一步是一個全綠的 commit；細節由 plan 說明）

1. `test:` 新增 `tests/conversion_harness.py`（`FakeThread` 從 `test_conversion_jobs.py` 移來、`DeferredCalls`、`FakeTimers`）與 frame 層級的特性測試類別（測試計畫 A 部分）。在今日程式碼上通過，由一個 fixture helper 把真正的 runner 接到 frame。以一個突變步驟證明新測試在刻意弄壞的 `gui.py`（全部匯出鏈直接呼叫下一步而不經 `wx.CallAfter`；轉換中對話框的計時器從不停止）上會失敗，之後還原。
2. `test:` 在 `tests/test_conversion_jobs.py` 新增 runner 契約測試（B 部分）。在今日程式碼上通過。一個突變步驟（非 daemon 執行緒；在回呼之後才清除執行緒）證明它們有效。
3. `refactor:` 先寫測試，新增 `conversion/presenter.py` 與 `tests/test_conversion_presenter.py`（C 部分）。此時仍呼叫 `runner.start(ConversionJobRequest(conversion_request=request))`，使用預設（未使用的）policy。`gui` 尚未使用它。
4. `refactor:` 讓轉換經過 presenter：接線、`on_convert`、`_on_close`、view 方法，以及一個暫時的 `_start_export_conversion`：以模組函式 `missing_default_table_message(self.translation_tables)`（本步 import，第 7 步移除）檢查點字表，再呼叫 `self._conversion_presenter.convert_for_export(...)`。frame helper 使用 `Mock(spec=ConversionPresenter)`，若改用 presenter 檢查點字表會拿到一個 `Mock`；這個函式讀取的是同一份即時的 `translation_tables`。從 frame 刪除轉換狀態機，並移除 `conversion.jobs`、`ConversionOutput` 與 `get_public_error_message` 的 import。搬移 `BrailleAppLifecycleTest` 的 12 個轉換測試（E 部分），包括 mock 了已刪除之 `_start_conversion` 的 `test_export_conversion_with_default_table_starts_background_conversion`，並把特性測試的 helper 換成 presenter。先寫紅燈測試：`FrameConversionDelegationTest`（以 `wx.CallAfter`/`wx.CallLater`、frame 作為 view、即時點字表接線；`_build_conversion_request_for_text`；轉換與 Ctrl+Enter 的委派；關閉時先詢問 presenter 再儲存）與 `FrameViewMethodsTest`（轉換的 view 方法）。
5. `refactor:` 讓完成狀態不再進入轉換 job（I-3）：刪除 `ConversionCompletionPolicy` 與 `ConversionJobRequest`，更新 `tests/test_conversion_jobs.py` 與 presenter。先寫紅燈測試：`test_results_carry_only_the_job_id_and_the_outcome`（在 runner 修改之前，既有的四個 runner 測試也會因新的 `start(ConversionRequest)` 呼叫而失敗）。
6. `refactor:` 先寫測試，新增 `documents/export_coordinator.py` 與 `tests/test_export_coordinator.py`（D 部分）。`gui` 尚未使用它。
7. `refactor:` 讓匯出經過 coordinator：接線、三個進入點、匯出 view 方法；從 frame 刪除匯出鏈；搬移匯出測試（E 部分，15 個測試行）；切換特性測試的 helper。移除 `ExportContext`、`ExportBatchResult` 與暫時的 `missing_default_table_message` import；`gui` 新增 `DocumentFormatDescriptor` 作為 `choose_export_path` 的型別標註；`tests/test_gui_document_flows.py` 移除只有被搬移測試使用的 `dataclasses.replace`、`ExportContext` 與 `get_format`。先寫紅燈測試：`FrameExportDelegationTest` 與 `FrameExportViewMethodsTest`。
8. `refactor:` 移除早已未使用的 `ConversionStageError` import、M-9（先寫紅燈測試：檢查簽章的 `test_show_file_error_formats_the_error_for_the_frame`）、最後的 grep 檢查與 msgid 掃描。

第 1 步的特性測試在每一步之後都必須以**不變的測試本體與預期記錄**通過。只有它們的 fixture helper `_wire_conversion` 會改變（第 4 步：改建 `ConversionPresenter` 而非 runner；第 7 步：再加建 `ExportCoordinator`）。驗收條件 6 以 AST 檢查這一點。

## 保持不變的部分

- 上面兩張表的每一列：各項檢查與其順序、忙碌切換（相同控制項、相同順序：檔案、翻譯、文件清單、原文編輯器）、轉換中對話框（2000 ms、job 與執行中檢查、最多一個、以 `Unbind` + `Destroy` 關閉）、訊息、標題、圖示、parent、寫出的檔案與其位元組、寫檔時讀取快取、只有手動轉換後才寫入快取。
- 「目前的非同步順序」所描述的順序：哪些效果發生在點擊回合、worker、計時器回合，以及每一個遞送或鏈的回合。全部匯出的第一步仍在選單回合同步執行；之後每一步都是一個 `call_after` 回合。
- 重入：重入表的每一列，包含既有缺陷 1 與 2。
- runner：id、過期過濾、完成回呼內 `is_running()` 為假、daemon 執行緒、非 `ConversionStageError` 例外不遞送。
- msgid（353 個，集合相同）；不動 `client/locales/` 與 `scripts/`；P1-2 的「檔案」選單建構記錄；P1-3 的文件流程。

刻意的內部差異（使用者都看不到）：翻譯設定與字典路徑改在 `build_request` 內讀取（設忙碌之後），而不是在 `on_convert` 內（設忙碌之前）；兩者之間沒有任何可觀察的事。`_start_export_conversion` 未使用的 `destination_path`/`format_key` 參數與 `bool` 回傳值消失。`_complete_conversion` 只給測試用的 `display_text=` 路徑消失。`_on_job_failure` 在結束 job 之前先格式化訊息（格式化沒有副作用）。`confirm_overwrite_all` 保留 `if not conflicts: return True`，雖然 coordinator 只在有衝突時呼叫它。

## 測試計畫

### 共用 harness（`tests/conversion_harness.py`，新檔，沒有 `test_` 前綴）

- `FakeThread`：從 `tests/test_conversion_jobs.py` 移來，除縮排外不變；`make_thread_factory()` 回傳 `thread_factory(*, target, args=(), daemon=None)`，其 `threads` 清單屬性記錄每條執行緒。
- `DeferredCalls(events=None)`：把 `(fn, args, kwargs)` 排入佇列並記錄 `("call_after",)` 的 `call_after`；提供 `run_next()`、`run_all()`（執行到佇列為空，包含新排入的呼叫）與 `pending`。
- `FakeTimers(events=None)`：記錄 `("call_later", ms, args)` 的 `call_later(ms, fn, *args)`，回傳具有 `number`（從 1 起算）、`stopped`、`Stop()`（設定 `stopped` 並記錄 `("timer.Stop", number)`）與 `fire()`（呼叫 `fn(*args)`，即使已 `Stop()` 也會呼叫，因此「遞送後觸發的計時器什麼都不做」是以 presenter 自己的防護來檢查）的 `FakeTimer`。

記錄項目不帶函式名稱：排入呼叫的程式碼會從 frame 移到 presenter 與 coordinator，而記錄不可以改變。

把它們放在 helper 模組，可以避免從一個測試模組 import 另一個 `TestCase` 模組（那會讓其測試跑兩次）。

### A. frame 特性測試（第 1 步，`tests/test_gui_document_flows.py`，新類別 `ConversionExportFlowsCharacterizationTest`）

每個測試以 `object.__new__` 建立 frame，使用真的 `DocumentController`、在暫存工作區上的 `DocumentWorkspaceService`、記錄用編輯器（值、`SetValue`、`SetFocus`、`Enable`）、記錄用文件清單（`Enable`）、回傳記錄用選單列（依標籤 `FindMenu`、`EnableTop`）的 `GetMenuBar`，以及在 `gui` 上 patch 的記錄用假物件：`wx.MessageBox`（排好的回答）、`wx.FileDialog`、`wx.DirDialog` 與 `ConvertingDialog`；`gui.get_lang`/`gui.get_charset_maps` 回傳常數。所有假物件都寫入同一份有序的 `self.events` 記錄。一個 fixture helper 用腳本化的假 converter（依原文：輸出或 `ConversionStageError`）、`FakeThread`、作為 `gui.wx.CallAfter` 的 `DeferredCalls` 與作為 `gui.wx.CallLater` 的 `FakeTimers` 接好轉換堆疊。測試只驅動 public 進入點（`on_convert`、`on_export_document`、`on_export_all_documents`、`on_output_text_key_down`、`on_char_hook`、`_on_close`），並明確推進 worker（`thread.run()`）、佇列（`run_next()`）與計時器（`fire()`），每一步之後檢查事件記錄。

忙碌切換也會記錄 `FindMenu(<翻譯後標題>)`，藉此釘住既有缺陷 5。`gui_frame_stubs()` 經由 stub 模組的 `__getattr__` 解析 `wx.EVT_CLOSE`，每次存取都回傳新的類別，因此測試把 `gui.wx.EVT_CLOSE` patch 成字串 `"EVT_CLOSE"` 以比對 `Unbind` 的參數。預期字串都經過 `_`：`i18n` 一律載入內建的 zh_TW 目錄，所以測試中 `gui._("Info")` 是 `資訊`，預期訊息以相同的 `_` 建立（frame 測試用 `gui._`，新模組的測試用 `from i18n import _`）。不是 msgid 的文字（全部匯出的摘要與訊息、公開的後備文字）以英文撰寫並加上 `KNOWN BUG (... defect 4)` 註解，因為使用者今天看到的就是英文。每個釘住既有缺陷的測試都帶有 `# KNOWN BUG (P1-4 spec, defect N)`。

案例（共 19 個測試；案例 9 是兩個測試）：

1. 手動成功：點擊回合（依序設忙碌、輸出不變、請求欄位：原文、寬度、模式、字典路徑、點字表副本、常數語言與對應；計時器 2000 ms）；worker 排入一個呼叫，其他都不變；遞送回合（停止計時器、解除忙碌、先設輸出再取得焦點、以原文與點字取代文件、設快取、重新整理 Dual View、"Conversion completed." / "Info" / 資訊圖示）。
2. 沒有開啟文件時手動成功：設輸出並取得焦點，文件與快取不變，重新整理 Dual View，顯示完成訊息框。
3. `ascii`、`text_processing`、`translation` 與未知 stage 的失敗訊息，以及公開文字（空訊息、liblouis 的 "Can't translate: tables ... inbuf"）：先解除忙碌，再顯示一個錯誤框（"Error"、錯誤圖示）；輸出、文件與快取不變。
4. 執行中再轉換：什麼都不發生（沒有訊息框、沒有新執行緒、沒有忙碌呼叫）。
5. 沒有預設點字表時轉換：一個 "Info" 訊息框，不設忙碌，不開執行緒。
6. 轉換中對話框：執行中觸發計時器會顯示一個對話框（parent 為 frame、`Show`、`Raise`）；再次觸發不會建立第二個；遞送時先停止計時器並關閉對話框（`Unbind(EVT_CLOSE)`、`Destroy`），再解除忙碌。遞送後觸發的計時器什麼都不做。
7. 過期計時器：job 2 執行中觸發 job 1 的計時器，什麼都不做。
8. 執行中關閉：`Veto`、不儲存、不關閉對話框；`CanVeto()` 為假時：儲存、關閉對話框、`Skip`。
9. 已有點字的單一匯出，兩個測試：(a) `test_single_export_with_braille_writes_and_reports`：檔案對話框參數、寫出的位元組、"Export Complete" 訊息框；(b) `test_single_export_write_error_and_extension_correction`：`OSError`（目標位置是資料夾）顯示 "Failed to export document" 錯誤框且沒有成功訊息框；錯誤的副檔名會被修正。
10. pending 文件的單一匯出：測試開啟一份文件、匯出另一份（已選取、pending）文件，因為先儲存會把編輯器文字複製到*開啟中*的文件，只有未開啟的文件才能證明匯出轉換的是 `document.text` 而不是編輯器文字。設忙碌、轉換 `document.text`（不是編輯器文字）；遞送：解除忙碌、以轉換後的點字寫檔、"Export Complete"；輸出編輯器、快取與 Dual View 都不變；沒有 "Conversion completed." 訊息框。
11. pending 文件的單一匯出：轉換失敗顯示一個 stage 錯誤框（"Error"），不寫檔；缺少點字表顯示一個 "Error" 訊息框，不設忙碌，不開執行緒。
12. 全部匯出，混合清單 `[ready, pending, ready-2, write-fail(資料夾), convert-fail, pending-ok]`：回合邊界（第一步在選單回合；之後每一步只有在 `run_next()` 之後才執行；pending 那一步只啟動轉換；它的遞送才寫檔並排入下一步）、只在每次轉換前後切換忙碌，以及最後一個帶有正確失敗行的警告摘要。
13. 全部匯出，全部已有點字：一個資訊摘要；沒有忙碌呼叫。
14. 沒有預設點字表時全部匯出：失敗累積並帶點字表訊息，沒有逐檔訊息框，每一步仍在各自的回合。
15. 全部匯出的對話框：取消資料夾什麼都不做；沒有衝突：不詢問；有衝突回答「否」：不寫任何檔；回答「是」：全部寫出。
16. 重入，手動轉換中在 pending 的開啟文件上按 Ctrl+S：儲存、第二個 job（再次設忙碌、關閉對話框、新計時器、第一個計時器沒有停止）；完成 job 1 不遞送任何東西；job 2 遞送時寫檔並顯示 "Export Complete"；輸出編輯器始終沒被設定（既有缺陷 2）。
17. 重入，手動轉換中按 Ctrl+Tab：結果寫入新開啟的文件與其快取項目（既有缺陷 1）。
18. 重入，在全部匯出的空檔中轉換：排入的下一個 pending 步驟取代手動 job，手動 job 不遞送任何東西。

### B. runner 契約（第 2 步，`tests/test_conversion_jobs.py`）

在既有 4 個測試之外新增：執行緒以 `daemon=True` 建立，每個 job 啟動一次；`on_success` 與 `on_failure` 內 `is_running()` 為假；過期的遞送不會清掉目前 job 的執行緒（`is_running()` 仍為真）；非 `ConversionStageError` 的例外不遞送任何東西，執行緒結束後 `is_running()` 為假；`active_job_id` 跟著 `start` 變化。第 5 步時既有 4 個測試移除 policy 參數，斷言不變。

### C. `tests/test_conversion_presenter.py`（新檔，第 3 步，不用 wx 也不用 stub scope）

一個記錄用 view（實作 `ConversionView`，一份有序記錄）、真的 `DocumentController`、harness 的 `FakeThread`/`DeferredCalls`/`FakeTimers`，以及假 converter。涵蓋 presenter 設計的每一點：`missing_default_table_message` 對 `{}`、`{"default": ""}`、`{"default": None}` 與已設定的點字表；`format_conversion_error` 對每個 stage 與公開文字；`convert()` 的防護順序（執行中、點字表、再讀原文）；`_start` 的順序；計時器回呼的檢查；手動成功（有／沒有開啟文件，以及開啟名稱不在清單中時仍寫入快取）；手動失敗；匯出成功與失敗（只有回呼，不動輸出、快取，也沒有訊息框）；前一個 job 完成後的下一個 job 使用自己的完成處理；被取代的 job 不遞送任何東西；`is_running()` 與 `missing_table_message()` 讀取即時狀態；模組既不 import `wx` 也不 import `gui`（AST 檢查，與 `test_workspace_service.py` 相同）。這些是 E 部分從 frame 搬來之測試的 presenter 版本。

### D. `tests/test_export_coordinator.py`（新檔，第 6 步，不用 wx 也不用 stub scope）

一個記錄用 view、真的 `DocumentController`、假的 `ExportConversions`（腳本化：啟動後由測試呼叫存下的回呼）、`DeferredCalls`、使用真實 registry writer 的暫存資料夾，以及用 `import documents.export_coordinator as coordinator_module` 來 patch `get_format`（P0 審查 I-1 建議的 import 寫法）。案例：`write_document`（每種格式的 registry writer 與 `ExportContext`、每份文件的快取、不可匯出的 `ValueError`）；`export_document`（傳給 view 的預設檔名與 descriptor、取消、副檔名修正、已有點字、`OSError`、pending 成功與失敗、缺少點字表）；`export_all`（取消資料夾、對話框之後才取快照、只在需要時詢問衝突及其回答、以 `DeferredCalls` 檢查回合邊界、`get_format` 在衝突檢查、每一步與每次 `write_document` 時讀取、成功／部分失敗摘要的文字、標題與種類、逐份文件的缺少點字表、`ValueError` 會中斷鏈）。一個整合測試在 coordinator 後面接真的 `ConversionPresenter`（記錄用 view、`FakeThread`）執行混合的全部匯出。模組既不 import `wx` 也不 import `gui`（AST 檢查）。

### E. 更新與搬移的測試（`tests/test_gui_document_flows.py`）

| 今日 | 之後 |
| --- | --- |
| `test_write_export_document_*`（3）與 `test_write_html_export_document_passes_cached_dual_view_results`、`test_export_next_document_uses_registry_extension`、`test_export_all_*`（4）、`test_single_pending_export_missing_table_*` | 相同斷言移到 D 部分（第 7 步；15 個測試行，因為前五個也在 `BrailleAppLifecycleTest` 中執行）。例外一個：`test_export_next_document_uses_registry_extension` 以假 writer 取代真的 writer，並斷言 `get_format` 只被呼叫一次。經由 coordinator 的 public `export_all`，`get_format` 會在衝突檢查、該步與 `write_document` 中被讀取，因此 `test_export_all_reads_the_format_for_conflicts_each_step_and_each_write` 斷言三次呼叫，以及寫出檔名中被 patch 的副檔名。 |
| `test_start_conversion_builds_request_and_starts_runner`、`test_manual_conversion_updates_output_focus_and_shows_completion`、`test_export_conversion_calls_success_callback_without_manual_message`、`test_export_conversion_calls_error_callback_without_showing_worker_error`、`test_export_conversion_does_not_replace_dual_view_cache`、`test_text_processing_failure_uses_its_own_message`、`test_later_job_uses_its_own_policy_after_previous_completion`、`test_successful_manual_conversion_stores_segments_and_refreshes_open_viewer`、`test_missing_default_table_message_reports_only_unset_default` | 相同斷言移到 C 部分（第 4 步）。 |
| `test_convert_without_default_table_*`、`test_convert_with_default_table_*` | C 部分，另加一個 frame 委派測試：`on_convert` 呼叫 `presenter.convert()`。 |
| `test_export_conversion_with_default_table_starts_background_conversion` | 在第 4 步刪除（它 mock 了第 4 步刪除的 `_start_conversion`）。由 `test_convert_for_export_converts_given_text_without_checks`（C 部分）與 frame 測試 `test_build_conversion_request_for_text_reads_current_settings` 涵蓋；暫時的 `_start_export_conversion` 在第 7 步刪除之前，由特性測試案例 10-12、14、16 與 18 端到端執行。 |
| P1-2 的 `test_export_dialog_title_default_file_wildcard_and_style`、`test_export_dialog_corrects_only_a_wrong_extension`、`test_real_writers_produce_today_bytes`、`test_export_all_html_uses_each_document_cache` | 斷言不變，改由以 frame 為 view 建立的 `frame._export_coordinator` 進入（第 7 步）。`gui._` 的 patch 仍作用在對話框標題與 wildcard 上。 |
| `test_ctrl_s_in_output_editor_exports_open_document_as_brl` | 預期在儲存與 `SetFocus` 之間出現 `call.coordinator.export_document(<開啟的文件>, "brl")`。 |
| `_make_frame`、`_make_workspace_frame` | 改設 `_conversion_presenter` / `_export_coordinator`（mock），不再設 `_conversion_runner`、`_convert_dialog_timer`、`_set_conversion_busy`、`_close_converting_dialog`、`_show_export_all_result`；`test_close_vetoes_when_save_fails` 改檢查 `close_converting_dialog`。 |

第 4 步的各列（9 + 2 + 1 個測試，全部定義在 `BrailleAppLifecycleTest`）移除 12 個測試行。

新的 frame 測試（第 4、7 與 8 步先紅後綠）：`FrameConversionDelegationTest`（`_initialize_conversion_state` 以 `wx.CallAfter`/`wx.CallLater`、frame 作為 view 及其 controller 接線；`on_convert`、Ctrl+Enter、`_on_close` 的委派）與 `FrameExportDelegationTest`（接線；三個進入點保留防護與先儲存，然後呼叫 coordinator）。frame view 方法的測試（第 4 步的 `FrameViewMethodsTest`、第 7 步的 `FrameExportViewMethodsTest`）：`set_conversion_busy`（FindMenu/EnableTop/Enable 呼叫、選單列為 `None`、找不到標籤）、`show_converting_dialog` 的重複呼叫、`close_converting_dialog`、`show_conversion_output`、`show_info`/`show_warning`/`show_error` 的參數、`choose_export_path`、`choose_export_directory`、`confirm_overwrite_all`；以及第 8 步的 `test_show_file_error_formats_the_error_for_the_frame`（M-9）。

## 驗收條件

1. `grep -rn "ConversionCompletionPolicy\|ConversionJobRequest" client` 沒有輸出。
2. `grep -nE "_start_conversion|_complete_conversion|_finish_conversion_|_start_export_conversion|_export_next_document|_write_export_document|_continue_single_export|_show_export_all_result|_missing_default_table_message|_export_document_with_dialog|_conversion_runner|_convert_dialog_timer|_set_conversion_busy|_show_converting_dialog|_close_converting_dialog|_confirm_overwrite_all" client/gui.py` 沒有輸出。
3. `grep -nE "^(import wx|from wx)|^(import|from) gui" client/conversion/presenter.py client/documents/export_coordinator.py client/conversion/jobs.py` 沒有輸出。
4. `grep -n "wx.CallAfter\|wx.CallLater" client/gui.py` 只輸出 `_initialize_conversion_state` 中的行。
5. `grep -nE "\b(ConversionStageError|ConversionOutput|get_public_error_message|ExportContext|ExportBatchResult)\b|conversion\.jobs" client/gui.py` 沒有輸出，且 `grep -n "parent: wx.Window | None = None" client/gui.py` 不會比對到 `_show_file_error`。
6. 第 1 步的特性測試類別除了 fixture helper 之外沒有改變：在第 1 步 commit 與工作目錄之間，以 AST（忽略行號）比對 `ConversionExportFlowsCharacterizationTest` 的每個成員及其模組層級假物件，只回報 `_wire_conversion` 有變更。（`git diff` 無法判斷變更是否位於測試方法內。）
7. `git diff main --stat -- client/locales scripts` 為空；msgid 掃描回報相同的 353 個 msgid。
8. 路線圖驗證通過：`cd client && python3 -m unittest tests.test_conversion_jobs tests.test_export_coordinator tests.test_conversion_presenter tests.test_gui_document_flows -v`。另外 `tests.test_i18n tests.test_wx_stub tests.test_removed_dead_code tests.test_menu_builder tests.test_workspace_service` 也通過。
9. 全套件：754 個測試（696 - 搬移的 27 + 新增的 85）、`failures=1`（只有 P2-5）、`errors=0`，Linux 上 `skipped=9`。
10. stub scope 順序：`tests.test_conversion_presenter` 與 `tests.test_export_coordinator` 單獨執行通過，`tests.test_gui_document_flows tests.test_conversion_presenter tests.test_export_coordinator` 以兩種順序執行都通過；全套件以固定 seed（1-10）打亂順序執行，沒有出現基準已知集合以外的失敗或錯誤行。基準上某些 seed 本來就會在 `test_conversion_service` 出現 8 個錯誤（P1-1 plan 細化第 8 點所述的 `translate` 重新 import 污染，其中包含 P2-5 測試）；新模組會改變打亂結果，所以會碰到它的 seed 也會改變。

## 風險

- **非同步順序偏移**（影響高、可能性中）。在解除忙碌前呼叫 `on_success`、匯出轉換也寫入快取、或把全部匯出第一步也改經 `call_after`，都能通過粗糙的測試。緩解：A 部分以延後執行的 `call_after` 逐回合記錄每個效果，且其測試本體從第 1 步起凍結。
- **job 記帳**（中）。presenter 在 `runner.start` 回傳後才存完成處理。這只因 `call_after` 會延後執行才正確。緩解：已寫明契約；harness 從不在 `start()` 內執行 target；一個以同步 `call_after` 加手動執行緒的 presenter 測試釘住這點。
- **stub 遮蔽**（中）。沒有 `_conversion_presenter` 或 `_export_coordinator` 的 frame 會拿到 no-op 函式而靜默什麼都不做。緩解：每個 frame helper 都明確設定兩者；A 部分檢查真實效果；委派測試使用 `Mock(spec=...)`。
- **frame 上的 view 方法**（低）。`wx.Frame` 子類別上的新 public 名稱可能與 wx 名稱衝突。選用的名稱全為小寫 `snake_case`；wxPython 使用 `CamelCase`。patch `frame._refresh_dual_view` 的測試仍有效，因為 `refresh_dual_view` 委派給它。
- **翻譯綁定**（低）。presenter 與 coordinator 的字串使用它們各自模組的 `_`。patch `gui._` 的測試（只有 P1-2 的對話框測試）仍作用在留在 `gui.py` 的字串上。
- **stub scope 下 import 新模組**（低）。兩個模組都會先由 `gui` 在 stub scope 內 import。緩解：驗收條件 10 的順序檢查（P0 審查 I-1）。
- **測試異動**（中）。22 個 GUI 測試要搬移（27 個測試行，因為其中五個也在子類別中執行），另有四個 P1-2 測試改經 coordinator 進入。緩解：E 部分的表逐一對應；plan 在刪除 frame 方法的同一個 commit 搬移它們。
- **只能在 Windows 驗證的行為**（中，此處無法驗證）。真實執行緒、`wx.CallAfter`、`wx.CallLater`、`ConvertingDialog`、`EnableTop` 與訊息框只在打包後的 app 中執行。見 Windows 驗證債。

## 調查中發現的既有缺陷（本任務不修）

這些在今天的 `main` 上就存在。本任務保留它們，A 部分以 `KNOWN BUG` 註解釘住 1 與 2。

1. **手動轉換的結果會寫入完成當時開啟的那份文件。** 忙碌時 Ctrl+Tab、Ctrl+Shift+Tab 與 Ctrl+O 仍可觸發（frame char hook 仍作用、點字結果編輯器仍啟用）。點字、當下原文編輯器的文字與 dual view 快取都會寫到新開啟的文件。
2. **匯出轉換不檢查是否已有轉換在執行。** 轉換中在點字結果編輯器按 Ctrl+S，或全部匯出鏈在步與步之間有人啟動轉換後繼續，都會啟動第二個 job。第一個 job 的結果被當成過期丟棄，沒有任何訊息；手動轉換的輸出永遠不會更新。
3. **以 HTML 匯出 pending 文件時，寫出的是快取中的 dual view，而不是剛轉換的結果。** 匯出轉換的 `dual_view_segments` 被丟棄，因此 HTML 顯示該文件上一次手動轉換的結果，或「No conversion data」頁面。
4. **全部匯出的摘要沒有翻譯。** `documents/export_results.py` 經由變數把標題與訊息傳給 `_()`，因此不會被抽取；它們的 zh_TW 項目已是過時項目（`#~`）。只有全部成功時的標題（"Export Complete"）有翻譯，因為別處有相同的常值。空訊息的後備文字 "An unknown error occurred." 與 "The selected translation table could not translate this text." 也不是 msgid。
5. **`set_conversion_busy` 依翻譯後的標題尋找選單**（refactor.md 5.3 節）。因為執行期間標籤不會改變，所以能運作。維持原樣。
6. **未被包成 `ConversionStageError` 的 worker 例外會讓 UI 永遠停在忙碌狀態。** 目前只有 `Exception` 以外的 `BaseException` 會如此，因為服務會包住所有 `Exception`。
7. **writer 拋出的 `ValueError` 會中斷全部匯出鏈且沒有摘要。** 從選單無法觸發，因為選單只提供可匯出的格式。

修正 1 與 2 代表忙碌時封鎖那些快捷鍵或把匯出轉換排隊。那是使用者可見的行為改變，應獨立成一個任務；之後 presenter 就是放這個修正的自然位置。

## Windows 驗證債

- 在打包版本上，改動前後各做一次：轉換短文字與長文字（「converting」對話框只在 2 秒後出現，完成時關閉；期間「檔案」與「翻譯」選單、文件清單與原文編輯器停用）；轉換錯誤（錯誤的點字表）及其訊息；長時間轉換中關閉視窗（被否決）。
- 對已轉換與 pending 文件做匯出（DEP、BRL、HTML）；點字結果編輯器中的 Ctrl+S；混合 pending 與已轉換文件的全部匯出，包含既有檔案（覆寫詢問，兩種回答）與唯讀目標檔（部分失敗摘要）。
- 使用 zh_TW 語系：上述所有訊息和以前一樣是中文（摘要仍是英文，缺陷 4）。
- 既有缺陷 1 與 2 的行為與以前相同（長時間轉換中按 Ctrl+Tab 與 Ctrl+S）。
- 沒有選單、對話框或字串變更，因此不需要截圖，也不需要執行 `generate-pot.bat`。

## 不在範圍內

- 修正上述既有缺陷，包括忙碌時封鎖快捷鍵。
- 以保存選單參照取代依標題 `FindMenu`（缺陷 5）。
- 把先儲存防護或選取查詢移出 frame，或搬移 `ConvertingDialog`。
- 修改 `ExportBatchResult` 或標記其字串（屬於在地化變更）。
- Dual View 視窗生命週期、`DualViewFrame` 與瀏覽器檢視。
- 通用 task framework、取消執行中的 job，或進度回報。
- 注入 `ApplicationPaths`（P2-6）、`TranslationResult` 相關工作（P1-5、P2-5）、縮排（P2-8）。
