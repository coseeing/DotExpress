# Task 1 完成說明

本次依據 `docs/superpowers/review_task0.md` 的 review 結果進行修正，並先確認 review 指出的問題確實會影響目前行為後才修改。

修正內容：

- 修正 `normalize_base_name()` 與 dialog 驗證流程，讓 `name ` / `name\t` 這類尾端空白輸入會被拒絕。
- 將 `DocumentNameDialog` 與 `DictionaryNameDialog` 的無效名稱訊息改為透過 gettext 取得對應翻譯，而不是硬編碼繁中。
- 更新對話框測試，讓它們驗證新的 gettext 訊息。

驗證結果：

- `cd client && python3 -m unittest tests.test_document_workspace.DocumentWorkspaceTest.test_normalize_document_name_rejects_windows_invalid_names tests.test_dictionary_manager.DictionaryManagerTest.test_normalize_dictionary_name_rejects_windows_invalid_names tests.test_dialog_validation -v`
- `cd client && python3 -m unittest discover -s tests -v`

結果：全部通過；完整 client unittest suite 為 `130` tests passed，`8` skipped（既有 Windows/liblouis 條件性 skip）。

新增 commit list：

- `aef30dc` — `fix: address filename validation review`

