# Windows 驗證：自動化執行結果（test.md §0.1、7、18–21、23–29）

- 日期：2026-10-09，由 Claude 執行
- 受測：N＝`main` `b823cae` 的 packaged build；B＝`6e5819f` 的 packaged build（見 §0.1）
- 方法：用 pywinauto 0.6.9（win32 backend）操作 packaged exe 的真實 GUI。訊息框文字用 UIA 讀取。每個情境都在 `D:\dxtest\auto*` 的獨立資料夾執行，沒有動到 `D:\dxtest\N`、`D:\dxtest\B`。
- 腳本在 `auto/`，測試字典在 `auto/data/`（`.gitattributes` 設為 `-text`，BOM 與換行原樣保存）。腳本寫死 `D:\dxtest\...` 路徑，執行前需要把 `pywinauto`、`psutil` 裝進另一個 venv。
- `.dep` 是 zip，每次存檔時間戳記都會變。所以判斷「內容不變」時，比對的是 zip 內各成員的名稱與內容，不是整個檔案的位元組。

## 0.1 Packaged build

| 版本 | 結果 |
| --- | --- |
| N | PyInstaller 6.21.0，exit 0；`D:\dxtest\N\DotExpress.exe`，48,731,302 bytes，sha256 `733168e8…54d0e5` |
| B | worktree `..\DotExpress-6e5819f`，exit 0；`D:\dxtest\B\DotExpress.exe`，48,705,657 bytes，sha256 `790180f4…12d43b` |

兩版都在暫存資料夾啟動過：視窗標題 `new - DotExpress`，並在 exe 旁建立 `config.json`、`dictionary`、`workspace`、`log`、`dual_view`。

## 7. 混排長文件的 BRL bytes（`auto/item7.py`）✔

流程：匯入 `p25_doc.txt` → 轉換 → 匯出 BRL → 設定把點字類型改成 ASCII → 轉換 → 匯出 BRL。

| | unicode | ascii |
| --- | --- | --- |
| N | `365d28a9…f9d683c` | `95b9a1a6…2538bc64` |
| B | `365d28a9…f9d683c` | `95b9a1a6…2538bc64` |

N 與 B 都等於 source-run 基線，`cmp` 也確認 N 與 B 逐位元組相同。

## 18–21. 文件只改大小寫（N）

| # | 結果 |
| --- | --- |
| 18 ✔ | 新增 `Alpha`、輸入內文、重新啟動：內文在。改名為 `alpha`：`workspace\` 只有 `alpha.dep`，沒有 `.tmp`；重新啟動後清單與內文正確。新增 `ALPHA`：`文件「ALPHA」已存在。`；改 `new` 為 `Alpha`：`文件「Alpha」已存在。`；兩次磁碟內容都不變。另見 F-W9 |
| 19 △ | 本機沒有 7-Zip，改用另一個程序以 `CreateFileW(GENERIC_READ)` 開著 `alpha.dep`（`auto/lock.py`），兩種共用模式都測。**只共用讀取**（`FILE_SHARE_READ`）：改名前的存檔就失敗，訊息 `儲存文件失敗：[Errno 13] Permission denied: '…alpha.dep'`，名稱對話框不會出現。**共用讀寫**：存檔成功，改名失敗，訊息 `儲存文件失敗：[WinError 32] … 'alpha.dep' -> '.alpha.dep.<亂數>.tmp'`，與 spec 預期相同。兩種情況清單都仍是 `alpha`，重新啟動後內容不變，也沒有 `.tmp`。真實 7-Zip 會落在哪一種，仍需人工確認 |
| 20 △ | `attrib +r alpha.dep` 後改名：改名前的存檔就失敗（`[Errno 13] Permission denied`），所以 M-7（留下唯讀 `.tmp`）的路徑在 GUI 走不到。關閉 app 時存檔又失敗，關閉被擋（F-W10）。B 行為相同 |
| 21 ✔ | Defender 即時保護開啟（`RealTimeProtectionEnabled=True`），連續 10 次 `alpha`↔`Alpha`：10 次都成功，沒有錯誤，沒有 `.tmp`，內容不變 |

## 23–29. 字典檔安全（N；23 為 N vs B）

測試字典 `auto/data/dict23.csv` 包含 General（含 `@` 與逗號欄位）、Braille（Unicode 點字）、Bopomofo 三種類型的列。

| # | 結果 |
| --- | --- |
| 23 ✔ | B 與 N 各自匯入同一份字典，開編輯器按確定：兩邊輸出 `cmp` 相同，sha256 `ef319c21…`，CRLF、無 BOM |
| 24 ✔（模擬） | 用程式產生 BOM＋CRLF（模擬 Excel「CSV UTF-8」與記事本「UTF-8 with BOM」）與 BOM＋LF 三份字典。匯入筆數正確，編輯器各列正確；按確定後沒有 BOM（CRLF）；在設定選擇該字典後轉換，輸出使用了字典（例如 `甲乙`→`⠁⠃`）。用真的 Excel／記事本存檔仍可人工補做 |
| 25 △ | 以只共用讀取的方式鎖住檔案（模擬 Excel）後按確定：`儲存失敗：[WinError 5] 存取被拒。: '….tmp' -> '…bom_lf.csv'`（spec 預期是 WinError 32）。編輯器維持開啟、列保留、檔案不變、沒有 `.tmp`。解鎖後再按確定成功 |
| 26 ✔ | `attrib +r` 後按確定：`儲存失敗：[Errno 13] Permission denied: '…bom_lf.csv'`，沒有 `.tmp`，檔案不變。`attrib -r` 後再按確定成功，新檔沒有唯讀屬性 |
| 27 | `attrib +h` 後按確定：**成功**，檔案被取代，**隱藏屬性消失**（M-8），沒有 `.tmp` |
| 28 ✔ | Defender 開啟，連續按確定 10 次：0 次失敗，沒有 `.tmp` |
| 29 | test.md 的 `icacls /deny "%USERNAME%:(W)"` 不適用（F-W13），改用 `(WD,AD,WEA,WA)`：按確定**成功**，檔案被整個取代，deny ACE 跟著消失（判決變寬）。已用 `icacls /remove:d` 還原 |

## 新發現

| ID | 內容 | B（`6e5819f`） |
| --- | --- | --- |
| F-W9 | 文件名稱對話框因「已存在」錯誤重新顯示時，按鈕變成英文 `OK`／`Cancel`（第一次顯示是「確定」／「取消」）。原因：`localize_standard_buttons`（`client/dialog.py`）呼叫 `dialog.FindWindowById(...)`，這在 wxPython 是全域搜尋，可能找到別的視窗的同 ID 按鈕並改了它的標籤。另外，所有 `wx.MessageBox` 的按鈕都是英文 `OK` | 程式碼相同（只比對了程式碼，沒有在 B 上執行） |
| F-W10 | 開著的文件 `.dep` 被設為唯讀，或被只共用讀取的程序開著時，任何會先存檔的動作（改名、關閉）都會失敗；關閉被 veto，app 無法正常結束（只能等鎖解除或改屬性）。另外，沒有修改的文件也會在這些動作前重寫 | 相同 |
| F-W11 | **資料遺失**：不合法的注音列（例如 `ㄉㄨˋ|ㄗ˙`、`ㄕㄨˋ ㄒㄩㄝˊ`）在載入時被默默略過；字典管理的筆數不含它們。即使沒修改，在編輯器按確定也會把它們從檔案刪掉（4 行→2 行） | 相同 |
| F-W12 | 字典資料夾中任一檔案讀不到（例如 ACL 拒絕 SYNCHRONIZE）時，字典管理靜默打不開：沒有視窗、沒有錯誤訊息。推測是 `_load_dictionary_counts` 讀檔時的例外從事件處理器拋出，而 packaged build 沒有 console，所以看不到（未逐行確認） | 相同 |
| F-W13 | test.md 的問題：(a) 29 的 `icacls (W)` 包含 SYNCHRONIZE，連讀取都會被拒，測不到「拒寫、允許刪除」，應改為 `(WD,AD,WEA,WA)`；(b) 0.2 的「`Braille/Unicode`（`@` 切分）」寫錯了：類型只有 `General`、`Bopomofo`、`Braille`（Unicode 點字），`@` 切分用在 General 列 | — |

另外，B 無法匯入帶 BOM 的字典（載入用 `utf-8`，不是 `utf-8-sig`）。這正是 F-2 修正的問題，N 已正常。

## 仍需人工

- 9–16、16b：需要 NVDA、視覺或互動判斷。
- 19：真實 7-Zip 的共用模式。
- 24：用真的 Excel／記事本另存一次（可選）。
