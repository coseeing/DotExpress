# Task 2 完成說明

本次依據 `docs/superpowers/review_task1.md` 的 review 結果進行修正，並先確認 review 指出的兩個問題確實存在後才修改。

修正內容：

- 修正 `normalize_base_name()` 與 dialog 驗證流程，讓原始尾端 ASCII 空格與控制字元不會被繞過。
- 將名稱驗證維持為 Windows filename 規則，但不再使用 `isspace()` 去誤殺可接受的 Unicode whitespace。
- 更新文件、字典與 dialog 的回歸測試，涵蓋 `name `、` name `、`name\t`、以及 Unicode whitespace 行為。

驗證結果：

- `cd client && python3 -m unittest tests.test_document_workspace tests.test_dictionary_manager tests.test_dialog_validation -v`
- `cd client && python3 -m unittest discover -s tests -v`

結果：全部通過；完整 client unittest suite 為 `130` tests passed，`8` skipped（既有 Windows/liblouis 條件性 skip）。

新增 commit list：

- `a5a2bc1` — `fix: tighten windows filename validation`

