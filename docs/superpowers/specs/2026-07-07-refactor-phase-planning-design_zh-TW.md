# DotExpress 重構分期規劃設計

日期：2026-07-07

## 目標

根據 `docs/refactor/refactor2.md` 中已確認的優先項目，整理出一份可直接進入實作排程的分期重構方案。

此方案的前提是：維持目前對使用者可見的行為不變，同時優先降低 client 端程式碼中責任最集中的熱點區域。

## 已確認的優先順序

執行順序如下：

1. 從 `BrailleFrame` 抽出 document workflow controller
2. 從 `dialog.py` 抽出 dictionary entry 與 dictionary domain 邏輯
3. 從 `BrailleFrame` 抽出 conversion job orchestration
4. 拆分 `conversion/service.py` 內部 conversion pipeline

這是一個風險平衡過的順序：

- 先處理 `client/gui.py` 中最大的 SRP 問題
- 第二步插入一個耦合度較低的 dictionary/domain 拆分
- 第三步再處理 conversion threading 與 callback orchestration
- 最後才整理 conversion 內部流程，因為外圈 orchestration 在那之前會更乾淨

## 非目標

這次規劃不包含：

- 重設計 wx UI
- 變更使用者可見字串或 menu 行為
- 導入 dependency-injection container
- 一次把整個 app 改成完整 MVC
- 為 translation 加入 plugin system
- 在這一輪一併重構 server

## Phase 1：Document Workflow Controller

### 目標

在不改變目前 UI 行為的前提下，降低 `BrailleFrame` 在文件狀態決策上的責任。

### 範圍

新增 controller 模組，例如：

- `client/documents/controller.py`

此 controller 應負責保存：

- `documents`
- `selected_document_name`
- `open_document_name`
- 以 document name 為 key 的 dual-view result cache

此 controller 應負責處理：

- open/select decision
- replace document update
- rename state update
- delete state update
- delete-all state reset

### 保留在 `BrailleFrame` 的內容

- wx dialog
- `TextCtrl` 與 `ListCtrl` 的讀寫
- message box
- 檔案持久化呼叫時機
- 最後的 `SetTitle(...)`

### 第一刀建議

優先抽出這些流程：

- `_open_document_by_name`
- `_replace_document`
- rename 相關的 document 與 dual-view cache update
- delete / delete-all 的 state transition

### 驗收條件

- 使用者可見的 open/switch/rename/delete 行為不變
- dual-view cache 在 document rename/delete 後仍正確追蹤
- `tests.test_document_session`
- `tests.test_document_workspace`
- `tests.test_gui_document_flows`
  維持全綠

## Phase 2：Dictionary Entry Domain Extraction

### 目標

把 `client/dialog.py` 中和 dictionary entry 有關的 model、validation 與 CSV persistence 抽出，讓 wx dialog class 專注在互動本身。

### 範圍

新增：

- `client/dictionaries/entries.py`

從 `dialog.py` 移出的責任：

- `DictionaryEntry`
- entry type 常數與 normalization
- dictionary entry validation
- dictionary entry CSV load/save
- Bopomofo 與 Unicode braille validation helper

### 保留在 `dialog.py` 的內容

- wx dialog class
- button layout
- focus handling
- virtual list 行為
- message box 行為

### 驗收條件

- `SpeechSymbolsDialog` 行為不變
- `DictionaryManagementDialog` 行為不變
- entry validation 與 CSV roundtrip 有 focused test 覆蓋
- `tests.test_dictionary_management_dialog`
- `tests.test_speech_symbols_dialog`
- 其他 dictionary 相關測試維持全綠

## Phase 3：Conversion Job Runner

### 目標

把 conversion thread 與 callback orchestration 從 `BrailleFrame` 中抽出，但不改變 conversion 行為。

### 範圍

新增：

- `client/conversion/jobs.py`

加入明確的小型型別，例如：

- `ConversionJobRequest`
- `ConversionJobResult`
- `ConversionJobRunner`

此 job runner 應負責：

- job id 指派
- worker thread 執行
- success/failure result 傳遞
- stale-job 保護

### 保留在 `BrailleFrame` 的內容

- `ConvertingDialog`
- busy-state UI 的啟用/停用
- output text 更新
- conversion 成功後的 dual-view refresh
- success/error message box

### 驗收條件

- manual convert 行為不變
- export-triggered conversion 仍不顯示多餘的 manual success dialog
- stale job result 不會覆蓋更新的 job
- `tests.test_gui_document_flows`
- `tests.test_conversion_service`
  維持全綠

## Phase 4：Conversion Pipeline Internal Split

### 目標

在維持目前 conversion 對外 entry point 不變的前提下，把 conversion 內部步驟拆成較小模組。

### 範圍

以下 public API 保持不變：

- `ConversionRequest`
- `ConversionOutput`
- `ConversionStageError`
- `convert_text_with_alignment()`
- `convert_text_for_output()`

內部拆分可考慮這些模組：

- `conversion/segments.py`
- `conversion/plain_text.py`
- `conversion/wrapping.py`
- `conversion/output.py`

### 建議拆分順序

1. inline math segmentation 與 boundary spacing
2. plain-text translation flow
3. merge / token cleanup / wrap flow
4. output formatting 與 public error-message helper

### 驗收條件

- 對外 conversion entry point 不變
- dual-view alignment 行為不變
- `TranslationResult` 的 segment boundary 不被破壞
- `tests.test_conversion_service`
- language detection 相關測試
- dual-view 相關測試
- translation adapter/runtime 相關測試
  維持全綠

## 測試策略

每一期開始前，都應先以 characterization test 固定現行行為。

每個切分步驟都應遵守以下模式：

1. 先為新模組補 focused non-wx test
2. 再讓既有 integration code 改走新邊界
3. 保持現有 GUI flow test 全綠
4. 在抽取過程中避免改變 user-visible behavior

主要回歸測試組：

- `tests.test_gui_document_flows`
- `tests.test_document_session`
- `tests.test_document_workspace`
- `tests.test_conversion_service`
- `tests.test_translation_runtime_provider`
- `tests.test_dictionary_management_dialog`
- `tests.test_speech_symbols_dialog`

## 設計總結

這份分期規劃刻意避免大規模改寫，而是延續本 repo 近期已被驗證可行的重構模式：

- 一次抽出一個真正存在的責任邊界
- 保持行為穩定
- 讓 state 與 domain logic 往內收斂
- 在更小的抽象邊界成熟前，先讓 wx UI 繼續作為最外層協調者

第一個實作目標應該是 document workflow controller。它在最少架構猜測的前提下，能帶來最高的維護性收益。
