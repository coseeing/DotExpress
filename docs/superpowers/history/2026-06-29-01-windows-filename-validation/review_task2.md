# Task 2 Code Review

## Findings

未發現需要修正的 blocking、important 或 minor finding。

## Resolved Findings

### Task1 P1：前置空白繞過尾端空白驗證

已完成修正。

`normalize_base_name()` 與 dialog helper 現在都先檢查原始輸入：

- U+0000 到 U+001F 控制字元會在 `strip()` 前被拒絕。
- 原始名稱以 ASCII Space U+0020 或 `.` 結尾時會被拒絕。
- 判斷不再依賴第一個字元，因此前置空白無法繞過。

聚焦 probe 結果：

```text
"name "   -> rejected
" name "  -> rejected
"\tname\t" -> rejected
```

文件與字典共用的 domain normalizer，以及兩個名稱 dialog，皆有對應回歸測試。

### Task1 P2：`isspace()` 誤拒非 ASCII whitespace

已完成修正。

production code 已移除 `isspace()`，改為精確區分：

- Windows 特別處理的尾端 ASCII Space U+0020。
- Windows 禁止的 U+0000 到 U+001F 控制字元。
- 其他 Unicode whitespace 不會因 `isspace()` 被直接判定為非法。

依 spec 的「Normalization remains trim-based」，例如 `"name\u3000"` 會被接受並正規化為 `"name"`。這與現行規格一致，因此不列為 finding。

## Commit Review

依 commit 時間由舊到新審查；task2 完成文件只列出一個 commit：

1. `a5a2bc1` — `fix: tighten windows filename validation`
   - 原始控制字元與尾端 ASCII 空格在 trim 前驗證，關閉前置空白繞過。
   - 移除過度寬泛的 `isspace()` 判斷。
   - dialog 的 OK 流程改讀取未 trim 的 TextCtrl 值，避免 UI 在驗證前遺失尾端字元。
   - 文件、字典與 dialog 測試均補上前次 findings 的回歸案例。
   - 未發現此 commit 引入新的功能或相容性問題。

## Verification

執行 task2 完成文件列出的聚焦測試：

```bash
cd client
python3 -m unittest \
  tests.test_document_workspace \
  tests.test_dictionary_manager \
  tests.test_dialog_validation \
  -v
```

結果：38 tests passed。

執行完整 client suite：

```bash
cd client
python3 -m unittest discover -s tests -v
```

結果：130 tests passed，8 skipped；skip 均為既有 Windows/liblouis 平台條件。

另以聚焦 probe 驗證：

- `"name "`、`" name "`、`"\tname\t"` 在文件與字典 normalizer 都會被拒絕。
- U+00A0、U+3000 等非 ASCII whitespace 不再被 `isspace()` 規則拒絕。
- `1.1`、Windows 非法字元、保留裝置名稱與 32 字元限制的既有測試仍通過。

## Residual Risk

目前沒有在 Windows 實際 wxPython UI 中執行手動驗證；本次結論依據 production code 路徑、無 GUI 單元測試與完整 client suite。

Unicode whitespace 會依 Python `strip()` 正規化，而非原樣保存。這符合目前 spec 的 trim-based normalization；若產品未來要求所有 Windows 合法 Unicode 字元必須原樣存在與顯示，應先修改規格並另行加入 round-trip 測試。

## Assessment

task2 已完成 task1 review 指出的兩項修正，且未發現由本次 commit 造成的新問題。就目前 spec、plan 與可執行測試而言，可判定 review 通過。
