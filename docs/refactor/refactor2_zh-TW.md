# Refactor 2 重構建議

日期：2026-07-07

## 範圍

本次檢視以目前的 `client/` 與 `server/` 原始碼為主，另外參考了近期
Superpowers 的設計與實作歷程：

- `docs/superpowers/specs/2026-07-06-settings-package-refactor-design.md`
- `docs/superpowers/plans/2026-07-06-settings-package-refactor.md`
- `docs/superpowers/specs/2026-07-06-platform-translation-adapters-design.md`
- `docs/superpowers/plans/2026-07-06-platform-translation-adapters.md`
- `docs/superpowers/specs/2026-07-06-dotexpress-settings-dialog-design.md`
- `docs/superpowers/specs/2026-06-30-import-export-conversion-design.md`
- `docs/superpowers/specs/2026-07-01-dual-view-braille-alignment-design.md`
- `docs/superpowers/history/2026-07-06-02-platform-translation-adapters/review_task.md`

最近的架構方向很明確：維持行為穩定、抽出小而明確的邊界、避免大規模改寫。
先前的 settings package 與 translation adapter 重構，已經讓程式碼逐步朝向
小型 model/persistence 模組、明確的 runtime 注入，以及以 wx UI 作為最外層的方向前進。

## 目前架構概況

程式碼目前已經有幾個不錯的邊界：

- `client/settings/` 已集中管理 settings model、staged state、persistence helper，
  以及多分類設定對話框。
- `client/adapters/translation/` 使用 Adapter 與 Strategy 風格的 runtime 選擇，
  封裝 liblouis、MathCAT 與 fallback translation。
- `client/documents/session.py` 包含純粹的文件選取決策邏輯。
- `client/documents/workspace.py` 集中管理文件封裝格式的持久化與 import/export helper。
- `client/ui/` 放置了小型且聚焦的 UI helper，包含選單、快捷鍵、區段導覽、
  字型支援與 dual-view frame 行為。
- `server/app/` 規模小，FastAPI app factory 與 persistence 分層也已足夠合理。

目前的主要壓力點集中在以下幾個位置：

- `client/gui.py` 約 1,700 行，處理 layout、menu 建立、文件 session state、
  檔案對話框、dictionary workflow、settings commit、conversion thread、
  export 批次流程、dual-view refresh 與 app lifecycle。
- `client/dialog.py` 約 900 行，混合了 dictionary entry 資料、dictionary CSV persistence、
  validation、virtual list 行為、symbol editor、name dialog 與 dictionary management UI。
- `client/settings/dialogs.py` 約 800 行，目前仍可接受，但若未來增加更多 settings category，
  而沒有進一步拆分 panel 建構邏輯，就會超出健康的模組邊界。
- `client/conversion/service.py` 已經有不錯的 request/output 邊界，但單一模組中仍同時負責
  inline math parsing、語言分段、dictionary replacement、runtime 呼叫、wrap 與
  ASCII 後處理。

## Design Patterns 檢視

### 已經運作良好的模式

Adapter / Strategy：

`client/adapters/translation/` 是目前最成熟的例子。native liblouis、
native MathCAT 與 fallback translator 透過小型 protocol 與 `TranslationRuntime`
共享介面。這種做法很適合作為未來其他邊界的參考，因為 conversion 不需要知道目前啟用的是哪一個 backend。

Facade：

`conversion.service.convert_text_with_alignment()` 與
`conversion.service.convert_text_for_output()` 已經扮演 facade，
封裝 dictionary mapping、language detection、translation、wrapping 與
ASCII conversion。這個方向是對的，但目前 facade 內部仍承擔太多步驟。

Template Method：

`settings.dialogs.SettingsPanel` 為每一個 settings category 提供一致的 lifecycle：
`make_settings`、`on_save`、`load_snapshot`、validation、activation 與 discard。
這對 wx settings panel 來說是合適的做法。

Command Descriptor：

`ui.action_menu.get_document_menu_descriptors()` 與
`ui.translation_menu.get_translation_menu_items()` 已經是小型的 command descriptor 來源。
這個模式值得延伸，進一步減少 `gui.py` 中的 menu wiring。

Decision Model：

`documents.session` 與 `dictionaries.actions` 內有純函式形式的 planning logic。
這是很好的輕量做法，可作為大型 domain service layer 之外的替代方案。

### 下一步適合導入的模式

Application Controller / Presenter：

建議引入一個不依賴 wx 的 document workflow controller，負責協調 document list state、
open/selected document name、rename/delete decision，以及 dual-view result cache。
讓 `BrailleFrame` 更接近單純的 view wiring 與 dialog 顯示層。

Service / Use Case：

將 import、export、conversion-launch workflow 抽成 use-case 函式或小型 class。
目前這些流程都散落在 `BrailleFrame`，橫跨 wx dialog、filesystem work、
conversion callback 與結果回報。

Command：

將 menu command 表示成 descriptor，包含 key、label、enabled-state query 與
handler name。這樣可以拿掉 `gui.py` 裡硬編碼的 menu binding map，也讓未來調整
menu 順序時不必改太多地方。

Pipeline / Chain of Responsibility：

將 conversion 拆成具名步驟：character mapping、inline math segmentation、
plain-text translation、math translation、merge、wrap、output formatting。
保留既有的 public conversion facade，但把內部步驟移到更容易測試的單元。

Repository / Gateway：

只有在呼叫端持續膨脹的前提下，才需要為 document workspace 與 dictionary storage
建立明確 repository。現有的函式模組本身沒有問題，但 `gui.py` 最好不要直接依賴太多底層函式。

ViewModel：

對 dictionary management row、export progress、conversion job state 等 UI 對外狀態，
使用小型 dataclass 表示。這有助於減少目前散落在 `BrailleFrame` 中的大量可變欄位。

## SOLID 檢視

### Single Responsibility Principle

最高風險：`client/gui.py` 中的 `BrailleFrame`

它目前同時負責 frame layout、document editing state、persistence call、
dictionary lifecycle callback、settings commit、export orchestration、
conversion threading、conversion completion behavior，以及 dual-view cache update。
這是未來每次變更都需要跑大範圍 GUI 測試、且容易產生手動回歸風險的主因。

第二高風險：`client/dialog.py`

它把 dialog class、dictionary CSV load/save 與 entry validation 混在一起。
其中一部分 domain logic 已經被測試直接使用，因此很適合抽出。

中度風險：`client/conversion/service.py`

這個模組在 conversion 領域內仍算有凝聚力，但多個職責被疊在同一條流程裡。
目前還能維持，但若未來增加新的 conversion mode 或 backend option，
就會變得比較難安全修改。

### Open/Closed Principle

優點：translation adapter 對新 backend 是開放的，只要增加新的 factory 與
translator implementation 即可。

弱點：新增一種 document import/export format，會同時牽動多個位置：
`documents.workspace.IMPORT_LOADERS`、wildcard/filter helper、export 分支，
以及 GUI export flow。若能改成 format registry 或 descriptor table，會更好維護。

弱點：新增 settings category 仍然會直接擴充 `settings/dialogs.py`。
目前 framework 已經備好，但在下一個 category 進來前，panel module 應進一步拆開。

### Liskov Substitution Principle

優點：`BrailleTextTranslator` 與 `MathSegmentTranslator` 的各種 implementation，
只要能回傳合法的 `TranslationResult` mapping，就可互相替代。

注意點：fallback text translation 刻意使用 `raw`，而不是 replacement `text`。
這是設計上正確的，但測試應持續清楚記錄這一點，因為它和 native mapping 行為
有刻意保留的差異。

### Interface Segregation Principle

優點：text 與 math translator protocol 已經分離。

弱點：`BrailleFrame` 目前透過大量 private method，實質上成為測試與 callback 的整合介面。
這表示測試依賴的是 frame 內部細節，而不是較小的 workflow 介面。

弱點：dictionary management callback 都經過 main frame 轉接，但該 dialog 實際上只需要一個
較窄的 dictionary workflow 介面。

### Dependency Inversion Principle

優點：conversion 依賴的是 `TranslationRuntime` protocol，而不是 native library。

弱點：`gui.py` 直接依賴許多具體的 filesystem、config、dictionary、document、
settings 與 conversion function。這使 GUI 測試需要大量 stub，也讓測試範圍過廣。

弱點：`dialog.py` 直接 import dictionary manager function。若未來 dictionary storage 改變，
UI 模組也會跟著被迫修改。

## 建議的下一階段重構

### 優先 1：從 `BrailleFrame` 抽出 Document Workflow Controller

建議：

新增 `client/documents/controller.py` 或 `client/app/document_controller.py`
模組，讓它在不依賴 wx control 的情況下，負責文件狀態轉換。

第一步可先負責：

- 保存 `documents`、`selected_document_name`、`open_document_name`
- open、select、rename、delete、delete all、replace document
- 維護 dual-view result cache 與 document name 的對應
- 回傳小型 result object，描述 UI 應如何更新
- 重用既有 `documents.session` 中的純邏輯 helper

先不要放進去的內容：

- wx dialog
- 真正的 `TextCtrl` 讀寫
- worker thread
- message box

為什麼這應該排第一：

- 它處理的是目前最大的 SRP 問題，但不需要改 conversion 或 storage。
- 可以在既有 `BrailleFrame` method 後方逐步導入，不必一次重寫。
- 可逐步把目前偏 GUI-heavy 的測試轉成較小的 controller test。
- 這也延續了 `documents.session` 已經驗證過可行的純邏輯模式。

建議第一刀：

- 抽出 `_open_document_by_name`、`_replace_document`、rename/delete cache update，
  以及 window title decision。
- `BrailleFrame` 只負責把回傳結果套用到 wx control。
- 補 focused test：document switch、rename 後 dual-view cache 保留、刪除 open document、
  delete all。

### 優先 2：從 `BrailleFrame` 抽出 Conversion Job Runner

建議：

把 conversion job state 與 thread lifecycle 抽到小型 service，例如
`client/conversion/jobs.py`。

第一步可先負責：

- 指派 job ID
- 保存 active worker state
- 在 worker thread 啟動 conversion
- 透過 callback 回傳 success/failure
- 將 `ConversionStageError` 正規化為 user-facing result object

保留在 `BrailleFrame` 的部分：

- 顯示與關閉 `ConvertingDialog`
- 啟用與停用 wx control
- 寫入 output text
- 顯示 message box

為什麼重要：

- Conversion 已被 manual convert、single export 與 export-all 共用。
- 目前這些行為由多個 frame mutable field 控制：
  `_convert_on_success`、`_convert_on_error`、`_convert_update_output`、
  `_convert_show_success`、`_convert_job_id`、`_convert_thread`、
  `_convert_dialog_timer`。
- 若有 job runner，export flow 會有更清楚的 API，callback coupling 也會下降。

建議模式：

- 用 Command 表示 `ConversionJobRequest`
- 用 Observer 風格 callback，或簡單的 `on_complete(job_id, result)`
- wx 專屬的 `wx.CallAfter` 保留在邊界層，或注入 scheduler function 方便測試

### 優先 3：把 Dictionary UI 的 Domain Logic 從 `dialog.py` 抽出

建議：

新增 `client/dictionaries/entries.py`，放 dictionary entry model、CSV
load/save、entry type normalization 與 entry validation。

從 `dialog.py` 移出的內容：

- `DictionaryEntry`
- `ENTRY_TYPE_OPTIONS`、`ENTRY_TYPE_LABELS`、`DEFAULT_ENTRY_TYPE`
- `normalize_entry_type`
- `load_dictionary_entries`
- Unicode braille 與 Bopomofo validation helper
- `SpeechSymbolsDialog` 使用的 dictionary entry CSV save logic

保留在 `dialog.py` 的內容：

- wx dialog class
- virtual list control
- button layout
- focus 與 message box 行為

為什麼重要：

- `dialog.py` 是第二大的檔案，且混合了 persistence 與 wx。
- `DictionaryManagementDialog` 已經是 callback-based lifecycle，和 Presenter 模式只差一步。
- 抽出 entry logic 後，未來 dictionary 功能就能有一套不依賴 wx 的 API。

### 優先 4：把 Conversion Service 拆成 Pipeline Steps

建議：

保留 `convert_text_with_alignment()` 作為 public facade，但把內部步驟移到更小的模組或函式。

候選模組：

- `conversion/segments.py`：inline math parsing 與 boundary spacing
- `conversion/plain_text.py`：dictionary application、language detection、
  table selection 與 plain text translation
- `conversion/wrapping.py`：merge、token cleanup、wrapping
- `conversion/output.py`：Unicode/ASCII output formatting

為什麼重要：

- Conversion 已經有不錯的測試，也已支援明確 runtime injection。
- 將內部 pipeline 拆開後，未來要加 output mode、語言策略或 math delimiter，
  就不用在同一個大 service 中修改。

Pipeline 要維持簡單，不要過度框架化：

- 一串純函式就夠了
- 不需要引入 generic pipeline engine
- 保留 `ConversionRequest` 與 `ConversionOutput`

### 優先 5：在增加更多 Settings Category 前，先拆 Settings Panel

建議：

`settings/dialogs.py` 不需要立刻拆。雖然它很大，但目前仍有一定凝聚性，
因為它主要包含一套 framework 與三個 panel。比較好的時機是下一個 settings category
確定要加入時再拆。

建議目標結構：

- `settings/dialog_framework.py`：`SettingsDialog`、`SettingsPanel`、
  `MultiCategorySettingsDialog`、accessibility helper
- `settings/panels/translation.py`
- `settings/panels/translation_tables.py`
- `settings/panels/view.py`
- `settings/dialogs.py`：組裝 `DotExpressSettingsDialog` 與對外 entry point

為什麼這項優先度較低：

- 最近的 settings refactor 已經大幅改善可發現性。
- 目前真正的痛點仍在 `gui.py` 與 `dialog.py`。
- 若現在就拆，較像是結構整理，而不是解決當前最迫切的維護壓力。

### 優先 6：Server 端重構先放低優先

建議：

下一輪 refactor 不要先花在 `server/app/`。

理由：

- `server/app/main.py`、`crud.py`、`database.py`、`models.py` 與 `schemas.py`
  規模都還小，對目前的 initialization service 已足夠清楚。
- 只有當 endpoint 或 version policy rule 持續增加時，才需要再加 service layer。

## 建議的執行順序

### Phase 1：Document Controller

目標：

在不改 UI 行為的前提下，降低 `BrailleFrame` 在 document-state 上的責任。

步驟：

- 先加 controller test，覆蓋 open/select/rename/delete/delete-all
- 引入 controller 與明確的 state/result dataclass
- 讓既有 `BrailleFrame` document method 改走 controller
- 所有 wx dialog 與 message box 仍保留在 `BrailleFrame`
- 執行 `tests.test_document_session`、`tests.test_document_workspace`、
  `tests.test_gui_document_flows`

### Phase 2：Conversion Job Runner

目標：

把 conversion threading 與 job state 從 frame UI 行為中拆開。

步驟：

- 先以 characterization test 固定 manual convert、export single、
  export all、stale job 與 error path 行為
- 抽出 job runner，並注入 scheduler 取代直接耦合 `wx.CallAfter`
- UI busy state 與 dialog 仍保留在 `BrailleFrame`
- 執行 `tests.test_conversion_service`、`tests.test_gui_document_flows`，
  以及 adapter/runtime 測試

### Phase 3：Dictionary Entry Module

目標：

讓 dictionary entry persistence 與 validation 可以在 wx 之外重用。

步驟：

- 把 entry model 與 CSV helper 搬到 `dictionaries/entries.py`
- 更新 `SpeechSymbolsDialog` 與 `DictionaryManagementDialog` 改用抽出的函式
- 補 focused test：entry validation 與 CSV roundtrip
- 執行 dictionary manager、dictionary management dialog 與 speech symbols 測試

### Phase 4：Conversion Pipeline Internal Split

目標：

在維持 facade 穩定的前提下，把 conversion 內部步驟縮小。

步驟：

- 先搬 inline math parsing，因為它最容易獨立
- 再搬 plain-text translation，同時保留 language table selection 測試
- 最後再搬 wrapping/output formatting
- 執行完整 conversion、language detection、dual-view 與 adapter 測試

## 測試策略

每一次抽取前，都應先補 characterization test。現有測試已經對高風險區域有不錯覆蓋：

- `tests.test_gui_document_flows`
- `tests.test_document_session`
- `tests.test_document_workspace`
- `tests.test_conversion_service`
- `tests.test_translation_runtime_provider`
- `tests.test_dictionary_management_dialog`
- `tests.test_speech_symbols_dialog`

對每一個 refactor slice：

- 先為新模組補 focused non-wx test
- 保留既有 GUI flow test 當 integration coverage
- 除非任務明確包含 localization 更新，否則不要改 user-facing string
- 從 `client/` 先跑 targeted suite，再視影響範圍擴大

## 不建議在下一輪做的重構

不要引入 dependency-injection container。

目前明確的 runtime injection 已足夠。容器只會增加儀式成本，無法直接解決目前 GUI 責任過重的問題。

不要一次把 `BrailleFrame` 全面改寫成 MVC。

Frame 雖然大，但大規模替換風險太高。應該一次抽一種 workflow，維持 wx 行為穩定。

不要把每一個模組立刻拆成更多 layer。

最近 settings 與 adapter 的經驗已證明：只有在結構真的對應到實際邊界時，package 化才有價值。
像 `server/app/crud.py` 或 `documents/session.py` 這種小模組，現在再拆只會降低可讀性。

不要太早把 conversion 變成 generic plugin system。

目前 adapter boundary 已足以支撐未來 backend 擴充。只有當真的出現多個 native backend，
或需要 user-selectable translation provider 時，再考慮 plugin system 才合理。

## 總結建議

下一階段重構應從 `BrailleFrame` 的責任抽離開始，第一優先是 document workflow controller。
這一項能在最少架構猜測的前提下，換來最大的維護性收益。之後依序是抽出 conversion job threading、
dictionary entry domain logic，最後再拆 conversion pipeline 內部步驟。這個順序符合本專案最近已驗證可行的方向：
針對既有行為抽出小邊界、維持對外行為穩定、並以 focused test 保護每一步重構。
