# Conversion Results Go to the Document They Came From (F-9) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ] `) syntax for tracking.

**Goal:** A manual conversion's result goes to the document that was open when the user pressed Convert, also when the user has switched documents (Ctrl+Tab and friends) or imported one (Ctrl+O) meanwhile (the user's decision U1): the open document is left alone, the result is saved to the starting document at once, and a new information box names it. A result whose starting document is gone or holds another text is discarded and logged. An export conversion asked for while another conversion runs waits in a FIFO queue instead of silently replacing it, so no result is dropped. The HTML export of a pending document shows its fresh conversion instead of the "No conversion data" page. Any worker error ends the busy state with the existing "Translation failed" box, and a closed window ignores late results. One new msgid (368 -> 369).

**Architecture:** Five commits on the client, each red first, the spec's migration steps with steps 4 and 5 swapped (Spec Corrections 2). Task 1 makes `ConversionJobRunner._run_job` deliver every exception as a "translation" failure and log it (D7). Task 2 passes the whole `ConversionOutput` to an export's success callback and lets `ExportCoordinator.write_document` take the fresh `dual_view_results` (D6). Task 3 gives `ConversionPresenter` a FIFO queue, a `_completing` flag and the try/finally drain, and makes `is_running()` mean "active or queued" (D4, D5). Task 4 adds `ConversionPresenter.shutdown()`, called by `BrailleFrame._finish_close` (D8). Task 5 records the starting document in each manual job and completes it by the spec's cases (a), (b) and (c) with the guard of D3, adds `DocumentWorkspaceService.save_document` (the body of `save_open_document`, which now delegates to it) and `BrailleFrame.save_converted_document`, and adds the D2 msgid to the catalogs (D1-D3, D9). Task 6 verifies (suite, shuffled order, catalogs, fixtures, application data, 30 mutants), Task 7 builds the exe and runs the GUI checks (items 85-93; item 94 stays manual).

**Tech Stack:** Python 3.13 standard library (`collections.deque`, `dataclasses`, `logging`, `unittest`, `unittest.mock`), wxPython 4.2.5 (message boxes through `ui.message_box`, unchanged), GNU gettext 0.23 (`xgettext`, `msgmerge`, `msgfmt`, `msgattrib`), Git Bash `unix2dos`. Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-10-f9-conversion-target-document-design.md` (+ `_zh-TW.md`), with the section "Corrected after planning (F-9, 2026-10-10)" / 「規劃後的修正（F-9，2026-10-10）」 added in the plan commit (both languages). The user decided U1 (2026-10-10). O1-O9 are the orchestrator's recommended defaults; the plan adds O10 and O11 (Spec Corrections 5 and 4), also defaults the user may override before the merge.

## Global Constraints

- Work in the worktree `D:\workspace\DotExpress-f9`, branch `fix/f9-conversion-target-document` (HEAD is the plan commit on top of the spec commit `a39d207`, which is on `main` at `7aba2be`, the F-8b merge). Never switch branches, never push, never merge, never rewrite history. The worktree has no `client\.venv`: `PY` is the main checkout's interpreter, run with the working directory inside the worktree. Do not work in the main checkout `D:\workspace\DotExpress` (the user may run the app from source there) and do not touch `D:\workspace\DotExpress-6e5819f`.
- Files that may change (12 under `client/`, nothing else there): production `client/conversion/jobs.py`, `client/gui.py` (**tabs**), `client/ui/conversion_presenter.py`, `client/documents/export_coordinator.py`, `client/documents/workspace_service.py` (4 spaces); tests `client/tests/test_conversion_jobs.py` (**tabs**), `client/tests/test_conversion_presenter.py`, `client/tests/test_export_coordinator.py`, `client/tests/test_workspace_service.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_i18n.py` (4 spaces); catalogs `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`; in Task 7 the new history folder `docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/` (scripts with tabs, results).
- Never touch, in the main checkout `D:\workspace\DotExpress`, `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data; Task 0 and Task 6 only hash them), or its untracked `client2/`, `preprocessing/`, `testdata/` and `task.md`. In the worktree no test may create `client/log/`, `client/workspace/` or `client/config.json`: every module whose code under test can log isolates `dotexpress.gui` (`test_conversion_jobs` and `test_conversion_presenter` get a `setUpModule` for it; the other three modules have one already). Never touch `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (CRLF bytes), tracked `client/braille/` content, `client/braille/liblouis/`, `client/tests/fixtures/`, `scripts/`, `vendor/`, the submodule pointers, or the committed scripts and data of earlier history folders. Never run `py scripts\sync-nvda.py`. Never start `gui.py` from source in either checkout: only packaged copies, each in a new `D:\dxtest\auto*-f9` folder. **Never write to the Windows clipboard**: no test, probe or GUI script of this plan does (no `SetClipboardData`, no Ctrl+C/V/X, no `wx.TheClipboard`; do not use `f5gui.paste_text_with_lone_surrogate`). `git status --short -- client docs scripts` must stay empty between commits (`docs/` holds the history folder of Task 7 only until Task 7 commits it).
- The worktree uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply the blocks **with a script that reads them from this file** (`$T/tools/apply_blocks.py`, Task 0 Step 3), not by hand: a `File:` block is written as is (LF is fine; git normalizes it); an `Edit:` block is the line ``Edit: `path` `` followed by two fenced blocks, the exact old text and its replacement; the old text must occur exactly once in the file at that point (compared with CRLF converted to LF; the file keeps its line endings). The blocks of one step are applied in order. Never edit with MSYS `sed -i` and never paste code through a shell heredoc (it turns `\\` into `\`). The blocks hold no `\uXXXX` escape, but the test files they edit do (`test_workspace_service.py`, `test_i18n.py`): the Edit/Write tools would turn such escapes into characters, so never rewrite a whole file through them. `apply_blocks.py` reads and writes bytes; the tree id check after each commit catches any other change. A lone surrogate in a test comes from the existing `LONE_SURROGATE = chr(0xD83D)` and U+FFFD from `chr(0xFFFD)`.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf` (`git show HEAD:<path> | sha256sum`), unchanged.
- Catalogs: `POT-Creation-Date` stays `2026-10-10 12:00+0800` (pinned by `$T/tools/pin_pot_date.py` after `generate-pot.bat`), so the `.pot`, `.po` and `.mo`, and with them the tree id, are the same in every run.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly; look at `git diff --cached --stat` first; never `git commit -F -`.
- The only failing test before and after F-9 is the F-W6 error `test_dictionary_name_prompt ... test_case_only_rename_still_renames` (out of scope).
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`, the random part of a temporary file name as `<rnd>`, object addresses as `<addr>`). Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks. Tests run as `$PY -B -X utf8 -m unittest ...` (no bytecode in the worktree).
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress-f9
  MAIN=/d/workspace/DotExpress
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f9impl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the main checkout: only its interpreter is used, its git-ignored runtime is copied if the worktree lacks it (Task 0 Step 2), and its application data is hashed read-only (Task 0 Step 4, Task 6 Step 5). The dry run used scratch clones as `REPO`. Task 7 uses PowerShell for the build and the UIA venv for the GUI scripts.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning (F-9, 2026-10-10)" in the plan commit. Re-checked against the code of `main` `7aba2be` (after F-8a and F-8b): every decision D1-D9, the behavior table and the reachability list hold. F-8 did not touch `ui/conversion_presenter.py`, `conversion/jobs.py` or `documents/export_coordinator.py`, so their line numbers in the spec are still right; `gui.py` and `workspace_service.py` moved (see 3). The refinements:

1. **Baseline and counts.** On `7aba2be` the suite gives `Ran 1444`, `FAILED (errors=1, skipped=7)` (F-W6 only) and the catalogs hold **368** msgids, so the D2 msgid makes **369** (the spec said 364 -> 365, with a note to recount after F-8). F-9 adds 34 tests: `Ran 1445` after Task 1 (A: 1 new, 1 flipped), `1450` after Task 2 (B15, C1-C3, E9), `1459` after Task 3 (B8-B13, E6, E7, E10; B7, E5 and E8 flipped), `1461` after Task 4 (B14, E11; E12 and the delegation test updated), `1478` after Task 5 (B1-B6, D1-D5, E2-E4, E13, E14, and one catalog test F1; E1 flipped). The acceptance-criterion-2 set (the five modules) goes from `Ran 330`, `OK` to `Ran 363`, `OK` (F1 is in `test_i18n`).
2. **Migration steps 4 and 5 are swapped**: Task 4 is D8 (`shutdown`), Task 5 is D1-D3 with the catalogs. D8 adds a line to `gui.py` above several msgids; done after the catalog regeneration it would leave their `#:` references stale, and Task 6's check that a fresh template differs from the committed one only in `POT-Creation-Date` would fail. The steps are independent (E11 does not need D1). Commit subjects stay the spec's.
3. **Line references on `7aba2be`** (orientation only): `save_open_document` is `workspace_service.py:187-197` (spec: 124-134); in `gui.py` `_open_adjacent_document` 627-634, `_editor_text` 636-638, `on_import_document` 918-946, `on_output_text_key_down` 986-995, `on_char_hook` 1006-1027, `_close` 1066-1077, `_finish_close` 1092-1099, `get_source_text` 1103-1104, `set_conversion_busy` 1106-1114 (spec: 1080-1088 and so on).
4. **D3 logs at `ERROR`, not `WARNING`** (O11). `dotexpress.gui` is bound with `log.get_logger`'s default level `ERROR`, and its `gui.log` handler too, so a `WARNING` never reaches `gui.log` (found in the F-8b fix phase). The message is `Discarded a conversion result: %s` with one of `document "<name>" no longer exists`, `the text of document "<name>" changed`, `document "<name>" was opened during a conversion without a document`. The runner's D7 line is `Unexpected error in a conversion job` with `exc_info`. Both loggers are bound at call time. Decided by orchestrator with the recommended default; user may override before merge.
5. **D8 also stops new jobs** (O10): after `shutdown()`, `_submit` returns at once (an Export All step's `CallAfter` that runs after the close would otherwise start a job and call a destroyed frame), and the dialog timer checks `_shut_down`. The drain checks it too, as the spec says. Decided by orchestrator with the recommended default; user may override before merge.
6. **Tests the spec did not list** that change: `FrameConversionDelegationTest.test_close_asks_presenter_before_saving` gets `call.presenter.shutdown()` between the save and `close_converting_dialog` (D8); `test_is_running_and_missing_table_message_read_live_state` now expects `is_running()` to stay `True` after the worker ends until the delivery (D5); three coordinator tests call `on_success` with a `ConversionOutput` instead of a string (D6), and the presenter's `_export_callbacks` records `output.display_text`.
7. **Test placement and names.** C3 is `test_write_document_uses_the_given_results_instead_of_the_cache` (`None` reads the cache; `()` and a tuple are used as they are; `()` writes "No conversion data" even with a cache entry). D1-D5 are methods of `SaveOnlyWhenChangedTest` (its loaded workspace: alpha open, pending beta not). E13 is in `FrameViewMethodsTest`. E3 drives Ctrl+O with a fake import dialog (`GetPaths`, `SetFilterIndex`, `GetFilterIndex`). F1 `test_conversion_result_saved_string_is_translated` (`test_i18n`) makes the catalog step red first. New frame tests compare message boxes without the frame (`_boxes()`), so no object address appears in a failure line.
8. **`_write_single(..., **results)`** passes `dual_view_results` to `write_document` only for a pending export, so the existing tests that mock `write_document` and expect `(path, document, format_key)` stay unchanged.
9. **Catalogs.** `msgmerge` does not fuzzy-match the new msgid (it stays untranslated until the block fills it: `368 translated messages, 1 untranslated message.`). Its reference is `ui/conversion_presenter.py:305`; the regeneration also refreshes the `#:` lines of `ui/conversion_presenter.py` and `gui.py` that Tasks 3-5 moved.
10. **Windows items** are numbered 85-93 (the spec's `9a`-`9i` in order; F-8a's manual item 84 was the last number used) and the manual NVDA item is 94. "Before" is `D:\dxtest\N-f8b2\DotExpress.exe` (F-8b after its review, `HEAD:client` `f6bd18c9...`, the code of `7aba2be`); the new build goes to `D:\dxtest\N-f9`. Method: a long source text (`f9gui.LONG_REPEAT` = 8000 copies of a 65-character mixed Chinese and English line, 520,000 characters) converts in about 15 s on the dry run's machine; the keys are sent right after Ctrl+Enter, before the converting dialog appears at 2 s. Disabling the source editor moves the focus to the Braille Result editor, so Ctrl+Tab, Ctrl+O and Ctrl+S reach the frame's char hook (measured). Items 89 and 90 focus the Braille Result editor directly instead of pressing F6. Every key goes through `f9gui.keys`, which first checks that the main window is the foreground window and stops the item otherwise (no key ever reaches another program). The logs show long texts by length and first characters and the work folder as `<d>`, so the dry run's logs (in `D:\dxtest\autodry*` folders) and the real ones compare line by line.
11. **Observed in the dry run (not a result of F-9, not blocking):** a `WM_ENDSESSION` while a conversion runs ended the process once with exit code `-1073740940` (`0xC0000374`, a heap corruption at process exit) instead of 0, in one of five runs of item 93 on F-9 builds; the other runs and the run on N-f8b2 exited with 0. wx 3.2.9 sends no close event on `WM_ENDSESSION` (F-7 item 60), so no F-9 code runs there; Windows ends the process while the worker thread is inside the converter. Item 93 expects 0; a crash code is recorded as this observation, and the item is run once more in a new folder (Task 7 Step 4). Added to the spec's Risks.
12. **Item 93 (spec 9i)** sends `WM_QUERYENDSESSION` after the switch away: the query returns 0 at once (refused), the app keeps running and the D2 box follows.
13. **Item 91 shows the out-of-scope case too:** the default document `new` (not pending, empty braille, no cache after a restart) still exports the "No conversion data" page, before and after F-9 (spec Out of Scope, first item).
14. **Before F-9, a second conversion during a long one crashes the app** (measured; the spec's "Before" for 9e and 9f expected one "Export Complete" box). The superseding job starts a second worker thread while the first still converts, so two liblouis conversions run at once; with the long texts of items 89 and 90, N-f8b2 ended without any box every time (four of four runs; Windows' Application log: `ntdll.dll`, exception `0xc0000374`). The spec's unit probes 2 and 3 used fake threads and could not show this. F-9's queue runs one job at a time, so the after-logs show both boxes. The item scripts report such an end deterministically (`the app has ended by itself, exit code nonzero: True`) and read only files after it.

## Dry Run

The plan was executed on scratch clones of the repository at the spec commit `a39d207` with a stand-in plan commit (this plan and the corrected spec files) on `fix/f9-conversion-target-document` (`$SP/f9plan/r*`, never the worktree or the main checkout), by F-8b's harness: it writes every `File:` block, applies every `Edit:` block exactly once (CRLF-aware), runs every `bash` block from `client/` with `REPO` set to the clone and `MAIN` to the main checkout (so Task 0's guarded copies filled the clone, and the application-data check read the real data read-only), and compares its stdout with the following `text` block. Task 7 needs the desktop and is not part of the replay. The final replay (Tasks 0-6 from a fresh clone) matched every expected block, including all red runs, the catalog steps, the per-commit tree ids, the six shuffle seeds and the mutation output; no `client/log`, `client/workspace`, `client/dictionary` or `client/config.json` appeared in the clone. A second fresh clone ran Task 0 Step 3's bootstrap command and then applied every step with that `apply_blocks.py` (the catalog commands of Task 5 Steps 4-5 run as written), committing at the end of each task: the block counts of Task 0 Step 3 and the tree ids of the Expected Counts table.

Task 7 was run too. The second clone, at Task 5 (`HEAD:client` `2fffcc5e1cefbfe656061f1c477dcdaadd00115a`), was built with Task 7 Step 1's command (PyInstaller 6.21.0, "Build complete!" in 40 s, 48,767,328 bytes; the four changed modules and `gui.py` from the clone), and Task 7 Step 2's scripts, written by `apply_blocks.py`, ran with Step 3's loop against `D:\dxtest\N-f8b2\DotExpress.exe` and against that build, in `D:\dxtest\autodry*-f9` folders that were deleted afterwards (no folder of Step 3 exists yet). They printed exactly the logs of Step 4: eighteen logs, each item once on each build, no re-run. An earlier full run of the same scripts against an earlier build of the same clone gave the same logs, except that items 89 and 90 on N-f8b2 then stopped with a pywinauto error when the app ended (Spec Corrections 14); the scripts were changed to wait for the next box or the end of the process, and 89 and 90 on N-f8b2 gave identical logs in all three runs after that. Drafts of the scripts, run against a build of the development clone, found tool problems that were fixed before those runs: a path inside an error message is a repr inside a repr (masked in all three forms); the time a session message took and how often Enter had to be pressed depend on the machine, not on the app (shown as `within_2_s` and left out). No script wrote to the clipboard, and every key went to the main window while it was in the foreground. Item 94 (manual) was not run.

## Review Focus

1. **Where a manual result goes** (D1, D3): case (a) is today's path, event for event; case (b) touches neither the open document's editors, focus nor Dual View, writes the starting document through `save_document` (memory first, then the package unless unchanged) and shows the D2 box only after a successful save; case (c) and the guard discard and log (B1-B6, E1-E4, E13, E14; 14 mutants; GUI 85-88).
2. **The queue** (D4, D5): one job at a time, FIFO, requests built at submit time, nothing starts during a completion (`_completing`), the drain in `finally`; `is_running()` covers the delivery gap and the queue; with no overlap every event is as before (B7-B13, E5-E8, E10; 6 mutants; GUI 89, 90, 92).
3. **HTML export of a pending document** uses the fresh segments and changes neither the cache nor the document (B15, C1-C3, E9; 3 mutants; GUI 91).
4. **Worker errors and the closed window** (D7, D8): every exception is delivered once and logged; after `shutdown()` nothing reaches the view (A1, A2, B14, E11, E12; 7 mutants; GUI 92, 93).
5. **Catalogs and strings:** one msgid, 369 translated, 0 fuzzy; `{name}` is `python-brace-format` (F1).
6. **The observations of Spec Corrections 11 and 14** (a crash code at `WM_ENDSESSION` during a conversion, pre-existing; the before build crashing on two conversions at once, fixed by the queue).

## File Map

- Task 1: `client/tests/test_conversion_jobs.py` (log isolation; A1 flipped, A2); `client/conversion/jobs.py` (`_run_job`, `log` import).
- Task 2: `client/tests/test_conversion_presenter.py` (`_export_callbacks`, B15), `client/tests/test_export_coordinator.py` (`_segment`, C1-C3, three `on_success` calls), `client/tests/test_gui_document_flows.py` (E9); `client/documents/export_coordinator.py` (`ExportConversions`, `write_document`, `export_document`, `_write_single`, `_export_next`, module docstring), `client/ui/conversion_presenter.py` (`_ExportCallbacks`, `convert_for_export`, `_on_job_success`).
- Task 3: `client/tests/test_conversion_presenter.py` (B7 flipped, B8-B13, the live-state test), `client/tests/test_gui_document_flows.py` (E5 and E8 flipped, E6, E7, E10, helpers); `client/ui/conversion_presenter.py` (`_Job`, `_ActiveJob`, `_queue`, `_completing`, `is_running`, `_submit`, `_start`, `_finish_completion`, the completions, module docstring).
- Task 4: `client/tests/test_conversion_presenter.py` (B14), `client/tests/test_gui_document_flows.py` (E11, E12, the delegation test); `client/ui/conversion_presenter.py` (`shutdown`, `_shut_down`, module docstring), `client/gui.py` (`_finish_close`).
- Task 5: `client/tests/test_conversion_presenter.py` (log isolation, the view's `save_converted_document`, B1-B6), `client/tests/test_workspace_service.py` (D1-D5), `client/tests/test_gui_document_flows.py` (E1 flipped, E2-E4, E13, E14), `client/tests/test_i18n.py` (F1); `client/ui/conversion_presenter.py` (`ConversionView.save_converted_document`, `_ManualTarget`, `convert`, `_complete_manual`, `_discard`, module docstring), `client/documents/workspace_service.py` (`save_document`, `save_open_document`, module docstring), `client/gui.py` (`save_converted_document`); the three catalogs.
- Task 7: `docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/` (`auto/f9gui.py`, `auto/item85.py`, `auto/item89.py`, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | msgids | `HEAD:client` |
| --- | --- | --- | --- | --- | --- |
| baseline (`7aba2be` + spec + plan) | - | 1444 | `FAILED (errors=1, skipped=7)` | 368 | `f6bd18c91dd1ccf78ff1c6d248f31df000d7337b` |
| 1 worker errors | 1 (A) | 1445 | `FAILED (errors=1, skipped=7)` | 368 | `503c9ef194f991d73a3a9dd1db0041207d87e2f8` |
| 2 pending HTML | 5 (B15, C, E9) | 1450 | `FAILED (errors=1, skipped=7)` | 368 | `1635c4957f0cc2f4c12fcbd02c2a8f4a1c0e60c6` |
| 3 queue | 9 (B8-B13, E6, E7, E10) | 1459 | `FAILED (errors=1, skipped=7)` | 368 | `c1207cf754c19df5b7c59498e397e969aff00ce4` |
| 4 close | 2 (B14, E11) | 1461 | `FAILED (errors=1, skipped=7)` | 368 | `abd8058bfcc39543393b0edd7e5e18339601d754` |
| 5 starting document | 17 (B1-B6, D, E2-E4, E13, E14, F1) | 1478 | `FAILED (errors=1, skipped=7)` | 369 | `2fffcc5e1cefbfe656061f1c477dcdaadd00115a` |
| 7 GUI results (docs only) | - | 1478 | `FAILED (errors=1, skipped=7)` | 369 | `2fffcc5e1cefbfe656061f1c477dcdaadd00115a` |

The error is F-W6 throughout; the 7 skips are POSIX-only tests. The spec's acceptance-criterion-2 set goes from `Ran 330`, `OK` to `Ran 363`, `OK`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 by the block script: `brief.py` (F-8b's, which also masks object addresses), `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` (unchanged), `mo_check.py` (listing the F-9 msgid), `f9_mutants.py` (30 mutants of the code after Task 5, run on a copy of `client/`; the repository is never changed) and `apply_blocks.py` (F-8b's, applies the `File:` and `Edit:` blocks of one step of this plan).

---

### Task 0: Baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short -- client docs scripts
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO rev-parse HEAD~1 HEAD~2 HEAD~2:client
git -C $REPO diff --stat 7aba2be -- client
```

Expected (`status` and the diff print nothing; `HEAD~1` is the spec commit, `HEAD~2` is `main` at `7aba2be`):

```text
docs: plan for writing conversion results to the document they came from (F-9)
fix/f9-conversion-target-document
a39d207b980dfefe4b42c3f2cfee2ff4fd8d5435
7aba2be866cd0a380c41203b7c9e7a0d698caaf0
f6bd18c91dd1ccf78ff1c6d248f31df000d7337b
```

- [ ] **Step 2: The git-ignored runtime the tests load.** The worktree already has the generated liblouis DLL and tables, `louis_helper.py`, MathCAT and the submodule's `configure.ac` (copied when it was made); the guarded copies below do nothing there (they filled the dry run's scratch clones, as F-3's Task 0 did). Never stage these files.

```bash
test -e $REPO/client/braille/liblouis.dll || cp $MAIN/client/braille/liblouis.dll $REPO/client/braille/
test -e $REPO/client/braille/louis_helper.py || cp $MAIN/client/braille/louis_helper.py $REPO/client/braille/
test -e $REPO/client/braille/liblouis || cp -r $MAIN/client/braille/liblouis $REPO/client/braille/liblouis
test -e $REPO/client/mathcat || cp -r $MAIN/client/mathcat $REPO/client/mathcat
test -e $REPO/include/liblouis/configure.ac || { mkdir -p $REPO/include/liblouis && cp $MAIN/include/liblouis/configure.ac $REPO/include/liblouis/; }
for f in client/braille/liblouis.dll client/braille/louis_helper.py client/braille/liblouis/tables client/mathcat/assets include/liblouis/configure.ac; do test -e $REPO/$f && echo "present: $f"; done
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
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
louis_helper.py is the vendored file
```

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed). `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` are F-8b's, unchanged; `brief.py` is F-8b's and also masks object addresses; `mo_check.py` lists the F-9 msgid; `apply_blocks.py` is F-8b's with its docstring naming this plan.

File: `$T/tools/brief.py`

````python
"""Condense unittest output read from stdin (throwaway, not committed).

Keeps the FAIL/ERROR headers and exception lines, cut to 160 characters (a cut line is
printed once, so the subtests of one test give one header), the "Ran" line without its
timing and the final OK/FAILED line, so that outputs can be compared with the plan. The
client directory is shown as <client>; temporary directories (tempfile.mkdtemp names,
also in repr form with doubled backslashes) as <tmp>; random temporary-file suffixes as
<rnd>; object addresses (the frame's repr in a message-box event, F-9) as <addr>, also
when unittest's diff has cut the repr down to its last characters.
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
seen = set()
for line in sys.stdin:
    line = line.rstrip("\n").replace(CLIENT_REPR, "<client>").replace(CLIENT, "<client>")
    line = TMPDIR.sub("<tmp>", line)
    line = RANDOM_TMP.sub(r"\1<rnd>\2", line)
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
the msgid that F-9 adds (msgfmt 0.23 leaves POT-Creation-Date out of the .mo header, so
the .mo does not depend on it). A msgid the catalog does not hold prints as "(missing)".
Output is UTF-8 (-I ignores PYTHONIOENCODING).
"""
import gettext
import sys

sys.stdout.reconfigure(encoding="utf-8")

MSGIDS = ('Conversion completed. The result was saved to document "{name}".',)

with open(sys.argv[1], "rb") as stream:
    catalog = gettext.GNUTranslations(stream)
print("catalog keys:", len(catalog._catalog))
for msgid in MSGIDS:
    translated = catalog._catalog.get(msgid, "(missing)")
    print(f"{msgid!r} -> {translated}")
````

File: `$T/tools/f9_mutants.py`

````python
"""Run the F-9 tests against deliberately broken code (throwaway, not committed).

Usage: python f9_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one file of the copy (one exact, unique replacement), runs the F-9 test
modules there, prints which tests caught it and restores the file. The repository is
never changed. Matches the code after Task 5. Exit status 1 if a mutant is not caught or
its pattern is not found exactly once. Python runs with -B (no bytecode is written): a
restored file can have the size and modification second of the mutant, and a cached
.pyc would then shadow it.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

GUI = "gui.py"
JOBS = "conversion/jobs.py"
PRESENTER = "ui/conversion_presenter.py"
SERVICE = "documents/workspace_service.py"
COORDINATOR = "documents/export_coordinator.py"
SAVE_CALL = "        if self._view.save_converted_document(Document(document.name, document.text, braille)):\n"
MUTANTS = {
	# D1-D3: the document that started the conversion.
	"result-to-the-open-document": (PRESENTER, "        if target.document_name == open_name:\n", "        if True:\n"),
	"memory-only-no-write": (
		PRESENTER,
		SAVE_CALL,
		"        self._documents.replace_document(Document(document.name, document.text, braille))\n        if True:\n",
	),
	"open-document-also-written": (
		PRESENTER,
		"                    self._documents.replace_document(Document(document.name, self._view.get_source_text(), braille))\n",
		"                    self._documents.replace_document(Document(document.name, self._view.get_source_text(), braille))\n"
		"                    self._view.save_converted_document(Document(document.name, self._view.get_source_text(), braille))\n",
	),
	"other-document-shows-the-output": (
		PRESENTER,
		"        self._documents.set_dual_view_results(document.name, output.dual_view_segments)\n",
		"        self._documents.set_dual_view_results(document.name, output.dual_view_segments)\n"
		"        self._view.show_conversion_output(braille)\n",
	),
	"other-document-refreshes-the-dual-view": (
		PRESENTER,
		"        self._documents.set_dual_view_results(document.name, output.dual_view_segments)\n",
		"        self._documents.set_dual_view_results(document.name, output.dual_view_segments)\n"
		"        self._view.refresh_dual_view()\n",
	),
	"editor-text-stored": (
		PRESENTER,
		SAVE_CALL,
		"        if self._view.save_converted_document(Document(document.name, self._view.get_source_text(), braille)):\n",
	),
	"no-text-guard": (PRESENTER, "        if document.text != target.source_text:\n", "        if False:\n"),
	"no-cache-for-the-starting-document": (
		PRESENTER,
		"        self._documents.set_dual_view_results(document.name, output.dual_view_segments)\n",
		"",
	),
	"old-completion-message": (
		PRESENTER,
		"""                _('Conversion completed. The result was saved to document "{name}".').format(name=document.name),\n""",
		"""                _("Conversion completed."),\n""",
	),
	"discard-not-logged": (
		PRESENTER,
		'        get_logger("dotexpress.gui", "gui.log").error("Discarded a conversion result: %s", reason)\n',
		"        pass\n",
	),
	"result-given-to-a-document-opened-later": (
		PRESENTER,
		"        if target.document_name is None:\n            self._discard(",
		"        if target.document_name is None and False:\n            self._discard(",
	),
	"save-document-applies-the-pending-rule": (
		SERVICE,
		"        updated_document = _encodable(document)\n",
		"        updated_document = prepare_document_for_save(\n"
		"            self._controller.get_document(document.name), text=document.text, braille=document.braille or \"\"\n"
		"        )\n",
	),
	"save-document-always-writes": (
		SERVICE,
		"        if self._is_saved(updated_document):\n            return updated_document\n        save_document_package(",
		"        save_document_package(",
	),
	"frame-save-error-not-reported": (
		GUI,
		"\t\t\tself._workspace_service.save_document(document)\n\t\texcept Exception as exc:\n\t\t\tself._show_document_save_error(exc)\n",
		"\t\t\tself._workspace_service.save_document(document)\n\t\texcept Exception as exc:\n\t\t\tpass\n",
	),
	# D4, D5: the queue.
	"export-replaces-the-running-job": (
		PRESENTER,
		"        if self._active is not None or self._completing or self._queue:\n",
		"        if False:\n",
	),
	"lifo": (PRESENTER, "            job = self._queue.popleft()\n", "            job = self._queue.pop()\n"),
	"drain-outside-finally": (
		PRESENTER,
		"                self._complete_manual(active.job.manual, output)\n        finally:\n            self._finish_completion()\n",
		"                self._complete_manual(active.job.manual, output)\n            self._finish_completion()\n        finally:\n"
		"            self._completing = False\n",
	),
	"completing-not-consulted": (
		PRESENTER,
		"        if self._active is not None or self._completing or self._queue:\n",
		"        if self._active is not None or self._queue:\n",
	),
	"is-running-is-the-thread-state": (
		PRESENTER,
		"        return self._active is not None or bool(self._queue)\n",
		"        return self._runner.is_running()\n",
	),
	"is-running-ignores-the-queue": (
		PRESENTER,
		"        return self._active is not None or bool(self._queue)\n",
		"        return self._active is not None\n",
	),
	# D8: the window closes.
	"shutdown-keeps-the-queue": (PRESENTER, "        self._active = None\n        self._queue.clear()\n", "        self._active = None\n"),
	"shutdown-keeps-the-timer": (
		PRESENTER,
		"        if self._timer is not None:\n            self._timer.Stop()\n            self._timer = None\n        self._active = None\n",
		"        self._active = None\n",
	),
	"timer-after-shutdown-shows-the-dialog": (
		PRESENTER,
		"        if self._shut_down or job_id != self._runner.active_job_id:\n",
		"        if job_id != self._runner.active_job_id:\n",
	),
	"jobs-start-after-shutdown": (PRESENTER, "        if self._shut_down:\n            return\n", ""),
	"close-does-not-shut-down": (GUI, "\t\tself._conversion_presenter.shutdown()\n", ""),
	# D6: HTML export of a pending document.
	"single-export-ignores-the-fresh-segments": (
		COORDINATOR,
		"                    format_key,\n                    dual_view_results=output.dual_view_segments,\n",
		"                    format_key,\n",
	),
	"export-all-ignores-the-fresh-segments": (
		COORDINATOR,
		"                Document(document.name, document.text, output.display_text),\n                dual_view_results=output.dual_view_segments,\n",
		"                Document(document.name, document.text, output.display_text),\n",
	),
	"export-writes-the-cache": (
		COORDINATOR,
		"        context = ExportContext(dual_view_results=dual_view_results)\n",
		"        self._documents.set_dual_view_results(document.name, dual_view_results)\n"
		"        context = ExportContext(dual_view_results=dual_view_results)\n",
	),
	# D7: the runner.
	"runner-catches-exception-only": (JOBS, "\t\texcept BaseException as error:\n", "\t\texcept Exception as error:\n"),
	"runner-does-not-log": (
		JOBS,
		'\t\t\tget_logger("dotexpress.gui", "gui.log").error("Unexpected error in a conversion job", exc_info=error)\n',
		"",
	),
}
MODULES = (
	"tests.test_conversion_jobs",
	"tests.test_conversion_presenter",
	"tests.test_export_coordinator",
	"tests.test_workspace_service",
	"tests.test_gui_document_flows",
)
IGNORE = shutil.ignore_patterns(".venv", "log", "dictionary", "workspace", "build", "dist", "config.json", "__pycache__")
FAILED = re.compile(r"^(?:FAIL|ERROR): (\w+) \(([\w.]+)\)", re.M)


def main() -> int:
	client_dir, scratch_dir, *selected = sys.argv[1:]
	copy = Path(scratch_dir) / "client"
	if copy.exists():
		shutil.rmtree(copy)
	shutil.copytree(client_dir, copy, ignore=IGNORE)
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
"""Apply the File: and Edit: blocks of one step of the F-9 plan (throwaway, not committed).

Usage: python apply_blocks.py <plan.md> <repo> <T> "<task>" "<step>"
  for example: python apply_blocks.py plan.md D:/workspace/DotExpress-f9 <T> "Task 1" "Step 1"

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
PLAN=$REPO/docs/superpowers/plans/2026-10-10-f9-conversion-target-document.md
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
wrote $T/tools/f9_mutants.py
wrote $T/tools/apply_blocks.py
7 blocks applied (Task 0, Step 3)
```

From then on apply every step's blocks with `apply_blocks.py`, for example `$PY $T/tools/apply_blocks.py ../docs/superpowers/plans/2026-10-10-f9-conversion-target-document.md $REPO $T "Task 1" "Step 1"`; it prints `N blocks applied` (Task 0 Step 3: 7; Task 1 Step 1: 2, Step 2: 2; Task 2 Step 1: 10, Step 2: 11; Task 3 Step 1: 7, Step 2: 6; Task 4 Step 1: 4, Step 2: 5; Task 5 Step 1: 12, Step 2: 12, Step 5: 1; Task 7 Step 2: 3).

- [ ] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, catalogs, tree, application data.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_conversion_jobs tests.test_conversion_presenter tests.test_export_coordinator tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "msgfmt rebuilds the committed .mo byte for byte"
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO rev-parse HEAD:client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) > $T/app-data.sha256; wc -l < $T/app-data.sha256
for f in log workspace config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application data checked"
```

Expected (the second `Ran` line is the spec's acceptance-criterion-2 set; the F-9 msgid is missing; the number after the tree id counts the files of the user's application data in the main checkout, including `client/log/`, recorded read-only for Task 6; if the user has used the app since the dry run, that number differs, which is fine; the worktree has no application data):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1444 tests
FAILED (errors=1, skipped=7)
Ran 330 tests
OK
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
source msgids: 368 sha256 c3fe6aa121698c16ef9b3bab6671f995f4648003c59912b1f1b2f82c754da7c5
locales/dotexpress.pot:369
locales/zh_TW/LC_MESSAGES/dotexpress.po:369
368 translated messages.
msgfmt rebuilds the committed .mo byte for byte
catalog keys: 369
'Conversion completed. The result was saved to document "{name}".' -> (missing)
f6bd18c91dd1ccf78ff1c6d248f31df000d7337b
4
worktree application data checked
```

### Task 1: Deliver every conversion worker error as a failure (D7)

- [ ] **Step 1: Red: Test Plan A; log isolation.** `test_conversion_jobs.py` (tabs) gets a `setUpModule` that isolates `dotexpress.gui`; `test_exception_outside_conversion_stage_error_delivers_nothing` (the KNOWN BUG pin of P1-4 defect 6) becomes A1, and A2 is new. Both share a helper that checks one delivered failure (stage `translation`, the same error object), no running thread and one log line with `exc_info`.

Edit: `client/tests/test_conversion_jobs.py`

```python
from config import DEFAULT_CHARSET_MAPS
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from tests.conversion_harness import FakeThread, make_thread_factory


class ConversionJobRunnerTest(unittest.TestCase):
```

```python
from config import DEFAULT_CHARSET_MAPS
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from tests.conversion_harness import FakeThread, make_thread_factory
from tests.file_log_isolation import isolate_file_logs

LOGGER = "dotexpress.gui"


def setUpModule() -> None:
	# The runner logs an unexpected worker error to gui.log (F-9 D7); keep the real file out of it.
	unittest.addModuleCleanup(isolate_file_logs(LOGGER))


class ConversionJobRunnerTest(unittest.TestCase):
```

Edit: `client/tests/test_conversion_jobs.py`

```python
		self.assertTrue(runner.is_running())
		self.assertEqual(runner.active_job_id, 2)

	def test_exception_outside_conversion_stage_error_delivers_nothing(self) -> None:
		def converter(_request, *, runtime):
			raise RuntimeError("unexpected")

		runner, successes, failures, threads = self.make_runner(converter=converter)

		runner.start(self.make_request())
		# KNOWN BUG (P1-4 spec, defect 6): nothing is delivered, so the UI would stay busy.
		with self.assertRaisesRegex(RuntimeError, "unexpected"):
			threads[0].run()

		self.assertEqual((successes, failures), ([], []))
		self.assertFalse(runner.is_running())
		self.assertEqual(runner.active_job_id, 1)


	def test_results_carry_only_the_job_id_and_the_outcome(self) -> None:
```

```python
		self.assertTrue(runner.is_running())
		self.assertEqual(runner.active_job_id, 2)

	def _assert_unexpected_error_is_delivered(self, error: BaseException) -> None:
		def converter(_request, *, runtime):
			raise error

		runner, successes, failures, threads = self.make_runner(converter=converter)

		job_id = runner.start(self.make_request())
		with self.assertLogs(LOGGER, level="ERROR") as logs:
			threads[0].run()

		self.assertEqual(successes, [])
		self.assertEqual(len(failures), 1)
		self.assertEqual(failures[0].job_id, job_id)
		self.assertEqual(failures[0].error.stage, "translation")
		self.assertIs(failures[0].error.error, error)
		self.assertFalse(runner.is_running())
		self.assertEqual([record.getMessage() for record in logs.records], ["Unexpected error in a conversion job"])
		self.assertIs(logs.records[0].exc_info[1], error)

	def test_unexpected_worker_error_is_delivered_as_a_translation_failure(self) -> None:
		# Was the P1-4 KNOWN BUG (defect 6), fixed by F-9 (D7): the error escaped the thread
		# and nothing was delivered, so the UI stayed busy.
		self._assert_unexpected_error_is_delivered(RuntimeError("unexpected"))

	def test_base_exception_in_the_worker_is_delivered_too(self) -> None:
		# A SystemExit in a worker thread would also leave the UI busy (F-9 D7).
		self._assert_unexpected_error_is_delivered(SystemExit("x"))


	def test_results_carry_only_the_job_id_and_the_outcome(self) -> None:
```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_jobs 2>&1 | $PY $T/tools/brief.py
```

Expected (both errors escape the worker thread, as the spec's probe 5 found):

```text
ERROR: test_base_exception_in_the_worker_is_delivered_too (tests.test_conversion_jobs.ConversionJobRunnerTest.test_base_exception_in_the_worker_is_delivered_too
SystemExit: x
ERROR: test_unexpected_worker_error_is_delivered_as_a_translation_failure (tests.test_conversion_jobs.ConversionJobRunnerTest.test_unexpected_worker_error_is_de
RuntimeError: unexpected
Ran 10 tests
FAILED (errors=2)
```

- [ ] **Step 2: Green: the runner delivers and logs anything else** (`client/conversion/jobs.py`, tabs). The logger is bound when an error is logged (as F-6 review M-6 and F-7 D6 do).

Edit: `client/conversion/jobs.py`

```python
	ConversionStageError,
	convert_text_with_alignment,
)


@dataclass(frozen=True)
```

```python
	ConversionStageError,
	convert_text_with_alignment,
)
from log import get_logger


@dataclass(frozen=True)
```

Edit: `client/conversion/jobs.py`

```python
				ConversionJobFailure(job_id=job_id, error=error),
			)
			return
		self._call_after(
			self._deliver_success,
			ConversionJobSuccess(job_id=job_id, conversion_output=conversion_output),
```

```python
				ConversionJobFailure(job_id=job_id, error=error),
			)
			return
		except BaseException as error:
			# Anything else is a bug; it is delivered as a translation failure so that the
			# busy state ends and the next queued job can start (F-9 D7). The logger is bound
			# here, not at import (as in F-6 review M-6).
			get_logger("dotexpress.gui", "gui.log").error("Unexpected error in a conversion job", exc_info=error)
			self._call_after(
				self._deliver_failure,
				ConversionJobFailure(job_id=job_id, error=ConversionStageError("translation", error)),
			)
			return
		self._call_after(
			self._deliver_success,
			ConversionJobSuccess(job_id=job_id, conversion_output=conversion_output),
```

- [ ] **Step 3: Green: the module, the presenter, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_jobs -v 2>&1 | grep -E "^test_(unexpected_worker_error_is_delivered_as_a_translation_failure|base_exception_in_the_worker_is_delivered_too) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_jobs tests.test_conversion_presenter 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_base_exception_in_the_worker_is_delivered_too ok
test_unexpected_worker_error_is_delivered_as_a_translation_failure ok
Ran 29 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1445 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/conversion/jobs.py client/tests/test_conversion_jobs.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: deliver every conversion worker error as a failure (F-9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/conversion/jobs.py            | 11 +++++++++++
 client/tests/test_conversion_jobs.py | 35 ++++++++++++++++++++++++++++-------
 2 files changed, 39 insertions(+), 7 deletions(-)
503c9ef194f991d73a3a9dd1db0041207d87e2f8
```

### Task 2: Export pending documents as HTML with their own conversion (D6)

- [ ] **Step 1: Red: B15, C1-C3, E9; the callbacks that take the output.** `test_conversion_presenter.py`: `_export_callbacks` records `output.display_text`, and B15 checks that `on_success` gets the very `ConversionOutput`. `test_export_coordinator.py`: a `_segment` helper, C3 next to the `write_document` tests, C1 after the pending single-export tests, C2 at the end of `ExportCoordinatorTest`, and the three tests that call a stored `on_success` pass a `ConversionOutput`. `test_gui_document_flows.py`: E9 after the pending single-export tests. All three files use 4 spaces.

Edit: `client/tests/test_conversion_presenter.py`

```python

    def _export_callbacks(self) -> dict:
        return {
            "on_success": lambda braille: self.events.append(("on_success", braille)),
            "on_error": lambda message: self.events.append(("on_error", message)),
        }

```

```python

    def _export_callbacks(self) -> dict:
        return {
            "on_success": lambda output: self.events.append(("on_success", output.display_text)),
            "on_error": lambda message: self.events.append(("on_error", message)),
        }

```

Edit: `client/tests/test_conversion_presenter.py`

```python
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("manual",)})

    def test_export_failure_calls_only_on_error(self) -> None:
        self.outputs["doc text"] = ConversionStageError("ascii", RuntimeError("bad map"))
        presenter = self._presenter()
```

```python
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("manual",)})

    def test_export_success_receives_the_conversion_output(self) -> None:
        # F-9 D6: the export gets the whole output, so a pending document's HTML export can use
        # the fresh dual-view segments.
        output = ConversionOutput("⠙", ("result",), ("export-segment",))
        self.outputs["doc text"] = output
        received: list = []
        presenter = self._presenter()
        presenter.convert_for_export("doc text", on_success=received.append, on_error=self.fail)
        self.threads[0].run()

        self.calls.run_next()

        self.assertEqual(len(received), 1)
        self.assertIs(received[0], output)

    def test_export_failure_calls_only_on_error(self) -> None:
        self.outputs["doc text"] = ConversionStageError("ascii", RuntimeError("bad map"))
        presenter = self._presenter()
```

Edit: `client/tests/test_export_coordinator.py`

```python
def setUpModule() -> None:
    # The coordinator logs unexpected export errors to gui.log (F-7); keep the real file out of it.
    unittest.addModuleCleanup(isolate_file_logs(LOGGER))


def _writer_failing_for(name: str, error: Exception):
```

```python
def setUpModule() -> None:
    # The coordinator logs unexpected export errors to gui.log (F-7); keep the real file out of it.
    unittest.addModuleCleanup(isolate_file_logs(LOGGER))


def _segment(raw: str, braille: str) -> DualViewSegment:
    """One dual-view segment showing ``raw`` above ``braille``."""
    return DualViewSegment(
        result=SimpleNamespace(raw=[raw], braille=[braille], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
        source_kind="text",
    )


def _writer_failing_for(name: str, error: Exception):
```

Edit: `client/tests/test_export_coordinator.py`

```python

        writer.assert_called_once_with(Path("/tmp/beta.html"), Document("beta", "b", "⠃"), ExportContext())

    def test_write_document_rejects_non_exportable_format(self) -> None:
        descriptor = replace(get_format("txt"), writer=Mock())

```

```python

        writer.assert_called_once_with(Path("/tmp/beta.html"), Document("beta", "b", "⠃"), ExportContext())

    def test_write_document_uses_the_given_results_instead_of_the_cache(self) -> None:
        # F-9 D6: None reads the cache, as before; a tuple, even an empty one, is used as it is.
        self.documents.set_dual_view_results("alpha", ("alpha-cache",))
        document = Document("alpha", "text", "braille")
        for given, expected in ((None, ("alpha-cache",)), ((), ()), (("fresh",), ("fresh",))):
            with self.subTest(given=given):
                writer = Mock()
                descriptor = replace(get_format("html"), writer=writer)
                with patch.object(coordinator_module, "get_format", return_value=descriptor):
                    self.coordinator.write_document(Path("/tmp/alpha.html"), document, "html", dual_view_results=given)

                writer.assert_called_once_with(Path("/tmp/alpha.html"), document, ExportContext(dual_view_results=expected))

        self.coordinator.write_document(self.root / "alpha.html", document, "html", dual_view_results=())
        self.assertIn("No conversion data", (self.root / "alpha.html").read_text(encoding="utf-8"))

    def test_write_document_rejects_non_exportable_format(self) -> None:
        descriptor = replace(get_format("txt"), writer=Mock())

```

Edit: `client/tests/test_export_coordinator.py`

```python
            self._take()
            on_success, _on_error = self.conversions.started[0]
            with self.assertLogs(LOGGER, level="ERROR") as logs:
                on_success("⠃⠃")

        self.assertEqual(
            self._take(),
```

```python
            self._take()
            on_success, _on_error = self.conversions.started[0]
            with self.assertLogs(LOGGER, level="ERROR") as logs:
                on_success(ConversionOutput("⠃⠃", ()))

        self.assertEqual(
            self._take(),
```

Edit: `client/tests/test_export_coordinator.py`

```python
        self.assertEqual(self._written(), {})

        on_success, _on_error = self.conversions.started[0]
        on_success("⠃⠃")

        self.assertEqual(self._take(), [self._exported()])
        self.assertEqual(self._written(), {"beta.brl": "⠃⠃"})
```

```python
        self.assertEqual(self._written(), {})

        on_success, _on_error = self.conversions.started[0]
        on_success(ConversionOutput("⠃⠃", ()))

        self.assertEqual(self._take(), [self._exported()])
        self.assertEqual(self._written(), {"beta.brl": "⠃⠃"})
```

Edit: `client/tests/test_export_coordinator.py`

```python
            ],
        )
        self.assertEqual(self.conversions.started, [])

    # --- export_all ----------------------------------------------------------------

```

```python
            ],
        )
        self.assertEqual(self.conversions.started, [])

    def test_html_export_of_a_pending_document_uses_its_conversion(self) -> None:
        # Was P1-4 defect 3 (task.md #11): the cache, empty for a pending document, gave the
        # "No conversion data" page (F-9 D6).
        self.view.paths.append(self.root / "beta.html")
        self.coordinator.export_document(Document("beta", "b", None), "html")
        self._take()

        on_success, _on_error = self.conversions.started[0]
        on_success(ConversionOutput("⠃", ("result",), (_segment("fresh-b", "⠃"),)))

        self.assertEqual(self._take(), [self._exported()])
        html = (self.root / "beta.html").read_text(encoding="utf-8")
        self.assertIn('<span class="source">fresh-b</span>', html)
        self.assertNotIn("No conversion data", html)
        self.assertEqual(self.documents.dual_view_results_by_document, {})
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", None))

    # --- export_all ----------------------------------------------------------------

```

Edit: `client/tests/test_export_coordinator.py`

```python
        self.assertEqual(self.calls.pending, [])

        on_success, _on_error = self.conversions.started[0]
        on_success("⠃")
        self.assertEqual(self._take(), [("call_after",)])
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "beta.brl": "⠃"})

```

```python
        self.assertEqual(self.calls.pending, [])

        on_success, _on_error = self.conversions.started[0]
        on_success(ConversionOutput("⠃", ()))
        self.assertEqual(self._take(), [("call_after",)])
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "beta.brl": "⠃"})

```

Edit: `client/tests/test_export_coordinator.py`

```python
        self.assertEqual([record.getMessage() for record in logs.records], ["Unexpected error while exporting a document"])
        self.assertIs(logs.records[0].exc_info[1], error)


class ExportThroughConversionPresenterTest(unittest.TestCase):
    def test_export_all_with_a_real_presenter_turn_by_turn(self) -> None:
```

```python
        self.assertEqual([record.getMessage() for record in logs.records], ["Unexpected error while exporting a document"])
        self.assertIs(logs.records[0].exc_info[1], error)

    def test_export_all_html_uses_each_pending_documents_conversion(self) -> None:
        # F-9 D6: each pending document gets its own fresh segments; a converted one keeps its cache.
        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", None), Document("gamma", "g", None)]
        self.documents.set_dual_view_results("alpha", (_segment("cached-a", "⠁"),))
        self.view.directories.append(self.root)

        self.coordinator.export_all("html")
        self.calls.run_next()
        self.conversions.started[0][0](ConversionOutput("⠃", (), (_segment("fresh-b", "⠃"),)))
        self.calls.run_next()
        self.conversions.started[1][0](ConversionOutput("⠛", (), (_segment("fresh-g", "⠛"),)))
        self.calls.run_next()

        self.assertEqual(self._take()[-1], self._all_exported())
        for name, source in (("alpha", "cached-a"), ("beta", "fresh-b"), ("gamma", "fresh-g")):
            with self.subTest(name=name):
                html = (self.root / f"{name}.html").read_text(encoding="utf-8")
                self.assertIn(f'<span class="source">{source}</span>', html)
                self.assertNotIn("No conversion data", html)
        self.assertEqual(list(self.documents.dual_view_results_by_document), ["alpha"])


class ExportThroughConversionPresenterTest(unittest.TestCase):
    def test_export_all_with_a_real_presenter_turn_by_turn(self) -> None:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(len(self.timers.timers), 1)
        self.assertFalse(target.exists())

    # --- Export All ----------------------------------------------------------

    def test_export_all_mixed_documents_turn_by_turn(self) -> None:
```

```python
        self.assertEqual(len(self.timers.timers), 1)
        self.assertFalse(target.exists())

    def test_pending_html_export_through_the_frame_shows_the_conversion(self) -> None:
        # Was P1-4 defect 3 (task.md #11): the "No conversion data" page (F-9 D6).
        frame = self._make_frame([Document("alpha", "alpha text", None)], "alpha")
        target = self.export_dir / "alpha.html"
        self.export_paths.append(target)
        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ("result",), (_dual_view_segment("fresh-a", "⠁⠁"),))

        frame.on_export_document("html")
        self.threads[0].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(self._take(), [("timer.Stop", 1)] + self._busy(False) + [self._exported(frame)])
        html = target.read_text(encoding="utf-8")
        self.assertIn('<span class="source">fresh-a</span>', html)
        self.assertNotIn("No conversion data", html)
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {})
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "alpha text", None)])
        self.assertEqual(frame.output_txt.value, "")

    # --- Export All ----------------------------------------------------------

    def test_export_all_mixed_documents_turn_by_turn(self) -> None:
```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_export_coordinator tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (the presenter still passes `display_text`, so the callbacks that read `output.display_text` raise and B15 gets a string; the coordinator has no `dual_view_results` parameter and writes the cache, so the HTML files show the "No conversion data" page; the pending BRL tests get a `ConversionOutput` where a string was):

```text
ERROR: test_export_success_calls_only_on_success (tests.test_conversion_presenter.ConversionPresenterTest.test_export_success_calls_only_on_success)
AttributeError: 'str' object has no attribute 'display_text'
ERROR: test_later_job_uses_its_own_completion (tests.test_conversion_presenter.ConversionPresenterTest.test_later_job_uses_its_own_completion)
ERROR: test_superseded_job_delivers_nothing (tests.test_conversion_presenter.ConversionPresenterTest.test_superseded_job_delivers_nothing)
ERROR: test_write_document_uses_the_given_results_instead_of_the_cache (tests.test_export_coordinator.ExportCoordinatorTest.test_write_document_uses_the_given_r
TypeError: ExportCoordinator.write_document() got an unexpected keyword argument 'dual_view_results'
FAIL: test_export_success_receives_the_conversion_output (tests.test_conversion_presenter.ConversionPresenterTest.test_export_success_receives_the_conversion_ou
AssertionError: '⠙' is not ConversionOutput(display_text='⠙', translation_results=('result',), dual_view_segments=('export-segment',))
FAIL: test_export_all_html_uses_each_pending_documents_conversion (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_html_uses_each_pending_do
AssertionError: '<span class="source">fresh-b</span>' not found in '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" con
AssertionError: '<span class="source">fresh-g</span>' not found in '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" con
FAIL: test_export_all_runs_first_step_now_and_each_later_step_in_its_own_turn (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_runs_first_st
AssertionError: {'alpha.brl': '⠁'} != {'alpha.brl': '⠁', 'beta.brl': '⠃'}
FAIL: test_export_document_pending_converts_document_text_then_writes (tests.test_export_coordinator.ExportCoordinatorTest.test_export_document_pending_converts
AssertionError: Lists differ: [('show_error', '匯出文件失敗：write() argument must be [29 chars]錯誤')] != [('show_info', '文件已成功匯出。', '匯出完成')]
FAIL: test_html_export_of_a_pending_document_uses_its_conversion (tests.test_export_coordinator.ExportCoordinatorTest.test_html_export_of_a_pending_document_use
FAIL: test_pending_html_export_through_the_frame_shows_the_conversion (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_pending_html
AssertionError: '<span class="source">fresh-a</span>' not found in '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" con
Ran 251 tests
FAILED (failures=7, errors=7)
```

- [ ] **Step 2: Green: the output reaches the coordinator; `write_document` takes the fresh results** (`client/documents/export_coordinator.py` and `client/ui/conversion_presenter.py`, 4 spaces).

Edit: `client/documents/export_coordinator.py`

```python
folder, check conflicts, then one document per UI turn through ``call_after``, then
one summary). The view owns its dialogs and their texts; the coordinator owns the
outcome messages. The first Export All step runs in the caller's turn.

Every write failure is reported: an ``OSError`` by its message, anything else also with
its traceback in ``gui.log`` (F-7).
```

```python
folder, check conflicts, then one document per UI turn through ``call_after``, then
one summary). The view owns its dialogs and their texts; the coordinator owns the
outcome messages. The first Export All step runs in the caller's turn.

A pending document is written with its fresh conversion, dual-view segments included
(F-9); the export changes neither the document nor the dual-view cache.

Every write failure is reported: an ``OSError`` by its message, anything else also with
its traceback in ``gui.log`` (F-7).
```

Edit: `client/documents/export_coordinator.py`

```python
from pathlib import Path
from typing import Protocol

from documents.controller import DocumentController
from documents.export_results import ExportBatchResult
from documents.formats import DocumentFormatDescriptor, ExportContext, get_format
```

```python
from pathlib import Path
from typing import Protocol

from conversion.output import ConversionOutput
from documents.controller import DocumentController
from documents.export_results import ExportBatchResult
from documents.formats import DocumentFormatDescriptor, ExportContext, get_format
```

Edit: `client/documents/export_coordinator.py`

```python
        self,
        raw_text: str,
        *,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None: ...

```

```python
        self,
        raw_text: str,
        *,
        on_success: Callable[[ConversionOutput], None],
        on_error: Callable[[str], None],
    ) -> None: ...

```

Edit: `client/documents/export_coordinator.py`

```python
        self._conversions = conversions
        self._call_after = call_after

    def write_document(self, destination_path: Path, document: Document, format_key: str) -> None:
        descriptor = get_format(format_key)
        if not descriptor.exportable or descriptor.writer is None:
            raise ValueError(f'Unsupported export format: "{format_key}".')
        context = ExportContext(dual_view_results=self._documents.get_dual_view_results(document.name))
        descriptor.writer(destination_path, document, context)

    def export_document(self, document: Document, format_key: str) -> None:
```

```python
        self._conversions = conversions
        self._call_after = call_after

    def write_document(
        self,
        destination_path: Path,
        document: Document,
        format_key: str,
        *,
        dual_view_results: tuple[object, ...] | None = None,
    ) -> None:
        """Write ``document``; ``dual_view_results`` ``None`` means the document's cached ones (F-9 D6)."""
        descriptor = get_format(format_key)
        if not descriptor.exportable or descriptor.writer is None:
            raise ValueError(f'Unsupported export format: "{format_key}".')
        if dual_view_results is None:
            dual_view_results = self._documents.get_dual_view_results(document.name)
        context = ExportContext(dual_view_results=dual_view_results)
        descriptor.writer(destination_path, document, context)

    def export_document(self, document: Document, format_key: str) -> None:
```

Edit: `client/documents/export_coordinator.py`

```python
                return
            self._conversions.convert_for_export(
                document.text,
                on_success=lambda braille: self._write_single(
                    Document(document.name, document.text, braille),
                    destination_path,
                    format_key,
                ),
                on_error=lambda message: self._view.show_error(message, _("Error")),
            )
```

```python
                return
            self._conversions.convert_for_export(
                document.text,
                on_success=lambda output: self._write_single(
                    Document(document.name, document.text, output.display_text),
                    destination_path,
                    format_key,
                    dual_view_results=output.dual_view_segments,
                ),
                on_error=lambda message: self._view.show_error(message, _("Error")),
            )
```

Edit: `client/documents/export_coordinator.py`

```python
        if not isinstance(error, OSError):
            get_logger("dotexpress.gui", "gui.log").error("Unexpected error while exporting a document", exc_info=error)

    def _write_single(self, document: Document, destination_path: Path, format_key: str) -> None:
        try:
            self.write_document(destination_path, document, format_key)
        except Exception as exc:
            self._log_unexpected_export_error(exc)
            self._view.show_error(_("Failed to export document: {error}").format(error=exc), _("Error"))
```

```python
        if not isinstance(error, OSError):
            get_logger("dotexpress.gui", "gui.log").error("Unexpected error while exporting a document", exc_info=error)

    def _write_single(self, document: Document, destination_path: Path, format_key: str, **results: object) -> None:
        """Write and report one export; ``results`` is a pending export's ``dual_view_results`` (F-9 D6)."""
        try:
            self.write_document(destination_path, document, format_key, **results)
        except Exception as exc:
            self._log_unexpected_export_error(exc)
            self._view.show_error(_("Failed to export document: {error}").format(error=exc), _("Error"))
```

Edit: `client/documents/export_coordinator.py`

```python
        def continue_batch() -> None:
            self._call_after(self._export_next, rest, destination_dir, format_key, result)

        def write_document(export_document: Document) -> None:
            try:
                self.write_document(destination_path, export_document, format_key)
            except Exception as exc:
                self._log_unexpected_export_error(exc)
                result.add_failure(document.name, str(exc))
```

```python
        def continue_batch() -> None:
            self._call_after(self._export_next, rest, destination_dir, format_key, result)

        def write_document(export_document: Document, **results: object) -> None:
            try:
                self.write_document(destination_path, export_document, format_key, **results)
            except Exception as exc:
                self._log_unexpected_export_error(exc)
                result.add_failure(document.name, str(exc))
```

Edit: `client/documents/export_coordinator.py`

```python
            return
        self._conversions.convert_for_export(
            document.text,
            on_success=lambda braille: write_document(Document(document.name, document.text, braille)),
            on_error=conversion_failed,
        )

```

```python
            return
        self._conversions.convert_for_export(
            document.text,
            on_success=lambda output: write_document(
                Document(document.name, document.text, output.display_text),
                dual_view_results=output.dual_view_segments,
            ),
            on_error=conversion_failed,
        )

```

Edit: `client/ui/conversion_presenter.py`

```python

@dataclass(frozen=True)
class _ExportCallbacks:
    on_success: Callable[[str], None]
    on_error: Callable[[str], None]


```

```python

@dataclass(frozen=True)
class _ExportCallbacks:
    on_success: Callable[[ConversionOutput], None]
    on_error: Callable[[str], None]


```

Edit: `client/ui/conversion_presenter.py`

```python
        self,
        raw_text: str,
        *,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        # No running check, as before (P1-4 spec, known defect 2): a running job is superseded.
```

```python
        self,
        raw_text: str,
        *,
        on_success: Callable[[ConversionOutput], None],
        on_error: Callable[[str], None],
    ) -> None:
        # No running check, as before (P1-4 spec, known defect 2): a running job is superseded.
```

Edit: `client/ui/conversion_presenter.py`

```python
        self._end_job()
        output = result.conversion_output
        if job.export is not None:
            job.export.on_success(output.display_text)
            return
        self._complete_manual(output)

```

```python
        self._end_job()
        output = result.conversion_output
        if job.export is not None:
            job.export.on_success(output)
            return
        self._complete_manual(output)

```

- [ ] **Step 3: Green: the three modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_export_coordinator tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(export_success_receives_the_conversion_output|html_export_of_a_pending_document_uses_its_conversion|export_all_html_uses_each_pending_documents_conversion|write_document_uses_the_given_results_instead_of_the_cache|pending_html_export_through_the_frame_shows_the_conversion) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_export_coordinator tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_export_success_receives_the_conversion_output ok
test_export_all_html_uses_each_pending_documents_conversion ok
test_html_export_of_a_pending_document_uses_its_conversion ok
test_write_document_uses_the_given_results_instead_of_the_cache ok
test_pending_html_export_through_the_frame_shows_the_conversion ok
Ran 251 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1450 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/documents/export_coordinator.py client/ui/conversion_presenter.py client/tests/test_conversion_presenter.py client/tests/test_export_coordinator.py client/tests/test_gui_document_flows.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: export pending documents as HTML with their own conversion (F-9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/documents/export_coordinator.py    | 39 +++++++++++++-----
 client/tests/test_conversion_presenter.py | 17 +++++++-
 client/tests/test_export_coordinator.py   | 68 +++++++++++++++++++++++++++++--
 client/tests/test_gui_document_flows.py   | 20 +++++++++
 client/ui/conversion_presenter.py         |  6 +--
 5 files changed, 133 insertions(+), 17 deletions(-)
1635c4957f0cc2f4c12fcbd02c2a8f4a1c0e60c6
```

### Task 3: Queue conversions instead of dropping the running one (D4, D5)

- [ ] **Step 1: Red: B7-B13, E5-E8, E10.** `test_conversion_presenter.py`: `test_superseded_job_delivers_nothing` (KNOWN BUG, defect 2) becomes B7, a `_started` helper and B8-B13 follow it, and the live-state test now expects `is_running()` to stay `True` between the worker's end and the delivery (Spec Corrections 6). `test_gui_document_flows.py`: `test_ctrl_s_during_manual_conversion_supersedes_it` becomes E5 and `test_convert_between_export_all_steps_is_superseded` E8 (both KNOWN BUG, defect 2); helpers `_written`, `_boxes` (message and caption only), `_exported_box` and `_finish_jobs` (run each worker, then each later UI turn, until nothing is left); E6, E7 after E5; E10 after the close test.

Edit: `client/tests/test_conversion_presenter.py`

```python
        presenter.convert()
        self.assertTrue(presenter.is_running())
        self.threads[0].run()
        self.assertFalse(presenter.is_running())

    # --- converting dialog timer ----------------------------------------------
```

```python
        presenter.convert()
        self.assertTrue(presenter.is_running())
        self.threads[0].run()
        # Running until the result is delivered, not until the worker ends (F-9 D5).
        self.assertTrue(presenter.is_running())
        self.calls.run_next()
        self.assertFalse(presenter.is_running())

    # --- converting dialog timer ----------------------------------------------
```

Edit: `client/tests/test_conversion_presenter.py`

```python
            ],
        )

    def test_superseded_job_delivers_nothing(self) -> None:
        self.outputs.update({"source": ConversionOutput("manual", ()), "doc text": ConversionOutput("export", ())})
        presenter = self._presenter()
        presenter.convert()
        # KNOWN BUG (P1-4 spec, defect 2): convert_for_export does not check for a running job.
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self.threads[1].run()
        self._take()

        self.calls.run_next()
        self.assertEqual(self._take(), [])

        self.calls.run_next()
        self.assertEqual(self._take(), self._end(2) + [("on_success", "export")])
        self.assertFalse(self.timers.timers[0].stopped)

    def test_synchronous_call_after_with_a_manually_run_thread_completes(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ())
```

```python
            ],
        )

    def _started(self, timer_number: int) -> list:
        return [("busy", True), ("close_converting_dialog",), ("call_later", CONVERTING_DIALOG_DELAY_MS, (timer_number,))]

    def test_export_requested_while_a_conversion_runs_waits_for_it(self) -> None:
        # Was the P1-4 KNOWN BUG (defect 2): the export superseded the manual conversion, whose
        # result was dropped. Now it waits (F-9 D4); its request is built when it is asked for.
        self.outputs.update({"source": ConversionOutput("manual", ()), "doc text": ConversionOutput("export", ())})
        presenter = self._presenter()
        presenter.convert()
        self._take()

        presenter.convert_for_export("doc text", **self._export_callbacks())

        self.assertEqual(self._take(), [("build_request", "doc text")])
        self.assertEqual(len(self.threads), 1)

        self.threads[0].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [
                ("show_conversion_output", "manual"),
                ("get_source_text",),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ]
            + self._started(2),
        )
        self.assertTrue(self.timers.timers[0].stopped)

        self.threads[1].run()
        self.assertEqual(self._take(), [("convert", "doc text"), ("call_after",)])
        self.calls.run_next()

        self.assertEqual(self._take(), self._end(2) + [("on_success", "export")])
        self.assertFalse(presenter.is_running())

    def test_queued_jobs_run_in_request_order(self) -> None:
        texts = ("first", "a", "b", "c")
        self.outputs.update({text: ConversionOutput(text.upper(), ()) for text in texts})
        presenter = self._presenter()
        for text in texts:
            presenter.convert_for_export(text, **self._export_callbacks())

        for index in range(len(texts)):
            self.threads[index].run()
            self.calls.run_next()

        self.assertEqual(
            [event for event in self.events if event[0] in ("convert", "on_success")],
            [("convert", "first"), ("on_success", "FIRST"), ("convert", "a"), ("on_success", "A")]
            + [("convert", "b"), ("on_success", "B"), ("convert", "c"), ("on_success", "C")],
        )
        self.assertEqual([timer.stopped for timer in self.timers.timers], [True, True, True, True])
        self.assertFalse(presenter.is_running())

    def test_queue_drains_after_a_failed_completion(self) -> None:
        self.outputs.update(
            {"source": ConversionStageError("translation", RuntimeError("boom")), "doc text": ConversionOutput("export", ())}
        )
        presenter = self._presenter()
        presenter.convert()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [("show_error", _("Translation failed: {error}").format(error="boom"), _("Error"))]
            + self._started(2),
        )

    def test_request_during_a_completion_waits_until_it_returns(self) -> None:
        # An Export All step's CallAfter runs inside the modal box of a completion: it queues,
        # so a second box never opens on top of the first (F-9 D4).
        self.outputs.update({"first": ConversionOutput("1", ()), "second": ConversionOutput("2", ())})
        presenter = self._presenter()

        def first_done(output) -> None:
            self.events.append(("on_success", output.display_text))
            presenter.convert_for_export("second", **self._export_callbacks())
            self.events.append(("callback returns",))

        presenter.convert_for_export("first", on_success=first_done, on_error=self.fail)
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end() + [("on_success", "1"), ("build_request", "second"), ("callback returns",)] + self._started(2),
        )

    def test_queue_drains_when_a_completion_raises(self) -> None:
        self.outputs.update({"first": ConversionOutput("1", ()), "second": ConversionOutput("2", ())})
        presenter = self._presenter()

        def first_done(_output) -> None:
            raise RuntimeError("callback boom")

        presenter.convert_for_export("first", on_success=first_done, on_error=self.fail)
        presenter.convert_for_export("second", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        with self.assertRaisesRegex(RuntimeError, "callback boom"):
            self.calls.run_next()

        self.assertEqual(self._take(), self._end() + self._started(2))
        self.assertTrue(presenter.is_running())

    def test_convert_returns_while_a_job_is_queued_or_in_the_delivery_gap(self) -> None:
        self.outputs.update(
            {"source": ConversionOutput("⠎", ()), "first": ConversionOutput("1", ()), "second": ConversionOutput("2", ())}
        )
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self._take()

        # The worker has ended; its result is not delivered yet.
        presenter.convert()

        self.assertEqual(self._take(), [])
        self.assertEqual(len(self.threads), 1)
        self.calls.run_next()
        self._take()

        def first_done(output) -> None:
            self.events.append(("on_success", output.display_text))
            # "second" is queued.
            presenter.convert()

        presenter.convert_for_export("first", on_success=first_done, on_error=self.fail)
        presenter.convert_for_export("second", **self._export_callbacks())
        self.threads[1].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(self._take(), self._end(2) + [("on_success", "1")] + self._started(3))
        self.assertEqual(len(self.threads), 3)

    def test_is_running_covers_the_delivery_gap_and_the_queue(self) -> None:
        self.outputs.update({"first": ConversionOutput("1", ()), "second": ConversionOutput("2", ())})
        seen: list = []
        presenter = self._presenter()
        for text in ("first", "second"):
            presenter.convert_for_export(
                text,
                on_success=lambda _output, text=text: seen.append((text, presenter.is_running())),
                on_error=self.fail,
            )

        self.threads[0].run()
        self.assertTrue(presenter.is_running())
        self.calls.run_next()
        self.threads[1].run()
        self.assertTrue(presenter.is_running())
        self.calls.run_next()

        # Queued: running; a completion with an empty queue: not running.
        self.assertEqual(seen, [("first", True), ("second", False)])
        self.assertFalse(presenter.is_running())

    def test_synchronous_call_after_with_a_manually_run_thread_completes(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ())
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "edited", None))
        self.assertIsNone(frame._dual_view_frame)

    # --- single export -------------------------------------------------------

    def test_single_export_with_braille_writes_and_reports(self) -> None:
```

```python
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "edited", None))
        self.assertIsNone(frame._dual_view_frame)

    def test_close_in_the_delivery_gap_is_vetoed(self) -> None:
        # The worker has ended but its result is not delivered yet: still running (F-9 D5).
        frame = self._make_frame([Document("alpha", "source", None)], "alpha")
        self.outputs["source"] = ConversionOutput("⠎", ())
        frame.on_convert(None)
        self.threads[0].run()
        self._take()

        frame._on_close(_CloseEvent(self.events, can_veto=True))

        self.assertEqual(self._take(), [("close.Veto",)])
        self.assertFalse(self.workspace.exists())

        self.calls.run_next()
        self._take()
        frame._on_close(_CloseEvent(self.events, can_veto=True))

        self.assertEqual(self._take(), [("dual_view.Destroy",), ("close.Skip",)])
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "source", "⠎"))

    # --- single export -------------------------------------------------------

    def test_single_export_with_braille_writes_and_reports(self) -> None:
```

Edit: `client/tests/test_gui_document_flows.py`

```python

    # --- re-entrancy (known defects 1 and 2) ----------------------------------

    def test_ctrl_s_during_manual_conversion_supersedes_it(self) -> None:
        frame = self._make_frame([Document("alpha", "alpha text", None)], "alpha")
        target = self.export_dir / "alpha.brl"
        self.export_paths.append(target)
```

```python

    # --- re-entrancy (known defects 1 and 2) ----------------------------------

    def _written(self, folder: Path | None = None) -> dict:
        folder = self.export_dir if folder is None else folder
        return {path.name: path.read_text(encoding="utf-8") for path in sorted(folder.glob("*.brl")) if path.is_file()}

    def _boxes(self) -> list:
        """(message, caption) of each message box so far (the frame's repr would vary in a diff)."""
        return [event[1:3] for event in self.events if event[0] == "MessageBox"]

    def _exported_box(self) -> tuple:
        return (gui._("The document was exported successfully."), gui._("Export Complete"))

    def _finish_jobs(self) -> None:
        """Run each started worker, then each later UI turn, until nothing is left."""
        done = 0
        while done < len(self.threads) or self.calls.pending:
            if self.calls.pending:
                self.calls.run_next()
            else:
                self.threads[done].run()
                done += 1

    def test_ctrl_s_during_manual_conversion_queues_the_export(self) -> None:
        frame = self._make_frame([Document("alpha", "alpha text", None)], "alpha")
        target = self.export_dir / "alpha.brl"
        self.export_paths.append(target)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        event = _KeyEvent(self.CTRL_S)
        frame.on_output_text_key_down(event)

        # KNOWN BUG (P1-4 spec, defect 2): the export conversion starts without a running check.
        self.assertEqual(
            self._take(),
            [self._export_dialog(frame, "alpha.brl")]
            + self._busy(True)
            + [("call_later", 2000, (2,)), ("focus", "output")],
        )
        self.assertFalse(event.skipped)
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "alpha text", None))

        self.threads[0].run()
        self.threads[1].run()
        self.assertEqual(self._take(), [("convert", "alpha text"), ("call_after",), ("convert", "alpha text"), ("call_after",)])

        self.calls.run_next()
        self.assertEqual(self._take(), [])

        self.calls.run_next()
        self.assertEqual(self._take(), [("timer.Stop", 2)] + self._busy(False) + [self._exported(frame)])
        self.assertEqual(target.read_text(encoding="utf-8"), "⠁⠁")
        self.assertFalse(self.timers.timers[0].stopped)
        self.assertEqual(frame.output_txt.value, "")
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "alpha text", None)])

    def test_ctrl_tab_during_manual_conversion_sends_result_to_new_document(self) -> None:
        segment = _dual_view_segment("a", "⠁")
```

```python
        event = _KeyEvent(self.CTRL_S)
        frame.on_output_text_key_down(event)

        # Was the P1-4 KNOWN BUG (defect 2): the export superseded the manual conversion, which
        # never showed its output. Now the export waits for it (F-9 D4).
        self.assertEqual(self._take(), [self._export_dialog(frame, "alpha.brl"), ("focus", "output")])
        self.assertFalse(event.skipped)
        self.assertEqual(len(self.threads), 1)
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "alpha text", None))

        self.threads[0].run()
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            [("convert", "alpha text"), ("call_after",), ("timer.Stop", 1)]
            + self._busy(False)
            + [("set", "output", "⠁⠁"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)]
            + self._busy(True)
            + [("call_later", 2000, (2,))],
        )
        self.assertFalse(target.exists())

        self.threads[1].run()
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            [("convert", "alpha text"), ("call_after",), ("timer.Stop", 2)] + self._busy(False) + [self._exported(frame)],
        )
        self.assertEqual(target.read_text(encoding="utf-8"), "⠁⠁")
        self.assertEqual(frame.output_txt.value, "⠁⠁")
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "alpha text", "⠁⠁")])

    def test_ctrl_s_during_export_all_waits_and_the_summary_appears(self) -> None:
        # Was P1-4 defect 2 (spec probe 3): the Ctrl+S export dropped the first step, the chain
        # stopped, no summary appeared and the Export All folder stayed empty (F-9 D4).
        frame = self._make_frame([Document("open", "t0", None), Document("p1", "t1", None), Document("p2", "t2", None)], "open")
        second_dir = self.root / "second"
        second_dir.mkdir()
        self.export_dirs.append(self.export_dir)
        self.export_paths.append(second_dir / "open.brl")
        self.outputs.update(t0=ConversionOutput("⠴", ()), t1=ConversionOutput("⠂", ()), t2=ConversionOutput("⠆", ()))

        frame.on_export_all_documents("brl")
        frame.on_output_text_key_down(_KeyEvent(self.CTRL_S))
        self._finish_jobs()

        self.assertEqual(
            self._boxes(),
            [self._exported_box(), ("All documents were exported successfully.", gui._("Export Complete"))],
        )
        self.assertEqual([request.raw_text for request in self.requests], ["t0", "t0", "t1", "t2"])
        self.assertEqual(self._written(), {"open.brl": "⠴", "p1.brl": "⠂", "p2.brl": "⠆"})
        self.assertEqual(self._written(second_dir), {"open.brl": "⠴"})
        self.assertFalse(frame._conversion_presenter.is_running())

    def test_ctrl_s_during_single_export_writes_both_files(self) -> None:
        # Was P1-4 defect 2 (spec probe 2): beta.brl was never written and nothing said so (F-9 D4).
        frame = self._make_frame(
            [Document("alpha", "alpha text", None), Document("beta", "beta text", None)],
            open_name="alpha",
            selected_name="beta",
        )
        self.export_paths.extend([self.export_dir / "beta.brl", self.export_dir / "alpha.brl"])
        self.outputs.update({"alpha text": ConversionOutput("⠁", ()), "beta text": ConversionOutput("⠃", ())})

        frame.on_export_document("brl")
        frame.on_output_text_key_down(_KeyEvent(self.CTRL_S))
        self.threads[0].run()
        self.calls.run_next()

        self.assertEqual(self._written(), {"beta.brl": "⠃"})
        self.assertEqual(self._boxes(), [self._exported_box()])

        self.threads[1].run()
        self.calls.run_next()

        self.assertEqual(self._written(), {"alpha.brl": "⠁", "beta.brl": "⠃"})
        self.assertEqual(self._boxes(), [self._exported_box(), self._exported_box()])
        self.assertEqual(self.calls.pending, [])

    def test_ctrl_tab_during_manual_conversion_sends_result_to_new_document(self) -> None:
        segment = _dual_view_segment("a", "⠁")
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        )
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": (segment,)})

    def test_convert_between_export_all_steps_is_superseded(self) -> None:
        frame = self._make_frame([Document("r1", "t1", "⠁"), Document("p1", "t2", None)], "r1")
        frame.input_txt.value = "manual text"
        self.export_dirs.append(self.export_dir)
```

```python
        )
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": (segment,)})

    def test_convert_between_export_all_steps_completes_before_the_next_step(self) -> None:
        frame = self._make_frame([Document("r1", "t1", "⠁"), Document("p1", "t2", None)], "r1")
        frame.input_txt.value = "manual text"
        self.export_dirs.append(self.export_dir)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (1,))])

        self.calls.run_next()
        # KNOWN BUG (P1-4 spec, defect 2): the next pending step starts a second job; the manual one is dropped.
        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (2,))])

        self.threads[0].run()
        self.threads[1].run()
        self.assertEqual(self._take(), [("convert", "manual text"), ("call_after",), ("convert", "t2"), ("call_after",)])
        self.calls.run_next()
        self.assertEqual(self._take(), [])
        self.calls.run_next()
        self.assertEqual(self._take(), [("timer.Stop", 2)] + self._busy(False) + [("call_after",)])
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [self._info(frame, "All documents were exported successfully.", gui._("Export Complete"))],
        )
        self.assertEqual(frame.output_txt.value, "⠁")
        self.assertEqual((self.export_dir / "p1.brl").read_text(encoding="utf-8"), "⠃")


```

```python
        self.assertEqual(self._take(), self._busy(True) + [("call_later", 2000, (1,))])

        self.calls.run_next()
        # Was the P1-4 KNOWN BUG (defect 2): the next pending step started a second job and the
        # manual one was dropped. Now the step waits for it (F-9 D4).
        self.assertEqual(self._take(), [])
        self.assertEqual(len(self.threads), 1)

        self.threads[0].run()
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [("convert", "manual text"), ("call_after",), ("timer.Stop", 1)]
            + self._busy(False)
            + [("set", "output", "⠍"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)]
            + self._busy(True)
            + [("call_later", 2000, (2,))],
        )
        self.threads[1].run()
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [("convert", "t2"), ("call_after",), ("timer.Stop", 2)] + self._busy(False) + [("call_after",)],
        )
        self.calls.run_next()
        self.assertEqual(
            self._take(),
            [self._info(frame, "All documents were exported successfully.", gui._("Export Complete"))],
        )
        self.assertEqual(frame.output_txt.value, "⠍")
        self.assertEqual((self.export_dir / "p1.brl").read_text(encoding="utf-8"), "⠃")


```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (a second request still starts at once and replaces the running job; a close in the delivery gap is not vetoed; the export folder of E6 stays empty and its summary never comes):

```text
FAIL: test_convert_returns_while_a_job_is_queued_or_in_the_delivery_gap (tests.test_conversion_presenter.ConversionPresenterTest.test_convert_returns_while_a_jo
AssertionError: Lists differ: [('get_source_text',), ('busy', True), ('c[78 chars]2,))] != []
FAIL: test_export_requested_while_a_conversion_runs_waits_for_it (tests.test_conversion_presenter.ConversionPresenterTest.test_export_requested_while_a_conversi
AssertionError: Lists differ: [('busy', True), ('close_converting_dialog',),[54 chars]2,))] != [('build_request', 'doc text')]
FAIL: test_is_running_and_missing_table_message_read_live_state (tests.test_conversion_presenter.ConversionPresenterTest.test_is_running_and_missing_table_messa
AssertionError: False is not true
FAIL: test_is_running_covers_the_delivery_gap_and_the_queue (tests.test_conversion_presenter.ConversionPresenterTest.test_is_running_covers_the_delivery_gap_and
FAIL: test_queue_drains_after_a_failed_completion (tests.test_conversion_presenter.ConversionPresenterTest.test_queue_drains_after_a_failed_completion)
AssertionError: Lists differ: [] != [('timer.Stop', 1), ('close_converting_dia[128 chars]2,))]
FAIL: test_queue_drains_when_a_completion_raises (tests.test_conversion_presenter.ConversionPresenterTest.test_queue_drains_when_a_completion_raises)
AssertionError: RuntimeError not raised
FAIL: test_queued_jobs_run_in_request_order (tests.test_conversion_presenter.ConversionPresenterTest.test_queued_jobs_run_in_request_order)
AssertionError: Lists differ: [('co[15 chars]), ('convert', 'a'), ('convert', 'b'), ('conve[26 chars]'C')] != [('co[15 chars]), ('on_success', 'FIRST'), ('conve
FAIL: test_request_during_a_completion_waits_until_it_returns (tests.test_conversion_presenter.ConversionPresenterTest.test_request_during_a_completion_waits_un
AssertionError: Lists differ: [('ti[82 chars] ('busy', True), ('close_converting_dialog',),[75 chars]s',)] != [('ti[82 chars] ('build_request', 'second'), ('cal
FAIL: test_close_in_the_delivery_gap_is_vetoed (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_close_in_the_delivery_gap_is_vetoed
AssertionError: Lists differ: [('dual_view.Destroy',), ('close.Skip',)] != [('close.Veto',)]
FAIL: test_convert_between_export_all_steps_completes_before_the_next_step (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_convert
AssertionError: Lists differ: [('FindMenu', '檔案'), ('EnableTop', 0, Fals[126 chars]2,))] != []
FAIL: test_ctrl_s_during_export_all_waits_and_the_summary_appears (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_ctrl_s_during_ex
AssertionError: Lists differ: [('文件已成功匯出。', '匯出完成')] != [('文件已成功匯出。', '匯出完成'), ('All documents were exported successfully.', '匯出完成')]
FAIL: test_ctrl_s_during_manual_conversion_queues_the_export (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_ctrl_s_during_manual_
AssertionError: Lists differ: [('Fi[110 chars]), ('FindMenu', '檔案'), ('EnableTop', 0, False)[145 chars]ut')] != [('Fi[110 chars]), ('focus', 'output')]
FAIL: test_ctrl_s_during_single_export_writes_both_files (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_ctrl_s_during_single_expo
AssertionError: {} != {'beta.brl': '⠃'}
Ran 230 tests
FAILED (failures=13)
```

- [ ] **Step 2: Green: the queue** (`client/ui/conversion_presenter.py`, 4 spaces). `_Job` holds the request (built at submit time) and the export callbacks; `_ActiveJob` holds the running job; `_submit` queues while a job is active, a completion runs or the queue is not empty, and otherwise starts at once with today's event order (busy, close the dialog, build the request, start, timer); each completion sets `_completing` and drains in `finally`.

Edit: `client/ui/conversion_presenter.py`

```python
frame through ``ConversionView``. Threading is injected: ``call_after`` must defer to a
later UI turn (as ``wx.CallAfter`` does), so the active job is recorded before any
result can be delivered.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol
```

```python
frame through ``ConversionView``. Threading is injected: ``call_after`` must defer to a
later UI turn (as ``wx.CallAfter`` does), so the active job is recorded before any
result can be delivered.

One job runs at a time. A job asked for while another one runs or completes waits in a
queue and starts, oldest first, when that completion returns, so no result is dropped
and a completion's message box closes before the next job starts (F-9).
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol
```

Edit: `client/ui/conversion_presenter.py`

```python


@dataclass(frozen=True)
class _ActiveJob:
    job_id: int
    export: _ExportCallbacks | None  # None: a manual conversion


def missing_default_table_message(translation_tables: Mapping[str, object]) -> str | None:
```

```python


@dataclass(frozen=True)
class _Job:
    request: ConversionRequest
    export: _ExportCallbacks | None  # None: a manual conversion


@dataclass(frozen=True)
class _ActiveJob:
    job_id: int
    job: _Job


def missing_default_table_message(translation_tables: Mapping[str, object]) -> str | None:
```

Edit: `client/ui/conversion_presenter.py`

```python
        )
        self._active: _ActiveJob | None = None
        self._timer: Timer | None = None

    def is_running(self) -> bool:
        return self._runner.is_running()

    def missing_table_message(self) -> str | None:
        return missing_default_table_message(self._get_translation_tables())
```

```python
        )
        self._active: _ActiveJob | None = None
        self._timer: Timer | None = None
        # Jobs asked for while another one is active or completing, oldest first (F-9 D4).
        self._queue: deque[_Job] = deque()
        self._completing = False

    def is_running(self) -> bool:
        """Whether a job is active (its result not yet delivered) or queued (F-9 D5)."""
        return self._active is not None or bool(self._queue)

    def missing_table_message(self) -> str | None:
        return missing_default_table_message(self._get_translation_tables())
```

Edit: `client/ui/conversion_presenter.py`

```python
        if message is not None:
            self._view.show_info(message, _("Info"))
            return
        self._start(self._view.get_source_text(), export=None)

    def convert_for_export(
        self,
```

```python
        if message is not None:
            self._view.show_info(message, _("Info"))
            return
        self._submit(self._view.get_source_text(), export=None)

    def convert_for_export(
        self,
```

Edit: `client/ui/conversion_presenter.py`

```python
        on_success: Callable[[ConversionOutput], None],
        on_error: Callable[[str], None],
    ) -> None:
        # No running check, as before (P1-4 spec, known defect 2): a running job is superseded.
        self._start(raw_text, export=_ExportCallbacks(on_success, on_error))

    def _start(self, raw_text: str, export: _ExportCallbacks | None) -> None:
        self._view.set_conversion_busy(True)
        self._view.close_converting_dialog()
        request = self._build_request(raw_text)
        job_id = self._runner.start(request)
        self._active = _ActiveJob(job_id, export)
        self._timer = self._call_later(CONVERTING_DIALOG_DELAY_MS, self._show_converting_dialog, job_id)

    def _show_converting_dialog(self, job_id: int) -> None:
        if job_id != self._runner.active_job_id:
```

```python
        on_success: Callable[[ConversionOutput], None],
        on_error: Callable[[str], None],
    ) -> None:
        # A running job is not replaced: this one waits for it (F-9 D4, was P1-4 defect 2).
        self._submit(raw_text, export=_ExportCallbacks(on_success, on_error))

    def _submit(self, raw_text: str, export: _ExportCallbacks | None) -> None:
        """Start a job now, or queue it while another one is active, completing or queued (F-9 D4).

        A queued job's request is built now, so the settings at the time of the command apply.
        """
        if self._active is not None or self._completing or self._queue:
            self._queue.append(_Job(self._build_request(raw_text), export))
            return
        self._start(lambda: _Job(self._build_request(raw_text), export))

    def _start(self, make_job: Callable[[], _Job]) -> None:
        self._view.set_conversion_busy(True)
        self._view.close_converting_dialog()
        job = make_job()
        job_id = self._runner.start(job.request)
        self._active = _ActiveJob(job_id, job)
        self._timer = self._call_later(CONVERTING_DIALOG_DELAY_MS, self._show_converting_dialog, job_id)

    def _finish_completion(self) -> None:
        """End a completion, also one that raised: start the oldest queued job (F-9 D4)."""
        self._completing = False
        if self._queue:
            job = self._queue.popleft()
            self._start(lambda: job)

    def _show_converting_dialog(self, job_id: int) -> None:
        if job_id != self._runner.active_job_id:
```

Edit: `client/ui/conversion_presenter.py`

```python
        self._view.set_conversion_busy(False)

    def _on_job_success(self, result: ConversionJobSuccess) -> None:
        job = self._take_active(result.job_id)
        if job is None:
            return
        self._end_job()
        output = result.conversion_output
        if job.export is not None:
            job.export.on_success(output)
            return
        self._complete_manual(output)

    def _on_job_failure(self, result: ConversionJobFailure) -> None:
        job = self._take_active(result.job_id)
        if job is None:
            return
        message = format_conversion_error(result.error)
        self._end_job()
        if job.export is not None:
            job.export.on_error(message)
            return
        self._view.show_error(message, _("Error"))

    def _complete_manual(self, output: ConversionOutput) -> None:
        braille = output.display_text
```

```python
        self._view.set_conversion_busy(False)

    def _on_job_success(self, result: ConversionJobSuccess) -> None:
        active = self._take_active(result.job_id)
        if active is None:
            return
        self._completing = True
        try:
            self._end_job()
            output = result.conversion_output
            if active.job.export is not None:
                active.job.export.on_success(output)
            else:
                self._complete_manual(output)
        finally:
            self._finish_completion()

    def _on_job_failure(self, result: ConversionJobFailure) -> None:
        active = self._take_active(result.job_id)
        if active is None:
            return
        message = format_conversion_error(result.error)
        self._completing = True
        try:
            self._end_job()
            if active.job.export is not None:
                active.job.export.on_error(message)
            else:
                self._view.show_error(message, _("Error"))
        finally:
            self._finish_completion()

    def _complete_manual(self, output: ConversionOutput) -> None:
        braille = output.display_text
```

- [ ] **Step 3: Green: the two modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(export_requested_while_a_conversion_runs_waits_for_it|queued_jobs_run_in_request_order|queue_drains_after_a_failed_completion|request_during_a_completion_waits_until_it_returns|queue_drains_when_a_completion_raises|convert_returns_while_a_job_is_queued_or_in_the_delivery_gap|is_running_covers_the_delivery_gap_and_the_queue|ctrl_s_during_manual_conversion_queues_the_export|ctrl_s_during_export_all_waits_and_the_summary_appears|ctrl_s_during_single_export_writes_both_files|convert_between_export_all_steps_completes_before_the_next_step|close_in_the_delivery_gap_is_vetoed) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_jobs tests.test_conversion_presenter tests.test_export_coordinator tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`test_export_all_with_a_real_presenter_turn_by_turn` and every other characterization test without an overlap pass unchanged):

```text
test_convert_returns_while_a_job_is_queued_or_in_the_delivery_gap ok
test_export_requested_while_a_conversion_runs_waits_for_it ok
test_is_running_covers_the_delivery_gap_and_the_queue ok
test_queue_drains_after_a_failed_completion ok
test_queue_drains_when_a_completion_raises ok
test_queued_jobs_run_in_request_order ok
test_request_during_a_completion_waits_until_it_returns ok
test_close_in_the_delivery_gap_is_vetoed ok
test_convert_between_export_all_steps_completes_before_the_next_step ok
test_ctrl_s_during_export_all_waits_and_the_summary_appears ok
test_ctrl_s_during_manual_conversion_queues_the_export ok
test_ctrl_s_during_single_export_writes_both_files ok
Ran 270 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1459 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/ui/conversion_presenter.py client/tests/test_conversion_presenter.py client/tests/test_gui_document_flows.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: queue conversions instead of dropping the running one (F-9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/tests/test_conversion_presenter.py | 166 +++++++++++++++++++++++++++++-
 client/tests/test_gui_document_flows.py   | 151 +++++++++++++++++++++++----
 client/ui/conversion_presenter.py         |  88 +++++++++++-----
 3 files changed, 355 insertions(+), 50 deletions(-)
c1207cf754c19df5b7c59498e397e969aff00ce4
```

### Task 4: Ignore conversion results after the window closes (D8)

- [ ] **Step 1: Red: B14, E11, E12; the delegation test.** `test_conversion_presenter.py`: B14 before the last presenter test. `test_gui_document_flows.py`: `test_close_while_running_vetoes_or_saves_and_closes` (E12) expects `("timer.Stop", 1)` first, E11 follows E10, and `FrameConversionDelegationTest.test_close_asks_presenter_before_saving` expects `call.presenter.shutdown()` after the save (Spec Corrections 6).

Edit: `client/tests/test_conversion_presenter.py`

```python
        self.assertEqual(seen, [("first", True), ("second", False)])
        self.assertFalse(presenter.is_running())

    def test_synchronous_call_after_with_a_manually_run_thread_completes(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter(call_after=lambda fn, *args: fn(*args))
```

```python
        self.assertEqual(seen, [("first", True), ("second", False)])
        self.assertFalse(presenter.is_running())

    def test_shutdown_drops_the_running_and_queued_jobs(self) -> None:
        # The window has closed (F-9 D8, P1 review M-10): nothing may reach the view any more.
        self.outputs.update({"source": ConversionOutput("⠎", ()), "doc text": ConversionOutput("⠙", ())})
        presenter = self._presenter()
        presenter.convert()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self._take()

        presenter.shutdown()

        self.assertEqual(self._take(), [("timer.Stop", 1)])
        self.assertFalse(presenter.is_running())
        self.timers.timers[0].fire()
        self.threads[0].run()
        self.calls.run_next()
        presenter.convert_for_export("late", **self._export_callbacks())

        self.assertEqual(self._take(), [("convert", "source"), ("call_after",)])
        self.assertEqual(len(self.threads), 1)
        self.assertFalse(presenter.is_running())

    def test_synchronous_call_after_with_a_manually_run_thread_completes(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter(call_after=lambda fn, *args: fn(*args))
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        frame._on_close(_CloseEvent(self.events, can_veto=False))

        self.assertEqual(
            self._take(),
            [("dialog.Unbind", "EVT_CLOSE"), ("dialog.Destroy",), ("dual_view.Destroy",), ("close.Skip",)],
        )
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "edited", None))
        self.assertIsNone(frame._dual_view_frame)
```

```python

        frame._on_close(_CloseEvent(self.events, can_veto=False))

        # The presenter is shut down first, which stops the dialog timer (F-9 D8).
        self.assertEqual(
            self._take(),
            [("timer.Stop", 1), ("dialog.Unbind", "EVT_CLOSE"), ("dialog.Destroy",), ("dual_view.Destroy",), ("close.Skip",)],
        )
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "edited", None))
        self.assertIsNone(frame._dual_view_frame)
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        self.assertEqual(self._take(), [("dual_view.Destroy",), ("close.Skip",)])
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "source", "⠎"))

    # --- single export -------------------------------------------------------

```

```python

        self.assertEqual(self._take(), [("dual_view.Destroy",), ("close.Skip",)])
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "source", "⠎"))

    def test_close_that_cannot_be_vetoed_shuts_the_presenter_down(self) -> None:
        # P1 review M-10: a result delivered after the window closed reached the destroyed
        # frame. Now it is ignored (F-9 D8): no view call and no write.
        frame = self._make_frame([Document("alpha", "alpha text", None), Document("beta", "beta text", "⠃")], "alpha")
        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ())
        frame.on_convert(None)
        frame.on_char_hook(_KeyEvent(self.CTRL_TAB))
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        self._take()

        frame._on_close(_CloseEvent(self.events, can_veto=False))

        self.assertEqual(self._take(), [("timer.Stop", 1), ("dual_view.Destroy",), ("close.Skip",)])

        self.threads[0].run()
        self.calls.run_next()
        self.timers.timers[0].fire()

        self.assertEqual(self._take(), [("convert", "alpha text"), ("call_after",)])
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(
            frame._document_controller.documents,
            [Document("alpha", "alpha text", None), Document("beta", "beta text", "⠃")],
        )
        self.assertFalse(frame._conversion_presenter.is_running())

    # --- single export -------------------------------------------------------

```

Edit: `client/tests/test_gui_document_flows.py`

```python
                call.presenter.is_running(),
                call.event.CanVeto(),
                call.save(),
                call.close_converting_dialog(),
                call.event.Skip(),
            ],
```

```python
                call.presenter.is_running(),
                call.event.CanVeto(),
                call.save(),
                call.presenter.shutdown(),
                call.close_converting_dialog(),
                call.event.Skip(),
            ],
```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (no `shutdown`; the close does not stop the timer; a late result reaches the closed frame):

```text
ERROR: test_shutdown_drops_the_running_and_queued_jobs (tests.test_conversion_presenter.ConversionPresenterTest.test_shutdown_drops_the_running_and_queued_jobs)
AttributeError: 'ConversionPresenter' object has no attribute 'shutdown'
FAIL: test_close_that_cannot_be_vetoed_shuts_the_presenter_down (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_close_that_cannot_
AssertionError: Lists differ: [('dual_view.Destroy',), ('close.Skip',)] != [('timer.Stop', 1), ('dual_view.Destroy',), ('close.Skip',)]
FAIL: test_close_while_running_vetoes_or_saves_and_closes (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_close_while_running_veto
AssertionError: Lists differ: [('dialog.Unbind', 'EVT_CLOSE'), ('dialog.De[45 chars]p',)] != [('timer.Stop', 1), ('dialog.Unbind', 'EVT_C[64 chars]p',)]
FAIL: test_close_asks_presenter_before_saving (tests.test_gui_document_flows.FrameConversionDelegationTest.test_close_asks_presenter_before_saving)
AssertionError: [call[19 chars]ng(),
Ran 232 tests
FAILED (failures=3, errors=1)
```

- [ ] **Step 2: Green: `shutdown()` and the frame's close** (`client/ui/conversion_presenter.py`, 4 spaces; `client/gui.py`, tabs).

Edit: `client/ui/conversion_presenter.py`

```python
One job runs at a time. A job asked for while another one runs or completes waits in a
queue and starts, oldest first, when that completion returns, so no result is dropped
and a completion's message box closes before the next job starts (F-9).
"""

from __future__ import annotations
```

```python
One job runs at a time. A job asked for while another one runs or completes waits in a
queue and starts, oldest first, when that completion returns, so no result is dropped
and a completion's message box closes before the next job starts (F-9).
``shutdown`` (the window closes) drops the running and queued jobs: later results are
ignored, and no view method runs after that (F-9).
"""

from __future__ import annotations
```

Edit: `client/ui/conversion_presenter.py`

```python
        # Jobs asked for while another one is active or completing, oldest first (F-9 D4).
        self._queue: deque[_Job] = deque()
        self._completing = False

    def is_running(self) -> bool:
        """Whether a job is active (its result not yet delivered) or queued (F-9 D5)."""
```

```python
        # Jobs asked for while another one is active or completing, oldest first (F-9 D4).
        self._queue: deque[_Job] = deque()
        self._completing = False
        self._shut_down = False

    def is_running(self) -> bool:
        """Whether a job is active (its result not yet delivered) or queued (F-9 D5)."""
```

Edit: `client/ui/conversion_presenter.py`

```python

        A queued job's request is built now, so the settings at the time of the command apply.
        """
        if self._active is not None or self._completing or self._queue:
            self._queue.append(_Job(self._build_request(raw_text), export))
            return
```

```python

        A queued job's request is built now, so the settings at the time of the command apply.
        """
        if self._shut_down:
            return
        if self._active is not None or self._completing or self._queue:
            self._queue.append(_Job(self._build_request(raw_text), export))
            return
```

Edit: `client/ui/conversion_presenter.py`

```python
    def _finish_completion(self) -> None:
        """End a completion, also one that raised: start the oldest queued job (F-9 D4)."""
        self._completing = False
        if self._queue:
            job = self._queue.popleft()
            self._start(lambda: job)

    def _show_converting_dialog(self, job_id: int) -> None:
        if job_id != self._runner.active_job_id:
            return
        if not self._runner.is_running():
            return
```

```python
    def _finish_completion(self) -> None:
        """End a completion, also one that raised: start the oldest queued job (F-9 D4)."""
        self._completing = False
        if self._queue and not self._shut_down:
            job = self._queue.popleft()
            self._start(lambda: job)

    def shutdown(self) -> None:
        """Drop the running and queued jobs; the window has closed (F-9 D8, P1 review M-10).

        Stops the dialog timer. A result delivered later finds no active job and is
        ignored; no view method is called from now on.
        """
        if self._timer is not None:
            self._timer.Stop()
            self._timer = None
        self._active = None
        self._queue.clear()
        self._shut_down = True

    def _show_converting_dialog(self, job_id: int) -> None:
        if self._shut_down or job_id != self._runner.active_job_id:
            return
        if not self._runner.is_running():
            return
```

Edit: `client/gui.py`

```python

	def _finish_close(self, evt: wx.CloseEvent) -> None:
		self._close_finished = True
		self.close_converting_dialog()
		if self._dual_view_frame is not None:
			viewer = self._dual_view_frame
```

```python

	def _finish_close(self, evt: wx.CloseEvent) -> None:
		self._close_finished = True
		# A conversion still running delivers nothing to the closed window (F-9 D8).
		self._conversion_presenter.shutdown()
		self.close_converting_dialog()
		if self._dual_view_frame is not None:
			viewer = self._dual_view_frame
```

- [ ] **Step 3: Green: the two modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(shutdown_drops_the_running_and_queued_jobs|close_that_cannot_be_vetoed_shuts_the_presenter_down|close_while_running_vetoes_or_saves_and_closes|close_asks_presenter_before_saving) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_shutdown_drops_the_running_and_queued_jobs ok
test_close_that_cannot_be_vetoed_shuts_the_presenter_down ok
test_close_while_running_vetoes_or_saves_and_closes ok
test_close_asks_presenter_before_saving ok
Ran 232 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1461 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/ui/conversion_presenter.py client/gui.py client/tests/test_conversion_presenter.py client/tests/test_gui_document_flows.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: ignore conversion results after the window closes (F-9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/gui.py                             |  2 ++
 client/tests/test_conversion_presenter.py | 21 +++++++++++++++++++++
 client/tests/test_gui_document_flows.py   | 30 +++++++++++++++++++++++++++++-
 client/ui/conversion_presenter.py         | 22 ++++++++++++++++++++--
 4 files changed, 72 insertions(+), 3 deletions(-)
abd8058bfcc39543393b0edd7e5e18339601d754
```

### Task 5: Write a conversion result to the document that started it (D1-D3, D9)

- [ ] **Step 1: Red: B1-B6, D1-D5, E1-E4, E13, E14, F1.** `test_conversion_presenter.py`: a `setUpModule` that isolates `dotexpress.gui`, the recording view's `save_converted_document` (configurable result), helpers `_switch_to` (stores the open document's editor text, then opens another, as the frame does) and `_saved_to`, and B1-B6 before the failure test. `test_workspace_service.py`: D1-D5 at the end of `SaveOnlyWhenChangedTest`. `test_gui_document_flows.py`: `CTRL_O`, `_saved_to`, `test_ctrl_tab_during_manual_conversion_sends_result_to_new_document` (KNOWN BUG, defect 1) becomes E1, then E2, a fake import dialog, E3, E4, E14; E13 in `FrameViewMethodsTest`. `test_i18n.py`: F1. All four files use 4 spaces.

Edit: `client/tests/test_conversion_presenter.py`

```python
from documents.workspace import Document
from i18n import _
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory

PRESENTER_PATH = Path(__file__).resolve().parents[1] / "ui" / "conversion_presenter.py"


class RecordingConversionView:
```

```python
from documents.workspace import Document
from i18n import _
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
from tests.file_log_isolation import isolate_file_logs

PRESENTER_PATH = Path(__file__).resolve().parents[1] / "ui" / "conversion_presenter.py"
LOGGER = "dotexpress.gui"


def setUpModule() -> None:
    # A discarded result is logged to gui.log (F-9 D3); keep the real file out of it.
    unittest.addModuleCleanup(isolate_file_logs(LOGGER))


class RecordingConversionView:
```

Edit: `client/tests/test_conversion_presenter.py`

```python
    def __init__(self, events: list, source_text: str = ""):
        self.events = events
        self.source_text = source_text

    def get_source_text(self) -> str:
        self.events.append(("get_source_text",))
```

```python
    def __init__(self, events: list, source_text: str = ""):
        self.events = events
        self.source_text = source_text
        self.save_result = True

    def get_source_text(self) -> str:
        self.events.append(("get_source_text",))
```

Edit: `client/tests/test_conversion_presenter.py`

```python

    def show_error(self, message: str, caption: str) -> None:
        self.events.append(("show_error", message, caption))


class ConversionPresenterTest(unittest.TestCase):
```

```python

    def show_error(self, message: str, caption: str) -> None:
        self.events.append(("show_error", message, caption))

    def save_converted_document(self, document: Document) -> bool:
        self.events.append(("save_converted_document", document))
        return self.save_result


class ConversionPresenterTest(unittest.TestCase):
```

Edit: `client/tests/test_conversion_presenter.py`

```python

    def _end(self, timer_number: int = 1) -> list:
        return [("timer.Stop", timer_number), ("close_converting_dialog",), ("busy", False)]

    # --- module helpers ------------------------------------------------------

```

```python

    def _end(self, timer_number: int = 1) -> list:
        return [("timer.Stop", timer_number), ("close_converting_dialog",), ("busy", False)]

    def _switch_to(self, name: str) -> None:
        """Switch documents as the frame does: store the open document's editor text, then open ``name``."""
        open_document = self.documents.get_document(self.documents.open_document_name)
        if open_document is not None:
            self.documents.replace_document(Document(open_document.name, self.view.source_text, open_document.braille))
        document = self.documents.open_document(name)
        self.view.source_text = document.text if document is not None else ""

    def _saved_to(self, name: str) -> tuple:
        return (
            "show_info",
            _('Conversion completed. The result was saved to document "{name}".').format(name=name),
            _("Info"),
        )

    # --- module helpers ------------------------------------------------------

```

Edit: `client/tests/test_conversion_presenter.py`

```python
        )
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {"ghost": ("segment",)})

    def test_manual_failure_shows_error_after_busy_off(self) -> None:
        self.outputs["source"] = ConversionStageError("text_processing", RuntimeError("script boom"))
```

```python
        )
        self.assertEqual(self.documents.documents, [Document("alpha", "old", None), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {"ghost": ("segment",)})

    # --- the document that started the conversion (F-9 D1-D3) -------------------

    def test_result_goes_to_the_document_that_started_the_conversion(self) -> None:
        # Was P1-4 defect 1: the result went to the document open at completion.
        self.outputs["source"] = ConversionOutput("⠎", ("result",), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self._switch_to("beta")
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end() + [("save_converted_document", Document("alpha", "source", "⠎")), self._saved_to("alpha")],
        )
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("segment",)})
        self.assertEqual(self.documents.get_document("beta"), Document("beta", "b", "⠃"))
        self.assertEqual(self.documents.open_document_name, "beta")

    def test_result_for_the_open_document_follows_todays_path(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ("result",), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self._switch_to("beta")
        self._switch_to("alpha")
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [
                ("show_conversion_output", "⠎"),
                ("get_source_text",),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ],
        )
        self.assertEqual(self.documents.documents, [Document("alpha", "source", "⠎"), Document("beta", "b", "⠃")])
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("segment",)})

    def test_failed_save_of_the_originating_document_shows_no_completion_message(self) -> None:
        # The view has shown the save error; the next queued job still starts.
        self.outputs.update({"source": ConversionOutput("⠎", (), ("segment",)), "doc text": ConversionOutput("⠙", ())})
        self.view.save_result = False
        presenter = self._presenter()
        presenter.convert()
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self._switch_to("beta")
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [("save_converted_document", Document("alpha", "source", "⠎"))]
            + [("busy", True), ("close_converting_dialog",), ("call_later", CONVERTING_DIALOG_DELAY_MS, (2,))],
        )
        self.assertEqual(self.documents.dual_view_results_by_document, {"alpha": ("segment",)})

    def _assert_discarded(self, presenter: ConversionPresenter, reason: str) -> None:
        """Deliver the running job's result and check that it was dropped with one log line."""
        self.threads[-1].run()
        self._take()
        documents_before = list(self.documents.documents)
        with self.assertLogs(LOGGER, level="ERROR") as logs:
            self.calls.run_next()

        self.assertEqual(self._take(), self._end(len(self.timers.timers)))
        self.assertEqual([record.getMessage() for record in logs.records], [f"Discarded a conversion result: {reason}"])
        self.assertEqual(self.documents.documents, documents_before)
        self.assertEqual(self.documents.dual_view_results_by_document, {})
        self.assertFalse(presenter.is_running())

    def test_result_for_a_document_that_is_gone_is_discarded_and_logged(self) -> None:
        # None of these can happen while a job runs today (the list and the File menu are
        # disabled); the result is not guessed onto another document (F-9 D3, O2).
        for case, remove in (
            ("deleted", lambda: self.documents.delete_document("alpha")),
            ("renamed", lambda: self.documents.rename_document("alpha", "gamma")),
            ("delete all", lambda: self.documents.delete_all_documents()),
        ):
            with self.subTest(case=case):
                self.setUp()
                self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
                presenter = self._presenter()
                presenter.convert()
                self._switch_to("beta")
                remove()

                self._assert_discarded(presenter, 'document "alpha" no longer exists')

    def test_result_for_a_changed_text_is_discarded_and_logged(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self._switch_to("beta")
        self.documents.replace_document(Document("alpha", "another text", None))

        self._assert_discarded(presenter, 'the text of document "alpha" changed')

    def test_result_without_a_starting_document(self) -> None:
        # No document open at the start: today's output-only path if none is open at the end;
        # if one was opened meanwhile, the result is discarded rather than given to it.
        self.documents.open_name = None
        self.outputs["source"] = ConversionOutput("⠎", (), ("segment",))
        presenter = self._presenter()
        presenter.convert()
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [
                ("show_conversion_output", "⠎"),
                ("refresh_dual_view",),
                ("show_info", _("Conversion completed."), _("Info")),
            ],
        )

        presenter.convert()
        self.documents.open_document("beta")
        self._assert_discarded(presenter, 'document "beta" was opened during a conversion without a document')

    def test_manual_failure_shows_error_after_busy_off(self) -> None:
        self.outputs["source"] = ConversionStageError("text_processing", RuntimeError("script boom"))
```

Edit: `client/tests/test_workspace_service.py`

```python

            self.assertEqual(self._disk(), before)


class ReplacedNulCharactersTest(unittest.TestCase):
    """U+0000 in a package or an import reaches the controller as U+FFFD, counted once (F-8 D12)."""
```

```python

            self.assertEqual(self._disk(), before)

    # --- save_document: a document that is not open (F-9 D1) -------------------
    # A conversion result for a document that is no longer open is written at once; here
    # alpha is open and the pending beta is not.

    def _save_document(self, document: Document) -> tuple[Document | None, int]:
        """Save ``document``; return what was saved and how many packages were written."""
        with patch.object(workspace_service, "save_document_package", wraps=workspace_service.save_document_package) as save:
            saved = self.service.save_document(document)
        return saved, save.call_count

    def test_save_document_writes_a_document_that_is_not_open(self) -> None:
        saved, written = self._save_document(Document("beta", "b", "⠃"))

        self.assertEqual((saved, written), (Document("beta", "b", "⠃"), 1))
        self.assertEqual(self.controller.get_document("beta"), saved)
        self.assertEqual(load_document_package(self._path("beta")), saved)
        self.assertEqual(self.controller.open_document_name, "alpha")
        # Recorded as written: opening beta and switching away does not write it again.
        self.controller.open_document("beta")
        self.assertEqual(self._save(text="b", braille="⠃"), 0)

    def test_save_document_skips_an_unchanged_document(self) -> None:
        before = self._disk("beta")

        saved, written = self._save_document(Document("beta", "b", None))

        self.assertEqual((saved, written), (Document("beta", "b", None), 0))
        self.assertEqual(self._disk("beta"), before)

    def test_save_document_failure_keeps_memory_and_the_package(self) -> None:
        before = self._disk("beta")

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")):
            with self.assertRaises(PermissionError):
                self.service.save_document(Document("beta", "b", "⠃"))

        self.assertEqual(self.controller.get_document("beta"), Document("beta", "b", "⠃"))
        self.assertEqual(self._disk("beta"), before)
        # The next save of beta retries the write.
        self.assertEqual(self._save_document(Document("beta", "b", "⠃"))[1], 1)
        self.assertEqual(load_document_package(self._path("beta")), Document("beta", "b", "⠃"))

    def test_save_document_of_an_unknown_name_returns_none(self) -> None:
        documents = list(self.controller.documents)

        self.assertEqual(self._save_document(Document("ghost", "g", "⠛")), (None, 0))

        self.assertEqual(self.controller.documents, documents)
        self.assertFalse(self._path("ghost").exists())

    def test_converted_braille_of_a_pending_document_is_saved(self) -> None:
        # The editor path keeps a pending document's braille pending (prepare_document_for_save);
        # save_document must not, or a converted result would be erased.
        self._save_document(Document("beta", "b", "⠃"))

        with zipfile.ZipFile(self._path("beta")) as archive:
            self.assertEqual(sorted(archive.namelist()), ["beta.brl", "beta.txt"])
            self.assertEqual(archive.read("beta.brl").decode("utf-8"), "⠃")


class ReplacedNulCharactersTest(unittest.TestCase):
    """U+0000 in a package or an import reaches the controller as U+FFFD, counted once (F-8 D12)."""
```

Edit: `client/tests/test_gui_document_flows.py`

```python
    CHARSET_MAPS = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "zh"}
    CTRL_S = 83
    CTRL_TAB = 9

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
```

```python
    CHARSET_MAPS = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "zh"}
    CTRL_S = 83
    CTRL_TAB = 9
    CTRL_O = 79

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
```

Edit: `client/tests/test_gui_document_flows.py`

```python

    def _completed(self, frame) -> tuple:
        return self._info(frame, gui._("Conversion completed."))

    def _exported(self, frame) -> tuple:
        return self._info(frame, gui._("The document was exported successfully."), gui._("Export Complete"))
```

```python

    def _completed(self, frame) -> tuple:
        return self._info(frame, gui._("Conversion completed."))

    def _saved_to(self, frame, name: str) -> tuple:
        return self._info(frame, gui._('Conversion completed. The result was saved to document "{name}".').format(name=name))

    def _exported(self, frame) -> tuple:
        return self._info(frame, gui._("The document was exported successfully."), gui._("Export Complete"))
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._boxes(), [self._exported_box(), self._exported_box()])
        self.assertEqual(self.calls.pending, [])

    def test_ctrl_tab_during_manual_conversion_sends_result_to_new_document(self) -> None:
        segment = _dual_view_segment("a", "⠁")
        frame = self._make_frame([Document("alpha", "alpha text", None), Document("beta", "beta text", "⠃")], "alpha")
        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ("result",), (segment,))
```

```python
        self.assertEqual(self._boxes(), [self._exported_box(), self._exported_box()])
        self.assertEqual(self.calls.pending, [])

    def test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document(self) -> None:
        segment = _dual_view_segment("a", "⠁")
        frame = self._make_frame([Document("alpha", "alpha text", None), Document("beta", "beta text", "⠃")], "alpha")
        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ("result",), (segment,))
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.threads[0].run()
        self.calls.run_next()

        # KNOWN BUG (P1-4 spec, defect 1): alpha's result lands in beta, the document open now.
        self.assertEqual(
            self._take(),
            [("convert", "alpha text"), ("call_after",), ("timer.Stop", 1)]
            + self._busy(False)
            + [("set", "output", "⠁⠁"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)],
        )
        self.assertEqual(
            frame._document_controller.documents,
            [Document("alpha", "alpha text", None), Document("beta", "beta text", "⠁⠁")],
        )
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {"beta": (segment,)})

    def test_convert_between_export_all_steps_completes_before_the_next_step(self) -> None:
        frame = self._make_frame([Document("r1", "t1", "⠁"), Document("p1", "t2", None)], "r1")
```

```python
        self.threads[0].run()
        self.calls.run_next()

        # Was the P1-4 KNOWN BUG (defect 1): alpha's result landed in beta, the document open
        # then, and the next save wrote it into beta.dep. Now it goes to alpha (F-9 D1, U1):
        # beta's editors, the focus and the Dual View are left alone.
        self.assertEqual(
            self._take(),
            [("convert", "alpha text"), ("call_after",), ("timer.Stop", 1)]
            + self._busy(False)
            + [self._saved_to(frame, "alpha")],
        )
        controller = frame._document_controller
        self.assertEqual(controller.documents, [Document("alpha", "alpha text", "⠁⠁"), Document("beta", "beta text", "⠃")])
        self.assertEqual(controller.dual_view_results_by_document, {"alpha": (segment,)})
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "alpha text", "⠁⠁"))
        self.assertFalse((self.workspace / "beta.dep").exists())
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("beta text", "⠃"))

        frame.on_char_hook(_KeyEvent(self.CTRL_TAB))

        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("alpha text", "⠁⠁"))
        self.assertEqual(load_document_package(self.workspace / "beta.dep"), Document("beta", "beta text", "⠃"))

    def test_ctrl_tab_away_and_back_during_conversion_keeps_todays_completion(self) -> None:
        segment = _dual_view_segment("a", "⠁")
        frame = self._make_frame([Document("alpha", "alpha text", None), Document("beta", "beta text", "⠃")], "alpha")
        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ("result",), (segment,))

        frame.on_convert(None)
        frame.on_char_hook(_KeyEvent(self.CTRL_TAB))
        frame.on_char_hook(_KeyEvent(self.CTRL_TAB, shift=True))
        self.threads[0].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(
            self._take(),
            [("timer.Stop", 1)]
            + self._busy(False)
            + [("set", "output", "⠁⠁"), ("focus", "output"), ("dual_view.refresh",), self._completed(frame)],
        )
        controller = frame._document_controller
        self.assertEqual(controller.documents, [Document("alpha", "alpha text", "⠁⠁"), Document("beta", "beta text", "⠃")])
        self.assertEqual(controller.dual_view_results_by_document, {"alpha": (segment,)})
        # Case (a) writes nothing at completion; the next save does, as before.
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "alpha text", None))

    def _import_dialog_class(self, paths: list[Path]):
        test = self

        class FakeImportFileDialog:
            def __init__(self, parent, title, wildcard="", style=0):
                test.events.append(("ImportDialog", title))
                self.filter_index = None

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def SetFilterIndex(self, index):
                self.filter_index = index

            def GetFilterIndex(self):
                return self.filter_index

            def ShowModal(self):
                return gui.wx.ID_OK

            def GetPaths(self):
                return [str(path) for path in paths]

        return FakeImportFileDialog

    def test_import_during_manual_conversion_does_not_receive_the_result(self) -> None:
        # Was P1-4 defect 1 through Ctrl+O: the imported document, open at completion, got the result.
        source = self.root / "imported.txt"
        source.write_text("imported text", encoding="utf-8")
        frame = self._make_frame([Document("alpha", "alpha text", None)], "alpha")
        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ("result",), (_dual_view_segment("a", "⠁"),))

        frame.on_convert(None)
        with patch.object(gui.wx, "FileDialog", self._import_dialog_class([source])):
            frame.on_char_hook(_KeyEvent(self.CTRL_O))
        self.assertEqual(frame._document_controller.open_document_name, "imported")
        self.threads[0].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(self._take(), [("timer.Stop", 1)] + self._busy(False) + [self._saved_to(frame, "alpha")])
        self.assertEqual(
            frame._document_controller.documents,
            [Document("alpha", "alpha text", "⠁⠁"), Document("imported", "imported text", None)],
        )
        self.assertEqual(load_document_package(self.workspace / "imported.dep"), Document("imported", "imported text", None))
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "alpha text", "⠁⠁"))
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("imported text", ""))

    def test_failed_save_of_the_starting_document_reports_the_save_error(self) -> None:
        frame = self._make_frame([Document("alpha", "alpha text", None), Document("beta", "beta text", "⠃")], "alpha")
        self.outputs["alpha text"] = ConversionOutput("⠁⠁", ())
        error = PermissionError(errno.EACCES, "injected")

        frame.on_convert(None)
        frame.on_char_hook(_KeyEvent(self.CTRL_TAB))
        self.threads[0].run()
        self._take()
        with patch("os.replace", side_effect=error):
            self.calls.run_next()

        # The usual save error and no completion box (F-9 D1); the result stays in memory.
        self.assertEqual(
            self._take(),
            [("timer.Stop", 1)]
            + self._busy(False)
            + [self._error(frame, gui._("Failed to save document: {error}").format(error=error))],
        )
        self.assertEqual(frame._document_controller.get_document("alpha"), Document("alpha", "alpha text", "⠁⠁"))
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "alpha text", None))

        # Opening alpha shows the result; switching away retries the write.
        frame.on_char_hook(_KeyEvent(self.CTRL_TAB))
        self.assertEqual(frame.output_txt.value, "⠁⠁")
        frame.on_char_hook(_KeyEvent(self.CTRL_TAB))
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", "alpha text", "⠁⠁"))

    def test_switch_away_stores_exactly_the_converted_text(self) -> None:
        # The text guard of F-9 D3 compares the memory text with the converted text; both come
        # from the same editor read, which replaces a lone surrogate (F-7), so the result is kept.
        replaced = "A" + chr(0xFFFD) + "B"
        frame = self._make_frame([Document("alpha", "a", None), Document("beta", "beta text", "⠃")], "alpha")
        frame.input_txt.value = "A" + LONE_SURROGATE + "B"
        self.outputs[replaced] = ConversionOutput("⠁", ())

        frame.on_convert(None)
        frame.on_char_hook(_KeyEvent(self.CTRL_TAB))
        self.threads[0].run()
        self._take()
        self.calls.run_next()

        self.assertEqual(self._take(), [("timer.Stop", 1)] + self._busy(False) + [self._saved_to(frame, "alpha")])
        self.assertEqual(frame._document_controller.get_document("alpha"), Document("alpha", replaced, "⠁"))
        self.assertEqual(load_document_package(self.workspace / "alpha.dep"), Document("alpha", replaced, "⠁"))

    def test_convert_between_export_all_steps_completes_before_the_next_step(self) -> None:
        frame = self._make_frame([Document("r1", "t1", "⠁"), Document("p1", "t2", None)], "r1")
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame.refresh_dual_view()

        frame._refresh_dual_view.assert_called_once_with()

    def test_message_methods_use_one_message_box_each(self) -> None:
        frame = self._make_frame()
```

```python
        frame.refresh_dual_view()

        frame._refresh_dual_view.assert_called_once_with()

    def test_save_converted_document_reports_failures_like_every_save(self) -> None:
        # F-9 D1: an OSError is shown; anything else is shown and logged (F-3, F-5).
        frame = self._make_frame()
        frame._workspace_service = Mock()
        document = Document("alpha", "a", "⠁")
        os_error, bug = OSError("disk full"), ValueError("injected")

        frame._workspace_service.save_document.side_effect = os_error
        with patch.object(gui, "message_box") as os_error_box, self.assertNoLogs("dotexpress.gui", "ERROR"):
            self.assertFalse(frame.save_converted_document(document))
        frame._workspace_service.save_document.side_effect = bug
        with patch.object(gui, "message_box") as bug_box, self.assertLogs("dotexpress.gui", "ERROR") as logs:
            self.assertFalse(frame.save_converted_document(document))

        for box, error in ((os_error_box, os_error), (bug_box, bug)):
            box.assert_called_once_with(
                gui._("Failed to save document: {error}").format(error=error),
                gui._("Error"),
                gui.wx.OK | gui.wx.ICON_ERROR,
                parent=frame,
            )
        self.assertEqual([record.getMessage() for record in logs.records], ["Unexpected error while saving a document"])
        self.assertIs(logs.records[0].exc_info[1], bug)
        frame._workspace_service.save_document.side_effect = None
        with patch.object(gui, "message_box") as message_box:
            self.assertTrue(frame.save_converted_document(document))

        message_box.assert_not_called()
        frame._workspace_service.save_document.assert_called_with(document)

    def test_message_methods_use_one_message_box_each(self) -> None:
        frame = self._make_frame()
```

Edit: `client/tests/test_i18n.py`

```python
            "文件「alpha」中有 3 個無法顯示的字元，已全部以替代字元 \ufffd 標示，後面的文字都保留下來了。"
            "\n\n轉換前請刪除或修改這些 \ufffd，否則每一個都會在點字中變成一段跳脫碼。",
        )

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```python
            "文件「alpha」中有 3 個無法顯示的字元，已全部以替代字元 \ufffd 標示，後面的文字都保留下來了。"
            "\n\n轉換前請刪除或修改這些 \ufffd，否則每一個都會在點字中變成一段跳脫碼。",
        )

    def test_conversion_result_saved_string_is_translated(self) -> None:
        # F-9 (D2): a conversion result written to the document that started it while
        # another document is open.
        message = 'Conversion completed. The result was saved to document "{name}".'
        translation = i18n.load_translation()

        self.assertEqual(translation.gettext(message), "轉換完成。結果已儲存到文件「{name}」。")
        self.assertEqual(translation.gettext(message).format(name="alpha"), "轉換完成。結果已儲存到文件「alpha」。")

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (the result still goes to the document open at completion; no `save_document`, no `save_converted_document`, no discard log, no msgid):

```text
ERROR: test_converted_braille_of_a_pending_document_is_saved (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_converted_braille_of_a_pending_document_
AttributeError: 'DocumentWorkspaceService' object has no attribute 'save_document'. Did you mean: 'create_document'?
ERROR: test_save_document_failure_keeps_memory_and_the_package (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_save_document_failure_keeps_memory_and
ERROR: test_save_document_of_an_unknown_name_returns_none (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_save_document_of_an_unknown_name_returns_no
ERROR: test_save_document_skips_an_unchanged_document (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_save_document_skips_an_unchanged_document)
ERROR: test_save_document_writes_a_document_that_is_not_open (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_save_document_writes_a_document_that_is_
FAIL: test_failed_save_of_the_originating_document_shows_no_completion_message (tests.test_conversion_presenter.ConversionPresenterTest.test_failed_save_of_the_
AssertionError: Lists differ: [('ti[60 chars], ('show_conversion_output', '⠎'), ('get_sourc[133 chars]2,))] != [('ti[60 chars], ('save_converted_document', Docu
FAIL: test_result_for_a_changed_text_is_discarded_and_logged (tests.test_conversion_presenter.ConversionPresenterTest.test_result_for_a_changed_text_is_discarde
AssertionError: no logs of level ERROR or higher triggered on dotexpress.gui
FAIL: test_result_for_a_document_that_is_gone_is_discarded_and_logged (tests.test_conversion_presenter.ConversionPresenterTest.test_result_for_a_document_that_i
FAIL: test_result_goes_to_the_document_that_started_the_conversion (tests.test_conversion_presenter.ConversionPresenterTest.test_result_goes_to_the_document_tha
AssertionError: Lists differ: [('ti[60 chars], ('show_conversion_output', '⠎'), ('get_sourc[59 chars]資訊')] != [('ti[60 chars], ('save_converted_document', Docum
FAIL: test_result_without_a_starting_document (tests.test_conversion_presenter.ConversionPresenterTest.test_result_without_a_starting_document)
FAIL: test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test
AssertionError: Lists differ: [('co[197 chars]), ('set', 'output', '⠁⠁'), ('focus', 'output'[106 chars]<addr>)] != [('co[197 chars]), ('MessageBox', 'Conversion
FAIL: test_failed_save_of_the_starting_document_reports_the_save_error (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_failed_save
AssertionError: Lists differ: [('ti[153 chars]), ('set', 'output', '⠁⠁'), ('focus', 'output'[106 chars]<addr>)] != [('ti[153 chars]), ('MessageBox', '儲存文件失敗：[Er
FAIL: test_import_during_manual_conversion_does_not_receive_the_result (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_import_duri
AssertionError: Lists differ: [('ti[153 chars]), ('set', 'output', '⠁⠁'), ('focus', 'output'[106 chars]<addr>)] != [('ti[153 chars]), ('MessageBox', 'Conversion
FAIL: test_switch_away_stores_exactly_the_converted_text (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_switch_away_stores_exactl
AssertionError: Lists differ: [('ti[153 chars]), ('set', 'output', '⠁'), ('focus', 'output')[105 chars]<addr>)] != [('ti[153 chars]), ('MessageBox', 'Conversion
FAIL: test_save_converted_document_reports_failures_like_every_save (tests.test_gui_document_flows.FrameViewMethodsTest.test_save_converted_document_reports_fai
FAIL: test_conversion_result_saved_string_is_translated (tests.test_i18n.TranslationTest.test_conversion_result_saved_string_is_translated)
AssertionError: 'Conversion completed. The result was saved to document "{name}".' != '轉換完成。結果已儲存到文件「{name}」。'
Ran 344 tests
FAILED (failures=13, errors=5)
```

- [ ] **Step 2: Green: the starting document, `save_document`, the frame's save.** `client/ui/conversion_presenter.py` and `client/documents/workspace_service.py` use 4 spaces, `client/gui.py` tabs. `convert()` records `_ManualTarget(open document name, source text)`; `_complete_manual` takes case (a) when the target is the open document (or none was and none is), case (b) otherwise, with the guard of D3 and `_discard`; `save_open_document` becomes `prepare_document_for_save`, then `save_document`.

Edit: `client/ui/conversion_presenter.py`

```python
and a completion's message box closes before the next job starts (F-9).
``shutdown`` (the window closes) drops the running and queued jobs: later results are
ignored, and no view method runs after that (F-9).
"""

from __future__ import annotations
```

```python
and a completion's message box closes before the next job starts (F-9).
``shutdown`` (the window closes) drops the running and queued jobs: later results are
ignored, and no view method runs after that (F-9).

A manual conversion's result goes to the document that was open when it started. If
another document is open when it completes, the result is saved to the starting
document and the open one is left alone; if the starting document is gone or holds
another text, the result is discarded and logged (F-9).
"""

from __future__ import annotations
```

Edit: `client/ui/conversion_presenter.py`

```python
from documents.controller import DocumentController
from documents.workspace import Document
from i18n import _

CONVERTING_DIALOG_DELAY_MS = 2000

```

```python
from documents.controller import DocumentController
from documents.workspace import Document
from i18n import _
from log import get_logger

CONVERTING_DIALOG_DELAY_MS = 2000

```

Edit: `client/ui/conversion_presenter.py`

```python

    def show_error(self, message: str, caption: str) -> None: ...


@dataclass(frozen=True)
class _ExportCallbacks:
```

```python

    def show_error(self, message: str, caption: str) -> None: ...

    def save_converted_document(self, document: Document) -> bool:
        """Save ``document``, which is not open; ``False`` if the save failed and was reported."""
        ...


@dataclass(frozen=True)
class _ExportCallbacks:
```

Edit: `client/ui/conversion_presenter.py`

```python


@dataclass(frozen=True)
class _Job:
    request: ConversionRequest
    export: _ExportCallbacks | None  # None: a manual conversion


@dataclass(frozen=True)
```

```python


@dataclass(frozen=True)
class _ManualTarget:
    """The document open when a manual conversion started, and the text it converted (F-9 D1)."""

    document_name: str | None
    source_text: str


@dataclass(frozen=True)
class _Job:
    request: ConversionRequest
    export: _ExportCallbacks | None  # None: a manual conversion
    manual: _ManualTarget | None = None


@dataclass(frozen=True)
```

Edit: `client/ui/conversion_presenter.py`

```python
        if message is not None:
            self._view.show_info(message, _("Info"))
            return
        self._submit(self._view.get_source_text(), export=None)

    def convert_for_export(
        self,
```

```python
        if message is not None:
            self._view.show_info(message, _("Info"))
            return
        source_text = self._view.get_source_text()
        target = _ManualTarget(self._documents.open_document_name, source_text)
        self._submit(source_text, export=None, manual=target)

    def convert_for_export(
        self,
```

Edit: `client/ui/conversion_presenter.py`

```python
        # A running job is not replaced: this one waits for it (F-9 D4, was P1-4 defect 2).
        self._submit(raw_text, export=_ExportCallbacks(on_success, on_error))

    def _submit(self, raw_text: str, export: _ExportCallbacks | None) -> None:
        """Start a job now, or queue it while another one is active, completing or queued (F-9 D4).

        A queued job's request is built now, so the settings at the time of the command apply.
```

```python
        # A running job is not replaced: this one waits for it (F-9 D4, was P1-4 defect 2).
        self._submit(raw_text, export=_ExportCallbacks(on_success, on_error))

    def _submit(self, raw_text: str, export: _ExportCallbacks | None, manual: _ManualTarget | None = None) -> None:
        """Start a job now, or queue it while another one is active, completing or queued (F-9 D4).

        A queued job's request is built now, so the settings at the time of the command apply.
```

Edit: `client/ui/conversion_presenter.py`

```python
        if self._shut_down:
            return
        if self._active is not None or self._completing or self._queue:
            self._queue.append(_Job(self._build_request(raw_text), export))
            return
        self._start(lambda: _Job(self._build_request(raw_text), export))

    def _start(self, make_job: Callable[[], _Job]) -> None:
        self._view.set_conversion_busy(True)
```

```python
        if self._shut_down:
            return
        if self._active is not None or self._completing or self._queue:
            self._queue.append(_Job(self._build_request(raw_text), export, manual))
            return
        self._start(lambda: _Job(self._build_request(raw_text), export, manual))

    def _start(self, make_job: Callable[[], _Job]) -> None:
        self._view.set_conversion_busy(True)
```

Edit: `client/ui/conversion_presenter.py`

```python
            if active.job.export is not None:
                active.job.export.on_success(output)
            else:
                self._complete_manual(output)
        finally:
            self._finish_completion()

```

```python
            if active.job.export is not None:
                active.job.export.on_success(output)
            else:
                self._complete_manual(active.job.manual, output)
        finally:
            self._finish_completion()

```

Edit: `client/ui/conversion_presenter.py`

```python
        finally:
            self._finish_completion()

    def _complete_manual(self, output: ConversionOutput) -> None:
        braille = output.display_text
        self._view.show_conversion_output(braille)
        # The result goes to the document open now, as before (P1-4 spec, known defect 1).
        open_name = self._documents.open_document_name
        if open_name:
            document = self._documents.get_document(open_name)
            if document is not None:
                self._documents.replace_document(Document(document.name, self._view.get_source_text(), braille))
            self._documents.set_dual_view_results(open_name, output.dual_view_segments)
        self._view.refresh_dual_view()
        self._view.show_info(_("Conversion completed."), _("Info"))
```

```python
        finally:
            self._finish_completion()

    def _complete_manual(self, target: _ManualTarget, output: ConversionOutput) -> None:
        braille = output.display_text
        open_name = self._documents.open_document_name
        if target.document_name == open_name:
            # The starting document is open (or none was and none is): as before F-9.
            self._view.show_conversion_output(braille)
            if open_name:
                document = self._documents.get_document(open_name)
                if document is not None:
                    self._documents.replace_document(Document(document.name, self._view.get_source_text(), braille))
                self._documents.set_dual_view_results(open_name, output.dual_view_segments)
            self._view.refresh_dual_view()
            self._view.show_info(_("Conversion completed."), _("Info"))
            return
        if target.document_name is None:
            self._discard(f'document "{open_name}" was opened during a conversion without a document')
            return
        # Another document is open (F-9 D1, U1): its editors, focus and Dual View stay as they are.
        document = self._documents.get_document(target.document_name)
        if document is None:
            self._discard(f'document "{target.document_name}" no longer exists')
            return
        if document.text != target.source_text:
            self._discard(f'the text of document "{target.document_name}" changed')
            return
        self._documents.set_dual_view_results(document.name, output.dual_view_segments)
        if self._view.save_converted_document(Document(document.name, document.text, braille)):
            self._view.show_info(
                _('Conversion completed. The result was saved to document "{name}".').format(name=document.name),
                _("Info"),
            )

    def _discard(self, reason: str) -> None:
        """Drop a manual result that has no document to go to (F-9 D3).

        Logged at ERROR, the level ``gui.log`` records. The logger is bound here, not at
        import (as in F-6 review M-6).
        """
        get_logger("dotexpress.gui", "gui.log").error("Discarded a conversion result: %s", reason)
```

Edit: `client/documents/workspace_service.py`

```python
aside before installing it (``move_document_package``): a failure leaves exactly the
old package, and a case-only rename (``Alpha`` to ``alpha``) is safe on a
case-insensitive file system, where both names are the same file.
Save writes only when the open document differs from what was last written to or
loaded from its package; that record changes only after a successful write, so a
failed save is retried by the next one.
Add, Rename, Import and the default document never replace a package that is on disk
but not listed, such as an invalid one kept at startup: its name counts as taken.
Startup puts back a package that a crash during Save or Rename left only in a
```

```python
aside before installing it (``move_document_package``): a failure leaves exactly the
old package, and a case-only rename (``Alpha`` to ``alpha``) is safe on a
case-insensitive file system, where both names are the same file.
Save writes only when the document differs from what was last written to or loaded
from its package; that record changes only after a successful write, so a failed save
is retried by the next one. ``save_open_document`` saves the open document from the
editors; ``save_document`` saves any listed document, such as a conversion result for
a document that is no longer open (F-9).
Add, Rename, Import and the default document never replace a package that is on disk
but not listed, such as an invalid one kept at startup: its name counts as taken.
Startup puts back a package that a crash during Save or Rename left only in a
```

Edit: `client/documents/workspace_service.py`

```python
        document = self._controller.get_document(self._controller.open_document_name)
        if document is None:
            return None
        updated_document = prepare_document_for_save(document, text=text, braille=braille)
        self._controller.replace_document(updated_document)
        if self._is_saved(updated_document):
            return updated_document
```

```python
        document = self._controller.get_document(self._controller.open_document_name)
        if document is None:
            return None
        # A pending document's braille stays pending here: the editor shows none (F-5).
        return self.save_document(prepare_document_for_save(document, text=text, braille=braille))

    def save_document(self, document: Document) -> Document | None:
        """Put ``document`` in memory, then write its package unless it already holds it (F-9 D1).

        ``None`` if no listed document has its name. The braille is kept as given, also for
        a document that was pending. Raises like ``save_document_package``; memory has the
        new document then, and the next save of it retries the write.
        """
        if self._controller.get_document(document.name) is None:
            return None
        updated_document = _encodable(document)
        self._controller.replace_document(updated_document)
        if self._is_saved(updated_document):
            return updated_document
```

Edit: `client/gui.py`

```python
	def show_error(self, message: str, caption: str) -> None:
		message_box(message, caption, wx.OK | wx.ICON_ERROR, parent=self)

	# --- ExportView (documents/export_coordinator.py) -----------------------

	def show_warning(self, message: str, caption: str) -> None:
```

```python
	def show_error(self, message: str, caption: str) -> None:
		message_box(message, caption, wx.OK | wx.ICON_ERROR, parent=self)

	def save_converted_document(self, document: Document) -> bool:
		"""Save a conversion result for a document that is not open (F-9 D1); failures as every save."""
		try:
			self._workspace_service.save_document(document)
		except Exception as exc:
			self._show_document_save_error(exc)
			return False
		return True

	# --- ExportView (documents/export_coordinator.py) -----------------------

	def show_warning(self, message: str, caption: str) -> None:
```

- [ ] **Step 3: Green apart from the catalog.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(result_goes_to_the_document_that_started_the_conversion|result_for_the_open_document_follows_todays_path|failed_save_of_the_originating_document_shows_no_completion_message|result_for_a_document_that_is_gone_is_discarded_and_logged|result_for_a_changed_text_is_discarded_and_logged|result_without_a_starting_document|save_document_writes_a_document_that_is_not_open|save_document_skips_an_unchanged_document|save_document_failure_keeps_memory_and_the_package|save_document_of_an_unknown_name_returns_none|converted_braille_of_a_pending_document_is_saved|ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document|ctrl_tab_away_and_back_during_conversion_keeps_todays_completion|import_during_manual_conversion_does_not_receive_the_result|failed_save_of_the_starting_document_reports_the_save_error|save_converted_document_reports_failures_like_every_save|switch_away_stores_exactly_the_converted_text) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (the seventeen tests pass; only the catalog test still fails):

```text
test_failed_save_of_the_originating_document_shows_no_completion_message ok
test_result_for_a_changed_text_is_discarded_and_logged ok
test_result_for_a_document_that_is_gone_is_discarded_and_logged ok
test_result_for_the_open_document_follows_todays_path ok
test_result_goes_to_the_document_that_started_the_conversion ok
test_result_without_a_starting_document ok
test_converted_braille_of_a_pending_document_is_saved ok
test_save_document_failure_keeps_memory_and_the_package ok
test_save_document_of_an_unknown_name_returns_none ok
test_save_document_skips_an_unchanged_document ok
test_save_document_writes_a_document_that_is_not_open ok
test_ctrl_tab_away_and_back_during_conversion_keeps_todays_completion ok
test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document ok
test_failed_save_of_the_starting_document_reports_the_save_error ok
test_import_during_manual_conversion_does_not_receive_the_result ok
test_switch_away_stores_exactly_the_converted_text ok
test_save_converted_document_reports_failures_like_every_save ok
FAIL: test_conversion_result_saved_string_is_translated (tests.test_i18n.TranslationTest.test_conversion_result_saved_string_is_translated)
AssertionError: 'Conversion completed. The result was saved to document "{name}".' != '轉換完成。結果已儲存到文件「{name}」。'
Ran 344 tests
FAILED (failures=1)
```

- [ ] **Step 4: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
```

Expected (no `xgettext` warning on stderr; `msgmerge` guessed no fuzzy translation, so the fuzzy listing is empty; the new msgid is untranslated and `python-brace-format`):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
368 translated messages, 1 untranslated message.
#: ui/conversion_presenter.py:305
#, python-brace-format
msgid "Conversion completed. The result was saved to document \"{name}\"."
msgstr ""
```

- [ ] **Step 5: Fill the msgstr** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
#: ui/conversion_presenter.py:305
#, python-brace-format
msgid "Conversion completed. The result was saved to document \"{name}\"."
msgstr ""

#: ui/translation_menu.py:8
msgid "Convert"
```

```po
#: ui/conversion_presenter.py:305
#, python-brace-format
msgid "Conversion completed. The result was saved to document \"{name}\"."
msgstr "轉換完成。結果已儲存到文件「{name}」。"

#: ui/translation_menu.py:8
msgid "Convert"
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
msggrep --msgid -e 'The result was saved to document' locales/zh_TW/LC_MESSAGES/dotexpress.po 2>/dev/null | sed -n '/^#: /,$p'
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (369 translated, no fuzzy; 370 `msgid` lines with the header; the 31 obsolete entries unchanged; no absolute, backslash, test or venv reference; `msggrep` writes a code-page warning to stderr, which is dropped):

```text
a second msgmerge changes nothing
msgfmt exit 0
369 translated messages.
0
#: ui/conversion_presenter.py:305
#, python-brace-format
msgid "Conversion completed. The result was saved to document \"{name}\"."
msgstr "轉換完成。結果已儲存到文件「{name}」。"
catalog keys: 370
'Conversion completed. The result was saved to document "{name}".' -> 轉換完成。結果已儲存到文件「{name}」。
29183
locales/dotexpress.pot:370
locales/zh_TW/LC_MESSAGES/dotexpress.po:370
31
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 369 sha256 a94d370e253c7c605c90ea5896f725ef09030d45cf5e2906d98333556a2ec0e4
```

- [ ] **Step 6: Green: the four modules and the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_i18n -v 2>&1 | grep -E "^test_conversion_result_saved_string_is_translated " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_conversion_result_saved_string_is_translated ok
Ran 344 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1478 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/ui/conversion_presenter.py client/documents/workspace_service.py client/gui.py client/tests/test_conversion_presenter.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py client/tests/test_i18n.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: write a conversion result to the document that started it (F-9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected (the `.pot` and `.po` also change in the `#:` reference lines of the moved code):

```text
 client/documents/workspace_service.py          |  22 +++-
 client/gui.py                                  |   9 ++
 client/locales/dotexpress.pot                  |  47 ++++---
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 29047 -> 29183 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po |  47 ++++---
 client/tests/test_conversion_presenter.py      | 160 +++++++++++++++++++++++
 client/tests/test_gui_document_flows.py        | 172 ++++++++++++++++++++++++-
 client/tests/test_i18n.py                      |   9 ++
 client/tests/test_workspace_service.py         |  59 +++++++++
 client/ui/conversion_presenter.py              |  78 ++++++++---
 10 files changed, 540 insertions(+), 63 deletions(-)
2fffcc5e1cefbfe656061f1c477dcdaadd00115a
```

### Task 6: Verification (no commit)

`BASE` is `main` at `7aba2be`.

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = 1444 + 34; the error is F-W6):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1478 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 2: Criterion 2, focused modules; the 39 F-9 tests (34 new, 5 flipped) ran and passed; both orders of three modules.** The verbose run is kept in `$T/verbose.txt`, so a failure there is named.

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_jobs tests.test_conversion_presenter tests.test_export_coordinator tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_gui_document_flows tests.test_conversion_presenter tests.test_export_coordinator 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_export_coordinator tests.test_conversion_presenter tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_conversion_jobs tests.test_conversion_presenter tests.test_export_coordinator tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n -v > $T/verbose.txt 2>&1; grep -cE "^test_(unexpected_worker_error_is_delivered_as_a_translation_failure|base_exception_in_the_worker_is_delivered_too|result_goes_to_the_document_that_started_the_conversion|result_for_the_open_document_follows_todays_path|failed_save_of_the_originating_document_shows_no_completion_message|result_for_a_document_that_is_gone_is_discarded_and_logged|result_for_a_changed_text_is_discarded_and_logged|result_without_a_starting_document|export_requested_while_a_conversion_runs_waits_for_it|queued_jobs_run_in_request_order|queue_drains_after_a_failed_completion|request_during_a_completion_waits_until_it_returns|queue_drains_when_a_completion_raises|convert_returns_while_a_job_is_queued_or_in_the_delivery_gap|is_running_covers_the_delivery_gap_and_the_queue|shutdown_drops_the_running_and_queued_jobs|export_success_receives_the_conversion_output|html_export_of_a_pending_document_uses_its_conversion|export_all_html_uses_each_pending_documents_conversion|write_document_uses_the_given_results_instead_of_the_cache|save_document_writes_a_document_that_is_not_open|save_document_skips_an_unchanged_document|save_document_failure_keeps_memory_and_the_package|save_document_of_an_unknown_name_returns_none|converted_braille_of_a_pending_document_is_saved|ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document|ctrl_tab_away_and_back_during_conversion_keeps_todays_completion|import_during_manual_conversion_does_not_receive_the_result|failed_save_of_the_starting_document_reports_the_save_error|ctrl_s_during_manual_conversion_queues_the_export|ctrl_s_during_export_all_waits_and_the_summary_appears|ctrl_s_during_single_export_writes_both_files|convert_between_export_all_steps_completes_before_the_next_step|pending_html_export_through_the_frame_shows_the_conversion|close_in_the_delivery_gap_is_vetoed|close_that_cannot_be_vetoed_shuts_the_presenter_down|save_converted_document_reports_failures_like_every_save|switch_away_stores_exactly_the_converted_text|conversion_result_saved_string_is_translated) .* ok$" $T/verbose.txt; grep -E "^(FAIL|ERROR):" $T/verbose.txt; tail -1 $T/verbose.txt
```

Expected:

```text
Ran 363 tests
OK
Ran 273 tests
OK
Ran 273 tests
OK
39
OK
```

- [ ] **Step 3: Criterion 3 (no KNOWN BUG pin of defects 1, 2, 3 or 6 is left) and the shuffled module order, six seeds** (one process each, about a minute and a half).

```bash
grep -rn "KNOWN BUG (P1-4 spec, defect [1236])" tests | wc -l
for s in 0 1 2 3 4 5; do $PY -B $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
0
      6 ran=1478 failures=0 errors=1 skipped=7 ['test_case_only_rename_still_renames']
```

- [ ] **Step 4: Criterion 4, catalogs.** A fresh template differs from the committed one only in `POT-Creation-Date`; `git diff` against `main` adds exactly the one entry (plus `#:` reference lines); 369 msgids, all translated, 0 fuzzy.

```bash
(cd $REPO && cmd //c "scripts\\generate-pot.bat $(cygpath -w $T/second.pot)"); echo "generate-pot exit $?"
diff --strip-trailing-cr <(grep -v '^"POT-Creation-Date: ' locales/dotexpress.pot) <(grep -v '^"POT-Creation-Date: ' $T/second.pot) && echo "fresh template identical apart from POT-Creation-Date"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
grep -c '^#, fuzzy' locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO diff 7aba2be -- client/locales/zh_TW/LC_MESSAGES/dotexpress.po | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[-+]#: '
```

Expected (no entry is fuzzy; the last command lists every changed line of the `.po` that is not a `#:` reference: only the new entry):

```text
generate-pot exit 0
fresh template identical apart from POT-Creation-Date
369 translated messages.
0
source msgids: 369 sha256 a94d370e253c7c605c90ea5896f725ef09030d45cf5e2906d98333556a2ec0e4
+#, python-brace-format
+msgid "Conversion completed. The result was saved to document \"{name}\"."
+msgstr "轉換完成。結果已儲存到文件「{name}」。"
+
```

- [ ] **Step 5: Criteria 5-7: fixtures, untouched modules, touched files, application data.**

```bash
BASE=7aba2be
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/shared client/dialog.py client/config.py client/log.py client/documents/controller.py client/documents/formats.py client/documents/workspace.py client/documents/session.py client/conversion/service.py client/conversion/output.py client/ui/shortcuts.py client/ui/menu_builder.py client/dual_view client/braille client/settings client/dictionaries && echo "shared, dialogs, config, log, controller, formats, workspace, session, conversion service and output, shortcuts, menus, dual view, braille, settings and dictionaries unchanged"
git -C $REPO diff --stat=200 $BASE -- client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) | diff - $T/app-data.sha256 && echo "application data unchanged"
for f in log workspace config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application data checked"
git -C $REPO status --short -- client scripts
```

Expected (the application data are the user's files in the main checkout, read only; `status` prints nothing):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
shared, dialogs, config, log, controller, formats, workspace, session, conversion service and output, shortcuts, menus, dual view, braille, settings and dictionaries unchanged
 client/conversion/jobs.py                      |  11 +++++
 client/documents/export_coordinator.py         |  39 ++++++++++++----
 client/documents/workspace_service.py          |  22 +++++++--
 client/gui.py                                  |  11 +++++
 client/locales/dotexpress.pot                  |  47 +++++++++++--------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 29047 -> 29183 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po |  47 +++++++++++--------
 client/tests/test_conversion_jobs.py           |  35 +++++++++++---
 client/tests/test_conversion_presenter.py      | 364 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 client/tests/test_export_coordinator.py        |  68 +++++++++++++++++++++++++--
 client/tests/test_gui_document_flows.py        | 373 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----------
 client/tests/test_i18n.py                      |   9 ++++
 client/tests/test_workspace_service.py         |  59 +++++++++++++++++++++++
 client/ui/conversion_presenter.py              | 182 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++---------------
 14 files changed, 1133 insertions(+), 134 deletions(-)
application data unchanged
worktree application data checked
```

- [ ] **Step 6: Criterion 8, mutation check** (30 mutants: the spec's list as 21 mutants (the result to the open document, memory only, the open document also written, the other document's output shown, its Dual View refreshed, the editor text stored, no text guard, `save_document` with the pending rule, the export replacing the running job, LIFO, the drain outside `finally`, `_completing` not consulted, `is_running()` as the thread state, `shutdown()` keeping the queue, the close not shutting down, the single export and Export All ignoring the fresh segments (two), the export writing the cache, the runner catching `Exception` only, the runner not logging), and nine more: no cache for the starting document, the old completion message, a discard not logged, a result given to a document opened later, `save_document` always writing, the frame not reporting a save error, `is_running()` ignoring the queue, `shutdown()` keeping the timer, the timer and new jobs after `shutdown()` (two); about a minute and a half). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f9_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
result-to-the-open-document: 9 caught: test_conversion_presenter.test_failed_save_of_the_originating_document_shows_no_completion_message, test_conversion_presenter.test_result_for_a_changed_text_is_discarded_and_logged, test_conversion_presenter.test_result_for_a_document_that_is_gone_is_discarded_and_logged, test_conversion_presenter.test_result_goes_to_the_document_that_started_the_conversion, and 5 more
memory-only-no-write: 6 caught: test_conversion_presenter.test_failed_save_of_the_originating_document_shows_no_completion_message, test_conversion_presenter.test_result_goes_to_the_document_that_started_the_conversion, test_gui_document_flows.test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document, test_gui_document_flows.test_failed_save_of_the_starting_document_reports_the_save_error, and 2 more
open-document-also-written: 7 caught: test_conversion_presenter.test_export_requested_while_a_conversion_runs_waits_for_it, test_conversion_presenter.test_later_job_uses_its_own_completion, test_conversion_presenter.test_manual_success_updates_output_document_cache_then_reports, test_conversion_presenter.test_result_for_the_open_document_follows_todays_path, and 3 more
other-document-shows-the-output: 6 caught: test_conversion_presenter.test_failed_save_of_the_originating_document_shows_no_completion_message, test_conversion_presenter.test_result_goes_to_the_document_that_started_the_conversion, test_gui_document_flows.test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document, test_gui_document_flows.test_failed_save_of_the_starting_document_reports_the_save_error, and 2 more
other-document-refreshes-the-dual-view: 6 caught: test_conversion_presenter.test_failed_save_of_the_originating_document_shows_no_completion_message, test_conversion_presenter.test_result_goes_to_the_document_that_started_the_conversion, test_gui_document_flows.test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document, test_gui_document_flows.test_failed_save_of_the_starting_document_reports_the_save_error, and 2 more
editor-text-stored: 6 caught: test_conversion_presenter.test_failed_save_of_the_originating_document_shows_no_completion_message, test_conversion_presenter.test_result_goes_to_the_document_that_started_the_conversion, test_gui_document_flows.test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document, test_gui_document_flows.test_failed_save_of_the_starting_document_reports_the_save_error, and 2 more
no-text-guard: 1 caught: test_conversion_presenter.test_result_for_a_changed_text_is_discarded_and_logged
no-cache-for-the-starting-document: 3 caught: test_conversion_presenter.test_failed_save_of_the_originating_document_shows_no_completion_message, test_conversion_presenter.test_result_goes_to_the_document_that_started_the_conversion, test_gui_document_flows.test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document
old-completion-message: 4 caught: test_conversion_presenter.test_result_goes_to_the_document_that_started_the_conversion, test_gui_document_flows.test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document, test_gui_document_flows.test_import_during_manual_conversion_does_not_receive_the_result, test_gui_document_flows.test_switch_away_stores_exactly_the_converted_text
discard-not-logged: 3 caught: test_conversion_presenter.test_result_for_a_changed_text_is_discarded_and_logged, test_conversion_presenter.test_result_for_a_document_that_is_gone_is_discarded_and_logged, test_conversion_presenter.test_result_without_a_starting_document
result-given-to-a-document-opened-later: 1 caught: test_conversion_presenter.test_result_without_a_starting_document
save-document-applies-the-pending-rule: 7 caught: test_gui_document_flows.test_ctrl_tab_during_manual_conversion_sends_result_to_the_starting_document, test_gui_document_flows.test_failed_save_of_the_starting_document_reports_the_save_error, test_gui_document_flows.test_import_during_manual_conversion_does_not_receive_the_result, test_gui_document_flows.test_switch_away_stores_exactly_the_converted_text, and 3 more
save-document-always-writes: 20 caught: test_gui_document_flows.test_close_with_an_unchanged_document_whose_save_would_fail_closes, test_gui_document_flows.test_switch_from_an_unchanged_document_whose_save_would_fail_opens_the_next, test_gui_document_flows.test_unchanged_read_only_document_blocks_neither_switch_nor_close, test_workspace_service.test_converted_pending_document_is_written, and 16 more
frame-save-error-not-reported: 2 caught: test_gui_document_flows.test_failed_save_of_the_starting_document_reports_the_save_error, test_gui_document_flows.test_save_converted_document_reports_failures_like_every_save
export-replaces-the-running-job: 13 caught: test_conversion_presenter.test_convert_returns_while_a_job_is_queued_or_in_the_delivery_gap, test_conversion_presenter.test_export_requested_while_a_conversion_runs_waits_for_it, test_conversion_presenter.test_failed_save_of_the_originating_document_shows_no_completion_message, test_conversion_presenter.test_is_running_covers_the_delivery_gap_and_the_queue, and 9 more
lifo: 1 caught: test_conversion_presenter.test_queued_jobs_run_in_request_order
drain-outside-finally: 1 caught: test_conversion_presenter.test_queue_drains_when_a_completion_raises
completing-not-consulted: 1 caught: test_conversion_presenter.test_request_during_a_completion_waits_until_it_returns
is-running-is-the-thread-state: 5 caught: test_conversion_presenter.test_convert_returns_while_a_job_is_queued_or_in_the_delivery_gap, test_conversion_presenter.test_is_running_and_missing_table_message_read_live_state, test_conversion_presenter.test_is_running_covers_the_delivery_gap_and_the_queue, test_conversion_presenter.test_shutdown_drops_the_running_and_queued_jobs, and 1 more
is-running-ignores-the-queue: 2 caught: test_conversion_presenter.test_convert_returns_while_a_job_is_queued_or_in_the_delivery_gap, test_conversion_presenter.test_is_running_covers_the_delivery_gap_and_the_queue
shutdown-keeps-the-queue: 1 caught: test_conversion_presenter.test_shutdown_drops_the_running_and_queued_jobs
shutdown-keeps-the-timer: 3 caught: test_conversion_presenter.test_shutdown_drops_the_running_and_queued_jobs, test_gui_document_flows.test_close_that_cannot_be_vetoed_shuts_the_presenter_down, test_gui_document_flows.test_close_while_running_vetoes_or_saves_and_closes
timer-after-shutdown-shows-the-dialog: 1 caught: test_conversion_presenter.test_shutdown_drops_the_running_and_queued_jobs
jobs-start-after-shutdown: 1 caught: test_conversion_presenter.test_shutdown_drops_the_running_and_queued_jobs
close-does-not-shut-down: 3 caught: test_gui_document_flows.test_close_asks_presenter_before_saving, test_gui_document_flows.test_close_that_cannot_be_vetoed_shuts_the_presenter_down, test_gui_document_flows.test_close_while_running_vetoes_or_saves_and_closes
single-export-ignores-the-fresh-segments: 2 caught: test_export_coordinator.test_html_export_of_a_pending_document_uses_its_conversion, test_gui_document_flows.test_pending_html_export_through_the_frame_shows_the_conversion
export-all-ignores-the-fresh-segments: 1 caught: test_export_coordinator.test_export_all_html_uses_each_pending_documents_conversion
export-writes-the-cache: 6 caught: test_export_coordinator.test_export_all_html_uses_each_pending_documents_conversion, test_export_coordinator.test_export_all_with_a_real_presenter_turn_by_turn, test_export_coordinator.test_html_export_of_a_pending_document_uses_its_conversion, test_gui_document_flows.test_export_all_mixed_documents_turn_by_turn, and 2 more
runner-catches-exception-only: 1 caught: test_conversion_jobs.test_base_exception_in_the_worker_is_delivered_too
runner-does-not-log: 2 caught: test_conversion_jobs.test_base_exception_in_the_worker_is_delivered_too, test_conversion_jobs.test_unexpected_worker_error_is_delivered_as_a_translation_failure
exit 0
```

### Task 7: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay. The dry run built the same code (the tree of Task 5) and ran Step 2's scripts against it and against `N-f8b2`; the blocks of Step 4 are those logs (see Dry Run). Run everything from the repository root, one item at a time, with nothing else driving the desktop. Never touch `D:\dxtest\N`, `B`, `N-p25`, `N-f3`, `N-f4*`, `N-f5*`, `N-f6*`, `N-f7`, `N-f8a`, `N-f8a2`, `N-f8b`, `N-f8b2` (only read and copied by the scripts) or the existing `D:\dxtest\auto*` folders; every run of this task uses a new folder whose name ends in `-f9`. Only processes whose exe lies under that folder are ended (`dx.kill_under`). The user may have DotExpress open: never end any other process. No script writes to the clipboard: the long texts reach the app only through package files, and keys go only to the main window while it is in the foreground (`f9gui.keys`).

- [ ] **Step 1: Build** (PowerShell, in the worktree). The main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`; `scripts\build-dotexpress.bat` calls `pyinstaller` from `PATH` and assumes no venv of its own.

```powershell
Set-Location D:\workspace\DotExpress-f9
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f9-build.log 2>&1"
if (Select-String -Path $env:TEMP\f9-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "ui\\conversion_presenter.py", "conversion\\jobs.py", "documents\\workspace_service.py", "documents\\export_coordinator.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress-f9\\client\\$m" -Quiet) { "$m bundled from the worktree" } }
if (Select-String -Path client\build\DotExpress\Analysis-00.toc -SimpleMatch "DotExpress-f9\\client\\gui.py" -Quiet) { "gui.py analyzed from the worktree" }
New-Item -ItemType Directory -Force D:\dxtest\N-f9 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f9\DotExpress.exe
(Get-Item D:\dxtest\N-f9\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f9\DotExpress.exe).Hash
git status --short -- client scripts
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f9-build.log`), the four `bundled from the worktree` lines (printed with their doubled backslash), `gui.py analyzed from the worktree`, a size near 48.77 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored). The `.mo` is bundled through `--add-data "locales;locales"`; items 85, 87 and 93 show its new string.

- [ ] **Step 2: Write the GUI scripts** into the new history folder with `apply_blocks.py` ("Task 7", "Step 2": 3 blocks). They reuse, unchanged, F-8b's `f8bgui.py` and through it F-8a's `f8agui.py`, F-7's `f7gui.py`, F-5's `f5gui.py` and `dx.py`, `docs.py`, `dicts.py`, `lock.py` of `2026-10-09-03-windows-verification/auto/`. Scripts use tabs.

File: `docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/auto/f9gui.py`

````python
"""Shared helpers for the F-9 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses f8bgui.py of F-8b (and through it f8agui.py, f7gui.py, f5gui.py and the helpers
of the 2026-10-09-03 Windows verification) unchanged. A conversion that runs for several
seconds comes from a long source text, LONG_REPEAT copies of UNIT (520,000 characters)
written into a package by script; the plan's dry run measured about 15 s for one
conversion of it. Keys go to the main window only while it is the foreground window
(``keys`` checks that first and stops the item otherwise, so no key reaches another
program). Output shows long texts by their length and first characters, the work folder
as <d> and the random part of a temporary file name as <rnd>. Nothing here touches the
clipboard.
"""
import os
import re
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
F8B = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-10-06-f8b-recovery-and-nul", "auto"))
sys.path.insert(0, F8B)
import f8bgui as B  # noqa: E402  (puts the F-8a, F-7, F-5 and 2026-10-09-03 auto folders on sys.path)
from f8bgui import A, D, F, G, dx  # noqa: E402

UNIT = "這是一段測試用的中文文字，DotExpress converts it to braille. 第二句還有數字 123 和符號。\n"
LONG_REPEAT = 8000
EXPORT_DIALOG = "匯出文件"
EXPORT_ALL_DIALOG = "匯出全部文件"
IMPORT_DIALOG = "匯入文件"
RANDOM_TMP = re.compile(r"(\.[\w.]+?\.dep\.)[A-Za-z0-9_]{8,16}(\.tmp)")


def long_text():
	return UNIT * LONG_REPEAT


def pending(d, name, text):
	"""workspace\\<name>.dep holding ``text`` with no braille yet (the app's pending marker)."""
	path = A.package(d, name, text, "")
	with zipfile.ZipFile(path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(f"{name}.meta.json", '{"braille_pending": true}')
	return path


def short(text):
	"""``repr`` of a short text; a long one as its length and first characters."""
	if text is None or len(text) <= 24:
		return repr(text)
	return f"<{len(text)} chars {text[:6]!r}...>"


def masked(d, value):
	"""``value`` as text, with the work folder as <d> and random temporary names as <rnd>."""
	text = B.show(value) if not isinstance(value, str) else value
	# A path inside an error message is a repr already, so it can be escaped twice.
	for form in (d.replace("\\", "\\" * 4), d.replace("\\", "\\" * 2), d):
		text = text.replace(form, "<d>")
	return RANDOM_TMP.sub(r"\1<rnd>\2", text)


def package(d, name):
	"""What workspace\\<name>.dep holds: its text and braille, shortened, and whether it is pending."""
	path = os.path.join(d, "workspace", f"{name}.dep")
	if not os.path.exists(path):
		return "missing"
	with zipfile.ZipFile(path) as archive:
		names = archive.namelist()
		text = archive.read(f"{name}.txt").decode("utf-8")
		braille = archive.read(f"{name}.brl").decode("utf-8")
	return f"text {short(text)} braille {short(braille)}{' (pending)' if f'{name}.meta.json' in names else ''}"


def editors(w):
	"""The window title and what the source and Braille Result editors show (WM_GETTEXT)."""
	source, braille = (control.window_text() for control in w.children(class_name="Edit")[:2])
	return f"{w.window_text()!r} source {short(source)} braille {short(braille)}"


def keys(w, sequence):
	"""Send ``sequence`` once the main window is the foreground window; raise if it never is."""
	import win32gui
	from pywinauto.keyboard import send_keys

	for _attempt in range(10):
		if win32gui.GetForegroundWindow() == w.handle:
			send_keys(sequence)
			time.sleep(0.5)
			return
		w.set_focus()
		time.sleep(0.3)
	raise RuntimeError(f"the main window is not in the foreground; {sequence!r} was not sent")


def convert(w):
	"""Ctrl+Enter in the source editor: a manual conversion of the open document."""
	w.children(class_name="Edit")[0].set_focus()
	keys(w, "^{ENTER}")


def box_open(app):
	"""Whether a message box is open now (a conversion that ended too soon shows its box).

	False if the windows cannot be read, as when the app has just ended.
	"""
	try:
		return bool(G.task_dialogs(app))
	except Exception:
		return False


def box(app, d, timeout):
	"""The next message box, answered with Enter (masked), or None if none opens within ``timeout`` s.

	How often Enter was pressed (f5gui.answer presses again if a key was lost) is left out:
	it depends on the foreground, not on the app.
	"""
	shown = G.answer_box(app, "enter", timeout=timeout)
	if shown is None:
		return None
	shown.pop("presses", None)
	return masked(d, shown)


def export_path(app, w, title, path):
	"""Fill the Save or folder dialog ``title`` with ``path`` and press its button (f7gui)."""
	G.path_dialog(app, w, title, path)


def html_summary(path):
	"""Whether an exported HTML file shows converted segments or the "No conversion data" page."""
	if not os.path.exists(path):
		return "missing"
	with open(path, encoding="utf-8") as stream:
		html = stream.read()
	segments = html.count('class="source"')
	return f"segments {segments} no-data {'No conversion data' in html}"


def written(folder):
	"""{file: its text, shortened} of an export folder."""
	result = {}
	for name in sorted(os.listdir(folder)):
		with open(os.path.join(folder, name), encoding="utf-8") as stream:
			result[name] = short(stream.read())
	return result


def call_state(sender):
	"""How a SessionMessage (f7gui) ended: its result, and whether it returned within 2 s."""
	if sender.returned_after is None:
		return "not returned"
	return {"ok": sender.ok, "result": sender.result, "within_2_s": sender.returned_after < 2}


def process_handle(pid):
	"""A handle to process ``pid`` that keeps its exit code readable after it ends."""
	import win32api

	# PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE
	return win32api.OpenProcess(0x1000 | 0x00100000, False, pid)


def ended(handle):
	"""None while the process runs; once it has ended, whether its exit code is nonzero."""
	import win32process

	code = win32process.GetExitCodeProcess(handle)
	return None if code == 259 else code != 0


def next_box(app, d, process, timeout):
	"""The next message box (as ``box`` gives it), "ended" if the app ends first, or None
	if neither happens within ``timeout`` s. ``process`` comes from ``process_handle``."""
	end = time.time() + timeout
	while time.time() < end:
		if ended(process) is not None:
			return "ended"
		if box_open(app):
			return box(app, d, timeout=5)
		time.sleep(0.5)
	return None


def finish(app, w, d):
	print("close:", masked(d, D.close(app, w)))
	dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/auto/item85.py`

````python
"""Items 85-88 and 93 (F-9 D1-D3, D5, D8): leaving the document that a conversion started from.

Usage: python item85.py <exe> <work folder> <85|86|87|88|93>
alpha holds a long text (pending), beta the short "beta body" with braille "⠃"; alpha is
open. Ctrl+Enter starts a conversion of alpha (about 15 s), then at once:
85: Ctrl+Tab to beta. Wait for the box; beta's editors; Ctrl+Tab back to alpha; Close;
    the packages; start again.
86: Ctrl+Tab and Ctrl+Shift+Tab (back to alpha) before the conversion ends.
87: Ctrl+O and import data\\imported.txt instead of Ctrl+Tab (the import opens it).
88: as 85, and then lock.py holds alpha.dep open (share read) until the box; unlock;
    Ctrl+Tab to alpha, Ctrl+Tab to beta; Close; the packages.
93: as 85, then WM_QUERYENDSESSION (ENDSESSION_LOGOFF) to the main window while the
    conversion runs; the box; Ctrl+Tab to alpha, Ctrl+Enter, and WM_ENDSESSION (wParam 1)
    while that conversion runs: the exit code, the files, gui.log.
Before F-9 (N-f8b2): the result goes to the document open when the conversion ends.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f9gui as H  # noqa: E402
from f9gui import A, B, D, F, G  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
H.pending(d, "alpha", H.long_text())
A.package(d, "beta", "beta body", "⠃")
app, w, shown = B.start(d)
print(f"{item} start: shown {shown} docs {D.docs(w)} {H.editors(w)}")
print(f"{item} alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
pid = app.process

H.convert(w)
if item == "87":
	imported = A.write(os.path.join(d, "data", "imported.txt"), "imported text".encode("utf-8"))
	H.keys(w, "^o")
	H.export_path(app, w, H.IMPORT_DIALOG, imported)
else:
	H.keys(w, "^{TAB}")
	if item == "86":
		H.keys(w, "^+{TAB}")
print(f"{item} while converting: docs {D.docs(w)} {H.editors(w)} box open {H.box_open(app)}")
holder = None
if item == "88":
	holder = F.lock(os.path.join(d, "workspace", "alpha.dep"), "r")
if item == "93":
	query = G.SessionMessage(w.handle, G.WM_QUERYENDSESSION)
	query.start()
	query.join(12)
	print(f"93 WM_QUERYENDSESSION: {H.call_state(query)} running {app.is_process_running()} box open {H.box_open(app)}")

print(f"{item} box: {H.box(app, d, timeout=90)}")
print(f"{item} after the box: {H.editors(w)}")
print(f"{item} alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
if holder is not None:
	F.unlock(holder)
print(f"{item} more boxes: {H.box(app, d, timeout=3)}")

if item in ("85", "88", "93"):
	H.keys(w, "^{TAB}")
	print(f"{item} Ctrl+Tab: {H.editors(w)} box {H.box(app, d, timeout=2)}")
if item == "88":
	H.keys(w, "^{TAB}")
	print(f"88 Ctrl+Tab: {H.editors(w)} box {H.box(app, d, timeout=2)}")
	print(f"88 alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
if item == "93":
	H.convert(w)
	print(f"93 converting again: box open {H.box_open(app)}")
	end = G.SessionMessage(w.handle, G.WM_ENDSESSION, wparam=1)
	end.start()
	end.join(12)
	print(f"93 WM_ENDSESSION: {H.call_state(end)} exit code {G.exit_code(pid, 5)}")
	print(f"93 files {A.files(d)} gui.log {G.gui_log(d)}")
	print(f"93 alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
	A.dx.kill_under(d)
	sys.exit(0)
print("close:", H.masked(d, D.close(app, w)))
print(f"{item} alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
print(f"{item} files {A.files(d)} gui.log {G.gui_log(d)}")
app, w, shown = B.start(d)
print(f"{item} restart: shown {shown} docs {D.docs(w)} {H.editors(w)}")
H.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/auto/item89.py`

````python
"""Items 89-92 (F-9 D4-D6): exports and Close while a conversion runs.

Usage: python item89.py <exe> <work folder> <89|90|91|92>
89: alpha (long, pending) is open. Ctrl+Enter, then Ctrl+S in the Braille Result editor
    and save <d>\\out\\alpha.brl: each box in turn; the editors; the file.
90: p1, p2 and p3 (long, pending); p1 is open. File > Export All > BRL into <d>\\out;
    during the first conversion, Ctrl+S in the Braille Result editor into <d>\\out2\\p1.brl:
    each box in turn; both folders.
91: File > Import data\\pend.txt (a pending document opens). File > Export > Dual View
    HTML into <d>\\out\\pend.html, then File > Export All > Dual View HTML into <d>\\outall:
    the boxes and what each file shows.
92: alpha (long, pending) is open. Ctrl+Enter; WM_CLOSE: the window stays; the box;
    WM_CLOSE again: the app exits; alpha.dep.
Before F-9 (N-f8b2): Ctrl+S starts a second conversion next to the running one (89, 90),
and with texts this long the app ends by itself; a pending document's HTML is the "No
conversion data" page (91); 92 is the same.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f9gui as H  # noqa: E402
from f9gui import A, B, D, G  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
out = os.path.join(d, "out")
os.makedirs(out)
if item in ("89", "92"):
	H.pending(d, "alpha", H.long_text())
elif item == "90":
	for name in ("p1", "p2", "p3"):
		H.pending(d, name, H.long_text())
app, w, shown = B.start(d)
print(f"{item} start: shown {shown} docs {D.docs(w)} {H.editors(w)}")
process = H.process_handle(app.process)


def boxes(label, first_timeout, count):
	"""Wait for up to ``count`` boxes, the first for ``first_timeout`` s and each next one for
	60 s; stop if the app ends by itself. Returns whether the app still runs."""
	timeout = first_timeout
	for number in range(1, count + 1):
		shown_box = H.next_box(app, d, process, timeout)
		if shown_box == "ended":
			print(f"{item} {label}: the app has ended by itself, exit code nonzero: {H.ended(process)}")
			return False
		print(f"{item} {label} box {number}: {shown_box}")
		if shown_box is None:
			return True
		print(f"{item} {label} after box {number}: {H.editors(w)}")
		timeout = 60
	return True


if item == "89":
	H.convert(w)
	w.children(class_name="Edit")[1].set_focus()
	H.keys(w, "^s")
	H.export_path(app, w, H.EXPORT_DIALOG, os.path.join(out, "alpha.brl"))
	print(f"89 exporting: box open {H.box_open(app)}")
	running = boxes("Ctrl+S", 90, 3)
	print(f"89 out {H.written(out)}")
	print(f"89 alpha.dep {H.package(d, 'alpha')}")
elif item == "90":
	out2 = os.path.join(d, "out2")
	os.makedirs(out2)
	G.menu(w, "#0->#7->#1", wait=0.5)
	H.export_path(app, w, H.EXPORT_ALL_DIALOG, out)
	w.children(class_name="Edit")[1].set_focus()
	H.keys(w, "^s")
	H.export_path(app, w, H.EXPORT_DIALOG, os.path.join(out2, "p1.brl"))
	print(f"90 exporting: box open {H.box_open(app)} out {H.written(out)} out2 {H.written(out2)}")
	running = boxes("Export All + Ctrl+S", 90, 3)
	print(f"90 out {H.written(out)}")
	print(f"90 out2 {H.written(out2)}")
elif item == "91":
	data = os.path.join(d, "data")
	A.write(os.path.join(data, "pend.txt"), "pending text\nsecond line".encode("utf-8"))
	B.import_files(app, w, data, ["pend.txt"])
	print(f"91 imported: docs {D.docs(w)} {H.editors(w)} pend.dep {H.package(d, 'pend')}")
	G.menu(w, "#0->#6->#2", wait=0.5)
	H.export_path(app, w, H.EXPORT_DIALOG, os.path.join(out, "pend.html"))
	print(f"91 export: box {H.box(app, d, timeout=30)}")
	print(f"91 pend.html {H.html_summary(os.path.join(out, 'pend.html'))}")
	outall = os.path.join(d, "outall")
	os.makedirs(outall)
	G.menu(w, "#0->#7->#2", wait=0.5)
	H.export_path(app, w, H.EXPORT_ALL_DIALOG, outall)
	print(f"91 export all: box {H.box(app, d, timeout=30)}")
	for name in sorted(os.listdir(outall)):
		print(f"91 outall\\{name} {H.html_summary(os.path.join(outall, name))}")
	print(f"91 {H.editors(w)} pend.dep {H.package(d, 'pend')}")
elif item == "92":
	import win32con

	H.convert(w)
	w.post_message(win32con.WM_CLOSE)
	time.sleep(2)
	print(f"92 WM_CLOSE while converting: running {app.is_process_running()} box open {H.box_open(app)} {H.editors(w)}")
	print(f"92 box: {H.box(app, d, timeout=90)}")
	print("close:", H.masked(d, D.close(app, w)))
	print(f"92 alpha.dep {H.package(d, 'alpha')} files {A.files(d)} gui.log {G.gui_log(d)}")
	A.dx.kill_under(d)
	sys.exit(0)
if item in ("89", "90") and not running:
	A.dx.kill_under(d)
else:
	H.finish(app, w, d)
````

- [ ] **Step 3: Items 85-93 on both builds** (Git Bash, from the repository root): first `D:\dxtest\N-f8b2\DotExpress.exe` ("Before", folders `auto<N>-f8b2-f9`), then the new build (folders `auto<N>-f9`). Each run makes its own work folder (`f8agui.prepare` deletes it first, after ending any process under it) and copies the exe into it. Read each log against Step 4 before the next run. The whole loop takes about 25 minutes.

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/auto
export PYTHONIOENCODING=utf-8
cd $REPO
for build in N-f8b2 N-f9; do
  tag=$([ $build = N-f8b2 ] && echo -f8b2-f9 || echo -f9)
  for i in 85 86 87 88 93; do "$UIA" $H/item85.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto$i$tag $i > /d/dxtest/auto$i$tag.log 2>&1; done
  for i in 89 90 91 92; do "$UIA" $H/item89.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto$i$tag $i > /d/dxtest/auto$i$tag.log 2>&1; done
done
```

- [ ] **Step 4: Expected logs.** Each log must equal its block line by line (`diff --strip-trailing-cr`). A box is `{'title': ..., 'main': ..., 'content': ..., 'buttons': [...], 'focus': ...}`, read through UIA (a message without a blank line has no main instruction, so `main` is `None`); how often Enter had to be pressed is left out. `<d>` is the item's work folder, `<rnd>` the random part of a temporary file name; a long text shows as `<length chars 'first characters'...>`; an editor's text is read with `WM_GETTEXT`, so its line ends are `\r\n` (the 520,000-character source is 528,000 characters there). The `focus` of a box is read from the system's focused element half a second after the box is brought forward; a notification of another program can show up there instead (a tool artifact, not a result: note it and run that item again in a new folder). If `f9gui.keys` stops an item because the main window is not in the foreground, or a `box open True` line shows that a conversion ended before the keys were sent, that is a tool problem too: run the item again in a new folder. Item 93's exit code after `WM_ENDSESSION` can be `-1073740940` instead of `0` (Spec Corrections 11): record it and run the item once more in a new folder. In items 89 and 90 the "Before" build ends by itself (Spec Corrections 14): the scripts wait for the next box or the end of the process, print `the app has ended by itself, exit code nonzero: True`, and read only files after it; Windows' Application log then holds an `ntdll.dll` fault with exception code `0xc0000374` for that exe, worth naming in `auto-results.md`.

**85** (spec 9a). Ctrl+Enter on `alpha` (long, pending), Ctrl+Tab to `beta` at once: the box `轉換完成。結果已儲存到文件「alpha」。`; `beta`'s editors keep `beta body` and `⠃`; `alpha.dep` holds the braille at once; Ctrl+Tab back shows it in `alpha`; after Close and a restart `alpha.dep` still holds it and `beta.dep` is unchanged. Before: `轉換完成。` while `beta` is open, `beta`'s Braille Result editor shows alpha's braille, the switch back writes it into `beta.dep`, and `alpha` stays pending (**the defect**).

After F-9, `D:\dxtest\auto85-f9.log`:

```text
85 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
85 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
85 while converting: docs ['alpha', 'beta'] 'beta - DotExpress' source 'beta body' braille '⠃' box open False
85 box: {'title': '資訊', 'main': None, 'content': '轉換完成。結果已儲存到文件「alpha」。', 'buttons': ['確定'], 'focus': '確定'}
85 after the box: 'beta - DotExpress' source 'beta body' braille '⠃'
85 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
85 more boxes: None
85 Ctrl+Tab: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...> box None
close: exited
85 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
85 files ['alpha.dep', 'beta.dep'] gui.log []
85 restart: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
close: exited
```

Before (N-f8b2), `D:\dxtest\auto85-f8b2-f9.log`:

```text
85 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
85 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
85 while converting: docs ['alpha', 'beta'] 'beta - DotExpress' source 'beta body' braille '⠃' box open False
85 box: {'title': '資訊', 'main': None, 'content': '轉換完成。', 'buttons': ['確定'], 'focus': '確定'}
85 after the box: 'beta - DotExpress' source 'beta body' braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
85 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
85 more boxes: None
85 Ctrl+Tab: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille '' box None
close: exited
85 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille <983999 chars '⠁⠮⠐⠊⠱⠐'...>
85 files ['alpha.dep', 'beta.dep'] gui.log []
85 restart: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
close: exited
```

**86** (9b). Ctrl+Tab and Ctrl+Shift+Tab (back to `alpha`) before the end: `轉換完成。`; `alpha`'s editor shows the braille; Close writes it. Before: identical.

After F-9, `D:\dxtest\auto86-f9.log`:

```text
86 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
86 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
86 while converting: docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille '' box open False
86 box: {'title': '資訊', 'main': None, 'content': '轉換完成。', 'buttons': ['確定'], 'focus': '確定'}
86 after the box: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
86 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
86 more boxes: None
close: exited
86 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
86 files ['alpha.dep', 'beta.dep'] gui.log []
86 restart: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
close: exited
```

Before (N-f8b2), `D:\dxtest\auto86-f8b2-f9.log`:

```text
86 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
86 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
86 while converting: docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille '' box open False
86 box: {'title': '資訊', 'main': None, 'content': '轉換完成。', 'buttons': ['確定'], 'focus': '確定'}
86 after the box: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
86 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
86 more boxes: None
close: exited
86 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
86 files ['alpha.dep', 'beta.dep'] gui.log []
86 restart: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
close: exited
```

**87** (9c). Ctrl+O and import `imported.txt` instead of Ctrl+Tab: the imported document opens and stays pending; the box names `alpha`, whose package holds the braille. Before: `轉換完成。`, the imported document's Braille Result editor shows alpha's braille (and Close writes it into `imported.dep`), `alpha` stays pending.

After F-9, `D:\dxtest\auto87-f9.log`:

```text
87 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
87 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
87 while converting: docs ['alpha', 'beta', 'imported'] 'imported - DotExpress' source 'imported text' braille '' box open False
87 box: {'title': '資訊', 'main': None, 'content': '轉換完成。結果已儲存到文件「alpha」。', 'buttons': ['確定'], 'focus': '確定'}
87 after the box: 'imported - DotExpress' source 'imported text' braille ''
87 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
87 more boxes: None
close: exited
87 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
87 files ['alpha.dep', 'beta.dep', 'imported.dep'] gui.log []
87 restart: shown [] docs ['alpha', 'beta', 'imported'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
close: exited
```

Before (N-f8b2), `D:\dxtest\auto87-f8b2-f9.log`:

```text
87 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
87 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
87 while converting: docs ['alpha', 'beta', 'imported'] 'imported - DotExpress' source 'imported text' braille '' box open False
87 box: {'title': '資訊', 'main': None, 'content': '轉換完成。', 'buttons': ['確定'], 'focus': '確定'}
87 after the box: 'imported - DotExpress' source 'imported text' braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
87 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
87 more boxes: None
close: exited
87 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
87 files ['alpha.dep', 'beta.dep', 'imported.dep'] gui.log []
87 restart: shown [] docs ['alpha', 'beta', 'imported'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
close: exited
```

**88** (9d). As 85, with `alpha.dep` held open (share read) until the box: the save error box (the package cannot be replaced) and no completion box; `alpha.dep` stays pending; after the unlock, Ctrl+Tab to `alpha` shows the result from memory and Ctrl+Tab away writes it. Before: as 85 before (the lock does not matter: nothing writes `alpha.dep`).

After F-9, `D:\dxtest\auto88-f9.log`:

```text
88 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
88 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
88 while converting: docs ['alpha', 'beta'] 'beta - DotExpress' source 'beta body' braille '⠃' box open False
lock: locked r
88 box: {'title': '錯誤', 'main': None, 'content': "儲存文件失敗：[WinError 5] 存取被拒。: '<d>\\\\workspace\\\\.alpha.dep.<rnd>.tmp' -> '<d>\\\\workspace\\\\alpha.dep'", 'buttons': ['確定'], 'focus': '確定'}
88 after the box: 'beta - DotExpress' source 'beta body' braille '⠃'
88 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
88 more boxes: None
88 Ctrl+Tab: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...> box None
88 Ctrl+Tab: 'beta - DotExpress' source 'beta body' braille '⠃' box None
88 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
close: exited
88 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
88 files ['alpha.dep', 'beta.dep'] gui.log []
88 restart: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
close: exited
```

Before (N-f8b2), `D:\dxtest\auto88-f8b2-f9.log`:

```text
88 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
88 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
88 while converting: docs ['alpha', 'beta'] 'beta - DotExpress' source 'beta body' braille '⠃' box open False
lock: locked r
88 box: {'title': '資訊', 'main': None, 'content': '轉換完成。', 'buttons': ['確定'], 'focus': '確定'}
88 after the box: 'beta - DotExpress' source 'beta body' braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
88 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
88 more boxes: None
88 Ctrl+Tab: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille '' box None
88 Ctrl+Tab: 'beta - DotExpress' source 'beta body' braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...> box None
88 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille <983999 chars '⠁⠮⠐⠊⠱⠐'...>
close: exited
88 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille <983999 chars '⠁⠮⠐⠊⠱⠐'...>
88 files ['alpha.dep', 'beta.dep'] gui.log []
88 restart: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
close: exited
```

**93** (9i). As 85; while the conversion runs, `WM_QUERYENDSESSION` (`ENDSESSION_LOGOFF`) returns 0 at once (refused) and the app keeps running; the box of 85; Ctrl+Tab to `alpha`, Ctrl+Enter, and `WM_ENDSESSION` (`wParam` 1) while that conversion runs: exit code 0, no `.tmp`, no `gui.log`. Before: the same session behavior; the result goes to `beta` as in 85 before. (A crash code here is the observation of Spec Corrections 11.)

After F-9, `D:\dxtest\auto93-f9.log`:

```text
93 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
93 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
93 while converting: docs ['alpha', 'beta'] 'beta - DotExpress' source 'beta body' braille '⠃' box open False
93 WM_QUERYENDSESSION: {'ok': 1, 'result': 0, 'within_2_s': True} running True box open False
93 box: {'title': '資訊', 'main': None, 'content': '轉換完成。結果已儲存到文件「alpha」。', 'buttons': ['確定'], 'focus': '確定'}
93 after the box: 'beta - DotExpress' source 'beta body' braille '⠃'
93 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
93 more boxes: None
93 Ctrl+Tab: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...> box None
93 converting again: box open False
93 WM_ENDSESSION: {'ok': 1, 'result': 0, 'within_2_s': True} exit code 0
93 files ['alpha.dep', 'beta.dep'] gui.log []
93 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> | beta.dep text 'beta body' braille '⠃'
```

Before (N-f8b2), `D:\dxtest\auto93-f8b2-f9.log`:

```text
93 start: shown [] docs ['alpha', 'beta'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
93 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
93 while converting: docs ['alpha', 'beta'] 'beta - DotExpress' source 'beta body' braille '⠃' box open False
93 WM_QUERYENDSESSION: {'ok': 1, 'result': 0, 'within_2_s': True} running True box open False
93 box: {'title': '資訊', 'main': None, 'content': '轉換完成。', 'buttons': ['確定'], 'focus': '確定'}
93 after the box: 'beta - DotExpress' source 'beta body' braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
93 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille '⠃'
93 more boxes: None
93 Ctrl+Tab: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille '' box None
93 converting again: box open False
93 WM_ENDSESSION: {'ok': 1, 'result': 0, 'within_2_s': True} exit code 0
93 files ['alpha.dep', 'beta.dep'] gui.log []
93 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending) | beta.dep text 'beta body' braille <983999 chars '⠁⠮⠐⠊⠱⠐'...>
```

**89** (9e). Ctrl+Enter on `alpha` (long, pending), Ctrl+S in the Braille Result editor and save `out\alpha.brl`: first `轉換完成。` with the braille shown, then the export runs and `文件已成功匯出。`; the file holds the braille. Before: no box at all: the second conversion runs next to the first and the app ends by itself (Spec Corrections 14); nothing is exported.

After F-9, `D:\dxtest\auto89-f9.log`:

```text
89 start: shown [] docs ['alpha'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
89 exporting: box open False
89 Ctrl+S box 1: {'title': '資訊', 'main': None, 'content': '轉換完成。', 'buttons': ['確定'], 'focus': '確定'}
89 Ctrl+S after box 1: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
89 Ctrl+S box 2: {'title': '匯出完成', 'main': None, 'content': '文件已成功匯出。', 'buttons': ['確定'], 'focus': '確定'}
89 Ctrl+S after box 2: 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille <1007998 chars '⠁⠮⠐⠊⠱⠐'...>
89 Ctrl+S box 3: None
89 out {'alpha.brl': "<983999 chars '⠁⠮⠐⠊⠱⠐'...>"}
89 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending)
close: exited
```

Before (N-f8b2), `D:\dxtest\auto89-f8b2-f9.log`:

```text
89 start: shown [] docs ['alpha'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
89 exporting: box open False
89 Ctrl+S: the app has ended by itself, exit code nonzero: True
89 out {}
89 alpha.dep text <520000 chars '這是一段測試'...> braille '' (pending)
```

**90** (9f). File > Export All > BRL with `p1`-`p3` (long, pending) and Ctrl+S during the first conversion: `文件已成功匯出。` for the Ctrl+S file, then the summary once at the end; `out` holds all three files, `out2` the Ctrl+S file. Before: the app ends by itself during the two conversions (Spec Corrections 14); no box, both folders stay empty.

After F-9, `D:\dxtest\auto90-f9.log`:

```text
90 start: shown [] docs ['p1', 'p2', 'p3'] 'p1 - DotExpress' source <528000 chars '這是一段測試'...> braille ''
90 exporting: box open False out {} out2 {}
90 Export All + Ctrl+S box 1: {'title': '匯出完成', 'main': None, 'content': '文件已成功匯出。', 'buttons': ['確定'], 'focus': '確定'}
90 Export All + Ctrl+S after box 1: 'p1 - DotExpress' source <528000 chars '這是一段測試'...> braille ''
90 Export All + Ctrl+S box 2: {'title': '匯出完成', 'main': None, 'content': 'All documents were exported successfully.', 'buttons': ['確定'], 'focus': '確定'}
90 Export All + Ctrl+S after box 2: 'p1 - DotExpress' source <528000 chars '這是一段測試'...> braille ''
90 Export All + Ctrl+S box 3: None
90 out {'p1.brl': "<983999 chars '⠁⠮⠐⠊⠱⠐'...>", 'p2.brl': "<983999 chars '⠁⠮⠐⠊⠱⠐'...>", 'p3.brl': "<983999 chars '⠁⠮⠐⠊⠱⠐'...>"}
90 out2 {'p1.brl': "<983999 chars '⠁⠮⠐⠊⠱⠐'...>"}
close: exited
```

Before (N-f8b2), `D:\dxtest\auto90-f8b2-f9.log`:

```text
90 start: shown [] docs ['p1', 'p2', 'p3'] 'p1 - DotExpress' source <528000 chars '這是一段測試'...> braille ''
90 exporting: box open False out {} out2 {}
90 Export All + Ctrl+S: the app has ended by itself, exit code nonzero: True
90 out {}
90 out2 {}
```

**91** (9g). Import `pend.txt` (pending), File > Export > Dual View HTML, then Export All as HTML: `pend.html` shows the converted segments both times; the default `new` (not pending, no cache) shows "No conversion data" (Spec Corrections 13). Before: every page is "No conversion data".

After F-9, `D:\dxtest\auto91-f9.log`:

```text
91 start: shown [] docs ['new'] 'new - DotExpress' source '' braille ''
91 imported: docs ['new', 'pend'] 'pend - DotExpress' source <25 chars 'pendin'...> braille '' pend.dep text 'pending text\nsecond line' braille '' (pending)
91 export: box {'title': '匯出完成', 'main': None, 'content': '文件已成功匯出。', 'buttons': ['確定'], 'focus': '確定'}
91 pend.html segments 23 no-data False
91 export all: box {'title': '匯出完成', 'main': None, 'content': 'All documents were exported successfully.', 'buttons': ['確定'], 'focus': '確定'}
91 outall\new.html segments 0 no-data True
91 outall\pend.html segments 23 no-data False
91 'pend - DotExpress' source <25 chars 'pendin'...> braille '' pend.dep text 'pending text\nsecond line' braille '' (pending)
close: exited
```

Before (N-f8b2), `D:\dxtest\auto91-f8b2-f9.log`:

```text
91 start: shown [] docs ['new'] 'new - DotExpress' source '' braille ''
91 imported: docs ['new', 'pend'] 'pend - DotExpress' source <25 chars 'pendin'...> braille '' pend.dep text 'pending text\nsecond line' braille '' (pending)
91 export: box {'title': '匯出完成', 'main': None, 'content': '文件已成功匯出。', 'buttons': ['確定'], 'focus': '確定'}
91 pend.html segments 0 no-data True
91 export all: box {'title': '匯出完成', 'main': None, 'content': 'All documents were exported successfully.', 'buttons': ['確定'], 'focus': '確定'}
91 outall\new.html segments 0 no-data True
91 outall\pend.html segments 0 no-data True
91 'pend - DotExpress' source <25 chars 'pendin'...> braille '' pend.dep text 'pending text\nsecond line' braille '' (pending)
close: exited
```

**92** (9h). `WM_CLOSE` during a conversion: the window stays and no box opens; then `轉換完成。`; the next Close exits and `alpha.dep` holds the braille. Before: identical.

After F-9, `D:\dxtest\auto92-f9.log`:

```text
92 start: shown [] docs ['alpha'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
92 WM_CLOSE while converting: running True box open False 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
92 box: {'title': '資訊', 'main': None, 'content': '轉換完成。', 'buttons': ['確定'], 'focus': '確定'}
close: exited
92 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> files ['alpha.dep'] gui.log []
```

Before (N-f8b2), `D:\dxtest\auto92-f8b2-f9.log`:

```text
92 start: shown [] docs ['alpha'] 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
92 WM_CLOSE while converting: running True box open False 'alpha - DotExpress' source <528000 chars '這是一段測試'...> braille ''
92 box: {'title': '資訊', 'main': None, 'content': '轉換完成。', 'buttons': ['確定'], 'focus': '確定'}
close: exited
92 alpha.dep text <520000 chars '這是一段測試'...> braille <983999 chars '⠁⠮⠐⠊⠱⠐'...> files ['alpha.dep'] gui.log []
```

- [ ] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/auto-results.md` in the style of `2026-10-10-06-f8b-recovery-and-nul/auto-results.md` (zh-TW): the build (PyInstaller version, `Build complete!`, the bundled modules, size, sha256), the method, then one row per item (85-93) with ✔/△/✘, the observed boxes, editors and packages after F-9 and the "Before" observations on N-f8b2. Any deviation from Step 4 is reported to the orchestrator before the commit, not explained away; a re-run after a GUI timing problem is recorded with the first attempt's log name. End the file with a short section **「仍需人工（使用者）」** for item 94, worded for the user (do not mark it done):

  > 94（NVDA）：請在 NVDA 執行中，把 `D:\dxtest\N-f9\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual94-f9\`，用 `auto/item85.py` 準備項目 85 的工作區（或把 `D:\dxtest\auto85-f9\workspace` 的初始內容複製過去：`alpha` 是很長的待轉換文件，`beta` 是短文件），然後：(1) 開啟 `alpha`，在原文編輯框按 Ctrl+Enter，立刻按 Ctrl+Tab 切到 `beta`；約 15 秒後出現「轉換完成。結果已儲存到文件「alpha」。」訊息框：記錄 NVDA 是否讀出文件名稱，以及按「確定」後焦點是否回到 `beta` 的編輯框；(2) 切回 `alpha`，按 Ctrl+Enter 後立刻在點字結果編輯框按 Ctrl+S 並存檔：記錄兩個訊息框（「轉換完成。」與「文件已成功匯出。」）是否依序讀出。若有讀不到或焦點跑掉的情形，請告訴我們。

Then add a section **Implementation Notes** at the end of this plan (what was applied, any deviation, the commit hashes and tree ids, the exe), as the F-8b plan has.

```bash
cd $REPO
git add docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/auto-results.md docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/auto/f9gui.py docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/auto/item85.py docs/superpowers/history/2026-10-10-07-f9-conversion-target-document/auto/item89.py docs/superpowers/plans/2026-10-10-f9-conversion-target-document.md
git diff --cached --stat
git commit -q -m "docs: record the F-9 packaged-build GUI checks (F-9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short -- client docs scripts
git rev-parse HEAD:client
```

Expected: the five files in the `--stat`, no `status` output, and the Task 5 tree id `2fffcc5e1cefbfe656061f1c477dcdaadd00115a` (the commit touches no file under `client/`). Do not merge `main` or push; the orchestrator decides.
