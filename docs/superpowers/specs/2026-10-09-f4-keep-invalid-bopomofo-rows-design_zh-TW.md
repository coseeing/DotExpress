# 保留不合法的注音列（F-4）設計

## 目標

修正任務 F-4 修正 F-W11：Windows 驗證的 GUI 自動化發現的資料遺失缺陷（`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`「新發現」；測試字典 `auto/data/dict_badbopo.csv`）：

> 不合法的注音列（例如 `ㄉㄨˋ|ㄗ˙`、`ㄕㄨˋ ㄒㄩㄝˊ`）在載入時被默默略過；字典管理的筆數不含它們。即使沒修改，在編輯器按確定也會把它們從檔案刪掉（4 行→2 行）。舊基線 `6e5819f` 相同。

它是 P2-2 quirk Q2（「OK 永遠重寫檔案，靜默丟掉 loader 略過的列（空 text、無效注音）與被 strip 的空白」）中「略過的列」那一半；P2 審查與 F 審查的缺陷清單都列為優先 2，並由 `# KNOWN BUG (P2-2 spec, Q2)` 的 `test_unchanged_dictionary_is_rewritten_in_normalized_form` 釘住。

使用者選擇方案 A：**編輯器無法顯示的列原封不動留在檔案中；編輯器不顯示、也不能刪除它們；按確定時寫回。**

本任務完成後：

- 字典編輯器顯示的列與今天完全相同。檔案中其餘的資料列（來源文字空白，或注音序列解析失敗的 `Bopomofo` 列）都被保留、隱藏，並留在檔案中的原位置。
- 確定會依檔案順序寫回每一列。隱藏列以讀入時的三個欄位原樣寫出（不 strip、類型不正規化）；以今天的 writer（F-2：UTF-8 無 BOM、`\r\n`、最小引號）寫出，原本就以同樣方式寫成的列會逐位元組相同。`dict_badbopo.csv` 按確定後逐位元組不變。
- 新增或編輯一個項目時，若來源文字與某個隱藏列的來源文字相同，以既有的重複訊息拒絕。
- 字典管理的筆數、匯入、匯出、改名、刪除與轉換都不變。

沒有新的使用者可見字串；msgid 不變（353，集合相同）。不改 `client/shared/atomic_write.py`、`client/dialog.py`、`client/gui.py`、`client/conversion/`。

非目標：在編輯器中顯示、編輯或修復隱藏列；告訴使用者它們存在（Q2）；改變轉換對它們的處理（Q3）；Q2 的其餘部分（沒修改的確定仍會 strip 顯示的列、把未知類型改寫成 `General`、丟掉 BOM、多餘欄位與超出 header 的欄位，並正規化換行與引號）；只在有變更時才寫檔；匯入／匯出／改名（它們本來就保留每一列，D8）。

## 現況（2026-10-09 於 `fix/f4-keep-invalid-bopomofo-rows`、HEAD `4953772` 驗證，Windows 11 26200）

`$PY` 是 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`（Python 3.13）；`$SP` 是本 session 的 scratchpad，本 spec 的原型放在 `$SP/f4spec/`（不 commit）。worktree 沒有 git-ignored 的 liblouis runtime 與 MathCAT；依 F-3 plan Task 0 從 main checkout 複製（`client/braille/liblouis.dll`、`client/braille/louis_helper.py`、`client/braille/liblouis/`、`client/mathcat/`、`include/liblouis/configure.ac`；兩邊 submodule 都是 `2aa5f84b`；`git status` 保持乾淨）後，`cd client && $PY -m unittest discover -s tests` 得到 `Ran 1211 tests`、`FAILED (errors=1, skipped=5)`；那個 error 是 F-W6（`test_dictionary_name_prompt ... test_case_only_rename_still_renames`）。`client` tree `c609d363`。msgid：`source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c`。Fixture（`git show HEAD:<path> | sha256sum`）：`dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`、`translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`。`dict_badbopo.csv` sha256 `c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4`。

### 所有 CSV reader（F-2 的 R1-R5）與它們丟掉的列

`grep -rn "csv.DictReader\|utf-8-sig" client --include=*.py --exclude-dir=.venv --exclude-dir=tests` 列出與 F-2 相同的五個 reader。只有 R1 的結果會被寫回。

| # | 位置 | 讀取 | 不使用的列 | 會寫回？ |
| --- | --- | --- | --- | --- |
| R1 | `dictionaries/entries.py:49-70` `load_dictionary_entries` | 使用者字典，供字典編輯器（`DictionaryEntryListModel.load`）與字典管理的筆數（`dialog.py:578-582`） | (a) `strip()` 後來源文字為空（`""`、`"  "`、缺欄）；(b) 正規化類型為 `Bopomofo` 且 strip 後的點字欄無法通過 `normalize_zhuyin_sequence`。兩者都 `continue`：該列從清單消失 | **會**：編輯器的確定（`save_dictionary_entries`）寫出清單，所以 (a)、(b) 從檔案被刪掉 |
| R2 | `dictionaries/manager.py:41-47` `validate_dictionary_csv` | 匯入時選的檔案 | 只讀 header | 否（匯入是 `shutil.copyfile`） |
| R3 | `conversion/text/dictionary_rules.py:169-197` `LoadedDictionaryRules.from_paths` | 使用者字典，每次轉換 | 只略過**未 strip** 的 text 為 `""` 的列。**不會**略過不合法的注音列（見下） | 否 |
| R4 | 同一方法，`:153-163` | 內附的 `client/data/Bopomofo2Braille.csv` | `Bopomofo` 為空的列 | 否 |
| R5 | `conversion/text/char_maps.py:14` | 內附的 `BopomofoChar2Braille.csv`、`Braille2Ascii.csv` | 來源不是單一字元的列 | 否 |

R1＋確定對一列做的其他事（變形，不是刪除）：text 與 braille 被 strip；`General`／`Bopomofo`／`Braille` 以外的類型（大小寫有別，空值或缺欄也算）變成 `General`；`text,braille,type` 以外的欄位與超出 header 的欄位（`DictReader` 放在 key `None` 下）被丟掉；header 變成 `text,braille,type`；BOM 被去掉、換行變成 `\r\n`（F-2 D2）；引號被正規化。完全空白的行由 `csv.DictReader` 自己略過。不合法的 `Braille` 列（U+2800-U+28FF 以外的字元）**不會**被丟掉：loader 不檢查它們（`test_load_preserves_invalid_braille_rows`）。

### 轉換會用到編輯器丟掉的列

brief 假設不合法的列在轉譯時被忽略。實際上沒有。R3 對 `Bopomofo` 列的點字欄執行 `processing`（`normalize_zhuyin_sequence`）；拋例外時保留原字串，改用 `Bopomofo2Braille.csv` 的 trie 掃描，所以該列仍然成為一條規則。原型（`$SP/f4spec/probe_translation.py`，使用真實資料檔與 parser）對 `dict_badbopo.csv` 的結果：

| 輸入 | 由檔案產生的規則 | 今天在編輯器按確定之後 |
| --- | --- | --- |
| `肚子` | replacement `\[⠙⠌⠐|⠓⠁\]` | 沒有規則，文字不變 |
| `數學` | replacement `\[⠊⠌⠐⠄⠑⠦⠂\]` | 沒有規則 |
| `臺北` | `\[⠞⠺\]` | `\[⠞⠺\]` |

R3 也會保留 text 只有空白的列（`"  "` 是一條取代兩個空白的規則），R1 則丟掉它。而且 R1 先 strip 再驗證，所以以一聲空白結尾的序列（`ㄇㄚ `）對 R3 合法、對 R1 不合法。因此今天一個沒有修改的確定就會改變轉換結果。這些路徑由 golden case「Bopomofo row with a processing that raises」與「Bopomofo row with the real zhuyin parser and data file」釘住（`tests/test_conversion_text_dictionary_rules.py:103-125`）。來源相同的兩條規則，R3 保留**第一條**（`_build_trie`，「the first duplicate source wins」），所以列的順序會影響轉換。

### Writer

`save_dictionary_entries`（`entries.py:73-89`，F-2：`write_text_atomically`、`DictWriter`、UTF-8 無 BOM、`\r\n`）是唯一會重寫使用者字典的 writer。`manager.py`：`ensure_default_dictionary` 與 `create_dictionary` 對新檔寫 header；`import_dictionary`、`export_dictionary` 是 `shutil.copyfile`；`rename_dictionary` 是 `Path.rename`；`delete_dictionary` 是 `unlink`。它們都不解析列，所以都不會丟列。沒有「複製字典」的動作。

### Model（`dictionaries/entry_list_model.py`，P2-2）

`DictionaryEntryListModel` 持有 `_entries`（依檔案順序的完整清單）、篩選文字與 `_visible`。`add` 附加到尾端；`replace` 以 identity 替換；`remove` 移除第一個**相等**的項目（`list.remove`）；`source_text_exists` 在完整清單上精確比較 `text`（被篩選隱藏的列也算）。`save` 把 `_entries` 交給 `save_dictionary_entries`。對話框（`dialog.py:330-497`）只使用 model 的公開介面。

### 釘住缺陷的測試

- `tests/test_dictionary_entries_dialog.py:1312` `test_unchanged_dictionary_is_rewritten_in_normalized_form`（`# KNOWN BUG (P2-2 spec, Q2)`）：輸入 `" Alpha ,  ⠁ ,General"`、`",⠃,General"`、`"Zhuyin,invalid,Bopomofo"`、`"Beta,⠃,Custom"`（LF）；確定後只寫出 `Alpha,⠁,General` 與 `Beta,⠃,General`。
- golden trace（`DictionaryEntriesTraceTest`）：`TRACE_CSV` 含空白來源文字列 `,⠃,General` 與不合法注音列 `zz,ab,Bopomofo`；40 個錄製序列都以確定結束，存下的 CSV 都沒有這兩列。
- `test_load_filters_empty_and_invalid_bopomofo_rows`（`test_dictionary_entries.py`）、`test_loads_only_rows_accepted_by_the_editor`（`test_dictionary_entries_dialog.py:513`）與 `test_refresh_sets_virtual_count_and_valid_entry_counts`（`test_dictionary_management_dialog.py:105`）釘住 `load_dictionary_entries` 的回傳與字典管理的筆數。它們維持成立（D6）。

## 決策

**D1. 範圍：今天 R1 略過的每一列，不只不合法的注音列。** R1 在同一個迴圈裡有兩個略過分支：空白來源文字與不合法注音。兩者機制相同（loader 中 `continue`，再由確定寫出清單），損失也相同（使用者寫的、R3 可能用到的一列，在沒有修改的確定後消失）。只修一個，同類 bug 就留在隔壁分支；golden trace 與 Q2 測試也各含一列。兩種列由同一段程式保留（D2）。不在範圍內：完全空白的行（沒有資料；R3 也忽略），以及「現況」列出的變形（strip、類型正規化、丟掉多餘欄位與超出 header 的欄位、header、BOM、換行、引號）。它們改變一列而不是刪除它；要修它們就得不重寫沒變的列，這會改變 F-2 已驗證的輸出（項目 23、24 預期確定後為 CRLF、無 BOM）。它們留在 Q2 之下（後續工作）。

**D2. 儲存層：`dictionaries/entries.py` 的 `PreservedDictionaryRow` 與 `load_dictionary_rows`。**

```python
@dataclass(frozen=True)
class PreservedDictionaryRow:
	text: str
	braille: str
	entry_type: str

DictionaryRow = DictionaryEntry | PreservedDictionaryRow

def load_dictionary_rows(dictionary_path: Path) -> list[DictionaryRow]: ...
def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]: ...  # 結果不變
def save_dictionary_entries(dictionary_path: Path, rows: Iterable[DictionaryRow]) -> None: ...
```

`load_dictionary_rows` 就是今天的迴圈，把兩個 `continue` 分支改成 `rows.append(PreservedDictionaryRow(row.get("text") or "", row.get("braille") or "", row.get("type") or ""))`；分類規則與今天完全相同（strip 後的 text 為空，或正規化類型為 `Bopomofo` 且 strip 後的點字欄無法通過 `normalize_zhuyin_sequence`），移到私有的 `_is_editable(entry)`。它**不是** `validate_dictionary_entry`：那會連今天編輯器有顯示的不合法 `Braille` 列也藏起來。`load_dictionary_entries` 改為 `[row for row in load_dictionary_rows(path) if isinstance(row, DictionaryEntry)]`，因此它的結果、字典管理的筆數與三個釘住它的測試都不變。`save_dictionary_entries` 保留名稱、F-2 的內容與項目寫出的位元組；兩種列都接受，每列寫出 `row.text`、`row.braille`、`row.entry_type`（兩個類別都有這些屬性）。用獨立的類別（而不是在 `DictionaryEntry` 上加旗標），因為保留列永遠不能被顯示、編輯、篩選命中或移除；另一個類別的 frozen dataclass 永遠不等於 `DictionaryEntry`（dataclass 的 `__eq__` 要求同一類別），所以 model 的 `list.remove` 與以相等性決定的選取永遠不會選到它。

**D3. 位元組層級的保留：欄位精確，由同一個 `DictWriter` 重新序列化。** 保留列保存 `csv.DictReader` 回傳的三個欄位值原樣（缺的欄位變成 `""`），由寫項目的同一個 writer 寫出。結果：DotExpress 寫的列（或任何以 UTF-8、`\r\n`、依 header 順序三欄、最小引號寫出的列）會逐位元組相同地寫回；其他列對每個 reader 都得到相同的欄位值（R1 與 R3 都用 `row.get(...) or ""`），只有下列正規化，而這些今天本來就套用在檔案的每一列：無 BOM、`\r\n` 換行、最小引號、缺少的尾端欄位寫成空欄位（`,⠃` 變成 `,⠃,`）、多餘欄位與超出 header 的欄位被丟掉、header 為 `text,braille,type` 且依此順序。不採用「保留原始行」：`csv` 不提供一筆記錄的原始文字（帶引號的欄位可以跨行，用 `line_num` 推算很脆弱），header 與其他列本來就會重新序列化（一列 LF 夾在 CRLF 列之間會造成換行混雜），而且所有使用者比較的都是欄位，不是位元組。不需要改 `shared/atomic_write.py`：文字 helper 的簽名與行為就是 F-2 交付、F-3 保留的樣子。

**D4. 位置：保留列留在原位置。** model 持有一個包含檔案所有列、依序排列的清單（`_rows: list[DictionaryRow]`）；可編輯的項目與可見清單都由它推導。每個操作對項目維持 P2-2 的語意，並讓保留列留在原處：`add` 附加到檔案尾端（在尾端的保留列之後）、`replace` 原地替換（identity）、`remove` 刪除第一個相等的項目（永遠不會是保留列，D2）。因此保留列保有它的鄰居（使用者刪掉的除外），沒有修改的確定會精確重現檔案的列順序。理由：(1) 轉換保留來源相同的第一條規則，把保留列移到尾端，會讓沒有修改的確定改變重複來源由哪一條規則勝出；(2) 使用者在別處（Excel、文字編輯器）維護的檔案保有原本的排列，確定前後的檔案 diff 只顯示真正的編輯；(3) 不需要維護錨點：單一清單讓位置保留成為結構上的性質，而不是記帳，比「附加到尾端」再重新錨定更不脆弱。附加到尾端因 (1) 被否決。

**D5. 重複檢查：保留列的來源文字也算。** `source_text_exists` 在所有列（含保留列）上精確比較 `text`（原始、未 strip 的文字，也就是 R3 用作規則來源的值）。新增或編輯成某個隱藏列已有的來源文字時，以既有的 `Source text "{identifier}" already exists.`（`來源文字「{identifier}」已存在。`）拒絕，與今天對被篩選隱藏的項目完全一樣。理由：R3 保留重複來源的第一條規則。如果編輯器接受一個合法序列的 `肚子`，而一個不合法的 `肚子` 列仍在檔案較前面，新項目會附加在它之後，默默永遠用不到，與使用者的意圖相反；F-4 之前舊列會在確定時被刪掉，新列才會生效。拒絕能告訴使用者有東西擋著；處理方式（在 app 外修正或刪除 CSV 中的那一列）與方案 A 對任何隱藏列的處理方式相同。空白來源文字的列永遠不會撞到（項目對話框會 strip 並要求來源文字）。副作用，與 P2-2 Q4 相同：檔案中若已有來源文字相同的一個合法列與一個不合法列，合法的那一列在不改文字的情況下無法編輯。其他做法見 Q1。

**D6. 字典管理只計算編輯器顯示的項目（不變）。** `_load_dictionary_counts` 繼續呼叫 `load_dictionary_entries`。`dict_badbopo.csv` 仍顯示 `1`。計算所有列會顯示一個編輯器對不上的數字，而「1＋2 筆隱藏」的顯示需要新字串（Q2）。由新測試釘住（P1）。

**D7. 轉換不變。** `client/conversion/` 底下不改。不合法的注音列繼續經由 R3 的 fallback 使用，空白來源文字的列繼續被它略過；只有空白的 text 繼續是規則。轉換的改變是間接且預期的：確定不再刪掉這些列，所以轉換結果不再因為使用者按了確定而改變。讓轉換忽略不合法的列會改變既有字典的轉換結果（Q3，不建議）。

**D8. 匯入、匯出、改名、刪除、新增：範圍外，沒有要修的。** 它們複製、改名、刪除或建立檔案，不解析列，所以逐位元組保留每一列（以及 BOM）。它們「失敗時留下部分新檔」的問題是 F-2 D6 的後續工作，與列無關。

**D9. 沒有新的使用者可見字串，不改 `dialog.py`。** 對話框本來就只跟 model 溝通；model 的公開介面維持原意（`entries`、`visible_entries`、`visible_count`、`cell_text`、`add`、`replace`、`remove`、`apply_filter`、`save`、`load`）。「有 2 列無法顯示，已保留」之類的提示需要新 msgid 與 `.po`／`.mo` 更新；對修正資料遺失不是必要的（Q2）。

## 各路徑的行為（之前／之後）

| 路徑 | 之前 | 之後 |
| --- | --- | --- |
| 開啟字典編輯器 | 空白文字或不合法注音的列被默默略過 | 顯示相同的列；略過的列以隱藏方式依檔案順序保存在 model 中 |
| 篩選 | 在顯示的列上 | 不變；保留列永遠不會命中（它們不顯示） |
| 新增 | 重複檢查涵蓋所有顯示的列（含被篩選隱藏的）；附加到尾端 | 重複檢查也涵蓋保留列的文字（既有訊息）；附加到檔案尾端，在尾端的保留列之後 |
| 編輯 | 以 identity 替換；同樣的重複規則 | 相同；保留列留在原處 |
| 刪除 | 移除第一個相等的項目 | 不變；保留列永遠不會被移除 |
| 確定 | 只寫出顯示的列：保留列從檔案被刪掉（F-W11） | 依檔案順序寫出所有列；保留列欄位精確（D3）；同樣的原子寫入、同樣的錯誤訊息；顯示的列仍有 Q2 的正規化 |
| 取消 | 不寫檔 | 不變 |
| 字典管理筆數 | 只算顯示的列 | 不變（D6） |
| 匯入／匯出／改名／刪除／新增 | 位元組複製、改名、刪除、只有 header 的新檔 | 不變 |
| 轉換（R3） | 使用不合法注音列（fallback）與只有空白的來源；任何確定之後結果都會改變 | 程式不變；沒有修改的確定之後結果不再改變 |

`dict_badbopo.csv`（`text,braille,type`／`臺北,⠞⠺,Braille`／`肚子,ㄉㄨˋ|ㄗ˙,Bopomofo`／`數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo`，CRLF、無 BOM）：編輯器顯示一列；筆數 `1`；確定後檔案逐位元組不變（之前：剩 2 行）；刪除 `臺北` 再按確定，留下 header 與兩個注音列；新增 `肚子` 顯示 `來源文字「肚子」已存在。`。

## 各檔案的設計

### `client/dictionaries/entries.py`（tab 縮排）

- `from collections.abc import Iterable`。
- `PreservedDictionaryRow`（frozen dataclass，D2），docstring：編輯器不顯示的列（來源文字空白，或注音序列無法解析的 Bopomofo 列）；依讀入原樣保存，並在檔案中的原位置原樣寫回。`DictionaryRow = DictionaryEntry | PreservedDictionaryRow`。
- `load_dictionary_rows(path)`（D2）：檔案不存在回傳 `[]`；相同的 `open(..., newline="", encoding="utf-8-sig")`、相同的 `DictReader`；錯誤照今天的方式往外拋（P2-2 Q8 不變）。
- `_is_editable(entry)`：空白文字為 `False`；類型為 `Bopomofo` 時，`normalize_zhuyin_sequence(entry.braille)` 拋出任何 `Exception` 即為 `False`（今天的 `except Exception`）。它透過模組全域名稱呼叫 `normalize_zhuyin_sequence`，所以 `test_loads_only_rows_accepted_by_the_editor` 的 `patch("dictionaries.entries.normalize_zhuyin_sequence", ...)` 仍然有效。
- `load_dictionary_entries(path)`：D2 的過濾，docstring「The rows the editor shows and Dictionary Management counts.」
- `save_dictionary_entries(path, rows: Iterable[DictionaryRow])`：除了迴圈變數，內容不變；docstring 不變（「Replace the file atomically; on an error it is unchanged.」）。

### `client/dictionaries/entry_list_model.py`（tab 縮排）

- 改為 import `DictionaryRow` 與 `load_dictionary_rows`，不再 import `load_dictionary_entries`。
- `__init__(self, rows: Iterable[DictionaryRow] = ())`：`self._rows = list(rows)`；`_entries` 變成私有 property `[row for row in self._rows if isinstance(row, DictionaryEntry)]`（字典不大；篩選本來就每次按鍵重建一個清單）。
- 新 property `rows -> tuple[DictionaryRow, ...]`（依檔案順序的每一列；給測試用）。`entries`、`visible_entries` 維持原意（只有可編輯的項目）。
- `load` 呼叫 `load_dictionary_rows`；`save` 傳 `self._rows`，docstring「Write every row (preserved rows unchanged, in place); errors propagate.」
- `source_text_exists`：在 `self._rows` 上（D5）。`add`：`self._rows.append`。`replace`：在 `self._rows` 中以 identity 搜尋。`remove`：`self._rows.remove(current_entry)`。
- 模組 docstring：model 擁有依檔案順序的每一列；不是 `DictionaryEntry` 的列永遠不會被顯示、篩選、編輯或移除，並留在原處；重複規則涵蓋它們。
- `ImportGuardTest` 的 import 集合不變。

### 不變

`client/dialog.py`、`client/gui.py`、`client/shared/atomic_write.py`、`client/dictionaries/manager.py`、`client/dictionaries/presenter.py`、`client/conversion/`、`client/locales/`、`client/tests/fixtures/`。

## 維持不變的部分

- 編輯器顯示的列、它們的順序、篩選、選取規則、每一個 wx 呼叫（golden trace 40 個序列的 1,040 筆逐動作觀察照舊重播；見測試計畫 G）。
- 沒有保留列的字典按確定寫出的位元組（dict23：項目 23 的 sha256 `ef319c21…`）。
- `load_dictionary_entries` 的結果；字典管理的筆數。
- 每個字典檔的轉換規則，以及轉換 golden `translation_golden.json`。
- 匯入／匯出／改名／刪除／新增；F-2 的原子寫入與訊息。
- msgid 353，集合相同；`client/locales` 不變。
- Fixture：`dictionary_entries_trace.json` 與 `translation_golden.json` 逐位元組相同（sha256 見上）。

## 測試計畫

新測試依各檔案的縮排（`test_dictionary_entries.py`、`test_dictionary_entry_list_model.py`、`test_dictionary_management_dialog.py` 用 tab；`test_dictionary_entries_dialog.py` 用 4 個空白）。全部使用暫存資料夾；不碰 `client/dictionary/`。測試資料寫在測試內（`dict_badbopo.csv` 的位元組由測試寫出，不從 history 資料夾讀）。行為測試已在 `$SP/f4spec/` 對今天的程式與原型實作跑過（見「數量」）。

測試標號：P（釘住）、S（儲存）、M（model）、E（編輯器）、G（golden trace）；`D1`-`D9` 仍指決策。

### P. 釘住（`test_dictionary_management_dialog.py`，`DictionaryManagementVirtualListTest`）

- P1 `test_rows_the_editor_does_not_show_are_not_counted`：`dict_badbopo.csv` 的位元組；筆數欄顯示 `"1"`。修正前後都是綠燈（D6）。

### S. 儲存（`test_dictionary_entries.py`，`DictionaryEntryStorageTest`）

全部的紅燈：`ImportError: cannot import name 'PreservedDictionaryRow' from 'dictionaries.entries'`（模組載入失敗，一個 error）。

1. S1 `test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order`：含 `Alpha,⠁,General`、`,⠃,General`、`  ,⠃,General`、`肚子, ㄉㄨˋ|ㄗ˙ ,Bopomofo`、`媽,ㄇㄚ ,Bopomofo`、`,⠃`（兩欄）、`"q,""x""","a<CRLF>b",Bopomofo`、`Beta,⠃,General` 的檔案，得到 `[DictionaryEntry(Alpha), Preserved("", "⠃", "General"), Preserved("  ", "⠃", "General"), Preserved("肚子", " ㄉㄨˋ|ㄗ˙ ", "Bopomofo"), Preserved("媽", "ㄇㄚ ", "Bopomofo"), Preserved("", "⠃", ""), Preserved('q,"x"', "a\r\nb", "Bopomofo"), DictionaryEntry(Beta)]`。
2. S2 `test_save_writes_preserved_rows_unchanged_at_their_place`：寫出該清單，得到與 S1 檔案相同的位元組，只有 `,⠃` 寫成 `,⠃,`。
3. S3 `test_round_trip_of_a_file_with_invalid_bopomofo_rows_is_byte_identical`：`dict_badbopo.csv` 的位元組，`save_dictionary_entries(path, load_dictionary_rows(path))`，位元組相同（F-W11 在儲存層的回歸測試）。
4. S4 `test_round_trip_normalizes_only_the_bom_line_ends_and_quoting`：`BOM + text,braille,type\n"肚子","ㄉ",Bopomofo\n` 寫回成 `text,braille,type\r\n肚子,ㄉ,Bopomofo\r\n`（不合法的單一符號序列、帶引號、LF、BOM）。
5. S5 `test_round_trip_keeps_the_conversion_rules`：S1 的檔案；round trip 前後的 `LoadedDictionaryRules.from_paths(path, client/data/Bopomofo2Braille.csv, processing=normalize_zhuyin_sequence)` 相等，且含 `肚子` 的規則（原型：今天的確定把 6 條規則變成 2 條）。
6. S6 `test_a_preserved_row_is_never_equal_to_an_entry`：`PreservedDictionaryRow("a", "b", "General") != DictionaryEntry("a", "b", "General")`，且 `[entry].count(preserved) == 0`（守住 model 的 `list.remove`，D2）。

`test_load_filters_empty_and_invalid_bopomofo_rows`、`test_save_load_roundtrip`、BOM 與失敗的測試都不變。

### M. Model（`test_dictionary_entry_list_model.py`，新類別 `PreservedRowsTest`；以及 `LoadSaveTest`）

紅燈：`AttributeError: 'DictionaryEntryListModel' object has no attribute 'rows'`，或保留列出現在 `entries`／`visible_entries`，或沒有 `DuplicateEntryError`。

1. M1 `test_preserved_rows_are_not_entries_and_never_visible`：model `[alpha, kept, beta]`（`kept = Preserved("肚子", "ㄉㄨˋ|ㄗ˙", "Bopomofo")`）：`entries == visible_entries == (alpha, beta)`；篩選 `"ㄉ"` 與 `"肚"` 得到 `()`；`rows == (alpha, kept, beta)`。
2. M2 `test_remove_and_add_leave_preserved_rows_in_place`：`remove(0)`、`add(gamma)`：`rows == (kept, beta, gamma)`。
3. M3 `test_replace_leaves_preserved_rows_in_place`：`replace(0, delta)`：`rows == (delta, kept, beta)`。
4. M4 `test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate`：`add(DictionaryEntry("肚子", "ㄉㄨˋㄗ˙", "Bopomofo"))` 與 `replace(1, <同上>)` 拋出 `DuplicateEntryError("肚子")`；`rows` 不變。
5. M5 `LoadSaveTest.test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place`：載入 S1 的檔案，存到新路徑：位元組同 S2。

### E. 編輯器（`test_dictionary_entries_dialog.py`）

- **翻轉** `test_unchanged_dictionary_is_rewritten_in_normalized_form` 為 `test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form`：相同輸入；預期 `HEADER + "Alpha,⠁,General\r\n,⠃,General\r\nZhuyin,invalid,Bopomofo\r\nBeta,⠃,General\r\n"`。`# KNOWN BUG (P2-2 spec, Q2)` 標記保留，註解縮小到剩下的部分（空白被 strip、未知類型改寫成 `General`；F-4 起略過的列會保留）。紅燈：舊的輸出。
- E1 `test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical`：`open_editor(data=<dict_badbopo 位元組>)`；`rows() == [["臺北", "⠞⠺", UNICODE_BRAILLE]]`；`press_ok()` 為 `True`；檔案位元組等於輸入（F-W11 在 GUI 邊界的回歸測試）。
- E2 `test_deleting_every_shown_row_keeps_the_hidden_rows`：選 0、刪除、`rows() == []`、確定：`HEADER + "肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n"`。
- E3 `test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message`：腳本 `("肚子", "ㄉㄨˋㄗ˙", "Bopomofo")`、新增：log 恰為 `[["AddSymbolDialog", None], ["MessageBox", _duplicate_message("肚子"), ERROR_TITLE, ERROR_FLAGS]]`；確定後檔案逐位元組不變。
- `test_loads_only_rows_accepted_by_the_editor` 不變。

### G. Golden trace（`DictionaryEntriesTraceTest`），fixture 不變

`TRACE_CSV` 含空白來源文字列 `,⠃,General` 與不合法注音列 `zz,ab,Bopomofo`。fixture 是在 P2-2 之前的編輯器上錄製的，那時確定會刪掉這兩列，所以每個序列最後的 `csv` 都沒有它們。F-4 之後重播只有最後一步在這一點上不同：原型結果是 40 個序列都只在 `ok` 這一步失敗，套用下面修改過的判準後 40 個全部通過，也就是說 1,040 筆逐動作觀察（log、列、選取、篩選）以及 `ok` 這一步的 log 與狀態都不變；錄製的動作從未新增 `zz` 或空白來源文字，所以 D5 不會出現在 trace 中。

fixture **不**重新產生（sha256 維持 `f493da52…6c2cf`；模組 docstring 規定不得為了讓修改通過而重新產生）。改為讓 `test_replay_matches_every_recorded_step` 只修改最後一步的判準：模組常數 `_TRACE_KEPT_ROWS = (",⠃,General", "zz,ab,Bopomofo")`（原始碼中與 `TRACE_CSV` 一樣用 `\u2803` 寫），附註解（錄於 F-4 之前，當時確定會丟掉它們）；比較前，重播把實際的 `csv` 以 `"\r\n"` 切開，斷言等於保留列的那些行恰好是依序的 `_TRACE_KEPT_ROWS`（各一次，空白文字列在前），移除它們後以 `"\r\n"` 接回其餘部分；接著每一步照今天一樣用 `assertEqual` 比較。以行為單位，而不是子字串：`ab,⠃,General` 以 `,⠃,General` 結尾（原型中子字串版本有 6 個 seed 失敗）。精確位置由 S 與 M 釘住，不靠 trace。`write_trace_fixture` 不改。紅燈：修正前，新的斷言在 40 個 seed 都失敗（保留列不見了）。

### 數量

新增：P 1、S 6、M 5、E 3，共 15；翻轉的測試一對一取代；trace 的修改不增加測試。預期 `Ran 1226`、`FAILED (errors=1, skipped=5)`（F-W6 的 error），前提是如「現況」複製了 runtime。原型（`$SP/f4spec/`）：把 S1-S4、M1-M4、E1-E3、一個 `load_dictionary_entries` 的特性測試與 trace 修改套到 worktree（之後還原），得到 `Ran 1223`，只有尚未翻轉的 Q2 測試與 F-W6 失敗；S5、S6 另外執行，綠燈；在今天的程式上，十二個行為測試都如上所述為紅燈。

## 遷移步驟（每步一個綠燈 commit，先紅後綠）

1. `test: pin that Dictionary Management counts only the rows the editor shows (F-4)`：P1（在今天的程式上就是綠燈）。1212 個測試。
2. `fix: keep the dictionary rows the editor does not show when saving (F-4)`：`entries.py` 的 D2／D3；測試 S1-S6（紅燈：一個 `ImportError`）。model 仍只載入項目，所以編輯器仍會丟列，Q2 測試仍通過。1218 個測試。
3. `fix: keep hidden dictionary rows in place through the entries editor (F-4)`：`entry_list_model.py` 的 D4／D5；測試 M1-M5、E1-E3、Q2 翻轉、trace 判準修改（紅燈：M 的 error／failure，E1-E3 與翻轉的測試在舊輸出上失敗，trace 40 個 subtest 失敗）。1226 個測試。

每個 commit 結尾加 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`；只 stage 明確列出的路徑。沒有 commit 碰 `client/locales/`、fixture、`client/dictionary/`、`client/braille/`、`dialog.py`、`gui.py`、`shared/atomic_write.py` 或 `conversion/`。

## 驗收標準

1. `cd client && $PY -m unittest discover -s tests`：`Ran 1226`、`FAILED (errors=1, skipped=5)`，唯一的 error 是 F-W6。
2. 聚焦：`$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_conversion_text_dictionary_rules tests.test_translation_golden -v` 通過。
3. Fixture sha256 不變（`git diff <merge-base> -- client/tests/fixtures` 為空）。
4. msgid 掃描：`353 sha256 24dbc629…5277c`；`git diff <merge-base> -- client/locales` 為空。
5. `git diff <merge-base> --stat -- client` 只列出 `dictionaries/entries.py`、`dictionaries/entry_list_model.py` 與四個測試檔。
6. `grep -rn "KNOWN BUG (P2-2 spec, Q2)" client/tests` 仍找到翻轉後的測試（註解已縮小）。
7. Mutation 檢查（plan）：每個 mutant 都被抓到：保留列欄位被 strip；保留列類型被正規化（`""` 寫成 `General`）；保留列寫到尾端；空白文字列顯示為項目；不合法注音列被顯示；保留列沒寫出；重複檢查只涵蓋項目；`load_dictionary_entries` 回傳所有列（P1）；`PreservedDictionaryRow` 改成 `DictionaryEntry` 的子類別或與它相等；`remove` 以相等性在所有列上比對而命中保留列；trace 判準以子字串而非整行移除。
8. App 資料：main checkout 的 `client/dictionary/` 未被碰觸（測試從不使用）。

## Windows 驗證（packaged build）

依 `docs/superpowers/history/2026-10-09-03-windows-verification/test.md` 第 0.1 節在本 worktree 建置（runtime 與 MathCAT 如「現況」複製），得到 `D:\dxtest\N-f4\DotExpress.exe`。不修改 2026-10-09-03 的腳本：F-4 history 資料夾（`docs/superpowers/history/2026-10-09-NN-f4-keep-invalid-bopomofo-rows/auto/`，`NN` 為下一個可用編號；若 F-3 的 `05` 先合併則為 `06`）中的 `rerun.py` 在記憶體中把 `D:\dxtest\N\DotExpress.exe` 換成 F-4 的 exe、把每個工作資料夾 `D:\dxtest\auto<N>` 換成 `D:\dxtest\auto<N>-f4`（項目 25 與 29 附掛在項目 24 的資料夾上，所以都用 `auto24-f4`）後執行；項目 25 只執行到 `# 29 ACL deny write` 之前（那一段用 `(W)`，已由 `item29.py` 取代，F-W13）。`auto/data/` 的資料檔複製到 `D:\dxtest\data\`。另建 venv 安裝 `pywinauto`、`psutil`。

| # | 腳本 | F-4 之後的預期 | 之前（N，2026-10-09-03） |
| --- | --- | --- | --- |
| 23 | `item23.py`（B 與 N-f4） | `dict23`：B 與 N-f4 相同，sha256 `ef319c21…`，CRLF、無 BOM。`dict_badbopo`：N-f4 `changed: False`，4 行→4 行，sha256 `c4324573…`；B 4→2（F-W11 基線）；兩邊字典管理都顯示 `dict_badbopo` `1` | N 與 B 的 `dict_badbopo` 都是 4→2 |
| 24 | `item24.py` | 不變：筆數、列、確定後無 BOM、轉換有使用該字典 | 相同 |
| 25-28 | `item25.py` 到項目 28 | 不變（F-2 的寫入路徑沒動）：25 `[WinError 5]`、檔案不變、無 `.tmp`；26 `[Errno 13]`；27 被取代、隱藏屬性消失；28 10 次 0 失敗 | 相同 |
| 29 | `item29.py` | 不變：被取代、deny ACE 消失；已還原 | 相同 |
| 35（新） | `item35.py`，全新的 `D:\dxtest\auto35-f4` | 匯入 `dict_badbopo`；字典管理筆數 `1`；在設定中選它，轉換 `肚子數學`（輸出 O1）；編輯器顯示一列；確定：位元組＝來源（sha256 `c4324573…`），無 `.tmp`；再轉換一次：輸出＝O1；編輯器：刪除 `臺北`、確定：`text,braille,type\r\n肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n`，筆數 `0`；重新啟動：編輯器是空的，檔案不變。可選（腳本無法操作項目對話框時改為人工）：新增 `肚子`／`ㄉㄨˋㄗ˙`／注音，顯示 `來源文字「肚子」已存在。`，檔案不變 | B：第一次確定後剩 2 行，第二次轉換輸出與 O1 不同 |

項目編號 30-34 屬於 F-3；若 F-3 的編號改變，35 跟著改。項目 35 可以在 B 上執行，填「之前」欄。

## 與 F-3 的互動（`fix/f3-dep-atomic-write` 進行中）

F-3 修改 `client/shared/atomic_write.py`（共用核心、`write_bytes_atomically`、`ensure_writable`）、`client/documents/workspace.py`、`client/documents/workspace_service.py`、`client/gui.py`（Save／Add／Rename handler、匯入迴圈），以及 `test_atomic_write.py`、`test_document_workspace.py`、`test_workspace_service.py`、`test_gui_document_flows.py`、`case_insensitive_package_files.py`、`windows_file_handles.py`。F-4 不改這些檔案（D3：`write_text_atomically` 照原樣使用；F-3 保留它的簽名、行為與 15 個測試），所以預期 `client/` 中不會有文字層級的合併衝突。語意上的相依只有 `write_text_atomically(path, write, encoding="utf-8", newline="")`，F-3 不改它。可能的衝突僅限文件：history 資料夾編號與 Windows 驗證項目編號（F-3 用 30-34；F-4 用 35），以及兩個任務都可能更新的 `test.md`／審查記錄。兩者都合併後預期 `Ran 1263`（1211＋F-3 的 37＋F-4 的 15）、`FAILED (errors=1, skipped=7)`；第二次合併後執行字典測試與 `tests.test_atomic_write`。

## 風險

- **使用者看不到隱藏列**（中，方案 A 已接受）。編輯器不提示檔案有保留列；筆數也不含它們。使用者在 app 外修正（Q2）。
- **因看不見的列而拒絕重複**（低到中，D5）。訊息有指出來源文字，但清單中沒有該列；使用者必須編輯 CSV。F-4 之前同樣的新增會成功，並在確定時默默刪掉舊列。
- **欄位精確而非位元組精確**（低，D3）。以 LF、多餘引號、缺欄或多欄寫成的保留列會被正規化，就像檔案中其他列在確定時本來就會的那樣。
- **在 golden trace 底下修改 model**（低）。`_entries` 改為推導；trace 與 60 多個編輯器測試釘住每個可觀察行為；trace 判準的修改只限最後一步的兩個指定行。
- **效能**（極低）。每次篩選或編輯對檔案的列做一次 list comprehension。

## 給使用者的開放問題

**Q1. 新增的項目與某個隱藏列的來源文字相同。** **建議：以既有的重複訊息拒絕（D5）。** 其他做法：(a) 接受並附加；隱藏列仍在檔案較前面，轉換繼續使用它，所以新項目沒有作用；(b) 讓新項目原地取代隱藏列，這等於讓編輯器間接刪除隱藏列（與方案 A 的「不能刪除」矛盾），也需要規則決定取代哪一個隱藏列。

**Q2. 告知使用者有隱藏列**（例如在編輯器顯示「有 2 列無法顯示，已原樣保留」，或在字典管理顯示 `1 (+2)`）。**建議：不在 F-4 做**；需要新 msgid 與 `.po`／`.mo` 更新，而且對停止資料遺失不是必要的。列為後續 UX 任務。

**Q3. 轉換繼續使用不合法的注音列**（經由 R3 的 fallback，D7）。brief 預期轉譯會忽略它們；實際上今天不會，F-4 之後也不會。**建議：F-4 不改轉換**；忽略它們會改變既有字典的轉換結果，若要做，應與 P1-6 defect 2（被吞掉的 `processing` 例外）一起處理。

## 範圍外／後續工作

- P2-2 Q2 的其餘部分：沒有修改的確定仍會重寫字典，strip 顯示列的 text 與 braille（可能改變 R3 比對的來源）、把未知類型改寫成 `General`、丟掉多餘欄位、超出 header 的欄位、BOM 與空白行，並正規化換行與引號。修法：只在清單有變更時寫檔，或連顯示的列也保留原始欄位。
- 上面 Q1 與 Q2 的 UX；P2-2 Q4-Q6、Q8；F-W12（字典讀不到時字典管理靜默失敗）。
- `manager.py` 的 writer 改走原子 helper（F-2 D6）。
- 為轉換驗證字典列（Q3、P1-6 defect 2）。
