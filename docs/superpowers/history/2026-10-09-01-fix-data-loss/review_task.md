# 資料遺失修復階段（F-1／F-2）審查記錄

- 日期：2026-10-09
- 範圍：`main` 的 `c8ecf66..80e7be6`（16 個 commit，兩次 merge：`aced6f8` F-1、`80e7be6` F-2）
- 對照：`docs/superpowers/specs/2026-10-09-f1-workspace-case-collisions-design.md`、`docs/superpowers/specs/2026-10-09-f2-dictionary-file-safety-design.md`、對應 plans，以及 `docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md` 「既有缺陷清單」優先 1 的四列。
- 審查方式：逐行讀 production diff（`client/` 非測試 8 個檔）與測試 diff（13 個檔），在 Linux 跑完整驗證（下節），另在 scratchpad 的副本上自行套用 5 個 mutant；Windows 行為以推理為主，凡不能在這台機器驗證的都標為「推理」或「不確定」。
- 本記錄只寫檔，未 commit。

## 驗證（Linux，`$SP` = session scratchpad，`$PY` = `$SP/venv/bin/python`）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| 完整套件 | `cd client && $PY -m unittest discover -s tests` | `Ran 1138 tests in 6.692s`, `FAILED (failures=1, skipped=7)`；唯一失敗為已知 P2-5 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math` |
| 20 個 shuffle seed | `cd client && for s in $(seq 1 20); do $PY $SP/shuffle_harness.py $s; done` | 20 個 seed 皆 `ran=1138 failures=1 errors=0 skipped=7`，BAD 只有 P2-5 |
| msgid | `$PY $SP/p12/tools/msgid_scan.py client`（repo root） | `source msgids: 353`（pot 357，四個 orphan 同前） |
| locales | `git diff c8ecf66..80e7be6 -- client/locales` | 空 |
| fixtures | `sha256sum client/tests/fixtures/*.json` | `translation_golden.json` `e67d95a1…11ccd`、`dictionary_entries_trace.json` `f493da52…6c2cf`，與 spec 相同 |
| app data | `$SP/p26impl/snap.sh` 於所有測試前後 | 完全相同（`client/dictionary/` 三個 CSV sha256 不變；`config.json`、`workspace/` 不存在） |
| KNOWN BUG 標記 | `grep -rn "KNOWN BUG (P1-3 spec, known defect [12]\|KNOWN BUG (P2-2 spec, Q[137]" client/tests` | 無；defect 3／4 與 Q2／Q4／Q5／Q6／Q8 標記仍在 |
| CSV reader | `grep -rn "csv.DictReader\|utf-8-sig" client --include=*.py --exclude-dir=.venv --exclude-dir=tests` | 恰好 R1–R5 五處，五處皆 `utf-8-sig` |
| 自套 mutant（5 個，見「測試品質」） | 在 `$SP/rev_mut/client` 的副本上 | 4 個被抓到、1 個存活（I-1） |

## 結論

**Ready。** 四個優先 1 的資料遺失缺陷在目標平台上確實修掉了（Windows 部分為推理，見下），沒有找到新的資料遺失或毀損路徑；行為變更都限於 spec 宣告的範圍且有測試釘住。沒有 Critical。兩個 Important 都是測試／驗證品質，不要求改 production code 才能接受；但 I-1 建議在下一個小 commit 補上。

## 1. 四個缺陷是否在目標平台修好（Windows NTFS 推理）

### F-1 defect 1：case-only Rename 刪掉同一個檔

`documents/workspace_service.py:116-123` 以名稱判定 case-only（`casefold()` 相等且不全等），走 `move_document_package`（`documents/workspace.py:95-148`）：stage 新包到 `.alpha.dep.<rnd>.tmp` → 若舊包存在，`os.replace(Alpha.dep, .Alpha.dep.<rnd>.tmp)` → `os.replace(staged, alpha.dep)` → 刪 aside。

逐步推理 NTFS：
- 第 2 步 `MoveFileExW(REPLACE_EXISTING)` 把目錄項 `Alpha.dep` 改名到一個已存在的空 tmp（`NamedTemporaryFile` 建好即關閉，不是開著的）：允許。改名不需要檔案的寫入權，所以舊包帶唯讀屬性也成立。
- 第 3 步時目錄內已無任何 casefold 等於 `alpha.dep` 的項目，所以新目錄項取得**精確**拼法 `alpha.dep`；這是 spec「不依賴 replace-onto-alias 的語意」的關鍵，正確。
- 失敗路徑：舊包被其他程式（zip 工具、AV）開著且無 `FILE_SHARE_DELETE` → 第 2 步 `[WinError 32]`；handler 刪 staged 與空 aside 後 re-raise，舊包完全未動；GUI 以既有 `Failed to save document: {error}` 顯示、controller 未改。第 3 步失敗 → 把 aside 改回 `Alpha.dep`（此時該名稱不存在，純 rename）並刪 staged。還原也失敗 → 舊包留在 `.Alpha.dep.<rnd>.tmp`，但記憶體仍有 `Alpha`，下一次 Save 會從記憶體重寫 `Alpha.dep`，不是資料遺失。
- `load_workspace_documents` 用 `Path.glob("*.dep")`（純 Python 比對，不經 Win32 萬用字元，不受 8.3 短檔名影響），`.Alpha.dep.<rnd>.tmp` 不會被列出、也不會被 startup dialog 提議刪除。
- 唯一無 `.dep` 的視窗是第 2、3 步之間（兩次同目錄 rename，毫秒級）；見 M-2。

### F-1 defect 2：Add 以大小寫變體覆寫另一份文件

`documents/session.py:52-54`：`document.name.casefold() == name.casefold() and document.name != exclude_name`。`gui.py:649` 是唯一 production caller，Add 不帶 exclude、Rename 帶來源名稱（精確），所以 `Alpha`→`alpha` 自己改自己仍放行，`beta`→`Alpha`（`alpha` 已存在）被拒。Import 原本就是 casefold（`batch_import_documents`）。這一條在所有平台都生效，與磁碟無關，Windows 推理無疑義。

### F-2 defect 3：BOM 字典開啟為空、OK 後只剩 header

五個 reader 全改 `utf-8-sig`（`dictionaries/entries.py:54`、`dictionaries/manager.py:43`、`conversion/text/dictionary_rules.py:153,169`、`conversion/text/char_maps.py:14`）。`utf-8-sig` 的 incremental decoder 只在串流開頭剝一次 BOM，無 BOM 的檔案解碼結果與 `utf-8` 完全相同（含 `UnicodeDecodeError`）；三個 data 檔無 BOM，微基準（每檔 20 次取最小）`utf-8` 0.098／0.072／0.129 ms vs `utf-8-sig` 0.100／0.073／0.133 ms，無可見差異。

### F-2 defect 4：OK 先 truncate 再寫、非 `OSError` 逃出 handler

`shared/atomic_write.py:52-92`：`os.access(W_OK)` 前置檢查 → 以 `open(..., opener=)` 建 `.<name>.<rnd>.tmp`（`O_WRONLY|O_CREAT|O_EXCL|O_BINARY`，mode `0o666`）→ `write` → `flush` → `fsync` → 關檔 → POSIX 下 `chmod` 成原 mode → `os.replace` → `finally` 未安裝則刪 tmp。

逐項推理 Windows：
- `O_BINARY` 由 opener 自己加（`_CREATE_FLAGS`），`newline=""` 關掉 text 層換行轉換，`DictWriter` 自寫 `\r\n`，所以 bytes 與舊的 `open("w", newline="")` 相同；fixture `dictionary_entries_trace.json` 未重生而通過，可佐證 Linux 側。
- 串流在 `with` 結束時已關閉，`os.replace` 才執行：Windows 不能 rename 自己還開著的檔，這個順序正確。
- `os.fsync` 在 Windows 走 `_commit`／`FlushFileBuffers`，對檔案 fd 有效。
- `os.access(path, W_OK)` 在 Windows 只看唯讀屬性、不看 ACL（spec Risks 已寫）。唯讀屬性 → `PermissionError [Errno 13] Permission denied: '<path>'`，與舊 `open("w")` 的判決一致；ACL 拒寫但允許刪除的檔會被 rename 覆蓋（判決變寬，spec 已列）。
- `os.replace` 失敗（Excel／AV／indexer 無 `FILE_SHARE_DELETE`）→ tmp 被刪、原檔未動、訊息顯示、再按 OK 重試（D8）。
- 若 AV 正好開著剛建好的 tmp，`unlink` 失敗會被 `suppress(OSError)` 吞掉、留下 `.default.csv.<rnd>.tmp`；`list_dictionary_names` 用 `glob("*.csv")`，不會被列出或載入。
- `dialog.py:494` `except Exception` 覆蓋 `UnicodeEncodeError`／`csv.Error`／`LookupError`，`BaseException` 仍傳播。

**沒有找到新的資料遺失或毀損路徑。** 兩個 fix 的所有失敗分支都以「原檔 bytes 不變、tmp 清掉（或留下但不會被載入）」收尾；測試 C9–C13、A3–A6、A11–A14、G15–G16 在 Linux 釘住。

## 2. 超出意圖的行為變更

| 變更 | 平台 | 記錄位置 | 判定 |
| --- | --- | --- | --- |
| Linux 上 Add／Rename `Alpha` 旁已有 `alpha` 被拒 | 全平台 | F-1 D1、Risks | 可接受：與 Import、排序一致，且避免 workspace 搬到 Windows 時碰撞；legacy 同時含兩種拼法的 workspace 仍可載入，只有改名到第三種拼法會被拒（測試 D15 釘住） |
| 只有 BOM 的檔案改報 `CSV must contain header row.`（原為 columns 訊息） | 全平台 | F-2 D1；`_error_cases()` 兩列 | 可接受，無 msgid 變更 |
| 錯誤訊息出現 tmp 路徑（`... '.default.csv.k2j1.tmp' -> 'default.csv'`） | 全平台 | F-1 D4、F-2 D5 | 可接受：模板不變、英文錯誤文字本來就是 Python 的；測試改以前綴＋` -> '<path>'` 後綴斷言，跨平台成立 |
| BOM 字典第一次 OK 後 BOM 消失 | 全平台 | F-2 D2 | 可接受（寫出 bytes 不變） |
| 目錄不可寫但檔案可寫（罕見）：舊的就地寫成功、現在建 tmp 失敗 | 全平台 | 未記錄 | 只記錄；app data 目錄是 per-user，P2-6 已在唯讀 root 阻擋啟動 |
| POSIX 上 case-only rename 後 `.dep` mode 變 `0600` | Linux／macOS | 未記錄 | 見 M-3 |

## 3. 測試品質

### 模型是否忠實（`tests/case_insensitive_package_files.py`）

- `resolve` 以 `iterdir()` 的真實拼法比對（先精確、再 casefold），不用 `Path ==`／`exists()`，所以在 Windows host 上也會得到相同結果；`write`／`remove`／`exists` 作用在解析到的項目，忠實重現「開啟大小寫變體會改寫既有目錄項並保留其拼法」（NTFS／APFS 的實際行為）。
- `replace` 的同項目分支直接 `os.replace(entry, destination)`：在 Linux 等於改拼法，在 Windows 就是真實的 case-only `MoveFileEx`。跨項目分支兩種讀法都有測（B3、B4 subTest），而 D4 不依賴該分支。
- 未建模：sharing violation、唯讀屬性、AV 持有；這些由 fault injector（`_FailingPackageFiles`、`_FailingInstallPackageFiles`）以字串比對 `path.name` 注入，不會在 Windows 因 `Path` 大小寫不敏感而誤判。
- 我逐一推演 B1–B4、C5–C14、E16–E22、F 四個測試在 Windows 真實 NTFS 上的預期：全部應通過（列入 Windows 檢查清單）。

### 實作耦合

- `test_regular_rename_does_not_use_package_files`（`_UnusablePackageFiles`）與 `_RecordingCaseInsensitivePackageFiles.replaced_onto` 斷言是守 D6 路由的 guard；在 Linux 沒有它們，「case-only 分支整個拿掉」的 mutant 會存活（舊路徑在 case-sensitive FS 上本來就正確），所以有必要，但修 defect 3 時必須一起翻。測試檔註解已說明。
- `test_temporary_path_creates_the_directory_and_is_not_a_package` 釘住 `.alpha.dep.` 前綴；有理由（loader glob），但屬命名耦合。
- A15 `ProductionCodeDoesNotSetTheUmaskTest` 每次 AST 掃整個 `client/`（0.14 s），守的是「不要讀 umask」的設計決定；可接受。

### 自套 mutant（scratchpad `rev_mut`，不在 repo 內）

| # | mutant | 結果 |
| --- | --- | --- |
| M1 | `move_document_package` install 失敗 handler 不刪 staged tmp | 抓到：`test_install_failure_puts_the_old_package_back`、`test_case_only_rename_install_failure_propagates_and_keeps_state` |
| M2 | service 先 `controller.rename_document` 再 `move_document_package` | 抓到：`test_case_only_rename_install_failure_propagates_and_keeps_state` |
| M3 | `write_text_atomically` 拿掉 `stream.flush()`（`fsync` 仍在） | **存活**（`tests.test_atomic_write`、`test_dictionary_entries`、`test_dictionary_entries_dialog` 94 個測試全綠）→ I-1 |
| M4 | `PackageFiles.temporary_path` 前綴去掉前導點 | 抓到：C13、C14 |
| M5 | `os.replace` 換成 `shutil.copyfile`＋`unlink`（非原子安裝） | 抓到：A4、A7、G update、G15 |

實作者的 mutant 清單（F-1 12 個、F-2 25 個）我抽查其腳本（`$SP/f1impl/tools/f1_mutants.py`、`$SP/f2impl/mutants.txt`），與 spec AC 一致；M3 是兩份清單都沒有的 mutant。

### 執行時間（`$SP/rev_tools/timed_runner.py`，old = `c8ecf66`、new = `80e7be6` 的 `client/` 副本）

- 總時間 2.37 s → 7.37 s（本機；orchestrator 看到的是 ~2.5 → ~5 s，同一方向）。
- 來源幾乎全在 `tests.test_dictionary_entries_dialog`：0.21 s → 2.46 s，其中 `DictionaryEntriesTraceTest.test_replay_matches_every_recorded_step` 0.064 s → 2.24 s。trace 內有 40 次 `ok`，每次現在真的做 `os.open`＋`fsync`＋`os.replace`；本機 fsync 約 50–70 ms（`tests.test_atomic_write` 15 個測試 1.13 s 亦同量級）。`tests.test_dictionary_entries` 0.003 → 0.113 s 同因。
- `test_conversion_text_dictionary_rules`、`test_config` 單跑無差異（0.14 vs 0.16 s；第一輪看到的 0.6／0.3 s 是整套件內的雜訊）。
- 對使用者：每次 OK 一次 fsync，字典是 KB 級，無感。對開發迴圈：+2–5 s，可接受；若想壓回來，見 M-6。

## 4. 一致性（其他 writer）

| writer | 目前 | 風險 | 建議 |
| --- | --- | --- | --- |
| `documents/workspace.py:63` `save_document_package`（Save／Add／Import／regular Rename 的新包） | `zipfile.ZipFile(path, "w")` 就地 truncate | **文件層級的 Q3 同款**：寫到一半（斷電、磁碟滿、`document.text` 含 lone surrogate 時 `writestr` 的 `UnicodeEncodeError`）留下截斷的 `.dep`；下次啟動被列為 invalid 並**提議刪除**。每次切換文件都會 Save，暴露頻率最高 | 優先 2：改走 staging（`temporary_path` + `os.replace`，`PackageFiles` 已有全部原語；需要 binary 版的 helper 或直接在 `PackageFiles.write` 內 stage） |
| `conversion/preprocessing/user_script.py:53-74` `save_preprocessing_script` | 已 stage＋`os.replace`，但 tmp 路徑在寫完才記錄；`NamedTemporaryFile` 給 `0600` | 寫入失敗漏 `.tmp`；POSIX 上腳本變 owner-only | 優先 3：改用 `write_text_atomically`（一行） |
| `dictionaries/manager.py:23,57` header 寫入；`:72,92` `shutil.copyfile` | 建新檔或複製到使用者選的路徑 | 失敗只留下部分的**新**檔／部分的匯出檔，不碰既有字典 | 優先 3：header 兩處改 helper；copy 兩處需 binary 變體 |
| `config.py:124` `ConfigStore._save` | 就地 `open("w")`＋`json.dump`，例外只 log | 寫一半斷電 → `config.json` 壞 JSON；`_load` 對壞 JSON 的處理未在本次查核（不確定） | 優先 3：改 helper；並確認 `_load` 遇壞 JSON 會回預設而非炸掉 |
| `dictionaries/manager.py:76-86` `rename_dictionary` | `exists()` 檢查＋`Path.rename` | 無資料遺失。Windows 上 case-only 改名被當重複拒絕；Linux 放行；`resolve_selected_dictionary` 精確比對 | 優先 4（UX）：見 F-1 spec Out of Scope；`tests/test_dictionary_name_prompt.py:82` 在 Windows 預期 error |
| `documents/formats.py:108`、`documents/workspace.py:198`（Export）、`dual_view/files.py:24` | `write_text` 就地 | Export 目標是使用者已確認覆蓋的路徑；dual view HTML 是暫存 | 不動 |

結論：`PackageFiles`（F-1）與 `write_text_atomically`（F-2）兩套原語暫時並存可接受（一個 binary zip、一個 text），但 `save_document_package` 應是下一個要收的 writer。

## 發現清單

### Critical

無。

### Important

**I-1 `test_data_is_flushed_to_disk_before_the_replace` 沒有釘住「fsync 時資料已經在 fd 上」**（`client/tests/test_atomic_write.py:91-100`）
- 情境：拿掉 `shared/atomic_write.py:81` 的 `stream.flush()`，94 個相關測試全綠（M3）。此時 `fsync` 作用在尚未 flush 的 fd 上（TextIOWrapper／BufferedWriter 的 buffer 還在 user space），資料要到 `with` 結束關檔才寫入 → `os.replace` 之前仍在 page cache，但「斷電後不會留下空檔」這個 spec 給 fsync 的理由就不成立。production code 目前是對的；問題是 spec AC10「no-fsync 被抓到」給了一個偏大的信心。
- 修法（測試，不改 production）：在 `patch("os.fsync", wraps=...)` 的 side effect 內用 `os.fstat(fd).st_size` 斷言長度已等於寫入內容（或 `os.pread` 讀回 `b"a,b\r\n"`），再比對呼叫順序。

**I-2 Windows 驗證債在這一階段再加一層，且 F-1 的真實 FS 測試在 Linux 永遠跑舊路徑**
- 情境：`test_case_only_rename_keeps_the_document`、`test_case_only_rename_moves_the_package_and_updates_the_controller`、`MoveDocumentPackageTest` 十個、模型四個自測在 Windows 真實 NTFS 上從未執行過；本記錄第 1 節的全部 Windows 結論都是推理。F-2 的 `O_BINARY`／`\r\n` bytes、`os.replace` 對目錄／唯讀／隱藏目標的錯誤、AV 下的 transient failure 亦同。
- 修法：執行下方「Windows 驗證清單 delta」，把結果附回本記錄；在那之前不要在 release note 裡宣稱 Windows 上已修復。

### Minor

**M-1 `on_rename_document` 只接 `OSError`**（`client/gui.py:759-762`）
- case-only rename 若在 staging 時拋非 `OSError`（`document.text` 含 lone surrogate → `UnicodeEncodeError`），例外逃出 handler、無訊息；磁碟不受影響（staged tmp 已清、舊包未動）。regular rename 與 Save 本來就如此，不是本次回歸；可併入 `save_document_package` 的 follow-up 一起把 `_save_open_document_with_feedback`／rename 的 except 放寬。

**M-2 F-1 第 2、3 步之間的 crash 視窗沒有任何提示**（`client/documents/workspace.py:131-140`）
- 情境：process 在 move-aside 之後、install 之前被殺（AV 隔離、藍屏）。下次啟動 `*.dep` 沒有這份文件，startup 不會提，`_ensure_open_document_exists` 可能建 default 文件；資料在 `.Alpha.dep.<rnd>.tmp` 與 `.alpha.dep.<rnd>.tmp`，使用者不知道。spec Risks 已列（低機率）。
- 建議（follow-up，優先 3）：`load_workspace_documents` 順便列出 `.*.dep.*.tmp` 並以 invalid-files dialog 的同一套 UI 提示「可復原」；或在 move 成功後才刪、啟動時若發現孤兒 `.tmp` 且無同名 `.dep` 就自動改回。

**M-3 POSIX 上 case-only rename 後 `.dep` 變 `0600`**（`client/documents/workspace.py:88-92`）
- 驗證：`save_document_package` 建的 `Alpha.dep` 為 `0644`，`move_document_package` 後 `alpha.dep` 為 `0600`（本機 umask 022）。來自 `NamedTemporaryFile`。F-2 刻意保留 mode（Corrections 1、2），F-1 沒有；只影響 Linux／macOS 的 per-user 目錄。
- 修法（可選）：`temporary_path` 改用與 `atomic_write` 相同的 `os.open(..., 0o666)` 命名迴圈，或安裝前 `chmod` 成舊包的 mode。

**M-4 aside 槽位預先建檔，多一個 AV／indexer 可持有的目標**（`client/documents/workspace.py:88-92,131-133`）
- 情境（推理）：Windows 即時掃描常在新檔建立後短暫開啟它；`temporary_path` 先建空檔，`os.replace(old, aside)` 緊接著要覆蓋它，若此刻被持有 → `[WinError 32]`，流程會正確中止並顯示錯誤（無資料風險），但多了一個 transient failure 點。staged 檔也是先建空檔再由 `ZipFile("w")` 重開。
- 建議：列入 Windows 清單的 AV 項目一起觀察；若實測出現，aside 改為「只產生名稱、不預建」（用 `O_EXCL` 建後立刻 unlink 不可取，直接以隨機名稱 rename 即可，碰撞機率 2^-64）。

**M-5 `casefold()` 比 NTFS upcase 表更寬**（`client/documents/session.py:52-54`）
- `Straße` vs `Strasse`、`ﬁle` vs `file`、`K`（U+212A）vs `k` 在 `casefold()` 下相等，NTFS 視為不同檔；結果是「被拒為重複」（安全方向）。D8 只寫了反方向（NTFS 相等但 casefold 不等）。只記錄；中文名無此問題。

**M-6 測試套件 +2–5 s 來自 40 次真實 fsync**（見第 3 節）
- 建議：`_EditorHarness` 或 `DictionaryEntriesTraceTest` 以 `patch("os.fsync")` 換成 no-op（replay 驗的是 dialog 行為與 bytes，不是耐久性；`tests.test_atomic_write` 已專責 fsync）。

**M-7 docstring 寫「hidden file」**（`client/documents/workspace.py:88`、`client/shared/atomic_write.py:3`）
- Windows 的前導點不是隱藏屬性，Explorer 會顯示 `.Alpha.dep.<rnd>.tmp`。改寫成「dot-prefixed, never matched by `*.dep`／`*.csv`」即可。

**M-8（不確定）`os.replace` 對帶 hidden／system 屬性的目標**（`client/shared/atomic_write.py:87`）
- 我記得 `MoveFileEx(REPLACE_EXISTING)` 對唯讀目標會 `ERROR_ACCESS_DENIED`（已由 `os.access` 先擋），對 hidden／system 目標是否也失敗我沒有把握。若失敗，結果仍是「訊息＋原檔不變」，不是資料風險；列入 Windows 清單實測。

## Windows 驗證清單 delta（接在 P2 記錄「Windows 驗證總清單」第 16 項之後）

**F-1（workspace case collisions）**
17. `cd client && python -m unittest tests.test_case_insensitive_package_files tests.test_document_workspace tests.test_document_controller tests.test_workspace_service tests.test_gui_document_flows -v`：預期全綠、`test_gui_document_flows` 無 skip；特別記錄 `test_case_only_rename_keeps_the_document`、`test_case_only_rename_moves_the_package_and_updates_the_controller`、`MoveDocumentPackageTest` 十個、模型四個自測（這些在 NTFS 上第一次執行）。`tests.test_dictionary_name_prompt ... test_case_only_rename_still_renames` 預期 error（既有，記錄即可）。
18. Packaged build：建 `Alpha`、打字、Rename 成 `alpha`、重啟 → 文件與內文都在，`dir` 顯示 `alpha.dep`、無 `.tmp`。Add `ALPHA` → 重複訊息、磁碟不變。選另一份文件 Rename 成 `Alpha` → 同。
19. 以 7-Zip 開著 `Alpha.dep` 時 case-only rename → `Failed to save document: [WinError 32] ...`，列表仍 `Alpha`，重啟後 `Alpha.dep` 內容不變，目錄無 `.tmp`。
20. 對 `Alpha.dep` 設唯讀屬性後 case-only rename → 預期成功，但留下唯讀的 `.Alpha.dep.<rnd>.tmp`（D4 step 4 忽略清理失敗）；記錄 Explorer 是否顯示它（M-7）。
21. 即時防毒開著連續做 10 次 case-only rename（`a`↔`A`）：記錄任何 transient failure（M-4）。

**F-2（dictionary file safety）**
22. `cd client && python -m unittest tests.test_atomic_write tests.test_dictionary_entries tests.test_dictionary_entries_dialog tests.test_dictionary_manager tests.test_dictionary_management_dialog tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps -v`：A8–A10 `skipped`（POSIX only）；`test_os_error_shows_the_message...` 的訊息以 ` -> '<path>'` 結尾（`[WinError 5]`）；A4 的 tmp 名為 `.d.csv.<16 hex>.tmp`。
23. 以 `fc /b` 比對：同一份字典在 F-2 前後的 build 各按一次 OK，CSV bytes 相同（`\r\n`、無 BOM；驗 `O_BINARY`）。
24. Excel「CSV UTF-8」與記事本（UTF-8 with BOM）各存一份字典 → Import → Dictionary Management 顯示筆數 → 編輯器顯示列 → OK → 轉換使用該字典；OK 後檔案無 BOM。
25. Excel 開著該字典時按 OK → `儲存失敗：[WinError 32] ...`，列保留、檔不變；關 Excel 再 OK 成功；字典資料夾無 `.default.csv.*.tmp`。
26. 設唯讀屬性後 OK → `儲存失敗：[Errno 13] Permission denied: '<path>'`，無 `.tmp`；清掉屬性後 OK 成功，新檔無唯讀屬性。
27. 設**隱藏**屬性後 OK：記錄成功或失敗訊息（M-8，不確定）；兩種結果都要求原檔不變、無 `.tmp`。
28. 即時防毒開著連續 OK 10 次：記錄 transient failure 與是否留下 `.tmp`（D8）。
29. 一個 ACL 拒寫、允許刪除的字典（`icacls` 設 `(D)` deny write）按 OK：記錄是被覆蓋（判決變寬）還是失敗；只記錄，不要求改。

## 剩餘缺陷清單（優先 2 起；優先 1 四列已由 F-1／F-2 關閉）

| 優先 | 缺陷 | 來源 | 影響 | 釘住的測試 | 建議修法 |
| --- | --- | --- | --- | --- | --- |
| 2（資料遺失，新列） | `save_document_package` 就地 truncate：Save／Add／Import／regular Rename 寫到一半（斷電、磁碟滿、lone surrogate 的 `UnicodeEncodeError`）留下截斷的 `.dep`，下次啟動列為 invalid 並提議刪除 | 本次審查第 4 節 | 中高：每次切換文件都會 Save | 無 | `PackageFiles.write` 內 stage＋`os.replace`（原語都在），或 binary 版 `write_*_atomically`；同時把 GUI 的 `except OSError` 放寬（M-1） |
| 2（資料不一致） | Rename 時 unlink 舊包失敗 → 磁碟兩份、記憶體一份 | P1-3 defect 3 | 中 | `test_rename_unlink_failure_leaves_both_packages_and_state`、service 版 | regular rename 改走 `move_document_package`（F-1 D6 的三個決定：訊息文字、唯讀包靜默留 `.tmp`、injector 重設計）；翻兩個 KNOWN BUG 與 `test_regular_rename_does_not_use_package_files` |
| 2 | Delete All 回滾後無有效文件：editors 清空但 title 不更新、不建 default | P1-3 defect 4 | 中低 | `test_delete_all_failure_without_valid_document_clears_editors_only` | 回滾分支呼叫 `_update_window_title()` + `_ensure_open_document_exists()` |
| 2 | 字典編輯器 OK 永遠重寫檔案，靜默丟掉 loader 略過的列與被 strip 的空白 | P2-2 Q2 | 中 | `test_unchanged_dictionary_is_rewritten_in_normalized_form` | 只在有變更時寫；或保留原始列 |
| 3（新列） | F-1 move-aside 與 install 之間 crash → 無 `.dep`、資料在兩個 `.tmp`、啟動無提示 | 本次 M-2 | 低機率、中影響 | 無 | 啟動時掃 `.*.dep.*.tmp` 並提示／自動復原 |
| 3（新列） | `save_preprocessing_script` 寫入失敗漏 `.tmp`、POSIX 腳本變 `0600`；`manager.py` 四個 writer 失敗留部分新檔；`config.json` 就地寫 | F-2 Follow-ups、本次第 4 節 | 低 | 無 | 全部改走 `write_text_atomically`（copy 需 binary 變體）；確認 `ConfigStore._load` 對壞 JSON 的處理 |
| 3 | 轉換中 Ctrl+Tab／Ctrl+O 仍可切換文件，結果寫入完成當下開啟的文件 | P1-4 defect 1 | 中高 | characterization case 17 | busy 期間擋 `on_char_hook`，或 presenter 記住啟動時的 open name |
| 3 | `convert_for_export` 不檢查 running：第二個 job 讓第一個結果靜默丟棄 | P1-4 defect 2 | 中 | cases 16、18 | presenter queue 或 running 時 `show_info` |
| 3 | pending 文件匯出 HTML 用舊快取 | P1-4 defect 3 | 中 | 無 | `convert_for_export` 的 on_success 帶 `dual_view_segments` |
| 3 | 字典編輯器 Add／Edit 重複時丟掉輸入；Delete／Cancel 無確認 | P2-2 Q6／Q5 | 中 | 有 | 重開 `AddSymbolDialog` 帶回原值；加確認（UX） |
| 3 | 字典編輯器載入失敗（壞 UTF-8）例外逃出建構子 | P2-2 Q8 | 中低 | `test_invalid_utf8_raises_from_the_constructor_after_the_native_dialog` | `gui.on_open_dictionary_management` 捕 `UnicodeDecodeError/OSError/csv.Error` |
| 4（新列） | 字典 case-only 改名在 Windows／macOS 被拒為重複；Linux 放行；`resolve_selected_dictionary` 精確比對 | F-1 spec Out of Scope | 低（UX） | `test_dictionary_presenter.py:397` skip；`test_dictionary_name_prompt.py:82` Windows 預期 error | 比照 F-1：casefold 檢查＋case-only 走 rename，並更新 `config.json` 的選取名 |
| 4（新列） | casefold 之外的 aliasing（NTFS upcase、APFS normalization；反向的 `ß`/`ss` 假重複）；Add／Rename 可覆寫磁碟上有、列表裡沒有的 `.dep`（啟動時選擇保留的 invalid 包）；legacy 同時含 `Alpha`／`alpha` 的 workspace 在 Windows Export All 互相覆蓋 | F-1 D8、Out of Scope | 低 | 無 | 以磁碟存在性再檢查一次；Export All 以 casefold 偵測目標碰撞 |
| 4 | 本地化四組（Export All 摘要、fallback、`"HTML"`、import reason、presenter `str(exc)`）；reserved 訊息永遠 `default`；設定面板 K1–K4；Ctrl+wheel quirk 1／2 | P2 清單優先 4 | 中／低 | 同前 | 同前（一個 localization 任務、UX 決策） |
| 5–7 | 穩健性（data 檔驗證、worker `BaseException`、Export All `ValueError`、關閉 race、`config.json` RMW 無鎖、`log.exception()` 無訊息、`sync-nvda.py` 還原 sconscript）、效能（`reclean_braille_endspace`、`LanguageDetector`、snapshot I/O）、測試與文件 | P2 清單優先 5–7 | 同前 | 同前 | 同前，無變動 |

## 建議的下一步

1. 補 I-1 的測試斷言（一個 `test:` commit）；順手做 M-6、M-7。
2. 執行 Windows 清單 17–29，結果附回本記錄；F-1 在 NTFS 上通過之前，不要把 defect 1 標為「已在 Windows 驗證」。
3. 下一個 fix task 建議先收優先 2 的新列（`save_document_package` staging）＋ defect 3，兩者共用 `move_document_package`／`PackageFiles`，可以一次做完並翻掉 D6 的 guard。

## 修正紀錄（review 之後）

- I-1：`3d7809e` test: pin flush before fsync in atomic write —— `test_data_is_flushed_to_disk_before_the_replace` 於 fsync 時記錄 `os.fstat(fd).st_size` 並斷言為完整長度 `[5]`；移除 `stream.flush()` 的 scratch mutant 以 `[0] != [5]` 失敗。
- M-3：`016c343` fix: keep package permissions on case-only rename —— 新增 `PackageFiles.copy_permissions`（POSIX 用 `shutil.copymode`，Windows 不動作），`move_document_package` 在安裝前於既有保護區塊內呼叫；新增 0640 保留測試與 copy 失敗回復測試。舊包不存在時新包仍為 0600（production 不會發生，保留）。
- M-6：`5757cd9` test: skip fsync in dictionary editor trace replay —— `_EditorHarness.open()` 期間以 no-op 取代 `os.fsync`，`test_atomic_write` 仍用真 fsync；全套 5.1–5.7 s → 3.5–3.6 s；trace fixture sha256 不變。
- 驗證：全套 `Ran 1141`, `failures=1`（P2-5）, `skipped=7`；20 個 shuffle seed 皆僅 P2-5；msgid 353；兩個 fixture 不變；app-data snapshot 不變。
- 未處理（交由使用者決定）：新發現的 P2 資料遺失風險 `save_document_package` 原地截斷寫入，建議與 defect 3 一併處理；其餘 Minor 與 follow-up 如上。

## Windows 驗證結果（2026-10-09）

完整記錄：`docs/superpowers/history/2026-10-09-03-windows-verification/results.md`。

- 17：`Ran 253`。NTFS 上的 F-1 測試（含 `MoveDocumentPackageTest`、case-only rename）全部通過。`test_case_only_rename_still_renames` 依預期 error。另有 2 個 HTML 匯出 CRLF failure，屬於測試假設，已由 W-2（`4b4a2b6`）修正。
- 22：`Ran 162`，`OK (skipped=3)`（A8–A10 POSIX only）。
- 18–21、23–29：需要 packaged build 或人工操作，尚待執行。在這些項目通過之前，I-2 維持不變：不要在 release note 宣稱 Windows 上已修復。
