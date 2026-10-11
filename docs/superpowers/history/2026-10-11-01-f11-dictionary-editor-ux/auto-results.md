# F-11 Windows 驗證：自動化執行結果（plan Task 12；項目 95–106，重跑 23–29、35、44、47；審查修正階段：項目 108 與重跑）

- 日期：2026-10-11，由 Claude 執行
- 受測：`fix/f11-dictionary-editor-ux` 在 Task 10 之後（`5d5f2fd`，`HEAD:client` `0d0f93c8340a7ca86bcaf46775b7970ad90b4935`，與 plan Task 10 Step 4 的 tree id 相同）的 packaged build，以下稱 N-f11。十個 client commit 的 tree id 都與 plan 相同：Task 1 `a02fe0a` `18b797eb…`、Task 2 `d585aa4` `3c987c09…`、Task 3 `5dc8bfe` `eafdc94c…`、Task 4 `bc7368a` `8c7487cb…`、Task 5 `19fe19d` `b2cfda10…`、Task 6 `8b9804f` `6c3946d1…`、Task 7 `2f6e70d` `8dcde92c…`、Task 8 `1df105f` `b3da7431…`、Task 9 `f9e66d6` `239eaf1d…`、Task 10 `5d5f2fd` `0d0f93c8…`。
- 改前對照：`D:\dxtest\N-f9b\DotExpress.exe`（F-9 審查修正後的 build，`HEAD:client` `a64da653…`，即 `1ce6ce5` 的程式；48,765,092 bytes，sha256 `B5AD9BFA9DA0C73F87C8FA547C1E7BDD1771A50E142E14EE1D86F37DD1AB83DD`），只讀取並由腳本複製到各自的資料夾；執行後 sha256 不變。
- 項目分類（使用者，2026-10-11）：**fix** 項目是兩個 build 的預期結果不同，或項目經過的程式碼有改動；**regression** 項目兩者都不是。fix 項目在 N-f11 與 N-f9b 都執行；regression 項目只在 N-f11 執行，結果不符預期時才也在 N-f9b 執行。F-11 的每個項目都是 fix：95–106 的預期結果在兩個 build 不同；重跑的 23–29、35 的預期結果不同（BOM、不寫入、隱藏列的對話框）；44、47 的預期結果相同，但經過 D12 改動的程式碼（編輯器在建立視窗前讀取字典）。所以沒有 regression 項目，全部在兩個 build 上執行。
- 方法：pywinauto 0.6.9（win32 backend）＋ psutil，venv 在 `$SP\uia`。wx 的訊息框（`ui.message_box`）是 task dialog，F-11 的兩個確認框（`confirm_box`）是 wx 的一般對話框，都用 UIA 讀取：task dialog 寫成 `{'title', 'text', 'buttons', 'focus', 'owner'}` 或 `('標題', [內容…, 按鈕])`，一般對話框寫成 `{'title', 'text': [每行一項], 'buttons', 'focus', 'owner'}`；`owner` 是擁有該對話框的視窗標題。按鈕以 `set_focus` 後送 `BM_CLICK` 按下（焦點留在按鈕上，與點按相同）；按鍵都經過 `f11gui.keys`／`f5gui.answer`：先確認受測程式的視窗是前景視窗才送出。`{'bytes': …, 'time': …}` 表示檔案的內容與修改時間是否保持不變；BOM 寫成 `<BOM>`；`<d>` 是該項目的工作資料夾，`<rnd>` 是暫存檔名稱的亂數部分。每個項目都在新的 `D:\dxtest\auto<N>-f11`（N-f11）或 `D:\dxtest\auto<N>-f9b-f11`（N-f9b）資料夾執行，exe 複製到該資料夾再啟動。依 plan Task 12 Step 3 的迴圈一次只跑一個項目；因為這台機器的記憶體不多，每個項目開始前先確認可用記憶體至少 1 GB，不足時等待（等待只延後開始時間，不影響結果）。沒有動到 `D:\dxtest\N`、`B`、`N-p25`、`N-f3`、`N-f4*`、`N-f5*`、`N-f6*`、`N-f7`、`N-f8a*`、`N-f8b*`、`N-f9`、`N-f9b` 與既有的 `D:\dxtest\auto*` 資料夾。只結束 exe 位於這些資料夾的程序（`dx.kill_under`）；`lockx.py`、`lock.py` 以 `taskkill /T` 結束。結束後沒有殘留的 DotExpress 程序。沒有任何腳本讀寫剪貼簿：文字只經由檔案與 `set_edit_text` 進入程式。
- 腳本：`auto/item95.py`（95、96）、`auto/item97.py`（97、98）、`auto/item99.py`（99、100）、`auto/item101.py`（101、102）、`auto/item103.py`（103、106）、`auto/item104.py`（104、105）、`auto/rerun23.py`（23、24）、`auto/rerun25.py`（25–29）、`auto/item35.py`（35），共用 `auto/f11gui.py`；44、47 以 F-6 的 `item42.py`（42–45）與 `item47.py` 執行，未修改。沿用 F-6 的 `f6gui.py`、`lockx.py`，F-7 的 `f7gui.py`，F-5 的 `f5gui.py` 與 2026-10-09-03 的 `dx.py`、`docs.py`、`dicts.py`、`lock.py` 及其 `data`（都未修改）。腳本由 plan Task 12 Step 2 的 `apply_blocks.py` 寫入。輸出在 `D:\dxtest\auto<N>-f11.log` 與 `D:\dxtest\auto<N>-f9b-f11.log`（UTF-8，從 Git Bash 執行）。
- 22 個 log（11 個腳本 × 2 個 build）中有 19 個第一次就與 plan Task 12 Step 4 的預期一致。三個 N-f9b 的項目因為工具問題中斷，依 plan 在新資料夾重跑，重跑的 log 與預期一致：`auto97-f9b-f11` 與 `auto101-f9b-f11` 在開啟「字典管理」時 `SetForegroundWindow` 失敗（`pywintypes.error`；執行期間使用者正在使用桌面上的其他程式，Windows 拒絕把受測程式帶到前景），重跑為 `auto97b-f9b-f11`、`auto101b-f9b-f11`；`auto44-f9b-f11` 在最後一步（`big5.csv` 改成 UTF-8 後按「編輯」）等不到編輯器視窗（`RuntimeError: no window 自訂字典管理器`），之前的 19 行與 N-f11 的 log 相同，重跑為 `auto44b-f9b-f11`，整個 log 與 `auto44-f11.log` 相同（資料夾名稱除外）。N-f11 的 11 個項目都沒有重跑。

## 0. Packaged build

| 版本 | 結果 |
| --- | --- |
| N-f11 | worktree `D:\workspace\DotExpress-f11`（`5d5f2fd`），主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面（`pyinstaller` 是 `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`）；PyInstaller 6.21.0（Python 3.13.15），`scripts\build-dotexpress.bat` 約 54 秒，log 有 `Build complete!`。`client\build\DotExpress\PYZ-00.toc` 的 `dialog.py`、`dictionaries\entries.py`、`dictionaries\entry_list_model.py`、`dictionaries\manager.py`、`dictionaries\presenter.py`、`ui\message_box.py`、`conversion\text\dictionary_rules.py` 與 `Analysis-00.toc` 的 `gui.py` 都來自 `DotExpress-f11\client\`。`D:\dxtest\N-f11\DotExpress.exe`，48,778,355 bytes，sha256 `3CEC35CE8A5C2102EC9CA1D9B8EC911B815B1F5B2DBBFF20D7E8BF01F46CC355`。`git status --short -- client scripts` 無輸出（build 產物都是 git-ignored）。`.mo` 經由 `--add-data "locales;locales"` 打包，95、99、103、105 顯示新的字串 |

## 95–106. F-11 項目（全部是 fix 項目）

D1 對話框（`移除無法顯示的列`）的內容，下文稱「D1 框」：`{'title': '移除無法顯示的列', 'text': ['字典「dict_badbopo」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：', '第 3 列：「肚子」的注音「ㄉㄨˋ|ㄗ˙」格式不正確', '第 4 列：「數學」的注音「ㄕㄨˋ ㄒㄩㄝˊ」格式不正確', '要移除這些列並儲存字典嗎？'], 'buttons': ['移除並儲存(S)', '返回編輯(B)'], 'focus': '返回編輯(B)', 'owner': '自訂字典管理器'}`。D7 對話框，下文稱「D7 框」：`{'title': '尚未儲存的變更', 'text': ['要放棄對字典「<名稱>」所做的變更嗎？'], 'buttons': ['放棄變更(D)', '返回編輯(B)'], 'focus': '返回編輯(B)', 'owner': '自訂字典管理器'}`。

| # | 分類 | N-f11（改後） | N-f9b（改前） |
| --- | --- | --- | --- |
| 95 ✔（D1） | fix | `auto95-f11`：匯入 `dict_badbopo.csv`（與來源相同，字典管理顯示 `1`）。編輯器只列 `臺北`；按「確定」：**D1 框**（第 3、4 列）。在框中按 Esc、Enter、Alt+F4：每次都 `windows ['自訂字典管理器']`（編輯器仍開著）、`file {'bytes': True, 'time': True}`、焦點回到 `('Button', '確定')`。再按「確定」、Alt+S：編輯器關閉，檔案 **`text,braille,type\r\n臺北,⠞⠺,Braille\r\n`**，字典管理仍是 `1` | `auto95-f9b-f11`：按「確定」沒有任何框，編輯器立即關閉，檔案內容相同但修改時間改變（`{'bytes': True, 'time': False}`，F-4 的重寫）；之後每一步都是 `box None`、`windows []`，檔案一直保有兩列隱藏列。此時讀到的焦點是其他程式的元素（編輯器已關閉，使用者正在使用桌面；不屬於改前的預期） |
| 96 ✔（D13） | fix | 同一個 log：以 `dict_badbopo` 轉換 `肚子數學`，存檔前 `'⠙⠌⠐⠓⠱⠁⠊⠌⠐⠑⠦⠂'`，**與 `default` 相同**（`equal: True`）；Alt+S 存檔後相同（`equal to default: True`） | 存檔前後都是 `'⠙⠌⠐⠳⠓⠁⠊⠌⠐⠄⠑⠦⠂'`，使用了兩條注音規則，與 `default` 的 `'⠙⠌⠐⠓⠱⠁⠊⠌⠐⠑⠦⠂'` 不同 |
| 97 ✔（D4） | fix | `auto97-f11`：`extra.csv`（BOM、`text,note,braille,type`、` Alpha ,first, ⠁ ,Custom`、CRLF），編輯器列 `Alpha`、`Beta`；不修改就按「確定」：沒有框，**`{'bytes': True, 'time': True}`**，檔案仍是 `'<BOM>text,note,braille,type\r\n Alpha ,first, ⠁ ,Custom\r\nBeta,second,⠃,General\r\n'` | `auto97b-f9b-f11`（第一次 `auto97-f9b-f11` 的這一步相同，之後中斷，見上）：按「確定」就重寫：`{'bytes': False, 'time': False}`，`'text,braille,type\r\nAlpha,⠁,General\r\nBeta,⠃,General\r\n'`（BOM 與 `note` 欄都不見了） |
| 98 ✔（D5） | fix | 編輯第 1 列（點字改成 `⠁⠁`）並新增 `Gamma`／`⠛`：**`'<BOM>text,note,braille,type\r\nAlpha,first,⠁⠁,General\r\nBeta,second,⠃,General\r\nGamma,,⠛,General\r\n'`**（BOM、標題、`note` 保留，新列的 `note` 是空的，每列都去掉空白，`Custom` 寫成 `General`）。`bom_lf.csv`（BOM、LF）編輯後：**`'<BOM>text,braille,type\r\n戊己,⠑⠋⠁,Braille\r\n'`**（保留 BOM，換行變成 CRLF；spec 修正 12） | `extra.csv`：`'text,braille,type\r\nAlpha,⠁⠁,General\r\nBeta,⠃,General\r\nGamma,⠛,General\r\n'`；`bom_lf.csv`：`'text,braille,type\r\n戊己,⠑⠋⠁,Braille\r\n'`（都沒有 BOM，`note` 欄不見了） |
| 99 ✔（D3、D7） | fix | `auto99-f11`：`alpha` 新增 `x` 後：在編輯器按 Esc → **D7 框**（`alpha`）；框中按 Esc：回到編輯器，`x` 仍在，焦點 `('ListItem', 'x')`。按「取消」→ D7 框；按框的關閉鈕：回到編輯器，焦點 `('Button', '取消')`。在編輯器按 Alt+F4 → D7 框；Alt+D：編輯器關閉，焦點回到主視窗的 `('Edit', '來源文字')`。檔案一直 `{'bytes': True, 'time': True}` | `auto99-f9b-f11`：Esc、「取消」、Alt+F4 都沒有框，編輯器立即關閉，`x` 不見了；檔案不變 |
| 100 ✔（D3） | fix | 沒有修改時按 Esc：沒有框，編輯器立即關閉。再開啟，刪除第 1 列：沒有詢問，列表剩 `丙丁`；按「取消」→ D7 框；Alt+D：關閉，檔案不變 | 沒有修改時相同；刪除後按「取消」沒有框，編輯器立即關閉 |
| 101 ✔（D8） | fix | `auto101-f11`：`twins.csv` 新增 `b`：錯誤框 **`來源文字「b」已存在。`，owner `新增字典項目`**；按 Enter 後新增對話框仍開著，欄位 `('b', '⠃', '一般')`，焦點 `('Edit', '來源文字')`，選取 `(0, 1)`；改成 `c` 按「確定」：新增成功（第 4 列 `c`）。「取消」→ D7 框（`twins`），檔案不變 | `auto101b-f9b-f11`（第一次 `auto101-f9b-f11` 在開啟字典管理時中斷，見上）：錯誤框的 owner 是 `自訂字典管理器`，新增對話框已關閉，輸入的內容不見了；列表不變；「取消」沒有框 |
| 102 ✔（D9） | fix | (1) 選第 3 列（`a`）編輯，點字改成 `⠉`：接受，列表第 3 列是 `a`／`⠉`；「取消」→ D7 框，放棄。(2) 選第 3 列刪除：列表剩 `a`、`b`；「確定」：**`'text,braille,type,note\r\na,⠁,General,first\r\nb,⠃,General,\r\n'`**（刪掉的是選取的列，第 1 列保留 `first`） | (1) 錯誤框 `來源文字「a」已存在。`，編輯被拒絕。(2) 刪除後列表是 `b`、`a`（刪掉的是第一個 `a`），檔案 `'text,braille,type\r\nb,⠃,General\r\na,⠁,General\r\n'`（`note` 欄不見了） |
| 103 ✔（D2、D1） | fix | `auto103-f11`：`dict_badbopo` 新增 `肚子`／`ㄉㄨˋㄗ˙`：沒有框，接受；按「確定」：**D1 框**（第 3、4 列）；Alt+S：**`'text,braille,type\r\n臺北,⠞⠺,Braille\r\n肚子,ㄉㄨˋㄗ˙,Bopomofo\r\n'`** | `auto103-f9b-f11`：新增被拒絕（`來源文字「肚子」已存在。`，owner `自訂字典管理器`，F-4 D5）；「確定」沒有框，檔案保有兩列隱藏列 |
| 104 ✔（D10） | fix | `auto104-f11`：`alpha` 在設定中被選取，改名為 `Alpha`：**沒有框**；列表 `[['Alpha', '2', 'selected'], ['default', '0']]`，檔案 `Alpha.csv`，`config.json` 是 `Alpha`；轉換 `甲乙` 得 `'⠁⠃'`（使用這個字典） | `auto104-f9b-f11`：`字典「Alpha」已存在。`，名稱對話框再次出現（腳本取消）；仍是 `alpha.csv`，`config.json` 是 `alpha` |
| 105 ✔（D11） | fix | 檔案對話框關閉後，`lock.py` 以不共用方式鎖住 `src.csv`：**`匯入字典失敗：無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。`**；`dictionary\` 沒有新檔案 | `匯入字典失敗：[Errno 13] Permission denied: '<d>\\data\\src.csv'`；沒有新檔案 |
| 106 ✔（D14） | fix | 同 `auto103-f11`：`tone1.csv` 的 `中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo` 顯示為 `['中心', 'ㄓㄨㄥˋㄒㄧㄣ ', '注音']`（保留聲調空白）；新增 `抹`／`ㄇㄚ`：接受，顯示並存成 `ㄇㄚ `；檔案 `'text,braille,type\r\n中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo\r\n抹,ㄇㄚ ,Bopomofo\r\n'`；以 `tone1` 轉換 `中心抹`：**`'⠁⠯⠐⠑⠹⠄⠍⠜⠄'`**（兩條規則都使用），`default` 是 `'⠁⠯⠄⠑⠹⠄⠍⠣⠈'` | 該列被隱藏（列表空的）；新增 `抹` 時新增對話框中出現 `請輸入有效的注音序列。`；檔案不變；轉換 `'⠁⠯⠐⠑⠹⠄⠍⠣⠈'`（只使用 `中心` 的規則） |

## 重跑 23–29、35、44、47（全部是 fix 項目）

| # | 分類 | N-f11（改後） | N-f9b（改前） |
| --- | --- | --- | --- |
| 23、24 ✔（D4、D5） | fix | `autorerun23-f11`：匯入 `dict23`、`bom_excel`、`bom_notepad`、`bom_lf`。不修改就按「確定」：四個都 **`{'bytes': True, 'time': True}`**。第 1 列加上 `⠿` 後：`dict23` 沒有 BOM（與原檔相同），**`bom_excel`、`bom_notepad`、`bom_lf` 保留 `<BOM>`**，都是 CRLF；`dict23` 的 `逗號,"a,b",General` 保持引號。以各字典轉換：`'⠁⠃⠿'`、`'⠉⠙⠿'`、`'⠑⠋⠿'`（使用字典） | `autorerun23-f9b-f11`：不修改就按「確定」也重寫（`{'bytes': False, 'time': False}`）；編輯後三個 BOM 檔都沒有 BOM；轉換結果相同 |
| 25–29 ✔（D4、D5，F-2 的寫入路徑） | fix | `autorerun25-f11`：25 以共用讀取鎖住：存檔錯誤 `儲存失敗：[WinError 5] 存取被拒。: '<d>\\dictionary\\.bom_lf.csv.<rnd>.tmp' -> '<d>\\dictionary\\bom_lf.csv'`（owner `自訂字典管理器`），編輯器仍開著，檔案 `ORIG`，沒有 `.tmp`；解除鎖定後 **`SAVED(⠑⠋⠁)`**（保留 BOM）。26 唯讀：`儲存失敗：[Errno 13] Permission denied: '<d>\\dictionary\\bom_lf.csv'`，`-r` 後 `SAVED`。27 隱藏：`SAVED`，屬性只剩 `A`（與改前相同）。28 十次存檔：**`failures: 0`**。29 存檔前有 deny 項目，存檔後檔案被取代、deny 項目消失，`SAVED` | `autorerun25-f9b-f11`：錯誤訊息、編輯器狀態與屬性都相同，但每個存好的檔案都沒有 BOM（`OTHER 'text,braille,type\r\n戊己,⠑⠋⠁,Braille\r\n'`），所以 28 是 `failures: 10`（這是腳本檢查 BOM 的失敗；每次存檔本身都成功） |
| 35 ✔（D1、D2、D13） | fix | `auto35-f11`：35a 按「確定」：**D1 框**；Alt+B：編輯器仍開著，檔案 `{'bytes': True, 'time': True}`；再按「確定」、Alt+S：`'text,braille,type\r\n臺北,⠞⠺,Braille\r\n'`；轉換前後都是 `'⠙⠌⠐⠓⠱⠁⠊⠌⠐⠑⠦⠂'`（隱藏列本來就不是規則）。35b 新增 `肚子`：接受並寫入。35c 刪除 `臺北`、確定：只剩 `肚子`，字典管理 `1`。35d 重新啟動後 `1`、列 `肚子`，「取消」沒有框直接關閉 | `auto35-f9b-f11`（F-4）：沒有框，檔案保有隱藏列；轉換使用注音規則（`'⠙⠌⠐⠳⠓⠁⠊⠌⠐⠄⠑⠦⠂'`）；35b 新增被拒絕；35c 留下兩列隱藏列（字典管理 `0`）；35d `0`、沒有列 |
| 44 ✔（F-6 `item42.py`，D12） | fix | `auto44-f11`：無法讀取的 `big5` 列、原因、Tab 順序（42、43、45）與 F-6 相同；選 `big5` 按「編輯」：`('錯誤', ['無法讀取字典「big5」。', '檔案不是以 UTF-8 儲存。…', '確定'])`，字典管理仍開著，`gui.log` 兩行；改成 UTF-8 後按「編輯」：編輯器開啟，列 `[['臺北', 'ㄊㄞˊㄅㄟˇ', '注音']]`；取消後沒有視窗、沒有框；重新開啟：`[['big5', '1'], ['default', '0', 'selected']]` | `auto44b-f9b-f11`（第一次 `auto44-f9b-f11` 在最後一步中斷，見上）：與 `auto44-f11.log` 逐行相同 |
| 47 ✔（F-6 `item47.py`，D12） | fix | `auto47-f11`：鎖住時 `alpha` 是「無法讀取」，原因 `無法開啟檔案。…`；解除鎖定後按「編輯」：沒有框，編輯器開啟，列 `[['Alpha', '⠁', '一般']]`；`alpha.csv` 不變；`gui.log` 一行 `PermissionError` | `auto47-f9b-f11`：與 `auto47-f11.log` 逐行相同（`gui.log` 那一行的資料夾名稱除外） |

## 結論

- 所有自動化項目（95–106、重跑的 23–29、35、44、47）在兩個 build 上的結果都與 plan Task 12 Step 4 的預期一致。三個 N-f9b 的項目因工具問題（前景視窗、視窗等待）重跑一次，見上；N-f11 沒有重跑。
- D1、D13：有隱藏列時「確定」先顯示 D1 框，列出各列在檔案中的起始行號與原因；Esc、Enter、Alt+F4 都回到編輯器，不移除、不寫入（使用者的硬性要求：Esc、Alt+F4、關閉鈕絕不觸發「移除並儲存」或「放棄變更」），焦點回到「確定」；只有 Alt+S（移除並儲存）寫入。轉換不再使用編輯器隱藏的列（95、96、35）。
- D3、D4、D7：沒有修改時「確定」不寫入（97、23、24）；有修改時 Esc、「取消」、Alt+F4 都先顯示 D7 框，Esc 與關閉鈕回到編輯器，只有 Alt+D 放棄（99、100）。
- D5：檔案的 BOM、標題與額外欄位保留，新列的額外欄位是空的；寫入時換行是 CRLF（98、23、25–29）。
- D8、D9：重複的來源文字在新增對話框中報告，輸入保留並選取（101）；編輯與刪除作用在選取的那一列（102）。
- D2、D14：與隱藏列同名的新增被接受（103、35b）；一聲結尾的注音保留聲調空白，輸入時沒打空白也接受（106）。
- D10、D11：只改大小寫的改名成功，設定跟著改（104）；被鎖住的匯入來源顯示 F-6 的原因（105）。
- D12：44、47 的結果與改前相同。

## 觀察（非 F-11 造成，不阻擋）

- **使用者同時使用桌面**：執行期間使用者在用其他程式（瀏覽器等）。`f11gui.keys` 只在受測程式是前景視窗時送出按鍵，所以沒有按鍵送到別的程式；但 pywinauto 的 `set_focus` 有兩次無法把受測程式帶到前景（`SetForegroundWindow` 失敗），一次等待視窗逾時，這三個項目都在新資料夾重跑。N-f9b 的 95 在編輯器關閉後讀到的焦點是其他程式的元素（改前的預期不包含焦點），log 中的那幾個元素名稱屬於使用者的其他程式，這裡不引用。
- **28 的 `failures: 10`（改前）**：是腳本檢查 BOM 的結果；改前的每次存檔都成功但去掉了 BOM（與 plan 的預期相同）。

## 審查修正階段（2026-10-11；審查 M-1、M-5）

- 受測：審查修正後的 `fix/f11-dictionary-editor-ux`（`976440f`，`HEAD:client` `0281ca0a8cc5f45142c732ae9f48896649bc5680`）的 packaged build，以下稱 **N-f11b**：`D:/dxtest/N-f11b/DotExpress.exe`，48,779,506 bytes，sha256 `41E7575DC2E36E191202635AB692616CC7E9130A41BB30923C11818A4C9AF039`。建置方式與上面的 N-f11 相同（主 checkout 的 `client/.venv/Scripts` 放在 `PATH` 最前面，`scripts/build-dotexpress.bat`，log 有 `Build complete!`，七個模組與 `gui.py` 都來自 worktree；建置前確認可用記憶體至少 1 GB）。改前對照仍是 N-f9b（sha256 `B5AD9BFA…`，執行後不變）。
- 改動的程式路徑：「確定」的處理（M-1：先檢查表頭），寫檔（M-5：補上的欄位放在超出表頭的欄位之前），以及模型讀檔時多帶一個 `header_recognized`。依分類規則，**fix 項目**是經過這些路徑、或預期結果不同的項目：95/96、97/98、101/102、103/106、35、23/24、25–29，以及新的 **108**（M-1），都在 N-f9b 與 N-f11b 上執行。**regression 項目**只在 N-f11b 執行：99/100（取消與 D7 框，經過讀檔）。104/105（改名、匯入）、44、47（開啟編輯器）經過的程式沒有改動（讀檔只多傳一個參數，每個項目開啟編輯器時都會經過），沒有重跑。
- 方法與上面相同，另外每個腳本都經由新的 `auto/safe_run.py` 執行：所有 `send_keys` 先確認前景視窗屬於該項目資料夾下的 DotExpress，否則 5 秒後停止腳本、不送出按鍵（`f5gui.answer` 原本在十次無法帶到前景後仍會送出）；`f11gui.focused` 在前景不是受測程式時記成 `('<another program>', '')`，所以 log 中不會有其他程式的元素名稱。腳本本身未修改。每個項目開始前確認可用記憶體至少 1 GB；結束後只結束 exe 位於該項目資料夾的 DotExpress。沒有任何腳本讀寫剪貼簿。資料夾 `D:/dxtest/auto<N>-f11b`（N-f11b）、`D:/dxtest/auto<N>-f9b-f11b`（N-f9b），log 在同名的 `.log`。

| # | 分類 | N-f11b（審查修正後） | N-f9b（改前） |
| --- | --- | --- | --- |
| 108 ✔（M-1，新項目，`auto/item108.py`） | fix | `auto108-f11b`：`caps.csv`（`Text,Braille,Type`、兩列）與 `blank1.csv`（第一行空白、`text,braille,type`、一列）字典管理都是 `0`，編輯器清單是空的。按「確定」：**`{'title': '錯誤', 'text': ['無法儲存字典「caps」：無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。'], 'buttons': ['確定'], 'focus': '確定', 'owner': '自訂字典管理器'}`**（`blank1` 相同，名稱為 `blank1`），沒有 D1 框；Enter 後編輯器仍開著，**`file {'bytes': True, 'time': True}`**，焦點 `('Button', '確定')`。新增 `戊己`／`⠑⠋` 後按「確定」：同一個錯誤框，檔案不變。「取消」→ D7 框（`caps`／`blank1`）；Alt+D：編輯器關閉，焦點 `('Edit', '來源文字')`。最後兩個檔案的位元組都與原檔相同（`'Text,Braille,Type\r\n甲乙,⠁⠃,Braille\r\n丙丁,⠉⠙,Braille\r\n'`、`'\r\ntext,braille,type\r\n甲乙,⠁⠃,Braille\r\n'`），字典管理 `0` | `auto108-f9b-f11b`：按「確定」沒有任何框，編輯器關閉，檔案被改寫（`{'bytes': False, 'time': False}`）；新增 `戊己` 再按「確定」後，兩個檔案都是 `'text,braille,type\r\n,,\r\n,,\r\n戊己,⠑⠋,General\r\n'`：原本各列的值都不見了（F-4 把隱藏列的空值寫回），字典管理 `1`。這是 F-11 之前就有的資料遺失；F-11 審查前的版本則會在 D1 框按「移除並儲存」後只留下表頭（審查 M-1） |
| 95、96 ✔ | fix | `auto95-f11b.log` 與 `auto95-f11.log` 逐行相同（資料夾名稱除外） | `auto95-f9b-f11b.log` 與 `auto95-f9b-f11.log` 相同（焦點欄位不比較：編輯器關閉後讀到的焦點可能屬於其他程式，新的 log 記成 `<another program>`） |
| 97、98 ✔ | fix | 與 `auto97-f11.log` 相同 | 與 `auto97b-f9b-f11.log` 相同 |
| 101、102 ✔ | fix | 與 `auto101-f11.log` 相同 | 與 `auto101b-f9b-f11.log` 相同 |
| 103、106 ✔ | fix | 與 `auto103-f11.log` 相同 | 與 `auto103-f9b-f11.log` 相同 |
| 35 ✔ | fix | 第一次 `auto35-f11b` 在 35d（重新啟動後按「取消」）時 `SetForegroundWindow` 失敗（`pywintypes.error`；使用者正在使用桌面），之前的 20 行與 `auto35-f11.log` 相同；在新資料夾重跑為 **`auto35b-f11b`**，整個 log 與 `auto35-f11.log` 相同 | 與 `auto35-f9b-f11.log` 相同 |
| 23、24 ✔ | fix | 與 `autorerun23-f11.log` 相同 | 與 `autorerun23-f9b-f11.log` 相同 |
| 25–29 ✔ | fix | 與 `autorerun25-f11.log` 相同（28 `failures: 0`） | 與 `autorerun25-f9b-f11.log` 相同 |
| 99、100 ✔ | regression | 與 `auto99-f11.log` 相同 | 未執行（regression 項目，結果符合預期） |

- 結論：M-1 修正後，表頭無法辨識的字典按「確定」只顯示錯誤、不提供移除、不寫入，檔案逐位元組不變（108）。其他重跑的項目在兩個 build 上的 log 都與第一次執行相同，M-1 與 M-5 的改動沒有影響表頭正常的字典。M-5 的情況（表頭缺少必要欄位且有超出表頭的欄位）只由單元測試涵蓋，GUI 項目沒有這種資料。
- 107（NVDA）仍是使用者的手動項目；可以用 N-f11b 進行（兩個確認框沒有改變）。

## 仍需人工（使用者）

> 107（NVDA）：請在 NVDA 執行中，把 `D:\dxtest\N-f11\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual107-f11\`，執行一次後關閉，把 `docs\superpowers\history\2026-10-09-03-windows-verification\auto\data\dict_badbopo.csv` 與 `alpha.csv`（`text,braille,type` / `甲乙,⠁⠃,Braille` / `丙丁,⠉⠙,Braille`）複製到 `D:\dxtest\manual107-f11\dictionary\`，再執行 DotExpress，開啟「字典管理」。(1) 編輯 `dict_badbopo`，按「確定」：「移除無法顯示的列」對話框是否讀出整段說明與兩列（第 3 列、第 4 列），焦點是否在「返回編輯」；按 Esc 後焦點回到哪裡。(2) 編輯 `alpha`，新增一筆後按 Esc：「尚未儲存的變更」對話框是否讀出問題與兩個按鈕；按 Esc 後是否回到編輯器、焦點在哪裡；再按 Alt+F4，在對話框中按 Alt+D 放棄變更。(3) 在 `alpha` 新增 `甲乙`（已存在）：「來源文字「甲乙」已存在。」之後，是否回到「新增字典項目」並讀出「來源文字」欄位與選取的文字。(4) 回到 (1) 按「移除並儲存」之後，焦點是否回到主視窗。這兩個確認框是 wx 的一般對話框（不是其他訊息框用的 task dialog），若 NVDA 只讀標題或按鈕、沒有讀出內容，請告訴我們。
