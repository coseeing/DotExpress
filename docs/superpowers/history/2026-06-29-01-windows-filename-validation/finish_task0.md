# Task 0 完成說明

本次實作已完成 Windows filename validation 設計與 plan 中的各項工作，重點如下：

- `normalize_base_name()` 改為檢查 Windows 合法檔名規則，允許 `1.1` 這類包含 `.` 的名稱。
- 文件與字典名稱共用同一套驗證邏輯。
- 文件匯入的 `1.1.txt` 可正常匯入，並保留 `1.1` 作為文件名稱。
- 字典匯入改為先依來源檔名 stem 預填名稱對話框，使用者可修改或取消。
- 名稱對話框改為委派 domain normalizer，並顯示新的 Windows 檔名驗證訊息。
- gettext template / zh_TW catalog / compiled `.mo` 已同步更新。

已新增或更新的測試涵蓋：

- 文件名稱允許 `1.1`，並拒絕 Windows 非法名稱。
- 字典名稱允許 `1.1`，並拒絕 Windows 非法名稱。
- 文件文字匯入與 `.dep` round-trip 對含點號名稱的行為。
- 字典匯入流程可預填來源 stem，且取消時不會進行匯入。
- 對話框可套用初始字串並全選。

驗證結果：

- `cd client && python3 -m unittest tests.test_document_workspace tests.test_dictionary_manager tests.test_dialog_validation tests.test_dictionary_import_flow -v`
- `cd client && python3 -m unittest discover -s tests -v`

結果：全部通過；完整 client unittest suite 為 `130` tests passed，`8` skipped（既有 Windows/liblouis 條件性 skip）。

補充：

- 本機沒有 `msgfmt`，因此 `.mo` 以 Python fallback 重新編譯；已用 `gettext.GNUTranslations` 驗證新訊息可正確載入。

新增 commit list：

- `236ad9d` — `fix: validate Windows-safe names`
- `14ee813` — `test: cover dotted document names`
- `b48d138` — `fix: validate dialog names with windows rules`
- `96366f3` — `fix: streamline dictionary import prompt`
- `c3a8176` — `fix: update filename validation translations`

