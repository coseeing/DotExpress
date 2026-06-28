# Task 1 完成說明

## 修正內容

- 已把共用名稱上限從 `16` 修正為 `32`，並補上 dictionary 的 32/33 邊界測試。
- 已將 braille font 的 no-config fallback 維持為 `SimBraille`。
- 已把 `File` / document menu 的建構與事件綁定集中到單一 helper，讓 top-level `File` 與 context menu 共用同一份 descriptor。
- 已把 `gui.py` 的 `Alt+O` shortcut 保持為直接導向 `on_import_document("txt")`。
- 已更新 `dotexpress.pot`，補上 `File` 與 32 字元驗證文案。

## 驗證

- `python3 -m py_compile client/gui.py client/config.py client/name_validation.py client/ui/action_menu.py client/ui/shortcuts.py client/dialog.py client/tests/test_config.py client/tests/test_document_workspace.py client/tests/test_dictionary_manager.py client/tests/test_action_menu.py client/tests/test_input_shortcuts.py client/tests/test_dialog_validation.py`
- `cd client && python3 -m unittest tests.test_config tests.test_document_workspace tests.test_dictionary_manager tests.test_action_menu tests.test_input_shortcuts tests.test_dialog_validation -v`
- `cd client && python3 -m unittest discover -s tests -v`

## Commit List

- `0a6736d` `fix: align file menu and name validation with review`
