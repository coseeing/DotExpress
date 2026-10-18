# F-18 腳本管理 review 記錄

- 日期：2026-10-18。依協調者要求以繁體中文撰寫。
- 範圍：worktree `D:\workspace\DotExpress-f18`、分支 `fix/f18-script-management`、範圍 `67c2a97..f7034ca`（8 個 commit：spec `f691b25`、使用者決定 `cb07a37`、plan `0049399`、三個功能 commit `1a10232` `fa16143` `b84b3fe`、編輯器標籤修正 `2e5057f`、GUI 記錄 `f7034ca`）。production diff：`client/` 底下 17 個 `.py`（新增套件 `text_scripts/` 四個模組、`shared/file_targets.py`）加兩個目錄檔；測試 15 個檔案。
- 對照：spec（含使用者 2026-10-18 的決定 D-A～D-D、Q1～Q4）、plan 的 Spec Corrections 1–12 與 Implementation Notes 1–6、`auto-results.md`、HANDOFF 第 4、5 節、`AGENTS.md`。
- 方法：逐行讀完全部 production diff 與周邊程式；追每個流程（新增、編輯、刪除、重新命名、匯入、匯出、設定、轉換）；檢查目錄與編譯後的 `.mo`；在 scratch 複本上跑 19 個獨立突變；跑完整測試。只寫入這一份檔案，沒有改任何原始碼、沒有啟動 GUI、沒有碰剪貼簿。

## 驗證（Windows 11 26200；`$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`；`$SP` = scratchpad `f18review\`）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| 完整測試 | `cd D:\workspace\DotExpress-f18\client; $PY -B -X utf8 -m unittest discover -s tests`（可用記憶體 1372 MB） | `Ran 1788 tests in 18.8s`、`OK (skipped=6)`，與 plan 的 Expected Counts 相同 |
| 不產生使用者資料 | `Test-Path` | 測試前後 worktree 與主 checkout 都沒有 `client\script\`；`git status --short` 乾淨 |
| 編譯目錄 | `msgfmt --check --statistics -o $SP\fresh.mo locales\zh_TW\LC_MESSAGES\dotexpress.po`；`cmp` 已提交的 `.mo` | 438 translated、0 fuzzy、0 untranslated；`.mo` 位元組相同 |
| 模板重新產生 | 以 `generate-pot.bat` 相同的 `xgettext` 參數與排序輸出到 `$SP\fresh.pot`，與 `locales\dotexpress.pot` 比對 | 除 `POT-Creation-Date` 外完全相同；`.pot`／`.po` 的日期都是 `2026-10-10 12:00+0800` |
| 佔位符 | 讀取 `.mo` 的 catalog（438 筆）比對 msgid／msgstr 的 `{...}` 集合、換行數、結尾換行 | 全部一致；msgstr 等於 msgid 的只有 `ASCII`、`BRL`、`DEP`、`DOCX`、`DotExpress`、`EPUB`、`PDF`、`SimBraille`、`TXT`、`Unicode`（刻意保留） |
| fixture | `git show HEAD:<path> \| sha256sum` | 三個值與 HANDOFF 第 5 節相同：`e67d95a1…11ccd`、`f493da52…66cf2`、`8dc8572e…2a80e` |
| 不能改的檔案 | `git diff 67c2a97..HEAD --stat -- client/tests/fixtures client/braille scripts` | 沒有差異；`client/braille/tables/__init__.py` 仍含 CR 位元組 |
| 未追蹤檔案 | `git diff --name-only` 比對 `preprocessing/`、`testdata/`、`task.md`、`client/dictionary/` 等 | 都沒有被 stage；worktree 的 git-ignored runtime 沒有被 stage |
| commit 格式 | `git log --format=%b 67c2a97..HEAD` | 沒有 `Co-Authored-By` |
| 剪貼簿 | `grep -rniE "clipboard\|\^c\|\^v\|TheClipboard\|pyperclip" auto/` | 只有註解（「never the clipboard」）；程式碼用 `WM_SETTEXT`、`BM_CLICK`、UIA invoke |
| 突變（19 個） | `$PY -B -X utf8 $SP\mut.py`（複製 `client\` 到 `$SP\work\`，每次改一處再還原，跑相關模組） | 19 個全部被抓到，見第 2 節 |
| 沒有跑 | - | 打包、GUI 項目（plan agent 已跑 146–158 並記錄）、NVDA 項目 159–160（使用者的） |

## 結論

**可以 merge。沒有 Critical；一個 Important（鍵盤焦點，可一行修正，未實測）；七個 Minor。** 程式碼在我追過的每條路徑上都符合 spec 與使用者的決定；目錄完整精確；測試有力（19 個獨立突變全部被抓到，涵蓋狀態重讀、焦點、錯誤分類、大小寫、位元組複製、作用中腳本的跟隨與回退、設定存取）。

我確認過沒有問題的重點：

- **D-A／D4／D10：** `preprocess_source_text` 在 `script_path is None` 時完全不呼叫 `execute_script`；`gui._get_selected_script_path` 對 `no-processing`（不分大小寫）回傳 `None`；`ConversionRequest.script_path` 預設 `None`，所以 `main.py`、golden 與所有舊測試的輸出不變；`conversion/output.py` 不再從字典資料夾推導 `preprocessing.py`，grep 全 `client/` 沒有任何舊名稱殘留。
- **D-B／D5：** `_is_str_annotation` 只接受 `ast.Name("str")` 與常數 `"str"`；兩個註解檢查在參數數量檢查之後；沒有執行任何程式碼（`ast.parse` + `compile`）。
- **D-D／D4 保留名稱：** `normalize_script_name` 的保留集合是內部名稱、msgid `No Processing`、翻譯「不處理」，`normalize_base_name` 以 `casefold` 比對（突變 s 證明少了翻譯會被抓到）；`reserved` 訊息顯示使用者輸入的名稱（`NameDialogMessages.reserved_name=None`），字典的訊息不變。
- **檔案操作：** 新增、匯入、匯出、`ensure_no_processing_script` 都走 `shared.atomic_write`（失敗時目標不變、不留暫存檔）；匯入先檢查副檔名（casefold）→ 名稱 → 是否已存在 → 讀位元組（`PermissionError` 變 `ScriptImportSourceError`）→ 以 `utf-8-sig` 解碼並驗證 → 寫入**原始位元組**；匯出「不處理」永遠寫規格文字；`rename_script` 允許只改大小寫（`is_same_file`）；`delete_script`／`rename_script` 拒絕「不處理」。`shared/file_targets.py` 是從 `dictionaries/manager.py` 原樣搬出的，字典行為沒有變。
- **設定：** `config.get_selected_script` 非字串回傳預設；`save_translation_settings` 以 tuple 呼叫四個 setter 並回傳第一個問題；`load`／`normalize` 以 `resolve_selected_script` 回退到 `no-processing`；`_set_active_dictionary` 改用 `dataclasses.replace`，不再丟掉 `selected_script`（有測試）。
- **對話框：** 腳本管理是 modal、以 `with` 建立並銷毀，沒有 singleton；編輯器也是 modal、在腳本管理之上；`TextProcessingDialog` 與它的 singleton 槽已移除，`wx_stub` 的對話框名單更新；確認框走 `message_box`／`confirm_box`（是／否無快速鍵，F-17）；每個框的 parent 都是發起它的對話框；「不處理」的狀態永遠「可使用」且不讀檔。編輯器的「變更」比較的是控制項回讀的文字，所以 CRLF 檔案不會被誤判為已變更；套用成功後更新基準，失敗後仍會問。
- **執行緒：** 轉換要求在主執行緒建立（`_build_request`），worker 只讀取 `script_path`；腳本以 `exec` 在 worker 執行，和之前一樣。

## 1. 發現

### Critical

無。

### Important

**I-1. 刪除（以及重新命名、匯入）後焦點留在按鈕上；刪除第一個使用者腳本後，「刪除」按鈕因新選取「不處理」而被停用，焦點停在被停用的按鈕上。**
- 位置：`client/dialog.py:1172-1175`（`_on_delete_clicked`）、`:1177-1180`（`_on_rename_clicked`）、`:1182-1183`（`_on_import_clicked`）、`:1190-1195`（`_refresh_after`，只有 `focus_list=True` 時才 `list_ctrl.SetFocus()`）；`text_scripts/presenter.py:180-181`（刪除後選取上一列）。
- 情境：清單只有「不處理」與 `upper`，使用者以 Tab 到「刪除」、Enter、在「是／否」框按「是」。presenter 回傳 `no-processing`，`refresh_scripts` 選取第 0 列並呼叫 `_update_button_states`，把「刪除」、「重新命名」、「編輯」都停用，但焦點仍在「刪除」。Windows 不會把鍵盤輸入送給被停用的視窗，所以 Tab／方向鍵／Esc 都沒有反應，直到使用者用滑鼠點某處；NVDA 使用者會聽到「刪除 按鈕 無法使用」然後失去位置。因為刪除的鄰居只要是「不處理」就會發生，這是**刪除最後一個使用者腳本的常態**，不是邊角；字典管理有相同的程式模式，但在那裡只有刪除排在 `default` 正下方的字典才會遇到。
- 未實測：GUI 項目 154 只記錄清單與 `config.json`，沒有記錄刪除後的焦點；我沒有啟動 GUI。wx 本身可能會在停用有焦點的按鈕時把焦點移走——如果實測是這樣，這一項降為 Minor。
- 建議：`_on_delete_clicked` 改為 `self._refresh_after(self._actions.delete(self, selected), focus_list=True)`（和新增、編輯一致：操作結束回到清單，焦點所在列就是新選取的腳本，NVDA 會讀出）。重新命名與匯入也可以一併加上，讓六個按鈕行為一致。一行修改；`test_script_dialogs.ScriptHandlersTest` 加一個刪除後焦點的斷言即可。若要維持現狀，至少請使用者在 NVDA 手動項目 159 時試一次「刪除 `upper`」。

### Minor

**M-1. 設定對話框開著時在腳本管理重新命名／刪除作用中的腳本，之後在設定按「確定」會把作用中腳本悄悄改回「不處理」。**
- 位置：`client/settings/dialogs.py:356-360`（`_selected_script` 回傳開啟時快照的內部名稱）、`client/gui.py:470-476`（`apply_settings_from_dialog` 以新的名單正規化）、`:1104-1110`（`on_open_settings`）。
- 情境：設定（modeless）開著，使用者從選單開腳本管理，把作用中的 `upper` 改名為 `Upper2`（`_set_active_script("Upper2")` 已存檔）。關閉腳本管理後設定仍顯示舊名單與 `upper`；使用者只是改寬度然後按「確定」，`upper` 不在名單中，`resolve_selected_script` 回退成 `no-processing`，腳本停止執行，沒有任何提示。spec「Risks」已說明這是字典既有的模式（字典會回到 `default`），使用者接受；但重新命名是 F-18 新增的常見路徑，而且 `show_singleton` 對已開啟的設定也不會更新名單。
- 建議：`on_open_script_management` 結束後，若 `DotExpressSettingsDialog.open_instance()` 不是 `None`，用 `sync_font_size` 的方式把新的 `script_names`／`dictionary_names` 與作用中名稱同步到面板；或在設定開著時先關閉它再開腳本管理。不是這次必須做的。

**M-2. 匯入非 `.py` 檔案時，要先輸入名稱並按「確定」之後才被拒絕。**
- 位置：`client/text_scripts/presenter.py:200-224`（`import_from_file` 先 `choose_import_path`，副檔名檢查在 `import_script` 的 submit 裡，`manager.py:103`）。
- 情境：使用者在檔案對話框輸入 `notes.txt`，出現「新增腳本」名稱框（預設 `notes`），按「確定」才看到「匯入腳本失敗：只能匯入 Python 檔案（.py）。」。多一個沒有意義的步驟。spec D8.5 寫的是「On submit」，所以符合 spec；列為使用者未確認的預設。
- 建議：在 `choose_import_path` 之後、提示名稱之前先檢查 `source_path.suffix.casefold() != SCRIPT_SUFFIX` 並顯示同一個訊息（不新增字串）；`import_script` 內的檢查保留作為最後防線。

**M-3. 「編輯」無法讀取的腳本時，同一個錯誤記兩行 log。**
- 位置：`client/text_scripts/presenter.py:153-158`（`edit` 讀失敗時 `log_script_read_error` 後回傳 `name`）、`client/dialog.py:1166-1170`（`_on_edit_clicked` 一律 `_refresh_after(..., focus_list=True)`）、`text_scripts/read_problems.py:35-39`（`read_script_status` 每次重新整理再記一次）。
- 情境：GUI 項目 156 的 `locked.py`：按一次「編輯」，`gui.log` 多兩行相同的 `Cannot read script "locked.py": PermissionError: …`。只影響 log 的可讀性。
- 建議：`edit` 讀失敗時不記 log（重新整理會記），或讀失敗時回傳 `None` 並由對話框自己 `list_ctrl.SetFocus()`。

**M-4. 在編輯器儲存會把 CRLF 換成 LF。**
- 位置：`client/dialog.py:1290`、`:1298-1300`（寫入 `editor.GetValue()`）、`conversion/preprocessing/user_script.py:83`（`newline=""`，照寫）。
- 情境：匯入一個 CRLF 的 `.py`（項目 152 的 `upper2.py`），之後在編輯器按「套用」，檔案變成 LF（wxMSW 回讀時已是 LF）。舊的「文字處理」對話框行為相同；Python 不在意。只是使用者未確認的預設，列出而已。
- 建議：不改。若要保留，`save` 時可用開啟時偵測到的換行重新 join；不值得。

**M-5. `list_script_names` 以「`others` 比 `stems` 少」間接判斷 `no-processing.py` 是否存在；若那個名稱是資料夾，「不處理」會從清單與設定中消失。**
- 位置：`client/text_scripts/manager.py:63-68`。
- 情境：`script\no-processing.py` 是一個資料夾（使用者誤建）。`ensure_no_processing_script` 看到 `exists()` 為真不重建；`glob` 的 `is_file()` 濾掉它；名單沒有 `no-processing`。設定的下拉第 0 項變成使用者腳本，`_select_script` 找不到儲存的名稱時選第 0 項，按「確定」就存成那個腳本。非常罕見。
- 建議：改成明確的 `path.is_file()` 判斷並永遠把 `NO_PROCESSING_SCRIPT_NAME` 放在第一位（`[NO_PROCESSING_SCRIPT_NAME] + others`），因為它是固定項目而不是檔案的存在與否；`ensure` 遇到資料夾時可以記 log。小改。

**M-6. 在程式外先刪掉檔案再按「刪除」，顯示「無法刪除腳本：[Errno 2] …」而不是直接更新清單。**
- 位置：`client/text_scripts/manager.py:146-150`（`unlink()`）、`presenter.py:172-176`。
- 情境：和字典一樣的既有模式；使用者再按一次「刪除」或關閉重開即可。也不會把作用中的腳本改回「不處理」（`active_name == name` 的判斷在 `unlink` 成功之後），下一次轉換會得到「文字處理失敗」。
- 建議：`delete_script` 用 `unlink(missing_ok=True)`，或 presenter 把 `FileNotFoundError` 當成功處理。可選。

**M-7. 文件殘留：spec 的 Windows 項目編號（150–162／163–164）與實際記錄（146–158／159–160）不同；spec 說「Obsolete `#~` entries are not kept」，實作保留了 28 筆（plan Spec Corrections 9、12 已說明）；`config.get_selected_script` 的預設值是字面值 `"no-processing"` 而不是 `NO_PROCESSING_SCRIPT_NAME`。**
- 位置：`docs/superpowers/specs/2026-10-18-f18-script-management-design.md:377`、`:509-530`；`client/config.py:307`。
- 情境：之後的 agent 讀 spec 找項目 153 會對不上 `auto-results.md` 的 149。`config.py` 的字面值和常數分開維護，改名時容易漏。
- 建議：spec 補一行「編號依 plan Spec Corrections 12 改為 146–160」；`config.py` 不必改（`config` 不 import `conversion` 是刻意的分層，plan 沒有說明但可以接受）。

## 2. 突變（scratch 複本 `$SP\work\client`，每個一處修改，跑完還原；全部被抓到）

| # | 修改 | 跑的模組 | 結果 |
| --- | --- | --- | --- |
| a | `refresh_scripts` 只在第一次讀狀態（編輯後狀態不更新） | `test_script_dialogs` | 抓到（1 failure） |
| b | `_refresh_after` 忽略 `focus_list` | `test_script_dialogs` | 抓到（2） |
| c | `presenter.edit` 只接 `OSError`（非 UTF-8 檔案會炸） | `test_text_scripts_presenter` | 抓到（1 error） |
| d | 匯入失敗訊息用 `str(error)` 而不是 `describe_script_problem` | `test_text_scripts_presenter` | 抓到（5） |
| e | 格式不正確的腳本也記 log | `test_text_scripts_manager` | 抓到（3） |
| f | `list_script_names` 不濾 `is_file()` | `test_text_scripts_manager` | 抓到（1） |
| g | 任何字串常數都當成 `"str"` 註解 | `test_user_preprocessing_script` | 抓到（1） |
| j | 「確定」在儲存失敗時也關閉 | `test_script_dialogs` | 抓到（4） |
| k | 腳本管理也讀「不處理」的檔案來決定狀態 | `test_script_dialogs` | 抓到（3） |
| l | 設定找不到儲存的名稱時選 `NOT_FOUND` 而不是第 0 項 | `test_settings_dialogs` | 抓到（1） |
| m | 刪除後一律選「不處理」而不是上一列 | `test_text_scripts_presenter` | 抓到（2） |
| n | 副檔名檢查改為區分大小寫（`.PY` 被拒） | `test_text_scripts_manager` | 抓到（1 error） |
| p | `_set_active_script` 不回報設定儲存問題 | `test_gui_document_flows` | 抓到（1） |
| q | 套用成功後不更新 `_saved_text` | `test_script_dialogs` | 抓到（1 error） |
| r | `on_open_script_management` 不先 `refresh` | `test_gui_document_flows` | 抓到（1） |
| s | 保留名稱少了翻譯「不處理」 | `test_text_scripts_manager`、`test_script_dialogs` | 抓到（2） |
| t | 匯入寫入解碼後再編碼的文字而不是原始位元組（BOM 消失） | `test_text_scripts_manager` | 抓到（1） |
| u | 重新命名作用中腳本後不跟隨新名稱 | `test_text_scripts_presenter` | 抓到（2） |
| v | 「不處理」也送出檔案路徑（會執行 `no-processing.py`） | `test_gui_document_flows` | 抓到（2 failures、30 errors） |

這 19 個和 plan 自己跑的 20 個（spec 的 14 個加 6 個）大多不重疊。沒有存活者，所以沒有必須補的測試；I-1 的焦點是唯一我認為該加斷言的地方（目前的測試只斷言新增與編輯會回到清單）。

## 3. zh_TW 用詞

33 個新字串全部有翻譯、沒有 fuzzy、和既有用詞一致：腳本（對應字典）、「新增腳本／重新命名腳本／匯入腳本／匯出腳本」對應「新增字典」等、「腳本「{name}」已存在。」對應「文件「{name}」已存在。」、「無法刪除腳本：{error}」對應「無法刪除字典：{error}」、「儲存腳本失敗／匯入腳本失敗／匯出腳本失敗」對應字典的三句、「無法讀取腳本「{name}」。」對應「無法讀取字典「{name}」。」、「要刪除腳本「{name}」嗎？／確認刪除腳本」對應文件與字典、「要放棄對腳本「{name}」所做的變更嗎？」對應字典編輯器、「Python 檔案 (*.py)」對應「CSV 檔案 (*.csv)」、狀態「可使用／無法讀取／格式不正確」與「無法使用的原因：」對應「無法讀取的原因：」、「文字處理腳本」與面板說明「轉譯輸出模式、寬度、字典與文字處理腳本選項」、「main 的參數只能標註為 str，或不加標註。」與既有的「main 必須恰好定義一個位置參數…」同一語氣。唯一的小地方：「只能匯入 Python 檔案（.py）。」用全形括號，目錄裡其他句子的半形括號都是引用外部程式的字串（例如 Excel 的「CSV UTF-8 (逗號分隔)」），所以全形是對的。重新命名失敗用「儲存腳本失敗」（spec D8.4 的選擇，和字典相同）。

## 4. 使用者還沒確認的使用者可見預設

spec 已標為「Decided by orchestrator with the recommended default」：D-E（新增＝名稱框再編輯器、按確定／套用前不寫檔、放棄變更的確認）、D-F（匯入＝`.py` 篩選＋副檔名檢查＋驗證＋原始位元組；同名時再問一次，不覆寫；匯出照位元組，「不處理」匯出規格文字）、D-G（無法讀取或格式不正確的腳本不擋對話框，用狀態欄＋原因欄）、D-H（匯入不加安全警告）、O1（「不處理」永遠排第一）、O2（只有 `str`／`"str"` 算 str）、O3（選單項目沒有快速鍵）、O4（編輯在腳本管理之上開啟並回到清單，和字典不同）、O5（刪除作用中腳本改為「不處理」；使用者 Q4 已確認）、O6（「可使用／無法讀取／格式不正確」、「文字處理腳本」）、O7（接受 BOM）、O8（選取的腳本不見時轉換失敗而不是當成不處理）、O9（編輯器名稱「Python 程式碼」）。

plan 與實作另外決定的（plan Spec Corrections 5–9、Implementation Notes 4、6）：

1. 「不處理」的狀態永遠「可使用」，不讀它的檔案（檔案被改過也一樣）。
2. 新增時若檔案已被別的程式建立，第一次儲存在編輯器的錯誤框顯示「儲存腳本失敗：腳本「x」已存在。」；是「儲存當下檔案存在」的檢查，不是排他建立。
3. 刪除後清單選取上一列；第一個使用者腳本的上一列是「不處理」。
4. 編輯器按鈕來自標準 sizer（確定、取消、套用，右對齊）。
5. 目錄保留 28 筆 `#~` 舊字串（spec 說不保留）。
6. 編輯器上方有可見的標籤「Python 程式碼」（為了 NVDA 讀到名稱，`2e5057f`）。

我在 review 時額外看到的：

7. 匯入非 `.py` 檔案時先問名稱再拒絕（M-2）。
8. 匯入一個叫 `no-processing.py` 的檔案（例如之前匯出的）時，名稱框預填保留名稱 `no-processing`，按確定會得到「腳本名稱「no-processing」為保留名稱。」，使用者要自己改名。
9. 在編輯器儲存會把 CRLF 變成 LF（M-4，舊對話框相同）。
10. `config.json` 裡不存在的 `selected_script` 要到下一次儲存設定才被改寫（GUI 157）；期間轉換顯示「文字處理失敗：[Errno 2] …」，錯誤文字是作業系統的英文。
11. 編輯無法讀取的腳本時，錯誤框關閉後焦點回到清單。
12. 腳本管理開啟時每個使用者腳本都會被讀取並編譯一次（不執行）；無法讀取的每次重新整理都記一行 log。
13. 設定對話框開著時在腳本管理改名或刪除作用中腳本，之後設定按確定會回到「不處理」（M-1，spec Risks 已寫）。
