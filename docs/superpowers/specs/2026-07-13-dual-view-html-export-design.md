# 雙視檢視 HTML 匯出設計

## 目標

在文件列表的「匯出」與「匯出全部」子選單中新增雙視檢視 HTML 匯出格式，讓使用者可以保存目前雙視檢視所呈現的來源文字與點字對照內容。

## 使用者介面

兩個匯出子選單都使用相同順序與標籤：

1. 封裝檔 DEP
2. 點字檔 BRL
3. 雙視檔 HTML

格式標籤採「描述＋大寫副檔名」；實際檔案副檔名使用 `.html`。英文介面對應為 `Package DEP`、`Braille BRL`、`Dual View HTML`。

## 實作設計

- 在文件格式 registry 新增可匯出的 `html` descriptor，副檔名為 `.html`，不直接要求既有 `document.braille`，因為 HTML 必須使用雙視檢視的對齊資料。
- 新增 HTML writer，接收 GUI 傳入的文件對應雙視結果，將其建立為 model 後交給既有 `render_dual_view_html()` 產生完整 HTML，寫入 UTF-8 檔案；不把暫存對齊資料加入 `Document` 持久化模型。
- GUI 單一匯出與批次匯出沿用既有 format registry、檔名、副檔名修正、轉換失敗與結果摘要流程；HTML 匯出在缺少對齊資料時使用與雙視檢視相同的空狀態內容，若尚未有轉換資料則先完成轉換。
- 匯出對話框的 wildcard 與格式標籤由 descriptor 驅動，避免新增第三套格式判斷。
- 將動態選單標籤加入 gettext markers，並更新繁體中文翻譯檔；編譯 `.mo` 依專案既有流程處理。

## 測試策略

先新增會失敗的測試，涵蓋：

- registry 回傳 HTML descriptor、`.html` 副檔名與 writer 能力。
- HTML writer 以雙視檢視 renderer 輸出 UTF-8 完整 HTML。
- 選單兩個匯出子選單都包含三個描述格式且順序正確。
- 單一與批次匯出使用 `.html` 副檔名並沿用既有成功／失敗流程。

接著以最小實作使測試通過，最後執行受影響測試與完整 client 測試範圍。
