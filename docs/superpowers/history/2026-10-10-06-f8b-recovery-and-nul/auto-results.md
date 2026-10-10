# F-8b Windows 驗證：自動化執行結果（plan Task 4；項目 70–75）

- 日期：2026-10-10，由 Claude 執行
- 受測：`fix/f8b-recovery-and-nul` 在 Task 2 之後（`af0bac9`，`HEAD:client` `667b2d2ce22f0a32996f68aa12eaaf23bc980071`，與 plan 的 tree id 相同）的 packaged build，以下稱 N-f8b。兩個 client commit 的 tree id（Task 1 `348f320` `b61ee7ab…`、Task 2 `af0bac9` `667b2d2c…`）都與 plan 相同。
- 改前對照：`D:\dxtest\N-f8a2\DotExpress.exe`（F-8a 審查修正後的 build，`HEAD:client` `1d6780c8…`；48,756,071 bytes，sha256 `9944656AA3DE4D7E9E089463FA2650878E9DAA5E082550635F240641AC1782FE`），只讀取並由腳本複製到各自的資料夾。
- 方法：pywinauto 0.6.9（win32 backend；wx 的訊息框是 task dialog，用 UIA 讀取）＋ psutil，venv 在 `$SP\uia`。每個情境都在新的 `D:\dxtest\auto<N>-f8b`（N-f8b）或 `D:\dxtest\auto<N>-f8a2-f8b`（N-f8a2）資料夾執行，工作區由腳本先建好（套件與暫存檔以 `zipfile` 寫入，暫存檔的修改時間以 `os.utime` 設定；`zero.txt` 與 `code0.pdf` 以原始位元組寫入），exe 複製到該資料夾再啟動。U+0000 只經由檔案進入程式。沒有動到 `D:\dxtest\N`、`B`、`N-p25`、`N-f3`、`N-f4*`、`N-f5*`、`N-f6*`、`N-f7`、`N-f8a`、`N-f8a2` 與既有的 `D:\dxtest\auto*` 資料夾。只結束 exe 位於這些資料夾的程序（`dx.kill_under`）；每次執行都以 `close: exited` 正常結束，結束後沒有殘留的 DotExpress 程序。沒有任何腳本讀寫剪貼簿。
- 腳本：`auto/item70.py`（70–72）、`auto/item73.py`（73–75），共用 `auto/f8bgui.py`，並沿用 F-8a 的 `f8agui.py`，以及透過它的 F-7 `f7gui.py`、F-5 `f5gui.py` 與 2026-10-09-03 的 `dx.py`、`docs.py`、`dicts.py`（都未修改）。腳本由 plan Task 4 Step 2 的 `apply_blocks.py` 寫入。輸出在 `D:\dxtest\auto<N>-f8b.log` 與 `D:\dxtest\auto<N>-f8a2-f8b.log`（UTF-8，從 Git Bash 執行）。
- 每個項目都只執行一次，沒有重跑；12 個 log 與 plan Task 4 Step 4 的預期區塊逐行一致（`diff --strip-trailing-cr` 無差異）。
- 審查修正（`review_task.md` 的 I-1 與 M-5）之後重新 build 為 N-f8b2，重跑 70–75 並新增 70b，見最後的「審查修正後的重新檢查（N-f8b2）」。第 0 節與「70–75. F-8b 項目」是審查前的記錄，保留不改。

## 0. Packaged build

| 版本 | 結果 |
| --- | --- |
| N-f8b | 主 checkout `D:\workspace\DotExpress`（`af0bac9`），`client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`）；PyInstaller 6.21.0（Python 3.13.15），`scripts\build-dotexpress.bat` 約 55 秒，log 有 `Build complete!`。`client\build\DotExpress\PYZ-00.toc` 的 `documents\workspace.py`、`documents\workspace_service.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress\client\`。`D:\dxtest\N-f8b\DotExpress.exe`，48,763,113 bytes，sha256 `8A07EBD3961B6D0FEE0D2548D893CECAF294195E5B2CDE1FFA70351E9FE6117E`。`git status --short -- client scripts` 無輸出（build 產物都是 git-ignored） |

## 70–75. F-8b 項目

訊息框寫成 `{'title': …, 'main': …, 'content': …, 'buttons': ['確定'], 'focus': '確定', 'presses': 1}`，用 UIA 讀取：wx 把訊息的第一段顯示為 task dialog 的主指示（`main`），其餘為內容（`content`）。`<U+FFFD>` 代表 U+FFFD（腳本如此輸出），`\x00` 是 `repr` 中的 U+0000；編輯框的文字以 `WM_GETTEXT` 讀取，所以換行是 `\r\n`。下文的「復原框」指 `{'title': '已復原文件', 'main': 'DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：', 'content': '<名稱>\n\n請確認內容是否正確。', …}`，「取代框」指 `{'title': '已取代字元', 'main': '文件「<名稱>」中有 <數量> 個無法顯示的字元，已全部以替代字元 <U+FFFD> 標示，後面的文字都保留下來了。', 'content': '轉譯前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。', …}`；兩者都只有 `確定`，焦點在 `確定`，按一次 Enter 關閉。每個 log 都以 `close: exited` 結束。

| # | N-f8b（改後） | N-f8a2（改前） |
| --- | --- | --- |
| 70 ✔ | `auto70-f8b`：中斷的改名（`alpha` → `gamma`）：工作區只有移到旁邊的 `.alpha.dep._vw4x6f_.tmp`（一小時前）與暫存的 `.gamma.dep.mlw4jang.tmp`（內容相同），沒有 `.dep`。啟動：主視窗出現前顯示**復原框，名稱 `alpha`**；`docs ['alpha']`，標題 `alpha - DotExpress`，原文 `'alpha body'`；`files ['.gamma.dep.mlw4jang.tmp', 'alpha.dep']`，**`.tmp left unchanged: True`**（暫存的 gamma 留在原處、位元組不變）。重新啟動：**沒有任何訊息框**，清單、文字、檔案都相同。第三次啟動（plan 的補充，見下方「待決問題」）：把 alpha 的文字改成 `alpha edited`、關閉、再啟動：**復原框，名稱 `gamma`**；`docs ['alpha', 'gamma']`，原文 `'alpha edited'`，`files ['alpha.dep', 'gamma.dep']` | `auto70-f8a2-f8b`：沒有訊息框；`docs ['new']`（新的預設文件），原文空白；`files ['.alpha.dep._vw4x6f_.tmp', '.gamma.dep.mlw4jang.tmp', 'new.dep']`，兩個 `.tmp` 不變；重新啟動相同。**文件 alpha 不見了**（只存在於暫存檔中），所以第三次啟動沒有執行（`70 alpha is not listed; nothing edited`） |
| 71 ✔ | `auto71-f8b`：已完成的改名留下的舊檔（`gamma.dep` 與 `.alpha.dep.7gdjw2yi.tmp`，內容相同，一小時前）：沒有訊息框；`docs ['gamma']`，原文 `'gamma body'`；`files ['.alpha.dep.7gdjw2yi.tmp', 'gamma.dep']`，`.tmp left unchanged: True`；重新啟動相同（**不復原**：清單中的 gamma 已有相同內容） | `auto71-f8a2-f8b`：每一行都與改後相同 |
| 72 ✔ | `auto72-f8b`：中斷的儲存（`alpha.dep` 的 `saved text` 與較新的 `.alpha.dep.97dc8315c5cf865f.tmp` 的 `newer text`）：沒有訊息框；`docs ['alpha']`，原文 `'saved text'`（套件的內容）；`files ['.alpha.dep.97dc8315c5cf865f.tmp', 'alpha.dep']`，`.tmp left unchanged: True`；重新啟動相同（**不復原**：名稱 alpha 已被使用） | `auto72-f8a2-f8b`：每一行都與改後相同 |
| 73 ✔ | `auto73-f8b`：`alpha.dep` 的文字是 `first line\nsecond\x00 after\nthird`、點字 `⠁\x00⠃`，`beta.dep` 沒有 U+0000。啟動：主視窗出現前顯示**取代框，`alpha`、2 個**；`docs ['alpha', 'beta']`，標題 `alpha - DotExpress`，**原文 `'first line\r\nsecond<U+FFFD> after\r\nthird'`（全部文字都在）**；此時 `alpha.dep` 仍是原本的位元組（`\x00`）。Ctrl+Tab 到 beta、Ctrl+Shift+Tab 回 alpha：**都沒有第二個訊息框**；原文不變；切換時存檔，`alpha.dep` 變成 `('first line\nsecond<U+FFFD> after\nthird', '⠁<U+FFFD>⠃')`；關閉後相同；重新啟動：沒有訊息框，原文相同 | `auto73-f8a2-f8b`：沒有訊息框；**原文只有 `'first line\r\nsecond'`**（在第一個 U+0000 處截斷）；第一次切換就把 `alpha.dep` 寫成 `('first line\nsecond', '⠁')`，`after`、`third` 與點字的 `⠃` 都遺失（**資料遺失**）；重新啟動後原文仍是 `'first line\r\nsecond'` |
| 74 ✔ | `auto74-f8b`：檔案 → 匯入 `data\zero.txt`（位元組 `A\x00B tail\r\nline 2`）：文件開啟並顯示**取代框，`zero`、1 個**；`docs ['new', 'zero']`，標題 `zero - DotExpress`，原文 `'A<U+FFFD>B tail\r\nline 2'`；關閉後 `zero.dep` 是 `('A<U+FFFD>B tail\nline 2', '')`；重新啟動沒有訊息框，`docs ['new', 'zero']` | `auto74-f8a2-f8b`：沒有訊息框；原文只有 `'A'`；關閉後 `zero.dep` 是 `('A', '')`（`B tail` 與第二行遺失） |
| 75 ✔ | `auto75-f8b`：一起匯入 `zero.txt` 與 `code0.pdf`（未加標籤的 PDF，文字字串含 code 0，匯入為 `A\x00B\n`）：匯入時**沒有訊息框**；`docs ['code0', 'new', 'zero']`，仍停在 `new`。檔案 → 開啟 `code0`：**取代框，`code0`、1 個**，原文 `'A<U+FFFD>B\r\n'`；開啟 `zero`：**取代框，`zero`、1 個**，原文 `'A<U+FFFD>B tail\r\nline 2'`；再開啟 `code0`：**沒有訊息框**，原文相同。關閉後 `zero.dep` `('A<U+FFFD>B tail\nline 2', '')`、`code0.dep` `('A<U+FFFD>B\n', '')`；重新啟動沒有訊息框 | `auto75-f8a2-f8b`：都沒有訊息框；兩份文件的原文都只有 `'A'`；關閉後 `zero.dep`、`code0.dep` 都是 `('A', '')` |

## 結論

- 所有自動化項目（70–75）在兩個 build 上的結果都與 plan Task 4 Step 4 的預期區塊一致，沒有產品缺陷，沒有重跑。
- D3–D5：只存在於暫存檔中的文件（中斷的改名）在啟動時以原本的名稱放回，並用「已復原文件」告知（70）；已完成的改名留下的舊檔、套件旁中斷的儲存都不復原（71、72）。沒有任何檔案被刪除或取代：沒有復原的 `.tmp` 位元組不變。改前 70 的文件 alpha 在清單中消失，程式改用新的預設文件。
- D12–D14：U+0000 在文件進入程式的地方（啟動時載入的套件、匯入的 TXT 與 PDF）變成 U+FFFD，編輯框拿到全部文字，下一次存檔寫入的是取代後的文字（73–75）。每份文件在本次執行中第一次開啟時顯示一次「已取代字元」，說明文件名稱與字元數；啟動時的第一份文件在主視窗出現前顯示（73），單獨匯入時在文件開啟後顯示（74），一次匯入多份時在各自開啟時顯示（75）。改前編輯框在第一個 U+0000 處截斷，下一次存檔就把後面的文字從套件中刪掉（73–75 的資料遺失）。

## 待決問題（plan Spec Corrections 13；已由使用者決定）

使用者已於 2026-10-10 決定：啟動時，復原決定不使用的暫存檔會被刪除（spec「規劃後的修正（F-8b）」第 10 點，審查 I-1）。審查修正後，項目 70 的 staged 暫存檔在第一次啟動就被刪除，第三次啟動不再出現訊息框（見「審查修正後的重新檢查（N-f8b2）」）。保存某段文字唯一副本的殘留檔（例如項目 72 中斷存檔的較新文字）保留不刪（Decided by orchestrator with the recommended default; user may override before merge）。以下是審查前的觀察，保留不改：

項目 70 的第三次啟動：復原 alpha 之後，暫存的 `.gamma.dep.mlw4jang.tmp` 依 D3 留在原處。只要 gamma 這個名稱沒有被使用、且清單中沒有內容相同的文件，每次啟動都會再檢查一次；使用者修改 alpha 之後，下一次啟動就把這個暫存檔以舊的內容復原成新文件 `gamma`，並顯示「已復原文件」（名稱 `gamma`）。資料沒有遺失，但可能在當機很久之後多出一份文件。是否要避免（例如記住已處理過的暫存檔，或把它們改名離開這個樣式，後者會改到使用者的檔案）需要使用者決定；本次依 spec 的 D3 實作。

## 審查修正後的重新檢查（N-f8b2）

- 日期：2026-10-10，由 Claude 執行。受測：`fix/f8b-recovery-and-nul` 在審查修正的程式 commit 之後（`f853059`，`HEAD:client` `f6bd18c91dd1ccf78ff1c6d248f31df000d7337b`），以下稱 N-f8b2。改動：啟動時刪除復原不使用的暫存檔（I-1），以及 U+0000 訊息框第二段的「轉譯前」改為「轉換前」（M-5）。
- Build：主 checkout，`client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`）；PyInstaller 6.21.0，`scripts\build-dotexpress.bat` 約 43 秒，log 有 `Build complete!`；`PYZ-00.toc` 的 `documents\workspace.py`、`documents\workspace_service.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress\client\`。`D:\dxtest\N-f8b2\DotExpress.exe`，48,763,199 bytes（N-f8b 是 48,763,113），sha256 `BC30BB3687B451A6B66C9E4FB9F6A7F71E65341C31647C25E27A46581DEB7445`。`git status --short -- client scripts` 無輸出。沒有動到 `N-f8b`、`N-f8a2` 或其他既有的 build 與 `auto*` 資料夾。
- 方法與第 0 節相同（同一個 `$SP\uia` venv、UIA 讀訊息框），腳本是更新後的 `auto/item70.py`（新增 70b，並在每次啟動印出 `log\gui.log` 去掉時間戳記的各行）與 `auto/item73.py`（每個「已取代字元」訊息框都與 `f8bgui.REPLACED_CONTENT` 比對）。每個項目都在新的 `D:\dxtest\auto<N>-f8b2` 資料夾執行一次，沒有重跑；70b 的「改前」在 `D:\dxtest\auto70b-f8a2-f8b2`（N-f8a2）。輸出在同名的 `.log`。每次執行都以 `close: exited` 結束，結束後沒有殘留的 DotExpress 程序；沒有結束任何程序（70b 開著檔案的 `lockshare.py` 在 30 秒後自己結束，`70b holder ended by itself: 0`）。沒有任何腳本讀寫剪貼簿。
- 失敗的刪除在 `gui.log` 記為 `[ERROR]`，不是審查設計中的 `WARNING`：`dotexpress.gui` 與它的 `gui.log` handler 不記錄低於 `ERROR` 的訊息（`log.get_logger` 的預設），警告不會寫進檔案。

| # | N-f8b2（審查修正後） | 對照 |
| --- | --- | --- |
| 70 ✔ | `auto70-f8b2`：中斷的改名（同第 0 節）。啟動：**復原框，名稱 `alpha`**；`docs ['alpha']`，原文 `'alpha body'`；**`files ['alpha.dep']`**（staged 的 `.gamma.dep.mlw4jang.tmp` 內容與復原的 alpha 相同，已刪除）；`gui.log []`。重新啟動：沒有訊息框，其餘相同。把 alpha 改成 `alpha edited` 後第三次啟動：**沒有訊息框**；`docs ['alpha']`，原文 `'alpha edited'`，`files ['alpha.dep']` | N-f8b（`auto70-f8b`）：`.gamma.dep.mlw4jang.tmp` 留著；第三次啟動顯示復原框，名稱 `gamma`，`docs ['alpha', 'gamma']`。N-f8a2：沒有訊息框，alpha 不見 |
| 70b ✔（新增） | `auto70b-f8b2`：`alpha.dep`、空的 `.beta.dep.k2j1abcd.tmp`、內容為 `not a zip` 的 `.alpha.dep.0123456789abcdef.tmp`，以及被 `lockshare.py` 以共用讀取開著、內容為 `not a zip` 的 `.gamma.dep.x2y3z4w5.tmp`。啟動：沒有訊息框；`docs ['alpha']`；**`files ['.gamma.dep.x2y3z4w5.tmp', 'alpha.dep']`**（前兩個已刪除，被開著的留著且位元組不變）；`gui.log` **只有一行** `[ERROR] Cannot remove unused temporary file D:\dxtest\auto70b-f8b2\workspace\.gamma.dep.x2y3z4w5.tmp: [WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用。: '<同一路徑>'`。關閉；開著的程式自己結束；重新啟動：沒有訊息框；**`files ['alpha.dep']`**；`gui.log` 仍是同一行（沒有新的） | `auto70b-f8a2-f8b2`（N-f8a2）：兩次啟動都沒有訊息框，三個 `.tmp` 都留著且不變，沒有 `gui.log` |
| 71 ✔ | `auto71-f8b2`：已完成的改名留下的舊包：沒有訊息框；`docs ['gamma']`，原文 `'gamma body'`；**`files ['gamma.dep']`**（內容相同的 `.alpha.dep.7gdjw2yi.tmp` 已刪除）；`gui.log []`；重新啟動相同 | N-f8b 與 N-f8a2：`.alpha.dep.7gdjw2yi.tmp` 留著 |
| 72 ✔ | `auto72-f8b2`：中斷的存檔：沒有訊息框；原文 `'saved text'`；`files ['.alpha.dep.97dc8315c5cf865f.tmp', 'alpha.dep']`，`.tmp left unchanged: True`（**較新文字的唯一副本，保留**）；`gui.log []`；重新啟動相同 | N-f8b：除了新增的 `gui.log` 行以外，每一行都相同 |
| 73 ✔ | `auto73-f8b2`：取代框的內容是 **`'轉換前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。'`**（`replaced box content as expected [True]`）；其餘每一行（原文全部保留、切換時寫入 U+FFFD、重新啟動沒有訊息框）都與 `auto73-f8b` 相同 | N-f8b：內容是「轉譯前…」 |
| 74 ✔ | `auto74-f8b2`：匯入 `zero.txt` 的取代框內容是新的文字（`[True]`）；其餘與 `auto74-f8b` 相同 | N-f8b：「轉譯前…」 |
| 75 ✔ | `auto75-f8b2`：匯入時沒有訊息框；開啟 `code0`、`zero` 的取代框內容都是新的文字（`[True]`、`[True]`）；再開啟 `code0` 沒有訊息框；其餘與 `auto75-f8b` 相同 | N-f8b：「轉譯前…」 |

結論：審查修正後，啟動時刪除復原不使用的暫存檔（70 的 staged 雙胞胎、71 的舊包、70b 的空檔與非 zip 檔），保留較新文字的唯一副本（72），刪不掉的檔案（被另一個程式開著）留著並在 `gui.log` 記一行，下次啟動再刪；不再出現「之後的某次啟動多出一份文件」（70 第三次啟動）。U+0000 訊息框的第二段是「轉換前…」（73–75）。沒有新的使用者可見字串，刪除不會顯示訊息。

## 仍需人工（使用者）

- [ ] 83（NVDA）：請在 NVDA 執行中，把 `D:\dxtest\N-f8b2\DotExpress.exe`（審查修正後的 build；原本寫的是 `N-f8b`）複製到新資料夾 `D:\dxtest\manual83-f8b\`，並用下列方式準備工作區後啟動：(1) 項目 73 的工作區（`alpha.dep` 的文字含 U+0000）：記錄 NVDA 對「已取代字元」對話框讀出的內容，特別是替代字元 �（U+FFFD）怎麼念（例如「替代字元」、「問號」或完全不念），以及按「確定」後焦點是否回到原文編輯框；(2) 項目 70 的工作區（只有 `.alpha.dep._vw4x6f_.tmp` 與 `.gamma.dep.mlw4jang.tmp`）：記錄 NVDA 對「已復原文件」對話框讀出的內容。兩個工作區可以用 `auto/item73.py`、`auto/item70.py` 建好後，把 `D:\dxtest\auto73-f8b\workspace`、`D:\dxtest\auto70-f8b\workspace` 的初始內容複製過去，或請我們幫忙準備。如果 NVDA 沒有讀出文件名稱、字元數或替代字元，請告訴我們。(3)（審查 M-8）這兩個訊息框都出現在主視窗顯示之前，工作列上還沒有 DotExpress 的按鈕：請在程式啟動時先切到另一個程式，記錄 NVDA 是否讀出訊息框，以及能否用 Alt+Tab 回到它。若有問題，會列入 F-12（UI 修飾）。
