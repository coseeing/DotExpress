# Client Init Version Check Design

## Goal

新增啟動行為，讓 DotExpress 將匿名使用版本 metadata 送到專案伺服器，並先確認 payload、request 與 response parsing 機制正常。本輪不顯示使用者可見的更新提示。

## Scope

此設計涵蓋：

- 匿名啟動統計
- 版本檢查 response 機制驗證
- `server/` 內的 FastAPI + SQLAlchemy + SQLite 暫時 server implementation

此設計不涵蓋自動下載或安裝更新、不涵蓋強制更新阻擋、不顯示 GUI 更新提示、不新增 telemetry controls 的 preferences UI，也不新增統計查詢或 admin endpoint。

## Request Contract

client 送出 POST request 到：

```text
https://dotexpress.coseeing.org/client/init
```

Payload：

```json
{
  "app": "DotExpress",
  "version": "1.2",
  "client_id": "generated-uuid",
  "os": "Windows",
  "os_version": "10.0.22631",
  "arch": "AMD64",
  "locale": "zh_TW",
  "event": "startup"
}
```

`client_id` 是由 DotExpress 產生並持久化保存在 local config 的穩定隨機 identifier。應用程式不得送出原始 MAC address。

## Response Contract

server 回傳：

```json
{
  "version": "1.3",
  "minimum_supported_version": "1.0",
  "download_url": "https://dotexpress.coseeing.org/download",
  "release_notes_url": "https://dotexpress.coseeing.org/releases/1.3",
  "message": "DotExpress 1.3 is available.",
  "severity": "optional"
}
```

client 會解析並保留這些 response 欄位，讓測試與後續整合能確認伺服器回傳機制正常。本輪即使回傳的 `version` 較新，或 `severity` 為 `required`，也不顯示 update notice、不關閉 DotExpress、不阻擋使用。

## Architecture

新增聚焦的 helper module，暫定為 `client_init.py`，負責：

- payload construction
- `client_id` lookup/generation
- HTTP POST behavior
- server response parsing
- no-update/failure result modeling

`gui.py` 只負責 startup orchestration；本輪不負責 user notification：

```text
BrailleApp.OnInit()
  ├─ louisHelper.initialize()
  ├─ create BrailleFrame
  ├─ show main frame
  └─ start background client init check
       ├─ build payload
       ├─ POST /client/init
       ├─ parse response
       └─ store/return parsed result without showing UI
```

## Server Architecture

Server 原始碼放在 `server/`：

```text
server/
  requirements.txt
  README.md
  app/
    __init__.py
    main.py
    config.py
    database.py
    models.py
    schemas.py
    crud.py
  tests/
    test_client_init.py
```

`main.py` 負責 FastAPI app 與 `/client/init` route；`schemas.py` 定義 Pydantic request/response；`models.py` 定義 SQLAlchemy models；`database.py` 負責 engine、session 與 table initialization；`crud.py` 負責寫入資料。

SQLite database 預設放在：

```text
server/data/dotexpress.sqlite3
```

初版不使用 Alembic，啟動時建立 table。後續若正式部署再評估 PostgreSQL 與 migration tool。

## Server Persistence

Server 使用兩張表：

```text
clients
  id
  client_id
  first_seen_at
  last_seen_at
  last_app_version
  last_os
  last_os_version
  last_arch
  last_locale

client_startup_events
  id
  client_id
  app
  version
  os
  os_version
  arch
  locale
  event
  received_at
```

`clients` 保存匿名 client 的最新狀態，`client_startup_events` 保存每次 startup request。本輪不提供 `GET /admin/stats` 或類似 statistics/admin query endpoint。

## Privacy Rules

request 不得包含：

- 原始 MAC address
- 使用者名稱
- 電腦名稱
- 文件內容
- 檔名
- 字典內容
- 檔案系統路徑
- 已安裝軟體清單

核准的 payload 範圍刻意保持狹窄，讓維護者能了解版本採用與作業環境分布，但不收集使用者工作資料。

## Failure Behavior

network errors、timeouts、server errors、invalid JSON 或缺少 response fields 都屬於 non-fatal。DotExpress 會繼續執行，且不顯示 startup error dialog。

## Testing

tests 應涵蓋：

- 產生並持久化 `client_id`
- 重複使用既有 `client_id`
- payload field contents
- sensitive-field exclusion
- response parsing
- malformed response handling
- network failure returning no-update behavior
- 在可行範圍內驗證 startup integration 會在 frame 顯示後開始
- 即使 response 表示有新版本，也不顯示 GUI update notice
- server valid request 與 invalid request
- server response contract
- SQLite 中 new client、existing client update 與 startup event recording
- 確認沒有 statistics/admin query endpoint

## OpenSpec Change

對應的 OpenSpec change 是：

```text
openspec/changes/add-client-init-version-check
```
