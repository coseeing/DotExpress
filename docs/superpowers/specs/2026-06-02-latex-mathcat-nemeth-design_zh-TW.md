# 使用 MathCAT 的 LaTeX 數學區塊轉換

## 摘要

將 DotExpress 目前 `$...$` 數學區塊使用的 placeholder 流程，替換為真正可執行的行內數學轉換流程：

1. 讀取數學區塊中的 LaTeX 原始內容
2. 使用 `latex2mathml` 將 LaTeX 轉為 MathML
3. 使用內建的 MathCAT runtime 將 MathML 轉為 Nemeth 點字
4. 將結果以單一 token 的 `TranslationResult` 形式合併回既有轉譯流程

這個階段是在前一份數學區塊偵測設計的基礎上，進一步把數學轉換做成可在 Windows 執行期真正運作的功能。

## 目標

- 將 `$...$` 區塊視為 LaTeX 數學輸入。
- 使用 `latex2mathml` 將 LaTeX 數學轉為 MathML。
- 使用 MathCAT 將 MathML 轉為 Nemeth 點字。
- 將 DotExpress 所需的 MathCAT runtime 與資源直接內建，而不是依賴外部已安裝的 NVDA。
- 維持數學區塊以單一 token 的 `TranslationResult` 表示。
- 只有在文字與數學區塊交界兩側都不是空白時，才插入邊界空白。
- 任何數學轉換階段失敗時，整次轉換直接失敗。

## 非目標

- 本階段不支援 `\\(...\\)` 等其他數學分隔符。
- 本階段不提供數學轉換失敗時保留原始 LaTeX 的 fallback 行為。
- 本階段不保證非 Windows 執行環境可用。
- 本階段不新增讓使用者選擇其他數學點字來源的設定。
- 本階段不實作數學區塊內部更細的 token 切分。

## 目前脈絡

DotExpress 目前已具備：

- 在 `client/conversion/service.py` 中做 `$...$` 的最上層數學區塊偵測
- 在 `translate_with_language()` 中分流處理 `text` / `math` 區塊
- 目前 `math` 區塊仍走 placeholder translator，並包成單一 token 的 `TranslationResult`

外部參考來源如下：

- Access8Math 在 LaTeX 轉 MathML 時使用 `latex2mathml.converter.convert()`
- NVDA 的 MathCAT 提供 `getBrailleForMathMl(mathml: str) -> str`，底層流程是先設定 MathML，再向 MathCAT 取得點字輸出

這些參考提供了目標流程，但 DotExpress 不會依賴外部已安裝的 NVDA 環境，而是內嵌自己需要的最小 MathCAT adapter/runtime。

## 設計

### 1. 保留 conversion/service.py 中的區塊分流架構

最上層的區塊模型維持不變：

- `text` 區塊繼續走既有語言偵測與 liblouis 文字轉譯流程
- `math` 區塊改視為 LaTeX 數學轉換請求

`translate_with_language()` 仍負責：

- 區塊分流
- 邊界空白插入
- 合併順序

它不應直接承擔 MathCAT runtime 初始化等細節責任。

### 2. 新增獨立的數學轉換模組

新增一個聚焦的模組，例如 `client/conversion/math_service.py`，對外介面保持精簡：

- `latex_to_mathml(latex_text: str) -> str`
- `mathml_to_nemeth_braille(mathml_text: str) -> str`
- `translate_math_segment(latex_text: str) -> str`

責任如下：

- `latex_to_mathml()` 封裝 `latex2mathml` library 與 DotExpress 所需的後處理
- `mathml_to_nemeth_braille()` 委派給內建的 MathCAT adapter
- `translate_math_segment()` 負責完整的 `LaTeX -> MathML -> Nemeth braille` 流程，並在失敗時拋出明確錯誤

這樣可讓 `conversion/service.py` 維持在 orchestration 層，而不是把數學 runtime 細節混進去。

### 3. 在 DotExpress 內建最小可用的 MathCAT runtime

DotExpress 不應依賴使用者機器另外安裝的 NVDA 或 MathCAT 環境。

因此需要從 NVDA MathCAT source 與所需 runtime 檔案中，整理出 DotExpress 自己可攜帶的最小執行環境，包括：

- 初始化 MathCAT 並呼叫 braille output 所需的 Python adapter 邏輯
- 必要的動態函式庫與 runtime 檔案
- 點字產生所需的 MathCAT rules / resources

設計限制：

- 內嵌範圍應盡量縮小
- 不應複製與 DotExpress 無關的 NVDA 呈現或 UI 程式
- DotExpress 對外只透過一個小型 adapter API 存取 MathCAT

建議的 DotExpress-facing adapter 介面例如：

- `get_braille_for_mathml(mathml_text: str) -> str`

這個 adapter 負責：

- 定位內建 runtime 檔案
- 做一次性的 runtime 初始化
- 設定輸出為 Nemeth 點字所需的 preference
- 將 runtime/library 例外轉成一般 Python 例外

### 4. 正式支援範圍限定為 Windows packaged runtime

這項功能以 Windows 執行期為正式支援目標。

支援策略如下：

- Windows 打包後的 DotExpress app：正式支援
- 非 Windows 的開發環境：允許用 stub、skip 或有限的測試覆蓋
- 跨平台 MathCAT runtime 支援：不在本階段範圍內

這與專案現有的 Windows 打包模式，以及既有點字原生相依套件的前提一致。

### 5. 將數學輸出包成單一 token 的 TranslationResult

數學區塊在合併後的轉譯結果中，仍維持原子化表示。

表示方式維持為：

- `raw = [latex_text]`
- `braille = list(nemeth_braille_output)`
- `raw_to_braille_pos = [0]`
- `braille_to_raw_pos = [0] * len(braille)`

這延續了前一版已確認的行為，也避免過早定義 LaTeX 數學式內部過細的游標或 token 對應。

### 6. 只有必要時才插入邊界空白

邊界空白由 conversion pipeline 處理，不交給 MathCAT。

規則如下：

- 當兩個最上層相鄰區塊接壤時
- 且至少其中一側是 `math`
- 且左側區塊尾端不是空白
- 且右側區塊開頭不是空白
- 才在它們之間插入一個普通空白 token 再合併

範例：

- `計算$1+2$的值` -> `計算 ⟨math⟩ 的值`
- `計算 $1+2$ 的值` -> 不額外補空白
- `$x+1$測試` -> `⟨math⟩ 測試`

這裡刻意和目前語言切換時只看左側的空白邏輯不同，因為數學邊界需要同時看左右兩側，才能避免補出重複空白。

### 7. 錯誤處理採 fail-fast

任何數學轉換失敗都會中止整次 conversion。

失敗點包括：

- LaTeX 轉 MathML 失敗
- MathCAT runtime 初始化失敗
- MathCAT 將 MathML 轉點字失敗

行為如下：

- 透過既有 conversion error 路徑向上拋出
- 不回退到原始 LaTeX
- 不輸出部分 placeholder 結果
- 不靜默略過數學區塊

對於以轉錄精確性為重點的工具來說，明確失敗比靜默產出錯誤點字更安全。

## 測試

### 單元測試

新增或更新測試以驗證：

- 數學區塊會依序呼叫 `LaTeX -> MathML -> MathCAT`
- 文字與數學交界只有在兩側都不是空白時才補空白
- 原本已存在的空白不會被重複補上
- 數學區塊仍以單一 token `TranslationResult` 合併
- LaTeX 轉換失敗時，conversion error 會向上傳遞
- MathCAT 點字轉換失敗時，conversion error 會向上傳遞

這些測試應使用 math adapter 的 mock/stub，以便在非 Windows 的開發環境中維持穩定。

### Windows 執行期驗證

仍需要在 Windows 環境做手動或環境相依驗證，確認：

- 內建 MathCAT runtime 可正確初始化
- 代表性 LaTeX 式子可正確輸出 Nemeth 點字
- 打包後 app 的資源路徑可正確定位

建議覆蓋至少包含：

- 基本算式，例如 `$1+2$`
- 分數，例如 `$\frac{1}{2}$`
- 上下標，例如 `$x^2$`、`$a_1$`
- 中文文字與 LaTeX 數學混排

## 取捨

### 為什麼不直接把真正的數學流程塞回 conversion/service.py？

因為 runtime 責任已經改變。真正的 MathCAT 相依包含初始化、打包、例外語意，值得有清楚的模組邊界。

### 為什麼不依賴外部已安裝的 NVDA 或 MathCAT？

那會讓 DotExpress 的執行結果依賴使用者機器上的外部狀態，不利於打包與部署的一致性。對桌面應用而言，直接攜帶所需 runtime 更合適。

### 為什麼數學區塊仍維持單一 token？

因為目前需求重點是先讓真正的 Nemeth 輸出可用，而不是同時重設數學區塊內部的細緻游標對應。維持數學原子化表示，可以在控制範圍內完成這一階段。

## 後續延伸

未來可能的後續工作：

- 支援 `\\(...\\)` 分隔符
- 細化數學區塊內部的游標 / token 對應
- 補齊內建 MathCAT 資產的 Windows 打包文件
- 若未來有需要，再加入更多 MathCAT 組態或其他點字碼支援
