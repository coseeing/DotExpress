# 行為與 NVDA 後續修正（F-13）設計

## 目標

F-13 處理 `task.md` 第五節「下一輪要修」的第 1、2、3、5、6 項，五項都由使用者在 2026-10-14 決定。這幾項修正的是螢幕報讀使用者會遇到的行為：轉換失敗後焦點停在哪裡、NVDA 與 Alt+Tab 找不到的啟動提示框、登出時偶爾異常結束，以及字典編輯器移除清單裡的文字。第 5 項（確認框改成系統樣式）有一個前提，實測結果前提不成立，所以第 5 項不做（D5）。

使用者已決定（2026-10-14，`task.md` 第五節「下一輪要修」；HANDOFF `2026-10-14-01-handoff` 第 1、4 節），以下不再詢問：

- **U1（第 1 項）：** 手動轉換失敗、且該文件已不是開啟中的文件時，失敗框按掉後用 F-9 M-6 的 `focus_source_editor()` 把焦點移到原文編輯框。
- **U2（第 2 項）：** 「已復原文件」「已取代字元」與無效檔案對話框改在主視窗顯示後才跳出，讓 NVDA 能報讀、Alt+Tab 找得到。
- **U3（第 3 項）：** 程式結束時，若背景轉換執行緒還活著，就跳過 `runtime.close()`（`lou_free()`）（F-9 review M-8）。以轉換中多次送出 WM_QUERYENDSESSION/WM_ENDSESSION 的 GUI 項目驗證。
- **U4（第 5 項）：** F-11 的兩個確認框（「移除無法顯示的列」「尚未儲存的變更」，`GenericMessageDialog`）改成系統「是／否」框，按鈕用自訂文字，和現有四個一致。Esc／Alt+F4 沒反應可以接受。**前提：** Esc、Alt+F4、關閉鈕絕不能觸發「移除並儲存」或「放棄變更」；若會觸發就不改，並回報使用者。現有四個框（刪除文件、全部刪除、覆寫確認、字典刪除確認）不動。
- **U5（第 6 項）：** 移除清單中的注音顯示檔案裡的原始值，頭尾空白不去掉；不另加標註，不新增字串。
- 第 4、7、8 項屬於 F-14（見「與 F-14 的關係」）。

完成後：

- 轉換由另一份文件啟動、失敗框按掉後，焦點在開啟中文件的原文編輯框；以前停在唯讀的點字結果框。
- 啟動時先出現主視窗，啟動提示框在它之後跳出，擁有者是已顯示的主視窗。
- 轉換中登出或關機時，不再在執行中的轉換執行緒底下釋放 liblouis。
- 檔案值為 `ㄇㄚ␠␠` 時，移除清單顯示 `「ㄇㄚ  」`；以前顯示 `「ㄇㄚ」`。
- F-11 的兩個確認框維持原樣（D5）。

新的使用者可見字串：**無**。catalog 只有 `#:` 參考行改變，`.mo` 位元組不變。

不做的事：F-14（介面語言的準備、HTML `lang`、設定備份訊息）；F-10；使用者 2026-10-14 決定不修的延後項目（匯出 `.tmp` 重試、表頭不分大小寫、F-9 M-5、`config.json` 損壞的提示、F-11 M-4）。

## 規劃後的修正（F-13，2026-10-14）

依 `main` `a147fed` 的程式碼重新檢查：決定 D1–D6、改前改後表、探測結果與測試計畫都成立，另有以下細化。plan 的「Spec Corrections and Refinements」一節是同一份清單。

1. **基準與數量。** 在 `a147fed`（`HEAD:client` `a967d8d4`）上完整測試為 `Ran 1632`、`OK (skipped=6)`；407 個 msgid。F-13 新增 14 個測試、修改 4 個：步驟 1 後 `Ran 1634`（新增 2、翻轉 1），步驟 2 後 `1638`（新增 4、修改 2），步驟 3 後 `1645`（新增 7），步驟 4 後 `1646`（新增 1、翻轉並改名 1）。
2. **每一步都更新 catalog。** 四個步驟都會移動 msgid 上方的行數，所以每一步都重新產生範本與 `.po`，並重建 `.mo`（位元組不變）；任何一個 commit 之後都沒有過期的 `#:` 參照，不需要另外的 `chore:` commit。`msgmerge` 也會把 F-12 修正 commit 寫成一行的一個 msgstr（「無法寫入檔案」的原因）折成兩行，文字相同。`.mo` 與 `a147fed` 的位元組完全相同。
3. **D1 的實作。** `_left_document(target)` 就是 F-12 D7 的具名條件。`_on_job_failure` 在訊息框之前只判斷一次：為真時顯示具名訊息，並在 `show_error` 返回後呼叫 `focus_source_editor()`；為假時只顯示原因，不移動焦點。`_name_unopened_document` 現在只負責組出具名訊息。
4. **D2 的實作。** `__init__` 最後的輕量步驟叫 `_show_empty_startup_state`。「只執行一次」的旗標是類別屬性 `_startup_documents_loaded`。測試 B2 把 post 本身記在 `"show"` 與 `"client_init"` 之間，所以在 `Show()` 之前 post 會被抓到。測試用的 wx stub 對不存在的屬性回傳不做事的函式，所以測試 B3 用同一個呼叫分別測視窗未關閉（會載入）與已關閉（什麼都不做）；測試 B5 用一個同時有三種提示的工作區（無效的 `bad.dep`、`alpha` 被中斷的重新命名，其文字含 U+0000）。
5. **D3 的實作。** `ConversionPresenter.worker_alive()`、`BrailleFrame.conversion_worker_check()`（回傳 presenter 的 bound method `worker_alive`）、`BrailleApp._conversion_worker_alive`（類別屬性，在 `OnInit` 建立 frame 之前是 `None`；在 `Show()` 之前設定）、`BrailleApp._conversion_worker_is_alive()`（沒有檢查函式時為假）。測試 C4 在 `OnInit` 之後讓 frame 替身的任何屬性都會丟出例外。比清單多一個測試：frame 交出的是 presenter 的 `worker_alive`。
6. **D6 的測試值。** `ㄇㄚ␠␠`、`␠ㄇㄚ`、`ㄇㄚ` 加 tab、`ㄇㄚ` 加 U+3000 在 `a147fed` 上都會被隱藏；一個測試用四個 subTest 確認每個值都原樣列出。
7. **變異檢查：17 個 mutant**：上面 15 個，加上空白啟動狀態不更新標題，以及 frame 的檢查函式交出 `is_running`。
8. **commit 主旨**以 `(F-13)` 結尾；`F-8b review M-8` 與 `F-9 review M-8` 寫在步驟 2、3 的 commit 內文。
9. **Windows 項目。** 項目 127 在啟動後另外寫入一個過期的 `dual_view\dual-view-f13probe.html`：程序結束後若它已被刪除，表示在 `WM_ENDSESSION` 的路徑上 `OnExit` 有執行（「現況」第 3 項對 wx 原始碼的解讀）。項目 125 的工作區：無效的 `bad.dep`、`alpha` 被中斷的重新命名（改為 `gamma`），其文字含 U+0000，以及有效的 `beta.dep`；先開啟的是 `alpha`。
10. **review 修正（F-13 review，對象 `fbca556`，2026-10-14）。由 orchestrator 依建議的預設決定；使用者可在 merge 前推翻。** review 沒有 Critical 或 Important；以下是它的 Minor M-1～M-3 與 M-5（M-4 是既有的 flaky 測試，不是 F-13 造成的，不處理）。沒有新字串：407 個 msgid，`.mo` 與 `a147fed` 的位元組相同；catalog 只有 `#:` 行改變。完整測試為 `Ran 1651`（1646 + 5）、`OK (skipped=6)`。
    - **M-1（延後載入時的未預期錯誤）。** `load_startup_documents` 是以 post 的方式執行，例外原本只會送到打包版不存在的 stderr，留下一個空視窗、沒有任何提示。現在載入時的任何例外都以 ERROR 寫入 `dotexpress.gui`（`gui.log`），含 traceback（`Failed to load the workspace at startup`），並以既有字串 `The file cannot be read: {error}`／`無法讀取檔案：{error}` 顯示在屬於主視窗的「錯誤」框；視窗維持原狀（若沒有開啟任何文件，標題為 `DotExpress`），也不會再試一次載入。若這時視窗已關閉，只寫 log。
    - **M-2（啟動提示框開著時登出）。** 在無效檔案對話框之後、「已復原文件」框之後、以及開啟第一份文件之後（它的「已取代字元」框，或預設文件的存檔錯誤），若 frame 在這期間已關閉（`_close_finished`），載入就停止：不再顯示後面的框、不寫入預設文件、不對已關閉的視窗更新標題或設定焦點。這細化了「風險」中的「延後載入前就關閉」：修正前，框返回後載入會繼續。
    - **M-3（測試）。** 一個測試在「已復原文件」框裡再呼叫一次 `load_startup_documents`，確認不會載入第二次，所以旗標必須在載入之前設定（review 存活的 mutant R1）。
    - **M-5（紀錄）。** `auto-results.md` 的項目 127 只引用存在的 log：正式結果是 `auto127r3-f13.log`（20 次中 20 次結束碼 0）與 `auto127r4-f12b-f13.log`（20 次中 1 次 `0xC0000374`）；這 40 次都刪除了 probe 檔。較早幾輪的 log 仍在；以它們算出的合計標為補充資料，N-f12b 的分母更正為 40（不是 41）。
    - **手動項目 131**（NVDA）可改用含這些修正的 `D:\dxtest\N-f13b\DotExpress.exe`；仍不勾選，留給使用者。

## 與 F-14 的關係

F-14（`D:/workspace/DotExpress-f14`）從同一個 `main`（`a147fed`）平行進行。兩個任務都會動到下列檔案：

| 檔案 | F-13 | F-14（依 `task.md` 的範圍） |
| --- | --- | --- |
| `client/gui.py` | `BrailleFrame.__init__`、`_load_startup_documents`、`BrailleApp.OnInit`、`BrailleApp.OnExit` | `_report_settings_save_problem`（設定備份訊息），可能還有載入時呼叫 `_()` 的地方 |
| `client/dialog.py` | `_hidden_row_line` | 可能有編輯器顯示的類型名稱（`dictionaries/entries.py` 的類型名稱） |
| `client/locales/dotexpress.pot`、`zh_TW/LC_MESSAGES/dotexpress.po` | 只有 `#:` 行號 | 新 msgid 與 `#:` 行 |
| `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` | 不變（位元組相同） | 重新產生 |
| `client/tests/test_gui_document_flows.py` | 啟動、結束、焦點的測試 | 設定備份訊息的測試 |

兩個任務沒有改到同一個函式。後 merge 的任務 rebase 到先 merge 的那個之上，再重新產生 catalog 的 `#:` 行（`scripts/generate-pot.bat`，然後 `msgmerge`）。F-13 沒有新增 msgid，catalog 內容以 F-14 的為準。F-14 的 `i18n.py`、`about.py`、`dictionaries/entries.py`、`settings/dialogs.py`、`dual_view/html.py`、`config.py`，F-13 都不動。

## 現況（2026-10-14 於 `main` `a147fed`、worktree `D:/workspace/DotExpress-f13` 確認）

行號取自 `a147fed`，僅供參考；程式碼以函式名稱指稱。

### 第 1 項：轉換失敗後的焦點

- `ConversionPresenter._on_job_failure`（`client/ui/conversion_presenter.py:287-300`）取出進行中的工作並結束它（`_end_job`：停止計時器、關閉轉換中對話框、`set_conversion_busy(False)`），接著：
  - **匯出工作**（`active.job.export is not None`）：呼叫 `export.on_error(message)`，由匯出協調器顯示它自己的框。
  - **手動工作**：`show_error(_name_unopened_document(target, message), "錯誤")`。`_name_unopened_document`（`:302-306`）只在 `target.document_name is not None` 且與開啟中的文件名稱不同時，才在前面加上 `無法轉換文件「X」。`（F-12 D7）。
  - 焦點從不移動。
- 成功時，`_complete_manual`（`:308-341`）處理情況 (b)（開著另一份文件），並在最後呼叫 `self._view.focus_source_editor()`（`:341`，F-9 review M-6）。情況 (a)（同一份文件）呼叫 `show_conversion_output`，刻意把焦點放在點字結果框。
- `BrailleFrame.set_conversion_busy`（`gui.py:1178-1187`）在工作進行時停用文件清單與 `input_txt`。有焦點的 `input_txt` 因此失去焦點，wx 把焦點移到點字結果框（F-9 review 第 2.1 節實測）。轉換中按 Ctrl+Tab 時，`_open_adjacent_document` 的 `input_txt.SetFocus()` 對停用的控制項無效。所以失敗框按掉後，焦點停在唯讀的點字結果框；切換過或沒切換都一樣（F-12 spec「Out of Scope」：「Focus after the D7 box」）。
- `BrailleFrame.focus_source_editor`（`gui.py:1225-1228`）只在 `IsActive()` 時把焦點移到 `input_txt`。
- 測試：`tests/test_conversion_presenter.py` 的 `test_a_failure_after_switching_names_the_document`、`test_a_failure_of_the_open_document_is_not_named`、`test_a_failure_after_switching_away_and_back_is_not_named`、`test_a_failure_without_a_starting_document_is_not_named`、`test_manual_failure_shows_error_after_busy_off`、`test_export_failure_calls_only_on_error`。每個測試都釘住送達後的完整事件清單，所以目前都釘住「沒有呼叫焦點」。另有 `tests/test_gui_document_flows.py` 的 `test_focus_source_editor_only_while_the_window_is_active`。

### 第 2 項：啟動提示框早於主視窗顯示

- `BrailleFrame.__init__`（`gui.py:125-145`）最後一步是 `self._load_startup_documents()`（`:145`）。
- `_load_startup_documents`（`:244-248`）：`_clear_document_editors()`、`_load_workspace_documents_at_startup()`、`_update_window_title()`、`input_txt.SetFocus()`。
- `_load_workspace_documents_at_startup`（`:807-822`）依序執行：
  1. `load_documents()`
  2. `_refresh_document_list()`
  3. `_review_invalid_workspace_files`（`:726-736`）：強制回應的 `InvalidWorkspaceFilesDialog`，依選擇刪除檔案
  4. 「已復原文件」資訊框（`show_info`，F-8）
  5. `_ensure_open_document_exists`（`:800-805`）：開啟第一份文件（`_open_document_by_name`，`:650-673`；其中 `:664-673` 是「已取代字元」警告框），或建立預設文件。建立失敗時，由 `_show_document_save_error` 顯示錯誤框。
  6. `_update_window_title()`
- `BrailleApp.OnInit`（`gui.py:1276-1300`）建立 frame（`:1290-1295`），之後才 `self.frame.Show()`（`:1298`），再 `start_client_init_background`。所以所有啟動提示框的擁有者都是還沒顯示的 frame。F-8b review M-8：NVDA 可能不會報讀，Alt+Tab 也找不到。F-8b 項目 70、73 記錄的是「主視窗出現前顯示」。
- 建構期間沒有其他框：`_initialize_state` 與版面程式碼不顯示任何東西；F-12 的設定存檔警告只在存檔時出現。
- 釘住目前順序的測試：
  - `tests/test_gui_document_flows.py` 的 `DocumentControllerOwnershipTest.STARTUP_STEPS`（`__init__` 的六個步驟，最後一個是 `_load_startup_documents`）。
  - `BrailleAppLifecycleTest.test_app_startup_runs_steps_in_contract_order`（`["prepare", "cleanup", "runtime", "frame", "show", "client_init"]`，frame 是 `Mock`）。
  - `test_app_builds_runtime_and_passes_it_to_frame`（`frame.Show.assert_called_once_with()`）。
  - 直接呼叫 `frame._load_workspace_documents_at_startup()` 的八個測試（`:318`、`:2134-2240`、`:2390`、`:3434`）測的是載入本身，與執行時機無關。
- 先前任務的 GUI 輔助程式假設舊順序：`2026-10-10-06-f8b-recovery-and-nul/auto/f8bgui.py` 的 `start()` 一直回答框，直到出現標題以 `DotExpress` 結尾的視窗才 attach 並返回。F-9 的 `B.start` 與 F-11／F-12 的 `dx.launch` 也一樣。

### 第 3 項：轉換中結束程式

- `BrailleApp.OnExit`（`gui.py:1302-1312`）：先 `cleanup_dual_view_html`，再無條件 `runtime.close()`。`TranslationRuntime.close`（`conversion/contracts.py:31-36`）以相反順序執行關閉回呼：MathCAT 的 `adapter.close`，以及 liblouis 的 `louis_helper.terminate()`（`lou_free()`；`braille/louis_helper.py` 是 git-ignored 的執行檔案）。
- 工作執行緒是 `ConversionJobRunner._thread`（`conversion/jobs.py:57-67`，`daemon=True`）。`ConversionJobRunner.is_running()`（`:55-56`）就是 `_thread is not None and _thread.is_alive()`。`_thread` 只在主執行緒送達結果時清除（`_deliver_success`／`_deliver_failure`）。
- `ConversionPresenter.is_running()`（`conversion_presenter.py:183-185`）的意思是「有工作進行中或排隊中」。`shutdown()`（`:238-249`，由 `BrailleFrame._finish_close` 呼叫，`gui.py:1162-1172`）會清掉這個狀態，所以關閉後 presenter 回報「沒有在執行」，即使工作執行緒可能還在 liblouis 裡。
- `_close`（`gui.py:1136-1147`）在 `is_running()` 時否決可否決的關閉。所以轉換中的 WM_QUERYENDSESSION 會立即被拒絕（F-9 GUI 項目 93）。
- WM_ENDSESSION 不會產生 close 事件（F-7 項目 60）。在 MSW 上，wxWidgets 3.2 的 `wxApp::OnEndSession` 會呼叫 `OnExit()`，然後結束程序（依閱讀 wx 原始碼的判斷，待 GUI 項目 127 確認）。所以 `OnExit` 執行時，工作執行緒可能正在 `lou_translateString` 裡。F-9 看過結束碼 `-1073740940`（`0xC0000374`，heap 損毀）：dry run 五次中一次，N-f8b2 上一次（`auto93-f8b2-f9`），都發生在轉換中的 WM_ENDSESSION 之後（`2026-10-10-07-f9-conversion-target-document/auto-results.md`「觀察」；review M-8）。
- 重現方式：`2026-10-10-07-f9-conversion-target-document/auto/item85.py` 的項目 93 依序：
  1. 準備一份待轉換的 `alpha`，內容是 `f9gui.long_text()`（轉換約 15 秒）。
  2. 按 Ctrl+Enter。
  3. 送 `f7gui.SessionMessage(w.handle, WM_QUERYENDSESSION)`（lParam `ENDSESSION_LOGOFF`；轉換中回傳 0）。
  4. 第二次轉換中送 `SessionMessage(w.handle, WM_ENDSESSION, wparam=1)`。
  5. 以 `f7gui.exit_code(pid, 5)` 讀結束碼。
- 測試：`BrailleAppLifecycleTest.test_app_exit_closes_runtime`、`test_app_exit_logs_cleanup_failure_and_still_closes_runtime`、`test_app_exit_cleans_the_validated_dual_view_folder`、`test_app_exit_without_initialized_runtime_is_safe`。這些測試建立的 `BrailleApp` 都沒有 frame。

### 第 5 項：F-11 的兩個確認框

- `ui/message_box.confirm_box`（`client/ui/message_box.py:36-54`）：`wx.GenericMessageDialog(parent, message, caption, wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING)` 加 `SetOKCancelLabels(ok_label, cancel_label)`，只有 `wx.ID_OK` 才回傳 `True`。
- 使用處：`DictionaryEntriesDialog._confirm_hidden_rows`（`dialog.py:609-624`，「移除無法顯示的列」，`移除並儲存(&S)`／`返回編輯(&B)`）與 `_on_cancel`（`:587-598`，「尚未儲存的變更」，`放棄變更(&D)`／`返回編輯(&B)`）。兩者都從編輯器（強制回應的 `wx.Dialog`）跳出。
- 現有四個是／否框用系統按鈕文字呼叫 `message_box(..., wx.YES_NO [| wx.NO_DEFAULT] | wx.ICON_WARNING)`：`gui.py` 的 `on_delete_document`（`:910`，樣式在 `:919`）、`on_delete_all_documents`（`:940`，樣式在 `:948`）、`confirm_overwrite_all`（`:1254-1262`），以及 `dialog.py` 的 `DictionaryManagementDialog.confirm`（`:898-899`）。
- F-11 規劃時（plan「Spec Corrections」3）實測：從對話框跳出、自訂按鈕文字的「確定／取消」task dialog，按 Alt+F4 回傳 OK；改用 `SetYesNoLabels` 則回傳 `ID_YES`。
- 測試：`tests/test_message_box.py` 的 `test_confirm_box_is_a_generic_warning_whose_cancel_button_is_the_default`、`test_confirm_box_closed_any_other_way_is_cancel`；`tests/test_wx_call_sites.py` 的 `test_the_only_generic_message_dialog_is_the_confirmation_box`。

### 第 6 項：移除清單

- `DictionaryEntriesDialog._hidden_row_line`（`dialog.py:626-634`）以 `text=row.text.strip()`、`bopomofo=row.braille.strip()` 格式化 `Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid`（zh_TW：`第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確`）。
- `PreservedDictionaryRow.braille`（`dictionaries/entries.py:37-57`，在 `:174` 建立）是讀到的原始欄位，沒有去空白。
- 注音列隱藏與否，看的是只去掉開頭空白後的值（F-11 D14、review I-1）。在 `a147fed` 以 `_is_editable` 確認：
  - `ㄇㄚ␠`、`␠ㄇㄚ␠` 會顯示。
  - `ㄇㄚ`、`ㄇㄚ␠␠`、`␠ㄇㄚ` 會隱藏。
  - 這三個隱藏的值，目前清單都顯示成 `「ㄇㄚ」`。
- 測試：`tests/test_dictionary_entries_dialog.py` 的 `test_a_row_line_shows_the_stripped_source_text_and_sequence`（檔案值 `␠ㄉㄨˋ|ㄗ˙␠`，清單顯示去空白後的值）、`test_a_row_without_its_tone_space_is_hidden_and_listed_on_ok`（`ㄇㄚ`，沒有空白），以及 trace 重放（`zz`／`ab`，沒有空白；fixture `dictionary_entries_trace.json` 不記錄這個框）。

### 實測（第 5 項的前提，2026-10-14）

`docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/probe/`（腳本、驅動程式、原始輸出、README）。設定：

- wx 4.2.5、wxWidgets 3.2.9、Windows 11 zh-TW。
- `wx.MessageDialog(dialog, ..., wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)` 加 `SetYesNoLabels`，從強制回應 `wx.Dialog`（其擁有者是一個 frame）的確定按鈕處理函式跳出。
- 每次都用新的程序執行；只在 probe 位於前景時送出按鍵。

| 框 | Esc | Alt+F4 | 關閉鈕 | Enter |
| --- | --- | --- | --- | --- |
| 是 = `移除並儲存(&S)`，否 = `返回編輯(&B)` | 沒反應 | **`ID_YES`：移除並儲存**（2 次中 2 次） | 框沒有關閉鈕；點標題列角落沒反應 | `ID_NO` |
| 是 = `放棄變更(&D)`，否 = `返回編輯(&B)` | 沒反應 | 沒反應（2 次中 2 次） | 沒有；沒反應 | `ID_NO` |
| 是 = `返回編輯(&B)`，否 = `移除並儲存(&S)`，YES_DEFAULT | 沒反應 | **`ID_NO`：移除並儲存** | 沒有；沒反應 | `ID_YES` |
| 系統文字 是(Y)／否(N)（同現有四個） | 沒反應 | 沒反應 | 沒有；沒反應 | `ID_NO` |
| 同第一列，但便捷鍵改為 R | 沒反應 | 沒反應 | 沒有；沒反應 | |

追加實測的結果：

- Alt+Numpad4 會按下 `放棄變更(&D)`。
- Alt+Numpad2 會按下 `返回編輯(&B)`。
- 從 frame 跳出時，Alt+F4 一樣按下 `移除並儲存(&S)`。
- **在系統框中，Alt+F10 會按下 `是(Y)`。**

規則（見 README）：按住 Alt 再按某個鍵，會按下便捷鍵字元碼等於該鍵虛擬鍵碼的按鈕，與按鈕位置無關：F4 = 0x73 = `s`、Numpad4 = 0x64 = `d`、F10 = 0x79 = `y`。a–z 每個字母都對應得到一個鍵：a–i 是 Numpad1–9，j–o 是數字鍵盤的運算鍵，p–z 是 F1–F11。F-11 規劃時的實測也是這個現象。

## 決定

**D1. 轉換的文件已不是開啟中的文件時，失敗框之後的焦點（第 1 項，U1）。**

- 在 `ConversionPresenter._on_job_failure` 的手動分支：`show_error` 之後，若工作的文件已不是開啟中的文件，就呼叫 `self._view.focus_source_editor()`。條件與 `_name_unopened_document` 加上文件名稱的條件相同：`target.document_name is not None and target.document_name != self._documents.open_document_name`。plan 把這個條件抽成一個 helper（例如 `_left_document(target) -> bool`），兩處共用，訊息與焦點就不會不一致。
- 各失敗路徑的焦點：

  | 路徑 | 框 | 框按掉後的焦點 |
  | --- | --- | --- |
  | 手動，啟動時的文件已不是開啟中的文件（轉換中用 Ctrl+Tab 切換，或匯入開啟了別的文件） | `無法轉換文件「X」。` + 原因 | **開啟中文件的原文編輯框**（新；與 F-9 M-6 相同，只在主視窗為使用中時） |
  | 手動，啟動時的文件仍開著（沒切換，或切走又切回） | 只有原因 | 不變：停在 wx 留下的地方（點字結果框；見 O1） |
  | 手動，啟動時沒有文件（之後有沒有開啟都一樣） | 只有原因 | 不變 |
  | 匯出（單一匯出或「全部匯出」的一步） | 匯出協調器的框或摘要 | 不變 |

- 呼叫放在 `show_error` 返回之後，在既有的 `try` 之內、`_finish_completion` 之前，與 `_complete_manual` 的位置相同。排在後面的工作照舊在呼叫焦點之後才開始。
- 不新增字串。

**D2. 主視窗顯示後才載入工作區並顯示啟動提示框（第 2 項，U2）。**

- `BrailleFrame.__init__` 不再載入工作區。最後一步改成輕量的步驟，讓視窗處於明確的空白狀態：`_clear_document_editors()` 與 `_update_window_title()`（標題 `DotExpress`）。
- 原本的 `_load_startup_documents` 改為公開的 `load_startup_documents()`，內容相同（`_clear_document_editors`、`_load_workspace_documents_at_startup`、`_update_window_title`、`input_txt.SetFocus()`），另加兩個防護：
  - 只執行一次。
  - 視窗已關閉（`_close_finished`）時不做任何事，也就是延後的呼叫執行前就已經關閉或登出的情況。
- `BrailleApp.OnInit`：在 `self.frame.Show()` 之後呼叫 `wx.CallAfter(self.frame.load_startup_documents)`，接著照舊 `start_client_init_background(config_store)`。這個呼叫在主迴圈處理第一批待處理事件時執行，那時 frame 已經可見，每個啟動提示框的擁有者都是可見的視窗。
- 其他都不變：提示框的順序（無效檔案 → 已復原 → 已取代，或預設文件的存檔錯誤）、文字、保留／刪除的結果、預設文件的命名規則（`new`、`new (2)`）、載入後的標題，以及最後焦點在原文編輯框。
- 使用者看到的：主視窗先出現，文件清單空白、標題 `DotExpress`，緊接著第一個框出現在它上面；不需要框時，清單稍後一瞬間就填入。NVDA 先報讀主視窗，再報讀框。
- 為什麼延後整個載入而不只延後框：無效檔案的回答決定 `_ensure_open_document_exists` 選第一份文件或預設名稱之前有哪些檔案。只延後框會改變這些結果，或需要第二輪處理。

**D3. 轉換執行緒還活著時，結束程式不釋放轉換執行環境（第 3 項，U3）。**

- `ConversionPresenter` 新增查詢工作執行緒的方法（例如 `worker_alive() -> bool`），回傳 `self._runner.is_running()`。執行緒還在跑時，`shutdown()` 之後也維持 true。`ConversionPresenter.is_running()` 的意思不變（有工作進行中或排隊中）。
- `BrailleFrame` 提供這個查詢（例如 `conversion_worker_alive()`）。
- `BrailleApp.OnInit` 保存一個讀 presenter、而不是讀 frame 的 callable（例如 `self._conversion_worker_alive = self.frame.conversion_worker_check()`，傳回 presenter 的 bound method）。`OnExit` 可能在 frame 被銷毀後才執行（wx 的 end-session 路徑），所以不能碰 wx frame。
- `BrailleApp.OnExit`：
  1. 照舊 `cleanup_dual_view_html`。
  2. `runtime is not None` 時，只在沒有活著的執行緒時才 `runtime.close()`。沒有這個 callable（沒有建立 frame，例如現有測試）時視為「沒有活著的執行緒」。
  3. 回傳 0。
- 執行緒活著時，整個 `runtime.close()` 都跳過，liblouis 和 MathCAT 的回呼都不執行（執行緒可能在任一個裡面）。程序在 `OnExit` 之後就結束，記憶體由 Windows 回收。不 join、不等待：Windows 給結束中工作階段的時間很短，而轉換可能要很多秒。
- 不寫 log（O4）。關閉時的否決、`shutdown()`、job runner 都不變。

**D4.（第 4 項屬於 F-14。）**

**D5. 第 5 項不做：F-11 的兩個框維持 `wx.GenericMessageDialog`（U4 的前提不成立）。**

- 實測（現況「實測」）顯示：從編輯器跳出、按鈕文字為 `移除並儲存(&S)` 的系統是／否框，按 **Alt+F4** 會按下這個按鈕，與它的位置或預設按鈕無關。這正是 U4 的前提所禁止的。依 U4（「若會觸發，就不改，回報使用者」），什麼都不改：`ui/message_box.confirm_box`、`_confirm_hidden_rows`、`_on_cancel` 及其測試維持原樣，並回報使用者。
- 「尚未儲存的變更」框單獨來看，使用者指定的三個按鍵都能通過；但 Alt+Numpad4 會按下 `放棄變更(&D)`，而且這一項要求兩個框一起改。
- 使用者之後可以選擇替代做法（Q1）；F-13 沒有任何程式碼依賴它。

**D6. 移除清單顯示原始注音（第 6 項，U5）。**

- `_hidden_row_line` 改成 `bopomofo=row.braille`（不去空白）。「沒有來源文字」那一行與來源文字（`text=row.text.strip()`）不變：U5 只提到注音。
- 值在 `「` 與 `」` 之間，原樣顯示讀到的內容，包括空白、tab 與全形空白。CSV 引號欄位裡的換行也會照樣換行（O5）。不加標註，不新增字串。

## 各路徑改前與改後

| 路徑 | 改前 | 改後 |
| --- | --- | --- |
| 轉換 `alpha`，Ctrl+Tab 到 `beta`，轉換失敗 | 框 `無法轉換文件「alpha」。…`；之後焦點在 `beta` 的點字結果框 | 同樣的框；之後焦點在 `beta` 的原文編輯框 |
| 轉換 `alpha`，沒切換，轉換失敗 | 只有原因的框；焦點在點字結果框 | 不變 |
| 單一匯出或「全部匯出」的一步失敗 | 匯出的框 | 不變 |
| 啟動時有中斷的存檔或改名 | DotExpress 還沒有任何可見視窗時就出現「已復原文件」；之後才是主視窗 | 先出現主視窗（標題 `DotExpress`，清單已填入，尚未開啟文件），框在它上面；按確定之後同改前 |
| 啟動時有含 U+0000 的文件 | 主視窗出現前就出現「已取代字元」 | 先出現主視窗（`alpha - DotExpress`，文字已載入），框在它上面 |
| 啟動時有無效的工作區檔案 | 主視窗出現前就出現無效檔案對話框 | 先出現主視窗，對話框在它上面；保留或刪除同改前 |
| 啟動時不需要任何框 | 主視窗出現時第一份文件已開啟 | 主視窗出現，文件稍後一瞬間開啟 |
| 轉換中收到 WM_ENDSESSION | 結束碼 0，偶爾 `0xC0000374` | 結束碼 0（不在執行緒底下釋放 liblouis） |
| 正常結束，沒有轉換在跑 | `runtime.close()` | 不變 |
| 移除清單，檔案值 `ㄇㄚ␠␠` 或 `␠ㄇㄚ` | `「ㄇㄚ」` | `「ㄇㄚ␠␠」`、`「␠ㄇㄚ」` |
| F-11 的兩個框、四個是／否框 | | 不變 |

## 各檔案的設計

### `client/ui/conversion_presenter.py`（4 個空白）

- D1：「工作的文件已不是開啟中的文件」的 helper，由 `_name_unopened_document` 與 `_on_job_failure` 共用；手動失敗分支呼叫 `focus_source_editor()`。
- D3：`worker_alive()`。

### `client/gui.py`（tab）

- D2：`__init__` 的最後一步；`load_startup_documents()`（由 `_load_startup_documents` 改名，加兩個防護）；`BrailleApp.OnInit` 在 `Show()` 之後以 `wx.CallAfter` 排入。
- D3：`BrailleFrame.conversion_worker_check()`（或同等、交出 presenter 查詢的方法）；`BrailleApp.OnInit` 保存 callable；`BrailleApp.OnExit` 在它回傳 true 時跳過 `runtime.close()`。

### `client/dialog.py`（tab）

- D6：`_hidden_row_line`。

### catalog

最後重新產生一次 `dotexpress.pot` 與 `zh_TW/LC_MESSAGES/dotexpress.po`，讓 `#:` 參考不過時（`gui.py`、`dialog.py`、`conversion_presenter.py` 的行號會移動）。msgid、msgstr 都不變。`dotexpress.mo` 必須與 `a147fed` 的位元組相同。`POT-Creation-Date` 不變，同 F-12。

### 不改

`client/ui/message_box.py`（D5）、`conversion/jobs.py`（已有 `is_running`）、`conversion/contracts.py`、`client/braille/` 底下所有檔案、`dictionaries/`、匯出協調器、四個是／否框、fixture。

## 維持不變的部分

- 每個框的文字、標題、按鈕、預設按鈕與便捷鍵。
- 啟動時提示框的順序與結果，以及啟動後的文件、標題、焦點。
- 轉換中關閉的否決（F-9 D8）、關閉時存檔（F-5），以及工作階段訊息的回覆。
- 轉換結果：兩個 golden fixture 的 sha256 不變。
- 編輯器的載入、儲存、隱藏列與修改判斷（F-11），只有 D6 的清單文字改變。

## 使用者可見字串

無。msgid 維持 407 個，`.mo` 位元組不變。

## 無障礙（NVDA）

- D1：失敗框之後，NVDA 報讀的是原文編輯框（可編輯，內容是開啟中文件的文字），而不是唯讀的點字結果框，使用者可以直接打字。
- D2：啟動提示框成為可見主視窗所擁有的一般對話框。NVDA 先報讀主視窗，再報讀框（標題、內容、有焦點的按鈕）。Alt+Tab 會列出主視窗，選它就回到框。NVDA 是否完整報讀是手動項目 131。
- D6：NVDA 是否念出頭尾空白取決於它的標點符號層級。`「」` 標出值的起訖，螢幕與點字顯示器上都看得到。依 U5 不另加標註。

## 測試計畫

可行的話，每個測試都先在 `a147fed` 上寫成失敗（red）。

### A. 失敗後的焦點（`tests/test_conversion_presenter.py`）

1. **改** `test_a_failure_after_switching_names_the_document`：事件在 `show_error` 之後以 `("focus_source_editor",)` 結束。（red）
2. 新測試：啟動時的文件被匯入取代（`documents.open_document` 開了新名稱）後失敗，同樣以呼叫焦點結束。（red）
3. 不改、仍釘住「沒有呼叫焦點」：`test_a_failure_of_the_open_document_is_not_named`、`..._after_switching_away_and_back_...`、`..._without_a_starting_document_...`、`test_manual_failure_shows_error_after_busy_off`、`test_export_failure_calls_only_on_error`。
4. 新測試：失敗的工作後面排著另一個工作時，呼叫焦點在排隊的工作開始之前（事件順序）。（red）

### B. Show 之後才啟動載入（`tests/test_gui_document_flows.py`）

1. **改** `DocumentControllerOwnershipTest.STARTUP_STEPS`：`__init__` 的最後一步是新的輕量步驟，不是 `load_startup_documents`。新測試：建立 frame（啟動步驟已 patch）時，不呼叫 `load_startup_documents`，也不呼叫工作區服務的 `load_documents`。（red）
2. **擴充** `test_app_startup_runs_steps_in_contract_order`：`gui.wx.CallAfter` 換成 `DeferredCalls` 佇列，並記錄 frame 的 `load_startup_documents`。順序是 `["prepare", "cleanup", "runtime", "frame", "show", "client_init"]`；執行佇列後再加上 `"load"`，所以載入在 `show` 之後。（red）
3. 新測試：`_close_finished` 之後呼叫 `load_startup_documents` 不做任何事（不載入工作區、沒有框）。（red）
4. 新測試：第二次呼叫 `load_startup_documents` 不做任何事。（red）
5. 新測試：`load_startup_documents` 之後，框的順序同舊（無效檔案、已復原、已取代），最後是 `input_txt` 的焦點呼叫。使用 `_load_workspace_documents_at_startup` 那些測試現有的假物件。
6. 不改：直接呼叫 `_load_workspace_documents_at_startup` 的八個測試。

### C. 結束（`tests/test_gui_document_flows.py`、`tests/test_conversion_presenter.py`）

1. 新測試：`OnExit` 的「執行緒活著」callable 回傳 `True` 時，不呼叫 `runtime.close()`，但仍清理雙視窗資料夾並回傳 0。（red）
2. 新測試：callable 回傳 `False` 時，`runtime.close()` 呼叫一次。
3. 不改：現有四個 `OnExit` 測試（沒有 frame，所以沒有 callable：執行環境會關閉）。
4. 新測試：`OnInit` 保存的 callable 不碰 frame。`OnInit` 之後讓 frame 的 `Mock` 對任何屬性存取都拋出 `RuntimeError`，呼叫它仍然有回應。（red）
5. presenter 測試（`make_thread_factory` 的 `FakeThread`）：
   - 沒有工作時 `worker_alive()` 是 `False`。
   - 執行緒在跑時是 `True`，`shutdown()` 之後也是。
   - 執行緒結束後是 `False`。（新方法，red）

### D. 移除清單（`tests/test_dictionary_entries_dialog.py`）

1. **改** `test_a_row_line_shows_the_stripped_source_text_and_sequence`：預期的行中來源文字去空白（`肚子`），注音保持原樣（`␠ㄉㄨˋ|ㄗ˙␠`）。改名，例如 `test_a_row_line_shows_the_stripped_source_text_and_the_raw_sequence`。（red）
2. 新測試：檔案值 `ㄇㄚ␠␠`、`␠ㄇㄚ`、`ㄇㄚ\t`、`ㄇㄚ\u3000` 各自原樣出現在清單的行中。（red）
3. 不改：`test_a_row_without_its_tone_space_is_hidden_and_listed_on_ok`、trace 重放、F-11 所有確認框的測試（D5）。

### E. 刻意不改

`tests/test_message_box.py`、`tests/test_wx_call_sites.py`（D5）。

### Mutation check（由 plan 執行；每個都必須被抓到）

1. D1 每次手動失敗都呼叫焦點。
2. D1 在 `show_error` 之前呼叫焦點。
3. D1 從不呼叫焦點。
4. D1 條件相反。
5. D2 仍在 `__init__` 中載入。
6. D2 在 `Show()` 之前排入載入。
7. D2 沒有 `_close_finished` 防護。
8. D2 沒有只執行一次的防護。
9. D3 一律 `close()`。
10. D3 從不 `close()`。
11. D3 `worker_alive` 讀 presenter 的 `is_running()`（進行中或排隊中）而不是讀執行緒。
12. D3 callable 讀 frame。
13. D6 保留 `.strip()`。
14. D6 只做 `.rstrip()`。
15. D6 來源文字不再去空白。

### 數量

約 14 個新測試、4 個修改（A 新 3、改 1；B 新 4、改 2；C 新 4、presenter 3；D 新 1、改 1）。確切的 `Ran` 由 plan 訂定；`a147fed` 的完整測試是 `Ran 1632`、`OK (skipped=6)`。

## 實作步驟（每步一個綠色 commit，先寫 red）

1. `fix: focus the source editor after a failed conversion of a document that is no longer open (F-13)`：D1；測試 A。
2. `fix: show the startup boxes after the main window (F-13, F-8b review M-8)`：D2；測試 B。
3. `fix: keep liblouis loaded at exit while a conversion is still running (F-13, F-9 review M-8)`：D3；測試 C。
4. `fix: list the Bopomofo value of a hidden row as it is in the file (F-13)`：D6；測試 D；更新 catalog 的 `#:`。

依 HANDOFF 第 5 節，每個 commit 只 stage 明確的路徑，結尾不加 `Co-Authored-By`。若有兩步都移動了 msgid 上方的行號，plan 可以把 catalog 更新移到最後一個 commit `chore: refresh catalog references (F-13)`。

## 驗收條件

在 Windows 的 `client/` 用主 checkout 的 `.venv` python 執行；執行檔案依 F-3 plan Task 0 複製，絕不 stage。

1. 完整測試：沒有失敗、沒有錯誤；`Ran` 依 plan；`OK (skipped=6)`。
2. 重點測試：`-m unittest tests.test_conversion_presenter tests.test_gui_document_flows tests.test_dictionary_entries_dialog tests.test_message_box tests.test_wx_call_sites tests.test_i18n -v` 通過。
3. catalog：407 個 msgid，全部已翻譯，0 fuzzy；`.mo` 的 sha256 與 `a147fed` 相同；沒有過時的 `#:`（重新產生沒有差異）。
4. 三個 fixture 的 sha256 不變（HANDOFF 第 5 節）。
5. 使用者資料未動：主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 不變，worktree 也不產生這些檔案。
6. `git diff main --stat` 只包含 `client/ui/conversion_presenter.py`、`client/gui.py`、`client/dialog.py`、catalog、上列測試，以及 spec、plan、history 檔案；`client/ui/message_box.py` 不變。
7. 上面的 mutation check。
8. 下面的打包版 GUI 驗證，結果放在 history 資料夾。

## Windows 驗證（打包版）

規則同 F-12，加上 HANDOFF 第 3 節的更新：

- 打包時把主 checkout 的 `client/.venv/Scripts` 放在 `PATH` 最前面，再執行 `scripts/build-dotexpress.bat`；在 `PYZ-00.toc` 確認改過的模組來自 worktree。
- 新版放在 `D:/dxtest/N-f13/`，舊版是 `D:/dxtest/N-f12b`。
- 每個項目在新的 `D:/dxtest/auto<item>-f13`（或 `-f12b-f13`）資料夾用 exe 副本執行；只結束這些資料夾底下的程序；每個項目開始前確認可用記憶體至少 600 MB，一次只跑一個。
- **修正項目**新舊版都跑；**回歸項目**只跑 `N-f13`，結果不符預期時才補跑 `N-f12b`。
- 腳本都經過 F-11／F-12 的 `safe_run.py`：DotExpress 在前景時才送按鍵，log 不記錄其他程式的名稱。**沒有任何腳本讀寫剪貼簿。** 檔案由腳本在啟動前寫入。
- **啟動輔助程式。** 舊的輔助程式（`f8bgui.start`、`B.start`、`dx.launch`）只要出現標題為 `…DotExpress` 的視窗就返回。在 `N-f13` 上，這個視窗會比啟動提示框、也比文件載入更早出現。plan 新增 `f13gui.start(d)`，做法如下：
  1. 等主視窗出現。
  2. 然後像舊的輔助程式一樣回答無效檔案對話框（保留）與每個框（Enter）。
  3. 每個框都記錄 `main_visible`（主視窗的 `IsWindowVisible`）、`owner_is_main`（`GW_OWNER` 是主視窗）與當時主視窗的標題。
  4. 主視窗已啟用、程序的框已有 1 秒沒出現，而且標題不只是 `DotExpress` 或文件清單不是空的，才返回。

  在 `N-f12b` 上，同一個輔助程式會記錄在任何主視窗出現前看到的框。先前項目的回歸重跑都改用這個輔助程式。

| # | 類別 | 步驟 | N-f13 的預期 | N-f12b |
| --- | --- | --- | --- | --- |
| 121 | 修正 | `preprocessing.py` 的 `main` 先睡 5 秒再拋出 `ValueError("boom")`（F-12 項目 115）。(a) 開啟 `alpha`，Ctrl+Enter，立刻 Ctrl+Tab 到 `beta`，等框出現，按 Enter。(b) 同 (a) 但不按 Ctrl+Tab | (a) 框 `無法轉換文件「alpha」。` + `文字處理失敗：boom`；按 Enter 後焦點在 `beta` 的原文編輯框（`('Edit', '來源文字')`，已啟用），`beta` 的編輯框不變。(b) 框 `文字處理失敗：boom`；按 Enter 後的焦點與改前相同（記錄下來；預期是點字結果框） | (a) 焦點在 `beta` 的點字結果框；(b) 同 N-f13 |
| 122 | 修正 | F-8b 項目 70 的工作區（中斷的改名 `alpha` → `gamma`），用 `f13gui.start` 啟動 | 「已復原文件」框（名稱 `alpha`），`main_visible True`、`owner_is_main True`，主視窗標題 `DotExpress`；按 Enter 後 `docs ['alpha']`、標題 `alpha - DotExpress`、焦點在原文編輯框；檔案同 F-8b 70 | 看到框時沒有可見的主視窗 |
| 123 | 修正 | F-8b 項目 73 的工作區（`alpha.dep` 含 U+0000） | 「已取代字元」框（`alpha`、2 個），`main_visible True`、`owner_is_main True`，主視窗標題 `alpha - DotExpress`；之後同 F-8b 73 | 主視窗出現前就有框 |
| 124 | 修正 | F-8a 項目 66 的工作區（`alpha.dep` 有效、`bad.dep` 無效）；選保留 | 無效檔案對話框（`['bad.dep']`），`main_visible True`、`owner_is_main True`；之後 `docs ['alpha']`，焦點在原文編輯框 | 主視窗出現前就有對話框 |
| 125 | 修正 | 同一個工作區同時有三種情況：無效的 `bad.dep`、`alpha` 中斷的改名，以及含 U+0000、在清單中排在 `alpha` 之後的 `beta.dep`；選保留 | 框依舊順序出現：無效檔案對話框、「已復原文件」，第一個開啟的文件含 U+0000 時再出現「已取代字元」。每個都是 `main_visible True`、`owner_is_main True`。最後的標題、文件、焦點與 N-f12b 相同。（名稱由 plan 安排，讓開啟的那份文件含 U+0000） | 順序相同，但都在主視窗出現前 |
| 126 | 回歸 | 用 `f13gui.start` 重跑：F-8b 70、70b、71、72、73；F-8a 66、69、79；F-12 113（啟動與新增的部分）；再加上一般啟動（只有一份有效的 `alpha`，沒有框），以及在空資料夾第一次啟動 | 每一行記錄都與原 log 相同，只有框相對於主視窗出現的時機不同；一般啟動：沒有框，`docs ['alpha']`，標題 `alpha - DotExpress`，焦點在原文編輯框；空資料夾：`docs ['new']` | （結果不符時才跑） |
| 127 | 修正 | F-9 項目 93 的工作區（`alpha` 待轉換的長文字、`beta`）。**20 次**，每次重新啟動：對 `alpha` 按 Ctrl+Enter；1 秒後送 `WM_QUERYENDSESSION`（`ENDSESSION_LOGOFF`）；再送 `WM_ENDSESSION`（wParam 1）；在 10 秒內讀結束碼 | 每次查詢都在 2 秒內回傳 0；**20 次的結束碼都是 0，從不出現 `-1073740940`（`0xC0000374`）**；`alpha.dep`、`beta.dep` 可讀；`gui.log` 沒有新的行 | 記錄 `-1073740940` 出現的次數（F-9 約 5 次中 1 次）。若 N-f12b 20 次都沒出現，GUI 證據不足：記錄下來，本項仍以 N-f13 的 20 次正常結束加上測試 C 判定通過 |
| 128 | 回歸 | F-9 項目 93（完整腳本）；F-7 項目 59（沒有要存的內容時送 `WM_QUERYENDSESSION`：結束碼 0）；轉換完成後一般關閉（F-12 項目 118 (a)，然後關閉） | 同原 log；一般關閉的結束碼是 0 | （結果不符時才跑） |
| 129 | 修正 | 字典 `raw.csv`：`text,braille,type` / `抹,ㄇㄚ␠␠,Bopomofo` / `媽,␠ㄇㄚ,Bopomofo` / `甲乙,⠁⠃,Braille`。編輯後按確定，用 UIA 讀框的文字；按返回編輯；再按確定、移除並儲存 | 清單中的行是 `第 2 列：「抹」的注音「ㄇㄚ␠␠」格式不正確` 與 `第 3 列：「媽」的注音「␠ㄇㄚ」格式不正確`（保留空白）；之後檔案只剩 `甲乙` | 兩行都是 `「ㄇㄚ」` |
| 130 | 回歸 | F-11 項目 95、99（兩個確認框；Esc、Enter、Alt+F4、關閉鈕） | 同 N-f11 的 log（D5：框不變；`dict_badbopo.csv` 的值前後沒有空白，所以清單文字也相同） | （結果不符時才跑） |

絕不觸發真的登出或關機；127、128 只把工作階段訊息送給 DotExpress 的主視窗。

**使用者的手動項目（項目 131，NVDA）：** 開著 NVDA 執行 `D:/dxtest/N-f13`：

1. 用項目 125 的工作區啟動（plan 會複製一份到 `D:/dxtest/manual131-f13/`）。NVDA 是否先報讀主視窗，再完整報讀每個啟動提示框？框開著時，Alt+Tab 是否列出 DotExpress，選它是否回到框？
2. 項目 121 (a)：失敗框之後，NVDA 是否報讀原文編輯框？
3. 項目 129：NVDA 怎麼念含 `ㄇㄚ␠␠` 的那一行？

## 風險

- **文件載入前視窗已可見**（低）：主視窗會有一瞬間是空的，標題 `DotExpress`。這一瞬間按的鍵作用在空視窗上，就像「全部刪除」之後。載入通常在第一個使用者輸入到達前就已排入。
- **延後載入前就關閉**（低）：由 `_close_finished` 防護（測試 B3）。啟動提示框開著時收到 WM_QUERYENDSESSION，行為與現在相同：frame 的關閉處理以當時已載入的內容執行。框返回後，載入就停止（規劃後的修正 10，review M-2）。
- **GUI 輔助程式**（中，機械性）：在新版上，先前所有的啟動輔助程式都會太早返回。啟動相關項目由項目 126 與新的輔助程式處理；其他會啟動程式的回歸腳本必須改用 `f13gui.start`，或等文件載入完成。
- **end-session 路徑**（低）：「wx 在 WM_ENDSESSION 時呼叫 `OnExit`」是閱讀 wx 原始碼的判斷，不是實測。若那時沒有呼叫 `OnExit`，D3 對登出沒有作用，項目 127 會出現和 N-f12b 一樣的結束碼。即使如此，測試仍釘住 `OnExit` 的規則，這個規則也涵蓋無法否決的關閉之後的一般結束。
- **記憶體沒有釋放**（無）：程序在 `OnExit` 之後就結束。
- **含控制字元的原始值**（低）：tab 顯示為 tab；引號欄位中的換行會讓清單的那一行斷開（O5）。
- **F-14 rebase**（低，機械性）：見「與 F-14 的關係」。

## 待決問題

**使用者已決定（2026-10-14）：** U1–U5。D5 依 U4 本身對前提不成立的規定處理。

**協調者採用建議預設（使用者可在 merge 前推翻）：**

- **O1.** D1 只適用於工作的文件已不是開啟中的文件，依使用者的措辭。開啟中文件的轉換失敗後，焦點仍停在 wx 留下的地方（點字結果框），與 F-9 之前相同。要延伸到這種情況只需改一行。
- **O2.** D2 延後整個工作區載入，不只延後框，好讓無效檔案的回答仍在選定預設文件之前。主視窗會有一瞬間是空的。
- **O3.** D2 在 `Show()` 之後立刻用 `wx.CallAfter` 排入載入，不等視窗繪製或啟用。項目 125 記錄 `main_visible`；若 NVDA 漏掉主視窗（項目 131），plan 可以改用 `EVT_ACTIVATE`／`EVT_SHOW` 觸發。
- **O4.** D3 跳過整個 `runtime.close()`（liblouis 與 MathCAT），不 join 執行緒，不寫 log。
- **O5.** D6 原樣顯示讀到的值，包括 tab、全形空白與引號中的換行；來源文字仍去空白。

**給使用者的問題**（不阻擋；F-13 不等回答繼續進行）：

- **Q1. 前提不成立後的第 5 項。** 在自訂按鈕文字的原生是／否框中，按住 Alt 再按某個鍵，會按下便捷鍵字元等於該鍵虛擬鍵碼的按鈕。Alt+F4 對應 `s`，會按下「移除並儲存(S)」。選項：
  - (a) **建議：** 兩個 F-11 的框維持原樣（傳統的 `GenericMessageDialog`：Esc、Enter、Alt+F4、關閉鈕都等於返回編輯）。F-13 就是這樣做。
  - (b) 改用系統框，並把「移除並儲存」的中文便捷鍵從 S 換成別的字母；msgstr 改變，msgid 不變。這樣 Esc、Alt+F4、關閉鈕都不會有反應（已用 R 實測）。但仍有別的 Alt+鍵會按下肯定按鈕：R 是 Alt+F3，放棄變更(D) 是 Alt+Numpad4。
  - (c) 其他設計，留待之後的任務。
- **Q2. 現有四個是／否框與 Alt+F10。** 實測發現：從對話框跳出的系統是／否框，按 Alt+F10 會按下「是(Y)」。字典刪除確認框就是這樣跳出的。從主視窗跳出的三個框（刪除文件、全部刪除、覆寫確認）沒有實測。這是既有行為，不在 F-13 範圍（使用者決定這四個框維持現狀）。僅回報；使用者需要的話再列為後續項目。

## 本 spec 引入、使用者尚未決定的可見預設

1. O1 的焦點規則（開啟中文件失敗時不變）。
2. 啟動時主視窗有一瞬間是空的（O2），以及 O3 的觸發方式。
3. 結束時跳過 `runtime.close()` 不寫 log（O4）。
4. 移除清單中原樣顯示控制字元與換行（O5）。

## 不在範圍內／後續項目

- **第 5 項**（D5、Q1）。
- **Alt+F10 與現有四個是／否框**（Q2；既有行為）。
- F-14：第 4、7、8 項。
- F-10（UEB 斷行、`$`）。
- 使用者 2026-10-14 決定延後或不修的：匯出 `.tmp` 重試、表頭不分大小寫、F-9 M-5（情況 (b) 存檔失敗的結果在關閉時遺失）、`config.json` 損壞的提示、F-11 M-4。
