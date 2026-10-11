# Localization Cleanup and Message Follow-ups (F-12) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ] `) syntax for tracking.

**Goal:** The messages users still see in English or as raw Python text are shown in Traditional Chinese with a reason they can act on, and the few messages that earlier reviews found missing are added, as the user decided on 2026-10-11 (U1-U3): the Export All summary and the conversion fallback texts (D1, D2); the reason of every Import Issues line (D3); a conversion that cannot read the selected dictionary names it and says why, in one line (D4); a document name held by a file in the workspace folder that is not listed gets its own message (D5); the first settings change of a session that cannot be saved to `config.json` shows one warning box (D6); a failed conversion of a document that is not open names it (D7); the HTML save filter, the exported page without conversion data, the browser error and the text processing script's errors (D8); `_()` is no longer applied to the window title (D9). Twenty-three new msgids, four of them revived from obsolete catalog entries (381 -> 404). Added to F-12 by the user (2026-10-11): a Delete All whose rollback leaves no valid document opens the default document with the right title (P1-3 defect 4), and `scripts/tests`' vendored-helper snapshot test compares with LF line ends (F-W5).

**Architecture:** Nine commits, each red first: Tasks 1-7 are the spec's migration steps in order, Tasks 8 and 9 the two items the user added. Task 1 marks the Export All texts and the two conversion fallback texts with `N_` (D1, D2). Task 2 adds `documents/import_problems.py` (`ImportProblem`, `describe_import_problem`), which every Import Issues line goes through; DotExpress's own loaders raise `ImportProblem` (D3). Task 3 reads the selected dictionary in one guarded helper that raises `DictionaryRulesReadError`, which `format_conversion_error` turns into `轉譯失敗：無法讀取字典「X」。<reason>` (D4). Task 4 adds `DocumentWorkspaceService.unlisted_package_entry` and the unlisted entries of Import (D5). Task 5 makes `ConfigStore._save` and the setters return a `ConfigSaveProblem`, and the frame shows the first one in a box (D6). Task 6 names the document of a failed manual conversion or single export that is not open (D7). Task 7 does D8 and D9 and adds the guard that the compiled catalog holds exactly the marked strings. Task 8 makes `on_delete_all_documents` update the title and open the default document when the rollback leaves no valid document (P1-3 defect 4). Task 9 normalizes the line ends in `scripts/tests/test_vendor_helper_snapshot.py` (F-W5). Task 10 verifies (suite, shuffled order, catalogs, fixtures, application data, 44 mutants); Task 11 builds the exe and runs GUI items 109-118 and 120 (119 stays manual).

**Tech Stack:** Python 3.13 standard library (`csv`, `dataclasses`, `enum`, `os.scandir`, `gettext`, `logging`, `unittest`, `unittest.mock`), wxPython 4.2.5 (`wx.GetActiveWindow`, `ui.message_box.message_box`), pypdf (an encrypted PDF in a test), GNU gettext 0.23 (`xgettext`, `msgmerge`, `msgfmt`, `msgattrib`), Git Bash `unix2dos`. Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-11-f12-localization-cleanup-design.md` (+ `_zh-TW.md`), with the section "Corrected after planning (F-12, 2026-10-11)" / 「規劃後的修正（F-12，2026-10-11）」 added in the plan commit (both languages). The user decided U1-U3 (2026-10-11), and that D7 is in scope; D9 is kept (it is trivial). Q1 (a) once per session, Q2 deferred and Q3 the spec's wording, and O1-O10, are the orchestrator's recommended defaults; the user may override them before the merge. The plan adds the refinements of "Spec Corrections and Refinements" below, each also a default the user may override.

## Global Constraints

- Work in the worktree `D:\workspace\DotExpress-f12`, branch `fix/f12-localization-cleanup` (HEAD is the plan commit on top of the spec commit `4b74444`, which is on `main` at `e0337df`, the F-11 merge). Never switch branches, never push, never merge, never rewrite history. The worktree has no `client\.venv`: `PY` is the main checkout's interpreter, run with the working directory inside the worktree. Do not work in the main checkout `D:\workspace\DotExpress` (the user may run the app from source there).
- Files that may change (under `client/`, nothing else there): production `client/documents/export_results.py`, `client/conversion/plain_text.py`, `client/documents/import_problems.py` (new), `client/documents/importers/base.py`, `client/documents/importers/epub_importer.py`, `client/documents/importers/pdf_importer.py`, `client/documents/workspace.py`, `client/documents/workspace_service.py`, `client/conversion/text/dictionary_rules.py`, `client/ui/conversion_presenter.py`, `client/documents/export_coordinator.py`, `client/config.py`, `client/settings/translation.py`, `client/settings/translation_tables.py`, `client/settings/view.py`, `client/documents/formats.py`, `client/dual_view/browser.py`, `client/conversion/preprocessing/user_script.py` (4 spaces), `client/gui.py` (**tabs**, but its import blocks use 4 spaces); tests `client/tests/test_i18n.py`, `client/tests/test_export_coordinator.py`, `client/tests/test_conversion_presenter.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_import_problems.py` (new), `client/tests/test_document_workspace.py`, `client/tests/test_workspace_service.py`, `client/tests/test_conversion_text_dictionary_rules.py`, `client/tests/test_conversion_service.py`, `client/tests/test_config.py`, `client/tests/test_translation_settings.py`, `client/tests/test_translation_tables.py`, `client/tests/test_view_settings.py`, `client/tests/test_document_formats.py`, `client/tests/test_dual_view_browser.py`, `client/tests/test_user_preprocessing_script.py` (4 spaces), and outside `client/` only `scripts/tests/test_vendor_helper_snapshot.py` (4 spaces, Task 9); catalogs `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`; in Task 11 the new history folder `docs/superpowers/history/2026-10-11-02-f12-localization-cleanup/` (scripts with tabs, results) and this plan's Implementation Notes.
- Never touch, in the main checkout `D:\workspace\DotExpress`, `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data; Task 0 and Task 10 only hash them), or its untracked `client2/`, `preprocessing/`, `testdata/` and `task.md` (read-only). In the worktree no test may create `client/log/`, `client/workspace/` or `client/config.json`: the modules whose code under test logs isolate `dotexpress.gui` or `dotexpress.config` (`tests.file_log_isolation`), and the new tests use temporary folders. Never touch `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (CRLF bytes), tracked `client/braille/` content, `client/braille/liblouis/`, `client/tests/fixtures/`, `scripts/` (apart from Task 9's test), `vendor/`, the submodule pointers, or the committed scripts and data of earlier history folders. Never run `py scripts\sync-nvda.py`. Never start `gui.py` from source in any checkout: only packaged copies, each in a new `D:\dxtest\auto*-f12` folder. **Never write to the Windows clipboard**: no test, probe or GUI script of this plan does (no `SetClipboardData`, no Ctrl+C/V/X, no `wx.TheClipboard`; text reaches the app through files and `set_edit_text`). `git status --short -- client docs scripts` must stay empty between commits (`docs/` holds the history folder of Task 11 only until Task 11 commits it).
- The worktree uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply the blocks **with a script that reads them from this file** (`$T/tools/apply_blocks.py`, Task 0 Step 3), not by hand: a `File:` block is written as is (LF is fine; git normalizes it); an `Edit:` block is the line ``Edit: `path` `` followed by two fenced blocks, the exact old text and its replacement; the old text must occur exactly once in the file at that point (compared with CRLF converted to LF; the file keeps its line endings). The blocks of one step are applied in order. Never edit with MSYS `sed -i` and never paste code through a shell heredoc (it turns `\\` into `\`). Several test files hold backslash-u escapes (`test_document_workspace.py`, `test_workspace_service.py`, `test_i18n.py`, `test_gui_document_flows.py`), and some blocks hold backslash escapes: the Edit/Write tools turn such an escape into its character, so never rewrite or patch these files through them. `apply_blocks.py` reads and writes bytes; the tree id check after each commit catches any other change.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`, `translation_liblouis_golden.json` `8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e` (`git show HEAD:<path> | sha256sum`), unchanged.
- Catalogs: `POT-Creation-Date` stays `2026-10-10 12:00+0800` (pinned by `$T/tools/pin_pot_date.py` after `generate-pot.bat`), so the `.pot`, `.po` and `.mo`, and with them the tree id, are the same in every run.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly; look at `git diff --cached --stat` first; never `git commit -F -`.
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (F-9's: FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`, the random part of a temporary file name as `<rnd>`, object addresses as `<addr>`). A failure line that shows a path inside the system temporary folder in a cut diff (`[84 chars]`) depends on the length of that folder's name; on another account it can differ in that count only. `brief.py` shows the last character of that random name, before `/sources/`, as `<c>`. Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks. Tests run as `$PY -B -X utf8 -m unittest ...` (no bytecode in the worktree).
- Memory (the machine has 8 GB and once ended jobs for low memory): run one heavy job at a time (a replay, a test suite, the mutants, the build, a GUI item), each only when PowerShell `(Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue` shows at least 600 (the user, 2026-10-11; 1024 before); otherwise wait. If the system ends a job, stop and report; do not restart it unasked.
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress-f12
  MAIN=/d/workspace/DotExpress
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f12impl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the main checkout: only its interpreter is used, its git-ignored runtime is copied into the worktree (Task 0 Step 2), and its application data is hashed read-only (Task 0 Step 4, Task 10 Step 5). The dry run used scratch clones as `REPO`. Task 11 uses PowerShell for the build and the UIA venv for the GUI scripts.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning (F-12, 2026-10-11)" in the plan commit. Re-checked against the code of `main` `e0337df` (F-11 merged, after its review and the I-1 fix): every decision D1-D9, the behavior table, the inventory E1-E8 and the probes hold, with the refinements below. Function names are as the spec gives them; line numbers moved (orientation only).

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

## Dry Run

The plan was replayed on scratch clones of the repository at the spec commit `4b74444` with a stand-in plan commit (this plan and the corrected spec files) on `fix/f12-localization-cleanup` (`$SP/f12plan/r*`, never the worktree or the main checkout), by F-9's harness: it writes every `File:` block, applies every `Edit:` block exactly once (CRLF-aware), runs every `bash` block from `client/` with `REPO` set to the clone and `MAIN` to the main checkout (so Task 0's guarded copies filled the clone, and the application-data check read the real data read-only), and compares its stdout with the following `text` block. That replay of Tasks 0-10 produced every expected block of this plan (0 mismatches), including all red runs, the catalog steps, the per-commit tree ids, the six shuffle seeds and the 44 mutants; no `client/log`, `client/workspace`, `client/dictionary` or `client/config.json` appeared in the clone. The code itself was developed on a separate clone, red first, in the same seven steps; the blocks are that clone's diffs, and its tree ids equal the replay's.

Then (planning and implementation are one run since 2026-10-11) a fresh clone of the branch with the plan commit applied every step with Task 0 Step 3's `apply_blocks.py`, ran every bash block and compared it with its expected block, and committed each task; its commits became the worktree's commits. Task 11 then ran once, on the build of the worktree (`D:\dxtest\N-f12`) against `N-f11c`. Both are recorded in the Implementation Notes.

A draft of item 111 on `N-f11c` showed that the file dialog accepts a file held open without sharing when it is typed with other names (Spec Corrections 16). No script wrote to the clipboard.

## Review Focus

1. **Import reasons** (D3, D5): the order of `describe_import_problem` (an `ImportProblem` first, then `PermissionError`, the name errors, any other error of a package that is not an `OSError`, `UnicodeDecodeError`, the raw text), the reason of each loader's refusal, the listed duplicate before the unlisted entry, and a failed package write (Test Plan E; 9 mutants; GUI 111, 113).
2. **The dictionary read of a conversion** (D4): the guarded helper reads the whole file before any row is processed; the Bopomofo file is not guarded; the one-line text and its four reasons plus the header reason (Test Plan C2, C3, D; 6 mutants; GUI 112).
3. **The name check** (D5): `unlisted_package_entry` (the on-disk spelling, `exclude_name`, the fallback), the box's two paragraphs and the folder path, Rename (Test Plan F; 4 mutants; GUI 113).
4. **Settings that cannot be saved** (D6): what `_save` returns in each F-8 case with the log lines unchanged, every setter called even after a failed one, the once-per-session flag, the parent (Test Plan G; 11 mutants; GUI 114).
5. **The document of a failed conversion** (D7): the open document at delivery, no name for a document that is open or for a manual job without one, Export All lines unchanged (Test Plan C4, C5; 4 mutants; GUI 115).
6. **The two added items:** the Delete All rollback without a valid document (Task 8; 2 mutants; GUI 120) and the snapshot test's line ends (Task 9: only the comparison changes, not the vendored file).
7. **Catalogs and strings:** twenty-three msgids (four revived exactly, not fuzzy), 404 translated, 0 fuzzy; eight wrong fuzzy guesses of `msgmerge` replaced; the guard that the compiled catalog equals the marked strings (Spec Corrections 14, 15).

## File Map

- Task 1: `client/tests/test_export_coordinator.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_conversion_presenter.py` (the P1-4 defect 4 pins flipped), `client/tests/test_i18n.py` (strings 1-5, the markers); `client/documents/export_results.py`, `client/conversion/plain_text.py`; the three catalogs.
- Task 2: `client/tests/test_import_problems.py` (new), `client/tests/test_document_workspace.py`, `client/tests/test_workspace_service.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_i18n.py` (strings 10-15); `client/documents/import_problems.py` (new), `client/documents/importers/base.py`, `client/documents/importers/epub_importer.py`, `client/documents/importers/pdf_importer.py`, `client/documents/workspace.py`, `client/documents/workspace_service.py`; the three catalogs.
- Task 3: `client/tests/test_conversion_text_dictionary_rules.py`, `client/tests/test_conversion_service.py`, `client/tests/test_conversion_presenter.py`, `client/tests/test_i18n.py` (strings 16, 17); `client/conversion/text/dictionary_rules.py`, `client/ui/conversion_presenter.py`; the three catalogs.
- Task 4: `client/tests/test_workspace_service.py`, `client/tests/test_document_workspace.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_i18n.py` (strings 18, 19); `client/documents/workspace.py`, `client/documents/workspace_service.py`, `client/gui.py`; the three catalogs.
- Task 5: `client/tests/test_config.py`, `client/tests/test_translation_settings.py`, `client/tests/test_translation_tables.py`, `client/tests/test_view_settings.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_i18n.py` (strings 20-22); `client/config.py`, `client/settings/translation.py`, `client/settings/translation_tables.py`, `client/settings/view.py`, `client/gui.py`; the three catalogs.
- Task 6: `client/tests/test_conversion_presenter.py`, `client/tests/test_export_coordinator.py`, `client/tests/test_i18n.py` (string 23); `client/ui/conversion_presenter.py`, `client/documents/export_coordinator.py`; the three catalogs.
- Task 7: `client/tests/test_user_preprocessing_script.py`, `client/tests/test_conversion_service.py`, `client/tests/test_dual_view_browser.py`, `client/tests/test_export_coordinator.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_document_formats.py`, `client/tests/test_i18n.py` (strings 6-9, the markers, the catalog guard); `client/documents/formats.py`, `client/dual_view/browser.py`, `client/conversion/preprocessing/user_script.py`, `client/gui.py`; the three catalogs.
- Task 8: `client/tests/test_gui_document_flows.py` (the P1-3 defect 4 pin flipped, one test, the delegation test); `client/gui.py`; the template and the `.po` (`#:` lines only).
- Task 9: `scripts/tests/test_vendor_helper_snapshot.py`.
- Task 11: `docs/superpowers/history/2026-10-11-02-f12-localization-cleanup/` (`auto/` scripts, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | msgids | `HEAD:client` |
| --- | --- | --- | --- | --- | --- |
| baseline (`e0337df` + spec + plan) | - | 1567 | `OK (skipped=6)` | 381 | `5e130210420bf7a3828936094ac0af5868c32801` |
| 1 Export All summary, fallback texts | 2 | 1569 | `OK (skipped=6)` | 386 | `b6d32d26860d0a9cdee68f3bd81634ec529d0efd` |
| 2 import reasons | 14 | 1583 | `OK (skipped=6)` | 392 | `5e23f82b85a0ff43a96236eca5e6e86cfe959905` |
| 3 dictionary that cannot be read | 8 | 1591 | `OK (skipped=6)` | 394 | `0661d35dc654b7e0f025ce34e452fd7629257273` |
| 4 name held by an unlisted entry | 8 | 1599 | `OK (skipped=6)` | 396 | `ebbf013b774aaeae21b6ce9dc98532f08d016023` |
| 5 settings not saved | 15 | 1614 | `OK (skipped=6)` | 399 | `cd5b9c3959ca123d34771634df05d9a028806c40` |
| 6 document of a failed conversion | 6 | 1620 | `OK (skipped=6)` | 400 | `b6929558c675a31124b2e1f418db2d2b87a7576a` |
| 7 remaining messages, title | 6 | 1626 | `OK (skipped=6)` | 404 | `9a5516a5f74312816fbae4ae2f8b7e2f75c210ef` |
| 8 Delete All rollback | 1 | 1627 | `OK (skipped=6)` | 404 | `62325f9a05b0cd0a1af9344cd078e417c09910d1` |
| 9 snapshot test line ends (scripts only) | 0 | 1627 | `OK (skipped=6)` | 404 | `62325f9a05b0cd0a1af9344cd078e417c09910d1` |
| 11 GUI results (docs only) | - | 1627 | `OK (skipped=6)` | 404 | `62325f9a05b0cd0a1af9344cd078e417c09910d1` |

"Tests added" is the net count (new tests minus removed ones; a renamed or flipped test counts as neither). The 6 skips are POSIX-only tests.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 by the block script: `brief.py`, `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` (F-9's, unchanged), `mo_check.py` (listing the 23 F-12 msgids), `po_entry.py` (how the `.po` holds a msgid: active, fuzzy, obsolete copies), `f12_mutants.py` (44 mutants of the code after Task 8, run on a copy of `client/`; the repository is never changed) and `apply_blocks.py` (F-11's with its docstring naming this plan; applies the `File:` and `Edit:` blocks of one step).

---

### Task 0: Baseline (no commit)

- [x] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short -- client docs scripts
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO rev-parse HEAD~1 HEAD~2 HEAD~2:client
git -C $REPO diff --stat e0337df -- client
```

Expected (`status` and the diff print nothing; `HEAD~1` is the spec commit, `HEAD~2` is `main` at `e0337df`):

```text
docs: plan for localization cleanup (F-12)
fix/f12-localization-cleanup
4b74444c1081c7054cf73c804f04688bac19d4d0
e0337df75dcff90e8a0134e0d2d7847f322075c1
5e130210420bf7a3828936094ac0af5868c32801
```

- [x] **Step 2: The git-ignored runtime the tests load.** A worktree is made without the generated liblouis DLL and tables, `louis_helper.py`, MathCAT, the submodule's `configure.ac` and the NVDA helper source that Task 9's test reads (`include/nvda/source/louisHelper.py`); the guarded copies below bring them from the main checkout, as F-3's Task 0 did (in a worktree that has them already they do nothing). Never stage these files.

```bash
test -e $REPO/client/braille/liblouis.dll || cp $MAIN/client/braille/liblouis.dll $REPO/client/braille/
test -e $REPO/client/braille/louis_helper.py || cp $MAIN/client/braille/louis_helper.py $REPO/client/braille/
test -e $REPO/client/braille/liblouis || cp -r $MAIN/client/braille/liblouis $REPO/client/braille/liblouis
test -e $REPO/client/mathcat || cp -r $MAIN/client/mathcat $REPO/client/mathcat
test -e $REPO/include/liblouis/configure.ac || { mkdir -p $REPO/include/liblouis && cp $MAIN/include/liblouis/configure.ac $REPO/include/liblouis/; }
test -e $REPO/include/nvda/source/louisHelper.py || { mkdir -p $REPO/include/nvda/source && cp $MAIN/include/nvda/source/louisHelper.py $REPO/include/nvda/source/; }
for f in client/braille/liblouis.dll client/braille/louis_helper.py client/braille/liblouis/tables client/mathcat/assets include/liblouis/configure.ac include/nvda/source/louisHelper.py; do test -e $REPO/$f && echo "present: $f"; done
git -C $MAIN submodule status include/liblouis | cut -c2-41
git -C $REPO rev-parse HEAD:include/liblouis
cmp $REPO/client/braille/louis_helper.py $REPO/vendor/nvda/liblouis/runtime/louis_helper.py && echo "louis_helper.py is the vendored file"
git -C $REPO status --short -- client docs scripts
```

Expected (`status` prints nothing):

```text
present: client/braille/liblouis.dll
present: client/braille/louis_helper.py
present: client/braille/liblouis/tables
present: client/mathcat/assets
present: include/liblouis/configure.ac
present: include/nvda/source/louisHelper.py
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
louis_helper.py is the vendored file
```

- [x] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed). `brief.py`, `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` are F-9's, unchanged; `mo_check.py` lists the F-12 msgids; `apply_blocks.py` is F-11's with its docstring naming this plan.

File: `$T/tools/brief.py`

````python
"""Condense unittest output read from stdin (throwaway, not committed).

Keeps the FAIL/ERROR headers and exception lines, cut to 160 characters (a cut line is
printed once, so the subtests of one test give one header), the "Ran" line without its
timing and the final OK/FAILED line, so that outputs can be compared with the plan. The
client directory is shown as <client>; temporary directories (tempfile.mkdtemp names,
also in repr form with doubled backslashes) as <tmp>; random temporary-file suffixes as
<rnd>; object addresses (the frame's repr in a message-box event, F-9) as <addr>, also
when unittest's diff has cut the repr down to its last characters. F-12 addition: the
last character of a cut temporary folder's random name before "/sources/" (a cut diff shows
only the end of the name) as <c>.
"""
import re
import sys
from pathlib import Path

CLIENT = str(Path.cwd())
CLIENT_REPR = CLIENT.replace("\\", "\\\\")
TMPDIR = re.compile(r"[A-Za-z]:(?:\\\\|\\)(?:[^'\"\s]*?(?:\\\\|\\))?tmp[a-z0-9_]{8}")
RANDOM_TMP = re.compile(r"(\.[\w.]+?\.(?:dep|csv|py|json|brl|html)\.)[a-z0-9_]{8,16}(\.tmp)")
ADDRESS = re.compile(r" at 0x[0-9A-Fa-f]+>")
CUT_ADDRESS = re.compile(r"(\[\d+ chars\])[0-9A-F]{1,16}>")
CUT_TMP = re.compile(r"[a-z0-9_]((?:/|\\\\|\\)sources(?:/|\\\\|\\))")
seen = set()
for line in sys.stdin:
    line = line.rstrip("\n").replace(CLIENT_REPR, "<client>").replace(CLIENT, "<client>")
    line = TMPDIR.sub("<tmp>", line)
    line = RANDOM_TMP.sub(r"\1<rnd>\2", line)
    line = CUT_TMP.sub(r"<c>\1", line)
    line = CUT_ADDRESS.sub(r"\1<addr>", ADDRESS.sub(" at <addr>>", line))
    if re.match(r"(FAIL|ERROR): ", line) or re.match(r"[A-Za-z_.]*(Error|Exception|Interrupt|Exit): ", line):
        line = line[:160]
        if line not in seen:
            seen.add(line)
            print(line)
    elif line.startswith("Ran "):
        print(re.sub(r" in [0-9.]+s$", "", line))
    elif line.startswith(("OK", "FAILED")):
        print(line)
````

File: `$T/tools/msgid_scan.py`

````python
"""List the gettext msgids of a client tree (throwaway, not committed).

Usage: python -I msgid_scan.py <client_dir>
AST stand-in for scripts/generate-pot.bat: keywords _ and N_, every *.py under
client_dir except .venv/, tests/, build/, dist/ (and the generated braille/liblouis/).
Prints the msgid count and the SHA-256 of the sorted, newline-joined msgids.
"""
import ast
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
msgids = set()
for path in sorted(root.rglob("*.py")):
    relative = path.relative_to(root)
    if relative.parts[0] in {".venv", "tests", "build", "dist"} or relative.parts[:2] == ("braille", "liblouis"):
        continue
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"_", "N_"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            msgids.add(node.args[0].value)
digest = hashlib.sha256("\n".join(sorted(msgids)).encode("utf-8")).hexdigest()
print(f"source msgids: {len(msgids)} sha256 {digest}")
````

File: `$T/tools/shuffle_harness.py`

````python
"""Run every test module in a seeded random order in one process (throwaway).

Usage (from client/): python shuffle_harness.py <seed> [<seed> ...]
Prints one line per seed: seed, tests run, failures, errors, skipped, and the ids
of the failing or erroring tests.
"""
import io
import random
import sys
import unittest

sys.path.insert(0, ".")

for seed in (int(arg) for arg in sys.argv[1:]):
    suite = unittest.defaultTestLoader.discover("tests")
    modules = list(suite)
    random.Random(seed).shuffle(modules)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.TestSuite(modules))
    bad = sorted(test.id().rsplit(".", 1)[-1] for test, _trace in result.failures + result.errors)
    print(
        f"seed {seed}: ran={result.testsRun} failures={len(result.failures)} "
        f"errors={len(result.errors)} skipped={len(result.skipped)} {bad}"
    )
````

File: `$T/tools/pin_pot_date.py`

````python
"""Set the POT-Creation-Date header of a .pot file to a fixed value (throwaway, not committed).

Usage: python pin_pot_date.py <file.pot> "<YYYY-MM-DD HH:MM+ZZZZ>"

xgettext writes the current time there, msgmerge copies it into the .po and msgfmt into
the .mo. A fixed value keeps the three catalogs, and so the commit's tree id, the same in
every run of the plan. Nothing else in the file changes; line ends are kept.
"""
import re
import sys
from pathlib import Path

path, value = Path(sys.argv[1]), sys.argv[2]
data = path.read_bytes().decode("utf-8")
pattern = re.compile(r'^"POT-Creation-Date: [^"\\]*\\n"$', re.M)
if len(pattern.findall(data)) != 1:
    sys.exit(f"{path}: expected one POT-Creation-Date line")
data = pattern.sub(lambda _match: f'"POT-Creation-Date: {value}\\n"', data)
path.write_bytes(data.encode("utf-8"))
print(f"{path.name}: POT-Creation-Date {value}")
````

File: `$T/tools/mo_check.py`

````python
"""Load a compiled catalog with gettext.GNUTranslations and print what it holds (throwaway).

Usage: python -I mo_check.py <file.mo>
Prints the number of catalog keys (the msgids plus the header) and the translation of
each msgid that F-12 adds, in the spec's order 1-23 (msgfmt 0.23 leaves POT-Creation-Date
out of the .mo header, so the .mo does not depend on it). A msgid the catalog does not
hold prints as "(missing)". Output is UTF-8 (-I ignores PYTHONIOENCODING).
"""
import gettext
import sys

sys.stdout.reconfigure(encoding="utf-8")

MSGIDS = (
    "Export Complete with Errors",
    "All documents were exported successfully.",
    "Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}",
    "An unknown error occurred.",
    "The selected translation table could not translate this text.",
    "HTML files (*.html)|*.html",
    "No supported browser or system HTML opener is available.",
    "main is not callable.",
    "main must return str, got {type}.",
    "The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.",
    "This file type cannot be imported.",
    "The file name extension does not match the selected file type.",
    "Imported file must be a valid DotExpress DEP package.",
    "This PDF file is encrypted and cannot be imported.",
    "The EPUB file is damaged or has no readable content.",
    'Dictionary "{name}" cannot be read. {reason}',
    "Its header is not recognized. The first line of the file must contain the text, braille, and type headers.",
    'The name "{name}" is used by "{file}" in the workspace folder, but that file is not in the document list.',
    "Choose another name, or move or delete that file. Workspace folder:\n{folder}",
    "Settings Not Saved",
    'DotExpress cannot save its settings to "{path}". Changes to the settings apply until DotExpress is closed, '
    "but they are not kept. This message is not shown again until DotExpress is started again.\n\n{reason}",
    'The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Details: {error}',
    'Document "{name}" could not be converted.\n\n{error}',
)

with open(sys.argv[1], "rb") as stream:
    catalog = gettext.GNUTranslations(stream)
print("catalog keys:", len(catalog._catalog))
for number, msgid in enumerate(MSGIDS, start=1):
    translated = catalog._catalog.get(msgid, "(missing)")
    print(f"{number:2d} {translated!r}")
````

File: `$T/tools/po_entry.py`

````python
"""Show how a .po file holds some msgids (throwaway, not committed).

Usage: python -I po_entry.py <file.po> <msgid> [<msgid> ...]
For each msgid (plain, or a quoted Python string literal): how many active entries, whether
one is fuzzy, how many obsolete (#~) copies, and the active msgstr. Output is UTF-8.
"""
import ast
import sys

sys.stdout.reconfigure(encoding="utf-8")


def entries(path):
    text = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    for block in text.split("\n\n"):
        lines = [line for line in block.split("\n") if line]
        obsolete = bool(lines) and all(line.startswith("#~") for line in lines)
        if obsolete:
            lines = [line[3:] if line.startswith("#~ ") else line[2:] for line in lines]
        fuzzy = any(line.startswith("#,") and "fuzzy" in line for line in lines)
        fields = {"msgid": "", "msgstr": ""}
        field = None
        for line in lines:
            if line.startswith("#"):
                continue
            for name in ("msgid", "msgstr"):
                if line.startswith(name + " "):
                    field = name
                    fields[name] = ast.literal_eval(line[len(name) + 1:])
                    break
            else:
                if line.startswith('"') and field:
                    fields[field] += ast.literal_eval(line)
        yield fields["msgid"], fields["msgstr"], fuzzy, obsolete


def main():
    path, *arguments = sys.argv[1:]
    # An argument in quotes is a Python string literal, so a msgid with a line break fits.
    msgids = [ast.literal_eval(argument) if argument[:1] in "'\"" else argument for argument in arguments]
    found = list(entries(path))
    for msgid in msgids:
        active = [(msgstr, fuzzy) for key, msgstr, fuzzy, obsolete in found if key == msgid and not obsolete]
        obsolete = [1 for key, _msgstr, _fuzzy, is_obsolete in found if key == msgid and is_obsolete]
        status = f"active {len(active)}, fuzzy {'yes' if any(f for _s, f in active) else 'no'}, obsolete copies {len(obsolete)}"
        print(f"{msgid!r}: {status}, msgstr {active[0][0]!r}" if active else f"{msgid!r}: {status}")


if __name__ == "__main__":
    main()
````

File: `$T/tools/f12_mutants.py`

````python
"""Run the F-12 tests against deliberately broken code (throwaway, not committed).

Usage: python f12_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run, and
scripts/generate-pot.bat to <scratch_dir>/scripts (test_i18n reads it). For each
mutant it edits one file of the copy (one exact, unique replacement), runs the F-12 test
modules there, prints which tests caught it and restores the file. The repository is
never changed. Matches the code after Task 8. Exit status 1 if a mutant is not caught or
its pattern is not found exactly once. Python runs with -B (no bytecode is written): a
restored file can have the size and modification second of the mutant, and a cached
.pyc would then shadow it.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

RESULTS = "documents/export_results.py"
PLAIN = "conversion/plain_text.py"
PROBLEMS = "documents/import_problems.py"
WORKSPACE = "documents/workspace.py"
SERVICE = "documents/workspace_service.py"
RULES = "conversion/text/dictionary_rules.py"
PRESENTER = "ui/conversion_presenter.py"
COORDINATOR = "documents/export_coordinator.py"
CONFIG = "config.py"
TRANSLATION = "settings/translation.py"
GUI = "gui.py"
FORMATS = "documents/formats.py"
BROWSER = "dual_view/browser.py"
SCRIPT = "conversion/preprocessing/user_script.py"
MUTANTS = {
    # D1, D2: the Export All summary and the fallback texts.
    "export-summary-unmarked": (
        RESULTS,
        'EXPORT_ALL_SUCCESS_MESSAGE = N_("All documents were exported successfully.")\n',
        'EXPORT_ALL_SUCCESS_MESSAGE = "All documents were exported successfully."\n',
    ),
    "fallback-text-unmarked": (PLAIN, '        return N_("An unknown error occurred.")\n', '        return "An unknown error occurred."\n'),
    # D3: the import reasons.
    "not-utf8-generic": (PROBLEMS, "    if isinstance(error, UnicodeDecodeError):\n", "    if False:\n"),
    "permission-raw": (PROBLEMS, "    if isinstance(error, PermissionError):\n", "    if False:\n"),
    "name-codes-swapped": (PROBLEMS, '        if error.code in ("empty", "too_long"):\n', '        if error.code in ("empty", "invalid"):\n'),
    "import-problem-shown-by-str": (PROBLEMS, "        return _(error.reason)\n", "        return str(error)\n"),
    "damaged-package-generic": (
        PROBLEMS,
        "    if format_key.casefold() == DEP_FORMAT_KEY and not isinstance(error, OSError):\n",
        "    if False:\n",
    ),
    "damaged-package-catches-os-errors": (
        PROBLEMS,
        "    if format_key.casefold() == DEP_FORMAT_KEY and not isinstance(error, OSError):\n",
        "    if format_key.casefold() == DEP_FORMAT_KEY:\n",
    ),
    "unlisted-reason-before-the-listed-one": (
        WORKSPACE,
        "        if document.name.casefold() in seen_names:\n"
        "            issues.append(BatchIssue(path=path, reason=_('Document \"{name}\" already exists.').format(name=document.name)))\n"
        "            continue\n"
        "        if document.name.casefold() in unlisted:\n",
        "        if document.name.casefold() in unlisted:\n"
        "            issues.append(BatchIssue(path=path, reason=unlisted_entry_reason(document.name, unlisted[document.name.casefold()])))\n"
        "            continue\n"
        "        if document.name.casefold() in seen_names:\n"
        "            issues.append(BatchIssue(path=path, reason=_('Document \"{name}\" already exists.').format(name=document.name)))\n"
        "            continue\n"
        "        if False:\n",
    ),
    "package-write-raw": (
        SERVICE,
        'reason=_("Failed to save document: {error}").format(error=exc)',
        "reason=str(exc)",
    ),
    # D4: a dictionary that cannot be read.
    "bopomofo-guarded": (
        RULES,
        '        with Path(bopomofo_path).open("r", newline="", encoding="utf-8-sig") as f_b:\n',
        "        try:\n"
        '            Path(bopomofo_path).read_text(encoding="utf-8-sig")\n'
        "        except (UnicodeDecodeError, OSError) as error:\n"
        "            raise DictionaryRulesReadError(bopomofo_path, error) from error\n"
        '        with Path(bopomofo_path).open("r", newline="", encoding="utf-8-sig") as f_b:\n',
    ),
    "processing-error-wrapped": (
        RULES,
        "                    target_parts = list(target)\n",
        "                    try:\n"
        "                        target_parts = list(target)\n"
        "                    except TypeError as error:\n"
        "                        raise DictionaryRulesReadError(dictionary_path, error) from error\n",
    ),
    "read-errors-not-wrapped": (
        RULES,
        "    except (UnicodeDecodeError, OSError, csv.Error) as error:\n",
        "    except csv.Error as error:\n",
    ),
    "header-told-as-other": (
        RULES,
        "    raise DictionaryRulesReadError(path, header_error, header_not_recognized=True)\n",
        "    raise DictionaryRulesReadError(path, header_error)\n",
    ),
    "read-error-not-recognized": (PRESENTER, "    if isinstance(error.error, DictionaryRulesReadError):\n", "    if False:\n"),
    "two-paragraph-form": (
        PRESENTER,
        ".format(name=error.path.stem, reason=reason)\n",
        '.format(name=error.path.stem, reason="\\n\\n" + reason)\n',
    ),
    # D5: a name held by an entry on disk that is not listed.
    "unlisted-box-for-a-listed-name": (
        GUI,
        "\t\t\tif self._document_controller.document_name_exists(document_name, exclude_name=exclude_name):\n",
        "\t\t\tif False:\n",
    ),
    "entry-takes-the-typed-spelling": (SERVICE, "                        return entry.name\n", '                        return f"{name}{DEP_EXTENSION}"\n'),
    "box-without-the-folder": (
        GUI,
        '\t\t\t\t\t\t_("Choose another name, or move or delete that file. Workspace folder:\\n{folder}").format(\n',
        '\t\t\t\t\t\t"".format(\n',
    ),
    "entry-ignores-exclude-name": (
        SERVICE,
        "        if not self.package_name_taken(name, exclude_name=exclude_name):\n",
        "        if not self.package_name_taken(name):\n",
    ),
    "import-sees-no-unlisted-entry": (SERVICE, "            unlisted_entries=unlisted,\n", "            unlisted_entries={},\n"),
    # D6: settings that cannot be saved.
    "unreadable-not-returned": (
        CONFIG,
        "            return ConfigSaveProblem(ConfigSaveProblemKind.UNREADABLE, data.error, self._path)\n",
        "            return None\n",
    ),
    "backup-failed-not-returned": (
        CONFIG,
        "                return ConfigSaveProblem(\n                    ConfigSaveProblemKind.BACKUP_FAILED,\n",
        "                return None\n                return ConfigSaveProblem(\n                    ConfigSaveProblemKind.BACKUP_FAILED,\n",
    ),
    "write-failed-not-returned": (
        CONFIG,
        "            return ConfigSaveProblem(ConfigSaveProblemKind.WRITE_FAILED, error, self._path)\n",
        "            return None\n",
    ),
    "once-per-session-flag-ignored": (
        GUI,
        "\t\tif problem is None or self._settings_save_problem_reported:\n",
        "\t\tif problem is None:\n",
    ),
    "client-id-returns-the-problem": (
        CONFIG,
        "        self._save(data)\n        return client_id\n",
        "        problem = self._save(data)\n        return problem or client_id\n",
    ),
    "set-lang-returns-the-problem": (CONFIG, "            data[\"language\"] = lang\n            self._save(data)\n", "            data[\"language\"] = lang\n            return self._save(data)\n"),
    "box-after-a-good-save": (
        GUI,
        "\t\tif problem is None or self._settings_save_problem_reported:\n",
        "\t\tif self._settings_save_problem_reported:\n",
    ),
    "font-size-not-reported": (
        GUI,
        "\t\tself._report_settings_save_problem(save_view_settings(self._config_store, self.view_settings))\n",
        "\t\tsave_view_settings(self._config_store, self.view_settings)\n",
    ),
    "dictionary-not-reported": (
        GUI,
        "\t\tself._report_settings_save_problem(self._config_store.set_selected_dictionary(selected_name))\n",
        "\t\tself._config_store.set_selected_dictionary(selected_name)\n",
    ),
    "first-failed-setter-stops-the-others": (
        TRANSLATION,
        "    problems = (\n"
        "        store.set_output_mode(settings.output_mode),\n"
        "        store.set_conversion_width(settings.width),\n"
        "        store.set_selected_dictionary(settings.selected_dictionary),\n"
        "    )\n"
        "    return next((problem for problem in problems if problem is not None), None)\n",
        "    return (\n"
        "        store.set_output_mode(settings.output_mode)\n"
        "        or store.set_conversion_width(settings.width)\n"
        "        or store.set_selected_dictionary(settings.selected_dictionary)\n"
        "    )\n",
    ),
    "box-always-on-the-frame": (GUI, "\t\t\tparent=wx.GetActiveWindow() or self,\n", "\t\t\tparent=self,\n"),
    # D7: the document of a failed conversion that is not open.
    "manual-named-when-open": (
        PRESENTER,
        "        if target.document_name is None or target.document_name == self._documents.open_document_name:\n",
        "        if target.document_name is None:\n",
    ),
    "manual-not-named-when-not-open": (
        PRESENTER,
        "        if target.document_name is None or target.document_name == self._documents.open_document_name:\n",
        "        if True:\n",
    ),
    "export-rule-takes-the-open-document-at-the-request": (
        COORDINATOR,
        "                on_error=lambda message: self._view.show_error(self._name_unopened_document(document.name, message), _(\"Error\")),\n",
        "                on_error=lambda message, open_name=self._documents.open_document_name: self._view.show_error(\n"
        "                    message if document.name == open_name else self._name_unopened_document(document.name, message), _(\"Error\")\n"
        "                ),\n",
    ),
    "export-all-lines-named": (
        COORDINATOR,
        "        def conversion_failed(message: str) -> None:\n            result.add_failure(document.name, message)\n",
        "        def conversion_failed(message: str) -> None:\n            result.add_failure(document.name, self._name_unopened_document(document.name, message))\n",
    ),
    # D8, D9: the remaining English messages and the window title.
    "exported-page-in-english": (
        FORMATS,
        '        empty_message=_("No conversion data is available for this document."),\n',
        '        empty_message="No conversion data is available for this document.",\n',
    ),
    "html-filter-unmarked": (FORMATS, '        export_wildcard=N_("HTML files (*.html)|*.html"),\n', '        export_wildcard="HTML files (*.html)|*.html",\n'),
    "browser-error-untranslated": (
        BROWSER,
        '        raise OSError(_("No supported browser or system HTML opener is available."))\n',
        '        raise OSError("No supported browser or system HTML opener is available.")\n',
    ),
    "script-error-untranslated": (
        SCRIPT,
        '        raise TypeError(_("main must return str, got {type}.").format(type=type(output).__name__))\n',
        '        raise TypeError(f"main must return str, got {type(output).__name__}.")\n',
    ),
    "script-callable-error-untranslated": (SCRIPT, '        raise TypeError(_("main is not callable."))\n', '        raise TypeError("main is not callable.")\n'),
    # Task 8 (P1-3 defect 4): the Delete All rollback without a valid document.
    "rollback-title-not-updated": (
        GUI,
        "\t\t\t\tself._update_window_title()\n\t\t\t\tself._clear_document_editors()\n\t\t\t\tself._ensure_open_document_exists()\n",
        "\t\t\t\tself._clear_document_editors()\n\t\t\t\tself._ensure_open_document_exists()\n",
    ),
    "rollback-without-the-default-document": (
        GUI,
        "\t\t\t\tself._update_window_title()\n\t\t\t\tself._clear_document_editors()\n\t\t\t\tself._ensure_open_document_exists()\n",
        "\t\t\t\tself._update_window_title()\n\t\t\t\tself._clear_document_editors()\n",
    ),
    "window-title-through-gettext": (
        GUI,
        "\t\tself.SetTitle(format_window_title(self._document_controller.open_document_name))\n",
        "\t\tself.SetTitle(_(format_window_title(self._document_controller.open_document_name)))\n",
    ),
}
MODULES = (
    "tests.test_i18n",
    "tests.test_export_coordinator",
    "tests.test_conversion_presenter",
    "tests.test_conversion_service",
    "tests.test_conversion_text_dictionary_rules",
    "tests.test_import_problems",
    "tests.test_document_workspace",
    "tests.test_workspace_service",
    "tests.test_config",
    "tests.test_translation_settings",
    "tests.test_translation_tables",
    "tests.test_view_settings",
    "tests.test_gui_document_flows",
    "tests.test_document_formats",
    "tests.test_dual_view_browser",
    "tests.test_user_preprocessing_script",
)
IGNORE = shutil.ignore_patterns(".venv", "log", "dictionary", "workspace", "build", "dist", "config.json", "__pycache__")
FAILED = re.compile(r"^(?:FAIL|ERROR): (\w+) \(([\w.]+)\)", re.M)


def main() -> int:
    client_dir, scratch_dir, *selected = sys.argv[1:]
    copy = Path(scratch_dir) / "client"
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(client_dir, copy, ignore=IGNORE)
    # test_i18n reads scripts/generate-pot.bat next to client/.
    (copy.parent / "scripts").mkdir(exist_ok=True)
    shutil.copy2(Path(client_dir).parent / "scripts" / "generate-pot.bat", copy.parent / "scripts" / "generate-pot.bat")
    status = 0
    for mutant in selected or list(MUTANTS):
        relative, old, new = MUTANTS[mutant]
        path = copy / relative
        original = path.read_bytes()
        text = original.decode("utf-8").replace("\r\n", "\n")
        if text.count(old) != 1:
            print(f"{mutant}: pattern found {text.count(old)} times in {relative}")
            status = 1
            continue
        path.write_bytes(text.replace(old, new).encode("utf-8"))
        try:
            completed = subprocess.run(
                [sys.executable, "-B", "-m", "unittest", *MODULES],
                cwd=copy, capture_output=True, text=True, encoding="utf-8",
            )
        finally:
            path.write_bytes(original)
        names = sorted({f"{where.split('.')[1]}.{test}" for test, where in FAILED.findall(completed.stderr)})
        shown = names if len(names) <= 4 else names[:4] + [f"and {len(names) - 4} more"]
        print(f"{mutant}: {len(names)} caught: {', '.join(shown) if names else 'NONE'}")
        if not names:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
````

File: `$T/tools/apply_blocks.py`

````python
"""Apply the File: and Edit: blocks of one step of the F-12 plan (throwaway, not committed).

Usage: python apply_blocks.py <plan.md> <repo> <T> "<task>" "<step>"
  for example: python apply_blocks.py plan.md D:/workspace/DotExpress-f12 <T> "Task 1" "Step 1"

The step is the "- [ ] **Step N" item under the "### Task N" heading. A File: block is
written as is (a path starting with $T goes under <T>, any other path under <repo>); an
Edit: block is the line "Edit: `path`" and the next two fenced blocks, the old text and
its replacement. The old text must occur exactly once in the file at that point
(compared with CRLF as LF; the file keeps its line endings). Blocks are applied in plan
order. Prints one line per block; stops with exit status 1 at the first block that does
not apply. Reads and writes bytes, so escapes such as \\u81fa stay as they are.
"""
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^(`{3,})[\w-]*\s*$")


def fenced(lines, start):
    """(body, index after the closing fence) of the first fenced block at or after ``start``."""
    index = start
    while not FENCE.match(lines[index]):
        index += 1
    fence = FENCE.match(lines[index]).group(1)
    end = index + 1
    while lines[end].strip() != fence:
        end += 1
    body = lines[index + 1:end]
    return "".join(line + "\n" for line in body), end + 1


def main() -> int:
    plan, repo, tdir, task, step = sys.argv[1:6]
    lines = Path(plan).read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n")
    in_task = in_step = False
    applied = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("### "):
            in_task = line.startswith(f"### {task}:")
            in_step = False
        elif line.startswith("- [ ] **Step"):
            in_step = in_task and line.startswith(f"- [ ] **{step}:")
        match = re.match(r"^(File|Edit): `([^`]+)`$", line) if in_step else None
        if not match:
            index += 1
            continue
        kind, path = match.groups()
        target = Path(tdir) / path[3:] if path.startswith("$T/") else Path(repo) / path
        if kind == "File":
            body, index = fenced(lines, index + 1)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body.encode("utf-8"))
            print(f"wrote {path}")
        else:
            old, index = fenced(lines, index + 1)
            new, index = fenced(lines, index)
            raw = target.read_bytes().decode("utf-8")
            crlf = "\r\n" in raw
            text = raw.replace("\r\n", "\n")
            count = text.count(old)
            if count != 1:
                print(f"edit of {path} (plan line {index}): old text found {count} times")
                return 1
            text = text.replace(old, new)
            target.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
            print(f"edited {path}")
        applied += 1
    print(f"{applied} blocks applied ({task}, {step})")
    return 0 if applied else 1


if __name__ == "__main__":
    sys.exit(main())
````

Write `apply_blocks.py` first by extracting it from this file as bytes (never through the Edit/Write tools), then let it write the step's blocks (it rewrites `apply_blocks.py` with the same bytes):

```bash
mkdir -p $T/tools
PLAN=$REPO/docs/superpowers/plans/2026-10-11-f12-localization-cleanup.md
$PY -c "import sys; from pathlib import Path; text = Path(sys.argv[1]).read_bytes().decode('utf-8').replace(chr(13) + chr(10), chr(10)); start = text.index('File: \`\$T/tools/apply_blocks.py\`'); body = text[text.index(chr(10), text.index('\`\`\`\`python', start)) + 1:text.index(chr(10) + '\`\`\`\`' + chr(10), start)]; Path(sys.argv[2]).write_bytes((body + chr(10)).encode('utf-8')); print('apply_blocks.py extracted')" "$PLAN" "$T/tools/apply_blocks.py"
$PY $T/tools/apply_blocks.py "$PLAN" $REPO $T "Task 0" "Step 3"
```

Expected:

```text
apply_blocks.py extracted
wrote $T/tools/brief.py
wrote $T/tools/msgid_scan.py
wrote $T/tools/shuffle_harness.py
wrote $T/tools/pin_pot_date.py
wrote $T/tools/mo_check.py
wrote $T/tools/po_entry.py
wrote $T/tools/f12_mutants.py
wrote $T/tools/apply_blocks.py
8 blocks applied (Task 0, Step 3)
```

From then on apply every step's blocks with `apply_blocks.py`, for example `$PY $T/tools/apply_blocks.py ../docs/superpowers/plans/2026-10-11-f12-localization-cleanup.md $REPO $T "Task 1" "Step 1"`; it prints `N blocks applied` (Task 0 Step 3: 8; Task 1 Step 1: 17, Step 2: 2, Step 5: 1; Task 2 Step 1: 13, Step 2: 17, Step 5: 1; Task 3 Step 1: 12, Step 2: 5, Step 5: 1; Task 4 Step 1: 8, Step 2: 7, Step 5: 2; Task 5 Step 1: 18, Step 2: 18, Step 5: 2; Task 6 Step 1: 4, Step 2: 3, Step 5: 1; Task 7 Step 1: 16, Step 2: 9, Step 5: 3; Task 8 Step 1: 3, Step 2: 1; Task 9 Step 2: 1).

- [x] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, catalogs, tree, application data.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_i18n tests.test_export_coordinator tests.test_conversion_presenter tests.test_conversion_text_dictionary_rules tests.test_workspace_service tests.test_config tests.test_gui_document_flows tests.test_document_workspace tests.test_conversion_service tests.test_translation_settings tests.test_translation_tables tests.test_view_settings tests.test_document_formats tests.test_dual_view_browser tests.test_user_preprocessing_script 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/translation_liblouis_golden.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "msgfmt rebuilds the committed .mo byte for byte"
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
$PY -I $T/tools/po_entry.py locales/zh_TW/LC_MESSAGES/dotexpress.po "Export Complete with Errors" "All documents were exported successfully." '"Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}"' "Imported file must be a valid DotExpress DEP package."
grep -rn "KNOWN BUG (P1-4 spec, defect 4)" tests | wc -l
git -C $REPO rev-parse HEAD:client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) > $T/app-data.sha256; wc -l < $T/app-data.sha256
for f in log workspace config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application data checked"
```

Expected (the second `Ran` line is the spec's acceptance-criterion-2 set without `tests.test_import_problems`, which Task 2 creates; the F-12 msgids are missing: the four strings to revive each have one obsolete copy and no active entry; six KNOWN BUG pins; the number after the tree id counts the files of the user's application data in the main checkout, including `client/log/`, recorded read-only for Task 10; if the user has used the app since the dry run, that number differs, which is fine; the worktree has no application data):

```text
Ran 1567 tests
OK (skipped=6)
Ran 611 tests
OK (skipped=2)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e *-
source msgids: 381 sha256 f7045463d8f2d240dbfdbe52dba9eb4b077c5c4e7f41576b8e24443e28766f20
locales/dotexpress.pot:382
locales/zh_TW/LC_MESSAGES/dotexpress.po:382
31
381 translated messages.
msgfmt rebuilds the committed .mo byte for byte
catalog keys: 382
 1 '(missing)'
 2 '(missing)'
 3 '(missing)'
 4 '(missing)'
 5 '(missing)'
 6 '(missing)'
 7 '(missing)'
 8 '(missing)'
 9 '(missing)'
10 '(missing)'
11 '(missing)'
12 '(missing)'
13 '(missing)'
14 '(missing)'
15 '(missing)'
16 '(missing)'
17 '(missing)'
18 '(missing)'
19 '(missing)'
20 '(missing)'
21 '(missing)'
22 '(missing)'
23 '(missing)'
'Export Complete with Errors': active 0, fuzzy no, obsolete copies 1
'All documents were exported successfully.': active 0, fuzzy no, obsolete copies 1
'Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}': active 0, fuzzy no, obsolete copies 1
'Imported file must be a valid DotExpress DEP package.': active 0, fuzzy no, obsolete copies 1
6
5e130210420bf7a3828936094ac0af5868c32801
4
worktree application data checked
```

### Task 1: Translate the Export All summary and the conversion fallback texts (D1, D2)

- [x] **Step 1: Red: Test Plan B, C1, A (strings 1-5).** `test_export_coordinator.py` (4 spaces): the two `KNOWN BUG (P1-4 spec, defect 4)` pins and every other Export All summary of the module expect the zh_TW texts (`ALL_EXPORTED`, `EXPORTED_WITH_ERRORS`, `成功匯出的文件：N` / `匯出失敗的文件：N`). `test_gui_document_flows.py` (4 spaces): the same for the frame's summaries (two pins), and the frame twin of the fallback-text test expects `發生不明的錯誤。` and `選取的轉譯表無法轉譯這段文字。` (a pin). `test_conversion_presenter.py` (4 spaces): `test_format_conversion_error_public_texts` likewise (a pin). `test_i18n.py` (4 spaces): strings 1-5, and a guard that the four constants of `export_results.py` are `N_` calls and that `get_public_error_message` returns `N_` calls (AST, Test Plan A3). The expected summaries are zh_TW literals: what the user sees**

Edit: `client/tests/test_export_coordinator.py`

```python
LOGGER = "dotexpress.gui"
# Half of a surrogate pair, as pasting part of an emoji can leave it in an editor (F-5 review M-7).
LONE_SURROGATE = chr(0xD83D)


def setUpModule() -> None:
```

```python
LOGGER = "dotexpress.gui"
# Half of a surrogate pair, as pasting part of an emoji can leave it in an editor (F-5 review M-7).
LONE_SURROGATE = chr(0xD83D)
# The Export All summary as the user sees it (F-12 D1; it was English, P1-4 defect 4).
ALL_EXPORTED = "所有文件皆已成功匯出。"
EXPORTED_WITH_ERRORS = "匯出完成，但有錯誤"


def setUpModule() -> None:
```

Edit: `client/tests/test_export_coordinator.py`

```python
        return ("show_info", _("The document was exported successfully."), _("Export Complete"))

    def _all_exported(self) -> tuple:
        # KNOWN BUG (P1-4 spec, defect 4): the message is not a msgid; only the caption is translated.
        return ("show_info", "All documents were exported successfully.", _("Export Complete"))

    def _os_error_text(self, path: Path) -> str:
        try:
```

```python
        return ("show_info", _("The document was exported successfully."), _("Export Complete"))

    def _all_exported(self) -> tuple:
        return ("show_info", ALL_EXPORTED, "匯出完成")

    def _os_error_text(self, path: Path) -> str:
        try:
```

Edit: `client/tests/test_export_coordinator.py`

```python
        on_error("Translation failed")
        self.calls.run_all()

        # KNOWN BUG (P1-4 spec, defect 4): the partial-export summary is not translated.
        self.assertEqual(
            self._take()[-1],
            (
                "show_warning",
                f"Exported documents: 1\nFailed documents: 2\n\nconvert-fail: Translation failed\nwrite-fail: {reason}",
                "Export Complete with Errors",
            ),
        )
        self.assertEqual(self._written(), {"alpha.brl": "⠁"})
```

```python
        on_error("Translation failed")
        self.calls.run_all()

        self.assertEqual(
            self._take()[-1],
            (
                "show_warning",
                f"成功匯出的文件：1\n匯出失敗的文件：2\n\nconvert-fail: Translation failed\nwrite-fail: {reason}",
                EXPORTED_WITH_ERRORS,
            ),
        )
        self.assertEqual(self._written(), {"alpha.brl": "⠁"})
```

Edit: `client/tests/test_export_coordinator.py`

```python
            [
                (
                    "show_warning",
                    f"Exported documents: 0\nFailed documents: 2\n\nalpha: {MISSING_TABLE}\nbeta: {MISSING_TABLE}",
                    "Export Complete with Errors",
                )
            ],
        )
```

```python
            [
                (
                    "show_warning",
                    f"成功匯出的文件：0\n匯出失敗的文件：2\n\nalpha: {MISSING_TABLE}\nbeta: {MISSING_TABLE}",
                    EXPORTED_WITH_ERRORS,
                )
            ],
        )
```

Edit: `client/tests/test_export_coordinator.py`

```python
                ("call_after",),
                (
                    "show_warning",
                    f"Exported documents: 0\nFailed documents: 2\n\nalpha: {reason}\nbeta: {reason}",
                    "Export Complete with Errors",
                ),
            ],
        )
```

```python
                ("call_after",),
                (
                    "show_warning",
                    f"成功匯出的文件：0\n匯出失敗的文件：2\n\nalpha: {reason}\nbeta: {reason}",
                    EXPORTED_WITH_ERRORS,
                ),
            ],
        )
```

Edit: `client/tests/test_export_coordinator.py`

```python
            self._take()[-1],
            (
                "show_warning",
                "Exported documents: 2\nFailed documents: 1\n\nbeta: injected",
                "Export Complete with Errors",
            ),
        )
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})
```

```python
            self._take()[-1],
            (
                "show_warning",
                "成功匯出的文件：2\n匯出失敗的文件：1\n\nbeta: injected",
                EXPORTED_WITH_ERRORS,
            ),
        )
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})
```

Edit: `client/tests/test_export_coordinator.py`

```python
                ("call_after",),
                (
                    "show_warning",
                    "Exported documents: 2\nFailed documents: 1\n\nbroken: "
                    + _("Translation failed: {error}").format(error="bad"),
                    "Export Complete with Errors",
                ),
            ],
        )
```

```python
                ("call_after",),
                (
                    "show_warning",
                    "成功匯出的文件：2\n匯出失敗的文件：1\n\nbroken: "
                    + _("Translation failed: {error}").format(error="bad"),
                    EXPORTED_WITH_ERRORS,
                ),
            ],
        )
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            ),
            (ConversionStageError("translation", RuntimeError("boom")), gui._("Translation failed: {error}"), "boom"),
            (ConversionStageError("other", RuntimeError("odd")), gui._("Translation failed: {error}"), "odd"),
            # KNOWN BUG (P1-4 spec, defect 4): the two public fallback texts are not msgids, so they stay English.
            (
                ConversionStageError("translation", RuntimeError("")),
                gui._("Translation failed: {error}"),
                "An unknown error occurred.",
            ),
            (
                ConversionStageError("translation", RuntimeError("Can't translate: tables zh-tw.ctb inbuf=12")),
                gui._("Translation failed: {error}"),
                "The selected translation table could not translate this text.",
            ),
        )
        for error, template, error_text in cases:
```

```python
            ),
            (ConversionStageError("translation", RuntimeError("boom")), gui._("Translation failed: {error}"), "boom"),
            (ConversionStageError("other", RuntimeError("odd")), gui._("Translation failed: {error}"), "odd"),
            # The two public fallback texts are msgids since F-12 (D2; were English, P1-4 defect 4).
            (
                ConversionStageError("translation", RuntimeError("")),
                gui._("Translation failed: {error}"),
                "發生不明的錯誤。",
            ),
            (
                ConversionStageError("translation", RuntimeError("Can't translate: tables zh-tw.ctb inbuf=12")),
                gui._("Translation failed: {error}"),
                "選取的轉譯表無法轉譯這段文字。",
            ),
        )
        for error, template, error_text in cases:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        )

        self.calls.run_next()
        # KNOWN BUG (P1-4 spec, defect 4): the partial-export summary is not translated.
        summary = (
            "Exported documents: 4\n"
            "Failed documents: 2\n"
            "\n"
            f"d4-write-fail: {write_reason}\n"
            f"d5-convert-fail: {gui._('Translation failed: {error}').format(error='t5 boom')}"
        )
        self.assertEqual(
            self._take(),
            [self._box(frame, summary, "Export Complete with Errors", gui.wx.OK | gui.wx.ICON_WARNING)],
        )
        self.assertEqual(self.calls.pending, [])
        self.assertEqual(
```

```python
        )

        self.calls.run_next()
        # The Export All summary in zh_TW (F-12 D1; was English, P1-4 defect 4).
        summary = (
            "成功匯出的文件：4\n"
            "匯出失敗的文件：2\n"
            "\n"
            f"d4-write-fail: {write_reason}\n"
            f"d5-convert-fail: {gui._('Translation failed: {error}').format(error='t5 boom')}"
        )
        self.assertEqual(
            self._take(),
            [self._box(frame, summary, "匯出完成，但有錯誤", gui.wx.OK | gui.wx.ICON_WARNING)],
        )
        self.assertEqual(self.calls.pending, [])
        self.assertEqual(
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._take(), [("call_after",)])
        self.calls.run_next()

        # KNOWN BUG (P1-4 spec, defect 4): the message is not a msgid; only the caption is translated.
        self.assertEqual(
            self._take(),
            [self._info(frame, "All documents were exported successfully.", gui._("Export Complete"))],
        )
        self.assertEqual(sorted(path.name for path in self.export_dir.iterdir()), ["alpha.brl", "beta.brl"])

```

```python
        self.assertEqual(self._take(), [("call_after",)])
        self.calls.run_next()

        # The Export All summary in zh_TW (F-12 D1; was English, P1-4 defect 4).
        self.assertEqual(
            self._take(),
            [self._info(frame, "所有文件皆已成功匯出。", "匯出完成")],
        )
        self.assertEqual(sorted(path.name for path in self.export_dir.iterdir()), ["alpha.brl", "beta.brl"])

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._take(), [("call_after",)])
        self.calls.run_next()

        summary = f"Exported documents: 0\nFailed documents: 2\n\np1: {message}\np2: {message}"
        self.assertEqual(
            self._take(),
            [self._box(frame, summary, "Export Complete with Errors", gui.wx.OK | gui.wx.ICON_WARNING)],
        )
        self.assertEqual(self.threads, [])
        self.assertEqual(list(self.export_dir.iterdir()), [])
```

```python
        self.assertEqual(self._take(), [("call_after",)])
        self.calls.run_next()

        summary = f"成功匯出的文件：0\n匯出失敗的文件：2\n\np1: {message}\np2: {message}"
        self.assertEqual(
            self._take(),
            [self._box(frame, summary, "匯出完成，但有錯誤", gui.wx.OK | gui.wx.ICON_WARNING)],
        )
        self.assertEqual(self.threads, [])
        self.assertEqual(list(self.export_dir.iterdir()), [])
```

Edit: `client/tests/test_gui_document_flows.py`

```python
                self._overwrite_question(frame),
                ("call_after",),
                ("call_after",),
                self._info(frame, "All documents were exported successfully.", gui._("Export Complete")),
            ],
        )
        self.assertEqual((self.export_dir / "alpha.brl").read_text(encoding="utf-8"), "⠁")
```

```python
                self._overwrite_question(frame),
                ("call_after",),
                ("call_after",),
                self._info(frame, "所有文件皆已成功匯出。", "匯出完成"),
            ],
        )
        self.assertEqual((self.export_dir / "alpha.brl").read_text(encoding="utf-8"), "⠁")
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        self.assertEqual(
            self._boxes(),
            [self._exported_box(), ("All documents were exported successfully.", gui._("Export Complete"))],
        )
        self.assertEqual([request.raw_text for request in self.requests], ["t0", "t0", "t1", "t2"])
        self.assertEqual(self._written(), {"open.brl": "⠴", "p1.brl": "⠂", "p2.brl": "⠆"})
```

```python

        self.assertEqual(
            self._boxes(),
            [self._exported_box(), ("所有文件皆已成功匯出。", "匯出完成")],
        )
        self.assertEqual([request.raw_text for request in self.requests], ["t0", "t0", "t1", "t2"])
        self.assertEqual(self._written(), {"open.brl": "⠴", "p1.brl": "⠂", "p2.brl": "⠆"})
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [self._info(frame, "All documents were exported successfully.", gui._("Export Complete"))],
        )
        self.assertEqual(frame.output_txt.value, "⠍")
        self.assertEqual((self.export_dir / "p1.brl").read_text(encoding="utf-8"), "⠃")
```

```python
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [self._info(frame, "所有文件皆已成功匯出。", "匯出完成")],
        )
        self.assertEqual(frame.output_txt.value, "⠍")
        self.assertEqual((self.export_dir / "p1.brl").read_text(encoding="utf-8"), "⠃")
```

Edit: `client/tests/test_conversion_presenter.py`

```python
                )

    def test_format_conversion_error_public_texts(self) -> None:
        # KNOWN BUG (P1-4 spec, defect 4): the two public fallback texts are not msgids, so they stay English.
        for raw, public in (
            ("", "An unknown error occurred."),
            ("Can't translate: tables zh-tw.ctb inbuf=12", "The selected translation table could not translate this text."),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(
```

```python
                )

    def test_format_conversion_error_public_texts(self) -> None:
        # The two public fallback texts are msgids since F-12 (D2; were English, P1-4 defect 4).
        for raw, public in (
            ("", "發生不明的錯誤。"),
            ("Can't translate: tables zh-tw.ctb inbuf=12", "選取的轉譯表無法轉譯這段文字。"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(
```

Edit: `client/tests/test_i18n.py`

```python
            translation.gettext(message),
            "無法儲存字典「{name}」：無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。",
        )

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```python
            translation.gettext(message),
            "無法儲存字典「{name}」：無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。",
        )

    def test_export_summary_and_conversion_fallback_strings_are_translated(self) -> None:
        # F-12 (D1, D2): the Export All summary (its three texts revived from obsolete catalog
        # entries) and the two public conversion fallback texts; all were English (P1-4 defect 4).
        expected = {
            "Export Complete with Errors": "匯出完成，但有錯誤",
            "All documents were exported successfully.": "所有文件皆已成功匯出。",
            "Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}": (
                "成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}"
            ),
            "An unknown error occurred.": "發生不明的錯誤。",
            "The selected translation table could not translate this text.": "選取的轉譯表無法轉譯這段文字。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

Edit: `client/tests/test_i18n.py`

```python
        self.assertEqual(len(self.FORMER_MARKER_MSGIDS), 44)
        self.assertEqual(sorted(set(self.FORMER_MARKER_MSGIDS) - extracted), [])

    def test_generate_pot_extracts_n_keyword(self) -> None:
        script = (CLIENT_ROOT.parent / "scripts" / "generate-pot.bat").read_text(encoding="utf-8")

```

```python
        self.assertEqual(len(self.FORMER_MARKER_MSGIDS), 44)
        self.assertEqual(sorted(set(self.FORMER_MARKER_MSGIDS) - extracted), [])

    def test_export_summary_and_conversion_fallback_texts_are_marked_where_defined(self) -> None:
        # F-12 (D1, D2): these values are translated where they are shown, so each must be an
        # N_ call where it is defined, or it stays English.
        tree = _module_tree("documents/export_results.py")
        values = {
            target.id: node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        names = (
            "EXPORT_COMPLETE_TITLE",
            "EXPORT_COMPLETE_WITH_ERRORS_TITLE",
            "EXPORT_ALL_SUCCESS_MESSAGE",
            "EXPORT_ALL_PARTIAL_MESSAGE",
        )
        self.assertEqual(
            {name: ast.unparse(values[name].func) if isinstance(values[name], ast.Call) else None for name in names},
            dict.fromkeys(names, "N_"),
        )
        returns = [
            ast.unparse(node.value)
            for node in sorted(
                (node for node in ast.walk(_module_tree("conversion/plain_text.py")) if isinstance(node, ast.Return)),
                key=lambda node: node.lineno,
            )
        ]
        self.assertEqual(
            returns,
            [
                "N_('An unknown error occurred.')",
                "N_('The selected translation table could not translate this text.')",
                "message",
            ],
        )

    def test_generate_pot_extracts_n_keyword(self) -> None:
        script = (CLIENT_ROOT.parent / "scripts" / "generate-pot.bat").read_text(encoding="utf-8")

```

```bash
$PY -B -X utf8 -m unittest tests.test_export_coordinator tests.test_gui_document_flows tests.test_conversion_presenter tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
FAIL: test_export_all_asks_about_conflicts_only_when_needed (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_asks_about_conflicts_only_when_
AssertionError: Lists differ: [('ch[64 chars]ow_info', 'All documents were exported successfully.', '匯出完成')] != [('ch[64 chars]ow_info', '所有文件皆已成功匯出。', '匯出完成')]
FAIL: test_export_all_goes_on_after_an_error_that_is_not_an_os_error (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_goes_on_after_an_error
AssertionError: Tuples differ: ('show_warning', 'Exported documents: 2\nFailed documents: [47 chars]ors') != ('show_warning', '成功匯出的文件：2\n匯出失敗的文件：1\n\nbeta: inj
FAIL: test_export_all_html_uses_each_pending_documents_conversion (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_html_uses_each_pending_do
AssertionError: Tuples differ: ('show_info', 'All documents were exported successfully.', '匯出完成') != ('show_info', '所有文件皆已成功匯出。', '匯出完成')
FAIL: test_export_all_missing_table_accumulates_failures_without_per_file_messages (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_missing_
AssertionError: Lists differ: [('show_warning', 'Exported documents: 0\nFailed documents: [75 chars]rs')] != [('show_warning', '成功匯出的文件：0\n匯出失敗的文件：2\n\nalpha: m
FAIL: test_export_all_partial_failure_summary_lists_each_failure (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_partial_failure_summary_li
AssertionError: Tuples differ: ('show_warning', "Exported documents: 1\nFailed documents: [192 chars]ors') != ('show_warning', "成功匯出的文件：1\n匯出失敗的文件：2\n\nconvert-
FAIL: test_export_all_runs_first_step_now_and_each_later_step_in_its_own_turn (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_runs_first_st
AssertionError: Lists differ: [('show_info', 'All documents were exported successfully.', '匯出完成')] != [('show_info', '所有文件皆已成功匯出。', '匯出完成')]
FAIL: test_export_all_writer_value_error_is_listed_and_the_chain_goes_on (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_writer_value_error
AssertionError: Lists differ: [('ch[73 chars]g', 'Exported documents: 0\nFailed documents: [115 chars]rs')] != [('ch[73 chars]g', '成功匯出的文件：0\n匯出失敗的文件：2\n\nalpha
FAIL: test_export_all_with_a_real_presenter_turn_by_turn (tests.test_export_coordinator.ExportThroughConversionPresenterTest.test_export_all_with_a_real_present
AssertionError: Lists differ: [('ch[440 chars]g', 'Exported documents: 2\nFailed documents: [50 chars]rs')] != [('ch[440 chars]g', '成功匯出的文件：2\n匯出失敗的文件：1\n\nbrok
FAIL: test_conversion_failure_messages_by_stage_and_public_text (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_conversion_failure
AssertionError: Lists differ: [('ti[172 chars]轉譯失敗：An unknown error occurred.', '錯誤', 516, <[43 chars]<addr>)] != [('ti[172 chars]轉譯失敗：發生不明的錯誤。', '錯誤', 516, <gu
AssertionError: Lists differ: [('ti[172 chars]轉譯失敗：The selected translation table could not [78 chars]<addr>)] != [('ti[172 chars]轉譯失敗：選取的轉譯表無法轉譯這段文字。', '錯誤', 5
FAIL: test_convert_between_export_all_steps_completes_before_the_next_step (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_convert
AssertionError: Lists differ: [('MessageBox', 'All documents were exported successfully.[60 chars]<addr>)] != [('MessageBox', '所有文件皆已成功匯出。', '匯出完成', 132, <gui.B
FAIL: test_ctrl_s_during_export_all_waits_and_the_summary_appears (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_ctrl_s_during_ex
AssertionError: Lists differ: [('文件已成功匯出。', '匯出完成'), ('All documents were exported successfully.', '匯出完成')] != [('文件已成功匯出。', '匯出完成'), ('所有文件皆已成功匯出。', '匯出完成')]
FAIL: test_export_all_folder_and_overwrite_dialogs (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_export_all_folder_and_overwrite
AssertionError: Lists differ: [('Di[224 chars]x', 'All documents were exported successfully.[60 chars]<addr>)] != [('Di[224 chars]x', '所有文件皆已成功匯出。', '匯出完成', 132
FAIL: test_export_all_mixed_documents_turn_by_turn (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_export_all_mixed_documents_turn
AssertionError: Lists differ: [('MessageBox', "Exported documents: 4\nFailed documents: [260 chars]<addr>)] != [('MessageBox', "成功匯出的文件：4\n匯出失敗的文件：2\n\nd4-write
FAIL: test_export_all_ready_documents_shows_one_information_summary (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_export_all_rea
FAIL: test_export_all_without_default_table_collects_failures_turn_by_turn (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_export_
AssertionError: Lists differ: [('MessageBox', 'Exported documents: 0\nFailed documents: [114 chars]<addr>)] != [('MessageBox', '成功匯出的文件：0\n匯出失敗的文件：2\n\np1: 請先選擇
FAIL: test_format_conversion_error_public_texts (tests.test_conversion_presenter.ConversionPresenterTest.test_format_conversion_error_public_texts) (raw='')
AssertionError: '轉譯失敗：An unknown error occurred.' != '轉譯失敗：發生不明的錯誤。'
FAIL: test_format_conversion_error_public_texts (tests.test_conversion_presenter.ConversionPresenterTest.test_format_conversion_error_public_texts) (raw="Can't
AssertionError: '轉譯失敗：The selected translation table could not translate this text.' != '轉譯失敗：選取的轉譯表無法轉譯這段文字。'
FAIL: test_export_summary_and_conversion_fallback_texts_are_marked_where_defined (tests.test_i18n.ExtractionMarkerTest.test_export_summary_and_conversion_fallba
AssertionError: {'EXP[16 chars]LE': None, 'EXPORT_COMPLETE_WITH_ERRORS_TITLE'[74 chars]None} != {'EXP[16 chars]LE': 'N_', 'EXPORT_COMPLETE_WITH_ERRORS_TITLE'[74
FAIL: test_export_summary_and_conversion_fallback_strings_are_translated (tests.test_i18n.TranslationTest.test_export_summary_and_conversion_fallback_strings_ar
AssertionError: {'Exp[23 chars]s': 'Export Complete with Errors', 'All docume[439 chars]xt.'} != {'Exp[23 chars]s': '匯出完成，但有錯誤', 'All documents were exported [3
Ran 306 tests
FAILED (failures=20)
```

- [x] **Step 2: Green: mark the texts with `N_`** (`client/documents/export_results.py`, `client/conversion/plain_text.py`, 4 spaces). `_show_batch_result` and `format_conversion_error` already translate them where they are shown.**

Edit: `client/documents/export_results.py`

```python

from dataclasses import dataclass, field


EXPORT_COMPLETE_TITLE = "Export Complete"
EXPORT_COMPLETE_WITH_ERRORS_TITLE = "Export Complete with Errors"
EXPORT_ALL_SUCCESS_MESSAGE = "All documents were exported successfully."
EXPORT_ALL_PARTIAL_MESSAGE = (
    "Exported documents: {success_count}\n"
    "Failed documents: {failure_count}\n"
    "\n"
```

```python

from dataclasses import dataclass, field

from i18n import N_

# msgids, translated where the summary is shown (ExportCoordinator._show_batch_result; F-12 D1).
EXPORT_COMPLETE_TITLE = N_("Export Complete")
EXPORT_COMPLETE_WITH_ERRORS_TITLE = N_("Export Complete with Errors")
EXPORT_ALL_SUCCESS_MESSAGE = N_("All documents were exported successfully.")
EXPORT_ALL_PARTIAL_MESSAGE = N_(
    "Exported documents: {success_count}\n"
    "Failed documents: {failure_count}\n"
    "\n"
```

Edit: `client/conversion/plain_text.py`

```python
def get_public_error_message(error: Exception) -> str:
    message = str(error)
    if not message:
        return "An unknown error occurred."
    if "Can't translate: tables" in message and "inbuf" in message:
        return "The selected translation table could not translate this text."
    return message
```

```python
from i18n import N_


def get_public_error_message(error: Exception) -> str:
    """The text of ``error``; a msgid for an empty text and for liblouis' "Can't translate".

    ``format_conversion_error`` translates the result (F-12 D2).
    """
    message = str(error)
    if not message:
        return N_("An unknown error occurred.")
    if "Can't translate: tables" in message and "inbuf" in message:
        return N_("The selected translation table could not translate this text.")
    return message
```

- [x] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_export_coordinator tests.test_gui_document_flows tests.test_conversion_presenter tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (only the tests that compare with the zh_TW text fail: the new msgids are not in the catalog yet):

```text
FAIL: test_export_all_asks_about_conflicts_only_when_needed (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_asks_about_conflicts_only_when_
AssertionError: Lists differ: [('ch[64 chars]ow_info', 'All documents were exported successfully.', '匯出完成')] != [('ch[64 chars]ow_info', '所有文件皆已成功匯出。', '匯出完成')]
FAIL: test_export_all_goes_on_after_an_error_that_is_not_an_os_error (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_goes_on_after_an_error
AssertionError: Tuples differ: ('show_warning', 'Exported documents: 2\nFailed documents: [47 chars]ors') != ('show_warning', '成功匯出的文件：2\n匯出失敗的文件：1\n\nbeta: inj
FAIL: test_export_all_html_uses_each_pending_documents_conversion (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_html_uses_each_pending_do
AssertionError: Tuples differ: ('show_info', 'All documents were exported successfully.', '匯出完成') != ('show_info', '所有文件皆已成功匯出。', '匯出完成')
FAIL: test_export_all_missing_table_accumulates_failures_without_per_file_messages (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_missing_
AssertionError: Lists differ: [('show_warning', 'Exported documents: 0\nFailed documents: [75 chars]rs')] != [('show_warning', '成功匯出的文件：0\n匯出失敗的文件：2\n\nalpha: m
FAIL: test_export_all_partial_failure_summary_lists_each_failure (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_partial_failure_summary_li
AssertionError: Tuples differ: ('show_warning', "Exported documents: 1\nFailed documents: [192 chars]ors') != ('show_warning', "成功匯出的文件：1\n匯出失敗的文件：2\n\nconvert-
FAIL: test_export_all_runs_first_step_now_and_each_later_step_in_its_own_turn (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_runs_first_st
AssertionError: Lists differ: [('show_info', 'All documents were exported successfully.', '匯出完成')] != [('show_info', '所有文件皆已成功匯出。', '匯出完成')]
FAIL: test_export_all_writer_value_error_is_listed_and_the_chain_goes_on (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_writer_value_error
AssertionError: Lists differ: [('ch[73 chars]g', 'Exported documents: 0\nFailed documents: [115 chars]rs')] != [('ch[73 chars]g', '成功匯出的文件：0\n匯出失敗的文件：2\n\nalpha
FAIL: test_export_all_with_a_real_presenter_turn_by_turn (tests.test_export_coordinator.ExportThroughConversionPresenterTest.test_export_all_with_a_real_present
AssertionError: Lists differ: [('ch[440 chars]g', 'Exported documents: 2\nFailed documents: [50 chars]rs')] != [('ch[440 chars]g', '成功匯出的文件：2\n匯出失敗的文件：1\n\nbrok
FAIL: test_conversion_failure_messages_by_stage_and_public_text (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_conversion_failure
AssertionError: Lists differ: [('ti[172 chars]轉譯失敗：An unknown error occurred.', '錯誤', 516, <[43 chars]<addr>)] != [('ti[172 chars]轉譯失敗：發生不明的錯誤。', '錯誤', 516, <gu
AssertionError: Lists differ: [('ti[172 chars]轉譯失敗：The selected translation table could not [78 chars]<addr>)] != [('ti[172 chars]轉譯失敗：選取的轉譯表無法轉譯這段文字。', '錯誤', 5
FAIL: test_convert_between_export_all_steps_completes_before_the_next_step (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_convert
AssertionError: Lists differ: [('MessageBox', 'All documents were exported successfully.[60 chars]<addr>)] != [('MessageBox', '所有文件皆已成功匯出。', '匯出完成', 132, <gui.B
FAIL: test_ctrl_s_during_export_all_waits_and_the_summary_appears (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_ctrl_s_during_ex
AssertionError: Lists differ: [('文件已成功匯出。', '匯出完成'), ('All documents were exported successfully.', '匯出完成')] != [('文件已成功匯出。', '匯出完成'), ('所有文件皆已成功匯出。', '匯出完成')]
FAIL: test_export_all_folder_and_overwrite_dialogs (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_export_all_folder_and_overwrite
AssertionError: Lists differ: [('Di[224 chars]x', 'All documents were exported successfully.[60 chars]<addr>)] != [('Di[224 chars]x', '所有文件皆已成功匯出。', '匯出完成', 132
FAIL: test_export_all_mixed_documents_turn_by_turn (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_export_all_mixed_documents_turn
AssertionError: Lists differ: [('MessageBox', "Exported documents: 4\nFailed documents: [260 chars]<addr>)] != [('MessageBox', "成功匯出的文件：4\n匯出失敗的文件：2\n\nd4-write
FAIL: test_export_all_ready_documents_shows_one_information_summary (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_export_all_rea
FAIL: test_export_all_without_default_table_collects_failures_turn_by_turn (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_export_
AssertionError: Lists differ: [('MessageBox', 'Exported documents: 0\nFailed documents: [114 chars]<addr>)] != [('MessageBox', '成功匯出的文件：0\n匯出失敗的文件：2\n\np1: 請先選擇
FAIL: test_format_conversion_error_public_texts (tests.test_conversion_presenter.ConversionPresenterTest.test_format_conversion_error_public_texts) (raw='')
AssertionError: '轉譯失敗：An unknown error occurred.' != '轉譯失敗：發生不明的錯誤。'
FAIL: test_format_conversion_error_public_texts (tests.test_conversion_presenter.ConversionPresenterTest.test_format_conversion_error_public_texts) (raw="Can't
AssertionError: '轉譯失敗：The selected translation table could not translate this text.' != '轉譯失敗：選取的轉譯表無法轉譯這段文字。'
FAIL: test_export_summary_and_conversion_fallback_strings_are_translated (tests.test_i18n.TranslationTest.test_export_summary_and_conversion_fallback_strings_ar
AssertionError: {'Exp[23 chars]s': 'Export Complete with Errors', 'All docume[439 chars]xt.'} != {'Exp[23 chars]s': '匯出完成，但有錯誤', 'All documents were exported [3
Ran 306 tests
FAILED (failures=19)
```

- [x] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
$PY -I $T/tools/po_entry.py locales/zh_TW/LC_MESSAGES/dotexpress.po "Export Complete with Errors" "All documents were exported successfully." '"Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}"'
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected:

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
384 translated messages, 1 fuzzy translation, 1 untranslated message.
#: conversion/plain_text.py:13
#, fuzzy
msgid "The selected translation table could not translate this text."
msgstr "請先選擇轉譯表。"
#: conversion/plain_text.py:11
msgid "An unknown error occurred."
msgstr ""
'Export Complete with Errors': active 1, fuzzy no, obsolete copies 0, msgstr '匯出完成，但有錯誤'
'All documents were exported successfully.': active 1, fuzzy no, obsolete copies 0, msgstr '所有文件皆已成功匯出。'
'Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}': active 1, fuzzy no, obsolete copies 0, msgstr '成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}'
28
```

- [x] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po

#: conversion/plain_text.py:11
msgid "An unknown error occurred."
msgstr ""

#: conversion/plain_text.py:13
#, fuzzy
msgid "The selected translation table could not translate this text."
msgstr "請先選擇轉譯表。"

#: conversion/preprocessing/user_script.py:40
msgid "The script must define exactly one top-level synchronous main function."
```

```po

#: conversion/plain_text.py:11
msgid "An unknown error occurred."
msgstr "發生不明的錯誤。"

#: conversion/plain_text.py:13
msgid "The selected translation table could not translate this text."
msgstr "選取的轉譯表無法轉譯這段文字。"

#: conversion/preprocessing/user_script.py:40
msgid "The script must define exactly one top-level synchronous main function."
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
a second msgmerge changes nothing
msgfmt exit 0
386 translated messages.
0
catalog keys: 387
 1 '匯出完成，但有錯誤'
 2 '所有文件皆已成功匯出。'
 3 '成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}'
 4 '發生不明的錯誤。'
 5 '選取的轉譯表無法轉譯這段文字。'
 6 '(missing)'
 7 '(missing)'
 8 '(missing)'
 9 '(missing)'
10 '(missing)'
11 '(missing)'
12 '(missing)'
13 '(missing)'
14 '(missing)'
15 '(missing)'
16 '(missing)'
17 '(missing)'
18 '(missing)'
19 '(missing)'
20 '(missing)'
21 '(missing)'
22 '(missing)'
23 '(missing)'
31244
locales/dotexpress.pot:387
locales/zh_TW/LC_MESSAGES/dotexpress.po:387
28
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 386 sha256 9f43d41592a51bd8527ee96c41e6274b8c5909803aa145847d651e5c80bc9d87
```

- [x] **Step 6: Green: the new tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_export_coordinator tests.test_gui_document_flows tests.test_conversion_presenter tests.test_i18n -v 2>&1 | grep -E "^(test_export_summary_and_conversion_fallback_strings_are_translated|test_export_summary_and_conversion_fallback_texts_are_marked_where_defined) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_export_coordinator tests.test_gui_document_flows tests.test_conversion_presenter tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (each new test once per subTest-free run, in the order unittest runs them):

```text
test_export_summary_and_conversion_fallback_texts_are_marked_where_defined ok
test_export_summary_and_conversion_fallback_strings_are_translated ok
Ran 306 tests
OK
Ran 1569 tests
OK (skipped=6)
```

- [x] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_export_coordinator.py client/tests/test_gui_document_flows.py client/tests/test_conversion_presenter.py client/tests/test_i18n.py client/documents/export_results.py client/conversion/plain_text.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: translate the Export All summary and the conversion fallback texts (F-12, P1-4 defect 4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/conversion/plain_text.py                |  11 ++++-
 client/documents/export_results.py             |  10 +++--
 client/locales/dotexpress.pot                  |  27 ++++++++++++-
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 30650 -> 31244 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po |  48 +++++++++++++---------
 client/tests/test_conversion_presenter.py      |   6 +--
 client/tests/test_export_coordinator.py        |  27 +++++++------
 client/tests/test_gui_document_flows.py        |  28 ++++++-------
 client/tests/test_i18n.py                      |  53 +++++++++++++++++++++++++
 9 files changed, 155 insertions(+), 55 deletions(-)
b6d32d26860d0a9cdee68f3bd81634ec529d0efd
```

### Task 2: Explain why an imported file was skipped (D3)

- [x] **Step 1: Red: Test Plan E, A (strings 10-15).** `test_import_problems.py` (new, 4 spaces): each row of the D3 table through `describe_import_problem` with the errors the loaders raise (a Big5 `.txt`, a `PermissionError`, the four name codes, the extension refusals of `load_text_document`, `import_pdf`, `import_epub`, the three package refusals, an encrypted PDF written with pypdf's `encrypt`, an EPUB without spine and one with a missing spine item, a package that is not a zip, one with metadata that is not JSON, one whose text is not UTF-8, a `KeyError`, and errors shown with their own text), `str()` of an `ImportProblem` English, no wx or `dictionaries` import. `test_document_workspace.py` (4 spaces): the batch's reasons in zh_TW, every reason of probe 1 that a Windows file system can hold, a package the loader refuses still counted invalid at startup (E5). `test_workspace_service.py` (4 spaces): a listed duplicate gives `文件「X」已存在。`, a failed package write `儲存文件失敗：...`. `test_gui_document_flows.py` (4 spaces): the Import Issues lines of the frame in zh_TW. `test_i18n.py`: strings 10-15**

File: `client/tests/test_import_problems.py`

````python
"""Why an imported file was skipped (F-12 D3): the reasons of the Import Issues dialog."""

from __future__ import annotations

import ast
import errno
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pypdf import PdfWriter

from documents.import_problems import ImportProblem, describe_import_problem
from documents.importers import import_epub, import_pdf
from documents.workspace import load_document_package, load_text_document
from shared.name_validation import NameValidationError

MODULE_PATH = Path(__file__).resolve().parents[1] / "documents" / "import_problems.py"
# The zh_TW reasons as the user sees them.
NOT_UTF8 = "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"
CANNOT_OPEN = "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。"
NAME_LENGTH = "文件名稱長度需為 1 到 32 個字元。"
NAME_INVALID = "文件名稱不是有效的 Windows 檔名。"
UNSUPPORTED = "無法匯入這種類型的檔案。"
WRONG_EXTENSION = "副檔名與選取的檔案類型不符。"
INVALID_PACKAGE = "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。"
ENCRYPTED_PDF = "這個 PDF 檔已加密，無法匯入。"
DAMAGED_EPUB = "EPUB 檔已損壞，或沒有可讀取的內容。"


def _raised(function, *args) -> Exception:
    try:
        function(*args)
    except Exception as error:  # noqa: BLE001 (the error is the value under test)
        return error
    raise AssertionError(f"{function.__name__} raised nothing")


class ImportProblemTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)

    def _package(self, name: str, members: dict[str, bytes]) -> Path:
        path = self.root / f"{name}.dep"
        with zipfile.ZipFile(path, "w") as archive:
            for member, data in members.items():
                archive.writestr(member, data)
        return path

    def test_import_problem_is_a_value_error_that_keeps_its_english_text(self) -> None:
        error = ImportProblem("Text document must use the .txt extension.", "The file name extension does not match the selected file type.")

        self.assertIsInstance(error, ValueError)
        self.assertEqual(str(error), "Text document must use the .txt extension.")
        self.assertEqual(error.reason, "The file name extension does not match the selected file type.")

    def test_a_text_file_that_is_not_utf8(self) -> None:
        path = self.root / "big5.txt"
        path.write_bytes("臺北".encode("cp950"))
        error = _raised(load_text_document, path)

        self.assertIsInstance(error, UnicodeDecodeError)
        self.assertEqual(describe_import_problem(error, "txt"), NOT_UTF8)

    def test_a_file_that_cannot_be_opened(self) -> None:
        error = PermissionError(errno.EACCES, "Permission denied", "locked.txt")

        for format_key in ("txt", "docx", "dep"):
            with self.subTest(format_key=format_key):
                self.assertEqual(describe_import_problem(error, format_key), CANNOT_OPEN)

    def test_a_file_name_that_is_not_a_document_name(self) -> None:
        cases = {
            "too_long": NAME_LENGTH,
            "empty": NAME_LENGTH,
            "invalid": NAME_INVALID,
            "reserved": NAME_INVALID,
        }
        for code, expected in cases.items():
            with self.subTest(code=code):
                self.assertEqual(describe_import_problem(NameValidationError(code, "English text"), "txt"), expected)

    def test_the_problems_of_the_loaders_show_their_reason(self) -> None:
        (self.root / "notes.md").write_text("x", encoding="utf-8")
        (self.root / "notes.pdf").write_text("x", encoding="utf-8")
        cases = (
            ("txt", lambda: load_text_document(self.root / "notes.md"), WRONG_EXTENSION),
            ("pdf", lambda: import_pdf(self.root / "notes.md"), WRONG_EXTENSION),
            ("epub", lambda: import_epub(self.root / "notes.pdf"), WRONG_EXTENSION),
            ("dep", lambda: load_document_package(self.root / "notes.md"), INVALID_PACKAGE),
            ("dep", lambda: load_document_package(self._package("one", {"one.txt": b"a"})), INVALID_PACKAGE),
            (
                "dep",
                lambda: load_document_package(self._package("two", {"two.txt": b"a", "other.brl": b"b"})),
                INVALID_PACKAGE,
            ),
        )
        for format_key, load, expected in cases:
            with self.subTest(format_key=format_key, expected=expected):
                error = _raised(load)

                self.assertIsInstance(error, ImportProblem)
                self.assertEqual(describe_import_problem(error, format_key), expected)

    def test_an_encrypted_pdf(self) -> None:
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.encrypt("secret")
        path = self.root / "locked.pdf"
        with path.open("wb") as stream:
            writer.write(stream)
        error = _raised(import_pdf, path)

        self.assertIsInstance(error, ImportProblem)
        self.assertEqual(str(error), "Encrypted PDF cannot be imported.")
        self.assertEqual(describe_import_problem(error, "pdf"), ENCRYPTED_PDF)

    def test_an_epub_without_readable_content(self) -> None:
        path = self.root / "book.epub"
        path.write_bytes(b"stub")
        books = {
            "no spine": SimpleNamespace(spine=[], get_item_with_id=lambda item_id: None),
            "a missing spine item": SimpleNamespace(spine=[("chapter1", "yes")], get_item_with_id=lambda item_id: None),
        }
        for label, book in books.items():
            with self.subTest(label), patch("documents.importers.epub_importer.epub.read_epub", return_value=book):
                error = _raised(import_epub, path)

                self.assertIsInstance(error, ImportProblem)
                self.assertEqual(describe_import_problem(error, "epub"), DAMAGED_EPUB)

    def test_any_other_error_reading_a_package(self) -> None:
        not_a_zip = self.root / "broken.dep"
        not_a_zip.write_bytes(b"not a zip")
        bad_metadata = self._package(
            "meta", {"meta.txt": b"a", "meta.brl": b"b", "meta.meta.json": b"{"}
        )
        not_utf8 = self._package("big5", {"big5.txt": "臺北".encode("cp950"), "big5.brl": b""})
        errors = {
            "not a zip archive": _raised(load_document_package, not_a_zip),
            "metadata that is not JSON": _raised(load_document_package, bad_metadata),
            "text that is not UTF-8": _raised(load_document_package, not_utf8),
            "a missing member": KeyError("There is no item named 'alpha.brl' in the archive"),
        }
        self.assertIsInstance(errors["not a zip archive"], zipfile.BadZipFile)
        self.assertIsInstance(errors["metadata that is not JSON"], json.JSONDecodeError)
        self.assertIsInstance(errors["text that is not UTF-8"], UnicodeDecodeError)
        for label, error in errors.items():
            with self.subTest(label):
                self.assertEqual(describe_import_problem(error, "dep"), INVALID_PACKAGE)

    def test_any_other_error_shows_its_own_text(self) -> None:
        missing = FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "gone.dep")
        cases = (
            ("docx", zipfile.BadZipFile("File is not a zip file")),
            ("pdf", ValueError("Stream has ended unexpectedly")),
            ("dep", missing),
        )
        for format_key, error in cases:
            with self.subTest(format_key=format_key):
                self.assertEqual(describe_import_problem(error, format_key), f"無法讀取檔案：{error}")

    def test_module_imports_neither_wx_nor_dictionaries(self) -> None:
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])

        self.assertFalse(imported & {"wx", "gui", "dialog", "dictionaries"}, imported)


if __name__ == "__main__":
    unittest.main()
````

Edit: `client/tests/test_document_workspace.py`

```python
        )

        self.assertEqual(documents, [Document(name="alpha", text="A", braille=None)])
        self.assertEqual(
            issues,
            [
                BatchIssue(path=source_dir / "alpha.dep", reason="Text document must use the .txt extension."),
                BatchIssue(path=source_dir / "beta.txt", reason='Document "beta" already exists.'),
            ],
        )

```

```python
        )

        self.assertEqual(documents, [Document(name="alpha", text="A", braille=None)])
        # The reasons in zh_TW (F-12 D3; were English, P1-4 defect 4).
        self.assertEqual(
            issues,
            [
                BatchIssue(path=source_dir / "alpha.dep", reason="副檔名與選取的檔案類型不符。"),
                BatchIssue(path=source_dir / "beta.txt", reason="文件「beta」已存在。"),
            ],
        )

    def test_batch_import_documents_explains_each_skipped_file(self) -> None:
        # F-12 (D3): every reason is in zh_TW; they were English or raw Python texts (P1-4
        # defect 4). Sorted by name, as the batch is.
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        long_stem = "x" * 40
        (source_dir / "alpha.txt").write_text("A", encoding="utf-8")
        (source_dir / "bad.docx").write_bytes(b"not a zip")
        (source_dir / "big5.txt").write_bytes("臺北".encode("cp950"))
        (source_dir / "broken.dep").write_bytes(b"not a zip")
        (source_dir / "foo.xyz").write_text("F", encoding="utf-8")
        (source_dir / f"{long_stem}.txt").write_text("L", encoding="utf-8")

        documents, issues = batch_import_documents(
            sorted(source_dir.iterdir()), format_key="all", existing_names={"alpha"}
        )

        self.assertEqual(documents, [])
        self.assertEqual(
            [(issue.path.name, issue.reason) for issue in issues],
            [
                ("alpha.txt", "文件「alpha」已存在。"),
                ("bad.docx", "無法讀取檔案：File is not a zip file"),
                ("big5.txt", "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"),
                ("broken.dep", "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。"),
                ("foo.xyz", "無法匯入這種類型的檔案。"),
                (f"{long_stem}.txt", "文件名稱長度需為 1 到 32 個字元。"),
            ],
        )

```

Edit: `client/tests/test_document_workspace.py`

```python

        self.assertEqual(kept, Document("alpha", "x�", "�⠁"))
        self.assertEqual(pending, Document("alpha", "x�", None))

    def test_load_workspace_documents_sorts_valid_documents_and_collects_invalid_paths(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
```

```python

        self.assertEqual(kept, Document("alpha", "x�", "�⠁"))
        self.assertEqual(pending, Document("alpha", "x�", None))

    def test_load_workspace_documents_counts_a_package_the_loader_refuses_as_invalid(self) -> None:
        # F-12 (D3): the loader's ImportProblem is a ValueError, so such a package is still
        # an invalid one.
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.workspace_dir / "mismatch.dep", "w") as archive:
            archive.writestr("other.txt", "a")
            archive.writestr("other.brl", "b")
        with zipfile.ZipFile(self.workspace_dir / "half.dep", "w") as archive:
            archive.writestr("half.txt", "a")

        documents, invalid_paths = load_workspace_documents(self.workspace_dir)

        self.assertEqual(documents, [])
        self.assertEqual([path.name for path in invalid_paths], ["half.dep", "mismatch.dep"])

    def test_load_workspace_documents_sorts_valid_documents_and_collects_invalid_paths(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
```

Edit: `client/tests/test_workspace_service.py`

```python


NO_SPACE = f"[Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}"

SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"

```

```python


NO_SPACE = f"[Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}"
# The lead of a failed write of an imported package (F-12 D3; the raw error came alone).
SAVE_FAILED = "儲存文件失敗："

SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"

```

Edit: `client/tests/test_workspace_service.py`

```python
            result,
            ImportResult(
                saved=[Document("ok", "o", None)],
                issues=[BatchIssue(path=sources[0], reason='Document "bad" already exists.')],
            ),
        )
        self.assertEqual(self.controller.document_names, ["alpha", "ok"])
```

```python
            result,
            ImportResult(
                saved=[Document("ok", "o", None)],
                issues=[BatchIssue(path=sources[0], reason="文件「bad」已存在。")],
            ),
        )
        self.assertEqual(self.controller.document_names, ["alpha", "ok"])
```

Edit: `client/tests/test_workspace_service.py`

```python
        self.assertEqual(result.saved, [Document("delta", "d", None)])
        self.assertEqual(
            result.issues,
            [BatchIssue(path=self.workspace / "beta.dep", reason=self._exists_error("beta.dep"))],
        )
        self.assertEqual(self.controller.document_names, ["zoo", "delta"])
        self.assertEqual(self._listing(), ["beta.dep", "delta.dep"])
```

```python
        self.assertEqual(result.saved, [Document("delta", "d", None)])
        self.assertEqual(
            result.issues,
            [BatchIssue(path=self.workspace / "beta.dep", reason=SAVE_FAILED + self._exists_error("beta.dep"))],
        )
        self.assertEqual(self.controller.document_names, ["zoo", "delta"])
        self.assertEqual(self._listing(), ["beta.dep", "delta.dep"])
```

Edit: `client/tests/test_workspace_service.py`

```python
        self.assertEqual(result.saved, [Document("beta", "b", None)])
        self.assertEqual(self.controller.document_names, ["alpha", "beta"])
        self.assertEqual(len(result.issues), 2)
        self.assertEqual(result.issues[0], BatchIssue(path=sources[0], reason='Document "Alpha" already exists.'))
        self.assertEqual(result.issues[1], BatchIssue(path=self.workspace / "delta.dep", reason=NO_SPACE))
        self.assertEqual(self._listing(), ["beta.dep"])

    def test_import_files_reports_any_save_error_as_an_issue(self) -> None:
```

```python
        self.assertEqual(result.saved, [Document("beta", "b", None)])
        self.assertEqual(self.controller.document_names, ["alpha", "beta"])
        self.assertEqual(len(result.issues), 2)
        self.assertEqual(result.issues[0], BatchIssue(path=sources[0], reason="文件「Alpha」已存在。"))
        self.assertEqual(result.issues[1], BatchIssue(path=self.workspace / "delta.dep", reason=SAVE_FAILED + NO_SPACE))
        self.assertEqual(self._listing(), ["beta.dep"])

    def test_import_files_reports_any_save_error_as_an_issue(self) -> None:
```

Edit: `client/tests/test_workspace_service.py`

```python
            result = service.import_files(self._sources(beta="b", delta="d"), format_key="all")

        self.assertEqual(result.saved, [Document("beta", "b", None)])
        self.assertEqual(result.issues, [BatchIssue(path=self.workspace / "delta.dep", reason=str(error))])
        self.assertEqual(self.controller.document_names, ["zoo", "beta"])
        self.assertEqual(self._listing(), ["beta.dep"])

```

```python
            result = service.import_files(self._sources(beta="b", delta="d"), format_key="all")

        self.assertEqual(result.saved, [Document("beta", "b", None)])
        self.assertEqual(result.issues, [BatchIssue(path=self.workspace / "delta.dep", reason=SAVE_FAILED + str(error))])
        self.assertEqual(self.controller.document_names, ["zoo", "beta"])
        self.assertEqual(self._listing(), ["beta.dep"])

```

Edit: `client/tests/test_workspace_service.py`

```python

        expected = [Document("delta", "d", None), Document("epsilon", "e", None)]
        self.assertEqual(result.saved, expected)
        self.assertEqual(result.issues, [BatchIssue(path=self.workspace / "beta.dep", reason=NO_SPACE)])
        self.assertEqual(self.controller.document_names, ["zoo", "delta", "epsilon"])
        self.assertEqual(self._package("delta"), expected[0])
        self.assertEqual(self._package("epsilon"), expected[1])
```

```python

        expected = [Document("delta", "d", None), Document("epsilon", "e", None)]
        self.assertEqual(result.saved, expected)
        self.assertEqual(result.issues, [BatchIssue(path=self.workspace / "beta.dep", reason=SAVE_FAILED + NO_SPACE)])
        self.assertEqual(self.controller.document_names, ["zoo", "delta", "epsilon"])
        self.assertEqual(self._package("delta"), expected[0])
        self.assertEqual(self._package("epsilon"), expected[1])
```

Edit: `client/tests/test_workspace_service.py`

```python
            result = self.service.import_files(sorted(sources.iterdir()), format_key="all")

        self.assertEqual(result.saved, [Document("gamma", "g\ufffd\ufffd", None)])
        self.assertEqual(result.issues, [BatchIssue(path=self._path("beta"), reason=NO_SPACE)])
        self.assertEqual(self._counts("beta", "gamma"), [0, 2])

    def test_pending_count_follows_rename_and_is_dropped_by_delete(self) -> None:
```

```python
            result = self.service.import_files(sorted(sources.iterdir()), format_key="all")

        self.assertEqual(result.saved, [Document("gamma", "g\ufffd\ufffd", None)])
        self.assertEqual(result.issues, [BatchIssue(path=self._path("beta"), reason=SAVE_FAILED + NO_SPACE)])
        self.assertEqual(self._counts("beta", "gamma"), [0, 2])

    def test_pending_count_follows_rename_and_is_dropped_by_delete(self) -> None:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(
            lines,
            [
                'Alpha.txt: Document "Alpha" already exists.',
                f"delta.dep: [Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}",
            ],
        )
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    # --- U+0000 (F-8 D12, D13) ---------------------------------------------

```

```python
        self.assertEqual(
            lines,
            [
                "Alpha.txt: 文件「Alpha」已存在。",
                f"delta.dep: 儲存文件失敗：[Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}",
            ],
        )
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    def test_import_issues_explain_each_skipped_file(self) -> None:
        # F-12 (D3): a reason the user can act on, in zh_TW, on each line.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        source_dir = self.root / "sources"
        source_dir.mkdir()
        (source_dir / "big5.txt").write_bytes("臺北".encode("cp950"))
        (source_dir / "foo.xyz").write_text("F", encoding="utf-8")
        self.import_paths = [str(source_dir / "big5.txt"), str(source_dir / "foo.xyz")]

        frame.on_import_document(None)

        self.assertEqual(
            self.events[-1],
            (
                "FileIssuesDialog",
                gui._("Import Issues"),
                gui._("Some files were skipped during import."),
                [
                    "big5.txt: 檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。",
                    "foo.xyz: 無法匯入這種類型的檔案。",
                ],
            ),
        )
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(frame._document_controller.document_names, ["alpha"])

    # --- U+0000 (F-8 D12, D13) ---------------------------------------------

```

Edit: `client/tests/test_gui_document_flows.py`

```python
                    "FileIssuesDialog",
                    gui._("Import Issues"),
                    gui._("Some files were skipped during import."),
                    ['Alpha.txt: Document "Alpha" already exists.'],
                ),
            ],
        )
```

```python
                    "FileIssuesDialog",
                    gui._("Import Issues"),
                    gui._("Some files were skipped during import."),
                    ["Alpha.txt: 文件「Alpha」已存在。"],
                ),
            ],
        )
```

Edit: `client/tests/test_i18n.py`

```python
            ),
            "An unknown error occurred.": "發生不明的錯誤。",
            "The selected translation table could not translate this text.": "選取的轉譯表無法轉譯這段文字。",
        }
        translation = i18n.load_translation()

```

```python
            ),
            "An unknown error occurred.": "發生不明的錯誤。",
            "The selected translation table could not translate this text.": "選取的轉譯表無法轉譯這段文字。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_import_problem_strings_are_translated(self) -> None:
        # F-12 (D3): the reasons of the Import Issues dialog; the DEP one is revived from an
        # obsolete catalog entry.
        expected = {
            "The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.": (
                "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"
            ),
            "This file type cannot be imported.": "無法匯入這種類型的檔案。",
            "The file name extension does not match the selected file type.": "副檔名與選取的檔案類型不符。",
            "Imported file must be a valid DotExpress DEP package.": "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。",
            "This PDF file is encrypted and cannot be imported.": "這個 PDF 檔已加密，無法匯入。",
            "The EPUB file is damaged or has no readable content.": "EPUB 檔已損壞，或沒有可讀取的內容。",
        }
        translation = i18n.load_translation()

```

```bash
$PY -B -X utf8 -m unittest tests.test_import_problems tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_import_problems (unittest.loader._FailedTest.test_import_problems)
ImportError: Failed to import test module: test_import_problems
ModuleNotFoundError: No module named 'documents.import_problems'
FAIL: test_batch_import_documents_explains_each_skipped_file (tests.test_document_workspace.DocumentWorkspaceTest.test_batch_import_documents_explains_each_skip
AssertionError: Lists differ: [('alpha.txt', 'Document "alpha" already exists.'), ('bad[300 chars]s.')] != [('alpha.txt', '文件「alpha」已存在。'), ('bad.docx', '無法讀取檔案
FAIL: test_batch_import_documents_imports_txt_only_and_reports_duplicates (tests.test_document_workspace.DocumentWorkspaceTest.test_batch_import_documents_impor
AssertionError: Lists differ: [Batc[96 chars]son='Text document must use the .txt extension[138 chars]s.')] != [Batc[96 chars]son='副檔名與選取的檔案類型不符。'), BatchIssue(
FAIL: test_import_does_not_replace_a_package_that_appeared_after_the_names_were_checked (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_import_d
AssertionError: Lists differ: [Batc[96 chars]son="[Errno 17] File exists: 'C:\\\\Users\\\\t[71 chars]p'")] != [Batc[96 chars]son="儲存文件失敗：[Errno 17] File exists:
FAIL: test_import_files_continues_after_a_failed_save (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_import_files_continues_after_a_failed_save
AssertionError: Lists differ: [Batc[82 chars]eta.dep'), reason='[Errno 28] No space left on device')] != [Batc[82 chars]eta.dep'), reason='儲存文件失敗：[Errno 28] No
FAIL: test_import_files_lists_load_issues_before_save_issues (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_import_files_lists_load_issues_befo
AssertionError: Batch[70 chars]sources/Alpha.txt'), reason='Document "Alpha" already exists.') != Batch[70 chars]sources/Alpha.txt'), reason='文件「Alpha」已存在。')
FAIL: test_import_files_reports_any_save_error_as_an_issue (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_import_files_reports_any_save_error_a
AssertionError: Lists differ: [Batc[97 chars]son="'utf-8' codec can't encode character '\\u[41 chars]ed")] != [Batc[97 chars]son="儲存文件失敗：'utf-8' codec can't enc
FAIL: test_import_treats_packages_on_disk_as_existing (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_import_treats_packages_on_disk_as_existing
AssertionError: Impor[142 chars]<c>/sources/bad.txt'), reason='Document "bad" already exists.')]) != Impor[142 chars]<c>/sources/bad.txt'), reason='文件「bad」已存在。'
FAIL: test_import_whose_save_fails_records_no_count (tests.test_workspace_service.ReplacedNulCharactersTest.test_import_whose_save_fails_records_no_count)
FAIL: test_import_issues_explain_each_skipped_file (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_import_issues_explain_each_ski
AssertionError: Tuples differ: ('Fil[36 chars]。', ["big5.txt: 'utf-8' codec can't decode byt[88 chars]".']) != ('Fil[36 chars]。', ['big5.txt: 檔案不是以 UTF-8 文字儲存。請
FAIL: test_import_reports_load_issues_before_save_issues (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_import_reports_load_issu
AssertionError: Lists differ: ['Alpha.txt: Document "Alpha" already exists.', 'delta[37 chars]ice'] != ['Alpha.txt: 文件「Alpha」已存在。', 'delta.dep: 儲存文件失敗：[Errno[25
FAIL: test_single_import_with_nul_shows_the_notice_before_the_issues (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_single_impor
AssertionError: Lists differ: [('Fi[260 chars]入時有部分檔案被略過。', ['Alpha.txt: Document "Alpha" already exists.'])] != [('Fi[260 chars]入時有部分檔案被略過。', ['Alpha.txt: 文件「A
FAIL: test_import_problem_strings_are_translated (tests.test_i18n.TranslationTest.test_import_problem_strings_are_translated)
AssertionError: {'The[93 chars].': 'The file is not saved as UTF-8 text. Save[595 chars]nt.'} != {'The[93 chars].': '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存[3
Ran 401 tests
FAILED (failures=12, errors=1, skipped=2)
```

- [x] **Step 2: Green: `ImportProblem` and `describe_import_problem`** (`client/documents/import_problems.py`, new; `client/documents/workspace.py`, `client/documents/importers/base.py`, `epub_importer.py`, `pdf_importer.py`, `client/documents/workspace_service.py`; 4 spaces). `ImportProblem` lives in `import_problems.py`, not in `importers/base.py`, which imports it (Spec Corrections 4).**

File: `client/documents/import_problems.py`

````python
"""Why an imported file was skipped, in words the user can act on (F-12 D3).

Nothing here imports wx or ``dictionaries``. DotExpress's own loaders raise ``ImportProblem``
for a file they refuse; ``describe_import_problem`` gives the reason of each line of the
Import Issues dialog (``{file name}: {reason}``), translated when it is called.
"""

from __future__ import annotations

from i18n import _
from shared.name_validation import NameValidationError

DEP_FORMAT_KEY = "dep"


class ImportProblem(ValueError):
    """A file that DotExpress's own loaders refuse to import.

    ``str()`` is the English text of before F-12 (for logs and ``except ValueError``);
    ``reason`` is the msgid shown to the user, marked with ``N_`` where the error is raised.
    """

    def __init__(self, detail: str, reason: str) -> None:
        super().__init__(detail)
        self.reason = reason


def describe_import_problem(error: Exception, format_key: str) -> str:
    """The reason shown for a file that the loader of ``format_key`` could not import."""
    if isinstance(error, ImportProblem):
        return _(error.reason)
    if isinstance(error, PermissionError):
        # F-6's CANNOT_OPEN text (dictionaries.read_problems), written here too: documents
        # do not depend on dictionaries.
        return _(
            "The file cannot be opened. It may be in use by another program, or you may not have "
            "permission to read it. Close the other program and try again."
        )
    if isinstance(error, NameValidationError):
        # The texts of the document name dialog; an empty name is told by its length.
        if error.code in ("empty", "too_long"):
            return _("Document name must be 1 to 32 characters.")
        return _("Document name is not a valid Windows file name.")
    if format_key.casefold() == DEP_FORMAT_KEY and not isinstance(error, OSError):
        # A damaged archive, a missing member, metadata that is not JSON, text that is not UTF-8.
        return _("Imported file must be a valid DotExpress DEP package.")
    if isinstance(error, UnicodeDecodeError):
        return _("The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.")
    return _("The file cannot be read: {error}").format(error=error)
````

Edit: `client/documents/workspace.py`

```python
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
from log import get_logger
from shared.atomic_write import ensure_writable, write_bytes_atomically, write_text_atomically
from shared.name_validation import normalize_base_name
```

```python
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
from documents.import_problems import ImportProblem, describe_import_problem
from i18n import N_, _
from log import get_logger
from shared.atomic_write import ensure_writable, write_bytes_atomically, write_text_atomically
from shared.name_validation import normalize_base_name
```

Edit: `client/documents/workspace.py`

```python
# ".<name>.dep.<random>.tmp": a Save's temporary file (16 hex digits) or the staged or
# moved-aside package of a Rename (8 characters of tempfile's alphabet).
_INTERRUPTED_PACKAGE = re.compile(r"^\.(?P<stem>.+)\.(?i:dep)\.[A-Za-z0-9_]+\.tmp$")


@dataclass(frozen=True)
```

```python
# ".<name>.dep.<random>.tmp": a Save's temporary file (16 hex digits) or the staged or
# moved-aside package of a Rename (8 characters of tempfile's alphabet).
_INTERRUPTED_PACKAGE = re.compile(r"^\.(?P<stem>.+)\.(?i:dep)\.[A-Za-z0-9_]+\.tmp$")
# The reasons of the import problems these loaders raise (F-12 D3).
_INVALID_PACKAGE = N_("Imported file must be a valid DotExpress DEP package.")
_WRONG_EXTENSION = N_("The file name extension does not match the selected file type.")


@dataclass(frozen=True)
```

Edit: `client/documents/workspace.py`

```python
def load_document_package(path: Path | str) -> Document:
    package_path = Path(path)
    if package_path.suffix.casefold() != DEP_EXTENSION:
        raise ValueError("Document package must use the .dep extension.")
    return _read_package(package_path, normalize_document_name(package_path.stem))


```

```python
def load_document_package(path: Path | str) -> Document:
    package_path = Path(path)
    if package_path.suffix.casefold() != DEP_EXTENSION:
        raise ImportProblem("Document package must use the .dep extension.", _INVALID_PACKAGE)
    return _read_package(package_path, normalize_document_name(package_path.stem))


```

Edit: `client/documents/workspace.py`

```python
        txt_names = [name for name in names if name.endswith(".txt")]
        brl_names = [name for name in names if name.endswith(".brl")]
        if len(txt_names) != 1 or len(brl_names) != 1:
            raise ValueError("Document package must contain one .txt and one .brl file.")
        txt_name = txt_names[0]
        brl_name = brl_names[0]
        txt_base = normalize_document_name(Path(txt_name).stem)
        brl_base = normalize_document_name(Path(brl_name).stem)
        if txt_base != brl_base or txt_base != package_name:
            raise ValueError("Document package names do not match.")
        text = archive.read(txt_name).decode("utf-8")
        braille = archive.read(brl_name).decode("utf-8")
        metadata_name = f"{package_name}{PENDING_METADATA_SUFFIX}"
```

```python
        txt_names = [name for name in names if name.endswith(".txt")]
        brl_names = [name for name in names if name.endswith(".brl")]
        if len(txt_names) != 1 or len(brl_names) != 1:
            raise ImportProblem("Document package must contain one .txt and one .brl file.", _INVALID_PACKAGE)
        txt_name = txt_names[0]
        brl_name = brl_names[0]
        txt_base = normalize_document_name(Path(txt_name).stem)
        brl_base = normalize_document_name(Path(brl_name).stem)
        if txt_base != brl_base or txt_base != package_name:
            raise ImportProblem("Document package names do not match.", _INVALID_PACKAGE)
        text = archive.read(txt_name).decode("utf-8")
        braille = archive.read(brl_name).decode("utf-8")
        metadata_name = f"{package_name}{PENDING_METADATA_SUFFIX}"
```

Edit: `client/documents/workspace.py`

```python
def load_text_document(path: Path | str) -> Document:
    source_path = Path(path)
    if source_path.suffix.casefold() != TXT_EXTENSION:
        raise ValueError("Text document must use the .txt extension.")
    return Document(
        name=normalize_document_name(source_path.stem),
        text=source_path.read_text(encoding="utf-8"),
```

```python
def load_text_document(path: Path | str) -> Document:
    source_path = Path(path)
    if source_path.suffix.casefold() != TXT_EXTENSION:
        raise ImportProblem("Text document must use the .txt extension.", _WRONG_EXTENSION)
    return Document(
        name=normalize_document_name(source_path.stem),
        text=source_path.read_text(encoding="utf-8"),
```

Edit: `client/documents/workspace.py`

```python
    if normalized_format_key != ALL_SUPPORTED_FILTER_KEY and normalized_format_key not in get_supported_import_filter_keys():
        raise ValueError(f'Unsupported import format: "{format_key}".')
    for path in sorted((Path(path) for path in paths), key=lambda item: (item.stem.casefold(), item.stem)):
        try:
            loader_key = path.suffix.lstrip(".").casefold() if normalized_format_key == ALL_SUPPORTED_FILTER_KEY else normalized_format_key
            loader = IMPORT_LOADERS.get(loader_key)
            if loader is None:
                raise ValueError(f'Unsupported import file type: "{path.suffix}".')
            document = loader(path)
        except Exception as exc:
            issues.append(BatchIssue(path=path, reason=str(exc)))
            continue
        if document.name.casefold() in seen_names:
            issues.append(BatchIssue(path=path, reason=f'Document "{document.name}" already exists.'))
            continue
        seen_names.add(document.name.casefold())
        documents.append(document)
```

```python
    if normalized_format_key != ALL_SUPPORTED_FILTER_KEY and normalized_format_key not in get_supported_import_filter_keys():
        raise ValueError(f'Unsupported import format: "{format_key}".')
    for path in sorted((Path(path) for path in paths), key=lambda item: (item.stem.casefold(), item.stem)):
        loader_key = path.suffix.lstrip(".").casefold() if normalized_format_key == ALL_SUPPORTED_FILTER_KEY else normalized_format_key
        try:
            loader = IMPORT_LOADERS.get(loader_key)
            if loader is None:
                raise ImportProblem(f'Unsupported import file type: "{path.suffix}".', N_("This file type cannot be imported."))
            document = loader(path)
        except Exception as exc:
            # A reason the user can act on, in the UI language (F-12 D3).
            issues.append(BatchIssue(path=path, reason=describe_import_problem(exc, loader_key)))
            continue
        if document.name.casefold() in seen_names:
            issues.append(BatchIssue(path=path, reason=_('Document "{name}" already exists.').format(name=document.name)))
            continue
        seen_names.add(document.name.casefold())
        documents.append(document)
```

Edit: `client/documents/importers/base.py`

```python
from dataclasses import dataclass
from pathlib import Path

from shared.name_validation import normalize_base_name


```

```python
from dataclasses import dataclass
from pathlib import Path

from documents.import_problems import ImportProblem
from i18n import N_
from shared.name_validation import normalize_base_name


```

Edit: `client/documents/importers/base.py`

```python
def validate_source(path: Path | str, extension: str) -> Path:
    source = Path(path)
    if source.suffix.casefold() != extension.casefold():
        raise ValueError(f"Source document must use the {extension} extension.")
    return source


```

```python
def validate_source(path: Path | str, extension: str) -> Path:
    source = Path(path)
    if source.suffix.casefold() != extension.casefold():
        raise ImportProblem(
            f"Source document must use the {extension} extension.",
            N_("The file name extension does not match the selected file type."),
        )
    return source


```

Edit: `client/documents/importers/epub_importer.py`

```python

from ebooklib import epub

from .base import ImportedDocument, source_name, validate_source
from .html_to_ast import html_to_ast
from .markdown_ast import DocumentAst
from .markdown_renderer import render_markdown


def import_epub(path: Path | str) -> ImportedDocument:
```

```python

from ebooklib import epub

from i18n import N_

from .base import ImportedDocument, ImportProblem, source_name, validate_source
from .html_to_ast import html_to_ast
from .markdown_ast import DocumentAst
from .markdown_renderer import render_markdown

# One reason for both problems: the spine item id means nothing to a user (F-12 D3).
_DAMAGED_EPUB = N_("The EPUB file is damaged or has no readable content.")


def import_epub(path: Path | str) -> ImportedDocument:
```

Edit: `client/documents/importers/epub_importer.py`

```python
    book = epub.read_epub(str(source))
    spine = getattr(book, "spine", None)
    if not spine:
        raise ValueError("EPUB does not contain a readable spine.")

    blocks = []
    for item_id, linear in spine:
```

```python
    book = epub.read_epub(str(source))
    spine = getattr(book, "spine", None)
    if not spine:
        raise ImportProblem("EPUB does not contain a readable spine.", _DAMAGED_EPUB)

    blocks = []
    for item_id, linear in spine:
```

Edit: `client/documents/importers/epub_importer.py`

```python
            continue
        item = book.get_item_with_id(item_id)
        if item is None:
            raise ValueError(f'EPUB spine item "{item_id}" is missing.')
        chapter = html_to_ast(item.get_content(), xhtml=True)
        blocks.extend(chapter.blocks)
    return ImportedDocument(source_name(source), render_markdown(DocumentAst(tuple(blocks))))
```

```python
            continue
        item = book.get_item_with_id(item_id)
        if item is None:
            raise ImportProblem(f'EPUB spine item "{item_id}" is missing.', _DAMAGED_EPUB)
        chapter = html_to_ast(item.get_content(), xhtml=True)
        blocks.extend(chapter.blocks)
    return ImportedDocument(source_name(source), render_markdown(DocumentAst(tuple(blocks))))
```

Edit: `client/documents/importers/pdf_importer.py`

```python
import pymupdf
from pypdf import PdfReader

from .base import ImportedDocument, source_name, validate_source
from .markdown_ast import Block, BlockQuote, DocumentAst, Heading, HorizontalRule, ListBlock, ListItem, Paragraph, Table
from .markdown_renderer import render_markdown

SUPPORTED_ROLES = {
    "H1",
```

```python
import pymupdf
from pypdf import PdfReader

from i18n import N_

from .base import ImportedDocument, ImportProblem, source_name, validate_source
from .markdown_ast import Block, BlockQuote, DocumentAst, Heading, HorizontalRule, ListBlock, ListItem, Paragraph, Table
from .markdown_renderer import render_markdown

_ENCRYPTED_PDF = N_("This PDF file is encrypted and cannot be imported.")

SUPPORTED_ROLES = {
    "H1",
```

Edit: `client/documents/importers/pdf_importer.py`

```python
    paragraphs: list[Paragraph] = []
    with pymupdf.open(path) as document:
        if getattr(document, "needs_pass", False) is True or getattr(document, "is_encrypted", False) is True:
            raise ValueError("Encrypted PDF cannot be imported.")
        for page in document:
            text = page.get_text("text").replace("\r\n", "\n").replace("\r", "\n")
            for part in text.split("\n\n"):
```

```python
    paragraphs: list[Paragraph] = []
    with pymupdf.open(path) as document:
        if getattr(document, "needs_pass", False) is True or getattr(document, "is_encrypted", False) is True:
            raise ImportProblem("Encrypted PDF cannot be imported.", _ENCRYPTED_PDF)
        for page in document:
            text = page.get_text("text").replace("\r\n", "\n").replace("\r", "\n")
            for part in text.split("\n\n"):
```

Edit: `client/documents/importers/pdf_importer.py`

```python
    source = validate_source(path, ".pdf")
    reader = PdfReader(str(source))
    if getattr(reader, "is_encrypted", False) is True:
        raise ValueError("Encrypted PDF cannot be imported.")
    catalog = _resolve(reader.trailer.get("/Root"))
    ast: DocumentAst | None = None
    if _has_tagged_structure(catalog):
```

```python
    source = validate_source(path, ".pdf")
    reader = PdfReader(str(source))
    if getattr(reader, "is_encrypted", False) is True:
        raise ImportProblem("Encrypted PDF cannot be imported.", _ENCRYPTED_PDF)
    catalog = _resolve(reader.trailer.get("/Root"))
    ast: DocumentAst | None = None
    if _has_tagged_structure(catalog):
```

Edit: `client/documents/workspace_service.py`

```python
    recover_interrupted_packages,
    save_document_package,
)


@dataclass(frozen=True)
```

```python
    recover_interrupted_packages,
    save_document_package,
)
from i18n import _


@dataclass(frozen=True)
```

Edit: `client/documents/workspace_service.py`

```python
                    raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(package_path))
                save_document_package(package_path, document)
            except Exception as exc:
                save_issues.append(BatchIssue(path=package_path, reason=str(exc)))
                continue
            self._remember(document)
            saved.append(document)
```

```python
                    raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(package_path))
                save_document_package(package_path, document)
            except Exception as exc:
                save_issues.append(BatchIssue(path=package_path, reason=_("Failed to save document: {error}").format(error=exc)))
                continue
            self._remember(document)
            saved.append(document)
```

- [x] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_import_problems tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (only the tests that compare with the zh_TW text fail: the new msgids are not in the catalog yet):

```text
FAIL: test_a_text_file_that_is_not_utf8 (tests.test_import_problems.ImportProblemTest.test_a_text_file_that_is_not_utf8)
AssertionError: 'The file is not saved as UTF-8 text. Save[52 chars]pad.' != '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。'
FAIL: test_an_encrypted_pdf (tests.test_import_problems.ImportProblemTest.test_an_encrypted_pdf)
AssertionError: 'This PDF file is encrypted and cannot be imported.' != '這個 PDF 檔已加密，無法匯入。'
FAIL: test_an_epub_without_readable_content (tests.test_import_problems.ImportProblemTest.test_an_epub_without_readable_content) [no spine]
AssertionError: 'The EPUB file is damaged or has no readable content.' != 'EPUB 檔已損壞，或沒有可讀取的內容。'
FAIL: test_an_epub_without_readable_content (tests.test_import_problems.ImportProblemTest.test_an_epub_without_readable_content) [a missing spine item]
FAIL: test_any_other_error_reading_a_package (tests.test_import_problems.ImportProblemTest.test_any_other_error_reading_a_package) [not a zip archive]
AssertionError: 'Imported file must be a valid DotExpress DEP package.' != '匯入的檔案必須是有效的 DotExpress DEP 封裝檔。'
FAIL: test_any_other_error_reading_a_package (tests.test_import_problems.ImportProblemTest.test_any_other_error_reading_a_package) [metadata that is not JSON]
FAIL: test_any_other_error_reading_a_package (tests.test_import_problems.ImportProblemTest.test_any_other_error_reading_a_package) [text that is not UTF-8]
FAIL: test_any_other_error_reading_a_package (tests.test_import_problems.ImportProblemTest.test_any_other_error_reading_a_package) [a missing member]
FAIL: test_the_problems_of_the_loaders_show_their_reason (tests.test_import_problems.ImportProblemTest.test_the_problems_of_the_loaders_show_their_reason) (form
AssertionError: 'The file name extension does not match the selected file type.' != '副檔名與選取的檔案類型不符。'
FAIL: test_batch_import_documents_explains_each_skipped_file (tests.test_document_workspace.DocumentWorkspaceTest.test_batch_import_documents_explains_each_skip
AssertionError: Lists differ: [('al[84 chars]t', 'The file is not saved as UTF-8 text. Save[252 chars]元。')] != [('al[84 chars]t', '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，
FAIL: test_batch_import_documents_imports_txt_only_and_reports_duplicates (tests.test_document_workspace.DocumentWorkspaceTest.test_batch_import_documents_impor
AssertionError: Lists differ: [Batc[96 chars]son='The file name extension does not match th[139 chars]在。')] != [Batc[96 chars]son='副檔名與選取的檔案類型不符。'), BatchIssue(
FAIL: test_import_issues_explain_each_skipped_file (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_import_issues_explain_each_ski
AssertionError: Tuples differ: ('Fil[47 chars]txt: The file is not saved as UTF-8 text. Save[101 chars]d.']) != ('Fil[47 chars]txt: 檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8
FAIL: test_import_problem_strings_are_translated (tests.test_i18n.TranslationTest.test_import_problem_strings_are_translated)
AssertionError: {'The[93 chars].': 'The file is not saved as UTF-8 text. Save[595 chars]nt.'} != {'The[93 chars].': '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存[3
Ran 410 tests
FAILED (failures=18, skipped=2)
```

- [x] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
$PY -I $T/tools/po_entry.py locales/zh_TW/LC_MESSAGES/dotexpress.po "Imported file must be a valid DotExpress DEP package."
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected:

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
387 translated messages, 2 fuzzy translations, 3 untranslated messages.
#: documents/import_problems.py:48
#, fuzzy
msgid ""
"The file is not saved as UTF-8 text. Save it again as UTF-8, for example "
"with Save As in Notepad."
msgstr ""
"檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel "
"中使用「另存新檔」。"

#: documents/workspace.py:446
#, fuzzy
msgid "This file type cannot be imported."
msgstr "無法讀取檔案：{error}"
#: documents/importers/base.py:22 documents/workspace.py:35
msgid "The file name extension does not match the selected file type."
msgstr ""

#: documents/importers/epub_importer.py:15
msgid "The EPUB file is damaged or has no readable content."
msgstr ""

#: documents/importers/pdf_importer.py:16
msgid "This PDF file is encrypted and cannot be imported."
msgstr ""
'Imported file must be a valid DotExpress DEP package.': active 1, fuzzy no, obsolete copies 0, msgstr '匯入的檔案必須是有效的 DotExpress DEP 封裝檔。'
27
```

- [x] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
msgstr "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。"

#: documents/import_problems.py:48
#, fuzzy
msgid ""
"The file is not saved as UTF-8 text. Save it again as UTF-8, for example "
"with Save As in Notepad."
msgstr ""
"檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel "
"中使用「另存新檔」。"

#: documents/importers/base.py:22 documents/workspace.py:35
msgid "The file name extension does not match the selected file type."
msgstr ""

#: documents/importers/epub_importer.py:15
msgid "The EPUB file is damaged or has no readable content."
msgstr ""

#: documents/importers/pdf_importer.py:16
msgid "This PDF file is encrypted and cannot be imported."
msgstr ""

#: documents/workspace.py:446
#, fuzzy
msgid "This file type cannot be imported."
msgstr "無法讀取檔案：{error}"

#: documents/workspace.py:453 gui.py:729
#, python-brace-format
```

```po
msgstr "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。"

#: documents/import_problems.py:48
msgid ""
"The file is not saved as UTF-8 text. Save it again as UTF-8, for example "
"with Save As in Notepad."
msgstr ""
"檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"

#: documents/importers/base.py:22 documents/workspace.py:35
msgid "The file name extension does not match the selected file type."
msgstr "副檔名與選取的檔案類型不符。"

#: documents/importers/epub_importer.py:15
msgid "The EPUB file is damaged or has no readable content."
msgstr "EPUB 檔已損壞，或沒有可讀取的內容。"

#: documents/importers/pdf_importer.py:16
msgid "This PDF file is encrypted and cannot be imported."
msgstr "這個 PDF 檔已加密，無法匯入。"

#: documents/workspace.py:446
msgid "This file type cannot be imported."
msgstr "無法匯入這種類型的檔案。"

#: documents/workspace.py:453 gui.py:729
#, python-brace-format
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
a second msgmerge changes nothing
msgfmt exit 0
392 translated messages.
0
catalog keys: 393
 1 '匯出完成，但有錯誤'
 2 '所有文件皆已成功匯出。'
 3 '成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}'
 4 '發生不明的錯誤。'
 5 '選取的轉譯表無法轉譯這段文字。'
 6 '(missing)'
 7 '(missing)'
 8 '(missing)'
 9 '(missing)'
10 '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。'
11 '無法匯入這種類型的檔案。'
12 '副檔名與選取的檔案類型不符。'
13 '匯入的檔案必須是有效的 DotExpress DEP 封裝檔。'
14 '這個 PDF 檔已加密，無法匯入。'
15 'EPUB 檔已損壞，或沒有可讀取的內容。'
16 '(missing)'
17 '(missing)'
18 '(missing)'
19 '(missing)'
20 '(missing)'
21 '(missing)'
22 '(missing)'
23 '(missing)'
32119
locales/dotexpress.pot:393
locales/zh_TW/LC_MESSAGES/dotexpress.po:393
27
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 392 sha256 9e6f0c97805b4e7b78958f923af558ffac62e93b00c6a5fb20dab8726105d26e
```

- [x] **Step 6: Green: the new tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_import_problems tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n -v 2>&1 | grep -E "^(test_a_file_name_that_is_not_a_document_name|test_a_file_that_cannot_be_opened|test_a_text_file_that_is_not_utf8|test_an_encrypted_pdf|test_an_epub_without_readable_content|test_any_other_error_reading_a_package|test_any_other_error_shows_its_own_text|test_batch_import_documents_explains_each_skipped_file|test_import_issues_explain_each_skipped_file|test_import_problem_is_a_value_error_that_keeps_its_english_text|test_import_problem_strings_are_translated|test_load_workspace_documents_counts_a_package_the_loader_refuses_as_invalid|test_module_imports_neither_wx_nor_dictionaries|test_the_problems_of_the_loaders_show_their_reason) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_import_problems tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (each new test once per subTest-free run, in the order unittest runs them):

```text
test_a_file_name_that_is_not_a_document_name ok
test_a_file_that_cannot_be_opened ok
test_a_text_file_that_is_not_utf8 ok
test_an_encrypted_pdf ok
test_an_epub_without_readable_content ok
test_any_other_error_reading_a_package ok
test_any_other_error_shows_its_own_text ok
test_import_problem_is_a_value_error_that_keeps_its_english_text ok
test_module_imports_neither_wx_nor_dictionaries ok
test_the_problems_of_the_loaders_show_their_reason ok
test_batch_import_documents_explains_each_skipped_file ok
test_load_workspace_documents_counts_a_package_the_loader_refuses_as_invalid ok
test_import_issues_explain_each_skipped_file ok
test_import_problem_strings_are_translated ok
Ran 410 tests
OK (skipped=2)
Ran 1583 tests
OK (skipped=6)
```

- [x] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_import_problems.py client/tests/test_document_workspace.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py client/tests/test_i18n.py client/documents/import_problems.py client/documents/workspace.py client/documents/importers/base.py client/documents/importers/epub_importer.py client/documents/importers/pdf_importer.py client/documents/workspace_service.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: explain why an imported file was skipped (F-12, P1-4 defect 4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/documents/import_problems.py            |  49 +++++++
 client/documents/importers/base.py             |   7 +-
 client/documents/importers/epub_importer.py    |  11 +-
 client/documents/importers/pdf_importer.py     |  10 +-
 client/documents/workspace.py                  |  22 +--
 client/documents/workspace_service.py          |   3 +-
 client/locales/dotexpress.pot                  |  54 ++++++--
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 31244 -> 32119 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po |  58 +++++---
 client/tests/test_document_workspace.py        |  50 ++++++-
 client/tests/test_gui_document_flows.py        |  34 ++++-
 client/tests/test_i18n.py                      |  17 +++
 client/tests/test_import_problems.py           | 183 +++++++++++++++++++++++++
 client/tests/test_workspace_service.py         |  16 ++-
 14 files changed, 455 insertions(+), 59 deletions(-)
5e23f82b85a0ff43a96236eca5e6e86cfe959905
```

### Task 3: Explain a conversion that cannot read the selected dictionary (D4)

- [x] **Step 1: Red: Test Plan D, C2, C3, A (strings 16, 17).** `test_conversion_text_dictionary_rules.py` (4 spaces): the error-case table expects `DictionaryRulesReadError` (with the same text) for the five dictionary rows, the loader's retry likewise; `DictionaryRulesReadErrorTest`: a Big5 file, a field over `csv.field_size_limit()`, the header `Text,Braille,Type` and an empty file raise it with the path, the cause and `header_not_recognized`; a `PermissionError` opening the dictionary (patched `Path.open`) is its cause; the Bopomofo file's error is not wrapped; a `processing` that returns a value that is not iterable fails after the read and is not wrapped (Spec Corrections 7). `test_conversion_service.py` (4 spaces): the headerless dictionary of the real pipeline gives it. `test_conversion_presenter.py` (4 spaces): `format_conversion_error` gives `轉譯失敗：無法讀取字典「d」。<reason>` for NOT_UTF8, CANNOT_OPEN, INVALID_CSV, OTHER and the header, one line; a manual failure and an export failure show it. `test_i18n.py`: strings 16, 17. The tests look the new class up when they run, so only they fail**

Edit: `client/tests/test_conversion_text_dictionary_rules.py`

```python
    split_bracket_segments,
)
from dictionaries.entries import DictionaryEntry, load_dictionary_rows
from text.zhuyin import normalize_zhuyin_sequence


```

```python
    split_bracket_segments,
)
from dictionaries.entries import DictionaryEntry, load_dictionary_rows
from tests.unreadable_dictionary_files import BIG5, FIELD_LIMIT
from text.zhuyin import normalize_zhuyin_sequence


```

Edit: `client/tests/test_conversion_text_dictionary_rules.py`

```python


def _error_cases() -> tuple[ErrorCase, ...]:
    return (
        ErrorCase("Bopomofo file missing", VALID_DICTIONARY, None, FileNotFoundError, None),
        ErrorCase("Bopomofo file empty", VALID_DICTIONARY, b"", ValueError, NO_HEADER),
```

```python


def _error_cases() -> tuple[ErrorCase, ...]:
    # The selected dictionary's read errors come wrapped since F-12 (D4); the Bopomofo file's
    # do not.
    read_error = dictionary_rules.DictionaryRulesReadError
    return (
        ErrorCase("Bopomofo file missing", VALID_DICTIONARY, None, FileNotFoundError, None),
        ErrorCase("Bopomofo file empty", VALID_DICTIONARY, b"", ValueError, NO_HEADER),
```

Edit: `client/tests/test_conversion_text_dictionary_rules.py`

```python
        # test_from_paths_ignores_a_utf8_bom_in_both_files); a file that is only a BOM has no header.
        ErrorCase("Bopomofo file is only a BOM", VALID_DICTIONARY, b"\xef\xbb\xbf", ValueError, NO_HEADER),
        ErrorCase("Bopomofo file not UTF-8", VALID_DICTIONARY, b"Bopomofo,Braille\n\xff,x\n", UnicodeDecodeError, None),
        ErrorCase("dictionary empty", b"", VALID_BOPOMOFO, ValueError, NO_HEADER),
        ErrorCase("dictionary columns missing", b"text,braille\n", VALID_BOPOMOFO, ValueError, DICTIONARY_COLUMNS),
        ErrorCase("dictionary is only a BOM", b"\xef\xbb\xbf", VALID_BOPOMOFO, ValueError, NO_HEADER),
        ErrorCase(
            "dictionary with a doubled BOM",
            b"\xef\xbb\xbf\xef\xbb\xbftext,braille,type\n",
            VALID_BOPOMOFO,
            ValueError,
            DICTIONARY_COLUMNS,
        ),
        ErrorCase("dictionary not UTF-8", b"text,braille,type\n\xe9,x,\n", VALID_BOPOMOFO, UnicodeDecodeError, None),
        ErrorCase("both malformed: Bopomofo first", b"text,braille\n", b"Bopomofo,Ascii\n", ValueError, BOPOMOFO_COLUMNS),
    )

```

```python
        # test_from_paths_ignores_a_utf8_bom_in_both_files); a file that is only a BOM has no header.
        ErrorCase("Bopomofo file is only a BOM", VALID_DICTIONARY, b"\xef\xbb\xbf", ValueError, NO_HEADER),
        ErrorCase("Bopomofo file not UTF-8", VALID_DICTIONARY, b"Bopomofo,Braille\n\xff,x\n", UnicodeDecodeError, None),
        ErrorCase("dictionary empty", b"", VALID_BOPOMOFO, read_error, NO_HEADER),
        ErrorCase("dictionary columns missing", b"text,braille\n", VALID_BOPOMOFO, read_error, DICTIONARY_COLUMNS),
        ErrorCase("dictionary is only a BOM", b"\xef\xbb\xbf", VALID_BOPOMOFO, read_error, NO_HEADER),
        ErrorCase(
            "dictionary with a doubled BOM",
            b"\xef\xbb\xbf\xef\xbb\xbftext,braille,type\n",
            VALID_BOPOMOFO,
            read_error,
            DICTIONARY_COLUMNS,
        ),
        ErrorCase("dictionary not UTF-8", b"text,braille,type\n\xe9,x,\n", VALID_BOPOMOFO, read_error, None),
        ErrorCase("both malformed: Bopomofo first", b"text,braille\n", b"Bopomofo,Ascii\n", ValueError, BOPOMOFO_COLUMNS),
    )

```

Edit: `client/tests/test_conversion_text_dictionary_rules.py`

```python
        self.assertEqual(LoadedDictionaryRules().apply(""), {"raw": "", "replacement": ""})


class EditorParityTest(DictionaryFilesTestCase):
    """Conversion ignores exactly the rows the dictionary editor hides (F-11 D13, U6)."""

```

```python
        self.assertEqual(LoadedDictionaryRules().apply(""), {"raw": "", "replacement": ""})


class DictionaryRulesReadErrorTest(DictionaryFilesTestCase):
    """F-12 (D4): the selected dictionary that cannot be read is reported as such."""

    def _load(self, processing=_identity) -> Exception:
        try:
            LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=processing)
        except Exception as error:  # noqa: BLE001 (the error is the value under test)
            return error
        self.fail("from_paths raised nothing")

    def test_a_dictionary_that_cannot_be_read_raises_the_read_error(self) -> None:
        cases = (
            ("not UTF-8 (Big5)", BIG5, UnicodeDecodeError, False),
            ("a field over the csv limit", FIELD_LIMIT, csv.Error, False),
            ("headers in capitals", b"Text,Braille,Type\r\nw,x,General\r\n", ValueError, True),
            ("an empty file", b"", ValueError, True),
        )
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
        for label, data, cause, header_not_recognized in cases:
            with self.subTest(label):
                self.dictionary_path.write_bytes(data)

                error = self._load()

                self.assertIsInstance(error, dictionary_rules.DictionaryRulesReadError)
                self.assertEqual(error.path, self.dictionary_path)
                self.assertIs(type(error.error), cause)
                self.assertEqual(str(error), str(error.error))
                self.assertIs(error.header_not_recognized, header_not_recognized)

    def test_a_dictionary_that_cannot_be_opened_raises_the_read_error(self) -> None:
        self.dictionary_path.write_bytes(VALID_DICTIONARY)
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)
        denied = PermissionError(13, "Permission denied", str(self.dictionary_path))
        original_open = Path.open

        def open_(path, *args, **kwargs):
            if path.name == "dictionary.csv":
                raise denied
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", open_):
            error = self._load()

        self.assertIsInstance(error, dictionary_rules.DictionaryRulesReadError)
        self.assertIs(error.error, denied)
        self.assertIs(error.__cause__, denied)
        self.assertFalse(error.header_not_recognized)

    def test_the_bundled_bopomofo_file_is_not_wrapped(self) -> None:
        # A broken installation, not the user's dictionary: its message stays as it is.
        self.dictionary_path.write_bytes(VALID_DICTIONARY)
        self.bopomofo_path.write_bytes(b"Bopomofo,Braille\n\xff,x\n")

        self.assertIs(type(self._load()), UnicodeDecodeError)

    def test_an_error_while_processing_the_rows_is_not_wrapped(self) -> None:
        # The file was read; a row that cannot be turned into a rule is another problem.
        self.dictionary_path.write_text(DICTIONARY_HEADER + "台,ㄊㄞˊ,Bopomofo\n", encoding="utf-8")
        self.bopomofo_path.write_bytes(VALID_BOPOMOFO)

        error = self._load(processing=lambda sequence: 5)

        self.assertIs(type(error), TypeError)


class EditorParityTest(DictionaryFilesTestCase):
    """Conversion ignores exactly the rows the dictionary editor hides (F-11 D13, U6)."""

```

Edit: `client/tests/test_conversion_text_dictionary_rules.py`

```python
        with patch.object(
            LoadedDictionaryRules, "from_paths", wraps=LoadedDictionaryRules.from_paths
        ) as from_paths:
            with self.assertRaisesRegex(ValueError, "^CSV must contain header row\\.$"):
                loader.load()
            self.dictionary_path.write_text(DICTIONARY_HEADER + "甲,X,\n", encoding="utf-8")
            rules = loader.load()
```

```python
        with patch.object(
            LoadedDictionaryRules, "from_paths", wraps=LoadedDictionaryRules.from_paths
        ) as from_paths:
            with self.assertRaisesRegex(dictionary_rules.DictionaryRulesReadError, "^CSV must contain header row\\.$"):
                loader.load()
            self.dictionary_path.write_text(DICTIONARY_HEADER + "甲,X,\n", encoding="utf-8")
            rules = loader.load()
```

Edit: `client/tests/test_conversion_service.py`

```python
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from config import DEFAULT_CHARSET_MAPS
from conversion.output import DualViewSegment
from conversion.service import (
    ConversionOutput,
    ConversionRequest,
```

```python
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from config import DEFAULT_CHARSET_MAPS
from conversion.output import DualViewSegment
from conversion.text import dictionary_rules
from conversion.service import (
    ConversionOutput,
    ConversionRequest,
```

Edit: `client/tests/test_conversion_service.py`

```python
            self._convert("abc", self._runtime())

        self.assertEqual(context.exception.stage, "translation")
        self.assertIs(type(context.exception.error), ValueError)
        self.assertEqual(str(context.exception.error), "CSV must contain header row.")

    def test_headerless_dictionary_does_not_fail_math_only_or_empty_input(self) -> None:
```

```python
            self._convert("abc", self._runtime())

        self.assertEqual(context.exception.stage, "translation")
        # Reported as a dictionary that cannot be read since F-12 (D4).
        self.assertIs(type(context.exception.error), dictionary_rules.DictionaryRulesReadError)
        self.assertTrue(context.exception.error.header_not_recognized)
        self.assertEqual(context.exception.error.path, self.dictionary_path)
        self.assertEqual(str(context.exception.error), "CSV must contain header row.")

    def test_headerless_dictionary_does_not_fail_math_only_or_empty_input(self) -> None:
```

Edit: `client/tests/test_conversion_presenter.py`

```python
    format_conversion_error,
    missing_default_table_message,
)
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from documents.controller import DocumentController
from documents.workspace import Document
from i18n import _
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
from tests.file_log_isolation import isolate_file_logs

PRESENTER_PATH = Path(__file__).resolve().parents[1] / "ui" / "conversion_presenter.py"
LOGGER = "dotexpress.gui"
```

```python
    format_conversion_error,
    missing_default_table_message,
)
import csv

from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from conversion.text import dictionary_rules
from documents.controller import DocumentController
from documents.workspace import Document
from i18n import _
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
from tests.file_log_isolation import isolate_file_logs
from tests.unreadable_dictionary_files import big5_decode_error

# F-12 (D4): a conversion that cannot read the selected dictionary, as the user sees it.
NOT_UTF8 = "檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。"
CANNOT_OPEN = "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。"
HEADER_NOT_RECOGNIZED = "無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。"
BIG5_DICTIONARY_FAILED = f"轉譯失敗：無法讀取字典「big5dict」。{NOT_UTF8}"


def _read_error(*args, **kwargs) -> Exception:
    """A DictionaryRulesReadError, looked up when the test runs."""
    return dictionary_rules.DictionaryRulesReadError(*args, **kwargs)


def _big5_dictionary_failure() -> ConversionStageError:
    return ConversionStageError("translation", _read_error(Path("dictionary/big5dict.csv"), big5_decode_error()))

PRESENTER_PATH = Path(__file__).resolve().parents[1] / "ui" / "conversion_presenter.py"
LOGGER = "dotexpress.gui"
```

Edit: `client/tests/test_conversion_presenter.py`

```python
                    format_conversion_error(ConversionStageError("translation", RuntimeError(raw))),
                    _("Translation failed: {error}").format(error=public),
                )

    # --- convert -------------------------------------------------------------

```

```python
                    format_conversion_error(ConversionStageError("translation", RuntimeError(raw))),
                    _("Translation failed: {error}").format(error=public),
                )

    def test_format_conversion_error_names_a_dictionary_that_cannot_be_read(self) -> None:
        # F-12 (D4): one line, as it is also a line of the Export All summary.
        path = Path("dictionary/d.csv")
        field_error = csv.Error("field larger than field limit (131072)")
        missing = FileNotFoundError(2, "No such file or directory", str(path))
        cases = (
            ("not UTF-8", _read_error(path, big5_decode_error()), NOT_UTF8),
            ("cannot be opened", _read_error(path, PermissionError(13, "Permission denied")), CANNOT_OPEN),
            (
                "not a valid CSV file",
                _read_error(path, field_error),
                f"檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：{field_error}",
            ),
            ("another error", _read_error(path, missing), f"無法讀取檔案：{missing}"),
            (
                "a header that is not recognized",
                _read_error(path, ValueError("CSV must contain header row."), header_not_recognized=True),
                HEADER_NOT_RECOGNIZED,
            ),
        )
        for label, error, reason in cases:
            with self.subTest(label):
                message = format_conversion_error(ConversionStageError("translation", error))

                self.assertEqual(message, f"轉譯失敗：無法讀取字典「d」。{reason}")
                self.assertNotIn("\n", message)

    # --- convert -------------------------------------------------------------

```

Edit: `client/tests/test_conversion_presenter.py`

```python
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {})

    # --- export completion ----------------------------------------------------

    def test_convert_for_export_converts_given_text_without_checks(self) -> None:
```

```python
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {})

    def test_manual_failure_names_a_dictionary_that_cannot_be_read(self) -> None:
        # F-12 (D4).
        self.outputs["source"] = _big5_dictionary_failure()
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(self._take(), self._end() + [("show_error", BIG5_DICTIONARY_FAILED, "錯誤")])

    # --- export completion ----------------------------------------------------

    def test_convert_for_export_converts_given_text_without_checks(self) -> None:
```

Edit: `client/tests/test_conversion_presenter.py`

```python
            self._take(),
            self._end() + [("on_error", _("ASCII conversion failed: {error}").format(error="bad map"))],
        )

    def test_later_job_uses_its_own_completion(self) -> None:
        self.outputs.update({"doc text": ConversionOutput("first", ()), "source": ConversionOutput("second", ())})
```

```python
            self._take(),
            self._end() + [("on_error", _("ASCII conversion failed: {error}").format(error="bad map"))],
        )

    def test_export_failure_names_a_dictionary_that_cannot_be_read(self) -> None:
        # F-12 (D4): a single export shows it, and Export All lists it after the document's name.
        self.outputs["doc text"] = _big5_dictionary_failure()
        presenter = self._presenter()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(self._take(), self._end() + [("on_error", BIG5_DICTIONARY_FAILED)])

    def test_later_job_uses_its_own_completion(self) -> None:
        self.outputs.update({"doc text": ConversionOutput("first", ()), "source": ConversionOutput("second", ())})
```

Edit: `client/tests/test_i18n.py`

```python
            "Imported file must be a valid DotExpress DEP package.": "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。",
            "This PDF file is encrypted and cannot be imported.": "這個 PDF 檔已加密，無法匯入。",
            "The EPUB file is damaged or has no readable content.": "EPUB 檔已損壞，或沒有可讀取的內容。",
        }
        translation = i18n.load_translation()

```

```python
            "Imported file must be a valid DotExpress DEP package.": "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。",
            "This PDF file is encrypted and cannot be imported.": "這個 PDF 檔已加密，無法匯入。",
            "The EPUB file is damaged or has no readable content.": "EPUB 檔已損壞，或沒有可讀取的內容。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unreadable_dictionary_conversion_strings_are_translated(self) -> None:
        # F-12 (D4): a conversion that cannot read the selected dictionary; the header reason
        # uses the words of F-11's message for the editor.
        expected = {
            'Dictionary "{name}" cannot be read. {reason}': "無法讀取字典「{name}」。{reason}",
            "Its header is not recognized. The first line of the file must contain the text, braille, and type headers.": (
                "無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。"
            ),
        }
        translation = i18n.load_translation()

```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_service tests.test_conversion_presenter tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_malformed_files_raise_the_recorded_errors (tests.test_conversion_text_dictionary_rules.DictionaryFileSemanticsTest.test_malformed_files_raise_the_re
AttributeError: module 'conversion.text.dictionary_rules' has no attribute 'DictionaryRulesReadError'. Did you mean: 'DictionaryRulesLoader'?
ERROR: test_a_failed_load_is_retried_by_the_next_load (tests.test_conversion_text_dictionary_rules.DictionaryRulesLoaderTest.test_a_failed_load_is_retried_by_th
ERROR: test_a_dictionary_that_cannot_be_opened_raises_the_read_error (tests.test_conversion_text_dictionary_rules.DictionaryRulesReadErrorTest.test_a_dictionary
ERROR: test_a_dictionary_that_cannot_be_read_raises_the_read_error (tests.test_conversion_text_dictionary_rules.DictionaryRulesReadErrorTest.test_a_dictionary_t
ERROR: test_from_paths_raises_the_recorded_errors (tests.test_conversion_text_dictionary_rules.LoadedDictionaryRulesTest.test_from_paths_raises_the_recorded_err
ERROR: test_headerless_dictionary_fails_text_at_the_translation_stage (tests.test_conversion_service.DictionaryErrorTimingTest.test_headerless_dictionary_fails_
ERROR: test_export_failure_names_a_dictionary_that_cannot_be_read (tests.test_conversion_presenter.ConversionPresenterTest.test_export_failure_names_a_dictionar
ERROR: test_format_conversion_error_names_a_dictionary_that_cannot_be_read (tests.test_conversion_presenter.ConversionPresenterTest.test_format_conversion_error
ERROR: test_manual_failure_names_a_dictionary_that_cannot_be_read (tests.test_conversion_presenter.ConversionPresenterTest.test_manual_failure_names_a_dictionar
FAIL: test_unreadable_dictionary_conversion_strings_are_translated (tests.test_i18n.TranslationTest.test_unreadable_dictionary_conversion_strings_are_translated
AssertionError: {'Dic[40 chars]}': 'Dictionary "{name}" cannot be read. {reas[220 chars]rs.'} != {'Dic[40 chars]}': '無法讀取字典「{name}」。{reason}', 'Its header is [1
Ran 123 tests
FAILED (failures=1, errors=12)
```

- [x] **Step 2: Green: `DictionaryRulesReadError` and its message** (`client/conversion/text/dictionary_rules.py`, `client/ui/conversion_presenter.py`, 4 spaces). The dictionary is read by `_read_dictionary_rows`, all rows before any is processed.**

Edit: `client/conversion/text/dictionary_rules.py`

```python
    return "".join(result)


@dataclass(frozen=True)
class LoadedDictionaryRules:
    """Parsed dictionary rules with their match tries, read once and applied many times.
```

```python
    return "".join(result)


class DictionaryRulesReadError(Exception):
    """The selected dictionary file cannot be read for a conversion (F-12 D4).

    ``path`` is the file and ``error`` the error that stopped the read: an ``OSError``, a
    ``UnicodeDecodeError``, a ``csv.Error``, or, when ``header_not_recognized`` is true, the
    ``ValueError`` of a first line that does not name the text, braille and type columns (an
    empty file included). ``str()`` is the text of ``error``.
    """

    def __init__(self, path: Path | str, error: Exception, *, header_not_recognized: bool = False) -> None:
        super().__init__(str(error))
        self.path = Path(path)
        self.error = error
        self.header_not_recognized = header_not_recognized


def _read_dictionary_rows(path: Path) -> list[dict[str, str | None]]:
    """Every row of the dictionary at ``path``; raises ``DictionaryRulesReadError`` if it cannot be read."""
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as f_d:
            reader = csv.DictReader(f_d)
            if reader.fieldnames is None:
                header_error = ValueError("CSV must contain header row.")
            elif not {"text", "braille", "type"}.issubset(reader.fieldnames):
                header_error = ValueError("CSV must contain columns: text, braille, type")
            else:
                return list(reader)
    except (UnicodeDecodeError, OSError, csv.Error) as error:
        raise DictionaryRulesReadError(path, error) from error
    raise DictionaryRulesReadError(path, header_error, header_not_recognized=True)


@dataclass(frozen=True)
class LoadedDictionaryRules:
    """Parsed dictionary rules with their match tries, read once and applied many times.
```

Edit: `client/conversion/text/dictionary_rules.py`

```python
        """Read the dictionary and Bopomofo rule files.

        A missing dictionary gives empty rules without opening the Bopomofo file.
        A leading UTF-8 BOM is ignored. A row the dictionary editor hides is not a rule:
        a source text that is empty once stripped, or a Bopomofo sequence that does not
        parse as it is once its leading whitespace is gone (F-11 D13, D14). A Bopomofo
```

```python
        """Read the dictionary and Bopomofo rule files.

        A missing dictionary gives empty rules without opening the Bopomofo file.
        A dictionary that cannot be read (opened, decoded, parsed as CSV, or whose header
        is not recognized) raises ``DictionaryRulesReadError``; its rows are read in full
        before any of them is processed, so an error while processing a row is not one of
        these. The bundled Bopomofo file's errors are raised as they are (F-12 D4).
        A leading UTF-8 BOM is ignored. A row the dictionary editor hides is not a rule:
        a source text that is empty once stripped, or a Bopomofo sequence that does not
        parse as it is once its leading whitespace is gone (F-11 D13, D14). A Bopomofo
```

Edit: `client/conversion/text/dictionary_rules.py`

```python
                replacements_bopomofo.append((source, target))
        bopomofo_trie = _build_trie(replacements_bopomofo)

        with dictionary_path.open("r", newline="", encoding="utf-8-sig") as f_d:
            reader = csv.DictReader(f_d)
            if reader.fieldnames is None:
                raise ValueError("CSV must contain header row.")
            if not {"text", "braille", "type"}.issubset(reader.fieldnames):
                raise ValueError("CSV must contain columns: text, braille, type")

            raws: list[tuple[str, str]] = []
            replacements: list[tuple[str, str]] = []
            for row in reader:
                source = (row.get("text") or "")
                target = (row.get("braille") or "")
                if not source.strip():
                    continue

                type_ = (row.get("type") or "")
                if type_ == "Bopomofo":
                    # The editor's rule (dictionaries.entries.canonical_bopomofo); this module
                    # imports nothing from dictionaries.
                    try:
                        target = processing(target.lstrip())
                    except Exception:
                        continue
                    if isinstance(target, str):
                        target_parts = [target]
                    else:
                        target_parts = list(target)
                    replacement_parts = [_scan_trie(part, bopomofo_trie) for part in target_parts]
                else:
                    replacement_parts = target.split("@")

                raw_parts, replacement_parts = _align_source_and_replacement_parts(source, replacement_parts)
                raws.append((source, _wrap_atomic_parts(raw_parts)))
                replacements.append((source, _wrap_atomic_parts(replacement_parts)))

        return cls(tuple(raws), tuple(replacements))

```

```python
                replacements_bopomofo.append((source, target))
        bopomofo_trie = _build_trie(replacements_bopomofo)

        rows = _read_dictionary_rows(dictionary_path)

        raws: list[tuple[str, str]] = []
        replacements: list[tuple[str, str]] = []
        for row in rows:
            source = (row.get("text") or "")
            target = (row.get("braille") or "")
            if not source.strip():
                continue

            type_ = (row.get("type") or "")
            if type_ == "Bopomofo":
                # The editor's rule (dictionaries.entries.canonical_bopomofo); this module
                # imports nothing from dictionaries.
                try:
                    target = processing(target.lstrip())
                except Exception:
                    continue
                if isinstance(target, str):
                    target_parts = [target]
                else:
                    target_parts = list(target)
                replacement_parts = [_scan_trie(part, bopomofo_trie) for part in target_parts]
            else:
                replacement_parts = target.split("@")

            raw_parts, replacement_parts = _align_source_and_replacement_parts(source, replacement_parts)
            raws.append((source, _wrap_atomic_parts(raw_parts)))
            replacements.append((source, _wrap_atomic_parts(replacement_parts)))

        return cls(tuple(raws), tuple(replacements))

```

Edit: `client/ui/conversion_presenter.py`

```python
    convert_text_with_alignment,
    get_public_error_message,
)
from documents.controller import DocumentController
from documents.workspace import Document
from i18n import _
```

```python
    convert_text_with_alignment,
    get_public_error_message,
)
from conversion.text.dictionary_rules import DictionaryRulesReadError
from dictionaries.read_problems import describe_dictionary_read_error
from documents.controller import DocumentController
from documents.workspace import Document
from i18n import _
```

Edit: `client/ui/conversion_presenter.py`

```python
    return _("Please select a translation table first.")


def format_conversion_error(error: ConversionStageError) -> str:
    message_templates = {
        "ascii": _("ASCII conversion failed: {error}"),
        "text_processing": _("Text processing failed: {error}"),
    }
    message_template = message_templates.get(error.stage, _("Translation failed: {error}"))
    error_text = _(get_public_error_message(error.error))
    return message_template.format(error=error_text)


```

```python
    return _("Please select a translation table first.")


def describe_dictionary_rules_read_error(error: DictionaryRulesReadError) -> str:
    """Which dictionary cannot be read and why, in one line (F-12 D4).

    One line, not F-6's headline and reason paragraphs: the text is also a line of the
    Export All summary. The header reason uses the words of the editor's message (F-11).
    """
    if error.header_not_recognized:
        reason = _(
            "Its header is not recognized. The first line of the file must contain the text, braille, and type headers."
        )
    else:
        reason = describe_dictionary_read_error(error.error)
    return _('Dictionary "{name}" cannot be read. {reason}').format(name=error.path.stem, reason=reason)


def format_conversion_error(error: ConversionStageError) -> str:
    message_templates = {
        "ascii": _("ASCII conversion failed: {error}"),
        "text_processing": _("Text processing failed: {error}"),
    }
    message_template = message_templates.get(error.stage, _("Translation failed: {error}"))
    if isinstance(error.error, DictionaryRulesReadError):
        error_text = describe_dictionary_rules_read_error(error.error)
    else:
        error_text = _(get_public_error_message(error.error))
    return message_template.format(error=error_text)


```

- [x] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_service tests.test_conversion_presenter tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (only the tests that compare with the zh_TW text fail: the new msgids are not in the catalog yet):

```text
FAIL: test_export_failure_names_a_dictionary_that_cannot_be_read (tests.test_conversion_presenter.ConversionPresenterTest.test_export_failure_names_a_dictionary
AssertionError: Lists differ: [('ti[76 chars]轉譯失敗：Dictionary "big5dict" cannot be read. 檔案不[56 chars]」。')] != [('ti[76 chars]轉譯失敗：無法讀取字典「big5dict」。檔案不是以 UTF-8 儲
FAIL: test_format_conversion_error_names_a_dictionary_that_cannot_be_read (tests.test_conversion_presenter.ConversionPresenterTest.test_format_conversion_error_
AssertionError: '轉譯失敗：Dictionary "d" cannot be read. 檔案不是以 UTF-[47 chars]新檔」。' != '轉譯失敗：無法讀取字典「d」。檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 [26 chars]新檔」。'
AssertionError: '轉譯失敗：Dictionary "d" cannot be read. 無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。' != '轉譯失敗：無法讀取字典「d」。無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。'
AssertionError: '轉譯失敗：Dictionary "d" cannot be read. 檔案不是有效的 CS[57 chars]072)' != '轉譯失敗：無法讀取字典「d」。檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資[36 chars]072)'
AssertionError: '轉譯失敗：Dictionary "d" cannot be read. 無法讀取[59 chars]sv\'' != "轉譯失敗：無法讀取字典「d」。無法讀取檔案：[Errno 2] No such [36 chars]csv'"
AssertionError: '轉譯失敗：Dictionary "d" cannot be read. Its header[92 chars]ers.' != '轉譯失敗：無法讀取字典「d」。無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。'
FAIL: test_manual_failure_names_a_dictionary_that_cannot_be_read (tests.test_conversion_presenter.ConversionPresenterTest.test_manual_failure_names_a_dictionary
AssertionError: Lists differ: [('ti[78 chars]轉譯失敗：Dictionary "big5dict" cannot be read. 檔案不[62 chars]錯誤')] != [('ti[78 chars]轉譯失敗：無法讀取字典「big5dict」。檔案不是以 UTF-8 儲
FAIL: test_unreadable_dictionary_conversion_strings_are_translated (tests.test_i18n.TranslationTest.test_unreadable_dictionary_conversion_strings_are_translated
AssertionError: {'Dic[40 chars]}': 'Dictionary "{name}" cannot be read. {reas[220 chars]rs.'} != {'Dic[40 chars]}': '無法讀取字典「{name}」。{reason}', 'Its header is [1
Ran 123 tests
FAILED (failures=8)
```

- [x] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected:

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
392 translated messages, 2 fuzzy translations.
#: ui/conversion_presenter.py:128
#, fuzzy
msgid ""
"Its header is not recognized. The first line of the file must contain the "
"text, braille, and type headers."
msgstr ""
"無法儲存字典「{name}」：無法辨識檔案的表頭。檔案的第一列必須包含 text、"
"braille 與 type 表頭。"

#: ui/conversion_presenter.py:132
#, fuzzy, python-brace-format
msgid "Dictionary \"{name}\" cannot be read. {reason}"
msgstr "無法讀取字典「{name}」。"
27
```

- [x] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
msgstr "請先選擇轉譯表。"

#: ui/conversion_presenter.py:128
#, fuzzy
msgid ""
"Its header is not recognized. The first line of the file must contain the "
"text, braille, and type headers."
msgstr ""
"無法儲存字典「{name}」：無法辨識檔案的表頭。檔案的第一列必須包含 text、"
"braille 與 type 表頭。"

#: ui/conversion_presenter.py:132
#, fuzzy, python-brace-format
msgid "Dictionary \"{name}\" cannot be read. {reason}"
msgstr "無法讀取字典「{name}」。"

#: ui/conversion_presenter.py:137
#, python-brace-format
```

```po
msgstr "請先選擇轉譯表。"

#: ui/conversion_presenter.py:128
msgid ""
"Its header is not recognized. The first line of the file must contain the "
"text, braille, and type headers."
msgstr ""
"無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。"

#: ui/conversion_presenter.py:132
#, python-brace-format
msgid "Dictionary \"{name}\" cannot be read. {reason}"
msgstr "無法讀取字典「{name}」。{reason}"

#: ui/conversion_presenter.py:137
#, python-brace-format
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
a second msgmerge changes nothing
msgfmt exit 0
394 translated messages.
0
catalog keys: 395
 1 '匯出完成，但有錯誤'
 2 '所有文件皆已成功匯出。'
 3 '成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}'
 4 '發生不明的錯誤。'
 5 '選取的轉譯表無法轉譯這段文字。'
 6 '(missing)'
 7 '(missing)'
 8 '(missing)'
 9 '(missing)'
10 '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。'
11 '無法匯入這種類型的檔案。'
12 '副檔名與選取的檔案類型不符。'
13 '匯入的檔案必須是有效的 DotExpress DEP 封裝檔。'
14 '這個 PDF 檔已加密，無法匯入。'
15 'EPUB 檔已損壞，或沒有可讀取的內容。'
16 '無法讀取字典「{name}」。{reason}'
17 '無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。'
18 '(missing)'
19 '(missing)'
20 '(missing)'
21 '(missing)'
22 '(missing)'
23 '(missing)'
32440
locales/dotexpress.pot:395
locales/zh_TW/LC_MESSAGES/dotexpress.po:395
27
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 394 sha256 4528a3b543937ea86b70120013e5d5a1014f37406e53baa836e6216f61c2113e
```

- [x] **Step 6: Green: the new tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_service tests.test_conversion_presenter tests.test_i18n -v 2>&1 | grep -E "^(test_a_dictionary_that_cannot_be_opened_raises_the_read_error|test_a_dictionary_that_cannot_be_read_raises_the_read_error|test_an_error_while_processing_the_rows_is_not_wrapped|test_export_failure_names_a_dictionary_that_cannot_be_read|test_format_conversion_error_names_a_dictionary_that_cannot_be_read|test_manual_failure_names_a_dictionary_that_cannot_be_read|test_the_bundled_bopomofo_file_is_not_wrapped|test_unreadable_dictionary_conversion_strings_are_translated) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_service tests.test_conversion_presenter tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (each new test once per subTest-free run, in the order unittest runs them):

```text
test_a_dictionary_that_cannot_be_opened_raises_the_read_error ok
test_a_dictionary_that_cannot_be_read_raises_the_read_error ok
test_an_error_while_processing_the_rows_is_not_wrapped ok
test_the_bundled_bopomofo_file_is_not_wrapped ok
test_export_failure_names_a_dictionary_that_cannot_be_read ok
test_format_conversion_error_names_a_dictionary_that_cannot_be_read ok
test_manual_failure_names_a_dictionary_that_cannot_be_read ok
test_unreadable_dictionary_conversion_strings_are_translated ok
Ran 123 tests
OK
Ran 1591 tests
OK (skipped=6)
```

- [x] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_conversion_text_dictionary_rules.py client/tests/test_conversion_service.py client/tests/test_conversion_presenter.py client/tests/test_i18n.py client/conversion/text/dictionary_rules.py client/ui/conversion_presenter.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: explain a conversion that cannot read the selected dictionary (F-12, F-6 O5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/conversion/text/dictionary_rules.py         |  95 ++++++++++++++-------
 client/locales/dotexpress.pot                      |  29 +++++--
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo     | Bin 32119 -> 32440 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po     |  30 +++++--
 client/tests/test_conversion_presenter.py          |  70 +++++++++++++++
 client/tests/test_conversion_service.py            |   6 +-
 .../tests/test_conversion_text_dictionary_rules.py |  82 ++++++++++++++++--
 client/tests/test_i18n.py                          |  13 +++
 client/ui/conversion_presenter.py                  |  22 ++++-
 9 files changed, 289 insertions(+), 58 deletions(-)
0661d35dc654b7e0f025ce34e452fd7629257273
```

### Task 4: Explain a document name held by a file that is not listed (D5)

- [x] **Step 1: Red: Test Plan F, E2 (unlisted part), A (strings 18, 19).** `test_workspace_service.py` (4 spaces): Import of a name that `Bad.dep` holds gives string 18 naming `Bad.dep`; `unlisted_package_entry` gives the on-disk spelling (`bad.dep` for `BAD` on NTFS), `folder.dep` for a folder, `None` for a free name and for a Rename's own package, and `bad.dep` when the folder cannot be listed. `test_document_workspace.py` (4 spaces): `batch_import_documents` with `unlisted_entries` gives string 18 and keeps the listed duplicate first. `test_gui_document_flows.py` (4 spaces): F-8's two tests of Add and Rename to `bad` expect the new box (string 18, a blank line, string 19 with the workspace folder) and the dialog again; Add `BAD` names `bad.dep` (skipped on a case-sensitive file system); a folder; a listed duplicate keeps its message and the entry is not asked for; the frame's Import names the file; the delegation test's stand-in service answers `None`. `test_i18n.py`: strings 18, 19**

Edit: `client/tests/test_workspace_service.py`

```python

        result = service.import_files(sources, format_key="all")

        self.assertEqual(
            result,
            ImportResult(
                saved=[Document("ok", "o", None)],
                issues=[BatchIssue(path=sources[0], reason="文件「bad」已存在。")],
            ),
        )
        self.assertEqual(self.controller.document_names, ["alpha", "ok"])
```

```python

        result = service.import_files(sources, format_key="all")

        # F-12 (D5): the reason names the file on disk, as it is spelled there.
        self.assertEqual(
            result,
            ImportResult(
                saved=[Document("ok", "o", None)],
                issues=[
                    BatchIssue(
                        path=sources[0],
                        reason="名稱「bad」已被工作區資料夾中的「Bad.dep」使用，但這個檔案不在文件清單中。",
                    )
                ],
            ),
        )
        self.assertEqual(self.controller.document_names, ["alpha", "ok"])
```

Edit: `client/tests/test_workspace_service.py`

```python
        for label, name, exclude_name, expected in cases:
            with self.subTest(label):
                self.assertIs(service.package_name_taken(name, exclude_name=exclude_name), expected)

    def test_free_document_name(self) -> None:
        cases = (
```

```python
        for label, name, exclude_name, expected in cases:
            with self.subTest(label):
                self.assertIs(service.package_name_taken(name, exclude_name=exclude_name), expected)

    def test_unlisted_package_entry_names_what_holds_a_name_on_disk(self) -> None:
        # F-12 (D5): the entry as the workspace folder lists it.
        service = self._start_with_a_kept_invalid_package()
        self._block("folder")
        cases = [
            ("free", "gamma", None, None),
            ("an invalid package kept at startup", "bad", None, "bad.dep"),
            ("a folder", "folder", None, "folder.dep"),
            ("its own package, any case", "Alpha", "alpha", None),
        ]
        if os.name == "nt":
            cases.append(("another case on NTFS: the spelling on disk", "BAD", None, "bad.dep"))
        for label, name, exclude_name, expected in cases:
            with self.subTest(label):
                self.assertEqual(service.unlisted_package_entry(name, exclude_name=exclude_name), expected)

    def test_unlisted_package_entry_falls_back_to_the_package_name(self) -> None:
        # The path is taken, but the listing does not show it (it went away in between).
        service = self._start_with_a_kept_invalid_package()

        with patch.object(workspace_service.os, "scandir", side_effect=PermissionError(13, "denied")):
            self.assertEqual(service.unlisted_package_entry("bad"), "bad.dep")

    def test_free_document_name(self) -> None:
        cases = (
```

Edit: `client/tests/test_document_workspace.py`

```python
                ("broken.dep", "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。"),
                ("foo.xyz", "無法匯入這種類型的檔案。"),
                (f"{long_stem}.txt", "文件名稱長度需為 1 到 32 個字元。"),
            ],
        )

```

```python
                ("broken.dep", "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。"),
                ("foo.xyz", "無法匯入這種類型的檔案。"),
                (f"{long_stem}.txt", "文件名稱長度需為 1 到 32 個字元。"),
            ],
        )

    def test_batch_import_documents_names_the_file_that_holds_a_name_on_disk(self) -> None:
        # F-12 (D5): a name held by a package on disk that is not listed gets its own reason;
        # a listed name keeps the duplicate message, also when an unlisted entry holds another
        # case of it (a case-sensitive file system).
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "alpha.txt").write_text("A", encoding="utf-8")
        (source_dir / "BAD.txt").write_text("B", encoding="utf-8")
        (source_dir / "ok.txt").write_text("O", encoding="utf-8")

        documents, issues = batch_import_documents(
            sorted(source_dir.iterdir()),
            format_key="txt",
            existing_names={"alpha"},
            unlisted_entries={"ALPHA": "ALPHA.dep", "bad": "bad.dep"},
        )

        self.assertEqual(documents, [Document("ok", "O", None)])
        self.assertEqual(
            [(issue.path.name, issue.reason) for issue in issues],
            [
                ("alpha.txt", "文件「alpha」已存在。"),
                ("BAD.txt", "名稱「BAD」已被工作區資料夾中的「bad.dep」使用，但這個檔案不在文件清單中。"),
            ],
        )

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame._workspace_service.workspace_dir = self.workspace
        # F-8 (D1, D2): a bare Mock would answer "taken" and loop the name prompt.
        frame._workspace_service.package_name_taken.return_value = False
        frame._workspace_service.free_document_name.side_effect = lambda base: base
        # F-8 (D4): a bare Mock would be a truthy list of recovered names.
        frame._workspace_service.take_recovered_document_names.return_value = []
```

```python
        frame._workspace_service.workspace_dir = self.workspace
        # F-8 (D1, D2): a bare Mock would answer "taken" and loop the name prompt.
        frame._workspace_service.package_name_taken.return_value = False
        # F-12 (D5): the same for the entry that holds a name on disk.
        frame._workspace_service.unlisted_package_entry.return_value = None
        frame._workspace_service.free_document_name.side_effect = lambda base: base
        # F-8 (D4): a bare Mock would be a truthy list of recovered names.
        frame._workspace_service.take_recovered_document_names.return_value = []
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._package("beta"), beta)
        self.assertEqual(self._state(frame), before)

    def _frame_with_a_kept_invalid_bad_package(self):
        """alpha listed and open, bad.dep invalid and kept at startup (F-8, M-1)."""
        alpha = Document("alpha", "a", "1")
```

```python
        self.assertEqual(self._package("beta"), beta)
        self.assertEqual(self._state(frame), before)

    def _unlisted_name_events(self, title: str, initial_name: str, typed_name: str, entry: str, frame) -> list:
        # F-12 (D5): the box names the entry on disk and shows the workspace folder.
        message = (
            f"名稱「{typed_name}」已被工作區資料夾中的「{entry}」使用，但這個檔案不在文件清單中。\n\n"
            f"請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n{self.workspace}"
        )
        return [
            ("DocumentNameDialog", gui._(title), initial_name),
            ("MessageBox", message, gui._("Error"), gui.wx.OK | gui.wx.ICON_ERROR, frame),
            ("DocumentNameDialog", gui._(title), typed_name),
        ]

    def _frame_with_a_kept_invalid_bad_package(self):
        """alpha listed and open, bad.dep invalid and kept at startup (F-8, M-1)."""
        alpha = Document("alpha", "a", "1")
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        frame.on_add_document(None)

        self.assertEqual(self.events, self._duplicate_name_events("Add Document", "", "bad", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
```

```python

        frame.on_add_document(None)

        self.assertEqual(self.events, self._unlisted_name_events("Add Document", "", "bad", "bad.dep", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        frame.on_rename_document(None)

        self.assertEqual(self.events, self._duplicate_name_events("Rename Document", "alpha", "bad", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(frame), before)

    # --- delete ------------------------------------------------------------

```

```python

        frame.on_rename_document(None)

        self.assertEqual(self.events, self._unlisted_name_events("Rename Document", "alpha", "bad", "bad.dep", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(frame), before)

    def test_add_of_another_case_of_an_unlisted_name_names_the_entry_on_disk(self) -> None:
        # F-12 (D5): the box names bad.dep, as it is spelled on disk, not the typed BAD.
        frame = self._frame_with_a_kept_invalid_bad_package()
        if not os.path.lexists(self.workspace / "BAD.dep"):
            self.skipTest("case-sensitive file system: BAD is a free name")
        self.names = ["BAD", None]

        frame.on_add_document(None)

        self.assertEqual(self.events, self._unlisted_name_events("Add Document", "", "BAD", "bad.dep", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])

    def test_add_of_a_name_held_by_a_folder_names_the_folder(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        self._block("folder")
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.names = ["folder", None]

        frame.on_add_document(None)

        self.assertEqual(self.events, self._unlisted_name_events("Add Document", "", "folder", "folder.dep", frame))
        self.assertEqual(frame._document_controller.document_names, ["alpha"])

    def test_a_listed_duplicate_keeps_its_message_before_any_entry_on_disk(self) -> None:
        # F-12 (D5): the document list is checked first (an unlisted ALPHA.dep can exist next
        # to the listed alpha on a case-sensitive file system).
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.names = ["alpha", None]

        with patch.object(DocumentWorkspaceService, "unlisted_package_entry", return_value="ALPHA.dep", create=True) as entry:
            frame.on_add_document(None)

        self.assertEqual(self.events, self._duplicate_name_events("Add Document", "", "alpha", frame))
        entry.assert_not_called()

    def test_import_of_a_name_held_by_an_unlisted_package_names_the_file(self) -> None:
        # F-12 (D5): without the folder line, which would repeat on every line.
        frame = self._frame_with_a_kept_invalid_bad_package()
        source_dir = self.root / "sources"
        source_dir.mkdir()
        (source_dir / "bad.txt").write_text("b", encoding="utf-8")
        self.import_paths = [str(source_dir / "bad.txt")]

        frame.on_import_document(None)

        self.assertEqual(
            self.events[-1],
            (
                "FileIssuesDialog",
                gui._("Import Issues"),
                gui._("Some files were skipped during import."),
                ["bad.txt: 名稱「bad」已被工作區資料夾中的「bad.dep」使用，但這個檔案不在文件清單中。"],
            ),
        )
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")

    # --- delete ------------------------------------------------------------

```

Edit: `client/tests/test_i18n.py`

```python
            'Dictionary "{name}" cannot be read. {reason}': "無法讀取字典「{name}」。{reason}",
            "Its header is not recognized. The first line of the file must contain the text, braille, and type headers.": (
                "無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。"
            ),
        }
        translation = i18n.load_translation()
```

```python
            'Dictionary "{name}" cannot be read. {reason}': "無法讀取字典「{name}」。{reason}",
            "Its header is not recognized. The first line of the file must contain the text, braille, and type headers.": (
                "無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。"
            ),
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unlisted_entry_strings_are_translated(self) -> None:
        # F-12 (D5): a document name held by a file in the workspace folder that is not listed.
        expected = {
            'The name "{name}" is used by "{file}" in the workspace folder, but that file is not in the document list.': (
                "名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清單中。"
            ),
            "Choose another name, or move or delete that file. Workspace folder:\n{folder}": (
                "請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n{folder}"
            ),
        }
        translation = i18n.load_translation()
```

```bash
$PY -B -X utf8 -m unittest tests.test_workspace_service tests.test_document_workspace tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_unlisted_package_entry_falls_back_to_the_package_name (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_unlisted_package_entry_falls_b
AttributeError: 'DocumentWorkspaceService' object has no attribute 'unlisted_package_entry'
ERROR: test_unlisted_package_entry_names_what_holds_a_name_on_disk (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_unlisted_package_entry_names_
ERROR: test_batch_import_documents_names_the_file_that_holds_a_name_on_disk (tests.test_document_workspace.DocumentWorkspaceTest.test_batch_import_documents_nam
TypeError: batch_import_documents() got an unexpected keyword argument 'unlisted_entries'
FAIL: test_import_treats_packages_on_disk_as_existing (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_import_treats_packages_on_disk_as_existing
AssertionError: Impor[154 chars]d.txt'), reason='文件「bad」已存在。')]) != Impor[154 chars]d.txt'), reason='名稱「bad」已被工作區資料夾中的「Bad.dep」使用，但這個檔案不在文件清單中。')])
FAIL: test_add_of_a_name_held_by_a_folder_names_the_folder (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_add_of_a_name_held_by_
AssertionError: Lists differ: [('Do[43 chars]x', '文件「folder」已存在。', '錯誤', 516, <gui.BrailleF[73 chars]er')] != [('Do[43 chars]x', '名稱「folder」已被工作區資料夾中的「folder.de
FAIL: test_add_of_a_name_whose_package_is_on_disk_asks_again (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_add_of_a_name_whose_
AssertionError: Lists differ: [('Do[43 chars]x', '文件「bad」已存在。', '錯誤', 516, <gui.BrailleFram[67 chars]ad')] != [('Do[43 chars]x', '名稱「bad」已被工作區資料夾中的「bad.dep」使用，但
FAIL: test_add_of_another_case_of_an_unlisted_name_names_the_entry_on_disk (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_add_of
AssertionError: Lists differ: [('Do[43 chars]x', '文件「BAD」已存在。', '錯誤', 516, <gui.BrailleFram[67 chars]AD')] != [('Do[43 chars]x', '名稱「BAD」已被工作區資料夾中的「bad.dep」使用，但
FAIL: test_import_of_a_name_held_by_an_unlisted_package_names_the_file (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_import_of_
AssertionError: Tuples differ: ('Fil[33 chars]被略過。', ['bad.txt: 文件「bad」已存在。']) != ('Fil[33 chars]被略過。', ['bad.txt: 名稱「bad」已被工作區資料夾中的「bad.dep」使用，但這個檔案不在文件清單中。'])
FAIL: test_rename_to_a_name_whose_package_is_on_disk_asks_again (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_rename_to_a_name_
AssertionError: Lists differ: [('Do[50 chars]x', '文件「bad」已存在。', '錯誤', 516, <gui.BrailleFram[69 chars]ad')] != [('Do[50 chars]x', '名稱「bad」已被工作區資料夾中的「bad.dep」使用，但
FAIL: test_unlisted_entry_strings_are_translated (tests.test_i18n.TranslationTest.test_unlisted_entry_strings_are_translated)
AssertionError: {'The[101 chars].': 'The name "{name}" is used by "{file}" in [223 chars]er}'} != {'The[101 chars].': '名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清
Ran 409 tests
FAILED (failures=7, errors=7, skipped=2)
```

- [x] **Step 2: Green: `unlisted_package_entry`, the unlisted entries of Import, the box** (`client/documents/workspace.py`, `client/documents/workspace_service.py`, 4 spaces; `client/gui.py`, tabs). The frame asks the service for the entry instead of `package_name_taken` (Spec Corrections 8).**

Edit: `client/documents/workspace.py`

```python
import stat
import tempfile
import zipfile
from collections.abc import Callable
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
```

```python
import stat
import tempfile
import zipfile
from collections.abc import Callable, Mapping
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
```

Edit: `client/documents/workspace.py`

```python
    *,
    format_key: str,
    existing_names: set[str],
) -> tuple[list[Document], list[BatchIssue]]:
    documents: list[Document] = []
    issues: list[BatchIssue] = []
    seen_names = {name.casefold() for name in existing_names}
    normalized_format_key = format_key.casefold()
    if normalized_format_key != ALL_SUPPORTED_FILTER_KEY and normalized_format_key not in get_supported_import_filter_keys():
        raise ValueError(f'Unsupported import format: "{format_key}".')
```

```python
    *,
    format_key: str,
    existing_names: set[str],
    unlisted_entries: Mapping[str, str] | None = None,
) -> tuple[list[Document], list[BatchIssue]]:
    """Load ``paths``; skip each file that cannot be loaded or whose name is taken, with a reason.

    ``existing_names`` are the listed documents; ``unlisted_entries`` maps each name that an
    entry on disk which is not listed holds to that entry's file name (F-12 D5). Names are
    compared ignoring case, and a listed name is reported as a duplicate first.
    """
    documents: list[Document] = []
    issues: list[BatchIssue] = []
    seen_names = {name.casefold() for name in existing_names}
    unlisted = {name.casefold(): entry for name, entry in (unlisted_entries or {}).items()}
    normalized_format_key = format_key.casefold()
    if normalized_format_key != ALL_SUPPORTED_FILTER_KEY and normalized_format_key not in get_supported_import_filter_keys():
        raise ValueError(f'Unsupported import format: "{format_key}".')
```

Edit: `client/documents/workspace.py`

```python
        if document.name.casefold() in seen_names:
            issues.append(BatchIssue(path=path, reason=_('Document "{name}" already exists.').format(name=document.name)))
            continue
        seen_names.add(document.name.casefold())
        documents.append(document)
    return documents, issues


def choose_selection_after_delete(names: list[str], deleted_name: str) -> str | None:
```

```python
        if document.name.casefold() in seen_names:
            issues.append(BatchIssue(path=path, reason=_('Document "{name}" already exists.').format(name=document.name)))
            continue
        if document.name.casefold() in unlisted:
            issues.append(BatchIssue(path=path, reason=unlisted_entry_reason(document.name, unlisted[document.name.casefold()])))
            continue
        seen_names.add(document.name.casefold())
        documents.append(document)
    return documents, issues


def unlisted_entry_reason(name: str, entry: str) -> str:
    """Why ``name`` cannot be used: ``entry``, in the workspace folder, is not a listed document (F-12 D5)."""
    return _(
        'The name "{name}" is used by "{file}" in the workspace folder, but that file is not in the document list.'
    ).format(name=name, file=entry)


def choose_selection_after_delete(names: list[str], deleted_name: str) -> str | None:
```

Edit: `client/documents/workspace_service.py`

```python
            return False
        return os.path.lexists(self.package_path(name))

    def free_document_name(self, base: str) -> str:
        """``base`` if no document and no package has it, else ``"base (2)"``, ``"base (3)"``... (F-8 D2)."""
        name = base
```

```python
            return False
        return os.path.lexists(self.package_path(name))

    def unlisted_package_entry(self, name: str, *, exclude_name: str | None = None) -> str | None:
        """The name on disk of what takes ``name``'s package path, or ``None`` if nothing does (F-12 D5).

        ``None`` exactly when ``package_name_taken`` is false. Callers check the document list
        first, so the entry is one that is not listed: an invalid package kept at startup, a
        package copied in while DotExpress runs, a folder. The workspace folder is listed, so
        the spelling is the one on disk (``bad.dep`` for ``BAD``); ``"<name>.dep"`` if the
        listing does not show the entry.
        """
        if not self.package_name_taken(name, exclude_name=exclude_name):
            return None
        wanted = f"{name}{DEP_EXTENSION}".casefold()
        try:
            with os.scandir(self._workspace_dir) as entries:
                for entry in entries:
                    if entry.name.casefold() == wanted:
                        return entry.name
        except OSError:
            pass
        return f"{name}{DEP_EXTENSION}"

    def free_document_name(self, base: str) -> str:
        """``base`` if no document and no package has it, else ``"base (2)"``, ``"base (3)"``... (F-8 D2)."""
        name = base
```

Edit: `client/documents/workspace_service.py`

```python
        self._controller.add_document(document)

    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult:
        on_disk = {path.stem for path in self._workspace_dir.glob(f"*{DEP_EXTENSION}")}
        documents, load_issues = batch_import_documents(
            list(paths),
            format_key=format_key,
            existing_names=set(self._controller.document_names) | on_disk,
        )
        saved: list[Document] = []
        save_issues: list[BatchIssue] = []
```

```python
        self._controller.add_document(document)

    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult:
        listed = set(self._controller.document_names)
        listed_folded = {name.casefold() for name in listed}
        # A package on disk that is not listed holds its name (F-8 D1); the reason names its
        # file (F-12 D5).
        unlisted = {
            path.stem: path.name
            for path in self._workspace_dir.glob(f"*{DEP_EXTENSION}")
            if path.stem.casefold() not in listed_folded
        }
        documents, load_issues = batch_import_documents(
            list(paths),
            format_key=format_key,
            existing_names=listed,
            unlisted_entries=unlisted,
        )
        saved: list[Document] = []
        save_issues: list[BatchIssue] = []
```

Edit: `client/gui.py`

```python
    create_default_document,
    normalize_document_name,
    replace_lone_surrogates,
)
from documents.workspace_service import DocumentWorkspaceService
from ui.action_menu import get_document_menu_enabled_state
```

```python
    create_default_document,
    normalize_document_name,
    replace_lone_surrogates,
    unlisted_entry_reason,
)
from documents.workspace_service import DocumentWorkspaceService
from ui.action_menu import get_document_menu_enabled_state
```

Edit: `client/gui.py`

```python
				if dialog.ShowModal() != wx.ID_OK:
					return None
				document_name = normalize_document_name(dialog.get_document_name())
			# A package on disk that is not listed (kept invalid at startup) counts too (F-8).
			if self._document_controller.document_name_exists(
				document_name, exclude_name=exclude_name
			) or self._workspace_service.package_name_taken(document_name, exclude_name=exclude_name):
				message_box(
					_('Document "{name}" already exists.').format(name=document_name),
					_("Error"),
					wx.OK | wx.ICON_ERROR,
					parent=self,
				)
				prefill_name = document_name
				continue
			return document_name

	def _create_default_document(self) -> bool:
		default_document = create_default_document()
```

```python
				if dialog.ShowModal() != wx.ID_OK:
					return None
				document_name = normalize_document_name(dialog.get_document_name())
			if self._document_controller.document_name_exists(document_name, exclude_name=exclude_name):
				message = _('Document "{name}" already exists.').format(name=document_name)
			else:
				# An entry on disk that is not listed (an invalid package kept at startup) holds
				# the name too (F-8); the box names it and the workspace folder (F-12 D5).
				entry = self._workspace_service.unlisted_package_entry(document_name, exclude_name=exclude_name)
				if entry is None:
					return document_name
				message = "\n\n".join(
					(
						unlisted_entry_reason(document_name, entry),
						_("Choose another name, or move or delete that file. Workspace folder:\n{folder}").format(
							folder=self._workspace_service.workspace_dir
						),
					)
				)
			message_box(message, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
			prefill_name = document_name

	def _create_default_document(self) -> bool:
		default_document = create_default_document()
```

- [x] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_workspace_service tests.test_document_workspace tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (only the tests that compare with the zh_TW text fail: the new msgids are not in the catalog yet):

```text
FAIL: test_import_treats_packages_on_disk_as_existing (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_import_treats_packages_on_disk_as_existing
AssertionError: Impor[166 chars]son='The name "bad" is used by "Bad.dep" in th[61 chars].')]) != Impor[166 chars]son='名稱「bad」已被工作區資料夾中的「Bad.dep」使用，但這個檔案不在文件清單中。
FAIL: test_batch_import_documents_names_the_file_that_holds_a_name_on_disk (tests.test_document_workspace.DocumentWorkspaceTest.test_batch_import_documents_name
AssertionError: Lists differ: [('al[36 chars]t', 'The name "BAD" is used by "bad.dep" in th[60 chars]t.')] != [('al[36 chars]t', '名稱「BAD」已被工作區資料夾中的「bad.dep」使用，但
FAIL: test_add_of_a_name_held_by_a_folder_names_the_folder (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_add_of_a_name_held_by_
AssertionError: Lists differ: [('Do[43 chars]x', 'The name "folder" is used by "folder.dep"[303 chars]er')] != [('Do[43 chars]x', '名稱「folder」已被工作區資料夾中的「folder.d
FAIL: test_add_of_a_name_whose_package_is_on_disk_asks_again (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_add_of_a_name_whose_
AssertionError: Lists differ: [('Do[43 chars]x', 'The name "bad" is used by "bad.dep" in th[294 chars]ad')] != [('Do[43 chars]x', '名稱「bad」已被工作區資料夾中的「bad.dep」使用，
FAIL: test_add_of_another_case_of_an_unlisted_name_names_the_entry_on_disk (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_add_of
AssertionError: Lists differ: [('Do[43 chars]x', 'The name "BAD" is used by "bad.dep" in th[294 chars]AD')] != [('Do[43 chars]x', '名稱「BAD」已被工作區資料夾中的「bad.dep」使用，
FAIL: test_import_of_a_name_held_by_an_unlisted_package_names_the_file (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_import_of_
AssertionError: Tuples differ: ('Fil[46 chars]txt: The name "bad" is used by "bad.dep" in th[60 chars]t.']) != ('Fil[46 chars]txt: 名稱「bad」已被工作區資料夾中的「bad.dep」使用，
FAIL: test_rename_to_a_name_whose_package_is_on_disk_asks_again (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_rename_to_a_name_
AssertionError: Lists differ: [('Do[50 chars]x', 'The name "bad" is used by "bad.dep" in th[296 chars]ad')] != [('Do[50 chars]x', '名稱「bad」已被工作區資料夾中的「bad.dep」使用，
FAIL: test_unlisted_entry_strings_are_translated (tests.test_i18n.TranslationTest.test_unlisted_entry_strings_are_translated)
AssertionError: {'The[101 chars].': 'The name "{name}" is used by "{file}" in [223 chars]er}'} != {'The[101 chars].': '名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清
Ran 409 tests
FAILED (failures=8, skipped=2)
```

- [x] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected:

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
394 translated messages, 2 untranslated messages.
#: documents/workspace.py:474
#, python-brace-format
msgid ""
"The name \"{name}\" is used by \"{file}\" in the workspace folder, but that "
"file is not in the document list."
msgstr ""

#: gui.py:736
#, python-brace-format
msgid ""
"Choose another name, or move or delete that file. Workspace folder:\n"
"{folder}"
msgstr ""
27
```

- [x] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
"The name \"{name}\" is used by \"{file}\" in the workspace folder, but that "
"file is not in the document list."
msgstr ""

#: documents/workspace_service.py:272 gui.py:474 gui.py:484
#, python-brace-format
```

```po
"The name \"{name}\" is used by \"{file}\" in the workspace folder, but that "
"file is not in the document list."
msgstr ""
"名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清單中。"

#: documents/workspace_service.py:272 gui.py:474 gui.py:484
#, python-brace-format
```

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
"Choose another name, or move or delete that file. Workspace folder:\n"
"{folder}"
msgstr ""

#: gui.py:770
#, python-brace-format
```

```po
"Choose another name, or move or delete that file. Workspace folder:\n"
"{folder}"
msgstr ""
"請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n"
"{folder}"

#: gui.py:770
#, python-brace-format
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
a second msgmerge changes nothing
msgfmt exit 0
396 translated messages.
0
catalog keys: 397
 1 '匯出完成，但有錯誤'
 2 '所有文件皆已成功匯出。'
 3 '成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}'
 4 '發生不明的錯誤。'
 5 '選取的轉譯表無法轉譯這段文字。'
 6 '(missing)'
 7 '(missing)'
 8 '(missing)'
 9 '(missing)'
10 '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。'
11 '無法匯入這種類型的檔案。'
12 '副檔名與選取的檔案類型不符。'
13 '匯入的檔案必須是有效的 DotExpress DEP 封裝檔。'
14 '這個 PDF 檔已加密，無法匯入。'
15 'EPUB 檔已損壞，或沒有可讀取的內容。'
16 '無法讀取字典「{name}」。{reason}'
17 '無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。'
18 '名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清單中。'
19 '請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n{folder}'
20 '(missing)'
21 '(missing)'
22 '(missing)'
23 '(missing)'
32855
locales/dotexpress.pot:397
locales/zh_TW/LC_MESSAGES/dotexpress.po:397
27
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 396 sha256 cccf45a7373f89174c881d08d24504408b59af3f8456e9c4d849d88232e508aa
```

- [x] **Step 6: Green: the new tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_workspace_service tests.test_document_workspace tests.test_gui_document_flows tests.test_i18n -v 2>&1 | grep -E "^(test_a_listed_duplicate_keeps_its_message_before_any_entry_on_disk|test_add_of_a_name_held_by_a_folder_names_the_folder|test_add_of_another_case_of_an_unlisted_name_names_the_entry_on_disk|test_batch_import_documents_names_the_file_that_holds_a_name_on_disk|test_import_of_a_name_held_by_an_unlisted_package_names_the_file|test_unlisted_entry_strings_are_translated|test_unlisted_package_entry_falls_back_to_the_package_name|test_unlisted_package_entry_names_what_holds_a_name_on_disk) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_workspace_service tests.test_document_workspace tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (each new test once per subTest-free run, in the order unittest runs them):

```text
test_unlisted_package_entry_falls_back_to_the_package_name ok
test_unlisted_package_entry_names_what_holds_a_name_on_disk ok
test_batch_import_documents_names_the_file_that_holds_a_name_on_disk ok
test_a_listed_duplicate_keeps_its_message_before_any_entry_on_disk ok
test_add_of_a_name_held_by_a_folder_names_the_folder ok
test_add_of_another_case_of_an_unlisted_name_names_the_entry_on_disk ok
test_import_of_a_name_held_by_an_unlisted_package_names_the_file ok
test_unlisted_entry_strings_are_translated ok
Ran 409 tests
OK (skipped=2)
Ran 1599 tests
OK (skipped=6)
```

- [x] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_workspace_service.py client/tests/test_document_workspace.py client/tests/test_gui_document_flows.py client/tests/test_i18n.py client/documents/workspace.py client/documents/workspace_service.py client/gui.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: explain a document name held by a file that is not listed (F-12, F-8a)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/documents/workspace.py                  |  20 ++++-
 client/documents/workspace_service.py          |  34 ++++++-
 client/gui.py                                  |  30 ++++---
 client/locales/dotexpress.pot                  | 114 ++++++++++++-----------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 32440 -> 32855 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 120 ++++++++++++++-----------
 client/tests/test_document_workspace.py        |  26 ++++++
 client/tests/test_gui_document_flows.py        |  77 +++++++++++++++-
 client/tests/test_i18n.py                      |  14 +++
 client/tests/test_workspace_service.py         |  31 ++++++-
 10 files changed, 346 insertions(+), 120 deletions(-)
ebbf013b774aaeae21b6ce9dc98532f08d016023
```

### Task 5: Tell the user when settings cannot be saved (D6)

- [x] **Step 1: Red: Test Plan G, A (strings 20-22).** `test_config.py` (4 spaces): `ConfigSaveProblemTest`: every setter returns `None` after a save; each returns `UNREADABLE` for a folder at `config.json`; a damaged file with a folder at `config.json.bak` gives `BACKUP_FAILED` (the backup path, the F-8 log line, the file kept); a failing `os.replace` gives `WRITE_FAILED`; the client id and `set_lang(persist=True)` behave as before. `test_translation_settings.py`, `test_translation_tables.py`, `test_view_settings.py` (4 spaces): the helpers return the first problem and call every setter. `test_gui_document_flows.py` (4 spaces): `SettingsSaveProblemFrameTest` (a real `ConfigStore` in a temporary folder, `config.log` isolated): one box after Apply, none after the second; the font size and the dictionary report through the same flag in either order; no box after good saves; the text of each kind; the box's parent is the active window. The frame tests whose stand-in saves are Mocks get `return_value=None` (Spec Corrections 9). `test_i18n.py`: strings 20-22**

Edit: `client/tests/test_config.py`

```python
        self.assertEqual(self._saved(), {"view": {"font_size": 20}, "conversion": {"width": 30, "output_mode": "ascii"}})


class ConfigModuleShapeTest(unittest.TestCase):
    """P2-6: config IO lives on ``ConfigStore``; the module holds no path and no IO functions."""

```

```python
        self.assertEqual(self._saved(), {"view": {"font_size": 20}, "conversion": {"width": 30, "output_mode": "ascii"}})


class ConfigSaveProblemTest(unittest.TestCase):
    """F-12 (D6): a save that does not reach config.json returns why; the F-8 rules stay."""

    SETTERS = (
        ("set_output_mode", ("ascii",)),
        ("set_conversion_width", (52,)),
        ("set_selected_dictionary", ("alpha",)),
        ("set_translation_tables", ({"default": "zh-tw.ctb"},)),
        ("set_view_settings", (18, "dark", "default")),
    )

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.directory = Path(temp_dir.name)
        self.path = self.directory / "config.json"
        self.backup = self.directory / "config.json.bak"
        self.store = config.ConfigStore(self.path)
        for logged in (config._logged_load_failures, config._logged_skipped_saves):
            logged.clear()
            self.addCleanup(logged.clear)

    def _problem(self):
        return config.ConfigSaveProblem

    def _kind(self, name: str):
        return getattr(config.ConfigSaveProblemKind, name)

    def test_every_setter_returns_none_when_the_save_works(self) -> None:
        for name, args in self.SETTERS:
            with self.subTest(name):
                self.assertIsNone(getattr(self.store, name)(*args))

        self.assertEqual(self._saved_keys(), ["conversion", "language_detection", "view"])

    def _saved_keys(self) -> list[str]:
        return sorted(json.loads(self.path.read_text(encoding="utf-8")))

    def test_a_file_that_cannot_be_read_is_unreadable(self) -> None:
        # A folder at config.json: opening it for reading fails, as for a locked file.
        self.path.mkdir()

        with self.assertLogs("dotexpress.config", level="WARNING"):
            problems = [getattr(self.store, name)(*args) for name, args in self.SETTERS]

        for (name, _args), problem in zip(self.SETTERS, problems):
            with self.subTest(name):
                self.assertIsInstance(problem, self._problem())
                self.assertIs(problem.kind, self._kind("UNREADABLE"))
                self.assertIsInstance(problem.error, OSError)
                self.assertEqual(problem.path, self.path)
                self.assertIsNone(problem.backup_path)
        self.assertTrue(self.path.is_dir())

    def test_a_damaged_file_whose_backup_fails_is_backup_failed(self) -> None:
        self.path.write_bytes(b"{")
        self.backup.mkdir()

        with self.assertLogs("dotexpress.config", level="WARNING") as captured:
            problem = self.store.set_output_mode("ascii")

        self.assertIs(problem.kind, self._kind("BACKUP_FAILED"))
        self.assertIsInstance(problem.error, OSError)
        self.assertEqual((problem.path, problem.backup_path), (self.path, self.backup))
        self.assertEqual(self.path.read_bytes(), b"{")
        errors = [record.getMessage() for record in captured.records if record.levelno == logging.ERROR]
        self.assertEqual(errors, [f"Failed to save config file {self.path}"])

    def test_a_write_that_fails_is_write_failed(self) -> None:
        error = OSError(errno.ENOSPC, "injected")

        with patch("os.replace", side_effect=error), self.assertLogs("dotexpress.config", level="ERROR") as captured:
            problem = self.store.set_view_settings(18, "dark", "default")

        self.assertEqual(problem, self._problem()(self._kind("WRITE_FAILED"), error, self.path))
        self.assertFalse(self.path.exists())
        self.assertEqual([record.getMessage() for record in captured.records], [f"Failed to save config file {self.path}"])

    def test_the_client_id_and_the_language_ignore_a_failed_save(self) -> None:
        # Not settings the user changed; the client id is saved on a background thread.
        self.path.mkdir()

        with self.assertLogs("dotexpress.config", level="WARNING"), patch.object(config, "_runtime_lang", None):
            client_id = self.store.get_or_create_client_id()
            language = self.store.set_lang("en", persist=True)

        self.assertEqual(str(UUID(client_id)), client_id)
        self.assertIsNone(language)


class ConfigModuleShapeTest(unittest.TestCase):
    """P2-6: config IO lives on ``ConfigStore``; the module holds no path and no IO functions."""

```

Edit: `client/tests/test_translation_settings.py`

```python
import tempfile
import unittest
from pathlib import Path

import config
from settings.translation import (
```

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import config
from settings.translation import (
```

Edit: `client/tests/test_translation_settings.py`

```python
    def _write_config(self, conversion: dict[str, object]) -> None:
        with open(self.store.path, "w", encoding="utf-8") as f:
            json.dump({"conversion": conversion}, f)

    def test_load_normalizes_invalid_config(self) -> None:
        self._write_config(
```

```python
    def _write_config(self, conversion: dict[str, object]) -> None:
        with open(self.store.path, "w", encoding="utf-8") as f:
            json.dump({"conversion": conversion}, f)

    def test_save_calls_every_setter_and_returns_the_first_problem(self) -> None:
        # F-12 (D6): the frame shows the first problem; a failed setter does not stop the others.
        store = Mock(spec=config.ConfigStore)
        first, second = object(), object()
        store.set_output_mode.return_value = None
        store.set_conversion_width.return_value = first
        store.set_selected_dictionary.return_value = second

        problem = save_translation_settings(store, TranslationSettings("ascii", 52, "alpha"))

        self.assertIs(problem, first)
        store.set_output_mode.assert_called_once_with("ascii")
        store.set_conversion_width.assert_called_once_with(52)
        store.set_selected_dictionary.assert_called_once_with("alpha")

    def test_save_returns_none_when_every_setter_saves(self) -> None:
        self.assertIsNone(save_translation_settings(self.store, TranslationSettings("ascii", 52, "alpha")))

    def test_load_normalizes_invalid_config(self) -> None:
        self._write_config(
```

Edit: `client/tests/test_translation_tables.py`

```python
import tempfile
import unittest
from pathlib import Path

import config
from settings.translation_tables import load_translation_tables, save_translation_tables
```

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import config
from settings.translation_tables import load_translation_tables, save_translation_tables
```

Edit: `client/tests/test_translation_tables.py`

```python

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_load_translation_tables_returns_copy(self) -> None:
        stored_tables = {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb"}
```

```python

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_save_returns_what_the_store_returns(self) -> None:
        # F-12 (D6): the save problem, or None.
        store = Mock(spec=config.ConfigStore)
        problem = object()
        store.set_translation_tables.return_value = problem

        self.assertIs(save_translation_tables(store, {"default": "zh-tw.ctb"}), problem)
        self.assertIsNone(save_translation_tables(self.store, {"default": "zh-tw.ctb"}))

    def test_load_translation_tables_returns_copy(self) -> None:
        stored_tables = {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb"}
```

Edit: `client/tests/test_view_settings.py`

```python
import tempfile
import unittest
from pathlib import Path

import config
from settings.view import (
```

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import config
from settings.view import (
```

Edit: `client/tests/test_view_settings.py`

```python

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_normalize_clamps_font_and_replaces_unknown_choices(self) -> None:
        self.assertEqual(
```

```python

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_returns_what_the_store_returns(self) -> None:
        # F-12 (D6): the save problem, or None.
        store = Mock(spec=config.ConfigStore)
        problem = object()
        store.set_view_settings.return_value = problem

        self.assertIs(save_view_settings(store, ViewSettings(18, "dark", "default")), problem)
        self.assertIsNone(save_view_settings(self.store, ViewSettings(18, "dark", "default")))

    def test_normalize_clamps_font_and_replaces_unknown_choices(self) -> None:
        self.assertEqual(
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        previous_tables = {"default": "zh-tw.ctb"}
        frame.translation_tables = previous_tables

        with patch.object(gui, "save_translation_settings"), \
             patch.object(gui, "save_translation_tables"), \
             patch.object(gui, "save_view_settings"):
            result = frame.apply_settings_from_dialog(snapshot)

        self.assertEqual(frame.translation_settings, snapshot.translation)
```

```python
        previous_tables = {"default": "zh-tw.ctb"}
        frame.translation_tables = previous_tables

        with patch.object(gui, "save_translation_settings", return_value=None), \
             patch.object(gui, "save_translation_tables", return_value=None), \
             patch.object(gui, "save_view_settings", return_value=None):
            result = frame.apply_settings_from_dialog(snapshot)

        self.assertEqual(frame.translation_settings, snapshot.translation)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        snapshot = make_snapshot(tables={"default": "test-default.ctb", "math": "test-math.ctb"})

        with patch.object(gui, "save_translation_settings"), \
             patch.object(gui, "save_translation_tables"), \
             patch.object(gui, "save_view_settings"):
            frame.apply_settings_from_dialog(snapshot)
        frame._config_store.get_lang.return_value = "zh_TW"
        frame._config_store.get_charset_maps.return_value = {"CJKCharactersLanguage": "zh"}
```

```python
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        snapshot = make_snapshot(tables={"default": "test-default.ctb", "math": "test-math.ctb"})

        with patch.object(gui, "save_translation_settings", return_value=None), \
             patch.object(gui, "save_translation_tables", return_value=None), \
             patch.object(gui, "save_view_settings", return_value=None):
            frame.apply_settings_from_dialog(snapshot)
        frame._config_store.get_lang.return_value = "zh_TW"
        frame._config_store.get_charset_maps.return_value = {"CJKCharactersLanguage": "zh"}
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            frame._register_output_font = Mock(return_value=False)
            frame._paths = make_paths(dictionary=dictionary_dir, workspace=Path("workspace"))
            frame._config_store = Mock(spec=gui.ConfigStore)
            with (
                patch.object(
                    gui,
```

```python
            frame._register_output_font = Mock(return_value=False)
            frame._paths = make_paths(dictionary=dictionary_dir, workspace=Path("workspace"))
            frame._config_store = Mock(spec=gui.ConfigStore)
            # A save that works: no settings save problem to report (F-12 D6).
            frame._config_store.set_selected_dictionary.return_value = None
            with (
                patch.object(
                    gui,
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        )


class _RecordingFont:
    """``wx.Font`` stand-in: the font it copies and the calls made on it."""

```

```python
        )


class SettingsSaveProblemFrameTest(unittest.TestCase):
    """F-12 (D6): the first settings change of a session that cannot be saved shows one box."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.config_path = self.root / "config.json"
        self.boxes: list = []
        self.active_window = None
        for logged in (config._logged_load_failures, config._logged_skipped_saves):
            logged.clear()
            self.addCleanup(logged.clear)
        for patcher in (
            patch.object(gui, "message_box", lambda *args, **kwargs: self.boxes.append((args, kwargs))),
            patch.object(gui.wx, "GetActiveWindow", lambda: self.active_window, create=True),
            patch.object(gui.DotExpressSettingsDialog, "open_instance", return_value=None),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        # A failed save logs to config.log: never to the real one.
        self.addCleanup(isolate_file_logs("dotexpress.config"))

    def _frame(self) -> gui.BrailleFrame:
        frame = object.__new__(gui.BrailleFrame)
        frame._config_store = config.ConfigStore(self.config_path)
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default", "math"])
        frame.translation_settings = TranslationSettings("unicode", 40, "default")
        frame.view_settings = ViewSettings(12, "light", "default")
        return frame

    def _box(self, frame, reason: str, parent=None) -> tuple:
        message = (
            f"DotExpress 無法將設定儲存到「{self.config_path}」。設定的變更在關閉 DotExpress 之前有效，但不會保留。"
            f"在下次啟動 DotExpress 之前，不會再顯示這則訊息。\n\n{reason}"
        )
        return ((message, "設定未儲存", gui.wx.OK | gui.wx.ICON_WARNING), {"parent": parent or frame})

    CANNOT_OPEN = "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。"

    def test_a_settings_change_that_cannot_be_saved_shows_one_box_and_still_applies(self) -> None:
        # A folder at config.json cannot be read, as a locked file: UNREADABLE.
        self.config_path.mkdir()
        frame = self._frame()
        snapshot = make_snapshot(translation=TranslationSettings("ascii", 52, "math"), view=ViewSettings(18, "dark", "default"))

        frame.apply_settings_from_dialog(snapshot)
        frame.apply_settings_from_dialog(snapshot)

        self.assertEqual(self.boxes, [self._box(frame, self.CANNOT_OPEN)])
        self.assertEqual(frame.translation_settings, TranslationSettings("ascii", 52, "math"))
        self.assertEqual(frame.view_settings, ViewSettings(18, "dark", "default"))
        self.assertTrue(self.config_path.is_dir())

    def test_font_size_and_dictionary_changes_report_through_the_same_flag(self) -> None:
        self.config_path.mkdir()
        for first, second in (("font", "dictionary"), ("dictionary", "font")):
            with self.subTest(first=first):
                self.boxes.clear()
                frame = self._frame()
                changes = {
                    "font": lambda: frame._set_view_font_size(20),
                    "dictionary": lambda: frame._set_active_dictionary("math"),
                }

                changes[first]()
                after_first = list(self.boxes)
                changes[second]()

                self.assertEqual(after_first, [self._box(frame, self.CANNOT_OPEN)])
                self.assertEqual(self.boxes, after_first)
                self.assertEqual(frame.view_settings.font_size, 20)
                self.assertEqual(frame.translation_settings.selected_dictionary, "math")

    def test_no_box_when_the_settings_are_saved(self) -> None:
        frame = self._frame()

        frame.apply_settings_from_dialog(make_snapshot(translation=TranslationSettings("ascii", 52, "math")))
        frame._set_view_font_size(20)
        frame._set_active_dictionary("default")

        self.assertEqual(self.boxes, [])
        saved = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["conversion"]["output_mode"], "ascii")
        self.assertEqual(saved["view"]["font_size"], 20)

    def test_each_kind_of_problem_gives_its_reason(self) -> None:
        error = OSError(13, "Access denied")
        backup = self.root / "config.json.bak"
        cases = (
            ("UNREADABLE", None, self.CANNOT_OPEN),
            (
                "BACKUP_FAILED",
                backup,
                f"檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}",
            ),
            ("WRITE_FAILED", None, str(error)),
        )
        for kind, backup_path, reason in cases:
            with self.subTest(kind):
                self.boxes.clear()
                frame = self._frame()
                problem = config.ConfigSaveProblem(
                    getattr(config.ConfigSaveProblemKind, kind), error, self.config_path, backup_path
                )

                frame._report_settings_save_problem(problem)

                self.assertEqual(self.boxes, [self._box(frame, reason)])

    def test_the_box_belongs_to_the_active_window(self) -> None:
        # The settings dialog after Apply, Dictionary Management after a rename.
        self.config_path.mkdir()
        frame = self._frame()
        self.active_window = Mock(name="settings dialog")

        frame._set_active_dictionary("math")

        self.assertEqual(self.boxes, [self._box(frame, self.CANNOT_OPEN, parent=self.active_window)])


class _RecordingFont:
    """``wx.Font`` stand-in: the font it copies and the calls made on it."""

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame.view_settings = view
        frame._apply_editor_view_settings = Mock()
        frame._config_store = Mock(spec=gui.ConfigStore)
        return frame

    def make_dialog(self):
```

```python
        frame.view_settings = view
        frame._apply_editor_view_settings = Mock()
        frame._config_store = Mock(spec=gui.ConfigStore)
        # A save that works: no settings save problem to report (F-12 D6).
        frame._config_store.set_view_settings.return_value = None
        return frame

    def make_dialog(self):
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            with self.subTest(start=start, rotation=rotation):
                frame = self.make_frame(ViewSettings(start, "dark", "default"))
                dialog = self.make_dialog()
                with self.open_dialog(dialog), patch.object(gui, "save_view_settings") as save:
                    frame.on_editor_mousewheel(self.wheel(rotation))

                # KNOWN QUIRK (P2-4 spec, 1): the size did not change, but it is saved and synced again.
```

```python
            with self.subTest(start=start, rotation=rotation):
                frame = self.make_frame(ViewSettings(start, "dark", "default"))
                dialog = self.make_dialog()
                with self.open_dialog(dialog), patch.object(gui, "save_view_settings", return_value=None) as save:
                    frame.on_editor_mousewheel(self.wheel(rotation))

                # KNOWN QUIRK (P2-4 spec, 1): the size did not change, but it is saved and synced again.
```

Edit: `client/tests/test_gui_document_flows.py`

```python
                frame = self.make_frame()
                dialog = self.make_dialog()
                event = self.wheel(rotation, control_down)
                with self.open_dialog(dialog), patch.object(gui, "save_view_settings") as save:
                    frame.on_editor_mousewheel(event)

                event.Skip.assert_called_once_with()
```

```python
                frame = self.make_frame()
                dialog = self.make_dialog()
                event = self.wheel(rotation, control_down)
                with self.open_dialog(dialog), patch.object(gui, "save_view_settings", return_value=None) as save:
                    frame.on_editor_mousewheel(event)

                event.Skip.assert_called_once_with()
```

Edit: `client/tests/test_gui_document_flows.py`

```python

    def test_without_an_open_dialog_the_editors_and_the_config_still_change(self) -> None:
        frame = self.make_frame()
        with self.open_dialog(None), patch.object(gui, "save_view_settings") as save:
            frame.on_editor_mousewheel(self.wheel(-120))

        expected = ViewSettings(11, "dark", "default")
```

```python

    def test_without_an_open_dialog_the_editors_and_the_config_still_change(self) -> None:
        frame = self.make_frame()
        with self.open_dialog(None), patch.object(gui, "save_view_settings", return_value=None) as save:
            frame.on_editor_mousewheel(self.wheel(-120))

        expected = ViewSettings(11, "dark", "default")
```

Edit: `client/tests/test_gui_document_flows.py`

```python
    def test_a_cancelled_dialog_is_no_longer_synced(self) -> None:
        frame = self.make_frame()
        dialog = self.make_dialog()
        with self.open_dialog(dialog), patch.object(gui, "save_view_settings") as save:
            frame.on_editor_mousewheel(self.wheel(120))
            dialog.on_cancel()
            self.assertIsNone(gui.DotExpressSettingsDialog._instance)
```

```python
    def test_a_cancelled_dialog_is_no_longer_synced(self) -> None:
        frame = self.make_frame()
        dialog = self.make_dialog()
        with self.open_dialog(dialog), patch.object(gui, "save_view_settings", return_value=None) as save:
            frame.on_editor_mousewheel(self.wheel(120))
            dialog.on_cancel()
            self.assertIsNone(gui.DotExpressSettingsDialog._instance)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        with (
            patch.object(gui.TextProcessingDialog, "_instance", text_dialog),
            self.open_dialog(None),
            patch.object(gui, "save_view_settings") as save,
        ):
            frame.on_editor_mousewheel(self.wheel(120))

```

```python
        with (
            patch.object(gui.TextProcessingDialog, "_instance", text_dialog),
            self.open_dialog(None),
            patch.object(gui, "save_view_settings", return_value=None) as save,
        ):
            frame.on_editor_mousewheel(self.wheel(120))

```

Edit: `client/tests/test_i18n.py`

```python

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")

```

```python

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_settings_not_saved_strings_are_translated(self) -> None:
        # F-12 (D6): the box of the first settings change of a session that cannot be saved.
        message = (
            'DotExpress cannot save its settings to "{path}". Changes to the settings apply until DotExpress is closed, '
            "but they are not kept. This message is not shown again until DotExpress is started again.\n\n{reason}"
        )
        backup = 'The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Details: {error}'
        expected = {
            "Settings Not Saved": "設定未儲存",
            message: (
                "DotExpress 無法將設定儲存到「{path}」。設定的變更在關閉 DotExpress 之前有效，但不會保留。"
                "在下次啟動 DotExpress 之前，不會再顯示這則訊息。\n\n{reason}"
            ),
            backup: "檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")

```

```bash
$PY -B -X utf8 -m unittest tests.test_config tests.test_translation_settings tests.test_translation_tables tests.test_view_settings tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_a_damaged_file_whose_backup_fails_is_backup_failed (tests.test_config.ConfigSaveProblemTest.test_a_damaged_file_whose_backup_fails_is_backup_failed)
AttributeError: 'NoneType' object has no attribute 'kind'
ERROR: test_a_file_that_cannot_be_read_is_unreadable (tests.test_config.ConfigSaveProblemTest.test_a_file_that_cannot_be_read_is_unreadable) [set_output_mode]
AttributeError: module 'config' has no attribute 'ConfigSaveProblem'
ERROR: test_a_file_that_cannot_be_read_is_unreadable (tests.test_config.ConfigSaveProblemTest.test_a_file_that_cannot_be_read_is_unreadable) [set_conversion_wid
ERROR: test_a_file_that_cannot_be_read_is_unreadable (tests.test_config.ConfigSaveProblemTest.test_a_file_that_cannot_be_read_is_unreadable) [set_selected_dicti
ERROR: test_a_file_that_cannot_be_read_is_unreadable (tests.test_config.ConfigSaveProblemTest.test_a_file_that_cannot_be_read_is_unreadable) [set_translation_ta
ERROR: test_a_file_that_cannot_be_read_is_unreadable (tests.test_config.ConfigSaveProblemTest.test_a_file_that_cannot_be_read_is_unreadable) [set_view_settings]
ERROR: test_a_write_that_fails_is_write_failed (tests.test_config.ConfigSaveProblemTest.test_a_write_that_fails_is_write_failed)
ERROR: test_each_kind_of_problem_gives_its_reason (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_each_kind_of_problem_gives_its_reason) [UNREA
ERROR: test_each_kind_of_problem_gives_its_reason (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_each_kind_of_problem_gives_its_reason) [BACKU
ERROR: test_each_kind_of_problem_gives_its_reason (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_each_kind_of_problem_gives_its_reason) [WRITE
FAIL: test_save_calls_every_setter_and_returns_the_first_problem (tests.test_translation_settings.TranslationSettingsTest.test_save_calls_every_setter_and_retur
AssertionError: None is not <object object at <addr>>
FAIL: test_save_returns_what_the_store_returns (tests.test_translation_tables.TranslationTablesTest.test_save_returns_what_the_store_returns)
FAIL: test_save_returns_what_the_store_returns (tests.test_view_settings.ViewSettingsTest.test_save_returns_what_the_store_returns)
FAIL: test_a_settings_change_that_cannot_be_saved_shows_one_box_and_still_applies (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_a_settings_ch
AssertionError: Lists differ: [] != [(('DotExpress 無法將設定儲存到「C:\\Users\\tseng\\[229 chars]<addr>})]
FAIL: test_font_size_and_dictionary_changes_report_through_the_same_flag (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_font_size_and_dictiona
FAIL: test_the_box_belongs_to_the_active_window (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_the_box_belongs_to_the_active_window)
AssertionError: Lists differ: [] != [(('DotExpress 無法將設定儲存到「C:\\Users\\tseng\\[230 chars]'>})]
FAIL: test_settings_not_saved_strings_are_translated (tests.test_i18n.TranslationTest.test_settings_not_saved_strings_are_translated)
AssertionError: {'Set[14 chars]d': 'Settings Not Saved', 'DotExpress cannot s[624 chars]or}'} != {'Set[14 chars]d': '設定未儲存', 'DotExpress cannot save its setti[4
Ran 321 tests
FAILED (failures=8, errors=10)
```

- [x] **Step 2: Green: `ConfigSaveProblem` and the box** (`client/config.py`, `client/settings/translation.py`, `translation_tables.py`, `view.py`, 4 spaces; `client/gui.py`, tabs).**

Edit: `client/config.py`

```python
import json
import logging
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4
```

```python
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4
```

Edit: `client/config.py`

```python

def _signature(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


class _UnreadableConfig(dict):
```

```python

def _signature(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


class ConfigSaveProblemKind(Enum):
    UNREADABLE = "unreadable"  # config.json exists but could not be read, so it is kept
    BACKUP_FAILED = "backup_failed"  # damaged, and config.json.bak could not be written first
    WRITE_FAILED = "write_failed"


@dataclass(frozen=True)
class ConfigSaveProblem:
    """Why a setting did not reach config.json (F-12 D6); the change still applies in memory."""

    kind: ConfigSaveProblemKind
    error: BaseException
    path: Path
    backup_path: Path | None = None  # BACKUP_FAILED only


class _UnreadableConfig(dict):
```

Edit: `client/config.py`

```python
        content = self._path.read_bytes()
        write_bytes_atomically(self._path.with_name(f"{self._path.name}.bak"), lambda stream: stream.write(content))

    def _save(self, data: dict) -> None:
        path = str(self._path)
        if isinstance(data, _UnreadableConfig) and isinstance(data.error, OSError):
            self._skip_save_of_unreadable_file(data.error)
            return
        try:
            if isinstance(data, _UnreadableConfig):
                self._backup_unreadable()
            if not os.path.exists(path):
                data = {
                    "language_detection": {
```

```python
        content = self._path.read_bytes()
        write_bytes_atomically(self._path.with_name(f"{self._path.name}.bak"), lambda stream: stream.write(content))

    def _save(self, data: dict) -> ConfigSaveProblem | None:
        """Write ``data``; ``None`` if it was written, else why not (logged as before, F-8 D11)."""
        path = str(self._path)
        if isinstance(data, _UnreadableConfig) and isinstance(data.error, OSError):
            self._skip_save_of_unreadable_file(data.error)
            return ConfigSaveProblem(ConfigSaveProblemKind.UNREADABLE, data.error, self._path)
        if isinstance(data, _UnreadableConfig):
            try:
                self._backup_unreadable()
            except Exception as error:
                _log_current_exception(logging.ERROR, "Failed to save config file %s", path)
                return ConfigSaveProblem(
                    ConfigSaveProblemKind.BACKUP_FAILED,
                    error,
                    self._path,
                    self._path.with_name(f"{self._path.name}.bak"),
                )
        try:
            if not os.path.exists(path):
                data = {
                    "language_detection": {
```

Edit: `client/config.py`

```python
                encoding="utf-8",
                newline=None,
            )
        except Exception:
            _log_current_exception(logging.ERROR, "Failed to save config file %s", path)

    def _set_section_value(self, section: str, key: str, value: object) -> None:
        data = self._load()
        section_data = _get_section(data, section).copy()
        section_data[key] = value
        data[section] = section_data
        self._save(data)

    def _get_dict_setting(self, section: str, key: str, default: dict) -> dict:
        data = self._load()
```

```python
                encoding="utf-8",
                newline=None,
            )
        except Exception as error:
            _log_current_exception(logging.ERROR, "Failed to save config file %s", path)
            return ConfigSaveProblem(ConfigSaveProblemKind.WRITE_FAILED, error, self._path)
        return None

    def _set_section_value(self, section: str, key: str, value: object) -> ConfigSaveProblem | None:
        data = self._load()
        section_data = _get_section(data, section).copy()
        section_data[key] = value
        data[section] = section_data
        return self._save(data)

    def _get_dict_setting(self, section: str, key: str, default: dict) -> dict:
        data = self._load()
```

Edit: `client/config.py`

```python
    def get_translation_tables(self) -> dict:
        return self._get_dict_setting(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, DEFAULT_TRANSLATION_TABLES)

    def set_translation_tables(self, tables: dict[str, str]) -> None:
        self._set_section_value(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, dict(tables))

    def get_output_mode(self, default: str = DEFAULT_OUTPUT_MODE) -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(OUTPUT_MODE_KEY)
        return value if isinstance(value, str) else default

    def set_output_mode(self, output_mode: str) -> None:
        self._set_section_value(CONVERSION_SECTION, OUTPUT_MODE_KEY, output_mode)

    def get_conversion_width(self, default: int = DEFAULT_CONVERSION_WIDTH) -> int:
        data = self._load()
        width = _coerce_int(_get_section(data, CONVERSION_SECTION).get(WIDTH_KEY))
        return width if width is not None else default

    def set_conversion_width(self, width: int) -> None:
        self._set_section_value(CONVERSION_SECTION, WIDTH_KEY, width)

    def get_selected_dictionary(self, default: str = "default") -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(SELECTED_DICTIONARY_KEY)
        return value if isinstance(value, str) else default

    def set_selected_dictionary(self, dictionary_name: str) -> None:
        self._set_section_value(CONVERSION_SECTION, SELECTED_DICTIONARY_KEY, dictionary_name)

    def get_view_font_size(self, default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
        data = self._load()
```

```python
    def get_translation_tables(self) -> dict:
        return self._get_dict_setting(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, DEFAULT_TRANSLATION_TABLES)

    def set_translation_tables(self, tables: dict[str, str]) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, TRANSLATION_TABLES_KEY, dict(tables))

    def get_output_mode(self, default: str = DEFAULT_OUTPUT_MODE) -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(OUTPUT_MODE_KEY)
        return value if isinstance(value, str) else default

    def set_output_mode(self, output_mode: str) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, OUTPUT_MODE_KEY, output_mode)

    def get_conversion_width(self, default: int = DEFAULT_CONVERSION_WIDTH) -> int:
        data = self._load()
        width = _coerce_int(_get_section(data, CONVERSION_SECTION).get(WIDTH_KEY))
        return width if width is not None else default

    def set_conversion_width(self, width: int) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, WIDTH_KEY, width)

    def get_selected_dictionary(self, default: str = "default") -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(SELECTED_DICTIONARY_KEY)
        return value if isinstance(value, str) else default

    def set_selected_dictionary(self, dictionary_name: str) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, SELECTED_DICTIONARY_KEY, dictionary_name)

    def get_view_font_size(self, default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
        data = self._load()
```

Edit: `client/config.py`

```python
        value = _get_section(data, VIEW_SECTION).get(BRAILLE_FONT_KEY)
        return value if isinstance(value, str) else default

    def set_view_settings(self, font_size: int, scheme: str, braille_font: str) -> None:
        data = self._load()
        section_data = _get_section(data, VIEW_SECTION).copy()
        section_data.update(
```

```python
        value = _get_section(data, VIEW_SECTION).get(BRAILLE_FONT_KEY)
        return value if isinstance(value, str) else default

    def set_view_settings(self, font_size: int, scheme: str, braille_font: str) -> ConfigSaveProblem | None:
        data = self._load()
        section_data = _get_section(data, VIEW_SECTION).copy()
        section_data.update(
```

Edit: `client/config.py`

```python
            }
        )
        data[VIEW_SECTION] = section_data
        self._save(data)

    def get_or_create_client_id(self) -> str:
        data = self._load()
```

```python
            }
        )
        data[VIEW_SECTION] = section_data
        return self._save(data)

    def get_or_create_client_id(self) -> str:
        data = self._load()
```

Edit: `client/config.py`

```python
        section_data = _get_section(data, CLIENT_SECTION).copy()
        section_data[CLIENT_ID_KEY] = client_id
        data[CLIENT_SECTION] = section_data
        self._save(data)
        return client_id
```

```python
        section_data = _get_section(data, CLIENT_SECTION).copy()
        section_data[CLIENT_ID_KEY] = client_id
        data[CLIENT_SECTION] = section_data
        # Not a setting the user changed, and saved on a background thread: a problem is only
        # logged (F-12 D6).
        self._save(data)
        return client_id
```

Edit: `client/settings/translation.py`

```python
from dataclasses import dataclass

from config import (
    ConfigStore,
    DEFAULT_CONVERSION_WIDTH,
    DEFAULT_OUTPUT_MODE,
```

```python
from dataclasses import dataclass

from config import (
    ConfigSaveProblem,
    ConfigStore,
    DEFAULT_CONVERSION_WIDTH,
    DEFAULT_OUTPUT_MODE,
```

Edit: `client/settings/translation.py`

```python
    return normalize_translation_settings(settings, dictionary_names)


def save_translation_settings(store: ConfigStore, settings: TranslationSettings) -> None:
    store.set_output_mode(settings.output_mode)
    store.set_conversion_width(settings.width)
    store.set_selected_dictionary(settings.selected_dictionary)

```

```python
    return normalize_translation_settings(settings, dictionary_names)


def save_translation_settings(store: ConfigStore, settings: TranslationSettings) -> ConfigSaveProblem | None:
    """Save the three settings, each one even if another fails; the first problem, or ``None`` (F-12 D6)."""
    problems = (
        store.set_output_mode(settings.output_mode),
        store.set_conversion_width(settings.width),
        store.set_selected_dictionary(settings.selected_dictionary),
    )
    return next((problem for problem in problems if problem is not None), None)

```

Edit: `client/settings/translation_tables.py`

```python
    return dict(store.get_translation_tables())


def save_translation_tables(store: config.ConfigStore, tables: dict[str, str]) -> None:
    store.set_translation_tables(dict(tables))
```

```python
    return dict(store.get_translation_tables())


def save_translation_tables(store: config.ConfigStore, tables: dict[str, str]) -> config.ConfigSaveProblem | None:
    return store.set_translation_tables(dict(tables))
```

Edit: `client/settings/view.py`

```python
from dataclasses import dataclass

from config import (
    ConfigStore,
    DEFAULT_BRAILLE_FONT,
    DEFAULT_VIEW_FONT_SIZE,
```

```python
from dataclasses import dataclass

from config import (
    ConfigSaveProblem,
    ConfigStore,
    DEFAULT_BRAILLE_FONT,
    DEFAULT_VIEW_FONT_SIZE,
```

Edit: `client/settings/view.py`

```python
    )


def save_view_settings(store: ConfigStore, settings: ViewSettings) -> None:
    normalized = normalize_view_settings(settings)
    store.set_view_settings(
        normalized.font_size,
        normalized.scheme,
        normalized.braille_font,
```

```python
    )


def save_view_settings(store: ConfigStore, settings: ViewSettings) -> ConfigSaveProblem | None:
    normalized = normalize_view_settings(settings)
    return store.set_view_settings(
        normalized.font_size,
        normalized.scheme,
        normalized.braille_font,
```

Edit: `client/gui.py`

```python
from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
from ui.menu_builder import apply_document_menu_state, build_document_menu
from ui.message_box import message_box
from config import ConfigStore, DEFAULT_TRANSLATION_TABLES
from settings.translation import (
	TranslationSettings,
	load_translation_settings,
```

```python
from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
from ui.menu_builder import apply_document_menu_state, build_document_menu
from ui.message_box import message_box
from config import ConfigSaveProblem, ConfigSaveProblemKind, ConfigStore, DEFAULT_TRANSLATION_TABLES
from settings.translation import (
	TranslationSettings,
	load_translation_settings,
```

Edit: `client/gui.py`

```python
	# Class attributes, so that frames built without __init__ (tests) have them too (F-7, M-5).
	_closing = False
	_close_finished = False

	def __init__(
		self,
```

```python
	# Class attributes, so that frames built without __init__ (tests) have them too (F-7, M-5).
	_closing = False
	_close_finished = False
	# The first settings save problem of the session was shown (F-12 D6).
	_settings_save_problem_reported = False

	def __init__(
		self,
```

Edit: `client/gui.py`

```python
		self.translation_tables = tables
		self._apply_editor_view_settings(view)

		save_translation_settings(self._config_store, translation)
		save_translation_tables(self._config_store, tables)
		save_view_settings(self._config_store, view)
		return DotExpressSettingsSnapshot.create(translation, tables, view)

	def _set_active_dictionary(self, selected_name: str) -> None:
```

```python
		self.translation_tables = tables
		self._apply_editor_view_settings(view)

		problems = (
			save_translation_settings(self._config_store, translation),
			save_translation_tables(self._config_store, tables),
			save_view_settings(self._config_store, view),
		)
		self._report_settings_save_problem(next((problem for problem in problems if problem is not None), None))
		return DotExpressSettingsSnapshot.create(translation, tables, view)

	def _set_active_dictionary(self, selected_name: str) -> None:
```

Edit: `client/gui.py`

```python
			width=self.translation_settings.width,
			selected_dictionary=selected_name,
		)
		self._config_store.set_selected_dictionary(selected_name)

	def _get_selected_dictionary_path(self) -> Path:
		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)
```

```python
			width=self.translation_settings.width,
			selected_dictionary=selected_name,
		)
		self._report_settings_save_problem(self._config_store.set_selected_dictionary(selected_name))

	def _report_settings_save_problem(self, problem: ConfigSaveProblem | None) -> None:
		"""Show the first settings save problem of the session; later ones are only logged (F-12 D6).

		Once per session, as Ctrl+wheel saves on every notch. Shown after the change, which
		still applies, in a box that belongs to the active window (the settings dialog,
		Dictionary Management), else to the frame.
		"""
		if problem is None or self._settings_save_problem_reported:
			return
		self._settings_save_problem_reported = True
		if problem.kind is ConfigSaveProblemKind.UNREADABLE:
			reason = _(
				"The file cannot be opened. It may be in use by another program, or you may not have "
				"permission to read it. Close the other program and try again."
			)
		elif problem.kind is ConfigSaveProblemKind.BACKUP_FAILED:
			reason = _(
				'The file is damaged, and a backup copy could not be saved as "{backup}" before replacing it. Details: {error}'
			).format(backup=problem.backup_path, error=problem.error)
		else:
			reason = str(problem.error)
		message_box(
			_(
				'DotExpress cannot save its settings to "{path}". Changes to the settings apply until DotExpress is closed, '
				"but they are not kept. This message is not shown again until DotExpress is started again.\n\n{reason}"
			).format(path=problem.path, reason=reason),
			_("Settings Not Saved"),
			wx.OK | wx.ICON_WARNING,
			parent=wx.GetActiveWindow() or self,
		)

	def _get_selected_dictionary_path(self) -> Path:
		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)
```

Edit: `client/gui.py`

```python
			replace(self.view_settings, font_size=font_size)
		)
		self._apply_editor_view_settings(self.view_settings)
		save_view_settings(self._config_store, self.view_settings)
		settings_dialog = DotExpressSettingsDialog.open_instance()
		if settings_dialog is not None:
			settings_dialog.sync_font_size(self.view_settings.font_size)
```

```python
			replace(self.view_settings, font_size=font_size)
		)
		self._apply_editor_view_settings(self.view_settings)
		self._report_settings_save_problem(save_view_settings(self._config_store, self.view_settings))
		settings_dialog = DotExpressSettingsDialog.open_instance()
		if settings_dialog is not None:
			settings_dialog.sync_font_size(self.view_settings.font_size)
```

- [x] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_config tests.test_translation_settings tests.test_translation_tables tests.test_view_settings tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (only the tests that compare with the zh_TW text fail: the new msgids are not in the catalog yet):

```text
FAIL: test_a_settings_change_that_cannot_be_saved_shows_one_box_and_still_applies (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_a_settings_ch
AssertionError: Lists differ: [(('DotExpress cannot save its settings to "C:\\Users\\t[335 chars]<addr>})] != [(('DotExpress 無法將設定儲存到「C:\\Users\\tseng\\AppData\
FAIL: test_each_kind_of_problem_gives_its_reason (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_each_kind_of_problem_gives_its_reason) [UNREAD
FAIL: test_each_kind_of_problem_gives_its_reason (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_each_kind_of_problem_gives_its_reason) [BACKUP
AssertionError: Lists differ: [(('DotExpress cannot save its settings to "C:\\Users\\t[479 chars]<addr>})] != [(('DotExpress 無法將設定儲存到「C:\\Users\\tseng\\AppData\
FAIL: test_each_kind_of_problem_gives_its_reason (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_each_kind_of_problem_gives_its_reason) [WRITE_
AssertionError: Lists differ: [(('DotExpress cannot save its settings to "C:\\Users\\t[317 chars]<addr>})] != [(('DotExpress 無法將設定儲存到「C:\\Users\\tseng\\AppData\
FAIL: test_font_size_and_dictionary_changes_report_through_the_same_flag (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_font_size_and_dictiona
FAIL: test_the_box_belongs_to_the_active_window (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_the_box_belongs_to_the_active_window)
AssertionError: Lists differ: [(('DotExpress cannot save its settings to "C:\\Users\\t[336 chars]'>})] != [(('DotExpress 無法將設定儲存到「C:\\Users\\tseng\\AppData\\Loc
FAIL: test_settings_not_saved_strings_are_translated (tests.test_i18n.TranslationTest.test_settings_not_saved_strings_are_translated)
AssertionError: {'Set[14 chars]d': 'Settings Not Saved', 'DotExpress cannot s[624 chars]or}'} != {'Set[14 chars]d': '設定未儲存', 'DotExpress cannot save its setti[4
Ran 321 tests
FAILED (failures=8)
```

- [x] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected:

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
396 translated messages, 1 fuzzy translation, 2 untranslated messages.
#: gui.py:481
#, fuzzy
msgid "Settings Not Saved"
msgstr "設定"
#: gui.py:472
#, python-brace-format
msgid ""
"The file is damaged, and a backup copy could not be saved as \"{backup}\" "
"before replacing it. Details: {error}"
msgstr ""

#: gui.py:478
#, python-brace-format
msgid ""
"DotExpress cannot save its settings to \"{path}\". Changes to the settings "
"apply until DotExpress is closed, but they are not kept. This message is not "
"shown again until DotExpress is started again.\n"
"\n"
"{reason}"
msgstr ""
27
```

- [x] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
"The file is damaged, and a backup copy could not be saved as \"{backup}\" "
"before replacing it. Details: {error}"
msgstr ""

#: gui.py:478
#, python-brace-format
```

```po
"The file is damaged, and a backup copy could not be saved as \"{backup}\" "
"before replacing it. Details: {error}"
msgstr ""
"檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}"

#: gui.py:478
#, python-brace-format
```

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
"\n"
"{reason}"
msgstr ""

#: gui.py:481
#, fuzzy
msgid "Settings Not Saved"
msgstr "設定"

#: gui.py:521
msgid "Cannot Save Document"
```

```po
"\n"
"{reason}"
msgstr ""
"DotExpress 無法將設定儲存到「{path}」。設定的變更在關閉 DotExpress 之前有效，但不會保留。在下次啟動 DotExpress 之前，不會再顯示這則訊息。\n"
"\n"
"{reason}"

#: gui.py:481
msgid "Settings Not Saved"
msgstr "設定未儲存"

#: gui.py:521
msgid "Cannot Save Document"
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
a second msgmerge changes nothing
msgfmt exit 0
399 translated messages.
0
catalog keys: 400
 1 '匯出完成，但有錯誤'
 2 '所有文件皆已成功匯出。'
 3 '成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}'
 4 '發生不明的錯誤。'
 5 '選取的轉譯表無法轉譯這段文字。'
 6 '(missing)'
 7 '(missing)'
 8 '(missing)'
 9 '(missing)'
10 '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。'
11 '無法匯入這種類型的檔案。'
12 '副檔名與選取的檔案類型不符。'
13 '匯入的檔案必須是有效的 DotExpress DEP 封裝檔。'
14 '這個 PDF 檔已加密，無法匯入。'
15 'EPUB 檔已損壞，或沒有可讀取的內容。'
16 '無法讀取字典「{name}」。{reason}'
17 '無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。'
18 '名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清單中。'
19 '請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n{folder}'
20 '設定未儲存'
21 'DotExpress 無法將設定儲存到「{path}」。設定的變更在關閉 DotExpress 之前有效，但不會保留。在下次啟動 DotExpress 之前，不會再顯示這則訊息。\n\n{reason}'
22 '檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}'
23 '(missing)'
33551
locales/dotexpress.pot:400
locales/zh_TW/LC_MESSAGES/dotexpress.po:400
27
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 399 sha256 85d26d612469d44fc2e8d60567a7a1eb8dfbb6787cec25cb1ad7f39b2fc6cc99
```

- [x] **Step 6: Green: the new tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_config tests.test_translation_settings tests.test_translation_tables tests.test_view_settings tests.test_gui_document_flows tests.test_i18n -v 2>&1 | grep -E "^(test_a_damaged_file_whose_backup_fails_is_backup_failed|test_a_file_that_cannot_be_read_is_unreadable|test_a_settings_change_that_cannot_be_saved_shows_one_box_and_still_applies|test_a_write_that_fails_is_write_failed|test_each_kind_of_problem_gives_its_reason|test_every_setter_returns_none_when_the_save_works|test_font_size_and_dictionary_changes_report_through_the_same_flag|test_no_box_when_the_settings_are_saved|test_save_calls_every_setter_and_returns_the_first_problem|test_save_returns_none_when_every_setter_saves|test_save_returns_what_the_store_returns|test_settings_not_saved_strings_are_translated|test_the_box_belongs_to_the_active_window|test_the_client_id_and_the_language_ignore_a_failed_save) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_config tests.test_translation_settings tests.test_translation_tables tests.test_view_settings tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (each new test once per subTest-free run, in the order unittest runs them):

```text
test_a_damaged_file_whose_backup_fails_is_backup_failed ok
test_a_file_that_cannot_be_read_is_unreadable ok
test_a_write_that_fails_is_write_failed ok
test_every_setter_returns_none_when_the_save_works ok
test_the_client_id_and_the_language_ignore_a_failed_save ok
test_save_calls_every_setter_and_returns_the_first_problem ok
test_save_returns_none_when_every_setter_saves ok
test_save_returns_what_the_store_returns ok
test_save_returns_what_the_store_returns ok
test_a_settings_change_that_cannot_be_saved_shows_one_box_and_still_applies ok
test_each_kind_of_problem_gives_its_reason ok
test_font_size_and_dictionary_changes_report_through_the_same_flag ok
test_no_box_when_the_settings_are_saved ok
test_the_box_belongs_to_the_active_window ok
test_settings_not_saved_strings_are_translated ok
Ran 321 tests
OK
Ran 1614 tests
OK (skipped=6)
```

- [x] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_config.py client/tests/test_translation_settings.py client/tests/test_translation_tables.py client/tests/test_view_settings.py client/tests/test_gui_document_flows.py client/tests/test_i18n.py client/config.py client/settings/translation.py client/settings/translation_tables.py client/settings/view.py client/gui.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: tell the user when settings cannot be saved (F-12, F-8a M-7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/config.py                               |  66 ++++++++---
 client/gui.py                                  |  48 +++++++-
 client/locales/dotexpress.pot                  | 123 +++++++++++---------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 32855 -> 33551 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 127 ++++++++++++---------
 client/settings/translation.py                 |  13 ++-
 client/settings/translation_tables.py          |   4 +-
 client/settings/view.py                        |   5 +-
 client/tests/test_config.py                    |  90 +++++++++++++++
 client/tests/test_gui_document_flows.py        | 148 +++++++++++++++++++++++--
 client/tests/test_i18n.py                      |  19 ++++
 client/tests/test_translation_settings.py      |  19 ++++
 client/tests/test_translation_tables.py        |  10 ++
 client/tests/test_view_settings.py             |  10 ++
 14 files changed, 538 insertions(+), 144 deletions(-)
cd5b9c3959ca123d34771634df05d9a028806c40
```

### Task 6: Name the document of a failed conversion that is not open (D7)

- [x] **Step 1: Red: Test Plan C4, C5, A (string 23).** `test_conversion_presenter.py` (4 spaces): a manual failure after switching to beta names alpha; after switching away and back, without a switch, and without a starting document it is not named. `test_export_coordinator.py` (4 spaces): a single export of beta names it when alpha is open at delivery, also after a switch away during the conversion, not when beta was opened during it; the existing pending-error test opens beta first (Spec Corrections 10). `test_i18n.py`: string 23**

Edit: `client/tests/test_conversion_presenter.py`

```python

        self.assertEqual(self._take(), self._end() + [("show_error", BIG5_DICTIONARY_FAILED, "錯誤")])

    # --- export completion ----------------------------------------------------

    def test_convert_for_export_converts_given_text_without_checks(self) -> None:
```

```python

        self.assertEqual(self._take(), self._end() + [("show_error", BIG5_DICTIONARY_FAILED, "錯誤")])

    def _failed_after(self, switch) -> list:
        """Convert alpha, run ``switch`` while the job runs, deliver a failure; the events after it."""
        self.outputs["source"] = ConversionStageError("translation", RuntimeError("boom"))
        presenter = self._presenter()
        presenter.convert()
        switch()
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        return self._take()

    def test_a_failure_after_switching_names_the_document(self) -> None:
        # F-12 (D7, F-9 review M-9): the box would otherwise seem to be about the open document.
        events = self._failed_after(lambda: self._switch_to("beta"))

        self.assertEqual(
            events,
            self._end() + [("show_error", "無法轉換文件「alpha」。\n\n轉譯失敗：boom", "錯誤")],
        )

    def _not_named(self) -> list:
        return self._end() + [("show_error", _("Translation failed: {error}").format(error="boom"), _("Error"))]

    def test_a_failure_of_the_open_document_is_not_named(self) -> None:
        self.assertEqual(self._failed_after(lambda: None), self._not_named())

    def test_a_failure_after_switching_away_and_back_is_not_named(self) -> None:
        events = self._failed_after(lambda: (self._switch_to("beta"), self._switch_to("alpha")))

        self.assertEqual(events, self._not_named())

    def test_a_failure_without_a_starting_document_is_not_named(self) -> None:
        # No document to name, also when one was opened during the conversion.
        self.documents.open_name = None

        events = self._failed_after(lambda: self.documents.open_document("alpha"))

        self.assertEqual(events, self._not_named())

    # --- export completion ----------------------------------------------------

    def test_convert_for_export_converts_given_text_without_checks(self) -> None:
```

Edit: `client/tests/test_export_coordinator.py`

```python
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", None))

    def test_export_document_pending_conversion_error_shows_it(self) -> None:
        self.view.paths.append(self.root / "beta.brl")
        self.coordinator.export_document(Document("beta", "b", None), "brl")
        self._take()
```

```python
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", None))

    def test_export_document_pending_conversion_error_shows_it(self) -> None:
        # The exported document is the open one: the message is not named (F-12 D7).
        self.documents.open_document("beta")
        self.view.paths.append(self.root / "beta.brl")
        self.coordinator.export_document(Document("beta", "b", None), "brl")
        self._take()
```

Edit: `client/tests/test_export_coordinator.py`

```python

        self.assertEqual(self._take(), [("show_error", "boom", _("Error"))])
        self.assertEqual(self._written(), {})

    def test_export_document_pending_without_table_shows_error_only(self) -> None:
        self.conversions.missing_message = MISSING_TABLE
```

```python

        self.assertEqual(self._take(), [("show_error", "boom", _("Error"))])
        self.assertEqual(self._written(), {})

    def test_a_failed_export_of_a_document_that_is_not_open_names_it(self) -> None:
        # F-12 (D7): the open document at delivery decides, not the one at the request.
        cases = (
            ("another document open", "alpha", "alpha", True),
            ("opened during the conversion", "alpha", "beta", False),
            ("switched away during the conversion", "beta", "alpha", True),
        )
        for label, open_at_request, open_at_delivery, named in cases:
            with self.subTest(label):
                self.events.clear()
                self.conversions.started.clear()
                self.documents.open_document(open_at_request)
                self.view.paths.append(self.root / "beta.brl")
                self.coordinator.export_document(Document("beta", "b", None), "brl")
                self._take()
                self.documents.open_document(open_at_delivery)

                _on_success, on_error = self.conversions.started[0]
                on_error("轉譯失敗：boom")

                message = "無法轉換文件「beta」。\n\n轉譯失敗：boom" if named else "轉譯失敗：boom"
                self.assertEqual(self._take(), [("show_error", message, _("Error"))])

    def test_export_document_pending_without_table_shows_error_only(self) -> None:
        self.conversions.missing_message = MISSING_TABLE
```

Edit: `client/tests/test_i18n.py`

```python

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")

```

```python

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_failed_conversion_of_a_document_that_is_not_open_string_is_translated(self) -> None:
        # F-12 (D7): a failed conversion of a document that is not the open one names it.
        translation = i18n.load_translation()

        self.assertEqual(
            translation.gettext('Document "{name}" could not be converted.\n\n{error}'),
            "無法轉換文件「{name}」。\n\n{error}",
        )

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")

```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_export_coordinator tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
FAIL: test_a_failure_after_switching_names_the_document (tests.test_conversion_presenter.ConversionPresenterTest.test_a_failure_after_switching_names_the_docume
AssertionError: Lists differ: [('ti[51 chars]', False), ('show_error', '轉譯失敗：boom', '錯誤')] != [('ti[51 chars]', False), ('show_error', '無法轉換文件「alpha」。\n\n轉譯失敗：b
FAIL: test_a_failed_export_of_a_document_that_is_not_open_names_it (tests.test_export_coordinator.ExportCoordinatorTest.test_a_failed_export_of_a_document_that_
AssertionError: Lists differ: [('show_error', '轉譯失敗：boom', '錯誤')] != [('show_error', '無法轉換文件「beta」。\n\n轉譯失敗：boom', '錯誤')]
FAIL: test_failed_conversion_of_a_document_that_is_not_open_string_is_translated (tests.test_i18n.TranslationTest.test_failed_conversion_of_a_document_that_is_n
AssertionError: 'Document "{name}" could not be converted.\n\n{error}' != '無法轉換文件「{name}」。\n\n{error}'
Ran 106 tests
FAILED (failures=4)
```

- [x] **Step 2: Green: name the document when another one is open at delivery** (`client/ui/conversion_presenter.py`, `client/documents/export_coordinator.py`, 4 spaces).**

Edit: `client/ui/conversion_presenter.py`

```python
A manual conversion's result goes to the document that was open when it started. If
another document is open when it completes, the result is saved to the starting
document and the open one is left alone; if the starting document is gone or holds
another text, the result is discarded and logged (F-9).
"""

from __future__ import annotations
```

```python
A manual conversion's result goes to the document that was open when it started. If
another document is open when it completes, the result is saved to the starting
document and the open one is left alone; if the starting document is gone or holds
another text, the result is discarded and logged (F-9). A failure names the starting
document when another one is open (F-12).
"""

from __future__ import annotations
```

Edit: `client/ui/conversion_presenter.py`

```python
            if active.job.export is not None:
                active.job.export.on_error(message)
            else:
                self._view.show_error(message, _("Error"))
        finally:
            self._finish_completion()

    def _complete_manual(self, target: _ManualTarget, output: ConversionOutput) -> None:
        braille = output.display_text
```

```python
            if active.job.export is not None:
                active.job.export.on_error(message)
            else:
                self._view.show_error(self._name_unopened_document(active.job.manual, message), _("Error"))
        finally:
            self._finish_completion()

    def _name_unopened_document(self, target: _ManualTarget, message: str) -> str:
        """``message``, led by the name of the job's document if another one is open now (F-12 D7)."""
        if target.document_name is None or target.document_name == self._documents.open_document_name:
            return message
        return _('Document "{name}" could not be converted.\n\n{error}').format(name=target.document_name, error=message)

    def _complete_manual(self, target: _ManualTarget, output: ConversionOutput) -> None:
        braille = output.display_text
```

Edit: `client/documents/export_coordinator.py`

```python
                    format_key,
                    dual_view_results=output.dual_view_segments,
                ),
                on_error=lambda message: self._view.show_error(message, _("Error")),
            )
            return
        self._write_single(document, destination_path, format_key)

    def _log_unexpected_export_error(self, error: Exception) -> None:
        """Log the traceback of a failed export if it is not an ``OSError`` (F-7).
```

```python
                    format_key,
                    dual_view_results=output.dual_view_segments,
                ),
                on_error=lambda message: self._view.show_error(self._name_unopened_document(document.name, message), _("Error")),
            )
            return
        self._write_single(document, destination_path, format_key)

    def _name_unopened_document(self, name: str, message: str) -> str:
        """``message``, led by ``name`` if that document is not the open one now (F-12 D7).

        The box does not otherwise say which export failed. Export All names each document
        in its summary instead.
        """
        if name == self._documents.open_document_name:
            return message
        return _('Document "{name}" could not be converted.\n\n{error}').format(name=name, error=message)

    def _log_unexpected_export_error(self, error: Exception) -> None:
        """Log the traceback of a failed export if it is not an ``OSError`` (F-7).
```

- [x] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_export_coordinator tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (only the tests that compare with the zh_TW text fail: the new msgids are not in the catalog yet):

```text
FAIL: test_a_failure_after_switching_names_the_document (tests.test_conversion_presenter.ConversionPresenterTest.test_a_failure_after_switching_names_the_docume
AssertionError: Lists differ: [('ti[73 chars]r', 'Document "alpha" could not be converted.\[16 chars]錯誤')] != [('ti[73 chars]r', '無法轉換文件「alpha」。\n\n轉譯失敗：boom',
FAIL: test_a_failed_export_of_a_document_that_is_not_open_names_it (tests.test_export_coordinator.ExportCoordinatorTest.test_a_failed_export_of_a_document_that_
AssertionError: Lists differ: [('show_error', 'Document "beta" could not be converted.\n\n轉譯失敗：boom', '錯誤')] != [('show_error', '無法轉換文件「beta」。\n\n轉譯失敗：boom', '錯
FAIL: test_failed_conversion_of_a_document_that_is_not_open_string_is_translated (tests.test_i18n.TranslationTest.test_failed_conversion_of_a_document_that_is_n
AssertionError: 'Document "{name}" could not be converted.\n\n{error}' != '無法轉換文件「{name}」。\n\n{error}'
Ran 106 tests
FAILED (failures=4)
```

- [x] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected:

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
399 translated messages, 1 fuzzy translation.
#: documents/export_coordinator.py:126 ui/conversion_presenter.py:306
#, fuzzy, python-brace-format
msgid ""
"Document \"{name}\" could not be converted.\n"
"\n"
"{error}"
msgstr "無法讀取字典「{name}」。{reason}"
27
```

- [x] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
msgstr "無法讀取字典「{name}」。"

#: documents/export_coordinator.py:126 ui/conversion_presenter.py:306
#, fuzzy, python-brace-format
msgid ""
"Document \"{name}\" could not be converted.\n"
"\n"
"{error}"
msgstr "無法讀取字典「{name}」。{reason}"

#: documents/export_coordinator.py:145
#, python-brace-format
```

```po
msgstr "無法讀取字典「{name}」。"

#: documents/export_coordinator.py:126 ui/conversion_presenter.py:306
#, python-brace-format
msgid ""
"Document \"{name}\" could not be converted.\n"
"\n"
"{error}"
msgstr ""
"無法轉換文件「{name}」。\n"
"\n"
"{error}"

#: documents/export_coordinator.py:145
#, python-brace-format
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
a second msgmerge changes nothing
msgfmt exit 0
400 translated messages.
0
catalog keys: 401
 1 '匯出完成，但有錯誤'
 2 '所有文件皆已成功匯出。'
 3 '成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}'
 4 '發生不明的錯誤。'
 5 '選取的轉譯表無法轉譯這段文字。'
 6 '(missing)'
 7 '(missing)'
 8 '(missing)'
 9 '(missing)'
10 '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。'
11 '無法匯入這種類型的檔案。'
12 '副檔名與選取的檔案類型不符。'
13 '匯入的檔案必須是有效的 DotExpress DEP 封裝檔。'
14 '這個 PDF 檔已加密，無法匯入。'
15 'EPUB 檔已損壞，或沒有可讀取的內容。'
16 '無法讀取字典「{name}」。{reason}'
17 '無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。'
18 '名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清單中。'
19 '請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n{folder}'
20 '設定未儲存'
21 'DotExpress 無法將設定儲存到「{path}」。設定的變更在關閉 DotExpress 之前有效，但不會保留。在下次啟動 DotExpress 之前，不會再顯示這則訊息。\n\n{reason}'
22 '檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}'
23 '無法轉換文件「{name}」。\n\n{error}'
33661
locales/dotexpress.pot:401
locales/zh_TW/LC_MESSAGES/dotexpress.po:401
27
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 400 sha256 d9e0453c698906cee395641e43763b0686fce14c840a9b1bf9c4d60aeb4d1616
```

- [x] **Step 6: Green: the new tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_export_coordinator tests.test_i18n -v 2>&1 | grep -E "^(test_a_failed_export_of_a_document_that_is_not_open_names_it|test_a_failure_after_switching_away_and_back_is_not_named|test_a_failure_after_switching_names_the_document|test_a_failure_of_the_open_document_is_not_named|test_a_failure_without_a_starting_document_is_not_named|test_failed_conversion_of_a_document_that_is_not_open_string_is_translated) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_export_coordinator tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (each new test once per subTest-free run, in the order unittest runs them):

```text
test_a_failure_after_switching_away_and_back_is_not_named ok
test_a_failure_after_switching_names_the_document ok
test_a_failure_of_the_open_document_is_not_named ok
test_a_failure_without_a_starting_document_is_not_named ok
test_a_failed_export_of_a_document_that_is_not_open_names_it ok
test_failed_conversion_of_a_document_that_is_not_open_string_is_translated ok
Ran 106 tests
OK
Ran 1620 tests
OK (skipped=6)
```

- [x] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_conversion_presenter.py client/tests/test_export_coordinator.py client/tests/test_i18n.py client/ui/conversion_presenter.py client/documents/export_coordinator.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: name the document of a failed conversion that is not open (F-12, F-9 M-9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/documents/export_coordinator.py         |  12 ++++++-
 client/locales/dotexpress.pot                  |  38 ++++++++++++---------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 33551 -> 33661 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po |  44 ++++++++++++++++---------
 client/tests/test_conversion_presenter.py      |  41 +++++++++++++++++++++++
 client/tests/test_export_coordinator.py        |  25 ++++++++++++++
 client/tests/test_i18n.py                      |   9 +++++
 client/ui/conversion_presenter.py              |  11 +++++--
 8 files changed, 146 insertions(+), 34 deletions(-)
b6929558c675a31124b2e1f418db2d2b87a7576a
```

### Task 7: Localize the remaining English messages and drop a misused _() (D8, D9)

- [x] **Step 1: Red: Test Plan C6, H, A (strings 6-9, A2-A4).** `test_user_preprocessing_script.py` (4 spaces): the two errors of the script's contract in zh_TW. `test_conversion_service.py`: through `format_conversion_error`, a `main` that returns `None` and one rebound to a non-callable. `test_dual_view_browser.py`: the browser error in zh_TW. `test_export_coordinator.py`, `test_gui_document_flows.py`: the exported page without conversion data holds `此文件沒有可顯示的轉換資料。` (two characterization tests flip; the `assertNotIn` checks look for the zh sentence, Spec Corrections 11); the title test drops `gui._()`. `test_document_formats.py`: `build_export_wildcard(get_format("html"), _)` gives `HTML 檔 (*.html)|*.html`. `test_i18n.py`: strings 6-9; the three save filters are `N_` calls (A3); `_update_window_title` calls no `_` (A4); the compiled catalog holds exactly the `_()`/`N_()` strings of the client (A2, Spec Corrections 13)**

Edit: `client/tests/test_user_preprocessing_script.py`

```python
            "def main(text):\n    return text\nmain = None\n",
            "def main(text):\n    return 42\n",
        )
        for source in invalid_sources:
            with self.subTest(source=source):
                self.path.write_text(source, encoding="utf-8")
                with self.assertRaises(TypeError):
                    execute_preprocessing_script(self.path, "source")

    def test_execution_rejects_externally_written_invalid_contract(self) -> None:
        self.path.write_text("def main(first, second):\n    return first\n", encoding="utf-8")
```

```python
            "def main(text):\n    return text\nmain = None\n",
            "def main(text):\n    return 42\n",
        )
        # Translated when raised (F-12 D8), as the second one is formatted.
        messages = ("main 不是可以呼叫的函式。", "main 必須傳回 str，而不是 int。")
        for source, message in zip(invalid_sources, messages):
            with self.subTest(source=source):
                self.path.write_text(source, encoding="utf-8")
                with self.assertRaises(TypeError) as raised:
                    execute_preprocessing_script(self.path, "source")

                self.assertEqual(str(raised.exception), message)

    def test_execution_rejects_externally_written_invalid_contract(self) -> None:
        self.path.write_text("def main(first, second):\n    return first\n", encoding="utf-8")
```

Edit: `client/tests/test_conversion_service.py`

```python
    translate_with_language_segments,
)
from translate import TranslationResult


LANG = "zh_TW"
```

```python
    translate_with_language_segments,
)
from translate import TranslationResult
from ui.conversion_presenter import format_conversion_error


LANG = "zh_TW"
```

Edit: `client/tests/test_conversion_service.py`

```python
        self.assertEqual(context.exception.stage, "text_processing")
        self.assertEqual(str(context.exception.error), "script boom")

    def test_math_before_the_first_text_is_translated_before_the_dictionary_error(self) -> None:
        self.dictionary_path.write_text("", encoding="utf-8")
        runtime = self._runtime()
```

```python
        self.assertEqual(context.exception.stage, "text_processing")
        self.assertEqual(str(context.exception.error), "script boom")

    def test_a_script_error_of_the_contract_is_shown_in_zh_tw(self) -> None:
        # F-12 (D8): a main that returns None is the realistic case.
        cases = (
            ("def main(text):\n    return None\n", "文字處理失敗：main 必須傳回 str，而不是 NoneType。"),
            ("def main(text):\n    return text\nmain = 1\n", "文字處理失敗：main 不是可以呼叫的函式。"),
        )
        self.dictionary_path.write_text("text,braille,type\n", encoding="utf-8")
        for source, message in cases:
            with self.subTest(source=source):
                (self.dictionary_dir / "preprocessing.py").write_text(source, encoding="utf-8")

                with self.assertRaises(ConversionStageError) as context:
                    self._convert("abc", self._runtime())

                self.assertEqual(format_conversion_error(context.exception), message)

    def test_math_before_the_first_text_is_translated_before_the_dictionary_error(self) -> None:
        self.dictionary_path.write_text("", encoding="utf-8")
        runtime = self._runtime()
```

Edit: `client/tests/test_dual_view_browser.py`

```python
        startfile.assert_not_called()

    def test_missing_non_windows_fallback_raises_os_error(self) -> None:
        with self.assertRaisesRegex(OSError, "No supported browser"):
            open_html_in_browser(
                Path("/tmp/dual-view-one.html"),
                (900, 600),
```

```python
        startfile.assert_not_called()

    def test_missing_non_windows_fallback_raises_os_error(self) -> None:
        # In zh_TW since F-12 (D8): it follows 無法開啟雙視檢視：.
        with self.assertRaisesRegex(OSError, "^找不到可用的瀏覽器，也沒有可開啟 HTML 檔的系統程式。$"):
            open_html_in_browser(
                Path("/tmp/dual-view-one.html"),
                (900, 600),
```

Edit: `client/tests/test_export_coordinator.py`

```python
                writer.assert_called_once_with(Path("/tmp/alpha.html"), document, ExportContext(dual_view_results=expected))

        self.coordinator.write_document(self.root / "alpha.html", document, "html", dual_view_results=())
        self.assertIn("No conversion data", (self.root / "alpha.html").read_text(encoding="utf-8"))

    def test_write_document_rejects_non_exportable_format(self) -> None:
        descriptor = replace(get_format("txt"), writer=Mock())
```

```python
                writer.assert_called_once_with(Path("/tmp/alpha.html"), document, ExportContext(dual_view_results=expected))

        self.coordinator.write_document(self.root / "alpha.html", document, "html", dual_view_results=())
        # The page's text in zh_TW, as the in-app Dual View shows it (F-12 D8).
        self.assertIn("此文件沒有可顯示的轉換資料。", (self.root / "alpha.html").read_text(encoding="utf-8"))

    def test_write_document_rejects_non_exportable_format(self) -> None:
        descriptor = replace(get_format("txt"), writer=Mock())
```

Edit: `client/tests/test_export_coordinator.py`

```python
        self.assertEqual(self._take(), [self._exported()])
        html = (self.root / "beta.html").read_text(encoding="utf-8")
        self.assertIn('<span class="source">fresh-b</span>', html)
        self.assertNotIn("No conversion data", html)
        self.assertEqual(self.documents.dual_view_results_by_document, {})
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", None))

```

```python
        self.assertEqual(self._take(), [self._exported()])
        html = (self.root / "beta.html").read_text(encoding="utf-8")
        self.assertIn('<span class="source">fresh-b</span>', html)
        self.assertNotIn("此文件沒有可顯示的轉換資料。", html)
        self.assertEqual(self.documents.dual_view_results_by_document, {})
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", None))

```

Edit: `client/tests/test_export_coordinator.py`

```python
            with self.subTest(name=name):
                html = (self.root / f"{name}.html").read_text(encoding="utf-8")
                self.assertIn(f'<span class="source">{source}</span>', html)
                self.assertNotIn("No conversion data", html)
        self.assertEqual(list(self.documents.dual_view_results_by_document), ["alpha"])


```

```python
            with self.subTest(name=name):
                html = (self.root / f"{name}.html").read_text(encoding="utf-8")
                self.assertIn(f'<span class="source">{source}</span>', html)
                self.assertNotIn("此文件沒有可顯示的轉換資料。", html)
        self.assertEqual(list(self.documents.dual_view_results_by_document), ["alpha"])


```

Edit: `client/tests/test_gui_document_flows.py`

```python

# Half of a surrogate pair, as pasting part of an emoji can leave it in an editor (F-5 review M-7).
LONE_SURROGATE = chr(0xD83D)


def make_paths(root: Path = Path("unused-root"), **folders: Path) -> app_paths.ApplicationPaths:
```

```python

# Half of a surrogate pair, as pasting part of an emoji can leave it in an editor (F-5 review M-7).
LONE_SURROGATE = chr(0xD83D)
# The text of an exported Dual View page without conversion data (F-12 D8).
EMPTY_PAGE = "此文件沒有可顯示的轉換資料。"


def make_paths(root: Path = Path("unused-root"), **folders: Path) -> app_paths.ApplicationPaths:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            self.assertIn('<span class="source">a</span>', cached_html)

            frame._export_coordinator.write_document(root / "beta.html", Document("beta", "text", "b"), "html")
            empty_html = render_dual_view_html(build_dual_view_model((), mathml_converter=latex_to_mathml))
            self.assertEqual((root / "beta.html").read_bytes(), text_file_bytes(empty_html))
            self.assertNotEqual(cached_html, empty_html)

```

```python
            self.assertIn('<span class="source">a</span>', cached_html)

            frame._export_coordinator.write_document(root / "beta.html", Document("beta", "text", "b"), "html")
            # The page without conversion data says so in zh_TW (F-12 D8).
            empty_html = render_dual_view_html(build_dual_view_model((), mathml_converter=latex_to_mathml), empty_message=EMPTY_PAGE)
            self.assertEqual((root / "beta.html").read_bytes(), text_file_bytes(empty_html))
            self.assertNotEqual(cached_html, empty_html)

```

Edit: `client/tests/test_gui_document_flows.py`

```python
            )
            self.assertEqual(
                (root / "beta.html").read_text(encoding="utf-8"),
                render_dual_view_html(build_dual_view_model((), mathml_converter=latex_to_mathml)),
            )
        frame.show_info.assert_called_once_with(
            gui._(ExportBatchResult().summary_template),
```

```python
            )
            self.assertEqual(
                (root / "beta.html").read_text(encoding="utf-8"),
                render_dual_view_html(build_dual_view_model((), mathml_converter=latex_to_mathml), empty_message=EMPTY_PAGE),
            )
        frame.show_info.assert_called_once_with(
            gui._(ExportBatchResult().summary_template),
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._take(), [("timer.Stop", 1)] + self._busy(False) + [self._exported(frame)])
        html = target.read_text(encoding="utf-8")
        self.assertIn('<span class="source">fresh-a</span>', html)
        self.assertNotIn("No conversion data", html)
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {})
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "alpha text", None)])
        self.assertEqual(frame.output_txt.value, "")
```

```python
        self.assertEqual(self._take(), [("timer.Stop", 1)] + self._busy(False) + [self._exported(frame)])
        html = target.read_text(encoding="utf-8")
        self.assertIn('<span class="source">fresh-a</span>', html)
        self.assertNotIn("此文件沒有可顯示的轉換資料。", html)
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {})
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "alpha text", None)])
        self.assertEqual(frame.output_txt.value, "")
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            [
                ("set", "input", "beta text"),
                ("set", "output", "⠃"),
                ("title", gui._(gui.format_window_title("beta"))),
                ("dual_view.refresh",),
                ("focus", "input"),
            ],
```

```python
            [
                ("set", "input", "beta text"),
                ("set", "output", "⠃"),
                ("title", gui.format_window_title("beta")),
                ("dual_view.refresh",),
                ("focus", "input"),
            ],
```

Edit: `client/tests/test_document_formats.py`

```python
    get_importable_formats,
)
from documents.workspace import Document
from tests.full_disk import full_disk


```

```python
    get_importable_formats,
)
from documents.workspace import Document
from i18n import _
from tests.full_disk import full_disk


```

Edit: `client/tests/test_document_formats.py`

```python
                self.assertEqual(build_export_wildcard(get_format(key)), wildcard)
                self.assertEqual(build_export_wildcard(get_format(key), lambda value: f"T[{value}]"), f"T[{wildcard}]")

    def test_export_wildcard_rejects_non_exportable_format(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
            build_export_wildcard(get_format("txt"))
```

```python
                self.assertEqual(build_export_wildcard(get_format(key)), wildcard)
                self.assertEqual(build_export_wildcard(get_format(key), lambda value: f"T[{value}]"), f"T[{wildcard}]")

    def test_html_save_filter_is_translated(self) -> None:
        # F-12 (D8): a msgid like the BRL filter; the label HTML stays as it is.
        self.assertEqual(build_export_wildcard(get_format("html"), _), "HTML 檔 (*.html)|*.html")

    def test_export_wildcard_rejects_non_exportable_format(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
            build_export_wildcard(get_format("txt"))
```

Edit: `client/tests/test_i18n.py`

```python
            "無法轉換文件「{name}」。\n\n{error}",
        )

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")

```

```python
            "無法轉換文件「{name}」。\n\n{error}",
        )

    def test_remaining_english_message_strings_are_translated(self) -> None:
        # F-12 (D8): the HTML save filter, the browser error and the text processing script's
        # two errors of its contract.
        expected = {
            "HTML files (*.html)|*.html": "HTML 檔 (*.html)|*.html",
            "No supported browser or system HTML opener is available.": "找不到可用的瀏覽器，也沒有可開啟 HTML 檔的系統程式。",
            "main is not callable.": "main 不是可以呼叫的函式。",
            "main must return str, got {type}.": "main 必須傳回 str，而不是 {type}。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")

```

Edit: `client/tests/test_i18n.py`

```python
            ],
        )

    def test_generate_pot_extracts_n_keyword(self) -> None:
        script = (CLIENT_ROOT.parent / "scripts" / "generate-pot.bat").read_text(encoding="utf-8")

```

```python
            ],
        )

    def test_html_save_filter_is_marked_where_defined(self) -> None:
        # F-12 (D8): build_export_wildcard translates it where it is shown.
        wildcards = {
            keyword.value.args[0].value if isinstance(keyword.value, ast.Call) else ast.unparse(keyword.value): (
                ast.unparse(keyword.value.func) if isinstance(keyword.value, ast.Call) else None
            )
            for node in ast.walk(_module_tree("documents/formats.py"))
            if isinstance(node, ast.Call)
            for keyword in node.keywords
            if keyword.arg == "export_wildcard"
        }

        self.assertEqual(
            wildcards,
            {
                "DotExpress files (*.dep)|*.dep": "N_",
                "Braille files (*.brl)|*.brl": "N_",
                "HTML files (*.html)|*.html": "N_",
            },
        )

    def test_window_title_is_not_passed_to_gettext(self) -> None:
        # F-12 (D9): "alpha - DotExpress" is not a msgid; DotExpress and the name stay as they are.
        method = next(
            node
            for node in ast.walk(_module_tree("gui.py"))
            if isinstance(node, ast.FunctionDef) and node.name == "_update_window_title"
        )
        calls = sorted(ast.unparse(node.func) for node in ast.walk(method) if isinstance(node, ast.Call))

        self.assertEqual(calls, ["format_window_title", "self.SetTitle"])

    def test_the_catalog_holds_exactly_the_marked_strings(self) -> None:
        # F-12 (Test Plan A2): every _() and N_() string of the client is a catalog entry, and the
        # compiled catalog holds no other.
        marked = set()
        for dirpath, dirnames, filenames in os.walk(CLIENT_ROOT):
            dirnames[:] = sorted(name for name in dirnames if name not in {"tests", ".venv", "__pycache__", "build", "dist"})
            if Path(dirpath).relative_to(CLIENT_ROOT).parts[:2] == ("braille", "liblouis"):
                continue
            for filename in sorted(filenames):
                if not filename.endswith(".py"):
                    continue
                path = Path(dirpath) / filename
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id in {"_", "N_"}
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                    ):
                        marked.add(node.args[0].value)
        catalog = set(i18n.load_translation()._catalog) - {""}

        self.assertEqual(sorted(marked - catalog), [])
        self.assertEqual(sorted(catalog - marked), [])

    def test_generate_pot_extracts_n_keyword(self) -> None:
        script = (CLIENT_ROOT.parent / "scripts" / "generate-pot.bat").read_text(encoding="utf-8")

```

```bash
$PY -B -X utf8 -m unittest tests.test_user_preprocessing_script tests.test_conversion_service tests.test_dual_view_browser tests.test_export_coordinator tests.test_gui_document_flows tests.test_document_formats tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
FAIL: test_execution_rejects_non_callable_main_and_non_string_return (tests.test_user_preprocessing_script.UserPreprocessingScriptTest.test_execution_rejects_no
AssertionError: 'main is not callable.' != 'main 不是可以呼叫的函式。'
AssertionError: 'main must return str, got int.' != 'main 必須傳回 str，而不是 int。'
FAIL: test_a_script_error_of_the_contract_is_shown_in_zh_tw (tests.test_conversion_service.DictionaryErrorTimingTest.test_a_script_error_of_the_contract_is_show
AssertionError: '文字處理失敗：main must return str, got NoneType.' != '文字處理失敗：main 必須傳回 str，而不是 NoneType。'
AssertionError: '文字處理失敗：main is not callable.' != '文字處理失敗：main 不是可以呼叫的函式。'
FAIL: test_missing_non_windows_fallback_raises_os_error (tests.test_dual_view_browser.DualViewBrowserTest.test_missing_non_windows_fallback_raises_os_error)
OSError: No supported browser or system HTML opener is available.
AssertionError: "^找不到可用的瀏覽器，也沒有可開啟 HTML 檔的系統程式。$" does not match "No supported browser or system HTML opener is available."
FAIL: test_write_document_uses_the_given_results_instead_of_the_cache (tests.test_export_coordinator.ExportCoordinatorTest.test_write_document_uses_the_given_re
AssertionError: '此文件沒有可顯示的轉換資料。' not found in '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-wi
FAIL: test_export_all_html_uses_each_document_cache (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_export_all_html_uses_each_docu
AssertionError: '<!do[1161 chars]ate">No conversion data is available for this [32 chars]tml>' != '<!do[1161 chars]ate">此文件沒有可顯示的轉換資料。</p></main></body>\n</html
FAIL: test_real_writers_produce_today_bytes (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_real_writers_produce_today_bytes)
AssertionError: b'<!d[1210 chars]ate">No conversion data is available for this [34 chars]tml>' != b'<!d[1210 chars]ate">\xe6\xad\xa4\xe6\x96\x87\xe4\xbb\xb6\xe6
FAIL: test_html_save_filter_is_translated (tests.test_document_formats.DocumentFormatsTest.test_html_save_filter_is_translated)
AssertionError: 'HTML files (*.html)|*.html' != 'HTML 檔 (*.html)|*.html'
FAIL: test_html_save_filter_is_marked_where_defined (tests.test_i18n.ExtractionMarkerTest.test_html_save_filter_is_marked_where_defined)
AssertionError: {'Dot[47 chars]les (*.brl)|*.brl': 'N_', "'HTML files (*.html)|*.html'": None} != {'Dot[47 chars]les (*.brl)|*.brl': 'N_', 'HTML files (*.html)|
FAIL: test_window_title_is_not_passed_to_gettext (tests.test_i18n.ExtractionMarkerTest.test_window_title_is_not_passed_to_gettext)
AssertionError: Lists differ: ['_', 'format_window_title', 'self.SetTitle'] != ['format_window_title', 'self.SetTitle']
FAIL: test_remaining_english_message_strings_are_translated (tests.test_i18n.TranslationTest.test_remaining_english_message_strings_are_translated)
AssertionError: {'HTM[27 chars]HTML files (*.html)|*.html', 'No supported bro[221 chars]e}.'} != {'HTM[27 chars]HTML 檔 (*.html)|*.html', 'No supported browser[1
Ran 362 tests
FAILED (failures=12)
```

- [x] **Step 2: Green: D8 and D9** (`client/documents/formats.py`, `client/dual_view/browser.py`, `client/conversion/preprocessing/user_script.py`, 4 spaces; `client/gui.py`, tabs). The script's two errors are translated when raised, as the second one is formatted.**

Edit: `client/documents/formats.py`

```python
from conversion.math_service import latex_to_mathml
from dual_view.html import render_dual_view_html
from dual_view.model import build_dual_view_model
from i18n import N_

if TYPE_CHECKING:
    from documents.importers import ImportedDocument
```

```python
from conversion.math_service import latex_to_mathml
from dual_view.html import render_dual_view_html
from dual_view.model import build_dual_view_model
from i18n import N_, _

if TYPE_CHECKING:
    from documents.importers import ImportedDocument
```

Edit: `client/documents/formats.py`

```python
    from documents.workspace import write_export_text

    destination = Path(path)
    html = render_dual_view_html(build_dual_view_model(context.dual_view_results, mathml_converter=latex_to_mathml))
    write_export_text(destination, html)
    return destination

```

```python
    from documents.workspace import write_export_text

    destination = Path(path)
    html = render_dual_view_html(
        build_dual_view_model(context.dual_view_results, mathml_converter=latex_to_mathml),
        # As the in-app Dual View shows it (F-12 D8).
        empty_message=_("No conversion data is available for this document."),
    )
    write_export_text(destination, html)
    return destination

```

Edit: `client/documents/formats.py`

```python
        export_wildcard=N_("Braille files (*.brl)|*.brl"),
        export_label=N_("Braille BRL"),
    ),
    # "HTML" and the HTML save filter are not msgids; marking them would add new catalog entries.
    DocumentFormatDescriptor(
        key="html",
        extension=HTML_EXTENSION,
```

```python
        export_wildcard=N_("Braille files (*.brl)|*.brl"),
        export_label=N_("Braille BRL"),
    ),
    # "HTML" is not a msgid: the label stays as it is, like ASCII and Unicode. The save filter is (F-12 D8).
    DocumentFormatDescriptor(
        key="html",
        extension=HTML_EXTENSION,
```

Edit: `client/documents/formats.py`

```python
        requires_braille=False,
        importable=False,
        exportable=True,
        export_wildcard="HTML files (*.html)|*.html",
        export_label=N_("Dual View HTML"),
    ),
)
```

```python
        requires_braille=False,
        importable=False,
        exportable=True,
        export_wildcard=N_("HTML files (*.html)|*.html"),
        export_label=N_("Dual View HTML"),
    ),
)
```

Edit: `client/dual_view/browser.py`

```python
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
```

```python
from pathlib import Path
import shutil
import subprocess

from i18n import _


@dataclass(frozen=True)
```

Edit: `client/dual_view/browser.py`

```python

    fallback = getattr(os, "startfile", None) if startfile is _DEFAULT_STARTFILE else startfile
    if fallback is None:
        raise OSError("No supported browser or system HTML opener is available.")
    fallback(str(html_path.resolve()))
    return "system"
```

```python

    fallback = getattr(os, "startfile", None) if startfile is _DEFAULT_STARTFILE else startfile
    if fallback is None:
        raise OSError(_("No supported browser or system HTML opener is available."))
    fallback(str(html_path.resolve()))
    return "system"
```

Edit: `client/conversion/preprocessing/user_script.py`

```python
import ast
from pathlib import Path

from i18n import N_
from shared.atomic_write import write_text_atomically


```

```python
import ast
from pathlib import Path

from i18n import N_, _
from shared.atomic_write import write_text_atomically


```

Edit: `client/conversion/preprocessing/user_script.py`

```python
    }
    exec(compile(source, str(source_path), "exec"), namespace)
    main = namespace.get("main")
    if not callable(main):
        raise TypeError("main is not callable.")
    output = main(input_text)
    if not isinstance(output, str):
        raise TypeError(f"main must return str, got {type(output).__name__}.")
    return output
```

```python
    }
    exec(compile(source, str(source_path), "exec"), namespace)
    main = namespace.get("main")
    # Translated when raised, as the second one is formatted (F-12 D8).
    if not callable(main):
        raise TypeError(_("main is not callable."))
    output = main(input_text)
    if not isinstance(output, str):
        raise TypeError(_("main must return str, got {type}.").format(type=type(output).__name__))
    return output
```

Edit: `client/gui.py`

```python
		apply_document_menu_state(target_items, menu_state)

	def _update_window_title(self) -> None:
		self.SetTitle(_(format_window_title(self._document_controller.open_document_name)))

	def _create_dual_view_frame(self) -> DualViewFrame:
		return DualViewFrame(self, title=_("Dual View"), on_closed=self._on_dual_view_closed)
```

```python
		apply_document_menu_state(target_items, menu_state)

	def _update_window_title(self) -> None:
		# Not a msgid: DotExpress and the document name stay as they are (F-12 D9).
		self.SetTitle(format_window_title(self._document_controller.open_document_name))

	def _create_dual_view_frame(self) -> DualViewFrame:
		return DualViewFrame(self, title=_("Dual View"), on_closed=self._on_dual_view_closed)
```

- [x] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_user_preprocessing_script tests.test_conversion_service tests.test_dual_view_browser tests.test_export_coordinator tests.test_gui_document_flows tests.test_document_formats tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (only the tests that compare with the zh_TW text fail: the new msgids are not in the catalog yet):

```text
FAIL: test_execution_rejects_non_callable_main_and_non_string_return (tests.test_user_preprocessing_script.UserPreprocessingScriptTest.test_execution_rejects_no
AssertionError: 'main is not callable.' != 'main 不是可以呼叫的函式。'
AssertionError: 'main must return str, got int.' != 'main 必須傳回 str，而不是 int。'
FAIL: test_a_script_error_of_the_contract_is_shown_in_zh_tw (tests.test_conversion_service.DictionaryErrorTimingTest.test_a_script_error_of_the_contract_is_show
AssertionError: '文字處理失敗：main must return str, got NoneType.' != '文字處理失敗：main 必須傳回 str，而不是 NoneType。'
AssertionError: '文字處理失敗：main is not callable.' != '文字處理失敗：main 不是可以呼叫的函式。'
FAIL: test_missing_non_windows_fallback_raises_os_error (tests.test_dual_view_browser.DualViewBrowserTest.test_missing_non_windows_fallback_raises_os_error)
OSError: No supported browser or system HTML opener is available.
AssertionError: "^找不到可用的瀏覽器，也沒有可開啟 HTML 檔的系統程式。$" does not match "No supported browser or system HTML opener is available."
FAIL: test_html_save_filter_is_translated (tests.test_document_formats.DocumentFormatsTest.test_html_save_filter_is_translated)
AssertionError: 'HTML files (*.html)|*.html' != 'HTML 檔 (*.html)|*.html'
FAIL: test_the_catalog_holds_exactly_the_marked_strings (tests.test_i18n.ExtractionMarkerTest.test_the_catalog_holds_exactly_the_marked_strings)
AssertionError: Lists differ: ['HTML files (*.html)|*.html', 'No support[105 chars]e}.'] != []
FAIL: test_remaining_english_message_strings_are_translated (tests.test_i18n.TranslationTest.test_remaining_english_message_strings_are_translated)
AssertionError: {'HTM[27 chars]HTML files (*.html)|*.html', 'No supported bro[221 chars]e}.'} != {'HTM[27 chars]HTML 檔 (*.html)|*.html', 'No supported browser[1
Ran 362 tests
FAILED (failures=8)
```

- [x] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected:

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
400 translated messages, 1 fuzzy translation, 3 untranslated messages.
#: documents/formats.py:193
#, fuzzy
msgid "HTML files (*.html)|*.html"
msgstr "文字檔 (*.txt)|*.txt"
#: conversion/preprocessing/user_script.py:76
msgid "main is not callable."
msgstr ""

#: conversion/preprocessing/user_script.py:79
#, python-brace-format
msgid "main must return str, got {type}."
msgstr ""

#: dual_view/browser.py:105
msgid "No supported browser or system HTML opener is available."
msgstr ""
26
```

- [x] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po

#: conversion/preprocessing/user_script.py:76
msgid "main is not callable."
msgstr ""

#: conversion/preprocessing/user_script.py:79
#, python-brace-format
msgid "main must return str, got {type}."
msgstr ""

#: dialog.py:33
msgid "CSV files (*.csv)|*.csv"
```

```po

#: conversion/preprocessing/user_script.py:76
msgid "main is not callable."
msgstr "main 不是可以呼叫的函式。"

#: conversion/preprocessing/user_script.py:79
#, python-brace-format
msgid "main must return str, got {type}."
msgstr "main 必須傳回 str，而不是 {type}。"

#: dialog.py:33
msgid "CSV files (*.csv)|*.csv"
```

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
msgstr "點字檔 BRL"

#: documents/formats.py:193
#, fuzzy
msgid "HTML files (*.html)|*.html"
msgstr "文字檔 (*.txt)|*.txt"

#: documents/formats.py:194
msgid "Dual View HTML"
```

```po
msgstr "點字檔 BRL"

#: documents/formats.py:193
msgid "HTML files (*.html)|*.html"
msgstr "HTML 檔 (*.html)|*.html"

#: documents/formats.py:194
msgid "Dual View HTML"
```

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po

#: dual_view/browser.py:105
msgid "No supported browser or system HTML opener is available."
msgstr ""

#: gui.py:184
msgid "Documents"
```

```po

#: dual_view/browser.py:105
msgid "No supported browser or system HTML opener is available."
msgstr "找不到可用的瀏覽器，也沒有可開啟 HTML 檔的系統程式。"

#: gui.py:184
msgid "Documents"
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
a second msgmerge changes nothing
msgfmt exit 0
404 translated messages.
0
catalog keys: 405
 1 '匯出完成，但有錯誤'
 2 '所有文件皆已成功匯出。'
 3 '成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}'
 4 '發生不明的錯誤。'
 5 '選取的轉譯表無法轉譯這段文字。'
 6 'HTML 檔 (*.html)|*.html'
 7 '找不到可用的瀏覽器，也沒有可開啟 HTML 檔的系統程式。'
 8 'main 不是可以呼叫的函式。'
 9 'main 必須傳回 str，而不是 {type}。'
10 '檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。'
11 '無法匯入這種類型的檔案。'
12 '副檔名與選取的檔案類型不符。'
13 '匯入的檔案必須是有效的 DotExpress DEP 封裝檔。'
14 '這個 PDF 檔已加密，無法匯入。'
15 'EPUB 檔已損壞，或沒有可讀取的內容。'
16 '無法讀取字典「{name}」。{reason}'
17 '無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。'
18 '名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清單中。'
19 '請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n{folder}'
20 '設定未儲存'
21 'DotExpress 無法將設定儲存到「{path}」。設定的變更在關閉 DotExpress 之前有效，但不會保留。在下次啟動 DotExpress 之前，不會再顯示這則訊息。\n\n{reason}'
22 '檔案已損壞，而且在取代它之前無法先備份為「{backup}」。詳細資訊：{error}'
23 '無法轉換文件「{name}」。\n\n{error}'
34046
locales/dotexpress.pot:405
locales/zh_TW/LC_MESSAGES/dotexpress.po:405
26
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 404 sha256 ad00d55f0a0da6a34e9676798b47ac1dfeb2d3ea7cadf1e5a53137265ce04d9b
```

- [x] **Step 6: Green: the new tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_user_preprocessing_script tests.test_conversion_service tests.test_dual_view_browser tests.test_export_coordinator tests.test_gui_document_flows tests.test_document_formats tests.test_i18n -v 2>&1 | grep -E "^(test_a_script_error_of_the_contract_is_shown_in_zh_tw|test_html_save_filter_is_marked_where_defined|test_html_save_filter_is_translated|test_remaining_english_message_strings_are_translated|test_the_catalog_holds_exactly_the_marked_strings|test_window_title_is_not_passed_to_gettext) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_user_preprocessing_script tests.test_conversion_service tests.test_dual_view_browser tests.test_export_coordinator tests.test_gui_document_flows tests.test_document_formats tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (each new test once per subTest-free run, in the order unittest runs them):

```text
test_a_script_error_of_the_contract_is_shown_in_zh_tw ok
test_html_save_filter_is_translated ok
test_html_save_filter_is_marked_where_defined ok
test_the_catalog_holds_exactly_the_marked_strings ok
test_window_title_is_not_passed_to_gettext ok
test_remaining_english_message_strings_are_translated ok
Ran 362 tests
OK
Ran 1626 tests
OK (skipped=6)
```

- [x] **Step 7: Commit.**

```bash
git -C $REPO add client/tests/test_user_preprocessing_script.py client/tests/test_conversion_service.py client/tests/test_dual_view_browser.py client/tests/test_export_coordinator.py client/tests/test_gui_document_flows.py client/tests/test_document_formats.py client/tests/test_i18n.py client/documents/formats.py client/dual_view/browser.py client/conversion/preprocessing/user_script.py client/gui.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: localize the remaining English messages and drop a misused _() (F-12)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/conversion/preprocessing/user_script.py |   7 +-
 client/documents/formats.py                    |  12 ++-
 client/dual_view/browser.py                    |   4 +-
 client/gui.py                                  |   3 +-
 client/locales/dotexpress.pot                  | 135 +++++++++++++-----------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 33661 -> 34046 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 138 ++++++++++++++-----------
 client/tests/test_conversion_service.py        |  17 +++
 client/tests/test_document_formats.py          |   5 +
 client/tests/test_dual_view_browser.py         |   3 +-
 client/tests/test_export_coordinator.py        |   7 +-
 client/tests/test_gui_document_flows.py        |  11 +-
 client/tests/test_i18n.py                      |  72 +++++++++++++
 client/tests/test_user_preprocessing_script.py |   8 +-
 14 files changed, 282 insertions(+), 140 deletions(-)
9a5516a5f74312816fbae4ae2f8b7e2f75c210ef
```
### Task 8: Open the default document after a Delete All rollback without a valid document (P1-3 defect 4; added to F-12 by the user)

- [x] **Step 1: Red: the P1-3 defect 4 pin flipped.** `test_gui_document_flows.py` (4 spaces): `test_delete_all_failure_without_valid_document_clears_editors_only` becomes `test_delete_all_failure_without_valid_document_opens_the_default_document`: after the error box and the invalid-files dialog, the title `DotExpress`, then `new - DotExpress`, the focus in the source editor, `new.dep` written; a new test holds `new` on disk (a folder) and expects `new (2)` (F-8's free-name rule); the delegation test `test_delete_all_failure_reviews_paths_from_service` expects `_update_window_title` and `_ensure_open_document_exists` around `_clear_document_editors`.

Edit: `client/tests/test_gui_document_flows.py`

```python
            frame.on_delete_all_documents(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
        self.assertEqual(
            frame.ui.mock_calls,
            [
                call._refresh_document_list(),
                call._review_invalid_workspace_files(invalid_paths),
                call._clear_document_editors(),
                call._refresh_dual_view(),
            ],
        )
```

```python
            frame.on_delete_all_documents(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
        # No valid document is left: as after a complete Delete All, the title follows and the
        # default document is opened (F-12, P1-3 defect 4).
        self.assertEqual(
            frame.ui.mock_calls,
            [
                call._refresh_document_list(),
                call._review_invalid_workspace_files(invalid_paths),
                call._update_window_title(),
                call._clear_document_editors(),
                call._ensure_open_document_exists(),
                call._refresh_dual_view(),
            ],
        )
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._state(frame), ([documents[2]], "gamma", "gamma", {"gamma": ("seg-c",)}))
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("c", "3"))

    def test_delete_all_failure_without_valid_document_clears_editors_only(self) -> None:
        # KNOWN BUG (P1-3 spec, known defect 4), pinned as it is today, NOT desired
        # behavior: the rollback leaves no valid document, so only the editors are
        # cleared (no title update, no default document). A later fix task flips this.
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        self._write_packages(documents[0])
        self._block("beta")
```

```python
        self.assertEqual(self._state(frame), ([documents[2]], "gamma", "gamma", {"gamma": ("seg-c",)}))
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("c", "3"))

    def test_delete_all_failure_without_valid_document_opens_the_default_document(self) -> None:
        # Was the KNOWN BUG of P1-3 known defect 4 (the rollback left no valid document, and
        # only the editors were cleared: the title kept the deleted name, no document was
        # open), fixed by F-12: as after a complete Delete All, the title follows and the
        # default document is created and opened.
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        self._write_packages(documents[0])
        self._block("beta")
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        frame.on_delete_all_documents(None)

        self.assertEqual(len(self.events), 3)
        self._assert_error_box(self.events[1], "Failed to delete document: {error}", "beta.dep", frame)
        self.assertEqual(self.events[2], ("InvalidWorkspaceFilesDialog", [self.workspace / "beta.dep"]))
        self.assertEqual(self._listing(), ["beta.dep"])
        self.assertEqual(self._state(frame), ([], None, None, {}))
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("", ""))

    def test_delete_all_without_documents_does_nothing(self) -> None:
        frame = self._make_workspace_frame()
```

```python

        frame.on_delete_all_documents(None)

        self.assertEqual(len(self.events), 6)
        self._assert_error_box(self.events[1], "Failed to delete document: {error}", "beta.dep", frame)
        self.assertEqual(
            self.events[2:],
            [
                ("InvalidWorkspaceFilesDialog", [self.workspace / "beta.dep"]),
                ("title", "DotExpress"),
                ("title", "new - DotExpress"),
                ("focus", "input"),
            ],
        )
        self.assertEqual(self._listing(), ["beta.dep", "new.dep"])
        self.assertEqual(self._state(frame), ([Document("new", "", None)], "new", "new", {}))
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("", ""))

    def test_delete_all_failure_with_new_held_on_disk_opens_a_free_default_name(self) -> None:
        # F-12 (P1-3 defect 4): the default document follows F-8's free-name rule, so a
        # package on disk named new is not replaced.
        documents = [Document("alpha", "a", "1"), Document("new", "b", "2")]
        self._write_packages(documents[0])
        self._block("new")
        frame = self._make_workspace_frame(documents, open_name="alpha", selected_name="alpha")
        self.answers = [gui.wx.YES]

        frame.on_delete_all_documents(None)

        self.assertEqual(self.events[3:], [("title", "DotExpress"), ("title", "new (2) - DotExpress"), ("focus", "input")])
        self.assertEqual(self._listing(), ["new (2).dep", "new.dep"])
        self.assertEqual(self._state(frame), ([Document("new (2)", "", None)], "new (2)", "new (2)", {}))

    def test_delete_all_without_documents_does_nothing(self) -> None:
        frame = self._make_workspace_frame()
```

```bash
$PY -B -X utf8 -m unittest tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (no title, no default document; the delegation test misses the two calls):

```text
FAIL: test_delete_all_failure_with_new_held_on_disk_opens_a_free_default_name (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_del
AssertionError: Lists differ: [] != [('title', 'DotExpress'), ('title', 'new (2) - DotExpress'), ('focus', 'input')]
FAIL: test_delete_all_failure_without_valid_document_opens_the_default_document (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_d
AssertionError: 3 != 6
FAIL: test_delete_all_failure_reviews_paths_from_service (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_delete_all_failure_reviews_path
AssertionError: [call[21 chars]st(),
Ran 224 tests
FAILED (failures=3)
```

- [x] **Step 2: Green: do what a complete Delete All does** (`client/gui.py`, tabs): in `on_delete_all_documents`, when the rollback leaves no valid document, `_update_window_title()`, `_clear_document_editors()` and `_ensure_open_document_exists()`, in the order of the success path.

Edit: `client/gui.py`

```python
			if self._document_controller.has_documents:
				self._open_document_by_name(self._document_controller.first_document_name)
			else:
				self._clear_document_editors()
			self._refresh_dual_view()
			return
		self._update_window_title()
```

```python
			if self._document_controller.has_documents:
				self._open_document_by_name(self._document_controller.first_document_name)
			else:
				# No valid document is left: as after a complete Delete All, the title follows
				# and the default document is created and opened (F-12, P1-3 defect 4).
				self._update_window_title()
				self._clear_document_editors()
				self._ensure_open_document_exists()
			self._refresh_dual_view()
			return
		self._update_window_title()
```

- [x] **Step 3: Regenerate the catalogs** (no new string; the `#:` references of `gui.py` move by four lines, so the template and the `.po` are regenerated as in the earlier tasks; the `.mo` does not change).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
git -C $REPO diff --stat -- client/locales
git -C $REPO diff -- client/locales | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -cvE '^[-+]#: '
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (only `#:` lines change; the `.mo` keeps its bytes, so it is not in the diff):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
a second msgmerge changes nothing
msgfmt exit 0
404 translated messages.
 client/locales/dotexpress.pot                  | 28 +++++++++++++-------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 28 +++++++++++++-------------
 2 files changed, 28 insertions(+), 28 deletions(-)
0
source msgids: 404 sha256 ad00d55f0a0da6a34e9676798b47ac1dfeb2d3ea7cadf1e5a53137265ce04d9b
```

- [x] **Step 4: Green: the changed tests, the module, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_gui_document_flows -v 2>&1 | grep -E "^(test_delete_all_failure_without_valid_document_opens_the_default_document|test_delete_all_failure_with_new_held_on_disk_opens_a_free_default_name|test_delete_all_failure_reviews_paths_from_service) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
grep -rn "KNOWN BUG (P1-3 spec, known defect 4)" tests | wc -l
```

Expected:

```text
test_delete_all_failure_with_new_held_on_disk_opens_a_free_default_name ok
test_delete_all_failure_without_valid_document_opens_the_default_document ok
test_delete_all_failure_reviews_paths_from_service ok
Ran 224 tests
OK
Ran 1627 tests
OK (skipped=6)
0
```

- [x] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/test_gui_document_flows.py client/gui.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: open the default document after a Delete All rollback without a valid document (F-12, P1-3 defect 4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/gui.py                                  |  4 +++
 client/locales/dotexpress.pot                  | 28 ++++++++--------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 28 ++++++++--------
 client/tests/test_gui_document_flows.py        | 44 +++++++++++++++++++++-----
 4 files changed, 68 insertions(+), 36 deletions(-)
62325f9a05b0cd0a1af9344cd078e417c09910d1
```

### Task 9: Compare the vendored helper snapshot with LF line ends (F-W5; added to F-12 by the user)

`scripts/tests` runs from the repository root: `$PY -B -X utf8 -m unittest discover -s scripts/tests -t .`. `test_vendor_helper_snapshot` needs `include/nvda/source/louisHelper.py`, which a worktree or clone without the `include/nvda` submodule lacks (the test is then skipped); Task 0 Step 2 copies that one file from the main checkout (never staged; git does not list files inside a submodule path that is not initialized). The other tests of `scripts/tests` need the full `include/liblouis` and `include/nvda` submodules, which a worktree does not have: there they raise `FileNotFoundError` before and after this task (13 errors); in the main checkout, which has the submodules, `results.md` of the 2026-10-09-03 Windows verification records `Ran 33`, `failures=1` (F-W5 only).

- [x] **Step 1: Red: the snapshot test as it is.** It reads the snapshot with `read_bytes().decode()`; the snapshot is LF in the repository and CRLF in a Windows working tree (`core.autocrlf=true`), while the expected text, read with `read_text`, has LF.

```bash
cd $REPO
$PY -B -X utf8 -m unittest scripts.tests.test_vendor_helper_snapshot 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s scripts/tests -t . 2>&1 | $PY $T/tools/brief.py | tail -2
```

Expected (the only failure is the snapshot's: `\n` against `\r\n`):

```text
FAIL: test_runtime_helper_snapshot_is_the_adapted_nvda_helper (scripts.tests.test_vendor_helper_snapshot.VendorHelperSnapshotTests.test_runtime_helper_snapshot_
AssertionError: '# A [35 chars]VDA)\n# This file is covered by the GNU Genera[7021 chars]ne\n' != '# A [35 chars]VDA)\r\n# This file is covered by the GNU Gene[
Ran 1 test
FAILED (failures=1)
Ran 33 tests
FAILED (failures=1, errors=13)
```

- [x] **Step 2: Green: compare with LF line ends** (`scripts/tests/test_vendor_helper_snapshot.py`, 4 spaces). The vendored file and `.gitattributes` are not changed: a `.gitattributes` rule would only take effect for files checked out again, and would change the bytes of the user's working tree.

Edit: `scripts/tests/test_vendor_helper_snapshot.py`

```python
class VendorHelperSnapshotTests(unittest.TestCase):
    def test_runtime_helper_snapshot_is_the_adapted_nvda_helper(self):
        expected = _load_sync_nvda()._adapt_helper(NVDA_HELPER.read_text(encoding="utf-8"))

        self.assertEqual(
            expected,
            RUNTIME_HELPER.read_bytes().decode("utf-8"),
            "regenerate vendor/nvda/liblouis/runtime/louis_helper.py with _adapt_helper",
        )

```

```python
class VendorHelperSnapshotTests(unittest.TestCase):
    def test_runtime_helper_snapshot_is_the_adapted_nvda_helper(self):
        expected = _load_sync_nvda()._adapt_helper(NVDA_HELPER.read_text(encoding="utf-8"))
        # Compared with LF line ends: the snapshot is LF in the repository, and core.autocrlf
        # checks it out with CRLF on Windows (F-W5, fixed in F-12). The vendored file is not
        # changed.
        actual = RUNTIME_HELPER.read_bytes().decode("utf-8").replace("\r\n", "\n")

        self.assertEqual(
            expected,
            actual,
            "regenerate vendor/nvda/liblouis/runtime/louis_helper.py with _adapt_helper",
        )

```

```bash
cd $REPO
$PY -B -X utf8 -m unittest scripts.tests.test_vendor_helper_snapshot 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s scripts/tests -t . 2>&1 | $PY $T/tools/brief.py | tail -2
git -C $REPO diff --quiet -- vendor && echo "vendor unchanged"
```

Expected:

```text
Ran 1 test
OK
Ran 33 tests
FAILED (errors=13)
vendor unchanged
```

- [x] **Step 3: Commit** (no file under `client/`: the client tree stays Task 8's).

```bash
git -C $REPO add scripts/tests/test_vendor_helper_snapshot.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "test: compare the vendored helper snapshot with LF line ends (F-12, F-W5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client HEAD:scripts
git -C $REPO status --short -- client scripts
```

Expected:

```text
 scripts/tests/test_vendor_helper_snapshot.py | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
62325f9a05b0cd0a1af9344cd078e417c09910d1
6a2bd0cb0ea886626e676bd69458b9939bd2462e
```

### Task 10: Verification (no commit)

`BASE` is `main` at `e0337df`.

- [x] **Step 1: Criterion 1, full suite.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = 1567 + 60; no failure and no error):

```text
Ran 1627 tests
OK (skipped=6)
```

- [x] **Step 2: Criterion 2, focused modules; the F-12 tests ran and passed; two orders of three modules.** The verbose run is kept in `$T/verbose.txt`, so a failure there is named.

```bash
$PY -B -X utf8 -m unittest tests.test_i18n tests.test_export_coordinator tests.test_conversion_presenter tests.test_conversion_text_dictionary_rules tests.test_import_problems tests.test_workspace_service tests.test_config tests.test_gui_document_flows tests.test_document_workspace tests.test_conversion_service tests.test_translation_settings tests.test_translation_tables tests.test_view_settings tests.test_document_formats tests.test_dual_view_browser tests.test_user_preprocessing_script 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_config tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_i18n tests.test_gui_document_flows tests.test_config 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_i18n tests.test_export_coordinator tests.test_conversion_presenter tests.test_conversion_text_dictionary_rules tests.test_import_problems tests.test_workspace_service tests.test_config tests.test_gui_document_flows tests.test_document_workspace tests.test_conversion_service tests.test_translation_settings tests.test_translation_tables tests.test_view_settings tests.test_document_formats tests.test_dual_view_browser tests.test_user_preprocessing_script -v > $T/verbose.txt 2>&1; grep -cE "^(test_a_damaged_file_whose_backup_fails_is_backup_failed|test_a_dictionary_that_cannot_be_opened_raises_the_read_error|test_a_dictionary_that_cannot_be_read_raises_the_read_error|test_a_failed_export_of_a_document_that_is_not_open_names_it|test_a_failure_after_switching_away_and_back_is_not_named|test_a_failure_after_switching_names_the_document|test_a_failure_of_the_open_document_is_not_named|test_a_failure_without_a_starting_document_is_not_named|test_a_file_name_that_is_not_a_document_name|test_a_file_that_cannot_be_opened|test_a_file_that_cannot_be_read_is_unreadable|test_a_listed_duplicate_keeps_its_message_before_any_entry_on_disk|test_a_script_error_of_the_contract_is_shown_in_zh_tw|test_a_settings_change_that_cannot_be_saved_shows_one_box_and_still_applies|test_a_text_file_that_is_not_utf8|test_a_write_that_fails_is_write_failed|test_add_of_a_name_held_by_a_folder_names_the_folder|test_add_of_another_case_of_an_unlisted_name_names_the_entry_on_disk|test_an_encrypted_pdf|test_an_epub_without_readable_content|test_an_error_while_processing_the_rows_is_not_wrapped|test_any_other_error_reading_a_package|test_any_other_error_shows_its_own_text|test_batch_import_documents_explains_each_skipped_file|test_batch_import_documents_names_the_file_that_holds_a_name_on_disk|test_delete_all_failure_with_new_held_on_disk_opens_a_free_default_name|test_delete_all_failure_without_valid_document_opens_the_default_document|test_each_kind_of_problem_gives_its_reason|test_every_setter_returns_none_when_the_save_works|test_export_failure_names_a_dictionary_that_cannot_be_read|test_export_summary_and_conversion_fallback_strings_are_translated|test_export_summary_and_conversion_fallback_texts_are_marked_where_defined|test_failed_conversion_of_a_document_that_is_not_open_string_is_translated|test_font_size_and_dictionary_changes_report_through_the_same_flag|test_format_conversion_error_names_a_dictionary_that_cannot_be_read|test_html_save_filter_is_marked_where_defined|test_html_save_filter_is_translated|test_import_issues_explain_each_skipped_file|test_import_of_a_name_held_by_an_unlisted_package_names_the_file|test_import_problem_is_a_value_error_that_keeps_its_english_text|test_import_problem_strings_are_translated|test_load_workspace_documents_counts_a_package_the_loader_refuses_as_invalid|test_manual_failure_names_a_dictionary_that_cannot_be_read|test_module_imports_neither_wx_nor_dictionaries|test_no_box_when_the_settings_are_saved|test_remaining_english_message_strings_are_translated|test_save_calls_every_setter_and_returns_the_first_problem|test_save_returns_none_when_every_setter_saves|test_save_returns_what_the_store_returns|test_settings_not_saved_strings_are_translated|test_the_box_belongs_to_the_active_window|test_the_bundled_bopomofo_file_is_not_wrapped|test_the_catalog_holds_exactly_the_marked_strings|test_the_client_id_and_the_language_ignore_a_failed_save|test_the_problems_of_the_loaders_show_their_reason|test_unlisted_entry_strings_are_translated|test_unlisted_package_entry_falls_back_to_the_package_name|test_unlisted_package_entry_names_what_holds_a_name_on_disk|test_unreadable_dictionary_conversion_strings_are_translated|test_window_title_is_not_passed_to_gettext) .* ok$" $T/verbose.txt; grep -E "^(FAIL|ERROR):" $T/verbose.txt; tail -1 $T/verbose.txt
```

Expected (the count is 61: the F-12 tests; `test_save_returns_what_the_store_returns` is a name in two modules):

```text
Ran 671 tests
OK (skipped=2)
Ran 311 tests
OK
Ran 311 tests
OK
61
OK (skipped=2)
```

- [x] **Step 3: Criterion 3 (no KNOWN BUG pin of P1-4 defect 4 or of P1-3 known defect 4 is left) and the shuffled module order, six seeds** (one process each, about two minutes).

```bash
grep -rn "KNOWN BUG (P1-4 spec, defect 4)\|KNOWN BUG (P1-3 spec, known defect 4)" tests | wc -l
for s in 0 1 2 3 4 5; do $PY -B $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
0
      6 ran=1627 failures=0 errors=0 skipped=6 []
```

- [x] **Step 4: Criterion 4, catalogs.** A fresh template differs from the committed one only in `POT-Creation-Date`; 404 msgids, all translated, 0 fuzzy; the four revived entries are active with their old translations and no obsolete copy; `git diff` against `main` adds the twenty-three entries (plus `#:` reference lines and entries that move); the obsolete entries that went away.

```bash
(cd $REPO && cmd //c "scripts\\generate-pot.bat $(cygpath -w $T/second.pot)"); echo "generate-pot exit $?"
diff --strip-trailing-cr <(grep -v '^"POT-Creation-Date: ' locales/dotexpress.pot) <(grep -v '^"POT-Creation-Date: ' $T/second.pot) && echo "fresh template identical apart from POT-Creation-Date"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
grep -c '^#, fuzzy' locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
$PY -I $T/tools/po_entry.py locales/zh_TW/LC_MESSAGES/dotexpress.po "Export Complete with Errors" "All documents were exported successfully." '"Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}"' "Imported file must be a valid DotExpress DEP package."
git -C $REPO diff e0337df -- client/locales/zh_TW/LC_MESSAGES/dotexpress.po | grep -E '^-#~ msgid'
git -C $REPO diff e0337df -- client/locales/zh_TW/LC_MESSAGES/dotexpress.po | grep -E '^\+msgid' | wc -l
```

Expected (no entry is fuzzy; the obsolete entries that went away are the four revived ones and `Text files (*.txt)|*.txt`, the source of `msgmerge`'s wrong guess for string 6 in Task 7 (Spec Corrections 14); the last count is the `+msgid` lines of the diff: the 23 new entries and the existing entries whose place in the file changed):

```text
generate-pot exit 0
fresh template identical apart from POT-Creation-Date
404 translated messages.
0
source msgids: 404 sha256 ad00d55f0a0da6a34e9676798b47ac1dfeb2d3ea7cadf1e5a53137265ce04d9b
'Export Complete with Errors': active 1, fuzzy no, obsolete copies 0, msgstr '匯出完成，但有錯誤'
'All documents were exported successfully.': active 1, fuzzy no, obsolete copies 0, msgstr '所有文件皆已成功匯出。'
'Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}': active 1, fuzzy no, obsolete copies 0, msgstr '成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}'
'Imported file must be a valid DotExpress DEP package.': active 1, fuzzy no, obsolete copies 0, msgstr '匯入的檔案必須是有效的 DotExpress DEP 封裝檔。'
-#~ msgid "Text files (*.txt)|*.txt"
-#~ msgid "Export Complete with Errors"
-#~ msgid "All documents were exported successfully."
-#~ msgid ""
-#~ msgid "Imported file must be a valid DotExpress DEP package."
26
```

- [x] **Step 5: Criteria 5-7: fixtures, untouched modules, touched files, application data.**

```bash
BASE=e0337df
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/translation_liblouis_golden.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/dialog.py client/ui/message_box.py client/dictionaries client/braille client/tests/fixtures client/translation client/shared client/text client/dual_view/html.py && echo "dialog, message_box, dictionaries, braille, translation, shared, text, dual_view/html and the fixtures unchanged"
git -C $REPO diff --stat=200 $BASE -- client scripts vendor
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) | diff - $T/app-data.sha256 && echo "application data unchanged"
for f in log workspace config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application data checked"
git -C $REPO status --short -- client scripts
```

Expected (the application data are the user's files in the main checkout, read only; `status` prints nothing):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e *-
dialog, message_box, dictionaries, braille, translation, shared, text, dual_view/html and the fixtures unchanged
 client/config.py                                      |  66 ++++++++++++++++++++-------
 client/conversion/plain_text.py                       |  11 ++++-
 client/conversion/preprocessing/user_script.py        |   7 +--
 client/conversion/text/dictionary_rules.py            |  95 ++++++++++++++++++++++++++-------------
 client/documents/export_coordinator.py                |  12 ++++-
 client/documents/export_results.py                    |  10 +++--
 client/documents/formats.py                           |  12 +++--
 client/documents/import_problems.py                   |  49 ++++++++++++++++++++
 client/documents/importers/base.py                    |   7 ++-
 client/documents/importers/epub_importer.py           |  11 +++--
 client/documents/importers/pdf_importer.py            |  10 +++--
 client/documents/workspace.py                         |  42 +++++++++++++----
 client/documents/workspace_service.py                 |  37 +++++++++++++--
 client/dual_view/browser.py                           |   4 +-
 client/gui.py                                         |  85 +++++++++++++++++++++++++++--------
 client/locales/dotexpress.pot                         | 280 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--------------------------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo        | Bin 30650 -> 34046 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po        | 325 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-------------------------------------------
 client/settings/translation.py                        |  13 ++++--
 client/settings/translation_tables.py                 |   4 +-
 client/settings/view.py                               |   5 ++-
 client/tests/test_config.py                           |  90 +++++++++++++++++++++++++++++++++++++
 client/tests/test_conversion_presenter.py             | 117 +++++++++++++++++++++++++++++++++++++++++++++--
 client/tests/test_conversion_service.py               |  23 +++++++++-
 client/tests/test_conversion_text_dictionary_rules.py |  82 ++++++++++++++++++++++++++++++---
 client/tests/test_document_formats.py                 |   5 +++
 client/tests/test_document_workspace.py               |  76 ++++++++++++++++++++++++++++++-
 client/tests/test_dual_view_browser.py                |   3 +-
 client/tests/test_export_coordinator.py               |  59 +++++++++++++++++-------
 client/tests/test_gui_document_flows.py               | 342 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----------------
 client/tests/test_i18n.py                             | 197 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_import_problems.py                  | 183 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_translation_settings.py             |  19 ++++++++
 client/tests/test_translation_tables.py               |  10 +++++
 client/tests/test_user_preprocessing_script.py        |   8 +++-
 client/tests/test_view_settings.py                    |  10 +++++
 client/tests/test_workspace_service.py                |  45 ++++++++++++++++---
 client/ui/conversion_presenter.py                     |  33 ++++++++++++--
 scripts/tests/test_vendor_helper_snapshot.py          |   6 ++-
 39 files changed, 2015 insertions(+), 378 deletions(-)
application data unchanged
worktree application data checked
```

- [x] **Step 6: Criterion 8, mutation check** (44 mutants: the spec's 31 as 32, its item 30 being two (each of the script's two errors) and its item 20 being the client id returning the save problem (the frame never saves the client id); and 10 more: a damaged package that also catches `OSError`, the box without the folder line, the entry ignoring `exclude_name`, Import seeing no unlisted entry, the dictionary's read errors not wrapped, the read error not recognized by `format_conversion_error`, `set_lang` returning the problem, the first failed setter stopping the others, the box always on the frame, the HTML save filter unmarked; and Task 8's two: the rollback without the title update, and without the default document; about eight minutes). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f12_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
export-summary-unmarked: 2 caught: test_i18n.test_export_summary_and_conversion_fallback_texts_are_marked_where_defined, test_i18n.test_the_catalog_holds_exactly_the_marked_strings
fallback-text-unmarked: 2 caught: test_i18n.test_export_summary_and_conversion_fallback_texts_are_marked_where_defined, test_i18n.test_the_catalog_holds_exactly_the_marked_strings
not-utf8-generic: 3 caught: test_document_workspace.test_batch_import_documents_explains_each_skipped_file, test_gui_document_flows.test_import_issues_explain_each_skipped_file, test_import_problems.test_a_text_file_that_is_not_utf8
permission-raw: 1 caught: test_import_problems.test_a_file_that_cannot_be_opened
name-codes-swapped: 2 caught: test_document_workspace.test_batch_import_documents_explains_each_skipped_file, test_import_problems.test_a_file_name_that_is_not_a_document_name
import-problem-shown-by-str: 6 caught: test_document_workspace.test_batch_import_documents_explains_each_skipped_file, test_document_workspace.test_batch_import_documents_imports_txt_only_and_reports_duplicates, test_gui_document_flows.test_import_issues_explain_each_skipped_file, test_import_problems.test_an_encrypted_pdf, and 2 more
damaged-package-generic: 2 caught: test_document_workspace.test_batch_import_documents_explains_each_skipped_file, test_import_problems.test_any_other_error_reading_a_package
damaged-package-catches-os-errors: 1 caught: test_import_problems.test_any_other_error_shows_its_own_text
unlisted-reason-before-the-listed-one: 1 caught: test_document_workspace.test_batch_import_documents_names_the_file_that_holds_a_name_on_disk
package-write-raw: 6 caught: test_gui_document_flows.test_import_reports_load_issues_before_save_issues, test_workspace_service.test_import_does_not_replace_a_package_that_appeared_after_the_names_were_checked, test_workspace_service.test_import_files_continues_after_a_failed_save, test_workspace_service.test_import_files_lists_load_issues_before_save_issues, and 2 more
bopomofo-guarded: 5 caught: test_conversion_text_dictionary_rules.test_from_paths_raises_the_recorded_errors, test_conversion_text_dictionary_rules.test_load_reads_the_rules_once_and_returns_the_same_object, test_conversion_text_dictionary_rules.test_malformed_files_raise_the_recorded_errors, test_conversion_text_dictionary_rules.test_reads_the_bopomofo_file_before_the_dictionary, and 1 more
processing-error-wrapped: 1 caught: test_conversion_text_dictionary_rules.test_an_error_while_processing_the_rows_is_not_wrapped
read-errors-not-wrapped: 4 caught: test_conversion_text_dictionary_rules.test_a_dictionary_that_cannot_be_opened_raises_the_read_error, test_conversion_text_dictionary_rules.test_a_dictionary_that_cannot_be_read_raises_the_read_error, test_conversion_text_dictionary_rules.test_from_paths_raises_the_recorded_errors, test_conversion_text_dictionary_rules.test_malformed_files_raise_the_recorded_errors
header-told-as-other: 2 caught: test_conversion_service.test_headerless_dictionary_fails_text_at_the_translation_stage, test_conversion_text_dictionary_rules.test_a_dictionary_that_cannot_be_read_raises_the_read_error
read-error-not-recognized: 3 caught: test_conversion_presenter.test_export_failure_names_a_dictionary_that_cannot_be_read, test_conversion_presenter.test_format_conversion_error_names_a_dictionary_that_cannot_be_read, test_conversion_presenter.test_manual_failure_names_a_dictionary_that_cannot_be_read
two-paragraph-form: 3 caught: test_conversion_presenter.test_export_failure_names_a_dictionary_that_cannot_be_read, test_conversion_presenter.test_format_conversion_error_names_a_dictionary_that_cannot_be_read, test_conversion_presenter.test_manual_failure_names_a_dictionary_that_cannot_be_read
unlisted-box-for-a-listed-name: 4 caught: test_gui_document_flows.test_a_listed_duplicate_keeps_its_message_before_any_entry_on_disk, test_gui_document_flows.test_add_case_variant_is_refused_as_a_duplicate, test_gui_document_flows.test_add_duplicate_name_reprompts_with_that_name, test_gui_document_flows.test_rename_to_a_case_variant_of_another_document_is_refused
entry-takes-the-typed-spelling: 2 caught: test_gui_document_flows.test_add_of_another_case_of_an_unlisted_name_names_the_entry_on_disk, test_workspace_service.test_unlisted_package_entry_names_what_holds_a_name_on_disk
box-without-the-folder: 5 caught: test_gui_document_flows.test_add_of_a_name_held_by_a_folder_names_the_folder, test_gui_document_flows.test_add_of_a_name_whose_package_is_on_disk_asks_again, test_gui_document_flows.test_add_of_another_case_of_an_unlisted_name_names_the_entry_on_disk, test_gui_document_flows.test_rename_to_a_name_whose_package_is_on_disk_asks_again, and 1 more
entry-ignores-exclude-name: 4 caught: test_gui_document_flows.test_case_only_rename_keeps_the_document, test_gui_document_flows.test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document, test_gui_document_flows.test_rename_cancelled_or_unchanged_does_nothing, test_workspace_service.test_unlisted_package_entry_names_what_holds_a_name_on_disk
import-sees-no-unlisted-entry: 2 caught: test_gui_document_flows.test_import_of_a_name_held_by_an_unlisted_package_names_the_file, test_workspace_service.test_import_treats_packages_on_disk_as_existing
unreadable-not-returned: 4 caught: test_config.test_a_file_that_cannot_be_read_is_unreadable, test_gui_document_flows.test_a_settings_change_that_cannot_be_saved_shows_one_box_and_still_applies, test_gui_document_flows.test_font_size_and_dictionary_changes_report_through_the_same_flag, test_gui_document_flows.test_the_box_belongs_to_the_active_window
backup-failed-not-returned: 1 caught: test_config.test_a_damaged_file_whose_backup_fails_is_backup_failed
write-failed-not-returned: 1 caught: test_config.test_a_write_that_fails_is_write_failed
once-per-session-flag-ignored: 2 caught: test_gui_document_flows.test_a_settings_change_that_cannot_be_saved_shows_one_box_and_still_applies, test_gui_document_flows.test_font_size_and_dictionary_changes_report_through_the_same_flag
client-id-returns-the-problem: 2 caught: test_config.test_save_failure_log_does_not_contain_config_data, test_config.test_the_client_id_and_the_language_ignore_a_failed_save
set-lang-returns-the-problem: 1 caught: test_config.test_the_client_id_and_the_language_ignore_a_failed_save
box-after-a-good-save: 10 caught: test_gui_document_flows.test_a_cancelled_dialog_is_no_longer_synced, test_gui_document_flows.test_a_clamped_step_still_saves_and_syncs_the_clamped_size, test_gui_document_flows.test_an_open_text_processing_dialog_is_left_alone, test_gui_document_flows.test_applied_settings_tables_reach_next_conversion_request, and 6 more
font-size-not-reported: 1 caught: test_gui_document_flows.test_font_size_and_dictionary_changes_report_through_the_same_flag
dictionary-not-reported: 2 caught: test_gui_document_flows.test_font_size_and_dictionary_changes_report_through_the_same_flag, test_gui_document_flows.test_the_box_belongs_to_the_active_window
first-failed-setter-stops-the-others: 1 caught: test_translation_settings.test_save_calls_every_setter_and_returns_the_first_problem
box-always-on-the-frame: 1 caught: test_gui_document_flows.test_the_box_belongs_to_the_active_window
manual-named-when-open: 6 caught: test_conversion_presenter.test_a_failure_after_switching_away_and_back_is_not_named, test_conversion_presenter.test_a_failure_of_the_open_document_is_not_named, test_conversion_presenter.test_manual_failure_names_a_dictionary_that_cannot_be_read, test_conversion_presenter.test_manual_failure_shows_error_after_busy_off, and 2 more
manual-not-named-when-not-open: 1 caught: test_conversion_presenter.test_a_failure_after_switching_names_the_document
export-rule-takes-the-open-document-at-the-request: 1 caught: test_export_coordinator.test_a_failed_export_of_a_document_that_is_not_open_names_it
export-all-lines-named: 5 caught: test_export_coordinator.test_export_all_missing_table_accumulates_failures_without_per_file_messages, test_export_coordinator.test_export_all_partial_failure_summary_lists_each_failure, test_export_coordinator.test_export_all_with_a_real_presenter_turn_by_turn, test_gui_document_flows.test_export_all_mixed_documents_turn_by_turn, and 1 more
exported-page-in-english: 3 caught: test_export_coordinator.test_write_document_uses_the_given_results_instead_of_the_cache, test_gui_document_flows.test_export_all_html_uses_each_document_cache, test_gui_document_flows.test_real_writers_produce_today_bytes
html-filter-unmarked: 2 caught: test_i18n.test_html_save_filter_is_marked_where_defined, test_i18n.test_the_catalog_holds_exactly_the_marked_strings
browser-error-untranslated: 2 caught: test_dual_view_browser.test_missing_non_windows_fallback_raises_os_error, test_i18n.test_the_catalog_holds_exactly_the_marked_strings
script-error-untranslated: 3 caught: test_conversion_service.test_a_script_error_of_the_contract_is_shown_in_zh_tw, test_i18n.test_the_catalog_holds_exactly_the_marked_strings, test_user_preprocessing_script.test_execution_rejects_non_callable_main_and_non_string_return
script-callable-error-untranslated: 2 caught: test_i18n.test_the_catalog_holds_exactly_the_marked_strings, test_user_preprocessing_script.test_execution_rejects_non_callable_main_and_non_string_return
rollback-title-not-updated: 3 caught: test_gui_document_flows.test_delete_all_failure_reviews_paths_from_service, test_gui_document_flows.test_delete_all_failure_with_new_held_on_disk_opens_a_free_default_name, test_gui_document_flows.test_delete_all_failure_without_valid_document_opens_the_default_document
rollback-without-the-default-document: 3 caught: test_gui_document_flows.test_delete_all_failure_reviews_paths_from_service, test_gui_document_flows.test_delete_all_failure_with_new_held_on_disk_opens_a_free_default_name, test_gui_document_flows.test_delete_all_failure_without_valid_document_opens_the_default_document
window-title-through-gettext: 1 caught: test_i18n.test_window_title_is_not_passed_to_gettext
exit 0
```

### Task 11: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay. Run everything from the repository root, one item at a time, with nothing else driving the desktop, and only when at least 1 GB of memory is available (Global Constraints). Never touch the existing `D:\dxtest\N*`, `B` builds (only read and copied by the scripts) or the existing `D:\dxtest\auto*` folders; every run of this task uses a new folder whose name ends in `-f12` (drafts in `D:\dxtest\autodraft*-f12`). Only processes whose exe lies under that folder are ended (`dx.kill_under`); the lock helper the scripts start is ended with `taskkill /T`. The user may have DotExpress open and is using the desktop: never end any other process. Every script runs through `auto/safe_run.py` (F-11's approach): a key is sent only while a window of the app under test is in the foreground, and no window or element name of another program is written to a log. No script writes to the clipboard: text reaches the app through files and `set_edit_text`.

**Fix and regression items** (user, 2026-10-11). A **fix** item is one whose expected result differs between the builds; it runs on both builds (`N-f11c`, the build of `main` `e0337df`'s code, then `N-f12`). A **regression** item runs on `N-f12` only, and on `N-f11c` too only when it misses its expectation (that run is then reported). Items 109-117 and 120 are fix items; 118 is a regression item; 119 is manual (NVDA) and stays unchecked. Item 120 is the Delete All rollback of Task 8 (added to F-12 by the user, 2026-10-11).

- [x] **Step 1: Build** (PowerShell, in the worktree). The main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`; `scripts\build-dotexpress.bat` calls `pyinstaller` from `PATH` and assumes no venv of its own.

```powershell
Set-Location D:\workspace\DotExpress-f12
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f12-build.log 2>&1"
if (Select-String -Path $env:TEMP\f12-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "documents\\export_results.py", "conversion\\plain_text.py", "documents\\import_problems.py", "documents\\workspace.py", "documents\\workspace_service.py", "conversion\\text\\dictionary_rules.py", "ui\\conversion_presenter.py", "documents\\export_coordinator.py", "config.py", "documents\\formats.py", "dual_view\\browser.py", "conversion\\preprocessing\\user_script.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress-f12\\client\\$m" -Quiet) { "$m bundled from the worktree" } }
if (Select-String -Path client\build\DotExpress\Analysis-00.toc -SimpleMatch "DotExpress-f12\\client\\gui.py" -Quiet) { "gui.py analyzed from the worktree" }
New-Item -ItemType Directory -Force D:\dxtest\N-f12 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f12\DotExpress.exe
(Get-Item D:\dxtest\N-f12\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f12\DotExpress.exe).Hash
git status --short -- client scripts
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f12-build.log`), the twelve `bundled from the worktree` lines (printed with their doubled backslash), `gui.py analyzed from the worktree`, a size near 48.8 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored). The `.mo` is bundled through `--add-data "locales;locales"`.

- [x] **Step 2: Write the GUI scripts** into `docs/superpowers/history/2026-10-11-02-f12-localization-cleanup/auto/` (tabs): a helper `f12gui.py` that reuses, unchanged, `f9gui.py` of F-9 and through it F-8b's, F-8a's, F-7's and F-5's helpers and `dx.py`, `docs.py`, `dicts.py` of `2026-10-09-03-windows-verification/auto/`; `safe_run.py` (F-11's, adapted to `f12gui`); one script per item (`item109.py` ... `item118.py`, `item120.py`; 109 and 110 may share one). Each script deletes its work folder first (after ending any process under it), copies the exe into it, starts it once so that it creates its folders, closes it, writes its test files (packages with `zipfile`, `config.json`, dictionaries and `preprocessing.py` as bytes) and starts it again. A box is read through UIA (`f5gui.describe`: title, main instruction, content, buttons, focus; `safe_run` masks a focus that belongs to another program) and answered with a key; the work folder is shown as `<d>`, the random part of a temporary file name as `<rnd>`. Drafts run against `N-f12` and `N-f11c` in `D:\dxtest\autodraft*-f12` folders until each script runs through; their logs are not results.

- [x] **Step 3: The items** (Git Bash, from the repository root): fix items on `D:\dxtest\N-f11c\DotExpress.exe` (folders `auto<N>-f11c-f12`) and on the new build (folders `auto<N>-f12`); the regression item on the new build only. Read each log against Step 4 before the next run.

- [x] **Step 4: Expected behaviour.** `<OS text>` is the error text of the operating system; a reason in `...` is the full zh_TW text of the spec's table.

| # | Class | Steps | Expected on `N-f12` | Expected on `N-f11c` |
| --- | --- | --- | --- | --- |
| 109 | fix | Three converted documents; File > Export All > BRL into an empty folder | the box `匯出完成` / `所有文件皆已成功匯出。`; three `.brl` files | caption `匯出完成`, text `All documents were exported successfully.` |
| 110 | fix | As 109, with `beta.brl` already in the folder and held share-none by the lock helper (the overwrite question answered Yes) | `匯出完成，但有錯誤`, `成功匯出的文件：2`, `匯出失敗的文件：1`, `beta: <OS text>` | caption `Export Complete with Errors`, `Exported documents: 2` ... |
| 111 | fix | Import, "All supported" filter, the names of `alpha.txt` (listed), `big5.txt`, a 40-character `.txt`, `locked.txt` (held share-none by the lock helper before the Import, Spec Corrections 16), `broken.dep` (not a zip), `foo.xyz` typed together | Import Issues lines: `alpha.txt: 文件「alpha」已存在。`, `big5.txt: 檔案不是以 UTF-8 文字儲存。...`, `<40 x>.txt: 文件名稱長度需為 1 到 32 個字元。`, `locked.txt: 無法開啟檔案。...`, `broken.dep: 匯入的檔案必須是有效的 DotExpress DEP 封裝檔。`, `foo.xyz: 無法匯入這種類型的檔案。` | the English and raw lines of the spec's probe 1 |
| 112 | fix | `config.json` selects `big5dict` (Big5 CSV); Convert a short text; the same with `caps` (`Text,Braille,Type`), `empty` (0 bytes), and a readable dictionary held share-none; then Export All (BRL) of two pending documents with `big5dict` | each Convert: `轉譯失敗：無法讀取字典「<name>」。<reason>` with NOT_UTF8, the header reason (twice), CANNOT_OPEN; the Export All summary: one line per document with the same text | `轉譯失敗：'utf-8' codec ...`, `CSV must contain ...`, `[Errno 13] ...` |
| 113 | fix | Workspace `alpha.dep` (valid) and `bad.dep` (invalid, kept at startup with Keep Invalid Files). Add `BAD`; Rename `alpha` to `bad`; Import `bad.txt` | Add and Rename: the box `錯誤` with string 18 naming `bad.dep` (main instruction) and string 19 with the workspace path (content); the name dialog back with the name; Import: `bad.txt: ` + string 18; the files unchanged | `文件「BAD」已存在。`, `文件「bad」已存在。`; `bad.txt: Document "bad" already exists.` |
| 114 | fix | (a) `config.json` held share-none by the lock helper after the start, before pressing OK (held from before the start, the app does not start); Settings: change the width, OK; then Ctrl+wheel in the source editor (Spec Corrections 16). (b) `config.json` = `{` and a folder `config.json.bak`; Settings: change the width, Apply, then OK | (a) after OK one box `設定未儲存` with string 21 (the path) and the CANNOT_OPEN reason, owned by the settings dialog; no box after Ctrl+wheel; the font size changes on screen; `config.json` keeps its bytes. (b) after Apply the box with string 22, owned by the settings dialog; nothing after OK; `config.json` still `{` | no box in either case |
| 115 | fix | `preprocessing.py` in the dictionary folder whose `main` sleeps 5 s, then raises `ValueError("boom")`. (a) open `alpha`, Ctrl+Enter, Ctrl+Tab at once to `beta`; wait. (b) open `alpha`, select `beta` (pending) in the list, File > Export > BRL; wait. (c) as (a) without Ctrl+Tab | (a) `錯誤`: `無法轉換文件「alpha」。` (main instruction), `文字處理失敗：boom` (content); (b) the same naming `beta`; (c) `文字處理失敗：boom` alone | (a), (b) `文字處理失敗：boom` alone; (c) the same |
| 116 | fix | The default document `new` (no conversion data): File > Export > Dual View HTML; read the save dialog's file type list; save | the type list shows `HTML 檔 (*.html)`; the file contains `此文件沒有可顯示的轉換資料。` | `HTML files (*.html)`; the English sentence |
| 117 | fix | `preprocessing.py` whose `main` returns `None`; Convert | `文字處理失敗：main 必須傳回 str，而不是 NoneType。` | `文字處理失敗：main must return str, got NoneType.` |
| 118 | regression | (a) Convert with a readable dictionary. (b) Add `alpha` while `alpha` is listed. (c) Settings OK with a writable `config.json`. (d) F-9's case (b): a long conversion of `alpha`, Ctrl+Tab to `beta` | (a) `轉換完成。`; (b) `文件「alpha」已存在。`, the dialog back; (c) no box, the file updated; (d) `轉換完成。結果已儲存到文件「alpha」。` | (only if a result misses) |
| 120 | fix | Workspace `alpha.dep` and `beta.dep` (both valid); `alpha` open. After the start, `beta.dep` is held share-none by the lock helper. File > Delete All, Yes; the error box; the invalid-files dialog (Keep) | after the dialog the window title `new - DotExpress`, the list `new`, the editors empty, `workspace` holds `beta.dep` and `new.dep` | the title stays `alpha - DotExpress`, the list is empty, the editors empty, no `new.dep` |

A task dialog without a blank line in its message has no main instruction (`main` is `None`, the text is the content). If a key or a click goes to another window (a `RuntimeError` from `safe_run`, or a box that never opens), that is a tool problem: run the item again in a new folder and record it.

- [x] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-11-02-f12-localization-cleanup/auto-results.md` in the style of `2026-10-11-01-f11-dictionary-editor-ux/auto-results.md` (zh-TW): the build (PyInstaller version, `Build complete!`, the bundled modules, size, sha256), the method, then one row per item (109-118, 120) with ✔/△/✘, the observed boxes, files and logs on `N-f12` and, for fix items, on `N-f11c`. Any deviation from Step 4 is reported to the orchestrator, not explained away; a re-run after a GUI timing problem is recorded with the first attempt's log name. End the file with a short section **「仍需人工（使用者）」** for item 119, worded for the user (do not mark it done): with `N-f12` and NVDA running, listen to the boxes of items 112 (one case), 113 (Add), 114 (a) and 115 (a): is the whole text read, including the document or dictionary name and the path; does Esc close each box; where is the focus afterwards.

Then add a section **Implementation Notes** at the end of this plan (what was applied, any deviation, the commit hashes and tree ids, the exe), as the F-11 plan has, and commit:

```bash
cd $REPO
git add docs/superpowers/history/2026-10-11-02-f12-localization-cleanup docs/superpowers/plans/2026-10-11-f12-localization-cleanup.md
git diff --cached --stat
git commit -q -m "docs: record the F-12 packaged-build GUI checks (F-12)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short -- client docs scripts
git rev-parse HEAD:client
```

Expected: the history folder's files and the plan in the `--stat`, no `status` output, and Task 8's tree id (the commit touches no file under `client/`). Do not merge `main` or push; the orchestrator decides.

## Implementation Notes (2026-10-11)

Planning and implementation were merged into one run (the user, 2026-10-11), and the work was done by two agents in turn. **Handover:** the first agent wrote the code (a scratch dev clone, red first, nine tasks as tags) and the plan source, then stopped to save quota. The second agent wrote the spec corrections into both spec files (the English text from the plan source, the zh-TW translation new), ran the fill replay, the verify replays and the final replay, landed the commits on the worktree's branch, built, ran the GUI items and wrote this record. The dev clone's code was not changed by the second agent; every commit below is the final replay's, taken over with `git fetch` and `git merge --ff-only` (no code was retyped).

1. **Commits and trees** (`HEAD:client` of each, equal to the plan's and to the dev clone's tags): plan `77f00a6` (this plan and both spec files); Task 1 `3c2eacf` `b6d32d26860d0a9cdee68f3bd81634ec529d0efd` (`Ran 1569`, 386 msgids); Task 2 `c05f262` `5e23f82b85a0ff43a96236eca5e6e86cfe959905` (`1583`, 392); Task 3 `6838990` `0661d35dc654b7e0f025ce34e452fd7629257273` (`1591`, 394); Task 4 `17b5cf4` `ebbf013b774aaeae21b6ce9dc98532f08d016023` (`1599`, 396); Task 5 `66db33d` `cd5b9c3959ca123d34771634df05d9a028806c40` (`1614`, 399); Task 6 `40b206f` `b6929558c675a31124b2e1f418db2d2b87a7576a` (`1620`, 400); Task 7 `611e618` `9a5516a5f74312816fbae4ae2f8b7e2f75c210ef` (`1626`, 404); Task 8 `cf8cada` `62325f9a05b0cd0a1af9344cd078e417c09910d1` (`1627`, 404); Task 9 `b52ac5c` (`HEAD:client` unchanged, `HEAD:scripts` `6a2bd0cb0ea886626e676bd69458b9939bd2462e`). Every run is `OK (skipped=6)`. The fixture sha256s of `HEAD` are unchanged (`e67d95a1...`, `f493da52...`, `8dc8572e...`).
2. **Replays.** The fill replay recorded the 59 expected blocks (`--record --fill`); the verify replay found one mismatch, in Task 2's red run: the cut diff line `Impor[142 chars]3/sources/bad.txt` shows the last character of the system temporary folder's random name, which differs per run. `brief.py` now shows that character, before `/sources/`, as `<c>` (and Global Constraints say so); the block's line, cut to 160 characters as `brief.py` does, was changed in the same way; the next verify replay and the final replay (a fresh clone of the worktree's branch with the plan commit, every step's blocks applied by Task 0 Step 3's `apply_blocks.py`: 24 apply steps) both ended with 0 mismatches, including the 44 mutants (all caught), six shuffle seeds and the catalogs (404 translated, 0 fuzzy). The sentence of the Dry Run section that named 42 mutants now says 44.
3. **Build.** `D:\dxtest\N-f12\DotExpress.exe` from `b52ac5c` (Step 1's command; PyInstaller 6.21.0, Python 3.13.15, `Build complete!` in about 44 s; the twelve modules and `gui.py` from the worktree), 48,792,061 bytes, sha256 `0D0239440B5D7E51977B9F5C74E752F46661186DEEC935AE6096284C44D49C82`, built when more than 600 MB of memory was free. The worktree's git-ignored runtime (Task 0 Step 2's guarded copies of the liblouis DLL and tables, `louis_helper.py`, MathCAT and the two include files) was copied into the worktree before the build; none of it is staged.
4. **GUI items.** The record is `docs/superpowers/history/2026-10-11-02-f12-localization-cleanup/auto-results.md`. Fix items 109-117 and 120 on `N-f11c` and `N-f12`, regression item 118 on `N-f12` only (all of it matched, so no `N-f11c` run); every result matched Step 4, except the one step of 114 (a) below. Item 119 (NVDA) is manual and stays unchecked. The scripts ran through `auto/safe_run.py`; `auto/run_item.sh` is the driver that waited for 600 MB of memory and named the folders and logs.
5. **Deviations.** (a) **114 (a):** an app whose `config.json` is held share-none from before the start does not start at all (F-8's startup check reports that it cannot write its data folder and exits), so the script holds the file after the start, before OK; the expected result is unchanged. The plan's Step 4 row and the spec's item 114 (a) said "from before the start"; both now say "locked after the start, before pressing OK" (fix phase, review M-4). (b) **Script problems, re-run after deleting their folders and logs:** a missing constant in `f12gui` (109), a Big5 file that could not be encoded and a here-doc that turned `\r\n` into line breaks (112, both before the app started), and a mask for temporary file names that did not cover `.brl` and `.bak` names (110, 114 (b)). (c) The plan commit's tooling sentence about `brief.py` (the `<c>` mask) is the one change made to the plan's text blocks after the fill replay besides this note. (d) `msgmerge`'s eight wrong fuzzy guesses (Spec Corrections 14) were replaced by the plan's blocks as designed; the catalogs hold 404 translated, 0 fuzzy.
6. **Left for the user.** GUI item 119 (NVDA, four boxes), the orchestrator's merge of `fix/f12-localization-cleanup`, and the open questions Q1 to Q3 (decided by the orchestrator with the recommended defaults; the user may override before merge).

7. **Fix phase (the F-12 review of `c1295df`, 2026-10-11; Spec Corrections 19).** Red first: the tests of M-1, M-2, M-3 and M-5 failed before the code (`test_gui_document_flows` 8 failures, `test_import_problems` and `test_document_workspace` 9). One commit `bdb3e78` holds the code, the tests and the catalogs (the catalog change is shared by the three strings): `Ran 1632` (1627 + 5 tests), `OK (skipped=6)`, 407 msgids translated, 0 fuzzy, `HEAD:client` `a967d8d4cea147cf25ccc0f490c8f94e41e711ce`; the three fixtures keep their sha256. `msgmerge` guessed two wrong fuzzy translations (the damaged-file string from the EPUB text, the write-permission string from CANNOT_OPEN), replaced by the fill step; a second `msgmerge` changes nothing; 26 obsolete entries as before. Build `D:\dxtest\N-f12b\DotExpress.exe` (48,791,375 bytes, sha256 `0F79EAC81386C2DE53D3E92BBA61DE5414A3114B49902E462AF333270BCEC4C2`) with more than 600 MB free; N-f12 and N-f11c are untouched. GUI items 114 (a) and (b) and 111 re-run on N-f12b and N-f11c in fresh `auto*-f12b` and `auto*-f11c-f12b` folders (`auto/run_item.sh` has the builds `newb` and `beforeb`); all as expected (`auto-results.md`, "Fix phase"). The plan's step boxes are ticked (they were all done); the dispositions of the review are in `review_task.md`: M-6 by design (Q1), M-7 a follow-up for the user to record.
