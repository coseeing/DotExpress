# DotExpress client 重構 — 交接文件（Linux session → Windows）

建立日期：2026-10-09。來源 session：Linux 容器上的 Claude Code CLI（session `c0b338ab-efa4-4037-b0f9-1b4ce4e6c150`）。
本文件讓 Windows 上的新 Claude Code session 能接續工作。請先讀完本文件，再讀「必讀文件」。

## 1. 工作方式（使用者指定，請沿用）

- 依 `refactor-review.md` §6.4 的執行順序逐一自動執行；除非遇到需要使用者決策的重大問題，否則一個任務完成後自動往下。
- 每個任務：
  1. 撰寫 spec（Opus 5.5，effort high）
  2. 撰寫 plan（Opus 5.5，effort high）
  3. 以 TDD 實作（Opus 5.5，effort high）
- 每個任務開一個 branch，完成並驗證後自動 `git merge --no-ff` 回 `main`（訊息 `merge: <描述> (<任務 ID>)`）。
- 每個階段完成後，用 Fable 5.1（effort high）對整個階段做 review；Critical／Important 由 Opus 修正後再 merge。
- 檔案位置慣例：
  - spec：`docs/superpowers/specs/<日期>-<slug>-design.md`，另附 `_zh-TW.md` 翻譯
  - plan：`docs/superpowers/plans/<日期>-<slug>.md`
  - 階段 review：`docs/superpowers/history/<日期>-<序號>-<名稱>/review_task.md`
- 共同約束：遵守 `AGENTS.md`；保留使用者可見行為；沿用檔案既有縮排（許多檔案是 tab）；不修改 NVDA 衍生的 `client/braille/tables/__tables.py` 與 vendored `client/braille/liblouis/`；`client/braille/tables/__init__.py` 是 CRLF，要逐位元組保留；`client/dictionary/` 是使用者真實資料（git-ignored），絕不可動。
- commit 訊息結尾：`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## 2. 必讀文件

| 文件 | 內容 |
| --- | --- |
| `docs/superpowers/history/2026-10-09-02-handoff/refactor-review.md` | 原始重構審查報告（Fable 5.1；原檔在 git-ignored 的 `storage/refactor.md`，此為複本）。§6 是路線圖 |
| `docs/superpowers/history/2026-10-08-01-refactor-p0/review_task.md` | P0 階段 review 與修正紀錄 |
| `docs/superpowers/history/2026-10-08-02-refactor-p1/review_task.md` | P1 階段 review 與修正紀錄 |
| `docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md` | P2 階段 review、**P2-5 準備度與失敗測試分析**、**既有缺陷清單**、**Windows 驗證總清單 1–16** |
| `docs/superpowers/history/2026-10-09-01-fix-data-loss/review_task.md` | F-1／F-2 review、**Windows 驗證清單 17–29**、剩餘缺陷清單 |
| `docs/superpowers/specs/2026-10-0[89]-*` 與 `docs/superpowers/plans/2026-10-0[89]-*` | 每個任務的 spec／plan（spec 內含「Corrected after planning」修正段） |

## 3. 已完成（全部已 merge 進 `main`，最新 `136b023`；尚未 push）

| 任務 | merge commit | 摘要 |
| --- | --- | --- |
| P0-1 | 506a8da | config 錯誤改為 log（含節流）；刪 3 個死 setter；**保留** `language_detection` 首次寫入（6e5819f 的刻意功能） |
| P0-2 | e5fa59a | 翻譯表全域變數改為 `BrailleFrame.translation_tables` |
| P0-3 | 8404088 | 刪除死碼（含 `dictionaries/import_flow.py`） |
| P0-4 | 78a2eb2 | 共用 `tests/wx_stub.py` + `StubScope`（解決測試順序污染） |
| P0-5 | 70aae6b | 單一 `client/i18n.py`；選單標記改 `N_`；`generate-pot.bat` 加 `--keyword=N_` |
| P0-6 | b2f7f62 | wx-free `dictionaries/presenter.py` |
| P0 review | 7f0d127 | Needs fixes → 修正 StubScope 父套件屬性 |
| P1-1 | 029a86e | `ConversionRequest.lang/charset_maps`；底層模組不再 import `config` |
| P1-2 | ef1988e | `ExportContext`、registry 產生 wildcard、`ui/menu_builder.py`、刪 `_MENU_TRANSLATION_MARKERS`（msgid 357→353，刪 4 個孤兒） |
| P1-3 | d6e4663 | `DocumentController` 完整採用 + `documents/workspace_service.py` |
| P1-4 | 7095265 | `ExportCoordinator` + conversion presenter（現於 `ui/conversion_presenter.py`） |
| P1-5 | cdae2f1 | `TranslationResult.concat` 線性合併；`DualViewSegment` 移至 `conversion/output.py`；黃金快照 `client/tests/fixtures/translation_golden.json` |
| P1-6 | c34d31c | 字典規則每次轉換只讀一次 |
| P1 review | 000239b | Ready；修 Windows-only 測試 import |
| P2-1 | 33dc34d | `ui/dialog_base.py` mixins；`NameValidationError(code)`；`ConvertingDialog` 移至 `dialog.py` |
| P2-2 | f16bfc8 | `dictionaries/entry_list_model.py`；`SpeechSymbolsDialog` 改名 `DictionaryEntriesDialog`；trace 快照 |
| P2-3 | 6dd65e3 | `settings/options.py` 單一選項來源 |
| P2-4 | f1ff5b3 | 字級同步改為實例方法（`SingletonDialogMixin.open_instance()`） |
| P2-6 | 5764ad3 | `ApplicationPaths` + `ConfigStore` 注入；刪 `CONFIG_PATH` 與模組層 config 函式 |
| P2-7 | e57cae7 | braille 膠水不再 `basicConfig`；MathCAT 由 runtime 管理；修改 `scripts/sync-nvda.py` 的 `_adapt_helper` 並重產 `vendor/nvda/liblouis/runtime/louis_helper.py` |
| P2 review | c8ecf66 | Ready（P2-5 除外） |
| F-1 | aced6f8 | 資料遺失修正：大小寫只差的改名／新增（case-safe `move_document_package`、casefold 重複檢查） |
| F-2 | 80e7be6 | 資料遺失修正：CSV 一律 `utf-8-sig`；`shared/atomic_write.py`；字典編輯器 OK 捕捉所有例外 |
| F review | 136b023 | Ready；補 fsync 測試、case-only 改名保留權限、測試加速 |

- **跳過**：P2-8（縮排統一），使用者未要求。
- **Linux 測試狀態**（`cd client && python -m unittest discover -s tests`）：`Ran 1141`, `failures=1`, `skipped=7`。唯一失敗是既有的 P2-5 測試 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`（從 6e5819f 起就失敗，非重構造成）。`python -m unittest discover -s scripts/tests`：27 OK。翻譯 msgid 353。
- **重要**：以上全部只在 Linux（無 wx、liblouis／MathCAT 以 fake 取代）驗證，**從未在 Windows 執行過**。

## 4. 待辦（依順序）

### 4.1 修好 Windows 上 `python gui.py` 的啟動錯誤
症狀：`AttributeError: function 'lou_freeTableInfo' not found` → `OnInit returned false`。
判斷：`client\braille\liblouis.dll` 比產生的綁定 `client\braille\liblouis\__init__.py` 舊（綁定需要 upstream 2025-05-29 加入的 `lou_freeTableInfo`）。重構前的 6e5819f 遇到同樣檔案也會失敗。
處理（repo 根目錄，先關閉所有 DotExpress／Python）：
1. `scripts\verify-liblouis-export-state.bat` → 預期看到 `MISSING: lou_freeTableInfo`
2. `scripts\clean-liblouis.bat`、`scripts\build-liblouis.bat`、`scripts\install.bat`
3. 再跑步驟 1，全部 `OK` 後執行 `python gui.py`

**不要執行 `py scripts\sync-nvda.py`**：完整 sync 不是冪等的，會把 `vendor/nvda/liblouis/build/sconscript` 的手動修改（commit `9aa8355`、`1bd19d7`）蓋回去（AGENTS.md 的說法已過時，見缺陷清單）。

### 4.2 Windows 驗證
依序執行兩份清單並把結果附回各自的 review 記錄：
- `2026-10-08-03-refactor-p2/review_task.md` 的「Windows 驗證總清單」1–16
- `2026-10-09-01-fix-data-loss/review_task.md` 的清單 17–29

其中包含 P2-5 需要的基線（同一份中／英／日／數學混排長文件的 BRL bytes、`" 的值"` 一次 vs 兩次翻譯的 cells、`reclean_braille_endspace` 在真實 `zh-tw.ctb` 輸出上的 trim 次數）。

### 4.3 P2-5（暫停中，待 4.2 完成後開始）
- 內容：`translate.py` 拆成 tokenizer／line wrapper（`refactor-review.md` §6.3 P2-5）。
- 使用者決定：**那個失敗測試留到 P2-5 一起決定**。Fable 分析（P2 review 記錄）：根因是 6e5819f 的 `LanguageDetector` 把 `" 的值"` 拆成 `' '` 與 `'的值'` 兩段；接起來文字相同、空白未重複；分開的空白 token 有利斷行；唯一可見差異是雙視多一個只有空白的片段。建議放寬斷言並加特性測試鎖住空白獨立成段，但需以 Windows 真實 liblouis 結果確認。
- P2-5 前置：把 pytest 寫法的 `tests/test_translation_result.py` 轉成 unittest 並裁決其 5 個失敗；決定 `adapters/translation/contracts.py` 的歸屬（P2 review M-1）。

### 4.4 待使用者決定
- **新發現的優先級 2 資料遺失**：`documents/workspace.py` 的 `save_document_package` 原地截斷寫入 `.dep`；中途當機／磁碟滿／編碼錯誤會留下壞檔，下次啟動被判無效並建議刪除。建議以 F-2 相同手法修正，並一併修「改名時刪不掉舊檔、兩份都留著」（P1-3 defect 3）。使用者尚未回覆是否要修。
- 其餘既有缺陷（優先級 2–7）見兩份 review 記錄的缺陷清單（例如轉換中切換文件會把結果寫到錯的文件、多處訊息未翻譯、`sync-nvda.py` 非冪等、AGENTS.md 寫成 `generate_pot.bat` 但實際是 `generate-pot.bat`）。

## 5. Windows 上接續時的注意事項

- Linux session 用的 venv、shuffle 測試工具、msgid 掃描工具都在 `/tmp` scratchpad，**沒有**帶過來。需要時請重建：
  - 測試：`cd client && py -m unittest discover -s tests`
  - 隨機順序測試：可自行寫一個以固定 seed 打亂模組順序再執行的小腳本
  - msgid 掃描：以 AST 抽出 `client/` 非測試檔中 `_()`／`N_()` 的字串字面值，與 `client/locales/dotexpress.pot` 比對（目前原始碼 353 個，`.pot` 357 個，差 4 個已知孤兒）
- 兩份 fixture 的 sha256 必須不變：`client/tests/fixtures/translation_golden.json` = `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`，`client/tests/fixtures/dictionary_entries_trace.json` = `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`（以 git 的換行設定 checkout 後若 sha 不同，先確認 `core.autocrlf`）。
- 所有 branch 都已 merge 回 `main`，舊 branch 未刪除。
