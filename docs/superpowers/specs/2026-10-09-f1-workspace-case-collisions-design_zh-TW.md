# 工作區大小寫衝突（F-1）設計

## 目標

修正任務 F-1 修正文件工作區中兩個優先序 1 的資料遺失缺陷，即 P2 階段審查在「既有缺陷清單」所列的前兩列（`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md`）。兩者都是在 P1-3 發現的（`docs/superpowers/specs/2026-10-08-p1-3-document-controller-design.md`，「Known defects」第 1、2 項），並由 `# KNOWN BUG` 測試釘住：

1. **只改大小寫的重新命名會讓文件遺失**，發生在不分大小寫的檔案系統（Windows、預設的 macOS）。把 `Alpha` 改名為 `alpha` 會寫入 `alpha.dep`，而它與 `Alpha.dep` 是同一個檔案，接著 `Alpha.dep` 被 unlink，包就不見了。由 `test_case_only_rename_on_case_insensitive_file_system_deletes_package` 釘住。
2. **新增只差大小寫的名稱會覆寫另一份文件。** 在 `alpha` 已存在時新增 `Alpha`，會通過區分大小寫的重複檢查，並覆寫 `alpha.dep`。由 `test_add_case_variant_on_case_insensitive_file_system_overwrites_package` 釘住。

完成後：

- 在所有平台上，新增與重新命名都以不分大小寫（`str.casefold()`）比較文件名稱，與匯入目前的做法一致。`alpha` 存在時 `Alpha` 會被拒絕。拒絕時沿用既有的 `Document "{name}" already exists.` 訊息與重新詢問。
- 只改大小寫的重新命名（`Alpha` 改為 `alpha`）是允許的，且在任何檔案系統上都保留文件。磁碟上的包最後的名稱正好是 `alpha.dep`，成員為 `alpha.*`。
- 重新命名成*另一份*文件的大小寫變體（`alpha` 存在時把 `beta` 改為 `Alpha`）會像完全重名一樣被拒絕。目前在 Windows 上這會覆寫 `alpha.dep`；同一個檢查順帶修好。
- 不分大小寫的行為在 Linux 上透過注入重新命名程式碼的「不分大小寫檔案模型」來驗證，不只在 Windows 驗證。

這是刻意的行為變更，僅限於大小寫變體。沒有新的使用者可見字串，msgid 不變（353，集合相同）。其他流程（儲存、匯入、刪除、全部刪除、一般重新命名及其失敗行為）完全不變。優先序 2 的 defect 3（重新命名時 unlink 失敗留下兩份包）**不**納入（見 D6）。

## 現況（2026-10-09 於 `fix/f1-workspace-case-collisions` 驗證，HEAD `c8ecf66`，P0–P2 全部任務已合併）

`$SP` 是 session scratchpad，`$PY` 是 `$SP/venv/bin/python`。

基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 1095 tests`、`FAILED (failures=1, skipped=9)`。失敗的是已知的 P2-5 案例 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。9 個 skip 為 7 個 Windows 專用的 liblouis 測試，以及 `tests/test_gui_document_flows.py` 中兩個 `..._on_case_insensitive_file_system_...` 測試（Linux 區分大小寫）。在 repo 根目錄執行 `$PY $SP/p12/tools/msgid_scan.py client` 回報 `source msgids: 353`。Fixture：`client/tests/fixtures/translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`、`client/tests/fixtures/dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`。

### 重複檢查

- `documents/session.py:52-53`（tab）`document_name_exists(documents, name, exclude_name)` 以**完全相等**比較：`document.name == name and document.name != exclude_name`。`DocumentController.document_name_exists`（`documents/controller.py:70-71`）委派給它。唯一的正式呼叫端是 `BrailleFrame._prompt_for_document_name`（`gui.py:637-658`），由新增（`gui.py:733-739`，無 exclude）與重新命名（`gui.py:741-767`，`exclude_name=` 來源名稱）使用。命中時以使用者輸入的名稱顯示 `_('Document "{name}" already exists.')`，標題 `_("Error")`，`wx.OK | wx.ICON_ERROR`，並以輸入的名稱預填重新開啟對話框。
- 匯入已經比較 casefold 後的名稱：`documents/workspace.py:152` 與 `:166-169`（`batch_import_documents`），問題文字 `Document "{name}" already exists.` 指名的是匯入進來的名稱。工作區排序也是 casefold 優先（`load_workspace_documents`、`DocumentController.sort_documents`）。
- 新名稱與來源完全相同時，`on_rename_document` 提前返回（`gui.py:756`）；只改大小寫的變更會進到 service。service 對相同名稱丟出 `ValueError`（`workspace_service.py:99-100`）。

### 包檔案

- `save_document_package(path, document)`（`documents/workspace.py:50-66`）以 `zipfile.ZipFile(path, "w")` 開啟 `path`，寫入 `<name>.txt`、`<name>.brl`，點字待轉換時另寫 `<name>.meta.json`。
- `load_document_package(path)`（`documents/workspace.py:69-93`）由**檔名**取得文件名稱，並要求成員名稱與之完全相同（`:84`，`txt_base != package_name` 丟出 `"Document package names do not match."`）。`load_workspace_documents` 會把這種檔案列為無效，啟動時的對話框會提議刪除它。
- `DocumentWorkspaceService.rename_document`（`documents/workspace_service.py:98-108`）：`save_document_package(new_path, ...)`，接著 `if old_path.exists(): old_path.unlink()`，再 `controller.rename_document`。寫入失敗會往外拋且什麼都沒改；unlink 失敗會往外拋，磁碟上留下兩份包，controller 不變（已知 defect 3）。

### 兩個缺陷的成因，以及為何「跳過 unlink」不夠

在 NTFS 與 APFS（不分大小寫、保留大小寫）上，`alpha.dep` 會解析到既有的項目 `Alpha.dep`。以寫入模式開啟會截斷並重寫**該項目，而它保留原本的拼寫** `Alpha.dep`。

- Defect 1：寫入把 `alpha.txt`／`alpha.brl` 放進 `Alpha.dep`；`old_path.exists()` 為真；unlink 刪掉唯一的檔案。記憶體中到程式關閉前仍有 `alpha`；下次啟動就沒有這份文件了。
- Defect 2：新增 `Alpha` 時把 `Alpha.*` 成員寫進 `alpha.dep` 這個項目。下次啟動時檔名（`alpha`）與成員（`Alpha`）不符，被列為無效，並提議使用者刪除。`alpha` 的內容早已不見。

審查建議「新舊路徑是同一個檔案時不要 unlink」。單靠這點修不好 defect 1：包會以 `Alpha.dep` 的名稱留下，內含 `alpha.*` 成員，下次啟動時一樣無法通過名稱檢查，與 defect 2 相同。必須重新命名目錄項目本身。這裡已用下文模型的原型確認：舊的流程留下 `[]`；只寫不 unlink 則留下被 `load_workspace_documents` 判為無效的 `Alpha.dep`。

### 字典（已檢查；沒有資料遺失）

`dictionaries/manager.py` 的 `create_dictionary`（`:50-60`）、`import_dictionary`（`:63-73`）與 `rename_dictionary`（`:76-86`）都檢查 `destination_path.exists()`，在不分大小寫的檔案系統上大小寫變體也會命中。因此大小寫變體在那裡會被拒絕（`FileExistsError`，顯示為 `Dictionary "{name}" already exists.`），而且 `Path.rename` 不會覆寫。沒有資料遺失。剩下的差異是易用性與平台分歧：在 Windows 上只改大小寫的字典重新命名會被當成重複而拒絕（`tests/test_dictionary_presenter.py:397-406` 因此在那裡 skip），在 Linux 上則允許大小寫變體。這與文件的機制不同（字典是沒有成員名稱的純 CSV，而選取中的字典名稱存在 `config.json`，由 `resolve_selected_dictionary` 以完全相等比對），修改需要另外的決定。列為後續，不在本任務內（見「範圍外」）。

檢查時順帶發現（既有，此處不修）：`tests/test_dictionary_name_prompt.py:82` `test_case_only_rename_still_renames` 沒有大小寫敏感度的 skip；在 Windows 上 `rename_dictionary` 對 `alpha` 改 `Alpha` 會丟出 `FileExistsError`，所以這個測試預期在那裡會 error。已加入 Windows 待驗證清單。

## 決定

**D1. 所有平台都以 casefold 檢查重複。** `session.document_name_exists` 比較 `document.name.casefold() == name.casefold()`；排除條件維持**完全相等**（`document.name != exclude_name`）。理由：匯入、排序與審查建議的修法都已使用 casefold；所有平台一套規則，可避免一個在 Linux 合法、複製到 Windows 卻會衝突的工作區；正式發行平台是 Windows。在區分大小寫的檔案系統（Linux）上可見的變化：`alpha` 旁邊再新增 `Alpha` 現在會被拒絕，與匯入已有的行為一致。排除條件完全相等，表示文件自己只改大小寫的重新命名是允許的；而在已同時有 `Alpha` 與 `alpha` 的舊工作區（只可能在區分大小寫的檔案系統上產生）中，把其中一個改成第三種拼寫會被拒絕。

**D2. 拒絕時沿用今天的重複訊息。** 以輸入的名稱顯示 `Document "{name}" already exists.`，然後以輸入的名稱預填重新開啟對話框，與完全重名時相同。這與匯入一致（匯入也指名進來的名稱）。沒有新字串。

**D3. 允許只改大小寫的重新命名，並安全地實作。** 使用者把 `Alpha` 改成 `alpha` 是有意的；拒絕它也會與既有的區分大小寫測試（預期改名成功）相矛盾。「只改大小寫」以名稱判斷：`source_name != new_name and source_name.casefold() == new_name.casefold()`，而不是探測檔案系統：結果確定、各處一致、可在 Linux 測試。新流程與檔案系統無關，因此在區分大小寫的檔案系統上也正確。

**D4. 安全流程（`move_document_package`）。** 絕不寫入、取代到或刪除一個可能與另一份包互為別名的名稱：

1. 暫存：把新包寫到旁邊一個新的暫存檔（`.<新名稱>.dep.<隨機>.tmp`）。任何失敗（也包括非 `OSError`，例如孤立 surrogate 造成的 `UnicodeEncodeError`）都刪除暫存檔並重新拋出。其他東西都沒變。
2. 移開：若舊包存在，以 `os.replace` 把它移到新的暫存檔 `.<舊名稱>.dep.<隨機>.tmp`。失敗時刪除兩個暫存檔並重新拋出。舊包未被動過。
3. 安裝：`os.replace(staged, new_path)`。此時已沒有任何同名項目（在不分大小寫的檔案系統上舊項目已被移開），所以新項目的拼寫完全是新名稱。失敗時（若第 2 步移開過）把舊包從暫存檔移回原路徑（原本的拼寫），刪除暫存的新包，並重新拋出。
4. 清理：刪除移開的暫存檔。此處的失敗**會被忽略**：重新命名已完成，記憶體與磁碟一致；若拋出例外，controller 會停在舊名稱而磁碟是新名稱（下次儲存就會在不分大小寫的檔案系統上把 `Alpha.*` 成員寫進 `alpha.dep` 項目，即 defect 2 的不一致）。殘留檔以 `.tmp` 結尾，`load_workspace_documents`（`*.dep`）不會列出它，也不會提議刪除。

暫存檔名沿用 `conversion/preprocessing/user_script.py:53-74`（`save_preprocessing_script`）的既有模式（`tempfile.NamedTemporaryFile(dir=..., prefix=f".{name}.", suffix=".tmp", delete=False)`，立即關閉）。會先建立目錄（`mkdir(parents=True, exist_ok=True)`），與 `save_document_package` 相同，因此舊包不存在時只改大小寫的重新命名仍可運作。第 2–3 步的 `OSError` 文字會包含暫存路徑（例如 `[WinError 32] ...: '...\Alpha.dep' -> '...\.Alpha.dep.k2j1.tmp'`），以既有的 `Failed to save document: {error}` 範本顯示。

**D5. 檔案操作的接縫：注入，而非 patch。** 此流程使用的五個基本操作（`exists`、`write`、`replace`、`remove` 與 `temporary_path`）放在一個小類別 `PackageFiles` 上，內含真正的實作。`move_document_package(..., files=...)` 接收它，`DocumentWorkspaceService.__init__` 接受選用的關鍵字參數 `package_files: PackageFiles | None = None`（預設 `PackageFiles()`）。測試傳入不分大小寫的模型（見測試計畫）或注入錯誤的子類別。採用注入而不是 `mock.patch` 模組全域名稱，因為 `documents` 在 `wx_stub` 的 restore roots 中：patch `sys.modules` 裡的 `documents.workspace` 的測試，可能碰不到 service 實際呼叫的那個模組物件。沒有任何 `isinstance` 檢查；任何具備這五個方法的物件都可以。

**D6. 不納入已知 defect 3。** 讓所有重新命名都使用 `move_document_package` 可以修好 defect 3（移開失敗時只留下舊包，controller 不變）。但它無法在不做新決定的情況下順帶修好，所以不納入：
- 一般重新命名的錯誤文字會指名暫存路徑，而不是 `beta.dep`；
- Windows 上唯讀的包可以改名但不能刪除，所以今天的「unlink 失敗、顯示錯誤」會變成「改名成功、悄悄留下隱藏的 `.tmp` 檔」：要不要回報是 UX 選擇；
- 既有的錯誤注入方式（以非空目錄當作包）可以被改名，所以兩個 defect-3 測試需要重新設計，而不只是翻轉。

因此一般（非只改大小寫）的重新命名逐字保留今天的程式路徑，兩個 defect-3 的 `KNOWN BUG` 測試維持原樣。後續任務在做出上述選擇後，只要一行就能把一般重新命名切換到 `move_document_package`。

**D7. service 層不另加重複檢查。** GUI 的名稱詢問仍是新增與重新命名的唯一關卡，與今天的完全重名相同。`create_document` 與 `rename_document` 不重新檢查名稱（`gui.py` 不需要處理新的例外路徑）。

**D8. casefold 以外的別名不在範圍內。** NTFS 以其 upcase 表比較，APFS 也忽略 Unicode 正規化，所以有少數名稱組合在磁碟上衝突卻不是 casefold 相等（例如 macOS 上 NFC 的 `é` 與 NFD 的 `e` + `U+0301`、NTFS 上土耳其文的 `ı` 與 `i`）。要攔下這些需要對磁碟做檢查（因為某個檔案已解析到該處而拒絕名稱），那是另一個決定；列為後續。本程式的名稱多為中文，中文沒有大小寫。

## 各檔設計

### `client/documents/session.py`（tab）

`document_name_exists`：與 `name` 的比較改用 casefold；`document.name != exclude_name` 維持完全相等。檔案其他部分不變。

### `client/documents/workspace.py`（4 空格）

加入 `import os` 與 `import tempfile`，並在 `save_document_package` 之後新增：

- `class PackageFiles`，方法有 `exists(path) -> bool`（`Path(path).exists()`）、`write(path, document) -> None`（`save_document_package(path, document)`）、`replace(source, destination) -> None`（`os.replace`）、`remove(path) -> None`（`Path(path).unlink(missing_ok=True)`），以及 `temporary_path(directory, name) -> Path`（先建立目錄，再用 D4 的 `NamedTemporaryFile` 模式；回傳已關閉檔案的路徑）。
- `move_document_package(old_path, new_path, document, *, files: PackageFiles) -> None`，實作 D4 的第 1–4 步。docstring 說明保證：正常返回時包只存在於 `new_path`（拼寫完全相同）且內容為 `document`；拋出例外時舊包回到 `old_path`，拼寫與位元組都不變，且不留下暫存檔，除非還原本身失敗（見「風險」）。

`save_document_package`、`load_document_package` 及其他所有函式維持原樣。

### `client/documents/workspace_service.py`（4 空格）

- `__init__(self, controller, workspace_dir, *, package_files: PackageFiles | None = None)`；儲存 `package_files or PackageFiles()`。
- `rename_document`：在既有的相同名稱檢查與來源查找之後，若 `source_name.casefold() == new_name.casefold()`，呼叫 `move_document_package(self.package_path(source_name), self.package_path(new_name), Document(new_name, source.text, source.braille), files=self._package_files)`，再呼叫 `self._controller.rename_document(...)`。否則原樣執行今天的程式行。
- 模組 docstring：補充只改大小寫的重新命名會先暫存新包、把舊包移開，再安裝（D4），其他重新命名仍是先寫新包再刪舊包。

### `client/documents/controller.py`、`client/gui.py`

程式不變。controller 委派給 `session.document_name_exists`；GUI 已會在重複時重新詢問，並把只改大小寫的名稱交給 service。

## 維持不變的部分

- 完全重名的新增／重新命名（訊息、預填、重新詢問）、取消、名稱未變的重新命名。
- 一般重新命名：順序、檔案、controller 更新、寫入失敗與 unlink 失敗的行為（defect 3 仍被釘住）。
- 儲存、匯入（本來就是 casefold）、刪除、全部刪除、啟動載入與無效檔案對話框。
- 包格式、載入器的完全名稱檢查，以及所有使用者可見字串（msgid 353，集合相同）。
- 只改大小寫的重新命名時，`controller.rename_document` 移動開啟／選取名稱與 dual-view 快取的方式與任何重新命名相同。

## 測試計畫

所有新測試程式碼使用 4 空格（受影響的測試檔都是 4 空格）。

### A. 不分大小寫的檔案模型（新檔 `client/tests/case_insensitive_package_files.py`，不是測試模組）

`CaseInsensitivePackageFiles(PackageFiles)` 在真實的暫存目錄上運作，並針對傳入的路徑模擬不分大小寫、保留大小寫的檔案系統（NTFS／APFS）。路徑若在同一目錄中有 casefold 相等的既有項目，就解析到該項目。

- `exists`／`write`／`remove`：作用在解析後的項目上。`Alpha.dep` 存在時寫入 `alpha.dep`，會重寫 `Alpha.dep` 並保留其拼寫。
- `replace(source, destination)`：兩者解析到同一項目時，把該項目改名為 destination 的拼寫（`MoveFileEx`／`rename(2)` 對只改大小寫的改名所做的事）；destination 解析到另一個既有項目時，取代該項目的內容並保留其拼寫（悲觀解讀）；否則就是一般的 `os.replace`。建構子旗標 `replace_keeps_existing_spelling=True` 讓測試也能跑另一種解讀（以 destination 拼寫為準），藉此證明流程不依賴它。
- `temporary_path`：繼承（唯一的真實名稱）。

### B. 模型自我測試（新檔 `client/tests/test_case_insensitive_package_files.py`）

1. 寫入大小寫變體會重寫既有項目並保留其拼寫；之後 `load_workspace_documents` 把它列為無效（defect 2 的機制）。
2. 透過模型執行今天的重新命名流程（`write(new)`，因 `exists(old)` 再 `remove(old)`）會留下空目錄（defect 1 的情境，保留為舊失敗的回歸紀錄）。
3. 把項目 `replace` 到自己的大小寫變體會把它改名。
4. 在模型上執行 `move_document_package`，只改大小寫 `Alpha` 改 `alpha`，`replace_keeps_existing_spelling` 兩種值各跑一次（subTest）：列表正好是 `["alpha.dep"]`，成員 `alpha.brl`／`alpha.txt`，`load_document_package` 回傳該文件。

### C. 真實檔案系統上的 `move_document_package`（`client/tests/test_document_workspace.py`）

5. 只改大小寫 `Alpha` 改 `alpha`：列表 `["alpha.dep"]`，內容與成員正確。
6. 不同名稱（`alpha` 改 `gamma`）：列表 `["gamma.dep"]`。
7. 舊包不存在且工作區目錄不存在：目錄被建立，寫入 `alpha.dep`。
8. 點字待轉換（`braille=None`）：有 `alpha.meta.json`，載入後 `braille=None`。
9. 暫存寫入以 `OSError` 失敗（注入錯誤的 `PackageFiles` 子類別）：拋出；舊包位元組不變；沒有殘留 `.tmp`。
10. 暫存寫入以非 `OSError` 失敗（`Document("alpha", "\ud800", "1")` 造成 `UnicodeEncodeError`）：結果相同。
11. 移開失敗：拋出；舊包不變；沒有殘留 `.tmp`。
12. 安裝失敗：拋出；`Alpha.dep` 以原拼寫與位元組回來；沒有殘留 `.tmp`。
13. 清理失敗：不拋例外；`alpha.dep` 正確；殘留的是 `.tmp` 檔，`load_workspace_documents` 只回傳 `alpha` 且沒有無效路徑。
14. `PackageFiles().temporary_path` 會建立不存在的目錄，並回傳不符合 `*.dep` 的隱藏 `.tmp` 名稱。

### D. 重複檢查（`client/tests/test_document_controller.py`）

15. 把 `test_document_name_exists_is_exact_and_honours_exclude` 翻轉為 `test_document_name_exists_ignores_case_and_honours_exact_exclude`：現在找得到 `"Beta"`；`exclude_name="beta"` 時找不到 `"BETA"`（自己只改大小寫）；`exclude_name="beta"` 時找得到 `"zoo"`；同時持有 `Alpha` 與 `alpha` 的 controller 在 `exclude_name="Alpha"` 時找得到 `"ALPHA"`。（數量不變。）

### E. Service（`client/tests/test_workspace_service.py`）

16. 真實檔案系統上只改大小寫的重新命名會更新 controller（文件、開啟、選取、dual-view 鍵），且只留下 `alpha.dep`。
17. 以 `package_files=CaseInsensitivePackageFiles()` 只改大小寫的重新命名：在模型上結果相同（Linux 上代替 Windows 的驗證）。
18. 只改大小寫的重新命名在安裝時失敗：拋出；controller 狀態不變；`Alpha.dep` 完好。
19. 一般重新命名不會碰 `package_files`（傳入方法都丟 `AssertionError` 的物件）：改名成功，證明一般重新命名維持今天的路徑。兩個 defect-3 測試不變。

### F. GUI 流程（`client/tests/test_gui_document_flows.py`）

- 把兩個只改大小寫的重新命名測試合併為 `test_case_only_rename_keeps_the_document`，不 skip：列表正好是 `["alpha.dep"]`，`self._package("alpha") == Document("alpha", "a", "1")`，成員 `["alpha.brl", "alpha.txt"]`，controller 名稱 `["alpha"]`，事件 `[("DocumentNameDialog", "Rename Document", "Alpha"), ("title", "alpha - DotExpress")]`。註解說明它取代 `KNOWN BUG`（P1-3 known defect 1）測試、由 F-1 修正，並在主機的真實檔案系統上執行（Windows／macOS 上不分大小寫）。
- 把兩個新增大小寫變體的測試合併為 `test_add_case_variant_is_refused_as_a_duplicate`，不 skip：`self.names = ["Alpha", None]`；事件：新增對話框、`Document "Alpha" already exists.` 錯誤框（標題 `Error`、`wx.OK | wx.ICON_ERROR`、parent 為 frame）、以 `Alpha` 預填的新增對話框；列表 `["alpha.dep"]`；`alpha.dep` 內容與成員不變；controller 名稱 `["alpha"]`。註解：取代 defect-2 的 `KNOWN BUG` 測試。
- 20. 新增 `test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document`：frame 的 service 以 `CaseInsensitivePackageFiles()` 建立；斷言與合併後的重新命名測試相同。
- 21. 新增 `test_rename_to_a_case_variant_of_another_document_is_refused`：`alpha` 與 `beta` 存在，重新命名 `beta`，`self.names = ["Alpha", None]`；錯誤框指名 `Alpha`；對話框以 `Alpha` 預填重新開啟；兩份包與 controller 狀態都不變。
- 移除已無人使用的 `_skip_unless_case_sensitive`。

淨數量：B 4、C 10、E 4、F 新增 2；D 與合併為一對一取代，但兩次合併使 4 個測試變成 2 個。總數 `1095 + 4 + 10 + 4 + 2 + 2 - 4 = 1113`。計畫可以修正確切數字，但必須說明差異。

**Skip。** 在 Linux 上兩個 `..._on_case_insensitive_file_system_...` 的 skip 會消失，因為合併後的測試在任何檔案系統上都會執行，而不分大小寫的行為由模型涵蓋：`skipped=7`（liblouis 測試）。在 Windows／macOS 上合併後的測試會在真實的不分大小寫檔案系統上執行。

## 遷移步驟（每一步一個綠燈 commit）

1. `fix:` 在 `documents/workspace.py` 新增 `PackageFiles` 與 `move_document_package`，附測試 C 5-14（先紅後綠）。此時還沒有人呼叫這個 helper。
2. `test:` 模型（A）及其自我測試 B 1-4。B 1-3 記錄舊的失敗情境；B 4 在模型上執行新 helper。
3. `fix:` casefold 的 `document_name_exists`（D1），翻轉 D 15、合併 F 中的新增測試，並加入 F 21（先紅）。
4. `fix:` `DocumentWorkspaceService.rename_document` 的只改大小寫分支與 `package_files` 參數（D3、D5），附 E 16-19、合併後的重新命名測試與 F 20（先紅）；移除 `_skip_unless_case_sensitive`。

每個 commit 結尾加上 brief 規定的 `Co-Authored-By` 行。沒有任何 commit 修改 `gui.py`、`.po`／`.mo`、fixture 或 `documents/controller.py`。

## 驗收條件

在所示路徑執行；`$SP`／`$PY` 同上。

1. `cd client && $PY -m unittest discover -s tests`：只有已知的 P2-5 失敗；`Ran 1113 tests`（或計畫中有說明理由的數字）；`skipped=7`。
2. `cd client && for s in $(seq 1 20); do $PY $SP/shuffle_harness.py $s; done`：每個 seed 都只回報 P2-5 失敗。
3. 聚焦：`cd client && $PY -m unittest tests.test_case_insensitive_package_files tests.test_document_workspace tests.test_document_controller tests.test_workspace_service tests.test_gui_document_flows -v` 通過，且 `tests.test_gui_document_flows` 沒有 skip。
4. 在 repo 根目錄，`$PY $SP/p12/tools/msgid_scan.py client` 回報 `source msgids: 353`，集合相同；`client/locales` 不變。
5. 兩個 fixture 的 sha256 不變。
6. App data：`$SP/p26impl/snap.sh` 的輸出在條件 1-2 前後相同。
7. `grep -rn "KNOWN BUG (P1-3 spec, known defect [12]" client/tests` 找不到任何結果；`grep -rn "KNOWN BUG (P1-3 spec, known defect 3" client/tests` 仍找到兩個未變的 defect-3 測試。
8. `git diff main --stat` 只動到 `client/documents/session.py`、`client/documents/workspace.py`、`client/documents/workspace_service.py`、測試計畫中列出的測試檔（含新模型與其測試模組），以及 spec 與 plan 檔。

## Windows 待驗證事項（此處無法執行）

- 在 Windows（可行的話也在 macOS）執行 `cd client && python -m unittest tests.test_gui_document_flows tests.test_workspace_service tests.test_document_workspace -v`：`test_case_only_rename_keeps_the_document` 與 `test_add_case_variant_is_refused_as_a_duplicate` 在真實的不分大小寫檔案系統上執行且必須通過；之後 `dir` 顯示小寫的 `alpha.dep`。
- 封裝版手動測試：建立 `Alpha`、輸入文字、改名為 `alpha`、重新啟動：文件仍在且內容完整，檔案總管顯示 `alpha.dep`。新增 `ALPHA`：出現重複錯誤，磁碟上沒有任何變化。把另一份文件改名為 `Alpha`：同上。
- 包被其他程式開啟時（例如壓縮工具）只改大小寫的重新命名：出現錯誤框，`Alpha` 仍在列表中，重新啟動後 `Alpha.dep` 不變。
- 既有、無關：`tests.test_dictionary_name_prompt ... test_case_only_rename_still_renames` 在不分大小寫的檔案系統上預期會 error（沒有 skip）；記錄結果。
- 沒有選單、對話框或字串變更：不需要截圖，也不需要執行 `generate-pot.bat`。

## 風險

- **在移開與安裝之間當機**（低）。若程序在 D4 第 2、3 步之間結束，該文件沒有任何 `.dep`；舊包在 `.Alpha.dep.<隨機>.tmp`，完整的新包在 `.alpha.dep.<隨機>.tmp`，都可以手動復原。時間窗只是兩個連續的同目錄改名。
- **還原失敗**（極低）。若安裝失敗且把舊包移回也失敗，會拋出原本的錯誤，舊包留在其 `.tmp` 檔中。復原方式相同。
- **清理失敗後殘留 `.tmp`**（低）。程式看不到；無害；只會因重複失敗而累積。
- **模型終究是模型。** 它編碼的是 NTFS／APFS 如何解析與保留名稱；D4 從不依賴有爭議的部分（取代到別名上），測試 B 4 兩種解讀都跑。真正的驗證是上面的 Windows 待驗證事項。
- **Linux 上的行為變更**（低，刻意）。在區分大小寫的檔案系統上，新增／重新命名為大小寫變體也會被拒絕（D1）。已同時含有兩種拼寫的舊 Linux 工作區仍可載入與使用；只有新的衝突會被拒絕。
- **Stub scope 的模組同一性。** 由注入（D5）解決；打亂順序的執行（條件 2）會檢查模組順序。

## 範圍外／後續

- **已知 defect 3**（重新命名時 unlink 失敗留下兩份包）：決定 D6 的問題後，把一般重新命名切換到 `move_document_package`；屆時翻轉它的兩個 `KNOWN BUG` 測試。
- **字典：** 在 Windows／macOS 上只改大小寫的重新命名會被拒絕；只有 Linux 允許大小寫變體；`resolve_selected_dictionary` 以完全相等比對已儲存的名稱。沒有資料遺失；需要另外的 UX 決定。
- **casefold 以外的別名**（D8），以及新增／重新命名悄悄覆寫一個在磁碟上但不在列表中的 `.dep`（使用者在啟動時選擇保留的無效包）：兩者都需要以磁碟為準的存在檢查。
- **全部匯出**時，若舊工作區同時有 `Alpha` 與 `alpha`，在 Windows 上 `Alpha.brl` 與 `alpha.brl` 會寫到同一個檔案；第二個會悄悄取代第一個（覆寫確認只列出匯出前已存在的檔案）。只有在區分大小寫的檔案系統上建立的工作區才會遇到。
