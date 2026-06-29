# Task 1 完成說明

本次依 `docs/superpowers/review_task0.md` 先驗證 review 指出的問題，再只修正確認成立的項目。

已處理的 review findings：

- 修正 `scripts/sync_nvda_liblouis.py` 的 `sconscript` 轉換：
  - 移除完整的 NVDA-only custom test table 區塊
  - 保留 tables 安裝節點並回傳 `louisLibInstall`、`louisPython`、`louisTables`
- 修正 `scripts/sync_nvda_liblouis.py` 的 helper 轉換：
  - 不再讀取 `git show HEAD:client/braille/louis_helper.py`
  - 改為只根據 pinned NVDA `source/louisHelper.py` 做 deterministic 文字轉換
  - 可在臨時 root / 非 repository current working directory 下獨立執行
- 補齊 `sconstruct` 的最小 NVDA build environment 契約：
  - `UNICODE`
  - Windows target defines
  - `/MT`
  - release/link flags
- 新增與擴充測試，覆蓋上述 review 指出的盲點
- 新增 Windows-only runtime smoke test `client/tests/test_liblouis_runtime.py`

本次驗證：

- `python3 -m unittest scripts.tests.test_sync_nvda_liblouis scripts.tests.test_liblouis_build_contract -v`
- `python3 scripts/sync_nvda_liblouis.py`
- `diff -u include/nvda/nvdaHelper/liblouis/sconscript vendor/nvda/liblouis/build/sconscript`
- `diff -u vendor/nvda/liblouis/runtime/louis_helper.py client/braille/louis_helper.py`
- `python3 - <<'PY' ...` 檢查 `client/braille/liblouis/__init__.py` 是否等於 vendor template 代入 `liblouis.dll`
- `cd client && python3 -m unittest tests.test_liblouis_runtime -v`
  - 在目前 Linux 環境為 `skipped=5`，原因是該測試明確限制 `win32`
- `git diff --check`

新增 commit list：

- `fix: align nvda liblouis sync and build contract`
- `docs: record review task 1 results`

限制：

- 目前環境不是 Windows，無法在此工作區直接完成 `scripts/build-liblouis.bat`、`scons --no-exec`、DLL 重建與真正的 Windows runtime ABI 驗證。
- 這次已補上對應測試檔與靜態/同步層驗證，但 review 提到的 Windows clean build 證據仍需在 Windows x64 環境補跑。
