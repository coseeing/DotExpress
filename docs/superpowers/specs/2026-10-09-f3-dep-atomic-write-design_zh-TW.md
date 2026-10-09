# `.dep` 原子寫入（F-3）設計

## 目標

修正任務 F-3 修正文件 workspace 的兩個優先 2 缺陷：

1. **存檔時原地截斷 `.dep`（資料遺失）。** `save_document_package` 以 `zipfile.ZipFile(path, "w")` 開啟文件包，先截斷檔案，再逐一寫入成員。中途失敗會留下壞掉的文件包：當機或斷電、磁碟已滿、或文字中的 lone surrogate 造成 `UnicodeEncodeError`。下次啟動時 `load_workspace_documents` 把它列為無效，啟動對話框建議刪除它。每次切換文件都會存檔，所以這是 app 中暴露最頻繁的寫入端。來源：F 審查第 4 節與「剩餘缺陷清單」第一列（`docs/superpowers/history/2026-10-09-01-fix-data-loss/review_task.md`），以及 HANDOFF 4.4（`docs/superpowers/history/2026-10-09-02-handoff/HANDOFF.md`）。目前沒有任何測試釘住它。
2. **一般改名在刪不掉舊包時留下兩份文件包（資料不一致）。** 一般（非只改大小寫）改名先寫 `gamma.dep`，再 unlink `beta.dep`。unlink 失敗時兩份文件包都留在磁碟上，記憶體只有 `beta`；下次啟動兩份都會列出。來源：P1-3 已知缺陷 3（`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md`，「既有缺陷清單」）。由 `KNOWN BUG` 測試 `test_rename_unlink_failure_leaves_both_packages_and_state`（GUI）與 `test_rename_unlink_failure_propagates_and_leaves_both_packages`（service）釘住，並由 `test_regular_rename_does_not_use_package_files`（F-1 D6）守住。

本任務完成後：

- 每次寫 `.dep`（存檔、新增、匯入、預設文件、匯出為 DEP）都寫到同一資料夾中的新暫存檔，flush 到磁碟，再以 `os.replace` 安裝。任何失敗後，磁碟上的文件包與之前逐位元組相同（或仍不存在），且不留下暫存檔。
- 每次改名，不論一般或只改大小寫，都使用 F-1 的 `move_document_package`：先 stage 新包、把舊包移開、安裝新包，最後移除移開的檔案。任何一步失敗都只留下一份文件包（舊的），文件清單不變。
- 使用者不能寫入的文件包（Windows 唯讀屬性、POSIX 無寫入權限）不會被存檔或改名取代或移除：兩者都以 `[Errno 13] Permission denied: '<文件包>'` 失敗，也就是存檔今天已經給出的訊息。
- 存檔、新增、改名的 UI 邊界捕捉所有 `Exception`，不再只捕捉 `OSError`，顯示既有的 `Failed to save document: {error}` 訊息（F 審查 M-1）。匯入把任何存檔錯誤列為匯入問題。

沒有新的使用者可見字串；msgid 不變（353，集合相同）。F-W10（開著的 `.dep` 為唯讀或被鎖住時擋住改名與關閉）不在範圍內；本任務只改變哪些鎖定模式會觸發它（D12）。

## 規劃後更正（2026-10-09）

規劃（`docs/superpowers/plans/2026-10-09-f3-dep-atomic-write.md`，已在 scratch clone 上 dry run）沒有發現決策 D1-D13 有錯；以下記錄已決定的開放問題，以及計畫細化本規格之處。兩者不同時以本節為準。

1. **Q1 與 Q2 已決定**：由協調者採用建議的預設（2026-10-09）；使用者可在合併前推翻任一項。**Q1：接受。** 被另一個程式以任何共用模式開著的 `.dep` 現在會擋住存檔，以及每個先存檔的動作（包括關閉），直到那個程式釋放它。**Q2：拒絕。** 唯讀文件包不能改名，一般改名與只改大小寫皆然：`[Errno 13] Permission denied: '<文件包>'`，磁碟上不留下任何東西。
2. **複製 runtime 後的基線。** worktree 沒有 git 忽略的 liblouis runtime、MathCAT 與 submodule 的 `configure.ac`，所以基線是 `Ran 1138`、`errors=2`、`skipped=7`（見「現況」）。計畫的 Task 0 從主 checkout 複製這些建置產物（submodule commit 相同，`2aa5f84b`；`louis_helper.py` 與 `vendor/nvda/liblouis/runtime/louis_helper.py` 逐位元組相同）；之後 worktree 的基線與主 checkout 相同（`Ran 1143`、`FAILED (failures=1, errors=1, skipped=5)`），`git status` 仍是空的，驗收條件 1 中 `test_liblouis_runtime` 的錯誤也不會出現。
3. **新增 37 個測試，不是 34 個。** 多出：`test_rename_of_a_package_held_open_by_another_program`（service，僅 Windows，四種共用模式：不共用刪除時改名以 `[WinError 32]` 失敗且只留下舊包，F-3 之前則兩份都留下；共用刪除時改名完成）、`test_regular_rename_ignores_a_failure_to_remove_the_moved_aside_package`（service）與 `test_startup_ignores_leftover_temporary_files`（GUI，D13 在啟動對話框的層級）。A11 與 B7 以 subtest 涵蓋讀取、讀寫、讀取加刪除、讀寫加刪除四種共用模式。僅 Windows 的測試：8 個。最後一步之後預期 `Ran 1180`、`FAILED (failures=1, errors=1, skipped=7)`（未複製 runtime 時 1175）；合併 `main` 的 `4953772`（P2-5）之後 `Ran 1248`、`FAILED (errors=1, skipped=7)`，唯一的錯誤是 F-W6。取代「數量」中的「預期：worktree `Ran 1172`（主 checkout 1177）」。
4. **六個 commit。** 第一個 commit 只含測試：在目前程式上就會通過的五個測試（B6、B9、B10、B11 與 GUI 啟動測試）；之後是五個遷移步驟，每步先紅後綠。commit 標題以 `(F-3)` 結尾。
5. **測試 helper。** `client/tests/windows_file_handles.py` 另外提供 `SHARE_MODES`（四種模式）、`make_read_only`（clean-up 只在檔案仍存在時清除屬性）、`make_hidden` 與 `is_hidden`；`hold_open` 回傳 `release` 函式，讓測試可以在檢查資料夾之前關閉 handle。
6. **匯入測試。** 讓兩份文件中的第二份（`beta` 之後的 `delta`）失敗，而不是 `beta`，這樣舊程式會顯示較嚴重的結果：`beta.dep` 已寫入卻從未加入清單。
7. **GUI 翻轉測試。** GUI 模組自己定義 `_FailingReplacePackageFiles(source_name=...)`；從 service 測試模組 import 會讓 `unittest` 把那些測試收集兩次。
8. **驗收條件 4 與 8** 與 merge base（`git merge-base main HEAD`）比較，而不是 `main`，因為 `main` 已包含 P2-5。條件 4 的「沒有新的 `_(`／`N_(` 字面值」只針對正式程式碼；測試以既有 msgid 呼叫 `gui._()`。
9. **Windows 驗證。** exe 放到 `D:\dxtest\N-f3\DotExpress.exe`（協調者指定），不是 `D:\dxtest\F3\`。不複製也不修改 2026-10-09-03 的腳本：包裝程式 `rerun.py` 在記憶體中替換 exe 與工作資料夾後執行第 18、19、21 項（19 與 21 從第 18 項資料夾的複本開始），`item20b.py` 本來就接受參數，第 30-33 項是新腳本；全部放在 `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/`。每一項在新的 `D:\dxtest\auto<N>-f3` 資料夾執行。建置時把主 checkout 的 `client\.venv` 放到 `PATH` 前面（worktree 沒有 venv）；計畫中的程式在 scratch clone 上建置成功，打包的是該 clone 自己的模組。第 34 項仍是人工、可選。

## 現況（2026-10-09 於 `fix/f3-dep-atomic-write`、HEAD `d4a7aa1` 驗證，Windows 11 26200，NTFS）

`$PY` 為 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`（Python 3.13.15）。`$SP` 為 session scratchpad；下文使用的原型在 `$SP\f3spec\`（`probe.py`、`probe2.py`、`probe3.py`、`lock.py`）。

基準：在 worktree 中 `cd client && $PY -m unittest discover -s tests` 得到 `Ran 1138 tests`、`FAILED (failures=1, errors=2, skipped=7)`。失敗為已知的 P2-5 案例 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`；錯誤為 F-W6（`test_dictionary_name_prompt ... test_case_only_rename_still_renames`，NTFS 上的 `FileExistsError`）與 `test_liblouis_runtime` 的 `setUpClass`（worktree 沒有產生的 `braille/louis_helper.py`）。在主 checkout 中同一套件得到 `Ran 1143`、`failures=1`、`errors=1`、`skipped=5`。相關模組（`tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller`）得到 `Ran 264`、`OK (skipped=4)`（四個僅限 POSIX 的權限測試）。

### 所有 `.dep` 寫入

| 呼叫端 | 路徑 | 寫入方式 | 目前失敗時 |
| --- | --- | --- | --- |
| `DocumentWorkspaceService.save_open_document`（`documents/workspace_service.py:78-85`） | 每個文件動作之前與關閉之前的存檔 | 先 `controller.replace_document`（先記憶體，為既定契約），再 `save_document_package(package_path(開啟中的名稱))` | 文件包被截斷 |
| `create_document`（`:87-89`） | 新增、預設的 `new` 文件 | `save_document_package`，再 `controller.add_document` | 部分寫入的新文件包（只有在原本已有檔案時才有影響：啟動時選擇保留的無效包） |
| `import_files`（`:91-108`） | 匯入 | 每份文件 `save_document_package`；`except OSError` 變成 `BatchIssue` | 部分寫入的新文件包；非 `OSError` 逃出並跳過 `controller.add_documents`，已寫入的文件不會加入清單 |
| `rename_document`，一般（`:124-128`） | 把 `beta` 改名為 `gamma` | `save_document_package(gamma.dep)`，再 `beta.dep.unlink()` | 寫入失敗：部分的 `gamma.dep`；unlink 失敗：兩份文件包（缺陷 3） |
| `rename_document`，只改大小寫（`:116-123`） | 把 `Alpha` 改名為 `alpha` | `move_document_package`（F-1） | 安全；見下 |
| `PackageFiles.write`（`documents/workspace.py:79-80`） | `move_document_package` 的 staged 檔 | `save_document_package(staged 路徑)`；沒有 `fsync` | staged 檔被移除，舊包保留 |
| `formats._write_dep`（`documents/formats.py:89-94`） | 匯出為 DEP 到使用者選的路徑 | `save_document_package(path, include_pending_metadata=False)` | 匯出檔被截斷（使用者已確認覆寫） |

`save_document_package`（`documents/workspace.py:54-70`）正規化名稱、建立資料夾，並以 `ZIP_DEFLATED` 寫入 `<name>.txt`、`<name>.brl`，點字待轉換時另寫 `<name>.meta.json`。`zipfile` 以 mode `"w"` 開啟路徑時用的是 `open(path, "w+b")`，在 Windows 上即 `CREATE_ALWAYS`。

`move_document_package`（`:101-156`，F-1 D4 與 M-3 修正）把新包 stage 到 `PackageFiles.temporary_path`（`tempfile.NamedTemporaryFile(prefix=".<name>.", suffix=".tmp", delete=False)`，建好立即關閉），把舊包移到另一個同類檔案，複製權限位元（POSIX），以 `os.replace` 安裝，最後移除移開的檔案並忽略該步的失敗。

`load_workspace_documents`（`:221-231`）列出 `directory.glob("*.dep")`。以 `probe2.py` 確認：`.alpha.dep.0123456789abcdef.tmp` 與 `..alpha.dep.x.tmp.y.tmp` 不會被列出，也不會被列為無效。

### UI 邊界（`client/gui.py`，tab 縮排）

| Handler | 捕捉 | 訊息 |
| --- | --- | --- |
| `_save_open_document_with_feedback`（`:596-602`），用於開啟、Ctrl+Tab、新增、改名、刪除、全部刪除、匯入、匯出、全部匯出、Ctrl+E 之前，以及 `_on_close`（`:956-969`，回傳 `False` 時 veto） | `OSError` | `Failed to save document: {error}`（`儲存文件失敗：{error}`） |
| `_create_document`（`:617-635`） | `OSError` | 同上 |
| `on_rename_document`（`:741-767`，`except` 在 `:760`） | `OSError` | 同上 |
| `on_delete_document`（`:785`）、`delete_all_documents`（`workspace_service.py:142`） | `OSError` | `Failed to delete document: {error}` |

非 `OSError`（實際上是 `UnicodeEncodeError`）會逃出 wx handler：什麼都不顯示；在 `_on_close` 中事件既不 veto 也不 skip，所以視窗保持開啟、沒有任何訊息。

### Windows NTFS 實測（原型，真實檔案）

由第二個程序（`lock.py`）或同一程序（`probe2.py`、`probe3.py`）以 `CreateFileW(GENERIC_READ, share)` 開著目標。「舊」為目前程式碼，「新」為下文設計。

| 目標狀態 | `open(path, "w+b")`（舊存檔） | `os.replace(tmp, target)`（新存檔） | `os.replace(target, aside)`（移開） | `unlink(target)`（舊的一般改名） | `os.access(W_OK)` |
| --- | --- | --- | --- | --- | --- |
| 唯讀屬性 | `[Errno 13] Permission denied: '<target>'` | `[WinError 5]` | 成功 | `[WinError 5]` | `False` |
| 開著，共用讀取 | `[Errno 13]` | `[WinError 5] ...: '<tmp>' -> '<target>'` | `[WinError 32] ...: '<target>' -> '<aside>'` | `[WinError 32]` | `True` |
| 開著，共用讀寫 | **成功**（在讀取者底下重寫） | `[WinError 5]` | `[WinError 32]` | `[WinError 32]` | `True` |
| 開著，共用讀寫刪除 | 成功 | `[WinError 5]` | 成功 | 成功 | `True` |
| 開著，共用讀取＋刪除 | `[Errno 13]` | `[WinError 5]` | 成功 | 成功 | `True` |
| 隱藏或系統屬性 | `[Errno 13]`（`CREATE_ALWAYS` 拒絕隱藏／系統檔） | 成功；屬性消失 | 成功 | 成功 | `True` |
| ACL 拒寫資料、允許刪除 | `[Errno 13]` | 成功；deny ACE 消失 | - | - | `True` |
| 非空資料夾（測試的 `_block`） | 錯誤 | `[WinError 5]` | **成功**（Linux：`ENOTDIR`） | 錯誤 | `True` |
| `Alpha.dep` 存在，目標拼成 `alpha.dep` | - | 成功；目錄項名稱變成 `alpha.dep` | - | - | - |

`os.replace` 即 `MoveFileExW(MOVEFILE_REPLACE_EXISTING)`：只要有任何 handle 開著目標，**即使帶 `FILE_SHARE_DELETE`** 也會拒絕；唯讀目標也會拒絕。把檔案移開只需要對它的刪除權，所以對唯讀檔、以及被允許共用刪除的程序開著的檔案都能成功。packaged zh-TW build 中 Windows 錯誤文字是在地化的（`存取被拒。`、`程序無法存取檔案，因為檔案正由另一個程序使用。`）；`[Errno N]` 的文字來自 C runtime，維持英文。

目前的存檔在錯誤情境下（`probe2.py`）：文字或點字中的 lone surrogate、以及在第二個成員時拋出的 `ENOSPC`，都留下一個缺少 `.txt` 成員的有效 zip，載入時得到 `ValueError: Document package must contain one .txt and one .brl file.`（`ZipFile.__exit__` 仍會寫入 central directory）。舊文字已遺失；下次啟動建議刪除這個文件包。採用下文設計後，同樣三種錯誤都讓 `alpha.dep` 逐位元組不變且可載入。

在本機上，2 KB 檔案的 `os.fsync` 加 `os.replace` 中位數為 1.0 ms（30 次，最大 2.8 ms）。在相同時間戳下，把 zip 寫到以 `"wb"` 開啟的串流，與直接寫到路徑得到完全相同的位元組（`probe2.py`，patch `time.time`）。

目前的一般改名 vs `move_document_package`（`probe3.py`，把 `beta` 改名為 `gamma`）：

| `beta.dep` 狀態 | 目前 | `move_document_package`（未加寫入檢查） |
| --- | --- | --- |
| 開著，共用讀取或讀寫 | `[WinError 32] ...: '<beta.dep>'`；**`beta.dep` 與 `gamma.dep` 都在**，啟動時兩份都列出 | `[WinError 32] ...: '<beta.dep>' -> '<.beta.dep.x.tmp>'`；只有 `beta.dep` |
| 開著，共用讀寫刪除 | 改名成功 | 改名成功 |
| 唯讀 | `[WinError 5] ...: '<beta.dep>'`；**兩份文件包** | 改名成功，但留下唯讀的 `.beta.dep.<random>.tmp`（刪不掉） |
| 隱藏 | 改名成功（新包不再隱藏） | 同左 |

### 真實 GUI 結果（`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`）

- 18（只改大小寫的改名、重啟、重複名稱）通過。21（Defender 開啟，10 次只改大小寫的改名）沒有暫時性失敗、沒有 `.tmp`。
- 19：`alpha.dep` 以共用讀取被開著時，改名**之前**的存檔就失敗（`[Errno 13]`），名稱對話框沒有出現；共用讀寫時存檔成功、只改大小寫的改名以 `[WinError 32] ... 'alpha.dep' -> '.alpha.dep.<random>.tmp'` 失敗。清單與內容不變，沒有 `.tmp`。
- 20：`alpha.dep` 為唯讀時，改名前的存檔失敗（`[Errno 13]`），所以 F-1「改名留下唯讀 `.tmp`」的路徑無法經由開啟中的文件走到；關閉也被同一個存檔失敗 veto（F-W10）。
- F-W10：開啟中文件的 `.dep` 為唯讀或被只共用讀取的程序開著時，所有先存檔的動作（包括關閉）都會失敗；未修改的文件也會在這些動作之前被重寫。
- 27（F-2，字典）：取代隱藏檔會成功，並讓隱藏屬性消失（F 審查 M-8）。

### 釘住缺陷的測試

- `tests/test_gui_document_flows.py:2071` `test_rename_unlink_failure_leaves_both_packages_and_state` 與 `tests/test_workspace_service.py:293` `test_rename_unlink_failure_propagates_and_leaves_both_packages`：`KNOWN BUG (P1-3 spec, known defect 3)`。兩者都把舊包做成非空資料夾（`_block`）讓 unlink 失敗。
- `tests/test_workspace_service.py:366` `test_regular_rename_does_not_use_package_files`，搭配 `_UnusablePackageFiles`（`:44-50`）：F-1 D6 的守門測試；必須翻轉。
- 沒有測試釘住截斷式存檔。

## 決策

**D1. 存檔使用 F-2 helper 的二進位版本，而不是 `PackageFiles` 的 staging。** `client/shared/atomic_write.py` 新增 `write_bytes_atomically(path, write)`，步驟與保證和 `write_text_atomically` 相同（F-2 D4 及其修正）：寫入檢查、在目標資料夾以 `O_EXCL` 與 mode `0o666` 建立新的 `.<name>.<16 hex>.tmp`、`write(stream)`、`flush`、`fsync`、關檔、POSIX 上複製既有目標的 mode、`os.replace`、任何失敗都移除暫存檔（`finally`，任何 `BaseException`）。兩個版本共用一個私有核心；文字版本的行為與其 15 個測試不變。理由：

- 它已經具備存檔所需、而 F-1 staging 缺少的一切：rename 之前的 `fsync`（沒有它，rename 後立即斷電可能留下空的文件包，正是本任務要消除的失敗）、原地寫入的寫入權限判決（D3）、以 `0o666` 建檔讓 kernel 套用 umask（`NamedTemporaryFile` 給 `0600`，F 審查 M-3）、以及在寫入任何內容之前就記下暫存路徑。
- 存檔以一次 `os.replace` 取代檔案。若以相同的新舊路徑重用 `move_document_package`，會在 app 中最頻繁的寫入加上一段完全沒有 `.dep` 的視窗（把舊包移開之後、安裝新包之前）。它唯一的優點是在共用刪除的持有者下讓存檔成功（直接 replace 會失敗，見上表），而實際上會共用刪除的 Defender 在項目 21、28 中沒有造成任何失敗。
- 文字與二進位共用一個 helper，F-2 審查後修正的規則（描述元所有權、umask、`O_EXCL` 命名迴圈）只有一份實作。

不採用：以 `ctypes` 呼叫 `ReplaceFileW`（保留屬性與 ACL，但僅限 Windows、有自己的部分失敗錯誤碼，且無法在 Linux 測試）；定時重試（F-2 D8）。

**D2. `save_document_package` 經由 helper 寫入。** 簽章、名稱正規化、`package_path.parent.mkdir(parents=True, exist_ok=True)` 與回傳值都保留。zip 由新的私有 `_write_package(stream, document, *, include_pending_metadata)` 寫入，內容是目前的三行 `writestr`；`save_document_package` 呼叫 `write_bytes_atomically(package_path, lambda stream: _write_package(...))`。`zipfile.ZipFile(stream, "w")` 不會關閉傳入的串流，所以由 helper flush 並 sync 完整的封存檔。相同時間戳下位元組與目前相同（已確認）。上表所有呼叫端不需修改就得到原子行為，包括匯出為 DEP。

**D3. 保留寫入權限判決，並共用。** `write_text_atomically` 的步驟 0（目標存在且 `not os.access(target, os.W_OK)` 時拋出 `PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(target))`）改為 `shared/atomic_write.py` 的公開函式 `ensure_writable(path)`，由兩個寫入版本與 D7 使用。對存檔的影響：唯讀文件包仍以完全相同的 `[Errno 13] Permission denied: '<文件包>'` 失敗，即目前 `zipfile` 給出的文字（實測），且不建立任何檔案。若沒有它，`os.replace` 也會以指名暫存檔的 `[WinError 5]` 失敗，但在 POSIX 上 `0444` 的文件包會被取代。

**D4. move 的 staged 檔直接寫入並 sync。** `PackageFiles.write(path, document)` 不再呼叫 `save_document_package`（現在那會在第一個暫存檔裡再 stage 一個暫存檔），改為把文件包直接寫入給定的新私有檔：`open(path, "wb")`、`_write_package(..., include_pending_metadata=True)`、`flush`、`fsync`，名稱正規化與 `save_document_package` 相同。改名的原子步驟是安裝的 `os.replace`；`fsync` 讓安裝的文件包在舊包被移除之前就已持久，與存檔一致。

**D5. 每次改名都經由 `move_document_package`（修正缺陷 3）。** `rename_document` 拿掉只改大小寫的分支，每次改名都呼叫 `move_document_package(package_path(來源), package_path(新名稱), Document(新名稱, source.text, source.braille), files=self._package_files)`，再呼叫 `controller.rename_document`，如 F 審查與 F-1 D6 所建議。名稱相同時的 `ValueError` 保留。結果：

- 無法把舊包移開（另一個程式開著它且不允許共用刪除）：不安裝任何東西，移除 staged 檔，錯誤往上拋，controller 不變。一份文件包，舊的。
- 安裝失敗：舊包被移回，staged 檔被移除。一份文件包。
- 移除移開的檔案失敗：與 F-1 相同地忽略（改名已完成；留下的 `.tmp` 永遠不會被載入）。有了 D7，唯讀文件包不再發生這種情況；只有在兩次呼叫之間的毫秒內被另一個程式開啟時才可能發生。
- `casefold()` 漏掉的別名（F-1 D8：NTFS upcase 表、APFS 正規化）不再會在改名時刪掉文件包，因為不會在可能與新名稱互為別名的名稱下移除任何東西。

不採用的替代方案：「先安裝新包，再 unlink 舊包，unlink 失敗時再移除新包」。它保留目前的訊息文字，且兩步之間當機時會留下兩份列出的文件包而不是零份；但它偵測不到的別名組合會先取代、再刪除同一個檔案（F-1 缺陷 1 的機制），而且它是 F-1 之外的第二套流程。所有非當機路徑上的資料安全，比訊息文字（D6）與當機視窗（風險）更重要。

**D6. 錯誤文字可能指名暫存路徑（F-1 D6 第一個問題）。** 一般改名失敗現在顯示例如 `儲存文件失敗：[WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用。: '...\beta.dep' -> '...\.beta.dep.k2j1abcd.tmp'`，而不是 `...: '...\beta.dep'`；存檔失敗顯示 `儲存文件失敗：[WinError 5] 存取被拒。: '...\.alpha.dep.<16 hex>.tmp' -> '...\alpha.dep'`，而不是 `[Errno 13] Permission denied: '...\alpha.dep'`。模板不變，文字中仍有文件包名稱。與 F-1 D4、F-2 D5 相同地接受：模板之後的文字在所有既有情況中都是 Python 的錯誤文字；改寫它需要新字串。

**D7. 使用者不能寫入的文件包永遠不會被改名（F-1 D6 第二個問題）。** `PackageFiles` 新增 `ensure_writable(path)`（呼叫 D3 的函式），`move_document_package` 在 stage 之前先呼叫 `files.ensure_writable(old_path)`。唯讀文件包（Windows 屬性；POSIX 上此使用者沒有寫入權限）以 `[Errno 13] Permission denied: '<舊文件包>'` 被拒，且不建立或移動任何檔案。只改大小寫的改名也適用。理由：存檔已經以相同文字拒絕這種文件包（D3），Windows 上刪除也會拒絕（`[WinError 5]`），所以規則成為「app 永遠不取代或移除使用者標為唯讀的文件包」；不會留下 app 刪不掉的唯讀 `.tmp`（沒有檢查時的實測結果）；也不會靜默拿掉唯讀屬性（改名後的文件包不會帶著它，新檔是預設屬性）。可見的變化：一般改名唯讀文件包以前也會失敗，是 `[WinError 5]` 加上兩份文件包；現在是 `[Errno 13]` 加上一份。只改大小寫地改名一個「不是開啟中文件」的唯讀文件包，以前會成功並留下唯讀 `.tmp`；現在被拒（開放問題 Q2）。在 POSIX 上 `0444` 的文件包以前可以改名，現在被拒（不是出貨平台）。模型 `CaseInsensitivePackageFiles` 先解析路徑再檢查。

**D8. 重新設計缺陷 3 的錯誤注入（F-1 D6 第三個問題）。** `_block`（把舊包做成非空資料夾）在 Windows 上不會讓「移開」失敗：`os.replace(資料夾, aside 檔)` 在那裡會成功（實測），而 Linux 拋出 `ENOTDIR`。因此翻轉後的測試改經由 `package_files` 注入：一個 `PackageFiles` 子類別，當 `Path(source).name` 等於指定名稱時（字串比較，F-1 D5），其 `replace` 拋出 `PermissionError(errno.EACCES, "injected", str(source), None, str(destination))`。文字為 `[Errno 13] injected: '<...beta.dep>' -> '<...aside>'`，所以 GUI 斷言「訊息包含 `beta.dep`」仍成立。`_block` 在目前用於安裝失敗的地方仍然有效（`os.replace(檔案, 資料夾)` 在兩個平台都失敗：Linux `IsADirectoryError`、Windows `[WinError 5]`），用於存檔、新增、匯入失敗也有效（replace 到資料夾失敗，暫存檔被移除）。

**D9. 存檔時的任何 `Exception` 都在 UI 邊界回報（F 審查 M-1）。** `gui.py` 中 `_save_open_document_with_feedback`、`_create_document` 與 `on_rename_document` 改為捕捉 `Exception` 而非 `OSError`，使用相同的 `_show_file_error(_("Failed to save document: {error}"), exc)` 與相同的回傳。因此 `_on_close` 會帶訊息 veto，而不是靜默失敗。`import_files` 中每份文件的 `except OSError` 改為 `except Exception`（原因為 `str(exc)`，與 `OSError` 相同），一份無法編碼的文件不再於先前文件已寫入、但未加入清單時中止整批匯入。捕捉範圍與理由同 F-2 D7；`BaseException` 仍往上拋。刪除與全部刪除（只有 `unlink`）維持 `OSError`。

**D10. 存檔不重試、不退回其他做法。** `os.replace` 失敗時（某程式以任何共用模式開著文件包、防毒正在掃描），存檔顯示訊息、保留文件包與記憶體中的編輯，使用者的下一個動作就會重試。不退回原地寫入（那正是缺陷），也不退回「移開再安裝」（D1）。同 F-2 D8。

**D11. 檔案中繼資料比照 F-2。** 存檔安裝的是新檔：

| 屬性 | 目前（原地） | 之後 |
| --- | --- | --- |
| POSIX 權限位元 | 保留 | 保留（replace 之前複製）；新文件包為 `0o666 & ~umask`，與目前相同 |
| Windows 唯讀屬性 | 存檔被拒，`[Errno 13]` | 存檔被拒，文字相同（D3） |
| Windows 隱藏／系統屬性 | 存檔被拒，`[Errno 13]`（`CREATE_ALWAYS`） | 存檔成功；屬性消失（同 F-2 項目 27） |
| 檔案上的明確 ACL 項目 | 保留；拒寫項目使存檔被拒 | 套用資料夾繼承的 ACL；「拒寫、允許刪除」的項目不再擋住存檔且會消失（同 F-2 項目 29） |
| 替代資料流（例如 `Zone.Identifier`）、擁有者、建立時間 | 保留 | 不保留（新檔） |
| 文件包路徑上的符號連結 | 寫穿過去 | 被一般檔案取代 |

改名：改名後的文件包目前也是新檔；變更後它還會保留舊包的 POSIX 位元（F-1 M-3 的 `copy_permissions`），但若舊包不存在則為 `0600`（`NamedTemporaryFile`，F-1 已記錄；僅 POSIX）。workspace 是每使用者的 app 資料；預期以上都不重要，而隱藏／系統的變化讓一個原本永遠無法成功的存檔變得可以成功。

**D12. F-W10 不在範圍內；但觸發它的情況會改變。** F-W10（存檔失敗擋住關閉與改名；未修改的文件被重寫）需要自己的決策：因為記憶體先於寫入更新，略過未修改文件的寫入需要「最後儲存」紀錄；不存檔就關閉需要新對話框與新字串。F-3 不改變控制流程。它對 F-W10 的確切影響（開啟中文件的文件包）：

| 文件包狀態 | 目前 | F-3 之後 |
| --- | --- | --- |
| 唯讀 | 擋住（`[Errno 13] ... '<pkg>'`） | 擋住，文字相同 |
| 開著，共用讀取（7-Zip 類） | 擋住（`[Errno 13]`） | 擋住（`[WinError 5] ... '<tmp>' -> '<pkg>'`） |
| 開著，共用讀寫 | 不擋；存檔在另一個程式底下重寫檔案 | **擋住**（`[WinError 5]`） |
| 開著，共用讀寫刪除（防毒、索引類） | 不擋 | **handle 開著期間擋住**（`[WinError 5]`） |
| 隱藏或系統 | 擋住（`[Errno 13]`） | 不擋；屬性消失 |
| ACL 拒寫、允許刪除 | 擋住 | 不擋；項目消失 |
| 未修改的文件 | 每個動作前都重寫 | 仍重寫（原子地） |

新增的擋住情況為開放問題 Q1。存檔的非 `OSError`（D9）現在會帶訊息擋住關閉；之前關閉靜默地什麼都不做。

**D13. 暫存名稱。** 存檔的暫存檔為 `.<文件包名稱>.<16 hex>.tmp`（`.alpha.dep.0123456789abcdef.tmp`）；move 沿用 F-1 的 `NamedTemporaryFile` 名稱（`.alpha.dep.<8 個字元>.tmp`）。兩者都以點開頭、以 `.tmp` 結尾，所以 `Path.glob("*.dep")` 永遠不會列出它們（已確認；pathlib 在 Windows 上的比對是純 Python，不看 8.3 短檔名），啟動對話框也永遠不會建議刪除它們。殘留只可能來自當機或清理失敗；無害，可以手動刪除。統一兩種命名（F 審查 M-3、M-4）為後續工作。在 Windows 上前導點不會隱藏檔案；`temporary_path` docstring 中的「hidden」一併更正（F 審查 M-7）。

## 各路徑的行為（之前／之後）

| 路徑 | 之前 | 之後 |
| --- | --- | --- |
| 存檔（`save_open_document`，每個文件動作與關閉之前） | 更新記憶體，再原地截斷並重寫文件包；中途失敗留下壞包（下次啟動無效、建議刪除）；顯示 `OSError`，其他例外逃出 | 更新記憶體（契約不變），再 stage、sync、replace；任何失敗都讓文件包逐位元組不變、無 `.tmp`；任何 `Exception` 都以相同模板顯示，動作停止 |
| 新增／預設文件（`create_document`） | 原地寫入文件包，再加入記憶體；失敗：不加入，可能留下部分檔案 | 原子寫入，再加入；失敗：不加入，磁碟上沒有新東西（該名稱已有的檔案不變） |
| 匯入（`import_files`） | 每份文件原地寫入；`OSError` 變成問題；其他錯誤中止整批（先前的文件包在磁碟上但不在清單中） | 每份文件原子寫入；任何 `Exception` 變成問題（`str(exc)`）；整批繼續 |
| 一般改名 | 原地寫 `gamma.dep`，unlink `beta.dep`；unlink 失敗：兩份文件包，記憶體為 `beta`（缺陷 3） | 拒絕不可寫的 `beta.dep`（`[Errno 13]`）；stage `gamma`、移開 `beta.dep`、安裝 `gamma.dep`、移除移開的檔案；任何失敗：只有 `beta.dep`，記憶體為 `beta` |
| 只改大小寫的改名 | F-1 move；唯讀文件包（非開啟中）被改名，留下唯讀 `.tmp` | 同一個 move，先做寫入檢查：唯讀文件包被拒（`[Errno 13]`），什麼都不留；staged 文件包已 sync |
| 關閉 | 存檔；失敗時帶訊息 veto；非 `OSError` 逃出（視窗保持開啟，沒有訊息） | 存檔；任何失敗都帶訊息 veto（鎖定情況見 D12） |
| 刪除／全部刪除 | `unlink`；失敗時顯示訊息，不改變任何東西（全部刪除會重新載入） | 不變 |
| 啟動載入 | `glob("*.dep")`；壞包被建議刪除 | 不變；`.tmp` 殘留永遠不會列出；存檔不再可能產生壞包 |
| 匯出為 DEP | 原地寫入使用者選的路徑 | 原子寫入使用者選的路徑（訊息相同；隱藏的目標現在會被取代） |

## Windows NTFS 上的失敗模式（除非註明，皆為開啟中文件的存檔）

「訊息」為 packaged zh-TW build 顯示的內容（標題 `錯誤`）。

| 錯誤 | 之前：磁碟 | 之前：使用者看到 | 之後：磁碟 | 之後：使用者看到 |
| --- | --- | --- | --- | --- |
| 文件包唯讀 | 不變 | `儲存文件失敗：[Errno 13] Permission denied: '...\alpha.dep'`；動作被擋 | 不變，無 `.tmp` | 相同 |
| 文件包開著，共用讀取（zip 工具） | 不變 | `[Errno 13] Permission denied: '...\alpha.dep'`；被擋 | 不變，無 `.tmp` | `儲存文件失敗：[WinError 5] 存取被拒。: '...\.alpha.dep.<hex>.tmp' -> '...\alpha.dep'`；被擋 |
| 文件包開著，共用讀寫 | 在讀取者底下重寫 | 沒有訊息 | 不變，無 `.tmp` | 同上的 `[WinError 5]`；被擋（Q1） |
| 防毒／索引當下持有它（全部共用） | 重寫 | 沒有訊息 | 不變，無 `.tmp` | 一次 `[WinError 5]`；下一個動作重試（實測 20 次中 0 次，項目 21、28） |
| 防毒持有新的暫存檔 | - | - | 不變；若移除也失敗則留下 `.tmp`（永不載入） | 指名 `.tmp` 的 `[WinError 5]` 或 `[WinError 32]` |
| 磁碟已滿 | **壞包**（缺少成員的有效 zip） | `[Errno 28] No space left on device`（預期；待驗證） | 不變；`.tmp` 已移除 | 相同訊息；編輯保留在記憶體 |
| 文字或點字中的 lone surrogate | **壞包** | 沒有訊息（例外逃出；關閉靜默無作用） | 不變，無 `.tmp` | `儲存文件失敗：'utf-8' codec can't encode character '\ud800' in position N: surrogates not allowed`；動作被擋 |
| 寫入中當機／斷電 | **壞包**；下次啟動建議刪除 | 無效文件包對話框 | 舊包或新包，完整（replace 前已 `fsync`）；可能殘留 `.tmp` | 沒有訊息 |
| 隱藏或系統屬性 | 不變 | `[Errno 13]`；被擋 | 被取代，屬性消失 | 沒有訊息 |
| ACL 拒寫、允許刪除 | 不變 | `[Errno 13]`；被擋 | 被取代，項目消失 | 沒有訊息 |
| 一般改名，舊包開著，共用讀取或讀寫 | **兩份文件包**；記憶體為舊名 | `[WinError 32] ...: '...\beta.dep'` | 只有 `beta.dep` | `[WinError 32] ...: '...\beta.dep' -> '...\.beta.dep.<rnd>.tmp'` |
| 一般改名，舊包唯讀 | **兩份文件包** | `[WinError 5] ...: '...\beta.dep'` | 只有 `beta.dep` | `[Errno 13] Permission denied: '...\beta.dep'` |
| 只改大小寫的改名，舊包唯讀、非開啟中 | 已改名，留下唯讀 `.Alpha.dep.<rnd>.tmp` | 沒有訊息 | 不變 | `[Errno 13] Permission denied: '...\Alpha.dep'`（Q2） |
| 改名時在「移開」與「安裝」之間當機 | （一般：不可能；只改大小寫：沒有 `.dep`，資料在兩個 `.tmp`） | 下次啟動文件不見 | 這份文件沒有 `.dep`，資料在兩個 `.tmp`（現在一般改名也會） | 下次啟動文件不見；可手動復原（風險） |

## 各檔案的設計

### `client/shared/atomic_write.py`（4 個空白）

- `ensure_writable(path: Path | str) -> None`：目前的步驟 0，公開，附 docstring（「原地 `open(path, "w")` 會給的判決；rename 不會問」）。
- `_open_temporary_file(destination, opener, **open_arguments)`：命名迴圈，把 `mode`、`encoding`、`newline` 傳給 `open`。
- `_write_atomically(destination, write, **open_arguments)`：目前 `write_text_atomically` 步驟 0 之後的內容（opener 記錄路徑、`write`、`flush`、`fsync`、POSIX `chmod`、`os.replace`、`finally` 清理）。
- `write_text_atomically(path, write, *, encoding="utf-8", newline="")`：`ensure_writable`，再以 `mode="w"` 呼叫核心。行為與簽章不變。
- `write_bytes_atomically(path, write: Callable[[BinaryIO], None]) -> None`：`ensure_writable`，再以 `mode="wb"` 呼叫核心。docstring：相同保證；資料夾必須已存在。
- 模組 docstring：提到兩個版本。

### `client/documents/workspace.py`（4 個空白）

- 從 `shared.atomic_write` 匯入 `ensure_writable` 與 `write_bytes_atomically`。
- `_normalized(document) -> Document`（目前 `save_document_package` 做的名稱正規化）與 `_write_package(stream, document, *, include_pending_metadata)`（目前的 `ZipFile` 區塊，改寫到串流）。
- `save_document_package`：D2。
- `PackageFiles.ensure_writable(path)`：D7。`PackageFiles.write`：D4，docstring「Write the package into the new private file ``path`` and flush it to disk.」。`temporary_path` docstring：「dot-prefixed `.tmp` file, never matched by `*.dep`」（M-7）。
- `move_document_package`：最先呼叫 `files.ensure_writable(old_path)`；docstring 加上「拒絕」與「每次改名都使用」。

### `client/documents/workspace_service.py`（4 個空白）

- `rename_document`：D5（兩種改名都是一次 `move_document_package` 呼叫）。`save_document_package` 的匯入保留（存檔、新增、匯入）。
- `import_files`：`except Exception as exc`（D9）。
- 模組 docstring：存檔經由暫存檔寫入；每次改名都先 stage 新包、把舊包移開，再安裝。

### `client/gui.py`（tab 縮排）

三個 `except OSError as exc:` 改為 `except Exception as exc:`（第 599、628、760 行）。其他不變。

### `client/tests/case_insensitive_package_files.py`（4 個空白）

`ensure_writable(path)`：`super().ensure_writable(self.resolve(path))`。

### 不變

`documents/controller.py`、`documents/formats.py`、`documents/export_coordinator.py`、對話框、`.po`/`.mo`、fixture。

## 維持不變的部分

- 相同時間戳下的文件包格式與位元組；成員名稱；待轉換中繼資料；載入器及其檢查。
- 存檔的「先記憶體後寫入」順序、新增的「先寫入後加入」順序、改名／刪除／全部刪除的 controller 更新。
- 所有訊息模板與標題；存檔遇到唯讀文件包時的文字。
- 只改大小寫的改名成功時的結果（F-1 測試不變）、新增／改名的重複檢查。
- `write_text_atomically` 的行為（其 15 個測試不變）。
- msgid（353，集合相同）、`client/locales`、兩個 fixture 的 sha256。

## 使用者可見字串

沒有新增或變更 msgid。可見的差異只有 `{error}` 內的 Python 錯誤文字（D6、D12），以及非 `OSError` 失敗現在會顯示訊息（D9）。不需要更新 `.po`/`.mo`；驗收時確認 `git diff main -- client/locales` 為空。

## 測試計畫

TDD：每一步的測試先寫，並因所述原因失敗，再由程式碼轉綠。測試檔維持各自的縮排（以下檔案都是 4 個空白）。所有測試都使用暫存資料夾；不碰 `client/dictionary/`、`client/workspace/` 或 `config.json`。錯誤注入經由 `package_files`（F-1 D5），或 patch `os` 函式（`os.replace`、`os.access`、`os.fsync`；呼叫時才查找，不受 `wx_stub` 模組副本影響），絕不從 GUI 測試 patch `documents.*` 的模組全域變數。

新增 helper `client/tests/windows_file_handles.py`（不是測試模組）：`hold_open(test_case, path, share)` 經由 `ctypes` 以 `CreateFileW(GENERIC_READ, share, OPEN_EXISTING)` 開著 `path`，並以 `addCleanup` 註冊 `CloseHandle`；常數 `SHARE_READ = 1`、`SHARE_READ_WRITE = 3`。共用檢查適用於每個 handle，包括測試自己的程序（實測）。設定唯讀屬性的 Windows 專屬測試，在暫存資料夾的清理之後以 `addCleanup` 註冊 `os.chmod(path, stat.S_IWRITE | stat.S_IREAD)`，讓它先執行。

### A. Helper（`client/tests/test_atomic_write.py`，新類別 `WriteBytesAtomicallyTest`）

紅燈：`AttributeError: ... has no attribute 'write_bytes_atomically'`／`'ensure_writable'`。

1. `test_replaces_an_existing_file_with_the_written_bytes`：清單 `["d.dep"]`，位元組完全相同。
2. `test_creates_a_file_that_does_not_exist`。
3. `test_disk_full_while_writing_keeps_the_original_bytes_and_leaves_no_temporary_file`：callback 先寫入，再拋出 `OSError(errno.ENOSPC, ...)`。
4. `test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file`：patch `os.replace`；記錄到的來源在同一資料夾，且符合 `\.d\.dep\.[0-9a-f]{16}\.tmp`。
5. `test_interrupt_leaves_no_temporary_file_and_propagates`（`KeyboardInterrupt`）。
6. `test_data_is_flushed_to_disk_before_the_replace`：`fsync` 時 `os.fstat(fd).st_size` 為完整長度；`fsync` 在 `replace` 之前（I-1 的寫法）。
7. `test_a_file_without_write_access_raises_permission_error_and_is_kept`：`os.access` patch 為 `False`；文字恰為 `[Errno 13] Permission denied: '<path>'`；不建立任何檔案。
8. `test_ensure_writable_accepts_missing_and_writable_files_and_refuses_others`。
9. 僅 POSIX：`test_keeps_the_permission_bits_of_an_existing_file`（`0o640`）。
10. 僅 Windows：`test_a_read_only_file_is_refused_with_the_in_place_verdict`（`os.chmod(path, stat.S_IREAD)`；`[Errno 13]` 文字完全相同；位元組不變；無 `.tmp`）。
11. 僅 Windows：`test_a_file_held_open_by_another_handle_is_kept`（共用讀寫：`PermissionError` 且 `winerror == 5`；位元組不變；無 `.tmp`）。

### B. 文件包（`client/tests/test_document_workspace.py`）

存檔（`DocumentWorkspaceTest` 或新類別 `AtomicSaveDocumentPackageTest`）：

1. `test_save_failure_from_a_lone_surrogate_keeps_the_existing_package`（subTest：文字、點字）：`UnicodeEncodeError`；位元組不變；清單 `["alpha.dep"]`；可載入。**目前紅燈**：文件包缺少 `.txt`。
2. `test_save_failure_while_writing_keeps_the_existing_package`：patch `zipfile.ZipFile.writestr`，在第二個成員拋出 `OSError(errno.ENOSPC)`。**紅燈**：壞包。
3. `test_save_install_failure_keeps_the_existing_package`：patch `os.replace`。**紅燈**：目前不會拋例外。
4. `test_save_installs_a_temporary_file_from_the_same_folder`：記錄到的 `os.replace` 來源名稱符合 `\.alpha\.dep\.[0-9a-f]{16}\.tmp`，目的地為文件包。**紅燈**。
5. `test_save_refuses_a_package_without_write_access`：patch `os.access`；`[Errno 13]` 文字完全相同；位元組不變。**紅燈**。
6. 僅 Windows：`test_save_of_a_read_only_package_gives_the_old_message`：恰為 `[Errno 13] Permission denied: '<文件包>'`。目前綠燈（釘住 D3）。
7. 僅 Windows：`test_save_of_a_package_held_open_keeps_it`（共用讀寫）：`winerror == 5`；位元組不變；無 `.tmp`。**紅燈**：目前存檔會原地成功。
8. 僅 Windows：`test_save_of_a_hidden_package_replaces_it_and_drops_the_attribute`。**紅燈**：目前 `[Errno 13]`。釘住 D11。
9. 僅 POSIX：`test_save_keeps_the_permission_bits_of_the_package`（`0o640`）。目前綠燈（回歸守門）。
10. `test_save_writes_the_same_bytes_as_the_in_place_writer`：`time.time` patch 為常數；與測試中以 `ZipFile(path, "w")` 寫出的參考比較。目前綠燈（釘住格式）。
11. `test_load_workspace_documents_ignores_leftover_temporary_files`（`.alpha.dep.0123456789abcdef.tmp`、`.alpha.dep.k2j1abcd.tmp`）。目前綠燈（釘住 D13）。

Move（`MoveDocumentPackageTest`）：

12. `test_unwritable_old_package_is_refused_before_anything_changes`：`os.access` patch 為 `False`；`PermissionError` 指名舊包；清單與位元組不變；無 `.tmp`。**紅燈**：目前 move 會成功。
13. 僅 Windows：`test_read_only_old_package_is_refused_and_leaves_no_temporary_file`（subTest：只改大小寫 `Alpha` 到 `alpha`、一般 `Alpha` 到 `gamma`）。**紅燈**：目前改名成功並留下唯讀 `.tmp`。
14. `test_staged_package_is_written_directly_and_flushed_to_disk`：`PackageFiles().write(staged, document)` 對一個大小（`os.fstat`）為完整封存檔的描述元呼叫 `os.fsync`，且不呼叫 `os.replace`（直接寫給定的檔案，不巢狀 stage）；檔案可載入。**紅燈**：目前沒有 `fsync`。

`_FailingPackageFiles` 新增 `ensure_writable`（委派，並 `_check("ensure_writable", path)`）。

### C. Service（`client/tests/test_workspace_service.py`）

- `_FailingInstallPackageFiles` 改為 `_FailingReplacePackageFiles(*, source_name=None, destination_name=None)`（D8 的錯誤文字）；只改大小寫的安裝測試傳 `destination_name="alpha.dep"`。移除 `_UnusablePackageFiles`。
- **翻轉** `test_rename_unlink_failure_propagates_and_leaves_both_packages` 為 `test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state`（`source_name="alpha.dep"`）：拋出例外；清單 `["alpha.dep"]`；位元組與狀態不變。註解：原為 P1-3 已知缺陷 3 的 `KNOWN BUG`，由 F-3 修正。**紅燈**：目前路徑不使用 `package_files`，會改名成功。
- **翻轉** `test_regular_rename_does_not_use_package_files` 為 `test_regular_rename_moves_the_old_package_aside_before_installing`：一個會記錄的 `PackageFiles` 子類別；`replace` 呼叫恰為 `alpha.dep -> .alpha.dep.*.tmp`，然後 `.gamma.dep.*.tmp -> gamma.dep`；清單 `["gamma.dep"]`。**紅燈**。
- 新增 `test_regular_rename_install_failure_puts_the_old_package_back`（`destination_name="gamma.dep"`）。**紅燈**。
- 新增 `test_rename_of_an_unwritable_package_is_refused`（patch `os.access`）：`PermissionError` 指名 `alpha.dep`；清單與狀態不變。**紅燈**。
- 新增 `test_save_failure_keeps_the_package_and_updates_memory`：`save_open_document(text="\ud800", ...)` 拋出例外；記憶體有編輯（契約）；文件包位元組不變。**紅燈**。
- 新增 `test_import_files_reports_any_save_error_as_an_issue`：`patch.object(workspace_service, "save_document_package", side_effect=...)`，只對 `beta` 拋出 `UnicodeEncodeError`；`delta` 被存檔並加入；`beta.dep` 的問題帶有錯誤文字。**紅燈**：錯誤會逃出。
- `test_rename_write_failure_propagates_and_keeps_state`（`_block("gamma")`）保留；加上清單檢查 `["alpha.dep", "gamma.dep"]`（擋路的資料夾，無 `.tmp`）。

### D. GUI 流程（`client/tests/test_gui_document_flows.py`）

- **翻轉** `test_rename_unlink_failure_leaves_both_packages_and_state` 為 `test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state`：frame 的 service 以 `package_files=` 本地的 `_FailingReplacePackageFiles(source_name="beta.dep")` 建立（同 `_rename_alpha_case_only` 的做法）；事件：改名對話框，然後錯誤框（模板，包含 `beta.dep`）；清單 `["alpha.dep", "beta.dep"]`；`beta.dep` 位元組與狀態不變。**紅燈**。
- 新增 `test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package`：輸入 `"x\ud800"`；`_save_open_document_with_feedback()` 回傳 `False`；一個以模板前綴開頭、包含 `surrogates not allowed` 的錯誤框；文件包位元組不變。**紅燈**：例外逃出且文件包壞掉。
- 新增 `test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error`。**紅燈**。
- 新增 `test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state`：改名非開啟中的 `beta`，其記憶體中的文字為 `"\ud800"`；錯誤框；清單與狀態不變。**紅燈**。
- 新增 `test_add_failure_that_is_not_an_os_error_shows_the_message`：在 frame 的 service 實例上 patch `create_document` 拋出 `ValueError("boom")`；錯誤框 `Failed to save document: boom`；沒有加入任何東西。**紅燈**。
- 新增，僅 Windows：`test_rename_of_a_read_only_package_is_refused_with_the_save_message`：`beta.dep` 唯讀、非開啟中；改名為 `gamma`；錯誤框包含 `[Errno 13]` 與 `beta.dep`；清單 `["alpha.dep", "beta.dep"]`；無 `.tmp`。**紅燈**：目前兩份文件包都留著。
- 不變且仍為綠燈：`test_save_failure_reports_error_after_updating_memory`、`test_close_vetoes_when_save_fails`、`test_add_write_failure_shows_error_and_keeps_state`、`test_rename_write_failure_keeps_old_package_and_state`、F-1 的只改大小寫測試。

### 數量

新增：A 11、B 14、C 4、D 5 = 34；翻轉的測試一對一取代。預期：worktree `Ran 1172`（主 checkout 1177）。僅 Windows：A10、A11、B6、B7、B8、B13、D 的唯讀測試（7 個，POSIX 上 skip）；僅 POSIX：A9、B9（2 個，Windows 上 skip）。Windows 上 skip 數增加 2。plan 可以調整數量；spec 中的紅綠意圖是約束性的。

## 遷移步驟（每步一個綠燈 commit，先紅後綠）

1. `refactor: share the atomic write core and add a bytes variant`：A 1-11（紅燈：缺少屬性）。文字版本的測試不變且為綠燈。
2. `fix: save document packages atomically`：D2、D4、D13 docstring；B 1-11、B 14、C「save failure keeps the package」。先紅：B 1-5、7、8、14 與該 service 測試。
3. `fix: refuse renaming a package the user may not write`：D7（`ensure_writable` seam、模型、`_FailingPackageFiles`）；B 12-13。先紅：兩者。
4. `fix: route every rename through move_document_package`：D5、D8；兩個翻轉、守門測試翻轉、C 的安裝失敗與不可寫測試、D 的翻轉與 Windows 唯讀 GUI 測試；模組 docstring。先紅：全部。
5. `fix: report every save error at the document UI boundary`：D9；C 的匯入測試、D 的 4 個非 `OSError` 測試。先紅：全部五個。

每個 commit 以 brief 中的 `Co-Authored-By` 行結尾，只 stage 明確的路徑。沒有任何 commit 修改 `.po`/`.mo`、fixture、`client/dictionary/`、`client/braille/`。

## 驗收標準

在 Windows（開發機）上於 `client/` 以 `$PY` 執行。

1. 完整套件：除了已知的 P2-5 失敗、F-W6，以及（僅 worktree）`test_liblouis_runtime` 匯入錯誤之外，沒有其他失敗或錯誤；`Ran` = 基準 + 34。
2. 相關模組：`$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller -v` 通過；七個僅 Windows 的測試有執行（沒有 skip）。
3. 若有 shuffle 工具（HANDOFF 第 5 節），五個 seed 都只回報已知失敗。
4. `git diff main -- client/locales` 為空；`git diff main -- client` 中沒有新的 `_(`／`N_(` 字面值。
5. 兩個 fixture 的 sha256 不變。
6. app 資料未被動到：`client/dictionary/` 的 sha256 在套件前後相同；沒有建立 `client/workspace/` 或 `client/config.json`。
7. `git grep -n "KNOWN BUG (P1-3 spec, known defect 3" -- client/tests` 找不到任何結果；缺陷 4 的標記仍在。
8. `git diff main --stat` 只碰 `client/shared/atomic_write.py`、`client/documents/workspace.py`、`client/documents/workspace_service.py`、`client/gui.py`、上述測試檔與 helper，以及 spec／plan 檔。
9. Mutation 檢查（plan）：每個 mutant 至少被一個測試抓到：`save_document_package` 改回 `ZipFile(path, "w")`；bytes 核心沒有 `fsync`；沒有 `flush`；只在 `OSError` 時清理；暫存檔放在系統暫存資料夾；`write_bytes_atomically` 沒有寫入檢查；寫入檢查套用到不存在的檔案；`PackageFiles.write` 沒有 `fsync`；`PackageFiles.write` 改回 `save_document_package`（巢狀 stage；由 B 14 的「不呼叫 `os.replace`」斷言抓到）；move 中沒有 `ensure_writable`；一般改名改回「先寫後 unlink」；三個 GUI handler 各自改回 `except OSError`；`import_files` 改回 `except OSError`。
10. 下方的 packaged GUI 驗證，結果附在實作記錄中。

## Windows 驗證（packaged build）

依 `docs/superpowers/history/2026-10-09-03-windows-verification/test.md` 第 0.1 節在本 worktree 建置：從主 checkout 複製 `client\braille\liblouis.dll`、`client\braille\liblouis\` 與 `client\mathcat\assets\`（同 build B 的做法；submodule 版本相同），再把 `vendor\nvda\liblouis\runtime\louis_helper.py` 複製到 `client\braille\`，執行 `scripts\build-dotexpress.bat`，把 `client\dist\DotExpress.exe` 複製到 `D:\dxtest\F3\`。把 `docs/superpowers/history/2026-10-09-03-windows-verification/auto/` 中的腳本複製到實作的 history 資料夾，只把寫死的 `EXE` 改為 `D:\dxtest\F3\DotExpress.exe`、資料夾改為 `D:\dxtest\auto-f3*`，在另一個裝了 `pywinauto`、`psutil` 的 venv 中執行。比對 zip 成員，而不是整個檔案（時間戳會變）。

| # | 腳本 | F-3 之後的預期 | 之前（N） |
| --- | --- | --- | --- |
| 18 | `item18.py` | 不變：只改大小寫的改名保留文件；重複名稱被拒；無 `.tmp` | 相同 |
| 19 r | `item19.py`，共用讀取 | 改名前的存檔失敗：`儲存文件失敗：[WinError 5] 存取被拒。: '...\.alpha.dep.<hex>.tmp' -> '...\alpha.dep'`；沒有名稱對話框；清單、內容不變；無 `.tmp`；重啟後不變 | `[Errno 13]` |
| 19 rw | `item19.py`，共用讀寫 | **存檔如共用讀取一樣失敗**（Q1） | 存檔成功，改名以 `[WinError 32]` 失敗 |
| 20 | `item19.py` 後半與 `item20b.py`（開啟中文件為唯讀） | 不變：`[Errno 13] Permission denied: '...\alpha.dep'`；關閉被 veto（F-W10） | 相同 |
| 21 | `item21.py`（Defender，10 次只改大小寫的改名） | 10/10，無 `.tmp` | 相同 |
| 30（新） | `beta.dep` 被開著（先共用讀取，再共用讀寫）時，一般改名非開啟中的 `beta` | `儲存文件失敗：[WinError 32] ...: '...\beta.dep' -> '...\.beta.dep.<rnd>.tmp'`；清單不變；只有 `beta.dep`（沒有 `gamma.dep`、沒有 `.tmp`）；重啟後不變 | 磁碟上 `gamma.dep` 與 `beta.dep` 都在，重啟後都列出 |
| 31（新） | `attrib +r` 後，一般改名與只改大小寫改名非開啟中的 `beta`／`Beta` | `[Errno 13] Permission denied: '...\beta.dep'`；什麼都不變；無 `.tmp` | 一般：`[WinError 5]`，兩份文件包；只改大小寫：改名成功，留下唯讀 `.tmp` |
| 32（新） | 對開啟中文件 `attrib +h`，輸入、切換文件、重啟 | 存檔成功；內容保留；檔案不再隱藏 | 存檔以 `[Errno 13]` 失敗，切換被擋 |
| 33（新） | Defender 開啟，20 次切換文件、每次切換前先編輯 | 預期 0 次失敗；記錄任何 `[WinError 5]`；無 `.tmp` | - |
| 34（可選，人工） | app 資料夾放在一個小 VHD 上、填到只剩幾 KB；貼上大量文字；切換文件；重啟 | 訊息（記錄文字，預期 `[Errno 28] No space left on device`）；重啟後文件包以舊文字載入 | 壞包，被建議刪除 |

真實 7-Zip 仍需人工（項目 19 的備註）：記錄它使用哪種共用模式，因此適用哪一列。

## 風險

- **被鎖住的文件包在更多情況下擋住存檔**（中，Q1）。以任何共用模式開著文件包的程式，現在都會讓存檔失敗；以前共用讀寫、共用讀寫刪除的持有者不會。所有先存檔的動作（包括關閉）都會被擋，直到 handle 關閉。安全（有訊息、文件包與編輯都保留），下一個動作會重試。實測的 Defender 行為（項目 21、28）沒有暫時性失敗。
- **一般改名的當機視窗**（低）。在把舊包移開與安裝新包之間（兩次連續的同資料夾 rename，毫秒級）當機，這份文件就沒有 `.dep`；資料在 `.<舊>.dep.<rnd>.tmp` 與 `.<新>.dep.<rnd>.tmp`，下次啟動不會提示（F 審查 M-2）。以前一般改名的當機視窗會留下「壞掉的新包加完整的舊包」或兩份文件包。為了別名安全（D5）接受；M-2 的啟動時復原是後續工作。
- **還原失敗**（很低）。安裝失敗、把舊包移回也失敗：顯示錯誤，舊包留在它的 `.tmp`；記憶體不變，所以該文件（若為開啟中）的下一次存檔會再寫出它。
- **檔案中繼資料**（低，D11）。存檔不保留隱藏／系統屬性、明確 ACL 項目、替代資料流與建立時間；符號連結被一般檔案取代。
- **寫入檢查**（低，D3/D7）。Windows 上 `os.access` 只看唯讀屬性；拒寫的 ACL 看不到，存檔就會取代該檔。在檢查與 replace 之間被設為唯讀的檔案，會在 replace 時安全地失敗（`[WinError 5]`）。
- **較寬的捕捉**（低，D9）。存檔時的程式錯誤現在顯示訊息而不是 traceback（packaged build 本來就沒有 console）。文字中有 lone surrogate 時，每次關閉都會帶訊息被 veto，直到移除該字元；以前關閉靜默無作用，且文件包壞掉。
- **兩種暫存命名**（低，D13）。兩者都是以點開頭的 `.tmp`；永不載入。
- **測試時間**（低）。每次存檔多一次 `fsync`：本機中位數 1 ms；F 審查在 Linux 量到每次 `fsync` 50-70 ms。若 GUI 流程測試在 Linux 上慢超過 2 s，比照 F 審查 M-6 在其 harness 中把 `os.fsync` 換成 no-op；`test_atomic_write` 保留真實呼叫。

## 給使用者的開放問題（已於 2026-10-09 決定，見「規劃後更正」）

**Q1. 被另一個程式開著的 `.dep` 現在在多兩種共用模式下擋住存檔。** 目前當另一個程式允許寫入（共用讀寫，含或不含刪除）時，存檔會原地重寫檔案；F-3 之後 `os.replace` 拒絕任何被開著的目標，所以存檔以 `[WinError 5]` 失敗，動作（切換、改名、關閉……）被擋，直到那個程式關閉檔案；這和目前只共用讀取的 zip 工具已經發生的情況相同。**建議：接受。** 在另一個程式開著的 handle 底下寫入，正是 F-3 要移除的行為（那個程式可能正在讀半寫完的封存檔），失敗是可見且安全的，實測的防毒行為也沒有暫時性失敗。替代方案：(a) replace 失敗時退回「把舊包移開再安裝」（只對共用刪除的持有者有幫助；會在每次這樣的存檔加上沒有 `.dep` 的當機視窗）；(b) 提前做 F-W10 後續工作（略過未修改文件的寫入；存檔失敗後允許不存檔就關閉）。**已決定：接受。** 由協調者採用建議的預設決定；使用者可在合併前推翻。

**Q2. 唯讀文件包不能再改名。** 兩種改名都以 `[Errno 13] Permission denied: '<文件包>'` 拒絕它（D7）。目前一般改名它會失敗並留下兩份文件包，而只改大小寫地改名一個非開啟中的唯讀文件包會成功，但留下 app 刪不掉的唯讀 `.tmp`。**建議：拒絕**，與已經會拒絕它的存檔和刪除一致。替代方案：刪除移開的檔案之前先清除它的唯讀屬性以允許改名；改名後的文件包會失去唯讀屬性，之後的存檔會覆寫它。**已決定：拒絕。** 由協調者採用建議的預設決定；使用者可在合併前推翻。

## 範圍外／後續工作

- **F-W10**：略過未修改文件的寫入（需要「最後儲存」紀錄）；存檔失敗後提供不存檔就關閉；對被鎖檔案給出更清楚的訊息（新字串）。
- **F 審查 M-2**：啟動時找出沒有對應 `.dep` 的孤兒 `.<name>.dep.<rnd>.tmp`，並提供還原（現在一般改名也相關）。
- **F 審查 M-3/M-4**：讓 `PackageFiles.temporary_path` 使用 helper 的 `O_EXCL`／`0o666` 命名迴圈，並不再預先建立 aside 檔。
- **P1-3 缺陷 4**（全部刪除回滾後沒有有效文件）、刪除／全部刪除的語意：不變。
- **其他寫入端**：匯出 BRL／HTML（`write_text`）、`config.json`、`save_preprocessing_script`、`dictionaries/manager.py` 的表頭寫入與複製（F 審查第 4 節）。
- **匯出的非 `OSError` 處理**（P1-4 缺陷 7）：不變；匯出為 DEP 只是多了原子性。
- **F-1 D8** 對新增的影響：磁碟上有但清單中沒有的 `.dep`（保留的無效包），仍會被同名的新增／匯入取代。
- 在 replace 時保留隱藏／系統屬性或 ACL（`ReplaceFileW`）：除非使用者要求，否則不計畫。
