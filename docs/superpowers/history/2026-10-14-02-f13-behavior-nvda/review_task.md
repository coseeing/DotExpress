# F-13 行為與 NVDA review 紀錄

- 日期：2026-10-14。依 orchestrator 要求以繁體中文撰寫；格式沿用 F-12 的 `review_task.md`。
- 範圍：worktree `D:/workspace/DotExpress-f13`，branch `fix/f13-behavior-nvda`，範圍 `a147fed..HEAD`（HEAD `fbca556`；7 個 commit：spec `1d07c04`、plan `27efb2b`、四個修正 `0fa4e3f` `206fc11` `266d89a` `a1e699d`、GUI 紀錄 `fbca556`）。`main` 之後的 `2053646`（`about.py` 版本號）與本次無關，未納入。production diff：`client/gui.py`（+43/-3）、`client/ui/conversion_presenter.py`（+24/-4）、`client/dialog.py`（+3/-1），加上兩個文字 catalog；測試三個檔案；history 資料夾（probe、auto 腳本、`auto-results.md`）。
- 對照讀過：spec（英文與 zh-TW，含「規劃後的修正」1–9）、plan（Global Constraints、Spec Corrections、Review Focus、Task 5 的 17 個 mutant、Implementation Notes 1–6）、`auto-results.md`、probe `README.md` 與三個 jsonl、`task.md` 第五節「下一輪要修」（唯讀）、HANDOFF `2026-10-14-01` 第 1–6 節、`AGENTS.md`。
- 方法：三個 production 檔案的 diff 逐行對照周邊程式（`_on_close`/`_close`/`_finish_close`、`_load_workspace_documents_at_startup`、`_open_document_by_name`、`set_conversion_busy`、`focus_source_editor`、`on_frame_activate`、`conversion/jobs.py`、`conversion/contracts.py`、`mathcat_adapter.close`、`client_init.start_client_init_background`）；wx 3.2 主迴圈對 `CallAfter`（pending event）與 Windows 訊息的處理順序；測試 diff 與其 fake（`_FakeEditor`、`DeferredCalls`、`FakeThread`、wx stub）；catalog 與 fixture 的位元組檢查；在 scratchpad 副本上跑 8 個自選 mutant；聚焦測試模組（不跑完整測試、不 build、不跑 GUI，依記憶體規則）；讀取 `D:/dxtest/auto*-f13.log` 核對 `auto-results.md` 的數字。
- 本紀錄只寫到磁碟，不 commit。沒有修改 repo 的其他檔案；沒有啟動 GUI；沒有碰剪貼簿；沒有碰 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/`、`client2/`、`preprocessing/`、`testdata/`、`task.md`。

## 驗證（Windows 11 26200，`$PY` = `D:/workspace/DotExpress/client/.venv/Scripts/python.exe`，`$SP` = session scratchpad 的 `f13review/`）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| 聚焦測試（spec 驗收條件 2 再加 `test_conversion_jobs`） | 在 worktree `client/`：`$PY -B -X utf8 -m unittest tests.<module>`，一次一個模組，每次前先以 PowerShell `(Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue` 確認 ≥ 600（實際 625–677） | `test_conversion_presenter` 48、`test_dictionary_entries_dialog` 99、`test_message_box` 8、`test_wx_call_sites` 8、`test_i18n` 36、`test_conversion_jobs` 10、`test_gui_document_flows` 233：全部 `OK`（共 442） |
| 完整測試 | 未跑（記憶體規則：另一個 agent 同時在跑重的工作） | 採信 plan Implementation Notes 1 的 `Ran 1646`、`OK (skipped=6)`；四個 commit 的 `HEAD:client` tree id 與 plan 的 Expected Counts 一致（`a1e699d` → `6c352f02…`） |
| catalog | `grep -c '^msgid ' .po`；`git diff a147fed..HEAD -- client/locales/` 過濾掉 `#:` 行；`sha256sum` 比對 `.mo` 與 `git show a147fed:…dotexpress.mo` | 408 行 `msgid`（含標頭）= 407 個 msgid；`.pot`/`.po` 除 `#:` 行外只有一個 msgstr 的折行（「無法寫入檔案。…」，文字相同，plan Spec Corrections 2 已說明）；`POT-Creation-Date` 不變；`.mo` sha256 `dcf50a62…f29e32`，與 `a147fed` 位元組相同 |
| fixture | `git rev-parse HEAD:<path>` 與 `a147fed:<path>` 比對；`git show HEAD:<path> \| sha256sum` | 三個 fixture 的 blob 都相同：`translation_golden.json` `e67d95a1…`、`dictionary_entries_trace.json` `f493da52…`、`translation_liblouis_golden.json` `8dc8572e…`（與 HANDOFF 第 5 節一致；工作樹檔案因 autocrlf 為 CRLF，所以直接 `sha256sum` 工作樹檔案會不同，這是正常的） |
| 禁改檔案 | `git diff a147fed..HEAD --stat -- client/braille/ scripts/ vendor/` | 無輸出；`client/ui/message_box.py` 未改（D5）；`git diff --stat` 只有 spec 驗收條件 6 列出的檔案 |
| commit 規則 | `git log a147fed..HEAD --format=%B \| grep -ic co-authored` | 0（HANDOFF 第 5 節）；主旨都以 `(F-13)` 結尾 |
| 剪貼簿／其他程式名稱 | `grep -rniE "clipboard\|SetClipboardData\|pyperclip"` 於 history 資料夾與三個測試檔；逐讀 `f13gui.py`、`safe_run.py`、`run_item.sh`、`item127.py`、`startup.py`、`item121.py`、`item128.py`、`item129.py`、`manual131.py`、`drive_probe.py` | 只有「不碰剪貼簿」的說明文字；按鍵一律經 `safe_run.py` 的前景檢查；`windows_of` 只列受測程序的視窗，`focus()` 只對應受測程式 UI 執行緒的焦點，`uia_focus`/`describe`/`f11gui.focused` 在前景不是受測程式時記 `<another program>`；`drive_probe.py` 只在 owner 屬於 probe 程序時印視窗名稱、只 kill 自己啟動的 pid |
| 結束程序的範圍 | `run_item.sh` 結尾兩段 PowerShell | 只 `Stop-Process` 可執行檔在該項目資料夾下、或命令列含 `lockshare.py` 加該項目資料夾名稱的程序；另外刪除 `%TEMP%` 下該項目開始之後建立、含 `mathcat`、且沒有任何 DotExpress 程序使用中的 `_MEI*` 資料夾（刪的是暫存資料夾不是程序；使用者自己先前啟動的打包版建立時間較早，不會被刪） |
| GUI 紀錄核對 | `grep` `D:/dxtest/auto127r3-f13.log`、`auto127r4-f12b-f13.log`、`auto122/123/124/125-*.log`、`auto121a-*.log`、`auto129-*.log` | 127：N-f13 `[0]*20`、`probe left False` 20 次；N-f12b 第 9 次 `-1073740940`，其餘 0，`probe left False` 20 次。122–125 的 placement 行與紀錄相同（N-f13 全部 `main_visible True`、`owner_is_main True`；N-f12b 找不到主視窗或 `main_visible False`、沒有 owner）。121 (a)：N-f13 焦點 `source editor`、UIA `('Edit', '來源文字')`；N-f12b `braille result editor`。129：兩行注音含空白；N-f12b 不含 |
| mutant（8 個，自選、與 plan 的 17 個不重複） | `$PY -X utf8 $SP/mut.py $SP/work/client $PY`（scratchpad 副本，每個 mutant 一處位元組取代、跑完還原；還原後 `cmp` 三個檔案與 worktree 相同） | 7 個被抓到，1 個存活（R1，見第 2 節與 M-3） |
| 未做 | - | 完整測試；重跑 plan 的 17 個 mutant（採信 replay 紀錄）；build；GUI 項目；項目 131（NVDA，使用者的） |

## 結論

**可以 merge。沒有 Critical，沒有 Important。** 四個決定（D1、D2、D3、D6）的程式都做到 spec 說的事，而且沒有超出；第 5 項的放棄有實測根據，沒有任何第 5 項的程式混進來；catalog、fixture、禁改檔案都沒動；測試在我自選的 mutant 下只有一個與實務無關的存活者。五個 Minor，都很便宜，都不擋 merge；M-4 是既有的 flaky 測試，不是 F-13 造成的。

逐項確認過、沒有問題的部分：

- **第 1 項（D1）。** `_left_document`（`conversion_presenter.py:317`）就是 F-12 D7 的命名條件，`_on_job_failure` 只算一次，訊息與焦點不可能不一致；`focus_source_editor()` 在 `show_error` 返回後、`finally` 的 `_finish_completion` 之前（`:313`），所以排在後面的 job 在焦點移動之後才開始（測試 A4，mutant R4 抓到）。不會偷焦點的路徑：匯出 job 走 `export.on_error`；文件仍開啟或沒有起始文件時 `left` 為假；有其他 modal（例如設定對話框）時 `BrailleFrame.focus_source_editor` 的 `IsActive()` 為假（`gui.py:1250-1253`，F-9 M-6 的既有保護）。`_end_job` 先 `set_conversion_busy(False)`，所以 `input_txt` 在框之前已啟用，`SetFocus` 不會落在停用的控制項上。GUI 121 (a)(b) 與 O1 一致。
- **第 2 項（D2）。** `__init__` 最後只剩 `_show_empty_startup_state`（清空編輯框、標題 `DotExpress`；`format_window_title(None)` 給 `DotExpress`）。`load_startup_documents` 在載入**之前**設旗標（`gui.py:261`），所以啟動框的巢狀事件迴圈裡若再有一次呼叫也不會重跑；`_close_finished` 擋掉視窗已關閉的情況（`_finish_close` 是唯一設它的地方）。wx 3.2 的 `wxEventLoopManual::DoRun` 在每次 `Dispatch()` 之前先 `ProcessPendingEvents()`，所以 `CallAfter` 的呼叫會在主迴圈處理第一個 Windows 訊息之前執行：使用者在空視窗上按鍵（Ctrl+N、Ctrl+Enter、Ctrl+Tab、Alt+F4）實務上排不到載入前面；就算排到，`adjacent_document_name` 沒有文件時回 None、`convert()` 的 `_ManualTarget(None, …)` 在文件開啟後會被 `_complete_manual` 丟棄、Alt+F4 走 `_close` 並設 `_close_finished` 使載入不執行。`on_frame_activate` 只處理雙視窗視窗，啟動框關閉時觸發它沒有副作用。`start_client_init_background` 的執行緒不呼叫 `CallAfter`、不碰 frame。載入順序（無效檔案 → 已復原 → `_ensure_open_document_exists` 的已取代字元或預設文件的存檔錯誤 → 標題 → 焦點）與 `a147fed` 相同，測試 B5 釘住；空工作區（`new`、`new (2)`）、Delete All 回滾（`on_delete_all_documents` 未改）、設定與字典選取（`_initialize_state`、`_apply_initial_settings` 在載入之前，未改）都不受影響。GUI 122–126 證實框都屬於可見的主視窗，最後狀態與 F-8a/F-8b/F-12 的紀錄相同。
- **第 3 項（D3）。** `worker_alive()` 讀 `ConversionJobRunner.is_running()`（`_thread.is_alive()`），`shutdown()` 不清 `_thread`，所以關閉後仍反映執行緒；`conversion_worker_check()` 交出 presenter 的 bound method，`OnExit` 不碰 frame（測試 C4 以 `mock_add_spec([])` 讓任何屬性存取都丟例外）。競態只會往安全方向：檢查時執行緒剛結束 → `close()`，執行緒已不在 liblouis 裡；檢查時仍活著但隨即結束 → 跳過 `close()`，程序結束由 Windows 釋放。跳過的是整個 `runtime.close()`，含 MathCAT（`MathCATAdapter.close` 只放掉 DLL 目錄 handle 與參考，不寫檔）與 `lou_free`；`cleanup_dual_view_html` 照常執行；沒有任何檔案在這條路徑上被寫到一半。正常關閉時 `_close` 在 `is_running()` 時 veto，所以 `OnExit` 遇到活著的執行緒只會在不可 veto 的關閉或 WM_ENDSESSION 路徑上。`OnInit` 失敗（例外）時 wx 不呼叫 `OnExit`，與改前相同。
- **第 3 項的 GUI 證據。** 單看 20/20 對 1/20 很弱（若真實機率是 5%，20 次都不出現的機率約 36%）；加上紀錄裡所有有效回合的合計（N-f12b 3/41、N-f13 0/51）約為 p ≈ 0.02，加上 `probe left False` 證明 `OnExit` 確實在 WM_ENDSESSION 路徑上執行、以及機制本身（`lou_free` 在 `lou_translateString` 底下），我認為足以支持「不再出現」的宣稱；主要的保護仍是 Test Plan C 的單元測試。見 M-5 關於引用已刪除 log 的小問題。
- **第 5 項（D5）的放棄。** 使用者的前提是「Esc、Alt+F4、關閉鈕絕不能觸發移除並儲存或放棄變更；若會觸發就不改」。probe 用的正是 HANDOFF 指定的設計（`wx.MessageDialog` + `SetYesNoLabels`，從 modal 的編輯器跳出），Alt+F4 在「移除並儲存(&S)」的框兩次都回答 `ID_YES`，從 frame 跳出也一樣；原因（Alt + 虛擬鍵碼等於存取鍵字元的按鍵）與 F-11 規劃時量到的「確定／取消」結果一致。結論成立。`client/ui/message_box.py`、`_confirm_hidden_rows`、`_on_cancel` 與其測試都沒動；`dialog.py` 的 diff 只有 `_hidden_row_line`。GUI 130 確認兩個框行為與 F-11 相同。Q1（b）與 Q2（Alt+F10）留給使用者。
- **第 6 項（D6）。** `_hidden_row_line` 只有 `_confirm_hidden_rows`（`dialog.py:611`）一個呼叫者；`row.braille` 是 `PreservedDictionaryRow` 讀入的原值（缺欄位時是 `""`，不會是 None）；來源文字仍 `strip()`；`no_source_text` 那行不變。tab、U+3000、引號內的換行都照原樣進入 `GenericMessageDialog` 的靜態文字（O5，使用者接受「不另外標註」）。
- **測試。** plan 的四個 red run 都有紀錄（failures 3 / 4+2 錯誤 / 3+4 錯誤 / 5），數字與各步新增的測試相符；17 個 mutant 全部被抓到；我的 8 個中 7 個被抓到。三個 flaky 測試都不是 F-13 造成的（M-4）。

## 1. 發現

### Critical

無。

### Important

無。

### Minor

**M-1. 延後載入時若發生未預期的例外，打包版會留下一個空的主視窗，沒有任何提示也沒有 log。**
- 位置：`client/gui.py:252-265`（`load_startup_documents`）、`:1330`（`wx.CallAfter`）。
- 情境：`load_documents`／`recover_interrupted_packages` 在啟動檢查之後才碰到的 OSError（例如工作區資料夾在這幾毫秒內被防毒軟體鎖住）或程式本身的 bug。改前這個例外發生在 `__init__` 裡，`OnInit` 失敗，程序結束（打包版同樣沒有訊息，但至少看得出沒啟動）。改後它發生在 pending event 的處理函式裡：wxPython 把 traceback 印到 `sys.stderr`，打包的視窗程式沒有 stderr，所以什麼都看不到；`_startup_documents_loaded` 已設為 True，視窗以標題 `DotExpress`、空清單留著，使用者可以在一個沒載入的工作區上新增文件（不會覆寫：名稱檢查會看磁碟），`gui.log` 沒有任何一行。
- 建議：在 `load_startup_documents` 把 `_load_workspace_documents_at_startup()` 包進 `try`，`except Exception` 時 `logger.exception("Failed to load the workspace at startup")` 並以既有字串 `_("The file cannot be read: {error}")` 或 `_show_file_error` 提示，然後重新 raise 或讓視窗維持空狀態。便宜；或者至少寫 log。

**M-2. 啟動框開著時收到 WM_QUERYENDSESSION，`load_startup_documents` 會在 frame 已關閉後繼續載入（既有風險，spec Risks 已列，可便宜加固）。**
- 位置：`client/gui.py:824-839`（`_load_workspace_documents_at_startup`）、`:743-753`（`_review_invalid_workspace_files`）、`:667-690`（`_open_document_by_name`）。
- 情境：無效檔案對話框或「已復原文件」框是 modal，其巢狀迴圈會把 WM_QUERYENDSESSION 派給 frame；`_close` → `_finish_close` 設 `_close_finished` 並讓 frame 關閉。框返回後載入繼續：`_ensure_open_document_exists` → `_load_document_into_editors` 對已銷毀的控制項 `SetValue`，丟 `RuntimeError`（wrapped C++ object deleted）。改前在 `__init__` 的 modal 迴圈裡也會發生同樣的事，結果一樣是程序結束，所以不是回歸；但 `_save_open_document_before_close` 在同樣情況下已有 `if self._close_finished: return` 的保護（`:736`）。
- 建議：在 `_load_workspace_documents_at_startup` 的 `_review_invalid_workspace_files` 與「已復原文件」框之後各加一行 `if self._close_finished: return`，`load_startup_documents` 在 `_load_workspace_documents_at_startup()` 之後也檢查一次再更新標題與焦點。可選。

**M-3. 「旗標在載入之前設定」沒有測試釘住（mutant R1 存活）。**
- 位置：`client/gui.py:261`；`client/tests/test_gui_document_flows.py:2373`（`test_startup_load_runs_once`）。
- 情境：把 `self._startup_documents_loaded = True` 移到載入之後，233 個測試仍全綠。實務上只有啟動框的巢狀事件迴圈能在載入中再呼叫一次，而目前沒有任何地方會這樣呼叫，所以不是 bug；但這個順序正是 docstring 說的「只跑一次」在巢狀迴圈下成立的前提，將來有人「整理」順序時不會被抓到。
- 建議：在 `test_startup_load_runs_once` 旁加一個測試：讓 fake 的 `InvalidWorkspaceFilesDialog`（或 `MessageBox`）在被呼叫時再呼叫 `frame.load_startup_documents()`，斷言事件與文件只有一份。便宜。

**M-4. 三個 flaky 測試是既有的，與 F-13 無關；其中「asks_again」兩個測試的斷言本身就依賴 2 秒內完成。**
- 位置：`client/tests/test_gui_document_flows.py:3153-3179`（`test_add_of_a_name_whose_package_is_on_disk_asks_again`、`test_rename_to_a_name_whose_package_is_on_disk_asks_again`）；`client/tests/test_workspace_service.py:1230`（`ReplacedNulCharactersTest`，`:1288`、`:1302`）；`client/tests/test_document_workspace.py:577`。
- 情境：兩個 `asks_again` 測試先讀 `alpha.dep` 的位元組，再呼叫 `on_add_document`／`on_rename_document`，而這兩個動作一開始就 `_save_open_document_with_feedback()` 重寫 `alpha.dep`；zip 的時間戳是 2 秒一格，跨過格線時位元組就不同，與 F-13 無關（F-13 沒改存檔、Add、Rename）。`ReplacedNulCharactersTest` 的 `PermissionError [WinError 5]` 來自 `os.replace`（防毒軟體短暫持有新檔）、lone-surrogate 測試的一次 error 也在存檔路徑上；這些程式 F-13 都沒碰。plan 的紀錄已正確地把它們歸為環境問題。
- 建議：不在 F-13 處理。之後可把 `asks_again` 的斷言改成比較 `load_document_package` 的內容而不是位元組，或在測試裡固定時間；`os.replace` 的 WinError 5 可考慮在 atomic write 加短暫重試（使用者 2026-10-14 已決定匯出的 `.tmp` 不加重試，這裡是另一個位置，需另問）。

**M-5. `auto-results.md` 的合計數字引用了已刪除的第一輪 log。**
- 位置：`docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/auto-results.md`「與 plan 的偏離」第 1、3 點與「觀察」第 2 點。
- 情境：第 1 點說第一輪在錯的資料夾執行、「舊 log 已刪除，本文只記錄重跑的結果」，但第 3 點與「觀察」仍引用第一、二輪的有效次數（N-f13 17+14 次、N-f12b 19 次中 1 次）來得出 3/41 與 0/51。正式結果（`auto127r3-f13.log` 20/20、`auto127r4-f12b-f13.log` 1/20）我核對過與紀錄相同；合計數字無法再核對。
- 建議：在「觀察」第 2 點註明合計包含已刪除 log 的回合、以 r3/r4 為正式結果；或刪掉合計。文件修改，便宜。

## 2. Mutant（scratchpad 副本 `$SP/work/client`，每個一處修改，跑完還原；列出的是跑的模組）

| # | 修改 | 模組 | 結果 |
| --- | --- | --- | --- |
| R1 | `load_startup_documents` 的旗標改在載入之後設定 | `test_gui_document_flows` | **存活**（M-3） |
| R2 | `_conversion_worker_is_alive` 回 `check is not None`（忽略檢查結果） | `test_gui_document_flows` | 抓到（3 個失敗） |
| R3 | `load_startup_documents` 少掉最後的 `_update_window_title()` | `test_gui_document_flows` | 抓到（3） |
| R4 | `focus_source_editor()` 移到 `_finish_completion()` 之後（排隊的 job 先開始） | `test_conversion_presenter` | 抓到（A4） |
| R5 | `bopomofo=row.braille.lstrip()` | `test_dictionary_entries_dialog` | 抓到（2） |
| R6 | `_left_document` 去掉 `is not None` | `test_conversion_presenter` | 抓到（`…without_a_starting_document_is_not_named`） |
| R7 | 關閉守衛改讀 `_closing` 而非 `_close_finished` | `test_gui_document_flows` | 抓到（B3 `closed=True`） |
| R8 | `OnInit` 在 `Show()` 之前 post 載入 | `test_gui_document_flows` | 抓到（B2） |

plan 的 17 個 mutant（Task 5 Step 6）由 replay 跑過、全部抓到，我沒有重跑。

## 3. zh_TW 用語

本次沒有新字串，catalog 只動 `#:` 行與一個 msgstr 的折行。GUI 129 讀回的清單行「第 2 列：「抹」的注音「ㄇㄚ  」格式不正確」符合 U5（原始值、不另外標註）。

## 4. 對 orchestrator 的補充

- 第 5 項的放棄：成立；沒有任何第 5 項的程式混進來（見結論）。
- 使用者尚未確認的可見預設（merge 時要列出）：O1（開啟中文件的失敗框後焦點維持原狀）、O2（主視窗先以空狀態出現一瞬）、O3（以 `CallAfter` 而非 `EVT_ACTIVATE` 觸發）、O4（跳過 `runtime.close()` 不寫 log）、O5（清單原樣顯示 tab、全形空白與引號內換行）、Q1 (a)（兩個 F-11 框維持傳統樣式）。Q2（Alt+F10 會按下既有「是／否」框的「是(Y)」）是既有行為，只回報。
- 留給使用者的：項目 131（NVDA；`D:/dxtest/manual131-f13`）；`D:/dxtest${NAME}` 這個放錯位置的資料夾與 `%TEMP%` 裡 2026-10-09～10-11 的 90 個 `_MEI*`；HANDOFF 第 6 節要求把 131 加進 `task.md` 第五節的手動項目表（`task.md` 對 agent 唯讀，由 orchestrator 處理）。
- worktree 的 `docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/auto/__pycache__/` 是執行腳本留下的，已被 `.gitignore` 排除、未進 commit；可以刪。

## 修正記錄（2026-10-14，修正階段；使用者可見的改變都是「由 orchestrator 依建議的預設決定；使用者可在 merge 前推翻」，見兩份 spec 的「規劃後的修正」第 10 點）

程式、測試與 catalog 在 commit `68c6bf4`（`fix: log an unexpected startup load error and stop the load when the window closed during a startup box (F-13 review M-1, M-2, M-3)`）：完整測試 `Ran 1651`（1646 + 5 個新測試）、`OK (skipped=6)`；407 個 msgid，catalog 只有 `#:` 行改變，`.mo` 與 `a147fed` 位元組相同（sha256 `dcf50a62…f29e32`）；`HEAD:client` `42826811dc2b5a6d5392098fbfddacba2f1cd1c1`；三個 fixture 的 sha256 不變。紀錄與文件在 commit `57f1994`（`docs: F-13 review fixes: item 127 record, spec corrections, fix-phase GUI results (F-13 review M-4, M-5)`）：`auto-results.md` 的項目 127 與新增的「修正階段」一節、`auto/run_item.sh` 與新的 `auto/mei_poll.ps1`、兩份 spec 的「規劃後的修正」第 10 點與「風險」、plan 的 35 個步驟打勾與 Implementation Notes 第 7 點。

| 發現 | 處理 | 做了什麼 |
| --- | --- | --- |
| M-1 | 已修正（`68c6bf4`） | `load_startup_documents` 把 `_load_workspace_documents_at_startup()` 包進 `try`；任何例外以 `logger.exception("Failed to load the workspace at startup")` 寫入 `gui.log`（含 traceback），並以既有字串 `無法讀取檔案：{error}`（`_show_file_error`，「錯誤」框，owner 為主視窗）顯示；視窗維持原狀，不再重試。視窗在這期間已關閉時只寫 log、不顯示框。沒有新字串。測試：`test_startup_load_logs_an_unexpected_error_and_shows_it`、`test_startup_load_error_after_the_window_closed_is_logged_without_a_box`。 |
| M-2 | 已修正（`68c6bf4`） | `_load_workspace_documents_at_startup` 在無效檔案對話框之後、「已復原文件」框之後、`_ensure_open_document_exists()`（「已取代字元」框或預設文件的存檔錯誤）之後各檢查 `_close_finished`，已關閉就返回；`load_startup_documents` 在載入之後也檢查一次再更新標題與焦點。已關閉時不再顯示後面的框、不寫入預設文件、不碰已關閉的視窗。測試：`test_startup_load_stops_when_the_window_closed_during_a_startup_box`（三個框各一個 subTest）、`test_startup_load_with_no_document_creates_none_after_the_window_closed`。 |
| M-3 | 已修正（`68c6bf4`） | 新測試 `test_startup_load_called_again_during_a_startup_box_does_nothing`：在「已復原文件」框裡再呼叫一次 `load_startup_documents`，事件、文件與檔案都只有一份。改前就會通過（釘住現有的順序），對 R1 會失敗。 |
| M-4 | 不處理（既有問題，不是 F-13 造成的） | 沒有改程式。修正階段在 scratchpad 副本用 `fbca556` 的 `gui.py` 跑 red 時，`test_rename_to_a_name_whose_package_is_on_disk_asks_again` 又因 zip 的 2 秒時間戳失敗一次，與本節所說的原因一致；記錄在 plan Implementation Notes 第 7 點。之後若要處理，見 M-4 的建議。 |
| M-5 | 已修正（`57f1994`） | 項目 127 的正式結果只引用存在的 log：`auto127r3-f13.log` 20 次中 20 次結束碼 0、`auto127r4-f12b-f13.log` 20 次中 1 次 `0xC0000374`，這 40 次都刪除了 probe 檔。核對時發現 review 的前提有一部分不成立：「舊 log 已刪除」指的只是放錯資料夾（`D:\dxtest${NAME}`）的那一輪；127 的第一、二、三輪都在 `D:\dxtest\auto127*` 執行，log 都還在。依這些 log 重新計算後，原記錄有一個錯：N-f12b 第一輪的有效次數是 18（不是 19），所以合計是 40 次中 3 次（不是 41 次）；N-f13 的 51 次中 0 次正確。合計已改標為「補充（非正式結果）」並列出所依據的 log 名稱；plan Implementation Notes 第 4 點同樣更正。 |

變異檢查（scratchpad 副本，每個一處修改，跑完還原；`test_gui_document_flows`）：R1（旗標移到載入之後）、拿掉 `except`、例外時不顯示框、視窗已關閉仍顯示框、以及四個 `_close_finished` 檢查各拿掉一個，共 8 個，全部被抓到。

修正階段的 GUI（`auto-results.md`「修正階段」）：build `D:\dxtest\N-f13b\DotExpress.exe`（48,794,200 bytes，sha256 `78CEA79B…60DE4E`）；項目 122–125 與 126（一般啟動、F-8b 70、73）在新資料夾 `D:\dxtest\auto*-f13b` 重跑，結果與 N-f13 相同。兩個與程式無關的差異：122 描述框的那一刻前景還不是 DotExpress（`<another program>`），框的 owner 與可見性相同；126 (73) 第一次啟動輔助在「已取代字元」框出現前就返回，腳本的 Ctrl+Tab 在框建立前送達主視窗，依 plan 在 `auto126-73-r2-f13b` 重跑，結果與 N-f13 相同（這個時間窗就是 spec 的 O2／「文件載入前視窗已可見」，與修正無關）。M-1、M-2 的情境沒有在 GUI 重現，由單元測試涵蓋。`run_item.sh` 改為只刪除 `mei_poll.ps1` 看到本項目程序載入的 `_MEI*`（本輪 12 個，全部刪除；`%TEMP%` 的 90 個舊資料夾未動）。

仍留給使用者：項目 131（NVDA；可用 `D:\dxtest\manual131-f13` 或含修正的 N-f13b，未勾選）；`D:\dxtest${NAME}` 與 `%TEMP%` 裡 2026-10-09～10-11 的 90 個 `_MEI*`；第 4 節列出的未確認預設 O1–O5、Q1 (a)，以及本次 M-1 的提示文字（沿用「無法讀取檔案：{error}」）與 M-2 的停止載入。
