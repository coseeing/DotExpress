# F-12 Windows 驗證：自動化執行結果（plan Task 11；項目 109–118、120）

- 日期：2026-10-11，由 Claude 執行（前一位 agent 完成程式碼與 dev 複本後交接；本次的 plan 補完、replay、落地、build 與 GUI 項目都由接手的 agent 完成）
- 受測：`fix/f12-localization-cleanup` 在 Task 9 之後（`b52ac5c`，`HEAD:client` `62325f9a05b0cd0a1af9344cd078e417c09910d1`，與 plan Task 8、Task 9 的 tree id 相同；`HEAD:scripts` `6a2bd0cb0ea886626e676bd69458b9939bd2462e`）的 packaged build，以下稱 N-f12。九個 commit 的 tree id 都與 plan 相同（見 plan 的 Implementation Notes）。
- Build：`scripts\build-dotexpress.bat`（PyInstaller 6.21.0、Python 3.13.15，`Build complete!`，約 44 秒），在 worktree `D:\workspace\DotExpress-f12` 內以主簽出的 `client\.venv\Scripts` 置於 `PATH` 最前面建置；`PYZ-00.toc` 確認十二個變更的模組與 `gui.py` 都來自 worktree。`D:\dxtest\N-f12\DotExpress.exe`：48,792,061 bytes，sha256 `0D0239440B5D7E51977B9F5C74E752F46661186DEEC935AE6096284C44D49C82`。
- 改前對照：`D:\dxtest\N-f11c\DotExpress.exe`（F-11 I-1 之後的 build，`e0337df` 的程式；48,779,918 bytes，sha256 `1E978045C581F2062EFC4196F2F192380E8BD2F8B234D8AB68CA47E10B3A983B`），只讀取並由腳本複製到各自的資料夾；執行後大小與 sha256 不變。
- 項目分類（使用者，2026-10-11）：**fix** 項目是兩個 build 的預期結果不同，或項目經過的程式碼有改動；**regression** 項目兩者都不是。109–117 與 120 是 fix 項目，在 N-f12 與 N-f11c 都執行；118 是 regression 項目，只在 N-f12 執行，且全部符合預期，所以沒有在 N-f11c 重跑。119 為手動（NVDA），不勾選。
- 方法：pywinauto 0.6.9（UIA 用於訊息框、win32 用於其他視窗）＋ psutil，venv 在 `$SP\uia`。wx 的訊息框是 task dialog，以 UIA 讀取（`f5gui.describe`：title、main instruction、content、buttons、focus）並以按鍵回答；`owner` 是擁有該對話框的視窗標題（主視窗寫成 `<main>`）。所有腳本都經 `auto/safe_run.py`（F-11 的版本，改為 `f12gui`）執行：只在受測程式的視窗位於前景時才送出按鍵，否則停止；前景不是受測程式時，焦點記為 `<another program>`，所以 log 不含其他程式的視窗或元件名稱。`<d>` 是該項目的工作資料夾，`<rnd>` 是暫存檔名稱的亂數部分。每個項目都在新的 `D:\dxtest\auto<N>-f12`（N-f12）或 `D:\dxtest\auto<N>-f11c-f12`（N-f11c）資料夾執行，exe 複製到該資料夾再啟動；config、字典、`preprocessing.py` 與 `.dep` 套件都由腳本在啟動前以位元組寫入。一次只跑一個項目，每個項目開始前先確認可用記憶體至少 600 MB（使用者設定）。只結束 exe 位於這些資料夾的程序（`dx.kill_under`）與該項目的 `lockshare.py`。沒有動到既有的 `D:\dxtest\N*`、`B` 與既有的 `D:\dxtest\auto*` 資料夾，也沒有碰主簽出的 `client\dictionary`、`workspace`、`config.json`、`log`。沒有任何腳本讀寫剪貼簿：文字只經由檔案與 `set_edit_text` 進入程式。
- 腳本：`auto/item109.py`（109、110）、`item111.py`、`item112.py`、`item113.py`、`item114.py`（114 a、b）、`item115.py`（115 a、b、c）、`item116.py`、`item117.py`、`item118.py`、`item120.py`，共用 `auto/f12gui.py`；沿用 F-9 的 `f9gui.py`、F-8b 的 `f8bgui.py`、F-8a 的 `f8agui.py` 與 `lockshare.py`、F-7 的 `f7gui.py`、F-5 的 `f5gui.py` 與 2026-10-09-03 的 `dx.py`、`docs.py`、`dicts.py`（都未修改）。輸出在 `D:\dxtest\auto<N>-f12.log` 與 `D:\dxtest\auto<N>-f11c-f12.log`（UTF-8，從 Git Bash 以 `safe_run.py` 執行）。
- 結果：27 個正式 log（13 個項目執行 × 2 個 build，加上只在 N-f12 執行的 118），**全部與 plan Task 11 Step 4 的預期一致**；114 (a) 的步驟有一處偏離（見下一節）。

## 與 plan 的偏離與重跑

1. **114 (a)：「從啟動前就以 share-none 占住 `config.json`」做不到。** 第一次在 N-f12 以 plan 的步驟執行時，程式根本沒有啟動：它在啟動時寫入 `config.json` 失敗，顯示啟動錯誤框（標題 `啟動錯誤`，`DotExpress 無法寫入應用程式資料目錄：…\config.json … [Errno 13] Permission denied`）後結束（exit code 1），沒有主視窗。這是 F-8 的啟動檢查，F-12 沒有改它。腳本改為**啟動之後、按設定的「確定」之前**才以 share-none 占住 `config.json`（與 F-11 項目 105 的做法相同）；這樣關閉的是 F-12 要驗證的情境（設定存檔失敗），預期結果不變。plan 的 Step 4 表格與 spec 的項目 114 (a) 寫的是「from before the start」，以此處為準。該次失敗的資料夾與 log 已刪除，之後的 `auto114a-f12.log` 是第一個有效結果；改前 build 沒有在「啟動前占住」的情況另外執行。
2. **腳本的小問題（都在 app 啟動之前或與結果無關，刪除該次資料夾與 log 後重跑）：** `auto109-f12` 第一次因 `f12gui` 缺少 `EXPORT_ALL_DIALOG` 常數而 `AttributeError`（程式已啟動，以 exe 路徑結束了它）；`auto112-f12` 兩次在建立 Big5 字典時失敗（`cp950` 無法編碼點字字元；之後是 here-doc 把 `\r\n` 變成真正的換行造成 `SyntaxError`），都在 app 啟動前；`auto110-f12` 與 `auto114b-f12` 的第一次 log 顯示未遮蔽的暫存檔名（`.beta.brl.<16 位十六進位>.tmp`、`.config.json.bak.<…>.tmp`），行為正確，只是遮蔽規則不夠，補上 `brl` 與 `bak` 後重跑。其餘每個項目都是第一次就一致。
3. **鎖定程序：** 以 `lockshare.py` 占住的檔案（110、111、112 的 locked 字典、114 (a)、120）都在腳本結束時解鎖；114 (a) 第一次失敗時留下的占住程序，由我以命令列同時含 `lockshare.py` 與該資料夾名稱為條件結束，之後 `run_item.sh` 也在每次執行後做同樣的清理。

## 逐項結果

| # | 類別 | N-f12（改後） | N-f11c（改前） | 判定 |
| --- | --- | --- | --- | --- |
| 109 | fix | 訊息框 `匯出完成`／`所有文件皆已成功匯出。`；`out\` 有 `alpha.brl`、`beta.brl`、`gamma.brl` | 同一框，內容 `All documents were exported successfully.`；三個檔案相同 | ✔ |
| 110 | fix | 覆蓋確認框（是）→ `匯出完成，但有錯誤`／`成功匯出的文件：2`、`匯出失敗的文件：1`、空行、`beta: [WinError 5] 存取被拒。: '<d>\\out\\.beta.brl.<rnd>.tmp' -> '<d>\\out\\beta.brl'`；`beta.brl` 仍是 `OLD BETA EXPORT`，`alpha.brl`、`gamma.brl` 已寫入 | 標題 `Export Complete with Errors`、`Exported documents: 2`、`Failed documents: 1`，其餘相同 | ✔ |
| 111 | fix | 匯入問題：`alpha.txt: 文件「alpha」已存在。`、`big5.txt: 檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。`、`broken.dep: 匯入的檔案必須是有效的 DotExpress DEP 封裝檔。`、`foo.xyz: 無法匯入這種類型的檔案。`、`locked.txt: 無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。`、`<40 個 x>.txt: 文件名稱長度需為 1 到 32 個字元。`；清單與工作區只有 `alpha` | 英文與原始文字：`Document "alpha" already exists.`、`'utf-8' codec can't decode byte 0xbb in position 0: invalid start byte`、`File is not a zip file`、`Unsupported import file type: ".xyz".`、`[Errno 13] Permission denied: '<d>\\data\\locked.txt'`、`Name cannot exceed 32 characters.` | ✔ |
| 112 | fix | Convert：`big5dict` → `轉譯失敗：無法讀取字典「big5dict」。檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。`；`caps`、`empty` → `轉譯失敗：無法讀取字典「<name>」。無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。`；`locked` → `…無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。`；點字結果都是空的。Export All（`big5dict`、兩份待轉換文件）：`匯出完成，但有錯誤`、`成功匯出的文件：0`、`匯出失敗的文件：2`，每份一行 `p1: 轉譯失敗：無法讀取字典「big5dict」。…`；`out\` 空 | `轉譯失敗：'utf-8' codec can't decode byte 0xa5 in position 19: invalid start byte`、`轉譯失敗：CSV must contain columns: text, braille, type`、`轉譯失敗：CSV must contain header row.`、`轉譯失敗：[Errno 13] Permission denied: '<d>\\dictionary\\locked.csv'`；Export All 摘要為英文標題與計數，每行同樣的原始文字 | ✔ |
| 113 | fix | 工作區有 `alpha.dep`（有效）與 `bad.dep`（無效，啟動時選「保留無效檔案」）。新增 `BAD`、將 `alpha` 重新命名為 `bad`：錯誤框，main instruction `名稱「BAD」已被工作區資料夾中的「bad.dep」使用，但這個檔案不在文件清單中。`（重新命名時為「bad」），content `請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：` 換行 `<d>\workspace`；名稱對話框再次出現並保留所輸入的名稱。匯入 `bad.txt`：`bad.txt: 名稱「bad」已被工作區資料夾中的「bad.dep」使用，但這個檔案不在文件清單中。`；`bad.dep` 位元組不變 | `文件「BAD」已存在。`、`文件「bad」已存在。`、`bad.txt: Document "bad" already exists.`；名稱對話框同樣再次出現；`bad.dep` 不變 | ✔ |
| 114 (a) | fix | 設定對話框改轉換寬度後按「確定」：一個框，標題 `設定未儲存`，main `DotExpress 無法將設定儲存到「<d>\config.json」。設定的變更在關閉 DotExpress 之前有效，但不會保留。在下次啟動 DotExpress 之前，不會再顯示這則訊息。`，content `無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。`，owner `DotExpress 設定：轉譯`；之後 Ctrl＋滾輪沒有任何框，字型高度 -16 → -17（畫面上改變）；`config.json` 位元組不變（偏離 1：`config.json` 在啟動之後才被占住） | 沒有框；字型高度 -16 → -17；`config.json` 不變 | ✔ |
| 114 (b) | fix | `config.json` 為 `{`、`config.json.bak` 是資料夾。改寬度後按「套用」：一個框，標題 `設定未儲存`，main 同上，content `檔案已損壞，而且在取代它之前無法先備份為「<d>\config.json.bak」。詳細資訊：[WinError 5] 存取被拒。: '<d>\\.config.json.bak.<rnd>.tmp' -> '<d>\\config.json.bak'`，owner `DotExpress 設定：轉譯`；再按「確定」沒有任何框；`config.json` 仍是 `{`，`config.json.bak` 仍是資料夾 | 套用與確定都沒有框；`config.json` 仍是 `{` | ✔ |
| 115 (a) | fix | 轉換 `alpha`（`main` 睡 5 秒後擲出 `ValueError("boom")`）並立刻 Ctrl+Tab 到 `beta`：框 `錯誤`，main `無法轉換文件「alpha」。`，content `文字處理失敗：boom`；標題停在 `beta - DotExpress`；兩個套件仍是待轉換 | 只有 `文字處理失敗：boom` | ✔ |
| 115 (b) | fix | 開著 `alpha`，在清單選取 `beta` 後 File > Export > BRL：框 `錯誤`，main `無法轉換文件「beta」。`，content `文字處理失敗：boom`；沒有匯出檔 | 只有 `文字處理失敗：boom` | ✔ |
| 115 (c) | fix | 轉換 `alpha` 後不切換：只有 `文字處理失敗：boom` | 相同 | ✔ |
| 116 | fix | 預設文件 `new`、File > Export > Dual View HTML：存檔對話框的檔案類型只有 `HTML 檔 (*.html)`；匯出成功框 `文件已成功匯出。`；檔案（1211 字元）含 `此文件沒有可顯示的轉換資料。`，不含英文句子 | 類型 `HTML files (*.html)`；檔案（1247 字元）含英文句子 `No conversion data`，不含中文句子 | ✔ |
| 117 | fix | `文字處理失敗：main 必須傳回 str，而不是 NoneType。` | `文字處理失敗：main must return str, got NoneType.` | ✔ |
| 118 | regression | (a) `轉換完成。`（資訊框），點字結果 `⠁⠃` 加空白補到寬度；(b) 新增 `alpha`：`文件「alpha」已存在。`，名稱對話框再次出現（保留 `alpha`）；(c) 設定「確定」沒有框，`config.json` 的 `conversion.width` 為 30；(d) 重新啟動並使用 520,000 字元的 `alpha`：Ctrl+Enter、Ctrl+Tab 到 `beta`：`轉換完成。結果已儲存到文件「alpha」。`，`beta` 的編輯區為 `beta body`／`⠃`，`alpha.dep` 的點字有 991,999 字元 | （全部符合預期，未在 N-f11c 執行） | ✔ |
| 120 | fix | `alpha`、`beta` 皆有效，`alpha` 開著；啟動後 `beta.dep` 被 share-none 占住。File > Delete All、是：`刪除文件失敗：[WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用。: '<d>\\workspace\\beta.dep'` 錯誤框；無效檔案對話框列出 `beta.dep`（保留）；之後視窗標題 `new - DotExpress`，清單為 `new`，編輯區為空，`workspace` 有 `beta.dep` 與 `new.dep` | 同樣的錯誤框與無效檔案對話框；之後標題仍是 `alpha - DotExpress`，清單為空，編輯區為空，`workspace` 只有 `beta.dep`（沒有 `new.dep`） | ✔ |

## 修正階段（F-12 審查 M-1、M-2、M-3、M-5；2026-10-11）

- 受測：`fix/f12-localization-cleanup` 在 `bdb3e78` 之後的 packaged build，以下稱 N-f12b。Build 方法同上（`scripts\build-dotexpress.bat`，主簽出的 `client\.venv\Scripts` 置於 `PATH` 最前面，`Build complete!`），`HEAD:client` `a967d8d4cea147cf25ccc0f490c8f94e41e711ce`。`D:\dxtest\N-f12b\DotExpress.exe`：48,791,375 bytes，sha256 `0F79EAC81386C2DE53D3E92BBA61DE5414A3114B49902E462AF333270BCEC4C2`。建置與每個項目開始前可用記憶體都至少 600 MB（建置前 1,119 MB）。N-f12、N-f11c 與其他 build 沒有動。
- 重跑的項目與方法：114 (a)、114 (b)（M-2、M-5 改了訊息框的原因）與 111（M-1 與 M-3 改了匯入問題的程式路徑）。每個項目都在新資料夾執行：N-f12b 為 `D:\dxtest\auto<N>-f12b`，N-f11c 為 `D:\dxtest\auto<N>-f11c-f12b`；一次一個；經 `auto/safe_run.py`（只在受測程式位於前景時送按鍵，log 不含其他程式的名稱）；`auto/run_item.sh` 新增 build 名稱 `newb`、`beforeb`。沒有任何腳本讀寫剪貼簿。只結束 exe 位於這些資料夾的程序與該項目的 `lockshare.py`。
- 腳本小問題：`auto114a-f12b` 第一次執行的最後一行是 `config.json bytes unchanged: False`。原因是腳本在視窗出現後立即讀取「之前」的位元組，而程式在稍後才寫入 client id（檔案的修改時間早於鎖定時間，`config.log` 也沒有寫入記錄），與程式碼無關。`item114.py` 在讀取前加了 2 秒等待，該次資料夾與 log 已刪除並重跑，以下是重跑的結果。

| # | N-f12b（改後） | N-f11c（改前） | 判定 |
| --- | --- | --- | --- |
| 114 (a) | 設定對話框改轉換寬度後按「確定」：一個框，標題 `設定未儲存`，owner `DotExpress 設定：轉譯`，content `無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。`（`PermissionError`，與 N-f12 相同）；Ctrl＋滾輪沒有框，字型高度 -16 → -17；`config.json` 位元組不變 | 沒有框；字型高度 -16 → -17；`config.json` 不變 | ✔ |
| 114 (b) | 按「套用」：一個框，owner 設定對話框，content `檔案已損壞，而且在取代它之前無法先備份為「<d>\config.json.bak」。詳細資訊：[WinError 5] 存取被拒。: '<d>\\.config.json.bak.<rnd>.tmp' -> '<d>\\config.json.bak'`（備份失敗的文字仍附作業系統文字，刻意保留，見 Spec Corrections 19）；按「確定」後沒有框；`config.json` 仍是 `{`，`config.json.bak` 仍是資料夾 | 沒有框；其餘相同 | ✔ |
| 111 | 匯入問題的六行與 N-f12 完全相同（沒有 DOCX、EPUB、PDF 的檔案，所以 M-3 的文字沒有出現在這個項目）；`log\gui.log` 有一筆 ERROR：`Cannot import "broken.dep" as dep: BadZipFile: File is not a zip file` 與 traceback（M-1 的記錄；沒有框） | 英文與原始 Python 文字，與先前記錄相同；沒有 `gui.log` | ✔ |

- 設定存檔失敗時「不是存取錯誤」的原因（磁碟已滿、其他 `OSError`）與損壞的 DOCX、EPUB、PDF 的新文字沒有在 GUI 重現（要有真實的磁碟已滿、或一個損壞的檔案經檔案對話框匯入），它們由單元測試涵蓋（`test_gui_document_flows`、`test_import_problems` 的真實函式庫檔案、`test_document_workspace`）。

## 仍需人工（使用者）

- [ ] **項目 119（NVDA）：** 以 `D:\dxtest\N-f12b\DotExpress.exe`（含審查修正的 build；先前的 N-f12 也可以，這四個框的文字相同）並開啟 NVDA，聽以下四個框：項目 112 的其中一種情況（例如 big5dict 的 Convert）、113（新增 `BAD`）、114 (a)（設定存檔失敗）、115 (a)（切換到 `beta` 之後的轉換失敗）。請確認：整段文字是否都被讀出，包括文件名稱、字典名稱與路徑；按 Esc 是否能關閉每個框；關閉之後焦點在哪裡。這項沒有自動化，未勾選。
