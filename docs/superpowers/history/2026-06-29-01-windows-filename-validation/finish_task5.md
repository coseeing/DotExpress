# Finish Task 5

## Review 結論確認

已確認 `docs/superpowers/review_task4.md` 指出的問題成立：先前的 no-op shortcut 使用 `casefold()` 比對，會把 `alpha -> Alpha` 這種大小寫變更也當成不需處理，導致 case-only rename 行為被吞掉。

## 實作結果

- 將 dictionary rename 的 no-op 判斷收斂為「完全相同字串」才視為不需變更。
- 保留原本的相同名稱 no-op 行為，讓按下確認後不會回到列表，而是維持在名稱確認流程中。
- 補上 regression test，確認：
  - 完全相同名稱時會回傳既有路徑，且不重新 rename。
  - 只有大小寫不同時仍會正常 rename 成新名稱。
- 清理 `client/gui.py` 中已無使用的 import。

## 驗證

已執行：

```bash
cd client
python3 -m unittest tests.test_dictionary_name_prompt tests.test_dictionary_manager tests.test_dialog_validation -v
python3 -m unittest discover -s tests -v
```

結果：

- 聚焦測試：通過
- client 全測試：`134` passed, `8` skipped

## 新增 Commit

- `3530772` — `fix: preserve case-only dictionary renames`
