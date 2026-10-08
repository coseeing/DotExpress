# Refactor Phase P1 — Review Record

## Review scope

審查範圍為 main 上 `7f0d127..c34d31c` 全部 64 個提交（六個任務 P1-1 至 P1-6，各以 `merge: ... (P1-N)` 合併），對照：

- `storage/refactor.md` §6.2（roadmap 來源）與 §3–5（細節發現）、§7（不建議變更）
- `docs/superpowers/specs/2026-10-08-p1-{1..6}-*-design.md`（含 zh-TW 版）
- `docs/superpowers/plans/2026-10-08-p1-{1..6}-*.md`（六份皆含 "Spec Corrections and Refinements"）
- `docs/superpowers/history/2026-10-08-01-refactor-p0/review_task.md`（P0 phase review，追蹤其 I-1 修正與 M-1..M-9 的後續）

Orchestrator 已記錄的決策視為既定前提，不重新爭論：P1-2 丟棄 4 個 orphan import-filter msgid（357 → 353）；P1-3／P1-4 以 `# KNOWN BUG` 測試釘住既有缺陷而不修；P1-6 字典規則採 lazy、每次轉換載入一次。

審查方式：

1. 逐檔閱讀 production diff（`git diff 7f0d127..c34d31c -- client ':!client/tests'`，31 個檔案、+1231/−906）；`gui.py` 以 `7f0d127` 舊版（1541 行）與 HEAD（1101 行）並排逐流程追 call path（文件 CRUD、匯出鏈、轉換狀態機、選單建構、close 流程）。
2. 閱讀六個新模組（`ui/menu_builder.py`、`documents/workspace_service.py`、`conversion/presenter.py`、`documents/export_coordinator.py`、`conversion/text/dictionary_rules.py` 新增部分、`conversion/math_braille_codes.py`）與被改動的 `conversion/{jobs,service,output}.py`、`conversion/text/pipeline.py`、`translate.py`、`dual_view/model.py`、`documents/{controller,formats}.py`、`ui/action_menu.py`、`languageDetection/__init__.py`、`conversion/mathcat_adapter.py`、`braille/tables/__init__.py`。
3. 以 venv 執行全套件、每個 spec 的 acceptance 指令（grep 與 unittest）、P0 I-1 的 order pair、P1-4／P1-5 的順序組合、全套件 seeded shuffle 20 seeds、每個測試模組單獨計時。
4. 以 AST 比對三個 characterization 測試類別在「step-1 commit」與 HEAD 之間的成員差異（P1-3／P1-4 acceptance criterion 6 的做法）；以 AST 掃描 `_()`/`N_()` msgid 集合並以正確的多行 `.pot` parser 比對。
5. 本機為 Linux，無 wxPython、無 liblouis DLL、無 MathCAT、無 xgettext/msgfmt；Windows-only 與 PyInstaller 路徑只能讀碼（見「Windows-only／無法在本機驗證」）。

## Result

**Verdict: Ready（production 行為未發現 regression；一項 Important 為測試安全網／流程問題，不阻擋 P1 完成，但應在 P2-5／P2-7 之前處理）。**

- Critical：0
- Important：1（I-1，Windows-only 測試模組 import 已壞 + 六個任務的 Windows 驗證債全數未清）
- Minor：10

六個任務的 acceptance criteria 皆以實際指令驗證通過。使用者可見行為（選單順序／標籤／enabled 狀態／bind 目標、匯出對話框與輸出 bytes、文件流程的磁碟副作用順序與錯誤訊息、轉換的非同步順序與 busy 切換、翻譯輸出與 dual view、字典錯誤時機）經逐行比對舊碼未發現改變。msgid 集合為 353，與 `.pot`（357）的差異恰為四個 orphan；`client/locales/`、`scripts/` 無 diff；P1-5 golden fixture sha256 未變。

## Verification（實際執行結果）

venv：`/tmp/.../scratchpad/venv/bin/python`（Python 3.14），皆於 `client/` 執行。

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| 全套件 | `python -m unittest discover -s tests -p "test_*.py"` | `Ran 818 tests in 1.601s`, `FAILED (failures=1, skipped=9)`；唯一失敗為已知 P2-5 `test_conversion_service...test_translate_with_language_does_not_duplicate_existing_spaces_around_math`；9 skips = 7 Windows-only liblouis + 2 case-insensitive FS（P1-3 cases 30/32） |
| 全套件 shuffle | `shuffle_harness.py <seed>`，seeds 0–19 | 20 個 seed 全部 `ran=818 failures=1 errors=0 skipped=9`，唯一 BAD 為 P2-5；P0 review M-1（`translate` 重 import 污染）已消失 |
| P1-1 | spec criterion 5 的 15 個模組 | `Ran 254`, `failures=1`（P2-5）, `skipped=2` |
| P1-1 greps | criteria 1–4 | 1、3 空；2 只列 `config.py`（定義）、`client_init.py`、`gui.py`（import + `_build_conversion_request`）、`main.py`；4（`__tables.py`／`braille/liblouis` diff）空 |
| P1-1 CRLF | `grep -c $'\r$' braille/tables/__init__.py` | 251/251 行 CRLF 保留，diff 僅 4+/4− |
| P1-2 | spec criterion 7 的 11 個模組 | `Ran 264`, `OK (skipped=2)` |
| P1-2 greps | criteria 1–4 | 全部空（`"html"`、marker 常數、label-keyed lookup、`N_` in gui、`wx` in menu_builder） |
| P1-2 msgid | AST 掃描 `client/**/*.py`（排除 tests/.venv）vs 多行 `.pot` parser | source 353、`.pot` 357；`pot − src` 恰為 `EPUB books`／`PDF files`／`Text files`／`Word documents` 四個 wildcard；`src − pot` 空 |
| P1-3 | roadmap 五模組 | `Ran 216`, `OK (skipped=2)` |
| P1-3 greps | criteria 1–7 | 全部空（無 property／setter、無直接 state 存取、無 workspace IO 名稱、無 `workspace_dir`、無 `hasattr` guard、service/controller 無 wx/gui import、`set_state` 已刪） |
| P1-4 | roadmap 四模組 | `Ran 192`, `OK (skipped=2)`；`test_gui_document_flows + presenter + coordinator` 兩種順序皆 OK |
| P1-4 greps | criteria 1–5 | 1、2、3、5 空；4 只列 `_initialize_conversion_state` 的三行（218、219、225） |
| P1-5 | roadmap 五模組 | `Ran 72`, `failures=1`（P2-5；`test_translation_result` 貢獻 0 個測試，見 M-4）；`core + service` 與 `service + core` 兩種順序皆只有 P2-5 失敗、`errors=0` |
| P1-5 greps／fixture | criteria 6–8；`sha256sum tests/fixtures/translation_golden.json` | `conversion/` 無 `dual_view` import；`dual_view/` 只剩 `model.py:7` 的 `TYPE_CHECKING` import；無 function-local `from translate import`；`translate.py` 無 `self.*_PUNCT =`；sha `e67d95a1…211ccd` 與 spec 一致 |
| P1-6 | roadmap 四模組 | `Ran 69`, `failures=1`（P2-5）；`tests.test_conversion_text_dictionary_rules` 單獨 `Ran 20 OK`（phase 前為 `NO TESTS RAN`） |
| P1-6 greps | criterion 6 | `apply_dictionary(` 在 `client/conversion` 只剩定義；`.open(` 只在 `from_paths` 內兩處 |
| P0 I-1 回歸 | `tests.test_speech_symbols_dialog tests.test_dictionary_presenter` | OK |
| 每模組計時 | 68 個模組各自單獨執行 | 最慢 `test_translation_result_core` 0.39 s、`test_gui_document_flows` 0.39 s（143 tests）；`LinearMergeTest` 三個測試合計 0.27 s（5 s 上限約 18 倍餘裕）；總和 9.6 s（含 interpreter 啟動） |
| AST 凍結檢查 | 三個 characterization class：step-1 commit vs HEAD | `ConversionExportFlowsCharacterizationTest`（`c19eae8`）：19 tests，只有 `_wire_conversion` 變動；`DocumentWorkspaceFlowsCharacterizationTest`（`75dfba5`）：32 tests，只有 `_make_workspace_frame` 與 `test_close_vetoes_when_save_fails`（P1-4 part E 已載明改為檢查 `close_converting_dialog`）變動；`DocumentMenuAndExportCharacterizationTest`（`1e26e39`）：11 → 12 tests，7 個測試只改 setup 行（P1-3 把 `frame._selected_document_name =` 改為 controller 呼叫；P1-4 把匯出入口改經 `_export_coordinator`），P1-5 新增 `test_dual_view_and_html_export_render_math_with_real_mathml` |
| locales／scripts／braille | `git diff 7f0d127..c34d31c --stat -- client/locales scripts client/braille` | 只有 `braille/tables/__init__.py`（P1-1 刻意改動） |
| KNOWN BUG 標記 | `grep -rn "KNOWN BUG" client/tests` | 17 處，每處標明 spec 與 defect 編號 |

## Findings

### Critical

無。

### Important

**I-1 Windows-only 安全網已壞、且 P0+P1 的 Windows 驗證債全數未清，而 P1-1／P1-5／P1-6 都動到只在 Windows 才真正執行的路徑**

- 位置：`client/tests/test_language_detection_translation.py:17` `from translate import translate, TranslationResult`。`client/translate.py` 沒有 `translate` 函式（只有 `TranslationResult`），所以這個模組在 Windows 上於 import 階段就 `ImportError`，在 Linux 則因第 10 行的 `SkipTest` 被跳過而看不到。P1-5 spec "Known defects" 第 2 項已記錄但未修；P1-1 只修了姊妹模組 `test_translation_language_result.py` 的 `"zh-tw.ctb"` 位置引數。
- 影響：Windows 上真正跑 liblouis 的語言偵測＋翻譯整合測試完全沒有在執行。再加上：
  - P1-1 改了 MathCAT 呼叫鏈的簽名（`get_braille_for_mathml(..., language=)`、`SetPreference("Language", …)` 由 request 的 `lang` 計算）—— 只在 Windows 載入 `libmathcat_py.pyd`。
  - P1-5 把 `TranslationResult` 的 12 個 set 與 `lang_blocks` 改為 class attribute、合併改為 `concat`—— liblouis adapter 在 Windows 才會真正產生結果。
  - P1-6 以真實使用者字典（含 `Bopomofo`、`@` 分段）驗證輸出 byte-identical 的項目也只能在 packaged build 做。
  - P0-5 criterion 10（`generate-pot.bat`）、P0-6 criterion 8、P1-2 的選單截圖與 `generate-pot.bat` + `msgmerge`、P1-3 的 case-insensitive 測試（cases 30／32 只在 Windows 執行）、P1-4 的 packaged-build 手動流程：六個 spec 的 "Windows verification debt" 段落至今都沒有執行紀錄。
- 為何列 Important 而非 Minor：下一階段 P2-5（`translate.py` 拆 tokenizer／wrapper，roadmap 標「中–高」風險）與 P2-7（`braille/` 膠水、`MathCATAdapter` 注入）正是這些 Windows-only 路徑；若在 P2-5 開工前沒有一次乾淨的 Windows 基線（packaged build 的 Braille Result／BRL bytes、三個 Windows-only 模組的結果），P2-5 的 golden test 只能證明「fake helper 下不變」，不能證明「真 liblouis 下不變」。
- 建議：
  1. 排一個獨立的 Windows 驗證 session（半天），依序：修 `test_language_detection_translation.py:17`（改為 `from translate import TranslationResult`，並把用到 `translate(...)` 的呼叫改經 `adapters.translation.provider.build_default_translation_runtime().text_translator.translate(...)`，或若測試邏輯已失效則刪除並記錄）；跑 `tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation` 與 `discover`，把 Windows 的 `Ran/skipped` 數字附回本記錄；跑 `scripts\generate-pot.bat` + `msgmerge`、確認四個 orphan 變 `#~`，重編 `.mo`；P1-2 四張截圖；各 spec 的 packaged-build 手動項目，重點是 P1-5／P1-6 的「轉換結果 byte-identical」與 P1-1 的 `TEXT2BRAILLE_LANG` unset／`=en` 比對。
  2. 把這次 Windows 結果當作 P2-5 的前置條件（而非 P2-5 的驗收項）。
  3. 順手在 Windows 上量 P1-5 known defect 3（`reclean_braille_endspace` 對真實 `zh-tw.ctb` 輸出的 trim 次數），P2-5 才能決定是否處理。

### Minor

**M-1 `conversion/presenter.py` 讓 `conversion` 套件反向依賴 `documents`**
- 位置：`client/conversion/presenter.py:31-32`（`from documents.controller import DocumentController`、`from documents.workspace import Document`）；同時 `client/documents/formats.py:8` `from conversion.math_service import latex_to_mathml`（P1-5 從 `dual_view.model` 搬過來的）。
- 驗證：`grep -rn "^from documents" client/conversion` 只有這兩行；phase 前 `conversion/` 完全不依賴 `documents/`。目前無 module-level import 循環（`conversion.math_service` 不會回頭 import presenter；全套件與 20 個 shuffle 皆正常），但套件層級變成 `conversion ⇄ documents` 雙向。
- 評估：`ConversionPresenter` 的職責是主視窗的轉換狀態機（busy、timer、對話框、把結果寫回 `DocumentController` 快取），是 application/UI 層的 coordinator，與 `documents/export_coordinator.py` 同層；放在 domain 套件 `conversion/` 是依 roadmap §6.2 的命名，符合 spec，故只列 Minor。
- 建議：P2（可併入 P2-6 或一個小 `refactor:`）把它搬到 `ui/conversion_presenter.py` 或新建 `app/`，與 `export_coordinator` 並列；`test_translation_import_isolation` 加一條「`conversion.*`（排除 presenter）不得 import `documents`」的 guard。若維持現狀，至少在 `refactor.md` §4.3 的分層圖註明。

**M-2 `tests/test_gui_document_flows.py` 已達 3550 行／12 個 class／138 個測試，且有兩個可測性弱點**
- `BrailleAppLifecycleTest(GuiDocumentFlowsTest)`（`:469`）仍繼承 `GuiDocumentFlowsTest`，基底的 5 個測試被跑兩次（P1-4 spec 已承認）。
- `FrameWorkspaceServiceDelegationTest._make_frame`（`:224`）用無 spec 的 `Mock()` 當 `_workspace_service`：若日後 service 方法改名，delegation 測試仍會綠（`Mock` 任何屬性都存在）。目前由 `DocumentWorkspaceFlowsCharacterizationTest` 以真 service 走檔案系統補住，所以不是缺口，但 `Mock(spec=DocumentWorkspaceService)` 零成本。對照 P1-4 的 delegation 測試已用 `Mock(spec=ConversionPresenter)`（4 處），兩個任務不一致。
- 建議：P2 任一碰到此檔的任務順手拆成 `test_gui_document_flows.py`（文件流程）、`test_gui_menu_export.py`、`test_gui_conversion.py`，並改掉子類繼承。

**M-3 P0 review M-2 的守門測試仍在，且如預期在 P1-2 被迫修改**
- `tests/test_i18n.py::SharedSetupConsumerTest` 在 P1-2 改成 `gui.py = {"_", "resource_path"}`、`dialog.py = {"N_", "_"}`（P1-2 spec 明文「redesign 留給 orchestrator follow-up」）；`tests/test_removed_dead_code.py`、`test_dead_frame_helpers_are_removed` 仍存在（P1-2 只刪了兩行正向斷言）。P1-3／P1-4 新增的是「positive contract」測試（`DocumentControllerOwnershipTest`、`Frame*DelegationTest`）而非 absence guard，方向正確。
- 建議：P2 kickoff 一次決定：`SharedSetupConsumerTest` 改負向斷言；P0-3 的 absence guard 在 P2-6 前刪除。

**M-4 `tests/test_translation_result.py` 仍是 pytest-style、`unittest` 下 `NO TESTS RAN`**
- 驗證：`python -m unittest tests.test_translation_result` → `NO TESTS RAN`；檔內 13 個頂層 `def test_`。P1-5 spec "Known defects" 第 1 項已記錄（直接呼叫 8 pass／5 fail），留給 P2-5。P1-6 把同型的 `test_conversion_text_dictionary_rules.py` 轉成 `unittest`（7 → 20 tests），兩者處置不一致，但 P1-5 的理由（這 13 個是 tokenizer／wrapper 行為，P2-5 要先釐清預期）成立。
- 建議：P2-5 step 1 先轉檔並把 5 個失敗案例與 P2-5 的既有失敗一併裁決；roadmap P1-5／P2-5 的驗證指令引用此模組，現在實際貢獻 0 個測試，記錄裡要註明。

**M-5 `ExportBatchResult` 的摘要文字未翻譯（P1-4 known defect 4）是 zh_TW 使用者可見的缺口**
- 位置：`client/documents/export_results.py` 的 `summary_template`／`summary_title` 經變數傳給 `_()`，不在 `.pot`；`.po` 裡對應條目已是 `#~`。另外 `conversion/plain_text.get_public_error_message` 的兩個 fallback 文字、P1-2 刻意未標記的 `"HTML"`／`"HTML files (*.html)|*.html"`、匯出 HTML 的 "No conversion data" 預設訊息也都是英文。P1-4 以 3 處 `KNOWN BUG (defect 4)` 釘住。
- 建議：合併為一個 localization 任務（見「既有缺陷清單」第 4 組），不要散在各 refactor 任務裡。

**M-6 P1-6 留下兩條取得字典規則的路徑**
- `conversion/text/pipeline.py:64-69` `translate_plain_text_segment(..., dictionary_rules=None)` 在未傳 loader 時自建一個；`conversion/text/dictionary_rules.py:249` `apply_dictionary` 只剩測試與 P0-3 guard 使用，production 無呼叫者。兩者都在 spec 內（向後相容既有測試、P0-3 guard 不改），且讀碼確認 service 永遠傳 loader，所以只是 API 表面多了一層。
- 建議：P2 整理 `conversion/text` 時把 `apply_dictionary` 改成 test helper 或刪除（同時更新 `test_removed_dead_code.py`），並考慮把 `dictionary_rules` 改為必填 keyword。

**M-7 `ConversionView` 與 `ExportView` 各自宣告 `show_info`／`show_error`**
- `client/conversion/presenter.py:59-61` 與 `client/documents/export_coordinator.py:32-36`。frame 只實作一次，Protocol 是結構型別，無害；只記錄。若之後再出現第三個 view protocol，抽一個 `MessageView` 共用。

**M-8 refactor.md §5.5 的 module alias 與 pipeline 的 function-local import 仍在**
- `client/conversion/service.py:21-23`（`_translate_plain_text_segment` 等三個 alias，供測試 monkeypatch）；`client/conversion/text/pipeline.py:50, 66`（`text.zhuyin`、`languageDetection` function-local import）。P1-5／P1-6 spec 皆明列 out of scope；非本階段問題，列入 P2 清單。

**M-9 `client/gui.py:30` import block 內一行 tab（`\tget_workspace_directory,`）夾在 4 空白的連續行之間**
- phase 前已如此（P1-2 spec 甚至註明「leave them as they are」）；純格式，P2-8 統一時處理。

**M-10（不確定、pre-existing）`_on_close` 不停止 presenter 的 timer、且 `CanVeto()` 為 false 時強制關閉可能讓 worker 完成後對已銷毀的 frame 呼叫 view 方法**
- `client/gui.py:966-979`：轉換進行中且 `CanVeto()` 為 false（例如系統關機）時，frame 被銷毀，但 worker 完成後 `wx.CallAfter(_deliver_success)` → `ConversionPresenter._end_job` → `view.set_conversion_busy(False)` → `self.GetMenuBar()`，在 wxPython 上會是 "wrapped C++ object has been deleted" 的 `RuntimeError`；2 秒 timer 也可能在 frame 銷毀後 `ConvertingDialog(self)`。舊碼（`7f0d127:1351-1364`）行為相同，不是 regression，且只在 Windows 真 wx 上能重現，故標不確定。
- 建議：若日後處理 P1-4 defect 1／2（busy 期間的 re-entrancy），在 presenter 加 `shutdown()`（stop timer、丟棄 active job）並由 `_on_close` 呼叫。

## 正確性追蹤（對照 `7f0d127`）

### P1-1 explicit conversion language

- `gui._build_conversion_request`（`gui.py:540-550`）每個 request 呼叫一次 `get_lang()`／`get_charset_maps()`（UI thread），值不正規化地往下傳；`main.run_demo` 相同。`config.get_lang()` 本身未改，`TEXT2BRAILLE_LANG` 優先序不變。
- `pipeline.translate_plain_text_segment`：`LanguageDetector(language, default_lang=lang, charset_maps=charset_maps)`、`default_lang = lang.replace("-", "_").split("_", 1)[0]`，與舊碼的 `config.get_lang()` 表達式逐字相同。
- `LanguageDetector`：`add_detected_language_commands` 的 `defaultLang`、`_preferred_full_lang` 的第 2 步改讀 `self.default_lang`（舊碼的 `try/except Exception` 只是包 config I/O，拿掉後語意相同）；`find_language_for_charset` 改為 `if configKey in self.charset_maps` 再 fall through 到 `langs[0]`——app 永遠傳完整 merged map，故 production 不可達；空字串值照舊原樣回傳（spec 已特意不做 truthiness 判斷）。`dict(charset_maps)` 複製，不與 request 共享。
- Math 鏈：`service` → `runtime.math_translator.translate(..., language=lang)` → `MathCATMathTranslator.translate` → `translate_math_segment(..., language=)` → `mathml_to_nemeth_braille` → `get_braille_for_mathml(..., language=)` → `_configure_runtime` 的 `language.replace("_", "-").lower()`，與舊碼 `get_lang().replace("_", "-").lower()` 相同；`provider.py:100` 的 `MathCATMathTranslator(translate_math=translate_math_segment)` 接線已核對，`FallbackMathTranslator.translate` 接受並忽略 `language`。
- `config.py` 從 `conversion.math_braille_codes` re-export 兩個常數（`conversion/__init__.py` 為 1 byte 空檔，無副作用）；`settings/dialogs.py` 等繼續從 `config` 讀。
- `braille/tables/__init__.py`：`getDefaultTableForCurLang(tableType, lang)`，無 production 呼叫者；CRLF 完整保留。
- 刻意差異（spec 已列）：同一次轉換的所有 segment 用同一份語言快照；partial map 不再 `KeyError`。

### P1-2 export／menu contracts

- 逐項比對舊 `_append_document_menu_items`／`_bind_document_menu_handlers`（`7f0d127:396-429`）與 `ui/menu_builder.build_document_menu`：Append 順序（6 個 command → Export submenu 3 項 → Export All submenu 3 項）、submenu item 用 `format_key.casefold()`、Bind 一律在頂層 `menu`、Bind 順序（command 依 descriptor 順序、再 export dep/brl/html、再 export_all dep/brl/html）皆相同；`_EXPORT_FORMATS` 由 registry 推導，值為 `(("dep","Package DEP"),("brl","Braille BRL"),("html","Dual View HTML"))`，與舊硬編碼相同。handler map 由 `_document_menu_handlers()` 建，8 個 action 一一對應；mismatch 改為 build 時 `ValueError`（舊碼為 `KeyError`／靜默略過）。
- `get_document_menu_enabled_state` 改以 action 為 key，真值表與舊 label-keyed 版相同，dict 順序即 descriptor 順序，`Enable` 呼叫順序不變。`apply_document_menu_state` 對缺 item 的 action 會 `KeyError`，production 兩個 dict 來源相同。
- 匯出：`build_export_wildcard(descriptor, _)` 回傳 `_()` 後的同三個字串；`_write_export_document`（現為 `ExportCoordinator.write_document`）對所有 writer 統一 `writer(path, document, ExportContext(dual_view_results=...))`；`_write_html` 不建 parent dir（與舊碼同，有測試釘住）、回傳 `Path` 而非字元數（無人讀）。
- `N_()` 標記：`documents/formats.py`、`ui/action_menu.py`、`ui/translation_menu.py`、`dialog.py`、`conversion/preprocessing/user_script.py` 的定義處；`i18n.N_` 為 identity，`_()` 呼叫點不變。msgid 集合驗證見上表。
- `scripts/generate-pot.bat` 以 `for /r *.py` 排除 `\.venv\` 與 `\tests\` 並帶 `--keyword=N_`，新標記位置都在掃描範圍內（讀碼確認，未執行）。

### P1-3 document controller／workspace service

逐流程對照舊 `gui.py:797-1111` 與 `DocumentWorkspaceService` + 新 frame handler：

- **Save**：`get_document(open_document_name)`（`get_document(None)` → `None`，等同舊的 `if not self._open_document_name: return`）→ `prepare_document_for_save` → **先** `replace_document` **再** `save_document_package`；`OSError` 由 frame 以同一訊息框處理。
- **Add／default**：`create_document` 先寫檔再 `add_document`，失敗時 controller 不動；frame 的 refresh／open／focus 順序不變；default document 仍帶 pending member。
- **Startup**：`ensure_workspace_directory`（`app_paths.get_workspace_directory(path)` 對傳入路徑只做 `Path(path)`，所以舊碼 `self.workspace_dir = ensure_workspace_directory(...)` 的回傳值與傳入值相同，service 忽略回傳值不造成差異）→ `load_workspace_documents` → `controller.load_documents`（多清 open/selected/cache，啟動時本就為空）→ refresh → invalid review（`delete_invalid_files` 逐一 `unlink(missing_ok=True)`、錯誤回呼後繼續）→ ensure → title。
- **Rename**：相等名稱 `ValueError`（frame 先擋掉，不可達）；寫新包 → 舊包存在才 unlink → `controller.rename_document`；任一 `OSError` 傳回 frame 的 "Failed to save document" 框，controller 不動（known defect 3 保留）。
- **Delete**：unlink 存在的包 → `controller.delete_document`；frame 之後讀 `selected_document_name`／`has_documents`／`open_document_name`／`decision.was_open`，分支與舊碼相同。
- **Delete All**：以 `documents_snapshot()` 迭代；第一個 `OSError` → `on_error`（frame 的錯誤框）**先** → `load_workspace_documents` → `restore_documents_after_delete_all_failure` → 回傳 `completed=False, invalid_paths`；frame 再 refresh → review → open first 或 clear editors（不更新 title、不建 default，known defect 4 保留）→ dual view。reload 自己拋錯時在 `on_error` 之後傳播，與舊碼同。
- **Import**：`existing_names=set(document_names)`（casefold 檢查在 `batch_import_documents` 內不變）→ 逐一寫包、失敗變 `BatchIssue(package_path, str(exc))` → `add_documents(saved)`；`issues = load_issues + save_issues` 順序不變；frame 的 open-or-refresh 與 issues dialog 不變。
- **Selection／context menu**：`document_name_at(index)` 對 `-1`（`wx.NOT_FOUND`）與越界回 `None`，再 fallback 到 `selected_document_name`，與舊碼的兩段 if 相同；`on_document_context_menu` 的 hit／select／clear／popup／Destroy 不變。
- **Init 順序**：`__init__` 第一行就建 controller，`_initialize_frame` 建選單時的首次 `_sync_document_menu_state` 讀到空 controller（`has_documents=False`、`document_list` 不存在 → `has_selection=False`），與舊碼 lazy throwaway controller 的結果相同；P1-2 的 `_create_document_menu` build log（含 `Enable`）未變。
- `DocumentController.load_documents` 以新 dict 取代 cache（spec 已列；無人持有舊引用）。

### P1-4 conversion presenter／export coordinator

逐行對照舊 `gui.py:1213-1495` 與 `ConversionPresenter`／`ExportCoordinator`：

- **Manual convert**：`convert()` 順序 running 檢查 → 表格檢查（`show_info(..., _("Info"))`）→ `get_source_text()` → `_start`：`set_conversion_busy(True)` → `close_converting_dialog()` → `build_request`（translation settings 與字典路徑改在 busy 之後讀；`dictionary_path_for_name` 只是 `Path / f"{name}.csv"`，不會拋錯，無可觀察差異）→ `runner.start` → 記 `_active` → `call_later(2000, _show_converting_dialog, job_id)`（舊 timer 被覆蓋不被 stop，同舊碼）。
- **Delivery**：runner 先依 `job_id` 丟棄 stale、`_thread = None`、再回呼；presenter `_take_active` 再比對一次 → `_end_job`（stop 最新 timer → close dialog → busy off）→ manual：`show_conversion_output`（SetValue 後 SetFocus）→ 若有 open document：list 內則 `replace_document(Document(name, source_text_now, braille))`，不論是否在 list 都 `set_dual_view_results(open_name, segments)` → `refresh_dual_view` → `show_info(_("Conversion completed."), _("Info"))`；export：只呼叫 `on_success(display_text)`。與舊 `_complete_conversion` 的 `update_output`／`show_success` 兩種形狀逐步相同。
- **Failure**：訊息模板（`ascii`／`text_processing`／其他）與 `_(get_public_error_message(...))` 搬到 `format_conversion_error`，文字相同；訊息在 `_end_job` 前算出（純函式）；manual → `show_error(message, _("Error"))`，export → `on_error(message)`。
- **Converting dialog**：`_show_converting_dialog(job_id)` 的兩個 guard（job id、running）在 presenter，第三個（dialog 已存在）在 frame 的 `show_converting_dialog`；`close_converting_dialog` 的 `Unbind(EVT_CLOSE)` + `Destroy` 不變。
- **Re-entrancy**：Ctrl+S（`on_output_text_key_down` → coordinator → `convert_for_export` 無 running 檢查）、Ctrl+Tab／Ctrl+O（char hook 仍 active）、Export All gap 的行為與 known defects 1／2 一致；characterization cases 16–18 以 deferred `call_after` + `FakeTimers` 逐 turn 釘住，且該 class 自 step-1 起只改 `_wire_conversion`（AST 驗證）。
- **Export single**：`choose_export_path`（frame：標題、`defaultFile`、wildcard、`FD_SAVE | FD_OVERWRITE_PROMPT`）→ 副檔名修正 → pending：`missing_table_message()` 有值 → `show_error(message, _("Error"))`（舊碼經 `on_error` 的 `wx.MessageBox(..., _("Error"), ICON_ERROR)`，相同）；否則 `convert_for_export(document.text, ...)` → 成功寫 `Document(name, document.text, braille)`；非 pending 直接 `_write_single`。`OSError` 訊息 `_("Failed to export document: {error}").format(error=exc)` 與舊 `_show_file_error` 相同格式；成功框 caption `_("Export Complete")`。
- **Export All**：`choose_export_directory` → `get_format(key).extension` → `documents_snapshot()`（一次快照同時用於衝突掃描與批次，舊碼兩次讀同一 list，內容相同）→ conflicts → `confirm_overwrite_all` → `_export_next`：第一步同步、之後每步 `call_after`；pending 文件在 step turn 啟動轉換、在 delivery turn 寫檔並排下一步；missing table → `conversion_failed(message)`；摘要以 `show_info`／`show_warning` 分 icon。
- **`_on_close`**：`presenter.is_running()` + `close_converting_dialog()`，其餘不變。
- **Runner**：只拿掉 policy，`daemon=True`、`_thread = None` 在回呼前、非 `ConversionStageError` 不投遞皆不變（`test_conversion_jobs` 新增 contract 測試釘住）。
- M-9（`_show_file_error` 的 `parent`）與 `ConversionStageError` 死 import 已清。

### P1-5 translation result layout

- 12 個 set → `frozenset` class attribute，名稱與成員相同；`lang_blocks` → `MappingProxyType` of tuples；唯一讀者 `language_has_all` 只做 `set(language_blocks.get(lang, []))`，tuple 與 list 等價。方法本體（`bind_word_tokens`、`reclean_token`、`wrap` 等）未動。
- `concat`：offset 為「已合併長度」，與舊 pairwise `__add__` 的算術逐元素相同；永遠建四個新 list（0／1 個輸入也不 alias），所以 `wrap_translation_results` 的 `reclean_braille_endspace` 不會碰到 dual-view 快取裡的 segment（`MergeTranslationResultsTest` 釘住）。`__add__` 保留 `TypeError("not TranslateResult object")`。
- `__eq__` 對非 result 回 `NotImplemented`；`__hash__ = None` 明示。
- `DualViewSegment` 搬到 `conversion/output.py`；`dual_view/model.py` 只在 `TYPE_CHECKING` 下 import；`build_dual_view_model(..., mathml_converter=)` 必填，`gui.py:333` 與 `documents/formats.py:107` 都傳 `latex_to_mathml`（與舊 default 相同）。`documents.formats` 的 import closure 不變（以前經 `dual_view.model` 間接載入 `conversion.math_service`）。
- golden fixture（360 segments 長文件 + 5 種短輸入 × 4 寬度 × 2 模式，含 segment 在 wrap 後的四個 list）sha 未變；M-1 的 `sys.modules.pop("translate")` 改為 subprocess，20 個 shuffle seed 全綠。

### P1-6 dictionary rules loader

- `from_paths` 是舊 `apply_dictionary` 前半段的搬移：`Path(dictionary_path)` 不存在 → `cls()` 且不開 Bopomofo 檔；否則先讀 `Bopomofo2Braille.csv`（header／欄位檢查與訊息相同）、建一次 trie，再逐列讀字典，`Bopomofo` 列經 `processing`（例外吞掉、整個 target 當一段）後用 `_scan_trie(part, bopomofo_trie)`（舊為 `mapping(part, replacements_bopomofo)` = `_replace_with_trie`，等價），其餘以 `@` 切；`_align_source_and_replacement_parts`／`_wrap_atomic_parts` 不變。
- `apply`：無規則時直接回傳原文（空 trie 掃描結果本就相同）；有規則時 `_scan_trie` 兩次。`_scan_trie` 只讀 trie。
- `DictionaryRulesLoader` 在 `translate_with_language_dual_view_segments` 的 `text == ""` early return **之後**建立、`load()` 於第一個 plain-text item 才讀檔：空輸入與 math-only 輸入不讀字典、preprocessing 失敗仍報 `text_processing` 階段、math segment 在字典錯誤前先翻譯——四條時序由 `DictionaryErrorTimingTest` 釘住。失敗不 memoize。每次 `translate_with_language*` 呼叫一個 loader，無跨轉換快取，Dictionary Management 編輯後下一次轉換即生效（`DictionarySnapshotTest`）。
- `char_maps.py`、`output.py`、`gui.py`、`dictionaries/` 無 diff（criterion 8）。
- 刻意差異（spec 已列）：同一次轉換用同一份字典快照（app 內因 busy 鎖選單不可達）；`processing` 每列每次轉換跑一次而非每 item 一次（純函式）。

### Windows-only／無法在本機驗證（僅讀碼）

- **PyInstaller**（`scripts/build-dotexpress.bat`）：`--onefile gui.py` + `--add-data`（dll、tables、mathcat assets、data、locales）+ `--collect-data latex2mathml`，無 hidden-import 清單；P1 新增的六個模組都由 `gui.py` 靜態 import（`conversion.presenter`、`documents.export_coordinator`、`documents.workspace_service`、`ui.menu_builder` 直接；`conversion.math_braille_codes` 經 `config`；`conversion.text.dictionary_rules` 經 pipeline），PyInstaller 的靜態分析會收進去。`i18n.resource_path` 未改。
- **liblouis／MathCAT**：P1-1 的 `SetPreference("Language", ...)` 值由同一表達式計算；P1-5 的 `LiblouisTextTranslator` 建出的 `TranslationResult` 只差 class attribute；P1-6 讀檔為純 Python。皆無法在 Linux 執行，見 I-1。
- **`generate-pot.bat`**：讀碼確認掃描範圍與 `--keyword=N_`；未執行。四個 orphan 仍在 `.pot`／`.po`，待 Windows 一次 regenerate + `msgmerge`。
- **wx 行為**：`wx.CallLater` 回傳物件的 `Stop()`、`EnableTop`、`FindMenu(翻譯後標題)`（defect 5）、`PopupMenu` 後 `Destroy()`，皆與舊碼同一組呼叫，但 stub 無法證明 wx 端語意。
- **NTFS／APFS case-insensitive**：P1-3 cases 30／32 在 Linux skip，Windows 上才會執行並釘住 known defects 1／2。

## 設計品質評估

- **`gui.py` 確實變薄**：1541 → 1101 行；`BrailleFrame` 約 1226 → 920 行。拿掉的是：轉換狀態機（約 170 行）、匯出鏈（約 110 行）、property 轉發與一行 wrapper（約 60 行）、選單 append/bind（約 35 行）、wildcard 常數／方法與 48 行 marker tuple。留下的是 wx 專屬碼：選單列、對話框、訊息框、list/editor 更新、view 方法（約 75 行）、設定快照、dual view 視窗、字型。剩餘可再抽的：`_set_view_font_size` → `sync_open_font_size`（P2-4）、`_initialize_state` 內的路徑解析（P2-6）、`ConvertingDialog`（可隨 P2-1 進 `ui/`）。
- **新模組 wx-free、內聚、依賴方向正確（M-1 除外）**：四個新模組與 `conversion/jobs.py` 都有 AST 測試證明不 import `wx`／`gui`；`menu_builder` 只依賴 `ui.action_menu`；`workspace_service` 只依賴 `documents.*`；`export_coordinator` 依賴 `documents.*` + `i18n`；`dictionary_rules` 無 client 依賴。`conversion` 不再 import `dual_view`、`dual_view` 不再 import `conversion`／`config`、四個 consumer 不再 import `config`（subprocess guard）。
- **符合 refactor.md §7 的取捨**：沒有通用 task framework（runner 只減不增）；沒有抽象 View 基類（`typing.Protocol` + recording fake，與 P0-6 同款）；registry 仍是 tuple；`languageDetection` 只拿掉 config 相依、演算法與 camelCase 保留；NVDA 衍生檔未動。
- **不必要的抽象**：未發現。`_ActiveJob`／`_ExportCallbacks` 取代四欄 policy 是縮減；`ImportResult`／`DeleteAllResult` 讓 frame 不再碰 tuple；`ExportConversions` Protocol 只有兩個方法，讓 coordinator 測試不必建 presenter。`LoadedDictionaryRules`（value）與 `DictionaryRulesLoader`（lazy once）分開是為了錯誤時機，spec 有理由。
- **跨任務一致性**：P1-3 的 Delete All 用 callback、其他流程用例外——spec 有解釋（錯誤框必須在 reload 之前）；P1-4 兩個 presenter 都由 view 擁有對話框文字、coordinator／presenter 擁有結果訊息；P1-2／P1-4 都以「注入 wx 零件」而非「import wx」。字串全部在定義處 `N_()` 或呼叫處 `_()`，`i18n` 是唯一 catalog。縮排：新檔 4 空白、舊檔保留 tab（`dual_view/model.py` 的 `TYPE_CHECKING` 區塊用 tab 與檔案一致）。
- **死碼／殘留**：`apply_dictionary`（test-only，M-6）、`getDefaultTableForCurLang`（無呼叫者，NVDA 對照用，P2-7 決定）、`DocumentFormatDescriptor.requires_braille`（仍無讀者，P1-2 spec 刻意保留）、`DocumentWorkspaceService.workspace_dir` property（只有測試讀）、`service.py` alias（M-8）。無新的死 import（P1-3／P1-4 每步清掉一個）。

## 測試品質評估

- **Characterization-first 且有凍結證明**：P1-3（32）、P1-4（19）兩個 class 在 step-1 commit 之後只動 fixture helper（AST 驗證）；P1-2 的 11 個在 P1-3／P1-4 只改 setup 行；P1-5 golden fixture sha 鎖定；P1-6 的 rule matrix／error table 同時跑舊 API 與新 API。
- **真正抓得到回歸的測試**：P1-4 的逐 turn event log（deferred `call_after`、`FakeTimers.fire()` 可在 `Stop()` 後觸發以測 presenter 自己的 guard）、P1-3 以檔案系統注入故障（目錄冒充 `.dep`）而非 patch 函式、P1-6 的 `Path.open` 計數（並斷言字典名稱至少出現一次，避免 vacuous pass）、P1-2 的 literal build log、P1-1 的「同一 request 在 `TEXT2BRAILLE_LANG=zh_TW`／`ja` 下輸出相同且 `config.get_lang` 被 patch 成 `AssertionError`」。
- **KNOWN BUG pins**：17 處，每處標 spec + defect 編號；P1-3 的四個（含兩個只在 case-insensitive FS 執行）、P1-4 的七個、`test_conversion_jobs` 一個。修復任務可用 `grep -rn "KNOWN BUG"` 找到全部要翻轉的斷言。
- **實作耦合／脆弱度**：build log 字面量（`DOCUMENT_MENU_BUILD_LOG`）與 `FindMenu(翻譯標題)` log 是刻意的 wx 呼叫層釘住，改 wx 呼叫方式時要一起改——可接受。`SharedSetupConsumerTest`／absence guard 為 P0 遺留（M-3）。`Mock()` 無 spec（M-2）。
- **時間**：唯一 timing 斷言 `LinearMergeTest`（5 s 上限，實測整個 class 0.27 s）；無 `sleep`；全套件 1.6 s；最慢模組 0.39 s。
- **隔離**：20 個 full-suite seed、P0 I-1 pair、P1-4 三模組兩種順序、P1-5 core/service 兩種順序皆乾淨；`StubScope` 對四個新純模組的 eviction 無問題。
- **缺口**：Windows-only 模組（I-1）；`tests/test_translation_result.py` 0 個測試（M-4）；`requires_braille` 無行為測試（因無行為）。

## P2 建議（對 `storage/refactor.md` §6.3 的調整；P2-8 已決定略過，P2-5 最後）

1. **P2 開工前：一次 Windows 驗證 session（I-1）**。修 `test_language_detection_translation.py:17`，跑三個 Windows-only 模組與 `discover`，packaged build 走各 spec 的 debt 清單（重點：P1-5／P1-6 轉換 bytes、P1-1 `TEXT2BRAILLE_LANG`、P1-2 截圖、`generate-pot.bat` + `msgmerge` + `.mo`），結果附回本記錄。沒有這個基線不要開 P2-5。
2. **P2-1（dialog base）**：`ConvertingDialog` 仍在 `gui.py:108-121`，可隨 P2-1 搬進 `ui/`；`NameValidationError(code)` 影響 `documents/workspace.normalize_document_name` 與 `_prompt_for_document_name` 的錯誤分支，P1-3 的 characterization case 2 會保護。
3. **P2-3（設定選項單一來源）**：math 表常數現在的真相在 `conversion/math_braille_codes.py`（P1-1 leaf），`config` 只是 re-export；P2-3 直接從 leaf 讀。P0 M-5（`__tables.py` 的 localedir 指向不存在的 `client/braille/locales`，source-run 表格排序與 packaged 不同）P1-1 未處理（spec 明列 `__tables.py` 不可編輯），P2-3／P2-7 擇一決定（adapter 層包一次排序，或記錄為 won't fix）。
4. **P2-4**：`gui.py:576` `DotExpressSettingsDialog.sync_open_font_size` 仍是反向探針，範圍未變。
5. **P2-6（ApplicationPaths 注入）**：P1-3 已讓 `DocumentWorkspaceService(controller, workspace_dir)` 接路徑、P0-6 讓 `DictionaryManagementPresenter(dictionary_dir)` 接路徑；剩 `gui._initialize_state` 的 `get_dictionary_directory()`／`get_workspace_directory()` 與 `_build_conversion_request` 的 `resource_path("data")`，加上 `config.ConfigStore`。建議在 P2-6 一併做 M-1（`conversion/presenter.py` → `ui/` 或 `app/`），因為兩者都在重畫 `BrailleFrame.__init__` 的組裝。
6. **P2-7（braille 膠水）**：`getDefaultTableForCurLang(tableType, lang)` 無呼叫者——決定刪除或接上；`MathCATAdapter.get_braille_for_mathml` 已有顯式 `language`，注入時保留；`logging.basicConfig` 兩處。Windows-only 驗證，與第 1 點合併排程。
7. **P2-5（最後）**：先做 M-4（轉 `test_translation_result.py`、裁決 5 個失敗）與既有 P2-5 失敗案例的預期；納入 P1-5 known defects 3（`reclean_braille_endspace` 二次方）與 4（`language_has_all` 每字建 set）——先用第 1 點量到的 Windows trim 次數決定優先序；golden fixture（fake helper）+ Windows 基線（真 liblouis）雙保險。
8. **測試衛生（任一 P2 任務順手）**：M-2 拆 `test_gui_document_flows.py`、去掉 `BrailleAppLifecycleTest` 繼承、`Mock(spec=...)`；M-3 守門測試退場；M-6 `apply_dictionary` 降級為 test helper。

## 既有缺陷清單（P0–P1 發現、尚未修復；建議獨立 fix task，依使用者影響排序）

| 優先 | 缺陷 | 來源 | 影響 | 釘住的測試 | 建議修法 |
| --- | --- | --- | --- | --- | --- |
| 1（資料遺失，Windows／macOS） | 大小寫-only 的 Rename（`Alpha`→`alpha`）在 case-insensitive FS 上寫完新包後把「舊包」unlink，實際刪掉同一個檔；文件在下次啟動消失 | P1-3 defect 1 | 高：使用者操作即丟文件 | `test_case_only_rename_on_case_insensitive_file_system_deletes_package`（Linux skip） | prompt 的重複檢查改 `casefold()`；rename 時若新舊路徑 `samefile` 則不 unlink（或改用 `os.replace`） |
| 1（資料遺失，Windows／macOS） | Add 一個只差大小寫的名稱（`Alpha` 而 `alpha` 已存在）覆寫另一份文件的包；下次啟動被判 invalid | P1-3 defect 2 | 高 | `test_add_case_variant_on_case_insensitive_file_system_overwrites_package` | 同上（Import 已是 casefold，對齊即可） |
| 2（資料不一致） | Rename 時 unlink 舊包失敗 → 磁碟兩份、記憶體一份；下次啟動出現兩份文件 | P1-3 defect 3 | 中 | `test_rename_unlink_failure_leaves_both_packages_and_state`、service `test_rename_unlink_failure_propagates_and_leaves_both_packages` | unlink 失敗時回滾（刪新包）或改用 rename-then-write |
| 2 | Delete All 回滾後沒有任何有效文件時：editors 清空但 title 不更新、不建 default document | P1-3 defect 4 | 中低 | `test_delete_all_failure_without_valid_document_clears_editors_only` | 回滾分支呼叫 `_update_window_title()` + `_ensure_open_document_exists()` |
| 3（結果寫錯文件、無提示） | 轉換中 Ctrl+Tab／Ctrl+Shift+Tab／Ctrl+O 仍可切換文件，結果寫入完成當下開啟的文件與其快取 | P1-4 defect 1 | 中高：輸出靜默錯位 | `ConversionExportFlowsCharacterizationTest` case 17 | busy 期間在 `on_char_hook` 擋掉這三個快捷鍵（或 presenter 記住啟動時的 open name，完成時比對） |
| 3 | `convert_for_export` 不檢查 running：Ctrl+S（Braille Result 區）或 Export All gap 內的 Convert 會啟動第二個 job，第一個結果被靜默丟棄、無訊息 | P1-4 defect 2 | 中 | cases 16、18；`test_conversion_presenter` 一處 | presenter 加 queue 或在 running 時回 `show_info`；Export All 期間維持 busy |
| 3 | pending 文件匯出 HTML 用的是舊快取（export 轉換的 `dual_view_segments` 被丟掉），可能輸出「No conversion data」 | P1-4 defect 3 | 中：匯出內容與預期不符 | 無（spec 記錄） | `convert_for_export` 的 on_success 多帶 `dual_view_segments`，HTML writer 用該次結果 |
| 4（本地化） | Export All 摘要（標題／訊息）、`get_public_error_message` 兩個 fallback 文字、`"HTML"`／`"HTML files (*.html)|*.html"`、匯出 HTML 的 "No conversion data" 訊息、`"Close"` 空翻譯；source-run 下表格排序（P0 M-5） | P1-4 defect 4、P1-2 out of scope、P0 M-5 | 中：zh_TW 使用者看到英文 | 3 處 `KNOWN BUG (defect 4)` | 一個 localization 任務：`export_results.py` 改 `N_()`、補 `.po`、`generate-pot.bat` 重跑 |
| 5（穩健性） | UTF-8 BOM 的字典（Windows 記事本）被拒：`CSV must contain columns: text, braille, type`；`validate_dictionary_csv` 同 | P1-6 defect 1 | 中：匯入／轉換直接失敗，訊息不指向原因 | 有（BOM header → `ValueError`，釘住現狀） | 讀取改 `utf-8-sig`，與匯入驗證一起決定 |
| 5 | `Bopomofo2Braille.csv` 壞掉只在「字典存在且有 plain text」時才報；`processing` 例外被吞 | P1-6 defect 2 | 低 | 有 | 啟動時或 Settings 驗證一次 data 檔 |
| 5 | worker 拋非 `ConversionStageError` 的例外（目前只剩 `BaseException`）→ 不投遞、UI 永遠 busy | P1-4 defect 6 | 低（幾乎不可達） | `test_conversion_jobs` 一處 | runner 把所有 `BaseException` 包成 failure 投遞 |
| 5 | Export All 中 writer 拋 `ValueError` 會中斷鏈且無摘要（選單只給 exportable 格式，不可達） | P1-4 defect 7 | 極低 | `test_export_coordinator` 一處 | `_export_next` 捕 `ValueError` 記為 failure |
| 5（不確定） | 不可 veto 的關閉（系統關機）在轉換中：worker 完成後對已銷毀 frame 呼叫 view 方法、2 s timer 可能建 dialog | 本次 M-10 | 低，Windows 才能重現 | 無 | presenter `shutdown()`，`_on_close` 呼叫 |
| 6（效能） | `reclean_braille_endspace` 對 trim 次數二次方（10k trims 3.8 s、40k 62 s，fake helper 量測） | P1-5 defect 3 | 視真實 trim 次數而定 | golden fixture 當安全網 | P2-5 或獨立任務；先在 Windows 量 |
| 6 | `LanguageDetector` 每個 text segment 建一次；preprocessing script 每次轉換編譯一次 | P1-6 defect 3 | 低 | — | 隨 P2-5／pipeline 整理 |
| 7（測試） | `test_language_detection_translation.py` import 不存在的 `translate.translate`（Windows 上 error）；`test_translation_result.py` pytest-style 不執行、5 個失敗；P2-5 既有失敗 `test_translate_with_language_does_not_duplicate_existing_spaces_around_math` | P1-5 defects 1／2、refactor.md §6.0 | 安全網缺口 | — | I-1 與 M-4；P2-5 裁決 |

## Final assessment

**Ready: Yes.** P1 六個任務的 production 變更經逐流程比對無 regression，acceptance 指令全數通過，測試隔離問題（P0 M-1）已清，`gui.py` 與新模組的分層達成 roadmap §6.2 的目標。需在 P2-5／P2-7 之前處理 I-1（Windows 驗證 session + 修一行 import）；Minor 項目併入 P2 對應任務即可，不需要回頭改 P1 的程式碼。

## 修正紀錄（review 之後）

- I-1：`5ff475b` test: repair Windows-only language detection translation test —— `tests/test_language_detection_translation.py` 改用 `adapters.translation.provider.create_default_text_translator()`（production 的 `LiblouisTextTranslator`）與 `TranslationResult.concat`，並改為 `unittest.TestCase`；`tests/test_translation_language_result.py` 由 pytest-style 函式包成 `TestCase`。兩者的 Windows skip guard 保持在最前面。
  - Linux：`py_compile` 通過；`discover` 仍為 `Ran 818`, `failures=1`（P2-5）, `skipped=9`；import-resolution 檢查 34 ok / 0 failed；以偽造 `WINFUNCTYPE` 模擬收集時兩個模組各收集到 1 個測試（修正前為 ImportError / 0 個）。
  - 仍待 Windows：執行上述模組與完整 discover、確認一致性斷言在真實 liblouis 下成立。
- 其餘 Minor：M-1（presenter 位置）併入 P2-6；M-2/M-3/M-6 測試衛生併入觸及該檔案的 P2 任務；M-4 併入 P2-5；M-5 與既有缺陷清單列入最終待辦。
- Windows 驗證工作階段：建議於 P2-5 之前執行，由使用者決定。
