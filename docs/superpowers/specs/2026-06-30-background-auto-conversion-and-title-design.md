# Background Auto-Conversion and Window Title Design

## Summary

DotExpress 目前在多個文件操作前，會同步自動轉換目前開啟且 `braille is None` 的文件。當文件很大時，這會把整個 UI 卡住，尤其是在匯入、切換文件或關閉視窗等本來不應等待 braille 結果的流程上。

這份設計將自動轉換縮減到真正必要的匯出情境，並把其餘情境改成「先保存 `text + pending`，再由單一背景 worker 默默轉換」。同時，主視窗標題改為固定顯示目前開啟文件名稱，格式為 `文件名 - DotExpress`。

## Background

- 目前同步自動轉換的核心入口是 `prepare_document_for_save()` in [client/documents/workspace.py](/workspace/DotExpress/client/documents/workspace.py:141)。
- 多個 UI 流程會先呼叫 `_save_open_document_with_feedback()` in [client/gui.py](/workspace/DotExpress/client/gui.py:794)，間接觸發同步自動轉換。
- 手動按「轉譯」已經有背景 thread 與 converting dialog，入口是 `on_convert()` in [client/gui.py](/workspace/DotExpress/client/gui.py:1410)。
- 目前視窗標題固定為 `DotExpress`，設定於 `_initialize_frame()` in [client/gui.py](/workspace/DotExpress/client/gui.py:245)。
- 啟動後目前幾乎一定會有一份開啟中的文件，因為 `_ensure_open_document_exists()` 會打開第一份文件，若沒有文件則建立預設文件 `new` in [client/gui.py](/workspace/DotExpress/client/gui.py:876)。

## Goals

- 讓非匯出類操作不再因自動轉換而阻塞 UI。
- 只在匯出確實需要 braille 輸出時才等待轉換完成。
- 用背景 queue 處理非匯出類操作留下的 pending 文件。
- 防止舊的背景結果覆蓋較新的文字版本。
- 讓手動按「轉譯」永遠優先於背景自動轉換。
- 視窗標題固定顯示目前開啟文件名稱。

## Non-Goals

- 不改變 `.dep` 格式。
- 不在標題中顯示 `[pending]` 或 `[converting]` 狀態。
- 不嘗試同時平行跑多份背景轉換。
- 不把所有保存行為都改成非同步 I/O；這次重點是 braille 轉換的阻塞問題。

## Confirmed Decisions

- 只有匯出類操作保留「必要時自動轉換」。
- 刪除單一文件與刪除全部文件都不應再觸發自動轉換。
- 關閉視窗時不等待背景轉換完成，只保存 `text + pending` 後直接關閉。
- 若同一份文件正在背景轉換或待轉換，而使用者手動按「轉譯」，必須取消原背景 job，改用最新文字啟動前景轉譯。
- 視窗標題固定為 `文件名 - DotExpress`。

## Operation Matrix

### 1. 非匯出類操作

以下操作不再等待 braille 自動轉換完成：

- 切換文件
- 新增文件
- 重新命名文件
- 匯入文件
- 刪除單一文件
- 刪除全部文件
- 關閉視窗

這些操作的共通原則是：

1. 先保存最新 `text`。
2. 若文件尚未有 braille 結果，保存為 pending 狀態。
3. 不阻塞目前操作。
4. 視需要將該文件排進背景轉換 queue。

### 2. 匯出類操作

以下操作保留「必要時自動轉換」：

- 匯出單一文件
- 匯出全部文件
- 匯出快捷鍵

這些操作的共通原則是：

1. 若目標文件已有可用 braille，直接匯出。
2. 若目標文件仍是 pending，必須等待轉換完成。
3. 等待期間顯示和手動按「轉譯」一致或等價的提示。
4. 匯出流程不得默默輸出空白 braille 來繞過等待。

## Detailed Behavior by Operation

### Switch / Add / Import

- 只保存 `text + pending`。
- 不等待轉換結果。
- 保存後可把該文件排進背景 queue。

### Rename

- 不重新轉換內容。
- 只改變文件名稱。
- 若該文件有 pending 狀態，pending 狀態跟著新名稱走。
- 若該文件已有 queued 或 running 背景 job，job 的歸屬也必須搬到新名稱。
- 背景轉換之後若完成，結果必須回寫到新名稱對應的 `.dep`。

### Delete Single / Delete All

- 不做自動轉換。
- 直接刪除文件。
- 若有對應 queued 或 running 背景 job，立即取消。

### Close Window

- 不等待背景轉換完成。
- 只保存 `text + pending`。
- 直接關閉視窗。
- 尚未完成的背景 job 可直接取消，不要求在結束前把所有文件都轉完。

### Export One / Export All / Export Shortcut

- 這三類都屬於需要 braille 結果的輸出操作。
- 若文件尚未有 braille 結果：
  - 若已有對應背景 job，匯出流程應接管它並等待完成。
  - 若沒有對應背景 job，匯出流程應啟動轉換並等待完成。
- 等待期間顯示 converting 提示。
- 匯出完成後，結果應回寫文件與 `.dep`，避免同一份文件下次又重新做相同轉換。

## Background Conversion Queue

### Single Worker

背景自動轉換採用單一 worker。

理由：

- 可避免多份大文件同時轉換造成資源競爭。
- 較容易管理 job 狀態、取消邏輯與結果回寫。
- 較符合目前已有的單次轉換 UI 結構。

### Queue Rules

- 同時間只允許一份背景轉換 running。
- 可以有多份 queued job。
- 同一份文件若產生新版本，只保留最新版本的 queued job。
- 舊版本 queued job 必須被取代，不可繼續執行。

## Versioning and Result Acceptance

背景轉換不能只用文件名稱判斷結果是否可回寫，必須帶有版本或 job id。

每個背景或前景轉換工作都應綁定：

- 文件識別
- 文字版本識別
- job id

結果回寫規則：

- 只有當完成結果仍對應到該文件的最新文字版本時，才允許回寫。
- 若文件在轉換期間已被再次編輯，舊 job 完成後必須丟棄結果。
- 不允許舊背景結果覆蓋新的文字狀態或新的手動轉譯結果。

## Manual Convert Priority

手動按「轉譯」的優先權高於背景自動轉換。

規則：

1. 若同一份文件已有 queued 或 running 背景 job，先取消它。
2. 以使用者按下當下的最新文字啟動前景轉譯。
3. 顯示現有的 converting dialog。
4. 最後只接受這個前景手動 job 的結果。

這可確保：

- 使用者的明確操作不會被背景工作拖慢或覆蓋。
- 手動轉譯永遠反映按下當下的最新內容。

## Window Title

### Title Format

主視窗標題固定為：

- `文件名 - DotExpress`

不顯示：

- `[pending]`
- `[converting]`

### Update Triggers

只要目前開啟文件改變，就必須立即更新標題，包括：

- 啟動時自動打開第一份文件
- 啟動時自動建立預設文件
- 切換開啟文件
- 重新命名目前開啟文件
- 刪除目前開啟文件後自動切到下一份文件

標題應綁定 `open document`，不是左側清單的暫時選取狀態。

## Error Handling

- 背景自動轉換失敗時，不應打斷非匯出類操作。
- 失敗後文件保留 pending 狀態，等待下次手動轉譯或匯出時重試。
- 匯出類操作若轉換失敗，匯出必須失敗並顯示錯誤，不能默默產生空白 braille 輸出。
- 被取消的背景 job 不視為錯誤，不應跳出錯誤對話框。

## Testing Strategy

### Unit / State Tests

驗證：

- 非匯出類操作不再同步呼叫自動轉換。
- 匯出類操作在 pending 文件上會等待轉換。
- 同文件新版本會取代舊 queued job。
- 舊 job 完成後不會覆蓋新版本。
- 手動轉譯會取消同文件的背景 job。

### UI Behavior Tests

驗證：

- 切換、匯入、重新命名、刪除、關閉不再因 pending 文件而卡在同步轉換。
- 匯出類操作仍有 converting 提示。
- 視窗標題隨目前開啟文件名稱更新。
- 左側只選取但尚未開啟的文件不應影響標題。

## Risks and Trade-offs

- 引入背景 queue 會增加狀態管理複雜度，尤其是取消與版本比對。
- 若關閉視窗時直接取消背景 job，下次開啟可能仍看到 pending 文件；這是刻意接受的 trade-off，因為它避免了退出時被大文件阻塞。
- 匯出全部文件在多份 pending 文件上仍可能等待很久；這是合理成本，因為匯出本身就需要最終 braille 結果。

## Implementation Outline

1. 抽離「保存文字但不強制同步自動轉換」的文件保存路徑。
2. 新增背景轉換 queue、job model、取消與版本比對機制。
3. 把非匯出類操作改接新保存路徑。
4. 把匯出類操作改成必要時等待背景或前景轉換完成。
5. 調整手動轉譯，讓它能取消同文件的背景 job。
6. 新增視窗標題更新 helper，綁定 open document 變動。
7. 補齊 queue、匯出等待、標題更新與競態保護測試。
