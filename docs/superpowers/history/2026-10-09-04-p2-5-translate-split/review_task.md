# P2-5 `translate.py` 拆分審查記錄

- 日期：2026-10-09
- 範圍：`refactor/p2-5-translate-split` 的 `main..refactor/p2-5-translate-split`（`main` = `d4a7aa1`；13 個 commit：`079d58b` spec、`355680f` plan、`f0e3b5a..02a9171` 實作 10 個、`e039aa4` 實作記錄）
- 對照：`docs/superpowers/specs/2026-10-09-p2-5-translate-split-design.md`（含 `_zh-TW.md`，含「Corrected after planning」）、`docs/superpowers/plans/2026-10-09-p2-5-translate-split.md`（含 Implementation Notes）、`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md`（缺陷清單、P2-5 readiness 一節）、`docs/superpowers/history/2026-10-09-03-windows-verification/results.md` §3 與 `auto-results.md`、`AGENTS.md`。
- 審查方式：把 `git show main:client/translate.py` 與 `conversion/{tokenizer,line_wrap,alignment,contracts}.py` 逐行並排讀（另以 script 列出三個新模組中不在舊檔的 175 行，逐行確認是預期變更）；對兩個線性演算法做手寫的等價論證，再以自己寫的差分 fuzz（生成器比 repo 內的更刁鑽）跑 180,000 個狀態 × 6 個操作 + 180,000 條完整鏈；在 Windows 上跑完整套件、P2-5 模組組、Windows-only 模組、`p25_baseline.py`／`p25_perf.py`；在 scratchpad 的 `client/` 副本上自套 12 個 mutant。Packaged build 只查 PyInstaller 的 `PYZ-00.toc`，沒有重建（`D:\dxtest\N-p25\DotExpress.exe` 已由實作者做過 GUI 檢查）。凡未能驗證的標為「推理」或「不確定」。
- 本記錄只寫檔，未 commit。

## 驗證（Windows 11，repo root 或 `client/`，`$PY` = `client\.venv\Scripts\python.exe`，`$SP` = session scratchpad `…\scratchpad\p25review`，`$H` = `docs\superpowers\history\2026-10-09-03-windows-verification`）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| 完整套件 | `cd client && $PY -m unittest discover -s tests` | `Ran 1208 tests in 13.496s`, `FAILED (errors=1, skipped=5)`；唯一 error 為 `test_case_only_rename_still_renames`（F-W6，既有）。與實作記錄相同；1143 → 1208 的 +65 可逐模組對帳（14+1+13+8+1+6+14+4+4） |
| P2-5 模組組（acceptance 2） | `cd client && $PY -m unittest tests.test_translation_result tests.test_translation_result_core tests.test_translation_golden tests.test_translation_split_equivalence tests.test_translation_liblouis_golden tests.test_conversion_tokenizer tests.test_conversion_line_wrap tests.test_conversion_service tests.test_translation_import_isolation -v` | `Ran 126`, `OK`；`test_translation_liblouis_golden` 13 個全部 `ok`、0 skip；各模組數：real golden 13、equivalence 8、tokenizer 14、line_wrap 4、`test_translation_result` 14、`_core` 28 |
| Windows-only 模組（acceptance 3） | `cd client && $PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation` | `Ran 7`, `OK` |
| 真 liblouis 基線 | `$PY $H\p25_baseline.py $SP\p25out`；`cmp` 兩個 `.brl` 與 `$H\baseline\` | A 三組 `identical=True`；B raw `['計','算',' ','1+2',' ','的','值']`；C unicode `365d28a9…f9d683c`、ascii `95b9a1a6…2538bc64`，`trims=13 cells_removed=13` 兩模式；`BRL identical` |
| 效能 | `$PY $H\p25_perf.py $SP\p25out 100 400 1600` | `chars=83200 translate=4.69s wrap=0.44s reclean=0.06s`（基線 28.92 s／28.55 s） |
| 差分 fuzz（自寫） | `cd client && $PY -I $SP\fuzz_diff.py 6 30000`（oracle = `tests/legacy_translation_result.py`） | 6 個 seed × 30,000 狀態 × {`reclean_braille_endspace`, `reclean_token`, `bind_word_tokens`, `bind_contracted_tokens`, `wrap`, `insert_token`} + 30,000 條 concat→trim→bind→reclean→wrap 鏈：四個 list、list identity、回傳值、例外型別與訊息全部相同。生成器含：第一個 token 前的 cell（`r2b[0]>0`）、大量零寬 token（含尾端 `== len(braille)`）、任意 `braille_to_raw_pos` 值（負數／`10**6`）、空 raw／空 braille、`""` token、shuffle／截短／加長的 map |
| 自套 mutant（12 個） | `$PY -I $SP\run_mutants.py $SP\mut\client $PY`（副本，不在 repo） | 12 個全部被抓到，0 個存活（表見第 4 節） |
| Fixture | `git show HEAD:client/tests/fixtures/translation_golden.json \| sha256sum` 等 | `e67d95a1…211ccd`、`f493da52…c66c2cf`，與 `main` 相同；`p25_doc.txt` 三份（fixture、history、HEAD blob）皆 `d287af56…5fa4a2` |
| 受限檔案 | `git diff --stat main..HEAD -- client/braille client/locales client/dictionary scripts client/DotExpress.spec README.md` | 空；`client/braille/tables/__init__.py` blob 相同，`git ls-files --eol` 為 `i/crlf w/crlf`，255 行 tab 縮排 |
| msgid | `grep -c '^msgid ' client/locales/zh_TW/LC_MESSAGES/dotexpress.po`（HEAD 與 main） | 354 = 353 source + header，不變 |
| 縮排 | Python 逐檔統計（`\t` 開頭行／四空白開頭行） | 新檔（三個 `conversion/*.py`、`contracts.py`、四個新測試）四空白，與 `conversion/service.py`、`output.py` 相同（spec D1 明寫）；`tests/test_translation_result.py` 保留 tab（203 行）；oracle 副本 tab 442 行；新檔 index 皆 LF |
| 匯入方向 | `git grep -nE "^\s*(from translate import\|import translate$)" -- client ':!client/tests' ':!client/translate.py'`；`git grep -n adapters -- client/conversion` | 皆空 |
| 搬移行審計 | script：三個新模組中（去縮排後）不在 `translate.py@d4a7aa1` 的行 | tokenizer 30、line_wrap 33、alignment 112，與 plan Task 11 Step 8 的數字相同；逐行讀過，全部是 docstring／import／hoist 常數／函式簽名與 return／兩個 fast path 與註解／`_regroup`／delegation |
| Packaged build | `client/build/DotExpress/PYZ-00.toc`（2026-10-09 20:15，與 `D:\dxtest\N-p25\DotExpress.exe` 同時間；exe sha256 `bdba718c…aec427` 與實作記錄相同） | 含 `conversion.alignment/contracts/line_wrap/tokenizer`、`adapters.translation.*`、`braille.*`；**不含 `translate`**（見 I-1） |
| 未執行 | 20 個 shuffle seed、實作者的 21 個 mutant 工具（未 commit，Appendix 有原始碼）、紅燈計時（42.6 s／19.9 s）、Dual View HTML 比對 | 標為未驗證；shuffle 與 mutant 以本記錄的 fuzz／mutant 替代 |

## 結論

**Ready。** 兩個線性演算法（`reclean_braille_endspace`、`reclean_token`）在我能構造的所有輸入上與 `d4a7aa1` 的程式逐位元組相同（含 list identity、例外型別與訊息、畸形 map 的 fallback），手寫論證與 180,000 組差分 fuzz 一致；真 liblouis 的 BRL 雜湊、13 次 trim、`p25_perf.py` 的 0.06 s 都重現；模組拆分沒有循環、沒有反向依賴、搬移的程式行逐一對得上；失敗測試的裁決有真 liblouis 證據支撐且特性測試確實釘住；12 個自套 mutant 全部被抓到。沒有 Critical。一個 Important（I-1）是 packaged build 不再附帶 `translate` 模組這件事 spec 沒寫、也沒有人決定，屬於「一行 hidden import 或一句文件」的決定，不阻擋合併；其餘為 Minor。

## 1. 行為保持：線性 trim 與線性 separator

### 1.1 `reclean_braille_endspace`（`client/conversion/alignment.py:250-295`）

fast path 條件 `_is_well_formed_alignment`（`alignment.py:11-21`）：`len(r2b)==len(raw)`、`len(b2r)==len(braille)`、`0 <= r2b[0] <= … <= r2b[-1] <= len(braille)`；其餘走 `_reclean_braille_endspace_stepwise`（`:297-335`，與舊碼逐字相同，含最後的 clamp 迴圈）。

論證（我自己推一次，與 spec D5 一致）：舊迴圈處理 token t 時，所有先前的刪除都落在 `[new_end_k, end_k)`、`k < t`，而 `r2b` 單調不減保證 `end_k <= r2b[t]`，所以 token t 的 start 與 end 都恰好左移了 `removed`，看到的 cell 就是原始的 `braille[start_t:end_t]`；每個 token 被 trim 的量只取決於自己的原始 cell，因此一次掃描累計位移的結果相同。零寬 token（`start == end`）兩邊都不動；單 cell 的純空白 token 兩邊都保留（`new_end - start > 1`）；第一個 start 之前的 cell 舊碼從不碰，新碼以 `braille[:first_start]` 保留。clamp：最後一個 token 的新 start `r2b[-1] - removed_before`，新長度 `len - removed_before - removed_last`，而 `removed_last <= len - r2b[-1] - 1`，所以 start 不可能超過新長度，略過 clamp 正確（spec Corrected 7）。identity：舊碼 `del` 就地、新碼 `lst[:] = new` 就地，三個 list 物件相同；`raw` 不動。沒有 trim 時舊碼不碰 list，新碼做一次內容相同的 slice assignment——物件相同、內容相同，呼叫端（`conversion/wrapping.py`、`p25_baseline.py` 的 counting wrapper）都只讀屬性，無差異。

邊界逐一跑過（fuzz 生成器刻意加權）：空 raw／空 braille／空 map（早退相同）；全空白 token；多 cell 尾端空白；`r2b` 比 raw 短（stepwise → 同一個 `IndexError`）；`b2r` 比 braille 長或短（stepwise，`del b2r[new_end:end]` 行為重現）；非單調 `r2b`（stepwise，重疊刪除重現）；`r2b[0] > 0`（fast path 保留前置 cell）。6 × 30,000 狀態無差異。

### 1.2 `reclean_token`（`alignment.py:193-248`）

`positions = list(iter_separator_positions(self.raw))`（`tokenizer.py:205-213`）先算：舊迴圈每插入一個 `" "` 就 `i += 1` 跳過它，所以檢查的正是原始相鄰 pair、各一次、依序——生成器等價。無 separator 時直接 return（四個 list 物件不變，與舊碼相同）；畸形 map 時以 `insert_token(index + offset, …)` 逐一插入，與舊碼在同一次插入拋同一個 `IndexError`（positions 對 str token 不會拋例外，spec Corrected 8）。

fast path 論證（我獨立推導，結論與 spec D6 一致）：
- 第 m 個 separator 在舊碼插在 token index `i_m + m`、cell index `r2b[i_m] + m`（每個更早的插入都在它之前，各把它的 start 推 1；`insert_token` 保持 `r2b` 單調，所以歸納成立）。
- `raw`／`raw_to_braille_pos`：原 token j 的 start 變成 `r2b[j] + #{m : i_m <= j}`——`insert_token` 以 token index 決定位移，不看 cell 位置，所以 start 相同的零寬 token（`j < i_m`、`r2b[j] == r2b[i_m]`）不位移；新碼的 `inserted` 計數正是 `#{m : i_m <= t_idx}`。
- `braille`：同一 cell 位置的多個 separator 保持插入順序（`while … separator_cells[inserted] <= b_idx`），`== len(braille)` 的尾端 separator 由最後的 `while inserted < count` 補上。
- `braille_to_raw_pos`：原 cell b（值 t，**t 可以是任意整數**，well-formed 檢查不看 b2r 的值）在第 m 步落在 `right` 的充要條件是 `r2b[i_m] <= b`（對 m 單調），再加 1 的條件是「目前值 >= i_m + m」——只要前面每一步都加過，這等於 `t >= i_m`，一旦失敗就永遠失敗（margin 每步至少掉 1）。兩個條件各是 m 的 prefix，交集是較短的 prefix，所以總增量 = `min(#{m : r2b[i_m] <= b}, #{m : i_m <= t})` = `min(inserted, bisect_right(positions, t))`。負數 t → 0；超大 t → `inserted`。
- identity：有 separator 時四個 list 都是新物件，與舊碼 `insert_token` 重新綁定相同。

### 1.3 其餘搬移

`bind_contracted_tokens`／`bind_word_tokens` 的 guard 順序與舊碼相同（先算 spans 再 guard），`_regroup` 的三個 list comprehension 與舊碼兩處的表達式逐字相同（含 `r2b` 比 spans 短時的 `IndexError`）；`insert_token` 原文不動；`wrap_tokens` 只有參數化、`SEPARATED_AFTER_PUNCT`／`SPACE_ONLY`（成員相同）與明確括號（`A and B or C and not D` → `(A and B) or (C and not D)`，優先序不變）。fuzz 中 `wrap` 有 27% 的 case 以 `IndexError` 結束（`""` token 的 `token[-1]`、或 fresh line 上零寬 token 的 `current_braille_parts[-1]`），兩邊例外型別與訊息相同——這是 spec Known Defect 2，不是本次引入。

## 2. 模組拆分正確性

- 依賴圖與 spec D1 相同：`tokenizer → languageDetection.unicode_blocks`；`line_wrap → tokenizer`（兩個常數）；`alignment → tokenizer, line_wrap`；`contracts → alignment`；`translate` → `alignment`（re-export，`__all__`）。`conversion/__init__.py` 為空，無循環。`adapters/translation/contracts.py` 只留 `RuntimeUnavailableError` 並 re-export 三個 port（同一物件，`__module__ == "conversion.contracts"`，有測試釘住）；`adapters/translation/__init__.py` 的匯出名單不變。
- 六個 `TranslationRuntime` 使用者（`conversion/{jobs,output,service,text/pipeline}.py`、`gui.py`、`ui/conversion_presenter.py`）改 import `conversion.contracts`；四個 `TranslationResult` 建構者（liblouis／mathcat／fallback adapter、`literal_braille.py`）與 `wrapping.py` 改 import `conversion.alignment`。`gui.py` 只改一行 import，無字串變更。
- Guard：`HIGHER_LAYERS` 加 `adapters`，`conversion/` 的 AST 掃描為空；`test_production_modules_do_not_import_translate`（排除 `tests/`、`.venv/`、`braille/liblouis/`）為空；子行程測試證明 `conversion.alignment/tokenizer/line_wrap/contracts` 不載入 `config`／`adapters`／`braille`／`wx`／`dual_view`／`libmathcat_py`，且 `tokenizer`／`line_wrap` 不載入 `alignment`。`test_platform_neutral_modules_do_not_load_native_modules` 仍 import `translate`，證明 shim 可用。
- 模組名用 `tokenizer` 而非 roadmap 的 `tokenize`（避免遮蔽標準庫）：合理。
- Packaging：`scripts/build-dotexpress.bat` 與 `client/DotExpress.spec` 未動（`hiddenimports=[]`）；三個新模組都是靜態 import，PyInstaller 的 `PYZ-00.toc` 已含它們。唯一差異：`translate` 不再被任何 production 模組 import，所以不再進 exe（I-1）。
- `p25_baseline.py`／`p25_perf.py`：仍 `import translate` 並 monkeypatch `translate.TranslationResult.reclean_braille_endspace`，因為 shim 回傳同一個 class 物件、`wrapping.py` 以方法呼叫，patch 生效（`trims=13` 證明）。

## 3. 失敗測試的裁決（`tests/test_conversion_service.py:289-325`）

- 放寬為 `"".join(result.raw) == "計算 1+2 的值"` 與 `"".join(result.braille) == "T[計算 ]M[1+2]⠀T[的值]"`：仍能抓到「空白重複」（join 後會多一個空白或多一個 `⠀`），也就是原測試名稱要守的事。fake 對單獨 `" "` 回 `[" "], ["⠀"]` 的特例在 `main` 就有，不是為了讓它過而加的。
- 證據：`results.md` §3 A（`" 的值"` 一次翻譯與拆開翻譯 cells 相同，且 `r2b=[0,1,4]`——空白在 zh-tw.ctb 下本來就是獨立 token）與 §3 B（真 pipeline raw 為七個 token）；本記錄重跑 `p25_baseline.py` 得到相同輸出。所以舊斷言 `["計算 ", "1+2", " 的值"]` 釘的是 fake 的「一次呼叫＝一個 token」模型，不是使用者行為；P2 review 的建議與 spec D9 一致。
- 特性測試 `test_leading_space_of_a_text_segment_is_its_own_token_and_segment` 釘住：token 列表 `["計算 ", "1+2", " ", "的值"]`、text translator 被呼叫的三段與順序、dual-view segments `[("text",["計算 "]),("math",["1+2"]),("text",[" "]),("text",["的值"])]`。真 liblouis 版 `test_leading_space_is_its_own_token_with_real_liblouis` 釘住字元級的同一形狀與 20 個 cell。兩者合起來，「文字段開頭的空白獨立成 token 與 segment」這個今日行為被鎖住；若未來決定合併相鄰 text segment，會先在這兩個測試紅燈。
- 是否有 under-test：沒有。原本能過的 fake 斷言其實一個也沒釘住真實 tokenization；現在 fake（呼叫粒度）＋真 golden（cells 與 segments）＋ BRL 雜湊三層都在。

## 4. 測試品質

### 4.1 Oracle 與等價測試（`tests/legacy_translation_result.py`、`tests/test_translation_split_equivalence.py`）

- Oracle：五行 header + marker + `d4a7aa1:client/translate.py` 逐位元組；`test_oracle_is_the_pre_split_translate_py` 以 `read_text` 做 LF 正規化後算 git blob id `10bd6414…`，我以 `git rev-parse main:client/translate.py` 核對相同；`assertIsNot` 確保不是同一個 class。檔名不以 `test_` 開頭，不會被 discover 收進來。
- 但 oracle 不是完全凍結：它 import 的是**現行** `languageDetection.unicode_blocks`（`build_language_blocks`、`language_has_all`），日後若改那裡（例如 P1-5 defect 4），oracle 與 production 會一起變，等價測試看不見；只有 fake golden／real golden 能抓（M-2）。
- 生成器涵蓋：12 種 unit（ASCII 單字／run、多字元 unit、漢字、假名、諺文、注音、全部標點＋`—`、半形與全形空白、`\n`、符號、3% 的 `""`）、每 unit 0–4 cell（兩種空白、兩種非空白）、25% 的 6 種畸形；separator 密集字母表用於 `reclean_token` 的一半與鏈的一半。我用相同 seed 重算：seed 105（trim）4,000 case 中 well-formed 3,260，其中 `r2b[0] > 0` 只有 7 個；seed 108（separator）2,000 case 中 well-formed 且有 separator 821 個，其中 `b2r` 非 canonical（任意值）43 個。數量薄但足以抓到對應 mutant（R1、R2，見下表）；建議補幾個決定性 case（M-3）。
- 比對項目完整：四個 list、identity 四元組、回傳值、例外型別＋訊息；`assertGreater(paths["returned"], cases // 2)` 防止生成器退化成全例外。

### 4.2 真 liblouis golden（`tests/test_translation_liblouis_golden.py`、`fixtures/translation_liblouis_golden.json`）

- Skip 規則：模組層 `ctypes.WINFUNCTYPE` 缺 → `SkipTest`；`from braille import louis_helper` 失敗 → `SkipTest`（helper 先 `os.add_dll_directory(BASE_DIR)` 再 `from braille import liblouis`，W-1 模式；`adapters/translation/liblouis.py` 本身不 import `braille.liblouis`，provider 也是先 import `louis_helper`）。`setUpClass` 先比 `louis_helper.louis.version()` 與 fixture 的 `3.37.0`，不同則 `AssertionError`（13 個 test 全部 error，訊息指示只在刻意升級時重生）；接著 `create_default_text_translator()`／`create_default_math_translator()` 直接呼叫，`RuntimeUnavailableError` → `SkipTest`，不會靜默落到 character fallback。runtime 與 temp dir 以 class cleanup 關閉。
- 本機：13 個 `ok`、0 skip（acceptance 2）。Linux 行為（模組 skip）為推理，未在本機驗證。
- 內容：17 個 case（8 輸入 × 2 table set + 長文件）× 5 run；`display_text` 全文、post-processed tokens 全文、merged／post-processed／segments 的 digest、segment 數；`snapshot_case` 另檢查 conversion 不隨 width 變。`test_p25_document_matches_the_recorded_brl` 把 history 文件複製進 fixtures（sha 釘住）並以 `display_text.replace("\n","\r\n").encode()` 重算兩個 BRL sha——與 GUI 匯出的實際 bytes 相同（`auto-results.md` 與本記錄 `cmp`）。
- 升級流程缺口：`AGENTS.md` 的 liblouis 升級 checklist 沒提到這個 fixture 要一起重生（M-4）。

### 4.3 `test_translation_result.py` 轉 unittest

- 13 個函式 → 4 個 class 14 個方法，名稱與期望不變，tab 縮排保留；5 個 fixture 依 spec 表修正（5/5、6/6 cell 與 position；`⠁` 非空白 cell；46 cell／`[0, 40, 41]`），各加一行理由；`test_end_right_end_sentence_blank` 的 docstring 說明它釘的是「已以空白 cell 結尾、不加分隔」分支；新增 `test_space_that_fits_at_the_line_end_stays_there` 釘住原 fixture 的今日結果。我以舊碼（oracle）核對：五個修正後的 fixture 在 `d4a7aa1` 上也得到相同結果，所以裁決「全是 fixture 缺陷」成立。
- `blank2`／`blank3` 的行內註解寫反了（M-5）。
- `test_bind_word_tokens_complex` 的 96 字／94 cell 短 map 保留（spec Corrected 10 已說明）。

### 4.4 結構與效能 guard

`LinearTrimTest`／`LinearSeparatorTest`：40,000 token／10,000 separator、獨立算的參考值、identity 斷言、`patch.object` 證明 fast path 不呼叫 stepwise／`insert_token` 而畸形輸入會；2 s 的計時上限是 backstop（M-6）。

### 4.5 自套 mutant（scratchpad `p25review/mut/client`，不在 repo 內；每個 mutant 跑 acceptance 2 的 9 個模組，含真 golden）

| # | mutant | 結果 |
| --- | --- | --- |
| R1 | fast trim 丟掉第一個 start 之前的 cell（`new_braille = []`） | 抓到：equivalence trim、whole chain |
| R2 | separator b2r 改成 `token_idx + inserted`（去掉 `min(…, bisect_right)`） | 抓到：equivalence reclean_token、whole chain |
| R3 | 刪掉尾端 `while inserted < count` 迴圈（`== len(braille)` 的 separator） | 抓到：equivalence reclean_token、whole chain |
| R4 | `_is_well_formed_alignment` 不檢查 `len(b2r) != len(braille)` | 抓到：`test_malformed_alignment_inserts_one_by_one`、equivalence ×2 |
| R5 | `reclean_token` 無 separator 時仍重建四個 list（identity 變） | 抓到：equivalence reclean_token、whole chain |
| R6 | `iter_separator_positions` 漏最後一對 | 抓到：tokenizer、`_core` ×2、equivalence ×2 |
| R7 | `wrap` 空輸入不補一行空白（`or not braille_lines` 拿掉） | 抓到：equivalence wrap、whole chain |
| R8 | `bind_word_tokens` guard 去掉 `len(b2r) != len(braille)` | 抓到：equivalence bind_word_tokens、whole chain |
| R9 | `_regroup` 負數 stray cell 走 Python 負索引（`0 <=` 拿掉） | 抓到：equivalence ×3 |
| R10 | `SPACE_ONLY` 加入全形空白 | 抓到：line_wrap sets、equivalence wrap、whole chain |
| R11 | fast trim 的 `removed` 在單 cell trim 時不累計 | 抓到：fake golden 5、real golden 8、`_core` 1、equivalence 2 |
| R12 | `contracted_token_spans` 以 `<=` 合併 | 抓到：equivalence bind_contracted_tokens |

12/12 抓到。R1–R3、R5、R7–R9、R12 只靠等價測試抓到（golden 沒有這些形狀），所以 oracle 是這次安全網的主力；實作者的 21 個 mutant 我沒重跑（工具未 commit）。

## 5. 限制條件

| 條件 | 結果 |
| --- | --- |
| `client/braille/tables/__tables.py`、`client/braille/liblouis/` 未動 | `git diff --stat main..HEAD -- client/braille` 空 |
| `client/braille/tables/__init__.py` 逐位元組相同（CRLF） | blob 相同；`i/crlf w/crlf`，255 行，tab |
| 兩個 fixture sha | `e67d95a1…211ccd`、`f493da52…c66c2cf`（HEAD 與 main 相同）；`tests/test_translation_golden.py` 未動 |
| msgid 353 | 354 行 `msgid`（含 header）HEAD 與 main 相同；`client/locales` 無 diff |
| tab 縮排 | 既有檔保留 tab；新檔四空白，spec D1／Test Plan 明寫「new files use 4 spaces, like the rest of `conversion/`」，與 `conversion/service.py`、`output.py` 一致（`conversion/jobs.py` 是 tab，既有不一致，不在範圍） |
| 無使用者可見行為變更 | 真 liblouis BRL 兩模式雜湊相同、13 trim 相同、fake golden 相同、dual-view segments digest 相同、無字串／`.po`／`.mo`／`scripts/` 變更。唯一的 artifact 差異是 exe 不含 `translate`（I-1） |
| `client/dictionary/` 未被測試讀寫 | 真 golden 用 temp dir 的不存在路徑；`p25_*` 用 `no-such-dictionary.csv`；`git status` 於全部測試後只有三個既有 untracked 目錄；`client/log/` 只有 15:39 的 `init.log`（早於本次所有執行） |

## 6. 實作記錄（plan「Implementation Notes」）的獨立驗證

| 聲明 | 驗證 |
| --- | --- |
| `Ran 1208`, `errors=1, skipped=5`，只有 F-W6 | 重現 |
| acceptance 2 `Ran 126 OK`，real golden 13 run 0 skip；acceptance 3 `Ran 7 OK` | 重現 |
| fixtures 不變、msgid 353 | 重現 |
| moved lines 30／33／112 | 重現（我的 script 與他們的數字一致） |
| `p25_baseline.py` BRL byte-identical；`p25_perf.py` 83,200 字 `wrap=0.44s reclean=0.06s` | 重現（0.44 s／0.06 s） |
| exe `D:\dxtest\N-p25\DotExpress.exe` 48,735,563 bytes、sha `bdba718c…aec427` | 重現；`PYZ-00.toc` 時間戳與 exe 相同 |
| 紅燈計時 42.6 s／19.9 s、各 task 的 `Ran` 計數序列、21 個 mutant 全抓到、20 個 shuffle seed | 未驗證（計數序列可由 commit 逐一跑出，但我沒做；mutant 工具未 commit） |
| 「Deviations: none in code, tests or expected values；only the Task 12 folder name」 | 程式與測試對照 plan 的 `File:` 區塊抽查（alignment、tokenizer、equivalence）一致 |

## 7. 文件正確性

- Spec「Corrected after planning」13 項與 plan「Spec Corrections and Refinements」12 項一致（spec 多了 Q1／Q2 的決定），zh-TW 版行數相同、第 27／44／314 行對應段落在。D5 原文「clamp runs anyway」與 Corrected 7 衝突，spec 自己宣告「the list wins」，可接受但留著會誤導（M-7）。
- Q2 已知缺陷：spec Open Questions、Corrected 1、Known Defects 1 三處一致，描述 `brown → br, ow, n`、width 8 `The quick br / own fox`、只影響 grade 2。我讀 fixture `ueb_g2/en_prose`：tokens 為 `br`,`ow`,`n`、`ov`,`er`、`the`,`n`、`re`,`st`,`s.`、`Te`,`st`,`ing,`——缺陷比例子寫的更廣（每個含縮寫的詞），且 `rests.` 的 `s.` 把句點也帶進片段；記錄的方向正確，建議把「每個縮寫詞」寫明（M-8）。根因（推理）：`bind_contracted_tokens` 先把共用一個 cell 起點的字元合併成多字元 unit，而 `word_token_spans` pass 1 只合併 `ch in ASCII_ALNUM` 的**單字元** unit，多字元 unit 不合併。
- Known Defect 2（空 token 的 `IndexError`）由 fuzz 證實存在且前後相同；Known Defect 4（`AGENTS.md` Key Modules 仍寫 `translate.py`）仍在。
- `test_translation_liblouis_golden.py` 的 docstring 與 skip／regenerate 說明正確；`--write` 入口正確。
- spec D7「`translate.py` kept for … anything outside the repository that imports `translate`」只對 source run 成立（I-1）。

## 發現清單

### Critical

無。

### Important

**I-1 Packaged build 不再附帶 `translate` 模組，spec 與 build 檔都沒有說**（`client/DotExpress.spec:13` `hiddenimports=[]`；`scripts/build-dotexpress.bat` 無 `--hidden-import`；spec D7）
- 情境：`client/build/DotExpress/PYZ-00.toc`（與 `N-p25` exe 同一次 build）有 `conversion.alignment` 等但沒有 `translate`，因為已無 production 模組 import 它，PyInstaller 的靜態分析不會收。`main` 的 exe 有它（adapters 當時 import `translate`）。唯一能在 exe 內動態 import 的使用者程式碼是前處理腳本（`conversion/preprocessing/user_script.py:78-90` 以 `exec` 執行，可 import 任何已打包模組）：一個寫了 `from translate import TranslationResult` 的腳本在 `N` 可跑、在 `N-p25` 會 `ModuleNotFoundError`。機率很低（腳本契約只有 `main(str) -> str`），但這是本次唯一的 artifact 層行為差異，而「無使用者可見變更」的聲明沒把它排除。
- 修法（二選一，使用者決定）：(a) 在 `build-dotexpress.bat` 加 `--hidden-import translate` 並在 `DotExpress.spec` 的 `hiddenimports` 加 `'translate'`，重建後以 `PYZ-00.toc` 確認；(b) 在 spec D7 與 Known Defects 明寫「frozen build 不含 `translate`；shim 只服務 source run、測試與 history scripts」。

### Minor

**M-1 Fast path 的 well-formed 檢查對 `braille_to_raw_pos` 的值不設限，正確性靠 `min(…)` 公式**（`alignment.py:239`）
- 不是缺陷（論證與 fuzz 都通過），但 `_is_well_formed_alignment` 的 docstring「one token per cell」會讓讀者以為 b2r 的值也被檢查了。建議在 docstring 補一句「b2r 的值不檢查；`reclean_token` 的公式對任意值與逐一插入相同」。

**M-2 Oracle 只凍結 `translate.py`，不凍結 `languageDetection.unicode_blocks`**（`tests/legacy_translation_result.py:9-13`）
- 情境：日後修 P1-5 defect 4（`language_has_all` 每字建 set）若順手改了語系判定，oracle 與 production 同步改變，`test_bind_word_tokens_matches_the_oracle` 仍綠；只剩 fake golden／real golden 擋。
- 修法：在 header 註明這個限制；或在 `test_conversion_tokenizer.py` 加幾個 `is_cjk_word_char` 的決定性 case（漢字／假名／諺文／注音／全形標點／`—`）。

**M-3 等價生成器對兩個 fast-path 特有形狀的覆蓋很薄**（`tests/test_translation_split_equivalence.py:69-96`）
- seed 105：well-formed 且 `r2b[0] > 0` 只有 7/4000；seed 108：well-formed、有 separator 且 b2r 非 canonical 只有 43/2000。這次都抓到了對應 mutant（R1、R2），但靠的是機率。
- 修法：在 `LinearTrimTest`／`LinearSeparatorTest` 各加一個決定性 case：前置 cell（`r2b=[2,4]`，braille 5 cell）與任意 b2r 值（含負數、`len(raw)+5`）的 separator case，期望值用 oracle 算一次寫死。

**M-4 liblouis 升級流程沒提到要重生 `translation_liblouis_golden.json`**（`AGENTS.md`「When upgrading liblouis」、`tests/test_translation_liblouis_golden.py:182-187`）
- 情境：依 AGENTS.md 升級 submodule 並重建 DLL 後，`setUpClass` 的版本比對讓 13 個測試 error，訊息雖清楚，但 checklist 第 5 步（驗證四種翻譯）沒說「然後 `python -m tests.test_translation_liblouis_golden --write` 並審閱 fixture diff」。
- 修法：AGENTS.md 升級步驟加一條；順手把 Key Modules 的 `translate.py`／`utils.py` 更新成 `conversion/{tokenizer,line_wrap,alignment}.py`（spec Known Defect 4）。

**M-5 `test_end_right_end_sentence_blank2`／`blank3` 的行內註解寫反**（`tests/test_translation_result.py:191,202`）
- 註解「Non-blank cells: a token whose braille ends in a blank cell gets no separator.」描述的是另一個分支；這兩個 fixture 用 `⠁` 正是為了讓分隔**被加上**。改成「Non-blank cells, so the closing mark gets its separator space (the all-blank fixture above pins the other branch).」

**M-6 兩個新的計時斷言（2 s）在慢 CI 上可能 flaky**（`tests/test_translation_result_core.py:294,331`）
- 本機 0.02 s／0.01 s，上限 100 倍；與既有 `LinearMergeTest` 的 5 s 同款。結構測試（`patch.object` 證明不走 stepwise／`insert_token`）才是 binding，計時可視為 backstop。若 CI 出現抖動，改成只比「線性 vs 二次」的比例或拉到 5 s。

**M-7 Spec D5 正文仍寫「clamp … runs anyway, as today」**（spec D5 末段；Corrected 7 說略過）
- spec 已宣告 Corrected 清單優先，但正文留著會讓下一個讀者對照程式時以為少了一段。建議直接改正文（或在該句後加「(superseded by Corrected 7)」）。

**M-8 Q2 的描述比實際缺陷窄**（spec Known Defects 1、Open Questions Q2）
- fixture `ueb_g2/en_prose` 顯示每個含縮寫的詞都被切（`brown`、`over`、`then`、`rests.`、`Testing,`），且句尾標點跟著最後片段（`s.`、`ing,`），所以 `wrap` 的「全形標點後加空白」與 `reclean_token` 的 pair 檢查都看不到整個詞。記錄方向正確；建議把「every word containing a contraction」與根因（`bind_contracted_tokens` 產生的多字元 unit 不被 `word_token_spans` pass 1 合併）寫進 Known Defects，方便日後的使用者決定。

**M-9 實作記錄的部分聲明無法由 repo 重現**（plan Implementation Notes）
- 紅燈計時、各 task 的 `Ran` 序列、21 個 mutant 的結果、20 個 shuffle seed 都依賴未 commit 的 throwaway 工具（Appendix 有原始碼）。不要求補；本記錄以自己的 fuzz／mutant 替代，但 release 記錄引用這些數字時應註明「implementer-reported」。

## 建議的下一步

1. 決定 I-1（hidden import 或文件化），一個小 commit；若選 (a) 需重建一次並確認 `PYZ-00.toc`，BRL 雜湊不會變。
2. 順手做 M-4、M-5、M-7、M-8（純文件／註解，一個 `docs:` commit），M-3 的兩個決定性 case 一個 `test:` commit。
3. 合併後把 `docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md` 缺陷清單的「優先 6 `reclean_braille_endspace` 二次方」與 P2-5 readiness 項目標為已關閉，並把 Q2 列入清單（優先 4，使用者決定）。

## 修正記錄

2026-10-09，同一 branch，未合併、未 push。協調者決定：I-1 採 (a)。

| 發現 | 處理 |
| --- | --- |
| I-1 | `10e267b`：`scripts/build-dotexpress.bat` 加 `--hidden-import translate`（bat 會重新產生被 git 忽略的 `client/DotExpress.spec`，重建後為 `hiddenimports=['translate']`）；新增守衛 `test_packaged_build_keeps_the_translate_shim`（`tests/test_translation_import_isolation.py`，檢查 bat 內容）；spec D7 與「規劃後更正」第 14 項（中英）寫明 frozen build 為使用者前處理腳本保留 shim |
| M-1 | `954146e`：`_is_well_formed_alignment` docstring 註明不檢查 `braille_to_raw_pos` 的值 |
| M-2 | `954146e`：spec D11.2（中英）註明 oracle 不凍結 `languageDetection.unicode_blocks`；oracle 檔本身不動（blob 檢查） |
| M-3 | `f015f31`：`LinearTrimTest.test_cells_before_the_first_token_start_are_kept`（`r2b=[2,4]`、6 cell、前置兩個空白 cell）與 `LinearSeparatorTest.test_arbitrary_cell_token_indices_shift_as_one_by_one`（b2r 含 `-1`、`-2`、`9` = `len(raw)+5`）；期望值以 oracle 算一次寫死，兩者都 patch 掉 fallback 以確認走 fast path。scratch 副本上 R1（`new_braille = []`）與 R2（`token_idx + inserted`）各只被對應的新測試抓到（兩個 class 的既有測試都沒抓到） |
| M-4 | 已修改本機 `AGENTS.md`（Key Modules 改為 `client/conversion/{tokenizer,line_wrap,alignment}.py` 與 `translate.py` shim；liblouis 升級步驟加第 6 步：`--write` 重生並審閱 `translation_liblouis_golden.json`）。`AGENTS.md` 被根目錄 `.gitignore` 忽略，所以沒有 commit |
| M-5 | `954146e`：`blank2`／`blank3` 註解改為「Non-blank cells, so the closing mark gets its separator space (the all-blank fixture above pins the other branch).」 |
| M-6 | 未處理（協調者決定維持；計時上限為 backstop） |
| M-7 | `954146e`：spec D5（中英）改為快速路徑略過夾限迴圈（規劃後更正第 7 項），fallback 保留 |
| M-8 | `954146e`：spec Q2 與 Known Defects 1（中英）寫明每個含部分詞縮寫的詞都被切（`brown`、`over`、`then`、`rests.`、`Testing,`），整詞縮寫（`the`、`and`）不受影響，句尾標點跟著最後片段，並記下推理的根因 |
| M-9 | 未處理（資訊性，不要求補） |

驗證：

- 重建：`client\.venv\Scripts` 置於 PATH 前執行 `scripts\build-dotexpress.bat`，exit 0。`client/build/DotExpress/PYZ-00.toc` 含 `('translate', 'D:\workspace\DotExpress\client\translate.py', 'PYMODULE')`；`client/DotExpress.spec` 為 `hiddenimports=['translate']`。
- exe：`D:\dxtest\N-p25\DotExpress.exe`（覆蓋前一版）48,735,916 bytes，sha256 `5caf56128310cc02da61b8a2f259cc088ed62580665a48fcbd3c8f2d7f462260`（舊版 48,735,563 bytes）。
- GUI：`auto\item7.py D:\dxtest\N-p25\DotExpress.exe D:\dxtest\auto7-p25b $H\p25_doc.txt`（pywinauto scratch venv）：`p25_unicode.brl` `365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c`、`p25_ascii.brl` `95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64`，與基線相同；轉換、匯出無錯誤，關閉後行程結束。
- 完整套件：`cd client && .venv\Scripts\python.exe -m unittest discover -s tests` → `Ran 1211`、`FAILED (errors=1, skipped=5)`，唯一 error 為 F-W6 `test_case_only_rename_still_renames`（1208 + 3：M-3 兩個、I-1 守衛一個）。
- Fixture sha256（`git show HEAD:<path> | sha256sum`）：`translation_golden.json` `e67d95a1…211ccd`、`dictionary_entries_trace.json` `f493da52…c66c2cf`，不變；`git diff main --stat -- client/braille client/locales client/dictionary` 為空。
