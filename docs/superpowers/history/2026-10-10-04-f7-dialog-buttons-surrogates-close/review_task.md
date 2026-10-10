# F-7 對話框按鈕本地化、surrogate 安全匯出、關閉重入審查記錄

- 日期：2026-10-10
- 範圍：worktree `D:\workspace\DotExpress-f7` 的 `fix/f7-dialog-buttons-surrogates-close`，`fb7aff9..HEAD`（`fb7aff9` = F-6 審查後的分支末端，等於 F-6 merge 後的 `main` tree；8 個 commit：`d10dd94` spec、`c6f24db` plan、`6898472` 按鈕只在自己的子視窗找、`8b786e2` 訊息框改走 helper、`ff5670d` 讀編輯框時替換 surrogate、`02bd44e` 匯出攔截所有例外、`ea39057` 關閉重入守衛、`4ee62c6` GUI 結果）。production diff `git diff fb7aff9..HEAD -- client`：16 個檔，+842／−77（新檔 `ui/message_box.py` 29 行、`tests/test_message_box.py` 166 行、`tests/test_wx_call_sites.py` 89 行；`gui.py` +60／−22、`dialog.py` +16／−10、`documents/export_coordinator.py` +19／−2、`settings/dialogs.py` +3／−2、`tests/wx_stub.py` +19／−1；8 個既有測試檔）。每個實作 commit 的 `HEAD:client` tree id（`f6a7409d…`、`79ee79a7…`、`7532bf2a…`、`f9563449…`、`652dabac…`，`4ee62c6` 與 `ea39057` 相同）都與 plan「Expected Counts」逐一相同。
- 對照：`docs/superpowers/history/2026-10-10-02-handoff/HANDOFF.md` §1、§2、§5.2、§5.3（使用者的決定 3：F-W9 只做 a＋b；決定 4：M-7 只替換程式拿到的文字，不改編輯框）、`AGENTS.md`、`docs/superpowers/specs/2026-10-10-f7-dialog-buttons-surrogates-close-design.md`（含 `_zh-TW.md`，各 663 行，含「Corrected after planning」／「規劃後的修正」13 點）、`docs/superpowers/plans/2026-10-10-f7-dialog-buttons-surrogates-close.md`、本資料夾的 `auto-results.md` 與 `auto/`、`2026-10-10-03-f6-unreadable-dictionaries/review_task.md`（格式）。
- 審查方式：逐行讀 5 個 production 檔的 diff 與 `localize_standard_buttons`、`FileIssuesDialog.__init__`、`DictionaryEntriesDialog._build_ui`、`_NameDialog`、`ui/dialog_base.py`、`_save_open_document_before_close`、`_ask_after_close_save_failure`、`_on_close` 一組、`close_converting_dialog`、`export_coordinator.py` 全文、`log.py`、`tests/file_log_isolation.py`、`tests/wx_stub.py` 的 `StubScope`；10 個測試檔的 diff；對 21 個訊息框呼叫端、每條讀取編輯框的路徑、匯出的兩條路徑、關閉的每個分支逐一推演；在 Windows 11 跑完整套件與焦點模組；每個實作 commit 的測試拿去跑其父 commit 的 production code（red-first 重放，`git archive` 到 scratchpad）；在 scratchpad 的 `client/` 副本自套 24 個 mutant（plan 的 26 個之外另寫的）；用真正的 wx 4.2.5 寫探針量 `message_box` 在 15 種樣式／按法下的按鈕文字、焦點與回傳值，以及 `FindWindow`／`FindWindowById`、`FileIssuesDialog` 與 `DocumentNameDialog` 的真實標籤；重跑 `msgfmt`、比對 catalog 與 fixture；稽核 `D:\dxtest\auto*-f7.log`、`auto*-f6b-f7.log` 十一個 log、exe 雜湊與時間戳；另以 pywinauto 在新的 `D:\dxtest\rev1-f7` 對 N-f7 補量「設定開著時名稱對話框第一次顯示」與真實按鍵的 Esc／Enter（只結束該資料夾底下的程序）。主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 在審查前後 sha256 相同；沒有啟動 source-run 的 `gui.py`；沒有動 `client2/`、`preprocessing/`、`testdata/`、主 checkout；沒有送出真的登出或關機。凡未能驗證的標為「推理」。
- 本記錄只寫檔，未 commit。

## 驗證（Windows 11 26200，`$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`，`$SP` = session scratchpad 的 `f7review\`）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| app data | 審查前後 `(find client/dictionary client/workspace client/log -type f; ls client/config.json) \| sort \| xargs sha256sum`，`diff` | 4 個檔（`config.json` `eea87b39…`、`dictionary/default.csv` `8f0594e9…`、`log/init.log` `1b787580…`、`workspace/new.dep` `d0cb6539…`）相同；worktree `git status --short` 全程為空（本記錄寫入前）；未 stage 任何東西 |
| 完整套件（驗收 1） | `cd client && $PY -B -X utf8 -m unittest discover -s tests` | `Ran 1365 tests in 16.747s`、`FAILED (errors=1, skipped=7)`；唯一 error 為 F-W6 `test_dictionary_name_prompt … test_case_only_rename_still_renames`。1365 = 1337 + 28，與 plan 相同。跑完 worktree 沒有 `client/log/`、`client/workspace/`、`client/config.json` |
| 焦點模組（驗收 2） | `$PY -B -X utf8 -m unittest tests.test_message_box tests.test_wx_call_sites tests.test_dialog_display tests.test_dialog_validation tests.test_converting_dialog tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_settings_dialogs tests.test_gui_document_flows tests.test_export_coordinator tests.test_wx_stub`（在 scratchpad 副本） | `Ran 471`、`OK` |
| red-first 重放 | `$SP\red_replay.sh`：對每個實作 commit 以 `git archive` 取出 `client/`，再用 `git show <parent>:<production 檔>` 覆蓋（新檔刪除），跑該 commit 動到的測試模組 | t1（`6898472` 於 `c6f24db`）：`Ran 82`，紅燈 7 = B1 的 3 個、B2、B3、B4、C3；t2（`8b786e2` 於 `6898472`）：`Ran 405`，紅燈 = C1、C2 兩個 FAIL ＋ 211 個 ERROR（re-pointed 測試 patch 不存在的 `message_box`，與 Corrected 4 的預測相同）；t3（`ff5670d` 於 `8b786e2`）：`Ran 187`，紅燈 D1、D2、D3；t4（`02bd44e` 於 `ff5670d`）：`Ran 27`，紅燈 D4、D6、D7、D8 與改寫的 defect-7 測試（D5、import 測試改前就綠，與 spec「guards the existing behavior」一致）；t5（`ea39057` 於 `02bd44e`）：`Ran 191`，紅燈 E1、E2、E4（E3 改前就綠，與 spec 一致） |
| 自套 mutant（24 個，plan 之外） | `$PY -B -X utf8 $SP\mutants.py $SP\copy\client`（副本不含 `.venv`、`dictionary/`、`workspace/`、`config.json`、`log/`；每個 mutant 跑對應模組，跑完還原） | 21 個被抓到：x01 helper 的 YES_NO 判斷反轉、x02 標籤在 `ShowModal` 之後才設、x03 未知回傳映成 OK、x04 `parent` 改用關鍵字傳、x05 不用 `with`（不 Destroy）、x06 `_closing` 在檢查前就設（永遠當重入）、x07 可否決的重入否決後又存一次、x08 巢狀關閉完成後外層仍 `Veto`、x09 `_finish_close` 不 `Skip`、x11 不可否決的重入只 `Skip` 不走 `_finish_close`、x12 `_closing` 不在 `finally` 重設、x13 `_editor_text` 回寫編輯框（違反 D5）、x14 只替換 `input_txt` 不替換 `output_txt`、x15 非預期匯出錯誤用 WARNING、x16 不帶 traceback、x17 單檔失敗後仍顯示成功、x18 批次失敗不列入摘要、x19 logger 改名、x20 `FindWindow` 找不到時退回 `FindWindowById`、x21 編輯器綁到 `ID_CANCEL`、x22 FileIssues 用 `OK\|CANCEL` 本地化。3 個存活：x10（`_save_open_document_before_close` 在 `_close_finished` 時回 `False`）等價，因為 `_close` 先檢查 `_close_finished` 再看 `may_close`；x23（`from wx import MessageBox as message_box`）、x24（`import wx as _wx; message_box = _wx.MessageBox`）是掃描測試的盲點，見 M-1 |
| 真 wx 探針 | `cd client && $PY -u -B -X utf8 $SP\probe_wx.py`（wx 4.2.5 msw、wxWidgets 3.2.9；自己建 frame，用 driver thread 以 `EnumThreadWindows` 找 task dialog、`EnumChildWindows` 讀按鈕、`GetGUIThreadInfo` 讀焦點、`TDM_CLICK_BUTTON`／`WM_CLOSE` 操作；不注入前景按鍵） | 見 §2 |
| catalog（驗收 4） | `git diff fb7aff9..HEAD --stat -- client/locales`；`msgfmt --check --statistics -o /dev/null …po`；`grep -c '^msgid '`、`grep -c '^#, fuzzy'`；`git log -1 -- client/locales` | locale diff 為空；`364 translated messages.`；`.po` 365 個 `msgid` 行（364 + header）、0 fuzzy；三個 locale 檔最後一次改動是 F-6 的 `aec3c64`（本任務沒有碰，D8） |
| fixtures、受限檔案（驗收 5–7） | `git show HEAD:client/tests/fixtures/…\| sha256sum` × 2；`git diff fb7aff9..HEAD --stat -- client/braille AGENTS.md`；`git ls-files --eol`；`git diff --name-only fb7aff9..HEAD` | `e67d95a1…1ccd`、`f493da52…c2cf`，與要求相同；`client/braille`、`AGENTS.md` 不在 diff 中；`client/braille/tables/__init__.py` 仍是 `i/crlf`（371 個 CR）；所有改動的 `.py` 在 index 都是 `i/lf`；diff 正是 16 個 client 檔 + 9 個 docs 檔（spec 驗收 7 的清單） |
| 縮排／ASCII | `grep -c $'^\t'`／`'^    '` 逐檔 | tab 檔：`dialog.py`、`gui.py`（`documents.workspace` 的 import 清單本來就是 4 空白）、`test_dialog_display.py`、`test_dictionary_management_dialog.py`、GUI 腳本（0 行以 4 空白開頭）；4 空白檔：`ui/message_box.py`、`documents/export_coordinator.py`、`settings/dialogs.py`、其餘測試檔（0 個 tab）。`ui/message_box.py`、`test_wx_call_sites.py`、GUI 腳本是純 ASCII；測試中的 surrogate 以 `chr(0xD83D)` 建立、U+FFFD 寫成字元本身，沒有 `\u` escape（HANDOFF §2 的 Edit／Write 陷阱沒踩到） |
| commit | `git log --format='%h %s%n%(trailers)' fb7aff9..HEAD` | 8 個 commit 都以 `Co-Authored-By: Claude Opus 5.5` 結尾；沒有 merge、沒有 push；時間順序 spec 12:52 → plan 14:07 → t1–t4 14:10–14:12 → D9 的 `auto58-f6b-f7.log`／`auto54-f6b-f7.log` 14:12–14:13 → t5（D7）14:15 → N-f7 build 14:19 → GUI 14:20–14:24 → docs 14:26，與 D9「先在舊 build 重現再寫 D7」一致 |
| GUI 結果稽核 | 讀 `D:\dxtest\auto{53,54,58,59,60,61,64a,64b}-f7.log` 與 `auto{53,54,58,61}-f6b-f7.log`；`sha256sum D:\dxtest\N-f7\DotExpress.exe` | 十一個 log 的關鍵行（53／54 的 `buttons`、55 的 `reopened rows` 與 `d1.csv` 位元組、58 的 `close dialogs within 3 s` 與 `call:`、59／60 的 `call:`、61 的點字與 `same as for U+FFFD`、62／63 的訊息框與檔案）都與 auto-results 逐字相符；改前（N-f6b）確實是 `['OK']`、`['OK', 'Cancel']`、`reopened rows: []`、`2` 個關閉對話框、`not returned`／`after_s 3.7`、`62 export html: None`；exe `8fb58561…1819f`、48,752,069 bytes，與 auto-results 相同；每個 `auto*-f7` 資料夾只有一個 log |
| 補量（rev1-f7） | `$SP\uia\Scripts\python.exe $SP\rev1.py D:\dxtest\N-f7\DotExpress.exe D:\dxtest\rev1-f7`（uia venv 依 HANDOFF §8 重建：pywinauto 0.6.9 + psutil；資料夾新建；結束後沒有 exe 位於 `D:\dxtest\rev*` 的程序） | 見 §2 |
| 未執行 | — | plan Task 7 Step 3 的 shuffle（工具未 commit；新測試都用獨立暫存目錄並隔離 logger，推理不互相影響）；POSIX-only 測試；items 53–64 重跑（結果檔與 log 沒有可疑處）；item 65（NVDA，仍待使用者）；F-W6 |

## 結論

**Ready**（item 65 NVDA 仍待使用者人工，與 auto-results「仍需人工」一致）。

沒有 Critical、沒有 Important。F-W9 的兩個根因都被堵住：`localize_standard_buttons` 與字典編輯器改用 `dialog.FindWindow(id)`，真 wx 探針與 GUI 55 證實編輯器的「確定」會存檔、另一個非 modal 對話框的按鈕不受影響；21 個訊息框全部改走 `ui.message_box.message_box`，探針證實它是 `wx.MessageBox` 的 drop-in（同樣的引數順序與位置參數 `parent`、OK 框的 Enter／Esc／關閉鈕都回 `wx.OK`、是／否框保留系統按鈕與原本的預設焦點、`ID_YES`／`ID_NO`／`ID_CANCEL` 的映射和 `wxMessageBox` 相同）。M-7 在 `_editor_text` 一處收口，production 只剩這一個 `GetValue()`，編輯框沒有任何回寫；匯出兩條路徑都攔 `Exception`、只對非 `OSError` 寫 traceback、批次繼續並列入摘要，順帶修掉 P1-4 defect 7。M-5 的守衛在可否決的重入立刻 `Veto`、不可否決的走一次 D8，`_closing` 在 `finally` 重設，GUI 58–60 與 F-5 的 38／39 重跑都和預期一致。catalog 逐位元組未動、364／0 fuzzy；fixture、受限檔案、使用者資料都沒動。red-first 可重放；24 個自套 mutant 只有 3 個存活（1 個等價、2 個掃描盲點）。下面 7 個 Minor 中，M-1、M-2、M-3 便宜，建議 merge 前一起修；M-4 到 M-6 是觀察與 follow-up；M-7 是待使用者的 NVDA 項目。O1、O5、O6 三個預設請使用者看一眼。

## 1. 逐路徑分析

### 1.1 `message_box` 是不是 `wx.MessageBox` 的 drop-in（D2、D3，21 個呼叫端）

| 面向 | 結果 | 依據 |
| --- | --- | --- |
| 引數順序與型別 | `(message, caption, style, parent=None)`，與 `wx.MessageBox(message, caption, style, parent)` 相同；site 19（`DotExpressSettingsDialog._collect`）仍以位置參數傳 `self`；其餘 20 處 `parent=self` 或不傳（site 17 啟動錯誤，當時沒有 frame） | diff；T A5；探針 `ok-info positional parent`、`ok-info no parent` |
| 樣式原樣送進 `wx.MessageDialog` | icon、`NO_DEFAULT`、`YES_DEFAULT` 都不動；OK 框只 `SetOKLabel`，OK＋Cancel 才 `SetOKCancelLabels`，含 `YES_NO` 的完全不設標籤 | `ui/message_box.py:22-28`；T A1–A3；mutant x01 |
| 回傳值 | `ID_OK→OK`、`ID_YES→YES`、`ID_NO→NO`、其他→`CANCEL`，與 wxWidgets `wxMessageBox` 的 switch 相同（`ID_HELP` 例外，沒有呼叫端用 `wx.HELP`）；4 個是／否呼叫端仍比 `== wx.YES`／`!= wx.YES` | T A1–A4；探針：OK 框按 OK／`IDCANCEL`（Esc）／`WM_CLOSE` 都回 `wx.OK (4)`；是／否框 `IDNO→wx.NO (8)`、`IDYES→wx.YES (2)`；OK＋Cancel 的 Cancel／關閉鈕→`wx.CANCEL (16)` |
| 按鈕文字與焦點 | OK 框：`['確定']`、焦點「確定」；`wx.MessageBox` 同樣式：`['OK']`；是／否（`NO_DEFAULT`）：`['是(&Y)', '否(&N)']`、焦點「否」；是／否（預設 Yes）：焦點「是」；OK＋Cancel：`['確定', '取消']`、焦點「確定」 | 探針 15 個案例；GUI 53、54、56、57、64 |
| 對話框生命週期 | `with wx.MessageDialog(...) as dialog` 離開時 Destroy，等於 `wxMessageBox` 的區域變數 | T A1 的 `enter`／`exit` 事件；mutant x05 |
| 21 個呼叫端的訊息、標題、樣式、owner、回傳值用法 | 逐一比對 diff：只有函式名從 `wx.MessageBox` 變 `message_box`，引數一字不差；`on_about` 由 `wx.MessageDialog(self, …).ShowModal()` 改為 `message_box(about.aboutMessage, _("About DotExpress"), OK \| ICON_INFORMATION, parent=self)`（原本也不用回傳值） | diff；re-pointed 測試的斷言一條都沒改（C4）；新測試 site 1、site 20 |
| 每個呼叫端至少一個斷言引數的測試 | sites 1（新）、2（name harness）、3／4（editor harness）、5／6／7（management view）、8（`_show_file_error`）、9（text processing OSError）、10（name prompt）、11／12（delete，回傳值）、13／14（`show_info`／`show_error`）、15（`show_warning`）、16（`confirm_overwrite_all`，回傳值）、17（startup）、18（新增完整斷言）、19（settings `_collect`）、20（新）、21（F-6 守衛的兩個測試） | plan Corrected 4、5；mutant 清單的四個 `*-back-to-wx-message-box` |
| 與 `wx.MessageBox` 唯一的差異 | `wxMessageBox` 在樣式沒有任何 icon 時會自動補 `ICON_INFORMATION`（有 `YES` 時 `ICON_QUESTION`）；helper 不補。21 個呼叫端都有明確 icon，所以今天沒有差異；只影響未來的呼叫端 | wxWidgets 3.2 `wxMessageBox` 原始碼（推理）；見 M-2 |
| Esc 與關閉鈕 | OK 框：Esc 與關閉鈕都關閉並回 `wx.OK`（與改前相同）；是／否框沒有 Cancel，task dialog 不接受 Esc／關閉鈕（探針送 `WM_CLOSE` 被忽略），這與 `wx.MessageBox` 改前完全相同，不是 F-7 的改變 | 探針；GUI 56（Esc 關掉「轉換完成。」）、rev1（About 以真實 Esc 關閉，之後沒有殘留框） |

### 1.2 按鈕查找（D1）

| 路徑 | 結果 | 依據 |
| --- | --- | --- |
| `localize_standard_buttons` | `dialog.FindWindow(button_id)` 只搜自己與子孫；`button_sizer` 的 getter 退路保留但在 wxPython 4.2.5 永遠不存在（O4） | 探針 `StdDialogButtonSizer getters: []`、`FindWindow own: True`、`FindWindowById global: True`（另一個非 modal 對話框的 `ID_OK`）；T B1、B2；mutant x20 |
| 字典編輯器的 OK 綁定（遺失編輯的缺陷） | `self.FindWindow(wx.ID_OK)` → 自己的按鈕 → `_on_ok` 先 `save` 再 `Skip` | T B3（另一個對話框的按鈕沒有任何 binding、標籤仍是 `OK`／`Cancel`）；GUI 55 改前 `reopened rows: []`、改後 `[['x', '1', '一般']]` 且 `d1.csv` 有該列；mutant x21 |
| 名稱對話框、字典管理 | 本來就用 `self.Bind(..., id=wx.ID_OK)`／`id=wx.ID_CLOSE` 綁在對話框上，不受 `FindWindowById` 影響；只有標籤修正 | 程式碼；GUI 53、54（重新顯示時 `['確定', '取消']`）；rev1（設定開著時第一次顯示就是 `['確定', '取消']`，設定自己的按鈕仍是 `['確定', '取消', '套用']`） |
| `FileIssuesDialog` | `if button_sizer:` 內呼叫 `localize_standard_buttons(self, wx.OK, button_sizer)`（`wx.Sizer` 為真，探針 `sizer truthy: True`） | T B4；探針 `FileIssuesDialog OK label: '確定'`，同時另一個對話框的 OK 仍是 `'OK'`；mutant x22 |
| `FindWindow` 找到同 id 的巢狀子視窗 | 編輯器建構時 `AddSymbolDialog`（有 `wx.Button(self, wx.ID_OK)`）尚未存在，`FindWindow` 只呼叫一次；名稱對話框沒有其他 `ID_OK` 子視窗 | 程式碼（推理，spec Risks 已列） |

### 1.3 落單 surrogate（D5）

| 路徑 | 結果 | 依據 |
| --- | --- | --- |
| production 讀編輯框的地方 | `grep GetValue` 只剩 `gui.py:626` `_editor_text`；`_save_open_document` 兩個引數與 `get_source_text` 都經過它；`SetValue` 只在開啟文件、清空與 `show_conversion_output`，沒有 `ChangeValue` | grep；T D1（`mock_calls == [call.input_txt.GetValue()]`）；mutant x13、x14 |
| 轉換、雙視窗、controller 副本 | `ConversionRequest.raw_text` 已是 U+FFFD，`_complete_manual` 存進 controller 的也是；輸入框不變 | T D3；GUI 61（點字與直接輸入 U+FFFD 相同、輸入框仍是 U+0041 U+D83D U+0042） |
| 存檔 | `prepare_document_for_save` 拿到的文字與改前（F-5 D4 之後）相同，F-5 的比較基準不變；documents 層的替換仍在 | T D2；既有 F-5 測試 `…x\ud800…` 照過 |
| 匯出 HTML／全部匯出 | 轉換後的 segments 不再帶 surrogate，`UnicodeEncodeError` 不再發生 | GUI 62（`EF BF BD: True`、`ED A0 BD: False`）、63 |
| 其他輸入（字典項目、文字處理腳本） | 不變（spec Out of Scope） | — |

### 1.4 匯出錯誤（D6）

| 路徑 | 結果 | 依據 |
| --- | --- | --- |
| 單檔，非 `OSError` | `except Exception` → log traceback → `show_error(Failed to export document: …)`，不顯示成功 | T D4、D6、D8；mutant x15–x17 |
| 單檔，`OSError` | 訊息同改前、不寫 log | T D5（`assertNoLogs`）；GUI 56 的摘要 `[Errno 13]` |
| 全部匯出，中間一份非 `OSError` | `add_failure(document.name, str(exc))` → `continue_batch()` → 其他文件照寫、摘要列出失敗、一筆 log | T D7（alpha、gamma 寫出，摘要 `beta: injected`）；mutant x18 |
| 全部匯出，格式沒有 writer（P1-4 defect 7） | `get_format("txt")` 本身成立（`export_all:127` 只取 `.extension`），`write_document` 才拋 `ValueError`，現在每份都列入摘要、兩筆 log | 改寫的 defect-7 測試 |
| 轉換失敗的 callback | 不變 | diff |
| logger | `get_logger("dotexpress.gui", "gui.log")` 在 `_log_unexpected_export_error` 內才綁定（同 F-6 M-6）；`get_logger` 遇到已有 handler 不再加；模組仍不 import `wx`／`gui` | `log.py:18`；T `test_importing_binds_no_log_file`、`test_module_imports_neither_wx_nor_gui`；mutant x19 |
| 半套檔案 | writer 用 `Path.write_text`，失敗仍可能留下空檔或半檔（spec Corrected 11 已列為 follow-up）；F-7 之後只剩 writer 的 bug 會走到這裡 | 推理 |

### 1.5 關閉重入（D7）

| 路徑 | 結果 | 依據 |
| --- | --- | --- |
| 可否決的重入（`WM_QUERYENDSESSION` 在 F-5 對話框開著時） | `_closing` 為真 → `_on_close_reentered` → `evt.Veto()`，不存檔、不開第二個框、不寫 log；外層對話框照常決定 | T E1（`replace` 1 次、`MessageDialog` 1 個、inner `Veto` 1 次）；GUI 58（`close dialogs within 3 s: 1`、`after_s 0.0`、`result 0`，改前 2 個框、3.7 s）；mutant x06、x07 |
| 不可否決的重入（防禦；wx 3.2.9 的工作階段結束不會產生） | D8 一次（存檔、失敗寫 `Failed to save the open document while closing`）→ `_finish_close`：`_close_finished = True`、關 converting dialog、Destroy 雙視窗、`Skip`；外層對話框回來後 `_save_open_document_before_close` 回 `True`，`_close` 看到 `_close_finished` 直接 return（不 `Veto`、不 `Skip`、不重試） | T E2；mutant x08、x11 |
| 旗標重設 | `_closing` 在 `finally` 重設：Cancel（`Veto`）、Retry 後成功、例外都會回 `False`；下一次關閉照常 | T E3、E4；mutant x12 |
| 類別屬性 | `_closing`／`_close_finished` 以類別屬性當預設，實例上才寫入；`object.__new__` 建的測試 frame 讀到 `False`；沒有跨實例或跨測試洩漏（寫入永遠是 `self.<attr> = …`） | 程式碼；T E4 的 `vars(frame).get("_closing")` |
| 無重入時 | `_close` 是原本 `_on_close` 的主體，順序不變：轉換中→`Veto`；存檔→對話框迴圈→`Veto` 或 `_finish_close` | 既有 F-5 關閉測試全綠；GUI 59（沒改動時 `result 1`、程式自行結束）、64（F-5 的 38／39 重跑相同，只有錯誤框按鈕變「確定」） |
| `WM_ENDSESSION` | wx 直接 `OnExit`／`exit()`，沒有關閉事件；套件是最後一次成功存檔、無 `.tmp` | GUI 60 |
| 與 F-5 對話框的互動 | 「重試」迴圈中 `_closing` 一直為真，期間所有可否決的關閉事件都被否決；「不儲存就關閉」→`_finish_close`；「取消」→`Veto` | 程式碼；T E1 |
| 真實登出時的使用者體驗 | DotExpress 回「不可結束」，Windows 顯示「此應用程式阻止登出」，使用者回到對話框決定（O6，by design） | spec Risks；推理 |

## 2. 補量

### 2.1 真 wx 探針（`$SP\probe_wx.py`，wx 4.2.5 msw、wxWidgets 3.2.9、zh-TW Windows）

| 案例 | 按鈕 | 焦點 | 動作 → 回傳 |
| --- | --- | --- | --- |
| `message_box(OK \| ICON_ERROR, parent=frame)` | `['確定']` | 確定 | 按 OK → `wx.OK`；`TDM_CLICK_BUTTON IDCANCEL`（Esc 的內部等價）→ `wx.OK`；`WM_CLOSE` → `wx.OK` |
| 同上 `parent=None`／位置參數 `frame`／只有 `wx.OK` 沒有 icon | `['確定']` | 確定 | `wx.OK` |
| `wx.MessageBox(OK \| ICON_ERROR)`（改前） | `['OK']` | OK | `wx.OK` |
| `YES_NO \| NO_DEFAULT \| ICON_WARNING` | `['是(&Y)', '否(&N)']` | 否 | `IDNO` → `wx.NO (8)`；`IDYES` → `wx.YES (2)`；`WM_CLOSE` 被忽略（沒有 Cancel；與 `wx.MessageBox` 相同） |
| `YES_NO \| ICON_WARNING` | 同上 | 是 | `IDNO` → `wx.NO` |
| `OK \| CANCEL \| ICON_WARNING`（目前沒有呼叫端） | `['確定', '取消']` | 確定 | `IDCANCEL` → `wx.CANCEL`；`IDOK` → `wx.OK`；`WM_CLOSE` → `wx.CANCEL` |
| 非 modal 對話框（`wx.Button(ID_OK)`）開著時建一個 `CreateButtonSizer(OK\|CANCEL)` 的對話框 | `FindWindow(ID_OK)` 是自己的、`FindWindowById(ID_OK)` 是另一個對話框的；`StdDialogButtonSizer` 沒有任何 `Get*Button` | — | — |
| 同情境建真的 `FileIssuesDialog`／`DocumentNameDialog` | `'確定'`／`'確定' '取消'`；另一個對話框的 OK 仍是 `'OK'` | — | — |

### 2.2 packaged build 補量（`D:\dxtest\rev1-f7`，N-f7）

| 量測 | 結果 |
| --- | --- |
| 「DotExpress 設定」開著時「檔案 → 新增」 | 名稱對話框**第一次**顯示就是 `['確定', '取消']`；設定的按鈕仍是 `['確定', '取消', '套用']`（行為表第三列，spec 原本只有 code reading） |
| 同時「字典管理 → 新增」 | `['確定', '取消']`；設定不受影響；Esc、關閉字典管理、設定的取消都正常，`windows: []` |
| 「關於」以真實 Esc 鍵關閉 | 框 `['確定']`、焦點「確定」、按一次即關；之後 2 秒內沒有殘留框 |
| 「轉換完成。」以 Enter 關閉 | 同上；`gui.log` 無內容；程式正常結束 |

## 3. Logging、測試隔離、測試品質

- `export_coordinator` 延遲綁定 logger；`test_export_coordinator` 在 `setUpModule` 以 `isolate_file_logs("dotexpress.gui")` 隔離並在每個會記錄的測試用 `assertLogs`／`assertNoLogs`；`test_gui_document_flows` 本來就隔離。完整套件與副本跑完後，worktree 與副本都沒有 `client/log/`。
- `test_importing_binds_no_log_file` 以 subprocess import，斷言 `dotexpress.gui` 沒有 handler；mutant「logger 綁在 import 時」由它抓到（plan 的 `export-logger-bound-at-import`）。
- 掃描測試（C1–C3）以 AST 掃 `client/` 下所有 `.py`（排除 `tests`、`.venv`、`build`、`dist`、`mathcat`、`braille/liblouis`），命中回報 `<file>:<class>.<function>`；巢狀函式、class body、lambda 都會遞迴；`test_scan_reads_the_production_modules` 保證掃描不是空的。盲點：只認 `wx.MessageBox(...)` 這種「名稱 `wx` 的屬性呼叫」，`from wx import MessageBox` 或 `import wx as x` 會漏掉（mutant x23、x24 存活，見 M-1）；另外它也會 parse git-ignored 的 `braille/louis_helper.py` 與任何遺留在 `client/` 的草稿 `.py`（見 M-6）。
- 關閉重入測試用對話框的一次性 hook 在 `ShowModal` 內送第二個事件，模型與真實情況（modal 迴圈中送達）一致；`_assert_close_dialogs` 斷言事件只有一個對話框。E2 的 `replace.call_count == 2` 把「不可否決的重入存一次」釘住。
- re-pointed 測試只改 patch 目標，斷言一條都沒改；site 18 的測試從 `assert_called_once()` 升級為完整引數（C5）。
- 編輯器 harness 同時保留 `FindWindow`（自己的）與 `FindWindowById`（模擬全域搜尋，可指定舊視窗的按鈕），所以既有 80 多個編輯器測試在 D1 前後都過，B3 才能專門驗證綁定對象。
- 存活的 x10 是等價 mutant，不建議補測。

## 4. 本地化（D4、D8）

- 沒有新字串；helper 只用既有的 `OK`→「確定」、`Cancel`→「取消」。`.pot`／`.po`／`.mo` 與 `fb7aff9` 逐位元組相同，`msgfmt` 364 translated、0 fuzzy。
- 仍是英文的可見字串都是既有缺陷、與 F-7 無關：全部匯出的摘要標題「Export Complete with Errors」與內文「Exported documents: …」、「All documents were exported successfully.」（P1-4 defect 4；GUI 56、63 的 log 可見）；關於對話框內文 `DotExpress (DotExpress) …`。是／否按鈕是系統文字（O1）。
- `.pot`／`.po` 的 `#:` 參照行號因 `dialog.py`、`gui.py`、`settings/dialogs.py`、`export_coordinator.py` 的行移動而過期，且 `ui/message_box.py` 的 `OK`／`Cancel` 參照沒有列入；spec Corrected 9 刻意留到下一次字串變更再重產，可接受（見 §7）。

## 5. 文件與流程

- spec（EN／zh-TW 各 663 行、章節對應）、plan、auto-results、實作四者一致：D1–D9 都找得到對應程式與測試；Corrected 1–13 都反映在實作（21 個呼叫端、`Ran` 1342/1352/1355/1361/1365、scan 模組、re-pointing 放在綠燈步、harness 雙查找、stub scope、延遲綁定、defect 7、catalog、GUI 腳本與編號、62／63 的空檔、D9 由 planner 與實作者各做一次）。
- HANDOFF §5.3 決定 3（只做 a＋b）與決定 4（不改編輯框）都照做；§5.2 建議的「匯出攔所有 Exception、檢查 export_all 批次」「先用 pywinauto 確認 M-5 再加 `_closing`」都做到了，且 D9 在舊 build 的重現發生在 D7 commit 之前（時間戳見驗證表）。
- O1–O9 的預設都是保守的；實作與預設相符。
- plan 沒有「Implementation Notes」一節（HANDOFF §3 說 plan 末尾有；F-6 審查 M-7 也要求過）。因為實作的五個 tree id 與 dry run 逐一相同、沒有偏離，可接受，但建議補一句，見 M-3。
- spec Out of Scope 說 F-5 spec D8 的「wx 會在可否決的 query-end-session 關閉之後再送一個不可否決的關閉」已量到在 wx 3.2.9 不成立，「審查可以在那裡加註」。本記錄不改檔，請修正者一併加，見 M-3。
- GUI 腳本只以 `dx.kill_under(d)` 結束該資料夾下的程序，`lock.py` 以 `taskkill /T`；工作階段訊息只用 `SendMessageTimeoutW` 送給受測程序的主視窗；沒有碰 `D:\dxtest\N*` 與既有 `auto*`。item 65 的人工步驟寫在 auto-results，清楚可照做，沒有被代為勾選。
- `AGENTS.md` 是 git-ignored，無法以 git 確認本任務沒改它（推理：diff 與 commit 都沒碰；本審查也沒改）。

## 6. 發現

### Critical

無。

### Important

無。

### Minor

**M-1 掃描測試認不出別名或 `from wx import …` 的呼叫**（`client/tests/test_wx_call_sites.py:48-57` `is_wx_call` 只接受 `wx.<name>(...)`；mutant x23 `from wx import MessageBox as message_box`、x24 `import wx as _wx; message_box = _wx.MessageBox` 都存活）
- 情境：日後有人用別名或直接 import `MessageBox`／`MessageDialog`／`FindWindowById`，C1–C3 不會變紅。今天的 production 沒有任何 `from wx import` 或 `import wx as`（`grep` 確認），所以只是守門的盲點，不是缺陷。
- 建議（便宜，約 10 行＋2 個斷言）：在同一個模組加一個 predicate，`ast.ImportFrom` 且 `module == "wx"` 且 `names` 含 `MessageBox`／`MessageDialog`／`FindWindowById` 的算命中；`ast.Import` 的 `wx` 若有 `asname` 也算命中（或改成「只允許 `import wx`」）。各加一個 `assertEqual(find_in_production(...), [])`。

**M-2 `message_box` 與 `wx.MessageBox` 唯一的語意差異沒有寫在 docstring**（`client/ui/message_box.py:15-21`）
- 情境：`wxMessageBox` 在樣式沒有任何 `ICON_*` 時會自動補 `ICON_INFORMATION`（含 `wx.YES` 時補 `ICON_QUESTION`），helper 不補；探針「只有 `wx.OK`」的案例只確認按鈕與回傳值，icon 沒量。21 個呼叫端都給了明確 icon，今天沒有差異；只影響未來的呼叫端。
- 建議（便宜，二選一）：(a) docstring 加一句「呼叫端必須自己給 icon；helper 不像 `wx.MessageBox` 那樣補預設 icon」；(b) 照 wx 補兩行 `if not style & (wx.ICON_MASK | wx.ICON_NONE): style |= wx.ICON_QUESTION if style & wx.YES else wx.ICON_INFORMATION` 並加一個測試。建議 (a)，因為 spec D2 說「style 原樣送進 `wx.MessageDialog`」。

**M-3 文件的小修**（便宜）
- `docs/superpowers/plans/2026-10-10-f7-dialog-buttons-surrogates-close.md` 末尾補一節「Implementation Notes」：一句「實作依 plan 套用，Task 1–4、6 的 tree id 與 dry run 逐一相同，沒有偏離；Task 5／8 的 exe 雜湊與結果見 auto-results」，並列出本審查的修正。
- `docs/superpowers/specs/2026-10-10-f5-save-failure-handling-design.md` D8（第 197 行）的「wx only sends a non-vetoable close after the vetoable query-end-session close…」加一行「Corrected after the F-7 review (2026-10-10)：在 wx 3.2.9 量到工作階段結束不會產生任何關閉事件（`WM_ENDSESSION` 直接 `OnExit`／`exit()`），D8 的路徑只剩 `Close(force=True)` 會走到；見 F-7 spec Current State M-5」。zh-TW 版同步。

**M-4 匯出失敗仍可能留下空檔或半檔**（`client/documents/formats.py` 的 writer 用 `Path.write_text`；spec Corrected 11）
- 情境：F-7 之後 surrogate 不再觸發，但任何 writer 的 bug 或編碼錯誤仍會在報錯前留下一個空的／不完整的匯出檔，摘要說失敗，檔案卻存在。既有行為，spec 已列為 follow-up。
- 建議：follow-up（可與 HANDOFF §6「`save_preprocessing_script`、`config.json` 改走 `write_text_atomically`」同一批）：writer 改走 `write_bytes_atomically`／`write_text_atomically`。不在 F-7 修。

**M-5 一次完成的關閉之後、frame 銷毀之前若再來一個關閉事件，會多做一次存檔並且不 `Veto` 也不 `Skip`**（`client/gui.py:1044-1048` `_close`；`_close_finished` 不重設，推理）
- 情境：使用者按 X 關閉成功（`Skip` 後 wx 排程 Destroy）後、idle 之前恰好收到 `WM_QUERYENDSESSION`。`_closing` 已重設，所以走 `_close`：再存一次（沒改動就不寫，F-5 D2），然後因 `_close_finished` 為真直接 return。改前同情境會再存一次並再 `Skip` 一次。兩者對使用者都沒有可見差異，frame 都會銷毀；只是記下來讓下一位代理知道 `_close_finished` 也擋了這條路。
- 建議：不處理；若要更明確，可在 `_close` 開頭就檢查 `_close_finished` 並 `Veto`／return（省掉那次存檔），但沒有必要。

**M-6 掃描測試會 parse 工作目錄裡所有非排除的 `.py`，包括 git-ignored 的 runtime 副本與草稿檔**（`client/tests/test_wx_call_sites.py:14-24` `production_sources`）
- 情境：`braille/louis_helper.py`（NVDA 衍生、git-ignored）每次都被 parse；若有人在 `client/` 留下一個語法錯誤的草稿 `.py`，整個模組會以 `SyntaxError` 失敗，訊息不會指出是哪個檔。
- 建議（可選，便宜）：`ast.parse` 包一層，失敗時 `self.fail(f"{name}: {exc}")`；或只掃 `git ls-files` 列出的檔。

**M-7 item 65（NVDA）仍待使用者**（auto-results「仍需人工」）
- 請在 NVDA 下確認：(a) 「已存在」錯誤框讀出「確定」、重新顯示的名稱對話框 Tab 到按鈕時讀出「確定」「取消」；(b) 關於對話框的按鈕讀出「確定」；(c) 文字處理開著時字典編輯器的按鈕讀出「確定」「取消」，按確定後那一筆仍在。步驟與資料夾（`D:\dxtest\manual65-f7\`）見 auto-results。

### 請使用者確認的預設（orchestrator 採用的 O1–O9 中與可見行為有關的三個）

| # | 預設 | 影響 |
| --- | --- | --- |
| O1 | 是／否框不設 app 自己的標籤，用系統的「是(Y)／否(N)」；不加 `&Yes`／`&No` 兩個 msgid | 在非繁中的 Windows 上，是／否會是該系統語言（與改前相同）；而且是／否框沒有 Cancel，Esc 與關閉鈕都無效（與改前相同，§1.1 最後一列） |
| O5 | 非 `OSError` 的匯出錯誤寫進 `gui.log`（`dotexpress.gui` logger，與存檔錯誤同一個檔）；`OSError` 只顯示訊息不記錄 | 與 F-3 M-3 的存檔策略一致 |
| O6 | 關閉對話框開著時的 `WM_QUERYENDSESSION` 被否決、不記錄；真的登出時 Windows 會顯示「DotExpress 正在阻止登出」，使用者回到對話框決定；若選「仍要登出」，wx 直接結束，上次成功存檔之後的修改遺失（套件完整） | 改前是巢狀第二個對話框後才到同一個選擇；這是 F-5 決定 B（不默默遺失修改）的延伸 |

## 7. 其他觀察（不需處理）

- `test_message_box.py` 是新檔卻含非 ASCII（「確定」「取消」的斷言）；AGENTS.md 的「預設 ASCII」是「預設」，這裡釘住 zh-TW 的實際標籤是合理的，不算違規。
- `.pot`／`.po` 的 `#:` 參照目前過期（行號移動、`ui/message_box.py` 未列）；`msgfmt` 不看 `#:`，`.mo` 不受影響；下一個有字串變更的任務跑 `generate-pot.bat`＋`msgmerge` 時會一起更新（POT-Creation-Date 固定為 `2026-10-10 12:00+0800`，可重現）。
- `test_importing_binds_no_log_file` 的 subprocess 沒帶 `-B`，會在 `client/` 下產生 `__pycache__`（git-ignored），無害。
- `_export_next` 的 `result.add_failure(document.name, …)` 用的是原文件名而非轉換後副本 `export_document.name`，兩者相同（既有程式）。
- `wx.Window.FindWindow(id)` 在 wxPython 有 `(id)` 與 `(name)` 兩個 overload，傳 `int` 走 id 版；若傳到字串會變成以名稱找，現有呼叫都是 `wx.ID_*` 常數。
- 審查工具（`$SP\probe_wx.py`、`mutants.py`、`red_replay.sh`、`rev1.py`）與副本都在 scratchpad，未放進 repo；`D:\dxtest\rev1-f7` 與 `rev1-f7.log` 是本次新建的補量資料夾，沒有動其他 `D:\dxtest` 內容；`$SP\uia` 是依 HANDOFF §8 重建的 pywinauto venv。

## 修正記錄

- 日期：2026-10-10，由 Claude 執行；worktree `D:\workspace\DotExpress-f7`，分支 `fix/f7-dialog-buttons-surrogates-close`，起點 `4ee62c6`。沒有 merge 進 `main`、沒有 push、沒有切換分支；沒有啟動 source-run 的 `gui.py`。主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 在修正前後 sha256 相同（4 個檔，比對無差異），未 stage；`client2/`、`preprocessing/`、`testdata/`、主 checkout 都沒有動。worktree 裡 git-ignored 的 runtime 副本沒有 stage。
- 每個 commit 只 stage 明確路徑（`git diff --cached --stat` 確認），結尾 `Co-Authored-By: Claude Opus 5.5`。

| 發現 | 處理 |
| --- | --- |
| M-1 | `035f813`：`test_wx_call_sites.py` 拿掉只認 `wx.<name>(...)` 的 `is_wx_call`。C2、C3 改用既有的 `is_attribute`，任何 `.MessageBox`／`.MessageDialog` 屬性都算（不論有沒有呼叫、前面是 `wx` 還是別名）；C3 的預期清單不變（`gui.py:BrailleFrame._ask_after_close_save_failure`、`ui/message_box.py:message_box`）。新增 predicate `hides_wx_names` 與測試 `test_no_production_module_imports_wx_names_around_the_scans`：`import wx as <別名>`（別名不是 `wx`），以及 `from wx import` 的 `MessageBox`、`MessageDialog`、`FindWindowById` 或 `*` 都算命中；`import wx.html2`、`from wx.lib.scrolledpanel import ScrolledPanel` 不受影響。今天的 production 沒有命中。mutant 證據見下 |
| M-2 | `7f9b2be`：只改 `ui/message_box.py` 的 docstring，寫明 `style` 原樣送進 `wx.MessageDialog`，且不像 `wx.MessageBox` 在沒有 icon 時補 `wx.ICON_INFORMATION`（有 `wx.YES` 時補 `wx.ICON_QUESTION`），呼叫端要自己給 icon（21 個呼叫端都有）。行為不變（採審查建議 (a)，與 spec D2 一致）。以 AST 比對 `4ee62c6` 與 `HEAD` 的 `ui/message_box.py`：把 docstring 清空後完全相同 |
| M-3 | `1db2641`：plan 末尾新增「Implementation Notes (2026-10-10)」：Task 0–8 照 plan 以 `apply_blocks.py` 套用，Task 0–4、6、7 與 dry run 沒有偏離，列出 Task 1–4、6（及 Task 8 的 `4ee62c6`）的 `HEAD:client` tree id，exe 與 GUI 結果在 auto-results；並註明本次的審查修正（M-1、M-2、M-6、M-3 與 commit）、新的數量（`Ran 1368`、驗收 2 的模組組 `Ran 474`）、修正後的 tree，以及 N-f7 仍是要用的 build；plan 的區塊保留原文。F-5 spec 兩個檔的 D8 段落末尾加上「Corrected after the F-7 review, 2026-10-10」／「F-7 審查後的修正，2026-10-10」：wx 3.2.9（wxPython 4.2.5）在工作階段結束時完全不產生關閉事件（`WM_ENDSESSION` 直接 `OnExit()`／`exit()`），Windows 造成的關閉只有可 veto 的 query-end-session 關閉；不可 veto 的關閉只來自 DotExpress 從不呼叫的 `Close(force=True)`，所以 D8 的路徑只是防禦性的；指向 F-7 spec「現況」M-5。兩檔仍各 493 行、CRLF |
| M-4 | 未處理，follow-up（匯出 writer 改走 `write_text_atomically`／`write_bytes_atomically`，可與 HANDOFF §6 的 `save_preprocessing_script`、`config.json` 同一批） |
| M-5 | 不處理（審查建議；`_close_finished` 已擋住第二次關閉的 `Veto`／`Skip`，使用者沒有可見差異） |
| M-6 | `51e3a1a`：`production_sources` 改由 `_python_files` 取檔：`git -C <client> ls-files -z --cached --others --exclude-standard -- *.py`，也就是已追蹤的檔加上未追蹤但沒被忽略的檔。選這個而不是只用 `git ls-files`（只列已追蹤的檔）的理由：git-ignored 的 runtime 副本（`braille/louis_helper.py`）與被忽略的草稿不再被 parse，而還沒 `git add` 的新模組仍會被掃到，TDD 時不會漏。不在 git work tree 裡（`git archive` 副本、沒有 git）時退回掃描所有 `.py`，所以審查用的 scratchpad 副本照樣能跑。`ast.parse` 包一層，`SyntaxError`／`ValueError` 轉成 `AssertionError("cannot scan <檔名>: …")`。`production_sources`、`find_in_production` 多一個預設為 `CLIENT` 的 `root` 參數，供新測試使用。新測試 `ScanSourcesTest` 兩個：`test_a_file_that_does_not_parse_is_named`（暫存目錄的 `settings/draft.py`）、`test_git_ignored_files_are_not_scanned`（暫存 git repo：`added.py` 已 add、`new.py` 未追蹤、`ignored.py` 在 `.gitignore`；沒有 git 時 skip）。先紅：只加 `root` 參數時 `Ran 7`、`FAILED (failures=1, errors=1)`（`SyntaxError` 訊息是 `File "<unknown>"`，沒有檔名；`['added.py', 'ignored.py', 'new.py'] != ['added.py', 'new.py']`）；改後 `Ran 7`、`OK`。worktree 掃描的檔從 100 個變成 99 個（少了 `braille/louis_helper.py`） |
| M-7 | 未處理，仍待使用者（item 65，NVDA；步驟見 auto-results「仍需人工」） |
| O1、O5、O6 | 未處理，仍待使用者確認；目前維持預設（是／否框用系統標籤；非 `OSError` 的匯出錯誤寫 `gui.log`；關閉對話框開著時的 `WM_QUERYENDSESSION` 被否決、不記錄） |

### Mutant（M-1、M-6）

`git archive 4ee62c6 client` 解到 `$SP\f7fix\copy\client`（不是 git work tree，不含 `.venv`、`dictionary/`、`workspace/`、`config.json`、`log/`）；`$SP\f7fix\mutants2.py` 在 `settings/dialogs.py` 把 `from ui.message_box import message_box` 換掉（舊文字恰好一次、保留行尾），跑 `$PY -B -X utf8 -m unittest tests.test_wx_call_sites`，跑完還原並確認位元組相同：

```text
== 4ee62c6 的測試
unmutated: Ran 4 | OK
x23（from wx import MessageBox as message_box）: Ran 4 | OK  -- 存活
x24（import wx as _wx; message_box = _wx.MessageBox）: Ran 4 | OK  -- 存活
y1（另加 from wx import FindWindowById）: Ran 4 | OK  -- 存活
y2（另加 from wx import MessageDialog）: Ran 4 | OK  -- 存活
y3（另加 show = wx.MessageBox，不呼叫）: Ran 4 | OK  -- 存活
== 035f813 的測試
unmutated: Ran 5 | OK
x23: FAILED (failures=1)  test_no_production_module_imports_wx_names_around_the_scans
x24: FAILED (failures=2)  test_no_production_module_calls_wx_message_box、test_no_production_module_imports_wx_names_around_the_scans
y1、y2: FAILED (failures=1)  test_no_production_module_imports_wx_names_around_the_scans
y3: FAILED (failures=1)  test_no_production_module_calls_wx_message_box
```

`51e3a1a` 的測試在同一個非 git 副本（退回掃描所有檔）與另一個 `git init`＋`git add -A` 的副本（git 模式；另放一個被 `.git/info/exclude` 忽略、含 `wx.MessageBox(...)` 的 `ignored_draft.py`）各跑一次：兩者 unmutated 都是 `Ran 7`、`OK`（git 模式沒有報出被忽略的草稿），x23、x24、y1–y3 都以同樣的測試失敗。

### Build 與 GUI

沒有重建。修正中唯一的 production 改動是 `ui/message_box.py` 的 docstring（AST 去掉 docstring 後與 `4ee62c6` 相同），所以 `D:\dxtest\N-f7\DotExpress.exe`（sha256 `8fb58561…1819f`）仍是要用的 build；重建出來的 exe 只會在該模組 bytecode 的 docstring 常數上不同。GUI 53–64 不需重跑；auto-results 不需更新。

### 最終驗證

- 完整套件：`cd client && $PY -B -X utf8 -m unittest discover -s tests` → `Ran 1368 tests`，`FAILED (errors=1, skipped=7)`；唯一 error 為 F-W6 的 `test_dictionary_name_prompt … test_case_only_rename_still_renames`。1368 = 1365 + 3 個新測試（M-1 的 `test_no_production_module_imports_wx_names_around_the_scans`、M-6 的 `test_a_file_that_does_not_parse_is_named`、`test_git_ignored_files_are_not_scanned`）。跑完 worktree 沒有 `client/log/`。
- 驗收 2 的焦點模組組：`Ran 474`、`OK`（471 + 3）。
- catalog：`git diff --stat fb7aff9..HEAD -- client/locales` 為空；`.po` 與 `.mo` 的 sha256 與 `fb7aff9` 相同（`fa24753a…`、`4b865e4b…`）。
- fixtures：`translation_golden.json` → `e67d95a1…1ccd`，`dictionary_entries_trace.json` → `f493da52…c2cf`，與要求相同。
- 受限檔案：`git diff --name-only 4ee62c6..HEAD` 只有 `client/tests/test_wx_call_sites.py`、`client/ui/message_box.py`、F-7 plan、F-5 spec 兩檔（加上本記錄）；`client/braille/`、`AGENTS.md` 不在其中。改動的檔在 index 都是 `i/lf`；`git diff --check` 無問題。
- `HEAD:client` tree（`51e3a1a` 起）：`9157dccd4c26f990c877ff1e2fd83e01fa1cac72`。
