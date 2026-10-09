# Windows 人工驗證清單（HANDOFF §4.2 剩餘項目）

本文件整理 HANDOFF §4.2 中無法自動執行、需要 packaged build、NVDA 或人工操作的全部項目。

- 編號沿用兩份 review 記錄的原清單（7、9–16 來自 `2026-10-08-03-refactor-p2/review_task.md`，18–21、23–29 來自 `2026-10-09-01-fix-data-loss/review_task.md`），方便結果對回。
- 另補一節 16b：P1-3 spec 的人工流程。它不在原總清單內，但同樣是未清的 Windows 驗證債。
- 細節來源：各任務 spec 的「Windows 驗證待辦／驗證債」段落（`docs/superpowers/specs/2026-10-0[89]-*_zh-TW.md`）。
- 已自動完成的項目（1–6、8、17、22，以及 7 的 source-run 部分）見同資料夾的 `results.md`。

**記錄方式**：每個步驟完成後勾選 `[x]`，並在「結果：」後填寫實際觀察。不符預期時，請記下畫面文字、截圖檔名或 log 內容。全部做完後交回，由 Claude 彙整進兩份 review 記錄。依 AGENTS.md，人工項目只有在你確認執行過之後才會標為完成。

---

## 0. 準備

### 0.1 兩個 packaged build

| 代號 | 版本 | 用途 |
| --- | --- | --- |
| **N** | 目前 `main`（`1db5767` 之後） | 受測版本 |
| **B** | 重構前基線 `6e5819f` | 「與 `main` 比對」「變更前後」的對照組 |

兩者的 `include/liblouis` submodule 相同（`2aa5f84b`，v3.37.0），建置輸入中只有 `vendor/nvda/liblouis/runtime/louis_helper.py` 不同（P2-7 移除 `basicConfig`）。因此 B 可以沿用 N 已建好的 DLL、tables 與 MathCAT assets，只需換回自己的 `louis_helper.py`。

在 repo root（`D:\workspace\DotExpress`）用 `cmd` 執行：

```bat
:: N
call client\.venv\Scripts\activate.bat
scripts\build-dotexpress.bat
mkdir D:\dxtest\N
copy client\dist\DotExpress.exe D:\dxtest\N\

:: B（6e5819f）
git worktree add ..\DotExpress-6e5819f 6e5819f
copy client\braille\liblouis.dll ..\DotExpress-6e5819f\client\braille\
robocopy client\braille\liblouis ..\DotExpress-6e5819f\client\braille\liblouis /E
robocopy client\mathcat\assets ..\DotExpress-6e5819f\client\mathcat\assets /E
copy ..\DotExpress-6e5819f\vendor\nvda\liblouis\runtime\louis_helper.py ..\DotExpress-6e5819f\client\braille\louis_helper.py
pushd ..\DotExpress-6e5819f
scripts\build-dotexpress.bat
popd
mkdir D:\dxtest\B
copy ..\DotExpress-6e5819f\client\dist\DotExpress.exe D:\dxtest\B\
```

- [x] N 建置成功，`D:\dxtest\N\DotExpress.exe` 存在　結果：（Claude 自動化，見 `auto-results.md`）PyInstaller 6.21.0，exit 0；48,731,302 bytes，sha256 `733168e8…54d0e5`；啟動冒煙測試正常
- [x] B 建置成功，`D:\dxtest\B\DotExpress.exe` 存在　結果：（Claude 自動化，見 `auto-results.md`）worktree `..\DotExpress-6e5819f`，exit 0；48,705,657 bytes，sha256 `790180f4…12d43b`；啟動冒煙測試正常

> packaged app 會把 `config.json`、`dictionary\`、`workspace\`、`log\`、`dual_view\` 建在 exe 旁邊。N 與 B 各用自己的資料夾，不要共用。**不要**直接拿 `client\dictionary\`（真實使用者資料）來測；需要真實字典時，一律**複製**到測試資料夾。

### 0.2 環境與工具

- [X] Windows 顯示語言為繁體中文（app 以 zh_TW 顯示）
- [X] NVDA 已啟動（11、12、13 需要）
- [ ] 即時防毒（Windows Defender 即時保護）維持開啟（21、28 需要）
- [X] 準備工具：7-Zip、Excel、記事本
- [X] 測試資料：
  - 混排文件 `docs\superpowers\history\2026-10-09-03-windows-verification\p25_doc.txt`
  - 一份含行內數學的長篇中英混排文件，例如匯入的 PDF 或 EPUB 章節，越長越好
  - 一份真實使用者字典的**複本**，需含 `General`（`braille` 欄可用 `@` 切分）、`Braille`（Unicode 點字）與 `Bopomofo` 類型的列。注意：不合法的注音列在按確定時會被刪除（F-W11），所以一定要用複本

### 0.3 常用指令

```bat
:: sha256
certutil -hashfile <檔案> SHA256
:: 逐位元組比對
fc /b <檔案1> <檔案2>
:: 檔案屬性
attrib +r <檔案>    & attrib -r <檔案>
attrib +h <檔案>    & attrib -h <檔案>
```

---

## A. P2-5 基線（packaged 部分）

### 7. 混排長文件的 BRL bytes

在 N 與 B 中各做一次，設定維持預設：Unicode 輸出、寬度 40、預設轉譯表、預設字典。

- [x] 匯入 `p25_doc.txt` 成為文件 → 執行轉換 → 匯出 BRL 為 `p25_unicode.brl`　結果：（Claude 自動化，見 `auto-results.md`）N、B 皆完成
- [x] 設定 > 輸出模式改為 ASCII → 再轉換 → 匯出 BRL 為 `p25_ascii.brl`　結果：（Claude 自動化，見 `auto-results.md`）N、B 皆完成（設定的「點字類型」改為 ASCII）
- [x] N 的 `p25_unicode.brl` sha256 是否等於 `365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c`（source-run 基線）　結果：（Claude 自動化，見 `auto-results.md`）相同
- [x] N 的 `p25_ascii.brl` sha256 是否等於 `95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64`　結果：（Claude 自動化，見 `auto-results.md`）相同
- [x] `fc /b` N vs B 的兩個 BRL：預期相同　結果：（Claude 自動化，見 `auto-results.md`）兩個 BRL 皆逐位元組相同

> 若 N 與 source-run 基線不同，但 N 與 B 相同，可能是匯入時調整了文字（例如去掉行尾空白）。請記錄下來，不要當成 regression。若 N 與 B 不同，才是 regression，請附上兩個檔案。

---

## B. P2 階段項目（9–16）

### 9. 路徑（P2-6）

**從可寫資料夾執行（N，`D:\dxtest\N`）**
- [ ] 第一次啟動後，exe 旁出現 `config.json`、`dictionary\`、`workspace\`、`log\`（`dual_view\` 可能要開過雙視才會出現）　結果：
- [ ] 修改一項設定、選取另一個字典、新增一份文件並輸入文字 → 關閉 → 重新啟動：三者都保留　結果：
- [ ] 開啟雙視檢視：`dual_view\` 內出現 HTML；結束 app 後 HTML 被清除　結果：
- [ ] client init 有回報：檢查 `log\init.log`。目前 server `/client/init` 回 404 屬於 server 端問題，只需記錄內容　結果：

**從唯讀資料夾執行（N 與 B 各一次）**
- [ ] 以系統管理員身分把 exe 複製到 `C:\Program Files\DotExpressTest\`，再以**一般權限**執行：出現本地化的啟動錯誤，內容含失敗路徑，且 runtime 未啟動。N 與 B 的訊息相同　結果：

**source run**
- [ ] `cd D:\workspace\DotExpress\client && python gui.py`：使用 `client\` 為 root（`client\config.json`、`client\log\`）　結果：
- [ ] `cd D:\ && python D:\workspace\DotExpress\client\gui.py`：同樣使用 `client\` 為 root，不在 `D:\` 建檔　結果：

### 10. 對話框（P2-1）

在 N 中逐一開啟並關閉下列對話框，確認都能正常開關、沒有錯誤：

- [ ] 新增字典項目／編輯字典項目　結果：
- [ ] 新增字典／重新命名字典　結果：
- [ ] 新增文件／重新命名文件　結果：
- [ ] 無效的工作區文件（觸發方式見 16b）　結果：
- [ ] 匯入問題（例如匯入一個名為 `CON.txt` 的檔案，或其他無法匯入的檔案）　結果：
- [ ] 字典項目編輯器（字典管理 → 編輯）　結果：
- [ ] 字典管理　結果：
- [ ] DotExpress 設定　結果：
- [ ] 文字處理　結果：
- [ ] 轉換中（長文件轉換時出現）　結果：
- [ ] 關於 DotExpress　結果：

**名稱驗證（N 與 B 比對訊息）**：在「新增字典」「重新命名字典」「新增文件」「重新命名文件」中分別輸入下列名稱，預期 zh_TW 訊息與 B 相同，且對話框保持開啟。

- [ ] 空白　結果：
- [ ] 33 個字元　結果：
- [ ] `CON`　結果：
- [ ] `Default`（僅字典的兩個對話框）　結果：

**單一實例與轉換中對話框**
- [ ] 設定開兩次 → 喚起既有視窗而不是開第二個；關閉後可以再開　結果：
- [ ] 文字處理開兩次 → 同上　結果：
- [ ] 長時間轉換時，「轉換中」對話框約 2 秒後出現，且按 Alt+F4 無法關閉　結果：

### 11. 字典編輯器（P2-2，N，zh_TW＋NVDA）

- [ ] 字典管理 → 編輯：開啟後第 1 列被選取，且 NVDA 讀出該列　結果：
- [ ] 在篩選框輸入文字：原本選取的項目仍保持選取　結果：
- [ ] 新增一個不符合目前篩選的項目：篩選被清除，且新項目被選取　結果：
- [ ] 編輯一列；在列上按 Enter 進入編輯　結果：
- [ ] 刪除一列：之後被選取的是原本同一個索引位置的列　結果：
- [ ] 新增重複項目：出現重複訊息　結果：
- [ ] 按確定會儲存；按取消會捨棄變更　結果：
- [ ] 在篩選框貼上、剪下、復原（Ctrl+V／Ctrl+X／Ctrl+Z）時，清單會跟著更新（D3）　結果：
- [ ] 篩選成「無結果」再清除：選取列行為正常，NVDA 沒有錯誤（`SetItemCount` 空結果分支）　結果：
- [ ] 把同一份字典複本分別放進 N 與 B 的 `dictionary\`，各開編輯器、不修改、按確定，再用 `fc /b` 比對兩份 CSV：預期相同（`\r\n`、無 BOM）　結果：

### 12. 設定面板（P2-3，N vs B，zh_TW＋NVDA）

- [ ] 開啟 DotExpress 設定，三個面板各截圖，並記錄 NVDA 讀出的選項清單（標籤、順序、初始選取）。N 與 B 相同　結果：
- [ ] 切換配色與點字字型：編輯區顏色與 SimBraille 字型跟著改變　結果：
- [ ] 英文／中文／日文轉譯表維持「未選擇」後按套用：沒有錯誤　結果：
- [ ] 把預設轉譯表清空後按套用：顯示驗證訊息，且焦點移到該列　結果：
- [ ] source run（`python gui.py`）與 N 的轉譯表名稱（已翻譯、已排序）相同（D6）　結果：

### 13. 字型同步（P2-4，N，NVDA）

- [ ] 開著 設定 > 檢視，在編輯區按 Ctrl+滾輪：字型大小 spin 跟著改變　結果：
- [ ] 在 spin 中手動輸入大小，再按 Ctrl+滾輪：spin 保留你輸入的值　結果：
- [ ] 按套用後再按 Ctrl+滾輪：spin 又會跟著改變　結果：
- [ ] 在「轉譯」分類開啟設定，按 Ctrl+滾輪後切到「檢視」：顯示新的大小　結果：
- [ ] 分別以確定、取消、關閉鈕、Esc 關閉設定，之後再按 Ctrl+滾輪：沒有錯誤　結果：
- [ ] 設定開著時按 Ctrl+滾輪，焦點留在編輯區　結果：
- [ ] （選做）觀察 `wx.SpinCtrl.SetValue` 是否會觸發 `EVT_TEXT`，程式兩種情況都能處理，只需記錄　結果：

### 14. 轉換與退出（P2-7、P1-1、P1-5、P1-6）

**source run**
- [ ] 在主控台執行 `python gui.py`，轉換一份含中、英、數學的文件，然後結束：沒有 traceback，主控台也不再出現帶時間戳的 `INFO` 行　結果：

**packaged，N vs B 逐位元組比對**
- [ ] 用 0.2 的長篇混排文件（含行內數學），分別以 `zh-tw.ctb` 和 `en-ueb-g2.ctb` 為預設表，各以 Unicode 與 ASCII 轉換並匯出 BRL：N 與 B 的 `fc /b` 相同　結果：
- [ ] 同一份長文件，N 的轉換時間明顯比 B 短（P1-5、P1-6），請記錄秒數　結果：
- [ ] 把真實使用者字典的複本放進 N 與 B 並選用它，再轉換同一份文件：BRL 相同（P1-6）　結果：
- [ ] 在兩次轉換之間，用字典管理修改字典：第二次轉換有套用修改（P1-6）　結果：
- [ ] 對含數學的文件開啟雙視檢視並匯出 HTML：N 與 B 相同，原文欄顯示 MathML（P1-5）　結果：

**語言環境變數（P1-1）**
- [ ] 用 `cmd` 啟動：`set TEXT2BRAILLE_LANG=` 後執行 exe，轉換並匯出；再 `set TEXT2BRAILLE_LANG=en` 後執行，轉換並匯出。兩種情況下 N 與 B 的輸出各自相同　結果：

**log 與退出**
- [ ] 以上轉換結束後，N 的 `log\translation.log` 沒有新的 fallback 警告，`log\math.log` 沒有新的錯誤　結果：
- [ ] 在數學轉換進行中結束 app：沒有當掉　結果：

### 15. 選單與匯出（P1-2、P1-4）

**選單截圖（N vs B，zh_TW）**：在「沒有文件」「有文件但沒有選取」「有選取」三種狀態下各截一次。
- [ ] 檔案選單　結果：
- [ ] 匯出子選單　結果：
- [ ] 匯出全部子選單　結果：
- [ ] 文件清單右鍵選單：在項目上開啟，以及沒有選取時用鍵盤選單鍵開啟　結果：

**匯出輸出（N vs B）**
- [ ] 每種格式各做一次單一匯出與匯出全部，比對 DEP zip 的成員與內容、BRL 位元組、HTML 位元組　結果：
- [ ] 在點字結果編輯區按 Ctrl+S：開啟 BRL 存檔對話框　結果：

**轉換流程（P1-4）**
- [ ] 短文字轉換不會出現「轉換中」；長文字約 2 秒後出現，完成時關閉。轉換期間檔案與轉譯選單、文件清單、原文編輯器皆停用　結果：
- [ ] 轉換錯誤（例如設定一個會失敗的點字表）：出現錯誤訊息，內容與 B 相同　結果：
- [ ] 長時間轉換中關閉主視窗：被擋下　結果：
- [ ] 對已轉換與尚未轉換（pending）的文件，分別匯出 DEP、BRL、HTML　結果：
- [ ] 匯出全部時混合 pending 與已轉換文件，目標資料夾已有同名檔案：出現覆寫詢問，「是」「否」兩種回答都測　結果：
- [ ] 匯出全部時有一個目標檔是唯讀：顯示部分失敗摘要。已知缺陷 4：摘要是英文　結果：
- [ ] 以上訊息除已知英文摘要外都是中文，且與 B 相同　結果：
- [ ] 已知缺陷 1、2（長時間轉換中按 Ctrl+Tab、Ctrl+S）的行為與 B 相同，只需記錄　結果：

### 16. 字典管理流程（P0-6 criterion 8）與本地化顯示（P0-5 criterion 10）

**字典管理（N vs B 的提示、訊息、清單選取一致）**
- [ ] 新增字典，以及新增重複名稱　結果：
- [ ] 重新命名作用中的字典、非作用中的字典　結果：
- [ ] 只改大小寫的重新命名：顯示重複名稱框，與 B 相同（已知行為，見 results.md F-W6）　結果：
- [ ] 刪除作用中的字典、非作用中的字典；刪除後在設定中確認退回到預設字典　結果：
- [ ] 匯入有效的字典檔、匯入沒有標頭的檔案　結果：
- [ ] 匯出字典、編輯字典　結果：

**本地化顯示（N）**
- [ ] 選單、對話框按鈕（確定、取消、套用、**關閉**）、字典項目類型、關於文字都是 zh_TW。「關閉」已在 W-3 補回翻譯　結果：
- [ ] 點字表名稱有翻譯（例如「日文 (六點漢字) 點字」）　結果：

### 16b. 文件流程（P1-3 spec，N vs B）

- [ ] 新增、重新命名、刪除、刪除全部、匯入（單一檔案、多個檔案、含重複）、Ctrl+Tab、關閉視窗。每一步比對工作區資料夾內容，以及清單、標題、編輯區的狀態　結果：
- [ ] 用 7-Zip 開著一個 `.dep`，執行刪除全部（觸發回滾）：先出現錯誤框，若有無效檔案再出現無效檔案對話框，最後清單重新載入　結果：
- [ ] 在 `workspace\` 放一個損毀的 `.dep`（例如把文字檔改名為 `bad.dep`）後啟動：出現「無效的工作區文件」對話框，兩個選項都測　結果：

---

## C. F-1：文件只改大小寫（18–21，N）

### 18. 基本流程
- [x] 新增文件 `Alpha`，輸入文字，重新命名為 `alpha`，重新啟動：文件與內文都在；在 `workspace\` 執行 `dir`，只看到 `alpha.dep`，沒有 `.tmp`　結果：（Claude 自動化，見 `auto-results.md`）通過
- [x] 新增文件 `ALPHA`：出現重複訊息，磁碟內容不變　結果：（Claude 自動化，見 `auto-results.md`）`文件「ALPHA」已存在。`，磁碟不變。名稱對話框重新顯示時按鈕變英文（F-W9）
- [x] 選另一份文件，重新命名為 `Alpha`：出現重複訊息，磁碟內容不變　結果：（Claude 自動化，見 `auto-results.md`）`文件「Alpha」已存在。`，磁碟不變

### 19. 檔案被鎖住
- [ ] 用 7-Zip 開著 `Alpha.dep`，同時把它重新命名為 `alpha`：出現 `Failed to save document: [WinError 32] ...`，清單仍顯示 `Alpha`；重新啟動後 `Alpha.dep` 內容不變，資料夾沒有 `.tmp`　結果：（Claude 自動化，見 `auto-results.md`）本機無 7-Zip，以程式模擬。只共用讀取：改名前的存檔就失敗 `[Errno 13] Permission denied`，不出現名稱對話框；共用讀寫：`[WinError 32]`，與預期相同。兩者資料不變、無 `.tmp`。**待人工：真實 7-Zip 屬於哪一種**

### 20. 唯讀屬性
- [x] `attrib +r Alpha.dep` 後重新命名為 `alpha`：預期成功，但可能留下唯讀的 `.Alpha.dep.<亂數>.tmp`。請記錄是否留下，以及檔案總管是否顯示它（M-7）　結果：（Claude 自動化，見 `auto-results.md`）改名前的存檔就失敗（`[Errno 13]`），M-7 路徑在 GUI 走不到；關閉也被擋（F-W10），B 相同

### 21. 即時防毒
- [x] Defender 即時保護開著，連續做 10 次只改大小寫的重新命名（`a` ↔ `A`）：記錄是否有暫時性失敗（M-4）　結果：（Claude 自動化，見 `auto-results.md`）10/10 成功，無 `.tmp`

---

## D. F-2：字典檔安全（23–29，N）

### 23. 寫出的位元組
- [x] 同一份字典複本分別放在 B 與 N，各按一次確定，用 `fc /b` 比對：預期相同（`\r\n`、無 BOM，驗證 `O_BINARY`）。可與 11 的最後一步合併　結果：（Claude 自動化，見 `auto-results.md`）B、N 相同（sha256 `ef319c21…`），CRLF、無 BOM

> 若 B 與 N 不同，再用 F-2 之前的 `aced6f8` 建一個 build 比對，以區分差異來自 F-2 還是更早的變更。

### 24. 帶 BOM 的字典
- [ ] 用 Excel 另存「CSV UTF-8」，用記事本另存「UTF-8 with BOM」，各做一份字典 → 匯入 → 字典管理顯示正確筆數 → 編輯器顯示各列 → 按確定 → 轉換時有使用該字典；確定後的檔案沒有 BOM　結果：（Claude 自動化，見 `auto-results.md`）以程式產生的 BOM＋CRLF／BOM＋LF 檔模擬，全部通過。**可選：用真的 Excel／記事本再做一次**

### 25. Excel 鎖檔
- [x] Excel 開著該字典時按確定：顯示 `儲存失敗：[WinError 32] ...`，列保留、檔案不變；關掉 Excel 再按確定則成功；字典資料夾沒有 `.default.csv.*.tmp`　結果：（Claude 自動化，見 `auto-results.md`）以只共用讀取的程序模擬：訊息是 `[WinError 5] 存取被拒`（不是 32），列保留、檔案不變、無 `.tmp`；解鎖後成功

### 26. 唯讀屬性
- [x] `attrib +r` 後按確定：顯示 `儲存失敗：[Errno 13] Permission denied: '<路徑>'`，沒有 `.tmp`；`attrib -r` 後再按確定成功，新檔案沒有唯讀屬性　結果：（Claude 自動化，見 `auto-results.md`）與預期相同

### 27. 隱藏屬性
- [x] `attrib +h` 後按確定：記錄是成功還是失敗、訊息內容（M-8）。不論哪種結果，原檔都要不變、沒有 `.tmp`；結束後執行 `attrib -h`　結果：（Claude 自動化，見 `auto-results.md`）成功，檔案被取代，隱藏屬性消失，無 `.tmp`

### 28. 即時防毒
- [x] Defender 即時保護開著，連續按確定 10 次：記錄是否有暫時性失敗，以及是否留下 `.tmp`（D8）　結果：（Claude 自動化，見 `auto-results.md`）0 次失敗，無 `.tmp`

### 29. ACL 拒寫、允許刪除
- [x] `icacls <字典.csv> /deny "%USERNAME%:(WD,AD,WEA,WA)"` 後按確定（不要用 `(W)`：它包含 SYNCHRONIZE，連讀取都會被拒，字典管理會打不開，見 F-W12、F-W13）：記錄結果是檔案被整個取代（判決變寬），還是失敗。只需記錄，不要求修改。結束後執行 `icacls <字典.csv> /remove:d "%USERNAME%"` 還原　結果：（Claude 自動化，見 `auto-results.md`）成功，檔案被整個取代，deny ACE 消失（判決變寬）；已還原

---

## E. 收尾

- [ ] 移除 B 的 worktree：`git worktree remove ..\DotExpress-6e5819f`（若有未追蹤的建置產物而失敗，加上 `--force`）
- [ ] 刪除 `D:\dxtest\` 與 `C:\Program Files\DotExpressTest\`
- [ ] 確認 29 的 ACL、20／26／27 的屬性都已還原
- [ ] 把這份勾選結果交回，由 Claude 彙整進 `results.md` 與兩份 review 記錄
