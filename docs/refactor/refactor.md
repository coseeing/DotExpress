# DotExpress client `轉譯` 區重構評估

## 目的與範圍

本文件針對 `client/` 現有 `轉譯` 區相關程式碼進行 review，並依照下一階段需求提供重構建議。

本次需求已確認為：

- 移除主畫面上方現有的 `Conversion` 控制列，騰出更多編輯空間
- 新增可由 `Alt` 存取的 `轉譯` 選單
- `轉譯` 選單先收斂為三項：
  - `執行轉換`
  - `轉譯設定...`
  - `轉譯表設定...`
- `轉譯設定...` 採對話框形式，使用者按 `OK` 後才一次套用
- `轉譯表設定...` 沿用現有做法，以對話框處理

本文件刻意避免為了重構而額外引入大型架構，重點是支撐這個需求，不做 over design。

## 現況摘要

目前 `Conversion` 區主要集中在 [client/gui.py](/workspace/DotExpress/client/gui.py:235) 的 `BrailleFrame`：

- `_create_conversion_controls()` 建立六個控制項
  - `Translation Tables...`
  - `Braille Type`
  - `Width`
  - `Dictionary`
  - `Actions`
  - `Convert`
- `_bind_events()` 直接綁定這些控制項事件
- `on_convert()` 直接從畫面控制項讀值並啟動轉換
- `on_open_table_dialog()` 開啟 `TranslationTableDialog`，按 `OK` 後寫回設定
- `_set_conversion_busy()`、`_get_section_controls()` 也直接依賴這批控制項

`轉譯表設定` 本身已經是獨立對話框，位於 [client/dialog.py](/workspace/DotExpress/client/dialog.py:537)，而且是 `OK/Cancel` 模式。這部分可直接延用，不需要重做。

## 需求導向的 review findings

以下以「這次需求下會造成阻力的地方」為主，而不是泛泛談架構。

### 1. `BrailleFrame` 對 `轉譯` UI、設定持久化、快捷鍵、轉換流程的責任仍然過多

位置：

- [client/gui.py](/workspace/DotExpress/client/gui.py:251)
- [client/gui.py](/workspace/DotExpress/client/gui.py:354)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1194)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1366)

影響：

- 目前控制列還在畫面上時，這種集中式寫法勉強可維持
- 一旦改成 `menu + dialog`，如果仍然把所有讀值、寫值、啟用/停用規則都留在 `BrailleFrame`，同一個類別會同時理解：
  - menu 結構
  - dialog 初始化與結果套用
  - config 寫回
  - convert 執行
  - busy state
  - section focus/navigation
- 這會讓後續再調整 `轉譯` 行為時，持續回到 `gui.py` 大類別修改

SOLID 評估：

- `SRP` 不足，這是本次最明顯的問題
- `DIP` 也偏弱，因為 frame 直接依賴具體 UI 控制項狀態

建議：

- 不需要引入 MVP/MVVM
- 只要把「轉譯設定的讀取/套用」抽成一組明確的方法或小型資料物件即可

### 2. 現有 `轉譯` 設定是「分散即時生效」，與新需求的 `OK 後一次套用` 模式不一致

位置：

- [client/gui.py](/workspace/DotExpress/client/gui.py:1191)
- [client/config.py](/workspace/DotExpress/client/config.py:106)
- [client/config.py](/workspace/DotExpress/client/config.py:116)
- [client/config.py](/workspace/DotExpress/client/config.py:126)

影響：

- `output_choice`、`width_spin`、`dictionary_choice` 目前都是各改各存
- 新需求中的 `轉譯設定...` 對話框則是典型的「先編輯草稿，按 `OK` 再一次套用」
- 若直接把現有控制項搬進 dialog，但沿用原本事件即時存檔的做法，會出現：
  - 使用者按 `Cancel` 也可能已經寫入部分設定
  - dialog 的 UX 與 `轉譯表設定` 不一致

SOLID / Pattern 評估：

- 目前缺少清楚的「設定快照」邊界
- 這裡適合用很小的 `Settings Data Object` 或 `dataclass`，不需要更重的模式

建議：

- 建立一個 `TranslationSettings` 資料物件，至少包含：
  - `output_mode`
  - `width`
  - `selected_dictionary`
- dialog 編輯此資料物件的副本
- 只有在 `OK` 時才呼叫統一的套用方法

### 3. 字典動作目前綁在按鈕 popup menu，重用性不足

位置：

- [client/gui.py](/workspace/DotExpress/client/gui.py:1200)

影響：

- 現有 `Actions` 是綁在 `self.actions_btn.PopupMenu(...)`
- 這個做法適合「畫面上有按鈕」的情境
- 一旦主畫面移除該按鈕，字典動作若要放進 `轉譯設定...`，現有互動模型就會變得不自然

建議：

- 不要保留外部漂浮 popup button 的心智模型
- 將字典動作改成 `轉譯設定...` 對話框中的按鈕或次級選單入口
- 底層字典操作函式可保留，重構的是觸發方式，不是字典邏輯本身

### 4. `Conversion` 區被當成鍵盤 section 的一部分，移除後需要同步整理焦點導航

位置：

- [client/gui.py](/workspace/DotExpress/client/gui.py:404)

影響：

- `_get_section_controls()` 目前把 `Conversion` controls 視為一個 section
- 如果 UI 改成 menu + dialog，這一段定義會失真
- 若不一起整理，F6 或其他 section focus 流程容易留下不一致行為

建議：

- 移除 `CONVERSION_SECTION` 對主畫面控制列的依賴
- 主畫面 section 專注保留：
  - 文件列表
  - 檢視列
  - 原文編輯區
  - 點字結果區
- `轉譯` 改由 menu mnemonic 與 `Ctrl+Enter` 支援

## Design Patterns vs SOLID 評估

### 適合保留或補強的做法

- `Dialog as configuration editor`
  - `TranslationTableDialog` 已經是合理模式
  - `轉譯設定...` 應該比照這個模式
- `Command-style menu action`
  - `執行轉換`
  - `開啟轉譯設定`
  - `開啟轉譯表設定`
  - 這三個動作適合作為清楚的 menu command handler
- `Small data object`
  - 用於承接 dialog 編輯中的設定草稿

### 不建議引入的做法

- 不建議為此導入 MVP / MVVM
- 不建議新增 mediator、event bus、observer layer
- 不建議把每個 menu item 都抽成獨立 command class
- 不建議現在就把整個 `BrailleFrame` 再切成大量 controller/service

原因：

- 這次需求的變動集中在 UI 呈現與設定套用邏輯
- 轉換核心已經有 `client/conversion/service.py`
- 真正需要的是「減少畫面控制項與設定存取的耦合」，不是建立新的框架

## 建議的最小重構方案

### 方案結論

採用以下結構即可：

- `Help` 之外新增 `轉譯` menu
- `轉譯` menu 只有三項：
  - `執行轉換`
  - `轉譯設定...`
  - `轉譯表設定...`
- 沿用現有 `TranslationTableDialog`
- 新增一個 `TranslationSettingsDialog`
- 在 `BrailleFrame` 中新增少量方法，統一讀取與套用轉譯設定

### 建議的責任切分

`BrailleFrame`

- 建立 menu
- 綁定 menu event
- 提供 `on_convert()`
- 提供 `on_open_translation_settings()`
- 提供 `on_open_table_dialog()`
- 統一套用設定結果到：
  - runtime state
  - config
  - 畫面需要更新的控制項或快取

`TranslationSettingsDialog`

- 顯示與編輯：
  - 點字類型
  - 寬度
  - 字典選擇
  - 字典動作入口
- 只管理暫存值
- `OK` 時回傳最終選擇

`config.py`

- 既有 `get_* / set_*` API 可沿用
- 不一定需要立刻改成批次儲存 API
- 但在 `BrailleFrame` 內應由單一套用方法集中呼叫，不再分散在各 UI event

### 建議新增的最小抽象

可新增一個很小的資料物件，例如：

```python
@dataclass
class TranslationSettings:
    output_mode: str
    width: int
    selected_dictionary: str
```

用途只有兩個：

- 當作 dialog 初始化資料
- 當作 `OK` 後套用的結果載體

這個抽象是必要的，因為它能把「畫面控制項狀態」和「設定值」分開；但它也已經是本次需求應有的上限，不需要再往上包裝更多層。

## 具體重構建議

### 1. 先把 menu 結構建立出來，再移除畫面上的 `Conversion` 列

原因：

- 先建立替代入口，再移除舊入口，風險最低
- 也比較容易驗證快捷鍵、Alt mnemonic、無障礙流程

建議順序：

1. 在 `_create_menu_bar()` 新增 `轉譯` menu
2. 綁定三個 menu handler
3. 確認 `Ctrl+Enter` 仍能執行轉換
4. 再移除 `_create_conversion_controls()` 與相關布局

### 2. 新增 `TranslationSettingsDialog`，不要把現有主畫面控制項直接硬搬

原因：

- 主畫面控制列原本是即時編輯模型
- 新 dialog 是 `OK/Cancel` 模型
- 兩者互動邏輯不同，直接重用控制項事件只會引入更多條件分支

建議內容：

- `Braille Type`: `wx.Choice`
- `Width`: `wx.SpinCtrl`
- `Dictionary`: `wx.Choice`
- `Dictionary Actions...`: `wx.Button` 或對話框內操作入口

### 3. 用單一套用方法處理設定寫回

建議在 `BrailleFrame` 增加類似方法：

- `_get_translation_settings()`
- `_apply_translation_settings(settings: TranslationSettings)`

`_apply_translation_settings()` 應集中處理：

- 正規化寬度
- 更新執行期狀態
- 寫入 `config.py`
- 更新任何依賴字典選擇的畫面狀態

這會明顯改善 `SRP`，而且不必大改現有轉換流程。

### 4. `轉譯表設定...` 繼續保留獨立對話框，不合併進 `轉譯設定...`

原因：

- 目前 `TranslationTableDialog` 已獨立、可用、且模式正確
- 它處理的是「多語言對照表」設定，複雜度與一般轉譯設定不同
- 合併只會讓 `轉譯設定...` 過胖，反而降低可理解性

### 5. 字典動作維持現有能力，但把入口收斂到 `轉譯設定...`

建議保留：

- Add
- Edit
- Delete
- Rename
- Import
- Export

建議調整：

- 不再依賴主畫面 `Actions` 按鈕座標來開 popup
- 讓 `轉譯設定...` 成為字典選擇與字典管理的主要入口

## 建議不要做的事

- 不要在這次重構順手改寫轉換執行緒流程
- 不要順手改 `conversion/service.py` 的責任
- 不要把所有設定都搬進同一個超大設定視窗
- 不要新增「轉譯 controller hierarchy」之類的抽象
- 不要因為 menu 化就取消 `Ctrl+Enter`

## 推薦實作步驟

1. 新增 `轉譯` menu 與三個 menu item
2. 保留現有 `on_convert()`、`on_open_table_dialog()`，先從 menu 觸發它們
3. 新增 `TranslationSettingsDialog`
4. 抽出 `TranslationSettings` 與 `_get_translation_settings() / _apply_translation_settings()`
5. 將原本 `output_choice`、`width_spin`、`dictionary_choice` 的即時寫回邏輯收斂到新的套用流程
6. 移除主畫面的 `Conversion` controls 與相關 section 定義
7. 檢查快捷鍵、Alt menu、dictionary action、忙碌狀態、locale 字串

## 驗證重點

- `Alt` 可進入 `轉譯` menu
- `執行轉換` 可從 menu 執行
- `Ctrl+Enter` 仍可執行轉換
- `轉譯設定...` 按 `Cancel` 不應改變設定
- `轉譯設定...` 按 `OK` 後應更新：
  - output mode
  - width
  - selected dictionary
- `轉譯表設定...` 行為不回歸
- 轉換進行中時，不應留下可觸發不一致狀態的入口
- 若新增或修改使用者可見字串，需同步更新：
  - `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
  - compiled `.mo`

## 最終判斷

這次重構的核心不是「把按鈕搬去 menu」，而是把原本依附在主畫面控制列上的轉譯設定，收斂成兩種清楚的互動模型：

- `命令型動作`：`執行轉換`
- `對話框型設定`：`轉譯設定...`、`轉譯表設定...`

以 SOLID 來看，這次只需要補強 `SRP` 與設定套用邊界即可；以 design pattern 來看，只要延用既有對話框模式，加上一個很小的設定資料物件，就足以支撐需求。再往上加架構，收益不高，維護成本反而會上升。
