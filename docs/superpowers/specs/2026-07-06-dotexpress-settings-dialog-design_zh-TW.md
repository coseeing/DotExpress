# DotExpress 設定多類別對話框設計

日期：2026-07-06

## 目標

將 DotExpress 現有分散的轉譯設定、轉譯表設定、檢視設定整合為一個參考 NVDA `settingsDialogs.py` 設計的多類別設定對話框，改善目前因 `Fit()` 導致項目少時視窗過小的問題，並建立可擴充的設定框架。

本次重構的結果必須符合以下使用者體驗：

- Translation menu 下只保留一個「設定」入口。
- 開啟後顯示同一個多類別設定對話框，標題為 `DotExpress 設定：<目前分類>`。
- 預設停在「轉譯」分類。
- 左側分類順序固定為：
  1. 轉譯
  2. 轉譯表
  3. 檢視
- 設定內容採 staged model；只有按下 `套用` 或 `確定` 才會生效。
- 主畫面原本可見的檢視控制項移除，但既有字體大小快捷/滾輪調整保留。

## 參考來源與對齊範圍

本設計參考 `include/nvda/source/gui/settingsDialogs.py` 的以下概念與行為：

- `SettingsDialog`
- `SettingsPanel`
- `MultiCategorySettingsDialog`
- `SpeechSettingsPanel`
- `SynthesizerSelectionDialog`
- `NVDASettingsDialog` 對分類切換時更新視窗標題的處理

對齊的重點如下：

- 多類別左側清單 + 右側內容區的整體視覺結構
- 對話框固定初始尺寸與最小尺寸，而非單純依內容 `Fit()`
- `OK / Cancel / Apply` 的 staged 提交流程
- `initialCategory` 機制
- 切換分類時同步更新視窗標題
- 使用 `Ctrl+Tab` / `Ctrl+Shift+Tab` 循環切換分類並在首尾 wraparound
- panel 層級的 accessibility helper
- 單一設定視窗實例的 multi-instance guard
- 採 modeless dialog 生命週期，使既有 instance 可被 bring-to-front 與聚焦

以下項目這次不納入：

- NVDA 的 context help / `helpId` 整合
- NVDA 的完整 multi-instance exception 流程
- NVDA 專屬 accessibility/context help infrastructure

## 使用者可見變更

### 1. Translation menu 調整

目前 Translation menu 內多個設定入口改為單一入口：

- `設定`

保留的其他項目例如 `Dual View` 不在本次調整範圍內，除非它們的排序因 menu 重組需要微調。

### 2. 新的多類別設定對話框

新增一個使用者可見的設定對話框：

- 對話框基礎標題：`DotExpress 設定`
- 切換分類後標題格式：`DotExpress 設定：轉譯`、`DotExpress 設定：轉譯表`、`DotExpress 設定：檢視`

左側分類顯示順序固定為：

1. 轉譯
2. 轉譯表
3. 檢視

開啟對話框時預設停在「轉譯」。

dialog 內任何位置有 focus 時，`Ctrl+Tab` 選取下一個分類，
`Ctrl+Shift+Tab` 選取上一個分類，並在首尾循環。此行為沿用 NVDA 的分類導覽，
不取代 category list 取得 focus 時原有的方向鍵操作。

### 3. 主畫面檢視控制項移除

主畫面目前的 View 區塊移除，包括：

- Font Size
- Braille Font
- Scheme / 配色

主畫面因此回歸以編輯與輸出區為核心，不再在主畫面直接顯示這三個設定控制項。

### 4. 主畫面快捷調整保留

雖然可見的 View 控制項移除，但既有的字體大小快捷/滾輪調整行為保留。這代表檢視設定仍有兩條修改途徑：

- 設定對話框：staged，`套用/確定` 才生效
- 主畫面快捷/滾輪：直接生效

兩者都必須最終更新同一份 view 設定來源，避免長期狀態分裂。

## 架構設計

### 新增通用設定框架

新增 DotExpress 版設定框架模組 `client/settings_dialogs.py`，包含以下類別。
將這個使用者可見的 wxPython dialog 放在 `client/dialog.py` 同一層，也可確保現有
localization extraction script 會掃描其中的 `_()` 字串。

#### `SettingsDialog`

職責：

- 提供對話框共用結構
- 建立按鈕列：`OK / Cancel / Apply`
- 支援可 resize 視窗
- 支援 `INITIAL_SIZE`、`MIN_SIZE`
- 提供標準的 `on_ok`、`on_cancel`、`on_apply` 流程
- 提供 close / destroy hooks，讓子類別可清除單一實例狀態

這個類別不負責多分類清單，只處理一般設定對話框基礎行為。

#### `SettingsPanel`

職責：

- 作為每個設定分類頁的基底 panel
- 提供一致的 GUI 建構入口，例如 `make_settings`
- 提供 staged model 生命周期方法：
  - `on_panel_activated`
  - `on_panel_deactivated`
  - `on_save`
  - `on_discard`
  - 必要時 `is_valid`
- 提供 panel title 與 panel description 供 UI 與 accessibility helper 使用

這個類別不直接寫入 config，也不直接操作主視窗最終狀態；它只負責將控制項值同步到 staged model。

#### `MultiCategorySettingsDialog`

職責：

- 建立左側 categories list 與右側 panel container
- 支援 `initial_category`
- 依分類延遲建立 panel instance
- 管理 panel 切換、`Apply`、`OK`、`Cancel`
- 提供 scrollable 的右側內容區
- 允許子類別覆寫分類切換後行為，例如更新 title

這個類別負責通用多類別設定框架，但不直接綁定 DotExpress 的具體設定內容。

#### `DotExpressSettingsDialog`

職責：

- 實際承載本次使用者看得到的 DotExpress 設定 UI
- 指定 category classes 的順序：
  1. `TranslationSettingsPanel`
  2. `TranslationTablesPanel`
  3. `ViewSettingsPanel`
- 開啟時預設落在 `TranslationSettingsPanel`
- 在分類切換時更新標題為 `DotExpress 設定：<分類名>`
- 持有 staged settings snapshot
- 在提交時通知主視窗套用最終設定
- 擁有 single-instance guard；通用 base classes 不可全面阻止其他 settings
  dialog subclasses 開啟

### Dialog 生命週期

`DotExpressSettingsDialog` 採 modeless，使用 `Show()` 開啟。主視窗保留存活的
instance，直到 dialog 被 destroy。這是指定 bring-to-front 行為的必要條件；
若使用 modal `ShowModal()`，主視窗 menu 會被阻擋，正常入口下的 guard 將無法
發揮作用。

經由 `取消`、`確定` 或視窗關閉按鈕關閉時，都必須 destroy 視窗並清除保留的
reference。視窗關閉按鈕的語意與 `取消` 相同，未提交的內容一律丟棄。

## 視覺與排版設計

### 對話框尺寸

為避免現有 `Fit()` 導致視窗過小，本對話框採固定初始尺寸與最小尺寸。

建議值：

- `INITIAL_SIZE = (720, 440)`
- `MIN_SIZE = (520, 300)`

理由：

- 比目前小型 dialog 更穩定
- 足以容納右側 panel 的表單
- 不會像 NVDA 主設定視窗一樣過重

### 版面結構

整體結構參考 NVDA：

- 上方：categories label
- 左側：分類清單
- 右側：內容 panel 容器
- 底部：`OK / Cancel / Apply`

初始視覺建議：

- 左側分類欄初始寬度約 `150`
- 右側內容區使用剩餘主要空間
- resize 時沿用類似 NVDA 的 grow 比例：左 1，右 3
- 初始大小由明確 size 設定，不依 grow proportion 決定

### 右側內容容器

右側內容區使用可捲動 panel，確保：

- 類別內容多時可垂直捲動
- 小類別內容不會反過來讓整個對話框縮小
- 未來若新增更多選項，不需重新設計整體尺寸策略

## Accessibility helper 設計

本次將 accessibility helper 納入。

### 目的

- 讓 assistive technologies 更清楚辨識右側目前內容是一個設定頁
- 將目前分類的描述與語意與 panel 綁定

### 設計

為 `SettingsPanel` 實作對應的 accessible helper，參考 NVDA `SettingsPanelAccessible` 的概念：

- panel role 應對應 property-page 類型語意
- panel description 來自各 panel 的 `panel_description`
- active panel 切換後，新的 panel 應維持正確 accessible metadata

### 對各 panel 的使用者可見文案

- `轉譯`：轉譯輸出模式、寬度與字典選項
- `轉譯表`：不同語言的轉譯表對應
- `檢視`：主視窗輸入/輸出區的字型、字體大小與配色

這些 description 不一定要完整顯示在畫面上，但應可供 accessibility helper 使用。

## Multi-instance guard 設計

本次將 multi-instance guard 納入。

### 目標

同一時間只允許一個 `DotExpressSettingsDialog` 存在，避免：

- 使用者開多個設定視窗同時編輯同一組 staged state
- `Apply/OK` 的先後順序造成狀態覆蓋
- 主視窗狀態與對話框暫存值不同步

### 行為

當使用者再次嘗試開啟 DotExpress 設定時：

- 若現有實例仍存在，則不建立新視窗
- 直接 bring-to-front 現有視窗
- 若未來使用程式路徑支援 `initialCategory`，則可同步切換到指定分類

即使目前 UI 只有單一入口，底層仍保留 `initialCategory` 支援，作為未來擴充或內部導向能力。

guard 應屬於 `DotExpressSettingsDialog`，不可放在 `SettingsDialog` 全域套用。
若保留的 instance 仍存活，open helper 應視需要切換指定分類、還原最小化視窗，
接著呼叫 `Raise()` 與 `SetFocus()`。reference 若已失效或視窗已 destroy，應先
清除再建立新 dialog。

## Panel 設計

### `TranslationSettingsPanel`

標題：`轉譯`

來源：取代現有 `TranslationSettingsDialog`

內容：

- Braille Type
- Width
- Dictionary

職責：

- 顯示 staged translation settings
- 使用者在 panel 內變更控制項時，只更新 panel 本地控制狀態
- `on_save` 時寫回 staged model 的 translation settings 區塊
- 驗證 width 與 dictionary selection 是否有效

不直接做的事：

- 不直接更新主視窗的 `translation_settings`
- 不直接寫入 config

### `TranslationTablesPanel`

標題：`轉譯表`

來源：取代現有 `TranslationTableDialog`

內容：

- default
- en
- zh
- ja
- math

職責：

- 顯示 staged translation tables mapping
- 保留原本各語系可選表格的篩選邏輯
- `on_save` 時將目前選取值寫回 staged translation tables model
- `default` 與 `math` 必須有有效選項；`en`、`zh`、`ja` 可沿用現有
  `None selected` 的空值

不直接做的事：

- 不直接寫入 config
- 不直接刷新主視窗

### `ViewSettingsPanel`

標題：`檢視`

來源：吸收主畫面原本的 View 區塊

內容：

- Font Size
- Braille Font
- Scheme / 配色

職責：

- 顯示 staged view settings
- `on_save` 時將值寫回 staged view settings model
- 驗證字體大小必須落在既有範圍內
- 點字字型與配色使用既有合法值正規化邏輯

注意：

- 在 panel 中變更這些值時，不立即影響主畫面
- 只有按下 `套用/確定` 後，由外層 dialog 通知主視窗真正套用

## 資料流與狀態管理

### Staged model

`DotExpressSettingsDialog` 開啟時建立 staged settings snapshot。建議至少包含：

- `translation_settings`
  - `output_mode`
  - `width`
  - `selected_dictionary`
- `translation_tables`
  - `default`
  - `en`
  - `zh`
  - `ja`
  - `math`
- `view_settings`
  - `font_size`
  - `braille_font`
  - `scheme`

這份 staged snapshot 必須與主視窗目前狀態解耦，使 `Cancel` 能安全丟棄變更。

snapshot 必須由正規化後的 application state 複製而來，不可直接持有 mutable
global dictionary。特別是 translation-table mappings 必須複製，避免 panel
編輯在 commit 前就改動 `language_map_translate_table`。

### Apply / OK 流程

1. 對所有已建立 panel 執行 `is_valid`
2. 對所有已建立 panel 執行 `on_save`，將控制項值回寫到 staged snapshot
3. 由 `DotExpressSettingsDialog` 統一呼叫主視窗提供的 apply 入口
4. 主視窗一次完成：
   - 更新 translation settings
   - 更新 translation tables
   - 更新 view settings
   - 套用主畫面外觀變更
   - 寫入 config / 持久化設定

`OK` 在成功提交後關閉對話框。`Apply` 則保留對話框繼續編輯。

成功 `套用` 後，已提交值成為 dialog 的新 baseline：

- 以主視窗 commit 入口回傳的正規化值刷新 staged snapshot
- 將已建立 panels 同步至此 baseline
- 清除 panel dirty state

因此之後按 `取消` 只會丟棄最近一次成功 `套用` 之後的編輯，不會復原已套用的設定。

### Cancel 流程

1. 不提交 staged snapshot
2. 呼叫各 panel `on_discard`（若有需要）
3. 關閉對話框

因為 staged model 與主畫面分離，`Cancel` 不需要額外回滾主畫面。

dialog 必須先收集並驗證所有已建立 panel 的值，之後才能呼叫主視窗 commit
入口。驗證失敗時，不可局部改寫代表最近一次成功套用狀態的 staged snapshot。

## 主視窗整合設計

### 需要移除的主畫面 UI

從 `BrailleFrame` 主畫面移除目前 View 區塊以及其控制項：

- font size spin control
- braille font choice
- color scheme controls

主畫面 layout 需重新整理，讓輸入/輸出區塊在垂直與水平空間上自然補滿。

移除後的 controls 不可繼續作為隱藏狀態。應在 `BrailleFrame` 引入明確且正規化
的 view-settings value；畫面 rendering 與快捷處理都從該 value 讀寫。

### 需要保留的主畫面能力

保留既有字體大小快捷/滾輪調整。這些互動屬於直接生效路徑，與設定對話框的 staged 模式並存。

這代表主視窗需要持續擁有以下能力：

- 直接套用 view font size 變更
- 將直接變更同步回設定儲存層

既有 section-navigation order 也必須移除已刪除的 View section，使 section
快捷只在文件清單、來源文字與點字結果之間循環。

### 主視窗應新增的 apply 入口

建議主視窗提供單一方法，供 `DotExpressSettingsDialog` 提交使用，例如：

- `apply_settings_from_dialog(...)`

此方法統一處理：

- translation settings 寫回
- translation tables 寫回
- view settings 寫回
- 視覺刷新
- 設定儲存

這樣可避免 panel 直接耦合主視窗內部細節。

commit method 應回傳實際接受的正規化設定，讓 dialog 建立正確的 post-Apply
baseline。

### Modeless dialog 開啟期間的設定變更

主視窗字體大小快捷與滑鼠滾輪仍直接生效。若設定 dialog 開啟期間發生：

- 更新並持久化主視窗明確的 view-settings value
- 若 View panel 的 font-size field 尚未修改，將新值同步至 staged snapshot
  與 control
- 若該 field 已是 dirty，保留使用者 draft；之後按 `套用/確定` 時，由 draft
  明確覆蓋快捷調整後的值

配色與點字字型沒有保留主視窗快速調整途徑，因此不需此衝突規則。

## 標題更新行為

`MultiCategorySettingsDialog` 基底不強制更新視窗標題。

`DotExpressSettingsDialog` 在分類切換時必須更新視窗標題，參考 NVDA `NVDASettingsDialog` 的行為：

- `轉譯` active 時：`DotExpress 設定：轉譯`
- `轉譯表` active 時：`DotExpress 設定：轉譯表`
- `檢視` active 時：`DotExpress 設定：檢視`

此行為應同時適用於：

- 初始開啟時
- 使用左側 categories list 切換時
- 既有 dialog instance 被重新喚回並切換分類時（若未來啟用）

## 錯誤處理

### 驗證錯誤

若 panel 中設定值無效：

- `Apply/OK` 應中止
- 不得提交任何 staged model 到主視窗
- 焦點應盡量回到出錯 panel 與相關控制項
- 必要時顯示錯誤訊息對話框

### 重複開啟設定視窗

若設定視窗已存在：

- 不顯示錯誤
- 直接 bring-to-front 與聚焦既有視窗

視窗關閉按鈕採 `取消` 語意，不得套用 pending changes。

### 部分 panel 尚未建立

由於 panel 可延遲建立：

- `Apply/OK` 只會處理已建立 panel 與 staged snapshot
- 未進入過的 panel 保持開啟時 snapshot 內容
- 這些值仍應被完整提交

## 測試策略

### 單元測試

新增或更新測試，至少涵蓋：

- 新 settings framework 基底類別的 title / category 切換邏輯
- multi-instance guard 行為
- staged model 在 `Apply/OK/Cancel` 的差異
- `TranslationSettingsPanel` 的值讀寫與驗證
- `TranslationTablesPanel` 的初始值與選項同步
- `ViewSettingsPanel` 的值讀寫與驗證
- 主視窗 apply 入口是否正確收到 staged 資料
- Translation menu 僅保留單一設定入口
- 向前、向後切換分類及首尾循環

### GUI 層級回歸測試

更新既有依賴以下對話框的測試：

- `TranslationSettingsDialog`
- `TranslationTableDialog`

若這兩者被完全取代，相關測試應改為針對新 `DotExpressSettingsDialog` 與對應 panel 行為驗證。

### 手動驗證重點

至少確認以下流程：

1. 從 Translation menu 開啟 `設定`
2. 預設落在 `轉譯`
3. 切換到 `轉譯表`、`檢視` 時 title 有同步改變
4. 修改任一 panel 後按 `Cancel`，主畫面與 config 不變
5. 修改 `檢視` 後按 `Apply`，主畫面字型/配色更新
6. 主畫面快捷/滾輪改字體大小後，設定對話框下次開啟能看到最新值
7. dialog 開啟且 View 字體大小未修改時，透過保留的主視窗快捷路徑變更字體，
   確認 staged value 同步
8. 先將 View 字體大小設為 dirty，再執行主視窗快速調整，確認 draft 會保留至
   `套用/確定`
9. 嘗試重複開啟設定對話框時只會聚焦既有視窗

## 實作切分建議

1. 建立 settings framework 基底類別
2. 建立 `DotExpressSettingsDialog` 與三個 panel
3. 將舊的 translation settings / translation tables UI 邏輯搬入 panel
4. 將主畫面 view controls 搬入 `ViewSettingsPanel`
5. 主畫面移除 View 區塊並補上新的 dialog 開啟入口
6. 接上 staged model 與 apply 提交路徑
7. 補 accessibility helper 與 multi-instance guard
8. 更新測試

## 非目標

本次不處理以下事項：

- 建立完整獨立的 Settings menu 系統
- 重構 Dual View 本身的行為
- 增加新設定分類（例如字典管理、匯出設定等）
- 將所有主畫面快捷操作都改成 staged 模型

## 決策摘要

- 採用 DotExpress 版 `SettingsDialog / SettingsPanel / MultiCategorySettingsDialog`
- 使用單一入口 `Translation -> 設定`
- 對話框標題採 `DotExpress 設定：<分類名>`
- 左側分類順序：轉譯、轉譯表、檢視
- 主畫面移除可見的 View 控制項
- 主畫面字體大小快捷/滾輪保留
- 導入 accessibility helper
- 導入 multi-instance guard
- 採 modeless dialog，視窗關閉按鈕語意等同 `取消`
- 設定採 staged model，`Apply/OK` 才提交
- 成功 `套用` 後以已提交值作為新的 Cancel baseline
