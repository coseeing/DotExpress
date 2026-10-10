# DotExpress client 重構：交接文件（2026-10-10）

- 建立日期：2026-10-10。來源 session：Windows 上的 Claude Code CLI（session `c9251692-6537-4306-992c-fd6377e303d0`）。
- 上一份交接文件：`docs/superpowers/history/2026-10-09-02-handoff/HANDOFF.md`。§1 的工作方式和共同約束仍然有效，本文件只補充這個 session 學到的事。
- 請先讀完本文件，再讀 §3 的必讀文件。下一步是 §5：F-6，接著 F-7。開工前先請使用者確認 §5.3 的四個問題。

## 1. 工作方式（使用者指定，請沿用）

使用者原話：「請逐一自動執行，除非有發現重大問題需要決策的，不然請一個任務完成後自動往下個階段執行」。

每個任務依序走這些步驟：

1. spec：Opus 5.5，effort high。
2. plan：Opus 5.5，effort high。
3. TDD 實作：Opus 5.5，effort high。
4. 全任務 review：Fable 5.1，effort high。
5. Critical／Important 由 Opus 修正後再 merge。便宜的 Minor 也在 merge 前一起修。

這個 session 的實際做法如下，運作良好，請沿用：

**主 session 只當協調者。** 每一步交給 subagent，在背景執行。

**spec 的待決問題。** spec 中「需要使用者決定」的問題，如果有保守、不改變使用者可見行為的預設，協調者先採用預設並往下做。這些決定在 spec 中記為 "Decided by orchestrator with the recommended default; user may override before merge"，同時告訴使用者。只有真正改變使用者可見行為的重大決定，才停下來問。

**plan 要先完整 dry run。** plan agent 在 scratchpad 的 clone 上把整份 plan 跑過一次。要求每個 red／green 輸出、`Ran` 數和每個 commit 的 `HEAD:client` tree id 都完全吻合，才能 commit。實作 agent 用腳本直接套用 plan 中的 File:／Edit: 區塊，不要手打。

**實作 agent 也負責 packaged build 和 GUI 驗證，不要丟給使用者。** 做法：
- build：`client\.venv\Scripts` 放在 PATH 最前面，執行 `scripts\build-dotexpress.bat`，exe 放到新的 `D:\dxtest\N-<任務>`。
- GUI：用 pywinauto 自動化跑，scratch venv 在 `…\scratchpad\uia`。若缺 `python.exe`，用 `py -3.13 -m venv --upgrade` 修復。
- 腳本、`auto-results.md` 和該任務的 history 資料夾一起 commit。
- 只有 NVDA 聽讀、視覺判斷、本機沒有的第三方軟體，才交給使用者手動做。

**review 的輸出位置。** review 寫在 `docs/superpowers/history/<日期>-<序號>-<slug>/review_task.md`，使用繁體中文。修正後在檔尾附「## 修正記錄」，並和修正一起 commit。

**分支與 merge。** branch 命名為 `fix/f<N>-<slug>`。merge 用 `git merge --no-ff -m "merge: <描述> (<任務 ID>)"`，再加第二個 `-m` 放 trailer。merge 後在 main 跑一次完整測試。

**並行。** 任務之間沒有依賴時，可以用 `git worktree add` 在 `D:\workspace\DotExpress-f<N>` 平行做 spec 或 plan。worktree 缺少 git-ignored 的 runtime，要從主 checkout 複製：liblouis DLL 和 tables、`louis_helper.py`、`mathcat/`、`configure.ac`，做法見 F-3 plan 的 Task 0。複製來的檔案絕不能 stage。用完以 `git worktree remove --force` 移除。

commit 訊息結尾：`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。不要 push。

## 2. 共同約束（上一份交接文件的約束加上本 session 的教訓）

- 遵守 `AGENTS.md`，保留使用者可見行為，沿用檔案既有縮排。`client/` 多數檔案用 tab，但有些測試檔用 4 個空白。
- 以下檔案不可修改，或必須保持原樣：
  - NVDA 衍生的 `client/braille/tables/__tables.py`：不修改。
  - vendored 的 `client/braille/liblouis/`：不修改。
  - `client/braille/tables/__init__.py`：CRLF，要逐位元組保留。
- **不要執行 `py scripts\sync-nvda.py`。**
- **使用者真實資料，絕不可動：**
  - `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/`，都是 git-ignored。
  - 在主 checkout 工作時，開始和結束各算一次 sha256，確認沒有變動。不要在主 checkout 以 source run 啟動 `gui.py`。
- 不要動 untracked 的 `client2/`、`preprocessing/`、`testdata/`。
- `AGENTS.md` 被 `.gitignore` 忽略（`.gitignore:14`），改了也不會進 commit。P2-5 的修正曾改過使用者本機的這份檔案，已告知使用者。
- **只 stage 明確路徑**，commit 前先看 `git diff --cached`。不要 stage 使用者可能正在編輯的檔案，例如 test.md。
- `core.autocrlf=true` 帶來的限制：
  - 不要用 MSYS 的 `sed -i`，用 Edit 工具或 Python。
  - `git commit -F -` 會壞掉，用 `-m`。
  - Bash 路徑用正斜線。
- **Edit／Write 工具會把 `"\ud83d\ude00"` 這類 escape 變成真的 emoji。** 測試中需要 surrogate escape 時，用腳本寫入，並檢查檔案位元組。F-5 plan 的 Implementation Notes 1 和 F-5 review 都踩過這個坑。
- 測試必須先經 `braille.louis_helper` 載入 liblouis（見 F-W1）。
- 兩個 fixture 的 sha256 必須永遠不變，用 `git show HEAD:<path> | sha256sum` 計算：
  - `client/tests/fixtures/translation_golden.json`：`e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`
  - `client/tests/fixtures/dictionary_entries_trace.json`：`f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`
- 真實 liblouis 的 golden 是 `client/tests/fixtures/translation_liblouis_golden.json`。liblouis 升級時要重新產生，步驟見 `AGENTS.md` 的 liblouis 升級第 6 步。
- **翻譯字串：**
  - 目前 msgid 共 357 個。
  - 新增字串時依序執行 `scripts\generate-pot.bat`、`msgmerge`，補上 msgstr，再跑 `msgfmt --check --statistics`，結果必須是 0 fuzzy。
  - `.pot` 的 `POT-Creation-Date` 固定為 `2026-10-10 12:00+0800`，讓 tree id 可以重現。
  - 檢查 `msgmerge` 是否把新字串標成 fuzzy，例如 F-5 的 "Cannot Save Document" 被誤配到 "Rename Document"。
- **GUI 自動化要點**（`docs/superpowers/history/2026-10-09-03-windows-verification/auto/`、`…/2026-10-10-01-f5-save-failure-handling/auto/f5gui.py`）：
  - 每個情境在新的 `D:\dxtest\auto*-<任務>` 資料夾執行。
  - 只 kill 該資料夾底下的 process，launcher 的子 process 要用 `taskkill /T`。使用者可能自己開著 DotExpress。
  - wx 的 MessageBox 和 F-5 的關閉對話框都是 task dialog，要用 UIA backend 讀取和操作，見 `f5gui.py`。
  - 鍵盤送給剛出現的對話框時偶爾會漏，`f5gui.answer` 會重送。
  - 前景視窗若被其他程式（例如瀏覽器）占走，點擊會失敗，這是工具問題，不是產品問題。

## 3. 必讀文件

| 文件 | 內容 |
| --- | --- |
| `docs/superpowers/history/2026-10-09-02-handoff/HANDOFF.md` | 上一份交接文件：工作方式、P0～P2 與 F-1／F-2 的歷史 |
| `docs/superpowers/history/2026-10-09-02-handoff/refactor-review.md` | 原始重構審查報告與路線圖 |
| `docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md` | **既有缺陷清單**、Windows 驗證總清單 1–16 |
| `docs/superpowers/history/2026-10-09-01-fix-data-loss/review_task.md` | F-1／F-2 review、驗證清單 17–29、剩餘缺陷清單（含優先序） |
| `docs/superpowers/history/2026-10-09-03-windows-verification/results.md`、`auto-results.md`、`test.md` | Windows 驗證記錄；**F-W1～F-W13**；給使用者的手動測試清單 |
| `docs/superpowers/history/2026-10-09-04-p2-5-translate-split/review_task.md` | P2-5 review |
| `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/review_task.md`、`auto-results.md` | F-3 review（M-1～M-7）、GUI 項目 18–21、30–33 |
| `docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/review_task.md`、`auto-results.md` | F-4 review（M-1～M-7）、GUI 項目 23–29、35 |
| `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/review_task.md`、`auto-results.md` | F-5 review（M-1～M-8）、GUI 項目 36–40、**手動項目 41** |
| `docs/superpowers/specs/2026-10-09-*`、`2026-10-10-*` 與對應的 plans | 每個任務的 spec／plan。spec 內含「Corrected after planning」，plan 末尾有 Implementation Notes |

## 4. 本 session 完成的工作（全部已 merge 進 `main`，最新 `0708f44`，尚未 push）

`main` 比 `origin/main` 多 73 個 commit。目前測試結果：`cd client && .venv\Scripts\python.exe -m unittest discover -s tests` 跑出 `Ran 1307`、`FAILED (errors=1, skipped=7)`。唯一的 error 是既有的 F-W6 `test_case_only_rename_still_renames`。

| 任務 | merge | 摘要 |
| --- | --- | --- |
| W-1～W-3 | 9a4ae81、4b4a2b6、115f57f | Windows 上的測試與工具修正（見 `results.md`） |
| HANDOFF 4.2 | 1db5767、b823cae、1505953、d4a7aa1 | Windows 驗證記錄、手動測試清單 test.md、pywinauto 自動化結果（F-W9～F-W13） |
| P2-5 | 4953772 | `translate.py` 拆成 `conversion/tokenizer.py`、`line_wrap.py`、`alignment.py`、`contracts.py`，`translate.py` 保留為 re-export shim（packaged build 用 `--hidden-import translate` 保留它）；修好已知失敗測試；`reclean_*` 改為線性，8 萬字文件的斷行從 28.9 s 降到 0.44 s，BRL 輸出逐位元組相同 |
| F-3 | b793704 | `.dep` 改為原子寫入（`write_bytes_atomically`）；所有改名都走 `move_document_package`（修好 P1-3 defect 3）；唯讀的 package 拒絕改名（Q2）；被其他程式開著時無法存檔（Q1）；UI 邊界攔截所有 Exception，非 `OSError` 的錯誤寫進 log |
| F-4 | 918c251 | 不合法的注音列和來源文字空白的列原樣保留在原位置（F-W11 選項 A）；新增與隱藏列同名的詞條時拒絕；轉換不變 |
| F-5 | 0708f44 | 沒修改就不寫（以「最後成功寫入的內容＋檔案大小＋修改時間」為基準）；關閉時存檔失敗會跳出「重試／不儲存就關閉／取消」對話框（新增 4 個字串）；其他動作存檔失敗時仍擋下；落單的 surrogate 在存檔時換成 U+FFFD；名稱中含 surrogate 的會被拒絕（M-1） |

使用者對 F-3、F-4、F-5 的待決問題都已確認，或同意採用預設。F-5 的 A～D 是使用者親自決定的。

## 5. 下一步：F-6、F-7

使用者已請協調者分析這四項（F-W9、F-W12、M-5、M-7）。以下是分析結果，§5.3 的問題還在等使用者回覆。

### 5.1 F-6：F-W12，字典資料夾中有讀不到的檔案時，字典管理會靜默打不開（優先）

**問題：** 只要字典資料夾中有任一檔案讀不到，點「字典管理」就完全沒反應，沒有視窗，也沒有訊息。

**成因（已讀程式碼確認）：**
- `DictionaryManagementDialog._load_dictionary_counts`（`client/dialog.py:578-582`）在開啟時，對每個字典呼叫 `load_dictionary_entries` 計算筆數。任何一份拋出例外，對話框就建不起來。
- packaged build 沒有 console，例外也沒寫進 log。
- `refresh_dictionaries`（`dialog.py:584`）也會呼叫它，所以在對話框裡匯入或改名後重新整理時同樣會出事。

**很容易遇到：**
- 已實測 Big5（cp950）的 CSV 會拋出 `UnicodeDecodeError`。
- 繁中 Windows 上，Excel「另存新檔 → CSV（逗號分隔）」預設就是 Big5。使用者用 Excel 編輯字典後存錯格式，字典管理就再也打不開。
- 權限被拒、檔案被鎖、CSV 格式錯誤也會觸發。

**建議方案：**
1. 計算筆數時個別處理每個檔案的例外。讀不到的字典在筆數欄顯示「無法讀取」（新字串），其他字典照常顯示，例外寫進 log。
2. 使用者嘗試編輯那份字典時，顯示具體原因。例如不是 UTF-8 時：「請用 Excel 另存為『CSV UTF-8』」。
3. **不要**自動偵測或讀取 Big5。容易猜錯，而且按確定後會把使用者的檔案默默改寫成 UTF-8。

**spec 階段要一併查清楚：**
- 轉換時選到這份字典會怎樣，是同樣靜默失敗還是有提示。
- 匯入一份 Big5 字典時會怎樣。
- 「讀不到」的字典能不能刪除、改名、匯出。

### 5.2 F-7：F-W9＋M-7＋M-5（錯誤訊息與關閉流程的強化）

**F-W9：對話框按鈕變英文**

問題有兩個：
1. 文件名稱對話框因「已存在」重新顯示時，按鈕變成 `OK`／`Cancel`。
2. 正式程式碼中 19 處 `wx.MessageBox` 的按鈕一律是英文 `OK`。

成因：
1. `localize_standard_buttons`（`client/dialog.py:37-57`，5 處使用）用 `dialog.FindWindowById`。這在 wxPython 是全程式搜尋，可能改到別的視窗的同 ID 按鈕。
2. 沒有設定 `wx.Locale`，也沒有 wx 自己的翻譯檔。

建議：
- a. 只在對話框自己的子視窗裡找按鈕：用 `dialog.FindWindow(id)`，或用 `button_sizer`。
- b. 19 處改用共用的 helper，以 `wx.MessageDialog` 搭配 `SetOKLabel(_("OK"))`，做法同 F-5 已驗證過的 `SetYesNoCancelLabels`。`OK` 已有翻譯，不需要新字串。
- **不做** c（全域設定 `wx.Locale`）。影響面大，packaged build 是否帶有 wx 的翻譯檔也還沒驗證。

**M-7（F-5 review）：落單的 surrogate 仍可能讓轉換或匯出失敗（推理）**
- F-5 只在存 `.dep` 時替換 surrogate。依 D5，編輯框不更新，所以轉換用的 `get_source_text` 仍可能拿到 surrogate。
- 雙視窗 HTML 等匯出會遇到 `UnicodeEncodeError`，但 `_write_single`（`client/documents/export_coordinator.py:99-105`）只攔 `OSError`，錯誤會往外拋。在 packaged build 上的結果是匯出失敗、沒有任何訊息。
- 建議：
  - 在讀取編輯框文字的入口（`get_source_text` 和存檔讀取處）統一替換。不回寫編輯框，維持 D5 的取捨。
  - 匯出也改為攔截所有 Exception：非 `OSError` 的寫進 log，顯示既有的「匯出失敗」訊息。
  - 也檢查 export_all 的批次路徑。

**M-5（F-5 review）：Windows 登出或關機時，`_on_close` 可能重入（推理）**
- 第一次詢問（可以拒絕）時存檔失敗，modal 關閉對話框會開著。這時第二個關閉事件可能在它的事件迴圈中進來，`_on_close`（`client/gui.py` 約 967 行）重入。
- 這不是 F-5 引入的：原本的 modal `wx.MessageBox` 也一樣。
- 建議：
  - 先用 pywinauto 送 `WM_QUERYENDSESSION`／`WM_ENDSESSION`，確認問題確實存在。
  - 加一個 `_closing` 旗標：重入時，可以拒絕的事件就拒絕；不能拒絕的照 D8 處理（寫 log 後關閉）。

### 5.3 待使用者回覆（開工前先問）

1. 是否照「F-6＝F-W12、F-7＝F-W9＋M-7＋M-5」的分法，依此順序做？
2. F-W12 讀不到的字典，筆數欄要怎麼顯示？建議顯示「無法讀取」，選取或編輯時再說明原因。
3. F-W9 確定只做 a＋b，不做 c（全域 `wx.Locale`）？
4. M-7 照 D5 的精神，只替換程式拿到的文字、不改編輯框內容，可以嗎？

## 6. 其他待決與後續項目（尚未排程）

| 項目 | 來源 | 狀態 |
| --- | --- | --- |
| UEB 二級縮寫字在字中間斷行且沒有連字號（`br`/`ow`/`n`、`ov`/`er`……） | P2-5 Q2；P2-5 spec 的 Known Defects | 待使用者決定 |
| F-W6：字典改名只差大小寫時被擋（唯一失敗的測試） | `results.md` | 既有缺陷，未排程 |
| F-W7：`$` 一律被當成 LaTeX 分隔（`NT$ 1,234` 等） | `results.md` | 待使用者決定是否加入跳脫規則 |
| F-W5：`scripts/tests` 的 `test_vendor_helper_snapshot` 在 Windows 上因 CRLF 失敗 | `results.md` | 建議 `.gitattributes eol=lf` 或讓測試正規化換行 |
| Rename、Add、Import 會覆寫磁碟上存在、但不在清單中的 `.dep`；啟動時沒有回收孤兒 `.tmp` | F-3 review M-1 | 建議下一個資料安全任務處理 |
| 編輯框遇到 U+0000 會截斷後面的文字，含 U+0000 的文件下次存檔會遺失後段 | F-5 spec 原型 | 既有問題，列為後續 |
| 隱藏的字典列沒有任何提示；筆數不含隱藏列 | F-4 Q2 | 後續 UX 任務（需要新字串） |
| 轉換仍使用不合法的注音列 | F-4 Q3；P1-6 defect 2 | 後續 |
| `remove` 改為以 identity 刪除 | P2-2 Q4；F-4 review M-2 | 後續 |
| `save_preprocessing_script`、`manager.py` 的 writer、`config.json` 就地寫入 | F-1／F-2 review 優先 3 | 後續：改走 `write_text_atomically` |
| pending 文件匯出 HTML 時用到舊快取 | P1-4 defect 3 | 後續 |
| 其他既有缺陷 | `2026-10-08-03-refactor-p2/review_task.md` 缺陷清單、`2026-10-09-01-fix-data-loss/review_task.md` 剩餘清單 | 參照原清單 |

## 7. 使用者的手動測試（待使用者執行，不可代為勾選）

**請用的 build：** `D:\dxtest\N-f5b\DotExpress.exe`，production 程式碼與 main `0708f44` 相同。

| 項目 | 內容 | 說明位置 |
| --- | --- | --- |
| 9–16、16b | NVDA、路徑、對話框、字典編輯器、設定、轉換、選單 | `2026-10-09-03-windows-verification/test.md` |
| 19 | 用真的 7-Zip 開著 `.dep` 時改名（F-3 之後，兩種共用模式的結果相同） | 同上 |
| 24（可選） | 用真的 Excel／記事本另存 CSV UTF-8 | 同上 |
| 34 | 真的把磁碟寫滿（需要系統管理員權限建立小 VHD） | `2026-10-09-05-f3-dep-atomic-write/auto-results.md` |
| 41 | 用 NVDA 聽 F-5 的關閉對話框，並確認按 X 等於取消 | `2026-10-10-01-f5-save-failure-handling/auto-results.md` 「仍需人工（使用者）」 |

18–29 雖然已自動化通過，但當時是在各任務自己的 build 上跑的。建議使用者在 N-f5b 上抽測。

## 8. 環境與清理

**環境：**
- Windows 11 Pro 10.0.26200。
- `client\.venv`：Python 3.13、wxPython 4.2.5、PyInstaller 6.21.0。
- 已安裝 gettext 0.23（`xgettext`、`msgmerge`、`msgfmt`）。
- Defender 即時保護開啟。
- 本機沒有 7-Zip。

**還保留、尚未清理（test.md §E）：**
- **worktree：** `D:\workspace\DotExpress-6e5819f`（baseline B 的 build 來源）。
- **build：** `D:\dxtest\N`、`B`、`N-p25`、`N-f3`、`N-f4`、`N-f4m`、`N-f5`、`N-f5b`。
- **測試資料：** `D:\dxtest\data`，以及許多 `D:\dxtest\auto*` 資料夾和 log。
- **已 merge 的 branch：**
  - `refactor/p2-5-translate-split`
  - `fix/f3-dep-atomic-write`
  - `fix/f4-keep-invalid-bopomofo-rows`
  - `fix/f5-save-failure-handling`
  - 先前的 `fix/w*` 和 `docs/*`
- 要刪除前，先問使用者。

**scratchpad：** session 專用目錄，裡面有 `uia` venv 和各任務的 dry-run 工具。新 session 的 scratchpad 路徑不同，`uia` venv 需要重建：

```
py -3.13 -m venv <scratchpad>\uia
<scratchpad>\uia\Scripts\pip install pywinauto==0.6.9 psutil
```
