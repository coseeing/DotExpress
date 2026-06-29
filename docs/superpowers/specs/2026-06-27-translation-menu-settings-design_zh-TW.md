# 轉譯選單與設定設計

## 背景

目前 client 在主視窗上方保留了一條可見的 `Conversion` 控制列。這一列同時承擔六個控制項：轉譯表、點字類型、寬度、字典選擇、字典管理動作，以及執行轉換。

下一階段需求是移除這條列，讓編輯區可以擴大，並把轉譯入口搬到可用 `Alt` 開啟的頂層選單中。現有的 `TranslationTableDialog` 已經使用模態 `OK/Cancel` 的流程，因此新的轉譯設定流程也應沿用這個模式，而不是把寬度直接塞進選單項目裡。

這份設計已經受到腦力激盪期間確認過的四個決策所約束：

- 頂層 `Translation` 選單只包含四個項目：`Convert`、`Translation Settings...`、`Translation Tables Setting...`、`Dictionary Management...`
- `Translation Settings...` 只在使用者按下 `OK` 時套用變更
- `Dictionary Management...` 是一個獨立對話框，內含自己的字典清單與管理動作
- 在 `Dictionary Management...` 中選擇 `Edit` 時，會先關閉該對話框，再開啟既有的字典條目編輯器；而從編輯器返回後，使用者會停留在主視窗

## 目標 / 非目標

**目標：**

- 移除主視窗上可見的 `Conversion` 列
- 新增一個頂層 `Translation` 選單，且內容為已確認的四個項目
- 新增一個模態 `Translation Settings...` 對話框，只負責點字類型、寬度與字典選擇
- 保留現有的 `Translation Tables Setting...` 對話框流程
- 新增獨立的 `Dictionary Management...` 對話框，處理字典生命週期操作
- 保留 `Ctrl+Enter` 這個直接執行轉換的快捷鍵
- 在移除 `Conversion` 列後，更新 `F6` / `Shift+F6` 的區塊循環，讓它只在可見的主視窗區塊之間切換
- 保持這次重構務實，避免引入這個功能不需要的架構

**非目標：**

- 不重新設計 `client/conversion/service.py` 裡的轉譯邏輯
- 不把轉譯表設定混進新的轉譯設定對話框
- 不把字典檔案管理語意混進轉譯設定對話框
- 不變更字典 CSV 格式、轉譯表持久化格式、或轉換輸出格式
- 不引入 MVP、MVVM、命令類別階層，或其他大型 UI 抽象

## 決策

### 1. 使用頂層 `Translation` 選單與四個直接命令

選單內容如下：

- `Convert`
- `Translation Settings...`
- `Translation Tables Setting...`
- `Dictionary Management...`

這樣可以維持選單簡潔、適合鍵盤操作。寬度不適合做成內嵌選單項目，而字典管理也比起混在轉譯設定裡，更適合獨立成自己的流程。

曾考慮的替代方案：把現有六個控制項全部搬進巢狀選單項目。這個方案被否決，因為它會讓寬度調整、字典選擇與動作發現都更難操作。

### 2. 保留 `Convert` 作為第一層動作

`Convert` 仍然是 `Translation` 選單中的直接命令，而且仍可透過來源文字編輯區的 `Ctrl+Enter` 觸發。

這可以保留高頻轉換路徑，不必為了執行轉換而先打開設定對話框。

曾考慮的替代方案：把 convert 放到子選單或設定對話框內。這個方案被否決，因為執行是動作，不是設定。

### 3. `Translation Settings...` 以現有轉譯表對話框的模式為準

`Translation Settings...` 會是一個模態對話框，提供 `OK` 與 `Cancel`。它會先暫存三個值：

- 點字輸出類型
- 轉換寬度
- 已選字典

這些值在對話框開啟時，會從目前的執行期 / 設定狀態載入。只有在使用者按下 `OK` 後，才會回寫到應用程式。

曾考慮的替代方案：直接重用主視窗上的控制項，維持逐一立即儲存。這個方案被否決，因為它和已確認的 `OK` 才套用行為不一致。

### 4. 字典生命週期操作改放到獨立的管理對話框

`Dictionary Management...` 會開啟一個專門管理字典的對話框。這個對話框會以 list view 顯示現有字典，並在清單下方放置管理按鈕：

- `Add`
- `Delete`
- `Rename`
- `Edit`
- `Import`
- `Export`

這些動作仍維持立即式的字典管理行為，但現在是放在管理對話框裡，因此語意是相容的，不會和 `OK/Cancel` 的設定對話框混在一起。

曾考慮的替代方案：把字典動作保留在 `Translation Settings...` 裡。這個方案被否決，因為它會把暫存設定語意與立即檔案變更混在一起，讓 `Cancel` 的行為更難理解。

### 5. 重用既有的轉譯表對話框

`Translation > Translation Tables Setting...` 會直接開啟現有的 `TranslationTableDialog`。它的行為維持不變：選擇內容會先暫存於對話框中，只有按下 `OK` 才真正提交。

曾考慮的替代方案：把轉譯表設定也合併進 `Translation Settings...`。這個方案被否決，因為現有轉譯表對話框已經可用，而且處理的是不同且更複雜的關注點。

### 6. 在開啟字典條目編輯器之前先關閉字典管理

當使用者在 `Dictionary Management...` 中選擇 `Edit` 時，應先關閉管理對話框，再開啟現有的字典條目編輯器。當編輯器關閉後，流程就結束在主視窗，不會自動重新打開字典管理。

這樣可以讓流程簡單，也避免建立一套會干擾其他開啟字典條目編輯器路徑的返回狀態邏輯。

曾考慮的替代方案：編輯結束後自動重新開啟 `Dictionary Management...`。這個方案被否決，因為它會增加狀態回復的複雜度，但使用者獲益有限。

### 7. 從主視窗區塊循環中移除 `Conversion`

當可見的 `Conversion` 列被移除後，`F6` / `Shift+F6` 應只在可見區塊之間切換：

- `Document List`
- `View`
- `Source Text`
- `Braille Result`

選單列仍然透過原生的 `Alt` 選單操作方式可達，不應透過區塊循環進入。

曾考慮的替代方案：保留一個概念上的 `Conversion` 區塊，但不顯示任何控制項。這個方案被否決，因為它會產生沒有可見對應物的焦點停點。

## UI 結構

### 主視窗

主視窗會完全移除可見的 `Conversion` 列。

選單列包含：

- `Translation`
- `Help`

`Translation` 內包含：

- `Convert`
- `Translation Settings...`
- `Translation Tables Setting...`
- `Dictionary Management...`

### Translation Settings 對話框

此對話框包含：

- `Braille Type` 下拉選單
- `Width` 數值微調控制
- `Dictionary` 下拉選單
- 標準 `OK` / `Cancel` 按鈕

這個對話框只編輯一份暫存的轉譯設定。

### Dictionary Management 對話框

此對話框包含：

- 一個列出現有管理字典的 list view
- 清單下方的動作按鈕：
  - `Add`
  - `Delete`
  - `Rename`
  - `Edit`
  - `Import`
  - `Export`

這個對話框是一個立即式管理介面，不是 `OK/Cancel` 型的設定介面。

## 狀態與行為

實作時應引入一個小型的轉譯設定狀態邊界，而不是引進新的框架。

像下面這樣的小型資料物件就足夠了：

```python
@dataclass
class TranslationSettings:
    output_mode: str
    width: int
    selected_dictionary: str
```

預期行為如下：

- 開啟 `Translation Settings...` 時，會把目前使用中的設定載入到暫存物件
- 編輯控制項時，只會改變暫存物件，不會立即影響目前設定
- 按下 `OK` 時，會把暫存物件套用到執行期狀態並持久化
- 按下 `Cancel` 時，會丟棄暫存物件
- 開啟 `Dictionary Management...` 時，會把目前字典清單載入 list view
- 執行 `Add`、`Delete`、`Rename`、`Import` 或 `Export` 時，會立即作用到字典檔案
- 在 `Add`、`Delete`、`Rename`、`Import` 之後，管理清單會立即更新
- 執行 `Edit` 時，會先關閉 `Dictionary Management...`，再開啟現有的字典條目編輯器
- 關閉字典條目編輯器後，使用者會停留在主視窗

## 風險 / 取捨

- 移除列之後，busy state 或 focus 邏輯裡的控制項參照可能會失效
  - 緩解方式：把 busy-state 處理與區塊循環定義一起更新
- 新增的選單與對話框字串可能和本地化內容脫節
  - 緩解方式：把所有新的使用者可見字串都視為本地化更新，並更新 `.po` 與編譯後的 catalog
- 字典管理流程中的刪除或重新命名，可能讓目前選取的字典變成過期狀態
  - 緩解方式：立即更新管理清單，並用既有的字典 fallback 規則重新決定目前選取項目
- 關閉管理對話框再開啟編輯器，對重複編輯來說可能稍微不夠直接
  - 緩解方式：接受多一步重開的成本，換取較低的實作複雜度與較少的對話框狀態互動

## 測試

驗證應涵蓋：

- `Translation` 選單出現，且四個項目與順序正確
- `Translation > Convert` 觸發和現有 convert action 相同的流程
- `Ctrl+Enter` 仍然觸發轉換
- `Translation Settings...` 只在按下 `OK` 時套用暫存設定
- `Translation Settings...` 在按下 `Cancel` 時不會改變目前設定
- `Dictionary Management...` 會以 list view 顯示目前的字典清單
- `Dictionary Management...` 會立即執行 add/delete/rename/import/export
- `Dictionary Management... > Edit` 會關閉管理對話框並開啟現有的字典條目編輯器
- `Translation Tables Setting...` 仍然使用既有對話框與 `OK/Cancel` 行為
- 在移除 `Conversion` 列後，`F6` / `Shift+F6` 只會在可見區塊之間循環
- 任何新增或變更的使用者可見字串，都已更新本地化檔案

## 實作大綱

1. 新增 `Translation` 選單，並把四個命令接到既有或新的處理函式。
2. 新增 `TranslationSettingsDialog`。
3. 為暫存載入與 `OK` 時套用加入一個小型的轉譯設定狀態邊界。
4. 新增 `DictionaryManagementDialog`，並提供 list view 與動作按鈕。
5. 把 `DictionaryManagementDialog` 的 `Edit` 接到「先關閉管理，再開啟既有字典條目編輯器」的流程。
6. 從主視窗版面中移除可見的 `Conversion` 列。
7. 更新 busy-state 處理、區塊循環與測試。
8. 更新新的字串所需的本地化資源。

## 未決問題

無。其餘的行為選擇已在腦力激盪階段完成確認，再開始撰寫這份規格前就已定案。
