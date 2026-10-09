# F-4 保留不合法注音列審查記錄

- 日期：2026-10-09
- 範圍：`fix/f4-keep-invalid-bopomofo-rows` 的 `main..fix/f4-keep-invalid-bopomofo-rows`（`main` = `b793704`，含 P2-5 與 F-3；7 個 commit：`806a034` spec、`8a9e836` plan、`c908cb7` 釘住筆數、`9846dc7` 與 `7341e5d` 實作、`ca31ec8` GUI 結果、`d6785a3` merge main）。production diff `git diff main...fix/f4-keep-invalid-bopomofo-rows -- client`：6 個檔，+362／−37（`dictionaries/entries.py`、`dictionaries/entry_list_model.py` +89／−33；4 個測試檔 +273／−4）。
- 對照：`docs/superpowers/specs/2026-10-09-f4-keep-invalid-bopomofo-rows-design.md`（含 `_zh-TW.md`，含「Corrected after planning」與 Q1 refuse／Q2 no notice／Q3 conversion unchanged）、`docs/superpowers/plans/2026-10-09-f4-keep-invalid-bopomofo-rows.md`、`docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/auto-results.md` 與 `auto/`、`2026-10-09-05-f3-dep-atomic-write/review_task.md`（格式）、`2026-10-09-01-fix-data-loss/review_task.md`（F-2 字典安全、優先清單）、`2026-10-08-03-refactor-p2/review_task.md`（P2-2 Q2／Q4）、`2026-10-09-03-windows-verification/auto-results.md`（F-W11）、`AGENTS.md`。
- 審查方式：逐行讀 2 個 production 檔的 diff 與全文、4 個測試檔的 diff、`dialog.py` 的編輯器與字典管理段落、`conversion/text/dictionary_rules.py`（R3）；對編輯器的每個動作序列推演 `_rows`／`_visible` 的索引對應；在 Windows 11（NTFS，`D:`）上跑完整套件、焦點模組、3 個 shuffle seed；把每個實作 commit 的測試拿去跑其父 commit 的 production code（red-first 重放）；在 scratchpad 的 `client/` 副本上自套 20 個 mutant；以 4000 個隨機 CSV 對 `main` 的 loader 做差分與 round-trip／冪等／轉換規則比對；8 個手寫情境探針；稽核 `D:\dxtest\auto{23,24,25,29,35}-f4*.log` 六個 log、exe 雜湊與 PyInstaller toc（沒有重跑 GUI、沒有結束任何程序）。凡未能驗證的標為「推理」或「不確定」。
- 本記錄只寫檔，未 commit。

## 驗證（Windows 11 26200，`$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`，cwd `D:\workspace\DotExpress-f4\client`，`$SP` = session scratchpad）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| 完整套件 | `$PY -B -m unittest discover -s tests` | `Ran 1268 tests in 12.742s`, `FAILED (errors=1, skipped=7)`；唯一 error 為 `test_dictionary_name_prompt ... test_case_only_rename_still_renames`（F-W6，`FileExistsError: Dictionary 'Alpha' already exists.`）。與 spec「Corrected after planning」第 5 點、plan Expected Counts 的 case B 完全相同 |
| 焦點模組（驗收標準 2） | `$PY -B -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_conversion_text_dictionary_rules tests.test_translation_golden -v` | `Ran 202`, `OK`（plan 預期 187 → 202）；15 個新測試與翻轉後的 Q2 測試、trace 重放全部 `ok` |
| shuffle | `$PY -B $SP\f3review_tools\shuffle_harness.py 7 11 23` | 三個 seed 皆 `ran=1268 failures=0 errors=1 skipped=7 ['test_case_only_rename_still_renames']` |
| fixtures | `git show HEAD:client/tests/fixtures/dictionary_entries_trace.json \| sha256sum`；`... translation_golden.json` | `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`、`e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`，與要求相同 |
| 受限檔案（spec D9、Not changed） | `git diff main...HEAD --stat -- client/dialog.py client/gui.py client/conversion client/shared client/locales client/tests/fixtures client/dictionaries/manager.py client/dictionaries/presenter.py` | 空（merge 之後 `main...HEAD` 即 `main HEAD`，6 個檔都在 `dictionaries/` 與 `tests/`） |
| msgid | `$PY -I $SP\f3review_tools\msgid_scan.py D:\workspace\DotExpress-f4\client`；`grep -c '^msgid ' client/locales/zh_TW/LC_MESSAGES/dotexpress.po`；`git diff main...HEAD -- client ':!client/tests' \| grep -E '^\+.*\b(N_\|_)\('` | `source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c`（與 spec／plan 相同）；po 354（353 + header）；production diff 無新的 gettext 呼叫（grep exit 1） |
| 實作 = plan dry run | `git rev-parse <commit>:client`（7 個 commit）；`git show 7341e5d:<path> \| sha256sum`、`git show d6785a3:<path> \| sha256sum` | tree id `c609d363`（spec、plan）、`d5217df5`（Task 1）、`c57e1d9a`（Task 2）、`a64e34d8`（Task 3、Task 5）、`70cc470e`（Task 6 case B）與 plan Expected Counts 逐一相同；`entries.py` `662cc618…92c7`、`entry_list_model.py` `998ae4c6…efc0` 在 `7341e5d` 與 `d6785a3` 都與 plan Dry Run 相同 |
| merge 乾淨 | `git diff ca31ec8 d6785a3 -- client` vs `git diff $(git merge-base ca31ec8 main) main -- client`（去掉 `index` 行後 `diff`） | 兩者相同：merge 只帶入 `main` 的 F-3 變更（`shared/atomic_write.py`、`documents/*`、`gui.py` 與 F-3 測試），沒有衝突殘留；F-4 的 6 個檔在 merge 前後 byte-identical |
| py_compile | `$PY -B -m py_compile dictionaries/entries.py dictionaries/entry_list_model.py` | 通過 |
| red-first 重放 | 對每個實作 commit：`git archive <commit> client` 到 `$SP\f4review\red\t<n>`，再以 `git show <parent>:<production 檔>` 覆蓋，跑該 commit 的測試模組（`-B`） | Task 1（`c908cb7` 的 P1 於 `8a9e836`）：`Ran 28`, `OK`（spec 說明綠燈是設計：釘住既有行為）。Task 2（`9846dc7` 的 S1–S6 於 `c908cb7` 的 `entries.py`）：`Ran 1`, `FAILED (errors=1)`，`ImportError: cannot import name 'PreservedDictionaryRow'`。Task 3（`7341e5d` 的 M1–M5、E1–E3、Q2 翻轉、trace 於 `9846dc7` 的 `entry_list_model.py`）：`Ran 116`, `FAILED (failures=48, errors=2)`：trace 40 個 subtest、M1／M2／M5、E1／E2／E3、翻轉的 Q2 測試、M4 各 1 個 FAIL，M3 與 M4 各 1 個 ERROR（`AttributeError: ... 'rows'`）。各自換回自己的 production：`Ran 17`, `OK`／`Ran 161`, `OK`。與 spec Migration Steps 所述紅燈完全相同 |
| 自套 mutant（20 個） | `$PY -B $SP\f4review_tools\mutants.py $SP\f4review\client`（副本由 `git archive HEAD client` 建立，不在 repo 內；跑四個字典測試模組，`Ran 161`；每個 mutant 後還原並比對 bytes） | 18 個被抓到、2 個存活：`m13-remove-first-row-with-same-text`、`m17-duplicate-check-strips-preserved-text`（見第 4 節與 M-1、M-4）。還原後兩檔與 `HEAD` 相同 |
| 隨機差分 | `$PY -B -X utf8 $SP\f4review_tools\probes.py 4000`（副本內另放 `main` 的 `entries.py` 為 `entries_main.py`；隨機 header 順序／缺欄／多欄／空行／BOM／LF／引號／空白／不合法注音／第一聲尾空白） | 4000 個檔：`load_dictionary_entries` 與 `main` 的結果（text、braille、type 三元組）0 個不同；`load_dictionary_rows` → `save` → `load_dictionary_rows` 0 個不同；第二次寫出與第一次 byte-identical（冪等）0 個例外；**F-4 分支在確定後造成、而 `main` 不會造成的轉換規則變化：0 個**；分支造成的規則變化全部可歸因於「顯示列的 strip」（Q2 餘項）或「R3 本來就拒絕的 header」 |
| 情境探針 | `$PY -B -X utf8 $SP\f4review_tools\probes.py scenarios` | S-A～S-H，見第 1.4 節 |
| GUI 結果稽核 | 讀 `D:\dxtest\auto23-f4.log`、`auto24-f4.log`、`auto25-f4.log`、`auto29-f4.log`、`auto35-f4.log`、`auto35-f4-B.log`；`sha256sum D:\dxtest\N-f4\DotExpress.exe`；`sha256sum D:\dxtest\data\dict_badbopo.csv`；`grep` `client\build\DotExpress\PYZ-00.toc`、`Analysis-00.toc` | exe `41ef168a…ec69`，48,736,571 bytes，與 auto-results 相同；`dict_badbopo.csv` `c4324573…6eb4`；toc 中 `dictionaries.entries`、`dictionaries.entry_list_model`、`gui` 都指向 `D:\workspace\DotExpress-f4\client\`（98 處），指向主 checkout `workspace\DotExpress\client` 的為 0；六個 log 的每一行（列、`changed`、行數、sha、`mgr items`、訊息字串、`attrib`、`icacls`、轉換輸出 O1、`same as convert 1`、`35b add` 的錯誤訊息、`35c` 檔案內容、`35d`）都與 auto-results 逐字相符；沒有 `.try1` log，與「只執行一次」一致。本次沒有重跑 GUI、沒有結束任何程序 |
| app data | `git status --short`（worktree 與主 checkout）；`ls client/dictionary`（worktree） | worktree 空；主 checkout 只有既有的 `client2/`、`preprocessing/`、`testdata/`；worktree 沒有 `client/dictionary/`；審查全程沒有讀寫任何 checkout 的 `client/dictionary/` |
| 未執行 | merge 後 tree（`70cc470e`）的 packaged build 與 GUI（auto-results 的 build 是 `7341e5d`，見 M-5）；B 基線 exe 的雜湊沒有重算；POSIX-only 測試；實作者的 19 個 mutant 工具（未 commit，以本記錄的 20 個替代） | 標為未驗證 |

## 結論

**Ready。** F-W11 在目標平台上確實修掉：編輯器看不到的列（空白來源文字、不合法注音）由 `load_dictionary_rows` 以 `PreservedDictionaryRow` 原欄位（未 strip、type 未正規化、缺欄為 `""`）放回同一個 `_rows` 清單，`add`／`replace`／`remove`／篩選／選取都只碰 `DictionaryEntry`，確定時依檔案順序原樣寫回；`dict_badbopo.csv` 在單元測試、模型測試、對話框測試與 packaged build 上都逐位元組不變，刪掉所有可見列後仍留在原位，重新啟動後不變，轉換輸出不再因為按確定而改變。隱藏的判準與 `main` 完全相同（4000 個隨機檔 0 個差異），字典管理筆數語意不變，轉換程式碼不變且 F-4 沒有帶入任何 `main` 不會造成的規則變化。每一步 red-first 可重放；7 個 tree id 與 2 個檔案雜湊與 plan dry run 逐一相同；merge 只帶入 `main` 的 F-3；msgid 353 同集合；fixtures 不變；`dialog.py`／`gui.py`／`conversion/`／`shared/` 未動。沒有 Critical，沒有 Important；7 個 Minor 都不要求改 production code 才能合併（M-1、M-4 是測試缺口，M-2 是 P2-2 Q4 的既有怪癖碰上隱藏列的極端組合，M-3、M-7 是 spec 沒列的邊角行為，M-5、M-6 是驗證範圍的註記）。

## 1. 資料安全：編輯器每個動作序列的推演

### 1.1 索引對應（`client/dictionaries/entry_list_model.py`）

模型只有一份有序清單 `_rows`（`:61`）；`_entries` 是 property（`:74-76`，每次重算 `[row for row in _rows if isinstance(row, DictionaryEntry)]`），`_visible` 由 `_refilter`（`:158-162`）從 `_entries` 重建，所以 `_visible` 裡的物件就是 `_rows` 裡的同一批物件。對話框每次都重新讀取 list control 的選取（`dialog.py:415-419` `_get_selected_index`，以 `visible_count` 夾住）再傳入可見索引，模型以 `_visible_at`（`:153-156`）取出物件後：

- `replace`（`:138-145`）以**身分**在 `_rows` 找 `current_entry` 的位置就地換掉：隱藏列與其他列的位置都不動（M3；mutant `m14` 改成等值比對被 3 個既有測試抓到）。
- `remove`（`:147-151`）`_rows.remove(current_entry)` 以**等值**刪掉第一個相等的列。`PreservedDictionaryRow` 是另一個 frozen dataclass，`__eq__` 對不同類別回 `NotImplemented`，兩邊都 `NotImplemented` 後退回身分比較 → 永遠 `False`（S6 釘住；mutant `m10` 加上跨類別 `__eq__` 被 S6 抓到）。所以隱藏列不可能被 `remove` 刪到。既有的 Q4 怪癖（相同列刪第一個）保留，見 M-2。
- `add`（`:128-136`）`_rows.append`：新列在檔尾，位於尾端隱藏列之後（M2；mutant `m12` 插在最後一個 entry 之後被 M2 抓到）。
- `apply_filter`／`_selection_after`（`:164-173`）只在 `_visible` 上以等值找回選取；隱藏列不在 `_visible`，不可能被選到。
- 沒有排序功能（`dialog.py` 無 `sort`／`SortItems`），所以沒有可見順序與檔案順序分離的路徑。
- 沒有 stale index：每個動作後 `_refilter` 重建 `_visible`，對話框 `_render` 以回傳的 `selection` 重設選取；刪除後再動作時索引是重新讀的。

序列推演（都在 `_rows = [A, H1, B, H2]` 上，H 為隱藏列）：開啟→確定：寫 `A,H1,B,H2`（E1、S3、item 23／35a）。新增 C 再刪 C：`append` 後 `remove(C)` 刪的是同一物件（唯一相等）→ 回到 `A,H1,B,H2`。編輯 B（H 的鄰居）：就地換 → `A,H1,B',H2`（M3）。刪 A、刪 B：`H1,H2`（E2、item 35c）。全刪後新增 C：`H1,H2,C`。取消：不寫（P2-2 既有）。重開：`load_dictionary_rows` 重新分類，分類只看欄位，而寫回的欄位與讀到的相同，所以 H 仍是 H、entry 仍是 entry（隨機差分 round-trip 0 個差異）。重複檢查：`source_text_exists`（`:119-120`）在 `_rows` 上精確比對 `text`，隱藏列算在內（M4、E3、item 35b）。匯入／匯出／改名／刪除／建立（`dictionaries/manager.py`）是 `shutil.copyfile`／`Path.rename`／`unlink`／只寫 header，不解析列（item 35 匯入後逐位元組相同）；設定對話框只選名稱。字典管理筆數仍是 `len(load_dictionary_entries(...))`（`dialog.py:580`），即可見列數（P1、item 23／35c）。

### 1.2 寫回（`client/dictionaries/entries.py:112-128`）

同一個 `DictWriter`（excel dialect：`\r\n`、minimal quoting、`doublequote`），以 `row.text`／`row.braille`／`row.entry_type` 寫每一列，`PreservedDictionaryRow` 的三個欄位是 `csv.DictReader` 回傳的原值（`:85-91`，缺欄 `None` → `""`）。含逗號、引號、`\r\n` 的欄位會被引號包住並在讀回時還原（S1／S2 的 `"q,""x""","a\r\nb"`）；前後空白不會被引號包住、也不會被 `DictReader` 吃掉（`skipinitialspace=False`；S1 的 ` ㄉㄨˋ|ㄗ˙ `、`ㄇㄚ `）。BOM 丟掉、LF 變 CRLF、引號正規化（S4）是對每一列既有的行為（F-2 D2）。`write_text_atomically` 是 F-2／F-3 的原子寫入，失敗時原檔不變（item 25–29 在 N-f4 上與 N 相同）。

### 1.3 KNOWN BUG 餘項

`test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form` 的標記縮小到：顯示列的 text／braille 被 strip、未知 type 改寫成 `General`（加上 spec Out of Scope 列的 BOM、多餘欄位、超出 header 的欄位、換行、引號、header 順序）。隨機差分證實：分支在確定後造成的每一個轉換規則變化，`main` 也會造成，而且全部可歸因於顯示列的 strip 或 R3 本來就拒絕的 header，沒有 F-4 新造成的變化。

### 1.4 情境探針（`$SP\f4review_tools\probes.py scenarios`）

| # | 情境 | 結果 | 判定 |
| --- | --- | --- | --- |
| S-A | 隱藏列 `肚子 `（尾空白，不合法注音）；新增 `肚子` | 接受；檔案兩列都在；R3 規則 `肚子 ` 與 `肚子` 各一條 | 與 D5「原始未 strip 的文字」一致，兩條規則來源不同，不互相遮蔽；無測試釘住（M-4） |
| S-B | 隱藏列 `肚子,ㄉㄨˋ\|ㄗ˙,Bopomofo` + 可見列 `肚子,⠁,General`；只改可見列的點字 | `DuplicateEntryError("肚子")` | spec D5 已明寫的副作用（與 Q4 相同）；可刪不可編 |
| S-C | `a,⠁,General`／`a,ㄉ\|,Bopomofo`／`a,⠁,General`；刪可見索引 1 | 檔案變 `a,ㄉ\|,Bopomofo`／`a,⠁,General`；`a` 的轉換從 `⠁` 變成不合法列的 fallback | M-2 |
| S-D | header `foo,bar`，兩列資料 | 兩列都成為 `Preserved("", "", "")`，確定寫 `,,` 兩列（`main`：只剩 header） | M-3 |
| S-E | header 多 `note` 欄、資料列多一欄 | 多餘欄位丟掉，三欄原值保留 | spec D3 已列 |
| S-G | 只有 `\r` 的換行 | `DictReader` 正常分列，隱藏列保留 | 與 `main` 的分類一致（`main` 全丟） |
| S-H | 模型層 `add(DictionaryEntry("", ...))` 在有空白隱藏列時 | `DuplicateEntryError("")`；`add(" ")` 被接受 | 對話框先 strip 再驗證，走不到；M-7 |

## 2. 哪些列被隱藏

`_is_editable`（`entries.py:95-104`）是把舊迴圈的兩個 `continue` 分支原樣搬出：stripped text 為空 → 不顯示；正規化 type 為 `Bopomofo` 且 stripped braille 讓 `normalize_zhuyin_sequence` 拋任何 `Exception` → 不顯示。它經模組全域呼叫 `normalize_zhuyin_sequence`，`test_loads_only_rows_accepted_by_the_editor` 的 `patch("dictionaries.entries.normalize_zhuyin_sequence", ...)` 仍有效（套件綠）。不合法 Unicode 點字列仍顯示（`test_load_preserves_invalid_braille_rows`；mutant `m20` 改用 `validate_dictionary_entry` 被它抓到）。`load_dictionary_entries` 是 `isinstance` 過濾（`:107-109`；mutant `m08` 回傳全部被 4 個測試抓到）。4000 個隨機檔（含小寫 `bopomofo`、`Custom`、空 type、缺 type 欄、header 重排、多欄、空行、`\r`、BOM）與 `main` 的 `load_dictionary_entries` 0 個差異：沒有任何可見列變隱藏，也沒有隱藏列變可見。完全空白的行由 `DictReader` 自己略過，與 `main` 相同（spec D1 已列為 not in scope）；`,`／`,,` 這類「有欄位但全空」的行現在保留為 `,,`，`main` 會丟掉（spec D1「blank source text」範圍內）。

## 3. 行為保持

- 字典管理筆數：`_load_dictionary_counts` 未改；P1 與 item 23／35 證實 `dict_badbopo` 顯示 `1`，刪掉臺北後 `0`。
- 轉換：`client/conversion/` 無 diff；S5 與 item 35a 證實確定前後 R3 規則相同；隨機差分證實沒有 F-4 新造成的規則變化。R3（`dictionary_rules.py:169-197`）仍用未 strip 的 `text` 當來源、對不合法注音走 fallback（Q3）。
- msgid 353 同集合；`dialog.py`、`gui.py` 在 F-4 的 commit 裡無 diff（`gui.py` 的變更全來自 merge 帶入的 F-3）。
- 模型公開介面（`entries`、`visible_entries`、`visible_count`、`cell_text`、`add`、`replace`、`remove`、`apply_filter`、`save`、`load`）語意不變；新增 `rows` 只給測試用；沒有其他模組讀 `_entries`（`grep` 無結果）。

## 4. 測試品質

- red-first：三步都可重放（驗證表）。Task 1 的 P1 在父 commit 上是綠的，與 spec「Green before and after (D6)」一致——它是釘住既有語意的測試，不是行為測試。
- 20 個 mutant：18 個被抓到。存活的兩個：
  - `m13`：`remove` 改成「刪第一個 `text` 相同的列」（含隱藏列）→ 161 個測試全綠。沒有任何測試讓「要刪的可見列」與某個隱藏列同來源文字（S-B 的檔案只測了編輯）。實作本身正確（`list.remove` 的等值永遠不會命中隱藏列，S6 守住），但這條「刪可見列不得刪到同名隱藏列」的性質沒有直接釘住。→ M-1。
  - `m17`：`source_text_exists` 改成 `row.text.strip() == text` → 全綠。D5「原始未 strip 的文字」沒有測試區分。→ M-4。
- Golden trace 判準：移除的只有兩個字面上整行相等的列（`,⠃,General`、`zz,ab,Bopomofo`），比對前先斷言它們恰好各出現一次、順序不變；trace 的文字池（`a`、`A`、`ab`、`Ab`、`Straße`、`STRASSE`、`b`、`ss`、`n<i>`）與點字池不可能產生與這兩行相同的可見列，也沒有動作能新增 `zz` 或空白來源文字，所以 D5 不會在 trace 裡出現、1,040 個每步觀測原樣比對（red-first：少了修正時 40 個 subtest 全紅；mutant `m06` 不寫隱藏列、`m15`／`m16` 隱藏列進可見清單都被 trace 抓到）。判準對隱藏列的**位置**是盲的：`m07`（隱藏列全部寫到檔尾）只被 S2、M5 與翻轉後的 Q2 測試抓到，trace 仍綠；spec G 已明寫「Exact positions are pinned by S and M, not by the trace」。→ M-6（無需動作）。
- fixture 未重新產生（sha256 相同）；`write_trace_fixture` 未改。

## 5. GUI 結果稽核

六個 log 與 auto-results 逐字相符（驗證表）。exe 來自 `7341e5d`（tree `a64e34d8`）的 build，toc 證實模組來自 `DotExpress-f4\client`。item 23 的 dict23 sha `ef319c2140b1465e` 與 2026-10-09-03 相同，證明沒有隱藏列的檔案寫出的 bytes 不變；item 24–29 與 N 相同，證明 F-2 的寫入路徑沒有退化。item 35 的 B 對照（4 行→2 行、第二次轉換不同、新增被接受）正是 F-W11 的基線。沒有需要重跑的跡象。

## 6. 與 F-3、P2-5 的互動

- F-3：F-4 只依賴 `write_text_atomically(path, write, encoding="utf-8", newline="")`。merge 後它變成 `ensure_writable` + `_write_atomically(mode="w", ...)` 的薄包裝（`client/shared/atomic_write.py:93-106`），簽章與行為不變；merge 後的 1268 個測試（含字典儲存失敗路徑的對話框測試與 `test_atomic_write` 的 15 個）全綠。GUI 的 build 是 merge 前的 tree，見 M-5。
- P2-5：只改 `gui.py` 的 import 與 conversion 契約，不碰字典模組；無互動。
- 兩者都沒有 F-4 之外的 `.csv` 寫入者（spec Writers 表仍正確）。

## 7. 文件正確性

- spec／plan 與實作：D1–D9、Design per File 的每一條都對得上程式碼；plan 的 7 個 tree id、2 個檔案雜湊、`Ran 146 → 161`／`187 → 202`、case B `Ran 1268` 都與實際相同。
- Q1–Q3 在 spec「Corrected after planning」第 1 點與 Open Questions 都標明「Decided by orchestrator with the recommended default; user may override before merge」，zh-TW 版同步。
- 已知缺陷：auto-results 結論與 spec Risks／Q2 都寫明隱藏列在編輯器看不到、筆數不含它們（35c／35d 顯示 `0` 但檔案仍有兩列）；重複訊息會指名一個看不到的列（Risks 第 2 點）。
- 小出入：spec D4「a preserved row keeps its neighbours except those the user deleted」在相同列跨越隱藏列時不精確（M-2）；D3 的正規化清單沒有涵蓋「header 缺少三欄之一時整列變成空欄位列」（M-3）；D5「Blank-text rows never collide」只在對話框層成立（M-7）。

## 8. 發現

### Critical

無。

### Important

無。

### Minor

- **M-1. 測試缺口：刪除可見列時「同來源文字的隱藏列不被刪」沒有直接釘住**（`client/tests/test_dictionary_entry_list_model.py` `PreservedRowsTest`，`:375-420`）。mutant `m13`（`remove` 改成刪第一個 `text` 相同的列）在 161 個測試上全綠。失敗情境：若日後有人把 `_rows.remove(current_entry)`（`entry_list_model.py:149`）改成依 `text` 找列，`肚子,ㄉㄨˋ|ㄗ˙,Bopomofo`（隱藏）＋`肚子,⠁,General`（可見）的檔案刪可見列會刪掉隱藏列。建議：在 `PreservedRowsTest` 加一個 `[alpha, kept(DUZI), _entry(DUZI, "\u2801")]` 的模型，`remove(1)` 後 `rows == (alpha, kept)`（這種狀態只能來自檔案，spec D5 已描述）。
- **M-2. Q4 的「刪第一個相等的列」碰上同來源文字的隱藏列會改變轉換結果**（`client/dictionaries/entry_list_model.py:149`）。情境 S-C：`a,⠁,General`／`a,ㄉ|,Bopomofo`／`a,⠁,General`，使用者選第二個可見的 `a` 按刪除 → 刪的是第一個 → 檔案變成隱藏列在前 → R3「第一條規則勝出」改用不合法列的 fallback；F-4 之前同一動作會留下 `a,⠁`（隱藏列被丟掉）。需要三列同來源文字、其中兩列完全相同，極端但由 F-4 新引入。建議：隨 P2-2 Q4 一起改成與 `replace` 相同的身分刪除（會翻掉 `test_identical_rows_delete_removes_the_first_equal_row` 等釘住 Q4 的測試，所以不在 F-4 做）；本次至少在 spec D4 註明「keeps its neighbours」在相同列跨越隱藏列時不精確。
- **M-3. header 缺少 `text`（或三欄全缺）時，確定會寫出每列 `,,`**（`client/dictionaries/entries.py:85-91`）。情境 S-D：`foo,bar` 兩列資料 → `main` 寫出只有 header，F-4 寫出 `text,braille,type` + `,,` ×2。沒有資料損失（這種檔案對 R1 沒有可用列、R3 在確定前就拒絕、確定後空來源被略過，與 `main` 相同），但不在 spec D3 的正規化清單裡。建議：在 spec Out of Scope／D3 記一句，或在 `load_dictionary_rows` 對 `reader.fieldnames` 不含任何一欄的檔案維持舊行為（不保留）。
- **M-4. D5 的「原始未 strip 文字」比對沒有測試區分**（`client/dictionaries/entry_list_model.py:119-120`）。mutant `m17`（`row.text.strip() == text`）全綠。情境 S-A：隱藏列 `肚子 `（尾空白）不會擋下新增 `肚子`，兩條 R3 規則來源不同、互不遮蔽，所以現行為是對的；但 Q1「拒絕」的範圍（精確比對、含空白）沒有被釘住，也沒寫在模型 docstring 的比較規則裡。建議：`PreservedRowsTest` 加一個隱藏 `DUZI + " "`、新增 `DUZI` 被接受且 `rows` 為 `(…, kept, new)` 的測試，並在 docstring 的 duplicate 規則加「preserved rows compare their raw, unstripped text」。
- **M-5. GUI 驗證的 build 是 merge 前的 `7341e5d`，不是最終的 `d6785a3`**（auto-results §0.1）。merge 帶入 F-3 對 `write_text_atomically` 的重構（`client/shared/atomic_write.py:93-106`），字典的確定現在經由 `_write_atomically`。推理：簽章與行為不變，merge 後套件（含字典儲存失敗路徑與 `test_atomic_write`）全綠，F-3 自己的 GUI item 30–33 已在 packaged build 上驅動同一核心；風險低，本次不重跑。建議：若要零推理，在發佈前用 `d6785a3` 的 build 重跑 item 23 與 35（約 2 分鐘）。
- **M-6. Golden trace 的判準對隱藏列位置是盲的**（`client/tests/test_dictionary_entries_dialog.py:1646-1649`）。mutant `m07`（隱藏列寫到檔尾）只被 S2、M5 與翻轉的 Q2 測試抓到，trace 仍綠。spec G 已明寫，位置由 S／M 釘住；無需動作，只提醒不要把 trace 單獨當成位置的證據。
- **M-7. 模型層 `add` 空白來源文字會被當成隱藏空白列的重複**（`client/dictionaries/entry_list_model.py:128-130`）。情境 S-H：`_rows` 含 `Preserved("", …)` 時 `add(DictionaryEntry("", …))` 拋 `DuplicateEntryError("")`，訊息會是「來源文字「」已存在。」。對話框先 strip 再 `validate_dictionary_entry`（`dialog.py:101-104`），走不到；spec D5「Blank-text rows never collide」只在對話框層成立。建議：`source_text_exists` 對空 `text` 直接回 `False`，或在 docstring 註明模型假設呼叫端已驗證。

## 9. 審查用的工具（未 commit，在 `$SP\f4review_tools\`）

- `mutants.py`：20 個 mutant（m01–m20），對 `$SP\f4review\client` 副本逐一套用、跑四個字典測試模組、還原並比對 bytes。
- `probes.py`：`scenarios`（S-A～S-H）與 `differential <seeds>`（隨機 CSV 對 `main` 的 loader、round-trip、冪等、R3 規則差分）。
- `shuffle_harness.py`、`msgid_scan.py`：沿用 F-3 審查的工具。

## 修正記錄

- 日期：2026-10-09，由 Claude 執行；分支 `fix/f4-keep-invalid-bopomofo-rows`，起點 `d6785a3`。沒有 merge 進 `main`、沒有 push；主 checkout `D:\workspace\DotExpress` 未修改；沒有讀寫任何 checkout 的 `client/dictionary/`。

| 發現 | 處理 |
| --- | --- |
| M-1 | `2d644ca`：`PreservedRowsTest.test_remove_of_an_entry_leaves_a_preserved_row_with_the_same_source_text`，模型 `[alpha, kept(DUZI), _entry(DUZI, "\u2801")]`，`remove(1)` 回 `EntryListUpdate(0)`、`rows` 為 `(alpha, kept)`（同一物件）。現行程式碼綠；mutant `m13-remove-first-row-with-same-text` 被它抓到（見下） |
| M-2 | 未處理程式碼（改成以身分刪除會翻掉釘住 P2-2 Q4 的測試；建議隨 P2-2 Q4 的 identity remove 一起改）。`b8baf2b`：spec D4（EN／zh-TW）註明「keeps its neighbours」在相同列跨越同來源隱藏列時不精確（S-C 情境、轉換改走 fallback、F-4 之前是確定時刪掉隱藏列），範圍外清單的 P2-2 Q4 項目註明它也會修掉這一處 |
| M-3 | `b8baf2b`：spec D3（EN／zh-TW）記一句：header 沒有 `text` 欄（或三欄都沒有）時每個資料列成為三欄皆空的保留列、確定寫回 `,,` 行（F-4 之前只寫 header），不會失去規則（R3 本來就拒絕這種 header、略過空白來源文字）。行為不變 |
| M-4 | `2d644ca`：`PreservedRowsTest.test_a_preserved_row_blocks_only_its_raw_unstripped_source_text`，隱藏 `PreservedDictionaryRow(DUZI + " ", INVALID_DUZI, "Bopomofo")` 不擋新增 `DUZI`，`add` 回 `EntryListUpdate(1)`、`rows` 為 `(alpha, spaced, valid)`；`entry_list_model.py` 的 `source_text_exists` 加 docstring：「Preserved rows compare their raw, unstripped text (the source R3 uses), so a hidden `"x "` does not block `"x"`」。現行程式碼綠；mutant `m17-duplicate-check-strips-preserved-text` 被它抓到 |
| M-5 | 已重跑：以 `b8baf2b`（`HEAD:client` `f244bb8e70a42ce08c98d3145f5c806f9818ac32`，含 merge 帶入的 F-3 與本次兩個 commit）重新 build，item 23（只跑 N 端）與 item 35 結果與 auto-results 相同（見下） |
| M-6 | 不處理（無需動作；spec G 已寫明位置由 S／M 釘住） |
| M-7 | `b8baf2b`：不改行為。`source_text_exists` 的 docstring 註明呼叫端傳入已驗證的項目、空 `text` 會撞到保留的空白來源文字列、但對話框先 strip 並要求來源文字所以 UI 走不到；spec D5（EN／zh-TW）把「Blank-text rows never collide」限定為「經由對話框」，並註明模型層的情況 |

### Mutant（M-1、M-4）

`git archive HEAD client`（`d6785a3`）到 `$SP\f4fix\client`，再以本次修改後的 `dictionaries/entry_list_model.py`、`tests/test_dictionary_entry_list_model.py` 覆蓋（與 worktree `cmp` 相同），以審查者的 `$SP\f4review_tools\mutants.py`（`-B`，四個字典測試模組，每個 mutant 後還原並比對 bytes）只套兩個存活的 mutant：

```text
m13-remove-first-row-with-same-text: CAUGHT Ran 163 tests FAILED (failures=1) ['test_remove_of_an_entry_leaves_a_preserved_row_with_the_same_source_text']
m17-duplicate-check-strips-preserved-text: CAUGHT Ran 163 tests FAILED (errors=1) ['test_a_preserved_row_blocks_only_its_raw_unstripped_source_text']
```

還原後副本的四個模組 `OK`（`Ran 163` = 161 + 2）。

### Merge 後 tree 的 packaged build 與 GUI（M-5）

| 項目 | 結果 |
| --- | --- |
| Build | worktree `HEAD` `b8baf2b`，主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` = `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`），`scripts\build-dotexpress.bat` 約 64 秒，log 有 `Build complete!`。`PYZ-00.toc` 的 `dictionaries\entries.py`、`dictionaries\entry_list_model.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress-f4\client\`；兩個 toc 中主 checkout `workspace\DotExpress\client\` 下 `.venv` 以外的路徑 0 處。`D:\dxtest\N-f4m\DotExpress.exe`，48,738,628 bytes，sha256 `D8FEDB2364275F6E85C3FB9816D7D0BD5253DD2C71DE2F8EB0FEA57342BC039B`。`git status` 只有本檔 |
| 23（N 端） | 以 scratch wrapper（`$SP\f4fix\rerun23_f4m.py`：import 已 commit 的 `auto/rerun.py`，只在記憶體中把 `REPLACE["item23.py"]` 換成 `("N-f4m",)` 與 `auto23-f4m-{v}`；`--check` 確認替換）執行未修改的 `item23.py`，資料夾 `D:\dxtest\auto23-f4m-N-f4m`，log `D:\dxtest\auto23-f4m.log`。`dict23`：6 列、確定 `([], False)`、`changed: True lines 7 -> 7 bom: False crlf: True sha ef319c2140b1465e`；`dict_badbopo`：列 `[['臺北', '⠞⠺', 'Unicode 點字']]`、確定 `([], False)`、`changed: False lines 4 -> 4 bom: False crlf: True sha c432457361b0997a`；`mgr items` `[['default', '0'], ['dict23', '6'], ['dict_badbopo', '1']]`；`close: exited`。去掉版本標籤後與 `auto23-f4.log` 的 N-f4 行逐字相同 |
| 35 | `auto/item35.py D:\dxtest\N-f4m\DotExpress.exe D:\dxtest\auto35-f4m`（腳本本來就接受 exe 與資料夾參數），log `D:\dxtest\auto35-f4m.log`：來源 sha256 `c4324573…6eb4` 4 行；匯入相同、筆數 1；O1 與 35a 轉換 2 相同（`True`）；35a 檔案相同、4 行、無 `.tmp`；35b `來源文字「肚子」已存在。`、檔案相同；35c 列 `[]`、檔案為 header 加兩列注音（`True`）、筆數 0；35d 筆數 0、列 `[]`、檔案不變；兩次 `close: exited`。與 `auto35-f4.log` 以 `diff` 比對完全相同 |
| 程序 | 只由 `dx.launch` 結束 exe 位於 `auto23-f4m-N-f4m`、`auto35-f4m` 下的程序；執行後沒有殘留的 DotExpress 程序。每個項目只執行一次 |

### 最終驗證（`$PY -B`，cwd `D:\workspace\DotExpress-f4\client`）

- 完整套件 `$PY -B -m unittest discover -s tests`：`Ran 1270 tests in 14.979s`，`FAILED (errors=1, skipped=7)`；唯一 error 為 F-W6 `test_case_only_rename_still_renames`（1268 + 本次 2 個）。
- fixtures：`translation_golden.json` `e67d95a1…1ccd`、`dictionary_entries_trace.json` `f493da52…c2cf`，不變。
- msgid：`source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c`，不變（docstring 不是使用者字串）。
- `git diff main HEAD -- client/conversion client/dialog.py client/gui.py client/locales client/tests/fixtures`：空。`git diff d6785a3 HEAD --stat`：`entry_list_model.py`（只有 docstring）、`test_dictionary_entry_list_model.py`、spec 兩個語言版。
