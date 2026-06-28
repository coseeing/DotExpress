# Task 2 完成說明

## 修正內容

- 已確認 `review_task1.md` 指出的問題成立：先前 `test_translation_dictionary_state.py` 的 Add 測試只覆蓋未被 production code 使用的 helper，無法保護實際字典管理流程。
- 已將字典管理的 Add / Rename / Delete decision path 收斂為 production 會實際呼叫的 orchestration helper：
  - `plan_dictionary_state_after_add()`
  - `plan_dictionary_state_after_rename()`
  - `plan_dictionary_state_after_delete()`
- `client/gui.py` 現在直接使用上述 helper，測試會真正保護 active dictionary 與 management selection 的更新規則。
- 已移除只為測試存在、但未被 production path 使用的 Add helper 介面。

## 驗證

- `cd client && python3 -m unittest tests.test_translation_dictionary_state tests.test_translation_settings tests.test_translation_menu tests.test_section_navigation tests.test_config tests.test_dictionary_actions tests.test_dictionary_manager tests.test_input_shortcuts -v`
- `python3 -m py_compile client/gui.py client/translation/dictionary_state.py client/tests/test_translation_dictionary_state.py`
- `cd client && python3 -m unittest discover -s tests -v`

`unittest discover` 仍有既有環境限制，沒有新增新的失敗：

- `test_language_detection_translation`：缺少 `liblouis.dll`
- `test_translation_language_result`：module-level `pytest.skip` 被 `unittest` 視為 import error
- `test_translation_result`：module-level `pytest.skip` 被 `unittest` 視為 import error

## Commit List

- `8f12bb2` `test: cover dictionary state orchestration`
