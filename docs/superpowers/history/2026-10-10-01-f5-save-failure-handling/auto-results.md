# F-5 Windows 驗證：自動化執行結果（plan Task 5；項目 36–40，重跑 18–20b、33）

- 日期：2026-10-10，由 Claude 執行
- 受測：`fix/f5-save-failure-handling` 在 Task 3 之後（`9ebf7ab`，`HEAD:client` `640d67bf…`）的 packaged build，以下稱 N-f5。這個 tree 與 plan 的 `8f8ee46e…` 只差 `client/tests/test_document_workspace.py` 的一行測試（見 plan 的 Implementation Notes），production 模組與三個 catalog 和 plan dry run 的 sha256 逐一相同
- 方法：用 pywinauto 0.6.9（win32 backend，F-5 的對話框用 UIA）＋ psutil 7.2.2 操作 packaged exe 的真實 GUI。每個項目都在新的 `D:\dxtest\auto<N>-f5` 資料夾執行（exe 會複製到該資料夾再啟動），沒有動到 `D:\dxtest\N`、`D:\dxtest\B`、`D:\dxtest\N-p25`、`D:\dxtest\N-f3`、`D:\dxtest\N-f4`、`D:\dxtest\N-f4m`（項目 20 的補充對照只讀取並複製 `N-f4m\DotExpress.exe`）。只結束 exe 位於這些 `auto*-f5` 測試資料夾的程序（`dx.kill_under`），`lock.py` 以 `taskkill /T` 結束；執行結束後沒有殘留的 DotExpress 或 `lock.py` 程序。
- 腳本：36、37 共用 `auto/item36.py`（`readonly`、`r`、`rw`），38、39 共用 `auto/item38.py`，40 是 `auto/item40.py`，共用 `auto/f5gui.py`（沿用 2026-10-09-03 的 `dx.py`、`docs.py`、`lock.py`，未修改）。18、19（含 20）、20b 沿用 2026-10-09-03 的腳本，33 沿用 F-3 的 `item33.py`，都經由 `auto/rerun.py` 執行（在記憶體中換掉 exe 與資料夾，並把 `dx.dismiss` 換成 `f5gui.dismiss`；已 commit 的腳本未修改）；19 從 18 結束後的資料夾複製開始（`--seed`）。輸出記錄在 `D:\dxtest\auto<N>-f5.log`（UTF-8，從 Git Bash 執行）。
- `.dep` 是 zip；「內容不變」比對 zip 內各成員（`docs.content_hash`、`docs.ws_state`）再加上 `st_mtime_ns`（`f5gui.package`），後者用來確認檔案沒有被重寫。
- 每個項目都只執行一次，沒有重跑。

## 0.1 Packaged build

| 版本 | 結果 |
| --- | --- |
| N-f5 | 主 checkout `D:\workspace\DotExpress`（`9ebf7ab`），`client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`）；PyInstaller 6.21.0，`scripts\build-dotexpress.bat` 約 53 秒，log 有 `Build complete!`。`client\build\DotExpress\PYZ-00.toc` 的 `documents\workspace.py`、`documents\workspace_service.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress\client\`。`D:\dxtest\N-f5\DotExpress.exe`，48,743,184 bytes，sha256 `0A0288538B2F33D81B4EEB27CF92D8E7E573931C12ECF825C803F9C050EDC312`。`git status` 無輸出（build 產物都是 git-ignored） |

## 0.2 對話框 smoke test

UIA venv（`$SP\uia`）的 `Scripts\python.exe` 不見了，依 plan 以 `py -3.13 -m venv --upgrade` 修復（pywinauto 0.6.9、psutil 7.2.2 仍在）。`smoke_f5gui.py` 以 client venv 執行一個與 `_ask_after_close_save_failure` 相同建法的對話框（使用已 commit 的 catalog），讀出：標題 `無法儲存文件`；`MainInstruction` `儲存文件失敗：[Errno 13] demo`；`ContentText` `上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。`；按鈕 `['重試(R)', '不儲存就關閉(W)', '取消']`；焦點在 `重試(R)`。Enter → `ID_YES`、Esc → `ID_CANCEL`、Alt+R → `ID_YES`、Alt+W → `ID_NO`，`SetYesNoCancelLabels` 都回傳 `True`，每個按鍵都只按一次（`presses: 1`）。

## 36–40. F-5 新項目（N-f5）

每個 log 都以 `add alpha: ('新增文件', [], [], [])`、`add beta: …`、`close: exited`、`docs: ['alpha', 'beta', 'new'] title: alpha - DotExpress input: 'alpha body' files: ['alpha.dep', 'beta.dep', 'new.dep']` 開始（重新啟動後 `alpha` 開著、未修改）。

| # | 結果 |
| --- | --- |
| 36 ✔ | `attrib +r alpha.dep`（`A    R`），`alpha` 未修改：Ctrl+Tab 沒有訊息，`beta - DotExpress`；新增 `gamma` 沒有訊息，清單 `['alpha', 'beta', 'gamma', 'new']`；開啟 `alpha` 沒有訊息；關閉 `([], 'exited')`。`alpha unchanged: True`（成員與 `st_mtime_ns` 都沒變），`attrib` 仍是 `A    R`；檔案 `['alpha.dep', 'beta.dep', 'gamma.dep', 'new.dep']`，`tmp: []`。改前（N-f4）：每個動作都是 `[Errno 13]`，關閉被擋（F-W10） |
| 37 r ✔ | `lock.py` 以只共用讀取開著 `alpha.dep`（`lock: locked r`，`attrib` 只有 `A`）：與 36 相同的各行，沒有任何訊息，關閉 `exited`，`alpha unchanged: True`，`tmp: []`。改前：`[WinError 5]`，關閉被擋 |
| 37 rw ✔ | 共用讀寫（`lock: locked rw`）：與 37 r 相同 |
| 38 ✔ | 輸入 `alpha edited`，`lock.py … r`。Ctrl+Tab：`[('錯誤', ["儲存文件失敗：[WinError 5] 存取被拒。: 'D:\\dxtest\\auto38-f5\\workspace\\.alpha.dep.c64623672d36cd4e.tmp' -> 'D:\\dxtest\\auto38-f5\\workspace\\alpha.dep'", 'OK'])]`，仍在 `alpha`，輸入框 `'alpha edited'`（決定 C：有修改時仍擋住）。關閉：出現 `無法儲存文件` 對話框，`main` 是同一行 `儲存文件失敗：[WinError 5] 存取被拒。: '…\\.alpha.dep.dc5e5079a6c95288.tmp' -> '…\\alpha.dep'`，`content` 是新句子，按鈕 `['重試(R)', '不儲存就關閉(W)', '取消']`，焦點 `重試(R)`；Esc → `running`，輸入框仍是 `'alpha edited'`，標題 `alpha - DotExpress`。再關閉，鎖住時按 Enter（重試）：對話框再次出現（新的 `.alpha.dep.cc583ad418a85429.tmp`，內容相同）；解鎖後按 Enter → `exited`。磁碟：`alpha members changed: True text: 'alpha edited'`，`tmp: []`；重新啟動後 `['alpha', 'beta', 'new']`，輸入框 `'alpha edited'`，關閉 `exited`。三次按鍵都是 `presses: 1`。改前：關閉只出現錯誤框（`OK`，F-W9），被擋 |
| 39 ✔ | 與 38 相同到對話框（Ctrl+Tab 同樣被擋，對話框的四個欄位與焦點相同）；Alt+W（不儲存就關閉）→ `exited`，`presses: 1`。磁碟：`alpha members changed: False text: 'alpha body'`（最後一次成功存檔），檔案 `['alpha.dep', 'beta.dep', 'new.dep']`，`tmp: []`；重新啟動後輸入框 `'alpha body'`，關閉 `exited`。改前：不可能（關閉被擋） |
| 40 ✔ | 剪貼簿放入 UTF-16 `41 D83D 42` 並貼上：輸入框 `'A\ud83dB'`。Ctrl+Tab 沒有訊息（`beta - DotExpress`）；`alpha.txt` 是 `41 ef bf bd 42`；Ctrl+Shift+Tab 回到 `alpha`，輸入框 `'A\ufffdB'`；再 Ctrl+Tab 沒有訊息，`alpha not rewritten: True`（成員與 `st_mtime_ns` 不變），`tmp: []`；關閉 `exited`；重新啟動後 `['alpha', 'beta', 'new']`，輸入框 `'A\ufffdB'`，關閉 `exited`。改前：每次切換都是 `儲存文件失敗：'utf-8' codec can't encode character '\ud83d' …`，關閉被擋 |

## 18–20b、33. 重跑（預期改變的項目；N-f5，經 `auto/rerun.py`）

| # | 結果 |
| --- | --- |
| 18 ✔ | 與 F-3 的 `auto18-f3.log` 逐行相同（把資料夾名稱換掉後 `diff` 無差異）：`Alpha` 改名為 `alpha` 後內文 `'Alpha body 中文內容 123'`，重新啟動後清單 `['alpha', 'new']`；新增 `ALPHA`：`文件「ALPHA」已存在。`；改 `new` 為 `Alpha`：`文件「Alpha」已存在。`；兩次 `disk diff: {}`；每次關閉都是 `exited` |
| 19 r ✔ | `alpha` 未修改，`lock.py … r` 時改名 `alpha`→`Alpha`：存檔被略過，**名稱對話框出現**，接著改名本身被拒：`儲存文件失敗：[WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用。: 'D:\\dxtest\\auto19-f5\\workspace\\alpha.dep' -> 'D:\\dxtest\\auto19-f5\\workspace\\.alpha.dep.sgrfcen3.tmp'`（F-3 D5）。清單 `['alpha', 'new']`，`diff: {}`，檔案 `['alpha.dep', 'new.dep']`；關閉 `exited`；重新啟動後不變。F-3：存檔失敗 `[WinError 5]`，沒有名稱對話框 |
| 19 rw ✔ | 共用讀寫：與 19 r 相同（`.alpha.dep.lek0toh3.tmp`） |
| 20 ✔ | `attrib +r alpha.dep`（開著、未修改）後改名：名稱對話框出現，改名被拒 `儲存文件失敗：[Errno 13] Permission denied: 'D:\\dxtest\\auto19-f5\\workspace\\alpha.dep'`（F-3 D7）；清單 `['alpha', 'new']`，`alpha.dep` 為 `R`。**關閉 `exited`**；`attrib -r` 後 `final:` 只有 `alpha.dep`、`new.dep`，沒有 `.tmp`。F-3：沒有名稱對話框；`close: … STILL RUNNING -> killed`（F-W10） |
| 20b ✔ | 開著、未修改的 `Alpha.dep` 設唯讀後改名 `Alpha`→`alpha`：名稱對話框出現，改名被拒 `儲存文件失敗：[Errno 13] Permission denied: 'D:\\dxtest\\auto20b-f5\\workspace\\Alpha.dep'`；清單 `['Alpha', 'new']`，`Alpha.dep` 為 `R`；**關閉 `exited`**。F-3：沒有名稱對話框，關閉被擋（`STILL RUNNING -> killed`） |
| 33 ✔ | Defender 即時保護開啟（`True`），每次先修改再切換，共 20 次：20 行 `ok [] []`，`failures: 0`；`alpha text: 'alpha edit 19'`、`beta text: 'beta edit 20'`，檔案 `['alpha.dep', 'beta.dep', 'new.dep']`。與 `auto33-f3.log` 逐行相同 |

## 20 補充：F-W10 的「關閉被擋」是真的，還是 `dx.dismiss` 造成的假象？

plan（Spec Corrections 7）在 dry run 中觀察到 `dx.dismiss` 的 win32 點擊關不掉 wx 的訊息框（task dialog），而開著的訊息框會讓程序在關閉後繼續存在。因此 F-3 項目 20／20b 的 `STILL RUNNING -> killed` 可能有一部分是「錯誤框沒被關掉」造成的。為了確認，以 F-5 之前的 build（`N-f4m`，sha256 `D8FEDB23…039B`，`b8baf2b`，與 F-5 的起點 `918c251` 內容相同的 F-4 build）在新的資料夾重跑 `item19.py`（含 20），種子是 `auto18-f5` 去掉 exe 的複本：

| 執行 | 關閉訊息框的方式 | 項目 20 的關閉 |
| --- | --- | --- |
| `D:\dxtest\auto20-f4m-uia-f5`（F-5 的 `rerun.py`） | `f5gui.dismiss`（UIA `invoke()`） | `close: [('錯誤', ["儲存文件失敗：[Errno 13] Permission denied: '…\\alpha.dep'", 'OK']), 'STILL RUNNING -> killed']` |
| `D:\dxtest\auto20-f4m-w32-f5`（F-3 的 `rerun.py`） | 原本的 `dx.dismiss`（win32 點擊） | 同上 |

兩次的 19 r／19 rw 也都與 F-3 相同（`[WinError 5]`，沒有名稱對話框，解鎖後關閉 `exited`）。`docs.close` 在 15 秒內每 0.8 秒呼叫一次 dismiss，並把每次看到的訊息框都記下來；兩次（以及 F-3 原本的 log）都只記到**一個**錯誤框，表示錯誤框在第一次 dismiss 就關掉了，之後主視窗沒有任何訊息框，卻在剩下的十多秒內一直沒有結束。另外以 `$SP\f5impl\tools\probe_old_dismiss.py`（`D:\dxtest\autoprobe-f5`，N-f5，修改後鎖住再 Ctrl+Tab 5 次）測試原本的 `dx.dismiss`：5 次都在第一次呼叫就關掉了錯誤框。

結論：

- **F-W10 的關閉被擋是真的**，不是假象：用 UIA 確實關掉錯誤框之後，F-5 之前的 build 仍然否決關閉、程序繼續執行（與程式碼一致：`_on_close` 在存檔失敗且 `CanVeto()` 時呼叫 `Veto()`）。F-3 的 `STILL RUNNING -> killed` 在修正後的 dismiss 下重現。
- 在這次的環境中，原本的 `dx.dismiss` 也能關掉 wx 的 `OK` 錯誤框（probe 的 5 次與 `auto20-f4m-w32-f5` 的各個錯誤框都是第一次呼叫就關掉）；plan 所說的「win32 點擊關不掉」沒有重現，比較可能是剛出現的對話框偶爾漏掉輸入的時序問題（F-3 項目 18 第一次執行也遇過一次）。這不影響上面的結論，`f5gui.dismiss` 與 `f5gui.answer` 的重按機制仍保留。
- F-5 之後，同一個項目 20 與 20b 都是 `close: exited`：未修改的文件不再寫入，關閉不再被擋；有修改時改由新的對話框決定（38、39）。

## 結論

- 所有自動化項目（36、37 r、37 rw、38、39、40、18、19 r、19 rw、20、20b、33）的結果都與 plan Task 5 的預期表一致，沒有產品缺陷，沒有重跑。對話框的每個按鍵都只按一次就生效。
- F-W10 已修正：未修改的開啟文件即使是唯讀或被其他程序開著，切換、新增、開啟與關閉都不再被擋，也不寫入（36、37、20、20b）；改名、刪除仍依 F-3 的規則處理該 package（19、20、20b 的名稱對話框之後的拒絕訊息）。
- 有修改而存檔失敗時，其他動作仍擋住（38 的 Ctrl+Tab，決定 C）；關閉時出現本地化的「無法儲存文件」對話框：重試（預設，焦點）、不儲存就關閉、取消，三者行為都符合 spec（38、39）。
- F-3 review M-4 已修正：貼上的孤立 surrogate 以 U+FFFD 存檔，不再出現訊息，之後未修改的切換不再重寫（40）。

## 審查後補充：關閉盒（X）＝取消（review M-8；N-f5b）

審查 M-8 指出 spec D7 的「Esc and the close box cancel」只量了 Esc。因為 review M-1 改了 production code（`shared/name_validation.py`），先依 plan Task 5 Step 1 重建，以下稱 N-f5b；再在新的 `D:\dxtest\auto*-f5m` 資料夾執行，只結束 exe 位於這些資料夾的程序（`dx.kill_under`）。

- **N-f5b**：主 checkout `6cfdaf4`（`a06a647` M-1 + `6cfdaf4` M-4 測試），PyInstaller 6.21.0，log 有 `Build complete!`；`documents\workspace.py`、`documents\workspace_service.py`、`shared\name_validation.py` 都來自 `DotExpress\client\`，`gui.py` 也是。`D:\dxtest\N-f5b\DotExpress.exe`，48,742,658 bytes，sha256 `ABEEFAF58973FDA2B8C28E50A94E9DF3C3C01FAAC464FE3F78669238C6EC62C4`。`git status` 只有本次修改的 `auto/f5gui.py`、`auto/item38.py` 與未追蹤的 `review_task.md`。
- **腳本**：`auto/f5gui.py` 新增 `CLOSE_BOX`（`answer` 以滑鼠 `click_input()` 點對話框標題列的關閉鈕「關閉」）與 `alt-f4` 鍵；`auto/item38.py` 新增 `x` 模式。
- **smoke test**（`smoke_f5gui.py`，scratchpad 的 client 副本，按鍵 `esc close-box alt-f4 enter`）：第一次執行時另一個程式（瀏覽器）在前景，`describe` 讀到的焦點是該程式的元素，`close-box` 的 `click_input` 在 pywinauto 的 `SetCursorPos` 拋出例外（工具錯誤，不是產品結果）；留下的兩個 demo 程序（`close_dialog_demo.py`）以 PID 結束。第二次執行：`esc -> ID_CANCEL`、`close-box -> ID_CANCEL`、`alt-f4 -> ID_CANCEL`、`enter -> ID_YES`，都是 `presses: 1`，`SetYesNoCancelLabels` 都回傳 `True`；標題、`main`、`content`、三個按鈕與 0.2 相同，`focus` 這次同樣讀到前景瀏覽器的元素（`describe` 在 `set_focus` 後 0.5 秒讀全域焦點，`answer` 之後才把對話框拉到前景；下面 38x 在 DotExpress 主視窗前景時讀到 `重試(R)`）。
- **38x ✔**（`item38.py … x`，`D:\dxtest\auto38x-f5m`）：Ctrl+Tab 與 38 相同（`[WinError 5]` 錯誤框，仍在 `alpha`，輸入框 `'alpha edited'`）。關閉 → 對話框（標題、`main`、`content`、按鈕與 38 相同，`focus: 重試(R)`）→ 以滑鼠點標題列的 X：`close, close-box: running`，`input after close-box: 'alpha edited' title: alpha - DotExpress`。再關閉 → Alt+F4：`close, alt-f4: running`，輸入框仍是 `'alpha edited'`。解鎖後關閉 → Enter：`exited`。磁碟：`alpha members changed: True text: 'alpha edited'`，檔案 `['alpha.dep', 'beta.dep', 'new.dep']`，`tmp: []`；重新啟動後 `['alpha', 'beta', 'new']`，輸入框 `'alpha edited'`，關閉 `exited`。每次都是 `presses: 1`。結論：關閉盒（X）與 Alt+F4 都等於「取消」（DotExpress 保持開啟、修改仍在），與 Esc 相同。
- **40 ✔、36 ✔（N-f5b smoke）**：`auto40-f5m.log`、`auto36-f5m.log`（`readonly`）把資料夾名稱換掉後與 `auto40-f5.log`、`auto36-f5.log` 逐行相同。
- 執行結束後沒有殘留的 DotExpress、`lock.py` 或 demo 程序。

## 仍需人工（使用者）

- 41（NVDA）：請在 NVDA 執行中檢查關閉時的「無法儲存文件」對話框。把 `D:\dxtest\N-f5b\DotExpress.exe`（審查修正後的 build；`N-f5` 亦可）複製到新資料夾 `D:\dxtest\manual41-f5\` 再執行；新增文件 `alpha` 並輸入一些文字，關閉後重新開啟，再修改 `alpha` 的內文；在命令提示字元執行 `attrib +r D:\dxtest\manual41-f5\workspace\alpha.dep`；然後關閉 DotExpress。請記錄 NVDA 依序讀出的內容（標題、錯誤那一行、說明句子、目前焦點的按鈕），並確認：Tab 與 Shift+Tab 在「重試」「不儲存就關閉」「取消」三個按鈕間移動，且每個按鈕都被讀出；Esc 取消（DotExpress 保持開啟，修改仍在）；再關閉一次，按對話框標題列的關閉鈕（X），確認它也是取消（DotExpress 保持開啟，修改仍在）；再關閉一次，Alt+R 重試（對話框再次出現）；最後執行 `attrib -r D:\dxtest\manual41-f5\workspace\alpha.dep` 再按 Alt+R（存檔後結束），或改按 Alt+W（不儲存就關閉）。
