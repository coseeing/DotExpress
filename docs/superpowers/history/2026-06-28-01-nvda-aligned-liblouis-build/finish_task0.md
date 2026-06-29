# Task 0 完成說明

## 變更摘要

- 已使用 `scripts/sync_nvda_liblouis.py` 產生 NVDA 對齊的 vendor snapshot。
- 已將 `client/braille/louis_helper.py` 更新為同步後的 NVDA helper 內容。
- 已將 `client/braille/liblouis/__init__.py` 更新為從 `vendor/nvda/liblouis/python/__init__.py.in` 產生的 runtime binding。
- 已更新 NVDA 對齊版 liblouis 設計文件與 README，補上 vendor snapshot、runtime 產生流程與同步驗證說明。

## 驗證

- `python3 scripts/sync_nvda_liblouis.py`
- `python3 -m unittest scripts.tests.test_sync_nvda_liblouis -v`
- `python3 -m unittest scripts.tests.test_liblouis_build_contract -v`
- `diff -u vendor/nvda/liblouis/runtime/louis_helper.py client/braille/louis_helper.py`
- `python3 - <<'PY' ...` 比對 `client/braille/liblouis/__init__.py` 與 `vendor/nvda/liblouis/python/__init__.py.in` 產生結果

## Commit List

- 尚未建立 commit；目前變更仍在工作樹中。
