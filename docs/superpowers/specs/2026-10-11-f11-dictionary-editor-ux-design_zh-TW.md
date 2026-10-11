# 字典編輯器 UX（F-11）設計

## 目標

F-11 是 `task.md` 排序中的第 4 項「F-11 字典編輯器 UX」。本任務讓自訂字典編輯器（`DictionaryEntriesDialog`，標題「Custom Dictionary Manager」）及相關功能，照使用者在 2026-10-10 的決定運作。涵蓋：

- `task.md` #7：編輯器隱藏的列（F-4）看不到，也沒有任何提示；
- `task.md` #8：轉換仍使用這些列；
- `task.md` #9 與 P2-2 Q4：刪除會刪掉第一筆「相等」的列，而不是選取的那一列；
- P2-2 Q2：按「確定」一定會重寫檔案；
- P2-2 Q5：取消、Esc、視窗關閉鈕不詢問就丟掉修改；
- P2-2 Q6：新增／編輯時來源文字重複，輸入的內容會被丟掉；
- `task.md` #2，F-W6：在 Windows 上，字典改名只改大小寫（`alpha` 改為 `Alpha`）會被拒絕。這是測試套件中唯一失敗的測試；
- F-6 review M-4：匯入的來源檔被鎖住時，顯示原始的 `[Errno 13]`；
- F-6 review M-5：編輯器在原生對話框建立之後才讀檔，讀檔失敗會留下一個隱藏、半建好的對話框，而且任何失敗都被說成「無法讀取」。

使用者的決定（2026-10-10，`task.md` 第三節）。本文件不再重新提問：

- **U1（#7，F-11 第 1 項）。** 回復 F-4 之前的行為：按「確定」會刪除編輯器隱藏的列。刪除前先跳出確認框，列出每一列的列號、來源文字和原因。選「是」刪除並存檔；選「否」回到編輯器，不存檔。沒有隱藏列的字典不受影響。移除 F-4 D5（新增與隱藏列來源文字相同的詞條時拒絕）。
- **U2（P2-2 Q2，第 2 項）。**
  1. 沒修改就不寫檔。例外是 U1：有隱藏列時，按「確定」仍會跳出確認框。
  2. 有修改時，保留「去前後空白」和「不認得的類型改成 General」，讓檔案與編輯器顯示的一致。
  3. 保留多出的欄位，依原本表頭順序寫回。沒修改的列保留原值；新增的列額外欄位留空。
  4. BOM 照原檔。程式新建的字典仍無 BOM（列為後續項目）。`dictionary_entries_trace.json` 的 sha256 不得改變。
- **U3（P2-2 Q5，第 3 項）。**
  1. 取消、Esc、視窗關閉鈕：有未存修改時才詢問。文字類似「要放棄對字典所做的變更嗎？」，按鈕為「放棄變更」與「返回編輯」，預設「返回編輯」。「有沒有修改」與 U2 用同一套判斷；隱藏列不算未存修改。
  2. 刪除詞條不詢問。誤刪可以用「取消」，再按「放棄變更」挽回。
- **U4（P2-2 Q6，第 4 項），採用 A。** 重複檢查移進「新增／編輯字典詞條」對話框的「確定」，和格式檢查一致。顯示既有的「來源文字「X」已存在。」。對話框不關閉，輸入保留，焦點回到來源文字欄並全選。只檢查看得到的詞條。沒有新字串。
- **U5（其餘四項，使用者同意協調者的預設）。**
  1. F-W6：允許只改大小寫的改名。改名的是目前選用的字典時，同步更新 `config.json` 的選取名稱。沒有新字串。
  2. #9（P2-2 Q4）：刪除與取代以選取的那一筆為準（identity）。判斷重複時排除正在編輯的那一筆。沒有新字串。
  3. F-6 M-4：匯入讀取失敗的原因屬於 F-6 已分類的幾種時，改用 F-6 的友善說明。沒有新字串。
  4. F-6 M-5：先讀檔，再建立對話框。讀檔失敗沿用 F-6 的原因說明；非預期錯誤顯示一般失敗訊息，並寫入 `gui.log`。最多 1 個新字串。
- **U6（#8）。** 轉換也忽略編輯器隱藏的列，判斷與編輯器相同（`dictionaries/entries.py` 的 `_is_editable`）：來源文字去空白後為空的列（包括只有空白的列），以及注音內容無法解析的 `Bopomofo` 列。含這類列的既有字典，轉換結果會改變。#8 併入 F-11。

完成後：

- 開啟編輯器、沒修改就按「確定」，不寫任何東西。有隱藏列時，會先出現 D1 的確認框。
- 有修改後按「確定」，依序寫入顯示中的詞條。每一筆照現在的方式去空白（注音只去掉開頭的空白，D14）、正規化類型。檔案的表頭、多出的欄位和 BOM 都保留。
- 取消、Esc、關閉鈕只在有修改時詢問。預設答案是留在編輯器。
- 新增／編輯時來源文字重複，會在詞條對話框裡告知，輸入的內容保留。
- 刪除和編輯作用在選取的那一列，有兩列完全相同時也一樣。
- 轉換忽略編輯器隱藏的列。
- `alpha` 可以改名為 `Alpha`。若它是選用中的字典，`config.json` 一起更新。
- 匯入被鎖住的來源檔，顯示 F-6 的「無法開啟檔案」說明。
- 編輯器在對話框建立之前讀檔。

新增使用者可見字串：**11 個**（見「使用者可見字串」）。msgid 從 369 個變成 380 個。審查修正再新增字串 12（380 -> 381；「審查後的修正（F-11）」1）。使用者已於 2026-10-11 決定 O1：選 (b)（D14），見「待決問題」。使用者於 2026-10-11 決定審查 I-1：注音只去掉開頭的空白，原樣無法解析的注音列會被隱藏、不用於轉換（D14、「審查後的修正（F-11）」5）。

非目標：

- 在編輯器中顯示或修復隱藏列；
- 字典管理的筆數計入隱藏列（U1 維持筆數不變）；
- 新字典加上 BOM；
- 本任務以外的訊息用詞（F-12）；
- F-10（UEB 斷行、`$`）。

## 規劃後的修正（F-11，2026-10-11）

撰寫 plan（`docs/superpowers/plans/2026-10-11-f11-dictionary-editor-ux.md`）時，對照 `main` `1ce6ce5` 的程式碼重新確認：D1～D14、改前改後表與可到達性清單都成立，另有以下修正與補充。plan 的「Spec Corrections and Refinements」一節是同樣的內容（英文）。

1. **基準與數量。** 在 `1ce6ce5` 上，完整測試為 `Ran 1483`、`FAILED (errors=1, skipped=7)`（只有 F-W6），catalog 有 369 個 msgid。F-11 淨增 70 個測試：Task 1 後 `Ran 1485`，Task 2 後 `1490`，Task 3 後 `1508`，Task 4 後 `1512`，Task 5 後 `1516`，Task 6 後 `1522`，Task 7 後 `1526`，Task 8 後 `1539`，Task 9 後 `1551`，Task 10 後 `1553`（spec 原估約 60 個新測試、8 個翻轉或移除）。最終結果是 `OK (skipped=6)`，不是 `skipped=7`：`test_dictionary_presenter.PresenterRenameTest.test_rename_case_only_change_renames_file` 在不分大小寫的檔案系統上會自己跳過（理由「只改大小寫的改名被當成重複」就是 F-W6）；Task 1 拿掉這個跳過，所以它在 Windows 上也會執行。msgid 從 369 變成 380：字串 11 在 Task 7，字串 1～7 在 Task 8，字串 8～10 在 Task 9；D14 不新增字串（已重新確認）。驗收條件 2 的模組組合（spec 的十個模組）從 `Ran 482`、`FAILED (errors=1, skipped=1)` 變成 `Ran 549`、`OK`。
2. **遷移順序。** 各 task 依序為：1 D10，2 D11，3 D5 與 D6，4 D9，5 D2 與 D8，6 D14，7 D12（字串 11），8 D1（字串 1～7），9 D3、D4 與 D7（字串 8～10），10 D13；每個 commit 沿用 spec 的標題。理由：(a) D1 在 D4 之前。若只有 D4，golden trace 中最後沒有淨修改的序列按「確定」時不會寫檔，記錄下來的 CSV 就要到 D1 之後才會出現；D1 的對話框讓 trace 的每次「確定」都寫檔（`TRACE_CSV` 有兩列隱藏列），所以每個 commit 中 trace 都通過。(b) 只有新增字串的三個 task 重新產生 catalog，而 Task 9 是最後一個會移動 msgid 上方程式行的 task（Task 10 不改任何含 msgid 的檔案），所以最後沒有過時的 `#:` 參照。(c) D14 在 D13 之前，轉換的規則與其一致性測試從一開始就包含一聲結尾的情況。(d) 字串 7「`&Back to Editing`」最先由 D1 的對話框使用，所以放在 Task 8。
3. **`confirm_box` 使用 wx 的一般對話框（O12）。** 規劃時實測（wx 4.2.5、Windows 11 繁中，由 wx 對話框的「確定」處理函式顯示訊息框，與編輯器相同）：使用自訂按鈕文字的原生 task dialog（`wx.MessageDialog`、`wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING`、`SetOKCancelLabels`）按 **Alt+F4** 會傳回 `wx.ID_OK`；Esc、Enter 與關閉鈕傳回 `wx.ID_CANCEL`。只自訂「確定」的文字時相同；使用 `SetYesNoLabels` 時 Alt+F4 傳回 `wx.ID_YES`；使用標準文字時傳回 `wx.ID_CANCEL`。spec 的探針 2 是在沒有執行中的 modal 對話框時，於 frame 上顯示訊息框；那種情況仍傳回 `wx.ID_CANCEL`（規劃時重跑過）。若用 task dialog，在 D1 的對話框按 Alt+F4 會移除隱藏列，在 D7 的對話框按 Alt+F4 會放棄變更。改用 `wx.GenericMessageDialog`（相同樣式與按鈕文字）時，Esc、Alt+F4、Enter 與關閉鈕都傳回 `wx.ID_CANCEL`；Alt+S、Alt+B、Alt+D 會按下對應按鈕；焦點一開始在「返回編輯(B)」（packaged build 的 GUI 項目 95、99、35）。對使用者而言，這兩個對話框是傳統對話框（警告圖示、訊息每一行一段文字、沒有粗體的主要指示），而不是 task dialog；NVDA 是否完整讀出由手動項目 107 確認。其他所有訊息框使用的 `message_box`（task dialog）不變。使用者於 2026-10-11 決定：使用傳統對話框，即目前的做法。使用者的硬性要求是：Esc、Alt+F4 與關閉鈕絕不能觸發「移除並儲存」或「放棄變更」；它們是否等於「返回編輯」本身不是要求。（F-5 的關閉對話框也有自訂按鈕文字；它是從 frame 顯示，不是從 modal 對話框，所以這項實測不適用；本任務未檢查。）
4. **F-W6 測試的最後一個斷言** `assertFalse((directory / "alpha.csv").exists())` 在不分大小寫的檔案系統上不可能成立：改名後檔案仍可用 `alpha.csv` 找到。Task 1 改為檢查資料夾清單 `["Alpha.csv", "default.csv"]`，在任何檔案系統上都成立。
5. **D11：先讀來源，再寫入副本。** `import_dictionary` 在同一個 `try` 內檢查並讀取來源（`validate_dictionary_csv`，然後 `Path.read_bytes`），再用讀到的位元組寫入副本，因此不必深入 `write_bytes_atomically`，就能分辨來源的 `PermissionError` 與寫入副本時的錯誤。字典是小的 CSV 檔，複製的位元組相同。
6. **D13：編輯器顯示的注音列才用於轉換，轉換的就是編輯器顯示的注音（O13）。使用者於 2026-10-11 決定（審查 I-1）。** `from_paths` 對 `target.lstrip()`（去掉開頭空白後的注音）解析一次；拋出例外就略過該列。不再有 fallback：無法解析的注音不會再以原始符號轉換，也不會補上聲調空白。這就是編輯器的規則（`canonical_bopomofo`，D14），用的是同一個解析器，所以兩者完全一致；`EditorParityTest` 檢查 31 列，另有一個測試確認解析器只呼叫一次、解析的是去掉開頭空白後的注音。用真正的解析器時，能解析的原始值不會以空白開頭（開頭的空白會被當成聲調，其他空白字元會被拒絕），所以以前能解析的列轉換結果完全不變。改變的是：結尾一聲卻沒有空白的列（`抹,ㄇㄚ,Bopomofo`）或最後一個音節後面還有空白的列（`ㄇㄚ  `、`ㄉㄨˋㄗ˙ `），以前經由 fallback 成為規則，現在被忽略（編輯器隱藏、按「確定」時列出）；開頭有空白的列（` ㄇㄚ `）以前經由 fallback 轉換、開頭的空白也被當成符號（`⠄⠍⠜⠄`），現在依編輯器顯示的注音轉換（`⠍⠜⠄`），也就是任何一次存檔之後的結果。這取代 plan 的預設（先解析原始值，編輯器會顯示的列保留 fallback）；在那個預設下，這種列的點字會在一次無關的修改存檔後改變（審查 I-1）。
7. **trace 重播有兩處調整，不是一處。** 除了回答 D1 的對話框並把它的記錄從「確定」那一步移除（D1），重播也會在開啟那一步的記錄中有編輯器新增的「取消」按鈕 `Bind` 時把它移除（D7）；完整的建構記錄由 `test_construction_log_is_exact` 固定。假的詞條對話框遇到重複時維持開啟，接著取下一個預先排定的回答，沒有就取消，所以記錄下來的 `MessageBox` 事件不變。`dictionary_entries_trace.json` 不變（`f493da52...`）。
8. **D9：刪除後選取第一個相等的列。** 有兩列完全相同時，刪除第二列後選取第一列：這是 golden trace 記錄的相等比對規則（O10）。保留相同來源文字的編輯與取代則以 identity 選取。
9. **D12 在主視窗中：** `gui.py` 匯入 `DictionaryEntryListModel`，載入模型後以 `model=` 傳入；非預期錯誤寫入 `gui.py` 的模組 logger `dotexpress.gui`（`gui.log`）。建構函式在原生 `__init__` 之後才設定路徑與模型；建立過程失敗時呼叫 `Destroy` 再重新拋出。
10. **字串。** 重複訊息只有一個呼叫點（`dialog.py` 的 `show_duplicate_source_text`），詞條對話框與編輯器的後備檢查共用，所以 D8 不新增 msgid。`msgmerge` 猜錯兩個 fuzzy 翻譯：`Failed to open the dictionary editor: {error}` <- `無法刪除字典：{error}`（Task 7）與 `Do you want to discard the changes you made to dictionary "{name}"?` <- `要刪除字典「{name}」嗎？`（Task 9）；填寫 msgstr 的步驟會取代兩者並移除 fuzzy 標記。
11. **spec 沒有列出的測試：** `test_wx_call_sites`（唯一的 `GenericMessageDialog` 是 `confirm_box`）、`test_message_box`（`confirm_box`，兩個測試）、`test_dialog_validation`（D8 三個；D14 兩個）、轉換的 golden 案例（翻轉一個，新增三個）、`test_dictionary_entries` 的往返測試（隱藏列不再是規則）、presenter 的只改大小寫改名（取消跳過）。D14 的驗證測試收集錯誤訊息，而不是讓解析器的錯誤往外拋：`text.zhuyin.ParseError` 是 frozen dataclass，unittest 無法替它附加 traceback（測試會在沒有 `Ran` 行的情況下中止）。
12. **Windows 項目：** 95～106 沿用 spec 的編號，手動 NVDA 項目為 107；「改前」是 `D:\dxtest\N-f9b`（F-9 審查修正後，程式碼等於 `1ce6ce5`）；新 build 放在 `D:\dxtest\N-f11`。修正：項目 98 原本預期「`bom_lf.csv` 仍沒有 BOM」，但 `bom_lf.csv` 有 BOM（且是 LF 換行）：編輯後保留 BOM、改為 CRLF。項目 106 改用與 liblouis 預設讀音不同的注音，讓輸出能看出兩條規則都有用到：`tone1.csv` 中的 `中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo`，以及新增 `抹`／`ㄇㄚ`（一聲讀音，輸入時沒有空白）。使用者決定審查 I-1（2026-10-11）之後，項目 106 改用 `auto/item106.py`：`tone1.csv` 含 `中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo` 與 `抹,ㄇㄚ,Bopomofo`（沒有聲調空白），新增先用 `末`／`ㄇㄚ`（被拒絕），再用 `末`／`ㄇㄚ `（被接受）；預期結果見下面表格中的項目 106。項目 105 在「匯入」的檔案對話框關閉後才以不共用方式鎖住檔案：Windows 的檔案對話框不接受沒有人能共用的檔案，實際使用時則是其他程式在輸入名稱時取得檔案。項目 23～29 改用新腳本 `rerun23.py`（23、24）與 `rerun25.py`（25～29），先編輯一列讓「確定」會寫檔；項目 35 使用新的 `item35.py`；項目 44 與 47 執行 F-6 的 `item42.py` 與 `item47.py`，不修改（兩個 build 的記錄除了項目 47 的 `gui.log` 那行中的資料夾名稱之外完全相同）。
13. **採用 D14（O1 選 (b)，使用者於 2026-10-11 決定）。** 由 Task 6 實作；GUI 項目 106 列入範圍。

## 審查後的修正（F-11，2026-10-11）

審查（`docs/superpowers/history/2026-10-11-01-f11-dictionary-editor-ux/review_task.md`）發現以下各點；本 spec 描述它們的段落已配合更新。

1. **表頭無法辨識的字典絕不會被清空（審查 M-1）。** 表頭沒有 `text` 欄（Excel 可能寫成 `Text,Braille,Type`，或 `source,braille,type`），或第一行是空行時，每一列都會被讀成沒有來源文字，所以 D1 確認框把它們全部列為隱藏列，「移除並儲存」只寫出表頭、沒有任何資料列。現在當表頭沒有 `text` 欄且至少有一列被隱藏時，`LoadedDictionary.header_recognized` 為 False；模型從讀檔結果取得這個值，為 False 時 `save` 不寫入並拋出 `ValueError`。「確定」先檢查它：顯示字串 12 `無法儲存字典「{name}」：無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。`（標題「錯誤」，`wx.OK | wx.ICON_ERROR`；用語沿用匯入的「匯入的檔案必須包含 text、braille 與 type 表頭。」），不寫入，編輯器保持開啟並還原焦點，不論有沒有修改；不顯示 D1 確認框。「取消」照舊（有修改時顯示 D7 確認框）。開啟編輯器不變（清單是空的）。沒有 `text` 欄、也沒有資料列的表頭不會遺失任何東西，所以「確定」照舊儲存（補上必要欄位）。這是最簡單又安全的做法：「確定」中一個檢查、模型中一個防護，不改讀檔的分類（它與 `DictReader` 和轉換一致），也不改開啟編輯器的流程。不採用：拒絕開啟編輯器（要在 frame 與字典管理新增路徑，而轉換本來就拒絕這種檔案），以及在 D1 確認框加一行表頭說明（仍會提議移除每一列）。msgid 380 -> 381。使用者已接受（2026-10-11）。
2. **補上的必要欄位不再覆蓋超出表頭的欄位（審查 M-5）。** 表頭缺少 `text`、`braille`、`type` 其中之一時，寫檔把補上的欄位放在表頭的欄位之後、超出表頭的欄位之前，超出的欄位往右移：`text,braille`／`a,⠁,Bopomofo,extra` 寫成 `text,braille,type`／`a,⠁,General,Bopomofo,extra`（以前是 `a,⠁,General,extra`）。沒有表頭（預設 layout）時，記錄的前幾個欄位仍是 `text`、`braille`、`type`。使用者已接受（2026-10-11）。
3. **D1、D7、「各檔案的設計」、「無障礙」與「風險」也改為描述 `wx.GenericMessageDialog`（審查 M-3）**，與「規劃後的修正（F-11）」3 一致；這些段落原本描述的是 `wx.MessageDialog` 與 task dialog。
4. **審查修正新增的測試（審查 M-2 與各項修正）：** 隱藏列說明代入去空白後的值、全空欄位的記錄（`,,`）是有行號的隱藏列、焦點在對話框出現前讀取（測試替身的對話框現在會像真的對話框一樣拿走焦點）、寫檔補上的欄位（M-5）、讀檔、模型與編輯器的表頭檢查，以及字串 12（M-1）。`Ran 1553` -> `1564`，`OK (skipped=6)`。
5. **審查 I-1（一聲結尾卻沒有聲調空白的列顯示為 `ㄇㄚ `，但在一次無關的存檔之前轉換時沒有一聲的點）。使用者於 2026-10-11 決定。** 注音欄只去掉開頭的空白；結尾的空白完全保留檔案中或輸入時的樣子，任何地方都不再補上聲調空白。原樣無法解析的注音（缺少聲調空白、結尾有兩個空白、結尾是 tab）是不合法的：編輯器隱藏它，「確定」時在 D1 確認框列出，轉換忽略它，編輯器與轉換用同一條規則。`ㄇㄚ ` 與 `ㄓㄨㄥˋㄒㄧㄣ ` 仍然合法：會顯示、可以編輯、存檔時位元組不變、轉換與以前相同。詞條對話框不再去掉注音欄結尾的空白，所以沒打空白的 `ㄇㄚ` 會出現原有的「請輸入有效的注音序列。」（沒有新字串）。D13、D14、「規劃後的修正（F-11）」6（O13）、O1、風險、「各檔案的設計」、測試計畫 A6 與 Windows 項目 106 都已更新。catalog 只有 `dialog.py` 的參照行號改變。測試：`Ran 1564` -> `1567`，`OK (skipped=6)`；golden 案例「first-tone Bopomofo rows convert as before」保留有空白的列、去掉沒有空白的列，另新增兩個案例（最後一個音節後面還有空白；開頭有空白）。`translation_golden.json`、`translation_liblouis_golden.json` 與 `dictionary_entries_trace.json` 不變：它們都沒有結果會改變的注音列。

## 現況（2026-10-11 在 `main` `1ce6ce5`、worktree `D:\workspace\DotExpress-f11`、`HEAD:client` `a64da653` 上確認）

`$PY` 是 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`。協調者在 worktree 的 `client\` 量到的基準：`$PY -B -X utf8 -m unittest discover -s tests` 為 `Ran 1483`、`FAILED (errors=1, skipped=7)`。唯一的 error 是 F-W6 的 `test_case_only_rename_still_renames`。catalog 有 369 個 msgid。以下探針在 session scratchpad 的 `client/` 副本（`...\scratchpad\f11spec\`）上執行，沒有 commit。

### 程式位置（`1ce6ce5`）

| 部分 | 位置 | 現況 |
| --- | --- | --- |
| 讀檔 | `dictionaries/entries.py:68-92` `load_dictionary_rows` | 以 `utf-8-sig` 開檔，用 `csv.DictReader` 讀。去掉文字與點字的前後空白，並正規化類型。`_is_editable`（`:95-104`）不通過的列，帶著原始欄位變成 `PreservedDictionaryRow`（`:30-42`）。不記錄表頭、BOM、多出的欄位，也不記錄行號。 |
| 寫檔 | `entries.py:112-128` `save_dictionary_entries` | 固定表頭 `text,braille,type`、UTF-8 **不含 BOM**、`\r\n`、最少引號；多出的欄位和超出表頭的欄位**被丟掉**。保留列依欄位原樣寫回（F-4 D3）。 |
| 模型 | `dictionaries/entry_list_model.py` | `source_text_exists`（`:119-127`）掃描**每一列，包括保留列**（F-4 D5）。`add`（`:135-143`）拋出 `DuplicateEntryError`。`replace`（`:145-152`）依 identity 取代。`remove`（`:154-158`）是 `self._rows.remove(entry)`，刪的是第一筆**相等**的列（Q4）。`_selection_after`（`:171-180`）依相等還原選取。`save`（`:70-72`）寫出每一列。 |
| 編輯器 | `dialog.py:341-508` `DictionaryEntriesDialog` | `super().__init__`（`:349`）在 `DictionaryEntryListModel.load`（`:352`）**之前**執行（Q8、M-5）。只有「確定」有 handler（`:399-401`），所以取消、Esc、關閉鈕會直接關閉（Q5）。`_on_add_clicked`／`_edit_selected`（`:451-480`）先關閉詞條對話框，之後才檢查重複，輸入因此遺失（Q6）。`_on_remove_clicked`（`:482-486`）不詢問。`_on_ok`（`:502-508`）**一定存檔**（Q2）。存檔錯誤顯示 `Failed to save: {error}`，編輯器保持開啟。 |
| 詞條對話框 | `dialog.py:70-164` `AddSymbolDialog` | `get_braille` 會去空白（`:113-114`）。`_on_ok`（`:144-164`）只檢查格式（`validate_dictionary_entry`，`entries.py:54-65`），訊息標題是 `Info`。 |
| 主視窗 | `gui.py:1029-1051` `on_open_dictionary_management` | 攔住建構子。任何例外都以 `log_dictionary_read_error` 記錄，並顯示 `describe_unreadable_dictionary`（F-6 D6）。半建好的對話框留在主視窗底下，隱藏著（F-6 M-5）。 |
| 訊息框 | `ui/message_box.py:15-33` | `message_box` 會把按鈕強制設成 `OK`／`Cancel`，無法自訂按鈕文字。F-5 的關閉對話框（`gui.py:474-490`）直接使用 `wx.MessageDialog` 搭配 `SetYesNoCancelLabels`。 |
| 改名 | `dictionaries/manager.py:100-110` `rename_dictionary` | `if destination_path.exists(): raise FileExistsError`（`:107-108`）。在 Windows 上，`alpha.csv` 存在時 `Alpha.csv` 也「存在」，所以只改大小寫會被拒絕（F-W6）。`name_prompt.py:33-42` 會放行只改大小寫的情況。presenter 的改名（`dictionaries/presenter.py:137-165`）已經透過 `plan_dictionary_state_after_rename`（`translation/dictionary_state.py:29-39`）更新選用名稱，所以改名一旦成功，`config.json` 就會跟著更新。 |
| 匯入 | `presenter.py:167-190`；`manager.py:87-97`、`validate_dictionary_csv` `:59-73` | `(UnicodeDecodeError, csv.Error)` 使用 F-6 的原因說明（`:178-181`）。其他 `OSError` 一律顯示 `Failed to import dictionary: {error}`，附原始錯誤（`:185-187`），不論是讀來源檔還是寫入副本時發生（M-4）。 |
| 原因說明 | `dictionaries/read_problems.py:29-57` | `PermissionError` 對應 CANNOT_OPEN：「無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限……」 |
| 筆數 | `read_problems.py:83-89`、`dialog.py:610-623` | `len(load_dictionary_entries(path))`：只算看得到的詞條。 |
| 轉換 | `conversion/text/dictionary_rules.py:169-200` `LoadedDictionaryRules.from_paths` | 只有**原始**文字是 `""` 時才跳過（`:181-182`）。只有空白的文字也是一條規則。`processing` 拋出例外的 `Bopomofo` 列，會改用注音 trie 掃描原始字串（`:185-194`），所以仍是一條規則。同一來源有兩條規則時，第一條生效（`_build_trie`，`:41-43`）。`processing` 由外部注入，正式環境是 `normalize_zhuyin_sequence`（`conversion/text/pipeline.py:52`）。這個模組沒有 import `dictionaries`。 |

`tests/test_dictionary_entries_dialog.py` 中固定現況缺陷的測試，都標有 `# KNOWN BUG (P2-2 spec, Qn)`：

- Q8：`test_invalid_utf8_raises_from_the_constructor_after_the_native_dialog`（`:840`）；
- Q5：`test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized`（`:862`）與 `test_delete_has_no_confirmation_and_selects_the_row_now_at_that_index`（`:1254`）；
- Q6：`test_duplicate_of_a_hidden_entry_is_rejected_with_the_exact_message`（`:1031`）與 `test_duplicate_is_rejected_with_the_exact_message_and_nothing_changes`（`:1186`）；
- Q4：`test_identical_rows_edit_replaces_the_selected_row_but_cannot_keep_its_text`（`:1206`）與 `test_identical_rows_delete_removes_the_first_equal_row`（`:1304`）；
- Q2：`test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form`（`:1348`）。

另有測試沒修改就按「確定」並預期寫檔，例如 `test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom`（`:852`）與 `test_ok_saves_the_full_list_in_order_and_closes`（`:1333`），會隨 D4、D5 改變。

F-4 的 D5 由 `tests/test_dictionary_entry_list_model.py` 的 `test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate`、`test_a_preserved_row_blocks_only_its_raw_unstripped_source_text` 固定。F-W6 是 `tests/test_dictionary_name_prompt.py:82`。轉換的 golden 案例「Bopomofo row with a processing that raises」（`tests/test_conversion_text_dictionary_rules.py`）預期 fallback 規則。

### 探針

1. **Golden trace 與 identity。** `DictionaryEntriesTraceTest` 在 `TRACE_CSV` 上重播 40 組錄製的操作序列。`TRACE_CSV` 有兩列相同的 `a,⠁,General`。fixture `dictionary_entries_trace.json`（sha256 `f493da52...`）不得改變。
   - 把 `remove` 改成 identity：重播通過。
   - 把選取改成依 identity 還原：有 4 組序列（seed 23、29、33、37）在刪除步驟不同，選取跑到索引 0，而不是剩下的那一列分身。
   - 錄製的編輯中，沒有任何一次是保留有分身的列的文字（0 次）。所以 D9 對 Q4 的修改不影響 trace。
2. **本機的 task dialog**（wx 4.2.5、繁中 Windows）。
   - `wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING` 加上 `SetOKCancelLabels`：顯示兩個自訂按鈕文字。鍵盤焦點在 Cancel 按鈕上，對話框有關閉鈕。Esc、Enter、Alt+F4 都回傳 `wx.ID_CANCEL`。
   - `wx.YES_NO | wx.NO_DEFAULT`（系統按鈕 是(Y)／否(N)）：Esc 與 Alt+F4 **沒有作用**，對話框維持開啟，也沒有關閉鈕。Enter 回傳 `wx.ID_NO`。
3. **只改大小寫的改名。** `rename_dictionary(d, "alpha", "Alpha")` 拋出 `FileExistsError`。`os.path.samefile(alpha.csv, Alpha.csv)` 為 `True`；`Path.rename` 把 `alpha.csv` 改為 `Alpha.csv` 可行，清單顯示 `Alpha.csv`。
4. **最後一個音節是一聲。** `normalize_zhuyin_sequence` 接受 `"ㄇㄚ "`，但拒絕 `"ㄇㄚ"`、`"ㄓㄨㄥ ㄒㄧㄣ"`、`"ㄇㄚˉ"`。它的規則是「若是一聲，必須有空白」。讀檔時會先去掉點字欄的空白再檢查，所以最後一個音節是一聲的 Bopomofo 列，編輯器全都會**隱藏**（例如 `中心,ㄓㄨㄥ ㄒㄧㄣ ,Bopomofo`）。`AddSymbolDialog.get_braille` 也會去空白，所以這種注音根本無法輸入。轉換用的是原始值，對轉換而言這列是合法的。F-4 已在其現況一節提到這點。見 O1。
5. **csv 記錄的行號。** 用 `csv.reader` 時，一筆記錄從前一筆的 `line_num + 1` 開始。空行本身是一筆 `[]` 記錄；有引號的欄位可以跨行。`csv.DictReader` 以第一筆記錄為表頭，即使是空的也一樣。它跳過 `[]` 記錄，缺少的欄位給 `None`，超出表頭的欄位放在鍵 `None` 底下。

## 決定

**D1. 隱藏列：按「確定」時確認，然後移除（U1）。**

- 模型照現在的方式保留隱藏列（`PreservedDictionaryRow`），讓編輯器可以列出它們。每一列另外記錄它的記錄從檔案第幾行開始，表頭算第 1 行（探針 5）。這就是記事本顯示的行號。除非有欄位跨行，Excel 顯示的列號也相同。
- 按「確定」時，只要模型中有隱藏列，編輯器就顯示確認框（`wx.GenericMessageDialog`，`wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING`，按鈕文字以 `SetOKCancelLabels` 設定；「規劃後的修正（F-11）」3）：
  - 標題 `Remove Rows That Cannot Be Shown`；
  - 訊息：依檔案順序，每個隱藏列一行，前面有一句引言，最後是一個問句（字串 1～5）；
  - 每一列是以下其中一種：
    - 去空白後文字為空：`Row {line}: no source text`；
    - 其他情況：`Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid`。代入的是去空白後的文字和注音。
  - 最多列出 **10** 列。超過時，接一行 `Other rows not listed: {count}`（O3）。
  - OK 按鈕文字是 `Remove and &Save`，Cancel 是 `&Back to Editing`。Cancel 是預設按鈕，焦點也在它上面；Esc、Enter、Alt+F4 和關閉鈕也等於「返回編輯」（一般對話框對這四者都傳回 `wx.ID_CANCEL`；使用自訂按鈕文字的 task dialog 從編輯器顯示時，會把 Alt+F4 當成 OK）。
- **移除並儲存：** 只寫入看得到的詞條（D5）；成功後以 `wx.ID_OK` 關閉。**返回編輯：** 不寫入，編輯器保持開啟，焦點回到原處（D7）。
- 有隱藏列時，即使沒有其他修改也會出現確認框（U2.1）。沒有隱藏列時，「確定」依 D4 處理。
- 「移除並儲存」後寫檔失敗，會出現既有的 `Failed to save: {error}`，編輯器保持開啟。隱藏列仍在模型中，所以下次按「確定」會再問一次（O4）。
- 表頭沒有 `text` 欄且有隱藏列時，這些列是因為表頭才被隱藏，不是因為它們是空的：「確定」改為顯示字串 12，不顯示確認框，也不寫入（「審查後的修正（F-11）」1）。
- 字典管理的筆數仍只算看得到的詞條（U1「字典管理的筆數不變」）。匯入、匯出、改名、刪除仍保留每一列，因為它們只是複製、搬移或刪除位元組。
- 為什麼用訊息框而不是清單對話框：訊息框一出現就顯示全文（一般對話框把訊息的每一行做成一段文字；NVDA 是否全部讀出由手動項目 107 確認）。它也有確認框應有的鍵盤行為（預設按鈕、Esc）。列數上限讓隱藏列很多時，確認框仍能放進螢幕。

**D2. 重複檢查只看看得到的詞條（U1、U4）。**

- `source_text_exists` 忽略 `PreservedDictionaryRow`。被篩選藏起來的詞條仍然算，與現在相同。
- 移除 F-4 D5 及其兩個測試。來源文字與隱藏列相同的詞條會被接受。按「確定」時，D1 會列出那個隱藏列，使用者看得到新詞條取代的是哪一列。
- 比對方式不變：以去空白後的文字精確比對（區分大小寫）。

**D3. 「有修改」是比對依序排列的詞條值（U2.1、U3.1）。**

- `DictionaryEntryListModel` 在載入時記下所有詞條，並新增 `has_changes() -> bool`。目前的詞條依序與載入時的詞條，以值比較（`DictionaryEntry` 的 dataclass 相等：text、braille、type）不同時，為 `True`。
- 隱藏列一律不算。
- 新增後又刪除同一筆，不算修改；編輯後每個值都沒變，也不算。刪掉一列再把它加回最後面算修改，因為順序對轉換有意義（同一來源的第一條規則生效）。
- 篩選不算修改。
- 快照存的是複本，所以之後若就地修改詞條物件（目前沒有這種程式），也不會讓修改被忽略。
- 不採用：每次新增、取代、刪除都設一個「已修改」旗標。那樣在新增又刪除之後，取消會詢問、確定會寫檔，但使用者看到的是什麼都沒變。

**D4. 「確定」只在需要時寫檔（U2）。**

`_on_ok` 依序：

0. 表頭無法辨識：顯示字串 12，不寫入，編輯器保持開啟（「審查後的修正（F-11）」1）。
1. 有隱藏列：依 D1，由使用者的回答決定。
2. 否則，若 `has_changes()`：寫檔（D5）。發生錯誤時顯示既有訊息並保持開啟；成功則 `event.Skip()`。
3. 否則：不寫檔，直接 `event.Skip()`。檔案的位元組與修改時間都不變。

檔案不存在（字典管理列出之後被刪掉）時，載入結果是空的。沒修改時，「確定」不再建立它；有修改時照舊建立。

**D5. 寫檔時保留檔案格式（U2.2～U2.4）。**

`save_dictionary_entries(path, entries, layout)` 只寫詞條；D1 之後，隱藏列永遠不會寫出。layout 來自讀檔（D6）。

- **BOM：** 讀進來的檔案開頭有 `EF BB BF` 才寫 BOM，否則不寫。DotExpress 自己建立的檔案（`create_dictionary`、`ensure_default_dictionary`）仍然沒有 BOM。
- **表頭：** 照讀到的表頭記錄與順序。`text`、`braille`、`type` 中缺少的，依這個順序補在最後。每一列中，補上的欄位放在表頭的欄位之後、超出表頭的欄位之前，超出的欄位往右移（「審查後的修正（F-11）」2）。沒有表頭記錄的空檔案，寫成 `text,braille,type`。
- **每一列：** 以該記錄讀到的欄位為起點：
  - 沒修改或編輯過的列，保留每一個欄位，包括多出的欄位、超出表頭的欄位、重複名稱的欄位；
  - 新增的列從空的開始；
  - 補 `""` 到表頭長度；
  - 再把 `text`、`braille`、`type` 欄設成詞條的值（去空白、類型已正規化；U2.2）。欄位名稱重複時，值寫到 `DictReader` 讀取的位置，也就是最後一個；另一個位置保留原值。
- 編輯過的列保留它多出的欄位：它是同一列，只是值變了（O5）。
- **與現在相同：** UTF-8、`\r\n` 換行、最少引號、原子取代（`write_text_atomically`）、空行丟掉。

以 `TRACE_CSV` 而言（無 BOM、表頭 `text,braille,type`、沒有多出的欄位），寫出的位元組與 F-4 之前的寫檔完全相同，所以 trace 預期的 CSV 仍然成立（測試計畫 C）。

**D6. 讀檔保留格式與記錄位置；分類方式不變。**

- `load_dictionary_rows` 改成包裝新的 `load_dictionary_file(path) -> LoadedDictionary(rows, layout)`。分類（`_is_editable`）和每一列的值，與現在 `DictReader` 給的完全相同。
- `DictionaryLayout` 記錄 `has_bom: bool` 與 `header: tuple[str, ...]`。
- 每一列帶著它記錄的原始欄位（`tuple[str, ...]`）和起始行號：
  - `PreservedDictionaryRow` 上是 `line` 與 `fields`；
  - `DictionaryEntry` 上是 `fields`，宣告為 `field(default=(), compare=False, repr=False)`（不需要 `line`）。
  所以 dataclass 相等、所有既有測試與 trace 步驟都不受影響。
- 讀檔可以改用 `csv.reader` 取得原始欄位和行號，但必須與 `DictReader` 的值一致（探針 5）：第一筆記錄是表頭、跳過 `[]` 記錄、缺少的欄位為 `""`、名稱重複時取最後一個值。由一致性測試以兩種讀法跑 F-4／F-6 的語料比對（測試計畫 A）。
- `load_dictionary_entries` 與筆數不變。讀檔錯誤照舊往外拋。

**D7. 取消、Esc、關閉鈕只在有修改時詢問（U3）。**

- 編輯器為 `wx.ID_CANCEL` 綁定 `wx.EVT_BUTTON`。wx 會把 Esc 和關閉鈕轉成點擊這個按鈕（`wxDialogBase::OnCloseWindow` 與 Esc 的 char hook 都模擬 Cancel 點擊），所以一個 handler 就涵蓋三者。由 GUI 項目確認。
- 沒有修改：`event.Skip()`，照現在的方式關閉。
- 有修改：顯示 `wx.GenericMessageDialog`（`wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING`，按鈕文字以 `SetOKCancelLabels` 設定；「規劃後的修正（F-11）」3）：
  - 標題 `Unsaved Changes`；
  - 訊息 `Do you want to discard the changes you made to dictionary "{name}"?`，`{name}` 是檔名（不含副檔名）；
  - OK 為 `&Discard Changes`，Cancel 為 `&Back to Editing`。
- 放棄變更：`event.Skip()`，對話框關閉，不寫任何東西。返回編輯（也包括 Esc、Alt+F4、關閉鈕、Enter）：編輯器保持開啟。
- 使用自訂文字的 OK／Cancel，而不是 是／否，因為 是／否 的 task dialog 會忽略 Esc 與 Alt+F4（探針 2）。NVDA 使用者在問句上按 Esc，應該回到編輯器，而不是停在一個沒有反應的對話框。使用一般對話框而不是 task dialog，因為使用自訂按鈕文字的 task dialog 從編輯器顯示時，會把 Alt+F4 當成 OK，也就是放棄變更（「規劃後的修正（F-11）」3）。
- **回到編輯器時的焦點**（本對話框、D1 的對話框、存檔錯誤）：顯示對話框前，編輯器記下 `wx.Window.FindFocus()`。之後若那個控制項仍是編輯器的子視窗，就把焦點放回去（通常是「確定」或「取消」按鈕；在清單上按 Esc 時則是清單）。Windows 通常會自己還原；明確設定是為了涵蓋 F-9 M-6 遇到的沒有還原的情況。
- 刪除不詢問（U3.2）。
- 在 `ui/message_box.py` 新增 `confirm_box(message, caption, ok_label, cancel_label, parent) -> bool`，兩個確認框都用它以 `wx.GenericMessageDialog` 建立。`message_box`（task dialog）不變。

**D8. 重複檢查在詞條對話框的「確定」中執行（U4）。**

- `AddSymbolDialog(parent, entry=None, *, is_duplicate=None)`，`is_duplicate` 是 `Callable[[str], bool]`。`_on_ok`：先做格式檢查（不變）；接著若 `is_duplicate(entry.text)`：
  - 顯示既有的 `Source text "{identifier}" already exists.`，標題 `Error`，`wx.OK | wx.ICON_ERROR`，父視窗是詞條對話框（文字、標題、樣式都與現在相同，所以 golden trace 中的訊息記錄不變）；
  - 焦點放到來源文字欄並全選；
  - 不 `Skip` 就 return，對話框保持開啟，每個欄位都維持輸入的內容。
- 編輯器傳入 `lambda text: self._model.is_duplicate(text, editing=current_entry)`（D9）。
- 模型的 `add`／`replace` 仍會拋出 `DuplicateEntryError` 作為最後防線，編輯器也保留它的 handler。介面上已經走不到這條路。

**D9. 刪除與編輯以 identity 為準（U5.2、P2-2 Q4）。**

- `remove` 刪除「就是」選取中那筆可見詞條的列（`is`），與 `replace` 已使用的查找方式相同。
- `replace` 把被取代那一列的原始 `fields`（D5）交給新詞條，所以多出的欄位會保留。
- `is_duplicate(text, editing=None)` 就是 `source_text_exists(text, exclude_entry=editing)`，再加一條：編輯時保留該詞條自己的來源文字（`text == editing.text`），永遠不算重複。現在有兩列相同的 `a` 時，任何一列都無法在不改文字的情況下編輯，因為另一列「已存在」（Q4 前半）。這樣的編輯沒有新增任何重複，所以接受（O6）。
- **選取。** 新增與取代後，以 identity 選取新詞條。因為依 Q4 的修改，編輯後的分身可能與另一個分身相等，以相等比對會跳到第一個。刪除與篩選後，照現在的方式以相等還原選取。探針 1 顯示 golden trace 固定了這個行為，而且選取會落在剩下的分身上。

**D10. 只改大小寫的改名（U5.1、F-W6）。**

- `rename_dictionary`：目的地存在且 `os.path.samefile(source, destination)` 為 `True` 時，代表是同一個檔案的不同大小寫，以 `Path.rename` 改名（探針 3）。目的地存在但是另一個檔案時，仍以 `FileExistsError` 拒絕（區分大小寫的檔案系統）。
- 名稱完全相同仍然不做任何事（`name_prompt.py`）。
- 選用名稱與 `config.json` 透過既有的 `plan_dictionary_state_after_rename`（`active_name == previous_name`）更新。presenter 測試分別固定改名的是選用中字典與其他字典的情況。
- 預設字典仍不能改名。`default` 改為 `Default` 會在任何檔案操作之前，被保留名稱檢查擋下。

**D11. 被鎖住的匯入來源顯示 F-6 的原因（U5.3、M-4）。**

- `import_dictionary` 在開啟或讀取**來源檔**時（`validate_dictionary_csv` 或複製時）若發生 `PermissionError`，包成新的 `DictionaryImportSourceError(error)`。這個例外不是 `OSError`，原始錯誤保留在 `.error` 與 `__cause__`。
- presenter 在 `OSError` 之前攔它，顯示既有的 `Failed to import dictionary: {error}`，`{error}` 代入 `describe_dictionary_read_error(exc.error)`（CANNOT_OPEN）。做法與 F-6 D9 處理 NOT_UTF8、INVALID_CSV 相同。
- 寫入字典資料夾時的錯誤，以及來源檔的其他 `OSError`（例如 `FileNotFoundError`），維持現在的訊息（O7）。

**D12. 先讀檔，再建立編輯器（U5.4、M-5）。**

- `DictionaryEntriesDialog.__init__(parent, dictionary_path, model=None)`。沒有傳入 `model` 時，在 `super().__init__` **之前**讀檔，讀檔錯誤時就不會留下原生對話框（Q8 的測試翻轉）。
- `gui.on_open_dictionary_management` 自己先載入模型，再建立對話框：
  - **讀檔錯誤：** 以 `log_dictionary_read_error` 記錄，顯示 `describe_unreadable_dictionary(name, error)`。訊息、標題、圖示都與現在相同。
  - **建立對話框時發生錯誤：** 以 `"Unexpected error while opening the dictionary editor"` 連同 traceback 記錄到 `dotexpress.gui`（`gui.log`），並顯示新的 `Failed to open the dictionary editor: {error}`（標題 `Error`，`wx.OK | wx.ICON_ERROR`）。
- 在 `super().__init__` 之後建立介面失敗時，建構子呼叫 `self.Destroy()` 再重新拋出，所以這種情況也不會留下東西。

**D13. 轉換忽略編輯器隱藏的列（U6、#8）。**

- 在 `LoadedDictionaryRules.from_paths` 中，以下情況跳過該列：`source.strip()` 為空；或 `type_ == "Bopomofo"` 且 `processing(target.lstrip())` 拋出例外（只去掉開頭的空白，D14；使用者於 2026-10-11 決定）。
- `type_` 是原始類型。編輯器的 `normalize_entry_type` 只把完全相同的字串 `Bopomofo` 當成注音，兩者一致。
- `processing` 是注入的解析器，正式環境是 `normalize_zhuyin_sequence`。所以 `dictionary_rules.py` 仍不 import `dictionaries`，而判斷結果等於對編輯器顯示的值執行 `_is_editable`。
- 一致性測試確認：對一組語料，「用 `normalize_zhuyin_sequence` 轉換時被跳過」等於「被 `load_dictionary_rows` 隱藏」（測試計畫 F）。
- 留下來的列以原始來源與原始目標轉換；`Bopomofo` 列以 `processing(target.lstrip())`（編輯器顯示的注音）轉換，沒有 fallback（「規劃後的修正（F-11）」6，使用者於 2026-10-11 決定）。原始值能解析的列轉換結果與以前完全相同；隱藏列與開頭有空白的注音列會改變輸出。
- golden 案例「Bopomofo row with a processing that raises」翻轉：這列現在被跳過。
- `translation_golden.json` 不受影響：它唯一的字典列是合法的。

**D14. 最後一個音節是一聲（O1 選 (b)，使用者於 2026-10-11 決定；下面的規則是使用者在審查 I-1 之後於 2026-10-11 決定的）。**

使用者選擇 O1 的 (b)（2026-10-11）。D14 的第一版會先去空白，只有加上聲調空白才能解析時再補回空白；審查 I-1 之後，使用者把它改成（2026-10-11）：

- `Bopomofo` 列的標準注音是 `braille.lstrip()`：只去掉開頭的空白，結尾的空白完全保留檔案中或輸入時的樣子；
- 這個注音原樣能解析，這列才合法；任何地方都不補上聲調空白；
- 這套規則用在讀檔的分類與值、`validate_dictionary_entry` 與 `AddSymbolDialog.get_braille`，以及 D13 的跳過判斷（轉換的也是同一個注音）。來源文字與其他類型照舊去掉前後的空白。

效果：

- 有聲調空白的列（`中心,ㄓㄨㄥ ㄒㄧㄣ ,Bopomofo`、`媽,ㄇㄚ ,Bopomofo`）會顯示、可以編輯、存檔時位元組不變，轉換與現在相同；
- 沒有聲調空白的列（`抹,ㄇㄚ,Bopomofo`），或最後一個音節後面還有空白的列（`ㄇㄚ  `、`ㄉㄨˋㄗ˙ `、tab 或 U+3000），是不合法的：會被隱藏，在 D1 確認框中以「格式不正確」列出，「移除並儲存」時被刪除，轉換也忽略它們；
- 在詞條對話框輸入有空白的 `ㄓㄨㄥ ㄒㄧㄣ ` 會被接受，照輸入的樣子儲存；沒有空白的 `ㄓㄨㄥ ㄒㄧㄣ` 或 `ㄇㄚ` 會出現原有的「請輸入有效的注音序列。」（沒有新字串）。

未採用的 (a) 會拿掉 D14：這類列會維持隱藏，在 D1 的確認框中以「格式不正確」列出，「移除並儲存」時被刪除，轉換也忽略它們。

**D15. 字串與 catalog。** 下表 11 個字串。依序執行 `generate-pot.bat`、`msgmerge`、補上 msgstr、`msgfmt --check --statistics`：全部已翻譯、0 fuzzy。`POT-Creation-Date` 維持固定。檢查 `msgmerge` 沒有把新 msgid 配對到舊字串而標成 fuzzy，例如 `&Discard Changes` 配到 `Close &Without Saving`，或 `Unsaved Changes` 配到 `Cannot Save Document`。

## 各路徑改前改後

| 路徑 | 改前 | 改後 |
| --- | --- | --- |
| 開啟編輯器 | 先建立原生對話框再讀檔（Q8） | 先讀檔；讀檔錯誤顯示 F-6 的原因，不建立對話框（D12） |
| 確定，沒修改，沒有隱藏列 | 重寫檔案（去空白、General、無 BOM、丟掉多出的欄位） | 不寫檔（D4） |
| 確定，沒修改，有隱藏列 | 重寫，隱藏列留在原位（F-4） | D1 確認框；「移除並儲存」寫入時不含隱藏列；「返回編輯」保持開啟 |
| 有修改後按確定 | 以正規化格式重寫 | 去空白／General 後重寫，保留表頭、多出的欄位和 BOM（D5）；有隱藏列時先出現 D1 確認框 |
| 取消／Esc／關閉鈕 | 直接關閉，修改默默遺失 | 沒修改：直接關閉；有修改：D7 確認框，預設「返回編輯」 |
| 刪除 | 刪除第一筆相等的列，不詢問 | 刪除選取的列（D9），不詢問（U3.2） |
| 新增／編輯時重複 | 詞條對話框先關閉，再出現錯誤；輸入遺失 | 錯誤在詞條對話框內出現；輸入保留；焦點在來源文字欄並全選（D8） |
| 新增與隱藏列相同的文字 | 拒絕（F-4 D5） | 接受（D2）；按「確定」時列出那個隱藏列 |
| 編輯分身並保留文字 | 被當成重複而拒絕 | 接受（D9） |
| 轉換 | 使用只有空白的文字與不合法的注音列 | 忽略它們（D13） |
| `alpha` 改名為 `Alpha` | 「已存在」 | 改名成功；選用中時 `config.json` 跟著更新（D10） |
| 匯入被鎖住的檔案 | `匯入字典失敗：[Errno 13] ...` | `匯入字典失敗：無法開啟檔案。……`（D11） |
| 建立編輯器時出錯 | 說成「無法讀取」；留下隱藏的對話框 | 一般失敗訊息，traceback 寫入 `gui.log`，不留下東西（D12） |
| 字典管理的筆數 | 看得到的詞條 | 不變 |

範例：`dict_badbopo.csv`（`text,braille,type`／`臺北,⠞⠺,Braille`／`肚子,ㄉㄨˋ|ㄗ˙,Bopomofo`／`數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo`，CRLF，無 BOM）。按「確定」顯示：

```text
字典「dict_badbopo」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：

第 3 列：「肚子」的注音「ㄉㄨˋ|ㄗ˙」格式不正確
第 4 列：「數學」的注音「ㄕㄨˋ ㄒㄩㄝˊ」格式不正確

要移除這些列並儲存字典嗎？
```

「移除並儲存」後檔案為 `text,braille,type\r\n臺北,⠞⠺,Braille\r\n`。轉換 `肚子數學` 在存檔前後輸出相同，因為兩列都不再被使用（D13）。

## 各檔案的設計

### `client/dictionaries/entries.py`（tab）

- `DictionaryLayout(has_bom: bool = False, header: tuple[str, ...] = ())` 與 `LoadedDictionary(rows, layout)`，都是 frozen dataclass。
- `PreservedDictionaryRow` 新增 `line: int = field(default=0, compare=False)`、`fields: tuple[str, ...] = field(default=(), compare=False)`，以及 `reason` property（`"no_source_text"` 或 `"invalid_bopomofo"`）。`DictionaryEntry` 新增 `fields`（`compare=False`、`repr=False`）。
- `load_dictionary_file(path)`（D6）。`load_dictionary_rows` 回傳 `load_dictionary_file(path).rows`。`load_dictionary_entries` 不變。
- `save_dictionary_entries(path, entries, layout=DictionaryLayout())`（D5）。使用預設 layout 時，詞條寫出的位元組與現在完全相同，所以沒傳 layout 的呼叫端輸出不變。
- D14：`canonical_bopomofo(braille) -> str | None`（`braille.lstrip()` 原樣能解析時傳回它，否則 `None`；使用者於 2026-10-11 決定），供 `_is_editable`、讀檔與 `validate_dictionary_entry` 使用。`AddSymbolDialog.get_braille` 對注音欄只去掉開頭的空白。
- `LoadedDictionary.header_recognized`；寫檔把補上的欄位放在超出表頭的欄位之前（「審查後的修正（F-11）」1、2）。

### `client/dictionaries/entry_list_model.py`（tab）

- 記錄 `_layout` 與 `_loaded_entries`（複本）。
- 新增 `has_changes()`、`hidden_rows`（依檔案順序的 `PreservedDictionaryRow` tuple）與 `is_duplicate(text, editing=None)`；審查後再新增 `header_recognized`（來自讀檔；由列建立的模型為 True），它為 False 時 `save` 拒絕寫入。
- `source_text_exists` 跳過保留列（D2）。`remove` 改用 identity。`replace` 複製 `fields`。`add` 與 `replace` 以 identity 選取（D9）。`save(path)` 以 layout 寫出詞條，**不含**保留列（D1）。
- 存檔成功後，快照更新為存下的詞條，隱藏列從模型中移除。編輯器隨即關閉；這是為了讓模型在測試中保持一致。
- import 清單維持 `{__future__, collections.abc, dataclasses, pathlib, dictionaries.entries}`（`test_model_imports_no_ui_or_translation_module`）。
- 更新模組 docstring 中的比對規則。

### `client/dialog.py`（tab）

- `AddSymbolDialog`：`is_duplicate` 參數（D8）。重複時，焦點與全選放在 `identifier_ctrl`。
- `DictionaryEntriesDialog`：
  - `model` 參數，以及在 `super().__init__` 之前讀檔（D12）；
  - 建立介面失敗時 `Destroy`；
  - 取消的 handler（D7）；
  - `_on_ok`（D4、D1），先檢查 `header_recognized`（「審查後的修正（F-11）」1）；
  - `_confirm_hidden_rows()` 組出 D1 的文字：由 `hidden_rows` 產生每一列、列數上限與「另有…」那一行；
  - 對話框之後還原焦點；
  - `_open_entry_dialog` 傳入 `is_duplicate`。編輯器自己的重複訊息只留作最後防線。

### `client/ui/message_box.py`（4 個空白）

- `confirm_box(message, caption, ok_label, cancel_label, parent=None) -> bool`：`wx.GenericMessageDialog(parent, message, caption, wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING)`、`SetOKCancelLabels(ok_label, cancel_label)`，回傳 `ShowModal() == wx.ID_OK`（「規劃後的修正（F-11）」3）。

### `client/gui.py`（tab）

- `on_open_dictionary_management`：先讀檔再建立，搭配 D12 的兩道防護。logger 用既有的 `dotexpress.gui`。

### `client/dictionaries/manager.py`（4 個空白）

- `rename_dictionary`：`samefile` 分支（D10）。
- `DictionaryImportSourceError`，以及 `import_dictionary` 中的包裝（D11）。

### `client/dictionaries/presenter.py`（tab）

- `import_from_file` 在 `OSError` 之前攔 `DictionaryImportSourceError`（D11）。`rename` 不變，但加上測試。

### `client/conversion/text/dictionary_rules.py`（4 個空白）

- `from_paths` 中 D13 的跳過判斷：`processing(target.lstrip())`，拋出例外就略過該列，沒有 fallback（使用者於 2026-10-11 決定）。docstring 註明規則與編輯器相同。

### Catalog

- `client/locales/dotexpress.pot`、`client/locales/zh_TW/LC_MESSAGES/dotexpress.po`、`.mo`（D15）。

### 不修改

- `read_problems.py`；
- `name_prompt.py`；
- `translation/dictionary_state.py`；
- `DictionaryManagementDialog`；
- `validate_dictionary_csv`（只是被包裝）；
- `shared/atomic_write.py`；
- `brailleTables/`、liblouis 與兩個 fixture。

## 維持不變的部分

- 編輯器的版面、標題、欄位、篩選、新增／編輯／刪除按鈕、篩選與刪除後的選取，以及詞條對話框的格式訊息。
- 重複訊息的文字、標題與圖示。
- 存檔錯誤的訊息，以及錯誤後保持開啟。
- 除了 D11 的情況外，`Failed to import dictionary: {error}` 一律不變。
- 字典管理：筆數、F-6 的原因欄、其他所有動作與訊息。
- 編輯器看得到的每一列的轉換結果。
- 無 BOM、表頭為 `text,braille,type`、沒有多出欄位的檔案，寫出的位元組不變。
- `translation_golden.json`（`e67d95a1...`）與 `dictionary_entries_trace.json`（`f493da52...`）。

## 使用者可見字串

| # | msgid | zh_TW msgstr | 用途 |
| --- | --- | --- | --- |
| 1 | `Remove Rows That Cannot Be Shown` | `移除無法顯示的列` | D1 標題 |
| 2 | `Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?` | `字典「{name}」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：\n\n{rows}\n\n要移除這些列並儲存字典嗎？` | D1 訊息 |
| 3 | `Row {line}: no source text` | `第 {line} 列：沒有來源文字` | D1 列說明 |
| 4 | `Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid` | `第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確` | D1 列說明 |
| 5 | `Other rows not listed: {count}` | `另有 {count} 列未列出` | D1，超過 10 列時 |
| 6 | `Remove and &Save` | `移除並儲存(&S)` | D1 OK 按鈕 |
| 7 | `&Back to Editing` | `返回編輯(&B)` | D1 與 D7 的 Cancel 按鈕 |
| 8 | `Unsaved Changes` | `尚未儲存的變更` | D7 標題 |
| 9 | `Do you want to discard the changes you made to dictionary "{name}"?` | `要放棄對字典「{name}」所做的變更嗎？` | D7 訊息 |
| 10 | `&Discard Changes` | `放棄變更(&D)` | D7 OK 按鈕 |
| 11 | `Failed to open the dictionary editor: {error}` | `無法開啟字典編輯器：{error}` | D12 |
| 12 | `Dictionary "{name}" cannot be saved: its header is not recognized. The first line of the file must contain the text, braille, and type headers.` | `無法儲存字典「{name}」：無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。` | 「確定」，表頭無法辨識（審查修正新增，「審查後的修正（F-11）」1） |

msgid：369 + 11 = **380**；加上審查修正的字串 12 是 **381**。引號沿用 `Dictionary "{name}" already exists.`／`字典「{name}」已存在。`；快速鍵的寫法沿用 F-5 的 `重試(&R)`。

新出現在其他路徑的既有訊息：

- `Source text "{identifier}" already exists.`，改由詞條對話框顯示（D8）；
- `Failed to import dictionary: {error}`，代入 CANNOT_OPEN 的說明（D11）。

## 無障礙（NVDA）

| 對話框 | 先讀出的標題 | 出現時的焦點 | Esc／Alt+F4 | 之後的焦點 |
| --- | --- | --- | --- | --- |
| D1 隱藏列 | 移除無法顯示的列 | 返回編輯（預設） | 返回編輯 | 移除並儲存：編輯器關閉，焦點回到主視窗，與現在按「確定」後相同。返回編輯：回到原本有焦點的控制項（D7） |
| D7 放棄變更 | 尚未儲存的變更 | 返回編輯（預設） | 返回編輯 | 放棄：編輯器關閉。返回：回到原本有焦點的控制項（通常是「取消」；在清單或篩選欄按 Esc 時則是該處） |
| D8 重複（詞條對話框內） | 錯誤 | 確定 | 關閉訊息 | 「來源文字」欄，文字全選；NVDA 讀出欄位名稱與選取的文字 |
| 存檔錯誤（既有） | 錯誤 | 確定 | 關閉訊息 | 原本有焦點的控制項 |
| D11 匯入 | 錯誤（既有） | 確定 | 關閉 | 不變（字典管理） |
| D12 失敗 | 錯誤 | 確定 | 關閉 | 主視窗 |
| 表頭無法辨識（審查修正） | 錯誤 | 確定 | 關閉訊息 | 原本有焦點的控制項 |

- D1 與 D7 的確認框是一般對話框（「規劃後的修正（F-11）」3）：標題是視窗標題，訊息的每一行是一段文字，接著是兩個按鈕；對話框出現時 NVDA 是否讀出全文由手動項目 107 確認。其他訊息框是 task dialog，出現時 NVDA 會讀出全文（F-5、F-9 的量測）。每一列的說明都很短，並以列號開頭，NVDA 讀起來是一份可用的清單。
- 預設按鈕一律是不會遺失任何東西的那個。
- 每個按鈕都有快速鍵：S、B、D。

## 測試計畫

TDD：每一步的測試先寫，並因預期的原因失敗。縮排依各檔案而定（`test_dictionary_entry_list_model.py`、`test_dictionary_name_prompt.py` 用 tab；`test_dictionary_entries_dialog.py`、`test_dictionary_entries.py` 用 4 個空白；請逐檔確認）。只使用暫存資料夾。會讓程式寫 log 的測試使用 `assertLogs` 或 `isolate_file_logs`，不寫入 `client/log/`。非 ASCII 測試資料用 `\u` escape；涉及 surrogate 時以腳本寫入（HANDOFF §2）。

### A. 讀檔與寫檔（`tests/test_dictionary_entries.py`）

1. layout 記錄 BOM（有與沒有）與讀到的表頭，包括多出的欄位、重複的名稱、缺少 `type`、空檔案。
2. 起始行號：表頭為 1；空行被跳過但有計入；有引號的跨行欄位；它之後的隱藏列行號正確。
3. 一致性：對 F-4、F-6 的語料加上 1、2 的案例，新讀法的 (text, braille, type, 類別) 與現在的 `DictReader` 相同。
4. 寫檔：
   - BOM 保留，也不會自己加上；
   - 表頭順序保留，缺少的必要欄位補在後面；
   - 沒修改的列保留多出的欄位與超出表頭的欄位；
   - 新增的列多出的欄位是空的；
   - 編輯過的列保留多出的欄位；
   - 太短的列補齊；
   - 套用去空白與 `General`；
   - 名稱重複時寫入最後一個位置；
   - 預設 layout 寫出現在的位元組；
   - 隱藏列永遠不寫出。
5. `PreservedDictionaryRow.reason`：空白文字、只有空白的文字、不合法的注音。
6. （D14，使用者於 2026-10-11 決定）`canonical_bopomofo`：`ㄇㄚ ` 不變、` ㄇㄚ ` 變成 `ㄇㄚ `、`ㄉㄨˋㄗ˙` 不變；`ㄇㄚ`、`ㄇㄚ  `、`ㄉㄨˋㄗ˙ ` 與 `ㄉㄨˋ|ㄗ˙` 為 `None`（不補任何東西）。讀檔時會顯示 `中心,ㄓㄨㄥ ㄒㄧㄣ ,Bopomofo`，沒有修改的存檔保留它的位元組；`抹,ㄇㄚ,Bopomofo` 被隱藏。

### B. 模型（`tests/test_dictionary_entry_list_model.py`）

1. `has_changes`：
   - 在載入後、篩選後、新增又刪除同一筆後、編輯成相同值後為 `False`；
   - 改了值、刪了一列、改了順序（刪掉再加回）後為 `True`；
   - 隱藏列一律不算。
2. `remove` 依 identity：在 `[a, b, a]` 中刪除可見索引 2，刪的是第三列。存檔順序為 `a, b`，保留第一個 `a` 的欄位。
3. `replace` 保留 `fields`；`add` 的 `fields` 為空。
4. D2：保留列的文字不算重複。**刪除** F-4 D5 的兩個測試（由這個取代）。
5. D9：編輯分身並保留文字不算重複；把另一列改成那個文字算重複。新增與取代以 identity 選取；篩選與刪除以相等選取。
6. `hidden_rows` 依檔案順序並帶行號。`save` 拿掉它們並保留 layout。

### C. 編輯器（`tests/test_dictionary_entries_dialog.py`，`_EditorHarness`）

1. 沒修改按「確定」：不寫檔，檔案位元組與 `st_mtime_ns` 不變，`Skip`。**翻轉** Q2 的測試。調整沒修改就按「確定」並預期寫檔的測試（`:852`、`:1333`）：先做修改，或改為預期不寫檔。
2. 有修改後按「確定」：寫檔（有 BOM 的檔案仍有 BOM；多出的欄位保留）；`Skip`。
3. 有隱藏列時按「確定」：以完全相同的 zh_TW 標題、訊息與按鈕文字呼叫 `confirm_box`（兩列；十一列時為 10 行加上 `另有 1 列未列出`）。
   - 移除並儲存：寫檔且不含隱藏列，`Skip`。
   - 返回編輯：不寫檔、不 `Skip`，焦點還原。
4. 「移除並儲存」後存檔失敗：既有訊息、保持開啟，下次按「確定」再問一次。
5. 取消已綁定 handler；沒修改：`Skip`，沒有對話框。**翻轉** Q5 的測試。
   - 有修改：出現 D7 對話框，文字完全相同；放棄：`Skip`、不寫檔；返回：不 `Skip`，焦點還原。
6. 刪除：沒有對話框（Q5 刪除測試的這一半保留，只翻轉 identity 的部分，D9）。
7. 新增與編輯時重複：訊息框的父視窗是**詞條對話框**，詞條對話框保持開啟，輸入保留，`identifier_ctrl` 取得焦點並 `SelectAll`。**翻轉**兩個 Q6 測試。harness 的假詞條對話框加上第二個腳本回答（改文字或取消）。
8. Q4：編輯分身並保留文字被接受；刪除第二個分身刪的是第二個。**翻轉**兩個 Q4 測試。
9. 建構：
   - 傳入 `model=` 時不讀檔；
   - 沒傳時，`UnicodeDecodeError` 在原生 `__init__` **之前**拋出。**翻轉** Q8 的測試；
   - `_build_ui` 失敗時呼叫 `Destroy` 並重新拋出。
10. **Golden trace。** 重播時以「移除並儲存」回答 D1 確認框，並在比對前從 OK 步驟的 log 拿掉這個確認框的記錄。斷言 `_TRACE_KEPT_ROWS` **不在**存下的 CSV 中（F-4 的剔除處理拿掉）。假詞條對話框執行 `is_duplicate`，重複時記錄相同的 `MessageBox`，然後取消（錄製的使用者只輸入一次）。不修改 `dictionary_entries_trace.json`，sha256 維持 `f493da52...`。

### D. 詞條對話框（`tests/test_dialog_validation.py`）

順序是先檢查格式再檢查重複。沒有 `is_duplicate` 時行為與現在相同。重複時不 `Skip`，訊息框的父視窗是詞條對話框。

### E. 改名、匯入、主視窗

- `tests/test_dictionary_name_prompt.py`：F-W6 通過。另一個大小寫不同、但確實存在的不同檔案仍被拒絕（把 `os.path.samefile` patch 成 `False`）。
- `tests/test_dictionary_manager.py`：來源檔的 `PermissionError`（patch 來源路徑的 `open`）變成 `DictionaryImportSourceError`；寫入目的地的仍是 `PermissionError`。
- `tests/test_dictionary_presenter.py`：
  - 選用中字典只改大小寫時呼叫 `set_active_name("Alpha")`；其他字典則不呼叫；
  - 來源錯誤顯示 `匯入字典失敗：無法開啟檔案。…`（CANNOT_OPEN 的文字）；目的地錯誤維持原始文字。
- `tests/test_gui_document_flows.py`：
  - 讀檔錯誤顯示 F-6 的文字，不建立編輯器；
  - 建立時錯誤顯示字串 11，並記錄 traceback（`assertLogs`）；
  - 調整 `test_editor_that_cannot_read_its_dictionary_shows_the_reason`。

### F. 轉換（`tests/test_conversion_text_dictionary_rules.py`）

- 只有空白的文字（`"  "`、U+3000）不是規則。
- 不合法的注音列不是規則（注入會拋例外的 `processing`，以及真的解析器）。**翻轉** golden 案例「processing that raises」。
- 合法列的輸出逐位元組相同。
- 一致性：對一組語料（F-4 的案例、`dict_badbopo`、各種空白、未知與小寫的類型、D14 的案例），「`from_paths` 以 `normalize_zhuyin_sequence` 跳過」等於「`load_dictionary_rows` 給出 `PreservedDictionaryRow`」。

### G. Catalog（`tests/test_i18n.py`）

11 個 msgstr；AST 掃描結果與 catalog 相同（380）。

### Mutation 檢查（plan 執行；每個都必須被抓到）

1. `has_changes` 永遠為 `True`；
2. `has_changes` 忽略順序；
3. `has_changes` 計入隱藏列；
4. 沒有隱藏列也顯示 D1 確認框；
5. 「移除並儲存」寫出保留列；
6. 「返回編輯」仍寫檔；
7. 拿掉 `CANCEL_DEFAULT`（OK 變成預設）；
8. 取消的 handler 不詢問就 `Skip`；
9. 沒修改也詢問；
10. 重複檢查計入保留列（D5 回來）；
11. 重複檢查沒有排除正在編輯的詞條；
12. 拿掉「分身保留文字」的例外；
13. 詞條對話框在重複時關閉（`Skip`）；
14. 焦點沒有放到來源文字欄；
15. `remove` 改回相等比對；
16. `replace` 丟掉 `fields`；
17. 丟掉 BOM；
18. 一律寫 BOM；
19. 丟掉多出的欄位；
20. 表頭重新排序；
21. 起始行號差一；
22. 列數上限變成 9 或 11；
23. 轉換保留只有空白的文字；
24. 轉換以原始（未去空白）的目標驗證；
25. `rename_dictionary` 沒有 `samefile`（會覆蓋另一個檔案）；
26. 匯入的包裝也攔到目的地錯誤；
27. 主視窗在讀檔前建立對話框。

### 數量

約 60 個新測試，8 個翻轉或刪除（A 16、B 14、C 14、D 3、E 8、F 6、G 1）。確切的 `Ran` 由 plan 決定。Windows 上：`FAILED (skipped=7)`，**沒有 error**，因為 F-W6 已修好。

## 遷移步驟（每一步一個綠燈 commit，先紅後綠）

1. `fix: allow a case-only dictionary rename (F-11, F-W6)`：D10，測試 E。
2. `fix: explain a locked dictionary import source (F-11, F-6 M-4)`：D11。
3. `fix: read the dictionary before building its editor (F-11, F-6 M-5)`：D12、字串 11、catalog。
4. `fix: keep the BOM, header and extra columns of a dictionary (F-11)`：D5、D6；測試 A、C2。
5. `fix: delete and edit the selected dictionary entry (F-11, #9)`：D9；測試 B2、B3、B5、C8。
6. `fix: report a duplicate source text inside the entry dialog (F-11, P2-2 Q6)`：D2、D8；測試 B4、C7、D、C10（詞條部分）。
7. `fix: save a dictionary only after a change and ask before discarding changes (F-11, P2-2 Q2, Q5)`：D3、D4、D7、字串 7～10、catalog。
8. `fix: confirm and remove dictionary rows the editor cannot show (F-11, #7)`：D1、字串 1～6、catalog；C3、C4、C10（確定的部分）。
9. `fix: ignore hidden dictionary rows when converting (F-11, #8)`：D13；測試 F。
10. `fix: keep the tone space of a first-tone final syllable (F-11)`：D14（O1 選 (b)；plan 以 Task 6 執行，見「規劃後的修正（F-11）」2）。

每個 commit 結尾加 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`，只 stage 明確路徑。

## 驗收條件

在 Windows 上，從 `client/` 以 `$PY` 執行，runtime 依 F-3 plan Task 0 複製。

1. 完整套件：沒有 failure，也沒有 error（F-W6 已修好）；`Ran` 與 plan 相同。
2. 重點測試：`$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation tests.test_dictionary_name_prompt tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_conversion_text_dictionary_rules tests.test_gui_document_flows tests.test_i18n -v` 通過。
3. `grep -rn "KNOWN BUG (P2-2 spec, Q[24568])" client/tests` 沒有輸出。
4. Catalog：11 個新 msgid，msgstr 與上表相同；`msgfmt --check --statistics` 全部已翻譯、0 fuzzy；AST 掃描與 catalog 相同（380）；`POT-Creation-Date` 不變。
5. 兩個 fixture 的 sha256 不變。
6. 沒有動到 app 資料：
   - 主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 前後 sha256 相同；
   - worktree 沒有產生 `client/log/`、`client/workspace/`、`client/config.json`。
7. `git diff main --stat` 只動到「各檔案的設計」中的檔案、上述測試，以及 spec、plan 與 history 檔案。
8. 上述 mutation 檢查。
9. 下方 packaged GUI 驗證，結果放在實作的 history 資料夾。

## Windows 驗證（packaged build）

build 與 process 規則同 F-9：

- 主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面，執行 `scripts\build-dotexpress.bat`；
- 在 `PYZ-00.toc` 中確認 `dialog.py`、`dictionaries\*.py`、`ui\message_box.py`、`conversion\text\dictionary_rules.py` 與 `gui.py` 都來自 worktree；
- exe 放在 `D:\dxtest\N-f11\`；「改前」是 `D:\dxtest\N-f9b`；
- 每個項目在新的 `D:\dxtest\auto<項目>-f11` 資料夾執行，使用 exe 的複本；
- 只結束這些資料夾底下的 process（`taskkill /T`）。
- 改前的 build `N-f9b` 只執行 fix 項目（兩個 build 的預期結果不同，或項目經過的程式碼有改動）；regression 項目只在 `N-f11` 執行，只有結果不符預期時才也在 `N-f9b` 執行（使用者，2026-10-11）。F-11 的每個項目（95–106，以及重跑的 23–29、35、44、47）都是 fix 項目，所以全部在兩個 build 上執行。

腳本放在 history 資料夾的 `auto/`。不修改、直接沿用 `2026-10-09-03-windows-verification/auto/`（`dx.py`、`dicts.py`、`lock.py`）與 `2026-10-10-01-f5-save-failure-handling/auto/f5gui.py`。task dialog 以 UIA 讀取。**任何腳本都不讀寫剪貼簿**；文字以 `set_edit_text` 或按鍵輸入。每個項目在前後記錄每個字典檔的 sha256、大小與 `st_mtime_ns`。

| # | 步驟 | F-11 之後的預期 | 改前 |
| --- | --- | --- | --- |
| 95 | 匯入 `dict_badbopo.csv`；開啟編輯器；按確定 | D1 確認框：標題、「各路徑改前改後」中的文字（兩行）、按鈕 移除並儲存(S)／返回編輯(B)，焦點在「返回編輯」。按 Esc：編輯器仍開著、檔案不變、焦點回到「確定」。按確定後按 Enter：同上。按確定後選「移除並儲存」：檔案為 `text,braille,type\r\n臺北,⠞⠺,Braille\r\n`，無 BOM；字典管理顯示 `1` | 沒有對話框；檔案不變（F-4） |
| 96 | 在設定選 `dict_badbopo`；在 95 的「移除並儲存」之前與之後各轉換一次 `肚子數學` | 兩次輸出都等於用 `default` 字典轉換同一段文字的輸出（沒有用到任何規則） | 用到兩條注音規則（`⠙⠌⠐...`） |
| 97 | `extra.csv`（有 BOM，表頭 `text,note,braille,type`，有一列前面有空白、類型為 `Custom`，CRLF）：開啟，按確定 | 沒有對話框，sha256 與 `st_mtime_ns` 不變 | 重寫：BOM 與 `note` 消失 |
| 98 | `extra.csv`：編輯第 1 列的點字、新增一列，按確定；對 `bom_lf.csv`（2026-10-09-03 的資料）做同樣的事 | BOM 保留；表頭為 `text,note,braille,type`；舊列的 `note` 保留，新列為空；每一列都去空白，`Custom` 寫成 `General`；`bom_lf.csv` 仍無 BOM、CRLF | BOM 與 `note` 消失 |
| 99 | 開啟 `alpha`（兩列）；新增 `x`；按 Esc；再按取消；再按 Alt+F4 | 每次都出現 D7 對話框：標題、提到 `alpha` 的訊息、按鈕 放棄變更(D)／返回編輯(B)，焦點在「返回編輯」。在對話框按 Esc：編輯器仍開著，`x` 仍在清單中。最後選「放棄變更」：編輯器關閉，檔案不變 | 編輯器直接關閉，`x` 遺失 |
| 100 | 開啟 `alpha`；按 Esc。再開啟；刪除第 1 列（沒有對話框）；按取消 | 第一次 Esc 直接關閉，沒有對話框；刪除不詢問；取消出現 D7 對話框 | 取消直接關閉 |
| 101 | `twins.csv`（`text,braille,type,note`／`a,⠁,General,first`／`b,⠃,General,`／`a,⠁,General,third`）：新增 `b` | 錯誤訊息 來源文字「b」已存在。，擁有者是**詞條對話框**；按確定後詞條對話框仍開著，`b` 與 `⠃` 保留，焦點在「來源文字」且 `b` 已全選（UIA `TextPattern` 的選取）；改成 `c` 再按確定：新增成功 | 詞條對話框先關閉，再出現錯誤；輸入遺失 |
| 102 | `twins.csv`：(1) 選第 3 列，編輯，把點字改成 `⠉`，按確定；再按取消並選「放棄變更」。(2) 再開啟，選第 3 列，刪除，按確定 | (1) 編輯被接受（第 3 列顯示 `a`、`⠉`）。(2) 檔案為 `a,⠁,General,first`／`b,⠃,General,`：刪掉的是選取的那一列，第 1 列保留它的 `note` | (1) 被當成重複而拒絕；(2) 檔案保留 `third`，`first` 消失（刪掉的是第一筆相等的列） |
| 103 | `dict_badbopo`：新增 `肚子`／`ㄉㄨˋㄗ˙`／注音；按確定；移除並儲存 | 新增被接受；D1 對話框列出第 3、4 列；檔案為 `臺北` 與新的 `肚子,ㄉㄨˋㄗ˙,Bopomofo` | 新增被拒絕（F-4 D5） |
| 104 | 在設定選 `alpha`；字典管理中改名為 `Alpha` | 沒有訊息；清單顯示 `Alpha` 並選取；`dictionary\Alpha.csv`；`config.json` 的 `selected_dictionary` 為 `Alpha`；轉換仍使用它 | 字典「Alpha」已存在。 |
| 105 | 以 share-none 鎖住 `src.csv`（`lock.py`）；匯入它 | `匯入字典失敗：無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。`；`dictionary\` 中沒有新檔案 | `[Errno 13] Permission denied: ...` |
| 106 | （D14，依使用者 2026-10-11 的決定；`auto/item106.py`，「規劃後的修正（F-11）」12）`tone1.csv` 含 `中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo` 與 `抹,ㄇㄚ,Bopomofo`；轉換 `中心抹末`；開啟；新增 `末`／`ㄇㄚ`，再新增 `末`／`ㄇㄚ `；按確定、返回編輯；按確定、移除並儲存；再轉換一次 | 有空白的那一列有顯示，沒有空白的被隱藏；第一次轉換用到 `中心`、沒有用到 `抹`（預設讀音）；`ㄇㄚ` 出現格式錯誤，`ㄇㄚ ` 被接受；按確定列出 `第 3 列：「抹」的注音「ㄇㄚ」格式不正確`；返回編輯時檔案不變；移除並儲存後檔案含 `中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo` 與 `末,ㄇㄚ ,Bopomofo`；第二次轉換用到 `中心` 與 `末` | 兩列都被隱藏；兩次新增都出現格式錯誤；按確定時沒有確認框、編輯器關閉、檔案不變；兩次轉換都用到 `中心` 與 `抹`（經由 fallback，`⠍⠜`） |
| 108 | （審查 M-1，審查修正新增）`caps.csv`（`Text,Braille,Type`／兩列）與 `blank1.csv`（第一行空白、`text,braille,type`、一列）：分別開啟；按確定；新增 `戊己`／`⠑⠋`，按確定；取消、放棄變更 | 清單是空的；每次按確定：錯誤框 `無法儲存字典「caps」：無法辨識檔案的表頭。…`，owner 是編輯器，沒有 D1 確認框，編輯器保持開啟，檔案的位元組與修改時間不變，焦點回到「確定」；新增後按取消：D7 確認框；放棄變更後關閉；檔案不變，字典管理 `0` | 按確定就關閉編輯器並把檔案改寫成 `text,braille,type` 與每列一個 `,,`（各列的值不見了）；新增後是 `,,`／`,,`／`戊己,⠑⠋,General`，筆數 `1` |

以新的預期重跑（需要寫檔時，腳本先做一次修改）：

- **23：** `dict23` 沒修改按確定：不寫檔。編輯後：寫檔，BOM 與原本相同。
- **24：** 有 BOM 的檔案沒修改按確定：不變。編輯後：BOM **保留**。
- **25～29：** 都先編輯一列讓「確定」會寫檔，再做原本的鎖定、屬性、ACL 檢查；預期的 `SAVED` 狀態保留檔案的 BOM。
- **35：** 35a 出現 D1 確認框（先返回編輯，再移除並儲存）；35b 的新增被接受（D2）；35c、35d 依此類推。

F-6 的項目 42～51 不變；因為編輯器改為先讀檔，重跑 44 與 47。

**給使用者的手動項目（項目 107，NVDA）：** 以 `N-f11`，開著 NVDA：

1. 項目 95 的確認框：整份清單有沒有讀出來？焦點是否在「返回編輯」？
2. 項目 99 的確認框：按 Esc 回到編輯器，焦點在哪裡？
3. 項目 101：重複訊息之後，NVDA 是否讀出「來源文字」與選取的文字？
4. 「移除並儲存」之後，焦點是否回到主視窗？

## 風險

- **既有字典的轉換結果改變**（中，U6 的本意）。只有空白的規則與不合法的注音規則不再生效。下次按「確定」時，D1 確認框會列出它們。發布說明應提到這點。
- **最後一個音節是一聲的列（O1，已決定 (b)；審查 I-1 由使用者於 2026-10-11 決定）**（低）。有聲調空白的列照舊顯示並用於轉換。存檔時沒有聲調空白、或最後一個音節後面還有空白的列，以前經由 fallback 成為規則；現在會被隱藏、按「確定」時列出、轉換忽略它們，所以它們的轉換結果會改變。開頭有空白的列，現在轉換時不再把那些空白當成符號。詞條對話框會拒絕沒有聲調空白、或聲調符號後面還有空白的注音。版本說明應該寫出這些改變。
- **trace 重播是調整過的，不是重新錄製**（低）。重播會拿掉並回答 D1 確認框的記錄。這個調整若有錯，可能掩蓋 OK 步驟的退化。測試 C3 另外單獨檢查 OK 步驟。
- **選取規則分成兩種**（低）。新增／取代後用 identity，刪除／篩選後用相等。只有完全相同的列時才有差別。保留相等是因為 golden trace 固定了它（探針 1）。
- **`csv.reader` 的一致性**（低）。與 `DictReader` 不一致會改變哪些列被隱藏。測試 A3 對每份語料比對兩者。
- **確認框的文字長度**（低）。10 行加上很長的來源文字，一般對話框可能很高。列數上限限制了它的高度。
- **一般對話框與 NVDA**（低）。兩個確認框是傳統對話框，不是 task dialog；如果 NVDA 只讀出標題和有焦點的按鈕，使用者聽到的清單會比較少。由手動項目 107 確認。
- **wx 的 Esc 處理改變**（低）。若 wx 不再把關閉鈕轉成點擊取消，就不會詢問。項目 99、100 在 packaged build 上檢查 Esc、取消與 Alt+F4。

## 待決問題

**使用者已決定：**

- **O1. 最後一個音節是一聲的注音列。使用者於 2026-10-11 決定：(b)。** 現在編輯器會隱藏它們，因為去空白把聲調空白也去掉了（探針 4）。轉換會使用它們。詞條對話框無法輸入它們。依目前寫下的 U1 與 U6：
  - **(a)** 轉換開始忽略它們，按「確定」時以「格式不正確」列出等待移除；
  - **(b)（建議）** 去空白時保留最後的一聲空白（D14）。它們會顯示、可以編輯、存檔時保留空白、轉換與現在相同；輸入時沒打最後的空白也會被接受。
  plan 實作 (b)（D14，plan 的 Task 6）；GUI 項目 106 列入範圍。審查 I-1 之後，使用者決定（2026-10-11）只去掉開頭的空白：聲調空白必須在檔案中或由使用者輸入，沒有聲調空白的列不合法（D14）。
- **O13. 轉換使用哪些注音列、用哪個值（plan 新增）。使用者於 2026-10-11 決定（審查 I-1）：** 正好是編輯器顯示的列，以編輯器顯示的注音（`target.lstrip()`）轉換，沒有 fallback。plan 的預設（先解析原始值，編輯器會顯示的列保留 fallback）不再使用（「規劃後的修正（F-11）」6）。
- **O12. 兩個確認框（規劃時發現）。使用者於 2026-10-11 決定：使用傳統對話框（`wx.GenericMessageDialog`）。** 從編輯器顯示時，使用自訂按鈕文字的原生 task dialog 會把 Alt+F4 當成按下「確定」（「規劃後的修正（F-11）」3）。硬性要求：Esc、Alt+F4 與關閉鈕絕不能觸發「移除並儲存」或「放棄變更」。

**協調者依建議預設決定；使用者可在 merge 前推翻：**

- **O2.** 「有修改」比對依序排列的詞條值與載入時的值，不用「已修改」旗標（D3）。
- **O3.** D1 確認框最多列出 10 列，之後接 `Other rows not listed: {count}`（D1）。
- **O4.** 「移除並儲存」失敗後，下次按「確定」會再問一次（D1）。
- **O5.** 編輯過的列保留多出欄位的值（D5）。U2.3 只提到沒修改的列與新增的列。
- **O6.** 編輯兩列相同的列中的一列並保留來源文字，不算重複（D9，補完 P2-2 Q4）。
- **O7.** 只有匯入來源的 `PermissionError` 改用友善說明。來源的其他 `OSError` 與目的地錯誤維持原始文字（D11）。
- **O8.** 隱藏列的行號以檔案行數計算，表頭為第 1 行（D1）。
- **O9.** 寫檔時換行維持 CRLF、引號維持最少（D5）。使用者只決定了 BOM。
- **O10.** 刪除與篩選後的選取維持相等比對（D9）。
- **O11.** 檔案不存在時，沒修改按「確定」不再建立它（D4）。

## 本 spec 新引入的使用者可見預設（不是使用者的決定）

以下不在 U1～U6 中。使用者若想要別的做法，每一項都只需改一行：

1. **隱藏列確認框的按鈕文字：** 移除並儲存(&S)／返回編輯(&B)，而不是 `task.md` 敘述中的 是／否。是／否 的 task dialog 無法用 Esc 關閉（探針 2）。
2. **隱藏列確認框的預設按鈕**是「返回編輯」。
3. **標題：** 移除無法顯示的列、尚未儲存的變更。**訊息文字：** 字串 2、3、4、9，兩個確認框都提到字典名稱。
4. 按鈕上的**快速鍵** (S)、(B)、(D)，沿用 F-5 的 `重試(&R)`。
5. **列號＝檔案行號**，表頭為第 1 行（O8）。**每一列的說明除了來源文字，也列出不合法的注音。**
6. **最多列出 10 列**，以及 `另有 {count} 列未列出` 那一行（O3）。
7. 「返回編輯」後，**焦點還原**到對話框出現前有焦點的控制項（D7）。
8. **編輯器的一般失敗訊息** `無法開啟字典編輯器：{error}`（D12）。
9. **接受編輯分身**（O6），以及**新增／取代後以 identity 選取**（D9）。
10. **「移除並儲存」失敗後再問一次**（O4）。
11. **表頭無法辨識的字典，「確定」不儲存：** 顯示字串 12，編輯器保持開啟（「審查後的修正（F-11）」1）。使用者已接受（2026-10-11）。
12. **寫檔補上必要欄位時，超出表頭的欄位往右移**（「審查後的修正（F-11）」2）。使用者已接受（2026-10-11）。

## 範圍外／後續項目

- DotExpress 建立的字典加上 BOM（U2.4 的後續項目）。
- 在編輯器中顯示隱藏列，或在字典管理的筆數中計入隱藏列。
- 既有的 是／否 確認框（「確認刪除字典」等）的 Esc：是／否 的 task dialog 會忽略 Esc（探針 2）。這是既有問題；F-12。
- 其他訊息的本地化與 F-6 O5 轉換錯誤的用詞（F-12）。
- F-10（UEB 斷行、`$` 跳脫）。
- 手動編輯的檔案中混用的換行或引號風格不會保留（O9）。
- 檔案中原本就存在的重複來源文字不會提示。轉換仍使用第一條。
