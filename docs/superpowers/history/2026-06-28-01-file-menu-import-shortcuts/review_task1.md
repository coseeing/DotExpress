# Task 1 Code Review

## Review Scope

- 修正資訊：`docs/superpowers/finish_task1.md`
- 原始 review：`docs/superpowers/review_task0.md`
- 設計規格：`docs/superpowers/specs/2026-06-28-file-menu-import-shortcuts-design.md`
- 實作計畫：`docs/superpowers/plans/2026-06-28-file-menu-import-shortcuts-implementation-plan.md`
- 審閱 commit（依提交時間由舊到新）：
  1. `0a6736d` `fix: align file menu and name validation with review`

## Findings

未發現需要修正的 blocking、important 或 minor findings。

## Previous Findings Verification

### P1：dictionary name boundary test

狀態：已修正。

- 舊的無效案例已改為明確的 33 字元輸入。
- 已新增 dictionary name 接受 32 字元的測試。
- document 與 dictionary 現在都覆蓋 32 字元成功、33 字元失敗的邊界。
- 完整 client test suite 已恢復通過。

### P2：File menu 與 context menu 重複建構及綁定

狀態：已修正。

- `DocumentMenuItem` descriptor 現在集中定義 kind、label、action 與 formats。
- top-level File menu 與 document context menu 都使用 `_append_document_menu_items()` 建構項目。
- 兩個入口都使用 `_bind_document_menu_handlers()` 綁定 command 及 submenu handlers。
- Import、Export、Export All 的格式與 action dispatch 由同一份 descriptor 驅動。
- enabled-state 仍共用 `get_document_menu_enabled_state()`，未因 refactor 改變。

### P2：gettext template 過期

狀態：已修正。

- `dotexpress.pot` 已將 dictionary/document 驗證訊息更新為 32 字元。
- `dotexpress.pot` 已加入 `File`。
- template 已無 `1 to 16 characters` 舊字串。
- zh_TW `.mo` 可正常載入，且 `File` 與兩個 32 字元訊息均存在。

## Commit-by-Commit Review

### `0a6736d`

- dictionary 測試修改與共用 32 字元規則一致，沒有放寬其他保留字或非法字元檢查。
- menu refactor 移除 top-level 與 context menu 的重複 submenu 建構程式。
- lambda 以 default argument 固定各自的 format key，未產生 late-binding 問題。
- command ordering、submenu formats 與 enabled-state API 保持不變。
- `Alt+O`、SimBraille fallback、既有 import/export handlers 與 zh_TW PO/MO 未被此 commit 改壞。
- POT 修改只補齊本次 user-facing strings，未見額外 catalog 變動。

## Verification

執行：

```bash
cd client
python3 -m unittest discover -s tests -v
```

結果：`114` tests passed，`3` tests skipped。skips 為既有非 Windows/liblouis 平台限制。

執行：

```bash
python3 -m py_compile \
  client/gui.py \
  client/config.py \
  client/name_validation.py \
  client/ui/action_menu.py \
  client/ui/shortcuts.py \
  client/dialog.py \
  client/tests/test_config.py \
  client/tests/test_document_workspace.py \
  client/tests/test_dictionary_manager.py \
  client/tests/test_action_menu.py \
  client/tests/test_input_shortcuts.py \
  client/tests/test_dialog_validation.py
```

結果：通過。

另外以 Python `gettext.GNUTranslations` 載入 zh_TW `.mo`，並檢查 POT/MO 的 `File`、dictionary 32 字元與 document 32 字元項目，結果通過。

## Residual Risk

- 現有自動測試主要驗證 descriptor、enabled-state 與 shortcut predicate，未在實際 wx frame 中觸發 menu events。
- 目前環境無法執行 Windows wxPython UI smoke test；合併前仍建議在 Windows 手動確認 File/context submenu dispatch 與 child control focus 下的 `Alt+O`。

## Assessment

本次修正已關閉 `review_task0.md` 的三項 findings，未發現由 `0a6736d` 引入的新問題。依現有自動化與靜態驗證結果，可進入合併流程。
