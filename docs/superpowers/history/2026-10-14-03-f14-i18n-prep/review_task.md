# F-14 i18n 準備 review 紀錄

- 日期：2026-10-14。依 orchestrator 的要求以繁體中文撰寫。
- 範圍：worktree `D:\workspace\DotExpress-f14`、branch `fix/f14-i18n-prep`、範圍 `a147fed..HEAD`（HEAD `10b277d`；7 個 commit：spec `1c4abb0`、plan `f8ee22c`、四個實作 commit `41d87e7` `e5f8e9f` `381bb80` `a8c9369`、GUI 紀錄 `10b277d`）。程式碼 diff：`client/` 下 9 個非測試檔（`i18n.py`、`about.py`、`dictionaries/entries.py`、`dictionaries/entry_list_model.py`、`dialog.py`、`settings/dialogs.py`、`dual_view/html.py`、`documents/formats.py`、`gui.py`）、兩個 catalog 加 `.mo`、10 個測試檔。
- 對照：spec（含「Corrected after planning」1–11）與 `_zh-TW.md`、plan（Spec Corrections、Implementation Notes 1–6）、`auto-results.md`、`auto/` 的 8 個腳本、HANDOFF（2026-10-14-01）第 1–5 節、`task.md` 第五節「下一輪要修」第 7、4、8 項、F-13 branch（`fix/f13-behavior-nvda`，`68c6bf4`）。
- 方法：逐行讀完 production diff 與周圍程式碼；自己 grep 全部 `client/` 找 `_`/`gettext`/`ngettext`/`pgettext`/`GetTranslation` 的別名與載入時呼叫；追 `title`/`panel_description`/`base_title`/`title_template`、`ENTRY_TYPE_LABELS`/`ENTRY_TYPE_OPTIONS`、`about.*`、`render_dual_view_html` 的每個讀取端；重新產生 `.pot` 與 `.mo`、重跑 `msgmerge` 比對；focused 測試模組與 20 個 mutant 在 scratch 副本上執行；F-13 的 diff 與 `git merge-tree`。
- 本紀錄只寫到磁碟，不 commit。沒有改任何其他 repo 檔案；沒有跑 GUI、沒有 build、沒有跑完整測試（記憶體規則）；沒有碰剪貼簿、使用者資料或 `task.md`。

## 驗證（Windows 11 26200，`$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`，`$SP` = session scratchpad 的 `f14review\`）

| 項目 | 指令 | 結果 |
| --- | --- | --- |
| focused 模組（基準） | `$PY -B -X utf8 -m unittest tests.test_i18n tests.test_dual_view_html tests.test_document_formats tests.test_settings_dialogs tests.test_settings_options tests.test_dialog_validation tests.test_dictionary_entry_list_model tests.test_config tests.test_translation_golden tests.test_gui_document_flows tests.test_dictionary_entries_dialog`，在 `$SP\work\client`（worktree `client\` 的副本，不含 `.venv`、`log`、`workspace`、`config.json`），可用記憶體 ≥ 600 MB 後才執行（實際 691 MB） | `Ran 654`、`FAILED (errors=1)`：唯一的 error 是 `test_generate_pot_extracts_n_keyword`，它讀 `../scripts/generate-pot.bat`，而我的副本一開始沒有 `scripts/`；補上 `scripts/` 後 M3、M4 的 `tests.test_i18n` 整個模組（47 個）只剩 mutant 造成的失敗，所以 branch 本身的 focused 模組全綠（653 個通過 + 1 個是副本的環境問題） |
| mutant（計畫 20 個，跑了 5 個） | `$PY $SP\mut.py $SP\work\client`（每個 mutant 一處文字修改，保留 CRLF，跑完還原；每次執行前等可用記憶體 ≥ 600 MB） | M1–M5 全部 CAUGHT。M6 等記憶體時整個工作被 Claude Code 以「系統記憶體不足」停掉（另一個 agent 同時在 build／跑 GUI）；依 HANDOFF 第 3 節第 4 點沒有自行重啟。M6–M20 **沒跑**，見第 2 節；副本裡留下的 M6 修改已還原 |
| 完整測試 | 未跑（記憶體規則；另一個 agent 同時在 build 與跑 GUI）。plan Implementation Notes 1 報 `Ran 1652`、`OK (skipped=6)` | — |
| catalog 編譯 | `msgfmt --check --statistics -o $SP/fresh.mo client/locales/zh_TW/LC_MESSAGES/dotexpress.po`；`cmp` 與 commit 的 `.mo` | 408 translated、0 fuzzy、0 untranslated；與 commit 的 `.mo` 位元組相同 |
| catalog 內容 | `grep` `.po`、`.pot` | `msgid` 行 409（含標頭）= 408 個 msgid；`#~` 26 個；`fuzzy` 0；`#\|`（previous-msgid）0 行；`POT-Creation-Date` 兩個檔都是 `2026-10-10 12:00+0800`；N1、N2 都帶 `#, python-brace-format`，msgstr 與 spec 表、使用者 Q1 決定（N1 長版）逐字相同 |
| `#:` 參照 | `scripts\generate-pot.bat $SP\fresh.pot`，與 commit 的 `.pot` 比對（略過 `POT-Creation-Date`） | 完全相同：沒有過期參照 |
| msgid 集合 | `msgattrib --no-wrap` 後 `sort` 比對 `a147fed` 與 HEAD 的 `.pot` | 差異恰好是 F-12 字串 22 消失、N1 與 N2 加入 |
| msgmerge 重跑 | `msgmerge -o $SP/merged.po <po> <pot>`，`diff --strip-trailing-cr` | **不是**「changes nothing」：N1、N2 的 msgstr 會被重新換行（見 M-3）；其他完全相同 |
| 載入時翻譯掃描 | `grep` 全 `client/`（排除 `tests/`、`.venv`、`braille/liblouis`）找 `GetTranslation`、`ngettext`、`pgettext`、`_translation`、`gettext.`；`tests.test_i18n` 的 AST guard 與 subprocess probe | 除了 `braille/tables/__tables.py`（自己的 `_`，HANDOFF 規定不能改）沒有其他別名；`conversion/` 等轉換熱路徑只有 `conversion/preprocessing/user_script.py` 在錯誤時呼叫 `_`，不在逐字元路徑上 |
| fixture | `git show HEAD:<path> \| sha256sum` | `translation_golden.json` `e67d95a1…`、`dictionary_entries_trace.json` `f493da52…`、`translation_liblouis_golden.json` `8dc8572e…`，三個都沒變 |
| 禁改檔案 | `git diff --stat a147fed..HEAD -- client/braille/ task.md client2 preprocessing testdata` | 無輸出；`client/braille/tables/__init__.py` 未動（371 個 CR 仍在） |
| worktree | `git status --short` | 乾淨 |
| F-13 | `git -C D:\workspace\DotExpress-f13 log a147fed..HEAD`（8 個 commit）、`git merge-tree --write-tree HEAD fix/f13-behavior-nvda`、F-13 的 `client/` diff | 只有兩個 catalog 衝突（`.pot`、`.po`，照 spec 重新產生）；`gui.py`、`dialog.py`、`test_gui_document_flows.py` 自動合併。F-13 沒有新增 msgid（`.po` 408 行 = 407 個 msgid）、沒有載入時 `_()`（新增的兩處 `_()` 都在函式內）、沒有新的 HTML 產生端、沒有碰 F-14 改的函式（`_report_settings_save_problem`、`on_about`、`_render_dual_view_for_open_document`、`AddSymbolDialog.__init__` 的類型選單、`_format_title` 等），所以沒有語意衝突。merge 後 catalog 應為 408 個 msgid |
| GUI 腳本的限制 | 讀 `auto/run_item.sh`、`safe_run.py`、`f14gui.py`、`item141–144.py`、`manual145.py`；`grep` 剪貼簿與 `^c`/`^v`/`^x` | 沒有剪貼簿操作；按鍵只在前景是 `D:\dxtest\auto…-f14` 底下的程序時送出；log 的焦點在非受測程式時記為 `<another program>`；結束的程序只限 `ExecutablePath` 在該資料夾下或命令列含該項目名稱的 `lockshare.py`；`_MEI*` 清理只刪該項目啟動後建立、含 `mathcat`、沒有被任何 DotExpress 程序使用的資料夾 |
| 瀏覽器替身 | 讀 `dual_view/browser.py` 與 `f14gui.fake_browser` | `find_browser_executable("chrome")` 先用 `shutil.which("chrome.exe")`（PATH 順序），再找安裝路徑；替身資料夾放 PATH 最前面，受測程式由 `subprocess.Popen` 啟動、繼承這個 PATH，工作資料夾裡沒有 `chrome.exe`，所以替身一定先被找到；`where.exe` 收到瀏覽器參數會印錯誤後結束，`Popen` 不會丟 `OSError`，因此不會再往 Edge／Firefox／`os.startfile` 走。做法成立；但 `item144.py` 保留的 `window` 模式仍會開真的瀏覽器（M-1） |
| 未做 | — | GUI 項目 145（NVDA，使用者）；沒有重跑 141–144；沒有 build |

## 結論

**可以 merge。沒有 Critical，沒有 Important。** 三個項目都照 spec 與使用者決定做到；zh_TW 下使用者看到的文字、標題、無障礙描述與對話框都和改前相同（GUI 143 逐項讀回），只有 HTML 的 `lang` 與備份失敗的說明如預期改變。Catalog 精確（408 個 msgid、0 fuzzy、沒有過期參照、`.mo` 可重現）。focused 模組全綠；mutant 跑到的 5 個（D1 的五個）全部被抓到，其餘 15 個因記憶體被系統停掉而沒跑，但它們對應的測試我逐一讀過（第 2 節列出每個 mutant 會被哪個測試抓到的理由），加上 plan 自己的 20 個 mutant 紀錄（Implementation Notes 2，replay `r4` 全部抓到），我認為測試強度足夠。四個 Minor，都便宜，沒有一個擋 merge。

我查過、認為正確的部分：

- **D1（`i18n`）：** `_` 變成模組函式，每次呼叫讀 `_translation`；`set_language` 用 `load_translation(localedir, (language,))`，找不到 catalog（`NullTranslations`）時記 `SOURCE_LANGUAGE`，找到（`GNUTranslations`）才記 `language`；模組底部 `set_language(LOCALE_LANGUAGES[0])` 給的就是今天的 zh_TW catalog。`_("")` 回 `""`（`gettext("")` 會回標頭，測試有驗）。`html_language_tag` 只把 `_` 換成 `-`，對 `ll`／`ll_CC` 正確。`config.py` 的 `get_lang`／`set_lang`（點字語言）完全沒動，`current_language()` 不讀 `config.json`。
- **D2（About）：** `longName`、`description` 改 `N_`；`copyright_text()`、`about_message()` 顯示時翻譯並 format；`gui.on_about` 改呼叫 `about.about_message()`；`client_init.py` 只用 `about.version`；全 repo 沒有其他讀 `aboutMessage`／`copyright` 的地方。`version`／`version_detailed` 行未動，與 `main` `2053646`（1.8）合併無衝突（`merge-tree` 驗過）。
- **D3（類型名稱）：** `ENTRY_TYPE_OPTIONS`／`ENTRY_TYPE_LABELS` 的 key 不變，`normalize_entry_type`、`dialog.py` 的 `get_entry_type`／`_select_entry_type` 只用 key 與索引；字典檔讀寫（`entries.py:173-186`、`:232`）寫的是 `row.entry_type`（key），所以 CSV 裡的 `General`／`Bopomofo`／`Braille` 前後完全一樣，不會變成翻譯過的字。顯示端只有兩處：`AddSymbolDialog` 的 `wx.Choice`（`entry_type_choices()`）與 `cell_text(row, 2)`（`entry_type_label`，未知 key 原樣回傳，和改前的 `.get(k, k)` 一致）。
- **D4（設定）：** 13 個屬性全是 `N_`（AST 測試驗）；讀取端 `SettingsPanel.__init__`（label、name）、`GetDescription`、`_build_layout` 的分類清單、`__init__` 的初始標題、`_format_title`、`_after_category_change`、`_collect` 的框標題都翻譯；基底類別的 `""` 經 `_("")` 規則仍是 `""`。`_load_table_options` 未動。
- **D5（guard）：** AST 掃描把模組層、class body、預設引數、decorator、lambda 預設都算載入時，函式與 lambda 本體不算；屬性呼叫（`x.gettext`）也算；對 snippet 的測試覆蓋每一種。期望值是「恰好 `braille/tables/__tables.py`」而不是 allow-list，所以把掃描範圍縮小也會被抓到。subprocess probe 在匯入任何 consumer 之前換掉 `i18n._`，能抓 AST 看不到的間接呼叫；`log.get_logger` 的 `FileHandler` 是 `delay=True`，probe 不會在 `client/log/` 建檔。
- **D6（HTML）：** `render_dual_view_html` 的 `lang` 是必填 keyword、`html.escape` 過；三個產生端（`gui._render_dual_view_for_open_document`：瀏覽器副本與空白頁；`formats._write_html`：單檔匯出、全部匯出、空白頁）都傳 `html_language_tag()`，每次 render 讀取。golden 測試明確傳 `lang="en"`，fixture 位元組與 sha256 未變。`dual_view/html.py` 仍不 import `i18n`。
- **D7（備份訊息）：** `BACKUP_FAILED` 分支用 F-12 的 `is_access_error`（`PermissionError`，或 `OSError` 的 winerror 5/32/33、errno `EACCES`/`EPERM`）選 N1，否則 N2；兩者只 format `{backup}`，沒有 `{error}`。`config.py` 未動：`_backup_unreadable` 仍只寫不讀、備份失敗就 return 不寫 `config.json`、`_log_current_exception(..., exc_info=True)` 把原文與暫存檔名留在 `config.log`（`test_config` 驗 `exc_info[1] is problem.error`；GUI 142 讀到 traceback 含 `WinError 5`）。`UNREADABLE`、`WRITE_FAILED` 分支、一次性旗標、框的 owner 都沒動。讀 `config.json` 失敗（被鎖）也是 access error，N1 的「檔案或備份檔」措辭涵蓋。
- **D8（catalog）：** 字串 22 是「消失」而不是 `#~`（因為 msgmerge 拿它當 N2 的 fuzzy 基底），spec 修正 3 有記；`.po` 裡沒有殘留 fuzzy 或 `#|` 行。
- **測試：** 每個切換語言的測試都 `addCleanup(i18n.set_language, i18n.current_language())`；`dictionary_entries_trace.json`（387 個 `一般`）所在的 `test_dictionary_entries_dialog` 在我的 focused 執行裡與切換語言的模組同批跑，結果見上表。red-first 可信：A（`current_language` 等函式不存在）、B（匯入時固定的文字）、C（15 個載入時呼叫）、D（`lang="en"`）、E（`詳細資訊：`）在 `a147fed` 上都必定失敗。
- **無障礙：** 面板的 accessible name／description 字串相同，只是改在讀取時翻譯（GUI 143 (b) 用 `LegacyIAccessible.Description` 讀回三個描述）；備份框不再唸出隨機暫存檔名。

## 1. 發現

### Critical

無。

### Important

無。

### Minor

**M-1. `item144.py` 的 `window` 模式仍會啟動使用者的真實瀏覽器。**
- 位置：`docs/superpowers/history/2026-10-14-03-f14-i18n-prep/auto/item144.py:29-31`（`if not window: ... fake_browser(d)`）、`:38`（`read = H.dual_view if window else H.dual_view_page`）；`auto/f14gui.py` 的 `dual_view_window`、`dual_view`。
- 情境：之後有人照 docstring 用 `run_item.sh 144 item144.py new window` 重跑（例如 F-13 merge 後回歸），替身瀏覽器不會安裝，DotExpress 會像第一次執行一樣開兩個真的瀏覽器視窗。auto-results 的「偏離 1」已說明第一次的情況，但腳本本身沒有關掉這條路。
- 建議：`fake_browser(d)` 無條件執行（`window` 模式只改讀法），或直接刪掉 `window` 參數與 `dual_view`／`dual_view_window`。便宜。

**M-2. spec 兩個語言版本仍把 H1 描述成程式內的 `DualViewFrame`，GUI 144 (a) 的步驟也照這個寫；「Corrected after planning」沒有補上。**
- 位置：`docs/superpowers/specs/2026-10-14-f14-i18n-prep-design.md:120`（H1 表列）、`:209`（前後對照表「Dual View window」）、`:365`（144 (a)「read the web view's text through UIA」）；`_zh-TW.md:120`、`:209`、`:365` 同。
- 事實：`gui.py` 的 `_show_dual_view`／`_create_dual_view_frame`（`:322-349`）在 `a147fed` 就沒有任何呼叫者（grep 全 `client/`，只有 `tests/test_gui_document_flows.py:131-158` 兩個單元測試直接呼叫）；選單「轉譯 > 雙視檢視」走 `on_open_dual_view` -> `_open_dual_view_in_browser`（H2）。plan Implementation Notes 5(a) 與 `auto-results.md` 偏離 1 寫對了，spec 沒改。`_render_dual_view_for_open_document` 是兩條路共用的，所以 D6 的實作不受影響；只是文件錯。
- 建議：兩個 spec 檔的「Corrected after planning」補第 12 點（H1 無路徑可達、144 (a) 改讀 `dual_view\` 的頁面檔），H1 列註明 dead code。把 `_show_dual_view`、`DualViewFrame` 的移除列為後續項目（不在 F-14）。便宜。

**M-3. 文件裡幾個與事實不符的小地方：「a second msgmerge changes nothing」不成立；Acceptance Criteria 4 與 D7／D8 仍寫字串 22 變 `#~`、obsolete 27。**
- 位置：spec `:38`（修正 3）、plan Spec Corrections 3；spec `:194`（D7「msgmerge moves it to the obsolete entries」）、`:200`（D8「Obsolete entries 26 -> 27」）、`:347`（criterion 4「obsolete entries 27」）；`_zh-TW.md` 對應行。
- 事實：用 HEAD 的 `.pot` 對 HEAD 的 `.po` 重跑 `msgmerge`，N1、N2 的 msgstr 會被折成三行（其他不變、`.mo` 相同）。F-13 merge 後照 spec「Relation to F-13」重新產生 catalog 時，這兩條會以折行形式出現，看起來像「有變」，但只是換行。obsolete 實際是 26、字串 22 消失，修正 3 說對了，但 D7／D8／criterion 4 沒同步。
- 建議：把修正 3 的那句改成「msgmerge 會重新折行，內容不變」，或現在就把兩條 msgstr 寫成 msgmerge 的折行形式讓 catalog 對 msgmerge 穩定；D7、D8、criterion 4 加一句「見修正 3」。便宜。

**M-4. `set_language` 分兩步改 `_translation` 與 `_language`，沒有鎖。**
- 位置：`client/i18n.py:62-64`。
- 情境：F-14 只有測試呼叫，所以今天沒有問題。將來的切換功能若在主執行緒呼叫 `set_language`，而轉換工作執行緒（`ui/conversion_presenter.py` 的 worker）同時呼叫 `_()` 或匯出呼叫 `html_language_tag()`，可能在兩步之間讀到新 catalog 配舊語言標籤（或反過來），匯出的 HTML `lang` 與內文語言不一致一次。
- 建議：把兩個值放進一個 tuple／小物件，一次指派（CPython 的單一屬性指派是原子的）；或在切換任務處理。不必在 F-14 做。

## 2. Mutant（scratch 副本 `$SP\work\client`，每個一處修改，跑完還原；「模組」是實際執行的測試模組）

跑了 M1–M5；M6 起在等記憶體時工作被系統停掉（見驗證表），沒有重啟。M6–M20 的「預期抓到的測試」是我讀測試後的判斷，不是執行結果。

| # | 修改 | 模組 | 結果 |
| --- | --- | --- | --- |
| M1 | `set_language` 不更新 `_translation`（consumer 停在匯入時的 catalog） | `test_i18n` | 抓到（6 個 failure） |
| M2 | `set_language` 不記語言（永遠 `en`） | `test_i18n` | 抓到（5 個 failure） |
| M3 | 找不到 catalog 仍記 `zh_TW` | `test_i18n` | 抓到（`test_a_missing_catalog_reports_the_source_language`） |
| M4 | `html_language_tag` 不把 `_` 換成 `-` | `test_i18n` | 抓到（2 個） |
| M5 | `_("")` 回標頭 | `test_i18n`、`test_settings_dialogs` | 抓到（兩個模組各 1 個） |
| M6 | `entry_type_label` 回 msgid | `test_i18n`、`test_dictionary_entry_list_model` | 未跑；預期 `test_entry_type_labels_are_translated_when_shown`（zh_TW 子測試）、`test_the_type_label_follows_the_interface_language` |
| M7 | `cell_text` 直接查字面 dict | `test_dictionary_entry_list_model`、`test_dictionary_entries_dialog` | 未跑；預期 `test_the_type_label_follows_the_interface_language`，以及 trace fixture 的 387 個 `一般` |
| M8 | `AddSymbolDialog` 的選項用 msgid | `test_dialog_validation` | 未跑；預期 `test_the_type_choice_follows_the_interface_language` |
| M9 | `GetDescription` 不翻譯 | `test_settings_dialogs` | 未跑；預期 `test_each_panel_label_name_and_accessible_description` |
| M10 | `_format_title` 的 category 不翻譯 | `test_settings_dialogs` | 未跑；預期 `test_the_category_list_the_titles_and_the_validation_caption`（`DotExpress 設定：Translation`） |
| M11 | `_collect` 的框標題不翻譯 | `test_settings_dialogs` | 未跑；預期同上（caption） |
| M12 | 模板寫死 `lang="en"` | `test_dual_view_html`、`test_document_formats` | 未跑；預期 `test_the_page_declares_the_given_language`、`test_html_writer_declares_the_interface_language` |
| M13 | `_write_html` 寫死 `zh-TW` | `test_document_formats` | 未跑；預期 `test_html_writer_declares_the_interface_language` 的 `en` 子測試 |
| M14 | frame render 寫死 `zh-TW` | `test_gui_document_flows` | 未跑；預期 `test_the_dual_view_window_declares_the_interface_language` 的 `en` 子測試 |
| M15 | N1、N2 對調 | `test_gui_document_flows` | 未跑；預期 `test_a_failed_backup_is_explained_by_its_kind_of_error`（10 個子測試全錯）、`test_each_kind_of_problem_gives_its_reason` |
| M16 | 去掉 access 判斷（永遠 N2） | `test_gui_document_flows` | 未跑；預期同上（6 個 access 子測試） |
| M17 | 不 format `{backup}` | `test_gui_document_flows` | 未跑；預期兩個測試比對整段文字 |
| M18 | 面板 label／name 用 msgid | `test_settings_dialogs` | 未跑；預期 `test_uses_title_for_accessible_label`（`轉譯`）、`test_each_panel_label_name_and_accessible_description` |
| M19 | `about.longName` 改回 `_()`（載入時翻譯） | `test_i18n` | 未跑；預期 AST guard、subprocess probe、`test_texts_defined_at_import_are_n_markers` 三個都抓 |
| M20 | 分類清單不翻譯 | `test_settings_dialogs` | 未跑；預期 `test_the_category_list_the_titles_and_the_validation_caption` |

要補跑時：`$PY $SP\mut.py $SP\work\client`（副本已含 `scripts/`；把 `MUTANTS` 切到 M6 起即可），一次一個，600 MB 規則。

## 3. zh_TW 措辭

N1 `檔案已損壞，而且在取代它之前無法先備份為「{backup}」。檔案或備份檔可能正被其他程式使用，或你沒有該資料夾的寫入權限。請關閉其他程式後再試一次。` 與 N2 `…請確認磁碟還有可用空間，且你有該資料夾的寫入權限。` 和使用者 2026-10-14 的決定（Q1 長版）逐字相同；第一句沿用字串 22，後半沿用 F-12 兩條寫入失敗的句子，`備份檔` 與 `點字檔`／`文字檔` 一致。其餘 13 個改成顯示時翻譯的字串，msgstr 完全沒變（`.mo` 在 step 2、3 位元組相同，GUI 143 讀回的文字和改前相同）。

## 修正記錄（2026-10-14，修正階段；本輪因記憶體只做輕量工作：git、編輯、catalog 重新產生、focused 測試模組）

**合併 `main`：** commit `180ba57`（`merge: main into fix/f14-i18n-prep after F-13 (F-14)`，`main` = `da01418`，含 F-13 與使用者的 `about.py` 1.8）。衝突只有 `client/locales/dotexpress.pot` 與 `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`，沒有手動合併：取本分支的 `.po`，以 `scripts/generate-pot.bat` 重新產生範本、把 `POT-Creation-Date` 固定為 `2026-10-10 12:00+0800`、`msgmerge`、`msgfmt --check --statistics`。結果 408 個 msgid、408 已翻譯、0 fuzzy、0 個 `#|` 行、26 筆 `#~`；`.pot` 可重現（再產生一次與 commit 的位元組相同）。與本分支合併前的 catalog 相比，除了 `#:` 參照以外只有 N1、N2 的 msgstr 被 `msgmerge` 折成兩行（文字不變）；`.mo` 與 `10b277d` 位元組相同（sha256 `9045b759…22a122b3`），所以 N1、N2 的內容仍是使用者決定的版本。`gui.py`、`dialog.py`、`about.py`、`test_gui_document_flows.py` 自動合併；`about.py` 保留 `version = "1.8"`、`version_detailed = "1.8"` 與 F-14 的 `N_`／`about_message()`。

程式與腳本在 commit `05b07ec`（`fix: set the interface language in one step; keep item 144 from starting a real browser (F-14 review M-1, M-4)`），`HEAD:client` `e4dc089f014011e1b8fd84e8bb31adb113c2eb39`；文件在 commit `ee6d88f`（`docs: F-14 review fixes: spec corrections 12, string 22 and catalog notes (F-14 review M-2, M-3)`）。

| 發現 | 處理 | 做了什麼 |
| --- | --- | --- |
| M-1 | 已修正（`05b07ec`） | `auto/item144.py` 移除 `window` 參數，`f14gui.fake_browser(d)` 在程式啟動前一律執行；`f14gui.py` 刪除 `dual_view`、`dual_view_window` 與 `DUAL_VIEW`；`dual_view_page` 在替身瀏覽器不在 `PATH` 最前面時丟 `RuntimeError`，不會送出「轉譯 > 雙視檢視」。`auto-results.md` 偏離 1 補註這次的修改。沒有執行任何 GUI 腳本。 |
| M-2 | 已修正（`ee6d88f`） | 兩份 spec 的「規劃後的修正」新增第 12 點：H1（`DualViewFrame`）沒有呼叫者、144 (a) 改讀程式為瀏覽器寫出的頁面檔、D6 不受影響。H1 列、前後對照表、144 (a) 的步驟與項目 145 的說明都改成「轉譯 > 雙視檢視（在瀏覽器開啟）」；「範圍外／後續」新增「雙視檢視視窗的 dead code」一項。dead code 沒有移除。 |
| M-3 | 已修正（`ee6d88f`） | 兩份 spec 的 D7、D8、「使用者可見字串」與驗收條件 4 改為「字串 22 直接消失、obsolete 維持 26」；第 3 點（與 plan 的 Spec Corrections 3）的「第二次 msgmerge 不再變動」改為：`msgmerge --update` 在沒有訊息改變時不寫檔，所以當時的檢查成立；任何會寫出檔案的 `msgmerge` 都會把 N1、N2 折行（已在 scratchpad 用 `10b277d` 的 catalog 驗證兩種情況）。合併 `main` 重新產生 catalog 後 N1、N2 已是折行形式，`msgmerge` 不再改動任何位元組。 |
| M-4 | 已修正（`05b07ec`） | `i18n` 的 `_translation`、`_language` 兩個全域變數改成一個 `_active = (catalog, language)`；`set_language` 先算好兩個值，再以一次指派換掉這一組；`_` 讀 `_active[0]`，`current_language` 讀 `_active[1]`。新測試 `test_the_catalog_and_the_language_change_in_one_assignment`（AST：`set_language` 只宣告 `_active` 一個 global、只有一次指派且是兩個元素的 tuple；並在切換 `en`、`zh_TW` 後檢查這一組）。沒有新字串，catalog 不變（重新產生範本，位元組相同）。 |

驗證（本輪，`$PY -B -X utf8 -m unittest`，cwd 為 worktree 的 `client/`，每批執行前可用記憶體都 ≥ 600 MB，實際 611–679 MB）：`tests.test_i18n` 48 個 OK；`test_dual_view_html`、`test_document_formats`、`test_settings_dialogs`、`test_settings_options` 135 個 OK；`test_dialog_validation`、`test_dictionary_entry_list_model`、`test_config`、`test_translation_golden` 147 個 OK；`test_dictionary_entries_dialog` 99 個 OK；`test_gui_document_flows` 240 個 OK（含 About 與備份訊息的測試）；F-13 合併進來的 `test_conversion_presenter`、`test_client_init` 58 個 OK。合計 727 個，全部通過。About 測試（`test_the_about_text_is_translated_when_shown`、`test_about_box_uses_the_helper`）在 1.8 下通過；catalog 測試（`test_generate_pot_extracts_n_keyword` 等）在 `test_i18n` 內通過。三個 fixture 的 blob sha256 不變（`e67d95a1…`、`f493da52…`、`8dc8572e…`）；`client/braille/`、`task.md`、`client2/`、`preprocessing/`、`testdata/` 與使用者資料都沒有改動。M-4 的新測試沒有另做 mutant 執行。

**尚未執行（由 orchestrator 之後排程）：** 完整測試、修正階段的 build，以及 GUI 項目重跑（至少 144 用新腳本；141–143 視需要）。本輪依記憶體限制沒有執行這些，也沒有補跑 review 第 2 節的 M6–M20。

仍留給使用者：項目 145（NVDA，未勾選）；spec「本 spec 引入的使用者可見預設」列出的未確認預設；移除雙視檢視視窗 dead code 的後續任務。
