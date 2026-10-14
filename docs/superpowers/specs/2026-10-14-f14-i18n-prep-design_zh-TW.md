# 介面語言切換的準備、HTML `lang` 與設定備份訊息（F-14）設計

## 目標

F-14 是 `docs/superpowers/history/2026-10-14-01-handoff/HANDOFF.md` 第 1 節的「i18n」任務，涵蓋 `task.md` 第五節「下一輪要修」中的三項（編號依該清單的順序）：

- **第 7 項：** 為將來在程式內切換介面語言做準備（F-12 review M-7）：不再於模組載入時翻譯任何介面文字；`i18n` 可以回答目前使用的介面語言。
- **第 4 項：** 雙視檢視的 HTML 與匯出的 HTML 宣告介面語言（`lang="zh-TW"`），不再是 `lang="en"`。
- **第 8 項：** `config.json.bak` 備份失敗時的「設定未儲存」框，用文字說明原因，不再附系統原文與暫存檔名。

先做第 7 項：第 4 項的 `lang` 取自第 7 項新增的「目前介面語言」。

使用者的決定（2026-10-14，`task.md` 第五節「下一輪要修」與「延後的項目」），本文不再重問：

- **U1（第 7 項）。**「全面找出模組載入時就呼叫 `_()` 的地方（已知 `about.py`、`dictionaries/entries.py` 的類型名稱、`settings/dialogs.py`，實作時要 grep 全部），改成載入時只用 `N_()` 標記、顯示時才翻譯（或改成函式）。介面語言改由 `i18n` 提供「目前語言」的查詢，雙視窗 HTML 的 `lang` 也從這裡取得。**不含**切換語言的功能本身（選單、設定、重建畫面）；目前介面語言仍固定 `zh_TW`，使用者看到的行為不變。」
- **U2（第 4 項）。**「雙視窗／匯出 HTML 的 `lang` 依 DotExpress 介面語言寫入（簡單版）：`dual_view/html.py` 目前寫死 `<html lang="en">`；改成依介面語言（如 `zh_TW` → `zh-TW`）。不做逐段標示英文的完整版。」
- **U3（第 8 項）。**「保留 `config.json.bak` 的備份行為（只寫不讀，損壞的 `config.json` 在第一次存設定前複製過去）。`BACKUP_FAILED` 的「設定未儲存」訊息不再附系統原文與暫存檔名，改照 F-12 寫入失敗的做法依錯誤類型顯示翻譯過的說明（權限／被占用 vs 其他），新增 1–2 條字串；原文照舊寫進 log。」
- **U4。** 同一清單的第 1、2、3、5、6 項屬於 F-13（見「與 F-13 的關係」）。HANDOFF 第 4 節：`config.py` 的 `set_lang` 是點字轉換的語言，不是介面語言。

完成後：

- 原本在載入時翻譯的介面文字，全部改在顯示時翻譯。載入後切換使用中的 catalog（F-14 只有測試會這麼做），這些文字就跟著改變。
- `i18n.current_language()` 傳回 `"zh_TW"`，`i18n.html_language_tag()` 傳回 `"zh-TW"`。
- 雙視檢視視窗、它在瀏覽器開啟的副本，以及每個匯出的雙視檢視 HTML 檔（單一匯出、全部匯出、沒有轉換資料的頁面）都以 `<html lang="zh-TW">` 開頭。
- 第一次存設定前備份失敗時，顯示兩種翻譯過的原因之一（存取問題，或其他），並寫出備份檔的路徑；系統原文只留在 `config.log`。
- 使用者看到的其他東西都不變：第 7 項涉及的每個文字、標題、標籤與對話框，在 zh_TW 下都完全相同。

新的使用者可見字串：**2** 個 msgid，另有 1 個 msgid 不再使用（F-12 的字串 22）。msgid 數量從 **407** 變成 **408**。第 7 項與第 4 項不新增也不移除任何 msgid。

非目標：切換語言的功能本身（選單、設定、重建視窗）；在 HTML 中逐段標示英文的 `lang`；修改 `braille/tables/__tables.py`；F-13 的項目。

## 規劃後的修正（F-14，2026-10-14）

依 `main` `a147fed` 的程式碼重新檢查：清單（`about.py`、`dictionaries/entries.py`、`settings/dialogs.py` 共 15 個載入時呼叫；`braille/tables/__tables.py` 198 個）、決定 D1–D8、前後對照表與測試計畫都成立，另有以下細化。plan（`docs/superpowers/plans/2026-10-14-f14-i18n-prep.md`）的「Spec Corrections and Refinements」一節是同一份清單。

1. **基準與數量。** 在 `a147fed`（`HEAD:client` `a967d8d4`）上完整測試為 `Ran 1632`、`OK (skipped=6)`；catalog 有 407 個 msgid、26 筆 obsolete。F-14 新增 20 個測試、修改 7 個：步驟 1 後 `Ran 1637`（新增 5），步驟 2 後 `1648`（新增 11；修改 2：About 測試、`test_uses_title_for_accessible_label`；以及 consumer 守門測試的集合），步驟 3 後 `1651`（新增 3；3 個匯出測試、`test_dual_view_html` 與 golden 測試的 render 呼叫），步驟 4 後 `1652`（新增 1；`test_each_kind_of_problem_gives_its_reason`、字串測試、`test_config` 的備份測試）。spec 估計約 30 個。
2. **Catalog。** 步驟 1 不動 catalog（`i18n.py` 沒有 msgid）。步驟 2–4 會移動 msgid 上方的行數，所以每一步都重新產生範本與 `.po`；任何 commit 之後都沒有過期的 `#:` 參照，不需要另外的 `chore:` commit。步驟 2 的 `msgmerge` 也會把 F-12 修正 commit 寫成一行的一個 msgstr（「無法寫入檔案」的原因）折成兩行（F-13 也一樣）。步驟 2、3 之後 `.mo` 與 `a147fed` 的位元組完全相同。
3. **D8 的實作。** `msgmerge` 把 N1 配對到 F-12 的「無法寫入檔案（權限）」字串、把 N2 配對到字串 22，兩者都是 `#, fuzzy`（修正前 406 個已翻譯、2 個 fuzzy）。一次性工具 `set_msgstr.py` 寫入表中的兩個 msgstr（各一行；第二次 `msgmerge --update` 因為沒有訊息改變而不寫檔，但任何會寫出檔案的 `msgmerge` 都會把兩者折成它的行寬，文字不變；見第 12 點）並清掉 fuzzy：408 個已翻譯、0 fuzzy。字串 22 成為 N2 的 fuzzy 來源，所以它**不會**變成 obsolete，而是直接消失，obsolete 維持 **26** 筆（spec 寫 27）。msgid 集合等於 `a147fed` 的加上 N1、N2，減去字串 22。
4. **使用者的決定（2026-10-14）。** Q1：N1 採用表中較長的版本，一字不改（`檔案已損壞，而且在取代它之前無法先備份為「{backup}」。檔案或備份檔可能正被其他程式使用，或你沒有該資料夾的寫入權限。請關閉其他程式後再試一次。`），N2 照表。Q2：使用者已把 `about.py` 的版本號更新 commit 到 `main`（`7db6538`、`2053646`：`version` 與 `version_detailed` = `"1.8"`），「Merge 前提」不再需要 stash。F-14 不動 `about.py` 第 4–8 行（本分支上是 `"1.2"`）；本分支與 `main` `2053646` 的 `git merge-tree` 沒有衝突，與 F-13 分支只有兩個 catalog 衝突，依「與 F-13 的關係」重新產生，不手動合併。
5. **B1 的實作。** About 測試的版本號從 `about.version` 與 `about.version_detailed` 讀取，而不是寫死 `1.2 (1.2)`，所以 merge `main` 的 1.8 之後仍是綠燈；其餘 zh_TW 文字是字面值。GUI 項目 143 (a) 在 `N-f14`（由本分支建置）上仍預期 `版本：1.2 (1.2)`。
6. **D5 的實作。** AST 守門測試斷言「載入時有翻譯呼叫的檔案」正好是 `["braille/tables/__tables.py"]`（原因寫在常數旁邊），而不是經過允許清單過濾；掃描函式本身用一段程式碼測試每一種呼叫（模組層級、類別本體、預設參數、decorator、lambda 預設值；不含函式與 lambda 本體；`translations.gettext` 這類屬性呼叫也算）。它和 catalog 測試一樣跳過產生出來的 `braille/liblouis/`。保留 import 探測：一個子程序（`-B`）把 `i18n._` 換成記錄器後 import `main.py` 以外的所有 client 模組（約 5 秒）；沒有安裝 wx 的環境會略過。
7. **D3、D4 測試的實作。** 沒有任何 wx stub 能建立 `AddSymbolDialog`，所以它的測試用真正的 `__init__`，把模組的 `wx` 換成 `MagicMock`，讀取傳給 `wx.Choice` 的 `choices`。設定測試用現有的 `build_panel` 建立三個面板，分類清單則在不經建構子建立的對話框上呼叫 `_build_layout`。`test_uses_title_for_accessible_label` 現在預期 `轉譯`（D4 之後它的 title 是 msgid）。
8. **E 測試的實作。** 一個表格式測試含十個錯誤：六個存取錯誤（`PermissionError`；`os.replace` 丟出、帶兩個檔名的 `[WinError 5]`；winerror 32；winerror 33；只有 winerror 5；errno `EACCES`）得到 N1，其他四個（`ENOSPC`、`EIO`、`IsADirectoryError`、`ValueError`）得到 N2；訊息框裡都沒有 `k3j9x2`、`.tmp`、`WinError`、`Errno`、`詳細資訊`。`test_config` 的備份測試另外確認 ERROR 紀錄的 `exc_info` 就是 problem 的錯誤。
9. **變異檢查：20 個 mutant**，即 spec 的清單，只改一項：第 20 個改為「守門測試跳過整個 `braille/`」（守門測試沒有可放寬的允許清單；跳過該資料夾會漏掉 `__tables.py`，而守門測試預期找到它）。
10. **commit 主旨**以 `(F-14)` 結尾；步驟 2 的 commit 內文註明 F-12 review M-7。
11. **Windows 項目。** 141、142 是修正項目（兩個版本都跑），143、144 是回歸項目（只跑 `N-f14`）。142 原封不動重跑 F-12 的 `item114.py` (b)。GUI 腳本放在 `docs/superpowers/history/2026-10-14-03-f14-i18n-prep/auto/`。
12. **review 修正（F-14 review M-1～M-4，2026-10-14）。** (a) **H1 沒有路徑可達。** `gui._show_dual_view` 與 `_create_dual_view_frame`（`DualViewFrame`，`web_view.SetPage`）在 `a147fed` 就沒有任何呼叫者，只有 `tests/test_gui_document_flows.py` 的兩個單元測試直接呼叫。「轉譯 > 雙視檢視」執行 `on_open_dual_view` -> `_open_dual_view_in_browser`（H2）。`_render_dual_view_for_open_document` 是兩者共用的，所以 D6 不受影響。GUI 項目 144 (a) 因此在 `PATH` 最前面放替身瀏覽器，讀程式寫到 `<d>\dual_view` 的頁面檔（plan 的 Implementation Notes 5(a) 與 `auto-results.md` 偏離 1 已這樣寫）；H1、前後對照表與項目 145 都以此為準。移除 `_show_dual_view`、`_create_dual_view_frame` 與 `DualViewFrame` 列為後續項目，不在 F-14（範圍外）。項目 144 的腳本已移除會讓程式啟動使用者真實瀏覽器的 `window` 模式，替身瀏覽器一律安裝，沒有替身時 `f14gui.dual_view_page` 拒絕執行（M-1）。(b) **字串 22 與 obsolete 數量。** D7、D8、「使用者可見字串」與驗收條件 4 原本寫字串 22 會變成 obsolete（27 筆）；實作時它直接消失，obsolete 維持 26 筆（第 3 點）。(c) **msgmerge 與兩個新 msgstr。** plan 的「第二次 msgmerge 不再變動」只是因為 `msgmerge --update` 在沒有訊息改變時不重寫檔案；`msgmerge -o`，或參照移動後的 `--update`，都會把 N1、N2 折成它的行寬，文字不變。把 `main`（F-13）merge 進本分支時重新產生了 catalog，所以現在 N1、N2 已是折行的形式：`msgmerge` 不再改動任何位元組，`.mo` 不變（408 個 msgid、0 fuzzy、26 筆 obsolete）。(d) **`set_language`** 把 catalog 與語言當成一組，一次指派（M-4），其他執行緒不會讀到新 catalog 配舊語言。

## 與 F-13 的關係

F-13（行為與 NVDA，worktree `D:\workspace\DotExpress-f13`，branch `fix/f13-behavior-nvda`）從同一個 `main` `a147fed` 平行進行，很可能先 merge。之後 F-14 的 plan 把 `main` merge 進自己的 branch，重新取得下列行號（行號只供定位；程式碼以函式名稱指稱），並重跑完整測試。

可能重疊的檔案：

| 檔案 | F-13（預期） | F-14 |
| --- | --- | --- |
| `client/gui.py` | `_load_startup_documents`（`:244`）、`BrailleFrame.__init__`、`BrailleApp.OnInit`、`OnExit`（`:1302-1311`） | import 行 `:9`；`_render_dual_view_for_open_document`（`:329-335`）；`_report_settings_save_problem` 的 `BACKUP_FAILED` 分支（`:474-477`）；`on_about`（`:546-547`） |
| `client/dialog.py` | `_confirm_hidden_rows`、`_hidden_row_line`（`:609` 起）、F-11 的兩個確認框 | import `:9-11`；`AddSymbolDialog.__init__` 的類型選單（`:110`） |
| `client/dictionaries/entry_list_model.py` | 可能改隱藏列的值（第 6 項） | import `:46`；`cell_text`（`:165`） |
| `client/ui/message_box.py`、`client/ui/conversion_presenter.py` | 會改 | 不碰 |
| `client/locales/dotexpress.pot`、`.po`、`.mo` | `#:` 參照隨 `gui.py`、`dialog.py` 移動；可能有字串 | `#:` 參照；新增 2 個字串、移除 1 個（修正第 3 點） |
| 測試：`test_gui_document_flows.py`、`test_i18n.py`、`test_dictionary_entries_dialog.py`、dialog 相關測試 | 新測試 | 新增與修改的測試 |

- 共用檔案中改的是不同函式，文字衝突應該很少；兩邊在同一處附加的測試都保留。
- catalog 一律不手動合併：merge `main` 之後，plan 重新產生 `.pot`（`scripts\generate-pot.bat`）、執行 `msgmerge`、再檢查 F-14 的兩個 msgstr 與 fuzzy 標記，然後重新編譯 `.mo`。數量是 `main` 的數量加 1。
- GUI 項目：F-13 用 121–140，F-14 用 141–145。

## Merge 前提（需要使用者處理）

主 checkout `D:\workspace\DotExpress` 的 `client/about.py` 有使用者尚未 commit 的修改（`version = "1.8"`，第 7 行）。F-14 會改 `client/about.py`（D2，第 1 行與第 10–41 行；第 7 行不動），所以只要那個修改還沒 commit，在主 checkout 執行 `git merge` 就會被拒絕。協調者不能自行 stash 或覆蓋它。merge 之前，使用者可以先 commit 這個版本號修改（之後 merge 會合併兩邊，修改區塊彼此分開，不會衝突），或同意在 merge 前後用 `git stash push client/about.py`／`git stash pop` 暫時移開。plan 與 review 都不需要主 checkout 的 `about.py`。

## 現況（2026-10-14 在 `main` `a147fed` 驗證，worktree `D:\workspace\DotExpress-f14`，`HEAD:client` `a967d8d4cea147cf25ccc0f490c8f94e41e711ce`）

`$PY` 是 `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`。撰寫本 spec 時沒有跑測試；基準取自 HANDOFF 第 2 節：`Ran 1632`、`OK (skipped=6)`；catalog 有 407 個 msgid（`.po` 有 408 行 `msgid`，含標頭），全部已翻譯，0 fuzzy，26 個 obsolete 條目。探針在 worktree 的 `client/` 執行，腳本放在本次 session 的 scratchpad（`f14spec\scan.py`、`scan2.py`、`probe_import.py`），沒有 commit。

### 目前的翻譯方式（`client/i18n.py`）

- `:44` `_translation = load_translation()` 只載入一次 zh_TW catalog（`LOCALE_LANGUAGES = ("zh_TW",)`，`:16`；`fallback=True`：找不到 catalog 時得到原樣傳回的 `NullTranslations`）。
- `:45` `_ = _translation.gettext`：綁定在這一個 catalog 物件上的方法。每個使用端都寫 `from i18n import _`，把這個綁定方法存在自己的全域變數裡。之後就算換掉 catalog，也影響不到任何模組。
- `N_`（`:48-50`）只是給 `xgettext` 的標記（`scripts\generate-pot.bat`：`--keyword=_ --keyword=N_`）。
- 沒有「目前介面語言」的概念：只有 `LOCALE_LANGUAGES` 透露了它。
- `gettext("")` 會傳回 catalog 標頭（`Project-Id-Version: ...` 那一段）。目前沒有程式刻意傳 `""`，但 `_(str(error))`（`settings/dialogs.py:158`）遇到 `ValueError("")` 時就會顯示標頭。

### 清單：載入時就執行的 `_()`

兩次掃描：

1. **AST 掃描**（`scan.py`）：`client/` 底下除了 `tests/`、`.venv/`、`build/`、`dist/` 以外的每個 `.py`，找出函式本體以外（模組層級、類別本體、預設參數、decorator）對 `_`、`gettext`、`ngettext`、`pgettext`、`GetTranslation` 的每個呼叫。`scan2.py` 列出模組層級對其他函式的呼叫（`get_importable_formats()`、`build_language_blocks(...)`、`get_logger(...)` 等）；其中沒有任何一個會翻譯。
2. **載入探針**（`probe_import.py`）：在載入任何東西之前把 `i18n._` 換成記錄器，再載入全部 99 個 client 模組（`main.py` 除外，它會執行示範；不建立任何視窗）。記錄到的正好是下表 15 個呼叫，沒有其他（沒有間接呼叫）。

| # | 位置（`a147fed`） | 程式碼 | msgid | 讀取的地方 |
| --- | --- | --- | --- | --- |
| I1 | `about.py:10` | `longName = _("DotExpress")` | `DotExpress` | `about.py:35`（I4 的 format） |
| I2 | `about.py:11` | `description = _("A text-to-braille ...")` | `A text-to-braille translation tool that converts plain text into fixed-width braille, ...` | 無（未使用） |
| I3 | `about.py:13-15` | `copyright = _(...).format(years=copyrightYears)` | `Copyright (C) {years} DotExpress Contributors` | `about.py:40`（I4 的 format） |
| I4 | `about.py:16-41` | `aboutMessage = _("""{longName} ({name}) ...""").format(...)` | 「關於」的文字 | `gui.py:547` `on_about` |
| I5 | `dictionaries/entries.py:15` | `ENTRY_TYPE_OPTIONS` 中的 `("General", _("General"))` | `General` | `dialog.py:110`（類型選單）、`entry_list_model.py:165` 經由 `ENTRY_TYPE_LABELS`（`entries.py:19`） |
| I6 | `dictionaries/entries.py:16` | `("Bopomofo", _("Bopomofo"))` | `Bopomofo` | 同 I5 |
| I7 | `dictionaries/entries.py:17` | `("Braille", _("Unicode Braille"))` | `Unicode Braille` | 同 I5 |
| I8 | `settings/dialogs.py:357` | `TranslationSettingsPanel.title = _("Translation")` | `Translation` | `SettingsPanel.__init__`（`:54-55` 標籤與名稱）、分類清單（`:270`）、對話框標題（`:677`、`:685`） |
| I9 | `settings/dialogs.py:358` | `TranslationSettingsPanel.panel_description = _(...)` | `Translation output mode, width, and dictionary options` | `SettingsPanelAccessible.GetDescription`（`:42-43`） |
| I10 | `settings/dialogs.py:438` | `TranslationTablesPanel.title` | `Translation Tables` | 同 I8 |
| I11 | `settings/dialogs.py:439` | `TranslationTablesPanel.panel_description` | `Translation table mappings for different languages` | 同 I9 |
| I12 | `settings/dialogs.py:557` | `ViewSettingsPanel.title` | `View` | 同 I8 |
| I13 | `settings/dialogs.py:558` | `ViewSettingsPanel.panel_description` | `Font, font size, and color scheme for the main window input and output areas` | 同 I9 |
| I14 | `settings/dialogs.py:653` | `DotExpressSettingsDialog.base_title = _("DotExpress Settings")` | `DotExpress Settings` | `_collect`（`:698`，驗證錯誤框的標題） |
| I15 | `settings/dialogs.py:654` | `DotExpressSettingsDialog.title_template = _(...)` | `DotExpress Settings: {category}` | `_format_title`（`:681-682`） |

**共 3 個檔案、15 個呼叫位置。** `ENTRY_TYPE_LABELS` 的其他用途（`entries.py:88` `normalize_entry_type`、`dialog.py:149`）與 `ENTRY_TYPE_OPTIONS` 的其他用途（`dialog.py:148`、`:167`）只讀鍵值。

**範圍外，記錄於此：** `client/braille/tables/__tables.py` 在載入時以**自己的** `_` 呼叫 **198** 次（`:23-32` 另外建立一個 `gettext.translation`，`languages=["zh_TW"]`、`localedir=<braille>/locales`；點字表顯示名稱在 `:36-695`）。這個檔案不能改（HANDOFF 第 5 節；它由 `scripts\sync-nvda.py` 從 NVDA 同步，而那個腳本也不能執行）。目前的效果：打包版找得到 `_MEIPASS\locales`，載入時就拿到 zh_TW 名稱；從原始碼執行找不到 `client/braille/locales`，拿到英文名稱，再由 `TranslationTablesPanel._load_table_options`（`settings/dialogs.py:545-551`）在顯示時翻譯一次（P2-3 spec D6）。對將來的語言切換而言：打包版的點字表名稱會停在啟動時的語言；顯示時的 `_()` 無法把中文名稱轉成別的語言。切換語言的任務必須在不修改 `__tables.py` 的前提下解決（例如重新載入點字表登錄，或另外保留英文名稱）。F-14 不改 `_load_table_options`。

在**建立**視窗或選單時翻譯的文字（標籤、選單項目、`wx.Choice` 項目、視窗標題）本來就是顯示時翻譯；要即時切換語言，必須重建這些視窗。這屬於將來的功能（U1），不在 F-14。

### 宣告 `lang` 的 HTML

`dual_view/html.py:36-75` 的 `render_dual_view_html(model, *, empty_message=...)` 是 client 唯一的 HTML 範本（grep `<html`、`doctype`、`SetPage`）。第 `:51` 行寫出 `<html lang="en">`。產生它的路徑：

| # | 路徑 | 呼叫 | 誰看到 |
| --- | --- | --- | --- |
| H1 | 雙視檢視視窗（檢視 > 雙視檢視） | `gui._render_dual_view_for_open_document`（`gui.py:329-335`）-> `_refresh_dual_view` -> `DualViewFrame.refresh_html` -> `web_view.SetPage`（`ui/dual_view.py:68-69`） | 程式內的網頁檢視。**沒有任何路徑會走到**（修正第 12 點）：在 `a147fed` 就已是 dead code |
| H2 | 在瀏覽器開啟雙視檢視（`on_open_dual_view` -> `_open_dual_view_in_browser`，`gui.py:350`） | 同一次 render，由 `write_dual_view_html` 寫成程式雙視資料夾下的 `dual-view-*.html` | 系統瀏覽器 |
| H3 | 檔案 > 匯出 > 雙視檢視 HTML，以及以此格式全部匯出 | `documents/formats._write_html`（`formats.py:104-113`，render 在 `:109`） | 匯出的檔案 |
| H4 | 沒有轉換資料的頁面 | H1–H3 帶 `empty_message`（`gui.py:334`、`formats.py:112`） | 同上 |

`tests/test_translation_golden.py:174` 執行 `render_dual_view_html(model)`，把結果的 sha256 存成 `tests/fixtures/translation_golden.json` 的 `dual_view_html_sha256`；這個 fixture 的 blob sha256（`e67d95a1...`）不能改變。所以必須仍能產生 `lang="en"` 的完全相同位元組。

目前沒有任何測試檢查 `lang` 屬性（grep）。

### 設定備份訊息（`config.py`、`gui.py`）

- `ConfigStore._save`（`config.py:194-229`）：`config.json` 損壞時（`_UnreadableConfig` 帶非 `OSError` 的錯誤），`_backup_unreadable`（`:189-192`）讀取 `config.json`，以 `write_bytes_atomically` 寫出 `config.json.bak`（先寫暫存檔 `.config.json.bak.<亂數>.tmp`，再 `os.replace`）。任何例外都由 `_log_current_exception(logging.ERROR, "Failed to save config file %s", path)` **連同 traceback**（`exc_info=True`）寫進 `config.log`，`_save` 傳回 `ConfigSaveProblem(BACKUP_FAILED, error, path, backup_path)`，不寫 `config.json`。
- `BrailleFrame._report_settings_save_problem`（`gui.py:456-494`，F-12 D6 與 review M-2／M-5）顯示這次執行的第一個問題。它的 `BACKUP_FAILED` 分支（`:474-477`）使用 F-12 的字串 22 `The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Details: {error}`／`檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}`。`UNREADABLE` 與 `WRITE_FAILED` 分支已經用 `config.is_access_error`（`config.py:84-90`：`PermissionError`，或 `winerror` 為 5、32、33 或 `errno` 為 `EACCES`、`EPERM` 的 `OSError`）選擇文字。
- F-12 的 GUI 紀錄（`auto-results.md` 項目 114 (b)，build `N-f12b`，`config.json` = `{`、`config.json.bak` 是資料夾）顯示的內容是 `檔案已損壞，而且在取代它之前無法先備份為「<d>\config.json.bak」。詳細資訊：[WinError 5] 存取被拒。: '<d>\\.config.json.bak.<rnd>.tmp' -> '<d>\\config.json.bak'`。
- 固定目前文字的測試：`tests/test_gui_document_flows.py:5289-5291`（`test_each_kind_of_problem_gives_its_reason`，`:5283`）與 `tests/test_i18n.py:237`、`:244`（`test_settings_not_saved_strings_are_translated`）。

## 設計

### 第 7 項：顯示時才翻譯

**D1. `i18n` 透過使用中的 catalog 翻譯，並知道介面語言。**

- `_` 改成模組函式：`def _(message: str) -> str`，每次呼叫時才查模組目前的 catalog。使用端照樣寫 `from i18n import _`；拿到的是這個函式，之後換 catalog 就會影響每個模組。patch 使用端 `_` 的測試（`dialog._`、`gui._`、`settings.dialogs._`、`dialog_base._`）不受影響。
- `_("")` 傳回 `""`，而不是 catalog 標頭。由協調者採用建議預設；使用者可在 merge 前推翻（O3）。
- 新增：`SOURCE_LANGUAGE = "en"`（msgid 的語言）。
- 新增：`set_language(language: str, *, localedir: Path | None = None) -> None`，以 `load_translation(localedir, (language,))` 載入 `language` 的 catalog，設為使用中。記錄的語言：找到 catalog（`gettext.GNUTranslations`）時是 `language`，否則是 `SOURCE_LANGUAGE`，因為這時使用者看到的是英文 msgid。`i18n` 載入時呼叫 `set_language(LOCALE_LANGUAGES[0])`，得到的 catalog 與現在完全相同。F-14 中沒有其他程式碼呼叫它；它是將來切換功能要用的接口，測試現在就用它。由協調者採用建議預設；使用者可在 merge 前推翻（O1、O2）。
- 新增：`current_language() -> str` 傳回記錄的語言（程式中是 `"zh_TW"`）。
- 新增：`html_language_tag(language: str | None = None) -> str` 傳回 `language`（預設為 `current_language()`）的 BCP 47 形式：把 gettext 代碼中的 `_` 換成 `-`（`zh_TW` -> `zh-TW`，`en` -> `en`）。不需要對照表：DotExpress 能提供的 gettext 代碼（`ll` 或 `ll_CC`）都是一對一。
- `LOCALE_LANGUAGES`、`load_translation`、`resource_path`、`N_` 的簽章不變。介面語言仍固定 `zh_TW`。
- 與 `ConfigStore.get_lang`／`set_lang`（`config.py:250-273`，選擇點字轉換語言）無關；F-14 兩者都不改，`current_language` 也不讀 `config.json`。

**D2. `about.py`：載入時只放 msgid，顯示時才產生文字。**

- `longName = N_("DotExpress")`、`description = N_("A text-to-braille ...")` 存 msgid（`description` 沒有人用，保留成 msgid 以留在 catalog）。
- `copyright_text() -> str` 傳回 `_("Copyright (C) {years} DotExpress Contributors").format(years=copyrightYears)`。
- `about_message() -> str` 傳回翻譯後的「關於」文字，format 方式與現在相同（`longName=_(longName)`、`copyright=copyright_text()`、`name`、`version`、`version_detailed`、`url`）。`# Translators:` 註解跟著 msgid。移除模組屬性 `copyright` 與 `aboutMessage`（只有 `gui.on_about` 讀 `aboutMessage`）。
- `name`、`url`、`version`、`version_detailed`、`copyrightYears`（第 4–8 行）不動（見「Merge 前提」）。
- `gui.on_about`（`gui.py:547`）顯示 `about.about_message()`。

**D3. `dictionaries/entries.py`：詞條類型標籤改存 msgid。**

- `ENTRY_TYPE_OPTIONS` 存 `(key, N_(label))`；`ENTRY_TYPE_LABELS` 把鍵對應到 msgid。兩者名稱與鍵都不變，所以 `normalize_entry_type`、`DEFAULT_ENTRY_TYPE`、`dialog.py:148-149` 與 `:167` 不必改。
- 新增 `entry_type_label(entry_type: str) -> str`：已知的鍵傳回翻譯後的標籤，否則原樣傳回 `entry_type`（與現在的 `ENTRY_TYPE_LABELS.get(entry.entry_type, entry.entry_type)` 相同）。
- 新增 `entry_type_choices() -> list[str]`：依選項順序傳回翻譯後的標籤。
- `AddSymbolDialog.__init__`（`dialog.py:110`）以 `entry_type_choices()` 建立 `wx.Choice`；`EntryListModel.cell_text`（`entry_list_model.py:165`）傳回 `entry_type_label(entry.entry_type)`。清單是 virtual list，儲存格在繪製時才讀。

**D4. `settings/dialogs.py`：面板與對話框標題改存 msgid。**

- 三個面板的 `title`、`panel_description`，以及 `DotExpressSettingsDialog` 的 `base_title`、`title_template`，都存 `N_` msgid。屬性名稱不變（`tests/test_settings_options.py:265` 固定了它們）。
- 每個讀取的地方都翻譯：`SettingsPanel.__init__`（`SetLabel`、`SetName`）、`SettingsPanelAccessible.GetDescription`、`MultiCategorySettingsDialog._build_layout`（分類清單）、`DotExpressSettingsDialog._format_title`（`_(self.title_template).format(category=_(category))`，傳入 msgid）、`_after_category_change`、`_collect`（對話框標題 `_(self.base_title)`）。
- 基底類別保留 `title = ""`、`panel_description = ""`；依 D1 的 `_("")` 規則，讀出來是 `""`，不是 catalog 標頭。
- `_load_table_options`（`:545-551`）不變（見 `__tables.py` 的說明）。

**D5. 防止再出現載入時翻譯的守門測試。**

- 一個測試像 `scan.py` 一樣走過 client，只要在函式本體以外（模組層級、類別本體、預設參數、decorator）出現 `_`／`gettext`／`ngettext`／`pgettext` 呼叫就失敗；唯一允許的檔案是 `braille/tables/__tables.py`，理由寫在測試中。
- 第二個測試在子程序中執行載入探針：載入 `main.py` 以外的每個 client 模組之前，把 `i18n._` 換成記錄器；不得記錄到任何呼叫。它能抓到 AST 掃描看不到的間接呼叫。若在 8 GB 的機器上記憶體負擔太大（會載入 `wx`），plan 可以不採用；AST 測試保留。

### 第 4 項：HTML `lang`

**D6. HTML 宣告介面語言。**

- `render_dual_view_html(model, *, lang: str, empty_message=...)`：`lang` 是必填的關鍵字參數；範本寫出 `<html lang="{lang}">`（經 escape）。沒有預設值，所以任何產生端都不會漏掉。由協調者採用建議預設；使用者可在 merge 前推翻（O4）。
- H1、H2、H4（`gui._render_dual_view_for_open_document`）與 H3、H4（`documents/formats._write_html`）傳入 `lang=html_language_tag()`，每次 render 時讀取。因此視窗、它的瀏覽器副本、每個匯出檔與空白頁都寫 `zh-TW`。
- `tests/test_translation_golden.py:174` 明確傳入 `lang="en"`，並註明 fixture 是以它記錄的。fixture 的位元組與 sha256 不變，`--write` 也會產生相同內容。
- `dual_view/html.py` 仍然不從 `i18n` 匯入任何東西（`test_translation_import_isolation` 對雙視檢視的檢查維持綠燈）。
- 不做逐段 `lang`（U2）：zh-TW 頁面中的英文字屬於整份 zh-TW 文件。

### 第 8 項：備份訊息

**D7. 依錯誤類型說明備份失敗。**

- `_report_settings_save_problem` 的 `BACKUP_FAILED` 分支：`config.is_access_error(problem.error)` 為真時用字串 N1，否則用字串 N2。兩者都寫出備份路徑（`{backup}` = `problem.backup_path`，與現在相同），都不含錯誤文字，所以暫存檔名與作業系統的措辭從對話框中消失。
- 不變：備份行為（`_backup_unreadable`，只寫不讀）、順序（第一次寫入前先備份；備份失敗就不寫）、每次執行只顯示一次的旗標、標題 `設定未儲存`、包住原因的字串 21、父視窗、`UNREADABLE` 與 `WRITE_FAILED` 分支，以及 log：`config.log` 仍以 ERROR 記錄 `Failed to save config file <path>` 與 traceback，其中有原始錯誤與暫存檔名。
- F-12 的字串 22 不再使用。（實作時它沒有變成 obsolete：`msgmerge` 拿它當 N2 的 fuzzy 來源，所以直接消失；見修正第 3、12 點。）
- 保留 `{backup}` 的理由：那是使用者可以查看或移除的檔案（F-12 的 GUI 項目用的就是名為 `config.json.bak` 的資料夾），而且以前就會顯示。暫存檔名只出現在錯誤文字裡。
- 為了備份而**讀取** `config.json` 時發生的錯誤（在載入與存檔之間被鎖住）也是存取錯誤；所以 N1 寫「檔案或備份檔」。

### Catalog

**D8.** 第 7、4 項不新增也不移除 msgid：plan 在步驟 1–3 之後重新產生範本，把排序後的 msgid 集合與 `a147fed` 比對（相同）；只有 `#:` 參照移動，`.mo` 位元組完全相同。步驟 4 新增 N1、N2：`scripts\generate-pot.bat`、`msgmerge`、填入下表的 msgstr、`msgfmt --check --statistics`（408 已翻譯、0 fuzzy、0 未翻譯）。`msgmerge` 很可能把 N1 或 N2 與字串 22 配成 fuzzy（第一句相同）；plan 要換成正確的 msgstr，並移除 `#, fuzzy` 與 previous-msgid 行。`POT-Creation-Date` 維持 `2026-10-10 12:00+0800`。obsolete 條目 26 -> 27（實作時維持 26，字串 22 直接消失；見修正第 3、12 點）。

## 各路徑的前後對照

| 路徑 | 之前 | 之後 |
| --- | --- | --- |
| 說明 > 關於 | `DotExpress (DotExpress)\n版本：1.2 (1.2) ...` | 相同（D2） |
| 設定對話框：標題、分類清單、面板的無障礙描述、驗證錯誤框標題 | `DotExpress 設定：轉譯`、`轉譯`／`轉譯表`／`檢視`、`轉譯輸出模式、寬度與字典選項`、`DotExpress 設定` | 相同（D4） |
| 字典編輯器：類型欄、新增／編輯詞條的類型選單 | `一般`、`注音`、`Unicode 點字` | 相同（D3） |
| 在瀏覽器開啟雙視檢視（雙視檢視視窗 H1 沒有路徑可達；修正第 12 點） | `<html lang="en">` | `<html lang="zh-TW">`（D6） |
| 匯出雙視檢視 HTML（單一、全部匯出），有或沒有轉換資料 | `<html lang="en">` | `<html lang="zh-TW">`（D6） |
| `config.json` 損壞、備份失敗時改設定（存取錯誤，例如名為 `config.json.bak` 的資料夾、被鎖住的 `.bak`） | `檔案已損壞，而且在取代它之前無法先備份為「<bak>」。詳細資訊：[WinError 5] ... .tmp' -> ...` | N1，帶 `<bak>`（D7） |
| 同上，其他錯誤（磁碟已滿、I/O 錯誤、非 `OSError`） | `... 詳細資訊：<error>` | N2，帶 `<bak>`（D7） |
| 兩者的 `config.log` | ERROR 行加 traceback | 不變 |
| 僅測試：載入後切換 catalog | 15 個文字停在載入時的語言 | 跟著切換（D1–D4） |

## 各檔案的設計

- `client/i18n.py`（4 個空白）：D1。
- `client/about.py`（tab）：D2。第 4–8 行不動。
- `client/dictionaries/entries.py`（tab）：D3。
- `client/dictionaries/entry_list_model.py`（tab）、`client/dialog.py`（tab）：D3 的讀取端。
- `client/settings/dialogs.py`（4 個空白）：D4。
- `client/dual_view/html.py`（tab）：D6 的範本。
- `client/gui.py`（tab）：`on_about`（D2）、`_render_dual_view_for_open_document`（D6）、`BACKUP_FAILED` 分支（D7）；從 `i18n` 匯入 `html_language_tag`。
- `client/documents/formats.py`（4 個空白）：`_write_html`（D6）。
- Catalog：`client/locales/dotexpress.pot`、`client/locales/zh_TW/LC_MESSAGES/dotexpress.po`、`.mo`（D8）。
- 測試：見「測試計畫」；`tests/test_translation_golden.py` 加上 `lang="en"`（D6）。
- 不修改：`config.py`、`client/braille/`（全部）、`ui/message_box.py`、`ui/conversion_presenter.py`、三個 fixture、HANDOFF 第 5 節列出的每個檔案。

## 維持不變

- 程式在 zh_TW 下的每個文字、標籤、標題、無障礙描述與對話框，除了 HTML 的 `lang` 屬性與 `BACKUP_FAILED` 的原因。
- `lang` 以外的 HTML：相同的標記、樣式、儲存格與空白頁句子。
- `config.json` 與 `config.json.bak` 的處理（F-8 D11、F-12 D6）、log 行、每次執行只顯示一次的規則。
- 點字轉換語言（`config.py` 的 `get_lang`／`set_lang`）。
- `translation_golden.json`（`e67d95a1...`）、`dictionary_entries_trace.json`（`f493da52...`，其中 387 個 `一般` 儲存格仍在 zh_TW 下產生）與 `translation_liblouis_golden.json`（`8dc8572e...`）。

## 使用者可見字串

| # | msgid | zh_TW msgstr（建議） | 位置 |
| --- | --- | --- | --- |
| N1 | `The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. The file or the backup copy may be in use by another program, or you may not have permission to write to the folder. Close the other program and try again.` | `檔案已損壞，而且在取代它之前無法先備份為「{backup}」。檔案或備份檔可能正被其他程式使用，或你沒有該資料夾的寫入權限。請關閉其他程式後再試一次。` | D7，存取錯誤 |
| N2 | `The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Check that the disk has free space and that you can write to the folder.` | `檔案已損壞，而且在取代它之前無法先備份為「{backup}」。請確認磁碟還有可用空間，且你有該資料夾的寫入權限。` | D7，其他錯誤 |

不再使用（實作時直接消失，不是 obsolete；修正第 3 點）：F-12 字串 22，`The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Details: {error}`。

msgid：407 + 2 - 1 = **408**。用詞沿用 F-12 的句子：第一句是字串 22 去掉 `詳細資訊`，後面沿用 F-12 兩則寫入失敗的文字（`無法寫入檔案。檔案可能正被其他程式使用，或你沒有寫入權限。請關閉其他程式後再試一次。`、`...請確認磁碟還有可用空間，且你有該資料夾的寫入權限。`）；「備份檔」比照「點字檔」「文字檔」。

## 無障礙（NVDA）

- 有了 `lang="zh-TW"`，開啟自動語言切換的螢幕報讀軟體會用中文語音念雙視檢視視窗與匯出的檔案（第 4 項的理由，見 F-12「範圍外」）。頁面中的英文字也會用這個語音念（簡單版，U2）。
- 備份失敗框不再念出帶亂數暫存檔名的路徑與 `[WinError 5]`；結尾是該怎麼做。
- 第 7 項不改變螢幕報讀軟體聽到的任何內容：設定面板的無障礙名稱與描述是同樣的字串，只是改在讀取時翻譯。
- 手動項目 145（使用者）確認語音。

## 測試計畫

TDD，標明處先紅燈。縮排依各檔案。會切換 catalog 的測試以 `addCleanup(i18n.set_language, previous)` 還原，避免後面的測試（例如 fixture 中是中文標籤的字典操作紀錄）在英文下執行。會讓程式寫 log 的測試使用 `assertLogs` 或隔離 logger；不寫進 `client/log/`。只用暫存資料夾。

### A. `i18n`（`tests/test_i18n.py`）

1. `current_language()` 是 `"zh_TW"`；`html_language_tag()` 是 `"zh-TW"`；`html_language_tag("en")` 是 `"en"`。紅燈（函式不存在）。
2. `set_language("en")`（沒有 `en` catalog）：`current_language()` 是 `"en"`，`i18n._("General")` 是 `"General"`；`set_language("zh_TW")` 後回到 `"一般"`。紅燈。
3. 在切換前就載入的使用端也跟著切換：`set_language("en")` 之後，`dialog._("General")`（任何寫了 `from i18n import _` 的模組）得到 `"General"`。紅燈（綁定在舊 catalog 上）。
4. `set_language("zh_TW", localedir=<空資料夾>)`：`current_language()` 是 `"en"`（O2）。
5. `_("")` 是 `""`。紅燈（標頭）。
6. 既有測試維持：`LOCALE_LANGUAGES == ("zh_TW",)`、`load_translation()` 是 `GNUTranslations`、環境變數測試（子程序印出 `一般`）、重複設定的守門測試。
7. `SharedSetupConsumerTest`：`about.py` 匯入 `{"N_", "_"}`，`dictionaries/entries.py` `{"N_", "_"}`，`settings/dialogs.py` `{"N_", "_"}`，`gui.py` `{"_", "html_language_tag", "resource_path"}`。

### B. 改過的地方在載入後切換語言時會跟著變（目前紅燈：文字在載入時就固定了）

1. `about.about_message()`：zh_TW 下含 `版本：1.2 (1.2)` 與 `版權所有 (C) 2025-2026 DotExpress 貢獻者`，且等於目前 `about.aboutMessage` 的文字（字面值）；`set_language("en")` 後含 `Version: 1.2 (1.2)` 與 `Copyright (C) 2025-2026 DotExpress Contributors`。`gui.on_about` 傳入 `about.about_message()`（`test_gui_document_flows.py:5021` 的既有測試從 `about.aboutMessage` 改過來）。
2. `entry_type_label`／`entry_type_choices`：中文 `一般`、`注音`、`Unicode 點字`；英文 `General`、`Bopomofo`、`Unicode Braille`；未知的鍵兩者都原樣傳回。
3. `EntryListModel.cell_text(row, 2)` 跟著切換；`AddSymbolDialog` 的選單項目（以既有 dialog 測試的建立方式）跟著切換。
4. 設定：三個面板各自的 `SettingsPanelAccessible(panel).GetDescription(0)`，以及 `SettingsPanel.__init__` 設定的標籤與名稱；`_build_layout` 的分類清單項目；`_format_title(TranslationSettingsPanel.title)`（`DotExpress 設定：轉譯`／`DotExpress Settings: Translation`）；`_collect` 驗證錯誤框的標題（`DotExpress 設定`／`DotExpress Settings`）。每項都測中文與英文。
5. 基底 `title = ""` 的 `SettingsPanel`：標籤與名稱是 `""`，描述是 `""`（不是 catalog 標頭）。
6. 以恆等函式 patch `settings.dialogs._` 的既有設定測試，維持原本的預期（它們本來就預期英文），標題改經 `_` 讀取之處視需要調整；`test_title_format_uses_localizable_template` 維持綠燈（不是 msgid 的範本原樣傳回）。

### C. 守門測試（`tests/test_i18n.py`）

1. D5 的 AST 守門：除了 `braille/tables/__tables.py`，client 中沒有載入時的翻譯呼叫。目前紅燈（15 處）。
2. D5 的子程序載入探針（視記憶體決定是否採用）：沒有記錄到呼叫。目前紅燈（15 次）。
3. AST：`ENTRY_TYPE_OPTIONS` 的值、各面板的 `title`／`panel_description`、`base_title`、`title_template`、`about.longName`、`about.description` 都是 `N_` 呼叫。
4. catalog 測試 `test_the_catalog_holds_exactly_the_marked_strings` 在每一步之後都維持綠燈。

### D. HTML `lang`（`tests/test_dual_view_html.py`、`tests/test_document_formats.py`、`tests/test_gui_document_flows.py`）

1. `render_dual_view_html(model, lang="zh-TW")` 以 `<!doctype html>\n<html lang="zh-TW">` 開頭；含 `"` 的值會被 escape；不給 `lang` 會丟出 `TypeError`。
2. `formats._write_html` 對有資料與沒有資料的文件（後者含中文空白頁句子）都寫出 `<html lang="zh-TW">`；`set_language("en")` 後寫 `lang="en"`。中文的部分紅燈。
3. `BrailleFrame._render_dual_view_for_open_document` 傳回 `lang="zh-TW"`（切換後是 `en`）。紅燈。
4. 以 HTML 格式全部匯出：每個檔案都是 `lang="zh-TW"`。
5. `test_translation_golden` 帶 `lang="en"` 維持綠燈；fixture 的 sha256 不變。
6. 把匯出結果與 `render_dual_view_html(...)` 比較的既有 frame 測試（`test_gui_document_flows.py:1622-1684`）在預期的 render 中傳入 `lang="zh-TW"`。

### E. 備份訊息（`tests/test_gui_document_flows.py`、`tests/test_i18n.py`、`tests/test_config.py`）

1. `BACKUP_FAILED` 搭配 F-12 review 測試中的每種存取錯誤（`PermissionError`、`winerror` 5、32、33、`errno` `EACCES`）呼叫 `_report_settings_save_problem`：原因是帶備份路徑的 N1。紅燈（目前是 `詳細資訊：...`）。
2. 搭配 `OSError(errno.ENOSPC, ..., <暫存檔名>)`、`OSError(errno.EIO, ...)`、`IsADirectoryError` 與非 `OSError`（`ValueError("x")`）：N2。紅燈。
3. 所有情況下，對話框文字都不含 `str(error)`、暫存檔名、`WinError` 或 `詳細資訊`。
4. `test_each_kind_of_problem_gives_its_reason`（`:5283`）：`BACKUP_FAILED` 那一列預期 N1（它的錯誤是 `OSError(13, ...)`，屬於存取錯誤）。第 1–3 點的情況以 `BACKUP_FAILED` 列加進 `test_only_an_access_error_says_the_file_is_in_use_or_not_permitted`（`:5307`），該測試已檢查暫存檔名 `k3j9x2` 不出現。
5. `test_config`：`config.json` 損壞且 `config.json.bak` 是資料夾時，仍傳回 `BACKUP_FAILED`，並以 ERROR 記錄 `Failed to save config file <path>`；該筆紀錄的 `exc_info` 含有錯誤（原文寫進 log）。
6. Catalog：N1、N2 的 msgstr；`test_settings_not_saved_strings_are_translated` 拿掉字串 22，改查 N1、N2。

### Mutation 檢查（plan；每個都必須被抓到）

1. `i18n._` 改回綁定在載入時 catalog 上的方法；
2. `set_language` 沒有記錄語言；
3. catalog 不存在時 `current_language` 傳回 `zh_TW`；
4. `html_language_tag` 保留 `_`；
5. `_("")` 傳回標頭；
6. `about_message` 又在載入時產生（模組常數）；
7. `entry_type_label` 傳回未翻譯的 msgid；
8. `cell_text` 直接讀 `ENTRY_TYPE_LABELS`；
9. `AddSymbolDialog` 的選項用 msgid；
10. 面板的 `title` 又在類別層級翻譯；
11. `GetDescription` 沒有翻譯；
12. `_format_title` 沒有翻譯分類名稱；
13. `_collect` 的標題沒有翻譯；
14. HTML 範本又寫 `lang="en"`；
15. `_write_html` 的 `lang` 不是來自 `html_language_tag()`（寫死 `zh-TW`，由切換成 en 的測試抓到）；
16. frame 的 render 沒有帶 tag；
17. N1 與 N2 對調；
18. 原因後面又接上 `{error}`；
19. 拿掉存取錯誤的判斷（一律 N2）；
20. AST 守門的允許清單放寬成整個 `braille/`。

### 數量

約 30 個新測試、3 處修改預期（A 6、B 6、C 4、D 6、E 6，加上使用端守門）。確切的 `Ran` 由 plan 決定；F-13 merge 之前，Windows 上為 `OK (skipped=6)`。

## 遷移步驟（每一步一個綠燈 commit，先紅燈）

1. `refactor: let i18n translate through the active catalog and report the interface language (F-14)`：D1；測試 A。catalog 不動。
2. `refactor: translate the About text, entry types and settings titles when they are shown (F-14, F-12 review M-7)`：D2–D5；測試 B、C、A7。重新產生範本：msgid 集合不變（D8），`.po` 只改 `#:` 行，`.mo` 位元組不變。
3. `fix: declare the interface language in dual view and exported HTML (F-14)`：D6；測試 D。catalog 不動。
4. `fix: explain a failed settings backup without the system's text (F-14)`：D7、D8；字串 N1、N2；測試 E。

每個會讓 msgid 上方行數移動的步驟都重新產生範本，最後不留過時的 `#:` 參照。commit 只 stage 明確的路徑，結尾不加 `Co-Authored-By`（HANDOFF 第 5 節），不 push。

## 驗收條件

在 Windows 上從 `client/` 以 `$PY` 執行，執行環境依 F-3 plan 的 Task 0 複製（絕不 stage）；每次重的工作之前，可用記憶體至少 600 MB。

1. 完整測試：沒有 failure、沒有 error；`Ran` 與 plan 所寫一致。
2. 重點測試：`$PY -B -X utf8 -m unittest tests.test_i18n tests.test_dual_view_html tests.test_document_formats tests.test_settings_dialogs tests.test_settings_options tests.test_dictionary_entries_dialog tests.test_config tests.test_translation_golden tests.test_gui_document_flows -v` 通過。
3. D5 的 AST 掃描只列出 `braille/tables/__tables.py`；載入探針沒有記錄到呼叫。
4. Catalog：408 個 msgid，全部已翻譯，0 fuzzy（`msgfmt --check --statistics`）；msgid 集合等於 `a147fed` 的集合加 N1、N2、減字串 22；`POT-Creation-Date` 不變；obsolete 條目 26（字串 22 直接消失，不是 obsolete；修正第 3、12 點）。
5. 三個 fixture 的 sha256 不變。
6. 程式資料未被動到（主 checkout 的 `client/dictionary/`、`client/workspace/`、`client/config.json`、`client/log/` 前後 sha256 相同）；worktree 中不出現這些。
7. `git diff main --stat` 只動到「各檔案的設計」列出的檔案、測試，以及 spec、plan 與 history 檔；`client/braille/tables/__init__.py` 位元組完全相同（CRLF），`__tables.py` 未改。
8. Mutation 檢查。
9. 下面的打包版 GUI 驗證，結果放在實作的 history 資料夾。

## Windows 驗證（打包版）

流程同 F-11、F-12：把主 checkout 的 `client\.venv\Scripts` 放在 `PATH` 最前面，執行 `scripts\build-dotexpress.bat`；改過的模組來自 worktree（`PYZ-00.toc`）；新版放在 `D:\dxtest\N-f14`，舊版是 `D:\dxtest\N-f12b`。每個項目在新的 `D:\dxtest\auto<項目>-f14` 資料夾執行（舊版：`auto<項目>-f12b-f14`），經由 `auto/safe_run.py`（只在 DotExpress 位於前景時送按鍵；log 不記錄其他程式的視窗名稱）；只結束這些資料夾底下的程序。檔案由腳本在啟動前準備；**任何腳本都不讀寫剪貼簿**；文字以 `set_edit_text` 或按鍵輸入。絕不真的登出或關機。一次只跑一項重的工作，每次開始前至少 600 MB 可用記憶體。

**修正**項目兩個 build 都跑；**回歸**項目只在 `N-f14` 跑，結果不符預期時才補跑 `N-f12b`。

| # | 類別 | 步驟 | `N-f14` 的預期 | `N-f12b` |
| --- | --- | --- | --- | --- |
| 141 | 修正 | (a) 文件 `alpha` 內容 `中文 abc`，轉換，檔案 > 匯出 > 雙視檢視 HTML 到空資料夾。(b) 預設文件 `new`（沒有轉換資料），匯出 > 雙視檢視 HTML。(c) 兩份已轉換文件，全部匯出，雙視檢視 HTML。讀每個檔案的前兩行。 | 每個檔案：`<!doctype html>`，接著 `<html lang="zh-TW">`；(b) 另含 `此文件沒有可顯示的轉換資料。` | `<html lang="en">` |
| 142 | 修正 | 啟動前 `config.json` = `{` 且 `config.json.bak` 是資料夾（F-12 項目 114 (b)）；設定：改轉換寬度，按「套用」，再按「確定」 | 按「套用」後出現一個框，標題 `設定未儲存`，主文字是帶 `<d>\config.json` 的字串 21，內容是帶 `<d>\config.json.bak` 的 N1，不含 `WinError`、`存取被拒`、`.tmp` 或 `詳細資訊`；擁有者是設定對話框；按「確定」後沒有框；`config.json` 仍是 `{`；`log\config.log` 有一筆 ERROR `Failed to save config file`，traceback 含 `WinError 5` | 內容 `... 詳細資訊：[WinError 5] 存取被拒。: '...\.config.json.bak.<rnd>.tmp' -> ...` |
| 143 | 回歸 | (a) 說明 > 關於：讀整段文字。(b) 設定：讀標題、分類清單，再按兩次 Ctrl+Tab，每次讀標題；讀每個面板的無障礙描述（UIA `LegacyIAccessible.Description`）。(c) 字典管理 > 編輯 `default`（含三種類型的列）：讀類型欄；新增：讀類型選單的項目；取消。 | (a) 開頭是 `DotExpress (DotExpress)`，接著 `版本：1.2 (1.2)`、`網址：https://coseeing.org`、`版權所有 (C) 2025-2026 DotExpress 貢獻者`；標題 `關於 DotExpress`。(b) `DotExpress 設定：轉譯`；`轉譯`、`轉譯表`、`檢視`；`DotExpress 設定：轉譯表`、`DotExpress 設定：檢視`；描述依序為 `轉譯輸出模式、寬度與字典選項`、`不同語言的轉譯表對應`、`主視窗輸入與輸出區的字型、字體大小與配色`。(c) 欄位與選單中都是 `一般`、`注音`、`Unicode 點字` | （結果不符時才跑） |
| 144 | 回歸 | (a) 對已轉換文件與沒有資料的文件執行轉譯 > 雙視檢視，`PATH` 最前面放替身瀏覽器：讀程式寫到 `<d>\dual_view` 的頁面檔（修正第 12 點；原步驟的程式內網頁檢視沒有任何路徑會開啟）。(b) `config.json` 正常：設定中改寬度，按「確定」。 | (a) 儲存格的文字；`new` 顯示 `此文件沒有可顯示的轉換資料。`；沒有錯誤框。(b) 沒有框；`config.json` 已更新 | （結果不符時才跑） |

**留給使用者的手動項目（項目 145，NVDA；agent 絕不代為勾選）：** 用 `N-f14`，開啟 NVDA 並啟用自動語言切換：對已轉換的中文文件執行轉譯 > 雙視檢視（會在瀏覽器開啟；修正第 12 點），用 NVDA 閱讀；再用瀏覽器開啟項目 141 匯出的雙視檢視 HTML 檔。中文是否用中文語音念（`N-f12b` 可能用英文語音）？接著打開項目 142 的對話框聆聽：是否念出完整文字，且沒有暫存檔名？

## 風險

- **測試中的全域 catalog**（中）。切換語言後沒有還原的測試，會讓後面的測試看到英文（字典操作紀錄的 fixture 是中文標籤）。每次切換都透過 `addCleanup`；plan 以預設順序與一個 shuffle seed 跑完整測試。
- **`_` 改成函式**（低）。每個呼叫處本來就只傳一個位置參數字串；patch 使用端 `_` 的測試不受影響。比較 `module._` 與 `i18n._translation.gettext` 的測試會壞，但沒有這樣的測試（grep）。
- **之後又加入隱藏的載入時翻譯**（低）。D5 的守門測試會失敗。
- **golden 的 render**（低）。只改 `test_translation_golden.py` 的呼叫；不重新產生 fixture，並檢查它的 sha256（驗收條件 5）。
- **與 F-13 合併 catalog**（中，機械性）。重新產生，不手動合併（見「與 F-13 的關係」）。
- **使用者尚未 commit 的 `about.py`**（只在 merge 時會擋住）。見「Merge 前提」。
- **資料夾情況的 `is_access_error`**（低）。在 Windows 上，名為 `config.json.bak` 的資料夾會讓 `os.replace` 產生 `[WinError 5]`，屬於存取錯誤，所以項目 142 顯示 N1；N2 由單元測試涵蓋（這台機器上無法安全地製造磁碟已滿或 I/O 錯誤）。

## 待決問題

**使用者已決定（2026-10-14）：** U1–U4。

**由協調者採用建議預設；使用者可在 merge 前推翻：**

- **O1.** `i18n` 新增 `set_language()` 作為將來切換的接口；F-14 中只有載入與測試會呼叫（D1）。使用者看不到。
- **O2.** 要求的 catalog 不存在時，`current_language()` 回報 `en`（這時使用者看到英文），讓 HTML 的 `lang` 與顯示的文字一致（D1）。打包版與原始碼都附帶 catalog，所以程式回報 `zh_TW`。
- **O3.** `_("")` 傳回 `""` 而非 catalog 標頭（D1）。只有在空字串原本會顯示標頭的地方才看得出差異（目前沒有已知路徑）。
- **O4.** `render_dual_view_html` 的 `lang` 必填；golden 測試明確傳入 `"en"`；fixture 不動（D6）。
- **O5.** `about.aboutMessage` 與 `about.copyright` 改成函式 `about_message()` 與 `copyright_text()`；`longName` 與 `description` 存 msgid（D2）。
- **O6.** `__tables.py` 的點字表名稱維持原狀，記錄下來留給切換語言的任務（現況）。
- **O7.** BACKUP_FAILED 的原因保留備份路徑 `{backup}`，並沿用 F-12 的 `is_access_error` 區分（D7）。
- **O8.** 沒有 GUI 項目去製造 N2 的情況；由單元測試涵蓋（風險）。

**給使用者的問題**（不阻擋；本 spec 以建議選項撰寫）：

- **Q1. N1 與 N2 的措辭**（上表）。建議：照寫。N1 較短的替代寫法：`檔案已損壞，而且在取代它之前無法先備份為「{backup}」。請關閉可能正在使用這些檔案的程式，並確認你有該資料夾的寫入權限，然後再試一次。` 修改只需改 catalog 的一行。
- **Q2. Merge 前提。** 在 F-14 merge 之前，於主 checkout commit `about.py` 的版本號修改；或同意協調者在 merge 前後 stash 並還原它。

## 本 spec 引入的使用者可見預設（使用者未決定）

1. **N1 與 N2 的文字**（Q1）。
2. **`lang` 的值是 `zh-TW`**，所有雙視檢視頁面都是，包括視窗（使用者決定「依介面語言」；確切的 tag 依 BCP 47）。
3. **備份失敗框仍寫出 `.bak` 路徑**，存取錯誤時說「檔案或備份檔」（O7）。

## 範圍外／後續

- **切換語言的功能本身**（U1）：選單或設定、保存選擇、重建開啟中的視窗與選單、`__tables.py` 的點字表名稱（現況）。
- 雙視檢視 HTML 中英文的**逐段 `lang`**（U2）。
- **F-13 的項目** 1、2、3、5、6。
- 使用者延後（`task.md`「延後的項目」，2026-10-14，「不修」）：匯出 `.tmp` 重試、表頭不分大小寫、從別份文件關閉時遺失的 case (b) 存檔失敗結果（F-9 M-5）、損壞的 `config.json` 被靜默取代（F-12 Q2）、刪除兩筆相同詞條之一後的選取（F-11 M-4）。
- F-10（UEB 斷行、`$`）。
- **雙視檢視視窗的 dead code**（F-14 review M-2）：`gui._show_dual_view`、`_create_dual_view_frame`、`ui/dual_view.DualViewFrame` 與它們的兩個單元測試沒有任何路徑會呼叫；之後另開任務移除。
