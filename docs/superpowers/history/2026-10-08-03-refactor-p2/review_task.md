# Refactor Phase P2 — Review Record（P2-1、P2-2、P2-3、P2-4、P2-6、P2-7）

## Review scope

審查範圍為 main 上 `000239b..e57cae7` 全部 51 個提交（六個任務，各以 `merge: ... (P2-N)` 合併；P2-5 尚未開工，P2-8 已決定略過），對照：

- `storage/refactor.md` §6.3（roadmap 來源）與 §3–5（細節發現）、§7（不建議變更）
- `docs/superpowers/specs/2026-10-08-p2-{1,2,3,4,6,7}-*-design.md`（含 zh-TW 版，行數與英文版逐一相同）
- `docs/superpowers/plans/2026-10-08-p2-*.md`（六份皆含 "Spec Corrections and Refinements"）
- `docs/superpowers/history/2026-10-08-01-refactor-p0/review_task.md`、`2026-10-08-02-refactor-p1/review_task.md`（追蹤 P0 M-1..M-9、P1 I-1 與 M-1..M-10 的後續）

Orchestrator 已記錄的決策視為既定前提，不重新爭論：P2-6 刪除 module-level config 函式與 `CONFIG_PATH`、改以 `ConfigStore` + 注入的 `ApplicationPaths`，並把 conversion presenter 搬到 `ui/`；P2-7 改 `scripts/sync-nvda.py` `_adapt_helper` 並重新產生 `vendor/nvda/liblouis/runtime/louis_helper.py`（git-ignored 的 `client/braille/louis_helper.py` 只由 Windows `install.bat` 更新）、移除 MathCAT singleton、加入測試 log 隔離；P2-2 更名 `SpeechSymbolsDialog` → `DictionaryEntriesDialog`；P2-4 不引入 event bus。

審查方式：

1. 逐檔閱讀 production diff（`git diff 000239b..e57cae7 -- . ':!client/tests' ':!docs'`，30 個檔案、+1059/−831）；`gui.py`、`dialog.py`、`settings/dialogs.py`、`config.py` 以新舊版並排逐流程比對；三個新模組（`ui/dialog_base.py`、`settings/options.py`、`dictionaries/entry_list_model.py`）與被改動的 `adapters/translation/{provider,mathcat}.py`、`conversion/{mathcat_adapter,math_service}.py`、`braille/tables/__init__.py`、`scripts/sync-nvda.py`、`vendor/.../louis_helper.py`、`app_paths.py`、`log.py`、`client_init.py`、`main.py` 全文閱讀。
2. 以 venv 執行全套件、六個 spec 的全部 acceptance 指令（unittest 組合與 grep）、全套件 seeded shuffle 20 seeds、`scripts/tests`、每個測試模組單獨計時、app-data 快照（含 `client/log/*` sha256）前後比對、msgid 掃描。
3. 以 AST 掃描 `client/` 全部 top-level package 的相依方向；執行所有 import guard。
4. P2-5：對失敗測試做 `git bisect`（`fd3aa74..6e5819f`，獨立 worktree，事後已移除）並以 probe 比較 bisect 前後的 tokenization 與 dual-view segments。
5. 本機為 Linux，無 wxPython、無 liblouis DLL、無 MathCAT、無 PyInstaller、無 msgfmt/xgettext、無 pytest；Windows-only 與 PyInstaller 路徑只能讀碼（見「Windows-only／無法在本機驗證」）。

## Result

**Verdict: Ready（六個任務的 production 行為未發現 regression；一項 Important 為安全網／流程問題（Windows 驗證債跨 P0–P2 全數未清、且 P2-7 的產生檔只有 Windows 能刷新），不阻擋 P2 收尾，但必須在 P2-5 之前處理）。**

- Critical：0
- Important：1（I-1）
- Minor：11

六個任務的 acceptance criteria 皆以實際指令驗證通過。使用者可見行為（對話框文字／順序／焦點／結果、設定面板的選項標籤／順序／選取／儲存值、Ctrl+wheel 字型同步、啟動順序與錯誤對話框、`config.json` bytes、log 檔、轉換輸出）經逐行比對舊碼未發現改變。msgid 集合 353 不變（`.pot` 357，差異仍為四個 orphan wildcard，Windows 待重產）；`client/locales`、`client/braille/tables/__tables.py`、`vendor/nvda/liblouis/{SOURCE.json,build,python}`、`vendor/nvda/mathcat` 無 diff；`translation_golden.json` sha256 `e67d95a1…1ccd` 未變；P2-2 新增的 `dictionary_entries_trace.json` sha256 `f493da52…cf` 與 spec 一致。

## Verification（實際執行結果）

venv：`$SP/venv/bin/python`（Python 3.14），皆於 `client/` 執行。

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| 全套件 | `python -m unittest discover -s tests -p "test_*.py"` | `Ran 1095 tests in 2.5s`, `FAILED (failures=1, skipped=9)`；唯一失敗為已知 P2-5 `test_conversion_service...test_translate_with_language_does_not_duplicate_existing_spaces_around_math`；9 skips = 7 Windows-only liblouis + 2 case-insensitive FS |
| 全套件 shuffle | `shuffle_harness.py <seed>`，seeds 0–19 | 20 個 seed 全部 `ran=1095 failures=1 errors=0 skipped=9`，唯一 BAD 為 P2-5 |
| scripts tests | repo root `python -m unittest discover -s scripts/tests` | `Ran 27 tests ... OK`（含新增 `test_vendor_helper_snapshot`，`include/nvda` 已 checkout 故未 skip） |
| P2-1 AC1 | `tests.test_dialog_validation tests.test_dialog_display tests.test_settings_dialogs` | `Ran 102, OK`（spec 寫 71；之後 P2-3／P2-4 再加入 `test_settings_dialogs` 的測試，數字合理） |
| P2-1 AC2 | spec 列的 13 個模組 | `Ran 370, OK (skipped=2)` |
| P2-1 AC4 greps | `__enter__/__exit__/_normalize_dialog_name/"exceed"` in `dialog.py`；`_is_destroyed_window_error/def _destroy` in `settings/dialogs.py`；`raise ValueError` in `shared/name_validation.py`；`class ConvertingDialog/finalize_dialog_layout` in `gui.py`；`in str(exc)` repo-wide | 全部空 |
| P2-2 AC1 | `tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog` | `Ran 105, OK` |
| P2-2 AC6 greps | `SpeechSymbols`（`--include=*.py`）；`filtered_entries/_identifier_exists/_normalize_type/Path("data")` in `dialog.py` | 全部空 |
| P2-3 AC1 | `tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_settings_options` | `Ran 110, OK` |
| P2-3 AC6 greps | 舊常數名 12 個；字面值 `"unicode|ascii|light|dark|simbraille|UEB|Nemeth"`（排除 tests） | 第一個空；第二個只列 `settings/options.py`、`config.py`（3 個 `DEFAULT_*`）、`conversion/math_braille_codes.py`、`conversion/output.py`（2）、`ui/conversion_presenter.py:84`（P2-6 搬家後的位置，spec 寫 `conversion/presenter.py`）、`main.py:23`，與 spec 一致 |
| P2-4 AC1 | `tests.test_settings_dialogs tests.test_dialog_base tests.test_gui_document_flows tests.test_view_settings tests.test_input_shortcuts` | `Ran 273, OK (skipped=2)` |
| P2-4 AC6 greps | `sync_open_font_size` repo-wide；`grep -nw _instance gui.py`；`grep -n _instance gui.py`；`isinstance(panel, ViewSettingsPanel)`；`font_size_dirty|font_size_spin` | 空；空；只有 `gui.py:564` `open_instance()`；只有 `settings/dialogs.py:777`（`_view_panel`）；全在 `ViewSettingsPanel`（562–629） |
| P2-6 AC1 | `tests.test_app_paths tests.test_config tests.test_gui_document_flows` | `Ran 204, OK (skipped=2)`（與 spec 的 204 相同） |
| P2-6 AC1b | spec 列的其餘 15 個模組 | `Ran 141, OK` |
| P2-6 AC6 greps | `CONFIG_PATH`；五個 `get_*_directory/get_config_path`；`(_dir|directory|paths): (Path|ApplicationPaths) \| None`；`conversion\.presenter|conversion/presenter`；`documents` import in `conversion/`；`conversion/presenter.py` 存在 | 全部空／不存在 |
| P2-6 AC7 ＋ P2-7 AC6 | app-data 快照（`config.json`、`workspace/` 存在性、`dual_view/` 非原始碼項目、`log/` 名稱＋每檔 sha256）於全套件前後 | `SNAPSHOT IDENTICAL`（套件不再 append 到 `client/log/*.log`） |
| P2-7 AC8 | CRLF 檢查 `braille/tables/__init__.py` | 255 行 `\n` = 255 行 `\r\n`；diff 只含 D1／D4／D5 行 |
| P2-7 AC9 | `command grep -rn "basicConfig\|_tablesDirs\.get\|get_shared_mathcat_adapter\|_SHARED_ADAPTER" client scripts vendor` | 恰為 spec 列出的集合：`tables/__init__.py:189`（D5 本體）、`sync-nvda.py:175`（NVDA 端 marker）、`vendor/.../python/louisHelper.py:53`（NVDA 原檔）、兩個測試檔、以及 git-ignored 舊 `client/braille/louis_helper.py:22,65`；`get_shared_mathcat_adapter`／`_SHARED_ADAPTER` 無任何匹配 |
| P2-7 AC7 | `git diff --stat` on `__tables.py`、`SOURCE.json`、`vendor/.../build`、`python`、`mathcat`、`client/locales`、`scripts/generate-pot.bat` | 空（fixtures 只多了 P2-2 的 trace） |
| msgid | `msgid_scan.py client` | `source msgids: 353`、`pot msgids: 357`、only-in-pot 恰為 EPUB／PDF／Text／Word 四個 wildcard |
| import guards | `tests.test_translation_import_isolation tests.test_removed_dead_code tests.test_i18n tests.test_dialog_base tests.test_settings_options tests.test_braille_glue tests.test_conversion_presenter` | `Ran 106, OK` |
| 每模組計時 | 82 個模組各自單獨執行 | 總和 11.6 s（含 interpreter 啟動）；最慢 `test_app_paths` 0.46 s（含 subprocess）、`test_gui_document_flows` 0.44 s（160 tests）、`test_translation_import_isolation` 0.44 s（6 個 subprocess） |
| `gui.py` 尺寸 | AST 量測 | `6e5819f`：1817 行，`BrailleFrame` 1502 行／125 方法 → `000239b`：1101／920／93 → `e57cae7`：1101／934／93（`ConvertingDialog` 14 行搬出、`BrailleFrame.__init__` 與 `BrailleApp` 各多幾行注入） |
| P2-5 bisect | `git bisect run`，good `fd3aa74`（測試誕生）、bad `6e5819f` | first bad commit = `6e5819f` 本身（`feat: align language detection with configured language`，2026-07-24，即重構基線）；`0586171` 通過 |

## Findings

### Critical

無。

### Important

**I-1 Windows 驗證債已累積到 P0–P2 全部 18 個任務未清，而 P2 新增了三類「只有 Windows 能證明」的變更；P2-5 開工前必須先有一次乾淨的 Windows 基線**

- 來源：P1 review I-1 建議的 Windows session 至今沒有執行紀錄；六份 P2 spec 的 "Windows verification debt" 段落同樣沒有紀錄。
- P2 新增的 Windows-only 風險（讀碼確認、本機無法執行）：
  1. **P2-7 的產生檔只在 Windows 刷新。** `client/braille/louis_helper.py`（git-ignored）在本 checkout 仍是舊版（`louis_helper.py:22` `logging.basicConfig(...)`、`:65` `braille_tables._tablesDirs.get(...)`，見 AC9 grep）。在任何還沒跑 `scripts\install.bat` 的 Windows checkout 上：(a) 從 source 執行仍會設定 root logger（D2 的行為差異看不到）；(b) `tests.test_liblouis_runtime` 跑的是舊 resolver，**不會**驗證新的 `get_table_directory` 路徑；(c) `scripts\build-dotexpress.bat` 直接打包工作副本，沒先 `install.bat` 的包裝版會帶舊 helper。舊 helper 仍可運作（`_tablesDirs` 保留），所以不是 regression，但代表 P2-7 的核心改動在 Windows 上尚未被任何測試碰到。
  2. **P2-1 D1 的前提未驗證**：`_DEAD_WINDOW_ERROR_TYPES` 以 `getattr(wx, "PyDeadObjectError", None)` 取代直接命名；spec 假設 wxPython 4.2.5 沒有該屬性（否則舊碼在這條不可達路徑會 `AttributeError`）。所有 stub 都定義了 `PyDeadObjectError`，Linux 看不到真實情形。另外 mixin 排在 sip class 前面（`class X(Mixin, wx.Dialog)`）、`ContextManagedDialog.__exit__` 覆蓋 Phoenix 自己的 `__exit__`，語意相同但只在真 wx 上能證明。
  3. **P2-6 frozen 路徑**：`BrailleApp.OnInit` 現在先 `build_application_paths()`（`sys.executable` parent）再驗證；`log._log_directory()` 在每個模組 import 時解析同一個 root。讀碼確認與 2026-07-20 契約相同，但 `--onefile` 的 `_MEIPASS` vs exe 目錄只能在包裝版確認。
  4. **P2-7 MathCAT 生命週期**：`TranslationRuntime.close()` 現在先 `MathCATAdapter.close()`（關閉 `os.add_dll_directory` handle）再 `louis_helper.terminate()`；轉換中退出的 race（spec Risks）只在 Windows 可重現。
  5. **P2-3 D6**：`_(table.displayName)` 保留的理由（source run 英文名、packaged 已翻譯、再翻譯 idempotent）以 AST 對真實 catalog 驗證過，但「source run 與 packaged 的表格順序相同」仍需在 Windows 看一次。
- 為何列 Important：下一個任務 P2-5 是 `translate.py` 拆 tokenizer／wrapper（roadmap 標「中–高」風險），其 golden fixture 只用 fake helper；沒有真 liblouis 的 Windows 基線（BRL bytes、三個 Windows-only 測試模組、`reclean_braille_endspace` 的 trim 次數），P2-5 只能證明「fake 下不變」。而且本次 P2-5 分析（見下節）顯示失敗測試的差異來自 `LanguageDetector`，真 adapter 下的 tokenization 是否真的相同也要 Windows 才能回答。
- 建議：排一個獨立的 Windows session（半天到一天），依本記錄最後一節的總清單執行，順序：`install.bat`（刷新 helper，`fc /b` 比對 vendor）→ 三個 Windows-only 模組＋`discover`（把 `Ran/skipped` 數字附回）→ `generate-pot.bat` + `msgmerge` + `.mo` → packaged build 走各 spec 的手動項目 → 為 P2-5 蒐集基線（同一份長文件的 BRL bytes、`" 的值"` 一次翻譯 vs 兩次翻譯的 cells、trim 次數）。把結果當作 P2-5 的前置條件。

### Minor

**M-1 `conversion` 套件反向依賴 `adapters.translation.contracts`（pre-existing，P2-6 的分層 guard 沒有涵蓋）**
- 位置：`conversion/service.py:1`、`conversion/jobs.py:5`、`conversion/output.py:5`、`conversion/text/pipeline.py:4`（皆 `from adapters.translation.contracts import TranslationRuntime`）；`ui/conversion_presenter.py:17` 同。`000239b` 已如此（2026-07-06 adapters 任務引入），非本階段 regression。
- 評估：`contracts.py` 只有 Protocol 與 `TranslationRuntime` dataclass，無副作用，所以沒有循環或 import 問題；但依名稱分層，domain（`conversion`）依賴 `adapters` 是方向反了（Protocol 應由使用端擁有）。P2-6 新增的 `test_conversion_package_imports_no_higher_layer` 的 `HIGHER_LAYERS` 不含 `adapters`，所以 guard 不會提醒。
- 建議：P2-5 動 `conversion/` 時把 `contracts.py` 搬到 `conversion/contracts.py`（`adapters` 反向 import 它），並把 `adapters` 加進 `HIGHER_LAYERS`；或在 `refactor.md` §4.3 分層圖註明 `adapters.translation.contracts` 視為 conversion 的一部分。

**M-2 `tests/test_gui_document_flows.py` 已 4028 行／15 個 class／160 個測試；P1 M-2 的兩個可測性弱點仍在**
- `BrailleAppLifecycleTest(GuiDocumentFlowsTest)`（`:491`）仍繼承，基底 5 個測試跑兩次；`frame._workspace_service = Mock()`（`:250`、`:875`）無 spec。P2-4 與 P2-6 各加一個 class（`ViewFontSizeSyncCharacterizationTest`、`ApplicationPathsWiringCharacterizationTest`），P2-6 spec 明列拆檔 out of scope。
- 建議：P2-5 之前（或與 P2-5 平行的測試衛生任務）拆成 `test_gui_document_flows`／`test_gui_app_lifecycle`／`test_gui_conversion_export`／`test_gui_settings_paths`，順手 `Mock(spec=DocumentWorkspaceService)`。

**M-3 P0 M-2／P1 M-3 的 absence／import-set 守門測試仍在，且每個 P2 任務都被迫碰它們**
- `tests/test_removed_dead_code.py`（5 個）；`tests/test_i18n.py::SharedSetupConsumerTest` 仍要求每個模組從 `i18n` import 的名稱集合**完全相等**（P2-3 加了 `settings/options.py = {"N_"}`）；`test_dictionary_dialog_helpers_and_imports_are_removed_from_gui` 的 "kept" 名單在 P2-6 step 4 被改（spec 有說明）。P2-4／P2-6 為了不觸發 AC 的 grep，改採 allow-list 寫法，方向正確。
- 建議：P2-5 之前一次決定：`SharedSetupConsumerTest` 改為「不得自建 catalog／`resource_path`」的負向斷言；`test_removed_dead_code.py` 與 P0-6 的 "kept" 名單退場（相關 P1-3／P1-4 positive contract 測試已足夠）。

**M-4 `tests/test_translation_result.py` 仍是 pytest-style，`unittest` 下 `NO TESTS RAN`，直接呼叫 13 個函式為 8 pass／5 fail**
- 失敗：`test_bind_word_tokens_lead_punct`、`test_bind_word_tokens_lead_punct_continue`（皆 `IndexError`）、`test_end_right_end_sentence_blank2`、`test_end_right_end_sentence_blank3`、`test_remove_start_line_blank`（`AssertionError`）。roadmap P2-5 的驗證指令引用此模組，實際貢獻 0 個測試。
- 建議：P2-5 step 1 轉成 `unittest.TestCase`，並與 P2-5 既有失敗一併裁決（哪些是過期預期、哪些是真缺陷）。

**M-5 文件殘留：`AGENTS.md:16`、`readme.md:175` 仍寫 `generate_pot.bat`（實際為 `scripts/generate-pot.bat`，P0 M-6）；`.pot` 四個 orphan 仍在；`storage/refactor.md` §6.3 行號已全部過期**
- 純文件；前兩項可併入 Windows session 的 `generate-pot.bat` 步驟一次處理，`refactor.md` 由 orchestrator 決定是否回寫狀態。

**M-6 P2-7 D9 的 `except BaseException: adapter.close(); raise`，若 `close()` 本身拋錯會以 `close()` 的例外取代原因**
- 位置：`adapters/translation/provider.py:103-107`。`MathCATAdapter.close()` → `handle.close()`（`os.add_dll_directory` handle）在 Windows 可能 `OSError`；此時 caller 收到的 `RuntimeUnavailableError(str(error))` 說的是 close 的錯而非 `initialize()` 的錯（原例外只在 `__context__`）。極低機率、只影響 `translation.log` 的 fallback 訊息。
- 建議：`try: adapter.close() finally: raise` 的寫法或 `except BaseException: try: adapter.close() except Exception: logger.debug(...)`；可與 M-7 一起處理。

**M-7 `MathCATAdapter.close()` 與 worker thread 的 race（P2-7 spec Risks）、以及 P1 M-10（不可 veto 關閉時 presenter 仍回呼已銷毀 frame）屬同一族**
- `OnExit` → `runtime.close()` 現在多關一個 adapter：worker 若正在 MathCAT 裡會收到 `MathCATError("MathCAT adapter is closed")` → `MathConversionError`（logged）。與 liblouis `terminate()` 的既有 race 相同，不是新問題，但 close 的順序（math 先、liblouis 後）讓「math 段先失敗、text 段再失敗」的順序固定。列入既有缺陷清單第 5 組，建議由 presenter `shutdown()` 一次解決。

**M-8 三個 view Protocol 各自宣告 `show_info/show_error`，且簽名不一致**
- `dictionaries/presenter.py:38-40` `show_info(message)`；`ui/conversion_presenter.py:59-61` 與 `documents/export_coordinator.py:32-36` `show_info(message, caption)`。P1 M-7 已記錄；P2-6 搬家後三者仍各自獨立。frame 只實作一次，無害；若 P2-5 之後再整理 UI 層，抽一個 `MessageView`。

**M-9 本階段新產生的無消費者名稱**
- `dictionaries/manager.py:11` `MAX_DICTIONARY_NAME_LENGTH`（P2-1 刪掉唯一消費者）、`dialog.py:327` `DictionaryEntryListCtrl` alias（P2-2 明列 out of scope）、`braille/tables/__init__.py` `getDefaultTableForCurLang`（P2-7 D4 刻意保留並加 docstring）。另 P1 M-6（`apply_dictionary` 只剩測試用）與 M-8（`service.py:21-23` 三個 alias）仍在。
- 建議：一個小 `refactor:` 清掉前兩個與 `apply_dictionary`（同時更新 `test_removed_dead_code.py`）。

**M-10 `settings/options.py` D3 的 import-cycle 限制源自 `settings/__init__.py` 的 eager re-export**
- `config` 不能 import `settings.options` 是因為 `settings/__init__` 立即 import `translation`／`view`（它們 import `config`）。目前以 invariant 測試防止預設值漂移，可接受；若日後做 S-5（`ConfigStore` 的 repository shape），讓 `settings/__init__` 不再 eager re-export 即可把 `DEFAULT_*` 搬到 `options.py`。只記錄。

**M-11 測試 fixture 體積**
- `tests/fixtures/dictionary_entries_trace.json` 300,540 bytes（P2-2 golden trace，40×25 動作）、`translation_golden.json` 189,305 bytes；合計約 490 KB。皆在 spec 目標內，replay 測試 0.11 s；只提醒 P2-5 的 golden 不要再以同樣密度生成（建議以「代表性輸入 × 寬度」取代隨機序列）。

（不確定、未列入計數）P2-3 D2 把選項標籤改成顯示時翻譯，`tests/test_settings_dialogs.py` 現在任何 `patch("settings.dialogs._", identity)` 都會連帶把選項與表格列標籤變英文；spec 已說明且 part A 刻意不用該 patch。若未來有人在舊式測試裡加 label 斷言會踩到；可在 `test_settings_dialogs.py` 檔頭留一行註解。

## 正確性追蹤（對照 `000239b`）

### P2-1 dialog base／typed name errors

- `ui/dialog_base.py`：`ContextManagedDialog.__exit__` 只呼叫 `Destroy()`、回傳 `None`（例外傳播），與七份舊複本相同。`NameDialogBase._check_name` 對原始文字呼叫 `normalize_name`：`normalize_base_name` 的前四項檢查（空、控制字元、尾端空白／句點、長度）順序與舊 `_normalize_dialog_name` 的 pre-check 相同、再 `strip()`，所以訊息與寫回的 normalized 名稱相同（spec 的 3,431 筆 oracle 測試在 `tests/test_dialog_validation.py` 釘住）。`except ValueError: code = "invalid"` 保留舊的「其他 ValueError 一律 invalid」寬度；reserved 訊息仍 `format(name=DEFAULT_DICTIONARY_NAME)`（quirk 4 保留）。
- `_on_ok` 順序：訊息框（`wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)`）→ `SetFocus()` → return；成功則 `SetValue(normalized)` → `event.Skip()`。七個訊息改為定義處 `N_()`、顯示時 `_()`，msgid 集合不變。
- `SingletonDialogMixin`：`_raise_existing` 的呼叫順序 `Iconize(False)` → `prepare`（`select_category`）→ `Raise()` → `SetFocus()`；dead-window 判斷邏輯逐字相同；`_show_new` 先設 slot 再 `Show()`；`_destroy` 改以 `type(self).__dict__` 判斷（D2，兩個 production class 結果相同）。`DotExpressSettingsDialog.show_singleton` 的 `initial_category` 檢查仍在讀 slot 之前。D1 把 `except` tuple 改為 `(ReferenceError, RuntimeError, *dead_window_error_types)`，只影響真 wx 上不可達的路徑（見 I-1 第 2 點）。
- `NameValidationError(ValueError)`：`args == (message,)`、`str()` 不變；`dictionaries/presenter.py`、`documents/importers/base.py`、`workspace_service` 的 `except ValueError/Exception` 全部不動（grep 確認無 `in str(exc)`）。
- `ConvertingDialog` 原封搬到 `dialog.py:295-308`（tabs）；`gui.show_converting_dialog/close_converting_dialog` 未改；`_GUI_DIALOG_NAMES` 加入。

### P2-2 dictionary entry list model

- `DictionaryEntryListModel` 的每個方法是舊 `SpeechSymbolsDialog` 對應段落的逐行搬移：`matches` casefold；`apply_filter` 在改 filter **之前**以舊 visible list 取 `preferred_entry`；`_selection_after` = `min(fallback, n-1)` 再以 `visible.index(preferred)`（equality）覆蓋；`add` 的 duplicate 檢查涵蓋隱藏列、append 到尾端、不匹配時清 filter；`replace` 以 identity 找 full-list 位置；`remove` 以 `list.remove`（first equal）。D4 的四條比較規則寫在 module docstring。
- Dialog：`__init__` 順序 `super().__init__` → `Path(dictionary_path)` → `load` → `_build_ui()` → `_render(apply_filter(filter_ctrl.GetValue(), _get_selected_index()))` → `_update_button_states()`，與舊的 `filter_entries()` + `_update_button_states()` 等價（初次 `GetFirstSelected()` 為 `NOT_FOUND` → `None`）。wx 呼叫順序：Add 的 `MessageBox` 在任何列表變更前、`ChangeValue("")` 在 `SetItemCount` 前；Edit／Delete／OK 的訊息、`Skip` 時機不變。`_get_selected_index`／`_select_index` 的邊界改讀 `visible_count`。`dictionary_path` 改為必填（D6；`gui.py:950` 以關鍵字傳入）。
- `_update_button_states`、`_clear_selection`、`_on_selection_changed`、`_on_item_activated`、`_open_entry_dialog`、`AddSymbolDialog`、`CallbackVirtualListCtrl`、`dictionaries/entries.py` 不變。golden trace replay（1,000 動作）釘住整體。

### P2-3 settings option source

- `settings/options.py`：值／標籤／順序與舊的六份 tuple 逐一相同（`unicode,ascii`／`light,dark`／`default,simbraille`／`10..200`／`8..48`／五個表格欄位含 `required` = 舊 `{"default","math"}`、`fixed_choices` = `MATH_BRAILLE_TABLES`）；`option_value_at` 保留「越界 → 第一個選項」（K1）、`option_index` 保留「未知 → 0」（K2）、`IntRange.clamp` = 舊 `max(min, min(max, v))`。
- `settings/translation.py`／`view.py`：normalizer 改呼叫 helper，預設值仍來自 `config.DEFAULT_*`（D3），結果相同。`settings/dialogs.py`：三個 `wx.Choice` 的 `choices=[_(o.label) ...]`、兩個 spin 的 `min/max/initial` 與 `load_snapshot` clamp、`TranslationTablesPanel` 迭代 `TABLE_FIELDS`（列順序、`None selected` 只在非 required 列、空列 `Disable()`、`validation_error` 以欄位順序找第一個空的 required 列、`on_save` 五個 key）皆與舊碼逐行對應；`_options_for_field` 的 `fixed_choices` 取代 `if key == "math"`。`_(table.displayName)` 保留並加註解（D6）。
- `gui.py`：`VIEW_SCHEMES` 由 `VIEW_SCHEME_OPTIONS` 建，key／顏色相同；`== BRAILLE_FONT_SIMBRAILLE`。`config.DEFAULT_TRANSLATION_TABLES["math"]` 改讀 `DEFAULT_MATH_BRAILLE_TABLE`（值同 `"UEB"`）。

### P2-4 font size sync

- `gui._set_view_font_size` 前三步（normalize → `_apply_editor_view_settings` → `save_view_settings`）順序不變；第四步改 `DotExpressSettingsDialog.open_instance()` + `sync_font_size()`。`open_instance` 讀 `cls.__dict__.get("_instance")`，對宣告自己 slot 的 `DotExpressSettingsDialog` 與舊 `cls._instance` 相同。
- `DotExpressSettingsDialog.sync_font_size`：normalize → `_view_panel()`（同一個 `isinstance` 掃描）→ panel dirty 則 return（snapshot 不動）→ 否則 panel `SetValue` + 清 flag → snapshot `with_view`。與舊 classmethod 的差異只有「先 `SetValue` 再寫 snapshot」（D6，不可觀察）。`ViewSettingsPanel.sync_font_size` 直接讀 `self.font_size_dirty`（所有 production panel 在 `make_settings` 設定）。

### P2-6 application paths injection

- **啟動順序**（`gui.py:1060-1083`）：`build_application_paths()`（無 IO）→ `self.paths = paths` → `prepare_application_directories(paths)` → `cleanup_dual_view_html(paths.dual_view)` →（`ApplicationDataError`／其他 `OSError` 的兩個分支與對話框不變；`paths` 已綁定，消除 refactor.md §5.3 的 unbound-name 風險）→ `ConfigStore(paths.config)`（無 IO）→ `build_default_translation_runtime()` → `BrailleFrame(None, runtime=, paths=, config_store=)` → `Show()` → `start_client_init_background(config_store)`。可觀察順序與 2026-07-20 契約相同（`test_app_startup_runs_steps_in_contract_order` 釘住）。`OnExit` 以 `getattr(self, "paths", None)` 守住，production 永遠有值。
- **`ConfigStore`**：每個方法是舊模組函式本體把 `CONFIG_PATH`／`_load_from_file`／`_save_to_file` 換成 `str(self._path)`／`self._load()`／`self._save()`；first-save 的 `language_detection` 注入、`os.makedirs`、`json.dump(ensure_ascii=False, indent=2)`、log 訊息與 `_logged_load_failures`（以 path 字串為 key、module-level）皆不變；`get_lang` 的順序 `_runtime_lang` → `TEXT2BRAILLE_LANG` → file → `zh_TW` 不變；每次 getter 重讀檔案（P1-1 的「每個 request 讀一次」仍成立，`ApplicationPathsWiringCharacterizationTest` 以 `open` 計數釘住）。
- **Threading**：`client_init.start_client_init_background(config_store)` 的 worker（`daemon=True`）呼叫 `config_store.get_or_create_client_id`／`get_lang`，client id 仍在背景 thread 建立與寫檔（`test_no_client_id_is_created_before_the_worker_runs` 釘住）；UI thread 的 `set_selected_dictionary`／`save_*` 與它共用同一個 `config.json`，無鎖的 read-modify-write race 與舊碼相同（quirk 2，未修）。`run_client_init` 的 `client_id_provider`／`locale_provider` 改為必填 keyword-only，`client_init.py` 不再 import `config`（subprocess guard）。
- **Frame**：`_initialize_state` 順序 `dictionary_dir = paths.dictionary` → presenter → `load_translation_settings(store, names)` → `load_translation_tables(store)` → `DocumentWorkspaceService(controller, paths.workspace)` → font → `load_view_settings(store)`，與舊碼相同；`_open_dual_view_in_browser`、`apply_settings_from_dialog`（三個 save 順序）、`_set_active_dictionary`、`_build_conversion_request`（`get_lang()` 再 `get_charset_maps()`）只換資料來源。
- **D11**：`dictionaries/manager.py`、`name_prompt.py`、`documents/workspace.py`、`dual_view/files.py` 的目錄參數改必填，`Path(x)` 與舊 `get_*_directory(x)` 對非 `None` 的回傳相同；production 呼叫端全部已傳明確目錄。`main.run_demo` 自成 composition root（不驗證目錄，與舊碼同）。`log._log_directory()` 與 `OnInit` 用同一個 resolver（D10）。
- **M-1 搬家**：`git mv conversion/presenter.py ui/conversion_presenter.py`，內容零變更（diff 顯示 rename 100%）；`test_conversion_package_imports_no_higher_layer` 以 AST 守住 `conversion/**` 不 import 七個高層套件。`gui.py:30` 那行 tab 縮排的 `get_workspace_directory,`（P1 M-9）隨 import 刪除而消失。

### P2-7 braille glue／MathCAT lifecycle

- `braille/tables/__init__.py`：`log = logging.getLogger(__name__)` 取代 `log = logging` + `basicConfig`；`addTable` 的兩處 `log.warning(...)` 呼叫點與訊息不變（改為 named logger，不再觸發 `logging.warning` 的隱性 `basicConfig()`）。`get_table_directory(source)` = `_tablesDirs.get(source)`，讀 module global（`terminate()` 後 parent map 仍在）。D4 docstring 一行。CRLF 完整。
- `scripts/sync-nvda.py` `_adapt_helper`：只改兩個 replacement 字串（去掉 `basicConfig` 區塊；`_tablesDirs.get` → `get_table_directory`）；marker 檢查與迴圈不變。`vendor/.../runtime/louis_helper.py` diff 恰為五行 `basicConfig` 消失 + 一行 resolver；`test_vendor_helper_snapshot` 證明 snapshot = `_adapt_helper(include/nvda/source/louisHelper.py)`。**向後相容**：舊的已安裝 helper 讀 `braille_tables._tablesDirs`（仍存在）→ 可運作；新 helper 需要 `get_table_directory`（同一 branch 先落地）。`_isDebug()` 在無 `basicConfig` 下 effective level `WARNING`，仍 > `DEBUG`，liblouis log callback 行為不變。
- **Logging 全貌**（移除 `basicConfig` 之後）：app 的六個 `get_logger` logger 都 `propagate=False`、各自 `FileHandler(delay=True)`，與 root 無關 → `<root>/log/*.log` 內容不變；packaged 以 `--noconsole` 建，root 輸出本來就丟棄；只有 source run 的 console 少了帶時間戳的 `INFO` 行（D2，spec 已宣告）。測試側以 `tests/file_log_isolation.py` 把四個會寫檔的 logger 換成 `NullHandler`（`addModuleCleanup` 還原），快照證明套件不再 append。
- **MathCAT**：`create_default_math_translator` 順序 platform 檢查 → import → `adapter_factory()`（預設 `_create_mathcat_adapter()` = `MathCATAdapter(resource_root=get_default_mathcat_resource_root())`）→ `initialize()`（失敗 → `close()` → 原例外繼續 → `ImportError/OSError/MathCATError` 映射為 `RuntimeUnavailableError`，其他傳播）→ `MathCATMathTranslator(translate_math=partial(translate_math_segment, mathcat=adapter), close=adapter.close)`。`build_translation_runtime` 的 `_close_callback` 已會收任何 callable `close`，所以 runtime 的 `close_callbacks = (liblouis.close, mathcat.close)`，`TranslationRuntime.close()` 反序 → MathCAT 先、liblouis 後（D10）。`MathCATAdapter.close()` 冪等（先清 handle 再關、`_libmathcat=None`、`_closed=True`）；關閉後 `initialize()`／`get_braille_for_mathml()` 以 `_ensure_open()` 拋 `MathCATError`（在 `try` 之前，所以 `translate_math_segment` 仍包成 `MathConversionError` 並 log）。`math_service` 不再 runtime import `mathcat_adapter`（`TYPE_CHECKING` only），平台中立 guard 仍過。`gui.OnExit`／`main.run_demo` 的 `runtime.close()` 呼叫點不變。

### Windows-only／無法在本機驗證（僅讀碼）

- **PyInstaller**（`scripts/build-dotexpress.bat`）：`--onefile gui.py` + 五個 `--add-data` + `--collect-data latex2mathml`，無 hidden-import 清單。P2 新增／搬移的模組全部可由靜態 import 鏈到達：`ui/dialog_base.py`（`dialog.py:24`、`settings/dialogs.py:16`）、`settings/options.py`（`gui.py:86`、`settings/translation.py`、`view.py`、`dialogs.py`）、`dictionaries/entry_list_model.py`（`dialog.py:16`）、`ui/conversion_presenter.py`（`gui.py:33`）、`config.ConfigStore`（`gui.py`、`main.py`、三個 settings 模組）。唯一的動態載入是既有的 `importlib` 載 `libmathcat_py.pyd`（`mathcat_adapter._load_libmathcat`）與 `provider.py` 內的 function-level `from braille import louis_helper`（PyInstaller 的 bytecode 掃描會收進 function-level import；且是 pre-existing）。沒有新的 `__import__`／`importlib.import_module` 字串載入。
- **liblouis／MathCAT／wx**：見 I-1。
- **`generate-pot.bat`**：P2-1／P2-3 把 msgid 的 `#:` 參照位置搬到 `ui/dialog_base.py`（否，訊息定義仍在 `dialog.py`）與 `settings/options.py`；msgid 集合不變，重產只會移動參照。未執行。

## 設計品質評估（P0 → P2 整體）

- **`gui.py` 與 `BrailleFrame`**：1817 → 1101 行、`BrailleFrame` 1502 行／125 方法 → 934 行／93 方法（−38% 行、−26% 方法）。P2 本身對 `gui.py` 是零淨行數變化（搬出 `ConvertingDialog` 14 行，換來注入的建構子與 `OnInit` 多出的行），這是預期的：P2 的目標是品質而非減量。剩下的 93 個方法可分為：wx 組裝（`_create_*`、`_bind_events`、accessible name、字型，約 20）、文件流程的 wx 端 handler（`on_*_document`、`_prompt_for_document_name`、`_review_invalid_workspace_files`，約 25；邏輯在 `DocumentWorkspaceService`／`DocumentController`）、`ConversionView`／`ExportView` 實作（13）、設定與字典對話框入口（8）、dual view 視窗（6）、鍵盤／焦點（6）、其餘。`BrailleFrame` 已不再自己讀 config、算路徑、翻譯、匯出或管理字典；它是 composition + wx adapter，符合 roadmap S-1 的目標。
- **相依方向**（AST 掃描，top-level package）：`gui → *`；`dialog → dictionaries, documents, i18n, ui`；`settings → braille, config, conversion, dictionaries, i18n, ui`；`ui → adapters, conversion, documents, i18n, log, shared`；`documents → conversion, dual_view, i18n, shared`；`conversion → adapters(contracts), config, i18n, languageDetection, log, text, translate`；`dictionaries → i18n, shared, text, translation`；`config → conversion(math_braille_codes), log`；`log → app_paths`；`app_paths/i18n/shared/text/braille/languageDetection` 為 leaf。無 module-level 循環；`conversion ⇄ documents` 的雙向（P1 M-1）已由 P2-6 消除並有 AST guard；`settings → ui` 只到 `ui/dialog_base`（leaf mixin）。唯一反向的邊是 M-1 的 `conversion → adapters.translation.contracts`。`app_paths` 的 service-locator 用法只剩 `build_application_paths()` 的三個合法呼叫點（guard 釘住）。
- **新模組內聚**：`ui/dialog_base.py`（三個 mixin + 一個 dataclass，無 wx，有 AST guard）、`settings/options.py`（純資料 + 四個 helper，AST guard 禁 `_()`）、`dictionaries/entry_list_model.py`（單一 class，規則寫在 docstring）、`config.ConfigStore`（路徑即狀態，無快取）皆單一職責，沒有把 UI 字串或 wx 帶進去。`ConfigStore` 的 getter 仍「每個 getter 讀一次檔」，是刻意保留的 P1-1 契約，S-5 另案。
- **符合 refactor.md §7 的取捨**：P2-4 沒有引入 Signal／bus（一個 publisher、一個 subscriber）；P2-2 沒有做 presenter／View protocol（訊息留在 dialog）；P2-7 沒有為 liblouis 新增 log 檔（產品決策）；P2-6 沒有把 log 目錄注入 logger（D10 有理由）；P2-1 的 mixin 沒有 `__init__`／metaclass。
- **過度設計**：未發現。`EntryListUpdate` 兩個欄位、`NameDialogMessages` 五個欄位、`IntRange` 一個方法、`TranslationTableField` 五個欄位，都各自消除一組重複。唯一可議的是 `SingletonDialogMixin` 同時提供 `_raise_existing`／`_show_new`／`open_instance` 三個 classmethod 而 `show_singleton` 仍在子類——這是刻意讓兩個對話框保留不同的建構參數，可接受。
- **重複**：production 側剩 M-8 的三個 view Protocol。測試側：`RecordingChoice/RecordingSpin`（`test_settings_dialogs`）、`_RecordingNameCtrl/_RecordingEvent`（`test_dialog_validation`）、`RecordingConversionView`／`RecordingExportView`、P2-2 的黑盒 harness，各自服務不同 stub profile，沒有同形的複本；`object.__new__` 建構在 `test_gui_document_flows`（21）、`test_settings_dialogs`（20）、`test_dialog_validation`（13）普遍使用，是 stub 策略的必然，P2-2 的 harness 示範了「走真 `__init__`」的替代做法，值得推廣到之後新寫的對話框測試。
- **已解決的 P1 Minor**：M-1（presenter 位置）、M-9（tab 行）；**仍待**：M-2、M-3、M-4、M-5（本地化，見缺陷清單）、M-6、M-7、M-8、M-10。

## 測試品質評估

- **Characterization-first 且有凍結證明**：六個任務都先提 `test:` commit；P2-1 的 3,431 筆 oracle、P2-2 的 1,000 動作 golden trace（sha 固定、replay 比對每一步 log＋state＋CSV）、P2-3 以真 catalog 不 patch `_` 的 panel 觀測、P2-4／P2-6 以 helper 隔離「切換點」讓斷言零修改、P2-7 以 subprocess 檢查 root logger 狀態。每份 spec 都記錄 throwaway mutant 數（13／15／20／15／26+22+8／6+4+7），方向正確。
- **真正抓得到回歸的測試**：P2-6 的 decoy root（隱性路徑解析會落到 decoy 而非 `client/`）、`open` 計數證明 config 不快取、`test_no_client_id_is_created_before_the_worker_runs`；P2-7 的「兩個 `create_default_math_translator` 得到兩個 adapter」「runtime close 順序」「`initialize()` 失敗必關 adapter」；P2-3 的 `TableDisplayNameGuardTest` 對 198 個 `addTable` 名稱檢查 idempotence；P2-1 的 `_on_ok` 呼叫順序與訊息框 parent。
- **KNOWN BUG／QUIRK pins**：34 處（P1 階段 17 → 34），每處標 spec 與編號：P1-3（5）、P1-4（11）、P2-2 Q1–Q8（11，其中 Q1、Q3 標 data loss）、P2-3 K1／K2／K4（4）、P2-4（2）。修復任務可用 `grep -rn "KNOWN BUG\|KNOWN QUIRK" client/tests` 找到全部要翻轉的斷言。
- **隔離與時間**：20 個 seed 全綠（P2-5 除外）、無 sleep、無 timing 斷言新增；全套件 2.5 s；套件不再寫 `client/log/*`、不建 `config.json`／`workspace/`、不碰 `client/dictionary/`（快照相同）。
- **缺口**：Windows-only 三個模組（I-1）；`test_translation_result.py` 0 個測試（M-4）；`test_gui_document_flows.py` 體積（M-2）；absence guards（M-3）。

## P2-5 readiness 與失敗測試分析

### 失敗測試：`tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math`

- **預期 vs 實際**：輸入 `"計算 $1+2$ 的值"`，預期 `result.raw == ["計算 ", "1+2", " 的值"]`、braille `"T[計算 ]M[1+2]T[ 的值]"`；實際 `raw == ["計算 ", "1+2", " ", "的值"]`、braille `"T[計算 ]M[1+2]T[ ]T[的值]"`。`"".join(raw)` 兩者都是 `"計算 1+2 的值"`——**沒有重複插入空白**，測試名稱所指的行為其實成立；差的是 math 之後那段文字被切成兩次 `text_translator.translate()` 呼叫（`" "` 與 `"的值"`），fake translator 每次呼叫產生一個 raw token，所以 raw 多了一個元素。
- **引入點**（bisect，good `fd3aa74`＝測試誕生、`0586171` 仍通過）：**`6e5819f` `feat: align language detection with configured language`（2026-07-24）**，即 `storage/refactor.md` 的重構基線本身；P0–P2 沒有任何 commit 碰到它。機制：該 commit 在 `languageDetection/__init__.py` `add_detected_language_commands` 加入 `leading`／`leadingPrefix` 處理——文字段開頭的「不參與偵測的字元」（`isspace()`、braille cells U+2800–U+28FF、`BLOCKS[block] is None` 的區塊）先緩衝，等遇到第一個可偵測字元決定語言、送出 `LangChangeCommand` 後，**把前綴當成獨立字串 yield**（`:222-224`、`:300-304`），接著才 yield 其餘文字。`conversion/text/pipeline.py:79-95` 對每個字串 item 各呼叫一次 `translate()`，於是 `" 的值"` → 兩個 `TranslationResult`。probe 確認：`" 的值"`、`"  中文"` 在 `0586171` 為一個 token，在 `6e5819f` 起為兩個；`"hello 世界 ok"`、`"中文 english 中文"` 前後相同（語言切換處本來就會插入／拆出空白 token）。
- **哪一個對點字使用者才正確**：
  1. 在**真 `LiblouisTextTranslator`**（`adapters/translation/liblouis.py`）下，非 `single_token` 的結果 raw 是 `list(text)` 字元級再 `bind_contracted_tokens()`（只合併共享同一 braille 起點的字元），所以 `" 的值"` 一次翻譯的 raw 本來就是 `[" ", "的", "值"]`——**空白在真 adapter 下原本就是獨立 token**。因此 wrap（`translate.py:446` 對 `token == " "` 的行首略過與 `reclean_braille_endspace`）在 Windows 真實輸出上**前後應相同**；差異只存在於 fake translator 的「一次呼叫＝一個 token」模型。這一點需要 Windows 驗證（同一輸入在舊／新 LanguageDetector 下的 cells 與 BRL bytes 是否 byte-identical；liblouis 對單獨 `" "` 與帶上下文的空白理論上都給一個 blank cell，但 zh-tw.ctb 的 context 規則要實測）。
  2. 真正的可觀察差異在 **dual view**：`translate_with_language_dual_view_segments` 把每個 `translate()` 結果各建一個 `DualViewSegment`（`service.py:62-66`），所以 math 之後會多出一個只含空白的 text segment → `build_dual_view_model` 多一個 `AlignmentSegment`（item 層級的 `is_space` card 相同，`dual_view/html.py:11-15` 以 `&nbsp;` 渲染）。對使用者是「多一個 segment 容器」，不是文字或點字內容差異；也需在 Windows 的 Dual View 視窗確認視覺上是否有差。
  3. 從 wrap 的角度，「空白是獨立 token」反而較佳：行寬剛好容不下 `空白+的值` 時，獨立的空白 token 可留在行尾（被 `reclean`／padding 吃掉）而 `的值` 從下一行開頭開始；若 `" 的值"` 是單一 token，整個 token 會換到下一行，讓該行以一個 blank cell 開頭。所以**不建議**把 `LanguageDetector` 改回「前綴併入第一段文字」。
  4. 結論：這個測試釘住的是 fake 下的呼叫粒度，不是使用者行為。P2-5 的裁決建議：把斷言改為 `"".join(result.raw) == "計算 1+2 的值"` + braille 以 `"".join(...)` 去掉 fake 的 `T[...]` 邊界（或改用字元級 fake 以貼近真 adapter），並新增一條明確的 characterization：「文字段開頭的空白會成為獨立的 raw token 與 dual-view segment」。若產品方認為 dual view 不該多一個空白 segment，正確的修法是在 `translate_with_language_dual_view_segments` 把連續的 text 結果合併為一個 segment（`TranslationResult.concat`），而不是改 `LanguageDetector`。
- **此測試非 P2 的 regression**，與 `storage/refactor.md` §6.0 的基線描述一致。

### P2-5 readiness

- **已就緒的部分**：`translate.py` 的 `TranslationResult` 已是 class-attribute 常數 + `concat`（P1-5），`conversion/` 不再 import `dual_view`／`documents`（guard），`DualViewSegment` 在 `conversion/output.py`，golden fixture（360 segments + 5 輸入 × 4 寬度 × 2 模式）sha 鎖定，`test_translation_result_core` 21 個測試綠，`service.py` 的三個 alias（M-8）仍可供 monkeypatch。
- **開工前必須完成**：
  1. **I-1 的 Windows session**（含 P2-5 專用基線：同一份中／英／日／數學混排長文件的 BRL bytes、`" 的值"` 一次 vs 兩次翻譯的 cells、`reclean_braille_endspace` 在真 `zh-tw.ctb` 輸出上的 trim 次數——決定 P1-5 defect 3 的優先序）。
  2. **M-4**：`tests/test_translation_result.py` 轉 `unittest` 並裁決 5 個失敗（兩個 `IndexError` 在 `bind_word_tokens` 的 lead-punct 案例可能是真缺陷）。
  3. **裁決本節的失敗測試**（上述建議），讓 P2-5 的 step 1 從全綠基線開始。
  4. 決定 M-1（`contracts.py` 歸屬），因為 P2-5 的新模組 `conversion/tokenize.py`／`line_wrap.py`／`alignment.py` 會再 import 它。
- **建議的 P2-5 範圍修正**：roadmap 的驗證指令引用 `tests.test_translation_result`（目前 0 個測試）與 `tests.test_translation_language_result`（Windows-only），Linux 上實際只有 `test_translation_result_core` + `test_conversion_service` + `test_translation_golden`；spec 應明寫。

## 既有缺陷清單（P0–P2 發現、尚未修復；建議獨立 fix task，依使用者影響排序）

| 優先 | 缺陷 | 來源 | 影響 | 釘住的測試 | 建議修法 |
| --- | --- | --- | --- | --- | --- |
| 1（資料遺失，Windows／macOS） | 大小寫-only 的 Rename（`Alpha`→`alpha`）在 case-insensitive FS 上 unlink 掉同一個檔；文件下次啟動消失 | P1-3 defect 1 | 高 | `test_case_only_rename_on_case_insensitive_file_system_deletes_package`（Linux skip） | 重複檢查改 `casefold()`；新舊路徑 `samefile` 時不 unlink（或 `os.replace`） |
| 1（資料遺失，Windows／macOS） | Add 只差大小寫的名稱覆寫另一份文件的包 | P1-3 defect 2 | 高 | `test_add_case_variant_on_case_insensitive_file_system_overwrites_package` | 同上（Import 已是 casefold） |
| 1（資料遺失） | 帶 UTF-8 BOM 的字典 CSV（Excel「CSV UTF-8」、記事本）在編輯器開啟為空，OK 後以只有 header 的檔覆寫；轉換側同一份檔被拒 `CSV must contain columns` | P2-2 Q1 + P1-6 defect 1 | 高：使用者一按 OK 字典全失 | `test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header`；P1-6 的 BOM header 測試 | `load_dictionary_entries`、`DictionaryRulesLoader.from_paths`、`validate_dictionary_csv` 一律 `utf-8-sig` |
| 1（資料遺失） | 字典編輯器 OK 先 truncate 再寫；中途失敗（例如 lone surrogate 的 `UnicodeEncodeError`）留下被截斷的檔，且非 `OSError` 逃出 handler | P2-2 Q3／Q7 | 中高 | `test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file` | temp file + `os.replace`；handler 捕 `Exception` 顯示訊息 |
| 2（資料不一致） | Rename 時 unlink 舊包失敗 → 磁碟兩份、記憶體一份 | P1-3 defect 3 | 中 | `test_rename_unlink_failure_leaves_both_packages_and_state`、service 版 | unlink 失敗回滾或 rename-then-write |
| 2 | Delete All 回滾後無有效文件：editors 清空但 title 不更新、不建 default | P1-3 defect 4 | 中低 | `test_delete_all_failure_without_valid_document_clears_editors_only` | 回滾分支呼叫 `_update_window_title()` + `_ensure_open_document_exists()` |
| 2 | 字典編輯器 OK 永遠重寫檔案，靜默丟掉 loader 略過的列（空 text、無效注音）與被 strip 的空白 | P2-2 Q2 | 中：使用者沒改也會改到檔 | `test_unchanged_dictionary_is_rewritten_in_normalized_form` | 只在有變更時寫；或保留原始列 |
| 3（結果寫錯文件、無提示） | 轉換中 Ctrl+Tab／Ctrl+Shift+Tab／Ctrl+O 仍可切換文件，結果寫入完成當下開啟的文件 | P1-4 defect 1 | 中高 | `ConversionExportFlowsCharacterizationTest` case 17 | busy 期間在 `on_char_hook` 擋掉，或 presenter 記住啟動時的 open name |
| 3 | `convert_for_export` 不檢查 running：Ctrl+S／Export All gap 內的 Convert 啟動第二個 job，第一個結果靜默丟棄 | P1-4 defect 2 | 中 | cases 16、18；`test_conversion_presenter` 一處 | presenter queue 或 running 時 `show_info`；Export All 期間維持 busy |
| 3 | pending 文件匯出 HTML 用舊快取（export 轉換的 `dual_view_segments` 被丟掉） | P1-4 defect 3 | 中 | 無 | `convert_for_export` 的 on_success 帶 `dual_view_segments` |
| 3 | 字典編輯器：Add／Edit 遇到重複來源文字時丟掉使用者剛輸入的內容（不重開對話框）；Delete 無確認、Cancel 不問 | P2-2 Q6／Q5 | 中 | Add／Edit duplicate 測試、`test_delete_has_no_confirmation_...` | 重複時重開 `AddSymbolDialog` 帶回原值；Delete／Cancel 加確認（UX 決策） |
| 3 | 字典編輯器載入失敗（壞 UTF-8）時例外逃出建構子，native dialog 已建立卻不銷毀 | P2-2 Q8 | 中低 | `test_invalid_utf8_raises_from_the_constructor_after_the_native_dialog` | `gui.on_open_dictionary_management` 捕 `UnicodeDecodeError/OSError/csv.Error` 顯示訊息；或先讀檔再建 dialog |
| 4（本地化） | Export All 摘要、`get_public_error_message` 兩個 fallback、`"HTML"`／`"HTML files (*.html)|*.html"`、匯出 HTML 的 "No conversion data"、`"Close"` 空翻譯、匯入 file-issue reason 的英文名稱訊息（`CON.txt: Name contains invalid characters.`）、presenter add/rename 的未翻譯 `str(exc)` | P1-4 defect 4、P1-2 out of scope、P2-1 quirks 1–3 | 中：zh_TW 使用者看到英文 | 3 處 `KNOWN BUG (defect 4)`；P0-6 兩處 | 一個 localization 任務：`export_results.py` 改 `N_()`、importer 以 `NameValidationError.code` 對應翻譯、補 `.po`、`generate-pot.bat` 重跑 |
| 4 | 字典名稱 reserved 訊息永遠顯示 `default`，不論使用者輸入的大小寫 | P2-1 quirk 4 | 低 | oracle 測試 | 訊息改用 `normalized` |
| 4 | 設定面板：越界／無選取時儲存第一個選項而非 config 預設（K1）；未知表格檔名靜默選 index 0 並在 Apply 時寫回（K2）；表格值載入時不正規化（K3）；prefix 以 `startswith` 比對（K4） | P2-3 K1–K4 | 低（K2 在表格被移除／改名時會悄悄換表） | 4 處 `KNOWN QUIRK (P2-3 ...)` | 載入時正規化；未知值保留原值並顯示警告 |
| 4 | Ctrl+wheel 在 8／48 邊界仍寫檔並同步；View panel 有未套用的字型大小編輯時，wheel 變更從對話框角度遺失 | P2-4 quirk 1／2 | 低 | 2 處 `KNOWN QUIRK (P2-4 ...)` | 不變則不寫；dirty 時只更新 snapshot 不動 spin（UX 決策） |
| 5（穩健性） | `Bopomofo2Braille.csv` 壞掉只在「字典存在且有 plain text」時才報；`processing` 例外被吞 | P1-6 defect 2 | 低 | 有 | 啟動或 Settings 驗證一次 data 檔 |
| 5 | worker 拋非 `ConversionStageError` 例外（`BaseException`）→ 不投遞、UI 永遠 busy | P1-4 defect 6 | 低 | `test_conversion_jobs` 一處 | runner 把所有 `BaseException` 包成 failure 投遞 |
| 5 | Export All 中 writer 拋 `ValueError` 中斷鏈且無摘要 | P1-4 defect 7 | 極低 | `test_export_coordinator` 一處 | `_export_next` 捕 `ValueError` |
| 5 | 關閉／退出與轉換 worker 的 race：不可 veto 的關閉後 presenter 仍回呼已銷毀 frame、2 s timer 可能建 dialog；`OnExit` 的 `runtime.close()`（現在含 `MathCATAdapter.close()`）在 worker 進行中會讓該段以 `MathConversionError`／liblouis 錯誤結束 | P1 M-10、P2-7 Risks、本次 M-7 | 低，Windows 才能重現 | 無 | presenter `shutdown()`（stop timer、丟棄 active job、等待或標記 worker）由 `_on_close`／`OnExit` 呼叫，再 `runtime.close()` |
| 5 | `config.json` 的 read-modify-write 無鎖：client-init worker 的 `get_or_create_client_id` 與 UI 的 save 可能互相覆蓋 | P2-6 quirk 2 | 低（啟動後幾秒內） | 無（timing） | client id 改在 UI thread 啟動前讀／建，或 store 加 lock |
| 5 | `louis_helper._resolveTable` 的 `log.exception()` 無訊息在 stdlib logger 下 `TypeError`（只在表格解析失敗時） | P2-7 follow-up | 低 | 無 | `_adapt_helper` 補訊息字串 |
| 5 | `sync-nvda.py` 全跑會還原手改的 `vendor/nvda/liblouis/build/sconscript`（`9aa8355`、`1bd19d7`） | P2-7 Key Finding | 中（流程）：AGENTS.md 要求重建前先 sync | `test_vendor_helper_snapshot` 只守 helper | 把 sconscript 的手改搬進 `_adapt_sconscript`，或文件化不再 sync 該檔 |
| 6（效能） | `reclean_braille_endspace` 對 trim 次數二次方（10k trims 3.8 s、40k 62 s，fake 量測） | P1-5 defect 3 | 視真實 trim 次數 | golden fixture | P2-5 或獨立任務；先在 Windows 量 |
| 6 | `LanguageDetector` 每個 text segment 建一次；preprocessing script 每次轉換編譯一次 | P1-6 defect 3 | 低 | — | 隨 P2-5／pipeline 整理 |
| 6 | `get_settings_snapshot()` 每次建 snapshot 都重新列字典目錄 | P0 M-8 | 低 | — | snapshot 建構移出 I/O |
| 7（測試） | `test_translation_result.py` pytest-style 不執行、5 個失敗；P2-5 既有失敗（本節已分析）；`test_gui_document_flows.py` 4028 行、`BrailleAppLifecycleTest` 重複執行、`Mock()` 無 spec；absence guards | M-2／M-3／M-4 | 安全網缺口 | — | P2-5 step 1 與測試衛生任務 |
| 7（文件） | `AGENTS.md`／`readme.md` 的 `generate_pot.bat`；`.pot` 四個 orphan；`refactor.md` 行號；`__tables.py` localedir 指向不存在的 `client/braille/locales`（P0 M-5，P2-3 D6 證明無可見影響，記 won't-fix） | P0 M-5／M-6 | 低 | `TableDisplayNameGuardTest` | docs commit + Windows `generate-pot.bat` |

## Windows 驗證總清單（P0–P2 全部待辦；建議一次 session 依序執行，結果附回本記錄）

**前置**
1. `python -c "import wx; print(wx.version(), hasattr(wx, 'PyDeadObjectError'))"`（P2-1 D1；預期 `4.2.5 … False`）。
2. `scripts\install.bat`（或 `clean-rebuild-dotexpress.bat`），然後 `fc /b client\braille\louis_helper.py vendor\nvda\liblouis\runtime\louis_helper.py`（P2-7；**不要**跑 `py scripts\sync-nvda.py`，會還原 `build/sconscript`）。
3. 記錄 `client\braille\liblouis\__init__.py` 與 `louis_helper.py` 的 sha256（P2-7 AC7）。

**自動測試（source checkout，`cd client`）**
4. `python -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation -v`（P1 I-1 修正後首次在 Windows 執行；`test_table_resolver_finds_bundled_table`、`test_chinese_default_table_translates` 走新的 `get_table_directory`）。
5. `python -m unittest tests.test_translation_runtime_provider tests.test_mathcat_adapter tests.test_braille_glue -v`（P2-7 roadmap 指令＋adapter／glue）。
6. `python -m unittest discover -s tests -p "test_*.py"`：附回 `Ran/failures/skipped`（預期 skipped 由 9 降為 0 或 2：7 個 liblouis skip 消失，case-insensitive 的 P1-3 cases 30／32 會執行並釘住 defect 1／2）。
7. P2-5 基線：同一份中／英／日／數學混排長文件在 packaged build 的 Braille Result 與 BRL bytes（sha256）；`" 的值"`／`"  中文"` 以真 liblouis 一次翻譯 vs 兩次翻譯（`" "` + `"的值"`）的 cells 是否相同；`reclean_braille_endspace` 對真 `zh-tw.ctb` 輸出的 trim 次數（決定 P1-5 defect 3）。

**本地化**
8. `scripts\generate-pot.bat` + `msgmerge`：msgid 集合不變（353）、四個 orphan 變 `#~`、參照移到 `settings/options.py`；重編 `.mo`；順手修 `AGENTS.md`／`readme.md` 的檔名（P0-5／P1-2／P2-3）。

**Packaged build（`scripts\build-dotexpress.bat`，zh_TW，NVDA）**
9. 路徑（P2-6）：從可寫資料夾執行，`config.json`、`dictionary\`、`workspace\`、`log\`、`dual_view\` 出現在 exe 旁；設定／選取字典／文件重啟後保留；Dual View 開啟且退出時 HTML 被清；client init 有回報（server log 或 `log\init.log`）。從唯讀資料夾（`Program Files` 無提權）執行：同一個本地化啟動錯誤含失敗路徑、runtime 未啟動。`python gui.py` 從 `client\` 與其他工作目錄執行：同一個 root。
10. 對話框（P2-1）：開關 inventory 中每個對話框；Add／Rename Dictionary 與 Add／Rename Document 以空、33 字元、`CON`、（字典）`Default` 輸入顯示相同 zh_TW 訊息且對話框保持開啟；Settings 與 Text Processing 各開兩次 → 提升既有視窗，關閉再開；長轉換時 converting dialog 出現且 Alt+F4 無法關閉。
11. 字典編輯器（P2-2）：Dictionary Management → Edit 開啟後第 1 列被選取並朗讀；filter 輸入保留選取；Add 不匹配項目清 filter 並選取它；Edit、Enter、Delete（同 index 的列被選取）；重複訊息；OK 儲存、Cancel 丟棄；filter 的貼上／剪下／復原更新列表（D3）；對未變更字典按 OK 的 CSV 與 `main` byte-compare；確認真 virtual list 的 `SetItemCount` 對選取列的影響（空結果分支）。
12. 設定面板（P2-3）：三個面板的截圖與朗讀選項清單與 `main` 比對（標籤、順序、初始選取）；切換 Scheme／Braille Font 看 editor 顏色與 SimBraille；en/zh/ja 留 "未選擇" 後 Apply；空的 Default 列顯示驗證訊息並聚焦；source run 與 packaged 的表格名稱排序相同（D6）。
13. 字型同步（P2-4）：Settings > View 開著 Ctrl+wheel → spin 跟著；在 spin 打字後 Ctrl+wheel → spin 保持；Apply 後再 wheel → 跟著；在 Translation 分類 wheel 再切到 View → 新值；以 OK／Cancel／close box／Esc 關閉後 wheel 無錯；wheel 時焦點留在 editor；觀察 `wx.SpinCtrl.SetValue` 是否發 `EVT_TEXT`。
14. 轉換與退出（P2-7、P1-1、P1-5、P1-6）：source run console 不再有時間戳 `INFO` 行；packaged 轉換同一份文件的 BRL 與 `main` 建的包 byte-identical；`log\translation.log` 無新 fallback 警告、`log\math.log` 無新錯誤；math 轉換進行中退出不崩潰；`TEXT2BRAILLE_LANG` unset／`=en` 的輸出比對（P1-1）；真實使用者字典（含 Bopomofo、`@` 分段）輸出 byte-identical（P1-6）。
15. 選單與匯出（P1-2／P1-4）：四張選單截圖；Export／Export All 的對話框與輸出檔；packaged-build 手動流程。
16. P0-6 criterion 8（字典管理流程）、P0-5 criterion 10。

## Final assessment

**Ready: Yes.** P2 六個任務的 production 變更經逐流程比對無 regression，acceptance 指令全數通過，20 個 shuffle seed 與 app-data 快照乾淨，分層目標（`gui.py` 只剩 wx 組裝與 view 實作、`conversion ⇄ documents` 雙向消除、config／paths 單一 composition root、braille 膠水不再碰 root logger、MathCAT 由 runtime 擁有）達成，且沒有引入 refactor.md §7 反對的抽象。唯一的 Important（I-1）是跨三個階段累積的 Windows 驗證債，加上 P2-7 的產生檔只有 Windows 能刷新；它不要求回頭改 P2 的程式碼，但必須在 P2-5 開工前完成，並順手為 P2-5 蒐集真 liblouis 基線。P2-5 的既有失敗測試已定位到重構基線 `6e5819f` 的 `LanguageDetector` 前綴處理，且在真 adapter 下很可能不是使用者可見差異；建議以「斷言 join 後的 raw／braille + 新增前綴 token 的 characterization」裁決，而不是改回 `LanguageDetector`。Minor 項目併入 P2-5 前的測試衛生任務與既有缺陷修復任務即可。
