# F-3 原子化 `.dep` 寫入審查記錄

- 日期：2026-10-09
- 範圍：`fix/f3-dep-atomic-write` 的 `main..fix/f3-dep-atomic-write`（`main` = `4953772`；10 個 commit：`b6d1c7d` spec、`e6fca4a` plan、`d9197dc..fa888ff` 實作 6 個、`e425fb0` GUI 結果、`35a0acc` merge main）。production diff `git diff main...fix/f3-dep-atomic-write -- client`：10 個檔，+964／−99。
- 對照：`docs/superpowers/specs/2026-10-09-f3-dep-atomic-write-design.md`（含 `_zh-TW.md`，含「Corrected after planning」與 Q1 accept／Q2 refuse）、`docs/superpowers/plans/2026-10-09-f3-dep-atomic-write.md`、`docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto-results.md` 與 `auto/`、`docs/superpowers/history/2026-10-09-01-fix-data-loss/review_task.md`（F-1／F-2、優先清單、D6 三個問題）、`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`（F-W9–F-W13）、`AGENTS.md`。
- 審查方式：逐行讀 4 個 production 檔的 diff 與全文、6 個測試檔的 diff；對 `write_bytes_atomically`／`_write_atomically` 與 `move_document_package` 逐步推演 Windows NTFS 的每個失敗分支；在 Windows 11（NTFS，`D:` 與 `C:`）上跑完整套件、焦點模組、3 個 shuffle seed；把每個實作 commit 的測試拿去跑其父 commit 的 production code（red-first 重放）；在 scratchpad 的 `client/` 副本上自套 15 個 mutant；以 24 組名稱對在真實 NTFS 上探測 `casefold()` 之外的別名；稽核 `D:\dxtest\auto*-f3.log` 十個 log 與 exe 雜湊（沒有重跑 GUI、沒有結束任何程序）。凡未能驗證的標為「推理」或「不確定」。
- 本記錄只寫檔，未 commit。

## 驗證（Windows 11 26200，`$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`，cwd `D:\workspace\DotExpress-f3\client`，`$SP` = session scratchpad）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| 完整套件 | `$PY -m unittest discover -s tests` | `Ran 1248 tests in 13.020s`, `FAILED (errors=1, skipped=7)`；唯一 error 為 `test_dictionary_name_prompt ... test_case_only_rename_still_renames`（F-W6，`FileExistsError: Dictionary 'Alpha' already exists.`）。與 plan Task 9 預期完全相同；13.0 s 與 P2-5 審查時的 13.5 s 同量級，每次 Save 多一次 `fsync` 沒有拖慢套件 |
| 焦點模組 | `$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller -v` | `Ran 301`, `OK (skipped=6)`；6 個 skip 全是 POSIX-only 權限測試；8 個 Windows-only 測試（`test_a_read_only_file_is_refused_with_the_in_place_verdict`、`test_a_file_held_open_by_another_handle_is_kept`、`test_save_of_a_read_only_package_gives_the_old_message`、`test_save_of_a_package_held_open_keeps_it`、`test_save_of_a_hidden_package_replaces_it_and_drops_the_attribute`、`test_read_only_old_package_is_refused_and_leaves_no_temporary_file`、`test_rename_of_a_package_held_open_by_another_program`、`test_rename_of_a_read_only_package_is_refused_with_the_save_message`）全部 `ok`，未 skip |
| shuffle | `$PY $SP\f3review_tools\shuffle_harness.py 7 11 23` | 三個 seed 皆 `ran=1248 failures=0 errors=1 skipped=7 ['test_case_only_rename_still_renames']` |
| fixtures | `git show HEAD:client/tests/fixtures/translation_golden.json \| sha256sum`；`... dictionary_entries_trace.json` | `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`、`f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`，與要求相同 |
| 受限檔案 | `git diff main...HEAD --stat -- client/locales client/braille scripts vendor`；`git show main:client/braille/tables/__init__.py \| sha256sum` vs `HEAD:` | diff 空；`__init__.py` 兩邊皆 `f4fffa2f…ee6a58`（byte-identical） |
| msgid | `$PY -I $SP\f3review_tools\msgid_scan.py client`（AST 掃 `_`／`N_`，同 P2-5 工具）；`grep -c '^msgid ' client/locales/zh_TW/LC_MESSAGES/dotexpress.po`；`git diff main...HEAD -- client ':!client/tests' \| grep -E '^\+.*\b(N_\|_)\('` | `source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c`（與 plan Task 0 相同）；po 354（353 + header）；production diff 無新的 gettext 呼叫（grep exit 1） |
| app data | `ls client/dictionary client/workspace client/config.json` 於套件後 | 三者皆不存在；`git status --short` 空（git-ignored 的 `braille/liblouis.dll`、`braille/liblouis/`、`braille/louis_helper.py`、`mathcat/` 為 Task 0 複製的 build 產物，`!!`） |
| KNOWN BUG 標記 | `git grep -n "KNOWN BUG" -- client/tests` | `P1-3 ... defect 3` 無；defect 4（`test_gui_document_flows.py:2465`）與 P1-4／P2-2 標記仍在；兩個翻掉的測試註解寫明「Was the KNOWN BUG test of P1-3 known defect 3 ... fixed by F-3」 |
| 實作 = plan dry run | `git show fa888ff:<path> \| sha256sum`（5 個檔）；`git rev-parse <commit>:client`（7 個 commit） | 5 個 sha256 與 plan「Dry Run」一致；7 個 `HEAD:client` tree id（`cc219319`、`d7fdb80a`、`5a370f05`、`5fb5a653`、`18d5cecf`、`d79139ec`、`3cdcf638`）與 plan「Expected Counts」逐一相同 |
| merge 乾淨 | `git diff fa888ff 35a0acc -- <F-3 的 8 個 client 檔>` vs `git diff $(git merge-base fa888ff main) main -- <同>` | 兩者內容相同（只有 index 雜湊不同）：merge 只帶入 `main` 對 `gui.py:11` 的一行 import 變更（`adapters.translation.contracts` → `conversion.contracts`），沒有衝突殘留；`git diff --stat 4953772 35a0acc -- client` = 10 files, +964/−99 |
| red-first 重放 | 對每個實作 commit：`git archive <commit> client` 到 scratch，再以 `git show <parent>:<production 檔>` 覆蓋 4 個 production 檔與模型檔，跑該 commit 的測試模組 | Task 2（`0197522` vs `d9197dc`）：13 個 ERROR（含 A11 的 4 個 subtest，`AttributeError ... write_bytes_atomically`）；Task 3（`9618e00` vs `0197522`）：11 個 FAIL/ERROR（含 B7 四個 subtest、B1 兩個 subtest）；Task 4：3 個 FAIL；Task 5：9 個 FAIL；Task 6：5 個 ERROR。每一步新測試在前一步的 code 上都是紅的；其餘測試綠 |
| 自套 mutant（15 個） | `$PY -I $SP\f3review_tools\mutants.py D:\workspace\DotExpress-f3\client $SP\f3review`（副本 `$SP\f3review\client`，不在 repo 內） | 13 個被抓到、2 個存活：`r7-staged-write-no-flush`（等價 mutant，見第 4 節）、`r12-import-breaks-on-failure`（真實缺口，M-2）。表見第 4 節 |
| NTFS 別名探測 | `$PY -I -X utf8 $SP\f3review_tools\ntfs_alias.py <D:\workspace\.f3review_ntfs_probe>`、`ntfs_alias2.py`（24 組名稱對；每組先建 `a.dep`，再 `os.replace(tmp, b.dep)`，看目錄剩一個還是兩個項目；探測完刪除） | NTFS 只把 `alpha`／`Alpha` 視為同一檔（且新項目取**新**拼法 `Alpha.dep`，與 spec 表格一致）；`Straße`／`STRASSE`／`Strasse`／`straẞe`、`ı`／`I`、`İ`／`i`、`ſ`／`s`／`S`、U+212A／`k`／`K`、`ﬁle`／`file`、NFD／NFC `é`、U+2126／`Ω`、U+212B／`Å`、`ǅ`／`Ǆ`／`ǆ`、`ᲀ`／`в`、Cherokee、`µ`／`μ` 在 NTFS 上全部是不同檔。**沒有任何一組「NTFS 相等但 `casefold()` 不等」**；反方向（casefold 相等、NTFS 不同）有 13 組，全部會被對話框當重複拒絕（安全方向）。`C:` 同結果 |
| GUI 結果稽核 | 讀 `D:\dxtest\auto18-f3.log`、`auto18-f3.try1.log`、`auto19-f3.log`、`auto20b-f3.log`、`auto21-f3.log`、`auto21-f3.try1.log`、`auto30-f3.log`–`auto33-f3.log`；`sha256sum D:\dxtest\N-f3\DotExpress.exe` | exe `c3f7b006…cdd8cfd`，48,732,768 bytes，與 auto-results 相同；每一項的訊息字串、清單、`diff: {}`、`tmp: []`、`attrib` 輸出都與 auto-results 逐字相符（細節見第 5 節）。本次沒有重跑 GUI、沒有結束任何程序 |
| py_compile | `$PY -m py_compile documents/workspace.py documents/workspace_service.py shared/atomic_write.py gui.py tests/windows_file_handles.py` | 通過 |
| 未執行 | item 34（磁碟滿 VHD）、真實 7-Zip、POSIX-only 測試（A9、B9 等 6 個）、實作者的 15 個 mutant 工具（未 commit；以本記錄的 15 個替代） | 標為未驗證 |

## 結論

**Ready。** 兩個優先 2 缺陷在目標平台上確實修掉：Save／Add／Import／default 文件／Export as DEP 全部經由同資料夾的 `.tmp` + `fsync` + `os.replace`，我推演的每一個失敗分支（任一行例外、兩步之間當機、`os.replace` WinError 5／32、AV 持有、磁碟滿、lone surrogate、唯讀／隱藏／ACL）都以「原檔 bytes 不變或仍不存在、`.tmp` 清掉（或留下但 `*.dep` 永不匹配）」收尾；一般與只改大小寫的 Rename 都走 `move_document_package`，任何失敗只留下舊包與未變的 controller；唯讀包被拒的判決與 Save 一致；UI 邊界的 `except Exception` 讓 Close 不再靜默失敗。Windows-only 測試在真實 NTFS 上執行且真的走到 share mode；每一步 red-first 可重放；plan dry run 的 5 個檔案雜湊與 7 個 tree id 與實際 commit 逐一相同；merge `main` 只帶入 P2-5 的一行 import。沒有 Critical，沒有 Important；7 個 Minor 都不要求改 production code 才能合併（M-1 是既有、spec 已列為 out of scope 的路徑，但 F-3 之後防護只需三行，建議排進下一個 fix task）。

## 1. 資料安全：每條路徑在 Windows NTFS 上的逐步推演

### 1.1 `write_bytes_atomically`（`client/shared/atomic_write.py:109-116` → `_write_atomically` `:63-90`）

步驟：`ensure_writable(destination)`（`:29-37`：存在且 `os.access(W_OK)` 為假 → `PermissionError(EACCES, ..., str(destination))`，文字與舊 `open("w+b")` 的 `[Errno 13] Permission denied: '<pkg>'` 相同，測試 A7／A10／B5／B6 釘住精確字串）→ `_open_temporary_file`（`:40-52`：`.<name>.<16 hex>.tmp`，`os.open(O_WRONLY|O_CREAT|O_EXCL|O_BINARY, 0o666)`，opener 在檔案存在的那一刻記錄 `temporary_path`）→ `write(stream)` → `flush` → `fsync` → `with` 結束關檔 → POSIX `chmod` → `os.replace` → `installed = True`；`finally`：未安裝且有 tmp 就 `unlink(missing_ok=True)`（`suppress(OSError)`）。

逐分支：
- `ensure_writable` 拋 → 什麼都沒建（B5、B6、A7、A10 斷言 listing 只有原包）。
- `os.open` 失敗（目錄不可寫、磁碟滿到連目錄項都建不出）→ `temporary_path` 仍為 `None`，`finally` 不動作，原包未動；訊息會指名 `.tmp` 路徑（F-2 同款、F review §2 已記）。
- `write` 中途例外（`UnicodeEncodeError`、`ENOSPC`、`KeyboardInterrupt`）→ `with` 先關檔（Windows 下 unlink 需要 handle 關閉，順序正確）→ `finally` 刪 tmp → 原包 bytes 不變（A3、A5、B1、B2 釘住，B1／B2 先 `load_document_package` 再比 bytes）。`ZipFile.__exit__` 在例外時仍寫 central directory 到 **tmp**，不再碰原包——這正是 spec「Today's Save under faults」三個案例被修掉的機制。
- 當機／斷電在 `fsync` 之前 → tmp 可能為空或半截，原包完整；在 `fsync` 之後、`os.replace` 之前 → tmp 完整但未安裝，原包完整；`os.replace`（`MoveFileExW(MOVEFILE_REPLACE_EXISTING)`）是單一目錄項操作，NTFS journal 保證不會出現「零個包」或「截斷的包」（推理，NTFS metadata journaling）。留下的 `.tmp` 由 `glob("*.dep")` 排除（B11、GUI startup test）。
- `os.replace` 失敗：目標被任何 handle 開著（四種 share mode 都是 `[WinError 5]`，A11／B7 在真實 handle 上驗證）、目標唯讀（被 `ensure_writable` 先擋）、目標是目錄（`_block`，既有 GUI 測試）、AV 正好持有 **tmp**（`[WinError 32]`，此時 `unlink` 也會失敗並被 suppress → 留下 `.tmp`，spec 表格已列，item 33 二十次切換未出現）→ 全部回到「原包不變」。
- `fsync` 失敗（`EIO`）→ 同 write 失敗分支。
- umask／權限：`0o666` 交給 kernel 套 umask（F-2 決定，A15 守住）；Windows 新檔取資料夾繼承 ACL，隱藏／系統屬性、顯式 ACE、ADS、建立時間不保留（D11 已列；B8 與 GUI item 32 證實隱藏包現在可存且屬性消失）。`os.access(W_OK)` 在 Windows 只看唯讀屬性、不看 ACL（spec Risks 已列）。

### 1.2 `save_document_package`（`client/documents/workspace.py:70-89`）與各 caller

| 路徑 | 推演 | 釘住 |
| --- | --- | --- |
| Save（`workspace_service.py:79-86`，每個文件動作與 Close 前） | 記憶體先更新（契約不變）→ 1.1；失敗 → 記憶體有編輯、磁碟原包、訊息、動作中止 | C save-failure、D save／close 測試 |
| Add／default（`:88-90`） | 1.1 然後 `add_document`；失敗 → 不加入、磁碟沒有新檔（若該名稱已有檔則不變） | 既有 `test_add_write_failure...`、新 `test_add_failure_that_is_not_an_os_error...` |
| Import（`:92-109`） | 逐份 1.1，任何 `Exception` 變 issue、`continue`；已寫好的仍加入 | `test_import_files_reports_any_save_error_as_an_issue`（但見 M-2） |
| Export as DEP（`formats.py:90-94`） | 同 1.1 於使用者選的路徑；唯讀目標 `[Errno 13]` 與舊相同；隱藏目標現在會被取代 | 無新測試（spec 說 same messages；推理） |
| 啟動載入（`workspace.py:258-268`） | `glob("*.dep")` 純 Python 比對，`.x.dep.<rnd>.tmp` 永不列出；Save 不再能產生壞包 | B11、GUI startup test；mutant r14（tmp 以 `.dep` 結尾）被 4 個測試抓到 |
| Delete／Delete All | 未改 | — |

### 1.3 `move_document_package`（`client/documents/workspace.py:132-193`）

步驟 0 `files.ensure_writable(old_path)`（唯讀舊包 → `[Errno 13] ... '<old>'`，什麼都沒建；B12、B13、GUI read-only 測試、item 31）→ 1 `temporary_path(new.parent, new.name)` 建空 staged → 2 `files.write(staged)`（`open("wb")` 覆寫該空檔、`ZipFile`、`flush`、`fsync`；失敗 → 刪 staged、raise）→ 3 若舊包存在：建空 aside、`os.replace(old, aside)`（失敗 → 刪 staged 與空 aside、raise；舊包未動）→ 4 `copy_permissions`（Windows no-op）、`os.replace(staged, new)`（失敗 → `os.replace(aside, old)` 還原、刪 staged、raise）→ 5 刪 aside（失敗忽略）。

- 零個包的視窗只在 3 與 4 之間（兩次同目錄 rename，毫秒級；F review M-2、spec Risks 已列，現在一般改名也適用）。當機在 4 之後、5 之前 → `gamma.dep` + `.beta.dep.<rnd>.tmp`，下次啟動只列 gamma，正確。
- 兩個包：不可能。步驟 4 之前 `new_path` 若已有第三個檔會被 `REPLACE_EXISTING` 覆寫（見 M-1，既有）。
- 截斷的包：staged 在 `fsync` 後才安裝；舊包只被 rename，從不被寫入。
- 還原也失敗（4 的 except 內 `replace(aside, old)` 失敗）→ 舊包留在 aside `.tmp`，記憶體仍是舊名；若它是開啟中文件，下一次 Save 從記憶體重寫；否則下次啟動少一份（spec Risks「Restore failure」）。
- 一般改名的別名安全（spec D5）：舊名在步驟 3 離開目錄後才安裝新名，所以 NTFS 把 `old` 與 `new` 視為同檔也不會刪錯（F-1 defect 1 的機制）。探測結果（驗證表）顯示本機 NTFS 只有 ASCII 大小寫對會別名，`casefold()` 漏掉的方向一組也沒有；反方向 13 組由對話框拒絕。所以「rename 到另一份文件的大小寫變體」在清單內的文件上不可能覆寫（`session.py:52-54` casefold 檢查；F-1 測試釘住）。
- Windows share mode（`test_rename_of_a_package_held_open_by_another_program`，真實 handle）：read／read+write → 步驟 3 `[WinError 32] ... '<old>' -> '<aside>'`，只剩舊包（item 30 在 packaged build 證實）；read+delete／read+write+delete → 改名完成（aside 的 unlink 走 POSIX delete semantics，項目立即消失）。
- `ensure_writable` 與 `os.replace` 之間檔案被設唯讀 → 步驟 3 仍成功（rename 只需 delete 權）、步驟 5 刪不掉 → 留下唯讀 `.tmp`（spec D5 第三點已承認；只會發生在競態）。

### 1.4 `PackageFiles.write`（`:102-107`）

`open(path, "wb")` 對 `NamedTemporaryFile` 預建的空檔是 truncate 重開，不是 `O_EXCL`；但該名稱是隨機、私有、剛建立的，F-1 既有設計（F review M-3／M-4 的 follow-up）。`fsync` 在 `with` 內、關檔前，順序正確；B14 在 `fsync` 當下以 `os.fstat` 斷言長度等於完整封存檔（F-1 I-1 的教訓有帶進來）。

## 2. 改名路由

- `rename_document`（`workspace_service.py:111-123`）只剩一條路：`ValueError`（同名）→ 取 source → `move_document_package` → `controller.rename_document`。case-only 分支與 `save_document_package` + `unlink` 都移除；mutant r8（先改記憶體再搬磁碟）被 10 個測試抓到，r10（先安裝再移走舊包，spec 否決的替代方案）被 17 個抓到。
- 名稱檢查仍在 GUI（`gui.py:649` `document_name_exists`，casefold，Rename 以 `exclude_name` 放行自己）。`normalize_base_name`（`shared/name_validation.py`）拒絕結尾 `.`／空白、控制字元、Windows 保留裝置名，所以「trailing dot/space」在 `.dep` 之前不會出現，`CON.dep` 類也進不來。NFC／NFD 不正規化：`é`（NFC）與 `é`（NFD）在 controller 與 NTFS 都是兩份不同文件，兩邊一致，不會互相覆寫（探測證實）。
- 唯一會覆寫另一個檔的情況是 M-1：目標名稱的 `.dep` 在磁碟上存在、但不在清單裡（啟動時選擇保留的 invalid 包），Rename／Add／Import／default 文件都會以 `REPLACE_EXISTING` 蓋掉它；既有行為，spec Out of Scope 只提 Add／Import。

## 3. UI 邊界（`client/gui.py:596-602`、`:625-628`、`:757-760`；`workspace_service.py:104`）

- 三個 handler 與 import 迴圈從 `OSError` 放寬到 `Exception`，模板與 caption 不變（msgid 353 同集合）；`BaseException` 仍傳播。
- controller 一致性：Save 記憶體先改（契約，`test_save_failure_keeps_the_package_and_updates_memory` 釘住）；Add 寫成功才 `add_document`；Rename 搬成功才 `controller.rename_document`；Import 只 `add_documents(saved)`。三者在任何 `Exception` 下記憶體與磁碟的關係都和 `OSError` 時相同。
- `_on_close`（`:956-969`）：`_save_open_document_with_feedback()` 回 `False` → `CanVeto()` 才 `Veto()`；非 `OSError` 以前逃出 handler（wx 會印到 stderr、`evt.Skip()` 不會呼叫、視窗不關、沒有訊息），現在有訊息且 veto。`CanVeto()` 為假（登出／關機）時兩種情況都會跳 modal 訊息，與舊的 `OSError` 行為相同，不是回歸。
- 程式錯誤被包成「儲存文件失敗：<str(exc)>」而沒有任何 log（M-3）；packaged build 沒有 console，這是唯一的診斷管道。`dialog.py:494` 的 F-2 先例同樣沒 log。
- 使用者可見差異只在 `{error}` 內文字（spec D6、D12 已列，GUI item 19／30／31 證實）與 Close 現在會被 lone surrogate 的訊息擋住（M-4）。

## 4. 測試品質

### 4.1 翻掉的測試與 F-1 guard

- `test_rename_unlink_failure_propagates_and_leaves_both_packages`（service）→ `test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state`：注入改為 `_FailingReplacePackageFiles(source_name="alpha.dep")`（字串比對 `Path(source).name`，F-1 D5），斷言 listing `["alpha.dep"]`、bytes、state 不變、例外文字含 `alpha.dep`。red-first 重放證實在 Task 5 之前 FAIL。
- GUI 版 `test_rename_unlink_failure_leaves_both_packages_and_state` → 同名新測試，以 `frame._workspace_service = DocumentWorkspaceService(..., package_files=_FailingReplacePackageFiles(source_name="beta.dep"))` 注入（GUI 模組自己定義 injector，避免 unittest 重複收集 service 測試）；斷言兩個事件（對話框、錯誤框含 `beta.dep`）、listing、bytes、state。
- `test_regular_rename_does_not_use_package_files`（`_UnusablePackageFiles`）→ `test_regular_rename_moves_the_old_package_aside_before_installing`：`_RecordingPackageFiles` 斷言 `replace` 恰好兩次、順序 `alpha.dep -> .alpha.dep.*.tmp`、`.gamma.dep.*.tmp -> gamma.dep`。這是 D5 的路由 guard，在 Linux 上也能抓到「換回 write-then-unlink」（mutant `regular-rename-write-then-unlink` 8 個測試抓到；我的 r10 17 個）。
- `_block` 改用途：spec D8 正確指出 `os.replace(dir, file)` 在 Windows 會成功，所以 move-aside 失敗不再用 `_block`；`_block("gamma")` 仍用於安裝失敗（`test_rename_write_failure_propagates_and_keeps_state` 加了 listing 斷言，確認 staged 與 aside 都清掉）。

### 4.2 Fault injection 的真實性

- `os.replace`／`os.access`／`os.fsync` 以 `patch("os.xxx")` 在呼叫時查找，不碰 `documents.*` 全域，GUI 測試用 `wx_stub` 模組副本也不受影響。
- `writestr` 第二個成員拋 `ENOSPC`（B2）模擬磁碟滿：對 `save_document_package` 而言與真實 `ENOSPC` 的差別只在例外來源點，清理路徑相同；真正的磁碟滿（item 34）仍未做。
- Windows-only（`tests/windows_file_handles.py`）：`hold_open` 真的 `CreateFileW(GENERIC_READ, share, OPEN_EXISTING)`，同程序 handle 也受 share 檢查；`test_rename_of_a_package_held_open_by_another_program` 以 delete sharing 有無區分結果（32 vs 完成），證明 share 參數確實到達 kernel。A11／B7 四種 mode 都是 `[WinError 5]`，本身無鑑別力但釘住 Q1。handle：`release` 冪等、`addCleanup` 保底，subTest 迴圈每輪 `finally: release()`，沒有外洩；`make_read_only` 的 clean-up 在 `TemporaryDirectory.cleanup` 之後註冊所以先跑（LIFO），三個測試類都用 `addCleanup` 而非 `tearDown`，順序正確。POSIX：模組層只有 `ctypes.c_void_p(-1).value` 與常數，`_kernel32()` 延後載入，`skipUnless(os.name == "nt")` 全部正確。
- `test_import_files_reports_any_save_error_as_an_issue` 以 `patch.object(workspace_service, "save_document_package")` 注入，失敗的是**最後一份** `delta`（plan 刻意為之，讓紅燈顯示舊行為更糟）；代價是「失敗後批次繼續」沒有被釘住（M-2）。

### 4.3 自套 mutant（scratchpad `f3review\client` 副本；`r7` 以外全部被抓到）

| # | mutant | 結果 |
| --- | --- | --- |
| r1 | move-aside 失敗時不刪 staged | 抓到 4 |
| r2 | 安裝失敗時不還原 aside | 抓到 6 |
| r3 | 安裝成功後永不刪 aside | 抓到 13 |
| r4 | `ensure_writable` 查 `R_OK` | 抓到 6（含真實唯讀檔的精確字串） |
| r5 | move 檢查 `new_path` 而非 `old_path` | 抓到 4 |
| r6 | staged 寫入不帶 pending metadata | 抓到 4 |
| r7 | `PackageFiles.write` 拿掉 `stream.flush()`（保留 `fsync`） | **存活，但等價**：`ZipFile.close()` → `_write_end_record` 結尾本來就 `self.fp.flush()`（`Lib/zipfile/__init__.py:2133`），所以 `fsync` 當下 fd 已有完整封存檔；B14 的 `fstat` 斷言因此仍成立。production 的 `flush()` 是多餘但無害（M-5） |
| r8 | service 先 `controller.rename_document` 再搬磁碟 | 抓到 10 |
| r9 | helper 在 `os.replace` 之前就設 `installed = True` | 抓到 4 |
| r10 | 先安裝再移走舊包（spec 否決的替代） | 抓到 17 |
| r11 | `save_document_package` 不先 `mkdir` | 抓到 87 |
| r12 | `import_files` 失敗後 `break` 而非 `continue` | **存活**（M-2） |
| r13 | helper tmp 名稱不帶前導點 | 抓到 4 |
| r14 | helper tmp 以 `.tmp.dep` 結尾（啟動會列出） | 抓到 4 |
| r15 | `save_document_package` 吞掉例外後回傳 | 抓到 16 |

實作者 plan Task 7 的 15 個 mutant（含 `no-fsync`、`no-flush`、`staged-write-nested` 等）與我的集合重疊 5 個、互補 10 個；其輸出未 commit，我沒有重跑，以本表替代。

## 5. GUI 結果稽核（`auto-results.md` vs `D:\dxtest\*.log`，未重跑）

- exe：`D:\dxtest\N-f3\DotExpress.exe` sha256 `c3f7b006…cdd8cfd`、48,732,768 bytes，與記錄相同；記錄中的 `HEAD:client d79139ec…` = `fa888ff`（merge 之前的 build，merge 只多一行 import，可接受）。
- 19 r／rw：log 顯示 `locked` 兩次（lock.py 真的開著 handle）、兩種 share 都是 `儲存文件失敗：[WinError 5] 存取被拒。: '…\.alpha.dep.<16 hex>.tmp' -> '…\alpha.dep'` 且 `'no name dialog'`（存檔先失敗）、`diff: {}`、files 無 `.tmp`、解鎖重啟後清單與雜湊不變。證明 Q1（rw 也擋）。
- 20／20b：`[Errno 13] Permission denied: '…\alpha.dep'`／`'…\Alpha.dep'`、`attrib` 顯示 `R`、`close` 顯示同訊息 + `STILL RUNNING -> killed`（F-W10 仍在，腳本自己結束該資料夾下的程序）。
- 21：10 次 `ok`，每次 listing 只有一個拼法 + `new.dep`，`content same (ignoring name): True`。try1 的 `SetForegroundWindow` 失敗在第一次改名**之前**（log 只有 `start:` 一行），app 未受操作，判定合理。
- 18：try1 的 log 顯示 `add ALPHA` 後錯誤框仍在（`['錯誤']`），接著 `menu_select` 拋 `ElementNotEnabled`；重跑 log 完整且 `disk diff: {}` 兩次。記錄的解釋（自動化時序）與 log 一致；也看得到 F-W9（第二次對話框按鈕是 `OK`/`Cancel`）。
- 30：lock 真的在（`locked`），兩種 share 都是 `[WinError 32] …: '…\beta.dep' -> '…\.beta.dep.<rnd>.tmp'`，`files` 無 `gamma.dep`、`tmp: []` 是在 `taskkill` lock **之前**量的；重啟後 `beta text: 'beta body'`。證明 defect 3 修好。
- 31：`attrib +r` 後 `beta→gamma` 與 `beta→Beta` 都是 `[Errno 13] Permission denied: '…\beta.dep'`、`tmp: []`、`attrib` 仍 `R`。證明 Q2 兩種改名都拒。
- 32：`attrib before: A   H` → 切換無訊息、`attrib after: A`、磁碟內文 `'alpha typed while hidden'`、重啟後相同。證明 D11。
- 33：`Defender real-time protection: True`，20 行 `ok [] []`，`failures: 0`，最終內文 `alpha edit 19`／`beta edit 20`。
- 腳本：`rerun.py` 只替換 `OLD_EXE`／`OLD_DIR` 兩個字面值（各需恰好一次）並以原 `__file__` 執行，03 的腳本未改；`f3gui.py` 重用 `dx.py`／`docs.py`／`lock.py`；`docs.ws_state` 比對 zip 成員雜湊而非整檔 bytes（時間戳記會變），這是正確的比對方式。`dx.kill_under` 以 `$_.Path -like '<prefix>*'` 只結束測試資料夾下的 exe。
- 結論：auto-results 的每一句話都有 log 依據，證明了它宣稱的事；沒有需要重跑的項目。

## 6. 文件準確性

- spec「Corrected after planning」1–9 兩種語言都在（`_zh-TW.md:23-31`）；Q1 accept／Q2 refuse 明確寫成「由協調者採用建議的預設決定；使用者可在合併前推翻」（`:390`、`:392`）。
- spec D1–D13 與實作逐條相符（含 D4 的 `include_pending_metadata=True`、D8 的 injector 錯誤文字、D13 的兩套 tmp 命名）；「Design per File」列的函式與 docstring 都在；「Not changed」的檔案確實未動。
- plan「Expected Counts」的 `Ran` 與 tree id 全部命中；「Dry Run」的 5 個 sha256 命中；Task 9 預期 `Ran 1248`, `FAILED (errors=1, skipped=7)` 命中。
- F-W10 明確列為 out of scope（spec `:17`、D12、Out of Scope），且 D12 表格把 trigger set 的變化寫清楚；GUI 20／20b 記錄「仍在、不在範圍」。
- 人工剩餘：auto-results「仍需人工」列 34 與真實 7-Zip，與 spec 一致。
- 小缺口：spec Out of Scope 的「F-1 D8 for Add」只提 Add／Import，Rename 與 default 文件同樣會覆寫磁碟上有、清單裡沒有的 `.dep`（M-1）。

## 7. 與 `main`（P2-5）的合併

P2-5 自 `d4a7aa1` 起只動 `gui.py:11` 一行 import（`conversion.contracts`），離三個 `except` 很遠；`documents/`、`shared/atomic_write.py`、六個測試檔 `main` 都沒碰。merge diff 與 `main` 側 diff 內容相同，沒有手動解衝突的痕跡；merge 後 P2-5 的失敗消失、只剩 F-W6。語意上 F-3 的程式路徑（存檔、改名）與 P2-5 的轉換管線無交集；`test_gui_document_flows` 以 `fake_translate` 隔離轉換。無互動。

## 發現清單

### Critical

無。

### Important

無。

### Minor

**M-1 Rename／Add／Import／default 文件會覆寫磁碟上存在但不在清單裡的 `.dep`**（`client/documents/workspace.py:180-183`、`client/documents/workspace_service.py:88-90, 100-107`）
- 情境：啟動時 `bad.dep`（例如使用者想手動救回的壞包）選「保留」→ 它不在 controller 裡；之後把 `beta` 改名為 `bad`、Add `bad`、Import `bad.txt`，或清單空時 app 自建 `new` 而磁碟有保留的壞 `new.dep` → `os.replace(staged, bad.dep)` 以 `REPLACE_EXISTING` 蓋掉它，沒有訊息。既有行為（F-3 之前 `CREATE_ALWAYS` 一樣蓋），spec Out of Scope 只寫 Add／Import，F review 優先 4 已列。
- 修法（下一個 fix task，三行）：`move_document_package` 在步驟 3 之後、安裝之前 `if files.exists(new_path): raise FileExistsError(...)`（此時舊包已離開目錄，`exists` 為真就一定是第三個檔；except 分支會把舊包還原）；`save_document_package` 給 Add／Import 的呼叫端在 `create_document`／`import_files` 前以 `package_path.exists()` 拒絕（需要一個新 msgid 或沿用 `Document "{name}" already exists.`）。順便把 spec Out of Scope 那一條補上 Rename 與 default 文件。

**M-2 「Import 某份存檔失敗後批次繼續」沒有被釘住**（`client/tests/test_workspace_service.py:827-845`）
- 情境：mutant r12（`continue` → `break`）在 301 個測試下存活：`test_import_files_reports_any_save_error_as_an_issue` 讓最後一份 `delta` 失敗，`test_import_files_lists_load_issues_before_save_issues` 同樣 `_block("delta")`，之後沒有別的文件可證明迴圈還在走。spec D9「the batch continues」目前只靠閱讀。
- 修法：加一份 `epsilon`（或讓 `beta` 失敗、斷言 `delta` 已存且已加入）。

**M-3 UI 邊界吞掉所有 `Exception` 但不記 log**（`client/gui.py:444-450` `_show_file_error`；`:596-602`、`:625-628`、`:757-760`）
- 情境：D9 的用意是讓 `UnicodeEncodeError` 有訊息，但 `AttributeError`／`TypeError` 之類的程式錯誤現在也只剩一個「儲存文件失敗：'NoneType' object has no attribute …」訊息框；packaged build 沒有 console，`gui.log`（`logger = get_logger("dotexpress.gui", "gui.log")`，`gui.py:97`）裡也不會有 traceback，使用者回報時無從追查。`dialog.py:494` 的 F-2 先例同樣沒 log。
- 修法：`_show_file_error` 內加 `logger.error("%s", message.format(error=error), exc_info=error)`（或在三個 except 內 `logger.exception`）；不改任何 msgid。

**M-4 記憶體裡的 lone surrogate 會讓 Save 永遠失敗、Close 永遠被 veto**（`client/gui.py:956-963`；spec Risks「Broader catch」已承認）
- 情境：從壞的剪貼簿貼進一個 `\ud800`（不可見），之後每個會先存檔的動作與 Close 都跳 `'utf-8' codec can't encode character '\ud800' …`，使用者找不到那個字元，只能強制結束並丟掉上次成功存檔之後的編輯。F-3 之前更糟（壞包 + 靜默），所以是改善；但它和 F-W10 是同一類「存檔失敗就出不去」的 UX 債。
- 建議（follow-up，與 F-W10 一起決）：`prepare_document_for_save` 或 `_write_package` 以 `text.encode("utf-8", "replace").decode()` 把 lone surrogate 換成 U+FFFD（不要用 `surrogatepass`，loader 的 `decode("utf-8")` 會壞），或 Close 時提供「不存檔關閉」。

**M-5 `PackageFiles.write` 的 `stream.flush()` 多餘**（`client/documents/workspace.py:106`）
- `ZipFile.close()`（`with` 結束）已在 `_write_end_record` 末尾 `self.fp.flush()`，所以 `fsync` 看到的本來就是完整封存檔；mutant r7 因此等價存活。不需要改；只記錄以免下次有人把「no-flush 沒被抓到」當成測試缺口。`_write_atomically` 的 `flush` 對一般 `write` callback（CSV writer 不 flush）仍是必要的，A6 抓得到。

**M-6 驗證債：item 34（磁碟滿）與真實 7-Zip 仍未做**（auto-results「仍需人工」）
- `ENOSPC` 只有單元層模擬（A3 在 callback 內 raise、B2 patch `writestr`）；真實磁碟滿時 `os.open` 可能在建 tmp 就失敗（訊息指名 `.tmp` 路徑，原包不變）或在 `fsync`／`close` 才回報（同樣清理）；兩種我都只推理。7-Zip 的 share mode 決定落在 19 r 或 19 rw，但 F-3 之後兩列結果相同，所以只影響記錄不影響結論。
- 建議：在 release note 前補做 34 一次（VHD 幾 KB 可用空間），記錄 `{error}` 文字。

**M-7（推理，非出貨平台）POSIX 上 `_write_atomically` 不 `fsync` 目錄**（`client/shared/atomic_write.py:85`）
- ext4／APFS 上 rename 後立刻斷電，目錄項可能回到舊檔（資料不會壞，只是回到上一版）；Windows NTFS 無此問題。F-2 同款，F review 當時也沒要求。只記錄。

## 建議的下一步

1. 合併 F-3（本記錄沒有阻擋項）。
2. 一個小 `test:`／`fix:` commit 收 M-2（import 測試）與 M-3（`_show_file_error` 加 log）；不動 msgid。
3. 下一個 fix task 把 M-1 的三行 guard 和 F review M-2（啟動時掃孤兒 `.*.dep.*.tmp`）一起做——兩者都在 `move_document_package` 周邊，且 F-3 之後一般改名也會留下該類孤兒。
4. F-W10 + M-4 一起做 UX 決策（跳過未修改文件的寫入、失敗後可不存檔關閉、lone surrogate 的處理）；需要新字串。
5. 人工補做 item 34 與真實 7-Zip，結果附回 `auto-results.md`。

## 修正記錄

在同一分支 `fix/f3-dep-atomic-write` 上處理（未 merge 進 `main`、未 push）；本記錄連同下列 commit 一起提交。

| 發現 | 處理 |
| --- | --- |
| M-1 | 未處理（既有行為，spec Out of Scope）；建議歸屬下一個 fix task，與 F review M-2 的孤兒 `.*.dep.*.tmp` 啟動回收一起做（都在 `move_document_package` 周邊）。 |
| M-2 | `045417a` `test: pin that a failed import save does not stop the batch (F-3 review M-2)`：新增 `test_import_files_continues_after_a_failed_save`，讓**第一份** `beta` 存檔失敗（`_block("beta")`），斷言其後的 `delta`、`epsilon` 仍寫入磁碟並加入清單。在 scratchpad 副本（`$SP\f3fix\client`）套 r12（`continue` → `break`）後此測試失敗（`AssertionError: Lists differ: [] != [Document(name='delta', ...)]`，`Ran 37`, `FAILED (failures=1)`）；真實 code 上 `tests.test_workspace_service` `Ran 37`, `OK`。 |
| M-3 | `b73a950` `fix: log unexpected document save errors (F-3 review M-3)`：Save／Add／Rename 三個 `except Exception` 改呼叫新的 `_show_document_save_error`，非 `OSError` 時先 `logger.error(..., exc_info=error)` 把 traceback 寫進 `gui.log`，再顯示原本的訊息框。只記非 `OSError`：鎖定、唯讀、磁碟滿等是預期的環境狀況，訊息框已含路徑與系統錯誤，重試時只會在 log 堆出相同 traceback。放在 save 專用 helper 而非 `_show_file_error`：dual view 的 handler 本來就 `logger.exception` 全部錯誤（放進 `_show_file_error` 會重複記錄），網站 handler 的 `webbrowser.Error` 是預期的非 `OSError`。msgid 仍 353（log 文字不翻譯；`xgettext` 重抽 354 行含 header）；`.po`／`.mo` 未動。新增 4 個測試（3 個 `assertLogs` 斷言 `exc_info` 與 traceback、1 個 `assertNoLogs` 守住 `OSError` 不記）；先在原 `gui.py` 上 3 紅 1 綠，log-everything mutant 讓守門測試紅。`test_gui_document_flows` 的 `setUpModule` 加上 `isolate_file_logs("dotexpress.gui")`，與其他會讓 production code 記 log 的測試模組一致（否則 worktree 無 `client/log/` 時 `FileHandler` 開檔失敗）。 |
| M-4 | 未處理；與 F-W10 一起做 UX 決策（失敗後可不存檔關閉、lone surrogate 處理），需要新字串。 |
| M-5 | 不需處理（資訊性：`flush()` 多餘但無害，r7 為等價 mutant）。 |
| M-6 | 未處理；item 34（磁碟滿 VHD）與真實 7-Zip 仍留給使用者人工補做，結果附回 `auto-results.md`。 |
| M-7 | 未處理；POSIX 目錄 `fsync` 只影響非出貨平台，僅記錄。 |

驗證（`$PY` 與 cwd 同上）：

- 完整套件 `$PY -m unittest discover -s tests`：`Ran 1253 tests`, `FAILED (errors=1, skipped=7)`（1248 + 5 個新測試）；唯一 error 仍為 F-W6 的 `test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames`。
- fixtures：`translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`、`dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`，未變。
- 套件後 `client/log/` 不存在（測試沒有寫入真實 log）。
