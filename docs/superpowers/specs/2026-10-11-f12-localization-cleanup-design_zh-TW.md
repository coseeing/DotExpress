# 本地化收尾與訊息後續項目（F-12）設計

## 目標

F-12 是 `task.md` 排序中的第 5 項（「F-12 本地化收尾」）。它把使用者仍會看到的英文訊息與原始 Python 錯誤，改成在地化、看得懂也知道怎麼處理的文字，並補上先前 review 發現缺少的幾則訊息。

使用者的決定（2026-10-11，`task.md` 第三節「F-12 範圍」），本文不再重問：

- **U1. 範圍只限文字訊息。** 納入：
  1. 尚未在地化、使用者看得到的英文訊息（P1-4 defect 4，例如 Export All 的摘要）；
  2. 轉換時讀不到所選字典，顯示友善訊息而非原始 Python 錯誤（F-6 O5）；
  3. 文件名稱被工作區資料夾中、不在文件清單裡的 `.dep`（或其他項目）占用時，顯示專門的訊息（F-8a review，表格 D1）；
  4. 設定無法寫入 `config.json` 時給出提示（F-8a review M-7）。
- **U2. F-9 review M-9 納入。** 轉換失敗、而該工作的文件不是目前開啟的文件時，失敗訊息要指出是哪份文件（D7）。
- **U3. 不納入**（列在「範圍外／後續項目」，本文不設計）：啟動提示框與 NVDA（F-8b review M-8）、`WM_ENDSESSION` 結束碼（F-9 review M-8）、匯出 `.tmp` 自動重試、字典表頭不分大小寫、Delete All 回復（P1-3 defect 4）、F-W5。

完成後：

- Export All 摘要、轉換的備用訊息、匯入問題的原因、HTML 存檔類型、匯出的「沒有轉換資料」頁面，以及幾則少見的錯誤訊息，都以繁體中文顯示。
- 轉換讀不到所選字典時，以一行文字說明是哪個字典、原因為何，原因沿用 F-6 的說明（表頭無法辨識另有新的原因字串）。
- 名稱被不在清單中的檔案占用時，訊息會說明這件事、指出是哪個檔案並顯示工作區資料夾；清單內的重複名稱仍顯示 `文件「X」已存在。`。
- 同一次執行中，第一次無法儲存的設定變更會跳出一個警告框；log 不變。
- 文件已不是開啟中的手動轉換失敗，以及非開啟中文件的單份匯出失敗，訊息會指出文件名稱。

新增的使用者可見字串：**23** 個 msgid，其中 4 個從 catalog 的廢棄項目恢復，沿用原本的翻譯（見「使用者可見字串」）。msgid 數從 **381**（F-11 之後的 main）變為 **404**。

非目標：

- 接在在地化前導文字之後的作業系統與第三方函式庫原文（`[Errno 13] ...`、pypdf、ebooklib、MathCAT；見「範圍外」）；
- 文字處理程式的 Python `SyntaxError` 原文（讀者是程式作者）；
- 除了顯示哪段文字之外的任何行為改變；唯一例外是 D6 新增的警告框；
- F-10（UEB 斷行、`$`）。

## 與 F-11 的關係

F-11（字典編輯器 UX，`D:\workspace\DotExpress-f11`，branch `fix/f11-dictionary-editor-ux`）會在 F-12 寫 plan 前 merge 進 `main`。本文以 `main` + F-11 為前提：

- catalog 有 381 個 msgid（F-11 新增 370–381，最後一個是 review 修正加的 `Dictionary "{name}" cannot be saved: its header is not recognized. ...`）。
- F-11 改動 `conversion/text/dictionary_rules.py`（`LoadedDictionaryRules.from_paths`：D13 略過隱藏列、D14 一聲空白）、`dictionaries/manager.py`、`dictionaries/presenter.py`、`dialog.py`、`ui/message_box.py` 與 `gui.on_open_dictionary_management`。F-12 的 D4 也會改 `from_paths`。程式碼以函式名稱指稱；下文行號取自 `main` `1ce6ce5`，僅供定位，plan 會在 F-11 之後的 `main` 上重新取得。
- D4 的表頭原因（字串 17）與 F-11 的字串 12 用詞相同，編輯器與轉換對無法辨識的表頭說法一致。
- F-12 沒有任何決定碰到編輯器、字典管理或 F-11 的確認框。F-11 的後續項目「既有是／否確認框的 Esc」不是文字訊息，依 U3 不納入（見「範圍外」）。
- F-11 的 GUI 項目到 108 為止（107 是手動 NVDA 項目）。F-12 的項目是 109–119。

## 現況（2026-10-11 在 `main` `1ce6ce5` 驗證，worktree `D:\workspace\DotExpress-f12`，`HEAD:client` `a64da653`）

`$PY` 是 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`。本文的探針在 session scratchpad（`...\scratchpad\f12spec\`：`scan.py`、`scan2.py`、`probe1.py`、`probe2.py`、一個 `msgmerge` 探針）以 worktree 的原始碼執行，不 commit。撰寫本文時沒有跑測試套件（機器忙碌中）；以下基線取自 F-9 與 F-11 的記錄：`1ce6ce5` 為 `Ran 1483`、`FAILED (errors=1, skipped=7)`（只有 F-W6）；F-11 branch 在 review 修正後為 `Ran 1564`、`OK (skipped=6)`。catalog 在 `1ce6ce5` 有 369 個 msgid，在 F-11 branch 有 381 個。

### 目前的在地化方式

- `_` 是內建 zh_TW catalog 的 `gettext`（`i18n.py`）；`N_` 只負責標記，讓 `xgettext` 擷取（`scripts\generate-pot.bat` 使用 `--keyword=_ --keyword=N_`）。
- 有幾處在顯示時以 `_(value)` 翻譯變數：`_(result.summary_template)` 與 `_(result.summary_title)`（`documents/export_coordinator.py:205-206`）、`_(get_public_error_message(error.error))`（`ui/conversion_presenter.py:124`）、文字處理 `ValueError` 的 `_(str(error))`（`settings/dialogs.py:158`）、`NameDialogMessages.message_for`（`ui/dialog_base.py:44-49`）、選單項目的 `_(label)`（`gui.py:260`）、設定對話框的 `_(option.label)`、`_(CSV_WILDCARD)`（`dialog.py:773`、`785`）。只有當該值是 msgid、也就是在定義處用 `N_` 標記過時，這種寫法才有效。**從未標記的值就一直是英文**，這正是 P1-4 defect 4 的根源。
- `gui.py:315` 的 `self.SetTitle(_(format_window_title(name)))` 把組好的標題（`"alpha - DotExpress"`）交給 `_`。這是誤用：它不是 msgid，所以原樣傳回；但若某份文件的標題剛好等於某個 msgid，就會被「翻譯」。

### 使用者可見英文文字清單（以 AST 掃描所有非測試模組中不在 `_()`／`N_()` 內的字串常數，再逐一追到顯示的位置）

| # | 目前的文字 | 定義處（`1ce6ce5`） | 使用者在哪裡看到 | 決定 |
| --- | --- | --- | --- | --- |
| E1 | `All documents were exported successfully.`、`Export Complete with Errors`、`Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}` | `documents/export_results.py:6-14`（一般常數） | Export All 摘要框（`export_coordinator.py:204-210`）；F-9 的 GUI 記錄顯示它是英文 | D1 |
| E2 | `An unknown error occurred.`、`The selected translation table could not translate this text.` | `conversion/plain_text.py:4-6` | 接在 `轉譯失敗：`／`文字處理失敗：` 之後 | D2 |
| E3 | `Document "{name}" already exists.`（f-string）、`Unsupported import file type: ".x".`、`Text document must use the .txt extension.`、`Source document must use the .x extension.`、`Document package must ...`（3 則）、`Encrypted PDF cannot be imported.`、`EPUB does not contain a readable spine.`、`EPUB spine item "x" is missing.`、`Name cannot exceed 32 characters.`／`Name contains invalid characters.`／…，以及原始的 `UnicodeDecodeError`、`OSError` 文字 | `documents/workspace.py:250-281`、`441`、`447`；`documents/importers/base.py:18`、`epub_importer.py:18`、`26`、`pdf_importer.py:270`、`284`；`shared/name_validation.py:71-82`；`workspace_service.py:241`（`str(exc)`） | 匯入問題對話框，每個被略過的檔案一行（`gui.py:583-590`、`940-946`） | D3 |
| E4 | `CSV must contain columns: text, braille, type`、`CSV must contain header row.`，以及原始的 `UnicodeDecodeError`／`PermissionError`／`csv.Error` | `conversion/text/dictionary_rules.py:156-174` 與 `from_paths` 中的開檔、讀取 | 轉換、單份匯出或 Export All 摘要中的 `轉譯失敗：...`（F-6 O5） | D4 |
| E5 | `HTML files (*.html)|*.html` | `documents/formats.py:189`（W-3 刻意不標記，「以免新增 catalog 項目」） | HTML 匯出存檔對話框的檔案類型清單 | D8 |
| E6 | `No conversion data is available for this document.`（預設參數） | `dual_view/html.py:39`，由 `documents/formats.py:109` 使用 | 沒有轉換資料的文件所匯出的雙視檢視 HTML 檔（程式內的雙視檢視已傳入翻譯後的文字，`gui.py:327-330`） | D8 |
| E7 | `No supported browser or system HTML opener is available.` | `dual_view/browser.py:103` | `無法開啟雙視檢視：{error}` | D8 |
| E8 | `main is not callable.`、`main must return str, got {type}.` | `conversion/preprocessing/user_script.py:75`、`78` | `文字處理失敗：...`（實際最可能的是程式傳回 `None`）；旁邊兩則檢查訊息已經用 `N_` 標記 | D8 |

已檢查、維持原狀（使用者看不到，或從 UI 到不了）：

- log 訊息（`config.py`、`ui/conversion_presenter.py` 的丟棄原因、`dotexpress.*` logger），以及內部不變量的 `ValueError`／`TypeError` 文字（`dialog.py:608`、`entry_list_model.py:112`、`162`、`dual_view/model.py`、`markdown_ast.py`、`markdown_renderer.py`、`menu_builder.py:36`、`settings/dialogs.py:209`、`745`、`alignment.py`、`zhuyin.py:68`）。
- `conversion/text/pipeline.py:121` 的 `assert ..., "No translatable text segments were found."`：只有空的文字片段才會觸發，而 service 從不傳入（探針 4）。
- `dictionaries/manager.py:82`、`93`、`103`、`108`、`130` 與 `dictionaries/actions.py:39`：名稱提示會用在地化的 `字典「X」已存在。` 回報重複，預設字典在到達這些程式前就被擋下（`presenter.py:113-116`、`137-139`）。
- `documents/workspace_service.py:252`（改名成同名；`gui.py:844` 會先 return）、`shared/atomic_write.py:52`、`app_paths.py:29`（啟動錯誤框顯示自己的在地化文字與 `error.cause`）、`adapters/translation/provider.py`（只在 Windows 上的 runtime 訊息，寫進 log）。
- Tagged PDF 的 `ValueError`（`pdf_importer.py:80-262`）：在 `import_pdf` 內被接住，改走純文字（`:286-291`）。
- 標準按鈕：`message_box` 與 `localize_standard_buttons` 已設定翻譯後的標籤（F-7、F-W9）。

### 探針（scratchpad，`1ce6ce5`）

1. **匯入問題的原因**（以真實檔案呼叫 `batch_import_documents`，`format_key="all"`，清單中有 `alpha`）：

   ```text
   alpha.txt: Document "alpha" already exists.
   bad.docx:  File is not a zip file
   bad.epub:  'Bad Zip file'
   bad.pdf:   Stream has ended unexpectedly
   big5.txt:  'utf-8' codec can't decode byte 0xa4 in position 0: invalid start byte
   con.txt:   Name contains invalid characters.
   foo.xyz:   Unsupported import file type: ".xyz".
   xxxx...(40).txt: Name cannot exceed 32 characters.
   ```

   在台灣，Big5 的 `.txt` 很常見，所以原始的 `UnicodeDecodeError` 是其中最可能遇到的。
2. **轉換時字典讀不到**（`from_paths` 拋出的例外經 `format_conversion_error`）：

   ```text
   Big5 CSV:            轉譯失敗：'utf-8' codec can't decode byte 0xa4 in position 18: invalid start byte
   表頭 Text,Braille,Type: 轉譯失敗：CSV must contain columns: text, braille, type
   0 位元組的檔案:        轉譯失敗：CSV must contain header row.
   PermissionError:     轉譯失敗：[Errno 13] Permission denied: '...'
   ```

   Python 3.13 的 `csv` 遇到 NUL 位元組或未結束的引號不會拋例外；欄位超過 `csv.field_size_limit()` 才會拋 `csv.Error`。字典管理把沒有表頭的檔案視為可讀、0 筆（F-6），但轉換會失敗。
3. **`msgmerge` 會原樣恢復廢棄項目。** `.po` 中有 `#~ msgid "All documents were exported successfully."`，與再度含有這個 msgid 的模板合併後，得到有效的項目並保留原本的 msgstr，不是 fuzzy。catalog 仍以廢棄項目保存 E1（`.po:1697-1710`）與 `Imported file must be a valid DotExpress DEP package.` 的 zh_TW 翻譯。
4. **pipeline 的 assertion 到不了**：`translate_plain_text_segment("")` 會觸發，但 `parse_inline_math_segments` 從不產生空的文字片段，而空文字在轉譯前就 return。
5. **名稱檢查**（`gui.py:711-735`）：`document_name_exists(...) or package_name_taken(...)` 兩種情況都顯示同一則 `文件「{name}」已存在。`。`package_name_taken` 是 `os.path.lexists(<workspace>/<name>.dep)`（`workspace_service.py:123-132`）：啟動時保留的無效封裝檔、資料夾、斷掉的連結，或程式執行中被複製進來的有效封裝檔都算，在 NTFS 上不分大小寫。匯入時會把磁碟上所有 `*.dep` 的主檔名放進 `existing_names`（`workspace_service.py:223-228`），所以這種名稱會得到英文的 `Document "X" already exists.`。
6. **設定存不進去**（`config.py:162-185`）：存在但讀不到的 `config.json`（帶 `OSError` 的 `_UnreadableConfig`）永遠不會被寫入；損壞的檔案會先複製成 `config.json.bak`，複製失敗就什麼都不寫；任何寫入錯誤都寫進 log。三種情況下 `_save` 都傳回 `None`，setter 也傳回 `None`，只有 `config.log` 有一行記錄。主視窗把變更後的值留在記憶體（`translation_settings`、`translation_tables`、`view_settings`），所以在關閉程式前仍然有效。主視窗的存檔位置是 `apply_settings_from_dialog`（`gui.py:421-438`，三次存檔）、`_set_view_font_size`（`:592-600`，Ctrl+滾輪與設定對話框的字型大小）和 `_set_active_dictionary`（`:440-446`，透過 presenter 的字典管理改名與刪除）。`get_or_create_client_id` 與 `set_lang(persist=True)` 也會存檔；前者在 client-init 背景執行緒執行（`client_init.py:164-173`）。
7. **手動轉換失敗**（`ui/conversion_presenter.py:266-279`）：`message = format_conversion_error(...)`；手動工作一律 `show_error(message, "Error")`，不論目前開著哪份文件。工作知道自己的目標（`_ManualTarget.document_name`，F-9 D1）。單份匯出的 `on_error`（`export_coordinator.py:113`）也用同樣方式顯示。

## 決定

**D1. Export All 摘要在地化（E1）。**

- `documents/export_results.py` 用 `N_` 標記四個常數（`EXPORT_COMPLETE_TITLE` 已經透過 `export_coordinator.py:137` 是 msgid，標記它不會增加 msgid）。`_show_batch_result` 照舊在顯示時翻譯。
- 三則文字從廢棄項目恢復，沿用舊翻譯（探針 3）：字串 1–3。
- 摘要中的失敗行維持 `{文件}: {原因}`；原因是轉換訊息（D2、D4；D7 不適用於此）或原始的寫入錯誤。

**D2. 轉換的備用訊息成為 msgid（E2）。**

`conversion/plain_text.py` 以 `N_` 標記兩則文字。`format_conversion_error` 本來就會翻譯 `get_public_error_message` 的結果。字串 4、5。

**D3. 匯入問題的原因在地化（E3）。**

- 新增 `documents/import_problems.py`（不 import wx），內含 `describe_import_problem(error, format_key) -> str`，每一行匯入問題都用它產生：

  | 原因 | 顯示的說明 |
  | --- | --- |
  | `UnicodeDecodeError`（不是 UTF-8 的 `.txt`） | 字串 10 |
  | `PermissionError`（被鎖住、沒有權限） | 既有的 F-6 CANNOT_OPEN 文字 `無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。` |
  | `NameValidationError`（檔名不能當文件名稱） | 既有的文件名稱訊息：`too_long` 與 `empty` -> `文件名稱長度需為 1 到 32 個字元。`，`invalid` -> `文件名稱不是有效的 Windows 檔名。` |
  | `ImportProblem`（新增，由 DotExpress 自己的載入程式拋出） | 它的 msgid，翻譯後顯示（字串 11–15） |
  | 載入 `dep` 時的其他錯誤 | 字串 13（恢復的 `匯入的檔案必須是有效的 DotExpress DEP 封裝檔。`）：壞掉的 zip、缺成員、JSON 錯誤 |
  | 其他 | 既有的 `無法讀取檔案：{error}`，附原始文字（F-6 OTHER） |

- `ImportProblem(ValueError)`（在 `documents/importers/base.py`）帶一個以 `N_` 標記的 msgid；`str()` 仍是英文，log 與 `except ValueError` 不受影響。它取代以下幾處的一般 `ValueError`：不支援的檔案類型（`workspace.py:441`，字串 11）、副檔名不符（`load_text_document`、`validate_source`；字串 12）、三則封裝結構錯誤（`load_document_package`；字串 13）、加密的 PDF（兩處；字串 14），以及兩則 EPUB 錯誤（字串 15，兩者共用；spine item 的 id 對使用者沒有意義）。
- 清單內的重複名稱透過 `_()` 顯示既有的 `文件「{name}」已存在。`；只被磁碟上項目占用的名稱顯示字串 18（D5）。
- 寫入匯入的封裝檔失敗（`workspace_service.py:241`）時顯示既有的 `儲存文件失敗：{error}`。
- 每行維持 `{檔名}: {原因}` 的格式，所以字串 11、12 不需要自己帶檔名。
- 為什麼集中在一個函式、而不是到處 `_(str(exc))`：`UnicodeDecodeError`、`PermissionError` 與名稱錯誤本來就需要對應，集中在一處也能在沒有 wx 的情況下測試。

**D4. 轉換讀不到所選字典時說清楚（E4，F-6 O5）。**

- `LoadedDictionaryRules.from_paths` 在一個受保護的區塊中讀取**字典**檔（開檔、檢查表頭、讀完所有列），若因 `UnicodeDecodeError`、`OSError`、`csv.Error`，或表頭缺少 `text`、`braille`、`type`（含空檔案）而失敗，就拋出新的 `DictionaryRulesReadError(path, error)`。各列在區塊之後才處理，所以處理階段的錯誤（F-11 D13／D14、對齊）不會被說成「無法讀取」。內建的 `Bopomofo2Braille.csv` 不受保護：它失敗代表安裝損壞，訊息維持原狀。`dictionary_rules.py` 仍然不 import `dictionaries` 的任何東西。
- `format_conversion_error` 辨認 `error` 為 `DictionaryRulesReadError` 的 `ConversionStageError`，組成 `轉譯失敗：` + 字串 16 `Dictionary "{name}" cannot be read. {reason}`，`{name}` 是檔案主檔名，`{reason}` 為：
  - 表頭的情況：字串 17（與 F-11 字串 12 的用詞相同）；
  - 其他：`describe_dictionary_read_error(cause)`（F-6：NOT_UTF8、CANNOT_OPEN、INVALID_CSV、OTHER）。
- **一行，而不是 F-6 的兩段式**，因為同一段文字也會是 Export All 摘要的一行（`{文件}: {原因}`）。例如：`轉譯失敗：無法讀取字典「big5dict」。檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。`
- 適用於轉換、單份匯出與 Export All 的每一步，因為它們都經過 `format_conversion_error`。
- 不新增 log：訊息框已指出檔案與原因，而 F-9 D7 只記錄非預期的 worker 錯誤。Decided by orchestrator with the recommended default; user may override before merge（O3）。
- 不存在的字典照舊以空規則轉換。

**D5. 名稱被不在清單中的檔案占用時，有專門的訊息（F-8a review）。**

- `DocumentWorkspaceService.unlisted_package_entry(name) -> str | None` 傳回占用 `name` 的磁碟項目名稱（例如使用者輸入 `BAD` 時是 `bad.dep`），做法是列出工作區資料夾並以 `casefold` 比對；沒有項目占用時傳回 `None`。若 `package_name_taken` 為真但列表沒找到（競態），項目名稱用 `"{name}.dep"`。
- `_prompt_for_document_name`（新增與改名）：**先**檢查清單，清單中有就維持 `文件「{name}」已存在。`。只有清單中沒有、但磁碟上被占用時，訊息框（標題 `錯誤`，`wx.OK | wx.ICON_ERROR`）顯示字串 18、一個空行，再顯示附工作區資料夾路徑的字串 19。之後名稱對話框照舊重新出現並預填名稱。
- 匯入：`batch_import_documents` 分開取得清單外的項目與清單中的名稱；名稱只被清單外項目占用的文件，原因顯示字串 18（不加字串 19：匯入問題對話框是逐檔列出，路徑會在每一行重複）。
- `free_document_name`（預設文件）不變：照舊靜默改用 `new (2)`。
- 用詞不指明成因（最常見的是啟動時保留的無效封裝檔，但資料夾或複製進來的封裝檔也會占用名稱），並告訴使用者怎麼做。

**D6. 同一次執行中第一次無法儲存的設定變更，顯示警告（F-8a review M-7）。**

- `ConfigStore._save` 傳回 `ConfigSaveProblem | None`（frozen dataclass：`kind` 為 `UNREADABLE`、`BACKUP_FAILED`、`WRITE_FAILED` 之一；`error`；`path`；`BACKUP_FAILED` 另有 `backup_path`）。經 `_save` 存檔的公開 setter 把它傳回（目前傳回 `None`，不會影響任何呼叫端）。`save_translation_settings`、`save_translation_tables` 與 `save_view_settings` 傳回其 setter 的第一個問題。log、略過與備份的規則（F-8 D11）不變。
- `get_or_create_client_id` 與 `set_lang` 忽略傳回值：它們不是使用者改的設定，而前者在背景執行緒執行。
- 主視窗的三個存檔位置（`apply_settings_from_dialog`、`_set_view_font_size`、`_set_active_dictionary`）把結果交給 `_report_settings_save_problem(problem)`。同一次執行中第一個問題顯示一個訊息框，之後不再顯示（旗標放在主視窗上）。Decided by orchestrator with the recommended default; user may override before merge（Q1 詢問使用者）。
- 訊息框：`message_box`，標題字串 20 `設定未儲存`，`wx.OK | wx.ICON_WARNING`，內容為字串 21，`{path}` 是 `config.json` 的完整路徑，`{reason}`：
  - `UNREADABLE`：既有的 CANNOT_OPEN 文字；
  - `BACKUP_FAILED`：字串 22，附 `.bak` 路徑與錯誤；
  - `WRITE_FAILED`：原樣的錯誤文字。
- 父視窗：顯示當下程式中作用中的視窗（按「套用」後的設定對話框、改名後的字典管理），否則為主視窗。訊息框在存檔位置的最後、記憶體中的變更完成後同步顯示，所以變更仍然生效。
- 為什麼每次執行只顯示一次：Ctrl+滾輪每轉一格就存一次檔，每格都跳框會讓使用者無法操作。訊息會說明之後的變更也不會保留，而且下次啟動前不會再出現。

**D7. 轉換失敗、而文件不是開啟中的文件時，指出文件名稱（F-9 review M-9；U2）。**

- 手動轉換：在 `_on_job_failure` 中，若工作的目標是一份文件（`_ManualTarget.document_name` 不是 `None`），且與送達時的 `documents.open_document_name` 不同，訊息為字串 23 `Document "{name}" could not be converted.\n\n{error}`，`{error}` 是現在的訊息（`轉譯失敗：...` 或 `文字處理失敗：...`）。標題照舊為 `錯誤`。
- 單份匯出（檔案 > 匯出、Ctrl+S）：coordinator 的 `on_error` 套用同一規則，名稱是被匯出的文件，比對送達時開啟的文件。在開著另一份文件時匯出選取的文件，就足以讓名稱出現；這是刻意的，因為否則訊息框不會說是哪一次匯出失敗。
- 不變：工作的文件就是開啟中的文件（照現在的訊息）；開始時沒有文件（沒有名稱可給）；Export All（摘要本來就逐份列出）；缺少轉譯表的訊息（在轉換之前就顯示）。
- 訊息框之後的焦點不變（F-9 review M-6 只在成功的 case (b) 之後移動焦點）；見「範圍外」。

**D8. 其餘的英文訊息（E5–E8）。**

- `HTML files (*.html)|*.html` 以 `N_` 標記（字串 6，`HTML 檔 (*.html)|*.html`，比照 `點字檔 (*.brl)|*.brl`）。格式標籤 `HTML` 維持原樣（如同 `ASCII`、`Unicode`）。
- `documents/formats._write_html` 以 `_("No conversion data is available for this document.")`（既有 msgid）作為 `empty_message`，與程式內的雙視檢視一致。
- `dual_view/browser.py` 以翻譯後的字串 7 拋出 `OSError`。
- `user_script.execute_preprocessing_script`：`main is not callable.` 以 `_()` 拋出（字串 8）；`main must return str, got {type}.` 由翻譯後的字串 9 組成。兩者都在拋出時翻譯，因為第二則需要代入值；`format_conversion_error` 對已翻譯的文字再做 `_()` 會原樣傳回。

**D9. `_()` 的誤用。**

- `gui._update_window_title` 呼叫 `SetTitle(format_window_title(name))`，不再經過 `_()`。標題文字不變（`DotExpress` 與 `{name} - DotExpress` 原樣保留，`AGENTS.md`）。
- 「現況」列出的顯示時 `_(value)` 寫法保留：每一處翻譯的值都在定義處以 `N_` 標記（D1、D2 讓最後兩個這種值成為 msgid）。

Decided by orchestrator with the recommended default; user may override before merge（O7）。

**D10. 字串與 catalog。**

- 下表的 23 個字串。依序 `scripts\generate-pot.bat`、`msgmerge`、填 msgstr、`msgfmt --check --statistics`：全部已翻譯，0 fuzzy，0 未翻譯。`POT-Creation-Date` 維持 `2026-10-10 12:00+0800`。
- 字串 1、2、3、13 必須從廢棄項目恢復並保留舊 msgstr（探針 3）；plan 檢查每一個都是有效項目、不是 fuzzy，且 `#~` 的副本已消失。
- 檢查 `msgmerge` 沒有把新 msgid 模糊配對到舊的。可能的組合：16 與 `Dictionary "{name}" cannot be read.`、18 與 `Document "{name}" already exists.`、23 與 `Conversion completed. The result was saved to document "{name}".`、20 與 `Settings`、6 與 `Braille files (*.brl)|*.brl`、17 與 F-11 的字串 12。若有，填入下表的 msgstr，並移除 `#, fuzzy` 與舊 msgid 的註解行。

## 各路徑的前後對照

| 路徑 | 之前 | 之後 |
| --- | --- | --- |
| Export All 全部成功 | 標題 `匯出完成`，內容 `All documents were exported successfully.` | `所有文件皆已成功匯出。`（D1） |
| Export All 部分失敗 | 標題 `Export Complete with Errors`，英文的數量 | `匯出完成，但有錯誤`、`成功匯出的文件：N` …（D1） |
| 轉換錯誤訊息為空，或 liblouis 的 "Can't translate" | `轉譯失敗：An unknown error occurred.`／`...could not translate this text.` | `轉譯失敗：發生不明的錯誤。`／`轉譯失敗：選取的轉譯表無法轉譯這段文字。`（D2） |
| 匯入 Big5 的 `.txt` | `big5.txt: 'utf-8' codec can't decode ...` | `big5.txt: 檔案不是以 UTF-8 文字儲存。...`（D3） |
| 匯入清單中已有的名稱 | `alpha.txt: Document "alpha" already exists.` | `alpha.txt: 文件「alpha」已存在。`（D3） |
| 匯入被鎖住的檔案 | `[Errno 13] Permission denied: ...` | CANNOT_OPEN 文字（D3） |
| 匯入損壞的 `.dep` | `File is not a zip file`／`Document package names do not match.` | `匯入的檔案必須是有效的 DotExpress DEP 封裝檔。`（D3） |
| 以 Big5、被鎖住、沒有表頭或空的字典轉換 | `轉譯失敗：<Python 文字>` | `轉譯失敗：無法讀取字典「X」。<原因>`（D4） |
| 新增或改名成只被清單外項目占用的名稱 | `文件「BAD」已存在。` | 字串 18（指出 `bad.dep`）、字串 19（附工作區資料夾）（D5） |
| 匯入名稱只被清單外項目占用的檔案 | `Document "bad" already exists.` | 字串 18（D5） |
| 無法儲存的設定變更 | 沒有任何提示（只有 log） | 該次執行第一次：D6 警告；之後：沒有 |
| 切到另一份文件後，手動轉換失敗 | `轉譯失敗：...` | `無法轉換文件「alpha」。` + 空行 + `轉譯失敗：...`（D7） |
| 非開啟中的待轉換文件，單份匯出失敗 | `轉譯失敗：...` | 同上，指出名稱（D7） |
| HTML 匯出存檔對話框 | `HTML files (*.html)` | `HTML 檔 (*.html)`（D8） |
| 沒有轉換資料時匯出的 HTML | 英文句子 | `此文件沒有可顯示的轉換資料。`（D8） |
| 文字處理程式傳回 `None` | `文字處理失敗：main must return str, got NoneType.` | `文字處理失敗：main 必須傳回 str，而不是 NoneType。`（D8） |

## 各檔案的設計

### `client/documents/export_results.py`（4 個空白）

四個常數加上 `N_`（D1）。從 `i18n` import `N_`。

### `client/conversion/plain_text.py`（4 個空白）

兩則對外文字加上 `N_`（D2）。

### `client/documents/importers/base.py`、`epub_importer.py`、`pdf_importer.py`（4 個空白）

`base.py` 新增 `ImportProblem(ValueError)`；`validate_source`、EPUB 與加密 PDF 的 raise 改用它（D3）。

### `client/documents/workspace.py`（4 個空白）

`load_text_document`、`load_document_package` 與不支援類型的 raise 改用 `ImportProblem`；`batch_import_documents` 分開接收清單外的項目，並以 `describe_import_problem` 產生每一則原因（D3、D5）。`load_workspace_documents` 仍把所有 `ValueError` 視為無效封裝檔（`ImportProblem` 也是）。

### `client/documents/import_problems.py`（新檔，4 個空白）

`describe_import_problem(error, format_key) -> str`（D3）。從 `i18n` import `_`。它直接寫出 CANNOT_OPEN 的 msgid，而不是 import `dictionaries.read_problems`（documents 不依賴 dictionaries）；`xgettext` 會把它列為同一個 msgid、兩個參照。

### `client/documents/workspace_service.py`（4 個空白）

`unlisted_package_entry(name)`（D5）；`import_files` 傳入清單外的項目，寫入失敗時用 `儲存文件失敗：{error}`（D3）。

### `client/conversion/text/dictionary_rules.py`（4 個空白）

`DictionaryRulesReadError(path, error)`，帶 `header_not_recognized: bool`；`from_paths` 中受保護的讀取（D4）。docstring 同步更新。

### `client/ui/conversion_presenter.py`（4 個空白）

`format_conversion_error` 對應 `DictionaryRulesReadError`（D4）；`_on_job_failure` 指出非開啟中的手動工作文件（D7）。可以 import `dictionaries.read_problems`（不含 wx）；`test_module_imports_neither_wx_nor_gui` 仍成立。

### `client/documents/export_coordinator.py`（4 個空白）

單份匯出的 `on_error` 指出非開啟中的文件（D7）。

### `client/config.py`、`client/settings/translation.py`、`settings/translation_tables.py`、`settings/view.py`（4 個空白）

`ConfigSaveProblem`；`_save` 與 setter 傳回它；三個 helper 傳回第一個問題（D6）。

### `client/gui.py`（tab）

`_prompt_for_document_name`（D5）、`_report_settings_save_problem` 與三個呼叫端（D6）、不經 `_()` 的 `_update_window_title`（D9）。

### `client/documents/formats.py`、`client/dual_view/browser.py`、`client/conversion/preprocessing/user_script.py`（4 個空白）

D8。

### Catalog

`client/locales/dotexpress.pot`、`client/locales/zh_TW/LC_MESSAGES/dotexpress.po`、`.mo`（D10）。

### 不修改

`dialog.py`、`ui/message_box.py`、`dictionaries/*`（只被 import）、`DictionaryEntriesDialog`、F-11 的訊息框、`client/braille/`、HANDOFF 第 2 節列出的每個檔案、兩個 fixture。

## 維持不變

- 每個訊息框的標題、圖示、按鈕與出現時機，D6 新增的訊息框除外。
- 「各路徑的前後對照」未列出的所有訊息文字。
- 轉換、匯出、匯入、儲存或拒絕的內容：只有用詞改變（加上 D6 的訊息框）。
- 清單內的重複名稱：`文件「{name}」已存在。`。
- F-8 D11 的 `config.json` 處理方式，以及 `config.log`、`gui.log` 的內容。
- Export All：步驟順序、`{文件}: {原因}` 的行、資訊／警告圖示的選擇。
- `translation_golden.json`（`e67d95a1...`）與 `dictionary_entries_trace.json`（`f493da52...`）。

## 使用者可見字串

| # | msgid | zh_TW msgstr | 位置 |
| --- | --- | --- | --- |
| 1 | `Export Complete with Errors` | `匯出完成，但有錯誤`（恢復） | D1 標題 |
| 2 | `All documents were exported successfully.` | `所有文件皆已成功匯出。`（恢復） | D1 |
| 3 | `Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}` | `成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}`（恢復） | D1 |
| 4 | `An unknown error occurred.` | `發生不明的錯誤。` | D2 |
| 5 | `The selected translation table could not translate this text.` | `選取的轉譯表無法轉譯這段文字。` | D2 |
| 6 | `HTML files (*.html)|*.html` | `HTML 檔 (*.html)|*.html` | D8 |
| 7 | `No supported browser or system HTML opener is available.` | `找不到可用的瀏覽器，也沒有可開啟 HTML 檔的系統程式。` | D8 |
| 8 | `main is not callable.` | `main 不是可以呼叫的函式。` | D8 |
| 9 | `main must return str, got {type}.` | `main 必須傳回 str，而不是 {type}。` | D8 |
| 10 | `The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.` | `檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。` | D3 |
| 11 | `This file type cannot be imported.` | `無法匯入這種類型的檔案。` | D3 |
| 12 | `The file name extension does not match the selected file type.` | `副檔名與選取的檔案類型不符。` | D3 |
| 13 | `Imported file must be a valid DotExpress DEP package.` | `匯入的檔案必須是有效的 DotExpress DEP 封裝檔。`（恢復） | D3 |
| 14 | `This PDF file is encrypted and cannot be imported.` | `這個 PDF 檔已加密，無法匯入。` | D3 |
| 15 | `The EPUB file is damaged or has no readable content.` | `EPUB 檔已損壞，或沒有可讀取的內容。` | D3 |
| 16 | `Dictionary "{name}" cannot be read. {reason}` | `無法讀取字典「{name}」。{reason}` | D4 |
| 17 | `Its header is not recognized. The first line of the file must contain the text, braille, and type headers.` | `無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。` | D4 |
| 18 | `The name "{name}" is used by "{file}" in the workspace folder, but that file is not in the document list.` | `名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清單中。` | D5（訊息框與匯入） |
| 19 | `Choose another name, or move or delete that file. Workspace folder:\n{folder}` | `請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n{folder}` | D5（訊息框） |
| 20 | `Settings Not Saved` | `設定未儲存` | D6 標題 |
| 21 | `DotExpress cannot save its settings to "{path}". Changes to the settings apply until DotExpress is closed, but they are not kept. This message is not shown again until DotExpress is started again.\n\n{reason}` | `DotExpress 無法將設定儲存到「{path}」。設定的變更在關閉 DotExpress 之前有效，但不會保留。在下次啟動 DotExpress 之前，不會再顯示這則訊息。\n\n{reason}` | D6 |
| 22 | `The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Details: {error}` | `檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}` | D6 |
| 23 | `Document "{name}" could not be converted.\n\n{error}` | `無法轉換文件「{name}」。\n\n{error}` | D7 |

msgid：381 + 23 = **404**（23 個中有 4 個是恢復的）。引號比照 `文件「{name}」已存在。`；「詳細資訊：」比照 F-6 的 INVALID_CSV 文字；「工作區」比照 `無效的工作區文件`；轉換／轉譯比照既有 catalog（轉換指整個操作，轉譯指 liblouis 的步驟）。

新近會出現的既有訊息：

- 作為匯入問題原因的 `文件「{name}」已存在。`、`文件名稱長度需為 1 到 32 個字元。`、`文件名稱不是有效的 Windows 檔名。`、`無法讀取檔案：{error}`、`儲存文件失敗：{error}` 與 CANNOT_OPEN 文字（D3）；
- 接在字串 16 之後的 F-6 四種原因（D4）；作為 D6 原因的 CANNOT_OPEN 文字；
- 匯出 HTML 中的 `此文件沒有可顯示的轉換資料。`（D8）。

## 無障礙（NVDA）

| 訊息 | 類型 | 開啟時讀出 | 之後的焦點 |
| --- | --- | --- | --- |
| Export All 摘要（D1） | task dialog（`message_box`） | 標題與全文（F-5、F-9 的量測） | 照舊（主視窗） |
| 匯入問題（D3、D5） | `FileIssuesDialog` | 對話框訊息；每則原因是清單中的一行 `{檔名}: {原因}` | 照舊 |
| 轉換錯誤（D2、D4、D7） | task dialog，標題 `錯誤` | 全文；D4 在 `轉譯失敗：` 之後是一組兩句；D7 以文件名稱開頭 | 照舊（D7 不移動焦點） |
| 名稱被清單外項目占用（D5） | task dialog，標題 `錯誤` | 字串 18，接著字串 19 與路徑 | 名稱對話框照舊重新出現，名稱已選取 |
| 設定未儲存（D6） | task dialog，標題 `設定未儲存`，警告圖示 | 全文，含路徑與原因 | 原本作用中的視窗（設定對話框或字典管理），否則為主視窗 |

- 新文字把「該怎麼做」放在同一個訊息框裡，螢幕報讀器使用者不必查 `config.log` 或工作區資料夾的檔案列表也能理解問題。
- D4 與 D7 把錯誤放在同一個訊息框：不需要多關一個框。
- 較長的路徑（D5、D6）放在訊息最後，先聽到句子，再聽到路徑。
- 手動項目 119 確認 NVDA 會完整讀出 D4、D5、D6、D7 的訊息框。

## 測試計畫

TDD：每一步的測試先寫，並因預期的原因失敗。縮排依各檔案（這裡大多數測試檔用 4 個空白；逐檔確認）。只使用暫存資料夾。會讓程式寫 log 的測試使用 `assertLogs`，或隔離 `dotexpress.gui`／`dotexpress.config`，不寫入 `client/log/`。預期文字以 `_()` 組成；以 catalog 為重點的測試直接比對 zh_TW msgstr。非 ASCII 測試資料在該檔已有慣例時用 `\u` 跳脫。

### A. Catalog（`tests/test_i18n.py`）

1. 下表 23 個 msgstr（subTest）。
2. AST msgid 掃描等於 catalog：404。
3. 防護測試：`export_results.py` 的常數、`plain_text.py` 的文字與 `formats.py` 的 HTML 類型字串都是 `N_` 呼叫（AST）。
4. 防護測試：`gui._update_window_title` 中沒有 `_` 呼叫（AST；D9）。

### B. Export All（`tests/test_export_coordinator.py`、`tests/test_gui_document_flows.py`）

1. **翻轉**摘要的四個 `KNOWN BUG (P1-4 spec, defect 4)` 釘選測試（`test_export_coordinator.py:148`、`547`；`test_gui_document_flows.py:4140`、`4171`）：成功摘要為 `所有文件皆已成功匯出。`／`匯出完成`；部分失敗為 `匯出完成，但有錯誤` 與中文的數量。紅燈：英文。

### C. 轉換訊息（`tests/test_conversion_presenter.py`、`tests/test_gui_document_flows.py`）

1. **翻轉** `test_format_conversion_error_public_texts` 與它在 frame 的對應測試（`:188`、`:3781`）：中文的備用訊息。紅燈。
2. D4：`DictionaryRulesReadError` 在 NOT_UTF8、CANNOT_OPEN、INVALID_CSV、OTHER 與表頭情況下，`format_conversion_error` 得到 `轉譯失敗：無法讀取字典「d」。<原因>`，一行（沒有 `\n`）。紅燈。
3. D4 經 presenter：手動失敗以標題 `錯誤` 顯示；匯出失敗把同一段文字交給 `on_error`；Export All 的一步把它列成一行。
4. D7：送達時目標不是開啟中的手動工作：字串 23 帶目標名稱；目標開啟中（含切走再切回）：現在的文字；開始時沒有文件、現在開著一份：現在的文字。第一種紅燈。
5. D7：送達時不是開啟中的文件，單份匯出：指出名稱；開啟中：不指出；Export All：各行不變。
6. D8：`main` 傳回 `None`，以及 `main` 定義後被改成不可呼叫的值時，`execute_preprocessing_script` 經 `format_conversion_error` 得到中文。

### D. 字典規則（`tests/test_conversion_text_dictionary_rules.py`）

1. `from_paths` 在下列情況拋出 `DictionaryRulesReadError`（帶路徑與原因）：Big5 檔、`PermissionError`（patch 字典路徑的 `open`）、欄位超過 `csv.field_size_limit()`、表頭 `Text,Braille,Type`、0 位元組檔（後兩者 `header_not_recognized` 為真）。紅燈。
2. 內建 Bopomofo 檔讀不到時**不**包裝。
3. 檔案中某一列在 `processing` 或對齊時拋出的錯誤不包裝（注入一個拋出 F-11 不攔截之例外的 `processing`，或一列對齊失敗的資料）。
4. 不存在的字典仍得到空規則；既有 golden 案例全部不變。

### E. 匯入（新檔 `tests/test_import_problems.py`；`tests/test_documents_workspace*.py`；`tests/test_workspace_service.py`；`tests/test_gui_document_flows.py`）

1. D3 表格每一列的 `describe_import_problem`，包括 `dep` 的 `BadZipFile`、缺 `.brl` 的封裝檔造成的 `KeyError`、加密的 PDF（以 `pypdf` writer 的 `encrypt` 產生，或以 stub reader 代替）、沒有 spine 的 EPUB。
2. `batch_import_documents`：探針 1 的原因變成中文；清單內的重複得到 `文件「alpha」已存在。`；清單外的項目得到帶磁碟拼寫的字串 18。
3. `import_files`：封裝檔寫入失敗得到 `儲存文件失敗：...`。
4. frame 的匯入流程在 `FileIssuesDialog` 中顯示中文的行。
5. `load_workspace_documents` 仍把損壞的封裝檔判為無效（`ImportProblem` 是 `ValueError`）。

### F. 名稱檢查（`tests/test_gui_document_flows.py`、`tests/test_workspace_service.py`）

1. 有清單外的 `bad.dep`（無效封裝檔，以及資料夾兩種）時新增 `BAD`：訊息框為指出 `bad.dep` 的字串 18、一個空行、附工作區路徑的字串 19；對話框以 `BAD` 重新出現。紅燈：`文件「BAD」已存在。`。
2. 改名成這種名稱：相同。
3. 清單內的重複維持 `文件「alpha」已存在。`（即使同名的另一種大小寫在磁碟上有清單外的項目，也以清單檢查為準）。
4. `unlisted_package_entry`：磁碟上的拼寫；名稱未被占用時為 `None`；列表沒找到時的 `"{name}.dep"` 備用值（patch `os.scandir`）。

### G. 設定（`tests/test_config.py`、`tests/test_settings_*.py`、`tests/test_gui_*.py`）

1. `_save`／setter 傳回 `UNREADABLE`（讀取時拋 `PermissionError` 的 `config.json`）、`BACKUP_FAILED`（損壞的 JSON 加上一個名為 `config.json.bak` 的資料夾）、`WRITE_FAILED`（`os.replace` 失敗）；存檔成功時為 `None`。log 與檔案位元組與之前相同（既有的 F-8 測試維持綠燈）。紅燈。
2. 三個 helper 傳回第一個問題。
3. `get_or_create_client_id` 與 `set_lang(persist=True)` 行為不變，傳回值也不變。
4. frame：有問題時 `apply_settings_from_dialog` 只顯示一次訊息框（精確的標題、含路徑與原因的內容、`wx.ICON_WARNING`）；第二次呼叫不顯示；`_set_view_font_size` 與 `_set_active_dictionary` 透過同一個旗標回報；沒有問題時不顯示。每種情況下記憶體中的設定都已改變。
5. 有作用中視窗時父視窗是它（patch `wx.GetActiveWindow`），否則是主視窗。

### H. 其餘（`tests/test_dual_view_browser.py`、`tests/test_document_formats.py` 或測試 `formats` 的模組）

1. 沒有可用程式時，`open_html_in_browser` 拋出文字為字串 7 msgstr 的 `OSError`。
2. 沒有資料的文件匯出 HTML 時，內容含 `此文件沒有可顯示的轉換資料。`。
3. `get_format("html").export_wildcard` 是該 msgid，`build_export_wildcard(_)` 顯示 `HTML 檔 (*.html)|*.html`。

### Mutation 檢查（plan；每個都必須被抓到）

1. `export_results` 的某個常數沒有標記（回到英文）；
2. `plain_text` 的文字沒有標記；
3. `UnicodeDecodeError` 用一般文字說明；
4. `PermissionError` 用原始文字說明；
5. 名稱代碼 `too_long` 與 `invalid` 對調；
6. `ImportProblem` 以 `str()`（英文）顯示；
7. 損壞的 `dep` 用一般文字說明；
8. 清單內的重複使用清單外的原因（先後順序顛倒）；
9. 封裝檔寫入失敗以原始文字顯示；
10. Bopomofo 檔也被保護；
11. 處理階段的錯誤落在保護區塊內；
12. 表頭情況說明成 OTHER；
13. 字串 16 換成 F-6 的兩段式（Export All 的一行中出現 `\n`）；
14. 清單內的名稱也顯示 D5 訊息框；
15. `{file}` 用輸入的拼寫；
16. 沒有傳回 `UNREADABLE`；
17. 沒有傳回 `BACKUP_FAILED`；
18. 沒有傳回 `WRITE_FAILED`；
19. 忽略「每次執行一次」的旗標；
20. `get_or_create_client_id` 也顯示訊息框；
21. 存檔成功後仍顯示訊息框；
22. `_set_view_font_size` 沒有回報；
23. `_set_active_dictionary` 沒有回報；
24. D7 在文件開啟中時也指出名稱；
25. D7 在文件不是開啟中時沒有指出名稱；
26. D7 的匯出規則用要求當下開啟的文件；
27. Export All 的行被字串 23 包起來；
28. 匯出 HTML 用英文的空白文字；
29. 瀏覽器錯誤沒有翻譯；
30. 文字處理程式錯誤沒有翻譯；
31. `_update_window_title` 又加回 `_()`。

### 數量

約 50 個新測試、6 個翻轉（A 4；B 翻轉 4；C 6 + 翻轉 2；D 4；E 5；F 4；G 5；H 3）。精確的 `Ran` 由 plan 決定。F-11 之後在 Windows 上：`OK (skipped=6)`。

## 遷移步驟（每一步一個綠燈 commit，先紅燈）

1. `fix: translate the Export All summary and the conversion fallback texts (F-12, P1-4 defect 4)`：D1、D2；字串 1–5；測試 A（部分）、B、C1。
2. `fix: explain why an imported file was skipped (F-12, P1-4 defect 4)`：D3；字串 10–15；測試 E。
3. `fix: explain a conversion that cannot read the selected dictionary (F-12, F-6 O5)`：D4；字串 16、17；測試 C2、C3、D。
4. `fix: explain a document name held by a file that is not listed (F-12, F-8a)`：D5；字串 18、19；測試 F、E2（清單外的部分）。
5. `fix: tell the user when settings cannot be saved (F-12, F-8a M-7)`：D6；字串 20–22；測試 G。
6. `fix: name the document of a failed conversion that is not open (F-12, F-9 M-9)`：D7；字串 23；測試 C4、C5。
7. `fix: localize the remaining English messages and drop a misused _() (F-12)`：D8、D9；字串 6–9；測試 C6、H、A3、A4。

每個新增字串的步驟都重新產生 catalog；最後一個會移動 msgid 上方行數的步驟再產生一次，確保 `#:` 參照沒有過期（F-9「Corrected after planning」2）。若能省一次 catalog 流程，plan 可以合併步驟 1 與 7，commit 主旨合併。每個 commit 以 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` 結尾，只 stage 明確路徑。

## 驗收條件

在 Windows 上從 `client/` 以 `$PY` 執行，runtime 依 F-3 plan Task 0 複製。

1. 完整測試：沒有 failure 與 error；`Ran` 如 plan 所述。
2. 聚焦：`$PY -m unittest tests.test_i18n tests.test_export_coordinator tests.test_conversion_presenter tests.test_conversion_text_dictionary_rules tests.test_import_problems tests.test_workspace_service tests.test_config tests.test_gui_document_flows -v`（加上 plan 為 G、H 指定的模組）通過。
3. `grep -rn "KNOWN BUG (P1-4 spec, defect 4)" client/tests` 沒有輸出。
4. Catalog：23 個新 msgid（4 個恢復），msgstr 與下表相同；`msgfmt --check --statistics` 全部已翻譯、0 fuzzy；AST 掃描等於 catalog（404）；`POT-Creation-Date` 不變；四個恢復的項目沒有殘留 `#~` 副本。
5. 兩個 fixture 的 sha256 不變。
6. 應用程式資料未被動到：主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 前後 sha256 相同；worktree 沒有產生 `client/log/`、`client/workspace/` 或 `client/config.json`。
7. `git diff main --stat` 只動到「各檔案的設計」列出的檔案、測試，以及 spec、plan、history 檔案。
8. 上述 mutation 檢查。
9. 下列 packaged GUI 驗證，結果放在實作的 history 資料夾。

## Windows 驗證（packaged build）

build 與 process 規則同 F-11：

- 主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面，再執行 `scripts\build-dotexpress.bat`；
- 在 `PYZ-00.toc` 確認改動的模組來自 worktree；
- exe 放到 `D:\dxtest\N-f12\`；「之前」是 F-11 之後 `main` 的 build（由 plan 指定）；
- 每個項目在新的 `D:\dxtest\auto<項目>-f12` 資料夾以 exe 的複本執行；只結束這些資料夾底下的 process（`taskkill /T`）；
- **fix** 項目在兩個 build 上都跑（預期文字不同）；**regression** 項目只在 `N-f12` 上跑，結果不符預期時才在之前的 build 上補跑（使用者，2026-10-11）；
- 腳本沿用 `2026-10-09-03-windows-verification/auto/`（`dx.py`、`docs.py`、`dicts.py`、`lock.py`）與 `2026-10-10-01-f5-save-failure-handling/auto/f5gui.py`，不修改；task dialog 透過 UIA 讀取；**腳本絕不讀寫剪貼簿**（文字以 `set_edit_text` 或按鍵輸入）；設定、字典與工作區檔案在啟動前由腳本寫好。

| # | 類別 | 步驟 | F-12 之後的預期 | 之前 |
| --- | --- | --- | --- | --- |
| 109 | fix | 三份已轉換的文件；檔案 > 匯出全部 > BRL，匯出到空資料夾 | 訊息框 `匯出完成`／`所有文件皆已成功匯出。`；三個檔案 | `All documents were exported successfully.` |
| 110 | fix | 同 109，但資料夾中已有 `beta.brl`，並由 `lock.py` 以 share-none 鎖住（覆寫詢問回答「是」） | `匯出完成，但有錯誤`／`成功匯出的文件：2`／`匯出失敗的文件：1`／`beta: <OS 文字>` | 英文的標題與數量 |
| 111 | fix | 匯入，篩選「所有支援的格式」，輸入下列路徑：`alpha.txt`（清單中已有）、`big5.txt`、40 字元的 `.txt`、`locked.txt`（share-none）、`broken.dep`（不是 zip）、`foo.xyz` | 匯入問題各行：`文件「alpha」已存在。`、字串 10、`文件名稱長度需為 1 到 32 個字元。`、CANNOT_OPEN 文字、字串 13、字串 11 | 探針 1 的英文各行 |
| 112 | fix | `config.json` 選擇 `big5dict`（Big5 CSV）；轉換一段短文字。再以 `caps`（`Text,Braille,Type`）、`empty`（0 位元組）、以及一個被 share-none 鎖住的可讀字典重複。最後以 `big5dict` 對兩份待轉換文件執行匯出全部（BRL） | 每次轉換：`轉譯失敗：無法讀取字典「<名稱>」。<原因>`，原因依序為 NOT_UTF8、字串 17（兩次）、CANNOT_OPEN；匯出全部摘要：每份文件一行，文字相同 | `轉譯失敗：'utf-8' codec ...`、`CSV must contain ...`、`[Errno 13] ...` |
| 113 | fix | 工作區有 `alpha.dep`（有效）與 `bad.dep`（無效，啟動時選「保留無效檔案」）。新增 `BAD`；把 `alpha` 改名為 `bad`；匯入 `bad.txt` | 新增與改名：訊息框為指出 `bad.dep` 的字串 18 與附工作區路徑的字串 19；名稱對話框帶著名稱重新出現；匯入：`bad.txt: ` + 字串 18；檔案都不變 | `文件「BAD」已存在。`；`Document "bad" already exists.` |
| 114 | fix | (a) 啟動前由 `lock.py` 以 share-none 鎖住 `config.json`；設定：改字型大小，確定；再於原文編輯框 Ctrl+滾輪。(b) `config.json` 內容為 `{`，另有名為 `config.json.bak` 的資料夾；設定：改寬度，套用，再按確定 | (a) 按確定後一個訊息框：`設定未儲存`、附路徑的字串 21、CANNOT_OPEN 原因；Ctrl+滾輪後沒有訊息框；畫面上字型大小改變；`config.json` 位元組不變。(b) 套用後出現以設定對話框為 owner、原因為字串 22 的訊息框；按確定後沒有；`config.json` 仍是 `{` | 沒有訊息框 |
| 115 | fix | 字典資料夾中的 `preprocessing.py`：`def main(input):` 先 sleep 5 秒，再拋出 `ValueError("boom")`。(a) 開啟 `alpha`，Ctrl+Enter，立刻 Ctrl+Tab 到 `beta`，等待。(b) 開啟 `alpha`，在清單中選取 `beta`（待轉換），檔案 > 匯出 > BRL，等待。(c) 同 (a) 但不按 Ctrl+Tab | (a) `錯誤` 訊息框 `無法轉換文件「alpha」。` + 空行 + `文字處理失敗：boom`；(b) 同上，指出 `beta`；(c) 只有 `文字處理失敗：boom` | (a)、(b) 只有 `文字處理失敗：boom`；(c) 相同 |
| 116 | fix | 預設文件 `new`（沒有轉換資料）：檔案 > 匯出 > 雙視檢視 HTML；讀取存檔對話框的檔案類型清單；存檔 | 類型清單顯示 `HTML 檔 (*.html)`；檔案內含 `此文件沒有可顯示的轉換資料。` | `HTML files (*.html)`；英文句子 |
| 117 | fix | `preprocessing.py` 的 `main` 傳回 `None`；轉換 | `文字處理失敗：main 必須傳回 str，而不是 NoneType。` | `...main must return str, got NoneType.` |
| 118 | regression | (a) 以可讀的字典轉換：`轉換完成。` (b) 清單中已有 `alpha` 時新增 `alpha`：`文件「alpha」已存在。` (c) `config.json` 可寫時在設定中按確定：沒有訊息框，檔案已更新。(d) F-9 case (b) 在 Ctrl+Tab 後的成功訊息框仍為 `轉換完成。結果已儲存到文件「alpha」。` | 如左 | （結果不符預期時才跑） |

絕不觸發真的登出或關機；沒有項目需要。

**給使用者的手動項目（項目 119，NVDA）：** 以 `N-f12` 並開著 NVDA，聆聽項目 112（任一情況）、113（新增）、114 (a) 與 115 (a) 的訊息框：是否讀出全文，包括文件或字典名稱與路徑；Esc 是否能關閉每個訊息框；之後焦點在哪裡。

## 風險

- **恢復的 catalog 項目**（低）。若 `msgmerge` 沒有恢復字串 1–3 或 13 之一，就要依下表填 msgstr。驗收條件會檢查。
- **模糊配對**（低）。`msgmerge` 可能把新 msgid 配到舊的（D10 列出可能的組合）。plan 逐一檢查新項目。
- **`ImportProblem` 是 `ValueError`**（低）。攔截 `ValueError` 的程式照常運作；`load_workspace_documents` 仍把損壞的封裝檔標為無效（測試 E5）。
- **字典的受保護讀取**（低）。先讀完所有列再處理，沒有可觀察的差異（檔案小，每次轉換只讀一次，`DictionaryRulesLoader`），但區塊邊界錯誤可能把處理錯誤說成「無法讀取」（mutant 11），或漏掉該包裝的錯誤（測試 D1–D3）。
- **setter 有了傳回值**（低）。忽略它的呼叫端不受影響；client-init 執行緒的存檔刻意忽略。
- **Ctrl+滾輪時跳出警告框**（低，刻意只有一次）。第一格無法儲存時出現 modal 訊息框，之後不再出現。Q1 讓使用者選擇其他觸發方式。
- **F-11 rebase**（中，機械性）。`dictionary_rules.py` 與 `gui.py` 兩邊都改；一律以函式名稱指稱，plan 從 F-11 之後的 `main` 開始。
- **匯入問題的行變長**（低）。有些原因是兩句；對話框清單照舊每個檔案一行，可水平捲動。

## 待決問題

**使用者已決定（2026-10-11）：** U1（只做文字訊息，候選 1–4）、U2（F-9 M-9 納入）、U3（不納入的項目）。

**Decided by orchestrator with the recommended default; user may override before merge：**

- **O1.** 匯入原因在合適時沿用既有文字（文件名稱訊息、CANNOT_OPEN、`無法讀取檔案：{error}`、`儲存文件失敗：{error}`），不另加新字串（D3）。
- **O2.** 兩則 EPUB 錯誤共用一段文字（字串 15），不顯示 spine item 的 id（D3）。
- **O3.** 轉換時讀不到字典不寫 log（D4）。
- **O4.** D4 訊息是一行（字串 16），而不是 F-6 的「標題、空行、原因」，因為它也是 Export All 摘要的一行（D4）。
- **O5.** 內建的 Bopomofo 檔不在 D4 範圍內（D4）。
- **O6.** 匯入顯示字串 18，不加資料夾那一行（D5）。
- **O7.** 移除視窗標題的 `_()`；顯示時的 `_(value)` 寫法保留（D9）。
- **O8.** 設定警告在存檔位置同步顯示，父視窗為作用中的視窗（D6）。
- **O9.** D7 也涵蓋非開啟中文件的單份匯出；Export All 維持逐份列出的行（D7）。
- **O10.** 文字處理程式的錯誤（字串 8、9）也在地化，雖然讀者是程式作者，以便與 catalog 中已有的兩則檢查訊息一致（D8）。

**需要使用者回答的問題**（不阻擋；本文以建議選項撰寫）：

- **Q1. 設定警告何時出現？** (a) **建議：** 每次執行一次，在第一次存檔失敗時，三個存檔位置都算（D6）。(b) 只在設定的確定／套用之後（Ctrl+滾輪與字典改名都不出現），每次執行一次。(c) 每次存檔失敗都出現。
- **Q2. DotExpress 取代損壞的 `config.json` 時**（會先複製成 `config.json.bak`，F-8 D11）目前也沒有提示：使用者之前的設定回到預設值，只有 `config.log` 說明原因。要告訴使用者嗎？(a) **建議：** 不在 F-12 做，列為後續（這不是存檔失敗，而且沒有遺失：`.bak` 保存了原檔）。(b) 在 F-12 用 D6 的機制多加一個訊息框（多一個字串）。
- **Q3. 用詞。** 下表 23 個 msgstr，特別是 10、18／19、21、23。建議：照本文；修改只是一行 catalog 編輯。

## 本文新引入的使用者可見預設（非使用者決定）

每一項若使用者想改，都只是一行的修改：

1. 字串 1–23 的**文字與標題**（4 個恢復的字串沿用舊翻譯）。
2. **D4 訊息是一行** `轉譯失敗：無法讀取字典「X」。<原因>`，空的（0 位元組）字典說明為表頭無法辨識。
3. **D5 訊息框指出磁碟上的項目**（`bad.dep`）並顯示工作區資料夾路徑；匯入只顯示句子、不含路徑。
4. **清單檢查優先**於清單外檢查（清單內的重複維持 `文件「X」已存在。`）。
5. **設定警告每次執行出現一次**，在設定、Ctrl+滾輪或字典改名第一次存檔失敗時（Q1），警告圖示，父視窗為作用中的視窗。
6. **D7 也對非開啟中文件的單份匯出指出名稱**，不只是切換後的手動轉換。
7. **無法使用的檔名在匯入時的原因**沿用文件名稱對話框的文字（空名稱也顯示 `文件名稱長度需為 1 到 32 個字元。`）。
8. **HTML 存檔類型**為 `HTML 檔 (*.html)|*.html`；標籤 `HTML` 維持英文。
9. **沒有轉換資料時匯出的 HTML** 顯示中文句子（`<html lang="en">` 屬性不變；見「範圍外」）。

## 範圍外／後續項目

使用者排除（U3），本文不設計：

- **啟動提示框掛在尚未顯示的主視窗下**（F-8b review M-8）：「已復原文件」「已取代字元」與無效檔案對話框都在 `Show()` 之前出現；NVDA 與 Alt+Tab 是否到得了，見手動項目 83。
- **轉換中收到 `WM_ENDSESSION`** 偶爾以 `0xC0000374` 結束（F-9 review M-8）：`BrailleApp.OnExit` -> `runtime.close()` 時 worker 仍在 liblouis 內（推測）；便宜的緩解是轉換執行緒還活著時跳過 `runtime.close()`。
- **防毒軟體抓住檔案時殘留的匯出 `.tmp`**（F-7／F-8a）：自動重試。
- **字典表頭不分大小寫**（`Text,Braille,Type`；F-11 review M-1 的後續）：要同時改編輯器的載入與轉換；在此之前由 D4 與 F-11 的字串 12 說明表頭問題。
- **Delete All 回復**（P1-3 defect 4）：沒有剩下有效文件時，標題不更新，也不建立預設文件（`gui.py:903-910`；由 `test_delete_all_failure_without_valid_document_clears_editors_only` 釘住）。
- **F-W5**：`scripts/tests/test_vendor_helper_snapshot.py` 以 `read_bytes()` 讀 autocrlf 轉成 CRLF 的檔案，與 LF 文字比較；在測試中先統一換行即可修正。

撰寫本文時發現、不屬於文字訊息或未被要求的項目：

- **D7 訊息框之後的焦點**：切換後仍停在唯讀的點字結果編輯框（F-9 review M-6 只在成功的 case (b) 之後移動焦點）。
- **雙視檢視 HTML 宣告 `<html lang="en">`**（`dual_view/html.py:51`），內容卻是中文。開啟 NVDA 自動切換語言時可能選到英文語音。不是訊息文字；列為後續（改成介面語言，或省略 `lang`）。
- **損壞的 `config.json` 被靜默取代**（Q2）。
- 在地化前導文字之後的**作業系統與函式庫原文**（`[Errno 13] ...`、`File is not a zip file`、MathCAT 訊息），以及文字處理程式的 Python `SyntaxError` 原文。
- **case (b) 存檔失敗的結果在關閉時遺失**（F-9 review M-5；屬 F-5 範圍）。
- **既有是／否確認框的 Esc**（F-11「範圍外」；對話框行為，不是文字）。
- F-10（UEB 斷行、`$`）。
