# F-8a 資料安全收尾（第一部分）審查記錄

- 日期：2026-10-10
- 範圍：主 checkout `D:\workspace\DotExpress` 的 `fix/f8-data-safety-cleanup`，`main...fix/f8-data-safety-cleanup`（base `861d110`；7 個 commit：`bfd24db` spec、`62e76ce` plan、`4323045` D1／D2 不取代未列出的套件、`a529284` D6／D7 腳本與字典原子寫入、`12f099e` D8 匯出失敗保留舊檔、`725376f` D9–D11 `config.json`、`22842ac` GUI 結果）。production diff `git diff main...HEAD -- client`：7 個 production 檔（`config.py` +74／−8、`documents/workspace_service.py` +33／−2、`documents/workspace.py` +27／−2、`dictionaries/manager.py` +31／−8、`conversion/preprocessing/user_script.py` +27／−20、`documents/formats.py` +4／−2、`gui.py` +8／−2）、8 個測試檔（新檔 `tests/full_disk.py` 81 行；`test_config.py` +188、`test_workspace_service.py` +112／−10、`test_gui_document_flows.py` +115／−17、`test_dictionary_manager.py` +81、`test_user_preprocessing_script.py` +47、`test_document_workspace.py` +43、`test_document_formats.py` +29），加上 spec 兩檔（各 632 行）、plan（4129 行）、本資料夾的 `auto-results.md` 與 6 個 `auto/` 腳本；共 25 個檔，與 plan「Global Constraints」列出的 15 個 `client/` 檔完全相同。每個實作 commit 的 `HEAD:client` tree id（`90a71c13…`、`adcfa533…`、`12837b65…`、`62ea9d3e…`）都與 plan「Expected Counts」相同；`22842ac` 之後仍是 `62ea9d3e…`。
- 對照：`docs/superpowers/history/2026-10-10-02-handoff/HANDOFF.md` §1、§2、§6；`AGENTS.md`；`docs/superpowers/specs/2026-10-10-f8-data-safety-cleanup-design.md`（含 `_zh-TW.md`，「Corrected after planning」／「規劃後的修正」13 點；F-8a = D1–D2、D6–D11）；`docs/superpowers/plans/2026-10-10-f8a-data-safety-cleanup.md`；本資料夾的 `auto-results.md` 與 `auto/`；`task.md`（使用者的決定：#5、#10、F-7 M-4 為 F-8；U+0000 屬 F-8b）；`2026-10-10-04-f7-dialog-buttons-surrogates-close/review_task.md`（格式）。
- 審查方式：逐行讀 7 個 production 檔的 diff 與 `shared/atomic_write.py`、`move_document_package` 全文、`load_document_package`、`batch_import_documents`、`export_coordinator.py` 全文、`log.py`、`tests/file_log_isolation.py`、`tests/windows_file_handles.py`、`documents/session.py` 的 `document_name_exists`、`shared/name_validation.py`；8 個測試檔的 diff；對 D1 的每條入口（名稱對話框、`create_document`、`move_document_package` 的安裝步、`import_files`、預設文件）、每個 writer 的每個失敗分支（callback 內例外、`flush`／`fsync`、`os.replace` 的共用衝突、暫存檔被掃描程式占住、磁碟滿、唯讀、隱藏、資料夾、資料夾不存在）、`config.json` 的每種檔案狀態逐一推演；在 Windows 11 跑完整套件；在 scratchpad 的 `client/` 副本（`git archive HEAD client` 加上複製的 liblouis runtime；不含 `.venv`、`dictionary/`、`workspace/`、`config.json`、`log/`）跑 8 組探針（P1–P8）與 35 個自寫 mutant（plan 的 26 個之外）；稽核 22 個 `D:\dxtest\auto*-f8a.log`／`auto*-f7-f8a.log` 與 exe 雜湊；另以 pywinauto 在新的 `D:\dxtest\rev1{a,b,c,d}-f8a` 對 N-f8a 補量 4 個情境（只結束該資料夾底下的程序；沒有任何腳本讀寫剪貼簿）。主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 在審查前後 sha256 相同；沒有啟動 source-run 的 `gui.py`；沒有動 `client2/`、`preprocessing/`、`testdata/`、`task.md`、兩個 worktree；沒有 stage 任何東西。凡未能驗證的標為「推理」。
- 本記錄只寫檔，未 commit。

## 驗證（Windows 11 26200，`$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`，`$SP` = session scratchpad 的 `f8areview\`）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| app data | 審查前後 `(find client/dictionary client/workspace client/log -type f; ls client/config.json) \| sort \| xargs sha256sum`，`diff` | 4 個檔（`config.json` `eea87b39…`、`dictionary/default.csv` `8f0594e9…`、`log/init.log` `1b787580…`、`workspace/new.dep` `d0cb6539…`）相同；`git status --short` 全程只有本來就 untracked 的 `client2/`、`preprocessing/`、`task.md`、`testdata/`（本記錄寫入前） |
| 完整套件（驗收 1） | `cd client && $PY -B -X utf8 -m unittest discover -s tests` | `Ran 1400 tests in 20.929s`、`FAILED (errors=1, skipped=7)`；唯一 error 為 F-W6 `test_dictionary_name_prompt … test_case_only_rename_still_renames`。1400 = 1368 + 32（10 + 8 + 3 + 11），與 plan「Expected Counts」相同 |
| 焦點模組（副本） | `$PY -B -X utf8 -m unittest <模組>`（mutant 腳本的 unmutated 基準） | `test_workspace_service`＋`test_document_workspace`＋`test_gui_document_flows`：`Ran 311`、`OK (skipped=2)`；`test_config`：`Ran 45`、`OK`；`test_dictionary_manager`：`Ran 20`、`OK`；`test_document_formats`＋`test_document_workspace`＋`test_export_coordinator`：`Ran 102`、`OK (skipped=2)`；`test_user_preprocessing_script`：`Ran 15`、`OK`（Windows-only 的 A3、A9、A15、C5 NTFS subTest 都有跑） |
| catalog | `msgfmt --check --statistics -o /dev/null …po`；`grep -c '^msgid '`；`grep -c '^#, fuzzy'`；`git diff main...HEAD --stat -- client/locales` | `364 translated messages.`；365 個 `msgid` 行（364 + header）；0 fuzzy；locale diff 為空（本任務沒有字串，D15 屬 F-8b） |
| fixtures、受限檔案 | `git show HEAD:client/tests/fixtures/… \| sha256sum` × 2；`git diff main...HEAD --stat -- client/braille AGENTS.md`；`git ls-files --eol` | `e67d95a1…1ccd`、`f493da52…c2cf`，與 HANDOFF §2 相同；`client/braille`、`AGENTS.md` 不在 diff 中；`client/braille/tables/__init__.py` 仍是 `i/crlf w/crlf`；25 個改動的檔在 index 都是 `i/lf`；spec、plan、auto-results 都是 `i/lf w/lf` |
| 縮排／ASCII | `grep -c $'^\t'`／`'^    '`／`-P '[^\x00-\x7F]'` 逐檔 | `gui.py` tab（diff 新增的行都是 tab；7 行 4 空白是既有的 import 清單）；其餘 6 個 production 檔與 8 個測試檔 0 個 tab；7 個 production 檔與新檔 `full_disk.py` 純 ASCII；測試檔的非 ASCII 是既有的或是釘位元組的 CJK／點字（`EXCEL_DICTIONARY`、「雙視」）；落單 surrogate 以 `chr(0xD800)` 建立，沒有 `\u` escape；6 個 GUI 腳本都是 tab |
| 驗收 7（來源掃描） | `grep -rn "shutil\.copyfile(\|\.write_text(\|\.write_bytes(\|open(…\"w"` 排除 tests、`.venv`、`build`、`mathcat`、`braille/liblouis`、`shared/atomic_write.py`、`dual_view/files.py` | 只剩 `documents/workspace.py:120` `PackageFiles.write`（F-3 的私有 staged 檔，spec Corrected 13 已列）；`app_paths.py` 的探針用 `"a"` 模式 |
| commit | `git log --format='%h %ci %s%n%(trailers)' main..HEAD` | 7 個 commit 都以 `Co-Authored-By: Claude Opus 5.5` 結尾；沒有 merge、沒有 push；時間順序 spec 17:38 → plan 19:00 → t1–t4 19:03–19:05 → N-f8a build 19:10（exe mtime 19:10:30）→ GUI log 19:15–19:17 → docs 19:19 |
| GUI 結果稽核 | 讀 22 個 `D:\dxtest\auto{66,67,68,69,76,77,78,79,80,81,82}-f8a.log` 與 `…-f7-f8a.log`；`sha256sum D:\dxtest\N-f8a\DotExpress.exe` | 每個 log 的關鍵行（66–68 的 `box`／`shown again`／`import issues`、`bad.dep unchanged`，69 的 `new (2)`，76 的位元組與 `sha 6d8d6724… crlf 25 lf 25`，77／78 的 `[WinError 5]` 與 `OLD … EXPORT`，79 的 `.bak b'null'`，80 的無 BOM 且 width 30 保留，81 的兩行 WARNING 與 `unchanged: True`，82 的四個 sha256 前綴）都與 auto-results 逐字相符；改前（N-f7）確實是 `box: None`、`bad.dep unchanged: False`、`alpha is gone`、`docs ['new']`、`文件已成功匯出。`、`exited with code 1`、`font_size: 13`；exe `5942454c…66f3`、48,755,723 bytes，與 auto-results 相同；每個 `auto*-f8a` 只有一個 log，沒有 `try1` |
| 探針（P1–P8） | `cd $SP\copy\client && $PY -B -X utf8 $SP\probes.py`（logger 以 `isolate_file_logs` 隔離；只寫在 `%TEMP%\f8areview-*`，跑完刪除） | 見 §2.1 |
| 自寫 mutant（35 個） | `$PY -B -X utf8 $SP\mutants.py $SP\copy\client`（每個 mutant 只改一個檔，舊文字恰好一次，跑對應模組，跑完還原並比對位元組） | 31 個被抓到，4 個存活：r01（`lexists`→`exists`，Windows 上沒有 symlink 時等價）、r32（成功讀取後不清除 `_logged_skipped_saves`，見 M-3）、r34（`_copy_file_into` 改用文字模式再 `encode`，見 M-2）、r35（在 `import_files` 寫入前再加一次磁碟檢查，所有測試照過，見 M-1）。被抓到的 31 個涵蓋 spec 驗收 8 中屬於 F-8a 的每一項（提示框沒有磁碟檢查、`exclude_name` 不 casefold、`create_document` 沒有檢查、移動守衛放在移開之前／拿掉、`import_files` 只看 controller、`free_document_name` 回 base 或從 (1) 起算、每個 writer 改回舊呼叫、`newline=""`、`utf-8-sig`、接受非物件、`OSError` 後仍寫、不備份、備份失敗仍寫、`_load` 回傳普通 dict、匯出到資料夾不先檢查） |
| 補量（rev1a–d） | `$SP\..\uia\Scripts\python.exe $SP\rev1.py D:\dxtest\N-f8a\DotExpress.exe D:\dxtest\rev1<x>-f8a <x>` | 見 §2.2；結束後 `tasklist` 沒有 DotExpress 程序 |
| 未執行 | — | 項目 84（磁碟快滿的 VHD，仍待使用者；`full_disk` 與探針 P8 以注入覆蓋同一條路徑）；POSIX-only 測試（7 個 skip）；F-W6；plan Task 5 的 shuffle（新測試都用獨立暫存目錄並隔離 logger，推理不互相影響） |

## 結論

**Ready**（項目 84 仍待使用者人工，與 auto-results「仍需人工」一致）。

沒有 Critical、沒有 Important。D1 的四條入口（名稱對話框、`create_document`、`move_document_package` 的安裝步、`import_files`）都看磁碟，只差大小寫的改名因 `exclude_name` 的 casefold 與「移開之後才檢查」不受影響，GUI 66–69 與補量 a、d（大小寫變體、資料夾）證實；D2 的 `new (2)` 在 GUI 69 與測試都正確。D6–D9 的四組 writer 全部改走 `shared.atomic_write`，成功時的位元組逐一與改前相同（探針 P4 用 7 組含 CRLF、落單 `\r`、CJK、U+FFFD 的樣本與 `Path.write_text` 比對、`config.json` 與 `open("w")+json.dump` 比對、字典複製與 `copyfile` 比對，全部相同；GUI 76、82），失敗時目標保持原樣且沒有 `.tmp`（GUI 77、78；探針 P7 的共用衝突）。`write_export_text` 讓匯出到資料夾仍是 `[Errno 13] Permission denied: '<dir>\alpha.brl'`（補量 b 在 packaged build 證實，mutant r19 被三個測試抓到）。D10／D11 的 BOM、非物件、`.bak`、不可讀不寫入都有測試釘住，GUI 79–81 與探針 P6 的 10 種檔案狀態（空檔、只有空白、只有 BOM、UTF-16、`null`、`.bak` 唯讀、`.bak` 是資料夾、`config.json` 是資料夾、隱藏、被共用讀開著）都沒有丟掉可讀的設定。`full_disk` 注入同時打到舊的就地寫入與新的原子寫入，每個 red 都有真正的理由。catalog、fixture、受限檔案、使用者資料都沒動；35 個自寫 mutant 只有 4 個存活（1 個等價、3 個是測試缺口或可選的對稱補強）。

下面 8 個 Minor 中，M-1、M-2、M-3、M-6 便宜，建議 merge 前一起修；M-4、M-5 是文件或可選的小修；M-7、M-8 是觀察。O2、O4、O6 與「隱藏檔案」四個預設請使用者看一眼（§6 末表）。

## 1. 逐路徑分析

### 1.1 D1／D2：磁碟上有、但不在清單中的套件

| 路徑 | 結果 | 依據 |
| --- | --- | --- |
| 名稱對話框（新增、改名） | `document_name_exists(name, exclude_name)`（controller，casefold）**或** `package_name_taken(name, exclude_name)`（`os.path.lexists(<workspace>/<name>.dep)`；NTFS 不分大小寫，資料夾與壞掉的連結也算）→ 既有的 `文件「{name}」已存在。` 錯誤框，名稱對話框重新顯示並預填 | `gui.py:711-714`；T C7、C8；mutant r10；GUI 66、67；補量 a（`BAD` 對上未列出的 `bad.dep`）、d（`bad.dep` 是資料夾） |
| 只差大小寫的改名 | `exclude_name` 以 casefold 比對，`Alpha`→`alpha` 不算被占；安裝步的 `files.exists(new_path)` 在舊套件移開之後才檢查，所以不會找到自己 | `workspace_service.py:103-104`、`workspace.py:201-202`；T C5「its own package, any case」、C3 的 `CaseInsensitivePackageFiles`、既有的 `test_case_only_rename_keeps_the_document`（真 NTFS）；mutant r02、r07（守衛放到移開之前時 9 個大小寫測試爆掉）；GUI 67 |
| `create_document`（新增、預設文件） | 寫入前 `os.path.lexists(package_path)` → `FileExistsError(EEXIST)`，`_create_document` 以 `儲存文件失敗：[Errno 17] File exists: '…\bad.dep'` 顯示；這條守住提示之後才出現的檔案 | `workspace_service.py:161-164`；T C1；mutant r03；探針 P5（`BAD.dep` 資料夾） |
| `move_document_package` 的安裝步 | `files.exists(new_path)` → `FileExistsError`，既有的 `except` 把舊套件放回、刪掉 staged 檔；磁碟上只剩舊套件與那個第三檔，沒有 `.tmp` | `workspace.py:200-210`；T C2、C3；mutant r06；探針 P5（`gamma`→`bad`，`gamma.dep` 仍在、無 `.tmp`） |
| `import_files` | `existing_names` = controller 名稱 ∪ `workspace.glob("*.dep")` 的 stem（Windows 的 `Path.glob` 不分大小寫，`Alpha.DEP` 也抓到）；`batch_import_documents` casefold 比對，列為 `Document "bad" already exists.` 匯入問題。工作區資料夾不存在時 `glob` 回空清單，不拋例外 | `workspace_service.py:170-175`；T C4（`Bad.dep` 對 `bad.txt`）；mutant r04、r05；GUI 68；探針 P5 的 `on_disk stems` |
| 預設文件 | `free_document_name("new")`：controller 或磁碟有就試 `new (2)`、`new (3)`…；`new (2)` 通過 `normalize_base_name` | `workspace_service.py:106-113`、`gui.py:725-732`；T C6、C10；mutant r08、r09、r11；GUI 69；探針 P5（39 個碰撞 → `new (40)`；`x (2)` → `x (2) (3)`） |
| 開啟中文件的存檔 | 不變：目標是自己的套件 | diff（`save_open_document` 未動） |
| 檢查與 `os.replace` 之間的 race | `create_document` 與安裝步都是「先檢查、再 `os.replace`」，兩者之間（微秒級）另一個程序建出的同名檔仍會被取代；`import_files` 只在批次開始時看一次磁碟，整批寫入期間沒有再檢查（見 M-1）。只有另一個 DotExpress 或外部工具同時寫工作區才會發生，spec Non-goals 列為不處理 | 推理 |
| 名稱正規化不一致的檔 | `bad .dep`（stem 尾端空白）：`package_name_taken('bad')` 不算被占、匯入的 stem 是 `'bad '` 也對不上，所以會另外建 `bad.dep`，兩個都保留，沒有遺失 | 探針 P5 |

### 1.2 D6：文字處理腳本

| 面向 | 結果 | 依據 |
| --- | --- | --- |
| 位元組 | `write_text_atomically(..., encoding="utf-8", newline="")`，不轉換換行；A1 的來源含 `\r\n`，mutant r12（`newline=None`）被抓到 | `user_script.py:61`；T A1、A4；GUI 82（`preprocessing.py` 位元組與改前相同） |
| 失敗 | callback 內的 ENOSPC → 舊腳本原樣、無 `.tmp`；唯讀 → `ensure_writable` 給 `[Errno 13] Permission denied: '<script>'`（改前是 `[WinError 5] …tmp -> …`，spec D6 已列） | T A2、A3；mutant r13 |
| `os`／`tempfile` import | 已移除；A4 的 patch 目標改成 `os.replace`（全域 wraps） | diff |

### 1.3 D7：字典檔

| 面向 | 結果 | 依據 |
| --- | --- | --- |
| 表頭 | `_write_header` 經 `write_text_atomically(newline="")`，`text,braille,type\r\n` 不變；`fsync` 一次 | T A5；mutant r16、r17；GUI 82 |
| 匯入 | `write_bytes_atomically(dest, lambda s: _copy_file_into(source, s))`：來源打不開或讀到一半的錯誤都在 callback 內拋出，暫存檔移除、沒有半套字典被列出 | T A6；mutant r15 |
| 匯出 | 舊檔在複製完成並 `fsync` 之後才被取代；被其他程式以共用讀寫開著時 `os.replace` 失敗 `[WinError 5]`，舊檔不動；匯出到自己的檔案現在會以同樣位元組重寫（改前 `SameFileError`） | T A7、A8、A9；mutant r14；探針 P4 |
| 複製的位元組 | BOM、CRLF、CJK、`\x00\xff` 等非 UTF-8 位元組都逐一相同；但測試只用合法 UTF-8，mutant r34（文字模式讀再 `encode`）存活，見 M-2 | 探針 P4；mutant r34 |
| 匯出到資料夾 | 訊息從 `[Errno 13] Permission denied: '<dest>'` 變成 `[WinError 5] 存取被拒。: '…\.math.csv.<hex>.tmp' -> '…\math.csv'`；wx 的另存對話框打到資料夾名稱會進入該資料夾，所以實務上到不了（見 M-5） | 探針 P3 |

### 1.4 D8：BRL／HTML 匯出

| 面向 | 結果 | 依據 |
| --- | --- | --- |
| 位元組 | `write_export_text` 用 `newline=None`，CRLF 與 `Path.write_text` 相同；含 `\r\n` 的點字一樣變 `\r\r\n`（與改前相同） | 探針 P4（7 組樣本）；T A12；mutant r18；GUI 76 |
| 失敗 | 編碼錯誤（落單 surrogate）或 ENOSPC → 舊檔原樣、無 `.tmp`；HTML 先 render 再寫（順序不變） | T A10、A11；mutant r20、r21 |
| 資料夾 | `destination.is_dir()` 先給 `PermissionError(EACCES)`，訊息仍是 `[Errno 13] Permission denied: '<dir>\alpha.brl'`，F-7 的三個 coordinator 測試與項目 56 釘住的文字不變 | `workspace.py:272-276`；mutant r19；補量 b（packaged build 的全部匯出摘要） |
| 被其他程式開著 | `[WinError 5] …: '<d>\out\.old.brl.<random>.tmp' -> '<d>\out\old.brl'`，舊檔不動（spec O6、Risks） | T A9（字典）、探針 P7；GUI 77、78 |
| 暫存檔被掃描程式占住 | 探針模擬 AV 在 `os.replace` 當下以共用讀開著暫存檔：`[WinError 32]`，舊檔不動，但 **暫存檔留下**（`unlink` 也失敗，被 `suppress` 吞掉）。這是 `atomic_write` docstring 寫明的限制（"unless removing it fails"），對套件自 F-3 起就是如此；匯出資料夾是使用者看得到的地方，見 M-4 | 探針 P7 |
| 資料夾不存在 | `export_document_brl` 有 `mkdir`；`_write_html` 沒有（與改前相同），訊息從 `[Errno 2] …: '…\gone\alpha.html'` 變成 `…: '…\gone\.alpha.html.<hex>.tmp'`（見 M-5） | 探針 P2 |
| 其他路徑 | `.dep` 匯出的 `_write_dep` 本來就原子；`Ctrl+E` 與全部匯出都經 `ExportCoordinator.write_document` → 同一個 writer | `export_coordinator.py`、`formats.py:97-110` |

### 1.5 D9–D11：`config.json`

| 檔案狀態 | 結果 | 依據 |
| --- | --- | --- |
| 正常 | 原子寫入，CRLF 位元組與 `open("w")+json.dump` 相同；`fsync` 每次一次 | T A13、A15；探針 P4；mutant r27、r33 |
| 寫入失敗（ENOSPC、被共用讀開著） | 舊檔原樣、無 `.tmp`、`ERROR` log 一筆（每次失敗都記，與改前相同） | T A14；探針 P6d |
| UTF-8 BOM | `utf-8-sig` 讀取，不記 log；下一次寫入去掉 BOM、其他設定保留 | T B1；mutant r22；GUI 80 |
| `null`、list、str、int | `_load` 內拋 `ValueError("config.json does not hold a JSON object (<type>)")`，一次 WARNING，回 `_UnreadableConfig`；程式可以啟動 | T B2；mutant r23；GUI 79 |
| 損壞（JSON 截斷、cp950、非物件、空檔、只有空白、只有 BOM、UTF-16） | 第一次變更前把原始位元組複製到 `config.json.bak`（原子寫入，覆蓋舊的 `.bak`），再寫新檔；啟動時 client id 的寫入就是那「第一次」，所以 `.bak` 在啟動時就產生 | T B3、B4；mutant r25、r30、r31；探針 P6e、P6f；GUI 79 |
| `.bak` 寫不進去（唯讀、是資料夾、檔案在中間被刪） | 不寫 `config.json`，`ERROR` log；之後每次設定變更都如此，直到使用者處理 `.bak`（見 M-7） | T B6；mutant r26；探針 P6a、P6b |
| 讀不到（`PermissionError`、是資料夾、被鎖） | 不寫；`WARNING` `Config file %s was not saved because it could not be read` 每個不同錯誤只記一次，成功讀取後重新計數（這一條沒有測試，mutant r32 存活，見 M-3） | T B5；mutant r24、r28、r29；探針 P6c；GUI 81 |
| 隱藏 | 改前 `open(path, "w")` 在隱藏檔上是 `[Errno 13]`，**設定存不進去**（只記 log）；改後 `os.replace` 成功，檔案被換掉並失去隱藏屬性，設定保留。匯出檔、字典檔、腳本同理（F-3 D11 的取捨，spec D9 有寫） | 探針 P1；補量 c |
| `_UnreadableConfig` 的傳遞 | `_set_section_value`、`set_lang`、`set_view_settings`、`get_or_create_client_id` 都 `data[...] = …; self._save(data)`，同一個物件，`isinstance` 保留 | `config.py:189-194, 215-220, 268-277, 279-289` |
| 「變更在本次 session 仍生效」 | 設定對話框與 frame 自己保存值（`self.translation_tables` 等），getter 雖每次重讀檔案，但 UI 用的是記憶體中的值；這點 spec D11 的敘述成立。不可讀時沒有任何 UI 提示，只有 `config.log`（O4，請使用者看一眼） | `gui.py:212`、`settings/*.py`；推理 |
| 兩個執行緒／兩個程序同時寫 | 原子寫入讓結果是「最後寫入者的完整檔案」，不再有交錯截斷；client-init 執行緒與 UI 的讀改寫 race 仍在（spec 列為不處理） | 推理 |

### 1.6 測試與 `full_disk`

- `full_disk(folder, after=N, pattern=…)` 同時 patch `builtins.open` 與 `io.open`，在 `write` 時而不是 `flush`／`close` 時拋 ENOSPC；對 `write_text_atomically`（`open(..., opener=…)`）、`Path.write_text`、`shutil.copyfile`、`NamedTemporaryFile`（以資料夾為 `file` 參數的 opener 開法）都打得到，讀取與其他資料夾不受影響，區塊結束後 `open` 還原（探針 P8）。真正的磁碟滿多半在 `flush`／`close` 才報錯：那條路徑在 `_write_atomically` 裡是 `with` 退出時 `close()` 再 `flush` 一次、`finally` 移除暫存檔，結果一樣（推理；項目 84 才是真實驗證）。
- 五個原本用「同名資料夾」讓寫入失敗的測試改用 `full_disk` 或 `_FailingReplacePackageFiles(destination_name=…)`，意圖不變，且訊息改為精確比對 `[Errno 28] No space left on device`。
- `test_config` 在 `setUpModule` 隔離 `dotexpress.config`；`test_gui_document_flows` 本來就隔離 `dotexpress.gui`；`manager.py`、`workspace*.py`、`user_script.py` 不記 log。完整套件跑完主 checkout 的 `client/log/` 沒有新檔（sha256 相同）。
- Windows-only 測試 4 個（A3 唯讀腳本、A9 共用讀寫開著的匯出目的檔、A15 CRLF、C5 的 NTFS subTest）都有跑；A9 在 `finally` 先釋放 handle 再讓 `tearDown` 刪資料夾。
- `Mock` service harness 設 `package_name_taken.return_value = False`、`free_document_name.side_effect = lambda base: base`，否則 truthy 的 `Mock` 會讓名稱提示無限迴圈（spec 有寫）。
- `ConfigDataSafetyTest.setUp` 只清 `_logged_load_failures`，沒清 `_logged_skipped_saves`（見 M-3）。

## 2. 補量

### 2.1 探針（`$SP\probes.py`，scratchpad 副本，Python 3.13.15）

| # | 量測 | 結果 |
| --- | --- | --- |
| P1 | 隱藏檔：`open("w")`、`write_text_atomically`、隱藏的 `config.json` 設定變更 | `open("w")`：`[Errno 13]`；原子寫入成功、`hidden now: False`；`config.json` 被換成含新設定的檔、原有 `font_size: 20` 保留、不再隱藏、無 log |
| P2 | 匯出到不存在的資料夾 | 改前 `[Errno 2] …: '…\gone\alpha.html'`；改後 `[Errno 2] …: '…\gone\.alpha.html.<hex>.tmp'`；字典匯出同樣命名 `.x.csv.<hex>.tmp` |
| P3 | 匯出到資料夾 | 字典：改前 `[Errno 13] Permission denied: '…\math.csv'`，改後 `[WinError 5] …: '…\.math.csv.<hex>.tmp' -> '…\math.csv'`；BRL／HTML：仍是 `[Errno 13] Permission denied: '…\alpha.brl'`；兩者都沒留 `.tmp` |
| P4 | 位元組 | 7 組樣本 `Path.write_text` 與 `write_export_text` 相同；`config.json` 與 `open("w")+json.dump` 相同（CRLF）；字典複製與 `copyfile` 相同（含 BOM、CRLF、`\x00\xff`） |
| P5 | 名稱邊界 | `BAD.dep` 資料夾、`bad .dep`、`Alpha.DEP` 都列為無效並保留；`package_name_taken` 對 `bad`／`Bad`／`alpha`／`ALPHA` 都 True，`gamma` False；39 個碰撞 → `new (40)`；`x (2)` → `x (2) (3)`；30 字的 base 會產生 34 字的名稱，`normalize` 拒絕（只有 `new` 會用到，見 M-8）；`create_document("BAD")` → `[Errno 17] File exists: '…\BAD.dep'`；`gamma`→`bad` → `[Errno 17] …'bad.dep'`，`gamma.dep` 仍在、無 `.tmp` |
| P6 | `config.json` 狀態 | a 損壞＋`.bak` 唯讀：兩次變更都 `ERROR`、檔案不動；b `.bak` 是資料夾：同上（`[WinError 5] …tmp -> config.json.bak`）；c `config.json` 是資料夾：預設值、兩次變更只記一次 WARNING；d 正常檔被共用讀開著：`[WinError 5]` `ERROR`、位元組不變、無 `.tmp`；e `null`＋client id：`.bak b'null'`、之後的 view 變更不再動 `.bak`；f 空檔／只有空白／只有 BOM／UTF-16：預設值，`.bak` 存原始位元組，新檔寫入 |
| P7 | 暫存檔清理 | 目的檔被共用讀寫開著：`[WinError 5]`，`OLD` 保留、無 `.tmp`；模擬 AV 在 `os.replace` 時以共用讀開著暫存檔：`[WinError 32]`，`OLD` 保留，**`.old.brl.<hex>.tmp` 留下** |
| P8 | `full_disk` | `create_dictionary` 與 `open(mode="w")` 都 `[Errno 28]`；讀取不受影響；舊檔只被寫到 `after` 個字元（就地寫入的真實後果）；區塊後 `builtins.open` 還原 |

### 2.2 packaged build 補量（`D:\dxtest\rev1{a,b,c,d}-f8a`，N-f8a；每個情境新資料夾，結束後無殘留程序）

| 情境 | 結果 |
| --- | --- |
| a `alpha` 有效、`bad.dep` 無效（保留）；改名 `alpha`→`BAD` | `錯誤` 框 `文件「BAD」已存在。`，名稱對話框重新出現 `{'buttons': ['確定', '取消'], 'name': 'BAD'}`；`docs ['alpha']`，兩個檔 sha256 不變 |
| b 全部匯出 BRL 到 `out\`，其中 `alpha.brl` 是資料夾 | 覆蓋問題回答是；摘要 `Export Complete with Errors`／`alpha: [Errno 13] Permission denied: '<d>\out\alpha.brl'`（與 F-7 項目 56 相同的文字）；`beta.brl` 寫出 `⠃⠑`；資料夾仍在；無 `.tmp` |
| c 隱藏的 `config.json`（font 20、width 30） | 啟動後檔案已被 client id 的寫入換掉：`hidden: False`、width 30 與 font 20 都在、無 `.bak`、`config.log` 空；Ctrl＋滾輪後 `font_size: 21`、width 30 仍在 |
| d 工作區有一個名為 `bad.dep` 的資料夾（內含檔案）；新增 `bad` | 啟動列為無效、保留；`錯誤` 框 `文件「bad」已存在。`，對話框重新出現；`docs ['alpha']`；資料夾與裡面的檔案原樣 |

## 3. Logging、測試隔離、測試品質

- `config.py` 新增的 `_skip_save_of_unreadable_file` 以 `exc_info=error` 附上讀取錯誤的 traceback；`_log_current_exception` 的 `exc_info` 參數預設 `True`，既有呼叫不變。
- `_backup_unreadable` 的失敗走既有的 `Failed to save config file` `ERROR`，與 spec Corrected 8 相同。
- 沒有新的 logger、沒有新的 log 檔；`dotexpress.gui` 在本任務沒有新的記錄點（D3 的記錄屬 F-8b）。
- 測試只用暫存目錄；`full_disk` 的 `pattern` 讓同一個資料夾裡其他檔案的寫入不受影響；`test_a_change_after_an_unreadable_load_does_not_write` 只攔 `builtins.open` 對該路徑的讀取，`write_text_atomically` 的 `open(..., mode="w")` 不受影響。
- red-first：plan 的每個 red 區塊都有理由（舊的就地寫入留下半檔或空檔、`NamedTemporaryFile` 留下 `.tmp`、沒有 `fsync`、8 字元暫存名、`AttributeError`、無 `.bak`）；dry run 已重放，本次以 mutant 反向驗證（31／35）。

## 4. 本地化

- 沒有新字串；`.pot`／`.po`／`.mo` 與 `main` 逐位元組相同，`msgfmt` 364 translated、0 fuzzy。
- 仍是英文的可見字串都是既有缺陷：全部匯出的摘要標題與內文（P1-4 defect 4；補量 b 與 GUI 78 可見）、匯入問題的 `Document "bad" already exists.`（不是 msgid，spec 列為沿用）。
- 新出現在使用者面前的英文是 OS 錯誤文字（`[Errno 17] File exists`、`[Errno 28] No space left on device`）與 Windows 的中文 `[WinError 5] 存取被拒。`，與 F-3 以來的做法一致。

## 5. 文件與流程

- spec（EN／zh-TW 各 632 行，「Corrected after planning」／「規劃後的修正」13 點對應）、plan、auto-results、實作四者一致：D1、D2、D6–D11 都找得到對應程式與測試；Corrected 1–13 都反映在實作（拆成 F-8a、`Ran` 1378/1386/1389/1400、`full_disk`、五個改注入方式的測試、Mock harness、`write_export_text`、`_write_header`、`_UnreadableConfig` 與 `_logged_skipped_saves`、`test_config` 隔離、測試細節、GUI 項目 66–69／76–82 的做法與 81 的共用模式）。
- 使用者的決定（task.md：#5、#10、F-7 M-4 併入 F-8；U1 的 U+0000 屬 F-8b）都照做；F-8a 沒有碰 `conversion/`、`ui/conversion_presenter.py`、dual view，與 F-9 的切割成立。
- HANDOFF §6 的三個項目（F-3 M-1、priority 3 的三個 writer、F-7 M-4）在本任務關閉；「啟動時回收孤兒 `.tmp`」留給 F-8b 的 D3。
- plan 沒有「Implementation Notes」一節（HANDOFF §3 說 plan 末尾有；F-7 審查 M-3 已要求過一次）。四個 tree id 與 dry run 逐一相同、沒有偏離，可接受，但建議補一句，見 M-6。
- auto-results 的「仍需人工」只有項目 84，措辭清楚，沒有被代為勾選。
- GUI 腳本只以 `dx.kill_under(d)` 結束該資料夾下的程序；`lockshare.py` 是獨立程序，由 `F.unlock` 結束；沒有任何腳本讀寫剪貼簿（`grep` 確認，`f8agui.py:8` 也明寫）。
- `AGENTS.md` 是 git-ignored，無法以 git 確認本任務沒改它（推理：diff 與 commit 都沒碰；本審查也沒改）。

## 6. 發現

### Critical

無。

### Important

無。

### Minor

**M-1 `import_files` 寫入前沒有第二次磁碟檢查**（`client/documents/workspace_service.py:170-186`；`create_document` 有，`move_document_package` 有，匯入只在批次開始時 `glob` 一次）
- 情境：匯入多個檔案期間，另一個 DotExpress 或外部工具在工作區建出同名的 `.dep`，`save_document_package` 的 `os.replace` 仍會取代它。視窗很窄，spec Non-goals 也排除並行程序，但與 D1 其他入口不對稱。
- 建議（便宜，3 行＋1 個測試）：迴圈內 `save_document_package` 之前加 `if os.path.lexists(package_path): raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(package_path))`，它會變成既有的 save issue（`<path>.dep: [Errno 17] File exists: …`）。mutant r35 證實加上去所有測試照過；補一個測試：在 `batch_import_documents` 之後、寫入之前以 patch 建出同名檔，斷言 issue 與檔案不變。

**M-2 字典複製的位元組測試只用合法 UTF-8**（`client/tests/test_dictionary_manager.py:252-258` `test_export_copies_the_same_bytes`；mutant r34 把 `_copy_file_into` 改成 `open(source, "r", encoding="utf-8", newline="")` 再 `.encode("utf-8")` 仍全綠）
- 情境：F-6 讓讀不到（cp950）的字典仍可匯出；這份保證只靠 `_copy_file_into` 用 `"rb"`，測試沒釘住。
- 建議（便宜）：`EXCEL_DICTIONARY` 或另一個 subTest 加上 `LATE_BIG5`（檔案已 import）或任意非 UTF-8 位元組（例如 `b"\x00\xff"`），斷言逐位元組相同。

**M-3 `_logged_skipped_saves` 的兩個小缺口**（`client/config.py:124-135, 142-153`；`client/tests/test_config.py:563-573`）
- (a) `ConfigDataSafetyTest.setUp` 只清 `_logged_load_failures`，沒清 `_logged_skipped_saves`；路徑是隨機暫存目錄所以今天不會互相影響，但對稱起見加一行 `config._logged_skipped_saves.clear()` 與 `addCleanup`。
- (b) 「成功讀取後清除」沒有測試（mutant r32 存活）：讀不到 → 一次 WARNING → 檔案恢復可讀並成功讀取 → 再次讀不到（同一個錯誤）時應再記一次。建議補一個測試（便宜）。

**M-4 掃描程式占住暫存檔時 `.tmp` 會留下，spec Risks 的敘述略為樂觀**（`client/shared/atomic_write.py:82-85` 以 `suppress(OSError)` 移除；spec Risks「it is removed or renamed within the export」）
- 情境：探針 P7 模擬 AV 在 `os.replace` 當下以共用讀開著暫存檔：`[WinError 32]`、舊檔完整，但 `.old.brl.<hex>.tmp` 留在匯出資料夾（桌面、USB）。套件自 F-3 起就有同樣性質；匯出資料夾是使用者看得到的地方，所以第一次可能會被問「這是什麼」。資料沒有風險。
- 建議：spec Risks 的那一句改成「暫存檔在匯出內移除；若當下被其他程式占住而移除失敗，會留下，需要使用者手動刪除」（zh-TW 同步）。可選的 follow-up：`_write_atomically` 的 `finally` 對 `unlink` 重試幾次（短暫 sleep），這會改 `shared/atomic_write.py`，不在 F-8a 修。

**M-5 幾個失敗訊息現在會提到暫存檔名**（`shared/atomic_write.py` 的 `_open_temporary_file` 與 `os.replace`）
- (a) 匯出目的檔被其他程式開著：`[WinError 5] …: '<d>\out\.old.brl.<random>.tmp' -> '<d>\out\old.brl'`（spec 項目 77 的預期，已知）。
- (b) 匯出或字典匯出時資料夾已不存在（對話框之後被刪）：`[Errno 2] …: '…\gone\.alpha.html.<hex>.tmp'`，改前指向 `alpha.html`（探針 P2）。
- (c) 字典匯出到同名資料夾：`[WinError 5] …tmp -> math.csv`，改前 `[Errno 13] Permission denied: 'math.csv'`（探針 P3）；wx 另存對話框實務上到不了。
- 建議：(a)、(b) 接受，列給使用者（§6 末表）；(c) 可選、便宜：`export_dictionary` 前加與 `write_export_text` 相同的 `is_dir()` 檢查（或把那段抽成 `shared` 的小 helper 供兩處用），讓 D7 與 D8 一致。

**M-6 plan 末尾補「Implementation Notes」**（便宜；F-7 審查 M-3 的同一要求）
- 一句「Task 0–6 依 plan 以 `apply_blocks.py` 套用，Task 1–4 的 tree id 與 dry run 逐一相同，沒有偏離；exe 雜湊與 GUI 結果見 auto-results」，並列出本審查的修正與修正後的 `Ran` 數。

**M-7 損壞的 `config.json` 加上寫不進去的 `.bak`，設定會一直存不進去**（`client/config.py:155-163`；探針 P6a、P6b）
- 情境：`.bak` 唯讀或是資料夾（或原檔在讀取與備份之間被刪）時，每次設定變更都只記 `ERROR`，`config.json` 保持損壞。這是 spec D11「If the copy fails, `_save` does not write」的既定取捨，資料沒有風險；只是使用者看不到任何提示。
- 建議：不在 F-8a 修；記在 F-12（本地化／訊息收尾）或 config 的後續：設定對話框按確定後若沒存成功，給一次提示。

**M-8 `free_document_name` 不檢查 32 字上限**（`client/documents/workspace_service.py:106-113`；探針 P5：30 字的 base 產生 34 字的名稱，`normalize` 在 `create_document` 時拒絕）
- 情境：只有 `DEFAULT_DOCUMENT_NAME`（`new`）會用到，`new (N)` 要到 N 有 26 位數才會超過，所以今天不會發生。
- 建議：不處理；或在 docstring 註明「base 要夠短」。

### 請使用者確認的預設（orchestrator 採用的 O1–O7 中屬於 F-8a 且與可見行為有關的，加上兩個 spec 有寫、但值得知道的改變）

| # | 預設 | 影響 |
| --- | --- | --- |
| O2 | 啟動時工作區只有一個保留下來的無效 `new.dep`，預設文件叫 `new (2)`（再來 `new (3)`…） | 改前 `new.dep` 被空文件默默取代；現在清單上會看到 `new (2)` |
| D1 | 保留下來的無效 `.dep`（或工作區裡同名的資料夾）永久占住那個名字：新增／改名會說「文件「bad」已存在。」，匯入列為「已存在」，但清單上沒有 `bad` | 使用者只能在下次啟動選「刪除無效檔案」或自己到資料夾刪掉；訊息沒有說明是磁碟上的檔案（新字串屬 F-8b／F-12，若要區分） |
| O6 | 匯出目的檔被其他程式以共用讀寫開著（例如編輯器開著 `old.brl`）時，匯出失敗：`匯出文件失敗：[WinError 5] 存取被拒。: '…\.old.brl.<random>.tmp' -> '…\old.brl'`；全部匯出的摘要列出該文件 | 改前會在對方開著時改寫檔案；現在舊檔完整，關掉對方再匯出一次即可。訊息裡會出現暫存檔名 |
| O4 | `config.json` 損壞（不是 JSON 物件、截斷、非 UTF-8、空檔）：啟動時先把原檔複製成 `config.json.bak`，再寫入（啟動時 client id 的寫入就是第一次）；`.bak` 只保留最近一份，程式不會讀它。讀不到（被鎖、權限）：設定變更不寫入、沒有任何訊息，只在 `log\config.log` 記一次 WARNING | 改前 `null` 讓程式無法啟動、有 BOM 或損壞的檔案在啟動時被換成只有 client id 的檔案 |
| 隱藏檔 | 隱藏的 `config.json`、匯出檔、字典檔、`preprocessing.py` 現在會被換掉並失去「隱藏」屬性；改前對隱藏檔的寫入一律失敗（`config.json` 只記 log，匯出顯示錯誤） | F-3 D11 對套件的同一取捨；設定終於存得進去 |
| D6／D7 | 唯讀的 `preprocessing.py` 訊息改為 `[Errno 13] Permission denied: '<script>'`；字典匯出到自己的檔案不再報 `SameFileError`，而是以同樣內容重寫 | 文字與邊界行為的小改變 |
| 暫存檔 | 匯出、字典匯出、腳本、`config.json` 寫入時會在同一資料夾短暫出現 `.<名稱>.<16 hex>.tmp`；若當下被掃描程式占住，可能留下（M-4） | 看到可以直接刪 |

## 7. 其他觀察（不需處理）

- `move_document_package` 的守衛用 `files.exists`（`Path.exists`）而非 `lexists`：指向不存在目標的 symlink 不會被看到；Windows 上建 symlink 需要特權，`package_name_taken` 在提示階段已用 `lexists` 擋下。mutant r01 等價。
- `write_export_text` 的 POSIX 分支（`IsADirectoryError`）沒有在 Windows 上執行；7 個 POSIX-only skip 與改前相同。
- `test_a_failed_backup_prevents_the_write` 的 `patch("config.write_bytes_atomically", create=True)`：`config` 已 import 該名稱，`create=True` 只是讓 red 步能跑，綠燈後無害。
- `test_save_installs_through_a_synced_temporary_file`（config）與 A5 以 `wraps` patch 全域 `os.fsync`，統計次數；`test_user_preprocessing_script` 的 A1 patch `shared.atomic_write.os.fsync`，兩種寫法都正確。
- `_FailingReplacePackageFiles` 的 `source_name` 改成可選、新增 `destination_name`，既有呼叫端不變。
- 全部匯出的摘要仍是英文（P1-4 defect 4）；補量 b 與 GUI 78 可見；屬 F-12。
- 審查工具（`$SP\probes.py`、`mutants.py`、`rev1.py`）與副本都在 scratchpad，未放進 repo；`D:\dxtest\rev1{a,b,c,d}-f8a` 是本次新建的補量資料夾（各含一個 exe 副本與測試資料），沒有動其他 `D:\dxtest` 內容；沒有重建 exe。

## 修正記錄

- 日期：2026-10-10，由 Claude 執行；主 checkout `D:\workspace\DotExpress`，分支 `fix/f8-data-safety-cleanup`，起點 `22842ac`。沒有 merge 進 `main`、沒有 push、沒有切換分支；沒有啟動 source-run 的 `gui.py`。主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 在修正前後 sha256 相同（4 個檔：`config.json` `eea87b39…`、`dictionary/default.csv` `8f0594e9…`、`log/init.log` `1b787580…`、`workspace/new.dep` `d0cb6539…`，比對無差異），未 stage；`client2/`、`preprocessing/`、`testdata/`、`task.md`、兩個 worktree 都沒有動。
- 每個 commit 只 stage 明確路徑（`git diff --cached --stat` 確認），結尾 `Co-Authored-By: Claude Opus 5.5`。`test_config.py` 與 `manager.py` 的改動以 Python 腳本寫入（舊文字恰好一次、保留 CRLF 工作檔的行尾）；`test_workspace_service.py`、`workspace_service.py`、`test_dictionary_manager.py` 以 Edit 工具改，新增的文字沒有 `\u` escape 與反斜線，commit 的 numstat 只有預期的行（`test_workspace_service.py` 既有的 10 行 `\ud…` escape 在 `22842ac` 與 `HEAD` 相同）；`test_dictionary_manager.py` 的 M-2 與 M-5 分兩個 commit，M-2 的版本由腳本從完整檔案去掉 M-5 的測試後暫時寫入、commit，再還原。

| 發現 | 處理 |
| --- | --- |
| M-1 | `823fb55`：`import_files` 的迴圈在每次 `save_document_package` 之前、`try` 之內加上 `os.path.lexists(package_path)` → `FileExistsError(EEXIST)`，與 `create_document` 相同；它成為既有的 save issue（`<ws>\beta.dep: [Errno 17] File exists: '<ws>\beta.dep'`），批次繼續。新測試 `test_import_does_not_replace_a_package_that_appeared_after_the_names_were_checked`：以 `batch_import_documents` 的 `side_effect`（呼叫原函式後在工作區建出 `beta.dep` = `b"not a zip"`）模擬名稱比對之後才出現的檔案；斷言 `saved` 只有 `delta`、issue 是 `[Errno 17]`、controller 是 `['zoo', 'delta']`、`beta.dep` 位元組不變。先紅：改前 `Ran 62`、`FAILED (failures=1)`（`beta` 被存進 `saved`，`beta.dep` 被取代）；改後綠 |
| M-2 | `749fb31`：`test_export_copies_the_same_bytes` 改成兩個 subTest，同一個匯出資料夾依序匯出 `EXCEL_DICTIONARY`（BOM、CRLF、CJK）與 `LATE_BIG5`（17 KB ASCII 之後的 cp950，F-6 讀不到的字典），各自斷言逐位元組相同、沒有 `.tmp`。測試數不變 |
| M-3 | `9ef8306`：(a) `ConfigDataSafetyTest.setUp` 也清 `config._logged_skipped_saves` 並 `addCleanup`；拒讀的 `open` 抽成 `_open_denying_reads()`，既有的 `test_a_change_after_an_unreadable_load_does_not_write` 改用它（斷言不變）。(b) 新測試 `test_a_good_load_logs_the_next_refused_save_again`：拒讀時變更一次 → 正常讀取（`get_conversion_width()` = 30）→ 再拒讀時變更一次，`was not saved` 的 WARNING 恰好兩筆，檔案位元組不變 |
| M-4 | `c9950ec`：spec 兩檔 Risks「匯出資料夾中的暫存檔」改為「通常」在匯出內移除，並加上「F-8a 審查後的修正（2026-10-10，M-4）」：掃描程式在 `os.replace` 當下開著暫存檔時匯出失敗（`[WinError 32]`）、舊檔完整、暫存檔留下（移除也失敗，`shared/atomic_write.py` 忽略該錯誤，套件自 F-3 起相同），使用者可手動刪除；重試移除列為後續項目。`shared/atomic_write.py` 未改。兩檔仍各 632 行 |
| M-5 | (a)、(b) 接受，不處理（§6 末表已列給使用者）。(c) `46a4ce2`：`export_dictionary` 在 `write_bytes_atomically` 之前檢查 `destination.is_dir()`，Windows 拋 `PermissionError(EACCES)`、其他平台 `IsADirectoryError(EISDIR)`，與 `write_export_text` 相同（就地內嵌，不另抽 helper：`dictionaries` 不 import `documents`，改 `shared/atomic_write.py` 會牽動 F-2 D5 釘住的字典編輯器訊息）。訊息回到改前 `copyfile` 的 `[Errno 13] Permission denied: '<目的地>'`；先查過沒有任何測試或 GUI 項目釘住被取代的 `[WinError 5] …tmp -> …` 文字（`test_dictionary_manager`、`test_dictionary_presenter`、`test_app_paths` 與 GUI 82 照過），所以沒有改到釘住的訊息。新測試 `test_export_onto_a_folder_fails_as_an_in_place_write_did`（資料夾內有檔案；斷言訊息、資料夾與舊的 `math.csv` 不變）。先紅：`[WinError 5] 存取被拒。: '…\.folder.csv.<hex>.tmp' -> '…\folder.csv'` ≠ `[Errno 13] Permission denied: '…\folder.csv'`；改後綠。spec 兩檔 D7「既有的匯出目的檔」段落末尾加上「F-8a 審查後的修正（M-5）」（同在 `c9950ec`） |
| M-6 | `c9950ec`：plan 末尾新增「Implementation Notes (2026-10-10)」：Task 0–6 照 plan 以 `apply_blocks.py` 套用，Task 0–5 與 dry run 沒有偏離，Task 6 的 log 與 Step 4 一致；列出 Task 1–4（及 Task 6 的 `22842ac`）的 `HEAD:client` tree id；註明本次修正（M-1、M-2、M-3、M-5 (c)、M-4／M-6 與 commit）、新的數量（`Ran 1403`、驗收 2 的模組組 `Ran 537`）、修正後的 tree，以及 N-f8a2 是之後要用的 build；plan 的區塊保留原文 |
| M-7 | 未處理，follow-up（F-12 或 config 的後續：設定沒存成功時給一次提示） |
| M-8 | 未處理，觀察（今天只有 `new` 會用到，`new (N)` 不會超過 32 字） |
| O2、O4、O6、D1、隱藏檔、D6／D7、暫存檔（§6 末表） | 未處理，仍待使用者確認；目前維持預設 |

### Mutant（M-1、M-2、M-3、M-5 (c)）

`git archive 22842ac client` 解到 `$SP\f8afix\old\client` 與 `$SP\f8afix\new\client`（不是 git work tree，不含 `.venv`、`dictionary/`、`workspace/`、`config.json`、`log/`；複製 liblouis runtime、`louis_helper.py`、`mathcat/`），`new` 再覆蓋上修正後的 5 個 `client/` 檔。`$SP\f8afix\mutants.py` 每個 mutant 只改一個檔（舊文字恰好一次、保留行尾），跑對應模組（工作區組：`test_workspace_service`＋`test_document_workspace`＋`test_gui_document_flows`；字典組：`test_dictionary_manager`＋`test_dictionary_presenter`；`test_config`），跑完還原並確認位元組相同：

```text
== 22842ac（修正前的程式與測試）
unmutated: 工作區組 Ran 311 | OK (skipped=2)；字典組 Ran 66 | OK (skipped=1)；config Ran 45 | OK
r35（每次匯入寫入前再檢查磁碟）: Ran 311 | OK (skipped=2)  -- 存活
r34（_copy_file_into 以文字模式讀再 encode）: Ran 66 | OK (skipped=1)  -- 存活
r32（成功讀取後不清 _logged_skipped_saves）: Ran 45 | OK  -- 存活
== 修正後
unmutated: 工作區組 Ran 312 | OK (skipped=2)；字典組 Ran 67 | OK (skipped=1)；config Ran 46 | OK
M-1 拿掉（= 修正前的 import_files）: FAILED (failures=1)  test_import_does_not_replace_a_package_that_appeared_after_the_names_were_checked
r34: FAILED (errors=1)  test_export_copies_the_same_bytes
r32: FAILED (failures=1)  test_a_good_load_logs_the_next_refused_save_again
M-5 (c) 拿掉: FAILED (failures=1)  test_export_onto_a_folder_fails_as_an_in_place_write_did
```

r35 是 M-1 的修正本身：修正前它讓所有測試照過，修正後反向（拿掉檢查）被新測試抓到。

### Build 與 GUI

M-1、M-5 (c) 改了 production 程式，所以重建：主 checkout `46a4ce2`（`HEAD:client` `1d6780c8f7a5e53bc494e0c54bbeadcb0fdea500`），Task 6 Step 1 的指令，PyInstaller 6.21.0，`Build complete!`，六個 F-8a 模組與 `gui.py` 都來自 checkout；`D:\dxtest\N-f8a2\DotExpress.exe`，48,756,071 bytes，sha256 `9944656AA3DE4D7E9E089463FA2650878E9DAA5E082550635F240641AC1782FE`；`git status --short -- client scripts` 無輸出。以已 commit 的 `auto/item66.py`（項目 68，匯入）與 `auto/item82.py`（項目 82，字典匯出）在新的 `D:\dxtest\auto68-f8a2`、`D:\dxtest\auto82-f8a2` 執行：兩個 log 與 `auto68-f8a.log`、`auto82-f8a.log` 逐行相同（`diff --strip-trailing-cr` 無差異）。只結束該資料夾下的程序，之後 `tasklist` 沒有 DotExpress 程序；沒有任何腳本讀寫剪貼簿。其他項目碰到的程式碼沒有改變，不重跑。結果寫在 `auto-results.md` 的「N-f8a2」一節。

### 最終驗證

- 完整套件：`cd client && $PY -B -X utf8 -m unittest discover -s tests` → `Ran 1403 tests`，`FAILED (errors=1, skipped=7)`；唯一 error 為 F-W6 的 `test_dictionary_name_prompt … test_case_only_rename_still_renames`。1403 = 1400 + 3 個新測試（M-1、M-3 (b)、M-5 (c) 各一；M-2 是 subTest）。跑完主 checkout 的 `client/log/` 沒有新檔（sha256 比對相同）。
- 驗收 2 的模組組：`Ran 537`、`OK (skipped=7)`（534 + 3）。
- catalog：`git diff --stat main -- client/locales` 為空；`.pot`、`.po`、`.mo` 的 blob id 與 `main` 相同（`1d7643e3…`、`d60c883d…`、`68e1ab6f…`）；`msgfmt --check --statistics` 364 translated。
- fixtures：`translation_golden.json` → `e67d95a1…1ccd`，`dictionary_entries_trace.json` → `f493da52…c2cf`，與要求相同。
- 受限檔案：`git diff --name-only 22842ac..HEAD` 只有 `client/dictionaries/manager.py`、`client/documents/workspace_service.py`、三個測試檔、F-8a plan、F-8 spec 兩檔（加上本記錄與 `auto-results.md`）；`client/braille/`、`AGENTS.md` 不在其中。改動的 `client/` 檔在 index 都是 `i/lf`、工作檔 `w/crlf`，縮排沿用 4 個空白，production 檔純 ASCII；`git diff --check` 無問題。
- `HEAD:client` tree（`46a4ce2` 起）：`1d6780c8f7a5e53bc494e0c54bbeadcb0fdea500`。
