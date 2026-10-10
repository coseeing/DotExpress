# Recovery of Interrupted Saves and U+0000 Replacement (F-8b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ] `) syntax for tracking.

**Goal:** The second half of F-8 (the spec's split O1). At startup, a document whose Save or Rename was interrupted by a crash, so that it exists only in a temporary file, is put back under its package name when that name is free and no listed document holds the same content; the user is told in one information box ("已復原文件"); no file is ever deleted or replaced. U+0000, which the Windows editors cannot hold, becomes U+FFFD where documents enter the app (packages loaded at startup, files imported), so nothing after it is lost at the next save; the first time such a document is opened in a session, a warning box ("已取代字元") names it and says how many characters were replaced. Four new msgids (364 -> 368).

**Architecture:** Two commits on the client, each red first, the spec's migration steps 5 and 6, each with its own catalog regeneration. Task 1 adds `recover_interrupted_packages` and `_read_package` to `documents/workspace.py`, calls it from `DocumentWorkspaceService.load_documents` (with `take_recovered_document_names`), shows the recovery box in `BrailleFrame._load_workspace_documents_at_startup`, and adds the two recovery msgids (D3-D5, D15). Task 2 adds `replace_nul_characters` and `_displayable` to `documents/workspace.py`, applies them in the service where packages are loaded and files imported, keeps the counts per document (`take_replaced_character_count`), shows the notice at the end of `BrailleFrame._open_document_by_name`, and adds the other two msgids (D12-D15). Task 3 verifies (suite, shuffled order, catalogs, fixtures, application data, 24 mutants), Task 4 builds the exe and runs the GUI checks (spec items 70-75; item 83 stays manual).

**Tech Stack:** Python 3.13 standard library (`os`, `re`, `zipfile`, `logging`, `gettext`, `unittest`, `unittest.mock`), wxPython 4.2.5 (message boxes through `ui.message_box`, unchanged), GNU gettext 0.23 (`xgettext`, `msgmerge`, `msgfmt`, `msgattrib`), Git Bash `unix2dos`. Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-10-f8-data-safety-cleanup-design.md` (+ `_zh-TW.md`), with the section "Corrected after planning (F-8b)" / 「規劃後的修正（F-8b）」 added in the plan commit (both languages). The user decided U1 (U+0000 becomes U+FFFD with a notice) and U2 (2026-10-10); O3, O5 and O7 are the orchestrator's recommended defaults (the user may override them before the merge). Spec Corrections 13 below records one behavior of D3 that the dry run measured and that the user may want to decide (a leftover that is skipped can be recovered at a later start); it does not block the plan, which implements D3 as specified.

## Global Constraints

- Work in the main checkout `D:\workspace\DotExpress`, branch `fix/f8b-recovery-and-nul` (HEAD is the plan commit on top of `main` at `1b19290`, the F-8a merge). Never switch branches, never push, never merge, never rewrite history. `D:\workspace\DotExpress-f9` is another task's worktree and `D:\workspace\DotExpress-6e5819f` an old one: do not touch them.
- Files that may change (10 under `client/`, nothing else there): production `client/documents/workspace.py`, `client/documents/workspace_service.py` (4 spaces), `client/gui.py` (**tabs**); tests `client/tests/test_document_workspace.py`, `client/tests/test_workspace_service.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_i18n.py` (4 spaces); catalogs `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`; in Task 4 the new history folder `docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/` (scripts with tabs, results).
- Never touch `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data in this checkout; the tests use temporary folders; every module whose code under test can log isolates that logger: `test_gui_document_flows` `dotexpress.gui` as before, and now `test_document_workspace` and `test_workspace_service` `dotexpress.gui` too; Task 0 and Task 3 compare their sha256), `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (CRLF bytes), tracked `client/braille/` content, `client/braille/liblouis/`, `client/tests/fixtures/`, `scripts/`, `vendor/`, the submodule pointers, the untracked `client2/`, `preprocessing/`, `testdata/` and `task.md`, or the committed scripts and data of earlier history folders. Never run `py scripts\sync-nvda.py`. Never start `gui.py` from source in the main checkout. **Never write to the Windows clipboard**: no test, probe or GUI script of this plan does (U+0000 reaches the app only through files; do not use `f5gui.paste_text_with_lone_surrogate`). `git status --short -- client docs scripts` must stay empty between commits (`docs/` holds the history folder of Task 4 only until Task 4 commits it).
- The checkout uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply the blocks **with a script that reads them from this file** (`$T/tools/apply_blocks.py`, Task 0 Step 3), not by hand: a `File:` block is written as is (LF is fine; git normalizes it); an `Edit:` block is the line ``Edit: `path` `` followed by two fenced blocks, the exact old text and its replacement; the old text must occur exactly once in the file at that point (compare with CRLF converted to LF, keep the file's line endings). The blocks of one step are applied in order. Never edit with MSYS `sed -i` and never paste code through a shell heredoc (it turns `\\` into `\`). **The blocks hold `\x00` and `\ufffd` escapes** (U+0000 and U+FFFD in tests and production code are always written as escapes, never as the characters); the Edit/Write tools turn `\uXXXX` escapes into the characters they stand for, so never retype a block or rewrite a whole file through those tools. `apply_blocks.py` reads and writes bytes, so the escapes stay as they are; Task 1 Step 1 and Task 2 Step 1 count them in the files, and the tree id check catches any other change.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf` (`git show HEAD:<path> | sha256sum`), unchanged.
- Catalogs: `POT-Creation-Date` stays `2026-10-10 12:00+0800` (pinned by `$T/tools/pin_pot_date.py` after every `generate-pot.bat`), so the `.pot`, `.po` and `.mo`, and with them the tree id, are the same in every run.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly; look at `git diff --cached --stat` first; never `git commit -F -`.
- The only failing test before and after F-8b is the F-W6 error `test_dictionary_name_prompt ... test_case_only_rename_still_renames` (out of scope).
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`, the random part of a temporary file name as `<rnd>`). Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks.
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress
  MAIN=$REPO
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f8bimpl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the same folder as `REPO` here; the dry run used a scratch clone as `REPO`, and the commands that read the user's application data or copy the git-ignored runtime use `MAIN`. Task 4 uses PowerShell for the build and the UIA venv for the GUI scripts.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning (F-8b)" in the plan commit. Re-checked against the code after F-8a (`1b19290`): decisions D3-D5 and D12-D15 and their rows of the behavior table hold; the line numbers have moved (`_load_workspace_documents_at_startup` is `gui.py:742-747`, `_open_document_by_name` `gui.py:602-613`, `load_documents` `workspace_service.py:134-139`, `import_files` `:169-191`). The refinements:

1. **Counts.** `Ran 1419` after Task 1 (16 new tests: D has 15, F has 1) and `Ran 1434` after Task 2 (15 new: E has 14, F has 1); baseline 1403 (F-8a's 1400 plus its three review tests); `FAILED (errors=1, skipped=7)` throughout, F-W6 only; msgids 364 -> 366 -> 368. D in `test_document_workspace` has 11 tests (D1-D9 and two more: files that are not package leftovers are ignored, and two interrupted renames are recovered oldest first; D8 also records `os.replace`, so it is `test_recovery_never_deletes_or_replaces_a_file`), D in `test_workspace_service` 3 (D11, a load without leftovers recovers nothing, D12), D13 in `test_gui_document_flows`; E has E1-E13 plus `test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened` (item 75's flow), E13 being `test_editors_receive_the_full_text`. Windows-only new test: D9 (the skip count stays 7). The acceptance-criterion-2 set goes from `Ran 537` to `Ran 568`, `OK (skipped=7)`.
2. **F1 is split in two,** one per step, so that each catalog regeneration is red first: `test_recovery_strings_are_translated` (Task 1) and `test_replaced_character_strings_are_translated` (Task 2). Each compares the msgstr through the compiled `.mo` (`i18n.load_translation`) and formats it (`names`; `name`, `count`, `mark`).
3. **Log isolation.** `test_document_workspace` and `test_workspace_service` gain a `setUpModule` that isolates `dotexpress.gui` (`isolate_file_logs`): recovery logs a failed rename there. The recovery tests assert that nothing is logged (`assertNoLogs`) except D9, which expects the one line: on Windows `os.rename` refuses a taken name, so without that assertion a missing name rule would only show up in the log.
4. **D9 simulates the race by a patched `os.rename`** that creates the target first and then renames (instead of "the disk check patched to miss"). The log line is `Cannot recover interrupted document package <path>: [WinError 183] ...`, at `ERROR`, without traceback.
5. **D3 details.** `_INTERRUPTED_PACKAGE` is `^\.(?P<stem>.+)\.(?i:dep)\.[A-Za-z0-9_]+\.tmp$`; only regular files are candidates; `_read_package(package_path, package_name)` is today's body of `load_document_package` after the suffix check. The explicit stem check of rule 1 stays, but `_read_package` alone already skips such files (member names are normalized and must equal the stem), so no mutant can isolate it; D6 pins the behavior with names a Windows folder can hold (`" alpha"`, `"alpha "`, `"alpha."`, 33 characters, `"CON"`). The logger is bound at call time (`log.get_logger("dotexpress.gui", "gui.log")`, as F-7 D6 does).
6. **D3/D4 order.** The recovered documents are merged into the loaded list in its order (`casefold`, then name). The box names them in recovery order, oldest first, one per line (`"beta\nalpha"` in D13).
7. **D12 helper.** `documents/workspace_service.py` gets `_displayable_documents(documents) -> (documents, counts)`, used by `load_documents` and by the reload after a failed Delete All; `take_replaced_character_count` pops the count.
8. **The `Mock` service harness** gets `take_recovered_document_names.return_value = []` (Task 1) and `take_replaced_character_count.return_value = 0` (Task 2), as the spec says.
9. **Catalogs.** `msgmerge` fuzzy-matches `Documents Recovered` to `Documents` (`文件`) in Task 1 (`364 translated messages, 1 fuzzy translation, 1 untranslated message.`); the plan's block drops the flag and fills both. In Task 2 nothing is fuzzy (two untranslated). Both regenerations also refresh the `#:` references that F-8a's line moves left stale. `git diff main -- client/locales` changes only the four entries and reference lines.
10. **Message boxes on Windows.** wx shows a message with a blank line as a task dialog whose first paragraph is the main instruction and the rest the content: the recovery box reads `DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：` / `alpha\n\n請確認內容是否正確。`, the U+0000 box `文件「alpha」中有 2 個無法顯示的字元，已全部以替代字元 <U+FFFD> 標示，後面的文字都保留下來了。` / `轉譯前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。` (U+FFFD shown as `<U+FFFD>`). UIA does not expose the icon; the unit tests pin `ICON_INFORMATION` and `ICON_WARNING`, and manual item 83 covers what NVDA reads.
11. **Windows items.** "Before" is `D:\dxtest\N-f8a2\DotExpress.exe` (F-8a after its review). The boxes that startup shows come before the main window (they are shown inside the frame's constructor), so the scripts answer them while they wait for it. Items 74 and 75 import `zero.txt`, not `nul.txt`: `nul` is a reserved Windows name, so `nul.txt` is an import issue. Item 75's PDF is the spec probe's untagged `(A\000B)` page; its text imports as `A\x00B\n`. Before F-8b, items 73-75 also show the data loss on disk: after the documents were opened and the app closed, the packages hold only the text before the first U+0000.
12. **Item 70 gets a third start** (the plan's addition): after the recovery and a restart without a box, the script changes alpha's text, closes and starts again. See 13.
13. **A skipped leftover can be recovered at a later start (new Risk, measured).** Recovery skips a leftover while its name is taken or a listed document holds its content, and leaves it on disk (D3, F-3 D13). Those conditions are checked again at every start. So after an interrupted Rename of alpha to gamma, alpha is recovered and the staged `.gamma.dep.<8>.tmp` stays; once the user edits alpha, the next start recovers that staged copy as a new document `gamma` with the old text, and shows "已復原文件" naming `gamma` (item 70, third start, on the F-8b build). In the same way the leftover of a completed Rename comes back under the old name once the renamed document is edited, and the leftover of an interrupted Save comes back once its document is renamed or deleted. Nothing is lost; an extra document appears, possibly long after the crash, and the box names it. Avoiding it needs a decision the spec does not make (for example remembering handled leftovers, or renaming them out of the pattern, which touches the user's files): **open question for the user, not blocking**; this plan implements D3 as specified.

## Dry Run

The plan was executed on scratch clones of `main` at `1b19290` with a stand-in plan commit (this plan and the corrected spec files) on `fix/f8b-recovery-and-nul` (`$SP/f8bplan/r*`, never the main checkout), by F-8a's harness: it writes every `File:` block, applies every `Edit:` block exactly once (CRLF-aware), runs every `bash` block from `client/` with `REPO` set to the clone and `MAIN` to the main checkout (so Task 0's guarded copies filled the clone, and the application-data check read the real data read-only), and compares its stdout with the following `text` block. Task 4 needs the desktop and is not part of the replay. The final replay (Tasks 0-3 from a fresh clone) matched every expected block, including all red runs, the catalog steps, the per-commit tree ids, the six shuffle seeds and the mutation output; no `client/log`, `client/workspace`, `client/dictionary` or `client/config.json` appeared in the clone. A second fresh clone ran Task 0 Step 3's bootstrap command and then applied every step with that `apply_blocks.py` (the catalog commands of Task 1 Step 4-5 and Task 2 Step 4-5 run as written), committing at the end of each task: the block counts of Task 0 Step 3 and the tree ids below.

Task 4 was run too. The second clone, at Task 2 (`HEAD:client` `667b2d2ce22f0a32996f68aa12eaaf23bc980071`), was built with Task 4 Step 1's command (PyInstaller 6.21.0, "Build complete!" in 44 s, 48,761,109 bytes; the two changed modules and `gui.py` from the clone; copied to `D:\dxtest\dryN2-f8b`), and Task 4 Step 2's scripts, written by `apply_blocks.py`, ran with Step 3's loop against `D:\dxtest\N-f8a2\DotExpress.exe` and against that build, in `D:\dxtest\dry*-f8b` folders that were deleted afterwards (no `D:\dxtest\auto*-f8b` folder exists yet). They printed exactly the logs of Step 4, each item once, with no re-run; an earlier run of the same scripts against a build of the development clone gave the same twelve logs. Drafts of the scripts found two tool problems, fixed before those runs: `nul.txt` is a reserved Windows name (an import issue, so the import never happened), and the file dialog does not take a single file name in quotes. No script wrote to the clipboard. Item 83 (manual) was not run.

## Review Focus

1. **Recovery never deletes or replaces** (D3): `os.rename` only, after the name and content rules; skipped files stay byte-identical; a failed rename is logged and leaves the file (D1-D9, D12; 9 mutants; GUI 70-72).
2. **The interrupted Rename comes back under its old name** (oldest first) and the staged twin stays (D1, `test_documents_are_recovered_oldest_first`; GUI 70); the recovery box comes after the invalid-files dialog and before the first document opens (D13).
3. **U+0000 never reaches the editors** (D12): the controller gets U+FFFD at load, import and the Delete All reload; the record keeps the package as read, so the first save writes the replaced text and an unopened document keeps its package (E3-E9; GUI 73).
4. **The notice is shown once per document, when it is first opened** (D13), after the editors hold the full text (E10-E13; GUI 73-75).
5. **Catalogs and strings:** four msgids, 368 translated, 0 fuzzy (the `Documents Recovered` fuzzy match is fixed); `{names}`, `{name}`, `{count}`, `{mark}` are `python-brace-format`; U+FFFD comes in through `{mark}` (F1).
6. **The open question of Spec Corrections 13** (a skipped leftover recovered at a later start).

## File Map

- Task 1: `client/tests/test_document_workspace.py` (log isolation, `RecoverInterruptedPackagesTest`: 11 tests), `client/tests/test_workspace_service.py` (log isolation, 3 tests), `client/tests/test_gui_document_flows.py` (D13, the `Mock` harness), `client/tests/test_i18n.py` (F1, recovery); `client/documents/workspace.py` (`_INTERRUPTED_PACKAGE`, `_read_package`, `recover_interrupted_packages`, `log` import), `client/documents/workspace_service.py` (`load_documents`, `take_recovered_document_names`, module docstring), `client/gui.py` (`_load_workspace_documents_at_startup`); the three catalogs.
- Task 2: `client/tests/test_document_workspace.py` (`ReplaceNulCharactersTest`: 2 tests), `client/tests/test_workspace_service.py` (`ReplacedNulCharactersTest`: 7 tests), `client/tests/test_gui_document_flows.py` (5 tests, the `Mock` harness), `client/tests/test_i18n.py` (F1, U+0000); `client/documents/workspace.py` (`replace_nul_characters`, `_displayable`), `client/documents/workspace_service.py` (`_displayable_documents`, `_nul_pending`, `load_documents`, `take_replaced_character_count`, `import_files`, `rename_document`, `delete_document`, `delete_all_documents`, module docstring), `client/gui.py` (`_open_document_by_name`); the three catalogs.
- Task 4: `docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/` (`auto/f8bgui.py`, `auto/item70.py`, `auto/item73.py`, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | msgids | `HEAD:client` |
| --- | --- | --- | --- | --- | --- |
| baseline (`1b19290` + plan) | - | 1403 | `FAILED (errors=1, skipped=7)` | 364 | `1d6780c8f7a5e53bc494e0c54bbeadcb0fdea500` |
| 1 recovery | 16 (D: 15; F: 1) | 1419 | `FAILED (errors=1, skipped=7)` | 366 | `b61ee7abb5e394733453ce6ea286561ef0e19377` |
| 2 U+0000 | 15 (E: 14; F: 1) | 1434 | `FAILED (errors=1, skipped=7)` | 368 | `667b2d2ce22f0a32996f68aa12eaaf23bc980071` |
| 4 GUI results (docs only) | - | 1434 | `FAILED (errors=1, skipped=7)` | 368 | `667b2d2ce22f0a32996f68aa12eaaf23bc980071` |

The error is F-W6 throughout; the 7 skips are POSIX-only tests. The spec's acceptance-criterion-2 set goes from `Ran 537`, `OK (skipped=7)` to `Ran 568`, `OK (skipped=7)`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 by the block script: `brief.py`, `msgid_scan.py` and `shuffle_harness.py` (F-8a's, unchanged), `pin_pot_date.py` (F-6's, unchanged), `mo_check.py` (F-6's, listing the four F-8b msgids), `f8b_mutants.py` (24 mutants of the code after Task 2, run on a copy of `client/`; the repository is never changed) and `apply_blocks.py` (F-8a's, applies the `File:` and `Edit:` blocks of one step of this plan).

---

### Task 0: Baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short -- client docs scripts
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO rev-parse HEAD~1 HEAD~1:client
git -C $REPO diff --stat 1b19290 -- client
```

Expected (`status` and the diff print nothing; `HEAD~1` is `main` at `1b19290`):

```text
docs: plan for recovering interrupted saves and replacing U+0000 (F-8b)
fix/f8b-recovery-and-nul
1b19290aca0ac540914602e602189cc5e069d911
1d6780c8f7a5e53bc494e0c54bbeadcb0fdea500
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

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed). `brief.py`, `msgid_scan.py` and `shuffle_harness.py` are F-8a's, `pin_pot_date.py` is F-6's, all unchanged; `mo_check.py` is F-6's with the F-8b msgids; `apply_blocks.py` is F-8a's with its docstring naming this plan.

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
each msgid that F-8b adds, with newlines shown as \\n (msgfmt 0.23 leaves
POT-Creation-Date out of the .mo header, so the .mo does not depend on it). A msgid the
catalog does not hold prints as "(missing)". Output is UTF-8 (-I ignores
PYTHONIOENCODING).
"""
import gettext
import sys

sys.stdout.reconfigure(encoding="utf-8")

MSGIDS = (
    "Documents Recovered",
    "DotExpress was interrupted while saving or renaming a document. These documents were "
    "recovered:\n\n{names}\n\nCheck that their content is what you expect.",
    "Characters Replaced",
    'Some characters in document "{name}" cannot be shown ({count} in all). Each one has been '
    "replaced with the replacement character {mark}, so the text after it is kept.\n\n"
    "Delete or change these {mark} characters before converting. Otherwise each one "
    "appears in the braille as an escape code.",
)

with open(sys.argv[1], "rb") as stream:
    catalog = gettext.GNUTranslations(stream)
print("catalog keys:", len(catalog._catalog))
for msgid in MSGIDS:
    translated = catalog._catalog.get(msgid, "(missing)")
    print(f"{msgid[:40]!r} -> {translated}".replace("\n", "\\n"))
````

File: `$T/tools/f8b_mutants.py`

````python
"""Run the F-8b tests against deliberately broken code (throwaway, not committed).

Usage: python f8b_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one file of the copy (one exact, unique replacement), runs the F-8b test
modules there, prints which tests caught it and restores the file. The repository is
never changed. Matches the code after Task 2. Exit status 1 if a mutant is not caught or
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
RECOVERY_BOX = (
	"\t\t# Documents put back from the temporary files of an interrupted save or rename (F-8).\n"
	"\t\trecovered_names = self._workspace_service.take_recovered_document_names()\n"
	"\t\tif recovered_names:\n"
	"\t\t\tself.show_info(\n"
	"\t\t\t\t_(\n"
	'\t\t\t\t\t"DotExpress was interrupted while saving or renaming a document. These documents were "\n'
	'\t\t\t\t\t"recovered:\\n\\n{names}\\n\\nCheck that their content is what you expect."\n'
	'\t\t\t\t).format(names="\\n".join(recovered_names)),\n'
	'\t\t\t\t_("Documents Recovered"),\n'
	"\t\t\t)\n"
)
REVIEW = "\t\tself._review_invalid_workspace_files(invalid_paths)\n"
MUTANTS = {
	# D3: recovery never deletes or replaces, oldest first, valid packages only.
	"recovery-deletes-a-skipped-file": (
		WORKSPACE,
		"        if folded in taken or (document.text, document.braille) in contents:\n            continue\n",
		"        if folded in taken or (document.text, document.braille) in contents:\n            path.unlink()\n            continue\n",
	),
	"recovery-with-os-replace": (
		WORKSPACE,
		'            os.rename(path, directory / f"{stem}{DEP_EXTENSION}")\n',
		'            os.replace(path, directory / f"{stem}{DEP_EXTENSION}")\n',
	),
	"no-content-duplicate-rule": (
		WORKSPACE,
		"        if folded in taken or (document.text, document.braille) in contents:\n",
		"        if folded in taken:\n",
	),
	"no-name-rule": (
		WORKSPACE,
		"        if folded in taken or (document.text, document.braille) in contents:\n",
		"        if (document.text, document.braille) in contents:\n",
	),
	"newest-first": (
		WORKSPACE,
		"sorted(candidates, key=lambda candidate: candidate[:3])",
		"sorted(candidates, key=lambda candidate: candidate[:3], reverse=True)",
	),
	"recovers-invalid-archives": (
		WORKSPACE,
		"            document = _read_package(path, stem)\n",
		"            try:\n                document = _read_package(path, stem)\n            except Exception:\n                document = Document(stem, \"\", None)\n",
	),
	"recovers-in-the-delete-all-reload": (
		SERVICE,
		"                remaining_documents, invalid_paths = load_workspace_documents(self._workspace_dir)\n",
		"                remaining_documents, invalid_paths = load_workspace_documents(self._workspace_dir)\n"
		"                remaining_documents += recover_interrupted_packages(self._workspace_dir, remaining_documents)\n",
	),
	"recovered-documents-not-sorted": (
		SERVICE,
		"        documents = sorted([*documents, *recovered], key=lambda document: (document.name.casefold(), document.name))\n",
		"        documents = [*documents, *recovered]\n",
	),
	"recovered-names-reported-every-time": (
		SERVICE,
		"        names, self._recovered_names = self._recovered_names, []\n",
		"        names = list(self._recovered_names)\n",
	),
	# D4: the recovery box.
	"no-recovery-box": (GUI, "\t\tif recovered_names:\n", "\t\tif False:\n"),
	"recovery-box-before-the-invalid-files-dialog": (GUI, REVIEW + RECOVERY_BOX, RECOVERY_BOX + REVIEW),
	# D12: U+0000 where documents enter the app.
	"braille-not-counted": (
		WORKSPACE,
		"    return Document(name=document.name, text=text, braille=braille), count + braille_count\n",
		"    return Document(name=document.name, text=text, braille=braille), count\n",
	),
	"load-gives-the-raw-text": (
		SERVICE,
		"        self._controller.load_documents(displayable)\n",
		"        self._controller.load_documents(documents)\n",
	),
	"record-built-from-the-replaced-text": (
		SERVICE,
		"        self._reset_saved(documents)\n        return invalid_paths\n",
		"        self._reset_saved(displayable)\n        return invalid_paths\n",
	),
	"nul-replaced-in-encodable": (
		WORKSPACE,
		"    return Document(name=document.name, text=replace_lone_surrogates(document.text), braille=braille)\n",
		'    return Document(name=document.name, text=replace_lone_surrogates(document.text).replace("\\x00", "\ufffd"), braille=braille)\n',
	),
	"import-saves-the-raw-text": (
		SERVICE,
		"            document, count = _displayable(document)\n",
		"            count = _displayable(document)[1]\n",
	),
	"import-not-counted": (
		SERVICE,
		"            if count:\n                self._nul_pending[document.name] = count\n",
		"",
	),
	"count-not-moved-on-rename": (
		SERVICE,
		"        if source_name in self._nul_pending:\n            self._nul_pending[new_name] = self._nul_pending.pop(source_name)\n",
		"",
	),
	"count-kept-after-delete": (SERVICE, "        self._nul_pending.pop(name, None)\n", ""),
	"counts-kept-after-delete-all": (SERVICE, "        self._saved = {}\n        self._nul_pending = {}\n", "        self._saved = {}\n"),
	"delete-all-reload-gives-the-raw-text": (
		SERVICE,
		"                self._controller.restore_documents_after_delete_all_failure(displayable)\n",
		"                self._controller.restore_documents_after_delete_all_failure(remaining_documents)\n",
	),
	"delete-all-reload-counts-again": (
		SERVICE,
		"                self._nul_pending = {name: count for name, count in self._nul_pending.items() if name in remaining}\n",
		"                self._nul_pending = _counts\n",
	),
	# D13: the notice.
	"notice-on-every-open": (SERVICE, "        return self._nul_pending.pop(name, 0)\n", "        return self._nul_pending.get(name, 0)\n"),
	"no-notice": (GUI, "\t\tif replaced:\n", "\t\tif False:\n"),
}
MODULES = (
	"tests.test_document_workspace",
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
"""Apply the File: and Edit: blocks of one step of the F-8b plan (throwaway, not committed).

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
PLAN=$REPO/docs/superpowers/plans/2026-10-10-f8b-recovery-and-nul.md
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
wrote $T/tools/f8b_mutants.py
wrote $T/tools/apply_blocks.py
7 blocks applied (Task 0, Step 3)
```

From then on apply every step's blocks with `apply_blocks.py`, for example `$PY $T/tools/apply_blocks.py ../docs/superpowers/plans/2026-10-10-f8b-recovery-and-nul.md $REPO $T "Task 1" "Step 1"`; it prints `N blocks applied` (Task 0 Step 3: 7; Task 1 Step 1: 9, Step 2: 9, Step 5: 1; Task 2 Step 1: 5, Step 2: 13, Step 5: 1; Task 4 Step 2: 3).

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
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO rev-parse HEAD:client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) > $T/app-data.sha256; wc -l < $T/app-data.sha256
```

Expected (the second `Ran` line is the spec's acceptance-criterion-2 set; the four F-8b msgids are missing; the last line counts the files of the user's application data in the main checkout, including `client/log/`, recorded read-only for Task 3; if the user has used the app since the dry run, that number differs, which is fine):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1403 tests
FAILED (errors=1, skipped=7)
Ran 537 tests
OK (skipped=7)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
source msgids: 364 sha256 7b53ff311c9e446767b0884bfc03148afe030ca7e15899d6ee6919e77c664ea7
locales/dotexpress.pot:365
locales/zh_TW/LC_MESSAGES/dotexpress.po:365
364 translated messages.
msgfmt rebuilds the committed .mo byte for byte
catalog keys: 365
'Documents Recovered' -> (missing)
'DotExpress was interrupted while saving ' -> (missing)
'Characters Replaced' -> (missing)
'Some characters in document "{name}" can' -> (missing)
1d6780c8f7a5e53bc494e0c54bbeadcb0fdea500
4
```

### Task 1: Recover documents whose save or rename was interrupted (D3-D5)

- [ ] **Step 1: Red: Test Plan D and the recovery half of F; log isolation; the `Mock` harness.** `test_document_workspace.py` gets a `setUpModule` that isolates `dotexpress.gui` and the class `RecoverInterruptedPackagesTest` (11 tests; D9 runs on Windows only); `test_workspace_service.py` gets the same `setUpModule` and three tests (D11, a load without leftovers, D12); `test_gui_document_flows.py` gets D13 and `take_recovered_document_names.return_value = []` in the `Mock` harness (Spec Corrections 8); `test_i18n.py` gets `test_recovery_strings_are_translated` (Spec Corrections 2). All four files use 4 spaces. The leftovers are written as the F-8 probe found them: `PackageFiles().write` into `.<name>.dep.<8 characters>.tmp` (a Rename's moved-aside or staged package, the moved-aside one an hour or a minute older) or `.<name>.dep.<16 hex>.tmp` (a Save).

Edit: `client/tests/test_document_workspace.py`

```python
import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
```

```python
import os
import stat
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
```

Edit: `client/tests/test_document_workspace.py`

```python
)
from shared import name_validation
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.windows_file_handles import SHARE_MODES, hold_open, is_hidden, make_hidden, make_read_only


class DocumentWorkspaceTest(unittest.TestCase):
```

```python
)
from shared import name_validation
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.file_log_isolation import isolate_file_logs
from tests.windows_file_handles import SHARE_MODES, hold_open, is_hidden, make_hidden, make_read_only


def setUpModule() -> None:
    # Recovery logs a failed rename to dotexpress.gui (F-8 D3): never to the real gui.log.
    unittest.addModuleCleanup(isolate_file_logs("dotexpress.gui"))


class DocumentWorkspaceTest(unittest.TestCase):
```

Edit: `client/tests/test_document_workspace.py`

```python
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "y�", "1"))


if __name__ == "__main__":
    unittest.main()
```

```python
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "y�", "1"))


class RecoverInterruptedPackagesTest(unittest.TestCase):
    """Startup puts back a package that a crash left only in a temporary file (F-8 D3).

    The leftovers are written as the F-8 probe found them: a Save writes
    ``.<name>.dep.<16 hex>.tmp`` and a Rename uses ``.<name>.dep.<8 characters>.tmp`` for the
    staged new package and for the old package moved aside, which keeps its older
    modification time.
    """

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.workspace_dir = Path(temp_dir.name) / "workspace"
        self.workspace_dir.mkdir()

    def _leftover(self, file_name: str, document: Document, *, age_s: int = 0) -> Path:
        """``file_name`` holding ``document`` as a package, last modified ``age_s`` seconds ago."""
        path = self.workspace_dir / file_name
        workspace.PackageFiles().write(path, document)
        modified = time.time_ns() - age_s * 1_000_000_000
        os.utime(path, ns=(modified, modified))
        return path

    def _raw_leftover(self, file_name: str, member_stem: str) -> Path:
        """``file_name`` holding a package whose members are ``<member_stem>.txt`` and ``.brl``."""
        path = self.workspace_dir / file_name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(f"{member_stem}.txt", "text")
            archive.writestr(f"{member_stem}.brl", "1")
        return path

    def _recover(self, listed=()) -> list[Document]:
        # Nothing is logged: a skipped file never even reaches os.rename (which on Windows
        # would refuse a taken name and log it).
        with self.assertNoLogs("dotexpress.gui"):
            return workspace.recover_interrupted_packages(self.workspace_dir, list(listed))

    def _listing(self) -> list[str]:
        return sorted(path.name for path in self.workspace_dir.iterdir())

    def _snapshot(self) -> dict[str, bytes]:
        return {path.name: path.read_bytes() for path in self.workspace_dir.iterdir()}

    def test_interrupted_rename_is_recovered_under_the_old_name(self) -> None:
        # Rename alpha -> gamma crashed after the move aside, before the install: no .dep.
        aside = self._leftover(".alpha.dep._vw4x6f_.tmp", Document("alpha", "text", "1"), age_s=60)
        before = aside.read_bytes()
        staged = self._leftover(".gamma.dep.mlw4jang.tmp", Document("gamma", "text", "1"))
        staged_bytes = staged.read_bytes()

        recovered = self._recover()

        self.assertEqual(recovered, [Document("alpha", "text", "1")])
        self.assertEqual(self._listing(), [".gamma.dep.mlw4jang.tmp", "alpha.dep"])
        self.assertEqual((self.workspace_dir / "alpha.dep").read_bytes(), before)
        self.assertEqual(staged.read_bytes(), staged_bytes)
        self.assertEqual(load_document_package(self.workspace_dir / "alpha.dep"), Document("alpha", "text", "1"))

    def test_leftover_of_a_completed_rename_is_not_recovered(self) -> None:
        # The rename installed gamma.dep, then removing the moved-aside alpha failed.
        gamma = Document("gamma", "text", "1")
        save_document_package(self.workspace_dir / "gamma.dep", gamma)
        self._leftover(".alpha.dep.7gdjw2yi.tmp", Document("alpha", "text", "1"), age_s=60)
        before = self._snapshot()

        self.assertEqual(self._recover([gamma]), [])

        self.assertEqual(self._snapshot(), before)

    def test_leftover_save_next_to_its_package_is_not_recovered(self) -> None:
        # The save wrote and synced its temporary file, then crashed before os.replace:
        # from the user's point of view that save never completed.
        alpha = Document("alpha", "old text", "1")
        save_document_package(self.workspace_dir / "alpha.dep", alpha)
        self._leftover(".alpha.dep.97dc8315c5cf865f.tmp", Document("alpha", "new text", "1"))
        before = self._snapshot()

        self.assertEqual(self._recover([alpha]), [])

        self.assertEqual(self._snapshot(), before)

    def test_invalid_and_empty_temporary_files_are_ignored(self) -> None:
        complete = self._leftover(".delta.dep.0123456789abcdef.tmp", Document("delta", "text", "1"))
        (self.workspace_dir / ".gamma.dep.x2y3z4w5.tmp").write_bytes(complete.read_bytes()[:40])
        complete.unlink()
        (self.workspace_dir / ".alpha.dep.0123456789abcdef.tmp").write_bytes(b"not a zip")
        (self.workspace_dir / ".beta.dep.k2j1abcd.tmp").write_bytes(b"")
        before = self._snapshot()

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._snapshot(), before)

    def test_name_held_by_an_unlisted_package_is_not_recovered(self) -> None:
        # An invalid package kept at startup holds the name in another case.
        (self.workspace_dir / "ALPHA.dep").write_bytes(b"not a zip")
        self._leftover(".alpha.dep.k2j1abcd.tmp", Document("alpha", "text", "1"))
        before = self._snapshot()

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._snapshot(), before)

    def test_names_that_are_not_valid_document_names_are_ignored(self) -> None:
        # Names a Windows folder can hold but a document cannot have.
        too_long = "x" * 33
        for stem in (" alpha", "alpha ", "alpha.", too_long, "CON"):
            self._raw_leftover(f".{stem}.dep.k2j1abcd.tmp", stem)
        before = self._snapshot()

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._snapshot(), before)

    def test_member_names_must_match_the_temporary_file_name(self) -> None:
        self._raw_leftover(".alpha.dep.k2j1abcd.tmp", "beta")
        self._raw_leftover(".gamma.dep.k2j1abcd.tmp", "Gamma")
        before = self._snapshot()

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._snapshot(), before)

    def test_files_that_are_not_package_leftovers_are_ignored(self) -> None:
        self._leftover("alpha.tmp", Document("alpha", "text", "1"))
        self._leftover(".beta.txt.k2j1abcd.tmp", Document("beta", "text", "2"))
        self._leftover(".gamma.dep.k2j1abcd.bak", Document("gamma", "text", "3"))
        (self.workspace_dir / ".delta.dep.k2j1abcd.tmp").mkdir()
        before = sorted(self._listing())

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._listing(), before)

    def test_recovery_never_deletes_or_replaces_a_file(self) -> None:
        self._leftover(".alpha.dep._vw4x6f_.tmp", Document("alpha", "text", "1"), age_s=60)
        self._leftover(".gamma.dep.mlw4jang.tmp", Document("gamma", "text", "1"))
        save_document_package(self.workspace_dir / "beta.dep", Document("beta", "b", "2"))
        self._leftover(".beta.dep.97dc8315c5cf865f.tmp", Document("beta", "newer", "2"))
        (self.workspace_dir / ".delta.dep.k2j1abcd.tmp").write_bytes(b"")
        recorders = [
            patch("os.unlink", wraps=os.unlink),
            patch("os.remove", wraps=os.remove),
            patch("os.replace", wraps=os.replace),
            patch("pathlib.Path.unlink", autospec=True, wraps=Path.unlink),
            patch("shutil.rmtree"),
        ]
        mocks = [recorder.start() for recorder in recorders]
        for recorder in recorders:
            self.addCleanup(recorder.stop)

        recovered = self._recover([Document("beta", "b", "2")])

        self.assertEqual(recovered, [Document("alpha", "text", "1")])
        self.assertEqual([mock.call_count for mock in mocks], [0, 0, 0, 0, 0])
        self.assertEqual(
            self._listing(),
            [".beta.dep.97dc8315c5cf865f.tmp", ".delta.dep.k2j1abcd.tmp", ".gamma.dep.mlw4jang.tmp", "alpha.dep", "beta.dep"],
        )

    def test_documents_are_recovered_oldest_first(self) -> None:
        # Two interrupted renames: each old package comes back under its own name; their
        # staged twins hold the same text and stay.
        self._leftover(".beta.dep.aaaaaaaa.tmp", Document("beta", "b", "2"), age_s=120)
        self._leftover(".alpha.dep.bbbbbbbb.tmp", Document("alpha", "a", "1"), age_s=60)
        self._leftover(".zeta.dep.cccccccc.tmp", Document("zeta", "a", "1"), age_s=30)
        self._leftover(".delta.dep.dddddddd.tmp", Document("delta", "b", "2"))

        recovered = self._recover()

        self.assertEqual(recovered, [Document("beta", "b", "2"), Document("alpha", "a", "1")])
        self.assertEqual(
            self._listing(),
            [".delta.dep.dddddddd.tmp", ".zeta.dep.cccccccc.tmp", "alpha.dep", "beta.dep"],
        )

    @unittest.skipUnless(os.name == "nt", "os.rename never replaces an existing file on Windows")
    def test_recovery_does_not_replace_a_file_created_meanwhile(self) -> None:
        # Another program creates alpha.dep between the disk check and the rename.
        leftover = self._leftover(".alpha.dep.k2j1abcd.tmp", Document("alpha", "text", "1"))
        before = leftover.read_bytes()
        target = self.workspace_dir / "alpha.dep"
        real_rename = os.rename

        def create_then_rename(source, destination):
            Path(destination).write_bytes(b"created meanwhile")
            real_rename(source, destination)

        with patch("os.rename", side_effect=create_then_rename), self.assertLogs("dotexpress.gui", "ERROR") as logs:
            recovered = workspace.recover_interrupted_packages(self.workspace_dir, [])

        self.assertEqual(recovered, [])
        self.assertEqual(target.read_bytes(), b"created meanwhile")
        self.assertEqual(leftover.read_bytes(), before)
        self.assertEqual(len(logs.records), 1)
        self.assertTrue(
            logs.records[0].getMessage().startswith(
                f"Cannot recover interrupted document package {leftover}: [WinError 183] "
            ),
            logs.records[0].getMessage(),
        )
        self.assertIsNone(logs.records[0].exc_info)


if __name__ == "__main__":
    unittest.main()
```

Edit: `client/tests/test_workspace_service.py`

```python
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from shared import name_validation
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.full_disk import full_disk
from tests.windows_file_handles import SHARE_DELETE, SHARE_MODES, hold_open, make_read_only

NO_SPACE = f"[Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}"

```

```python
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from shared import name_validation
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.file_log_isolation import isolate_file_logs
from tests.full_disk import full_disk
from tests.windows_file_handles import SHARE_DELETE, SHARE_MODES, hold_open, make_read_only


def setUpModule() -> None:
    # load_documents can log a failed recovery to dotexpress.gui (F-8 D3): never to the real gui.log.
    unittest.addModuleCleanup(isolate_file_logs("dotexpress.gui"))


NO_SPACE = f"[Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}"

```

Edit: `client/tests/test_workspace_service.py`

```python

        self.assertEqual(invalid_paths, [self.workspace / "bad.dep"])
        self.assertEqual(self.controller.documents, [Document("Alpha", "a", None), Document("beta", "b", "2")])

    def test_delete_invalid_files_reports_each_error_and_continues(self) -> None:
        blocked = self._block("a-blocked")
```

```python

        self.assertEqual(invalid_paths, [self.workspace / "bad.dep"])
        self.assertEqual(self.controller.documents, [Document("Alpha", "a", None), Document("beta", "b", "2")])

    def _interrupted_rename(self, old_name: str, new_name: str, text: str) -> None:
        """The two temporary files a crash inside Rename leaves: the old package moved aside
        (with its older modification time) and the staged new one (F-8 D3)."""
        self.workspace.mkdir(exist_ok=True)
        files = PackageFiles()
        aside = self.workspace / f".{old_name}.dep._vw4x6f_.tmp"
        files.write(aside, Document(old_name, text, "1"))
        older = aside.stat().st_mtime_ns - 60_000_000_000
        os.utime(aside, ns=(older, older))
        files.write(self.workspace / f".{new_name}.dep.mlw4jang.tmp", Document(new_name, text, "1"))

    def test_load_documents_recovers_and_reports_names_once(self) -> None:
        self._write(Document("beta", "b", "2"))
        self._interrupted_rename("alpha", "gamma", "a")
        service = self._service()

        self.assertEqual(service.load_documents(), [])

        self.assertEqual(self.controller.documents, [Document("alpha", "a", "1"), Document("beta", "b", "2")])
        self.assertEqual(self._listing(), [".gamma.dep.mlw4jang.tmp", "alpha.dep", "beta.dep"])
        self.assertEqual(service.take_recovered_document_names(), ["alpha"])
        self.assertEqual(service.take_recovered_document_names(), [])
        # The recovered package is recorded as loaded: an unchanged save writes nothing (F-5).
        self.controller.open_document("alpha")
        with patch.object(workspace_service, "save_document_package") as save:
            service.save_open_document(text="a", braille="1")
        save.assert_not_called()

    def test_load_documents_without_leftovers_recovers_nothing(self) -> None:
        self._write(Document("alpha", "a", "1"))
        service = self._service()

        self.assertEqual(service.load_documents(), [])

        self.assertEqual(service.take_recovered_document_names(), [])
        self.assertEqual(self.controller.documents, [Document("alpha", "a", "1")])

    def test_delete_invalid_files_reports_each_error_and_continues(self) -> None:
        blocked = self._block("a-blocked")
```

Edit: `client/tests/test_workspace_service.py`

```python
        self.assertEqual(calls, ["on_error"])
        self.assertEqual(self.controller.documents, documents)


class SaveOnlyWhenChangedTest(unittest.TestCase):
    """Save writes only when the open document differs from its last write or load (F-5, D1-D3).
```

```python
        self.assertEqual(calls, ["on_error"])
        self.assertEqual(self.controller.documents, documents)

    def test_delete_all_failure_reload_does_not_recover(self) -> None:
        # Only startup recovers (F-8 D3): the reload after a failed Delete All lists what
        # is on disk and leaves the temporary files alone.
        documents = [Document("alpha", "a", "1"), Document("beta", "b", "2")]
        self._write(documents[0])
        self._block("beta")
        self._interrupted_rename("delta", "gamma", "d")
        service = self._service(documents)

        result = service.delete_all_documents(on_error=lambda _error: None)

        self.assertFalse(result.completed)
        self.assertEqual(self.controller.documents, [])
        self.assertEqual(service.take_recovered_document_names(), [])
        self.assertEqual(self._listing(), [".delta.dep._vw4x6f_.tmp", ".gamma.dep.mlw4jang.tmp", "beta.dep"])


class SaveOnlyWhenChangedTest(unittest.TestCase):
    """Save writes only when the open document differs from its last write or load (F-5, D1-D3).
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        # F-8 (D1, D2): a bare Mock would answer "taken" and loop the name prompt.
        frame._workspace_service.package_name_taken.return_value = False
        frame._workspace_service.free_document_name.side_effect = lambda base: base
        frame.input_txt = Mock()
        frame.output_txt = Mock()
        frame._show_file_error = Mock()
```

```python
        # F-8 (D1, D2): a bare Mock would answer "taken" and loop the name prompt.
        frame._workspace_service.package_name_taken.return_value = False
        frame._workspace_service.free_document_name.side_effect = lambda base: base
        # F-8 (D4): a bare Mock would be a truthy list of recovered names.
        frame._workspace_service.take_recovered_document_names.return_value = []
        frame.input_txt = Mock()
        frame.output_txt = Mock()
        frame._show_file_error = Mock()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._package("new (2)"), Document("new (2)", "", None))
        self.assertEqual(frame._document_controller.document_names, ["new (2)"])
        self.assertEqual(frame._document_controller.open_name, "new (2)")

    # --- save --------------------------------------------------------------

```

```python
        self.assertEqual(self._package("new (2)"), Document("new (2)", "", None))
        self.assertEqual(frame._document_controller.document_names, ["new (2)"])
        self.assertEqual(frame._document_controller.open_name, "new (2)")

    def _interrupted_rename(self, old_name: str, new_name: str, text: str, age_s: int) -> None:
        """What a crash inside Rename leaves: the old package moved aside, ``age_s`` seconds
        old, and the staged new one, written now (F-8 D3)."""
        self.workspace.mkdir(exist_ok=True)
        files = PackageFiles()
        aside = self.workspace / f".{old_name}.dep._vw4x6f_.tmp"
        files.write(aside, Document(old_name, text, "1"))
        older = aside.stat().st_mtime_ns - age_s * 1_000_000_000
        os.utime(aside, ns=(older, older))
        files.write(self.workspace / f".{new_name}.dep.mlw4jang.tmp", Document(new_name, text, "1"))

    def test_startup_reports_recovered_documents(self) -> None:
        # F-8 (D3, D4): two interrupted renames, and an invalid package kept at startup.
        self._interrupted_rename("beta", "delta", "b", 120)
        self._interrupted_rename("alpha", "gamma", "a", 60)
        (self.workspace / "bad.dep").write_bytes(b"not a zip")
        frame = self._make_workspace_frame()

        frame._load_workspace_documents_at_startup()

        message = gui._(
            "DotExpress was interrupted while saving or renaming a document. These documents were "
            "recovered:\n\n{names}\n\nCheck that their content is what you expect."
        ).format(names="beta\nalpha")
        self.assertEqual(
            self.events,
            [
                ("InvalidWorkspaceFilesDialog", [self.workspace / "bad.dep"]),
                ("MessageBox", message, gui._("Documents Recovered"), gui.wx.OK | gui.wx.ICON_INFORMATION, frame),
                ("title", "alpha - DotExpress"),
                ("title", "alpha - DotExpress"),
            ],
        )
        self.assertEqual(frame._document_controller.document_names, ["alpha", "beta"])
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))
        self.assertEqual(
            self._listing(),
            [".delta.dep.mlw4jang.tmp", ".gamma.dep.mlw4jang.tmp", "alpha.dep", "bad.dep", "beta.dep"],
        )

    # --- save --------------------------------------------------------------

```

Edit: `client/tests/test_i18n.py`

```python
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```python
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_recovery_strings_are_translated(self) -> None:
        # F-8 (D4): the box that names the documents startup put back.
        message = (
            "DotExpress was interrupted while saving or renaming a document. These documents were "
            "recovered:\n\n{names}\n\nCheck that their content is what you expect."
        )
        expected = {
            "Documents Recovered": "已復原文件",
            message: "DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\n{names}\n\n請確認內容是否正確。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)
        self.assertEqual(
            translation.gettext(message).format(names="alpha\nbeta"),
            "DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\nalpha\nbeta\n\n請確認內容是否正確。",
        )

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

Run the four modules:

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (the eleven workspace tests and two service tests fail with `AttributeError`, the function and the method do not exist yet; D11 fails because nothing is recovered, so only `beta` is listed; D13 because the workspace frame starts with a new default document and no box; F because the catalog does not know the two msgids. The 2 skips are POSIX-only tests):

```text
ERROR: test_documents_are_recovered_oldest_first (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_documents_are_recovered_oldest_first)
AttributeError: module 'documents.workspace' has no attribute 'recover_interrupted_packages'
ERROR: test_files_that_are_not_package_leftovers_are_ignored (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_files_that_are_not_package_lefto
ERROR: test_interrupted_rename_is_recovered_under_the_old_name (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_interrupted_rename_is_recovere
ERROR: test_invalid_and_empty_temporary_files_are_ignored (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_invalid_and_empty_temporary_files_a
ERROR: test_leftover_of_a_completed_rename_is_not_recovered (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_leftover_of_a_completed_rename_is
ERROR: test_leftover_save_next_to_its_package_is_not_recovered (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_leftover_save_next_to_its_pack
ERROR: test_member_names_must_match_the_temporary_file_name (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_member_names_must_match_the_tempo
ERROR: test_name_held_by_an_unlisted_package_is_not_recovered (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_name_held_by_an_unlisted_packag
ERROR: test_names_that_are_not_valid_document_names_are_ignored (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_names_that_are_not_valid_docu
ERROR: test_recovery_does_not_replace_a_file_created_meanwhile (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_recovery_does_not_replace_a_fi
ERROR: test_recovery_never_deletes_or_replaces_a_file (tests.test_document_workspace.RecoverInterruptedPackagesTest.test_recovery_never_deletes_or_replaces_a_fi
ERROR: test_delete_all_failure_reload_does_not_recover (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_delete_all_failure_reload_does_not_recove
AttributeError: 'DocumentWorkspaceService' object has no attribute 'take_recovered_document_names'
ERROR: test_load_documents_without_leftovers_recovers_nothing (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_load_documents_without_leftovers_r
FAIL: test_load_documents_recovers_and_reports_names_once (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_load_documents_recovers_and_reports_na
AssertionError: Lists differ: [Document(name='beta', text='b', braille='2')] != [Document(name='alpha', text='a', braille='1'), Document([31 chars]'2')]
FAIL: test_startup_reports_recovered_documents (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_startup_reports_recovered_document
AssertionError: Lists differ: [('In[108 chars]), ('title', 'new - DotExpress'), ('focus', 'i[33 chars]ss')] != [('In[108 chars]), ('MessageBox', 'DotExpress was
FAIL: test_recovery_strings_are_translated (tests.test_i18n.TranslationTest.test_recovery_strings_are_translated)
AssertionError: {'Doc[15 chars]d': 'Documents Recovered', 'DotExpress was int[291 chars]ct.'} != {'Doc[15 chars]d': '已復原文件', 'DotExpress was interrupted while[1
Ran 346 tests
FAILED (failures=3, errors=13, skipped=2)
```

- [ ] **Step 2: Green: recovery in the workspace, the service and the frame.** `client/documents/workspace.py` and `client/documents/workspace_service.py` use 4 spaces, `client/gui.py` tabs.

Edit: `client/documents/workspace.py`

```python
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
from shared.atomic_write import ensure_writable, write_bytes_atomically, write_text_atomically
from shared.name_validation import normalize_base_name

```

```python
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
from log import get_logger
from shared.atomic_write import ensure_writable, write_bytes_atomically, write_text_atomically
from shared.name_validation import normalize_base_name

```

Edit: `client/documents/workspace.py`

```python
PENDING_METADATA_SUFFIX = ".meta.json"
DEFAULT_DOCUMENT_NAME = "new"
_LONE_SURROGATE = re.compile(r"[\ud800-\udfff]")


@dataclass(frozen=True)
```

```python
PENDING_METADATA_SUFFIX = ".meta.json"
DEFAULT_DOCUMENT_NAME = "new"
_LONE_SURROGATE = re.compile(r"[\ud800-\udfff]")
# ".<name>.dep.<random>.tmp": a Save's temporary file (16 hex digits) or the staged or
# moved-aside package of a Rename (8 characters of tempfile's alphabet).
_INTERRUPTED_PACKAGE = re.compile(r"^\.(?P<stem>.+)\.(?i:dep)\.[A-Za-z0-9_]+\.tmp$")


@dataclass(frozen=True)
```

Edit: `client/documents/workspace.py`

```python
    package_path = Path(path)
    if package_path.suffix.casefold() != DEP_EXTENSION:
        raise ValueError("Document package must use the .dep extension.")
    package_name = normalize_document_name(package_path.stem)
    with zipfile.ZipFile(package_path, "r") as archive:
        names = [info.filename for info in archive.infolist() if not info.is_dir()]
        txt_names = [name for name in names if name.endswith(".txt")]
```

```python
    package_path = Path(path)
    if package_path.suffix.casefold() != DEP_EXTENSION:
        raise ValueError("Document package must use the .dep extension.")
    return _read_package(package_path, normalize_document_name(package_path.stem))


def _read_package(package_path: Path, package_name: str) -> Document:
    """The document of the package archive at ``package_path``, whose members must be named ``package_name``."""
    with zipfile.ZipFile(package_path, "r") as archive:
        names = [info.filename for info in archive.infolist() if not info.is_dir()]
        txt_names = [name for name in names if name.endswith(".txt")]
```

Edit: `client/documents/workspace.py`

```python
    return documents, invalid_paths


def batch_import_documents(
    paths: list[Path | str],
    *,
```

```python
    return documents, invalid_paths


def recover_interrupted_packages(directory: Path, listed: list[Document]) -> list[Document]:
    """Put back the packages that a crash left only in temporary files (F-8); never deletes, never replaces.

    A Rename moves the old package aside to ``.<name>.dep.<random>.tmp`` before it
    installs the staged new one, and a Save writes ``.<name>.dep.<random>.tmp`` before it
    replaces the package, so a crash in between can leave a document only there. Each
    such file in ``directory`` that is a valid package of a valid document name is
    renamed to ``<name>.dep``, oldest first (a moved-aside package keeps the old
    package's modification time, so an interrupted Rename gives the document back under
    its old name, as a failed Rename does), unless a ``.dep`` of that name exists in any
    case or ``listed`` or a document recovered before it holds the same text and braille.
    Every other file stays as it is; a rename that fails is logged and leaves the file in
    place. Returns the recovered documents, in that order.
    """
    directory = Path(directory)
    candidates = []
    for path in sorted(directory.iterdir()):
        match = _INTERRUPTED_PACKAGE.match(path.name)
        if match is None or not path.is_file():
            continue
        stem = match.group("stem")
        try:
            if normalize_document_name(stem) != stem:
                continue
            document = _read_package(path, stem)
            modified = path.stat().st_mtime_ns
        except Exception:
            continue
        candidates.append((modified, stem.casefold(), stem, path, document))
    taken = {path.stem.casefold() for path in directory.glob(f"*{DEP_EXTENSION}")}
    contents = {(document.text, document.braille) for document in listed}
    recovered: list[Document] = []
    for _modified, folded, stem, path, document in sorted(candidates, key=lambda candidate: candidate[:3]):
        if folded in taken or (document.text, document.braille) in contents:
            continue
        try:
            # On Windows os.rename never replaces an existing file, unlike os.replace.
            os.rename(path, directory / f"{stem}{DEP_EXTENSION}")
        except OSError as error:
            # Bound here, not at import, so importing this module adds no file handler.
            get_logger("dotexpress.gui", "gui.log").error("Cannot recover interrupted document package %s: %s", path, error)
            continue
        taken.add(folded)
        contents.add((document.text, document.braille))
        recovered.append(document)
    return recovered


def batch_import_documents(
    paths: list[Path | str],
    *,
```

Edit: `client/documents/workspace_service.py`

```python
failed save is retried by the next one.
Add, Rename, Import and the default document never replace a package that is on disk
but not listed, such as an invalid one kept at startup: its name counts as taken.
"""

from __future__ import annotations
```

```python
failed save is retried by the next one.
Add, Rename, Import and the default document never replace a package that is on disk
but not listed, such as an invalid one kept at startup: its name counts as taken.
Startup puts back a package that a crash during Save or Rename left only in a
temporary file, and reports its name once; it never deletes or replaces a file.
"""

from __future__ import annotations
```

Edit: `client/documents/workspace_service.py`

```python
    load_workspace_documents,
    move_document_package,
    prepare_document_for_save,
    save_document_package,
)

```

```python
    load_workspace_documents,
    move_document_package,
    prepare_document_for_save,
    recover_interrupted_packages,
    save_document_package,
)

```

Edit: `client/documents/workspace_service.py`

```python
        self._workspace_dir = Path(workspace_dir)
        self._package_files = package_files or PackageFiles()
        self._saved: dict[str, _SavedPackage] = {}

    @property
    def workspace_dir(self) -> Path:
```

```python
        self._workspace_dir = Path(workspace_dir)
        self._package_files = package_files or PackageFiles()
        self._saved: dict[str, _SavedPackage] = {}
        self._recovered_names: list[str] = []

    @property
    def workspace_dir(self) -> Path:
```

Edit: `client/documents/workspace_service.py`

```python
    def load_documents(self) -> list[Path]:
        ensure_workspace_directory(self._workspace_dir)
        documents, invalid_paths = load_workspace_documents(self._workspace_dir)
        self._controller.load_documents(documents)
        self._reset_saved(documents)
        return invalid_paths

    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None:
        for path in paths:
```

```python
    def load_documents(self) -> list[Path]:
        ensure_workspace_directory(self._workspace_dir)
        documents, invalid_paths = load_workspace_documents(self._workspace_dir)
        recovered = recover_interrupted_packages(self._workspace_dir, documents)
        self._recovered_names = [document.name for document in recovered]
        documents = sorted([*documents, *recovered], key=lambda document: (document.name.casefold(), document.name))
        self._controller.load_documents(documents)
        self._reset_saved(documents)
        return invalid_paths

    def take_recovered_document_names(self) -> list[str]:
        """The documents the last ``load_documents`` put back from temporary files, once (F-8 D4)."""
        names, self._recovered_names = self._recovered_names, []
        return names

    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None:
        for path in paths:
```

Edit: `client/gui.py`

```python
		invalid_paths = self._workspace_service.load_documents()
		self._refresh_document_list()
		self._review_invalid_workspace_files(invalid_paths)
		self._ensure_open_document_exists()
		self._update_window_title()

```

```python
		invalid_paths = self._workspace_service.load_documents()
		self._refresh_document_list()
		self._review_invalid_workspace_files(invalid_paths)
		# Documents put back from the temporary files of an interrupted save or rename (F-8).
		recovered_names = self._workspace_service.take_recovered_document_names()
		if recovered_names:
			self.show_info(
				_(
					"DotExpress was interrupted while saving or renaming a document. These documents were "
					"recovered:\n\n{names}\n\nCheck that their content is what you expect."
				).format(names="\n".join(recovered_names)),
				_("Documents Recovered"),
			)
		self._ensure_open_document_exists()
		self._update_window_title()

```

- [ ] **Step 3: Green apart from the catalog.**

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(interrupted_rename_is_recovered_under_the_old_name|leftover_of_a_completed_rename_is_not_recovered|leftover_save_next_to_its_package_is_not_recovered|invalid_and_empty_temporary_files_are_ignored|name_held_by_an_unlisted_package_is_not_recovered|names_that_are_not_valid_document_names_are_ignored|member_names_must_match_the_temporary_file_name|files_that_are_not_package_leftovers_are_ignored|recovery_never_deletes_or_replaces_a_file|documents_are_recovered_oldest_first|recovery_does_not_replace_a_file_created_meanwhile|load_documents_recovers_and_reports_names_once|load_documents_without_leftovers_recovers_nothing|delete_all_failure_reload_does_not_recover|startup_reports_recovered_documents) " | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (the fifteen D tests pass; only the catalog test still fails):

```text
test_documents_are_recovered_oldest_first ok
test_files_that_are_not_package_leftovers_are_ignored ok
test_interrupted_rename_is_recovered_under_the_old_name ok
test_invalid_and_empty_temporary_files_are_ignored ok
test_leftover_of_a_completed_rename_is_not_recovered ok
test_leftover_save_next_to_its_package_is_not_recovered ok
test_member_names_must_match_the_temporary_file_name ok
test_name_held_by_an_unlisted_package_is_not_recovered ok
test_names_that_are_not_valid_document_names_are_ignored ok
test_recovery_does_not_replace_a_file_created_meanwhile ok
test_recovery_never_deletes_or_replaces_a_file ok
test_delete_all_failure_reload_does_not_recover ok
test_load_documents_recovers_and_reports_names_once ok
test_load_documents_without_leftovers_recovers_nothing ok
test_startup_reports_recovered_documents ok
FAIL: test_recovery_strings_are_translated (tests.test_i18n.TranslationTest.test_recovery_strings_are_translated)
AssertionError: {'Doc[15 chars]d': 'Documents Recovered', 'DotExpress was int[291 chars]ct.'} != {'Doc[15 chars]d': '已復原文件', 'DotExpress was interrupted while[1
Ran 346 tests
FAILED (failures=1, skipped=2)
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

Expected (no `xgettext` warning on stderr; `msgmerge` guessed one wrong fuzzy translation, `Documents Recovered` as `文件` from `Documents`, and left the long message empty; both are printed):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
364 translated messages, 1 fuzzy translation, 1 untranslated message.
#: gui.py:754
#, fuzzy
msgid "Documents Recovered"
msgstr "文件"
#: gui.py:751
#, python-brace-format
msgid ""
"DotExpress was interrupted while saving or renaming a document. These "
"documents were recovered:\n"
"\n"
"{names}\n"
"\n"
"Check that their content is what you expect."
msgstr ""
```

- [ ] **Step 5: Fill both msgstr values and drop the fuzzy flag** (block script, as every other block), check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
"\n"
"Check that their content is what you expect."
msgstr ""

#: gui.py:754
#, fuzzy
msgid "Documents Recovered"
msgstr "文件"

#: gui.py:812
msgid "Add Document"
```

```po
"\n"
"Check that their content is what you expect."
msgstr ""
"DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n"
"\n"
"{names}\n"
"\n"
"請確認內容是否正確。"

#: gui.py:754
msgid "Documents Recovered"
msgstr "已復原文件"

#: gui.py:812
msgid "Add Document"
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
msggrep --msgid -e 'Documents Recovered' -e 'DotExpress was interrupted' locales/zh_TW/LC_MESSAGES/dotexpress.po 2>/dev/null | sed -n '/^#: /,$p'
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (366 translated, no fuzzy; 367 `msgid` lines with the header; the 31 obsolete entries unchanged; no absolute, backslash, test or venv reference; the long entry is `python-brace-format`; `msggrep` writes a code-page warning to stderr, which is dropped; the two Task 2 msgids are still missing):

```text
a second msgmerge changes nothing
msgfmt exit 0
366 translated messages.
0
#: gui.py:751
#, python-brace-format
msgid ""
"DotExpress was interrupted while saving or renaming a document. These "
"documents were recovered:\n"
"\n"
"{names}\n"
"\n"
"Check that their content is what you expect."
msgstr ""
"DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n"
"\n"
"{names}\n"
"\n"
"請確認內容是否正確。"

#: gui.py:754
msgid "Documents Recovered"
msgstr "已復原文件"
catalog keys: 367
'Documents Recovered' -> 已復原文件
'DotExpress was interrupted while saving ' -> DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\n{names}\n\n請確認內容是否正確。
'Characters Replaced' -> (missing)
'Some characters in document "{name}" can' -> (missing)
28418
locales/dotexpress.pot:367
locales/zh_TW/LC_MESSAGES/dotexpress.po:367
31
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 366 sha256 48f907533e4ef38297b316ba8d4235f7f180533d80ea9d6e407abfae084c74e2
```

- [ ] **Step 6: Green: the four modules and the full suite.**

```bash
$PY -m unittest tests.test_i18n -v 2>&1 | grep -E "^test_recovery_strings_are_translated " | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_recovery_strings_are_translated ok
Ran 346 tests
OK (skipped=2)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1419 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/documents/workspace.py client/documents/workspace_service.py client/gui.py client/tests/test_document_workspace.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py client/tests/test_i18n.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: recover documents whose save or rename was interrupted (F-8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected (the `.pot` and `.po` also change in the `#:` reference lines that F-8a's line moves left stale):

```text
 client/documents/workspace.py                  |  58 +++++-
 client/documents/workspace_service.py          |  12 ++
 client/gui.py                                  |  10 +
 client/locales/dotexpress.pot                  | 252 ++++++++++++------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 28058 -> 28418 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 257 +++++++++++++------------
 client/tests/test_document_workspace.py        | 211 ++++++++++++++++++++
 client/tests/test_gui_document_flows.py        |  42 ++++
 client/tests/test_i18n.py                      |  18 ++
 client/tests/test_workspace_service.py         |  60 ++++++
 10 files changed, 683 insertions(+), 237 deletions(-)
b61ee7abb5e394733453ce6ea286561ef0e19377
```

### Task 2: Replace U+0000 when documents are loaded or imported, and say so (D12-D14)

- [ ] **Step 1: Red: Test Plan E and the U+0000 half of F; the `Mock` harness.** `test_document_workspace.py` gets `ReplaceNulCharactersTest` (E1, E2); `test_workspace_service.py` gets `ReplacedNulCharactersTest` (E3-E9); `test_gui_document_flows.py` gets E10-E13 and `test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened`, and `take_replaced_character_count.return_value = 0` in the `Mock` harness; `test_i18n.py` gets `test_replaced_character_strings_are_translated`. U+0000 and U+FFFD appear only as `\x00` and `\ufffd` escapes (the check after the blocks counts them in the added lines).

Edit: `client/tests/test_document_workspace.py`

```python
        self.assertIsNone(logs.records[0].exc_info)


if __name__ == "__main__":
    unittest.main()
```

```python
        self.assertIsNone(logs.records[0].exc_info)


class ReplaceNulCharactersTest(unittest.TestCase):
    """U+0000 becomes U+FFFD where documents enter the app (F-8 D12)."""

    def test_replace_nul_characters(self) -> None:
        clean = "clean text\r\n"
        self.assertIs(workspace.replace_nul_characters(clean)[0], clean)
        cases = {
            "clean": (clean, (clean, 0)),
            "empty": ("", ("", 0)),
            "inside": ("a\x00b", ("a\ufffdb", 1)),
            "leading and trailing": ("\x00ab\x00", ("\ufffdab\ufffd", 2)),
            "consecutive": ("a\x00\x00\x00b", ("a\ufffd\ufffd\ufffdb", 3)),
            "next to CRLF": ("line\r\n\x00\r\nend", ("line\r\n\ufffd\r\nend", 1)),
        }
        for label, (text, expected) in cases.items():
            with self.subTest(label):
                self.assertEqual(workspace.replace_nul_characters(text), expected)

    def test_displayable_counts_text_and_braille_and_keeps_pending_braille(self) -> None:
        cases = (
            ("text and braille", Document("alpha", "a\x00b", "⠁\x00"), Document("alpha", "a\ufffdb", "⠁\ufffd"), 2),
            ("braille only", Document("alpha", "ab", "\x00⠁\x00"), Document("alpha", "ab", "\ufffd⠁\ufffd"), 2),
            ("pending braille", Document("alpha", "\x00", None), Document("alpha", "\ufffd", None), 1),
        )
        for label, document, expected, count in cases:
            with self.subTest(label):
                self.assertEqual(workspace._displayable(document), (expected, count))
        clean = Document("alpha", "ab", "⠁")
        displayable, count = workspace._displayable(clean)
        self.assertIs(displayable, clean)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
```

Edit: `client/tests/test_workspace_service.py`

```python
            self.assertEqual(self._disk(), before)


if __name__ == "__main__":
    unittest.main()
```

```python
            self.assertEqual(self._disk(), before)


class ReplacedNulCharactersTest(unittest.TestCase):
    """U+0000 in a package or an import reaches the controller as U+FFFD, counted once (F-8 D12)."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.workspace = self.root / "workspace"
        self.controller = DocumentController()
        self.service = DocumentWorkspaceService(self.controller, self.workspace)

    def _path(self, name: str) -> Path:
        return self.workspace / f"{name}.dep"

    def _write(self, *documents: Document) -> None:
        for document in documents:
            save_document_package(self._path(document.name), document)

    def _save(self, text: str, braille: str) -> int:
        """Save the open document from these editor values; return how many packages were written."""
        with patch.object(workspace_service, "save_document_package", wraps=workspace_service.save_document_package) as save:
            self.service.save_open_document(text=text, braille=braille)
        return save.call_count

    def _counts(self, *names: str) -> list[int]:
        return [self.service.take_replaced_character_count(name) for name in names]

    def test_load_replaces_nul_for_the_controller_and_keeps_the_package(self) -> None:
        self._write(Document("alpha", "a\x00b", "⠁\x00"))
        before = self._path("alpha").read_bytes()

        self.assertEqual(self.service.load_documents(), [])

        self.assertEqual(self.controller.documents, [Document("alpha", "a\ufffdb", "⠁\ufffd")])
        self.assertEqual(self._path("alpha").read_bytes(), before)
        self.assertEqual(self._counts("alpha", "alpha"), [2, 0])

    def test_first_save_after_load_writes_the_replaced_text(self) -> None:
        # The record keeps the package as read (with U+0000), so the editors' text differs
        # from it and the first save writes; from then on the package holds U+FFFD.
        self._write(Document("alpha", "a\x00b", "⠁\x00"))
        self.service.load_documents()
        self.controller.open_document("alpha")

        self.assertEqual(self._save("a\ufffdb", "⠁\ufffd"), 1)
        self.assertEqual(self._save("a\ufffdb", "⠁\ufffd"), 0)

        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a\ufffdb", "⠁\ufffd"))
        self.service.load_documents()
        self.assertEqual(self._counts("alpha"), [0])

    def test_unopened_document_keeps_its_package_and_count(self) -> None:
        self._write(Document("alpha", "a\x00b", "⠁"), Document("beta", "b", "⠃"))
        self.service.load_documents()
        before = self._path("alpha").read_bytes()
        self.controller.open_document("beta")

        self.assertEqual(self._save("b edited", "⠃"), 1)

        self.assertEqual(self._path("alpha").read_bytes(), before)
        self.assertEqual(self._counts("alpha", "beta"), [1, 0])
        # Replaced again at the next load; nothing is written without the user.
        self.service.load_documents()
        self.assertEqual(self._counts("alpha"), [1])
        self.assertEqual(self._path("alpha").read_bytes(), before)

    def test_import_saves_the_replaced_text_and_counts_it(self) -> None:
        sources = self.root / "sources"
        sources.mkdir()
        (sources / "gamma.txt").write_bytes(b"A\x00B\nline2\x00\x00end\n")
        save_document_package(sources / "delta.dep", Document("delta", "d\x00", "\x00⠙"))
        (sources / "zeta.txt").write_bytes(b"clean")
        self.service.load_documents()

        result = self.service.import_files(sorted(sources.iterdir()), format_key="all")

        expected = [
            Document("delta", "d\ufffd", "\ufffd⠙"),
            Document("gamma", "A\ufffdB\nline2\ufffd\ufffdend\n", None),
            Document("zeta", "clean", None),
        ]
        self.assertEqual(result, ImportResult(saved=expected, issues=[]))
        self.assertEqual(self.controller.documents, expected)
        self.assertEqual([load_document_package(self._path(document.name)) for document in expected], expected)
        self.assertEqual(self._counts("delta", "gamma", "zeta"), [2, 3, 0])
        # The record holds what was written: the unchanged text is not written again.
        self.controller.open_document("gamma")
        self.assertEqual(self._save("A\ufffdB\nline2\ufffd\ufffdend\n", ""), 0)

    def test_pending_count_follows_rename_and_is_dropped_by_delete(self) -> None:
        self._write(Document("alpha", "a\x00", "1"), Document("beta", "b\x00\x00", "2"), Document("zoo", "z\x00", "3"))
        self.service.load_documents()

        self.service.rename_document("alpha", "gamma")
        self.service.delete_document("beta")

        self.assertEqual(self._counts("alpha", "beta", "gamma"), [0, 0, 1])
        self.assertTrue(self.service.delete_all_documents(on_error=lambda _error: None).completed)
        self.assertEqual(self._counts("zoo"), [0])

    def test_delete_all_failure_reload_keeps_only_pending_counts(self) -> None:
        self._write(Document("alpha", "a\x00", "1"), Document("beta", "b\x00\x00", "2"), Document("zoo", "z\x00", "3"))
        self.service.load_documents()
        self.assertEqual(self._counts("alpha"), [1])
        real_unlink = Path.unlink

        def unlink(path, *args, **kwargs):
            if path.name == "alpha.dep":
                raise PermissionError(errno.EACCES, "injected", str(path))
            return real_unlink(path, *args, **kwargs)

        errors: list[OSError] = []
        with patch("pathlib.Path.unlink", autospec=True, side_effect=unlink):
            result = self.service.delete_all_documents(on_error=errors.append)

        self.assertFalse(result.completed)
        self.assertEqual(len(errors), 1)
        self.assertEqual(
            self.controller.documents,
            [
                Document("alpha", "a\ufffd", "1"),
                Document("beta", "b\ufffd\ufffd", "2"),
                Document("zoo", "z\ufffd", "3"),
            ],
        )
        self.assertEqual(self._counts("alpha", "beta", "zoo"), [0, 2, 1])

    def test_text_without_nul_is_unchanged(self) -> None:
        self._write(Document("alpha", "a", "1"), Document("beta", "b", None))
        loaded: list[Document] = []
        real_load = workspace_service.load_workspace_documents

        def load(directory):
            result = real_load(directory)
            loaded.extend(result[0])
            return result

        with patch.object(workspace_service, "load_workspace_documents", side_effect=load):
            self.service.load_documents()

        self.assertEqual(len(loaded), 2)
        self.assertTrue(all(shown is read for shown, read in zip(self.controller.documents, loaded)))
        self.assertEqual(self._counts("alpha", "beta"), [0, 0])
        self.controller.open_document("alpha")
        self.assertEqual(self._save("a", "1"), 0)


if __name__ == "__main__":
    unittest.main()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame._workspace_service.free_document_name.side_effect = lambda base: base
        # F-8 (D4): a bare Mock would be a truthy list of recovered names.
        frame._workspace_service.take_recovered_document_names.return_value = []
        frame.input_txt = Mock()
        frame.output_txt = Mock()
        frame._show_file_error = Mock()
```

```python
        frame._workspace_service.free_document_name.side_effect = lambda base: base
        # F-8 (D4): a bare Mock would be a truthy list of recovered names.
        frame._workspace_service.take_recovered_document_names.return_value = []
        # F-8 (D13): a bare Mock would be a truthy count of replaced characters.
        frame._workspace_service.take_replaced_character_count.return_value = 0
        frame.input_txt = Mock()
        frame.output_txt = Mock()
        frame._show_file_error = Mock()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        )
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    # --- selection ---------------------------------------------------------

    def test_selection_change_maps_index_to_name(self) -> None:
```

```python
        )
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    # --- U+0000 (F-8 D12, D13) ---------------------------------------------

    NUL_NOTICE = (
        'Some characters in document "{name}" cannot be shown ({count} in all). Each one has been '
        "replaced with the replacement character {mark}, so the text after it is kept.\n\n"
        "Delete or change these {mark} characters before converting. Otherwise each one "
        "appears in the braille as an escape code."
    )

    def _nul_notice(self, name: str, count: int, frame) -> tuple:
        message = gui._(self.NUL_NOTICE).format(name=name, count=count, mark="\ufffd")
        return ("MessageBox", message, gui._("Characters Replaced"), gui.wx.OK | gui.wx.ICON_WARNING, frame)

    def test_opening_a_document_with_nul_shows_the_notice_once(self) -> None:
        self._write_packages(Document("alpha", "a\x00b tail", "1\x00"), Document("beta", "b", "2"))
        frame = self._make_workspace_frame()
        frame._workspace_service.load_documents()
        editors_at_the_notice = []

        def message_box(message, caption, style, parent=None):
            editors_at_the_notice.append((frame.input_txt.value, frame.output_txt.value))
            return self._message_box(message, caption, style, parent)

        with patch.object(gui, "message_box", message_box):
            for name in ("alpha", "beta", "alpha"):
                frame._open_document_by_name(name)

        self.assertEqual(
            self.events,
            [
                ("title", "alpha - DotExpress"),
                self._nul_notice("alpha", 2, frame),
                ("title", "beta - DotExpress"),
                ("title", "alpha - DotExpress"),
            ],
        )
        self.assertEqual(editors_at_the_notice, [("a\ufffdb tail", "1\ufffd")])

    def test_editors_receive_the_full_text(self) -> None:
        self._write_packages(Document("alpha", "first\nsecond\x00 after\nthird", "1\x002"))
        frame = self._make_workspace_frame()
        frame._workspace_service.load_documents()

        frame._open_document_by_name("alpha")

        self.assertEqual(
            (frame.input_txt.value, frame.output_txt.value),
            ("first\nsecond\ufffd after\nthird", "1\ufffd2"),
        )

    def test_startup_opens_the_first_document_and_shows_its_notice(self) -> None:
        self._write_packages(Document("alpha", "\x00", ""), Document("beta", "b\x00", "2"))
        frame = self._make_workspace_frame()

        frame._load_workspace_documents_at_startup()

        self.assertEqual(
            self.events,
            [
                ("title", "alpha - DotExpress"),
                self._nul_notice("alpha", 1, frame),
                ("title", "alpha - DotExpress"),
            ],
        )
        self.assertEqual(frame._workspace_service.take_replaced_character_count("beta"), 1)

    def test_single_import_with_nul_shows_the_notice_before_the_issues(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        source_dir = self.root / "sources"
        source_dir.mkdir()
        (source_dir / "beta.txt").write_bytes(b"b\x00\x00\x00 tail")
        (source_dir / "Alpha.txt").write_bytes(b"dup")
        self.import_paths = [str(source_dir / "Alpha.txt"), str(source_dir / "beta.txt")]

        frame.on_import_document(None)

        self.assertEqual(
            self.events,
            [
                ("FileDialog", gui._("Import Document"), gui.wx.FD_OPEN | gui.wx.FD_MULTIPLE),
                ("title", "beta - DotExpress"),
                self._nul_notice("beta", 3, frame),
                (
                    "FileIssuesDialog",
                    gui._("Import Issues"),
                    gui._("Some files were skipped during import."),
                    ['Alpha.txt: Document "Alpha" already exists.'],
                ),
            ],
        )
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("b\ufffd\ufffd\ufffd tail", ""))

    def test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        source_dir = self.root / "sources"
        source_dir.mkdir()
        (source_dir / "beta.txt").write_bytes(b"b\x00")
        (source_dir / "gamma.txt").write_bytes(b"g\x00\x00")
        self.import_paths = [str(source_dir / "beta.txt"), str(source_dir / "gamma.txt")]

        frame.on_import_document(None)
        for name in ("gamma", "beta", "gamma"):
            frame._open_document_by_name(name)

        self.assertEqual(
            self.events,
            [
                ("FileDialog", gui._("Import Document"), gui.wx.FD_OPEN | gui.wx.FD_MULTIPLE),
                ("title", "gamma - DotExpress"),
                self._nul_notice("gamma", 2, frame),
                ("title", "beta - DotExpress"),
                self._nul_notice("beta", 1, frame),
                ("title", "gamma - DotExpress"),
            ],
        )

    # --- selection ---------------------------------------------------------

    def test_selection_change_maps_index_to_name(self) -> None:
```

Edit: `client/tests/test_i18n.py`

```python
        self.assertEqual(
            translation.gettext(message).format(names="alpha\nbeta"),
            "DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\nalpha\nbeta\n\n請確認內容是否正確。",
        )

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
```

```python
        self.assertEqual(
            translation.gettext(message).format(names="alpha\nbeta"),
            "DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\nalpha\nbeta\n\n請確認內容是否正確。",
        )

    def test_replaced_character_strings_are_translated(self) -> None:
        # F-8 (D13): the box shown when a document whose U+0000 was replaced is first opened.
        message = (
            'Some characters in document "{name}" cannot be shown ({count} in all). Each one has been '
            "replaced with the replacement character {mark}, so the text after it is kept.\n\n"
            "Delete or change these {mark} characters before converting. Otherwise each one "
            "appears in the braille as an escape code."
        )
        expected = {
            "Characters Replaced": "已取代字元",
            message: "文件「{name}」中有 {count} 個無法顯示的字元，已全部以替代字元 {mark} 標示，後面的文字都保留下來了。"
            "\n\n轉譯前請刪除或修改這些 {mark}，否則每一個都會在點字中變成一段跳脫碼。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)
        self.assertEqual(
            translation.gettext(message).format(name="alpha", count=3, mark="\ufffd"),
            "文件「alpha」中有 3 個無法顯示的字元，已全部以替代字元 \ufffd 標示，後面的文字都保留下來了。"
            "\n\n轉譯前請刪除或修改這些 \ufffd，否則每一個都會在點字中變成一段跳脫碼。",
        )

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
```

```bash
git -C $REPO diff -U0 -- client/tests | grep '^+[^+]' | $PY -c "import sys; text = sys.stdin.buffer.read().decode('utf-8'); print('added lines:', text.count(chr(10)), '| U+0000:', text.count(chr(0)), '| U+FFFD:', text.count(chr(0xFFFD)), '| escapes x00:', text.count(chr(92) + 'x00'), '| escapes ufffd:', text.count(chr(92) + 'ufffd'))"
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (no U+0000 or U+FFFD character was written, only escapes; E1, E2 and five service tests fail with `AttributeError`; E3 and E6 because the controller and the saved packages still hold U+0000; the GUI tests because the editors get U+0000 and no box opens; F because the catalog does not know the two msgids):

```text
added lines: 269 | U+0000: 0 | U+FFFD: 0 | escapes x00: 42 | escapes ufffd: 43
ERROR: test_displayable_counts_text_and_braille_and_keeps_pending_braille (tests.test_document_workspace.ReplaceNulCharactersTest.test_displayable_counts_text_a
AttributeError: module 'documents.workspace' has no attribute '_displayable'
ERROR: test_replace_nul_characters (tests.test_document_workspace.ReplaceNulCharactersTest.test_replace_nul_characters)
AttributeError: module 'documents.workspace' has no attribute 'replace_nul_characters'
ERROR: test_delete_all_failure_reload_keeps_only_pending_counts (tests.test_workspace_service.ReplacedNulCharactersTest.test_delete_all_failure_reload_keeps_onl
AttributeError: 'DocumentWorkspaceService' object has no attribute 'take_replaced_character_count'
ERROR: test_first_save_after_load_writes_the_replaced_text (tests.test_workspace_service.ReplacedNulCharactersTest.test_first_save_after_load_writes_the_replace
ERROR: test_pending_count_follows_rename_and_is_dropped_by_delete (tests.test_workspace_service.ReplacedNulCharactersTest.test_pending_count_follows_rename_and_
ERROR: test_text_without_nul_is_unchanged (tests.test_workspace_service.ReplacedNulCharactersTest.test_text_without_nul_is_unchanged)
ERROR: test_unopened_document_keeps_its_package_and_count (tests.test_workspace_service.ReplacedNulCharactersTest.test_unopened_document_keeps_its_package_and_c
FAIL: test_import_saves_the_replaced_text_and_counts_it (tests.test_workspace_service.ReplacedNulCharactersTest.test_import_saves_the_replaced_text_and_counts_i
AssertionError: Impor[40 chars]xt='d\x00', braille='\x00⠙'), Document(name='g[114 chars]s=[]) != Impor[40 chars]xt='d�', braille='�⠙'), Document(name='gamma',[9
FAIL: test_load_replaces_nul_for_the_controller_and_keeps_the_package (tests.test_workspace_service.ReplacedNulCharactersTest.test_load_replaces_nul_for_the_con
AssertionError: Lists differ: [Document(name='alpha', text='a\x00b', braille='⠁\x00')] != [Document(name='alpha', text='a�b', braille='⠁�')]
FAIL: test_editors_receive_the_full_text (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_editors_receive_the_full_text)
AssertionError: Tuples differ: ('first\nsecond\x00 after\nthird', '1\x002') != ('first\nsecond� after\nthird', '1�2')
FAIL: test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_impor
AssertionError: Lists differ: [('Fi[59 chars]), ('title', 'beta - DotExpress'), ('title', '[16 chars]ss')] != [('Fi[59 chars]), ('MessageBox', 'Some characters
FAIL: test_opening_a_document_with_nul_shows_the_notice_once (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_opening_a_document_w
AssertionError: Lists differ: [('ti[26 chars]), ('title', 'beta - DotExpress'), ('title', '[16 chars]ss')] != [('ti[26 chars]), ('MessageBox', 'Some characters
FAIL: test_single_import_with_nul_shows_the_notice_before_the_issues (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_single_impor
AssertionError: Lists differ: [('Fi[58 chars]), ('FileIssuesDialog', '匯入問題', '匯入時有部分檔案被略過。'[46 chars].'])] != [('Fi[58 chars]), ('MessageBox', 'Some characters
FAIL: test_startup_opens_the_first_document_and_shows_its_notice (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_startup_opens_th
AssertionError: Lists differ: [('ti[26 chars]), ('title', 'alpha - DotExpress')] != [('ti[26 chars]), ('MessageBox', 'Some characters in document[354 chars]ss')
FAIL: test_replaced_character_strings_are_translated (tests.test_i18n.TranslationTest.test_replaced_character_strings_are_translated)
AssertionError: {'Cha[15 chars]d': 'Characters Replaced', 'Some characters in[563 chars]de.'} != {'Cha[15 chars]d': '已取代字元', 'Some characters in document "{na[3
Ran 361 tests
FAILED (failures=8, errors=10, skipped=2)
```

- [ ] **Step 2: Green: the replacement, the counts and the notice.** Same indentation as Task 1; the blocks write U+0000 and U+FFFD as escapes, and `gui.py` stays ASCII.

Edit: `client/documents/workspace.py`

```python
    if _LONE_SURROGATE.search(text) is None:
        return text
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def _encodable(document: Document) -> Document:
```

```python
    if _LONE_SURROGATE.search(text) is None:
        return text
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def replace_nul_characters(text: str) -> tuple[str, int]:
    """Replace each U+0000 with U+FFFD; return the text and how many were replaced (F-8).

    The Windows Edit control ends its text at U+0000, so a document shown with one
    would be saved without everything after it. Text without U+0000 is returned as is.
    """
    count = text.count("\x00")
    if not count:
        return text, 0
    return text.replace("\x00", "\ufffd"), count


def _displayable(document: Document) -> tuple[Document, int]:
    """``document`` with U+0000 replaced in its text and braille, and how many were replaced (F-8).

    Pending braille stays ``None``; a document without U+0000 is returned as is.
    """
    text, count = replace_nul_characters(document.text)
    braille, braille_count = (None, 0) if document.braille is None else replace_nul_characters(document.braille)
    if not count and not braille_count:
        return document, 0
    return Document(name=document.name, text=text, braille=braille), count + braille_count


def _encodable(document: Document) -> Document:
```

Edit: `client/documents/workspace_service.py`

```python
but not listed, such as an invalid one kept at startup: its name counts as taken.
Startup puts back a package that a crash during Save or Rename left only in a
temporary file, and reports its name once; it never deletes or replaces a file.
"""

from __future__ import annotations
```

```python
but not listed, such as an invalid one kept at startup: its name counts as taken.
Startup puts back a package that a crash during Save or Rename left only in a
temporary file, and reports its name once; it never deletes or replaces a file.
U+0000, which the Windows editors cannot hold, reaches the controller as U+FFFD when
packages are loaded and files imported; the count is kept per document until the
frame takes it to tell the user, and a loaded package is recorded as read, so the
first save of such a document writes the replaced text.
"""

from __future__ import annotations
```

Edit: `client/documents/workspace_service.py`

```python
    DEP_EXTENSION,
    Document,
    PackageFiles,
    _encodable,
    batch_import_documents,
    document_package_path_for_name,
```

```python
    DEP_EXTENSION,
    Document,
    PackageFiles,
    _displayable,
    _encodable,
    batch_import_documents,
    document_package_path_for_name,
```

Edit: `client/documents/workspace_service.py`

```python
    return status.st_size, status.st_mtime_ns


class DocumentWorkspaceService:
    def __init__(
        self,
```

```python
    return status.st_size, status.st_mtime_ns


def _displayable_documents(documents: Iterable[Document]) -> tuple[list[Document], dict[str, int]]:
    """``documents`` with U+0000 replaced (F-8 D12), and the count of each name that had any."""
    shown: list[Document] = []
    counts: dict[str, int] = {}
    for document in documents:
        displayable, count = _displayable(document)
        shown.append(displayable)
        if count:
            counts[document.name] = count
    return shown, counts


class DocumentWorkspaceService:
    def __init__(
        self,
```

Edit: `client/documents/workspace_service.py`

```python
        self._package_files = package_files or PackageFiles()
        self._saved: dict[str, _SavedPackage] = {}
        self._recovered_names: list[str] = []

    @property
    def workspace_dir(self) -> Path:
```

```python
        self._package_files = package_files or PackageFiles()
        self._saved: dict[str, _SavedPackage] = {}
        self._recovered_names: list[str] = []
        # Document name -> how many U+0000 were replaced, until the frame reports it (F-8 D12).
        self._nul_pending: dict[str, int] = {}

    @property
    def workspace_dir(self) -> Path:
```

Edit: `client/documents/workspace_service.py`

```python
        recovered = recover_interrupted_packages(self._workspace_dir, documents)
        self._recovered_names = [document.name for document in recovered]
        documents = sorted([*documents, *recovered], key=lambda document: (document.name.casefold(), document.name))
        self._controller.load_documents(documents)
        self._reset_saved(documents)
        return invalid_paths

```

```python
        recovered = recover_interrupted_packages(self._workspace_dir, documents)
        self._recovered_names = [document.name for document in recovered]
        documents = sorted([*documents, *recovered], key=lambda document: (document.name.casefold(), document.name))
        displayable, self._nul_pending = _displayable_documents(documents)
        self._controller.load_documents(displayable)
        # Recorded as read: the replaced text differs, so the first save writes it.
        self._reset_saved(documents)
        return invalid_paths

```

Edit: `client/documents/workspace_service.py`

```python
        """The documents the last ``load_documents`` put back from temporary files, once (F-8 D4)."""
        names, self._recovered_names = self._recovered_names, []
        return names

    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None:
        for path in paths:
```

```python
        """The documents the last ``load_documents`` put back from temporary files, once (F-8 D4)."""
        names, self._recovered_names = self._recovered_names, []
        return names

    def take_replaced_character_count(self, name: str) -> int:
        """How many U+0000 of ``name`` were replaced and not yet reported; 0 from then on (F-8 D12)."""
        return self._nul_pending.pop(name, 0)

    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None:
        for path in paths:
```

Edit: `client/documents/workspace_service.py`

```python
        saved: list[Document] = []
        save_issues: list[BatchIssue] = []
        for document in documents:
            package_path = self.package_path(document.name)
            try:
                if os.path.lexists(package_path):
```

```python
        saved: list[Document] = []
        save_issues: list[BatchIssue] = []
        for document in documents:
            # The replaced text is what gets saved (F-8 D12).
            document, count = _displayable(document)
            package_path = self.package_path(document.name)
            try:
                if os.path.lexists(package_path):
```

Edit: `client/documents/workspace_service.py`

```python
                continue
            self._remember(document)
            saved.append(document)
        self._controller.add_documents(saved)
        return ImportResult(saved=saved, issues=load_issues + save_issues)

```

```python
                continue
            self._remember(document)
            saved.append(document)
            if count:
                self._nul_pending[document.name] = count
        self._controller.add_documents(saved)
        return ImportResult(saved=saved, issues=load_issues + save_issues)

```

Edit: `client/documents/workspace_service.py`

```python
        )
        self._saved.pop(source_name, None)
        self._remember(renamed)
        return self._controller.rename_document(source_name, new_name)

    def delete_document(self, name: str) -> DeleteDocumentDecision:
```

```python
        )
        self._saved.pop(source_name, None)
        self._remember(renamed)
        if source_name in self._nul_pending:
            self._nul_pending[new_name] = self._nul_pending.pop(source_name)
        return self._controller.rename_document(source_name, new_name)

    def delete_document(self, name: str) -> DeleteDocumentDecision:
```

Edit: `client/documents/workspace_service.py`

```python
        if package_path.exists():
            package_path.unlink()
        self._saved.pop(name, None)
        return self._controller.delete_document(name)

    def delete_all_documents(self, *, on_error: Callable[[OSError], None]) -> DeleteAllResult:
```

```python
        if package_path.exists():
            package_path.unlink()
        self._saved.pop(name, None)
        self._nul_pending.pop(name, None)
        return self._controller.delete_document(name)

    def delete_all_documents(self, *, on_error: Callable[[OSError], None]) -> DeleteAllResult:
```

Edit: `client/documents/workspace_service.py`

```python
            except OSError as exc:
                on_error(exc)
                remaining_documents, invalid_paths = load_workspace_documents(self._workspace_dir)
                self._controller.restore_documents_after_delete_all_failure(remaining_documents)
                self._reset_saved(remaining_documents)
                return DeleteAllResult(completed=False, invalid_paths=invalid_paths)
        self._saved = {}
        self._controller.delete_all_documents()
        return DeleteAllResult(completed=True, invalid_paths=[])
```

```python
            except OSError as exc:
                on_error(exc)
                remaining_documents, invalid_paths = load_workspace_documents(self._workspace_dir)
                displayable, _counts = _displayable_documents(remaining_documents)
                self._controller.restore_documents_after_delete_all_failure(displayable)
                self._reset_saved(remaining_documents)
                # Only documents that were still to be reported are reported later.
                remaining = {document.name for document in remaining_documents}
                self._nul_pending = {name: count for name, count in self._nul_pending.items() if name in remaining}
                return DeleteAllResult(completed=False, invalid_paths=invalid_paths)
        self._saved = {}
        self._nul_pending = {}
        self._controller.delete_all_documents()
        return DeleteAllResult(completed=True, invalid_paths=[])
```

Edit: `client/gui.py`

```python
		self._refresh_document_list(self._document_controller.selected_document_name)
		self._update_window_title()
		self._refresh_dual_view()

	def _open_adjacent_document(self, step: int) -> None:
		target_name = self._document_controller.adjacent_document_name(step)
```

```python
		self._refresh_document_list(self._document_controller.selected_document_name)
		self._update_window_title()
		self._refresh_dual_view()
		# U+0000 replaced when the document was loaded or imported: said once per document (F-8).
		replaced = self._workspace_service.take_replaced_character_count(document.name)
		if replaced:
			self.show_warning(
				_(
					'Some characters in document "{name}" cannot be shown ({count} in all). Each one has been '
					"replaced with the replacement character {mark}, so the text after it is kept.\n\n"
					"Delete or change these {mark} characters before converting. Otherwise each one "
					"appears in the braille as an escape code."
				).format(name=document.name, count=replaced, mark="\ufffd"),
				_("Characters Replaced"),
			)

	def _open_adjacent_document(self, step: int) -> None:
		target_name = self._document_controller.adjacent_document_name(step)
```

- [ ] **Step 3: Green apart from the catalog.**

```bash
git -C $REPO diff -U0 -- client/documents client/gui.py | grep '^+[^+]' | $PY -c "import sys; text = sys.stdin.buffer.read().decode('utf-8'); print('added lines:', text.count(chr(10)), '| U+0000:', text.count(chr(0)), '| U+FFFD:', text.count(chr(0xFFFD)), '| escapes x00:', text.count(chr(92) + 'x00'), '| escapes ufffd:', text.count(chr(92) + 'ufffd'))"
grep -cP '[^\x00-\x7F]' gui.py documents/workspace.py documents/workspace_service.py
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(replace_nul_characters|displayable_counts_text_and_braille_and_keeps_pending_braille|load_replaces_nul_for_the_controller_and_keeps_the_package|first_save_after_load_writes_the_replaced_text|unopened_document_keeps_its_package_and_count|import_saves_the_replaced_text_and_counts_it|pending_count_follows_rename_and_is_dropped_by_delete|delete_all_failure_reload_keeps_only_pending_counts|text_without_nul_is_unchanged|opening_a_document_with_nul_shows_the_notice_once|editors_receive_the_full_text|startup_opens_the_first_document_and_shows_its_notice|single_import_with_nul_shows_the_notice_before_the_issues|import_of_two_files_with_nul_shows_each_notice_when_it_is_opened) " | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (`grep -c` prints 0 for each file: the three production files stay ASCII; the fourteen E tests pass; only the catalog test still fails):

```text
added lines: 66 | U+0000: 0 | U+FFFD: 0 | escapes x00: 2 | escapes ufffd: 2
gui.py:0
documents/workspace.py:0
documents/workspace_service.py:0
test_displayable_counts_text_and_braille_and_keeps_pending_braille ok
test_replace_nul_characters ok
test_delete_all_failure_reload_keeps_only_pending_counts ok
test_first_save_after_load_writes_the_replaced_text ok
test_import_saves_the_replaced_text_and_counts_it ok
test_load_replaces_nul_for_the_controller_and_keeps_the_package ok
test_pending_count_follows_rename_and_is_dropped_by_delete ok
test_text_without_nul_is_unchanged ok
test_unopened_document_keeps_its_package_and_count ok
test_editors_receive_the_full_text ok
test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened ok
test_opening_a_document_with_nul_shows_the_notice_once ok
test_single_import_with_nul_shows_the_notice_before_the_issues ok
test_startup_opens_the_first_document_and_shows_its_notice ok
FAIL: test_replaced_character_strings_are_translated (tests.test_i18n.TranslationTest.test_replaced_character_strings_are_translated)
AssertionError: {'Cha[15 chars]d': 'Characters Replaced', 'Some characters in[563 chars]de.'} != {'Cha[15 chars]d': '已取代字元', 'Some characters in document "{na[3
Ran 361 tests
FAILED (failures=1, skipped=2)
```

- [ ] **Step 4: Regenerate the template, pin its date, merge.**

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
msgattrib --untranslated --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
```

Expected (nothing is fuzzy this time; the two new entries are empty):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
366 translated messages, 2 untranslated messages.
#: gui.py:619
#, python-brace-format
msgid ""
"Some characters in document \"{name}\" cannot be shown ({count} in all). "
"Each one has been replaced with the replacement character {mark}, so the "
"text after it is kept.\n"
"\n"
"Delete or change these {mark} characters before converting. Otherwise each "
"one appears in the braille as an escape code."
msgstr ""

#: gui.py:624
msgid "Characters Replaced"
msgstr ""
```

- [ ] **Step 5: Fill both msgstr values**, check that a second `msgmerge` changes nothing, compile the `.mo`, give the two text files their working-tree CRLF back. The long msgstr is wrapped exactly as `msgmerge` wraps it.

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
"Delete or change these {mark} characters before converting. Otherwise each "
"one appears in the braille as an escape code."
msgstr ""

#: gui.py:624
msgid "Characters Replaced"
msgstr ""

#: gui.py:688
#, python-brace-format
```

```po
"Delete or change these {mark} characters before converting. Otherwise each "
"one appears in the braille as an escape code."
msgstr ""
"文件「{name}」中有 {count} 個無法顯示的字元，已全部以替代字元 {mark} 標示，後"
"面的文字都保留下來了。\n"
"\n"
"轉譯前請刪除或修改這些 {mark}，否則每一個都會在點字中變成一段跳脫碼。"

#: gui.py:624
msgid "Characters Replaced"
msgstr "已取代字元"

#: gui.py:688
#, python-brace-format
```

```bash
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | wc -l
msggrep --msgid -e 'Characters Replaced' -e 'Some characters in document' locales/zh_TW/LC_MESSAGES/dotexpress.po 2>/dev/null | sed -n '/^#: /,$p'
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/mo_check.py locales/zh_TW/LC_MESSAGES/dotexpress.mo
wc -c < locales/zh_TW/LC_MESSAGES/dotexpress.mo
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid' locales/zh_TW/LC_MESSAGES/dotexpress.po
grep '^#:' locales/dotexpress.pot | grep -c -E '\\|[A-Za-z]:|tests/|\.venv/'
grep -c 'POT-Creation-Date: 2026-10-10 12:00+0800' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (368 translated, no fuzzy; 369 `msgid` lines with the header; the four F-8b translations load from the `.mo`):

```text
a second msgmerge changes nothing
msgfmt exit 0
368 translated messages.
0
#: gui.py:619
#, python-brace-format
msgid ""
"Some characters in document \"{name}\" cannot be shown ({count} in all). "
"Each one has been replaced with the replacement character {mark}, so the "
"text after it is kept.\n"
"\n"
"Delete or change these {mark} characters before converting. Otherwise each "
"one appears in the braille as an escape code."
msgstr ""
"文件「{name}」中有 {count} 個無法顯示的字元，已全部以替代字元 {mark} 標示，後"
"面的文字都保留下來了。\n"
"\n"
"轉譯前請刪除或修改這些 {mark}，否則每一個都會在點字中變成一段跳脫碼。"

#: gui.py:624
msgid "Characters Replaced"
msgstr "已取代字元"
catalog keys: 369
'Documents Recovered' -> 已復原文件
'DotExpress was interrupted while saving ' -> DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\n{names}\n\n請確認內容是否正確。
'Characters Replaced' -> 已取代字元
'Some characters in document "{name}" can' -> 文件「{name}」中有 {count} 個無法顯示的字元，已全部以替代字元 {mark} 標示，後面的文字都保留下來了。\n\n轉譯前請刪除或修改這些 {mark}，否則每一個都會在點字中變成一段跳脫碼。
29047
locales/dotexpress.pot:369
locales/zh_TW/LC_MESSAGES/dotexpress.po:369
31
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
source msgids: 368 sha256 c3fe6aa121698c16ef9b3bab6671f995f4648003c59912b1f1b2f82c754da7c5
```

- [ ] **Step 6: Green: the four modules and the full suite.**

```bash
$PY -m unittest tests.test_i18n -v 2>&1 | grep -E "^test_(recovery|replaced_character)_strings_are_translated " | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_recovery_strings_are_translated ok
test_replaced_character_strings_are_translated ok
Ran 361 tests
OK (skipped=2)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1434 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/documents/workspace.py client/documents/workspace_service.py client/gui.py client/tests/test_document_workspace.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py client/tests/test_i18n.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: replace U+0000 when documents are loaded or imported, and say so (F-8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client scripts
```

Expected:

```text
 client/documents/workspace.py                  |  24 ++++
 client/documents/workspace_service.py          |  41 ++++++-
 client/gui.py                                  |  12 ++
 client/locales/dotexpress.pot                  |  61 ++++++----
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 28418 -> 29047 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po |  65 +++++++----
 client/tests/test_document_workspace.py        |  33 ++++++
 client/tests/test_gui_document_flows.py        | 122 ++++++++++++++++++++
 client/tests/test_i18n.py                      |  22 ++++
 client/tests/test_workspace_service.py         | 147 +++++++++++++++++++++++++
 10 files changed, 479 insertions(+), 48 deletions(-)
667b2d2ce22f0a32996f68aa12eaaf23bc980071
```

### Task 3: Verification (no commit)

`BASE` is `main` at `1b19290`.

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = 1403 + 31; the error is F-W6):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1434 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 2: Criterion 2, focused modules; the 31 new tests ran and passed.** The verbose run is kept in `$T/verbose.txt`, so a failure there is named.

```bash
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_document_formats tests.test_export_coordinator tests.test_user_preprocessing_script tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_config tests.test_gui_document_flows tests.test_i18n tests.test_wx_call_sites 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n -v > $T/verbose.txt 2>&1; grep -cE "^test_(interrupted_rename_is_recovered_under_the_old_name|leftover_of_a_completed_rename_is_not_recovered|leftover_save_next_to_its_package_is_not_recovered|invalid_and_empty_temporary_files_are_ignored|name_held_by_an_unlisted_package_is_not_recovered|names_that_are_not_valid_document_names_are_ignored|member_names_must_match_the_temporary_file_name|files_that_are_not_package_leftovers_are_ignored|recovery_never_deletes_or_replaces_a_file|documents_are_recovered_oldest_first|recovery_does_not_replace_a_file_created_meanwhile|load_documents_recovers_and_reports_names_once|load_documents_without_leftovers_recovers_nothing|delete_all_failure_reload_does_not_recover|startup_reports_recovered_documents|recovery_strings_are_translated|replace_nul_characters|displayable_counts_text_and_braille_and_keeps_pending_braille|load_replaces_nul_for_the_controller_and_keeps_the_package|first_save_after_load_writes_the_replaced_text|unopened_document_keeps_its_package_and_count|import_saves_the_replaced_text_and_counts_it|pending_count_follows_rename_and_is_dropped_by_delete|delete_all_failure_reload_keeps_only_pending_counts|text_without_nul_is_unchanged|opening_a_document_with_nul_shows_the_notice_once|editors_receive_the_full_text|startup_opens_the_first_document_and_shows_its_notice|single_import_with_nul_shows_the_notice_before_the_issues|import_of_two_files_with_nul_shows_each_notice_when_it_is_opened|replaced_character_strings_are_translated) .* ok$" $T/verbose.txt; grep -E "^(FAIL|ERROR):" $T/verbose.txt; tail -1 $T/verbose.txt
```

Expected:

```text
Ran 568 tests
OK (skipped=7)
31
OK (skipped=2)
```

- [ ] **Step 3: Shuffled module order, six seeds** (one process each, about two minutes).

```bash
for s in 0 1 2 3 4 5; do $PY $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
      6 ran=1434 failures=0 errors=1 skipped=7 ['test_case_only_rename_still_renames']
```

- [ ] **Step 4: Criterion 3, catalogs.** A fresh template differs from the committed one only in `POT-Creation-Date`; `git diff` against `main` adds exactly the four entries (plus `#:` reference lines); 368 msgids, all translated, 0 fuzzy.

```bash
(cd $REPO && cmd //c "scripts\\generate-pot.bat $(cygpath -w $T/second.pot)"); echo "generate-pot exit $?"
diff --strip-trailing-cr <(grep -v '^"POT-Creation-Date: ' locales/dotexpress.pot) <(grep -v '^"POT-Creation-Date: ' $T/second.pot) && echo "fresh template identical apart from POT-Creation-Date"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
grep -c '^#, fuzzy' locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO diff 1b19290 -- client/locales/zh_TW/LC_MESSAGES/dotexpress.po | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[-+]#: ' 
```

Expected (no entry is fuzzy; the last command lists every changed line of the `.po` that is not a `#:` reference: only the four new entries, sorted by their references in `gui.py`):

```text
generate-pot exit 0
fresh template identical apart from POT-Creation-Date
368 translated messages.
0
source msgids: 368 sha256 c3fe6aa121698c16ef9b3bab6671f995f4648003c59912b1f1b2f82c754da7c5
+#, python-brace-format
+msgid ""
+"Some characters in document \"{name}\" cannot be shown ({count} in all). "
+"Each one has been replaced with the replacement character {mark}, so the "
+"text after it is kept.\n"
+"\n"
+"Delete or change these {mark} characters before converting. Otherwise each "
+"one appears in the braille as an escape code."
+msgstr ""
+"文件「{name}」中有 {count} 個無法顯示的字元，已全部以替代字元 {mark} 標示，後"
+"面的文字都保留下來了。\n"
+"\n"
+"轉譯前請刪除或修改這些 {mark}，否則每一個都會在點字中變成一段跳脫碼。"
+
+msgid "Characters Replaced"
+msgstr "已取代字元"
+
+#, python-brace-format
+msgid ""
+"DotExpress was interrupted while saving or renaming a document. These "
+"documents were recovered:\n"
+"\n"
+"{names}\n"
+"\n"
+"Check that their content is what you expect."
+msgstr ""
+"DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n"
+"\n"
+"{names}\n"
+"\n"
+"請確認內容是否正確。"
+
+msgid "Documents Recovered"
+msgstr "已復原文件"
+
```

- [ ] **Step 5: Criteria 4-6: fixtures, untouched modules, touched files, application data.**

```bash
BASE=1b19290
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/shared client/dialog.py client/config.py client/documents/controller.py client/documents/export_coordinator.py client/documents/formats.py client/ui client/conversion client/dictionaries client/dual_view client/braille client/settings && echo "shared, dialogs, config, controller, export coordinator, formats, ui, conversion, dictionaries, dual view, braille and settings unchanged"
git -C $REPO diff --stat=200 $BASE -- client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) | diff - $T/app-data.sha256 && echo "application data unchanged"
git -C $REPO status --short -- client scripts
```

Expected (the application data are the user's files in the main checkout, read only; in the dry run's scratch clone no `client/log`, `client/workspace`, `client/dictionary` or `client/config.json` appeared, so no test creates them; `status` prints nothing):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
shared, dialogs, config, controller, export coordinator, formats, ui, conversion, dictionaries, dual view, braille and settings unchanged
 client/documents/workspace.py                  |  82 ++++++++++++++++++++++++++++++++++++++++++-
 client/documents/workspace_service.py          |  53 ++++++++++++++++++++++++++--
 client/gui.py                                  |  22 ++++++++++++
 client/locales/dotexpress.pot                  | 267 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--------------------------------------------------------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 28058 -> 29047 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 276 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--------------------------------------------------------------
 client/tests/test_document_workspace.py        | 244 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_gui_document_flows.py        | 164 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_i18n.py                      |  40 +++++++++++++++++++++
 client/tests/test_workspace_service.py         | 207 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 10 files changed, 1116 insertions(+), 239 deletions(-)
application data unchanged
```

- [ ] **Step 6: Criterion 8, mutation check** (24 mutants: the spec's F-8b items as 12 mutants (deleting a skipped candidate, `os.replace` instead of `os.rename`, no content-duplicate rule, newest first, recovering invalid archives, recovering in the Delete All reload; braille not counted, the record built from the replaced text, the notice on every open, no notice, the count not moved on Rename, U+0000 replaced in `_encodable`), and twelve more: no name rule, the recovered documents not sorted into the list, the recovered names reported every time, no recovery box, the recovery box before the invalid-files dialog, the load giving the raw text to the controller, Import saving the raw text, Import not counting, the count kept after Delete and after Delete All, and the Delete All reload giving the raw text or counting again; about a minute and a half). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f8b_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
recovery-deletes-a-skipped-file: 8 caught: test_document_workspace.test_documents_are_recovered_oldest_first, test_document_workspace.test_interrupted_rename_is_recovered_under_the_old_name, test_document_workspace.test_leftover_of_a_completed_rename_is_not_recovered, test_document_workspace.test_leftover_save_next_to_its_package_is_not_recovered, and 4 more
recovery-with-os-replace: 2 caught: test_document_workspace.test_recovery_does_not_replace_a_file_created_meanwhile, test_document_workspace.test_recovery_never_deletes_or_replaces_a_file
no-content-duplicate-rule: 7 caught: test_document_workspace.test_documents_are_recovered_oldest_first, test_document_workspace.test_interrupted_rename_is_recovered_under_the_old_name, test_document_workspace.test_leftover_of_a_completed_rename_is_not_recovered, test_document_workspace.test_recovery_never_deletes_or_replaces_a_file, and 3 more
no-name-rule: 3 caught: test_document_workspace.test_leftover_save_next_to_its_package_is_not_recovered, test_document_workspace.test_name_held_by_an_unlisted_package_is_not_recovered, test_document_workspace.test_recovery_never_deletes_or_replaces_a_file
newest-first: 5 caught: test_document_workspace.test_documents_are_recovered_oldest_first, test_document_workspace.test_interrupted_rename_is_recovered_under_the_old_name, test_document_workspace.test_recovery_never_deletes_or_replaces_a_file, test_gui_document_flows.test_startup_reports_recovered_documents, and 1 more
recovers-invalid-archives: 3 caught: test_document_workspace.test_invalid_and_empty_temporary_files_are_ignored, test_document_workspace.test_member_names_must_match_the_temporary_file_name, test_document_workspace.test_recovery_never_deletes_or_replaces_a_file
recovers-in-the-delete-all-reload: 1 caught: test_workspace_service.test_delete_all_failure_reload_does_not_recover
recovered-documents-not-sorted: 1 caught: test_workspace_service.test_load_documents_recovers_and_reports_names_once
recovered-names-reported-every-time: 1 caught: test_workspace_service.test_load_documents_recovers_and_reports_names_once
no-recovery-box: 1 caught: test_gui_document_flows.test_startup_reports_recovered_documents
recovery-box-before-the-invalid-files-dialog: 1 caught: test_gui_document_flows.test_startup_reports_recovered_documents
braille-not-counted: 4 caught: test_document_workspace.test_displayable_counts_text_and_braille_and_keeps_pending_braille, test_gui_document_flows.test_opening_a_document_with_nul_shows_the_notice_once, test_workspace_service.test_import_saves_the_replaced_text_and_counts_it, test_workspace_service.test_load_replaces_nul_for_the_controller_and_keeps_the_package
load-gives-the-raw-text: 3 caught: test_gui_document_flows.test_editors_receive_the_full_text, test_gui_document_flows.test_opening_a_document_with_nul_shows_the_notice_once, test_workspace_service.test_load_replaces_nul_for_the_controller_and_keeps_the_package
record-built-from-the-replaced-text: 1 caught: test_workspace_service.test_first_save_after_load_writes_the_replaced_text
nul-replaced-in-encodable: 7 caught: test_gui_document_flows.test_opening_a_document_with_nul_shows_the_notice_once, test_gui_document_flows.test_startup_opens_the_first_document_and_shows_its_notice, test_workspace_service.test_delete_all_failure_reload_keeps_only_pending_counts, test_workspace_service.test_import_saves_the_replaced_text_and_counts_it, and 3 more
import-saves-the-raw-text: 2 caught: test_gui_document_flows.test_single_import_with_nul_shows_the_notice_before_the_issues, test_workspace_service.test_import_saves_the_replaced_text_and_counts_it
import-not-counted: 3 caught: test_gui_document_flows.test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened, test_gui_document_flows.test_single_import_with_nul_shows_the_notice_before_the_issues, test_workspace_service.test_import_saves_the_replaced_text_and_counts_it
count-not-moved-on-rename: 1 caught: test_workspace_service.test_pending_count_follows_rename_and_is_dropped_by_delete
count-kept-after-delete: 1 caught: test_workspace_service.test_pending_count_follows_rename_and_is_dropped_by_delete
counts-kept-after-delete-all: 1 caught: test_workspace_service.test_pending_count_follows_rename_and_is_dropped_by_delete
delete-all-reload-gives-the-raw-text: 1 caught: test_workspace_service.test_delete_all_failure_reload_keeps_only_pending_counts
delete-all-reload-counts-again: 1 caught: test_workspace_service.test_delete_all_failure_reload_keeps_only_pending_counts
notice-on-every-open: 4 caught: test_gui_document_flows.test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened, test_gui_document_flows.test_opening_a_document_with_nul_shows_the_notice_once, test_workspace_service.test_delete_all_failure_reload_keeps_only_pending_counts, test_workspace_service.test_load_replaces_nul_for_the_controller_and_keeps_the_package
no-notice: 4 caught: test_gui_document_flows.test_import_of_two_files_with_nul_shows_each_notice_when_it_is_opened, test_gui_document_flows.test_opening_a_document_with_nul_shows_the_notice_once, test_gui_document_flows.test_single_import_with_nul_shows_the_notice_before_the_issues, test_gui_document_flows.test_startup_opens_the_first_document_and_shows_its_notice
exit 0
```

### Task 4: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay. The dry run built the same code (the tree of Task 2) and ran Step 2's scripts against it and against `N-f8a2`; the blocks of Step 4 are those logs (see Dry Run). Run everything from the repository root, one item at a time, with nothing else driving the desktop. Never touch `D:\dxtest\N`, `B`, `N-p25`, `N-f3`, `N-f4*`, `N-f5*`, `N-f6*`, `N-f7`, `N-f8a`, `N-f8a2` (only read and copied by the scripts) or the existing `D:\dxtest\auto*` folders; every run of this task uses a new folder whose name ends in `-f8b`. Only processes whose exe lies under that folder are ended (`dx.kill_under`). The user may have DotExpress open: never end any other process. No script writes to the clipboard: text with U+0000 reaches the app only through package and text files.

- [ ] **Step 1: Build** (PowerShell). The main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`.

```powershell
Set-Location D:\workspace\DotExpress
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f8b-build.log 2>&1"
if (Select-String -Path $env:TEMP\f8b-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "documents\\workspace.py", "documents\\workspace_service.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress\\client\\$m" -Quiet) { "$m bundled from the checkout" } }
if (Select-String -Path client\build\DotExpress\Analysis-00.toc -SimpleMatch "DotExpress\\client\\gui.py" -Quiet) { "gui.py analyzed from the checkout" }
New-Item -ItemType Directory -Force D:\dxtest\N-f8b | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f8b\DotExpress.exe
(Get-Item D:\dxtest\N-f8b\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f8b\DotExpress.exe).Hash
git status --short -- client scripts
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f8b-build.log`), the two `bundled from the checkout` lines (printed with their doubled backslash), `gui.py analyzed from the checkout`, a size near 48.76 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored). The `.mo` is bundled through `--add-data "locales;locales"`; items 70, 73-75 show its zh-TW strings.

- [ ] **Step 2: Write the GUI scripts** into the new history folder with `apply_blocks.py` ("Task 4", "Step 2": 3 blocks). They reuse, unchanged, F-8a's `f8agui.py` and through it F-7's `f7gui.py`, F-5's `f5gui.py` and `dx.py`, `docs.py`, `dicts.py` of `2026-10-09-03-windows-verification/auto/`. Scripts use tabs.

File: `docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/auto/f8bgui.py`

````python
"""Shared helpers for the F-8b GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses f8agui.py of F-8a (and through it f7gui.py, f5gui.py and the helpers of the
2026-10-09-03 Windows verification) unchanged. Startup can show message boxes before
the main window appears (the recovery box, the U+0000 box of the first document) as
well as the invalid-files dialog: ``start`` answers each one and returns what it showed.
Work folders are built by script: packages are written with zipfile, and U+0000 reaches
the app only through files. Nothing here touches the clipboard. Output shows U+FFFD as
<U+FFFD>.
"""
import os
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
F8A = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-10-05-f8a-data-safety-cleanup", "auto"))
sys.path.insert(0, F8A)
import f8agui as A  # noqa: E402  (puts the F-7, F-5 and 2026-10-09-03 auto folders on sys.path)
from f8agui import D, F, G, X, dx  # noqa: E402

IMPORT_DIALOG = "匯入文件"
REPLACEMENT = chr(0xFFFD)


def show(value):
	"""``repr(value)`` with U+FFFD written as <U+FFFD>."""
	return repr(value).replace(REPLACEMENT, "<U+FFFD>")


def leftover(d, file_name, name, text, braille, age_s=0):
	"""workspace\\<file_name> holding a package of ``name`` (as a crash leaves it), ``age_s`` seconds old."""
	path = os.path.join(d, "workspace", file_name)
	with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(f"{name}.txt", text)
		archive.writestr(f"{name}.brl", braille)
	modified = time.time() - age_s
	os.utime(path, (modified, modified))
	return path


def temporary_files(d):
	"""{name: sha256 prefix} of the .tmp files in workspace\\."""
	return {name: A.sha(os.path.join(d, "workspace", name)) for name in A.files(d) if name.endswith(".tmp")}


def members(d, name):
	"""(text, braille) of workspace\\<name>.dep as stored, or None if it is missing."""
	path = os.path.join(d, "workspace", f"{name}.dep")
	if not os.path.exists(path):
		return None
	with zipfile.ZipFile(path) as archive:
		return archive.read(f"{name}.txt").decode("utf-8"), archive.read(f"{name}.brl").decode("utf-8")


def start(d, timeout=40):
	"""Start <d>\\DotExpress.exe and answer what startup shows before the main window.

	The invalid-files dialog is answered with Keep; each message box is read through UIA
	(f5gui.describe) and answered with Enter. Returns (app, w, shown): ``shown`` lists in
	order ("invalid", <its list>) and the description of each box. If the main window
	does not appear, returns (None, None, shown + [how the start ended]).
	"""
	from pywinauto import Application, Desktop

	launcher = subprocess.Popen([os.path.join(d, "DotExpress.exe")], cwd=d)
	started = time.time()
	shown = []
	handled = set()
	while time.time() - started < timeout:
		for handle, title in A.top_windows(d):
			if handle in handled:
				continue
			if title.endswith("DotExpress"):
				app, w = dx.attach(d)
				return app, w, shown
			win = Application(backend="win32").connect(handle=handle).window(handle=handle)
			if title == A.INVALID_FILES:
				shown.append(("invalid", win.child_window(class_name="ListBox").wrapper_object().item_texts()))
				X.btn(win, A.KEEP_INVALID).click()
				handled.add(handle)
				time.sleep(1)
			elif G.is_task_dialog(win):
				box = Desktop(backend="uia").window(handle=handle)
				described = F.describe(box)
				described["presses"] = F.answer(box, "enter")
				shown.append(described)
				handled.add(handle)
		if launcher.poll() is not None and not A.processes(d):
			return None, None, shown + [f"no main window; exited with code {launcher.returncode}"]
		time.sleep(0.5)
	return None, None, shown + [f"no main window after {timeout} s: {A.top_windows(d)}"]


def box(app, timeout=3):
	"""The next message box (answered with Enter), or None if none opens within ``timeout`` s."""
	return G.answer_box(app, "enter", timeout=timeout)


def switch(app, w, back=False):
	"""Ctrl+Tab (Ctrl+Shift+Tab if ``back``): (the box it showed, the title)."""
	from pywinauto.keyboard import send_keys

	w.set_focus()
	send_keys("^+{TAB}" if back else "^{TAB}")
	time.sleep(1)
	return box(app), w.window_text()


def open_document(app, w, name):
	"""Select ``name`` and choose File > Open: the box it showed (or None)."""
	D.select(w, name)
	G.menu(w, "#0->#0", wait=0.5)
	return box(app)


def import_files(app, w, folder, names):
	"""File > Import; open ``folder`` in the file dialog, then choose ``names`` together."""
	G.menu(w, "#0->#5", wait=0.5)
	dialog = X.wait_window(app, w, IMPORT_DIALOG)
	edit = dialog.child_window(class_name="Edit", found_index=0).wrapper_object()
	edit.set_edit_text(folder)
	G.press_keys(dialog, "{ENTER}")
	# Several names are quoted; one name is typed as it is (the dialog does not take a single quoted name).
	edit.set_edit_text(" ".join(f'"{name}"' for name in names) if len(names) > 1 else names[0])
	G.press_keys(dialog, "{ENTER}", wait=1)


def finish(app, w, d):
	print("close:", D.close(app, w))
	dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/auto/item70.py`

````python
"""Items 70-72 (F-8 D3, D4): packages that a crash left in temporary files.

Usage: python item70.py <exe> <work folder> <70|71|72>
70: an interrupted Rename of alpha to gamma: the moved-aside .alpha.dep._vw4x6f_.tmp (an
    hour old) and the staged .gamma.dep.mlw4jang.tmp (now, same content), no .dep. Start:
    what startup shows, the list, the text, the files; close; start again. Then (the F-8b
    plan's addition, spec Risks) change alpha's text, close and start again.
71: gamma.dep and the leftover .alpha.dep.7gdjw2yi.tmp of a completed Rename (same
    content, an hour old). Start: what startup shows; the list; the .tmp files.
72: alpha.dep and the leftover .alpha.dep.97dc8315c5cf865f.tmp of an interrupted Save
    (newer text). Start: what startup shows; alpha's text; the .tmp files.
Before F-8b (N-f8a2): 70 shows nothing and starts with a new default document.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8bgui as B  # noqa: E402
from f8bgui import A, D  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
if item == "70":
	B.leftover(d, ".alpha.dep._vw4x6f_.tmp", "alpha", "alpha body", "⠁⠃", age_s=3600)
	B.leftover(d, ".gamma.dep.mlw4jang.tmp", "gamma", "alpha body", "⠁⠃")
elif item == "71":
	A.package(d, "gamma", "gamma body", "⠛")
	B.leftover(d, ".alpha.dep.7gdjw2yi.tmp", "alpha", "gamma body", "⠛", age_s=3600)
elif item == "72":
	A.package(d, "alpha", "saved text", "⠁")
	B.leftover(d, ".alpha.dep.97dc8315c5cf865f.tmp", "alpha", "newer text", "⠁")
before = B.temporary_files(d)


def state(label, app, w, shown):
	print(f"{item} {label}: shown {B.show(shown)}")
	print(f"{item} {label}: docs {D.docs(w)} title {w.window_text()!r} input {B.show(D.get_input(w))}")
	left = B.temporary_files(d)
	print(f"{item} {label}: files {A.files(d)} .tmp left unchanged: {all(before.get(name) == sha for name, sha in left.items())}")


app, w, shown = B.start(d)
state("start", app, w, shown)
print("close:", D.close(app, w))
app, w, shown = B.start(d)
state("restart", app, w, shown)
if item == "70":
	if D.docs(w) == ["alpha"]:
		D.set_input(w, "alpha edited")
		print("close:", D.close(app, w))
		app, w, shown = B.start(d)
		state("alpha edited, restart", app, w, shown)
	else:
		print("70 alpha is not listed; nothing edited")
B.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/auto/item73.py`

````python
"""Items 73-75 (F-8 D12, D13): U+0000 in a package or in an imported file.

Usage: python item73.py <exe> <work folder> <73|74|75>
73: alpha.dep with the text "first line\nsecond\x00 after\nthird" and the braille
    "⠁\x00⠃", beta.dep without U+0000. Start: what startup shows; the source editor's text
    (WM_GETTEXT); Ctrl+Tab to beta and back (the boxes); alpha.dep; close; alpha.dep; start
    again: what startup shows.
74: File > Import data\\zero.txt (the bytes "A\x00B tail\r\nline 2"): the box; the editor;
    the package.
75: File > Import data\\zero.txt and data\\code0.pdf (an untagged PDF whose text string
    holds code 0): the box (none); then File > Open code0, zero and code0 again: the boxes.
Before F-8b (N-f8a2): no box; the editor ends at the first U+0000, and in 73 the first
switch writes that cut text to alpha.dep.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8bgui as B  # noqa: E402
from f8bgui import A, D  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
NUL_TEXT = b"A\x00B tail\r\nline 2"
d = A.prepare(EXE, d)
data = os.path.join(d, "data")


def pdf_with_code_0(path):
	"""A one-page untagged PDF that shows the string (A\\000B) in Helvetica (F-8 spec probe)."""
	content = b"BT /F1 12 Tf 72 700 Td (A\\000B) Tj ET"
	objects = [
		b"<< /Type /Catalog /Pages 2 0 R >>",
		b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
		b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
		b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
		b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
	]
	out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
	offsets = []
	for index, body in enumerate(objects, start=1):
		offsets.append(len(out))
		out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
	xref = len(out)
	out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
	for offset in offsets:
		out += f"{offset:010d} 00000 n \n".encode()
	out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
	return A.write(path, bytes(out))


if item == "73":
	A.package(d, "alpha", "first line\nsecond\x00 after\nthird", "⠁\x00⠃")
	A.package(d, "beta", "beta body", "⠃")
	app, w, shown = B.start(d)
	print(f"73 start: shown {B.show(shown)}")
	print(f"73 docs {D.docs(w)} title {w.window_text()!r} input {B.show(D.get_input(w))}")
	print(f"73 alpha.dep {B.show(B.members(d, 'alpha'))}")
	print(f"73 Ctrl+Tab: {B.show(B.switch(app, w))}")
	print(f"73 Ctrl+Shift+Tab: {B.show(B.switch(app, w, back=True))}")
	print(f"73 input {B.show(D.get_input(w))}")
	print(f"73 alpha.dep {B.show(B.members(d, 'alpha'))}")
	print("close:", D.close(app, w))
	print(f"73 alpha.dep {B.show(B.members(d, 'alpha'))}")
	app, w, shown = B.start(d)
	print(f"73 restart: shown {B.show(shown)} input {B.show(D.get_input(w))}")
else:
	A.write(os.path.join(data, "zero.txt"), NUL_TEXT)
	names = ["zero.txt"]
	if item == "75":
		pdf_with_code_0(os.path.join(data, "code0.pdf"))
		names.append("code0.pdf")
	app, w, shown = B.start(d)
	print(f"{item} start: shown {B.show(shown)} docs {D.docs(w)}")
	B.import_files(app, w, data, names)
	print(f"{item} import: box {B.show(B.box(app))}")
	print(f"{item} docs {D.docs(w)} title {w.window_text()!r} input {B.show(D.get_input(w))}")
	if item == "75":
		for name in ("code0", "zero", "code0"):
			print(f"75 open {name}: box {B.show(B.open_document(app, w, name))}")
			print(f"75 title {w.window_text()!r} input {B.show(D.get_input(w))}")
	print("close:", D.close(app, w))
	for name in ("zero", "code0")[: len(names)]:
		print(f"{item} {name}.dep {B.show(B.members(d, name))}")
	app, w, shown = B.start(d)
	print(f"{item} restart: shown {B.show(shown)} docs {D.docs(w)}")
B.finish(app, w, d)
````

- [ ] **Step 3: Items 70-75 on both builds** (Git Bash, from the repository root): first `D:\dxtest\N-f8a2\DotExpress.exe` ("Before", folders `auto<N>-f8a2-f8b`), then the new build (folders `auto<N>-f8b`). Each run makes its own work folder (`f8agui.prepare` deletes it first, after ending any process under it) and copies the exe into it. Read each log against Step 4 before the next run.

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/auto
export PYTHONIOENCODING=utf-8
cd $REPO
for build in N-f8a2 N-f8b; do
  tag=$([ $build = N-f8a2 ] && echo -f8a2-f8b || echo -f8b)
  for i in 70 71 72; do "$UIA" $H/item70.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto$i$tag $i > /d/dxtest/auto$i$tag.log 2>&1; done
  for i in 73 74 75; do "$UIA" $H/item73.py /d/dxtest/$build/DotExpress.exe /d/dxtest/auto$i$tag $i > /d/dxtest/auto$i$tag.log 2>&1; done
done
```

- [ ] **Step 4: Expected logs.** Each log must equal its block line by line (`diff --strip-trailing-cr`). A box is `{'title': ..., 'main': ..., 'content': ..., 'buttons': [...], 'focus': ..., 'presses': 1}`, read through UIA: wx shows the first paragraph of a message as the task dialog's main instruction and the rest as its content (Spec Corrections 10). `<U+FFFD>` stands for U+FFFD (the scripts print it so); `\x00` is U+0000 in a `repr`; the editor's text is read with `WM_GETTEXT`, so its line ends are `\r\n`. The `focus` of a box is read from the system's focused element half a second after the box is brought forward; a notification of another program can show up there instead (a tool artifact, not a result: note it and run that item again in a new folder).

**70.** An interrupted Rename of `alpha` to `gamma` (no `.dep`): the `已復原文件` box names `alpha` (main instruction and content, `確定`); `alpha` is listed with its text; `alpha.dep` exists and the staged `.gamma.dep.mlw4jang.tmp` is still there, unchanged; the restart shows no box. The third start (Spec Corrections 12, 13): after alpha's text was changed and saved, the staged copy comes back as `gamma`, with a box naming it. Before: no box, a new default document `new`, both `.tmp` files stay (the document is missing).

After F-8b, `D:\dxtest\auto70-f8b.log`:

```text
70 start: shown [{'title': '已復原文件', 'main': 'DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：', 'content': 'alpha\n\n請確認內容是否正確。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}]
70 start: docs ['alpha'] title 'alpha - DotExpress' input 'alpha body'
70 start: files ['.gamma.dep.mlw4jang.tmp', 'alpha.dep'] .tmp left unchanged: True
close: exited
70 restart: shown []
70 restart: docs ['alpha'] title 'alpha - DotExpress' input 'alpha body'
70 restart: files ['.gamma.dep.mlw4jang.tmp', 'alpha.dep'] .tmp left unchanged: True
close: exited
70 alpha edited, restart: shown [{'title': '已復原文件', 'main': 'DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：', 'content': 'gamma\n\n請確認內容是否正確。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}]
70 alpha edited, restart: docs ['alpha', 'gamma'] title 'alpha - DotExpress' input 'alpha edited'
70 alpha edited, restart: files ['alpha.dep', 'gamma.dep'] .tmp left unchanged: True
close: exited
```

Before (N-f8a2), `D:\dxtest\auto70-f8a2-f8b.log`:

```text
70 start: shown []
70 start: docs ['new'] title 'new - DotExpress' input ''
70 start: files ['.alpha.dep._vw4x6f_.tmp', '.gamma.dep.mlw4jang.tmp', 'new.dep'] .tmp left unchanged: True
close: exited
70 restart: shown []
70 restart: docs ['new'] title 'new - DotExpress' input ''
70 restart: files ['.alpha.dep._vw4x6f_.tmp', '.gamma.dep.mlw4jang.tmp', 'new.dep'] .tmp left unchanged: True
70 alpha is not listed; nothing edited
close: exited
```

**71.** The leftover of a completed Rename (`gamma.dep` and `.alpha.dep.7gdjw2yi.tmp`, same content): no box; `gamma` listed; the `.tmp` unchanged. Before: identical.

After F-8b, `D:\dxtest\auto71-f8b.log`:

```text
71 start: shown []
71 start: docs ['gamma'] title 'gamma - DotExpress' input 'gamma body'
71 start: files ['.alpha.dep.7gdjw2yi.tmp', 'gamma.dep'] .tmp left unchanged: True
close: exited
71 restart: shown []
71 restart: docs ['gamma'] title 'gamma - DotExpress' input 'gamma body'
71 restart: files ['.alpha.dep.7gdjw2yi.tmp', 'gamma.dep'] .tmp left unchanged: True
close: exited
```

Before (N-f8a2), `D:\dxtest\auto71-f8a2-f8b.log`:

```text
71 start: shown []
71 start: docs ['gamma'] title 'gamma - DotExpress' input 'gamma body'
71 start: files ['.alpha.dep.7gdjw2yi.tmp', 'gamma.dep'] .tmp left unchanged: True
close: exited
71 restart: shown []
71 restart: docs ['gamma'] title 'gamma - DotExpress' input 'gamma body'
71 restart: files ['.alpha.dep.7gdjw2yi.tmp', 'gamma.dep'] .tmp left unchanged: True
close: exited
```

**72.** The leftover of an interrupted Save next to its package (newer text): no box; `alpha` shows the package's text; the `.tmp` unchanged. Before: identical.

After F-8b, `D:\dxtest\auto72-f8b.log`:

```text
72 start: shown []
72 start: docs ['alpha'] title 'alpha - DotExpress' input 'saved text'
72 start: files ['.alpha.dep.97dc8315c5cf865f.tmp', 'alpha.dep'] .tmp left unchanged: True
close: exited
72 restart: shown []
72 restart: docs ['alpha'] title 'alpha - DotExpress' input 'saved text'
72 restart: files ['.alpha.dep.97dc8315c5cf865f.tmp', 'alpha.dep'] .tmp left unchanged: True
close: exited
```

Before (N-f8a2), `D:\dxtest\auto72-f8a2-f8b.log`:

```text
72 start: shown []
72 start: docs ['alpha'] title 'alpha - DotExpress' input 'saved text'
72 start: files ['.alpha.dep.97dc8315c5cf865f.tmp', 'alpha.dep'] .tmp left unchanged: True
close: exited
72 restart: shown []
72 restart: docs ['alpha'] title 'alpha - DotExpress' input 'saved text'
72 restart: files ['.alpha.dep.97dc8315c5cf865f.tmp', 'alpha.dep'] .tmp left unchanged: True
close: exited
```

**73.** `alpha.dep` with one U+0000 in the text and one in the braille, `beta.dep` clean: the `已取代字元` box names `alpha` and 2 before the main window appears; the source editor holds the whole text with U+FFFD; Ctrl+Tab to `beta` and back shows no second box; the switch saves `alpha.dep` with U+FFFD and `third`; the restart shows no box. Before: no box; the editor ends at `second`, and the first switch writes `first line\nsecond` and `⠁` to `alpha.dep` (**the data loss**).

After F-8b, `D:\dxtest\auto73-f8b.log`:

```text
73 start: shown [{'title': '已取代字元', 'main': '文件「alpha」中有 2 個無法顯示的字元，已全部以替代字元 <U+FFFD> 標示，後面的文字都保留下來了。', 'content': '轉譯前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}]
73 docs ['alpha', 'beta'] title 'alpha - DotExpress' input 'first line\r\nsecond<U+FFFD> after\r\nthird'
73 alpha.dep ('first line\nsecond\x00 after\nthird', '⠁\x00⠃')
73 Ctrl+Tab: (None, 'beta - DotExpress')
73 Ctrl+Shift+Tab: (None, 'alpha - DotExpress')
73 input 'first line\r\nsecond<U+FFFD> after\r\nthird'
73 alpha.dep ('first line\nsecond<U+FFFD> after\nthird', '⠁<U+FFFD>⠃')
close: exited
73 alpha.dep ('first line\nsecond<U+FFFD> after\nthird', '⠁<U+FFFD>⠃')
73 restart: shown [] input 'first line\r\nsecond<U+FFFD> after\r\nthird'
close: exited
```

Before (N-f8a2), `D:\dxtest\auto73-f8a2-f8b.log`:

```text
73 start: shown []
73 docs ['alpha', 'beta'] title 'alpha - DotExpress' input 'first line\r\nsecond'
73 alpha.dep ('first line\nsecond\x00 after\nthird', '⠁\x00⠃')
73 Ctrl+Tab: (None, 'beta - DotExpress')
73 Ctrl+Shift+Tab: (None, 'alpha - DotExpress')
73 input 'first line\r\nsecond'
73 alpha.dep ('first line\nsecond', '⠁')
close: exited
73 alpha.dep ('first line\nsecond', '⠁')
73 restart: shown [] input 'first line\r\nsecond'
close: exited
```

**74.** Import `zero.txt` (one U+0000) alone: the document opens and the box names it; the editor holds the whole text; `zero.dep` holds U+FFFD. Before: no box; the editor shows `A`; after Close the package holds only `A`.

After F-8b, `D:\dxtest\auto74-f8b.log`:

```text
74 start: shown [] docs ['new']
74 import: box {'title': '已取代字元', 'main': '文件「zero」中有 1 個無法顯示的字元，已全部以替代字元 <U+FFFD> 標示，後面的文字都保留下來了。', 'content': '轉譯前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
74 docs ['new', 'zero'] title 'zero - DotExpress' input 'A<U+FFFD>B tail\r\nline 2'
close: exited
74 zero.dep ('A<U+FFFD>B tail\nline 2', '')
74 restart: shown [] docs ['new', 'zero']
close: exited
```

Before (N-f8a2), `D:\dxtest\auto74-f8a2-f8b.log`:

```text
74 start: shown [] docs ['new']
74 import: box None
74 docs ['new', 'zero'] title 'zero - DotExpress' input 'A'
close: exited
74 zero.dep ('A', '')
74 restart: shown [] docs ['new', 'zero']
close: exited
```

**75.** Import `zero.txt` and `code0.pdf` together: no box at the import; File > Open shows one box for each document the first time, none when `code0` is opened again; both packages hold U+FFFD. Before: no box; each editor shows `A`; after Close both packages hold only `A`.

After F-8b, `D:\dxtest\auto75-f8b.log`:

```text
75 start: shown [] docs ['new']
75 import: box None
75 docs ['code0', 'new', 'zero'] title 'new - DotExpress' input ''
75 open code0: box {'title': '已取代字元', 'main': '文件「code0」中有 1 個無法顯示的字元，已全部以替代字元 <U+FFFD> 標示，後面的文字都保留下來了。', 'content': '轉譯前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
75 title 'code0 - DotExpress' input 'A<U+FFFD>B\r\n'
75 open zero: box {'title': '已取代字元', 'main': '文件「zero」中有 1 個無法顯示的字元，已全部以替代字元 <U+FFFD> 標示，後面的文字都保留下來了。', 'content': '轉譯前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。', 'buttons': ['確定'], 'focus': '確定', 'presses': 1}
75 title 'zero - DotExpress' input 'A<U+FFFD>B tail\r\nline 2'
75 open code0: box None
75 title 'code0 - DotExpress' input 'A<U+FFFD>B\r\n'
close: exited
75 zero.dep ('A<U+FFFD>B tail\nline 2', '')
75 code0.dep ('A<U+FFFD>B\n', '')
75 restart: shown [] docs ['code0', 'new', 'zero']
close: exited
```

Before (N-f8a2), `D:\dxtest\auto75-f8a2-f8b.log`:

```text
75 start: shown [] docs ['new']
75 import: box None
75 docs ['code0', 'new', 'zero'] title 'new - DotExpress' input ''
75 open code0: box None
75 title 'code0 - DotExpress' input 'A'
75 open zero: box None
75 title 'zero - DotExpress' input 'A'
75 open code0: box None
75 title 'code0 - DotExpress' input 'A'
close: exited
75 zero.dep ('A', '')
75 code0.dep ('A', '')
75 restart: shown [] docs ['code0', 'new', 'zero']
close: exited
```

- [ ] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/auto-results.md` in the style of `2026-10-10-05-f8a-data-safety-cleanup/auto-results.md` (zh-TW): the build (PyInstaller version, `Build complete!`, the bundled modules, size, sha256), the method, then one row per item (70-75) with ✔/△/✘, the observed boxes, lists, editor texts and packages after F-8b and the "Before" observations on N-f8a2, and item 70's third start as an observation for the open question (Spec Corrections 13), not as a failure. Any deviation from Step 4 is reported to the orchestrator before the commit, not explained away; a re-run after a GUI timing problem (for example the foreground taken by another program) is recorded with the first attempt's log name. End the file with a short section **「仍需人工（使用者）」** for item 83, worded for the user (do not mark it done):

  > 83（NVDA）：請在 NVDA 執行中，把 `D:\dxtest\N-f8b\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual83-f8b\`，並用下列方式準備工作區後啟動：(1) 項目 73 的工作區（`alpha.dep` 的文字含 U+0000）：記錄 NVDA 對「已取代字元」對話框讀出的內容，特別是替代字元 �（U+FFFD）怎麼念（例如「替代字元」、「問號」或完全不念），以及按「確定」後焦點是否回到原文編輯框；(2) 項目 70 的工作區（只有 `.alpha.dep._vw4x6f_.tmp` 與 `.gamma.dep.mlw4jang.tmp`）：記錄 NVDA 對「已復原文件」對話框讀出的內容。兩個工作區可以用 `auto/item73.py`、`auto/item70.py` 建好後，把 `D:\dxtest\auto73-f8b\workspace`、`D:\dxtest\auto70-f8b\workspace` 的初始內容複製過去，或請我們幫忙準備。如果 NVDA 沒有讀出文件名稱、字元數或替代字元，請告訴我們。

Then add a section **Implementation Notes** at the end of this plan (what was applied, any deviation, the commit hashes and tree ids, the exe), as the F-8a plan has.

```bash
cd $REPO
git add docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/auto-results.md docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/auto/f8bgui.py docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/auto/item70.py docs/superpowers/history/2026-10-10-06-f8b-recovery-and-nul/auto/item73.py docs/superpowers/plans/2026-10-10-f8b-recovery-and-nul.md
git diff --cached --stat
git commit -q -m "docs: record the F-8b packaged-build GUI checks (F-8b)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short -- client docs scripts
git rev-parse HEAD:client
```

Expected: the five files in the `--stat`, no `status` output, and the Task 2 tree id `667b2d2ce22f0a32996f68aa12eaaf23bc980071` (the commit touches no file under `client/`). Do not merge `main` or push; the orchestrator decides.
