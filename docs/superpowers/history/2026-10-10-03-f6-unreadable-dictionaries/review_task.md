# F-6 讀不到的字典審查記錄

- 日期：2026-10-10
- 範圍：`fix/f6-unreadable-dictionaries` 的 `main...fix/f6-unreadable-dictionaries`（`main` = `e46ff26`；7 個 commit：`eb2a88f` spec、`fca6202` plan、`36d863e` 逐檔計算筆數與 log、`99fda8a` 原因列／編輯重讀／frame 守衛、`7cc1fd1` 匯入讀完整個檔案、`6068661` catalog、`2dc5328` GUI 結果）。production diff `git diff main...HEAD -- client`：15 個檔，+1071／−205（新檔 `dictionaries/read_problems.py` 88 行；`dialog.py` +73／−9、`gui.py` +17／−2、`dictionaries/manager.py` +12／−4、`dictionaries/presenter.py` +6；三個 locale 檔；6 個測試檔含新檔 `tests/test_dictionary_read_problems.py` 與 `tests/unreadable_dictionary_files.py`）。`HEAD:client` tree `e995d544…`，8 個 production／locale 檔的 blob sha256 都與 plan「Dry Run」列出的逐一相同（`1c26c04c…`、`3dd5dda1…`、`fe2127cd…`、`b88a05bd…`、`6416bfa0…`、`7cb6a45d…`、`3c4e9653…`、`44037940…`）。
- 對照：`docs/superpowers/history/2026-10-10-02-handoff/HANDOFF.md` §1、§2、§5.1、§5.3（使用者的決定 2：筆數欄顯示「無法讀取」，選取後再說明原因）、`AGENTS.md`、`docs/superpowers/specs/2026-10-10-f6-unreadable-dictionaries-design.md`（含 `_zh-TW.md`，含「Corrected after planning」／「規劃後的修正」9 點）、`docs/superpowers/plans/2026-10-10-f6-unreadable-dictionaries.md`、`docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto-results.md` 與 `auto/`、`2026-10-10-01-f5-save-failure-handling/review_task.md`（格式）。
- 審查方式：逐行讀 5 個 production 檔的 diff 與 `DictionaryManagementDialog`、`DictionaryEntriesDialog.__init__`、`on_open_dictionary_management`、`import_from_file`、`validate_dictionary_csv`、`load_dictionary_rows`、`name_prompt.py`、`log.py`、`app_paths.py`、`tests/file_log_isolation.py`、`tests/windows_file_handles.py` 全文；6 個測試檔的 diff；對字典檔的每條讀取路徑（開啟對話框、新增／刪除／改名／匯入後的 refresh、選取、編輯重讀、frame 守衛、匯入驗證、匯出、轉換）逐一推演；在 Windows 11（NTFS，`D:`／`C:`）跑完整套件與焦點模組；把每個實作 commit 的測試拿去跑其父 commit 的 production code（red-first 重放，`git archive` 到 scratchpad）；在 scratchpad 的 `client/` 副本自套 22 個 mutant（plan 的 22 個之外另寫的）；20 種邊界檔案的讀取器一致性探針；重建 `.pot`／`.mo` 比對與 AST 掃描 msgid；稽核 `D:\dxtest\auto*-f6.log` 六個 log 與 exe 雜湊；另以 pywinauto 在新的 `D:\dxtest\rev1-f6`／`rev2-f6` 對 packaged build 補量鍵盤行為與對話框尺寸（只結束這兩個資料夾底下的程序）。主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 在審查前後 sha256 相同；沒有啟動 source-run 的 `gui.py`；沒有動 `client2/`、`preprocessing/`、`testdata/`、`DotExpress-f7`。凡未能驗證的標為「推理」。
- 本記錄只寫檔，未 commit。

## 驗證（Windows 11 26200，`$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`，`$SP` = session scratchpad 的 `f6review\`）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| app data | 審查前後 `(find client/dictionary client/workspace client/log -type f; ls client/config.json) \| sort \| xargs sha256sum`，`diff` | 4 個檔（`config.json` `eea87b39…`、`dictionary/default.csv` `8f0594e9…`、`log/init.log` `1b787580…`、`workspace/new.dep` `d0cb6539…`）相同；`git status --short` 全程只有既有的 `client2/`、`preprocessing/`、`testdata/`；未 stage 任何東西 |
| 完整套件（驗收 1） | `cd client && $PY -B -X utf8 -m unittest discover -s tests` | `Ran 1335 tests in 16.477s`、`FAILED (errors=1, skipped=7)`；唯一 error 為 F-W6 `test_dictionary_name_prompt … test_case_only_rename_still_renames`。1335 = 1307 + 28，與 plan Expected Counts 相同 |
| 焦點模組（驗收 2） | `$PY -B -X utf8 -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_gui_document_flows tests.test_i18n tests.test_dictionary_entries`；`-v` 抓 Windows-only | `Ran 327`、`OK (skipped=1)`；`test_file_held_open_without_sharing_cannot_be_opened ok`、`test_dictionary_held_open_without_sharing_is_unreadable ok`（有跑、沒被 skip） |
| 副本與 commit 一致 | `git show HEAD:<path> \| sha256sum` × 8 | 全部與 plan Dry Run 的 sha256 相同（見範圍一節）；`git rev-parse HEAD:client` = `e995d544…`（Task 4／6 的 tree id） |
| red-first 重放 | `$SP\tools\red_replay.sh`：對每個實作 commit 以 `git archive` 取出整個 `client/`，再用 `git show <parent>:<production 檔>` 覆蓋（t1 覆蓋 `dialog.py`、移除 `read_problems.py`；t2 覆蓋 `dialog.py`、`gui.py`；t3 覆蓋 `manager.py`、`presenter.py`；t4 覆蓋三個 locale 檔），跑六個 F-6 模組 | t1（`36d863e` 的測試於 `fca6202`）：`Ran 289`，紅燈 = `test_dictionary_read_problems` 整個模組 ImportError（R1–R8）、M1、M2、M3、M10（2 subtest）、M11、M12 共 7 個測試；t2（`99fda8a` 於 `36d863e`）：`Ran 304`，紅燈 M4–M9、M12 的原因列斷言、G1、G2 共 9 個；t3（`7cc1fd1` 於 `99fda8a`）：`Ran 309`，紅燈 P1 的 2 個（含 2 subtest）＋ P2 的 3 個；t4（`6068661` 於 `7cc1fd1`）：`Ran 310`，紅燈 I1。四步都與 spec Migration Steps／Corrected 3 一致。（副本沒有 `scripts/`，所以每次多一個環境錯誤 `test_generate_pot_extracts_n_keyword`，與 F-6 無關；主 checkout 上該測試是綠的） |
| 自套 mutant（22 個，plan 之外） | `$PY -B -X utf8 $SP\tools\mutants.py $SP\copy\client`（副本不含 `.venv`、`dictionary/`、`workspace/`、`config.json`、`log/`；每個 mutant 跑六個 F-6 模組 `Ran 310`，跑完還原） | 18 個被抓到：x01 `read_dictionary_count` 只接預期型別、x02 log 用 WARNING、x03 log 用完整路徑、x04 標題與原因只隔一個換行、x05 OTHER 不帶錯誤文字、x06 所有 `OSError` 都算 CANNOT_OPEN、x07 編輯後不 `Refresh`、x08 編輯後不更新原因列、x09 錯誤時仍設 `edit_dictionary_name`、x11 原因列不 `Layout`、x12 隱藏時不清空、x14 匯入用 `show_info`、x15 presenter 只接 `UnicodeDecodeError`、x17 `validate` 用 `utf-8` 不處理 BOM、x18 守衛沒有 `parent`、x19 守衛後仍開編輯器、x20 欄寬只量 `Entries`、x22 選取事件不更新原因列。4 個存活：x10（`_get_item_text` 改成「不在 counts 就顯示 Unreadable」）與 x13（`_load_dictionary_counts` 不重設 `_dictionary_read_errors`）在現行不變式下等價（每個名稱恰在其中一個 dict，`_store_count` 成功時會 pop 錯誤）；x16（`validate_dictionary_csv` 先讀完所有列再檢查表頭）與 x21（`_store_count` 錯誤路徑不清除舊筆數）是測試缺口，見 M-3 |
| 讀取器一致性探針 | `$PY -B -X utf8 $SP\tools\probes.py`（20 種檔案：空檔、只有 BOM、只有表頭、無表頭、錯表頭、UTF-16、欄位含 NUL、小檔未閉合引號、游離引號、多餘欄位、LF、Big5、多位元組字元跨 8192 邊界、Big5 跨 8192 邊界、Latin-1 位元組、超過欄位上限、UTF-8 BOM、引號內換行、未知類型、EOF 處未閉合引號） | 每一種的 `validate_dictionary_csv`（匯入）、`read_dictionary_count`（筆數）、`DictionaryEntryListModel.load`（編輯器）三者一致：匯入接受的檔都能計數與編輯；只有表頭類（空檔、只有 BOM、無表頭、錯表頭）是匯入拒絕（`ValueError`，既有訊息）而筆數為 0（O8，不變）。Big5／Latin-1／UTF-16 → `NOT_UTF8`，超過上限 → `INVALID_CSV`，NUL 與小檔未閉合引號照舊載入（spec Out of Scope）。`.format` 對含 `{x}`、`}{` 的錯誤文字與名稱安全；`import_dictionary` 被拒時 `dictionary/` 仍為空（沒有半套副本）；錯表頭＋Big5 的小檔是 `UnicodeDecodeError` 先出（整檔一次解碼），與改前相同 |
| catalog（驗收 3） | `LANGUAGE=C msgfmt --check --statistics -o /dev/null …po`；`grep -c fuzzy`；`msgfmt --check -o $SP\rebuilt.mo` 後 `sha256sum` 與 `git show HEAD:…mo`；`cmd /c scripts\generate-pot.bat $SP\tools\second.pot` 後去掉 `POT-Creation-Date` 行 `diff`；`$PY -I $SP\tools\msgid_scan.py`（AST 掃 `_`／`N_`，與 `.mo` 的 key 集合互比） | `364 translated messages.`，fuzzy 0；`.po`／`.pot` 各 365 個 `msgid` 行（364 + header）；重建的 `.mo` sha256 `44037940…` 與已 commit 的相同（28,058 bytes）；第二次產生的模板除日期外相同（exit 0）；`source msgids: 364 sha256 7b53ff31…`（與 plan Task 5 Step 4 相同）；source 與 `.mo` 的 msgid 集合互為子集（差集皆空）；`msgstr == msgid` 只有 `ASCII`、`BRL`、`DEP`、`DOCX`、`DotExpress`、`EPUB`、`PDF`、`SimBraille`、`TXT`、`Unicode`（AGENTS.md 允許的既有術語）；兩個檔的 `POT-Creation-Date` 都是 `2026-10-10 12:00+0800`；86 個 `#~` obsolete 與 `main` 相同；`#, python-brace-format` 在三個 `{…}` 字串上；`.po` diff 中出現的 `Imported file must contain…` 只是 `msgmerge` 依行號重排，不是新增（msgfmt 無重複） |
| fixtures、受限檔案（驗收 4–6） | `git show HEAD:client/tests/fixtures/…\| sha256sum` × 2；`git diff --stat main...HEAD -- client/braille client/conversion client/dictionaries/entries.py scripts vendor client/tests/fixtures client/tests/wx_stub.py`；`git show HEAD:client/braille/tables/__init__.py \| od -c \| grep -c '\\r'` | `e67d95a1…1ccd`、`f493da52…c2cf`，與要求相同；受限路徑的 `--stat` 為空；`__init__.py` 371 個 CR、未在 diff 中；`git diff --name-only main...HEAD` 正是 15 個 client 檔 + 11 個 docs 檔（spec 驗收 6 + Corrected 1 的 `unreadable_dictionary_files.py`） |
| 縮排／ASCII | `grep -c $'^\t'`／`'^    '` 逐檔；`grep -P '[^\x00-\x7F]'` | tab 檔：`read_problems.py`、`dialog.py`、`gui.py`、`presenter.py`、三個 tab 測試檔（0 行以 4 空白開頭，`gui.py` 的 6 行是既有 docstring）；4 空白檔：`manager.py`、`test_dictionary_manager.py`、`test_gui_document_flows.py`、`test_i18n.py`、`unreadable_dictionary_files.py`（0 個 tab）；`unreadable_dictionary_files.py` 與 `read_problems.py` 都是純 ASCII（測試資料用 `\u` escape，HANDOFF §2 的 Edit／Write 陷阱沒踩到） |
| commit | `git log --format='%h %s%n%b' main..HEAD` | 7 個 commit 都以 `Co-Authored-By: Claude Opus 5.5` 結尾；沒有 merge、沒有 push |
| GUI 結果稽核 | 讀 `D:\dxtest\auto{42,46,47,48,50,42-f5b}-f6.log`；`sha256sum D:\dxtest\N-f6\DotExpress.exe`；`client\build\DotExpress\PYZ-00.toc` | 六個 log 的每一行（列、原因列的 `uia name`／`uia value`／`sel`／`length`／`lines`、焦點、訊息框、檔案清單、`unchanged: True`、log 行）都與 auto-results 逐字相符；每個 `auto*-f6` 資料夾只有一個 log，時間戳 12:14–12:16 依序；exe `a3ca72de…7994`、48,749,053 bytes，與 auto-results 相同；`PYZ-00.toc` 的 `dialog`、`dictionaries.read_problems` 來自 `D:\workspace\DotExpress\client\` |
| 補量（rev2-f6） | `$SP\uia\Scripts\python.exe $SP\tools\rev1.py D:\dxtest\N-f6\DotExpress.exe D:\dxtest\rev2-f6`（rev1-f6 第一次因腳本錯誤中止，該資料夾下的程序已以 PID 結束；兩個資料夾都是新建） | 見 §2；結束後沒有 exe 位於 `D:\dxtest\rev*` 的程序 |
| 未執行 | — | plan Task 5 Step 3 的 shuffle（工具未 commit；新測試都用獨立暫存目錄並隔離 logger，推理不互相影響）；POSIX-only 測試；items 42–51 重跑（結果檔與 log 沒有可疑處）；item 52（NVDA，仍待使用者）；F-W6 |

## 結論

**Ready**（item 52 NVDA 仍待使用者人工，與 auto-results「仍需人工」一致）。

沒有 Critical、沒有 Important。F-W12 的根因（`_load_dictionary_counts` 一個例外就讓對話框建不起來）確實被逐檔 `read_dictionary_count` 接住，refresh 的每個呼叫端（開啟、新增、刪除、改名、匯入）都不再會失敗；例外分類順序正確（`UnicodeDecodeError` 先於 `ValueError`、`PermissionError` 先於 `OSError`→OTHER）；原因列只在選到讀不到的字典時出現、是清單之後的下一個 Tab 停點、UIA 名稱是標籤、文字全選；編輯重讀＋frame 守衛把 D5／D6 的競態都接住；匯入在複製之前讀完整個檔案，被拒時沒有半套副本；改名／匯出／刪除／轉換不變；log 一行一檔、非預期錯誤才有 traceback，所有會記錄的測試模組都隔離了 `dotexpress.gui`；catalog 364／0 fuzzy 且 `.mo` 可逐位元組重現；使用者真實資料、兩個 fixture、受限檔案都沒動。測試 red-first 可重放，22 個自套 mutant 只有 4 個存活（2 個等價、2 個測試缺口）。下面 8 個 Minor 中，M-1、M-3、M-4、M-7 便宜，建議 merge 前一起修；M-2 與 M-8 是 O7／O1 的 UX 取捨，請使用者決定。

## 1. 逐路徑分析（最重要：對話框永遠開得起來，而且不改寫使用者的檔案）

| 路徑 | 結果 | 依據 |
| --- | --- | --- |
| 開啟時有一個檔讀不到（Big5、UTF-16、Latin-1、ACL 拒絕、被 share-none 開著、超過 CSV 欄位上限） | `read_dictionary_count` 接 `Exception`，回 `DictionaryCount(error=…)`；其他字典照常計數；對話框開啟 | T R5、R7、M1、M3、M12；GUI 42、46、47、49；探針 20 種檔 |
| 新增／匯入／改名／刪除後 refresh，另一個檔仍讀不到 | `refresh_dictionaries` 先 `_load_dictionary_counts`（兩個 dict 都重設）再 `SetItemCount`，名稱、筆數、item count 一致 | T M2；GUI 48、50；mutant x13（等價）、plan 的 `counts-without-the-per-file-catch` |
| 選取讀不到的字典／可讀的字典 | `_on_selection_changed` → `_update_read_problem`：`ChangeValue` + `SelectAll` + `Show(True)` + `Layout`；可讀時 `ChangeValue("")` + `Show(False)`。`EVT_LIST_ITEM_DESELECTED` 時 `_get_selected_name()` 為 `None` → 隱藏，之後 SELECTED 再顯示（只是閃一下，推理） | T M4–M6；GUI 43；補量 rev2 |
| 開啟時設定裡選的字典就是讀不到的那份 | `refresh_dictionaries(…, selected_name)` 末尾的 `_update_read_problem` → 原因列在開啟時就顯示，焦點在該列 | 補量 rev2（`open with big5 configured: … 'selected'`，`sel (0, 61)`，焦點 `ListItem big5`） |
| 編輯：仍讀不到／已修好／開著時才壞掉 | 先重讀、`_store_count`、`Refresh`、`_update_read_problem`，有錯就 `show_error(describe_unreadable_dictionary)` 並 return（`edit_dictionary_name` 仍 `None`、沒有 `EndModal`）；修好則筆數更新、原因列隱藏、`EndModal(ID_EDIT)` | T M7–M9；GUI 44、47；mutant x07、x08、x09 |
| 編輯器建構時才讀不到（競態） | `gui.py` 只包住建構子；log（預期錯誤一行、其他 traceback）＋ `wx.MessageBox(…, parent=self)`；`with editor as entries_dialog: ShowModal()` 不變，既有 frame 測試照跑 | T G1、G2；mutant x18、x19 |
| 匯入 Big5（前 8 KiB 含中文／只有 ASCII）、超過上限 | `validate_dictionary_csv` 在同一個 `with` 內先檢查表頭再讀完所有列；presenter 在 `except ValueError` 之前接 `(UnicodeDecodeError, csv.Error)`；`shutil.copyfile` 在驗證之後 | T P1、P2；GUI 48、49；探針 `import … []`；mutant x15、x16（見 M-3）、x17 |
| 匯入來源缺表頭／名稱無效／來源被鎖 | 既有訊息不變（`ValueError`／`OSError` 分支沒動） | 既有測試；見 M-4 |
| 改名、匯出、刪除讀不到的字典 | presenter 既有程式；`Path.rename`／`copyfile`／`unlink` 不解碼內容；匯出位元組相同 | GUI 50（`out.csv equals the source: True`）、46（ACL 拒絕時既有 `匯出字典失敗：[Errno 13]`） |
| 轉換選到讀不到的字典 | 不變（D10）：`轉譯失敗：<Python 錯誤>` | GUI 51 |
| 空檔、只有 BOM、無表頭 | 筆數 0、可讀（O8），匯入仍以表頭訊息拒絕 | 探針；T R4 |
| 任何路徑改寫字典檔？ | `read_problems` 只讀；匯入被拒不複製；沒有自動偵測／轉碼（U2） | GUI 每個項目的 sha256 前後相同；`grep` 確認 `read_problems.py` 沒有 `open(`／`write` |

另外確認：`DictionaryReadProblem` 的分類對 `FileNotFoundError`／`OSError(22)`／`ValueError`／`RuntimeError` 都是 OTHER（T R1）；`describe_*` 以 `.format(error=…)`／`.format(name=…)` 代入，錯誤文字或名稱含大括號不會出事（探針）；一個叫 `x.csv` 的資料夾會被 `list_dictionary_names` 的 `is_file()` 濾掉，所以探針看到的「資料夾 → `PermissionError` → CANNOT_OPEN（『正被其他程式使用』）」在 UI 走不到；`DictionaryCount` 是 frozen dataclass、`__eq__` 以例外物件的 identity 比對，測試裡的 `assertEqual(count, DictionaryCount(error=error))` 成立是因為同一物件。

## 2. 無障礙與鍵盤（補量 rev2-f6，packaged build；數字是實體像素，125 %）

| 量測 | 結果 |
| --- | --- |
| Tab 鏈（big5 選取、焦點在清單） | Tab → `Edit`「無法讀取的原因：」→ Tab → `Button`「新增」；Shift+Tab 兩次回到 `ListItem big5`。多行欄位沒有 `TE_PROCESS_TAB`，Tab 不會被吃掉 |
| 在欄位內打字 `abc`、Del、Backspace | 文字不變（length 61、`uia value` 相同），唯讀生效 |
| 在欄位內按 Enter | 對話框仍開著、沒有訊息框（沒有誤觸預設按鈕） |
| 在欄位內按 Esc | 對話框關閉，與焦點在清單時按 Esc 相同 |
| **在欄位內按 → 之後 Shift+Tab 再 Tab 回來** | 選取維持折疊 `(61, 61)`，**不會重新全選**（見 M-1） |
| 對話框／清單尺寸（default 選取 → big5 選取） | 對話框 673 × 359 不變；清單 193 px → 83 px 高（含表頭；約 2–3 列可見；見 M-2） |
| 原因列的 UIA | `Edit`，name = 標籤、value = 原因全文、`EM_GETSEL (0, 61)`、兩行（GUI 43、46、49） |
| gui.log | 三次開啟三行，選取與 Tab 不記錄 |

D3 的「全選讓 NVDA 讀全文」在正常路徑成立（`ChangeValue` 後 `SelectAll`，量到 `(0, 61)`），NVDA 實際朗讀仍待 item 52。

## 3. Logging、測試隔離、測試品質

- `read_problems.logger = get_logger("dotexpress.gui", "gui.log")` 在 import 時綁定（`FileHandler(delay=True)`，不碰磁碟）；`gui.py:98` 本來就綁同一個 logger，packaged build 無差異。`isolate_file_logs` 在 R、M 兩個新模組的 `setUpModule` 與既有的 `test_gui_document_flows` 都有；完整套件跑完 `client/log/` 只有原本的 `init.log`（app data 列）。`dictionaries.presenter` 現在 import 時也會綁定（它 import `read_problems`），但 presenter 的路徑不記錄；見 M-6。
- `log_dictionary_read_error` 的分類（`UnicodeDecodeError`／`csv.Error`／`OSError` 一行，其餘 `exc_info`）由 R5、R6、M3、G1、G2 釘住；mutant x01–x03 都被抓到。`_csv.Error.__name__` 是 `Error`（GUI 49 的 log 行 `Error: field larger…`，Corrected 7）。
- 測試用真實檔案而不 patch `read_problems`（speech-dialog stub 的 eviction 會讓 `dictionaries.read_problems` 有兩個模組物件，Corrected 4 的理由正確：`test_dictionary_management_dialog.py` 第 9–10 行先 import，第 17 行才 `load_speech_dialog()`）。`_FakeControl` 記錄 `Show`／`ChangeValue`／`SelectAll` 的順序，M4 斷言的順序 `ChangeValue → SelectAll → Show(True)` 與 `_update_read_problem` 相同。
- 既有測試只改了 `_make_dialog`（多四個屬性）與 `_open_management`（多一個 `editor_error` 參數）；沒有翻轉任何既有斷言。
- 存活的 x16／x21 見 M-3；x10／x13 是等價 mutant，不建議補測。

## 4. 本地化（D11）

- 7 個新 msgid 全部譯出、0 fuzzy（Corrected 8 說的兩個 `msgmerge` 誤配已清掉：`無法讀取的原因：` 不是 `預設字典無法刪除。`，`無法讀取字典「{name}」。` 不是 `字典「{name}」已存在。`）。
- 詞彙與既有一致：`無法讀取字典「{name}」。` 對 `字典「{name}」已存在。`／`無法刪除字典：{error}`；`無法讀取檔案：{error}` 對 `無法開啟雙視檢視：{error}`；`無法讀取` 與 `條目數量` 都是四字（欄寬不變）；`CSV UTF-8 (逗號分隔)` 是繁中 Excel「另存新檔」清單裡的寫法；`Excel`、`UTF-8`、`CSV` 依 AGENTS.md 保留原文。
- 一處不一致：CANNOT_OPEN 用「您」，catalog 其他三處第二人稱都是「你」（`.po:77`、`:89`、`:988`）。見 M-7。
- `#:` 參照相對 `client/`、正斜線，`dialog.py:31`／`gui.py:483` 等行號與目前原始碼相符；`generate-pot.bat` 重跑相同。

## 5. 文件與流程

- spec（EN／zh-TW 各 423 行、章節對應）、plan、auto-results 三者與實作一致：D1–D11 都找得到對應程式；Corrected 1–9 都反映在測試與腳本；auto-results 的每個數字都能在 log 找到；「與 F-7 的關係」說 production `wx.MessageBox` 會變 20 處，`grep` 確認正是 20（`gui.py` 11 處）。
- HANDOFF §5.3 決定 2「顯示『無法讀取』，選取後再說明原因」已照做；§5.1 要求 spec 查清的三件事（轉換、匯入 Big5、刪除／改名／匯出）都在 spec Findings (a)(b)(c) 與 D7／D9／D10。
- O1–O8 的預設都是保守的，實作與預設相符；O1（不自動朗讀）與 O7（對話框不長高）是使用者可能想改的兩個，見 M-2、M-8。
- plan 沒有「Implementation Notes」一節（HANDOFF §3 說 plan 末尾有）；因為實作與 dry run 的 tree id 逐一相同、沒有偏離，可接受，但建議補一句，見 M-7。
- GUI 腳本只以 `dx.kill_under(d)` 結束該資料夾下的程序，`lockx.py` 以 `taskkill /T`；`item46.py` 在 `finally` 還原 ACL；沒有碰 `D:\dxtest\N*`、既有 `auto*` 與主 checkout。item 52 的人工步驟寫在 auto-results，清楚可照做，沒有被代為勾選。
- `AGENTS.md` 是 git-ignored，無法以 git 確認本任務沒改它（推理：diff 與 commit 都沒碰）。

## 6. 發現

### Critical

無。

### Important

無。

### Minor

**M-1 原因欄位的全選只在內容改變時設定，重新取得焦點時不會恢復**（`client/dialog.py:637-651` `_update_read_problem`；補量 rev2：`after RIGHT (61, 61)`、`after leaving and returning (61, 61)`）
- 情境：NVDA 使用者 Tab 進欄位聽完原因，按一下方向鍵（選取折疊到行尾），Shift+Tab 回清單，再 Tab 回來：這時 NVDA 只會讀游標所在的最後一行，D3 依賴的「取得焦點時文字是選取的」不再成立。只在同一個選取狀態下發生；換選別的字典後 `ChangeValue` + `SelectAll` 會重設。
- 建議（便宜，3 行＋1 個測試）：在 `_build_ui` 綁 `self.read_problem_ctrl.Bind(wx.EVT_SET_FOCUS, self._on_read_problem_focus)`，handler 做 `self.read_problem_ctrl.SelectAll(); event.Skip()`；測試直接呼叫 handler 並斷言 `_FakeControl.calls` 有 `("SelectAll",)`。改了 `dialog.py` 就要重 build 並重跑 item 43／45（`item42.py`）。可與 item 52 的結果一起定案。

**M-2 原因列顯示時清單只剩約 2–3 列可見（O7，請使用者決定）**（`client/dialog.py:552-556`、`_update_read_problem` 的 `Layout()`；補量 rev2：清單 193 → 83 px，對話框 359 px 不變；plan Corrected 6 的 154 → 66 邏輯像素）
- 情境：預設視窗大小下，選到讀不到的字典時清單突然縮到含表頭 83 px，有 5 個以上字典時要捲動；視覺上「跳一下」。對話框可拉大，拉大後清單取回空間。
- 選項：(a) 維持現狀（O7 的預設，不改變沒有壞檔時的任何尺寸）；(b) 第一次顯示原因列時讓對話框長高該列的高度（`self.SetMinSize`／`Fit` 一次，之後不再縮回）；(c) 欄位改成 3 行（`GetCharHeight() * 3`，zh-TW 的 61 字在這個寬度是兩行）。(b)、(c) 都要重 build 並重量 43／45。

**M-3 兩個便宜的測試缺口**（mutant x21、x16 存活）
- x21：`_store_count` 的錯誤路徑若不 `pop` 舊筆數，`_dictionary_counts` 會留下讀不到的字典的舊數字；UI 看不出來（`_get_item_text` 先查錯誤），但 spec D2 說 `_dictionary_counts` 只放可讀的字典。建議在 `test_edit_on_a_dictionary_that_became_unreadable_stays_open` 加 `self.assertEqual(target._dictionary_counts, {})`。
- x16：`validate_dictionary_csv` 把表頭檢查移到讀完所有列之後，現有測試都過；差別只在「表頭錯誤且 8 KiB 之後才有 Big5」的檔會先報 NOT_UTF8 而不是表頭訊息（D9 規定表頭先）。建議在 `test_validate_reads_every_row` 加一個 subtest：`b"x,y,z\r\n" + 17 KB ASCII + cp950 列` → `ValueError`。

**M-4 匯入來源被鎖或被拒時仍顯示原始 `[Errno 13]`，與字典資料夾內同一狀況的友善說明不一致**（`client/dictionaries/presenter.py:184-186` `except OSError`；spec D9「OSError … keep their current messages」）
- 情境：匯入一個正被 Excel 以 share-none 開著的檔：`匯入字典失敗：[Errno 13] Permission denied: 'C:\…'`；同一檔若在字典資料夾裡，原因列會說「無法開啟檔案。檔案可能正被其他程式使用…」。spec 刻意保留既有訊息，所以不是缺陷。
- 建議：follow-up（或 F-7 整理訊息時）把 `PermissionError` 也走 `describe_dictionary_read_error`；這會改一個既有訊息，需使用者點頭。

**M-5 frame 守衛把編輯器建構時的任何例外都說成「無法讀取字典」，且每次都留下一個隱藏的半建構 `wx.Dialog`**（`client/gui.py:1005-1016`；`client/dialog.py:342-349` 先 `super().__init__` 再 `load`；spec Current State「Leak」、Out of Scope）
- 情境：只在 D5 檢查之後、建構子之前檔案才壞掉的競態路徑；訊息對 `UnicodeDecodeError`／`PermissionError` 正確，對 `_build_ui` 的程式錯誤則誤導（log 有 traceback）。洩漏的 dialog 是 frame 的子視窗，隨 frame 關閉。
- 建議：follow-up 把 `DictionaryEntryListModel.load` 移到 `super().__init__` 之前（或先讀再建），守衛就只會接到讀取錯誤，也不再洩漏；spec 明說本任務不改建構順序，所以不在這裡修。

**M-6 `dictionaries.presenter` 現在 import 時就會綁定 `dotexpress.gui` 的 FileHandler**（`client/dictionaries/read_problems.py:19` 模組層級 `get_logger`；`client/log.py:18-30` `delay=True`）
- 情境：任何 import `dictionaries.presenter`、`dialog` 或 `read_problems` 卻沒呼叫 `isolate_file_logs("dotexpress.gui")` 的測試模組，只要日後讓 `read_dictionary_count` 失敗一次，就會把一行寫進真實的 `client/log/gui.log`。目前會記錄的三個模組都隔離了（本次套件跑完 `log/` 沒有新增檔案），所以只是脆弱，不是缺陷。
- 建議（便宜，可選）：改成在 `log_dictionary_read_error` 內 `get_logger(...)`（延遲綁定，`isolate_file_logs` 對尚未存在的 logger 也有效），測試不用動；或在 `tests/file_log_isolation.py` 的 docstring 補一句「import `dictionaries.presenter` 的模組也要隔離」。

**M-7 文字與文件的小修**（便宜）
- `client/locales/zh_TW/LC_MESSAGES/dotexpress.po:1165`：CANNOT_OPEN 的「或您沒有讀取權限」改成「或你沒有讀取權限」，與 catalog 其他三處「你」一致（`:77`、`:89`、`:988`）；同步改 `tests/test_i18n.py:719-721` 的預期字串、spec 兩個檔的字串表與 auto-results 的 `<CANNOT_OPEN>` 定義，重跑 `msgfmt --check -o …mo`（`.pot` 不變）。改了 `.mo` 就要重 build 才能讓 packaged 的 46／47 顯示新字；只重跑 item 46 或 47 其一即可。
- `docs/superpowers/plans/2026-10-10-f6-unreadable-dictionaries.md` 末尾補一節「Implementation Notes」：一句「實作依 plan 套用，Task 1–4 的 tree id 與 dry run 逐一相同，沒有偏離；Task 6 的 exe 雜湊見 auto-results」，讓下一位代理不必自己比對。

**M-8 不自動朗讀原因（O1，請使用者決定）**（spec D3「No automatic announcement on selection」）
- 情境：方向鍵移到讀不到的那列時 NVDA 讀「big5 無法讀取」（推理：報表模式的清單會讀出各欄），原因要再按一次 Tab。這符合決定 2 的「選取後再說明原因」的保守解讀。若使用者希望一到該列就聽到原因，需要新的平台程式（UIA notification 或 live region），不建議在 F-6 做；item 52 時可一併判斷現在的做法夠不夠。

## 7. 其他觀察（不需處理）

- 小檔的未閉合引號、游離引號、欄位含 NUL 在 Python 3.13 都不會拋錯，會載入成一筆合併的長項目（spec Out of Scope 已列）；超過 131,072 字元才是 `csv.Error`。
- `UnicodeDecodeError` 的 log 行與訊息框都不含檔案內容，只含位元組位置；`PermissionError` 的 log 行含完整路徑（既有 `Failed to …: {error}` 訊息也是）。
- 每次開啟對話框、每次 refresh、每次編輯都會對仍讀不到的檔各記一行；補量三次開啟三行，與 D8／Risks 相符。
- `validate_dictionary_csv` 現在讀完整個檔，匯入等於讀兩次（驗證＋複製）；字典都是小檔，spec Risks 已承認。
- 審查工具（`$SP\tools\red_replay.sh`、`mutants.py`、`probes.py`、`msgid_scan.py`、`rev1.py`）與副本都在 scratchpad，未放進 repo；`D:\dxtest\rev1-f6`、`rev2-f6` 是本次新建的補量資料夾，沒有動其他 `D:\dxtest` 內容。

## 修正記錄

- 日期：2026-10-10，由 Claude 執行；分支 `fix/f6-unreadable-dictionaries`，起點 `2dc5328`。沒有 merge 進 `main`、沒有 push、沒有切換分支；沒有啟動 source-run 的 `gui.py`。主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 在修正前後 sha256 相同（4 個檔，`diff` 無差異），未 stage；`client2/`、`preprocessing/`、`testdata/`、`DotExpress-f7` 沒有動。
- 每個 commit 只 stage 明確路徑（`git diff --cached --stat` 確認），結尾 `Co-Authored-By: Claude Opus 5.5`。

| 發現 | 處理 |
| --- | --- |
| M-1 | `610c18a`：`_build_ui` 綁 `self.read_problem_ctrl.Bind(wx.EVT_SET_FOCUS, self._on_read_problem_focus)`，handler 做 `SelectAll()` 後 `event.Skip()`。新測試 `test_the_reason_is_selected_again_when_the_field_gets_focus` 直接呼叫 handler，斷言 `_FakeControl.calls == [("SelectAll",)]` 與 `Skip` 一次；先紅（`AttributeError: … '_on_read_problem_focus'`，`Ran 41`、`FAILED (errors=1)`），改後綠。測試不跑 `_build_ui`，speech-dialog 的 wx stub 不需改（`AutoSubmoduleModule` 會吸收 `wx.EVT_SET_FOCUS`），`test_dialog_validation`、`test_dictionary_entries_dialog`、`test_gui_document_flows` 照過。commit 前先在 scratchpad 用真正的 wx 4.2.5 做原型（清單＋唯讀多行欄位）：Tab `(0, 105)` → → `(105, 105)` → Shift+Tab → Tab `(0, 105)`；滑鼠點仍把游標放在點的位置 `(84, 84)`。packaged build（N-f6b）的結果見下 |
| M-2 | 未處理，待使用者決定（O7）。目前維持預設 (a)：對話框不長高，原因列顯示時清單變矮 |
| M-3 | `fd002d6`：`test_edit_on_a_dictionary_that_became_unreadable_stays_open` 加 `self.assertEqual(target._dictionary_counts, {})`；`test_validate_reads_every_row` 加 subtest `a wrong header, then Big5 after 17 KB of ASCII rows`（`b"x,y,z\r\n" + ASCII_ROWS + TAIPEI_ROW` 的 cp950），並把每個 subtest 改成同時斷言 `type(raised.exception) is error_type`（`UnicodeDecodeError` 是 `ValueError` 的子類別，只用 `assertRaises(ValueError)` 抓不到 x16）。mutant 證據見下 |
| M-4 | 未處理（匯入來源被鎖時仍是原始 `[Errno 13]`；spec D9 刻意保留既有訊息）。建議歸屬：follow-up，或 F-7 整理訊息時一起做；會改既有訊息，需使用者同意 |
| M-5 | 未處理（frame 守衛把建構子的任何例外都說成讀不到，並留下半建構的 dialog；spec Out of Scope）。建議歸屬：follow-up，把 `DictionaryEntryListModel.load` 移到 `super().__init__` 之前 |
| M-6 | `cdadbfe`：`read_problems` 拿掉模組層級的 `logger = get_logger(...)`，改在 `log_dictionary_read_error` 內呼叫 `get_logger("dotexpress.gui", "gui.log")`；log 內容不變，`isolate_file_logs` 對尚未建立 handler 的 logger 照樣有效，既有測試不用改。新測試 `test_importing_binds_no_log_file`（subprocess import `dictionaries.presenter` 與 `dictionaries.read_problems`，斷言 `dotexpress.gui` 沒有 handler）先紅（`AssertionError: [<FileHandler D:\workspace\DotExpress\client\log\gui.log (ERROR)>]`），改後綠。完整套件跑完後與 26 個 import 字典／對話框程式的測試模組逐一單獨執行後，`client/log/` 都只有原本的 `init.log`，sha256 不變 |
| M-7 | `aec3c64`：`CANNOT_OPEN` 的 msgstr 改為「或你沒有讀取權限」；`tests/test_i18n.py` 的預期字串同步（先紅 `FAILED (failures=1)`，改後 `Ran 18`、`OK`）；spec 兩個檔的字串表改成「你」，並在「Corrected after planning」之後新增「Corrected after review」／「審查後的修正」（M-1、M-3、M-6、M-7 與數量）；plan 末尾新增「Implementation Notes」（實作與 dry run 相同、沒有偏離，列出 Task 1–4 的 tree id，並註明這些審查修正；plan 的區塊保留原文）。auto-results 的 `<CANNOT_OPEN>` 定義在本記錄的 commit 中更新。catalog：`generate-pot.bat` → 固定 `POT-Creation-Date: 2026-10-10 12:00+0800` → `msgmerge --update` → `msgfmt --check` → `unix2dos`。M-1、M-6 讓 `dialog.py`、`read_problems.py` 的行號移動，所以 `.pot`／`.po` 的 `#:` 參照一起更新（兩檔各 15 個 `#:` 行）；`msgmerge` 也把 NOT_UTF8 與 CANNOT_OPEN 兩個 msgstr 依它自己的寬度重新折行（文字相同；之前的折行是手寫的，當時 `--update` 判斷沒變而沒有改寫檔案，以 `msgmerge -o` 對 `2dc5328` 的 `.po` 可重現同樣的折行）。結果：`364 translated messages.`、0 fuzzy；`.pot`／`.po` 各 365 個 `msgid` 行、31 個 `#~ msgid`；`POT-Creation-Date` 兩檔都是 `2026-10-10 12:00+0800`；再跑一次 `msgmerge -o` 輸出相同；第二次產生的模板除日期外相同；重建的 `.mo` 與 commit 的逐位元組相同（28,058 bytes，sha256 `4b865e4b…e6e2`）；`msgid_scan.py` → `source msgids: 364 sha256 7b53ff31…`（與 plan 相同，msgid 沒變） |
| M-8 | 未處理，待使用者決定（O1）。目前維持預設：選取時不自動朗讀原因，按 Tab 進欄位才讀；可與 item 52 的結果一起判斷 |

### Mutant（M-3）

主 checkout `client/` 的純複本（不含 `.venv`、`dictionary/`、`workspace/`、`config.json`、`log/`、`build/`、`dist/`）在 `$SP\f6fix\copy\client`，以 `python -B -X utf8` 跑對應模組；mutant 以腳本套用（CRLF-aware、舊文字恰好一次），跑完還原並以 `cmp` 確認與主 checkout 相同：

```text
x21（_store_count 錯誤路徑不 pop 舊筆數）+ 新測試：Ran 41, FAILED (failures=1)
  FAIL: test_edit_on_a_dictionary_that_became_unreadable_stays_open  AssertionError: {'alpha': 1} != {}
x16（validate_dictionary_csv 先讀完所有列再檢查表頭）+ 新測試：Ran 15, FAILED (failures=1)
  FAIL: test_validate_reads_every_row [a wrong header, then Big5 after 17 KB of ASCII rows]
  AssertionError: <class 'UnicodeDecodeError'> is not <class 'ValueError'>
x21、x16 + M-3 之前的測試（610c18a 的兩個測試檔）：Ran 41, OK；Ran 15, OK  -- 存活
未改的複本 + 新測試：OK
```

### 重建與 GUI（M-1、M-7；詳見 auto-results「審查後補充」）

| 項目 | 結果 |
| --- | --- |
| Build | 主 checkout `aec3c64`，PyInstaller 6.21.0，`Build complete!`；`dialog`、`dictionaries.read_problems`、`dictionaries.presenter`、`dictionaries.manager` 與 `gui` 都來自 `DotExpress\client\`。`D:\dxtest\N-f6b\DotExpress.exe`，48,749,506 bytes，sha256 `E1ED0B7712801B01950C08439EAE367D79423D4D1BE7A17A9CFB6514C4283BDA` |
| 42–45 ✔ | `auto42-f6b.log` 去掉新增的 `45 sel` 四行後與 `auto42-f6.log` 逐行相同 |
| 45 sel ✔（M-1） | N-f6b：Tab `(0, 61)` → → `(61, 61)` → Shift+Tab（`ListItem big5`）→ Tab `('Edit', '無法讀取的原因：') (0, 61)`。同一腳本在 N-f6（`auto42n6-f6b.log`）最後仍是 `(61, 61)`，重現本審查的量測 |
| 47 ✔（M-7） | `auto47-f6b.log`：原因 `無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。`，`(0, 42)`、兩行；其餘與 `auto47-f6.log` 相同 |
| 程序 | 結束後沒有 exe 位於 `D:\dxtest\*f6b*`／`N-f6*` 的程序，也沒有 `lockx.py` |
| item 52 | 仍待使用者（NVDA）；auto-results 的人工步驟改用 N-f6b（`D:\dxtest\manual52-f6b\`），並加上「按 → 之後 Shift+Tab、Tab 回來仍讀完整原因」 |

`item42.py` 新增四行 `45 sel` 與 docstring 說明，和 auto-results 一起在本記錄的 commit 中提交。

### 最終驗證

- 完整套件：`cd client && .venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests` → `Ran 1337 tests`，`FAILED (errors=1, skipped=7)`；唯一 error 為 F-W6 的 `test_dictionary_name_prompt … test_case_only_rename_still_renames`。1337 = 1335 + 2 個新測試（M-1 的 `test_the_reason_is_selected_again_when_the_field_gets_focus`、M-6 的 `test_importing_binds_no_log_file`；M-3 是既有測試的斷言與 subtest）。
- fixtures：`git show HEAD:client/tests/fixtures/translation_golden.json | sha256sum` → `e67d95a1…1ccd`，`dictionary_entries_trace.json` → `f493da52…c2cf`，與要求相同。
- 受限檔案：`client/braille/tables/__tables.py`、`client/braille/liblouis/`、`client/braille/tables/__init__.py` 沒有在任何修正 commit 中。
- `HEAD:client` tree（`aec3c64`）：`31560e3e2f2984f5a263acc271e1937fb267c152`。
