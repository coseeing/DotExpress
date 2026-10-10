# Localized Dialog Buttons, Surrogate-Safe Export, Close Re-entry (F-7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix F-W9, F-5 review M-7 and F-5 review M-5. The app's dialogs find their standard buttons among their own children only, so a name dialog shown again after "already exists" keeps the translated `確定` / `取消`, and the dictionary editor's OK saves even while the Settings or Text Processing dialog is open (today it closes without saving). Every message box goes through one helper, `ui.message_box.message_box`, which shows the translated OK; Yes/No boxes keep Windows' own labels. The editors are read through `replace_lone_surrogates`, so a pasted lone surrogate becomes U+FFFD in conversion, dual view and every export, while the editors keep what the user typed. Export reports every failure and logs unexpected ones; Export All goes on after one. A close event that arrives while the close dialog is open (Windows' `WM_QUERYENDSESSION`) is vetoed, so there is never a second dialog. No new strings; the catalogs stay byte-identical.

**Architecture:** Five commits on the client, each red first, in the spec's migration order. Task 1 changes the two button lookups of `client/dialog.py` to `FindWindow` and localizes the file-issues dialog (D1). Task 2 adds `client/ui/message_box.py` and migrates the 21 production call sites (20 `wx.MessageBox` and the About box) to it (D2-D4). Task 3 reads the editors through `_editor_text` (D5). Task 4 makes the export coordinator catch and log every exception (D6). Task 5 confirms M-5 and the lost dictionary edits on the pre-F-7 packaged build (D9), before Task 6 adds the close re-entry guard (D7). Task 7 verifies (suite, shuffled order, catalogs, fixtures, application data, 26 mutants), Task 8 builds the exe and runs the GUI checks (items 53-64; item 65 stays manual).

**Tech Stack:** Python 3.13 standard library (`ast`, `logging`, `subprocess`, `unittest`, `unittest.mock`), wxPython 4.2.5 (`wx.MessageDialog`, `wx.Window.FindWindow`), GNU gettext 0.23 (`xgettext`, `msgfmt`; checks only). Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-10-f7-dialog-buttons-surrogates-close-design.md` (+ `_zh-TW.md`), commit `d10dd94`, with the section "Corrected after planning" added in the plan commit (both languages). The user decided U1-U3 (2026-10-10); O1-O9 are the orchestrator's recommended defaults (the user may override them before the merge). No open question blocks the plan.

## Global Constraints

- Work in the worktree `D:\workspace\DotExpress-f7`, branch `fix/f7-dialog-buttons-surrogates-close` (HEAD is the plan commit on top of the spec commit `d10dd94`, which is on top of the F-6 head `fb7aff9`; F-6 is merged into `main` with a `--no-ff` merge whose tree equals `fb7aff9`, so the tree ids below hold for a branch rebased onto that merge too). Never switch branches, never push, never merge, never rewrite history. The main checkout `D:\workspace\DotExpress` is read only (another process may be merging there): this plan only reads its runtime files, its venv and the sha256 of its application data.
- Files that may change (16 under `client/`, nothing else): production `client/ui/message_box.py` (new, 4 spaces), `client/dialog.py`, `client/gui.py` (**tabs**; the `documents.workspace` import list in `gui.py` uses 4 spaces), `client/settings/dialogs.py`, `client/documents/export_coordinator.py` (4 spaces); tests `client/tests/test_message_box.py` and `client/tests/test_wx_call_sites.py` (new), `client/tests/wx_stub.py`, `client/tests/test_dialog_validation.py`, `client/tests/test_converting_dialog.py`, `client/tests/test_dictionary_entries_dialog.py`, `client/tests/test_settings_dialogs.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_export_coordinator.py` (4 spaces), `client/tests/test_dialog_display.py`, `client/tests/test_dictionary_management_dialog.py` (**tabs**); in Tasks 5 and 8 the new history folder `docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/` (scripts with tabs, results). `client/locales/` does not change (D8).
- Never touch `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data lives in the main checkout; the tests use temporary folders, every module that can log isolates the `dotexpress.gui` logger, and Task 0 and Task 7 compare the main checkout's sha256 read-only), `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (CRLF bytes), tracked `client/braille/` content, `client/braille/liblouis/`, `client/tests/fixtures/`, `client/locales/`, `scripts/`, `vendor/`, the submodule pointers, or the committed scripts and data of earlier history folders. Never stage the git-ignored runtime copies (liblouis DLL and tables, `louis_helper.py`, `mathcat/`, `include/liblouis/configure.ac`). Never run `py scripts\sync-nvda.py`. Never start `gui.py` from source. `git status --short -- client scripts` must stay empty between commits (`docs/` holds the untracked history folder from Task 5 until Task 8 commits it).
- The checkout uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply the blocks **with a script that reads them from this file** (`$T/tools/apply_blocks.py`, Task 0 Step 3), not by hand: a `File:` block is written as is (LF is fine; git normalizes it); an `Edit:` block is the line ``Edit: `path` `` followed by two fenced blocks, the exact old text and its replacement; the old text must occur exactly once in the file at that point (compare with CRLF converted to LF, keep the file's line endings). The blocks of one step are applied in order. Never edit with MSYS `sed -i` and never paste code through a shell heredoc. The Edit/Write tools turn `\uXXXX` escapes into the characters they stand for: the context lines of some blocks of `test_dictionary_entries_dialog.py` hold such escapes, so a block typed or pasted through those tools changes the tree. The new tests build the lone surrogate with `chr(0xD83D)` and write U+FFFD as the character itself, as F-5's tests do; they hold no `\u` escape.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf` (`git show HEAD:<path> | sha256sum`), unchanged.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly; look at `git diff --cached --stat` first; never `git commit -F -`.
- The only failing test before and after F-7 is the F-W6 error `test_dictionary_name_prompt ... test_case_only_rename_still_renames` (out of scope).
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`). Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks.
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress-f7
  MAIN=/d/workspace/DotExpress
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f7impl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the main checkout: Task 0 copies the git-ignored runtime from it if the checkout lacks it (the worktree already has it; the dry run's scratch clone did not), the venv is its, and Tasks 0 and 7 hash its application data read-only. Tasks 5 and 8 use PowerShell for the build and the UIA venv for the GUI scripts.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning" in the plan commit. The dry run found no error in decisions D1-D9 or in the behavior table; the corrections below are the post-F-6 call sites, counts and test mechanics, and details of the GUI items.

1. **Call sites after F-6** (`fb7aff9`, counted with the scan of Test Plan C1): 20 `wx.MessageBox` calls in production code (7 in `dialog.py`, 11 in `gui.py`, 2 in `settings/dialogs.py`), plus the About box. F-6 added one: **site 21**, `BrailleFrame.on_open_dictionary_management` (the editor guard of F-6 D6: `describe_unreadable_dictionary(...)`, `_("Error")`, `OK | ICON_ERROR`, `parent=self`; the task dialog shows the headline as its main instruction and the reason as its content, unchanged). F-6's Edit error box in Dictionary Management is site 6 (`show_error`). F-6 added no `wx.MessageDialog` and no `FindWindowById`. The site numbers 1-20 of the spec stay; their lines on `fb7aff9`: `dialog.py` 149, 166, 489, 500, 755, 758, 761; `gui.py` 446, 511, 705, 830, 859, 1075, 1078, 1083, 1111, 1115, site 21 at 1010, and the About box's `wx.MessageDialog` at 493 (`on_about`); `settings/dialogs.py` 158, 695.
2. **Counts: `Ran 1342`, `1352`, `1355`, `1361`, `1365`** (5, 10, 3, 6, 4 new tests; baseline 1337; `FAILED (errors=1, skipped=7)` throughout, F-W6 only). Task 1: B2, B3, B4, C3 and `test_scan_reads_the_production_modules` (the scan is not empty). Task 2: A1-A6, C1, C2, the About box (site 20) and the entry dialog's own message (site 1, which had no test). Task 3: Test Plan D1-D3. Task 4: D4-D8 and `test_importing_binds_no_log_file`. Task 6: E1-E4. msgids stay 364.
3. **The scan tests live in a new module `client/tests/test_wx_call_sites.py`** (4 spaces): C3 and the sanity test in Task 1, C1 and C2 in Task 2. A hit is reported as `<file>:<class>.<function>`.
4. **Re-pointing (Test Plan C4) is part of Task 2's green step,** not of its red step: patching `message_box` before the helper exists fails with `AttributeError` in every re-pointed test (the editor harness alone serves about 80). The red step holds the new tests only. Re-pointed: `test_dialog_validation` (the name-dialog harness), `test_dictionary_entries_dialog` (the editor harness patches `dialog.message_box`; its fake `wx` namespace loses `MessageBox`), `test_dictionary_management_dialog` (3 tests), `test_gui_document_flows` (19 patches, both `setUp`s included), `test_settings_dialogs` (2 tests). Every assertion stays; the recorded event keeps its label `"MessageBox"`. Site 18's test (`test_apply_failure_keeps_dialog_open_and_focuses_editor`) only asserted that a box was shown; it now asserts the message, caption, style and parent (C5).
5. **The editor harness keeps both lookups:** `FindWindow` returns the editor's own buttons, `FindWindowById` models wx's global search (the buttons of an older window first, when a test sets `other_dialog_buttons`, else the editor's own). So the existing editor tests pass before and after Task 1, and B3 sets the other dialog's buttons.
6. **Stub scopes (Design per File, `wx_stub.py`):** `ui.message_box` is an `isolate` name of every scope whose code under test imports it: `wx_stub.load_speech_dialog` (editor and management tests), `test_dialog_validation`, `test_converting_dialog`, `test_settings_dialogs`, `test_gui_document_flows`; the display scope evicts everything already. The `gui_frame_stubs` `_MessageDialog` gains `__enter__`/`__exit__`, `SetOKLabel`, `SetOKCancelLabels`, `SetYesNoLabels` (each `True`) and `ShowModal` returning `wx.ID_OK`, so an unpatched box still answers `wx.OK`, as the old stub `wx.MessageBox` did. `test_wx_stub.py` is unchanged.
7. **D6's logger is bound when it logs** (`get_logger("dotexpress.gui", "gui.log")` inside `_log_unexpected_export_error`), not at import, as F-6 review M-6 did for `read_problems`; `test_importing_binds_no_log_file` pins it, and `test_export_coordinator` isolates `dotexpress.gui` in `setUpModule`.
8. **D6 also fixes P1-4 defect 7:** Export All with a format that has no writer raised `ValueError` out of the menu handler, without a summary. `test_export_all_writer_value_error_stops_the_chain`, which pinned that KNOWN BUG, becomes `test_export_all_writer_value_error_is_listed_and_the_chain_goes_on` (both documents listed in the summary, two log records).
9. **Catalogs (D8):** not regenerated, byte-identical to `fb7aff9`. A fresh `generate-pot.bat` differs from the committed template only in `POT-Creation-Date` and in `#:` reference lines (lines moved in `dialog.py`, `gui.py`, `settings/dialogs.py` and `documents/export_coordinator.py`, and `ui/message_box.py` now refers to `OK` and `Cancel`); they are left as they are until the next string change regenerates the template. msgids 364, `msgfmt --statistics` 364 translated.
10. **Windows verification numbering:** items 4a-4l are **53-64**; the manual NVDA item is **65**. Scripts: `item53.py` (53, 56, 57), `item54.py` (54, 55), `item58.py` (58-60), `item61.py` (61-63), shared helpers `f7gui.py`; 64 runs F-5's `item38.py` directly with `38` and `39` (it takes the item as its third argument, which F-5's `rerun.py` does not pass).
11. **Item details:** 56's failing document is a folder named `alpha.brl` in the export folder (the overwrite question answered Yes; the summary lists `alpha: [Errno 13] Permission denied: ...`), not a lock; its Convert box is closed with Esc and the others with Enter. 57's conflict is a file `new.brl`. 61 converts `A` U+FFFD `B` first and compares: after F-7 the braille of the pasted surrogate equals it (`⡳⠭⠋⠋⠋⠙`, the escape `\xfffd`); before, it is `⡳⠭⠙⠦⠒⠙` (`\xd83d`). 58 counts the process's top-level windows titled `無法儲存文件` (both dialogs are owned by the main window) and answers the topmost first.
12. **Item 62 and 63, Before:** no message, but an empty `alpha.html` is left (the HTML writer's `Path.write_text` creates the file before the encoder fails); Export All leaves an empty `alpha.html`, no `new.html` and no summary. After F-7 a writer that fails with any error can still leave an empty or partial file (the writers are not atomic); that is unchanged and noted as a follow-up.
13. **D9 was also run by the planner** on `D:\dxtest\N-f6b\DotExpress.exe` (the build of `fb7aff9`'s code): item 58 showed **two** close dialogs within 3 s, the `SendMessageTimeoutW` call had not returned, and it returned (`ok 1`, result `0`, after 3.6 s and 4.2 s in two runs) only when the inner dialog was answered. Item 55 on the same build: the editor showed `OK` / `Cancel` and its OK closed without saving with either the Text Processing or the Settings dialog open (`d1.csv` kept only its header). M-5 and the lost-edits defect are confirmed on the packaged build; Task 5 repeats both before the D7 commit.
14. **Small fixes:** the timing of 58 is "returns at once" (measured `0.0 s`, result `0`) rather than "within about 1 s"; migration step 5's "Before step 6" means "before step 5"; acceptance criterion 2 adds `tests.test_wx_call_sites` and `tests.test_converting_dialog`; criterion 7's file list adds `test_wx_call_sites.py`, `test_converting_dialog.py` and `test_dialog_validation.py`; `_editor_text` is annotated `control: wx.TextCtrl`; the docstring of `localize_standard_buttons` does not name `FindWindowById`, so a plain `grep` of the production code finds none (Task 7 Step 4).

## Dry Run

The plan was executed on scratch clones of the worktree's branch at `d10dd94` with a stand-in plan commit (this plan and the corrected spec files) (`$SP/f7plan/r*`, never the worktree or the main checkout), by F-6's harness: it writes every `File:` block, applies every `Edit:` block exactly once (CRLF-aware), runs every `bash` block from `client/` with `REPO` set to the clone and `MAIN` to the main checkout (so Task 0's guarded copies filled the clone, and the application-data check read the real data read-only), and compares its stdout with the following `text` block. Tasks 5 and 8 need the desktop and are not part of the replay. The final replay (Tasks 0-4, 6 and 7 from a fresh clone) matched every expected block, including all red runs, the per-commit tree ids, the six shuffle seeds and the mutation output; no `client/log`, `client/workspace`, `client/dictionary` or `client/config.json` appeared in the clone. A second fresh clone ran Task 0 Step 3's bootstrap command and then applied every step with that `apply_blocks.py`, committing at the end of each task: the block counts of Task 0 Step 3 and the tree ids below, and Task 5's scripts equal to the ones run below (apart from line ends). Final sha256 after Task 6 (`git show HEAD:<path>`): `client/ui/message_box.py` `4fed944b2961927acccf019c4978b4191cdd8ab69f15e2ccf11a3782b7de8dd1`, `client/dialog.py` `8f39a58449709f7cfa737edc167b0b3916dd98b19687c1b1f48bde3f85dc48e3`, `client/gui.py` `cd463cbcb9ab0f2d425f0f8c15d4a4a334a3f8d9921cc1c3a3f855bbd42e6e7c`, `client/settings/dialogs.py` `53218c9086a36ac08c6695199a41dd88efba7d7285234a3d5827519df17cb066`, `client/documents/export_coordinator.py` `4de672b892aeaf7180f5115a01b3b822a5bfdfb8bb6183d0838efd333ba83d60`, `client/tests/wx_stub.py` `a3ef663b4c68cfa7217bed5b46446fcc220ac7545d88405ed0797d7e78309ed4`.

Tasks 5 and 8 were run too. The second clone, at Task 6, was built with Task 8 Step 1's command ("Build complete!", 48,752,349 bytes; the four modules from the clone; `D:\dxtest\dryN2-f7`), and Task 5's scripts, written by `apply_blocks.py`, ran against `D:\dxtest\N-f6b\DotExpress.exe` (Task 5 Step 2) and against that build (Task 8 Step 2). They printed exactly the lines of Task 8 Step 3's table, each item once, in `D:\dxtest\dry*-f7` folders that were deleted afterwards (no `D:\dxtest\auto*-f7` folder exists yet). An earlier draft of `item58.py` pressed Esc in the oldest close dialog first; a key there cannot end the nested modal loop, so the script now answers the topmost dialog (z-order) first. The planner had also run 58 and 55 on `N-f6b` before writing the guard (Spec Corrections 13). Item 65 (NVDA) was not run.

## Review Focus

1. **The lookups are scoped and the editor saves** (D1): `FindWindow` everywhere, the editor binds its own OK, the other dialog's buttons are untouched (B1-B3; mutants `localize-searches-every-window`, `editor-binds-ok-of-any-window`; GUI 55 before and after).
2. **The helper is a drop-in** (D2, D3): same arguments, styles, owners and return values at all 21 sites; only OK and OK/Cancel get labels (A1-A6, C1, C2, the re-pointed tests; 8 mutants).
3. **The editors are never changed** (D5): no `SetValue`, no `ChangeValue`; conversion, the saved package and the dual view hold U+FFFD (D1-D3; GUI 61).
4. **Every export failure is reported, unexpected ones logged once, and the tests never write the real log** (D6): `OSError` not logged; the logger bound only when logging (D4-D8, the import test; 5 mutants).
5. **Close re-entry** (D7): a vetoable re-entry is vetoed without a save or a dialog; a non-vetoable one runs D8 once and the outer close stops; the flag is reset in `finally` (E1-E4; 7 mutants; GUI 58-60).

## File Map

- Task 1: `client/tests/test_dialog_display.py` (B1, B2, B4), `client/tests/test_dictionary_entries_dialog.py` (harness lookups, B3), new `client/tests/test_wx_call_sites.py` (C3, the sanity test); `client/dialog.py` (`localize_standard_buttons`, `FileIssuesDialog.__init__`, `DictionaryEntriesDialog._build_ui`).
- Task 2: new `client/tests/test_message_box.py` (A1-A6), `client/tests/test_wx_call_sites.py` (C1, C2), `client/tests/test_dialog_validation.py` (site 1), `client/tests/test_gui_document_flows.py` (site 20); new `client/ui/message_box.py`; `client/dialog.py`, `client/gui.py`, `client/settings/dialogs.py` (the 21 sites); `client/tests/wx_stub.py`; re-pointed `client/tests/test_dialog_validation.py`, `test_converting_dialog.py`, `test_dictionary_entries_dialog.py`, `test_dictionary_management_dialog.py`, `test_gui_document_flows.py`, `test_settings_dialogs.py`.
- Task 3: `client/tests/test_gui_document_flows.py` (D1-D3); `client/gui.py` (`_editor_text`, `_save_open_document`, `get_source_text`).
- Task 4: `client/tests/test_export_coordinator.py` (D4-D8, the import test, the rewritten defect-7 test); `client/documents/export_coordinator.py`.
- Task 5 (no commit): the GUI scripts in the new history folder; items 53-55, 58 and 61-63 on the pre-F-7 build.
- Task 6: `client/tests/test_gui_document_flows.py` (the dialog hook, E1-E4); `client/gui.py` (`_closing`, `_close_finished`, `_on_close`, `_close`, `_on_close_reentered`, `_finish_close`, one check in `_save_open_document_before_close`).
- Task 8: `docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/` (`auto/f7gui.py`, `auto/item53.py`, `auto/item54.py`, `auto/item58.py`, `auto/item61.py`, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | `HEAD:client` |
| --- | --- | --- | --- | --- |
| baseline (`d10dd94` + plan) | - | 1337 | `FAILED (errors=1, skipped=7)` | `31560e3e2f2984f5a263acc271e1937fb267c152` |
| 1 button lookups | 5 (B2, B3, B4, C3, scan sanity); 3 changed (B1) | 1342 | `FAILED (errors=1, skipped=7)` | `f6a7409dd7196d6b1310ce4493e5a844356c2339` |
| 2 message boxes | 10 (A1-A6, C1, C2, sites 1 and 20); patches re-pointed (Spec Corrections 4) | 1352 | `FAILED (errors=1, skipped=7)` | `79ee79a7c70413df0305e3136ce88e071397e5d0` |
| 3 editor reads | 3 (D1-D3) | 1355 | `FAILED (errors=1, skipped=7)` | `7532bf2a6b19387398ece4e0f50c9fe430e2ae40` |
| 4 export failures | 6 (D4-D8, import); 1 rewritten (defect 7) | 1361 | `FAILED (errors=1, skipped=7)` | `f9563449fabf770733188b74f5734b3eb09dd7db` |
| 6 close re-entry | 4 (E1-E4) | 1365 | `FAILED (errors=1, skipped=7)` | `652dabacc5f65dec492a86672309e9c4da5af8cb` |
| 8 GUI results (docs only) | - | 1365 | `FAILED (errors=1, skipped=7)` | `652dabacc5f65dec492a86672309e9c4da5af8cb` |

The error is F-W6 throughout; the 7 skips are POSIX-only tests. The spec's acceptance-criterion-2 set (with `tests.test_wx_call_sites` and `tests.test_converting_dialog`) goes from `Ran 443`, `OK` (without the two new modules) to `Ran 471`, `OK`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 by the block script: `brief.py`, `msgid_scan.py` and `shuffle_harness.py` (F-6's, unchanged), `f7_mutants.py` (26 mutants of the code after Task 6, run on a copy of `client/`; the repository is never changed) and `apply_blocks.py` (F-6's, applies the `File:` and `Edit:` blocks of one step of this plan).

---

### Task 0: Baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short -- client docs scripts
git -C $REPO log --format=%s -3
git -C $REPO branch --show-current
git -C $REPO rev-parse HEAD~2:client
git -C $REPO diff --stat fb7aff9 -- client
```

Expected (`status` and the diff print nothing; `HEAD~2` is the F-6 head `fb7aff9`, or main's F-6 merge if the branch was rebased onto it: the same client tree):

```text
docs: plan for localized dialog buttons, surrogate-safe export, close re-entry (F-7)
docs: spec for localized dialog buttons, surrogate-safe export, close re-entry (F-7)
docs: F-6 review record
fix/f7-dialog-buttons-surrogates-close
31560e3e2f2984f5a263acc271e1937fb267c152
```

- [ ] **Step 2: The git-ignored runtime the tests load.** The worktree already has the generated liblouis DLL and tables, `louis_helper.py`, MathCAT and the submodule's `configure.ac` (copied from the main checkout as in F-3's Task 0); the guarded copies below do nothing there (they filled the dry run's scratch clone). Never stage these files.

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

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed). `brief.py`, `msgid_scan.py` and `shuffle_harness.py` are F-6's, unchanged; `apply_blocks.py` is F-6's with its docstring naming this plan.

File: `$T/tools/brief.py`

````python
"""Condense unittest output read from stdin (throwaway, not committed).

Keeps the FAIL/ERROR headers and exception lines, cut to 160 characters (a cut line is
printed once, so the subtests of one test give one header), the "Ran" line without its
timing and the final OK/FAILED line, so that outputs can be compared with the plan. The
client directory is shown as <client>; temporary directories (tempfile.mkdtemp names,
also in repr form with doubled backslashes) as <tmp>; random temporary-file suffixes as
<rnd>.
"""
import re
import sys
from pathlib import Path

CLIENT = str(Path.cwd())
CLIENT_REPR = CLIENT.replace("\\", "\\\\")
TMPDIR = re.compile(r"[A-Za-z]:(?:\\\\|\\)(?:[^'\"\s]*?(?:\\\\|\\))?tmp[a-z0-9_]{8}")
RANDOM_TMP = re.compile(r"(\.[\w.]+?\.(?:dep|csv)\.)[a-z0-9_]{8,16}(\.tmp)")
seen = set()
for line in sys.stdin:
    line = line.rstrip("\n").replace(CLIENT_REPR, "<client>").replace(CLIENT, "<client>")
    line = TMPDIR.sub("<tmp>", line)
    line = RANDOM_TMP.sub(r"\1<rnd>\2", line)
    if re.match(r"(FAIL|ERROR): ", line) or re.match(r"[A-Za-z_.]*(Error|Exception|Interrupt): ", line):
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

File: `$T/tools/f7_mutants.py`

````python
"""Run the F-7 tests against deliberately broken code (throwaway, not committed).

Usage: python f7_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one file of the copy (one exact, unique replacement), runs the F-7 test
modules there, prints which tests caught it and restores the file. The repository is
never changed. Matches the code after Task 6. Exit status 1 if a mutant is not caught or
its pattern is not found exactly once. Python runs with -B (no bytecode is written): a
restored file can have the size and modification second of the mutant, and a cached
.pyc would then shadow it.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

DIALOG = "dialog.py"
GUI = "gui.py"
HELPER = "ui/message_box.py"
SETTINGS = "settings/dialogs.py"
EXPORT = "documents/export_coordinator.py"
MUTANTS = {
	# D1: a dialog's standard buttons are looked up among its own children.
	"localize-searches-every-window": (
		DIALOG,
		"\t\t\tbutton = dialog.FindWindow(button_id)\n",
		"\t\t\tbutton = dialog.FindWindowById(button_id)\n",
	),
	"editor-binds-ok-of-any-window": (
		DIALOG,
		"\t\t\tok_button = self.FindWindow(wx.ID_OK)\n",
		"\t\t\tok_button = self.FindWindowById(wx.ID_OK)\n",
	),
	"file-issues-ok-not-localized": (DIALOG, "\t\t\tlocalize_standard_buttons(self, wx.OK, button_sizer)\n", ""),
	# D2: the helper.
	"helper-without-the-ok-label": (HELPER, '                dialog.SetOKLabel(_("OK"))\n', "                pass\n"),
	"helper-labels-yes-no-too": (HELPER, "        if not style & wx.YES_NO:\n", "        if True:\n"),
	"helper-ok-cancel-sets-only-ok": (
		HELPER,
		'dialog.SetOKCancelLabels(_("OK"), _("Cancel"))',
		'dialog.SetOKLabel(_("OK"))',
	),
	"helper-returns-the-raw-id": (
		HELPER,
		"    return {wx.ID_OK: wx.OK, wx.ID_YES: wx.YES, wx.ID_NO: wx.NO}.get(answer, wx.CANCEL)\n",
		"    return answer\n",
	),
	# D3: every message box goes through the helper.
	"dialog-site-back-to-wx-message-box": (
		DIALOG,
		'\t\tmessage_box(message, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)\n',
		'\t\twx.MessageBox(message, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)\n',
	),
	"gui-site-back-to-wx-message-box": (
		GUI,
		"\t\tmessage_box(message, caption, wx.OK | wx.ICON_WARNING, parent=self)\n",
		"\t\twx.MessageBox(message, caption, wx.OK | wx.ICON_WARNING, parent=self)\n",
	),
	"settings-site-back-to-wx-message-box": (
		SETTINGS,
		"            message_box(\n                _(\"Unable to save text processing script: {error}\")",
		"            wx.MessageBox(\n                _(\"Unable to save text processing script: {error}\")",
	),
	"about-box-back-to-wx-message-box": (
		GUI,
		"\t\tmessage_box(about.aboutMessage,",
		"\t\twx.MessageBox(about.aboutMessage,",
	),
	# D5: the editors are read through replace_lone_surrogates.
	"source-text-without-the-replacement": (
		GUI,
		"\tdef get_source_text(self) -> str:\n\t\treturn self._editor_text(self.input_txt)\n",
		"\tdef get_source_text(self) -> str:\n\t\treturn self.input_txt.GetValue()\n",
	),
	"saved-text-without-the-replacement": (
		GUI,
		"\t\t\ttext=self._editor_text(self.input_txt),\n",
		"\t\t\ttext=self.input_txt.GetValue(),\n",
	),
	"saved-braille-without-the-replacement": (
		GUI,
		"\t\t\tbraille=self._editor_text(self.output_txt),\n",
		"\t\t\tbraille=self.output_txt.GetValue(),\n",
	),
	# D6: export reports every failure.
	"single-export-catches-only-os-error": (
		EXPORT,
		"            self.write_document(destination_path, document, format_key)\n        except Exception as exc:\n",
		"            self.write_document(destination_path, document, format_key)\n        except OSError as exc:\n",
	),
	"batch-catches-only-os-error": (
		EXPORT,
		"                self.write_document(destination_path, export_document, format_key)\n            except Exception as exc:\n",
		"                self.write_document(destination_path, export_document, format_key)\n            except OSError as exc:\n",
	),
	"os-error-logged-too": (EXPORT, "        if not isinstance(error, OSError):\n", "        if True:\n"),
	"unexpected-export-error-not-logged": (EXPORT, "        if not isinstance(error, OSError):\n", "        if False:\n"),
	"export-logger-bound-at-import": (
		EXPORT,
		"CallAfter = Callable[..., object]\n",
		'CallAfter = Callable[..., object]\nlogger = get_logger("dotexpress.gui", "gui.log")\n',
	),
	# D7: a close that arrives during a close is vetoed.
	"no-reentry-guard": (GUI, "\t\tif self._closing:\n\t\t\tself._on_close_reentered(evt)\n\t\t\treturn\n", ""),
	"reentry-skips-instead-of-vetoing": (
		GUI,
		"\t\tif evt.CanVeto():\n\t\t\tevt.Veto()\n\t\t\treturn\n\t\tself._save_open_document_before_close(False)\n",
		"\t\tif evt.CanVeto():\n\t\t\tevt.Skip()\n\t\t\treturn\n\t\tself._save_open_document_before_close(False)\n",
	),
	"reentry-without-the-save": (
		GUI,
		"\t\tself._save_open_document_before_close(False)\n\t\tself._finish_close(evt)\n",
		"\t\tself._finish_close(evt)\n",
	),
	"closing-not-reset": (GUI, "\t\tfinally:\n\t\t\tself._closing = False\n", "\t\tfinally:\n\t\t\tpass\n"),
	"outer-loop-ignores-a-finished-close": (
		GUI,
		"\t\t\t\tif self._close_finished:\n\t\t\t\t\t# A nested close that could not be vetoed closed the frame meanwhile (F-7, M-5).\n\t\t\t\t\treturn True\n",
		"",
	),
	"outer-close-ignores-a-finished-close": (
		GUI,
		"\t\tif self._close_finished:\n\t\t\t# A nested close that could not be vetoed already closed the frame (M-5).\n\t\t\treturn\n",
		"",
	),
	"finish-close-not-recorded": (GUI, "\t\tself._close_finished = True\n", ""),
}
MODULES = (
	"tests.test_message_box",
	"tests.test_wx_call_sites",
	"tests.test_dialog_display",
	"tests.test_dialog_validation",
	"tests.test_converting_dialog",
	"tests.test_dictionary_entries_dialog",
	"tests.test_dictionary_management_dialog",
	"tests.test_settings_dialogs",
	"tests.test_gui_document_flows",
	"tests.test_export_coordinator",
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
"""Apply the File: and Edit: blocks of one step of the F-7 plan (throwaway, not committed).

Usage: python apply_blocks.py <plan.md> <repo> <T> "<task>" "<step>"
  for example: python apply_blocks.py plan.md D:/workspace/DotExpress-f7 <T> "Task 1" "Step 1"

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
PLAN=$REPO/docs/superpowers/plans/2026-10-10-f7-dialog-buttons-surrogates-close.md
$PY -c "import sys; from pathlib import Path; text = Path(sys.argv[1]).read_bytes().decode('utf-8').replace(chr(13) + chr(10), chr(10)); start = text.index('File: \`\$T/tools/apply_blocks.py\`'); body = text[text.index(chr(10), text.index('\`\`\`\`python', start)) + 1:text.index(chr(10) + '\`\`\`\`' + chr(10), start)]; Path(sys.argv[2]).write_bytes((body + chr(10)).encode('utf-8')); print('apply_blocks.py extracted')" "$PLAN" "$T/tools/apply_blocks.py"
$PY $T/tools/apply_blocks.py "$PLAN" $REPO $T "Task 0" "Step 3"
```

Expected:

```text
apply_blocks.py extracted
wrote $T/tools/brief.py
wrote $T/tools/msgid_scan.py
wrote $T/tools/shuffle_harness.py
wrote $T/tools/f7_mutants.py
wrote $T/tools/apply_blocks.py
5 blocks applied (Task 0, Step 3)
```

From then on apply every step's blocks with `apply_blocks.py`, for example `$PY $T/tools/apply_blocks.py ../docs/superpowers/plans/2026-10-10-f7-dialog-buttons-surrogates-close.md $REPO $T "Task 1" "Step 1"`; it prints `N blocks applied` (Task 0 Step 3: 5; Task 1 Step 1: 10, Step 2: 4; Task 2 Step 1: 6, Step 2: 53; Task 3 Step 1: 4, Step 2: 3; Task 4 Step 1: 5, Step 2: 4; Task 5 Step 1: 5; Task 6 Step 1: 3, Step 2: 3).

- [ ] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, catalogs, tree, application data.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_dialog_display tests.test_dialog_validation tests.test_converting_dialog tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_settings_dialogs tests.test_gui_document_flows tests.test_export_coordinator tests.test_wx_stub 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "msgfmt rebuilds the committed .mo byte for byte"
grep -c 'wx.MessageBox(' dialog.py gui.py settings/dialogs.py
grep -n 'FindWindowById\|wx.MessageDialog(' dialog.py gui.py settings/dialogs.py
git -C $REPO rev-parse HEAD:client
for f in dictionary workspace log config.json; do test -e $REPO/client/$f && echo "unexpected: client/$f"; done; echo "no application data in the checkout"
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) > $T/app-data.sha256; wc -l < $T/app-data.sha256
```

Expected (the second `Ran` line is the acceptance-criterion-2 set without the two new modules; the 20 `wx.MessageBox(` and the two `FindWindowById` and two `wx.MessageDialog(` lines are the call sites of Spec Corrections 1; the last line counts the files of the user's application data in the main checkout, recorded read-only for Task 7; if the user has used the app since the dry run, that number differs, which is fine):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1337 tests
FAILED (errors=1, skipped=7)
Ran 443 tests
OK
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
source msgids: 364 sha256 7b53ff311c9e446767b0884bfc03148afe030ca7e15899d6ee6919e77c664ea7
locales/dotexpress.pot:365
locales/zh_TW/LC_MESSAGES/dotexpress.po:365
364 translated messages.
msgfmt rebuilds the committed .mo byte for byte
dialog.py:7
gui.py:11
settings/dialogs.py:2
dialog.py:56:			button = dialog.FindWindowById(button_id)
dialog.py:393:			ok_button = self.FindWindowById(wx.ID_OK)
gui.py:474:		with wx.MessageDialog(
gui.py:493:		with wx.MessageDialog(
31560e3e2f2984f5a263acc271e1937fb267c152
no application data in the checkout
4
```

### Task 1: Look up standard dialog buttons among the dialog's own children (D1)

- [ ] **Step 1: Red: B1-B4, C3 and the scan's sanity test.** `test_dialog_display.py` keeps its tabs (the three existing `localize_standard_buttons` tests set `FindWindow` instead of `FindWindowById`); the editor harness of `test_dictionary_entries_dialog.py` (4 spaces) answers both lookups (Spec Corrections 5); the new scan module uses 4 spaces.

Edit: `client/tests/test_dialog_display.py`

```python
import unittest
from unittest.mock import Mock

from tests import wx_stub

```

```python
import unittest
from unittest.mock import MagicMock, Mock, patch

from tests import wx_stub

```

Edit: `client/tests/test_dialog_display.py`

```python
			dialog_module.wx.ID_OK: Mock(),
			dialog_module.wx.ID_CANCEL: Mock(),
		}
		dialog.FindWindowById.side_effect = buttons.get

		translations = {"OK": "確定", "Cancel": "取消", "Apply": "套用"}
		previous_gettext = dialog_module._
```

```python
			dialog_module.wx.ID_OK: Mock(),
			dialog_module.wx.ID_CANCEL: Mock(),
		}
		dialog.FindWindow.side_effect = buttons.get

		translations = {"OK": "確定", "Cancel": "取消", "Apply": "套用"}
		previous_gettext = dialog_module._
```

Edit: `client/tests/test_dialog_display.py`

```python
	def test_localizes_close_button(self):
		dialog = Mock()
		close_button = Mock()
		dialog.FindWindowById.return_value = close_button

		previous_gettext = dialog_module._
		dialog_module._ = {"Close": "關閉"}.get
```

```python
	def test_localizes_close_button(self):
		dialog = Mock()
		close_button = Mock()
		dialog.FindWindow.return_value = close_button

		previous_gettext = dialog_module._
		dialog_module._ = {"Close": "關閉"}.get
```

Edit: `client/tests/test_dialog_display.py`

```python

	def test_localizes_buttons_from_standard_button_sizer(self):
		dialog = Mock()
		dialog.FindWindowById.return_value = None
		button_sizer = Mock()
		button_sizer.GetAffirmativeButton.return_value = Mock()
		button_sizer.GetCancelButton.return_value = Mock()
```

```python

	def test_localizes_buttons_from_standard_button_sizer(self):
		dialog = Mock()
		dialog.FindWindow.return_value = None
		button_sizer = Mock()
		button_sizer.GetAffirmativeButton.return_value = Mock()
		button_sizer.GetCancelButton.return_value = Mock()
```

Edit: `client/tests/test_dialog_display.py`

```python
		button_sizer.GetAffirmativeButton.return_value.SetLabel.assert_called_once_with("確定")
		button_sizer.GetCancelButton.return_value.SetLabel.assert_called_once_with("取消")


if __name__ == "__main__":
	unittest.main()
```

```python
		button_sizer.GetAffirmativeButton.return_value.SetLabel.assert_called_once_with("確定")
		button_sizer.GetCancelButton.return_value.SetLabel.assert_called_once_with("取消")

	def test_localize_ignores_buttons_of_other_windows(self):
		# F-W9: called on a dialog, wx.Window.FindWindowById searches every top-level window
		# and can return another dialog's button (a destroyed name dialog, an open Settings).
		dialog = Mock()
		own = {dialog_module.wx.ID_OK: Mock(), dialog_module.wx.ID_CANCEL: Mock()}
		other = {dialog_module.wx.ID_OK: Mock(), dialog_module.wx.ID_CANCEL: Mock()}
		dialog.FindWindow.side_effect = own.get
		dialog.FindWindowById.side_effect = other.get

		previous_gettext = dialog_module._
		dialog_module._ = {"OK": "確定", "Cancel": "取消"}.get
		try:
			dialog_module.localize_standard_buttons(dialog, dialog_module.wx.OK | dialog_module.wx.CANCEL)
		finally:
			dialog_module._ = previous_gettext

		own[dialog_module.wx.ID_OK].SetLabel.assert_called_once_with("確定")
		own[dialog_module.wx.ID_CANCEL].SetLabel.assert_called_once_with("取消")
		for button in other.values():
			button.SetLabel.assert_not_called()
		dialog.FindWindowById.assert_not_called()

	def test_file_issues_dialog_localizes_its_ok_button(self):
		dialog = object.__new__(dialog_module.FileIssuesDialog)
		button_sizer = Mock()
		dialog.CreateButtonSizer = Mock(return_value=button_sizer)
		dialog.SetMinSize = Mock()
		widgets = MagicMock(OK=dialog_module.wx.OK)

		with (
			patch.object(dialog_module.wx.Dialog, "__init__", lambda *_args, **_kwargs: None),
			patch.object(dialog_module, "wx", widgets),
			patch.object(dialog_module, "finalize_dialog_layout"),
			patch.object(dialog_module, "localize_standard_buttons") as localize,
		):
			dialog_module.FileIssuesDialog.__init__(dialog, None, "Import Issues", "Some files were skipped.", ["a.txt"])

		dialog.CreateButtonSizer.assert_called_once_with(dialog_module.wx.OK)
		localize.assert_called_once_with(dialog, dialog_module.wx.OK, button_sizer)


if __name__ == "__main__":
	unittest.main()
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.list: _FakeListCtrl | None = None
        self.ok_button = _FakeButton(self, "ok", "OK")
        self.cancel_button = _FakeButton(self, "cancel", "Cancel")
        self.script: list[tuple[int, DictionaryEntry | None]] = []
        self.entry_dialog_parents: list[object] = []
        self.message_box_parents: list[object] = []
```

```python
        self.list: _FakeListCtrl | None = None
        self.ok_button = _FakeButton(self, "ok", "OK")
        self.cancel_button = _FakeButton(self, "cancel", "Cancel")
        # The standard buttons of an older top-level window, such as an open Settings dialog (F-W9).
        self.other_dialog_buttons: dict[int, _FakeButton] = {}
        self.script: list[tuple[int, DictionaryEntry | None]] = []
        self.entry_dialog_parents: list[object] = []
        self.message_box_parents: list[object] = []
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            stack.enter_context(patch("os.fsync", _skip_fsync))
            editor = object.__new__(DictionaryEntriesDialog)
            editor.CreateButtonSizer = self._create_button_sizer
            editor.FindWindowById = self._find_window_by_id
            editor.SetSizerAndFit = lambda _sizer: self.record("SetSizerAndFit")
            editor.GetParent = lambda: self.parent
```

```python
            stack.enter_context(patch("os.fsync", _skip_fsync))
            editor = object.__new__(DictionaryEntriesDialog)
            editor.CreateButtonSizer = self._create_button_sizer
            editor.FindWindow = self._find_own_window
            editor.FindWindowById = self._find_window_by_id
            editor.SetSizerAndFit = lambda _sizer: self.record("SetSizerAndFit")
            editor.GetParent = lambda: self.parent
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.record("CreateButtonSizer", flags)
        return _FakeSizer()

    def _find_window_by_id(self, window_id: int) -> _FakeButton | None:
        return {ID_OK: self.ok_button, ID_CANCEL: self.cancel_button}.get(window_id)

    def _message_box(self, message: str, caption: str, style: int, parent=None) -> int:
        self.record("MessageBox", message, caption, style)
```

```python
        self.record("CreateButtonSizer", flags)
        return _FakeSizer()

    def _find_own_window(self, window_id: int) -> _FakeButton | None:
        """``wxWindow::FindWindow``: the editor and its children only."""
        return {ID_OK: self.ok_button, ID_CANCEL: self.cancel_button}.get(window_id)

    def _find_window_by_id(self, window_id: int) -> _FakeButton | None:
        """``wx.Window.FindWindowById`` without a parent: every top-level window, oldest first."""
        return self.other_dialog_buttons.get(window_id) or self._find_own_window(window_id)

    def _message_box(self, message: str, caption: str, style: int, parent=None) -> int:
        self.record("MessageBox", message, caption, style)
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
        self.assertEqual(harness.cancel_button.bindings, [])
        self.assertEqual(harness.ok_button.label, "\u78ba\u5b9a")
        self.assertEqual(harness.cancel_button.label, "\u53d6\u6d88")


class DictionaryEntriesDialogCellTextTest(_EditorTestCase):
```

```python
        self.assertEqual(harness.cancel_button.bindings, [])
        self.assertEqual(harness.ok_button.label, "\u78ba\u5b9a")
        self.assertEqual(harness.cancel_button.label, "\u53d6\u6d88")

    def test_entries_dialog_binds_ok_to_its_own_button(self) -> None:
        # F-7 (F-W9): while the Settings or Text Processing dialog is open, a global lookup of
        # ID_OK finds that dialog's OK. The editor's own OK then closed without saving.
        path = self.make_path()
        _write_rows(path, [ALPHA])
        harness = _EditorHarness(path)
        other_ok = _FakeButton(harness, "other ok", "OK")
        other_cancel = _FakeButton(harness, "other cancel", "Cancel")
        harness.other_dialog_buttons = {ID_OK: other_ok, ID_CANCEL: other_cancel}
        harness.open()
        self.addCleanup(harness.close)
        harness.script_entry(*BETA)
        harness.click("Add")

        self.assertTrue(harness.press_ok())
        self.assertEqual(load_dictionary_entries(path), [DictionaryEntry(*ALPHA), DictionaryEntry(*BETA)])
        self.assertEqual((harness.ok_button.label, harness.cancel_button.label), (_("OK"), _("Cancel")))
        self.assertEqual([event for event, _handler in other_ok.bindings], [])
        self.assertEqual((other_ok.label, other_cancel.label), ("OK", "Cancel"))


class DictionaryEntriesDialogCellTextTest(_EditorTestCase):
```

File: `client/tests/test_wx_call_sites.py`

````python
"""Source scans that keep the wx calls F-7 replaced out of the production code (F-W9).

The scan covers every ``.py`` file under ``client/`` except the tests, the virtual
environment, the build output and the vendored or generated trees. A hit is reported as
``<file>:<class>.<function>`` so that a failure names the call site.
"""

import ast
import unittest
from collections.abc import Callable, Iterator
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[1]
EXCLUDED_FOLDERS = {".venv", "tests", "build", "dist", "mathcat"}


def production_sources() -> list[Path]:
    paths = []
    for path in sorted(CLIENT.rglob("*.py")):
        parts = path.relative_to(CLIENT).parts
        if parts[0] in EXCLUDED_FOLDERS or parts[:2] == ("braille", "liblouis"):
            continue
        paths.append(path)
    return paths


def _matches(node: ast.AST, predicate: Callable[[ast.AST], bool], scope: str) -> Iterator[str]:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield from _matches(child, predicate, f"{scope}.{child.name}" if scope else child.name)
            continue
        if predicate(child):
            yield scope or "<module>"
        yield from _matches(child, predicate, scope)


def find_in_production(predicate: Callable[[ast.AST], bool]) -> list[str]:
    """``<file>:<scope>`` of every node of the production code for which ``predicate`` is true."""
    found = []
    for path in production_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        name = path.relative_to(CLIENT).as_posix()
        found.extend(f"{name}:{scope}" for scope in _matches(tree, predicate, ""))
    return found


def is_attribute(name: str) -> Callable[[ast.AST], bool]:
    return lambda node: isinstance(node, ast.Attribute) and node.attr == name


class WxCallSitesTest(unittest.TestCase):
    def test_scan_reads_the_production_modules(self) -> None:
        names = {path.relative_to(CLIENT).as_posix() for path in production_sources()}

        self.assertTrue({"dialog.py", "gui.py", "settings/dialogs.py"} <= names, sorted(names))
        self.assertFalse([name for name in names if name.startswith("tests/")])

    def test_no_production_code_searches_windows_by_id_globally(self) -> None:
        # wx.Window.FindWindowById is static: called on a dialog, it still searches every
        # top-level window and can return another dialog's button (F-W9). FindWindow
        # searches the window and its children only.
        self.assertEqual(find_in_production(is_attribute("FindWindowById")), [])


if __name__ == "__main__":
    unittest.main()
````

```bash
$PY -m unittest tests.test_dialog_display tests.test_dictionary_entries_dialog tests.test_wx_call_sites 2>&1 | $PY $T/tools/brief.py
```

Expected (the three changed tests get no label, because the Mock's `FindWindowById` returns another Mock; the other dialog's OK gets the editor's handler; the scan finds both lookups):

```text
FAIL: test_file_issues_dialog_localizes_its_ok_button (tests.test_dialog_display.FinalizeDialogLayoutTest.test_file_issues_dialog_localizes_its_ok_button)
AssertionError: Expected 'localize_standard_buttons' to be called once. Called 0 times.
FAIL: test_localize_ignores_buttons_of_other_windows (tests.test_dialog_display.FinalizeDialogLayoutTest.test_localize_ignores_buttons_of_other_windows)
AssertionError: Expected 'SetLabel' to be called once. Called 0 times.
FAIL: test_localizes_buttons_from_standard_button_sizer (tests.test_dialog_display.FinalizeDialogLayoutTest.test_localizes_buttons_from_standard_button_sizer)
FAIL: test_localizes_close_button (tests.test_dialog_display.FinalizeDialogLayoutTest.test_localizes_close_button)
FAIL: test_localizes_standard_dialog_buttons (tests.test_dialog_display.FinalizeDialogLayoutTest.test_localizes_standard_dialog_buttons)
FAIL: test_entries_dialog_binds_ok_to_its_own_button (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.test_entries_dialog_binds_ok_
AssertionError: False is not true
FAIL: test_no_production_code_searches_windows_by_id_globally (tests.test_wx_call_sites.WxCallSitesTest.test_no_production_code_searches_windows_by_id_globally)
AssertionError: Lists differ: ['dialog.py:localize_standard_buttons', 'd[39 chars]_ui'] != []
Ran 82 tests
FAILED (failures=7)
```

- [ ] **Step 2: Search the dialog's own children** (`client/dialog.py`, tabs).

Edit: `client/dialog.py`

```python
	flags: int,
	button_sizer: wx.StdDialogButtonSizer | None = None,
) -> None:
	"""Apply application translations to wxPython's standard dialog buttons."""
	button_labels = (
		(wx.OK, wx.ID_OK, _("OK"), "GetAffirmativeButton"),
		(wx.CANCEL, wx.ID_CANCEL, _("Cancel"), "GetCancelButton"),
```

```python
	flags: int,
	button_sizer: wx.StdDialogButtonSizer | None = None,
) -> None:
	"""Apply application translations to wxPython's standard dialog buttons.

	Only the dialog's own children are searched (F-W9): a search of every top-level
	window could find another dialog's button with the same id and relabel that one.
	"""
	button_labels = (
		(wx.OK, wx.ID_OK, _("OK"), "GetAffirmativeButton"),
		(wx.CANCEL, wx.ID_CANCEL, _("Cancel"), "GetCancelButton"),
```

Edit: `client/dialog.py`

```python
	)
	for flag, button_id, label, sizer_button_getter in button_labels:
		if flags & flag:
			button = dialog.FindWindowById(button_id)
			if button is None and button_sizer is not None:
				getter = getattr(button_sizer, sizer_button_getter, None)
				if getter is not None:
```

```python
	)
	for flag, button_id, label, sizer_button_getter in button_labels:
		if flags & flag:
			button = dialog.FindWindow(button_id)
			if button is None and button_sizer is not None:
				getter = getattr(button_sizer, sizer_button_getter, None)
				if getter is not None:
```

Edit: `client/dialog.py`

```python
		main_sizer.Add(self.list_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		button_sizer = self.CreateButtonSizer(wx.OK)
		if button_sizer:
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		finalize_dialog_layout(self, main_sizer)
		self.SetMinSize((520, 320))
```

```python
		main_sizer.Add(self.list_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		button_sizer = self.CreateButtonSizer(wx.OK)
		if button_sizer:
			localize_standard_buttons(self, wx.OK, button_sizer)
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		finalize_dialog_layout(self, main_sizer)
		self.SetMinSize((520, 320))
```

Edit: `client/dialog.py`

```python
		if button_bar:
			localize_standard_buttons(self, wx.OK | wx.CANCEL, button_bar)
			main_sizer.Add(button_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
			ok_button = self.FindWindowById(wx.ID_OK)
			if ok_button:
				ok_button.Bind(wx.EVT_BUTTON, self._on_ok)

```

```python
		if button_bar:
			localize_standard_buttons(self, wx.OK | wx.CANCEL, button_bar)
			main_sizer.Add(button_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
			ok_button = self.FindWindow(wx.ID_OK)
			if ok_button:
				ok_button.Bind(wx.EVT_BUTTON, self._on_ok)

```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_dialog_display tests.test_dictionary_entries_dialog tests.test_wx_call_sites -v 2>&1 | grep -E "^test_(localize_ignores_buttons_of_other_windows|file_issues_dialog_localizes_its_ok_button|entries_dialog_binds_ok_to_its_own_button|no_production_code_searches_windows_by_id_globally|scan_reads_the_production_modules) " | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_dialog_display tests.test_dictionary_entries_dialog tests.test_wx_call_sites 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_file_issues_dialog_localizes_its_ok_button ok
test_localize_ignores_buttons_of_other_windows ok
test_entries_dialog_binds_ok_to_its_own_button ok
test_no_production_code_searches_windows_by_id_globally ok
test_scan_reads_the_production_modules ok
Ran 82 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1342 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/dialog.py client/tests/test_dialog_display.py client/tests/test_dictionary_entries_dialog.py client/tests/test_wx_call_sites.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: look up standard dialog buttons among the dialog's own children (F-7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dialog.py                               | 11 +++--
 client/tests/test_dialog_display.py            | 48 +++++++++++++++++--
 client/tests/test_dictionary_entries_dialog.py | 30 +++++++++++-
 client/tests/test_wx_call_sites.py             | 66 ++++++++++++++++++++++++++
 4 files changed, 147 insertions(+), 8 deletions(-)
f6a7409dd7196d6b1310ce4493e5a844356c2339
```

### Task 2: Show message boxes with the translated OK button (D2-D4)

- [ ] **Step 1: Red: A1-A6, C1, C2 and the two sites that had no test** (site 1, the entry dialog's own message; site 20, the About box). `test_message_box.py` (new, 4 spaces) loads `ui.message_box` under its own stub scope with wx's real values for the styles, results and ids; the labels are the real zh-TW catalog.

File: `client/tests/test_message_box.py`

````python
"""Tests of ``ui.message_box`` (F-7, F-W9) against a minimal fake ``wx``.

The fake has wx's own values for the styles, the results and the ids; its
``MessageDialog`` is replaced in each test by a recorder that answers from a queue.
The labels are the real zh_TW catalog, through ``i18n``.
"""

import importlib
import types
import unittest
from unittest.mock import patch

from i18n import _
from tests import wx_stub


def _fake_wx() -> types.ModuleType:
    wx = types.ModuleType("wx")
    wx.Window = type("Window", (), {})
    wx.MessageDialog = type("MessageDialog", (), {})
    wx.YES = 0x2
    wx.OK = 0x4
    wx.NO = 0x8
    wx.YES_NO = wx.YES | wx.NO
    wx.CANCEL = 0x10
    wx.NO_DEFAULT = 0x80
    wx.ICON_WARNING = 0x100
    wx.ICON_ERROR = 0x200
    wx.ICON_INFORMATION = 0x800
    wx.ID_OK = 5100
    wx.ID_CANCEL = 5101
    wx.ID_YES = 5103
    wx.ID_NO = 5104
    return wx


_SCOPE = wx_stub.StubScope({"wx": _fake_wx()}, isolate=("ui.message_box",))
with _SCOPE.loading():
    message_box_module = importlib.import_module("ui.message_box")

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate

message_box = message_box_module.message_box
wx = message_box_module.wx


class MessageBoxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list = []
        self.answers: list = []
        self.label_result = True
        patcher = patch.object(wx, "MessageDialog", self._dialog_class())
        patcher.start()
        self.addCleanup(patcher.stop)

    def _dialog_class(self):
        test = self

        class RecordingMessageDialog:
            def __init__(self, *args):
                test.calls.append(("MessageDialog", *args))

            def __enter__(self):
                test.calls.append(("enter",))
                return self

            def __exit__(self, *_exc):
                test.calls.append(("exit",))
                return False

            def SetOKLabel(self, ok):
                test.calls.append(("SetOKLabel", ok))
                return test.label_result

            def SetOKCancelLabels(self, ok, cancel):
                test.calls.append(("SetOKCancelLabels", ok, cancel))
                return test.label_result

            def SetYesNoLabels(self, yes, no):
                test.calls.append(("SetYesNoLabels", yes, no))
                return test.label_result

            def ShowModal(self):
                test.calls.append(("ShowModal",))
                return test.answers.pop(0)

        return RecordingMessageDialog

    def test_ok_box_sets_the_translated_ok_label(self) -> None:
        parent = object()
        self.answers = [wx.ID_OK]

        result = message_box("message", "caption", wx.OK | wx.ICON_ERROR, parent=parent)

        self.assertEqual(
            self.calls,
            [
                ("MessageDialog", parent, "message", "caption", wx.OK | wx.ICON_ERROR),
                ("enter",),
                ("SetOKLabel", "確定"),
                ("ShowModal",),
                ("exit",),
            ],
        )
        self.assertEqual(_("OK"), "確定")
        self.assertEqual(result, wx.OK)

    def test_ok_cancel_box_sets_both_labels(self) -> None:
        self.answers = [wx.ID_CANCEL]

        result = message_box("message", "caption", wx.OK | wx.CANCEL | wx.ICON_WARNING)

        self.assertEqual(self.calls[2], ("SetOKCancelLabels", "確定", "取消"))
        self.assertEqual([call[0] for call in self.calls], ["MessageDialog", "enter", "SetOKCancelLabels", "ShowModal", "exit"])
        self.assertEqual(result, wx.CANCEL)

    def test_yes_no_box_keeps_the_system_labels(self) -> None:
        for style in (wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, wx.YES_NO | wx.ICON_WARNING):
            for answer, expected in ((wx.ID_YES, wx.YES), (wx.ID_NO, wx.NO)):
                with self.subTest(style=style, answer=answer):
                    self.calls.clear()
                    self.answers = [answer]

                    result = message_box("question", "caption", style, parent=None)

                    self.assertEqual(
                        self.calls,
                        [("MessageDialog", None, "question", "caption", style), ("enter",), ("ShowModal",), ("exit",)],
                    )
                    self.assertEqual(result, expected)

    def test_unexpected_result_maps_to_cancel(self) -> None:
        for answer in (wx.ID_CANCEL, 12345):
            with self.subTest(answer=answer):
                self.answers = [answer]

                self.assertEqual(message_box("message", "caption", wx.OK | wx.ICON_INFORMATION), wx.CANCEL)

    def test_parent_can_be_omitted_or_positional(self) -> None:
        frame = object()
        self.answers = [wx.ID_OK, wx.ID_OK]

        message_box("first", "caption", wx.OK | wx.ICON_ERROR)
        message_box("second", "caption", wx.OK | wx.ICON_ERROR, frame)

        self.assertEqual(
            [call for call in self.calls if call[0] == "MessageDialog"],
            [
                ("MessageDialog", None, "first", "caption", wx.OK | wx.ICON_ERROR),
                ("MessageDialog", frame, "second", "caption", wx.OK | wx.ICON_ERROR),
            ],
        )

    def test_a_label_the_platform_refuses_still_shows_the_box(self) -> None:
        self.label_result = False
        self.answers = [wx.ID_OK]

        result = message_box("message", "caption", wx.OK | wx.ICON_INFORMATION)

        self.assertEqual([call[0] for call in self.calls], ["MessageDialog", "enter", "SetOKLabel", "ShowModal", "exit"])
        self.assertEqual(result, wx.OK)


if __name__ == "__main__":
    unittest.main()
````

Edit: `client/tests/test_wx_call_sites.py`

```python
    return lambda node: isinstance(node, ast.Attribute) and node.attr == name


class WxCallSitesTest(unittest.TestCase):
    def test_scan_reads_the_production_modules(self) -> None:
        names = {path.relative_to(CLIENT).as_posix() for path in production_sources()}
```

```python
    return lambda node: isinstance(node, ast.Attribute) and node.attr == name


def is_wx_call(name: str) -> Callable[[ast.AST], bool]:
    """A call of ``wx.<name>(...)``."""
    return lambda node: (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == name
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "wx"
    )


class WxCallSitesTest(unittest.TestCase):
    def test_scan_reads_the_production_modules(self) -> None:
        names = {path.relative_to(CLIENT).as_posix() for path in production_sources()}
```

Edit: `client/tests/test_wx_call_sites.py`

```python
        # searches the window and its children only.
        self.assertEqual(find_in_production(is_attribute("FindWindowById")), [])


if __name__ == "__main__":
    unittest.main()
```

```python
        # searches the window and its children only.
        self.assertEqual(find_in_production(is_attribute("FindWindowById")), [])

    def test_no_production_module_calls_wx_message_box(self) -> None:
        # wx.MessageBox labels its OK button from wx's own catalog, which DotExpress does not
        # load; ui.message_box.message_box sets the translated label (F-7, F-W9).
        self.assertEqual(find_in_production(is_wx_call("MessageBox")), [])

    def test_message_dialogs_are_the_helper_or_set_every_label(self) -> None:
        # F-5's close dialog sets all three of its labels itself.
        self.assertEqual(
            find_in_production(is_wx_call("MessageDialog")),
            ["gui.py:BrailleFrame._ask_after_close_save_failure", "ui/message_box.py:message_box"],
        )


if __name__ == "__main__":
    unittest.main()
```

Edit: `client/tests/test_dialog_validation.py`

```python
setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate

from dictionaries.manager import DEFAULT_DICTIONARY_NAME, MAX_DICTIONARY_NAME_LENGTH, normalize_dictionary_name
from documents.workspace import normalize_document_name
from i18n import _
```

```python
setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate

from dictionaries.entries import DictionaryEntry
from dictionaries.manager import DEFAULT_DICTIONARY_NAME, MAX_DICTIONARY_NAME_LENGTH, normalize_dictionary_name
from documents.workspace import normalize_document_name
from i18n import _
```

Edit: `client/tests/test_dialog_validation.py`

```python
        self.assert_accepts(DocumentNameDialog, ((" name", "name"), ("name\u3000", "name"), ("Default", "Default")))


class DialogContextManagerTest(unittest.TestCase):
    def make_dialog(self, dialog_class):
        dialog = object.__new__(dialog_class)
```

```python
        self.assert_accepts(DocumentNameDialog, ((" name", "name"), ("name\u3000", "name"), ("Default", "Default")))


class AddSymbolDialogOkTest(unittest.TestCase):
    def test_invalid_entry_shows_the_message_on_the_dialog_and_focuses_the_source_text(self) -> None:
        # Message box call site 1 of F-7: the entry dialog's own validation message.
        dialog = object.__new__(AddSymbolDialog)
        dialog.identifier_ctrl = _TextCtrl()
        dialog.braille_ctrl = _TextCtrl()
        dialog.get_entry = lambda: DictionaryEntry("", "x", "General")
        event = Mock()

        with (
            patch.object(dialog_module, "message_box") as message_box,
            patch.object(dialog_module.wx, "OK", 4, create=True),
            patch.object(dialog_module.wx, "ICON_INFORMATION", 128, create=True),
        ):
            AddSymbolDialog._on_ok(dialog, event)

        message_box.assert_called_once_with(_("Please enter the source text."), INFO_TITLE, 132, parent=dialog)
        self.assertTrue(dialog.identifier_ctrl.focused)
        self.assertFalse(dialog.braille_ctrl.focused)
        event.Skip.assert_not_called()


class DialogContextManagerTest(unittest.TestCase):
    def make_dialog(self, dialog_class):
        dialog = object.__new__(dialog_class)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            ],
        )

    def test_show_file_error_formats_the_error_for_the_frame(self) -> None:
        frame = self._make_frame()
        with patch.object(gui.wx, "MessageBox") as message_box:
```

```python
            ],
        )

    def test_about_box_uses_the_helper(self) -> None:
        frame = self._make_frame()
        with patch.object(gui, "message_box") as message_box:
            frame.on_about(None)

        message_box.assert_called_once_with(
            gui.about.aboutMessage, gui._("About DotExpress"), gui.wx.OK | gui.wx.ICON_INFORMATION, parent=frame
        )

    def test_show_file_error_formats_the_error_for_the_frame(self) -> None:
        frame = self._make_frame()
        with patch.object(gui.wx, "MessageBox") as message_box:
```

```bash
$PY -m unittest tests.test_message_box tests.test_wx_call_sites tests.test_dialog_validation tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (the helper does not exist; 20 `wx.MessageBox` calls and the About box's `wx.MessageDialog` are found):

```text
ERROR: test_message_box (unittest.loader._FailedTest.test_message_box)
ImportError: Failed to import test module: test_message_box
ModuleNotFoundError: No module named 'ui.message_box'
ERROR: test_invalid_entry_shows_the_message_on_the_dialog_and_focuses_the_source_text (tests.test_dialog_validation.AddSymbolDialogOkTest.test_invalid_entry_sho
AttributeError: <module 'dialog' from '<client>\\dialog.py'> does not have the attribute 'message_box'
ERROR: test_about_box_uses_the_helper (tests.test_gui_document_flows.FrameViewMethodsTest.test_about_box_uses_the_helper)
AttributeError: <module 'gui' from '<client>\\gui.py'> does not have the attribute 'message_box'
FAIL: test_message_dialogs_are_the_helper_or_set_every_label (tests.test_wx_call_sites.WxCallSitesTest.test_message_dialogs_are_the_helper_or_set_every_label)
AssertionError: Lists differ: ['gui[18 chars]ask_after_close_save_failure', 'gui.py:BrailleFrame.on_about'] != ['gui[18 chars]ask_after_close_save_failure', 'ui
FAIL: test_no_production_module_calls_wx_message_box (tests.test_wx_call_sites.WxCallSitesTest.test_no_production_module_calls_wx_message_box)
AssertionError: Lists differ: ['dialog.py:AddSymbolDialog._on_ok', 'dial[858 chars]ect'] != []
Ran 210 tests
FAILED (failures=2, errors=3)
```

- [ ] **Step 2: The helper, the 21 call sites, the stubs and the re-pointed tests.** `client/ui/message_box.py` (new, 4 spaces) is D2 verbatim. Each `wx.MessageBox(` becomes `message_box(` with the same arguments (7 in `dialog.py`, 11 in `gui.py`, 2 in `settings/dialogs.py`), and `on_about` calls it (D3). The re-pointed tests change their patch target only (Spec Corrections 4), and `ui.message_box` joins the isolate names (Spec Corrections 6).

File: `client/ui/message_box.py`

````python
"""``wx.MessageBox`` with the application's own button labels (F-7, F-W9).

wx draws the OK button of a message box with a label from its own catalog, which
DotExpress does not load, so ``wx.MessageBox`` shows an English "OK". Yes and No
are Windows' common buttons, which Windows labels in the system language.
"""

from __future__ import annotations

import wx

from i18n import _


def message_box(message: str, caption: str, style: int, parent: wx.Window | None = None) -> int:
    """Show a message box like ``wx.MessageBox``: same arguments and return values.

    Returns ``wx.OK``, ``wx.YES``, ``wx.NO`` or ``wx.CANCEL``. An OK button (and a
    Cancel button next to it) gets the translated label; a Yes/No box keeps the
    system's labels.
    """
    with wx.MessageDialog(parent, message, caption, style) as dialog:
        if not style & wx.YES_NO:
            if style & wx.CANCEL:
                dialog.SetOKCancelLabels(_("OK"), _("Cancel"))
            else:
                dialog.SetOKLabel(_("OK"))
        answer = dialog.ShowModal()
    return {wx.ID_OK: wx.OK, wx.ID_YES: wx.YES, wx.ID_NO: wx.NO}.get(answer, wx.CANCEL)
````

Edit: `client/dialog.py`

```python
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages

CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")

```

```python
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
from ui.message_box import message_box

CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")

```

Edit: `client/dialog.py`

```python
		try:
			validate_dictionary_entry(entry)
		except ValueError as exc:
			wx.MessageBox(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
			try:
				if not entry.text:
					self.identifier_ctrl.SetFocus()
```

```python
		try:
			validate_dictionary_entry(entry)
		except ValueError as exc:
			message_box(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
			try:
				if not entry.text:
					self.identifier_ctrl.SetFocus()
```

Edit: `client/dialog.py`

```python
	"""Name dialog base: shows a name error in an information message box."""

	def _show_name_error(self, message: str) -> None:
		wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)


class DictionaryNameDialog(_NameDialog):
```

```python
	"""Name dialog base: shows a name error in an information message box."""

	def _show_name_error(self, message: str) -> None:
		message_box(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)


class DictionaryNameDialog(_NameDialog):
```

Edit: `client/dialog.py`

```python
			return dialog.get_entry()

	def _show_duplicate_error(self, identifier: str) -> None:
		wx.MessageBox(
			_('Source text "{identifier}" already exists.').format(identifier=identifier),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
```

```python
			return dialog.get_entry()

	def _show_duplicate_error(self, identifier: str) -> None:
		message_box(
			_('Source text "{identifier}" already exists.').format(identifier=identifier),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
```

Edit: `client/dialog.py`

```python
		try:
			self._model.save(self.dictionary_path)
		except Exception as exc:
			wx.MessageBox(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
			return
		event.Skip()

```

```python
		try:
			self._model.save(self.dictionary_path)
		except Exception as exc:
			message_box(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
			return
		event.Skip()

```

Edit: `client/dialog.py`

```python
			return name_dialog.get_dictionary_name()

	def show_info(self, message: str) -> None:
		wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)

	def show_error(self, message: str) -> None:
		wx.MessageBox(message, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)

	def confirm(self, message: str, caption: str) -> bool:
		return wx.MessageBox(message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self) == wx.YES

	def choose_import_path(self, title: str) -> Path | None:
		with wx.FileDialog(
```

```python
			return name_dialog.get_dictionary_name()

	def show_info(self, message: str) -> None:
		message_box(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)

	def show_error(self, message: str) -> None:
		message_box(message, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)

	def confirm(self, message: str, caption: str) -> bool:
		return message_box(message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self) == wx.YES

	def choose_import_path(self, title: str) -> Path | None:
		with wx.FileDialog(
```

Edit: `client/gui.py`

```python
from ui.conversion_presenter import ConversionPresenter
from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
from ui.menu_builder import apply_document_menu_state, build_document_menu
from config import ConfigStore, DEFAULT_TRANSLATION_TABLES
from settings.translation import (
	TranslationSettings,
```

```python
from ui.conversion_presenter import ConversionPresenter
from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
from ui.menu_builder import apply_document_menu_state, build_document_menu
from ui.message_box import message_box
from config import ConfigStore, DEFAULT_TRANSLATION_TABLES
from settings.translation import (
	TranslationSettings,
```

Edit: `client/gui.py`

```python
		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)

	def _show_file_error(self, message: str, error: Exception) -> None:
		wx.MessageBox(
			message.format(error=error),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
```

```python
		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)

	def _show_file_error(self, message: str, error: Exception) -> None:
		message_box(
			message.format(error=error),
			_("Error"),
			wx.OK | wx.ICON_ERROR,
```

Edit: `client/gui.py`

```python
			self._show_file_error(_("Failed to open website: {error}"), exc)

	def on_about(self, _evt: wx.CommandEvent) -> None:
		with wx.MessageDialog(
			self,
			about.aboutMessage,
			_("About DotExpress"),
			wx.OK | wx.ICON_INFORMATION,
		) as dialog:
			dialog.ShowModal()

	def on_open_dual_view(self, _evt) -> None:
		self._open_dual_view_in_browser()
```

```python
			self._show_file_error(_("Failed to open website: {error}"), exc)

	def on_about(self, _evt: wx.CommandEvent) -> None:
		message_box(about.aboutMessage, _("About DotExpress"), wx.OK | wx.ICON_INFORMATION, parent=self)

	def on_open_dual_view(self, _evt) -> None:
		self._open_dual_view_in_browser()
```

Edit: `client/gui.py`

```python
				script_path=preprocessing_script_path(self.dictionary_dir),
			)
		except OSError as error:
			wx.MessageBox(
				_("Unable to open text processing script: {error}").format(error=error),
				_("Text Processing"),
				wx.OK | wx.ICON_ERROR,
```

```python
				script_path=preprocessing_script_path(self.dictionary_dir),
			)
		except OSError as error:
			message_box(
				_("Unable to open text processing script: {error}").format(error=error),
				_("Text Processing"),
				wx.OK | wx.ICON_ERROR,
```

Edit: `client/gui.py`

```python
					return None
				document_name = normalize_document_name(dialog.get_document_name())
			if self._document_controller.document_name_exists(document_name, exclude_name=exclude_name):
				wx.MessageBox(
					_('Document "{name}" already exists.').format(name=document_name),
					_("Error"),
					wx.OK | wx.ICON_ERROR,
```

```python
					return None
				document_name = normalize_document_name(dialog.get_document_name())
			if self._document_controller.document_name_exists(document_name, exclude_name=exclude_name):
				message_box(
					_('Document "{name}" already exists.').format(name=document_name),
					_("Error"),
					wx.OK | wx.ICON_ERROR,
```

Edit: `client/gui.py`

```python
			return
		if not self._save_open_document_with_feedback():
			return
		confirmation = wx.MessageBox(
			_('Do you want to delete document "{name}"?').format(name=selected_document.name),
			_("Confirm Delete Document"),
			wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
```

```python
			return
		if not self._save_open_document_with_feedback():
			return
		confirmation = message_box(
			_('Do you want to delete document "{name}"?').format(name=selected_document.name),
			_("Confirm Delete Document"),
			wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
```

Edit: `client/gui.py`

```python
			return
		if not self._save_open_document_with_feedback():
			return
		confirmation = wx.MessageBox(
			_("Delete All will remove all documents. Do you want to continue?"),
			_("Confirm Delete All"),
			wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
```

```python
			return
		if not self._save_open_document_with_feedback():
			return
		confirmation = message_box(
			_("Delete All will remove all documents. Do you want to continue?"),
			_("Confirm Delete All"),
			wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
```

Edit: `client/gui.py`

```python
		except Exception as error:
			# F-6 (D6): the file could not be read after Dictionary Management checked it.
			log_dictionary_read_error(dictionary_path, error)
			wx.MessageBox(
				describe_unreadable_dictionary(edit_name, error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
```

```python
		except Exception as error:
			# F-6 (D6): the file could not be read after Dictionary Management checked it.
			log_dictionary_read_error(dictionary_path, error)
			message_box(
				describe_unreadable_dictionary(edit_name, error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
```

Edit: `client/gui.py`

```python
		self._refresh_dual_view()

	def show_info(self, message: str, caption: str) -> None:
		wx.MessageBox(message, caption, wx.OK | wx.ICON_INFORMATION, parent=self)

	def show_error(self, message: str, caption: str) -> None:
		wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR, parent=self)

	# --- ExportView (documents/export_coordinator.py) -----------------------

	def show_warning(self, message: str, caption: str) -> None:
		wx.MessageBox(message, caption, wx.OK | wx.ICON_WARNING, parent=self)

	def choose_export_path(self, default_file: str, descriptor: DocumentFormatDescriptor) -> Path | None:
		wildcard = build_export_wildcard(descriptor, _)
```

```python
		self._refresh_dual_view()

	def show_info(self, message: str, caption: str) -> None:
		message_box(message, caption, wx.OK | wx.ICON_INFORMATION, parent=self)

	def show_error(self, message: str, caption: str) -> None:
		message_box(message, caption, wx.OK | wx.ICON_ERROR, parent=self)

	# --- ExportView (documents/export_coordinator.py) -----------------------

	def show_warning(self, message: str, caption: str) -> None:
		message_box(message, caption, wx.OK | wx.ICON_WARNING, parent=self)

	def choose_export_path(self, default_file: str, descriptor: DocumentFormatDescriptor) -> Path | None:
		wildcard = build_export_wildcard(descriptor, _)
```

Edit: `client/gui.py`

```python
			"The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
		)
		return (
			wx.MessageBox(message, _("Confirm Overwrite"), wx.YES_NO | wx.ICON_WARNING, parent=self) == wx.YES
		)

def _show_application_data_error(error: ApplicationDataError) -> None:
	wx.MessageBox(
		_(
			"DotExpress cannot write to its application data directory:\n"
			"{path}\n\nChoose a writable installation or execution location.\n\n{error}"
```

```python
			"The destination folder already contains one or more files that would be overwritten. Do you want to overwrite all of them?"
		)
		return (
			message_box(message, _("Confirm Overwrite"), wx.YES_NO | wx.ICON_WARNING, parent=self) == wx.YES
		)

def _show_application_data_error(error: ApplicationDataError) -> None:
	message_box(
		_(
			"DotExpress cannot write to its application data directory:\n"
			"{path}\n\nChoose a writable installation or execution location.\n\n{error}"
```

Edit: `client/settings/dialogs.py`

```python
)
from i18n import _
from ui.dialog_base import SingletonDialogMixin
from .options import (
    BRAILLE_FONT_OPTIONS,
    CONVERSION_WIDTH_RANGE,
```

```python
)
from i18n import _
from ui.dialog_base import SingletonDialogMixin
from ui.message_box import message_box
from .options import (
    BRAILLE_FONT_OPTIONS,
    CONVERSION_WIDTH_RANGE,
```

Edit: `client/settings/dialogs.py`

```python
            save_preprocessing_script(self.script_path, self.editor.GetValue())
        except (OSError, SyntaxError, ValueError) as error:
            display_error = _(str(error)) if isinstance(error, ValueError) else error
            wx.MessageBox(
                _("Unable to save text processing script: {error}").format(
                    error=display_error
                ),
```

```python
            save_preprocessing_script(self.script_path, self.editor.GetValue())
        except (OSError, SyntaxError, ValueError) as error:
            display_error = _(str(error)) if isinstance(error, ValueError) else error
            message_box(
                _("Unable to save text processing script: {error}").format(
                    error=display_error
                ),
```

Edit: `client/settings/dialogs.py`

```python
                focus_target: wx.Window | None = panel
                if message_and_focus is not None:
                    message, focus_target = message_and_focus
                    wx.MessageBox(
                        message,
                        self.base_title,
                        wx.OK | wx.ICON_ERROR,
```

```python
                focus_target: wx.Window | None = panel
                if message_and_focus is not None:
                    message, focus_target = message_and_focus
                    message_box(
                        message,
                        self.base_title,
                        wx.OK | wx.ICON_ERROR,
```

Edit: `client/tests/wx_stub.py`

```python
            return ""

    class _MessageDialog(Dialog):
        def SetExtendedMessage(self, _message):
            return None

        def SetYesNoCancelLabels(self, _yes, _no, _cancel):
            return True

    wx.Window = Window
    wx.Frame = Frame
```

```python
            return ""

    class _MessageDialog(Dialog):
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def SetExtendedMessage(self, _message):
            return None

        def SetOKLabel(self, _ok):
            return True

        def SetOKCancelLabels(self, _ok, _cancel):
            return True

        def SetYesNoLabels(self, _yes, _no):
            return True

        def SetYesNoCancelLabels(self, _yes, _no, _cancel):
            return True

        def ShowModal(self):
            return wx.ID_OK

    wx.Window = Window
    wx.Frame = Frame
```

Edit: `client/tests/wx_stub.py`

```python

def load_speech_dialog():
    """Load ``dialog.py`` as ``SPEECH_DIALOG_MODULE_NAME``; return ``(module, scope)``."""
    scope = StubScope(speech_dialog_stubs(), evict=evict_speech_roots)
    with scope.loading():
        module = scope.load_file(SPEECH_DIALOG_MODULE_NAME, DIALOG_PATH)
    return module, scope
```

```python

def load_speech_dialog():
    """Load ``dialog.py`` as ``SPEECH_DIALOG_MODULE_NAME``; return ``(module, scope)``."""
    scope = StubScope(speech_dialog_stubs(), isolate=("ui.message_box",), evict=evict_speech_roots)
    with scope.loading():
        module = scope.load_file(SPEECH_DIALOG_MODULE_NAME, DIALOG_PATH)
    return module, scope
```

Edit: `client/tests/test_dialog_validation.py`

```python

from tests import wx_stub

_SCOPE = wx_stub.StubScope(wx_stub.dialog_validation_stubs(), isolate=("dialog",))
with _SCOPE.loading():
    import dialog as dialog_module
    from dialog import (
```

```python

from tests import wx_stub

_SCOPE = wx_stub.StubScope(wx_stub.dialog_validation_stubs(), isolate=("dialog", "ui.message_box"))
with _SCOPE.loading():
    import dialog as dialog_module
    from dialog import (
```

Edit: `client/tests/test_dialog_validation.py`

```python
            events.append(("MessageBox", args, kwargs))

        with (
            patch.object(dialog_module.wx, "MessageBox", message_box, create=True),
            patch.object(dialog_module.wx, "OK", 4, create=True),
            patch.object(dialog_module.wx, "ICON_INFORMATION", 128, create=True),
        ):
```

```python
            events.append(("MessageBox", args, kwargs))

        with (
            patch.object(dialog_module, "message_box", message_box),
            patch.object(dialog_module.wx, "OK", 4, create=True),
            patch.object(dialog_module.wx, "ICON_INFORMATION", 128, create=True),
        ):
```

Edit: `client/tests/test_converting_dialog.py`

```python
from tests import wx_stub

# The module that defines ConvertingDialog, loaded against stub wx.
_SCOPE = wx_stub.StubScope(wx_stub.dialog_validation_stubs(), isolate=("dialog",))
with _SCOPE.loading():
    import dialog as defining_module

```

```python
from tests import wx_stub

# The module that defines ConvertingDialog, loaded against stub wx.
_SCOPE = wx_stub.StubScope(wx_stub.dialog_validation_stubs(), isolate=("dialog", "ui.message_box"))
with _SCOPE.loading():
    import dialog as defining_module

```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            StaticText=self._static_text,
            TextCtrl=self._text_ctrl,
            Button=self._button,
            MessageBox=self._message_box,
        )

    # construction
```

```python
            StaticText=self._static_text,
            TextCtrl=self._text_ctrl,
            Button=self._button,
        )

    # construction
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
            stack.enter_context(patch.object(dialog, "wx", self.wx))
            stack.enter_context(patch.object(dialog, "CallbackVirtualListCtrl", self._list_ctrl))
            stack.enter_context(patch.object(dialog, "AddSymbolDialog", self._entry_dialog))
            # Editor tests check the dialog and the saved bytes, not durability: every OK
            # would otherwise wait for a real fsync (40 in the trace replay alone).
            # tests.test_atomic_write keeps the real fsync.
```

```python
            stack.enter_context(patch.object(dialog, "wx", self.wx))
            stack.enter_context(patch.object(dialog, "CallbackVirtualListCtrl", self._list_ctrl))
            stack.enter_context(patch.object(dialog, "AddSymbolDialog", self._entry_dialog))
            stack.enter_context(patch.object(dialog, "message_box", self._message_box))
            # Editor tests check the dialog and the saved bytes, not durability: every OK
            # would otherwise wait for a real fsync (40 in the trace replay alone).
            # tests.test_atomic_write keeps the real fsync.
```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
		name_dialog.__exit__.assert_called_once()

	def test_show_info_uses_information_box_on_dialog(self):
		with patch.object(self.wx, "MessageBox") as message_box:
			self.target.show_info("message")

		message_box.assert_called_once_with(
```

```python
		name_dialog.__exit__.assert_called_once()

	def test_show_info_uses_information_box_on_dialog(self):
		with patch.object(dialog, "message_box") as message_box:
			self.target.show_info("message")

		message_box.assert_called_once_with(
```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
		)

	def test_show_error_uses_error_box_on_dialog(self):
		with patch.object(self.wx, "MessageBox") as message_box:
			self.target.show_error("message")

		message_box.assert_called_once_with(
```

```python
		)

	def test_show_error_uses_error_box_on_dialog(self):
		with patch.object(dialog, "message_box") as message_box:
			self.target.show_error("message")

		message_box.assert_called_once_with(
```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
	def test_confirm_uses_warning_yes_no_box_with_no_default(self):
		for answer, expected in ((self.wx.YES, True), (self.wx.NO, False)):
			with self.subTest(answer=answer):
				with patch.object(self.wx, "MessageBox", return_value=answer) as message_box:
					result = self.target.confirm("message", "caption")

				self.assertIs(result, expected)
```

```python
	def test_confirm_uses_warning_yes_no_box_with_no_default(self):
		for answer, expected in ((self.wx.YES, True), (self.wx.NO, False)):
			with self.subTest(answer=answer):
				with patch.object(dialog, "message_box", return_value=answer) as message_box:
					result = self.target.confirm("message", "caption")

				self.assertIs(result, expected)
```

Edit: `client/tests/test_gui_document_flows.py`

```python

_SCOPE = wx_stub.StubScope(
    wx_stub.gui_frame_stubs(),
    isolate=("gui", "settings.dialogs", "ui.dual_view"),
)
with _SCOPE.loading():
    gui = importlib.import_module("gui")
```

```python

_SCOPE = wx_stub.StubScope(
    wx_stub.gui_frame_stubs(),
    isolate=("gui", "settings.dialogs", "ui.dual_view", "ui.message_box"),
)
with _SCOPE.loading():
    gui = importlib.import_module("gui")
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame = self._make_frame(documents, open_name="alpha", selected_name="beta")
        frame._workspace_service.delete_document.side_effect = frame._document_controller.delete_document

        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
            frame.on_delete_document(None)

        frame._workspace_service.delete_document.assert_called_once_with("beta")
```

```python
        frame = self._make_frame(documents, open_name="alpha", selected_name="beta")
        frame._workspace_service.delete_document.side_effect = frame._document_controller.delete_document

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_document(None)

        frame._workspace_service.delete_document.assert_called_once_with("beta")
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        error = OSError("locked")
        frame._workspace_service.delete_document.side_effect = error

        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
            frame.on_delete_document(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
```

```python
        error = OSError("locked")
        frame._workspace_service.delete_document.side_effect = error

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_document(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents

        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
            frame.on_delete_all_documents(None)

        frame._workspace_service.delete_all_documents.assert_called_once_with(on_error=ANY)
```

```python

        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_all_documents(None)

        frame._workspace_service.delete_all_documents.assert_called_once_with(on_error=ANY)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            return DeleteAllResult(completed=False, invalid_paths=invalid_paths)

        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents

        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
            frame.on_delete_all_documents(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
        self.assertEqual(
```

```python
            return DeleteAllResult(completed=False, invalid_paths=invalid_paths)

        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_all_documents(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
        self.assertEqual(
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame.dictionary_dir = Path("dictionary")
        with (
            patch.object(gui.TextProcessingDialog, "show_singleton", side_effect=OSError("denied")),
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            frame.on_open_text_processing(None)
        message_box.assert_called_once_with(
```

```python
        frame.dictionary_dir = Path("dictionary")
        with (
            patch.object(gui.TextProcessingDialog, "show_singleton", side_effect=OSError("denied")),
            patch.object(gui, "message_box") as message_box,
        ):
            frame.on_open_text_processing(None)
        message_box.assert_called_once_with(
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            patch.object(gui, "prepare_application_directories", side_effect=error),
            patch.object(gui, "build_default_translation_runtime") as build_runtime,
            patch.object(gui, "BrailleFrame") as frame_class,
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            app = gui.BrailleApp()
            result = app.OnInit()
```

```python
            patch.object(gui, "prepare_application_directories", side_effect=error),
            patch.object(gui, "build_default_translation_runtime") as build_runtime,
            patch.object(gui, "BrailleFrame") as frame_class,
            patch.object(gui, "message_box") as message_box,
        ):
            app = gui.BrailleApp()
            result = app.OnInit()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
            patch.object(gui, "prepare_application_directories", return_value=paths),
            patch.object(gui, "cleanup_dual_view_html", side_effect=cause),
            patch.object(gui, "build_default_translation_runtime") as build_runtime,
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            app = gui.BrailleApp()
            result = app.OnInit()
```

```python
            patch.object(gui, "prepare_application_directories", return_value=paths),
            patch.object(gui, "cleanup_dual_view_html", side_effect=cause),
            patch.object(gui, "build_default_translation_runtime") as build_runtime,
            patch.object(gui, "message_box") as message_box,
        ):
            app = gui.BrailleApp()
            result = app.OnInit()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        with ExitStack() as stack:
            for name, fake in self._startup_recorders(order).items():
                stack.enter_context(patch.object(gui, name, side_effect=fake))
            message_box = stack.enter_context(patch.object(gui.wx, "MessageBox"))
            result = gui.BrailleApp().OnInit()

        self.assertTrue(result)
```

```python
        with ExitStack() as stack:
            for name, fake in self._startup_recorders(order).items():
                stack.enter_context(patch.object(gui, name, side_effect=fake))
            message_box = stack.enter_context(patch.object(gui, "message_box"))
            result = gui.BrailleApp().OnInit()

        self.assertTrue(result)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        with ExitStack() as stack:
            for name, fake in self._startup_recorders(order, prepare_error=error).items():
                stack.enter_context(patch.object(gui, name, side_effect=fake))
            message_box = stack.enter_context(patch.object(gui.wx, "MessageBox"))
            result = gui.BrailleApp().OnInit()

        self.assertFalse(result)
```

```python
        with ExitStack() as stack:
            for name, fake in self._startup_recorders(order, prepare_error=error).items():
                stack.enter_context(patch.object(gui, name, side_effect=fake))
            message_box = stack.enter_context(patch.object(gui, "message_box"))
            result = gui.BrailleApp().OnInit()

        self.assertFalse(result)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame._workspace_service = Mock()
        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents

        with patch.object(gui.wx, "MessageBox", return_value=gui.wx.YES):
            frame.on_delete_all_documents(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
```

```python
        frame._workspace_service = Mock()
        frame._workspace_service.delete_all_documents.side_effect = delete_all_documents

        with patch.object(gui, "message_box", return_value=gui.wx.YES):
            frame.on_delete_all_documents(None)

        frame._show_file_error.assert_called_once_with(gui._("Failed to delete document: {error}"), error)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        error = big5_decode_error()

        with (
            patch.object(gui.wx, "MessageBox") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)
```

```python
        error = big5_decode_error()

        with (
            patch.object(gui, "message_box") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        error = RuntimeError("injected")

        with (
            patch.object(gui.wx, "MessageBox") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)
```

```python
        error = RuntimeError("injected")

        with (
            patch.object(gui, "message_box") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)
```

Edit: `client/tests/test_gui_document_flows.py`

```python
                document = Document("alpha", "t", "b")
                with (
                    patch.object(gui.wx, "FileDialog", Mock(return_value=dialog)),
                    patch.object(gui.wx, "MessageBox", Mock()) as message_box,
                ):
                    frame._export_coordinator.export_document(document, "brl")

```

```python
                document = Document("alpha", "t", "b")
                with (
                    patch.object(gui.wx, "FileDialog", Mock(return_value=dialog)),
                    patch.object(gui, "message_box", Mock()) as message_box,
                ):
                    frame._export_coordinator.export_document(document, "brl")

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.import_paths: list[str] = []
        self.import_filter_index = gui.ALL_SUPPORTED_FILTER_INDEX
        for patcher in (
            patch.object(gui.wx, "MessageBox", self._message_box),
            patch.object(gui.wx, "MessageDialog", self._message_dialog_class()),
            patch.object(gui, "DocumentNameDialog", self._name_dialog_class()),
            patch.object(gui, "InvalidWorkspaceFilesDialog", self._invalid_files_dialog_class()),
```

```python
        self.import_paths: list[str] = []
        self.import_filter_index = gui.ALL_SUPPORTED_FILTER_INDEX
        for patcher in (
            patch.object(gui, "message_box", self._message_box),
            patch.object(gui.wx, "MessageDialog", self._message_dialog_class()),
            patch.object(gui, "DocumentNameDialog", self._name_dialog_class()),
            patch.object(gui, "InvalidWorkspaceFilesDialog", self._invalid_files_dialog_class()),
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.threads = self.thread_factory.threads
        self.menu_bar = _RecordingMenuBar(self.events)
        for patcher in (
            patch.object(gui.wx, "MessageBox", self._message_box),
            patch.object(gui.wx, "FileDialog", self._file_dialog_class()),
            patch.object(gui.wx, "DirDialog", self._dir_dialog_class()),
            patch.object(gui.wx, "CallAfter", self.calls),
```

```python
        self.threads = self.thread_factory.threads
        self.menu_bar = _RecordingMenuBar(self.events)
        for patcher in (
            patch.object(gui, "message_box", self._message_box),
            patch.object(gui.wx, "FileDialog", self._file_dialog_class()),
            patch.object(gui.wx, "DirDialog", self._dir_dialog_class()),
            patch.object(gui.wx, "CallAfter", self.calls),
```

Edit: `client/tests/test_gui_document_flows.py`

```python

    def test_message_methods_use_one_message_box_each(self) -> None:
        frame = self._make_frame()
        with patch.object(gui.wx, "MessageBox") as message_box:
            frame.show_info("info text", "Info caption")
            frame.show_error("error text", "Error caption")

```

```python

    def test_message_methods_use_one_message_box_each(self) -> None:
        frame = self._make_frame()
        with patch.object(gui, "message_box") as message_box:
            frame.show_info("info text", "Info caption")
            frame.show_error("error text", "Error caption")

```

Edit: `client/tests/test_gui_document_flows.py`

```python

    def test_show_file_error_formats_the_error_for_the_frame(self) -> None:
        frame = self._make_frame()
        with patch.object(gui.wx, "MessageBox") as message_box:
            frame._show_file_error("Failed: {error}", OSError("disk full"))

        message_box.assert_called_once_with(
```

```python

    def test_show_file_error_formats_the_error_for_the_frame(self) -> None:
        frame = self._make_frame()
        with patch.object(gui, "message_box") as message_box:
            frame._show_file_error("Failed: {error}", OSError("disk full"))

        message_box.assert_called_once_with(
```

Edit: `client/tests/test_gui_document_flows.py`

```python

    def test_confirm_overwrite_all_asks_only_for_conflicts(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        with patch.object(gui.wx, "MessageBox") as message_box:
            self.assertTrue(frame.confirm_overwrite_all([]))
            message_box.assert_not_called()
            for answer, expected in ((gui.wx.YES, True), (gui.wx.NO, False)):
```

```python

    def test_confirm_overwrite_all_asks_only_for_conflicts(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        with patch.object(gui, "message_box") as message_box:
            self.assertTrue(frame.confirm_overwrite_all([]))
            message_box.assert_not_called()
            for answer, expected in ((gui.wx.YES, True), (gui.wx.NO, False)):
```

Edit: `client/tests/test_gui_document_flows.py`

```python

    def test_show_warning_uses_the_warning_icon(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        with patch.object(gui.wx, "MessageBox") as message_box:
            frame.show_warning("warning text", "Warning caption")

        message_box.assert_called_once_with(
```

```python

    def test_show_warning_uses_the_warning_icon(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        with patch.object(gui, "message_box") as message_box:
            frame.show_warning("warning text", "Warning caption")

        message_box.assert_called_once_with(
```

Edit: `client/tests/test_settings_dialogs.py`

```python

from tests import wx_stub

_SCOPE = wx_stub.StubScope(wx_stub.settings_dialog_stubs(), isolate=("settings.dialogs",))
with _SCOPE.loading():
    import wx

```

```python

from tests import wx_stub

_SCOPE = wx_stub.StubScope(wx_stub.settings_dialog_stubs(), isolate=("settings.dialogs", "ui.message_box"))
with _SCOPE.loading():
    import wx

```

Edit: `client/tests/test_settings_dialogs.py`

```python
                "settings.dialogs.save_preprocessing_script",
                side_effect=SyntaxError("invalid syntax"),
            ),
            patch("settings.dialogs.wx.MessageBox") as message_box,
        ):
            self.assertFalse(dialog.on_apply())
        dialog.Destroy.assert_not_called()
        dialog.editor.SetFocus.assert_called_once_with()
        message_box.assert_called_once()

    def test_ok_destroys_only_after_successful_apply(self) -> None:
        dialog = self.make_dialog()
```

```python
                "settings.dialogs.save_preprocessing_script",
                side_effect=SyntaxError("invalid syntax"),
            ),
            patch("settings.dialogs.message_box") as message_box,
        ):
            self.assertFalse(dialog.on_apply())
        dialog.Destroy.assert_not_called()
        dialog.editor.SetFocus.assert_called_once_with()
        message_box.assert_called_once_with(
            i18n._("Unable to save text processing script: {error}").format(error="invalid syntax"),
            i18n._("Text Processing"),
            wx.OK | wx.ICON_ERROR,
            parent=dialog,
        )

    def test_ok_destroys_only_after_successful_apply(self) -> None:
        dialog = self.make_dialog()
```

Edit: `client/tests/test_settings_dialogs.py`

```python
        dialog.panel_instances = {1: panel}

        with patch("settings.dialogs._", side_effect=lambda text: text):
            with patch("settings.dialogs.wx.MessageBox") as message_box:
                result = dialog.on_apply()

        self.assertFalse(result)
```

```python
        dialog.panel_instances = {1: panel}

        with patch("settings.dialogs._", side_effect=lambda text: text):
            with patch("settings.dialogs.message_box") as message_box:
                result = dialog.on_apply()

        self.assertFalse(result)
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_message_box tests.test_wx_call_sites tests.test_dialog_validation tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(ok_box_sets|ok_cancel_box|yes_no_box_keeps|unexpected_result_maps|parent_can_be|a_label_the_platform|no_production_module_calls|message_dialogs_are_the_helper|invalid_entry_shows_the_message_on_the_dialog|about_box_uses_the_helper)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_message_box tests.test_wx_call_sites tests.test_dialog_display tests.test_dialog_validation tests.test_converting_dialog tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_settings_dialogs tests.test_gui_document_flows tests.test_wx_stub 2>&1 | $PY $T/tools/brief.py
grep -c 'message_box(' dialog.py gui.py settings/dialogs.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`gui.py` counts its 11 former `wx.MessageBox` calls and `on_about`; the import lines have no parenthesis):

```text
test_a_label_the_platform_refuses_still_shows_the_box ok
test_ok_box_sets_the_translated_ok_label ok
test_ok_cancel_box_sets_both_labels ok
test_parent_can_be_omitted_or_positional ok
test_unexpected_result_maps_to_cancel ok
test_yes_no_box_keeps_the_system_labels ok
test_message_dialogs_are_the_helper_or_set_every_label ok
test_no_production_module_calls_wx_message_box ok
test_invalid_entry_shows_the_message_on_the_dialog_and_focuses_the_source_text ok
test_about_box_uses_the_helper ok
Ran 437 tests
OK
dialog.py:7
gui.py:12
settings/dialogs.py:2
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1352 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/ui/message_box.py client/dialog.py client/gui.py client/settings/dialogs.py client/tests/wx_stub.py client/tests/test_message_box.py client/tests/test_wx_call_sites.py client/tests/test_dialog_validation.py client/tests/test_converting_dialog.py client/tests/test_dictionary_entries_dialog.py client/tests/test_dictionary_management_dialog.py client/tests/test_gui_document_flows.py client/tests/test_settings_dialogs.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: show message boxes with the translated OK button (F-7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/dialog.py                                  |  15 +-
 client/gui.py                                     |  31 ++--
 client/settings/dialogs.py                        |   5 +-
 client/tests/test_converting_dialog.py            |   2 +-
 client/tests/test_dialog_validation.py            |  27 +++-
 client/tests/test_dictionary_entries_dialog.py    |   2 +-
 client/tests/test_dictionary_management_dialog.py |   6 +-
 client/tests/test_gui_document_flows.py           |  49 ++++---
 client/tests/test_message_box.py                  | 166 ++++++++++++++++++++++
 client/tests/test_settings_dialogs.py             |  13 +-
 client/tests/test_wx_call_sites.py                |  23 +++
 client/tests/wx_stub.py                           |  20 ++-
 client/ui/message_box.py                          |  29 ++++
 13 files changed, 329 insertions(+), 59 deletions(-)
79ee79a7c70413df0305e3136ce88e071397e5d0
```

### Task 3: Read the editors without lone surrogates (D5)

- [ ] **Step 1: Red: D1-D3** (`client/tests/test_gui_document_flows.py`, 4 spaces; `LONE_SURROGATE = chr(0xD83D)` at module level). D1 is in `FrameViewMethodsTest` (the frame's view methods with Mock editors), D2 in the F-5 save tests, D3 in `ConversionExportFlowsCharacterizationTest` (the fake converter knows only the replaced text).

Edit: `client/tests/test_gui_document_flows.py`

```python
from dual_view.model import build_dual_view_model
from dictionaries.read_problems import describe_unreadable_dictionary
from tests.unreadable_dictionary_files import big5_decode_error


def make_paths(root: Path = Path("unused-root"), **folders: Path) -> app_paths.ApplicationPaths:
```

```python
from dual_view.model import build_dual_view_model
from dictionaries.read_problems import describe_unreadable_dictionary
from tests.unreadable_dictionary_files import big5_decode_error

# Half of a surrogate pair, as pasting part of an emoji can leave it in an editor (F-5 review M-7).
LONE_SURROGATE = chr(0xD83D)


def make_paths(root: Path = Path("unused-root"), **folders: Path) -> app_paths.ApplicationPaths:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._package("alpha"), Document("alpha", "x�", "1"))
        self.assertEqual(frame.input_txt.value, "x\ud800")

    def test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks(self) -> None:
        # Before F-3 the exception escaped _on_close: no message, and the window neither
        # closed nor said why. F-5 (D6, D9): the traceback is logged at each attempt and
```

```python
        self.assertEqual(self._package("alpha"), Document("alpha", "x�", "1"))
        self.assertEqual(frame.input_txt.value, "x\ud800")

    def test_save_reads_both_editors_through_the_replacement(self) -> None:
        # F-7 (M-7): the frame reads the editors through replace_lone_surrogates; F-5's
        # replacement in the documents layer stays as the second line of defense.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a" + LONE_SURROGATE)
        frame.output_txt.SetValue("1" + LONE_SURROGATE)
        service = frame._workspace_service

        with patch.object(service, "save_open_document", wraps=service.save_open_document) as save:
            frame._save_open_document()

        save.assert_called_once_with(text="a�", braille="1�")
        self.assertEqual(frame.input_txt.value, "a" + LONE_SURROGATE)
        self.assertEqual(frame.output_txt.value, "1" + LONE_SURROGATE)
        self.assertEqual(self._package("alpha"), Document("alpha", "a�", "1�"))

    def test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks(self) -> None:
        # Before F-3 the exception escaped _on_close: no message, and the window neither
        # closed nor said why. F-5 (D6, D9): the traceback is logged at each attempt and
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "a", None)])
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {})

    def test_conversion_failure_messages_by_stage_and_public_text(self) -> None:
        cases = (
            (ConversionStageError("ascii", RuntimeError("bad map")), gui._("ASCII conversion failed: {error}"), "bad map"),
```

```python
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "a", None)])
        self.assertEqual(frame._document_controller.dual_view_results_by_document, {})

    def test_manual_conversion_stores_replaced_text(self) -> None:
        # F-7 (M-7): the conversion, its dual-view segments and the open document's text get
        # U+FFFD; the source editor keeps what the user pasted.
        frame = self._make_frame([Document("alpha", "a", None)], "alpha")
        frame.input_txt.value = "A" + LONE_SURROGATE + "B"
        segment = _dual_view_segment("A�B", "⠁")
        self.outputs["A�B"] = ConversionOutput("⠁", ("result",), (segment,))

        frame.on_convert(None)
        self.threads[0].run()

        self.assertEqual([request.raw_text for request in self.requests], ["A�B"])
        self.calls.run_next()
        controller = frame._document_controller
        self.assertEqual(controller.documents, [Document("alpha", "A�B", "⠁")])
        self.assertEqual(controller.dual_view_results_by_document, {"alpha": (segment,)})
        self.assertEqual(frame.input_txt.value, "A" + LONE_SURROGATE + "B")
        self.assertEqual([event for event in self.events if event[:2] == ("set", "input")], [])

    def test_conversion_failure_messages_by_stage_and_public_text(self) -> None:
        cases = (
            (ConversionStageError("ascii", RuntimeError("bad map")), gui._("ASCII conversion failed: {error}"), "bad map"),
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        self.assertEqual(frame.get_source_text(), "source")

    def test_set_conversion_busy_toggles_file_and_translation_menus_list_and_source(self) -> None:
        menu_bar = Mock()
        menu_bar.FindMenu.side_effect = lambda title: {gui._("File"): 0, gui._("Translation"): 1}.get(
```

```python

        self.assertEqual(frame.get_source_text(), "source")

    def test_source_text_for_conversion_replaces_lone_surrogates_without_touching_the_editor(self) -> None:
        # F-7 (M-7): no SetValue, so the caret stays where it is and NVDA does not re-read.
        frame = self._make_frame()
        frame.input_txt.GetValue.return_value = "A" + LONE_SURROGATE + "B"

        self.assertEqual(frame.get_source_text(), "A�B")
        self.assertEqual(frame.steps.mock_calls, [call.input_txt.GetValue()])

    def test_set_conversion_busy_toggles_file_and_translation_menus_list_and_source(self) -> None:
        menu_bar = Mock()
        menu_bar.FindMenu.side_effect = lambda title: {gui._("File"): 0, gui._("Translation"): 1}.get(
```

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (the raw editor text is passed on; the fake converter has no output for it):

```text
ERROR: test_manual_conversion_stores_replaced_text (tests.test_gui_document_flows.ConversionExportFlowsCharacterizationTest.test_manual_conversion_stores_replac
KeyError: 'A\ud83dB'
FAIL: test_save_reads_both_editors_through_the_replacement (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_save_reads_both_editor
AssertionError: expected call not found.
FAIL: test_source_text_for_conversion_replaces_lone_surrogates_without_touching_the_editor (tests.test_gui_document_flows.FrameViewMethodsTest.test_source_text_
AssertionError: 'A\ud83dB' != 'A�B'
Ran 187 tests
FAILED (failures=2, errors=1)
```

- [ ] **Step 2: Read the editors through `replace_lone_surrogates`** (`client/gui.py`, tabs; the import list of `documents.workspace` uses 4 spaces).

Edit: `client/gui.py`

```python
    Document,
    create_default_document,
    normalize_document_name,
)
from documents.workspace_service import DocumentWorkspaceService
from ui.action_menu import get_document_menu_enabled_state
```

```python
    Document,
    create_default_document,
    normalize_document_name,
    replace_lone_surrogates,
)
from documents.workspace_service import DocumentWorkspaceService
from ui.action_menu import get_document_menu_enabled_state
```

Edit: `client/gui.py`

```python
		self._open_document_by_name(target_name)
		self.input_txt.SetFocus()

	def _save_open_document(self) -> None:
		self._workspace_service.save_open_document(
			text=self.input_txt.GetValue(),
			braille=self.output_txt.GetValue(),
		)

	def _save_open_document_with_feedback(self) -> bool:
```

```python
		self._open_document_by_name(target_name)
		self.input_txt.SetFocus()

	def _editor_text(self, control: wx.TextCtrl) -> str:
		"""The control's text with each lone surrogate replaced by U+FFFD (F-7, M-7); the control is not changed."""
		return replace_lone_surrogates(control.GetValue())

	def _save_open_document(self) -> None:
		self._workspace_service.save_open_document(
			text=self._editor_text(self.input_txt),
			braille=self._editor_text(self.output_txt),
		)

	def _save_open_document_with_feedback(self) -> bool:
```

Edit: `client/gui.py`

```python
	# --- ConversionView (ui/conversion_presenter.py) ------------------------

	def get_source_text(self) -> str:
		return self.input_txt.GetValue()

	def set_conversion_busy(self, busy: bool) -> None:
		menu_bar = self.GetMenuBar()
```

```python
	# --- ConversionView (ui/conversion_presenter.py) ------------------------

	def get_source_text(self) -> str:
		return self._editor_text(self.input_txt)

	def set_conversion_busy(self, busy: bool) -> None:
		menu_bar = self.GetMenuBar()
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(source_text_for_conversion_replaces|save_reads_both_editors|manual_conversion_stores_replaced_text|get_source_text_reads|pasted_lone_surrogate)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_manual_conversion_stores_replaced_text ok
test_pasted_lone_surrogate_is_saved_as_replacement_character ok
test_save_reads_both_editors_through_the_replacement ok
test_get_source_text_reads_the_source_editor ok
test_source_text_for_conversion_replaces_lone_surrogates_without_touching_the_editor ok
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1355 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: read the editors without lone surrogates (F-7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/gui.py                           | 11 +++++---
 client/tests/test_gui_document_flows.py | 46 +++++++++++++++++++++++++++++++++
 2 files changed, 54 insertions(+), 3 deletions(-)
7532bf2a6b19387398ece4e0f50c9fe430e2ae40
```

### Task 4: Report every export failure (D6)

- [ ] **Step 1: Red: D4-D8, the import test and the defect-7 test** (`client/tests/test_export_coordinator.py`, 4 spaces). The module now isolates the `dotexpress.gui` logger in `setUpModule`. D5 (an `OSError` is not logged) and the import test are green before the change; they guard what must stay.

Edit: `client/tests/test_export_coordinator.py`

```python
from __future__ import annotations

import ast
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, call, patch

import documents.export_coordinator as coordinator_module
from ui.conversion_presenter import ConversionPresenter
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from documents.controller import DocumentController
from documents.export_coordinator import ExportCoordinator
```

```python
from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import documents.export_coordinator as coordinator_module
from ui.conversion_presenter import ConversionPresenter
from conversion.output import DualViewSegment
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from documents.controller import DocumentController
from documents.export_coordinator import ExportCoordinator
```

Edit: `client/tests/test_export_coordinator.py`

```python
from documents.workspace import Document
from i18n import _
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory

COORDINATOR_PATH = Path(__file__).resolve().parents[1] / "documents" / "export_coordinator.py"
MISSING_TABLE = "missing table"


class RecordingExportView:
```

```python
from documents.workspace import Document
from i18n import _
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
from tests.file_log_isolation import isolate_file_logs

COORDINATOR_PATH = Path(__file__).resolve().parents[1] / "documents" / "export_coordinator.py"
MISSING_TABLE = "missing table"
LOGGER = "dotexpress.gui"
# Half of a surrogate pair, as pasting part of an emoji can leave it in an editor (F-5 review M-7).
LONE_SURROGATE = chr(0xD83D)


def setUpModule() -> None:
    # The coordinator logs unexpected export errors to gui.log (F-7); keep the real file out of it.
    unittest.addModuleCleanup(isolate_file_logs(LOGGER))


def _writer_failing_for(name: str, error: Exception):
    """The BRL writer, except that it raises ``error`` for the document called ``name``."""
    write_brl = get_format("brl").writer

    def writer(path, document, context):
        if document.name == name:
            raise error
        return write_brl(path, document, context)

    return writer


class RecordingExportView:
```

Edit: `client/tests/test_export_coordinator.py`

```python

        self.assertFalse(imported & {"wx", "gui", "dialog"}, imported)

    # --- write_document --------------------------------------------------------

    def test_write_document_uses_registry_writer(self) -> None:
```

```python

        self.assertFalse(imported & {"wx", "gui", "dialog"}, imported)

    def test_importing_binds_no_log_file(self) -> None:
        # The gui.log handler is bound when the first error is logged (as in F-6 review M-6), so a
        # test that imports the coordinator without isolating the logger cannot write to log/.
        script = (
            "import logging\n"
            "import documents.export_coordinator\n"
            "handlers = logging.getLogger('dotexpress.gui').handlers\n"
            "assert handlers == [], handlers\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=COORDINATOR_PATH.parents[1],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    # --- write_document --------------------------------------------------------

    def test_write_document_uses_registry_writer(self) -> None:
```

Edit: `client/tests/test_export_coordinator.py`

```python
                ("show_error", _("Failed to export document: {error}").format(error=reason), _("Error")),
            ],
        )

    def test_export_document_pending_converts_document_text_then_writes(self) -> None:
        self.view.paths.append(self.root / "beta.brl")
```

```python
                ("show_error", _("Failed to export document: {error}").format(error=reason), _("Error")),
            ],
        )

    def test_single_export_error_that_is_not_an_os_error_shows_the_failure_message(self) -> None:
        # F-7: before, the exception left the menu handler; the packaged build showed nothing.
        error = ValueError("injected")
        descriptor = replace(get_format("brl"), writer=_writer_failing_for("alpha", error))
        self.view.paths.append(self.root / "alpha.brl")

        with (
            patch.object(coordinator_module, "get_format", return_value=descriptor),
            self.assertLogs(LOGGER, level="ERROR") as logs,
        ):
            self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")

        self.assertEqual(
            self._take(),
            [
                ("choose_export_path", "alpha.brl", "brl"),
                ("show_error", _("Failed to export document: {error}").format(error="injected"), _("Error")),
            ],
        )
        self.assertEqual([record.getMessage() for record in logs.records], ["Unexpected error while exporting a document"])
        self.assertIs(logs.records[0].exc_info[1], error)

    def test_single_export_os_error_is_not_logged(self) -> None:
        blocked = self.root / "blocked.brl"
        blocked.mkdir()
        reason = self._os_error_text(blocked)
        self.view.paths.append(blocked)

        with self.assertNoLogs(LOGGER, level="ERROR"):
            self.coordinator.export_document(Document("alpha", "a", "⠁"), "brl")

        self.assertEqual(
            self._take()[-1],
            ("show_error", _("Failed to export document: {error}").format(error=reason), _("Error")),
        )

    def test_html_export_with_a_lone_surrogate_in_the_dual_view_reports_failure(self) -> None:
        # The M-7 trigger: the dual-view segments carry the source text, and UTF-8 cannot
        # encode a lone surrogate. The frame now replaces it before converting (F-7 D5).
        result = SimpleNamespace(
            raw=["A" + LONE_SURROGATE + "B"], braille=["⠁"], braille_to_raw_pos=[0], raw_to_braille_pos=[0]
        )
        self.documents.set_dual_view_results("alpha", (DualViewSegment(result=result, source_kind="text"),))
        self.view.paths.append(self.root / "alpha.html")

        with self.assertLogs(LOGGER, level="ERROR") as logs:
            self.coordinator.export_document(Document("alpha", "a", "⠁"), "html")

        kind, message, caption = self._take()[-1]
        self.assertEqual((kind, caption), ("show_error", _("Error")))
        self.assertTrue(message.startswith(_("Failed to export document: {error}").format(error="")), message)
        self.assertIn("surrogates not allowed", message)
        self.assertIsInstance(logs.records[0].exc_info[1], UnicodeEncodeError)

    def test_pending_export_failure_after_conversion_is_reported(self) -> None:
        error = ValueError("injected")
        descriptor = replace(get_format("brl"), writer=_writer_failing_for("beta", error))
        self.view.paths.append(self.root / "beta.brl")

        with patch.object(coordinator_module, "get_format", return_value=descriptor):
            self.coordinator.export_document(Document("beta", "b", None), "brl")
            self._take()
            on_success, _on_error = self.conversions.started[0]
            with self.assertLogs(LOGGER, level="ERROR") as logs:
                on_success("⠃⠃")

        self.assertEqual(
            self._take(),
            [("show_error", _("Failed to export document: {error}").format(error="injected"), _("Error"))],
        )
        self.assertIs(logs.records[0].exc_info[1], error)
        self.assertEqual(self._written(), {})

    def test_export_document_pending_converts_document_text_then_writes(self) -> None:
        self.view.paths.append(self.root / "beta.brl")
```

Edit: `client/tests/test_export_coordinator.py`

```python
        )
        self.assertEqual(self.conversions.started, [])

    def test_export_all_writer_value_error_stops_the_chain(self) -> None:
        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", "⠃")]
        self.view.directories.append(self.root)

        # KNOWN BUG (P1-4 spec, defect 7): the error escapes and no summary is shown.
        with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
            self.coordinator.export_all("txt")

        self.assertEqual(self._take(), [("choose_export_directory",)])
        self.assertEqual(self.calls.pending, [])


class ExportThroughConversionPresenterTest(unittest.TestCase):
```

```python
        )
        self.assertEqual(self.conversions.started, [])

    def test_export_all_writer_value_error_is_listed_and_the_chain_goes_on(self) -> None:
        # Was the P1-4 KNOWN BUG (defect 7), fixed by F-7: the error escaped, the chain stopped
        # and no summary was shown.
        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", "⠃")]
        self.view.directories.append(self.root)

        with self.assertLogs(LOGGER, level="ERROR") as logs:
            self.coordinator.export_all("txt")
            self.calls.run_all()

        reason = 'Unsupported export format: "txt".'
        self.assertEqual(
            self._take(),
            [
                ("choose_export_directory",),
                ("call_after",),
                ("call_after",),
                (
                    "show_warning",
                    f"Exported documents: 0\nFailed documents: 2\n\nalpha: {reason}\nbeta: {reason}",
                    "Export Complete with Errors",
                ),
            ],
        )
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(self.calls.pending, [])

    def test_export_all_goes_on_after_an_error_that_is_not_an_os_error(self) -> None:
        error = ValueError("injected")
        descriptor = replace(get_format("brl"), writer=_writer_failing_for("beta", error))
        self.documents.documents = [Document("alpha", "a", "⠁"), Document("beta", "b", "⠃"), Document("gamma", "g", "⠛")]
        self.view.directories.append(self.root)

        with (
            patch.object(coordinator_module, "get_format", return_value=descriptor),
            self.assertLogs(LOGGER, level="ERROR") as logs,
        ):
            self.coordinator.export_all("brl")
            self.calls.run_all()

        self.assertEqual(
            self._take()[-1],
            (
                "show_warning",
                "Exported documents: 2\nFailed documents: 1\n\nbeta: injected",
                "Export Complete with Errors",
            ),
        )
        self.assertEqual(self._written(), {"alpha.brl": "⠁", "gamma.brl": "⠛"})
        self.assertEqual([record.getMessage() for record in logs.records], ["Unexpected error while exporting a document"])
        self.assertIs(logs.records[0].exc_info[1], error)


class ExportThroughConversionPresenterTest(unittest.TestCase):
```

```bash
$PY -m unittest tests.test_export_coordinator 2>&1 | $PY $T/tools/brief.py
```

Expected (each non-`OSError` leaves the coordinator; the HTML writer cannot encode the lone surrogate of the dual-view segment):

```text
ERROR: test_export_all_goes_on_after_an_error_that_is_not_an_os_error (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_goes_on_after_an_erro
ValueError: injected
ERROR: test_export_all_writer_value_error_is_listed_and_the_chain_goes_on (tests.test_export_coordinator.ExportCoordinatorTest.test_export_all_writer_value_erro
ValueError: Unsupported export format: "txt".
ERROR: test_html_export_with_a_lone_surrogate_in_the_dual_view_reports_failure (tests.test_export_coordinator.ExportCoordinatorTest.test_html_export_with_a_lone
UnicodeEncodeError: 'utf-8' codec can't encode character '\ud83d' in position 1290: surrogates not allowed
ERROR: test_pending_export_failure_after_conversion_is_reported (tests.test_export_coordinator.ExportCoordinatorTest.test_pending_export_failure_after_conversio
ERROR: test_single_export_error_that_is_not_an_os_error_shows_the_failure_message (tests.test_export_coordinator.ExportCoordinatorTest.test_single_export_error_
Ran 27 tests
FAILED (errors=5)
```

- [ ] **Step 2: Catch, log and report every write failure** (`client/documents/export_coordinator.py`, 4 spaces). The logger is bound when an error is logged (Spec Corrections 7).

Edit: `client/documents/export_coordinator.py`

```python
folder, check conflicts, then one document per UI turn through ``call_after``, then
one summary). The view owns its dialogs and their texts; the coordinator owns the
outcome messages. The first Export All step runs in the caller's turn.
"""

from __future__ import annotations
```

```python
folder, check conflicts, then one document per UI turn through ``call_after``, then
one summary). The view owns its dialogs and their texts; the coordinator owns the
outcome messages. The first Export All step runs in the caller's turn.

Every write failure is reported: an ``OSError`` by its message, anything else also with
its traceback in ``gui.log`` (F-7).
"""

from __future__ import annotations
```

Edit: `client/documents/export_coordinator.py`

```python
from documents.formats import DocumentFormatDescriptor, ExportContext, get_format
from documents.workspace import Document
from i18n import _

CallAfter = Callable[..., object]

```

```python
from documents.formats import DocumentFormatDescriptor, ExportContext, get_format
from documents.workspace import Document
from i18n import _
from log import get_logger

CallAfter = Callable[..., object]

```

Edit: `client/documents/export_coordinator.py`

```python
            return
        self._write_single(document, destination_path, format_key)

    def _write_single(self, document: Document, destination_path: Path, format_key: str) -> None:
        try:
            self.write_document(destination_path, document, format_key)
        except OSError as exc:
            self._view.show_error(_("Failed to export document: {error}").format(error=exc), _("Error"))
            return
        self._view.show_info(_("The document was exported successfully."), _("Export Complete"))
```

```python
            return
        self._write_single(document, destination_path, format_key)

    def _log_unexpected_export_error(self, error: Exception) -> None:
        """Log the traceback of a failed export if it is not an ``OSError`` (F-7).

        An ``OSError`` (locked, read-only, disk full) is expected and the message names it
        fully. Anything else is a bug or text the writer cannot encode, and the packaged
        build has no console. The logger is bound here, not at import, so importing this
        module adds no file handler (as in F-6 review M-6).
        """
        if not isinstance(error, OSError):
            get_logger("dotexpress.gui", "gui.log").error("Unexpected error while exporting a document", exc_info=error)

    def _write_single(self, document: Document, destination_path: Path, format_key: str) -> None:
        try:
            self.write_document(destination_path, document, format_key)
        except Exception as exc:
            self._log_unexpected_export_error(exc)
            self._view.show_error(_("Failed to export document: {error}").format(error=exc), _("Error"))
            return
        self._view.show_info(_("The document was exported successfully."), _("Export Complete"))
```

Edit: `client/documents/export_coordinator.py`

```python
        def write_document(export_document: Document) -> None:
            try:
                self.write_document(destination_path, export_document, format_key)
            except OSError as exc:
                result.add_failure(document.name, str(exc))
            else:
                result.add_success(document.name)
```

```python
        def write_document(export_document: Document) -> None:
            try:
                self.write_document(destination_path, export_document, format_key)
            except Exception as exc:
                self._log_unexpected_export_error(exc)
                result.add_failure(document.name, str(exc))
            else:
                result.add_success(document.name)
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_export_coordinator -v 2>&1 | grep -E "^test_(importing_binds_no_log_file|single_export_error_that_is_not|single_export_os_error_is_not_logged|html_export_with_a_lone_surrogate|pending_export_failure_after|export_all_writer_value_error_is_listed|export_all_goes_on_after|module_imports_neither)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_export_all_goes_on_after_an_error_that_is_not_an_os_error ok
test_export_all_writer_value_error_is_listed_and_the_chain_goes_on ok
test_html_export_with_a_lone_surrogate_in_the_dual_view_reports_failure ok
test_importing_binds_no_log_file ok
test_module_imports_neither_wx_nor_gui ok
test_pending_export_failure_after_conversion_is_reported ok
test_single_export_error_that_is_not_an_os_error_shows_the_failure_message ok
test_single_export_os_error_is_not_logged ok
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1361 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/documents/export_coordinator.py client/tests/test_export_coordinator.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: report every export failure (F-7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/documents/export_coordinator.py  |  21 +++-
 client/tests/test_export_coordinator.py | 166 +++++++++++++++++++++++++++++++-
 2 files changed, 181 insertions(+), 6 deletions(-)
f9563449fabf770733188b74f5734b3eb09dd7db
```

### Task 5: Confirm M-5 and the lost edits on the pre-F-7 packaged build (D9; no commit)

Not part of the replay (it needs the desktop). Spec D9: before the D7 commit, M-5 must be seen on a packaged build of the pre-F-7 code. `D:\dxtest\N-f6b\DotExpress.exe` is that build (F-6's head `fb7aff9` after its review fixes; the user's current test build); only read and copy it. If it is missing, build `fb7aff9` in a scratch clone as in Task 8 Step 1 into a new `D:\dxtest\N-f6c` and use that. The same run reproduces the newly found lost-edits defect (item 55) and records the "Before" column of the other items. Run everything from the repository root, one script at a time, with nothing else driving the desktop. Never touch `D:\dxtest\N`, `B`, `N-p25`, `N-f3`, `N-f4*`, `N-f5*`, `N-f6*` or the existing `D:\dxtest\auto*` folders; every run of this task uses a new folder whose name ends in `-f6b-f7`. Only processes whose exe lies under that folder are ended (`dx.kill_under`); `lock.py` is ended with `taskkill /T`. The user may have DotExpress open: never end any other process. Messages go only to the main window of the DotExpress process under test: never call `ExitWindowsEx`, `InitiateSystemShutdownEx`, `shutdown.exe` or `logoff`.

- [ ] **Step 1: Create the GUI scripts** in the new history folder by the block script (tabs, like the 2026-10-09-03 and F-5 helpers they import; they hold zh-TW labels as real characters, as `dicts.py` does). `f7gui.py` holds the shared helpers (message boxes through UIA, win32 dialog buttons, the file and folder dialogs, the session messages from a driver thread, the close-dialog count); `item53.py` covers items 53, 56 and 57, `item54.py` 54 and 55, `item58.py` 58-60 (one mode per item), `item61.py` 61-63. The folder stays untracked until Task 8.

File: `docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/f7gui.py`

````python
"""Shared helpers for the F-7 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py, dicts.py and lock.py of the 2026-10-09-03 Windows verification
and f5gui.py of F-5, unchanged. wx shows its message boxes as Windows task dialogs:
``boxes`` reads each one through UIA (title, main instruction, content, buttons, focus)
and ``answer_box`` presses a key in it (f5gui.answer, which presses again if the key was
lost). The app's own dialogs (name dialogs, the dictionary editor, Settings, Text
Processing) are plain win32 dialogs, read by ``buttons``.

The session-end items send WM_QUERYENDSESSION or WM_ENDSESSION to the main window of
the DotExpress process under test only, from a driver thread (SendMessageTimeoutW).
Nothing here asks Windows to log off or shut down.
"""
import ctypes
import os
import sys
import threading
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
F5 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-10-01-f5-save-failure-handling", "auto"))
sys.path.insert(0, F5)
import f5gui as F  # noqa: E402  (puts 2026-10-09-03/auto on sys.path)
from f5gui import D, dx  # noqa: E402
import dicts as X  # noqa: E402

F.KEYS.update({"alt-y": "%y", "alt-n": "%n"})
CLOSE_DIALOG = F.CLOSE_DIALOG_TITLE
TEXT_PROCESSING = "文字處理"
SETTINGS_PREFIX = "DotExpress 設定"
MGR = "字典管理"
EDITOR = "自訂字典管理器"
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
ENDSESSION_LOGOFF = 0x80000000
SMTO_NORMAL = 0x0000

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SendMessageTimeoutW.argtypes = (
	wintypes.HWND,
	wintypes.UINT,
	wintypes.WPARAM,
	wintypes.LPARAM,
	wintypes.UINT,
	wintypes.UINT,
	ctypes.POINTER(ctypes.c_size_t),
)
user32.SendMessageTimeoutW.restype = ctypes.c_size_t


def is_task_dialog(win):
	return any(c.class_name() == "DirectUIHWND" for c in win.wrapper_object().children())


def task_dialogs(app):
	"""The open message boxes (task dialogs) of ``app``, as UIA wrappers."""
	from pywinauto import Desktop

	return [Desktop(backend="uia").window(handle=box.handle) for box in dx.dialogs(app) if is_task_dialog(box)]


def wait_box(app, timeout=10):
	end = time.time() + timeout
	while time.time() < end:
		found = task_dialogs(app)
		if found:
			return found[0]
		time.sleep(0.3)
	return None


def answer_box(app, key, timeout=10):
	"""Read the next message box, press ``key`` (a key of f5gui.KEYS) and return what it showed.

	The result is the description of f5gui.describe plus ``presses``, or None if no box
	opened within ``timeout`` seconds.
	"""
	box = wait_box(app, timeout)
	if box is None:
		return None
	described = F.describe(box)
	described["presses"] = F.answer(box, key)
	return described


def buttons(win):
	"""The visible win32 buttons of a wx dialog, in tab order."""
	return [c.window_text() for c in win.wrapper_object().descendants() if c.class_name() == "Button" and c.is_visible()]


def edit_text(win):
	return win.child_window(class_name="Edit", found_index=0).wrapper_object().window_text()


def windows(app, w):
	return sorted(X.windows(app, w))


def window_titled(app, w, prefix, timeout=10):
	end = time.time() + timeout
	while time.time() < end:
		for title, win in X.windows(app, w).items():
			if title.startswith(prefix):
				return win
		time.sleep(0.3)
	raise RuntimeError(f"no window {prefix}: {windows(app, w)}")


def menu(w, path, wait=1.5):
	w.set_focus()
	w.menu_select(path)
	time.sleep(wait)


def path_dialog(app, w, title, path):
	"""Fill the file or folder dialog ``title`` with ``path`` and press its Save, Open or
	Select Folder button: the first visible button other than Cancel."""
	dialog = X.wait_window(app, w, title)
	dialog.child_window(class_name="Edit", found_index=0).wrapper_object().set_edit_text(path)
	pressable = [
		c
		for c in dialog.wrapper_object().descendants()
		if c.class_name() == "Button" and c.is_visible() and c.window_text() not in ("取消", "Cancel")
	]
	pressable[0].click()
	time.sleep(2)


def press_keys(win, keys, wait=1.0):
	from pywinauto.keyboard import send_keys

	win.set_focus()
	send_keys(keys)
	time.sleep(wait)


def count_titled(app, title):
	return len([h for h in app.windows(visible_only=True) if h.window_text() == title])


class SessionMessage(threading.Thread):
	"""Send WM_QUERYENDSESSION or WM_ENDSESSION to ``hwnd`` from a driver thread.

	``returned_after`` is the time from the start of the call to its return in seconds,
	``ok`` the return value of SendMessageTimeoutW (0: timed out or failed) and
	``result`` the window's answer (WM_QUERYENDSESSION: 1 may end, 0 may not).
	"""

	def __init__(self, hwnd, message, wparam=0, lparam=ENDSESSION_LOGOFF, timeout_ms=10000):
		super().__init__(daemon=True)
		self.args = (hwnd, message, wparam, lparam, SMTO_NORMAL, timeout_ms)
		self.ok = None
		self.result = None
		self.returned_after = None

	def run(self):
		result = ctypes.c_size_t(0)
		start = time.time()
		self.ok = user32.SendMessageTimeoutW(*self.args, ctypes.byref(result))
		self.returned_after = round(time.time() - start, 1)
		self.result = result.value

	def state(self):
		if self.returned_after is None:
			return "not returned"
		return {"ok": self.ok, "result": self.result, "after_s": self.returned_after}


def watch_close_dialogs(app, seconds=3.0, step=0.25):
	"""The largest number of open close dialogs seen during ``seconds``."""
	most = 0
	end = time.time() + seconds
	while time.time() < end:
		most = max(most, count_titled(app, CLOSE_DIALOG))
		time.sleep(step)
	return most


def answer_close_dialogs(app, key="esc", sender=None):
	"""Press ``key`` in the topmost open close dialog (the innermost one), one dialog at a
	time, until none is left. Returns one entry per dialog: the dialogs open before the key,
	how often it was pressed, and the state of ``sender`` after it."""
	from pywinauto import Desktop

	steps = []
	end = time.time() + 40
	while time.time() < end:
		# Top-level windows come in z-order, topmost first.
		open_now = [h.handle for h in app.windows(visible_only=True) if h.window_text() == CLOSE_DIALOG]
		if not open_now:
			break
		dialog = Desktop(backend="uia").window(handle=open_now[0])
		presses = F.answer(dialog, key)
		time.sleep(0.5)
		steps.append({"open": len(open_now), "presses": presses, "call": sender.state() if sender else None})
	return steps


def exit_code(pid, timeout=10):
	"""The exit code of process ``pid`` once it has ended, or None if it is still running."""
	import psutil

	try:
		process = psutil.Process(pid)
	except psutil.NoSuchProcess:
		return "gone"
	try:
		return process.wait(timeout)
	except psutil.TimeoutExpired:
		return None


def gui_log(d):
	path = os.path.join(d, "log", "gui.log")
	if not os.path.exists(path):
		return []
	with open(path, encoding="utf-8") as stream:
		return stream.read().splitlines()
````

File: `docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/item53.py`

````python
"""Items 53, 56 and 57 (F-7, F-W9): the document name dialog and the message boxes.

Usage: python item53.py <exe> <work folder>
53: Add alpha; Add again, alpha: the "already exists" box (Enter), then the name dialog
    shown again (its buttons and name), Esc; the document list.
56: one OK box of each kind: Convert ("Conversion completed.", Esc); Help > About
    (Enter); Export All as BRL into <work folder>\\out56, where a folder named alpha.brl
    makes that document fail: the overwrite question (Alt+Y), then the summary (Enter).
57: Delete alpha: the question (Alt+N: kept), Delete again (Alt+Y: deleted); Export All
    as BRL into <work folder>\\out57, which already holds new.brl: the question (Alt+N).
Before F-7 (N-f6b): every OK box and the name dialog shown again are English (F-W9);
the Yes/No questions are the same.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f7gui as G  # noqa: E402
from f7gui import D, X, dx  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = dx.launch(EXE, d)
print("53 add alpha:", D.add(app, w, "alpha"))
G.menu(w, "#0->#3")
dialog = X.wait_window(app, w, "新增文件")
dialog.child_window(class_name="Edit").wrapper_object().set_edit_text("alpha")
X.btn(dialog, "確定", "OK").click()
print("53 box:", G.answer_box(app, "enter"))
again = X.wait_window(app, w, "新增文件")
print("53 shown again: buttons", G.buttons(again), "name", repr(G.edit_text(again)))
G.press_keys(again, "{ESC}")
print("53 after esc: windows:", G.windows(app, w), "docs:", D.docs(w))

D.set_input(w, "abc")
G.menu(w, "#1->#0", wait=0.5)
print("56 convert:", G.answer_box(app, "esc", timeout=60))
G.menu(w, "#2->#1", wait=0.5)
about = G.answer_box(app, "enter")
about["content"] = about["content"].splitlines()[0] + " ..."
print("56 about:", about)
out56 = os.path.join(d, "out56")
os.makedirs(os.path.join(out56, "alpha.brl"))
G.menu(w, "#0->#7->#1", wait=0.5)
G.path_dialog(app, w, "匯出全部文件", out56)
print("56 overwrite question:", G.answer_box(app, "alt-y"))
print("56 summary:", G.answer_box(app, "enter"))
print("56 out56:", sorted(os.listdir(out56)), "windows:", G.windows(app, w))

D.select(w, "alpha")
G.menu(w, "#0->#1", wait=0.5)
print("57 delete, no:", G.answer_box(app, "alt-n"), "docs:", D.docs(w))
D.select(w, "alpha")
G.menu(w, "#0->#1", wait=0.5)
print("57 delete, yes:", G.answer_box(app, "alt-y"), "docs:", D.docs(w))
out57 = os.path.join(d, "out57")
os.makedirs(out57)
with open(os.path.join(out57, "new.brl"), "wb") as stream:
	stream.write(b"old")
G.menu(w, "#0->#7->#1", wait=0.5)
G.path_dialog(app, w, "匯出全部文件", out57)
print("57 overwrite question:", G.answer_box(app, "alt-n"))
print("57 boxes after no:", G.answer_box(app, "enter", timeout=2))
with open(os.path.join(out57, "new.brl"), "rb") as stream:
	print("57 out57:", sorted(os.listdir(out57)), "new.brl:", stream.read())
print("close:", D.close(app, w))
dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/item54.py`

````python
"""Items 54 and 55 (F-7, F-W9): the dictionary name dialog and the dictionary editor.

Usage: python item54.py <exe> <work folder>
54: Dictionary Management: Add d1; Add again, d1: the "already exists" box (Enter), then
    the name dialog shown again (its buttons and name), Esc; the list.
55: Text Processing is opened and kept open; Dictionary Management, select d1, Edit: the
    editor's buttons; Add the entry x / 1; the editor's OK. Dictionary Management, Edit
    d1 again: the rows; Cancel. dictionary\\d1.csv. Then Text Processing's own Cancel.
    The same with the Settings dialog open instead (entry y / 2).
Before F-7 (N-f6b): English OK / Cancel in the box and the dialog shown again (F-W9); in
55 the editor's buttons are English and its OK closes without saving (the entry is lost).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f7gui as G  # noqa: E402
from f7gui import D, X, dx  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d1 = os.path.join(d, "dictionary", "d1.csv")


def press_esc(win):
	from pywinauto.keyboard import send_keys

	win.set_focus()
	send_keys("{ESC}")
	time.sleep(1)


def add_dictionary(app, w, mgr, name):
	X.btn(mgr, "新增").click()
	dialog = X.wait_window(app, w, "新增字典")
	dialog.child_window(class_name="Edit").wrapper_object().set_edit_text(name)
	X.btn(dialog, "確定", "OK").click()
	time.sleep(1.5)


def add_entry_and_ok(app, w, mgr, text, braille):
	X.mgr_select(mgr, "d1")
	X.btn(mgr, "編輯").click()
	editor = X.wait_window(app, w, G.EDITOR)
	print("55 editor buttons:", G.buttons(editor))
	X.btn(editor, "新增").click()
	entry = X.wait_window(app, w, "新增字典項目")
	fields = [c for c in entry.wrapper_object().descendants() if c.class_name() == "Edit"]
	fields[0].set_edit_text(text)
	fields[1].set_edit_text(braille)
	X.btn(entry, "確定", "OK").click()
	time.sleep(1)
	print("55 editor rows before OK:", X.editor_rows(editor))
	X.btn(editor, "確定", "OK").click()
	time.sleep(1.5)
	print("55 after OK: windows:", G.windows(app, w), "boxes:", G.answer_box(app, "enter", timeout=1))


def reopen_rows(app, w):
	mgr = G.window_titled(app, w, G.MGR) if G.MGR in X.windows(app, w) else X.open_mgr(app, w)
	editor = X.open_editor(app, w, mgr, "d1")
	rows = X.editor_rows(editor)
	X.btn(editor, "取消", "Cancel").click()
	time.sleep(1)
	return rows


def with_modeless(app, w, menu_path, title_prefix, text, braille):
	G.menu(w, menu_path)
	modeless = G.window_titled(app, w, title_prefix)
	print(f"55 [{title_prefix}] open: buttons {G.buttons(modeless)}")
	mgr = X.open_mgr(app, w)
	add_entry_and_ok(app, w, mgr, text, braille)
	print(f"55 [{title_prefix}] reopened rows:", reopen_rows(app, w))
	with open(d1, "rb") as stream:
		print(f"55 [{title_prefix}] d1.csv:", stream.read())
	print(f"55 [{title_prefix}] its own buttons now: {G.buttons(modeless)}; windows: {G.windows(app, w)}")
	X.btn(modeless, "取消", "Cancel").click()
	time.sleep(1)
	print(f"55 [{title_prefix}] after its Cancel: windows:", G.windows(app, w))


app, w = dx.launch(EXE, d)
mgr = X.open_mgr(app, w)
add_dictionary(app, w, mgr, "d1")
print("54 first add: windows:", G.windows(app, w), "rows:", X.mgr_items(mgr)[1])
add_dictionary(app, w, mgr, "d1")
print("54 box:", G.answer_box(app, "enter"))
again = X.wait_window(app, w, "新增字典")
print("54 shown again: buttons", G.buttons(again), "name", repr(G.edit_text(again)))
press_esc(again)
print("54 after esc: windows:", G.windows(app, w), "rows:", X.mgr_items(mgr)[1])
X.close_mgr(app, w, mgr)

with_modeless(app, w, "#1->#2", G.TEXT_PROCESSING, "x", "1")
with_modeless(app, w, "#1->#4", G.SETTINGS_PREFIX, "y", "2")
print("close:", D.close(app, w))
dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/item58.py`

````python
"""Items 58-60 (F-7, M-5): Windows ends the session while DotExpress is open.

Usage: python item58.py <exe> <work folder> <query|idle|end>
alpha and beta are created, the app is restarted, alpha is open. Each message goes to the
main window of this DotExpress process only, from a driver thread; Windows itself is
never asked to log off or shut down.
query (58, spec D9): type an edit; lock.py holds alpha.dep (share read); post WM_CLOSE;
    the close dialog opens. Send WM_QUERYENDSESSION (lParam ENDSESSION_LOGOFF, timeout
    10 s) and watch the close dialogs for 3 s. Then press Esc in each open close dialog,
    newest first. The app keeps running with the edit; unlock, Close, Enter (Retry): the
    app exits, and after a restart alpha holds the edit.
idle (59): no edit, no dialog; send WM_QUERYENDSESSION: the app closes by itself.
end (60): as query up to the dialog; send WM_ENDSESSION (wParam 1): wx exits at once.
Before F-7 (N-f6b), query shows two close dialogs (the nested close of M-5) and the call
returns only after the inner one is answered.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f7gui as G  # noqa: E402
from f7gui import D, F, dx  # noqa: E402

EXE, d, mode = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
app, w = F.setup_alpha_beta(EXE, d)
alpha = os.path.join(F.workspace(d), "alpha.dep")
before = F.package(alpha)
pid = app.process
holder = None
if mode in ("query", "end"):
	D.set_input(w, "alpha edited")
	holder = F.lock(alpha, "r")
	import win32con

	w.post_message(win32con.WM_CLOSE)
	dialog = F.close_dialog(w)
	print("close dialog:", F.describe(dialog) if dialog is not None else None)
if mode == "end":
	sender = G.SessionMessage(w.handle, G.WM_ENDSESSION, wparam=1)
else:
	sender = G.SessionMessage(w.handle, G.WM_QUERYENDSESSION)
sender.start()
if mode == "query":
	print("close dialogs within 3 s:", G.watch_close_dialogs(app), "call:", sender.state())
	print("esc in each close dialog:", G.answer_close_dialogs(app, sender=sender))
	sender.join(12)
	print("call:", sender.state())
	time.sleep(1)
	print("running:", app.is_process_running(), "close dialogs:", G.count_titled(app, G.CLOSE_DIALOG))
	print("input:", repr(D.get_input(w)), "title:", w.window_text())
	dialogs, outcome = F.close_and_answer(app, w, ["enter"], between={0: lambda: F.unlock(holder)})
	print("unlock, close, enter:", outcome, [dialog["title"] for dialog in dialogs])
else:
	sender.join(12)
	print("call:", sender.state())
	print("exit code:", G.exit_code(pid, 5))
	if holder is not None:
		F.unlock(holder)
print(
	"alpha members changed:", F.package(alpha)[0] != before[0],
	"text:", repr(F.member(alpha, "alpha.txt").decode("utf-8")),
	"files:", F.files(d), "tmp:", F.leftovers(d),
)
print("gui.log:", G.gui_log(d))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart:", D.docs(w), "title:", w.window_text(), "input:", repr(D.get_input(w)))
print("close:", F.close_and_answer(app, w, []))
dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/item61.py`

````python
"""Items 61-63 (F-7, F-5 review M-7): a lone surrogate in the source text.

Usage: python item61.py <exe> <work folder>
61: Add alpha. Type A U+FFFD B and convert: the braille of U+FFFD. Then paste A U+D83D B
    (f5gui.paste_text_with_lone_surrogate) and convert: the box, the braille (the same
    as for U+FFFD), and the source editor (it still holds the surrogate).
62: File > Export > HTML to <work folder>\\alpha.html: the box and the file's bytes.
63: File > Export All > HTML into the new folder <work folder>\\out63: the box and the files.
Before F-7 (N-f6b): the braille is that of the surrogate; the HTML export shows nothing,
and Export All stops at alpha without a summary.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f7gui as G  # noqa: E402
from f7gui import D, F, X, dx  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
REPLACEMENT = chr(0xFFFD)
BLANK_CELL = chr(0x2800)


def code_points(text):
	return " ".join(f"U+{ord(character):04X}" for character in text)


def convert(app, w):
	"""Convert; return the box and the braille without its trailing blank cells."""
	G.menu(w, "#1->#0", wait=0.5)
	box = G.answer_box(app, "enter", timeout=60)
	return box, w.children(class_name="Edit")[1].window_text().rstrip(BLANK_CELL)


app, w = dx.launch(EXE, d)
print("add alpha:", D.add(app, w, "alpha"))
D.set_input(w, "A" + REPLACEMENT + "B")
box, replacement_braille = convert(app, w)
print("61 U+FFFD typed: box", box, "braille", repr(replacement_braille))
F.paste_text_with_lone_surrogate(w)
print("61 pasted:", code_points(D.get_input(w)))
box, braille = convert(app, w)
print("61 surrogate: box", box)
print("61 braille", repr(braille), "same as for U+FFFD:", braille == replacement_braille)
print("61 source editor after:", code_points(D.get_input(w)))

html = os.path.join(d, "alpha.html")
G.menu(w, "#0->#6->#2", wait=0.5)
G.path_dialog(app, w, "匯出文件", html)
print("62 export html:", G.answer_box(app, "enter", timeout=5))
if os.path.exists(html):
	with open(html, "rb") as stream:
		data = stream.read()
	print("62 alpha.html:", len(data) > 0, "EF BF BD:", b"\xef\xbf\xbd" in data, "ED A0 BD:", b"\xed\xa0\xbd" in data)
else:
	print("62 alpha.html: missing")

out63 = os.path.join(d, "out63")
os.makedirs(out63)
G.menu(w, "#0->#7->#2", wait=0.5)
G.path_dialog(app, w, "匯出全部文件", out63)
print("63 export all html:", G.answer_box(app, "enter", timeout=5))
print("63 out63:", {name: os.path.getsize(os.path.join(out63, name)) > 0 for name in sorted(os.listdir(out63))})
print("windows:", G.windows(app, w), "gui.log:", G.gui_log(d))
print("close:", D.close(app, w))
dx.kill_under(d)
````

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto
cd $REPO
"$UIA" -c "import pywinauto, psutil; print(pywinauto.__version__, psutil.__version__)"
"$UIA" -m py_compile $H/f7gui.py $H/item53.py $H/item54.py $H/item58.py $H/item61.py && echo "scripts compile"
rm -rf $H/__pycache__
git status --short -- client docs scripts
```

Expected: `0.6.9 7.2.2` (or a later psutil), `scripts compile`, and `?? docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/`. `UIA` is a pywinauto venv outside the repo (HANDOFF section 8: `py -3.13 -m venv <scratchpad>\uia`, then `pip install pywinauto==0.6.9 psutil`); if its `Scripts\python.exe` is missing, run `py -3.13 -m venv --upgrade <venv>`.

- [ ] **Step 2: Run the items on the pre-F-7 build** (Git Bash, from the repository root). Item 58 (`query`) is the D9 check; item 54 includes item 55 (the lost edits).

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto
EXE=/d/dxtest/N-f6b/DotExpress.exe
export PYTHONIOENCODING=utf-8
cd $REPO
"$UIA" $H/item58.py $EXE /d/dxtest/auto58-f6b-f7 query > /d/dxtest/auto58-f6b-f7.log 2>&1
"$UIA" $H/item54.py $EXE /d/dxtest/auto54-f6b-f7 > /d/dxtest/auto54-f6b-f7.log 2>&1
"$UIA" $H/item53.py $EXE /d/dxtest/auto53-f6b-f7 > /d/dxtest/auto53-f6b-f7.log 2>&1
"$UIA" $H/item61.py $EXE /d/dxtest/auto61-f6b-f7 > /d/dxtest/auto61-f6b-f7.log 2>&1
```

- [ ] **Step 3: Read the logs against the "Before" column** of Task 8 Step 3's table. These lines decide whether Task 6 goes ahead (the dry run printed them on the same build, Spec Corrections 13):

  - `auto58-f6b-f7.log`: `close dialogs within 3 s: 2 call: not returned`, then `esc in each close dialog:` with two entries (`'open': 2`, then `'open': 1`), the call returning with `'ok': 1, 'result': 0` a few seconds after the start (3.6 s in the dry run: when the inner dialog was answered); `running: True close dialogs: 0`; `input: 'alpha edited'`; `unlock, close, enter: exited ['無法儲存文件']`; `alpha members changed: True text: 'alpha edited'`, `tmp: []`; `gui.log: []`.
  - `auto54-f6b-f7.log`: `55 editor buttons: ['新增', '編輯', '刪除', 'OK', 'Cancel']`, `55 editor rows before OK: [['x', '1', '一般']]`, `55 after OK: windows: ['文字處理'] boxes: None`, `55 [文字處理] reopened rows: []`, `55 [文字處理] d1.csv: b'text,braille,type\r\n'`; the same for `DotExpress 設定` with `y` / `2` (`reopened rows: []`, the header only).

  **If item 58 shows only one close dialog, or the call returns before the dialogs are answered, stop before Task 6 and report to the orchestrator** (spec D9: the plain-wx probe and the planner's run predict the nested dialog). Any other deviation is reported too, not explained away. Keep the four logs for Task 8's `auto-results.md`.

### Task 6: Veto a close that arrives while another close is asking (D7)

- [ ] **Step 1: Red: E1-E4** (`client/tests/test_gui_document_flows.py`, 4 spaces). The fake `MessageDialog` of `DocumentWorkspaceFlowsCharacterizationTest` runs a one-shot hook from `dialog_hooks` while it is "open" (between recording itself and answering); the hooks send the inner close event. E3 passes before the change (there is no flag yet to reset) and guards the `finally`.

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.events: list = []
        self.answers: list = []
        self.dialog_answers: list = []
        self.names: list = []
        self.delete_invalid = False
        self.import_paths: list[str] = []
```

```python
        self.events: list = []
        self.answers: list = []
        self.dialog_answers: list = []
        # One-shot callbacks, each run by one MessageDialog while it is open (F-7, M-5).
        self.dialog_hooks: list = []
        self.names: list = []
        self.delete_invalid = False
        self.import_paths: list[str] = []
```

Edit: `client/tests/test_gui_document_flows.py`

```python

            def ShowModal(self):
                test.events.append(("MessageDialog", *self.shown))
                return test.dialog_answers.pop(0) if test.dialog_answers else gui.wx.ID_CANCEL

        return FakeMessageDialog
```

```python

            def ShowModal(self):
                test.events.append(("MessageDialog", *self.shown))
                hook = test.dialog_hooks.pop(0) if test.dialog_hooks else None
                if hook is not None:
                    hook()
                return test.dialog_answers.pop(0) if test.dialog_answers else gui.wx.ID_CANCEL

        return FakeMessageDialog
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        event.Skip.assert_called_once_with()
        self.assertEqual(self._disk(), before)
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    def test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes(self) -> None:
        # D8: Windows is ending the session; nobody could answer a dialog.
```

```python
        event.Skip.assert_called_once_with()
        self.assertEqual(self._disk(), before)
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    # --- a close that arrives while the close dialog is open (F-7, M-5) ------

    def test_close_reentered_while_the_close_dialog_is_open_is_vetoed(self) -> None:
        # Windows sends WM_QUERYENDSESSION again while the close dialog's modal loop runs, and
        # wx delivers another close event to the frame. The open dialog decides.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()
        outer = self._vetoable_close()
        inner = self._vetoable_close()
        self.dialog_hooks = [lambda: frame._on_close(inner)]
        self.dialog_answers = [gui.wx.ID_CANCEL]

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace:
            frame._on_close(outer)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        self.assertEqual(replace.call_count, 1)
        inner.Veto.assert_called_once_with()
        inner.Skip.assert_not_called()
        outer.Veto.assert_called_once_with()
        outer.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
        self.assertEqual(frame.input_txt.value, "a edited")
        self.assertEqual(self._disk(), before)

    def test_close_reentered_that_cannot_be_vetoed_closes_once(self) -> None:
        # Defensive: wx 3.2 ends a session without a close event, and DotExpress never forces a
        # close. A nested close that cannot be vetoed runs F-5 D8 once, and the outer close
        # stops when its dialog returns, whatever the answer.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        viewer = Mock()
        frame._dual_view_frame = viewer
        before = self._disk()
        outer = self._vetoable_close()
        inner = Mock()
        inner.CanVeto.return_value = False
        self.dialog_hooks = [lambda: frame._on_close(inner)]
        self.dialog_answers = [gui.wx.ID_YES]

        with (
            patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace,
            self.assertLogs(gui.logger, level="ERROR") as logs,
        ):
            frame._on_close(outer)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        self.assertEqual(replace.call_count, 2)
        self.assertEqual([record.getMessage() for record in logs.records], ["Failed to save the open document while closing"])
        frame.close_converting_dialog.assert_called_once_with()
        viewer.Destroy.assert_called_once_with()
        inner.Veto.assert_not_called()
        inner.Skip.assert_called_once_with()
        outer.Veto.assert_not_called()
        outer.Skip.assert_not_called()
        self.assertEqual(self._disk(), before)

    def test_close_works_again_after_a_vetoed_close(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        first = self._vetoable_close()
        second = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_CANCEL]

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")):
            frame._on_close(first)
        frame._on_close(second)

        first.Veto.assert_called_once_with()
        second.Veto.assert_not_called()
        second.Skip.assert_called_once_with()
        self.assertEqual(self._package("alpha"), Document("alpha", "a edited", "1"))

    def test_close_flag_is_reset_when_the_close_raises(self) -> None:
        frame = self._start_with_alpha_and_beta()
        event = self._vetoable_close()

        with (
            patch.object(frame, "_save_open_document_before_close", side_effect=RuntimeError("injected")),
            self.assertRaisesRegex(RuntimeError, "injected"),
        ):
            frame._on_close(event)

        # The wx stub answers every missing attribute, so read the frame's own attributes.
        self.assertIs(vars(frame).get("_closing"), False)

    def test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes(self) -> None:
        # D8: Windows is ending the session; nobody could answer a dialog.
```

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (today the nested close saves again and shows a second dialog; the stub answers any missing attribute, so E4 reads the frame's own attributes):

```text
FAIL: test_close_flag_is_reset_when_the_close_raises (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_flag_is_reset_when_the
AssertionError: None is not False
FAIL: test_close_reentered_that_cannot_be_vetoed_closes_once (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_reentered_that
AssertionError: Lists differ: ['MessageDialog', 'MessageDialog'] != ['MessageDialog']
FAIL: test_close_reentered_while_the_close_dialog_is_open_is_vetoed (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_reenter
Ran 191 tests
FAILED (failures=3)
```

- [ ] **Step 2: The re-entry guard** (`client/gui.py`, tabs; D7 verbatim, with the check after the dialog in `_save_open_document_before_close`).

Edit: `client/gui.py`

```python


class BrailleFrame(wx.Frame):
	def __init__(
		self,
		*args,
```

```python


class BrailleFrame(wx.Frame):
	# Class attributes, so that frames built without __init__ (tests) have them too (F-7, M-5).
	_closing = False
	_close_finished = False

	def __init__(
		self,
		*args,
```

Edit: `client/gui.py`

```python
					return True
				self._log_unexpected_save_error(error)
				answer = self._ask_after_close_save_failure(error)
				if answer == wx.ID_YES:
					continue
				return answer == wx.ID_NO
```

```python
					return True
				self._log_unexpected_save_error(error)
				answer = self._ask_after_close_save_failure(error)
				if self._close_finished:
					# A nested close that could not be vetoed closed the frame meanwhile (F-7, M-5).
					return True
				if answer == wx.ID_YES:
					continue
				return answer == wx.ID_NO
```

Edit: `client/gui.py`

```python
		self._conversion_presenter.convert()

	def _on_close(self, evt: wx.CloseEvent):
		if self._conversion_presenter.is_running() and evt.CanVeto():
			evt.Veto()
			return
		if not self._save_open_document_before_close(evt.CanVeto()):
			evt.Veto()
			return
		self.close_converting_dialog()
		if self._dual_view_frame is not None:
			viewer = self._dual_view_frame
```

```python
		self._conversion_presenter.convert()

	def _on_close(self, evt: wx.CloseEvent):
		if self._closing:
			self._on_close_reentered(evt)
			return
		self._closing = True
		try:
			self._close(evt)
		finally:
			self._closing = False

	def _close(self, evt: wx.CloseEvent) -> None:
		if self._conversion_presenter.is_running() and evt.CanVeto():
			evt.Veto()
			return
		may_close = self._save_open_document_before_close(evt.CanVeto())
		if self._close_finished:
			# A nested close that could not be vetoed already closed the frame (M-5).
			return
		if not may_close:
			evt.Veto()
			return
		self._finish_close(evt)

	def _on_close_reentered(self, evt: wx.CloseEvent) -> None:
		"""A close event while another close is still asking (F-7, M-5).

		Windows sends WM_QUERYENDSESSION again while the close dialog's modal loop runs.
		A close that can be vetoed is vetoed: the open dialog decides. One that cannot
		follows F-5 D8: one save attempt, a logged failure, and the frame closes.
		"""
		if evt.CanVeto():
			evt.Veto()
			return
		self._save_open_document_before_close(False)
		self._finish_close(evt)

	def _finish_close(self, evt: wx.CloseEvent) -> None:
		self._close_finished = True
		self.close_converting_dialog()
		if self._dual_view_frame is not None:
			viewer = self._dual_view_frame
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(close_reentered|close_works_again|close_flag_is_reset|close_asks_presenter_before_saving|close_that_cannot_be_vetoed_logs)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (the F-5 close tests and `test_close_asks_presenter_before_saving` are unchanged and pass):

```text
test_close_flag_is_reset_when_the_close_raises ok
test_close_reentered_that_cannot_be_vetoed_closes_once ok
test_close_reentered_while_the_close_dialog_is_open_is_vetoed ok
test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes ok
test_close_works_again_after_a_vetoed_close ok
test_close_asks_presenter_before_saving ok
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1365 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: veto a close that arrives while another close is asking (F-7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/gui.py                           | 40 +++++++++++++-
 client/tests/test_gui_document_flows.py | 92 +++++++++++++++++++++++++++++++++
 2 files changed, 131 insertions(+), 1 deletion(-)
652dabacc5f65dec492a86672309e9c4da5af8cb
```

### Task 7: Verification (no commit)

`BASE` is the F-6 head `fb7aff9`.

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = 1337 + 28; the error is F-W6):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1365 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 2: Criterion 2, focused modules; the 28 new tests ran and passed.**

```bash
$PY -m unittest tests.test_message_box tests.test_wx_call_sites tests.test_dialog_display tests.test_dialog_validation tests.test_converting_dialog tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_settings_dialogs tests.test_gui_document_flows tests.test_export_coordinator tests.test_wx_stub 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_message_box tests.test_wx_call_sites tests.test_dialog_display tests.test_dialog_validation tests.test_dictionary_entries_dialog tests.test_gui_document_flows tests.test_export_coordinator -v 2>&1 | grep -cE "^test_(localize_ignores_buttons_of_other_windows|file_issues_dialog_localizes_its_ok_button|entries_dialog_binds_ok_to_its_own_button|no_production_code_searches_windows_by_id_globally|scan_reads_the_production_modules|ok_box_sets|ok_cancel_box|yes_no_box_keeps|unexpected_result_maps|parent_can_be|a_label_the_platform|no_production_module_calls|message_dialogs_are_the_helper|invalid_entry_shows_the_message_on_the_dialog|about_box_uses_the_helper|source_text_for_conversion_replaces|save_reads_both_editors|manual_conversion_stores_replaced_text|importing_binds_no_log_file|single_export_error_that_is_not|single_export_os_error_is_not_logged|html_export_with_a_lone_surrogate|pending_export_failure_after|export_all_goes_on_after|close_reentered|close_works_again|close_flag_is_reset)[a-z0-9_]* .* ok$"
```

Expected:

```text
Ran 471 tests
OK
28
```

- [ ] **Step 3: Shuffled module order, six seeds** (one process each, about two minutes).

```bash
for s in 0 1 2 3 4 5; do $PY $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
      6 ran=1365 failures=0 errors=1 skipped=7 ['test_case_only_rename_still_renames']
```

- [ ] **Step 4: Criteria 3 and 4, call sites and catalogs.** No `wx.MessageBox` and no `FindWindowById` in production code, two `wx.MessageDialog` calls (the helper and F-5's close dialog); the catalogs are those of `fb7aff9`; a fresh template differs only in `POT-Creation-Date` and the `#:` reference lines (Spec Corrections 9); 364 msgids, all translated.

```bash
grep -rn --include=*.py 'wx.MessageBox(\|FindWindowById' dialog.py gui.py settings ui documents dictionaries; echo "grep exit $?"
grep -rn --include=*.py 'wx.MessageDialog(' dialog.py gui.py settings ui documents dictionaries | sed 's/:[0-9]*:.*//'
git -C $REPO diff --quiet fb7aff9 -- client/locales && echo "catalogs unchanged"
(cd $REPO && cmd //c "scripts\\generate-pot.bat $(cygpath -w $T/second.pot)"); echo "generate-pot exit $?"
diff --strip-trailing-cr <(grep -v '^"POT-Creation-Date: \|^#: ' locales/dotexpress.pot) <(grep -v '^"POT-Creation-Date: \|^#: ' $T/second.pot) && echo "fresh template identical apart from POT-Creation-Date and #: lines"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (`grep` finds nothing and exits 1):

```text
grep exit 1
gui.py
ui/message_box.py
catalogs unchanged
generate-pot exit 0
fresh template identical apart from POT-Creation-Date and #: lines
364 translated messages.
source msgids: 364 sha256 7b53ff311c9e446767b0884bfc03148afe030ca7e15899d6ee6919e77c664ea7
```

- [ ] **Step 5: Criteria 5-7, fixtures, untouched modules, touched files, application data.**

```bash
BASE=fb7aff9
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/conversion client/dictionaries client/documents/workspace.py client/documents/workspace_service.py client/documents/formats.py client/ui/conversion_presenter.py client/dual_view client/braille client/locales client/tests/test_wx_stub.py && echo "conversion, dictionaries, documents layer, presenter, dual view, braille, catalogs and the stub tests unchanged"
git -C $REPO diff --stat=200 $BASE -- client
for f in dictionary workspace log config.json; do test -e $REPO/client/$f && echo "unexpected: client/$f"; done; echo "no application data in the checkout"
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) | diff - $T/app-data.sha256 && echo "application data unchanged"
git -C $REPO status --short -- client scripts
```

Expected (`status` prints nothing):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
conversion, dictionaries, documents layer, presenter, dual view, braille, catalogs and the stub tests unchanged
 client/dialog.py                                  |  26 ++++++++++++--------
 client/documents/export_coordinator.py            |  21 ++++++++++++++--
 client/gui.py                                     |  82 +++++++++++++++++++++++++++++++++++++++++++++-----------------
 client/settings/dialogs.py                        |   5 ++--
 client/tests/test_converting_dialog.py            |   2 +-
 client/tests/test_dialog_display.py               |  48 +++++++++++++++++++++++++++++++++----
 client/tests/test_dialog_validation.py            |  27 +++++++++++++++++++--
 client/tests/test_dictionary_entries_dialog.py    |  32 +++++++++++++++++++++++--
 client/tests/test_dictionary_management_dialog.py |   6 ++---
 client/tests/test_export_coordinator.py           | 166 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 client/tests/test_gui_document_flows.py           | 187 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----------------
 client/tests/test_message_box.py                  | 166 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_settings_dialogs.py             |  13 ++++++----
 client/tests/test_wx_call_sites.py                |  89 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/wx_stub.py                           |  20 +++++++++++++++-
 client/ui/message_box.py                          |  29 ++++++++++++++++++++++
 16 files changed, 842 insertions(+), 77 deletions(-)
no application data in the checkout
application data unchanged
```

- [ ] **Step 6: Criterion 8, mutation check** (26 mutants: the spec's fourteen items as 18 mutants (both lookups, a site reverted in each of `dialog.py`, `gui.py` and `settings/dialogs.py`, the save read of text and of braille), and eight more: the file-issues dialog, the OK/Cancel labels, the About box, an unexpected error not logged, the logger bound at import, the re-entry without its save, `_close` ignoring a finished close, and the finish not recorded; about a minute). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f7_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
localize-searches-every-window: 6 caught: test_dialog_display.test_localize_ignores_buttons_of_other_windows, test_dialog_display.test_localizes_buttons_from_standard_button_sizer, test_dialog_display.test_localizes_close_button, test_dialog_display.test_localizes_standard_dialog_buttons, and 2 more
editor-binds-ok-of-any-window: 2 caught: test_dictionary_entries_dialog.test_entries_dialog_binds_ok_to_its_own_button, test_wx_call_sites.test_no_production_code_searches_windows_by_id_globally
file-issues-ok-not-localized: 1 caught: test_dialog_display.test_file_issues_dialog_localizes_its_ok_button
helper-without-the-ok-label: 2 caught: test_message_box.test_a_label_the_platform_refuses_still_shows_the_box, test_message_box.test_ok_box_sets_the_translated_ok_label
helper-labels-yes-no-too: 1 caught: test_message_box.test_yes_no_box_keeps_the_system_labels
helper-ok-cancel-sets-only-ok: 1 caught: test_message_box.test_ok_cancel_box_sets_both_labels
helper-returns-the-raw-id: 5 caught: test_message_box.test_a_label_the_platform_refuses_still_shows_the_box, test_message_box.test_ok_box_sets_the_translated_ok_label, test_message_box.test_ok_cancel_box_sets_both_labels, test_message_box.test_unexpected_result_maps_to_cancel, and 1 more
dialog-site-back-to-wx-message-box: 2 caught: test_dictionary_management_dialog.test_show_error_uses_error_box_on_dialog, test_wx_call_sites.test_no_production_module_calls_wx_message_box
gui-site-back-to-wx-message-box: 4 caught: test_gui_document_flows.test_export_all_mixed_documents_turn_by_turn, test_gui_document_flows.test_export_all_without_default_table_collects_failures_turn_by_turn, test_gui_document_flows.test_show_warning_uses_the_warning_icon, test_wx_call_sites.test_no_production_module_calls_wx_message_box
settings-site-back-to-wx-message-box: 2 caught: test_settings_dialogs.test_apply_failure_keeps_dialog_open_and_focuses_editor, test_wx_call_sites.test_no_production_module_calls_wx_message_box
about-box-back-to-wx-message-box: 2 caught: test_gui_document_flows.test_about_box_uses_the_helper, test_wx_call_sites.test_no_production_module_calls_wx_message_box
source-text-without-the-replacement: 2 caught: test_gui_document_flows.test_manual_conversion_stores_replaced_text, test_gui_document_flows.test_source_text_for_conversion_replaces_lone_surrogates_without_touching_the_editor
saved-text-without-the-replacement: 1 caught: test_gui_document_flows.test_save_reads_both_editors_through_the_replacement
saved-braille-without-the-replacement: 1 caught: test_gui_document_flows.test_save_reads_both_editors_through_the_replacement
single-export-catches-only-os-error: 3 caught: test_export_coordinator.test_html_export_with_a_lone_surrogate_in_the_dual_view_reports_failure, test_export_coordinator.test_pending_export_failure_after_conversion_is_reported, test_export_coordinator.test_single_export_error_that_is_not_an_os_error_shows_the_failure_message
batch-catches-only-os-error: 2 caught: test_export_coordinator.test_export_all_goes_on_after_an_error_that_is_not_an_os_error, test_export_coordinator.test_export_all_writer_value_error_is_listed_and_the_chain_goes_on
os-error-logged-too: 1 caught: test_export_coordinator.test_single_export_os_error_is_not_logged
unexpected-export-error-not-logged: 5 caught: test_export_coordinator.test_export_all_goes_on_after_an_error_that_is_not_an_os_error, test_export_coordinator.test_export_all_writer_value_error_is_listed_and_the_chain_goes_on, test_export_coordinator.test_html_export_with_a_lone_surrogate_in_the_dual_view_reports_failure, test_export_coordinator.test_pending_export_failure_after_conversion_is_reported, and 1 more
export-logger-bound-at-import: 1 caught: test_export_coordinator.test_importing_binds_no_log_file
no-reentry-guard: 1 caught: test_gui_document_flows.test_close_reentered_while_the_close_dialog_is_open_is_vetoed
reentry-skips-instead-of-vetoing: 1 caught: test_gui_document_flows.test_close_reentered_while_the_close_dialog_is_open_is_vetoed
reentry-without-the-save: 1 caught: test_gui_document_flows.test_close_reentered_that_cannot_be_vetoed_closes_once
closing-not-reset: 3 caught: test_gui_document_flows.test_close_asks_presenter_before_saving, test_gui_document_flows.test_close_flag_is_reset_when_the_close_raises, test_gui_document_flows.test_close_works_again_after_a_vetoed_close
outer-loop-ignores-a-finished-close: 1 caught: test_gui_document_flows.test_close_reentered_that_cannot_be_vetoed_closes_once
outer-close-ignores-a-finished-close: 1 caught: test_gui_document_flows.test_close_reentered_that_cannot_be_vetoed_closes_once
finish-close-not-recorded: 1 caught: test_gui_document_flows.test_close_reentered_that_cannot_be_vetoed_closes_once
exit 0
```

### Task 8: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay. The dry run built the same code in a scratch clone with Step 1's command and ran Step 2's scripts against it; the table of Step 3 is that output (see Dry Run). Run everything from the repository root, one item at a time, with nothing else driving the desktop. Never touch `D:\dxtest\N`, `B`, `N-p25`, `N-f3`, `N-f4*`, `N-f5*`, `N-f6*` or the existing `D:\dxtest\auto*` folders (Task 5's `*-f6b-f7` folders included); every run of this task uses a new folder whose name ends in `-f7`. Only processes whose exe lies under that folder are ended (`dx.kill_under`); `lock.py` is ended with `taskkill /T`. The user may have DotExpress open: never end any other process. The session messages go only to the main window of the DotExpress process under test: never call `ExitWindowsEx`, `InitiateSystemShutdownEx`, `shutdown.exe` or `logoff`.

- [ ] **Step 1: Build** (PowerShell). The main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`; the build runs in the worktree.

```powershell
Set-Location D:\workspace\DotExpress-f7
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f7-build.log 2>&1"
if (Select-String -Path $env:TEMP\f7-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "dialog.py", "ui\\message_box.py", "settings\\dialogs.py", "documents\\export_coordinator.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress-f7\\client\\$m" -Quiet) { "$m bundled from the checkout" } }
if (Select-String -Path client\build\DotExpress\Analysis-00.toc -SimpleMatch "DotExpress-f7\\client\\gui.py" -Quiet) { "gui.py analyzed from the checkout" }
New-Item -ItemType Directory -Force D:\dxtest\N-f7 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f7\DotExpress.exe
(Get-Item D:\dxtest\N-f7\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f7\DotExpress.exe).Hash
git status --short -- client scripts
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f7-build.log`), the four `bundled from the checkout` lines (the three in subfolders print with their doubled backslash), `gui.py analyzed from the checkout`, a size near 48.75 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored).

- [ ] **Step 2: Items 53-64** (Git Bash, from the repository root). The scripts are Task 5's. Each item makes a new work folder (`dx.launch` deletes it first, after ending any process under it); 58-60 and 64 first create alpha and beta and restart, as F-5's scripts do. Read each log against the table before the next item.

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto
H5=docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto
EXE=/d/dxtest/N-f7/DotExpress.exe
export PYTHONIOENCODING=utf-8
cd $REPO
"$UIA" $H/item53.py $EXE /d/dxtest/auto53-f7 > /d/dxtest/auto53-f7.log 2>&1
"$UIA" $H/item54.py $EXE /d/dxtest/auto54-f7 > /d/dxtest/auto54-f7.log 2>&1
"$UIA" $H/item58.py $EXE /d/dxtest/auto58-f7 query > /d/dxtest/auto58-f7.log 2>&1
"$UIA" $H/item58.py $EXE /d/dxtest/auto59-f7 idle > /d/dxtest/auto59-f7.log 2>&1
"$UIA" $H/item58.py $EXE /d/dxtest/auto60-f7 end > /d/dxtest/auto60-f7.log 2>&1
"$UIA" $H/item61.py $EXE /d/dxtest/auto61-f7 > /d/dxtest/auto61-f7.log 2>&1
"$UIA" $H5/item38.py $EXE /d/dxtest/auto64a-f7 38 > /d/dxtest/auto64a-f7.log 2>&1
"$UIA" $H5/item38.py $EXE /d/dxtest/auto64b-f7 39 > /d/dxtest/auto64b-f7.log 2>&1
```

- [ ] **Step 3: Expected results.** Every log ends with `close: exited` (item58.py and item38.py: `close: ([], 'exited')`). `<box X>` stands for `{'title': ..., 'main': None, 'content': X, 'buttons': ['確定'], 'focus': '確定', 'presses': 1}` with the title given; `<question X, focus F>` for `{'title': ..., 'main': None, 'content': X, 'buttons': ['是(Y)', '否(N)'], 'focus': F, 'presses': 1}`; `<close dialog>` for `{'title': '無法儲存文件', 'main': "儲存文件失敗：[WinError 5] 存取被拒。: '...\\.alpha.dep.<random>.tmp' -> '...\\alpha.dep'", 'content': '上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。', 'buttons': ['重試(R)', '不儲存就關閉(W)', '取消'], 'focus': '重試(R)'}`. Paths appear with doubled backslashes, as Python's repr prints them. The "Before" column is Task 5's run on N-f6b (items 59, 60 and 64 were not run there: the spec expects them identical).

| # | Expected after F-7 (N-f7) | Before (N-f6b, Task 5) |
| --- | --- | --- |
| 53 | `53 add alpha: ('新增文件', [], [], [])`; `53 box: <box '文件「alpha」已存在。'>` (title `錯誤`); `53 shown again: buttons ['確定', '取消'] name 'alpha'`; `53 after esc: windows: [] docs: ['alpha', 'new']` | the box has `'buttons': ['OK'], 'focus': 'OK'`; `53 shown again: buttons ['OK', 'Cancel'] name 'alpha'` (F-W9) |
| 54 | `54 first add: windows: ['字典管理'] rows: [['d1', '0'], ['default', '0']]`; `54 box: <box '字典「d1」已存在。'>` (title `錯誤`); `54 shown again: buttons ['確定', '取消'] name 'd1'`; `54 after esc: windows: ['字典管理'] rows: [['d1', '0'], ['default', '0']]` | `['OK']` in the box; `54 shown again: buttons ['OK', 'Cancel'] name 'd1'` |
| 55 | `55 [文字處理] open: buttons ['確定', '取消', '套用']`; `55 editor buttons: ['新增', '編輯', '刪除', '確定', '取消']`; `55 editor rows before OK: [['x', '1', '一般']]`; `55 after OK: windows: ['文字處理'] boxes: None`; `55 [文字處理] reopened rows: [['x', '1', '一般']]`; `55 [文字處理] d1.csv: b'text,braille,type\r\nx,1,General\r\n'`; `55 [文字處理] its own buttons now: ['確定', '取消', '套用']; windows: ['文字處理']`; `55 [文字處理] after its Cancel: windows: []`. Then the same with `[DotExpress 設定]`: the editor's buttons translated, `55 editor rows before OK: [['x', '1', '一般'], ['y', '2', '一般']]`, `55 after OK: windows: ['DotExpress 設定：轉譯'] boxes: None`, `reopened rows: [['x', '1', '一般'], ['y', '2', '一般']]`, `d1.csv: b'text,braille,type\r\nx,1,General\r\ny,2,General\r\n'`, its Cancel closes it | `55 editor buttons: ['新增', '編輯', '刪除', 'OK', 'Cancel']`; OK closes the editor the same way, but `55 [文字處理] reopened rows: []` and `d1.csv: b'text,braille,type\r\n'` (the entry is lost: the newly found defect); with Settings `55 editor rows before OK: [['y', '2', '一般']]`, `reopened rows: []`, the header only |
| 56 | `56 convert: <box '轉換完成。'>` (title `資訊`, closed with Esc); `56 about: {'title': '關於 DotExpress', 'main': None, 'content': 'DotExpress (DotExpress) ...', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}`; `56 overwrite question: <question '目的資料夾中已有一個或多個檔案會被覆蓋。要全部覆蓋嗎？', focus '是(Y)'>` (title `確認覆蓋`); `56 summary: {'title': 'Export Complete with Errors', 'main': None, 'content': "Exported documents: 1\nFailed documents: 1\n\nalpha: [Errno 13] Permission denied: '...\\out56\\alpha.brl'", 'buttons': ['確定'], 'focus': '確定', 'presses': 1}` (title and text untranslated: P1-4 defect 4, unchanged); `56 out56: ['alpha.brl', 'new.brl'] windows: []` | every OK box has `'buttons': ['OK'], 'focus': 'OK'`; the question is the same |
| 57 | `57 delete, no: <question '要刪除文件「alpha」嗎？', focus '否(N)'> docs: ['alpha', 'new']` (title `確認刪除文件`); `57 delete, yes:` the same box, `docs: ['new']`; `57 overwrite question: <question ..., focus '是(Y)'>` as in 56; `57 boxes after no: None`; `57 out57: ['new.brl'] new.brl: b'old'` | identical |
| 58 | `close dialog: <close dialog>`; `close dialogs within 3 s: 1 call: {'ok': 1, 'result': 0, 'after_s': 0.0}`; `esc in each close dialog: [{'open': 1, 'presses': 1, 'call': {'ok': 1, 'result': 0, 'after_s': 0.0}}]`; `call:` the same; `running: True close dialogs: 0`; `input: 'alpha edited' title: alpha - DotExpress`; `unlock, close, enter: exited ['無法儲存文件']`; `alpha members changed: True text: 'alpha edited' files: ['alpha.dep', 'beta.dep', 'new.dep'] tmp: []`; `gui.log: []`; `after restart: ['alpha', 'beta', 'new'] title: alpha - DotExpress input: 'alpha edited'` | `close dialogs within 3 s: 2 call: not returned`; `esc in each close dialog:` two entries (`'open': 2`, then `'open': 1`), the call `{'ok': 1, 'result': 0, 'after_s': ...}` a few seconds after it started (3.6 and 4.2 in the dry runs: when the inner dialog was answered); the rest as after F-7 (M-5) |
| 59 | no `close dialog` line; `call: {'ok': 1, 'result': 1, 'after_s': 0.0}`; `exit code: 0`; `alpha members changed: False text: 'alpha body' files: ['alpha.dep', 'beta.dep', 'new.dep'] tmp: []`; `gui.log: []`; `after restart: ... input: 'alpha body'` | not run (identical, spec) |
| 60 | `close dialog: <close dialog>`; `call: {'ok': 1, 'result': 0, 'after_s': 0.0}`; `exit code: 0`; `alpha members changed: False text: 'alpha body' files: ['alpha.dep', 'beta.dep', 'new.dep'] tmp: []` (the last good save); `gui.log: []`; `after restart: ... input: 'alpha body'` | not run (identical: wx exits without a close event) |
| 61 | `add alpha: ('新增文件', [], [], [])`; `61 U+FFFD typed: box <box '轉換完成。'> braille '⠠⠁⠄⡳⠭⠋⠋⠋⠙⠄⠠⠃'` (title `資訊`); `61 pasted: U+0041 U+D83D U+0042`; `61 surrogate: box <box '轉換完成。'>`; `61 braille '⠠⠁⠄⡳⠭⠋⠋⠋⠙⠄⠠⠃' same as for U+FFFD: True`; `61 source editor after: U+0041 U+D83D U+0042` | boxes with `['OK']`; `61 braille '⠠⠁⠄⡳⠭⠙⠦⠒⠙⠄⠠⠃' same as for U+FFFD: False` (the escape of the surrogate) |
| 62 | `62 export html: <box '文件已成功匯出。'>` (title `匯出完成`); `62 alpha.html: True EF BF BD: True ED A0 BD: False` | `62 export html: None` (no message); `62 alpha.html: False EF BF BD: False ED A0 BD: False` (an empty file is left) |
| 63 | `63 export all html: <box 'All documents were exported successfully.'>` (title `匯出完成`; the text is not a msgid, P1-4 defect 4); `63 out63: {'alpha.html': True, 'new.html': True}`; `windows: [] gui.log: []` | `63 export all html: None`; `63 out63: {'alpha.html': False}` (the batch stops at alpha without a summary) |
| 64 | `auto64a-f7.log` (38): as F-5's item 38 (`2026-10-10-01-f5-save-failure-handling/auto-results.md`), with `'確定'` instead of `'OK'` in the Ctrl+Tab error box; three close dialogs, each `presses: 1`; `close, enter while locked, unlock, enter: exited`; `alpha members changed: True text: 'alpha edited'`, `tmp: []`. `auto64b-f7.log` (39): as F-5's 39 with `'確定'`; `close, alt-w: exited`; `alpha members changed: False text: 'alpha body'`, `tmp: []` | F-5's results (`'OK'` in the Ctrl+Tab box) |

The `focus` of a `close dialog` line is read from the system's focused element half a second after the dialog is brought forward; a notification of another program can show up there instead of `重試(R)` (it did once in the dry run, as in F-5's smoke test). That is a tool artifact, not a result; note it and go on.

- [ ] **Step 4: Record and commit the results.** Write `docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto-results.md` in the style of `2026-10-10-03-f6-unreadable-dictionaries/auto-results.md` (zh-TW): the build (PyInstaller version, `Build complete!`, the bundled modules, size, sha256), the D9 run of Task 5 on N-f6b (58 and 55, with the call timing), then one row per item (53-64) with ✔/△/✘ and the observed boxes (title, content, buttons, focus, presses), dialogs, rows, files and log lines, and the "Before" observations of Task 5. Any deviation from the table above is reported to the orchestrator before the commit, not explained away; a re-run after a GUI timing problem (for example the foreground taken by another program) is recorded with the first attempt's log name. End the file with a short section **「仍需人工（使用者）」** for item 65, worded for the user (do not mark it done):

  > 65（NVDA）：請在 NVDA 執行中檢查 F-7 的按鈕標籤。把 `D:\dxtest\N-f7\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual65-f7\` 執行。(a) 按「檔案 → 新增」建立文件 `alpha`，再按一次「檔案 → 新增」輸入 `alpha` 按 Enter：NVDA 應讀出「錯誤」對話框、內容「文件「alpha」已存在。」與按鈕「確定」；按 Enter 後重新出現的「新增文件」對話框，Tab 到按鈕時應讀出「確定」「取消」（不是 OK、Cancel）。(b) 按「說明 → 關於」：關於對話框的按鈕應讀出「確定」。(c) 在「轉譯 → 文字處理」開著的情況下，開「轉譯 → 字典管理...」新增字典 `d1`，選 `d1` 按「編輯」：編輯器的按鈕應讀出「確定」「取消」；新增一筆後按「確定」，再開一次編輯器，那一筆應該還在。請記錄 NVDA 讀出的內容；如果哪裡仍讀出英文 OK／Cancel，或 (c) 的那一筆不見了，請告訴我們。

```bash
cd $REPO
git add docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto-results.md docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/f7gui.py docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/item53.py docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/item54.py docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/item58.py docs/superpowers/history/2026-10-10-04-f7-dialog-buttons-surrogates-close/auto/item61.py
git diff --cached --stat
git commit -q -m "docs: record the F-7 packaged-build GUI checks (F-7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short -- client docs scripts
git rev-parse HEAD:client
```

Expected: the six files in the `--stat`, no `status` output, and the Task 6 tree id `652dabacc5f65dec492a86672309e9c4da5af8cb` (the commit touches no file under `client/`). Do not merge `main` or push; the orchestrator decides.
