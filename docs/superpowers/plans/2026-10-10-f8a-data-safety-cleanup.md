# Data Safety Cleanup, Part A (F-8a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The first half of F-8 (the spec's split O1). No action of the app replaces a `.dep` that is on disk but not listed: Add and Rename refuse such a name with the existing "already exists" box, Import lists it as an import issue, and the default document takes a free name (`new (2)`). Every remaining writer of user data goes through `shared/atomic_write.py`: the text-processing script, the dictionary files of Add, Import, Export and the default dictionary, the BRL and HTML exports, and `config.json`; a failed write leaves the target byte-identical (or absent) and no temporary file, and the bytes of a successful write do not change. `config.json` that cannot be used no longer stops the app or is silently thrown away: a UTF-8 BOM is read, a file that is not a JSON object counts as damaged, a file that cannot be read is not overwritten, and a damaged one is copied to `config.json.bak` before it is replaced. No new strings, no new UI; the catalogs stay byte-identical. F-8b (startup recovery of interrupted packages, U+0000, the two notices and their 4 msgids) gets its own plan on a new branch after F-8a is merged.

**Architecture:** Four commits on the client, each red first, in the spec's migration steps 1-4. Task 1 adds `package_name_taken` and `free_document_name` to `DocumentWorkspaceService`, a disk check to `create_document`, `import_files`, the name prompt and `move_document_package`'s install step, and the free default name (D1, D2). Task 2 writes the text-processing script and the dictionary files through the atomic helpers (D6, D7). Task 3 writes the BRL and HTML exports through a new `documents.workspace.write_export_text` (D8). Task 4 makes `ConfigStore` save atomically, read a BOM, reject non-objects and keep an unusable file (D9-D11). Task 5 verifies (suite, shuffled order, catalogs, fixtures, application data, source scan, 26 mutants), Task 6 builds the exe and runs the GUI checks (spec items 66-69 and 76-82; item 84 stays manual).

**Tech Stack:** Python 3.13 standard library (`builtins`, `io`, `json`, `logging`, `shutil`, `unittest`, `unittest.mock`), wxPython 4.2.5 (unchanged UI), GNU gettext 0.23 (`xgettext`, `msgfmt`; checks only). Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-10-f8-data-safety-cleanup-design.md` (+ `_zh-TW.md`), commit `bfd24db`, with the section "Corrected after planning" added in the plan commit (both languages). The user decided U1 and U2 (2026-10-10); O1-O7 are the orchestrator's recommended defaults (the user may override them before the merge); O1 (the split) is adopted. No open question blocks the plan.

## Global Constraints

- Work in the main checkout `D:\workspace\DotExpress`, branch `fix/f8-data-safety-cleanup` (HEAD is the plan commit on top of the spec commit `bfd24db`, which is on top of `main` at `861d110`). Never switch branches, never push, never merge, never rewrite history. `D:\workspace\DotExpress-f9` is another task's worktree and `D:\workspace\DotExpress-6e5819f` an old one: do not touch them.
- Files that may change (15 under `client/`, nothing else): production `client/documents/workspace.py`, `client/documents/workspace_service.py`, `client/documents/formats.py`, `client/conversion/preprocessing/user_script.py`, `client/dictionaries/manager.py`, `client/config.py` (4 spaces), `client/gui.py` (**tabs**); tests `client/tests/full_disk.py` (new), `client/tests/test_document_workspace.py`, `client/tests/test_workspace_service.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_user_preprocessing_script.py`, `client/tests/test_dictionary_manager.py`, `client/tests/test_document_formats.py`, `client/tests/test_config.py` (4 spaces); in Task 6 the new history folder `docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/` (scripts with tabs, results). `client/shared/atomic_write.py` and `client/locales/` do not change.
- Never touch `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data in this checkout; the tests use temporary folders, every module whose code under test can log isolates that logger: `test_gui_document_flows` `dotexpress.gui` as before, `test_config` now `dotexpress.config`; Task 0 and Task 5 compare their sha256), `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (CRLF bytes), tracked `client/braille/` content, `client/braille/liblouis/`, `client/tests/fixtures/`, `client/locales/`, `scripts/`, `vendor/`, the submodule pointers, the untracked `client2/`, `preprocessing/`, `testdata/` and `task.md`, or the committed scripts and data of earlier history folders. Never run `py scripts\sync-nvda.py`. Never start `gui.py` from source in the main checkout. Never write to the Windows clipboard (no test or GUI script of this plan does). `git status --short -- client docs scripts` must stay empty between commits (the untracked folders at the root are not part of it; `docs/` holds the history folder of Task 6 only until Task 6 commits it).
- The checkout uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply the blocks **with a script that reads them from this file** (`$T/tools/apply_blocks.py`, Task 0 Step 3), not by hand: a `File:` block is written as is (LF is fine; git normalizes it); an `Edit:` block is the line ``Edit: `path` `` followed by two fenced blocks, the exact old text and its replacement; the old text must occur exactly once in the file at that point (compare with CRLF converted to LF, keep the file's line endings). The blocks of one step are applied in order. Never edit with MSYS `sed -i` and never paste code through a shell heredoc (it turns `\\` into `\`). The Edit/Write tools turn `\uXXXX` escapes into the characters they stand for: several of the edited test files hold such escapes outside the blocks (for example `test_workspace_service.py`), so never retype a block or rewrite a whole file through those tools. The blocks themselves hold no `\u` escape (a lone surrogate is `chr(0xD800)`, a BOM `b"\xef\xbb\xbf"`); the tree id check catches any change anyway.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf` (`git show HEAD:<path> | sha256sum`), unchanged.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly; look at `git diff --cached --stat` first; never `git commit -F -`.
- The only failing test before and after F-8a is the F-W6 error `test_dictionary_name_prompt ... test_case_only_rename_still_renames` (out of scope).
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`, the random part of a temporary file name as `<rnd>`). Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks.
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress
  MAIN=$REPO
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f8aimpl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the same folder as `REPO` here; the dry run used a scratch clone as `REPO`, and the commands that read the user's application data or copy the git-ignored runtime use `MAIN`. Task 6 uses PowerShell for the build and the UIA venv for the GUI scripts.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning" in the plan commit. The dry run found no error in decisions D1, D2 and D6-D11 or in their rows of the behavior table, apart from the refinements below.

1. **The split is adopted (O1).** F-8a = D1, D2, D6-D11, migration steps 1-4, Test Plan A-C, no new strings or UI, on `fix/f8-data-safety-cleanup`. F-8b = D3-D5, D12-D15, steps 5-6, Test Plan D-F, the two notices and the 4 msgids, with its own plan on a new branch after F-8a is merged. Windows items **66-69 and 76-82** belong to F-8a (manual item **84** too); items 70-75 and manual item 83 belong to F-8b. The spec's numbering is kept.
2. **Counts: `Ran 1378`, `1386`, `1389`, `1400`** (10, 8, 3, 11 new tests; baseline 1368; `FAILED (errors=1, skipped=7)` throughout, F-W6 only; msgids stay 364). Per group: C has 10 tests (C3 is two tests: the third-file test and `test_case_only_move_on_the_case_insensitive_model_is_not_refused`; C9 is the existing `test_case_only_rename_keeps_the_document`, which already runs a case-only rename through the frame on the real NTFS); A has 14 (A4 is a changed test, not a new one); B has 8 (B7 is two tests). Windows-only new tests: A3, A9, A15 and C5's NTFS subtest; they run on Windows, so the skip count stays 7.
3. **One fault injection for every writer:** a new test helper `client/tests/full_disk.py` (`full_disk(folder, after=N, pattern=...)`) patches `builtins.open` and `io.open` for a `with` block, so that a file opened for writing inside `folder` (name matching `pattern`) takes `N` characters or bytes and then raises `OSError(ENOSPC)`. It reaches the old in-place writers (`Path.write_text`, `shutil.copyfile`, `open("w")`, `tempfile.NamedTemporaryFile`) and `shared.atomic_write` alike, so each red test fails for the stated reason (a partial or emptied file, a leftover `.tmp`) and passes after the change. It replaces the spec's patches of `shutil.copyfileobj` (A6, A7: on Windows `copyfile` does not call it), `json.dump` (A14) and `os.replace` (A11).
4. **Five existing tests used a folder at `<name>.dep` to make a write fail.** D1 makes such a name taken (a folder counts, as the spec says), so they now inject the failure differently and keep their intent: `test_workspace_service` `test_import_files_lists_load_issues_before_save_issues` and `test_import_files_continues_after_a_failed_save`, `test_gui_document_flows` `test_add_write_failure_shows_error_and_keeps_state` and `test_import_reports_load_issues_before_save_issues` use `full_disk` and now compare the exact `[Errno 28] No space left on device` text; `test_rename_write_failure_keeps_old_package_and_state` fails the install with the file's `_FailingReplacePackageFiles` (which gains `destination_name`). The other tests that block a name (save of the open document, Delete, Delete All, Create of an existing folder in `test_create_document_failure_adds_nothing`, Rename onto a folder in `test_rename_write_failure_propagates_and_keeps_state`) pass unchanged. These re-pointed tests are part of Task 1's red step: they pass before and after.
5. **The `Mock` service harness** (`FrameWorkspaceServiceDelegationTest._make_frame`) sets `package_name_taken.return_value = False` and `free_document_name.side_effect = lambda base: base` (the other two settings of the spec belong to F-8b).
6. **D8: an export onto a folder of the same name keeps its message.** Through `write_text_atomically` alone, the export would fail with a failed replace that names the temporary file (`[WinError 5] ...: '<dir>\.alpha.brl.<random>.tmp' -> '<dir>\alpha.brl'`) instead of today's `[Errno 13] Permission denied: '<dir>\alpha.brl'`, which F-7's export tests and Windows item 56 pin. The BRL and HTML writers therefore go through one new function, `documents.workspace.write_export_text(path, text)`: a folder at `path` raises the in-place error (Windows `PermissionError` 13, elsewhere `IsADirectoryError`), otherwise it calls `write_text_atomically(..., encoding="utf-8", newline=None)`. `_write_html` imports it inside the function, as `formats.py` does for every `documents.workspace` name. `shared/atomic_write.py` stays unchanged: changing `ensure_writable` would also change the dictionary editor's message for a folder, which F-2 D5 pins (`test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds`).
7. **D6, D7 names:** the header writer is the private `_write_header(stream)` (the spec wrote `write_header`); `dictionaries/manager.py` gains a module docstring that states the atomic writes. `save_preprocessing_script` drops its `os` and `tempfile` imports.
8. **D10, D11 details:** `_load` raises `ValueError("config.json does not hold a JSON object (<type>)")` inside its `try` for a non-object (`NoneType`, `list`, `str`, `int`), so it is logged as today ("Failed to read config file %s; using defaults", traceback attached). `_UnreadableConfig(error)` is a `dict` subclass with `error`. A skipped save is logged once per distinct read error per path (`_logged_skipped_saves`, cleared by a successful load, as `_logged_load_failures` is) at `WARNING`, `Config file %s was not saved because it could not be read`, with the read error attached (`_log_current_exception` gains an `exc_info` keyword). `_backup_unreadable` reads the current bytes, then writes `config.json.bak` with `write_bytes_atomically`; any failure there (also a file deleted meanwhile) is logged as a failed save and nothing is written.
9. **`test_config` isolates `dotexpress.config`** in `setUpModule` (`isolate_file_logs`): the work runs in the main checkout, and a red test that logs outside `assertLogs` must not append to the user's `client/log/config.log`. `assertLogs` still captures; the existing tests are unchanged.
10. **Test details:** A1's script holds a `\r\n` so that newline translation would show; A3 checks the error's file name first, so its red message names no absolute path; A9 releases its holder before `tearDown` removes the folder; A12 (`test_exports_keep_their_crlf_bytes`) compares with `os.linesep` so it also runs on POSIX; A15 stays Windows-only; B2 also checks the logged `ValueError` text; B5 makes two setting changes and expects one skipped-save warning; B6 patches `config.write_bytes_atomically` with `create=True`, so the red step runs.
11. **Windows items (Task 6):** the font size is changed with Ctrl + one wheel notch over the source editor (`WM_MOUSEWHEEL` with `MK_CONTROL`), one point above the size the app read. 80 checks that the width 30 of the BOM file is kept instead of changing it in Settings. The app writes its client id into `config.json` at startup (the client-init thread), so in 80 the old build already replaces the BOM file at startup. 81 holds `config.json` with share mode **write only** (others may write but not read) instead of "none": with share "none" the existing writability probe at startup (`prepare_application_directories` opens `config.json` for append) fails and both builds show the existing "Startup Error"; that is not the D11 case. 79 on the old build: no main window, the process exits with code 1 after about 3 s and writes no log. 82 compares the bytes of both builds for the same steps (Text Processing's editor is a rich edit; its text is set with `WM_SETTEXT`).
12. **Acceptance criterion 7 (source scan):** the remaining matches in production code are `app_paths.py`'s append probe of `config.json` (opens, writes nothing), `PackageFiles.write` and `PackageFiles.temporary_path` (F-3's private staged file of a Rename, synced and installed with `os.replace`), and `dual_view/files.py` (excluded by the spec).

## Dry Run

The plan was executed on scratch clones of the branch at `bfd24db` with a stand-in plan commit (this plan and the corrected spec files) and a local `main` at `861d110` (`$SP/f8plan/r*`, never the main checkout), by F-7's harness: it writes every `File:` block, applies every `Edit:` block exactly once (CRLF-aware), runs every `bash` block from `client/` with `REPO` set to the clone and `MAIN` to the main checkout (so Task 0's guarded copies filled the clone, and the application-data check read the real data read-only), and compares its stdout with the following `text` block. Task 6 needs the desktop and is not part of the replay. The final replay (Tasks 0-5 from a fresh clone) matched every expected block, including all red runs, the per-commit tree ids, the six shuffle seeds and the mutation output; no `client/log`, `client/workspace`, `client/dictionary` or `client/config.json` appeared in the clone. A second fresh clone ran Task 0 Step 3's bootstrap command and then applied every step with that `apply_blocks.py`, committing at the end of each task: the block counts of Task 0 Step 3 and the tree ids below, and Task 6 Step 2's scripts equal to the ones run in the dry run.

Task 6 was run too. The second clone, at Task 4 (`HEAD:client` `62ea9d3e...`), was built with Task 6 Step 1's command ("Build complete!" in 45 s, 48,755,367 bytes; the six changed modules and `gui.py` from the clone; copied to `D:\dxtest\dryN2-f8a`), and Task 6 Step 2's scripts, written by `apply_blocks.py`, ran with Step 3's loop against `D:\dxtest\N-f7\DotExpress.exe` and against that build, in `D:\dxtest\dry*-f8a` folders that were deleted afterwards (no `D:\dxtest\auto*-f8a` folder exists yet). They printed exactly the logs of Step 4, each item once, with no re-run. Drafts of the scripts found two tool problems, fixed before that run: wx hides a dialog that ends and destroys it later, so `f8agui.closed` counts a hidden dialog as closed (a click repeated on the hidden name dialog raised `ElementNotVisible`); and item 81 with share mode "none" stops both builds at the startup probe (Spec Corrections 11). Item 84 (manual) was not run.

## Review Focus

1. **No unlisted package is ever replaced** (D1, D2): the prompt, `create_document`, `import_files` and the install step of `move_document_package` all see the disk; a case-only rename is not blocked by its own package (`exclude_name`, and the install check after the move aside); the default document takes `new (2)` (C1-C10; 8 mutants; GUI 66-69).
2. **Every writer is atomic and its bytes do not change** (D6-D9): the script keeps `newline=""`, the exports and `config.json` `newline=None` (CRLF), dictionary copies are byte copies; a failure leaves the target and no `.tmp` (A1-A15; 12 mutants; GUI 76-78, 82).
3. **An export onto a folder keeps today's message** (Spec Corrections 6): `write_export_text` (the export coordinator tests; mutant `export-onto-a-folder-names-the-temporary-file`).
4. **`config.json` is never silently discarded** (D10, D11): BOM accepted; non-object rejected without an exception; an unreadable file never written; a damaged one backed up first, and not written if the backup fails (B1-B7; 6 mutants; GUI 79-81).
5. **The tests never write the user's data or logs** in the main checkout: temporary folders only, `full_disk` restores `open` after each block, `test_config` isolates its logger.

## File Map

- Task 1: new `client/tests/full_disk.py`; `client/tests/test_document_workspace.py` (C3: two tests), `client/tests/test_workspace_service.py` (C1, C2, C4, C5, C6; two re-pointed import tests), `client/tests/test_gui_document_flows.py` (C7, C8, C10; the `Mock` harness; three re-pointed tests; `_FailingReplacePackageFiles.destination_name`); `client/documents/workspace.py` (`move_document_package`), `client/documents/workspace_service.py` (`package_name_taken`, `free_document_name`, `create_document`, `import_files`, module docstring), `client/gui.py` (`_prompt_for_document_name`, `_create_default_document`).
- Task 2: `client/tests/test_user_preprocessing_script.py` (A1-A3; A4's patch target), `client/tests/test_dictionary_manager.py` (A5-A9); `client/conversion/preprocessing/user_script.py` (`save_preprocessing_script`), `client/dictionaries/manager.py` (`_write_header`, `_copy_file_into`, the four writers, module docstring).
- Task 3: `client/tests/test_document_workspace.py` (A10), `client/tests/test_document_formats.py` (A11, A12); `client/documents/workspace.py` (`write_export_text`, `export_document_brl`), `client/documents/formats.py` (`_write_html`).
- Task 4: `client/tests/test_config.py` (log isolation; `ConfigDataSafetyTest`: A13-A15, B1-B7); `client/config.py` (`_UnreadableConfig`, `_signature`, `_logged_skipped_saves`, `_load`, `_save`, `_skip_save_of_unreadable_file`, `_backup_unreadable`, the `ConfigStore` docstring).
- Task 6: `docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/` (`auto/f8agui.py`, `auto/lockshare.py`, `auto/item66.py`, `auto/item76.py`, `auto/item79.py`, `auto/item82.py`, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | `HEAD:client` |
| --- | --- | --- | --- | --- |
| baseline (`bfd24db` + plan) | - | 1368 | `FAILED (errors=1, skipped=7)` | `9157dccd4c26f990c877ff1e2fd83e01fa1cac72` |
| 1 unlisted packages | 10 (C1-C8, C10; C3 is two); 5 re-pointed | 1378 | `FAILED (errors=1, skipped=7)` | `90a71c133ec42145605ea30e3f4ae07d916a6c71` |
| 2 script and dictionaries | 8 (A1-A3, A5-A9); A4 changed | 1386 | `FAILED (errors=1, skipped=7)` | `adcfa53378542f878db2fc2ac8c0626576c67a6d` |
| 3 exports | 3 (A10-A12) | 1389 | `FAILED (errors=1, skipped=7)` | `12837b650949f046c76ccf5b0fa2b76c927f4910` |
| 4 config.json | 11 (A13-A15, B1-B7; B7 is two) | 1400 | `FAILED (errors=1, skipped=7)` | `62ea9d3eadebd3064e70e675138c6a32c7543f7d` |
| 6 GUI results (docs only) | - | 1400 | `FAILED (errors=1, skipped=7)` | `62ea9d3eadebd3064e70e675138c6a32c7543f7d` |

The error is F-W6 throughout; the 7 skips are POSIX-only tests. The spec's acceptance-criterion-2 set goes from `Ran 502`, `OK (skipped=7)` to `Ran 534`, `OK (skipped=7)`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 by the block script: `brief.py` (F-7's, with the random part of `.py`, `.json`, `.brl` and `.html` temporary names normalized too), `msgid_scan.py` and `shuffle_harness.py` (F-7's, unchanged), `f8a_mutants.py` (26 mutants of the code after Task 4, run on a copy of `client/`; the repository is never changed) and `apply_blocks.py` (F-7's, applies the `File:` and `Edit:` blocks of one step of this plan).

---

### Task 0: Baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short -- client docs scripts
git -C $REPO log --format=%s -2
git -C $REPO branch --show-current
git -C $REPO rev-parse HEAD~2 HEAD~2:client
git -C $REPO diff --stat 861d110 -- client
```

Expected (`status` and the diff print nothing; `HEAD~2` is `main` at `861d110`):

```text
docs: plan for data safety cleanup, part a (F-8a)
docs: spec for data safety cleanup (F-8)
fix/f8-data-safety-cleanup
861d110e37f0bfad59737c03f6dde307bfde2462
9157dccd4c26f990c877ff1e2fd83e01fa1cac72
```

- [ ] **Step 2: The git-ignored runtime the tests load.** The main checkout already has the generated liblouis DLL and tables, `louis_helper.py`, MathCAT and the submodule's `configure.ac`; the guarded copies below do nothing there (they filled the dry run's scratch clone, as F-3's Task 0 did for its worktree). Never stage these files.

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

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed). `msgid_scan.py` and `shuffle_harness.py` are F-7's, unchanged; `brief.py` is F-7's with a wider temporary-name pattern; `apply_blocks.py` is F-7's with its docstring naming this plan.

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
RANDOM_TMP = re.compile(r"(\.[\w.]+?\.(?:dep|csv|py|json|brl|html)\.)[a-z0-9_]{8,16}(\.tmp)")
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

File: `$T/tools/f8a_mutants.py`

````python
"""Run the F-8a tests against deliberately broken code (throwaway, not committed).

Usage: python f8a_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one file of the copy (one exact, unique replacement), runs the F-8a test
modules there, prints which tests caught it and restores the file. The repository is
never changed. Matches the code after Task 4. Exit status 1 if a mutant is not caught or
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
WORKSPACE = "documents/workspace.py"
SERVICE = "documents/workspace_service.py"
FORMATS = "documents/formats.py"
SCRIPT = "conversion/preprocessing/user_script.py"
MANAGER = "dictionaries/manager.py"
CONFIG = "config.py"
MUTANTS = {
	# D1: a package on disk that is not listed is never replaced.
	"prompt-without-the-disk-check": (
		GUI,
		"\t\t\t) or self._workspace_service.package_name_taken(document_name, exclude_name=exclude_name):\n",
		"\t\t\t):\n",
	),
	"name-taken-ignores-exclude-name": (
		SERVICE,
		"        if exclude_name is not None and name.casefold() == exclude_name.casefold():\n            return False\n",
		"",
	),
	"create-without-its-check": (
		SERVICE,
		"        if os.path.lexists(package_path):\n",
		"        if False:\n",
	),
	"move-guard-before-the-move-aside": (
		WORKSPACE,
		"    files.ensure_writable(old_path)\n",
		"    files.ensure_writable(old_path)\n    if files.exists(new_path):\n        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(new_path))\n",
	),
	"move-guard-removed": (
		WORKSPACE,
		"        if files.exists(new_path):\n            raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(new_path))\n",
		"",
	),
	"import-with-listed-names-only": (
		SERVICE,
		"            existing_names=set(self._controller.document_names) | on_disk,\n",
		"            existing_names=set(self._controller.document_names),\n",
	),
	# D2: the default document takes a free name.
	"free-name-returns-base": (
		SERVICE,
		"        while self._controller.document_name_exists(name) or self.package_name_taken(name):\n",
		"        while False:\n",
	),
	"default-document-always-new": (
		GUI,
		"\t\t\tself._workspace_service.free_document_name(DEFAULT_DOCUMENT_NAME),\n",
		"\t\t\tDEFAULT_DOCUMENT_NAME,\n",
	),
	# D6: the text-processing script.
	"script-written-in-place": (
		SCRIPT,
		'    write_text_atomically(destination, lambda stream: stream.write(source), encoding="utf-8", newline="")\n',
		'    destination.write_text(source, encoding="utf-8", newline="")\n',
	),
	"script-newlines-translated": (
		SCRIPT,
		'stream.write(source), encoding="utf-8", newline="")\n',
		'stream.write(source), encoding="utf-8", newline=None)\n',
	),
	# D7: dictionary files.
	"default-dictionary-written-in-place": (
		MANAGER,
		'        write_text_atomically(default_path, _write_header, encoding="utf-8", newline="")\n',
		'        with default_path.open("w", newline="", encoding="utf-8") as fp:\n            _write_header(fp)\n',
	),
	"new-dictionary-written-in-place": (
		MANAGER,
		'    write_text_atomically(path, _write_header, encoding="utf-8", newline="")\n',
		'    with path.open("w", newline="", encoding="utf-8") as fp:\n        _write_header(fp)\n',
	),
	"import-copyfile": (
		MANAGER,
		"    write_bytes_atomically(destination_path, lambda stream: _copy_file_into(source, stream))\n",
		"    shutil.copyfile(source, destination_path)\n",
	),
	"export-copyfile": (
		MANAGER,
		"    write_bytes_atomically(destination, lambda stream: _copy_file_into(source_path, stream))\n",
		"    shutil.copyfile(source_path, destination)\n",
	),
	# D8: BRL and HTML exports.
	"export-text-written-in-place": (
		WORKSPACE,
		'    write_text_atomically(destination, lambda stream: stream.write(text), encoding="utf-8", newline=None)\n',
		'    destination.write_text(text, encoding="utf-8")\n',
	),
	"export-text-without-newline-translation": (
		WORKSPACE,
		'stream.write(text), encoding="utf-8", newline=None)\n',
		'stream.write(text), encoding="utf-8", newline="")\n',
	),
	"export-onto-a-folder-names-the-temporary-file": (
		WORKSPACE,
		"    if destination.is_dir():\n",
		"    if False:\n",
	),
	"html-written-in-place": (
		FORMATS,
		"    write_export_text(destination, html)\n",
		'    destination.write_text(html, encoding="utf-8")\n',
	),
	# D9: config.json is written atomically.
	"config-written-in-place": (
		CONFIG,
		"            write_text_atomically(\n                path,\n                lambda stream: json.dump(data, stream, ensure_ascii=False, indent=2),\n",
		'            with open(path, "w", encoding="utf-8") as f:\n                json.dump(data, f, ensure_ascii=False, indent=2)\n            (lambda *args, **kwargs: None)(\n                path,\n                None,\n',
	),
	"config-without-newline-translation": (
		CONFIG,
		"                encoding=\"utf-8\",\n                newline=None,\n            )\n        except Exception:\n",
		"                encoding=\"utf-8\",\n                newline=\"\",\n            )\n        except Exception:\n",
	),
	# D10: the load.
	"load-without-utf8-sig": (CONFIG, 'open(path, "r", encoding="utf-8-sig")', 'open(path, "r", encoding="utf-8")'),
	"load-accepts-a-non-object": (CONFIG, "            if not isinstance(data, dict):\n", "            if False:\n"),
	# D11: the save after a failed load.
	"save-after-an-unreadable-load": (
		CONFIG,
		"        if isinstance(data, _UnreadableConfig) and isinstance(data.error, OSError):\n",
		"        if False:\n",
	),
	"no-backup": (CONFIG, "                self._backup_unreadable()\n", "                pass\n"),
	"write-when-the-backup-fails": (
		CONFIG,
		"                self._backup_unreadable()\n",
		"                try:\n                    self._backup_unreadable()\n                except OSError:\n                    pass\n",
	),
	"skipped-save-logged-every-time": (CONFIG, "        if _logged_skipped_saves.get(path) != signature:\n", "        if True:\n"),
}
MODULES = (
	"tests.test_atomic_write",
	"tests.test_document_workspace",
	"tests.test_workspace_service",
	"tests.test_document_formats",
	"tests.test_export_coordinator",
	"tests.test_user_preprocessing_script",
	"tests.test_dictionary_manager",
	"tests.test_dictionary_presenter",
	"tests.test_config",
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
"""Apply the File: and Edit: blocks of one step of the F-8a plan (throwaway, not committed).

Usage: python apply_blocks.py <plan.md> <repo> <T> "<task>" "<step>"
  for example: python apply_blocks.py plan.md D:/workspace/DotExpress <T> "Task 1" "Step 1"

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
PLAN=$REPO/docs/superpowers/plans/2026-10-10-f8a-data-safety-cleanup.md
$PY -c "import sys; from pathlib import Path; text = Path(sys.argv[1]).read_bytes().decode('utf-8').replace(chr(13) + chr(10), chr(10)); start = text.index('File: \`\$T/tools/apply_blocks.py\`'); body = text[text.index(chr(10), text.index('\`\`\`\`python', start)) + 1:text.index(chr(10) + '\`\`\`\`' + chr(10), start)]; Path(sys.argv[2]).write_bytes((body + chr(10)).encode('utf-8')); print('apply_blocks.py extracted')" "$PLAN" "$T/tools/apply_blocks.py"
$PY $T/tools/apply_blocks.py "$PLAN" $REPO $T "Task 0" "Step 3"
```

Expected:

```text
apply_blocks.py extracted
wrote $T/tools/brief.py
wrote $T/tools/msgid_scan.py
wrote $T/tools/shuffle_harness.py
wrote $T/tools/f8a_mutants.py
wrote $T/tools/apply_blocks.py
5 blocks applied (Task 0, Step 3)
```

From then on apply every step's blocks with `apply_blocks.py`, for example `$PY $T/tools/apply_blocks.py ../docs/superpowers/plans/2026-10-10-f8a-data-safety-cleanup.md $REPO $T "Task 1" "Step 1"`; it prints `N blocks applied` (Task 0 Step 3: 5; Task 1 Step 1: 16, Step 2: 9; Task 2 Step 1: 6, Step 2: 7; Task 3 Step 1: 4, Step 2: 3; Task 4 Step 1: 3, Step 2: 6; Task 6 Step 2: 6).

- [ ] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, catalogs, tree, application data.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_document_formats tests.test_export_coordinator tests.test_user_preprocessing_script tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_config tests.test_gui_document_flows tests.test_i18n tests.test_wx_call_sites 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "msgfmt rebuilds the committed .mo byte for byte"
git -C $REPO rev-parse HEAD:client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) > $T/app-data.sha256; wc -l < $T/app-data.sha256
```

Expected (the second `Ran` line is the spec's acceptance-criterion-2 set; the last line counts the files of the user's application data in the main checkout, including `client/log/`, recorded read-only for Task 5; if the user has used the app since the dry run, that number differs, which is fine):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1368 tests
FAILED (errors=1, skipped=7)
Ran 502 tests
OK (skipped=7)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
source msgids: 364 sha256 7b53ff311c9e446767b0884bfc03148afe030ca7e15899d6ee6919e77c664ea7
locales/dotexpress.pot:365
locales/zh_TW/LC_MESSAGES/dotexpress.po:365
364 translated messages.
msgfmt rebuilds the committed .mo byte for byte
9157dccd4c26f990c877ff1e2fd83e01fa1cac72
4
```

### Task 1: Never replace a document package that is not listed (D1, D2)

- [ ] **Step 1: Red: C1-C8, C10; the shared fault injection; five re-pointed tests; the `Mock` harness.** The new `client/tests/full_disk.py` (4 spaces) makes writes fail as on a full disk (Spec Corrections 3). `test_workspace_service.py` gets C1, C2, C4, C5, C6 and re-points its two import-failure tests; `test_document_workspace.py` gets the two C3 tests; `test_gui_document_flows.py` gets C7, C8, C10, the `Mock` service settings, `_FailingReplacePackageFiles.destination_name` and re-points three tests (Spec Corrections 4, 5). All three test files use 4 spaces. The re-pointed tests pass before and after this task.

File: `client/tests/full_disk.py`

````python
"""Make writes fail as on a full disk, for the data safety tests (F-8).

``full_disk(folder, after=..., pattern=...)`` patches ``builtins.open`` and ``io.open``
(which ``pathlib``, ``tempfile`` and ``shutil`` call) for the length of a ``with`` block.
A file opened for writing inside ``folder`` whose name matches ``pattern`` takes ``after``
more characters (text) or bytes (binary); the write that would go past them writes what
fits and raises ``OSError(ENOSPC)``, as a full disk does. Reads and other files are not
touched. The same fault reaches the old in-place writers and ``shared.atomic_write``, so a
test sees what each leaves behind. ``tempfile.NamedTemporaryFile`` opens its folder with an
opener; that open counts as one of the folder itself.
"""

from __future__ import annotations

import builtins
import contextlib
import errno
import io
import os
import re
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

_WRITE_MODES = frozenset("wax+")


class _FullDiskStream:
    """A writable stream with ``room`` characters or bytes left before the disk is full."""

    def __init__(self, stream, room: int) -> None:
        self._stream = stream
        self._room = room

    def write(self, data):
        if len(data) > self._room:
            if self._room > 0:
                self._stream.write(data[: self._room])
                self._room = 0
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
        self._room -= len(data)
        return self._stream.write(data)

    def writelines(self, lines) -> None:
        for line in lines:
            self.write(line)

    def __getattr__(self, name: str):
        return getattr(self._stream, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return self._stream.__exit__(*exc_info)


@contextlib.contextmanager
def full_disk(folder: Path | str, *, after: int = 0, pattern: str = "") -> Iterator[None]:
    """Writes inside ``folder`` to names matching ``pattern`` fail after ``after`` units."""
    real_open = io.open
    root = os.path.normcase(os.path.abspath(folder))
    name_pattern = re.compile(pattern)

    def inside(path: str) -> bool:
        try:
            return os.path.commonpath([os.path.normcase(path), root]) == root
        except ValueError:  # another drive
            return False

    def open_on_a_full_disk(file, mode="r", *args, **kwargs):
        stream = real_open(file, mode, *args, **kwargs)
        if isinstance(file, int) or not _WRITE_MODES & set(mode):
            return stream
        path = os.path.abspath(os.fspath(file))
        if not inside(path) or not name_pattern.search(os.path.basename(path)):
            return stream
        return _FullDiskStream(stream, after)

    with patch.object(builtins, "open", open_on_a_full_disk), patch.object(io, "open", open_on_a_full_disk):
        yield
````

Edit: `client/tests/test_workspace_service.py`

```python
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from shared import name_validation
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.windows_file_handles import SHARE_DELETE, SHARE_MODES, hold_open, make_read_only

SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"

```

```python
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from shared import name_validation
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.full_disk import full_disk
from tests.windows_file_handles import SHARE_DELETE, SHARE_MODES, hold_open, make_read_only

NO_SPACE = f"[Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}"

SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"

```

Edit: `client/tests/test_workspace_service.py`

```python
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual(self._state(), before)

    # --- import ------------------------------------------------------------

    def _sources(self, **texts: str) -> list[Path]:
```

```python
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual(self._state(), before)

    # --- packages on disk that are not listed (F-8, D1, D2) ----------------

    def _start_with_a_kept_invalid_package(self, name: str = "bad") -> DocumentWorkspaceService:
        """alpha listed and open; ``<name>.dep`` invalid, kept at startup (not listed)."""
        self._write(Document("alpha", "a", "1"))
        (self.workspace / f"{name}.dep").write_bytes(b"not a zip")
        service = self._service()
        self.assertEqual(service.load_documents(), [self.workspace / f"{name}.dep"])
        self.controller.open_document("alpha")
        return service

    def _exists_error(self, name: str) -> str:
        return f"[Errno {errno.EEXIST}] {os.strerror(errno.EEXIST)}: {str(self.workspace / name)!r}"

    def test_create_document_refuses_a_package_that_is_not_listed(self) -> None:
        service = self._start_with_a_kept_invalid_package()
        before = self._state()

        with self.assertRaises(FileExistsError) as raised:
            service.create_document(Document("bad", "", ""))

        self.assertEqual(str(raised.exception), self._exists_error("bad.dep"))
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual(self._state(), before)

    def test_rename_onto_a_package_that_is_not_listed_keeps_both_files(self) -> None:
        service = self._start_with_a_kept_invalid_package()
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        before = self._state()

        with self.assertRaises(FileExistsError) as raised:
            service.rename_document("alpha", "bad")

        self.assertEqual(str(raised.exception), self._exists_error("bad.dep"))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual(self._state(), before)

    def test_import_treats_packages_on_disk_as_existing(self) -> None:
        # The kept package is spelled Bad.dep: names on disk are compared ignoring case.
        service = self._start_with_a_kept_invalid_package("Bad")
        sources = self._sources(bad="b", ok="o")

        result = service.import_files(sources, format_key="all")

        self.assertEqual(
            result,
            ImportResult(
                saved=[Document("ok", "o", None)],
                issues=[BatchIssue(path=sources[0], reason='Document "bad" already exists.')],
            ),
        )
        self.assertEqual(self.controller.document_names, ["alpha", "ok"])
        self.assertEqual(self._listing(), ["Bad.dep", "alpha.dep", "ok.dep"])
        self.assertEqual((self.workspace / "Bad.dep").read_bytes(), b"not a zip")

    def test_package_name_taken(self) -> None:
        service = self._start_with_a_kept_invalid_package()
        self._block("folder")
        cases = [
            ("missing", "gamma", None, False),
            ("listed", "alpha", None, True),
            ("unlisted file", "bad", None, True),
            ("folder", "folder", None, True),
            ("its own package, any case", "Alpha", "alpha", False),
            ("another package than the excluded one", "bad", "alpha", True),
        ]
        if os.name == "nt":
            cases.append(("other case on NTFS", "BAD", None, True))
        for label, name, exclude_name, expected in cases:
            with self.subTest(label):
                self.assertIs(service.package_name_taken(name, exclude_name=exclude_name), expected)

    def test_free_document_name(self) -> None:
        cases = (
            ("free", (), (), "new"),
            ("new.dep on disk", ("new",), (), "new (2)"),
            ("new.dep and new (2).dep on disk", ("new", "new (2)"), (), "new (3)"),
            ("new listed, no file", (), (Document("new", "", None),), "new (2)"),
        )
        for label, on_disk, listed, expected in cases:
            with self.subTest(label):
                self.workspace = self.root / label
                self.workspace.mkdir()
                for name in on_disk:
                    (self.workspace / f"{name}.dep").write_bytes(b"not a zip")
                service = self._service(listed)

                self.assertEqual(service.free_document_name("new"), expected)

    # --- import ------------------------------------------------------------

    def _sources(self, **texts: str) -> list[Path]:
```

Edit: `client/tests/test_workspace_service.py`

```python
        self.assertEqual(self._listing(), ["beta.dep", "delta.dep"])

    def test_import_files_lists_load_issues_before_save_issues(self) -> None:
        self._block("delta")
        service = self._service([Document("alpha", "a", "1")])
        sources = self._sources(Alpha="dup", beta="b", delta="d")

        result = service.import_files(sources, format_key="all")

        self.assertEqual(result.saved, [Document("beta", "b", None)])
        self.assertEqual(self.controller.document_names, ["alpha", "beta"])
        self.assertEqual(len(result.issues), 2)
        self.assertEqual(result.issues[0], BatchIssue(path=sources[0], reason='Document "Alpha" already exists.'))
        self.assertEqual(result.issues[1].path, self.workspace / "delta.dep")
        self.assertIn("delta.dep", result.issues[1].reason)

    def test_import_files_reports_any_save_error_as_an_issue(self) -> None:
        # F-3 (D9): an error that is not an OSError becomes an issue too; before, it
```

```python
        self.assertEqual(self._listing(), ["beta.dep", "delta.dep"])

    def test_import_files_lists_load_issues_before_save_issues(self) -> None:
        # F-8 (D1): a folder at delta.dep would now make the name taken (a load issue),
        # so the save of delta fails on a full disk instead.
        service = self._service([Document("alpha", "a", "1")])
        sources = self._sources(Alpha="dup", beta="b", delta="d")

        with full_disk(self.workspace, pattern=r"^\.delta\.dep\."):
            result = service.import_files(sources, format_key="all")

        self.assertEqual(result.saved, [Document("beta", "b", None)])
        self.assertEqual(self.controller.document_names, ["alpha", "beta"])
        self.assertEqual(len(result.issues), 2)
        self.assertEqual(result.issues[0], BatchIssue(path=sources[0], reason='Document "Alpha" already exists.'))
        self.assertEqual(result.issues[1], BatchIssue(path=self.workspace / "delta.dep", reason=NO_SPACE))
        self.assertEqual(self._listing(), ["beta.dep"])

    def test_import_files_reports_any_save_error_as_an_issue(self) -> None:
        # F-3 (D9): an error that is not an OSError becomes an issue too; before, it
```

Edit: `client/tests/test_workspace_service.py`

```python
    def test_import_files_continues_after_a_failed_save(self) -> None:
        # F-3 (D9): a failed save is an issue and the batch goes on; the
        # documents after it are still saved and added.
        blocked = self._block("beta")
        service = self._service([Document("zoo", "z", "1")])

        result = service.import_files(self._sources(beta="b", delta="d", epsilon="e"), format_key="all")

        expected = [Document("delta", "d", None), Document("epsilon", "e", None)]
        self.assertEqual(result.saved, expected)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].path, blocked)
        self.assertEqual(self.controller.document_names, ["zoo", "delta", "epsilon"])
        self.assertEqual(self._package("delta"), expected[0])
        self.assertEqual(self._package("epsilon"), expected[1])
```

```python
    def test_import_files_continues_after_a_failed_save(self) -> None:
        # F-3 (D9): a failed save is an issue and the batch goes on; the
        # documents after it are still saved and added.
        service = self._service([Document("zoo", "z", "1")])

        with full_disk(self.workspace, pattern=r"^\.beta\.dep\."):
            result = service.import_files(self._sources(beta="b", delta="d", epsilon="e"), format_key="all")

        expected = [Document("delta", "d", None), Document("epsilon", "e", None)]
        self.assertEqual(result.saved, expected)
        self.assertEqual(result.issues, [BatchIssue(path=self.workspace / "beta.dep", reason=NO_SPACE)])
        self.assertEqual(self.controller.document_names, ["zoo", "delta", "epsilon"])
        self.assertEqual(self._package("delta"), expected[0])
        self.assertEqual(self._package("epsilon"), expected[1])
```

Edit: `client/tests/test_document_workspace.py`

```python
    save_document_package,
)
from shared import name_validation
from tests.windows_file_handles import SHARE_MODES, hold_open, is_hidden, make_hidden, make_read_only


```

```python
    save_document_package,
)
from shared import name_validation
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.windows_file_handles import SHARE_MODES, hold_open, is_hidden, make_hidden, make_read_only


```

Edit: `client/tests/test_document_workspace.py`

```python
        self.assertEqual(self._listing(), ["gamma.dep"])
        self.assertEqual(load_document_package(self._path("gamma")), Document("gamma", "a", "1"))

    def test_missing_old_package_and_directory_writes_the_new_package(self) -> None:
        self._move("Alpha", Document("alpha", "a", "1"))

```

```python
        self.assertEqual(self._listing(), ["gamma.dep"])
        self.assertEqual(load_document_package(self._path("gamma")), Document("gamma", "a", "1"))

    def test_move_onto_an_existing_third_file_puts_the_old_package_back(self) -> None:
        # F-8 (D1): a package that is not listed (kept invalid at startup) or one created
        # after the name was checked is never replaced; the old package stays.
        save_document_package(self._path("alpha"), Document("alpha", "a", "1"))
        before = self._path("alpha").read_bytes()
        self._path("bad").write_bytes(b"not a zip")

        with self.assertRaises(FileExistsError) as raised:
            self._move("alpha", Document("bad", "a", "1"))

        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EEXIST}] {os.strerror(errno.EEXIST)}: {str(self._path('bad'))!r}",
        )
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual(self._path("alpha").read_bytes(), before)
        self.assertEqual(self._path("bad").read_bytes(), b"not a zip")

    def test_case_only_move_on_the_case_insensitive_model_is_not_refused(self) -> None:
        # The check for a third file runs after the old package is moved aside: before
        # that, the new spelling names the old package itself on such a file system.
        self._write_alpha()

        self._move("Alpha", Document("alpha", "a", "1"), CaseInsensitivePackageFiles())

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", "1"))

    def test_missing_old_package_and_directory_writes_the_new_package(self) -> None:
        self._move("Alpha", Document("alpha", "a", "1"))

```

Edit: `client/tests/test_gui_document_flows.py`

```python
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.file_log_isolation import isolate_file_logs
from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
from tests.windows_file_handles import make_read_only

```

```python
from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.file_log_isolation import isolate_file_logs
from tests.full_disk import full_disk
from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
from tests.windows_file_handles import make_read_only

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        )
        frame._workspace_service = Mock()
        frame._workspace_service.workspace_dir = self.workspace
        frame.input_txt = Mock()
        frame.output_txt = Mock()
        frame._show_file_error = Mock()
```

```python
        )
        frame._workspace_service = Mock()
        frame._workspace_service.workspace_dir = self.workspace
        # F-8 (D1, D2): a bare Mock would answer "taken" and loop the name prompt.
        frame._workspace_service.package_name_taken.return_value = False
        frame._workspace_service.free_document_name.side_effect = lambda base: base
        frame.input_txt = Mock()
        frame.output_txt = Mock()
        frame._show_file_error = Mock()
```

Edit: `client/tests/test_gui_document_flows.py`

```python


class _FailingReplacePackageFiles(PackageFiles):
    """The real file operations, except that moving the file named ``source_name`` raises."""

    def __init__(self, *, source_name: str) -> None:
        self.source_name = source_name

    def replace(self, source: Path, destination: Path) -> None:
        if Path(source).name == self.source_name:
            raise PermissionError(errno.EACCES, "injected", str(source), None, str(destination))
        super().replace(source, destination)

```

```python


class _FailingReplacePackageFiles(PackageFiles):
    """The real file operations, except that moving the file named ``source_name``, or onto
    the file named ``destination_name``, raises."""

    def __init__(self, *, source_name: str | None = None, destination_name: str | None = None) -> None:
        self.source_name = source_name
        self.destination_name = destination_name

    def replace(self, source: Path, destination: Path) -> None:
        if Path(source).name == self.source_name or Path(destination).name == self.destination_name:
            raise PermissionError(errno.EACCES, "injected", str(source), None, str(destination))
        super().replace(source, destination)

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    def test_add_write_failure_shows_error_and_keeps_state(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        self._block("beta")
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        before = self._state(frame)
        self.names = ["beta"]

        frame.on_add_document(None)

        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
        self.assertEqual(self._state(frame), before)
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))

    def test_add_failure_that_is_not_an_os_error_shows_the_message(self) -> None:
```

```python
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    def test_add_write_failure_shows_error_and_keeps_state(self) -> None:
        # F-8 (D1): a folder at beta.dep would now make the name taken, so the write of
        # beta fails on a full disk instead.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        before = self._state(frame)
        self.names = ["beta"]

        with full_disk(self.workspace, pattern=r"^\.beta\.dep\."):
            frame.on_add_document(None)

        self.assertEqual(len(self.events), 2)
        self.assertEqual(
            self.events[1],
            (
                "MessageBox",
                gui._("Failed to save document: {error}").format(error=f"[Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}"),
                gui._("Error"),
                gui.wx.OK | gui.wx.ICON_ERROR,
                frame,
            ),
        )
        self.assertEqual(self._state(frame), before)
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))

    def test_add_failure_that_is_not_an_os_error_shows_the_message(self) -> None:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self.events, [("title", "good - DotExpress"), ("title", "good - DotExpress")])
        self.assertEqual(self._listing(), sorted(leftovers + ["good.dep"]))
        self.assertEqual(frame._document_controller.document_names, ["good"])

    # --- save --------------------------------------------------------------

```

```python
        self.assertEqual(self.events, [("title", "good - DotExpress"), ("title", "good - DotExpress")])
        self.assertEqual(self._listing(), sorted(leftovers + ["good.dep"]))
        self.assertEqual(frame._document_controller.document_names, ["good"])

    def test_startup_with_only_a_kept_invalid_new_package_creates_new_2(self) -> None:
        # F-8 (D2): the default document takes a free name; the kept new.dep stays as it is.
        self.workspace.mkdir()
        (self.workspace / "new.dep").write_bytes(b"not a zip")
        frame = self._make_workspace_frame()

        frame._load_workspace_documents_at_startup()

        self.assertEqual(
            self.events,
            [
                ("InvalidWorkspaceFilesDialog", [self.workspace / "new.dep"]),
                ("title", "new (2) - DotExpress"),
                ("focus", "input"),
                ("title", "new (2) - DotExpress"),
            ],
        )
        self.assertEqual(self._listing(), ["new (2).dep", "new.dep"])
        self.assertEqual((self.workspace / "new.dep").read_bytes(), b"not a zip")
        self.assertEqual(self._package("new (2)"), Document("new (2)", "", None))
        self.assertEqual(frame._document_controller.document_names, ["new (2)"])
        self.assertEqual(frame._document_controller.open_name, "new (2)")

    # --- save --------------------------------------------------------------

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(frame._document_controller.selected_name, "gamma")

    def test_rename_write_failure_keeps_old_package_and_state(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        self._block("gamma")
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        before = self._state(frame)
        self.names = ["gamma"]

```

```python
        self.assertEqual(frame._document_controller.selected_name, "gamma")

    def test_rename_write_failure_keeps_old_package_and_state(self) -> None:
        # F-8 (D1): a folder at gamma.dep would now make the name taken, so installing
        # gamma.dep fails instead.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame._workspace_service = DocumentWorkspaceService(
            frame._document_controller,
            self.workspace,
            package_files=_FailingReplacePackageFiles(destination_name="gamma.dep"),
        )
        before = self._state(frame)
        self.names = ["gamma"]

```

Edit: `client/tests/test_gui_document_flows.py`

```python

        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "gamma.dep", frame)
        self.assertEqual(self._package("alpha"), alpha)
        self.assertEqual(self._state(frame), before)

```

```python

        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "gamma.dep", frame)
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._package("alpha"), alpha)
        self.assertEqual(self._state(frame), before)

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._package("beta"), beta)
        self.assertEqual(self._state(frame), before)

    # --- delete ------------------------------------------------------------

    def test_delete_open_middle_document_opens_previous_neighbour(self) -> None:
```

```python
        self.assertEqual(self._package("beta"), beta)
        self.assertEqual(self._state(frame), before)

    def _frame_with_a_kept_invalid_bad_package(self):
        """alpha listed and open, bad.dep invalid and kept at startup (F-8, M-1)."""
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        (self.workspace / "bad.dep").write_bytes(b"not a zip")
        return self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")

    def test_add_of_a_name_whose_package_is_on_disk_asks_again(self) -> None:
        frame = self._frame_with_a_kept_invalid_bad_package()
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        before = self._state(frame)
        self.names = ["bad", None]

        frame.on_add_document(None)

        self.assertEqual(self.events, self._duplicate_name_events("Add Document", "", "bad", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(frame), before)

    def test_rename_to_a_name_whose_package_is_on_disk_asks_again(self) -> None:
        frame = self._frame_with_a_kept_invalid_bad_package()
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        before = self._state(frame)
        self.names = ["bad", None]

        frame.on_rename_document(None)

        self.assertEqual(self.events, self._duplicate_name_events("Rename Document", "alpha", "bad", frame))
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual((self.workspace / "bad.dep").read_bytes(), b"not a zip")
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(frame), before)

    # --- delete ------------------------------------------------------------

    def test_delete_open_middle_document_opens_previous_neighbour(self) -> None:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self.events[1:], [("title", "beta - DotExpress")])

    def test_import_reports_load_issues_before_save_issues(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        self._block("delta")
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.import_paths = self._write_sources(Alpha="dup", beta="b", delta="d")

        frame.on_import_document(None)

        self.assertEqual(frame._document_controller.document_names, ["alpha", "beta"])
        self.assertEqual(frame._document_controller.open_name, "beta")
        kind, title, message, lines = self.events[-1]
        self.assertEqual((kind, title, message), ("FileIssuesDialog", gui._("Import Issues"), gui._("Some files were skipped during import.")))
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], 'Alpha.txt: Document "Alpha" already exists.')
        self.assertTrue(lines[1].startswith("delta.dep: "), lines[1])
        self.assertIn("delta.dep", lines[1][len("delta.dep: "):])

    # --- selection ---------------------------------------------------------

```

```python
        self.assertEqual(self.events[1:], [("title", "beta - DotExpress")])

    def test_import_reports_load_issues_before_save_issues(self) -> None:
        # F-8 (D1): a folder at delta.dep would now make the name taken (a load issue),
        # so the save of delta fails on a full disk instead.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        self.import_paths = self._write_sources(Alpha="dup", beta="b", delta="d")

        with full_disk(self.workspace, pattern=r"^\.delta\.dep\."):
            frame.on_import_document(None)

        self.assertEqual(frame._document_controller.document_names, ["alpha", "beta"])
        self.assertEqual(frame._document_controller.open_name, "beta")
        kind, title, message, lines = self.events[-1]
        self.assertEqual((kind, title, message), ("FileIssuesDialog", gui._("Import Issues"), gui._("Some files were skipped during import.")))
        self.assertEqual(
            lines,
            [
                'Alpha.txt: Document "Alpha" already exists.',
                f"delta.dep: [Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}",
            ],
        )
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    # --- selection ---------------------------------------------------------

```

Run the three modules:

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (C5 and C6 fail in every subtest with `AttributeError`, the methods do not exist yet; C1, C2 and C3's third-file test because nothing refuses the name; C4 imports `bad`; C7 and C8 create or rename to `bad` without a message; C10 replaces `new.dep`. The second C3 test and the re-pointed tests pass. The 2 skips are POSIX-only tests):

```text
ERROR: test_free_document_name (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_free_document_name) [free]
AttributeError: 'DocumentWorkspaceService' object has no attribute 'free_document_name'
ERROR: test_free_document_name (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_free_document_name) [new.dep on disk]
ERROR: test_free_document_name (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_free_document_name) [new.dep and new (2).dep on disk]
ERROR: test_free_document_name (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_free_document_name) [new listed, no file]
ERROR: test_package_name_taken (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_package_name_taken) [missing]
AttributeError: 'DocumentWorkspaceService' object has no attribute 'package_name_taken'
ERROR: test_package_name_taken (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_package_name_taken) [listed]
ERROR: test_package_name_taken (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_package_name_taken) [unlisted file]
ERROR: test_package_name_taken (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_package_name_taken) [folder]
ERROR: test_package_name_taken (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_package_name_taken) [its own package, any case]
ERROR: test_package_name_taken (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_package_name_taken) [another package than the excluded one]
ERROR: test_package_name_taken (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_package_name_taken) [other case on NTFS]
FAIL: test_move_onto_an_existing_third_file_puts_the_old_package_back (tests.test_document_workspace.MoveDocumentPackageTest.test_move_onto_an_existing_third_fi
AssertionError: FileExistsError not raised
FAIL: test_create_document_refuses_a_package_that_is_not_listed (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_create_document_refuses_a_packag
FAIL: test_import_treats_packages_on_disk_as_existing (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_import_treats_packages_on_disk_as_existing
AssertionError: Impor[25 chars]ame='bad', text='b', braille=None), Document(n[41 chars]s=[]) != Impor[25 chars]ame='ok', text='o', braille=None)], issues=[Ba[12
FAIL: test_rename_onto_a_package_that_is_not_listed_keeps_both_files (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_rename_onto_a_package_that_
FAIL: test_add_of_a_name_whose_package_is_on_disk_asks_again (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_add_of_a_name_whose_
AssertionError: Lists differ: [('Do[29 chars]), ('title', 'bad - DotExpress')] != [('Do[29 chars]), ('MessageBox', '文件「bad」已存在。', '錯誤', 516, <g[81 chars]ad')]
FAIL: test_rename_to_a_name_whose_package_is_on_disk_asks_again (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_rename_to_a_name_
AssertionError: Lists differ: [('Do[36 chars]), ('title', 'bad - DotExpress')] != [('Do[36 chars]), ('MessageBox', '文件「bad」已存在。', '錯誤', 516, <g[83 chars]ad')]
FAIL: test_startup_with_only_a_kept_invalid_new_package_creates_new_2 (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_startup_wit
AssertionError: Lists differ: [('In[121 chars]'new - DotExpress'), ('focus', 'input'), ('tit[20 chars]ss')] != [('In[121 chars]'new (2) - DotExpress'), ('focus'
Ran 310 tests
FAILED (failures=7, errors=11, skipped=2)
```

- [ ] **Step 2: Green: the disk check in the service, the move, the prompt and the default document.** `client/documents/workspace.py` and `client/documents/workspace_service.py` use 4 spaces, `client/gui.py` tabs.

Edit: `client/documents/workspace.py`

```python

from contextlib import suppress
from dataclasses import dataclass
import json
import os
from pathlib import Path
```

```python

from contextlib import suppress
from dataclasses import dataclass
import errno
import json
import os
from pathlib import Path
```

Edit: `client/documents/workspace.py`

```python

    An old package the user may not write (a read-only file) raises ``PermissionError``
    before anything is created or moved, as saving it does (F-3).
    """
    old_path = Path(old_path)
    new_path = Path(new_path)
```

```python

    An old package the user may not write (a read-only file) raises ``PermissionError``
    before anything is created or moved, as saving it does (F-3).

    A file already at ``new_path`` (a package that is not listed) raises
    ``FileExistsError``; the old package is put back (F-8). The check runs after the old
    package is moved aside, so a case-only rename does not find the old package itself.
    """
    old_path = Path(old_path)
    new_path = Path(new_path)
```

Edit: `client/documents/workspace.py`

```python
                files.remove(aside_path)
        raise
    try:
        if aside_path is not None:
            files.copy_permissions(aside_path, staged_path)
        files.replace(staged_path, new_path)
```

```python
                files.remove(aside_path)
        raise
    try:
        if files.exists(new_path):
            raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(new_path))
        if aside_path is not None:
            files.copy_permissions(aside_path, staged_path)
        files.replace(staged_path, new_path)
```

Edit: `client/documents/workspace_service.py`

```python
Save writes only when the open document differs from what was last written to or
loaded from its package; that record changes only after a successful write, so a
failed save is retried by the next one.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import os
from pathlib import Path
import stat
```

```python
Save writes only when the open document differs from what was last written to or
loaded from its package; that record changes only after a successful write, so a
failed save is retried by the next one.
Add, Rename, Import and the default document never replace a package that is on disk
but not listed, such as an invalid one kept at startup: its name counts as taken.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import errno
import os
from pathlib import Path
import stat
```

Edit: `client/documents/workspace_service.py`

```python
from documents.session import DeleteDocumentDecision
from documents.workspace import (
    BatchIssue,
    Document,
    PackageFiles,
    _encodable,
```

```python
from documents.session import DeleteDocumentDecision
from documents.workspace import (
    BatchIssue,
    DEP_EXTENSION,
    Document,
    PackageFiles,
    _encodable,
```

Edit: `client/documents/workspace_service.py`

```python
    def package_path(self, name: str) -> Path:
        return document_package_path_for_name(name, self._workspace_dir)

    def _remember(self, document: Document) -> None:
        """Record ``document`` as its package holds it now, right after a write or a load."""
        fingerprint = _package_fingerprint(self.package_path(document.name))
```

```python
    def package_path(self, name: str) -> Path:
        return document_package_path_for_name(name, self._workspace_dir)

    def package_name_taken(self, name: str, *, exclude_name: str | None = None) -> bool:
        """Whether something is on disk at ``name``'s package path (F-8 D1).

        A listed package, one that is not listed, a folder or a broken link all count; on
        a case-insensitive file system any spelling does. ``exclude_name`` is a Rename's
        own document: a name equal to it ignoring case is never taken.
        """
        if exclude_name is not None and name.casefold() == exclude_name.casefold():
            return False
        return os.path.lexists(self.package_path(name))

    def free_document_name(self, base: str) -> str:
        """``base`` if no document and no package has it, else ``"base (2)"``, ``"base (3)"``... (F-8 D2)."""
        name = base
        number = 1
        while self._controller.document_name_exists(name) or self.package_name_taken(name):
            number += 1
            name = f"{base} ({number})"
        return name

    def _remember(self, document: Document) -> None:
        """Record ``document`` as its package holds it now, right after a write or a load."""
        fingerprint = _package_fingerprint(self.package_path(document.name))
```

Edit: `client/documents/workspace_service.py`

```python
        return updated_document

    def create_document(self, document: Document) -> None:
        save_document_package(self.package_path(document.name), document)
        self._remember(document)
        self._controller.add_document(document)

    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult:
        documents, load_issues = batch_import_documents(
            list(paths),
            format_key=format_key,
            existing_names=set(self._controller.document_names),
        )
        saved: list[Document] = []
        save_issues: list[BatchIssue] = []
```

```python
        return updated_document

    def create_document(self, document: Document) -> None:
        package_path = self.package_path(document.name)
        if os.path.lexists(package_path):
            # Created after the name was checked, or never listed (F-8 D1): not replaced.
            raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(package_path))
        save_document_package(package_path, document)
        self._remember(document)
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

Edit: `client/gui.py`

```python
				if dialog.ShowModal() != wx.ID_OK:
					return None
				document_name = normalize_document_name(dialog.get_document_name())
			if self._document_controller.document_name_exists(document_name, exclude_name=exclude_name):
				message_box(
					_('Document "{name}" already exists.').format(name=document_name),
					_("Error"),
```

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
```

Edit: `client/gui.py`

```python
	def _create_default_document(self) -> bool:
		default_document = create_default_document()
		return self._create_document(
			DEFAULT_DOCUMENT_NAME,
			default_document.text,
			default_document.braille,
			focus_input=True,
```

```python
	def _create_default_document(self) -> bool:
		default_document = create_default_document()
		return self._create_document(
			# "new (2)", "new (3)", ... when a package that is not listed holds "new" (F-8).
			self._workspace_service.free_document_name(DEFAULT_DOCUMENT_NAME),
			default_document.text,
			default_document.braille,
			focus_input=True,
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(move_onto_an_existing_third_file_puts_the_old_package_back|case_only_move_on_the_case_insensitive_model_is_not_refused|create_document_refuses_a_package_that_is_not_listed|rename_onto_a_package_that_is_not_listed_keeps_both_files|import_treats_packages_on_disk_as_existing|package_name_taken|free_document_name|add_of_a_name_whose_package_is_on_disk_asks_again|rename_to_a_name_whose_package_is_on_disk_asks_again|startup_with_only_a_kept_invalid_new_package_creates_new_2) " | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_case_only_move_on_the_case_insensitive_model_is_not_refused ok
test_move_onto_an_existing_third_file_puts_the_old_package_back ok
test_create_document_refuses_a_package_that_is_not_listed ok
test_free_document_name ok
test_import_treats_packages_on_disk_as_existing ok
test_package_name_taken ok
test_rename_onto_a_package_that_is_not_listed_keeps_both_files ok
test_add_of_a_name_whose_package_is_on_disk_asks_again ok
test_rename_to_a_name_whose_package_is_on_disk_asks_again ok
test_startup_with_only_a_kept_invalid_new_package_creates_new_2 ok
Ran 310 tests
OK (skipped=2)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1378 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/full_disk.py client/tests/test_document_workspace.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py client/documents/workspace.py client/documents/workspace_service.py client/gui.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: never replace a document package that is not listed (F-8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/documents/workspace.py           |   7 ++
 client/documents/workspace_service.py   |  33 ++++++++-
 client/gui.py                           |   8 ++-
 client/tests/full_disk.py               |  81 ++++++++++++++++++++++
 client/tests/test_document_workspace.py |  29 ++++++++
 client/tests/test_gui_document_flows.py | 115 ++++++++++++++++++++++++++++----
 client/tests/test_workspace_service.py  | 112 ++++++++++++++++++++++++++++---
 7 files changed, 360 insertions(+), 25 deletions(-)
90a71c133ec42145605ea30e3f4ae07d916a6c71
```

### Task 2: Write the text-processing script and dictionary files atomically (D6, D7)

- [ ] **Step 1: Red: A1-A3, A5-A9; A4's patch target.** `test_user_preprocessing_script.py` gets A1-A3, and `test_save_uses_utf8_and_atomic_replace` (A4) patches `os.replace` itself, because `user_script` will no longer import `os`; it passes before and after. `test_dictionary_manager.py` gets A5-A9. Both files use 4 spaces. A3 and A9 run on Windows only.

Edit: `client/tests/test_user_preprocessing_script.py`

```python
import os
import tempfile
import unittest
```

```python
import errno
import os
import tempfile
import unittest
```

Edit: `client/tests/test_user_preprocessing_script.py`

```python
    save_preprocessing_script,
    validate_preprocessing_script,
)


class UserPreprocessingScriptTest(unittest.TestCase):
```

```python
    save_preprocessing_script,
    validate_preprocessing_script,
)
from tests.full_disk import full_disk
from tests.windows_file_handles import make_read_only


class UserPreprocessingScriptTest(unittest.TestCase):
```

Edit: `client/tests/test_user_preprocessing_script.py`

```python

    def test_save_uses_utf8_and_atomic_replace(self) -> None:
        source = "def main(text):\n    return text + '臺灣'\n"
        with patch("conversion.preprocessing.user_script.os.replace", wraps=os.replace) as replace:
            save_preprocessing_script(self.path, source)
        self.assertEqual(self.path.read_text(encoding="utf-8"), source)
        replace.assert_called_once()
        self.assertEqual(list(self.directory.glob(".preprocessing.py.*.tmp")), [])

    def test_invalid_save_does_not_overwrite_existing_file(self) -> None:
        original = "def main(text):\n    return text\n"
```

```python

    def test_save_uses_utf8_and_atomic_replace(self) -> None:
        source = "def main(text):\n    return text + '臺灣'\n"
        with patch("os.replace", wraps=os.replace) as replace:
            save_preprocessing_script(self.path, source)
        self.assertEqual(self.path.read_text(encoding="utf-8"), source)
        replace.assert_called_once()
        self.assertEqual(list(self.directory.glob(".preprocessing.py.*.tmp")), [])

    def _temporary_files(self) -> list[str]:
        return sorted(path.name for path in self.directory.iterdir() if path.name.endswith(".tmp"))

    def test_save_installs_through_the_shared_atomic_writer(self) -> None:
        # F-8 (D6): synced before the replace, through the temporary-file name of
        # shared.atomic_write (16 hex digits).
        source = "def main(text):\r\n    return text\n"
        with patch("shared.atomic_write.os.fsync", wraps=os.fsync) as fsync, patch("os.replace", wraps=os.replace) as replace:
            save_preprocessing_script(self.path, source)

        fsync.assert_called_once()
        replace.assert_called_once()
        self.assertRegex(Path(replace.call_args.args[0]).name, r"^\.preprocessing\.py\.[0-9a-f]{16}\.tmp$")
        self.assertEqual(self.path.read_bytes(), source.encode("utf-8"))
        self.assertEqual(self._temporary_files(), [])

    def test_write_error_leaves_no_temporary_file_and_keeps_the_script(self) -> None:
        old = b"def main(text):\n    return text\n"
        self.path.write_bytes(old)

        with full_disk(self.directory, after=10), self.assertRaises(OSError) as raised:
            save_preprocessing_script(self.path, "def main(text):\n    return text.upper()\n")

        self.assertEqual(raised.exception.errno, errno.ENOSPC)
        self.assertEqual(self.path.read_bytes(), old)
        self.assertEqual(self._temporary_files(), [])

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_read_only_script_is_refused_with_the_in_place_verdict(self) -> None:
        # F-8 (D6): the message names the script, as an in-place write would (F-3 D3).
        old = b"def main(text):\n    return text\n"
        self.path.write_bytes(old)
        make_read_only(self, self.path)

        with self.assertRaises(PermissionError) as raised:
            save_preprocessing_script(self.path, "def main(text):\n    return text.upper()\n")

        self.assertEqual(Path(raised.exception.filename).name, "preprocessing.py")
        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), old)
        self.assertEqual(self._temporary_files(), [])

    def test_invalid_save_does_not_overwrite_existing_file(self) -> None:
        original = "def main(text):\n    return text\n"
```

Edit: `client/tests/test_dictionary_manager.py`

```python
import csv
import tempfile
import unittest
from pathlib import Path

from shared import name_validation
from dictionaries.entries import DictionaryEntry, load_dictionary_entries
```

```python
import csv
import errno
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shared import name_validation
from dictionaries.entries import DictionaryEntry, load_dictionary_entries
```

Edit: `client/tests/test_dictionary_manager.py`

```python
    rename_dictionary,
    validate_dictionary_csv,
)
from tests.unreadable_dictionary_files import ASCII_ROWS, FIELD_LIMIT, LATE_BIG5, TAIPEI_ROW

WRONG_HEADER_LATE_BIG5 = b"x,y,z\r\n" + ASCII_ROWS.encode("ascii") + TAIPEI_ROW.encode("cp950")


class DictionaryManagerTest(unittest.TestCase):
```

```python
    rename_dictionary,
    validate_dictionary_csv,
)
from tests.full_disk import full_disk
from tests.unreadable_dictionary_files import ASCII_ROWS, FIELD_LIMIT, LATE_BIG5, TAIPEI_ROW
from tests.windows_file_handles import SHARE_READ_WRITE, hold_open

WRONG_HEADER_LATE_BIG5 = b"x,y,z\r\n" + ASCII_ROWS.encode("ascii") + TAIPEI_ROW.encode("cp950")
# A dictionary as Excel saves it: a UTF-8 BOM, CRLF and CJK text (F-8).
EXCEL_DICTIONARY = b"\xef\xbb\xbf" + "text,braille,type\r\n臺灣,⠞⠺,General\r\n".encode("utf-8")


class DictionaryManagerTest(unittest.TestCase):
```

Edit: `client/tests/test_dictionary_manager.py`

```python

        self.assertEqual(list(self.dictionary_dir.iterdir()), [])

    def test_rename_dictionary_renames_file_and_preserves_contents(self) -> None:
        source_path = create_dictionary(self.dictionary_dir, "math")
        with source_path.open("a", newline="", encoding="utf-8") as f:
```

```python

        self.assertEqual(list(self.dictionary_dir.iterdir()), [])

    # --- atomic writes (F-8, D7) -------------------------------------------

    def _temporary_files(self, folder: Path) -> list[str]:
        return sorted(path.name for path in folder.iterdir() if path.name.endswith(".tmp"))

    def test_header_writers_install_through_a_synced_temporary_file(self) -> None:
        writers = (
            ("ensure_default_dictionary", lambda: ensure_default_dictionary(self.dictionary_dir)),
            ("create_dictionary", lambda: create_dictionary(self.dictionary_dir, "math")),
        )
        for label, write in writers:
            with self.subTest(label):
                with patch("os.fsync", wraps=os.fsync) as fsync:
                    path = write()

                fsync.assert_called_once()
                self.assertEqual(path.read_bytes(), b"text,braille,type\r\n")
                self.assertEqual(self._temporary_files(self.dictionary_dir), [])

    def test_import_copy_failure_leaves_no_dictionary(self) -> None:
        ensure_default_dictionary(self.dictionary_dir)
        source_path = Path(self._tmpdir.name) / "excel.csv"
        source_path.write_bytes(EXCEL_DICTIONARY)

        with full_disk(self.dictionary_dir, after=8), self.assertRaises(OSError) as raised:
            import_dictionary(self.dictionary_dir, source_path, "science")

        self.assertEqual(raised.exception.errno, errno.ENOSPC)
        self.assertEqual(list_dictionary_names(self.dictionary_dir), ["default"])
        self.assertEqual(self._temporary_files(self.dictionary_dir), [])

    def _export_folder_with_old_file(self) -> Path:
        create_dictionary(self.dictionary_dir, "math").write_bytes(EXCEL_DICTIONARY)
        export_dir = Path(self._tmpdir.name) / "export"
        export_dir.mkdir()
        (export_dir / "math.csv").write_bytes(b"OLD")
        return export_dir

    def test_export_failure_keeps_the_existing_destination(self) -> None:
        export_dir = self._export_folder_with_old_file()

        with full_disk(export_dir, after=8), self.assertRaises(OSError) as raised:
            export_dictionary(self.dictionary_dir, "math", export_dir / "math.csv")

        self.assertEqual(raised.exception.errno, errno.ENOSPC)
        self.assertEqual((export_dir / "math.csv").read_bytes(), b"OLD")
        self.assertEqual(self._temporary_files(export_dir), [])

    def test_export_copies_the_same_bytes(self) -> None:
        export_dir = self._export_folder_with_old_file()

        export_dictionary(self.dictionary_dir, "math", export_dir / "math.csv")

        self.assertEqual((export_dir / "math.csv").read_bytes(), EXCEL_DICTIONARY)
        self.assertEqual(self._temporary_files(export_dir), [])

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_export_onto_a_destination_held_open_keeps_it(self) -> None:
        # Replacing a file needs its holder to share delete access; an editor that shares
        # reading and writing does not, so the export fails instead of writing under it.
        export_dir = self._export_folder_with_old_file()
        release = hold_open(self, export_dir / "math.csv", SHARE_READ_WRITE)

        try:
            with self.assertRaises(PermissionError) as raised:
                export_dictionary(self.dictionary_dir, "math", export_dir / "math.csv")
        finally:
            # Before tearDown removes the folder.
            release()

        self.assertEqual(raised.exception.winerror, 5)
        self.assertEqual((export_dir / "math.csv").read_bytes(), b"OLD")
        self.assertEqual(self._temporary_files(export_dir), [])

    def test_rename_dictionary_renames_file_and_preserves_contents(self) -> None:
        source_path = create_dictionary(self.dictionary_dir, "math")
        with source_path.open("a", newline="", encoding="utf-8") as f:
```

```bash
$PY -m unittest tests.test_user_preprocessing_script tests.test_dictionary_manager 2>&1 | $PY $T/tools/brief.py
```

Expected (A1 and A5 (both subtests): no `fsync`; A2: the `.tmp` of `NamedTemporaryFile` stays after the write error; A3: the old message names the temporary file; A6: a partial `science.csv` is listed; A7: the existing export is truncated to the 8 bytes written; A9: the export succeeds under an editor's handle. A8 passes):

```text
FAIL: test_read_only_script_is_refused_with_the_in_place_verdict (tests.test_user_preprocessing_script.UserPreprocessingScriptTest.test_read_only_script_is_refu
AssertionError: '.preprocessing.py.<rnd>.tmp' != 'preprocessing.py'
FAIL: test_save_installs_through_the_shared_atomic_writer (tests.test_user_preprocessing_script.UserPreprocessingScriptTest.test_save_installs_through_the_share
AssertionError: Expected 'fsync' to have been called once. Called 0 times.
FAIL: test_write_error_leaves_no_temporary_file_and_keeps_the_script (tests.test_user_preprocessing_script.UserPreprocessingScriptTest.test_write_error_leaves_n
AssertionError: Lists differ: ['.preprocessing.py.<rnd>.tmp'] != []
FAIL: test_export_failure_keeps_the_existing_destination (tests.test_dictionary_manager.DictionaryManagerTest.test_export_failure_keeps_the_existing_destination
AssertionError: b'\xef\xbb\xbftext,' != b'OLD'
FAIL: test_export_onto_a_destination_held_open_keeps_it (tests.test_dictionary_manager.DictionaryManagerTest.test_export_onto_a_destination_held_open_keeps_it)
AssertionError: PermissionError not raised
FAIL: test_header_writers_install_through_a_synced_temporary_file (tests.test_dictionary_manager.DictionaryManagerTest.test_header_writers_install_through_a_syn
FAIL: test_import_copy_failure_leaves_no_dictionary (tests.test_dictionary_manager.DictionaryManagerTest.test_import_copy_failure_leaves_no_dictionary)
AssertionError: Lists differ: ['default', 'science'] != ['default']
Ran 35 tests
FAILED (failures=8)
```

- [ ] **Step 2: Green: the script and the dictionary files through `shared.atomic_write`.** Both files use 4 spaces.

Edit: `client/conversion/preprocessing/user_script.py`

```python
from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path

from i18n import N_


PREPROCESSING_FILENAME = "preprocessing.py"
```

```python
from __future__ import annotations

import ast
from pathlib import Path

from i18n import N_
from shared.atomic_write import write_text_atomically


PREPROCESSING_FILENAME = "preprocessing.py"
```

Edit: `client/conversion/preprocessing/user_script.py`

```python


def save_preprocessing_script(path: Path | str, source: str) -> None:
    destination = Path(path)
    validate_preprocessing_script(source, filename=str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(source)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def execute_preprocessing_script(path: Path | str, input_text: str) -> str:
```

```python


def save_preprocessing_script(path: Path | str, source: str) -> None:
    """Validate ``source`` and write it to ``path`` through a synced temporary file (F-8).

    The text is written as is (no newline translation). On an error the script keeps
    its bytes and no temporary file is left.
    """
    destination = Path(path)
    validate_preprocessing_script(source, filename=str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomically(destination, lambda stream: stream.write(source), encoding="utf-8", newline="")


def execute_preprocessing_script(path: Path | str, input_text: str) -> str:
```

Edit: `client/dictionaries/manager.py`

```python
from __future__ import annotations

import csv
from pathlib import Path
import shutil

from shared.name_validation import MAX_NAME_LENGTH, normalize_base_name

DEFAULT_DICTIONARY_NAME = "default"
```

```python
"""The dictionary files: create, import, rename, export, delete.

Every file this module writes goes through ``shared.atomic_write`` (F-8): a failed
write leaves the target as it was (or absent) and no temporary file.
"""

from __future__ import annotations

import csv
from pathlib import Path
import shutil
from typing import BinaryIO, TextIO

from shared.atomic_write import write_bytes_atomically, write_text_atomically
from shared.name_validation import MAX_NAME_LENGTH, normalize_base_name

DEFAULT_DICTIONARY_NAME = "default"
```

Edit: `client/dictionaries/manager.py`

```python
    return Path(dictionary_dir) / f"{name}.csv"


def ensure_default_dictionary(dictionary_dir: Path) -> Path:
    directory = Path(dictionary_dir)
    directory.mkdir(parents=True, exist_ok=True)
    default_path = directory / f"{DEFAULT_DICTIONARY_NAME}.csv"
    if not default_path.exists():
        with default_path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow(DEFAULT_HEADER)
    return default_path


```

```python
    return Path(dictionary_dir) / f"{name}.csv"


def _write_header(stream: TextIO) -> None:
    csv.writer(stream).writerow(DEFAULT_HEADER)


def _copy_file_into(source: Path, stream: BinaryIO) -> None:
    """Copy the bytes of ``source`` into ``stream``; an error opening or reading it is raised."""
    with open(source, "rb") as source_stream:
        shutil.copyfileobj(source_stream, stream)


def ensure_default_dictionary(dictionary_dir: Path) -> Path:
    directory = Path(dictionary_dir)
    directory.mkdir(parents=True, exist_ok=True)
    default_path = directory / f"{DEFAULT_DICTIONARY_NAME}.csv"
    if not default_path.exists():
        write_text_atomically(default_path, _write_header, encoding="utf-8", newline="")
    return default_path


```

Edit: `client/dictionaries/manager.py`

```python
    path = directory / f"{normalized}.csv"
    if path.exists():
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(DEFAULT_HEADER)
    return path


```

```python
    path = directory / f"{normalized}.csv"
    if path.exists():
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    write_text_atomically(path, _write_header, encoding="utf-8", newline="")
    return path


```

Edit: `client/dictionaries/manager.py`

```python
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    source = Path(source_path)
    validate_dictionary_csv(source)
    shutil.copyfile(source, destination_path)
    return destination_path


```

```python
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    source = Path(source_path)
    validate_dictionary_csv(source)
    write_bytes_atomically(destination_path, lambda stream: _copy_file_into(source, stream))
    return destination_path


```

Edit: `client/dictionaries/manager.py`

```python
def export_dictionary(dictionary_dir: Path, name: str, destination_path: Path | str) -> Path:
    source_path = dictionary_path_for_name(name.strip(), dictionary_dir)
    destination = Path(destination_path)
    shutil.copyfile(source_path, destination)
    return destination


```

```python
def export_dictionary(dictionary_dir: Path, name: str, destination_path: Path | str) -> Path:
    source_path = dictionary_path_for_name(name.strip(), dictionary_dir)
    destination = Path(destination_path)
    # An existing file there is replaced only once the copy is complete and synced.
    write_bytes_atomically(destination, lambda stream: _copy_file_into(source_path, stream))
    return destination


```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_user_preprocessing_script tests.test_dictionary_manager -v 2>&1 | grep -E "^test_(save_installs_through_the_shared_atomic_writer|write_error_leaves_no_temporary_file_and_keeps_the_script|read_only_script_is_refused_with_the_in_place_verdict|header_writers_install_through_a_synced_temporary_file|import_copy_failure_leaves_no_dictionary|export_failure_keeps_the_existing_destination|export_copies_the_same_bytes|export_onto_a_destination_held_open_keeps_it) " | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_user_preprocessing_script tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_settings_dialogs 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_read_only_script_is_refused_with_the_in_place_verdict ok
test_save_installs_through_the_shared_atomic_writer ok
test_write_error_leaves_no_temporary_file_and_keeps_the_script ok
test_export_copies_the_same_bytes ok
test_export_failure_keeps_the_existing_destination ok
test_export_onto_a_destination_held_open_keeps_it ok
test_header_writers_install_through_a_synced_temporary_file ok
test_import_copy_failure_leaves_no_dictionary ok
Ran 159 tests
OK (skipped=1)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1386 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_user_preprocessing_script.py client/tests/test_dictionary_manager.py client/conversion/preprocessing/user_script.py client/dictionaries/manager.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: write the text-processing script and dictionary files atomically (F-8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/conversion/preprocessing/user_script.py | 27 +++------
 client/dictionaries/manager.py                 | 31 +++++++---
 client/tests/test_dictionary_manager.py        | 81 ++++++++++++++++++++++++++
 client/tests/test_user_preprocessing_script.py | 47 ++++++++++++++-
 4 files changed, 157 insertions(+), 29 deletions(-)
adcfa53378542f878db2fc2ac8c0626576c67a6d
```

### Task 3: Keep the previous export when an export fails (D8)

- [ ] **Step 1: Red: A10-A12.** `test_document_workspace.py` gets A10 (the BRL writer), `test_document_formats.py` A11 and A12 (through `get_format(...).writer`, as the export coordinator calls them). Both files use 4 spaces.

Edit: `client/tests/test_document_workspace.py`

```python
        output_path = self.workspace_dir / "lesson1.brl"
        export_document_brl(output_path, document)
        self.assertEqual(output_path.read_text(encoding="utf-8"), "⠇⠑⠎⠎")

    def test_batch_import_documents_imports_txt_only_and_reports_duplicates(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
```

```python
        output_path = self.workspace_dir / "lesson1.brl"
        export_document_brl(output_path, document)
        self.assertEqual(output_path.read_text(encoding="utf-8"), "⠇⠑⠎⠎")

    def test_brl_export_failure_keeps_the_existing_file(self) -> None:
        # F-8 (D8): the in-place write emptied an existing export before it failed. Here
        # the encoder fails part way (a lone surrogate in the braille).
        self.workspace_dir.mkdir(parents=True)
        output_path = self.workspace_dir / "lesson1.brl"
        output_path.write_bytes(b"OLD GOOD EXPORT")
        document = Document(name="lesson1", text="source", braille="⠇⠑" + chr(0xD800) + "⠎")

        with self.assertRaises(UnicodeEncodeError):
            export_document_brl(output_path, document)

        self.assertEqual(output_path.read_bytes(), b"OLD GOOD EXPORT")
        self.assertEqual(sorted(path.name for path in self.workspace_dir.iterdir()), ["lesson1.brl"])

    def test_batch_import_documents_imports_txt_only_and_reports_duplicates(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
```

Edit: `client/tests/test_document_formats.py`

```python
import inspect
import unittest
import zipfile
from pathlib import Path
```

```python
import errno
import inspect
import os
import unittest
import zipfile
from pathlib import Path
```

Edit: `client/tests/test_document_formats.py`

```python
    get_importable_formats,
)
from documents.workspace import Document


class DocumentFormatsTest(unittest.TestCase):
```

```python
    get_importable_formats,
)
from documents.workspace import Document
from tests.full_disk import full_disk


class DocumentFormatsTest(unittest.TestCase):
```

Edit: `client/tests/test_document_formats.py`

```python

            self.assertEqual(destination.read_text(encoding="utf-8"), "雙視內容")
            render.assert_called_once()

    def test_writers_take_path_document_and_context(self) -> None:
        for descriptor in get_exportable_formats():
```

```python

            self.assertEqual(destination.read_text(encoding="utf-8"), "雙視內容")
            render.assert_called_once()

    def test_html_export_failure_keeps_the_existing_file(self) -> None:
        # F-8 (D8): the page is rendered first; a write that failed part way left the
        # first part of the page in place of the old file.
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "alpha.html"
            destination.write_bytes(b"OLD GOOD EXPORT")
            with patch("documents.formats.render_dual_view_html", return_value="<p>雙視</p>\n<p>內容</p>\n"):
                with full_disk(directory, after=5), self.assertRaises(OSError) as raised:
                    get_format("html").writer(destination, Document("alpha", "a", "1"), ExportContext())

            self.assertEqual(raised.exception.errno, errno.ENOSPC)
            self.assertEqual(destination.read_bytes(), b"OLD GOOD EXPORT")
            self.assertEqual(sorted(path.name for path in Path(directory).iterdir()), ["alpha.html"])

    def test_exports_keep_their_crlf_bytes(self) -> None:
        # F-8 (D8): the atomic writes translate newlines as Path.write_text did (CRLF on Windows).
        text = "line 1\nline 2\n"
        with TemporaryDirectory() as directory:
            for key in ("brl", "html"):
                with self.subTest(key):
                    destination = Path(directory) / f"alpha.{key}"
                    with patch("documents.formats.render_dual_view_html", return_value=text):
                        get_format(key).writer(destination, Document("alpha", "a", text), ExportContext())

                    self.assertEqual(destination.read_bytes(), text.replace("\n", os.linesep).encode("utf-8"))

    def test_writers_take_path_document_and_context(self) -> None:
        for descriptor in get_exportable_formats():
```

```bash
$PY -m unittest tests.test_document_workspace tests.test_document_formats 2>&1 | $PY $T/tools/brief.py
```

Expected (A10: the in-place write emptied the old export, as the spec measured; A11: the first five characters of the page replaced it. A12 passes: the bytes do not change):

```text
FAIL: test_brl_export_failure_keeps_the_existing_file (tests.test_document_workspace.DocumentWorkspaceTest.test_brl_export_failure_keeps_the_existing_file)
AssertionError: b'' != b'OLD GOOD EXPORT'
FAIL: test_html_export_failure_keeps_the_existing_file (tests.test_document_formats.DocumentFormatsTest.test_html_export_failure_keeps_the_existing_file)
AssertionError: b'<p>\xe9\x9b\x99\xe8\xa6\x96' != b'OLD GOOD EXPORT'
Ran 75 tests
FAILED (failures=2, skipped=2)
```

- [ ] **Step 2: Green: `write_export_text` for BRL and HTML (Spec Corrections 6).** Both files use 4 spaces.

Edit: `client/documents/workspace.py`

```python
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
from shared.atomic_write import ensure_writable, write_bytes_atomically
from shared.name_validation import normalize_base_name

DEP_EXTENSION = ".dep"
```

```python
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
from shared.atomic_write import ensure_writable, write_bytes_atomically, write_text_atomically
from shared.name_validation import normalize_base_name

DEP_EXTENSION = ".dep"
```

Edit: `client/documents/workspace.py`

```python
}


def export_document_brl(path: Path | str, document: Document) -> Path:
    destination_path = Path(path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(document.braille or "", encoding="utf-8")
    return destination_path


```

```python
}


def write_export_text(path: Path | str, text: str) -> None:
    """Write an exported file through a synced temporary file (F-8).

    Newlines are translated as ``Path.write_text`` did (CRLF on Windows), so the bytes do
    not change. On an error an existing file keeps its bytes and no temporary file is
    left. A folder at ``path`` fails with the error an in-place write gives, as exports
    always reported it, not with a failed replace that names the temporary file.
    """
    destination = Path(path)
    if destination.is_dir():
        if os.name == "nt":
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(destination))
        raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(destination))
    write_text_atomically(destination, lambda stream: stream.write(text), encoding="utf-8", newline=None)


def export_document_brl(path: Path | str, document: Document) -> Path:
    destination_path = Path(path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    write_export_text(destination_path, document.braille or "")
    return destination_path


```

Edit: `client/documents/formats.py`

```python

def _write_html(path: Path | str, document: Document, context: ExportContext) -> Path:
    del document
    destination = Path(path)
    html = render_dual_view_html(build_dual_view_model(context.dual_view_results, mathml_converter=latex_to_mathml))
    destination.write_text(html, encoding="utf-8")
    return destination


```

```python

def _write_html(path: Path | str, document: Document, context: ExportContext) -> Path:
    del document
    from documents.workspace import write_export_text

    destination = Path(path)
    html = render_dual_view_html(build_dual_view_model(context.dual_view_results, mathml_converter=latex_to_mathml))
    write_export_text(destination, html)
    return destination


```

- [ ] **Step 3: Green.** The export coordinator tests and the frame's export tests pin today's message for a folder at the destination (`[Errno 13] Permission denied: '<path>'`) and the real writers' bytes; they pass unchanged.

```bash
$PY -m unittest tests.test_document_workspace tests.test_document_formats -v 2>&1 | grep -E "^test_(brl_export_failure_keeps_the_existing_file|html_export_failure_keeps_the_existing_file|exports_keep_their_crlf_bytes) " | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_document_workspace tests.test_document_formats tests.test_export_coordinator tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_brl_export_failure_keeps_the_existing_file ok
test_exports_keep_their_crlf_bytes ok
test_html_export_failure_keeps_the_existing_file ok
Ran 296 tests
OK (skipped=2)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1389 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_document_workspace.py client/tests/test_document_formats.py client/documents/workspace.py client/documents/formats.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: keep the previous export when an export fails (F-8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/documents/formats.py             |  4 +++-
 client/documents/workspace.py           | 20 ++++++++++++++++++--
 client/tests/test_document_formats.py   | 29 +++++++++++++++++++++++++++++
 client/tests/test_document_workspace.py | 14 ++++++++++++++
 4 files changed, 64 insertions(+), 3 deletions(-)
12837b650949f046c76ccf5b0fa2b76c927f4910
```

### Task 4: Write config.json atomically and never discard an unusable one (D9-D11)

- [ ] **Step 1: Red: A13-A15, B1-B7.** `test_config.py` (4 spaces) isolates `dotexpress.config` for the module (Spec Corrections 9) and gets the class `ConfigDataSafetyTest`. A15 runs on Windows only.

Edit: `client/tests/test_config.py`

```python
import json
import logging
import os
```

```python
import errno
import json
import logging
import os
```

Edit: `client/tests/test_config.py`

```python
from uuid import UUID

import config


class ConfigTest(unittest.TestCase):
```

```python
from uuid import UUID

import config
from tests.file_log_isolation import isolate_file_logs
from tests.full_disk import full_disk


def setUpModule() -> None:
    # A test that makes config.py log outside assertLogs must not append to the real
    # log/config.log (F-8); assertLogs still captures the records.
    unittest.addModuleCleanup(isolate_file_logs("dotexpress.config"))


class ConfigTest(unittest.TestCase):
```

Edit: `client/tests/test_config.py`

```python
        )


class ConfigModuleShapeTest(unittest.TestCase):
    """P2-6: config IO lives on ``ConfigStore``; the module holds no path and no IO functions."""

```

```python
        )


GOOD_CONFIG = b'{"view": {"font_size": 20}, "conversion": {"width": 30}}'


class ConfigDataSafetyTest(unittest.TestCase):
    """F-8 (D9-D11): config.json is written atomically and an unusable one is never silently discarded."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.directory = Path(temp_dir.name)
        self.path = self.directory / "config.json"
        self.backup = self.directory / "config.json.bak"
        self.store = config.ConfigStore(self.path)
        config._logged_load_failures.clear()
        self.addCleanup(config._logged_load_failures.clear)

    def _listing(self) -> list[str]:
        return sorted(os.listdir(self.directory))

    def _saved(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _backup_bytes(self) -> bytes | None:
        return self.backup.read_bytes() if self.backup.exists() else None

    # --- atomic save (D9) --------------------------------------------------

    def test_save_installs_through_a_synced_temporary_file(self) -> None:
        with patch("os.fsync", wraps=os.fsync) as fsync:
            self.store.set_output_mode("ascii")
            self.store.set_conversion_width(52)

        self.assertEqual(fsync.call_count, 2)
        self.assertEqual(self._listing(), ["config.json"])
        self.assertEqual(self._saved()["conversion"], {"output_mode": "ascii", "width": 52})

    def test_save_failure_keeps_the_previous_file(self) -> None:
        self.path.write_bytes(GOOD_CONFIG)

        with full_disk(self.directory, after=10), self.assertLogs("dotexpress.config", level="ERROR") as captured:
            self.store.set_output_mode("ascii")

        self.assertEqual(self.path.read_bytes(), GOOD_CONFIG)
        self.assertEqual(self._listing(), ["config.json"])
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].getMessage(), f"Failed to save config file {self.path}")

    @unittest.skipUnless(os.name == "nt", "Windows line ends")
    def test_saved_bytes_use_crlf_on_windows(self) -> None:
        self.store.set_view_settings(18, "dark", "default")

        expected = {
            "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
            "view": {"font_size": 18, "scheme": "dark", "braille_font": "default"},
        }
        self.assertEqual(
            self.path.read_bytes(),
            json.dumps(expected, ensure_ascii=False, indent=2).replace("\n", "\r\n").encode("utf-8"),
        )

    # --- load (D10) --------------------------------------------------------

    def test_a_utf8_bom_is_read(self) -> None:
        # Older Notepad writes "UTF-8" with a BOM.
        self.path.write_bytes(b"\xef\xbb\xbf" + GOOD_CONFIG)

        with patch.object(config, "logger") as logger:
            self.assertEqual(self.store.get_view_font_size(), 20)
            self.assertEqual(self.store.get_conversion_width(), 30)

        self.assertEqual(logger.mock_calls, [])

    def test_json_that_is_not_an_object_gives_defaults_and_one_warning(self) -> None:
        # Before, every getter raised AttributeError, and the app did not start.
        for content, type_name in ((b"null", "NoneType"), (b"[1, 2]", "list"), (b'"text"', "str"), (b"3", "int")):
            with self.subTest(content=content):
                self.path.write_bytes(content)

                with self.assertLogs("dotexpress.config", level="WARNING") as captured:
                    self.assertEqual(self.store.get_output_mode(), config.DEFAULT_OUTPUT_MODE)
                    self.assertEqual(self.store.get_view_font_size(), config.DEFAULT_VIEW_FONT_SIZE)

                self.assertEqual(len(captured.records), 1)
                self.assertEqual(captured.records[0].getMessage(), f"Failed to read config file {self.path}; using defaults")
                self.assertEqual(
                    str(captured.records[0].exc_info[1]),
                    f"config.json does not hold a JSON object ({type_name})",
                )

    # --- save after a failed load (D11) ------------------------------------

    def test_a_change_after_a_damaged_load_keeps_a_backup(self) -> None:
        cases = (
            ("truncated JSON", b'{"view": {"font_size": 2'),
            ("cp950 bytes", '{"language": "臺灣"}'.encode("cp950")),
            ("a list", b"[1, 2]"),
        )
        for label, content in cases:
            with self.subTest(label):
                self.path.write_bytes(content)
                self.backup.unlink(missing_ok=True)

                with self.assertLogs("dotexpress.config", level="WARNING"):
                    self.store.set_output_mode("ascii")

                self.assertEqual(self._backup_bytes(), content)
                self.assertEqual(self._saved(), {"conversion": {"output_mode": "ascii"}})
                self.assertEqual(self._listing(), ["config.json", "config.json.bak"])

    def test_a_second_backup_replaces_the_first(self) -> None:
        for content in (b"{first", b"[second"):
            self.path.write_bytes(content)
            with self.assertLogs("dotexpress.config", level="WARNING"):
                self.store.set_output_mode("ascii")

        self.assertEqual(self._backup_bytes(), b"[second")
        self.assertEqual(self._listing(), ["config.json", "config.json.bak"])

    def test_a_change_after_an_unreadable_load_does_not_write(self) -> None:
        # Locked or denied: the file still holds the user's settings, so it is kept.
        self.path.write_bytes(GOOD_CONFIG)
        real_open = open

        def open_denying_reads(file, mode="r", *args, **kwargs):
            if os.fspath(file) == str(self.path) and "r" in mode:
                raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(file))
            return real_open(file, mode, *args, **kwargs)

        with (
            patch("builtins.open", open_denying_reads),
            self.assertLogs("dotexpress.config", level="WARNING") as captured,
        ):
            self.store.set_output_mode("ascii")
            self.store.set_conversion_width(52)

        self.assertEqual(self.path.read_bytes(), GOOD_CONFIG)
        self.assertEqual(self._listing(), ["config.json"])
        refusals = [record for record in captured.records if "was not saved" in record.getMessage()]
        self.assertEqual(
            [(record.levelno, record.getMessage()) for record in refusals],
            [(logging.WARNING, f"Config file {self.path} was not saved because it could not be read")],
        )

    def test_a_failed_backup_prevents_the_write(self) -> None:
        self.path.write_bytes(b"{damaged")

        with (
            patch("config.write_bytes_atomically", side_effect=OSError(errno.ENOSPC, "injected"), create=True),
            self.assertLogs("dotexpress.config", level="WARNING") as captured,
        ):
            self.store.set_output_mode("ascii")

        self.assertEqual(self.path.read_bytes(), b"{damaged")
        self.assertEqual(self._listing(), ["config.json"])
        errors = [record for record in captured.records if record.levelno == logging.ERROR]
        self.assertEqual([record.getMessage() for record in errors], [f"Failed to save config file {self.path}"])
        self.assertEqual(str(errors[0].exc_info[1]), f"[Errno {errno.ENOSPC}] injected")

    def test_a_missing_file_is_created_without_backup(self) -> None:
        self.store.set_output_mode("ascii")

        self.assertEqual(self._listing(), ["config.json"])
        self.assertEqual(
            self._saved(),
            {
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                "conversion": {"output_mode": "ascii"},
            },
        )

    def test_a_good_file_is_updated_without_backup(self) -> None:
        self.path.write_bytes(GOOD_CONFIG)

        self.store.set_output_mode("ascii")

        self.assertEqual(self._listing(), ["config.json"])
        self.assertEqual(self._saved(), {"view": {"font_size": 20}, "conversion": {"width": 30, "output_mode": "ascii"}})


class ConfigModuleShapeTest(unittest.TestCase):
    """P2-6: config IO lives on ``ConfigStore``; the module holds no path and no IO functions."""

```

```bash
$PY -m unittest tests.test_config 2>&1 | $PY $T/tools/brief.py
```

Expected (B2 and B3's list subtest: every getter or setter raises `AttributeError` on a non-object; B3's other subtests, B4: no `.bak`; B5: the unreadable file is replaced by the one changed value; B6: the file is written although the backup fails; B1: the BOM file gives the default 12; A14: the in-place write left the first 10 characters; A13: no `fsync`. A15 and B7 pass):

```text
ERROR: test_a_change_after_a_damaged_load_keeps_a_backup (tests.test_config.ConfigDataSafetyTest.test_a_change_after_a_damaged_load_keeps_a_backup) [a list]
AttributeError: 'list' object has no attribute 'get'
ERROR: test_json_that_is_not_an_object_gives_defaults_and_one_warning (tests.test_config.ConfigDataSafetyTest.test_json_that_is_not_an_object_gives_defaults_and
AttributeError: 'NoneType' object has no attribute 'get'
AttributeError: 'str' object has no attribute 'get'
AttributeError: 'int' object has no attribute 'get'
FAIL: test_a_change_after_a_damaged_load_keeps_a_backup (tests.test_config.ConfigDataSafetyTest.test_a_change_after_a_damaged_load_keeps_a_backup) [truncated JS
AssertionError: None != b'{"view": {"font_size": 2'
FAIL: test_a_change_after_a_damaged_load_keeps_a_backup (tests.test_config.ConfigDataSafetyTest.test_a_change_after_a_damaged_load_keeps_a_backup) [cp950 bytes]
AssertionError: None != b'{"language": "\xbbO\xc6W"}'
FAIL: test_a_change_after_an_unreadable_load_does_not_write (tests.test_config.ConfigDataSafetyTest.test_a_change_after_an_unreadable_load_does_not_write)
AssertionError: b'{\r\n  "conversion": {\r\n    "width": 52\r\n  }\r\n}' != b'{"view": {"font_size": 20}, "conversion": {"width": 30}}'
FAIL: test_a_failed_backup_prevents_the_write (tests.test_config.ConfigDataSafetyTest.test_a_failed_backup_prevents_the_write)
AssertionError: b'{\r\n  "conversion": {\r\n    "output_mode": "ascii"\r\n  }\r\n}' != b'{damaged'
FAIL: test_a_second_backup_replaces_the_first (tests.test_config.ConfigDataSafetyTest.test_a_second_backup_replaces_the_first)
AssertionError: None != b'[second'
FAIL: test_a_utf8_bom_is_read (tests.test_config.ConfigDataSafetyTest.test_a_utf8_bom_is_read)
AssertionError: 12 != 20
FAIL: test_save_failure_keeps_the_previous_file (tests.test_config.ConfigDataSafetyTest.test_save_failure_keeps_the_previous_file)
AssertionError: b'{\r\n  "view"' != b'{"view": {"font_size": 20}, "conversion": {"width": 30}}'
FAIL: test_save_installs_through_a_synced_temporary_file (tests.test_config.ConfigDataSafetyTest.test_save_installs_through_a_synced_temporary_file)
AssertionError: 0 != 2
Ran 45 tests
FAILED (failures=8, errors=5)
```

- [ ] **Step 2: Green: `ConfigStore._load` and `_save`.** 4 spaces.

Edit: `client/config.py`

```python

from conversion.math_braille_codes import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES  # noqa: F401  (re-exported)
from log import get_logger

logger = get_logger("dotexpress.config", "config.log", level=logging.WARNING)

```

```python

from conversion.math_braille_codes import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES  # noqa: F401  (re-exported)
from log import get_logger
from shared.atomic_write import write_bytes_atomically, write_text_atomically

logger = get_logger("dotexpress.config", "config.log", level=logging.WARNING)

```

Edit: `client/config.py`

```python

# Config path -> signature of the last load failure that was logged for it.
_logged_load_failures: dict[str, str] = {}


def _log_current_exception(level: int, message: str, *args: object) -> None:
    try:
        logger.log(level, message, *args, exc_info=True)
    except OSError:
        # A delay=True FileHandler opens its file inside emit() and raises if
        # log/ is missing or unwritable. Config I/O must never raise, so a
```

```python

# Config path -> signature of the last load failure that was logged for it.
_logged_load_failures: dict[str, str] = {}
# Config path -> signature of the read error of the last save that was skipped for it (F-8).
_logged_skipped_saves: dict[str, str] = {}


def _signature(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


class _UnreadableConfig(dict):
    """The empty settings ``_load`` returns for a config.json it could not use (F-8).

    ``error`` is why: an ``OSError`` if the file could not be read, anything else if it
    was read but is not a JSON object. ``_save`` keeps the file accordingly.
    """

    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error


def _log_current_exception(level: int, message: str, *args: object, exc_info: object = True) -> None:
    try:
        logger.log(level, message, *args, exc_info=exc_info)
    except OSError:
        # A delay=True FileHandler opens its file inside emit() and raises if
        # log/ is missing or unwritable. Config I/O must never raise, so a
```

Edit: `client/config.py`

```python


class ConfigStore:
    """config.json at one path. Each getter re-reads the file; nothing is cached."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
```

```python


class ConfigStore:
    """config.json at one path. Each getter re-reads the file; nothing is cached.

    The file is written through a synced temporary file: a failed save leaves it as it
    was (F-8). It is read as UTF-8 with or without a BOM; a file that is not a JSON
    object counts as damaged and gives the defaults. A setting changed after a failed
    load never silently discards the file: one that could not be read is not written
    (the change lasts for this session), and a damaged one is first copied to
    ``config.json.bak``.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
```

Edit: `client/config.py`

```python
    def _load(self) -> dict:
        path = str(self._path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            _logged_load_failures.pop(path, None)
            return {}
        except Exception as error:
            signature = f"{type(error).__name__}: {error}"
            if _logged_load_failures.get(path) != signature:
                _logged_load_failures[path] = signature
                _log_current_exception(
```

```python
    def _load(self) -> dict:
        path = str(self._path)
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError(f"config.json does not hold a JSON object ({type(data).__name__})")
        except FileNotFoundError:
            _logged_load_failures.pop(path, None)
            _logged_skipped_saves.pop(path, None)
            return {}
        except Exception as error:
            signature = _signature(error)
            if _logged_load_failures.get(path) != signature:
                _logged_load_failures[path] = signature
                _log_current_exception(
```

Edit: `client/config.py`

```python
                    "Failed to read config file %s; using defaults",
                    path,
                )
            return {}
        _logged_load_failures.pop(path, None)
        return data

    def _save(self, data: dict) -> None:
        path = str(self._path)
        try:
            if not os.path.exists(path):
                data = {
                    "language_detection": {
```

```python
                    "Failed to read config file %s; using defaults",
                    path,
                )
            return _UnreadableConfig(error)
        _logged_load_failures.pop(path, None)
        _logged_skipped_saves.pop(path, None)
        return data

    def _skip_save_of_unreadable_file(self, error: OSError) -> None:
        """The file exists but could not be read: keep it, log once per distinct error."""
        path = str(self._path)
        signature = _signature(error)
        if _logged_skipped_saves.get(path) != signature:
            _logged_skipped_saves[path] = signature
            _log_current_exception(
                logging.WARNING,
                "Config file %s was not saved because it could not be read",
                path,
                exc_info=error,
            )

    def _backup_unreadable(self) -> None:
        """Copy the damaged file's bytes to config.json.bak, replacing an older one."""
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

Edit: `client/config.py`

```python
                    **data,
                }
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            _log_current_exception(logging.ERROR, "Failed to save config file %s", path)

```

```python
                    **data,
                }
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write_text_atomically(
                path,
                lambda stream: json.dump(data, stream, ensure_ascii=False, indent=2),
                encoding="utf-8",
                newline=None,
            )
        except Exception:
            _log_current_exception(logging.ERROR, "Failed to save config file %s", path)

```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_config -v 2>&1 | grep -E "^test_(save_installs_through_a_synced_temporary_file|save_failure_keeps_the_previous_file|saved_bytes_use_crlf_on_windows|a_utf8_bom_is_read|json_that_is_not_an_object_gives_defaults_and_one_warning|a_change_after_a_damaged_load_keeps_a_backup|a_second_backup_replaces_the_first|a_change_after_an_unreadable_load_does_not_write|a_failed_backup_prevents_the_write|a_missing_file_is_created_without_backup|a_good_file_is_updated_without_backup) " | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_config tests.test_client_init tests.test_settings_state tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_a_change_after_a_damaged_load_keeps_a_backup ok
test_a_change_after_an_unreadable_load_does_not_write ok
test_a_failed_backup_prevents_the_write ok
test_a_good_file_is_updated_without_backup ok
test_a_missing_file_is_created_without_backup ok
test_a_second_backup_replaces_the_first ok
test_a_utf8_bom_is_read ok
test_json_that_is_not_an_object_gives_defaults_and_one_warning ok
test_save_failure_keeps_the_previous_file ok
test_save_installs_through_a_synced_temporary_file ok
test_saved_bytes_use_crlf_on_windows ok
Ran 250 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1400 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_config.py client/config.py
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: write config.json atomically and never discard an unusable one (F-8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/config.py            |  74 +++++++++++++++--
 client/tests/test_config.py | 188 ++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 254 insertions(+), 8 deletions(-)
62ea9d3eadebd3064e70e675138c6a32c7543f7d
```

### Task 5: Verification (no commit)

`BASE` is `main` at `861d110`.

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = 1368 + 32; the error is F-W6):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1400 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 2: Criterion 2, focused modules; the 32 new tests ran and passed.** The verbose run is kept in `$T/verbose.txt`, so a failure there is named.

```bash
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_document_formats tests.test_export_coordinator tests.test_user_preprocessing_script tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_config tests.test_gui_document_flows tests.test_i18n tests.test_wx_call_sites 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_user_preprocessing_script tests.test_dictionary_manager tests.test_document_formats tests.test_config -v > $T/verbose.txt 2>&1; grep -cE "^test_(move_onto_an_existing_third_file_puts_the_old_package_back|case_only_move_on_the_case_insensitive_model_is_not_refused|create_document_refuses_a_package_that_is_not_listed|rename_onto_a_package_that_is_not_listed_keeps_both_files|import_treats_packages_on_disk_as_existing|package_name_taken|free_document_name|add_of_a_name_whose_package_is_on_disk_asks_again|rename_to_a_name_whose_package_is_on_disk_asks_again|startup_with_only_a_kept_invalid_new_package_creates_new_2|save_installs_through_the_shared_atomic_writer|write_error_leaves_no_temporary_file_and_keeps_the_script|read_only_script_is_refused_with_the_in_place_verdict|header_writers_install_through_a_synced_temporary_file|import_copy_failure_leaves_no_dictionary|export_failure_keeps_the_existing_destination|export_copies_the_same_bytes|export_onto_a_destination_held_open_keeps_it|brl_export_failure_keeps_the_existing_file|html_export_failure_keeps_the_existing_file|exports_keep_their_crlf_bytes|save_installs_through_a_synced_temporary_file|save_failure_keeps_the_previous_file|saved_bytes_use_crlf_on_windows|a_utf8_bom_is_read|json_that_is_not_an_object_gives_defaults_and_one_warning|a_change_after_a_damaged_load_keeps_a_backup|a_second_backup_replaces_the_first|a_change_after_an_unreadable_load_does_not_write|a_failed_backup_prevents_the_write|a_missing_file_is_created_without_backup|a_good_file_is_updated_without_backup) .* ok$" $T/verbose.txt; grep -E "^(FAIL|ERROR):" $T/verbose.txt; tail -1 $T/verbose.txt
```

Expected:

```text
Ran 534 tests
OK (skipped=7)
32
OK (skipped=2)
```

- [ ] **Step 3: Shuffled module order, six seeds** (one process each, about two minutes).

```bash
for s in 0 1 2 3 4 5; do $PY $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
      6 ran=1400 failures=0 errors=1 skipped=7 ['test_case_only_rename_still_renames']
```

- [ ] **Step 4: Criterion 3, catalogs (F-8a adds no msgid).** The catalogs are those of `861d110`; a fresh template differs only in `POT-Creation-Date` and in `#:` reference lines (lines moved in `gui.py`, `config.py`, `user_script.py`); 364 msgids, all translated, with the same msgid digest as at the baseline.

```bash
git -C $REPO diff --quiet 861d110 -- client/locales && echo "catalogs unchanged"
(cd $REPO && cmd //c "scripts\\generate-pot.bat $(cygpath -w $T/second.pot)"); echo "generate-pot exit $?"
diff --strip-trailing-cr <(grep -v '^"POT-Creation-Date: \|^#: ' locales/dotexpress.pot) <(grep -v '^"POT-Creation-Date: \|^#: ' $T/second.pot) && echo "fresh template identical apart from POT-Creation-Date and #: lines"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
catalogs unchanged
generate-pot exit 0
fresh template identical apart from POT-Creation-Date and #: lines
364 translated messages.
source msgids: 364 sha256 7b53ff311c9e446767b0884bfc03148afe030ca7e15899d6ee6919e77c664ea7
```

- [ ] **Step 5: Criteria 4-7: fixtures, untouched modules, touched files, application data, source scan.** The scan lists every remaining direct write in production code outside `shared/atomic_write.py` (Spec Corrections 12).

```bash
BASE=861d110
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/shared client/dialog.py client/documents/controller.py client/documents/export_coordinator.py client/ui client/dictionaries/entries.py client/dual_view client/braille client/locales client/settings && echo "atomic_write, dialogs, controller, export coordinator, ui, entries, dual view, braille, catalogs and settings unchanged"
git -C $REPO diff --stat=200 $BASE -- client
git -C $REPO ls-files 'client/*.py' | grep -v '^client/tests/' | sed 's|^client/||' | xargs grep -nE 'copyfile\(|\.write_text\(|\.write_bytes\(|open\([^)]*"(w|a|x|wb|ab|xb)"|NamedTemporaryFile|mkstemp' | grep -v '^shared/atomic_write.py' | cut -d: -f1,3- | sed 's/^\([^:]*\):[[:space:]]*/\1: /'
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) | diff - $T/app-data.sha256 && echo "application data unchanged"
git -C $REPO status --short -- client scripts
```

Expected (the application data are the user's files in the main checkout, read only; in the dry run's scratch clone no `client/log`, `client/workspace`, `client/dictionary` or `client/config.json` appeared, so no test creates them; `status` prints nothing):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
atomic_write, dialogs, controller, export coordinator, ui, entries, dual view, braille, catalogs and settings unchanged
 client/config.py                               |  74 ++++++++++++++++++++++++++++++++++++++++++++++++++-------
 client/conversion/preprocessing/user_script.py |  27 ++++++---------------
 client/dictionaries/manager.py                 |  31 +++++++++++++++++-------
 client/documents/formats.py                    |   4 +++-
 client/documents/workspace.py                  |  27 +++++++++++++++++++--
 client/documents/workspace_service.py          |  33 ++++++++++++++++++++++++--
 client/gui.py                                  |   8 +++++--
 client/tests/full_disk.py                      |  81 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_config.py                    | 188 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_dictionary_manager.py        |  81 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_document_formats.py          |  29 +++++++++++++++++++++++
 client/tests/test_document_workspace.py        |  43 +++++++++++++++++++++++++++++++++
 client/tests/test_gui_document_flows.py        | 115 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----------
 client/tests/test_user_preprocessing_script.py |  47 ++++++++++++++++++++++++++++++++++++-
 client/tests/test_workspace_service.py         | 112 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-------
 15 files changed, 835 insertions(+), 65 deletions(-)
app_paths.py: with paths.config.open("a", encoding="utf-8"):
documents/workspace.py: with open(path, "wb") as stream:
documents/workspace.py: with tempfile.NamedTemporaryFile(dir=directory, prefix=f".{name}.", suffix=".tmp", delete=False) as temporary:
dual_view/files.py: target.write_text(content, encoding="utf-8")
application data unchanged
```

- [ ] **Step 6: Criterion 8, mutation check** (26 mutants: the spec's F-8a items as 21 mutants (the prompt, `exclude_name`, `create_document`, the move guard moved before the move aside and removed, Import, `free_document_name`, each of the seven writers back to its old call, `newline=""` for the exports and `config.json`, the load without `utf-8-sig` and accepting a non-object, the save after an `OSError` load, no `.bak`, writing when the `.bak` fails), and five more: the default document always `new`, the script's newline translation, the second header writer, the export onto a folder, and the skipped save logged every time; about two minutes). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f8a_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
prompt-without-the-disk-check: 2 caught: test_gui_document_flows.test_add_of_a_name_whose_package_is_on_disk_asks_again, test_gui_document_flows.test_rename_to_a_name_whose_package_is_on_disk_asks_again
name-taken-ignores-exclude-name: 4 caught: test_gui_document_flows.test_case_only_rename_keeps_the_document, test_gui_document_flows.test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document, test_gui_document_flows.test_rename_cancelled_or_unchanged_does_nothing, test_workspace_service.test_package_name_taken
create-without-its-check: 1 caught: test_workspace_service.test_create_document_refuses_a_package_that_is_not_listed
move-guard-before-the-move-aside: 12 caught: test_document_workspace.test_case_only_move_leaves_only_the_new_spelling, test_document_workspace.test_case_only_move_on_the_case_insensitive_model_is_not_refused, test_document_workspace.test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores, test_document_workspace.test_pending_braille_keeps_its_metadata, and 8 more
move-guard-removed: 2 caught: test_document_workspace.test_move_onto_an_existing_third_file_puts_the_old_package_back, test_workspace_service.test_rename_onto_a_package_that_is_not_listed_keeps_both_files
import-with-listed-names-only: 1 caught: test_workspace_service.test_import_treats_packages_on_disk_as_existing
free-name-returns-base: 2 caught: test_gui_document_flows.test_startup_with_only_a_kept_invalid_new_package_creates_new_2, test_workspace_service.test_free_document_name
default-document-always-new: 1 caught: test_gui_document_flows.test_startup_with_only_a_kept_invalid_new_package_creates_new_2
script-written-in-place: 3 caught: test_user_preprocessing_script.test_save_installs_through_the_shared_atomic_writer, test_user_preprocessing_script.test_save_uses_utf8_and_atomic_replace, test_user_preprocessing_script.test_write_error_leaves_no_temporary_file_and_keeps_the_script
script-newlines-translated: 1 caught: test_user_preprocessing_script.test_save_installs_through_the_shared_atomic_writer
default-dictionary-written-in-place: 1 caught: test_dictionary_manager.test_header_writers_install_through_a_synced_temporary_file
new-dictionary-written-in-place: 1 caught: test_dictionary_manager.test_header_writers_install_through_a_synced_temporary_file
import-copyfile: 1 caught: test_dictionary_manager.test_import_copy_failure_leaves_no_dictionary
export-copyfile: 2 caught: test_dictionary_manager.test_export_failure_keeps_the_existing_destination, test_dictionary_manager.test_export_onto_a_destination_held_open_keeps_it
export-text-written-in-place: 2 caught: test_document_formats.test_html_export_failure_keeps_the_existing_file, test_document_workspace.test_brl_export_failure_keeps_the_existing_file
export-text-without-newline-translation: 3 caught: test_document_formats.test_exports_keep_their_crlf_bytes, test_gui_document_flows.test_dual_view_and_html_export_render_math_with_real_mathml, test_gui_document_flows.test_real_writers_produce_today_bytes
export-onto-a-folder-names-the-temporary-file: 5 caught: test_export_coordinator.test_export_all_partial_failure_summary_lists_each_failure, test_export_coordinator.test_export_document_write_error_shows_one_error, test_export_coordinator.test_single_export_os_error_is_not_logged, test_gui_document_flows.test_export_all_mixed_documents_turn_by_turn, and 1 more
html-written-in-place: 1 caught: test_document_formats.test_html_export_failure_keeps_the_existing_file
config-written-in-place: 2 caught: test_config.test_save_failure_keeps_the_previous_file, test_config.test_save_installs_through_a_synced_temporary_file
config-without-newline-translation: 1 caught: test_config.test_saved_bytes_use_crlf_on_windows
load-without-utf8-sig: 1 caught: test_config.test_a_utf8_bom_is_read
load-accepts-a-non-object: 2 caught: test_config.test_a_change_after_a_damaged_load_keeps_a_backup, test_config.test_json_that_is_not_an_object_gives_defaults_and_one_warning
save-after-an-unreadable-load: 1 caught: test_config.test_a_change_after_an_unreadable_load_does_not_write
no-backup: 3 caught: test_config.test_a_change_after_a_damaged_load_keeps_a_backup, test_config.test_a_failed_backup_prevents_the_write, test_config.test_a_second_backup_replaces_the_first
write-when-the-backup-fails: 1 caught: test_config.test_a_failed_backup_prevents_the_write
skipped-save-logged-every-time: 1 caught: test_config.test_a_change_after_an_unreadable_load_does_not_write
exit 0
```

### Task 6: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay. The dry run built the same code (the tree of Task 4) and ran Step 2's scripts against it and against `N-f7`; the blocks of Step 4 are those logs (see Dry Run). Run everything from the repository root, one item at a time, with nothing else driving the desktop. Never touch `D:\dxtest\N`, `B`, `N-p25`, `N-f3`, `N-f4*`, `N-f5*`, `N-f6*`, `N-f7` (only read and copied by the scripts) or the existing `D:\dxtest\auto*` folders; every run of this task uses a new folder whose name ends in `-f8a`. Only processes whose exe lies under that folder are ended (`dx.kill_under`); `lockshare.py` is ended with `taskkill /T` (`f5gui.unlock`). The user may have DotExpress open: never end any other process. No script writes to the clipboard.

- [ ] **Step 1: Build** (PowerShell). The main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`.

```powershell
Set-Location D:\workspace\DotExpress
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f8a-build.log 2>&1"
if (Select-String -Path $env:TEMP\f8a-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "config.py", "dictionaries\\manager.py", "documents\\workspace.py", "documents\\workspace_service.py", "documents\\formats.py", "conversion\\preprocessing\\user_script.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress\\client\\$m" -Quiet) { "$m bundled from the checkout" } }
if (Select-String -Path client\build\DotExpress\Analysis-00.toc -SimpleMatch "DotExpress\\client\\gui.py" -Quiet) { "gui.py analyzed from the checkout" }
New-Item -ItemType Directory -Force D:\dxtest\N-f8a | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f8a\DotExpress.exe
(Get-Item D:\dxtest\N-f8a\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f8a\DotExpress.exe).Hash
git status --short -- client scripts
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f8a-build.log`), the six `bundled from the checkout` lines (the five in subfolders print with their doubled backslash), `gui.py analyzed from the checkout`, a size near 48.76 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored).

- [ ] **Step 2: Write the GUI scripts** into the new history folder with `apply_blocks.py` ("Task 6", "Step 2": 6 blocks). They reuse, unchanged, `dx.py`, `docs.py`, `dicts.py` and `lock.py` of `2026-10-09-03-windows-verification/auto/`, F-5's `f5gui.py` and F-7's `f7gui.py`. Scripts use tabs.

File: `docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/f8agui.py`

````python
"""Shared helpers for the F-8a GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py, dicts.py and lock.py of the 2026-10-09-03 Windows verification,
f5gui.py of F-5 and f7gui.py of F-7, unchanged. Every item builds its own work folder
before the start: packages are written with zipfile, config.json as raw bytes. Startup
can show the invalid-workspace-files dialog before the main window; ``start`` answers it
with Keep. Message boxes are task dialogs, read and answered through UIA (f7gui).
Nothing here touches the clipboard.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
F7 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-10-04-f7-dialog-buttons-surrogates-close", "auto"))
sys.path.insert(0, F7)
import f7gui as G  # noqa: E402  (puts F-5's and 2026-10-09-03's auto folders on sys.path)
from f7gui import D, F, X, dx  # noqa: E402

LOCKSHARE = os.path.join(HERE, "lockshare.py")
INVALID_FILES = "無效的工作區文件"
KEEP_INVALID = "保留無效檔案"
OVERWRITE_PROMPT = "確認另存新檔"
WM_MOUSEWHEEL = 0x020A
MK_CONTROL = 0x0008
WHEEL_DELTA = 120


def prepare(exe, d):
	"""A new, empty work folder ``d`` (with workspace\\) and the exe copied in.

	Only processes whose exe lies under ``d`` are ended first (dx.kill_under).
	"""
	d = os.path.normpath(d)
	if os.path.isdir(d):
		dx.kill_under(d)
		shutil.rmtree(d)
	os.makedirs(os.path.join(d, "workspace"))
	shutil.copy(exe, os.path.join(d, "DotExpress.exe"))
	return d


def write(path, data):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "wb") as stream:
		stream.write(data)
	return path


def read(path):
	if not os.path.exists(path):
		return None
	with open(path, "rb") as stream:
		return stream.read()


def package(d, name, text, braille=""):
	"""Write workspace\\<name>.dep as the app writes a package (members <name>.txt and .brl)."""
	path = os.path.join(d, "workspace", f"{name}.dep")
	with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(f"{name}.txt", text)
		archive.writestr(f"{name}.brl", braille)
	return path


def sha(path):
	data = read(path)
	return None if data is None else hashlib.sha256(data).hexdigest()[:16]


def listing(folder):
	return sorted(os.listdir(folder)) if os.path.isdir(folder) else None


def files(d):
	return listing(os.path.join(d, "workspace"))


def processes(d):
	import psutil

	d = os.path.normpath(d).lower()
	return [p for p in psutil.process_iter(["exe", "pid"]) if (p.info["exe"] or "").lower().startswith(d)]


def top_windows(d):
	"""(handle, title) of the visible top-level windows of the processes under ``d``."""
	import win32gui
	import win32process

	pids = {p.pid for p in processes(d)}
	found = []

	def collect(handle, _extra):
		if win32gui.IsWindowVisible(handle) and win32process.GetWindowThreadProcessId(handle)[1] in pids:
			found.append((handle, win32gui.GetWindowText(handle)))

	win32gui.EnumWindows(collect, None)
	return found


def start(d, timeout=40):
	"""Start <d>\\DotExpress.exe; press Keep if the invalid-files dialog opens.

	Returns (app, w, invalid): ``invalid`` is the list of the dialog (None if it did not
	open). If the main window does not appear, returns (None, None, how the start ended).
	"""
	from pywinauto import Application

	target = os.path.join(d, "DotExpress.exe")
	launcher = subprocess.Popen([target], cwd=d)
	started = time.time()
	invalid = None
	while time.time() - started < timeout:
		for handle, title in top_windows(d):
			if title == INVALID_FILES and invalid is None:
				dialog = Application(backend="win32").connect(handle=handle).window(handle=handle)
				listbox = dialog.child_window(class_name="ListBox").wrapper_object()
				invalid = listbox.item_texts()
				X.btn(dialog, KEEP_INVALID).click()
				time.sleep(1)
			elif title.endswith("DotExpress"):
				app, w = dx.attach(d)
				return app, w, invalid
		if launcher.poll() is not None and not processes(d):
			return None, None, f"no main window; exited with code {launcher.returncode}"
		time.sleep(0.5)
	return None, None, f"no main window after {timeout} s: {top_windows(d)}"


def maybe_window(app, w, title, timeout=5):
	try:
		return X.wait_window(app, w, title, timeout=timeout)
	except RuntimeError:
		return None


def closed(handle, timeout=5):
	"""Whether the window ``handle`` is gone or hidden within ``timeout`` seconds.

	wx hides a dialog when it ends and destroys it later, so hidden counts as closed.
	"""
	import win32gui

	end = time.time() + timeout
	while time.time() < end:
		if not win32gui.IsWindow(handle) or not win32gui.IsWindowVisible(handle):
			return True
		time.sleep(0.2)
	return False


def name_prompt(app, w, menu_path, title, name):
	"""Choose ``menu_path``, type ``name`` in the name dialog ``title`` and press 確定.

	The dialog closes before the app checks the name, so a click that is lost (the
	dialog stays open) is repeated, at most three times. Returns the box shown then
	(None if none) and the name dialog shown again (its buttons and name; it is closed
	with Esc), or None.
	"""
	G.menu(w, menu_path, wait=0.5)
	dialog = X.wait_window(app, w, title)
	handle = dialog.wrapper_object().handle
	dialog.child_window(class_name="Edit").wrapper_object().set_edit_text(name)
	ok = X.btn(dialog, "確定", "OK")
	for _attempt in range(3):
		ok.click()
		if closed(handle):
			break
	box = G.answer_box(app, "enter", timeout=5)
	again = maybe_window(app, w, title, timeout=3)
	shown_again = None
	if again is not None:
		handle = again.wrapper_object().handle
		shown_again = {"buttons": G.buttons(again), "name": G.edit_text(again)}
		G.press_keys(again, "{ESC}")
		closed(handle)
	return box, shown_again


def save_dialog(app, w, title, path):
	"""Fill the Save dialog ``title`` with ``path``; answer the overwrite prompt with Yes.

	Returns whether the overwrite prompt appeared.
	"""
	G.path_dialog(app, w, title, path)
	prompt = maybe_window(app, w, OVERWRITE_PROMPT, timeout=3)
	if prompt is None:
		return False
	G.press_keys(prompt, "%y", wait=1.5)
	return True


def wheel_up_with_ctrl(w):
	"""Ctrl + one wheel notch up over the source editor: the font size grows by one."""
	import win32api

	editor = w.children(class_name="Edit")[0]
	rect = editor.rectangle()
	x, y = (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
	editor.send_message(WM_MOUSEWHEEL, (WHEEL_DELTA << 16) | MK_CONTROL, win32api.MAKELONG(x, y))
	time.sleep(1)


def config(d):
	"""config.json: (BOM, CRLF line ends only, parsed JSON or the bytes if it does not parse)."""
	data = read(os.path.join(d, "config.json"))
	if data is None:
		return None
	try:
		parsed = json.loads(data.decode("utf-8-sig"))
	except ValueError:
		parsed = data
	return {
		"bom": data.startswith(b"\xef\xbb\xbf"),
		"crlf": data.count(b"\n") == data.count(b"\r\n"),
		"json": parsed,
	}


def config_log(d):
	"""The messages of log\\config.log without their timestamps."""
	data = read(os.path.join(d, "log", "config.log"))
	if data is None:
		return []
	return [line[24:] for line in data.decode("utf-8").splitlines() if line[:4].isdigit()]


def lock(path, seconds="600", share="rw"):
	"""Hold ``path`` open in another process (lockshare.py) until ``unlock``."""
	process = subprocess.Popen([sys.executable, LOCKSHARE, path, seconds, share], stdout=subprocess.PIPE, text=True)
	print("lock:", process.stdout.readline().strip(), share)
	return process


unlock = F.unlock


def finish(app, w, d):
	print("close:", D.close(app, w))
	dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/lockshare.py`

````python
"""Hold a file open for reading with a chosen share mode: CreateFileW(GENERIC_READ, share).

Usage: python lockshare.py <path> <seconds> <share>
share: "rw" (others may read and write: an editor), "w" (others may write but not read)
or "none". Prints "locked" once the handle is open. lock.py of 2026-10-09-03 knows only
"r" and "rw"; F-6's lockx.py only "none".
"""
import ctypes
import sys
import time
from ctypes import wintypes

SHARES = {"none": 0, "r": 1, "w": 2, "rw": 3}

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateFileW.argtypes = (
	wintypes.LPCWSTR,
	wintypes.DWORD,
	wintypes.DWORD,
	wintypes.LPVOID,
	wintypes.DWORD,
	wintypes.DWORD,
	wintypes.HANDLE,
)
kernel32.CreateFileW.restype = wintypes.HANDLE
handle = kernel32.CreateFileW(sys.argv[1], 0x80000000, SHARES[sys.argv[3]], None, 3, 0x80, None)
if handle is None or handle == wintypes.HANDLE(-1).value:
	print("open failed", ctypes.get_last_error(), flush=True)
	sys.exit(1)
print("locked", flush=True)
time.sleep(float(sys.argv[2]))
````

File: `docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/item66.py`

````python
"""Items 66-69 (F-8 D1, D2): a package that is on disk but not listed.

Usage: python item66.py <exe> <work folder> <66|67|68|69>
66: alpha.dep valid, bad.dep invalid; start, Keep. Add "bad": the box, the name dialog
    shown again (Esc); the list; bad.dep unchanged.
67: as 66. Rename alpha to "bad": the box, the dialog shown again (Esc); then Rename
    alpha to "Alpha" (case only): renamed.
68: as 66. Import bad.txt and ok.txt: the Import Issues dialog; the list; bad.dep unchanged.
69: only an invalid new.dep; start, Keep: the default document; new.dep unchanged.
Before F-8 (N-f7): bad.dep or new.dep is replaced without a message.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8agui as A  # noqa: E402
from f8agui import D, G, X  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
kept = "new" if item == "69" else "bad"
kept_path = A.write(os.path.join(d, "workspace", f"{kept}.dep"), b"not a zip")
if item != "69":
	A.package(d, "alpha", "alpha body")
before = A.sha(kept_path)
app, w, invalid = A.start(d)
print(f"{item} start: invalid {invalid} docs {D.docs(w)} title {w.window_text()!r}")


def import_files(folder, names):
	"""File > Import; open ``folder`` in the file dialog, then choose ``names`` together."""
	G.menu(w, "#0->#5", wait=0.5)
	dialog = X.wait_window(app, w, "匯入文件")
	edit = dialog.child_window(class_name="Edit", found_index=0).wrapper_object()
	edit.set_edit_text(folder)
	G.press_keys(dialog, "{ENTER}")
	edit.set_edit_text(" ".join(f'"{name}"' for name in names))
	G.press_keys(dialog, "{ENTER}", wait=2)


if item == "66":
	box, again = A.name_prompt(app, w, "#0->#3", "新增文件", "bad")
	print("66 box:", box)
	print("66 shown again:", again)
elif item == "67":
	D.select(w, "alpha")
	box, again = A.name_prompt(app, w, "#0->#4", "重新命名文件", "bad")
	print("67 box:", box)
	print("67 shown again:", again)
	if "alpha" in D.docs(w):
		D.select(w, "alpha")
		print("67 case only:", A.name_prompt(app, w, "#0->#4", "重新命名文件", "Alpha"))
	else:
		print("67 case only: alpha is gone", D.docs(w))
elif item == "68":
	data = os.path.join(d, "data")
	A.write(os.path.join(data, "bad.txt"), b"bad text")
	A.write(os.path.join(data, "ok.txt"), b"ok text")
	import_files(data, ["bad.txt", "ok.txt"])
	issues = A.maybe_window(app, w, "匯入問題")
	if issues is None:
		print("68 import issues: none")
	else:
		print("68 import issues:", issues.child_window(class_name="ListBox").wrapper_object().item_texts())
		X.btn(issues, "確定", "OK").click()
		time.sleep(1)
print(f"{item} docs: {D.docs(w)} title: {w.window_text()!r} files: {A.files(d)} {kept}.dep unchanged: {A.sha(kept_path) == before}")
A.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/item76.py`

````python
"""Items 76-78 (F-8 D8): BRL and HTML exports.

Usage: python item76.py <exe> <work folder> <76|77|78>
76: alpha (two braille lines): File > Export > BRL to out\\alpha.brl, then HTML to
    out\\alpha.html: the boxes, each file's sha256 and CRLF count, the folder.
77: Export BRL over out\\old.brl while lockshare.py holds it open (share rw, as an editor
    does), overwrite Yes: the box; old.brl's bytes; the folder.
78: alpha and beta: File > Export All > BRL into out\\, where beta.brl is held open (share
    rw), overwrite Yes: the summary; alpha.brl, beta.brl; the folder.
Before F-8 (N-f7): 76 is the reference (the same bytes); 77 and 78 write under the holder.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8agui as A  # noqa: E402
from f8agui import D, G  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
BRAILLE = {"alpha": "⠁⠃\n⠉⠙", "beta": "⠃⠑\n⠞⠁"}
d = A.prepare(EXE, d)
out = os.path.join(d, "out")
os.makedirs(out)
A.package(d, "alpha", "ab\ncd", BRAILLE["alpha"])
if item == "78":
	A.package(d, "beta", "be\nta", BRAILLE["beta"])
app, w, invalid = A.start(d)
print(f"{item} start: invalid {invalid} docs {D.docs(w)}")


def shown(box):
	"""The box with the work folder as <d> and a temporary file's random part as <random>."""
	if box is None:
		return None
	content = box["content"].replace(repr(d)[1:-1], "<d>")
	box["content"] = re.sub(r"(\.\w+\.brl\.)[0-9a-f]{16}(\.tmp)", r"\1<random>\2", content)
	return box


def describe(name):
	path = os.path.join(out, name)
	data = A.read(path)
	if data is None:
		return f"{name}: missing"
	crlf, lf = data.count(b"\r\n"), data.count(b"\n")
	return f"{name}: {data!r}" if len(data) < 20 else f"{name}: sha {A.sha(path)} crlf {crlf} lf {lf}"


if item == "76":
	D.select(w, "alpha")
	for key, menu_path, name in (("brl", "#0->#6->#1", "alpha.brl"), ("html", "#0->#6->#2", "alpha.html")):
		G.menu(w, menu_path, wait=0.5)
		A.save_dialog(app, w, "匯出文件", os.path.join(out, name))
		print(f"76 export {key}:", shown(G.answer_box(app, "enter")))
		print("76", describe(name))
elif item == "77":
	old = A.write(os.path.join(out, "old.brl"), b"OLD GOOD EXPORT")
	holder = A.lock(old, share="rw")
	D.select(w, "alpha")
	G.menu(w, "#0->#6->#1", wait=0.5)
	print("77 overwrite prompt:", A.save_dialog(app, w, "匯出文件", old))
	print("77 export brl:", shown(G.answer_box(app, "enter")))
	A.unlock(holder)
	print("77", describe("old.brl"))
elif item == "78":
	beta = A.write(os.path.join(out, "beta.brl"), b"OLD BETA EXPORT")
	holder = A.lock(beta, share="rw")
	G.menu(w, "#0->#7->#1", wait=0.5)
	G.path_dialog(app, w, "匯出全部文件", out)
	print("78 overwrite question:", shown(G.answer_box(app, "alt-y")))
	print("78 summary:", shown(G.answer_box(app, "enter")))
	A.unlock(holder)
	print("78", describe("alpha.brl"))
	print("78", describe("beta.brl"))
print(f"{item} out: {A.listing(out)}")
A.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/item79.py`

````python
"""Items 79-81 (F-8 D9-D11): config.json that cannot be used.

Usage: python item79.py <exe> <work folder> <79|80|81>
The font size is changed with Ctrl + one wheel notch up over the source editor (one point
more than the size the app read). The client id that the app adds at startup is shown
as <id>. A file that is not JSON is shown as its bytes.
79: config.json holds null. Start: the main window; config.json, config.json.bak and
    log\\config.log; change the font size; config.json and .bak again.
80: config.json with a UTF-8 BOM, font size 20 and width 30. Start; change the font size:
    config.json (BOM, CRLF, values), no .bak.
81: config.json (font size 20, width 30) held open by lockshare.py with share "w" (others
    may write but not read). Start; change the font size: config.json unchanged,
    config.log; release; close; start again; change the font size: the old values were read.
Before F-8 (N-f7): 79 does not start; 80 and 81 lose the settings.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8agui as A  # noqa: E402
from f8agui import D  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
GOOD = b'{\r\n  "view": {\r\n    "font_size": 20\r\n  },\r\n  "conversion": {\r\n    "width": 30\r\n  }\r\n}'
d = A.prepare(EXE, d)
path = os.path.join(d, "config.json")
backup = path + ".bak"
A.write(path, {"79": b"null", "80": b"\xef\xbb\xbf" + GOOD, "81": GOOD}[item])
original = A.sha(path)


def state(label, held=False):
	"""config.json (client id as <id>), config.json.bak and config.log.

	While lockshare.py holds config.json without read sharing, only its log is read.
	"""
	if held:
		log = [line.replace(d, "<d>") for line in A.config_log(d)]
		print(f"{item} {label}: config.json held open; config.json.bak {A.read(backup)!r} config.log {log}")
		return
	described = A.config(d)
	if described is not None and isinstance(described["json"], dict):
		client = described["json"].get("client")
		if isinstance(client, dict) and "id" in client:
			client["id"] = "<id>"
		described["json"] = json.dumps(described["json"], sort_keys=True, ensure_ascii=False)
	log = [line.replace(d, "<d>") for line in A.config_log(d)]
	print(f"{item} {label}: config.json {described} unchanged: {A.sha(path) == original}")
	print(f"{item} {label}: config.json.bak {A.read(backup)!r} config.log {log}")


holder = A.lock(path, share="w") if item == "81" else None
app, w, invalid = A.start(d)
if app is None:
	print(f"{item} start: {invalid}")
	print(f"{item} files: {A.listing(d)}")
	if holder is not None:
		A.unlock(holder)
	sys.exit(0)
time.sleep(2)
print(f"{item} start: main window, docs {D.docs(w)}")
state("after start", held=holder is not None)
A.wheel_up_with_ctrl(w)
state("after the font change", held=holder is not None)
if item == "81":
	A.unlock(holder)
	state("released")
	print("close:", D.close(app, w))
	app, w, invalid = A.start(d)
	time.sleep(2)
	A.wheel_up_with_ctrl(w)
	state("released, restarted, font changed")
print(f"{item} files: {A.listing(d)}")
A.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/item82.py`

````python
"""Item 82 (F-8 D6, D7): the dictionary files and the text-processing script.

Usage: python item82.py <exe> <work folder>
Dictionary Management: Add d1; Import data\\d2.csv (a UTF-8 file with a BOM, CRLF and
CJK text) as d2; select d1, Export over out\\d1.csv (which holds b"OLD"), overwrite Yes.
Text Processing: replace the script by one that returns text.upper(), Apply, then OK.
Prints the sha256 of every file in dictionary\\ and out\\ and preprocessing.py's bytes.
Before F-8 (N-f7) is the reference: the same bytes, no .tmp either way.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8agui as A  # noqa: E402
from f8agui import D, G, X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
D2 = b"\xef\xbb\xbftext,braille,type\r\n" + "臺灣,⠞⠺,General\r\n".encode("utf-8")
SCRIPT = "def main(text):\r\n    return text.upper()\r\n"
WM_SETTEXT = 0x000C
d = A.prepare(EXE, d)
dictionary = os.path.join(d, "dictionary")
out = os.path.join(d, "out")
data = A.write(os.path.join(d, "data", "d2.csv"), D2)
A.write(os.path.join(out, "d1.csv"), b"OLD")
app, w, invalid = A.start(d)
print(f"82 start: invalid {invalid} docs {D.docs(w)}")

mgr = X.open_mgr(app, w)
X.btn(mgr, "新增").click()
dialog = X.wait_window(app, w, "新增字典")
dialog.child_window(class_name="Edit").wrapper_object().set_edit_text("d1")
X.btn(dialog, "確定", "OK").click()
time.sleep(1.5)
print("82 import d2:", X.import_named(app, w, mgr, data))
X.mgr_select(mgr, "d1")
X.btn(mgr, "匯出").click()
print("82 export d1, overwrite prompt:", A.save_dialog(app, w, "匯出字典", os.path.join(out, "d1.csv")))
print("82 export d1, box:", G.answer_box(app, "enter", timeout=3))
print("82 rows:", X.mgr_items(mgr)[1])
X.close_mgr(app, w, mgr)

G.menu(w, "#1->#2")
processing = G.window_titled(app, w, G.TEXT_PROCESSING)
editor = [c for c in processing.wrapper_object().descendants() if c.class_name().upper().startswith("RICHEDIT")][0]
editor.send_message(WM_SETTEXT, 0, SCRIPT)
X.btn(processing, "套用", "Apply").click()
time.sleep(1)
print("82 apply:", G.answer_box(app, "enter", timeout=2), "windows:", G.windows(app, w))
X.btn(processing, "確定", "OK").click()
time.sleep(1)
print("82 after OK: windows:", G.windows(app, w))

for folder in (dictionary, out):
	print(f"82 {os.path.basename(folder)}:", {name: A.sha(os.path.join(folder, name)) for name in A.listing(folder)})
print("82 preprocessing.py:", A.read(os.path.join(dictionary, "preprocessing.py")))
print("82 d2.csv equals the source:", A.read(os.path.join(dictionary, "d2.csv")) == D2)
print("82 out d1.csv equals dictionary d1.csv:", A.read(os.path.join(out, "d1.csv")) == A.read(os.path.join(dictionary, "d1.csv")))
A.finish(app, w, d)
````

- [ ] **Step 3: Items 66-69 and 76-82 on both builds** (Git Bash, from the repository root): first `D:\dxtest\N-f7\DotExpress.exe` ("Before", folders `auto<N>-f7-f8a`), then the new build (folders `auto<N>-f8a`). Each run makes its own work folder (`f8agui.prepare` deletes it first, after ending any process under it) and copies the exe into it. Read each log against Step 4 before the next run.

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto
export PYTHONIOENCODING=utf-8
cd $REPO
for build in N-f7 N-f8a; do
  tag=$([ $build = N-f7 ] && echo -f7-f8a || echo -f8a)
  for i in 66 67 68 69; do "$UIA" $H/item66.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto$i$tag $i > /d/dxtest/auto$i$tag.log 2>&1; done
  for i in 76 77 78; do "$UIA" $H/item76.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto$i$tag $i > /d/dxtest/auto$i$tag.log 2>&1; done
  for i in 79 80 81; do "$UIA" $H/item79.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto$i$tag $i > /d/dxtest/auto$i$tag.log 2>&1; done
  "$UIA" $H/item82.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto82$tag > /d/dxtest/auto82$tag.log 2>&1
done
```

- [ ] **Step 4: Expected logs.** Each log must equal its block line by line (`diff --strip-trailing-cr`). A box is `{'title': ..., 'main': None, 'content': ..., 'buttons': [...], 'focus': ..., 'presses': 1}`, read through UIA; `<d>` stands for the work folder, `<random>` for the 16 hex digits of a temporary name, `<id>` for the client id the app writes at startup. The `focus` of a box is read from the system's focused element half a second after the box is brought forward; a notification of another program can show up there instead (a tool artifact, not a result: note it and run that item again in a new folder).

**66.** Add `bad` while the kept invalid `bad.dep` is on disk: the `錯誤` box `文件「bad」已存在。`, the name dialog again with `bad` (translated buttons), the list and `bad.dep` unchanged. Before: `bad` is added and `bad.dep` replaced, without a message.

After F-8a, `D:\dxtest\auto66-f8a.log`:

```text
66 start: invalid ['bad.dep'] docs ['alpha'] title 'alpha - DotExpress'
66 box: {'title': '錯誤', 'main': None, 'content': '文件「bad」已存在。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
66 shown again: {'buttons': ['確定', '取消'], 'name': 'bad'}
66 docs: ['alpha'] title: 'alpha - DotExpress' files: ['alpha.dep', 'bad.dep'] bad.dep unchanged: True
close: exited
```

Before (N-f7), `D:\dxtest\auto66-f7-f8a.log`:

```text
66 start: invalid ['bad.dep'] docs ['alpha'] title 'alpha - DotExpress'
66 box: None
66 shown again: None
66 docs: ['alpha', 'bad'] title: 'bad - DotExpress' files: ['alpha.dep', 'bad.dep'] bad.dep unchanged: False
close: exited
```

**67.** Rename `alpha` to `bad`: the same box and dialog, nothing changes; then the case-only Rename to `Alpha` succeeds (`Alpha.dep`). Before: `bad.dep` is replaced and `alpha.dep` is gone.

After F-8a, `D:\dxtest\auto67-f8a.log`:

```text
67 start: invalid ['bad.dep'] docs ['alpha'] title 'alpha - DotExpress'
67 box: {'title': '錯誤', 'main': None, 'content': '文件「bad」已存在。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
67 shown again: {'buttons': ['確定', '取消'], 'name': 'bad'}
67 case only: (None, None)
67 docs: ['Alpha'] title: 'Alpha - DotExpress' files: ['Alpha.dep', 'bad.dep'] bad.dep unchanged: True
close: exited
```

Before (N-f7), `D:\dxtest\auto67-f7-f8a.log`:

```text
67 start: invalid ['bad.dep'] docs ['alpha'] title 'alpha - DotExpress'
67 box: None
67 shown again: None
67 case only: alpha is gone ['bad']
67 docs: ['bad'] title: 'bad - DotExpress' files: ['bad.dep'] bad.dep unchanged: False
close: exited
```

**68.** Import `bad.txt` and `ok.txt`: the Import Issues dialog lists `bad.txt: Document "bad" already exists.`; `ok` is imported; `bad.dep` unchanged. Before: no issue, `bad.dep` replaced.

After F-8a, `D:\dxtest\auto68-f8a.log`:

```text
68 start: invalid ['bad.dep'] docs ['alpha'] title 'alpha - DotExpress'
68 import issues: ['bad.txt: Document "bad" already exists.']
68 docs: ['alpha', 'ok'] title: 'ok - DotExpress' files: ['alpha.dep', 'bad.dep', 'ok.dep'] bad.dep unchanged: True
close: exited
```

Before (N-f7), `D:\dxtest\auto68-f7-f8a.log`:

```text
68 start: invalid ['bad.dep'] docs ['alpha'] title 'alpha - DotExpress'
68 import issues: none
68 docs: ['alpha', 'bad', 'ok'] title: 'alpha - DotExpress' files: ['alpha.dep', 'bad.dep', 'ok.dep'] bad.dep unchanged: False
close: exited
```

**69.** Only an invalid `new.dep`, kept: the default document is `new (2)`; `new.dep` unchanged. Before: `new` replaces `new.dep`.

After F-8a, `D:\dxtest\auto69-f8a.log`:

```text
69 start: invalid ['new.dep'] docs ['new (2)'] title 'new (2) - DotExpress'
69 docs: ['new (2)'] title: 'new (2) - DotExpress' files: ['new (2).dep', 'new.dep'] new.dep unchanged: True
close: exited
```

Before (N-f7), `D:\dxtest\auto69-f7-f8a.log`:

```text
69 start: invalid ['new.dep'] docs ['new'] title 'new - DotExpress'
69 docs: ['new'] title: 'new - DotExpress' files: ['new.dep'] new.dep unchanged: False
close: exited
```

**76.** BRL and HTML exports: the same bytes from both builds (CRLF), no `.tmp`.

After F-8a, `D:\dxtest\auto76-f8a.log`:

```text
76 start: invalid None docs ['alpha']
76 export brl: {'title': '匯出完成', 'main': None, 'content': '文件已成功匯出。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
76 alpha.brl: b'\xe2\xa0\x81\xe2\xa0\x83\r\n\xe2\xa0\x89\xe2\xa0\x99'
76 export html: {'title': '匯出完成', 'main': None, 'content': '文件已成功匯出。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
76 alpha.html: sha 6d8d672429f56e30 crlf 25 lf 25
76 out: ['alpha.brl', 'alpha.html']
close: exited
```

Before (N-f7), `D:\dxtest\auto76-f7-f8a.log`:

```text
76 start: invalid None docs ['alpha']
76 export brl: {'title': '匯出完成', 'main': None, 'content': '文件已成功匯出。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
76 alpha.brl: b'\xe2\xa0\x81\xe2\xa0\x83\r\n\xe2\xa0\x89\xe2\xa0\x99'
76 export html: {'title': '匯出完成', 'main': None, 'content': '文件已成功匯出。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
76 alpha.html: sha 6d8d672429f56e30 crlf 25 lf 25
76 out: ['alpha.brl', 'alpha.html']
close: exited
```

**77.** Export BRL over `old.brl` held open (share read+write): `匯出文件失敗：[WinError 5] ...` and `old.brl` keeps its bytes, no `.tmp` (Risks, O6). Before: the export succeeds and rewrites the file under the holder.

After F-8a, `D:\dxtest\auto77-f8a.log`:

```text
77 start: invalid None docs ['alpha']
lock: locked rw
77 overwrite prompt: True
77 export brl: {'title': '錯誤', 'main': None, 'content': "匯出文件失敗：[WinError 5] 存取被拒。: '<d>\\\\out\\\\.old.brl.<random>.tmp' -> '<d>\\\\out\\\\old.brl'", 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
77 old.brl: b'OLD GOOD EXPORT'
77 out: ['old.brl']
close: exited
```

Before (N-f7), `D:\dxtest\auto77-f7-f8a.log`:

```text
77 start: invalid None docs ['alpha']
lock: locked rw
77 overwrite prompt: True
77 export brl: {'title': '匯出完成', 'main': None, 'content': '文件已成功匯出。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
77 old.brl: b'\xe2\xa0\x81\xe2\xa0\x83\r\n\xe2\xa0\x89\xe2\xa0\x99'
77 out: ['old.brl']
close: exited
```

**78.** Export All BRL with `beta.brl` held open: the summary lists `beta` as failed, `alpha.brl` is written, `beta.brl` keeps its bytes. Before: everything is written, `beta.brl` under the holder.

After F-8a, `D:\dxtest\auto78-f8a.log`:

```text
78 start: invalid None docs ['alpha', 'beta']
lock: locked rw
78 overwrite question: {'title': '確認覆蓋', 'main': None, 'content': '目的資料夾中已有一個或多個檔案會被覆蓋。要全部覆蓋嗎？', 'buttons': ['是(Y)', '否(N)'], 'focus': '是(Y)', 'presses': 1}
78 summary: {'title': 'Export Complete with Errors', 'main': None, 'content': "Exported documents: 1\nFailed documents: 1\n\nbeta: [WinError 5] 存取被拒。: '<d>\\\\out\\\\.beta.brl.<random>.tmp' -> '<d>\\\\out\\\\beta.brl'", 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
78 alpha.brl: b'\xe2\xa0\x81\xe2\xa0\x83\r\n\xe2\xa0\x89\xe2\xa0\x99'
78 beta.brl: b'OLD BETA EXPORT'
78 out: ['alpha.brl', 'beta.brl']
close: exited
```

Before (N-f7), `D:\dxtest\auto78-f7-f8a.log`:

```text
78 start: invalid None docs ['alpha', 'beta']
lock: locked rw
78 overwrite question: {'title': '確認覆蓋', 'main': None, 'content': '目的資料夾中已有一個或多個檔案會被覆蓋。要全部覆蓋嗎？', 'buttons': ['是(Y)', '否(N)'], 'focus': '是(Y)', 'presses': 1}
78 summary: {'title': '匯出完成', 'main': None, 'content': 'All documents were exported successfully.', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
78 alpha.brl: b'\xe2\xa0\x81\xe2\xa0\x83\r\n\xe2\xa0\x89\xe2\xa0\x99'
78 beta.brl: b'\xe2\xa0\x83\xe2\xa0\x91\r\n\xe2\xa0\x9e\xe2\xa0\x81'
78 out: ['alpha.brl', 'beta.brl']
close: exited
```

**79.** `config.json` = `null`: the main window appears with defaults; the client id written at startup keeps `config.json.bak` = `null` first; the font change is saved. Before: no main window, the process exits with code 1.

After F-8a, `D:\dxtest\auto79-f8a.log`:

```text
79 start: main window, docs ['new']
79 after start: config.json {'bom': False, 'crlf': True, 'json': '{"client": {"id": "<id>"}}'} unchanged: False
79 after start: config.json.bak b'null' config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults']
79 after the font change: config.json {'bom': False, 'crlf': True, 'json': '{"client": {"id": "<id>"}, "view": {"braille_font": "simbraille", "font_size": 13, "scheme": "light"}}'} unchanged: False
79 after the font change: config.json.bak b'null' config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults']
79 files: ['DotExpress.exe', 'config.json', 'config.json.bak', 'dictionary', 'dual_view', 'log', 'workspace']
close: exited
```

Before (N-f7), `D:\dxtest\auto79-f7-f8a.log`:

```text
79 start: no main window; exited with code 1
79 files: ['DotExpress.exe', 'config.json', 'dictionary', 'dual_view', 'log', 'workspace']
```

**80.** `config.json` with a BOM, font size 20, width 30: read normally (font 20 + 1 = 21), the width is kept, written without BOM, CRLF, no `.bak`. Before: the BOM file is replaced at startup by the client id; the font starts at 12, the width is lost.

After F-8a, `D:\dxtest\auto80-f8a.log`:

```text
80 start: main window, docs ['new']
80 after start: config.json {'bom': False, 'crlf': True, 'json': '{"client": {"id": "<id>"}, "conversion": {"width": 30}, "view": {"font_size": 20}}'} unchanged: False
80 after start: config.json.bak None config.log []
80 after the font change: config.json {'bom': False, 'crlf': True, 'json': '{"client": {"id": "<id>"}, "conversion": {"width": 30}, "view": {"braille_font": "simbraille", "font_size": 21, "scheme": "light"}}'} unchanged: False
80 after the font change: config.json.bak None config.log []
80 files: ['DotExpress.exe', 'config.json', 'dictionary', 'dual_view', 'log', 'workspace']
close: exited
```

Before (N-f7), `D:\dxtest\auto80-f7-f8a.log`:

```text
80 start: main window, docs ['new']
80 after start: config.json {'bom': False, 'crlf': True, 'json': '{"client": {"id": "<id>"}}'} unchanged: False
80 after start: config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults']
80 after the font change: config.json {'bom': False, 'crlf': True, 'json': '{"client": {"id": "<id>"}, "view": {"braille_font": "simbraille", "font_size": 13, "scheme": "light"}}'} unchanged: False
80 after the font change: config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults']
80 files: ['DotExpress.exe', 'config.json', 'dictionary', 'dual_view', 'log', 'workspace']
close: exited
```

**81.** `config.json` held with share "write only": the app starts with defaults, the file is never written (one `was not saved because it could not be read` warning), and after the release the old values are read (font 20 + 1 = 21, width 30 kept). Before: the file is replaced while held, and the old values are lost.

After F-8a, `D:\dxtest\auto81-f8a.log`:

```text
lock: locked w
81 start: main window, docs ['new']
81 after start: config.json held open; config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults', '[WARNING] Config file <d>\\config.json was not saved because it could not be read']
81 after the font change: config.json held open; config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults', '[WARNING] Config file <d>\\config.json was not saved because it could not be read']
81 released: config.json {'bom': False, 'crlf': True, 'json': '{"conversion": {"width": 30}, "view": {"font_size": 20}}'} unchanged: True
81 released: config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults', '[WARNING] Config file <d>\\config.json was not saved because it could not be read']
close: exited
81 released, restarted, font changed: config.json {'bom': False, 'crlf': True, 'json': '{"client": {"id": "<id>"}, "conversion": {"width": 30}, "view": {"braille_font": "simbraille", "font_size": 21, "scheme": "light"}}'} unchanged: False
81 released, restarted, font changed: config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults', '[WARNING] Config file <d>\\config.json was not saved because it could not be read']
81 files: ['DotExpress.exe', 'config.json', 'dictionary', 'dual_view', 'log', 'workspace']
close: exited
```

Before (N-f7), `D:\dxtest\auto81-f7-f8a.log`:

```text
lock: locked w
81 start: main window, docs ['new']
81 after start: config.json held open; config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults']
81 after the font change: config.json held open; config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults']
81 released: config.json {'bom': False, 'crlf': True, 'json': '{"view": {"braille_font": "simbraille", "font_size": 13, "scheme": "light"}}'} unchanged: False
81 released: config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults']
close: exited
81 released, restarted, font changed: config.json {'bom': False, 'crlf': True, 'json': '{"client": {"id": "<id>"}, "view": {"braille_font": "simbraille", "font_size": 14, "scheme": "light"}}'} unchanged: False
81 released, restarted, font changed: config.json.bak None config.log ['[WARNING] Failed to read config file <d>\\config.json; using defaults']
81 files: ['DotExpress.exe', 'config.json', 'dictionary', 'dual_view', 'log', 'workspace']
close: exited
```

**82.** Dictionary Add, Import, Export over an existing file and Text Processing Apply: the same bytes from both builds, no `.tmp`.

After F-8a, `D:\dxtest\auto82-f8a.log`:

```text
82 start: invalid None docs ['new']
82 import d2: []
82 export d1, overwrite prompt: True
82 export d1, box: None
82 rows: [['d1', '0'], ['d2', '1'], ['default', '0']]
82 apply: None windows: ['文字處理']
82 after OK: windows: []
82 dictionary: {'d1.csv': '8f0594e9a11d46bb', 'd2.csv': 'f58a2e62a8033753', 'default.csv': '8f0594e9a11d46bb', 'preprocessing.py': '3413db2502421693'}
82 out: {'d1.csv': '8f0594e9a11d46bb'}
82 preprocessing.py: b'def main(text):\n    return text.upper()\n'
82 d2.csv equals the source: True
82 out d1.csv equals dictionary d1.csv: True
close: exited
```

Before (N-f7), `D:\dxtest\auto82-f7-f8a.log`:

```text
82 start: invalid None docs ['new']
82 import d2: []
82 export d1, overwrite prompt: True
82 export d1, box: None
82 rows: [['d1', '0'], ['d2', '1'], ['default', '0']]
82 apply: None windows: ['文字處理']
82 after OK: windows: []
82 dictionary: {'d1.csv': '8f0594e9a11d46bb', 'd2.csv': 'f58a2e62a8033753', 'default.csv': '8f0594e9a11d46bb', 'preprocessing.py': '3413db2502421693'}
82 out: {'d1.csv': '8f0594e9a11d46bb'}
82 preprocessing.py: b'def main(text):\n    return text.upper()\n'
82 d2.csv equals the source: True
82 out d1.csv equals dictionary d1.csv: True
close: exited
```

- [ ] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto-results.md` in the style of `2026-10-10-04-f7-dialog-buttons-surrogates-close/auto-results.md` (zh-TW): the build (PyInstaller version, `Build complete!`, the bundled modules, size, sha256), the method, then one row per item (66-69, 76-82) with ✔/△/✘, the observed boxes, dialogs, lists, files and log lines after F-8a and the "Before" observations on N-f7. Any deviation from Step 4 is reported to the orchestrator before the commit, not explained away; a re-run after a GUI timing problem (for example the foreground taken by another program) is recorded with the first attempt's log name. End the file with a short section **「仍需人工（使用者）」** for item 84, worded for the user (do not mark it done):

  > 84（可選）：在磁碟快滿時匯出，確認舊檔不會被破壞。請沿用項目 34 的小型 VHD（需要系統管理員權限），把它寫到只剩幾 KB 可用空間，並在其中放一個內容正常的 `old.brl`。把 `D:\dxtest\N-f8a\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual84-f8a\` 執行，新增文件、貼上一段長文字並轉換，再用「檔案 → 匯出 → 點字檔 BRL」覆蓋那個 `old.brl`。預期：出現「匯出文件失敗：…」訊息，訊息中是磁碟已滿的錯誤；`old.brl` 的內容和大小完全不變；資料夾中沒有留下 `.old.brl.….tmp`。如果舊檔變空或只剩一部分，請告訴我們。

```bash
cd $REPO
git add docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto-results.md docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/f8agui.py docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/lockshare.py docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/item66.py docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/item76.py docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/item79.py docs/superpowers/history/2026-10-10-05-f8a-data-safety-cleanup/auto/item82.py
git diff --cached --stat
git commit -q -m "docs: record the F-8a packaged-build GUI checks (F-8a)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short -- client docs scripts
git rev-parse HEAD:client
```

Expected: the seven files in the `--stat`, no `status` output, and the Task 4 tree id `62ea9d3eadebd3064e70e675138c6a32c7543f7d` (the commit touches no file under `client/`). Do not merge `main` or push; the orchestrator decides.
