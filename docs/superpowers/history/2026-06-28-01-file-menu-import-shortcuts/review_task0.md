# Task 0 Code Review

## Review Scope

- 完成資訊：`docs/superpowers/finish_task0.md`
- 設計規格：`docs/superpowers/specs/2026-06-28-file-menu-import-shortcuts-design.md`
- 實作計畫：`docs/superpowers/plans/2026-06-28-file-menu-import-shortcuts-implementation-plan.md`
- 審閱 commits（依提交時間由舊到新）：
  1. `ab63aee` `feat: widen shared name limits and default braille font`
  2. `e534a52` `refactor: share document menu definitions`
  3. `9d44429` `feat: add file menu and txt import shortcut`
  4. `e1ee8aa` `fix: update validation text for 32 character names`

## Findings

### [P1] 共用名稱上限變更造成完整 client test suite 失敗

位置：`client/tests/test_dictionary_manager.py:48`

`ab63aee` 將共用 `MAX_NAME_LENGTH` 從 16 改為 32，但只更新 document workspace 測試，沒有同步更新使用同一規則的 dictionary manager 測試。既有無效值 `"this-name-is-way-too-long"` 長度未超過 32，現在是合法名稱，因此：

```text
FAIL: test_normalize_dictionary_name_rejects_reserved_or_invalid_names
AssertionError: ValueError not raised
```

這與 spec 明確要求 document 與 dictionary 共用 32 字元規則不一致，也表示完成紀錄中的聚焦驗證未涵蓋此次共用常數影響的所有呼叫端。應把無效邊界改為 33 字元，並新增 dictionary 32 字元成功案例，避免只修正失敗資料卻未鎖定新邊界。

### [P2] File menu 與 context menu 並未共用同一套建構及事件綁定

位置：`client/gui.py:377`、`client/gui.py:903`

`e534a52` 建立了選單 descriptor，但 `9d44429` 在 `_create_document_menu()` 與 `on_document_context_menu()` 仍各自重複：

- 建立 Import、Export、Export All submenu
- 逐一建立格式項目
- 綁定 import/export handler
- 依 label 使用硬編碼分支

兩處甚至忽略 `get_document_menu_items()` 回傳 tuple 中的 formats，改為另外呼叫 format label helpers。這不符合 spec「item order、submenu structure、handler binding、enable/disable state 由一份共用定義驅動」的設計要求，未來新增格式或調整 handler 時仍可能產生兩個入口不一致。

應抽出單一 `_append_document_menu_items()` 與 `_bind_document_menu_handlers()`，讓頂層 File menu 和 context menu 使用相同的 item/format maps。現有 `test_action_menu.py` 只測純 helper，未測 `gui.py` 是否確實依 descriptor 建構及綁定，因此沒有攔截這項偏差。

### [P2] gettext template 未隨 user-facing strings 更新

位置：`client/locales/dotexpress.pot:924`、`client/locales/dotexpress.pot:945`

`e1ee8aa` 更新了 `dotexpress.po` 與編譯後的 `.mo`，但 `dotexpress.pot` 仍包含：

```text
Dictionary name must be 1 to 16 characters.
Document name must be 1 to 16 characters.
```

template 也沒有新增 `File`。下次依 repository 的 translation template 流程更新 catalog 時，會重新帶回過期 msgid 或漏掉新增字串。應執行 `scripts\generate_pot.bat` 對應的 extraction 流程並提交更新後的 POT，再確認 PO/MO 一致。

## Commit-by-Commit Review

### `ab63aee`

- `DEFAULT_BRAILLE_FONT = "simbraille"` 放在 config source of truth，符合 spec。
- document name 與 TXT stem 已覆蓋 32/33 邊界。
- 遺漏 dictionary manager 測試更新，導致完整 suite 失敗，詳見 P1。

### `e534a52`

- 選單順序、格式與 enabled-state helper 的純函式測試完整涵蓋四種 selection/document 組合。
- `Alt+O` helper 正確限制為 Alt + key code 79。
- descriptor 未包含 handler/action key，後續 GUI 串接因此仍以 label 分支處理，形成 P2 的設計落差。

### `9d44429`

- File menu 加入既有 menu bar，且 `Alt+O` 直接呼叫 `on_import_document("txt")`。
- top-level menu state 會在文件清單與 selection 變更時同步。
- File/Translation 在 conversion busy state 下會一起停用。
- menu construction 與 submenu handler binding 仍在兩個入口重複，詳見 P2。
- 缺少 wx GUI integration test；目前測試只能證明 helper 結構與 shortcut predicate，不能證明 menu item 實際 dispatch 到正確 handler。

### `e1ee8aa`

- document/dictionary 驗證訊息與 zh_TW PO/MO 已改為 32 字元。
- 新增的 dialog validation test 可鎖定翻譯後訊息。
- POT 未同步更新，詳見 P2。

## Verification

執行：

```bash
cd client
python3 -m unittest discover -s tests -v
```

結果：`112` tests，`1` failure，`3` skips。

- Failure：`test_normalize_dictionary_name_rejects_reserved_or_invalid_names`
- Skips：既有非 Windows/liblouis 平台限制項目

## Assessment

目前不建議合併。至少需先修正 P1 並讓完整 client suite 通過；兩項 P2 應在本次功能內完成，因為它們分別違反已確認的共用選單架構與 repository localization 維護流程。
