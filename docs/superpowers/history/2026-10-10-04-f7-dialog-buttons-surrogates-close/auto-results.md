# F-7 Windows 驗證：自動化執行結果（plan Task 5、Task 8；項目 53–64）

- 日期：2026-10-10，由 Claude 執行
- 受測：`fix/f7-dialog-buttons-surrogates-close` 在 Task 6 之後（`ea39057`，`HEAD:client` `652dabacc5f65dec492a86672309e9c4da5af8cb`，與 plan 的 tree id 相同）的 packaged build，以下稱 N-f7。五個 client commit 的 tree id（`f6a7409d…`、`79ee79a7…`、`7532bf2a…`、`f9563449…`、`652dabac…`）都與 plan 相同。
- 改前對照：`D:\dxtest\N-f6b\DotExpress.exe`（F-6 審查後的 `aec3c64` 程式碼，與 `fb7aff9` 相同；48,749,506 bytes，sha256 `E1ED0B7712801B01950C08439EAE367D79423D4D1BE7A17A9CFB6514C4283BDA`），只讀取並由腳本複製到各自的資料夾。
- 方法：pywinauto 0.6.9（win32 backend；wx 的訊息框和 F-5 的關閉對話框是 task dialog，用 UIA 讀取）＋ psutil，venv 在 `$SP\uia`。每個情境都在新的 `D:\dxtest\auto<N>-f7`（N-f7）或 `D:\dxtest\auto<N>-f6b-f7`（N-f6b）資料夾執行，exe 複製到該資料夾再啟動。沒有動到 `D:\dxtest\N`、`B`、`N-p25`、`N-f3`、`N-f4*`、`N-f5*`、`N-f6*` 與既有的 `D:\dxtest\auto*` 資料夾。只結束 exe 位於這些資料夾的程序（`dx.kill_under`），`lock.py` 以 `taskkill /T` 結束；執行結束後沒有殘留的 DotExpress 或 `lock.py` 程序。
- 工作階段訊息（58–60）：`WM_QUERYENDSESSION`／`WM_ENDSESSION` 只用 `SendMessageTimeoutW` 從 driver thread 送到受測程序的主視窗。沒有呼叫 `ExitWindowsEx`、`InitiateSystemShutdownEx`、`shutdown.exe` 或 `logoff`，沒有真的登出或關機。
- 腳本：`auto/item53.py`（53、56、57）、`auto/item54.py`（54、55）、`auto/item58.py`（58 `query`、59 `idle`、60 `end`）、`auto/item61.py`（61–63），共用 `auto/f7gui.py`，並沿用 2026-10-09-03 的 `dx.py`、`docs.py`、`dicts.py`、`lock.py` 與 F-5 的 `f5gui.py`、`item38.py`（都未修改）。腳本由 plan Task 5 Step 1 的 `apply_blocks.py` 寫入。輸出在 `D:\dxtest\auto<N>-f7.log` 與 `D:\dxtest\auto<N>-f6b-f7.log`（UTF-8，從 Git Bash 執行）。
- 每個項目都只執行一次，沒有重跑；輸出與 plan Task 8 Step 3 預期表的兩欄逐行一致。

## 0. Packaged build

| 版本 | 結果 |
| --- | --- |
| N-f7 | worktree `D:\workspace\DotExpress-f7`（`ea39057`），主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`）；PyInstaller 6.21.0（Python 3.13.15），`scripts\build-dotexpress.bat` 約 59 秒，log 有 `Build complete!`。`client\build\DotExpress\PYZ-00.toc` 的 `dialog.py`、`ui\message_box.py`、`settings\dialogs.py`、`documents\export_coordinator.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress-f7\client\`。`D:\dxtest\N-f7\DotExpress.exe`，48,752,069 bytes，sha256 `8FB585614AB755A3F2C61CE2439A71899E133A417FA9EAECCD310863EED1819F`。`git status --short -- client scripts` 無輸出（build 產物都是 git-ignored） |

## D9：改前確認（plan Task 5，N-f6b，在 D7 commit 之前）

| # | 結果 |
| --- | --- |
| 58 ✔ 重現 M-5 | `auto58-f6b-f7`：`alpha` 輸入 `alpha edited`，`lock.py` 以 share `r` 鎖住 `alpha.dep`，送 `WM_CLOSE`：出現 `無法儲存文件` 對話框（`main` `儲存文件失敗：[WinError 5] 存取被拒。: '…\.alpha.dep.<random>.tmp' -> '…\alpha.dep'`，按鈕 `['重試(R)', '不儲存就關閉(W)', '取消']`，焦點 `重試(R)`）。從 driver thread 送 `WM_QUERYENDSESSION`（`ENDSESSION_LOGOFF`，timeout 10 s）：**3 秒內有 2 個關閉對話框，呼叫尚未返回**（`close dialogs within 3 s: 2 call: not returned`）。從最上層開始每個按 Esc：`[{'open': 2, 'presses': 1, …}, {'open': 1, 'presses': 1, …}]`，呼叫在內層對話框被回答時才返回：`{'ok': 1, 'result': 0, 'after_s': 3.7}`。之後 `running: True close dialogs: 0`，輸入框 `'alpha edited'`；解鎖、關閉、Enter → `exited ['無法儲存文件']`；`alpha members changed: True text: 'alpha edited'`，`tmp: []`，`gui.log: []`；重新啟動後輸入框 `'alpha edited'`。巢狀的 `_on_close` 確實發生，所以繼續寫 D7（Task 6） |
| 55 ✔ 重現遺失的編輯 | `auto54-f6b-f7`：「文字處理」開著時，字典編輯器的按鈕是 `['新增', '編輯', '刪除', 'OK', 'Cancel']`；新增 `x`／`1` 後按 OK：`windows: ['文字處理'] boxes: None`，重新開啟編輯器 `reopened rows: []`，`d1.csv: b'text,braille,type\r\n'`（只有標頭，那一筆遺失，沒有任何訊息）。「DotExpress 設定」開著時相同（`y`／`2`，`reopened rows: []`，只有標頭）。兩個非 modal 對話框自己的按鈕仍是 `['確定', '取消', '套用']`，按它們的 Cancel 正常關閉 |
| 53、54 改前 | `auto53-f6b-f7`、`auto54-f6b-f7`：「已存在」訊息框 `'buttons': ['OK'], 'focus': 'OK'`；重新顯示的名稱對話框 `buttons ['OK', 'Cancel']`（F-W9）；其餘各行與改後相同 |
| 56、57 改前 | `auto53-f6b-f7`：轉換完成、關於、匯出摘要都是 `'buttons': ['OK'], 'focus': 'OK'`；是／否問題（覆蓋、刪除）與改後相同（系統的 `是(Y)`／`否(N)`，焦點相同） |
| 61–63 改前 | `auto61-f6b-f7`：訊息框 `['OK']`；貼上 U+0041 U+D83D U+0042 後轉換的點字 `⠠⠁⠄⡳⠭⠙⠦⠒⠙⠄⠠⠃`（surrogate 的 escape），`same as for U+FFFD: False`；匯出 HTML：`62 export html: None`（沒有訊息），`alpha.html: False`（留下空檔）；全部匯出 HTML：`63 export all html: None`，`out63: {'alpha.html': False}`（停在 alpha，沒有摘要） |

## 53–64. F-7 項目（N-f7）

`<box X>` 指 `{'title': …, 'main': None, 'content': X, 'buttons': ['確定'], 'focus': '確定', 'presses': 1}`；`<question X, focus F>` 指 `{'title': …, 'main': None, 'content': X, 'buttons': ['是(Y)', '否(N)'], 'focus': F, 'presses': 1}`；`<close dialog>` 指 `{'title': '無法儲存文件', 'main': "儲存文件失敗：[WinError 5] 存取被拒。: '…\.alpha.dep.<random>.tmp' -> '…\alpha.dep'", 'content': '上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。', 'buttons': ['重試(R)', '不儲存就關閉(W)', '取消'], 'focus': '重試(R)'}`。每個 log 都以 `close: exited`（item58.py、item38.py 是 `close: ([], 'exited')`）結束。

| # | 結果 |
| --- | --- |
| 53 ✔ | `auto53-f7`：新增 `alpha` 後再新增一次 `alpha`：`53 box: <box '文件「alpha」已存在。'>`（標題 `錯誤`，Enter 關閉）；**重新顯示的名稱對話框 `buttons ['確定', '取消'] name 'alpha'`**；Esc 取消：`windows: [] docs: ['alpha', 'new']`（清單不變） |
| 54 ✔ | `auto54-f7`：字典管理新增 `d1` 後再新增 `d1`：`54 box: <box '字典「d1」已存在。'>`（標題 `錯誤`）；**`54 shown again: buttons ['確定', '取消'] name 'd1'`**；Esc 後 `['字典管理']` 仍開著，`rows: [['d1', '0'], ['default', '0']]` |
| 55 ✔ | 「文字處理」開著：`open: buttons ['確定', '取消', '套用']`；**編輯器 `['新增', '編輯', '刪除', '確定', '取消']`**；新增 `x`／`1`，按確定：`windows: ['文字處理'] boxes: None`；**重新開啟 `reopened rows: [['x', '1', '一般']]`，`d1.csv: b'text,braille,type\r\nx,1,General\r\n'`**；文字處理自己的按鈕 `['確定', '取消', '套用']`，按它的取消後 `windows: []`。「DotExpress 設定」開著：編輯器按鈕同上，`rows before OK: [['x', '1', '一般'], ['y', '2', '一般']]`，`windows: ['DotExpress 設定：轉譯'] boxes: None`，`reopened rows: [['x', '1', '一般'], ['y', '2', '一般']]`，`d1.csv: b'text,braille,type\r\nx,1,General\r\ny,2,General\r\n'`；設定自己的取消正常關閉（`windows: []`） |
| 56 ✔ | `auto53-f7`：`56 convert: <box '轉換完成。'>`（標題 `資訊`，以 Esc 關閉）；`56 about: {'title': '關於 DotExpress', 'main': None, 'content': 'DotExpress (DotExpress) ...', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}`；`56 overwrite question: <question '目的資料夾中已有一個或多個檔案會被覆蓋。要全部覆蓋嗎？', focus '是(Y)'>`（標題 `確認覆蓋`，回答是）；匯出資料夾中有名為 `alpha.brl` 的資料夾，所以 alpha 失敗：`56 summary: {'title': 'Export Complete with Errors', …, 'content': "Exported documents: 1\nFailed documents: 1\n\nalpha: [Errno 13] Permission denied: '…\out56\alpha.brl'", 'buttons': ['確定'], 'focus': '確定', 'presses': 1}`（標題與內文未翻譯是既有的 P1-4 defect 4，不變）；`out56: ['alpha.brl', 'new.brl'] windows: []` |
| 57 ✔ | `57 delete, no: <question '要刪除文件「alpha」嗎？', focus '否(N)'> docs: ['alpha', 'new']`（標題 `確認刪除文件`，Alt+N）；`57 delete, yes:` 同一個問題，`docs: ['new']`；全部匯出到有 `new.brl` 的資料夾：`57 overwrite question: <question …, focus '是(Y)'>`，回答否：`boxes after no: None`，`out57: ['new.brl'] new.brl: b'old'`（未覆蓋）。是／否仍是系統按鈕，與改前相同 |
| 58 ✔ | `auto58-f7`：`close dialog: <close dialog>`；**`close dialogs within 3 s: 1 call: {'ok': 1, 'result': 0, 'after_s': 0.0}`**（巢狀的關閉被立即否決，Windows 得到「不可結束」）；`esc in each close dialog: [{'open': 1, 'presses': 1, 'call': {'ok': 1, 'result': 0, 'after_s': 0.0}}]`；`running: True close dialogs: 0`；`input: 'alpha edited' title: alpha - DotExpress`；解鎖、關閉、Enter（重試）：`exited ['無法儲存文件']`；`alpha members changed: True text: 'alpha edited' files: ['alpha.dep', 'beta.dep', 'new.dep'] tmp: []`；`gui.log: []`；重新啟動後 `['alpha', 'beta', 'new']`，輸入框 `'alpha edited'` |
| 59 ✔ | `auto59-f7`：`alpha` 沒有修改，送 `WM_QUERYENDSESSION`：沒有對話框，`call: {'ok': 1, 'result': 1, 'after_s': 0.0}`，`exit code: 0`；`alpha members changed: False text: 'alpha body'`，`tmp: []`，`gui.log: []`；重新啟動後輸入框 `'alpha body'` |
| 60 ✔ | `auto60-f7`：同 58 到關閉對話框（`<close dialog>`），送 `WM_ENDSESSION`（`wParam` 1，`ENDSESSION_LOGOFF`）：`call: {'ok': 1, 'result': 0, 'after_s': 0.0}`，`exit code: 0`（wx 直接結束，沒有關閉事件）；`alpha members changed: False text: 'alpha body'`（最後一次成功存檔），`files: ['alpha.dep', 'beta.dep', 'new.dep'] tmp: []`；`gui.log: []`；重新啟動後輸入框 `'alpha body'` |
| 61 ✔ | `auto61-f7`：先輸入 `A` U+FFFD `B` 轉換：`<box '轉換完成。'>`（標題 `資訊`），點字 `⠠⠁⠄⡳⠭⠋⠋⠋⠙⠄⠠⠃`；再貼上 U+0041 U+D83D U+0042 轉換：`<box '轉換完成。'>`；**點字 `⠠⠁⠄⡳⠭⠋⠋⠋⠙⠄⠠⠃`，`same as for U+FFFD: True`**；轉換後輸入框仍是 `U+0041 U+D83D U+0042`（編輯框沒有被改寫） |
| 62 ✔ | 檔案 → 匯出 → HTML（雙視窗）：`62 export html: <box '文件已成功匯出。'>`（標題 `匯出完成`）；`alpha.html: True EF BF BD: True ED A0 BD: False` |
| 63 ✔ | 全部匯出為 HTML 到空資料夾：`63 export all html: <box 'All documents were exported successfully.'>`（標題 `匯出完成`；內文不是 msgid，既有的 P1-4 defect 4）；`out63: {'alpha.html': True, 'new.html': True}`；`windows: [] gui.log: []` |
| 64 ✔ | `auto64a-f7`（F-5 的 38）：Ctrl+Tab 被擋，錯誤框 `('錯誤', ["儲存文件失敗：[WinError 5] 存取被拒。: '…\.alpha.dep.<random>.tmp' -> '…\alpha.dep'", '確定'])`（F-5 時是 `'OK'`）；關閉 → Esc：`running`，輸入框 `'alpha edited'`；鎖住時關閉按 Enter、解鎖再按 Enter：`exited`；三個關閉對話框都與 `<close dialog>` 相同，`presses: 1`；`alpha members changed: True text: 'alpha edited'`，`tmp: []`；重新啟動後輸入框 `'alpha edited'`。`auto64b-f7`（F-5 的 39）：Ctrl+Tab 錯誤框同樣是 `'確定'`；關閉 → Alt+W：`exited`，`presses: 1`；`alpha members changed: False text: 'alpha body'`，`tmp: []`；重新啟動後輸入框 `'alpha body'`。其餘與 F-5 的 `auto-results.md` 相同 |

## 結論

- 所有自動化項目（53–64）的結果都與 plan Task 8 Step 3 的預期表一致，沒有產品缺陷，沒有重跑。
- D9：在 N-f6b 上，58 重現了 M-5（關閉對話框開著時送 `WM_QUERYENDSESSION`，出現第二個關閉對話框，呼叫要等到內層被回答才在 3.7 秒後返回），55 重現了新發現的缺陷（「文字處理」或「設定」開著時，字典編輯器的 OK 不存檔就關閉，編輯遺失）。這些都在 D7 commit 之前確認。
- F-W9 已修正：重新顯示的名稱對話框（53、54）、在非 modal 對話框開著時的字典編輯器（55）都顯示「確定」「取消」；所有只有 OK 的訊息框與關於對話框都顯示「確定」，焦點在它上面，Enter 和 Esc 都能關閉（53、54、56、64）。是／否問題維持系統按鈕與原本的預設焦點（56、57）。
- 字典編輯器的確定按鈕在「文字處理」或「設定」開著時也會存檔（55），那兩個對話框本身不受影響。
- M-7 已修正：貼上的落單 surrogate 在轉換時變成 U+FFFD，點字與輸入 U+FFFD 時相同，編輯框不變（61）；雙視窗 HTML 匯出與全部匯出都成功，檔案中是 `EF BF BD`（62、63）。
- M-5 已修正：關閉對話框開著時的 `WM_QUERYENDSESSION` 被立即否決，只有一個對話框（58）；沒有關閉進行中時照常關閉（59）；`WM_ENDSESSION` 時 wx 直接結束，套件是最後一次成功存檔，沒有 `.tmp`（60）。F-5 的關閉流程不變（64）。

## 仍需人工（使用者）

- [ ] 65（NVDA）：請在 NVDA 執行中檢查 F-7 的按鈕標籤。把 `D:\dxtest\N-f7\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual65-f7\` 執行。(a) 按「檔案 → 新增」建立文件 `alpha`，再按一次「檔案 → 新增」輸入 `alpha` 按 Enter：NVDA 應讀出「錯誤」對話框、內容「文件「alpha」已存在。」與按鈕「確定」；按 Enter 後重新出現的「新增文件」對話框，Tab 到按鈕時應讀出「確定」「取消」（不是 OK、Cancel）。(b) 按「說明 → 關於」：關於對話框的按鈕應讀出「確定」。(c) 在「轉譯 → 文字處理」開著的情況下，開「轉譯 → 字典管理...」新增字典 `d1`，選 `d1` 按「編輯」：編輯器的按鈕應讀出「確定」「取消」；新增一筆後按「確定」，再開一次編輯器，那一筆應該還在。請記錄 NVDA 讀出的內容；如果哪裡仍讀出英文 OK／Cancel，或 (c) 的那一筆不見了，請告訴我們。
