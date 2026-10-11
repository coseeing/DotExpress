# F-12 Localization Cleanup review record

- Date: 2026-10-11. Written in English at the orchestrator's request.
- Scope: worktree `D:\workspace\DotExpress-f12`, branch `fix/f12-localization-cleanup`, range `e0337df..HEAD` (HEAD `c1295df`; 12 commits: spec `4b74444`, plan `77f00a6`, seven localization commits `3c2eacf` `c05f262` `6838990` `17b5cf4` `66db33d` `40b206f` `611e618`, `cf8cada` Delete All rollback, `b52ac5c` F-W5, `c1295df` GUI record). Production diff: 19 files under `client/` (400 insertions, 113 deletions) plus the two catalogs.
- Read against: the spec and its corrections 1-18, the plan (Spec Corrections, Implementation Notes 1-6), `auto-results.md`, HANDOFF sections 1-2, `AGENTS.md`.
- Method: every production diff read line by line with the code around it; a scan of all message boxes, `show_*` calls and dialog labels for text outside `_()`/`N_()`; an AST scan of the client for `_()` at import time and for non-literal `_()`; a catalog check of the compiled `.mo`; 18 mutants on a scratch copy; the full suite.
- This record is written to disk only, not committed. No repo file was modified; no GUI was run; the clipboard was not touched.

## Verification (Windows 11 26200, `$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`, `$SP` = session scratchpad `f12review\`)

| Item | Command | Result |
| --- | --- | --- |
| full suite | `cd D:\workspace\DotExpress-f12\client && $PY -B -X utf8 -m unittest discover -s tests` (free memory 1.2 GB before) | `Ran 1627 tests`, `OK (skipped=6)`, as expected |
| F-W5 module | `$PY -B -X utf8 -m unittest scripts.tests.test_vendor_helper_snapshot` from the worktree root | `Ran 1 test`, `OK`; `git show HEAD:vendor/nvda/liblouis/runtime/louis_helper.py` has 0 CR bytes, so the snapshot is LF in the repository and the test hides nothing |
| compiled catalog | `msgfmt --statistics -c -o $SP/fresh.mo client/locales/zh_TW/LC_MESSAGES/dotexpress.po`; `cmp` with the committed `.mo` | 404 translated, 0 fuzzy, 0 untranslated; byte-identical to the committed `.mo` |
| placeholders | `$SP\po.py` over the compiled catalog (405 keys with the header) | every `{...}` set equal between msgid and msgstr; same newline count and trailing-newline state; the only msgstr equal to msgid are `ASCII`, `DOCX`, `DotExpress`, `EPUB`, `SimBraille`, `Unicode` (intended) |
| flags and dates | `grep` of the `.po` diff, `POT-Creation-Date` in both text catalogs | the new brace-format msgids carry `#, python-brace-format`; `POT-Creation-Date` is `2026-10-10 12:00+0800` in `.pot` and `.po`, unchanged by the range; `#~` entries 86 -> 68 |
| revived entries | the `.po` diff | the four revived msgids (Export Complete with Errors, All documents were exported successfully., Exported documents..., Imported file must be a valid DotExpress DEP package.) are active with their old msgstr; the obsolete `Text files (*.txt)|*.txt` is gone and unused (no `*.txt` wildcard remains in non-test code) |
| `_()` scan | `$SP\ast_scan.py` | no `_()` with an f-string or concatenation; the non-literal `_(x)` sites all translate an `N_`-marked value (`export_results`, `import_problems`, `plain_text`, `dialog_base`, `settings/dialogs`); the import-time `_()` calls (`about.py`, `dictionaries/entries.py`, `settings/dialogs.py` class bodies) are all pre-existing, none added in this range |
| mutants (18) | `$PY $SP\mut.py` (one edit per mutant on `$SP\work\client`, CRLF aware, restored after each) | all 18 caught, see section 2 |
| not run | - | GUI item 119 (NVDA, the user's); no packaged build run by me; the plan's 44 mutants and six shuffle seeds (replayed by the implementation) |

## Conclusion

**Ready to merge. No Critical finding and no Important finding.** The code does what the spec asks on every path I traced, the catalogs are exact, and the tests are strong (18 of 18 independent mutants caught). Seven Minor findings, all cheap, none blocking.

What I checked and found sound:

- D4: `_read_dictionary_rows` catches exactly `UnicodeDecodeError`, `OSError`, `csv.Error` around open, header check and `list(reader)`; row processing runs after the block, so a bug in `processing` or alignment is not reported as "cannot be read". The bundled Bopomofo file is read before it, unguarded. `DictionaryRulesReadError` derives from `Exception`, and no caller of `LoadedDictionaryRules` catches `ValueError` (grep), so nothing silently stopped catching it. A missing dictionary still gives empty rules.
- D5: the frame checks the list first (`document_name_exists`), then `unlisted_package_entry`, which is `None` exactly when `package_name_taken` is false (same `exclude_name` rule for Rename's own name in any case). Import checks listed names first, then unlisted ones (mutant M6 caught). The only path shown is the app's own workspace folder, in the box, not in the Import Issues lines. Add, Rename and Import all go through the same helper `unlisted_entry_reason`.
- D6: the flag is set before the box opens, so a second save during the modal box cannot recurse; once per session holds. `_save` returns before writing when the backup fails or the file is unreadable, and the atomic writer leaves the old file when the write fails, so `config.json` stays intact (GUI 114 (a), (b) confirm the bytes). The parent is the active window (the settings dialog) else the frame; the GUI record shows the box owned by the settings dialog. `save_translation_settings` calls all three setters (tuple, not an `or` chain; mutant M3 caught).
- D7: manual job and single export both name the document only when it differs from the open one at delivery. A rename while a conversion runs is not possible (`set_conversion_busy` disables the menus and the list), so a stale old name cannot appear.
- P1-3 defect 4: after an incomplete Delete All with no valid document the title is updated, the editors cleared and `_ensure_open_document_exists` runs, which creates the default document through `free_document_name` (`new (2)` if `new.dep` is held). The review dialog runs before it, so no double creation; GUI 120 shows `new - DotExpress`, list `new`, one `new.dep`. Mutants M8 and M8b caught.
- F-W5: the fix only normalizes CRLF to LF on the runtime file; the expected text is built from a text-mode read (LF). A real content difference still fails.
- Accessibility: every new box has a caption and uses `message_box` (translated buttons); the long texts are structured as a first sentence, a blank line, then the detail or path, which the task dialog splits into main instruction and content (read back in the GUI record). Focus after the boxes is unchanged from the existing boxes. Item 119 (NVDA) is still the user's.

## 1. Findings

### Critical

None.

### Important

None.

### Minor

**M-1. A non-`ImportProblem` error while loading a `.dep` is reported as "must be a valid DEP package" and is not logged, so a real bug in the loader would look like a bad file.**
- Where: `client/documents/import_problems.py:41-43`, `client/documents/workspace.py` (`batch_import_documents`, the `except Exception` that builds the `BatchIssue`).
- Scenario: a future change makes `_read_package` raise a `TypeError` or `AttributeError` for a good package. Before F-12 the Import Issues line showed the raw text of the error (useful in a bug report); now it says `匯入的檔案必須是有效的 DotExpress DEP 封裝檔。`, the user blames the file, and nothing is in `log/gui.log` either. The same holds for the "cannot be read: {error}" lines of other formats, which are only shown, not logged. At startup an invalid package is kept, so the loss is a diagnosis, not data.
- Fix: in `batch_import_documents`, log every error that is not an `ImportProblem`, `OSError`, `UnicodeDecodeError` or `NameValidationError` with `exc_info` (as `log_dictionary_read_error` does for the dictionary reads), or narrow the `dep` branch to `zipfile.BadZipFile`, `KeyError`, `ValueError`, `RuntimeError`. Cheap.

**M-2. The "settings not saved" reason for an unreadable `config.json` always says "in use by another program, or no permission".**
- Where: `client/gui.py:466-470` (`ConfigSaveProblemKind.UNREADABLE` branch).
- Scenario: `config.json` is a folder (the unit tests use this), or the disk reports an I/O error: the error is an `OSError` but not a `PermissionError`, yet the box tells the user to "close the other program and try again". The statement is then wrong and the actual error is not shown.
- Fix: use the CANNOT_OPEN text only for `PermissionError`; otherwise use `_("The file cannot be read: {error}").format(error=problem.error)` (an existing msgid). Cheap, no new string.

**M-3. A damaged importer file of the other formats (DOCX, EPUB zip, PDF) still shows an English library text after the translated prefix.**
- Where: `client/documents/import_problems.py:49` (`_("The file cannot be read: {error}")`).
- Scenario: a truncated `.docx` or `.epub` gives `無法讀取檔案：File is not a zip file`, a broken PDF a pypdf message. The spec limits D3's "own words" to DEP, text, encrypted PDF and EPUB spine, so this is within scope, but a zh_TW user still meets English there, and the catalog check cannot see it because the text is not a msgid.
- Fix: map `zipfile.BadZipFile` (and a pypdf `PdfReadError` if that is cheap to import lazily) to a translated "The file is damaged or is not a {type} file" text for the docx, epub and pdf keys; or accept and list it under follow-ups in the spec. Small.

**M-4. Handover leftovers in the docs: the plan's step checkboxes are all unchecked, and the spec's Windows item 114 (a) still describes a setup that cannot run.**
- Where: `docs/superpowers/plans/2026-10-11-f12-localization-cleanup.md` (every `- [ ] **Step n` from line 117; 0 are `[x]`); `docs/superpowers/specs/2026-10-11-f12-localization-cleanup-design.md:502` and the plan's step 4 table (`config.json` held "from before the start"; also the spec says the font size changes, the plan says the width).
- Scenario: a later reader of the plan believes no task was done; a later agent repeating item 114 (a) from the spec gets an app that exits at start (F-8's startup check), which Implementation Notes 5(a) and `auto-results.md` already explain but the spec and plan tables still contradict. The Implementation Notes say this is a known leftover.
- Fix: tick the steps (or add one line saying the plan is a record replayed by tag, not ticked), and correct row 114 (a) in both spec files (English and zh-TW) and the plan to "held after the start, before OK". Cheap.

**M-5. The `ConfigSaveProblem` box shows the raw operating-system error for a failed write.**
- Where: `client/gui.py:472` (`reason = str(problem.error)` for `WRITE_FAILED`), also the `{error}` in the BACKUP_FAILED text.
- Scenario: the GUI record shows `[WinError 5] 存取被拒。: '<d>\\.config.json.bak.<rnd>.tmp' -> '<d>\\config.json.bak'` on a zh_TW Windows. On a non-localized Windows the user sees English OS text, and the temporary file name with a random part appears. It is accurate but noisy for NVDA users, who hear the whole name.
- Fix: optional; for `PermissionError` use the CANNOT_OPEN text, and keep the raw text only for other errors. Cheap, same fix as M-2.

**M-6. The once-per-session flag is never reset, so after the user fixes the cause and a later, different problem appears, nothing is shown.**
- Where: `client/gui.py:458-462`.
- Scenario: the lock on `config.json` is released, saves succeed for an hour, then the disk becomes read-only: no box, only the log. This is the orchestrator default Q1, stated in the message itself ("not shown again until DotExpress is started again"), so it is by design.
- Fix: none needed; optionally reset the flag when a save succeeds after a problem. Not recommended without the user asking: it would show the box again after every flaky stretch.

**M-7. Import-time `_()` calls remain in three modules (pre-existing, not in this range), so they depend on the language being installed before the import.**
- Where: `client/about.py:10-16`, `client/dictionaries/entries.py:15-17`, `client/settings/dialogs.py` class bodies (lines 357, 438, 557, 653 and the following `panel_description`).
- Scenario: `client_init` sets the language before these imports, so the packaged app is translated today (the GUI record shows zh_TW for them). A test or tool that imports `settings.dialogs` first shows English, and a user-selected language change at run time cannot affect them. The spec's D9 only covered the window title.
- Fix: leave for a later task (or move them to `N_` and translate at use). Not for F-12.

## 2. Mutants (scratch copy `$SP\work\client`, one edit each, all restored; modules named are the ones run)

| # | Edit | Modules run | Result |
| --- | --- | --- | --- |
| M2 | `_settings_save_problem_reported = True` removed (box every time) | `test_gui_document_flows` | caught (3 failures) |
| M3 | `save_translation_settings` as an `or` chain | `test_translation_settings`, `test_config` | caught |
| M4 | coordinator names the document always | `test_export_coordinator`, `test_gui_document_flows` | caught (3) |
| M4b | presenter never names the document | `test_conversion_presenter`, `test_gui_document_flows` | caught |
| M5 | `_read_dictionary_rows` catches only `OSError` | `test_conversion_text_dictionary_rules`, `test_conversion_service` | caught (2 failures, 2 errors) |
| M6 | unlisted check before the listed check in `batch_import_documents` | `test_document_workspace`, `test_workspace_service`, `test_import_problems` | caught |
| M7 | `dep` branch also catches `OSError` | `test_import_problems` | caught |
| M8 | Delete All rollback without `_update_window_title()` | `test_gui_document_flows` | caught (3) |
| M8b | Delete All rollback without `_ensure_open_document_exists()` | `test_gui_document_flows` | caught (3) |
| M9 | settings box parent is always the frame | `test_gui_document_flows` | caught |
| M10 | `WRITE_FAILED` returns `None` | `test_config` | caught |
| M11 | `unlisted_package_entry` fallback without `.dep` | `test_workspace_service` | caught |
| M15 | backup failure still writes `config.json` | `test_config` | caught (1 failure, 1 error) |
| M16 | header error without `header_not_recognized` | rules, service, presenter tests | caught (3) |
| M17 | HTML export without the translated `empty_message` | `test_document_formats`, `test_i18n`, `test_gui_document_flows` | caught |
| M18 | unlisted stems put back into `existing_names` | `test_workspace_service`, `test_gui_document_flows` | caught |
| M19 | unlisted names not case-folded | `test_document_workspace`, `test_workspace_service` | caught |
| M20 | frame skips the listed check (`if False`) | `test_gui_document_flows` | caught (4) |

No survivor, so I found no test gap that needs a new test; the untested items are the ones the GUI record covers (parent window of the box, real file locks).

## 3. zh_TW wording

Natural and consistent with the catalog: 轉換 for Convert (`無法轉換文件「{name}」。`), 轉譯 for tables and the failure prefix (`轉譯失敗：`, `選取的轉譯表無法轉譯這段文字。`), 文件 and 字典 as elsewhere, 封裝檔 for DEP (as the revived entry), 表頭 as in F-11's strings (`無法辨識檔案的表頭。...`), 副檔名, 工作區資料夾, 設定未儲存. The long warning (`DotExpress 無法將設定儲存到「{path}」。設定的變更在關閉 DotExpress 之前有效，但不會保留。...`) reads correctly and keeps the placeholders. One nit only: `HTML 檔` follows `點字檔` and `文字檔`; fine.

## Disposition (2026-10-11, fix phase; all user-visible changes are "Decided by orchestrator with the recommended default; user may override before merge", Spec Corrections 19)

Code, tests and catalogs are in commit `bdb3e78` (`Ran 1632`, `OK (skipped=6)`, 407 msgids translated, 0 fuzzy, `HEAD:client` `a967d8d4cea147cf25ccc0f490c8f94e41e711ce`). The GUI re-runs are in `auto-results.md`, section "Fix phase" (build `D:\dxtest\N-f12b`).

| Finding | Disposition | What was done |
| --- | --- | --- |
| M-1 | fixed | `batch_import_documents` logs every error that is not an `ImportProblem`, `OSError`, `UnicodeDecodeError` or `NameValidationError` at ERROR on `dotexpress.gui` with the file name and the traceback. The Import Issues text is unchanged. Tests: `test_batch_import_documents_logs_an_error_that_is_not_the_files_fault`, `..._does_not_log_the_files_own_problems`. GUI 111 shows the log line for `broken.dep`. Side effect: a `.dep` that is not a zip is logged too. |
| M-2 | fixed | `config.is_access_error` (`PermissionError`, or `OSError` with `winerror` 5, 32, 33 or `errno` `EACCES`, `EPERM`). An unreadable `config.json` shows CANNOT_OPEN only for such an error, else the existing `無法讀取檔案：{error}` (no new string). Test: `test_only_an_access_error_says_the_file_is_in_use_or_not_permitted`. |
| M-3 | fixed | One new string, `檔案已損壞或格式不正確。`, for a non-`OSError` of the docx, epub and pdf loaders; the library text goes to the log (M-1). Tests with a truncated `.docx` and `.pdf` from the real libraries. |
| M-4 | fixed | The plan's 72 step boxes are ticked (all were done, see the Implementation Notes); item 114 (a) corrected in both spec files and in the plan to "locked after the start, before pressing OK", and it changes the conversion width. |
| M-5 | fixed for a failed write | Two new strings: a write-permission text for an access error, and a generic text (`無法寫入檔案。請確認磁碟還有可用空間，且你有該資料夾的寫入權限。`) otherwise; the operating system's text with the random temporary name is not shown for a failed write. Not changed: the backup-failed text keeps `詳細資訊：{error}` (it needs a fourth string; it shows the diagnosis, once per session). |
| M-6 | by design (Q1) | No change. The once-per-session flag stays; the message says so. |
| M-7 | follow-up | Pre-existing import-time `_()` calls in `about.py`, `dictionaries/entries.py`, `settings/dialogs.py`; the user records it. |

New strings (3): `The file is damaged or is not in the expected format.`; `The file cannot be written. It may be in use by another program, or you may not have permission to write to it. Close the other program and try again.`; `The file cannot be written. Check that the disk has free space and that you can write to the folder.` (zh_TW in Spec Corrections 19). Item 119 (NVDA) stays unchecked for the user.
