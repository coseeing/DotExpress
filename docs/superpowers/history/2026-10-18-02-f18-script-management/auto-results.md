# F-18 腳本管理：Windows 打包版 GUI 自動測試結果

2026-10-18，plan＋實作 agent 執行。計畫：`docs/superpowers/plans/2026-10-18-f18-script-management.md` Task 5。

## 打包版本

- **`D:\dxtest\N-f18b\DotExpress.exe`（最終版本，以下結果都用這個）**：`fix/f18-script-management` 的 `2e5057f`（`HEAD:client` `c9b6ef97d4ed27835c829a77e53c8494dca4b8e1`，含編輯器標籤的修正），PyInstaller 6.21.0，`Build complete!`，48,822,842 bytes，sha256 `D1C9BFFEF05B0EABF3938638F7A375ACC1EBEFD7768F7AD8655942633E71123C`。`text_scripts.actions`、`manager`、`presenter`、`read_problems` 與 `shared.file_targets` 都在 PyInstaller 的 xref 中。
- `D:\dxtest\N-f18\DotExpress.exe`：第一次打包（`b84b3fe`，`HEAD:client` `c825cb3b`，48,822,215 bytes，sha256 `A143B61748C948C00DB14D431C96113FDA355FEF79839A5B73030FA178B8CBA7`）。在這個版本上跑了 146、147、149 後發現編輯器的無障礙名稱不對（見下方「發現與修正」），修正後重新打包為 N-f18b，所有項目在 N-f18b 重跑。N-f18 保留未刪。
- 舊版：`D:\dxtest\N-f14b\DotExpress.exe`（F-13＋F-14，F-18 之前）。
- `script\` 不需要改打包設定：`prepare_application_directories` 在 exe 旁邊建立，和 `dictionary\` 一樣（項目 146 確認）。

## 方法

- 腳本：`auto/f18gui.py`（共用：沿用 F-13 的 `f13gui.start` 與更早的 helper，F-14 的替身瀏覽器）、`auto/item146.py`（146、148）、`item147.py`、`item149.py`（149–151）、`item152.py`（152–153）、`item154.py`（154–155）、`item156.py`、`item157.py`、`item158.py`（回歸）、`manual159.py`（準備手動項目資料夾，不啟動程式）、`run_item.sh`、`run_all.sh`。
- 每個項目一個新資料夾 `D:\dxtest\auto<N>-f18b`（舊版 `auto<N>-f14b-f18`），經 F-13 的 `auto/safe_run.py` 執行：DotExpress 在前景時才送按鍵，log 不記錄其他程式的視窗或元件名稱。`run_item.sh` 只接受 `D:\dxtest\auto*-f18`／`-f18b` 資料夾、資料夾已存在就不執行、C 槽少於 2 GB 或可用記憶體少於 600 MB 就不執行；結束後只結束該資料夾底下的程序，只刪除 F-13 `mei_poll.ps1` 記錄到的、這個項目自己的 `_MEI*`。每個工作資料夾都把替身 `chrome.exe`（`where.exe` 的複本）放在 PATH 最前面。
- **沒有任何腳本讀寫剪貼簿**：編輯器的程式碼用 `WM_SETTEXT` 放入，名稱欄位與檔案對話框用 `set_edit_text`（`WM_SETTEXT`），按鈕用 `BM_CLICK`，系統是／否框的按鈕用 UIA invoke（F-17 之後沒有快速鍵）。
- 輸出：`D:\dxtest\auto<N>-f18b.log` 等（UTF-8）。項目分類：146–157 是 F-18 新功能（fix），舊版沒有腳本管理，所以只有 147（舊的 `preprocessing.py`）在新舊版都跑；158 是回歸項目，其中 (a) 的點字也在舊版跑來比對。

## 結果

| # | 規格 | 結果 | 判定 |
| --- | --- | --- | --- |
| 146 | 150 | 新資料夾啟動：`script\` 只有 `no-processing.py`，內容與規格文字逐位元組相同；「轉譯」選單為 `執行轉換、雙視檢視、腳本管理...、字典管理...、設定`（「腳本管理...」在原「文字處理」的位置）；設定 > 轉譯的標籤為 `點字類型、寬度、字典、文字處理腳本`，腳本下拉為 `['不處理']`、選取 `不處理`；取消後 `config.json` 未寫入 | ✔ |
| 147 | 151 | `dictionary\preprocessing.py`（轉大寫）：N-f18b 轉換 `abc` 得 `⠁⠃⠉`、`ABC` 得 `⠠⠠⠁⠃⠉`，兩者不同（腳本沒有執行）；檔案位元組不變；`config.json` 在設定「套用」前沒有 `selected_script`，套用後為 `no-processing`。舊版 N-f14b：`abc` 也得 `⠠⠠⠁⠃⠉`（舊腳本有執行）、套用後沒有 `selected_script` | ✔ |
| 148 | 152 | 腳本管理：列 `[['不處理', '可使用']]`、選取第 0 列、焦點在清單項目「不處理」；新增、匯入、匯出啟用，刪除、重新命名、編輯停用；沒有原因欄；關閉後沒有其他視窗 | ✔ |
| 149 | 153 | 新增 `upper`：名稱框空白；編輯器標題 `upper`、內容是範本（`def main(input: str) -> str:` …）、UIA 名稱 `Python 程式碼`（Document）、焦點在編輯器；換成轉大寫的 `main` 後「確定」：只剩腳本管理視窗、列多了 `upper 可使用` 並被選取、焦點回到清單項目 `upper`；`script\upper.py` 與輸入的文字相同。設定選 `upper`、確定：`config.json` 的 `selected_script` 為 `upper`；轉換 `abc` 的點字等於先前 `ABC`（No Processing）的點字 | ✔ |
| 150 | 154 | 新增 `bad`，`def main(a, b): return a`，套用：框「儲存腳本失敗：main 必須恰好定義一個位置參數，且不得有其他參數。」（owner `bad`）；框後焦點回到編輯器（`Python 程式碼`）；沒有 `bad.py`；取消：框「要放棄對腳本「bad」所做的變更嗎？」（標題「尚未儲存的變更」，按鈕「放棄變更」「返回編輯」，預設焦點「返回編輯」）；放棄變更後編輯器關閉，清單沒有 `bad` | ✔ |
| 151 | 155 | `def main(x: int) -> str:`：「儲存腳本失敗：main 的參數只能標註為 str，或不加標註。」；取消、放棄變更後沒有 `typed` | ✔ |
| 152 | 156 | 匯入 `upper2.py`（BOM＋CRLF）：名稱框預設 `upper2`，沒有框，複本位元組與來源相同，並被選取；`x.txt`（在檔案對話框輸入完整路徑）：「匯入腳本失敗：只能匯入 Python 檔案（.py）。」；`cp950.py`：「匯入腳本失敗：檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。」；`bad.py`（缺冒號）：「匯入腳本失敗：expected ':' (bad.py, line 1)」；失敗的都沒有複製 | ✔ |
| 153 | 157 | 以 `upper` 匯入：「腳本「upper」已存在。」，名稱框再次出現且保留 `upper`；取消後 `script\upper.py` 不變 | ✔ |
| 154 | 158 | `config.json` 選 `upper`：設定顯示 `upper`，`abc` 轉為大寫點字。重新命名 `upper` → `Upper2`（名稱框預設 `upper`）：列為 `Upper2` 並選取，`config.json` 為 `Upper2`，設定顯示 `Upper2`。刪除 `Upper2`：框「要刪除腳本「Upper2」嗎？」（「確認刪除腳本」，按鈕「是」「否」，預設焦點「否」）按「是」：列只剩「不處理」並選取，`config.json` 為 `no-processing`，設定顯示「不處理」，`abc` 轉換結果回到小寫（與 `ABC` 不同） | ✔ |
| 155 | 159 | `no-processing.py` 先改成轉大寫的內容；匯出「不處理」：對話框預設檔名 `no-processing.py`，沒有框；匯出的檔案等於規格文字，磁碟上的 `no-processing.py` 保留被改的內容（同一次執行中 154 的轉換證明 No Processing 不執行該檔） | ✔ |
| 156 | 160 | `locked.py` 由 `lockshare.py`（share none）佔住、`broken.py` 語法錯誤：腳本管理正常開啟，列 `不處理 可使用`、`broken 格式不正確`、`locked 無法讀取`；選 `locked`：原因欄標籤「無法使用的原因：」、內容為無法開啟檔案的說明；編輯：框（主旨「無法讀取腳本「locked」。」、內容同上），腳本管理仍開著；選 `broken`：原因「expected ':' (broken.py, line 1)」；編輯：編輯器開啟、內容為檔案文字；未修改直接取消立即關閉、沒有框；兩個檔案不變；`gui.log` 對 `locked.py` 每次重新整理記一行（共 4 行，沒有 traceback） | ✔ |
| 157 | 161 | 選用 `upper` 後在程式外刪除 `upper.py`，轉換：框「文字處理失敗：[Errno 2] No such file or directory: '<d>\\script\\upper.py'」，點字結果維持上一次的內容；重新啟動後設定顯示「不處理」，`config.json` 仍是 `upper`（下次儲存設定時才改寫） | ✔ |
| 158 | 162 | 回歸。(a) 混合文字（中文、英文、數字、字典詞「甲乙」、行內數學）的點字在 N-f18b 與 N-f14b 完全相同（sha256 前 16 碼 `92b8d86cddb6ed6a`）。(b) 字典管理：新增 `dict2`、重新命名為 `dict3`、刪除（框「要刪除字典「dict3」嗎？」，新版按鈕「是」「否」、舊版「是(Y)」「否(N)」）、編輯 `good` 時字典管理關閉並開啟自訂字典管理器、取消直接關閉；兩版行為相同。(c) 設定寬度改 30、確定：沒有框，`config.json` 寬度 30 | ✔ |

## 發現與修正

- **編輯器的無障礙名稱**：第一次打包（N-f18）的項目 149 讀到編輯器的 UIA 名稱是 `RichEdit Control`，不是規格 O9 的「Python 程式碼」：`SetName` 不會成為螢幕閱讀器讀到的名稱（舊的「文字處理」對話框也是同樣的寫法）。修正 `2e5057f`「fix: name the script editor through a label before it (F-18)」：在編輯器前面建立標籤「Python 程式碼」（既有字串，不新增 msgid），和字典管理的原因欄一樣由前一個標籤提供名稱；先改測試（`test_script_dialogs` 的建構測試，紅燈），再改 `dialog.py`，目錄只有 `#:` 行號變動，`.mo` 不變。N-f18b 上 149、150、156 讀到的名稱都是 `Python 程式碼`。
- 舊版 158 第一次（`auto158-f14b-f18`）在刪除確認框停住：舊版的按鈕是「是(Y)」，腳本用完整名稱找「是」而找不到；`f18gui.box_press` 改成忽略括號內的快速鍵後重跑（`auto158r2-f14b-f18`），結果如上表。(a) 的點字在第一次就已讀到，兩次相同。

## review 修正後（N-f18c）

2026-10-18，修正 agent 執行，對應 `review_task.md` 的 I-1、M-2、M-3、M-5、M-6（見該檔「修正記錄」）。

- **打包版本 `D:\dxtest\N-f18c\DotExpress.exe`**：`fix/f18-script-management` 的 `b07234c`（`HEAD:client` `612bb9e5f55860c5e45be86be81c549dd3a7ee3b`），PyInstaller 6.21.0，`Build complete!`，48,823,692 bytes，sha256 `4D920C0D55F405F67EE7E8B1FF2962A861E3D554C6EB2E271C3D310E7BC5FF8B`。打包前 C 槽 10.5 GB、可用記憶體 653 MB。
- **腳本的變動**：`run_item.sh` 新增 `fix`（N-f18c，資料夾 `auto<N>-f18c`）；`f18gui.py` 新增 `press_focused`（先把鍵盤焦點放在按鈕上再按，和鍵盤使用者相同）與 `script_log_lines`；`item152.py` 的名稱框改為可有可無（M-2），每次匯入後記錄焦點；`item154.py` 以 `press_focused` 按「重新命名」「刪除」並記錄之後的焦點與按鈕；`item156.py` 記錄「編輯」`locked` 新增的 `gui.log` 行；新增 `item154b.py`（刪除最後一列、程式外已刪除的腳本、第一個使用者腳本，且 `no-processing.py` 是資料夾）。各項目以 `bash run_item.sh <N> item<N>.py fix` 逐一執行，每次結束後沒有殘留程序，`_MEI*` 只刪自己的。

| # | 結果（N-f18c） | 判定 |
| --- | --- | --- |
| 152 | 匯入 `upper2.py`：名稱框 `upper2`、沒有框、位元組相同、**焦點在清單項目 `upper2`**（I-1）；`x.txt`：**沒有名稱框**，直接出現「匯入腳本失敗：只能匯入 Python 檔案（.py）。」（M-2），之後焦點在「匯入」按鈕（沒有重新整理，按鈕仍可用）；`cp950.py`、`bad.py` 的訊息與 N-f18b 相同，焦點在「匯入」；資料夾只有 `no-processing.py`、`upper.py`、`upper2.py` | ✔ |
| 153 | 與 N-f18b 相同（「腳本「upper」已存在。」、名稱框再出現並保留 `upper`、取消後 `upper.py` 不變）；取消後焦點在「匯入」 | ✔ |
| 154 | 與 N-f18b 相同（轉換、重新命名、`config.json`、設定、刪除）；另外：**重新命名後焦點在清單項目 `Upper2`**；**刪除唯一的使用者腳本後選取「不處理」，焦點在清單項目「不處理」**，刪除／重新命名／編輯停用 | ✔ |
| 155 | 與 N-f18b 相同 | ✔ |
| 154b | 新增項目。`no-processing.py` 是資料夾：清單 `不處理、alpha、gone、zeta`（M-5：「不處理」仍在第一列），設定為 `['不處理']`、選取「不處理」。刪除 `zeta`（最後一列）：選取上一列 `gone`，焦點在清單項目 `gone`。程式外刪掉 `gone.py` 後刪除 `gone`（作用中）：**沒有錯誤框**（M-6），清單 `不處理、alpha`，`config.json` 改為 `no-processing`，焦點在清單項目 `alpha`。刪除 `alpha`（第一個使用者腳本）：選取「不處理」、刪除停用，**焦點在清單項目「不處理」**（I-1） | ✔ |
| 156 | 與 N-f18b 相同；「編輯」`locked` 只新增 **1 行** `gui.log`（M-3；N-f18b 為 2 行），整個項目共 3 行（N-f18b 為 4 行）；錯誤框關閉後焦點在清單項目 `locked` | ✔ |
| 158 | 回歸：(a) 點字 sha256 前 16 碼 `92b8d86cddb6ed6a`，與 N-f18b、N-f14b 相同；(b) 字典管理新增、重新命名、刪除、編輯、取消與 N-f18b 相同；(c) 寬度 30 | ✔ |

修正前的對照（N-f18b，新資料夾）：

- `auto154r2-f18b`（`item154.py`）：重新命名後焦點在「重新命名」按鈕；刪除唯一的使用者腳本後焦點在「匯入」按鈕。也就是說 wx 在停用有焦點的按鈕時會把焦點移到下一個可用的按鈕，焦點沒有停在被停用的按鈕上（review I-1 說「未實測」的部分），但也沒有回到清單。
- `auto154b-f18b`（`item154b.py`）：`no-processing.py` 是資料夾時清單沒有「不處理」（M-5）；刪除 `zeta` 後焦點在「刪除」按鈕；刪除程式外已刪除的 `gone` 出現「無法刪除腳本：[WinError 2] 系統找不到指定的檔案。: '<d>\script\gone.py'」，清單仍有 `gone`，`config.json` 仍是 `gone`（M-6）；刪除 `alpha` 後清單是空的、焦點在「匯入」；最後讀設定的下拉時因為清單沒有選取項目，腳本在讀取時出錯（`IndexError`，是測試腳本的錯誤，不是程式的）。
- `auto154b-f18c` 是第一次執行：選取 `zeta` 沒有生效（UIA 選取偶發失敗），刪到的是作用中的 `gone`，之後 `os.remove` 找不到檔案而停止；加上「選取後的列」輸出後在新資料夾 `auto154b2-f18c` 重跑，結果如上表。

## 仍需人工（使用者）

- [ ] **159**（NVDA，資料夾 `D:\dxtest\manual159-f18`，由 `auto/manual159.py` 準備：N-f18b 的 exe、待轉換文件 `alpha`、`script\upper.py`、語法錯誤的 `broken.py`、非 UTF-8 的 `cp950.py`）：啟動後開「轉譯 > 腳本管理...」，確認 NVDA 讀出對話框標題「腳本管理」、焦點所在列「不處理 可使用」；方向鍵到 `broken`、`cp950` 時讀出名稱與狀態（「格式不正確」「無法讀取」）；Tab 到原因欄時讀出「無法使用的原因：」與完整原因；選「不處理」時刪除、重新命名、編輯按鈕讀為不可用。再開「轉譯 > 設定」，確認讀出「文字處理腳本 下拉式方塊 不處理」。
- [ ] **160**（NVDA，同一資料夾）：在腳本管理選 `upper` 按「編輯」，確認標題讀為「upper」、編輯區讀為「Python 程式碼」多行編輯；輸入任意文字後按 Esc，確認「要放棄對腳本「upper」所做的變更嗎？」整句與兩個按鈕「放棄變更」「返回編輯」都被讀出；按「返回編輯」後焦點回到編輯區。
