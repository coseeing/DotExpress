# 字典檔案安全（F-2）設計

## 目標

修正任務 F-2 修正 P2 階段審查列在「既有缺陷清單」（`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md` 第 3、4 列）中，兩個與字典檔案有關的優先 1 資料遺失缺陷。兩者都由 `# KNOWN BUG` 測試釘住：

1. **帶 UTF-8 BOM 的字典 CSV 在按 OK 後遺失。** Excel（「CSV UTF-8」）與記事本存 UTF-8 時會加上位元組順序標記。所有讀取端都以 `encoding="utf-8"` 開啟字典 CSV，所以第一個表頭被讀成 `"\ufefftext"`。條目編輯器（`DictionaryEntriesDialog`）顯示零列，按 OK 後檔案被只有表頭的內容覆寫（P2-2 spec Q1，由 `test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header` 釘住）。同一份檔案讓每次轉換都以 `CSV must contain columns: text, braille, type` 失敗（P1-6 spec 已知缺陷 1），匯入以「匯入的檔案必須包含 text、braille 與 type 表頭。」拒絕，字典管理顯示 0 個條目。
2. **OK 先截斷字典檔再寫入。** `save_dictionary_entries` 以 `"w"` 開檔逐列寫入。中途失敗（例如 lone surrogate 造成的 `UnicodeEncodeError`）會留下表頭與失敗列之前的列，其餘全部消失（P2-2 Q3）。非 `OSError` 的例外也會逃出 OK handler，使用者什麼都看不到（P2-2 Q7）。兩者由 `test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file` 釘住。

本任務完成後：

- client 內每個 CSV 讀取端（字典讀取端與 `client/data` 的三個內建資料檔）都改用 `encoding="utf-8-sig"`：開頭的 UTF-8 BOM 被忽略，沒有 BOM 的檔案讀法與以前完全相同。
- 編輯器的 OK 先把字典寫到同目錄的暫存檔，再以 `os.replace` 安裝。任何失敗後，磁碟上的字典與之前逐位元組相同，且不留下暫存檔。
- OK handler 捕捉存檔時的任何 `Exception`，顯示既有的 `Failed to save: {error}` 訊息；對話框保持開啟、編輯內容保留。
- 寫出的內容不變：表頭 `text,braille,type`、欄位順序相同、UTF-8 **不帶** BOM、`\r\n` 行尾。

這是刻意的行為變更，只限於 BOM 檔案與存檔失敗。沒有新的使用者可見字串，msgid 不變（353，集合相同）。P2-2 Q2（未修改的字典也以正規化形式重寫）、Q4–Q6 與 Q8 維持原狀。

## 現況（2026-10-09 於 `fix/f2-dictionary-file-safety`、HEAD `aced6f8` 驗證）

`$SP` 為 session scratchpad，`$PY` 為 `$SP/venv/bin/python`。

基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 1114 tests`、`FAILED (failures=1, skipped=7)`；失敗為已知的 P2-5 案例 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`，skip 為僅限 Windows 的 liblouis 測試。在 repo 根目錄執行 `$PY $SP/p12/tools/msgid_scan.py client` 回報 `source msgids: 353`。Fixture：`client/tests/fixtures/translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`、`client/tests/fixtures/dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`。

### client 內所有 CSV 讀取

對 `client/`（排除 `.venv` 與 `tests`）grep `open(`、`read_text`、`csv.`，找到五個 CSV 讀取端，全部是 `open("r", newline="", encoding="utf-8")` + `csv.DictReader`：

| # | 位置 | 讀取 | 使用者 | 目前遇到 BOM |
| --- | --- | --- | --- | --- |
| R1 | `dictionaries/entries.py:48-69` `load_dictionary_entries`（tabs） | 使用者字典 | 條目編輯器（`DictionaryEntryListModel.load`，`dictionaries/entry_list_model.py:57-60`）；字典管理的條目數（`dialog.py:578-582`） | 沒有欄位對得上；每列 `row.get("text")` 為 `None`，全部被略過：空清單、條目數 0 |
| R2 | `dictionaries/manager.py:41-47` `validate_dictionary_csv`（4 spaces） | 匯入時選的檔案 | `import_dictionary`（`:63-73`） | `ValueError`；presenter（`dictionaries/presenter.py:176-178`）顯示「匯入的檔案必須包含 text、braille 與 type 表頭。」 |
| R3 | `conversion/text/dictionary_rules.py:168`，位於 `LoadedDictionaryRules.from_paths`（4 spaces） | 使用者字典 | 每次經 `DictionaryRulesLoader` 的轉換 | `ValueError("CSV must contain columns: text, braille, type")`，顯示為 `轉譯失敗：...`（stage `translation`） |
| R4 | `conversion/text/dictionary_rules.py:152`（同一方法） | `client/data/Bopomofo2Braille.csv` | 同上 | `ValueError("CSV must contain columns: Bopomofo, Braille")` |
| R5 | `conversion/text/char_maps.py:14` `_load_char_mapping`（4 spaces） | `client/data/BopomofoChar2Braille.csv`、`client/data/Braille2Ascii.csv` | 文字處理、ASCII 輸出 | `ValueError("CSV must contain columns: ...")` |

三個內建資料檔目前沒有 BOM（已檢查：開頭為 `Bopomofo,`／`Braille,`）。沒有其他程式碼讀 CSV：`config.py` 讀 JSON、`user_script.py` 讀前處理腳本、`documents/` 讀文字與文件包；`server/` 與 `scripts/` 沒有 CSV 程式碼。

### 所有字典寫入

| 位置 | 內容 | 模式 |
| --- | --- | --- |
| `dictionaries/entries.py:72-84` `save_dictionary_entries` | 編輯器的 OK（`DictionaryEntryListModel.save`，`entry_list_model.py:62-64`） | `mkdir(parents=True)`、`open("w")`（截斷）、`DictWriter` 表頭 + 各列。**覆寫使用者資料。** |
| `dictionaries/manager.py:18-26` `ensure_default_dictionary` | 只有表頭的 `default.csv` | 只在檔案不存在時 |
| `dictionaries/manager.py:50-60` `create_dictionary` | 只有表頭的新字典 | 只在 `exists()` 為 false 之後 |
| `dictionaries/manager.py:63-73` `import_dictionary` | `shutil.copyfile(來源, 新路徑)` | 只在 `exists()` 為 false 之後 |
| `dictionaries/manager.py:89-93` `export_dictionary` | `shutil.copyfile(受管字典, 使用者選的路徑)` | 使用者已在存檔對話框確認覆寫 |

只有 `save_dictionary_entries` 會覆寫既有的使用者字典。其他四個建立原本不存在的檔案（失敗時留下不完整的新檔，來源從未被動到），或複製到使用者在 app 外選定的路徑。它們與編輯器的存檔不共用 helper（見 D6）。

### OK handler

`dialog.py:491-497`（tabs）：

```python
def _on_ok(self, event: wx.CommandEvent) -> None:
	try:
		self._model.save(self.dictionary_path)
	except IOError as exc:
		wx.MessageBox(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
		return
	event.Skip()
```

`IOError` 就是 `OSError`。其他例外會逃出 wx handler（wx 會印出；對話框保持開啟，使用者什麼都看不到）。msgid `Failed to save: {error}` 的翻譯為 `儲存失敗：{error}`。

### 既有的原子寫入程式碼

`conversion/preprocessing/user_script.py:53-74`（`save_preprocessing_script`）與 `documents/workspace.py`（`PackageFiles.temporary_path`，F-1）已經以 `tempfile.NamedTemporaryFile(dir=<目標目錄>, prefix=f".{name}.", suffix=".tmp", delete=False)` 暫存寫入，再以 `os.replace` 安裝。`save_preprocessing_script` 在寫入**之後**才記下暫存路徑，所以寫入失敗會遺留 `.tmp` 檔（既有問題，本任務不修；見後續事項）。

### 釘住缺陷的測試

- `tests/test_dictionary_entries_dialog.py:823-830` Q1（BOM 開啟為空，OK 寫入只有表頭）。
- `tests/test_dictionary_entries_dialog.py:1344-1360` Q3 + Q7（條目 `"\ud800"` 取代 Alpha；OK 拋出 `UnicodeEncodeError`；檔案只剩表頭）。
- `tests/test_dictionary_entries_dialog.py:1312-1342` `test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds` 把字典路徑變成目錄，並以 `path.open("w")` 的錯誤組出預期訊息。不是 `KNOWN BUG`，但預期文字會改變（見 D5）。
- `tests/test_conversion_text_dictionary_rules.py:178-193` `_error_cases()` 中「Bopomofo header with BOM」與「dictionary header with BOM」兩列預期 `ValueError` 與欄位訊息。由 `test_apply_dictionary_raises_the_recorded_errors`（`:470`）與 `test_from_paths_raises_the_recorded_errors`（`:501`）使用。

以原型驗證（venv 的 Python 3.14）：`utf-8-sig` 把 `b"\xef\xbb\xbftext,..."` 讀成 `text`；只有 BOM 的檔案讀成空（`fieldnames is None`）；第二個 BOM 不會被去掉。把暫存檔 `os.replace` 到目錄上會拋出 `IsADirectoryError: [Errno 21] Is a directory: '<dir>/.dictionary.csv.<random>.tmp' -> '<dir>/dictionary.csv'`。Linux 上 `NamedTemporaryFile` 的 mode 為 `0600`。

## 決策

**D1. 五個讀取端全部用 `utf-8-sig`，資料檔也包含在內。** app 讀的每個 CSV 適用同一規則：R1–R5 只把 `encoding="utf-8"` 改成 `encoding="utf-8-sig"`。`utf-8-sig` 解碼沒有 BOM 的檔案時與 `utf-8` 完全相同（包括無效位元組的 `UnicodeDecodeError`），所以 app 與測試目前寫出的每個檔案讀法都不變。資料檔雖然出貨時沒有 BOM 也一併納入：維護者若用 Excel 或記事本編輯 `Bopomofo2Braille.csv`，否則會讓每次轉換失敗；也讓 R3 與 R4（同一方法）一致。兩個邊界情況都會釘住：只有 BOM 的檔案現在得到 `CSV must contain header row.`（以前是欄位訊息）；重複的 BOM 仍然在欄位檢查失敗。UTF-16 檔案（Excel「Unicode 文字」）與目前一樣不支援。

字面值在五個呼叫處各寫一次，不透過常數共用：`conversion/text` 目前不 import `dictionaries` 或 `shared`，且行為由每個讀取端各自的測試釘住。

**D2. 輸出編碼維持 UTF-8 不帶 BOM。** `save_dictionary_entries` 保持 `encoding="utf-8"`、`newline=""` 與 `DictWriter` 的 `\r\n`。因此帶 BOM 的字典在第一次 OK 後失去 BOM。這讓 app 寫出的每個位元組都不變（P2-2 golden trace 記錄了存檔後的 CSV），也是 brief 的要求。為了讓雙擊匯出檔時 Excel 正確開啟而寫入 BOM，是另一個 UX 選擇（後續事項）。

**D3. 匯入與匯出維持位元組複製。** D1 之後，`validate_dictionary_csv` 接受帶 BOM 的表頭，`shutil.copyfile` 連同 BOM 複製檔案；每個讀取端都接受它。匯入時去掉 BOM 會把複製變成重寫。不變。

**D4. 共用的原子文字寫入 helper：`client/shared/atomic_write.py`。** 新模組（4 spaces，與 `shared/name_validation.py` 相同），純 Python，不依賴 wx、i18n：

```python
def write_text_atomically(
    path: Path | str,
    write: Callable[[TextIO], None],
    *,
    encoding: str = "utf-8",
    newline: str | None = "",
) -> None:
```

行為：
1. 建立 `tempfile.NamedTemporaryFile("w", encoding=encoding, newline=newline, dir=<path 所在目錄>, prefix=f".{name}.", suffix=".tmp", delete=False)`（既有程式碼已用過兩次的模式）。目錄必須已存在；helper 不建立目錄（由呼叫端建立，`save_dictionary_entries` 本來就會）。
2. 在呼叫 `write(stream)` **之前**記下暫存路徑，接著 `stream.flush()` 與 `os.fsync(stream.fileno())`，然後關檔。
3. `os.replace(temporary, path)`，以 `os.replace` 形式呼叫（呼叫時才查屬性，讓測試可以 patch `os.replace`，不受 `wx_stub` 模組副本影響）。
4. 在 `finally` 中，若尚未安裝，就移除暫存檔（`unlink(missing_ok=True)`）；原本的例外原封不動傳出。涵蓋所有 `BaseException`（包括 `KeyboardInterrupt`）。移除失敗不會蓋掉原例外：原例外仍然傳出（`unlink` 的錯誤以 `contextlib.suppress(OSError)` 吞掉）。

保證（docstring）：正常返回時 `path` 的內容正好是 `write` 產生的內容；拋出例外時 `path` 不變（位元組相同，或仍不存在），且不留下暫存檔，除非移除暫存檔本身失敗。

納入 `fsync`，因為這次變更的重點就是字典永遠不會只寫一半；沒有它，某些檔案系統在 rename 之後立刻斷電可能留下空檔。字典很小，代價是每次 OK 一次 flush。

位置：放在 `shared/`，因為 helper 是通用的（目前給字典用，之後可能給前處理腳本等），而且 `shared` 不是 `wx_stub` 的 restore root，所以每份 `dictionaries.entries` 副本都使用同一個模組。`save_preprocessing_script` 與 `PackageFiles` **不**遷移（範圍；見後續事項）。

**D5. `save_dictionary_entries` 透過 helper 寫入。** 保留 `dictionary_path.parent.mkdir(parents=True, exist_ok=True)`，接著呼叫 `write_text_atomically(dictionary_path, <以 DictWriter 寫表頭與各列>, encoding="utf-8", newline="")`。位元組與現在相同。可見的後果：`os.replace` 拋出的 `OSError` 會同時列出暫存路徑與字典路徑（`... '<dir>\.default.csv.k2j1.tmp' -> '<dir>\default.csv'`）；建立暫存檔時拋出的則列出暫存路徑。訊息範本不變。因此 `test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds` 改為檢查訊息以 `儲存失敗：` 開頭、以 ` -> ` + `repr(str(path))` 結尾（CPython 在 Linux 與 Windows 都以 `%R -> %R` 格式化雙路徑的 `OSError`），不再用 `path.open("w")` 重建訊息。

**D6. 寫入端只改編輯器的存檔。** `manager.py` 的四個寫入端與 `save_dictionary_entries` 沒有共用程式碼（兩個以 `csv.writer` 寫表頭、兩個 `shutil.copyfile`），也從不覆寫既有的受管字典：最壞情況是留下不完整的**新**檔（建立／匯入失敗後的空的或不完整的 `name.csv`），或在使用者選定路徑留下不完整的匯出檔。這是一致性問題，不是使用者建立的字典遺失。列為後續事項；之後把兩個寫表頭的函式改用 helper 各只需一行。

**D7. OK handler 捕捉 `Exception`。** `except IOError as exc` 改為 `except Exception as exc`，保持相同的 `wx.MessageBox(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)` 與 `return`（不 `Skip`，對話框保持開啟、編輯保留）。理由：這是存檔的 UI 邊界；D4 之後任何失敗都保留原檔，唯一的問題是有沒有告訴使用者，而未捕捉的例外什麼都沒告訴他們；審查建議的修法也是如此；`conversion/output.py` 與 `gui.py:343` 在各自的邊界也用相同寬度。實際可能的非 `OSError` 失敗是 `UnicodeEncodeError`（lone surrogate）與 `csv.Error`；其他都是 bug，現在至少看得到。`BaseException`（`KeyboardInterrupt`、`SystemExit`）仍然傳出。`儲存失敗：` 後面是 Python 的英文錯誤文字，與 `OSError` 目前的情況相同。沒有新 msgid。

**D8. Windows 共用違規不重試。** `os.replace` 可能在舊的原地寫入會成功的情況下失敗：某個程式開著字典但沒有 `FILE_SHARE_DELETE`（編輯器、防毒掃描、索引服務、同步用戶端）。結果是既有的錯誤訊息且編輯保留；再按一次 OK 即重試。定時重試迴圈會加入 sleep 與一套策略，而這裡無法驗證。記錄於風險與 Windows 驗證待辦。

## 各檔設計

### `client/shared/atomic_write.py`（新檔，4 spaces）

依 D4 實作 `write_text_atomically`；import `os`、`tempfile`、`contextlib`、`Path`、`Callable`、`TextIO`。模組 docstring：一段說明保證，以及暫存檔為同目錄下的 `.<name>.<random>.tmp`。

### `client/dictionaries/entries.py`（tabs）

- `load_dictionary_entries`：`encoding="utf-8-sig"`。
- `save_dictionary_entries`：主體依 D5（以巢狀 `def _write(stream)` 包住既有的 `DictWriter` 程式碼）。加一行 docstring：「Replace the file atomically; on an error it is unchanged.」
- Import `from shared.atomic_write import write_text_atomically`。

### `client/dictionaries/manager.py`（4 spaces）

`validate_dictionary_csv`：`encoding="utf-8-sig"`。其他不變。

### `client/conversion/text/dictionary_rules.py`、`client/conversion/text/char_maps.py`（4 spaces）

`dictionary_rules.py:152`、`:168` 與 `char_maps.py:14` 改為 `encoding="utf-8-sig"`。訊息、順序與其他一切不變。`from_paths` 的 docstring 加上「A leading UTF-8 BOM is ignored.」

### `client/dialog.py`（tabs）

`DictionaryEntriesDialog._on_ok`：`except IOError as exc:` 改為 `except Exception as exc:`。其他不變。

### `client/dictionaries/entry_list_model.py`

不改程式碼。`save` 的 docstring（「errors propagate」）仍然正確。

## 維持不變的部分

- 任何字典按 OK 寫出的位元組（表頭、欄位順序、quoting、UTF-8 不帶 BOM、`\r\n`），包括未修改字典的正規化重寫（Q2，仍釘住）。
- 讀取任何沒有 BOM 的檔案：列、略過、strip、錯誤型別與訊息、先讀 Bopomofo 的順序（`OpenRecorder`）。
- 匯入／匯出／新增／重新命名／刪除流程及其訊息；編輯器的新增／編輯／刪除／篩選；Q4、Q5、Q6、Q8 測試不變。
- `client/tests/fixtures/dictionary_entries_trace.json`：trace 的 `TRACE_CSV` 沒有 BOM，其文字也都能編碼，所以每個記錄的 `csv`（OK 之後的位元組）經過 helper 仍相同。不重新產生。
- `client/tests/fixtures/translation_golden.json`：其字典由測試以 `encoding="utf-8"`（無 BOM）寫出，並讀取內建資料檔（無 BOM），所以 D1 不改變任何輸入。不重新產生。
- msgid：353，集合相同；`client/locales` 不變。

## 測試計畫

新測試程式碼依各檔縮排（`test_dictionary_entries.py` 與 `test_dictionary_management_dialog.py` 用 tabs，其他用 4 spaces）。所有測試使用暫存目錄；不碰 `client/dictionary/`（真實使用者資料）。

### A. Helper（新檔 `client/tests/test_atomic_write.py`，class `WriteTextAtomicallyTest`）

1. `test_replaces_an_existing_file_with_the_written_text`：既有 `d.csv` 內容不同；callback 寫入 `"a,b\r\n"`；位元組正好是 `b"a,b\r\n"`（無 BOM、換行不轉換），目錄清單為 `["d.csv"]`。
2. `test_creates_a_file_that_does_not_exist`。
3. `test_write_error_keeps_the_original_bytes_and_leaves_no_temporary_file`：callback 先寫一行，再寫 `"\ud800"`；`UnicodeEncodeError` 傳出；原位元組相同；清單 `["d.csv"]`。
4. `test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file`：`patch("os.replace", side_effect=PermissionError(13, "denied"))`；記錄到的來源參數在同一目錄、名稱為 `.d.csv.*.tmp`；錯誤傳出；位元組相同；清單 `["d.csv"]`。
5. `test_interrupt_leaves_no_temporary_file_and_propagates`：callback 拋出 `KeyboardInterrupt`。
6. `test_failure_without_an_existing_file_creates_nothing`：同 3 但沒有既有檔；清單 `[]`。
7. `test_data_is_flushed_to_disk_before_the_replace`：以共用的 `Mock` parent 包裝（`wraps=`）`os.fsync` 與 `os.replace`；呼叫順序為先 `fsync` 後 `replace`。

### B. 字典存取（`client/tests/test_dictionary_entries.py`，`DictionaryEntryStorageTest`）

8. `test_load_ignores_a_utf8_bom`：`b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n"` 得到 `[DictionaryEntry("Alpha", "\u2801", "General")]`。
9. `test_save_writes_utf8_without_a_bom`：位元組正好是 `b"text,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n"`。
10. `test_save_failure_leaves_the_existing_file_unchanged`：既有兩列的檔案；存 `[Alpha, DictionaryEntry("\ud800", ...)]` 拋出 `UnicodeEncodeError`；位元組相同；清單不變（在存取層記錄 Q3 的回歸情境）。

### C. 轉換規則（`client/tests/test_conversion_text_dictionary_rules.py`）

- `_error_cases()`：把兩個「header with BOM」列換成「Bopomofo file is only a BOM」（`b"\xef\xbb\xbf"` → `ValueError`、`NO_HEADER`）與「dictionary is only a BOM」（同）。仍為 10 個案例；兩個表格測試的數量不變。加註解說明 F-2 讓 BOM 表頭變為有效（測試 11）。
11. `test_from_paths_ignores_a_utf8_bom_in_both_files`：一份含 Braille 列與 Bopomofo 列的字典加上 `TEST_BOPOMOFO`，各以有 BOM 與無 BOM 寫出；兩個 `LoadedDictionaryRules` 相等，`apply` 結果相同。

### D. 字元對照（`client/tests/test_conversion_text_char_maps.py`）

12. `test_translate_mapping_char_ignores_a_utf8_bom`：`"\ufeffsource,target\r\na,x\r\n"` 把 `"abc"` 對照為 `"xbc"`。

### E. 匯入（`client/tests/test_dictionary_manager.py`）

13. `test_import_dictionary_accepts_a_utf8_bom_and_copies_the_bytes`：`validate_dictionary_csv` 不拋例外；匯入後檔案位元組與來源相同（保留 BOM）；對它 `load_dictionary_entries` 得到該列。

### F. 字典管理條目數（`client/tests/test_dictionary_management_dialog.py`）

14. `test_utf8_bom_dictionary_counts_its_entries`：與 `test_refresh_sets_virtual_count_and_valid_entry_counts` 相同但用 BOM 檔；條目數欄顯示 `"1"`。

### G. 條目編輯器（`client/tests/test_dictionary_entries_dialog.py`）

- 翻轉 Q1：`test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header` 改為 `test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom`：列為 `[ALPHA_CELLS]`；OK 回傳 `True`；`saved_csv() == HEADER + "Alpha,\u2801,General\r\n"`，原始位元組不以 BOM 開頭。註解：原為 Q1 `KNOWN BUG`，由 F-2 修正。
- 翻轉 Q3/Q7：`test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file` 改為 `test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged`：相同設定（`"\ud800"` 編輯，即回歸情境）；先讀出原位元組；OK 回傳 `False`；log 正好是 `[["MessageBox", "儲存失敗：'utf-8' codec can't encode character '\\ud800' in position 0: surrogates not allowed", ERROR_TITLE, ERROR_FLAGS]]`（由 `UnicodeEncodeError` 文字組成；Python 的訊息，Linux 與 Windows 相同）；檔案位元組相同；目錄只有 `dictionary.csv`；列表仍顯示編輯內容。註解：原為 Q3/Q7 `KNOWN BUG`。
- 依 D5 更新 `test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds`（前綴與 ` -> 'path'` 後綴；另外：目錄只有 `dictionary.csv` 這個目錄，沒有 `.tmp`）。
15. `test_replace_failure_shows_the_message_keeps_the_file_and_a_later_ok_succeeds`：新增 Beta，`patch("os.replace", side_effect=PermissionError(13, "denied"))`；OK 回傳 `False`；訊息 `儲存失敗：[Errno 13] denied`；位元組相同；沒有 `.tmp`；patch 結束後 OK 回傳 `True` 並存下 Alpha 與 Beta。

淨數量：A 7、B 3、C 1、D 1、E 1、F 1、G 1 = 新增 15；翻轉與更新都是一對一取代。總數 `1114 + 15 = 1129`。

## 遷移步驟（每步一個綠燈 commit，先紅後綠）

1. `fix: add an atomic text-write helper` —— `shared/atomic_write.py` 與測試 A 1–7（紅：`ModuleNotFoundError`）。尚無使用者。
2. `fix: save dictionary entries atomically` —— D5 與 D7；測試 B 9–10、G 翻轉 Q3/Q7、G 更新、G 15。先紅：B 10、翻轉後的 Q3/Q7 測試與 G 15 在舊程式碼上失敗（截斷的檔案／逃出的例外／舊路徑從不拋出 `PermissionError`）。B 9 原本就通過（它釘住 D2）。
3. `fix: read dictionary and data CSVs with utf-8-sig` —— R1–R5 套用 D1；測試 B 8、C（表格變更與 11）、D 12、E 13、F 14、G 翻轉 Q1。先紅：每個新測試在 `utf-8` 下失敗，翻轉後的 Q1 測試也失敗。

每個 commit 以 brief 規定的 `Co-Authored-By` 行結尾。沒有 commit 修改 `.po`／`.mo`、fixture、`gui.py` 或 `entry_list_model.py`。

## 驗收標準

在所示路徑執行；`$SP`／`$PY` 同上。

1. `cd client && $PY -m unittest discover -s tests`：`Ran 1129 tests`、`FAILED (failures=1, skipped=7)`，唯一的失敗是已知的 P2-5 案例。
2. `cd client && for s in $(seq 1 20); do $PY $SP/shuffle_harness.py $s; done`：每個 seed 只回報 P2-5 失敗。
3. 聚焦：`cd client && $PY -m unittest tests.test_atomic_write tests.test_dictionary_entries tests.test_dictionary_entries_dialog tests.test_dictionary_manager tests.test_dictionary_management_dialog tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps -v` 通過。
4. 在 repo 根目錄，`$PY $SP/p12/tools/msgid_scan.py client` 回報 `source msgids: 353`，集合相同；`git diff main -- client/locales` 為空。
5. 兩個 fixture 的 sha256 不變。
6. App 資料：`$SP/p26impl/snap.sh` 在標準 1–2 前後輸出相同（`client/dictionary/` 是真實使用者資料，從不寫入）。
7. `grep -rn "KNOWN BUG (P2-2 spec, Q[137]" client/tests` 找不到結果；Q2、Q4、Q5、Q6、Q8 的標記不變。
8. `grep -rn "csv.DictReader" client --include=*.py --exclude-dir=.venv --exclude-dir=tests` 列出五個讀取端 R1–R5，且 `grep -rn "utf-8-sig" client --include=*.py --exclude-dir=.venv --exclude-dir=tests` 正好列出它們的五個 `open` 呼叫。
9. `git diff main --stat` 只涉及 `client/shared/atomic_write.py`、`client/dictionaries/entries.py`、`client/dictionaries/manager.py`、`client/conversion/text/dictionary_rules.py`、`client/conversion/text/char_maps.py`、`client/dialog.py`、上述測試檔，以及 spec／plan 檔。
10. Mutation 檢查（plan）：每個 mutant 至少被一個測試抓到：R1–R5 各自改回 `utf-8`（5 個）；`save_dictionary_entries` 改回直接 `open("w")`；helper 只在 `OSError` 時清理；在 `write` 之後才記下暫存路徑；沒有 `fsync`；暫存檔放在系統暫存目錄；輸出編碼改為 `utf-8-sig`；對話框只捕捉 `OSError`。

## Windows 驗證待辦（此處無法執行）

- 在 Windows 執行 `cd client && python -m unittest tests.test_atomic_write tests.test_dictionary_entries_dialog tests.test_dictionary_entries -v`：取代到目錄上的測試現在會在 `os.replace` 以 `PermissionError [WinError 5]` 失敗；其訊息仍必須以 ` -> '<path>'` 結尾。
- 打包後的程式，手動：用 Excel 存成「CSV UTF-8」、用記事本存成 UTF-8（含 BOM）各一份字典；匯入；字典管理顯示條目數；編輯器顯示其列；OK 後列仍在；轉換會使用它們。
- 用 Excel 開啟一份字典（Excel 會鎖住它），在編輯器按 OK：出現 `儲存失敗：` 訊息、編輯保留、檔案不變；關閉 Excel 後再按 OK 成功。字典資料夾中不留下 `.default.csv.*.tmp`。
- 開啟即時防毒時，連續編輯並按 OK 十次；記錄任何暫時性失敗（D8）。

## 風險

- **Windows 共用模式**（低到中，D8）。開著 CSV 但沒有 `FILE_SHARE_DELETE` 的程式，現在會讓 OK 在舊的原地寫入會成功的情況下失敗。失敗是可見且安全的（訊息、編輯保留、檔案不變），再按一次 OK 即重試。Excel 會完全鎖住檔案，以前同樣失敗。
- **檔案中繼資料**（低）。安裝的是新檔：在 Windows 上取得資料夾繼承的 ACL 與預設屬性；在 POSIX 上 mode 為 `0600`（NamedTemporaryFile），不是舊的 mode。字典路徑上的符號連結會被一般檔案取代。字典資料夾是每位使用者的 app 資料，預期都不影響；前處理腳本已是相同行為。
- **當機後遺留 `.tmp`**（低）。在建立與安裝暫存檔之間當機，會留下 `.<name>.csv.<random>.tmp`。`list_dictionary_names` 以 `*.csv` glob，所以它永遠不會被列出或載入；無害，可手動刪除。
- **捕捉範圍較廣**（低，D7）。存檔時的程式錯誤現在顯示訊息而不是 traceback；traceback 不再印出。在這個邊界可接受，而且無論如何檔案都完好。
- **BOM 檔案的行為變更**（刻意）。原本顯示為空且讓轉換失敗的 BOM 字典現在可用；第一次 OK 後以不帶 BOM 的形式存檔（D2）。

## 範圍外／後續事項

- P2-2 Q2（OK 以正規化形式重寫未修改的字典）、Q4–Q6、Q8：不變，仍釘住。
- `manager.py` 寫入端（D6）：新增／確保預設字典的表頭寫入、匯入／匯出的 `shutil.copyfile`：改走 helper（複製需二進位版本），讓失敗永遠不會留下不完整的新字典或被截斷的匯出檔。
- `save_preprocessing_script`（`user_script.py:53-74`）寫入失敗時遺留 `.tmp` 檔（暫存路徑在寫入後才記錄）；遷移到 `write_text_atomically`。`PackageFiles`（F-1）可維持原狀（二進位 zip、注入的 seam）。
- 匯出時（或每次存檔時）寫入 BOM，讓 Excel 正確開啟 UTF-8 字典：UX 決策。
- 其他會被 BOM 弄壞的文字輸入：前處理腳本（`read_text(encoding="utf-8")`，BOM 在那裡是 `SyntaxError`）與匯入的 `.txt` 文件（`documents/workspace.py:178-185` `load_text_document`，BOM 會成為文字的一部分）。若需要另開任務。
