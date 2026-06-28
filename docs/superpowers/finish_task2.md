# Task 2 完成說明

本次依 `docs/superpowers/review_task1.md` 先驗證 review 指出的問題，再只修正確認成立的項目。

已確認並處理的 review findings：

- `scripts/sync_nvda_liblouis.py` 的 `sconscript` 轉換原本依賴脆弱的多行 `replace()`：
  - 已改為精確一次匹配的 `_replace_once(...)`
  - 若上游 NVDA `sconscript` 形狀改變，現在會明確拋出 `SyncError`
- `sconstruct` 原本沒有在安裝 runtime tables 前清理舊目錄：
  - 已加入 `Delete("#client/braille/liblouis/tables")`
  - 避免舊版 `.in` / `Makefile.am` / `README` 類殘留檔混入 runtime tree
- `client/tests/test_liblouis_runtime.py` 原本只檢查 DLL 有載入、版本字串非空：
  - 已改為從 `include/liblouis/configure.ac` 解析 expected version
  - Windows runtime 測試在可執行環境下會直接比對 DLL 回報版本與 pinned source version 是否一致
- 依上述修正補強測試：
  - 新增 `sconscript` install block 形狀改變時必須失敗的測試
  - 新增 `sconstruct` 必須包含 runtime tables cleanup 契約的測試

本次驗證：

- `python3 -m unittest scripts.tests.test_sync_nvda_liblouis scripts.tests.test_liblouis_build_contract -v`
- `python3 -m py_compile scripts/sync_nvda_liblouis.py client/tests/test_liblouis_runtime.py`
- `python3 -c "compile(open('sconstruct', encoding='utf-8').read(), 'sconstruct', 'exec')"`
- `cd client && python3 -m unittest tests.test_liblouis_runtime -v`
  - 在目前 Linux 環境為 `skipped=5`，原因是該測試明確限制 `win32`
- `git diff --check`

新增 commit list：

- `fix: harden nvda liblouis sync review fixes`

限制：

- 目前工作區不是 Windows x64 環境，無法在此直接重建 `client/braille/liblouis.dll` 並完成實際 DLL/tables 配對驗證。
- 這次已把 review 指出的同步、建置契約與 runtime version 檢查補齊；若要真正消除目前 `3.37.0` source / `3.35.0` DLL 的落差，仍需在 Windows clean build 環境重建並重新驗證。
