# 對話框顯示優化設計

## 摘要

這項變更要修正 DotExpress 現有對話框在初始大小、置中策略與清單呈現上的不一致問題。現況中，`TranslationSettingsDialog` 與 `TranslationTableDialog` 已採內容導向的 `SetSizerAndFit()`，但 `DictionaryManagementDialog` 與 `SpeechSymbolsDialog` 仍使用固定最小尺寸作為主要初始大小策略，多數自訂 `wx.Dialog` 也沒有明確依上層母視窗置中。

這次設計會統一自訂對話框的顯示規則：一般對話框應以內容決定初始大小，並盡可能依母視窗置中；`DictionaryManagementDialog` 會改成兩欄虛擬 list，第一欄顯示字典名稱，第二欄顯示字典條目數量；`SpeechSymbolsDialog` 則保留多欄虛擬 list 與欄位分隔線，但改成內容導向初始大小。另有一個刻意的例外：`Dual ViewFrame` 不採置中，而是直接複製主視窗當下的位置與大小，以覆蓋整個主視窗區域。

## 目標

- 讓 `DictionaryManagementDialog` 的初始大小依內容 `Fit`。
- 讓 `SpeechSymbolsDialog` 的初始大小依內容 `Fit`。
- 移除 `DictionaryManagementDialog` 與 `SpeechSymbolsDialog` 對固定最小尺寸作為初始大小的依賴。
- 讓所有自訂 `wx.Dialog` 盡可能依據母視窗置中顯示。
- 將 `DictionaryManagementDialog` 改為和字典條目管理器同型態的虛擬 list 實作。
- 讓 `DictionaryManagementDialog` 以兩欄顯示字典名稱與字典條目數量。
- 讓 `DictionaryManagementDialog` 只保留單擊選取，不使用雙擊編輯。
- 讓 `DictionaryManagementDialog` 的欄位寬度能隨可用寬度重算，而不是固定寫死。
- 讓 `Dual ViewFrame` 開啟時套用與主視窗相同的位置與大小。

## 非目標

- 不重新設計字典管理與字典條目管理的功能流程。
- 不新增新的字型系統、DPI 架構或跨平台縮放層。
- 不將 `DictionaryManagementDialog` 改寫為 `wx.ListBox`、`wx.DataViewListCtrl` 或其他不同元件。
- 不修改內建 `wx.FileDialog`、`wx.DirDialog`、`wx.MessageDialog` 的平台預設行為。
- 不特別同步 `Dual ViewFrame` 的最大化狀態旗標。
- 不為字典條目數量引入額外快取或背景載入機制。

## 使用者可見行為

### 一般自訂對話框

- 一般自訂 `wx.Dialog` 開啟時，應盡可能以母視窗為基準置中顯示。
- 若對話框沒有母視窗，則以一般視窗置中方式顯示。
- 小型設定型對話框的初始大小應由內容決定，而不是依賴固定寬高。

### `DictionaryManagementDialog`

- 開啟時，初始大小應由內容決定。
- 對話框應依母視窗置中。
- 字典清單仍為單選。
- 清單改為虛擬 list 實作。
- 清單使用兩欄顯示：
  - 字典名稱
  - 字典條目數量
- 清單只需支援單擊選取。
- 不需要雙擊直接進入編輯。
- 使用者需透過 `Edit` 按鈕開啟字典條目管理器。
- 第二欄的條目數量應反映開啟或刷新當下的真實值。
- 欄位寬度應隨視窗可用寬度變化，而非固定寫死。

### `SpeechSymbolsDialog`

- 開啟時，初始大小應由內容決定。
- 對話框應依母視窗置中。
- 保留目前多欄虛擬 list。
- 保留欄位分隔線，因為這是合理的多欄資料呈現。

### `Dual ViewFrame`

- 開啟 `Dual View` 時，不進行一般置中。
- `Dual ViewFrame` 應直接複製主視窗當下的位置與大小。
- 視覺目標是覆蓋主視窗當前所在區域，而不是維持自己預設的獨立小視窗尺寸。

## 內部設計

### 共用對話框收尾規則

在 `client/dialog.py` 中新增一個很小的共用 helper，用來統一處理自訂對話框在建構尾端的顯示收尾。

此 helper 的責任只有：

- 套用最終 layout / fit
- 若有 parent，執行 `CentreOnParent()`
- 若沒有 parent，執行 `Centre()`

這個 helper 不應引入新的狀態管理或抽象層。它只是把目前分散、遺漏或不一致的顯示收尾邏輯集中起來。

### 一般對話框的初始大小策略

以下類型的對話框維持既有結構，但初始大小策略統一為內容導向：

- `AddSymbolDialog`
- `DictionaryNameDialog`
- `DocumentNameDialog`
- `InvalidWorkspaceFilesDialog`
- `FileIssuesDialog`
- `TranslationSettingsDialog`
- `TranslationTableDialog`
- `ConvertingDialog`

原本已使用 `SetSizerAndFit()` 的對話框維持此模式。若有以固定最小尺寸作為主要初始大小來源的對話框，應移除這種依賴，改由 `Fit()` 決定初始大小。

### `SpeechSymbolsDialog` 的大小與位置

`SpeechSymbolsDialog` 維持以下核心特性：

- `wx.RESIZE_BORDER`
- 三欄虛擬 `wx.ListCtrl`
- `Filter` 輸入框
- `Add` / `Edit` / `Delete` / `OK` / `Cancel` 互動

這次只調整顯示規則：

- 建構 UI 完成後應做最終 `Fit()`
- 不再以 `SetMinSize((560, 440))` 當作初始尺寸基準
- 套用依母視窗置中的一致規則

使用者仍可在開啟後手動調整視窗大小。

### `DictionaryManagementDialog` 改為虛擬 list

目前的 `DictionaryManagementDialog` 使用一般 `wx.ListCtrl`，透過 `DeleteAllItems()` 與 `InsertItem()` 重建資料列。這次設計要改成與字典條目管理器同型態的虛擬 list 實作。

建議做法是新增一個可重用的虛擬 list control 基底，角色與目前 `DictionaryEntryListCtrl` 相同，但不要把它綁死在特定資料模型。其最小責任是：

- 接受 `get_item_text(row, column)` callback
- 由 `OnGetItemText()` 動態提供每個儲存格文字

`SpeechSymbolsDialog` 與 `DictionaryManagementDialog` 都可使用這個更通用的虛擬 list 控制項。

### `DictionaryManagementDialog` 的資料來源

`DictionaryManagementDialog` 的真實資料來源維持為：

- `self._dictionary_names`

除此之外，對話框應維護一份與字典名稱對應的條目數量資料，例如：

- `dictionary_name -> entry_count`

這份資料在對話框開啟時應即時計算，而不是依賴快取。

### `DictionaryManagementDialog` 的條目數量計算

第二欄顯示的字典條目數量應在對話框開啟或資料刷新時即時計算。

建議做法：

- 逐一讀取每個字典 CSV
- 計算有效條目數量
- 將結果存入對話框目前使用的數量對照表

這裡的「有效條目數量」應與現有字典編輯器實際會載入的資料概念一致。若某列在字典編輯器中會被忽略，就不應計入數量。

這次不需要為條目數量額外設計快取或背景執行緒。依目前規模，開啟對話框時即時計算即可。

清單不再用插入資料列的方式更新，而是：

- 更新 `self._dictionary_names`
- 更新每個字典對應的條目數量
- 透過 `SetItemCount(len(self._dictionary_names))` 更新虛擬列數
- 呼叫 `Refresh()` 重新繪製
- 再依 `preferred_name` 恢復選取

這樣可讓清單更新邏輯與 `SpeechSymbolsDialog` 的虛擬 list 模式一致，也減少重建資料列帶來的額外視覺副作用。

### `DictionaryManagementDialog` 的互動模式

清單互動規則應簡化為：

- 單擊選取目前列
- `Edit` 按鈕才會進入字典條目管理器
- 不使用雙擊直接編輯
- 不要求 `Enter` 快捷進入編輯

因此：

- 移除 `EVT_LIST_ITEM_ACTIVATED` 綁定
- `_on_edit()` 保留作為 `Edit` 按鈕的明確入口

### `DictionaryManagementDialog` 的欄位呈現

這個清單應使用兩欄報表視覺，兩欄都具有實際資訊意義：

設計要求：

- 第 1 欄顯示字典名稱
- 第 2 欄顯示字典條目數量
- 欄位寬度不固定寫死
- 第 2 欄應足以穩定顯示數量值，並與第 1 欄形成清楚區隔

欄寬應在以下時機重算：

- 對話框建立完成後
- 對話框 resize 後
- 字典清單刷新後

欄寬目標是貼齊 `ListCtrl` 的 client width，讓 Windows 字體放大、內容變寬或使用者手動改變視窗大小時，兩欄都能跟著有效空間調整。第 1 欄應取得主要剩餘空間，第 2 欄則保留適合顯示數量的寬度。

### `DictionaryManagementDialog` 的初始大小

`DictionaryManagementDialog` 保留 `wx.RESIZE_BORDER`，但不再依賴固定 `SetMinSize((650, 400))` 作為初始大小。

新的規則是：

- UI 建構完成後做 `Fit()`
- 再依母視窗置中

這讓初始尺寸能反映目前按鈕列、清單、標題與系統字體的實際大小，而不是固定使用某組假定尺寸。

### `Dual ViewFrame` 的位置與大小同步

`Dual ViewFrame` 是這次設計中刻意不跟隨一般 dialog 規則的例外。

當使用者從主視窗開啟 `Dual View` 時：

- 不進行 `CentreOnParent()`
- 不使用預設尺寸
- 直接讀取主視窗當下的幾何資訊
  - 位置
  - 大小
- 將相同的位置與大小套用到 `Dual ViewFrame`

這裡的目標是讓 `Dual ViewFrame` 覆蓋主視窗目前所在的可見區域。這次不額外同步最大化旗標，只依賴主視窗當下的實際位置與大小。

## 實作分解

### 1. 對話框共用 helper

- 新增 dialog 顯示收尾 helper
- 讓需要的自訂 dialog 在建構尾端統一使用

### 2. `SpeechSymbolsDialog`

- 保留既有多欄虛擬 list 架構
- 移除固定最小尺寸依賴
- 改為內容導向 `Fit`
- 套用依母視窗置中

### 3. `DictionaryManagementDialog`

- 將一般 `wx.ListCtrl` 改為虛擬 list
- 改寫資料刷新流程，使用 `SetItemCount()` 與 `Refresh()`
- 在開啟與刷新時即時計算每份字典的條目數量
- 移除清單雙擊編輯行為
- 保留 `Edit` 按鈕入口
- 新增欄寬重算邏輯
- 改為內容導向 `Fit`
- 套用依母視窗置中

### 4. `Dual ViewFrame`

- 在開啟流程中讀取主視窗當下位置與大小
- 建立後套用同一組位置與大小

## 測試

### 對話框顯示行為

- 開啟各自訂 `wx.Dialog`，確認會依母視窗置中顯示
- 確認 `TranslationSettingsDialog` 與 `TranslationTableDialog` 行為不回歸
- 確認 `InvalidWorkspaceFilesDialog` 與 `FileIssuesDialog` 不因移除固定最小尺寸而出現內容裁切

### `SpeechSymbolsDialog`

- 確認初始大小來自內容 `Fit`
- 確認仍可手動調整大小
- 確認多欄分隔線仍正常顯示

### `DictionaryManagementDialog`

- 確認改為虛擬 list 後仍可正常顯示全部字典名稱
- 確認第二欄可正確顯示各字典的條目數量
- 確認單擊可選取目前字典
- 確認沒有雙擊直接編輯行為
- 確認 `Edit` 按鈕仍可開啟 `SpeechSymbolsDialog`
- 確認新增、刪除、重新命名、匯入後，清單刷新與選取恢復正常
- 確認新增、刪除、匯入或編輯字典條目後，數量欄位會反映最新值
- 確認初始大小來自內容 `Fit`
- 確認兩欄欄寬在建立後、刷新後、resize 後都能重算

### `Dual ViewFrame`

- 從主視窗開啟 `Dual View`
- 確認其位置與大小與主視窗一致
- 確認效果為覆蓋主視窗當下區域，而非另開預設尺寸視窗

## 風險與限制

- `wx.ListCtrl` 的虛擬模式會改變 `DictionaryManagementDialog` 的刷新與選取管理方式，這是主要實作風險。
- 欄寬貼齊 client width 的視覺效果仍會受平台原生主題影響，但應顯著優於固定欄寬。
- 若字典數量很多且每份字典檔很大，開啟對話框時計算條目數量可能增加少量等待時間；依目前規模這是可接受的取捨。
- 對話框改為 `Fit()` 後，某些環境下初始尺寸可能與現在不同；這是預期中的行為改變，而不是副作用。
- `Dual ViewFrame` 只複製主視窗當下位置與大小，不額外追蹤之後的主視窗移動或大小變化。

## 驗收標準

- `DictionaryManagementDialog` 開啟時，初始大小依內容決定。
- `SpeechSymbolsDialog` 開啟時，初始大小依內容決定。
- 所有自訂 `wx.Dialog` 都會盡可能依母視窗置中。
- `DictionaryManagementDialog` 使用虛擬 list 顯示字典清單。
- `DictionaryManagementDialog` 使用兩欄顯示字典名稱與字典條目數量。
- `DictionaryManagementDialog` 只需要單擊選取，不提供雙擊直接編輯。
- `DictionaryManagementDialog` 的欄位寬度不再固定寫死，且能隨可用寬度重算。
- `DictionaryManagementDialog` 第二欄會反映字典條目數量的真實值。
- `SpeechSymbolsDialog` 仍保留多欄分隔線。
- `Dual ViewFrame` 開啟時會複製主視窗當下的位置與大小。
