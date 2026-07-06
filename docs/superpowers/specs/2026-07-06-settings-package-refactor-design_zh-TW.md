# DotExpress 設定 Package 重構設計

日期：2026-07-06

## 目標

將 DotExpress 與設定相關的模組集中到單一的 `client/settings/` package，
讓設定資料模型、持久化 helper、staged snapshot 狀態，以及設定對話框 UI
都位於一致且清楚的命名空間下。

這次重構的目標是改善可發現性，並讓未來新增設定分類時有固定落點，同時不改變使用者可見的設定行為。

## 範圍

這次變更包含：

- 將 `client/view_settings.py` 的檢視設定邏輯搬到 `client/settings/view.py`
- 將 `client/translation/settings.py` 的轉譯設定邏輯搬到 `client/settings/translation.py`
- 新增專用的 `client/settings/translation_tables.py`，處理轉譯表設定的持久化 helper
- 將 `client/settings_state.py` 搬到 `client/settings/state.py`
- 將 `client/settings_dialogs.py` 搬到 `client/settings/dialogs.py`
- 更新應用程式與測試的 import 路徑，改用新的 package 結構

這次變更不包含：

- 修改設定對話框的 UX、分類順序或 staged apply 行為
- 重設計 `config.py`
- 修改使用者可見字串
- 立即再往下拆成 `constants.py` 或 `persistence.py` 等更深層結構

## 目前問題

目前設定相關程式碼散落在多個不一致的位置：

- `client/view_settings.py`
- `client/settings_state.py`
- `client/settings_dialogs.py`
- `client/translation/settings.py`
- `client/config.py`

這造成四個實際問題：

1. 必須先知道專案歷史，才找得到設定邏輯放在哪裡。
2. 轉譯設定是依功能區塊分組，view/state/dialog 卻是依歷史檔名分組，結構不一致。
3. `gui.py` 需要從多個彼此無關的路徑匯入設定功能。
4. 未來新增設定類別時，很可能繼續複製這種分散結構。

## 評估方案

### A. 維持現狀

繼續把設定邏輯放在最早需要它的功能模組旁邊。

這樣可以避免 import 路徑改動，但會保留目前分散的結構問題。

### B. 導入扁平的 `client/settings/` Package

將所有設定相關模組集中到同一 package，並使用聚焦的檔名：

- `view.py`
- `translation.py`
- `translation_tables.py`
- `state.py`
- `dialogs.py`

這能建立單一設定命名空間，同時避免過度分層。

### C. 直接導入更深的分層 Package

將設定搬進 `client/settings/` 後，立刻再細分成：

- `models/`
- `ui/`
- `persistence/`
- `constants/`

這在結構上更乾淨，但以目前模組數量與大小來看，還不值得增加額外導覽成本。

## 決策

採用方案 B。

方案 B 抓住了這次重構的主要價值：讓設定程式碼有一個明確、單一的歸屬位置。
它避免了方案 C 的過早切細，同時也保留未來若 `dialogs.py` 或 persistence helper
明顯膨脹時，再往更深結構演進的空間。

## 目標結構

```text
client/
├── settings/
│   ├── __init__.py
│   ├── dialogs.py
│   ├── state.py
│   ├── translation.py
│   ├── translation_tables.py
│   └── view.py
├── config.py
└── gui.py
```

## 模組責任

### `client/settings/view.py`

職責：

- 定義 `ViewSettings`
- 定義檢視設定常數與合法 key
- 正規化檢視設定值
- 從 `config.py` 讀取檢視設定
- 透過 `config.py` 儲存檢視設定

此模組不應包含 wx UI 程式碼。

### `client/settings/translation.py`

職責：

- 定義 `TranslationSettings`
- 正規化轉譯設定值
- 從 `config.py` 讀取轉譯設定
- 透過 `config.py` 儲存轉譯設定

此模組是轉譯設定資料與持久化邏輯的唯一權威位置。

### `client/settings/translation_tables.py`

職責：

- 提供轉譯表設定的讀取與儲存 helper
- 集中設定流程中需要的預設 mapping 正規化邏輯
- 保持轉譯表 persistence 與 wx UI 層分離

此模組不負責從 liblouis 探索可用表格選項。那部分仍屬於 dialog layer，
因為它依賴呈現需求與執行期資料。

### `client/settings/state.py`

職責：

- 定義 `DotExpressSettingsSnapshot`
- 集中 staged settings state 的建立、複製與更新 helper

此模組依賴設定資料模型，不依賴 wx UI。

### `client/settings/dialogs.py`

職責：

- 定義可重用的 settings dialog framework 類別
- 定義 DotExpress 各設定 panel
- 定義 `DotExpressSettingsDialog`
- 透過 `DotExpressSettingsSnapshot` 協調 staged settings editing

這是 package 內唯一主要依賴 wx 的設定模組。

## Import 邊界

預期的依賴方向如下：

- `settings/view.py`、`settings/translation.py`、`settings/translation_tables.py`
  可以依賴 `config.py`
- `settings/state.py` 可以依賴設定模型模組
- `settings/dialogs.py` 可以依賴 `settings/state.py` 與設定模型模組
- `gui.py` 可以依賴整個 `settings` package

反向依賴則不允許：

- 設定模型或 persistence 模組不得 import `dialogs.py`
- `config.py` 不得 import `settings` package

這樣可讓 wx UI 保持在最外層。

## Package 對外介面

`client/settings/__init__.py` 應重新匯出應用程式與測試常用的設定 API：

- `DotExpressSettingsDialog`
- `DotExpressSettingsSnapshot`
- `TranslationSettings`
- `ViewSettings`
- `load_translation_settings`
- `save_translation_settings`
- `normalize_translation_settings`
- `load_translation_tables`
- `save_translation_tables`
- `normalize_translation_tables`
- `load_view_settings`
- `save_view_settings`
- `normalize_view_settings`

目標不是隱藏所有 submodule。當呼叫端只需要單一關注點時，仍可直接 import
對應 submodule。這些 re-export 只是提供 package 的明確入口。

## 遷移策略

### 步驟 1：建立 Package 並搬移模組

建立 `client/settings/`，將目前頂層的設定模組搬進去。

### 步驟 2：拆出轉譯表 Persistence

將轉譯表設定的讀寫 helper 從 `gui.py` 的直接呼叫點移入
`settings/translation_tables.py`。

`gui.py` 不應再直接呼叫 `config.get_translation_tables()` 與
`config.set_translation_tables()`。

### 步驟 3：更新應用程式 Import

更新 `gui.py` 與其他受影響應用程式模組的 import 路徑，改用新的 package 結構。

### 步驟 4：更新測試

更新以下測試的 import：

- `client/tests/test_view_settings.py`
- `client/tests/test_settings_state.py`
- `client/tests/test_settings_dialogs.py`
- `client/tests/test_gui_document_flows.py`
- `client/tests/test_translation_settings.py`

如果測試失敗暴露出其他設定消費者，也要一併更新。

### 步驟 5：維持行為穩定

這次重構必須保留：

- 目前設定對話框行為
- 目前 config 檔 key 與持久化行為
- 目前 view normalization 行為
- 目前 translation settings normalization 行為
- 目前 translation-table 的 save/apply 流程

## 錯誤處理與相容性

這是內部重構，因此不需要維持舊 import 路徑的向後相容。

此 repo 看起來是單一應用程式的內部模組，而非對外發布的函式庫。
若保留暫時性 compatibility shim，只會拉長遷移面而沒有實際使用者收益。

如果某個被搬移的模組行為被測試依賴，應直接更新測試到新的 import 路徑，
而不是依賴 alias module。

## 測試計畫

至少執行以下聚焦的 client 測試，覆蓋設定模組與設定對話框：

- `python3 -m unittest tests.test_view_settings -v`
- `python3 -m unittest tests.test_settings_state -v`
- `python3 -m unittest tests.test_settings_dialogs -v`
- `python3 -m unittest tests.test_translation_settings -v`
- `python3 -m unittest tests.test_gui_document_flows -v`

依照 repo 指南，這些命令應從 `client/` 目錄執行。

## 未來延伸路徑

如果未來設定程式碼繼續成長，這個 package 可以再往方案 C 演進，例如：

- 將 `dialogs.py` 再拆成 UI framework 與 DotExpress 專用 panels
- 將 persistence helper 從設定資料定義中再分開
- 當常數變成跨模組共用關注點時，再抽出 shared constants

這種再切分應由實際模組膨脹驅動，而不是在這次重構中預先完成。
