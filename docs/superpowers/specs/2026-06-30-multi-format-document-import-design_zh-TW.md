# 多格式文件匯入與 Markdown 中介設計

## 摘要

DotExpress 目前的文件匯入只支援純文字 `TXT` 與既有封裝格式 `DEP`。本設計將匯入來源擴充為 `PDF`、`DOCX`、`EPUB`，並在匯入階段先將來源內容轉成統一的 Markdown 字串後再寫入既有 `Document.text`。

設計的核心不是直接為每種格式各自輸出字串，而是先建立一個只描述 block-level 語意的中介 AST。`DOCX` 與 `EPUB` 走語意保留路徑，`PDF` 則先檢查是否具有 tagged PDF 結構；若有可解析語意就轉成 AST，若沒有就直接退回純文字，不做任何 layout heuristic 推論。

## 背景

- 目前文件匯入入口在 [client/gui.py](/workspace/DotExpress/client/gui.py:1044) 的 `on_import_document(format_key)`。
- 目前批次匯入實作在 [client/documents/workspace.py](/workspace/DotExpress/client/documents/workspace.py:162) 的 `batch_import_documents()`。
- 現況只有兩種匯入格式：
  - `dep` -> `load_document_package()`
  - `txt` -> `load_text_document()`
- `Document` 模型目前只有：
  - `name`
  - `text`
  - `braille`

這表示新的多格式支援應優先設計成「匯入前轉換」，而不是修改工作區儲存模型或 `DEP` 封裝格式。

## 目標

- 支援從 `PDF`、`DOCX`、`EPUB` 匯入文件。
- `DOCX` 與 `EPUB` 在可行範圍內保留 block-level 語意並輸出 Markdown。
- `PDF` 在有 tagged PDF 語意時抽出 block-level 結構並輸出 Markdown。
- `PDF` 在沒有可用語意時退回純文字抽取。
- 保持現有 `Document` 與 `DEP` 工作區格式不變。
- 將新格式匯入整合進現有 `Import` 選單與批次匯入流程。

## 非目標

- 不改變 `.dep` 套件格式。
- 不修改 `Document.text` 的資料型別。
- 不保留 inline 語意，例如強調、連結、註腳。
- 不對 untagged PDF 做標題、清單、表格、引述或分隔線推論。
- 不承諾 PDF 表格在沒有結構標記時仍能還原成 Markdown table。
- 第一版不支援舊版 `DOC`。

## 確認過的需求

本設計依據已確認的需求約束如下：

- `Word` 第一版只支援 `DOCX`。
- 保留的語意只限 block-level：
  - 標題
  - 清單
  - 引述
  - 分隔線
  - 表格
- inline 語意先全部忽略。
- `PDF` 必須先檢查 `/MarkInfo` 與 `/StructTreeRoot`。
- `PDF` 若沒有語意，直接轉純文字，不做推論。
- `PDF` 若有語意，則需要抽出語意結構，而不是一律走純文字 fallback。

## 核心決策

### 1. 以 block-level AST 作為唯一中介模型

所有新匯入格式都不直接輸出 Markdown 字串，而是先轉成共用 AST，再由 renderer 統一輸出 Markdown。

這樣的好處是：

- `DOCX`、`EPUB`、`PDF` 的語意邏輯可以共用輸出規則。
- 測試可以直接驗證語意結構，而不是只比對最終字串。
- 未來若要增加其他輸出格式，例如純文字或 HTML，可重用同一份中介結果。
- `PDF` fallback 純文字可以用專用節點表達，而不必假裝成有語意的段落。

### 2. AST 只支援 block-level 語意

第一版 AST 型別定義如下：

- `Document(blocks)`
- `Heading(level, text)`
- `Paragraph(text)`
- `ListBlock(ordered, items)`
- `ListItem(blocks)`
- `BlockQuote(blocks)`
- `HorizontalRule()`
- `Table(headers, rows)`
- `RawTextBlock(text)`

其中：

- `Heading.level` 限定為 `1` 到 `6`
- `Paragraph.text` 與 `Heading.text` 都只保存純文字
- `ListItem.blocks` 允許巢狀 block，避免未來擴充時需要重寫資料模型
- `RawTextBlock` 只用於無法可靠重建語意的內容，特別是 `PDF` 純文字 fallback

不建立 inline AST，例如 `Strong`、`Emphasis`、`Link`、`Footnote`。

### 3. Markdown renderer 只負責序列化，不做語意判斷

Markdown renderer 的責任是：

- `Heading` -> `#` 到 `######`
- `Paragraph` -> 一般段落
- `ListBlock` / `ListItem` -> 有序或無序清單
- `BlockQuote` -> `>`
- `HorizontalRule` -> `---`
- `Table` -> Markdown table
- `RawTextBlock` -> 原樣輸出文字區塊

renderer 不應在這一層推論結構，也不應重新解讀來源內容。所有語意判斷都必須在各格式 importer 內完成。

### 4. `DOCX`、`EPUB`、`PDF` 採分流策略，不走單一萬用轉換器

本設計不採「全部先轉 HTML，再從 HTML 轉 Markdown」的單一路徑。

原因如下：

- `DOCX` 與 `EPUB` 本身就有較清楚的文件語意，適合直接保留。
- `PDF` 若沒有結構標記，轉成 HTML 也不會自然變成可靠的語意來源。
- 單一路徑會把 `PDF` 的退化情況帶進 `DOCX` / `EPUB`，降低可維護性。

因此每種格式都要有自己的 importer，但共用同一套 AST 與 Markdown renderer。

### 5. `PDF` 採雙路徑：先讀語意，失敗再退回純文字

`PDF` 的處理順序固定如下：

1. 用 `pypdf` 開啟文件。
2. 檢查 catalog 與文件結構中的 `/MarkInfo`。
3. 檢查是否存在 `/StructTreeRoot`。
4. 若存在可解析的 tagged structure，走 `tagged PDF -> AST -> Markdown`。
5. 若不存在、結構無法解析，或內容不足以可靠映射到支援的 block-level AST，改走 `PyMuPDF` 純文字抽取。

這個決策的重點是：

- `pypdf` 是 `PDF` importer 的必要元件，負責結構檢查與結構樹讀取。
- `PyMuPDF` 是純文字 fallback 的必要元件，負責穩定文字抽取。
- 不使用字級、縮排、粗體、線段等 heuristic 猜測語意。

## 模組設計

建議新增一組文件匯入相關模組，例如：

- `client/documents/importers/__init__.py`
- `client/documents/importers/base.py`
- `client/documents/importers/markdown_ast.py`
- `client/documents/importers/markdown_renderer.py`
- `client/documents/importers/docx_importer.py`
- `client/documents/importers/epub_importer.py`
- `client/documents/importers/pdf_importer.py`

### `base.py`

定義 importer 共用介面，例如：

- `import_document(path: Path) -> ImportedDocument`
- `ImportedDocument(name: str, markdown_text: str)`

`ImportedDocument` 應作為正式回傳型別，而不是只回傳 tuple。重點是將 AST 生成與 Markdown 渲染封裝在 importer 層內，不把 AST 泄漏到 UI 層。

### `markdown_ast.py`

定義 AST 節點資料結構。建議使用 `dataclass(frozen=True)`，讓測試與比較更穩定。

### `markdown_renderer.py`

接受 `Document` AST，輸出 Markdown 字串。所有換行規則必須集中在這裡，避免 importer 各自手寫 Markdown 導致格式漂移。

## 各格式匯入流程

### `DOCX`

`DOCX` 使用 `mammoth` 作為主要轉換器。

流程如下：

1. 讀取 `DOCX`
2. 用 `mammoth` 轉成乾淨 HTML
3. 解析 HTML DOM
4. 將下列元素映射為 AST：
   - `h1`-`h6` -> `Heading`
   - `p` -> `Paragraph`
   - `ul` / `ol` / `li` -> `ListBlock` / `ListItem`
   - `blockquote` -> `BlockQuote`
   - `hr` -> `HorizontalRule`
   - `table` / `tr` / `th` / `td` -> `Table`
5. 將 AST 交給 Markdown renderer
6. 以檔名 stem 當作文件名稱，輸出最終 Markdown

第一版不需保留：

- 粗體、斜體
- 連結
- 圖片
- 註腳

### `EPUB`

`EPUB` 使用 `ebooklib` 作為主要讀取器。

流程如下：

1. 讀取 `EPUB`
2. 依 spine 順序取出 XHTML/HTML 內容
3. 逐章節解析 DOM
4. 將與 `DOCX` 相同的 block-level 元素映射為 AST
5. 在章節內容之間保留合理區隔，避免不同 spine item 直接黏成一段
6. 將合併後 AST 交給 Markdown renderer

關鍵決策：

- 依 spine 順序作為輸出順序的唯一來源
- 不保留 EPUB 內部連結與導覽結構
- 不額外輸出 metadata 區塊

### `PDF`

`PDF` importer 分成兩條路徑。

#### 路徑 A：tagged PDF 語意路徑

前提是 `pypdf` 可確認並讀取可用的 `/StructTreeRoot`。

第一版只正式支援以下 block-level 結構映射：

- `H1`-`H6` -> `Heading`
- `P` -> `Paragraph`
- `L` / `LI` / `Lbl` / `LBody` -> `ListBlock` / `ListItem`
- `BlockQuote` 或等價引用容器 -> `BlockQuote`
- `Table` / `TR` / `TH` / `TD` -> `Table`
- 可明確表示水平分隔的結構元素 -> `HorizontalRule`

遇到下列情況時，不應做 heuristic 補救：

- 結構元素缺失但視覺上像標題
- 只有字體大小差異、沒有結構標記
- 只有對齊或縮排、沒有清單結構
- 表格只存在視覺欄位，沒有可解析結構

對於未支援或無法可靠映射的 tagged 結構：

- 若該節點的子孫文字內容仍可依原順序安全攤平成單一文字區塊，降為 `Paragraph`
- 若連原順序都無法可靠保留，直接放棄整份文件的語意路徑，改走純文字 fallback

第一版不處理 inline tag，也不處理註腳、交叉參照、連結。

#### 路徑 B：純文字 fallback

若 `PDF` 缺少可用語意，或 `pypdf` 無法可靠建立對應 AST，則：

1. 用 `PyMuPDF` 依頁面順序抽取文字
2. 進行最小必要正規化：
   - 統一換行
   - 去除明顯的空頁輸出
3. 依頁面順序串接文字，並以整份文件建立單一 `RawTextBlock`
4. 交給 Markdown renderer 輸出

這條路徑的原則是：

- 只保證可讀純文字
- 不猜測標題
- 不猜測清單
- 不猜測引述
- 不猜測分隔線
- 不猜測表格

## 與現有 DotExpress 的整合

### 文件模型

`Document` 資料模型維持不變：

- `name`
- `text`
- `braille`

新 importer 的輸出仍然只會寫入 `Document.text`。這可避免：

- 改動工作區載入/儲存格式
- 改動 `.dep` 內部內容
- 改動轉譯、點字轉換與編輯器現有介面

### 工作區與封裝格式

`.dep` 格式不變：

- 仍保存 `<name>.txt`
- 仍保存 `<name>.brl`
- 匯入後的 Markdown 就直接當成 `.txt` 內容保存

這代表工作區內部不需要知道原始來源檔是 `PDF`、`DOCX` 還是 `EPUB`。

### 匯入入口

現有 `batch_import_documents()` 需要擴充為依 `format_key` 派發不同 loader，而不是只在 `dep` 與 `txt` 之間二選一。

建議邏輯：

- `dep` -> `load_document_package()`
- `txt` -> `load_text_document()`
- `docx` -> `load_imported_markdown_document(..., importer=docx_importer)`
- `epub` -> `load_imported_markdown_document(..., importer=epub_importer)`
- `pdf` -> `load_imported_markdown_document(..., importer=pdf_importer)`

### UI / 選單

需要同步擴充：

- `Import` 子選單格式
- `wx.FileDialog` 的 wildcard
- 匯入錯誤顯示文案

匯入格式應新增：

- `PDF`
- `DOCX`
- `EPUB`

現有 `DEP`、`TXT` 行為不變。

## 錯誤處理

### 共通原則

- 單一檔案匯入失敗時，以現有 `BatchIssue` 回報對應 `path` 與 `reason`
- 其他成功匯入的檔案不受影響
- 不在 importer 內彈 UI；只丟出可顯示的例外訊息

### `DOCX`

- 無法開啟、格式損壞、無法轉 HTML -> 匯入失敗
- 若轉換結果為空白內容，仍可匯入，但產生空 Markdown

### `EPUB`

- 無法讀取封裝、spine 缺失、章節內容不可解析 -> 匯入失敗
- 個別章節解析失敗的策略應保持保守：若整體順序或語意會失真，直接視為整份匯入失敗

### `PDF`

- 加密或無法開啟 -> 匯入失敗
- `/MarkInfo` / `/StructTreeRoot` 缺失 -> 直接走純文字 fallback，不視為錯誤
- `/StructTreeRoot` 存在但結構不可可靠映射 -> 直接走純文字 fallback，不視為錯誤
- `PyMuPDF` 純文字抽取失敗 -> 匯入失敗

這裡的關鍵是：`PDF` 無語意不是失敗條件，只是切換到 fallback 路徑的條件。

## 測試策略

### AST 與 renderer 單元測試

驗證：

- 各 AST 節點能正確序列化成 Markdown
- `Table` 的表頭、資料列輸出一致
- `BlockQuote`、清單、標題之間的空行規則穩定
- `RawTextBlock` 不會被誤加 Markdown 語意

### importer 單元測試

`DOCX`：

- 標題轉 `Heading`
- 清單轉 `ListBlock`
- 表格轉 `Table`
- 分隔線轉 `HorizontalRule`

`EPUB`：

- 依 spine 順序輸出
- 跨章節內容之間不會黏連
- 標題、清單、引述、表格能映射

`PDF`：

- 有 `/MarkInfo` 與 `/StructTreeRoot` 的 tagged fixture 會走語意路徑
- 缺少語意結構的 fixture 會走 `RawTextBlock`
- untagged PDF 不會觸發 heuristic 推論

### 整合測試

驗證：

- `batch_import_documents()` 能接受新 `format_key`
- 新格式檔案匯入後會產生 `Document(name, text, braille=None)`
- 檔名重複檢查仍沿用既有規則
- 匯入失敗時 `BatchIssue` 回報保持既有格式

## 風險與取捨

- `PDF` 語意路徑的最大風險是 open-source Python 生態對 structure tree 的高階封裝不足
  - 緩解方式：明確將 `pypdf` 侷限為結構檢查與結構讀取，並接受第一版只支援有限的 block-level mapping
- Markdown table 對複雜表格表達能力有限
  - 接受這項限制；遇到複雜合併儲存格不保證完美輸出
- `DOCX` / `EPUB` 的 HTML 結構可能與來源實際樣式不完全一致
  - 接受這項限制，因為本設計目標是語意可讀性，不是樣式保真
- 把 Markdown 存回 `.txt` 會讓工作區內文本看起來不再是純 prose
  - 接受這項限制，因為需求本身就是保留 Markdown 語意

## 實作大綱

1. 新增 block-level AST 與 Markdown renderer。
2. 新增 `DOCX` importer，完成 `mammoth HTML -> AST -> Markdown`。
3. 新增 `EPUB` importer，完成 `ebooklib spine XHTML -> AST -> Markdown`。
4. 新增 `PDF` importer，完成：
   - `pypdf` `/MarkInfo` / `/StructTreeRoot` 檢查
   - tagged structure -> AST
   - `PyMuPDF` 純文字 fallback
5. 擴充 `batch_import_documents()` 與相關 loader dispatch。
6. 擴充文件匯入選單與 wildcard。
7. 增加 importer、renderer、整合測試。

## 開放問題

沒有未決策項目。

下列邊界已在設計前確認完成：

- `DOCX` 第一版只支援 `docx`
- inline 語意先全部忽略
- `PDF` 沒語意時只抽純文字
- `PDF` 有語意時才轉 block-level Markdown
