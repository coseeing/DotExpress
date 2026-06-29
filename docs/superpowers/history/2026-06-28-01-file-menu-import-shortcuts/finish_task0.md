# Task 0 完成說明

## 變更摘要

- 已將無設定時的 braille font 預設改為 `SimBraille`。
- 已將共用名稱長度上限從 `16` 提升到 `32`，並同步更新文件 / 字典名稱驗證文案。
- 已建立共用 document menu descriptor 與 `Alt+O` TXT import shortcut helper。
- 已在主視窗加入 top-level `File` 選單，並讓它與 document context menu 共用同一組動作與啟用狀態。
- 已將 frame-level `Alt+O` 直接導向既有 `on_import_document("txt")` 流程。
- 已更新 zh_TW 翻譯 catalog 與編譯後的 `.mo`。

## 驗證

- `cd client && python3 -m unittest tests.test_config tests.test_document_workspace tests.test_action_menu tests.test_input_shortcuts tests.test_dialog_validation -v`
- `python3 -m py_compile client/gui.py client/config.py client/name_validation.py client/ui/action_menu.py client/ui/shortcuts.py client/dialog.py client/tests/test_config.py client/tests/test_document_workspace.py client/tests/test_action_menu.py client/tests/test_input_shortcuts.py client/tests/test_dialog_validation.py`
- `python3 - <<'PY' ...` 驗證 `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` 可讀，且 `File` / 32 字元驗證字串都存在

## Commit List

- `ab63aee` `feat: widen shared name limits and default braille font`
- `e534a52` `refactor: share document menu definitions`
- `9d44429` `feat: add file menu and txt import shortcut`
- `e1ee8aa` `fix: update validation text for 32 character names`
