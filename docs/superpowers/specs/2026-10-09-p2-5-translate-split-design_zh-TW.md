# translate.py 拆分（P2-5）設計

## 目標

路線圖任務 P2-5（`docs/superpowers/history/2026-10-09-02-handoff/refactor-review.md` 6.3 節、發現 S-2、D-3 的其餘部分）把 `client/translate.py` 拆成三個各司其職的模組：

- `client/conversion/tokenizer.py`：原文字元如何組成 token（標點類別、縮寫 token 的範圍、詞級 token 的範圍、收尾標點與起始標點之間要插入分隔空白的位置）。
- `client/conversion/line_wrap.py`：token 如何依指定寬度排成多行。
- `client/conversion/alignment.py`：`TranslationResult` 值物件（原文 token、點字方與兩個位置對應表），以及維持對應表一致的操作（合併、重組、插入、修剪）。

`client/translate.py` 保留為一行 re-export，既有的 import 照常可用。`conversion/wrapping.py` 的兩個函式與簽章不變。

同一個任務、同一個 branch 中還包括：

1. **失敗測試** `test_translate_with_language_does_not_duplicate_existing_spaces_around_math` 依使用者決定處理：斷言改為比對接起來的原文與接起來的點字，並新增特性化測試，鎖定「文字段開頭的空白是獨立的 token，也是獨立的 Dual View 段」。
2. **`reclean_braille_endspace` 改為線性**（P1-5 已知缺陷 3）。輸出必須逐位元組相同。
3. **前置工作**（HANDOFF 4.3 節）：`tests/test_translation_result.py` 轉成 `unittest`，並裁決其 5 個失敗（裁決見下：五個都是 fixture 錯誤，沒有正式程式碼的缺陷）；`adapters/translation/contracts.py` 的 port 移到 `conversion/contracts.py`，並把 `adapters` 加入 `HIGHER_LAYERS`（P2 審查 M-1）。
4. **先建安全網，再動正式程式碼**：既有的假 helper golden 維持逐位元組不變；以目前 `translate.py` 的凍結複本作為測試 oracle，進行隨機等價測試（所有平台都執行）；新增只在 Windows 執行的 golden，鎖定真實 liblouis 與 MathCAT 的輸出（中文、英文 UEB 一級與二級、日文、數學、標點、寬度 1-40）以及已記錄的 `p25_*.brl` 雜湊值，沒有 liblouis 的環境則略過。
5. **提議新增（已決定納入，見「待使用者決定」）：** `reclean_token` 也改為線性。這是撰寫本規格時發現的：在對話很多的中文文字上，它是平方複雜度，而且比修剪慢得多（真實 liblouis，99,200 字、9,600 個分隔空白需 322 秒）。輸出逐位元組相同、使用同一張安全網、獨立 commit，可以拿掉而不影響其他步驟。

除了第 1 項的測試預期（它鎖定的是目前的行為）以外，這是保持行為不變的重構。對任何輸入，點字文字（Unicode 與 ASCII）、BRL 位元組、原文換行、每個對位 list、每個 Dual View 段與 HTML 都與 `main` 的 `d4a7aa1` 逐位元組相同。使用者可見字串不變；`.po`/`.mo` 不變。

規劃後更正：計畫 `docs/superpowers/plans/2026-10-09-p2-5-translate-split.md`（「Spec Corrections and Refinements」一節）更正了三項事實（oracle 不可能既是逐位元組複本又帶標頭；language blocks 的 patch 目標必須在抽出 tokenizer 時就改，而不是搬移類別時；分隔空白計時測試的規模），並細化了安全網、兩處實作細節與測試數量。下方「規劃後更正」一節列出相對於第一版（commit `079d58b`）的所有變更；若後面的章節與該清單不一致，以清單為準。

## 規劃後更正（2026-10-09）

1. **Q1 與 Q2 已決定**（協調者，2026-10-09）：Q1 同意，遷移步驟 7（D6，線性 `reclean_token`）納入 P2-5。Q2 不在範圍內：P2-5 只鎖定目前的行為；UEB 二級在詞中間斷行仍是既有的已知缺陷（「發現但不在此修正的缺陷」第 1 項），留待使用者日後決定。
2. **oracle 是「標頭 + 標記行 + 逐位元組複本」（D11.2）。** `tests/legacy_translation_result.py` 開頭是五行註解，最後一行是標記 `# ---- verbatim copy of client/translate.py at d4a7aa1 follows ----`，其後是 `git show d4a7aa1:client/translate.py` 的原始位元組。oracle 測試把檔案換行正規化為 LF，檢查標記之後的部分的 blob id 為 `10bd641485327b00cb71a14d4946f01a1788f794`（加了標頭的整份複本 blob id 一定不同）。
3. **`build_language_blocks` 的 patch 目標在步驟 8 改，而不是步驟 10（D7、測試計畫 F）。** tokenizer 擁有常數之後，`translate.py` 不再 import `build_language_blocks`，`patch("translate.build_language_blocks")` 會引發 `AttributeError`；步驟 8 把它改成 `conversion.tokenizer.build_language_blocks`。
4. **分隔空白計時測試用 10,000 個分隔空白（測試計畫 E）。** 舊的 `reclean_token` 在這台 Windows 機器上處理 10,000 組 `」「` 需 19 秒，20,000 組會超過一分鐘；測試名稱為 `test_inserting_ten_thousand_separators_takes_linear_time`（上限 2 秒；線性版 0.01 秒）。修剪測試維持 40,000 個 token（舊程式在該機器上 42 秒而非 37 秒；線性版 0.02 秒）。
5. **真實 golden 的形狀（D11.3）。** 17 個案例：兩組翻譯表各 8 個輸入，加上一份長文件（`p25_perf.py` 的段落 x 400，寬度 40），長文件只用預設翻譯表，因為它只有中文。每個案例記錄：輸入的 sha256、每次執行的顯示文字（長文件只記摘要）、後處理後的 token（長文件記摘要）、合併後 list、後處理後 list 與 Dual View 段的摘要，以及段數。fixture 約 34 KB；步驟 6 之後模組執行 1.7 秒（之前 4.9 秒）。liblouis 版本不是記錄的 `3.37.0` 時，`setUpClass` 會引發 `AssertionError`，訊息說明只有在刻意升級時才重新產生。runtime 直接由 `create_default_text_translator()` 與 `create_default_math_translator()` 建立，並由 class cleanup 關閉。
6. **等價測試（D11.2）** 也比對四個屬性中哪些仍是原本的 list 物件（「就地修改或替換」）。`reclean_token` 的案例與整條鏈的案例各有一半使用分隔空白密集的單位字母表（只用一般字母表時，4,000 個格式正確的案例中有分隔空白的不到 100 個，有兩個以上的為零）。每種操作 4,000 個案例，整條鏈 2,000 個；模組執行 1.3 秒。
7. **快速修剪不執行最後的夾限迴圈（D5）。** 快速路徑上不可能有起點超過新長度，所以略過（程式中有註解說明）；逐步的後備路徑保留它。
8. **分隔空白位置一次算出（D6）。** `reclean_token` 在選擇路徑之前先算 `list(iter_separator_positions(...))`。位置只取決於原本的 token，而且對字串 token 計算時不會引發例外，所以逐一插入的後備路徑仍在同一次插入時引發例外。
9. **搬移的程式碼保留註解（D1）。** 搬移的程式本體原樣保留中文註解；`bind_word_tokens` 的 docstring 留在方法上。`line_wrap.py` 刪除 `wrap` 結尾兩行被註解掉的程式碼，並加入 D4 允許的英文分支註解。
10. **fixture 錯誤（D10）。** `test_bind_word_tokens_complex` 的對應表也偏短（96 個字元、94 個點字方與位置）；因為重組從不讀到位置 82 之後，它會通過，維持原樣。
11. **守衛（測試計畫 F）。** `test_tokenizer_and_line_wrap_do_not_import_alignment` 加入時就會通過（它是守衛，不是紅燈測試）。步驟 10 之前，`conversion/contracts.py` 從 `translate` import `TranslationResult`。
12. **Windows 驗證第 4 項。** `D:\dxtest\N` 只有 `DotExpress.exe`；packaged build 的輸出改與 `docs/superpowers/history/2026-10-09-03-windows-verification/baseline/p25_*.brl` 比對，N 與 B 都與它逐位元組相同。
13. **測試數量。** 步驟 10 之後在 Windows 上為 `Ran 1208`、`FAILED (errors=1, skipped=5)`（只有 F-W6）。各 commit：1157、1158、1171、1179、1180、1183、1186、1200、1204、1208。真實 golden 模組 13 個測試；等價模組 8 個；tokenizer 模組 14 個；line wrap 模組 4 個。
14. **packaged build 保留 `translate` shim（D7；P2-5 審查 I-1 之後加入）。** 一旦沒有正式模組 import `translate`，PyInstaller 就不會把它打包進 exe，import 它的使用者前處理腳本只會在打包版失敗。`scripts/build-dotexpress.bat` 加上 `--hidden-import translate`（它重新產生的、被 git 忽略的 `client/DotExpress.spec` 因此列出 `hiddenimports=['translate']`），並由 `test_packaged_build_keeps_the_translate_shim` 檢查這個批次檔。這是唯一的 `scripts/` 與打包設定變更；它取代「維持不變的部分」與驗收條件 7 中相關的字句。

## 待使用者決定（已於 2026-10-09 決定，見上）

- **Q1. 是否在 P2-5 把 `reclean_token` 改為線性（D6）？** 不在原本的範圍內，但與已決定的修剪是同一類修正、位於同一條程式路徑。**決定：納入**，作為遷移步驟 7。
- **Q2（發現，不屬於 P2-5）。** 英文設為 UEB 二級時，含縮寫的詞會被切成數個 token（`brown` -> `br`、`ow`、`n`），所以換行器可能在詞的中間斷行而沒有連字號：寬度 8 時為 `The quick br` / `own fox`。一級（預設）不受影響。修正會改變點字版面，所以是使用者的決定，應另立任務。**決定：不在範圍內**；P2-5 在 Windows golden 中鎖定目前的行為，此缺陷留待使用者日後決定（「發現但不在此修正的缺陷」第 1 項）。

## 已決定的前提

- 失敗測試在 P2-5 處理：放寬斷言為比對接起來的 raw/braille 文字，並新增特性化測試鎖定空白獨立成段。證據：`docs/superpowers/history/2026-10-09-03-windows-verification/results.md` 3 節 A-B（真實 liblouis 得到 raw `['計','算',' ','1+2',' ','的','值']`；`" 的值"` 一次翻譯與分兩次翻譯的點字方完全相同）。
- `reclean_braille_endspace` 改為線性且輸出逐位元組相同（results.md 3 節 C-D：`p25_doc.txt` 有 13 次修剪；83,200 字時 wrap 的 28.92 秒中有 28.55 秒花在這裡，翻譯本身只要 4.17 秒）。
- 真實 liblouis 只能經由 `braille.louis_helper` 取得（results.md F-W1、W-1 守衛）。

## 現況（2026-10-09 於 `main` `d4a7aa1` 驗證）

### `client/translate.py`（537 行，tab）

| 行 | 成員 | 角色 |
| --- | --- | --- |
| 11-14 | `_CJK_LANGUAGE_BLOCKS` | 唯讀的 CJK 區塊表（P1-5） |
| 17-35 | 類別屬性 | 12 個標點 `frozenset`、`lang_blocks`、`__hash__ = None` |
| 37-70 | `__init__`、`concat`、`__add__`、`__eq__` | 值物件與線性合併（P1-5） |
| 72-114 | `bind_contracted_tokens` | 合併共用同一個點字起點的原文字元（由 liblouis adapter 呼叫） |
| 116-317 | `bind_word_tokens` | 對單元走三遍（ASCII 連續字元、單一 CJK 字、尾隨標點鏈、開頭標點鏈），再把兩個對應表重建為 token 級 |
| 319-367 | `insert_token` | 插入一個 token 與其點字方，重建全部四個 list |
| 369-391 | `reclean_token` | 在以 `RIGHT_PUNCT` 結尾與以 `LEFT_PUNCT` 開頭的兩個 token 之間插入 `" "` 與一個空白點字方 |
| 393-444 | `reclean_braille_endspace` | 修剪每個 token 結尾的空白點字方（至少保留一格） |
| 446-537 | `wrap` | 把 token 排成寬度 `width` 的多行，回傳 `(braille, source)` |

`bind_word_tokens` 每次呼叫都建立 `ASCII_ALNUM`、`TRAIL_PUNCT` 與 `LEAD_PUNCT`；`wrap` 對每個 token 都建立 `RIGHT_PUNCT_FULL | END_SENTENCE_PUNCT_FULL` 與 `set(" ")`。

呼叫端：`conversion/wrapping.py`（先 `concat`，再以方法呼叫 `reclean_braille_endspace`、`bind_word_tokens`、`reclean_token`、`wrap`）、`adapters/translation/liblouis.py`（`bind_contracted_tokens`）。建構者：liblouis、MathCAT 與 fallback adapter，以及 `conversion/preprocessing/literal_braille.py`。型別使用者：`adapters/translation/contracts.py`。`translate.py` 以外沒有正式程式碼讀取標點集合或 `lang_blocks`。Windows 歷史腳本 `p25_baseline.py` 與 `p25_perf.py` 會 import `translate`，並 monkeypatch `TranslationResult.reclean_braille_endspace` 以計算修剪次數與計時。

`wrap` 結果中的原文那一半從未顯示：`conversion/output.py:80` 直接丟棄（`_text_wrapped`）。只有 golden 測試會記錄它。點字那一半才是使用者看到與匯出的內容。

### 目前的 import 關係

`conversion/{jobs,output,service,text/pipeline}.py`、`gui.py` 與 `ui/conversion_presenter.py` 從 `adapters.translation.contracts` import `TranslationRuntime`（P2 審查 M-1：`conversion` 依賴 `adapters`）。`adapters/translation/contracts.py` 包含 `RuntimeUnavailableError`（只有 `adapters/translation/provider.py` 會拋出與捕捉）、兩個翻譯器 `Protocol` 與 `TranslationRuntime` dataclass，並 import `translate`。`tests/test_translation_import_isolation.py:8` 的 `HIGHER_LAYERS` 不含 `adapters`，所以 AST 守衛看不到這條反向的邊。

### 目前的測試安全網

- 本機全套測試（`cd client && .venv/Scripts/python.exe -m unittest discover -s tests`）：`Ran 1143`、`failures=1`（P2-5 測試）、`errors=1`（`test_case_only_rename_still_renames`，F-W6，不在範圍內）、`skipped=5`（平台 skip）。
- `tests/test_translation_golden.py` + `fixtures/translation_golden.json`：假 liblouis helper，5 個短輸入 x 5 次執行 + 一份 360 段的文件。涵蓋中文、含縮寫的英文、數學、全形成對標點、字面點字、寬度 1/10/24/40。沒有日文、沒有韓文、沒有破折號、沒有緊貼詞的半形括號鏈。fixture sha256（以 `git show HEAD:<path> | sha256sum` 計算，因為 `core.autocrlf=true`）：`translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`、`dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`。
- `tests/test_translation_result_core.py`：21 個測試（值物件、合併、常數）。`test_construction_does_not_build_language_blocks` patch 的是 `translate.build_language_blocks`。
- `tests/test_translation_result.py`：13 個 pytest 風格函式，`unittest` 下 `NO TESTS RAN`；直接呼叫時 8 個通過、5 個失敗（見下節）。
- 只在 Windows 執行、使用真實 liblouis：`test_translation_language_result.py`（1 個測試）、`test_language_detection_translation.py`（1 個）、`test_liblouis_runtime.py`（5 個）。沒有任何一個針對真實文字鎖定換行或 token 輸出。

### `test_translation_result.py` 的 5 個失敗

先直接呼叫每個函式，再以修正後的 fixture 呼叫（暫存腳本，未 commit）。

| 測試 | 失敗 | 原因 | 裁決 |
| --- | --- | --- | --- |
| `test_bind_word_tokens_lead_punct` | `translate.py:297`（`old_r2b[c_start]`）拋出 `IndexError` | fixture 有 5 個原文字元，卻只有 4 個點字方與 4 個 `raw_to_braille_pos` 項目 | **fixture 錯誤。** 沒有任何產生者會建出這種結果（liblouis 對每個輸入字元回傳一個位置；MathCAT、字面點字與 fallback 建出的長度相等；`concat` 與重組都保持長度）。改成 5 格、5 個位置後，程式正好回傳預期的 `['「嶼', '我', '共', '視']`。 |
| `test_bind_word_tokens_lead_punct_continue` | 同樣的 `IndexError` | 6 個字元，只有 5 個點字方與位置 | **fixture 錯誤**，理由相同；改為 6/6 後回傳預期的 `['「「嶼', '我', '共', '視']`。 |
| `test_end_right_end_sentence_blank2` | 硬換行前、`」` 之後少了 `" "` | fixture 的每個點字方都是 `BLANK`；`wrap` 只在 token 的點字不是以空白點字方結尾時，才在全形收尾或句尾標點後加分隔空白（`translate.py:509-515`） | **fixture 錯誤。** 改用非空白點字方後，程式正好回傳預期字串。 |
| `test_end_right_end_sentence_blank3` | `」` 與 `『` 之間少了 `" "` | 同樣是全為 `BLANK` 的 fixture | **fixture 錯誤**；改用非空白點字方後回傳預期的 `"「嶼我」 『共視』"`。 |
| `test_remove_start_line_blank` | 得到 `"...an \nI see"` 而不是 `"...an\nI see"` | 第一個 token 有 39 個字元、給了 39 格，所以空白 token 剛好放在第 1 行行尾（39 + 1 = 40），永遠不會到第 2 行行首 | **fixture 錯誤**（算術）。第一個 token 給 40 格時，空白會落在第 2 行行首而被移除，回傳預期字串。原寫法的情況是正確行為（放得進行尾的空白就留在行尾）。 |

對目前通過的 `test_end_right_end_sentence_blank` 的影響：它同樣使用全為 `BLANK` 的點字方，所以它鎖定的是「token 已經以空白點字方結尾，不再加任何東西」這個分支。它保持原樣，並註明這一點；`..._blank2` 改用非空白點字方後鎖定另一個分支。當 fixture 真的反映它們要測的東西時，兩者的預期是一致的。

### 效能

- `reclean_braille_endspace` 每修剪一個 token，就從兩個 list 中段刪除，並位移之後所有 `raw_to_braille_pos` 項目：O(修剪次數 x 長度)。Windows：83,200 字的真實 `zh-tw.ctb` 輸出需 28.55 秒（results.md 3 節 D）；最壞情況修剪 10,000 次需 2.3 秒。
- **新發現：** `reclean_token` 每個分隔空白都呼叫一次 `insert_token`，而 `insert_token` 會重建全部四個 list：O(分隔空白數 x 長度)。真實 liblouis，文字 `他說：「你好嗎？」「我很好，謝謝。」（甲）（乙）大家都笑了。` 重複：6,200 字（600 個分隔空白）0.35 秒、24,800 字（2,400 個）11.6 秒、99,200 字（9,600 個）322 秒。對話（`」「`）與列舉（`）（`）讓這在小說與教科書中是實際會發生的情況。
- 兩個線性版本的原型（只在暫存區）：83,200 字的情況下修剪 0.053 秒、整個 wrap 0.50 秒；48,000 個分隔空白 0.064 秒。兩者在假 golden、`p25` BRL 位元組、對話文字（寬度 1/7/10/24/40），以及 30,000 + 40,000 個隨機案例（含格式錯誤的對位）上都與凍結的程式碼一致。所有觀察到的真實輸出，對位都是格式正確的（走快速路徑），從未走到 fallback。

## 設計

### D1. 模組配置與相依

```
conversion/tokenizer.py   -> languageDetection.unicode_blocks, string, types
conversion/line_wrap.py   -> conversion.tokenizer（只用常數）
conversion/alignment.py   -> conversion.tokenizer, conversion.line_wrap
conversion/contracts.py   -> conversion.alignment
translate.py              -> conversion.alignment            （只做 re-export）
```

沒有循環；`tokenizer` 與 `line_wrap` 永遠不 import `alignment`。它們都不 import `config`、`braille`、`adapters`、`wx` 或 `dual_view`。新檔案與 `conversion/` 其他檔案一樣使用 4 個空白；搬過來的本體由 tab 機械式地改為空白縮排，除了本節明列的地方以外不做其他修改。

模組命名為 `tokenizer`，而不是路線圖的 `tokenize`：與標準函式庫 `tokenize` 同名的檔案，只要 `conversion/` 出現在 `sys.path` 上（例如執行 `python conversion/line_wrap.py`），就會讓 `traceback`/`linecache` 壞掉。

### D2. `TranslationResult` 保留完整的方法 API

`TranslationResult`（位於 `conversion/alignment.py`）保留 `__init__`、`concat`、`__add__`、`__eq__`、`__hash__ = None`、12 個標點類別屬性與 `lang_blocks`（與 tokenizer 的常數是同一批物件），以及 `bind_contracted_tokens`、`bind_word_tokens`、`insert_token`、`reclean_token`、`reclean_braille_endspace`、`wrap` 等方法，簽章、回傳值與修改行為都不變。斷詞與換行的方法變成薄薄的委派。`conversion/wrapping.py` 照舊以方法呼叫它們。

理由：所有呼叫端、測試，以及兩個 Windows 歷史腳本（它們 monkeypatch `TranslationResult.reclean_braille_endspace`，而且驗證時會重跑）都不需修改；這個類別仍是唯一修改四個 list 的地方。

### D3. `conversion/tokenizer.py`

- 常數：12 個標點 `frozenset`（名稱與成員與目前相同）、`CJK_LANGUAGE_BLOCKS`（目前的 `_CJK_LANGUAGE_BLOCKS`），以及從函式內提升到模組層級、成員相同的集合：`ASCII_ALNUM = frozenset(string.ascii_letters + string.digits)`、`TRAIL_PUNCT = RIGHT_PUNCT | MIDDLE_SENTENCE_PUNCT | END_SENTENCE_PUNCT`、`LEAD_PUNCT = LEFT_PUNCT | frozenset("—")`。
- `is_cjk_word_char(ch, lang_blocks) -> bool`：目前的巢狀函式。
- `contracted_token_spans(raw_to_braille_pos) -> list[tuple[int, int]]`：`bind_contracted_tokens` 的範圍迴圈（85-97 行）。
- `word_token_spans(units, lang_blocks=CJK_LANGUAGE_BLOCKS) -> list[tuple[int, int]]`：`bind_word_tokens` 的第 1-3 遍（159-285 行），回傳最後的範圍。一個範圍的 token 文字一定是 `"".join(units[start:end])`：第 1 遍是接起連續字元或取單一單元，第 2、3 遍只會依序串接相鄰的 token。
- `iter_separator_positions(tokens)`：以目前的成對檢查（`prev and curr and prev[-1] in RIGHT_PUNCT and curr[0] in LEFT_PUNCT`）為內容的 generator，依序產生 `reclean_token` 要在其前方插入分隔空白的每個索引 `i`（`1 <= i < len(tokens)`）。目前的迴圈會跳過剛插入的 token，所以檢查的正好是原本相鄰的每一對、每對一次、依序進行；generator 也是如此。

都是純函式，不 import `TranslationResult`。`language_has_all` 每次呼叫建立一個 set（P1-5 已知缺陷 4）不在範圍內。

### D4. `conversion/line_wrap.py`

`wrap_tokens(tokens, braille, raw_to_braille_pos, width) -> tuple[str, str]`：即 `wrap` 的本體，把 `self.raw`、`self.braille`、`self.raw_to_braille_pos` 換成參數，把 `self.RIGHT_PUNCT_FULL | self.END_SENTENCE_PUNCT_FULL` 換成模組常數 `SEPARATED_AFTER_PUNCT`，把 `set(" ")` 換成 `SPACE_ONLY = frozenset(" ")`（成員判斷完全相同）。只讀取輸入，從不修改。唯一允許的其他修改：在硬換行分支的兩個條件加上括號，把既有的 `and`/`or` 優先順序明確寫出來，以及說明各分支的英文註解（包括為何第二個條件與第一個不同）。`TranslationResult.wrap(width)` 回傳 `wrap_tokens(self.raw, self.braille, self.raw_to_braille_pos, width)`。

### D5. `conversion/alignment.py`

- 依 D2 的 `TranslationResult`，從 `translate.py` 搬來。
- `_regroup(spans)`（私有方法）：`raw = ["".join(old_raw[s:e]) ...]`、`raw_to_braille_pos = [old_r2b[s] ...]`、`braille_to_raw_pos = [char_to_token[c] if 0 <= c < len(old_raw) else 0 for c in old_b2r]`。目前兩處重組（99-114 行與 296-317 行）用的正是這些運算式，包括 `raw_to_braille_pos` 比範圍所需短時拋出的 `IndexError`。
- `bind_contracted_tokens`：守衛不變（`if not self.raw or len(self.raw) != len(self.raw_to_braille_pos): return`），接著 `self._regroup(contracted_token_spans(self.raw_to_braille_pos))`。
- `bind_word_tokens`：先計算 `word_token_spans(self.raw, self.lang_blocks)`，再做目前的守衛（`not r2b or not raw or len(b2r) != len(braille)` 就 return），再 `_regroup`。順序與目前相同。`self.lang_blocks` 仍經由實例讀取。
- `insert_token`：本體不變。
- `reclean_braille_endspace`（線性，第 2 項）：
  - 與目前相同的提早 return（`raw`/`braille` 為空、對應表為空）。
  - **快速路徑**在對位格式正確時使用：`len(raw_to_braille_pos) == len(raw)`、`len(braille_to_raw_pos) == len(braille)`，且 `0 <= raw_to_braille_pos[0] <= ... <= raw_to_braille_pos[-1] <= len(braille)`。對 token 走一遍，並累計已刪除的點字方數 `removed`：token `t` 的原始範圍為 `[start, end)`（`end` 是下一個起點或 `len(braille)`），新起點為 `start - removed`；保留的點字方是 `braille[start:new_end]`，其中 `new_end` 在剩下不只一格時去掉結尾的空白點字方；第一個起點之前的點字方保留。三個 list 以 slice assignment（`lst[:] = new`）就地取代，因此仍是同一個物件，與目前的 `del` 相同。
  - 為何完全相同：目前的迴圈對之後的每個起點位移相同的量，所以處理 token `t` 時，它的起點與終點都是原始值減去到目前為止刪除的點字方數；起點不遞減時，先前的每次刪除都在目前起點之前，所以目前看到的點字方就是同樣位移後的原始點字方。因此被修剪的 token 與修剪的量都相同。最後的夾限迴圈在這條路徑上不可能生效（token `t` 之後的刪除都落在 `[start_t, len)` 之內），但仍照目前的做法執行。
  - **Fallback**：其他任何對位都執行目前的迴圈，內容不變（私有的 `_reclean_braille_endspace_stepwise`）。非單調或長度不符的對應表會讓刪除與後面的範圍重疊，只有逐步模擬才能重現；真實輸出從不出現這種情況，所以 fallback 實際上沒有成本，同時讓每個輸入（包括會拋出的例外）都保持逐位元組相同。
- `reclean_token`（D6）。

### D6. `reclean_token` 一次走完（提議，Q1）

不做 D6 時，`reclean_token` 改寫為 `for offset, index in enumerate(iter_separator_positions(list(self.raw))): self.insert_token(index + offset, " ", blank)`，也就是把目前的迴圈換個寫法（位置從原始 token 的快照中延遲讀取，所以任何例外都在同一對上發生）。

做 D6 時，若至少有一個分隔空白且對位格式正確（與修剪相同的檢查），四個 list 一次重建。設分隔空白位置為 `i_0 < ... < i_{k-1}`（原始 token 索引）：

- `raw`：在每個原始 token `i_m` 之前放 `" "`。
- `raw_to_braille_pos`：原始 token `j` 的起點是 `r2b[j] + #{m : i_m <= j}`；分隔空白 `m` 的起點是 `r2b[i_m] + m`。
- `braille`：對每個 `m`，依序在原始點字方 `r2b[i_m]` 之前放一個空白點字方（位置相同時保持分隔空白的順序；等於 `len(braille)` 的位置附加在最後）。
- `braille_to_raw_pos`：分隔空白 `m` 的點字方對應到 `i_m + m`；位於位置 `b`、值為 `t` 的原始點字方對應到 `t + min(#{m : r2b[i_m] <= b}, #{m : i_m <= t})`。

為何完全相同：分隔空白 `m` 插在 token 索引 `i_m + m` 與點字方 `r2b[i_m] + m`；起點不遞減時，原始點字方位於該插入點或其後，若且唯若 `b >= r2b[i_m]`；目前的更新在第 `m` 步只對「位於插入點或其後、且值 `v >= i_m + m`」的點字方加一，而這個比較一旦不成立就一直不成立（每一步差距至少減一），因此得到 `min`。沒有分隔空白時什麼都不變（同一批 list 物件，與目前相同）；至少有一個時，四個 list 都是新物件，也與目前相同（`insert_token` 會重新綁定它們）。格式錯誤的對位使用上面的迴圈。

### D7. `translate.py` 改為 re-export

```python
from conversion.alignment import TranslationResult

__all__ = ["TranslationResult"]
```

保留給測試、Windows 歷史腳本，以及 repository 以外任何 import `translate` 的程式，包括使用者前處理腳本（由 `conversion/preprocessing/user_script.py` 在打包版內執行）。沒有正式模組 import 它，所以 PyInstaller 本來不會把它放進 frozen build；`scripts/build-dotexpress.bat` 以 `--hidden-import translate` 保留它（規劃後更正第 14 項）。正式模組改為 import `conversion.alignment`（各 adapter、`conversion/wrapping.py`、`conversion/preprocessing/literal_braille.py`、`conversion/contracts.py`）；由守衛維持。`test_import_does_not_import_liblouis_helper` 仍成立（`translate` 有 `TranslationResult`、沒有 `translate`、沒有 `translate_as_single_token`、不載入原生模組）。`SharedConstantsTest.test_construction_does_not_build_language_blocks` 改為 patch `conversion.tokenizer.build_language_blocks`，而不是 `translate.build_language_blocks`（shim 上已沒有這個屬性）。

### D8. contracts 移入 `conversion`（P2 審查 M-1）

- 新增 `conversion/contracts.py`（4 個空白）：原封不動搬入 `BrailleTextTranslator`、`MathSegmentTranslator` 與 `TranslationRuntime`；它從 `conversion.alignment` import `TranslationResult`。
- `adapters/translation/contracts.py` 保留 `RuntimeUnavailableError`（屬於 adapter 的關注點：只有 `provider.py` 拋出與捕捉），並從 `conversion.contracts` re-export 三個 port，所以 `adapters.translation` 與所有從那裡 import 的測試都照常可用，拿到的是同一批物件。
- `conversion/{jobs,output,service,text/pipeline}.py`、`gui.py` 與 `ui/conversion_presenter.py` 改從 `conversion.contracts` import `TranslationRuntime`。
- `tests/test_translation_import_isolation.py`：`HIGHER_LAYERS` 加入 `"adapters"`。之後的方向只有 `adapters -> conversion`。port 屬於使用端，這也是 `Protocol` 通常放的位置。
- 不採用的方案：註明 `adapters.translation.contracts` 屬於 `conversion` 的一部分。D7 之後各 adapter 會 import `conversion.alignment`，套件層級就會變成 `adapters <-> conversion` 雙向。

### D9. 失敗測試（已決定）

`tests/test_conversion_service.py`：

- `test_translate_with_language_does_not_duplicate_existing_spaces_around_math` 保留名稱與輸入，斷言改為 `"".join(result.raw) == "計算 1+2 的值"` 與 `"".join(result.braille) == "T[計算 ]M[1+2]⠀T[的值]"`（假翻譯器把單獨的 `" "` 翻成一個空白點字方）。原文的每個空白在文字中只出現一次，在點字中也只對應到一個位置：沒有重複的空白。
- 新增 `test_leading_space_of_a_text_segment_is_its_own_token_and_segment`：相同輸入；`result.raw == ["計算 ", "1+2", " ", "的值"]`；文字翻譯器依序以 `"計算 "`、`" "`、`"的值"` 被呼叫；Dual View 段以 `(source_kind, raw)` 表示為 `[("text", ["計算 "]), ("math", ["1+2"]), ("text", [" "]), ("text", ["的值"])]`。
- Windows golden（D11）以真實 liblouis 鎖定相同的形狀：合併後 raw `['計','算',' ','1+2',' ','的','值']`、點字 `⠅⠡⠐⠑⠻⠐⠀⠼⠁⠐⠖⠼⠃⠀⠙⠮⠁⠁⠱⠂`、各段為 `text ['計','算',' ']`、`math ['1+2']`、`text [' ']`、`text ['的','值']`；以及 `zh-tw.ctb` 對 `" 的值"`、`"  中文"`、`"計算 "` 一次翻譯與拆開翻譯得到相同的點字方，如 results.md 3 節 A。

拆段唯一可見的影響（多一個只含空白的 Dual View 段）視為目前的行為而接受。

### D10. `test_translation_result.py` 改為 `unittest`

同一個檔案，保留 tab，類別為 `BindContractedTokensTest`、`BindWordTokensTest`、`RecleanTokenTest`、`WrapTest`。13 個函式全部變成方法，名稱與預期不變；五個 fixture 依裁決表修正（點字方與位置改為 5/5 與 6/6；`..._blank2` 與 `..._blank3` 改用非空白點字方 `⠁`；`test_remove_start_line_blank` 改為 46 格、`[0, 40, 41]`），每處以一行註解說明原因。`test_end_right_end_sentence_blank` 保持原樣，並以 docstring 說明它鎖定的是空白點字方分支。新增一個測試 `test_space_that_fits_at_the_line_end_stays_there`，以原本 `test_remove_start_line_blank` 的 fixture 鎖定目前的結果 `"...an \nI see"`。14 個測試在未修改的程式碼上全部通過。

### D11. 安全網

1. **假 golden 不變。** `tests/test_translation_golden.py` 與其 fixture 完全不修改；fixture sha256 在每個 commit 都維持 `e67d95a1…211ccd`。
2. **凍結 oracle + 等價測試（所有平台）。** `tests/legacy_translation_result.py` 是 `client/translate.py` 在 `d4a7aa1` 的位元組複本（git blob `10bd641485327b00cb71a14d4946f01a1788f794`），開頭加一段註解，說明它是拆分前的參考實作，永遠不得修改。`tests/test_translation_split_equivalence.py`（4 個空白）先檢查複本的 git blob id（先正規化為 LF，所以不受 `autocrlf` 影響），再以固定 seed 產生隨機案例，從相同的起始狀態分別交給 oracle 與正式類別，比對四個 list、回傳值，以及任何例外的型別與訊息，涵蓋：`bind_contracted_tokens`、`bind_word_tokens`、`insert_token`（隨機索引）、`reclean_token`、`reclean_braille_endspace`、`wrap`（寬度 1-45），以及對 1-3 個結果做完整串接 `concat` -> 修剪 -> `bind_word_tokens` -> `reclean_token` -> `wrap`。產生器：單元取自 ASCII 字母與數字（單一與連續）、多字元單元（`the`、`1+2`、`台灣`）、漢字、假名、諺文、注音、12 個標點集合的每個成員與 `—`、`" "`、`"　"`、`"\n"`，偶爾 `""`；每個單元 0-4 個點字方，取自空白與兩種非空白點字方；大多數案例的對應表格式正確，固定比例的案例使用打亂、過長、過短或超出範圍的對應表，以及任意的 `braille_to_raw_pos` 值（讓 fallback 會被執行）。seed 固定；案例數量讓此模組在 3 秒內跑完。
3. **Windows 真實 liblouis golden。** `tests/test_translation_liblouis_golden.py`（4 個空白）與 `tests/fixtures/translation_liblouis_golden.json`：
   - 略過規則：`ctypes` 沒有 `WINFUNCTYPE`，或 `from braille import louis_helper` 失敗時，在模組層級拋出 `SkipTest`（W-1 的模式；不直接 import `braille.liblouis`）。`setUpClass` 以 `create_default_text_translator()` 與 `create_default_math_translator()` 建立 `TranslationRuntime`；任一個拋出 `RuntimeUnavailableError` 時，以該原因拋出 `SkipTest`（不會默默退回字元 fallback）。Linux 與 CI 會略過；本機 Windows 必須執行（驗收條件）。
   - 設定：一個沒有字典檔的暫存資料夾（沒有規則、沒有前處理腳本）、`lang="zh_TW"`、`DEFAULT_CHARSET_MAPS`，兩組翻譯表：`DEFAULT_TRANSLATION_TABLES`，以及把 `"en"` 換成 `"en-ueb-g2.ctb"` 的同一組。
   - 輸入：`zh_prose`（夾英文詞，含 `，`、`；`、`。`）、`en_prose`（`The quick brown fox ... rests. Testing, (one) [two]!`）、`ja_prose`（漢字、平假名、片假名、`：`、`。`）、`math_mix`（分數、加法、中英混排）、`spaced_math`（`計算 $1+2$ 的值`）、`punctuation`（`「」（）（甲）（乙）『』——`、ASCII 引號、`、`、`[a] {b}`）、`spaces_lines`（前導空白、結尾空白、全形空白、換行）、`numbers`（`1,234`、`USD 40`、`2026/10/09`、`（）`）。每組翻譯表執行：Unicode 寬度 1、10、24、40，以及 ASCII 寬度 40。
   - 每個輸入與翻譯表組合儲存：每次執行的完整 `display_text`；後處理（修剪、`bind_word_tokens`、`reclean_token`）後的完整 token；合併後 list、後處理後 list 與 Dual View 段（在換行後讀取）的標準 JSON 的 SHA-256。一個長案例（`p25_perf.py` 的段落 x 400，寬度 40）只存摘要值。fixture 記錄 `louis_helper.louis.version()`（`3.37.0`）；版本不同時會先失敗，訊息說明只有在有意升級 liblouis 時才可重新產生。原型量測：96 筆、約 15 KB、0.4 秒，兩個行程結果相同。
   - 在 Windows 上、以未修改的正式程式碼，從 `client/` 執行 `python -m tests.test_translation_liblouis_golden --write` 產生一次；本任務之後不再重新產生。
   - 同一模組中的固定測試：`test_p25_document_matches_the_recorded_brl`（`tests/fixtures/p25_doc.txt` 是歷史文件的複本，以 `read_text(encoding="utf-8")` 讀取；Unicode 與 ASCII、寬度 40、預設翻譯表；BRL 位元組 = `display_text` 換成 `\r\n` 行尾後的 UTF-8；sha256 `365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c` 與 `95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64` 取自 results.md 3 節 C，寫在測試中而非 fixture 中；測試也檢查文件文字的 sha256，複本被改動時會被發現）、`test_one_call_equals_split_calls` 與 `test_leading_space_is_its_own_token_with_real_liblouis`（D9）。

## 維持不變的部分（行為不變條件）

- 對任何輸入、翻譯表組合與寬度：Unicode 與 ASCII 模式的點字輸出、BRL 與其他所有匯出、原文換行、合併後與後處理後的對位 list、每個 Dual View 段，以及 Dual View HTML（視窗與匯出）。
- 格式錯誤的對位所拋出的例外（相同型別與訊息、在同一處拋出），因為格式錯誤的輸入走原本的程式路徑。
- `TranslationResult` 的屬性、常數（成員相同、仍是 `frozenset`、`lang_blocks` 仍是唯讀 mapping）、方法、簽章、回傳值，以及哪個方法就地修改或替換哪些 list。
- `conversion.wrapping.merge_translation_results` / `wrap_translation_results`、`conversion.service.*`、`conversion.output.*` 的簽章與行為；`adapters.translation` 套件的匯出。
- `client/tests/fixtures/translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd` 與 `client/tests/fixtures/dictionary_entries_trace.json` sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`（`git show HEAD:<path> | sha256sum`）。
- 已記錄的 BRL 雜湊：Unicode `365d28a9…f9d683c`、ASCII `95b9a1a6…2538bc64`，source run 與 packaged build 皆同。
- 不修改任何字串、選單、對話框、`.po`/`.mo`、`client/braille/`、`client/locales/`、`scripts/` 或打包設定。任何測試都不讀寫 `client/dictionary/`。

## 遷移步驟（單一 branch `refactor/p2-5-translate-split`；每一步一個綠燈 commit）

步驟 1-4 只改測試，在未修改的正式程式碼上進行；步驟 5-10 修改正式程式碼，先紅燈。

1. `test: run test_translation_result under unittest`（D10）。14 個測試，全綠。
2. `test: pin the leading space of a text segment`（D9 的 Linux 部分）。已知的失敗轉綠；全套測試在 Windows 上只剩 F-W6 的 error。
3. `test: pin real liblouis output on Windows`（D11.3）。fixture 在此步、在 Windows 上、以未修改的程式碼產生。
4. `test: add the pre-split oracle and equivalence tests`（D11.2）。必然是綠燈；以一次性的突變檢查（計畫中）證明：刻意在記憶體中改壞某個正式方法時，對應的等價測試會失敗。
5. `refactor: move the translation ports into conversion`（D8）。紅燈：把 `"adapters"` 加進 `HIGHER_LAYERS` 後列出 `conversion` 的四個 import。
6. `perf: trim trailing blank cells in one pass`（D5，第 2 項）。紅燈：計時測試。
7. `perf: insert punctuation separators in one pass`（D6）。紅燈：計時測試。**Q1 已決定為「要」：納入。**
8. `refactor: extract the tokenizer`（D3）。紅燈：`tests/test_conversion_tokenizer.py`（`ModuleNotFoundError`）。
9. `refactor: extract the line wrapper`（D4）。紅燈：`tests/test_conversion_line_wrap.py`。
10. `refactor: move TranslationResult to conversion.alignment`（D1、D2、D7）。紅燈：F 部分的 import 守衛。

步驟 6 與 7 就地修改 `translate.py`；步驟 10 再把結果搬走。每一步都讓假 golden、等價測試以及（在 Windows 上）真實 golden 保持綠燈。每個 commit 訊息結尾都是一個空行加上 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## 測試計畫

全部是 `unittest`；新檔案用 4 個空白，修改的檔案沿用原本的縮排。

### A. 轉換的測試（步驟 1）

依 D10 的 `tests/test_translation_result.py`：14 個測試。

### B. 失敗測試的處理（步驟 2）

`tests/test_conversion_service.py`：放寬的測試與 `test_leading_space_of_a_text_segment_is_its_own_token_and_segment`（D9）。+1 個測試。

### C. Windows 真實 liblouis golden（步驟 3）

依 D11.3 的 `tests/test_translation_liblouis_golden.py`：每個輸入一個測試（8 個，翻譯表組合與各次執行為 subtest）、`test_long_document`、`test_fixture_covers_every_case`、`test_p25_document_matches_the_recorded_brl`、`test_one_call_equals_split_calls`、`test_leading_space_is_its_own_token_with_real_liblouis`。Windows 上 13 個測試；其他平台為一個模組層級 skip。

### D. 等價（步驟 4）

依 D11.2 的 `tests/test_translation_split_equivalence.py`：`test_oracle_is_the_pre_split_translate_py`，加上每個操作一個測試（6 個）與 `test_whole_post_processing_matches_the_oracle`。8 個測試。

### E. 效能守衛（步驟 6、7），位於 `tests/test_translation_result_core.py`

- `LinearTrimTest`：`test_trimming_forty_thousand_tokens_takes_linear_time`（每個 token 一個非空白與一個空白點字方；結果等於以單純切片計算的參考值；上限 2 秒；原型 0.015 秒，目前在本機約 37 秒）、`test_trim_keeps_the_list_objects`（三個 list 前後是同一物件）、`test_malformed_alignment_uses_the_stepwise_trim`（以包裝函式 patch 私有 fallback：打亂的對應表會呼叫它，格式正確的不會）。
- `LinearSeparatorTest`（Q1 =「要」）：`test_inserting_ten_thousand_separators_takes_linear_time`（`」「` 成對，10,000 個分隔空白，見規劃後更正第 4 項；參考值獨立建立；上限 2 秒）、`test_well_formed_alignment_never_calls_insert_token`（`insert_token` 以 `side_effect=AssertionError` patch）、`test_malformed_alignment_inserts_one_by_one`。

計時上限只是後盾；結構測試與 D 部分才是真正的檢查。

### F. 結構守衛（步驟 5、8-10）

- `tests/test_translation_import_isolation.py`：`HIGHER_LAYERS` 加入 `"adapters"`（步驟 5）；`test_adapter_contracts_reexport_the_conversion_ports`（三個名稱是同一批物件；`RuntimeUnavailableError` 定義在 adapters）（步驟 5）；`test_production_modules_do_not_import_translate`（以 AST 掃描 `client/**/*.py`，排除 `tests/`、`.venv/`、`translate.py`）（步驟 10）；`test_alignment_modules_load_no_config_adapters_or_native_code`（子行程：`import conversion.alignment, conversion.tokenizer, conversion.line_wrap, conversion.contracts` 不載入 `config`、`adapters*`、`braille*`、`wx*`、`dual_view*`、`libmathcat_py`）（步驟 10）；`test_tokenizer_and_line_wrap_do_not_import_alignment`（子行程）（步驟 10）。
- `tests/test_conversion_tokenizer.py`（步驟 8）：縮寫範圍；詞級範圍涵蓋 ASCII 連續字元、單一 CJK 字、換行、尾隨鏈（`視。」`）、開頭鏈（`「「嶼`）、緊鄰空白或換行的開頭標點保持獨立、破折號；`」「`、`）（`、空 token 的分隔位置；常數與 `TranslationResult` 提供的是同一批物件。
- `tests/test_conversion_line_wrap.py`（步驟 9）：`wrap_tokens` 在 `WrapTest` 的 fixture 上等於 `TranslationResult.wrap`，且不修改輸入。
- `tests/test_translation_result_core.py`：`test_construction_does_not_build_language_blocks` 的 patch 目標改為 `conversion.tokenizer.build_language_blocks`（步驟 10）；`test_translate_reexports_the_alignment_class`（`translate.TranslationResult is conversion.alignment.TranslationResult`）（步驟 10）。

### 預期數量（Windows，由計畫確認）

基線 `Ran 1143`、`failures=1, errors=1, skipped=5`。步驟 10 完成且 Q1 =「要」時約 1200 個測試：`failures=0`、`errors=1`（只有 F-W6）、`skipped=5`。Linux 上真實 liblouis 模組多一個模組層級 skip。

## 驗收條件

在 `client/` 執行，`$PY = .venv/Scripts/python.exe`，並設定 `PYTHONIOENCODING=utf-8`。

1. `$PY -m unittest discover -s tests`：沒有 failure；唯一的 error 是 `test_case_only_rename_still_renames`（F-W6）。
2. 修正後的路線圖指令：`$PY -m unittest tests.test_translation_result tests.test_translation_result_core tests.test_translation_golden tests.test_translation_split_equivalence tests.test_translation_liblouis_golden tests.test_conversion_tokenizer tests.test_conversion_line_wrap tests.test_conversion_service tests.test_translation_import_isolation -v` 通過，且在本機 Windows 上 `tests.test_translation_liblouis_golden` 的 13 個測試都有執行、沒有 skip。
3. 只在 Windows 執行的模組：`$PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation -v` 的結果與任務前相同。
4. `git show HEAD:client/tests/fixtures/translation_golden.json | sha256sum` 與 `dictionary_entries_trace.json` 的同一指令印出上面的兩個值；`git diff <步驟 3 的 commit> HEAD -- client/tests/fixtures/translation_liblouis_golden.json` 為空。
5. 全套測試以模組順序打亂執行，seed 0-19（與先前階段相同的暫存 harness）：每個 seed 的數量相同，且只有 F-W6 的 error。
6. `git grep -nE "^[[:space:]]*(from translate import|import translate$)" -- client ':!client/tests' ':!client/translate.py'` 沒有輸出；`git grep -n "adapters" -- client/conversion` 沒有輸出。
7. `git diff main --stat -- client/locales client/braille scripts client/dictionary` 為空。
8. 突變檢查（計畫中）：刻意改壞某個操作時，該操作的等價測試與真實 golden 都會抓到；計時測試在修改前的程式碼上會失敗。

## Windows 驗證（可自動執行；實作完成後執行）

在完成的 branch 上，從 repo 根目錄執行。`$PY = client\.venv\Scripts\python.exe`；`$H = docs\superpowers\history\2026-10-09-03-windows-verification`。

1. source run 測試：驗收條件 1-3（真實 golden 有執行，不是 skip）。
2. source run 基線：`$PY $H\p25_baseline.py <out>`。預期：A 節三次 `identical=True`；B 節 raw `['計', '算', ' ', '1+2', ' ', '的', '值']` 與上面的點字；C 節 sha256 `365d28a9…`（unicode）與 `95b9a1a6…`（ascii），兩種模式都是 `trims=13 cells_removed=13`；`fc /b <out>\p25_unicode.brl $H\baseline\p25_unicode.brl` 與 ASCII 的同一比對：沒有差異。（腳本對 `translate.TranslationResult.reclean_braille_endspace` 的 monkeypatch 因 D2 與 D7 仍然有效。）
3. 效能：`$PY $H\p25_perf.py <out> 100 400 1600`。預期：83,200 字時 `reclean` 低於 0.2 秒（原為 28.55 秒；原型 0.053 秒）、`wrap` 低於 2 秒（原為 28.92 秒）。Q1 =「要」時，另以「效能」一節的對話段落 x 3,200 計時 `reclean_token`（計畫中的小腳本）：低於 1 秒（原為 322 秒）。
4. packaged build：執行 `scripts\build-dotexpress.bat`，把 `client\dist\DotExpress.exe` 複製到新的資料夾，並以 pywinauto venv 執行 `$H\auto\item7.py <exe> <工作資料夾> $H\p25_doc.txt`（與 `auto-results.md` 相同）。預期：`p25_unicode.brl` sha256 `365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c`、`p25_ascii.brl` `95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64`，且與 `D:\dxtest\N` 的輸出逐位元組相同。
5. 選擇性，以相同的自動化方式：分別從新 build 與 `main` build 匯出 `p25_doc.txt` 的 Dual View HTML 並比對位元組（假 golden 已鎖定 HTML；這一項加入真實 MathCAT/MathML）。

沒有選單、對話框或字串變更，所以不需要截圖，也不需要執行 `generate-pot.bat`。

## 風險

- **搬移時隱藏的輸出漂移**（影響高、可能性低）。緩解：三張獨立的安全網（假 golden、含格式錯誤案例的 oracle 等價測試、真實 Windows golden 加上 BRL 雜湊），並且在效能步驟之後才搬移，讓每個 diff 都小。
- **線性演算法在某些輸入上不同**（影響高、可能性低）。緩解：只在檢查過格式正確的對位上走快速路徑，其餘走原本的程式碼；D5/D6 的證明概要；包含格式錯誤對應表與任意 `braille_to_raw_pos` 值的隨機等價測試；原型已在 70,000 個隨機案例與所有真實輸出上一致。
- **改縮排時出錯**（影響中、可能性低）。緩解：等價測試會走過每個被搬移的分支；計畫加入一項「忽略空白差異」的比對，把搬移後的本體與 `d4a7aa1` 比較。
- **真實 golden 依賴 liblouis build**（低）。它記錄版本，升級後會以清楚的訊息失敗；屆時重新產生就是既定步驟，與 AGENTS.md 的 liblouis 升級檢查清單相同。
- **`StubScope` 的 eviction 產生第二個 `TranslationResult` 類別**（低）。與目前的 `translate` 情況相同：只有在 scope 內第一次 import 的模組才會被 evict，而在 scope 內 import 它的模組也會一起被 evict。驗收條件 5 涵蓋此情況。
- **慢機器上的計時守衛**（低）。上限約為原型時間的 100 倍，且遠低於舊程式的時間。

## 發現但不在此修正的缺陷

1. UEB 二級中含縮寫的詞可能被斷在兩行（Q2）。這是既有缺陷，P2-5 不改變它，並由真實 golden 鎖定（`ueb_g2/en_prose` 的 token `br`、`ow`、`n`）；修正會改變點字版面，留待使用者決定後另立任務。
2. `wrap` 遇到空的原文 token 會拋出 `IndexError`（`token[-1]`），`bind_word_tokens` 遇到比 `raw` 短的 `raw_to_braille_pos` 也會。沒有任何產生者會建出這兩種情況；維持原樣，由等價測試涵蓋。
3. `language_has_all` 對每個字元建立一個 set（P1-5 已知缺陷 4）。
4. 根目錄 `AGENTS.md` 的「Key Modules」仍描述舊的頂層配置（`translate.py`、`utils.py` 等）。

## 不在範圍內

- 任何斷詞或換行規則的變更，包括 Q2，以及把相鄰的文字 Dual View 段合併。
- `LanguageDetector` 每段建立一次，以及 pipeline 的函式內 import（P1-6 缺陷 3）。
- 進一步拆分 `bind_word_tokens`、為 `DualViewSegment.result` 加上更精確的型別、其他檔案的 P2-8 縮排統一。
