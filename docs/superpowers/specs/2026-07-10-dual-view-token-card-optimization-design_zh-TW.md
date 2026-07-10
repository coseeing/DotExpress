# 雙視檢視 Token 卡片優化設計

日期：2026-07-10

## 摘要

這項變更會調整 DotExpress 的雙視檢視，讓畫面上的對照單位與
`TranslationResult` 真正提供的對映粒度一致。現行 dual view model 會把每個
`raw` element 再拆成逐字卡片，導致多字 token 的整段點字只出現在第一張卡片，
後續字元卡片則顯示空對映。這對字典替換、群組文字 token 與數學區段都會造成誤導。

新的設計改為預設「一個 `TranslationResult.raw` element 對一張卡片」。同時保留
`TranslationResult` 層級的 segment 邊界、移除 segment container 上會產生 named
region 的 `aria-label`，並將數學卡片的來源內容改為 MathML DOM render，而不是
原始 LaTeX 字串。

## Superpower Brainstorming 結論

本 spec 依照撰寫前已確認的需求制定：

- 視覺單位是一個 `TranslationResult.raw` element，而不是 element 內的單一字元
- 每個 `TranslationResult` 仍會渲染成一個 segment container
- segment container 保持 `<section class="segment">`，但不再加上 `aria-label`
- 只有 raw element 剛好等於 `" "` 或剛好等於 `"\n"` 時才套用特殊空白處理
- 數學來源會以產生出的 MathML DOM content 顯示在對應點字上方

## 目標

- 讓 dual view 的每張卡片對應一個 `TranslationResult.raw` element。
- 停止把多字 `raw` element 拆成逐字卡片。
- 在 HTML 結構中保留 `TranslationResult` 的 segment 邊界。
- 移除目前會讓每個 segment 變成 named region 的 `aria-label`。
- 以 MathML DOM output 顯示數學卡片的來源內容。
- 保持既有 session 內刷新與快取行為不變。

## 非目標

- 不更動轉譯流程的 wrap 後點字輸出。
- 不在單一數學 token 內新增更細的內部對映。
- 不在缺乏更細 mapping 的情況下重切或重解釋 `raw` element。
- 不重做 dual view 視窗生命週期或選單入口。
- 不把 dual view 對照資料持久化到文件封裝格式。

## 問題描述

目前 `client/dual_view/model.py` 會先用每個 `raw` token 的
`raw_to_braille_pos` 範圍取得點字區段，再把該 token 展開成逐字卡片。對於像
`"我們"` 這種只對應一段點字範圍的 token，第一張卡片會拿到整段點字，第二張卡片
則顯示空對映。畫面看起來像是第二個字沒有點字，但實際資料只是說整個 token 對應到
那一段點字。

相同問題也會出現在：

- 故意綁定多個來源字元的字典替換
- 以 atomic 方式產生的文字 token
- 目前作為單一 token mapping 的數學區段

另外，現行 HTML renderer 會在每個 `<section>` 上輸出
`aria-label="Translation segment"`，這通常會在可及性樹中形成 named region。
這個 landmark 在此情境中沒有實際價值。

## 使用者可見行為

### 卡片粒度

- 每張 dual-view 卡片代表一個 `TranslationResult.raw` element。
- 卡片的來源區顯示完整 raw element，而不是其中單一字元。
- 卡片的點字區顯示該 raw element 對應的完整點字切片。

範例：

```python
raw = ["我們", "這", "一家"]
braille ranges = ["b1", "b2", "b3"]
```

Dual view 應顯示：

- `我們 / b1`
- `這 / b2`
- `一家 / b3`

不得顯示成：

- `我 / b1`
- `們 / ∅`

### 空白與換行行為

只有當 `raw` element 本身就是單一空白字元或單一換行字元時，dual view 才保留特殊
處理：

- `" "` 會顯示為獨立空白卡片。
- `"\n"` 會顯示為斷行節點，而不是一般卡片。

除上述情況外，其他 `raw` element 一律維持整體單一卡片，即使字串內容本身包含空白
或換行也不拆分。這樣可以避免在 `TranslationResult` 並未提供更細對映邊界時，畫面
自行捏造不存在的 alignment boundary。

範例：

- `["我們", " ", "這一家"]` 會顯示為三張卡片。
- `["我們", "\n", "這一家"]` 會顯示為一張卡片、一個斷行，再一張卡片。
- `["我們 這 一家"]` 會顯示為一張卡片。
- `["我們\n"]` 會顯示為一張卡片。

### Segment 容器

- 每個 `TranslationResult` 仍會渲染在一個 `<section class="segment">` 容器中。
- Segment 容器不再加上 `aria-label`。
- 可以保留視覺上的 segment 樣式，但不得再形成 named region。

### 數學卡片

- 數學區段仍以「每個 `raw` element 一張卡片」為單位。
- 數學卡片的來源區顯示由原始 LaTeX 來源轉出的 MathML DOM render 結果。
- 點字區顯示既有的數學點字轉譯結果。
- 不會再把數學卡片內部拆成更小的符號卡片。

## 資料模型設計

### 1. Segment 範圍保持不變

Dual view 繼續使用最近一次成功轉換時保存的未 bind `TranslationResult`。每個輸入
`TranslationResult` 在輸出 model 中對應一個 segment。

因為數學呈現現在需要知道 segment 是否來自 math translation path，dual-view 快取
payload 必須用一個小型 descriptor 包住每個 result，並保存 source kind：

```python
@dataclass(frozen=True)
class DualViewSegment:
    result: object
    source_kind: str  # "text" or "math"
```

Wrapping 與 display-output pipeline 應繼續操作原本的 `TranslationResult`。這個
descriptor 只供 dual-view cache 與 model builder 使用。

### 2. Item 粒度由字元級改為 raw-element 級

Dual-view model 不應再把單一字元當成預設 item 單位。每個 item 應對應到一個
`raw` element 及其對應的點字範圍。

Model 應攜帶足夠資訊供 rendering 與測試使用，例如：

```python
@dataclass(frozen=True)
class AlignmentItem:
    raw_index: int
    raw_text: str
    braille_start: int
    braille_end: int
    braille_text: str
    is_space: bool
    is_newline: bool
    source_kind: str  # "text" or "math"
    source_html: str | None
```

欄位名稱可依實作調整，但 model 必須能區分：

- 由 escaped text 顯示的純文字卡片
- 由生成後的 MathML markup 顯示的數學卡片
- 單一空白卡片
- 單一換行斷行節點

### 3. Raw-element 對映規則

對每個 `TranslationResult`：

- `raw_to_braille_pos[i]` 是第 `i` 個 raw element 的起點
- 第 `i` 個 element 的終點是 `raw_to_braille_pos[i + 1]`，最後一個則為
  `len(braille)`
- `braille[start:end]` 就是該 item 顯示的點字內容

驗證規則保持不變：

- `len(raw_to_braille_pos)` 必須等於 `len(raw)`
- start/end 範圍必須遞增且落在 braille 長度範圍內

## 數學來源呈現

### 1. 真實資料來源

Dual view 的數學來源呈現使用和目前數學轉譯相同的來源文字，也就是 math segment 的
`TranslationResult.raw` element 中保存的原始 LaTeX-like 字串。

### 2. 轉換流程

在 dual view HTML render 數學來源內容之前，會先使用
`client/conversion/math_service.py` 內現有的 `latex_to_mathml()` helper，將數學原文
轉成 MathML。

接著 HTML renderer 會把這份 MathML 以 DOM markup 的方式放入卡片來源區中。

### 3. 失敗行為

若 dual-view model 建構或 rendering 過程中的 MathML 轉換失敗：

- dual view refresh 應沿用既有錯誤路徑失敗，而不是默默顯示錯誤的數學內容
- 在沒有額外設計變更前，不得 fallback 成部分解析或猜測出的 math HTML

這樣才能和現行數學轉譯邊界一致，因為目前無效數學輸入本來就會被視為錯誤。

## HTML Rendering 設計

### Segment 結構

每個 segment 會渲染成：

```html
<section class="segment">
  ...
</section>
```

`section` 上不再加入 `aria-label`。

### Item 結構

文字卡片顯示 escaped source text 與 escaped braille text。

數學卡片顯示：

- 一個來源容器，其 `inner HTML` 為產生出的 MathML markup
- 一個點字容器，內容為 escaped braille text

換行 item 顯示為斷行節點，而不是一般卡片。

空白 item 仍以一般卡片呈現，但來源區會使用 non-breaking-space 顯示處理。

### 信任邊界

插入文件中的 MathML 必須只來自專案自身的 `latex_to_mathml()` 轉換流程。Renderer
不得接受來自文件文字內容的任意未受信任 raw HTML。

## 內部分類規則

Dual view 需要知道哪些 item 是數學卡片。實作上應只有在該 `TranslationResult`
原本就是由 math translation path 產生時，才把該 segment 視為數學，而不是在 render
階段再根據 raw text 猜測。

因此此設計要求 dual-view cache 必須為每個 segment 明確保留 source-kind metadata。
預期 representation 是前述 `DualViewSegment` descriptor。

不可接受做法：

- 之後再掃描 `$...$` 或從文件編輯器文字重新解析來推斷哪些是 math segment

具體 representation 屬於實作細節，但 spec 明確要求 math 與 text 的來源差異必須被顯式保留。

## 測試

應新增或更新測試，覆蓋：

- 多字 raw element 只渲染成一張卡片，且只對應一段點字
- 單一字元空白 element 會渲染為獨立空白卡片
- 單一字元換行 element 會渲染為斷行節點
- 內含空白的多字 raw element 仍保持一張卡片
- 數學卡片的來源區會渲染 MathML markup
- segment `<section>` 輸出不再包含 `aria-label`
- 無效 range 驗證仍會拋出清楚錯誤

必要時也要更新 GUI flow 測試，確認 dual-view refresh path 仍使用最新快取轉換結果。

## 風險與限制

- 現有測試與註解仍把 model 視為字元級，需要一併更新。
- 數學來源 render 會讓 dual view 新增一個對 segment-origin metadata 的需求。
- 不同 WebView backend 對 MathML 的支援品質可能不同；此 spec 只要求生成出的 HTML
  內包含真正的 MathML DOM markup。
- 對於 atomic multi-character element，由於本來就不存在更細 mapping，UI 不得暗示逐字對映。

## 驗收標準

- 預設情況下，一個 `raw` element 對應一張 dual-view 卡片。
- 多字文字 token 不再為尾端字元顯示 `∅` 卡片。
- 單一 raw 空白 element 會渲染為空白卡片。
- 單一 raw 換行 element 會渲染為斷行。
- 即使文字內容內含空白或換行，多字 raw element 仍保持單一卡片。
- 每個 `TranslationResult` 仍渲染於一個 `<section class="segment">` 中。
- Segment section 不再包含 `aria-label`。
- 數學卡片會在點字輸出上方顯示以 MathML render 的來源內容。
- Dual view 仍沿用最近一次成功快取的轉換資料，不會自行重新觸發轉換。
