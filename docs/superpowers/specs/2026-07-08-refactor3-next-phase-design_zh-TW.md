# DotExpress Refactor 3 下一階段設計

日期：2026-07-08

## 背景

`docs/refactor/refactor3.md` 已確認前一輪重構成果已經落地：

- `DocumentController` 已存在
- dictionary entry domain 已搬到 `client/dictionaries/entries.py`
- conversion job runner 已搬到 `client/conversion/jobs.py`
- `client/conversion/service.py` 已成為較薄的 facade

因此下一階段的重點不再是重複抽出同類型模組，而是把已存在邊界收斂成真正穩定的單一來源與擴充點，降低 `BrailleFrame` 中殘留的狀態同步與 workflow 協調風險。

## Superpower Brainstorming 結論

這次先確認三個問題，再決定 spec 範圍。

### 問題 1：現在最大的維護風險是什麼

不是「檔案太大」本身，而是 `client/gui.py` 同時保存多份互相鏡像的狀態：

- frame 內 document 狀態
- `DocumentController` 內 document 狀態
- conversion workflow 的 per-job UI policy
- import/export format 的分散規則

真正高風險點是這些狀態分散後仍需要手動同步。

### 問題 2：下一階段應優先做哪一類重構

應優先做「邊界收斂」，不是再做一輪大規模 package split。

原因：

1. `DocumentController` 已存在，現在最值得做的是讓它成為 document state single source of truth。
2. conversion thread runner 已存在，但 UI completion policy 仍掛在 frame mutable fields，上層邏輯還沒收斂。
3. import/export format 仍散落在 GUI 與 workspace 分支判斷中，是明顯的 OCP 缺口。

### 問題 3：哪些事情這一輪不要做

這一輪不做：

- 重設計 wx UI
- 改寫成完整 MVC / MVVM
- 導入 DI container
- 再抽 generic pipeline framework
- 優先處理 server 重構
- 改動 user-visible strings、menu 順序或 export/import 行為

## 目標

將下一階段重構聚焦為三個可驗證的目標：

1. 讓 `DocumentController` 成為文件狀態單一來源
2. 收斂 conversion UI workflow state，移除 frame 全域 mutable policy 欄位
3. 建立 document format descriptor / registry，集中 import/export format knowledge

這三項完成後，`BrailleFrame` 仍是 wx outer layer，但不再負責保存與協調過多 domain state。

## 範圍

這次變更包含：

- 擴充 `client/documents/controller.py` 的 read-only state surface 與 state transition API
- 修改 `client/gui.py`，讓 document 相關流程優先透過 controller 讀寫
- 新增 conversion UI workflow state object，讓 per-job completion policy 跟著 request/result 走
- 修改 `client/gui.py` 與 `client/conversion/jobs.py` 的協作邊界
- 新增 `client/documents/formats.py` 或等價模組，集中 format descriptor / registry
- 修改 import/export 相關流程改讀 registry
- 補上對應 focused tests 與既有 GUI flow regression coverage

這次變更不包含：

- settings dialog panel split
- `client/dialog.py` 剩餘 UI class split
- server 端 service layer
- 新增任何新的 document format
- 調整 import/export 的使用者可見字串

## 需求確認

### 需求 1：DocumentController 必須是唯一文件狀態來源

`BrailleFrame` 不應再持有與 controller 等價的可變文件狀態副本。

具體要求：

- document list 應由 controller 持有
- selected/open document name 應由 controller 持有
- dual-view cache 應由 controller 持有或由 controller 擁有唯一權威更新路徑
- `BrailleFrame.documents` 若短期保留，必須改為委派 property，而不是獨立 state
- `_sync_document_controller_state()` 應被移除，或縮減成單向 compatibility shim，最後可刪除

### 需求 2：Conversion workflow policy 必須變成 per-job state

目前 manual convert、single export、batch export 共用同一組 frame 欄位傳遞 completion policy，這使 stale job 或流程交錯時風險偏高。

具體要求：

- conversion request 需攜帶完成後的 UI policy
- success / error / output update / success message 類型設定不得再依賴 frame 全域 mutable fields
- stale-job protection 仍由 job runner 維持
- `BrailleFrame` 仍負責 wx dialog、message box 與 control 更新，不把 wx 物件傳入 non-wx domain module

### 需求 3：Document format knowledge 必須集中管理

新增格式時，不應同時修改 GUI、workspace、wildcard 與 suffix 分支邏輯。

具體要求：

- 定義 descriptor 統一描述 `key`、extension、wildcard label、loader、writer、是否需要 braille、是否支援 import/export
- 現有 `IMPORT_LOADERS` 應由 registry 產生，或與 registry 保持單一來源
- `dep` 與 `brl` export 流程優先 descriptor 化
- 不新增新格式，不改既有 labels 與副檔名

## 設計決策

### 決策 1：延續 Application Controller，而不是回到 frame-centric state

`DocumentController` 已經是最接近穩定邊界的位置。下一步不是把更多狀態搬回 `BrailleFrame`，而是讓 frame 只做：

- 事件接收
- wx controls update
- dialog / message box
- 呼叫 controller 與 use-case helper

### 決策 2：用小型 State Object 表示 conversion completion policy

不引入更重的 workflow engine。

使用小型 dataclass 即可，例如：

- `ConversionUiRequest`
- `ConversionCompletionPolicy`
- `ConversionWorkflowResult`

這些型別只描述流程意圖，不直接依賴 wx。

### 決策 3：用 Descriptor / Registry 集中文件格式規則

這一層不追求 plugin system，只做 repo 內部一致的格式描述。

registry 應提供：

- importable formats
- exportable formats
- file dialog wildcard 文字
- format key -> loader / writer 查找
- 需要 braille 的 export policy

## 方案比較

### A. 只拆更多 `gui.py` helper methods

優點：

- 改動小

缺點：

- 狀態同步問題仍存在
- OCP 缺口仍存在
- 只是把大型方法拆成較小方法，沒有改善邊界

不採用。

### B. 收斂現有 controller / job runner / registry 邊界

優點：

- 直接解決狀態單一來源問題
- 可保留既有 wx UI 與 public behavior
- 每一步都能用 focused unit test 驗證

缺點：

- 需要小心處理現有測試與 compatibility layer

採用。

### C. 一次把整個 client 改成完整 MVC / MVVM

優點：

- 理論上架構更一致

缺點：

- 變更面過大
- 無法維持低風險漸進式重構
- 與目前專案規模不成比例

不採用。

## 目標結構

```text
client/
├── conversion/
│   ├── jobs.py
│   └── ...
├── documents/
│   ├── controller.py
│   ├── formats.py
│   ├── session.py
│   └── workspace.py
└── gui.py
```

## 模組責任

### `client/documents/controller.py`

職責：

- 保存 documents、selected/open name 與 dual-view cache
- 提供 document read-only snapshot / accessor
- 執行 rename / replace / delete / open 等 state transition

不應負責：

- wx controls
- message box
- filesystem dialog

### `client/conversion/jobs.py`

職責：

- job id 指派
- worker thread 執行
- stale-job protection
- 回傳與 request 關聯的 workflow result

不應負責：

- wx dialog
- `TextCtrl` 更新
- 成功或錯誤訊息顯示

### `client/documents/formats.py`

職責：

- 集中定義 document format descriptor
- 提供 import/export format registry
- 提供 loader / writer / wildcard / extension 查找

不應負責：

- 實際顯示 file dialog
- 額外修改 user-visible labels

## 遷移策略

### 步驟 1：先補 focused characterization tests

先鎖住：

- document rename/delete/open 的 state transition
- conversion stale job 與 completion policy
- import/export format lookup 與 wildcard 組裝

### 步驟 2：讓 GUI 讀 controller，而不是維護鏡像 state

優先把讀路徑改成 controller accessor，再逐步刪掉 frame mutable document 欄位。

### 步驟 3：把 conversion policy 綁到 request/result

先新增資料型別與 adapter glue，再移除 frame 上對應欄位。

### 步驟 4：把 format branch 收斂到 registry

先處理 `dep` 與 `brl` export，再把 import loaders 與 wildcard 接到同一來源。

## 驗收條件

### 文件狀態

- open / select / rename / delete / delete-all 行為不變
- dual-view cache rename/delete 後仍正確追蹤
- `BrailleFrame` 不再保存需要和 controller 雙向同步的 document state 副本

### conversion workflow

- manual convert 行為不變
- single export 與 batch export 不會錯用 manual success policy
- stale job result 不會套用到錯誤 workflow policy

### format registry

- `dep` / `brl` export 行為不變
- import wildcard/filter 與 loader mapping 來自同一來源
- 新增格式所需修改點少於現況

## 測試策略

核心回歸組：

- `python3 -m unittest tests.test_document_controller -v`
- `python3 -m unittest tests.test_document_session tests.test_document_workspace tests.test_gui_document_flows -v`
- `python3 -m unittest tests.test_conversion_jobs tests.test_conversion_service -v`
- `python3 -m unittest tests.test_import_dialog tests.test_gui_document_flows -v`

若 importer optional dependency 不齊，需在實作紀錄中註明未執行項目。

## 實作決策

實作時應採用以下決策，避免把邊界選擇留給後續 worker 自行判斷：

1. dual-view cache 應放在 `DocumentController`。`BrailleFrame` 可短期保留委派 property 作為相容層，但不應擁有獨立 cache。
2. conversion policy 型別本階段應放在 `client/conversion/jobs.py`。只有當 job orchestration 後續超出本次需求時，才再評估獨立 `workflow.py`。
3. format registry 應提供 file-dialog wildcard helper，也提供 descriptor list，因為 GUI import/export flow 已經需要穩定的 wildcard 組裝邊界。
