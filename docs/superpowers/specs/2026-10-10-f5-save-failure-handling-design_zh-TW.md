# 存檔失敗處理（F-5）設計

## 目標

任務 F-5 修正 F-W10 與 F-3 審查 M-4：開啟中的文件無法儲存時，app 仍應讓使用者離開這份文件或結束程式。

1. **F-W10**（`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`「新發現」）：開啟中文件的 `.dep` 是唯讀，或被另一個程式開著時，每個會先存檔的動作都會失敗，包括切換文件、改名、刪除、匯入、匯出與關閉。關閉被 veto，所以在鎖或屬性解除之前 app 無法結束。沒有修改的文件也會在這些動作前重寫，所以即使沒有東西要存也會遇到這個失敗。F-3（Q1 接受）之後，被**任何**共用模式開著的包都會讓存檔失敗（`[WinError 5]`），使 F-W10 更容易發生。
2. **F-3 審查 M-4**（`docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/review_task.md`）：記憶體中的 lone surrogate（通常來自貼上的文字）讓每次存檔都以 `'utf-8' codec can't encode character '\ud800' ... surrogates not allowed` 失敗。使用者看不到這個字元，所以無法修正。每個動作與關閉都一直被擋，唯一的出路是強制結束程序，這會丟掉上次成功存檔之後的所有修改。

使用者的決定（2026-10-10）：

- **A.** 開啟中的文件沒有變更時跳過寫入。比較基準是上次成功寫入磁碟（或從磁碟載入）的內容，另外記錄，絕不取自 controller。`save_open_document` 在寫入前就更新 controller，所以存檔失敗後 controller 已經持有未存的文字。
- **B.** 關閉時存檔失敗，顯示有**重試／不儲存就關閉／取消**的對話框。不儲存就關閉會捨棄上次成功存檔之後的修改。
- **C.** 其他每個動作在存檔失敗時仍以既有訊息擋下。有了 A，這只會在真的有變更時發生。
- **D.** 存檔時把 lone surrogate 換成 U+FFFD，存檔就一定能編碼。
- F-3 Q1 維持：被其他程式開著的包會擋住存檔。有了 A，這只在文件有變更時才有影響。

本任務完成後：

- service 為每份文件記住上次寫入或載入的內容，以及包的大小與修改時間。只有當準備好的文件與這份記錄不同，或磁碟上的包已不是記錄中的那一個時，存檔才寫入。記錄只在成功寫入或載入後改變，所以失敗的存檔會由下一個動作重試。
- 沒有變更的文件，即使其包是唯讀、被鎖、磁碟已滿或因其他原因無法寫入，也不再擋住切換、新增、匯入、匯出或關閉。改名與刪除仍對該包套用各自的規則：F-3 D7 拒絕改名唯讀的包，Windows 拒絕刪除唯讀的包。
- 關閉時存檔失敗，對話框顯示既有訊息（`Failed to save document: {error}`）、一句說明「不儲存就關閉會遺失上次成功存檔之後的修改」的文字，以及三個在地化的按鈕。重試是預設。
- 文字與點字不會帶著 lone surrogate 到達寫入器，所以這個錯誤不再發生。

新的使用者可見字串：4 個（msgid 353 -> 357），在 `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` 翻譯，並重新產生 `.pot` 與 `.mo`。

非目標：標題列的「已修改」標記、存檔命令、自動存檔、`.tmp` 殘留檔的回收（F 審查 M-2）、F-3 審查 M-1（新增、改名與匯入覆寫被保留的 invalid `.dep`）、依原因區分的訊息（被鎖 vs 唯讀）、刪除規則，以及含 lone surrogate 的文字的轉換。

## 規劃後更正（2026-10-10）

規劃（`docs/superpowers/plans/2026-10-10-f5-save-failure-handling.md`，已在 scratch clone 上 dry run：Task 0-4 完全重播，GUI 項目也以同一份程式碼的 build 執行過）沒有發現決策 D1-D11、行為表格或總數有錯。以下是計畫細化本規格之處，兩者不同時以本節為準。

1. **代理字元的 pattern 改用 raw string**：`re.compile(r"[\ud800-\udfff]")`。若照「各檔案的設計」寫成一般字串，`xgettext` 0.23（`scripts\generate-pot.bat` 會掃描每個 client 模組）每次執行都會對 `documents/workspace.py:24` 警告 U+D800 與 U+DFFF 是不合法的 Unicode 字元。`re` 會自行解讀 `\uXXXX` 跳脫，編譯出的 pattern 相同。
2. **`test_close_asks_presenter_before_saving` 多一個呼叫。** `_on_close` 會把 `evt.CanVeto()` 傳給 `_save_open_document_before_close`，所以存檔分支預期的呼叫是 `is_running(), event.CanVeto(), save(), close_converting_dialog(), event.Skip()`；測試計畫 C 所說「預期順序不變」不成立。該測試改 mock `_save_open_document`，它沒有回傳值。
3. **各遷移步驟的數量：`Ran 1277`、`1298`、`1304`**（新增 7 + 21 + 6 個測試），全程都是 `FAILED (errors=1, skipped=7)`，只有 F-W6。步驟 2 中，B2、B3、B5、B8、B9、B10、B15a 與 C3 在修改前就會通過（現在每次存檔都會寫入），用來守住「應寫入」的情況；其餘 13 個新測試是紅燈。
4. **測試細節。** B4 先確認未變更的待轉譯文件不會寫入，再模擬轉換。B11 有三個 subtest：空白文件、待轉譯的預設文件 `new`，以及文字與點字都含孤立代理字元的新文件（唯一確認紀錄保存的是 `_encodable(document)` 的測試）。B15b 的 controller 不經過 service 填入，因此只有「全部刪除」失敗後的重新載入能為剩下的文件建立紀錄。C1 直接呼叫 `_open_adjacent_document(1)`；C2 依序切換 alpha -> beta -> alpha 再關閉，讓關閉時開著的是唯讀的 alpha。假的對話框在沒有排定回答時回答「取消」。非 `OSError` 的重新命名測試使用本地的 `PackageFiles` 子類別，其 `write` 會丟出 `ValueError("injected")`。
5. **`wx_stub` 的值**：`ID_CANCEL = 5101`、`ID_YES = 5103`、`ID_NO = 5104`（與 wx 相同），`YES_DEFAULT = 1 << 27`。它們在遷移步驟 3 的紅燈階段與測試一起加入。
6. **翻譯檔。** `msgmerge` 會把 `Cannot Save Document` 標成 fuzzy，msgstr 借用 `Rename Document` 的翻譯，其餘三個新項目留空；計畫填入四個 msgstr 並移除該旗標。計畫在 `msgmerge` 之前把 `.pot` 的 `POT-Creation-Date` 固定為 `2026-10-10 12:00+0800`，讓 commit 可重現；`msgfmt` 0.23 不會把這個標頭放進 `.mo`。重新產生時也會更新 F-4 留下的 `dictionaries/entries.py` 過期行號，並移動 `Failed to save document: {error}`（第一個參照變成 `gui.py:465`）：`.pot` 與 `.po` 各為 57 行新增、38 行刪除，沒有 msgid 被移除，31 個過時（`#~`）項目不變。`.mo` 從 26,579 bytes 變成 26,971 bytes（358 個 catalog key）。
7. **Windows 驗證。** wx 的訊息框是 task dialog；`dx.dismiss` 讀得到內容，但它的 win32 點擊關不掉，而開著的訊息框會讓程序在關閉後仍然存活。F-5 的 `f5gui.py` 改用 UIA 按「OK」，18、19（含 20）、20b、33 的重跑透過新的 `rerun.py`，以它取代 `dx.dismiss`（先前的腳本，包括 F-3 的 `rerun.py`，都不修改）。送給剛出現的對話框的按鍵偶爾會遺失，所以 `f5gui.answer` 在 5 秒後若仍是同一個對話框，會再按一次。第 36、37 項共用 `item36.py`，第 38、39 項共用 `item38.py`。第 38 項「之前」欄中訊息框的按鈕是 `OK`（F-W9），不是 `確定`。*實作時未重現（審查 M-3）：* 原本的 `dx.dismiss` 每次都在第一次呼叫就關掉 wx 的 `OK` 訊息框（見 `auto-results.md` 的「20 補充」與 plan 的 Implementation Notes 3）；dry run 漏掉的點擊較可能是 `f5gui.answer` 已處理的時序問題。`f5gui.dismiss` 與 `answer` 的重按機制仍保留。

## 現況（2026-10-10 於 `fix/f5-save-failure-handling`、HEAD `918c251`、Windows 11 26200、NTFS 驗證）

`$PY` 是 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`（Python 3.13.15、wxPython 4.2.5 msw、wxWidgets 3.2.9）。`$SP` 是 session scratchpad。本 spec 的原型在 `$SP\f5spec\`（`dlg.py`、`drive.py`、`probe.py`、`surrogates.py`；不 commit）。UIA 驅動程式在 `$SP\uia` 執行（pywinauto 0.6.9、psutil 7.2.2）。

基線：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 1270 tests`、`FAILED (errors=1, skipped=7)`。唯一的 error 是 F-W6（`test_dictionary_name_prompt ... test_case_only_rename_still_renames`）。原始碼 msgid：353；`dotexpress.po` 有 354 行 `msgid`（含 header）。`xgettext`、`msgmerge`、`msgfmt` 已安裝（`C:\Program Files\gettext-iconv\bin`）。

### 開啟中文件的存檔

`DocumentWorkspaceService.save_open_document`（`client/documents/workspace_service.py:79-86`，4 空白）：

```python
document = self._controller.get_document(self._controller.open_document_name)
if document is None:
    return None
updated_document = prepare_document_for_save(document, text=text, braille=braille)
self._controller.replace_document(updated_document)      # memory first (documented contract)
save_document_package(self.package_path(updated_document.name), updated_document)
return updated_document
```

controller 的副本是 pending 時，`prepare_document_for_save`（`client/documents/workspace.py:248-255`）保留 `braille=None`（pending：寫出時帶 `<name>.meta.json`），因此忽略點字編輯框；否則取點字編輯框的內容。F-3 之後 `save_document_package` 經由 `write_bytes_atomically` 寫入，所以失敗的存檔讓包逐位元組不變，但此時記憶體已經更新。**若拿 controller 的副本來比較，失敗的存檔會被當成已存，重試就會跳過寫入，這就是資料遺失。**

記憶體也可能在沒有任何寫入的情況下改變。`ConversionPresenter._complete_manual`（`client/ui/conversion_presenter.py:198-209`）把 controller 中開啟中的文件換成編輯框的文字加上新的點字，在下一次存檔之前不會寫入任何東西。

### `client/gui.py` 的呼叫端（tab）

| 行 | Handler | 存檔失敗時的行為 |
| --- | --- | --- |
| 592-599 | `_open_adjacent_document`（Ctrl+Tab、Ctrl+Shift+Tab） | `_save_open_document_with_feedback()` 顯示 `Failed to save document: {error}`；不切換 |
| 735-742 | `on_open_document`（開啟、Enter、雙擊） | 同上 |
| 744-750 | `on_add_document` | 同上，在名稱對話框之前 |
| 752-778 | `on_rename_document` | 同上，在名稱對話框之前 |
| 780-808 | `on_delete_document` | 同上，在確認之前 |
| 810-839 | `on_delete_all_documents` | 同上 |
| 841-869 | `on_import_document` | 同上，在檔案對話框之前 |
| 871-878 | `on_export_document` | 同上 |
| 880-885 | `on_export_all_documents` | 同上 |
| 909-918 | `on_output_text_key_down`（Ctrl+E，匯出 BRL） | 同上 |
| 967-980 | `_on_close` | 轉換中且可 veto：veto，不存檔。否則存檔失敗、出現訊息框，若 `CanVeto()` 則 veto 關閉；不可 veto 時不呼叫 `Skip` 就返回 |

`_save_open_document_with_feedback`（`:607-613`）攔下 `Exception` 並呼叫 `_show_document_save_error`（`:452-461`）。該方法把非 `OSError` 的 traceback 記到 `gui.log`（F-3 審查 M-3），並顯示 `wx.MessageBox(..., _("Error"), wx.OK | wx.ICON_ERROR)`。

### 量測（原型）

**對話框**（以 `$PY` 執行 `dlg.py`，由 `drive.py` 經 UIA 操作）。對話框是 `wx.MessageDialog(parent, error_line, "無法儲存文件", wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_ERROR)`，加上 `SetExtendedMessage(question)` 與 `SetYesNoCancelLabels("重試(&R)", "不儲存就關閉(&W)", "取消")`：

- `SetYesNoCancelLabels` 回傳 `True`。wxMSW 顯示 Windows task dialog（`#32770`），由 frame 擁有：在 UIA 樹中它是主視窗的子項，不是頂層視窗。
- UIA 樹：`Image MainInstructionIcon`、automation id 為 `MainInstruction` 的 `Text`（錯誤那一行）、automation id 為 `ContentText` 的 `Text`（延伸訊息）、名為 `重試(R)` 的 `Button`、名為 `不儲存就關閉(W)` 的 `Button`、名為 `取消` 的 `Button`，以及含系統關閉鈕的標題列。所有標籤都是傳進去的那些；`&` 變成底線的助記鍵，並從 UIA 名稱中去掉。沒有任何英文。沒有用到 `FindWindowById`，所以 F-W9 不會在這裡重現。
- 焦點一開始在 `重試(R)`。按鍵：Enter -> `ID_YES`、Esc -> `ID_CANCEL`、Alt+R -> `ID_YES`、Alt+W -> `ID_NO`、Tab 再 Enter -> `ID_NO`。在 task dialog 中不按 Alt 只按 `W` 沒有作用。
- 把兩段放在同一個訊息、中間空一行，得到相同的主要指示／內容分段。`SetExtendedMessage` 把這個分段明確寫出來。
- 原型的內容句子與「使用者可見字串」的最終用字略有不同，版面相同。

**編輯框來回**（`probe.py`，`wx.TextCtrl` 加 `wx.TE_MULTILINE`，輸入框與唯讀輸出框的 style）：`SetValue(x)` 後 `GetValue()`，對 LF、結尾 LF、tab、NBSP、點字、astral 字元（`U+1F600`）與 lone surrogate（`a\ud800b`）都原樣傳回 `x`。`\r\n` 與 `\r` 傳回 `\n`。**`a\x00b` 傳回 `a`**：Edit 控制項在 U+0000 處截斷。

**包的指紋**（`probe.py`，對存好的 `alpha.dep` 呼叫 `os.stat`）：`(st_size, st_mtime_ns)` 在 `attrib +r`、`attrib -r`、`attrib +h` 之後，以及另一個 handle 以共用讀取、讀寫或不共用開著檔案時都不變。`os.stat` 在這些情況下都能用。失敗的 `save_document_package` 不改變它。以相同內容重寫會改變 `st_mtime_ns`。

**lone surrogate 替換**（`surrogates.py`）：`text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")` 每個 lone surrogate 給一個 U+FFFD（`a\ud800b` -> `a\ufffdb`；順序顛倒的一對 -> 兩個 U+FFFD；`\udcff` -> 一個 U+FFFD）。它把被拆開的一對合回字元（`\ud83d\ude00` -> U+1F600），其餘不動。UTF-8 版本每個 surrogate 給三個 U+FFFD。M-4 建議的 `encode("utf-8", "replace")` 給 `?`。在 550,000 個字元上，乾淨文字的 `re.search("[\ud800-\udfff]")` 掃描花 1.7 ms，有髒字元時的替換花 2.9 ms。比較兩個等長且相等的字串花 0.65 ms。

### 釘住今天行為的測試

- 以 lone surrogate 當作非 `OSError` 錯誤（F-3 D9 與 M-3）。D4 落地後這些不再失敗：
  - `test_document_workspace.py`：`test_save_failure_from_a_lone_surrogate_keeps_the_existing_package` 與 `test_staging_error_that_is_not_an_os_error_keeps_the_old_package`。
  - `test_workspace_service.py`：`test_save_failure_keeps_the_package_and_updates_memory`。
  - `test_gui_document_flows.py`：`test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package`、`test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error`、`test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state`、`test_save_failure_that_is_not_an_os_error_is_logged_with_its_traceback` 與 `test_rename_failure_that_is_not_an_os_error_is_logged_with_its_traceback`。
- 關閉：`test_close_vetoes_when_save_fails`（錯誤框與 veto）與 `test_close_asks_presenter_before_saving`（mock 掉 `_save_open_document_with_feedback`）。
- 存檔永遠寫入：沒有測試斷言沒修改的文件會被重寫。每個 GUI 與 service 測試都直接建 controller（`_make_workspace_frame`、`_service`），不經過 `load_documents`；D3 的「沒有記錄就寫入」讓這些測試維持有效。

## 決定

**D1. 基準是 `DocumentWorkspaceService` 中每份文件的「已存記錄」，絕不是 controller 的副本。** service 保存 `self._saved: dict[str, _SavedPackage]`，key 是 controller 拼寫的文件名稱。`_SavedPackage` 是 frozen dataclass，含 `document: Document`（正好是寫入或載入的內容）與 `fingerprint: tuple[int, int] | None`（該次寫入或載入之後包的 `(st_size, st_mtime_ns)`）。service 是唯一寫入或載入包的地方，所以也是唯一知道磁碟上有什麼的地方。controller 維持純記憶體模型。否決的做法：

- 與 controller 的副本比較。controller 在寫入前更新（F-3 保留的文件化契約），轉換也會不寫檔就更新它。失敗的存檔之後的重試會被跳過：資料遺失。
- 由 `EVT_TEXT` 設定的「dirty」旗標。wx 對 `SetValue` 也會送出它，所以載入或切換文件都會設定它。除非每條路徑都正確重設，否則它會漏掉轉換結果與失敗的存檔，而且看不到磁碟上已改變的包。
- 不帶指紋的內容比較。app 執行期間若另一個程式刪除或取代了包，沒有變更的文件就不會被寫回，而今天的存檔會寫回。依「有疑慮就寫入」的原則，指紋保留這個行為（D2）。

**D2.「沒有變更」的定義。** 令 `prepared = prepare_document_for_save(controller 副本, text=編輯框文字, braille=點字編輯框)`。它在 D4 之後計算，所以不含 lone surrogate。只有以下全部成立時存檔才跳過寫入：

1. `prepared.name` 有記錄；
2. `prepared == record.document`（名稱、文字，以及含 `None` 的點字；`None` 恰好等於「寫了 pending metadata」，因為工作區存檔一律傳 `include_pending_metadata=True`）；
3. `_package_fingerprint(package_path(name))` 不是 `None`，且等於 `record.fingerprint`。`_package_fingerprint` 呼叫 `os.stat`，遇到任何 `OSError` 或路徑不是一般檔案時回傳 `None`。

其他情況一律寫入，與今天完全相同。dual view 結果不屬於包，不列入比較。兩種情況都先更新 controller。寫入或跳過是內部決定：`save_open_document` 簽章不變，兩種情況都回傳 `prepared`。

後果：

- 寫入失敗不動記錄，所以重試時 `prepared != record.document`，會寫入。
- 存檔失敗後把文字改回已存的版本，文件又變成沒有變更，不會擋住。
- 轉換結果改變 `prepared.braille`（pending 文件變成非 pending），所以會寫入。
- 編輯框把 `\r\n` 與 `\r` 正規化為 `\n`，並在 U+0000 處截斷（現況）。載入的文件含這些字元時算作有變更，寫入一次（與今天相同），之後記錄就相符。

**D3. 記錄的生命週期（每條寫入、載入或移除包的路徑）。**

| 路徑 | 成功後的記錄 | 失敗後 |
| --- | --- | --- |
| `load_documents`（啟動） | 換成載入的文件，各帶 `package_path(name)` 的指紋 | （沒有載入任何東西） |
| `save_open_document`，有寫入 | `_saved[name] = (prepared, 寫入後的指紋)` | 不變（舊記錄或沒有記錄）；controller 持有 `prepared` |
| `save_open_document`，跳過 | 不變 | - |
| `create_document`（新增、預設的 `new` 文件） | `_saved[name] = (寫出的文件, 指紋)` | 不新增 |
| `import_files` | 每份存好的文件一筆記錄 | 寫入失敗的文件沒有記錄 |
| `rename_document`（一般與只改大小寫） | `_saved.pop(source)`；`_saved[new] = (寫出的 Document(new, source.text, source.braille), 新路徑的指紋)` | 不變（舊名稱保有其記錄） |
| `delete_document` | unlink 之後 `_saved.pop(name, None)` | 不變 |
| `delete_all_documents`，完成 | 清空 | 重新載入：換成剩下的文件，同 `load_documents` |
| 匯出為 DEP（`formats._write_dep`，任何使用者路徑） | 不變 | 不變 |
| 轉換（`_complete_manual`，只改記憶體） | 不變 | - |
| 不經 service 放進 controller 的文件（測試） | 沒有，所以每次存檔都寫入 | - |

「寫出的」指經過 D4 替換之後。service 記錄 `_encodable(document)`，也就是 `_normalized` 寫出的同一個值，所以下一次存檔比較會相等。若匯出為 DEP 的目標正好是工作區自己的 `alpha.dep`，指紋會改變，下一次存檔就把工作區版本再寫一次：那個檔剛被不帶 pending metadata 的版本取代了。

**D4. lone surrogate 在 documents 層換成 U+FFFD。** `client/documents/workspace.py` 新增公開函式 `replace_lone_surrogates(text: str) -> str`。若沒有出現 `[\ud800-\udfff]`，回傳 `text` 本身；否則回傳 `text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")`：每個 lone surrogate 一個 U+FFFD，被拆開的高低一對合回字元，其餘不變。套用在兩處：

- `prepare_document_for_save`，套在文字，以及保留（非 `None`）的點字上。因此 controller 副本、D2 的比較與記錄都持有替換後的文字。
- `_normalized`，每個包的寫入器都經過它：存檔、新增、匯入、每次改名的 staged 包（`PackageFiles.write`）與匯出為 DEP。因此寫包一定能編碼。

否決：`encode("utf-8", "replace")`（M-4 的建議）給的是 `?` 而不是 U+FFFD。UTF-8 `surrogatepass` 來回每個字元給三個 U+FFFD。以 `surrogatepass` 寫出會讓包讀不回來，因為 loader 嚴格解碼。

**D5. 不動編輯框，不顯示也不記錄任何東西。** 替換了 surrogate 的存檔之後，`input_txt` 仍持有該字元。設定控制項的值會移動游標並讓 NVDA 重讀，而且發生在使用者自己啟動的動作中途。那個 surrogate 本來就看不見。下次開啟文件時，控制項會從 controller 重新載入；在那之前，每次存檔都會再替換一次、與記錄比較相等（D2）並跳過寫入。轉換仍讀取控制項的文字（不在範圍內，見「不在範圍內」）。不記 log：`gui.log` 設定在 `ERROR` 等級，而這是一次成功、預期中的修復，不是錯誤。

**D6. 關閉時存檔失敗就詢問。** `_on_close`：

1. 若轉換進行中且事件可 veto：veto，不存檔（不變）。
2. 嘗試 `_save_open_document()`。若成功，或被 D2 跳過，照今天的方式關閉。
3. 若拋出任何 `Exception` 且事件可 veto：照 M-3 的方式記 log（只記非 `OSError`，含 traceback），並顯示對話框（D7）。
   - **重試**：回到步驟 2。再次失敗時，對話框以新的錯誤文字再出現一次。
   - **不儲存就關閉**：照今天的方式關閉（`close_converting_dialog`、銷毀 dual view、`evt.Skip()`）。磁碟上的包是上次成功的存檔（F-3 保證失敗的寫入讓它逐位元組不變）。記憶體中的修改被丟棄。
   - **取消**、Esc 或對話框的關閉鈕：veto。記憶體與編輯框保留修改，使用者可以排除原因後再次關閉或透過任何動作重試。
4. 若拋出例外且事件不可 veto：D8。

關閉時不再顯示單純的錯誤框；對話框帶有相同的文字。重試是 handler 內的迴圈，不是新的關閉事件，所以 `CanVeto()` 從頭到尾不變。

**D7. 對話框是帶自訂標籤的 `wx.MessageDialog`（Windows task dialog）。**

```python
with wx.MessageDialog(
	self,
	_("Failed to save document: {error}").format(error=error),
	_("Cannot Save Document"),
	wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_ERROR,
) as dialog:
	dialog.SetExtendedMessage(_("Changes made since the last successful save have not been saved. If you close without saving, these changes will be lost."))
	dialog.SetYesNoCancelLabels(_("&Retry"), _("Close &Without Saving"), _("Cancel"))
	return dialog.ShowModal()  # ID_YES: retry, ID_NO: close without saving, else cancel
```

- **保留既有錯誤文字**作為主要指示，原封不動：同一個 msgid，其後是同樣的 Python 錯誤文字（F-3 D6）。新句子是內容文字。
- **無障礙**：標準的 Windows task dialog，NVDA 以對話框方式朗讀：標題、主要指示、內容，然後是有焦點的按鈕。每個標籤都經 `SetYesNoCancelLabels` 傳入，所以三個都在地化（經 UIA 量測），而且沒有走訪視窗樹，避開 F-W9 的 `FindWindowById` 錯誤。鍵盤：焦點在重試且為預設（Enter），Alt+R 與 Alt+W 是助記鍵，Esc 或關閉鈕等於取消。具破壞性的選項永遠不是預設。
- **順序**重試、不儲存就關閉、取消：wx 在 Windows 上給 Yes/No/Cancel 按鈕的順序，也是常見的「重試在前、退路在後」模式。
- **圖示** `ICON_ERROR`，與既有的失敗訊息框一致。
- 若 `SetYesNoCancelLabels` 回傳 `False`（沒有任何出貨平台會這樣），對話框仍可運作，使用平台的 Yes/No/Cancel 標籤，不另外處理。
- helper 是 frame 方法 `_ask_after_close_save_failure(error) -> int`，讓測試可以 patch `wx.MessageDialog` 並斷言每個參數。

否決：

- 自訂 `wx.Dialog`：程式碼更多，要自己處理焦點與無障礙名稱，還有 F-W9 那類標準按鈕在地化的問題。
- `wx.MessageBox`：不能自訂標籤；按鈕顯示英文 `OK`（F-W9）。
- 連續兩個問題（錯誤框，然後「仍要關閉？」）：螢幕報讀器使用者要多走幾步，而且做決定時錯誤文字已經不見了。

**D8. 不可 veto 的關閉（Windows 結束工作階段）不詢問。** 若 `evt.CanVeto()` 為假，handler 嘗試存檔一次。失敗時記 log（`logger.error("Failed to save the open document while closing", exc_info=error)`，所有例外類型都記，因為沒有人會看到訊息）並關閉（`Skip`）。今天它顯示 modal 錯誤框，並且不呼叫 `Skip` 就返回，讓視窗留著，而 Windows 終究會結束程序。兩種情況下上次成功存檔之後的修改都會遺失；包是完整的（F-3）。wx 只在可 veto 的 query-end-session 關閉已經走過對話框之後才送出不可 veto 的關閉，所以這條路徑很少見。

**D9. 記錄 log。** M-3 的邏輯移到 `_log_unexpected_save_error(error)`，它以 traceback 記錄非 `OSError`。`_show_document_save_error` 呼叫它，D6 的步驟 3 也呼叫它，每次失敗的嘗試一次。`OSError` 仍不記（預期中，而且對話框已寫明），D8 除外。

**D10. 其他動作不變（決定 C）。** `_save_open_document_with_feedback` 與它的十個呼叫端程式碼不變。只有當存檔真的寫入並失敗時，它們才以既有錯誤框擋下。F-3 Q1 維持：包上任何開著的 handle 都會讓寫入失敗。改名與刪除接著對包套用各自的規則（F-3 D7、Windows 的刪除語意），不變。

**D11. 沒有新的標示、命令或設定。** 標題沒有「已修改」標記，沒有存檔選單項目，沒有自動存檔，沒有關閉 dirty 檢查的偏好設定。

**D12. 翻譯目錄。** `gui.py` 有四個新 msgid，在 `dotexpress.po` 翻譯。以 `scripts\generate-pot.bat` 重新產生，再以預設換行執行 `msgmerge --update --backup=none locales\zh_TW\LC_MESSAGES\dotexpress.po locales\dotexpress.pot`（W-3 D5）。填入 msgstr，清掉 `msgmerge` 加上的任何 `fuzzy` 旗標，並以 `msgfmt --check -o locales\zh_TW\LC_MESSAGES\dotexpress.mo locales\zh_TW\LC_MESSAGES\dotexpress.po` 建置。`msgfmt` 已安裝，不需要替代方案。若實作的機器上沒有，使用前先驗證某個腳本對目前的 `.po` 產生逐位元組相同的輸出，再用它建 `.mo`（AGENTS.md）。

## 每條路徑的前後行為

「沒有變更」指 D2 成立。「失敗」指寫入拋出例外。

| 路徑 | 之前 | 之後 |
| --- | --- | --- |
| 切換（開啟、Enter、Ctrl+Tab），沒有變更 | 重寫；寫入失敗時：錯誤框，不切換 | 不寫入；切換 |
| 切換，有變更 | 寫入；失敗：錯誤框，不切換 | 相同 |
| 新增、匯入、匯出、全部匯出、Ctrl+E，沒有變更 | 重寫；失敗：錯誤框，動作中止 | 不寫入；動作繼續 |
| 同上，有變更 | 寫入；失敗：錯誤框，中止 | 相同 |
| 改名，開啟中的文件沒有變更 | 重寫；失敗：名稱對話框之前出現錯誤框 | 不寫入；名稱對話框；改名本身接著套用 F-3 規則（唯讀：`[Errno 13]`；被開著且未共用刪除：`[WinError 32]`） |
| 刪除／全部刪除，沒有變更 | 重寫；失敗：錯誤框 | 不寫入；確認；unlink 套用今天的規則（Windows 上唯讀：`[WinError 5]`「Failed to delete document」） |
| 關閉，沒有變更 | 重寫；失敗：錯誤框，關閉被 veto（F-W10） | 不寫入；關閉 |
| 關閉，有變更，寫入成功 | 關閉 | 相同 |
| 關閉，有變更，寫入失敗 | 錯誤框，關閉被 veto；非 `OSError` 另外記 log | 對話框 D7：重試（迴圈）、不儲存就關閉（關閉，包 = 上次成功的存檔）、取消（veto，保留修改）；非 `OSError` 每次嘗試記 log |
| 關閉，轉換進行中 | veto（可 veto 時） | 相同 |
| 關閉，不可 veto，寫入失敗 | 錯誤框，然後不呼叫 `Skip` 就返回 | 記 log；關閉（D8） |
| 輸入或貼上 lone surrogate，任何存檔 | `UnicodeEncodeError`：每次都出現錯誤框（或關閉被 veto）；不強制結束 app 就離不開 | 以 U+FFFD 存檔，沒有訊息；編輯框保留該字元直到重新開啟文件；之後的存檔跳過（D5） |
| 啟動 | 載入包 | 相同，另外建立記錄與指紋 |
| 開著時包在磁碟上被刪除或取代，記憶體沒有變更 | 下一次存檔重寫 | 相同（指紋不同：寫入） |
| 匯出為 DEP 到任何路徑 | 原子寫入 | 相同；lone surrogate 寫成 U+FFFD |

## Windows NTFS 上的失敗模式

「訊息」是 packaged zh-TW build 今天的文字（`儲存文件失敗：{error}`，標題 `錯誤`）。「切換」代表除了關閉之外的每個動作。改名與刪除接著套用各自的規則，如上表。

### 開啟中的文件自上次載入或寫入後沒有變更

| 其 `.dep` 的狀況 | 之前：切換／其他 | 之前：關閉 | 之後：切換／其他 | 之後：關閉 |
| --- | --- | --- | --- | --- |
| 唯讀屬性 | `[Errno 13] Permission denied: '...\alpha.dep'`；擋下 | 同樣訊息；veto；app 無法結束（F-W10） | 繼續，不寫入 | 關閉 |
| 被開著，共用讀取（壓縮工具） | `[WinError 5] ...: '...\.alpha.dep.<hex>.tmp' -> '...\alpha.dep'`；擋下 | 同上；veto | 繼續 | 關閉 |
| 被開著，共用讀寫／含刪除（F-3 Q1） | `[WinError 5]`；擋下 | 同上；veto | 繼續 | 關閉 |
| 磁碟已滿 | `[Errno 28]` 或指名 `.tmp` 的錯誤；擋下 | 同上；veto | 繼續 | 關閉 |
| lone surrogate | 不會發生：包裡永遠不會有（loader 嚴格解碼），而貼上的字元會讓文件變成有變更 | - | - | - |
| 寫入器中的非 `OSError`（bug） | 訊息 + `gui.log` traceback；擋下 | 同上；veto | 繼續；不呼叫寫入器 | 關閉 |
| 包被其他程式刪除或取代 | 重寫 | 重寫，關閉 | 重寫（指紋，D2）；成功或失敗都如有變更的文件 | 同左 |

### 開啟中的文件有未存的修改

| 狀況 | 之前：切換／其他 | 之前：關閉 | 之後：切換／其他 | 之後：關閉 |
| --- | --- | --- | --- | --- |
| 唯讀屬性 | `[Errno 13]`；擋下 | 同上；veto | 相同：訊息，擋下；記憶體保留修改 | 對話框帶 `[Errno 13] ...`；重試在 `attrib -r` 之前會再失敗，之後存檔並關閉；不儲存就關閉則結束，包不變；取消讓 app 保持開啟 |
| 被開著，任何共用模式 | `[WinError 5]`；擋下 | 同上；veto | 相同 | 對話框；其他程式關掉檔案後重試會存檔並結束；其他選項同上 |
| 磁碟已滿 | `[Errno 28]`（或 `.tmp` 的錯誤）；擋下 | 同上；veto | 相同 | 對話框；騰出空間後重試會存檔 |
| lone surrogate（貼上） | `UnicodeEncodeError` 訊息；每次都擋下 | 同上；每次都 veto | 以 U+FFFD 存檔；繼續 | 以 U+FFFD 存檔；關閉 |
| 寫入器中的非 `OSError`（bug） | 訊息 + traceback；擋下 | 同上；veto | 相同 | 對話框帶錯誤文字；每次嘗試記 traceback；不儲存就關閉是出路 |
| 以上任一種，關閉不可 veto | - | 錯誤框，視窗未被銷毀 | - | 記 log，關閉（D8） |

每一列中，磁碟上的包都是上次成功的存檔（F-3），也不會留下 `.tmp`。

## 各檔案的設計

### `client/documents/workspace.py`（4 空白）

- `_LONE_SURROGATE = re.compile("[\ud800-\udfff]")` 與公開的 `replace_lone_surrogates(text: str) -> str`（D4）。Docstring：「Replace every unpaired UTF-16 surrogate with U+FFFD so the text can be encoded as UTF-8; a split pair is joined.」
- `_encodable(document) -> Document`：同樣的名稱，文字與點字經過 `replace_lone_surrogates`，點字為 `None` 時保留。
- `_normalized(document)`：另外套用 `_encodable`（名稱正規化不變）。
- `prepare_document_for_save`：回傳 `_encodable(Document(name, text, saved_braille))`。

### `client/documents/workspace_service.py`（4 空白）

- `_SavedPackage`（frozen dataclass：`document`、`fingerprint`）、`_package_fingerprint(path) -> tuple[int, int] | None`。
- `__init__`：`self._saved: dict[str, _SavedPackage] = {}`。
- `_remember(document)`：存入 `_SavedPackage(_encodable(document), _package_fingerprint(self.package_path(document.name)))`。`_is_saved(document) -> bool` 實作 D2。`_reset_saved(documents)` 由 `load_documents` 與 `delete_all_documents` 的失敗分支使用。
- `save_open_document`：到 `replace_document` 為止與今天相同；接著 `if self._is_saved(updated_document): return updated_document`；然後寫入、`_remember`、回傳。
- `create_document`、`import_files`、`rename_document`、`delete_document`、`delete_all_documents`：D3 的記錄更新，每一項都在磁碟效果成功之後。
- 模組 docstring：「Save writes only when the open document differs from what was last written to or loaded from its package; that record changes only after a successful write, so a failed save is retried by the next one.」

### `client/gui.py`（tab）

- `_log_unexpected_save_error(error)`（D9）；`_show_document_save_error` 呼叫它。
- `_ask_after_close_save_failure(error) -> int`（D7）。
- `_save_open_document_before_close(can_veto: bool) -> bool`（D6、D8）：

```python
def _save_open_document_before_close(self, can_veto: bool) -> bool:
	"""Save before closing; True if the frame may close."""
	while True:
		try:
			self._save_open_document()
			return True
		except Exception as error:
			if not can_veto:
				logger.error("Failed to save the open document while closing", exc_info=error)
				return True
			self._log_unexpected_save_error(error)
			answer = self._ask_after_close_save_failure(error)
			if answer == wx.ID_YES:
				continue
			return answer == wx.ID_NO
```

- `_on_close`：轉換檢查仍在最前面。接著 `if not self._save_open_document_before_close(evt.CanVeto()): evt.Veto(); return`。其餘不變。

### `client/locales/`（D12）

`dotexpress.pot`、`zh_TW/LC_MESSAGES/dotexpress.po`、`zh_TW/LC_MESSAGES/dotexpress.mo`。

### `client/tests/wx_stub.py`（4 空白）

`gui_frame_stubs`：新增 `wx.ID_YES`、`wx.ID_NO`、`wx.ID_CANCEL` 與 `wx.YES_DEFAULT`，其值與既有的 id 和旗標都不同（真實 wx 的 `YES_DEFAULT` 是 0；stub 讓它在 style 斷言中看得見）。`_MessageDialog` 增加 `SetExtendedMessage` 與 `SetYesNoCancelLabels`（回傳 `True`）。

### 不變

`documents/controller.py`、`documents/session.py`、`documents/formats.py`、`documents/export_coordinator.py`、`ui/conversion_presenter.py`、`shared/atomic_write.py`、`dialog.py`（含 `localize_standard_buttons`）、其他所有對話框、包格式、`client/dictionary/`、`client/braille/`。

## 保持相同的部分

- 相同文件與時間戳記下的包格式與位元組。不含 lone surrogate 的文字寫出結果與以前完全相同。
- 存檔「先記憶體後寫入」的順序。新增、匯入、改名、刪除與全部刪除的每個磁碟效果與 controller 更新。
- 每個既有訊息樣板與標題。關閉以外、存檔真的寫入並失敗的每個動作，其錯誤框與擋下行為。
- 轉換進行中時關閉被 veto。
- F-3：原子寫入、唯讀判定、Q1 的鎖定行為與 Q2 的改名拒絕。
- 兩個 fixture 的 sha256。

## 使用者可見字串

新的 msgid，全部在 `client/gui.py`（D7）：

| msgid | msgstr（zh_TW） | 位置 |
| --- | --- | --- |
| `Cannot Save Document` | `無法儲存文件` | 對話框標題 |
| `Changes made since the last successful save have not been saved. If you close without saving, these changes will be lost.` | `上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。` | 內容文字，在錯誤那一行下方 |
| `&Retry` | `重試(&R)` | 按鈕（Yes），預設 |
| `Close &Without Saving` | `不儲存就關閉(&W)` | 按鈕（No） |

沿用：`Failed to save document: {error}`（`儲存文件失敗：{error}`）作為主要指示，`Cancel`（`取消`）作為第三個按鈕。助記鍵格式依照目錄的慣例（`&Categories:` -> `分類(&C)：`）。D8 的 log 訊息不翻譯（log 文字從不翻譯）。msgid 353 -> 357。

## 測試計畫

TDD：每一步的新測試先寫、並以所述原因失敗，再由程式碼讓它們通過。測試檔維持原本的縮排（以下所有檔案都是 4 空白）。每個測試都使用暫存目錄，從不碰 `client/dictionary/`、`client/workspace/` 或 `config.json`。

錯誤注入：

- `patch("os.replace", ...)` 模擬 staging 之後失敗的寫入（呼叫時才查找，不受 `wx_stub` 模組副本影響）。
- `patch("zipfile.ZipFile.writestr", side_effect=ValueError("injected"))` 模擬寫入封存檔時拋出的非 `OSError`。它取代 lone surrogate 注入方式。
- 改名使用 `package_files=`。
- `client/tests/windows_file_handles.py` 的 Windows 專用 helper（`hold_open`、`SHARE_MODES`、`make_read_only`）。
- GUI 測試從不 patch `documents.*` 的全域（F-3 規則）。「沒有寫入」的斷言在 service 測試用 `patch.object(workspace_service, "save_document_package", wraps=...)`，在 GUI 測試用 `os.replace` 呼叫次數加上包的位元組與 `st_mtime_ns`。

### A. documents 層（`client/tests/test_document_workspace.py`）

新增，紅燈原因是缺少 `replace_lone_surrogates` 或寫入拋出 `UnicodeEncodeError`：

1. `test_replace_lone_surrogates_replaces_each_unpaired_surrogate`，subTest：lone high、lone low、順序顛倒的一對（兩個 U+FFFD）、兩個 high、結尾的 high、`\udcff`。
2. `test_replace_lone_surrogates_joins_split_pairs_and_keeps_other_text`：`\ud83d\ude00` -> U+1F600；astral、CJK、點字與 `""` 不變；乾淨的輸入原物件傳回。
3. `test_prepare_document_for_save_replaces_lone_surrogates`：文字與點字；pending 文件維持 `None`。
4. `test_save_replaces_lone_surrogates_with_the_replacement_character`（subTest：文字、點字）：包載入後是 U+FFFD，`.txt` 成員含 `EF BF BD`。
5. `test_staged_package_replaces_lone_surrogates`：文字含 surrogate 時的 `PackageFiles().write` 與 `move_document_package`。

變更（注入方式，不是用意）：

- `test_save_failure_from_a_lone_surrogate_keeps_the_existing_package` 改為 `test_save_failure_that_is_not_an_os_error_keeps_the_existing_package`：`writestr` 在第一個成員、再在第二個成員拋出 `ValueError`（subTest）；位元組不變、可載入、沒有 `.tmp`。
- `test_staging_error_that_is_not_an_os_error_keeps_the_old_package`：以同樣的 `writestr` 注入取代 `"\ud800"`。

### B. service（`client/tests/test_workspace_service.py`，新類別 `SaveOnlyWhenChangedTest`）

紅燈：今天每次存檔都寫入（或拋出 `UnicodeEncodeError`）。除非另外說明，每個測試都從 `load_documents()` 與 `controller.open_document("alpha")` 開始。

1. `test_unchanged_document_is_not_written`：不呼叫 `save_document_package`；包的位元組與 `st_mtime_ns` 不變。
2. `test_changed_text_is_written`。
3. `test_changed_braille_is_written`。
4. `test_converted_pending_document_is_written`：controller 副本得到點字（如 `_complete_manual`）；存檔寫入，`alpha.meta.json` 消失。
5. `test_failed_save_is_retried_by_the_next_save`。**必備的案例。** `os.replace` 失敗一次：第一次存檔拋出例外，controller 持有 `"edited"`。第二次相同的存檔會寫入，包持有 `"edited"`。這會抓到以 controller 副本當基準，以及在寫入前就更新記錄。
6. `test_reverting_after_a_failed_save_is_not_written`：失敗的存檔之後，以原文字存檔不呼叫寫入器，即使 `os.replace` 仍會失敗。
7. `test_lone_surrogate_text_is_saved_once`：`"x\ud800"` 寫成 `"x\ufffd"`；以 `"x\ud800"` 第二次存檔不寫入。
8. `test_package_removed_on_disk_is_written_again`。
9. `test_package_replaced_on_disk_is_written_again`（subTest：大小不同；位元組相同但以 `os.utime` 改成另一個時間）：存檔寫入記憶體的版本。
10. `test_document_without_a_record_is_written`：直接填入的 controller，記錄保守的預設行為。
11. `test_created_document_is_not_written_again`。
12. `test_imported_document_is_not_written_again`。
13. `test_renamed_document_is_not_written_again`（subTest：一般 `alpha` 到 `gamma`；只改大小寫 `alpha` 到 `Alpha`）：改名開啟中的文件，再以未變更狀態存檔。
14. `test_failed_rename_keeps_the_record_of_the_old_name`：`_FailingReplacePackageFiles(source_name="alpha.dep")`；之後未變更的 `alpha` 存檔不寫入。
15. `test_deleted_then_created_document_is_written`（刪除 `beta`、建立 `beta`、編輯、存檔：寫入）與 `test_documents_reloaded_after_a_failed_delete_all_are_not_written_again`。
16. 僅 Windows：`test_unchanged_unwritable_package_saves_without_error`，subTest 涵蓋唯讀（`make_read_only`）與 `SHARE_MODES` 的每一種（`hold_open`）：沒有例外，位元組不變。
17. `test_save_open_document_replaces_lone_surrogates_in_memory_and_on_disk`。

變更：`test_save_failure_keeps_the_package_and_updates_memory` 改用 `writestr` `ValueError` 注入，文字為 `"edited"`。

### C. GUI 流程（`client/tests/test_gui_document_flows.py`，類別 `DocumentWorkspaceFlowsCharacterizationTest`）

`setUp` 的 patcher 清單加入假的 `wx.MessageDialog`：在 `self.events` 記錄 `("MessageDialog", message, caption, style, extended, labels, parent)`，`ShowModal` 的結果取自新的 `self.dialog_answers` 清單，並支援 `with`。以啟動為起點的測試在準備好的工作區上呼叫 `frame._load_workspace_documents_at_startup()`。

新增：

1. `test_switch_from_an_unchanged_document_whose_save_would_fail_opens_the_next`：`os.replace` patch 成拋出例外；Ctrl+Tab 開啟 `beta`；沒有錯誤框；沒有呼叫 `os.replace`。紅燈：今天出現錯誤框且什麼都沒開。
2. 僅 Windows：`test_unchanged_read_only_document_blocks_neither_switch_nor_close`：真的 `attrib +r`；切換，然後以可 veto 的事件呼叫 `_on_close`：呼叫 `Skip`，沒有對話框。紅燈。
3. `test_switch_from_a_changed_document_whose_save_fails_still_blocks`：已載入、已編輯、`os.replace` 失敗；既有錯誤框；仍在 `alpha`；記憶體持有修改。回歸防護；在步驟 1 之後也是綠燈。
4. `test_close_with_an_unchanged_document_whose_save_would_fail_closes`。紅燈。
5. `test_close_save_failure_asks_and_cancel_keeps_the_window_open`：斷言對話框事件（message `gui._("Failed to save document: {error}").format(error=...)`、caption `gui._("Cannot Save Document")`、style `YES_NO | CANCEL | YES_DEFAULT | ICON_ERROR`、延伸文字、標籤 `(gui._("&Retry"), gui._("Close &Without Saving"), gui._("Cancel"))`、parent 為 frame）；回答 `ID_CANCEL`；呼叫 `Veto`，沒有 `Skip`；沒有錯誤框；記憶體與編輯框保留修改；包不變。紅燈：今天是錯誤框。
6. `test_close_retry_after_the_cause_is_gone_saves_and_closes`：`os.replace` 失敗一次後恢復；回答 `ID_YES`；一個對話框；`Skip`；包持有修改。
7. `test_close_retry_that_fails_again_asks_again`：失敗兩次；回答 `ID_YES`，再回答 `ID_CANCEL`；兩個對話框，各帶自己的錯誤文字；`Veto`。
8. `test_close_without_saving_closes_and_keeps_the_last_saved_package`：回答 `ID_NO`；呼叫 `close_converting_dialog`、銷毀 dual view、`Skip`；包的位元組不變；沒有 `.tmp`。
9. `test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes`：`CanVeto()` 為假；沒有對話框，沒有錯誤框；`assertLogs` 帶 `PermissionError` 的 `exc_info`；`Skip`。
10. `test_pasted_lone_surrogate_is_saved_as_replacement_character`：編輯框持有 `"x\ud800"`；存檔成功、沒有事件；記憶體與包持有 `"x\ufffd"`；編輯框仍持有 `"x\ud800"`。（之後的第二次存檔被跳過屬於 B7，步驟 2。）
11. `test_close_dialog_strings_are_translated`：`i18n.load_translation()` 把四個新 msgid 對應到上面的 zh-TW 文字。

翻轉或變更：

- `test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error` 改為 `test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks`：`writestr` `ValueError`；對話框訊息含 `injected`；一筆帶 traceback 的 log；回答 `ID_CANCEL`；`Veto`；包的位元組不變。紅燈：今天是錯誤框。
- `test_close_vetoes_when_save_fails`：對話框回答 `ID_CANCEL`；改為斷言對話框而不是錯誤框（改名為 `test_close_save_failure_cancel_vetoes`）。
- `test_close_asks_presenter_before_saving`（約第 3620 行的類別）：mock 的對象改為 `_save_open_document`（單純存檔），而不是 `_save_open_document_with_feedback`；預期順序不變。
- 四個把 `"\ud800"` 注入存檔或改名的測試改用新的注入方式。存檔的測試（`test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package`、`test_save_failure_that_is_not_an_os_error_is_logged_with_its_traceback`）用 `writestr` `ValueError`，預期文字為 `injected`、類型為 `ValueError`。改名的測試（`test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state`、`test_rename_failure_that_is_not_an_os_error_is_logged_with_its_traceback`）給 frame 的 service 傳入 `package_files=`，一個 `write` 會拋出 `ValueError("injected")` 的本地 `PackageFiles` 子類別。若 patch `writestr`，開啟中文件的存檔會先失敗。
- 不變且仍為綠燈：其他所有存檔、新增、改名、刪除、匯入與匯出流程測試（它們的 controller 沒有記錄，所以每次存檔都寫入），以及 `test_close_while_running_vetoes_or_saves_and_closes`。

### 數量

新測試：A 5、B 18（B15 是兩個測試）、C 11 = 34。翻轉與變更一對一取代原測試。預期：Windows 上 `Ran 1304`、`FAILED (errors=1, skipped=7)`，只有 F-W6。2 個新的 Windows 專用測試（B16、C2）在 POSIX 上 skip。plan 可以調整數量；紅綠燈的用意有約束力。

## 移轉步驟（每一步一個綠燈 commit，先紅燈）

1. `fix: save lone surrogates as U+FFFD (F-5)`：D4、D5。A 1-5、B17、C10。A、B、C 的注入方式變更放在同一個 commit，因為這一步移除了被注入的錯誤。這包括 `test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error`：它在這一步改用 `writestr` 注入，並保留錯誤框斷言，直到步驟 3 翻轉它。
2. `fix: skip saving an unchanged document (F-5)`：D1-D3。B 1-16、C 1-4。
3. `fix: offer retry or close without saving when saving fails on close (F-5)`：D6-D9、D12、`wx_stub` 的新增。C 5-9 與 11，三個關閉測試的翻轉。`.pot`、`.po` 與 `.mo` 在這個 commit 重新產生。

每個 commit 以 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` 結尾，只 stage 明確列出的路徑。

## 驗收標準

在 Windows 上從 `client/` 以 `$PY` 執行。

1. 完整套件：除了 F-W6 沒有其他失敗或 error；`Ran` = 1270 + 新測試數。
2. 焦點：`$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n tests.test_atomic_write tests.test_document_controller -v` 通過；Windows 專用測試有執行（沒有 skip）。
3. 翻譯目錄：以 `$PY -I` 對 `_`／`N_` 做 AST 掃描得到 357 個原始碼 msgid；`.po` 的 `msgfmt --statistics` 回報 357 個已翻譯，沒有 fuzzy，沒有未翻譯；`.mo` 能以 `gettext.GNUTranslations` 載入，並翻譯四個新 msgid；`scripts\generate-pot.bat` 執行兩次，除了 `POT-Creation-Date` 之外輸出相同。
4. 兩個 fixture 的 sha256 不變（`translation_golden.json` `e67d95a1...`、`dictionary_entries_trace.json` `f493da52...`）。
5. app 資料未被碰觸：套件前後 `client/dictionary/` 的 sha256 相同；沒有建立 `client/workspace/`、`client/config.json` 或 `client/log/`。
6. `git diff main --stat` 只涉及 `client/documents/workspace.py`、`client/documents/workspace_service.py`、`client/gui.py`、三個 locale 檔、`client/tests/wx_stub.py`、上面列出的測試檔，以及 spec、plan 與 history 檔。
7. 變異檢查（plan）：每個 mutant 至少被一個測試抓到。mutant：
   - 基準取自 controller 副本。
   - 在寫入前更新記錄。
   - 寫入失敗也更新記錄。
   - 不檢查指紋。
   - 改名不搬移記錄。
   - `delete_all_documents` 的失敗分支不重設記錄。
   - `prepare_document_for_save` 中跳過替換。
   - `_normalized` 中跳過替換。
   - 不替換點字。
   - 不儲存就關閉仍然存檔。
   - 重試不重試就關閉。
   - 取消會關閉。
   - 不可 veto 的關閉顯示對話框。
   - 對話框沒有 `YES_DEFAULT`，或標籤順序不同。
8. 下方的 packaged GUI 驗證，結果放在實作的 history 資料夾。

## Windows 驗證（packaged build）

照 F-4 的方式建置：主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面，執行 `scripts\build-dotexpress.bat`。在 `client\build\DotExpress\PYZ-00.toc` 與 `Analysis-00.toc` 確認 `documents\workspace.py`、`documents\workspace_service.py` 與 `gui.py` 來自要驗證的 checkout。把 `client\dist\DotExpress.exe` 複製到 `D:\dxtest\N-f5\`。每個項目在新的 `D:\dxtest\auto<N>-f5` 資料夾執行；只結束 exe 位於這些資料夾下的程序（`dx.kill_under`）。腳本重用 `docs/superpowers/history/2026-10-09-03-windows-verification/auto/`（`dx.py`、`docs.py`、`lock.py`）與 `.../2026-10-09-05-f3-dep-atomic-write/auto/f3gui.py`，不修改它們。新的腳本與 helper `f5gui.py` 放在 `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/`，在 pywinauto venv（`$SP\uia`）執行。包以 zip 成員雜湊（`docs.ws_state`）與 `st_mtime_ns` 比對。

`f5gui.py` 經 UIA 讀取新對話框，因為 win32 backend 的 `dx.dismiss` 看不到 task dialog 的按鈕。它以 `Desktop(backend="uia").window(handle=<main>).child_window(title="無法儲存文件", control_type="Window")` 找到對話框，以 automation id 讀取 `MainInstruction` 與 `ContentText` 的文字以及三個按鈕的名稱，記錄哪個元素有焦點，並以 Enter、Esc 或 Alt+W（或按鈕的 `invoke()`）回答。這些項目不能用 `docs.close`。`f5gui.close_and_answer(app, w, answers)` 送出 `WM_CLOSE`，並依序回答每個對話框。lone surrogate 以 `ctypes` 放上剪貼簿（`OpenClipboard`、`SetClipboardData(CF_UNICODETEXT)`，內容為原始 UTF-16 code unit `41 00 3D D8 42 00 00 00`），再對輸入的 `Edit` 送 `WM_PASTE`（0x0302）貼上。

| # | 步驟 | F-5 之後的預期 | 之前（N-f4） |
| --- | --- | --- | --- |
| 36 | 新增 `alpha` 與 `beta`（兩者都有文字），關閉，重新啟動；`attrib +r alpha.dep`；`alpha` 開啟且未變更：Ctrl+Tab、新增 `gamma`、回到 `alpha`、關閉 | 沒有訊息；切換與新增都成功；app 結束；`alpha.dep` 的位元組與 `st_mtime_ns` 不變；仍為 `R` | 每個動作都 `[Errno 13]`；關閉被 veto（項目 20） |
| 37 | 同 36，但改由 `lock.py` 開著 `alpha.dep`（共用 `r`，再 `rw`）而不是設屬性 | 兩種共用模式都同 36 | 每個動作都 `[WinError 5]`；關閉被 veto |
| 38 | 開啟 `alpha`；輸入修改；`lock.py` 開著 `alpha.dep`（共用 `r`）；Ctrl+Tab；然後關閉 | Ctrl+Tab：今天的訊息 `儲存文件失敗：[WinError 5] ...`，仍在 `alpha`。關閉：對話框 `無法儲存文件`；`MainInstruction` = 同一行 `儲存文件失敗：...`；`ContentText` = 新句子；按鈕 `重試(R)`、`不儲存就關閉(W)`、`取消`；焦點在 `重試(R)`。Esc：app 保持開啟，修改仍在編輯框。再次關閉，在鎖定中按 Enter（重試）：對話框再出現。結束 lock，Enter：app 結束。重新啟動：`alpha` 持有修改 | Ctrl+Tab 相同；關閉：只有 `確定` 的錯誤框，veto |
| 39 | 同 38 直到對話框；Alt+W（不儲存就關閉） | app 結束；`alpha.dep` 的成員與修改前相同；沒有 `.tmp`；重新啟動顯示舊文字 | 不可能（veto） |
| 40 | 開啟 `alpha`；貼上剪貼簿中的 `A\ud83dB`；Ctrl+Tab；Ctrl+Tab 回來；再 Ctrl+Tab | 沒有訊息；包中的 `alpha.txt` 為 `41 EF BF BD 42`；第二次切走時 `st_mtime_ns` 不變（沒有重寫）；重新啟動：`alpha` 顯示 `A\ufffdB` | 每次切換都 `儲存文件失敗：'utf-8' codec can't encode character '\ud83d' ...`；關閉被 veto |
| 41（人工，使用者） | 在 NVDA 執行中，重做 38 直到對話框 | NVDA 讀出標題、錯誤那一行與句子，然後讀「重試 按鈕」（或 NVDA 的對應說法）；Tab 與 Shift+Tab 在三個按鈕間移動，NVDA 讀出每個按鈕的名稱；Alt+R、Alt+W 與 Esc 有作用。記錄 NVDA 的朗讀內容 | - |

預期改變的重跑（同樣的腳本透過 `rerun.py` 執行，替換 exe 與資料夾）：

- **19**（`alpha` 未變更，被共用 `r`、再 `rw` 開著，只改大小寫改名為 `Alpha`）：存檔被跳過，出現名稱對話框。改名接著以 `[WinError 32] ...: '...\alpha.dep' -> '...\.alpha.dep.<rnd>.tmp'` 失敗（F-3 D5）。清單與內容不變，沒有 `.tmp`，關閉會結束。之前（F-3）：存檔失敗，沒有名稱對話框。
- **20 / 20b**（`attrib +r`，未變更，改名）：出現名稱對話框，然後改名以 `[Errno 13] Permission denied: '...\alpha.dep'` 被拒（F-3 D7）。關閉會結束。之前：存檔先失敗，關閉被 veto（F-W10）。
- **33**（選做，Defender 開啟，20 次切換、每次切換前先編輯）：0 次失敗，沒有 `.tmp`，與 F-3 相同。

## 風險

- **已被改變的包若指紋未變就不會被重寫**（極低）。另一個程式必須在同一個檔案時間 tick 內，以相同大小的檔取代包，才會發生。`st_mtime_ns` 的單位是 100 ns，但 NTFS 只在系統時鐘 tick 更新修改時間（開發機量到 0.5 ms，Windows 預設 15.6 ms）；FAT 與 exFAT 是 2 s，網路磁碟另加 client 端的 metadata cache（SMB 預設 10 s）。app 自己的存檔（含 fsync）至少佔一個 tick，所以窗口仍然很小。那時沒有變更的文件會維持該程式寫入的內容，而今天的存檔會覆寫它；使用者自己的修改不會遺失，因為記憶體中的文件就是上次成功存檔的內容。（審查後更正，M-2：此項原寫「精確到 100 ns」。）
- **不儲存就關閉是自己選擇遺失修改**（低）。對話框預設重試，說明修改會遺失，具破壞性的按鈕永遠不是預設。螢幕報讀器使用者在聽到按鈕之前會先聽到這句說明。
- **編輯框會正規化的文件第一次算作有變更**（低）。載入的文字含 `\r`、`\r\n` 或 U+0000 時，第一次存檔時文件是「有變更」。若該包同時是唯讀或被鎖，第一個動作會像今天一樣被擋；這時關閉會提供對話框。
- **U+0000 截斷**（既有，不在範圍內）。Edit 控制項在 U+0000 處截斷，所以文字含 U+0000 的包開啟後第一次存檔會失去其後的內容。今天也是如此；列為後續工作。
- **無聲的替換**（低）。lone surrogate 變成 U+FFFD 時沒有訊息。它原本看不見、無法存檔又擋住 app；U+FFFD 是標準的可見標記。
- **工作階段結束**（低，D8）。Windows 結束工作階段時存檔失敗只會記 log。今天修改也會遺失，只是先出現一個沒有人能處理的訊息。
- **log 數量**（低）。關閉時的非 `OSError` 每次重試記一次。重試由使用者觸發。

## 待決問題

沒有。使用者已決定 A-D。D5（不動編輯框）、D8（不可 veto 的關閉）與對話框用字都從這些決定推出，記錄在上面以便審查。

## 不在範圍內／後續工作

- **文件文字中的 U+0000**：Edit 控制項在該處截斷（已量測），下一次存檔寫出截斷後的文字。今天也是如此。後續工作應決定在匯入與載入時保留、替換或拒絕 U+0000。
- **含 lone surrogate 的文字的轉換**：`get_source_text` 仍把編輯框的值傳給轉換。F-5 不改變它。
- **F 審查 M-2**（啟動時回收孤兒 `.tmp`）、**F-3 審查 M-1**（新增、改名、匯入或預設文件取代被保留的 invalid `.dep`）、**F-3 審查 M-6**（真實磁碟已滿與 7-Zip 的檢查）。
- 依原因區分的訊息（被鎖 vs 唯讀）、「已修改」標示、存檔命令、自動存檔。
- 其他地方的 **F-W9**（`localize_standard_buttons`、`wx.MessageBox` 的 OK 按鈕）：不碰。新對話框不使用它們。
