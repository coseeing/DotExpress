# Interface-Language Preparation, HTML `lang` and the Settings Backup Message (F-14) Design

## Goal

Task F-14 is the "i18n" task of `docs/superpowers/history/2026-10-14-01-handoff/HANDOFF.md` section 1. It covers three items of `task.md` section 五 "下一輪要修" (numbered by their order there):

- **Item 7.** Prepare for switching the interface language inside the app (F-12 review M-7): no interface text is translated when a module is imported any more; `i18n` can say which interface language is active.
- **Item 4.** The Dual View HTML and the exported HTML declare the interface language (`lang="zh-TW"`) instead of `lang="en"`.
- **Item 8.** The "settings not saved" box for a failed `config.json.bak` backup explains the cause in words, without the operating system's text and the temporary file name.

Item 7 comes first: item 4 takes its `lang` from the "current interface language" that item 7 adds.

Decided by the user (2026-10-14), `task.md` section 五 "下一輪要修" and "延後的項目"; not asked again here:

- **U1 (item 7).** "全面找出模組載入時就呼叫 `_()` 的地方（已知 `about.py`、`dictionaries/entries.py` 的類型名稱、`settings/dialogs.py`，實作時要 grep 全部），改成載入時只用 `N_()` 標記、顯示時才翻譯（或改成函式）。介面語言改由 `i18n` 提供「目前語言」的查詢，雙視窗 HTML 的 `lang` 也從這裡取得。**不含**切換語言的功能本身（選單、設定、重建畫面）；目前介面語言仍固定 `zh_TW`，使用者看到的行為不變。"
- **U2 (item 4).** "雙視窗／匯出 HTML 的 `lang` 依 DotExpress 介面語言寫入（簡單版）：`dual_view/html.py` 目前寫死 `<html lang="en">`；改成依介面語言（如 `zh_TW` → `zh-TW`）。不做逐段標示英文的完整版。"
- **U3 (item 8).** "保留 `config.json.bak` 的備份行為（只寫不讀，損壞的 `config.json` 在第一次存設定前複製過去）。`BACKUP_FAILED` 的「設定未儲存」訊息不再附系統原文與暫存檔名，改照 F-12 寫入失敗的做法依錯誤類型顯示翻譯過的說明（權限／被占用 vs 其他），新增 1–2 條字串；原文照舊寫進 log。"
- **U4.** Items 1, 2, 3, 5 and 6 of the same list are F-13 (see "Relation to F-13"). HANDOFF section 4: `config.py`'s `set_lang` is the braille conversion language, not the interface language.

After this task:

- Every interface text that used to be translated at import is translated when it is shown. Switching the active catalog after the import (only tests do it in F-14) changes those texts.
- `i18n.current_language()` returns `"zh_TW"`, `i18n.html_language_tag()` returns `"zh-TW"`.
- The Dual View window, its browser copy and every exported Dual View HTML file (single export, Export All, the page without conversion data) start with `<html lang="zh-TW">`.
- A failed backup before the first settings save shows one of two translated reasons (access problem, or anything else) and names the backup file; the operating system's text stays in `config.log` only.
- Nothing else the user sees changes: every text, title, label and box of item 7 is identical in zh_TW.

New user-visible strings: **2** msgids, and 1 msgid becomes unused (F-12's string 22). The msgid count goes from **407** to **408**. Item 7 and item 4 add and remove no msgid.

Non-goals: the language switch itself (menu, setting, rebuilding windows); per-segment `lang` for English text in the HTML; any change to `braille/tables/__tables.py`; F-13's items.

## Corrected after planning (F-14, 2026-10-14)

Re-checked against the code of `main` `a147fed`: the inventory (15 import-time calls in `about.py`, `dictionaries/entries.py`, `settings/dialogs.py`; 198 in `braille/tables/__tables.py`), every decision D1-D8, the behaviour table and the test plan hold, with the refinements below. The plan's (`docs/superpowers/plans/2026-10-14-f14-i18n-prep.md`) section "Spec Corrections and Refinements" holds the same list.

1. **Baseline and counts.** On `a147fed` (`HEAD:client` `a967d8d4`) the suite gives `Ran 1632`, `OK (skipped=6)`; the catalogs hold 407 msgids and 26 obsolete entries. F-14 adds 20 tests and changes 7: `Ran 1637` after step 1 (5 new), `1648` after step 2 (11 new; 2 changed: the About test, `test_uses_title_for_accessible_label`; the consumer guard's sets), `1651` after step 3 (3 new; the render calls of 3 export tests, of `test_dual_view_html` and of the golden test), `1652` after step 4 (1 new; `test_each_kind_of_problem_gives_its_reason`, the strings test, the `test_config` backup test). The spec estimated about 30.
2. **Catalogs.** Step 1 touches no catalog (`i18n.py` holds no msgid). Steps 2-4 move lines above msgids, so each regenerates the template and the `.po`; no `#:` reference is stale after any commit, and no separate `chore:` commit is needed. In step 2 `msgmerge` also re-wraps one msgstr that F-12's fix commit wrote on one line (the "file cannot be written" reason; F-13 sees the same). The `.mo` is byte-identical to `a147fed`'s after steps 2 and 3.
3. **D8 as built.** `msgmerge` pairs N1 with F-12's "file cannot be written (access)" text and N2 with string 22, both `#, fuzzy` (406 translated, 2 fuzzy before the fix). A throwaway `set_msgstr.py` writes the two msgstr values of the table (one line each; `msgmerge` keeps them so, and a second `msgmerge` changes nothing) and clears the flags: 408 translated, 0 fuzzy. Because string 22 became N2's fuzzy base, it does **not** become obsolete: it is gone, and the obsolete entries stay **26** (the spec said 27). The msgid set is `a147fed`'s plus N1 and N2 minus string 22.
4. **The user's decisions (2026-10-14).** Q1: N1 uses the longer wording exactly as in the table (`檔案已損壞，而且在取代它之前無法先備份為「{backup}」。檔案或備份檔可能正被其他程式使用，或你沒有該資料夾的寫入權限。請關閉其他程式後再試一次。`), N2 as in the table. Q2: the user committed the `about.py` version bump on `main` (`7db6538`, `2053646`: `version` and `version_detailed` = `"1.8"`), so "Merge precondition" no longer needs a stash. F-14 leaves `about.py` lines 4-8 (`"1.2"` on this branch) untouched; `git merge-tree` of the branch with `main` `2053646` gives no conflict, and with F-13's branch only the two catalogs conflict, which are regenerated, not hand-merged (as "Relation to F-13" says).
5. **B1 as built.** The About test reads the version from `about.version` and `about.version_detailed` instead of the literal `1.2 (1.2)`, so it stays green after `main`'s 1.8 is merged; the rest of the zh_TW text is a literal. GUI item 143 (a) still expects `版本：1.2 (1.2)` on `N-f14` (built from this branch).
6. **D5 as built.** The AST guard asserts that the files with import-time translation calls are exactly `["braille/tables/__tables.py"]` (the reason is written beside the constant), rather than filtering through an allow-list; its scanner is tested on a snippet with each kind of call (module level, class body, default argument, decorator, lambda default; not function or lambda bodies; attribute calls such as `translations.gettext` count). It skips the generated `braille/liblouis/` like the catalog test. The import probe is kept: one subprocess (`-B`) imports every client module but `main.py` with `i18n._` replaced by a recorder (about 5 s); it is skipped where wx is not installed.
7. **D3 and D4 tests as built.** No wx stub builds `AddSymbolDialog`, so its test runs the real `__init__` with the module's `wx` replaced by a `MagicMock` and reads the `choices` passed to `wx.Choice`. The settings tests build the three panels with the existing `build_panel`, and the category list with `_build_layout` on a dialog made without its constructor. `test_uses_title_for_accessible_label` now expects `轉譯` (its title is a msgid since D4).
8. **E tests as built.** One table test with ten errors: six access errors (`PermissionError`; the `[WinError 5]` `os.replace` raises, with both names; winerror 32; winerror 33; a bare winerror 5; errno `EACCES`) give N1, four others (`ENOSPC`, `EIO`, `IsADirectoryError`, `ValueError`) give N2; none of `k3j9x2`, `.tmp`, `WinError`, `Errno`, `詳細資訊` is in the box. `test_config`'s backup test also checks that the ERROR record's `exc_info` is the problem's error.
9. **Mutation check: 20 mutants**, the spec's list with one change: mutant 20 is "the guard skipping all of `braille/`" (the guard has no allow-list to widen; skipping the folder hides `__tables.py`, which the guard expects to find).
10. **Commit subjects** end in `(F-14)`; step 2's body names F-12 review M-7.
11. **Windows items.** 141 and 142 are fix items (both builds), 143 and 144 regression items (`N-f14` only). 142 reruns F-12's `item114.py` case (b) unchanged. The GUI scripts are in `docs/superpowers/history/2026-10-14-03-f14-i18n-prep/auto/`.

## Relation to F-13

F-13 (behaviour and NVDA, worktree `D:\workspace\DotExpress-f13`, branch `fix/f13-behavior-nvda`) runs in parallel from the same `main` `a147fed` and will probably merge first. F-14's plan then merges `main` into its branch, re-takes the line numbers below (they are orientation only; code is named by function) and re-runs the full suite.

Likely file overlaps:

| File | F-13 (expected) | F-14 |
| --- | --- | --- |
| `client/gui.py` | `_load_startup_documents` (`:244`), `BrailleFrame.__init__`, `BrailleApp.OnInit`, `OnExit` (`:1302-1311`) | import line `:9`; `_render_dual_view_for_open_document` (`:329-335`); the `BACKUP_FAILED` branch of `_report_settings_save_problem` (`:474-477`); `on_about` (`:546-547`) |
| `client/dialog.py` | `_confirm_hidden_rows`, `_hidden_row_line` (`:609` on), the two F-11 confirmation boxes | imports `:9-11`; the type choice in `AddSymbolDialog.__init__` (`:110`) |
| `client/dictionaries/entry_list_model.py` | possibly the hidden-row values (item 6) | import `:46`; `cell_text` (`:165`) |
| `client/ui/message_box.py`, `client/ui/conversion_presenter.py` | yes | not touched |
| `client/locales/dotexpress.pot`, `.po`, `.mo` | `#:` references move with `gui.py` and `dialog.py`; maybe strings | `#:` references; 2 strings added, 1 obsolete |
| tests: `test_gui_document_flows.py`, `test_i18n.py`, `test_dictionary_entries_dialog.py`, dialog tests | new tests | new and changed tests |

- Different functions in each shared file, so textual conflicts should be small; tests appended at the same place keep both sides.
- Catalogs are never hand-merged: after merging `main`, the plan regenerates `.pot` (`scripts\generate-pot.bat`), runs `msgmerge`, re-checks the two F-14 msgstr values and the fuzzy flags, and recompiles the `.mo`. The count is then `main`'s count + 1.
- GUI items: F-13 uses 121-140, F-14 141-145.

## Merge precondition (needs the user)

The main checkout `D:\workspace\DotExpress` has an uncommitted user change in `client/about.py` (`version = "1.8"`, line 7). F-14 changes `client/about.py` (D2, lines 1 and 10-41; line 7 untouched), so `git merge` in the main checkout refuses to run while that change is uncommitted. The orchestrator must not stash or overwrite it on its own. Before the merge the user either commits the version bump (the merge then joins both changes without conflict, the hunks are apart) or allows a `git stash push client/about.py` / `git stash pop` around the merge. The plan and the review do not need the main checkout's `about.py`.

## Current State (verified 2026-10-14 on `main` `a147fed`, worktree `D:\workspace\DotExpress-f14`, `HEAD:client` `a967d8d4cea147cf25ccc0f490c8f94e41e711ce`)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`. No test suite was run for this spec; the baseline is HANDOFF section 2: `Ran 1632`, `OK (skipped=6)`; the catalog holds 407 msgids (408 `msgid` lines in the `.po`, header included), all translated, 0 fuzzy, 26 obsolete entries. Probes ran from the worktree's `client/` with scripts in the session scratchpad (`f14spec\scan.py`, `scan2.py`, `probe_import.py`), not committed.

### How translation works today (`client/i18n.py`)

- `:44` `_translation = load_translation()` loads the zh_TW catalog once (`LOCALE_LANGUAGES = ("zh_TW",)`, `:16`; `fallback=True` gives a pass-through `NullTranslations` when the catalog is missing).
- `:45` `_ = _translation.gettext`: a bound method of that one catalog object. Every consumer does `from i18n import _` and keeps that bound method in its own global. Replacing the catalog later would reach nobody.
- `N_` (`:48-50`) only marks a msgid for `xgettext` (`scripts\generate-pot.bat`: `--keyword=_ --keyword=N_`).
- There is no notion of "the current interface language": `LOCALE_LANGUAGES` is the only trace of it.
- `gettext("")` returns the catalog header (the `Project-Id-Version: ...` block). No code passes `""` on purpose today, but `_(str(error))` (`settings/dialogs.py:158`) would show the header for a `ValueError("")`.

### Inventory: `_()` executed at import time

Two scans:

1. **AST scan** (`scan.py`) of every `.py` under `client/` except `tests/`, `.venv/`, `build/`, `dist/`: every call of `_`, `gettext`, `ngettext`, `pgettext` or `GetTranslation` outside a function body, that is at module level, in a class body, in a default argument or in a decorator. `scan2.py` lists the module-level calls of other functions (`get_importable_formats()`, `build_language_blocks(...)`, `get_logger(...)` and the like); none of them translates.
2. **Import probe** (`probe_import.py`): replaces `i18n._` with a recorder before anything else is imported, then imports all 99 client modules (all but `main.py`, which runs a demo; no window is created). It recorded exactly the 15 calls below and no other (none from an indirect call).

| # | Where (`a147fed`) | Code | msgid | Read at |
| --- | --- | --- | --- | --- |
| I1 | `about.py:10` | `longName = _("DotExpress")` | `DotExpress` | `about.py:35` (format of I4) |
| I2 | `about.py:11` | `description = _("A text-to-braille ...")` | `A text-to-braille translation tool that converts plain text into fixed-width braille, ...` | nowhere (unused) |
| I3 | `about.py:13-15` | `copyright = _(...).format(years=copyrightYears)` | `Copyright (C) {years} DotExpress Contributors` | `about.py:40` (format of I4) |
| I4 | `about.py:16-41` | `aboutMessage = _("""{longName} ({name}) ...""").format(...)` | the About text | `gui.py:547` `on_about` |
| I5 | `dictionaries/entries.py:15` | `("General", _("General"))` in `ENTRY_TYPE_OPTIONS` | `General` | `dialog.py:110` (type choice), `entry_list_model.py:165` via `ENTRY_TYPE_LABELS` (`entries.py:19`) |
| I6 | `dictionaries/entries.py:16` | `("Bopomofo", _("Bopomofo"))` | `Bopomofo` | as I5 |
| I7 | `dictionaries/entries.py:17` | `("Braille", _("Unicode Braille"))` | `Unicode Braille` | as I5 |
| I8 | `settings/dialogs.py:357` | `TranslationSettingsPanel.title = _("Translation")` | `Translation` | `SettingsPanel.__init__` (`:54-55` label, name), the category list (`:270`), the dialog title (`:677`, `:685`) |
| I9 | `settings/dialogs.py:358` | `TranslationSettingsPanel.panel_description = _(...)` | `Translation output mode, width, and dictionary options` | `SettingsPanelAccessible.GetDescription` (`:42-43`) |
| I10 | `settings/dialogs.py:438` | `TranslationTablesPanel.title` | `Translation Tables` | as I8 |
| I11 | `settings/dialogs.py:439` | `TranslationTablesPanel.panel_description` | `Translation table mappings for different languages` | as I9 |
| I12 | `settings/dialogs.py:557` | `ViewSettingsPanel.title` | `View` | as I8 |
| I13 | `settings/dialogs.py:558` | `ViewSettingsPanel.panel_description` | `Font, font size, and color scheme for the main window input and output areas` | as I9 |
| I14 | `settings/dialogs.py:653` | `DotExpressSettingsDialog.base_title = _("DotExpress Settings")` | `DotExpress Settings` | `_collect` (`:698`, caption of the validation box) |
| I15 | `settings/dialogs.py:654` | `DotExpressSettingsDialog.title_template = _(...)` | `DotExpress Settings: {category}` | `_format_title` (`:681-682`) |

**15 call sites in 3 files.** All other uses of `ENTRY_TYPE_LABELS` (`entries.py:88` `normalize_entry_type`, `dialog.py:149`) and `ENTRY_TYPE_OPTIONS` (`dialog.py:148`, `:167`) read only the keys.

**Out of scope, recorded:** `client/braille/tables/__tables.py` makes **198** import-time calls of its **own** `_` (`:23-32` builds a separate `gettext.translation` with `languages=["zh_TW"]` and `localedir=<braille>/locales`; the table display names `:36-695`). It must not be changed (HANDOFF section 5; it is synced from NVDA by `scripts\sync-nvda.py`, which must not be run either). Effect today: the packaged build finds `_MEIPASS\locales` and gets zh_TW names at import; a source run finds no `client/braille/locales` and gets English names, which `TranslationTablesPanel._load_table_options` (`settings/dialogs.py:545-551`) translates again at display time (P2-3 spec D6). For a future switch this means: in the packaged build the table names stay in the language that was active at start; the display-time `_()` cannot turn a zh name into another language. The future switching task has to solve it without editing `__tables.py` (for example by reloading the table registry, or by keeping the English names through another path). F-14 does not change `_load_table_options`.

Texts translated when a window or menu is **built** (labels, menu items, `wx.Choice` items, window titles) are display-time already; a live switch has to rebuild those windows. That is the future feature (U1), not F-14.

### The HTML that declares `lang`

`dual_view/html.py:36-75` `render_dual_view_html(model, *, empty_message=...)` is the only HTML template of the client (grep for `<html`, `doctype`, `SetPage`). Line `:51` writes `<html lang="en">`. Its producers:

| # | Path | Call | Who sees it |
| --- | --- | --- | --- |
| H1 | Dual View window (View > Dual View) | `gui._render_dual_view_for_open_document` (`gui.py:329-335`) -> `_refresh_dual_view` -> `DualViewFrame.refresh_html` -> `web_view.SetPage` (`ui/dual_view.py:68-69`) | the in-app web view |
| H2 | Dual View in the browser (`on_open_dual_view` -> `_open_dual_view_in_browser`, `gui.py:350`) | the same render, written by `write_dual_view_html` to `dual-view-*.html` under the app's dual view folder | the system browser |
| H3 | File > Export > Dual View HTML, and Export All with that format | `documents/formats._write_html` (`formats.py:104-113`, render at `:109`) | the exported file |
| H4 | The page without conversion data | H1-H3 with `empty_message` (`gui.py:334`, `formats.py:112`) | same as above |

`tests/test_translation_golden.py:174` renders `render_dual_view_html(model)` and stores its sha256 as `dual_view_html_sha256` in `tests/fixtures/translation_golden.json`, whose blob sha256 (`e67d95a1...`) must not change. So the bytes of a render with `lang="en"` must stay reachable and identical.

No existing test asserts the `lang` attribute (grep).

### The settings backup message (`config.py`, `gui.py`)

- `ConfigStore._save` (`config.py:194-229`): for a damaged `config.json` (`_UnreadableConfig` with a non-`OSError`), `_backup_unreadable` (`:189-192`) reads `config.json` and writes `config.json.bak` with `write_bytes_atomically` (a temporary `.config.json.bak.<random>.tmp`, then `os.replace`). Any exception is logged by `_log_current_exception(logging.ERROR, "Failed to save config file %s", path)` **with the traceback** (`exc_info=True`) to `config.log`, and `_save` returns `ConfigSaveProblem(BACKUP_FAILED, error, path, backup_path)` without writing `config.json`.
- `BrailleFrame._report_settings_save_problem` (`gui.py:456-494`, F-12 D6 and review M-2/M-5) shows the first problem of the session. Its `BACKUP_FAILED` branch (`:474-477`) uses F-12's string 22 `The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Details: {error}` / `檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}`. The `UNREADABLE` and `WRITE_FAILED` branches already choose their text with `config.is_access_error` (`config.py:84-90`: `PermissionError`, or an `OSError` with `winerror` 5, 32, 33 or `errno` `EACCES`, `EPERM`).
- F-12's GUI record (`auto-results.md`, item 114 (b), build `N-f12b`, `config.json` = `{`, a folder `config.json.bak`) shows the content `檔案已損壞，而且在取代它之前無法先備份為「<d>\config.json.bak」。詳細資訊：[WinError 5] 存取被拒。: '<d>\\.config.json.bak.<rnd>.tmp' -> '<d>\\config.json.bak'`.
- Tests that pin today's text: `tests/test_gui_document_flows.py:5289-5291` (`test_each_kind_of_problem_gives_its_reason`, `:5283`) and `tests/test_i18n.py:237`, `:244` (`test_settings_not_saved_strings_are_translated`).

## Design

### Item 7: translate at display time

**D1. `i18n` translates through the active catalog and knows the interface language.**

- `_` becomes a module function: `def _(message: str) -> str`, which looks up the module's current catalog at each call. Consumers keep `from i18n import _`; what they hold is now this function, so a later catalog change reaches every module. Tests that patch a consumer's `_` (`dialog._`, `gui._`, `settings.dialogs._`, `dialog_base._`) keep working.
- `_("")` returns `""` instead of the catalog header. Decided by orchestrator with the recommended default; user may override before merge (O3).
- New: `SOURCE_LANGUAGE = "en"` (the language of the msgids).
- New: `set_language(language: str, *, localedir: Path | None = None) -> None` loads the catalog of `language` with `load_translation(localedir, (language,))` and makes it the active one. The language it records is `language` when a catalog was found (a `gettext.GNUTranslations`), else `SOURCE_LANGUAGE`, because the user then sees the English msgids. At import, `i18n` calls `set_language(LOCALE_LANGUAGES[0])`, which gives exactly today's catalog. No other application code calls it in F-14; it is the seam the future switch will use, and tests use it now. Decided by orchestrator with the recommended default; user may override before merge (O1, O2).
- New: `current_language() -> str` returns the recorded language (`"zh_TW"` in the app).
- New: `html_language_tag(language: str | None = None) -> str` returns the BCP 47 form of `language` (default: `current_language()`): the gettext code with `_` replaced by `-` (`zh_TW` -> `zh-TW`, `en` -> `en`). No mapping table: the gettext codes DotExpress can ship (`ll` or `ll_CC`) map one to one.
- `LOCALE_LANGUAGES`, `load_translation`, `resource_path` and `N_` keep their signatures. The interface language stays fixed `zh_TW`.
- Not related to `ConfigStore.get_lang` / `set_lang` (`config.py:250-273`), which select the braille conversion language; F-14 changes neither, and `current_language` reads nothing from `config.json`.

**D2. `about.py`: msgids at import, text at display.**

- `longName = N_("DotExpress")` and `description = N_("A text-to-braille ...")` hold msgids (`description` is unused; it stays a msgid for the catalog).
- `copyright_text() -> str` returns `_("Copyright (C) {years} DotExpress Contributors").format(years=copyrightYears)`.
- `about_message() -> str` returns the translated About text, formatted as today (`longName=_(longName)`, `copyright=copyright_text()`, `name`, `version`, `version_detailed`, `url`). The `# Translators:` comment stays with the msgid. The module attributes `copyright` and `aboutMessage` are removed (only `gui.on_about` read `aboutMessage`).
- `name`, `url`, `version`, `version_detailed`, `copyrightYears` (lines 4-8) are not touched (see "Merge precondition").
- `gui.on_about` (`gui.py:547`) shows `about.about_message()`.

**D3. `dictionaries/entries.py`: entry type labels are msgids.**

- `ENTRY_TYPE_OPTIONS` holds `(key, N_(label))`; `ENTRY_TYPE_LABELS` maps a key to its msgid. Both keep their names and keys, so `normalize_entry_type`, `DEFAULT_ENTRY_TYPE`, `dialog.py:148-149` and `:167` do not change.
- New `entry_type_label(entry_type: str) -> str`: the translated label of a known key, else `entry_type` unchanged (as `ENTRY_TYPE_LABELS.get(entry.entry_type, entry.entry_type)` does today).
- New `entry_type_choices() -> list[str]`: the translated labels in option order.
- `AddSymbolDialog.__init__` (`dialog.py:110`) builds its `wx.Choice` with `entry_type_choices()`; `EntryListModel.cell_text` (`entry_list_model.py:165`) returns `entry_type_label(entry.entry_type)`. The list is virtual, so its cells are read at paint time.

**D4. `settings/dialogs.py`: panel and dialog titles are msgids.**

- `title` and `panel_description` of the three panels, `base_title` and `title_template` of `DotExpressSettingsDialog` hold `N_` msgids. The attribute names stay (`tests/test_settings_options.py:265` pins them).
- Every reader translates: `SettingsPanel.__init__` (`SetLabel`, `SetName`), `SettingsPanelAccessible.GetDescription`, `MultiCategorySettingsDialog._build_layout` (the category list), `DotExpressSettingsDialog._format_title` (`_(self.title_template).format(category=_(category))`, called with the msgid), `_after_category_change`, `_collect` (the box caption `_(self.base_title)`).
- The base class keeps `title = ""` and `panel_description = ""`; with D1's `_("")` rule they read as `""`, not as the catalog header.
- `_load_table_options` (`:545-551`) is unchanged (see the `__tables.py` note).

**D5. A guard keeps import-time translation out.**

- A test walks the client like `scan.py` and fails on any `_`/`gettext`/`ngettext`/`pgettext` call outside a function body (module level, class body, default argument, decorator), with one allowed file, `braille/tables/__tables.py`, whose reason is written in the test.
- A second test runs the import probe in a subprocess: `i18n._` replaced by a recorder before the import of every client module except `main.py`; no call may be recorded. It catches an indirect call that the AST scan cannot see. The plan may drop it if it costs too much memory on the 8 GB machine (it imports `wx`); the AST test stays.

### Item 4: HTML `lang`

**D6. The HTML declares the interface language.**

- `render_dual_view_html(model, *, lang: str, empty_message=...)`: `lang` is a required keyword; the template writes `<html lang="{lang}">` (escaped). No default, so no producer can forget it. Decided by orchestrator with the recommended default; user may override before merge (O4).
- H1, H2, H4 (`gui._render_dual_view_for_open_document`) and H3, H4 (`documents/formats._write_html`) pass `lang=html_language_tag()`, read at each render. So the window, its browser copy, every exported file and the empty page say `zh-TW`.
- `tests/test_translation_golden.py:174` passes `lang="en"` explicitly, with a comment that the fixture was recorded with it. The fixture bytes and its sha256 do not change, and `--write` would reproduce them.
- `dual_view/html.py` still imports nothing from `i18n` (`test_translation_import_isolation`'s Dual View check stays green).
- No per-segment `lang` (U2): English words in a zh-TW page are inside the zh-TW document.

### Item 8: the backup message

**D7. A failed backup is explained by its kind of error.**

- `_report_settings_save_problem`, branch `BACKUP_FAILED`: when `config.is_access_error(problem.error)`, string N1; otherwise string N2. Both name the backup path (`{backup}` = `problem.backup_path`, as today) and neither contains the error text, so the temporary file name and the operating system's wording are gone from the box.
- Unchanged: the backup behaviour (`_backup_unreadable`, written and never read), the order (backup before the first write; nothing is written when it fails), the once-per-session flag, the caption `設定未儲存`, string 21 around the reason, the parent window, the `UNREADABLE` and `WRITE_FAILED` branches, and the log: `config.log` still gets `Failed to save config file <path>` at ERROR with the traceback, which holds the raw error and the temporary name.
- F-12's string 22 is no longer used; `msgmerge` moves it to the obsolete entries.
- Why `{backup}` stays: it is the file the user can look at or remove (a folder named `config.json.bak` is the case F-12's GUI item used), and it was shown before. The temporary name was only inside the error text.
- An error while **reading** `config.json` for the backup (it became locked between the load and the save) is also an access error; N1 therefore says "the file or the backup copy".

### Catalogs

**D8.** Items 7 and 4 add and remove no msgid: the plan regenerates the template after steps 1-3 and compares the sorted msgid set with that of `a147fed` (equal); only `#:` references move, and the `.mo` stays byte-identical. Step 4 adds N1 and N2: `scripts\generate-pot.bat`, `msgmerge`, the msgstr values of the table, `msgfmt --check --statistics` (408 translated, 0 fuzzy, 0 untranslated). `msgmerge` will likely pair N1 or N2 with string 22 as fuzzy (same first sentence); the plan replaces that msgstr and drops `#, fuzzy` and the previous-msgid lines. `POT-Creation-Date` stays `2026-10-10 12:00+0800`. Obsolete entries 26 -> 27.

## Behavior per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Help > About | `DotExpress (DotExpress)\n版本：1.2 (1.2) ...` | identical (D2) |
| Settings dialog: title, category list, accessible panel description, validation caption | `DotExpress 設定：轉譯`, `轉譯` / `轉譯表` / `檢視`, `轉譯輸出模式、寬度與字典選項`, `DotExpress 設定` | identical (D4) |
| Dictionary editor: Type column, Add/Edit entry Type choice | `一般`, `注音`, `Unicode 點字` | identical (D3) |
| Dual View window, Dual View in the browser | `<html lang="en">` | `<html lang="zh-TW">` (D6) |
| Export Dual View HTML (single, Export All), with or without conversion data | `<html lang="en">` | `<html lang="zh-TW">` (D6) |
| Settings change with a damaged `config.json` whose backup fails (access error, for example a folder `config.json.bak`, a locked `.bak`) | `檔案已損壞，而且在取代它之前無法先備份為「<bak>」。詳細資訊：[WinError 5] ... .tmp' -> ...` | N1 with `<bak>` (D7) |
| The same, other error (disk full, I/O error, not an `OSError`) | `... 詳細資訊：<error>` | N2 with `<bak>` (D7) |
| `config.log` for both | ERROR line with traceback | unchanged |
| Tests only: catalog switched after import | the 15 texts stay in the language of the import | they follow the switch (D1-D4) |

## Design per File

- `client/i18n.py` (4 spaces): D1.
- `client/about.py` (tabs): D2. Lines 4-8 untouched.
- `client/dictionaries/entries.py` (tabs): D3.
- `client/dictionaries/entry_list_model.py` (tabs), `client/dialog.py` (tabs): D3 readers.
- `client/settings/dialogs.py` (4 spaces): D4.
- `client/dual_view/html.py` (tabs): D6 template.
- `client/gui.py` (tabs): `on_about` (D2), `_render_dual_view_for_open_document` (D6), the `BACKUP_FAILED` branch (D7); imports `html_language_tag` from `i18n`.
- `client/documents/formats.py` (4 spaces): `_write_html` (D6).
- Catalogs: `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `.mo` (D8).
- Tests: see "Test Plan"; `tests/test_translation_golden.py` gets `lang="en"` (D6).
- Not changed: `config.py`, `client/braille/` (all of it), `ui/message_box.py`, `ui/conversion_presenter.py`, the three fixtures, every file of HANDOFF section 5.

## What Stays Identical

- Every text, label, title, accessible description and box of the app in zh_TW, except the HTML `lang` attribute and the `BACKUP_FAILED` reason.
- The HTML apart from `lang`: the same markup, styles, cells and empty-state sentence.
- `config.json` and `config.json.bak` handling (F-8 D11, F-12 D6), the log lines, the once-per-session rule.
- The braille conversion language (`config.py` `get_lang` / `set_lang`).
- `translation_golden.json` (`e67d95a1...`), `dictionary_entries_trace.json` (`f493da52...`, its 387 `一般` cells are produced under zh_TW as before) and `translation_liblouis_golden.json` (`8dc8572e...`).

## User-Visible Strings

| # | msgid | zh_TW msgstr (proposed) | Where |
| --- | --- | --- | --- |
| N1 | `The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. The file or the backup copy may be in use by another program, or you may not have permission to write to the folder. Close the other program and try again.` | `檔案已損壞，而且在取代它之前無法先備份為「{backup}」。檔案或備份檔可能正被其他程式使用，或你沒有該資料夾的寫入權限。請關閉其他程式後再試一次。` | D7, access error |
| N2 | `The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Check that the disk has free space and that you can write to the folder.` | `檔案已損壞，而且在取代它之前無法先備份為「{backup}」。請確認磁碟還有可用空間，且你有該資料夾的寫入權限。` | D7, any other error |

Removed from use (becomes obsolete): F-12 string 22, `The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Details: {error}`.

msgids: 407 + 2 - 1 = **408**. The wording reuses F-12's sentences: the first sentence is string 22's without `詳細資訊`, the rest follows F-12's two write-failure texts (`無法寫入檔案。檔案可能正被其他程式使用，或你沒有寫入權限。請關閉其他程式後再試一次。`, `...請確認磁碟還有可用空間，且你有該資料夾的寫入權限。`); 備份檔 follows 點字檔 / 文字檔.

## Accessibility (NVDA)

- With `lang="zh-TW"`, a screen reader with automatic language switching reads the Dual View window and the exported files with the Chinese voice (the reason for item 4, F-12 "Out of Scope"). English words in the page are read by that voice too (simple version, U2).
- The backup box no longer reads out a path with a random temporary name and `[WinError 5]`; it ends with what to do.
- Item 7 changes nothing a screen reader hears: the accessible names and descriptions of the settings panels are the same strings, now translated when read.
- Manual item 145 (user) checks the voice.

## Test Plan

TDD, red first where stated. Indentation follows each file. Tests that switch the catalog restore it with `addCleanup(i18n.set_language, previous)` so no later test (for example the dictionary trace, whose fixture holds zh labels) runs in English. Tests that make the code log use `assertLogs` or isolate the logger; nothing reaches `client/log/`. Temporary folders only.

### A. `i18n` (`tests/test_i18n.py`)

1. `current_language()` is `"zh_TW"`; `html_language_tag()` is `"zh-TW"`; `html_language_tag("en")` is `"en"`. Red (no such functions).
2. `set_language("en")` (no `en` catalog): `current_language()` is `"en"`, `i18n._("General")` is `"General"`; `set_language("zh_TW")`: `"一般"` again. Red.
3. A consumer imported before the switch follows it: `dialog._("General")` (any module holding `from i18n import _`) gives `"General"` after `set_language("en")`. Red (a bound method of the old catalog).
4. `set_language("zh_TW", localedir=<empty folder>)`: `current_language()` is `"en"` (O2).
5. `_("")` is `""`. Red (the header).
6. Existing tests stay: `LOCALE_LANGUAGES == ("zh_TW",)`, `load_translation()` is `GNUTranslations`, the environment test (subprocess prints `一般`), the duplicate-setup guard.
7. `SharedSetupConsumerTest`: `about.py` imports `{"N_", "_"}`, `dictionaries/entries.py` `{"N_", "_"}`, `settings/dialogs.py` `{"N_", "_"}`, `gui.py` `{"_", "html_language_tag", "resource_path"}`.

### B. The refactored places follow a switch after import (red today: their texts are frozen at import)

1. `about.about_message()`: under zh_TW contains `版本：1.2 (1.2)` and `版權所有 (C) 2025-2026 DotExpress 貢獻者` and equals today's `about.aboutMessage` text (literal); after `set_language("en")` contains `Version: 1.2 (1.2)` and `Copyright (C) 2025-2026 DotExpress Contributors`. `gui.on_about` passes `about.about_message()` (the existing test at `test_gui_document_flows.py:5021` changes from `about.aboutMessage`).
2. `entry_type_label` / `entry_type_choices`: zh `一般`, `注音`, `Unicode 點字`; en `General`, `Bopomofo`, `Unicode Braille`; an unknown key is returned unchanged in both.
3. `EntryListModel.cell_text(row, 2)` follows the switch; `AddSymbolDialog`'s choice items (as the existing dialog tests build it) follow the switch.
4. Settings: for each of the three panels, `SettingsPanelAccessible(panel).GetDescription(0)` and the label/name set by `SettingsPanel.__init__`; `_build_layout`'s category list items; `_format_title(TranslationSettingsPanel.title)` (`DotExpress 設定：轉譯` / `DotExpress Settings: Translation`); the `_collect` validation box caption (`DotExpress 設定` / `DotExpress Settings`). Each in zh and in en.
5. `SettingsPanel` with the base `title = ""`: label and name `""`, description `""` (not the catalog header).
6. The existing settings tests that patch `settings.dialogs._` with the identity keep their expectations (they already expect English) or are adjusted where a title is now read through `_`; `test_title_format_uses_localizable_template` stays green (a non-msgid template is returned unchanged).

### C. Guards (`tests/test_i18n.py`)

1. D5 AST guard: no import-time translation call in the client except `braille/tables/__tables.py`. Red today (15 hits).
2. D5 import probe in a subprocess (optional by memory): no recorded call. Red today (15 calls).
3. AST: the values of `ENTRY_TYPE_OPTIONS`, the panels' `title`/`panel_description`, `base_title`, `title_template`, `about.longName`, `about.description` are `N_` calls.
4. The catalog test `test_the_catalog_holds_exactly_the_marked_strings` stays green after each step.

### D. HTML `lang` (`tests/test_dual_view_html.py`, `tests/test_document_formats.py`, `tests/test_gui_document_flows.py`)

1. `render_dual_view_html(model, lang="zh-TW")` starts with `<!doctype html>\n<html lang="zh-TW">`; a value with `"` is escaped; calling it without `lang` raises `TypeError`.
2. `formats._write_html` writes `<html lang="zh-TW">` for a document with data and for one without (with the zh empty sentence); after `set_language("en")` it writes `lang="en"`. Red for zh.
3. `BrailleFrame._render_dual_view_for_open_document` returns `lang="zh-TW"` (and `en` after the switch). Red.
4. Export All with the HTML format: each file `lang="zh-TW"`.
5. `test_translation_golden` stays green with `lang="en"`; the fixture sha256 is unchanged.
6. Existing frame tests that compare an export with `render_dual_view_html(...)` (`test_gui_document_flows.py:1622-1684`) pass `lang="zh-TW"` in the expected render.

### E. Backup message (`tests/test_gui_document_flows.py`, `tests/test_i18n.py`, `tests/test_config.py`)

1. `_report_settings_save_problem` with `BACKUP_FAILED` and each access error of the F-12 review test (`PermissionError`, `winerror` 5, 32, 33, `errno` `EACCES`): reason N1 with the backup path. Red (today `詳細資訊：...`).
2. With `OSError(errno.ENOSPC, ..., <temp name>)`, `OSError(errno.EIO, ...)`, `IsADirectoryError`, and a non-`OSError` (`ValueError("x")`): N2. Red.
3. For every case the box text contains neither `str(error)`, the temporary name, `WinError`, nor `詳細資訊`.
4. `test_each_kind_of_problem_gives_its_reason` (`:5283`): the `BACKUP_FAILED` row expects N1 (its error is `OSError(13, ...)`, an access error). Cases 1-3 are `BACKUP_FAILED` rows added to `test_only_an_access_error_says_the_file_is_in_use_or_not_permitted` (`:5307`), which already asserts that the temporary name `k3j9x2` is absent.
5. `test_config`: a damaged `config.json` with a folder `config.json.bak` still returns `BACKUP_FAILED` and logs `Failed to save config file <path>` at ERROR; the record's `exc_info` holds the error (the raw text reaches the log).
6. Catalog: N1, N2 msgstr values; `test_settings_not_saved_strings_are_translated` drops string 22 and checks N1, N2.

### Mutation check (plan; each must be caught)

1. `i18n._` back to a bound method of the import-time catalog;
2. `set_language` not recording the language;
3. `current_language` returning `zh_TW` for a missing catalog;
4. `html_language_tag` keeping `_`;
5. `_("")` returning the header;
6. `about_message` built at import again (a module constant);
7. `entry_type_label` returning the msgid untranslated;
8. `cell_text` reading `ENTRY_TYPE_LABELS` directly;
9. `AddSymbolDialog` choices from the msgids;
10. a panel `title` translated at class level again;
11. `GetDescription` not translating;
12. `_format_title` not translating the category;
13. `_collect` caption not translated;
14. the HTML template with `lang="en"` again;
15. `_write_html` without `lang` from `html_language_tag()` (hardcoded `zh-TW`, caught by the en switch);
16. the frame render without the tag;
17. N1 and N2 swapped;
18. `{error}` appended to the reason again;
19. the access check dropped (always N2);
20. the AST guard's allow-list widened to all of `braille/`.

### Counts

About 30 new tests and 3 changed expectations (A 6, B 6, C 4, D 6, E 6, plus the consumer guards). The plan fixes the exact `Ran`; on Windows `OK (skipped=6)` before F-13's merge.

## Migration Steps (each step one green commit, red first)

1. `refactor: let i18n translate through the active catalog and report the interface language (F-14)`: D1; tests A. Catalogs untouched.
2. `refactor: translate the About text, entry types and settings titles when they are shown (F-14, F-12 review M-7)`: D2-D5; tests B, C, A7. Template regenerated: msgid set unchanged (D8), `.po` `#:` lines only, `.mo` byte-identical.
3. `fix: declare the interface language in dual view and exported HTML (F-14)`: D6; tests D. No catalog change.
4. `fix: explain a failed settings backup without the system's text (F-14)`: D7, D8; strings N1, N2; tests E.

Each step that moves lines above a msgid regenerates the template, so no `#:` reference is stale at the end. Commits stage explicit paths, end without a `Co-Authored-By` trailer (HANDOFF section 5), and are not pushed.

## Acceptance Criteria

Run on Windows from `client/` with `$PY`, the runtime copied as in Task 0 of the F-3 plan (never staged); available memory at least 600 MB before each heavy run.

1. Full suite: no failure, no error; `Ran` as the plan states.
2. Focused: `$PY -B -X utf8 -m unittest tests.test_i18n tests.test_dual_view_html tests.test_document_formats tests.test_settings_dialogs tests.test_settings_options tests.test_dictionary_entries_dialog tests.test_config tests.test_translation_golden tests.test_gui_document_flows -v` passes.
3. The D5 AST scan lists only `braille/tables/__tables.py`; the import probe records no call.
4. Catalogs: 408 msgids, all translated, 0 fuzzy (`msgfmt --check --statistics`); the msgid set equals `a147fed`'s plus N1, N2 minus string 22; `POT-Creation-Date` unchanged; obsolete entries 27.
5. The three fixture sha256 values unchanged.
6. App data untouched (main checkout's `client/dictionary/`, `client/workspace/`, `client/config.json`, `client/log/` same sha256 before and after); the worktree gets none of them.
7. `git diff main --stat` touches only the files of "Design per File", tests, and the spec, plan and history files; `client/braille/tables/__init__.py` byte-identical (CRLF), `__tables.py` unchanged.
8. The mutation check.
9. The packaged GUI verification below, results in the implementation's history folder.

## Windows Verification (packaged build)

Process as in F-11 and F-12: `scripts\build-dotexpress.bat` with the main checkout's `client\.venv\Scripts` first on `PATH`; the changed modules come from the worktree (`PYZ-00.toc`); the new build goes to `D:\dxtest\N-f14`, the old one is `D:\dxtest\N-f12b`. Each item runs in a new `D:\dxtest\auto<item>-f14` folder (old build: `auto<item>-f12b-f14`) through `auto/safe_run.py` (keys only while DotExpress is in front; the log names no other program's windows); only processes under those folders are ended. Files are prepared by the script before launch; **no script reads or writes the clipboard**; text goes in with `set_edit_text` or typed keys. Never a real logoff or shutdown. One heavy job at a time, 600 MB free before each.

**fix** items run on both builds; **regression** items run on `N-f14` only, and on `N-f12b` only when they miss their expectation.

| # | Class | Steps | Expected on `N-f14` | `N-f12b` |
| --- | --- | --- | --- | --- |
| 141 | fix | (a) Document `alpha` with `中文 abc`, Convert, File > Export > Dual View HTML to an empty folder. (b) Default document `new` (no conversion data), Export > Dual View HTML. (c) Two converted documents, Export All, Dual View HTML. Read each file's first two lines. | every file: `<!doctype html>` then `<html lang="zh-TW">`; (b) also contains `此文件沒有可顯示的轉換資料。` | `<html lang="en">` |
| 142 | fix | `config.json` = `{` and a folder `config.json.bak` before start (F-12 item 114 (b)); Settings: change the conversion width, Apply, then OK | after Apply one box, caption `設定未儲存`, main text string 21 with `<d>\config.json`, content N1 with `<d>\config.json.bak`, no `WinError`, `存取被拒`, `.tmp` or `詳細資訊`; owner the settings dialog; nothing after OK; `config.json` still `{`; `log\config.log` has an ERROR `Failed to save config file` whose traceback contains `WinError 5` | content `... 詳細資訊：[WinError 5] 存取被拒。: '...\.config.json.bak.<rnd>.tmp' -> ...` |
| 143 | regression | (a) Help > About: read the whole text. (b) Settings: read the title, the category list, then Ctrl+Tab twice reading the title each time; read each panel's accessible description (UIA `LegacyIAccessible.Description`). (c) Dictionary Management > Edit `default` with rows of the three types: read the Type column; Add: read the Type choice items; Cancel. | (a) starts `DotExpress (DotExpress)`, then `版本：1.2 (1.2)`, `網址：https://coseeing.org`, `版權所有 (C) 2025-2026 DotExpress 貢獻者`; caption `關於 DotExpress`. (b) `DotExpress 設定：轉譯`; `轉譯`, `轉譯表`, `檢視`; `DotExpress 設定：轉譯表`, `DotExpress 設定：檢視`; descriptions `轉譯輸出模式、寬度與字典選項`, `不同語言的轉譯表對應`, `主視窗輸入與輸出區的字型、字體大小與配色`. (c) `一般`, `注音`, `Unicode 點字` in the column and in the choice | (only if a result misses) |
| 144 | regression | (a) View > Dual View for a converted document and for `new` without data: read the web view's text through UIA. (b) Settings with an intact `config.json`: change the width, OK. | (a) the cells' text, and `此文件沒有可顯示的轉換資料。` for `new`; no error box. (b) no box; `config.json` updated | (only if a result misses) |

**Manual for the user (item 145, NVDA; never ticked by an agent):** with `N-f14`, NVDA running and its automatic language switching on: open View > Dual View on a converted Chinese document and read it with NVDA; then open an exported Dual View HTML file of item 141 in the browser. Is the Chinese text read with the Chinese voice (with `N-f12b` it may use the English voice)? Then open the box of item 142 and listen: is the whole text read, without a temporary file name?

## Risks

- **A global catalog in tests** (medium). A test that switches the language and does not restore it would make later tests see English (the dictionary trace fixture holds zh labels). Every switch goes through `addCleanup`; the plan runs the suite in the default order and with a shuffle seed.
- **`_` as a function** (low). Every call site already calls it with one positional string; tests patching a consumer's `_` are unaffected. A test that compared `module._` with `i18n._translation.gettext` would break; none does (grep).
- **Hidden import-time translation added later** (low). The D5 guards fail on it.
- **The golden render** (low). Only `test_translation_golden.py`'s call changes; the fixture is not regenerated, and its sha256 is checked (criterion 5).
- **Catalog merge with F-13** (medium, mechanical). Regenerate, do not hand-merge (see "Relation to F-13").
- **The user's uncommitted `about.py`** (blocking at merge time only). See "Merge precondition".
- **`is_access_error` for the folder case** (low). On Windows a folder `config.json.bak` gives `[WinError 5]` from `os.replace`, an access error, so item 142 shows N1; N2 is covered by unit tests (a disk-full or I/O error cannot be produced safely on this machine).

## Open Questions

**Decided by the user (2026-10-14):** U1-U4.

**Decided by orchestrator with the recommended default; user may override before merge:**

- **O1.** `i18n` gains `set_language()` as the seam for the future switch; in F-14 only the import and tests call it (D1). Not user-visible.
- **O2.** `current_language()` reports `en` when the requested catalog is missing (the user then sees English), so the HTML `lang` matches the shown text (D1). The packaged and source builds ship the catalog, so the app reports `zh_TW`.
- **O3.** `_("")` returns `""` instead of the catalog header (D1). Visible only where an empty text would have shown the header (no known path).
- **O4.** `render_dual_view_html` requires `lang`; the golden test passes `"en"` explicitly; the fixture is not touched (D6).
- **O5.** `about.aboutMessage` and `about.copyright` become functions `about_message()` and `copyright_text()`; `longName` and `description` hold msgids (D2).
- **O6.** The `__tables.py` table names are left as they are and recorded for the switching task (Current State).
- **O7.** The BACKUP_FAILED reason keeps the backup path `{backup}` and uses F-12's `is_access_error` split (D7).
- **O8.** No GUI item forces the N2 case; unit tests cover it (Risks).

**Questions for the user** (not blocking; the spec is written with the recommended option):

- **Q1. Wording of N1 and N2** (table above). Recommended: as written. A shorter alternative for N1 is `檔案已損壞，而且在取代它之前無法先備份為「{backup}」。請關閉可能正在使用這些檔案的程式，並確認你有該資料夾的寫入權限，然後再試一次。` Changes are one-line catalog edits.
- **Q2. Merge precondition.** Commit the `about.py` version bump in the main checkout before F-14 merges, or allow the orchestrator to stash and restore it around the merge.

## User-Visible Defaults Introduced by This Spec (not decided by the user)

1. **The texts of N1 and N2** (Q1).
2. **The `lang` value is `zh-TW`** for every Dual View page, the window included (the user decided "依介面語言"; the exact tag follows BCP 47).
3. **The backup box still names the `.bak` path** and says "the file or the backup copy" for an access error (O7).

## Out of Scope / Follow-ups

- **The language switch itself** (U1): a menu or setting, saving the choice, rebuilding open windows and menus, the table names of `__tables.py` (Current State).
- **Per-segment `lang`** for English in the Dual View HTML (U2).
- **F-13's items** 1, 2, 3, 5, 6.
- Deferred by the user (`task.md` "延後的項目", 2026-10-14, "不修"): the export `.tmp` retry, case-insensitive dictionary headers, a failed case (b) save lost at close (F-9 M-5), a damaged `config.json` replaced silently (F-12 Q2), the selection after deleting one of two equal entries (F-11 M-4).
- F-10 (UEB line breaks, `$`).
