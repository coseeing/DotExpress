# Refactor Phase P0 — Review Record

## Review scope

審查範圍為 main 上 `6e5819f..b2f7f62` 全部提交（六個任務 P0-1 至 P0-6，各以 `merge: ... (P0-N)` 合併），對照：

- `storage/refactor.md` §6.1（roadmap 來源）與 §3–5（細節發現）
- `docs/superpowers/specs/2026-10-08-p0-{1..6}-*-design.md`（含 zh-TW 版）
- `docs/superpowers/plans/2026-10-08-p0-{1..6}-*.md`

Orchestrator 已記錄的決策（P0-1 保留 `language_detection` 注入；P0-5 排除 NVDA 衍生的 `braille/tables/__tables.py`）視為既定前提，不重新爭論。

審查方式：逐檔閱讀 production diff（`config.py`、`i18n.py`、`gui.py`、`dialog.py`、`dictionaries/presenter.py`、`documents/*`、`conversion/text/*`、`languageDetection/__init__.py`、`ui/*`、`about.py`、`dictionaries/entries.py`、`settings/dialogs.py`、`scripts/generate-pot.bat`），對照 `6e5819f` 的舊版字典回呼逐步追 call path；閱讀 `tests/wx_stub.py` 與六個新增／改寫的測試模組；以 venv 執行全套件、每個 spec 的 verification command、七個 wx 測試模組單獨執行、seeded shuffle（全套件 12 seeds；GUI/i18n/presenter 10 模組 30 seeds）；以 AST 比對 `6e5819f` 與 `b2f7f62` 的 `_()`/`N_()` msgid 集合。本機為 Linux，無 wxPython、無 liblouis DLL、無 xgettext/msgfmt，Windows-only 行為只能讀碼。

## Result

**Verdict: Needs fixes（一項 Important，皆為測試層；production 行為未發現 regression）。**

- Critical：0
- Important：1（I-1，順序相依的測試失敗，`wx_stub.StubScope` eviction 與 `test_dictionary_presenter` 的 import 形式互動）
- Minor：9

六個任務的 acceptance criteria 皆以實際指令驗證通過（見 Verification）。使用者可見行為（字典管理訊息文字、順序、parent window、flag、存檔、匯入／匯出選單、設定套用、frozen 模式 catalog 載入）經逐行比對舊碼未發現改變；msgid 集合前後完全相同（357 個，等於 `.pot`），`client/locales/` 無 diff。

## Verification（實際執行結果）

venv：`/tmp/.../scratchpad/venv/bin/python`（Python 3.14），皆於 `client/` 執行。

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| 全套件 | `python -m unittest discover -s tests -p "test_*.py"` | `Ran 550`, `FAILED (failures=1, skipped=7)`；唯一失敗為已知 P2-5 `test_conversion_service.test_translate_with_language_does_not_duplicate_existing_spaces_around_math` |
| P0-1 | `tests.test_config tests.test_translation_settings tests.test_view_settings tests.test_translation_tables tests.test_log tests.test_app_paths` | `Ran 40`, OK |
| P0-2 | `tests.test_gui_document_flows tests.test_settings_dialogs tests.test_settings_state tests.test_translation_tables tests.test_conversion_jobs` | `Ran 102`, OK |
| P0-3 | spec criterion 2 的 12 個模組 | `Ran 139`, OK（spec 寫 132，是 P0-4/P0-6 之後新增的 gui 測試所致，非問題） |
| P0-4 roadmap | `tests.test_gui_document_flows tests.test_settings_dialogs tests.test_speech_symbols_dialog tests.test_dictionary_management_dialog` | `Ran 142`, OK |
| P0-4 order pairs | `gui_document_flows+dialog_validation`、`gui_document_flows+settings_dialogs+dual_view_frame`、`gui_document_flows+dual_view_frame` | 三組皆 OK（phase 前這三組會失敗） |
| P0-4 per-module | 七個 wx 模組 + `test_wx_stub` 各自單獨執行 | 全部 OK |
| P0-5 | `tests.test_i18n`（16）；roadmap `tests.test_dialog_validation tests.test_dialog_display`；criterion 6 兩種順序 | 全部 OK |
| P0-6 | spec criterion 6 的 7 個模組 | `Ran 164`, OK（43 + 26 + 11 + 6 + 6 + 4 + 68，與 spec 一致） |
| 全套件 shuffle | 自寫 harness，模擬 `discover`（import-time `SkipTest` 計為 skip），seeds 1–12 | 每個 seed `ran=550 skipped=7`；seeds 1,2,3,5,10,12 只有 P2-5 失敗；seeds 4,6,7,8,9,11 另有 `test_conversion_service` 8 個 errors（`test_translation_result_core` 先於它時 `translate` 被 pop 重 import；P0-4 spec 已記錄為 out of scope，phase 前即存在） |
| GUI 10 模組 shuffle | 同 harness，seeds 1–30，模組：七個 wx 模組 + `test_wx_stub` + `test_i18n` + `test_dictionary_presenter` | seed 8 出現 4 個 failures（見 I-1）；其餘 29 個 seed 全綠 |
| msgid 集合 | AST 掃描 `client/**/*.py`（排除 tests/.venv），分別在 `6e5819f` 與 `b2f7f62` | 兩者皆 357 個且集合完全相同；`.pot` 有 357 個非空 msgid |
| Acceptance greps | P0-1 setters、P0-2 `language_map_translate_table`／訊息字串、P0-3 的 27 個死碼名稱與 `if False`/`prevInIgnore`、P0-5 的 gettext/`_MEIPASS`/`resource_path`、P0-6 的 `prompt_dictionary_name_until_success(`／duplicate msgid／gui 九個識別字／`dialog.list_dictionary_names` | 全部符合 spec 預期 |
| locales | `git diff 6e5819f..b2f7f62 --stat -- client/locales` | 空 |

## Findings

### Critical

無。

### Important

**I-1 順序相依的測試失敗：`StubScope` eviction 留下過期的 package attribute，`test_dictionary_presenter` 的 fault injection 打到錯的 module**

- 位置：`client/tests/wx_stub.py:243-246`（`StubScope.loading()` 的 eviction 迴圈只 `del sys.modules[name]`，不處理 parent package attribute）；`client/tests/test_dictionary_presenter.py:8`（`from dictionaries import presenter as presenter_module`）；`client/dialog.py:24`（`dialog.py` 在 speech scope 內首次 import `dictionaries.presenter`）。
- 重現：`cd client && python -m unittest tests.test_speech_symbols_dialog tests.test_dictionary_presenter` → `FAILED (failures=4)`：`test_add_does_not_catch_os_error`、`test_delete_os_error_shows_error_and_changes_nothing`、`test_export_os_error_shows_error`、`test_rename_os_error_shows_save_error`。GUI 10 模組 shuffle seed 8 亦重現。
- 機制（以 probe 驗證）：`test_speech_symbols_dialog` 在 scope 外先 import `dictionaries.entries`（`dictionaries` package 因此在 `before` 集合內，不會被 evict）；`load_speech_dialog()` 在 scope 內載入 `dialog.py`，後者首次 import `dictionaries.presenter`；離開 scope 時 `evict_speech_roots` 將 `dictionaries.presenter` 從 `sys.modules` 移除，但 `dictionaries` package 物件上的 `presenter` attribute 仍指向被移除的 module。之後 `test_dictionary_presenter` 的 `from dictionaries import presenter` 走 `_handle_fromlist`，`hasattr(dictionaries, "presenter")` 為真而**不重新 import**，拿到舊 module；下一行 `from dictionaries.presenter import DictionaryManagementPresenter` 則因 `sys.modules` 沒有該名稱而重新 import，拿到新 module。四個 OSError 測試用 `patch.object(presenter_module, "<manager fn>", side_effect=PermissionError)` 補丁舊 module，presenter class 卻讀新 module 的全域，故障注入無效。
- 為何 `discover` 目前綠：字母序下 `test_dictionary_management_dialog`（在 scope 外先 import `dictionaries.presenter`，使其成為 `before` 成員）早於 `test_dictionary_presenter` 與 `test_speech_symbols_dialog`，屬巧合。P0-4 spec Risks 已指出 "stale parent-package attributes" 是中風險，但只對 `isolate` 名單處理（`_parent_attrs`/`_restore`），未涵蓋被 `evict` 的一般 module。
- 影響：測試層；production 無影響。但 P1-2/P1-3/P1-4 會新增更多被 `dialog.py`/`gui.py` import 的純模組（`ui/menu_builder.py`、`documents/workspace_service.py`、`conversion/presenter.py` 等），曝險面會擴大。
- 建議修法（擇一或並行）：
  1. 根本修法：`StubScope.loading()` evict 時，若 `sys.modules[parent]` 的 `child` attribute `is` 被 evict 的 module，同步 `delattr`；`_restore` 對 `evict` 範圍也比照 `isolate` 處理。並在 `test_wx_stub.py` 加一個回歸測試（scope 內首次 import `pkg.sub`，離開後 `pkg` 不應再有 `sub` attribute），以及把 `tests.test_speech_symbols_dialog tests.test_dictionary_presenter` 這組加進 P0-4 式的 order check。
  2. 防禦修法：`test_dictionary_presenter.py:8` 改為 `import dictionaries.presenter as presenter_module`（`import a.b as c` 會在 `sys.modules` 缺少時重新 import 並更新 parent attribute），或以 `sys.modules[DictionaryManagementPresenter.__module__]` 取得 module。
  建議兩者都做：1 修 stub 的契約，2 讓 presenter 測試不依賴 stub 行為。

### Minor

**M-1 既有順序相依：`test_translation_result_core` → `test_conversion_service`**
- 位置：`client/tests/test_translation_result_core.py`（pop 並重 import `translate`，造成 `TranslationResult` 兩份）。
- 證據：全套件 shuffle 12 seeds 中 6 個出現 8 個 errors。P0-4 spec §"Leaks and order dependence" 已記錄為 out of scope，phase 前即存在。
- 建議：P1-5（擁有 `translate.py` / `TranslationResult` 的任務）順手修掉；在那之前不要以 shuffle 作為 CI gate。

**M-2 大量「名稱不存在」守門測試釘住實作細節，P1 會與之衝突**
- 位置：`tests/test_removed_dead_code.py`（5 個）、`tests/test_config.py::test_unused_single_view_setters_are_removed`、`tests/test_gui_document_flows.py::test_dead_frame_helpers_are_removed`、`::test_frame_dictionary_callbacks_are_removed`、`::test_dictionary_dialog_helpers_and_imports_are_removed_from_gui`（禁止 `gui` 擁有 `ensure_default_dictionary`、`list_dictionary_names` 等 16 個名稱）、`tests/test_i18n.py::SharedSetupConsumerTest`（要求每個模組從 `i18n` import 的名稱集合**完全相等**，例如 `gui` 必須恰為 `{"N_", "_", "resource_path"}`）、`tests/test_dictionary_management_dialog.py::test_constructor_takes_actions_and_selected_name`（釘住參數名列表）。
- 問題：這些測試作為 TDD red step 合理，但長期回歸價值接近零，且會對後續任務造成摩擦：P1-2 若把 `_MENU_TRANSLATION_MARKERS` 搬到 `ui/action_menu.py`，`gui` 不再 import `N_`，`SharedSetupConsumerTest` 立即失敗；P2-6 把 `ApplicationPaths` 注入 `BrailleFrame` 時若 `gui` 需要 `ensure_default_dictionary` 之類名稱，守門測試會擋。
- 建議：P0 結束後整併為單一 `test_phase_p0_removals.py`（或在各任務合併後刪除對應 guard），`SharedSetupConsumerTest` 改成「不得定義自己的 catalog／resource_path」的負向斷言即可，不必釘 import 集合。

**M-3 P0-3 漏掉的死 import（phase 前即存在，不在 §5.4 清單）**
- `client/gui.py:20` `ConversionStageError`、`client/gui.py:36` `export_document_brl`、`client/documents/workspace.py:11` `MAX_NAME_LENGTH`：以 AST 掃描皆無使用者（`ui/import_dialog.py:5` 的 `ALL_SUPPORTED_FILTER_INDEX` 是刻意 re-export，不算）。
- 建議：P1-2（`gui.py` export 區）與 P1-3（`documents/workspace.py`）動到該檔時一併移除；不值得單獨開 PR。

**M-4 `_MENU_TRANSLATION_MARKERS` 仍是 48 行 hack，`N_` 只是把它合法化**
- `client/gui.py:128-176`。P0-5 spec 明確把搬遷留給 O-1/P1-2。可接受，但 P1-2 應以「label 定義處直接 `N_()`、刪除 tuple」為驗收項，否則 `N_` 的引入只是換湯。

**M-5 `braille/tables/__tables.py` 的 localedir 指向不存在的 `client/braille/locales`（已記錄、刻意不修）**
- P0-5 spec "Known issues" 已完整描述：source run 下 196 個 output table 的排序與 packaged app 不同（英文序 vs 中文序）。只影響開發者從 source 執行時 settings 對話框的表格順序，packaged 不受影響。
- 建議：排進 P1-1（已擁有 `braille/tables` 去 `config` 相依）一起處理，並在該 spec 聲明 source-run 排序會改變。

**M-6 文件名稱不一致：`generate_pot.bat` vs 實際 `scripts/generate-pot.bat`**
- `AGENTS.md:16`、`readme.md:175`。P0-5 已列為 follow-up，仍未處理。建議一個 docs-only commit。

**M-7 `DictionaryManagementActions` Protocol 與 `DictionaryManagementPresenter` 公開介面重複**
- `client/dictionaries/presenter.py:46-62` vs `:65-`。新增一個 action 要改兩處，且沒有靜態檢查保證兩者一致（只有 `test_presenter_provides_every_action` 以 `hasattr` 比對名稱）。這是刻意的（讓 `dialog.py` 依賴 wx-free 的型別、測試可用 `_FakeActions`），與 refactor.md §7.4「純 Python presenter + callable 回呼」一致，故只記錄。若日後 Protocol 增長，可考慮直接讓 dialog 型別標注為 `DictionaryManagementPresenter`。

**M-8 `get_settings_snapshot()` 每次建立 snapshot 都重新列目錄**
- `client/gui.py:545-553` → `get_dictionary_names_for_dialog()` → `presenter.refresh()`。行為與 phase 前相同（舊碼也 refresh），但現在 refresh 已集中在 presenter，P2-3/P2-6 整理 settings 時可把 I/O 移出 snapshot 建構。

**M-9 `BrailleFrame._show_file_error` 的 `parent` 參數已無人傳入**
- `client/gui.py:582`。P0-6 spec 已記錄為刻意保留。P1-4（`ExportCoordinator`）重整 `_show_file_error` 呼叫者時一併移除。

（不確定、未列入計數）`client/i18n.py` 使用頂層模組名 `i18n`；PyPI 的 `python-i18n` 套件也提供頂層 `i18n`。因 `client/` 在 `sys.path` 最前且 PyInstaller 從 script 目錄解析，實務上不會撞名，但若 build venv 裝了該套件而有人改變 `sys.path` 順序就可能靜默載錯。P0-5 spec 已以 `find_spec` 檢查 venv。僅提醒，不要求修改。

## 正確性追蹤（對照 `6e5819f`）

### P0-6 字典管理流程（重點區域）

逐步比對 `gui.py@6e5819f:1287-1491` 與 `dictionaries/presenter.py` + `dialog.py` 的 view 方法：

- **Add / Import**：name loop（`prompt_dictionary_name_until_success`）、duplicate 錯誤框文字（`.strip()` 後的 name）、`ValueError` → Info 框 `str(exc)`、Import 的所有 `ValueError` → header 訊息、`OSError` → `Failed to import dictionary: {error}`、Add 不捕 `OSError`，皆一致。成功後 `refresh(active)` + `plan_dictionary_state_after_add` 一致。
- **Delete**：`is_default_dictionary` → Info 框；confirm 的 caption/flag（`YES_NO | NO_DEFAULT | ICON_WARNING`）與 `== wx.YES` 判斷一致；`previous_names` 改讀 presenter 的 list，與舊 frame cached list 的刷新時點相同（開啟時、每次成功動作後、`get_dictionary_names_for_dialog`）；`OSError` → `Failed to delete dictionary: {error}` 且不刷新、不改 active；`_set_active_dictionary` 只在 planned active 改變時呼叫，一致。
- **Rename**：default 靜默 `None`；`ValueError` → Info；`OSError` → `Failed to save dictionary: {error}`；成功後 `refresh(path.stem)`；舊碼在 plan 前多做一次 `get_dictionary_names_for_dialog()`（同目錄再列一次），新碼省略，中間無任何寫入，不可觀察。
- **Export**：空 list 直接返回；`FileDialog` 的 `defaultFile`、wildcard、`FD_SAVE | FD_OVERWRITE_PROMPT`；`OSError` → `Failed to export dictionary: {error}`；永不刷新，一致。
- **Parent window**：舊碼 `dialog_parent = parent or self`，dialog 永遠傳 `self`；新碼 view 方法固定 `parent=self`（dialog）。一致。
- **Open / Edit**：`refresh(active)` → `DictionaryManagementDialog(self, presenter, selected)`；`wx.ID_EDIT` + name → `SpeechSymbolsDialog(self, dictionary_path=presenter.dictionary_path(name))`。一致。
- **`_initialize_state`**：舊碼 `ensure_default` → list → `load_translation_settings(names)` → 第二次 refresh（結果未用）；新碼 `presenter.refresh()` → `load_translation_settings(presenter.dictionary_names)`。`load_translation_settings` 只用 names 做 `resolve_dictionary_selection`，不保存引用，故舊碼 `self._dictionary_names[:] =` 的 in-place 刷新沒有被依賴。一致。
- `get_active_name` lambda 延遲讀 `self.translation_settings`，`apply_settings_from_dialog` 重新指派後仍正確。

### P0-2 翻譯表

`self.translation_tables` 在 `_initialize_state` 設定；所有讀取點（`get_settings_snapshot`、`apply_settings_from_dialog`、`_build_conversion_request`、`_missing_default_table_message`）皆在 `__init__` 後；replace-only，無 `clear()/update()`。時序差異（import 時 → frame 建構時）在 `BrailleApp.OnInit` 內 `prepare_application_directories` 之後，兩點間無人寫 tables。`on_convert` 與 `_start_export_conversion` 的訊息、caption、flag、callback 順序（`on_missing_table` 先於 `on_error`）未變。

### P0-1 config

`_load_from_file` 的 throttle 以 path+signature 為 key，成功讀取或 `FileNotFoundError` 清除；`_save_to_file` 每次記錄。`_log_current_exception` 捕 `OSError` 處理 `delay=True` `FileHandler` 在 `log/` 不存在時 `emit()` 外的 `_open()` 拋錯（已核對 CPython `FileHandler.emit` 流程，`_open()` 確實在 `StreamHandler.emit` 的 try 之外）。`log` → `app_paths` 無循環。兩個 I/O helper 仍不拋錯。`language_detection` 注入保留。

### P0-3 死碼

27 個名稱 grep 僅剩守門測試；`prepare_document_for_save` 唯一 production 呼叫者 `gui.py:804` 已改為單值接收，並有 `test_save_open_document_saves_prepared_document` 保護；`languageDetection` 刪除的 `if False` 分支與 `prevInIgnore` 確實無其他讀者。`getDefaultTableForCurLang`、`get_exportable_formats`、`translate__mapping_char` 依 spec 保留。

### P0-5 i18n

`resource_path` 的 frozen 判斷（`sys.frozen and hasattr(sys, "_MEIPASS")`）與三個原始站點逐字相同；`about.py`/`dictionaries/entries.py` 原本無 `_MEIPASS` 分支但 `__file__` 在 PyInstaller 下已落在 `_MEIPASS`，改用 `i18n` 後 packaged 結果相同。`_` 為 consumer 的 module global（`from i18n import _`），`test_dialog_display` 置換 `dialog_module._` 的既有做法仍有效。`i18n` 無 client 相依、無 `wx`，不觸發 `StubScope` R4。

### P0-4 wx stub

每個 factory 皆為新物件；`isolate` 名單的 `sys.modules` 與 parent attribute 都有快照／還原；R4 leak guard 有測試。缺口即 I-1：`evict` 的一般模組沒有 parent-attribute 處理。

### Windows-only／無法在本機驗證（僅讀碼）

- liblouis DLL／`WINFUNCTYPE` 路徑：本 phase 未動 `braille/`（P0-5 排除 `__tables.py`；P0-3 保留 `getDefaultTableForCurLang`）。
- PyInstaller bundle：`i18n` 由 `gui.py` 靜態 import，無需 hidden-import；`scripts/build-dotexpress.bat` 未改。P0-5 criterion 10（執行 `generate-pot.bat`，只有 `#:` 與 `POT-Creation-Date` 變動）與 P0-6 criterion 8（手動走過字典管理）均**未執行**，需 Windows 機器補做。
- P0-4 spec 提到 Windows 上 `test_liblouis_runtime.setUpClass` 可能因不再拿到 G stub 的 `louis_helper` 而由 error 轉 pass，需 Windows 上前後各跑一次 `discover` 比對。
- NTFS case-insensitive rename（`alpha` → `Alpha` 會進 duplicate loop）：行為與 phase 前相同，`test_rename_case_only_change_renames_file` 在 case-insensitive FS 上自我 skip。

## 設計品質評估

- **P0-6 presenter**：結構改善明確。五個回呼 + 三份 lambda 收斂為一個 `_prompt_name_until_success`；dialog 從 9 參數變 3 參數；字典列表只在 presenter 列目錄（dialog 的 `_dictionary_names` 只是 render snapshot，且只從 `actions.dictionary_names` 取得）。Protocol 方向正確（`dialog.py` 依賴 wx-free 的 `dictionaries.presenter`，反向不存在）。符合 refactor.md §7.4「不引入完整 MVP 框架」。presenter 使用 tab 與 `dictionaries/` 同目錄一致。
- **P0-5 i18n**：單一 catalog、單一 `resource_path`，消除 `parents[1]` 差異；`N_` 讓 marker 不再在 import 時白做翻譯。缺點見 M-4。
- **P0-4 wx stub**：以「每個 consumer 一個 factory + `StubScope`」而非合併 profile，是保守且正確的選擇（避免把 behavior change 混進 refactor）。`StubScope` 的契約（R1–R4）有測試。缺口見 I-1。
- **P0-1/P0-2/P0-3**：小而正確。P0-2 的 `_missing_default_table_message` 回傳訊息而非 table 名稱，命名比 roadmap 的 `_require_default_table` 清楚。
- **跨任務一致性**：presenter 直接 `from i18n import _`（P0-5 的 `DuplicateSetupGuardTest` 會掃到新模組）；presenter 測試不用 wx stub（純 Python），dialog 測試用 `load_speech_dialog()`，frame 測試用 `gui_frame_stubs()`——分層清楚。唯一的交互問題是 I-1。
- **不必要的抽象**：未發現。`DictionaryManagementActions` 與 presenter 的重複（M-7）是為了可測性的合理代價。

## 測試品質評估

- `test_dictionary_presenter.py`（43）：高品質。`FakeView` 記錄完整呼叫序列且用 queue 回答（多餘的 prompt 會 `IndexError`），每個測試同時斷言 view calls、回傳值、磁碟狀態、`dictionary_names`、`set_active_name`。能抓到訊息順序、parent、flag 以外的所有回歸。缺點：OSError 注入靠 `patch.object(presenter_module, ...)`，即 I-1 的受害者。
- `test_dictionary_management_dialog.py`（26）：view 方法測試逐一斷言 wx 呼叫的參數與 flag（speech stub 已加 2 的冪次常數，能抓掉 flag）。良好。
- `test_gui_document_flows.py::DictionaryManagementFrameTest`（7）：`test_initialize_state_wires_presenter_to_active_dictionary` 以真目錄 + 真 presenter 走到 `set_selected_dictionary`，是真正的整合點測試。良好。
- `test_i18n.py`（16）：行為測試（frozen 路徑、fallback、環境不影響語言）有價值；`SharedSetupConsumerTest` 與 `DuplicateSetupGuardTest` 偏向實作細節（M-2）。子程序測試約 0.1s，可接受。
- `test_config.py` 新增 11 個：失敗路徑、throttle、recovery、log 檔不可開啟時不拋錯，皆以 `assertLogs`/patched logger 避免寫入真實 `log/`。良好。
- `test_wx_stub.py`（16）：覆蓋 R1–R4 與各 factory 新鮮性。缺 evict 的 parent-attribute 案例（I-1）。
- 守門測試：見 M-2。
- 隔離：`discover` 與 12 個全套件 seed 皆無 wx 相關失敗；GUI 模組 30 個 seed 只有 I-1 一例。

## P1 建議（對 `storage/refactor.md` §6.2 的調整）

1. **P1 開工前先修 I-1**（半天內）：修 `StubScope` 的 evict parent-attribute，加回歸測試，並把 `tests.test_speech_symbols_dialog tests.test_dictionary_presenter` 加進「order pairs」驗收清單。P1-2/P1-3/P1-4 都會新增被 `dialog.py`/`gui.py` import 的純模組，不先修會反覆踩到。
2. **P1-5 納入 M-1**：`test_translation_result_core` 的 `translate` 重 import 是 P1-5 的檔案範圍，修掉後 shuffle 才能當 CI gate。
3. **P1-2 驗收加一條**：`_MENU_TRANSLATION_MARKERS` 刪除、label 定義處直接 `N_()`（`ui/action_menu.py`、`documents/formats.py` 的 wildcard label）；同時更新 `SharedSetupConsumerTest` 對 `gui` 的 import 集合（或依 M-2 放寬）。
4. **P1-1 納入 M-5**：`__tables.py` 改用 `i18n._`（或 `parents[2]`），spec 要聲明 source-run 的 table 排序會改變；之後 P2-3 才能移除 `settings/dialogs.py` 的 `_(table.displayName)`。
5. **P1-3/P1-4 的起點已改變**：`prepare_document_for_save` 現在回傳 `Document`（不再是 tuple），`batch_export_documents_to_folder` 已刪除——P1-4 的 `ExportCoordinator` 不要復活它，應基於 P1-2 的 `ExportContext` 重寫；P1-3 的 `workspace_service` 可直接建在新簽名上。
6. **守門測試退場策略（M-2）**：建議在 P1 kickoff 決定：保留 `test_removed_dead_code.py` 到 P1 結束後刪除；`SharedSetupConsumerTest` 改為負向斷言；`test_dictionary_dialog_helpers_and_imports_are_removed_from_gui` 的 import 黑名單在 P2-6 前移除。
7. **順手清理（不需獨立任務）**：M-3 的三個死 import、M-6 的 `generate_pot.bat` 文件名、M-9 的 `_show_file_error(parent=...)`，分別掛在 P1-2、docs commit、P1-4。
8. **Windows 驗證債**：P0-5 criterion 10 與 P0-6 criterion 8 尚未在 Windows 執行；P0-4 的 `test_liblouis_runtime` 前後比對也未做。建議在 P1 第一個 Windows build 時一次補齊，並把結果附回本記錄。

## Final assessment

**Ready: No（Needs fixes）。** 需修 I-1（測試隔離）後即可視為 P0 完成；production 程式碼不需要改動。其餘為 Minor，可併入 P1 相關任務。

## 修正紀錄（review 之後）

- I-1：`88d7d32` fix: restore parent package attributes after stub eviction —— `StubScope._forget()` 於 eviction 與 `_restore()` 時一併移除指向被移除模組的父套件屬性（子模組先於父模組），並保留 scope 自身 stub 之間的連線；`test_dictionary_presenter` 改用 `import dictionaries.presenter as presenter_module`。新增 4 個 `test_wx_stub` 測試。
  - 重現指令 `python -m unittest tests.test_speech_symbols_dialog tests.test_dictionary_presenter`：修正前 `FAILED (failures=4)`，修正後 `Ran 64 ... OK`。
  - 10 個 GUI/i18n/presenter 模組：90 組 ordered pairs、60 組 seeded shuffles 皆 0 bad。
- M-3：`2ad3f04` refactor: remove unused imports —— 移除 `gui.export_document_brl`、`documents/workspace.MAX_NAME_LENGTH`；`gui.ConversionStageError` 保留（`tests/test_gui_document_flows.py:455` 使用 `gui.ConversionStageError`）。
- 全套：`Ran 554`, `FAILED (failures=1, skipped=7)`（僅既有 P2-5）。
- 其餘 Minor 處置：M-1 併入 P1-5；M-4 併入 P1-2；M-2 guard 測試原則已寫入後續任務指引；M-5、M-6 及 Windows 驗證項目列入最終待辦。
