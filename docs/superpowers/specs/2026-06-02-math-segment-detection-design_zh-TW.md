# 轉譯流程中的數學區塊偵測

## 摘要

在 DotExpress 的來源文字中，加入第一階段對未跳脫美元符號所包覆之行內數學內容的支援。數學區塊將在 `translate_with_language()` 中被辨識，並導向專用的 placeholder 數學轉譯函式，而不是走一般文字的轉譯流程。

這個階段只實作偵測與流程串接，尚不實作真正的數學點字規則。

## 目標

- 使用 `$...$` 偵測行內數學區塊。
- 採用非貪心語意，使同一行中的多個數學區塊能各自獨立處理。
- 將 `\$` 視為一般字面的美元符號，而不是數學分隔符。
- 將未成對的開頭 `$` 視為一般文字。
- 將偵測到的數學區塊導向 placeholder 數學轉譯函式。
- 將每個數學區塊表示成單一 token 的 `TranslationResult`，以便與現有的一般文字轉譯結果合併。

## 非目標

- 本階段不支援 `\\(...\\)` 分隔符。
- 本階段不實作真正的數學點字轉譯規則。
- 本階段不新增數學模式相關 GUI 控制項或使用者設定。
- 本階段不定義數學內容內部的字元層級游標對應。

## 目前脈絡

DotExpress 目前的文字轉點字流程如下：

1. `client/gui.py` 建立 `ConversionRequest`。
2. `client/conversion/service.py:convert_text_for_output()` 先做前置字元映射，之後呼叫 `translate_and_wrap_both()`。
3. `translate_and_wrap_both()` 呼叫 `translate_with_language()`。
4. `translate_with_language()` 使用語言偵測、字典套用與 liblouis 轉譯，產出合併後的 `TranslationResult`。

因此，`translate_with_language()` 是整合數學區塊分流的合適位置。它本來就負責決定不同內容片段要如何轉譯與合併。

## 設計

### 1. 加入行內數學區塊 parser

在 `client/conversion/service.py` 中加入一個 helper，線性掃描文字並輸出依序排列的區塊，例如：

- `{"type": "text", "text": "..."}`
- `{"type": "math", "text": "..."}`

parser 規則如下：

- 只有未跳脫的 `$` 可以開啟或結束數學區塊。
- `\$` 會保留在目前區塊的文字內容中。
- 由於第一個合法的結尾 `$` 就會結束目前數學區塊，因此整體行為等同非貪心比對。
- 同一段輸入中可支援多個數學區塊。
- 如果某個開頭 `$` 找不到對應的結尾 `$`，則回退為一般文字，保留該 `$` 及其後續內容。

範例：

- `計算$1+2$的值` -> `text("計算")`, `math("1+2")`, `text("的值")`
- `計算$1+2$和$3+4$` -> `text("計算")`, `math("1+2")`, `text("和")`, `math("3+4")`
- `$1+\\$2$` -> `math("1+\\$2")`
- `計算$1+2` -> `text("計算$1+2")`

### 2. 加入 placeholder 數學轉譯函式

在 `client/conversion/service.py` 中加入一個介面明確的 placeholder 函式：

```python
def translate_math_placeholder(math_text: str) -> str:
```

輸入：

- 僅包含數學內容本體，不含外層分隔符。

輸出：

- 一段 placeholder 點字字串，用來驗證整體流程已可端到端串通。

此函式會刻意維持獨立，讓下一階段可以直接替換成真正的數學點字轉譯邏輯，而不必改動區塊切分或分流架構。

### 3. 將數學輸出包成單一 token 的 TranslationResult

加入一個 helper，將 placeholder 數學輸出包成可與現有合併邏輯相容的 `TranslationResult`。

表示方式如下：

- `raw = [math_text]`
- `braille = list(placeholder_output)`
- `raw_to_braille_pos = [0]`，適用於輸出非空的情況
- `braille_to_raw_pos = [0] * len(braille)`

若 placeholder 輸出為空：

- `raw = [math_text]`
- `braille = []`
- `raw_to_braille_pos = [0]`
- `braille_to_raw_pos = []`

這樣會將整段數學內容視為單一原子 token。這符合本階段範圍，也避免過早定義尚未成熟的數學內容內部對應規則。

### 4. 在 translate_with_language() 中做分流

更新 `translate_with_language()`，讓它先把輸入文字切成最上層的 `text` / `math` 區塊。

分流規則如下：

- `text` 區塊繼續走現有流程：
  - 語言偵測
  - 字典套用
  - `split_bracket_segments()`
  - `translate()` / `translate_as_single_token()`
- `math` 區塊不走語言偵測與 liblouis 一般文字轉譯。
  - 直接交給 `translate_math_placeholder()`
  - 再包成單一 token 的 `TranslationResult`

所有產出的 `TranslationResult` 會沿用既有串接行為依序合併。

### 5. 維持後續流程不變

以下部分本階段不預計修改：

- `convert_text_for_output()`
- `translate_and_wrap_both()` 中的換行包裝行為
- 輸出模式處理
- GUI 儲存與匯出流程

這些流程原本就消費合併後的轉譯結果，因此會自然繼承數學區塊支援。

## 錯誤處理

- 非法或未成對的 `$` 分隔符不拋出錯誤，而是視為一般文字。
- 跳脫美元符號維持為字面內容。
- placeholder 數學轉譯不應靜默丟失內容。未來若在數學轉譯階段失敗，應沿用既有例外處理流程回報 conversion error。

## 測試

在 `client/tests/test_conversion_service.py` 中新增聚焦單元測試，覆蓋：

- 沒有數學區塊的一般文字
- 單一 `$...$` 數學區塊
- 同一字串中多個 `$...$` 數學區塊
- 數學內容中的跳脫美元符號
- 數學區塊外的跳脫美元符號
- 未閉合開頭 `$` 回退為一般文字
- 驗證一般文字與數學區塊會依原始順序處理的 conversion flow
- 驗證數學區塊會被包成單一 token 的 `TranslationResult`

本階段測試重點應放在 parser 行為與分流行為，而不是實際數學點字正確性。

## 取捨

### 為什麼不放在 convert_text_for_output()？

如果只是做純字串替換原型，這樣會比較簡單，但它會把數學視為最終輸出前的例外處理，而不是轉譯流程中的一級內容型別。

將分流放在 `translate_with_language()`，能讓責任邊界與現有的區塊式轉譯邏輯保持一致，也能降低未來重構成本。

### 為什麼現在不切分數學內容內部 token？

目前尚未定義數學點字內容應如何切分。先把整段數學區塊視為單一原子 token，可以與現有合併邏輯相容，同時保留未來細化設計的空間。

## 後續延伸

下一階段可以將 `translate_math_placeholder()` 替換成真正的數學轉譯器；若有需要，也可以再把數學區塊的 `TranslationResult` 對應從單一 token 細化成更完整的內部結構。
