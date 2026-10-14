# F-14 Windows 驗證：自動化執行結果（plan Task 6；項目 141–144）

- 日期：2026-10-14，由 Claude（plan 兼實作 agent）執行。
- 受測：`fix/f14-i18n-prep` 在 Task 4 之後（`a8c9369`，`HEAD:client` `d42539e91c59acf99e29d408e5c84367c85bc1c1`，與 plan 的 tree id 相同）的 packaged build，以下稱 N-f14。
- Build：`scripts\build-dotexpress.bat`（PyInstaller 6.21.0，`Build complete!`），在 worktree `D:\workspace\DotExpress-f14` 內以主簽出的 `client\.venv\Scripts` 置於 `PATH` 最前面建置；`PYZ-00.toc` 確認 `i18n.py`、`about.py`、`dialog.py`、`dual_view\html.py`、`settings\dialogs.py`、`documents\formats.py`、`dictionaries\entries.py` 來自 worktree，`Analysis-00.toc` 確認 `gui.py` 來自 worktree。`D:\dxtest\N-f14\DotExpress.exe`：48,794,536 bytes，sha256 `6ACDC6421A00A8E2B1C01C01099ED0C690681F19D09CF827C4F380F92DB68163`。`git status --short -- client scripts docs` 無輸出。
- 改前對照：`D:\dxtest\N-f12b\DotExpress.exe`（`a147fed` 的程式；48,791,375 bytes，sha256 `0F79EAC81386C2DE53D3E92BBA61DE5414A3114B49902E462AF333270BCEC4C2`），只讀取並由腳本複製到各自的資料夾。
- 項目分類（HANDOFF 2026-10-14-01 第 3 節）：141、142 是 **fix** 項目，在 N-f14 與 N-f12b 都執行；143、144 是 **regression** 項目，只在 N-f14 執行，且全部符合預期，所以沒有在 N-f12b 重跑。145 為手動（NVDA），不勾選。
- 方法：pywinauto 0.6.9（UIA 用於訊息框與設定對話框、win32 用於其他視窗）＋ psutil，venv 在 session scratchpad 的 `uia`（其 `Scripts\python.exe` 不見了，以 `py -3.13 -m venv --upgrade` 補回，套件未變）。所有腳本都經 `auto/safe_run.py`（F-12 的版本，改為 `f14gui`，並像 F-13 一樣遮蔽 `f11gui.focused`）執行：只在受測程式的視窗位於前景時才送出按鍵，否則停止；前景不是受測程式時，焦點記為 `<another program>`，所以 log 不含其他程式的視窗或元件名稱。**沒有腳本讀寫剪貼簿**；文字一律經由檔案或 `set_edit_text` 進入程式。每個項目在新的 `D:\dxtest\auto<N>-f14`（N-f14）或 `D:\dxtest\auto<N>-f12b-f14`（N-f12b）資料夾執行，一次一個；`auto/run_item.sh` 先印出並檢查資料夾名稱（必須是 `D:\dxtest\auto…-f14`，且尚不存在），確認 C: 至少 2 GB、可用記憶體至少 600 MB，結束後只結束 exe 位於該資料夾下的程序，並刪除該項目建立、未在使用中的 `%TEMP%\_MEI*`。所有項目前後 `%TEMP%\_MEI*` 的清單相同（90 個，都是先前任務留下的，未動），C: 維持約 5.7 GB。
- 啟動：兩個 build 都還沒有 F-13 的啟動順序變更，所以沿用 F-12 的 `f12gui.start`。
- 腳本：`auto/item141.py`、`auto/item142.py`（原封不動執行 F-12 的 `item114.py` (b)，再讀 `log\config.log`）、`auto/item143.py`、`auto/item144.py`、`auto/manual145.py`（準備手動項目的資料夾，不啟動程式）；共用輔助 `auto/f14gui.py`。輸出在 `D:\dxtest\auto<N>-f14.log` 與 `D:\dxtest\auto<N>-f12b-f14.log`（UTF-8）。

## 與 plan 的偏離與重跑

1. **雙視檢視不是程式內的視窗，而是瀏覽器（144 (a) 的作法改變；第一次執行開了真的瀏覽器）。** spec 的 H1（「雙視檢視」視窗 `DualViewFrame`，`web_view.SetPage`）在這個版本沒有任何呼叫者：「轉譯 > 雙視檢視」執行 `on_open_dual_view` → `_open_dual_view_in_browser`，把頁面寫到 `<d>\dual_view\dual-view-<token>.html` 後用 Chrome／Edge／Firefox（或系統預設程式）開啟；`_show_dual_view` 與 `_create_dual_view_frame` 只在程式碼裡，沒有路徑會呼叫。第一次執行 144（`auto144-f14`，腳本以 `window` 參數保留這種讀法）找不到程式內的視窗，**並且讓 DotExpress 開了兩次使用者的瀏覽器**（`alpha` 的頁面兩次：選取 `beta` 並不會開啟它，見第 2 點）。我沒有讀取、操作或關閉那些瀏覽器視窗（不是受測程式）；頁面檔已在 DotExpress 結束時被它自己刪除。**請使用者自行關閉那兩個瀏覽器分頁或視窗（2026-10-14 約 22:4x 開啟）。** 之後的執行（`auto144r2-f14`、`auto144r3-f14`）先在工作資料夾放一個替身瀏覽器（`where.exe` 的複本，命名為 `chrome.exe`，放在 `PATH` 最前面；它只印出參數錯誤就結束），再讀取程式寫出的頁面檔，所以沒有再啟動真的瀏覽器。這讀到的是 H2（瀏覽器開啟的那一份），也就是使用者實際會看到的頁面；UIA 讀不到 `lang`，所以改讀檔案的 `lang` 與內容。
2. **144 的 `beta`：只選取清單項目不會開啟文件。** `auto144r2-f14` 用 `D.select` 選取 `beta` 後，開啟中的仍是 `alpha`（`on_document_selection_changed` 只選取），所以第二個頁面仍是 `alpha` 的。`auto144r3-f14` 在選取後加上「檔案 > 開啟」，得到 `beta` 的頁面；以 `auto144r3-f14` 為正式結果。
3. 其餘項目都一次完成。

## 逐項結果

| # | 類別 | N-f14（改後） | N-f12b（改前） | 判定 |
| --- | --- | --- | --- | --- |
| 141 (a) | fix | `alpha`（`中文 abc`）轉換後「檔案 > 匯出 > 雙視檢視 HTML」：`alpha.html` 前兩行 `<!doctype html>`、`<html lang="zh-TW">`，6 個 cell，CRLF | 同樣的檔案，但 `<html lang="en">` | ✔ |
| 141 (b) | fix | 空工作區的預設文件 `new`（沒有轉換資料）匯出：`<html lang="zh-TW">`，含 `此文件沒有可顯示的轉換資料。`，0 個 cell | `<html lang="en">`，同樣的中文句子 | ✔ |
| 141 (c) | fix | `beta` 也轉換後「全部匯出 > 雙視檢視 HTML」：`alpha.html`（6 cell）、`beta.html`（9 cell）都是 `<html lang="zh-TW">`；框 `所有文件皆已成功匯出。` | 兩個檔案都是 `<html lang="en">` | ✔ |
| 142 | fix | `config.json` = `{`、`config.json.bak` 是資料夾。改寬度後按「套用」：一個框，標題 `設定未儲存`，main `DotExpress 無法將設定儲存到「<d>\config.json」。…不會再顯示這則訊息。`，content **`檔案已損壞，而且在取代它之前無法先備份為「<d>\config.json.bak」。檔案或備份檔可能正被其他程式使用，或你沒有該資料夾的寫入權限。請關閉其他程式後再試一次。`**（沒有 `WinError`、`存取被拒`、`.tmp`、`詳細資訊`），owner `DotExpress 設定：轉譯`；按「確定」後沒有框；`config.json` 仍是 `{`，`config.json.bak` 仍是資料夾；`log\config.log` 的 ERROR 都是 `Failed to save config file <d>\config.json`，traceback 含 `WinError 5` | 同一個框，但 content 是 `檔案已損壞，而且在取代它之前無法先備份為「<d>\config.json.bak」。詳細資訊：[WinError 5] 存取被拒。: '<d>\\.config.json.bak.<rnd>.tmp' -> '<d>\\config.json.bak'`；其餘相同 | ✔ |
| 143 (a) | regression | 「說明 > 關於」：標題 `關於 DotExpress`，content 以 `DotExpress (DotExpress)`、`版本：1.2 (1.2)`、`網址：https://coseeing.org`、`版權所有 (C) 2025-2026 DotExpress 貢獻者` 開頭，全文與 F-14 之前的 zh_TW 文字相同，owner 主視窗 | — | ✔ |
| 143 (b) | regression | 設定：標題 `DotExpress 設定：轉譯`，分類 `轉譯`、`轉譯表`、`檢視`，面板 `轉譯` 的描述（UIA `LegacyIAccessible.Description`）`轉譯輸出模式、寬度與字典選項`；Ctrl+Tab：`DotExpress 設定：轉譯表`、`不同語言的轉譯表對應`；再 Ctrl+Tab：`DotExpress 設定：檢視`、`主視窗輸入與輸出區的字型、字體大小與配色`；取消後沒有框 | — | ✔ |
| 143 (c) | regression | 字典 `types` 的編輯器：類型欄 `一般`、`注音`、`Unicode 點字`；「新增」的類型選項 `一般`、`注音`、`Unicode 點字`，預設 `一般`；兩次取消後沒有框 | — | ✔ |
| 144 (a) | regression | （`auto144r3-f14`，替身瀏覽器）`alpha` 轉換後「轉譯 > 雙視檢視」：頁面 `<html lang="zh-TW">`，6 個 cell，沒有錯誤框；開啟 `beta`（未轉換）後再一次：`<html lang="zh-TW">`，0 個 cell，含 `此文件沒有可顯示的轉換資料。`，沒有錯誤框；程式結束後 `dual_view` 資料夾是空的 | — | ✔（作法見偏離 1） |
| 144 (b) | regression | `config.json` 完好時改寬度為 30、按「確定」：沒有框；`config.json` 的 width 為 30 | — | ✔ |

## 仍需人工（使用者）

- [ ] **145（NVDA）**：用 `D:\dxtest\manual145-f14`（`auto/manual145.py` 準備：N-f14 的 exe、待轉換的文件 `中文`、`config.json` = `{` 加上資料夾 `config.json.bak`、空的 `out\`）。開啟 NVDA 並打開自動切換語言，啟動 `D:\dxtest\manual145-f14\DotExpress.exe`：
  1. 轉換 `中文`（Ctrl+Enter），按「轉譯 > 雙視檢視」：頁面在瀏覽器開啟，用 NVDA 閱讀，中文是否用中文語音讀出？（N-f12b 的頁面宣告 `lang="en"`，可能用英文語音。）
  2. 「檔案 > 匯出 > 雙視檢視 HTML」存到 `out\`，在瀏覽器開啟該檔，同樣確認語音。
  3. 「轉譯 > 設定」改寬度後按「套用」：聽 142 的框，是否整段讀出、沒有暫存檔名？
  轉換結果會留在 `中文.dep`；要從頭再試時，用 `auto/manual145.py` 準備另一個新的資料夾。
