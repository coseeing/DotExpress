# F-4 Windows 驗證：自動化執行結果（plan Task 5；項目 23–29、35）

- 日期：2026-10-09，由 Claude 執行
- 受測：`fix/f4-keep-invalid-bopomofo-rows` 在 Task 3 之後（`7341e5d`，`HEAD:client` `a64e34d8…`）的 packaged build，以下稱 N-f4；項目 23 與 35 另以 B（`6e5819f` 的 packaged build，`D:\dxtest\B`）對照
- 方法：用 pywinauto 0.6.9（win32 backend）＋ psutil 7.2.2 操作 packaged exe 的真實 GUI，訊息框文字用 UIA 讀取。每個項目都在新的 `D:\dxtest\auto<N>-f4*` 資料夾執行（exe 會複製到該資料夾再啟動），沒有動到 `D:\dxtest\N`、`D:\dxtest\B`、`D:\dxtest\N-p25`、`D:\dxtest\N-f3`。只結束 exe 位於這些 `auto*-f4*` 測試資料夾的程序（`dx.kill_under`）；執行結束後沒有殘留的 DotExpress 程序。
- 腳本：23、24、25、29 沿用 `2026-10-09-03-windows-verification/auto/` 的腳本（未修改），以 `auto/rerun.py` 在記憶體中把 exe 與資料夾換成 N-f4（23 是 B 與 N-f4，資料夾 `D:\dxtest\auto23-f4-B`、`D:\dxtest\auto23-f4-N-f4`；24、25、29 用 `D:\dxtest\auto24-f4`；25 只執行到 `# 29 ACL deny write` 之前，29 由 `item29.py` 執行，F-W13）。35 是新腳本 `auto/item35.py`，沿用 2026-10-09-03 的 `dx.py`、`docs.py`、`dicts.py`。測試字典是 2026-10-09-03 的 `auto/data/`，`D:\dxtest\data\` 的六個檔案與它逐位元組相同（`dict_badbopo.csv` sha256 `c4324573…6eb4`）。輸出記錄在 `D:\dxtest\auto<N>-f4*.log`（UTF-8，從 Git Bash 執行）。
- 每個項目都只執行一次，沒有重跑。

## 0.1 Packaged build

| 版本 | 結果 |
| --- | --- |
| N-f4 | worktree `D:\workspace\DotExpress-f4`，主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`）；PyInstaller 6.21.0，`scripts\build-dotexpress.bat` 約 46 秒，log 有 `Build complete!`。`client\build\DotExpress\PYZ-00.toc` 的 `dictionaries\entries.py`、`dictionaries\entry_list_model.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress-f4\client\`，兩個 toc 都沒有主 checkout（`workspace\DotExpress\client`）的模組。`D:\dxtest\N-f4\DotExpress.exe`，48,736,571 bytes，sha256 `41EF168A8AB8F08D1AD80282818E3F052ADC05803D363DFD0EC96D83E8EC6F69`。`git status` 只列出本資料夾（build 產物都是 git-ignored） |

## 23–29. 字典檔安全（N-f4；23 為 B vs N-f4）

| # | 結果 |
| --- | --- |
| 23 ✔ | `dict23`：B 與 N-f4 編輯器各 6 列相同，按確定沒有訊息；兩邊都是 `changed: True lines 7 -> 7 bom: False crlf: True sha ef319c2140b1465e`（與 2026-10-09-03 的 `ef319c21…` 相同）。`dict_badbopo`：兩邊編輯器都只顯示 `[['臺北', '⠞⠺', 'Unicode 點字']]`，按確定沒有訊息；**N-f4 `changed: False lines 4 -> 4 bom: False crlf: True sha c432457361b0997a`**（檔案逐位元組不變，F-W11 已修正）；B `changed: True lines 4 -> 2 … sha d978403dcb4cb16d`（F-W11 基線）。`mgr items` 兩邊都是 `[['default', '0'], ['dict23', '6'], ['dict_badbopo', '1']]`；字典資料夾只有 `default.csv`、`dict23.csv`、`dict_badbopo.csv`；兩邊關閉都是 `exited` |
| 24 ✔ | 與 N 相同：`bom_excel`、`bom_notepad` 匯入後筆數 `2`、`bom_lf` `1`，匯入的檔案保留 BOM；編輯器各列正確；按確定沒有訊息，之後 `BOM False`，位元組是 CRLF（例如 `bom_lf`：`b'text,braille,type\r\n戊己,⠑⠋,Braille\r\n'` 的 UTF-8）。在設定選字典後轉換：`'甲乙' -> '⠁⠃…'`、`'丙丁' -> '⠉⠙…'`、`'戊己' -> '⠑⠋…'`，`uses dict: True`；`default` 的 `'甲乙丙丁'` 也正常轉換。關閉 `exited` |
| 25 ✔ | 以只共用讀取鎖住 `bom_lf.csv` 後按確定：`儲存失敗：[WinError 5] 存取被拒。: 'D:\\dxtest\\auto24-f4\\dictionary\\.bom_lf.csv.e5aaa5123679ba8a.tmp' -> 'D:\\dxtest\\auto24-f4\\dictionary\\bom_lf.csv'`；編輯器維持開啟，列保留，`state: ('ORIG', [...])`，沒有 `.tmp`。解鎖後再按確定：沒有訊息，`SAVED(CRLF,noBOM)`。與 N 相同 |
| 26 ✔ | `attrib +r` 後按確定：`儲存失敗：[Errno 13] Permission denied: 'D:\\dxtest\\auto24-f4\\dictionary\\bom_lf.csv'`，編輯器維持開啟，`ORIG`，沒有 `.tmp`。`attrib -r` 後再按確定成功（`SAVED(CRLF,noBOM)`），`attrib` 只有 `A`。與 N 相同 |
| 27 ✔ | `attrib +h` 後按確定：沒有訊息，`SAVED(CRLF,noBOM)`，`attrib` 只有 `A`（隱藏屬性消失，M-8，與 N 相同），沒有 `.tmp` |
| 28 ✔ | Defender 即時保護開啟（`RealTimeProtectionEnabled=True`），連續按確定 10 次：`28 failures: 0`，`SAVED(CRLF,noBOM)`，沒有 `.tmp` |
| 29 ✔ | `icacls /deny "%USERNAME%:(WD,AD,WEA,WA)"`（F-W13）後按確定：沒有訊息，`SAVED(CRLF,noBOM)`；`icacls` 已沒有 deny ACE（檔案被整個取代，與 N 相同）。`/remove:d` 還原成功；關閉 `exited`；`final: ('SAVED(CRLF,noBOM)', ['bom_excel.csv', 'bom_lf.csv', 'bom_notepad.csv', 'default.csv']) A` |

## 35. `dict_badbopo.csv` 經過字典管理與編輯器（新項目，`auto/item35.py`）

N-f4 在 `D:\dxtest\auto35-f4`，B 在 `D:\dxtest\auto35-f4-B`（對照用）。轉換輸入 `肚子數學`，選用字典 `dict_badbopo`。

| 步驟 | N-f4 | B（改前） |
| --- | --- | --- |
| 來源 | sha256 `c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4`，4 行 | 同左 |
| 匯入 | 沒有訊息；匯入檔與來源逐位元組相同；字典管理 `[['dict_badbopo', '1']]` | 同左 |
| 轉換 1（O1） | `'⠙⠌⠐⠳⠓⠁⠊⠌⠐⠄⠑⠦⠂'`（後面接空白點字格），`轉換完成。` | 同左 |
| 35a 編輯器、確定 ✔ | 列 `[['臺北', '⠞⠺', 'Unicode 點字']]`；確定 `([], False)`；**檔案相同 `True`，4 行，sha256 `c4324573…6eb4`**，資料夾 `['default.csv', 'dict_badbopo.csv']`（沒有 `.tmp`） | 列相同；檔案 `False`，**2 行**，sha256 `d978403d…` |
| 35a 轉換 2 ✔ | 與 O1 相同（`same as convert 1: True`） | `'⠙⠌⠐⠓⠱⠁⠊⠌⠐⠑⠦⠂'`，`False`（兩列注音規則被刪掉） |
| 35b 新增 `肚子`／`ㄉㄨˋㄗ˙`／注音 ✔ | 透過真實的新增項目對話框：`[('錯誤', ['來源文字「肚子」已存在。', 'OK'])]`；列仍是 `[['臺北', '⠞⠺', 'Unicode 點字']]`；確定 `([], False)`；檔案相同 `True` | 沒有訊息，新增成功，列變成兩列（`臺北`、`肚子`）；檔案 `False` |
| 35c 刪除 `臺北`、確定 ✔ | 刪除後列 `[]`；確定 `([], False)`；檔案是 `'text,braille,type\r\n肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n'`（`True`）；字典管理 `[['dict_badbopo', '0']]` | 刪除後列剩 `肚子`（35b 新增的那筆）；檔案 `'text,braille,type\r\n肚子,ㄉㄨˋㄗ˙,Bopomofo\r\n'`；字典管理 `1` |
| 35d 重新啟動 ✔ | 字典管理 `[['dict_badbopo', '0']]`；編輯器列 `[]`；取消後檔案仍等於 35c 的內容（`True`），沒有 `.tmp` | 字典管理 `1`；列 `[['肚子', 'ㄉㄨˋㄗ˙', '注音']]` |
| 關閉 | 兩次都是 `exited` | 同左 |

## 結論

- 所有項目的結果都與 plan Task 5 的預期表一致，沒有產品缺陷，也沒有腳本問題，沒有重跑。
- F-W11 已修正：編輯器看不到的列（不合法的注音列）在未修改按確定後逐位元組保留（23、35a），刪除所有可見列後仍保留在原位（35c），重新啟動後也不變（35d）；轉換輸出不再因為按確定而改變（35a）。B 仍是 4 行→2 行、轉換結果改變。
- 與 spec 一致的行為變化（Q1，orchestrator 依建議預設決定）：新增與隱藏列相同來源文字的項目會被拒絕，顯示既有的 `來源文字「肚子」已存在。`（35b）；B 會接受。
- 已知缺陷（Q2，不在 F-4 範圍）：隱藏的列在編輯器中看不到，字典管理的筆數也不含它們（35c、35d 顯示 `0`，但檔案仍有兩列注音）。
- F-2 的寫入路徑（24–29）與 N 相同，沒有退化。

## 仍需人工

- 無（35 的新增重複項目已透過真實的新增項目對話框自動化）。
