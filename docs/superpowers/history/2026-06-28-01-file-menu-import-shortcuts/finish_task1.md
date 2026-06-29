# Task 1 完成說明

## 修正內容

- 已將文件匯入快捷鍵從 `Alt+O` 改成 `Ctrl+O`。
- `client/ui/shortcuts.py` 的 TXT import 判斷現在改用 `control_down`。
- `client/gui.py` 的 frame-level `on_char_hook()` 也同步改成以 `Ctrl+O` 直接觸發 `on_import_document("txt")`。
- 已更新對應測試，確認 `Ctrl+O` 為正確觸發條件。

## 驗證

- `python3 -m py_compile client/gui.py client/ui/shortcuts.py client/tests/test_input_shortcuts.py`
- `cd client && python3 -m unittest tests.test_input_shortcuts -v`

## Commit List

- `7bb19b1` `feat: switch txt import shortcut to ctrl+o`
