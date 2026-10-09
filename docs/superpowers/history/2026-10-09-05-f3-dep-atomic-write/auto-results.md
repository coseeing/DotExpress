# F-3 Windows 驗證：自動化執行結果（plan Task 8；項目 18–21、30–33）

- 日期：2026-10-09，由 Claude 執行
- 受測：`fix/f3-dep-atomic-write` 在 Task 6 之後（`fa888ff`，`HEAD:client` `d79139ec…`）的 packaged build，以下稱 F3
- 方法：用 pywinauto 0.6.9（win32 backend）＋ psutil 7.2.2 操作 packaged exe 的真實 GUI，訊息框文字用 UIA 讀取。每個項目都在新的 `D:\dxtest\auto<N>-f3` 資料夾執行（exe 會複製到該資料夾再啟動），沒有動到 `D:\dxtest\N`、`D:\dxtest\B`、`D:\dxtest\N-p25`。只結束 exe 位於這些 `auto*-f3` 測試資料夾的程序（`dx.kill_under`、`taskkill /T`）。
- 腳本：18、19、20、21 沿用 `2026-10-09-03-windows-verification/auto/` 的腳本（未修改），以 `auto/rerun.py` 在記憶體中把 exe 與資料夾換成 F3；19、21 從 18 結束後的資料夾複製開始（`--seed`）。20b 本來就接受參數。30–33 是新腳本（`auto/item30.py`–`item33.py`，共用 `auto/f3gui.py`）。輸出記錄在 `D:\dxtest\auto<N>-f3.log`（UTF-8，從 Git Bash 執行）。
- `.dep` 是 zip，每次存檔時間戳記都會變；「內容不變」比對的是 zip 內各成員的名稱與內容（`docs.ws_state`），不是整個檔案的位元組。

## 0.1 Packaged build

| 版本 | 結果 |
| --- | --- |
| F3 | worktree `D:\workspace\DotExpress-f3`，主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面；PyInstaller 6.21.0，`scripts\build-dotexpress.bat` exit 0，約 60 秒，log 有 `Build complete!`。`client\build\DotExpress\PYZ-00.toc` 的 `documents\workspace.py`、`documents\workspace_service.py`、`shared\atomic_write.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress-f3\client\`，沒有主 checkout 的模組。`D:\dxtest\N-f3\DotExpress.exe`，48,732,768 bytes，sha256 `C3F7B0068AE5C737F923A74FAFF1F65BFFB07E23255B946B13A12A737CDD8CFD`。`git status` 無輸出 |

## 18–21. 文件只改大小寫、鎖定、唯讀、Defender（F3）

| # | 結果 |
| --- | --- |
| 18 ✔ | 新增 `Alpha`、輸入內文、重新啟動：內文在。改名為 `alpha`：`workspace\` 只有 `alpha.dep`、`new.dep`，沒有 `.tmp`；重新啟動後清單 `['alpha', 'new']`，內文 `'Alpha body 中文內容 123'`。新增 `ALPHA`：`文件「ALPHA」已存在。`；改 `new` 為 `Alpha`：`文件「Alpha」已存在。`；兩次 `disk diff: {}`。與 N 相同。第一次執行時，`ALPHA` 的錯誤框按 OK 的點擊沒有生效（框仍在，主視窗停用），腳本在下一步 `ElementNotEnabled` 中止；手動檢查確認再按一次 OK 後名稱對話框正常重新出現。F3 沒有改動新增文件的流程（`b823cae` 到 F-3 起點之間 `client/` 無差異，F-3 在 `gui.py` 只改三行 `except`），判定為 GUI 自動化的時序問題，重跑一次通過（第一次的 log：`D:\dxtest\auto18-f3.try1.log`） |
| 19 r ✔ | `alpha.dep` 由另一程序以只共用讀取開著（`lock.py … r`）時改名 `alpha`→`Alpha`：改名前的存檔失敗，`儲存文件失敗：[WinError 5] 存取被拒。: 'D:\\dxtest\\auto19-f3\\workspace\\.alpha.dep.3b06566cf242b9f3.tmp' -> 'D:\\dxtest\\auto19-f3\\workspace\\alpha.dep'`，名稱對話框沒有出現。清單 `['alpha', 'new']`，`diff: {}`，檔案只有 `alpha.dep`、`new.dep`（沒有 `.tmp`）；解鎖後重新啟動，清單與內容不變。N 的訊息是 `[Errno 13] Permission denied: '…alpha.dep'`，與 spec 預期的變化相同 |
| 19 rw ✔ | 共用讀寫（`lock.py … rw`）：**與只共用讀取相同**（Q1）：`儲存文件失敗：[WinError 5] 存取被拒。: '…\\.alpha.dep.7131dfb5203bae52.tmp' -> '…\\alpha.dep'`，沒有名稱對話框，`diff: {}`，沒有 `.tmp`，重新啟動後不變。N 是存檔成功、改名失敗 `[WinError 32]` |
| 20 ✔ | `attrib +r alpha.dep`（開著的文件）後改名：`儲存文件失敗：[Errno 13] Permission denied: 'D:\\dxtest\\auto19-f3\\workspace\\alpha.dep'`，沒有名稱對話框；清單、內容不變，`alpha.dep` 仍是唯讀。關閉時存檔又失敗（同一訊息），關閉被擋，腳本最後結束程序（`STILL RUNNING -> killed`，F-W10）。`attrib -r` 後沒有 `.tmp`。與 N 相同 |
| 20b ✔ | 開著的 `Alpha.dep` 設唯讀後改名 `Alpha`→`alpha`：`儲存文件失敗：[Errno 13] Permission denied: 'D:\\dxtest\\auto20b-f3\\workspace\\Alpha.dep'`，沒有名稱對話框；清單 `['Alpha', 'new']`，檔案只有 `Alpha.dep`、`new.dep`；關閉被擋（F-W10）。與 N 相同 |
| 21 ✔ | Defender 即時保護開啟（`True`），連續 10 次 `alpha`↔`Alpha`：10 次都成功，`failures: 0`，每次清單都只有一個 `alpha.dep`／`Alpha.dep` 與 `new.dep`，沒有 `.tmp`，`content same (ignoring name): True`。第一次執行時在第一次改名前 `w.set_focus()` 的 `SetForegroundWindow` 被 Windows 拒絕（前景鎖定，app 尚未收到任何操作），結束該測試資料夾的程序、刪除資料夾後重跑通過（第一次的 log：`D:\dxtest\auto21-f3.try1.log`） |

## 30–33. F-3 新項目（F3）

| # | 結果 |
| --- | --- |
| 30 ✔ | 開著 `alpha`，`beta.dep` 由另一程序開著時把（未開啟的）`beta` 改名為 `gamma`。只共用讀取：`儲存文件失敗：[WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用。: 'D:\\dxtest\\auto30-f3\\workspace\\beta.dep' -> 'D:\\dxtest\\auto30-f3\\workspace\\.beta.dep.lp_07841.tmp'`。共用讀寫：同一訊息（`.beta.dep.2pxgzthh.tmp`）。兩次清單都是 `['alpha', 'beta', 'new']`，`diff: {}`，檔案 `['alpha.dep', 'beta.dep', 'new.dep']`，沒有 `gamma.dep`，`tmp: []`。解鎖後重新啟動：清單相同，`beta` 內文 `'beta body'`。改前（spec）：`gamma.dep` 與 `beta.dep` 都留在磁碟，重新啟動後兩個都列出 |
| 31 ✔ | `attrib +r beta.dep`（未開啟）後改名：`beta`→`gamma` 與 `beta`→`Beta` 都是 `儲存文件失敗：[Errno 13] Permission denied: 'D:\\dxtest\\auto31-f3\\workspace\\beta.dep'`；兩次 `diff: {}`、`tmp: []`，`attrib` 仍是 `R`。`attrib -r` 後重新啟動：`['alpha', 'beta', 'new']`。改前（spec）：一般改名 `[WinError 5]` 且留下兩個 package；只改大小寫會成功並留下唯讀 `.tmp`（Q2） |
| 32 ✔ | 開著的 `alpha.dep` 設 `attrib +h`（`A   H`），輸入 `alpha typed while hidden`，切換到 `beta`：沒有訊息，標題 `beta - DotExpress`；`alpha.dep` 不再隱藏（`attrib` 只剩 `A`），`tmp: []`，磁碟上的內文 `'alpha typed while hidden'`。重新啟動後清單 `['alpha', 'beta', 'new']`，開啟 `alpha` 內文相同。改前（spec）：`[Errno 13]`，切換被擋 |
| 33 ✔ | Defender 即時保護開啟（`True`），每次先修改內文再切換文件，共 20 次：20 行都是 `ok [] []`，`failures: 0`，沒有任何 `[WinError 5]`。關閉後磁碟上 `alpha` 為 `'alpha edit 19'`、`beta` 為 `'beta edit 20'`，檔案 `['alpha.dep', 'beta.dep', 'new.dep']`，沒有 `.tmp` |
| 34 | 未執行（選用、需人工：小型 VHD 磁碟已滿） |

## 結論

- 所有自動化項目的結果都與 plan Task 8 的預期表一致，沒有產品缺陷。兩次重跑（18、21）都是 GUI 自動化的時序／前景視窗問題，第一次執行的 app 狀態與磁碟內容都沒有異常。
- 與 N 相比的行為變化都在 spec 的預期內：被其他程序以任何共用模式開著的 `.dep` 會擋住存檔（19 rw，Q1）；唯讀 package 不能改名，也不會留下 `.tmp`（31，Q2）；改名失敗只留下舊 package（30，P1-3 已知缺陷 3 已修正）；隱藏的 package 可以存檔並失去隱藏屬性（32，D11）。
- F-W10（開著的文件唯讀或被鎖時，關閉被擋）仍在，不在 F-3 範圍內（20、20b）。

## 仍需人工

- 34：磁碟已滿（小型 VHD）。
- 19：真實 7-Zip 使用的共用模式（決定落在 19 r 或 19 rw；F-3 之後兩者結果相同）。
