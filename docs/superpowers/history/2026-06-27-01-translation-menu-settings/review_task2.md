# Task 2 修正程式碼審閱報告

## 審閱範圍

- 修正完成資訊：`docs/superpowers/finish_task2.md`
- 前次審閱：`docs/superpowers/review_task1.md`
- 設計規格：`docs/superpowers/specs/2026-06-27-translation-menu-settings-design.md`
- 實作計畫：`docs/superpowers/plans/2026-06-27-translation-menu-settings-implementation-plan.md`
- 文件列出的 commit：
  1. `8f12bb20ef44b780cb4230001c2457990e53fa26` — `test: cover dictionary state orchestration`
- 比較基準：`6f06a4779331c7716090fe95056932063447840f`

`finish_task2.md` 只列出 `8f12bb2`，因此本次依 commit 時間由舊到新的審閱順序只有該 commit。Ancestry 中的 `f040b7f` 與文件 commit `6f06a47` 未列在 Task 2 Commit List，不納入本次 commit-by-commit 評斷。

## Findings

**沒有發現新的 P1 或 P2 程式缺陷。**

本次變更正確地讓 production code 與測試共用相同的 dictionary-state orchestration planner。Task 1 指出的「測試只覆蓋未使用 helper」問題已消除。

## Task 1 Finding 關閉狀態

### 新增測試未驗證 production decision path

**狀態：已修正。**

修正內容：

- 移除未被 production code 使用的 `resolve_active_dictionary_after_add()`。
- 新增 `DictionaryStateUpdate`，同時表達：
  - Dictionary Management 應選取的字典
  - Translation Settings 應維持或更新的 active dictionary
- 新增並由 production code 實際呼叫：
  - `plan_dictionary_state_after_add()`
  - `plan_dictionary_state_after_rename()`
  - `plan_dictionary_state_after_delete()`
- Add 與 Import 共用 `plan_dictionary_state_after_add()`。
- Rename 與 Delete 依 planner 結果判斷是否需要呼叫 `_set_active_dictionary()`。
- 新測試直接驗證 production 使用的 planner，而非只為測試存在的替代函式。

對照 spec，planner 結果符合下列規則：

- Add / Import：管理清單選取新字典，active dictionary 保持原值。
- Rename 非 active dictionary：管理清單選取新名稱，active dictionary 不變。
- Rename active dictionary：管理清單與 active dictionary 都更新為新名稱。
- Delete 非 active dictionary：active dictionary 不變。
- Delete active dictionary：active dictionary 套用既有 fallback。

## Commit-by-commit 審閱

### 1. `8f12bb2` — `test: cover dictionary state orchestration`

**正確性：**

- `DictionaryStateUpdate` 讓 management selection 與 active selection 的兩種語意明確分離。
- Add / Import 在建立或匯入完成後重新讀取實際字典清單，再交由 planner 決定管理清單選取。
- Delete 使用刪除前清單計算 remaining names 與 active fallback，符合既有 `plan_dictionary_delete()` 規則。
- Rename 使用重新命名後的實際清單解析新名稱與 active selection。
- `_set_active_dictionary()` 只在 Rename / Delete 的 planner 結果與目前 active name 不同時呼叫，沒有重新引入 Task 0 的「管理動作一律改寫 active setting」問題。
- Dictionary Management 仍透過共享 list 的 slice update 立即取得新清單；本 commit 沒有破壞 list view refresh 流程。

**新問題檢查：**

- 沒有新增對 wxPython 的依賴到純 state 模組。
- 沒有變更字典 CSV、config schema、轉譯表或轉換輸出格式。
- 沒有改動 Translation Settings 的 OK / Cancel 提交邊界。
- 沒有改動 Dictionary Management 的 Edit 關閉與 editor 開啟順序。
- 沒有改動 F6 / Shift+F6 或 `Ctrl+Enter`。
- 沒有留下舊的 `resolve_active_dictionary_after_add()` 參照。

## 非阻擋風險

本次修正已關閉 Task 1 的具體 finding，但原始 Task 0 所提的完整 wx UI orchestration 覆蓋仍不完整。目前自動化測試仍未直接建立或 mock `BrailleFrame` 來驗證：

- Translation menu item 到 handler 的 binding
- Translation Settings 的 modal OK / Cancel wiring
- Dictionary Management list view 的實際 refresh
- Edit 關閉管理對話框後才開啟 entry editor
- `Ctrl+Enter` 與 menu Convert 的同一路徑

這些是既有測試範圍限制，不是 `8f12bb2` 引入的新問題。建議在可穩定執行 wxPython 測試的 Windows CI 或以 dialog factory/mock 方式逐步補上；同時仍需保留人工 Windows UI smoke test。

另外，Add / Import handler 目前只消費 `DictionaryStateUpdate.management_selected_name`，不消費 `active_selected_name`。在 active dictionary 有效的正常流程中，這正好確保 Add / Import 不改變 active setting，符合 spec。若未來要支援「active dictionary 已被外部刪除」的自動修復，需明確決定是否在此流程套用 planner 的 active 結果，不應在未定義需求下自行改變。

## 驗證結果

### 通過

```bash
python3 -m py_compile \
  client/gui.py \
  client/translation/dictionary_state.py \
  client/tests/test_translation_dictionary_state.py
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

```bash
git diff --check 8f12bb2^ 8f12bb2
```

結果：沒有 whitespace error。

### 未完全通過

```bash
cd client && python3 -m unittest discover -s tests -v
```

結果：執行 102 tests，3 個既有環境相關 import errors：

- `test_language_detection_translation`：缺少 `liblouis.dll`
- `test_translation_language_result`：module-level `pytest.skip` 被 unittest discovery 視為 import error
- `test_translation_result`：module-level `pytest.skip` 被 unittest discovery 視為 import error

此命令 exit code 為 1。失敗項目與 Task 0、Task 1 相同，沒有出現由 `8f12bb2` 新增的測試失敗。

## 整體結論

**審閱結論：Task 2 修正完成，可接受。**

Task 1 指出的 production/test decision-path 落差已消除，本次未發現修正引入新的功能性缺陷。完整 wx UI orchestration 測試仍屬後續測試改善項目，但不阻擋本次修正驗收。
