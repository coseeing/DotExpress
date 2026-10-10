# 轉換結果寫回正確的文件（F-9）設計

## 目標

任務 F-9 修正「進行中的轉換」與「使用者正在操作的文件」之間的競態（`task.md` 排序建議第 2 項「F-9」）。範圍是 P1-4 spec（`docs/superpowers/specs/2026-10-08-p1-4-export-conversion-presenters-design.md`，「Known defects found during this investigation」）的三個已知缺陷，再加上修正本身所依賴的另一個缺陷：

1. **P1-4 defect 1。** 手動轉換進行中，使用者仍可切換文件（Ctrl+Tab、Ctrl+Shift+Tab、Ctrl+PageUp、Ctrl+PageDown）或匯入文件（Ctrl+O）。結果會寫進轉換完成當下開著的那份文件。下一次存檔再把它寫進那份文件的 `.dep`（見下方探測 1）。輸出靜默錯位，沒有任何提示。
2. **P1-4 defect 2。** `ConversionPresenter.convert_for_export` 不檢查是否已有工作在跑。第二個工作（點字結果編輯框中的 Ctrl+S，或「全部匯出」的某一步）會靜默取代第一個，第一個的結果被丟掉：手動轉換的輸出永遠不顯示、單一匯出永遠不寫檔、「全部匯出」的鏈中斷且沒有摘要（探測 2、3）。
3. **P1-4 defect 3（`task.md` #11）。** 匯出待轉換文件為 HTML 時會先轉換，但匯出沒有使用那次轉換的 `dual_view_segments`，而是寫出雙視快取。待轉換文件的快取是空的，所以檔案是「No conversion data」頁面（探測 4）。
4. **P1-4 defect 6**（納入範圍，D7）。worker 拋出非 `ConversionStageError` 的例外時什麼都不投遞，UI 一直停在忙碌狀態。D4 的佇列會讓它更嚴重：一個永遠不結束的工作會擋住之後所有工作。所以在這裡一併修正。

使用者的決定（2026-10-10，`task.md` 第三節問題 2；此處不再重新提問），記為 Decided by the user (2026-10-10)：

- **U1.** 轉換進行中**不**阻擋切換文件。結果寫回**啟動**轉換時的那份文件。

本任務完成後：

- 手動轉換的結果送到使用者按下「轉換」時開著的那份文件。那份文件若仍開著（或又被切回來），一切與今天相同。若開著的是別份文件，開著文件的點字編輯框與雙視都不動。結果存進原本那份文件的記憶體與磁碟，並有訊息說出那份文件的名稱。訊息框關閉後，焦點在開著文件的原文編輯框（F-9 審查 M-6）。
- 若原本的文件已不存在，或它的文字已和轉換時不同，結果會被丟棄並寫進 log。這在今天的 UI 中不可能發生（D3）。
- 在另一個轉換進行中或正在收尾時要求的匯出轉換，會在佇列中等待，之後再執行。不會丟掉任何結果。每個完成各自顯示自己的訊息，依要求的順序。
- 匯出待轉換文件為 HTML 時，顯示這次新轉換的內容。
- 任何種類的 worker 錯誤都會以既有的「Translation failed: {error}」訊息結束忙碌狀態，並寫進 log。
- 視窗關閉後，晚到的轉換結果一律忽略（P1 審查 M-10）。

新的使用者可見字串：**一個**（D2）：`Conversion completed. The result was saved to document "{name}".`。msgid 數量從 364 變成 365。F-8 可能先新增字串；plan 會在 F-8 之後的 `main` 上重新計數。

非目標：

- 忙碌時阻擋快速鍵（U1 已否決）；
- 改變忙碌時哪些指令可用；
- 「全部匯出」摘要文字（P1-4 defect 4；F-12）；
- 讓雙視資料在重新啟動後保留（見「不在範圍內」）。

## 與 F-8 的關係（資料安全）

F-8（其餘寫入改為原子寫入、孤兒 `.tmp` 回收、載入與匯入時把 U+0000 換成 U+FFFD）正平行撰寫 spec，可能會先 merge。本 spec 的寫法要能承受這點：

- 程式碼以函式命名，不以行號。下列行號取自 `main` `861d110`，僅供定位。
- 唯一新增的磁碟寫入（D1）經由 `DocumentWorkspaceService`，使用與 `save_open_document` 相同的 `save_document_package` 呼叫。F-8 在那裡做的任何改變（存在性檢查、正規化）都會自動套用。`save_open_document` 與新的 `save_document` 共用同一段主體，兩條路徑不會分歧。
- D3 的文字檢查比對記憶體中文件的文字與被轉換的文字。兩者都來自同一個編輯框讀取（`BrailleFrame._editor_text`）。有一個測試釘住「切走時的存檔所存的文字，正是 `get_source_text()` 回傳的文字」（測試計畫 E14）。如果 F-8 在那條路徑上多做了正規化，該測試會顯示出來。
- plan 會在 F-8 之後的 `main` 上重新取得基準數字（`Ran`、msgid）。Windows 驗證項目排在 F-8 之後（此處以 `9a`-`9i` 作為佔位）。

## 規劃後的修正（F-9，2026-10-10）

plan（`docs/superpowers/plans/2026-10-10-f9-conversion-target-document.md`）在 spec commit `a39d207` 的 scratch clone 上完整 dry run。`a39d207` 位於 `main` `7aba2be` 之上（F-8a、F-8b 之後）。重新從頭 replay 時，每個紅燈與綠燈輸出、翻譯檔步驟、每個 commit 的 tree id、打亂順序的 seed 與 30 個 mutant 都吻合；每一步也用 plan 自己的區塊腳本套用過；同一份程式碼的 packaged build 與 `D:\dxtest\N-f8b2`（「改前」build，即 `7aba2be` 的程式碼）都跑過 Windows 項目。D1-D9 每個決定、行為對照表、轉換進行中仍可操作的清單，都已對照 `7aba2be` 重新確認，仍然成立。F-8 沒有改到 `ui/conversion_presenter.py`、`conversion/jobs.py` 與 `documents/export_coordinator.py`，上文這些檔案的行號仍正確。修正與補充如下：

1. **基準與數量。** 在 `7aba2be` 上，測試得到 `Ran 1444`、`FAILED (errors=1, skipped=7)`（只有 F-W6），翻譯檔有 **368** 個 msgid。D2 的 msgid 使數量成為 **369**，不是 364 -> 365。F-9 新增 34 個測試（另有 5 個翻轉）：五個步驟後的 `Ran` 依序是 1445、1450、1459、1461、1478。驗收條件 2 的模組組合從 `Ran 330` 變成 `Ran 363`、`OK`。測試計畫 A-E 之外還有一個翻譯檔測試 F1 `test_conversion_result_saved_string_is_translated`（`test_i18n`）。
2. **移轉步驟 4 與 5 對調**：步驟 4 是 D8（`shutdown`），步驟 5 是 D1-D3 加 D9。D8 在 `gui.py` 中、好幾個 msgid 的上方加了一行。如果在翻譯檔重新產生之後才做，那些 msgid 的 `#:` 參照就會過時，「重新產生的範本只有 `POT-Creation-Date` 不同」這項檢查也會失敗。兩個步驟互不依賴；commit 標題維持上文所列。
3. **`7aba2be` 上的行號**（僅供定位）：`save_open_document` 是 `workspace_service.py:187-197`（上文：124-134）。`gui.py` 中：`_open_adjacent_document` 627-634、`_editor_text` 636-638、`on_import_document` 918-946、`on_output_text_key_down` 986-995、`on_char_hook` 1006-1027、`_close` 1066-1077、`_finish_close` 1092-1099、`get_source_text` 1103-1104、`set_conversion_busy` 1106-1114（上文：1080-1088 等）。
4. **D3 以 `ERROR` 層級寫 log，不是 `WARNING`。** `dotexpress.gui` 與它的 `gui.log` handler 都以 `log.get_logger` 的預設層級 `ERROR` 建立，`WARNING` 永遠不會寫進 `gui.log`（F-8b 修正階段發現）。訊息是 `Discarded a conversion result: %s`，原因為下列之一：`document "<name>" no longer exists`、`the text of document "<name>" changed`、`document "<name>" was opened during a conversion without a document`。D7 的訊息是 `Unexpected error in a conversion job`，附 `exc_info`。兩個 logger 都在呼叫時才綁定。這是 O11。Decided by orchestrator with the recommended default; user may override before merge.
5. **`shutdown()` 之後不再開始新的工作**（D8）。`_submit` 直接返回：否則在關閉之後才執行的「全部匯出」步驟 `CallAfter` 會開始一個工作，呼叫已銷毀的 frame。「轉換中」對話框的 timer 也檢查 `_shut_down`。佇列的取出同樣檢查它，與上文相同。這是 O10。Decided by orchestrator with the recommended default; user may override before merge.
6. **測試計畫以外會改到的測試：**
   - `FrameConversionDelegationTest.test_close_asks_presenter_before_saving` 預期在存檔之後、`close_converting_dialog` 之前有 `call.presenter.shutdown()`（D8）。
   - `test_is_running_and_missing_table_message_read_live_state` 預期 worker 結束後到投遞之前，`is_running()` 仍是 `True`（D5）。
   - coordinator 的三個測試以 `ConversionOutput` 而不是字串呼叫存起來的 `on_success`；presenter 測試的 `_export_callbacks` 記錄 `output.display_text`（D6）。
7. **測試的位置與名稱。**
   - C3 是 `test_write_document_uses_the_given_results_instead_of_the_cache`：`None` 讀快取；`()` 與 tuple 照原樣使用；即使有快取，`()` 也寫出「No conversion data」。
   - D1-D5 是 `SaveOnlyWhenChangedTest` 的方法；它載入的 workspace 中 alpha 開著，待轉換的 beta 沒有開。
   - E13 在 `FrameViewMethodsTest`。
   - E3 以假的匯入對話框（`GetPaths`、`SetFilterIndex`、`GetFilterIndex`）驅動 Ctrl+O。
   - 新的 frame 測試比對訊息框時不含 frame，所以失敗訊息中不會出現物件位址。
8. **`_write_single(..., **results)`** 只有在匯出待轉換文件時才把 `dual_view_results` 傳給 `write_document`。既有的、mock `write_document` 並預期 `(path, document, format_key)` 的測試不需修改。
9. **翻譯檔。** `msgmerge` 沒有把新的 msgid 誤配成 fuzzy。參照是 `ui/conversion_presenter.py:305`。重新產生時，步驟 3-5 移動過的 `#:` 參照也一併更新。
10. **Windows 項目。**
    - 佔位的 `9a`-`9i` 依序是項目 **85-93**：F-8a 的手動項目 84 是目前用過的最後一個編號。NVDA 手動項目是 **94**。
    - 「改前」是 `D:\dxtest\N-f8b2\DotExpress.exe`，新的 build 放在 `D:\dxtest\N-f9`。
    - 慢的轉換來自腳本寫進包裡的長原文：一行 65 字元的中英混合文字重複 8000 次，共 520,000 字元，每次轉換約 15 秒。
    - 按鍵在 Ctrl+Enter 之後立刻送出，在 2 秒時「轉換中」對話框出現之前。原文編輯框停用時焦點移到點字結果編輯框，所以 Ctrl+Tab、Ctrl+O、Ctrl+S 都會到達 frame 的 char hook（已實測）。9e 與 9f 直接把焦點放到點字結果編輯框，不按 F6。
    - 腳本只在主視窗位於前景時才送按鍵，否則停止該項目。
    - dry run 實測每個項目在兩個 build 上的結果都與上表預期相同，只有 9e 與 9f 的「改前」不同（見第 14 點）。
11. **規劃時觀察到的現象（不是 F-9 造成，不阻擋）。** 在轉換進行中送出 `WM_ENDSESSION`（項目 93 的第二次轉換），有一次程序以結束碼 `-1073740940`（`0xC0000374`，程序結束時的 heap 損毀）結束，而不是 0。這在 F-9 build 的五次執行中發生一次；其他次與 N-f8b2 上的執行都以 0 結束。wx 3.2.9 在 `WM_ENDSESSION` 時不送關閉事件（F-7 項目 60），所以不會執行任何 F-9 的程式碼：是 Windows 在 worker 執行緒還在轉換器裡時結束了程序。已加入「風險」。plan 會記錄這樣的執行，並把該項目再跑一次。
12. **項目 93（9i）** 在切走之後送出 `WM_QUERYENDSESSION`：查詢立刻回傳 0，程式繼續執行，接著出現 D2 訊息框。
13. **項目 91（9g）** 也把預設文件 `new` 匯出為 HTML。它不是待轉換文件，也沒有快取，所以頁面是「No conversion data」，改前改後相同（「不在範圍內」第一項）。
14. **F-9 之前，在長轉換進行中開始第二個轉換會讓程式當掉**（規劃時實測；修正 9e、9f 的「改前」，以及對照表中「轉換中對開著的待轉換文件按 Ctrl+S」與「含待轉換文件的「全部匯出」中按 Ctrl+S」兩列的「改前」）。取代的工作在第一個還在轉換時就啟動第二個 worker 執行緒，於是兩個 liblouis 轉換同時進行。以 9e、9f 的長原文，N-f8b2 四次執行都在沒有任何訊息框的情況下結束（Windows 應用程式記錄：`ntdll.dll`，例外狀況代碼 `0xc0000374`，heap 損毀）。探測 2、3 使用假的執行緒，所以看不到這點；原文短時，第一個執行緒通常在第二個開始前就結束了。D4 一次只執行一個工作，因此也消除了這個當機。所以 defect 2 比「丟掉一個結果」更嚴重。

## 審查後的修正（F-9，2026-10-11）

審查（`docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/review_task.md`，結論「Ready to merge after the cheap Minor fixes」）帶來以下修改。與下文不一致時，以本節為準；本節改動的 D1、對照表、風險與 O10 的句子都註明審查編號。

1. **(b) 的訊息框關閉後，焦點移到開著文件的原文編輯框**（審查 M-6；D1「焦點」）。在 N-f9 上實測（審查第 2.1 節；修正階段的 `auto/focus_check.py`）：轉換開始時停用原文編輯框，焦點會移到點字結果編輯框；`_open_adjacent_document`（Ctrl+Tab）的 `input_txt.SetFocus()` 對停用的控制項沒有作用。所以焦點留在新文件唯讀的點字結果編輯框，modal 訊息框關閉後也回到那裡：鍵盤使用者要先按 Shift+Tab 或 F6 才能打字。D1 寫的「通常是剛開啟那份文件的原文編輯框」是錯的。現在 `_complete_manual` 在 (b) 的最後呼叫新的 `ConversionView.focus_source_editor()`，也就是 D2 訊息框或存檔錯誤框關閉之後。這時忙碌狀態已經結束，原文編輯框已重新啟用。frame 的實作是 `if self.IsActive(): self.input_txt.SetFocus()`：另一個視窗是作用中視窗時（例如轉換中按 Ctrl+S 開啟的檔案對話框，審查第 7 節觀察 3，或別的程式），焦點不變。(a)、(c) 與丟棄的情況不變；(a) 仍把焦點放在顯示輸出的點字結果編輯框。排在手動轉換後面的工作隨即開始，並和以前一樣再次停用原文編輯框。`ui/conversion_presenter.py` 與 `gui.py` 共新增 12 行（不計空行與註解是 8 行），沒有新字串；翻譯檔只更新 `#:` 參照。為什麼改程式而不是改 spec：spec 的原意與 NVDA 項目 94 都預期焦點在原文編輯框，而讓螢幕報讀器使用者停在唯讀欄位是比較差的預設；改動很小，並有測試釘住（B1、B3、E1、E3、E4、E14 與一個 frame 方法的測試）。在修正後的 build `N-f9b` 上實測：項目 85 與 88 的訊息框關閉後，焦點在 `beta` 的原文編輯框（已啟用）；N-f9 上則是點字結果編輯框。Decided by orchestrator with the recommended default; user may override before merge. 另一個選擇是拿掉這個呼叫，焦點就會和 N-f9 一樣停在點字結果編輯框。
2. **(b) 存檔失敗的結果，只有那份文件之後的存檔會重試**（審查 M-5；D1「為什麼立即寫入」、對照表、風險）。frame 只存開著的文件。使用者若在關閉程式前沒有再開啟起始文件，關閉時只會存開著的那份，結果就此遺失，不會有第二個訊息（第一個是存檔錯誤）。原文在磁碟上是安全的，也可以再轉換一次。讓關閉時也存下記憶體與已存紀錄不同的每份文件，屬於 F-5 的範圍；記錄給 F-12。
3. **O10 只適用於轉換**（審查 M-7；「規劃後的修正」第 5 點、O10）。`shutdown()` 之後不再開始新的轉換，所以待轉換文件的「全部匯出」步驟什麼都不做。已有點字的文件不需要轉換：它的步驟仍會寫出檔案，最後一步還會在已銷毀的 frame 上顯示摘要。F-9 之前就是如此，而且今天不會發生：沒有無法否決的關閉會落在兩個「全部匯出」步驟之間。
4. **延到 F-12，F-9 不改程式。** 審查 M-8：`BrailleApp.OnExit` 釋放 liblouis（`runtime.close()`）時，worker 可能還在裡面，這被懷疑是 `0xC0000374` 結束碼的原因（「風險」最後一項；是假設，未實測）。審查 M-9：起始文件已不是開著的文件時，手動轉換失敗的訊息「Translation failed: {error}」不會說出文件名稱；要說出名稱需要新字串。
5. **測試與數量。** 新增五個測試：`test_request_during_a_failed_completion_waits_until_it_returns`（M-1）、`test_queue_drains_when_a_failed_completion_raises`（M-2）、`test_queued_manual_job_keeps_its_target`（M-3）、`test_ctrl_s_then_ctrl_tab_during_manual_conversion`（M-4）與 `test_focus_source_editor_only_while_the_window_is_active`（M-6，`FrameViewMethodsTest`）。B1、B3、E1、E3、E4 與 E14 預期訊息框之後的焦點呼叫。審查中存活的 mutant r1、r2、r3 各自被對應的新測試抓到；M-4 沒有 mutant，它的測試抓到一個新的 mutant（r17：(b) 存檔成功後清掉佇列），其他測試都抓不到。完整測試 `Ran 1483`、`FAILED (errors=1, skipped=7)`，只有 F-W6；驗收條件 2 的組合 `Ran 368`、`OK`。Windows 項目 85、87、88、93 在 `N-f9b` 上重跑，log 與 N-f9 相同。

## 現況（2026-10-10 於 `main` `861d110`、worktree `D:\workspace\DotExpress-f9`、Windows 11 26200 驗證）

`$PY` 是 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`。依 F-3 plan Task 0 複製 runtime 後的基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 1368`、`FAILED (errors=1, skipped=7)`，唯一的 error 是 F-W6。AST msgid 掃描與翻譯檔都是 364 個 msgid。

探測程式在 session scratchpad 的 `...\scratchpad\f9\probe_f9.py`，不 commit。它繼承 `ConversionExportFlowsCharacterizationTest`（`client/tests/test_gui_document_flows.py`），使用其中的 fake：帶紀錄編輯框的 frame，以及在暫存 workspace 上真實的 `DocumentController`、`DocumentWorkspaceService` 與 `ConversionPresenter`，加上 `FakeThread`、延後執行的 `CallAfter` 與 fake timer。

### 各部分的位置

| 部分 | 位置（`861d110`） | 今天的行為 |
| --- | --- | --- |
| 手動開始 | `ConversionPresenter.convert`（`ui/conversion_presenter.py` 128-135） | `if is_running(): return`；檢查轉譯表；`_start(view.get_source_text(), export=None)`。**沒有**記下開著的文件。 |
| 匯出開始 | `convert_for_export` 137-145 | `_start(raw_text, export=...)`，不檢查是否在跑（註解寫明 defect 2）。 |
| 開始 | `_start` 147-153 | 設為忙碌、關閉對話框、`build_request`、`runner.start`、`self._active = _ActiveJob(job_id, export)`、新的 2 秒 timer（舊 timer 被覆蓋而沒有停止）。 |
| 手動完成 | `_complete_manual` 198-209 | `view.show_conversion_output(braille)`（設值並取得焦點）；**此刻的** `open_name = documents.open_document_name`；若有：存在就 `replace_document(Document(open_name, view.get_source_text(), braille))`、`set_dual_view_results(open_name, segments)`；`refresh_dual_view()`；「Conversion completed.」 |
| 匯出完成 | `_on_job_success` 176-185 | `job.export.on_success(output.display_text)`。segments 被丟掉（defect 3）。 |
| 執行中 | `is_running` 122-123 | `runner.is_running()`，也就是「worker 執行緒還活著」。worker 結束到投遞那一輪之間是 `False`（探測 6）。 |
| worker | `ConversionJobRunner._run_job`（`conversion/jobs.py` 68-83，tab） | 只有 `ConversionStageError` 以失敗投遞。其他例外跑出執行緒，什麼都不投遞（defect 6）。 |
| 忙碌 | `BrailleFrame.set_conversion_busy`（`gui.py` 1080-1088） | 停用「檔案」與「轉譯」選單、文件清單與原文編輯框。frame 的 char hook 與點字結果編輯框仍可用。 |
| 切換 | `on_char_hook` 980-1001、`_open_adjacent_document` 615-622 | 先存開著的文件（`save_open_document`：先更新記憶體，有變更才寫 package），再開另一份。 |
| 匯入 | `on_import_document` 892-920（Ctrl+O 經 char hook） | 先存檔；只匯入一個檔案時會開啟它。 |
| Ctrl+S | `on_output_text_key_down` 960-969 | 存檔，然後 `export_document(開著的文件, "brl")`；待轉換文件會啟動匯出轉換。 |
| 關閉 | `_close` 1040-1051、`_finish_close` 1066-1073 | `is_running()` 且事件可拒絕時拒絕（沒有訊息）。否則存檔、關閉轉換中對話框、銷毀雙視視窗。presenter 不會被告知（P1 審查 M-10）。 |
| 存檔 | `DocumentWorkspaceService.save_open_document`（`documents/workspace_service.py` 124-134） | **只存開著的文件**。其他文件只在新增、匯入、改名時寫入。 |
| 匯出 | `ExportCoordinator.export_document` 78-101、`_export_next` 138-183、`write_document` 71-76（`documents/export_coordinator.py`） | `write_document` 一律使用 `ExportContext(dual_view_results=documents.get_dual_view_results(name))`，也就是快取。 |
| 快取 | `DocumentController.dual_view_results_by_document` | 只在記憶體。`load_documents` 會清空它，所以重新啟動後每份文件的快取都是空的。 |

### 轉換進行中仍可操作的部分

「檔案」與「轉譯」選單、文件清單（含 F2、Delete 與快顯選單）以及原文編輯框都停用。以下仍可操作：

- Ctrl+Tab、Ctrl+Shift+Tab、Ctrl+PageDown、Ctrl+PageUp 切換文件。
- Ctrl+O 經匯入對話框匯入。只匯入一個檔案時會開啟它。
- 點字結果編輯框中的 Ctrl+S 存檔並匯出開著的文件。
- F6 移動焦點。
- 視窗的關閉鈕。

工作進行中**無法**改名、刪除或全部刪除：文件選單沒有加速鍵（`ui/menu_builder.py`），清單也停用。「全部匯出」各步驟之間沒有工作在跑，一切都可操作。

### 探測（皆在 `861d110`）

1. **defect 1 會寫進磁碟。** `alpha`（待轉換，開著）與 `beta`（`"B"`）。轉換 `alpha`，按 Ctrl+Tab，再讓工作完成。記憶體中 `alpha` 仍是待轉換，`beta` 的點字變成 `"AA"`（alpha 的結果）。快取記在 `beta` 名下。下一次存檔後，**`beta.dep` 存著 alpha 的點字**，`alpha.dep` 仍是待轉換。既有的釘選測試是 `test_ctrl_tab_during_manual_conversion_sends_result_to_new_document`（`KNOWN BUG`，defect 1）。
2. **defect 2，單一匯出。** `alpha`（待轉換，開著）與 `beta`（待轉換，選取中）。「檔案 > 匯出」`beta`，在第一個工作完成前對 `alpha` 按 Ctrl+S。啟動了兩個工作。只寫出 `alpha.brl`，出現一個「匯出完成」；**`beta.brl` 永遠沒寫出，也沒有任何訊息**。忙碌狀態結束。
3. **defect 2，全部匯出。** `open`（待轉換，開著）、`p1`、`p2`（待轉換）。「全部匯出」為 `open` 啟動工作 1；接著 Ctrl+S 啟動工作 2，工作 1 被丟掉。**匯出資料夾一直是空的，也沒有摘要。** 只有 Ctrl+S 的檔案寫出。既有的釘選測試是 `test_ctrl_s_during_manual_conversion_supersedes_it`、`test_convert_between_export_all_steps_is_superseded`（`test_gui_document_flows.py`）與 `test_superseded_job_delivers_nothing`（`test_conversion_presenter.py`）。
4. **defect 3。** 待轉換文件 `pend`（快取為空）匯出為 HTML：檔案是「No conversion data is available for this document.」頁面，沒有這次轉換的 segment。快取與記憶體都沒變。目前沒有釘選測試。
5. **defect 6。** converter 拋出 `RuntimeError`：例外跑出 `thread.run()`，什麼都沒投遞，忙碌狀態維持，`is_running()` 是 `False`，`_active` 仍有值。既有的釘選測試是 `test_exception_outside_conversion_stage_error_delivers_nothing`（`test_conversion_jobs.py`）。正式環境中 `convert_text_with_alignment` 會包住所有 `Exception`，所以今天只有 `BaseException` 會走到這條路。
6. **投遞空檔。** worker 結束後、它的 `CallAfter` 執行前，工作仍在 active，但 `is_running()` 是 `False`。在這個空檔關閉視窗不會被拒絕。
7. **已轉換文件在手動轉換中按 Ctrl+S。** 不會啟動第二個工作。匯出寫出的是**先前的**點字（`"old"`），之後手動轉換的結果才到。這不是轉換的競態，維持原樣（見「不在範圍內」）。

## 決定

**D1. 手動工作記住啟動它的文件，結果送到那裡（U1）。**

- `convert()` 在開始時記下 `target = documents.open_document_name` 與 `source_text = view.get_source_text()`，兩者都放進工作中。`get_source_text` 和今天一樣只呼叫一次。
- 成功時，完成流程依 target 分支。為了說明清楚，以下的 `open_name` 指完成當下的 `documents.open_document_name`。
  - **(a) target 開著**（`target == open_name`，切走再切回來也算）：今天的路徑，不變。顯示輸出並取得焦點。以 `Document(target, view.get_source_text(), braille)` 取代文件（編輯框顯示的就是 target，所以這是使用者看到的文字）。這裡不做文字檢查：忙碌時原文編輯框停用，切回來載入的是同樣的文字；而且檢查必須在顯示輸出前讀取編輯框，會改變今天的事件順序。設定 target 的快取、更新雙視、顯示「Conversion completed.」。不寫磁碟；和今天一樣由下一次存檔寫入。
  - **(b) target 沒開著**（`target` 有值，開著的是另一份文件）：開著文件的編輯框、焦點與雙視都不動，所以不呼叫 `show_conversion_output` 與 `refresh_dual_view`。接著：
    1. `document = documents.get_document(target)`；
    2. D3 的檢查；
    3. `documents.set_dual_view_results(target, output.dual_view_segments)`；
    4. `view.save_converted_document(Document(target, document.text, braille))`。文字取自記憶體，所以只有點字改變；使用者的文字絕不被改寫。
    5. 回傳 `True` 時：`view.show_info(<D2 訊息>, _("Info"))`。回傳 `False` 時：view 已經顯示過存檔錯誤，不再出第二個訊息框。
  - **(c) 開始時沒有文件**（`target is None`）：若完成時仍沒有開著的文件，走今天的路徑（顯示輸出、更新、「Conversion completed.」）。若現在有開著的文件，結果丟棄（D3）。
- **新增的寫入。** 新增 `DocumentWorkspaceService.save_document(document) -> Document | None`。它是今天 `save_open_document` 的主體，改為針對指定名稱的文件：
  - 名稱不在 controller 中就回傳 `None`；
  - `updated = _encodable(document)`：替換 lone surrogate，點字照原樣保留；
  - **先**更新記憶體；
  - `_is_saved(updated)` 時跳過寫入（F-5 D2）；
  - 否則 `save_document_package` 並 `_remember`。

  `save_open_document(text=, braille=)` 改為「`prepare_document_for_save(開著的文件, text=, braille=)`，再 `save_document`」，所以它的行為與 F-5 的測試都不變。

  `prepare_document_for_save` 的「待轉換維持 `None`」規則只屬於編輯框路徑。`save_document` 不可套用它，否則剛轉換完的待轉換文件的點字會被抹掉（測試計畫 D5）。
- **新增 `ConversionView.save_converted_document(document) -> bool`。** frame 的實作是 `try: self._workspace_service.save_document(document)`，`except Exception as exc: self._show_document_save_error(exc); return False`，最後 `return True`。非 `OSError` 寫 log，`OSError` 顯示訊息，和其他所有存檔完全一樣（F-3、F-5）。沒有新訊息。
- **為什麼立即寫入**（Decided by orchestrator with the recommended default; user may override before merge）。frame 只存開著的文件。沒開著的文件若只把結果放在記憶體，除非使用者關閉前又開過那份文件，否則離開程式時就會遺失。立即寫入是讓使用者的要求（「結果寫回那份文件」）在重新啟動後仍成立的唯一做法。這次寫入與每次存檔一樣是原子的 package 寫入。F-5 的指紋紀錄也會更新，所以之後開啟再切走不會重寫。存檔失敗時，記憶體中的副本保留結果；那份文件的下一次存檔（開啟它再切走）會重試寫入，就像 F-5 重試任何失敗的存檔。在別份文件開著時關閉程式不會重試：關閉只存開著的文件，所以結果會遺失，也沒有第二個訊息；原文是安全的（F-9 審查 M-5，「審查後的修正」第 2 點）。
- **與 F-5 的互動。**
  - 情況 (a)：不變。結果在記憶體中，下一次存檔寫入。
  - 情況 (b)：結果立即寫進磁碟，`_saved[target]` 與之相符。開啟 target 會把結果載入編輯框，切走時不會再寫一次。
  - (b) 存檔失敗時，`_saved[target]` 是舊的，所以下一次存檔會重試。
- **焦點。** (b) 不改變開著文件的編輯框與雙視。切換時原文編輯框是停用的，所以焦點留在它唯讀的點字結果編輯框（已實測）。訊息框（D2 訊息或存檔錯誤）關閉後，若主視窗是作用中視窗，焦點移到開著文件的原文編輯框（F-9 審查 M-6，「審查後的修正」第 1 點）。

否決的方案：

- 忙碌時阻擋 Ctrl+Tab／Ctrl+O（U1）。
- (b) 的結果只放記憶體：離開時遺失（見上）。
- 完成時重新開啟 target 文件：會把使用者從他選擇的文件拉走。

**D2. 情況 (b) 的一個新訊息。**

`_('Conversion completed. The result was saved to document "{name}".')`，標題 `_("Info")`，`wx.OK | wx.ICON_INFORMATION`（經 `view.show_info`）。zh_TW：「轉換完成。結果已儲存到文件「{name}」。」。引號沿用既有的 `Document "{name}" already exists.`（「文件「{name}」已存在。」），「儲存」沿用「Cannot Save Document」（「無法儲存文件」）。

Decided by orchestrator with the recommended default; user may override before merge（O1）。使用者決定了結果送到哪裡，但沒有決定要告訴使用者什麼。沿用「Conversion completed.」不需新字串，但使用者在另一份文件時，它沒說結果去了哪裡，這會是新的靜默意外；而且螢幕報讀器使用者聽不到任何輸出變化。若使用者偏好沿用舊訊息，只要改一行。

**D3. 寧可丟棄也不猜測。**

以下任一成立時，結果被丟棄，不顯示訊息框，並寫進 log（`dotexpress.gui`、`gui.log`、等級 WARNING、`"Discarded a conversion result: %s"`，附原因與 target 名稱）：

- (b) 且 `documents.get_document(target)` 是 `None`（改名、刪除、全部刪除）；
- (b) 且 `document.text != job.source_text`（文件現在是另一段文字）；
- (c) 且現在有開著的文件。

忙碌狀態照常結束（`_end_job` 在分支之前執行）。不寫快取、不改記憶體、不寫磁碟。

- 今天的 UI 走不到其中任何一種：工作進行中清單與「檔案」選單都停用，原文編輯框也是。切走時存的正是 `get_source_text()` 讀到的編輯框文字（測試計畫 E14）。這個檢查是為了未來的新入口，以及回答本任務關於改名／刪除的問題而設的安全網。
- 不追蹤改名。名稱是 app 唯一的文件識別（快取、package、清單）。要追蹤就得為一個走不到的情況在 presenter 加改名 hook（Decided by orchestrator with the recommended default; user may override before merge，O2）。
- 使用者要求「靜默丟棄或寫 log」：選擇寫 log，讓支援時查得到（O3）。

**D4. 匯出轉換在佇列中等待，而不是取代正在跑的工作（defect 2）。**

- presenter 保留一個 FIFO 的待執行工作佇列。每個工作帶著它的 request（在提交時建立）與它的完成方式：匯出 callback，或 D1 的手動 target。
- **提交**（`convert()` 通過檢查後，以及 `convert_for_export`）：若有工作 active、有完成流程正在進行，或佇列不是空的，就加入佇列；否則立即開始。在提交時建立 request，維持今天「以下指令當下的設定、轉譯表與語言為準」的規則。
- **完成**（`_on_job_success`、`_on_job_failure`）：取出 active 工作，設 `_completing = True`，然後：
  - `try`：今天的步驟（`_end_job`：停止 timer、關閉對話框、結束忙碌），再執行完成流程（D1、匯出 callback 或錯誤框）；
  - `finally`：`_completing = False`；若佇列不是空的且 presenter 未關閉，開始佇列最前面的工作。

  因此完成流程的 modal 訊息框（例如「Conversion completed.」）會在下一個工作開始前關閉。在訊息框開著時進來的要求（「全部匯出」某一步的 `CallAfter` 會在 modal 迴圈中執行）排在後面。不會有第二個訊息框疊在第一個上面，順序就是要求的順序。
- **手動「轉換」維持今天的行為**：有工作 active **或在佇列中**時，靜默返回（`is_running()`，D5）。它只能從原文編輯框與「轉譯」選單觸發，而兩者在忙碌時都停用。在「全部匯出」的空檔沒有工作 active，所以「轉換」會開始，而鏈的下一個待轉換步驟排在它後面（以前會把它丟掉）。
- 每個開始的工作都有自己的 timer 與轉換中對話框，和今天一樣。一次只跑一個工作，`_start`「覆蓋 timer 而不 Stop」的怪癖也就消失了。
- **沒有重疊時，每個事件的順序都和今天完全相同。** 所有沒有重疊的 characterization 測試都不需修改即通過，包括 `test_export_all_with_a_real_presenter_turn_by_turn`。

否決的方案：

- `show_info("A conversion is already running")`：需要一個新字串，而且「全部匯出」會因為一個無關的手動轉換把某份文件列為失敗。
- 取消正在跑的工作：它無法中止（worker 中是 liblouis），而且使用者兩個結果都要。

Decided by orchestrator with the recommended default; user may override before merge（O4）。

**D5. `is_running()` 的意思是「有工作 active 或在佇列中」。**

`ConversionPresenter.is_running()` 回傳 `self._active is not None or bool(self._queue)`，不再看執行緒狀態。影響：

- `_close` 在投遞空檔（探測 6）與有工作排隊時，也會拒絕可拒絕的關閉。和今天一樣，拒絕時沒有訊息。
- 它不涵蓋完成流程的訊息框（`_completing` 且佇列為空）。這時的關閉不會因這個檢查而被拒絕，和今天一樣，所以 F-7 在訊息框期間的關閉行為不變。
- `_show_converting_dialog` 仍使用 runner（`active_job_id`、執行緒是否活著）。

D7 讓這件事安全：每個開始的工作現在都恰好投遞一次。converter 卡住時，可拒絕的關閉仍會被拒絕，和今天看執行緒的檢查相同。

**D6. 待轉換文件匯出 HTML 時使用自己的轉換（defect 3，#11）。**

- `convert_for_export(raw_text, *, on_success: Callable[[ConversionOutput], None], on_error)`：匯出 callback 收到整個 `ConversionOutput`，而不是 `display_text`。`ExportConversions`（coordinator 的 protocol）同樣修改。
- `ExportCoordinator.write_document(destination_path, document, format_key, *, dual_view_results=None)`：`None` 表示使用快取，和今天一樣；tuple 則原樣使用。
- `export_document`（待轉換）與 `_export_next`（待轉換）建立 `Document(name, text, output.display_text)`，並傳入 `dual_view_results=output.dual_view_segments`。有點字的文件仍使用快取，不變。
- 匯出**不**把 segments 寫進快取，文件也仍是待轉換，和今天一樣。匯出結果從不改變文件；而為待轉換文件快取 segments，會讓雙視顯示點字結果編輯框沒有的資料（O5）。
- BRL 與 DEP 的 writer 不看 context，所以只有 HTML 改變。

**D7. 每個 worker 的結果都會投遞（defect 6）。**

在 `ConversionJobRunner._run_job` 中，`except ConversionStageError` 之後加上 `except BaseException as error`：

1. 以 `exc_info` 寫 log `"Unexpected error in a conversion job"`（logger `dotexpress.gui`、`gui.log`，比照 F-6 審查 M-6 與 F-7 D6，在呼叫時才綁定）；
2. 投遞 `ConversionJobFailure(job_id, ConversionStageError("translation", error))`；
3. 返回，不再拋出。

使用者看到既有的「Translation failed: {error}」訊息框，內容是 `get_public_error_message(error)`（空訊息時為「An unknown error occurred.」），忙碌狀態結束。攔截的是 `BaseException` 而不只 `Exception`：否則 worker 執行緒中的 `SystemExit` 也會讓 UI 一直忙碌，而 daemon 執行緒沒有地方可以把它交出去。

O6：Decided by orchestrator with the recommended default; user may override before merge。

**D8. 視窗關閉時通知 presenter（P1 審查 M-10、F-7 的關閉防護）。**

- 新增 `ConversionPresenter.shutdown()`。它停止並清除 timer、清除 active 工作與佇列，並設定 `_shut_down`。之後的投遞找不到 active 工作，一律忽略；timer callback 與佇列的取出都不做事。它不呼叫任何 view 方法。
- `BrailleFrame._finish_close` 在 `_close_finished = True` 之後、`close_converting_dialog()` 之前呼叫 `self._conversion_presenter.shutdown()`。
- **轉換進行中關閉**，搭配 F-7 的防護：
  - 可拒絕的關閉被拒絕（D5），沒有訊息，和今天一樣。
  - 不可拒絕的關閉（F-7 中不可拒絕的重入關閉，或任何強制關閉）依 F-5 D8 存開著的文件後關閉。F-7 實測 wx 3.2.9 在 `WM_ENDSESSION` 時不送 close 事件（行程直接結束，F-7 項目 60），所以這條路徑實務上很少見，D8 是低成本的安全網。此時正在跑的工作結果會被**丟棄**。對沒開著的 target（D1 b）而言，就是保留它先前的點字。使用者的文字是安全的，因為切走時已經存過。視窗消失後不會再寫檔，也不會對已銷毀的 frame 呼叫 view 方法。
- 對既有測試的影響：有工作在跑時的不可拒絕關閉，現在會在對話框的 `Unbind`／`Destroy` 之前記錄 `("timer.Stop", n)`。`test_close_while_running_vetoes_or_saves_and_closes` 隨之更新（它是關閉順序的 characterization 測試；plan 會說明）。

**D9. 字串與翻譯檔。**

- 一個 msgid（D2）。
- 依序執行 `scripts\generate-pot.bat`、`msgmerge`、補上 msgstr、`msgfmt --check --statistics`：0 fuzzy、0 未翻譯。
- `POT-Creation-Date` 維持 `2026-10-10 12:00+0800`（交接文件第 2 節）。
- 確認 `msgmerge` 沒有把新 msgid 以 fuzzy 配到「Conversion completed.」（交接文件第 2 節提醒過這類問題）；若有，移除 `#, fuzzy` 旗標與舊 msgid 註解行。

## 各路徑改前與改後的行為

| 路徑 | 改前 | 改後 |
| --- | --- | --- |
| 轉換 `alpha`，完成時 `alpha` 開著 | 設定輸出並取得焦點、更新記憶體、快取、雙視、「Conversion completed.」 | 相同 |
| 轉換 `alpha`，Ctrl+Tab 到 `beta`，完成 | `beta` 得到 alpha 的點字（編輯框、記憶體、快取）；下一次存檔寫進 `beta.dep` | `beta` 不動；`alpha` 的記憶體、快取與 `alpha.dep` 得到點字；D2 訊息；之後焦點在 `beta` 的原文編輯框（審查 M-6） |
| 同上，但完成前 Ctrl+Tab 回到 `alpha` | (a) | 相同 |
| 轉換 `alpha`，Ctrl+O 匯入一個檔案，完成 | 匯入的文件得到點字 | 同 Ctrl+Tab：`alpha` 得到；匯入的文件仍是待轉換 |
| 同上，但完成時 `alpha.dep` 無法寫入 | （無） | 「Failed to save document: {error}」錯誤框；`alpha` 在記憶體中保留結果；`alpha` 的下一次存檔重試，前提是關閉程式前再開啟 `alpha`（審查 M-5） |
| 轉換中對開著的待轉換文件按 Ctrl+S | 匯出取代手動工作；輸出永不顯示；一個「匯出完成」 | 「Conversion completed.」（輸出顯示），接著執行匯出，再「匯出完成」 |
| 「檔案 > 匯出」待轉換的 `beta`，再對待轉換的 `alpha` 按 Ctrl+S | 只有 `alpha.brl`，一個訊息框 | 先 `beta.brl` 再 `alpha.brl`，依序兩個訊息框 |
| 含待轉換文件的「全部匯出」中按 Ctrl+S | 鏈中斷、沒有摘要、資料夾是空的 | Ctrl+S 的匯出等輪到它；每份文件都寫出；摘要出現 |
| 在「全部匯出」空檔中轉換 | 下一個待轉換步驟取代它；手動輸出永不顯示 | 手動先完成（「Conversion completed.」），鏈接著繼續並以摘要結束 |
| 匯出待轉換文件為 HTML | 「No conversion data」頁面 | 這次新的雙視；快取不變；文件仍待轉換 |
| 匯出已轉換文件為 HTML | 快取 | 相同 |
| worker 拋出非 stage 錯誤 | 永遠忙碌、沒有訊息 | 「Translation failed: {error}」、結束忙碌、寫 log |
| 轉換中關閉（可拒絕） | 拒絕 | 相同；投遞空檔與排隊時也拒絕 |
| 轉換中關閉（不可拒絕） | 存檔、關閉；晚到的投遞會呼叫已銷毀的 frame | 存檔、關閉；presenter 已關閉；晚到的結果忽略 |

## 各檔案的設計

### `client/ui/conversion_presenter.py`（4 個空白）

- `_ManualTarget(document_name: str | None, source_text: str)`（私有、frozen）。
- `_Job(request, export: _ExportCallbacks | None, manual: _ManualTarget | None)` 承擔佇列中工作的角色；`_ActiveJob(job_id, job)` 表示正在跑的那一個（plan 可以合併兩者）。
- `self._queue: collections.deque[_Job]`、`self._completing = False`、`self._shut_down = False`。
- `is_running()`（D5）、經 `_submit` 的 `convert()` 與 `convert_for_export()`（D4）、`_start_next()`、帶 `try`／`finally` 取出佇列的 `_on_job_success`／`_on_job_failure`、含 (a)(b)(c) 分支與 D3 的 `_complete_manual(job, output)`、`shutdown()`（D8）。
- `ConversionView` 新增 `save_converted_document(document: Document) -> bool`，以及 `focus_source_editor()`（審查 M-6）。
- 匯出成功 callback 收到 `ConversionOutput`（D6）。
- 模組仍不 import `wx` 或 `gui`（`test_module_imports_neither_wx_nor_gui`）。
- D3 的 logger 在呼叫時才綁定。

### `client/conversion/jobs.py`（tab）

`_run_job`：D7。其他不變：job id、過期結果的過濾、`daemon=True`、callback 前設 `_thread = None`。

### `client/documents/workspace_service.py`（4 個空白）

`save_document`（D1）；`save_open_document` 委派給它。模組 docstring 中「Save writes only when...」那句改為同時提到兩者。

### `client/documents/export_coordinator.py`（4 個空白）

`ExportConversions.convert_for_export` 的簽名、`write_document(..., dual_view_results=None)`、兩條待轉換路徑（D6）。

### `client/gui.py`（tab）

- 在 `ConversionView` 區塊加上 `save_converted_document`，以及 `focus_source_editor`（審查 M-6）。
- `_finish_close` 呼叫 `shutdown()`（D8）。
- 其他不變。`_close` 的檢查仍是 `self._conversion_presenter.is_running()`；它的意義在 presenter 中擴大。

### 翻譯檔

`client/locales/dotexpress.pot`、`client/locales/zh_TW/LC_MESSAGES/dotexpress.po` 與 `.mo`（D9）。

### 不修改

- `set_conversion_busy`、`on_char_hook`、`_open_adjacent_document`、`on_import_document`、`on_output_text_key_down`；
- `DocumentController`；
- `documents/formats.py` 中的 writer；
- `client/braille/` 以及交接文件第 2 節清單中的每個檔案。

## 維持不變的部分

- 工作沒有重疊時，每個手動轉換、單一匯出、全部匯出與失敗路徑的逐輪事件紀錄。
- 除了 D2 訊息與 D7 路徑（在今天什麼都不出現的地方顯示既有訊息）之外，每個訊息、標題與圖示。
- 情況 (a)，包括「下一次存檔前不寫磁碟」。
- 每個工作的忙碌切換；2 秒的轉換中對話框；忙碌時手動「轉換」靜默返回。
- 匯出從不改變文件或快取。
- F-5 的指紋語意，以及 F-7 的關閉與重入處理（D5、D8 除外）。

## 使用者可見字串

| msgid | zh_TW msgstr | 位置 |
| --- | --- | --- |
| `Conversion completed. The result was saved to document "{name}".` | 轉換完成。結果已儲存到文件「{name}」。 | D1 (b)，標題 `Info` |

新近可能出現的既有訊息：

- 非預期的 worker 錯誤時的「Translation failed: {error}」（D7）；
- D1 (b) 寫入失敗時的「Failed to save document: {error}」。

## 測試計畫

TDD：每一步的測試先寫，並因所述原因失敗，再由程式碼轉綠。縮排依各檔案：`test_conversion_jobs.py` 用 tab，此處提到的其他測試檔用 4 個空白。測試只使用暫存資料夾。每個會讓程式寫 log 的測試都使用 `assertLogs`（或隔離 `dotexpress.gui`），所以不會寫進 `client/log/`。

### A. runner（`client/tests/test_conversion_jobs.py`）

1. **翻轉** `test_exception_outside_conversion_stage_error_delivers_nothing` 為 `test_unexpected_worker_error_is_delivered_as_a_translation_failure`：`RuntimeError("unexpected")` 投遞一個失敗，stage 為 `translation`，`error` 是同一個物件；`thread.run()` 不拋出；`is_running()` 為 `False`；一筆帶 `exc_info` 的 log。紅燈原因：例外跑出來。
2. `test_base_exception_in_the_worker_is_delivered_too`：`SystemExit("x")`，期望相同。紅燈。

### B. presenter（`client/tests/test_conversion_presenter.py`）

紀錄用的 view 新增 `save_converted_document`，記錄 `("save_converted_document", document)` 並回傳可設定的結果。一個小 helper 以 frame 的方式「切換」文件：先把開著文件的文字換成 view 的原文，再呼叫 `documents.open_document(other)`。

1. `test_result_goes_to_the_document_that_started_the_conversion`：在 `alpha` 開始、切到 `beta`、投遞。`_end` 之後的事件：`("save_converted_document", Document("alpha", "source", braille))`，再 `show_info(含 alpha 的 D2 訊息, Info)`。沒有 `show_conversion_output`、`get_source_text`、`refresh_dual_view`。快取 `{"alpha": segments}`；`beta` 不變。紅燈：今天 `beta` 得到結果。
2. `test_result_for_the_open_document_follows_todays_path`：切走再切回；事件清單等於今天的手動完成。改前改後都綠（防護用）。
3. `test_failed_save_of_the_originating_document_shows_no_completion_message`：view 回傳 `False`；沒有 `show_info`；`alpha` 的快取保留；之後排隊的工作仍會開始。（記憶體的部分是 service 的責任，見 D1 與 E4。）
4. `test_result_for_a_document_that_is_gone_is_discarded_and_logged`（subTest：刪除、改名、全部刪除）：`_end` 之後沒有任何 view 呼叫、沒有快取、一筆 WARNING。紅燈。
5. `test_result_for_a_changed_text_is_discarded_and_logged`：(b) 且記憶體中是另一段文字。紅燈。
6. `test_result_without_a_starting_document`：(c)，完成時仍沒有開著的文件時走今天只顯示輸出的路徑；有開著的文件時丟棄並寫 log。後者紅燈。
7. **翻轉** `test_superseded_job_delivers_nothing` 為 `test_export_requested_while_a_conversion_runs_waits_for_it`：第一個完成前只有一個執行緒；`build_request` 在提交時就已記錄；匯出在手動完成的 `show_info` 之後開始；兩個完成依序到達；第一個 timer 有被停止。紅燈。
8. `test_queued_jobs_run_in_request_order`：一個在跑時提交三個匯出；FIFO。
9. `test_queue_drains_after_a_failed_completion`：第一個工作失敗（錯誤框），排隊的在它之後開始。
10. `test_request_during_a_completion_waits_until_it_returns`：`on_success` callback 自己呼叫 `convert_for_export`（代表在 modal 訊息框中執行的 `CallAfter`），它會排隊；callback 返回前沒有第二次 `busy True`。紅燈。
11. `test_queue_drains_when_a_completion_raises`：`on_success` 拋出 `RuntimeError`；例外往外傳，而下一個工作已經開始（`finally`）。
12. `test_convert_returns_while_a_job_is_queued_or_in_the_delivery_gap`：沒有新執行緒、沒有事件。
13. `test_is_running_covers_the_delivery_gap_and_the_queue`：worker 結束後、投遞前為 `True`；排隊時為 `True`；完成流程中且佇列為空時為 `False`；之後為 `False`。空檔的部分紅燈。
14. `test_shutdown_drops_the_running_and_queued_jobs`：`timer.Stop`；之後的投遞沒有事件；timer callback 沒有事件；`is_running()` 為 `False`；排隊的工作不會開始。紅燈：沒有 `shutdown`。
15. `test_export_success_receives_the_conversion_output`：`on_success` 收到帶 segments 的 `ConversionOutput`。紅燈。

既有 presenter 測試中接收 `braille` 的匯出 callback，改為接收 `output` 並記錄 `output.display_text`。它們的事件清單不變。

### C. coordinator（`client/tests/test_export_coordinator.py`）

1. `test_html_export_of_a_pending_document_uses_its_conversion`：真的 HTML writer；檔案含這次新 segment 的原文；快取不變；文件仍待轉換。紅燈：「No conversion data」頁面。
2. `test_export_all_html_uses_each_pending_documents_conversion`：兩份待轉換、一份已轉換且有快取；每個檔案顯示各自的資料。紅燈。
3. `test_write_document_without_results_uses_the_cache`：既有的 `write_document` 測試不變，再加上明確傳入 `dual_view_results=()` 時，即使有快取也寫出「No conversion data」。
4. `test_export_all_with_a_real_presenter_turn_by_turn` 維持原樣（事件相同；fake converter 不變）。

本模組的 fake `ExportConversions` 改為傳 `ConversionOutput` 給 `on_success`。

### D. service（`client/tests/test_workspace_service.py`）

1. `test_save_document_writes_a_document_that_is_not_open`：package 含新點字；記憶體已更新；之後 `_is_saved` 為真。
2. `test_save_document_skips_an_unchanged_document`：不寫入（mtime 與位元組不變），比照 F-5 開著文件的測試。
3. `test_save_document_failure_keeps_memory_and_the_package`（比照 F-3／F-5 的測試，注入 `os.replace` 失敗或唯讀 package）：拋出；記憶體有新點字；package 位元組不變；之後的 `save_document` 重試並寫入。
4. `test_save_document_of_an_unknown_name_returns_none`：不寫入。
5. `test_converted_braille_of_a_pending_document_is_saved`：待轉換文件經 `save_document` 取得點字（不被待轉換規則抹掉）。
6. 既有的 `save_open_document` 測試不修改，維持綠燈。

### E. frame 與 characterization（`client/tests/test_gui_document_flows.py`，`ConversionExportFlowsCharacterizationTest`）

1. **翻轉** `test_ctrl_tab_during_manual_conversion_sends_result_to_new_document` 為 `test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document`：
   - 投遞後：`timer.Stop`、結束忙碌、D2 訊息框，沒有其他事件（沒有 `set output`、沒有焦點、沒有 `dual_view.refresh`）；審查修正後，訊息框之後接著原文編輯框的焦點（「審查後的修正」第 1 點）；
   - 記憶體：`alpha` 有點字，`beta` 不變；
   - 快取：`{"alpha": (segment,)}`；
   - `alpha.dep` 存著點字；`beta.dep` 沒有被寫；
   - Ctrl+Tab 回到 `alpha` 後，輸出編輯框顯示點字。
   紅燈。
2. `test_ctrl_tab_away_and_back_during_conversion_keeps_todays_completion`。
3. `test_import_during_manual_conversion_does_not_receive_the_result`：以 fake 匯入檔案對話框（`GetPaths`、`SetFilterIndex`、`GetFilterIndex`）驅動 `on_import_document`。plan 加入這個 fake；若太繁重，改為以 service 匯入後呼叫 `_open_document_by_name`。匯入的文件仍待轉換；`alpha` 得到結果。紅燈。
4. `test_failed_save_of_the_starting_document_reports_the_save_error`：切換後讓 `alpha.dep` 無法寫入（F-3／F-5 的注入方式）；「Failed to save document: {error}」錯誤框；沒有完成訊息框；記憶體中的 `alpha` 有點字。
5. **翻轉** `test_ctrl_s_during_manual_conversion_supersedes_it` 為 `..._queues_the_export`：輸出顯示並出現「Conversion completed.」訊息框，接著第二個工作開始，然後寫出 `alpha.brl` 並出現「匯出完成」。紅燈。
6. `test_ctrl_s_during_export_all_waits_and_the_summary_appears`（把探測 3 寫成測試）。紅燈。
7. `test_ctrl_s_during_single_export_writes_both_files`（把探測 2 寫成測試）。紅燈。
8. **翻轉** `test_convert_between_export_all_steps_is_superseded` 為 `..._completes_before_the_next_step`。紅燈。
9. `test_pending_html_export_through_the_frame_shows_the_conversion`。紅燈。
10. `test_close_in_the_delivery_gap_is_vetoed`。紅燈。
11. `test_close_that_cannot_be_vetoed_shuts_the_presenter_down`：工作在跑；不可拒絕的關閉；之後 worker 結束、它的投遞執行：沒有任何事件、沒有寫入、target 的 package 不變。紅燈。
12. `test_close_while_running_vetoes_or_saves_and_closes` 加上 `("timer.Stop", 1)`（D8）。
13. `test_save_converted_document_reports_failures_like_every_save`（frame 方法）：`OSError` 顯示訊息框、不寫 log；`ValueError` 顯示訊息框並寫 log。比照 F-7 patch `gui.message_box`。
14. **D3 的不變式：** `test_switch_away_stores_exactly_the_converted_text`。原文編輯框中是 `A` U+D83D `B`（以腳本寫入、以位元組檢查；交接文件第 2 節）；轉換、Ctrl+Tab、投遞。結果被儲存，而不是被丟棄。

`FrameConversionDelegationTest`：presenter 仍以相同引數建立。

### 數量

約 40 個新測試與 5 個翻轉（A 2；B 15；C 3；D 5；E 14）。在 Windows 上：`Ran` ＝ F-8 之後的基準＋新測試，`FAILED (errors=1, skipped=7)`，只有 F-W6。確切數字由 plan 決定；紅燈／綠燈的意圖具有約束力。

## 移轉步驟（每一步一個綠燈 commit，先紅燈）

1. `fix: deliver every conversion worker error as a failure (F-9)`：D7；測試 A。
2. `fix: export pending documents as HTML with their own conversion (F-9)`：D6；測試 B15、C、E9。這一步改變匯出 callback。
3. `fix: queue conversions instead of dropping the running one (F-9)`：D4、D5；測試 B7-B13、E5-E8、E10。
4. `fix: write a conversion result to the document that started it (F-9)`：D1-D3、D9；`save_document`、`save_converted_document`、翻譯檔；測試 B1-B6、D、E1-E4、E13、E14。
5. `fix: ignore conversion results after the window closes (F-9)`：D8；測試 B14、E11、E12。

每個 commit 結尾是 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`，且只 stage 明確的路徑。只有第 4 步會動到 `client/locales/`。

## 驗收條件

在 Windows 上從 `client/` 以 `$PY` 執行，runtime 依 F-3 plan Task 0 複製。

1. 完整測試：除 F-W6 外沒有 failure 或 error；`Ran` 如 plan 所述。
2. 聚焦測試：`$PY -m unittest tests.test_conversion_jobs tests.test_conversion_presenter tests.test_export_coordinator tests.test_workspace_service tests.test_gui_document_flows -v` 通過；`tests.test_gui_document_flows tests.test_conversion_presenter tests.test_export_coordinator` 兩種順序都通過。
3. `grep -rn "KNOWN BUG (P1-4 spec, defect [1236])" client/tests` 沒有輸出。
4. 翻譯檔：
   - 新增一個 msgid，msgstr 如上表；
   - `msgfmt --check --statistics`：全部已翻譯、0 fuzzy、0 未翻譯；
   - AST msgid 掃描等於翻譯檔數量（F-8 之後的數量＋1）；
   - `POT-Creation-Date` 不變。
5. 兩個 fixture 的 sha256 不變（`translation_golden.json` `e67d95a1...`、`dictionary_entries_trace.json` `f493da52...`）。
6. app 資料不受影響：
   - 主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 前後 sha256 相同；
   - worktree 中沒有產生 `client/log/`、`client/workspace/` 或 `client/config.json`。
7. `git diff main --stat` 只動到「各檔案的設計」中的檔案、上述測試檔，以及 spec、plan 與 history 檔案。
8. mutation 檢查（plan）。每個 mutant 至少被一個測試抓到：
   - (b) 使用完成當下的 `open_document_name` 而非工作的 target；
   - (b) 只寫記憶體（不呼叫 `save_converted_document`）；
   - (a) 也寫磁碟；
   - (b) 呼叫 `show_conversion_output` 或 `refresh_dual_view`；
   - (b) 存入編輯框文字而非記憶體中的文字；
   - 移除 (b) 的文字檢查；
   - `save_document` 套用待轉換規則（抹掉新點字）；
   - `_submit` 在有工作 active 時仍立即開始（今天的取代行為）；
   - 以 LIFO 取代 FIFO；
   - 取出佇列不在 `finally` 中；
   - 從不設定 `_completing`；
   - `is_running()` 改回看執行緒狀態；
   - `shutdown()` 不清除佇列；另一個 mutant：`_finish_close` 不呼叫它；
   - coordinator 忽略 `output.dual_view_segments`；
   - coordinator 把它們寫進快取；
   - runner 只攔截 `Exception`；
   - runner 不寫 log。
9. 下方的 packaged GUI 驗證，結果放在實作的 history 資料夾。

## Windows 驗證（packaged build）

build 與行程的規則同 F-7：

- 主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面，再執行 `scripts\build-dotexpress.bat`；
- 在 `PYZ-00.toc` 中確認 `ui\conversion_presenter.py`、`conversion\jobs.py`、`documents\workspace_service.py`、`documents\export_coordinator.py` 與 `gui.py` 來自被驗證的 checkout；
- exe 複製到 `D:\dxtest\N-f9\`；
- 「改前」是 F-8 之後 `main` 的 build；
- 每個項目在新的 `D:\dxtest\auto<項目>-f9` 資料夾執行；
- 只結束這些資料夾底下的行程。

腳本放在實作 history 資料夾的 `auto/`。它們不修改地重用 `docs/superpowers/history/2026-10-09-03-windows-verification/auto/`（`dx.py`、`docs.py`、`lock.py`）與 `.../2026-10-10-01-f5-save-failure-handling/auto/f5gui.py`。訊息框是 task dialog，經 UIA 讀取（`f5gui.describe`）。

**緩慢的轉換。** 這些項目需要執行數秒的轉換。plan 校準一段原文（例如由腳本貼上數十萬字的中英混合文字），讓「轉換中」對話框出現。按鍵在最初 2 秒內、該對話框搶到前景之前送出，或在重新聚焦主視窗之後送出；plan 選定並記錄做法。若某個長度在 build 上太快，就加長文字，絕不在 app 內加 sleep。

項目 `9a`-`9i` 是佔位編號；最終編號在 plan 階段排在 F-8 的項目之後決定（F-7 結束於 65，F-8 從 66 開始）。

| # | 步驟 | F-9 之後的預期 | 改前 |
| --- | --- | --- | --- |
| 9a | 文件 `alpha`（長文、待轉換）與 `beta`（短文、已轉換、點字 `B`）。開啟 `alpha`，Ctrl+Enter，立即 Ctrl+Tab。等待完成。 | 出現點名 `alpha` 的 D2 訊息框，按鈕為翻譯後的「確定」；`beta` 的點字編輯框不變；Ctrl+Tab 回去：`alpha` 顯示點字；重新啟動後 `alpha.dep` 有點字、`beta.dep` 不變 | **`beta` 顯示 alpha 的點字，切換後 `beta.dep` 存著它** |
| 9b | 同 9a，但完成前按兩次 Ctrl+Tab（回到 `alpha`） | 「Conversion completed.」；`alpha` 的輸出顯示點字 | 相同 |
| 9c | 同 9a，但不按 Ctrl+Tab，改按 Ctrl+O 匯入一個 `.txt` | 匯入的文件開啟且仍待轉換；D2 訊息框點名 `alpha` | 匯入的文件得到 alpha 的點字 |
| 9d | 同 9a；Ctrl+Tab 後以 `lock.py` 鎖住 `alpha.dep`（共用模式 `r`）直到完成 | 「Failed to save document: ...」錯誤框，沒有完成訊息框；解鎖；開啟 `alpha`：顯示點字；切走；重新啟動：`alpha.dep` 有點字 | （同 9a 的「改前」） |
| 9e | 開著 `alpha`（長文、待轉換）。Ctrl+Enter，F6 到點字結果編輯框，Ctrl+S，選擇路徑 | 先「Conversion completed.」，接著執行匯出，再「匯出完成」；檔案內容是點字 | **只有一個「匯出完成」；輸出永遠不顯示轉換結果** |
| 9f | 三份長的待轉換文件（開著的是其中一份）。「檔案 > 全部匯出 > BRL」到空資料夾；第一個轉換進行中，F6 到點字結果編輯框，Ctrl+S 匯出到第二個資料夾 | Ctrl+S 的檔案與三個檔案都寫出；最後出現一次摘要 | **沒有摘要；全部匯出的資料夾是空的** |
| 9g | 匯入一個 `.txt`（待轉換）。「檔案 > 匯出 > 雙視 HTML」；也以 HTML「全部匯出」 | 每個檔案都顯示轉換後的 segments | 「No conversion data」頁面 |
| 9h | 長轉換進行中送出 `WM_CLOSE`；等待完成；再送一次 `WM_CLOSE` | 第一次關閉被拒絕（視窗仍在、沒有訊息框）；完成後 app 正常關閉 | 相同（測試工具檢查） |
| 9i | 在 9a 那種已切走的長轉換進行中：`SendMessageTimeoutW(main, WM_QUERYENDSESSION, 0, ENDSESSION_LOGOFF, ...)`；讓它完成；再開始另一個長轉換並送 `WM_ENDSESSION`（`wParam` 1、`ENDSESSION_LOGOFF`） | 查詢立即回傳 0（拒絕）；app 繼續執行，第一個轉換以 D2 訊息框完成；`WM_ENDSESSION` 後行程在 5 秒內以代碼 0 結束；沒有留下 `.tmp`；`log\gui.log` 沒有新的 traceback | 相同（以測試工具檢查 D5／D8 與 F-7 登出處理的配合） |

絕不觸發真正的登出或關機；訊息只送給測試實例的主視窗。需要 NVDA 的項目維持手動。

**使用者手動項目**（編號於 plan 階段決定）：以 NVDA 聽 9a 的 D2 訊息框，確認有唸出文件名稱，且按「確定」後焦點在 `beta` 的原文編輯框（審查修正後；在 `N-f9b` 上已實測，「審查後的修正」第 1 點）。9e 的兩個訊息框依序被唸出。

## 風險

- **在開著的文件之外新增一次磁碟寫入**（低）。與每次存檔相同的原子 package 寫入與指紋紀錄（F-3、F-5）。失敗時顯示一般的存檔錯誤，結果保留在記憶體。只有那份文件之後的存檔會寫入它；若從別份文件關閉程式，結果遺失，只留下原文（審查 M-5）。
- **佇列讓忙碌時間變長**（低，刻意的）。長轉換中按 Ctrl+S 現在會等它，而不是取代它；期間顯示轉換中對話框。
- **卡住的 converter 會擋住佇列**（低）。和今天永遠不結束的忙碌狀態相同。D7 排除了「沒有投遞」的情況。
- **文字不符時丟棄**（低）。若日後的改動讓切走時存的文字和 `get_source_text()` 不同，結果會被丟棄並寫 log。E14 釘住這個不變式；log 會指出情況。
- **F-8 的 rebase**（中，機械性的）。`workspace_service.py`，可能還有 `gui.py`，兩邊都會修改。一切以函式命名，plan 在 F-8 之後的 `main` 上 rebase。
- **presenter 與 runner 寫 log**（低）。測試必須使用 `assertLogs`，否則測試會寫出 `client/log/gui.log`（驗收 6）。
- **測試異動**（低）。每個 fake `ExportConversions` 的匯出 callback 型別都要改；關閉順序的測試多一個 `timer.Stop`。
- **轉換進行中程序被結束**（低，既有的；F-9 規劃後新增，見「規劃後的修正（F-9）」第 11 點）。轉換進行中 Windows 結束工作階段時，程序可能以 heap 損毀的結束碼結束，而不是 0（五次中出現一次）。那一刻不會寫入任何資料：開著的文件之前已存檔，轉換結果則和程序因其他原因結束時一樣遺失。懷疑的原因（審查 M-8，假設）：若 wx 結束主迴圈，`BrailleApp.OnExit` 會呼叫 `runtime.close()`，在 worker 還在 liblouis 裡時就釋放 liblouis。延到 F-12。

## 待決問題

沒有會擋住進度的問題。U1 是使用者的決定（2026-10-10）。

Decided by orchestrator with the recommended default; user may override before merge：

- **O1.** 情況 (b) 顯示點名文件的新 D2 訊息。替代方案是沿用「Conversion completed.」（不需新字串）。
- **O2.** 文件以名稱識別；轉換中改名（今天走不到）時丟棄結果，不追蹤改名（D3）。
- **O3.** 丟棄的結果以 WARNING 寫 log；不顯示訊息框（D3）。
- **O4.** defect 2 以 FIFO 佇列修正，而不是顯示「忙碌中」訊息（D4）。
- **O5.** 匯出轉換仍不更新快取或文件（D6）。
- **O6.** runner 攔截 `BaseException`、寫 log 並投遞「translation」失敗（D7）。
- **O7.** 情況 (b) 立即寫入 `alpha.dep`，而不是只把結果放在記憶體（D1）。
- **O8.** `is_running()` 涵蓋投遞空檔與佇列，所以這時可拒絕的關閉也會被拒絕；只有完成訊息框時不拒絕（D5）。
- **O9.** 關閉時的 `shutdown()` 丟棄正在跑與排隊中的結果（D8）。

F-9 的 plan 新增（「規劃後的修正（F-9）」第 4、5 點）。Decided by orchestrator with the recommended default; user may override before merge：

- **O10.** `shutdown()` 之後不再開始新的工作，所以關閉之後才執行的、待轉換文件的「全部匯出」步驟什麼都不做（D8）。已有點字的文件不需要轉換，它的步驟和 F-9 之前一樣仍會寫出檔案；今天不會發生（審查 M-7，「審查後的修正」第 3 點）。
- **O11.** 丟棄的結果（O3）以 `gui.log` 會記錄的 `ERROR` 層級寫 log，而不是 `WARNING`（D3）。

## 不在範圍內／後續項目

- **重新啟動後匯出已轉換文件為 HTML** 會是「No conversion data」：雙視快取只在記憶體（`load_documents` 會清空）。修正需要在匯出時轉換，或保存雙視資料。後續項目。
- **已轉換文件在手動轉換中按 Ctrl+S** 匯出的是先前的點字（探測 7）。不變。
- **轉換中關閉被拒絕時沒有任何回饋。** 不變（需要新字串）。
- 「全部匯出」摘要的本地化（P1-4 defect 4，F-12）；以標題 `FindMenu`（defect 5）。
- 起始文件已不是開著的文件時，手動轉換失敗的訊息不說出文件名稱（審查 M-9；需要新字串；F-12）。
- 關閉時也存下 (b) 存檔失敗且沒開著的文件（審查 M-5；F-5 的範圍；F-12）。
- worker 執行中時，`OnExit` 不釋放 liblouis（審查 M-8；F-12）。
- 全部刪除失敗後的狀態（P1-3 defect 4）。
- 把匯出轉換的結果存進文件（待轉換文件匯出後仍是待轉換）。
