# DotExpress `src` 重構評估

日期：2026-07-09

## 範圍與方法

本次 review 依使用者要求，以 repo 中實際原始碼為準。此 repo 沒有獨立 `src/` 目錄，因此本文件將 `client/` 與 `server/` 視為 `src`；其中主要評估重點放在目前複雜度最高、且直接承接下一階段需求的 `client/`。

本文件先做需求導向的 superpower brainstorming，再用 Design Patterns 與 SOLID 原則檢視現況，最後只提出支撐需求所需的最小重構建議，避免 overlay design。

參考依據：

- `docs/prd/2026-07-04-dotexpress-current-state-prd_zh-TW.md`
- `docs/refactor/refactor3.md`
- `docs/superpowers/specs/2026-07-08-refactor3-next-phase-design_zh-TW.md`
- `docs/superpowers/specs/2026-06-27-translation-menu-settings-design_zh-TW.md`
- 目前 `client/`、`server/` 程式碼現況

## Superpower Brainstorming

### 先確認產品不是只剩下「轉換器」

從 PRD 與近幾輪 spec 來看，DotExpress 已經不是單次文字轉點字工具，而是逐步往「桌面工作流產品」演進。下一階段更可能擴充的是：

- 更多文件工作流，而不是更多 `gui.py` 按鈕
- 更多設定與字典流程，而不是只調整 conversion pipeline
- 更多匯入匯出與批次處理能力，而不是只增加一個副檔名分支
- 更穩定的 dual view / 校稿路徑，而不是單純把 UI 再切碎

### 下一階段最合理的需求假設

以下需求不是 roadmap 承諾，而是依現況最值得拿來評估重構方向的假設：

1. 文件工作流會繼續增長  
可能包含更多文件狀態操作、更多匯入匯出規則、更多批次行為。

2. 設定面會繼續增長  
目前已經有 Translation、Translation Tables、View 三類；後續很可能再增加更多分類或更細的 validation / apply 規則。

3. 字典工作流會繼續增長  
目前已有 add/delete/rename/import/export/edit；之後若加 preview、duplicate、usage 狀態、active dictionary fallback，現有 UI 協調點會先出現壓力。

4. 轉換會繼續嵌入其他流程  
目前 conversion 已被用在 manual convert、single export、batch export。後續若再加入 auto-convert、background refresh、document-open refresh，workflow 協調複雜度會上升。

### Brainstorming 結論

真正該優先處理的，不是再做一輪大架構重寫，而是把下列三條邊界收斂好：

- `BrailleFrame` 與各 workflow 的邊界
- 設定狀態與持久化邊界
- 字典 / 文件 / 匯出流程的 application-level 協調邊界

這些問題若不先處理，下一階段每新增一個功能，都會回到 `client/gui.py` 疊更多 event handler、message box、filesystem 操作與狀態同步。

## 現況摘要

目前已經有幾個健康的方向：

- `client/adapters/translation/` 已是合理的 Adapter / Strategy 邊界
- `client/conversion/jobs.py` 已將 conversion thread 與 stale-job protection 抽離
- `client/documents/controller.py` 已開始承接 document state
- `client/documents/formats.py` 已有 format descriptor / registry 基礎
- `client/settings/dialogs.py` 已有可重用的 Multi-category dialog / Template Method 結構

但主要壓力仍集中在：

- [client/gui.py](/workspace/DotExpress/client/gui.py:253) `BrailleFrame`
- [client/dialog.py](/workspace/DotExpress/client/dialog.py:640) 各種 dictionary / generic dialog
- [client/settings/dialogs.py](/workspace/DotExpress/client/settings/dialogs.py:123) settings dialog 與 panels

就檔案大小看，`client/gui.py` 1739 行、`client/dialog.py` 834 行、`client/settings/dialogs.py` 788 行，表示主要風險仍在 UI outer layer 與 workflow 協調層。

## Design Patterns vs SOLID Review

### 適合保留的做法

#### 1. Adapter / Strategy

`client/adapters/translation/` 的方向是正確的。translation backend 已被隔離在 runtime contract 後方，這符合 DIP，也讓後續替換 backend 的風險較低。

#### 2. Descriptor / Registry

`client/documents/formats.py` 已經用 `DocumentFormatDescriptor` 集中描述格式知識，方向正確。這種資料化 descriptor 比繼續在 GUI 層加 `if format_key == ...` 更符合 OCP。

#### 3. Template Method

`client/settings/dialogs.py` 中 `SettingsPanel` 與 `MultiCategorySettingsDialog` 的 lifecycle 設計是合理的。它已經提供：

- `load_snapshot`
- `on_save`
- `validation_error`
- `on_discard`

這比把所有 settings 邏輯堆在單一 dialog handler 乾淨得多。

### 目前最明顯的 SOLID 缺口

#### Finding 1: `BrailleFrame` 仍是過大的 application coordinator

位置：

- [client/gui.py](/workspace/DotExpress/client/gui.py:253)
- [client/gui.py](/workspace/DotExpress/client/gui.py:398)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1015)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1257)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1469)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1617)

現況：

- 建 menu
- 綁 key / menu / dialog event
- 管 document open/save/delete/import/export
- 管 dictionary active state 與 dictionary lifecycle
- 管 settings snapshot commit
- 管 conversion busy state / dialog / result routing
- 管 dual-view refresh

評估：

- `SRP` 仍明顯不足
- `ISP` 也偏弱，因為大量 workflow 都只能透過 frame 這個大介面存取

對下一階段需求的影響：

- 新增 document workflow 時，幾乎一定回到 `gui.py`
- 新增字典或 export 變體時，容易把 UI、檔案操作、狀態更新混在同一個 handler

建議：

- 不要導入 MVC / MVVM
- 直接把 document、dictionary、export 三塊 workflow 各自收斂成小型 application service / workflow module 即可

#### Finding 2: 文件 state 已有 controller，但 document workflow 仍大量留在 frame

位置：

- [client/gui.py](/workspace/DotExpress/client/gui.py:273)
- [client/gui.py](/workspace/DotExpress/client/gui.py:692)
- [client/gui.py](/workspace/DotExpress/client/gui.py:827)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1015)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1032)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1065)

現況：

- `DocumentController` 已持有 documents / open / selected / dual-view cache
- 但 open/save/rename/delete/import 後的 filesystem 與 UI 協調仍主要在 frame
- `documents`、`_open_document_name`、`_selected_document_name` 雖已委派到 controller，frame 仍保留大量「文件操作劇本」

評估：

- Pattern 上是「Controller 已存在，但還沒有成為完整的 application boundary」
- `SRP` 與 `DIP` 只做了一半

對下一階段需求的影響：

- 若之後增加「另存新檔」、「duplicate document」、「recent documents」、「unsaved indicator」，frame 會繼續膨脹

建議：

- 不要再把狀態搬回 frame
- 新增小型 `documents/workflows.py` 或等價模組，集中：
  - rename document 的磁碟與 state 更新順序
  - delete document 的磁碟與 state rollback
  - import 後的 save / issue aggregation
- `DocumentController` 繼續當 state holder
- frame 只負責 dialog、focus、message box、render

#### Finding 3: 字典 domain 已分模組，但 dictionary workflow 仍由 frame 手工協調

位置：

- [client/gui.py](/workspace/DotExpress/client/gui.py:582)
- [client/gui.py](/workspace/DotExpress/client/gui.py:620)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1257)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1279)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1310)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1349)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1394)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1443)

現況：

- dictionary entry domain 已抽到 `client/dictionaries/entries.py`
- dictionary file 操作已在 `client/dictionaries/manager.py`
- dictionary state planning 已在 `translation/dictionary_state.py`
- 但 frame 仍負責：
  - prompt
  - duplicate error message
  - file dialog
  - active dictionary 變更
  - management selection 變更

評估：

- 這是典型「有 domain helper，但缺 workflow boundary」
- `SRP` 不足，`BrailleFrame` 仍像是 dictionary use case 的實作者

對下一階段需求的影響：

- 若加上 dictionary preview、clone、default lock 規則、active dictionary badge，frame 會再增加更多例外分支

建議：

- 新增 `DictionaryWorkflow` 這種很小的 facade 即可，不需要 service hierarchy
- 將 add/delete/rename/import/export 的結果統一回傳為小型 result object，例如：
  - `active_selected_name`
  - `management_selected_name`
  - `message`
  - `error`

#### Finding 4: 設定 UI 的 pattern 是好的，但設定 state 仍有全域 mutable 邊界

位置：

- [client/gui.py](/workspace/DotExpress/client/gui.py:592)
- [client/gui.py](/workspace/DotExpress/client/gui.py:600)
- [client/gui.py](/workspace/DotExpress/client/gui.py:733)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1492)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1573)

現況：

- `DotExpressSettingsDialog` 已經有 staged snapshot / apply / validation
- 但 translation tables 仍透過 module-level `language_map_translate_table` 流動
- conversion request、settings commit、export conversion 都直接讀這份全域 dict

評估：

- 這部分違反的是較輕微但實際存在的 `DIP`
- UI 雖然 staged 了，但真正的 runtime settings source 仍不夠集中

對下一階段需求的影響：

- 若以後加入第二個 frame、background conversion queue、或更細的 settings apply policy，global mutable dict 會先成為測試與同步風險

建議：

- 不需要 DI container
- 建一個很小的 `AppSettingsState` 或 `TranslationContext` 即可，集中：
  - `translation_settings`
  - `translation_tables`
  - `view_settings`
- 讓 conversion request 從這個 object 取值，而不是直接讀 module global

#### Finding 5: Export workflow 仍混合了 UI、conversion、檔案寫入與批次控制

位置：

- [client/gui.py](/workspace/DotExpress/client/gui.py:782)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1469)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1482)
- [client/gui.py](/workspace/DotExpress/client/gui.py:1514)

現況：

- format descriptor 已集中
- conversion per-job policy 也已抽出
- 但 export single / export all 仍主要靠 frame 內 callback 串接

評估：

- Pattern 上已接近 Command / Workflow，但還停在 event-handler 形式
- `SRP` 與 `OCP` 改善了一部分，但還沒完全收斂

對下一階段需求的影響：

- 如果新增更多 export 類型、更多 conflict policy、或「匯出前自動轉換」選項，這段會持續長大

建議：

- 不用引入 workflow engine
- 只要把 export orchestration 搬到 `documents/export_workflow.py` 之類的 plain module
- frame 保留：
  - 選路徑
  - 顯示結果
  - 啟動 workflow

#### Finding 6: Settings dialog 本身已可用，但 `client/settings/dialogs.py` 已接近下一次切檔門檻

位置：

- [client/settings/dialogs.py](/workspace/DotExpress/client/settings/dialogs.py:123)
- [client/settings/dialogs.py](/workspace/DotExpress/client/settings/dialogs.py:304)
- [client/settings/dialogs.py](/workspace/DotExpress/client/settings/dialogs.py:400)
- [client/settings/dialogs.py](/workspace/DotExpress/client/settings/dialogs.py:523)
- [client/settings/dialogs.py](/workspace/DotExpress/client/settings/dialogs.py:630)

現況：

- 架構本身合理
- 但 panel 類別、dialog skeleton、table option 邏輯都在同一檔

評估：

- 這比較像 module boundary 問題，不是 pattern 問題
- 目前仍可接受，但若下一階段要再加 category，就應切檔

建議：

- 現在不必優先動
- 但若要新增第 4 個以上 settings category，就先拆成：
  - `settings/dialog_base.py`
  - `settings/panels/translation.py`
  - `settings/panels/tables.py`
  - `settings/panels/view.py`

## 不建議的重構

以下都屬於 over design，這一輪不建議做：

- 將整個 client 改寫成完整 MVC / MVP / MVVM
- 導入 DI container
- 為每個 menu item 建 command class
- 為 document / dictionary / export 建一整套 service inheritance hierarchy
- 把 server 也一起做大規模 service layer 重構

原因很簡單：目前真正的痛點不是抽象不足，而是 workflow 邊界還停留在 `BrailleFrame`。

## 需求導向的最小重構建議

### 優先 1：先切出 document workflow

目標：

- 讓 `BrailleFrame` 不再實作 rename/delete/import 的完整劇本

建議最小新增：

- `client/documents/workflows.py`

先搬出的 use cases：

- `rename_document_workflow`
- `delete_document_workflow`
- `import_documents_workflow`

收益：

- 直接改善 `gui.py` 的 SRP
- 為後續 document 功能擴充預留位置

### 優先 2：再切出 dictionary workflow facade

目標：

- 讓 frame 不再手工串接 dictionary prompt、state planning、active selection 更新

建議最小新增：

- `client/dictionaries/workflows.py`

先搬出的 use cases：

- `add_dictionary_workflow`
- `delete_dictionary_workflow`
- `rename_dictionary_workflow`
- `import_dictionary_workflow`
- `export_dictionary_workflow`

收益：

- 新增字典需求時，不必再把例外邏輯都加回 `gui.py`

### 優先 3：把 runtime settings 集中成單一 object

目標：

- 移除 `language_map_translate_table` 這類 module-global runtime state 的中心地位

建議最小新增：

- `client/settings/runtime_state.py` 或等價模組

集中內容：

- translation settings
- translation tables
- view settings

收益：

- 讓 settings dialog、conversion request、export conversion 共用單一 runtime state source

### 優先 4：最後再收斂 export orchestration

目標：

- 將 single export / batch export 從 frame handler 轉成可測試的 workflow function

建議最小新增：

- `client/documents/export_workflow.py`

收益：

- 若之後新增更多 export format 或 export policy，不必擴大 `gui.py`

## 建議的重構順序

1. 先做 document workflow  
因為這會影響最多主流程，而且最能立刻降低 `gui.py` 責任。

2. 再做 dictionary workflow  
因為它已經有 domain helper，補上 facade 成本低、收益高。

3. 接著集中 runtime settings state  
因為這能避免後續功能又重新依賴 global mutable state。

4. 最後再做 export orchestration  
因為它的重要性高，但建立在前面三步收斂後會比較乾淨。

## Server 評估

`server/app/main.py` 目前只有約 49 行，整體也仍是很薄的初始化服務。就下一階段需求來看，server 不是現在的重構瓶頸，不建議把精力分散到 server。

## 結論

若從 Design Patterns vs SOLID 來看，DotExpress 目前最值得保留的是：

- translation adapter 邊界
- document format descriptor
- settings dialog 的 staged snapshot pattern

最需要補強的則不是新 pattern，而是 workflow boundary：

- document workflow
- dictionary workflow
- runtime settings state
- export orchestration

這樣的重構路線能支撐下一階段需求，同時避免為了「看起來很完整的架構」而過度設計。
