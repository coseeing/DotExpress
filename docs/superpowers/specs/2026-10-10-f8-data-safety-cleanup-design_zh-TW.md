# 資料安全收尾（F-8）設計

## 目標

任務 F-8 收掉重構剩下的資料遺失路徑（使用者待辦清單 `task.md` 的「資料安全收尾」：第 5、10、6 項，以及 F-7 匯出的後續項目）：

1. **F-3 審查 M-1**（`docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/review_task.md`）：新增、重新命名、匯入與預設文件，會覆寫磁碟上存在、但不在文件清單裡的 `.dep`。使用者在啟動時選「保留無效檔案」，就會有這種檔案。`os.replace`（`REPLACE_EXISTING`）把它蓋掉，沒有任何訊息。
2. **F 審查 M-2／F-3 風險**（`docs/superpowers/history/2026-10-09-01-fix-data-loss/review_task.md`，優先 3）：重新命名時，若在「把舊包移到旁邊」與「安裝新包」之間當機，這份文件就沒有 `.dep`。資料留在以點開頭的 `.tmp` 檔裡，啟動時完全不提。對使用者來說，文件不見了。
3. **優先 3 的就地寫入**（同一份審查；HANDOFF 第 6 節）：`save_preprocessing_script`、`dictionaries/manager.py` 的寫入（表頭寫入，以及字典匯入、匯出用的 `shutil.copyfile`）與 `ConfigStore._save`，會就地寫入或留下暫存檔。同一份審查也問到 `ConfigStore._load` 遇到損壞的 `config.json` 會怎樣。
4. **F-7 審查 M-4**：匯出 writer 失敗時，會留下空的或寫一半的檔案。若是覆寫既有的匯出檔，原本好的檔案就沒了。
5. **第 6 項，U+0000**：Windows 的 Edit 控制項在 U+0000 結束文字。含 U+0000 的文件只顯示它之前的文字，下一次存檔就把截斷的文字寫回 `.dep`。第一個 U+0000 之後的內容全部遺失。

使用者的決定（2026-10-10，`task.md`；此處不再重新提問），記為 Decided by the user (2026-10-10)：

- **U1.** 文字進入程式時（載入 `.dep`、匯入文件），U+0000 換成 U+FFFD（替代字元），並告訴使用者，例如「文件中有 N 個無法顯示的字元，已以 U+FFFD 標示」。呈現形式由本 spec 決定，NVDA 必須讀得到。
- **U2.** F-9（後續任務，平行撰寫 spec）會把轉換結果寫回啟動轉換的那份文件。F-8 不規格化它，也不能和它衝突。

本任務完成後：

- 程式的任何動作都不會覆寫或移除不在文件清單中的 `.dep`。新增與重新命名會以既有的「已存在」訊息拒絕這個名稱，匯入把它列為匯入問題，預設文件改用一個沒被占用的名稱。
- 啟動時，若某份文件的重新命名或存檔因當機而中斷，只要名稱沒被占用、清單裡也沒有內容相同的文件，就把它放回原本的包名稱，並告訴使用者復原了哪些文件。程式從不刪除任何暫存檔。
- 其餘所有寫入使用者資料的地方都改走 `shared/atomic_write.py`：文字處理程式、新增／匯入／預設字典建立的字典檔、字典匯出、`config.json`，以及 BRL 與 HTML 匯出。失敗時目標檔逐位元組不變（或仍不存在），也不留下暫存檔。成功時寫出的位元組與現在相同。
- 不能用的 `config.json` 不再讓程式無法啟動，也不會被默默丟掉：不是 JSON 物件的檔案視同損壞；接受 UTF-8 BOM；讀不到的檔案不會被覆寫；損壞的檔案在被取代前會先複製成 `config.json.bak`。
- U+0000 永遠不會進到編輯框。開啟原本含 U+0000 的文件時，會跳出訊息框，寫出文件名稱與字元數；每份文件每次執行只出現一次。第一次存檔就寫入取代後的文字，所以下次啟動不會再出現。

新的使用者可見字串：4 個（msgid 364 -> 368），見「使用者可見字串」。

非目標：字典條目與文字處理程式中的 U+0000（見範圍外）；刪除或清理暫存檔；取代時保留屬性、ACL 或替代資料流（沿用 F-3 D11）；不同執行緒之間 `config.json` 的讀改寫競態；F-9 的轉換結果去向。

**拆分建議。** 工作可以乾淨地分成兩個任務。建議實作為 **F-8a**（D1–D2、D6–D11：沒有新字串、沒有新 UI），接著 **F-8b**（D3–D5、D12–D15：兩個提示與 4 個新 msgid），各自有 plan、review 與 build。本 spec 同時涵蓋兩者，讓決策保持一致。若協調者決定維持一個任務，下面的遷移步驟依序執行即可，不需更動（Decided by orchestrator with the recommended default; user may override before merge）。

## 與 F-9 的關係

F-9（轉換結果寫回啟動轉換的文件）正在 `D:\workspace\DotExpress-f9` 平行撰寫 spec。F-8 刻意避開它：

- F-8 不動 `ui/conversion_presenter.py`、`conversion/`、雙視窗模組，也不動 `gui.py` 中與轉換有關的部分。
- U+0000 的提示（D13）加在 `BrailleFrame._open_document_by_name` 的最後。它只讀 service 的記錄，從不讀編輯框或轉換狀態。
- service 新增的記錄（待提示的 U+0000 數量，D12）以文件名稱為鍵，並跟著重新命名與刪除移動，和 F-5 的存檔記錄一樣。F-9 把轉換結果存進未開啟的文件時，走 `DocumentController.replace_document`，不會產生 U+0000，所以不需要 F-8 做任何事。
- 後 merge 的任務在合併後的 `main` 上重跑完整套件；行號由 plan 重新標出。

## 規劃後的修正（2026-10-10）

F-8a 的 plan（`docs/superpowers/plans/2026-10-10-f8a-data-safety-cleanup.md`，在 `bfd24db` 的 scratch clone 上 dry run：Task 0–5 完全重現，每個步驟也以 plan 自己的區塊腳本套用過，GUI 項目 66–69 與 76–82 對同一份程式碼的 packaged build 與 `N-f7` 都執行過）沒有發現決策 D1、D2、D6–D11 或其行為對照列的錯誤。plan 細化本規格之處，以本節為準。D3–D5 與 D12–D15 屬於 F-8b，之後再規劃；本節不改動它們。

1. **採用拆分（O1）。** F-8a ＝ D1、D2、D6–D11，遷移步驟 1–4，測試計畫 A–C，沒有新字串也沒有新 UI，在 `fix/f8-data-safety-cleanup` 上進行。F-8b ＝ D3–D5、D12–D15，步驟 5–6，測試計畫 D–F，兩個通知與 4 個 msgid；F-8a merge 之後在新分支上另寫 plan。Windows 項目 66–69、76–82 與人工項目 84 屬於 F-8a；項目 70–75 與人工項目 83 屬於 F-8b。編號不變。
2. **F-8a 的數量：** 步驟 1–4 之後分別是 `Ran 1378`、`1386`、`1389`、`1400`（新增 10、8、3、11 個測試；基準 1368；全程 `FAILED (errors=1, skipped=7)`，只有 F-W6；msgid 維持 364 個）。測試計畫 C 有 10 個測試（C3 是兩個：第三個檔案，以及經 `CaseInsensitivePackageFiles` 的只改大小寫重新命名；C9 就是既有的 `test_case_only_rename_keeps_the_document`，它已經在真正的 NTFS 上經由主視窗把 `Alpha` 改名為 `alpha`）；A 有 14 個（A4 是修改既有測試）；B 有 8 個（B7 是兩個測試）。驗收條件 2 的測試組從 `Ran 502` 變為 `Ran 534`，`OK (skipped=7)`。
3. **所有寫入者共用一種故障注入。** 新的測試輔助模組 `client/tests/full_disk.py`（`full_disk(folder, after=N, pattern=...)`）在 `with` 區塊內替換 `builtins.open` 與 `io.open`：在 `folder` 內以寫入模式開啟的檔案，寫入 `N` 個字元或位元組之後就拋出 `OSError(ENOSPC)`。舊的就地寫入（`Path.write_text`、`shutil.copyfile`、`open("w")`、`NamedTemporaryFile`）與 `shared.atomic_write` 都會遇到這個故障。它取代了對 `shutil.copyfileobj`（A6、A7；在 Windows 上 `copyfile` 不會呼叫它）、`json.dump`（A14）與 `os.replace`（A11）的 patch。
4. **五個既有測試用 `<name>.dep` 資料夾讓寫入失敗。** D1 讓這種名稱算作已被占用，所以它們改用 `full_disk`（新增，以及服務與主視窗的匯入）或讓安裝步驟失敗（重新命名，`_FailingReplacePackageFiles(destination_name=...)`）注入故障，測試目的不變；訊息改為逐字比對（`[Errno 28] No space left on device`）。為了存檔、刪除或全部刪除而占用名稱的測試不變。
5. **`Mock` 服務的測試骨架**設定 `package_name_taken.return_value = False` 與 `free_document_name.side_effect = lambda base: base`；測試計畫中另外兩項設定屬於 F-8b。
6. **D8：匯出到同名資料夾時保留現在的訊息。** 只靠 `write_text_atomically` 的話，匯出到同名資料夾會以「取代失敗」結束，訊息中出現暫存檔名（`[WinError 5] ...: '<dir>\.alpha.brl.<random>.tmp' -> '<dir>\alpha.brl'`），而不是 F-7 的匯出測試與項目 56 固定下來的 `[Errno 13] Permission denied: '<dir>\alpha.brl'`。因此 `documents/workspace.py` 新增 `write_export_text(path, text)`：`path` 是資料夾時，拋出就地寫入會拋出的錯誤（Windows 是 `PermissionError` 13，其他平台是 `IsADirectoryError`）；否則呼叫 `write_text_atomically(..., encoding="utf-8", newline=None)`。`export_document_brl` 與 `_write_html`（在函式內 import）都使用它。`shared/atomic_write.py` 維持不變：改 `ensure_writable` 也會改變字典編輯器遇到資料夾時的訊息，而那是 F-2 D5 固定下來的。
7. **D6、D7 的名稱。** 寫標頭的函式是私有的 `_write_header(stream)`；`dictionaries/manager.py` 新增模組說明，寫明以原子方式寫入；`save_preprocessing_script` 移除 `os` 與 `tempfile` 的 import。
8. **D10、D11 的細節。** 不是物件時，在 `_load` 的 `try` 內拋出 `ValueError("config.json does not hold a JSON object (<type>)")`（型別名稱為 `NoneType`、`list`、`str`、`int`），因此照舊記錄。略過的存檔以 `WARNING` 記錄 `Config file %s was not saved because it could not be read`，同一路徑的同一種讀取錯誤只記一次（`_logged_skipped_saves`，讀取成功時清除），並附上讀取錯誤（`_log_current_exception` 新增 `exc_info` 參數）。`_backup_unreadable` 先讀出目前的位元組，再以 `write_bytes_atomically` 寫入 `config.json.bak`；這一步任何失敗都記錄為存檔失敗，且不寫入任何檔案。
9. **`test_config` 在 `setUpModule` 隔離 `dotexpress.config`**（實作在主 checkout 執行；在 `assertLogs` 之外記錄的測試不可以寫入使用者的 `client/log/config.log`）。
10. **測試細節。** A1 的腳本含 `\r\n`，換行轉換會現形；A3 先檢查錯誤的檔名；A9 在資料夾被刪除之前釋放佔用；A12 以 `os.linesep` 比較；B2 也檢查記錄下來的 `ValueError` 文字；B5 改兩次設定，預期只有一個略過存檔的警告；B6 以 `create=True` patch `config.write_bytes_atomically`。
11. **程式在啟動時就會寫入 `config.json`。** client-init 執行緒在主視窗顯示後立刻存入 client id，所以行為對照表中的「下一次變更」在啟動時就發生：F-8 之前，含 BOM 的檔案在啟動時就被 `{"client": {"id": ...}}` 取代（在 `N-f7` 上實測，項目 80；截斷或不是 UTF-8 的檔案走同一條路）；F-8 之後，檔案損壞時這第一次寫入會先保留 `config.json.bak`（項目 79），檔案讀不到時則略過並記錄一次警告（項目 81）。
12. **Windows 項目。** 字型大小以「Ctrl＋在原文編輯框上滾動滑輪一格」改變。項目 80 檢查含 BOM 的檔案中的寬度 30 被保留，不在「設定」中改寬度。項目 81 以**只允許寫入**的共用模式（其他程式可寫不可讀）佔用 `config.json`，而不是「不共用」：不共用時，啟動時既有的可寫入檢查（`prepare_application_directories` 以附加模式開啟 `config.json`）會失敗，兩個版本都顯示既有的「啟動錯誤」，那不是 D11 的情況。F-8 之前的項目 79：沒有主視窗，程序約 3 秒後以結束碼 1 結束，沒有任何記錄。項目 77、78 以 `lockshare.py`（共用讀寫）佔用目標檔。項目 82 比較兩個版本做同樣步驟後的位元組。
13. **驗收條件 7。** `shared/atomic_write.py` 之外，正式程式碼中剩下的直接寫入是：`app_paths.py` 對 `config.json` 的附加模式檢查（不寫入任何內容）、`PackageFiles.write` 與 `PackageFiles.temporary_path`（F-3 重新命名時私有的暫存套件檔，同步到磁碟後以 `os.replace` 安裝），以及 `dual_view/files.py`（規格已排除）。

## 規劃後的修正（F-8b，2026-10-10）

F-8b 的 plan（`docs/superpowers/plans/2026-10-10-f8b-recovery-and-nul.md`，在 `main` `1b19290` 的 scratch clone 上 dry run：Task 0–3 完全重現，每個步驟也以 plan 自己的區塊腳本套用、翻譯檔指令照 plan 執行，GUI 項目 70–75 對同一份程式碼的 packaged build 與 `N-f8a2` 都執行過）依 F-8a 之後的程式碼重新檢查了 D3–D5 與 D12–D15，沒有發現這些決策或其行為對照列的錯誤。plan 細化本規格之處，以本節為準。

1. **數量。** 步驟 5 之後 `Ran 1419`（新增 16 個測試），步驟 6 之後 `Ran 1434`（新增 15 個）；基準 1403（F-8a 的 1400 加上其審查補的 3 個）；全程 `FAILED (errors=1, skipped=7)`，只有 F-W6；msgid 364 -> 366 -> 368。測試計畫 D 有 15 個：`test_document_workspace` 的 D1–D9 再加兩個（不是包殘留的檔案被忽略；兩個中斷的重新命名依舊到新復原），D8 也記錄 `os.replace`（`test_recovery_never_deletes_or_replaces_a_file`）；`test_workspace_service` 的 D11、D12 與「沒有殘留時不復原任何東西」；D13。測試計畫 E 有 14 個：E1–E13（E13 是 `test_editors_receive_the_full_text`）再加 `test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened`（項目 75 的流程）。驗收條件 2 的測試組從 `Ran 537` 變為 `Ran 568`，`OK (skipped=7)`。
2. **F1 拆成兩個，** 每個步驟一個，讓每次重新產生翻譯檔之前都先紅燈：`test_recovery_strings_are_translated`（步驟 5）與 `test_replaced_character_strings_are_translated`（步驟 6）。
3. **log 隔離。** `test_document_workspace` 與 `test_workspace_service` 在 `setUpModule` 隔離 `dotexpress.gui`。復原的測試斷言沒有任何記錄，D9 除外：在 Windows 上 `os.rename` 會拒絕已被占用的名稱，所以少了名稱規則時只會在 log 中出現。
4. **D9** 以 patch 過的 `os.rename`（先建出目標檔再改名）模擬競態。記錄為 `ERROR` 層級的一行 `Cannot recover interrupted document package <path>: [WinError 183] ...`，不附 traceback。
5. **D3 的細節。** 樣式為 `^\.(?P<stem>.+)\.(?i:dep)\.[A-Za-z0-9_]+\.tmp$`，只看一般檔案。主檔名不是合法文件名稱的檔案，光靠 `_read_package(package_path, package_name)` 就會略過（成員名稱經正規化後必須等於主檔名）；規則 1 的明確檢查保留，由 D6 釘住行為。logger 在呼叫時才取得。復原的文件依載入清單的順序（先 `casefold`，再比名稱）併入；訊息框依復原順序（最舊的先）列出名稱。
6. **D12 的輔助函式。** `documents/workspace_service.py` 新增 `_displayable_documents(documents) -> (documents, counts)`，載入與全部刪除後的重新載入都用它；`take_replaced_character_count` 取出並移除數量。
7. **翻譯檔。** 步驟 5 中 `msgmerge` 把 `Documents Recovered` 模糊配對到 `Documents`（`文件`）；plan 去掉這個旗標。步驟 6 沒有模糊配對。兩次重新產生也一併更新 F-8a 留下的過時 `#:` 參照行。
8. **Windows 項目。** 「改前」是 `N-f8a2`。wx 把每個訊息框顯示成 task dialog：第一段是主要說明，其餘是內容；UIA 讀不到圖示（由單元測試釘住）。啟動時的訊息框出現在主視窗之前。項目 74、75 匯入 `zero.txt`：`nul` 是 Windows 的保留名稱，`nul.txt` 會成為匯入問題。F-8b 之前，項目 73–75 也顯示磁碟上的遺失：文件開啟後關閉程式（或開啟另一份文件），包裡只剩第一個 U+0000 之前的文字。項目 70 多一次啟動：改 alpha 的文字、關閉後再啟動（見 9）。
9. **新的風險（已實測）：被略過的殘留檔，之後的某次啟動可能被復原。** 規則 1–4 每次啟動都重新判斷，被略過的檔案留在磁碟上。重新命名 alpha 為 gamma 時中斷：alpha 被復原，staged 的 `.gamma.dep.<8>.tmp` 留著；使用者一旦修改 alpha，下次啟動就把那份 staged 檔以舊文字復原成新文件 `gamma`，並顯示列出 `gamma` 的「已復原文件」（F-8b build 上項目 70 的第三次啟動）。同理，已完成的重新命名留下的舊包，在改名後的文件被修改後會以舊名稱回來；中斷的存檔留下的暫存檔，在其文件被改名或刪除後會回來。不會遺失資料；只是多出一份文件，可能在當機很久之後才出現，訊息框會列出它。要避免這種情況，需要本規格沒有做的決定（例如記住處理過的殘留檔，或把它們改名移出樣式，那會動到使用者的檔案）。這是給使用者的待決問題，不阻擋實作；F-8b 照上面的 D3 實作。

## 現況（2026-10-10 於 `main` `861d110`、Windows 11 26200、NTFS 驗證）

`$PY` 是 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`（Python 3.13.15，wxPython 4.2.5 msw）。`$SP` 是 session 的 scratchpad。探針在 `$SP\f8\probes\`，不 commit。它們在 `$SP\f8\copy\client` 上執行（`861d110` 的 `git archive`，加上從主 checkout 複製的 git-ignored liblouis 與 MathCAT runtime），只寫入 `$SP\f8\` 底下：

- `nul_sources.py`：哪些匯入路徑會讓 U+0000 進到 `Document`（真實匯入程式碼，手工製作的範例檔）；
- `nul_editor.py`：主視窗兩種 `wx.TextCtrl` 樣式遇到 U+0000、打字與貼上；
- `workspace_probe.py`：M-1、當機殘留（子程序在指定步驟以 `os._exit` 結束自己）、U+0000 的存檔路徑；
- `config_probe.py`：`ConfigStore` 遇到不尋常的 `config.json`；
- `export_probe.py`：匯出的位元組與失敗行為。

基準：`main` 上 `cd client && $PY -B -X utf8 -m unittest discover -s tests` 為 `Ran 1368`、`FAILED (errors=1, skipped=7)`（F-7 審查記錄）；唯一的 error 是 F-W6（`test_dictionary_name_prompt ... test_case_only_rename_still_renames`）。msgid：364 個（`dotexpress.po` 含表頭共 365 行 `msgid`）。

### M-1：在磁碟上、但不在清單中的檔案（`workspace_probe.py m1`）

每個工作區都有一份有效的 `alpha.dep`，和一份無效的 `bad.dep`（啟動時選擇保留：`load_documents` 在 `invalid_paths` 中回傳它，controller 不列出它）。

| 動作 | 程式路徑 | 結果 |
| --- | --- | --- |
| 新增 `bad` | `DocumentWorkspaceService.create_document` -> `save_document_package` -> `os.replace` | 沒有錯誤；`bad.dep` 被空文件取代 |
| 把 `alpha` 重新命名為 `bad` | `rename_document` -> `move_document_package`（安裝時 `os.replace(staged, bad.dep)`） | 沒有錯誤；`bad.dep` 被取代，`alpha.dep` 消失 |
| 匯入 `bad.txt` | `import_files` -> `batch_import_documents(existing_names=controller 的名稱)` -> `save_document_package` | 沒有匯入問題；`bad.dep` 被取代 |
| 啟動時只剩一份被保留的無效 `new.dep` | `_ensure_open_document_exists` -> `_create_default_document` -> `create_document("new")` | 沒有錯誤；`new.dep` 被空文件取代 |

`BrailleFrame._prompt_for_document_name`（`gui.py:699-720`）只檢查 `DocumentController.document_name_exists`，而它只知道清單中的文件。

### 當機殘留（`workspace_probe.py crash`）

先存好 `alpha.dep`，再由子程序存檔或重新命名，並在指定步驟結束自己。

| 中斷的步驟 | 之後的檔案 | 下次啟動（`load_workspace_documents`） |
| --- | --- | --- |
| 把 `alpha` 重新命名為 `gamma`，移到旁邊之後、安裝之前 | `.alpha.dep._vw4x6f_.tmp`（成員 `alpha.txt`／`alpha.brl`，mtime 等於舊包的 mtime）、`.gamma.dep.mlw4jang.tmp`（成員 `gamma.*`，文字相同，mtime 為當時） | **一份文件都沒有**；沒有任何提示 |
| 重新命名完成，但移除旁邊那份檔案失敗（注入） | `gamma.dep`、`.alpha.dep.7gdjw2yi.tmp`（內容與 `gamma` 相同） | `gamma` |
| 存 `alpha`，`fsync` 之後、`os.replace` 之前 | `alpha.dep`（舊文字）、`.alpha.dep.97dc8315c5cf865f.tmp`（完整，新文字） | `alpha`，內容是舊文字 |

- `os.replace` 保留被搬動檔案的修改時間，所以移到旁邊的舊包一定比 staged 的新包舊。
- 寫到一半中斷的暫存檔，以及 `PackageFiles.temporary_path` 在寫入前預先建立的空檔，都不是有效的 zip。
- 兩種暫存檔名是 `.<包名>.<16 個十六進位字元>.tmp`（`write_bytes_atomically`，存檔／新增／匯入）與 `.<包名>.<8 個字元>.tmp`（`PackageFiles.temporary_path` 中的 `tempfile.NamedTemporaryFile`，重新命名時的 staged 檔與移到旁邊的檔）。`*.dep` 兩種都不會比對到（F-3 D13，由 `test_load_workspace_documents_ignores_leftover_temporary_files` 與 `test_startup_ignores_leftover_temporary_files` 釘住）。
- 在 NTFS 上，`dst` 已存在時 `os.rename(src, dst)` 會拋出 `FileExistsError`（`winerror` 183），只有大小寫不同（`Alpha.dep`）或 `dst` 是資料夾時也一樣。它從不取代。

### 仍然就地寫入的地方

| 寫入者 | 程式碼 | 目前失敗時 |
| --- | --- | --- |
| `save_preprocessing_script`（`conversion/preprocessing/user_script.py:53-74`） | `NamedTemporaryFile(prefix=".preprocessing.py.")` + `os.replace`；沒有 `fsync`；暫存路徑在寫完之後才記錄 | 寫入時的例外會留下 `.tmp`；沒有 `fsync`；POSIX 權限 `0600`。唯讀的程式檔得到 `[WinError 5] 存取被拒。: '...\.preprocessing.py.<8>.tmp' -> '...\preprocessing.py'`（實測） |
| `ensure_default_dictionary`（`dictionaries/manager.py:18-26`）、`create_dictionary`（`:58-68`） | `path.open("w", newline="")` + `csv.writer` 寫表頭 | 留下寫一半的新檔；成功時的位元組 `text,braille,type\r\n`（實測） |
| `import_dictionary`（`:71-81`） | 在 F-6 的完整驗證之後 `shutil.copyfile(source, destination)` | 留下寫一半的新字典，而且會被列出 |
| `export_dictionary`（`:97-101`） | `shutil.copyfile` 到使用者選的路徑 | 留下寫一半的檔案；該處既有的檔案先被截斷 |
| `ConfigStore._save`（`config.py:113-127`） | `open(path, "w")` + `json.dump(indent=2)`；任何例外都記到 `config.log` 後吞掉 | 截斷的 `config.json`。成功時的位元組用 CRLF（文字模式，實測） |
| `export_document_brl`（`documents/workspace.py:256-260`，BRL 匯出與 Ctrl+E） | `Path.write_text(encoding="utf-8")`，CRLF | **既有的好檔案變成空檔**（實測：寫入拋出例外時 `b"OLD GOOD EXPORT"` -> `b""`） |
| `formats._write_html`（`documents/formats.py:104-109`） | 先轉成 HTML，再 `Path.write_text`，CRLF（實測：空的雙視窗有 25 個 CRLF） | 轉換階段的錯誤不動舊檔；寫入階段的錯誤會截斷它 |
| `formats._write_dep`、`save_document_package` | `write_bytes_atomically`（F-3） | 已是原子寫入 |
| `dictionaries/entries.py`（`save`） | `write_text_atomically`（F-2） | 已是原子寫入 |
| `dual_view/files.write_dual_view_html` | 在 `paths.dual_view` 中以 `write_text` 寫程式自己的暫存頁面，結束時刪除 | 不是使用者資料；不在範圍內 |

### `ConfigStore` 遇到不尋常的檔案（`config_probe.py`）

`_load`（`config.py:92-111`）攔下 `FileNotFoundError`（回傳空 dict，不記 log）與其他所有 `Exception`（每種不同的失敗記一次 `WARNING`「Failed to read config file %s; using defaults」，回傳空 dict）。它回傳 `json.load` 回傳的任何東西。

| `config.json` | getter | 第一次變更設定（`set_output_mode("ascii")`） |
| --- | --- | --- |
| 不存在 | 預設值 | 建立檔案，`language_detection` 預設值在最前面 |
| 空檔、截斷的 JSON、cp950 位元組、**含 BOM 的 UTF-8** | 預設值；一則 warning | **把檔案換成 `{"conversion": {"output_mode": "ascii"}}`**：其他設定全部消失，舊內容也沒了 |
| `[1, 2]`、`"text"`、`null`（合法 JSON，但不是物件） | **每個 getter 都拋出 `AttributeError`**（`'list' object has no attribute 'get'`） | 同樣拋出 |
| 某個 section 不是物件（`{"conversion": [1], "view": 3}`） | 該 section 用預設值 | 該 section 被取代；其他保留 |
| 正常的檔案 | 檔案中的值 | 合併，其他值保留 |

- `BrailleFrame.__init__` 透過這些 getter 讀設定，`BrailleApp.OnInit` 在那裡沒有攔例外。所以 `config.json` 是 `null` 或陣列時，packaged build 會在啟動時直接停止，沒有任何訊息（讀程式碼推得；Windows 項目 79 確認）。
- UTF-8 BOM 來自會寫 BOM 的編輯器（舊版記事本的「UTF-8」）。這種檔案被當成損壞，下一次變更設定就把它的設定全部丟掉。
- 讀取時的 `OSError`（例如共用衝突）也會得到預設值，下一次變更設定就把整個檔案換成那一個值（讀程式碼推得）。
- `start_client_init_background` 在另一個執行緒呼叫 `get_or_create_client_id`（讀改寫，沒有鎖）。已知缺陷；不變。

### U+0000 從哪裡來（`nul_sources.py`，真實匯入程式碼）

| 來源 | 結果 |
| --- | --- |
| 含 NUL 位元組的 `.txt`（`load_text_document`，UTF-8） | **保留**：`'A\x00B\nline2\x00\x00end\n'`，3 個 NUL |
| **沒有** BOM 的 UTF-16LE `.txt`（`"AB"`） | **保留**：以 UTF-8 解碼成 `'A\x00B\x00'`，每個 ASCII 字元後面一個 NUL |
| 有 BOM 的 UTF-16 `.txt` | `UnicodeDecodeError`（匯入問題；不變） |
| `.txt`、`.brl` 成員含 NUL 的 `.dep`（`load_document_package`，啟動與匯入） | 文字與點字都**保留** |
| `.pdf`，標準字型的字串 `(A\000B)`，無標記（pymupdf 路徑） | **保留**：`'A\x00B'` |
| `.pdf`，同樣的字串在有標記的 PDF 中（pypdf MCID 路徑） | **保留**：`'A\x00B'` |
| `.pdf`，`ToUnicode` CMap 把某個碼對應到 `<0000>` | 不保留：pymupdf 給出字形本身的字元 |
| `.docx`，原始 NUL 位元組或 `&#0;`（`&#1;` 也是） | `ExpatError`（匯入問題；不變） |
| `.docx`，`_x0000_` 或 `<w:sym w:char="0000"/>` | 沒有 NUL（`_x0000_` 保持為字面文字） |
| `.epub`，原始 NUL 位元組或 `&#0;` | 沒有 NUL（被丟掉） |

DotExpress 也會把 NUL 寫進自己的包：含 NUL 的匯入原樣存成 `.dep`，所以來自 PDF 或文字檔的 NUL 會一直留在工作區裡。

### 編輯框遇到 U+0000（`nul_editor.py`，`TE_MULTILINE` 與 `TE_MULTILINE | TE_READONLY` 的 `wx.TextCtrl`）

| 操作 | 結果（兩種樣式相同） |
| --- | --- |
| `SetValue("a\x00b")`／`ChangeValue` | `GetValue()` 為 `'a'` |
| `SetValue("line1\nli\x00ne2\nline3")` | `'line1\nli'`：第一個 NUL 之後的內容全部消失，跨行也一樣 |
| `SetValue("\x00abc")` | `''` |
| `SetValue("a\ufffd\ufffdb\n\ufffd")` | 原樣傳回 |
| 碼為 0 的 `WM_CHAR`（Ctrl+@ 會送出的） | 被忽略；什麼都沒插入 |
| `EM_REPLACESEL "X\x00Y"`、`WriteText("X\x00Y")` | 只插入 `X` |
| `WM_PASTE` 一個內容為 `"P\x00Q tail"` 的 `CF_UNICODETEXT` | 只貼上 `P`；`wx.TheClipboard` 讀到的也是 `'P'` |

所以打字與貼上都無法把 U+0000 放進編輯框。貼上會停在 NUL，但文件中原有的內容不會遺失，使用者也看得到貼上了什麼。唯一的路徑是從文件 `SetValue`（`_load_document_into_editors`，`gui.py:554-556`）與從轉換結果 `SetValue`（`show_conversion_output`）。轉換讀的是編輯框（F-7 的 `_editor_text`），而編輯框不可能含 NUL，所以開啟中文件的轉換結果，除了使用者的文字處理程式之外沒有 NUL 的來源（見範圍外）。

注意：貼上的探針會先存下剪貼簿的 Unicode 文字，結束後再放回去。這裡記錄的那次執行中，放回失敗（`OpenClipboard` 短暫被占用），所以改為清空剪貼簿。之後的探針必須重試 `OpenClipboard`。

**存檔路徑**（`workspace_probe.py nul`，真實的 service 與真實的 `wx.TextCtrl`）：`alpha.dep` 的文字為 `"first line\nsecond\x00 line after NUL\nthird"`。`controller.open_document("alpha")` 並 `SetValue` 之後，編輯框顯示 `'first line\nsecond'`。`save_open_document(text=編輯框文字, ...)`（每次切換文件都會做）寫入 `'first line\nsecond'`，文件其餘部分遺失。F-5 D2 會寫入它，因為編輯框的文字和存檔記錄不同。

實測成本：550,000 個字元，乾淨文字的 `str.count("\x00")` 0.15 ms，計數加 `replace` 0.6 ms。

### 主視窗的呈現方式

主視窗沒有狀態列（`_create_main_layout`，`gui.py:167-176`：文件清單與兩個編輯框）。而且 NVDA 本來就不會自動報讀狀態列的變化。主視窗現有的提示全部是透過 `ui.message_box.message_box`（F-7）的訊息框：`show_info`、`show_warning`、`show_error`（`gui.py:1112-1121`）。訊息框出現時，NVDA 會讀出標題、內文與按鈕。

### 釘住目前行為的測試

- `test_document_workspace.py` 的 `test_load_workspace_documents_ignores_leftover_temporary_files` 與 `test_gui_document_flows.py` 的 `test_startup_ignores_leftover_temporary_files`：殘留檔內容是 `b"not a zip"`。它們維持綠燈（無效的封存檔從不被復原，D3）。
- `test_user_preprocessing_script.py` 的 `test_save_uses_utf8_and_atomic_replace` patch `conversion.preprocessing.user_script.os.replace`，並 glob `.preprocessing.py.*.tmp`。
- `test_config.py`：`ConfigLoadFailureLoggingTest`（每種不同的失敗一則 warning，回傳預設值）、`test_store_writes_the_documented_config_bytes`（用 `read_text` 讀，所以看不到 CRLF）、`ConfigSaveFailureLoggingTest`。
- `test_dictionary_manager.py`：複製與表頭的測試比對位元組或列。
- `test_gui_document_flows.py` 的 `_make_frame` 用 `Mock` service 建 frame。新的 service 方法在那裡會回傳為真的 `Mock`（見測試計畫）。
- 沒有測試釘住 M-1、匯出截斷或 U+0000。

## 決定

### M-1：絕不取代不在清單中的包

**D1. 名稱的包在磁碟上，就算已被占用。**

- `DocumentWorkspaceService.package_name_taken(name: str, *, exclude_name: str | None = None) -> bool`：若有 `exclude_name` 且 `name.casefold() == exclude_name.casefold()`（重新命名時自己的包，包括 NTFS 上只改大小寫的重新命名），回傳 `False`；否則回傳 `os.path.lexists(self.package_path(name))`。在 NTFS 上這個檢查不分大小寫，資料夾或壞掉的連結也算。
- `BrailleFrame._prompt_for_document_name`：既有的檢查改為 `self._document_controller.document_name_exists(document_name, exclude_name=exclude_name) or self._workspace_service.package_name_taken(document_name, exclude_name=exclude_name)`。使用者看到既有的訊息框 `Document "{name}" already exists.`（`文件「{name}」已存在。`），名稱對話框再次出現並預先填好名稱。新增與重新命名都適用。沒有新字串。
- `DocumentWorkspaceService.create_document`：寫入前 `if os.path.lexists(path): raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(path))`。這攔下在詢問名稱之後才出現的檔案（競態）。`_create_document` 以既有的 `Failed to save document: {error}` 顯示。
- `move_document_package`：安裝的 `try` 區塊一開始就 `if files.exists(new_path): raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(new_path))`。這時舊包已移到旁邊，所以在不分大小寫的檔案系統上只改大小寫的重新命名，`new_path` 已不存在；找到的任何東西都是第三個檔案。既有的 `except` 把舊包放回去並移除 staged 檔。留下一份包，也就是舊的那份（F-3 的失敗約定）。
- `import_files`：`existing_names` 改為 controller 的名稱，加上磁碟上每個 `*.dep` 的主檔名（`{path.stem for path in workspace.glob("*.dep")}`）。名稱已被占用的檔案，會得到既有的匯入問題文字 `Document "{name}" already exists.`，路徑是來源檔，和現在清單內重複時一樣。

開啟中文件的存檔不變：它的目標就是自己的包。

**D2. 預設文件使用沒被占用的名稱。** `DocumentWorkspaceService.free_document_name(base: str) -> str`：controller 與磁碟（D1）都沒有 `base` 時回傳 `base`，否則回傳 `f"{base} (2)"`、`f"{base} (3)"`……中第一個沒被占用的。`_create_default_document` 使用 `free_document_name(DEFAULT_DOCUMENT_NAME)`。因此現在「保留了無效的 `new.dep`」的啟動，會建立 `new (2)`，不動 `new.dep`。沒有 `new.dep` 時完全不變（Decided by orchestrator with the recommended default; user may override before merge）。`new (2)` 通過 `normalize_base_name`（已確認）。否決：不建立預設文件（編輯框會接受永遠存不起來的輸入）。

### 中斷的存檔與重新命名

**D3. 啟動時把中斷的包放回去，不刪除也不取代任何東西。** `documents/workspace.py` 新增 `recover_interrupted_packages(directory: Path, listed: list[Document]) -> list[Document]`：

1. 候選者是 `directory` 中檔名符合 `^\.(?P<stem>.+)\.dep\.[A-Za-z0-9_]+\.tmp$`（`.dep` 不分大小寫）的一般檔案。現況中的兩種命名都符合。`stem` 必須等於 `normalize_document_name(stem)`，否則略過。
2. 每個候選者都以包載入程式的檢查讀取，並以 `stem` 為名稱比對（新的私有函式 `_read_package(path, package_name)`；`load_document_package` 保留它的 `.dep` 檢查並呼叫它）。不是有效包的檔案（寫到一半中斷的、預先建立的空檔）略過。
3. 候選者依 `(st_mtime_ns, stem.casefold(), stem)` 的順序處理。移到旁邊的包保留舊包的 mtime，所以重新命名中斷後它排在最前面，文件以舊名稱回來，正如 F-3 對失敗的重新命名所承諾的。
4. 若資料夾中任何 `*.dep`（不論是否在清單中、不分大小寫）的主檔名（`casefold`）與它相同，或清單中、已復原的文件有相同的 `(text, braille)`，就略過。第二條規則略過「已完成的重新命名」留下的舊包，以及剛復原的檔案的 staged 雙胞胎。
5. 否則以 `os.rename(candidate, directory / f"{stem}.dep")` 改名。在 Windows 上這永遠不會取代既有檔案（見現況）。在 POSIX 上由第 4 步把關（不是出貨平台）。復原的 `Document` 加入結果。
6. 改名時的 `OSError` 寫進 log（`dotexpress.gui` logger，在呼叫時才綁定，同 F-7 D6：`Cannot recover interrupted document package %s: %s`，一行），檔案留著。

不刪除任何東西：被略過的候選者照舊留在磁碟上（F-3 D13）。`DocumentWorkspaceService.load_documents` 在 `load_workspace_documents` 之後呼叫它，在 controller 與存檔記錄看到之前，把復原的文件加進載入清單，並保留它們的名稱給 D4。只有啟動時會復原，全部刪除失敗後的重新載入不會。

對實測殘留的結果：重新命名中斷 -> `alpha` 帶著它的文字回來，`.gamma.dep.<8>.tmp` 留著（內容相同）。重新命名已完成、留下舊包 -> 什麼都不做。存檔中斷而 `alpha.dep` 存在 -> 什麼都不做（名稱已被占用）。不提供那份完整的較新暫存檔：從使用者的角度，那次存檔從未完成，就像當機時遺失的編輯。否決：用對話框列出每個殘留檔（為幾乎都是重複的檔案新增 UI）；復原最新的檔案（會把中斷的重新命名變成已完成，F-3 從不這樣做）；刪除重複的檔案（使用者的資料，絕不默默刪除）。

**D4. 告訴使用者復原了什麼。** `DocumentWorkspaceService.take_recovered_document_names() -> list[str]` 回傳並清空 D3 的名稱。`BrailleFrame._load_workspace_documents_at_startup` 在 `_review_invalid_workspace_files` 之後呼叫它；若不是空的，呼叫 `self.show_info(_("DotExpress was interrupted ...").format(names="\n".join(names)), _("Documents Recovered"))`（字串見下）。接著照舊執行 `_ensure_open_document_exists` 與更新標題。用訊息框，是因為主視窗沒有狀態列，而 NVDA 會完整讀出訊息框（見現況）。用資訊圖示：現在沒有任何問題（Decided by orchestrator with the recommended default; user may override before merge）。

**D5. 其他的暫存檔名與殘留不變。** `PackageFiles.temporary_path` 保留 `NamedTemporaryFile`（F 審查 M-3／M-4 仍是後續）。啟動時從不刪除 `.tmp`、從不把它列為無效、也從不提議刪除它。

### 原子寫入

**D6. 文字處理程式。** `save_preprocessing_script` 照舊驗證、照舊建立資料夾，然後呼叫 `write_text_atomically(destination, lambda stream: stream.write(source), encoding="utf-8", newline="")`。位元組不變（不轉換換行，和現在的 `NamedTemporaryFile(newline="")` 相同）。好處：取代前 `fsync`、任何失敗都不留 `.tmp`、POSIX 上為 `0o666 & ~umask`。若沒有其他地方使用，移除 `tempfile` 與 `os` 的 import。可見的改變：唯讀的 `preprocessing.py` 現在得到 `[Errno 13] Permission denied: '<程式檔>'`（F-3 D3 的判定），而不是 `[WinError 5] ...: '<tmp>' -> '<程式檔>'`，包在既有的 `Unable to save text processing script: {error}` 裡。

**D7. 字典檔。** 在 `dictionaries/manager.py`：

- `ensure_default_dictionary` 與 `create_dictionary` 以 `write_text_atomically(path, write_header, encoding="utf-8", newline="")` 寫表頭，`write_header(stream)` 為 `csv.writer(stream).writerow(DEFAULT_HEADER)`。位元組相同（`text,braille,type\r\n`）。既有的存在檢查留在原處。
- `import_dictionary` 與 `export_dictionary` 以 `write_bytes_atomically(destination, lambda stream: _copy_file_into(source, stream))` 複製，`_copy_file_into` 以 `open(source, "rb")` 開啟來源並呼叫 `shutil.copyfileobj`。位元組與 `shutil.copyfile` 相同。開啟或讀取來源的錯誤在 callback 內拋出，所以不會安裝，暫存檔也會被移除。來源不存在或被鎖住時的錯誤文字，是和以前相同的 `OSError`。
- 既有的匯出目的檔（使用者已在檔案對話框中確認覆寫）只在複製完成並同步到磁碟後才被取代。唯讀的目的檔得到 `[Errno 13] Permission denied: '<目的檔>'`，與現在 `copyfile` 給的文字相同。把字典匯出到它自己的檔案時，`copyfile` 會以 `SameFileError` 拒絕；現在會用相同的位元組重寫它。F-8a 審查後的修正（2026-10-10，M-5）：目的地是資料夾時，`export_dictionary` 先檢查，拋出就地寫入會拋出的錯誤（Windows 是 `[Errno 13] Permission denied: '<目的地>'`，與 `copyfile` 相同；其他平台是 `IsADirectoryError`），與 D8 的 `write_export_text` 一致，而不是以「取代失敗」結束、訊息中出現暫存檔名。

**D8. 匯出 BRL 與 HTML。** `export_document_brl` 保留 `mkdir(parents=True, exist_ok=True)`，改以 `write_text_atomically(destination_path, lambda stream: stream.write(document.braille or ""), encoding="utf-8", newline=None)` 寫入。`_write_html` 保留「先轉成 HTML」，再以同樣方式寫入結果。`newline=None` 讓位元組與現在的 CRLF 完全相同（見現況）。BRL 路徑也涵蓋 Ctrl+E 與全部匯出。匯出失敗（任何例外，F-7 D6 的訊息不變）時，既有檔案逐位元組不變，也不會建立檔案。`_write_dep` 已是原子寫入。

**D9. `config.json` 以原子方式寫入。** `ConfigStore._save` 照舊建立 `data`、保留 `os.makedirs`，改以 `write_text_atomically(path, lambda stream: json.dump(data, stream, ensure_ascii=False, indent=2), encoding="utf-8", newline=None)` 寫入。`newline=None` 保留現在的 CRLF 位元組。錯誤仍然記進 log 並吞掉。唯讀的 `config.json` 仍以 `[Errno 13]` 失敗（記進 log）；隱藏的會被取代並失去該屬性（F-3 D11）。

**D10. `ConfigStore._load` 接受 BOM，並拒絕非物件的內容。**

- 以 `encoding="utf-8-sig"` 讀檔，和 F-2 讓所有字典讀取者做的一樣。有 UTF-8 BOM 的檔案正常讀取。沒有 BOM 時完全不變。
- 解析出來不是 `dict` 的值視同解析錯誤：和現在一樣記一則 warning（簽名寫出型別，例如 `ValueError: config.json does not hold a JSON object (list)`），回傳預設值。`config.json` 是 `null` 或陣列時，程式也能啟動。
- 除了 `FileNotFoundError` 之外的所有失敗，`_load` 都回傳一個空的 `_UnreadableConfig`，而不是普通的 `{}`。它是私有的 `dict` 子類別，只有一個屬性 `error`。getter 看到的仍是空 dict，和現在一樣。

**D11. 變更設定時，絕不默默丟掉不能用的 `config.json`。** setter 會把 `_load` 回傳的 dict 繼續傳下去（`data[...] = ...; self._save(data)` 仍是同一個物件），所以 `_save` 看得到載入是否失敗：

- `error` 是 `OSError`（檔案存在但讀不到，例如被鎖住或被拒絕）：`_save` 不寫入。每種不同的錯誤記一次 `WARNING`：`Config file %s was not saved because it could not be read`。檔案保留使用者的設定。變更只在這次執行中生效（程式的狀態已經有它）。
- 其他任何 `error`（讀得到，但不是能用的 JSON）：`_save` 先把目前的位元組複製到同資料夾的 `config.json.bak`（`write_bytes_atomically`，取代較舊的 `.bak`），再寫入新檔。若複製失敗，`_save` 不寫入，並記錄錯誤（`ERROR`，和現在的存檔失敗相同）。
- 沒有錯誤：不變。

沒有 UI 也沒有字串：設定檔不是程式會顯示的東西。程式從不讀 `.bak`（Decided by orchestrator with the recommended default; user may override before merge）。否決：損壞的載入之後拒絕所有存檔（使用者就再也無法變更設定）；每次事故一份帶時間戳記的備份（檔案越積越多）。

### U+0000

**D12. 文件進入程式的地方，U+0000 換成 U+FFFD（U1）。** `documents/workspace.py` 新增：

```python
def replace_nul_characters(text: str) -> tuple[str, int]:
    """Replace each U+0000 with U+FFFD; return the text and how many were replaced (F-8).

    The Windows Edit control ends its text at U+0000, so a document shown with one
    would be saved without everything after it.
    """
```

乾淨的文字回傳 `(text, 0)`，是同一個物件。`_displayable(document) -> tuple[Document, int]` 對文字套用它，點字不是 `None` 時也套用，並把數量相加。

`DocumentWorkspaceService` 在包或匯入進入 controller 的每個地方套用它：

| 入口 | controller 收到 | 存檔記錄（F-5） | 待提示數量 |
| --- | --- | --- | --- |
| `load_documents`（啟動，含 D3 復原的文件） | 取代後的文件 | **讀到的原樣**（含 U+0000） | 數量 > 0 的每份文件都設定 |
| `delete_all_documents` 失敗後重新載入 | 取代後的文件 | 讀到的原樣 | 只保留原本仍待提示的名稱 |
| `import_files` | 取代後的文件 | 寫入的內容 | 已存檔且數量 > 0 的每份文件都設定 |

- **載入：記錄保留磁碟上的內容。** F-5 D1 規定記錄是「寫入或載入的確切內容」。編輯框於是顯示取代後的文字，和記錄不同，所以這份文件第一次存檔就會寫入。之後包裡是 U+FFFD，下次啟動什麼都不顯示。從未開啟的文件在磁碟上保留 U+0000，沒有害處：每次載入都會再取代一次，沒有使用者的動作就不會寫入。否決：啟動時改寫包（使用者沒要求的寫入，遇到唯讀或被鎖住的包會失敗）。
- **匯入：存進去的就是取代後的文字。** 匯入本來就要寫一份新包，而 U1 把取代放在入口。
- 待提示數量（`self._nul_pending: dict[str, int]`）跟著文件走：`rename_document` 把它移到新名稱，`delete_document` 移除它，完成的全部刪除清空它。
- `take_replaced_character_count(name: str) -> int` 回傳數量並移除它（沒有則為 0）。
- 不含 U+0000 的文字完全不變：同樣的物件、同樣的記錄、沒有訊息。
- `prepare_document_for_save` 與 `_encodable`（F-5 D4）不取代 U+0000。D12 之後沒有任何路徑能把它帶到存檔（見現況）；若在那裡取代，從未開啟的文件會被當成已存檔，而它的包仍含 U+0000。

**D13. 開啟這種文件時的提示（U1）。** 在 `BrailleFrame._open_document_by_name` 的最後（編輯框、清單、標題、雙視窗都更新之後）：`count = self._workspace_service.take_replaced_character_count(document.name)`。若 `count` 為正：`self.show_warning(_('Some characters in document "{name}" ...').format(name=document.name, count=count, mark="\ufffd"), _("Characters Replaced"))`。

- 時機：這次執行中使用者第一次看到這份文件的時候。涵蓋啟動（第一份文件）、開啟、Ctrl+Tab、只匯入一份文件（會開啟它），以及刪除後開啟的文件。每份文件每次執行只提示一次，來回切換不會重複。
- 為什麼用訊息框：主視窗沒有狀態列，訊息框出現時 NVDA 會讀出（標題、內文、F-7 翻譯過的「確定」）。按「確定」後，焦點回到呼叫端指定的地方（`on_open_document` 與 `_open_adjacent_document` 照舊把焦點放在原文編輯框）。
- 警告圖示：文件的文字已和它的檔案不同，使用者應該看一下（Decided by orchestrator with the recommended default; user may override before merge）。
- 內文除了字形，還用文字寫出「替代字元」，因為螢幕報讀器不一定會念 U+FFFD（手動項目 83）。第二段說明保留它們的後果：liblouis 會把 U+FFFD 寫成跳脫碼（`\xfffd`，F-7 實測）。
- 否決：啟動時與匯入後各顯示一次總表（從未開啟的文件每次啟動都會再出現）；狀態列（NVDA 不會報讀）；為只匯出、從未開啟的文件提示（它們以 U+FFFD 寫出；見風險）。

**D14. 其他地方都不處理 U+0000。** 編輯框的讀取（`_editor_text`）、貼上、轉換與存檔路徑維持原樣：編輯框不可能含 U+0000（見現況）。F-5 落單 surrogate 的規則和 D12 一致：都用 U+FFFD，都保留位置。兩者有一處刻意不同：落單 surrogate 是看不見的剪貼簿殘渣，默默取代（F-5 D5）；U+0000 來自使用者的檔案，使用者決定要被告知（U1）。

**D15. 翻譯檔。** 四個新 msgid，都在 `gui.py`：D4 兩個、D13 兩個。照 F-6 D11 重新產生：`scripts\generate-pot.bat`、`POT-Creation-Date` 固定為 `2026-10-10 12:00+0800`、`msgmerge --update --backup=none`、填入四個 msgstr、移除任何 `fuzzy` 標記、`msgfmt --check -o ...dotexpress.mo ...dotexpress.po`。`msgfmt --check --statistics` 必須是 368 個已翻譯、0 fuzzy、0 未翻譯。含 `{name}`、`{count}`、`{mark}`、`{names}` 的訊息會得到 `#, python-brace-format`。確認 `msgmerge` 沒有把 `Documents Recovered` 誤配到 `Document` 開頭的標題，也沒有把長訊息誤配到其他含 `{name}` 的訊息。

## 各路徑改前與改後的行為

| 路徑 | 改前 | 改後 |
| --- | --- | --- |
| 磁碟上有被保留的無效 `bad.dep` 時新增 `bad` | `bad.dep` 被空文件取代 | `文件「bad」已存在。`；名稱對話框再次出現；`bad.dep` 不變 |
| 重新命名為 `bad`（同上） | `bad.dep` 被取代；舊包消失 | 同樣的訊息；磁碟上什麼都不變 |
| 重新命名，詢問名稱之後目標處出現第三個檔案（競態） | 被取代 | `儲存文件失敗：[Errno 17] File exists: '...\bad.dep'`；舊包放回去，沒有 `.tmp` |
| 匯入 `bad.txt`（同上） | `bad.dep` 被取代 | 匯入問題：`bad.txt: Document "bad" already exists.`；`bad.dep` 不變 |
| 啟動時只有一份被保留的無效 `new.dep` | `new.dep` 被空的 `new` 取代 | 建立並開啟 `new (2)`；`new.dep` 不變 |
| 重新命名中當機後啟動（沒有 `.dep`，兩個 `.tmp`） | 文件不見；沒有任何提示 | 文件以舊名稱回來；「已復原文件」訊息框；另一個 `.tmp` 留著 |
| 啟動時有已完成重新命名留下的舊包 | 無 | 相同（清單中有相同內容） |
| 啟動時包旁邊有存檔留下的 `.tmp` | 無 | 相同 |
| 啟動時有無效或空的 `.tmp` | 無 | 相同 |
| 文字處理「套用」 | 原子寫入但沒有 `fsync`；寫入錯誤後可能留下 `.tmp` | 原子寫入並 `fsync`；不留東西；位元組相同；唯讀：`[Errno 13]` 文字 |
| 建立預設字典、新增字典 | 就地寫入 | 原子寫入；位元組相同 |
| 匯入字典 | `copyfile`；失敗時留下半個檔案 | 原子複製；失敗時什麼都沒有 |
| 匯出字典覆寫既有檔案 | 先截斷再複製；失敗時留下半個檔案 | 複製完成前保留舊檔 |
| 匯出 BRL／HTML／全部匯出／Ctrl+E，成功 | CRLF 檔案 | 位元組相同 |
| 同上，writer 在覆寫既有檔案時失敗 | **舊檔變成空檔或半個檔案** | 舊檔逐位元組不變；沒有 `.tmp`；訊息或摘要相同 |
| 同上，目的檔被另一個允許寫入共用的程式開著 | 可能在對方開著時被改寫 | `[WinError 5]` 的失敗訊息；保留舊檔（見風險、O6） |
| 變更設定，正常的 `config.json` | 就地重寫（CRLF） | 原子寫入；位元組相同 |
| `config.json` 有 UTF-8 BOM | 預設值；下次變更把檔案清掉 | 正常讀取；下次變更寫成沒有 BOM |
| `config.json` 是 `null` 或陣列 | 程式無法啟動（沒有訊息） | 以預設值啟動（一則 warning）；下次變更前先留 `.bak` |
| `config.json` 被截斷或不是 UTF-8 | 預設值；下次變更把它清掉 | 預設值；下次變更前先留 `.bak` |
| `config.json` 讀不到（被鎖住、被拒絕） | 預設值；下次變更把它換成一個值 | 預設值；變更不寫入（`config.log` 中有 warning） |
| 開啟包中曾含 U+0000 的文件 | 編輯框只顯示到第一個 U+0000；**下次存檔寫入截斷的文字** | 編輯框以 U+FFFD 顯示全文；「已取代字元」訊息框一次；下次存檔寫入含 U+FFFD 的全文 |
| 匯入含 U+0000 的 `.txt`／`.pdf`／`.dep` | 以 U+0000 存檔；開啟時被截斷 | 以 U+FFFD 存檔；第一次開啟時顯示訊息框 |
| 匯出從未開啟、含 U+0000 的文件 | 匯出／轉換中有 U+0000 | 匯出／轉換中為 U+FFFD |
| 貼上含 U+0000 的文字 | 停在 U+0000（剪貼簿的規則） | 相同 |
| 不含 U+0000 的文件，其他所有路徑 | - | 相同 |

## 各檔案的設計

### `client/documents/workspace.py`（4 個空白）

- `replace_nul_characters`、`_displayable`（D12）。
- `_read_package(path, package_name) -> Document`：目前 `load_document_package` 在副檔名檢查之後的本體；`load_document_package` 以 `normalize_document_name(path.stem)` 呼叫它。
- `_INTERRUPTED_PACKAGE`（編譯好的 pattern）與 `recover_interrupted_packages`（D3），docstring 寫明「從不刪除、從不取代」。
- `move_document_package`：在安裝區塊開頭檢查 `files.exists(new_path)`（D1）。docstring：「A file already at ``new_path`` (a package that is not listed) raises ``FileExistsError``; the old package is put back.」
- `export_document_brl`：`write_text_atomically`（D8）；從 `shared.atomic_write` import。

### `client/documents/workspace_service.py`（4 個空白）

- `package_name_taken`、`free_document_name`（D1、D2）；`create_document` 的存在檢查（D1）；`import_files` 的 `existing_names`（D1）、`_displayable` 與待提示數量（D12）。
- `load_documents`：`load_workspace_documents`，然後 `recover_interrupted_packages`，再以 `_displayable` 給 controller、以原樣給 `_reset_saved`，並設定待提示數量。回傳值不變（`list[Path]`）。
- `take_recovered_document_names`、`take_replaced_character_count`（D4、D12）；`rename_document`、`delete_document` 與 `delete_all_documents` 維護 `_nul_pending`（D12）。
- 模組 docstring：D1、D3、D12 各一句。

### `client/documents/formats.py`（4 個空白）

`_write_html` 在轉換之後以 `write_text_atomically(..., newline=None)` 寫入（D8）。

### `client/gui.py`（tab）

- `_prompt_for_document_name`：磁碟檢查（D1）。
- `_create_default_document`：`free_document_name`（D2）。
- `_load_workspace_documents_at_startup`：復原提示（D4）。
- `_open_document_by_name`：U+0000 提示（D13）。
- 四個 msgid（D15）。

### `client/conversion/preprocessing/user_script.py`（4 個空白）

`save_preprocessing_script`（D6）。

### `client/dictionaries/manager.py`（4 個空白）

D7：`write_header`、`_copy_file_into`、四個寫入者；`shutil` 保留給 `copyfileobj`。

### `client/config.py`（4 個空白）

D9–D11：`_UnreadableConfig`、`_load`、`_save`、`_backup_unreadable(path)`；`ConfigStore` 的 docstring 各加一句。

### `client/locales/`

`dotexpress.pot`、`zh_TW/LC_MESSAGES/dotexpress.po`、`zh_TW/LC_MESSAGES/dotexpress.mo`（D15）。

### 不修改

`shared/atomic_write.py`（兩種寫入都已存在；`newline=None` 本來就接受）、`dialog.py`、`documents/controller.py`、`documents/export_coordinator.py`（它的訊息已涵蓋所有失敗，F-7 D6）、`ui/`、除了 `user_script.py` 以外的 `conversion/`、`dictionaries/entries.py`、`dual_view/`、`client/braille/`、包的格式、兩個 fixture。

## 維持不變的部分

- 每次成功寫入的位元組：包、字典檔、程式檔、`config.json`（CRLF）、BRL 與 HTML 匯出（CRLF）。
- 所有既有的訊息、標題與按鈕。F-5 的存檔比對與關閉對話框，F-7 的匯出回報。
- 磁碟上沒有不在清單中的 `.dep`、也沒有可復原的中斷包時，啟動、新增、重新命名與匯入。
- 不含 U+0000 的文件：編輯框顯示的、存檔與匯出的內容都不變，也沒有訊息。
- 程式從不刪除暫存檔。
- 兩個 fixture 的 sha256（`translation_golden.json` `e67d95a1...`、`dictionary_entries_trace.json` `f493da52...`）。

## 使用者可見字串

新 msgid（364 -> 368），全部在 `gui.py`：

| msgid | msgstr（zh_TW） | 位置 |
| --- | --- | --- |
| `Characters Replaced` | `已取代字元` | U+0000 訊息框的標題（D13） |
| `Some characters in document "{name}" cannot be shown ({count} in all). Each one has been replaced with the replacement character {mark}, so the text after it is kept.\n\nDelete or change these {mark} characters before converting. Otherwise each one appears in the braille as an escape code.` | `文件「{name}」中有 {count} 個無法顯示的字元，已全部以替代字元 {mark} 標示，後面的文字都保留下來了。\n\n轉譯前請刪除或修改這些 {mark}，否則每一個都會在點字中變成一段跳脫碼。` | U+0000 訊息框的內文；`{mark}` 是 U+FFFD（D13） |
| `Documents Recovered` | `已復原文件` | 復原訊息框的標題（D4） |
| `DotExpress was interrupted while saving or renaming a document. These documents were recovered:\n\n{names}\n\nCheck that their content is what you expect.` | `DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\n{names}\n\n請確認內容是否正確。` | 復原訊息框的內文；每行一個名稱（D4） |

- msgid 維持 ASCII：字形經由 `{mark}` 帶入。英文避開複數，因為 `i18n` 沒有 `ngettext`；出貨的翻譯檔是 zh_TW（`LOCALE_LANGUAGES`），數量不需要複數形。
- 不變、直接沿用：`Document "{name}" already exists.`、`Error`、`Failed to save document: {error}`、匯入問題文字 `Document "{name}" already exists.`（目前不是 msgid，不變）、`Unable to save text processing script: {error}`、字典的訊息、`Failed to export document: {error}` 與全部匯出的摘要。

U+0000 訊息框的 zh-TW 內容（U+FFFD 以 `<U+FFFD>` 表示）：

```
已取代字元

文件「alpha」中有 3 個無法顯示的字元，已全部以替代字元 <U+FFFD> 標示，後面的文字都保留下來了。

轉譯前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。

[確定]
```

## 測試計畫

TDD：每一步的新測試先寫、並因所述的原因失敗，再由程式碼轉綠。測試檔保留原本的縮排（這裡提到的檔案都用 4 個空白）。測試只用暫存資料夾，絕不碰 `client/dictionary/`、`client/workspace/`、`client/config.json` 或 `client/log/`。

**log 隔離是必要的。** `recover_interrupted_packages` 在記 log 時綁定 `dotexpress.gui`；`config.py` 記到 `dotexpress.config`。每個可能讓 production code 記 log 的新測試模組，都要在 `setUpModule` 呼叫 `unittest.addModuleCleanup(isolate_file_logs(...))`（`tests/file_log_isolation.py`），log 斷言用 `assertLogs`。`test_gui_document_flows.py` 已隔離 `dotexpress.gui`；`test_config.py` 保留它自己的 `patch.object(config, "logger")` 做法。

**測試原始碼中的 U+0000 與 U+FFFD** 以腳本寫成 `"\x00"`、`"\ufffd"` 跳脫，並檢查檔案位元組，絕不透過 Edit／Write 工具輸入（HANDOFF 第 2 節）。

**`Mock` service 的測試架構**（`test_gui_document_flows.py` 的 `_make_frame`）設定 `package_name_taken.return_value = False`、`free_document_name.side_effect = lambda base: base`、`take_recovered_document_names.return_value = []`、`take_replaced_character_count.return_value = 0`；否則為真的 `Mock` 會讓名稱對話框無限循環或跳出訊息框。

**只在 Windows 執行的測試** 使用 `tests/windows_file_handles.py`（`hold_open`、`make_read_only`）與 `@unittest.skipUnless(os.name == "nt", ...)`。

### A. 原子寫入

`test_user_preprocessing_script.py`：

1. `test_save_installs_through_the_shared_atomic_writer`：`patch("shared.atomic_write.os.fsync", wraps=os.fsync)` 被呼叫一次，記錄到的 `os.replace` 來源符合 `\.preprocessing\.py\.[0-9a-f]{16}\.tmp`。紅燈：沒有 `fsync`，名稱是 8 個字元。
2. `test_write_error_leaves_no_temporary_file_and_keeps_the_script`：在寫入程式文字時拋出 `OSError(errno.ENOSPC)`（由 plan 選一個同時能打到目前 `NamedTemporaryFile` 的 stream 與 helper 的 stream 的注入點）；舊位元組保留；沒有 `.tmp`。紅燈：目前 `.tmp` 會留下（路徑在寫完後才記錄）。
3. 只在 Windows：`test_read_only_script_is_refused_with_the_in_place_verdict`：完全符合 `[Errno 13] Permission denied: '<程式檔>'`；沒有 `.tmp`。紅燈：`[WinError 5]`。
4. `test_save_uses_utf8_and_atomic_replace` 保留它的斷言；patch 的目標改為 `os.replace`（模組可能不再 import `os`）。位元組不變。

`test_dictionary_manager.py`：

5. `test_header_writers_install_through_a_synced_temporary_file`（subTest：`ensure_default_dictionary`、`create_dictionary`）：有呼叫 `os.fsync`；位元組 `text,braille,type\r\n`；沒有 `.tmp`。紅燈：沒有 `fsync`。
6. `test_import_copy_failure_leaves_no_dictionary`：把 `shutil.copyfileobj` patch 成寫一半後拋出 `OSError(errno.ENOSPC)`；`list_dictionary_names` 不變；沒有 `.tmp`。紅燈：留下半個 `.csv` 並被列出。
7. `test_export_failure_keeps_the_existing_destination`：目的檔內容 `b"OLD"`；同樣的注入；目的檔仍是 `b"OLD"`。紅燈：被截斷。
8. `test_export_copies_the_same_bytes`（BOM、CRLF、中日韓文字）：與來源逐位元組相同。目前就是綠燈（守護）。
9. 只在 Windows：`test_export_onto_a_destination_held_open_keeps_it`（`hold_open` share read+write）：`PermissionError` 且 `winerror == 5`；位元組不變。紅燈：目前在對方開著時複製成功。

`test_document_workspace.py`／`test_document_formats.py`（由 plan 選擇已經在測各 writer 的模組）：

10. `test_brl_export_failure_keeps_the_existing_file`：目的檔 `b"OLD GOOD EXPORT"`；點字含以腳本寫入的落單 surrogate，讓編碼在寫入途中失敗；位元組不變；沒有 `.tmp`。紅燈：`b""`（實測）。
11. `test_html_export_failure_keeps_the_existing_file`：把 `shared.atomic_write.os.replace` patch 成拋出例外；位元組不變。紅燈：目前沒有 `os.replace`，新檔會被寫入。
12. `test_exports_keep_their_crlf_bytes`（subTest：BRL、HTML）：含 `\r\n` 的確切位元組。目前就是綠燈（防止改成 `newline=""`）。

`test_config.py`：

13. `test_save_installs_through_a_synced_temporary_file`：每次存檔呼叫一次 `os.fsync`；沒有 `.tmp`。紅燈。
14. `test_save_failure_keeps_the_previous_file`：把 `json.dump` patch 成寫一部分文字後拋出例外；舊位元組不變；失敗被記錄（沿用既有做法）。紅燈：被截斷。
15. `test_saved_bytes_use_crlf_on_windows`（只在 Windows）：確切位元組。目前就是綠燈（守護）。

### B. `ConfigStore` 載入的強化（`test_config.py`）

1. `test_a_utf8_bom_is_read`：`b"\xef\xbb\xbf{...}"` 讀到存入的值；沒有 warning。紅燈。
2. `test_json_that_is_not_an_object_gives_defaults_and_one_warning`（subTest：`null`、`[1, 2]`、`"text"`、`3`）：getter 回傳預設值；一則 warning，訊息含路徑。紅燈：`AttributeError`。
3. `test_a_change_after_a_damaged_load_keeps_a_backup`（subTest：截斷的 JSON、cp950 位元組、`[1, 2]`）：`set_output_mode("ascii")` 之後，`config.json.bak` 是完全相同的舊位元組，`config.json` 有新設定。紅燈：沒有 `.bak`。
4. `test_a_second_backup_replaces_the_first`。紅燈。
5. `test_a_change_after_an_unreadable_load_does_not_write`：把 `open` patch 成只在讀取該路徑時拋出 `PermissionError`；`set_output_mode` 之後位元組不變、沒有 `.bak`、記一則 warning `was not saved because it could not be read`。紅燈：檔案被換成一個值。
6. `test_a_failed_backup_prevents_the_write`：寫 `.bak` 的 `write_bytes_atomically` 拋出例外；`config.json` 不變；記錄錯誤。紅燈。
7. `test_a_missing_file_is_created_without_backup` 與 `test_a_good_file_is_updated_without_backup`。目前就是綠燈（守護）。
8. `ConfigLoadFailureLoggingTest` 與位元組測試不改、維持綠燈。

### C. M-1（`test_document_workspace.py`、`test_workspace_service.py`、`test_gui_document_flows.py`）

1. Service：`test_create_document_refuses_a_package_that_is_not_listed`：保留無效的 `bad.dep`（`load_documents` 回傳了它）；`create_document(Document("bad", ...))` 拋出指名 `bad.dep` 的 `FileExistsError`；位元組不變；沒有加入。紅燈：被取代。
2. Service：`test_rename_onto_a_package_that_is_not_listed_keeps_both_files`（`move_document_package` 的防護）：`alpha` -> `bad`；`FileExistsError`；`alpha.dep` 與 `bad.dep` 逐位元組不變；沒有 `.tmp`；controller 不變。紅燈。
3. Workspace：`test_move_onto_an_existing_third_file_puts_the_old_package_back`，並確認透過 `CaseInsensitivePackageFiles` 的只改大小寫重新命名仍然成功（防止在移到旁邊之前就檢查）。紅燈／綠燈。
4. Service：`test_import_treats_packages_on_disk_as_existing`：匯入問題 `bad.txt: Document "bad" already exists.`；`bad.dep` 不變；其他檔案照常匯入。紅燈。
5. Service：`test_package_name_taken`（subTest：不存在、在清單中、不在清單中的檔案、資料夾、NTFS 上大小寫不同（只在 Windows）、`exclude_name` 忽略大小寫相等）。紅燈：方法不存在。
6. Service：`test_free_document_name`（subTest：沒被占用、磁碟上有 `new.dep` -> `new (2)`、有 `new.dep` 與 `new (2).dep` -> `new (3)`、清單中有 `new`）。紅燈。
7. GUI：`test_add_of_a_name_whose_package_is_on_disk_asks_again`：事件：名稱對話框、`message_box('Document "bad" already exists.', 'Error', OK | ICON_ERROR)`、預填 `bad` 的名稱對話框、取消；檔案清單不變。紅燈。
8. GUI：`test_rename_to_a_name_whose_package_is_on_disk_asks_again`。紅燈。
9. GUI：`test_case_only_rename_is_not_blocked_by_its_own_package`（只在 Windows，`Alpha` -> `alpha`）：改名成功。目前就是綠燈；守護 `exclude_name`。
10. GUI：`test_startup_with_only_a_kept_invalid_new_package_creates_new_2`：`new.dep` 不變；清單 `["new (2)"]`。紅燈。

### D. 復原

`test_document_workspace.py`：

1. `test_interrupted_rename_is_recovered_under_the_old_name`：照探針看到的樣子寫兩個 `.tmp`（旁邊那份以 `os.utime` 設成舊 mtime，staged 較新）；結果 `[alpha]`；`alpha.dep` 存在且是舊位元組；staged 的 `.tmp` 留著。紅燈：函式不存在。
2. `test_leftover_of_a_completed_rename_is_not_recovered`（清單中的 `gamma.dep` 內容相同）。紅燈（函式不存在），之後由規則 4 轉綠。
3. `test_leftover_save_next_to_its_package_is_not_recovered`。
4. `test_invalid_and_empty_temporary_files_are_ignored`（也含 `b"not a zip"`、零位元組檔）。
5. `test_name_held_by_an_unlisted_package_is_not_recovered`（保留的無效 `alpha.dep`，任何大小寫）。
6. `test_names_that_are_not_valid_document_names_are_ignored`（`.CON.dep.x.tmp`；`.a<b.dep.x.tmp` 在 Windows 上無法建立，plan 選用能存在的名稱）。
7. `test_member_names_must_match_the_temporary_file_name`。
8. `test_recovery_never_deletes_a_file`：記錄用的 `os.unlink`／`os.remove`／`Path.unlink` patch 沒有被呼叫。
9. 只在 Windows：`test_recovery_does_not_replace_a_file_created_meanwhile`：把磁碟檢查 patch 成看不到；`os.rename` 拋出 `FileExistsError`；既有檔案不變；`.tmp` 留著；一行 log（`assertLogs("dotexpress.gui", "ERROR")`）。
10. F-3 的 `test_load_workspace_documents_ignores_leftover_temporary_files` 不改、維持綠燈。

`test_workspace_service.py`：

11. `test_load_documents_recovers_and_reports_names_once`：controller 列出 `alpha`；`take_recovered_document_names()` 先是 `["alpha"]`，再來是 `[]`；記錄讓下一次未修改的存檔略過（F-5）。紅燈。
12. `test_delete_all_failure_reload_does_not_recover`。守護。

`test_gui_document_flows.py`（在暫存工作區用真的 service，和既有的啟動測試相同）：

13. `test_startup_reports_recovered_documents`：事件：若有則先是無效檔案對話框，接著 `message_box(<含 "alpha" 的復原文字>, "Documents Recovered", OK | ICON_INFORMATION, parent=frame)`，然後是標題。紅燈。
14. `test_startup_ignores_leftover_temporary_files` 不改、維持綠燈（沒有訊息）。

### E. U+0000

`test_document_workspace.py`：

1. `test_replace_nul_characters`（subTest：乾淨文字回傳同一個物件與 0；`"a\x00b"`；開頭、結尾、連續；前後是 CRLF）。紅燈。
2. `test_displayable_counts_text_and_braille_and_keeps_pending_braille`。紅燈。

`test_workspace_service.py`：

3. `test_load_replaces_nul_for_the_controller_and_keeps_the_record_as_read`：包的文字 `"a\x00b"`、點字 `"\u2801\x00"`；controller 是 U+FFFD；載入後包的位元組不變；`take_replaced_character_count("alpha") == 2`，之後為 0。紅燈。
4. `test_first_save_after_load_writes_the_replaced_text`：`save_open_document(text="a\ufffdb", braille="\u2801\ufffd")` 會寫入；之後包是 U+FFFD，載入時數量為 0。紅燈（改之前載入仍把 U+0000 交給 controller）。
5. `test_unopened_document_keeps_its_package_and_count`。紅燈。
6. `test_import_saves_the_replaced_text_and_counts_it`（含 NUL 位元組的 `.txt`、含 NUL 的 `.dep`）。紅燈。
7. `test_pending_count_follows_rename_and_is_dropped_by_delete`。紅燈。
8. `test_delete_all_failure_reload_keeps_only_pending_counts`。紅燈。
9. `test_text_without_nul_is_unchanged`（同樣的物件、記錄、沒有數量）。守護。

`test_gui_document_flows.py`：

10. `test_opening_a_document_with_nul_shows_the_notice_once`：開啟 `alpha` -> 在編輯框已是取代後的文字之後，一次 `message_box(<含 "alpha"、2、U+FFFD 的文字>, "Characters Replaced", OK | ICON_WARNING, parent=frame)`；開啟 `beta`、再開 `alpha` -> 沒有第二次。紅燈。
11. `test_startup_opens_the_first_document_and_shows_its_notice`。紅燈。
12. `test_single_import_with_nul_shows_the_notice`：順序：先是提示（來自開啟），然後是匯入問題對話框（若有）。紅燈。
13. `test_editor_receives_the_full_text`：`input_txt.SetValue` 以 `"a\ufffdb tail"` 呼叫。紅燈。

### F. 翻譯檔（`test_i18n.py`）

1. `test_f8_messages_are_translated`：四個 msgid 都在編譯後的翻譯檔中，msgstr 如上（透過 `gettext` 讀 `dotexpress.mo` 比對），格式化時接受 `name`、`count`、`mark`、`names`。紅燈：不存在。

### 數量

新測試：A 15、B 7、C 10、D 13、E 13、F 1，約 59 個（subTest 算一個）。只在 Windows：A3、A9、A15、C5 的 NTFS subTest、C9、D9（5 個測試）。全部步驟之後預期：Windows 上 `Ran` = 1368 + 新測試，`FAILED (errors=1, skipped=7)`，只有 F-W6。確切數字由 plan 決定；紅綠燈的意圖有約束力。若拆分，F-8a 含 A、B、C；F-8b 含 D、E、F。

## 遷移步驟（每一步一個綠燈 commit，先紅燈）

F-8a：

1. `fix: never replace a document package that is not listed (F-8)`：D1、D2；測試計畫 C。
2. `fix: write the text-processing script and dictionary files atomically (F-8)`：D6、D7；A1–A9。
3. `fix: keep the previous export when an export fails (F-8)`：D8；A10–A12。
4. `fix: write config.json atomically and never discard an unusable one (F-8)`：D9–D11；A13–A15、B。

F-8b：

5. `fix: recover documents whose save or rename was interrupted (F-8)`：D3–D5 與測試計畫 D，加上兩個復原用 msgid 與翻譯檔重新產生（這兩個的 D15）。
6. `fix: replace U+0000 when documents are loaded or imported, and say so (F-8)`：D12–D14；測試計畫 E 與 F，加上另外兩個 msgid 與翻譯檔重新產生。

每個 commit 結尾加 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`，只 stage 明確的路徑。只有步驟 5、6 動到 `client/locales/`。

## 驗收條件

在 Windows 上從 `client/` 以 `$PY` 執行；在 worktree 中時照 F-3 plan Task 0 複製 runtime。

1. 完整套件：除了 F-W6 沒有任何 failure 或 error；`Ran` = 基準 + 新測試。
2. 焦點：`$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_document_formats tests.test_export_coordinator tests.test_user_preprocessing_script tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_config tests.test_gui_document_flows tests.test_i18n tests.test_wx_call_sites -v` 通過；只在 Windows 的測試有執行。
3. 翻譯檔：AST msgid 掃描得到 368；`msgfmt --check --statistics` 回報 368 個已翻譯、0 fuzzy、0 未翻譯；`git diff main -- client/locales` 只改到這四個條目與參照行。
4. 兩個 fixture 的 sha256 不變。
5. 使用者資料未被動到：在主 checkout 中，`client/dictionary/`、`client/workspace/`、`client/config.json` 與 `client/log/` 前後的 sha256 相同；在 worktree 中，都沒有被建立。
6. `git diff main --stat` 只動到「各檔案的設計」中的檔案、上面列出的測試檔，以及 spec、plan 與 history 檔。
7. 原始碼掃描（或 `grep`）在 `client/` 的 production code 中，`shared/atomic_write.py` 與 `dual_view/files.py` 以外，找不到寫入使用者資料的 `shutil.copyfile`、`Path.write_text` 或 `open(..., "w")`。
8. Mutation 檢查（plan）。每個 mutant 至少被一個測試抓到：
   - 名稱對話框沒有磁碟檢查；`package_name_taken` 忽略 `exclude_name`；`create_document` 沒有檢查；移動防護放在移到旁邊之前（弄壞只改大小寫的重新命名）或被移除；`import_files` 只用 controller 的名稱；`free_document_name` 一律回傳 `base`；
   - 復原：刪除被略過的候選者；用 `os.replace` 取代 `os.rename`；沒有內容重複規則；最新的優先；復原無效的封存檔；在全部刪除後的重新載入中復原；
   - 每個寫入者改回舊的呼叫（`copyfile`、`write_text`、`open("w")`、`NamedTemporaryFile`）；BRL、HTML 或 config 用 `newline=""`；
   - `_load` 不用 `utf-8-sig`；接受非 dict；`OSError` 的載入之後 `_save` 仍寫入；沒有 `.bak`；`.bak` 失敗仍寫入；
   - `replace_nul_characters` 不計點字；以取代後的文字建立記錄；每次開啟都提示；不提示；重新命名時數量沒有移動；在 `_encodable` 中取代 U+0000。
9. 下面的 packaged GUI 驗證，結果放在實作的 history 資料夾。

## Windows 驗證（packaged build）

照 F-7 建置：主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面，執行 `scripts\build-dotexpress.bat`；在 `PYZ-00.toc`／`Analysis-00.toc` 確認改過的模組來自受測的 checkout；把 exe 複製到 `D:\dxtest\N-f8\`（若拆分則為 `N-f8a`、`N-f8b`）。「改前」是 `D:\dxtest\N-f7\DotExpress.exe`。

每個項目在新的 `D:\dxtest\auto<項目>-f8` 資料夾執行，exe 複製進去；`dictionary\`、`workspace\`、`log\` 與 `config.json` 都在它旁邊。只結束 exe 位於該資料夾下的程序（`dx.kill_under`；`lock.py` 用 `taskkill /T`）。訊息框是 task dialog，透過 UIA 讀取（`f5gui.describe`）。腳本放在實作的 history 資料夾 `auto/`，不修改地重用 `docs/superpowers/history/2026-10-09-03-windows-verification/auto/`（`dx.py`、`docs.py`、`dicts.py`、`lock.py`）、F-5 的 `f5gui.py` 與 F-7 的 `f7gui.py`。測試工作區以腳本建立（用 `zipfile` 寫入成員；U+0000 與 U+FFFD 用跳脫）。pywinauto venv 是 `$SP\uia`（以 `py -3.13 -m venv` 與 `pip install pywinauto==0.6.9 psutil` 重建）。

項目接在 F-7 的 65 之後：

| # | 步驟 | F-8 之後的預期 | 改前（N-f7） |
| --- | --- | --- | --- |
| 66 | 工作區：有效的 `alpha.dep`、無效的 `bad.dep`。啟動；「保留無效檔案」。新增 `bad` | `錯誤` 訊息框 `文件「bad」已存在。` 與 `確定`；名稱對話框再次出現，預填 `bad`；Esc；`bad.dep` 的 sha256 不變 | 新增了 `bad`；`bad.dep` 被取代 |
| 67 | 同 66；把 `alpha` 重新命名為 `bad`；再把 `alpha` 重新命名為 `Alpha` | 第一次：同樣的訊息框，什麼都不變；第二次：改名成功（只改大小寫） | 第一次：`bad.dep` 被取代，`alpha.dep` 消失 |
| 68 | 同 66；匯入 `bad.txt` 與 `ok.txt` | 匯入問題列出 `bad.txt: Document "bad" already exists.`；`ok` 匯入；`bad.dep` 不變 | `bad.dep` 被取代 |
| 69 | 工作區只有無效的 `new.dep`；保留 | 清單中有 `new (2)` 並開啟；`new.dep` 不變 | 建立 `new`，`new.dep` 被取代 |
| 70 | 照重新命名中斷的樣子建立工作區（舊 mtime 的 `.alpha.dep.<8>.tmp`、staged 的 `.gamma.dep.<8>.tmp`、沒有 `.dep`）；啟動 | `已復原文件` 訊息框列出 `alpha`，資訊圖示，`確定`；清單 `alpha`，文字正確；`alpha.dep` 存在；`.gamma.dep.*.tmp` 仍在；重新啟動：沒有訊息框 | 清單空的，建立新的 `new` 文件，沒有訊息 |
| 71 | `gamma.dep` 加上內容相同、殘留的 `.alpha.dep.<8>.tmp`；啟動 | 沒有訊息框；清單 `gamma`；`.tmp` 未動 | 相同 |
| 72 | `alpha.dep` 加上文字較新、殘留的 `.alpha.dep.<16 hex>.tmp`；啟動 | 沒有訊息框；`alpha` 是包中的文字；`.tmp` 未動 | 相同 |
| 73 | `alpha.dep` 文字 `"first line\nsecond\x00 after\nthird"`，點字有一個 U+0000；`beta.dep` 乾淨；啟動 | `已取代字元` 訊息框，警告圖示，內文寫出 `alpha` 與 `2`，`確定`；原文編輯框（`WM_GETTEXT`）是含 U+FFFD 的全文；Ctrl+Tab 到 `beta` 再回來：沒有第二次；關閉；`alpha.dep` 含 U+FFFD 與 `third`；重新啟動：沒有訊息框 | 編輯框是 `first line\nsecond`；Ctrl+Tab 之後 `alpha.dep` 只剩 `first line\nsecond`（**資料遺失**） |
| 74 | 匯入含 NUL 位元組的 `.txt`（單一檔案） | 文件開啟，訊息框寫出它的名稱；包含 U+FFFD | 編輯框只顯示到 NUL；包含 U+0000 |
| 75 | 匯入該 `.txt` 與文字中有碼 0 的 `.pdf`（兩個檔案）；再各自開啟 | 匯入時沒有訊息框；每份文件第一次開啟時各一次 | 沒有訊息框；文字被截斷 |
| 76 | 把 `alpha` 匯出 BRL 到新檔；匯出 HTML；和 N-f7 對同一工作區的輸出比對 | 位元組相同（CRLF），資料夾中沒有 `.tmp` | 參照 |
| 77 | 匯出 BRL 覆寫既有的 `old.brl`，而它被 `lock.py` 開著（share read+write） | `匯出文件失敗：[WinError 5] ...`；`old.brl` 不變；沒有 `.tmp` | 匯出成功，在對方開著時改寫檔案 |
| 78 | 全部匯出 BRL 到一個 `beta.brl` 被開著（share read+write）的資料夾，覆寫：是 | 摘要列出 `beta` 失敗；寫入 `alpha.brl`；`beta.brl` 不變 | 全部寫入 |
| 79 | `config.json` = `null`；啟動 | 主視窗以預設值出現；變更字型大小（Ctrl+滾輪或設定）；`config.json.bak` = `null`；`config.json` 有字型大小 | 沒有主視窗；程序結束（記錄情形） |
| 80 | `config.json` 有 UTF-8 BOM、字型大小 20；啟動；在設定中變更寬度 | 啟動時字型大小 20；之後檔案兩個值都有，沒有 BOM，CRLF；沒有 `.bak` | 字型大小為預設；變更後只剩寬度 |
| 81 | `config.json` 被 `lock.py` 以 share **none** 開著；啟動；變更字型大小；解鎖；重新啟動 | 以預設值啟動；變更後檔案逐位元組不變；`log\config.log` 有 `was not saved because it could not be read`；重新啟動讀到舊值 | 檔案被換成只有字型大小（或記錄實際結果） |
| 82 | 字典管理：新增 `d1`；匯入有效的 CSV `d2`；把 `d1` 匯出覆寫既有檔案；文字處理：套用一個程式 | 字典檔與 N-f7 相同步驟的結果逐位元組相同；`dictionary\` 與匯出資料夾中沒有 `.tmp`；匯出目標被取代 | 參照 |

絕不碰真正的工作區；每個項目建立自己的。項目 81 只在自己的資料夾中以 share none 開著 `config.json`。

給使用者的手動項目（實作者把它們加到使用者的清單；agent 絕不代為勾選）：

- **83（NVDA）。** 在 F-8 build 的副本中，NVDA 執行時，分別開啟項目 73 與項目 70 的工作區。記錄 NVDA 對 `已取代字元` 訊息框（特別是它怎麼念替代字元）與 `已復原文件` 訊息框讀出的內容，以及按「確定」後焦點是否回到原文編輯框。
- **84（可選）。** 用項目 34 那個只剩幾 KB 的小 VHD：匯出一個大的 BRL 覆寫既有檔案；舊檔必須完整保留，訊息必須寫出磁碟已滿的錯誤。

## 風險

- **覆寫被其他程式開著的檔案時，匯出現在會失敗**（中，O6）。`os.replace` 拒絕任何被開著的目標，所以覆寫點字印表軟體或編輯器開著的檔案時，以前允許共用時會成功，現在以 `[WinError 5]` 失敗。會顯示訊息、保留舊檔，使用者關掉另一個程式再匯出即可。和 F-3 Q1 是同樣的取捨。
- **隱藏或唯讀的目標**（低，F-3 D11）。隱藏的匯出檔、字典檔、程式檔與 `config.json` 會被取代並失去該屬性；唯讀的照舊被拒。
- **匯出資料夾中的暫存檔**（低）。匯出時會在目標旁短暫建立 `.<名稱>.<16 hex>.tmp`（USB 隨身碟、網路磁碟也一樣）。監看資料夾的程式可能看得到它；通常匯出結束前它就被移除或改名。F-8a 審查後的修正（2026-10-10，M-4）：若掃描程式（例如防毒軟體）在 `os.replace` 當下開著暫存檔，匯出會失敗（`[WinError 32]`），舊檔保持完整，但暫存檔會留下，因為移除它也會失敗（`shared/atomic_write.py` 忽略這個錯誤，套件自 F-3 起就是如此）；使用者可以手動刪除。重試移除留作後續項目。
- **可以覆寫檔案、但不能建立檔案的資料夾**（很低；F 審查）。原子寫入需要在那裡建立暫存檔。
- **復原把使用者刻意改過名的文件放回舊名稱**（低）。只發生在重新命名被當機打斷時：文件以舊名稱回來，和失敗的重新命名一樣（F-3）。staged 的那份留在磁碟上。
- **被略過的殘留檔在之後的某次啟動被復原**（低；F-8b 規劃後新增，見「規劃後的修正（F-8b）」第 9 點）。重新命名中斷時的 staged 檔，在復原的文件被修改後會成為另一份文件回來；已完成的重新命名或中斷的存檔留下的殘留檔，在名稱空出來或內容變得獨一無二時會回來。不會遺失資料；訊息框會列出多出來的文件。
- **兩份內容相同的不同文件**（很低）。若中斷的文件與清單中另一份文件的文字和點字完全相同，就不復原（規則 4）；沒有遺失文字，只少了名稱。
- **不提供中斷存檔的較新文字**（低，D3）。等同當機時遺失的編輯；`.tmp` 留在磁碟上，可手動救回。
- **只匯出、從未開啟的文件以 U+FFFD 匯出，沒有提示**（低，D13）。
- **沒有 BOM 的 UTF-16 檔案產生大量 U+FFFD**（低）。每個 ASCII 字元後面都是 U+FFFD；提示中的數量讓編碼錯誤一目了然。偵測 UTF-16 不在範圍內。
- **`config.json` 一直被鎖住**（低，D11）。設定變更在這次執行中生效，但檔案能讀之前不會存檔；`config.log` 說明原因。
- **`config.json.bak` 存的是損壞的檔案**（設計如此）。程式從不讀它。
- **`config.json` 的執行緒競態**（不變，已知）：client-init 執行緒上的 `get_or_create_client_id`。

## 待決問題

沒有阻擋性的問題。U1 與 U2 是使用者的決定（2026-10-10）。

Decided by orchestrator with the recommended default; user may override before merge：

- **O1.** 拆成 F-8a（沒有字串）與 F-8b（提示與 4 個 msgid），依此順序（目標、遷移步驟）。
- **O2.** `new.dep` 在磁碟上但不在清單中時，預設文件使用 `new (2)`、`new (3)`……（D2）。
- **O3.** 啟動時自動復原中斷的包，並以一個資訊訊息框告知；從不刪除任何東西，重複的檔案留在磁碟上（D3、D4）。
- **O4.** `config.json`：損壞的檔案在第一次變更取代它之前，先複製成 `config.json.bak`；讀不到的檔案不會被覆寫；接受 BOM；非物件視同損壞（D10、D11）。
- **O5.** U+0000 的提示是警告訊息框，在每次執行中每份受影響的文件第一次開啟時顯示，不是啟動時的總表（D13）。
- **O6.** 匯出改為原子寫入，因此覆寫被其他程式開著的目標時會失敗，和 F-3 Q1 對包的處理相同（D8、風險）。
- **O7.** 不在 `_encodable`／`prepare_document_for_save` 中取代 U+0000（D12）。

F-8b 的 plan 提出（不阻擋）：被復原略過的殘留檔，之後的某次啟動可不可以被復原（「規劃後的修正（F-8b）」第 9 點）。F-8b 維持上面的 D3。

## 不在範圍內／後續項目

- **字典條目中的 U+0000。** Python 3.13 的 `csv` 會讀出 `a\x00b`（實測）；條目編輯器的文字欄會截斷它，按「確定」就存下截斷的條目。字典相關任務應在載入條目時做同樣的取代。
- **文字處理程式中的 U+0000。** 程式編輯框會截斷它；轉換時 `ast.parse` 已經會拒絕這種程式。
- **使用者的文字處理程式回傳 U+0000** 到點字輸出。
- **統一兩種暫存檔命名**（F 審查 M-3／M-4），以及清理殘留的 `.tmp`（需要使用者同意；未規劃）。
- **提供中斷存檔的較新文字。**
- **`dual_view/files.write_dual_view_html`**（程式自己的暫存頁面）。
- **UTF-16 文字匯入**（有 BOM：目前是匯入問題；沒有 BOM：大量 U+FFFD）。
- **`config.json` 在 UI 與 client-init 執行緒之間的讀改寫競態。**
- `task.md` 中的其他項目（F-9 到 F-12）。
