# Refactor 3 重構建議

日期：2026-07-07

## 範圍與脈絡

本次檢視以目前的 `client/` 與 `server/` 程式碼為主；使用者提到的 `src`，在此 repo 中對應為現有的 `client/` 與 `server/` 原始碼目錄。

已參考的重構與歷史文件包含：

- `docs/refactor/refactor.md`
- `docs/refactor/refactor2.md`
- `docs/refactor/refactor2_zh-TW.md`
- `docs/superpowers/specs/2026-07-07-refactor-phase-planning-design_zh-TW.md`
- `docs/superpowers/plans/2026-07-07-refactor-phase-planning.md`
- `docs/superpowers/specs/2026-07-06-settings-package-refactor-design_zh-TW.md`
- `docs/superpowers/plans/2026-07-06-settings-package-refactor.md`
- `docs/superpowers/history/2026-07-06-03-settings-package-refactor/review_task.md`

補充：`openspec list --json` 目前回報 repo 沒有 `openspec/changes` 目錄，因此本文件以 `docs/superpowers/specs` 與 `docs/superpowers/plans` 作為現況與歷史依據。

## 前一階段狀態

`refactor2` 與 `2026-07-07-refactor-phase-planning` 規劃的四個主要方向，現況已大致落地：

- `client/documents/controller.py` 已存在，用於文件狀態轉換。
- `client/dictionaries/entries.py` 已存在，承接 dictionary entry model、validation 與 CSV load/save。
- `client/conversion/jobs.py` 已存在，承接 conversion worker thread 與 stale job 保護。
- `client/conversion/service.py` 已拆成較小 facade，內部委派到 `conversion/output.py`、`conversion/plain_text.py`、`conversion/segments.py`、`conversion/wrapping.py`。

因此下一階段不應重複「再抽一次相同模組」，而應收斂已抽出的邊界，處理仍殘留在 `BrailleFrame` 與 wx dialog 層的協調責任。

## 現況摘要

目前已有幾個健康的架構方向：

- `client/adapters/translation/` 使用 Adapter / Strategy 風格，將 liblouis、MathCAT 與 fallback runtime 包在小型 protocol 後方。
- `client/settings/` 已將 settings model、staged state、persistence helper 與 wx dialog 收斂到同一 package。
- `client/documents/controller.py`、`client/documents/session.py` 已開始把文件狀態決策移出 frame。
- `client/conversion/jobs.py` 已將 thread 啟動、job id 與 stale result 保護移出 frame。
- `client/dictionaries/entries.py` 已將 dictionary entry domain logic 從 `dialog.py` 抽出。

主要壓力點仍然集中在：

- `client/gui.py` 約 1,700 行，`BrailleFrame` 仍有 100 個以上 method。
- `client/gui.py` 同時保留 frame 欄位與 `DocumentController` 欄位，需要 `_sync_document_controller_state()` 雙向同步。
- `client/gui.py` 的 conversion workflow 仍以多個 frame mutable field 保存 per-job callback 與 UI policy。
- `client/gui.py` 的 import/export flow 仍把 format 判斷、dialog、conversion、filesystem write 與 result reporting 混在同一層。
- `client/settings/dialogs.py` 約 800 行，Template Method 架構可用，但所有 panel 仍集中在單一檔案。
- `client/dialog.py` 雖已抽出 dictionary entry domain logic，但仍同時放 generic dialogs、speech symbols dialog 與 dictionary management dialog。

## Design Patterns Review

### 已經適合保留的模式

Adapter / Strategy：

`client/adapters/translation/` 是目前最成熟的邊界。conversion 呼叫者不需要知道 native liblouis、MathCAT 或 fallback translator 的具體實作，這符合 DIP，也讓未來替換 runtime 的風險較低。

Facade：

`client/conversion/service.py` 現在扮演 public facade，保留 `convert_text_with_alignment()` 與 `convert_text_for_output()`，並將內部步驟委派到較小模組。這個方向正確，下一階段不需要再引入 generic pipeline engine。

Template Method：

`settings.dialogs.SettingsPanel` 讓每個設定分類共用 `make_settings()`、`load_snapshot()`、`on_save()`、validation 等 lifecycle。這對 wx 設定對話框是合適的模式。

Command Descriptor：

`client/ui/action_menu.py`、`client/ui/translation_menu.py` 已把部分 menu item 定義資料化。這個模式可繼續延伸到 import/export format 與 menu enable-state。

Decision Model：

`documents.session`、`dictionaries.actions` 這類純函式 planning logic 是很好的輕量做法，比直接導入大型 domain service 更符合目前專案規模。

### 下一階段應補強的模式

Presenter / Application Controller：

`DocumentController` 已存在，但 `BrailleFrame` 仍保留鏡像欄位並透過 `_sync_document_controller_state()` 雙向同步。下一步應讓 controller 成為文件狀態的單一來源，frame 只讀取 controller snapshot 並更新 wx controls。

Command + State Object：

conversion job runner 已處理 thread，但 `BrailleFrame` 仍以 `_convert_on_success`、`_convert_on_error`、`_convert_update_output`、`_convert_show_success` 保存每次轉換的 UI policy。建議新增一個小型 conversion workflow state，例如 `ConversionUiRequest` 或 `ConversionCompletionPolicy`，把 per-job completion 行為綁在 request/result 上，而不是存在 frame 全域 mutable field。

Registry / Descriptor：

import/export format 目前有部分 registry，例如 `documents.workspace.IMPORT_LOADERS`，但 export 仍在 `gui.py` 與 `workspace.py` 以 `format_key == "dep"` 判斷。下一步適合建立文件格式 descriptor，集中定義 key、extension、wildcard label、loader、writer、是否需要 braille。

Package Split / Module Boundary：

`settings.dialogs.py` 與 `dialog.py` 的問題不是缺少設計模式，而是檔案邊界已經承載太多 UI 類別。這裡應採取 package-level split，不需要新增更重的抽象。

## SOLID Review

### Single Responsibility Principle

最高風險仍是 `client/gui.py` 的 `BrailleFrame`。

雖然前一階段已抽出 document controller、conversion job runner 與 conversion pipeline，但 frame 仍負責 layout、menu、document list、workspace persistence、import/export dialogs、dictionary workflow、settings commit、conversion UI、dual-view refresh 與 app close lifecycle。

具體殘留點：

- `client/gui.py:272` 初始化文件、字典、settings、workspace 與 controller。
- `client/gui.py:646` 透過 `_sync_document_controller_state()` 在 frame 欄位與 controller 欄位間同步。
- `client/gui.py:772` 開始的單文件 export flow 同時處理 dialog、suffix、conversion 與 write。
- `client/gui.py:1477` 開始的 export conversion 與 batch export flow 仍集中在 frame。
- `client/gui.py:1611` 開始的 conversion 啟動與完成流程仍由 frame 保存 per-job callback state。

### Open/Closed Principle

translation backend 的 OCP 狀態良好；新增 backend 可以走 adapter/provider。

較弱的是 document format。新增 import/export format 仍會牽動：

- `client/documents/workspace.py:125` 的 `IMPORT_LOADERS`
- `client/documents/workspace.py:203` 的 batch export suffix/write 判斷
- `client/gui.py:772` 的單文件 export dialog 與 suffix 判斷
- `client/gui.py:1173` 的 export-all suffix/conflict 判斷

這是下一階段比繼續拆 conversion pipeline 更值得處理的 OCP 缺口。

### Liskov Substitution Principle

translation adapter 目前仍是最好的 LSP 範例。只要 translator 回傳符合 `TranslationResult` 行為的結果，呼叫端可以替換實作。

需要注意的是 conversion pipeline 拆分後，`conversion/service.py` 對 helper 的預設參數與測試替身仍要維持一致。不要讓某些 helper 只能在 native runtime 下工作，否則會破壞替換性。

### Interface Segregation Principle

`BrailleFrame` 仍是過大的整合介面。GUI tests 與 callbacks 仍需要依賴大量 private methods，而不是小型 workflow interface。

`DictionaryManagementDialog` 與 `SpeechSymbolsDialog` 雖已改用 `dictionaries.entries`，但 `client/dialog.py` 仍混合多種 dialog 類別。未來若 dictionary workflow 增加功能，dialog class 需要的 interface 應比整個 frame 更窄。

### Dependency Inversion Principle

conversion 對 `TranslationRuntime` 的依賴方向良好。

較弱的是 frame 對具體 filesystem、workspace、dictionary、settings、conversion 與 wx dialog API 的直接依賴。短期不需要 DI container，但可以透過小型 controller/use-case function 讓 frame 依賴更窄的 application boundary。

## 建議的下一階段重構

### 優先 1：讓 DocumentController 成為文件狀態單一來源

建議：

把目前 `BrailleFrame` 中的 `documents`、`_open_document_name`、`_selected_document_name`、`_dual_view_results_by_document` 鏡像欄位逐步收斂到 `DocumentController`，移除或縮小 `_sync_document_controller_state()`。

目標不是擴大 controller，而是避免兩份 state 同步造成未來維護風險。

建議第一刀：

- 在 `DocumentController` 補上 read-only snapshot 或 property，例如 `document_names`、`open_document`、`selected_name`。
- `BrailleFrame.documents` 若仍需保留，先改成 property，委派到 `self._document_controller.documents`。
- `_get_document_by_name()`、`_document_name_exists()`、`_refresh_document_list()` 逐步改讀 controller。
- 最後移除 `_sync_document_controller_state()` 的雙向模式。

適用模式：

- Presenter / Application Controller
- State holder

主要改善：

- SRP：frame 不再同時保存文件 domain state。
- DIP：frame 依賴 controller interface，而不是多個 document helper。
- 測試：文件 state 測試可集中在 `tests.test_document_controller`。

驗證建議：

- `python3 -m unittest tests.test_document_controller -v`
- `python3 -m unittest tests.test_document_session tests.test_document_workspace tests.test_gui_document_flows -v`

### 優先 2：收斂 Conversion UI Workflow State

建議：

`ConversionJobRunner` 已經負責 thread 與 stale job，但 frame 仍保存每次轉換的 completion policy。下一階段可新增小型資料物件，例如：

- `ConversionUiRequest`
- `ConversionCompletionPolicy`
- `ConversionWorkflowResult`

把以下狀態從 frame 欄位改為 per-job state：

- `on_success`
- `on_error`
- `update_output`
- `show_success`
- 是否屬於 manual convert、single export、batch export

`ConversionJobRunner` 不一定要直接知道 wx dialog；可以只讓 request 帶 policy，完成時回傳 job id 與 policy。`BrailleFrame` 仍負責 message box、text control 與 dual-view refresh。

適用模式：

- Command
- State Object
- Observer callback

主要改善：

- SRP：frame 不再以全域 mutable field 保存 conversion job 狀態。
- ISP：manual convert 與 export conversion 可共享較窄的 request/result interface。
- 測試：可在非 wx 測試中驗證 stale job 不會取用錯誤的 completion policy。

驗證建議：

- `python3 -m unittest tests.test_conversion_jobs tests.test_conversion_service -v`
- `python3 -m unittest tests.test_gui_document_flows -v`

### 優先 3：建立 Document Format Descriptor / Registry

建議：

建立集中式 document format registry，先處理現有格式，不新增功能。

候選模組：

- `client/documents/formats.py`

每個 descriptor 可包含：

- `key`
- `extension`
- `wildcard_label`
- `loader`
- `writer`
- `requires_braille`
- `supports_import`
- `supports_export`

現有 `IMPORT_LOADERS` 可以由 registry 產生；`gui.py` 中的 suffix、wildcard、writer 分支也可改讀 descriptor。

適用模式：

- Strategy
- Registry
- Descriptor

主要改善：

- OCP：新增格式時不必同時修改 GUI、workspace 與 import dialog 多個分支。
- SRP：format knowledge 不再散落在 frame。
- 測試：format registry 可用純 unittest 覆蓋，不需要 wx。

建議第一刀：

- 先只把 `dep` 與 `brl` export descriptor 化。
- 再把 import wildcard/filter 與 `IMPORT_LOADERS` 接到同一 registry。
- 保留現有 user-facing labels，不做字串調整。

驗證建議：

- `python3 -m unittest tests.test_document_workspace tests.test_import_dialog tests.test_gui_document_flows -v`
- `python3 -m unittest tests.test_docx_importer tests.test_epub_importer tests.test_pdf_importer -v`，若環境缺 optional dependency，需在 handoff notes 明確記錄。

### 優先 4：拆分 Settings Dialog Panels

建議：

`client/settings/dialogs.py` 目前仍可運作，但已包含 framework、三個 panel 與 `DotExpressSettingsDialog`。下一個 settings category 進來前，應先拆成 package modules。

建議結構：

- `client/settings/dialogs.py`：保留對外 entry point 與 `DotExpressSettingsDialog`
- `client/settings/dialog_framework.py`：`SettingsDialog`、`SettingsPanel`、`MultiCategorySettingsDialog`
- `client/settings/panels/translation.py`
- `client/settings/panels/translation_tables.py`
- `client/settings/panels/view.py`

適用模式：

- Template Method 保留
- Factory / Registry 用於 category class list

主要改善：

- SRP：framework 與 panel implementation 分離。
- OCP：新增 category 時新增 panel module，較少碰觸既有 panel。
- ISP：panel test 可更聚焦。

驗證建議：

- `python3 -m unittest tests.test_settings_dialogs tests.test_settings_state -v`
- `python3 -m unittest tests.test_translation_settings tests.test_translation_tables tests.test_view_settings -v`
- `python3 -c "import sys, settings; assert 'settings.dialogs' not in sys.modules; assert 'wx' not in sys.modules"`

### 優先 5：拆分 `dialog.py` 的剩餘 UI 類別

建議：

`dictionaries.entries` 已完成 domain extraction，因此下一步可把 `client/dialog.py` 拆成較小的 UI modules。這是中低風險的結構整理，適合排在 conversion/document 狀態收斂之後。

建議結構：

- `client/ui/dialogs/common.py`：`DocumentNameDialog`、`InvalidWorkspaceFilesDialog`、`FileIssuesDialog`
- `client/dictionaries/dialogs.py`：`DictionaryNameDialog`、`DictionaryManagementDialog`
- `client/dictionaries/speech_symbols_dialog.py`：`SpeechSymbolsDialog`、`AddSymbolDialog`
- `client/dialog.py`：短期可保留 re-export，等所有 import 更新後再移除或縮小

若專案偏好不保留 compatibility shim，也可以一次更新所有 import；但要避免同時改 user-facing behavior。

適用模式：

- Package split
- Presenter-lite callback interface

主要改善：

- SRP：不同 dialog 不再共用單一大型檔案。
- ISP：dictionary dialog 可依賴較窄的 dictionary callbacks。
- 測試：speech symbols 與 dictionary management 測試可分開 patch import target。

驗證建議：

- `python3 -m unittest tests.test_speech_symbols_dialog tests.test_dictionary_management_dialog tests.test_dialog_validation -v`
- `python3 -m unittest tests.test_dialog_display -v`

### 優先 6：Server 端維持低優先

目前 `server/app/` 規模仍小，沒有明顯需要 service layer 或 repository abstraction 的壓力。除非後續 endpoint、version policy 或資料表增加，否則 server 重構不應排在下一階段前段。

## 不建議下一階段進行的事

不要導入 dependency-injection container。

目前明確的 runtime injection 與小型 constructor injection 已足夠。DI container 會增加 ceremony，但無法直接解決 `BrailleFrame` 狀態同步與 export workflow 分散的問題。

不要把整個 wx app 一次改成完整 MVC/MVVM。

目前更好的方式是延續已驗證的漸進式抽取：一次收斂一個 workflow 邊界，保留 GUI 行為。

不要再把 conversion pipeline 抽成 generic pipeline framework。

`conversion/service.py` 已經足夠像 public facade，內部 helper 也已分模組。下一步應處理 conversion job/UI workflow，而不是發明 pipeline engine。

不要優先重構 server。

server 現況不是主要維護壓力來源。

## 建議執行順序

1. DocumentController single source of truth
2. Conversion completion policy / UI workflow state
3. Document format descriptor / registry
4. Settings dialog panel module split
5. `dialog.py` UI class split
6. 視 server 功能增長再評估 server service layer

這個順序的理由：

- 第 1 項先修補前一階段抽取後留下的雙 state 問題。
- 第 2 項降低 conversion/export callback coupling，直接改善 `BrailleFrame` 的高風險 mutable state。
- 第 3 項補 OCP 缺口，讓下一次 import/export format 變更更小。
- 第 4、5 項是結構健康度整理，適合在高風險 workflow 收斂後進行。

## 測試策略

每個階段都應先補或確認 characterization tests，再改 production code。

建議固定核心回歸組：

- `tests.test_document_controller`
- `tests.test_document_session`
- `tests.test_document_workspace`
- `tests.test_gui_document_flows`
- `tests.test_conversion_jobs`
- `tests.test_conversion_service`
- `tests.test_settings_dialogs`
- `tests.test_dictionary_management_dialog`
- `tests.test_speech_symbols_dialog`

若碰到 importer 測試，需注意環境可能缺 `mammoth`、`lxml`、`ebooklib`、`pypdf` 等 optional dependencies。若無法跑完整 discovery，應在 handoff notes 中記錄 focused suite 與未跑項目。

## 總結

下一階段重構的重點不是「再切更多檔案」，而是讓前一階段抽出的邊界真正成為單一來源與穩定介面。

最推薦先做的是 `DocumentController` single source of truth，因為它能移除 `BrailleFrame` 與 controller 之間的雙向同步，降低最核心 GUI class 的狀態風險。第二優先是 conversion completion policy，因為目前 manual convert、single export、batch export 仍透過 frame mutable fields 串接。第三優先是 document format descriptor，補上 import/export 擴充時的 OCP 缺口。
