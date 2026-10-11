# Localization Cleanup and Message Follow-ups (F-12) Design

## Goal

Task F-12 is item 5 of the ordering in `task.md` ("F-12 本地化收尾"). It turns the remaining English and raw Python messages that users see into localized, actionable text, and adds the few messages that earlier reviews found missing.

Decided by the user (2026-10-11), `task.md` section 三 "F-12 範圍"; not asked again here:

- **U1. Scope is text messages only.** In scope:
  1. user-visible English messages that are not localized (P1-4 defect 4, for example the Export All summary);
  2. a friendly message instead of the raw Python error when a conversion cannot read the selected dictionary (F-6 O5);
  3. a dedicated message when a document name is held by a `.dep` (or anything else) in the workspace folder that is not in the document list (F-8a review, table D1);
  4. a hint when settings cannot be saved to `config.json` (F-8a review M-7).
- **U2. F-9 review M-9 is in scope.** When a conversion fails for a job whose document is not the open one, the failure message names the document (D7).
- **U3. Out of scope** (listed under "Out of Scope / Follow-ups", no design here): the startup boxes and NVDA (F-8b review M-8), the `WM_ENDSESSION` exit code (F-9 review M-8), the export `.tmp` retry, case-insensitive dictionary headers, the Delete All rollback (P1-3 defect 4), and F-W5.

After this task:

- The Export All summary, the conversion fallback texts, the import problem reasons, the HTML save filter, the exported "no conversion data" page and a few rare error texts are shown in Traditional Chinese.
- A conversion that cannot read the selected dictionary says which dictionary and why, in one line, with the F-6 reasons (and a new reason for a header that is not recognized).
- A name held by a file that is not listed says so, names the file and shows the workspace folder; a listed duplicate keeps `文件「X」已存在。`.
- The first settings change of a session that cannot be saved shows one warning box; the log lines stay as they are.
- A failed manual conversion whose document is no longer open, and a failed single export of a document that is not open, name the document.

New user-visible strings: **23** msgids, 4 of them revived from obsolete catalog entries with their old translations (see "User-Visible Strings"). The msgid count goes from **381** (main after F-11) to **404**.

Non-goals:

- raw operating-system and third-party library texts that follow a localized lead (`[Errno 13] ...`, pypdf, ebooklib, MathCAT; "Out of Scope");
- Python's own `SyntaxError` text for a text processing script (it is for the script's author);
- any change of behaviour other than which text is shown, except the one new warning box of D6;
- F-10 (UEB line breaks, `$`).

## Relation to F-11

F-11 (dictionary editor UX, `D:\workspace\DotExpress-f11`, branch `fix/f11-dictionary-editor-ux`) merges into `main` before F-12 is planned. This spec assumes `main` + F-11:

- The catalog holds 381 msgids (F-11 adds 370-381, the last one its review fix: `Dictionary "{name}" cannot be saved: its header is not recognized. ...`).
- F-11 changes `conversion/text/dictionary_rules.py` (`LoadedDictionaryRules.from_paths`: D13 skips hidden rows, D14 the first-tone space), `dictionaries/manager.py`, `dictionaries/presenter.py`, `dialog.py`, `ui/message_box.py` and `gui.on_open_dictionary_management`. F-12's D4 also changes `from_paths`. Code is named by function; the line numbers below are from `main` `1ce6ce5` and are orientation only. The plan re-takes them on the post-F-11 `main`.
- D4's header reason (string 17) uses the same words as F-11's string 12, so the editor and the conversion describe an unrecognized header alike.
- No F-12 decision touches the editor, Dictionary Management or the F-11 confirmation boxes. F-11's follow-up "Esc in the existing Yes/No confirmations" is not a text message, so it stays out (U3; "Out of Scope").
- F-11's GUI items end at 108 (107 is the manual NVDA item). F-12's items are 109-119.

## Corrected after planning (F-12, 2026-10-11)

Re-checked against the code of `main` `e0337df` (F-11 merged, after its review and the I-1 fix): every decision D1-D9, the behavior table, the inventory E1-E8 and the probes hold, with the refinements below. Function names are as the spec gives them; line numbers moved (orientation only). The plan's section "Spec Corrections and Refinements" holds the same list.

1. **Baseline and counts.** On `e0337df` (`HEAD:client` `5e130210`) the suite gives `Ran 1567`, `OK (skipped=6)` (the spec quoted the F-11 branch before I-1, `Ran 1564`) and the catalogs hold 381 msgids. F-12 adds 60 tests net: `Ran 1569` after Task 1, `1583` after Task 2, `1591` after Task 3, `1599` after Task 4, `1614` after Task 5, `1620` after Task 6, `1626` after Task 7 (the spec estimated about 50 new tests and 6 flipped), `1627` after Task 8 (corrections 17); Task 9 changes `scripts/tests` only (corrections 18). msgids 381 -> 386 (Task 1) -> 392 (Task 2) -> 394 (Task 3) -> 396 (Task 4) -> 399 (Task 5) -> 400 (Task 6) -> 404 (Task 7). Tasks 1-7 follow the spec's seven migration steps in order, each with its own catalog pass (every step adds strings); Task 8 adds none but moves `gui.py` lines, so it regenerates the template and the `.po` too (`#:` lines only, the `.mo` unchanged), and no `#:` reference is stale at the end.
2. **The pins that flip.** Besides the six `KNOWN BUG (P1-4 spec, defect 4)` pins (now at `test_export_coordinator.py:148`, `547`, `test_gui_document_flows.py:3818`, `4177`, `4208`, `test_conversion_presenter.py:188`), every other Export All summary in those two modules expects the zh_TW texts (eleven assertions in all). The expected summaries and fallback texts are zh_TW literals (what the user sees), so they also fail while the code is changed but the catalog is not ("green apart from the catalog").
3. **Import reasons in existing tests.** `test_document_workspace.py`, `test_workspace_service.py` (four save issues, two duplicates) and the frame's Import tests in `test_gui_document_flows.py` expected the English or raw reasons; they expect the zh_TW ones (Task 2), and the unlisted one in Task 4.
4. **`ImportProblem` lives in `documents/import_problems.py`**, next to `describe_import_problem`, not in `documents/importers/base.py`: importing anything from `documents.importers` runs its `__init__`, which imports the DOCX, EPUB and PDF importers (pypdf, pymupdf, ebooklib), and `documents/workspace.py` imports them lazily today. `importers/base.py` imports `ImportProblem` from there. Its signature is `ImportProblem(detail, reason)`: `str()` is the English detail of before, `reason` the `N_`-marked msgid. The three package refusals and the unsupported type use module constants or an inline `N_`.
5. **The order of `describe_import_problem`:** an `ImportProblem` first, then `PermissionError` (CANNOT_OPEN), the name errors (`reserved`, which no document name can raise, shows the invalid-name text), then any other error of a `dep` **that is not an `OSError`** (string 13: a damaged zip, a missing member, metadata that is not JSON, text that is not UTF-8), then `UnicodeDecodeError` (string 10), else `無法讀取檔案：{error}`. A package that disappeared (`FileNotFoundError`) gets the raw text, not "must be a valid DEP package". Decided by orchestrator with the recommended default; user may override before merge.
6. **D3 before D5.** Until Task 4, Import still counts the stems of the unlisted packages as taken names, so such a name gets the listed message `文件「X」已存在。` (Task 2) and string 18 from Task 4 on.
7. **D4 on the code after F-11's I-1.** `from_paths` now catches every exception of `processing` (`except Exception: continue`), so Test Plan D3's "error raised by `processing` that F-11 does not catch" is a `processing` that returns a value that is not iterable: `list(target)` raises `TypeError` after the read, and it is not wrapped. The guarded read is a helper `_read_dictionary_rows` (open, header check, `list(reader)`); the Bopomofo file is read before it, unguarded, as before. `DictionaryRulesReadError` is an `Exception`, not a `ValueError`, so a test that the Bopomofo error is not wrapped cannot pass by subclassing. The existing tests that expected `ValueError` or `UnicodeDecodeError` for the dictionary (the error-case table, the loader's retry, `test_conversion_service`'s headerless case) expect `DictionaryRulesReadError` with the same text.
8. **D5's entry and Rename.** `unlisted_package_entry(name, *, exclude_name=None)` returns `None` exactly when `package_name_taken(name, exclude_name=...)` is false, so the frame asks it instead of `package_name_taken` (Rename passes its own document as `exclude_name`); a folder that cannot be listed also falls back to `"<name>.dep"`. `batch_import_documents` gets `unlisted_entries` (name -> file name) and `import_files` no longer puts those stems into `existing_names`. String 18 is built by one function, `documents.workspace.unlisted_entry_reason`, for the box and for Import. The frame's delegation test gives its stand-in service `unlisted_package_entry.return_value = None`.
9. **D6's details.** `save_translation_settings` calls all three setters and returns the first problem (a tuple, not an `or` chain, which would skip the later setters). The once-per-session flag is a class attribute of the frame, like `_closing`, because tests build frames without `__init__`. Frame tests whose stand-in saves are Mocks (`Mock(spec=ConfigStore)`, a patched `save_*`) get `return_value=None`: a Mock would count as a problem and show a box. The UNREADABLE tests use a folder at `config.json` (opening it fails as for a locked file); GUI item 114 (a) uses the share-none lock.
10. **D7 for a single export without an open document.** The rule compares the exported document with the open one at delivery; with no open document they differ, so the message is named. The existing coordinator test that exports the pending `beta` with no open document opens `beta` first, so it still pins the unnamed text. The presenter and the coordinator each format string 23 (one msgid, two references).
11. **D8 in existing tests.** Two frame characterization tests (`test_real_writers_produce_today_bytes`, `test_export_all_html_uses_each_document_cache`) rendered the page without conversion data with the English default; they expect the zh_TW sentence. The checks `assertNotIn("No conversion data", html)` look for the zh_TW sentence, or they would pass whatever the page says. The title test that expected `gui._(gui.format_window_title("beta"))` expects `gui.format_window_title("beta")` (D9).
12. **The script errors (D8)** are tested through `test_user_preprocessing_script.py` and, for `format_conversion_error`, through the real pipeline in `test_conversion_service.py` (a `main` that returns `None`, and `main = 1` after its definition).
13. **Test Plan A2** compares the set of `_()`/`N_()` strings of the client (AST) with the keys of the compiled catalog, both ways; the count 404 is checked in Task 10 (msgid scan) rather than pinned in the test, which would fail in every later task that adds a string.
14. **Catalogs.** `msgmerge` revives strings 1-3 (Task 1) and 13 (Task 2) exactly from their obsolete entries (active, not fuzzy, the old msgstr, no obsolete copy left). It guesses eight wrong fuzzy translations, which the fill steps replace (and drop the fuzzy flag): string 5 <- `請先選擇轉譯表。` (Task 1); string 10 <- F-6's NOT_UTF8 text and string 11 <- `無法讀取檔案：{error}` (Task 2); string 16 <- `無法讀取字典「{name}」。` and string 17 <- F-11's string 12 (Task 3); string 20 <- `設定` (Task 5); string 23 <- string 16's msgstr (Task 6); string 6 <- the obsolete `文字檔 (*.txt)|*.txt` (Task 7), which `msgmerge` then drops from the obsolete entries. Obsolete entries: 31 -> 28 (Task 1) -> 27 (Task 2) -> 26 (Task 7). The `.mo` grows from 30,650 to 34,046 bytes.
15. **Tests the spec did not list:** the frame's Import Issues in zh_TW (D3); a package the loader refuses is still invalid at startup (E5, `test_document_workspace`); the listed check before the entry on disk at the batch level; the helpers' first problem; `set_lang` and the client id; the browser error; the two characterization tests and the title test of correction 11.
16. **Windows items.** "Before" is `D:\dxtest\N-f11c` (the code of `e0337df`), the new build `D:\dxtest\N-f12`. Items 109-117 and 120 are fix items (run on both builds), 118 a regression item (`N-f12` only), 119 manual; 120 is Task 8's (correction 17). Item 111's `locked.txt` is held share-none by F-8a's `lockshare.py` before the Import: typed together with other names, the file dialog accepts it (a draft run on `N-f11c` showed `[Errno 13] Permission denied` for it), unlike a single file chosen alone (F-11 Spec Corrections 12). Item 114 changes the conversion width on the settings dialog's first page for (a) as well: every OK or Apply saves all settings, so which value changes does not matter, and the font size is then changed with Ctrl+wheel, which is what (a) checks for a second box.
17. **P1-3 defect 4, added to F-12 scope by the user (2026-10-11).** When a Delete All fails and the reload finds no valid document, `on_delete_all_documents` only cleared the editors: the title kept the deleted document's name and no document was open. It now does what a complete Delete All does: `_update_window_title()`, `_clear_document_editors()`, `_ensure_open_document_exists()` (which creates and opens the default document under F-8's free-name rule: `new (2)` when something on disk holds `new`). Task 8; the pin `test_delete_all_failure_without_valid_document_clears_editors_only` flips (renamed `..._opens_the_default_document`), a test for the free name is added, the frame delegation test expects the two calls; no new string; two mutants; GUI fix item 120 (a valid `beta.dep` held share-none after the start, so its delete fails and the reload finds it invalid). User-visible: after such a failure the default document is open and the title names it.
18. **F-W5, added to F-12 scope by the user (2026-10-11).** `scripts/tests/test_vendor_helper_snapshot.py` compared `read_bytes().decode()` of `vendor/nvda/liblouis/runtime/louis_helper.py` (LF in the repository, CRLF in a Windows working tree with `core.autocrlf=true`) with LF text, so it failed on Windows (`results.md` of the 2026-10-09-03 verification). Task 9 normalizes CRLF to LF in the test's comparison; the vendored file and `.gitattributes` are not changed (an `eol=lf` rule would take effect only for files checked out again and would change the bytes of existing working trees). How it was run: from the repository root, `python -B -X utf8 -m unittest discover -s scripts/tests -t .` and the single module `scripts.tests.test_vendor_helper_snapshot`, in a clone with `include/nvda/source/louisHelper.py` copied from the main checkout (the rest of the `include/nvda` and `include/liblouis` submodules is absent there, so 13 other tests raise `FileNotFoundError` before and after, unchanged): before `FAIL` (`\n` against `\r\n`), after `OK`.
19. **Review fixes (F-12 review of `c1295df`, 2026-10-11). Decided by orchestrator with the recommended default; user may override before merge.** The review found no Critical or Important finding; these are its Minor findings M-1 to M-5 (M-6 is by design, Q1; M-7 is a follow-up). Three strings are added, so the catalogs hold 407 translated msgids (404 + 3), 0 fuzzy; `msgmerge` guessed two wrong fuzzy translations (the new damaged-file text from the EPUB text, the write-permission text from CANNOT_OPEN), both replaced.
    - **M-1 (log).** `batch_import_documents` logs every error that is not an `ImportProblem`, `OSError`, `UnicodeDecodeError` or `NameValidationError` at ERROR on `dotexpress.gui` (`gui.log`), with the traceback and the file name, so a bug in a loader is not mistaken for a bad file. A file that is not a zip archive as a `.dep` is logged too. The Import Issues text is unchanged.
    - **M-3 (damaged DOCX, EPUB, PDF).** For the `docx`, `epub` and `pdf` loaders, an error that is not an `OSError` is shown as the new string `The file is damaged or is not in the expected format.` / `檔案已損壞或格式不正確。` (the library's English text is only in the log). A locked or missing file keeps `無法讀取檔案：{error}`. Before: `無法讀取檔案：File is not a zip file`.
    - **M-2, M-5 (settings not saved).** The reason of the box is chosen by the error. `config.is_access_error` is true for a `PermissionError` or an `OSError` with `winerror` 5, 32 or 33 or `errno` `EACCES` or `EPERM`. An unreadable `config.json` shows the CANNOT_OPEN text only for such an error, else the existing `無法讀取檔案：{error}`. A failed write shows, for such an error, the new string `The file cannot be written. It may be in use by another program, or you may not have permission to write to it. Close the other program and try again.` / `無法寫入檔案。檔案可能正被其他程式使用，或你沒有寫入權限。請關閉其他程式後再試一次。`; for any other error the new string `The file cannot be written. Check that the disk has free space and that you can write to the folder.` / `無法寫入檔案。請確認磁碟還有可用空間，且你有該資料夾的寫入權限。` The operating system's text, which holds the random name of the temporary file, is no longer shown for a failed write. The backup-failed text still ends with the operating system's text (`詳細資訊：{error}`), kept on purpose as the diagnosis (GUI 114 (b)); the box is shown once per session.
    - **M-4 (docs).** Item 114 (a) is "locked after the start, before pressing OK" and changes the conversion width (as the plan and the implementation notes say); the plan's step boxes are ticked.
    - **Manual item 119** (NVDA) now uses `D:\dxtest\N-f12b\DotExpress.exe`, the build with these fixes; it stays unchecked for the user.

## Current State (verified 2026-10-11 on `main` `1ce6ce5`, worktree `D:\workspace\DotExpress-f12`, `HEAD:client` `a64da653`)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`. The spec's probes ran on the worktree's sources in the session scratchpad (`...\scratchpad\f12spec\`, `scan.py`, `scan2.py`, `probe1.py`, `probe2.py`, a `msgmerge` probe) and are not committed. No test suite was run for this spec (the machine was busy); the baselines below come from the F-9 and F-11 records: `1ce6ce5` gives `Ran 1483`, `FAILED (errors=1, skipped=7)` (F-W6 only); the F-11 branch after its review fix gives `Ran 1564`, `OK (skipped=6)`. The catalog on `1ce6ce5` has 369 msgids, on the F-11 branch 381.

### How messages are localized today

- `_` is `gettext` of the bundled zh_TW catalog (`i18n.py`); `N_` only marks a string for `xgettext` (`scripts\generate-pot.bat` uses `--keyword=_ --keyword=N_`).
- Several sites translate a value at display time with `_(value)`: `_(result.summary_template)` and `_(result.summary_title)` (`documents/export_coordinator.py:205-206`), `_(get_public_error_message(error.error))` (`ui/conversion_presenter.py:124`), `_(str(error))` for a text processing `ValueError` (`settings/dialogs.py:158`), `NameDialogMessages.message_for` (`ui/dialog_base.py:44-49`), `_(label)` of menu items (`gui.py:260`), `_(option.label)` in the settings dialog, `_(CSV_WILDCARD)` (`dialog.py:773`, `785`). This works only when the value is a msgid, that is when it was marked with `N_` where it is defined. **The values that were never marked stay English.** That is the root of P1-4 defect 4.
- `gui.py:315` `self.SetTitle(_(format_window_title(name)))` passes a formatted title (`"alpha - DotExpress"`) to `_`. That is a misuse: it is not a msgid, so it returns unchanged, but a document whose title happened to equal a msgid would be "translated".

### Inventory of user-visible English text (AST scan of every non-test module for string literals outside `_()`/`N_()`, then each hit traced to where it is shown)

| # | Text (today) | Defined at (`1ce6ce5`) | Where the user sees it | Decision |
| --- | --- | --- | --- | --- |
| E1 | `All documents were exported successfully.`, `Export Complete with Errors`, `Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}` | `documents/export_results.py:6-14` (plain constants) | Export All summary box (`export_coordinator.py:204-210`); the F-9 GUI record shows it in English | D1 |
| E2 | `An unknown error occurred.`, `The selected translation table could not translate this text.` | `conversion/plain_text.py:4-6` | after `轉譯失敗：` / `文字處理失敗：` | D2 |
| E3 | `Document "{name}" already exists.` (f-string), `Unsupported import file type: ".x".`, `Text document must use the .txt extension.`, `Source document must use the .x extension.`, `Document package must ...` (3), `Encrypted PDF cannot be imported.`, `EPUB does not contain a readable spine.`, `EPUB spine item "x" is missing.`, `Name cannot exceed 32 characters.` / `Name contains invalid characters.` / ..., raw `UnicodeDecodeError` and `OSError` texts | `documents/workspace.py:250-281`, `441`, `447`; `documents/importers/base.py:18`, `epub_importer.py:18`, `26`, `pdf_importer.py:270`, `284`; `shared/name_validation.py:71-82`; `workspace_service.py:241` (`str(exc)`) | the Import Issues dialog, one line per skipped file (`gui.py:583-590`, `940-946`) | D3 |
| E4 | `CSV must contain columns: text, braille, type`, `CSV must contain header row.`, raw `UnicodeDecodeError` / `PermissionError` / `csv.Error` | `conversion/text/dictionary_rules.py:156-174` and the `open`/read in `from_paths` | `轉譯失敗：...` after Convert, a single export, or an Export All summary line (F-6 O5) | D4 |
| E5 | `HTML files (*.html)|*.html` | `documents/formats.py:189` (left unmarked on purpose in W-3 "to add no catalog entry") | the file type list of the HTML export save dialog | D8 |
| E6 | `No conversion data is available for this document.` (default argument) | `dual_view/html.py:39`, used by `documents/formats.py:109` | the exported Dual View HTML file of a document without conversion data (the in-app Dual View already passes the translated text, `gui.py:327-330`) | D8 |
| E7 | `No supported browser or system HTML opener is available.` | `dual_view/browser.py:103` | `無法開啟雙視檢視：{error}` | D8 |
| E8 | `main is not callable.`, `main must return str, got {type}.` | `conversion/preprocessing/user_script.py:75`, `78` | `文字處理失敗：...` (a script that returns `None` is the realistic case); the two validation messages next to them are already `N_` | D8 |

Checked and left as they are (not user-visible, or not reachable through the UI):

- Log lines (`config.py`, `ui/conversion_presenter.py` discard reasons, `dotexpress.*` loggers) and `ValueError`/`TypeError` texts of internal invariants (`dialog.py:608`, `entry_list_model.py:112`, `162`, `dual_view/model.py`, `markdown_ast.py`, `markdown_renderer.py`, `menu_builder.py:36`, `settings/dialogs.py:209`, `745`, `alignment.py`, `zhuyin.py:68`).
- `conversion/text/pipeline.py:121` `assert ..., "No translatable text segments were found."`: raised only for an empty text segment, which the service never passes (probe 4).
- `dictionaries/manager.py:82`, `93`, `103`, `108`, `130` and `dictionaries/actions.py:39`: the name prompt reports duplicates with the localized `字典「X」已存在。`, and the default dictionary is guarded before these are reached (`presenter.py:113-116`, `137-139`).
- `documents/workspace_service.py:252` (rename to the same name; `gui.py:844` returns first), `shared/atomic_write.py:52`, `app_paths.py:29` (the startup box shows its own localized text and `error.cause`), `adapters/translation/provider.py` (Windows-only runtime messages, logged).
- Tagged-PDF `ValueError`s (`pdf_importer.py:80-262`): caught inside `import_pdf`, which falls back to plain text (`:286-291`).
- Standard buttons: `message_box` and `localize_standard_buttons` already set translated labels (F-7, F-W9).

### Probes (scratchpad, `1ce6ce5`)

1. **Import Issues reasons** (`batch_import_documents` on real files, `format_key="all"`, `alpha` listed):

   ```text
   alpha.txt: Document "alpha" already exists.
   bad.docx:  File is not a zip file
   bad.epub:  'Bad Zip file'
   bad.pdf:   Stream has ended unexpectedly
   big5.txt:  'utf-8' codec can't decode byte 0xa4 in position 0: invalid start byte
   con.txt:   Name contains invalid characters.
   foo.xyz:   Unsupported import file type: ".xyz".
   xxxx...(40).txt: Name cannot exceed 32 characters.
   ```

   A Big5 `.txt` is common in Taiwan, so the raw `UnicodeDecodeError` is the most likely of these.
2. **Conversion with an unreadable dictionary** (`format_conversion_error` of what `from_paths` raises):

   ```text
   Big5 CSV:            轉譯失敗：'utf-8' codec can't decode byte 0xa4 in position 18: invalid start byte
   header Text,Braille,Type: 轉譯失敗：CSV must contain columns: text, braille, type
   0-byte file:         轉譯失敗：CSV must contain header row.
   PermissionError:     轉譯失敗：[Errno 13] Permission denied: '...'
   ```

   A NUL byte and an unclosed quote do not raise in Python 3.13's `csv`; a field over `csv.field_size_limit()` raises `csv.Error`. Dictionary Management counts a header-less file as readable with 0 entries (F-6), while conversion fails on it.
3. **`msgmerge` revives obsolete entries exactly.** A `.po` with `#~ msgid "All documents were exported successfully."` merged with a template that has the msgid again gives the active entry with its old msgstr, not fuzzy. The catalog still holds, as obsolete entries, the zh_TW translations of E1 (`.po:1697-1710`) and of `Imported file must be a valid DotExpress DEP package.` (`.po`, obsolete block).
4. **The pipeline assertion is unreachable**: `translate_plain_text_segment("")` raises it; `parse_inline_math_segments` never yields an empty text segment, and an empty text returns before translation.
5. **Name check** (`gui.py:711-735`): `document_name_exists(...) or package_name_taken(...)` shows the same `文件「{name}」已存在。` for both. `package_name_taken` is `os.path.lexists(<workspace>/<name>.dep)` (`workspace_service.py:123-132`): an invalid package kept at startup, a folder, a broken link, or a valid package copied in while the app runs all count, in any spelling on NTFS. Import puts the stems of every `*.dep` on disk into `existing_names` (`workspace_service.py:223-228`), so such a name gets the English `Document "X" already exists.`.
6. **Settings that cannot be saved** (`config.py:162-185`): a `config.json` that exists but cannot be read (`_UnreadableConfig` with an `OSError`) is never written; a damaged one is copied to `config.json.bak` first, and if that copy fails nothing is written; any write error is logged. In all three cases `_save` returns `None` and the setters return `None`; only `config.log` gets a line. The frame keeps the changed values in memory (`translation_settings`, `translation_tables`, `view_settings`), so they apply until the app closes. The frame's save sites are `apply_settings_from_dialog` (`gui.py:421-438`, three saves), `_set_view_font_size` (`:592-600`, Ctrl+wheel and the settings dialog's font size) and `_set_active_dictionary` (`:440-446`, Dictionary Management rename and delete through the presenter). `get_or_create_client_id` and `set_lang(persist=True)` also save; the first runs on the client-init background thread (`client_init.py:164-173`).
7. **A failed manual conversion** (`ui/conversion_presenter.py:266-279`): `message = format_conversion_error(...)`; a manual job always gets `show_error(message, "Error")`, whichever document is open. The job knows its target (`_ManualTarget.document_name`, F-9 D1). A single export's `on_error` (`export_coordinator.py:113`) shows the message the same way.

## Decisions

**D1. The Export All summary is localized (E1).**

- `documents/export_results.py` marks the four constants with `N_` (`EXPORT_COMPLETE_TITLE` is already a msgid through `export_coordinator.py:137`; marking it adds no msgid). `_show_batch_result` keeps translating them at display time.
- The three texts come back from the obsolete catalog entries with their old translations (probe 3): strings 1-3.
- The failure lines inside the summary keep the form `{document}: {reason}`; their reasons are the conversion messages (D2, D4, D7 does not apply here) or a raw write error.

**D2. The conversion fallback texts are msgids (E2).**

`conversion/plain_text.py` marks both texts with `N_`. `format_conversion_error` already translates the result of `get_public_error_message`. Strings 4 and 5.

**D3. Import problem reasons are localized (E3).**

- A new `documents/import_problems.py` (no wx) holds `describe_import_problem(error, format_key) -> str`, used for every Import Issues line:

  | Cause | Reason shown |
  | --- | --- |
  | `UnicodeDecodeError` (a `.txt` not in UTF-8) | string 10 |
  | `PermissionError` (locked, no permission) | the existing F-6 CANNOT_OPEN text `無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。` |
  | `NameValidationError` (file name not usable as a document name) | the existing document name messages: `too_long` and `empty` -> `文件名稱長度需為 1 到 32 個字元。`, `invalid` -> `文件名稱不是有效的 Windows 檔名。` |
  | `ImportProblem` (new, raised by DotExpress's own loaders) | its msgid, translated (strings 11-15) |
  | any other error while loading a `dep` | string 13 (the revived `匯入的檔案必須是有效的 DotExpress DEP 封裝檔。`): a damaged zip, a missing member, bad JSON |
  | anything else | the existing `無法讀取檔案：{error}` with the raw text (F-6 OTHER) |

- `ImportProblem(ValueError)` (in `documents/importers/base.py`) carries an `N_`-marked msgid; `str()` stays the English text, so logs and `except ValueError` keep working. It replaces the plain `ValueError`s of: unsupported file type (`workspace.py:441`, string 11), extension mismatch (`load_text_document`, `validate_source`; string 12), the three package structure errors (`load_document_package`; string 13), encrypted PDF (both places; string 14), and both EPUB errors (string 15, one text for both; the spine item id means nothing to a user).
- A listed duplicate gets the existing `文件「{name}」已存在。` through `_()`; a name held only on disk gets string 18 (D5).
- A failed write of the imported package (`workspace_service.py:241`) gets the existing `儲存文件失敗：{error}`.
- The lines keep the form `{file name}: {reason}`, so strings 11 and 12 need no file name of their own.
- Why one function and not `_(str(exc))` everywhere: `UnicodeDecodeError`, `PermissionError` and the name errors need a mapping anyway, and one place makes the reasons testable without wx.

**D4. A conversion that cannot read the selected dictionary says so (E4, F-6 O5).**

- `LoadedDictionaryRules.from_paths` reads the **dictionary** file (open, header check, all rows) inside one guarded block and raises a new `DictionaryRulesReadError(path, error)` when that fails with `UnicodeDecodeError`, `OSError`, `csv.Error`, or a header without `text`, `braille`, `type` (including an empty file). The rows are processed after the block, so an error in processing (F-11 D13/D14, alignment) is not reported as "cannot be read". The bundled `Bopomofo2Braille.csv` is not guarded: its failure is a broken installation, and the message stays as it is. `dictionary_rules.py` still imports nothing from `dictionaries`.
- `format_conversion_error` recognises a `ConversionStageError` whose `error` is a `DictionaryRulesReadError` and builds `轉譯失敗：` + string 16, `Dictionary "{name}" cannot be read. {reason}`, with `{name}` the file stem and `{reason}`:
  - the header case: string 17 (same words as F-11's string 12);
  - otherwise `describe_dictionary_read_error(cause)` (F-6: NOT_UTF8, CANNOT_OPEN, INVALID_CSV, OTHER).
- **One line, not F-6's two-paragraph form**, because the same text is a line of the Export All summary (`{document}: {reason}`). Example: `轉譯失敗：無法讀取字典「big5dict」。檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。`
- It applies to Convert, a single export and every Export All step, because all of them go through `format_conversion_error`.
- No new log line: the box names the file and the reason, and F-9 D7 logs only unexpected worker errors. Decided by orchestrator with the recommended default; user may override before merge (O3).
- A dictionary that does not exist still converts with no rules, as today.

**D5. A name held by a file that is not listed gets its own message (F-8a review).**

- `DocumentWorkspaceService.unlisted_package_entry(name) -> str | None` returns the on-disk name of the entry that holds `name` (for example `bad.dep` when the user typed `BAD`), found by listing the workspace folder and comparing with `casefold`; `None` when no entry holds it. When `package_name_taken` is true but the listing finds nothing (a race), the entry is `"{name}.dep"`.
- `_prompt_for_document_name` (Add and Rename): the listed check runs **first** and keeps `文件「{name}」已存在。`. Only when the name is free in the list but taken on disk, the box (caption `錯誤`, `wx.OK | wx.ICON_ERROR`) shows string 18, a blank line, then string 19 with the workspace folder path. The name dialog then reappears with the name prefilled, as today.
- Import: `batch_import_documents` gets the unlisted entries separately from the listed names, and a document whose name only an unlisted entry holds gets string 18 as its reason (without string 19; the Import Issues dialog lists files, and the path would repeat on every line).
- `free_document_name` (the default document) is unchanged: it picks `new (2)` silently.
- The wording names no cause (an invalid package kept at startup is the usual one, but a folder or a copied-in package hold names too) and tells the user what to do.

**D6. The first settings change that cannot be saved shows a warning (F-8a review M-7).**

- `ConfigStore._save` returns a `ConfigSaveProblem | None` (a frozen dataclass: `kind` one of `UNREADABLE`, `BACKUP_FAILED`, `WRITE_FAILED`; `error`; `path`; for `BACKUP_FAILED` also `backup_path`). The public setters that `_save` serves return it (they return `None` today, so no caller breaks). `save_translation_settings`, `save_translation_tables` and `save_view_settings` return the first problem of their setters. The log lines, the skip and the backup rules of F-8 D11 do not change.
- `get_or_create_client_id` and `set_lang` ignore the result: they are not settings the user changed, and the first one runs on a background thread.
- The frame's three save sites (`apply_settings_from_dialog`, `_set_view_font_size`, `_set_active_dictionary`) pass the result to `_report_settings_save_problem(problem)`. The first problem of the session shows one box; later ones show nothing (the flag lives on the frame). Decided by orchestrator with the recommended default; user may override before merge (Q1 asks the user).
- The box: `message_box`, caption string 20 `設定未儲存`, `wx.OK | wx.ICON_WARNING`, message string 21 with `{path}` the full `config.json` path and `{reason}`:
  - `UNREADABLE`: the existing CANNOT_OPEN text;
  - `BACKUP_FAILED`: string 22 with the `.bak` path and the error;
  - `WRITE_FAILED`: the error text as is.
- Parent: the active window of the app when the box is shown (the settings dialog after Apply, Dictionary Management after a rename), else the frame. The box is shown synchronously at the end of the save site, after the in-memory change, so the change still applies.
- Why once per session: Ctrl+wheel saves on every notch; a box on each would stop the user. The message says the later changes are not kept either and that it will not appear again until the next start.

**D7. A failed conversion names its document when that document is not open (F-9 review M-9; U2).**

- Manual conversion: in `_on_job_failure`, when the job's target is a document (`_ManualTarget.document_name` is not `None`) and it differs from `documents.open_document_name` at delivery, the message is string 23, `Document "{name}" could not be converted.\n\n{error}`, with `{error}` the message of today (`轉譯失敗：...` or `文字處理失敗：...`). Caption `錯誤`, as today.
- Single export (File > Export, Ctrl+S): the coordinator's `on_error` applies the same rule with the exported document's name and the open document at delivery. Exporting the selected document while another one is open is enough for the name to appear; that is intended, since the box does not otherwise say which export failed.
- Unchanged: the job's document is open (the message of today); no document at start (no name to give); Export All (its summary already names each document); the missing-table message (shown before any conversion).
- The focus after the box is not changed (F-9 review M-6 moved it only after a successful case (b)); "Out of Scope".

**D8. The remaining English messages (E5-E8).**

- `HTML files (*.html)|*.html` is marked with `N_` (string 6, `HTML 檔 (*.html)|*.html`, following `點字檔 (*.brl)|*.brl`). The format label `HTML` stays as it is (like `ASCII`, `Unicode`).
- `documents/formats._write_html` passes `_("No conversion data is available for this document.")` (an existing msgid) as `empty_message`, as the in-app Dual View does.
- `dual_view/browser.py` raises its `OSError` with the translated string 7.
- `user_script.execute_preprocessing_script`: `main is not callable.` is raised with `_()` (string 8); `main must return str, got {type}.` is formatted from the translated string 9. Both are translated at raise time because the second one is formatted; `format_conversion_error`'s `_()` of an already translated text returns it unchanged.

**D9. `_()` misuse.**

- `gui._update_window_title` calls `SetTitle(format_window_title(name))` without `_()`. The title text does not change (`DotExpress` and `{name} - DotExpress` are kept as is, `AGENTS.md`).
- The display-time `_(value)` sites listed in "Current State" stay: each translates a value that is `N_`-marked where it is defined (D1 and D2 make the last two such values msgids).

Decided by orchestrator with the recommended default; user may override before merge (O7).

**D10. Strings and catalogs.**

- The 23 strings of the table below. `scripts\generate-pot.bat`, then `msgmerge`, then the msgstr values, then `msgfmt --check --statistics`: all translated, 0 fuzzy, 0 untranslated. `POT-Creation-Date` stays `2026-10-10 12:00+0800`.
- Strings 1, 2, 3 and 13 must come back from the obsolete entries with their old msgstr (probe 3); the plan checks that each one is active, not fuzzy, and that its `#~` copy is gone.
- Check that `msgmerge` does not fuzzy-match a new msgid to an old one. Likely pairs: 16 with `Dictionary "{name}" cannot be read.`, 18 with `Document "{name}" already exists.`, 23 with `Conversion completed. The result was saved to document "{name}".`, 20 with `Settings`, 6 with `Braille files (*.brl)|*.brl`, 17 with F-11's string 12. If it does, set the msgstr of the table and drop the `#, fuzzy` flag and the previous-msgid lines.

## Behavior per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Export All, all succeed | caption `匯出完成`, message `All documents were exported successfully.` | `所有文件皆已成功匯出。` (D1) |
| Export All, some fail | caption `Export Complete with Errors`, English counts | `匯出完成，但有錯誤`, `成功匯出的文件：N` ... (D1) |
| Conversion error with an empty text, or liblouis "Can't translate" | `轉譯失敗：An unknown error occurred.` / `...could not translate this text.` | `轉譯失敗：發生不明的錯誤。` / `轉譯失敗：選取的轉譯表無法轉譯這段文字。` (D2) |
| Import a Big5 `.txt` | `big5.txt: 'utf-8' codec can't decode ...` | `big5.txt: 檔案不是以 UTF-8 文字儲存。...` (D3) |
| Import a listed name | `alpha.txt: Document "alpha" already exists.` | `alpha.txt: 文件「alpha」已存在。` (D3) |
| Import a locked file | `[Errno 13] Permission denied: ...` | the CANNOT_OPEN text (D3) |
| Import a damaged `.dep` | `File is not a zip file` / `Document package names do not match.` | `匯入的檔案必須是有效的 DotExpress DEP 封裝檔。` (D3) |
| Convert with a Big5, locked, header-less or empty dictionary | `轉譯失敗：<Python text>` | `轉譯失敗：無法讀取字典「X」。<reason>` (D4) |
| Add or Rename to a name only an unlisted entry holds | `文件「BAD」已存在。` | string 18 naming `bad.dep`, string 19 with the workspace folder (D5) |
| Import a file whose name only an unlisted entry holds | `Document "bad" already exists.` | string 18 (D5) |
| Settings change that cannot be saved | nothing (log only) | first time in the session: the D6 warning; later: nothing |
| Manual conversion fails after switching to another document | `轉譯失敗：...` | `無法轉換文件「alpha」。` + blank line + `轉譯失敗：...` (D7) |
| Single export of a pending document that is not open fails | `轉譯失敗：...` | named as above (D7) |
| HTML export save dialog | `HTML files (*.html)` | `HTML 檔 (*.html)` (D8) |
| Exported HTML without conversion data | English sentence | `此文件沒有可顯示的轉換資料。` (D8) |
| Text processing script returns `None` | `文字處理失敗：main must return str, got NoneType.` | `文字處理失敗：main 必須傳回 str，而不是 NoneType。` (D8) |

## Design per File

### `client/documents/export_results.py` (4 spaces)

`N_` on the four constants (D1). Imports `N_` from `i18n`.

### `client/conversion/plain_text.py` (4 spaces)

`N_` on the two public texts (D2).

### `client/documents/importers/base.py`, `epub_importer.py`, `pdf_importer.py` (4 spaces)

`ImportProblem(ValueError)` in `base.py`; `validate_source`, the EPUB and the encrypted-PDF raises use it (D3).

### `client/documents/workspace.py` (4 spaces)

`load_text_document`, `load_document_package` and the unsupported-type raise use `ImportProblem`; `batch_import_documents` takes the unlisted entries separately and builds every reason with `describe_import_problem` (D3, D5). `load_workspace_documents` still treats every `ValueError` as an invalid package (`ImportProblem` is one).

### `client/documents/import_problems.py` (new, 4 spaces)

`describe_import_problem(error, format_key) -> str` (D3). Imports `_` from `i18n`. It writes the CANNOT_OPEN msgid literally instead of importing `dictionaries.read_problems` (documents do not depend on dictionaries); `xgettext` then lists one msgid with two references.

### `client/documents/workspace_service.py` (4 spaces)

`unlisted_package_entry(name)` (D5); `import_files` passes the unlisted entries and words a failed write with `儲存文件失敗：{error}` (D3).

### `client/conversion/text/dictionary_rules.py` (4 spaces)

`DictionaryRulesReadError(path, error)` with `header_not_recognized: bool`; the guarded read in `from_paths` (D4). Docstring updated.

### `client/ui/conversion_presenter.py` (4 spaces)

`format_conversion_error` maps `DictionaryRulesReadError` (D4); `_on_job_failure` names a manual job's document that is not open (D7). It may import `dictionaries.read_problems` (no wx); `test_module_imports_neither_wx_nor_gui` still holds.

### `client/documents/export_coordinator.py` (4 spaces)

The single export's `on_error` names a document that is not open (D7).

### `client/config.py`, `client/settings/translation.py`, `settings/translation_tables.py`, `settings/view.py` (4 spaces)

`ConfigSaveProblem`; `_save` and the setters return it; the three helpers return the first problem (D6).

### `client/gui.py` (tabs)

`_prompt_for_document_name` (D5), `_report_settings_save_problem` and its three callers (D6), `_update_window_title` without `_()` (D9).

### `client/documents/formats.py`, `client/dual_view/browser.py`, `client/conversion/preprocessing/user_script.py` (4 spaces)

D8.

### Catalogs

`client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `.mo` (D10).

### Not changed

`dialog.py`, `ui/message_box.py`, `dictionaries/*` (except being imported), `DictionaryEntriesDialog`, the F-11 boxes, `client/braille/`, every file of HANDOFF section 2's list, both fixtures.

## What Stays Identical

- Every message box's caption, icon, buttons and the moment it appears, except the new D6 box.
- The texts of every message not listed in "Behavior per Path".
- What is converted, exported, imported, saved or refused: only the words change (and the one D6 box).
- A listed duplicate name: `文件「{name}」已存在。`.
- `config.json` handling of F-8 D11, the log lines in `config.log` and `gui.log`.
- Export All: the order of steps, the `{document}: {reason}` lines, the info/warning icon choice.
- `translation_golden.json` (`e67d95a1...`) and `dictionary_entries_trace.json` (`f493da52...`).

## User-Visible Strings

| # | msgid | zh_TW msgstr | Where |
| --- | --- | --- | --- |
| 1 | `Export Complete with Errors` | `匯出完成，但有錯誤` (revived) | D1 caption |
| 2 | `All documents were exported successfully.` | `所有文件皆已成功匯出。` (revived) | D1 |
| 3 | `Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}` | `成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}` (revived) | D1 |
| 4 | `An unknown error occurred.` | `發生不明的錯誤。` | D2 |
| 5 | `The selected translation table could not translate this text.` | `選取的轉譯表無法轉譯這段文字。` | D2 |
| 6 | `HTML files (*.html)|*.html` | `HTML 檔 (*.html)|*.html` | D8 |
| 7 | `No supported browser or system HTML opener is available.` | `找不到可用的瀏覽器，也沒有可開啟 HTML 檔的系統程式。` | D8 |
| 8 | `main is not callable.` | `main 不是可以呼叫的函式。` | D8 |
| 9 | `main must return str, got {type}.` | `main 必須傳回 str，而不是 {type}。` | D8 |
| 10 | `The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.` | `檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。` | D3 |
| 11 | `This file type cannot be imported.` | `無法匯入這種類型的檔案。` | D3 |
| 12 | `The file name extension does not match the selected file type.` | `副檔名與選取的檔案類型不符。` | D3 |
| 13 | `Imported file must be a valid DotExpress DEP package.` | `匯入的檔案必須是有效的 DotExpress DEP 封裝檔。` (revived) | D3 |
| 14 | `This PDF file is encrypted and cannot be imported.` | `這個 PDF 檔已加密，無法匯入。` | D3 |
| 15 | `The EPUB file is damaged or has no readable content.` | `EPUB 檔已損壞，或沒有可讀取的內容。` | D3 |
| 16 | `Dictionary "{name}" cannot be read. {reason}` | `無法讀取字典「{name}」。{reason}` | D4 |
| 17 | `Its header is not recognized. The first line of the file must contain the text, braille, and type headers.` | `無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。` | D4 |
| 18 | `The name "{name}" is used by "{file}" in the workspace folder, but that file is not in the document list.` | `名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清單中。` | D5 (box and Import) |
| 19 | `Choose another name, or move or delete that file. Workspace folder:\n{folder}` | `請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n{folder}` | D5 (box) |
| 20 | `Settings Not Saved` | `設定未儲存` | D6 caption |
| 21 | `DotExpress cannot save its settings to "{path}". Changes to the settings apply until DotExpress is closed, but they are not kept. This message is not shown again until DotExpress is started again.\n\n{reason}` | `DotExpress 無法將設定儲存到「{path}」。設定的變更在關閉 DotExpress 之前有效，但不會保留。在下次啟動 DotExpress 之前，不會再顯示這則訊息。\n\n{reason}` | D6 |
| 22 | `The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Details: {error}` | `檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}` | D6 |
| 23 | `Document "{name}" could not be converted.\n\n{error}` | `無法轉換文件「{name}」。\n\n{error}` | D7 |

msgids: 381 + 23 = **404** (4 of the 23 revived). The quoting follows `文件「{name}」已存在。`; "詳細資訊：" follows F-6's INVALID_CSV text; 工作區 follows `無效的工作區文件`; 轉換/轉譯 follow the existing catalog (轉換 for the operation, 轉譯 for liblouis' step).

Existing messages newly reachable:

- `文件「{name}」已存在。`, `文件名稱長度需為 1 到 32 個字元。`, `文件名稱不是有效的 Windows 檔名。`, `無法讀取檔案：{error}`, `儲存文件失敗：{error}` and the CANNOT_OPEN text as Import Issues reasons (D3);
- F-6's four reasons after string 16 (D4); the CANNOT_OPEN text as a D6 reason;
- `此文件沒有可顯示的轉換資料。` in exported HTML (D8).

## Accessibility (NVDA)

| Message | Kind | Read when it opens | Focus after |
| --- | --- | --- | --- |
| Export All summary (D1) | task dialog (`message_box`) | caption and the whole text (F-5, F-9 measurements) | as today (the main window) |
| Import Issues (D3, D5) | `FileIssuesDialog` | its message; each reason is one list line `{file}: {reason}` | as today |
| Conversion error (D2, D4, D7) | task dialog, caption `錯誤` | the whole text; D4 is one sentence pair after `轉譯失敗：`; D7 starts with the document name | as today (the focus is not moved, D7) |
| Name held by an unlisted entry (D5) | task dialog, caption `錯誤` | string 18, then string 19 and the path | the name dialog reappears with the name selected, as today |
| Settings not saved (D6) | task dialog, caption `設定未儲存`, warning icon | the whole text, with the path and the reason | the window that was active (the settings dialog or Dictionary Management), else the main window |

- The new texts put the actionable part (what to do) in the same box, so a screen reader user does not need `config.log` or the workspace folder listing to understand the problem.
- D4 and D7 keep the error in one box: no second box to dismiss.
- Long paths (D5, D6) come last in their box, so the sentence is heard before the path.
- Manual item 119 checks that NVDA reads the D4, D5, D6 and D7 boxes in full.

## Test Plan

TDD: each step's tests are written first and fail for the stated reason. Indentation follows each file (most tests here use 4 spaces; check each file). Temporary folders only. Tests that make the code log use `assertLogs` or isolate `dotexpress.gui` / `dotexpress.config`, so nothing reaches `client/log/`. Expected texts are built with `_()` and compared with the zh_TW msgstr where the test is about the catalog. Non-ASCII test data uses `\u` escapes where the file already does.

### A. Catalog (`tests/test_i18n.py`)

1. The 23 msgstr values of the table (subTests).
2. The AST msgid scan equals the catalog: 404.
3. A guard that `export_results.py`'s constants, `plain_text.py`'s texts and `formats.py`'s HTML filter are `N_` calls (AST).
4. A guard that `gui._update_window_title` contains no `_` call (AST; D9).

### B. Export All (`tests/test_export_coordinator.py`, `tests/test_gui_document_flows.py`)

1. **Flip** the four `KNOWN BUG (P1-4 spec, defect 4)` pins of the summary (`test_export_coordinator.py:148`, `547`; `test_gui_document_flows.py:4140`, `4171`): the success summary is `所有文件皆已成功匯出。` / `匯出完成`; the partial one has `匯出完成，但有錯誤` and the zh counts. Red: English.

### C. Conversion texts (`tests/test_conversion_presenter.py`, `tests/test_gui_document_flows.py`)

1. **Flip** `test_format_conversion_error_public_texts` and its frame twin (`:188`, `:3781`): zh fallbacks. Red.
2. D4: `format_conversion_error` of a `DictionaryRulesReadError` for NOT_UTF8, CANNOT_OPEN, INVALID_CSV, OTHER and the header case gives `轉譯失敗：無法讀取字典「d」。<reason>`, one line (no `\n`). Red.
3. D4 through the presenter: a manual failure shows it with caption `錯誤`; an export failure passes the same text to `on_error`; an Export All step lists it on one line.
4. D7: a manual job whose target is not open at delivery: string 23 with the target's name; target open (also after switching away and back): today's text; no document at start, one open now: today's text. Red for the first.
5. D7: a single export of a document that is not open at delivery: named; open: not named; Export All: lines unchanged.
6. D8: `execute_preprocessing_script` with a `main` returning `None`, and with `main` rebound to a non-callable after its definition: zh texts through `format_conversion_error`.

### D. Dictionary rules (`tests/test_conversion_text_dictionary_rules.py`)

1. `from_paths` raises `DictionaryRulesReadError` (with the path and the cause) for: a Big5 file, a `PermissionError` (patched `open` for the dictionary path), a field over `csv.field_size_limit()`, the header `Text,Braille,Type`, a 0-byte file (`header_not_recognized` true for the last two). Red.
2. A bundled Bopomofo file that cannot be read is **not** wrapped.
3. An error raised by `processing` or by the alignment of a row the file holds is not wrapped (inject a `processing` that raises something F-11 does not catch, or a row that fails alignment).
4. A missing dictionary still gives empty rules; every existing golden case is unchanged.

### E. Import (`tests/test_import_problems.py` new; `tests/test_documents_workspace*.py`; `tests/test_workspace_service.py`; `tests/test_gui_document_flows.py`)

1. `describe_import_problem` for each row of the D3 table, including a `dep` `BadZipFile`, a `KeyError` from a package without `.brl`, an encrypted PDF (built with `pypdf`'s writer `encrypt`, or a stubbed reader), an EPUB without spine.
2. `batch_import_documents`: the reasons of probe 1 become the zh texts; a listed duplicate gives `文件「alpha」已存在。`; an unlisted entry gives string 18 with the on-disk spelling.
3. `import_files`: a failed package write gives `儲存文件失敗：...`.
4. The frame's Import flow shows the zh lines in `FileIssuesDialog`.
5. `load_workspace_documents` still classifies a damaged package as invalid (`ImportProblem` is a `ValueError`).

### F. Name check (`tests/test_gui_document_flows.py`, `tests/test_workspace_service.py`)

1. Add `BAD` with an unlisted `bad.dep` (an invalid package, and a folder): the box has string 18 naming `bad.dep`, a blank line, string 19 with the workspace path; the dialog reappears with `BAD`. Red: `文件「BAD」已存在。`.
2. Rename to such a name: same.
3. A listed duplicate keeps `文件「alpha」已存在。` (also when an unlisted entry exists for another case of the same name, the listed check wins).
4. `unlisted_package_entry`: the on-disk spelling; `None` for a free name; the `"{name}.dep"` fallback when the listing misses it (patched `os.scandir`).

### G. Settings (`tests/test_config.py`, `tests/test_settings_*.py`, `tests/test_gui_*.py`)

1. `_save` / the setters return `UNREADABLE` (a `config.json` that raises `PermissionError` on read), `BACKUP_FAILED` (damaged JSON and a `config.json.bak` folder), `WRITE_FAILED` (an `os.replace` failure); `None` when the save works. The log lines and the file bytes are as before (the existing F-8 tests stay green). Red.
2. The three helpers return the first problem.
3. `get_or_create_client_id` and `set_lang(persist=True)` behave as before and return what they returned.
4. The frame: `apply_settings_from_dialog` with a problem shows the box once (exact caption, text with path and reason, `wx.ICON_WARNING`); a second call shows nothing; `_set_view_font_size` and `_set_active_dictionary` report through the same flag; no box without a problem. The in-memory settings change in every case.
5. The parent is the active window when there is one (patched `wx.GetActiveWindow`), else the frame.

### H. Remaining (`tests/test_dual_view_browser.py`, `tests/test_document_formats.py` or the module that tests `formats`)

1. `open_html_in_browser` without an opener raises an `OSError` whose text is string 7's msgstr.
2. The HTML export of a document without data contains `此文件沒有可顯示的轉換資料。`.
3. `get_format("html").export_wildcard` is the msgid and `build_export_wildcard(_)` shows `HTML 檔 (*.html)|*.html`.

### Mutation check (plan; each must be caught)

1. an `export_results` constant not marked (back to English);
2. `plain_text` texts not marked;
3. `UnicodeDecodeError` described by the generic text;
4. `PermissionError` described by the raw text;
5. the name codes `too_long` and `invalid` swapped;
6. an `ImportProblem` shown by `str()` (English);
7. a damaged `dep` described by the generic text;
8. the unlisted reason used for a listed duplicate (precedence reversed);
9. a failed package write shown raw;
10. the Bopomofo file guarded too;
11. a processing error inside the guarded block;
12. the header case described as OTHER;
13. string 16 replaced by F-6's two-paragraph form (`\n` in an Export All line);
14. the D5 box shown for a listed name;
15. `{file}` taking the typed spelling;
16. `UNREADABLE` not returned;
17. `BACKUP_FAILED` not returned;
18. `WRITE_FAILED` not returned;
19. the once-per-session flag ignored;
20. the box shown for `get_or_create_client_id`;
21. the box shown after a good save;
22. `_set_view_font_size` not reporting;
23. `_set_active_dictionary` not reporting;
24. D7 naming the document when it is open;
25. D7 not naming it when it is not open;
26. D7's export rule taking the open document at request time;
27. Export All lines wrapped with string 23;
28. exported HTML with the English empty text;
29. the browser error untranslated;
30. a user script error untranslated;
31. `_()` back in `_update_window_title`.

### Counts

About 50 new tests and 6 flipped (A 4; B 4 flips; C 6 + 2 flips; D 4; E 5; F 4; G 5; H 3). The plan fixes the exact `Ran`. On Windows after F-11: `OK (skipped=6)`.

## Migration Steps (each step one green commit, red first)

1. `fix: translate the Export All summary and the conversion fallback texts (F-12, P1-4 defect 4)`: D1, D2; strings 1-5; tests A (part), B, C1.
2. `fix: explain why an imported file was skipped (F-12, P1-4 defect 4)`: D3; strings 10-15; tests E.
3. `fix: explain a conversion that cannot read the selected dictionary (F-12, F-6 O5)`: D4; strings 16, 17; tests C2, C3, D.
4. `fix: explain a document name held by a file that is not listed (F-12, F-8a)`: D5; strings 18, 19; tests F, E2 (unlisted part).
5. `fix: tell the user when settings cannot be saved (F-12, F-8a M-7)`: D6; strings 20-22; tests G.
6. `fix: name the document of a failed conversion that is not open (F-12, F-9 M-9)`: D7; string 23; tests C4, C5.
7. `fix: localize the remaining English messages and drop a misused _() (F-12)`: D8, D9; strings 6-9; tests C6, H, A3, A4.

Each step that adds strings regenerates the catalogs; the last step that moves lines above a msgid regenerates them again, so no `#:` reference is stale (F-9 "Corrected after planning" 2). The plan may merge steps 1 and 7 if that saves a catalog pass; the subjects then join. Each commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and stages explicit paths only.

## Acceptance Criteria

Run on Windows from `client/` with `$PY`, with the runtime copied as in F-3 plan Task 0.

1. Full suite: no failure and no error; `Ran` as the plan states.
2. Focused: `$PY -m unittest tests.test_i18n tests.test_export_coordinator tests.test_conversion_presenter tests.test_conversion_text_dictionary_rules tests.test_import_problems tests.test_workspace_service tests.test_config tests.test_gui_document_flows -v` (plus the modules the plan names for G and H) passes.
3. `grep -rn "KNOWN BUG (P1-4 spec, defect 4)" client/tests` prints nothing.
4. Catalogs: 23 new msgids (4 revived) with the msgstr of the table; `msgfmt --check --statistics` all translated, 0 fuzzy; the AST scan equals the catalog (404); `POT-Creation-Date` unchanged; the four revived entries have no `#~` copy left.
5. Both fixture sha256 values unchanged.
6. App data untouched: the main checkout's `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` have the same sha256 before and after; the worktree gets no `client/log/`, `client/workspace/` or `client/config.json`.
7. `git diff main --stat` touches only the files of "Design per File", the tests, and the spec, plan and history files.
8. The mutation check above.
9. The packaged GUI verification below, with results in the implementation's history folder.

## Windows Verification (packaged build)

Build and process rules as in F-11:

- the main checkout's `client\.venv\Scripts` first on `PATH`, then `scripts\build-dotexpress.bat`;
- check in `PYZ-00.toc` that the changed modules come from the worktree;
- the exe goes to `D:\dxtest\N-f12\`; "Before" is the build of `main` after F-11 (the plan names it);
- each item runs in a new `D:\dxtest\auto<item>-f12` folder with a copy of the exe; only processes under those folders are ended (`taskkill /T`);
- **fix** items run on both builds (the expected text differs); **regression** items run on `N-f12` only, and on the before build too only when they miss their expectation (user, 2026-10-11);
- scripts reuse `2026-10-09-03-windows-verification/auto/` (`dx.py`, `docs.py`, `dicts.py`, `lock.py`) and `2026-10-10-01-f5-save-failure-handling/auto/f5gui.py` without editing; task dialogs are read through UIA; **no script reads or writes the clipboard** (text goes in with `set_edit_text` or typed keys); config, dictionary and workspace files are written by the script before launch.

| # | Class | Steps | Expected after F-12 | Before |
| --- | --- | --- | --- | --- |
| 109 | fix | Three converted documents; File > Export All > BRL to an empty folder | the box `匯出完成` / `所有文件皆已成功匯出。`; three files | `All documents were exported successfully.` |
| 110 | fix | As 109, with `beta.brl` already in the folder and held share-none by `lock.py` (answer the overwrite question Yes) | `匯出完成，但有錯誤` / `成功匯出的文件：2` / `匯出失敗的文件：1` / `beta: <OS text>` | English caption and counts |
| 111 | fix | Import, "All supported" filter, typing the paths of: `alpha.txt` (listed), `big5.txt`, a 40-character `.txt`, `locked.txt` (share-none), `broken.dep` (not a zip), `foo.xyz` | Import Issues lines: `文件「alpha」已存在。`, string 10, `文件名稱長度需為 1 到 32 個字元。`, the CANNOT_OPEN text, string 13, string 11 | the English lines of probe 1 |
| 112 | fix | `config.json` selects `big5dict` (Big5 CSV); Convert a short text. Then the same with `caps` (`Text,Braille,Type`), with `empty` (0 bytes), and with a readable dictionary held share-none. Then Export All (BRL) of two pending documents with `big5dict` | each Convert: `轉譯失敗：無法讀取字典「<name>」。<reason>` with NOT_UTF8, string 17 (twice), CANNOT_OPEN; Export All summary: one line per document with the same text | `轉譯失敗：'utf-8' codec ...`, `CSV must contain ...`, `[Errno 13] ...` |
| 113 | fix | Workspace `alpha.dep` (valid) and `bad.dep` (invalid, kept at startup: Keep Invalid Files). Add `BAD`; Rename `alpha` to `bad`; Import `bad.txt` | Add and Rename: the box with string 18 naming `bad.dep` and string 19 with the workspace path; the name dialog back with the name; Import: `bad.txt: ` + string 18; files unchanged | `文件「BAD」已存在。`; `Document "bad" already exists.` |
| 114 | fix | (a) `config.json` held share-none by `lock.py` after the start, before pressing OK (held from before the start, the app does not start; F-8's startup check); Settings: change the conversion width, OK; then Ctrl+wheel in the source editor. (b) `config.json` = `{` and a folder `config.json.bak`; Settings: change the width, Apply, then OK | (a) after OK one box: `設定未儲存`, string 21 with the path, CANNOT_OPEN reason; no box after Ctrl+wheel; the font size changes on screen; `config.json` bytes unchanged. (b) after Apply the box with string 22 owned by the settings dialog; nothing after OK; `config.json` still `{` | no box |
| 115 | fix | `preprocessing.py` in the dictionary folder: `def main(input):` sleeps 5 s, then raises `ValueError("boom")`. (a) open `alpha`, Ctrl+Enter, Ctrl+Tab at once to `beta`; wait. (b) open `alpha`, select `beta` (pending) in the list, File > Export > BRL; wait. (c) as (a) without Ctrl+Tab | (a) `錯誤` box `無法轉換文件「alpha」。` + blank line + `文字處理失敗：boom`; (b) the same naming `beta`; (c) `文字處理失敗：boom` alone | (a), (b) `文字處理失敗：boom` alone; (c) identical |
| 116 | fix | Default document `new` (no conversion data): File > Export > Dual View HTML; read the save dialog's file type list; save | the type list shows `HTML 檔 (*.html)`; the file contains `此文件沒有可顯示的轉換資料。` | `HTML files (*.html)`; the English sentence |
| 117 | fix | `preprocessing.py` whose `main` returns `None`; Convert | `文字處理失敗：main 必須傳回 str，而不是 NoneType。` | `...main must return str, got NoneType.` |
| 118 | regression | (a) Convert with a readable dictionary: `轉換完成。` (b) Add `alpha` while `alpha` is listed: `文件「alpha」已存在。` (c) Settings OK with a writable `config.json`: no box, the file updated. (d) The F-9 case (b) success box after Ctrl+Tab still reads `轉換完成。結果已儲存到文件「alpha」。` | as listed | (only if a result misses) |

Never trigger a real logoff or shutdown; no item needs one.

**Manual for the user (item 119, NVDA):** with `N-f12` and NVDA running, listen to the boxes of items 112 (one case), 113 (Add), 114 (a) and 115 (a): is the whole text read, including the document or dictionary name and the path; does Esc close each box; where is the focus afterwards.

## Risks

- **Revived catalog entries** (low). If `msgmerge` did not revive one of strings 1-3 or 13, its msgstr must be filled from the table. The acceptance criterion checks it.
- **Fuzzy matches** (low). `msgmerge` may pair a new msgid with an old one (D10 lists the likely pairs). The plan checks each new entry.
- **`ImportProblem` is a `ValueError`** (low). Code that catches `ValueError` keeps working; `load_workspace_documents` still marks a damaged package invalid (test E5).
- **The guarded read of the dictionary** (low). Reading all rows before processing them changes nothing observable (the file is small and read once per conversion, `DictionaryRulesLoader`), but a wrong block boundary could report a processing error as "cannot be read" (mutant 11) or miss one (D1-D3 tests).
- **Setters with a return value** (low). Callers that ignore it are unaffected; the client-init thread's save ignores it on purpose.
- **A warning box during Ctrl+wheel** (low, intended once). The first wheel notch that cannot be saved opens a modal box; later notches do not. Q1 lets the user choose another trigger.
- **F-11 rebase** (medium, mechanical). `dictionary_rules.py` and `gui.py` are changed by both; everything is named by function, and the plan starts from the post-F-11 `main`.
- **Longer Import Issues lines** (low). Some reasons are two sentences; the dialog's list shows one line per file and scrolls horizontally as today.

## Open Questions

**Decided by the user (2026-10-11):** U1 (text messages only, candidates 1-4), U2 (F-9 M-9 in scope), U3 (the excluded items).

**Decided by orchestrator with the recommended default; user may override before merge:**

- **O1.** Import reasons reuse existing texts where they fit (the document name messages, CANNOT_OPEN, `無法讀取檔案：{error}`, `儲存文件失敗：{error}`) instead of new ones (D3).
- **O2.** Both EPUB errors share one text (string 15); the spine item id is dropped (D3).
- **O3.** A dictionary read failure during conversion is not logged (D4).
- **O4.** The D4 message is one line (string 16) rather than F-6's headline, blank line, reason, because it is also an Export All summary line (D4).
- **O5.** The bundled Bopomofo file is not covered by D4 (D4).
- **O6.** Import shows string 18 without the folder line (D5).
- **O7.** `_()` is removed from the window title; the display-time `_(value)` sites stay (D9).
- **O8.** The settings warning is shown synchronously at the save site, parented to the active window (D6).
- **O9.** D7 also covers a single export of a document that is not open; Export All keeps its per-document lines (D7).
- **O10.** The text processing script errors (strings 8, 9) are localized, although their reader is the script's author, for consistency with the two validation messages already in the catalog (D8).

**Questions for the user** (not blocking; the spec is written with the recommended option):

- **Q1. When does the settings warning appear?** (a) **Recommended:** once per session, at the first save that fails, from any of the three sites (D6). (b) Only after Settings OK/Apply (never from Ctrl+wheel or a dictionary rename), once per session. (c) Every time a save fails.
- **Q2. A damaged `config.json` that DotExpress replaces** (it is copied to `config.json.bak` first, F-8 D11) is also silent today: the user's earlier settings are back to defaults and only `config.log` says why. Tell the user? (a) **Recommended:** not in F-12; a follow-up (it is not a save failure, and nothing is lost: the `.bak` holds the file). (b) Add one more box (one more string) in F-12, using D6's mechanism.
- **Q3. Wording.** The 23 msgstr values of the table, especially 10, 18/19, 21 and 23. Recommended: as written; changes are one-line catalog edits.

## User-Visible Defaults Introduced by This Spec (not decided by the user)

Each one is a one-line change if the user prefers otherwise:

1. **The texts and captions** of strings 1-23 (the four revived ones keep their old translations).
2. **The D4 message is one line**, `轉譯失敗：無法讀取字典「X」。<reason>`, and an empty (0-byte) dictionary is described as a header that is not recognized.
3. **The D5 box names the on-disk entry** (`bad.dep`) and shows the workspace folder path; Import shows the sentence without the path.
4. **The listed check wins** over the unlisted one (a listed duplicate keeps `文件「X」已存在。`).
5. **The settings warning appears once per session**, at the first failed save from Settings, Ctrl+wheel or a dictionary rename (Q1), with a warning icon, parented to the active window.
6. **D7 names the document** for a single export of a document that is not open, not only for a manual conversion after a switch.
7. **Import reasons for unusable file names** reuse the document name dialog's texts (`文件名稱長度需為 1 到 32 個字元。` also for an empty name).
8. **The HTML save filter** is `HTML 檔 (*.html)|*.html`; the label `HTML` stays English.
9. **Exported HTML** without conversion data shows the zh sentence (its `<html lang="en">` attribute is unchanged; see "Out of Scope").

## Out of Scope / Follow-ups

Excluded by the user (U3), no design here:

- **Startup boxes owned by a frame not yet shown** (F-8b review M-8): `已復原文件`, `已取代字元` and the invalid-files dialog appear before `Show()`; NVDA and Alt+Tab reachability is manual item 83.
- **`WM_ENDSESSION` during a conversion** sometimes ends with `0xC0000374` (F-9 review M-8): `BrailleApp.OnExit` -> `runtime.close()` while the worker is in liblouis (hypothesis); the cheap mitigation is to skip `runtime.close()` while a conversion thread is alive.
- **Export `.tmp` left when a scanner holds the file** (F-7/F-8a): automatic retry.
- **Case-insensitive dictionary headers** (`Text,Braille,Type`; F-11 review M-1 follow-up): would change both the editor loader and conversion; D4 and F-11's string 12 explain the header meanwhile.
- **Delete All rollback** (P1-3 defect 4): the title is not updated and no default document is created when nothing valid remains (`gui.py:903-910`; pinned by `test_delete_all_failure_without_valid_document_clears_editors_only`).
- **F-W5**: `scripts/tests/test_vendor_helper_snapshot.py` compares `read_bytes()` of an autocrlf CRLF checkout with LF text; a newline-normalized comparison in the test fixes it.

Found while writing this spec, not text messages or not asked for:

- **Focus after the D7 box** stays in the read-only Braille Result editor after a switch (F-9 review M-6 moved it only after a successful case (b)).
- **The Dual View HTML says `<html lang="en">`** (`dual_view/html.py:51`) for Chinese content. With NVDA's automatic language switching this may pick an English voice. Not a message text; a follow-up (set the UI language, or omit `lang`).
- **A damaged `config.json` replaced silently** (Q2).
- **Raw OS and library texts** after a localized lead (`[Errno 13] ...`, `File is not a zip file`, MathCAT messages) and Python's `SyntaxError` text for a text processing script.
- **A failed case (b) save lost at close** (F-9 review M-5; F-5 scope).
- **Esc in the existing Yes/No confirmations** (F-11 "Out of Scope"; a dialog behaviour, not a text).
- F-10 (UEB line breaks, `$`).
