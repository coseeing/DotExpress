# Task 0 Code Review

## Findings

### [P1] 名稱尾端空白在驗證前被移除，未依 spec 拒絕

位置：`client/name_validation.py:51-58`  
相關 commit：`236ad9d` (`fix: validate Windows-safe names`)

`normalize_base_name()` 先執行 `name.strip()`，再把結果交給 `_is_windows_legal_name()`。因此 `"name "`、`"name\t"` 等輸入會先變成 `"name"` 並通過，而 `_is_windows_legal_name()` 的 `name.endswith(" ")` 分支永遠無法看到原始尾端空白。

這與 spec 的明確要求「names ending with `.` or space」及測試清單中的 `name ` 必須拒絕不符。文件和字典共用此入口，所以兩者都受影響。現有測試只使用 `"a. "`；該值在 `strip()` 後仍以 `.` 結尾，因此沒有捕捉純尾端空白案例。

實際結果：

```text
normalize_document_name("name ") -> "name"
normalize_dictionary_name("name ") -> "name"
```

建議在正規化前先拒絕原始名稱的尾端 `.` 或空白，或明確調整 spec；依目前已核准規格應採前者。並為文件及字典加入精準的 `"name "` 回歸測試。

### [P2] 新驗證訊息未經 gettext，POT/PO 中新增的是未使用字串

位置：`client/dialog.py:47`、`client/dialog.py:69`  
相關 commits：`b48d138` (`fix: validate dialog names with windows rules`)、`c3a8176` (`fix: update filename validation translations`)

`WINDOWS_FILE_NAME_ERROR` 直接硬編碼為繁體中文：

```python
WINDOWS_FILE_NAME_ERROR = "請輸入有效的 Windows 檔名。"
```

但 `c3a8176` 在 POT/PO/MO 中加入的是：

```text
Dictionary name is not a valid Windows file name.
Document name is not a valid Windows file name.
```

production code 沒有呼叫這兩個 msgid，因此 catalog 更新不會控制實際 UI 訊息；重新執行字串擷取時也可能移除這些無來源字串。這同時讓文件與字典共用同一個硬編碼訊息，無法依 catalog 分別翻譯。

現有 `test_dialog_validation.py:67-98` 直接期待硬編碼繁中，反而固定了這個錯誤行為。建議由兩個 dialog 傳入各自的 `_()` 訊息，移除硬編碼常數，並讓測試驗證對應 gettext 結果。

## Commit Review

依 commit 時間由舊到新審查：

1. `236ad9d` — 共用 Windows 檔名驗證方向正確，文件與字典確實共用入口；發現尾端空白被提前 trim 的 spec 偏差。
2. `14ee813` — `1.1.txt` 與 DEP 內部 `1.1.txt`／`1.1.brl` round-trip 測試符合規格，未發現其他問題。
3. `b48d138` — dialog 已委派 domain normalizer，初始值與全選行為正確；發現錯誤訊息硬編碼繁中。
4. `96366f3` — 匯入流程以 `source.stem` 預填、可採用修改後名稱，Cancel 時不呼叫匯入；新增、重新命名與匯入共用提示 helper，未發現阻擋問題。
5. `c3a8176` — POT/PO/MO 有更新，但新增 msgid 未被 production code 使用，未真正完成 gettext 串接。

## Verification

執行：

```bash
cd client
python3 -m unittest \
  tests.test_document_workspace \
  tests.test_dictionary_manager \
  tests.test_dialog_validation \
  tests.test_dictionary_import_flow \
  -v
```

結果：40 tests passed。

執行：

```bash
cd client
python3 -m unittest discover -s tests -v
```

結果：130 tests passed，8 skipped；skip 均為既有 Windows/liblouis 平台條件。

另以聚焦 probe 確認兩項 findings：尾端空白目前會被正規化後接受；POT/PO 有新英文 msgid，但 `dialog.py` 未以 gettext 使用它們。

## Assessment

目前不建議視為完全符合 spec。核心含點號文件／字典名稱及字典匯入取消流程已完成，但應先修正上述 P1，並同步處理 P2 的 gettext 串接與測試。
