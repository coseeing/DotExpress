# F-6 Windows 驗證：自動化執行結果（plan Task 6；項目 42–51）

- 日期：2026-10-10，由 Claude 執行
- 受測：`fix/f6-unreadable-dictionaries` 在 Task 4 之後（`6068661`，`HEAD:client` `e995d544…`，與 plan 的 tree id 相同）的 packaged build，以下稱 N-f6。`read_problems.py`、`dialog.py`、`gui.py`、`manager.py`、`presenter.py` 與三個 catalog 的 sha256 都與 plan dry run 逐一相同。
- 方法：用 pywinauto 0.6.9（win32 backend；wx 的訊息框是 task dialog，用 UIA）＋ psutil 7.2.2 操作 packaged exe 的真實 GUI。UIA venv 依 HANDOFF §8 在 `$SP\uia` 重建。每個腳本都在新的 `D:\dxtest\auto<N>-f6` 資料夾執行（exe 複製到該資料夾再啟動），先啟動一次再關閉，接著由腳本寫入測試檔，再啟動。沒有動到 `D:\dxtest\N`、`B`、`N-p25`、`N-f3`、`N-f4*`、`N-f5*`（改前對照只讀取並複製 `N-f5b\DotExpress.exe`）與既有的 `D:\dxtest\auto*` 資料夾。只結束 exe 位於這些 `*-f6` 資料夾的程序（`dx.kill_under`），`lockx.py` 以 `taskkill /T` 結束；執行結束後沒有殘留的 DotExpress 或 `lockx.py` 程序。
- 腳本：`auto/item42.py`（42–45）、`auto/item46.py`、`auto/item47.py`、`auto/item48.py`（48、49）、`auto/item50.py`（50、51），共用 `auto/f6gui.py`、`auto/lockx.py`（`CreateFileW(GENERIC_READ, share 0)`），並沿用 2026-10-09-03 的 `dx.py`、`docs.py`、`dicts.py` 與 F-5 的 `f5gui.py`（都未修改）。輸出在 `D:\dxtest\auto<N>-f6.log`（UTF-8，從 Git Bash 執行）。
- 測試檔由腳本產生：`big5.csv`（`text,braille,type` ＋ `臺北,ㄊㄞˊㄅㄟˇ,Bopomofo`，cp950，sha256 前綴 `f951f65cad59b201`）、`big5_late.csv`（1,000 列 ASCII 之後才是 cp950 那一列）、`badquote.csv`（UTF-8，第 2 列有未閉合的 `"`，後面超過 128 KiB，`90f44d31d25e93a0`）、`alpha.csv`／`acl.csv`（可讀的 UTF-8，`fba22ddc73966c0d`）；`default.csv` 是 `8f0594e9a11d46bb`。每個項目前後都記錄 sha256。
- 每個項目都只執行一次，沒有重跑；輸出與 plan Task 6 Step 3 的預期表逐行一致。

## 0. Packaged build

| 版本 | 結果 |
| --- | --- |
| N-f6 | 主 checkout `D:\workspace\DotExpress`（`6068661`），`client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`）；PyInstaller 6.21.0（Python 3.13.15），`scripts\build-dotexpress.bat` 約 45 秒，log 有 `Build complete!`。`client\build\DotExpress\PYZ-00.toc` 的 `dialog.py`、`dictionaries\read_problems.py`、`dictionaries\presenter.py`、`dictionaries\manager.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress\client\`。`D:\dxtest\N-f6\DotExpress.exe`，48,749,053 bytes，sha256 `A3CA72DEE6DE2E89FC1625C7FB441A7A06DBAE5138C6E61B2360F83860647994`。`git status` 無輸出（build 產物都是 git-ignored） |

## 42–51. F-6 新項目（N-f6）

每個 log 都以 `first start, close: exited` 和 `dictionary:` 那一行開始，以 `close: exited` 結束。`<NOT_UTF8>` 指 `檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。`（61 字），`<CANNOT_OPEN>` 指 `無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。`（42 字；N-f6 顯示的是審查前的「或您沒有」，審查 M-7 之後的 N-f6b 為「或你沒有」，見「審查後補充」），`<decode error>` 指 `'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte`。

| # | 結果 |
| --- | --- |
| 42 ✔ | `auto42-f6`：`big5.csv` 放進 `dictionary\` 後開啟字典管理，**對話框開啟**：`[['big5', '無法讀取'], ['default', '0', 'selected']]`；沒有原因列（`{'edit': None, 'uia edits': 0, 'labels': []}`）；`log\gui.log` 一行 `[ERROR] Cannot read dictionary "big5.csv": UnicodeDecodeError: <decode error>`，沒有 `Traceback`；`big5.csv unchanged: True` |
| 43 ✔ | 選 `big5`：`[['big5', '無法讀取', 'selected'], ['default', '0']]`；原因列 `{'labels': ['無法讀取的原因：'], 'uia name': '無法讀取的原因：', 'uia value': '<NOT_UTF8>', 'sel': (0, 61), 'length': 61, 'lines': 2}`（全文選取，兩行）。選 `default`：原因列消失（`'edit': None, 'uia edits': 0, 'labels': []`） |
| 45 ✔ | `big5` 選取、焦點在清單：Tab → `('Edit', '無法讀取的原因：')`；Shift+Tab → `('ListItem', 'big5')`。`default` 選取：Tab → `('Button', '新增')`（與現在相同） |
| 44 ✔ | 選 `big5` 按「編輯」：`[('錯誤', ['無法讀取字典「big5」。', '<NOT_UTF8>', 'OK'])]`（task dialog：主要指示是標題句，內容是原因）；按 OK 後 `['字典管理']` 仍開著，`big5` 仍選取，沒有 `自訂字典管理器`；`gui.log` 多一行（共兩行相同的 `UnicodeDecodeError`）。腳本把 `big5.csv` 改寫成 UTF-8 後再按「編輯」：`['自訂字典管理器']`，列 `[['臺北', 'ㄊㄞˊㄅㄟˇ', '注音']]`；取消後 `windows: [] boxes: []`；重新開啟字典管理：`[['big5', '1'], ['default', '0', 'selected']]`，沒有原因列；`gui.log lines: 2` |
| 46 ✔ | `auto46-f6`：`icacls dictionary\acl.csv /deny %USERNAME%:(W)`（F-W12 原本的重現方式；`W` 含 SYNCHRONIZE，所以連讀取用的開啟也被拒）。`[['acl', '無法讀取'], ['default', '0', 'selected']]`；原因列標籤與 UIA 名稱同 43，`'uia value': '<CANNOT_OPEN>', 'sel': (0, 42), 'length': 42, 'lines': 2`；編輯：`[('錯誤', ['無法讀取字典「acl」。', '<CANNOT_OPEN>', 'OK'])]`，`['字典管理']` 仍開著；匯出到 `out.csv`：`[('錯誤', ["匯出字典失敗：[Errno 13] Permission denied: 'D:\\dxtest\\auto46-f6\\dictionary\\acl.csv'", 'OK'])]`（現有訊息，不變），`out.csv exists: False`，對話框仍可用；`acl restored: True`，`acl.csv unchanged: True`；`gui.log` 兩行 `[ERROR] Cannot read dictionary "acl.csv": PermissionError: [Errno 13] Permission denied: '…\\acl.csv'` |
| 47 ✔ | `auto47-f6`：`lockx.py` 以 share 0 開著 `alpha.csv`（`lock: locked`）。`[['alpha', '無法讀取'], ['default', '0', 'selected']]`；原因 `<CANNOT_OPEN>`，`(0, 42)`；解鎖（`47 unlocked`）後按「編輯」：`boxes: [] windows: ['自訂字典管理器']`，列 `[['Alpha', '⠁', '一般']]`（重新讀取成功）；`alpha.csv unchanged: True`；`gui.log` 一行 `PermissionError`（`alpha.csv`） |
| 48 ✔ | `auto48-f6`：`badquote.csv` 在 `dictionary\`，`[['badquote', '無法讀取'], ['default', '0', 'selected']]`。從 `data\` 匯入 `big5.csv` 為 `b1`、`big5_late.csv` 為 `b2`：兩次都是名稱對話框之後 `[('錯誤', ['匯入字典失敗：<NOT_UTF8>', 'OK'])]`；清單不變，`['字典管理']` 仍開著；`dictionary files: ['badquote.csv', 'default.csv']`（沒有複製） |
| 49 ✔ | 選 `badquote`：原因列 `'uia value': '檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：field larger than field limit (131072)', 'sel': (0, 71), 'length': 71, 'lines': 2`；匯入同一檔為 `bq2`：`[('錯誤', ['匯入字典失敗：檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：field larger than field limit (131072)', 'OK'])]`；`[['badquote', '無法讀取', 'selected'], ['default', '0']]`，`dictionary files: ['badquote.csv', 'default.csv']`；`48-49 sources unchanged: True`；`gui.log` 一行 `[ERROR] Cannot read dictionary "badquote.csv": Error: field larger than field limit (131072)` |
| 50 ✔ | `auto50-f6`：改名 `big5`→`big5x`：沒有訊息（`[]`），`[['big5x', '無法讀取', 'selected'], ['default', '0']]`，原因列 `<NOT_UTF8>`，`(0, 61)`；匯出 `big5x`：沒有訊息，`out.csv equals the source: True`（位元組相同）；刪除 `big5x`：`[('確認刪除字典', ['要刪除字典「big5x」嗎？', '是(Y)', '否(N)'])]`，之後 `[['default', '0', 'selected']]`，`boxes: []`，`dictionary files: ['default.csv']` |
| 51 ✔ | 重新放入 `big5.csv`，在設定選 `big5` 為字典，輸入 `臺北` 後轉譯：`('', [('錯誤', ["轉譯失敗：<decode error>", 'OK'])])`（與改前相同，D10）。`50-51 gui.log`：`big5.csv` 一行、`big5x.csv` 一行，都是 `UnicodeDecodeError`，沒有 `Traceback` |

## 改前對照：42 在 N-f5b

| # | 結果 |
| --- | --- |
| 42（N-f5b）✔ 重現 F-W12 | `D:\dxtest\auto42-f5b-f6`，`D:\dxtest\N-f5b\DotExpress.exe`（main `0708f44`）：相同的 `big5.csv`；`42: Dictionary Management did not open; windows: [] boxes: []`，`42: gui.log: []`，`close: exited`。沒有視窗、沒有訊息、沒有 log |

## 審查後補充（N-f6b；審查 M-1、M-7）

審查（`review_task.md`）的 M-1（原因欄位重新取得焦點時再全選）與 M-7（`CANNOT_OPEN` 改用「你」）改了 `dialog.py` 與 catalog（M-6 改了 `read_problems.py`，只影響 log handler 何時建立），所以重建為 N-f6b，重跑 item 42–45（`item42.py` 新增四行 `45 sel`：在原因欄位按 → 之後 Shift+Tab 再 Tab）與 item 47。每個情境都在新的 `D:\dxtest\auto*-f6b` 資料夾執行；沒有動 `N-f6`（只複製它的 exe 做改前對照）與既有的 `auto*-f6` 資料夾。只結束 exe 位於這些資料夾的程序（`dx.kill_under`），`lockx.py` 以 `taskkill /T` 結束；結束後沒有殘留的 DotExpress 或 `lockx.py` 程序。每個項目只執行一次。

| 項目 | 結果 |
| --- | --- |
| Build | 主 checkout `aec3c64`，`client\.venv\Scripts` 放在 `PATH` 最前面；PyInstaller 6.21.0（Python 3.13.15），`scripts\build-dotexpress.bat` 約 57 秒，`Build complete!`；`PYZ-00.toc` 的 `dialog`、`dictionaries.read_problems`、`dictionaries.presenter`、`dictionaries.manager` 與 `Analysis-00.toc` 的 `gui` 都來自 `D:\workspace\DotExpress\client\`。`D:\dxtest\N-f6b\DotExpress.exe`，48,749,506 bytes，sha256 `E1ED0B7712801B01950C08439EAE367D79423D4D1BE7A17A9CFB6514C4283BDA`。`git status` 只有既有的 untracked 資料夾 |
| 42、43、44、45 ✔ | `auto42-f6b.log`：去掉新增的 `45 sel` 四行之後，與 `auto42-f6.log` 逐行相同（列、原因列 `(0, 61)`、Tab 順序、編輯錯誤框、修好後開啟編輯器、`gui.log` 兩行） |
| 45 sel ✔（M-1） | N-f6b：Tab → `('Edit', '無法讀取的原因：') (0, 61)`；→ → `(61, 61)`；Shift+Tab → `('ListItem', 'big5') (61, 61)`；**Tab → `('Edit', '無法讀取的原因：') (0, 61)`（重新全選）** |
| 45 sel 改前（N-f6） | `auto42n6-f6b.log`（同一腳本、`N-f6\DotExpress.exe`）：前三步相同，最後 Tab 回來仍是 `(61, 61)`（審查 M-1 描述的行為）；其餘各行與 `auto42-f6.log` 相同 |
| 47 ✔（M-7） | `auto47-f6b.log`：原因列 `'uia value': '無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。', 'sel': (0, 42), 'length': 42, 'lines': 2`；把「你」換回「您」、資料夾名換回 `auto47-f6` 之後，與 `auto47-f6.log` 逐行相同（解鎖後編輯器開啟、`alpha.csv unchanged: True`、`gui.log` 一行 `PermissionError`） |

## 結論

- 所有自動化項目（42、43、44、45、46、47、48、49、50、51）的結果都與 plan Task 6 Step 3 的預期表一致，沒有產品缺陷，沒有重跑；N-f5b 的 42 重現了 F-W12。
- F-W12 已修正：有讀不到的字典時，字典管理仍會開啟，該列顯示 `無法讀取`，其他字典照常顯示筆數；原因寫進 `gui.log`，每次一行，沒有 traceback（42、46、47、49、50）。
- 選取讀不到的字典時，清單下方出現有標籤的唯讀多行欄位，文字全選，是清單之後的下一個 Tab 停點；選取可讀的字典時隱藏，Tab 順序與現在相同（43、45）。
- 「編輯」會重新讀取：仍讀不到時顯示 `無法讀取字典「…」。` 與原因，字典管理保持開啟；檔案修好或解鎖後直接開啟編輯器（44、46、47）。
- 匯入會先讀完整個檔案，非 UTF-8（含前 8 KiB 都是 ASCII 的 Big5）與無效 CSV 都被拒，並說明原因，不會複製（48、49）。
- 改名、匯出、刪除與轉譯維持原本行為，之後清單正確（46、50、51）。所有測試檔的位元組都沒有被改寫。

## 仍需人工（使用者）

- 52（NVDA）：請在 NVDA 執行中檢查字典管理的「無法讀取的原因」欄位。把 `D:\dxtest\N-f6b\DotExpress.exe`（審查修正後的 build）複製到新資料夾 `D:\dxtest\manual52-f6b\` 執行一次後關閉；把 `D:\dxtest\auto48-f6\data\big5.csv`（以 Big5 儲存的字典，和繁體中文 Excel「CSV（逗號分隔）」存出的格式相同）複製到 `D:\dxtest\manual52-f6b\dictionary\`，再執行 DotExpress，開啟「字典管理」。請記錄 NVDA 依序讀出的內容，並確認：用方向鍵移到 `big5` 時讀出「無法讀取」；按 Tab 時讀出標籤「無法讀取的原因」、欄位的角色（編輯區、多行、唯讀）以及**完整的**原因文字（兩行都讀到，不是只讀第一行）；在欄位內按一下方向鍵 → 之後，按 Shift+Tab 回到清單，再按 Tab 回到欄位時，NVDA 仍讀出完整的原因（不是只讀游標所在的那一行）；按「編輯」時錯誤對話框被當作對話框讀出（標題、「無法讀取字典「big5」。」與原因）。如果 NVDA 只讀出第一行，請告訴我們（D3 的全選做法可能需要調整）。
