# F-13 Windows 驗證：自動化執行結果（plan Task 6；項目 121–130）

- 日期：2026-10-14，由 Claude（plan 兼實作 agent）執行。
- 受測：`fix/f13-behavior-nvda` 在 Task 4 之後（`a1e699d`，`HEAD:client` `6c352f0225a9167e33e2977b7ad34c7c2427f480`，與 plan 的 tree id 相同）的 packaged build，以下稱 N-f13。
- Build：`scripts\build-dotexpress.bat`（PyInstaller 6.21.0，`Build complete!`），在 worktree `D:\workspace\DotExpress-f13` 內以主簽出的 `client\.venv\Scripts` 置於 `PATH` 最前面建置；`PYZ-00.toc` 確認 `ui\conversion_presenter.py`、`dialog.py` 來自 worktree，`Analysis-00.toc` 確認 `gui.py` 來自 worktree。`D:\dxtest\N-f13\DotExpress.exe`：48,793,062 bytes，sha256 `00DCE0055B93C80F95518188E37D14B56E6F3C33890347587D24E7C8D397708A`。`git status --short -- client scripts` 無輸出。
- 改前對照：`D:\dxtest\N-f12b\DotExpress.exe`（`a147fed` 的程式；48,791,375 bytes，sha256 `0F79EAC81386C2DE53D3E92BBA61DE5414A3114B49902E462AF333270BCEC4C2`），只讀取並由腳本複製到各自的資料夾；執行後大小與 sha256 不變。
- 項目分類（HANDOFF 2026-10-14-01 第 3 節）：121–125、127、129 是 **fix** 項目，在 N-f13 與 N-f12b 都執行；126、128、130 是 **regression** 項目，只在 N-f13 執行，且全部符合預期，所以沒有在 N-f12b 重跑。131 為手動（NVDA），不勾選。
- 方法：pywinauto 0.6.9（UIA 用於訊息框、win32 用於其他視窗）＋ psutil，venv 在 session scratchpad 的 `uia`。所有腳本都經 `auto/safe_run.py`（F-12 的版本，改為 `f13gui`）執行：只在受測程式的視窗位於前景時才送出按鍵，否則停止；前景不是受測程式時，焦點記為 `<another program>`，所以 log 不含其他程式的視窗或元件名稱。**沒有腳本讀寫剪貼簿**；文字一律經由檔案或 `set_edit_text` 進入程式。每個項目在新的 `D:\dxtest\auto<N>-f13`（N-f13）或 `D:\dxtest\auto<N>-f12b-f13`（N-f12b）資料夾執行，一次一個，開始前確認可用記憶體至少 600 MB（`auto/run_item.sh`）；只結束 exe 位於該資料夾下的程序。
- 啟動輔助：`auto/f13gui.py` 的 `start` 等主視窗出現後，回答無效檔案對話框（保留）與每個訊息框（Enter），不論當時是否已有主視窗；每個框記錄 `main_visible`（主視窗是否可見，找不到主視窗時為 `None`）、`owner_is_main`（框的 owner 是否為主視窗）、當時的主視窗標題，以及 `owner_visible`（owner 視窗是否可見，沒有 owner 時為 `None`）；主視窗可見且啟用、1 秒內沒有框、標題不是單獨的 `DotExpress` 時才返回。`safe_run.py` 把 `f8agui.start`、`f8bgui.start`、`dx.launch` 換成 `f13gui` 的版本，所以 126、128、130 用的是原本項目的腳本（未修改），只多印一行 `f13 start: [(視窗, main_visible, owner_is_main, main_title, owner_visible), …]`。
- 焦點：`f13gui.focus` 以 `GetGUIThreadInfo` 讀取程式 UI 執行緒的焦點並對應到主視窗的兩個編輯框（F-9 `focus_check.py` 的作法），另以 UIA 讀取焦點元素（`('Edit', '來源文字')` 等）。
- 腳本：`auto/item121.py`、`auto/startup.py`（122–125、126 的一般啟動與空資料夾）、`auto/item127.py`、`auto/item128.py`（128 (c)）、`auto/item129.py`、`auto/manual131.py`（準備手動項目的資料夾，不啟動程式）；126、128 (a)(b)、130 直接執行 F-8b `item70.py`、`item73.py`，F-8a `item66.py`、`item79.py`，F-12 `item113.py`，F-9 `item85.py`（93），F-7 `item58.py`（idle），F-11 `item95.py`、`item99.py`。輸出在 `D:\dxtest\auto<N>-f13.log` 與 `D:\dxtest\auto<N>-f12b-f13.log`（UTF-8）。

## 與 plan 的偏離與重跑

1. **第一輪的工作資料夾放錯位置（工具問題，全部重跑）。** `run_item.sh` 第一版在雙引號中寫了 `\${NAME}`，資料夾名稱沒有展開，所有項目都在 `D:\dxtest${NAME}`（`D:\dxtest` 的同層，不是 `D:\dxtest\auto*`）執行，而且彼此共用。結果與後來相同，但不符合「每個項目一個新的 `D:\dxtest\auto*` 資料夾」，所以修正後所有項目都在正確的資料夾重跑，舊 log 已刪除，本文只記錄重跑的結果。（修正階段補註，review M-5：刪除的只有這一輪放錯資料夾的 log；第 3 點所說 127 的第一～四輪都是修正之後在 `D:\dxtest\auto127*` 執行的，它們的 log 都還在。）`D:\dxtest${NAME}` 這個資料夾無法由 agent 刪除（安全檢查擋下），**請使用者手動刪除**（裡面只有 exe 副本與測試資料）。
2. **121 (b) 在 N-f12b 第一次：Ctrl+Enter 沒有送達**（`while converting` 時焦點仍在可用的原文編輯框，沒有框）。在新資料夾 `auto121b-r2-f12b-f13` 重跑，結果與預期一致；第一次的 log `auto121b-f12b-f13.log` 保留。
3. **127 的重跑。**
   - 第一輪（`auto127-f13`、`auto127-f12b-f13`）：N-f13 有 3 次、N-f12b 有 1 次 Ctrl+Enter 沒有被程式當成 Ctrl+Enter（原文開頭多了一個字元 `⌂`，轉換沒有開始，所以 `WM_QUERYENDSESSION` 回答 1，程式關閉時把多了字元的原文存檔）。這幾次不是「轉換中登出」，不能算數。
   - 腳本因此改為：送出訊息前確認原文編輯框已停用（轉換中），否則記為 `not converting`、結束該次並多做一次，最多 RUNS + 10 次。
   - 第二輪（`auto127r2-*`）在 N-f13 的第 16 次之後啟動失敗（PyInstaller 的 `Error` 框）：**C: 只剩 0.45 GB**。原因是 onefile exe 每次啟動都解壓到 `%TEMP%\_MEI<n>`（約 100 MB），被結束或隨工作階段訊息結束的程序會留下這個資料夾。我刪除了本次 GUI 執行（N-f13 build 之後）建立、內含 DotExpress 檔案的 95 個 `_MEI*` 資料夾（當時沒有任何 DotExpress 程序在執行），C: 回到 9.5 GB；之後 `run_item.sh` 在每個項目結束後刪除該項目建立、不在使用中的 `_MEI*`。`%TEMP%` 裡另有 90 個 2026-10-09～10-11 建立的 `_MEI*`（約 9 GB，先前任務的 GUI 執行留下），**我沒有動，請使用者決定是否刪除**。N-f12b 的第二輪（`auto127r2-f12b-f13`）在第一次 Ctrl+Enter 前就因 `SetForegroundWindow` 失敗而停止；清理後的第三輪（`auto127r3-f12b-f13`）在第 2 次以 `-1073740940` 結束之後，第 3 次同樣因 `SetForegroundWindow` 失敗而停止（當機後 Windows 暫時保留前景）。
   - 腳本再改為 Ctrl+Enter 失敗時等 3 秒重試（最多 5 次）。第三輪 N-f13（`auto127r3-f13`，busy 檢查版，未用到重試）與第四輪 N-f12b（`auto127r4-f12b-f13`，最終版）各 20 次有效執行，作為正式結果。
4. 其餘項目都一次完成。

## 逐項結果

| # | 類別 | N-f13（改後） | N-f12b（改前） | 判定 |
| --- | --- | --- | --- | --- |
| 121 (a) | fix | 轉換 `alpha` 後立刻 Ctrl+Tab 到 `beta`，轉換中焦點在點字結果編輯框（原文編輯框停用）；框 `錯誤`，main `無法轉換文件「alpha」。`，content `文字處理失敗：boom`；按 Enter 後 **焦點在 `beta` 的原文編輯框（`source editor (enabled True)`，UIA `('Edit', '來源文字')`）**，`beta` 的編輯框仍是 `beta text`／空白；兩個套件仍是待轉換 | 同樣的框；之後焦點在 **點字結果編輯框（UIA `('Edit', '點字結果')`）** | ✔ |
| 121 (b) | fix | 不切換：框只有 `文字處理失敗：boom`；之後焦點在點字結果編輯框（`('Edit', '點字結果')`，O1：維持原狀） | 相同（`auto121b-r2-f12b-f13`） | ✔ |
| 122 | fix | F-8b 70 的工作區（中斷的改名 `alpha` → `gamma`）：「已復原文件」框（`alpha`），**`main_visible True`、`owner_is_main True`、主視窗標題 `DotExpress`、`owner_visible True`**；Enter 後 `docs ['alpha']`、標題 `alpha - DotExpress`、原文 `alpha body`、焦點在原文編輯框；`files ['alpha.dep']`，`gui.log []` | 同一個框，但**找不到主視窗（`main_visible None`），框沒有 owner（`owner_visible None`）**；之後的狀態相同 | ✔ |
| 123 | fix | F-8b 73 的工作區：「已取代字元」框（`alpha`、2 個），`main_visible True`、`owner_is_main True`、標題 `alpha - DotExpress`；內容與 F-8b2 相同（`replaced box content as expected [True]`）；`docs ['alpha', 'beta']`，原文全部保留，焦點在原文編輯框 | 同一個框，**`main_visible False`、沒有 owner**；描述框時前景不是受測程式（`focus '<another program>'`，框沒有取得前景）；之後的狀態相同 | ✔ |
| 124 | fix | F-8a 66 的工作區：無效檔案對話框（`['bad.dep']`），`main_visible True`、`owner_is_main True`、標題 `DotExpress`；保留後 `docs ['alpha']`，焦點在原文編輯框；`files ['alpha.dep', 'bad.dep']` | 同一個對話框，找不到主視窗、沒有 owner；之後相同 | ✔ |
| 125 | fix | `bad.dep`（無效）、`alpha` 中斷的改名（原文含一個 U+0000）、`beta.dep`：依序 **無效檔案對話框 → 「已復原文件」（`alpha`）→ 「已取代字元」（`alpha`、1 個）**，三者都 `main_visible True`、`owner_is_main True`（前兩個時標題 `DotExpress`，第三個時 `alpha - DotExpress`）；之後 `docs ['alpha', 'beta']`、標題 `alpha - DotExpress`、原文 `alpha<U+FFFD>body`、焦點在原文編輯框；`files ['alpha.dep', 'bad.dep', 'beta.dep']` | 同樣的順序與最後狀態；前兩個找不到主視窗，第三個 `main_visible False`，三者都沒有 owner | ✔ |
| 126 | regression | 一般啟動（只有 `alpha`）：沒有框，`docs ['alpha']`、`alpha - DotExpress`、焦點在原文編輯框。空資料夾：`docs ['new']`、`new - DotExpress`、`files ['new.dep']`。F-8b 70、70b、71、72、73 以新的啟動重跑：每一行都與 F-8b2 的記錄相同（70：復原框 `alpha`，`files ['alpha.dep']`，重新啟動與修改後啟動都沒有框；70b：只有一行無法刪除被占住暫存檔的 `gui.log`，重新啟動後已刪除；71、72 不復原；73：取代框 2 個、原文全部保留、切換時寫入 U+FFFD、重新啟動沒有框），差別只在框出現時主視窗已顯示（`f13 start:` 行）。F-8a 66：保留後 `docs ['alpha']`，新增 `bad` 時的框是 F-12 D5 之後的文字（`名稱「bad」已被工作區資料夾中的「bad.dep」使用…`，與 F-12 項目 113 相同），名稱對話框再次出現，`bad.dep unchanged: True`；69：`docs ['new (2)']`、`new.dep unchanged: True`；79：`config.json` 為 `null` 時主視窗出現、`docs ['new']`、`.bak` 為 `b'null'`、`config.log` 一行警告、放大字型後寫入 `font_size 13`。F-12 113：三個訊息與 F-12 的記錄相同，`bad.dep unchanged: True` | 未執行 | ✔ |
| 127 | fix | `auto127r3-f13`：20 次有效執行，每次 `WM_QUERYENDSESSION` 回答 0（2 秒內）、`WM_ENDSESSION` 後 **結束碼 0（20/20），沒有 `-1073740940`**；`dual-view-f13probe.html` 每次都被刪除（**`OnExit` 在 `WM_ENDSESSION` 的路徑上有執行**，證實 spec 對 wx 原始碼的解讀）；`alpha.dep` 仍是待轉換、`beta.dep` 不變，`gui.log []`。補充（非正式結果）：第一、二輪的有效執行（`auto127-f13.log` 17 次、`auto127r2-f13.log` 14 次）也都是 0 | `auto127r4-f12b-f13`：20 次有效執行中 **1 次結束碼 `-1073740940`（`0xC0000374`）**，其餘 0；`OnExit` 同樣每次執行；套件都可讀、`gui.log []`。補充（非正式結果）：第一輪（`auto127-f12b-f13.log`）18 次有效執行中也有 1 次（原記錄誤寫為 19 次，修正階段依 log 更正）、第三輪（`auto127r3-f12b-f13.log`）的 2 次中有 1 次 `-1073740940` | ✔ |
| 128 | regression | (a) F-9 93：`WM_QUERYENDSESSION` 立即回答 0；`轉換完成。結果已儲存到文件「alpha」。`；回到 `alpha` 再轉換時 `WM_ENDSESSION`：結束碼 0；`files ['alpha.dep', 'beta.dep']`、`gui.log []`；與 F-9 的記錄相同。(b) F-7 59（沒有修改時 `WM_QUERYENDSESSION`）：`result 1`、結束碼 0、`alpha` 未改變、`gui.log []`、重新啟動後原文 `alpha body`。(c) 轉換完成（`轉換完成。`）後關閉：結束碼 0，`alpha.dep` 有點字 | 未執行 | ✔ |
| 129 | fix | `raw.csv`：框 `移除無法顯示的列` 的兩行為 **`第 2 列：「抹」的注音「ㄇㄚ  」格式不正確`、`第 3 列：「媽」的注音「 ㄇㄚ」格式不正確`**（空白保留），按鈕 `移除並儲存(S)`、`返回編輯(B)`，焦點 `返回編輯(B)`，owner `自訂字典管理器`；Alt+B 後編輯器仍開著、檔案位元組與時間不變；再按「確定」、Alt+S：檔案為 `text,braille,type\r\n甲乙,⠁⠃,Braille\r\n` | 兩行都是 `「ㄇㄚ」`；其餘相同 | ✔ |
| 130 | regression | F-11 95：框的三種關法（Esc、Enter、Alt+F4）都回到編輯器、檔案不變、焦點 `('Button', '確定')`；Alt+S 後檔案為 `text,braille,type\r\n臺北,⠞⠺,Braille\r\n`（列的文字與 F-11 相同，`dict_badbopo.csv` 的值前後沒有空白）。F-11 99、100：Esc、關閉鈕回到編輯器，Alt+D 放棄，焦點與檔案與 F-11 的記錄相同 | 未執行 | ✔ |

## 觀察

- **舊版的啟動框沒有 owner。** N-f12b 在主視窗顯示前跳出的框與對話框都沒有 owner 視窗（`owner_visible None`），描述「已取代字元」框時前景甚至不是 DotExpress。N-f13 的框都屬於可見的主視窗。這是 F-8b review M-8 所說 NVDA 與 Alt+Tab 找不到它們的原因；NVDA 實際朗讀的情況仍待項目 131。
- **`WM_ENDSESSION` 的當機確實存在，F-13 之後沒有再出現。** 正式結果：N-f13 `auto127r3-f13.log` 20 次有效執行全部結束碼 0；N-f12b `auto127r4-f12b-f13.log` 20 次中 1 次以 `0xC0000374` 結束；這 40 次都刪除了 probe 檔（`probe left False`）。補充（非正式結果，修正階段依 log 重新計算，review M-5）：加上同樣仍在 `D:\dxtest` 的較早幾輪（`auto127-f13.log`、`auto127r2-f13.log`、`auto127-f12b-f13.log`、`auto127r3-f12b-f13.log`；不含第 1 點已刪除的、放錯資料夾的那一輪），N-f12b 在 40 次有效的「轉換中登出」中有 3 次（約 7.5%；原記錄誤寫為 41 次），N-f13 在 51 次中 0 次。這是統計上的證據，加上 Test Plan C 的單元測試。
- **自動測試的資源問題（與程式無關）。** 被結束的 onefile 程序會在 `%TEMP%` 留下約 100 MB 的 `_MEI*`；大量重複啟動的項目（127）一次就會留下數 GB。見「與 plan 的偏離」第 3 點。

## 修正階段（F-13 review M-1、M-2、M-3、M-5；2026-10-14）

- 受測：`fix/f13-behavior-nvda` 在 `68c6bf4`（review 修正 commit）之後的 packaged build，以下稱 N-f13b。Build 方法同上（`scripts\build-dotexpress.bat`，主簽出的 `client\.venv\Scripts` 置於 `PATH` 最前面；PyInstaller 6.21.0、Python 3.13.15，`Build complete!`；`PYZ-00.toc` 確認 `ui\conversion_presenter.py`、`dialog.py` 來自 worktree，`Analysis-00.toc` 確認 `gui.py` 來自 worktree），`HEAD:client` `42826811dc2b5a6d5392098fbfddacba2f1cd1c1`。`D:\dxtest\N-f13b\DotExpress.exe`：48,794,200 bytes，sha256 `78CEA79B5C001CA605651F5B863419379034755E359A6BC003BF9105B460DE4E`。`git status --short -- client scripts` 無輸出。N-f13、N-f12b 與其他 build 沒有動。
- 建置與每個項目開始前：可用記憶體至少 600 MB、F-14 的 agent 沒有在跑重的工作（測試、build、DotExpress）、C: 至少 2 GB；條件不符時等待（本輪多次等待，因同一台機器上其他程式占用記憶體）。
- 重跑的項目：M-1、M-2 改的是啟動載入，所以只重跑啟動相關的 122–125 與 126（一般啟動、F-8b 70、73），只在 N-f13b 執行（改前的結果已在上表）。每個項目在新資料夾 `D:\dxtest\auto<N>-f13b`，一次一個，經 `auto/safe_run.py`。`auto/run_item.sh` 新增 build 名稱 `newb`，並在執行前檢查展開後的資料夾必須是 `D:\dxtest\auto*`（避免第一輪 `D:\dxtest${NAME}` 的問題；每個 log 前一行印出資料夾與 exe）。沒有任何腳本讀寫剪貼簿；只結束 exe 位於該項目資料夾下的程序。
- `_MEI*` 清理改為只刪本項目程序載入的資料夾：新的 `auto/mei_poll.ps1` 在項目執行期間每 0.25 秒記錄 exe 位於該項目資料夾下的 DotExpress 程序所載入的 `%TEMP%\_MEI<n>`，項目結束後 `run_item.sh` 只刪除這些、且沒有任何 DotExpress 程序使用中的資料夾（不再以建立時間判斷，所以不會刪到其他 agent 或使用者的資料夾）。本輪 8 次執行共記錄並刪除 12 個；之前與之後的 `%TEMP%\_MEI*` 都是 90 個（2026-10-09～10-11 的舊資料夾，未動）。

| # | N-f13b（review 修正後） | 與 N-f13 的 log 比較 | 判定 |
| --- | --- | --- | --- |
| 122 | 「已復原文件」框（`alpha`），`main_visible True`、`owner_is_main True`、標題 `DotExpress`、`owner_visible True`；之後 `docs ['alpha']`、`alpha - DotExpress`、原文 `alpha body`、焦點在原文編輯框（UIA `('Edit', '來源文字')`）；`files ['alpha.dep']`、`gui.log []` | 只有一處不同：描述框的那一刻前景還不是 DotExpress（`focus '<another program>'`，N-f13 為 `確定`）；`safe_run` 等到框取得前景才按 Enter（`presses 1`）。框的 owner 與可見性相同 | ✔ |
| 123 | 「已取代字元」框（`alpha`、2 個），`main_visible True`、`owner_is_main True`、標題 `alpha - DotExpress`；內容符合預期；`docs ['alpha', 'beta']`，焦點在原文編輯框 | 相同 | ✔ |
| 124 | 無效檔案對話框（`['bad.dep']`），`main_visible True`、`owner_is_main True`；保留後 `docs ['alpha']`，焦點在原文編輯框；`files ['alpha.dep', 'bad.dep']` | 相同 | ✔ |
| 125 | 依序無效檔案對話框 → 「已復原文件」→「已取代字元」，三者都 `main_visible True`、`owner_is_main True`；`docs ['alpha', 'beta']`、`alpha - DotExpress`、原文 `alpha<U+FFFD>body`、焦點在原文編輯框；`files ['alpha.dep', 'bad.dep', 'beta.dep']`、`gui.log []` | 相同 | ✔ |
| 126 一般啟動 | 沒有框；`docs ['alpha']`、`alpha - DotExpress`、焦點在原文編輯框 | 相同 | ✔ |
| 126 F-8b 70 | 復原框 `alpha`（主視窗可見、屬於主視窗）；`files ['alpha.dep']`；重新啟動與修改後啟動都沒有框；`gui.log []` | 相同 | ✔ |
| 126 F-8b 73 | `auto126-73-r2-f13b`：取代框 2 個（屬於可見的主視窗）、原文全部保留、切換時寫入 U+FFFD、重新啟動沒有框 | 相同 | ✔ |

- **126 F-8b 73 第一次（`auto126-73-f13b`）：工具時序問題，在新資料夾重跑。** 啟動輔助在「已取代字元」框出現之前就返回（`f13 start: []`）：程式在顯示這個框之前已把標題設為 `alpha - DotExpress`，而輔助程式以「標題不是單獨的 `DotExpress`、1 秒內沒有框」判斷載入完成；開始時可用記憶體只有 625 MB，框比平常晚出現。腳本接著送出的 Ctrl+Tab 在框建立之前送達原文編輯框，所以在框開著的期間切換到 `beta`（`alpha.dep` 這時以 U+FFFD 存檔）；之後按 Enter 關閉框，載入以 `beta - DotExpress` 結束。最後的檔案與重新啟動的結果與預期相同，但與 N-f13 的 log 不同，所以依 plan 在 `auto126-73-r2-f13b` 重跑，重跑的 log 除了記憶體數字外與 N-f13 完全相同。這個情況（主視窗顯示後、啟動框出現前的瞬間按下的鍵作用在主視窗上）就是 spec 的預設 O2／風險「文件載入前視窗已可見」，與 review 修正無關；N-f13 也一樣。
- M-1（載入時的未預期例外寫入 `gui.log` 並顯示「無法讀取檔案：…」）與 M-2（啟動框開著時登出）沒有在 GUI 重現：前者要在啟動檢查之後、載入之前讓工作區變得不可讀，後者要在啟動框開著時送 `WM_QUERYENDSESSION`／`WM_ENDSESSION`，都由單元測試涵蓋（`test_gui_document_flows` 的 5 個新測試；在 scratchpad 副本上跑的 8 個 mutant，含 review 存活的 R1，都被抓到）。

## 仍需人工（使用者）

- [ ] **項目 131（NVDA）：** 以 `D:\dxtest\manual131-f13\DotExpress.exe`（N-f13 的副本，工作區已是項目 125 的內容；每次啟動都會復原 `alpha`，重試前請執行 `python auto\manual131.py D:\dxtest\N-f13\DotExpress.exe D:\dxtest\manual131-f13` 重建，需 pywinauto 的 venv；也可以改用含 review 修正的 `D:\dxtest\N-f13b\DotExpress.exe`，把上面指令的 exe 換成它、資料夾換成新的資料夾，這三個啟動框與 N-f13 相同）開啟 NVDA：
  1. 啟動時 NVDA 是否先報讀主視窗，再完整讀出每個啟動框（無效檔案對話框、「已復原文件」、「已取代字元」）？框開著時 Alt+Tab 是否列出 DotExpress，選它是否回到框？
  2. 項目 121 (a)：轉換失敗的框按「確定」後，NVDA 是否報讀原文編輯框？
  3. 項目 129：`第 2 列：「抹」的注音「ㄇㄚ  」格式不正確` 這一行，NVDA 怎麼讀出空白？
