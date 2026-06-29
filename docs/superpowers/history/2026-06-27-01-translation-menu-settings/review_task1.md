# Task 1 修正程式碼審閱報告

## 審閱範圍

- 修正完成資訊：`docs/superpowers/finish_task1.md`
- 前次審閱：`docs/superpowers/review_task0.md`
- 設計規格：`docs/superpowers/specs/2026-06-27-translation-menu-settings-design.md`
- 實作計畫：`docs/superpowers/plans/2026-06-27-translation-menu-settings-implementation-plan.md`
- 文件列出的 commit：
  1. `f040b7f57bf60cc3e29f68cefa20836882ef049f` — `fix: separate dictionary state updates`
- 比較基準：`0bdcfce48d66c0aa47b69d69f92db6a443b0a54e`

`finish_task1.md` 只列出 `f040b7f`，因此本次依 commit 時間由舊到新的審閱順序只有該 commit。雖然 ancestry 中另有 `078f2b2` 與 `0bdcfce`，但依使用者要求，不把未列於 `finish_task1.md` 的 commit 納入本次 commit-by-commit 審閱。

## Findings

### [P2] 新增測試仍未驗證實際字典管理 handler，Add 測試只覆蓋未使用函式

**位置：**

- `client/translation/dictionary_state.py:10-11`
- `client/tests/test_translation_dictionary_state.py:24-28`
- `client/gui.py:1170-1191`
- `client/gui.py:1193-1230`
- `client/gui.py:1232-1271`
- `client/gui.py:1273-1312`

`test_add_keeps_active_dictionary_unchanged()` 測試的是 `resolve_active_dictionary_after_add()`，但 production code 沒有匯入或呼叫這個函式。實際 `add_dictionary()` 是直接執行 `_refresh_dictionary_names(path.stem)`。

因此此測試即使通過，也不能證明 Add 流程沒有改動：

- `self.translation_settings.selected_dictionary`
- `set_selected_dictionary()`
- Dictionary Management list view

Delete 與 Rename 測試也只驗證純函式輸出，沒有驗證 `BrailleFrame` handler 確實在正確條件下呼叫 `_set_active_dictionary()`。本次人工 diff 檢查確認目前 wiring 符合預期，但測試無法防止後續 wiring 回歸。

這也是 Task 0 第三項 P2 finding 的延續：核心 UI orchestration 仍未被自動化測試覆蓋。Task 1 新增純函式測試降低了規則本身的風險，但尚未完整關閉該 finding。

**建議修正：**

- 移除未使用的 `resolve_active_dictionary_after_add()`，或讓 production Add 流程實際使用它；不要保留只為測試存在的 production helper。
- 將「dictionary operation 後如何更新 active setting」抽成不依賴 wx 的 orchestration 函式，並由實際 handler 呼叫。
- 或以 mock 建立 `BrailleFrame` handler 測試，至少驗證：
  - Add / Import 不呼叫 `_set_active_dictionary()`
  - Delete 非 active dictionary 不呼叫 `_set_active_dictionary()`
  - Delete active dictionary 以 fallback 呼叫 `_set_active_dictionary()`
  - Rename 非 active dictionary 不呼叫 `_set_active_dictionary()`
  - Rename active dictionary 以新名稱呼叫 `_set_active_dictionary()`
  - 操作成功後管理清單立即 refresh

此項屬測試完整性與維護風險；依目前程式碼審閱，未觀察到已發生的使用者功能錯誤。

## 前次 Findings 關閉狀態

### Task 0 P1：字典管理動作直接改變目前轉譯字典

**狀態：已修正。**

修正後：

- `_refresh_dictionary_names()` 只更新 `_dictionary_names` 並回傳管理清單選取，不再改寫 `translation_settings` 或 config。
- Add / Import 成功後只重載字典名稱與管理清單選取。
- Delete 只有在刪除目標等於 active dictionary 時，才透過 `resolve_active_dictionary_after_delete()` 和 `_set_active_dictionary()` 套用 fallback。
- Rename 只有在重新命名目標等於 active dictionary 時，才透過 `resolve_active_dictionary_after_rename()` 和 `_set_active_dictionary()` 更新名稱。
- 管理對話框持有與 frame 相同的 `_dictionary_names` list；frame 使用 slice assignment 更新內容，讓 callback 返回後 list view 能立即讀到新清單。

以上行為符合 spec 對 staged Translation Settings 與 immediate Dictionary Management 的責任分離。本次未發現 Add、Import、Delete 非 active dictionary 或 Rename 非 active dictionary 會改寫 active setting 的路徑。

### Task 0 P2：F6 測試與主視窗使用不同 section order

**狀態：已修正。**

`gui.py` 已刪除 `VISIBLE_SECTION_ORDER` 與 `_get_adjacent_visible_section()`，`on_char_hook()` 現在直接呼叫 `ui.section_navigation.get_adjacent_section()`。主視窗與 `test_section_navigation.py` 已使用同一個 `SECTION_ORDER` source of truth。

### Task 0 P2：核心 UI 流程缺少自動化回歸測試

**狀態：部分改善，尚未關閉。**

新增的 `test_translation_dictionary_state.py` 已覆蓋 active dictionary 的純規則，但沒有覆蓋 handler wiring、modal dialog 結果、list view refresh 或 Edit 關閉/開啟順序。詳見本次 P2 finding。

## Commit-by-commit 審閱

### 1. `f040b7f` — `fix: separate dictionary state updates`

**正確的修正：**

- 將 `_refresh_dictionary_names()` 與 `_set_active_dictionary()` 分離，避免 refresh 隱含持久化 active setting。
- Add / Import 不再改變 active dictionary。
- Delete / Rename 只在操作目標是 active dictionary 時修正 active state。
- 刪除 active dictionary 時使用刪除前清單計算 fallback，避免已刪除項目造成錯誤選取。
- 主視窗 F6 導覽改用共用 `get_adjacent_section()`。
- 以 slice assignment 更新共享字典名稱清單，使目前 callback/list view 架構能立即看到內容變更。

**未發現的新功能性問題：**

- 沒有改變 CSV 格式、轉譯表設定或轉換輸出。
- 沒有讓 Add / Import 重新取得修改 active setting 的路徑。
- Delete / Rename 的 active 與 non-active 分支符合 spec。
- Edit 關閉管理對話框再開啟 entry editor 的流程未被此 commit 改動。
- Translation Settings 的 `Cancel` 分支仍不提交；`OK` 分支仍正規化並持久化完整設定。

**仍需改善：**

- 新增的 Add 純函式未接入 production code，相關測試無法驗證實際 handler。
- 尚缺 Windows UI smoke test結果與 wx orchestration 自動化測試。

## 驗證結果

### 通過

```bash
python3 -m py_compile \
  client/gui.py \
  client/dialog.py \
  client/translation/settings.py \
  client/translation/dictionary_state.py \
  client/ui/translation_menu.py \
  client/ui/section_navigation.py \
  client/tests/test_translation_dictionary_state.py \
  client/tests/test_section_navigation.py
```

結果：exit code 0。

```bash
cd client && python3 -m unittest \
  tests.test_translation_dictionary_state \
  tests.test_translation_settings \
  tests.test_translation_menu \
  tests.test_section_navigation \
  tests.test_config \
  tests.test_dictionary_actions \
  tests.test_dictionary_manager \
  tests.test_input_shortcuts -v
```

結果：40 tests passed。

`git diff --check f040b7f^ f040b7f` 結果：沒有 whitespace error。

### 未完全通過

```bash
cd client && python3 -m unittest discover -s tests -v
```

結果：執行 102 tests，3 個既有環境相關 import errors：

- `test_language_detection_translation`：缺少 `liblouis.dll`
- `test_translation_language_result`：module-level `pytest.skip` 被 unittest discovery 視為 import error
- `test_translation_result`：module-level `pytest.skip` 被 unittest discovery 視為 import error

與 Task 0 相同，此命令 exit code 為 1。未出現由 `f040b7f` 新增的測試失敗。

## 整體結論

**審閱結論：主要修正正確，但測試 finding 尚未完整關閉。**

Task 0 的 P1 狀態耦合與 F6 雙重 source of truth 已完成修正，本次未發現因此產生新的功能性問題。仍需補上實際 handler / dialog orchestration 的回歸測試；尤其目前 Add 測試只覆蓋未被 production code 使用的 helper，不能作為修正已被自動化保護的證據。
