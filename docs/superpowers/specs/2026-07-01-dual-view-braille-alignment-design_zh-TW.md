# 雙視檢視點字對照視窗設計

## 摘要

這項變更會在 DotExpress 中新增一個可由選單開啟的「雙視檢視」浮動視窗，用來顯示目前文件的原文字元與對應點字碼之間的逐字對照。這個視窗使用 `wx.html2.WebView` 顯示 HTML 內容，並以文件最後一次成功轉換所產生的原始 `TranslationResult` 資料為基礎，建立未換行、未 token 綁定的字元級對照模型。

這個 viewer 的目標是幫助使用者檢查原文字元與點字輸出的對應關係，而不是取代既有的點字結果編輯區或最終輸出排版。因此它應獨立於既有 `bind_word_tokens()`、`wrap()` 與輸出框顯示邏輯之外，走一條專用的檢視資料管線。

## 目標

- 在 `檔案` 選單下新增 `雙視檢視` 指令。
- 以可關閉的 modeless 子視窗顯示目前文件的原文與點字逐字對照。
- 對照資料基於未 wrap、未 bind 的原始 `TranslationResult`。
- 支援整份文件由多個 `TranslationResult` 組成的情境，並保留 segment 邊界。
- 僅在明確的刷新時機更新 viewer：
  - 開啟 `雙視檢視` 時
  - 手動執行轉換成功後
  - 切換到另一份文件後
- 畫面只做檢視，不提供 HTML 內編輯。

## 非目標

- 不在 HTML viewer 內編輯原文或點字。
- 不讓 viewer 即時跟著來源文字每次輸入更新。
- 不將 viewer 建立在 wrap 後或 `bind_word_tokens()` 後的輸出結果上。
- 不重新設計既有點字結果編輯區。
- 不在這次變更中加入 React、Vue 或其他前端框架。

## 使用者可見行為

### 開啟方式

- `檔案` 選單下新增一個 `雙視檢視` 指令。
- 使用者點擊後，開啟一個附屬於主視窗的 modeless viewer 視窗。
- 如果 viewer 尚未開啟，建立新視窗。
- 如果 viewer 已開啟，將既有 viewer 帶到前景並刷新內容。

### 視窗行為

- viewer 是可關閉的獨立子視窗。
- 關閉 viewer 不影響主視窗、目前文件或點字結果。
- viewer 應只相對於 DotExpress 主視窗浮動，不應搶占其他應用程式的全系統最上層。
- viewer 可移動、可調整大小，並保留一般視窗行為。

### 顯示內容

- viewer 顯示目前文件最後一次成功轉換所得的字元級原文/點字對照。
- 每個原文字元各自對應一個 HTML 顯示單位。
- 每個顯示單位上方為原文字元，下方為該字元對應的點字片段。
- 整份文件可包含多個 translation segment，畫面應保留 segment 邊界。
- 換行與空白必須保留，以維持原文閱讀節奏。

### 更新時機

- 開啟 viewer 時，若目前文件已有最近一次成功轉換資料，立即顯示該內容。
- 手動執行轉換成功後，若 viewer 已開啟，刷新 viewer 內容。
- 切換到另一份文件後，若 viewer 已開啟，刷新為該文件最近一次成功轉換內容。
- 使用者僅修改來源文字、但尚未重新執行轉換時，viewer 不更新。

## 內部設計

### 視窗結構

- 在 `BrailleFrame` 中加入 viewer 視窗生命週期管理。
- 新增一個專用的 `DualViewFrame` 或同等責任的 GUI 類別，內部持有：
  - `wx.html2.WebView`
  - 初始 HTML shell 載入邏輯
  - 接收 JSON/view model 並重新 render 的橋接方法
- `DualViewFrame` 應為 modeless 子 `wx.Frame`，parent 指向主 `BrailleFrame`。

### 資料來源

- viewer 的真實資料來源是「目前文件最後一次成功轉換」所得到的原始 translation data。
- 這份資料必須保留未 wrap、未 bind 的 `TranslationResult`，不可只保留最終點字字串。
- 現有手動轉換流程在成功後，除更新點字結果區外，也應保存 viewer 所需的原始 translation data。
- 文件切換時，viewer 讀取該文件目前保存的最近一次成功轉換資料；若該文件尚無可用資料，viewer 顯示空內容或明確的無資料狀態。

### 文件級對照模型

- 新增一個純資料 builder，例如 `build_dual_view_model(...)`，輸入多個 `TranslationResult`，輸出供 HTML 使用的文件級 view model。
- builder 必須保留 segment 邊界，不應先把所有段落無差別壓平成單一大字串。
- 推薦輸出結構：

```json
{
  "segments": [
    {
      "source_text": "abc",
      "braille_text": "⠁⠃⠉",
      "items": [
        {
          "raw_index": 0,
          "raw_char": "a",
          "braille_start": 0,
          "braille_end": 1,
          "braille_text": "⠁"
        }
      ]
    }
  ]
}
```

- `segments` 對應文件中的多個 translation segment。
- `items` 為字元級對照單位，每個 item 只代表一個 raw char。

### 字元級 mapping 規則

- 對每個 `TranslationResult`：
  - `raw_to_braille_pos[i]` 作為第 `i` 個原文字元的 braille 起點。
  - 終點使用下一個字元的起點推算。
  - 最後一個字元的終點為 `len(braille)`。
- 每個字元的 braille 片段為 `braille[start:end]`。
- 一個原文字元可對應零個、一個或多個 braille cell。
- UI 主軸固定是原文字元，不反向以 braille cell 作為主顯示單位。

### 特殊字元與 segment 處理

- 空白字元必須保留為獨立顯示單位，不與前後字元合併。
- 換行字元不應作為一般字元卡片顯示，應轉為 HTML 斷行或新的 block 邊界。
- 若某字元對應的 `braille_start == braille_end`，允許顯示為空 braille 對照，占位樣式由前端決定。
- 數學 segment、字典替換 segment 與一般文字 segment 都走同一份 view model 結構，不在 HTML render 層推斷翻譯來源。

### HTML render 結構

- 第一版前端使用原生 HTML/CSS/JS，不引入 React/Vue。
- HTML 應以「文件 > segment > 字元卡片」三層結構 render。
- 每個字元卡片包含：
  - 原文字元區
  - 對應點字區
  - 供偵錯或未來 hover 使用的 metadata
- 不建議第一版使用 `<ruby>` 作為主要結構，因為空白、換行、長點字片段與細部樣式控制會較難處理。
- 改採自訂 `<span class="cell">` 類型結構更穩定。

### 更新管線

- viewer 只在以下三種情況刷新：
  - 開啟 `雙視檢視`
  - 手動轉換成功
  - 切換文件
- viewer 不應監聽來源文字編輯器的每次變更。
- 若 viewer 未開啟，主視窗不需要主動建構或推送 HTML。
- 若 viewer 已開啟但目前文件沒有最近一次成功轉換資料，viewer 顯示空狀態即可，不觸發額外轉換。

### 與既有轉換流程的關係

- viewer pipeline 與現有輸出 pipeline 並行存在。
- 現有 `translate_and_wrap_both()`、`bind_word_tokens()`、`reclean_token()`、`wrap()` 仍專門服務既有點字結果顯示與輸出。
- viewer 不應重用 wrap 後結果，避免喪失字元級 mapping。
- 若現有轉換流程目前未保留 viewer 所需的原始 translation data，應在成功轉換時加上保存行為，但不得改變既有輸出文字內容。

## 測試

### 單元測試

- 為文件級對照 builder 新增測試，覆蓋：
  - 單一 segment 的一般字元對照
  - 多個 segment 串接但保留 segment 邊界
  - 一個字元對多個 braille cell
  - 空白與換行處理
  - 空對照範圍處理
- 若新增文件層資料儲存結構，補上對「最近一次成功轉換資料」保存與切換的測試。

### GUI / 流程測試

- 更新或新增選單測試，確認 `檔案` 選單下存在 `雙視檢視`。
- 若目前測試架構允許，補上主視窗層級的流程測試，確認：
  - 開啟 viewer 會顯示目前文件資料
  - 手動轉換成功後會刷新 viewer
  - 切換文件後會刷新 viewer
  - 單純編輯文字不會刷新 viewer

## 風險與限制

- 若目前文件模型沒有保存「最近一次成功轉換的原始 `TranslationResult` 集合」，需要補一層資料保存責任，否則 viewer 無法在切換文件後重建精確對照。
- 多語言、字典替換與數學 segment 若在現有流程中混合產生不同型態的 `TranslationResult`，builder 必須統一處理其 `raw` 與 `braille` 結構，不可依賴單一 segment 來源假設。
- 如果未來需要顯示 wrap 後排版版面，應視為另一種 viewer mode，而不是覆蓋目前這條字元級未 wrap 對照模式。
- `wx.html2.WebView` 在不同平台 backend 能力不完全一致，因此第一版應避免依賴複雜雙向腳本橋接；純 render 為主較穩。

## 驗收標準

- `檔案` 選單下可開啟 `雙視檢視` 視窗。
- viewer 是可關閉的 modeless 子視窗，且不搶其他應用程式的全系統最上層。
- viewer 以原文字元為主單位，顯示上方原文、下方對應點字片段。
- viewer 顯示基於未 wrap、未 bind 的原始 translation data。
- 整份文件可由多個 `TranslationResult` 組成，viewer 仍能正確保留 segment 邊界並顯示完整內容。
- viewer 只在開啟、手動轉換成功、切換文件時更新。
- 單純編輯來源文字但未重新轉換時，viewer 不更新。
- 既有點字結果區與匯出流程行為不因 viewer 導入而改變。
