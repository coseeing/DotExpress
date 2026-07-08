# DotExpress Conversion Text Processing 重構設計

日期：2026-07-08

## 背景

目前 DotExpress 的 conversion 主流程已從 `client/conversion/service.py` 拆出 facade，但與「文字前後處理」直接相關的規則仍散落在多個模組：

- `client/conversion/output.py`
- `client/conversion/plain_text.py`
- `client/conversion/segments.py`
- `client/conversion/wrapping.py`
- `client/utils.py`
- `client/Bopomofo.py`
- `client/conversion/math_service.py`

現況下，若下一階段要加入「某些字元/字詞前處理替換」或「系統級文字規則」，開發者很容易同時修改 `output.py`、`plain_text.py` 與 `utils.py`。這表示 conversion-facing text processing 還沒有明確邊界。

同時，現有 repo 內也存在其他文字處理，例如：

- `client/documents/importers/html_to_ast.py`
- `client/documents/importers/markdown_renderer.py`
- `client/documents/importers/pdf_importer.py`

這些屬於文件匯入清洗，不屬於 braille conversion 前段規則。若將它們與 conversion text processing 一起重組，會讓範圍擴大且模糊。

因此，這次 spec 聚焦在 conversion-facing text processing 的 package-level 收斂，讓未來文字前處理有明確落點，同時避免過早重構 `client/translate.py`。

## Superpower Brainstorming 結論

這次先確認三個問題，再決定 spec 範圍。

### 問題 1：下一階段需求真正要解的是哪一層

下階段需求是「conversion 前的文字替換與前處理」，不是：

- 文件匯入清洗
- UI workflow
- `TranslationResult` 的 wrapping / token cleanup

因此本輪重構應聚焦在 conversion 前段，而不是整條輸出 pipeline。

### 問題 2：目前最大的技術風險是什麼

最大的風險不是單一檔案太大，而是 conversion 前處理的責任分散：

- char-level map
- dictionary replacement
- Bopomofo dictionary rule handling
- inline math segmentation
- language-aware plain text entry

這些責任分散後，新增一條新規則很容易只補到其中一條 conversion 入口，造成行為漂移。

### 問題 3：這一輪不要做哪些事情

這一輪不做：

- 重寫 `client/translate.py`
- 把 `client/conversion/wrapping.py` 併回 text package
- 抽 generic pipeline framework
- 將 importer normalization 併入同一 package
- 改動 user-visible behavior、output 規則或 UI

## 目標

將 conversion 前段文字處理收斂到一個小型 package，使以下需求有穩定落點：

1. 某些字元替換
2. 某些字詞取代
3. 系統級文字前處理規則
4. 未來可能的 rule 疊加或 debug 檢查

完成後應達成：

- conversion 前段規則不再散落在 `output.py`、`plain_text.py` 與 `utils.py`
- 新規則有單一 package-level 邊界可擴充
- 不需要先大拆 `translate.py`
- 現有 conversion public API 與使用者可見結果維持不變

## 非目標

- 不重寫 `TranslationResult`
- 不將 `wrap(width)` 邏輯搬離 `client/conversion/wrapping.py`
- 不改動 `client/conversion/math_service.py` 的 MathML 與 MathCAT 路徑
- 不整理文件匯入器的 whitespace normalization
- 不引入 plugin system、DI container 或可配置的 pipeline engine
- 不新增新的 conversion output mode

## 目前問題

### 問題 1：前處理與規則執行沒有明確邊界

目前 conversion 主流程中至少有以下處理：

- `BopomofoChar2Braille.csv` char-level map
- inline math 分段
- dictionary replacement
- Bopomofo dictionary target normalization
- language detection / table switching
- ASCII 後處理 map

這些步驟分散於不同模組，使開發者難以判斷新規則應該加在哪一層。

### 問題 2：`apply_dictionary()` 承擔過多責任

`client/utils.py` 中的 `apply_dictionary()` 同時負責：

- 讀取 dictionary CSV
- 讀取 Bopomofo 映射 CSV
- 處理 `type == "Bopomofo"` 的條目
- 依 `@` 切分 replacement parts
- 建立 atomic marker
- 對齊 raw / replacement segment
- 執行整體 replacement

這使它兼具 persistence、rule application 與 alignment protocol 的責任，不利於後續擴充與測試。

### 問題 3：兩條 conversion 入口共用規則但未共用邊界

`client/conversion/output.py` 目前在 `convert_text_with_alignment()` 與 `convert_text_for_output()` 兩個入口都各自做：

- `BopomofoChar2Braille` 前處理
- `Braille2Ascii` 後處理

雖然行為目前一致，但若新增新的 source text preprocess，很容易只補到其中一條路徑。

## 設計原則

- 只收斂 conversion-facing text processing
- 以 package split 與小型 orchestration function 解決邊界問題
- 保留現有 facade：`client/conversion/service.py`
- 不為了「模式完整性」導入 generic pipeline framework
- 新 package 內模組應盡量依賴純文字資料與小型 helper，而不是 `wx` 或 GUI state

## 評估過的方案

### A. 維持現況，只在原模組中繼續加 helper

優點：

- 改動最小

缺點：

- 規則邊界仍不明確
- 新前處理規則仍會散落
- 無法解決 `apply_dictionary()` 過胖問題

不採用。

### B. 建立小型 `client/conversion/text/` package，收斂 conversion 前段規則

優點：

- 與需求直接對齊
- 可保留既有 facade 與 wrapping
- 改動範圍有限，適合漸進式重構
- 提供後續文字替換的穩定落點

缺點：

- 需要同步更新既有 import 與測試 patch target

採用。

### C. 直接重寫 `client/translate.py` 並重整整條 conversion pipeline

優點：

- 理論上責任會更乾淨

缺點：

- 變更面過大
- 與本輪需求不對齊
- 對 alignment、dual-view、wrap 風險偏高

不採用。

## 決策

採用方案 B：新增 `client/conversion/text/` package，先收斂 conversion 前段文字規則與 orchestration；`client/conversion/wrapping.py` 保留不動；`client/translate.py` 不在這一輪處理。

## 目標結構

```text
client/
├── conversion/
│   ├── output.py
│   ├── plain_text.py
│   ├── service.py
│   ├── wrapping.py
│   └── text/
│       ├── __init__.py
│       ├── char_maps.py
│       ├── dictionary_rules.py
│       ├── math_segments.py
│       └── pipeline.py
└── utils.py
```

`utils.py` 在這一輪後不應再承擔 conversion text processing 的主要責任。新的 conversion 邏輯應直接從 `conversion/text/` 取用，舊的 conversion 相關入口應移除，不保留相容層。

## 模組責任

### `client/conversion/text/char_maps.py`

職責：

- 提供 char-level mapping helper
- 封裝 `BopomofoChar2Braille.csv` 與 `Braille2Ascii.csv` 這類單字元映射

應包含：

- 既有 `translate__mapping_char()` 的等價功能

不應負責：

- dictionary rule
- language detection
- wrapping

### `client/conversion/text/dictionary_rules.py`

職責：

- 套用 dictionary replacement
- 管理 atomic marker / bracket segment alignment
- 處理 `type == "Bopomofo"` 的 dictionary target 邏輯

應包含：

- `apply_dictionary()`
- `split_bracket_segments()`
- 相關 alignment helper
- string replacement helper

不應負責：

- `TranslationRuntime`
- wrapping / output formatting
- GUI 或 settings state

### `client/conversion/text/math_segments.py`

職責：

- 解析 `$...$` inline math segment
- 判斷 math / text segment 邊界是否需要補空白

應包含：

- `parse_inline_math_segments()`
- `segment_needs_boundary_space()`

不應負責：

- MathCAT translation
- MathML normalization

### `client/conversion/text/pipeline.py`

職責：

- 提供 conversion 前段的小型 orchestration function
- 串起 source preprocess、plain-text rule application 與 language-aware translation entry

第一版只需要小範圍 API，例如：

- `preprocess_source_text()`
- `apply_plain_text_rules()`

它應該收斂目前分散於 `output.py` 與 `plain_text.py` 的前段步驟，但不應變成完整 pipeline framework。

不應負責：

- threading
- GUI callback policy
- wrap / layout

### 保留 `client/conversion/wrapping.py`

這一輪保留現有責任：

- merge translation results
- cleanup translation result
- wrap output

原因：

- 這些邏輯已經比較偏 translation-result postprocess 與 output formatting
- 需求目前不在這一層
- 先不與前段 text package 混合，避免 scope 膨脹

## API 邊界

這一輪不追求大量新抽象，但需要建立清楚的 helper 落點。

### `preprocess_source_text()`

責任：

- 接收原始 source text
- 套用前置的 char-level preprocess
- 回傳供後續 segmentation / translation 使用的 text

第一版至少涵蓋目前的 `BopomofoChar2Braille` source map。

### `apply_plain_text_rules()`

責任：

- 套用 dictionary replacement
- 保留 raw / replacement alignment 資訊
- 讓後續 runtime translation 可以知道哪些 segment 屬於 atomic token

回傳型態不必一開始就做成很重的 class，但至少應該明確表達：

- raw side
- replacement side
- atomic segmentation

第一版可以沿用現有 `{"raw": ..., "replacement": ...}` 結構，只要把責任收進正確模組。

## 遷移策略

### Phase 1：建立 package 殼

- 新增 `client/conversion/text/__init__.py`

### Phase 2：搬移 `math_segments`

- 將 `client/conversion/segments.py` 的內容搬到 `conversion/text/math_segments.py`
- `client/conversion/service.py` 改從新位置匯入

### Phase 3：搬移 `char_maps`

- 將 `translate__mapping_char()` 搬到 `conversion/text/char_maps.py`
- `output.py` 與其他 conversion 路徑改從新位置匯入

### Phase 4：搬移 `dictionary_rules`

- 將 `apply_dictionary()`、`split_bracket_segments()` 與相關 helper 搬到 `conversion/text/dictionary_rules.py`
- `plain_text.py` 改用新位置

### Phase 5：建立 `pipeline.py`

- 將 source preprocess 與 plain-text rule orchestration 收斂到 `pipeline.py`
- `output.py` 與 `plain_text.py` 透過它共用前段流程

這五步應維持每一步都可獨立驗證，不需要一次完成全部。

## 相依方向

- `char_maps.py` 只依賴標準函式庫與 CSV 檔案
- `dictionary_rules.py` 依賴標準函式庫與 Bopomofo normalization helper
- `math_segments.py` 為純文字分段邏輯
- `pipeline.py` 可依賴 `char_maps.py`、`dictionary_rules.py` 與 `languageDetection`
- `wrapping.py` 依然依賴 `TranslationResult`

`pipeline.py` 不應反向依賴 `wrapping.py` 或 GUI module。

## 對現有 public behavior 的要求

這次重構必須保留以下行為：

- conversion public API 不變：
  - `convert_text_with_alignment()`
  - `convert_text_for_output()`
- dictionary replacement 對 dual-view alignment 的既有行為不變
- `BopomofoChar2Braille` source preprocess 行為不變
- `Braille2Ascii` output map 行為不變
- inline math segmentation 與 boundary space 行為不變
- 現有測試若 patch 舊目標，必須同步改到新模組位置

## 測試策略

這次重構碰到文字轉換前段，屬於業務核心功能。實作時必須先補 characterization tests，再搬移模組；測試應證明新邊界與現行行為一致，而不是只證明新檔案可匯入。

每一步搬移後至少執行 focused tests：

- `tests.test_conversion_service`
- `tests.test_utils`
- `tests.test_conversion_segments`
- `tests.test_dual_view_model`
- `tests.test_gui_document_flows`

必須覆蓋的現行行為：

- `BopomofoChar2Braille.csv` source preprocess 仍在 translation 前套用。
- `Braille2Ascii.csv` 只在 `output_mode == "ascii"` 時套用，且發生在 braille wrapping 後。
- `convert_text_with_alignment()` 與 `convert_text_for_output()` 共享相同 source preprocess 語意。
- `$...$` inline math segmentation、escaped dollar、unclosed dollar fallback 與 math/text boundary space 行為不變。
- dictionary replacement 仍依來源字串長度由長到短套用，避免短詞先替換造成重疊。
- dictionary replacement 不會再次改寫已標記的 atomic replacement output。
- dictionary `type == "Bopomofo"` 仍會經過 zhuyin normalization 與 Bopomofo-to-braille mapping。
- `@` 分隔的 multi-part braille replacement 仍能與來源字元對齊。
- raw / replacement segment 的 atomic flag 必須一致，不一致時仍拋錯。
- language detection 與 table switching 行為不變，切換表格時必要的 boundary space 仍會插入。
- fallback text translator 仍以 `raw` 建立結果，而不是 replacement text。
- dual-view model 看到的 raw / braille alignment 與搬移前一致。

建議新增或補強的 characterization tests：

- `tests.test_conversion_text_char_maps`：覆蓋 char map CSV 欄位驗證、單字元轉換、空 target 刪除、非單字元 source 忽略、ASCII output map。
- `tests.test_conversion_text_dictionary_rules`：覆蓋一般 replacement、長詞優先、atomic marker 保護、Bopomofo dictionary、`@` multi-part alignment、缺少 dictionary 檔案 fallback。
- `tests.test_conversion_text_math_segments`：覆蓋 inline math、escaped dollar、unclosed dollar、相鄰 text/math boundary space。
- `tests.test_conversion_text_pipeline`：覆蓋 source preprocess 被兩條 conversion 入口共用，並驗證 plain-text rule application 回傳 raw / replacement / atomic segmentation。

建議的對應驗證：

### 搬移 `math_segments.py` 後

- 確認 text / math segment 順序與 boundary space 不變
- 執行 `tests.test_conversion_text_math_segments`

### 搬移 `char_maps.py` 後

- 確認 source preprocess 與 ASCII output map 不變
- 執行 `tests.test_conversion_text_char_maps`

### 搬移 `dictionary_rules.py` 後

- 確認 atomic segment alignment 不變
- 確認 Bopomofo dictionary multi-part 對齊不變
- 執行 `tests.test_conversion_text_dictionary_rules`

### 建立 `pipeline.py` 後

- 確認兩條 conversion 入口仍共用相同 preprocess semantics
- 執行 `tests.test_conversion_text_pipeline`

## 風險與取捨

### 風險 1：搬移函式時破壞既有 patch 目標

部分測試可能 patch 既有 import 位置。這一輪的做法不是保留相容 alias，而是同步更新測試與呼叫端，讓新邊界一次到位。

### 風險 2：`dictionary_rules.py` 第一版仍偏胖

這是刻意接受的取捨。第一版目標是先修正 package boundary，而不是一次把 rule persistence 與 rule execution 全拆乾淨。

### 風險 3：`pipeline.py` 可能長成 generic engine

這一輪必須刻意避免。`pipeline.py` 只能是幾個小型 orchestration function，不應變成可配置、可註冊、可動態組裝的 framework。

## 成功標準

完成後應能滿足：

1. 新的 conversion text preprocess / replacement 規則有明確模組落點。
2. `client/utils.py` 不再是 conversion 文字規則的主要承載點。
3. `client/conversion/output.py` 與 `client/conversion/plain_text.py` 不再各自維護分散的前段規則細節。
4. 不需要先修改 `client/translate.py` 就能支持下一階段需求。
5. 既有 focused tests 與 GUI flow regression tests 仍通過。
