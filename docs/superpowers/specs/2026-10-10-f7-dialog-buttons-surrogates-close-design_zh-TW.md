# 對話框按鈕在地化、轉換與匯出的 surrogate 防護、關閉重入（F-7）設計

## 目標

任務 F-7 把錯誤訊息與關閉流程的三項強化合在一起（交接文件 `docs/superpowers/history/2026-10-10-02-handoff/HANDOFF.md` 5.2）：

1. **F-W9**（`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`）：對話框按鈕顯示英文。
   - 文件名稱對話框因「已存在」重新顯示時，按鈕是 `OK`／`Cancel`，不是翻譯後的標籤。第一次顯示時有翻譯。
   - 正式程式碼中每個 `wx.MessageBox` 的按鈕都是英文 `OK`。
2. **F-5 審查 M-7**（`docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/review_task.md`）：在編輯框輸入或貼上的 lone surrogate 仍會進入轉換與匯出，因為只有存 `.dep` 時會替換它（F-5 D4）。匯出雙視 HTML 時會拋出 `UnicodeEncodeError`，而 `ExportCoordinator._write_single` 沒有攔截：匯出失敗，沒有任何訊息。
3. **F-5 審查 M-5**：F-5 的 modal 關閉對話框開著時，Windows 登出或關機會送出 `WM_QUERYENDSESSION`，wx 再送一個 close 事件，`BrailleFrame._on_close` 在對話框的 modal 迴圈裡再執行一次。

使用者的決定（2026-10-10，交接文件 5.3；此處不再重新提問），記為 Decided by the user (2026-10-10)：

- **U1.** F-7 是 F-W9＋M-7＋M-5，在 F-6 之後做。
- **U2.** F-W9 只做 (a) 與 (b)。(a) `localize_standard_buttons` 只搜尋對話框自己的子視窗。(b) 正式程式碼中的 `wx.MessageBox` 改用一個共用 helper，以 `wx.MessageDialog` 搭配 `SetOKLabel(_("OK"))`。**不做** (c) 全域 `wx.Locale`。
- **U3.** M-7 依 F-5 D5 的精神：只替換程式讀到的文字，絕不修改編輯框控制項。

另外依交接文件 5.2 的建議，在決定 U1 之下納入範圍：

- 匯出攔截所有 `Exception`。非 `OSError` 的錯誤連同 traceback 寫進 log，使用者看到既有的「匯出失敗」訊息。單一匯出與「全部匯出」的批次都涵蓋。
- M-5 先在 packaged build 上送 `WM_QUERYENDSESSION`／`WM_ENDSESSION` 確認（D9），再加 `_closing` 重入防護：可以拒絕的重入關閉就拒絕；不能拒絕的照 F-5 D8 處理（寫 log 後關閉）。

本任務完成後：

- app 自己的對話框只在該對話框的子視窗中尋找標準按鈕。每個名稱對話框，包括因「已存在」重新顯示的，都顯示翻譯後的標籤：「確定」與「取消」。
- **新發現、由 (a) 一併修好的問題**（見「現況」）：設定或文字處理對話框開著時，字典編輯器的「確定」不再不存檔就關閉。
- app 的每個訊息框都顯示翻譯後的「確定」。是／否訊息框保留 Windows 自己的是／否按鈕，這些按鈕本來就已在地化。每個訊息框的圖示、預設按鈕、按鍵與回傳值都不變。
- 轉換與存檔經由 `replace_lone_surrogates` 讀取編輯框。貼上的 lone surrogate 在轉換、點字輸出、雙視與每種匯出中都變成 U+FFFD。編輯框仍顯示使用者輸入的內容。
- 任何原因的匯出失敗都會顯示既有的失敗訊息，或列在「全部匯出」的摘要中，而且「全部匯出」會繼續處理下一份文件。非預期的錯誤寫進 `gui.log`。
- 關閉對話框開著時又來的關閉會被拒絕，所以不會出現第二個對話框。

新的使用者可見字串：無。用到的每個標籤都已有翻譯：`OK`、`Cancel`、`Failed to export document: {error}`，以及「全部匯出」摘要的文字。msgid 數量維持 F-6 之後 `main` 的數量。撰寫本 spec 時還不知道 F-6 之後的數量；F-6 之前是 357。

非目標：

- 全域 `wx.Locale` 與 wx 自己的翻譯檔（U2）；
- 由 app 翻譯的是／否標籤（D4）；
- 修改編輯框顯示的內容（U3）；
- 字典詞條與文字處理腳本中的 lone surrogate（見「不在範圍內」）；
- 依原因區分的匯出訊息；
- 對 F-5 關閉對話框本身的任何修改。

## 與 F-6 的關係（穩健性）

F-6 正在平行撰寫 spec。它會修改 `client/dialog.py` 的字典管理對話框、新增字串，也可能新增訊息框，並會在 F-7 的 plan 撰寫之前 merge 進 `main`。本 spec 的寫法能承受這些變動：

- 呼叫處以函式名稱標示，不以行號標示。下面的行號取自 `main` `e46ff26`，只供參考。
- **F-6 在正式程式碼中新增的每個 `wx.MessageBox` 呼叫，以及每個沒有設定全部自訂標籤的 `wx.MessageDialog`，也都改用 helper（D3）。** plan 會在 F-6 之後的 `main` 上用「測試計畫」C1 的掃描重新列舉呼叫處，掃描測試也會持續守住這一點。
- F-6 在 `tests/test_dictionary_management_dialog.py` 中 patch `wx.MessageBox` 的測試，也和既有測試一樣改為 patch helper（測試計畫 C）。
- Windows 驗證項目編在 F-6 的項目之後：53–64（plan 的編號；本規格最初使用預留的 `4a`–`4l`）。
- 基準數字（`Ran`、msgid）由 plan 在 F-6 之後的 `main` 上重新量測。

## 規劃後的修正（2026-10-10）

plan（`docs/superpowers/plans/2026-10-10-f7-dialog-buttons-surrogates-close.md`，在 `d10dd94` 的 scratch clone 上 dry run：Task 0–4、6、7 完全重現，每個步驟也以 plan 自己的區塊腳本套用過，GUI 項目 53–64 對同一份程式碼的 packaged build 與 `N-f6b` 都執行過）沒有發現決策 D1–D9 或行為對照表的錯誤。plan 細化本規格之處，以本節為準。下文 Windows 驗證的項目 `4a`–`4l` 重新編為 **53–64**；NVDA 的人工項目是 **65**。

1. **F-6 之後的呼叫處**（`fb7aff9`）：正式程式碼中有 20 處 `wx.MessageBox`（`dialog.py` 7 處、`gui.py` 11 處、`settings/dialogs.py` 2 處），加上「關於」對話框。F-6 新增了**第 21 處**：`BrailleFrame.on_open_dictionary_management`（編輯器的保護：`describe_unreadable_dictionary(...)`、`_("Error")`、`OK | ICON_ERROR`、`parent=self`），與其他各處一樣改用 helper。F-6 在字典管理中「編輯」的錯誤框是第 6 處。F-6 沒有新增 `wx.MessageDialog`，也沒有新增 `FindWindowById`。在 `fb7aff9` 上的行號：`dialog.py` 149、166、489、500、755、758、761（第 1–7 處）；`gui.py` 446、511、705、830、859、1075、1078、1083、1111、1115（第 8–17 處），493（`on_about`，第 20 處），1010（第 21 處）；`settings/dialogs.py` 158、695（第 18、19 處）。D1 的兩處查找在 `dialog.py` 56 與 393。
2. **數量。** 基準是 `Ran 1337`（F-6 之後）；每個遷移步驟之後分別是 `Ran 1342`、`1352`、`1355`、`1361`、`1365`（新增 5、10、3、6、4 個測試，共 28 個），全程 `FAILED (errors=1, skipped=7)`，只有 F-W6。msgid 維持 364 個。測試計畫 A–E 之外的新測試：`test_scan_reads_the_production_modules`（掃描不是空的）、`test_invalid_entry_shows_the_message_on_the_dialog_and_focuses_the_source_text`（第 1 處原本沒有測試）與 `test_importing_binds_no_log_file`（第 7 點）。
3. **掃描測試**（C1–C3）放在新模組 `client/tests/test_wx_call_sites.py`（4 個空白）；命中的位置寫成 `<檔案>:<類別>.<函式>`。
4. **改指向**（C4）在遷移步驟 2 的綠燈步驟中進行，不在紅燈步驟：helper 存在之前 patch `message_box`，每個改指向的測試都會以 `AttributeError` 失敗。記錄的事件名稱保留 `"MessageBox"`。第 18 處既有的測試原本只檢查有訊息框出現，現在也斷言訊息、標題、樣式與 parent（C5）。
5. **編輯器的測試工具**（`test_dictionary_entries_dialog.py`）兩種查找都提供：`FindWindow`（編輯器自己的按鈕），以及模擬 wx 全域搜尋的 `FindWindowById`（測試設定了較早開啟的對話框的按鈕時，先找到那些）。因此既有的編輯器測試在 D1 前後都通過，B3 則設定另一個對話框的按鈕。
6. **Stub scope：** 每個受測程式碼會 import `ui.message_box` 的 scope 都把它列為 `isolate`（`wx_stub.load_speech_dialog`、`test_dialog_validation`、`test_converting_dialog`、`test_settings_dialogs`、`test_gui_document_flows`）。`gui_frame_stubs` 的 `_MessageDialog` 另外加上 `__enter__`／`__exit__` 與回傳 `wx.ID_OK` 的 `ShowModal`，讓沒有 patch 的訊息框仍回答 `wx.OK`，與舊的 stub `wx.MessageBox` 相同。
7. **D6 的 logger** 在寫 log 時才綁定（在 `_log_unexpected_export_error` 裡面），不在 import 時綁定，做法同 F-6 審查 M-6 對 `read_problems` 的修正；`test_export_coordinator` 隔離 `dotexpress.gui`。
8. **D6 也修好 P1-4 的缺陷 7**（以沒有 writer 的格式「全部匯出」時拋出 `ValueError`，沒有摘要）；原本釘住這個 KNOWN BUG 的測試改寫成修好之後的行為。
9. **翻譯檔（D8）：** 逐位元組不變。重新執行 `generate-pot.bat` 產生的模板，與 commit 的模板只差 `POT-Creation-Date` 與 `#:` 參照行（行號移動，以及 `ui/message_box.py` 現在參照 `OK` 與 `Cancel`）；這些留到下一次字串變更重新產生模板時再更新。
10. **GUI 腳本與項目：** `item53.py`（53、56、57）、`item54.py`（54、55）、`item58.py`（58–60）、`item61.py`（61–63），共用 `f7gui.py`；64 直接以 `38`、`39` 執行 F-5 的 `item38.py`（F-5 的 `rerun.py` 不傳這個參數）。56 讓一份文件匯出失敗的方法，是在匯出資料夾放一個名為 `alpha.brl` 的資料夾（覆蓋的問題回答「是」），不是鎖住檔案。61 先轉換 `A` U+FFFD `B` 作為比較：F-7 之後，貼上的 surrogate 得到相同的點字（`⡳⠭⠋⠋⠋⠙`，即 `\xfffd` 的跳脫）；之前是 `⡳⠭⠙⠦⠒⠙`（`\xd83d`）。58 計算程序中標題為 `無法儲存文件` 的頂層視窗數量，並先回答最上層的對話框；F-7 之後呼叫立即回傳（`0.0 s`，結果 0），不是「約 1 秒內」。
11. **62、63 的改前結果：** 沒有訊息，但留下空的 `alpha.html`（`Path.write_text` 在編碼器失敗之前就建立了檔案）；「全部匯出」留下空的 `alpha.html`，沒有 `new.html`，也沒有摘要。F-7 之後，writer 不論因何種錯誤失敗，仍可能留下空的或不完整的檔案（writer 不是原子寫入）；列為後續項目。
12. **plan 已確認 D9：** 在 `D:\dxtest\N-f6b\DotExpress.exe`（`fb7aff9` 的程式碼）上，項目 58 在 3 秒內出現兩個關閉對話框，`SendMessageTimeoutW` 要等內層對話框被回答才回傳（結果 0；兩次執行分別在 3.6 秒與 4.2 秒）。同一個 build 上的項目 55：編輯器顯示 `OK`／`Cancel`，文字處理或設定對話框開著時按它的「確定」都不存檔就關閉（`d1.csv` 只剩表頭）。plan 的 Task 5 在 D7 的 commit 之前重做這兩項。
13. **小修正：** 遷移步驟 5 改為「（本步驟之前：D9，項目 58……）」；驗收標準 2 加上 `tests.test_wx_call_sites` 與 `tests.test_converting_dialog`；標準 7 的檔案清單加上 `test_wx_call_sites.py`、`test_converting_dialog.py` 與 `test_dialog_validation.py`；`_editor_text` 標註為 `control: wx.TextCtrl`；`localize_standard_buttons` 的 docstring 不提 `FindWindowById`，所以直接 `grep` 正式程式碼也找不到。

## 現況（2026-10-10 於 `main` `e46ff26`、worktree `D:\workspace\DotExpress-f7`、Windows 11 26200 驗證）

`$PY` 是 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`（Python 3.13.15、wxPython 4.2.5 msw、wxWidgets 3.2.9）。本 spec 依據的原型在 session scratchpad `...\scratchpad\f7\`，沒有 commit：

- `probe_buttons.py`、`probe_flow.py`、`probe_modeless.py`：按鈕查找與標籤；
- `probe_esc.py`：按鍵；
- `probe_surrogate_conversion.py`：M-7；
- `probe_endsession.py`：M-5。

它們只建立自己的 wx 視窗，並透過 win32 讀取（`EnumChildWindows`、`GetWindowText`、`TDM_CLICK_BUTTON`、`BM_CLICK`）。沒有碰任何其他視窗，也沒有要求登出或關機。

基準：依 F-3 plan Task 0 複製 liblouis runtime 與 MathCAT 後，`cd client && $PY -B -X utf8 -m unittest discover -s tests` 得到 `Ran 1307 tests`、`FAILED (errors=1, skipped=7)`。唯一的 error 是 F-W6（`test_dictionary_name_prompt ... test_case_only_rename_still_renames`）。`dotexpress.po` 中 `OK` -> 「確定」、`Cancel` -> 「取消」，`Apply`、`Close` 也已翻譯。**沒有** `Yes`、`&Yes`、`No`、`&No` 這些 msgid。

### F-W9 (a)：`client/dialog.py`（tab）中的按鈕查找

`localize_standard_buttons(dialog, flags, button_sizer=None)`（`:37-57`）以 `button = dialog.FindWindowById(button_id)` 找到標準按鈕並改標籤。找不到時，退而使用 `button_sizer.GetAffirmativeButton()`、`GetCancelButton()`、`GetApplyButton()`、`GetCloseButton()`。這類查找共有五處（交接文件稱為「5 處使用」）：

| 位置（函式） | 呼叫 |
| --- | --- |
| `DictionaryNameDialog.__init__` | `localize_standard_buttons(self, wx.OK \| wx.CANCEL, button_sizer)` |
| `DocumentNameDialog.__init__` | 同上 |
| `DictionaryEntriesDialog.__init__` | `localize_standard_buttons(self, wx.OK \| wx.CANCEL, button_bar)`，接著 `ok_button = self.FindWindowById(wx.ID_OK)` 與 `ok_button.Bind(wx.EVT_BUTTON, self._on_ok)` |
| `DictionaryManagementDialog.__init__` | `localize_standard_buttons(self, wx.CLOSE, button_bar)` |

另外兩類對話框有標準按鈕：

- `FileIssuesDialog.__init__` 建立 `CreateButtonSizer(wx.OK)`，但從不在地化，所以它的 OK 永遠是英文。
- `AddSymbolDialog`、`TextProcessingDialog`、`DotExpressSettingsDialog` 用明確的 `_("OK")`／`_("Cancel")` 標籤建立按鈕，不受影響。

正式程式碼中其他地方都沒有 `FindWindowById`。

**量測結果**（`probe_buttons.py`、`probe_flow.py`、`probe_modeless.py`）：

- wxPython 的 `wx.Window.FindWindowById(id, parent=None)` 是 static method。以 `dialog.FindWindowById(id)` 呼叫時，對話框不會被當成 `parent` 傳入，所以它會從最舊的開始搜尋所有 top-level 視窗。`dialog.FindWindow(id)` 與 `wx.Window.FindWindowById(id, dialog)` 都回傳對話框自己的按鈕。
- 對話框的 `Destroy()` 只是排定刪除。在下一次 idle 事件之前，該對話框仍在 `wx.GetTopLevelWindows()` 中，而原生訊息框的 modal 迴圈不會執行 wx 的 idle 處理。
- 重現 `BrailleFrame._prompt_for_document_name`（顯示、按確定結束、`Destroy`、「已存在」訊息框、新的對話框；共三輪）：
  - 用 `FindWindowById` 時，第 0 輪有翻譯，第 1、2 輪是 `['OK', 'Cancel']`；
  - 用 `FindWindow` 時，每一輪都有翻譯。
  - 每一輪在訊息框之後，都恰好還有一個已銷毀的名稱對話框留在 top-level 視窗中。**這證實了 F-W9 症狀的成因：** 新對話框的查找改到的是前一個已銷毀對話框的按鈕，它自己的按鈕維持 wx 未翻譯的預設標籤 `OK`／`Cancel`。
- 字典名稱的詢問迴圈（`prompt_dictionary_name_until_success`：名稱對話框、`show_error`、再一次名稱對話框）是同樣的模式，所以有同樣的症狀（讀程式碼推得）。
- wxPython 4.2.5 的 `wx.StdDialogButtonSizer` 只有 `SetAffirmativeButton`、`SetCancelButton`、`SetNegativeButton`，沒有 `Get*Button` 這些 getter。因此在出貨的 wxPython 上，`localize_standard_buttons` 的 sizer 退路永遠找不到按鈕，目前真正有作用的只有 `FindWindowById` 那條查找。

**新發現：字典編輯器的「確定」可能丟掉修改**（以 `probe_modeless.py` 在純 wx 中量測；app 中的路徑由讀程式碼推得，由 GUI 項目 55 確認）。

- `TextProcessingDialog` 與 `DotExpressSettingsDialog` 是非 modal 的單例對話框，各有一個 `wx.Button(self, wx.ID_OK, ...)`。其中之一開著時，使用者仍可以開啟字典管理並選「編輯」。
- 這時 `DictionaryEntriesDialog.__init__` 透過 `self.FindWindowById(wx.ID_OK)` 找到的是**那個對話框**的確定按鈕，並把 `_on_ok` 綁在它上面。`_on_ok` 正是呼叫 `self._model.save(...)` 的處理函式。
- 編輯器自己的確定按鈕維持 wx 的預設處理：`EndModal(wx.ID_OK)`，不存檔。`on_open_dictionary_management` 忽略結果，所以這次在編輯器中做的每個修改都會在沒有任何訊息的情況下遺失。
- 原型：先開一個帶 `ID_OK` 的非 modal 對話框，再開一個仿編輯器的 modal 對話框，然後對編輯器自己的確定按鈕送 `BM_CLICK`。用 `FindWindowById` 時，`ShowModal` 回傳 `ID_OK`，存檔處理函式沒有執行；用 `FindWindow` 時有執行。
- 同一個查找也改到另一個對話框的按鈕標籤，而不是編輯器的，所以編輯器顯示英文 `OK`／`Cancel`。只要這兩個非 modal 對話框之一開著，名稱對話框連第一次顯示都是英文。

### F-W9 (b)：訊息框

正式程式碼中的 `wx.MessageBox` 呼叫（`grep -rn "wx.MessageBox" client --include=*.py`，排除 `tests/`）：**19 處**。

| # | 檔案 | 函式 | 樣式 | 是否使用回傳值 |
| --- | --- | --- | --- | --- |
| 1 | `dialog.py:144` | `AddSymbolDialog._on_ok` | `OK \| ICON_INFORMATION`，`parent=self` | 否 |
| 2 | `dialog.py:161` | `_NameDialog._show_name_error` | `OK \| ICON_INFORMATION`，`parent=self` | 否 |
| 3 | `dialog.py:484` | `DictionaryEntriesDialog._show_duplicate_error` | `OK \| ICON_ERROR`，`parent=self` | 否 |
| 4 | `dialog.py:495` | `DictionaryEntriesDialog._on_ok` | `OK \| ICON_ERROR`，`parent=self` | 否 |
| 5 | `dialog.py:688` | `DictionaryManagementDialog.show_info` | `OK \| ICON_INFORMATION`，`parent=self` | 否 |
| 6 | `dialog.py:691` | `DictionaryManagementDialog.show_error` | `OK \| ICON_ERROR`，`parent=self` | 否 |
| 7 | `dialog.py:694` | `DictionaryManagementDialog.confirm` | `YES_NO \| NO_DEFAULT \| ICON_WARNING`，`parent=self` | `== wx.YES` |
| 8 | `gui.py:445` | `BrailleFrame._show_file_error` | `OK \| ICON_ERROR`，`parent=self` | 否 |
| 9 | `gui.py:510` | `BrailleFrame.on_open_text_processing` | `OK \| ICON_ERROR`，`parent=self` | 否 |
| 10 | `gui.py:704` | `BrailleFrame._prompt_for_document_name` | `OK \| ICON_ERROR`，`parent=self` | 否 |
| 11 | `gui.py:829` | `BrailleFrame.on_delete_document` | `YES_NO \| NO_DEFAULT \| ICON_WARNING`，`parent=self` | `!= wx.YES` |
| 12 | `gui.py:858` | `BrailleFrame.on_delete_all_documents` | `YES_NO \| NO_DEFAULT \| ICON_WARNING`，`parent=self` | `!= wx.YES` |
| 13 | `gui.py:1062` | `BrailleFrame.show_info` | `OK \| ICON_INFORMATION`，`parent=self` | 否 |
| 14 | `gui.py:1065` | `BrailleFrame.show_error` | `OK \| ICON_ERROR`，`parent=self` | 否 |
| 15 | `gui.py:1070` | `BrailleFrame.show_warning` | `OK \| ICON_WARNING`，`parent=self` | 否 |
| 16 | `gui.py:1098` | `BrailleFrame.confirm_overwrite_all` | `YES_NO \| ICON_WARNING`（預設為「是」），`parent=self` | `== wx.YES` |
| 17 | `gui.py:1102` | `_show_application_data_error`（模組層級，啟動時） | `OK \| ICON_ERROR`，沒有 parent | 否 |
| 18 | `settings/dialogs.py:158` | `TextProcessingDialog.on_apply` | `OK \| ICON_ERROR`，`parent=self` | 否 |
| 19 | `settings/dialogs.py:695` | `DotExpressSettingsDialog._collect` | `OK \| ICON_ERROR`，parent `self` 以**位置參數**傳入 | 否 |

正式程式碼中的 `wx.MessageDialog`：

- `BrailleFrame.on_about`（`gui.py:492`，`OK | ICON_INFORMATION`，沒有設定標籤）：同樣顯示英文 `OK`（下面的第 20 個呼叫處）。
- F-5 的 `BrailleFrame._ask_after_close_save_failure` 三個標籤都有設定，是正確的。

每個呼叫都傳入明確的圖示。縮排：`dialog.py` 與 `gui.py` 用 tab，`settings/dialogs.py` 用 4 個空白。

**量測結果**（`probe_buttons.py`、`probe_esc.py`）。wxMSW 把這些訊息框顯示為 task dialog。

| 訊息框 | 按鈕（視窗文字） | 焦點 | 回傳 |
| --- | --- | --- | --- |
| `wx.MessageBox(..., OK \| ICON_ERROR)` | `OK`（英文） | `OK` | `wx.OK`；Esc 與 Enter 都會關閉並回傳 `wx.OK` |
| `wx.MessageDialog(..., OK \| ICON_ERROR)` ＋ `SetOKLabel(<OK 的譯文>)` | 「確定」 | 該按鈕 | `ID_OK`；Esc 與 Enter 都以 `ID_OK` 關閉；`SetOKLabel` 回傳 `True` |
| 同上，`parent=None` | 「確定」 | - | `ID_OK` |
| `wx.MessageBox(..., YES_NO \| NO_DEFAULT \| ICON_WARNING)` | 「是(&Y)」、「否(&N)」：**Windows 自己的通用按鈕**，已是系統語言 | 否 | IDNO 時為 `wx.NO`（`8`） |
| `wx.MessageDialog(..., YES_NO \| NO_DEFAULT ...)` ＋ `SetYesNoLabels(...)` | 傳入的標籤 | 否 | `ID_YES`／`ID_NO` |
| `wx.MessageDialog(..., YES_NO ...)`（預設為「是」）＋ `SetYesNoLabels(...)` | 傳入的標籤 | 是 | IDNO 時為 `ID_NO` |

結論：

- wx 把只有確定的訊息框中的 OK 畫成自訂按鈕，標籤取自 wx 自己的翻譯檔，而 app 從未載入它，所以是英文 `OK`。
- 是／否訊息框使用 Windows 的通用按鈕，由系統決定標籤。在這台 zh-TW 系統上已是中文。
- 只要設定了一個標籤，wx 就把該訊息框的每個按鈕都畫成自訂按鈕，所以同時有確定與取消的訊息框必須兩個標籤都設定。
- `wx.MessageBox` 等於 `wx.MessageDialog(parent, message, caption, style).ShowModal()`，再把結果對應為 `ID_OK -> OK`、`ID_YES -> YES`、`ID_NO -> NO`、`ID_CANCEL -> CANCEL`。量到的回傳值與此相符。

既有的 GUI 自動化（`docs/superpowers/history/2026-10-09-03-windows-verification/auto/dx.py` 的 `dismiss`、`docs.py`、`dicts.py`，以及 F-5 的 `f5gui.dismiss`）都會按 `OK` 或「確定」，`dx.dismiss` 也會按是／否標籤。所以 F-7 之後舊腳本仍可使用。

### M-7：讀取編輯框的位置（`client/gui.py`）

- `BrailleFrame._save_open_document` 把 `text=self.input_txt.GetValue()` 與 `braille=self.output_txt.GetValue()` 傳給 `save_open_document`。F-5 D4 之後才在 `prepare_document_for_save` 與 `_normalized` 中替換 lone surrogate。
- `BrailleFrame.get_source_text` 原樣回傳 `self.input_txt.GetValue()`。`ConversionPresenter.convert`（手動轉換）與 `_complete_manual` 都呼叫它。`_complete_manual` 把結果存成 controller 中開啟文件的文字。

`input_txt` 與 `output_txt` 沒有其他的 `GetValue()`。

**量測結果**（`probe_surrogate_conversion.py`，使用 worktree 的 runtime 複本中真正的 liblouis，預設表格，`lang="zh_TW"`）。輸入為 `A`＋U+D83D＋`B`、U+4E2D U+D83D U+6587、`abc` U+4E2D U+6587 U+DC00 ` def`，以及單獨的 U+D83D。

- 轉換成功。點字以 liblouis 表示未定義字元的跳脫寫法（`\xd83d`，以點字方格呈現）顯示該 surrogate，顯示文字中沒有 surrogate。
- 寫出結果：BRL 成功，DEP 成功（F-5 D4）。**HTML（雙視）拋出 `UnicodeEncodeError: 'utf-8' codec can't encode character '\ud83d' ... surrogates not allowed`**，因為雙視的 segment 帶著原文。
- 先把輸入經過 `replace_lone_surrogates`，三種寫出都成功，點字變成 U+FFFD 的跳脫寫法（`\xfffd`）。

到達 HTML 寫出器的路徑：

- 匯出開啟中的文件：`on_export_document` 會先存檔，之後 controller 持有乾淨的文字。但 `ExportContext.dual_view_results` 是上一次以編輯框原始文字轉換所得的 segment。
- 同一份文件的「全部匯出」，經由同樣的 segment。

`ExportCoordinator._write_single` 只攔截 `OSError`，所以例外會離開選單處理函式。wx 把它印到 packaged build 沒有的 console，使用者什麼都看不到。`_export_next` 中的 `write_document` 也只攔截 `OSError`：批次停在這份文件，不顯示摘要。瀏覽器中的雙視（`_open_dual_view_in_browser`）已攔截 `Exception`，所以那裡使用者會看到「開啟雙視失敗：...」。

### M-5：關閉重入

`BrailleFrame._on_close`（`gui.py:1010`）：

1. 先做轉換檢查。
2. 執行 `_save_open_document_before_close(evt.CanVeto())`（F-5 D6／D8）。可否決的關閉存檔失敗時，顯示 `_ask_after_close_save_failure`，它執行一個 modal task dialog。
3. 接著否決事件，或執行清理並 `evt.Skip()`。

沒有重入防護。只有主視窗綁定這個處理函式（`self.Bind(wx.EVT_CLOSE, self._on_close)`）。app 沒有覆寫 wx 的 session 結束處理；`BrailleApp` 只定義 `OnInit` 與 `OnExit`。

**量測結果**（`probe_endsession.py`）。一個視窗的 close 處理函式顯示 task dialog（來自 `WM_CLOSE` 的可否決關閉）。接著另一個執行緒以 `SendMessageTimeoutW` 對該視窗送出 `WM_QUERYENDSESSION`（`lParam = ENDSESSION_LOGOFF`）。

- **處理函式照今天的寫法：** 第一個對話框開著時，close 處理函式被第二次進入（`depth 2`、`CanVeto True`），第二個對話框疊在第一個上面打開；兩個都被計數到。`SendMessageTimeoutW` 直到內層對話框被回答才返回：結果 `0`（不可結束），約 2 秒後，也就是測試回答所花的時間。
- **加上會否決可否決重入的 `_closing` 防護：** 第二次進入立刻否決。`SendMessageTimeoutW` 在同一個 tick 內返回，結果 `0`。始終只有一個對話框，之後正常回答。
- **對話框開著時送 `WM_ENDSESSION`（`wParam = TRUE`）：** 兩種寫法下程序都立刻以結束碼 0 結束，而且**沒有第二個 close 事件**。wx 3.2 預設的 `wxApp::OnEndSession` 呼叫 `OnExit()` 與 `exit()`，而不是關閉視窗。磁碟上的包此時是上次成功的存檔（F-3 原子寫入）。因此 F-5 D8 所說「wx 只會在可否決的 query-end-session 關閉之後才送不可否決的關閉」並不符合 wx 3.2.9：session 結束從不產生不可否決的 close 事件。不可否決的關閉只來自 `Close(force=True)`，而 DotExpress 從不呼叫它。D8 的程式路徑保留為防禦分支。

因此 `WM_QUERYENDSESSION` 的 M-5 已在純 wx 中確認：巢狀對話框，以及巢狀的「不儲存就關閉」在外層對話框的 modal 迴圈還在時銷毀視窗。packaged build 在撰寫防護之前，由 D9／項目 58 檢查。

### 釘住今天行為的測試

- `tests/test_dialog_display.py`：三個 `localize_standard_buttons` 的測試設定 `dialog.FindWindowById`，其中一個走 sizer 退路。
- `tests/test_dictionary_entries_dialog.py`（`editor.FindWindowById = self._find_window_by_id`，約第 330 行）供應編輯器確定按鈕的綁定。
- patch 或記錄 `wx.MessageBox` 的地方：
  - `tests/test_dialog_validation.py`（約第 264-285、363 行）；
  - `tests/test_dictionary_entries_dialog.py`（harness 的 `MessageBox=self._message_box`）；
  - `tests/test_dictionary_management_dialog.py`（約第 365-393 行）；
  - `tests/test_gui_document_flows.py`（超過 20 處，包括 `DocumentWorkspaceFlowsCharacterizationTest` 的 `setUp`）；
  - `tests/test_settings_dialogs.py`（約第 174、451 行）。
- `tests/test_wx_stub.py` 測試 stub 自己的 `MessageBox`，維持不變。
- `tests/test_export_coordinator.py` 釘住兩條匯出路徑對 `OSError` 的處理，以及該模組既不 import `wx` 也不 import `gui`。
- F-5 的關閉測試（`test_close_*`，約第 2098-2372 行；`test_close_asks_presenter_before_saving`，約第 3910 行）釘住關閉流程。

## 決定

**D1. 對話框的標準按鈕只在它自己的子視窗中查找（U2 a）。**

- `localize_standard_buttons` 中的 `button = dialog.FindWindowById(button_id)` 改為 `button = dialog.FindWindow(button_id)`。
  - `wxWindow::FindWindow(id)` 搜尋該視窗與其所有後代，所以找得到 `CreateButtonSizer` 為這個對話框建立的按鈕，不會找到別的。
  - 簽章、旗標表、標籤與 `button_sizer` 退路都不變。退路在 wxPython 4.2.5 上沒有作用（見「現況」），但無害，它的測試也保留（Decided by orchestrator with the recommended default; user may override before merge）。
- `DictionaryEntriesDialog.__init__` 中的 `ok_button = self.FindWindowById(wx.ID_OK)` 改為 `ok_button = self.FindWindow(wx.ID_OK)`。這修好修改遺失的問題。
- `FileIssuesDialog.__init__` 在既有的 `if button_sizer:` 區塊內呼叫 `localize_standard_buttons(self, wx.OK, button_sizer)`，讓它的 OK 也有翻譯。這是把使用者的決定 U2 套用到交接文件沒有列出的對話框（Decided by orchestrator with the recommended default; user may override before merge）。
- 之後正式程式碼中不再有 `FindWindowById`（掃描測試 C3）。

否決的做法：

- `wx.Window.FindWindowById(id, dialog)`：正確，但容易再寫錯，而且交接文件指名的是 `FindWindow`。
- sizer 的 getter：wxPython 4.2.5 中不存在。
- 每個對話框改用明確的 `wx.Button(self, wx.ID_OK, _("OK"))` 按鈕：每個對話框都要多寫程式碼，結果相同。

**D2. 一個共用 helper：`client/ui/message_box.py`（新檔，4 個空白）（U2 b）。**

```python
"""``wx.MessageBox`` with the application's own button labels (F-7, F-W9).

wx draws the OK button of a message box with a label from its own catalog, which
DotExpress does not load, so ``wx.MessageBox`` shows an English "OK". Yes and No
are Windows' common buttons, which Windows labels in the system language.
"""

from __future__ import annotations

import wx

from i18n import _


def message_box(message: str, caption: str, style: int, parent: wx.Window | None = None) -> int:
    """Show a message box like ``wx.MessageBox``: same arguments and return values.

    Returns ``wx.OK``, ``wx.YES``, ``wx.NO`` or ``wx.CANCEL``. An OK button (and a
    Cancel button next to it) gets the translated label; a Yes/No box keeps the
    system's labels.
    """
    with wx.MessageDialog(parent, message, caption, style) as dialog:
        if not style & wx.YES_NO:
            if style & wx.CANCEL:
                dialog.SetOKCancelLabels(_("OK"), _("Cancel"))
            else:
                dialog.SetOKLabel(_("OK"))
        answer = dialog.ShowModal()
    return {wx.ID_OK: wx.OK, wx.ID_YES: wx.YES, wx.ID_NO: wx.NO}.get(answer, wx.CANCEL)
```

- **直接替換的契約。** 參數的順序與意義和 `wx.MessageBox(message, caption, style, parent)` 相同，包括以位置傳入的 `parent`（第 19 處）。回傳值是 wx 自己的對應（見「現況」）；`ID_CANCEL` 與任何非預期的值都對應為 `wx.CANCEL`，和 `wxMessageBox` 一樣。不支援 `wx.HELP`，也沒有呼叫處用到。樣式原樣傳給 `wx.MessageDialog`，所以圖示、`NO_DEFAULT` 與預設為「是」都不變。
- **標籤。**
  - 只有確定：`SetOKLabel(_("OK"))`。
  - 確定加取消（目前沒有呼叫處；給未來的呼叫者）：`SetOKCancelLabels(_("OK"), _("Cancel"))`。設定一個標籤後每個按鈕都會變成自訂按鈕（已量測），所以兩個都要設定。
  - 是／否：不設定任何標籤（D4）。
  - setter 回傳 `False`（沒有出貨平台會這樣）時保留平台的標籤；訊息框仍可正常使用。
- **按鍵與無障礙。** 仍是 wx 先前顯示的同一種 task dialog，只是確定改為翻譯後的標籤：Enter 與 Esc 都會關閉只有確定的訊息框（已量測），焦點從預設按鈕開始，NVDA 照舊朗讀，只是讀出新標籤。
- `from __future__ import annotations` 讓 `wx.Window` 註記不被求值，所以這個模組在每種測試 stub 下都能乾淨地 import。

否決的做法：

- `wx.GenericMessageDialog`：不是原生對話框，焦點與無障礙行為不同。
- 對 task dialog 呼叫 `localize_standard_buttons`：它沒有 wx 的子按鈕。
- 每個呼叫處各自 `SetOKLabel`：二十份重複的程式碼。

**D3. 每個訊息框都經過 helper。**

- 19 處 `wx.MessageBox(...)`（見「現況」的表）改為 `message_box(...)`，參數相同。
- `BrailleFrame.on_about` 改為 `message_box(about.aboutMessage, _("About DotExpress"), wx.OK | wx.ICON_INFORMATION, parent=self)`；這是第 20 個呼叫處。
- `dialog.py`、`gui.py`、`settings/dialogs.py` 以 `from ui.message_box import message_box` import 它。每個呼叫保留原本的訊息、標題、樣式、parent 與回傳值的用法，所以確認框仍與 `wx.YES` 比較。
- F-5 的 `_ask_after_close_save_failure` 維持直接使用 `wx.MessageDialog`，因為它已設定所有標籤。
- **F-6：** F-6 在正式程式碼中新增的任何 `wx.MessageBox` 呼叫，或任何沒有設定全部標籤的 `wx.MessageDialog`，都以同樣方式改寫。
- 之後正式程式碼的模組中不再有 `wx.MessageBox`。每個正式程式碼中的 `wx.MessageDialog` 不是在 `ui/message_box.py`，就是在 `BrailleFrame._ask_after_close_save_failure`（掃描測試 C1、C2）。

**D4. 不新增字串；是／否維持系統的按鈕。**

- helper 只用到 `OK` 與 `Cancel`，兩者都已有翻譯。
- 是／否訊息框（第 7、11、12、16 處）不設定 app 的標籤。它們已顯示系統在地化的是／否（在這台 zh-TW Windows 上量測），而 app 自己的標籤需要兩個新 msgid。在其他顯示語言的 Windows 上，它們維持該語言，和今天完全相同。
- （Decided by orchestrator with the recommended default; user may override before merge。由 app 翻譯的 `&Yes`／`&No` 可作為一個小的後續項目，需要兩個新 msgid。）

**D5. 編輯框經由 surrogate 替換讀取（M-7、U3）。** `BrailleFrame` 新增：

```python
def _editor_text(self, control) -> str:
	"""The control's text with each lone surrogate replaced by U+FFFD (F-7, M-7); the control is not changed."""
	return replace_lone_surrogates(control.GetValue())
```

- `_save_open_document` 傳入 `text=self._editor_text(self.input_txt)` 與 `braille=self._editor_text(self.output_txt)`。
- `get_source_text` 回傳 `self._editor_text(self.input_txt)`。
- `replace_lone_surrogates` 來自 `documents.workspace`，`gui.py` 已經從這個模組 import 其他名稱。乾淨的文字原物件回傳，檢查 550,000 個字元約需 1.7 ms（F-5 的量測）。
- 不呼叫任何 `SetValue`（U3、F-5 D5）：游標不移動，NVDA 不重讀。
- documents 層的 F-5 D4 保留，作為每個寫出器的第二道防線。
- 影響：
  - 轉換、轉換出的點字、雙視 segment，以及 `_complete_manual` 存進 controller 的副本，都持有 U+FFFD。
  - 這個字元的點字從 liblouis 對 surrogate 的跳脫寫法（`\xd83d`）變成對 U+FFFD 的跳脫寫法（`\xfffd`）。兩者代表的都是使用者看不到、而且從來不是合法文字的字元。
  - F-5 D2 的存檔比較不變，因為 `prepare_document_for_save` 拿到的就是它先前自己產生的同一段文字。
- 不記 log：這個替換是預期中的修復，和 F-5 D5 相同。

**D6. 匯出回報每一種失敗（M-7、交接文件 5.2）。** 在 `client/documents/export_coordinator.py`（4 個空白）：

- `_write_single`：`except OSError` 改為 `except Exception as exc`。呼叫 `self._log_unexpected_export_error(exc)`，並以標題 `_("Error")` 顯示既有的 `_("Failed to export document: {error}").format(error=exc)`。不顯示成功訊息。
- `_export_next.write_document`：`except OSError` 改為 `except Exception as exc`，同樣記 log，並呼叫 `result.add_failure(document.name, str(exc))`。批次接著以 `continue_batch()` 繼續，和 `OSError` 時完全相同。摘要會列出這筆失敗。
- `_log_unexpected_export_error(error)` 只記非 `OSError` 的錯誤，和 F-3 審查 M-3 對存檔的做法相同：`logger.error("Unexpected error while exporting a document", exc_info=error)`。`OSError` 是預期中的錯誤，訊息已完整說明。
- 模組層級的 `logger = get_logger("dotexpress.gui", "gui.log")`，搭配 `from log import get_logger`。這和 `gui.py` 是同一個 logger 與檔案，所以所有非預期的錯誤都在同一個檔案中（Decided by orchestrator with the recommended default; user may override before merge）。這個模組仍不 import `wx` 或 `gui`，所以 `test_module_imports_neither_wx_nor_gui` 維持通過。
- 兩條路徑都涵蓋：匯出已轉換的文件，以及為匯出而轉換後的 `on_success` 回呼。轉換失敗的回呼不變。
- 否決：只攔截 `UnicodeEncodeError`（審查提出的較窄選項）。寫出器的其他 bug 仍會靜默失敗，而 F-3 M-3 正是為存檔修好了這種情況。

**D7. 關閉進行中又來的關閉會被否決（M-5）。** 在 `client/gui.py`（tab）的 `BrailleFrame`：

```python
	# Class attributes, so frames built without __init__ (tests) have them too (F-7, M-5).
	_closing = False
	_close_finished = False

	def _on_close(self, evt: wx.CloseEvent):
		if self._closing:
			self._on_close_reentered(evt)
			return
		self._closing = True
		try:
			self._close(evt)
		finally:
			self._closing = False

	def _close(self, evt: wx.CloseEvent) -> None:
		if self._conversion_presenter.is_running() and evt.CanVeto():
			evt.Veto()
			return
		may_close = self._save_open_document_before_close(evt.CanVeto())
		if self._close_finished:
			# A nested close that could not be vetoed already closed the frame (M-5).
			return
		if not may_close:
			evt.Veto()
			return
		self._finish_close(evt)

	def _on_close_reentered(self, evt: wx.CloseEvent) -> None:
		"""A close event while another close is still asking (F-7, M-5).

		Windows sends WM_QUERYENDSESSION again while the close dialog's modal loop runs.
		A close that can be vetoed is vetoed: the open dialog decides. One that cannot
		follows F-5 D8: one save attempt, a logged failure, and the frame closes.
		"""
		if evt.CanVeto():
			evt.Veto()
			return
		self._save_open_document_before_close(False)
		self._finish_close(evt)

	def _finish_close(self, evt: wx.CloseEvent) -> None:
		self._close_finished = True
		self.close_converting_dialog()
		if self._dual_view_frame is not None:
			viewer = self._dual_view_frame
			self._dual_view_frame = None
			viewer.Destroy()
		evt.Skip()
```

`_save_open_document_before_close` 在 `answer = self._ask_after_close_save_failure(error)` 之後多一行：`if self._close_finished: return True`。巢狀的不可否決關閉已完成時，外層迴圈不重試也不再詢問。之後 `_close` 不呼叫 `Veto` 也不呼叫 `Skip` 就返回。

- **可否決的重入**（量測到的情況：對話框開著時送 `WM_QUERYENDSESSION`）：巢狀事件立刻被否決。不會第二次存檔，不會出現第二個對話框，也不記 log（這是預期中的情況，不是錯誤）。真的登出時，Windows 會把 DotExpress 列為阻止登出的程式。使用者回到仍開著的對話框，由它決定。這符合 F-5 B 的用意（絕不在無聲中丟掉修改）。
- **不可否決的重入**（防禦用：wx 3.2.9 的 session 結束不會產生這種事件，見「現況」）：照 F-5 D8 做一次。嘗試存檔，失敗就記 `Failed to save the open document while closing`，接著執行清理與 `Skip`。
- `_closing` 在 `finally` 中重設，所以否決或例外之後的下一次關閉仍正常。`_close_finished` 從不重設：視窗即將消失。
- 沒有重入時的行為逐行不變：轉換檢查、F-5 的對話框迴圈、D8、清理與 `Skip`。
- 否決的做法：
  - 對話框期間以 `Unbind` 停用處理函式：這樣重入的關閉會走 wx 的預設處理，直接銷毀視窗。
  - 用計數器而不是旗標：允許的層級從來不會超過一層。

**D8. 不修改翻譯檔。** 不重新產生 `dotexpress.pot`、`.po`、`.mo`。plan 檢查 AST msgid 掃描與 `msgfmt --statistics` 在前後得到相同的數字。

**D9. 撰寫 D7 之前，先在 packaged build 上確認 M-5。**

1. 實作 agent 建置 F-7 之前的 `main`（F-6 之後；或沿用 F-6 任務的 build）。
2. 對它執行項目 58（見「Windows 驗證」）。
3. 把巢狀對話框與被擋住的 `SendMessageTimeoutW` 記錄在 history 資料夾中。
4. 然後才撰寫 D7 的 commit。

若 packaged build **沒有**重入，agent 在 D7 的 commit 之前停下來回報協調者，因為純 wx 的原型預測它會重入。訊息只送給 DotExpress 自己的主視窗。絕不呼叫 `ExitWindowsEx`、`InitiateSystemShutdownEx`、`shutdown.exe` 或 `logoff`。

## 各路徑改前與改後的行為

| 路徑 | 改前 | 改後 |
| --- | --- | --- |
| 名稱對話框（文件或字典）第一次顯示，沒有開其他對話框 | 翻譯後的確定／取消 | 相同 |
| 因「已存在」重新顯示的名稱對話框 | 英文 `OK`／`Cancel`（F-W9） | 有翻譯 |
| 設定或文字處理對話框開著時的任何名稱對話框或字典編輯器 | 英文 `OK`／`Cancel`；改到的是另一個對話框的按鈕 | 有翻譯；另一個對話框不受影響 |
| 設定或文字處理對話框開著時，字典編輯器按確定 | **不存檔就關閉；修改在無聲中遺失** | 存檔（或顯示「儲存失敗：...」），然後關閉 |
| 其他情況下字典編輯器按確定 | 存檔、關閉 | 相同 |
| 檔案問題對話框（匯入時略過檔案） | 英文 `OK` | 有翻譯 |
| 每個只有確定的訊息框（第 1–6、8–10、13–15、17–20 處） | 英文 `OK`；Enter 或 Esc 關閉 | 翻譯後的確定；Enter 或 Esc 關閉；文字、標題、圖示與擁有者相同 |
| 是／否確認框（第 7、11、12、16 處） | 系統的是／否，預設為「否」（7、11、12）或「是」（16） | 相同（同一個對話框；不設定標籤） |
| F-5 關閉對話框 | 重試／不儲存就關閉／取消 | 相同 |
| 輸入含 lone surrogate 時轉換 | 成功；點字顯示 surrogate 的跳脫寫法 | 成功；點字顯示 U+FFFD 的跳脫寫法；編輯框仍持有該 surrogate |
| 之後匯出 HTML（雙視） | `UnicodeEncodeError` 逸出；沒有訊息、沒有檔案 | 成功；檔案中是 U+FFFD |
| 之後「全部匯出」 | 停在這份文件；沒有摘要 | 完成；照常顯示摘要 |
| 匯出時寫出器拋出任何非 `OSError`（bug） | 逸出；沒有訊息；「全部匯出」停止 | 「匯出文件失敗：...」（單一）或列在摘要中（批次）；traceback 寫進 `gui.log`；批次繼續 |
| 匯出時寫出器拋出 `OSError` | 訊息／摘要 | 相同；不記 log |
| 編輯框含 lone surrogate 時存檔 | 以 U+FFFD 存檔（F-5） | 相同（讀取時也替換） |
| 關閉對話框開著時收到 `WM_QUERYENDSESSION` | 巢狀 `_on_close`：再存一次、第二個對話框；Windows 一直等到內層被回答 | 立刻否決；只有一個對話框；Windows 得到「不可結束」 |
| 沒有關閉進行中時收到 `WM_QUERYENDSESSION` | 照 F-5 的 `_on_close`（關閉，或存檔失敗時詢問） | 相同 |
| `WM_ENDSESSION`（強制登出） | wx 呼叫 `OnExit` 並結束；沒有 close 事件；包＝上次成功的存檔 | 相同 |
| 關閉進行中時來了不可否決的關閉（`Close(True)`，app 沒有使用） | 巢狀執行 D8，之後外層對話框在正被銷毀的視窗上繼續 | D8 一次；外層在對話框返回後停止 |

## 各檔案的設計

### `client/ui/message_box.py`（新檔，4 個空白）

D2。模組 docstring 如 D2 所示。

### `client/dialog.py`（tab）

- `localize_standard_buttons`：`dialog.FindWindow(button_id)`（D1）。docstring 加上「Only the dialog's own children are searched (F-W9).」
- `DictionaryEntriesDialog.__init__`：`self.FindWindow(wx.ID_OK)`（D1）。
- `FileIssuesDialog.__init__`：`localize_standard_buttons(self, wx.OK, button_sizer)`（D1）。
- `from ui.message_box import message_box`；第 1–7 處呼叫它（D3）。

### `client/gui.py`（tab）

- `from ui.message_box import message_box`；第 8–17 處與 `on_about` 呼叫它（D3）。
- `_editor_text`、`_save_open_document`、`get_source_text`（D5）；在既有的 `from documents.workspace import (...)` 中加入 `replace_lone_surrogates`。
- `_closing`、`_close_finished`、`_on_close`、`_close`、`_on_close_reentered`、`_finish_close`，以及 `_save_open_document_before_close` 中那一行檢查（D7）。

### `client/settings/dialogs.py`（4 個空白）

`from ui.message_box import message_box`；第 18、19 處呼叫它，第 19 處仍以位置傳入 `self`（D3）。

### `client/documents/export_coordinator.py`（4 個空白）

D6：`from log import get_logger`、`logger`、`_log_unexpected_export_error`，以及兩個 `except Exception` 區塊。模組 docstring 加上「Every write failure is reported: an `OSError` by its message, anything else also with its traceback in `gui.log`.」

### `client/tests/wx_stub.py`（4 個空白）

- `gui_frame_stubs()`：`_MessageDialog` 新增 `SetOKLabel`、`SetOKCancelLabels`、`SetYesNoLabels`，都回傳 `True`（真實的簽章）。
- 每個受測程式碼會 import `ui.message_box` 的 `StubScope`（直接，或經由 `dialog`、`gui`、`settings.dialogs`），都要透過 `isolate` 或其 `evict` 規則，讓這個模組不留在共用的模組表中。否則 scope 會拋出 `StubLeakError`。各 scope 用哪種做法由 plan 決定。

### 不修改

- F-5 的關閉對話框，以及 `_save_open_document_before_close` 中那一行以外的部分；
- `documents/workspace.py`、`documents/workspace_service.py`、`documents/formats.py` 與 `ui/conversion_presenter.py`；
- 雙視相關模組；
- `client/locales/`、`client/braille/` 與 `client/dictionary/`；
- 包的格式。

## 維持不變的部分

- 每個訊息框的訊息、標題、圖示、預設按鈕與擁有者。是／否的標籤。程式碼依訊息框取得的每個回傳值與判斷。
- 每個名稱對話框的第一次顯示。每個對話框的版面、焦點與加速鍵。
- 不含 lone surrogate 的文字：轉換輸入、點字、包與匯出都逐位元組相同。
- 編輯框的內容。F-5 的存檔比較、關閉對話框、D8，以及轉換進行中被否決的關閉。
- 成功或以 `OSError` 失敗的匯出：相同的訊息與摘要。
- 兩個 fixture 的 sha256。翻譯檔。

## 使用者可見字串

沒有新字串（D4、D8）。改變的標籤：

| 位置 | 改前 | 改後（msgid） |
| --- | --- | --- |
| 每個只有確定的訊息框與「關於」對話框的確定按鈕 | `OK` | `OK` -> 「確定」 |
| 重新顯示的名稱對話框；設定或文字處理對話框開著時的任何標準按鈕對話框 | `OK`／`Cancel` | `OK`、`Cancel` -> 「取消」 |
| 檔案問題對話框 | `OK` | `OK` |

## 測試計畫

TDD：每一步的新測試先寫，並以說明的原因失敗，然後程式碼讓它們通過。每個測試檔維持原本的縮排；`test_dialog_display.py` 用 tab，下面提到的其他檔案用 4 個空白。測試只用暫存目錄，絕不碰 `client/dictionary/`、`client/workspace/`、`client/config.json` 或 `client/log/`。每個會讓程式碼寫 log 的測試都用 `assertLogs`，它會替換 handler，所以不會寫入 `client/log/gui.log`。

### A. helper（`client/tests/test_message_box.py`，新檔，4 個空白）

這個模組有自己的 `StubScope`，搭配最小的假 `wx`：

- `OK`、`CANCEL`、`YES`、`NO`、`YES_NO`（`YES | NO`）、`NO_DEFAULT`、各個 `ICON_*` 旗標、`ID_OK`、`ID_CANCEL`、`ID_YES`、`ID_NO` 各有不同的值；
- 一個會記錄的 `MessageDialog`：支援 `with`，記錄建構參數、每個 setter 呼叫與 `ShowModal`；從佇列取答案，除非另外指定，setter 都回傳 `True`。

`ui.message_box` 被 isolate。翻譯經由 `i18n` 使用真正的翻譯檔。

1. `test_ok_box_sets_the_translated_ok_label`：`(parent, message, caption, OK | ICON_ERROR)` 原樣傳到 `MessageDialog`。`SetOKLabel(_("OK"))` 是唯一的 setter，且 `_("OK")` 是 zh-TW 的譯文。`ShowModal` 只呼叫一次，對話框有被關閉（`__exit__`）。`ID_OK` 時回傳 `OK`。紅燈原因：模組不存在。
2. `test_ok_cancel_box_sets_both_labels`：`SetOKCancelLabels(_("OK"), _("Cancel"))`；`ID_CANCEL` -> `CANCEL`。
3. `test_yes_no_box_keeps_the_system_labels`（subTest：有 `NO_DEFAULT`、沒有）：不呼叫任何 setter，樣式原樣傳入，`ID_YES` -> `YES`、`ID_NO` -> `NO`。
4. `test_unexpected_result_maps_to_cancel`（`ID_CANCEL` 與一個未知的 id）。
5. `test_parent_can_be_omitted_or_positional`：`message_box(m, c, s)` 傳入 `None`；`message_box(m, c, s, frame)` 傳入 `frame`。
6. `test_a_label_the_platform_refuses_still_shows_the_box`：setter 回傳 `False`；`ShowModal` 仍被呼叫一次。

### B. 按鈕查找（`client/tests/test_dialog_display.py`，tab；`client/tests/test_dictionary_entries_dialog.py`）

1. 三個既有的 `localize_standard_buttons` 測試改為設定 `dialog.FindWindow`，不再設定 `dialog.FindWindowById`。紅燈原因：今天的程式碼呼叫 `FindWindowById`，它是回傳另一個 `Mock` 的 `Mock`，所以預期的按鈕沒有被設定標籤。sizer 的測試維持讓 `FindWindow` 回傳 `None`。
2. `test_localize_ignores_buttons_of_other_windows`：`dialog.FindWindowById` 回傳外部的按鈕，`dialog.FindWindow` 回傳對話框自己的按鈕。只有自己的按鈕被改標籤，而且 `FindWindowById` 沒有被呼叫。
3. `test_entries_dialog_binds_ok_to_its_own_button`：harness 的 `editor.FindWindowById` 掛鉤改為 `editor.FindWindow`。新測試讓 `FindWindowById` 回傳外部的按鈕，檢查 `_on_ok` 綁在 `FindWindow` 回傳的按鈕上。
4. `test_file_issues_dialog_localizes_its_ok_button`（放在 stub 能建立 `FileIssuesDialog` 的模組中，由 plan 決定）：以 `(dialog, wx.OK, button_sizer)` 呼叫 `localize_standard_buttons`。

### C. 呼叫處

1. `test_no_production_module_calls_wx_message_box`：以 AST 掃描 `client/` 下每個 `.py`，排除 `tests/`、`.venv/`、`build/`、`dist/`、`mathcat/` 與 `braille/liblouis/`。找不到名稱 `wx` 上的 `MessageBox` 屬性。紅燈原因：19 處命中（F-6 若有新增則更多）。
2. `test_message_dialogs_are_the_helper_or_set_every_label`：同一個掃描中的每個 `wx.MessageDialog` 呼叫，都在 `ui/message_box.py` 或 `BrailleFrame._ask_after_close_save_failure` 中。紅燈原因：`on_about`。
3. `test_no_production_code_searches_windows_by_id_globally`：掃描中沒有 `FindWindowById` 屬性。紅燈原因：`dialog.py` 中兩處命中。
4. **改指向的測試。** 每個為正式程式碼 patch 或記錄 `wx.MessageBox` 的測試，改為 patch 受測模組的模組全域 `message_box`（`gui.message_box`、`dialog_module.message_box`、`settings.dialogs.message_box`）。假函式維持簽章 `(message, caption, style, parent=None)` 與回傳值，所以既有對訊息、標題、樣式、parent 與回答的斷言全部不變。這包括 `DocumentWorkspaceFlowsCharacterizationTest` 的 `setUp`、字典編輯器 harness、管理對話框的測試、驗證測試與設定測試。F-6 的新測試也同樣改指向。
5. **每個呼叫處的涵蓋。** 20 個呼叫處中，每一處至少由一個斷言 `message_box` 參數的測試執行到，可以是改指向的既有測試，也可以是新測試。plan 列出對應關係。`test_about_box_uses_the_helper` 是新測試，檢查 `(about.aboutMessage, _("About DotExpress"), OK | ICON_INFORMATION, parent=frame)`。紅燈原因：`on_about` 使用 `wx.MessageDialog`。

### D. surrogate 與匯出

GUI 測試在 `client/tests/test_gui_document_flows.py`。含 surrogate 的字串以腳本寫入並以位元組檢查，絕不經由 Edit／Write 工具輸入（交接文件 §2）。

1. `test_source_text_for_conversion_replaces_lone_surrogates_without_touching_the_editor`：`input_txt` 持有 `A`＋U+D83D＋`B`。`frame.get_source_text()` 回傳 `A`＋U+FFFD＋`B`。編輯框仍持有 surrogate，也沒有記錄到 `SetValue` 事件。紅燈原因：回傳原始值。
2. `test_save_reads_both_editors_through_the_replacement`：`patch.object(frame._workspace_service, "save_open_document", wraps=...)`。`_save_open_document` 傳入的文字與點字都是 U+FFFD，兩個編輯框都不變。紅燈原因：傳入原始值。
3. `test_manual_conversion_stores_replaced_text`（使用視窗的 view 方法與假的 runner，和既有的轉換 GUI 測試相同；harness 由 plan 決定）：`_complete_manual` 之後 controller 的副本持有 U+FFFD。

在 `client/tests/test_export_coordinator.py`：

4. `test_single_export_error_that_is_not_an_os_error_shows_the_failure_message`：寫出器（patch 過的 descriptor，做法同 `test_write_document_uses_registry_writer`）拋出 `ValueError("injected")`。顯示 `show_error(_("Failed to export document: {error}").format(error=...), _("Error"))`；沒有成功訊息；`assertLogs("dotexpress.gui", "ERROR")` 看到一筆帶有該 `ValueError` 之 `exc_info` 的記錄。紅燈原因：例外逸出。
5. `test_single_export_os_error_is_not_logged`：`assertNoLogs`；訊息與以前相同。守住既有行為。
6. `test_html_export_with_a_lone_surrogate_in_the_dual_view_reports_failure`：真正的 HTML 寫出器，搭配原文含 U+D83D 的雙視 segment，顯示含 `surrogates not allowed` 的失敗訊息並記 log。這在 coordinator 層釘住 M-7 的觸發條件。紅燈。
7. `test_export_all_goes_on_after_an_error_that_is_not_an_os_error`：三份文件。第二份的寫入拋出 `ValueError("injected")`。第一份與第三份寫出，摘要警告列出第二份與 `injected`，並有一筆 log 記錄。紅燈原因：批次停止，沒有摘要。
8. `test_pending_export_failure_after_conversion_is_reported`：`convert_for_export` 的 `on_success` 路徑搭配會拋出例外的寫出器，顯示失敗訊息。紅燈。

### E. 關閉重入（`client/tests/test_gui_document_flows.py`，F-5 關閉測試所在的類別）

該類別的假 `MessageDialog` 新增一個可選的一次性掛鉤。第一次 `ShowModal` 在回答之前執行它（它呼叫 `frame._on_close(inner_event)`）；之後的對話框不執行。

1. `test_close_reentered_while_the_close_dialog_is_open_is_vetoed`：外層關閉可否決，存檔失敗，對話框的掛鉤送出內層的可否決事件。內層事件被否決，從未被 skip。只記錄到一個 `MessageDialog` 事件，存檔只嘗試一次（`os.replace` 的呼叫次數）。外層的回答 `ID_CANCEL` 接著否決外層事件，包不變。紅燈原因：今天內層關閉會再存一次，並記錄到第二個對話框。
2. `test_close_reentered_that_cannot_be_vetoed_closes_once`：掛鉤送出內層的不可否決事件，外層對話框的回答是 `ID_YES`（重試）。內層執行嘗試存檔一次，記錄 `Failed to save the open document while closing`（`assertLogs`）。接著 `close_converting_dialog` 被呼叫一次，雙視被銷毀一次，內層事件被 skip。外層既不重試（沒有第二個對話框），也不否決、不 skip。紅燈原因：今天外層會重試並再次詢問。
3. `test_close_works_again_after_a_vetoed_close`：第一次關閉回答 `ID_CANCEL`（被否決）。解除鎖定後，第二次關閉存檔並 skip。這守住 `finally` 的重設；改前就是綠燈（旗標還不存在），之後也維持綠燈。
4. `test_close_flag_is_reset_when_the_close_raises`：patch `_save_open_document_before_close` 讓它拋出 `RuntimeError`。`_on_close` 讓例外傳出去，之後 `frame._closing` 為 `False`。紅燈原因：屬性不存在。

既有的 F-5 關閉測試與 `test_close_asks_presenter_before_saving` 不需修改，維持綠燈。它們的呼叫順序不變，因為 `_close` 就是原本的處理函式本體。

### 數量

新測試：A 6、B 3（另有 1 個 harness 掛鉤修改、3 個修改）、C 4（加上 plan 發現缺少的呼叫處測試）、D 8、E 4，約 25 個。改指向的測試一對一取代原本的斷言。Windows 上預期 `Ran` ＝ F-6 之後的基準＋新測試，`FAILED (errors=1, skipped=7)`，只有 F-W6。確切數字由 plan 決定；紅燈／綠燈的意圖有約束力。

## 移轉步驟（每一步一個綠燈 commit，先紅燈）

1. `fix: look up standard dialog buttons among the dialog's own children (F-7)`：D1，B1–B4、C3。
2. `fix: show message boxes with the translated OK button (F-7)`：D2–D4。新增 `ui/message_box.py`，改寫 20 個呼叫處（加上 F-6 的），加入 `wx_stub` 的修改，搭配 A1–A6、C1、C2、C4 與 C5。
3. `fix: read the editors without lone surrogates (F-7)`：D5，測試計畫 D 的 D1–D3。
4. `fix: report every export failure (F-7)`：D6，測試計畫 D4–D8。
5. （本步驟之前：D9，在 F-7 之前的 build 上執行並記錄項目 58。）`fix: veto a close that arrives while another close is asking (F-7)`：D7，E1–E4。

每個 commit 以 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` 結尾，只 stage 明確的路徑。不碰翻譯檔（D8）。

## 驗收條件

在 Windows 上從 `client/` 以 `$PY` 執行，runtime 依 F-3 plan Task 0 複製。

1. 完整套件：除了 F-W6 之外沒有失敗或 error；`Ran` ＝ F-6 之後的基準＋新測試。
2. 聚焦測試：`$PY -m unittest tests.test_message_box tests.test_dialog_display tests.test_dialog_validation tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_settings_dialogs tests.test_gui_document_flows tests.test_export_coordinator tests.test_wx_stub -v` 通過。
3. 掃描：正式程式碼中沒有 `wx.MessageBox`，也沒有 `FindWindowById`。每個正式程式碼中的 `wx.MessageDialog` 都在兩個允許的位置之一。
4. 翻譯檔不變。`git diff main -- client/locales` 為空，AST msgid 掃描得到 F-6 之後的數量，`msgfmt --check --statistics` 回報該數量全部已翻譯、0 fuzzy、0 未翻譯。
5. 兩個 fixture 的 sha256 不變（`translation_golden.json` `e67d95a1...`、`dictionary_entries_trace.json` `f493da52...`）。
6. 不動 app 資料：主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 前後 sha256 相同。在 worktree 中，測試沒有建立 `client/log/`、`client/workspace/` 或 `client/config.json`。
7. `git diff main --stat` 只涉及 `client/ui/message_box.py`、`client/dialog.py`、`client/gui.py`、`client/settings/dialogs.py`、`client/documents/export_coordinator.py`、`client/tests/wx_stub.py`、上面提到的測試檔，以及 spec、plan 與 history 檔案。
8. 突變檢查（plan）。每個突變至少被一個測試抓到：
   - `localize_standard_buttons` 中的 `FindWindow` 改回 `FindWindowById`；另外，編輯器中的也單獨改回；
   - helper 不呼叫 `SetOKLabel`；
   - helper 對是／否設定標籤；
   - helper 回傳 `ShowModal` 的原始值；
   - 某一個呼叫處改回 `wx.MessageBox`；
   - `get_source_text` 不做替換；
   - 存檔讀取不做替換（文字；另外，點字單獨一個）；
   - `_write_single` 改回 `except OSError`；
   - 批次改回 `except OSError`；
   - `OSError` 也記 log；
   - 移除防護；
   - 重入分支改為 skip 而不是否決；
   - `_closing` 沒有在 `finally` 中重設；
   - 外層迴圈忽略 `_close_finished`。
9. 下面的 packaged GUI 驗證，結果寫在實作的 history 資料夾中。

## Windows 驗證（packaged build）

建置方式同 F-5：把主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面，再執行 `scripts\build-dotexpress.bat`。在 `client\build\DotExpress\PYZ-00.toc` 與 `Analysis-00.toc` 中確認 `ui\message_box.py`、`dialog.py`、`gui.py`、`settings\dialogs.py` 與 `documents\export_coordinator.py` 都來自受驗證的 checkout。把 exe 複製到 `D:\dxtest\N-f7\`。

「改前」是 F-6 之後 `main` 的 build（F-6 任務的 build，或新建一個）。每個項目在新的 `D:\dxtest\auto<項目>-f7` 資料夾中執行；app 的 `dictionary\`、`workspace\` 與 `log\` 位於複製過去的 exe 旁邊。只結束 exe 位於這些資料夾底下的程序（`dx.kill_under`；輔助程序用 `taskkill /T`）。使用者可能自己開著 DotExpress。

腳本放在實作 history 資料夾的 `auto/`。它們不加修改地沿用：

- `docs/superpowers/history/2026-10-09-03-windows-verification/auto/`（`dx.py`、`docs.py`、`dicts.py`、`lock.py`）；
- `.../2026-10-10-01-f5-save-failure-handling/auto/f5gui.py`。

它們在 pywinauto venv（`$SP\uia`）中執行；缺少時以 `py -3.13 -m venv` 重建，並 `pip install pywinauto==0.6.9 psutil`。訊息框與 F-5 對話框都是 task dialog，所以用 UIA 讀取，做法同 `f5gui.describe`：標題、`MainInstruction`／`ContentText`、按鈕名稱、焦點。

項目編號為 53–64，接在 F-6 的 42–52 之後（由 plan 指定；預留的編號是 `4a`–`4l`）。

| # | 步驟 | F-7 之後的預期 | 改前 |
| --- | --- | --- | --- |
| 53 | 新增 `alpha`；再新增一次，輸入 `alpha`，按 Enter | 「已存在」訊息框：一個按鈕，翻譯後的確定；Enter 關閉它；重新顯示的名稱對話框有翻譯後的確定／取消，預填 `alpha`；Esc 取消；清單不變 | 訊息框按鈕是 `OK`；重新顯示的對話框是 `OK`／`Cancel`（F-W9） |
| 54 | 字典管理：新增 `d1`；再新增一次 `d1` | 字典名稱對話框同 53；「已存在」訊息框有翻譯後的確定 | 英文，同 53 |
| 55 | 開啟文字處理（保持開著），開啟字典管理，選 `d1`，按編輯；新增詞條 `x`／`1`；按確定。再編輯一次 `d1` | 編輯器的按鈕有翻譯。確定會存檔：重新開啟時列出 `x`，`dictionary\d1.csv` 中有它。之後文字處理對話框自己的取消可以正常關閉它。改為在設定對話框開著時再做一次 | **編輯器的按鈕是 `OK`／`Cancel`；確定不存檔就關閉：沒有 `x`，`d1.csv` 不變**（記錄新發現的缺陷） |
| 56 | 只有確定的訊息框，每種各一：「已存在」錯誤（53）；Ctrl+Enter 之後的「轉換完成。」；「關於」對話框；一次有一份文件失敗的「全部匯出」（摘要警告；如何讓它失敗由 plan 指定，例如用 `lock.py` 開著目標檔） | 每個都顯示原本的文字、標題與圖示，以及翻譯後的確定，焦點在它上面；用 Enter 關閉其中一個、用 Esc 關閉另一個 | 同樣的訊息框，按鈕是 `OK` |
| 57 | 刪除文件 `alpha`（先選否，再一次選是）；「全部匯出」到有衝突的資料夾（覆寫：否） | 系統的是／否標籤與以前相同；刪除時焦點在「否」，覆寫時在「是」；Alt+N／Alt+Y 可以回答；選否時文件／檔案保留 | 相同 |
| 58（D9） | 開著 `alpha`；輸入修改；`lock.py` 開著 `alpha.dep`（共用 `r`）；送出 `WM_CLOSE`。關閉對話框出現。在 driver 的執行緒中：`SendMessageTimeoutW(main, WM_QUERYENDSESSION, 0, ENDSESSION_LOGOFF, SMTO_NORMAL, 10000)`。在 3 秒內計數主視窗底下的「無法儲存文件」對話框，並記錄呼叫返回的時間與結果。對開著的對話框按 Esc；然後解除鎖定，按 Enter（重試）關閉 | 約 1 秒內呼叫返回，結果 0；全程恰好一個對話框；按 Esc 後 app 仍在執行，修改仍在編輯框中；解除鎖定＋Enter 後 app 結束，重新啟動後 `alpha` 有這個修改 | **兩個對話框（巢狀）；呼叫要等內層被回答後才返回**（確認 M-5） |
| 59 | 開著 `alpha` 且未修改；同 58 送出 `WM_QUERYENDSESSION` | 呼叫回傳 1；app 結束；`alpha.dep` 不變 | 相同（驗證工具本身） |
| 60 | 同 58 直到對話框出現；送出 `WM_ENDSESSION`（`wParam` 1、`lParam` `ENDSESSION_LOGOFF`） | 程序在 5 秒內以結束碼 0 結束；`alpha.dep` 的成員不變（上次成功的存檔），沒有 `.tmp`；`log\gui.log` 沒有新的 traceback | 相同（wx 不送 close 事件就結束） |
| 61 | 貼上 `A`＋U+D83D＋`B`（`f5gui.paste_text_with_lone_surrogate`）；按 Ctrl+Enter | 「轉換完成。」，按鈕是翻譯後的確定；點字顯示 U+FFFD 的跳脫寫法（`\xfffd` 的點字方格），不是 `\xd83d`；編輯框仍是 `A`＋U+D83D＋`B` | 點字顯示 `\xd83d` 的跳脫寫法 |
| 62 | 接續 61：檔案 > 匯出 > HTML（雙視），存成新檔 | 「文件已成功匯出。」；檔案存在，內容有 `EF BF BD`，沒有 `ED A0 BD` | **沒有訊息，沒有檔案** |
| 63 | 接續 61：以 HTML「全部匯出」到空資料夾 | 成功的摘要；每份文件一個檔案 | **沒有摘要；批次停在 `alpha`** |
| 64 | 重跑 F-5 的項目 38 與 39（既有的 `item38.py`，經由 `rerun.py`） | 與 F-5 的記錄相同，只是 Ctrl+Tab 的錯誤框現在顯示翻譯後的確定 | F-5 的結果 |

絕不觸發真正的登出或關機；訊息只送給測試實例的主視窗。需要 NVDA 的項目維持人工，加入給使用者的清單。人工項目（使用者）：在 NVDA 下，一個只有確定的訊息框（56）與重新顯示的名稱對話框（53）讀出翻譯後的標籤。這是項目 65。

## 風險

- **非中文 Windows 上的是／否**（低，D4）。不變：由系統決定標籤。英文 Windows 上會在中文文字旁顯示英文的是／否，和今天相同。
- **`FindWindow` 找到 id 相同的巢狀子視窗**（極低）。app 的對話框中沒有任何一個有兩個 id 相同的標準視窗。
- **標籤改變影響自動化或 NVDA 使用習慣**（低）。新的文字就是第一次顯示時已在用的翻譯。舊腳本兩種標籤都接受。
- **`_closing` 的否決讓 Windows 在登出時等待**（設計如此）。對話框開著時，DotExpress 回答「不可結束」，Windows 顯示「此 app 正在阻止登出」的畫面。「仍要登出」會經由 wx 的 `OnEndSession` 結束程序（60）；上次成功存檔之後的修改會遺失，包完整無損。今天同樣的選擇出現在一個巢狀對話框之後。
- **lone surrogate 的點字改變**（極低）。顯示 U+FFFD 的跳脫寫法，而不是 surrogate 的跳脫寫法；這個字元本來就看不見，也從來不是合法的文字。
- **documents 層寫 `gui.log`**（低）。coordinator 現在 import `log`；若有測試讓它寫 log 卻沒有用 `assertLogs`，就會在 checkout 中寫出 `client/log/gui.log`。上面的測試規則與驗收條件 6 守住這一點。

## 待決問題

沒有需要使用者決定的問題。決定 U1–U3 是使用者的決定（2026-10-10）。

Decided by orchestrator with the recommended default; user may override before merge：

- **O1.** 是／否訊息框保留系統的標籤；不新增 msgid（D4）。
- **O2.** helper 是 `client/ui/message_box.py` 的 `message_box(message, caption, style, parent=None) -> int`，可直接替換 `wx.MessageBox`（D2）。
- **O3.** 「關於」對話框與檔案問題對話框納入 F-W9（D1、D3）。
- **O4.** 保留 `localize_standard_buttons` 中已無作用的 `button_sizer` 退路（D1）。
- **O5.** 非預期的匯出錯誤以 `dotexpress.gui` logger 寫進 `gui.log`；`OSError` 不記 log（D6）。
- **O6.** 不可否決的重入關閉照 F-5 D8 執行一次，外層關閉在其對話框返回後停止。被否決的重入不記 log（D7）。
- **O7.** M-7 套用在 GUI 讀取編輯框的位置（`_editor_text`）；F-5 D4 保留在 documents 層（D5）。
- **O8.** 以原始碼掃描測試防止 `wx.MessageBox`、沒有標籤的 `wx.MessageDialog` 與 `FindWindowById`，包括 F-6 新增的部分（測試計畫 C）。
- **O9.** 字典編輯器維持直接綁定自己的確定按鈕（`self.FindWindow(wx.ID_OK)`），不改為 `self.Bind(..., id=wx.ID_OK)`（D1）。

## 不在範圍內／後續項目

- **由 app 翻譯的是／否**（`&Yes`、`&No`；兩個 msgid），供非中文的 Windows 使用。
- **其他輸入中的 lone surrogate。**
  - 含 surrogate 的字典詞條存檔時會以「儲存失敗：...」失敗（`DictionaryEntriesDialog._on_ok` 會攔截）。
  - 文字處理腳本編輯器把 `UnicodeEncodeError` 當成 `ValueError` 訊息回報。
  - 兩者都不會卡住，也不會在無聲中丟資料；維持不變。
- **F-5 spec D8 中**關於「可否決的關閉之後才有不可否決的關閉」的說法：量測結果顯示 wx 3.2.9 不會這樣（見「現況」）。本任務不修改 F-5 spec，審查時可以在那裡加註。
- **全域 `wx.Locale` 與 wx 的翻譯檔**（U2 c，已否決）。
- F-5 仍未處理的後續項目：U+0000 截斷、孤兒 `.tmp` 回收，以及 F-3 審查 M-1。
