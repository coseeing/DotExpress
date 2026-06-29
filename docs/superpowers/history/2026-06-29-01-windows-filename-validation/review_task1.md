# Task 1 Code Review

## Findings

### [P1] 前置空白可繞過尾端空白驗證，task0 的問題未完整關閉

位置：`client/name_validation.py:57-58`、`client/dialog.py:63-64`  
相關 commit：`aef30dc` (`fix: address filename validation review`)

新增條件只有在名稱第一個字元不是空白時，才拒絕尾端空白：

```python
if name and name[-1].isspace() and not name[:1].isspace():
```

因此修正雖然會拒絕 `"name "` 與 `"name\t"`，但只要在前面加上空白，同一個尾端空白就會略過驗證：

```text
normalize_document_name(" name ") -> "name"
normalize_dictionary_name(" name ") -> "name"
normalize_document_name("\tname\t") -> "name"
normalize_dictionary_name("\tname\t") -> "name"
```

這仍違反 spec 的「names ending with `.` or space」及 task0 要求原始尾端空白必須被拒絕。domain normalizer 與 dialog 又各自實作相同條件，使兩條路徑同時存在此繞過。

建議先明確區分「允許前置空白並 trim」與「拒絕任何原始尾端 ASCII 空格／控制字元」，不要讓是否拒絕尾端字元取決於第一個字元。至少新增 `" name "` 與 `"\tname\t"` 的文件、字典及 dialog 回歸測試。

### [P2] `isspace()` 會拒絕 Windows 可保留的非 ASCII 尾端空白

位置：`client/name_validation.py:57`、`client/dialog.py:63`  
相關 commit：`aef30dc` (`fix: address filename validation review`)

Windows 特別處理的是尾端 ASCII Space U+0020 與 ASCII period U+002E；其他前置或尾端空白字元會保留。Microsoft 文件亦明確說明，U+3000 IDEOGRAPHIC SPACE 不會受到相同特殊處理。

目前使用 `str.isspace()`，會把 U+00A0 NO-BREAK SPACE、U+3000 IDEOGRAPHIC SPACE 等非 ASCII 空白一併拒絕：

```text
normalize_document_name("name\u00a0") -> ValueError
normalize_document_name("name\u3000") -> ValueError
```

這與「只要是 Windows 合法檔名就允許」的需求不符，屬於本次修正新增的過度限制。參考：[Microsoft Learn: Support for whitespace characters in file and folder names](https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/file-folder-name-whitespace-characters)。

建議不要用 `isspace()` 代表 Windows 尾端 ASCII 空格規則。ASCII Space 應以 `char == " "` 判定；U+0000 到 U+001F 控制字元則使用既有的 code point 規則在 trim 前驗證，避免 tab/newline 被 `strip()` 消除。

## Resolved Findings

task0 的 gettext finding 已完成：

- `dialog.py` 不再硬編碼繁中錯誤訊息。
- 文件與字典 dialog 分別使用 `_()` 取得自己的 msgid。
- POT/PO/MO 中的 key 與 production code 一致。
- `gettext.GNUTranslations` 可從 `.mo` 正確載入：

```text
Dictionary name is not a valid Windows file name.
  -> 字典名稱不是有效的 Windows 檔名。
Document name is not a valid Windows file name.
  -> 文件名稱不是有效的 Windows 檔名。
```

## Commit Review

依 commit 時間由舊到新審查；task1 完成文件只列出一個 commit：

1. `aef30dc` — gettext 修正完成，且新增測試涵蓋 `"name "`／`"name\t"`；但前置空白條件造成可繞過的尾端驗證，`isspace()` 也新增了對合法 Unicode 空白的過度限制。

## Verification

執行 task1 完成文件列出的聚焦測試：

```bash
cd client
python3 -m unittest \
  tests.test_document_workspace.DocumentWorkspaceTest.test_normalize_document_name_rejects_windows_invalid_names \
  tests.test_dictionary_manager.DictionaryManagerTest.test_normalize_dictionary_name_rejects_windows_invalid_names \
  tests.test_dialog_validation \
  -v
```

結果：10 tests passed。

執行完整 client suite：

```bash
cd client
python3 -m unittest discover -s tests -v
```

結果：130 tests passed，8 skipped；skip 均為既有 Windows/liblouis 平台條件。

另外執行聚焦 probe，確認 `"name "` 與 `"name\t"` 已拒絕、gettext catalog 已生效，但也重現上述前置空白繞過與 Unicode 空白過度拒絕。

## Assessment

task1 已完整修正 gettext finding，但尾端空白 finding 只處理了測試列出的直接字串，仍可由前置空白繞過，並新增 Unicode 空白相容性問題。目前不建議將 task1 判定為 review 完成。
