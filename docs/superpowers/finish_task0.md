# Task 0 完成說明

## 變更摘要

- 已將主視窗的可見 `Conversion` 控制列移除，改成頂層 `Translation` 選單。
- 已新增 `Translation Settings...` 與 `Dictionary Management...` 對話框流程。
- 已把轉譯設定抽成 `client/translation/settings.py`，並用 `TranslationSettings` 來管理 staged state。
- 已更新 `F6` / `Shift+F6` 區塊循環，只保留可見區塊。
- 已更新 `zh_TW` 翻譯與 `.mo` catalog。

## 驗證

- `python3 -m py_compile client/gui.py client/dialog.py client/translation/settings.py client/ui/translation_menu.py client/ui/section_navigation.py client/tests/test_section_navigation.py`
- `cd client && python3 -m unittest tests.test_translation_settings tests.test_translation_menu tests.test_section_navigation tests.test_config tests.test_dictionary_actions tests.test_dictionary_manager tests.test_input_shortcuts -v`
- `cd client && python3 -m unittest discover -s tests -v`

`unittest discover` 目前仍有 3 個與既有環境限制相關的 import error：

- `tests.test_language_detection_translation` 需要 `liblouis.dll`
- `tests.test_translation_language_result` 在此平台被 skip
- `tests.test_translation_result` 在此平台被 skip

## Commit List

- `078f2b2` `feat: move translation controls to menu`
