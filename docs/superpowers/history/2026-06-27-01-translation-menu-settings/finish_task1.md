# Task 1 完成說明

## 修正內容

- 已將字典管理流程與 active translation dictionary 狀態拆開。
- `Dictionary Management...` 的 Add / Delete / Rename / Import 只會更新管理清單，不會直接改寫目前轉譯設定。
- 只有在刪除或重新命名的字典原本就是 active dictionary 時，才會同步更新 `Translation Settings` 的字典選擇。
- 已移除 `gui.py` 內部獨立的 section order，改為直接使用共用的 `ui.section_navigation.get_adjacent_section()`。
- 已新增純函式回歸測試，覆蓋字典管理對 active dictionary 的影響規則。

## 驗證

- `python3 -m py_compile client/gui.py client/dialog.py client/translation/settings.py client/translation/dictionary_state.py client/ui/translation_menu.py client/ui/section_navigation.py client/tests/test_translation_dictionary_state.py client/tests/test_section_navigation.py`
- `cd client && python3 -m unittest tests.test_translation_dictionary_state tests.test_translation_settings tests.test_translation_menu tests.test_section_navigation tests.test_config tests.test_dictionary_actions tests.test_dictionary_manager tests.test_input_shortcuts -v`

## Commit List

- `f040b7f` `fix: separate dictionary state updates`
