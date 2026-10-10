# F-9 Windows 驗證：自動化執行結果（plan Task 7；項目 85–93）

- 日期：2026-10-10 至 2026-10-11，由 Claude 執行
- 受測：`fix/f9-conversion-target-document` 在 Task 5 之後（`b18112e`，`HEAD:client` `2fffcc5e1cefbfe656061f1c477dcdaadd00115a`，與 plan 的 tree id 相同）的 packaged build，以下稱 N-f9。五個 client commit 的 tree id 都與 plan 相同：Task 1 `3ec0e95` `503c9ef1…`、Task 2 `dd25bcc` `1635c495…`、Task 3 `33fc5ed` `c1207cf7…`、Task 4 `4347c5a` `abd8058b…`、Task 5 `b18112e` `2fffcc5e…`。
- 改前對照：`D:\dxtest\N-f8b2\DotExpress.exe`（F-8b 審查修正後的 build，`HEAD:client` `f6bd18c9…`，即 `7aba2be` 的程式；48,763,199 bytes，sha256 `BC30BB3687B451A6B66C9E4FB9F6A7F71E65341C31647C25E27A46581DEB7445`），只讀取並由腳本複製到各自的資料夾。
- 方法：pywinauto 0.6.9（win32 backend；wx 的訊息框是 task dialog，用 UIA 讀取）＋ psutil，venv 在 `$SP\uia`。需要幾秒鐘的轉換來自很長的原文：`f9gui.LONG_REPEAT` = 8000 份 65 個字元的中英混合句子（520,000 個字元），由腳本以 `zipfile` 寫入待轉換（pending）的套件，一次轉換約 15 秒。按鍵在 Ctrl+Enter 之後立刻送出，早於 2 秒後才出現的轉換中對話框。每個按鍵都經過 `f9gui.keys`：先確認主視窗是前景視窗才送出，否則停止該項目（沒有按鍵會送到別的程式）。每個情境都在新的 `D:\dxtest\auto<N>-f9`（N-f9）或 `D:\dxtest\auto<N>-f8b2-f9`（N-f8b2）資料夾執行，exe 複製到該資料夾再啟動。沒有動到 `D:\dxtest\N`、`B`、`N-p25`、`N-f3`、`N-f4*`、`N-f5*`、`N-f6*`、`N-f7`、`N-f8a`、`N-f8a2`、`N-f8b`、`N-f8b2` 與既有的 `D:\dxtest\auto*` 資料夾。只結束 exe 位於這些資料夾的程序（`dx.kill_under`）；執行期間使用者沒有開著 DotExpress，結束後沒有殘留的 DotExpress 程序。沒有任何腳本讀寫剪貼簿：長文字只經由套件檔案進入程式。
- 腳本：`auto/item85.py`（85–88、93）、`auto/item89.py`（89–92），共用 `auto/f9gui.py`，並沿用 F-8b 的 `f8bgui.py`，以及透過它的 F-8a `f8agui.py`、F-7 `f7gui.py`、F-5 `f5gui.py` 與 2026-10-09-03 的 `dx.py`、`docs.py`、`dicts.py`、`lock.py`（都未修改）。腳本由 plan Task 7 Step 2 的 `apply_blocks.py` 寫入。輸出在 `D:\dxtest\auto<N>-f9.log` 與 `D:\dxtest\auto<N>-f8b2-f9.log`（UTF-8，從 Git Bash 執行）。
- 18 個 log 都與 plan Task 7 Step 4 的預期區塊逐行一致（`diff --strip-trailing-cr` 無差異）。只有一次重跑：N-f8b2 的項目 93 第一次（`auto93-f8b2-f9.log`）在 `WM_ENDSESSION` 後的結束碼是 `-1073740940`（`0xC0000374`），其餘各行與預期相同；依 plan 在新資料夾 `auto93b-f8b2-f9` 再跑一次，結束碼 `0`，log 與預期一致。見「觀察」。

## 0. Packaged build

| 版本 | 結果 |
| --- | --- |
| N-f9 | worktree `D:\workspace\DotExpress-f9`（`b18112e`），主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`）；PyInstaller 6.21.0（Python 3.13.15），`scripts\build-dotexpress.bat` 約 52 秒，log 有 `Build complete!`。`client\build\DotExpress\PYZ-00.toc` 的 `ui\conversion_presenter.py`、`conversion\jobs.py`、`documents\workspace_service.py`、`documents\export_coordinator.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress-f9\client\`。`D:\dxtest\N-f9\DotExpress.exe`，48,767,217 bytes（plan dry run 的 build 是 48,767,328），sha256 `5DE1ACDB864D1FDF7C2BC68479B42985ACCFFD6EC46A3A93030E4861ACA0B4E9`。`git status --short -- client scripts` 無輸出（build 產物都是 git-ignored）。`.mo` 經由 `--add-data "locales;locales"` 打包，85、87、93 顯示新的字串 |

## 85–93. F-9 項目

訊息框寫成 `{'title': …, 'main': …, 'content': …, 'buttons': ['確定'], 'focus': '確定'}`，用 UIA 讀取（訊息沒有空行時沒有主指示，`main` 是 `None`）；按了幾次 Enter 不列出。`<d>` 是該項目的工作資料夾，`<rnd>` 是暫存檔名稱的亂數部分。長文字寫成 `<長度 chars '開頭'...>`；編輯框的文字以 `WM_GETTEXT` 讀取，換行是 `\r\n`，所以 520,000 個字元的原文在編輯框中是 528,000 個字元，套件中的點字 983,999 個字元在編輯框中是 1,007,998 個字元。下文的「alpha 的點字」指 `<983999 chars '⠁⠮⠐⠊⠱⠐'...>`（套件）／`<1007998 chars …>`（編輯框）。85–88、93 的工作區：`alpha` 是很長的待轉換文件（開啟中），`beta` 的原文是 `beta body`、點字 `⠃`。

| # | N-f9（改後） | N-f8b2（改前） |
| --- | --- | --- |
| 85 ✔（spec 9a） | `auto85-f9`：在 `alpha` 按 Ctrl+Enter，立刻 Ctrl+Tab 到 `beta`。轉換中：標題 `beta - DotExpress`，`beta` 的編輯框 `'beta body'`／`'⠃'`，沒有訊息框。轉換結束：**`{'title': '資訊', 'content': '轉換完成。結果已儲存到文件「alpha」。'}`**；之後 `beta` 的編輯框仍是 `'beta body'`／`'⠃'`；**`alpha.dep` 已寫入 alpha 的點字**（不再是 pending），`beta.dep` 不變；沒有第二個訊息框。Ctrl+Tab 回 `alpha`：點字編輯框顯示 alpha 的點字，沒有訊息框。關閉（`exited`）後兩個套件相同，`gui.log []`；重新啟動後 `alpha` 顯示 alpha 的點字 | `auto85-f8b2-f9`：訊息框只有 `'轉換完成。'`，此時 **`beta` 的點字編輯框顯示 alpha 的點字**；`alpha.dep` 仍是 pending。Ctrl+Tab 回 `alpha`：點字是空的。關閉後 **`beta.dep` 的點字被寫成 alpha 的點字**，`alpha.dep` 仍是 pending；重新啟動後 `alpha` 的點字是空的（**缺陷 1**） |
| 86 ✔（spec 9b） | `auto86-f9`：Ctrl+Enter，轉換中 Ctrl+Tab 再 Ctrl+Shift+Tab 回 `alpha`：訊息框 `'轉換完成。'`（**今天的路徑**：結束時開著的是起始文件），`alpha` 的點字編輯框顯示 alpha 的點字；`alpha.dep` 在關閉時寫入（之前仍是 pending，與今天相同）；`beta.dep` 不變；重新啟動相同 | `auto86-f8b2-f9`：每一行都與改後相同 |
| 87 ✔（spec 9c） | `auto87-f9`：Ctrl+Enter，立刻 Ctrl+O 匯入 `data\imported.txt`（匯入後開啟 `imported`）：轉換中 `docs ['alpha', 'beta', 'imported']`，標題 `imported - DotExpress`，原文 `'imported text'`。訊息框 **`'轉換完成。結果已儲存到文件「alpha」。'`**；`imported` 的點字編輯框仍是空的；`alpha.dep` 已寫入 alpha 的點字；關閉後 `files ['alpha.dep', 'beta.dep', 'imported.dep']`，`gui.log []`；重新啟動後 `alpha` 有點字 | `auto87-f8b2-f9`：訊息框 `'轉換完成。'`，**`imported` 的點字編輯框顯示 alpha 的點字**；`alpha.dep` 一直是 pending；重新啟動後 `alpha` 的點字是空的 |
| 88 ✔（spec 9d） | `auto88-f9`：同 85，但轉換中 `lock.py` 以共用讀取開著 `alpha.dep`（`lock: locked r`）。轉換結束：**只有存檔錯誤框** `{'title': '錯誤', 'content': "儲存文件失敗：[WinError 5] 存取被拒。: '<d>\\\\workspace\\\\.alpha.dep.<rnd>.tmp' -> '<d>\\\\workspace\\\\alpha.dep'"}`，**沒有「轉換完成」框**；`beta` 的編輯框不變；`alpha.dep` 仍是 pending（套件沒被改）。解除鎖定後 Ctrl+Tab 到 `alpha`：點字編輯框已有 alpha 的點字（記憶體中已更新），沒有訊息框；再 Ctrl+Tab 到 `beta`：兩次切換後 `alpha.dep` 已寫入 alpha 的點字，`beta.dep` 不變；關閉、重新啟動相同，`gui.log []` | `auto88-f8b2-f9`：訊息框 `'轉換完成。'`（結果送到 `beta`，`alpha.dep` 沒被寫入，所以鎖定沒有影響）；`beta` 的點字編輯框顯示 alpha 的點字；之後的 Ctrl+Tab 把 alpha 的點字寫進 **`beta.dep`**，`alpha.dep` 一直是 pending |
| 89 ✔（spec 9e） | `auto89-f9`：只有 `alpha`（很長、pending）。Ctrl+Enter，立刻在點字結果編輯框按 Ctrl+S 匯出到 `<d>\out\alpha.brl`：訊息框依序為 **`'轉換完成。'`**（之後點字編輯框顯示 alpha 的點字）與 **`{'title': '匯出完成', 'content': '文件已成功匯出。'}`**，沒有第三個；`out {'alpha.brl': <983999 chars …>}`；關閉 `exited` | `auto89-f8b2-f9`：Ctrl+S 啟動第二個轉換，和還在跑的第一個同時執行；**程式自己結束，沒有任何訊息框**（`the app has ended by itself, exit code nonzero: True`）；`out {}`，`alpha.dep` 仍是 pending。Windows 的應用程式記錄：`DotExpress.exe`、`ntdll.dll`、例外碼 `c0000374`，路徑 `D:\dxtest\auto89-f8b2-f9\DotExpress.exe`（spec 修正 14） |
| 90 ✔（spec 9f） | `auto90-f9`：`p1`、`p2`、`p3`（都很長、pending），開著 `p1`。檔案 → 全部匯出 → BRL 到 `<d>\out`，第一個轉換中在點字結果編輯框按 Ctrl+S 匯出到 `<d>\out2\p1.brl`：訊息框依序為 **`'文件已成功匯出。'`**（Ctrl+S 的匯出，排在 Export All 的第一步之後）與 **`'All documents were exported successfully.'`**（全部匯出的摘要），沒有第三個；`out` 有 `p1.brl`、`p2.brl`、`p3.brl`，`out2` 有 `p1.brl`，四個檔案都是完整的點字；關閉 `exited` | `auto90-f8b2-f9`：**程式自己結束，沒有任何訊息框**；`out {}`、`out2 {}`。應用程式記錄：`ntdll.dll`、`c0000374`，`D:\dxtest\auto90-f8b2-f9\DotExpress.exe` |
| 91 ✔（spec 9g） | `auto91-f9`：匯入 `data\pend.txt`（開啟待轉換的 `pend`）。檔案 → 匯出 → Dual View HTML 到 `<d>\out\pend.html`：`'文件已成功匯出。'`，**`pend.html` 有 23 個段落，沒有 "No conversion data"**。全部匯出 → Dual View HTML 到 `<d>\outall`：摘要框；**`pend.html` 有 23 個段落**；`new.html` 仍是 "No conversion data" 頁面（預設文件 `new` 不是 pending、點字是空的，spec 的範圍外第一項，改前改後相同）。之後 `pend` 的點字編輯框仍是空的，`pend.dep` 仍是 pending（匯出不改變文件與快取） | `auto91-f8b2-f9`：兩次匯出的 `pend.html` 都是 **0 個段落、"No conversion data"** 頁面；其餘相同 |
| 92 ✔（spec 9h） | `auto92-f9`：只有 `alpha`（很長、pending）。Ctrl+Enter 後送 `WM_CLOSE`：視窗留著（`running True`，沒有訊息框）；轉換結束出現 `'轉換完成。'`；再關閉：`exited`；`alpha.dep` 有 alpha 的點字，`gui.log []` | `auto92-f8b2-f9`：每一行都與改後相同 |
| 93 ✔（spec 9i） | `auto93-f9`：同 85（Ctrl+Tab 到 `beta`），轉換中送 `WM_QUERYENDSESSION`（`ENDSESSION_LOGOFF`）：**立即回傳 0（拒絕）**，程式繼續執行；之後 **`'轉換完成。結果已儲存到文件「alpha」。'`**，`alpha.dep` 已寫入。Ctrl+Tab 回 `alpha`，Ctrl+Enter，轉換中送 `WM_ENDSESSION`（wParam 1）：結束碼 **0**；`files ['alpha.dep', 'beta.dep']`，`gui.log []`，`alpha.dep` 保有第一次的點字，`beta.dep` 不變 | `auto93-f8b2-f9`（第一次）：`WM_ENDSESSION` 後結束碼 **`-1073740940`**（`0xC0000374`；應用程式記錄有 `ntdll.dll`、`c0000374`，`D:\dxtest\auto93-f8b2-f9\DotExpress.exe`），其餘各行與預期相同。`auto93b-f8b2-f9`（重跑）：`WM_QUERYENDSESSION` 同樣回傳 0；訊息框 `'轉換完成。'`，結果送到 `beta`；`WM_ENDSESSION` 後結束碼 0；`alpha.dep` 仍是 pending，**`beta.dep` 被寫成 alpha 的點字** |

## 結論

- 所有自動化項目（85–93）在兩個 build 上的結果都與 plan Task 7 Step 4 的預期區塊一致。只有 N-f8b2 的 93 重跑一次（結束時的當機碼，見下方「觀察」）。
- D1–D3：轉換結果送到按下「轉換」時開著的文件。使用者在轉換中切換（85、93）或匯入（87）時，開著的文件的編輯框不受影響（訊息框關閉後的焦點見下方「審查修正後的重跑」），結果立刻存進起始文件的套件，並以新的訊息框「轉換完成。結果已儲存到文件「alpha」。」告知；切回起始文件就看到結果，重新啟動後也還在。轉換中切走再切回（86）走今天的路徑，訊息框仍是「轉換完成。」。存檔失敗（88）只顯示存檔錯誤，不顯示完成訊息；結果留在記憶體中，之後的切換時寫入。改前結果送到結束時開著的文件，並在切換或關閉時寫進那份文件的套件（85、87、88、93 的 `beta.dep`／`imported` 被寫入 alpha 的點字，`alpha` 一直是 pending）。
- D4、D5：轉換中要求的匯出（89 的 Ctrl+S、90 的 Export All 加 Ctrl+S）排隊依序執行，每個訊息框都出現，所有檔案都寫出。改前第二個轉換與第一個同時執行，在這麼長的文字下程式當機（`ntdll.dll`、`c0000374`）。
- D6：待轉換文件的 Dual View HTML 匯出（單一匯出與全部匯出）顯示這次新轉換的段落，不再是 "No conversion data" 頁面；文件與快取不變（91）。
- D8：轉換中關閉被擋下，結束後可以正常關閉（92，改前改後相同）；登出查詢在轉換中被拒絕，之後的結果仍正確送到起始文件（93）。

## 觀察（非 F-9 造成，不阻擋）

- **`WM_ENDSESSION` 時的當機碼（spec 修正 11）**：轉換中收到 `WM_ENDSESSION` 時，程式偶爾以 `-1073740940`（`0xC0000374`，結束時的 heap 損毀）結束，而不是 0。plan 的 dry run 只在 F-9 的 build 上看過一次（五次中的一次）；這次是在**改前的 N-f8b2** 上出現（`auto93-f8b2-f9`），N-f9 的 `auto93-f9` 結束碼是 0。這證實它是既有的行為：wx 3.2.9 在 `WM_ENDSESSION` 時不送 close 事件（F-7 項目 60），沒有 F-9 的程式碼會執行，Windows 在工作執行緒仍在轉換時結束程序。套件沒有損壞（`alpha.dep`、`beta.dep` 都可讀）。
- **改前兩個轉換同時執行會當機（spec 修正 14）**：89、90 在 N-f8b2 上都以 `ntdll.dll` 的 `c0000374` 結束，與 dry run 的四次相同。F-9 的佇列一次只執行一個轉換，所以改後兩個訊息框都出現。
- **英文的摘要字串**：全部匯出成功的摘要 `'All documents were exported successfully.'` 在中文介面仍是英文（90、91，改前改後相同）。這是既有缺陷（P1-4 defect 4，F-7 審查已記錄），與 F-9 無關。

## 審查修正後的重跑（2026-10-11，N-f9b）

審查 M-6：在 N-f9 上，(b) 的訊息框關閉後焦點停在 `beta` 唯讀的點字結果編輯框。修正（`f755e3c`）讓 (b) 的訊息框（D2 訊息或存檔錯誤）關閉後，若主視窗是作用中視窗，焦點移到開著文件的原文編輯框（spec「審查後的修正」第 1 點）。

- Build：`fix/f9-conversion-target-document` 在 `f755e3c`（`HEAD:client` `a64da653f7348440a9a8b7419cb9aaea1e7a3440`），同樣以主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面執行 `scripts\build-dotexpress.bat`，約 64 秒，log 有 `Build complete!`；`PYZ-00.toc` 的四個模組與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress-f9\client\`。`D:\dxtest\N-f9b\DotExpress.exe`，48,765,092 bytes，sha256 `B5AD9BFA9DA0C73F87C8FA547C1E7BDD1771A50E142E14EE1D86F37DD1AB83DD`。沒有動到 `N-f9`、`N-f8b2` 與其他 build（`N-f9` 只被腳本讀取、複製，sha256 仍是 `5DE1ACDB…`）。
- 會受影響的是 (b) 的項目：85、87、88、93 在新資料夾 `D:\dxtest\auto<N>-f9b` 重跑，四個 log 與 N-f9 的 `auto<N>-f9.log` 逐行相同（`diff --strip-trailing-cr` 無差異；93 的 `WM_ENDSESSION` 結束碼 0）。86、89–92 不經過 (b)，沒有重跑。
- 焦點：新腳本 `auto/focus_check.py`（沿用審查的 `focus_probe.py` 做法：以 `GetGUIThreadInfo` 讀取程式 UI 執行緒的焦點，對應到主視窗的兩個編輯框）。85 的流程，以及 88 的流程（`lock.py` 鎖住 `alpha.dep`，訊息框是存檔錯誤）：

| 步驟 | N-f9b（修正後）`auto85focus-f9b`、`auto88focus-f9b` | N-f9（修正前）`auto85focus-before-f9b`、`auto88focus-before-f9b` |
| --- | --- | --- |
| 開始，`alpha` 開著 | 原文編輯框 | 相同 |
| Ctrl+Enter 之後 | 點字結果編輯框（原文編輯框停用） | 相同 |
| Ctrl+Tab 到 `beta` 之後 | `beta` 的點字結果編輯框 | 相同 |
| 訊息框 | 85：`'轉換完成。結果已儲存到文件「alpha」。'`；88：`'儲存文件失敗：[WinError 5] 存取被拒。…'` | 相同 |
| 按 Enter 關閉訊息框之後 | **`beta` 的原文編輯框（已啟用）**；`beta` 的編輯框內容不變 | `beta` 的點字結果編輯框（唯讀） |
| Ctrl+Tab 回 `alpha` | 原文編輯框，點字結果編輯框顯示 alpha 的點字 | 相同 |

  兩個 build 上的程式都正常關閉（`exited`），沒有殘留的 DotExpress 程序；執行期間使用者沒有開著 DotExpress，只結束 exe 位於這些資料夾的程序。沒有腳本讀寫剪貼簿。
- 沒有自動驗證的部分：轉換在 Ctrl+S 的檔案對話框開著時結束的情況（`IsActive()` 為 false，焦點不動）只有單元測試，沒有 GUI 實測。

## 仍需人工（使用者）

- [ ] 94（NVDA）：請在 NVDA 執行中，把 `D:\dxtest\N-f9b\DotExpress.exe`（審查修正後的 build）複製到新資料夾 `D:\dxtest\manual94-f9b\`，用 `auto/item85.py` 準備項目 85 的工作區（或把 `D:\dxtest\auto85-f9\workspace` 的初始內容複製過去：`alpha` 是很長的待轉換文件，`beta` 是短文件），然後：(1) 開啟 `alpha`，在原文編輯框按 Ctrl+Enter，立刻按 Ctrl+Tab 切到 `beta`；約 15 秒後出現「轉換完成。結果已儲存到文件「alpha」。」訊息框：記錄 NVDA 是否讀出文件名稱，以及按「確定」後焦點是否在 `beta` 的原文編輯框、NVDA 是否唸出它（修正後的預期；修正前停在唯讀的點字結果編輯框）；(2) 切回 `alpha`，按 Ctrl+Enter 後立刻在點字結果編輯框按 Ctrl+S 並存檔：記錄兩個訊息框（「轉換完成。」與「文件已成功匯出。」）是否依序讀出。若有讀不到或焦點跑掉的情形，請告訴我們。
