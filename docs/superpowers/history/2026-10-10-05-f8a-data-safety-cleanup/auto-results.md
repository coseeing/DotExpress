# F-8a Windows 驗證：自動化執行結果（plan Task 6；項目 66–69、76–82）

- 日期：2026-10-10，由 Claude 執行
- 受測：`fix/f8-data-safety-cleanup` 在 Task 4 之後（`725376f`，`HEAD:client` `62ea9d3eadebd3064e70e675138c6a32c7543f7d`，與 plan 的 tree id 相同）的 packaged build，以下稱 N-f8a。四個 client commit 的 tree id（`90a71c13…`、`adcfa533…`、`12837b65…`、`62ea9d3e…`）都與 plan 相同。
- 改前對照：`D:\dxtest\N-f7\DotExpress.exe`（F-7 的程式碼；48,752,069 bytes，sha256 `8FB585614AB755A3F2C61CE2439A71899E133A417FA9EAECCD310863EED1819F`），只讀取並由腳本複製到各自的資料夾。
- 方法：pywinauto 0.6.9（win32 backend；wx 的訊息框是 task dialog，用 UIA 讀取）＋ psutil，venv 在 `$SP\uia`。每個情境都在新的 `D:\dxtest\auto<N>-f8a`（N-f8a）或 `D:\dxtest\auto<N>-f7-f8a`（N-f7）資料夾執行，工作區、`config.json` 由腳本先建好（套件以 `zipfile` 寫入，`config.json` 以原始位元組寫入），exe 複製到該資料夾再啟動。沒有動到 `D:\dxtest\N`、`B`、`N-p25`、`N-f3`、`N-f4*`、`N-f5*`、`N-f6*`、`N-f7` 與既有的 `D:\dxtest\auto*` 資料夾。只結束 exe 位於這些資料夾的程序（`dx.kill_under`），`lockshare.py` 以 `taskkill /T` 結束；執行結束後沒有殘留的 DotExpress 或 `lockshare.py` 程序。沒有任何腳本讀寫剪貼簿。
- 腳本：`auto/item66.py`（66–69）、`auto/item76.py`（76–78）、`auto/item79.py`（79–81）、`auto/item82.py`（82），共用 `auto/f8agui.py` 與 `auto/lockshare.py`，並沿用 2026-10-09-03 的 `dx.py`、`docs.py`、`dicts.py`、`lock.py`，F-5 的 `f5gui.py` 與 F-7 的 `f7gui.py`（都未修改）。腳本由 plan Task 6 Step 2 的 `apply_blocks.py` 寫入。輸出在 `D:\dxtest\auto<N>-f8a.log` 與 `D:\dxtest\auto<N>-f7-f8a.log`（UTF-8，從 Git Bash 執行）。
- 每個項目都只執行一次，沒有重跑；22 個 log 與 plan Task 6 Step 4 的預期區塊逐行一致。

## 0. Packaged build

| 版本 | 結果 |
| --- | --- |
| N-f8a | 主 checkout `D:\workspace\DotExpress`（`725376f`），`client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`）；PyInstaller 6.21.0（Python 3.13.15），`scripts\build-dotexpress.bat` 約 47 秒，log 有 `Build complete!`。`client\build\DotExpress\PYZ-00.toc` 的 `config.py`、`dictionaries\manager.py`、`documents\workspace.py`、`documents\workspace_service.py`、`documents\formats.py`、`conversion\preprocessing\user_script.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress\client\`。`D:\dxtest\N-f8a\DotExpress.exe`，48,755,723 bytes，sha256 `5942454C46CFB1D514C9130F2E243D4CC6F23A98B8E61C0E98DA0E24124566F3`。`git status --short -- client scripts` 無輸出（build 產物都是 git-ignored） |

## 66–69、76–82. F-8a 項目

`<box X>` 指 `{'title': …, 'main': None, 'content': X, 'buttons': ['確定'], 'focus': '確定', 'presses': 1}`。`<d>` 是工作資料夾，`<random>` 是暫存檔名中的 16 個十六進位字，`<id>` 是程式啟動時寫入的 client id。每個 log 都以 `close: exited` 結束（79 改前除外）。

| # | N-f8a（改後） | N-f7（改前） |
| --- | --- | --- |
| 66 ✔ | `auto66-f8a`：工作區 `alpha.dep`（有效）、`bad.dep`（無效），啟動時選「保留」：`invalid ['bad.dep'] docs ['alpha']`。新增 `bad`：**`<box '文件「bad」已存在。'>`（標題 `錯誤`）**；名稱對話框重新出現，`{'buttons': ['確定', '取消'], 'name': 'bad'}`；Esc 取消。`docs: ['alpha']`，`files: ['alpha.dep', 'bad.dep']`，**`bad.dep unchanged: True`** | `auto66-f7-f8a`：沒有訊息（`box: None`、`shown again: None`）；`docs: ['alpha', 'bad']`，標題 `bad - DotExpress`，**`bad.dep unchanged: False`**（被空文件取代） |
| 67 ✔ | `auto67-f8a`：同 66，把 `alpha` 改名為 `bad`：同樣的 `錯誤` 訊息框與重新出現的名稱對話框（`name 'bad'`）；再把 `alpha` 改名為 `Alpha`（只差大小寫）：`case only: (None, None)`（沒有訊息），`docs: ['Alpha']`，`files: ['Alpha.dep', 'bad.dep']`，**`bad.dep unchanged: True`** | `auto67-f7-f8a`：沒有訊息；`case only: alpha is gone ['bad']`；`docs: ['bad']`，`files: ['bad.dep']`，**`bad.dep unchanged: False`**，`alpha.dep` 不見了 |
| 68 ✔ | `auto68-f8a`：同 66，匯入 `bad.txt` 與 `ok.txt`：匯入問題對話框 **`['bad.txt: Document "bad" already exists.']`**；`docs: ['alpha', 'ok']`，標題 `ok - DotExpress`，`files: ['alpha.dep', 'bad.dep', 'ok.dep']`，**`bad.dep unchanged: True`** | `auto68-f7-f8a`：`import issues: none`；`docs: ['alpha', 'bad', 'ok']`，**`bad.dep unchanged: False`** |
| 69 ✔ | `auto69-f8a`：工作區只有無效的 `new.dep`，選「保留」：**`docs ['new (2)']`，標題 `new (2) - DotExpress`**；`files: ['new (2).dep', 'new.dep']`，**`new.dep unchanged: True`** | `auto69-f7-f8a`：`docs ['new']`；`files: ['new.dep']`，**`new.dep unchanged: False`**（被空的 `new` 取代） |
| 76 ✔ | `auto76-f8a`：匯出 BRL：`<box '文件已成功匯出。'>`（標題 `匯出完成`）；`alpha.brl: b'\xe2\xa0\x81\xe2\xa0\x83\r\n\xe2\xa0\x89\xe2\xa0\x99'`（CRLF）；匯出 HTML：同樣的訊息框；`alpha.html: sha 6d8d672429f56e30 crlf 25 lf 25`；**`out: ['alpha.brl', 'alpha.html']`**（沒有 `.tmp`） | `auto76-f7-f8a`：兩個訊息框、`alpha.brl` 的位元組、`alpha.html` 的 sha256 前綴與 CRLF 數都相同 |
| 77 ✔ | `auto77-f8a`：`lockshare.py` 以 share 讀＋寫開著 `out\old.brl`（`b'OLD GOOD EXPORT'`），匯出 BRL 覆蓋它（確認覆蓋）：**`<box "匯出文件失敗：[WinError 5] 存取被拒。: '<d>\\out\\.old.brl.<random>.tmp' -> '<d>\\out\\old.brl'">`（標題 `錯誤`）**；**`old.brl: b'OLD GOOD EXPORT'`**，`out: ['old.brl']`（沒有 `.tmp`）。這是 spec Risks／O6 預期的行為 | `auto77-f7-f8a`：`<box '文件已成功匯出。'>`；`old.brl` 在持有者開著時被改寫成新的點字 |
| 78 ✔ | `auto78-f8a`：`beta.brl`（`b'OLD BETA EXPORT'`）以 share 讀＋寫開著，全部匯出為 BRL，覆蓋問題回答 `是(Y)`：摘要 **`{'title': 'Export Complete with Errors', …, 'content': "Exported documents: 1\nFailed documents: 1\n\nbeta: [WinError 5] 存取被拒。: '<d>\\out\\.beta.brl.<random>.tmp' -> '<d>\\out\\beta.brl'", 'buttons': ['確定'], 'focus': '確定', 'presses': 1}`**（標題與內文未翻譯是既有的 P1-4 defect 4）；`alpha.brl` 已寫入，**`beta.brl: b'OLD BETA EXPORT'`**，`out: ['alpha.brl', 'beta.brl']` | `auto78-f7-f8a`：摘要 `'All documents were exported successfully.'`（標題 `匯出完成`）；`beta.brl` 在持有者開著時被改寫 |
| 79 ✔ | `auto79-f8a`：`config.json` = `null`：**主視窗出現，`docs ['new']`**；啟動時寫入 client id 之前先保留備份：`config.json.bak b'null'`，`config.json` 是 `{"client": {"id": "<id>"}}`（無 BOM，CRLF）；`config.log` 一行 `[WARNING] Failed to read config file <d>\config.json; using defaults`；Ctrl＋滾輪放大字型後 `config.json` 含 `"font_size": 13`（及 client id），`.bak` 仍是 `b'null'` | `auto79-f7-f8a`：**沒有主視窗，程序以 exit code 1 結束**，沒有任何訊息；`files` 中沒有 `config.json.bak` |
| 80 ✔ | `auto80-f8a`：`config.json` 有 UTF-8 BOM，字型 20、寬度 30：啟動後 `config.json` 是 `{"client": {"id": "<id>"}, "conversion": {"width": 30}, "view": {"font_size": 20}}`（**無 BOM、CRLF，原有設定都保留**），`config.log` 為空，沒有 `.bak`；放大字型後 `"font_size": 21`，寬度 30 仍在 | `auto80-f7-f8a`：啟動時讀不到（`config.log` 有 `Failed to read config file`），寫入 client id 時把整個檔案換成 `{"client": {"id": "<id>"}}`，寬度與字型 20 都不見了；放大字型後是預設值加一（`font_size: 13`） |
| 81 ✔ | `auto81-f8a`：`lockshare.py` 以 share「只寫」開著 `config.json`（字型 20、寬度 30）：主視窗出現，使用預設值；`config.log`：`Failed to read config file …; using defaults` 與 **`[WARNING] Config file <d>\config.json was not saved because it could not be read`（只有一次，放大字型後也沒有第二行）**；釋放後 **`config.json unchanged: True`**，沒有 `.bak`；重新啟動並放大字型：`"font_size": 21`，寬度 30 仍在 | `auto81-f7-f8a`：釋放後 `config.json` 被換成 `{"view": {"braille_font": "simbraille", "font_size": 13, "scheme": "light"}}`（`unchanged: False`），原本的字型 20 與寬度 30 都不見了；重新啟動並放大字型後是 `font_size: 14` |
| 82 ✔ | `auto82-f8a`：字典管理新增 `d1`、匯入有效的 `d2.csv`（`import d2: []`）、把 `d1` 匯出覆蓋既有的檔案（確認覆蓋，沒有訊息框），`rows: [['d1', '0'], ['d2', '1'], ['default', '0']]`；文字處理以 `WM_SETTEXT` 填入腳本後套用、確定。`dictionary: {'d1.csv': '8f0594e9a11d46bb', 'd2.csv': 'f58a2e62a8033753', 'default.csv': '8f0594e9a11d46bb', 'preprocessing.py': '3413db2502421693'}`，`out: {'d1.csv': '8f0594e9a11d46bb'}`（**都沒有 `.tmp`**），`preprocessing.py: b'def main(text):\n    return text.upper()\n'`，`d2.csv equals the source: True`，`out d1.csv equals dictionary d1.csv: True` | `auto82-f7-f8a`：每一行都與改後相同（同樣的 sha256 前綴與位元組） |

## 結論

- 所有自動化項目（66–69、76–82）在兩個 build 上的結果都與 plan Task 6 Step 4 的預期區塊一致，沒有產品缺陷，沒有重跑。
- D1、D2：磁碟上有、但不在清單中的 `.dep` 不再被取代。新增與改名顯示既有的「已存在」訊息框並重新顯示名稱對話框（66、67），只差大小寫的改名不受影響（67）；匯入把它列為匯入問題（68）；預設文件改用 `new (2)`（69）。改前在這四個情境下 `bad.dep`／`new.dep` 都被默默取代，67 還讓 `alpha.dep` 消失。
- D6–D8：成功寫入的位元組與改前完全相同（BRL、HTML 的 CRLF 76；字典、匯出、文字處理腳本 82），資料夾中沒有留下 `.tmp`。匯出失敗時舊檔逐位元組保留（77、78）；被其他程式以共用讀寫開著的目的檔現在會匯出失敗並顯示 `[WinError 5]`，這是 spec Risks／O6 已知的取捨。
- D9–D11：`config.json` 為 `null` 時程式可以啟動，並先把原檔保留為 `config.json.bak`（79；改前直接結束，沒有訊息）；有 BOM 的檔案正常讀取，設定都保留（80；改前啟動時就被清掉）；讀不到的檔案不會被寫入，`config.log` 只記一次警告，釋放後原本的設定還在（81；改前被換成單一設定）。

## N-f8a2：審查修正後的重建（2026-10-10）

審查（`review_task.md`）之後的修正改了兩個 production 檔：M-1（`823fb55`，`documents/workspace_service.py`：`import_files` 在寫入每份匯入文件前再看一次磁碟）與 M-5（`46a4ce2`，`dictionaries/manager.py`：`export_dictionary` 對資料夾目的地先給 `[Errno 13] Permission denied: '<目的地>'`）。因此重建，並重跑碰到這兩段程式的項目：68（匯入）與 82（字典匯出）。

| 項目 | 結果 |
| --- | --- |
| build | 主 checkout（`46a4ce2`，`HEAD:client` `1d6780c8f7a5e53bc494e0c54bbeadcb0fdea500`），與 Task 6 Step 1 相同的指令：`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`，PyInstaller 6.21.0（Python 3.13.15），log 有 `Build complete!`；六個 F-8a 改動的模組都 `bundled from the checkout`，`gui.py analyzed from the checkout`。`D:\dxtest\N-f8a2\DotExpress.exe`，48,756,071 bytes，sha256 `9944656AA3DE4D7E9E089463FA2650878E9DAA5E082550635F240641AC1782FE`。`git status --short -- client scripts` 無輸出 |
| 68 ✔ | `auto68-f8a2`（`item66.py … 68`）：與 `auto68-f8a.log` 逐行相同（`diff --strip-trailing-cr` 無差異）：匯入問題 `['bad.txt: Document "bad" already exists.']`，`docs: ['alpha', 'ok']`，`bad.dep unchanged: True`，`close: exited` |
| 82 ✔ | `auto82-f8a2`（`item82.py`）：與 `auto82-f8a.log` 逐行相同：四個 sha256 前綴、`out d1.csv equals dictionary d1.csv: True`、`preprocessing.py` 的位元組都不變，`out` 只有 `d1.csv`（沒有 `.tmp`），`close: exited` |

每個情境都在新的 `D:\dxtest\auto<N>-f8a2` 資料夾執行，腳本是已 commit 的 `auto/item66.py`、`auto/item82.py`（未修改）；只結束該資料夾底下的程序，結束後 `tasklist` 沒有 DotExpress 程序；沒有任何腳本讀寫剪貼簿。其他項目（66、67、69、76–81）碰到的程式碼沒有改變，不重跑。新的檢查是在名稱比對之後才出現的檔案（M-1）與資料夾目的地（M-5），packaged build 中無法以這些腳本穩定重現，由單元測試涵蓋。N-f8a2 是之後要用的 build；項目 84 只走 BRL 匯出（`write_export_text`，兩個 build 相同），用 N-f8a 或 N-f8a2 都可以。

## 仍需人工（使用者）

- [ ] 84（可選）：在磁碟快滿時匯出，確認舊檔不會被破壞。請沿用項目 34 的小型 VHD（需要系統管理員權限），把它寫到只剩幾 KB 可用空間，並在其中放一個內容正常的 `old.brl`。把 `D:\dxtest\N-f8a\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual84-f8a\` 執行，新增文件、貼上一段長文字並轉換，再用「檔案 → 匯出 → 點字檔 BRL」覆蓋那個 `old.brl`。預期：出現「匯出文件失敗：…」訊息，訊息中是磁碟已滿的錯誤；`old.brl` 的內容和大小完全不變；資料夾中沒有留下 `.old.brl.….tmp`。如果舊檔變空或只剩一部分，請告訴我們。
