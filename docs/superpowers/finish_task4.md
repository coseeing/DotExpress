# Task 4 完成說明

本次延續 liblouis build / runtime debug，處理了兩個已確認的問題：

1. `client/braille/liblouis.dll` 少了 `lou_freeTableInfo` export
2. `client/braille/louis_helper.py` 把 NVDA 專用的 `log.DEBUG` 寫法搬進來，但本專案使用的是標準 `logging.Logger`

## 已確認的發現

- `include/liblouis/liblouis/metadata.c` 內確實有 `lou_freeTableInfo(char *info)` 定義。
- `metadata.c.obj` 裡也能看到 `lou_freeTableInfo` symbol。
- 但 `client/braille/liblouis.dll` / `.lib` / `.exp` 起初缺少 `lou_freeTableInfo` export。
- `lou_freeTableFile` 與 `lou_freeTableFiles` 已存在，只有 `lou_freeTableInfo` 缺失。
- 這表示問題在 link/export 階段，而不是 header 宣告或 source 實作本身。

## 已完成的修正

### 1) 匯出層修正

在 `sconstruct` 補上顯式 export：

```text
/EXPORT:lou_freeTableInfo
```

這是為了強制 linker 把 `lou_freeTableInfo` 放進 DLL export table，讓產物與 NVDA reference 對齊。

### 2) sync 層修正

`scripts/sync_nvda_liblouis.py` 生成的 `louis_helper.py` 原本沿用 NVDA 的 logging level mapping 寫法：

- `louis.LOG_ALL: log.DEBUG`
- `louis.LOG_DEBUG: log.DEBUG`
- ...

但 DotExpress 的 helper 使用的是標準 `logging.getLogger(__name__)`，所以 `log` 沒有 `.DEBUG` 這些屬性。

已改為：

- `louis.LOG_ALL: logging.DEBUG`
- `louis.LOG_DEBUG: logging.DEBUG`
- ...

同時也把 fallback level 改成 `logging.DEBUG`。

### 3) 已生成檔同步更新

同步更新了：

- `client/braille/louis_helper.py`
- `vendor/nvda/liblouis/runtime/louis_helper.py`

避免下次重新 sync 時把修正覆蓋回去。

### 4) memo 補充

已將這次確認的兩層差異補進 `docs/liblouis-build-memo.md`：

- compile-time declaration layer
- link/export layer

## 驗證

已驗證：

- `scripts\verify-liblouis-export-state.bat`
  - `lou_freeTableInfo` 現在已在 current DLL 與 NVDA reference DLL 兩邊都存在
- `python3 -m py_compile client/braille/louis_helper.py vendor/nvda/liblouis/runtime/louis_helper.py scripts/sync_nvda_liblouis.py`

## 新增 commit list

- `fix: sync NVDA-style logging level mappings for liblouis helper`

