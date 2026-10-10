# F-5 存檔失敗處理審查記錄

- 日期：2026-10-10
- 範圍：`fix/f5-save-failure-handling` 的 `main..fix/f5-save-failure-handling`（`main` = `918c251`；6 個 commit：`30becb7` spec、`69f153d` plan、`c87681a` lone surrogate → U+FFFD、`cc02a3d` 略過未變更文件的寫入、`9ebf7ab` 關閉時的重試／不儲存就關閉對話框與 catalog、`1cf59b1` GUI 結果）。production diff `git diff main...HEAD -- client`：10 個檔，+913／−132（`documents/workspace.py` +19／−1、`documents/workspace_service.py` +58／−1、`gui.py` +54／−8、三個 locale 檔、`tests/wx_stub.py` +11／−1、三個測試檔）。`HEAD:client` tree `640d67bf…`；Task 1／2 的 tree `01861fd4…`／`cd438c11…`，與 plan Implementation Notes 逐一相同。
- 對照：`docs/superpowers/specs/2026-10-10-f5-save-failure-handling-design.md`（含 `_zh-TW.md`，含「Corrected after planning」／「規劃後更正」）、`docs/superpowers/plans/2026-10-10-f5-save-failure-handling.md`（含 Implementation Notes：A2 測試修正、`dx.dismiss` 的發現）、`docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto-results.md` 與 `auto/`、`2026-10-09-05-f3-dep-atomic-write/review_task.md`（M-4）、`2026-10-09-06-f4-keep-invalid-bopomofo-rows/review_task.md`（格式）、`2026-10-09-03-windows-verification/auto-results.md`（F-W9、F-W10）、`AGENTS.md`（Localization）。
- 審查方式：逐行讀 3 個 production 檔的 diff 與全文、4 個測試檔的 diff、`controller.py`／`session.py`／`formats.py`／`export_coordinator.py`／`conversion_presenter.py` 的相關段落；對 saved record 的每條生命週期路徑（載入、存檔成功／失敗／略過、新增、匯入、改名、刪除、刪除全部、匯出 DEP、轉換、外部修改）逐一推演「record 說未變更但磁碟與使用者所見不同」的可能；在 Windows 11（NTFS，`D:`／`C:`）上跑完整套件與焦點模組；把每個實作 commit 的測試拿去跑其父 commit 的 production code（red-first 重放，`git archive` 到 scratchpad，不含 app data）；在 scratchpad 的 `client/` 副本上自套 35 個 mutant（`python -B`）；8 個情境探針與 NTFS mtime 粒度量測；重建 `.pot`／`.mo` 比對；稽核 `D:\dxtest\auto*-f5.log` 十三個 log 與兩個 exe 的雜湊（沒有重跑 GUI、沒有結束任何程序）。主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 在審查前後 sha256 相同；沒有啟動 source-run 的 `gui.py`。凡未能驗證的標為「推理」或「不確定」。
- 本記錄只寫檔，未 commit。

## 驗證（Windows 11 26200，`$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`，`$SP` = session scratchpad 的 `f5review\`）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| app data | 審查前：`(find client/dictionary client/workspace client/log -type f; ls client/config.json) \| sort \| xargs sha256sum > $SP/appdata_before.sha256`（4 個檔：`config.json`、`dictionary/default.csv`、`log/init.log`、`workspace/new.dep`）；審查後（完整套件與焦點模組跑完、本檔寫出後）同指令 `diff` | `app data unchanged`；`git status --short` 全程只有既有的 `client2/`、`preprocessing/`、`testdata/`；四個資料夾都在 `client/.gitignore`，未 stage 任何東西 |
| 完整套件（驗收 1） | `cd client && $PY -B -X utf8 -m unittest discover -s tests` | `Ran 1304 tests in 16.280s`, `FAILED (errors=1, skipped=7)`；唯一 error 為 `test_dictionary_name_prompt ... test_case_only_rename_still_renames`（F-W6）。與 plan Expected Counts 相同。（先在 `$SP\head`／`$SP\repo` 的 `git archive` 副本跑過：因副本沒有 git-ignored 的 `client/braille/liblouis.dll`、`louis_helper.py` 與 submodule 內容，只得 `Ran 1287`／`1291`，差額全是 liblouis／vendor 環境錯誤，故改在主 checkout 跑；測試全用暫存目錄，跑完沒有產生 `client/workspace/`、`config.json`、`log/`，見 app data 列） |
| 焦點模組（驗收 2） | `$PY -B -X utf8 -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n tests.test_atomic_write tests.test_document_controller`；`-v` 抓兩個 Windows-only 測試 | `Ran 353`, `OK (skipped=6)`；`test_unchanged_unwritable_package_saves_without_error ok`、`test_unchanged_read_only_document_blocks_neither_switch_nor_close ok`（有跑、沒被 skip）。三個 F-5 模組單獨跑 `Ran 289`, `OK (skipped=2)` |
| 副本與 commit 一致 | `git archive <commit> client` 到 `$SP\head`、`$SP\red\t1..t3`、`$SP\mut`；對 `git ls-tree -r <commit>:client` 的 209 個 blob 逐一 `git hash-object` 比對 | 209 個 blob 全部相同（`core.autocrlf=true` 讓 archive 輸出 CRLF，4 個本來就以 CRLF 入庫、與 F-5 無關的檔在加 filter 的雜湊下不同、raw 雜湊相同；F-5 的 10 個檔兩種算法都相同） |
| red-first 重放 | 對每個實作 commit：副本放該 commit 的全部檔案，再以 `git show <parent>:<production 檔>` 覆蓋（t1 覆蓋 `documents/workspace.py`；t2 覆蓋 `documents/workspace_service.py`；t3 覆蓋 `gui.py` 與三個 locale 檔），跑三個 F-5 測試模組（`-B -X utf8`） | t1（`c87681a` 的測試於 `69f153d` = `main` 的 production）：`Ran 262`, `FAILED (failures=2, errors=11, skipped=2)`，紅燈為 A1（6 個 subtest ERROR）、A2、A3、A4（2 subtest）、A5、B17、C10 共 7 個測試；改過注入器的 8 個既有測試在舊碼上仍綠。t2（`cc02a3d` 於 `c87681a`）：`Ran 283`, `FAILED (failures=14, errors=6, skipped=2)`，紅燈 13 個：B1、B4、B6、B7、B11（3 subtest）、B12、B13（2 subtest）、B14、B15b、B16（5 subtest ERROR）、C1、C2、C4；B2、B3、B5、B8、B9、B10、B15a、C3 在舊碼綠（每次都寫），與 spec Corrected 3 相同。t3（`9ebf7ab` 於 `cc02a3d`）：`Ran 289`, `FAILED (failures=9, skipped=2)`，紅燈 C5–C9、C11 六個新測試與三個翻轉（`test_close_save_failure_cancel_vetoes`、`test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks`、`test_close_asks_presenter_before_saving`）。三步都與 spec Migration Steps 一致 |
| 自套 mutant（35 個） | `$PY -B -X utf8 $SP\tools\mutants.py $SP\mut\client`（每個 mutant 跑三個 F-5 模組 `Ran 289`；跑完還原並比對 sha256；三個 production 檔還原後與 `HEAD` 的 LF 內容相同） | 31 個被抓到、4 個存活：`m04-fingerprint-mtime-only`（fingerprint 只留 `st_mtime_ns`）、`m11-rename-keeps-source-record`、`m12-delete-keeps-record`、`m13-delete-all-success-keeps-records`。四個在現行程式下都是等價 mutant（見 §3.3、M-4）。plan 列的 25 個 mutant 中我另寫對應的 `m01`（無 record 視為已存）、`m07`、`m08`（只在寫入時更新 controller）、`m09`、`m10`、`m14`、`m17`、`m19`–`m35`，全部被抓到 |
| 情境探針 | `$PY -B -X utf8 $SP\tools\probes.py $SP\head\client $SP` | P1 匯出 DEP 蓋到工作區自己的 `alpha.dep`（pending 文件）：匯出前未變更存檔 0 次寫入；匯出後成員只剩 `.txt`/`.brl`；再存一次未變更的文件 → 寫入 1 次、`alpha.meta.json` 回來（spec D3 所述）。P1b 非 pending：匯出改了 mtime、下次存檔重寫 1 次。P2 載入 `line1\r\nline2`、編輯器給 `\n`：第一次寫 1、第二次 0，磁碟 `line1\nline2`。P3 名稱含 lone surrogate：Add 與 Rename 都 `UnicodeEncodeError`，檔案與 controller 不變、沒有殘留（見 M-1）。P4 轉換把含 surrogate 的文字放進 controller：下次存檔寫 1 次、controller 與磁碟都是 `x\ufffd`；之後 Rename 的新包也是 U+FFFD。P5 改名失敗且舊包放不回去（留在 `.tmp`）：下次未變更存檔寫 1 次、`alpha.dep` 重建（when in doubt, write）。P6 外部程式換成**同大小且 `os.utime` 還原同 mtime** 的另一內容：未變更存檔 0 次、磁碟留外部版本（spec Risks 已承認；見 M-2）。P7 pending 文件忽略編輯器點字（0 次）；轉換結果為空字串 `""` 仍寫 1 次、磁碟 `braille=''`。P8 載入含 U+0000 的文字、編輯器截斷為 `ab`：寫 1 次、磁碟 `ab`（spec Out of Scope，既有行為） |
| NTFS mtime 粒度 | `$PY -B -X utf8 $SP\tools\mtime_probe.py $SP\head\client D:/dxtest`（與 `C:`）；`NtQueryTimerResolution` | 連續 200 次 `save_document_package`（同大小、含 fsync）：`D:` 平均 59.8 ms／次、`C:` 5.0 ms／次，兩個磁碟都 0 次連續相同 fingerprint，最小 mtime 差 `D:` 48.8 ms、`C:` 0.50 ms。不含 fsync 的 2000 次小寫入：`D:` 1778 次、`C:` 1535 次連續相同 mtime，最小非零差 0.503 ms。timer resolution 目前 1.0 ms（最大 15.625 ms）。結論：NTFS 的 `st_mtime_ns` 實際粒度是系統時鐘 tick（本機 0.5 ms，一般可到 15.6 ms），不是 100 ns；對 F-5 的影響見 M-2 |
| catalog（驗收 3） | `$PY -I $SP\tools\msgid_scan.py $SP\head\client`；`LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po`；`grep -c fuzzy`；`cmd /c scripts\generate-pot.bat $SP\second.pot` 後去掉 `POT-Creation-Date` 行 `diff`；`msgfmt --check -o $SP\rebuilt.mo …po` 後 `sha256sum` 與 `git show HEAD:…dotexpress.mo \| sha256sum`；`$PY -I -X utf8 $SP\tools\mo_check.py $SP\committed.mo`；AST 掃出的 msgid 集合與 `.po` 非 obsolete msgid 集合互比；`git show main:…po \| grep '^#~'` 與現在的 `#~` 行 `diff` | `source msgids: 357 sha256 7ebbbe56…26c6`（與 plan Task 4 相同）；`357 translated messages.`，`fuzzy` 0；`.po` 358 個 `msgid` 行（357 + header）、31 個 obsolete 與 `main` 逐字相同；`generate-pot exit 0`、`second template identical apart from POT-Creation-Date`；重建的 `.mo` sha256 `a4999716…ae8f5` 與已 commit 的相同（26,971 bytes）；`catalog keys: 358`，六個字串都譯出（`無法儲存文件`、`上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。`、`重試(&R)`、`不儲存就關閉(&W)`、`取消`、`儲存文件失敗：{error}`）；source 與 `.po` 的 msgid 集合互為子集（差集皆空）、沒有空 `msgstr`；`msgstr == msgid` 的只有 `DotExpress`、`DEP`、`DOCX`、`EPUB`、`PDF`、`TXT`、`BRL`、`Unicode`、`ASCII`、`SimBraille`（AGENTS.md 允許的既有術語）；`#:` 參照 `gui.py:465 gui.py:475`／`476`／`480`／`482` 與目前 `gui.py` 的行號相符、相對 `client/`、正斜線；兩個檔的 `POT-Creation-Date` 都是 `2026-10-10 12:00+0800` |
| fixtures、未動的模組（驗收 4–6） | `git show HEAD:client/tests/fixtures/translation_golden.json \| sha256sum`、`…dictionary_entries_trace.json`；`git diff --quiet main...HEAD -- client/conversion`；`git diff --stat main...HEAD -- client/tests/fixtures client/dialog.py client/documents/controller.py client/documents/session.py client/documents/formats.py client/documents/export_coordinator.py client/ui client/shared client/braille client/dictionaries` | `e67d95a1…1ccd`、`f493da52…c2cf`，與要求相同；`client/conversion unchanged`；受限檔案的 `--stat` 為空；`git diff --stat main...HEAD -- client` 正是 10 個檔 +913／−132 |
| 呼叫端（決定 C） | `grep -n "_save_open_document_with_feedback" client/gui.py` | 10 個呼叫端（`:618` 切換、`:782` 開啟、`:788` 新增、`:800` 改名、`:827` 刪除、`:856` 刪除全部、`:885` 匯入、`:918` 匯出、`:926` 匯出全部、`:954` Ctrl+E）的程式碼都沒改；diff 只動 `_on_close`。有修改且寫入失敗時仍以 `_show_document_save_error` 擋住（C3、GUI item 38 的 Ctrl+Tab） |
| wx 常數 | `$PY -c "import wx; print(wx.ID_CANCEL, wx.ID_YES, wx.ID_NO, wx.YES_DEFAULT, …)"` | wxPython 4.2.5 msw：`ID_CANCEL 5101`、`ID_YES 5103`、`ID_NO 5104`、`YES_DEFAULT 0`，與 `wx_stub` 新增值相同（`YES_DEFAULT` 在 stub 故意設 `1 << 27`，讓 style 斷言看得到）；`MessageDialog.SetYesNoCancelLabels(yes, no, cancel) -> bool`、`SetExtendedMessage` 存在 |
| GUI 結果稽核 | 讀 `D:\dxtest\auto{36,37r,37rw,38,39,40,18,19,20b,33,20-f4m-uia,20-f4m-w32,probe}-f5.log`；`sha256sum D:\dxtest\N-f5\DotExpress.exe`、`D:\dxtest\N-f4m\DotExpress.exe`；讀 `auto/f5gui.py`、`item36.py`、`item38.py`、`item40.py`、`rerun.py` 與 2026-10-09-03 的 `docs.close`／`dx.dismiss` | N-f5 `0a0288538b…2312`、48,743,184 bytes；N-f4m `d8fedb2364…039b`，都與 auto-results 相同。十三個 log 的每一行（訊息字串、`.tmp` 名稱、`presses: 1`、`alpha unchanged: True`、`members changed`、`attrib`、`41 ef bf bd 42`、`'A\ufffdB'`、item 33 的 20 行 `ok` 與 `failures: 0`、兩個 f4m log 的單一錯誤框 + `STILL RUNNING -> killed`、probe 的 5 個 `box still open: False`）都與 auto-results 逐字相符；每個 `auto*-f5` 資料夾只有一個 log、時間戳 09:44–09:56 依序遞增，與「每個項目只執行一次」一致。本次沒有重跑 GUI、沒有結束任何程序 |
| 未執行 | — | plan Task 4 Step 3 的 shuffle（工具未 commit；F-3／F-4 審查時三個 seed 都穩定，這次新增的測試都用獨立暫存目錄，推理不會互相影響）；POSIX-only 測試；GUI 重跑（結果檔與 log 沒有可疑處）；item 41（NVDA，仍待使用者）；F-3 M-6 的 item 34／真實 7-Zip（本任務不在範圍） |

## 結論

**Ready**（item 41 NVDA 仍待使用者人工，與 auto-results「仍需人工」一致）。

沒有 Critical、沒有 Important。決定 A（略過未變更文件的寫入）的基線確實只在成功寫入或載入後更新、永遠不取自 controller，所有「record 說未變更但磁碟不同」的路徑都被 `(st_size, st_mtime_ns)` fingerprint 或「無 record 就寫」接住；唯一略過而磁碟留外部版本的情況（同大小 + 同 mtime 的外部替換）是 spec Risks 承認的設計取捨，而且不會丟使用者自己的編輯。決定 B 的關閉對話框三個按鈕、重試迴圈、Cancel／Esc 否決、D8 不可否決路徑都正確；決定 C 的十個呼叫端沒動；決定 D 的替換函式對 lone high／low、反序、split pair、astral 字元都正確，且每個會寫 `.dep` 的路徑都經過 `_normalized`。測試 red-first 可重放、35 個 mutant 只有 4 個等價存活、catalog 可重現且無 fuzzy。下面 8 個 Minor 都是文件措辭、測試缺口或範圍外的既有邊角，不影響合併。

## 1. 略過寫入的資料遺失分析（決定 A，最重要）

逐一列出「record 說未變更、但磁碟內容與使用者所見／預期不同」或「真實變更被略過」的可能，並標記驗證方式（T = 測試、P = 探針、R = 推理）：

| 路徑 | 結果 | 依據 |
| --- | --- | --- |
| 存檔失敗後重試 | `save_open_document` 先 `replace_document` 再 `_is_saved`，`_remember` 在 `save_document_package` 之後；失敗時 record 不動，重試時 `prepared != record.document` → 寫 | T B5（must-have）、B6；mutant m09（record 先於寫入）被 5 個測試抓到 |
| 寫入成功但 record 未更新／record 更新但寫入失敗 | `save_document_package` 是原子寫入，`_remember` 緊接其後、內部只有 `os.stat`（捕捉 `OSError`）與 dict 指派，沒有會拋例外的東西；反向順序不存在 | R（`workspace_service.py:126-135`）；m09 |
| 一般改名 `alpha → gamma` | `move_document_package` 成功後 `pop(source)`、`_remember(renamed)`；`renamed` 來自 controller 副本，而改名開啟中的文件前一定先存檔（失敗即擋住），非開啟文件的 controller 副本等於磁碟 | T B13；m10（記住 source 而非 renamed）被抓 |
| case-only 改名 `alpha → Alpha` | 同上；Windows 上 `package_path("Alpha")` stat 到同一檔，controller 名稱改為 `Alpha`，record 以 `Alpha` 為 key | T B13 subtest `Alpha`、GUI 18／20b |
| 改名失敗（舊包放回） | 例外前沒有動 `_saved`，舊名 record 仍對應舊包（bytes 與 mtime 不變）→ 之後未變更存檔略過 | T B14 |
| 改名失敗且舊包放不回（留在 `.tmp`） | record 的 fingerprint 指向已不存在的 `alpha.dep` → `_package_fingerprint` 回 `None` → 寫，重建 `alpha.dep` | P5 |
| 刪除 | unlink 後 `pop`；unlink 失敗時 record 不動，仍與磁碟一致 | T B15a；m12 等價存活（見 §3.3） |
| 刪除全部（成功／失敗 + reload） | 成功：清空；失敗：`restore_documents_after_delete_all_failure` 後 `_reset_saved(remaining)`，與 `load_documents` 同邏輯 | T B15b；m32 被抓、m13 等價存活 |
| 匯入（含部分失敗） | 每份寫入成功後才 `_remember`；失敗的那份沒有 record 也不進 controller | T B12；m14 被抓 |
| 新增／預設文件 `new` | `create_document` 寫入 → `_remember` → `add_document`；pending（`None`）照原樣記住 | T B11（三個 subtest，含 `new`） |
| 匯出 DEP 蓋到工作區自己的包 | `_write_dep` 不經 service，但改了 mtime（pending 文件還改了大小）→ 下次存檔重寫、`meta.json` 回來 | P1／P1b |
| 外部修改 `.dep`（刪除、換內容、同 bytes 但 touch） | fingerprint 不同 → 寫（與 F-5 之前「每次都重寫」相同） | T B8、B9（兩個 subtest）；m30（缺檔視為已存）被抓 |
| 外部替換為同大小 + 同 mtime | 略過，磁碟留外部版本；使用者的記憶體內容本來就等於上次成功存檔，不會丟自己的編輯 | P6；spec Risks 第一項已承認；粒度見 M-2 |
| 轉換只更新 controller 的點字、沒有寫入 | `prepared.braille` 變了（pending → 非 pending，或新點字）→ 寫；轉換結果等於 record 時略過是正確的 | T B4、P7；m05（忽略點字）被抓 |
| pending 文件 / `braille=None` | `prepare_document_for_save` 保留 `None`，record 也是 `None`（`include_pending_metadata=True` 寫進 `meta.json`）；`None != ""` | T B4、B11 `new`；m18（pending 變 `""`）被 22 個測試抓到 |
| 編輯器正規化（`\r\n` → `\n`、U+0000 截斷） | record 持磁碟文字、編輯器給正規化文字 → 第一次視為變更而寫入（spec D2 consequence 4、Risks 第三項）；之後 record 與編輯器相符。方向只會「多寫」，不會略過 | P2、P8 |
| surrogate 替換 | record 存 `_encodable(document)`，`prepared` 已是 encodable，controller 在 `_is_saved` 之前就換成 encodable → 三者一致；編輯器仍留 surrogate（D5），每次存檔再替換一次後相等 → 略過 | T B7、B11 `delta`、B17、C10、GUI 40；m07（record 存原文）被抓 |
| 快速切換文件 | wx 單執行緒，存檔同步；轉換執行緒不碰 service（`_complete_manual` 經 `CallAfter` 在主執行緒）；`_saved` 只在主執行緒讀寫 | R（`conversion_presenter.py:198-209`） |
| 開啟中文件名稱 vs record key 大小寫 | key 是 controller 的拼法（`document.name`），`open_document_name` 也是；`load_documents` 用 `normalize_document_name(stem)`，controller 持同一物件 | R、T B13 |
| controller 裡沒有 record 的文件（測試直接填入） | `record is None` → 寫 | T B10；m01 被 8 個測試抓到 |

另外確認：`_is_saved` 比對整個 frozen dataclass（name、text、braille），`Document.__eq__` 沒有被覆寫；`_package_fingerprint` 對非 regular file（目錄）回 `None` → 寫 → 失敗訊息與以前相同。

## 2. 關閉對話框（決定 B）

- **重試迴圈**（`gui.py:637-656`）：`while True` 只在使用者按 Retry 時繼續，每輪都是同步的 `ShowModal`，沒有無人介入的無窮迴圈；`can_veto` 為 `False` 時第一次失敗就 log 並回 `True`（D8），不進對話框；`_on_close` 只在回 `False` 時 `Veto()`，而回 `False` 只發生在 `can_veto` 為 `True` 時，所以不會對不可否決的事件呼叫 `Veto()`（舊碼需要 `if evt.CanVeto()` 守衛，新碼不需要）。T C5–C9；m21、m22、m23、m27、m28、m29、m33 都被抓。
- **不儲存就關閉**：回 `True` 後只做 `close_converting_dialog`、`viewer.Destroy()`、`evt.Skip()`，沒有任何寫入；失敗的那次寫入由 F-3 保證無殘留 `.tmp`。T C8（`os.replace` 只被呼叫 1 次、bytes 與 listing 不變、dual view 被 destroy）；GUI 39（`members changed: False`、`tmp: []`）。
- **Cancel／Esc／關閉盒**：`ShowModal` 回 `ID_CANCEL` → `Veto()`、記憶體與編輯器保留修改。T C5、C7、翻轉後的 `cancel_vetoes`；GUI 38 的 Esc。關閉盒（標題列 X）回 `ID_CANCEL` 是 task dialog 有 Cancel 按鈕時的標準行為，smoke test 只量了 Esc：**推理**（見 M-8）。
- **轉換進行中先否決**：`_on_close` 第一個檢查沒動；m35 被 `test_close_while_running_vetoes_or_saves_and_closes` 與 presenter 順序測試抓到。
- **dual view 清理**：與以前相同的三行；T C8。
- **Logging**（F-3 M-3 延續）：`_log_unexpected_save_error` 只 log 非 `OSError`；`_show_document_save_error` 與關閉迴圈各呼叫一次（每次重試一次）；D8 對所有例外型別 log（`"Failed to save the open document while closing"`）。T C9、翻轉後的 `logged_and_asks`、既有的 `test_save_failure_from_an_os_error_is_not_logged`；m24 被抓。
- **無障礙與本地化**：三個按鈕都經 `SetYesNoCancelLabels` 傳入（C5 斷言三個 label 與順序；m34 換序被抓），沒有 `FindWindowById`，F-W9 不會重現；`YES_DEFAULT` + 焦點在重試（GUI 38／39 `focus: 重試(R)`）；`&R`／`&W` 助記符（smoke test Alt+R → `ID_YES`、Alt+W → `ID_NO`）；`ICON_ERROR` 與既有錯誤框一致。NVDA 朗讀仍待 item 41。
- **可重入**（推理，見 M-5）：`ShowModal` 的巢狀事件迴圈期間主視窗被 disable，使用者無法再觸發 Close；但 `WM_QUERYENDSESSION` 不受 disable 影響，wx 會對 top window 再送一個 close event → `_on_close` 巢狀執行。舊碼在同一位置是 modal 的 `wx.MessageBox`，問題類別相同、不是 F-5 引入。

## 3. 其他動作（決定 C）、surrogate（決定 D）、測試

### 3.1 決定 C

十個呼叫端的程式碼沒有改動（見驗證表）；行為差異只來自 service 的略過：未變更 → 不寫、動作繼續（T C1、C2；GUI 36、37、19、20、20b）；有修改且寫入失敗 → 既有錯誤框、動作停止、記憶體保留修改（T C3；GUI 38 的 Ctrl+Tab）。Rename／Delete 對該包的規則（F-3 D7、Windows 刪除語意）沒動，GUI 19／20／20b 的訊息都在名稱對話框之後出現，與 spec 行為表相符。

### 3.2 決定 D

- `replace_lone_surrogates`（`workspace.py:58-62`）：`[\ud800-\udfff]` raw-string pattern，`re` 自己解 `\uXXXX`，能命中 str 裡的 surrogate code point；清潔文字回傳同一物件（A2 `assertIs`）。`utf-16-le` + `surrogatepass` → `replace`：lone high／low 各一個 U+FFFD、反序 pair 兩個、連續兩個 high 兩個、結尾 high 一個、`\udcff` 一個（A1）；`\ud83d\ude00` 合成 U+1F600、真正的 astral 字元原樣（A2，plan Implementation Notes 1 已把原本沒測到 join 的那行修正，red-first 重放確認此測試在舊碼是 ERROR）。m15（只抓 high）、m16（`ignore` 丟掉）都被抓。
- 套用點：`prepare_document_for_save`（text 與保留的 braille；pending 留 `None`，A3、m19）、`_normalized`（Save、Add、Import、Rename 的 staged 包 `PackageFiles.write`、Export DEP 都經過它；A4、A5、m20）。`_encodable` 不碰 name（見 M-1）。
- 其他 writer：`export_document_brl` 與 `_write_html` 用 `write_text(encoding="utf-8")`，遇到 surrogate 會 `UnicodeEncodeError`。走得到的輸入：匯出開啟中文件前一定先 `_save_open_document_with_feedback`，成功後 controller 已是 encodable（P4 證實轉換塞進來的 surrogate 文字在下次存檔被換掉）；非開啟文件來自磁碟或匯入（strict UTF-8 解碼，不可能含 surrogate）。唯一剩下的入口是 dual-view 結果（轉換直接吃編輯器文字），spec Out of Scope 已列「conversion of text with a lone surrogate」：**推理，未探針**（M-7）。字典寫入是另一條流程，不在本任務範圍。

### 3.3 測試

- **10 個改動的既有測試**都是把「lone surrogate 當非 `OSError` 故障」的注入器換成 `zipfile.ZipFile.writestr` 的 `ValueError("injected")`（`test_document_workspace` 2 個、`test_workspace_service` 1 個、`test_gui_document_flows` 的 save 2 個）、Rename 改用 `_FailingWritePackageFiles`（2 個）、`test_close_vetoes_when_save_fails` → `cancel_vetoes`、`close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error` → `logged_and_asks`（翻轉，D6 的直接後果）、`test_close_asks_presenter_before_saving` 改 mock `_save_open_document` 並多一個 `event.CanVeto()` 呼叫（spec Corrected 2）。每個都保住原本的斷言意圖（bytes 不變、listing、記憶體保留修改、traceback 型別改為 `ValueError`）。合理。
- **新測試 34 個**（A 5、B 18、C 11）都在；B16／C2 在 Windows 真的跑；GUI 測試沒有 patch `documents.*`（F-3 規則），用 `os.replace` 與 `writestr` 注入。
- **wx_stub**：`ID_CANCEL`／`ID_YES`／`ID_NO` 是真實 wx 值；`YES_DEFAULT = 1 << 27` 是刻意的（真值 0 在 style 斷言裡看不見），已註解；`_MessageDialog` 的兩個新方法與真實簽章一致。
- **等價存活的 4 個 mutant**：`m04`（fingerprint 只留 mtime）存活是因為每個改大小的測試同時也改了 mtime（見 M-4 的補測建議）；`m11`／`m12`／`m13` 留下陳舊 record 都無害：舊名稱的 record 只會在同名文件再度出現時被查到，而每條建立同名文件的路徑（Add、Import、Delete All 後 Add）都會重新 `_remember`，且就算查到，`_package_fingerprint` 會重新 stat → 檔案不存在就寫。不建議為它們補測試。

## 4. 本地化（決定 D12）

見驗證表「catalog」列。補充：四個新 msgid 的譯文自然、與既有詞彙一致（`儲存`／`文件`／`關閉`；標題 `無法儲存文件` 與既有 `儲存文件失敗：` 區分「對話框標題」與「錯誤那一行」；助記符格式 `重試(&R)` 與 `分類(&C)：` 同款；`取消` 沿用既有 msgstr、無助記符，符合 Windows 慣例）。`msgmerge` 順帶刷新的 `dictionaries/entries.py` 參照（F-4 留下的 stale 行號）與 `gui.py` 行號都與現在的原始碼相符，`#:` 參照相對 `client/`、正斜線，重跑 `generate-pot.bat` 得到相同模板。

## 5. GUI 結果與文件

- auto-results 的每個數字與字串都能在 log 找到（見驗證表）；exe 雜湊相符；結果檔沒有宣稱 log 之外的事。
- **item 20 補充的結論成立**：`docs.close` 每 0.8 s 呼叫一次 dismiss 並記錄看到的每個訊息框；兩個 f4m log 都只記到**一個**錯誤框、之後十幾秒沒有新的框、程序仍在 → 錯誤框確實被關掉、關閉確實被 veto（與 F-5 之前的 `_on_close` 一致）。probe 的 5/5 也顯示舊的 `dx.dismiss` 在這個環境能關掉 wx 的 OK 框，所以 plan Spec Corrections 7 的「win32 click 關不掉」沒有重現（M-3）。
- plan Implementation Notes 的三個 tree id、A2 修正、「8 tests instead of 7」與 Task 5 的數字都與我看到的相符；A2 修正是對的（原 block 的 literal U+1F600 測不到 join）。
- **仍需人工**：item 41（NVDA）步驟寫在 auto-results「仍需人工」，清楚可照做。

## 6. 發現

### Critical

無。

### Important

無。

### Minor

**M-1 文件名稱裡的 lone surrogate 仍會讓 Add／Rename 失敗**（`client/documents/workspace.py:68-70` `_encodable` 不碰 `name`；`client/shared/name_validation.py:68-80` 不檢查 surrogate）
- 情境：把含 lone surrogate 的字串貼進名稱對話框。`normalize_base_name` 放行，`archive.writestr(f"{name}.txt", …)` 在 zip 檔名 UTF-8 編碼時 `UnicodeEncodeError`：Add 跳 `儲存文件失敗：'utf-8' codec can't encode character …` 並以非 `OSError` 記 traceback；Rename 經 `move_document_package` 同樣失敗、舊包與 controller 不變、沒有 `.tmp` 殘留（P3）。不會卡住、不丟資料，只是訊息對使用者無意義，而且 spec D4 的「every package writer can always encode」對名稱不成立。
- 建議：`normalize_base_name` 把 `[\ud800-\udfff]` 視為 `"invalid"`（名稱對話框已有「Name contains invalid characters.」的路徑），或在 `_prompt_for_document_name` 先 `replace_lone_surrogates`。Follow-up 即可。

**M-2 spec Risks 的「to the 100 ns」不準確；fingerprint 的實際粒度是系統 tick**（`docs/superpowers/specs/2026-10-10-f5-save-failure-handling-design.md:475`，`client/documents/workspace_service.py:61-70`）
- 量測：NTFS 的 `st_mtime_ns` 只會以 timer tick 更新（本機 0.5 ms；一般 Windows 預設 15.625 ms），不含 fsync 的連續寫入有 77–89% 得到相同 mtime；含 fsync 的 `save_document_package` 連續 200 次沒有碰撞（最小差 0.5 ms／48 ms）。所以「外部程式在同一 tick 內換成同大小的檔」是真正的碰撞窗口，而不是 100 ns。P6 證實同大小 + 同 mtime 的替換會被略過。實務上這需要外部程式在 app 寫完後的同一個 tick 內寫同大小檔，而 app 自己的寫入含 fsync 至少佔一個 tick 以上，機率仍可忽略；FAT／exFAT（2 s 粒度）與 SMB（client 端 metadata cache 預設 10 s）會放大窗口，但結果只是「磁碟留外部版本」，使用者的記憶體內容本來就等於上次成功存檔，不丟自己的編輯（推理，未在 FAT／SMB 上量測）。
- 建議：把 Risks 第一項改寫成「同一個檔案時間戳 tick（NTFS 0.5–15.6 ms；FAT 2 s；網路磁碟另加 metadata cache）內、同大小的替換」；程式不需改。

**M-3 spec「Corrected after planning」7 與 plan「Spec Corrections」7 仍把「`dx.dismiss` 的 win32 click 關不掉 task dialog」寫成事實**（`…design.md:39`、`…design_zh-TW.md` 對應段、`…plan.md:46`）
- plan Implementation Notes 3 與 auto-results「20 補充」都說沒有重現（probe 5/5、f4m 兩個 log），較可能是 dry run 的時序問題。spec 是「本節優先」的文件，現在與結果檔互相矛盾。
- 建議：在 spec 的第 7 點末尾加一句「實作時未重現，見 auto-results 20 補充；`f5gui.dismiss`／`answer` 的重按機制仍保留」。

**M-4 沒有測試釘住 fingerprint 的 `st_size` 成分**（`client/tests/test_workspace_service.py` `test_package_replaced_on_disk_is_written_again`）
- mutant `m04`（fingerprint 只留 `st_mtime_ns`）存活：`other size` subtest 換內容時 mtime 也跟著變。plan 的 `fingerprint-without-the-modification-time` 只釘 mtime 那一半。
- 建議：加第三個 subtest「不同大小、以 `os.utime` 還原原本的 mtime」，預期仍寫 1 次。順帶可在測試註解記下 `m11`／`m12`／`m13` 類的陳舊 record 是等價 mutant，免得下次把它們當缺口。

**M-5 關閉對話框開著時的巢狀 `_on_close`（推理）**（`client/gui.py:1010-1022`、`637-656`）
- `ShowModal` 期間主視窗 disable，但 `WM_QUERYENDSESSION`（登出／關機）仍會讓 wx 再送一個 close event，`_on_close` 會在外層對話框的巢狀迴圈裡再跑一次：再存一次、再開一個對話框；若內層選「不儲存就關閉」，frame 會在外層 modal 迴圈還在時開始銷毀。舊碼同一位置是 modal 的 `wx.MessageBox`，問題類別相同，不是 F-5 引入；沒有在真機重現（需要觸發 session end）。
- 建議：follow-up 加一個 `self._closing` 旗標：巢狀進入時直接 `Veto()`（可否決）或走 D8（不可否決），不再開第二個對話框。

**M-6 record 持有每份文件的完整 text／braille 副本**（`client/documents/workspace_service.py:53-58`、`93-96`）
- 記憶體從 controller 一份變兩份；對本程式的文件大小（數十 KB 到數 MB）可忽略。資訊性，不需處理；若日後文件變大，可改存 `(len, sha256)` 之類的摘要，但要注意 D2 的 `prepared == record.document` 語意要改成摘要比對。

**M-7 含 surrogate 的文字仍會進入轉換與 dual-view HTML 匯出（推理，spec Out of Scope）**（`client/gui.py:1026` `get_source_text`、`client/documents/formats.py:103-108` `_write_html`、`client/documents/export_coordinator.py:97-103`）
- 編輯器留著 surrogate（D5），轉換直接吃 `input_txt.GetValue()`；若 dual-view segment 帶著 surrogate，`_write_html` 的 `write_text` 會 `UnicodeEncodeError`，而 `_write_single` 只接 `OSError`，例外會逃到 wx 事件處理（wx 印 traceback、程式繼續）。沒有探針驗證 segment 是否真的會含 surrogate（liblouis 可能先失敗或替換）：**不確定**。
- 建議：follow-up 時在 `_write_single` 把 `UnicodeEncodeError` 一併接成「匯出失敗」訊息，或在 `get_source_text` 也套 `replace_lone_surrogates`（這會改變轉換輸入，需另行決定）。

**M-8 關閉盒（X）＝ Cancel 只有推理，smoke test 與 item 38 只量了 Esc**（`docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto-results.md` §0.2）
- spec D7 寫「Esc and the close box cancel」；task dialog 有 Cancel 按鈕時 X 回 `IDCANCEL` 是 Windows 的標準行為，wx 映射成 `wxID_CANCEL`，應該成立，但沒有量測。
- 建議：item 41 人工時順便按一次 X，確認 DotExpress 保持開啟、修改仍在；或之後在 `smoke_f5gui.py` 加 `WM_SYSCOMMAND SC_CLOSE` 一案。

## 7. 其他觀察（不需處理）

- commit trailer 是 `Co-Authored-By: Claude Opus 5.5`，與 plan 所述一致；本記錄未建立任何 commit。
- `_write_dep`（Export DEP）蓋到工作區自己的包後，在下一次存檔之前該包沒有 `meta.json`；若此時程式被強制結束，下次啟動該 pending 文件會變成 `braille=""` 的非 pending 文件。F-5 之前就如此（匯出前的存檔之後同樣沒有再寫），不是這次引入。
- spec Current State 列的 `gui.py` 行號在 Task 3 之後已位移（例如 `_on_close` 由 `:967` 變 `:1010`），catalog 的 `#:` 參照是新的；spec 本身沒有宣稱追蹤最終行號。
- 審查工具（`$SP\tools\mutants.py`、`probes.py`、`mtime_probe.py`、`msgid_scan.py`、`mo_check.py`）與副本都在 scratchpad，未放進 repo。

## 修正記錄

- 日期：2026-10-10，由 Claude 執行；分支 `fix/f5-save-failure-handling`，起點 `1cf59b1`。沒有 merge 進 `main`、沒有 push、沒有切換分支；沒有啟動 source-run 的 `gui.py`。主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 在修正前後 sha256 相同（4 個檔，`diff` 無差異），未 stage。

| 發現 | 處理 |
| --- | --- |
| M-1 | `a06a647`：`normalize_base_name` 在原本的控制字元檢查加上 surrogate code point（`0xD800 <= ord(char) <= 0xDFFF`，含寫成兩個 code point 的 pair），以既有的 `NameValidationError("invalid", "Name contains invalid characters.")` 拒絕；名稱對話框沿用各自既有的 invalid 訊息（`文件名稱不是有效的 Windows 檔名。`／`字典名稱不是有效的 Windows 檔名。`），沒有新增字串，`.po`／`.mo` 未動（msgid 357、`357 translated messages.`）。字典名稱共用同一個 validator（`dictionaries/manager.py` `normalize_dictionary_name`），所以也涵蓋：探針顯示以前可以建立 `a\ud800.csv`，但選它之後 `config.json` 以 `ensure_ascii=False` 寫入時 `UnicodeEncodeError`、檔案只寫到一半（`Config._save` 只 log）。匯入時 source 檔名含 surrogate 改為在載入階段成為 issue（`Name contains invalid characters.`），不再到寫入時才失敗。既有的字典檔名不經 validator 列出，行為不變。先紅：新測試在舊碼 `FAILED (failures=11, errors=1)`（`test_name_validation` 5 個 subtest、文件與字典名稱 typed error 各 1、兩個對話框各 2、service 的 Add／Rename 1 個 ERROR），改後 5 個模組 `Ran 154`、`OK (skipped=2)` |
| M-2 | `65fae9f`：spec Risks 第一項（EN／zh-TW）改寫成「同一個檔案時間 tick 內、同大小的替換」（NTFS 0.5–15.6 ms；FAT／exFAT 2 s；SMB metadata cache 預設 10 s），並註明使用者自己的修改不會遺失；程式不變 |
| M-3 | `65fae9f`：spec「Corrected after planning」7（EN／zh-TW）末尾註明實作時未重現（見 auto-results「20 補充」與 plan Implementation Notes 3），`f5gui.dismiss`／`answer` 的重按機制仍保留；plan Spec Corrections 7 註明被 Implementation Notes 3 部分取代；`f5gui.py` docstring 加一句同樣的說明；plan Implementation Notes 新增第 4 點指向本節 |
| M-4 | `6cfdaf4`：`test_package_replaced_on_disk_is_written_again` 新增 subtest `other size, same time`（另一程式寫入不同大小的包，再以 `os.utime` 還原原本的 atime／mtime，先斷言大小不同、mtime 相同），預期仍寫 1 次。mutant 證據見下 |
| M-5 | 未處理（`_closing` 旗標，防 `WM_QUERYENDSESSION` 造成的巢狀 `_on_close`；F-5 之前就存在的問題類別、需要 session end 才能重現）。建議歸屬：follow-up，與關閉流程的下一次修改一起做 |
| M-6 | 未處理（資訊性：record 多一份 text／braille，對本程式的文件大小可忽略） |
| M-7 | 未處理（含 surrogate 的編輯器文字進入轉換與 dual-view HTML 匯出；spec Out of Scope）。建議歸屬：follow-up，在 `_write_single` 把 `UnicodeEncodeError` 接成匯出失敗訊息，或決定是否在 `get_source_text` 套 `replace_lone_surrogates` |
| M-8 | `65fae9f`：`f5gui.answer` 可用滑鼠點對話框標題列的關閉鈕（`CLOSE_BOX`）與按 Alt+F4；`item38.py` 新增 `x` 模式。因 M-1 改了 production code，依 plan Task 5 Step 1 重建為 N-f5b 後量測：關閉盒（X）與 Alt+F4 都等於取消（見下）。auto-results 的 item 41 人工步驟加上「按標題列的 X，確認也是取消」，並改用 N-f5b |

### Mutant（M-4）

主 checkout `client/` 的純複本（不含 `.venv`、`dictionary/`、`workspace/`、`config.json`、`log/`、`build/`、`dist/`）在 `$SP\f5fix\client`，以 `python -B` 跑三個 F-5 模組（`test_document_workspace`、`test_workspace_service`、`test_gui_document_flows`）；mutant `m04` 把 `_package_fingerprint` 的 `return status.st_size, status.st_mtime_ns` 換成 `return status.st_mtime_ns`：

```text
mutant m04 + 新測試：Ran 290 tests, FAILED (failures=1, skipped=2)
  FAIL: test_package_replaced_on_disk_is_written_again (replaced='other size, same time')
mutant m04 + M-4 之前的測試（HEAD a06a647 的 test_workspace_service.py）：Ran 290 tests, OK (skipped=2)  -- 存活
還原（cmp 與主 checkout 相同）+ 新測試：Ran 290 tests, OK (skipped=2)
```

### 重建與 GUI（M-8；詳見 auto-results「審查後補充」）

| 項目 | 結果 |
| --- | --- |
| Build | 主 checkout `6cfdaf4`，PyInstaller 6.21.0，`Build complete!`；`documents\workspace.py`、`documents\workspace_service.py`、`shared\name_validation.py` 與 `gui.py` 都來自 `DotExpress\client\`。`D:\dxtest\N-f5b\DotExpress.exe`，48,742,658 bytes，sha256 `ABEEFAF58973FDA2B8C28E50A94E9DF3C3C01FAAC464FE3F78669238C6EC62C4` |
| smoke | `close_dialog_demo.py`（scratchpad 的 client 副本）第二次執行：`esc`／`close-box`／`alt-f4` → `ID_CANCEL`，`enter` → `ID_YES`，都 `presses: 1`。第一次執行時前景是另一個程式，`close-box` 的 `click_input` 在 `SetCursorPos` 失敗（工具錯誤），留下的兩個 demo 程序以 PID 結束 |
| 38x ✔ | `D:\dxtest\auto38x-f5m`：X → `running`、輸入框 `'alpha edited'`；Alt+F4 → `running`、輸入框不變；解鎖後 Enter → `exited`，`alpha.txt` 為 `'alpha edited'`、`tmp: []`，重新啟動後內容相同；每次 `presses: 1`，`focus: 重試(R)` |
| 40 ✔、36 ✔ | `auto40-f5m.log`、`auto36-f5m.log`（`readonly`）把資料夾名稱換掉後與 `auto40-f5.log`、`auto36-f5.log` 逐行相同 |
| 程序 | 結束後沒有 exe 位於 `D:\dxtest\*f5m*`／`N-f5b` 的程序，也沒有 `lock.py`、demo 程序 |

### 最終驗證

- 完整套件：`cd client && .venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests` → `Ran 1307 tests`，`FAILED (errors=1, skipped=7)`；唯一 error 為 F-W6 的 `test_dictionary_name_prompt ... test_case_only_rename_still_renames`。1307 = 1304 + 3 個新測試（`test_rejects_surrogate_code_points`、`test_create_or_rename_with_a_lone_surrogate_in_the_name_is_an_invalid_name`、`test_name_with_a_lone_surrogate_shows_the_existing_invalid_name_message`；其餘為既有測試的新 subtest）。
- fixtures：`git show HEAD:client/tests/fixtures/translation_golden.json | sha256sum` → `e67d95a1…1ccd`，`dictionary_entries_trace.json` → `f493da52…c2cf`，與要求相同。
- catalog：`msgid_scan.py` → `source msgids: 357 sha256 7ebbbe56…26c6`；`git diff 1cf59b1 HEAD -- client/locales` 為空；`msgfmt --check --statistics` → `357 translated messages.`。
- `HEAD:client` tree（`65fae9f`）：`9503872e0082fc9799e11c7f97ff53b6f02e15b7`。
