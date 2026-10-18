# Script Management (F-18) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ] `) syntax for tracking.

**Goal:** Text Processing becomes Script Management (the user, 2026-10-18): several text-processing scripts in a new `script` folder next to `dictionary`, managed like dictionaries (Add, Delete, Rename, Edit, Import, Export) in a modal dialog that replaces the Translation menu item 「文字處理」 by 「腳本管理...」; the script that conversion runs is chosen in Settings > Translation (「文字處理腳本」, default 「不處理」, saved as `conversion.selected_script`). No Processing (`no-processing.py`) cannot be renamed, deleted or edited, and conversion never runs its file. The signature rule gains optional `str` annotations (D-B). The legacy `dictionary/preprocessing.py` is no longer read (D-A). 33 new msgids, 5 removed: 438.

**Architecture:** Three commits, each red first, in the spec's migration order. Task 1 adds the script contract to `conversion/preprocessing/user_script.py` (`validate_script` with the annotation rule, `read_script_source` with `utf-8-sig`, `save_script`, `execute_script` without a fallback), the package `client/text_scripts/` (`manager.py`, `actions.py`, `read_problems.py`), `ApplicationPaths.script` and `shared/file_targets.py` (the same-file and folder-target checks, moved out of `dictionaries/manager.py`). Task 2 adds `conversion.selected_script` (`config.py`, `settings/translation.py`), the Settings choice, `ConversionRequest.script_path` (`None` is No Processing and skips the stage) and the frame's `ScriptManagementPresenter` (names only), `_set_active_script` and `_get_selected_script_path`. Task 3 adds the presenter's flows, `ScriptNameDialog`, `ScriptManagementDialog` and `ScriptEditorDialog` (`dialog.py`), the menu item and its handler, and removes `TextProcessingDialog` and the single-script API. Task 4 verifies (suite, shuffled order, catalogs, fixtures, folders, 20 mutants); Task 5 builds the exe and runs the GUI items 146-158 (159-160 stay manual).

**Tech Stack:** Python 3.13 standard library (`ast`, `difflib`-free), wxPython 4.2.5, GNU gettext 0.23 (`xgettext`, `msgmerge`, `msgfmt`), Git Bash `unix2dos`. Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-18-f18-script-management-design.md` (commit `f691b25`), with the user's answers to Q1-Q4 recorded in `cb07a37` (2026-10-18: the script is chosen in Settings > Translation and Script Management has no 「使用」 button; no message about the stale `preprocessing.py`; no security warning on Import; deleting the active script makes No Processing active). D-E to D-H and O1-O9 are the orchestrator's recommended defaults; the user may override them before the merge. The refinements of "Spec Corrections and Refinements" below are defaults of the same kind.

## Global Constraints

- Work in the worktree `D:\workspace\DotExpress-f18`, branch `fix/f18-script-management` (HEAD is the plan commit on top of `cb07a37`, which is on top of the spec commit `f691b25`, which is on `main` at `67c2a97`, the F-17 merge). Never switch branches, never push, never merge, never rewrite history. The worktree has no `client\.venv`: `PY` is the main checkout's interpreter, run with the working directory inside the worktree. Do not work in the main checkout `D:\workspace\DotExpress` (the user may run the app from source there).
- Files that may change (under `client/`, nothing else there): production `client/app_paths.py`, `client/.gitignore`, `client/config.py`, `client/conversion/preprocessing/user_script.py`, `client/conversion/output.py`, `client/conversion/text/pipeline.py`, `client/dictionaries/manager.py` (the two helpers move out), `client/shared/file_targets.py` (new), `client/text_scripts/` (new: `__init__.py`, `manager.py` 4 spaces, `actions.py`, `read_problems.py`, `presenter.py` **tabs**), `client/settings/translation.py`, `client/settings/dialogs.py` (4 spaces), `client/ui/dialog_base.py`, `client/ui/translation_menu.py`, `client/dialog.py` and `client/gui.py` (**tabs**); the tests named in each task (`client/tests/wx_stub.py` gets one dialog name); the catalogs `client/locales/dotexpress.pot` and `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` / `.mo`; in Task 5 the history folder `docs/superpowers/history/2026-10-18-02-f18-script-management/` and this plan's Implementation Notes.
- Never touch, in the main checkout `D:\workspace\DotExpress`, `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data), or its untracked `preprocessing/`, `testdata/` and `task.md`. `storage/` is read-only and no test depends on it. In the worktree no test may create `client/dictionary/`, `client/script/`, `client/log/`, `client/workspace/` or `client/config.json` (Task 4 Step 5 checks). Never touch `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (CRLF bytes), tracked `client/braille/` content, `client/braille/liblouis/`, `client/tests/fixtures/`, `scripts/`, `vendor/`, the submodule pointers, or the committed scripts and data of earlier history folders. Never run `py scripts\sync-nvda.py`. Never start `gui.py` from source in any checkout: only packaged copies, each in a new `D:\dxtest\auto*-f18` folder. **Never write to the Windows clipboard**: no test, probe or GUI script of this plan does (no `SetClipboardData`, no Ctrl+C/V/X, no `wx.TheClipboard`; code reaches the editor by keystrokes or UIA `ValuePattern.SetValue`, file names reach file dialogs by keystrokes). `git status --short -- client docs scripts` must stay empty between commits.
- The worktree uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply the blocks **with a script that reads them from this file** (`$T/tools/apply_blocks.py`, Task 0 Step 3), not by hand: a `File:` block is written as is; an `Edit:` block is the line ``Edit: `path` `` followed by two fenced blocks, the exact old text and its replacement; the old text must occur exactly once in the file at that point (compared with CRLF converted to LF; the file keeps its line endings). Never edit with MSYS `sed -i` and never paste code through a shell heredoc (Git Bash heredocs and the Edit/Write tools can turn `\n`, `\t` or `\uXXXX` escapes into characters; this plan's blocks hold several). `apply_blocks.py` reads and writes bytes; the tree id check after each commit catches any other change.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`, `translation_liblouis_golden.json` `8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e` (`git show HEAD:<path> | sha256sum`), unchanged after every commit.
- Catalogs: `POT-Creation-Date` stays `2026-10-10 12:00+0800` (pinned by `$T/tools/pin_pot_date.py` after `generate-pot.bat`), so the `.pot`, `.po` and `.mo`, and with them the tree id, are the same in every run. Each task regenerates the template, merges the `.po`, writes the spec's msgstr values of the strings the task adds (`$T/tools/set_msgstr.py` with `$T/tools/f18_msgstr.tsv`; it also clears the `fuzzy` flag and the `#|` line `msgmerge` adds when it pairs a new string with an old one), merges again (which wraps the new msgstr values), and rebuilds the `.mo`. After every task: 0 fuzzy, 0 untranslated, and a second `msgmerge` changes nothing.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -q -m "<subject>"`, the subject ending in `(F-18)`, **no `Co-Authored-By` line** (HANDOFF 2026-10-18-01 section 5); stage only the files the task names, explicitly; look at `git diff --cached --stat` first; never `git commit -F -`.
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (F-12's: FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`, the random part of a temporary file name as `<rnd>`, object addresses as `<addr>`). Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks. Tests run as `$PY -B -X utf8 -m unittest ...` (no bytecode in the worktree).
- Some tests that write packages fail now and then on this machine and pass on the next run, unrelated to F-18 (HANDOFF section 3: `test_workspace_service.ReplacedNulCharactersTest` with `PermissionError` [WinError 5] from `os.replace`, a virus scanner holding the new file; the lone-surrogate save of `test_document_workspace`; the zip timestamp of `test_rename_to_a_name_whose_package_is_on_disk_asks_again`). If a run shows one of them, run it again; report it, do not change code for it.
- Memory (the machine has 8 GB and once ended jobs for low memory): run one heavy job at a time (a replay, a test suite, the mutants, the build, a GUI item), each only when PowerShell `(Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue` shows at least 600; otherwise wait. If the system ends a job, stop and report; do not restart it unasked.
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo; `PLAN` is this file):
  ```bash
  REPO=/d/workspace/DotExpress-f18
  MAIN=/d/workspace/DotExpress
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f18impl
  PLAN=$REPO/docs/superpowers/plans/2026-10-18-f18-script-management.md
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the main checkout: only its interpreter is used, and its git-ignored runtime is copied into the worktree (Task 0 Step 2). The dry run used scratch clones as `REPO` (with `PLAN` pointing at this file outside the clone). Task 5 uses PowerShell for the build and the UIA venv for the GUI scripts.

## Spec Corrections and Refinements (decided in this plan)

Re-checked against the code of `67c2a97`: every decision D1-D13, the behaviour table, the strings table and the test plan hold, with the refinements below. Line numbers moved (orientation only).

1. **Baseline and counts.** On `cb07a37` (`HEAD:client` `a615c7e9`, the code of `67c2a97`) the suite gives `Ran 1681`, `OK (skipped=6)`; the catalogs hold 410 msgids and 26 obsolete entries. F-18 adds 107 tests (net): `Ran 1725` after Task 1 (44; the contract tests are rewritten, 2 legacy ones stay until Task 3), `1748` after Task 2 (23), `1788` after Task 3 (40, after the Text Processing dialog's tests are removed).
2. **Where the single-script API goes.** Each commit stays green, so the old names leave with their last caller: Task 1 keeps `preprocessing_script_path`, `PREPROCESSING_FILENAME`, `DEFAULT_PREPROCESSING_SCRIPT`, `load_preprocessing_script` (with its missing-file fallback), `save_preprocessing_script` (now `save_script` under its old name) and `execute_preprocessing_script` (sharing `_run_script` with `execute_script`), all on `validate_script`; Task 2 removes `execute_preprocessing_script` (the pipeline's default becomes `execute_script`); Task 3 removes the rest with `TextProcessingDialog`. So between Task 2 and Task 3 the old dialog still edits `dictionary/preprocessing.py`, which conversion no longer reads.
3. **The presenter in two steps.** Settings needs the script names in Task 2, so `ScriptManagementPresenter` (its `refresh`, `script_names`, `script_path`) comes with the frame wiring in Task 2 (`gui.py` builds it in `_initialize_state`, next to the dictionary presenter); the flows and the view protocol come in Task 3.
4. **Shared helpers.** `dictionaries/manager.py`'s `_is_same_file` and its folder-target refusal move to `shared/file_targets.py` (`is_same_file`, `refuse_folder_target`); `dictionaries/manager.py` imports them (spec D2). `is_no_processing_script` and the msgid `No Processing` (`NO_PROCESSING_DISPLAY_NAME`) live in `text_scripts/manager.py`, which needs them for the reserved names, the refusals and the export; `actions.py` imports them (no import cycle). `script_display_name` is in `actions.py` as the spec says.
5. **No Processing's status is always Ready.** Script Management never reads `no-processing.py` for its status (conversion never runs it, D4), so a user who altered the file still sees 「不處理 可使用」.
6. **The first save of an Add that finds a file of that name** fails with `FileExistsError`, shown by the editor as 「儲存腳本失敗：腳本「upper」已存在。」 (the existing save box with string 18; the spec said "fails with string 18"). As `create_dictionary`, the check is "the file exists at the moment of the save", not an exclusive create.
7. **Delete selection.** The list selects the script above the deleted one; for the first user script that is No Processing (spec D8.3, "the neighbour above").
8. **Editor details.** The buttons come from `CreateButtonSizer(OK | CANCEL | APPLY)` with `localize_standard_buttons` (the dictionary editor's way; native order OK, Cancel, Apply) instead of three hand-made buttons. "Changed" compares the control's text with the text it held after the last save or when it opened, read back from the control, so a file with CRLF line ends (which wxMSW hands back as LF) does not count as changed.
9. **Catalogs.** The template has 438 msgids after Task 3 (410 + 33 - 5, as the spec expected): 5 after Task 1 (`No Processing`, the two annotation msgids, the `.py` refusal, `Script "{name}" cannot be read.`), 2 after Task 2 (the Settings label and the new panel description, which `msgmerge` pairs with the old description, so the old one is not kept), 26 after Task 3. `msgmerge` keeps the four removed Text Processing strings as obsolete `#~` entries and turns two older obsolete entries (`PDF files (*.pdf)|*.pdf`, `Failed to import document: {error}`) into the fuzzy bases of new strings: 28 obsolete entries (26 before). The spec said obsolete entries are not kept "as in earlier tasks"; the earlier tasks kept `msgmerge`'s obsolete entries (26 at `67c2a97`), and this plan does the same.
10. **Tests.** The spec's test files are `tests/test_user_preprocessing_script.py` (kept, rewritten), `tests/test_text_scripts_manager.py` (also the actions and the status reading), `tests/test_text_scripts_presenter.py`, `tests/test_script_dialogs.py`. Two existing guards change: `test_i18n.ExtractionMarkerTest.FORMER_MARKER_MSGIDS` loses the four Text Processing strings (44 to 40), and `test_i18n.TranslationTest.test_confirm_box_labels_have_no_access_key` lists the script editor's two labels too. `tests/wx_stub.py` gets `ScriptManagementDialog` in the frame profile's dialog names. The `_initialize_state` tests patch `gui.ScriptManagementPresenter`, so no test creates `script/` under a relative root.
11. **Mutation check: 20 mutants** (Task 4 Step 6): the spec's 14 (9 split into "Cancel saves" and "Add writes before a save"), plus No Processing's status read from disk, the editor comparing with the source instead of the control's text, the dictionary choice dropping the selected script, the script not saved with the other settings, a BOM refused, and the return annotation unchecked.
12. **Windows items** are renumbered 146-158 (the spec's 150-162) and the manual NVDA items 159-160 (the spec's 163-164), after F-14's 145. The new build is `D:\dxtest\N-f18`; the old one is `D:\dxtest\N-f14b`.

## Dry Run

The plan was replayed on scratch clones of the branch at `cb07a37` (`$SP/f18plan/r*`, never the worktree or the main checkout), by a harness in the style of F-12/F-13's: for every step it applies the step's blocks with Task 0 Step 3's `apply_blocks.py`, runs every `bash` block from `client/` with `REPO` set to the clone, `MAIN` to the main checkout and `PLAN` to this file, and compares its stdout with the following `text` block. The code was developed first on a separate clone, red first, in the same three steps; the blocks are generated from the diffs of the final development history (and checked to rebuild each file exactly), whose tree ids equal the replay's (Implementation Notes 2). The results are in the Implementation Notes.

## Review Focus

1. **D4, D10:** No Processing is `script_path=None` and runs nothing; the request is built on the main thread; a missing or invalid selected script gives the existing text-processing box; the legacy `dictionary/preprocessing.py` is never read (Test Plan F; mutants 1, 11, 12; GUI 147, 157).
2. **D5, D6:** the annotation rule (`str` or `"str"`, optional) in Save, Import, status and execution; the BOM (Test Plan A; mutants 2, 3, 19, 20; GUI 150, 151).
3. **D8:** Add writes nothing before a save; Delete of the active script makes No Processing active; Rename follows; Import refuses other suffixes and copies the original bytes; Export of No Processing writes its text (Test Plan B, C; mutants 4-7, 9b, 13, 14; GUI 149-155).
4. **D7, D9:** availability (Edit disabled for No Processing), statuses and the reason row, the editor's discard question only after a change (Test Plan D; mutants 8, 9a, 10, 15, 16; GUI 148, 150, 156).
5. **D3:** the fourth setting is loaded, normalized, shown, saved and reported like the others; the dictionary choice keeps it (Test Plan E; mutants 17, 18; GUI 146, 149, 154).
6. **Catalogs:** 438 msgids, all translated, 0 fuzzy; 28 obsolete entries (Spec Corrections 9).

## File Map

- Task 1: tests `client/tests/test_user_preprocessing_script.py`, `client/tests/test_text_scripts_manager.py` (new), `client/tests/test_app_paths.py`; production `client/app_paths.py`, `client/.gitignore`, `client/conversion/preprocessing/user_script.py`, `client/dictionaries/manager.py`, `client/shared/file_targets.py`, `client/text_scripts/{__init__,manager,actions,read_problems}.py`; the catalogs.
- Task 2: tests `client/tests/test_config.py`, `test_conversion_service.py`, `test_conversion_text_pipeline.py`, `test_gui_document_flows.py`, `test_settings_dialogs.py`, `test_text_scripts_presenter.py` (new), `test_translation_settings.py`; production `client/config.py`, `client/conversion/output.py`, `client/conversion/preprocessing/user_script.py`, `client/conversion/text/pipeline.py`, `client/gui.py`, `client/settings/dialogs.py`, `client/settings/translation.py`, `client/text_scripts/presenter.py`; the catalogs.
- Task 3: tests `client/tests/test_dialog_base.py`, `test_gui_document_flows.py`, `test_i18n.py`, `test_script_dialogs.py` (new), `test_settings_dialogs.py`, `test_text_scripts_presenter.py`, `test_translation_menu.py`, `test_user_preprocessing_script.py`, `wx_stub.py`; production `client/conversion/preprocessing/user_script.py`, `client/dialog.py`, `client/gui.py`, `client/settings/dialogs.py`, `client/text_scripts/presenter.py`, `client/ui/dialog_base.py`, `client/ui/translation_menu.py`; the catalogs.
- Task 5: `docs/superpowers/history/2026-10-18-02-f18-script-management/` (`auto/` scripts, `auto-results.md`), this plan's Implementation Notes.

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | msgids | obsolete | `HEAD:client` |
| --- | --- | --- | --- | --- | --- | --- |
| baseline (`cb07a37` + plan) | - | 1681 | `OK (skipped=6)` | 410 | 26 | `a615c7e9405157ae2c6f397360a35f66859dd716` |
| 1 script folder and contract | 44 | 1725 | `OK (skipped=6)` | 415 | 26 | `39db6b1856c8aa24e53e931f2d101838c08f94de` |
| 2 selection and conversion | 23 | 1748 | `OK (skipped=6)` | 416 | 26 | `ef352d3c9d121f629192431ce10031bd33aec7f1` |
| 3 Script Management | 40 | 1788 | `OK (skipped=6)` | 438 | 28 | `c825cb3bf2746815ebf3a76d995472cd3f0e2ef5` |
| 5 GUI results (docs only) | - | 1788 | `OK (skipped=6)` | 438 | 28 | `c825cb3bf2746815ebf3a76d995472cd3f0e2ef5` |

"Tests added" is the net count. The 6 skips are POSIX-only tests.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 by the block script: `brief.py` (F-12's, also masking a temporary folder written with forward slashes), `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` (F-12's, unchanged), `msgid_diff.py` (F-14's), `set_msgstr.py` (F-14's, reading the msgid and msgstr pairs from a tab-separated file and skipping msgids a later task adds), `f18_msgstr.tsv` (the spec's 33 msgstr values), `f18_mutants.py` (20 mutants of the code after Task 3, run on a copy of `client/`; the repository is never changed) and `apply_blocks.py` (F-13's).

---

### Task 0: Baseline (no commit)

- [x] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short -- client docs scripts
git -C $REPO branch --show-current
git -C $REPO merge-base --is-ancestor cb07a37 HEAD && echo "cb07a37 (the user's answers to the spec questions) is in the branch"
git -C $REPO rev-parse cb07a37~1 cb07a37~2 HEAD:client
git -C $REPO diff --stat cb07a37 -- client
```

Expected (`status` and the diff print nothing; `cb07a37~1` is the spec commit, `cb07a37~2` is `main` at `67c2a97`):

```text
fix/f18-script-management
cb07a37 (the user's answers to the spec questions) is in the branch
f691b2517f1974645d495bccc593085087962a09
67c2a97cfb437fd7c10b51dba1bbb49b17a28dba
a615c7e9405157ae2c6f397360a35f66859dd716
```

- [x] **Step 2: The git-ignored runtime the tests load.** A worktree is made without the generated liblouis DLL and tables, `louis_helper.py`, MathCAT and the submodule's `configure.ac`; the guarded copies below bring them from the main checkout, as F-3's Task 0 did (in a worktree that has them already they do nothing). Never stage these files.

```bash
test -e $REPO/client/braille/liblouis.dll || cp $MAIN/client/braille/liblouis.dll $REPO/client/braille/
test -e $REPO/client/braille/louis_helper.py || cp $MAIN/client/braille/louis_helper.py $REPO/client/braille/
test -e $REPO/client/braille/liblouis/tables || cp -r $MAIN/client/braille/liblouis $REPO/client/braille/
test -e $REPO/client/mathcat/assets || cp -r $MAIN/client/mathcat $REPO/client/
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

- [x] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed).

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
only the end of the name) as <c>. F-18 addition: a temporary folder written with forward
slashes (the repr of a WindowsPath) is <tmp> too.
"""
import re
import sys
from pathlib import Path

CLIENT = str(Path.cwd())
CLIENT_REPR = CLIENT.replace("\\", "\\\\")
TMPDIR = re.compile(r"[A-Za-z]:(?:\\\\|\\|/)(?:[^'\"\s]*?(?:\\\\|\\|/))?tmp[a-z0-9_]{8}")
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

File: `$T/tools/msgid_diff.py`

````python
"""Compare the msgids of two catalogs (throwaway, not committed).

Usage: python -I msgid_diff.py <old.pot|.po> <new.pot|.po>
Reads the active entries (not the header, not obsolete "#~" ones) of both files and prints
the count of each, then every msgid only in the new file ("+") and only in the old one
("-"), as its first 20 and last 60 characters. Output is UTF-8.
"""
import ast
import sys

sys.stdout.reconfigure(encoding="utf-8")


def msgids(path):
    found = set()
    text = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    for block in text.split("\n\n"):
        lines = [line for line in block.split("\n") if line and not line.startswith("#")]
        value, reading = None, False
        for line in lines:
            if line.startswith("msgid "):
                value, reading = ast.literal_eval(line[6:]), True
            elif line.startswith('"') and reading:
                value += ast.literal_eval(line)
            else:
                reading = False
        if value:
            found.add(value)
    return found


old, new = msgids(sys.argv[1]), msgids(sys.argv[2])
print(f"old {len(old)} new {len(new)}")
for sign, values in (("+", new - old), ("-", old - new)):
    for value in sorted(values):
        print(f"{sign} {value[:20]!r} ... {value[-60:]!r}")
````

File: `$T/tools/set_msgstr.py`

````python
"""Set the msgstr of the F-18 strings in a .po file (throwaway, not committed).

Usage: python -I set_msgstr.py <file.po> <pairs.tsv>

pairs.tsv holds one msgid and its msgstr per line, separated by a tab (the spec's table;
F-14's set_msgstr.py took them as arguments). Every msgid that is an active (not obsolete)
entry of the file, exactly once, gets its msgstr on one line, loses "fuzzy" from its "#,"
flags (the line goes when no flag is left) and any "#|" previous-msgid line; a msgid that
is not in the file yet (a later task adds its source string) is skipped. Run msgmerge again
afterwards: it wraps the msgstr as it wraps every entry. Line ends are kept. Prints how
many were set and skipped.
"""
import ast
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def main() -> int:
    path, pairs_path = sys.argv[1:3]
    lines = Path(pairs_path).read_bytes().decode("utf-8").splitlines()
    pairs = dict(line.split(chr(9)) for line in lines)
    raw = Path(path).read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    blocks = raw.replace("\r\n", "\n").split("\n\n")
    set_count = skipped = 0
    for msgid, msgstr in pairs.items():
        found = []
        for index, block in enumerate(blocks):
            lines = block.split("\n")
            if any(line.startswith("#~") for line in lines):
                continue
            field, values = None, {"msgid": "", "msgstr": ""}
            for line in lines:
                if line.startswith("msgid "):
                    field, values["msgid"] = "msgid", ast.literal_eval(line[6:])
                elif line.startswith("msgstr "):
                    field, values["msgstr"] = "msgstr", ast.literal_eval(line[7:])
                elif line.startswith('"') and field:
                    values[field] += ast.literal_eval(line)
            if values["msgid"] == msgid:
                found.append(index)
        if not found:
            skipped += 1
            continue
        if len(found) != 1:
            sys.exit(f"{msgid[:60]!r}: found {len(found)} active entries")
        kept = []
        for line in blocks[found[0]].split("\n"):
            if line.startswith("#|"):
                continue
            if line.startswith("#,"):
                flags = [flag.strip() for flag in line[2:].split(",") if flag.strip() and flag.strip() != "fuzzy"]
                if not flags:
                    continue
                line = "#, " + ", ".join(flags)
            kept.append(line)
        start = next(i for i, line in enumerate(kept) if line.startswith("msgstr "))
        blocks[found[0]] = "\n".join(kept[:start] + ["msgstr " + quote(msgstr)])
        set_count += 1
    text = "\n\n".join(blocks)
    Path(path).write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    print(f"msgstr set: {set_count}, not in the file yet: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
````

File: `$T/tools/f18_msgstr.tsv`

````tsv
Script Management...	腳本管理...
Script Management	腳本管理
Script	腳本
Status	狀態
Ready	可使用
Not Valid	格式不正確
Why this script cannot be used:	無法使用的原因：
No Processing	不處理
Add Script	新增腳本
Rename Script	重新命名腳本
Import Script	匯入腳本
Export Script	匯出腳本
Script Name	腳本名稱
Please enter the script name.	請輸入腳本名稱。
Script name must be 1 to 32 characters.	腳本名稱長度需為 1 到 32 個字元。
Script name is not a valid Windows file name.	腳本名稱不是有效的 Windows 檔名。
Script name "{name}" is reserved.	腳本名稱「{name}」為保留名稱。
Script "{name}" already exists.	腳本「{name}」已存在。
Do you want to delete script "{name}"?	要刪除腳本「{name}」嗎？
Confirm Delete Script	確認刪除腳本
Failed to delete script: {error}	無法刪除腳本：{error}
Failed to save script: {error}	儲存腳本失敗：{error}
Failed to import script: {error}	匯入腳本失敗：{error}
Failed to export script: {error}	匯出腳本失敗：{error}
Python files (*.py)|*.py	Python 檔案 (*.py)|*.py
Only Python files (.py) can be imported.	只能匯入 Python 檔案（.py）。
Script "{name}" cannot be read.	無法讀取腳本「{name}」。
Do you want to discard the changes you made to script "{name}"?	要放棄對腳本「{name}」所做的變更嗎？
Python Code	Python 程式碼
Text Processing Script	文字處理腳本
Translation output mode, width, dictionary, and text processing script options	轉譯輸出模式、寬度、字典與文字處理腳本選項
The parameter of main must be annotated as str, or not annotated.	main 的參數只能標註為 str，或不加標註。
The return value of main must be annotated as str, or not annotated.	main 的傳回值只能標註為 str，或不加標註。
````

File: `$T/tools/f18_mutants.py`

````python
"""Run the F-18 tests against deliberately broken code (throwaway, not committed).

Usage: python f18_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, script/, workspace/,
build/, dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For
each mutant it edits one file of the copy (one exact, unique replacement), runs the F-18
test modules there, prints which tests caught it and restores the file. The repository is
never changed. Matches the code after Task 3. Exit status 1 if a mutant is not caught or
its pattern is not found exactly once. Python runs with -B (no bytecode is written): a
restored file can have the size and modification second of the mutant, and a cached .pyc
would then shadow it.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = "conversion/preprocessing/user_script.py"
MANAGER = "text_scripts/manager.py"
ACTIONS = "text_scripts/actions.py"
PRESENTER = "text_scripts/presenter.py"
DIALOG = "dialog.py"
GUI = "gui.py"
OUTPUT = "conversion/output.py"
SETTINGS = "settings/translation.py"
PARAMETER_CHECK = "    if positional[0].annotation is not None and not _is_str_annotation(positional[0].annotation):\n"
READ = '    return Path(path).read_bytes().decode("utf-8-sig")\n'
MUTANTS = {
    # The spec's 14 (Test Plan, "Mutation check").
    "1-no-processing-runs-its-file": (GUI, "\t\tif is_no_processing_script(name):\n\t\t\treturn None\n", "\t\tif False:\n\t\t\treturn None\n"),
    "2-annotation-check-removed": (
        SCRIPT,
        '    if isinstance(annotation, ast.Name):\n        return annotation.id == "str"\n',
        "    if True:\n        return True\n",
    ),
    "3-annotation-made-mandatory": (
        SCRIPT,
        PARAMETER_CHECK,
        "    if positional[0].annotation is None or not _is_str_annotation(positional[0].annotation):\n",
    ),
    "4-suffix-check-removed": (MANAGER, "    if source.suffix.casefold() != SCRIPT_SUFFIX:\n", "    if False:\n"),
    "5-import-copies-decoded-text": (
        MANAGER,
        "    write_bytes_atomically(destination, lambda stream: stream.write(data))\n",
        '    write_bytes_atomically(destination, lambda stream: stream.write(data.decode("utf-8-sig").encode("utf-8")))\n',
    ),
    "6-delete-picks-the-neighbour": (
        PRESENTER,
        "\t\t\tself._set_active_name(NO_PROCESSING_SCRIPT_NAME)\n",
        "\t\t\tself._set_active_name(previous_names[previous_names.index(name) - 1])\n",
    ),
    "7-rename-keeps-the-old-active-name": (
        PRESENTER,
        "\t\tif self._get_active_name() == name and path.stem != name:\n",
        "\t\tif False:\n",
    ),
    "8-edit-enabled-for-no-processing": (ACTIONS, "\t\tedit=can_modify,\n", "\t\tedit=has_selection,\n"),
    "9a-cancel-saves": (
        DIALOG,
        "\t\t\tself._restore_focus(focused)\n\t\t\treturn\n\t\tevent.Skip()\n\n\tdef _restore_focus(self, window: wx.Window | None) -> None:\n\t\t\"\"\"Put the focus back where it was before the box (F-11 D7).\"\"\"\n",
        "\t\t\tself._restore_focus(focused)\n\t\t\treturn\n\t\tself._apply()\n\t\tevent.Skip()\n\n\tdef _restore_focus(self, window: wx.Window | None) -> None:\n\t\t\"\"\"Put the focus back where it was before the box (F-11 D7).\"\"\"\n",
    ),
    "9b-add-writes-before-a-save": (
        PRESENTER,
        "\t\tcreated = False\n",
        "\t\tcreate_script(self._script_dir, name, NO_PROCESSING_SCRIPT)\n\t\tcreated = True\n",
    ),
    "10-question-without-a-change": (DIALOG, "\t\tif self.has_changes() and not confirm_box(\n", "\t\tif not confirm_box(\n"),
    "11-legacy-script-still-runs": (
        OUTPUT,
        "            script_path=request.script_path,\n",
        '            script_path=request.script_path or (request.dictionary_path.parent / "preprocessing.py" if (request.dictionary_path.parent / "preprocessing.py").exists() else None),\n',
    ),
    "12-missing-script-reads-as-identity": (
        SCRIPT,
        READ,
        '    return Path(path).read_bytes().decode("utf-8-sig") if Path(path).exists() else NO_PROCESSING_SCRIPT\n',
    ),
    "13-reserved-names-case-sensitive": (
        MANAGER,
        "    return normalize_base_name(name, reserved_names=reserved)\n",
        "    return normalize_base_name(name, reserved_names=reserved if name.strip() in reserved else None)\n",
    ),
    "14-no-processing-export-reads-the-file": (
        MANAGER,
        "    refuse_folder_target(destination)\n    if is_no_processing_script(name):\n",
        "    refuse_folder_target(destination)\n    if False:\n",
    ),
    # Plan additions.
    "15-no-processing-status-read-from-disk": (DIALOG, "\t\t\tif not is_no_processing_script(name)\n", "\t\t\tif True\n"),
    "16-editor-compares-the-source": (DIALOG, "\t\tself._saved_text = self.editor.GetValue()\n", "\t\tself._saved_text = source\n"),
    "17-dictionary-choice-drops-the-script": (
        GUI,
        "\t\tself.translation_settings = replace(self.translation_settings, selected_dictionary=selected_name)\n",
        "\t\tself.translation_settings = type(self.translation_settings)(\n"
        "\t\t\tself.translation_settings.output_mode, self.translation_settings.width, selected_name\n"
        "\t\t)\n",
    ),
    "18-script-not-saved": (SETTINGS, "        store.set_selected_script(settings.selected_script),\n", ""),
    "19-bom-refused": (SCRIPT, READ, '    return Path(path).read_bytes().decode("utf-8")\n'),
    "20-return-annotation-unchecked": (
        SCRIPT,
        "    if main.returns is not None and not _is_str_annotation(main.returns):\n",
        "    if False:\n",
    ),
}
MODULES = (
    "tests.test_user_preprocessing_script",
    "tests.test_text_scripts_manager",
    "tests.test_text_scripts_presenter",
    "tests.test_script_dialogs",
    "tests.test_config",
    "tests.test_translation_settings",
    "tests.test_settings_dialogs",
    "tests.test_conversion_text_pipeline",
    "tests.test_conversion_service",
    "tests.test_gui_document_flows",
    "tests.test_translation_menu",
    "tests.test_app_paths",
)
IGNORE = shutil.ignore_patterns(".venv", "log", "dictionary", "script", "workspace", "build", "dist", "config.json", "__pycache__")
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
                [sys.executable, "-B", "-X", "utf8", "-m", "unittest", *MODULES],
                cwd=copy, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
        finally:
            path.write_bytes(original)
        names = sorted({f"{where.split('.')[1]}.{test}" for test, where in FAILED.findall(completed.stderr)})
        shown = names if len(names) <= 3 else names[:3] + [f"and {len(names) - 3} more"]
        print(f"{mutant}: {len(names)} caught: {', '.join(shown) if names else 'NONE'}")
        if not names:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
````

File: `$T/tools/apply_blocks.py`

````python
"""Apply the File: and Edit: blocks of one step of the F-18 plan (throwaway, not committed).

Usage: python apply_blocks.py <plan.md> <repo> <T> "<task>" "<step>"
  for example: python apply_blocks.py plan.md D:/workspace/DotExpress-f18 <T> "Task 1" "Step 1"

The step is the "- [x] **Step N" (or ticked "- [x]") item under the "### Task N" heading. A File: block is
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
        elif re.match(r"- \[[ x]\] \*\*Step", line):
            in_step = in_task and line[6:].startswith(f"**{step}:")
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
wrote $T/tools/msgid_diff.py
wrote $T/tools/set_msgstr.py
wrote $T/tools/f18_msgstr.tsv
wrote $T/tools/f18_mutants.py
wrote $T/tools/apply_blocks.py
9 blocks applied (Task 0, Step 3)
```

From then on apply every step's blocks with `apply_blocks.py`, for example `$PY $T/tools/apply_blocks.py "$PLAN" $REPO $T "Task 1" "Step 1"`; it prints `N blocks applied`.

- [x] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, catalogs, tree, application folders.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_user_preprocessing_script tests.test_config tests.test_translation_settings tests.test_settings_dialogs tests.test_conversion_text_pipeline tests.test_conversion_service tests.test_gui_document_flows tests.test_translation_menu tests.test_app_paths 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/translation_liblouis_golden.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid ' locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "msgfmt rebuilds the committed .mo byte for byte"
git -C $REPO rev-parse HEAD:client
for f in dictionary script workspace log config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application folders checked"
```

Expected (the second `Ran` line is the existing part of the spec's acceptance-criterion-2 set; `msgid` lines count the header too):

```text
Ran 1681 tests
OK (skipped=6)
Ran 451 tests
OK
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e *-
source msgids: 410 sha256 623b707fd5629b5e7341259929b103c5231c61f639365e0ff863b21f54904853
locales/dotexpress.pot:411
locales/zh_TW/LC_MESSAGES/dotexpress.po:411
26
410 translated messages.
msgfmt rebuilds the committed .mo byte for byte
a615c7e9405157ae2c6f397360a35f66859dd716
worktree application folders checked
```

### Task 1: Keep text-processing scripts in a script folder with a stricter signature rule (D1, D2, D4-D6)

- [x] **Step 1: Red: Test Plan A and B.** `test_user_preprocessing_script.py` (4 spaces) is rewritten for `validate_script`, `read_script_source`, `save_script` and `execute_script` (a script folder file `upper.py`; the annotation rule with its two new msgids; the BOM; no fallback for a missing or undecodable file); the two legacy tests (`test_path_uses_dictionary_directory`, `test_missing_file_loads_identity_script_without_creating_file`) stay until Task 3 (Spec Corrections 2). New `test_text_scripts_manager.py`: the folder (No Processing created once, never rewritten, listed first), the names (reserved in any case), create, import (suffix, encoding, rule, source that cannot be opened, original bytes, taken name), rename, delete, export (No Processing writes its text), the actions table, the status and the reasons. `test_app_paths.py`: the `script` folder after `dictionary`, and the script functions' folder parameters.

Edit: `client/tests/test_app_paths.py`

````python
        self.assertEqual(paths.config, root / "config.json")
        self.assertEqual(paths.dictionary, root / "dictionary")
        self.assertEqual(paths.workspace, root / "workspace")
        self.assertEqual(paths.log, root / "log")
````

````python
        self.assertEqual(paths.config, root / "config.json")
        self.assertEqual(paths.dictionary, root / "dictionary")
        self.assertEqual(paths.script, root / "script")
        self.assertEqual(paths.workspace, root / "workspace")
        self.assertEqual(paths.log, root / "log")
````

Edit: `client/tests/test_app_paths.py`

````python
            self.assertEqual(probed, list(paths.writable_directories))
            self.assertTrue(all(path.is_dir() for path in paths.writable_directories))

    def test_prepare_reports_the_exact_unwritable_directory(self) -> None:
````

````python
            self.assertEqual(probed, list(paths.writable_directories))
            self.assertTrue(all(path.is_dir() for path in paths.writable_directories))

    def test_the_script_folder_is_prepared_after_the_dictionary_folder(self) -> None:
        # F-18 (D1): created at startup next to dictionary/, like it.
        root = Path("C:/DotExpress")

        paths = app_paths.build_application_paths(root)

        self.assertEqual(
            paths.writable_directories,
            (root, root / "dictionary", root / "script", root / "workspace", root / "log", root / "dual_view"),
        )

    def test_prepare_reports_the_exact_unwritable_directory(self) -> None:
````

Edit: `client/tests/test_app_paths.py`

````python
        import documents.workspace as workspace
        import dual_view.files as dual_view_files

        cases = (
````

````python
        import documents.workspace as workspace
        import dual_view.files as dual_view_files
        import text_scripts.manager as scripts

        cases = (
````

Edit: `client/tests/test_app_paths.py`

````python
            (manager.delete_dictionary, "dictionary_dir"),
            (name_prompt.rename_dictionary_after_name_prompt, "dictionary_dir"),
            (workspace.ensure_workspace_directory, "workspace_dir"),
            (workspace.document_package_path_for_name, "workspace_dir"),
````

````python
            (manager.delete_dictionary, "dictionary_dir"),
            (name_prompt.rename_dictionary_after_name_prompt, "dictionary_dir"),
            (scripts.script_path_for_name, "script_dir"),
            (scripts.ensure_no_processing_script, "script_dir"),
            (scripts.list_script_names, "script_dir"),
            (scripts.script_exists, "script_dir"),
            (scripts.create_script, "script_dir"),
            (scripts.import_script, "script_dir"),
            (scripts.rename_script, "script_dir"),
            (scripts.export_script, "script_dir"),
            (scripts.delete_script, "script_dir"),
            (workspace.ensure_workspace_directory, "workspace_dir"),
            (workspace.document_package_path_for_name, "workspace_dir"),
````

File: `client/tests/test_text_scripts_manager.py`

````python
"""The script folder of F-18: the files (manager), the actions and the status of a script."""

import errno
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conversion.preprocessing.user_script import NO_PROCESSING_SCRIPT
from i18n import _
from shared.name_validation import NameValidationError
from tests.file_log_isolation import isolate_file_logs
from tests.windows_file_handles import hold_open
from text_scripts.actions import get_script_action_availability, script_display_name
from text_scripts.manager import (
    NO_PROCESSING_DISPLAY_NAME,
    ScriptImportSourceError,
    create_script,
    delete_script,
    ensure_no_processing_script,
    export_script,
    import_script,
    is_no_processing_script,
    list_script_names,
    normalize_script_name,
    rename_script,
    resolve_selected_script,
    script_exists,
    script_path_for_name,
)
from text_scripts.read_problems import (
    ScriptStatus,
    describe_script_problem,
    describe_unreadable_script,
    read_script_status,
)

LOGGER = "dotexpress.gui"
UPPER = b"def main(text: str) -> str:\n    return text.upper()\n"
# As some Windows editors save it: a BOM, CRLF and CJK text.
BOM_SCRIPT = b"\xef\xbb\xbf" + "def main(text):\r\n    return text.replace('台', '臺')\r\n".encode("utf-8")
NOT_UTF8 = "def main(text):\n    return text + '臺'\n".encode("cp950")


def setUpModule() -> None:
    # A script that cannot be read is logged to dotexpress.gui (gui.log), as a dictionary is (F-6).
    unittest.addModuleCleanup(isolate_file_logs(LOGGER))


class ScriptFolderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.script_dir = self.root / "script"

    def write_script(self, name: str, data: bytes = UPPER) -> Path:
        self.script_dir.mkdir(parents=True, exist_ok=True)
        path = self.script_dir / f"{name}.py"
        path.write_bytes(data)
        return path

    def listing(self, directory: Path | None = None) -> list[str]:
        return sorted(path.name for path in (directory or self.script_dir).iterdir())


class ScriptFolderTest(ScriptFolderTestCase):
    def test_ensure_creates_the_folder_and_no_processing(self) -> None:
        path = ensure_no_processing_script(self.script_dir)

        self.assertEqual(path, self.script_dir / "no-processing.py")
        self.assertEqual(path.read_bytes(), b"def main(input: str) -> str:\n    return input\n")
        self.assertEqual(self.listing(), ["no-processing.py"])

    def test_ensure_never_rewrites_an_existing_file(self) -> None:
        # F-18 (D4): user bytes in no-processing.py are left alone; conversion never reads them.
        altered = self.write_script("no-processing", b"def main(text):\n    return text.upper()\n")

        with patch("os.replace") as replace:
            ensure_no_processing_script(self.script_dir)

        replace.assert_not_called()
        self.assertEqual(altered.read_bytes(), b"def main(text):\n    return text.upper()\n")

    def test_no_processing_comes_first_and_the_others_in_dictionary_order(self) -> None:
        # F-18 (D1, O1): not alphabetical for No Processing; the others casefold, then the name.
        for name in ("zeta", "Beta", "alpha", "中文", "beta2", "no-processing"):
            self.write_script(name)

        self.assertEqual(list_script_names(self.script_dir), ["no-processing", "alpha", "Beta", "beta2", "zeta", "中文"])

    def test_only_python_files_are_scripts(self) -> None:
        self.write_script("alpha")
        (self.script_dir / "notes.txt").write_text("x", encoding="utf-8")
        (self.script_dir / "folder.py").mkdir()

        self.assertEqual(list_script_names(self.script_dir), ["alpha"])

    def test_a_missing_folder_lists_nothing(self) -> None:
        self.assertEqual(list_script_names(self.script_dir), [])

    def test_a_name_maps_to_a_python_file(self) -> None:
        self.assertEqual(script_path_for_name("臺灣", self.script_dir), self.script_dir / "臺灣.py")
        self.assertTrue(is_no_processing_script("no-processing"))
        self.assertTrue(is_no_processing_script(" No-Processing "))
        self.assertFalse(is_no_processing_script("no-processing2"))

    def test_resolve_keeps_a_listed_name_and_falls_back_to_no_processing(self) -> None:
        names = ["no-processing", "alpha"]
        self.assertEqual(resolve_selected_script(names, "alpha"), "alpha")
        for saved in ("missing", "", None, "Alpha"):
            with self.subTest(saved=saved):
                self.assertEqual(resolve_selected_script(names, saved), "no-processing")
        self.assertEqual(resolve_selected_script([], "alpha"), "no-processing")


class ScriptNameTest(ScriptFolderTestCase):
    def assert_refused(self, name: str, code: str) -> None:
        with self.assertRaises(NameValidationError) as raised:
            normalize_script_name(name)
        self.assertEqual(raised.exception.code, code)

    def test_names_follow_the_dictionary_rules(self) -> None:
        self.assertEqual(normalize_script_name("  大寫 1"), "大寫 1")
        self.assertEqual(normalize_script_name("1.1"), "1.1")
        for name, code in (("", "empty"), ("   ", "empty"), ("x" * 33, "too_long"), ("a/b", "invalid"), ("CON", "invalid"), ("a.", "invalid")):
            with self.subTest(name=name):
                self.assert_refused(name, code)

    def test_no_processing_names_are_reserved_in_any_case(self) -> None:
        # F-18 (D4): the internal name, the msgid and its translation.
        self.assertEqual(NO_PROCESSING_DISPLAY_NAME, "No Processing")
        for name in ("no-processing", "NO-PROCESSING", " No-Processing", "No Processing", "no processing", "不處理"):
            with self.subTest(name=name):
                self.assert_refused(name, "reserved")

    def test_script_exists_compares_the_normalized_name(self) -> None:
        self.write_script("alpha")

        self.assertTrue(script_exists(self.script_dir, " alpha"))
        self.assertFalse(script_exists(self.script_dir, "beta"))


class CreateScriptTest(ScriptFolderTestCase):
    def test_create_writes_the_source_as_it_is(self) -> None:
        source = "def main(text):\r\n    return text + '臺'\n"

        path = create_script(self.script_dir, " upper", source)

        self.assertEqual(path, self.script_dir / "upper.py")
        self.assertEqual(path.read_bytes(), source.encode("utf-8"))

    def test_a_taken_name_is_refused_and_the_file_kept(self) -> None:
        existing = self.write_script("upper", b"KEEP")

        with self.assertRaises(FileExistsError):
            create_script(self.script_dir, "upper", NO_PROCESSING_SCRIPT)

        self.assertEqual(existing.read_bytes(), b"KEEP")

    def test_invalid_code_writes_nothing(self) -> None:
        self.script_dir.mkdir()
        for source, error in (("def main(:\n", SyntaxError), ("def main(a, b):\n    return a\n", ValueError)):
            with self.subTest(source=source):
                with self.assertRaises(error):
                    create_script(self.script_dir, "bad", source)
                self.assertEqual(self.listing(), [])


class ImportScriptTest(ScriptFolderTestCase):
    def source(self, name: str, data: bytes) -> Path:
        folder = self.root / "source"
        folder.mkdir(exist_ok=True)
        path = folder / name
        path.write_bytes(data)
        return path

    def test_import_copies_the_original_bytes(self) -> None:
        for name, data in (("upper2.py", UPPER), ("bom.PY", BOM_SCRIPT)):
            with self.subTest(name=name):
                path = import_script(self.script_dir, self.source(name, data), Path(name).stem)

                self.assertEqual(path, self.script_dir / f"{Path(name).stem}.py")
                self.assertEqual(path.read_bytes(), data)

    def test_only_a_py_suffix_is_accepted(self) -> None:
        # F-18 (D8.5): the file filter can be bypassed by typing a name.
        for name in ("upper.txt", "upper", "upper.pyw", "upper.py.txt"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as raised:
                    import_script(self.script_dir, self.source(name, UPPER), "upper")
                self.assertEqual(str(raised.exception), "Only Python files (.py) can be imported.")
                self.assertFalse(self.script_dir.exists() and self.listing())

    def test_invalid_sources_copy_nothing(self) -> None:
        cases = (
            ("cp950.py", NOT_UTF8, UnicodeDecodeError),
            ("bad.py", b"def main(:\n", SyntaxError),
            ("two.py", b"def main(a, b):\n    return a\n", ValueError),
            ("int.py", b"def main(a: int) -> str:\n    return str(a)\n", ValueError),
        )
        for name, data, error in cases:
            with self.subTest(name=name):
                with self.assertRaises(error):
                    import_script(self.script_dir, self.source(name, data), Path(name).stem)
                self.assertEqual(self.listing(), [])

    def test_a_source_that_cannot_be_opened_is_told_apart(self) -> None:
        source = self.source("upper.py", UPPER)
        denied = PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(source))

        with patch.object(Path, "read_bytes", side_effect=denied), self.assertRaises(ScriptImportSourceError) as raised:
            import_script(self.script_dir, source, "upper")

        self.assertIs(raised.exception.error, denied)
        self.assertIs(raised.exception.__cause__, denied)
        self.assertEqual(self.listing(), [])

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_a_source_held_without_read_sharing_is_told_apart(self) -> None:
        source = self.source("upper.py", UPPER)
        hold_open(self, source, 0)

        with self.assertRaises(ScriptImportSourceError) as raised:
            import_script(self.script_dir, source, "upper")

        self.assertIsInstance(raised.exception.error, PermissionError)
        self.assertEqual(self.listing(), [])

    def test_a_taken_name_raises_file_exists_and_keeps_the_file(self) -> None:
        existing = self.write_script("upper", b"KEEP")

        with self.assertRaises(FileExistsError):
            import_script(self.script_dir, self.source("upper.py", UPPER), "Upper")

        self.assertEqual(existing.read_bytes(), b"KEEP")
        self.assertEqual(self.listing(), ["upper.py"])

    def test_a_reserved_name_is_refused(self) -> None:
        with self.assertRaises(NameValidationError):
            import_script(self.script_dir, self.source("no-processing.py", UPPER), "no-processing")


class RenameDeleteExportTest(ScriptFolderTestCase):
    def test_rename_moves_the_file(self) -> None:
        self.write_script("upper", BOM_SCRIPT)

        path = rename_script(self.script_dir, "upper", " shout")

        self.assertEqual(path, self.script_dir / "shout.py")
        self.assertEqual(self.listing(), ["shout.py"])
        self.assertEqual(path.read_bytes(), BOM_SCRIPT)

    def test_rename_refuses_no_processing_and_a_taken_name(self) -> None:
        ensure_no_processing_script(self.script_dir)
        self.write_script("upper")
        self.write_script("shout")

        with self.assertRaises(ValueError):
            rename_script(self.script_dir, "no-processing", "other")
        with self.assertRaises(FileExistsError):
            rename_script(self.script_dir, "upper", "shout")
        with self.assertRaises(NameValidationError):
            rename_script(self.script_dir, "upper", "No Processing")
        self.assertEqual(self.listing(), ["no-processing.py", "shout.py", "upper.py"])

    @unittest.skipUnless(os.name == "nt", "case-insensitive file names")
    def test_a_case_only_rename_works(self) -> None:
        self.write_script("upper")

        rename_script(self.script_dir, "upper", "Upper")

        self.assertEqual(list_script_names(self.script_dir), ["Upper"])

    def test_delete_removes_a_script_and_refuses_no_processing(self) -> None:
        ensure_no_processing_script(self.script_dir)
        self.write_script("upper")

        delete_script(self.script_dir, "upper")
        with self.assertRaises(ValueError):
            delete_script(self.script_dir, "No-Processing")

        self.assertEqual(self.listing(), ["no-processing.py"])

    def test_export_copies_the_bytes(self) -> None:
        self.write_script("bom", BOM_SCRIPT)
        self.write_script("cp950", NOT_UTF8)
        export_dir = self.root / "export"
        export_dir.mkdir()
        (export_dir / "bom.py").write_bytes(b"OLD")

        for name, data in (("bom", BOM_SCRIPT), ("cp950", NOT_UTF8)):
            with self.subTest(name=name):
                export_script(self.script_dir, name, export_dir / f"{name}.py")
                self.assertEqual((export_dir / f"{name}.py").read_bytes(), data)
        self.assertEqual(self.listing(export_dir), ["bom.py", "cp950.py"])

    def test_export_of_no_processing_writes_its_text_not_the_file(self) -> None:
        # F-18 (D4): the documented content, even after the disk file was altered.
        self.write_script("no-processing", b"def main(text):\n    return text.upper()\n")
        destination = self.root / "no-processing.py"

        export_script(self.script_dir, "no-processing", destination)

        self.assertEqual(destination.read_bytes(), b"def main(input: str) -> str:\n    return input\n")

    def test_export_onto_a_folder_fails_as_a_dictionary_export_does(self) -> None:
        self.write_script("upper")
        destination = self.root / "folder.py"
        (destination / "keep").mkdir(parents=True)

        for name in ("upper", "no-processing"):
            with self.subTest(name=name):
                with self.assertRaises(OSError) as raised:
                    export_script(self.script_dir, name, destination)
                code = errno.EACCES if os.name == "nt" else errno.EISDIR
                self.assertEqual(str(raised.exception), f"[Errno {code}] {os.strerror(code)}: {str(destination)!r}")
                self.assertEqual(os.listdir(destination), ["keep"])


class ScriptActionsTest(unittest.TestCase):
    def test_no_processing_can_only_be_exported(self) -> None:
        # F-18 (D7): unlike the default dictionary, it cannot be edited either.
        names = ["no-processing", "upper"]
        availability = get_script_action_availability(names, "no-processing")
        self.assertEqual(
            (availability.edit, availability.delete, availability.rename, availability.export),
            (False, False, False, True),
        )
        availability = get_script_action_availability(names, "upper")
        self.assertEqual(
            (availability.edit, availability.delete, availability.rename, availability.export),
            (True, True, True, True),
        )
        availability = get_script_action_availability([], "")
        self.assertEqual(
            (availability.edit, availability.delete, availability.rename, availability.export),
            (False, False, False, False),
        )

    def test_no_processing_is_shown_translated(self) -> None:
        self.assertEqual(script_display_name("no-processing"), "不處理")
        self.assertEqual(script_display_name("no-processing"), _("No Processing"))
        self.assertEqual(script_display_name("大寫"), "大寫")


class ScriptStatusTest(ScriptFolderTestCase):
    def test_a_valid_script_is_ready(self) -> None:
        for name, data in (("upper", UPPER), ("bom", BOM_SCRIPT)):
            with self.subTest(name=name):
                check = read_script_status(self.write_script(name, data))
                self.assertEqual((check.status, check.error), (ScriptStatus.READY, None))

    def test_code_that_breaks_the_rule_is_not_valid_and_not_logged(self) -> None:
        cases = (
            (b"def main(:\n", SyntaxError),
            (b"def main(a, b):\n    return a\n", ValueError),
            (b"def main(a) -> int:\n    return a\n", ValueError),
        )
        for data, error in cases:
            with self.subTest(data=data):
                with self.assertNoLogs(LOGGER):
                    check = read_script_status(self.write_script("bad", data))
                self.assertEqual(check.status, ScriptStatus.NOT_VALID)
                self.assertIsInstance(check.error, error)

    def test_a_file_that_cannot_be_read_is_unreadable_and_logged_on_one_line(self) -> None:
        path = self.write_script("cp950", NOT_UTF8)
        with self.assertLogs(LOGGER, "ERROR") as logs:
            check = read_script_status(path)

        self.assertEqual(check.status, ScriptStatus.UNREADABLE)
        self.assertIsInstance(check.error, UnicodeDecodeError)
        self.assertEqual(len(logs.records), 1)
        self.assertTrue(logs.output[0].startswith('ERROR:dotexpress.gui:Cannot read script "cp950.py": UnicodeDecodeError: '))
        self.assertIsNone(logs.records[0].exc_info)

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_a_file_held_without_read_sharing_is_unreadable(self) -> None:
        path = self.write_script("locked")
        hold_open(self, path, 0)
        with self.assertLogs(LOGGER, "ERROR"):
            check = read_script_status(path)

        self.assertEqual(check.status, ScriptStatus.UNREADABLE)
        self.assertIsInstance(check.error, PermissionError)
        self.assertEqual(
            describe_script_problem(check.error),
            "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。",
        )

    def test_each_problem_has_its_reason(self) -> None:
        not_utf8 = self.assertRaises(UnicodeDecodeError)
        with not_utf8:
            NOT_UTF8.decode("utf-8")
        cases = (
            (not_utf8.exception, "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"),
            (
                PermissionError(errno.EACCES, "denied"),
                "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。",
            ),
            (FileNotFoundError(errno.ENOENT, "missing"), "無法讀取檔案：[Errno 2] missing"),
            (SyntaxError("invalid syntax", ("bad.py", 1, 10, "def main(:\n")), "invalid syntax (bad.py, line 1)"),
            (
                ValueError("main must define exactly one positional parameter and no other parameters."),
                "main 必須恰好定義一個位置參數，且不得有其他參數。",
            ),
            (ValueError("The parameter of main must be annotated as str, or not annotated."), "main 的參數只能標註為 str，或不加標註。"),
            (
                ValueError("The return value of main must be annotated as str, or not annotated."),
                "main 的傳回值只能標註為 str，或不加標註。",
            ),
            (RecursionError("too deep"), "too deep"),
        )
        for error, reason in cases:
            with self.subTest(error=type(error).__name__, reason=reason):
                self.assertEqual(describe_script_problem(error), reason)

    def test_the_edit_box_names_the_script_above_the_reason(self) -> None:
        error = FileNotFoundError(errno.ENOENT, "missing")

        self.assertEqual(describe_unreadable_script("upper", error), "無法讀取腳本「upper」。\n\n無法讀取檔案：[Errno 2] missing")


if __name__ == "__main__":
    unittest.main()
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
from conversion.preprocessing.user_script import (
    DEFAULT_PREPROCESSING_SCRIPT,
    execute_preprocessing_script,
    load_preprocessing_script,
    preprocessing_script_path,
    save_preprocessing_script,
    validate_preprocessing_script,
)
from tests.full_disk import full_disk
from tests.windows_file_handles import make_read_only


````

````python
from conversion.preprocessing.user_script import (
    DEFAULT_PREPROCESSING_SCRIPT,
    NO_PROCESSING_SCRIPT,
    NO_PROCESSING_SCRIPT_NAME,
    SCRIPT_SUFFIX,
    execute_script,
    load_preprocessing_script,
    preprocessing_script_path,
    read_script_source,
    save_script,
    validate_script,
)
from tests.full_disk import full_disk
from tests.windows_file_handles import make_read_only

# The msgids of the signature rule (F-18 D5).
ONE_MAIN = "The script must define exactly one top-level synchronous main function."
ONE_PARAMETER = "main must define exactly one positional parameter and no other parameters."
PARAMETER_ANNOTATION = "The parameter of main must be annotated as str, or not annotated."
RETURN_ANNOTATION = "The return value of main must be annotated as str, or not annotated."


````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
        self.addCleanup(self._tmpdir.cleanup)
        self.directory = Path(self._tmpdir.name)
        self.path = preprocessing_script_path(self.directory)

    def test_path_uses_dictionary_directory(self) -> None:
        self.assertEqual(self.path, self.directory / "preprocessing.py")

    def test_missing_file_loads_identity_script_without_creating_file(self) -> None:
        self.assertEqual(load_preprocessing_script(self.path), DEFAULT_PREPROCESSING_SCRIPT)
        self.assertFalse(self.path.exists())

    def test_validation_accepts_helpers_imports_and_any_parameter_name(self) -> None:
        source = "import re\n\ndef clean(value):\n    return re.sub(' +', ' ', value)\n\ndef main(text):\n    return clean(text)\n"
        validate_preprocessing_script(source)

    def test_validation_rejects_syntax_error(self) -> None:
        with self.assertRaises(SyntaxError):
            validate_preprocessing_script("def main(:\n")

    def test_validation_does_not_execute_valid_module_code(self) -> None:
        validate_preprocessing_script(
            "raise RuntimeError('must not run while saving')\n"
            "def main(text):\n    return text\n"
````

````python
        self.addCleanup(self._tmpdir.cleanup)
        self.directory = Path(self._tmpdir.name)
        self.path = self.directory / "upper.py"

    def test_path_uses_dictionary_directory(self) -> None:
        self.assertEqual(preprocessing_script_path(self.directory), self.directory / "preprocessing.py")

    def test_missing_file_loads_identity_script_without_creating_file(self) -> None:
        path = preprocessing_script_path(self.directory)
        self.assertEqual(load_preprocessing_script(path), DEFAULT_PREPROCESSING_SCRIPT)
        self.assertFalse(path.exists())

    def test_no_processing_is_the_identity_script_of_the_spec(self) -> None:
        # F-18 (D-D): the text the user gave, also the template of a new script.
        self.assertEqual(NO_PROCESSING_SCRIPT_NAME, "no-processing")
        self.assertEqual(NO_PROCESSING_SCRIPT, "def main(input: str) -> str:\n    return input\n")
        self.assertEqual(SCRIPT_SUFFIX, ".py")
        validate_script(NO_PROCESSING_SCRIPT)

    def test_validation_accepts_helpers_imports_and_any_parameter_name(self) -> None:
        source = "import re\n\ndef clean(value):\n    return re.sub(' +', ' ', value)\n\ndef main(text):\n    return clean(text)\n"
        validate_script(source)

    def test_validation_rejects_syntax_error(self) -> None:
        with self.assertRaises(SyntaxError):
            validate_script("def main(:\n")

    def test_validation_does_not_execute_valid_module_code(self) -> None:
        validate_script(
            "raise RuntimeError('must not run while saving')\n"
            "def main(text):\n    return text\n"
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    validate_preprocessing_script(source)

    def test_validation_requires_one_positional_parameter_and_no_others(self) -> None:
````

````python
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError) as raised:
                    validate_script(source)
                self.assertEqual(str(raised.exception), ONE_MAIN)

    def test_validation_requires_one_positional_parameter_and_no_others(self) -> None:
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    validate_preprocessing_script(source)

    def test_save_uses_utf8_and_atomic_replace(self) -> None:
        source = "def main(text):\n    return text + '臺灣'\n"
        with patch("os.replace", wraps=os.replace) as replace:
            save_preprocessing_script(self.path, source)
        self.assertEqual(self.path.read_text(encoding="utf-8"), source)
        replace.assert_called_once()
        self.assertEqual(list(self.directory.glob(".preprocessing.py.*.tmp")), [])

    def _temporary_files(self) -> list[str]:
````

````python
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError) as raised:
                    validate_script(source)
                self.assertEqual(str(raised.exception), ONE_PARAMETER)

    def test_annotations_are_optional_and_str_when_present(self) -> None:
        # F-18 (D-B, D5, O2): a quoted "str" counts; a default value stays allowed.
        valid_sources = (
            "def main(x):\n    return x\n",
            "def main(x: str):\n    return x\n",
            "def main(x) -> str:\n    return x\n",
            "def main(x: str) -> str:\n    return x\n",
            "def main(x: 'str') -> 'str':\n    return x\n",
            "def main(x: str = '') -> str:\n    return x\n",
            "def main(x, /) -> str:\n    return x\n",
        )
        for source in valid_sources:
            with self.subTest(source=source):
                validate_script(source)

    def test_an_annotation_other_than_str_is_refused(self) -> None:
        invalid_sources = (
            ("from typing import Optional\ndef main(x: Optional[str]) -> str:\n    return x\n", PARAMETER_ANNOTATION),
            ("def main(x: int) -> str:\n    return str(x)\n", PARAMETER_ANNOTATION),
            ("import builtins\ndef main(x: builtins.str):\n    return x\n", PARAMETER_ANNOTATION),
            ("def main(x: 'int'):\n    return x\n", PARAMETER_ANNOTATION),
            ("def main(x: int) -> int:\n    return x\n", PARAMETER_ANNOTATION),
            ("def main(x) -> int:\n    return x\n", RETURN_ANNOTATION),
            ("def main(x: str) -> None:\n    return None\n", RETURN_ANNOTATION),
            ("from typing import Text\ndef main(x) -> Text:\n    return x\n", RETURN_ANNOTATION),
        )
        for source, message in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError) as raised:
                    validate_script(source)
                self.assertEqual(str(raised.exception), message)

    def test_save_uses_utf8_and_atomic_replace(self) -> None:
        source = "def main(text):\n    return text + '臺灣'\n"
        with patch("os.replace", wraps=os.replace) as replace:
            save_script(self.path, source)
        self.assertEqual(self.path.read_text(encoding="utf-8"), source)
        replace.assert_called_once()
        self.assertEqual(list(self.directory.glob(".upper.py.*.tmp")), [])

    def _temporary_files(self) -> list[str]:
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
        source = "def main(text):\r\n    return text\n"
        with patch("shared.atomic_write.os.fsync", wraps=os.fsync) as fsync, patch("os.replace", wraps=os.replace) as replace:
            save_preprocessing_script(self.path, source)

        fsync.assert_called_once()
        replace.assert_called_once()
        self.assertRegex(Path(replace.call_args.args[0]).name, r"^\.preprocessing\.py\.[0-9a-f]{16}\.tmp$")
        self.assertEqual(self.path.read_bytes(), source.encode("utf-8"))
        self.assertEqual(self._temporary_files(), [])

    def test_write_error_leaves_no_temporary_file_and_keeps_the_script(self) -> None:
````

````python
        source = "def main(text):\r\n    return text\n"
        with patch("shared.atomic_write.os.fsync", wraps=os.fsync) as fsync, patch("os.replace", wraps=os.replace) as replace:
            save_script(self.path, source)

        fsync.assert_called_once()
        replace.assert_called_once()
        self.assertRegex(Path(replace.call_args.args[0]).name, r"^\.upper\.py\.[0-9a-f]{16}\.tmp$")
        self.assertEqual(self.path.read_bytes(), source.encode("utf-8"))
        self.assertEqual(self._temporary_files(), [])

    def test_save_creates_the_folder(self) -> None:
        path = self.directory / "script" / "upper.py"

        save_script(path, "def main(text):\n    return text\n")

        self.assertEqual(path.read_bytes(), b"def main(text):\n    return text\n")

    def test_write_error_leaves_no_temporary_file_and_keeps_the_script(self) -> None:
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python

        with full_disk(self.directory, after=10), self.assertRaises(OSError) as raised:
            save_preprocessing_script(self.path, "def main(text):\n    return text.upper()\n")

        self.assertEqual(raised.exception.errno, errno.ENOSPC)
````

````python

        with full_disk(self.directory, after=10), self.assertRaises(OSError) as raised:
            save_script(self.path, "def main(text):\n    return text.upper()\n")

        self.assertEqual(raised.exception.errno, errno.ENOSPC)
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python

        with self.assertRaises(PermissionError) as raised:
            save_preprocessing_script(self.path, "def main(text):\n    return text.upper()\n")

        self.assertEqual(Path(raised.exception.filename).name, "preprocessing.py")
        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), old)
````

````python

        with self.assertRaises(PermissionError) as raised:
            save_script(self.path, "def main(text):\n    return text.upper()\n")

        self.assertEqual(Path(raised.exception.filename).name, "upper.py")
        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), old)
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
        original = "def main(text):\n    return text\n"
        self.path.write_text(original, encoding="utf-8")
        with self.assertRaises(SyntaxError):
            save_preprocessing_script(self.path, "def main(:\n")
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_execution_supports_helpers_imports_file_name_and_fresh_globals(self) -> None:
````

````python
        original = "def main(text):\n    return text\n"
        self.path.write_text(original, encoding="utf-8")
        for source, error in (("def main(:\n", SyntaxError), ("def main(x: int):\n    return x\n", ValueError)):
            with self.subTest(source=source):
                with self.assertRaises(error):
                    save_script(self.path, source)
                self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_read_keeps_the_text_and_drops_a_bom(self) -> None:
        # F-18 (D6): UTF-8 with or without a BOM; line ends as they are.
        source = "def main(text):\r\n    return text + '臺'\r\n"
        for data in (source.encode("utf-8"), b"\xef\xbb\xbf" + source.encode("utf-8")):
            with self.subTest(bom=data.startswith(b"\xef")):
                self.path.write_bytes(data)
                self.assertEqual(read_script_source(self.path), source)

    def test_read_refuses_a_file_that_is_not_utf8_and_a_missing_file(self) -> None:
        self.path.write_bytes("def main(text):\n    return text + '臺'\n".encode("cp950"))
        with self.assertRaises(UnicodeDecodeError):
            read_script_source(self.path)
        with self.assertRaises(FileNotFoundError):
            read_script_source(self.directory / "missing.py")

    def test_execution_supports_helpers_imports_file_name_and_fresh_globals(self) -> None:
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
        )
        expected = f"1:{self.path}:a b"
        self.assertEqual(execute_preprocessing_script(self.path, "a  b"), expected)
        self.assertEqual(execute_preprocessing_script(self.path, "a  b"), expected)

    def test_execution_rejects_non_callable_main_and_non_string_return(self) -> None:
````

````python
        )
        expected = f"1:{self.path}:a b"
        self.assertEqual(execute_script(self.path, "a  b"), expected)
        self.assertEqual(execute_script(self.path, "a  b"), expected)

    def test_execution_runs_a_script_saved_with_a_bom(self) -> None:
        self.path.write_bytes(b"\xef\xbb\xbfdef main(text: str) -> str:\r\n    return text.upper()\r\n")

        self.assertEqual(execute_script(self.path, "abc"), "ABC")

    def test_execution_of_a_missing_or_undecodable_script_fails(self) -> None:
        # F-18 (D10, O8): no identity fallback.
        with self.assertRaises(FileNotFoundError):
            execute_script(self.directory / "missing.py", "source")
        self.path.write_bytes("def main(text):\n    return '臺'\n".encode("cp950"))
        with self.assertRaises(UnicodeDecodeError):
            execute_script(self.path, "source")

    def test_execution_rejects_non_callable_main_and_non_string_return(self) -> None:
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
                self.path.write_text(source, encoding="utf-8")
                with self.assertRaises(TypeError) as raised:
                    execute_preprocessing_script(self.path, "source")

                self.assertEqual(str(raised.exception), message)

    def test_execution_rejects_externally_written_invalid_contract(self) -> None:
        self.path.write_text("def main(first, second):\n    return first\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            execute_preprocessing_script(self.path, "source")


````

````python
                self.path.write_text(source, encoding="utf-8")
                with self.assertRaises(TypeError) as raised:
                    execute_script(self.path, "source")

                self.assertEqual(str(raised.exception), message)

    def test_execution_rejects_externally_written_invalid_contract(self) -> None:
        for source in ("def main(first, second):\n    return first\n", "def main(x) -> bytes:\n    return x\n"):
            with self.subTest(source=source):
                self.path.write_text(source, encoding="utf-8")
                with self.assertRaises(ValueError):
                    execute_script(self.path, "source")


````

```bash
$PY -B -X utf8 -m unittest tests.test_user_preprocessing_script tests.test_text_scripts_manager tests.test_app_paths 2>&1 | $PY $T/tools/brief.py
```

Expected (the new names do not exist yet):

```text
ERROR: test_user_preprocessing_script (unittest.loader._FailedTest.test_user_preprocessing_script)
ImportError: Failed to import test module: test_user_preprocessing_script
ImportError: cannot import name 'NO_PROCESSING_SCRIPT' from 'conversion.preprocessing.user_script' (<client>\conversion\preprocessing\user_script.py)
ERROR: test_text_scripts_manager (unittest.loader._FailedTest.test_text_scripts_manager)
ImportError: Failed to import test module: test_text_scripts_manager
ERROR: test_folder_parameters_have_no_default (tests.test_app_paths.ApplicationPathsApiTest.test_folder_parameters_have_no_default)
ModuleNotFoundError: No module named 'text_scripts'
ERROR: test_build_application_paths_uses_one_root (tests.test_app_paths.ApplicationPathsTest.test_build_application_paths_uses_one_root)
AttributeError: 'ApplicationPaths' object has no attribute 'script'
FAIL: test_the_script_folder_is_prepared_after_the_dictionary_folder (tests.test_app_paths.ApplicationPathsTest.test_the_script_folder_is_prepared_after_the_dic
AssertionError: Tuples differ: (Wind[89 chars]ress/workspace'), WindowsPath('C:/DotExpress/l[40 chars]ew')) != (Wind[89 chars]ress/script'), WindowsPath('C:/Dot
Ran 13 tests
FAILED (failures=1, errors=4)
```

- [x] **Step 2: Green: the contract, the script folder, the manager, the actions and the status** (`user_script.py`, `manager.py`, `app_paths.py`, `file_targets.py` 4 spaces; `actions.py`, `read_problems.py` tabs).

Edit: `client/.gitignore`

````python
dist/
dictionary/
log/
.venv/
````

````python
dist/
dictionary/
script/
log/
.venv/
````

Edit: `client/app_paths.py`

````python
    config: Path
    dictionary: Path
    workspace: Path
    log: Path
````

````python
    config: Path
    dictionary: Path
    script: Path
    workspace: Path
    log: Path
````

Edit: `client/app_paths.py`

````python
    @property
    def writable_directories(self) -> tuple[Path, ...]:
        return (self.root, self.dictionary, self.workspace, self.log, self.dual_view)


````

````python
    @property
    def writable_directories(self) -> tuple[Path, ...]:
        return (self.root, self.dictionary, self.script, self.workspace, self.log, self.dual_view)


````

Edit: `client/app_paths.py`

````python
        config=application_root / "config.json",
        dictionary=application_root / "dictionary",
        workspace=application_root / "workspace",
        log=application_root / "log",
````

````python
        config=application_root / "config.json",
        dictionary=application_root / "dictionary",
        script=application_root / "script",
        workspace=application_root / "workspace",
        log=application_root / "log",
````

Edit: `client/conversion/preprocessing/user_script.py`

````python
from __future__ import annotations

````

````python
"""The contract of a text-processing script: check, read, save and run it (F-18).

A script is a Python file with one top-level ``main`` that takes the source text and
returns the text to convert. Scripts run with the full rights of DotExpress; nothing
here limits what they do (F-18 D13).
"""

from __future__ import annotations

````

Edit: `client/conversion/preprocessing/user_script.py`

````python


PREPROCESSING_FILENAME = "preprocessing.py"
DEFAULT_PREPROCESSING_SCRIPT = "def main(input: str) -> str:\n    return input\n"


````

````python


# The script that changes nothing: its internal name (the stem of its file) and its text
# (F-18 D-D). It is also the template of a new script.
NO_PROCESSING_SCRIPT_NAME = "no-processing"
NO_PROCESSING_SCRIPT = "def main(input: str) -> str:\n    return input\n"
SCRIPT_SUFFIX = ".py"

# The single script of the Text Processing dialog, next to the dictionaries (before F-18).
PREPROCESSING_FILENAME = "preprocessing.py"
DEFAULT_PREPROCESSING_SCRIPT = NO_PROCESSING_SCRIPT


````

Edit: `client/conversion/preprocessing/user_script.py`

````python


def validate_preprocessing_script(
    source: str,
    *,
    filename: str = PREPROCESSING_FILENAME,
) -> None:
    tree = ast.parse(source, filename=filename, mode="exec")
    compile(tree, filename, "exec")
````

````python


def _is_str_annotation(annotation: ast.expr) -> bool:
    """Whether ``annotation`` is ``str`` or the quoted ``"str"`` (F-18 D5, O2)."""
    if isinstance(annotation, ast.Name):
        return annotation.id == "str"
    return isinstance(annotation, ast.Constant) and isinstance(annotation.value, str) and annotation.value == "str"


def validate_script(source: str, *, filename: str = "<script>") -> None:
    """Check ``source`` without running it (F-18 D-B, D5).

    Raises ``SyntaxError`` if it does not compile, and ``ValueError`` with an untranslated
    msgid if it does not define exactly one top-level synchronous ``main`` with exactly one
    positional parameter, or if an annotation of ``main`` is not ``str``. Annotations are
    optional.
    """
    tree = ast.parse(source, filename=filename, mode="exec")
    compile(tree, filename, "exec")
````

Edit: `client/conversion/preprocessing/user_script.py`

````python
    if len(main_definitions) != 1 or not isinstance(main_definitions[0], ast.FunctionDef):
        raise ValueError(N_("The script must define exactly one top-level synchronous main function."))
    arguments = main_definitions[0].args
    positional = [*arguments.posonlyargs, *arguments.args]
    if (
````

````python
    if len(main_definitions) != 1 or not isinstance(main_definitions[0], ast.FunctionDef):
        raise ValueError(N_("The script must define exactly one top-level synchronous main function."))
    main = main_definitions[0]
    arguments = main.args
    positional = [*arguments.posonlyargs, *arguments.args]
    if (
````

Edit: `client/conversion/preprocessing/user_script.py`

````python
    ):
        raise ValueError(N_("main must define exactly one positional parameter and no other parameters."))


def save_preprocessing_script(path: Path | str, source: str) -> None:
    """Validate ``source`` and write it to ``path`` through a synced temporary file (F-8).

````

````python
    ):
        raise ValueError(N_("main must define exactly one positional parameter and no other parameters."))
    if positional[0].annotation is not None and not _is_str_annotation(positional[0].annotation):
        raise ValueError(N_("The parameter of main must be annotated as str, or not annotated."))
    if main.returns is not None and not _is_str_annotation(main.returns):
        raise ValueError(N_("The return value of main must be annotated as str, or not annotated."))


def read_script_source(path: Path | str) -> str:
    """The text of the script at ``path``, UTF-8 with or without a BOM (F-18 D6).

    A missing file raises ``FileNotFoundError`` and a file that is not UTF-8
    ``UnicodeDecodeError``; other ``OSError``s pass through. Line ends are kept.
    """
    return Path(path).read_bytes().decode("utf-8-sig")


def save_script(path: Path | str, source: str) -> None:
    """Validate ``source`` and write it to ``path`` through a synced temporary file (F-8).

````

Edit: `client/conversion/preprocessing/user_script.py`

````python
    """
    destination = Path(path)
    validate_preprocessing_script(source, filename=str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomically(destination, lambda stream: stream.write(source), encoding="utf-8", newline="")


def execute_preprocessing_script(path: Path | str, input_text: str) -> str:
    source_path = Path(path)
    source = load_preprocessing_script(source_path)
    validate_preprocessing_script(source, filename=str(source_path))
    namespace = {
        "__name__": "__dotexpress_preprocessing__",
````

````python
    """
    destination = Path(path)
    validate_script(source, filename=str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomically(destination, lambda stream: stream.write(source), encoding="utf-8", newline="")


save_preprocessing_script = save_script


def execute_script(path: Path | str, input_text: str) -> str:
    """Read the script at ``path``, check it and return ``main(input_text)`` (F-18 D10)."""
    source_path = Path(path)
    return _run_script(read_script_source(source_path), source_path, input_text)


def execute_preprocessing_script(path: Path | str, input_text: str) -> str:
    source_path = Path(path)
    return _run_script(load_preprocessing_script(source_path), source_path, input_text)


def _run_script(source: str, source_path: Path, input_text: str) -> str:
    validate_script(source, filename=str(source_path))
    namespace = {
        "__name__": "__dotexpress_preprocessing__",
````

Edit: `client/dictionaries/manager.py`

````python

import csv
import errno
import os
from pathlib import Path
import shutil
````

````python

import csv
from pathlib import Path
import shutil
````

Edit: `client/dictionaries/manager.py`

````python

from shared.atomic_write import write_bytes_atomically, write_text_atomically
from shared.name_validation import MAX_NAME_LENGTH, normalize_base_name

````

````python

from shared.atomic_write import write_bytes_atomically, write_text_atomically
from shared.file_targets import is_same_file, refuse_folder_target
from shared.name_validation import MAX_NAME_LENGTH, normalize_base_name

````

Edit: `client/dictionaries/manager.py`

````python
    source_path = dictionary_path_for_name(source_normalized, dictionary_dir)
    destination_path = dictionary_path_for_name(destination_normalized, dictionary_dir)
    if destination_path.exists() and not _is_same_file(source_path, destination_path):
        raise FileExistsError(f"Dictionary '{destination_normalized}' already exists.")
    source_path.rename(destination_path)
````

````python
    source_path = dictionary_path_for_name(source_normalized, dictionary_dir)
    destination_path = dictionary_path_for_name(destination_normalized, dictionary_dir)
    if destination_path.exists() and not is_same_file(source_path, destination_path):
        raise FileExistsError(f"Dictionary '{destination_normalized}' already exists.")
    source_path.rename(destination_path)
````

Edit: `client/dictionaries/manager.py`

````python


def _is_same_file(source: Path, destination: Path) -> bool:
    """Whether ``destination`` names ``source`` itself: a case-only rename on a
    case-insensitive file system, such as ``alpha`` to ``Alpha`` on Windows (F-W6, F-11 D10).

    Another file that only differs in case (a case-sensitive file system) is not the same file.
    """
    try:
        return os.path.samefile(source, destination)
    except OSError:
        return False


def export_dictionary(dictionary_dir: Path, name: str, destination_path: Path | str) -> Path:
    source_path = dictionary_path_for_name(name.strip(), dictionary_dir)
    destination = Path(destination_path)
    if destination.is_dir():
        # The error copying onto a folder gave, as documents.workspace.write_export_text
        # gives for a BRL or HTML export, not a failed replace naming the temporary file.
        if os.name == "nt":
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(destination))
        raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(destination))
    # An existing file there is replaced only once the copy is complete and synced.
    write_bytes_atomically(destination, lambda stream: _copy_file_into(source_path, stream))
````

````python


def export_dictionary(dictionary_dir: Path, name: str, destination_path: Path | str) -> Path:
    source_path = dictionary_path_for_name(name.strip(), dictionary_dir)
    destination = Path(destination_path)
    refuse_folder_target(destination)
    # An existing file there is replaced only once the copy is complete and synced.
    write_bytes_atomically(destination, lambda stream: _copy_file_into(source_path, stream))
````

File: `client/shared/file_targets.py`

````python
"""Checks on the file a rename or a copy goes to, shared by dictionaries and scripts (F-18)."""

from __future__ import annotations

import errno
import os
from pathlib import Path


def is_same_file(source: Path, destination: Path) -> bool:
    """Whether ``destination`` names ``source`` itself: a case-only rename on a
    case-insensitive file system, such as ``alpha`` to ``Alpha`` on Windows (F-W6, F-11 D10).

    Another file that only differs in case (a case-sensitive file system) is not the same file.
    """
    try:
        return os.path.samefile(source, destination)
    except OSError:
        return False


def refuse_folder_target(destination: Path) -> None:
    """Raise the error copying onto a folder gives, if ``destination`` is a folder.

    As ``documents.workspace.write_export_text`` gives it for a BRL or HTML export, not a
    failed replace naming the temporary file.
    """
    if not destination.is_dir():
        return
    if os.name == "nt":
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(destination))
    raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(destination))
````

File: `client/text_scripts/__init__.py`

````python
"""The text-processing scripts and Script Management (F-18)."""
````

File: `client/text_scripts/actions.py`

````python
"""What Script Management may do with the selected script, and how a script is named (F-18)."""

from dataclasses import dataclass

from i18n import _
from text_scripts.manager import NO_PROCESSING_DISPLAY_NAME, is_no_processing_script


@dataclass(frozen=True)
class ScriptActionAvailability:
	edit: bool
	delete: bool
	rename: bool
	export: bool


def get_script_action_availability(script_names: list[str], selected_name: str) -> ScriptActionAvailability:
	"""No Processing can only be exported; any other script can be edited, renamed, deleted and exported (F-18 D7)."""
	has_selection = bool(script_names)
	can_modify = has_selection and not is_no_processing_script(selected_name)
	return ScriptActionAvailability(
		edit=can_modify,
		delete=can_modify,
		rename=can_modify,
		export=has_selection,
	)


def script_display_name(name: str) -> str:
	"""「不處理」 for No Processing, else the name (F-18 D-D)."""
	return _(NO_PROCESSING_DISPLAY_NAME) if is_no_processing_script(name) else name
````

File: `client/text_scripts/manager.py`

````python
"""The script files: list, create, import, rename, export, delete (F-18).

A script name maps to ``<name>.py`` in the script folder, as a dictionary name maps to
``<name>.csv``. ``no-processing.py`` is No Processing, the script that changes nothing:
it is created when missing and never rewritten, and it cannot be renamed or deleted.
Every file this module writes goes through ``shared.atomic_write`` (F-8).
"""

from __future__ import annotations

from pathlib import Path

from conversion.preprocessing.user_script import (
    NO_PROCESSING_SCRIPT,
    NO_PROCESSING_SCRIPT_NAME,
    SCRIPT_SUFFIX,
    save_script,
    validate_script,
)
from i18n import N_, _
from shared.atomic_write import write_bytes_atomically, write_text_atomically
from shared.file_targets import is_same_file, refuse_folder_target
from shared.name_validation import normalize_base_name

# How No Processing is shown; translated when shown (F-14 D4).
NO_PROCESSING_DISPLAY_NAME = N_("No Processing")


class ScriptImportSourceError(Exception):
    """The Import source cannot be opened or read: another program holds it, or reading it
    is not permitted (the twin of ``DictionaryImportSourceError``, F-11 D11).

    ``error`` (also ``__cause__``) is the ``PermissionError``. Not an ``OSError``, so a
    caller can give it F-6's reason while an ``OSError`` writing the copy into the script
    folder keeps its own message.
    """

    def __init__(self, error: PermissionError) -> None:
        super().__init__(str(error))
        self.error = error


def is_no_processing_script(name: str) -> bool:
    return name.strip().casefold() == NO_PROCESSING_SCRIPT_NAME


def script_path_for_name(name: str, script_dir: Path) -> Path:
    return Path(script_dir) / f"{name}{SCRIPT_SUFFIX}"


def ensure_no_processing_script(script_dir: Path) -> Path:
    """Create ``no-processing.py`` with its text if it is missing; an existing file is left alone (F-18 D4)."""
    directory = Path(script_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = script_path_for_name(NO_PROCESSING_SCRIPT_NAME, directory)
    if not path.exists():
        write_text_atomically(path, lambda stream: stream.write(NO_PROCESSING_SCRIPT), encoding="utf-8", newline="")
    return path


def list_script_names(script_dir: Path) -> list[str]:
    """No Processing first, then the other scripts in the order of the dictionaries (F-18 D1, O1)."""
    directory = Path(script_dir)
    if not directory.exists():
        return []
    stems = [path.stem for path in directory.glob(f"*{SCRIPT_SUFFIX}") if path.is_file()]
    others = sorted((stem for stem in stems if not is_no_processing_script(stem)), key=lambda name: (name.casefold(), name))
    return ([NO_PROCESSING_SCRIPT_NAME] if len(others) < len(stems) else []) + others


def normalize_script_name(name: str) -> str:
    """The name without surrounding spaces; ``NameValidationError`` if it cannot name a script.

    No Processing's internal name, its msgid and its translation are reserved, whatever
    their case (F-18 D4).
    """
    reserved = {NO_PROCESSING_SCRIPT_NAME, NO_PROCESSING_DISPLAY_NAME, _(NO_PROCESSING_DISPLAY_NAME)}
    return normalize_base_name(name, reserved_names=reserved)


def script_exists(script_dir: Path, name: str) -> bool:
    return script_path_for_name(normalize_script_name(name), script_dir).exists()


def create_script(script_dir: Path, name: str, source: str) -> Path:
    """Write a new script; ``FileExistsError`` if a script of that name exists (F-18 D8.1)."""
    path = script_path_for_name(normalize_script_name(name), script_dir)
    if path.exists():
        raise FileExistsError(f"Script '{path.stem}' already exists.")
    save_script(path, source)
    return path


def import_script(script_dir: Path, source_path: Path | str, name: str) -> Path:
    """Copy a ``.py`` file that passes the signature rule into the script folder (F-18 D8.5).

    Raises ``ValueError`` (a msgid) for another suffix or a ``main`` that breaks the rule,
    ``SyntaxError``, ``UnicodeDecodeError``, ``ScriptImportSourceError`` when the source
    cannot be opened, and ``FileExistsError`` for a taken name. The copy has the source's
    bytes; nothing is written on any error.
    """
    source = Path(source_path)
    if source.suffix.casefold() != SCRIPT_SUFFIX:
        raise ValueError(N_("Only Python files (.py) can be imported."))
    directory = Path(script_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = script_path_for_name(normalize_script_name(name), directory)
    if destination.exists():
        raise FileExistsError(f"Script '{destination.stem}' already exists.")
    try:
        data = source.read_bytes()
    except PermissionError as error:
        raise ScriptImportSourceError(error) from error
    validate_script(data.decode("utf-8-sig"), filename=str(source))
    write_bytes_atomically(destination, lambda stream: stream.write(data))
    return destination


def rename_script(script_dir: Path, source_name: str, new_name: str) -> Path:
    source_normalized = source_name.strip()
    if is_no_processing_script(source_normalized):
        raise ValueError("No Processing cannot be renamed.")
    destination_normalized = normalize_script_name(new_name)
    source_path = script_path_for_name(source_normalized, script_dir)
    destination_path = script_path_for_name(destination_normalized, script_dir)
    if destination_path.exists() and not is_same_file(source_path, destination_path):
        raise FileExistsError(f"Script '{destination_normalized}' already exists.")
    source_path.rename(destination_path)
    return destination_path


def export_script(script_dir: Path, name: str, destination_path: Path | str) -> Path:
    """Copy a script's bytes to ``destination_path``; No Processing writes its text (F-18 D4)."""
    destination = Path(destination_path)
    refuse_folder_target(destination)
    if is_no_processing_script(name):
        # The documented content, whatever the file on disk holds.
        write_text_atomically(destination, lambda stream: stream.write(NO_PROCESSING_SCRIPT), encoding="utf-8", newline="")
        return destination
    source_path = script_path_for_name(name.strip(), script_dir)
    # An existing file there is replaced only once the copy is complete and synced.
    write_bytes_atomically(destination, lambda stream: stream.write(source_path.read_bytes()))
    return destination


def delete_script(script_dir: Path, name: str) -> None:
    normalized = name.strip()
    if is_no_processing_script(normalized):
        raise ValueError("No Processing cannot be deleted.")
    script_path_for_name(normalized, script_dir).unlink()


def resolve_selected_script(names: list[str], saved_name: str | None) -> str:
    """``saved_name`` if it is listed, else No Processing (F-18 D3)."""
    if saved_name and saved_name in names:
        return saved_name
    return NO_PROCESSING_SCRIPT_NAME
````

File: `client/text_scripts/read_problems.py`

````python
"""Whether a script can be used and, if not, why, in words the user can act on (F-18 D7).

The twin of ``dictionaries.read_problems``: an error reading the file is classified as a
dictionary's (F-6), with the plain-text advice for a file that is not UTF-8; a file that can
be read can still be not valid, when it does not compile or its ``main`` breaks the
signature rule (F-18 D5). Nothing here imports wx, and nothing runs the script.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from conversion.preprocessing.user_script import read_script_source, validate_script
from dictionaries.read_problems import DictionaryReadProblem, classify_dictionary_read_error
from i18n import _
from log import get_logger


class ScriptStatus(Enum):
	READY = "ready"
	UNREADABLE = "unreadable"
	NOT_VALID = "not_valid"


@dataclass(frozen=True)
class ScriptCheck:
	status: ScriptStatus = ScriptStatus.READY
	error: Exception | None = None  # None while the script is ready


def read_script_status(path: Path) -> ScriptCheck:
	"""Read and check the script at ``path``; an error reading it is logged, invalid code is not."""
	try:
		source = read_script_source(path)
	except Exception as error:
		log_script_read_error(path, error)
		return ScriptCheck(ScriptStatus.UNREADABLE, error)
	try:
		validate_script(source, filename=str(path))
	except Exception as error:
		# The user's code, not an error of DotExpress.
		return ScriptCheck(ScriptStatus.NOT_VALID, error)
	return ScriptCheck()


def describe_script_problem(error: Exception) -> str:
	"""Why the script cannot be used, as one or more full sentences."""
	problem = classify_dictionary_read_error(error)
	if problem is DictionaryReadProblem.NOT_UTF8:
		return _("The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.")
	if isinstance(error, SyntaxError):
		return str(error)
	if isinstance(error, ValueError):
		# A msgid of the signature rule (F-18 D5).
		return _(str(error))
	if problem is DictionaryReadProblem.CANNOT_OPEN:
		return _(
			"The file cannot be opened. It may be in use by another program, or you may not have "
			"permission to read it. Close the other program and try again."
		)
	if isinstance(error, OSError):
		return _("The file cannot be read: {error}").format(error=error)
	return str(error)


def describe_unreadable_script(name: str, error: Exception) -> str:
	"""A headline naming the script, a blank line, then the reason."""
	headline = _('Script "{name}" cannot be read.').format(name=name)
	return f"{headline}\n\n{describe_script_problem(error)}"


def log_script_read_error(path: Path, error: Exception) -> None:
	"""One line for an error that comes from the file; a traceback for anything else."""
	# Bound here, not at import, as in dictionaries.read_problems (F-6 review M-6).
	logger = get_logger("dotexpress.gui", "gui.log")
	if isinstance(error, (UnicodeDecodeError, OSError)):
		logger.error('Cannot read script "%s": %s: %s', Path(path).name, type(error).__name__, error)
	else:
		logger.error('Unexpected error while reading script "%s"', Path(path).name, exc_info=error)
````

```bash
$PY -B -X utf8 -m unittest tests.test_user_preprocessing_script tests.test_text_scripts_manager tests.test_app_paths tests.test_dictionary_manager 2>&1 | $PY $T/tools/brief.py
```

Expected (only the strings that need the catalog fail: 「不處理」, the two annotation msgids and the Edit box headline):

```text
FAIL: test_no_processing_is_shown_translated (tests.test_text_scripts_manager.ScriptActionsTest.test_no_processing_is_shown_translated)
AssertionError: 'No Processing' != '不處理'
FAIL: test_no_processing_names_are_reserved_in_any_case (tests.test_text_scripts_manager.ScriptNameTest.test_no_processing_names_are_reserved_in_any_case) (name
AssertionError: NameValidationError not raised
FAIL: test_each_problem_has_its_reason (tests.test_text_scripts_manager.ScriptStatusTest.test_each_problem_has_its_reason) (error='ValueError', reason='main 的參數
AssertionError: 'The parameter of main must be annotated as str, or not annotated.' != 'main 的參數只能標註為 str，或不加標註。'
FAIL: test_each_problem_has_its_reason (tests.test_text_scripts_manager.ScriptStatusTest.test_each_problem_has_its_reason) (error='ValueError', reason='main 的傳回
AssertionError: 'The return value of main must be annotated as str, or not annotated.' != 'main 的傳回值只能標註為 str，或不加標註。'
FAIL: test_the_edit_box_names_the_script_above_the_reason (tests.test_text_scripts_manager.ScriptStatusTest.test_the_edit_box_names_the_script_above_the_reason)
AssertionError: 'Script "upper" cannot be read.\n\n無法讀取檔案：[Errno 2] missing' != '無法讀取腳本「upper」。\n\n無法讀取檔案：[Errno 2] missing'
Ran 93 tests
FAILED (failures=5)
```

- [x] **Step 3: Regenerate the catalogs** (5 new msgids; `msgmerge` pairs three of them with old strings as fuzzy entries, which `set_msgstr.py` replaces).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
$PY -I $T/tools/set_msgstr.py locales/zh_TW/LC_MESSAGES/dotexpress.po $T/tools/f18_msgstr.tsv
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid ' locales/zh_TW/LC_MESSAGES/dotexpress.po
git -C $REPO diff --stat -- client/locales
git -C $REPO diff -- client/locales/zh_TW/LC_MESSAGES/dotexpress.po | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[-+]#: '
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (before `set_msgstr.py` 410 translated, 3 fuzzy and 2 untranslated; afterwards 415 translated):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
410 translated messages, 3 fuzzy translations, 2 untranslated messages.
msgstr set: 5, not in the file yet: 28
a second msgmerge changes nothing
msgfmt exit 0
415 translated messages.
26
 client/locales/dotexpress.pot                  |  32 +++++++++++++++++++++----
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 35341 -> 35839 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po |  32 +++++++++++++++++++++----
 3 files changed, 54 insertions(+), 10 deletions(-)
+msgid "The parameter of main must be annotated as str, or not annotated."
+msgstr "main 的參數只能標註為 str，或不加標註。"
+
+msgid "The return value of main must be annotated as str, or not annotated."
+msgstr "main 的傳回值只能標註為 str，或不加標註。"
+
+msgid "No Processing"
+msgstr "不處理"
+
+msgid "Only Python files (.py) can be imported."
+msgstr "只能匯入 Python 檔案（.py）。"
+
+#, python-brace-format
+msgid "Script \"{name}\" cannot be read."
+msgstr "無法讀取腳本「{name}」。"
+
source msgids: 415 sha256 80bf5628b545f091f8ce72e20456c6bb52e27fa04a736e3bfafced6bbebebe06
```

- [x] **Step 4: Green: the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_user_preprocessing_script tests.test_text_scripts_manager tests.test_app_paths tests.test_dictionary_manager tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 142 tests
OK
Ran 1725 tests
OK (skipped=6)
```

- [x] **Step 5: Commit.**

```bash
git -C $REPO add client/.gitignore client/app_paths.py client/conversion/preprocessing/user_script.py client/dictionaries/manager.py client/shared/file_targets.py client/text_scripts/__init__.py client/text_scripts/actions.py client/text_scripts/manager.py client/text_scripts/read_problems.py client/tests/test_app_paths.py client/tests/test_text_scripts_manager.py client/tests/test_user_preprocessing_script.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "feat: keep text-processing scripts in a script folder with a stricter signature rule (F-18)"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
 client/.gitignore                              |   1 +
 client/app_paths.py                            |   4 +-
 client/conversion/preprocessing/user_script.py |  72 ++++-
 client/dictionaries/manager.py                 |  24 +-
 client/locales/dotexpress.pot                  |  32 +-
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 35341 -> 35839 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po |  32 +-
 client/shared/file_targets.py                  |  32 ++
 client/tests/test_app_paths.py                 |  22 ++
 client/tests/test_text_scripts_manager.py      | 427 +++++++++++++++++++++++++
 client/tests/test_user_preprocessing_script.py | 151 +++++++--
 client/text_scripts/__init__.py                |   1 +
 client/text_scripts/actions.py                 |  31 ++
 client/text_scripts/manager.py                 | 157 +++++++++
 client/text_scripts/read_problems.py           |  81 +++++
 15 files changed, 994 insertions(+), 73 deletions(-)
39db6b1856c8aa24e53e931f2d101838c08f94de
```

### Task 2: Select the text-processing script in Settings and run it at conversion (D3, D4, D10)

- [x] **Step 1: Red: Test Plan E, F and the frame part of G.** `test_config.py`: `selected_script` round trip, its default, a non-string value; the setter list of the save-problem tests. `test_translation_settings.py`: load, normalize (an unlisted script becomes No Processing) and save with four keys and the first problem. `test_settings_dialogs.py`: the Translation panel's fourth row 「文字處理腳本」 lists 「不處理」 first and round-trips the internal name; the panel description; `script_names` in the dialog's arguments and owners. `test_conversion_text_pipeline.py`: `script_path=None` runs no script and still maps characters. `test_conversion_service.py`: the scripts move to a `script` folder and reach the request as `script_path`; the legacy `dictionary/preprocessing.py` is not run; a missing script fails at the text-processing stage; No Processing equals the identity script. `test_gui_document_flows.py`: `_initialize_state` patches `gui.ScriptManagementPresenter`; the request carries `None` for No Processing and `script/<name>.py` otherwise; `get_script_names_for_dialog`; `_set_active_script` and `_set_active_dictionary` keep each other's setting; the save problem is reported once for a script too; Settings gets `script_names`; the frame under one root creates `script/no-processing.py` and reads `selected_script`. New `test_text_scripts_presenter.py`: `refresh` creates No Processing, lists it first and resolves the preferred name.

Edit: `client/tests/test_config.py`

````python
        )
        self.assertEqual(self.store.get_selected_dictionary("default"), "math")

    def test_view_settings_write_braille_font_and_keep_other_sections(self) -> None:
````

````python
        )
        self.assertEqual(self.store.get_selected_dictionary("default"), "math")

    def test_selected_script_roundtrip_under_conversion_section(self) -> None:
        # F-18 (D3): next to the dictionary; No Processing until one is saved.
        self.assertEqual(config.SELECTED_SCRIPT_KEY, "selected_script")
        self.assertEqual(self.store.get_selected_script(), "no-processing")

        self.assertIsNone(self.store.set_selected_script("大寫"))

        with open(self.store.path, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f)["conversion"], {"selected_script": "大寫"})
        self.assertEqual(self.store.get_selected_script(), "大寫")

    def test_a_selected_script_that_is_not_a_string_reads_as_the_default(self) -> None:
        for value in (None, 3, ["upper"], {"name": "upper"}):
            with self.subTest(value=value):
                with open(self.store.path, "w", encoding="utf-8") as f:
                    json.dump({"conversion": {"selected_script": value}}, f)
                self.assertEqual(self.store.get_selected_script(), "no-processing")
                self.assertEqual(self.store.get_selected_script("other"), "other")

    def test_view_settings_write_braille_font_and_keep_other_sections(self) -> None:
````

Edit: `client/tests/test_config.py`

````python
        ("set_conversion_width", (52,)),
        ("set_selected_dictionary", ("alpha",)),
        ("set_translation_tables", ({"default": "zh-tw.ctb"},)),
        ("set_view_settings", (18, "dark", "default")),
````

````python
        ("set_conversion_width", (52,)),
        ("set_selected_dictionary", ("alpha",)),
        ("set_selected_script", ("upper",)),
        ("set_translation_tables", ({"default": "zh-tw.ctb"},)),
        ("set_view_settings", (18, "dark", "default")),
````

Edit: `client/tests/test_conversion_service.py`

````python
        )

    def test_empty_source_does_not_read_or_execute_preprocessing_script(self) -> None:
        dictionary_dir = self.test_dir / "dictionary"
````

````python
        )

    def _script(self, name: str, source: str) -> Path:
        # F-18 (D1): scripts live in their own folder, not next to the dictionary.
        script_dir = self.test_dir / "script"
        script_dir.mkdir(exist_ok=True)
        path = script_dir / f"{name}.py"
        path.write_text(source, encoding="utf-8")
        return path

    def test_empty_source_does_not_read_or_execute_preprocessing_script(self) -> None:
        dictionary_dir = self.test_dir / "dictionary"
````

Edit: `client/tests/test_conversion_service.py`

````python
        dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(dictionary_path, ["text", "braille", "type"], [])
        (dictionary_dir / "preprocessing.py").write_text(
            "raise RuntimeError('must not run')\ndef main(text):\n    return text\n",
            encoding="utf-8",
        )
        request = ConversionRequest(
            raw_text="",
````

````python
        dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(dictionary_path, ["text", "braille", "type"], [])
        script_path = self._script("boom", "raise RuntimeError('must not run')\ndef main(text):\n    return text\n")
        request = ConversionRequest(
            raw_text="",
````

Edit: `client/tests/test_conversion_service.py`

````python
            translation_tables={"default": "table.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        output = convert_text_with_alignment(request, runtime=self._runtime())
````

````python
            translation_tables={"default": "table.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
            script_path=script_path,
        )

        output = convert_text_with_alignment(request, runtime=self._runtime())
````

Edit: `client/tests/test_conversion_service.py`

````python
        dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(dictionary_path, ["text", "braille", "type"], [])
        (dictionary_dir / "preprocessing.py").write_text(
            "def main(text):\n    return text.replace('raw', 'processed')\n",
            encoding="utf-8",
        )
        request = ConversionRequest(
            raw_text="raw",
````

````python
        dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(dictionary_path, ["text", "braille", "type"], [])
        script_path = self._script("processed", "def main(text):\n    return text.replace('raw', 'processed')\n")
        request = ConversionRequest(
            raw_text="raw",
````

Edit: `client/tests/test_conversion_service.py`

````python
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        runtime = self._runtime()
````

````python
            lang=LANG,
            charset_maps=CHARSET_MAPS,
            script_path=script_path,
        )
        runtime = self._runtime()
````

Edit: `client/tests/test_conversion_service.py`

````python
        dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(dictionary_path, ["text", "braille", "type"], [])
        (dictionary_dir / "preprocessing.py").write_text(
            "def main(text):\n    raise RuntimeError('script boom')\n",
            encoding="utf-8",
        )
        request = ConversionRequest(
            raw_text="raw",
````

````python
        dictionary_path = dictionary_dir / "default.csv"
        self._write_csv(dictionary_path, ["text", "braille", "type"], [])
        script_path = self._script("boom", "def main(text):\n    raise RuntimeError('script boom')\n")
        request = ConversionRequest(
            raw_text="raw",
````

Edit: `client/tests/test_conversion_service.py`

````python
            translation_tables={"default": "table.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )

        with self.assertRaises(ConversionStageError) as context:
````

````python
            translation_tables={"default": "table.ctb"},
            lang=LANG,
            charset_maps=CHARSET_MAPS,
            script_path=script_path,
        )

        with self.assertRaises(ConversionStageError) as context:
````

Edit: `client/tests/test_conversion_service.py`

````python
        self.dictionary_dir.mkdir()
        self.dictionary_path = self.dictionary_dir / "default.csv"

    def _convert(self, raw_text: str, runtime: TranslationRuntime) -> ConversionOutput:
        request = ConversionRequest(
            raw_text=raw_text,
````

````python
        self.dictionary_dir.mkdir()
        self.dictionary_path = self.dictionary_dir / "default.csv"
        self.script_dir = self.test_dir / "script"
        self.script_dir.mkdir()

    def _convert(self, raw_text: str, runtime: TranslationRuntime, script_path: Path | None = None) -> ConversionOutput:
        request = ConversionRequest(
            raw_text=raw_text,
````

Edit: `client/tests/test_conversion_service.py`

````python
            lang=LANG,
            charset_maps=CHARSET_MAPS,
        )
        return convert_text_with_alignment(request, runtime=runtime)
````

````python
            lang=LANG,
            charset_maps=CHARSET_MAPS,
            script_path=script_path,
        )
        return convert_text_with_alignment(request, runtime=runtime)
````

Edit: `client/tests/test_conversion_service.py`

````python
    def test_failing_preprocessing_script_is_reported_before_a_broken_dictionary(self) -> None:
        self.dictionary_path.write_text("", encoding="utf-8")
        (self.dictionary_dir / "preprocessing.py").write_text(
            "def main(text):\n    raise RuntimeError('script boom')\n",
            encoding="utf-8",
````

````python
    def test_failing_preprocessing_script_is_reported_before_a_broken_dictionary(self) -> None:
        self.dictionary_path.write_text("", encoding="utf-8")
        script_path = self.script_dir / "boom.py"
        script_path.write_text(
            "def main(text):\n    raise RuntimeError('script boom')\n",
            encoding="utf-8",
````

Edit: `client/tests/test_conversion_service.py`

````python

        with self.assertRaises(ConversionStageError) as context:
            self._convert("abc", self._runtime())

        self.assertEqual(context.exception.stage, "text_processing")
````

````python

        with self.assertRaises(ConversionStageError) as context:
            self._convert("abc", self._runtime(), script_path)

        self.assertEqual(context.exception.stage, "text_processing")
````

Edit: `client/tests/test_conversion_service.py`

````python
        for source, message in cases:
            with self.subTest(source=source):
                (self.dictionary_dir / "preprocessing.py").write_text(source, encoding="utf-8")

                with self.assertRaises(ConversionStageError) as context:
                    self._convert("abc", self._runtime())

                self.assertEqual(format_conversion_error(context.exception), message)

    def test_math_before_the_first_text_is_translated_before_the_dictionary_error(self) -> None:
````

````python
        for source, message in cases:
            with self.subTest(source=source):
                script_path = self.script_dir / "contract.py"
                script_path.write_text(source, encoding="utf-8")

                with self.assertRaises(ConversionStageError) as context:
                    self._convert("abc", self._runtime(), script_path)

                self.assertEqual(format_conversion_error(context.exception), message)

    def test_the_legacy_script_next_to_the_dictionary_is_not_run(self) -> None:
        # F-18 (D-A, D12): dictionary/preprocessing.py is no longer read.
        self.dictionary_path.write_text("text,braille,type\n", encoding="utf-8")
        legacy = self.dictionary_dir / "preprocessing.py"
        legacy.write_text("def main(text):\n    raise RuntimeError('must not run')\n", encoding="utf-8")
        runtime = self._runtime()

        self._convert("abc", runtime)

        self.assertEqual(runtime.text_translator.calls, [("abc", "zh-tw.ctb", "abc", False)])
        self.assertEqual(legacy.read_text(encoding="utf-8"), "def main(text):\n    raise RuntimeError('must not run')\n")

    def test_a_selected_script_that_is_missing_fails_at_the_text_processing_stage(self) -> None:
        # F-18 (D10, O8): no identity fallback; the existing text-processing box.
        self.dictionary_path.write_text("text,braille,type\n", encoding="utf-8")
        missing = self.script_dir / "gone.py"

        with self.assertRaises(ConversionStageError) as context:
            self._convert("abc", self._runtime(), missing)

        self.assertEqual(context.exception.stage, "text_processing")
        self.assertIsInstance(context.exception.error, FileNotFoundError)
        self.assertEqual(
            format_conversion_error(context.exception),
            f"文字處理失敗：[Errno 2] No such file or directory: {str(missing)!r}",
        )

    def test_no_processing_gives_the_output_of_the_identity_script(self) -> None:
        # F-18 (D4): skipping the stage changes nothing, so the fixtures keep their bytes.
        self.dictionary_path.write_text("text,braille,type\n甲,X,Braille\n", encoding="utf-8")
        identity = self.script_dir / "identity.py"
        identity.write_text("def main(input: str) -> str:\n    return input\n", encoding="utf-8")

        skipped = self._convert("甲 abc $x$", self._runtime())
        run = self._convert("甲 abc $x$", self._runtime(), identity)

        self.assertEqual(skipped, run)

    def test_math_before_the_first_text_is_translated_before_the_dictionary_error(self) -> None:
````

Edit: `client/tests/test_conversion_text_pipeline.py`

````python
                "B",
                data_dir=data_dir,
                preprocessing_path=directory / "preprocessing.py",
                execute_script=execute_script,
                map_char=map_char,
````

````python
                "B",
                data_dir=data_dir,
                script_path=directory / "upper.py",
                execute_script=execute_script,
                map_char=map_char,
````

Edit: `client/tests/test_conversion_text_pipeline.py`

````python
                events,
                [
                    ("script", directory / "preprocessing.py", "B"),
                    ("map", "ㄅ"),
                ],
            )

    def test_preprocess_source_text_preserves_script_exception(self) -> None:
````

````python
                events,
                [
                    ("script", directory / "upper.py", "B"),
                    ("map", "ㄅ"),
                ],
            )

    def test_no_processing_runs_no_script_and_still_maps_characters(self) -> None:
        # F-18 (D4): script_path None is No Processing.
        def execute_script(_path: Path, _text: str) -> str:
            raise AssertionError("No Processing must not run a script")

        events = []

        def map_char(text: str, **kwargs) -> str:
            events.append(("map", text, kwargs["dictionary_path"]))
            return "mapped"

        result = preprocess_source_text(
            "B",
            data_dir=Path("data"),
            script_path=None,
            execute_script=execute_script,
            map_char=map_char,
        )

        self.assertEqual(result, "mapped")
        self.assertEqual(events, [("map", "B", Path("data") / "BopomofoChar2Braille.csv")])

    def test_preprocess_source_text_preserves_script_exception(self) -> None:
````

Edit: `client/tests/test_conversion_text_pipeline.py`

````python
        with self.assertRaises(TextProcessingError) as context:
            preprocess_source_text(
                "source",
                data_dir=Path("data"),
                preprocessing_path=Path("dictionary/preprocessing.py"),
                execute_script=execute_script,
            )

        self.assertIs(context.exception.error, error)
````

````python
        with self.assertRaises(TextProcessingError) as context:
            preprocess_source_text(
                "source",
                data_dir=Path("data"),
                script_path=Path("script/upper.py"),
                execute_script=execute_script,
            )

        self.assertIs(context.exception.error, error)
````

Edit: `client/tests/test_conversion_text_pipeline.py`

````python
                "source",
                data_dir=Path("data"),
                preprocessing_path=Path("dictionary/preprocessing.py"),
                execute_script=execute_script,
            )
````

````python
                "source",
                data_dir=Path("data"),
                script_path=Path("script/upper.py"),
                execute_script=execute_script,
            )
````

Edit: `client/tests/test_conversion_text_pipeline.py`

````python
            dictionary_dir.mkdir()
            dictionary_path = self._write_csv(dictionary_dir, "default.csv", ["text", "braille", "type"], [])
            (dictionary_dir / "preprocessing.py").write_text(
                "def main(text):\n    return text.replace('raw', 'processed')\n",
                encoding="utf-8",
````

````python
            dictionary_dir.mkdir()
            dictionary_path = self._write_csv(dictionary_dir, "default.csv", ["text", "braille", "type"], [])
            script_path = directory / "script" / "processed.py"
            script_path.parent.mkdir()
            script_path.write_text(
                "def main(text):\n    return text.replace('raw', 'processed')\n",
                encoding="utf-8",
````

Edit: `client/tests/test_conversion_text_pipeline.py`

````python
                translation_tables={"default": "table.ctb"},
                lang="en",
                charset_maps=dict(DEFAULT_CHARSET_MAPS),
            )

            translated_texts = []
````

````python
                translation_tables={"default": "table.ctb"},
                lang="en",
                charset_maps=dict(DEFAULT_CHARSET_MAPS),
                script_path=script_path,
            )

            translated_texts = []
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        frame._paths = make_paths(dictionary=Path("dictionary"), workspace=Path("workspace"))
        frame._config_store = Mock(spec=gui.ConfigStore)
        with (
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
            patch.object(gui, "load_translation_tables", return_value={}),
        ):
````

````python
        frame._paths = make_paths(dictionary=Path("dictionary"), workspace=Path("workspace"))
        frame._config_store = Mock(spec=gui.ConfigStore)
        with (
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(gui, "ScriptManagementPresenter", return_value=Mock(script_names=["no-processing"])),
            patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
            patch.object(gui, "load_translation_tables", return_value={}),
        ):
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        with (
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
````

````python
        with (
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(gui, "ScriptManagementPresenter", return_value=Mock(script_names=["no-processing"])),
            patch.object(gui, "load_translation_settings", return_value=TranslationSettings("unicode", 40, "default")),
            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default", "math"])
        snapshot = make_snapshot(
            translation=TranslationSettings("ascii", 52, "math"),
            tables={"default": "en-ueb-g1.ctb", "math": "Nemeth"},
            view=ViewSettings(18, "dark", "default"),
````

````python
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default", "math"])
        frame.get_script_names_for_dialog = Mock(return_value=["no-processing", "upper"])
        snapshot = make_snapshot(
            translation=TranslationSettings("ascii", 52, "math", "upper"),
            tables={"default": "en-ueb-g1.ctb", "math": "Nemeth"},
            view=ViewSettings(18, "dark", "default"),
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        with (
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(
                gui,
````

````python
        with (
            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
            patch.object(gui, "ScriptManagementPresenter", return_value=Mock(script_names=["no-processing"])),
            patch.object(
                gui,
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        frame.view_settings = ViewSettings(40, "light", "default")
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        frame.translation_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}

````

````python
        frame.view_settings = ViewSettings(40, "light", "default")
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        frame.get_script_names_for_dialog = Mock(return_value=["no-processing", "upper"])
        frame.translation_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}

````

Edit: `client/tests/test_gui_document_flows.py`

````python
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        snapshot = make_snapshot(tables={"default": "test-default.ctb", "math": "test-math.ctb"})

````

````python
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        frame.get_script_names_for_dialog = Mock(return_value=["no-processing", "upper"])
        snapshot = make_snapshot(tables={"default": "test-default.ctb", "math": "test-math.ctb"})

````

Edit: `client/tests/test_gui_document_flows.py`

````python
        frame.get_settings_snapshot = Mock(return_value=make_snapshot())
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        frame.apply_settings_from_dialog = Mock()

````

````python
        frame.get_settings_snapshot = Mock(return_value=make_snapshot())
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        frame.get_script_names_for_dialog = Mock(return_value=["no-processing", "upper"])
        frame.apply_settings_from_dialog = Mock()

````

Edit: `client/tests/test_gui_document_flows.py`

````python
        show.assert_called_once()
        self.assertIs(show.call_args.kwargs["initial_category"], TranslationSettingsPanel)


````

````python
        show.assert_called_once()
        self.assertIs(show.call_args.kwargs["initial_category"], TranslationSettingsPanel)
        # F-18 (D3): the Translation panel lists the scripts.
        self.assertEqual(show.call_args.kwargs["script_names"], ["no-processing", "upper"])


class ScriptSelectionFrameTest(unittest.TestCase):
    """F-18 (D3, D10): the selected script reaches the conversion request; No Processing is None."""

    def _make_frame(self, script: str = "no-processing") -> gui.BrailleFrame:
        frame = object.__new__(gui.BrailleFrame)
        frame.translation_settings = TranslationSettings("unicode", 40, "default", script)
        frame._script_presenter = Mock()
        frame._config_store = Mock(spec=gui.ConfigStore)
        frame._config_store.set_selected_script.return_value = None
        frame._config_store.get_lang.return_value = "zh_TW"
        frame._config_store.get_charset_maps.return_value = {}
        frame.dictionary_dir = Path("dictionaries")
        frame.script_dir = Path("scripts")
        frame.translation_tables = {"default": "zh-tw.ctb"}
        return frame

    def test_no_processing_sends_no_script(self) -> None:
        for name in ("no-processing", "No-Processing"):
            with self.subTest(name=name):
                frame = self._make_frame(name)

                self.assertIsNone(frame._get_selected_script_path())
                self.assertIsNone(frame._build_conversion_request_for_text("text").script_path)

    def test_a_user_script_is_sent_by_its_path_in_the_script_folder(self) -> None:
        frame = self._make_frame("upper")

        request = frame._build_conversion_request_for_text("text")

        self.assertEqual(request.script_path, Path("scripts/upper.py"))
        self.assertEqual(request.dictionary_path, Path("dictionaries/default.csv"))

    def test_script_names_for_dialog_refresh_with_the_active_script(self) -> None:
        frame = self._make_frame("upper")
        frame._script_presenter.script_names = ["no-processing", "upper"]

        names = frame.get_script_names_for_dialog()

        self.assertEqual(names, ["no-processing", "upper"])
        frame._script_presenter.refresh.assert_called_once_with("upper")

    def test_set_active_script_saves_it_and_keeps_the_other_settings(self) -> None:
        frame = self._make_frame("upper")
        frame.translation_settings = TranslationSettings("ascii", 52, "math", "upper")

        frame._set_active_script("no-processing")

        self.assertEqual(frame.translation_settings, TranslationSettings("ascii", 52, "math", "no-processing"))
        frame._config_store.set_selected_script.assert_called_once_with("no-processing")


````

Edit: `client/tests/test_gui_document_flows.py`

````python
            frame._config_store.set_selected_dictionary.return_value = None
            with (
                patch.object(
                    gui,
````

````python
            frame._config_store.set_selected_dictionary.return_value = None
            with (
                patch.object(gui, "ScriptManagementPresenter", return_value=Mock(script_names=["no-processing"])),
                patch.object(
                    gui,
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        self.assertIsInstance(presenter, gui.DictionaryManagementPresenter)
        self.assertEqual(presenter.dictionary_dir, dictionary_dir)
        load_settings.assert_called_once_with(frame._config_store, ["alpha", "default"])
        self.assertEqual(selected, "default")
        self.assertEqual(remaining, ["default.csv"])
        frame._config_store.set_selected_dictionary.assert_called_once_with("default")
        self.assertEqual(frame.translation_settings, TranslationSettings("unicode", 40, "default"))

    def test_frame_dictionary_callbacks_are_removed(self) -> None:
````

````python
        self.assertIsInstance(presenter, gui.DictionaryManagementPresenter)
        self.assertEqual(presenter.dictionary_dir, dictionary_dir)
        load_settings.assert_called_once_with(frame._config_store, ["alpha", "default"], ["no-processing"])
        self.assertEqual(selected, "default")
        self.assertEqual(remaining, ["default.csv"])
        frame._config_store.set_selected_dictionary.assert_called_once_with("default")
        self.assertEqual(frame.translation_settings, TranslationSettings("unicode", 40, "default"))

    def test_set_active_dictionary_keeps_the_selected_script(self) -> None:
        # F-18 (D3): the dictionary twin must not drop the script.
        frame = self._make_frame()
        frame.translation_settings = TranslationSettings("ascii", 52, "default", "upper")
        frame._config_store = Mock(spec=gui.ConfigStore)
        frame._config_store.set_selected_dictionary.return_value = None

        frame._set_active_dictionary("math")

        self.assertEqual(frame.translation_settings, TranslationSettings("ascii", 52, "math", "upper"))

    def test_frame_dictionary_callbacks_are_removed(self) -> None:
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default", "math"])
        frame.translation_settings = TranslationSettings("unicode", 40, "default")
        frame.view_settings = ViewSettings(12, "light", "default")
````

````python
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default", "math"])
        frame.get_script_names_for_dialog = Mock(return_value=["no-processing", "upper"])
        frame.translation_settings = TranslationSettings("unicode", 40, "default")
        frame.view_settings = ViewSettings(12, "light", "default")
````

Edit: `client/tests/test_gui_document_flows.py`

````python
    def test_font_size_and_dictionary_changes_report_through_the_same_flag(self) -> None:
        self.config_path.mkdir()
        for first, second in (("font", "dictionary"), ("dictionary", "font")):
            with self.subTest(first=first):
                self.boxes.clear()
                frame = self._frame()
````

````python
    def test_font_size_and_dictionary_changes_report_through_the_same_flag(self) -> None:
        self.config_path.mkdir()
        for first, second in (("font", "dictionary"), ("dictionary", "font"), ("script", "dictionary"), ("font", "script")):
            with self.subTest(first=first, second=second):
                self.boxes.clear()
                frame = self._frame()
````

Edit: `client/tests/test_gui_document_flows.py`

````python
                    "font": lambda: frame._set_view_font_size(20),
                    "dictionary": lambda: frame._set_active_dictionary("math"),
                }

````

````python
                    "font": lambda: frame._set_view_font_size(20),
                    "dictionary": lambda: frame._set_active_dictionary("math"),
                    "script": lambda: frame._set_active_script("upper"),
                }

````

Edit: `client/tests/test_gui_document_flows.py`

````python
                self.assertEqual(after_first, [self._box(frame, self.CANNOT_OPEN)])
                self.assertEqual(self.boxes, after_first)
                self.assertEqual(frame.view_settings.font_size, 20)
                self.assertEqual(frame.translation_settings.selected_dictionary, "math")

    def test_no_box_when_the_settings_are_saved(self) -> None:
        frame = self._frame()

        frame.apply_settings_from_dialog(make_snapshot(translation=TranslationSettings("ascii", 52, "math")))
        frame._set_view_font_size(20)
        frame._set_active_dictionary("default")
````

````python
                self.assertEqual(after_first, [self._box(frame, self.CANNOT_OPEN)])
                self.assertEqual(self.boxes, after_first)
                if "font" in (first, second):
                    self.assertEqual(frame.view_settings.font_size, 20)
                if "dictionary" in (first, second):
                    self.assertEqual(frame.translation_settings.selected_dictionary, "math")
                if "script" in (first, second):
                    self.assertEqual(frame.translation_settings.selected_script, "upper")

    def test_no_box_when_the_settings_are_saved(self) -> None:
        frame = self._frame()

        frame.apply_settings_from_dialog(make_snapshot(translation=TranslationSettings("ascii", 52, "math", "upper")))
        frame._set_view_font_size(20)
        frame._set_active_dictionary("default")
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        saved = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["conversion"]["output_mode"], "ascii")
        self.assertEqual(saved["view"]["font_size"], 20)

````

````python
        saved = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["conversion"]["output_mode"], "ascii")
        self.assertEqual(saved["conversion"]["selected_script"], "upper")
        self.assertEqual(saved["view"]["font_size"], 20)

````

Edit: `client/tests/test_gui_document_flows.py`

````python
                    "width": 52,
                    "selected_dictionary": "alpha",
                    "translation_tables": {"default": "en-ueb-g1.ctb"},
                },
````

````python
                    "width": 52,
                    "selected_dictionary": "alpha",
                    "selected_script": "upper",
                    "translation_tables": {"default": "en-ueb-g1.ctb"},
                },
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        (self.root / "dictionary").mkdir()
        (self.root / "dictionary" / "alpha.csv").write_text("text,braille,type\n", encoding="utf-8")
        frame = self.make_frame()
        frame._document_controller = DocumentController()
````

````python
        (self.root / "dictionary").mkdir()
        (self.root / "dictionary" / "alpha.csv").write_text("text,braille,type\n", encoding="utf-8")
        (self.root / "script").mkdir()
        (self.root / "script" / "upper.py").write_text("def main(text):\n    return text.upper()\n", encoding="utf-8")
        frame = self.make_frame()
        frame._document_controller = DocumentController()
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        self.assertTrue((self.root / "dictionary" / "default.csv").is_file())
        self.assertEqual(frame._workspace_service.workspace_dir, self.root / "workspace")
        self.assertEqual(frame.translation_settings, TranslationSettings("ascii", 52, "alpha"))
        self.assertEqual(frame.translation_tables, {**gui.DEFAULT_TRANSLATION_TABLES, "default": "en-ueb-g1.ctb"})
        self.assertEqual(view, ViewSettings(18, "dark", "default"))
        self.assertIs(frame.view_settings, view)
        self.assertEqual(self.root_entries(), ["config.json", "dictionary"])

    def test_selecting_a_dictionary_writes_the_config_file_under_the_root(self) -> None:
````

````python
        self.assertTrue((self.root / "dictionary" / "default.csv").is_file())
        self.assertEqual(frame._workspace_service.workspace_dir, self.root / "workspace")
        # F-18 (D1, D3): the script folder is under the root too; No Processing is created there.
        self.assertEqual(frame.script_dir, self.root / "script")
        self.assertEqual(frame._script_presenter.script_dir, self.root / "script")
        self.assertEqual(sorted(path.name for path in (self.root / "script").iterdir()), ["no-processing.py", "upper.py"])
        self.assertEqual(frame.translation_settings, TranslationSettings("ascii", 52, "alpha", "upper"))
        self.assertEqual(frame.translation_tables, {**gui.DEFAULT_TRANSLATION_TABLES, "default": "en-ueb-g1.ctb"})
        self.assertEqual(view, ViewSettings(18, "dark", "default"))
        self.assertIs(frame.view_settings, view)
        self.assertEqual(self.root_entries(), ["config.json", "dictionary", "script"])

    def test_selecting_a_dictionary_writes_the_config_file_under_the_root(self) -> None:
````

Edit: `client/tests/test_settings_dialogs.py`

````python
        panel.dictionary_choice = FakeChoice(1)
        panel.dictionary_names = ["default", "math"]

        result = panel.on_save(baseline)

        self.assertEqual(result.translation, TranslationSettings("ascii", 52, "math"))
        self.assertEqual(baseline.translation, TranslationSettings("unicode", 40, "default"))

````

````python
        panel.dictionary_choice = FakeChoice(1)
        panel.dictionary_names = ["default", "math"]
        panel.script_choice = FakeChoice(1)
        panel.script_names = ["no-processing", "upper"]

        result = panel.on_save(baseline)

        self.assertEqual(result.translation, TranslationSettings("ascii", 52, "math", "upper"))
        self.assertEqual(baseline.translation, TranslationSettings("unicode", 40, "default"))

````

Edit: `client/tests/test_settings_dialogs.py`

````python
                snapshot=make_snapshot(),
                dictionary_names=["default"],
                commit=Mock(),
            )
````

````python
                snapshot=make_snapshot(),
                dictionary_names=["default"],
                script_names=["no-processing"],
                commit=Mock(),
            )
````

Edit: `client/tests/test_settings_dialogs.py`

````python
    PANELS = {
        "TranslationSettingsPanel": (
            ("轉譯", "轉譯輸出模式、寬度與字典選項"),
            ("Translation", "Translation output mode, width, and dictionary options"),
        ),
        "TranslationTablesPanel": (
````

````python
    PANELS = {
        "TranslationSettingsPanel": (
            ("轉譯", "轉譯輸出模式、寬度、字典與文字處理腳本選項"),
            ("Translation", "Translation output mode, width, dictionary, and text processing script options"),
        ),
        "TranslationTablesPanel": (
````

Edit: `client/tests/test_settings_dialogs.py`

````python
            "snapshot": self.snapshot,
            "dictionary_names": ["default", "math"],
            "commit": self.commit,
        }
````

````python
            "snapshot": self.snapshot,
            "dictionary_names": ["default", "math"],
            "script_names": ["no-processing", "upper"],
            "commit": self.commit,
        }
````

Edit: `client/tests/test_settings_dialogs.py`

````python
            view=view,
        )
        owner = SimpleNamespace(snapshot=snapshot, dictionary_names=["default", "math"])
    with (
        patch.multiple(module.wx, Choice=RecordingChoice, SpinCtrl=RecordingSpin),
````

````python
            view=view,
        )
        owner = SimpleNamespace(snapshot=snapshot, dictionary_names=["default", "math"], script_names=["no-processing", "upper"])
    with (
        patch.multiple(module.wx, Choice=RecordingChoice, SpinCtrl=RecordingSpin),
````

Edit: `client/tests/test_settings_dialogs.py`

````python

        rows = grid_rows(panel)
        self.assertEqual([label for label, _control in rows], ["點字類型", "寬度", "字典"])
        self.assertEqual([control for _label, control in rows], [panel.output_choice, panel.width_spin, panel.dictionary_choice])
        self.assertEqual(panel.output_choice.items, ["Unicode", "ASCII"])
        self.assertEqual(panel.output_choice.items, [i18n._("Unicode"), i18n._("ASCII")])
````

````python

        rows = grid_rows(panel)
        self.assertEqual([label for label, _control in rows], ["點字類型", "寬度", "字典", "文字處理腳本"])
        self.assertEqual(
            [control for _label, control in rows],
            [panel.output_choice, panel.width_spin, panel.dictionary_choice, panel.script_choice],
        )
        self.assertEqual(panel.output_choice.items, ["Unicode", "ASCII"])
        self.assertEqual(panel.output_choice.items, [i18n._("Unicode"), i18n._("ASCII")])
````

Edit: `client/tests/test_settings_dialogs.py`

````python
        panel.load_snapshot(translation_snapshot("unicode", 64))
        self.assertEqual((panel.output_choice.selection, panel.width_spin.value), (0, 64))


````

````python
        panel.load_snapshot(translation_snapshot("unicode", 64))
        self.assertEqual((panel.output_choice.selection, panel.width_spin.value), (0, 64))


class TranslationPanelScriptChoiceTest(unittest.TestCase):
    """F-18 (D3): the text-processing script is chosen below the dictionary."""

    def build(self, script_names, selected):
        snapshot = DotExpressSettingsSnapshot.create(
            translation=TranslationSettings("unicode", 40, "default", selected),
            translation_tables={},
            view=ViewSettings(12, "light", "simbraille"),
        )
        owner = SimpleNamespace(snapshot=snapshot, dictionary_names=["default"], script_names=script_names)
        return build_panel("TranslationSettingsPanel", owner=owner)

    def test_no_processing_is_listed_first_by_its_display_name(self) -> None:
        panel = self.build(["no-processing", "upper", "中文"], "upper")

        self.assertEqual(panel.script_choice.items, ["不處理", "upper", "中文"])
        self.assertEqual(panel.script_choice.selection, 1)
        self.assertEqual(panel.script_names, ["no-processing", "upper", "中文"])

    def test_the_choice_round_trips_the_internal_name(self) -> None:
        panel = self.build(["no-processing", "upper"], "no-processing")
        baseline = translation_snapshot()
        for selection, expected in ((0, "no-processing"), (1, "upper"), (-1, "no-processing"), (2, "no-processing")):
            with self.subTest(selection=selection):
                panel.script_choice.SetSelection(selection)
                self.assertEqual(panel.on_save(baseline).translation.selected_script, expected)

    def test_an_unknown_name_selects_no_processing_and_a_new_snapshot_reselects(self) -> None:
        panel = self.build(["no-processing", "upper"], "missing")
        self.assertEqual(panel.script_choice.selection, 0)

        panel.load_snapshot(
            DotExpressSettingsSnapshot.create(
                translation=TranslationSettings("unicode", 40, "default", "upper"),
                translation_tables={},
                view=ViewSettings(12, "light", "simbraille"),
            )
        )
        self.assertEqual(panel.script_choice.selection, 1)

    def test_no_script_names_disable_the_choice(self) -> None:
        panel = self.build([], "no-processing")

        self.assertEqual((panel.script_choice.selection, panel.script_choice.enabled), (-1, False))
        self.assertEqual(panel.on_save(translation_snapshot()).translation.selected_script, "no-processing")


````

File: `client/tests/test_text_scripts_presenter.py`

````python
"""Script Management without wx (F-18): ``text_scripts.presenter.ScriptManagementPresenter``."""

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import text_scripts.presenter as presenter_module
from text_scripts.presenter import ScriptManagementPresenter

PRESENTER_PATH = Path(presenter_module.__file__)
UPPER = "def main(text: str) -> str:\n    return text.upper()\n"


class PresenterTestCase(unittest.TestCase):
	def setUp(self):
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.root = Path(temp_dir.name)
		self.script_dir = self.root / "script"
		self.active = ["no-processing"]
		self.set_active_name = Mock(side_effect=lambda name: self.active.__setitem__(0, name))

	def write_script(self, name, source=UPPER):
		self.script_dir.mkdir(parents=True, exist_ok=True)
		path = self.script_dir / f"{name}.py"
		path.write_text(source, encoding="utf-8")
		return path

	def make_presenter(self, *names, active="no-processing"):
		for name in names:
			self.write_script(name)
		self.active[0] = active
		presenter = ScriptManagementPresenter(
			self.script_dir,
			get_active_name=lambda: self.active[0],
			set_active_name=self.set_active_name,
		)
		presenter.refresh(active)
		return presenter

	def files(self):
		return sorted(path.name for path in self.script_dir.iterdir())


class PresenterModuleTest(unittest.TestCase):
	def test_presenter_module_does_not_import_wx(self):
		tree = ast.parse(PRESENTER_PATH.read_text(encoding="utf-8"))
		imported = set()
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				imported.update(alias.name.split(".")[0] for alias in node.names)
			elif isinstance(node, ast.ImportFrom) and node.module:
				imported.add(node.module.split(".")[0])

		self.assertNotIn("wx", imported)


class PresenterRefreshTest(PresenterTestCase):
	def test_constructor_does_no_io(self):
		ScriptManagementPresenter(self.script_dir, get_active_name=lambda: "no-processing", set_active_name=Mock())

		self.assertFalse(self.script_dir.exists())

	def test_refresh_creates_no_processing_and_lists_it_first(self):
		self.write_script("zeta")
		self.write_script("Alpha")
		presenter = ScriptManagementPresenter(self.script_dir, get_active_name=lambda: "no-processing", set_active_name=Mock())

		selected = presenter.refresh()

		self.assertEqual(selected, "no-processing")
		self.assertEqual(presenter.script_names, ["no-processing", "Alpha", "zeta"])
		self.assertEqual(self.files(), ["Alpha.py", "no-processing.py", "zeta.py"])
		self.assertEqual(presenter.script_dir, self.script_dir)

	def test_refresh_selects_the_preferred_name_if_listed(self):
		presenter = self.make_presenter("upper")

		self.assertEqual(presenter.refresh("upper"), "upper")
		self.assertEqual(presenter.refresh("gone"), "no-processing")

	def test_the_names_are_a_copy_and_a_name_maps_to_its_file(self):
		presenter = self.make_presenter("upper")

		presenter.script_names.append("other")

		self.assertEqual(presenter.script_names, ["no-processing", "upper"])
		self.assertEqual(presenter.script_path("upper"), self.script_dir / "upper.py")
		self.set_active_name.assert_not_called()


if __name__ == "__main__":
	unittest.main()
````

Edit: `client/tests/test_translation_settings.py`

````python
        store.set_conversion_width.return_value = first
        store.set_selected_dictionary.return_value = second

        problem = save_translation_settings(store, TranslationSettings("ascii", 52, "alpha"))

        self.assertIs(problem, first)
````

````python
        store.set_conversion_width.return_value = first
        store.set_selected_dictionary.return_value = second
        store.set_selected_script.return_value = None

        problem = save_translation_settings(store, TranslationSettings("ascii", 52, "alpha", "upper"))

        self.assertIs(problem, first)
````

Edit: `client/tests/test_translation_settings.py`

````python
        store.set_conversion_width.assert_called_once_with(52)
        store.set_selected_dictionary.assert_called_once_with("alpha")

    def test_save_returns_none_when_every_setter_saves(self) -> None:
````

````python
        store.set_conversion_width.assert_called_once_with(52)
        store.set_selected_dictionary.assert_called_once_with("alpha")
        store.set_selected_script.assert_called_once_with("upper")

    def test_save_returns_the_script_problem_when_it_is_the_only_one(self) -> None:
        # F-18 (D3): the fourth setting is saved and reported like the others.
        store = Mock(spec=config.ConfigStore)
        problem = object()
        store.set_output_mode.return_value = None
        store.set_conversion_width.return_value = None
        store.set_selected_dictionary.return_value = None
        store.set_selected_script.return_value = problem

        self.assertIs(save_translation_settings(store, TranslationSettings("ascii", 52, "alpha")), problem)
        store.set_selected_script.assert_called_once_with("no-processing")

    def test_save_returns_none_when_every_setter_saves(self) -> None:
````

Edit: `client/tests/test_translation_settings.py`

````python
                config.WIDTH_KEY: 999,
                config.SELECTED_DICTIONARY_KEY: "missing",
            }
        )

        settings = load_translation_settings(self.store, ["default", "math"])

        self.assertEqual(
````

````python
                config.WIDTH_KEY: 999,
                config.SELECTED_DICTIONARY_KEY: "missing",
                config.SELECTED_SCRIPT_KEY: "gone",
            }
        )

        settings = load_translation_settings(self.store, ["default", "math"], ["no-processing", "upper"])

        self.assertEqual(
````

Edit: `client/tests/test_translation_settings.py`

````python
                width=200,
                selected_dictionary="default",
            ),
        )
````

````python
                width=200,
                selected_dictionary="default",
                selected_script="no-processing",
            ),
        )
````

Edit: `client/tests/test_translation_settings.py`

````python
                config.WIDTH_KEY: 52,
                config.SELECTED_DICTIONARY_KEY: "math",
            }
        )

        self.assertEqual(
            load_translation_settings(self.store, ["default", "math"]),
            TranslationSettings("ascii", 52, "math"),
        )

    def test_save_persists_one_complete_settings_value(self) -> None:
        settings = TranslationSettings("ascii", 64, "math")

        save_translation_settings(self.store, settings)
````

````python
                config.WIDTH_KEY: 52,
                config.SELECTED_DICTIONARY_KEY: "math",
                config.SELECTED_SCRIPT_KEY: "upper",
            }
        )

        self.assertEqual(
            load_translation_settings(self.store, ["default", "math"], ["no-processing", "upper"]),
            TranslationSettings("ascii", 52, "math", "upper"),
        )

    def test_a_config_without_a_script_selects_no_processing(self) -> None:
        # F-18 (D-A): every user starts with No Processing.
        self._write_config({config.SELECTED_DICTIONARY_KEY: "math"})

        self.assertEqual(
            load_translation_settings(self.store, ["default", "math"], ["no-processing", "upper"]).selected_script,
            "no-processing",
        )
        self.assertEqual(DEFAULT_TRANSLATION_SETTINGS.selected_script, "no-processing")
        self.assertEqual(TranslationSettings("unicode", 40, "default").selected_script, "no-processing")

    def test_save_persists_one_complete_settings_value(self) -> None:
        settings = TranslationSettings("ascii", 64, "math", "upper")

        save_translation_settings(self.store, settings)
````

Edit: `client/tests/test_translation_settings.py`

````python
                        config.WIDTH_KEY: 64,
                        config.SELECTED_DICTIONARY_KEY: "math",
                    },
                },
````

````python
                        config.WIDTH_KEY: 64,
                        config.SELECTED_DICTIONARY_KEY: "math",
                        config.SELECTED_SCRIPT_KEY: "upper",
                    },
                },
````

Edit: `client/tests/test_translation_settings.py`

````python
            TranslationSettings(output_mode, width, "default"),
            ["default"],
        )

````

````python
            TranslationSettings(output_mode, width, "default"),
            ["default"],
            ["no-processing"],
        )

````

Edit: `client/tests/test_translation_settings.py`

````python
                self.assertEqual(self.normalize(output_mode).output_mode, "unicode")

    def test_width_is_clamped_at_both_ends(self) -> None:
        for width, expected in ((-5, 10), (9, 10), (10, 10), (40, 40), (200, 200), (201, 200)):
````

````python
                self.assertEqual(self.normalize(output_mode).output_mode, "unicode")

    def test_a_script_that_is_not_listed_becomes_no_processing(self) -> None:
        # F-18 (D3): a script deleted or renamed outside the app.
        for script, expected in (("upper", "upper"), ("gone", "no-processing"), ("Upper", "no-processing")):
            with self.subTest(script=script):
                settings = normalize_translation_settings(
                    TranslationSettings("unicode", 40, "default", script),
                    ["default"],
                    ["no-processing", "upper"],
                )
                self.assertEqual(settings.selected_script, expected)

    def test_width_is_clamped_at_both_ends(self) -> None:
        for width, expected in ((-5, 10), (9, 10), (10, 10), (40, 40), (200, 200), (201, 200)):
````

```bash
$PY -B -X utf8 -m unittest tests.test_config tests.test_translation_settings tests.test_settings_dialogs tests.test_conversion_text_pipeline tests.test_conversion_service tests.test_gui_document_flows tests.test_text_scripts_presenter 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_a_file_that_cannot_be_read_is_unreadable (tests.test_config.ConfigSaveProblemTest.test_a_file_that_cannot_be_read_is_unreadable)
AttributeError: 'ConfigStore' object has no attribute 'set_selected_script'
ERROR: test_every_setter_returns_none_when_the_save_works (tests.test_config.ConfigSaveProblemTest.test_every_setter_returns_none_when_the_save_works) [set_sele
ERROR: test_a_selected_script_that_is_not_a_string_reads_as_the_default (tests.test_config.ConfigTest.test_a_selected_script_that_is_not_a_string_reads_as_the_d
AttributeError: 'ConfigStore' object has no attribute 'get_selected_script'
ERROR: test_selected_script_roundtrip_under_conversion_section (tests.test_config.ConfigTest.test_selected_script_roundtrip_under_conversion_section)
AttributeError: module 'config' has no attribute 'SELECTED_SCRIPT_KEY'
ERROR: test_a_script_that_is_not_listed_becomes_no_processing (tests.test_translation_settings.TranslationSettingsNormalizeTest.test_a_script_that_is_not_listed
TypeError: TranslationSettings.__init__() takes 4 positional arguments but 5 were given
ERROR: test_every_output_mode_is_kept_and_unknown_modes_become_the_default (tests.test_translation_settings.TranslationSettingsNormalizeTest.test_every_output_m
TypeError: normalize_translation_settings() takes 2 positional arguments but 3 were given
ERROR: test_width_is_clamped_at_both_ends (tests.test_translation_settings.TranslationSettingsNormalizeTest.test_width_is_clamped_at_both_ends) (width=-5)
ERROR: test_width_is_clamped_at_both_ends (tests.test_translation_settings.TranslationSettingsNormalizeTest.test_width_is_clamped_at_both_ends) (width=9)
ERROR: test_width_is_clamped_at_both_ends (tests.test_translation_settings.TranslationSettingsNormalizeTest.test_width_is_clamped_at_both_ends) (width=10)
ERROR: test_width_is_clamped_at_both_ends (tests.test_translation_settings.TranslationSettingsNormalizeTest.test_width_is_clamped_at_both_ends) (width=40)
ERROR: test_width_is_clamped_at_both_ends (tests.test_translation_settings.TranslationSettingsNormalizeTest.test_width_is_clamped_at_both_ends) (width=200)
ERROR: test_width_is_clamped_at_both_ends (tests.test_translation_settings.TranslationSettingsNormalizeTest.test_width_is_clamped_at_both_ends) (width=201)
ERROR: test_a_config_without_a_script_selects_no_processing (tests.test_translation_settings.TranslationSettingsTest.test_a_config_without_a_script_selects_no_p
TypeError: load_translation_settings() takes 2 positional arguments but 3 were given
ERROR: test_load_keeps_valid_config (tests.test_translation_settings.TranslationSettingsTest.test_load_keeps_valid_config)
ERROR: test_load_normalizes_invalid_config (tests.test_translation_settings.TranslationSettingsTest.test_load_normalizes_invalid_config)
ERROR: test_save_calls_every_setter_and_returns_the_first_problem (tests.test_translation_settings.TranslationSettingsTest.test_save_calls_every_setter_and_retu
AttributeError: Mock object has no attribute 'set_selected_script'
ERROR: test_save_persists_one_complete_settings_value (tests.test_translation_settings.TranslationSettingsTest.test_save_persists_one_complete_settings_value)
ERROR: test_save_returns_the_script_problem_when_it_is_the_only_one (tests.test_translation_settings.TranslationSettingsTest.test_save_returns_the_script_proble
ERROR: test_show_singleton_reraises_unexpected_existing_dialog_errors (tests.test_settings_dialogs.DotExpressSettingsDialogFlowTest.test_show_singleton_reraises
TypeError: DotExpressSettingsDialog.show_singleton() got an unexpected keyword argument 'script_names'
ERROR: test_constructor_failure_leaves_the_slot_empty (tests.test_settings_dialogs.DotExpressSettingsSingletonTest.test_constructor_failure_leaves_the_slot_empt
ERROR: test_show_singleton_builds_forwards_and_shows_a_new_dialog (tests.test_settings_dialogs.DotExpressSettingsSingletonTest.test_show_singleton_builds_forwar
ERROR: test_show_singleton_forwards_the_initial_category_to_a_new_dialog (tests.test_settings_dialogs.DotExpressSettingsSingletonTest.test_show_singleton_forwar
ERROR: test_show_singleton_propagates_other_exceptions_and_keeps_the_slot (tests.test_settings_dialogs.DotExpressSettingsSingletonTest.test_show_singleton_propa
ERROR: test_show_singleton_raises_the_live_dialog_in_order (tests.test_settings_dialogs.DotExpressSettingsSingletonTest.test_show_singleton_raises_the_live_dial
ERROR: test_show_singleton_rebuilds_after_a_dead_window_error (tests.test_settings_dialogs.DotExpressSettingsSingletonTest.test_show_singleton_rebuilds_after_a_
ERROR: test_show_singleton_rejects_an_unregistered_category_before_reading_the_slot (tests.test_settings_dialogs.DotExpressSettingsSingletonTest.test_show_singl
ERROR: test_show_singleton_reraises_a_live_window_error_and_keeps_the_slot (tests.test_settings_dialogs.DotExpressSettingsSingletonTest.test_show_singleton_rera
ERROR: test_show_singleton_selects_the_initial_category_before_raising (tests.test_settings_dialogs.DotExpressSettingsSingletonTest.test_show_singleton_selects_
ERROR: test_an_unknown_name_selects_no_processing_and_a_new_snapshot_reselects (tests.test_settings_dialogs.TranslationPanelScriptChoiceTest.test_an_unknown_nam
ERROR: test_no_processing_is_listed_first_by_its_display_name (tests.test_settings_dialogs.TranslationPanelScriptChoiceTest.test_no_processing_is_listed_first_b
ERROR: test_no_script_names_disable_the_choice (tests.test_settings_dialogs.TranslationPanelScriptChoiceTest.test_no_script_names_disable_the_choice)
ERROR: test_the_choice_round_trips_the_internal_name (tests.test_settings_dialogs.TranslationPanelScriptChoiceTest.test_the_choice_round_trips_the_internal_name
ERROR: test_translation_panel_collects_controls_without_mutating_baseline (tests.test_settings_dialogs.TranslationSettingsPanelTest.test_translation_panel_colle
ERROR: test_alignment_output_entry_applies_source_preprocessing_once (tests.test_conversion_text_pipeline.ConversionTextPipelineTest.test_alignment_output_entry
TypeError: ConversionRequest.__init__() got an unexpected keyword argument 'script_path'
ERROR: test_no_processing_runs_no_script_and_still_maps_characters (tests.test_conversion_text_pipeline.ConversionTextPipelineTest.test_no_processing_runs_no_sc
TypeError: preprocess_source_text() got an unexpected keyword argument 'script_path'
ERROR: test_preprocess_source_text_normalizes_system_exit (tests.test_conversion_text_pipeline.ConversionTextPipelineTest.test_preprocess_source_text_normalizes
ERROR: test_preprocess_source_text_preserves_script_exception (tests.test_conversion_text_pipeline.ConversionTextPipelineTest.test_preprocess_source_text_preser
ERROR: test_preprocess_source_text_runs_user_script_before_bopomofo_mapping (tests.test_conversion_text_pipeline.ConversionTextPipelineTest.test_preprocess_sour
ERROR: test_conversion_reports_text_processing_stage (tests.test_conversion_service.ConversionServiceTest.test_conversion_reports_text_processing_stage)
ERROR: test_conversion_uses_processed_text_for_translation_and_dual_view (tests.test_conversion_service.ConversionServiceTest.test_conversion_uses_processed_tex
ERROR: test_empty_source_does_not_read_or_execute_preprocessing_script (tests.test_conversion_service.ConversionServiceTest.test_empty_source_does_not_read_or_e
ERROR: test_a_script_error_of_the_contract_is_shown_in_zh_tw (tests.test_conversion_service.DictionaryErrorTimingTest.test_a_script_error_of_the_contract_is_sho
ERROR: test_a_selected_script_that_is_missing_fails_at_the_text_processing_stage (tests.test_conversion_service.DictionaryErrorTimingTest.test_a_selected_script
ERROR: test_failing_preprocessing_script_is_reported_before_a_broken_dictionary (tests.test_conversion_service.DictionaryErrorTimingTest.test_failing_preprocess
ERROR: test_headerless_dictionary_does_not_fail_math_only_or_empty_input (tests.test_conversion_service.DictionaryErrorTimingTest.test_headerless_dictionary_doe
ERROR: test_headerless_dictionary_fails_text_at_the_translation_stage (tests.test_conversion_service.DictionaryErrorTimingTest.test_headerless_dictionary_fails_
ERROR: test_math_before_the_first_text_is_translated_before_the_dictionary_error (tests.test_conversion_service.DictionaryErrorTimingTest.test_math_before_the_f
ERROR: test_next_conversion_after_the_dictionary_is_deleted_applies_no_rule (tests.test_conversion_service.DictionaryErrorTimingTest.test_next_conversion_after_
ERROR: test_next_conversion_reads_the_rewritten_dictionary (tests.test_conversion_service.DictionaryErrorTimingTest.test_next_conversion_reads_the_rewritten_dic
ERROR: test_no_processing_gives_the_output_of_the_identity_script (tests.test_conversion_service.DictionaryErrorTimingTest.test_no_processing_gives_the_output_o
ERROR: test_the_legacy_script_next_to_the_dictionary_is_not_run (tests.test_conversion_service.DictionaryErrorTimingTest.test_the_legacy_script_next_to_the_dict
ERROR: test_one_conversion_uses_one_dictionary_snapshot (tests.test_conversion_service.DictionarySnapshotTest.test_one_conversion_uses_one_dictionary_snapshot)
ERROR: test_apply_settings_from_dialog_updates_all_live_state (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_apply_settings_from_dialog_updates_all
ERROR: test_initialize_state_falls_back_to_default_tables_when_loader_returns_empty (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_initialize_state
AttributeError: <module 'gui' from '<client>\\gui.py'> does not have the attribute 'ScriptManagementPresenter'
ERROR: test_initialize_state_loads_translation_tables_into_frame (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_initialize_state_loads_translation_
ERROR: test_open_settings_uses_singleton_dialog (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_open_settings_uses_singleton_dialog)
KeyError: 'script_names'
ERROR: test_initialize_state_wires_presenter_to_active_dictionary (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_initialize_state_wires_prese
ERROR: test_set_active_dictionary_keeps_the_selected_script (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_set_active_dictionary_keeps_the_se
ERROR: test_initialize_state_keeps_the_frame_controller (tests.test_gui_document_flows.DocumentControllerOwnershipTest.test_initialize_state_keeps_the_frame_con
ERROR: test_initialize_state_creates_service_for_frame_controller (tests.test_gui_document_flows.FrameWorkspaceServiceDelegationTest.test_initialize_state_creat
ERROR: test_a_user_script_is_sent_by_its_path_in_the_script_folder (tests.test_gui_document_flows.ScriptSelectionFrameTest.test_a_user_script_is_sent_by_its_pat
ERROR: test_no_processing_sends_no_script (tests.test_gui_document_flows.ScriptSelectionFrameTest.test_no_processing_sends_no_script) (name='no-processing')
ERROR: test_no_processing_sends_no_script (tests.test_gui_document_flows.ScriptSelectionFrameTest.test_no_processing_sends_no_script) (name='No-Processing')
ERROR: test_script_names_for_dialog_refresh_with_the_active_script (tests.test_gui_document_flows.ScriptSelectionFrameTest.test_script_names_for_dialog_refresh_
ERROR: test_set_active_script_saves_it_and_keeps_the_other_settings (tests.test_gui_document_flows.ScriptSelectionFrameTest.test_set_active_script_saves_it_and_
ERROR: test_font_size_and_dictionary_changes_report_through_the_same_flag (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_font_size_and_diction
AttributeError: 'TranslationSettings' object has no attribute 'selected_script'
ERROR: test_no_box_when_the_settings_are_saved (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_no_box_when_the_settings_are_saved)
ERROR: test_text_scripts_presenter (unittest.loader._FailedTest.test_text_scripts_presenter)
ImportError: Failed to import test module: test_text_scripts_presenter
ModuleNotFoundError: No module named 'text_scripts.presenter'
FAIL: test_each_panel_label_name_and_accessible_description (tests.test_settings_dialogs.SettingsTitlesFollowTheLanguageTest.test_each_panel_label_name_and_acce
AssertionError: Tuples differ: (0, '轉譯輸出模式、寬度與字典選項') != (0, '轉譯輸出模式、寬度、字典與文字處理腳本選項')
AssertionError: Tuples differ: (0, '[17 chars]t mode, width, and dictionary options') != (0, '[17 chars]t mode, width, dictionary, and text processing script op
FAIL: test_rows_and_output_mode_choices_show_the_translated_labels_in_order (tests.test_settings_dialogs.TranslationPanelOptionsTest.test_rows_and_output_mode_c
AssertionError: Lists differ: ['點字類型', '寬度', '字典'] != ['點字類型', '寬度', '字典', '文字處理腳本']
FAIL: test_initialize_state_keeps_dictionaries_workspace_and_settings_under_the_root (tests.test_gui_document_flows.ApplicationPathsWiringCharacterizationTest.t
AssertionError: <function NoOpAttributes.__getattr__.<locals>._method at <addr>> != WindowsPath('<tmp>/application/script')
FAIL: test_font_size_and_dictionary_changes_report_through_the_same_flag (tests.test_gui_document_flows.SettingsSaveProblemFrameTest.test_font_size_and_dictiona
AssertionError: Lists differ: [] != [(('DotExpress 無法將設定儲存到「C:\\Users\\tseng\\[229 chars]<addr>})]
Ran 444 tests
FAILED (failures=5, errors=86)
```

- [x] **Step 2: Green: the setting, the Settings choice, the request path and the frame** (`config.py`, `settings/translation.py`, `settings/dialogs.py`, `conversion/*.py` 4 spaces; `gui.py`, `text_scripts/presenter.py` tabs).

Edit: `client/config.py`

````python
WIDTH_KEY = "width"
SELECTED_DICTIONARY_KEY = "selected_dictionary"
FONT_SIZE_KEY = "font_size"
SCHEME_KEY = "scheme"
````

````python
WIDTH_KEY = "width"
SELECTED_DICTIONARY_KEY = "selected_dictionary"
# The text-processing script; "no-processing" is No Processing (F-18 D3).
SELECTED_SCRIPT_KEY = "selected_script"
FONT_SIZE_KEY = "font_size"
SCHEME_KEY = "scheme"
````

Edit: `client/config.py`

````python
        return self._set_section_value(CONVERSION_SECTION, SELECTED_DICTIONARY_KEY, dictionary_name)

    def get_view_font_size(self, default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
        data = self._load()
````

````python
        return self._set_section_value(CONVERSION_SECTION, SELECTED_DICTIONARY_KEY, dictionary_name)

    def get_selected_script(self, default: str = "no-processing") -> str:
        data = self._load()
        value = _get_section(data, CONVERSION_SECTION).get(SELECTED_SCRIPT_KEY)
        return value if isinstance(value, str) else default

    def set_selected_script(self, script_name: str) -> ConfigSaveProblem | None:
        return self._set_section_value(CONVERSION_SECTION, SELECTED_SCRIPT_KEY, script_name)

    def get_view_font_size(self, default: int = DEFAULT_VIEW_FONT_SIZE) -> int:
        data = self._load()
````

Edit: `client/conversion/output.py`

````python

from conversion.contracts import TranslationRuntime
from conversion.preprocessing.user_script import preprocessing_script_path
from conversion.text.char_maps import translate__mapping_char
from conversion.text.pipeline import TextProcessingError, preprocess_source_text
````

````python

from conversion.contracts import TranslationRuntime
from conversion.text.char_maps import translate__mapping_char
from conversion.text.pipeline import TextProcessingError, preprocess_source_text
````

Edit: `client/conversion/output.py`

````python
    lang: str
    charset_maps: dict[str, str]


````

````python
    lang: str
    charset_maps: dict[str, str]
    # The text-processing script to run; None is No Processing (F-18 D10).
    script_path: Path | None = None


````

Edit: `client/conversion/output.py`

````python
            request.raw_text,
            data_dir=request.data_dir,
            preprocessing_path=preprocessing_script_path(request.dictionary_path.parent),
            map_char=map_char,
        )
````

````python
            request.raw_text,
            data_dir=request.data_dir,
            script_path=request.script_path,
            map_char=map_char,
        )
````

Edit: `client/conversion/preprocessing/user_script.py`

````python


def execute_preprocessing_script(path: Path | str, input_text: str) -> str:
    source_path = Path(path)
    return _run_script(load_preprocessing_script(source_path), source_path, input_text)


def _run_script(source: str, source_path: Path, input_text: str) -> str:
    validate_script(source, filename=str(source_path))
````

````python


def _run_script(source: str, source_path: Path, input_text: str) -> str:
    validate_script(source, filename=str(source_path))
````

Edit: `client/conversion/text/pipeline.py`

````python

from conversion.contracts import TranslationRuntime
from conversion.preprocessing.user_script import execute_preprocessing_script
from conversion.preprocessing.literal_braille import (
    build_literal_translation_result,
````

````python

from conversion.contracts import TranslationRuntime
from conversion.preprocessing.user_script import execute_script
from conversion.preprocessing.literal_braille import (
    build_literal_translation_result,
````

Edit: `client/conversion/text/pipeline.py`

````python
    *,
    data_dir: Path,
    preprocessing_path: Path,
    execute_script: ExecuteScript = execute_preprocessing_script,
    map_char: Callable[..., str] = map_characters,
) -> str:
    try:
        processed_text = execute_script(preprocessing_path, text)
    except BaseException as error:
        normalized_error = (
````

````python
    *,
    data_dir: Path,
    script_path: Path | None,
    execute_script: ExecuteScript = execute_script,
    map_char: Callable[..., str] = map_characters,
) -> str:
    """The text after the selected script and the Bopomofo character map.

    ``script_path`` ``None`` is No Processing: no script runs (F-18 D4). Any failure of a
    script, including a missing or invalid file, is a ``TextProcessingError`` (F-18 D10).
    """
    try:
        processed_text = text if script_path is None else execute_script(script_path, text)
    except BaseException as error:
        normalized_error = (
````

Edit: `client/gui.py`

````python
)
from documents.workspace_service import DocumentWorkspaceService
from ui.action_menu import get_document_menu_enabled_state
from ui.conversion_presenter import ConversionPresenter
````

````python
)
from documents.workspace_service import DocumentWorkspaceService
from text_scripts.manager import is_no_processing_script, script_path_for_name
from text_scripts.presenter import ScriptManagementPresenter
from ui.action_menu import get_document_menu_enabled_state
from ui.conversion_presenter import ConversionPresenter
````

Edit: `client/gui.py`

````python
from config import ConfigSaveProblem, ConfigSaveProblemKind, ConfigStore, DEFAULT_TRANSLATION_TABLES, is_access_error
from settings.translation import (
	TranslationSettings,
	load_translation_settings,
	normalize_translation_settings,
````

````python
from config import ConfigSaveProblem, ConfigSaveProblemKind, ConfigStore, DEFAULT_TRANSLATION_TABLES, is_access_error
from settings.translation import (
	load_translation_settings,
	normalize_translation_settings,
````

Edit: `client/gui.py`

````python
		)
		self._dictionary_presenter.refresh()
		self.translation_settings = load_translation_settings(
			self._config_store,
			self._dictionary_presenter.dictionary_names,
		)
		self.translation_tables = load_translation_tables(self._config_store) or DEFAULT_TRANSLATION_TABLES.copy()
````

````python
		)
		self._dictionary_presenter.refresh()
		self.script_dir = self._paths.script
		self._script_presenter = ScriptManagementPresenter(
			self.script_dir,
			get_active_name=lambda: self.translation_settings.selected_script,
			set_active_name=self._set_active_script,
		)
		self._script_presenter.refresh()
		self.translation_settings = load_translation_settings(
			self._config_store,
			self._dictionary_presenter.dictionary_names,
			self._script_presenter.script_names,
		)
		self.translation_tables = load_translation_tables(self._config_store) or DEFAULT_TRANSLATION_TABLES.copy()
````

Edit: `client/gui.py`

````python
		return self._dictionary_presenter.dictionary_names

	def get_settings_snapshot(self) -> DotExpressSettingsSnapshot:
		dictionary_names = self.get_dictionary_names_for_dialog()
		return DotExpressSettingsSnapshot.create(
			normalize_translation_settings(self.translation_settings, dictionary_names),
			self.translation_tables,
			normalize_view_settings(self.view_settings),
````

````python
		return self._dictionary_presenter.dictionary_names

	def get_script_names_for_dialog(self) -> list[str]:
		self._script_presenter.refresh(self.translation_settings.selected_script)
		return self._script_presenter.script_names

	def get_settings_snapshot(self) -> DotExpressSettingsSnapshot:
		dictionary_names = self.get_dictionary_names_for_dialog()
		script_names = self.get_script_names_for_dialog()
		return DotExpressSettingsSnapshot.create(
			normalize_translation_settings(self.translation_settings, dictionary_names, script_names),
			self.translation_tables,
			normalize_view_settings(self.view_settings),
````

Edit: `client/gui.py`

````python
	) -> DotExpressSettingsSnapshot:
		dictionary_names = self.get_dictionary_names_for_dialog()
		translation = normalize_translation_settings(snapshot.translation, dictionary_names)
		view = normalize_view_settings(snapshot.view)
		tables = dict(snapshot.translation_tables)
````

````python
	) -> DotExpressSettingsSnapshot:
		dictionary_names = self.get_dictionary_names_for_dialog()
		script_names = self.get_script_names_for_dialog()
		translation = normalize_translation_settings(snapshot.translation, dictionary_names, script_names)
		view = normalize_view_settings(snapshot.view)
		tables = dict(snapshot.translation_tables)
````

Edit: `client/gui.py`

````python

	def _set_active_dictionary(self, selected_name: str) -> None:
		self.translation_settings = TranslationSettings(
			output_mode=self.translation_settings.output_mode,
			width=self.translation_settings.width,
			selected_dictionary=selected_name,
		)
		self._report_settings_save_problem(self._config_store.set_selected_dictionary(selected_name))

	def _report_settings_save_problem(self, problem: ConfigSaveProblem | None) -> None:
````

````python

	def _set_active_dictionary(self, selected_name: str) -> None:
		self.translation_settings = replace(self.translation_settings, selected_dictionary=selected_name)
		self._report_settings_save_problem(self._config_store.set_selected_dictionary(selected_name))

	def _set_active_script(self, selected_name: str) -> None:
		"""Make ``selected_name`` the script of the next conversions and save it (F-18 D3)."""
		self.translation_settings = replace(self.translation_settings, selected_script=selected_name)
		self._report_settings_save_problem(self._config_store.set_selected_script(selected_name))

	def _report_settings_save_problem(self, problem: ConfigSaveProblem | None) -> None:
````

Edit: `client/gui.py`

````python
	def _get_selected_dictionary_path(self) -> Path:
		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)

	def _show_file_error(self, message: str, error: Exception) -> None:
````

````python
	def _get_selected_dictionary_path(self) -> Path:
		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)

	def _get_selected_script_path(self) -> Path | None:
		"""The selected script's file; ``None`` for No Processing, whose file is never run (F-18 D4)."""
		name = self.translation_settings.selected_script
		if is_no_processing_script(name):
			return None
		return script_path_for_name(name, self.script_dir)

	def _show_file_error(self, message: str, error: Exception) -> None:
````

Edit: `client/gui.py`

````python
		self.input_txt.ShowPosition(0)

	def _build_conversion_request(self, raw_text: str, output_mode: str, width: int, dictionary_path: Path) -> ConversionRequest:
		return ConversionRequest(
			raw_text=raw_text,
````

````python
		self.input_txt.ShowPosition(0)

	def _build_conversion_request(
		self,
		raw_text: str,
		output_mode: str,
		width: int,
		dictionary_path: Path,
		script_path: Path | None = None,
	) -> ConversionRequest:
		return ConversionRequest(
			raw_text=raw_text,
````

Edit: `client/gui.py`

````python
			lang=self._config_store.get_lang(),
			charset_maps=self._config_store.get_charset_maps(),
		)

````

````python
			lang=self._config_store.get_lang(),
			charset_maps=self._config_store.get_charset_maps(),
			script_path=script_path,
		)

````

Edit: `client/gui.py`

````python
			settings.width,
			self._get_selected_dictionary_path(),
		)

````

````python
			settings.width,
			self._get_selected_dictionary_path(),
			self._get_selected_script_path(),
		)

````

Edit: `client/gui.py`

````python
			snapshot=self.get_settings_snapshot(),
			dictionary_names=self.get_dictionary_names_for_dialog(),
			commit=self.apply_settings_from_dialog,
			initial_category=TranslationSettingsPanel,
````

````python
			snapshot=self.get_settings_snapshot(),
			dictionary_names=self.get_dictionary_names_for_dialog(),
			script_names=self.get_script_names_for_dialog(),
			commit=self.apply_settings_from_dialog,
			initial_category=TranslationSettingsPanel,
````

Edit: `client/settings/dialogs.py`

````python
from braille.tables import listTables
from conversion.preprocessing.user_script import (
    load_preprocessing_script,
    save_preprocessing_script,
)
from i18n import N_, _
from ui.dialog_base import SingletonDialogMixin
from ui.message_box import message_box
````

````python
from braille.tables import listTables
from conversion.preprocessing.user_script import (
    NO_PROCESSING_SCRIPT_NAME,
    load_preprocessing_script,
    save_preprocessing_script,
)
from i18n import N_, _
from text_scripts.actions import script_display_name
from ui.dialog_base import SingletonDialogMixin
from ui.message_box import message_box
````

Edit: `client/settings/dialogs.py`

````python
    title = N_("Translation")
    panel_description = N_(
        "Translation output mode, width, and dictionary options"
    )

    def make_settings(self) -> None:
        self.dictionary_names = list(self.owner.dictionary_names)
        settings = self.owner.snapshot.translation
        grid = wx.FlexGridSizer(0, 2, 8, 8)
````

````python
    title = N_("Translation")
    panel_description = N_(
        "Translation output mode, width, dictionary, and text processing script options"
    )

    def make_settings(self) -> None:
        self.dictionary_names = list(self.owner.dictionary_names)
        # Internal names; the choice shows their display names (F-18 D3).
        self.script_names = list(self.owner.script_names)
        settings = self.owner.snapshot.translation
        grid = wx.FlexGridSizer(0, 2, 8, 8)
````

Edit: `client/settings/dialogs.py`

````python
        grid.Add(self.dictionary_choice, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
````

````python
        grid.Add(self.dictionary_choice, 1, wx.EXPAND)

        script_label = wx.StaticText(self, label=_("Text Processing Script"))
        self.script_choice = wx.Choice(self, choices=[script_display_name(name) for name in self.script_names])
        grid.Add(script_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.script_choice, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
````

Edit: `client/settings/dialogs.py`

````python
        self._select_output_mode(settings.output_mode)
        self._select_dictionary(settings.selected_dictionary)

    def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
````

````python
        self._select_output_mode(settings.output_mode)
        self._select_dictionary(settings.selected_dictionary)
        self._select_script(settings.selected_script)

    def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
````

Edit: `client/settings/dialogs.py`

````python
        self._select_output_mode(settings.output_mode)
        self._select_dictionary(settings.selected_dictionary)

    def on_save(self, snapshot: DotExpressSettingsSnapshot) -> DotExpressSettingsSnapshot:
````

````python
        self._select_output_mode(settings.output_mode)
        self._select_dictionary(settings.selected_dictionary)
        self._select_script(settings.selected_script)

    def on_save(self, snapshot: DotExpressSettingsSnapshot) -> DotExpressSettingsSnapshot:
````

Edit: `client/settings/dialogs.py`

````python
            width=self.width_spin.GetValue(),
            selected_dictionary=self._selected_dictionary(),
        )
        return snapshot.with_translation(value)
````

````python
            width=self.width_spin.GetValue(),
            selected_dictionary=self._selected_dictionary(),
            selected_script=self._selected_script(),
        )
        return snapshot.with_translation(value)
````

Edit: `client/settings/dialogs.py`

````python
        return self.dictionary_names[index]

    def _select_output_mode(self, output_mode: str) -> None:
        self.output_choice.SetSelection(option_index(OUTPUT_MODE_OPTIONS, output_mode))
````

````python
        return self.dictionary_names[index]

    def _selected_script(self) -> str:
        index = self.script_choice.GetSelection()
        if index < 0 or index >= len(self.script_names):
            return self.script_names[0] if self.script_names else NO_PROCESSING_SCRIPT_NAME
        return self.script_names[index]

    def _select_output_mode(self, output_mode: str) -> None:
        self.output_choice.SetSelection(option_index(OUTPUT_MODE_OPTIONS, output_mode))
````

Edit: `client/settings/dialogs.py`

````python
        )
        self.dictionary_choice.SetSelection(index)


````

````python
        )
        self.dictionary_choice.SetSelection(index)

    def _select_script(self, script_name: str) -> None:
        if not self.script_names:
            self.script_choice.SetSelection(wx.NOT_FOUND)
            self.script_choice.Disable()
            return
        index = self.script_names.index(script_name) if script_name in self.script_names else 0
        self.script_choice.SetSelection(index)


````

Edit: `client/settings/dialogs.py`

````python
        *,
        snapshot: DotExpressSettingsSnapshot,
        dictionary_names: list[str],
        commit: CommitSettings,
        initial_category=None,
    ) -> None:
````

````python
        *,
        snapshot: DotExpressSettingsSnapshot,
        dictionary_names: list[str],
        script_names: list[str],
        commit: CommitSettings,
        initial_category=None,
    ) -> None:
````

Edit: `client/settings/dialogs.py`

````python
        self.snapshot = snapshot.copied()
        self.dictionary_names = list(dictionary_names)
        self.commit = commit
        super().__init__(
````

````python
        self.snapshot = snapshot.copied()
        self.dictionary_names = list(dictionary_names)
        self.script_names = list(script_names)
        self.commit = commit
        super().__init__(
````

Edit: `client/settings/dialogs.py`

````python
        snapshot: DotExpressSettingsSnapshot,
        dictionary_names: list[str],
        commit: CommitSettings,
        initial_category=None,
````

````python
        snapshot: DotExpressSettingsSnapshot,
        dictionary_names: list[str],
        script_names: list[str],
        commit: CommitSettings,
        initial_category=None,
````

Edit: `client/settings/dialogs.py`

````python
                snapshot=snapshot,
                dictionary_names=dictionary_names,
                commit=commit,
                initial_category=initial_category,
````

````python
                snapshot=snapshot,
                dictionary_names=dictionary_names,
                script_names=script_names,
                commit=commit,
                initial_category=initial_category,
````

Edit: `client/settings/translation.py`

````python
    DEFAULT_OUTPUT_MODE,
)
from dictionaries.actions import resolve_dictionary_selection
from .options import CONVERSION_WIDTH_RANGE, OUTPUT_MODE_OPTIONS, normalize_option_value

````

````python
    DEFAULT_OUTPUT_MODE,
)
from conversion.preprocessing.user_script import NO_PROCESSING_SCRIPT_NAME
from dictionaries.actions import resolve_dictionary_selection
from text_scripts.manager import resolve_selected_script
from .options import CONVERSION_WIDTH_RANGE, OUTPUT_MODE_OPTIONS, normalize_option_value

````

Edit: `client/settings/translation.py`

````python
    width: int
    selected_dictionary: str


````

````python
    width: int
    selected_dictionary: str
    # The text-processing script (F-18 D3); No Processing skips the script stage.
    selected_script: str = NO_PROCESSING_SCRIPT_NAME


````

Edit: `client/settings/translation.py`

````python
    width=DEFAULT_CONVERSION_WIDTH,
    selected_dictionary="default",
)

````

````python
    width=DEFAULT_CONVERSION_WIDTH,
    selected_dictionary="default",
    selected_script=NO_PROCESSING_SCRIPT_NAME,
)

````

Edit: `client/settings/translation.py`

````python
    settings: TranslationSettings,
    dictionary_names: list[str],
) -> TranslationSettings:
    return TranslationSettings(
````

````python
    settings: TranslationSettings,
    dictionary_names: list[str],
    script_names: list[str],
) -> TranslationSettings:
    return TranslationSettings(
````

Edit: `client/settings/translation.py`

````python
            settings.selected_dictionary,
        ),
    )


def load_translation_settings(store: ConfigStore, dictionary_names: list[str]) -> TranslationSettings:
    settings = TranslationSettings(
        output_mode=store.get_output_mode(DEFAULT_OUTPUT_MODE),
        width=store.get_conversion_width(DEFAULT_CONVERSION_WIDTH),
        selected_dictionary=store.get_selected_dictionary(DEFAULT_TRANSLATION_SETTINGS.selected_dictionary),
    )
    return normalize_translation_settings(settings, dictionary_names)


def save_translation_settings(store: ConfigStore, settings: TranslationSettings) -> ConfigSaveProblem | None:
    """Save the three settings, each one even if another fails; the first problem, or ``None`` (F-12 D6)."""
    problems = (
        store.set_output_mode(settings.output_mode),
        store.set_conversion_width(settings.width),
        store.set_selected_dictionary(settings.selected_dictionary),
    )
    return next((problem for problem in problems if problem is not None), None)
````

````python
            settings.selected_dictionary,
        ),
        selected_script=resolve_selected_script(script_names, settings.selected_script),
    )


def load_translation_settings(
    store: ConfigStore,
    dictionary_names: list[str],
    script_names: list[str],
) -> TranslationSettings:
    settings = TranslationSettings(
        output_mode=store.get_output_mode(DEFAULT_OUTPUT_MODE),
        width=store.get_conversion_width(DEFAULT_CONVERSION_WIDTH),
        selected_dictionary=store.get_selected_dictionary(DEFAULT_TRANSLATION_SETTINGS.selected_dictionary),
        selected_script=store.get_selected_script(DEFAULT_TRANSLATION_SETTINGS.selected_script),
    )
    return normalize_translation_settings(settings, dictionary_names, script_names)


def save_translation_settings(store: ConfigStore, settings: TranslationSettings) -> ConfigSaveProblem | None:
    """Save the four settings, each one even if another fails; the first problem, or ``None`` (F-12 D6)."""
    problems = (
        store.set_output_mode(settings.output_mode),
        store.set_conversion_width(settings.width),
        store.set_selected_dictionary(settings.selected_dictionary),
        store.set_selected_script(settings.selected_script),
    )
    return next((problem for problem in problems if problem is not None), None)
````

File: `client/text_scripts/presenter.py`

````python
"""Script-management workflow without wx (F-18).

``ScriptManagementPresenter`` owns the list of script names, the twin of
``dictionaries.presenter.DictionaryManagementPresenter``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from text_scripts.manager import (
	ensure_no_processing_script,
	list_script_names,
	resolve_selected_script,
	script_path_for_name,
)


class ScriptManagementPresenter:
	"""The only owner of the script name list."""

	def __init__(
		self,
		script_dir: Path,
		*,
		get_active_name: Callable[[], str],
		set_active_name: Callable[[str], None],
	) -> None:
		self._script_dir = Path(script_dir)
		self._get_active_name = get_active_name
		self._set_active_name = set_active_name
		self._script_names: list[str] = []

	@property
	def script_dir(self) -> Path:
		return self._script_dir

	@property
	def script_names(self) -> list[str]:
		return list(self._script_names)

	def refresh(self, preferred_name: str | None = None) -> str:
		"""Read the folder again (No Processing is created if missing); the name to select."""
		ensure_no_processing_script(self._script_dir)
		self._script_names = list_script_names(self._script_dir)
		return resolve_selected_script(self._script_names, preferred_name)

	def script_path(self, name: str) -> Path:
		return script_path_for_name(name, self._script_dir)
````

- [x] **Step 3: Regenerate the catalogs** (2 new msgids; the old panel description becomes the fuzzy base of the new one and leaves).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
$PY -I $T/tools/set_msgstr.py locales/zh_TW/LC_MESSAGES/dotexpress.po $T/tools/f18_msgstr.tsv
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid ' locales/zh_TW/LC_MESSAGES/dotexpress.po
git -C $REPO diff --stat -- client/locales
git -C $REPO diff -- client/locales/zh_TW/LC_MESSAGES/dotexpress.po | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[-+]#: '
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
414 translated messages, 2 fuzzy translations.
msgstr set: 7, not in the file yet: 26
a second msgmerge changes nothing
msgfmt exit 0
416 translated messages.
26
 client/locales/dotexpress.pot                  | 174 ++++++++++++------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 35839 -> 35942 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 176 +++++++++++++------------
 3 files changed, 181 insertions(+), 169 deletions(-)
-msgid "Translation output mode, width, and dictionary options"
-msgstr "轉譯輸出模式、寬度與字典選項"
+msgid ""
+"Translation output mode, width, dictionary, and text processing script "
+"options"
+msgstr "轉譯輸出模式、寬度、字典與文字處理腳本選項"
+msgid "Text Processing Script"
+msgstr "文字處理腳本"
+
source msgids: 416 sha256 da10e661fb446762088c3bc1b345e73be332c2c57912efe6f8dd934b4eb47877
```

- [x] **Step 4: Green: the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_config tests.test_translation_settings tests.test_settings_dialogs tests.test_conversion_text_pipeline tests.test_conversion_service tests.test_gui_document_flows tests.test_text_scripts_presenter tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 497 tests
OK
Ran 1748 tests
OK (skipped=6)
```

- [x] **Step 5: Commit.**

```bash
git -C $REPO add client/config.py client/conversion/output.py client/conversion/preprocessing/user_script.py client/conversion/text/pipeline.py client/gui.py client/settings/dialogs.py client/settings/translation.py client/text_scripts/presenter.py client/tests/test_config.py client/tests/test_conversion_service.py client/tests/test_conversion_text_pipeline.py client/tests/test_gui_document_flows.py client/tests/test_settings_dialogs.py client/tests/test_text_scripts_presenter.py client/tests/test_translation_settings.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "feat: select the text-processing script in Settings and run it at conversion (F-18)"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
 client/config.py                               |  10 ++
 client/conversion/output.py                    |   5 +-
 client/conversion/preprocessing/user_script.py |   5 -
 client/conversion/text/pipeline.py             |  13 +-
 client/gui.py                                  |  51 +++++--
 client/locales/dotexpress.pot                  | 174 ++++++++++++------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 35839 -> 35942 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 176 +++++++++++++------------
 client/settings/dialogs.py                     |  32 ++++-
 client/settings/translation.py                 |  19 ++-
 client/tests/test_config.py                    |  20 +++
 client/tests/test_conversion_service.py        |  79 ++++++++---
 client/tests/test_conversion_text_pipeline.py  |  35 ++++-
 client/tests/test_gui_document_flows.py        | 104 +++++++++++++--
 client/tests/test_settings_dialogs.py          |  66 +++++++++-
 client/tests/test_text_scripts_presenter.py    |  95 +++++++++++++
 client/tests/test_translation_settings.py      |  51 ++++++-
 client/text_scripts/presenter.py               |  50 +++++++
 18 files changed, 750 insertions(+), 235 deletions(-)
ef352d3c9d121f629192431ce10031bd33aec7f1
```

### Task 3: Replace Text Processing with Script Management (D7-D9, D11)

- [x] **Step 1: Red: Test Plan C, D and the rest of G.** `test_text_scripts_presenter.py` (tabs): the flows through a fake view (Add: name, then the template, nothing written before a save, a taken name asks again, a file written meanwhile; Edit: the file's text, an invalid script opens, an unreadable one is explained; Delete: the question, the neighbour above, the active one becomes No Processing; Rename: the active name follows; Import: each error text, the original bytes, a taken name; Export: the suggested file names). New `test_script_dialogs.py` (tabs): the management dialog's statuses, reason row, selection, availability, handlers and view methods; the name dialog's messages (the reserved one with the name as typed); the editor built for real against fake widgets (title, 「Python 程式碼」, Apply, the failure box and focus, OK, the discard question only after a change, line ends). `test_dialog_base.py`: `reserved_name=None`. `test_gui_document_flows.py`: the menu item and `on_open_script_management`; the Text Processing tests go. `test_settings_dialogs.py`: the Text Processing tests go (one test checks the class is gone). `test_user_preprocessing_script.py`: the two legacy tests become one that checks the old names are gone. `test_translation_menu.py`, `test_i18n.py` (Spec Corrections 10), `wx_stub.py`.

Edit: `client/tests/test_dialog_base.py`

````python
        self.assertEqual(translate.call_args_list, [call("P2-1 test: {name} is reserved"), call("P2-1 test: empty")])

    def test_messages_are_frozen(self) -> None:
        with self.assertRaises(dataclasses.FrozenInstanceError):
````

````python
        self.assertEqual(translate.call_args_list, [call("P2-1 test: {name} is reserved"), call("P2-1 test: empty")])

    def test_reserved_without_a_fixed_name_shows_the_name_typed(self) -> None:
        # F-18 (D4): three script names are reserved; the message repeats the one typed.
        messages = NameDialogMessages(
            empty="e",
            too_long="t",
            invalid="i",
            reserved='Script name "{name}" is reserved.',
            reserved_name=None,
        )

        self.assertEqual(messages.message_for("reserved", "不處理"), "腳本名稱「不處理」為保留名稱。")
        self.assertEqual(TEST_MESSAGES.message_for("reserved", "typed"), "P2-1 test: default is reserved")

    def test_messages_are_frozen(self) -> None:
        with self.assertRaises(dataclasses.FrozenInstanceError):
````

Edit: `client/tests/test_dialog_base.py`

````python
                    dialog = make_name_dialog(base, raising(NameValidationError(code, "English")), "x")
                    self.assertEqual(dialog._validate_name("x"), message)

    def test_a_plain_value_error_is_reported_as_invalid(self) -> None:
````

````python
                    dialog = make_name_dialog(base, raising(NameValidationError(code, "English")), "x")
                    self.assertEqual(dialog._validate_name("x"), message)

    def test_the_reserved_message_gets_the_name_typed_without_spaces(self) -> None:
        messages = dataclasses.replace(TEST_MESSAGES, reserved_name=None)
        for base in DIALOG_BASES:
            with self.subTest(base=base.__name__):
                dialog = make_name_dialog(base, raising(NameValidationError("reserved", "English")), " No Processing")
                dialog.name_messages = messages
                self.assertEqual(dialog._validate_name(" No Processing"), "P2-1 test: No Processing is reserved")

    def test_a_plain_value_error_is_reported_as_invalid(self) -> None:
````

Edit: `client/tests/test_gui_document_flows.py`

````python

class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
    def test_open_text_processing_uses_dictionary_directory_script(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        frame.dictionary_dir = Path("dictionary")
        with patch.object(gui.TextProcessingDialog, "show_singleton") as show:
            frame.on_open_text_processing(None)
        show.assert_called_once_with(
            parent=frame,
            script_path=Path("dictionary/preprocessing.py"),
        )

    def test_open_text_processing_reports_read_error(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
        frame.dictionary_dir = Path("dictionary")
        with (
            patch.object(gui.TextProcessingDialog, "show_singleton", side_effect=OSError("denied")),
            patch.object(gui, "message_box") as message_box,
        ):
            frame.on_open_text_processing(None)
        message_box.assert_called_once_with(
            gui._("Unable to open text processing script: {error}").format(error="denied"),
            gui._("Text Processing"),
            gui.wx.OK | gui.wx.ICON_ERROR,
            parent=frame,
        )

    def test_app_builds_runtime_and_passes_it_to_frame(self) -> None:
````

````python

class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
    def test_open_script_management_shows_the_presenter_on_the_active_script(self) -> None:
        # F-18 (D7, D11): modal, the focus on the active script.
        frame = object.__new__(gui.BrailleFrame)
        frame.translation_settings = TranslationSettings("unicode", 40, "default", "upper")
        frame._script_presenter = Mock()
        frame._script_presenter.refresh.return_value = "upper"
        with patch.object(gui, "ScriptManagementDialog") as dialog_class:
            frame.on_open_script_management(None)

        frame._script_presenter.refresh.assert_called_once_with("upper")
        dialog_class.assert_called_once_with(frame, frame._script_presenter, "upper")
        dialog_class.return_value.__enter__.return_value.ShowModal.assert_called_once_with()

    def test_the_text_processing_dialog_and_its_handler_are_gone(self) -> None:
        # Check the class and the module: the wx stub makes missing instance attributes look present.
        self.assertFalse(hasattr(gui.BrailleFrame, "on_open_text_processing"))
        for name in ("TextProcessingDialog", "preprocessing_script_path"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(gui, name))

    def test_app_builds_runtime_and_passes_it_to_frame(self) -> None:
````

Edit: `client/tests/test_gui_document_flows.py`

````python
            "on_convert",
            "on_open_dual_view",
            "on_open_text_processing",
            "on_open_dictionary_management",
            "on_open_settings",
````

````python
            "on_convert",
            "on_open_dual_view",
            "on_open_script_management",
            "on_open_dictionary_management",
            "on_open_settings",
````

Edit: `client/tests/test_gui_document_flows.py`

````python
                ("menu3", "Append", -1, "T[Dual View]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_dual_view, "menu3:T[Dual View]"),
                ("menu3", "Append", -1, "T[Text Processing]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_text_processing, "menu3:T[Text Processing]"),
                ("menu3", "Append", -1, "T[Dictionary Management...]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_dictionary_management, "menu3:T[Dictionary Management...]"),
````

````python
                ("menu3", "Append", -1, "T[Dual View]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_dual_view, "menu3:T[Dual View]"),
                ("menu3", "Append", -1, "T[Script Management...]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_script_management, "menu3:T[Script Management...]"),
                ("menu3", "Append", -1, "T[Dictionary Management...]"),
                ("frame", "Bind", "EVT_MENU", frame.on_open_dictionary_management, "menu3:T[Dictionary Management...]"),
````

Edit: `client/tests/test_gui_document_flows.py`

````python
        self.assertEqual(dialog.snapshot.view, ViewSettings(13, "light", "simbraille"))

    def test_an_open_text_processing_dialog_is_left_alone(self) -> None:
        frame = self.make_frame()
        text_dialog = Mock()
        with (
            patch.object(gui.TextProcessingDialog, "_instance", text_dialog),
            self.open_dialog(None),
            patch.object(gui, "save_view_settings", return_value=None) as save,
        ):
            frame.on_editor_mousewheel(self.wheel(120))

        save.assert_called_once_with(frame._config_store, ViewSettings(13, "dark", "default"))
        self.assertEqual(text_dialog.mock_calls, [])


````

````python
        self.assertEqual(dialog.snapshot.view, ViewSettings(13, "light", "simbraille"))



````

Edit: `client/tests/test_i18n.py`

````python
        translated = [translation.gettext(label) for label in labels]

        self.assertEqual(
            translated,
            ["放棄變更", "返回編輯", "移除並儲存", "返回編輯"],
        )
        self.assertEqual([label for label in labels + translated if "&" in label], [])
````

````python
        translated = [translation.gettext(label) for label in labels]

        # F-18 (D9): the script editor asks before discarding changes, as the dictionary editor does.
        self.assertEqual(
            translated,
            ["放棄變更", "返回編輯", "移除並儲存", "返回編輯", "放棄變更", "返回編輯"],
        )
        self.assertEqual([label for label in labels + translated if "&" in label], [])
````

Edit: `client/tests/test_i18n.py`

````python
        "Settings",
        "Dictionary Management...",
        "Text Processing",
        "Text Processing Python Code",
        "Unable to open text processing script: {error}",
        "Unable to save text processing script: {error}",
        "Text processing failed: {error}",
        "The script must define exactly one top-level synchronous main function.",
````

````python
        "Settings",
        "Dictionary Management...",
        # F-18 removed the Text Processing dialog and its four strings.
        "Text processing failed: {error}",
        "The script must define exactly one top-level synchronous main function.",
````

Edit: `client/tests/test_i18n.py`

````python
                        extracted.add(node.args[0].value)

        self.assertEqual(len(self.FORMER_MARKER_MSGIDS), 44)
        self.assertEqual(sorted(set(self.FORMER_MARKER_MSGIDS) - extracted), [])

````

````python
                        extracted.add(node.args[0].value)

        self.assertEqual(len(self.FORMER_MARKER_MSGIDS), 40)
        self.assertEqual(sorted(set(self.FORMER_MARKER_MSGIDS) - extracted), [])

````

File: `client/tests/test_script_dialogs.py`

````python
"""The wx dialogs of Script Management (F-18 D7, D8, D9), against the wx stubs.

``ScriptManagementDialog`` is built without its native window (``object.__new__``) and fake
list, reason and button widgets, as ``test_dictionary_management_dialog`` builds its twin;
``ScriptEditorDialog`` is built for real against a namespace of fake widgets and distinct
power-of-two flags.
"""

import os
import tempfile
import types
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

from i18n import _
from tests import wx_stub
from tests.file_log_isolation import isolate_file_logs
from tests.windows_file_handles import hold_open

dialog, _DIALOG_SCOPE = wx_stub.load_speech_dialog()
LOGGER = "dotexpress.gui"


def setUpModule():
	_DIALOG_SCOPE.activate()
	# A script that cannot be read is logged to dotexpress.gui (gui.log).
	unittest.addModuleCleanup(isolate_file_logs(LOGGER))


tearDownModule = _DIALOG_SCOPE.deactivate

UPPER = b"def main(text: str) -> str:\n    return text.upper()\n"
NOT_UTF8 = "def main(text):\n    return text + '臺'\n".encode("cp950")
CANNOT_OPEN = "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。"


class _FakeListCtrl:
	def __init__(self, width: int = 500):
		self.item_count = 0
		self.selected = -1
		self.focused = -1
		self.width = width
		self.column_widths = {}
		self.calls = []

	def SetItemCount(self, count):
		self.item_count = count

	def Refresh(self):
		pass

	def GetFirstSelected(self):
		return self.selected

	def Select(self, index, on=True):
		self.selected = index if on else -1

	def Focus(self, index):
		self.focused = index

	def SetFocus(self):
		self.calls.append("SetFocus")

	def GetClientSize(self):
		return types.SimpleNamespace(width=self.width)

	def GetTextExtent(self, text):
		return (len(text) * 8, 16)

	def SetColumnWidth(self, column, width):
		self.column_widths[column] = width


class _FakeControl:
	"""The reason label or field: records what the dialog does."""

	def __init__(self):
		self.shown = False
		self.value = ""
		self.calls = []

	def Show(self, show=True):
		self.shown = show

	def ChangeValue(self, value):
		self.value = value

	def SelectAll(self):
		self.calls.append("SelectAll")


class _FakeActions:
	"""Stands in for the presenter: fixed names, scripted results, recorded calls."""

	def __init__(self, script_dir, names, results=None):
		self.script_dir = Path(script_dir)
		self.script_names = list(names)
		self.results = dict(results or {})
		self.calls = []

	def script_path(self, name):
		return self.script_dir / f"{name}.py"

	def _record(self, action, *args):
		self.calls.append((action, *args))
		return self.results.get(action)

	def add(self, view):
		return self._record("add", view)

	def edit(self, view, name):
		return self._record("edit", view, name)

	def delete(self, view, name):
		return self._record("delete", view, name)

	def rename(self, view, name):
		return self._record("rename", view, name)

	def import_from_file(self, view):
		return self._record("import", view)

	def export_to_file(self, view, name):
		return self._record("export", view, name)


class ManagementTestCase(unittest.TestCase):
	def setUp(self):
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.script_dir = Path(temp_dir.name)

	def write(self, name, data=UPPER):
		path = self.script_dir / f"{name}.py"
		path.write_bytes(data)
		return path

	def make_dialog(self, names, actions=None):
		target = object.__new__(dialog.ScriptManagementDialog)
		target._actions = actions if actions is not None else _FakeActions(self.script_dir, names)
		target._script_names = list(names)
		target._script_checks = {}
		target._selected_name = names[0] if names else ""
		target.list_ctrl = _FakeListCtrl()
		for name in ("add", "delete", "rename", "edit", "import", "export"):
			setattr(target, f"{name}_button", Mock())
		target.problem_label = _FakeControl()
		target.problem_ctrl = _FakeControl()
		target.Layout = Mock()
		return target

	def rows(self, target):
		return [[target._get_item_text(row, column) for column in (0, 1)] for row in range(target.list_ctrl.item_count)]

	def select(self, target, index):
		target.list_ctrl.selected = index
		target._on_selection_changed(Mock())


class ScriptListTest(ManagementTestCase):
	def test_no_processing_is_shown_translated_and_ready_without_reading_its_file(self):
		# F-18 (D4): conversion never reads no-processing.py, so its bytes do not matter.
		self.write("no-processing", b"def main(:\n")
		target = self.make_dialog(["no-processing"])

		with patch.object(dialog, "read_script_status", wraps=dialog.read_script_status) as read:
			target.refresh_scripts(["no-processing"], "no-processing")

		read.assert_not_called()
		self.assertEqual(self.rows(target), [["不處理", "可使用"]])
		self.assertFalse(target.problem_ctrl.shown)

	def test_each_script_shows_its_status(self):
		# F-18 (D7, O6): Ready, Unreadable, Not Valid.
		self.write("upper")
		self.write("cp950", NOT_UTF8)
		self.write("bad", b"def main(:\n")
		self.write("two", b"def main(a, b):\n    return a\n")
		names = ["no-processing", "bad", "cp950", "two", "upper"]
		target = self.make_dialog(names)

		with self.assertLogs(LOGGER, "ERROR") as logs:
			target.refresh_scripts(names, "no-processing")

		self.assertEqual(
			self.rows(target),
			[["不處理", "可使用"], ["bad", "格式不正確"], ["cp950", "無法讀取"], ["two", "格式不正確"], ["upper", "可使用"]],
		)
		# Only the read error is logged; invalid code is the user's content.
		self.assertEqual(len(logs.records), 1)
		self.assertIn('"cp950.py"', logs.output[0])

	def test_the_reason_row_says_why_and_selects_its_text(self):
		self.write("upper")
		self.write("two", b"def main(a, b):\n    return a\n")
		self.write("cp950", NOT_UTF8)
		names = ["no-processing", "cp950", "two", "upper"]
		target = self.make_dialog(names)
		with self.assertLogs(LOGGER, "ERROR"):
			target.refresh_scripts(names, "two")

		self.assertEqual(target.problem_ctrl.value, "main 必須恰好定義一個位置參數，且不得有其他參數。")
		self.assertEqual((target.problem_label.shown, target.problem_ctrl.shown), (True, True))
		self.assertEqual(target.problem_ctrl.calls, ["SelectAll"])

		self.select(target, 1)
		self.assertEqual(target.problem_ctrl.value, "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。")

		self.select(target, 3)
		self.assertEqual((target.problem_ctrl.value, target.problem_ctrl.shown, target.problem_label.shown), ("", False, False))

	def test_the_active_script_is_selected_and_focused(self):
		self.write("alpha")
		self.write("upper")
		names = ["no-processing", "alpha", "upper"]
		target = self.make_dialog(names)

		target.refresh_scripts(names, "upper")

		self.assertEqual((target.list_ctrl.selected, target.list_ctrl.focused), (2, 2))

		target.refresh_scripts(names, "gone")
		self.assertEqual(target.list_ctrl.selected, 0)

	@unittest.skipUnless(os.name == "nt", "Windows sharing modes")
	def test_a_locked_and_a_broken_script_do_not_stop_the_dialog(self):
		# F-18 (D-G): the GUI item 160 case.
		locked = self.write("locked")
		self.write("broken", b"def main(text)\n    return text\n")
		hold_open(self, locked, 0)
		names = ["no-processing", "broken", "locked"]
		target = self.make_dialog(names)

		with self.assertLogs(LOGGER, "ERROR"):
			target.refresh_scripts(names, "locked")

		self.assertEqual(self.rows(target), [["不處理", "可使用"], ["broken", "格式不正確"], ["locked", "無法讀取"]])
		self.assertEqual(target.problem_ctrl.value, CANNOT_OPEN)


class ScriptButtonsTest(ManagementTestCase):
	def enabled(self, target):
		return {
			name: getattr(target, f"{name}_button").Enable.call_args.args[0]
			for name in ("add", "delete", "rename", "edit", "import", "export")
		}

	def test_no_processing_can_only_be_exported_and_a_user_script_everything(self):
		# F-18 (D7): Edit too is disabled for No Processing.
		self.write("upper")
		names = ["no-processing", "upper"]
		target = self.make_dialog(names)

		target.refresh_scripts(names, "no-processing")
		self.assertEqual(
			self.enabled(target),
			{"add": True, "delete": False, "rename": False, "edit": False, "import": True, "export": True},
		)

		self.select(target, 1)
		self.assertEqual(
			self.enabled(target),
			{"add": True, "delete": True, "rename": True, "edit": True, "import": True, "export": True},
		)


class ScriptHandlersTest(ManagementTestCase):
	def setUp(self):
		super().setUp()
		for name in ("upper", "shout"):
			self.write(name)
		self.names = ["no-processing", "shout", "upper"]

	def test_edit_runs_the_action_then_refreshes_and_focuses_the_list(self):
		# F-18 (D8.2, O4): the dialog stays open; the status is read again.
		actions = _FakeActions(self.script_dir, self.names, {"edit": "upper"})
		target = self.make_dialog(self.names, actions)
		target.refresh_scripts(self.names, "upper")
		self.write("upper", b"def main(:\n")

		target._on_edit_clicked(Mock())

		self.assertEqual(actions.calls, [("edit", target, "upper")])
		self.assertEqual(self.rows(target)[2], ["upper", "格式不正確"])
		self.assertEqual(target.list_ctrl.calls, ["SetFocus"])

	def test_add_delete_rename_and_import_refresh_with_the_name_they_return(self):
		for action, handler, selected in (
			("add", "_on_add_clicked", None),
			("delete", "_on_delete_clicked", "upper"),
			("rename", "_on_rename_clicked", "upper"),
			("import", "_on_import_clicked", None),
		):
			with self.subTest(action=action):
				actions = _FakeActions(self.script_dir, self.names, {action: "shout"})
				target = self.make_dialog(self.names, actions)
				target.refresh_scripts(self.names, "upper")

				getattr(target, handler)(Mock())

				expected = (action, target, selected) if selected else (action, target)
				self.assertEqual(actions.calls, [expected])
				self.assertEqual(target.list_ctrl.selected, 1)
				self.assertEqual(target.list_ctrl.calls, ["SetFocus"] if action == "add" else [])

	def test_nothing_is_refreshed_when_an_action_returns_none_and_export_returns_nothing(self):
		actions = _FakeActions(self.script_dir, self.names)
		target = self.make_dialog(self.names, actions)
		target.refresh_scripts(self.names, "upper")
		target.refresh_scripts = Mock()

		for handler in ("_on_add_clicked", "_on_edit_clicked", "_on_delete_clicked", "_on_rename_clicked", "_on_import_clicked", "_on_export_clicked"):
			getattr(target, handler)(Mock())

		target.refresh_scripts.assert_not_called()
		self.assertEqual(actions.calls[-1], ("export", target, "upper"))


class ScriptViewTest(ManagementTestCase):
	def test_delete_asks_in_a_system_yes_no_box_with_no_as_default(self):
		target = self.make_dialog(["no-processing"])
		with patch.object(dialog, "message_box", return_value=dialog.wx.YES) as box:
			self.assertTrue(target.confirm("要刪除腳本「upper」嗎？", "確認刪除腳本"))

		box.assert_called_once_with(
			"要刪除腳本「upper」嗎？",
			"確認刪除腳本",
			dialog.wx.YES_NO | dialog.wx.NO_DEFAULT | dialog.wx.ICON_WARNING,
			parent=target,
		)

	def test_boxes_belong_to_the_dialog(self):
		target = self.make_dialog(["no-processing"])
		with patch.object(dialog, "message_box") as box:
			target.show_error("e")
			target.show_info("i")

		self.assertEqual(
			[call.args + (call.kwargs["parent"],) for call in box.call_args_list],
			[
				("e", "錯誤", dialog.wx.OK | dialog.wx.ICON_ERROR, target),
				("i", "資訊", dialog.wx.OK | dialog.wx.ICON_INFORMATION, target),
			],
		)

	def test_the_file_dialogs_offer_python_files(self):
		target = self.make_dialog(["no-processing"])
		created = []

		class FileDialog:
			def __init__(self, *args, **kwargs):
				created.append((args, kwargs))

			def __enter__(self):
				return self

			def __exit__(self, *_exc):
				return False

			def ShowModal(self):
				return dialog.wx.ID_OK

			def GetPath(self):
				return "C:/in/upper.py"

		with patch.object(dialog.wx, "FileDialog", FileDialog, create=True):
			self.assertEqual(target.choose_import_path("匯入腳本"), Path("C:/in/upper.py"))
			self.assertEqual(target.choose_export_path("匯出腳本", "upper.py"), Path("C:/in/upper.py"))

		self.assertEqual(
			created,
			[
				((target, "匯入腳本"), {"wildcard": "Python 檔案 (*.py)|*.py", "style": dialog.wx.FD_OPEN}),
				(
					(target, "匯出腳本"),
					{
						"defaultFile": "upper.py",
						"wildcard": "Python 檔案 (*.py)|*.py",
						"style": dialog.wx.FD_SAVE | dialog.wx.FD_OVERWRITE_PROMPT,
					},
				),
			],
		)

	def test_the_name_prompt_and_the_editor_open_over_the_dialog(self):
		target = self.make_dialog(["no-processing"])
		name_dialog = Mock()
		name_dialog.__enter__ = Mock(return_value=name_dialog)
		name_dialog.__exit__ = Mock(return_value=False)
		name_dialog.ShowModal.return_value = dialog.wx.ID_OK
		name_dialog.get_script_name.return_value = "upper"
		editor = Mock()
		editor.__enter__ = Mock(return_value=editor)
		editor.__exit__ = Mock(return_value=False)
		save = Mock()

		with (
			patch.object(dialog, "ScriptNameDialog", return_value=name_dialog) as name_class,
			patch.object(dialog, "ScriptEditorDialog", return_value=editor) as editor_class,
		):
			self.assertEqual(target.prompt_script_name("新增腳本", "x"), "upper")
			self.assertIsNone(target.edit_script("upper", "source", save))

		name_class.assert_called_once_with(target, "新增腳本", initial_name="x")
		editor_class.assert_called_once_with(target, script_name="upper", source="source", save=save)
		editor.ShowModal.assert_called_once_with()


class ScriptNameDialogTest(unittest.TestCase):
	def make(self, text):
		target = object.__new__(dialog.ScriptNameDialog)
		target.name_ctrl = Mock()
		target.name_ctrl.GetValue.return_value = text
		return target

	def test_each_refused_name_gets_its_message(self):
		cases = (
			("", "請輸入腳本名稱。"),
			("x" * 33, "腳本名稱長度需為 1 到 32 個字元。"),
			("a/b", "腳本名稱不是有效的 Windows 檔名。"),
			# F-18 (D4): the name as typed, not one fixed reserved name.
			(" 不處理", "腳本名稱「不處理」為保留名稱。"),
			("No-Processing", "腳本名稱「No-Processing」為保留名稱。"),
			("no processing", "腳本名稱「no processing」為保留名稱。"),
		)
		for text, message in cases:
			with self.subTest(text=text):
				target = self.make(text)
				event = Mock()
				with patch.object(dialog, "message_box") as box:
					target._on_ok(event)

				box.assert_called_once_with(message, "資訊", dialog.wx.OK | dialog.wx.ICON_INFORMATION, parent=target)
				event.Skip.assert_not_called()

	def test_a_valid_name_is_written_back_without_spaces(self):
		target = self.make(" 大寫")
		event = Mock()

		target._on_ok(event)

		target.name_ctrl.SetValue.assert_called_once_with("大寫")
		event.Skip.assert_called_once_with()


# --- the editor ----------------------------------------------------------------


FLAG_NAMES = (
	"DEFAULT_DIALOG_STYLE",
	"RESIZE_BORDER",
	"TE_MULTILINE",
	"TE_RICH2",
	"TE_DONTWRAP",
	"EXPAND",
	"ALL",
	"LEFT",
	"RIGHT",
	"BOTTOM",
	"OK",
	"CANCEL",
	"APPLY",
	"CLOSE",
	"ICON_ERROR",
	"VERTICAL",
)
FLAGS = types.SimpleNamespace(**{name: 1 << index for index, name in enumerate(FLAG_NAMES)})
ID_OK, ID_CANCEL, ID_APPLY, ID_CLOSE = 5100, 5101, 5102, 5103


class _Event:
	def __init__(self):
		self.skipped = False

	def Skip(self):
		self.skipped = True


class _FakeButton:
	def __init__(self, harness, button_id):
		self.harness = harness
		self.id = button_id
		self.label = None
		self.handlers = []

	def SetLabel(self, label):
		self.label = label

	def Bind(self, _event, handler):
		self.handlers.append(handler)

	def click(self):
		event = _Event()
		for handler in self.handlers:
			handler(event)
		return event.skipped


class _FakeEditor:
	"""Multi-line text control; like wxMSW it hands back its line ends as \\n."""

	def __init__(self, harness, value):
		self.harness = harness
		self.value = value.replace("\r\n", "\n")
		self.name = None
		self.font = Mock()
		self.insertion_point = None

	def GetValue(self):
		return self.value

	def SetName(self, name):
		self.name = name

	def GetFont(self):
		return self.font

	def SetFont(self, font):
		self.harness.log.append(("SetFont", font.SetFamily.call_args.args))

	def SetInsertionPoint(self, position):
		self.insertion_point = position

	def SetFocus(self):
		self.harness.log.append(("SetFocus", "editor"))
		self.harness.focus = self


class _EditorHarness:
	"""Builds the real ``ScriptEditorDialog`` against fake widgets and drives it."""

	def __init__(self, test, source="def main(text):\n    return text\n", save=None):
		self.log = []
		self.saved = []
		self.confirm_answers = []
		self.focus = None
		self.buttons = {button_id: _FakeButton(self, button_id) for button_id in (ID_OK, ID_CANCEL, ID_APPLY)}
		self.save = save if save is not None else self.saved.append
		stack = ExitStack()
		test.addCleanup(stack.close)
		wx = types.SimpleNamespace(
			**vars(FLAGS),
			ID_OK=ID_OK,
			ID_CANCEL=ID_CANCEL,
			ID_APPLY=ID_APPLY,
			ID_CLOSE=ID_CLOSE,
			EVT_BUTTON="EVT_BUTTON",
			FONTFAMILY_TELETYPE="TELETYPE",
			Window=types.SimpleNamespace(FindFocus=lambda: self.focus),
			BoxSizer=lambda _orientation: Mock(),
			TextCtrl=self._text_ctrl,
		)
		harness = self

		def base_init(_dialog, parent, title=None, style=None):
			harness.log.append(("Dialog.__init__", parent, title, style))

		# The stub's wx.Dialog under the editor; looked up here, so that the module loads before the class exists.
		native_base = next(base for base in dialog.ScriptEditorDialog.__mro__ if base.__name__ == "Dialog")
		stack.enter_context(patch.object(native_base, "__init__", base_init, create=True))
		stack.enter_context(patch.object(dialog, "wx", wx))
		stack.enter_context(patch.object(dialog, "message_box", self._message_box))
		stack.enter_context(patch.object(dialog, "confirm_box", self._confirm_box))
		editor = object.__new__(dialog.ScriptEditorDialog)
		editor.CreateButtonSizer = lambda flags: self.log.append(("CreateButtonSizer", flags)) or Mock()
		editor.FindWindow = self.buttons.get
		editor.SetSizer = lambda _sizer: None
		editor.SetMinSize = lambda size: self.log.append(("SetMinSize", size))
		editor.SetSize = lambda size: self.log.append(("SetSize", size))
		editor.CentreOnParent = lambda: None
		editor.IsDescendant = lambda window: window is editor.__dict__.get("editor")
		editor.Destroy = lambda: self.log.append(("Destroy",))
		self.dialog = editor
		editor.__init__("parent", script_name="upper", source=source, save=self._save)
		# What the construction did; the log then records only what the test drives.
		self.built = list(self.log)
		self.log.clear()

	def _text_ctrl(self, _parent, value="", style=None):
		self.log.append(("TextCtrl", value, style))
		self.editor = _FakeEditor(self, value)
		return self.editor

	def _save(self, text):
		self.log.append(("save", text))
		self.save(text)

	def _message_box(self, message, caption, style, parent=None):
		self.log.append(("MessageBox", message, caption, style, parent))
		self.focus = "box button"

	def _confirm_box(self, message, caption, ok_label, cancel_label, parent=None):
		self.log.append(("ConfirmBox", message, caption, ok_label, cancel_label, parent))
		self.focus = "box button"
		return self.confirm_answers.pop(0)

	def type(self, text):
		self.editor.value = text


class ScriptEditorBuildTest(unittest.TestCase):
	def test_the_title_is_the_name_and_the_code_is_in_a_named_monospace_editor(self):
		# F-18 (D9, O9): the title names the script, so the editor is 「Python 程式碼」.
		source = "def main(text):\r\n    return text\r\n"
		harness = _EditorHarness(self, source=source)

		self.assertEqual(harness.built[0], ("Dialog.__init__", "parent", "upper", FLAGS.DEFAULT_DIALOG_STYLE | FLAGS.RESIZE_BORDER))
		self.assertEqual(harness.built[1], ("TextCtrl", source, FLAGS.TE_MULTILINE | FLAGS.TE_RICH2 | FLAGS.TE_DONTWRAP))
		self.assertIn(("SetFont", ("TELETYPE",)), harness.built)
		self.assertIn(("CreateButtonSizer", FLAGS.OK | FLAGS.CANCEL | FLAGS.APPLY), harness.built)
		self.assertEqual(harness.built[-3:], [("SetMinSize", (520, 300)), ("SetSize", (720, 440)), ("SetFocus", "editor")])
		self.assertEqual(harness.editor.name, "Python 程式碼")
		self.assertEqual(harness.editor.insertion_point, 0)
		self.assertEqual([button.label for button in harness.buttons.values()], ["確定", "取消", "套用"])


class ScriptEditorSaveTest(unittest.TestCase):
	def test_apply_saves_the_text_and_keeps_the_dialog_open(self):
		harness = _EditorHarness(self)
		harness.type("def main(text):\n    return text.upper()\n")

		self.assertFalse(harness.buttons[ID_APPLY].click())

		self.assertEqual(harness.saved, ["def main(text):\n    return text.upper()\n"])
		self.assertEqual(harness.log, [("save", "def main(text):\n    return text.upper()\n")])

	def test_a_failed_save_is_explained_and_the_focus_goes_back_to_the_code(self):
		cases = (
			(
				ValueError("main must define exactly one positional parameter and no other parameters."),
				"儲存腳本失敗：main 必須恰好定義一個位置參數，且不得有其他參數。",
			),
			(SyntaxError("invalid syntax", ("upper.py", 1, 10, "def main(:\n")), "儲存腳本失敗：invalid syntax (upper.py, line 1)"),
			(FileExistsError("腳本「upper」已存在。"), "儲存腳本失敗：腳本「upper」已存在。"),
			(PermissionError(13, "Permission denied"), "儲存腳本失敗：[Errno 13] Permission denied"),
		)
		for error, message in cases:
			with self.subTest(error=type(error).__name__):
				harness = _EditorHarness(self, save=Mock(side_effect=error))
				harness.type("changed")

				self.assertFalse(harness.buttons[ID_OK].click())

				self.assertEqual(
					harness.log,
					[
						("save", "changed"),
						("MessageBox", message, "錯誤", FLAGS.OK | FLAGS.ICON_ERROR, harness.dialog),
						("SetFocus", "editor"),
					],
				)

	def test_ok_closes_after_a_successful_save(self):
		harness = _EditorHarness(self)
		harness.type("def main(text):\n    return text\n# changed\n")

		self.assertTrue(harness.buttons[ID_OK].click())
		self.assertEqual(harness.saved, ["def main(text):\n    return text\n# changed\n"])


class ScriptEditorCancelTest(unittest.TestCase):
	QUESTION = (
		"ConfirmBox",
		"要放棄對腳本「upper」所做的變更嗎？",
		"尚未儲存的變更",
		"放棄變更",
		"返回編輯",
	)

	def test_cancel_without_a_change_closes_without_asking_or_saving(self):
		# The template of an Add, unchanged, is no change either.
		for source in ("def main(input: str) -> str:\n    return input\n", "def main(text):\r\n    return text\r\n"):
			with self.subTest(source=source):
				harness = _EditorHarness(self, source=source)

				self.assertTrue(harness.buttons[ID_CANCEL].click())
				self.assertEqual(harness.log, [])

	def test_back_to_editing_keeps_the_dialog_and_the_focus(self):
		harness = _EditorHarness(self)
		harness.type("changed")
		harness.confirm_answers.append(False)

		self.assertFalse(harness.buttons[ID_CANCEL].click())

		self.assertEqual(harness.log, [(*self.QUESTION, harness.dialog), ("SetFocus", "editor")])
		self.assertEqual(harness.editor.value, "changed")

	def test_discard_changes_closes_without_saving(self):
		harness = _EditorHarness(self)
		harness.type("changed")
		harness.confirm_answers.append(True)

		self.assertTrue(harness.buttons[ID_CANCEL].click())

		self.assertEqual(harness.log, [(*self.QUESTION, harness.dialog)])
		self.assertEqual(harness.saved, [])

	def test_after_a_successful_apply_cancel_closes_without_asking(self):
		harness = _EditorHarness(self)
		harness.type("def main(text):\n    return text.upper()\n")
		harness.buttons[ID_APPLY].click()
		harness.log.clear()

		self.assertTrue(harness.buttons[ID_CANCEL].click())
		self.assertEqual(harness.log, [])

	def test_after_a_failed_apply_cancel_still_asks(self):
		harness = _EditorHarness(self, save=Mock(side_effect=SyntaxError("bad")))
		harness.type("def main(:\n")
		harness.buttons[ID_APPLY].click()
		harness.log.clear()
		harness.focus = harness.editor
		harness.confirm_answers.append(True)

		self.assertTrue(harness.buttons[ID_CANCEL].click())
		self.assertEqual(harness.log, [(*self.QUESTION, harness.dialog)])


if __name__ == "__main__":
	unittest.main()
````

Edit: `client/tests/test_settings_dialogs.py`

````python


class TextProcessingDialogTest(unittest.TestCase):
    def make_dialog(self):
        from settings.dialogs import TextProcessingDialog

        dialog = object.__new__(TextProcessingDialog)
        dialog.script_path = Path("dictionary/preprocessing.py")
        dialog.editor = Mock()
        dialog.Destroy = Mock()
        return dialog

    def test_initial_size_title_and_accessible_editor_name(self) -> None:
        from settings.dialogs import TextProcessingDialog

        with (
            patch(
                "settings.dialogs.load_preprocessing_script",
                return_value="def main(text):\n    return text\n",
            ),
            patch("settings.dialogs._", side_effect=lambda text: text),
        ):
            dialog = TextProcessingDialog(
                None,
                script_path=Path("dictionary/preprocessing.py"),
            )

        self.assertEqual(dialog.size, (720, 440))
        self.assertEqual(dialog.title, "Text Processing")
        self.assertEqual(dialog.editor.GetName(), "Text Processing Python Code")

    def test_apply_saves_editor_source(self) -> None:
        dialog = self.make_dialog()
        dialog.editor.GetValue.return_value = "def main(text):\n    return text\n"
        with patch("settings.dialogs.save_preprocessing_script") as save:
            self.assertTrue(dialog.on_apply())
        save.assert_called_once_with(dialog.script_path, dialog.editor.GetValue.return_value)

    def test_apply_failure_keeps_dialog_open_and_focuses_editor(self) -> None:
        dialog = self.make_dialog()
        dialog.editor.GetValue.return_value = "def main(:\n"
        with (
            patch(
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
        dialog.on_apply = Mock(return_value=True)
        dialog._destroy = Mock()
        dialog.on_ok()
        dialog._destroy.assert_called_once_with()

    def test_cancel_does_not_save(self) -> None:
        dialog = self.make_dialog()
        dialog._destroy = Mock()
        with patch("settings.dialogs.save_preprocessing_script") as save:
            dialog.on_cancel()
        save.assert_not_called()
        dialog._destroy.assert_called_once_with()

    def test_show_singleton_reuses_live_dialog(self) -> None:
        from settings.dialogs import TextProcessingDialog

        existing = Mock()
        original = TextProcessingDialog._instance
        TextProcessingDialog._instance = existing
        try:
            result = TextProcessingDialog.show_singleton(
                parent=Mock(),
                script_path=Path("dictionary/preprocessing.py"),
            )
        finally:
            TextProcessingDialog._instance = original

        self.assertIs(result, existing)
        existing.Iconize.assert_called_once_with(False)
        existing.Raise.assert_called_once_with()
        existing.SetFocus.assert_called_once_with()

    def test_show_singleton_reraises_unexpected_existing_dialog_error(self) -> None:
        from settings.dialogs import TextProcessingDialog

        existing = Mock()
        existing.Iconize.side_effect = RuntimeError("unexpected")
        original = TextProcessingDialog._instance
        TextProcessingDialog._instance = existing
        try:
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                TextProcessingDialog.show_singleton(
                    parent=Mock(),
                    script_path=Path("dictionary/preprocessing.py"),
                )
            self.assertIs(TextProcessingDialog._instance, existing)
        finally:
            TextProcessingDialog._instance = original


````

````python


class TextProcessingDialogRemovedTest(unittest.TestCase):
    def test_the_text_processing_dialog_is_gone(self) -> None:
        # F-18 (D11): Script Management (dialog.py) replaces it.
        from settings import dialogs

        self.assertFalse(hasattr(dialogs, "TextProcessingDialog"))


````

Edit: `client/tests/test_settings_dialogs.py`

````python


class TextProcessingSingletonTest(_SingletonCharacterization, unittest.TestCase):
    def dialog_class(self):
        from settings.dialogs import TextProcessingDialog

        return TextProcessingDialog

    def show_kwargs(self) -> dict:
        return {"parent": "parent-window", "script_path": "dictionary/preprocessing.py"}


class DotExpressSettingsSingletonTest(_SingletonCharacterization, unittest.TestCase):
    def setUp(self) -> None:
````

````python


class DotExpressSettingsSingletonTest(_SingletonCharacterization, unittest.TestCase):
    def setUp(self) -> None:
````

Edit: `client/tests/test_settings_dialogs.py`

````python
        self.assertEqual(existing.mock_calls, [])
        self.assertEqual(events, [])


class SingletonSlotIndependenceTest(unittest.TestCase):
    def test_the_two_singleton_dialogs_keep_separate_slots(self) -> None:
        from settings.dialogs import DotExpressSettingsDialog, TextProcessingDialog

        text_dialog = Mock()
        settings_dialog = object.__new__(DotExpressSettingsDialog)
        settings_dialog.Destroy = Mock()
        with (
            patch.object(TextProcessingDialog, "_instance", text_dialog),
            patch.object(DotExpressSettingsDialog, "_instance", settings_dialog),
        ):
            self.assertIs(
                TextProcessingDialog.show_singleton(parent=None, script_path="dictionary/preprocessing.py"),
                text_dialog,
            )
            settings_dialog._destroy()
            self.assertIsNone(DotExpressSettingsDialog._instance)
            self.assertIs(TextProcessingDialog._instance, text_dialog)

        settings_dialog.Destroy.assert_called_once_with()


````

````python
        self.assertEqual(existing.mock_calls, [])
        self.assertEqual(events, [])


````

Edit: `client/tests/test_text_scripts_presenter.py`

````python

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import text_scripts.presenter as presenter_module
from text_scripts.presenter import ScriptManagementPresenter

PRESENTER_PATH = Path(presenter_module.__file__)
UPPER = "def main(text: str) -> str:\n    return text.upper()\n"


````

````python

import ast
import os
import tempfile
import unittest
from pathlib import Path
from typing import Protocol
from unittest.mock import Mock, patch

import text_scripts.presenter as presenter_module
from conversion.preprocessing.user_script import NO_PROCESSING_SCRIPT
from tests.file_log_isolation import isolate_file_logs
from text_scripts.presenter import ScriptManagementPresenter

PRESENTER_PATH = Path(presenter_module.__file__)
UPPER = "def main(text: str) -> str:\n    return text.upper()\n"


def setUpModule():
	# An Edit of a script that cannot be read logs to dotexpress.gui (gui.log).
	unittest.addModuleCleanup(isolate_file_logs("dotexpress.gui"))


````

Edit: `client/tests/test_text_scripts_presenter.py`

````python
		self.script_dir.mkdir(parents=True, exist_ok=True)
		path = self.script_dir / f"{name}.py"
		path.write_text(source, encoding="utf-8")
		return path

````

````python
		self.script_dir.mkdir(parents=True, exist_ok=True)
		path = self.script_dir / f"{name}.py"
		path.write_bytes(source.encode("utf-8"))
		return path

````

Edit: `client/tests/test_text_scripts_presenter.py`

````python

		self.assertNotIn("wx", imported)


````

````python

		self.assertNotIn("wx", imported)

	def test_view_and_actions_are_protocols(self):
		for name in ("ScriptManagementView", "ScriptManagementActions"):
			with self.subTest(name=name):
				self.assertIn(Protocol, getattr(presenter_module, name).__bases__)

	def test_presenter_provides_every_action(self):
		for name in ("script_names", "script_path", "add", "edit", "delete", "rename", "import_from_file", "export_to_file"):
			with self.subTest(name=name):
				self.assertTrue(hasattr(presenter_module.ScriptManagementActions, name))
				self.assertTrue(hasattr(ScriptManagementPresenter, name))


````

Edit: `client/tests/test_text_scripts_presenter.py`

````python


if __name__ == "__main__":
	unittest.main()
````

````python


class FakeView:
	"""Records every view call in order and answers from scripted values.

	``edits`` holds one entry per editor: the texts saved in turn (a failed save is recorded
	with its error), or a function that gets ``save``.
	"""

	def __init__(self, *, names=(), confirm=True, import_path=None, export_path=None, edits=()):
		self.calls = []
		self._names = list(names)
		self._confirm = confirm
		self._import_path = import_path
		self._export_path = export_path
		self._edits = list(edits)

	def prompt_script_name(self, title, initial_name):
		self.calls.append(("prompt", title, initial_name))
		return self._names.pop(0)

	def edit_script(self, title, source, save):
		self.calls.append(("edit", title, source))
		edit = self._edits.pop(0)
		if callable(edit):
			edit(save)
			return
		for text in edit:
			try:
				save(text)
			except (OSError, SyntaxError, ValueError) as error:
				self.calls.append(("save failed", type(error).__name__, str(error)))
			else:
				self.calls.append(("saved", text))

	def show_info(self, message):
		self.calls.append(("info", message))

	def show_error(self, message):
		self.calls.append(("error", message))

	def confirm(self, message, caption):
		self.calls.append(("confirm", message, caption))
		return self._confirm

	def choose_import_path(self, title):
		self.calls.append(("choose_import", title))
		return self._import_path

	def choose_export_path(self, title, default_file):
		self.calls.append(("choose_export", title, default_file))
		return self._export_path


SHOUT = "def main(text):\n    return text.upper() + '!'\n"
NOT_UTF8 = "def main(text):\n    return text + '臺'\n".encode("cp950")
NOT_UTF8_REASON = "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"


class PresenterAddTest(PresenterTestCase):
	def test_add_asks_a_name_then_opens_the_template_and_writes_nothing_without_a_save(self):
		# F-18 (D8.1): Cancel in the editor creates nothing.
		presenter = self.make_presenter()
		view = FakeView(names=["upper"], edits=[[]])

		self.assertIsNone(presenter.add(view))

		self.assertEqual(view.calls, [("prompt", "新增腳本", ""), ("edit", "upper", NO_PROCESSING_SCRIPT)])
		self.assertEqual(self.files(), ["no-processing.py"])
		self.assertEqual(presenter.script_names, ["no-processing"])

	def test_the_first_save_creates_the_file_and_the_next_one_replaces_it(self):
		presenter = self.make_presenter()
		view = FakeView(names=[" upper"], edits=[[UPPER, SHOUT]])

		self.assertEqual(presenter.add(view), "upper")

		self.assertEqual(view.calls[1:], [("edit", "upper", NO_PROCESSING_SCRIPT), ("saved", UPPER), ("saved", SHOUT)])
		self.assertEqual((self.script_dir / "upper.py").read_text(encoding="utf-8"), SHOUT)
		self.assertEqual(presenter.script_names, ["no-processing", "upper"])
		self.set_active_name.assert_not_called()

	def test_an_invalid_save_writes_nothing(self):
		presenter = self.make_presenter()
		view = FakeView(names=["upper"], edits=[["def main(a, b):\n    return a\n", UPPER]])

		presenter.add(view)

		self.assertEqual(
			view.calls[2],
			("save failed", "ValueError", "main must define exactly one positional parameter and no other parameters."),
		)
		self.assertEqual(view.calls[3], ("saved", UPPER))
		self.assertEqual(self.files(), ["no-processing.py", "upper.py"])

	def test_a_taken_name_asks_again(self):
		presenter = self.make_presenter("upper")
		view = FakeView(names=["Upper", "shout"], edits=[[]])

		presenter.add(view)

		self.assertEqual(
			view.calls,
			[
				("prompt", "新增腳本", ""),
				("error", "腳本「Upper」已存在。"),
				("prompt", "新增腳本", "Upper"),
				("edit", "shout", NO_PROCESSING_SCRIPT),
			],
		)

	def test_a_file_written_meanwhile_fails_the_first_save_and_is_kept(self):
		presenter = self.make_presenter()

		def edit(save):
			self.write_script("upper", "KEEP")
			with self.assertRaises(FileExistsError) as raised:
				save(UPPER)
			self.assertEqual(str(raised.exception), "腳本「upper」已存在。")

		self.assertIsNone(presenter.add(FakeView(names=["upper"], edits=[edit])))
		self.assertEqual((self.script_dir / "upper.py").read_text(encoding="utf-8"), "KEEP")

	def test_a_cancelled_name_opens_no_editor(self):
		presenter = self.make_presenter()
		view = FakeView(names=[None])

		self.assertIsNone(presenter.add(view))
		self.assertEqual(view.calls, [("prompt", "新增腳本", "")])


class PresenterEditTest(PresenterTestCase):
	def test_edit_opens_the_text_of_the_file_and_saves_it(self):
		presenter = self.make_presenter("upper", active="upper")
		(self.script_dir / "upper.py").write_bytes(b"\xef\xbb\xbf" + UPPER.encode("utf-8"))
		view = FakeView(edits=[[SHOUT]])

		self.assertEqual(presenter.edit(view, "upper"), "upper")

		self.assertEqual(view.calls, [("edit", "upper", UPPER), ("saved", SHOUT)])
		self.assertEqual((self.script_dir / "upper.py").read_bytes(), SHOUT.encode("utf-8"))
		self.set_active_name.assert_not_called()

	def test_an_invalid_script_opens_so_that_it_can_be_fixed(self):
		presenter = self.make_presenter()
		self.write_script("bad", "def main(:\n")
		presenter.refresh()
		view = FakeView(edits=[[]])

		presenter.edit(view, "bad")

		self.assertEqual(view.calls, [("edit", "bad", "def main(:\n")])

	def test_a_script_that_cannot_be_read_is_explained_and_not_opened(self):
		presenter = self.make_presenter()
		(self.script_dir / "cp950.py").write_bytes(NOT_UTF8)
		view = FakeView()

		with self.assertLogs("dotexpress.gui", "ERROR"):
			self.assertEqual(presenter.edit(view, "cp950"), "cp950")

		self.assertEqual(view.calls, [("error", f"無法讀取腳本「cp950」。\n\n{NOT_UTF8_REASON}")])

	def test_no_processing_is_not_edited(self):
		presenter = self.make_presenter()
		view = FakeView()

		self.assertIsNone(presenter.edit(view, "no-processing"))
		self.assertEqual(view.calls, [])


class PresenterDeleteTest(PresenterTestCase):
	def test_delete_asks_first_and_selects_the_script_above(self):
		presenter = self.make_presenter("alpha", "beta", "gamma")
		view = FakeView(confirm=True)

		self.assertEqual(presenter.delete(view, "beta"), "alpha")

		self.assertEqual(view.calls, [("confirm", "要刪除腳本「beta」嗎？", "確認刪除腳本")])
		self.assertEqual(self.files(), ["alpha.py", "gamma.py", "no-processing.py"])
		self.set_active_name.assert_not_called()

	def test_no_keeps_the_file(self):
		presenter = self.make_presenter("alpha")

		self.assertIsNone(presenter.delete(FakeView(confirm=False), "alpha"))
		self.assertEqual(self.files(), ["alpha.py", "no-processing.py"])

	def test_deleting_the_active_script_makes_no_processing_active(self):
		# F-18 (O5): not the neighbour, which would start running another script.
		presenter = self.make_presenter("alpha", "beta", active="beta")

		self.assertEqual(presenter.delete(FakeView(), "beta"), "alpha")

		self.set_active_name.assert_called_once_with("no-processing")
		self.assertEqual(self.active, ["no-processing"])

	def test_the_first_user_script_selects_no_processing_after_its_delete(self):
		presenter = self.make_presenter("alpha", active="alpha")

		self.assertEqual(presenter.delete(FakeView(), "alpha"), "no-processing")
		self.assertEqual(self.active, ["no-processing"])

	def test_a_failed_delete_is_reported(self):
		presenter = self.make_presenter("alpha", active="alpha")
		error = PermissionError(13, "Permission denied")

		with patch.object(presenter_module, "delete_script", side_effect=error):
			view = FakeView()
			self.assertIsNone(presenter.delete(view, "alpha"))

		self.assertEqual(view.calls[-1], ("error", "無法刪除腳本：[Errno 13] Permission denied"))
		self.set_active_name.assert_not_called()

	def test_no_processing_is_not_deleted(self):
		presenter = self.make_presenter()
		view = FakeView()

		self.assertIsNone(presenter.delete(view, "no-processing"))
		self.assertEqual(view.calls, [])


class PresenterRenameTest(PresenterTestCase):
	def test_renaming_the_active_script_makes_the_new_name_active(self):
		presenter = self.make_presenter("upper", active="upper")
		view = FakeView(names=["shout"])

		self.assertEqual(presenter.rename(view, "upper"), "shout")

		self.assertEqual(view.calls, [("prompt", "重新命名腳本", "upper")])
		self.assertEqual(self.files(), ["no-processing.py", "shout.py"])
		self.set_active_name.assert_called_once_with("shout")

	def test_renaming_another_script_keeps_the_active_one(self):
		presenter = self.make_presenter("upper", "alpha", active="alpha")

		self.assertEqual(presenter.rename(FakeView(names=["shout"]), "upper"), "shout")
		self.set_active_name.assert_not_called()

	def test_a_taken_name_asks_again_and_the_same_name_changes_nothing(self):
		presenter = self.make_presenter("upper", "shout", active="upper")
		view = FakeView(names=["shout", "upper"])

		self.assertEqual(presenter.rename(view, "upper"), "upper")

		self.assertEqual(view.calls[1], ("error", "腳本「shout」已存在。"))
		self.assertEqual(self.files(), ["no-processing.py", "shout.py", "upper.py"])
		self.set_active_name.assert_not_called()

	@unittest.skipUnless(os.name == "nt", "case-insensitive file names")
	def test_a_case_only_rename_follows_the_active_script(self):
		presenter = self.make_presenter("upper", active="upper")

		self.assertEqual(presenter.rename(FakeView(names=["Upper"]), "upper"), "Upper")
		self.assertEqual(self.active, ["Upper"])

	def test_a_failed_rename_is_reported(self):
		presenter = self.make_presenter("upper", active="upper")

		with patch.object(presenter_module, "rename_script", side_effect=PermissionError(13, "Permission denied")):
			view = FakeView(names=["shout"])
			self.assertIsNone(presenter.rename(view, "upper"))

		self.assertEqual(view.calls[-1], ("error", "儲存腳本失敗：[Errno 13] Permission denied"))
		self.set_active_name.assert_not_called()


class PresenterImportTest(PresenterTestCase):
	def source(self, name, data):
		folder = self.root / "source"
		folder.mkdir(exist_ok=True)
		path = folder / name
		path.write_bytes(data)
		return path

	def test_import_asks_a_name_from_the_file_and_copies_its_bytes(self):
		presenter = self.make_presenter("alpha", active="alpha")
		data = b"\xef\xbb\xbf" + UPPER.replace("\n", "\r\n").encode("utf-8")
		view = FakeView(names=["upper2"], import_path=self.source("upper2.py", data))

		self.assertEqual(presenter.import_from_file(view), "upper2")

		self.assertEqual(view.calls, [("choose_import", "匯入腳本"), ("prompt", "新增腳本", "upper2")])
		self.assertEqual((self.script_dir / "upper2.py").read_bytes(), data)
		self.set_active_name.assert_not_called()

	def test_a_cancelled_file_dialog_does_nothing(self):
		presenter = self.make_presenter()
		view = FakeView()

		self.assertIsNone(presenter.import_from_file(view))
		self.assertEqual(view.calls, [("choose_import", "匯入腳本")])

	def test_each_error_is_reported_and_nothing_is_copied(self):
		cases = (
			("x.txt", UPPER.encode("utf-8"), "匯入腳本失敗：只能匯入 Python 檔案（.py）。"),
			("cp950.py", NOT_UTF8, f"匯入腳本失敗：{NOT_UTF8_REASON}"),
			("int.py", b"def main(x: int):\n    return x\n", "匯入腳本失敗：main 的參數只能標註為 str，或不加標註。"),
			("two.py", b"def main(a, b):\n    return a\n", "匯入腳本失敗：main 必須恰好定義一個位置參數，且不得有其他參數。"),
		)
		for name, data, message in cases:
			with self.subTest(name=name):
				presenter = self.make_presenter()
				view = FakeView(names=[Path(name).stem], import_path=self.source(name, data))

				self.assertIsNone(presenter.import_from_file(view))

				self.assertEqual(view.calls[-1], ("error", message))
				self.assertEqual(self.files(), ["no-processing.py"])

	def test_a_syntax_error_is_shown_as_python_gives_it(self):
		presenter = self.make_presenter()
		source = self.source("bad.py", b"def main(:\n")
		with self.assertRaises(SyntaxError) as raised:
			compile("def main(:\n", str(source), "exec")

		view = FakeView(names=["bad"], import_path=source)
		presenter.import_from_file(view)

		self.assertEqual(view.calls[-1], ("error", f"匯入腳本失敗：{raised.exception}"))
		self.assertEqual(self.files(), ["no-processing.py"])

	def test_a_source_that_cannot_be_opened_gets_the_reason(self):
		presenter = self.make_presenter()
		source = self.source("upper.py", UPPER.encode("utf-8"))
		view = FakeView(names=["upper"], import_path=source)

		with patch.object(Path, "read_bytes", side_effect=PermissionError(13, "denied")):
			presenter.import_from_file(view)

		self.assertEqual(
			view.calls[-1],
			("error", "匯入腳本失敗：無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。"),
		)

	def test_a_taken_name_asks_again(self):
		presenter = self.make_presenter("upper")
		view = FakeView(names=["upper", "upper2"], import_path=self.source("upper.py", SHOUT.encode("utf-8")))

		self.assertEqual(presenter.import_from_file(view), "upper2")

		self.assertEqual(view.calls[2:4], [("error", "腳本「upper」已存在。"), ("prompt", "新增腳本", "upper")])
		self.assertEqual((self.script_dir / "upper.py").read_text(encoding="utf-8"), UPPER)


class PresenterExportTest(PresenterTestCase):
	def test_export_suggests_the_file_name_and_copies(self):
		for name, expected in (("upper", UPPER.encode("utf-8")), ("no-processing", NO_PROCESSING_SCRIPT.encode("utf-8"))):
			with self.subTest(name=name):
				presenter = self.make_presenter("upper")
				destination = self.root / f"out-{name}.py"
				view = FakeView(export_path=destination)

				self.assertIsNone(presenter.export_to_file(view, name))

				self.assertEqual(view.calls, [("choose_export", "匯出腳本", f"{name}.py")])
				self.assertEqual(destination.read_bytes(), expected)

	def test_a_cancelled_or_failed_export(self):
		presenter = self.make_presenter("upper")
		view = FakeView()
		presenter.export_to_file(view, "upper")
		self.assertEqual(view.calls, [("choose_export", "匯出腳本", "upper.py")])

		folder = self.root / "folder.py"
		folder.mkdir()
		view = FakeView(export_path=folder)
		presenter.export_to_file(view, "upper")
		self.assertEqual(view.calls[-1][0], "error")
		self.assertTrue(view.calls[-1][1].startswith("匯出腳本失敗：[Errno "))


if __name__ == "__main__":
	unittest.main()
````

Edit: `client/tests/test_translation_menu.py`

````python
                ("convert", "Convert"),
                ("dual_view", "Dual View"),
                ("text_processing", "Text Processing"),
                ("dictionaries", "Dictionary Management..."),
                ("settings", "Settings"),
````

````python
                ("convert", "Convert"),
                ("dual_view", "Dual View"),
                ("scripts", "Script Management..."),
                ("dictionaries", "Dictionary Management..."),
                ("settings", "Settings"),
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
from unittest.mock import patch

from conversion.preprocessing.user_script import (
    DEFAULT_PREPROCESSING_SCRIPT,
    NO_PROCESSING_SCRIPT,
    NO_PROCESSING_SCRIPT_NAME,
    SCRIPT_SUFFIX,
    execute_script,
    load_preprocessing_script,
    preprocessing_script_path,
    read_script_source,
    save_script,
````

````python
from unittest.mock import patch

from conversion.preprocessing import user_script
from conversion.preprocessing.user_script import (
    NO_PROCESSING_SCRIPT,
    NO_PROCESSING_SCRIPT_NAME,
    SCRIPT_SUFFIX,
    execute_script,
    read_script_source,
    save_script,
````

Edit: `client/tests/test_user_preprocessing_script.py`

````python
        self.path = self.directory / "upper.py"

    def test_path_uses_dictionary_directory(self) -> None:
        self.assertEqual(preprocessing_script_path(self.directory), self.directory / "preprocessing.py")

    def test_missing_file_loads_identity_script_without_creating_file(self) -> None:
        path = preprocessing_script_path(self.directory)
        self.assertEqual(load_preprocessing_script(path), DEFAULT_PREPROCESSING_SCRIPT)
        self.assertFalse(path.exists())

    def test_no_processing_is_the_identity_script_of_the_spec(self) -> None:
````

````python
        self.path = self.directory / "upper.py"

    def test_the_single_script_next_to_the_dictionaries_is_gone(self) -> None:
        # F-18 (D-A): dictionary/preprocessing.py is not read, so nothing names it any more.
        for name in (
            "PREPROCESSING_FILENAME",
            "DEFAULT_PREPROCESSING_SCRIPT",
            "preprocessing_script_path",
            "load_preprocessing_script",
            "save_preprocessing_script",
            "execute_preprocessing_script",
            "validate_preprocessing_script",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(user_script, name))

    def test_no_processing_is_the_identity_script_of_the_spec(self) -> None:
````

Edit: `client/tests/wx_stub.py`

````python
    "FileIssuesDialog",
    "InvalidWorkspaceFilesDialog",
    "TranslationSettingsDialog",
    "TranslationTableDialog",
````

````python
    "FileIssuesDialog",
    "InvalidWorkspaceFilesDialog",
    "ScriptManagementDialog",
    "TranslationSettingsDialog",
    "TranslationTableDialog",
````

```bash
$PY -B -X utf8 -m unittest tests.test_text_scripts_presenter tests.test_script_dialogs tests.test_dialog_base tests.test_gui_document_flows tests.test_settings_dialogs tests.test_user_preprocessing_script tests.test_translation_menu tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_a_cancelled_name_opens_no_editor (tests.test_text_scripts_presenter.PresenterAddTest.test_a_cancelled_name_opens_no_editor)
AttributeError: 'ScriptManagementPresenter' object has no attribute 'add'
ERROR: test_a_file_written_meanwhile_fails_the_first_save_and_is_kept (tests.test_text_scripts_presenter.PresenterAddTest.test_a_file_written_meanwhile_fails_th
ERROR: test_a_taken_name_asks_again (tests.test_text_scripts_presenter.PresenterAddTest.test_a_taken_name_asks_again)
ERROR: test_add_asks_a_name_then_opens_the_template_and_writes_nothing_without_a_save (tests.test_text_scripts_presenter.PresenterAddTest.test_add_asks_a_name_t
ERROR: test_an_invalid_save_writes_nothing (tests.test_text_scripts_presenter.PresenterAddTest.test_an_invalid_save_writes_nothing)
ERROR: test_the_first_save_creates_the_file_and_the_next_one_replaces_it (tests.test_text_scripts_presenter.PresenterAddTest.test_the_first_save_creates_the_fil
ERROR: test_a_failed_delete_is_reported (tests.test_text_scripts_presenter.PresenterDeleteTest.test_a_failed_delete_is_reported)
AttributeError: <module 'text_scripts.presenter' from '<client>\\text_scripts\\presenter.py'> does not have the attribute 'delete_script'
ERROR: test_delete_asks_first_and_selects_the_script_above (tests.test_text_scripts_presenter.PresenterDeleteTest.test_delete_asks_first_and_selects_the_script_
AttributeError: 'ScriptManagementPresenter' object has no attribute 'delete'
ERROR: test_deleting_the_active_script_makes_no_processing_active (tests.test_text_scripts_presenter.PresenterDeleteTest.test_deleting_the_active_script_makes_n
ERROR: test_no_keeps_the_file (tests.test_text_scripts_presenter.PresenterDeleteTest.test_no_keeps_the_file)
ERROR: test_no_processing_is_not_deleted (tests.test_text_scripts_presenter.PresenterDeleteTest.test_no_processing_is_not_deleted)
ERROR: test_the_first_user_script_selects_no_processing_after_its_delete (tests.test_text_scripts_presenter.PresenterDeleteTest.test_the_first_user_script_selec
ERROR: test_a_script_that_cannot_be_read_is_explained_and_not_opened (tests.test_text_scripts_presenter.PresenterEditTest.test_a_script_that_cannot_be_read_is_e
AttributeError: 'ScriptManagementPresenter' object has no attribute 'edit'
ERROR: test_an_invalid_script_opens_so_that_it_can_be_fixed (tests.test_text_scripts_presenter.PresenterEditTest.test_an_invalid_script_opens_so_that_it_can_be_
ERROR: test_edit_opens_the_text_of_the_file_and_saves_it (tests.test_text_scripts_presenter.PresenterEditTest.test_edit_opens_the_text_of_the_file_and_saves_it)
ERROR: test_no_processing_is_not_edited (tests.test_text_scripts_presenter.PresenterEditTest.test_no_processing_is_not_edited)
ERROR: test_a_cancelled_or_failed_export (tests.test_text_scripts_presenter.PresenterExportTest.test_a_cancelled_or_failed_export)
AttributeError: 'ScriptManagementPresenter' object has no attribute 'export_to_file'
ERROR: test_export_suggests_the_file_name_and_copies (tests.test_text_scripts_presenter.PresenterExportTest.test_export_suggests_the_file_name_and_copies) (name
ERROR: test_a_cancelled_file_dialog_does_nothing (tests.test_text_scripts_presenter.PresenterImportTest.test_a_cancelled_file_dialog_does_nothing)
AttributeError: 'ScriptManagementPresenter' object has no attribute 'import_from_file'
ERROR: test_a_source_that_cannot_be_opened_gets_the_reason (tests.test_text_scripts_presenter.PresenterImportTest.test_a_source_that_cannot_be_opened_gets_the_r
ERROR: test_a_syntax_error_is_shown_as_python_gives_it (tests.test_text_scripts_presenter.PresenterImportTest.test_a_syntax_error_is_shown_as_python_gives_it)
ERROR: test_a_taken_name_asks_again (tests.test_text_scripts_presenter.PresenterImportTest.test_a_taken_name_asks_again)
ERROR: test_each_error_is_reported_and_nothing_is_copied (tests.test_text_scripts_presenter.PresenterImportTest.test_each_error_is_reported_and_nothing_is_copie
ERROR: test_import_asks_a_name_from_the_file_and_copies_its_bytes (tests.test_text_scripts_presenter.PresenterImportTest.test_import_asks_a_name_from_the_file_a
ERROR: test_presenter_provides_every_action (tests.test_text_scripts_presenter.PresenterModuleTest.test_presenter_provides_every_action) (name='script_names')
AttributeError: module 'text_scripts.presenter' has no attribute 'ScriptManagementActions'. Did you mean: 'ScriptManagementPresenter'?
ERROR: test_presenter_provides_every_action (tests.test_text_scripts_presenter.PresenterModuleTest.test_presenter_provides_every_action) (name='script_path')
ERROR: test_presenter_provides_every_action (tests.test_text_scripts_presenter.PresenterModuleTest.test_presenter_provides_every_action) (name='add')
ERROR: test_presenter_provides_every_action (tests.test_text_scripts_presenter.PresenterModuleTest.test_presenter_provides_every_action) (name='edit')
ERROR: test_presenter_provides_every_action (tests.test_text_scripts_presenter.PresenterModuleTest.test_presenter_provides_every_action) (name='delete')
ERROR: test_presenter_provides_every_action (tests.test_text_scripts_presenter.PresenterModuleTest.test_presenter_provides_every_action) (name='rename')
ERROR: test_presenter_provides_every_action (tests.test_text_scripts_presenter.PresenterModuleTest.test_presenter_provides_every_action) (name='import_from_file
ERROR: test_presenter_provides_every_action (tests.test_text_scripts_presenter.PresenterModuleTest.test_presenter_provides_every_action) (name='export_to_file')
ERROR: test_view_and_actions_are_protocols (tests.test_text_scripts_presenter.PresenterModuleTest.test_view_and_actions_are_protocols) (name='ScriptManagementVi
AttributeError: module 'text_scripts.presenter' has no attribute 'ScriptManagementView'. Did you mean: 'ScriptManagementPresenter'?
ERROR: test_view_and_actions_are_protocols (tests.test_text_scripts_presenter.PresenterModuleTest.test_view_and_actions_are_protocols) (name='ScriptManagementAc
ERROR: test_a_case_only_rename_follows_the_active_script (tests.test_text_scripts_presenter.PresenterRenameTest.test_a_case_only_rename_follows_the_active_scrip
AttributeError: 'ScriptManagementPresenter' object has no attribute 'rename'
ERROR: test_a_failed_rename_is_reported (tests.test_text_scripts_presenter.PresenterRenameTest.test_a_failed_rename_is_reported)
AttributeError: <module 'text_scripts.presenter' from '<client>\\text_scripts\\presenter.py'> does not have the attribute 'rename_script'
ERROR: test_a_taken_name_asks_again_and_the_same_name_changes_nothing (tests.test_text_scripts_presenter.PresenterRenameTest.test_a_taken_name_asks_again_and_th
ERROR: test_renaming_another_script_keeps_the_active_one (tests.test_text_scripts_presenter.PresenterRenameTest.test_renaming_another_script_keeps_the_active_on
ERROR: test_renaming_the_active_script_makes_the_new_name_active (tests.test_text_scripts_presenter.PresenterRenameTest.test_renaming_the_active_script_makes_th
ERROR: test_no_processing_can_only_be_exported_and_a_user_script_everything (tests.test_script_dialogs.ScriptButtonsTest.test_no_processing_can_only_be_exported
AttributeError: module '_speech_symbols_dialog_under_test' has no attribute 'ScriptManagementDialog'. Did you mean: 'DictionaryManagementDialog'?
ERROR: test_the_title_is_the_name_and_the_code_is_in_a_named_monospace_editor (tests.test_script_dialogs.ScriptEditorBuildTest.test_the_title_is_the_name_and_th
AttributeError: module '_speech_symbols_dialog_under_test' has no attribute 'ScriptEditorDialog'
ERROR: test_after_a_failed_apply_cancel_still_asks (tests.test_script_dialogs.ScriptEditorCancelTest.test_after_a_failed_apply_cancel_still_asks)
ERROR: test_after_a_successful_apply_cancel_closes_without_asking (tests.test_script_dialogs.ScriptEditorCancelTest.test_after_a_successful_apply_cancel_closes_
ERROR: test_back_to_editing_keeps_the_dialog_and_the_focus (tests.test_script_dialogs.ScriptEditorCancelTest.test_back_to_editing_keeps_the_dialog_and_the_focus
ERROR: test_cancel_without_a_change_closes_without_asking_or_saving (tests.test_script_dialogs.ScriptEditorCancelTest.test_cancel_without_a_change_closes_withou
ERROR: test_discard_changes_closes_without_saving (tests.test_script_dialogs.ScriptEditorCancelTest.test_discard_changes_closes_without_saving)
ERROR: test_a_failed_save_is_explained_and_the_focus_goes_back_to_the_code (tests.test_script_dialogs.ScriptEditorSaveTest.test_a_failed_save_is_explained_and_t
ERROR: test_apply_saves_the_text_and_keeps_the_dialog_open (tests.test_script_dialogs.ScriptEditorSaveTest.test_apply_saves_the_text_and_keeps_the_dialog_open)
ERROR: test_ok_closes_after_a_successful_save (tests.test_script_dialogs.ScriptEditorSaveTest.test_ok_closes_after_a_successful_save)
ERROR: test_add_delete_rename_and_import_refresh_with_the_name_they_return (tests.test_script_dialogs.ScriptHandlersTest.test_add_delete_rename_and_import_refre
ERROR: test_edit_runs_the_action_then_refreshes_and_focuses_the_list (tests.test_script_dialogs.ScriptHandlersTest.test_edit_runs_the_action_then_refreshes_and_
ERROR: test_nothing_is_refreshed_when_an_action_returns_none_and_export_returns_nothing (tests.test_script_dialogs.ScriptHandlersTest.test_nothing_is_refreshed_
ERROR: test_a_locked_and_a_broken_script_do_not_stop_the_dialog (tests.test_script_dialogs.ScriptListTest.test_a_locked_and_a_broken_script_do_not_stop_the_dial
ERROR: test_each_script_shows_its_status (tests.test_script_dialogs.ScriptListTest.test_each_script_shows_its_status)
ERROR: test_no_processing_is_shown_translated_and_ready_without_reading_its_file (tests.test_script_dialogs.ScriptListTest.test_no_processing_is_shown_translate
ERROR: test_the_active_script_is_selected_and_focused (tests.test_script_dialogs.ScriptListTest.test_the_active_script_is_selected_and_focused)
ERROR: test_the_reason_row_says_why_and_selects_its_text (tests.test_script_dialogs.ScriptListTest.test_the_reason_row_says_why_and_selects_its_text)
ERROR: test_a_valid_name_is_written_back_without_spaces (tests.test_script_dialogs.ScriptNameDialogTest.test_a_valid_name_is_written_back_without_spaces)
AttributeError: module '_speech_symbols_dialog_under_test' has no attribute 'ScriptNameDialog'. Did you mean: 'DocumentNameDialog'?
ERROR: test_each_refused_name_gets_its_message (tests.test_script_dialogs.ScriptNameDialogTest.test_each_refused_name_gets_its_message) (text='')
ERROR: test_each_refused_name_gets_its_message (tests.test_script_dialogs.ScriptNameDialogTest.test_each_refused_name_gets_its_message) (text='xxxxxxxxxxxxxxxxx
ERROR: test_each_refused_name_gets_its_message (tests.test_script_dialogs.ScriptNameDialogTest.test_each_refused_name_gets_its_message) (text='a/b')
ERROR: test_each_refused_name_gets_its_message (tests.test_script_dialogs.ScriptNameDialogTest.test_each_refused_name_gets_its_message) (text=' 不處理')
ERROR: test_each_refused_name_gets_its_message (tests.test_script_dialogs.ScriptNameDialogTest.test_each_refused_name_gets_its_message) (text='No-Processing')
ERROR: test_each_refused_name_gets_its_message (tests.test_script_dialogs.ScriptNameDialogTest.test_each_refused_name_gets_its_message) (text='no processing')
ERROR: test_boxes_belong_to_the_dialog (tests.test_script_dialogs.ScriptViewTest.test_boxes_belong_to_the_dialog)
ERROR: test_delete_asks_in_a_system_yes_no_box_with_no_as_default (tests.test_script_dialogs.ScriptViewTest.test_delete_asks_in_a_system_yes_no_box_with_no_as_d
ERROR: test_the_file_dialogs_offer_python_files (tests.test_script_dialogs.ScriptViewTest.test_the_file_dialogs_offer_python_files)
ERROR: test_the_name_prompt_and_the_editor_open_over_the_dialog (tests.test_script_dialogs.ScriptViewTest.test_the_name_prompt_and_the_editor_open_over_the_dial
ERROR: test_reserved_without_a_fixed_name_shows_the_name_typed (tests.test_dialog_base.NameDialogMessagesTest.test_reserved_without_a_fixed_name_shows_the_name_
TypeError: NameDialogMessages.message_for() takes 2 positional arguments but 3 were given
ERROR: test_open_script_management_shows_the_presenter_on_the_active_script (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_open_script_management_s
AttributeError: <module 'gui' from '<client>\\gui.py'> does not have the attribute 'ScriptManagementDialog'
FAIL: test_the_reserved_message_gets_the_name_typed_without_spaces (tests.test_dialog_base.NameDialogBaseTest.test_the_reserved_message_gets_the_name_typed_with
AssertionError: 'P2-1 test: None is reserved' != 'P2-1 test: No Processing is reserved'
FAIL: test_the_text_processing_dialog_and_its_handler_are_gone (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_the_text_processing_dialog_and_its_ha
AssertionError: True is not false
FAIL: test_menu_bar_menus_items_and_handlers (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_menu_bar_menus_items_and_handlers)
AssertionError: Lists differ: [('ne[1959 chars], 'T[Text Processing]'), ('frame', 'Bind', 'EV[893 chars]p]')] != [('ne[1959 chars], 'T[Script Management...]'), 
FAIL: test_the_text_processing_dialog_is_gone (tests.test_settings_dialogs.TextProcessingDialogRemovedTest.test_the_text_processing_dialog_is_gone)
FAIL: test_the_single_script_next_to_the_dictionaries_is_gone (tests.test_user_preprocessing_script.UserPreprocessingScriptTest.test_the_single_script_next_to_t
FAIL: test_items_have_stable_keys_labels_and_order (tests.test_translation_menu.TranslationMenuTest.test_items_have_stable_keys_labels_and_order)
AssertionError: Lists differ: [('co[45 chars]), ('text_processing', 'Text Processing'), ('d[63 chars]gs')] != [('co[45 chars]), ('scripts', 'Script Management..
FAIL: test_confirm_box_labels_have_no_access_key (tests.test_i18n.TranslationTest.test_confirm_box_labels_have_no_access_key)
AssertionError: Lists differ: ['放棄變更', '返回編輯', '移除並儲存', '返回編輯'] != ['放棄變更', '返回編輯', '移除並儲存', '返回編輯', '放棄變更', '返回編輯']
Ran 474 tests
FAILED (failures=12, errors=81)
```

- [x] **Step 2: Green: the flows, the three dialogs, the menu, and the removal of Text Processing** (`text_scripts/presenter.py`, `dialog.py`, `gui.py` tabs; the others 4 spaces).

Edit: `client/conversion/preprocessing/user_script.py`

````python
NO_PROCESSING_SCRIPT = "def main(input: str) -> str:\n    return input\n"
SCRIPT_SUFFIX = ".py"

# The single script of the Text Processing dialog, next to the dictionaries (before F-18).
PREPROCESSING_FILENAME = "preprocessing.py"
DEFAULT_PREPROCESSING_SCRIPT = NO_PROCESSING_SCRIPT


def preprocessing_script_path(dictionary_dir: Path | str) -> Path:
    return Path(dictionary_dir) / PREPROCESSING_FILENAME


def load_preprocessing_script(path: Path | str) -> str:
    source_path = Path(path)
    try:
        return source_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return DEFAULT_PREPROCESSING_SCRIPT


````

````python
NO_PROCESSING_SCRIPT = "def main(input: str) -> str:\n    return input\n"
SCRIPT_SUFFIX = ".py"


````

Edit: `client/conversion/preprocessing/user_script.py`

````python


save_preprocessing_script = save_script


def execute_script(path: Path | str, input_text: str) -> str:
    """Read the script at ``path``, check it and return ``main(input_text)`` (F-18 D10)."""
````

````python


def execute_script(path: Path | str, input_text: str) -> str:
    """Read the script at ``path``, check it and return ``main(input_text)`` (F-18 D10)."""
````

Edit: `client/dialog.py`

````python
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
from ui.message_box import confirm_box, message_box

CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")
# The hidden rows the box on OK lists by line; a count stands for the rest (F-11 D1).
HIDDEN_ROWS_LISTED = 10
````

````python
from documents.workspace import normalize_document_name
from i18n import N_, _
from text_scripts.actions import get_script_action_availability, script_display_name
from text_scripts.manager import is_no_processing_script, normalize_script_name, resolve_selected_script
from text_scripts.presenter import SaveScript, ScriptManagementActions
from text_scripts.read_problems import ScriptCheck, ScriptStatus, describe_script_problem, read_script_status
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
from ui.message_box import confirm_box, message_box

CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")
PYTHON_WILDCARD = N_("Python files (*.py)|*.py")
# The Status column of Script Management (F-18 D7, O6); translated when shown.
SCRIPT_STATUS_LABELS = {
	ScriptStatus.READY: N_("Ready"),
	ScriptStatus.UNREADABLE: N_("Unreadable"),
	ScriptStatus.NOT_VALID: N_("Not Valid"),
}
# The hidden rows the box on OK lists by line; a count stands for the rest (F-11 D1).
HIDDEN_ROWS_LISTED = 10
````

Edit: `client/dialog.py`

````python
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return None
			return Path(file_dialog.GetPath())
````

````python
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return None
			return Path(file_dialog.GetPath())


class ScriptNameDialog(_NameDialog):
	"""The name prompt of Script Management: Add, Rename and Import (F-18 D8)."""

	normalize_name = staticmethod(normalize_script_name)
	name_messages = NameDialogMessages(
		empty=N_("Please enter the script name."),
		too_long=N_("Script name must be 1 to 32 characters."),
		invalid=N_("Script name is not a valid Windows file name."),
		reserved=N_('Script name "{name}" is reserved.'),
		# The name as typed: three names are reserved, in any case (F-18 D4).
		reserved_name=None,
	)

	def __init__(self, parent: wx.Window | None, title: str, initial_name: str = ""):
		super().__init__(parent, title=title)

		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid = wx.FlexGridSizer(0, 2, 8, 8)
		grid.AddGrowableCol(1, 1)

		name_label = wx.StaticText(self, label=_("Script Name"))
		self.name_ctrl = wx.TextCtrl(self)
		grid.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL)
		grid.Add(self.name_ctrl, 1, wx.EXPAND)
		main_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

		button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		if button_sizer:
			localize_standard_buttons(self, wx.OK | wx.CANCEL, button_sizer)
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
			self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

		finalize_dialog_layout(self, main_sizer)
		self.name_ctrl.SetValue(initial_name)
		self.name_ctrl.SetFocus()
		self.name_ctrl.SelectAll()

	def get_script_name(self) -> str:
		return self.name_ctrl.GetValue().strip()


class ScriptManagementDialog(ContextManagedDialog, wx.Dialog):
	"""Passive view of Script Management (F-18 D7): runs ``actions`` and implements ``ScriptManagementView``.

	Modal, the twin of ``DictionaryManagementDialog``; the editor opens over it and the
	dialog stays open (F-18 O4).
	"""

	def __init__(
		self,
		parent: wx.Window | None,
		actions: ScriptManagementActions,
		selected_name: str,
	):
		super().__init__(
			parent,
			title=_("Script Management"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
		)
		self._actions = actions
		self._script_names = list(actions.script_names)
		self._selected_name = selected_name
		# The status of each script, read on every refresh (F-18 D7, D-G).
		self._script_checks: dict[str, ScriptCheck] = {}
		self._build_ui()
		self.refresh_scripts(self._script_names, selected_name)

	def _build_ui(self) -> None:
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		self.list_ctrl = CallbackVirtualListCtrl(
			self,
			self._get_item_text,
			style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL,
		)
		self.list_ctrl.InsertColumn(0, _("Script"))
		self.list_ctrl.InsertColumn(1, _("Status"))
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)
		self.list_ctrl.Bind(wx.EVT_SIZE, self._on_list_size)
		main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 12)

		# Why the selected script cannot be used, as in Dictionary Management (F-6 D3): the next
		# Tab stop after the list, its label the field's accessible name, multi-line so that it
		# is a Tab stop, shown only while an unreadable or invalid script is selected.
		self.problem_label = wx.StaticText(self, label=_("Why this script cannot be used:"))
		self.problem_ctrl = wx.TextCtrl(
			self,
			style=wx.TE_MULTILINE | wx.TE_READONLY,
			size=(-1, self.GetCharHeight() * 4),
		)
		main_sizer.Add(self.problem_label, 0, wx.LEFT | wx.RIGHT, 12)
		main_sizer.Add(self.problem_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		self.problem_label.Hide()
		self.problem_ctrl.Hide()
		self.problem_ctrl.Bind(wx.EVT_SET_FOCUS, self._on_problem_focus)

		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.add_button = wx.Button(self, label=_("Add"))
		self.delete_button = wx.Button(self, label=_("Delete"))
		self.rename_button = wx.Button(self, label=_("Rename"))
		self.edit_button = wx.Button(self, label=_("Edit"))
		self.import_button = wx.Button(self, label=_("Import"))
		self.export_button = wx.Button(self, label=_("Export"))
		for button in (
			self.add_button,
			self.delete_button,
			self.rename_button,
			self.edit_button,
			self.import_button,
			self.export_button,
		):
			button_sizer.Add(button, 0, wx.RIGHT, 8)
		main_sizer.Add(button_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

		button_bar = self.CreateButtonSizer(wx.CLOSE)
		if button_bar:
			localize_standard_buttons(self, wx.CLOSE, button_bar)
			main_sizer.Add(button_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
			self.Bind(wx.EVT_BUTTON, lambda _event: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)

		self.add_button.Bind(wx.EVT_BUTTON, self._on_add_clicked)
		self.delete_button.Bind(wx.EVT_BUTTON, self._on_delete_clicked)
		self.rename_button.Bind(wx.EVT_BUTTON, self._on_rename_clicked)
		self.edit_button.Bind(wx.EVT_BUTTON, self._on_edit_clicked)
		self.import_button.Bind(wx.EVT_BUTTON, self._on_import_clicked)
		self.export_button.Bind(wx.EVT_BUTTON, self._on_export_clicked)

		finalize_dialog_layout(self, main_sizer)
		self._resize_columns()

	def _get_item_text(self, item: int, column: int) -> str:
		name = self._script_names[item]
		if column == 0:
			return script_display_name(name)
		if column == 1:
			return _(SCRIPT_STATUS_LABELS[self._script_check(name).status])
		raise ValueError(f"Unknown column: {column}")

	def _script_check(self, name: str | None) -> ScriptCheck:
		return self._script_checks.get(name, ScriptCheck()) if name is not None else ScriptCheck()

	def _load_script_checks(self) -> None:
		"""Read and check every script on its own; one that fails never stops the dialog (F-18 D-G).

		No Processing is ready whatever its file holds: conversion never reads it (F-18 D4).
		"""
		self._script_checks = {
			name: read_script_status(self._actions.script_path(name))
			for name in self._script_names
			if not is_no_processing_script(name)
		}

	def refresh_scripts(self, script_names: list[str], preferred_name: str | None) -> None:
		self._script_names = list(script_names)
		self._load_script_checks()
		self.list_ctrl.SetItemCount(len(self._script_names))
		self.list_ctrl.Refresh()
		selected = resolve_selected_script(self._script_names, preferred_name)
		self._selected_name = selected
		if selected in self._script_names:
			index = self._script_names.index(selected)
			self.list_ctrl.Select(index)
			self.list_ctrl.Focus(index)
		self._resize_columns()
		self._update_button_states()
		self._update_problem()

	def _update_problem(self) -> None:
		"""Show why the selected script cannot be used, or hide the reason row (F-6 D3 twin).

		The text is selected, so a screen reader reads all of it when the field gets focus.
		"""
		error = self._script_check(self._get_selected_name()).error
		if error is None:
			self.problem_ctrl.ChangeValue("")
		else:
			self.problem_ctrl.ChangeValue(describe_script_problem(error))
			self.problem_ctrl.SelectAll()
		self.problem_label.Show(error is not None)
		self.problem_ctrl.Show(error is not None)
		self.Layout()

	def _on_problem_focus(self, event: wx.FocusEvent) -> None:
		self.problem_ctrl.SelectAll()
		event.Skip()

	def _resize_columns(self) -> None:
		available_width = max(0, self.list_ctrl.GetClientSize().width)
		if available_width == 0:
			return
		labels = [_("Status"), *(_(label) for label in SCRIPT_STATUS_LABELS.values())]
		status_text_width = max(self.list_ctrl.GetTextExtent(label)[0] for label in labels)
		status_width = min(available_width, max(96, status_text_width + 32))
		self.list_ctrl.SetColumnWidth(0, max(0, available_width - status_width))
		self.list_ctrl.SetColumnWidth(1, status_width)

	def _on_list_size(self, event: wx.SizeEvent) -> None:
		self._resize_columns()
		event.Skip()

	def _get_selected_name(self) -> str | None:
		index = self.list_ctrl.GetFirstSelected()
		if index == wx.NOT_FOUND or index >= len(self._script_names):
			return None
		return self._script_names[index]

	def _update_button_states(self) -> None:
		selected_name = self._get_selected_name() or self._selected_name or ""
		availability = get_script_action_availability(self._script_names, selected_name)
		self.add_button.Enable(True)
		self.import_button.Enable(True)
		self.delete_button.Enable(availability.delete)
		self.rename_button.Enable(availability.rename)
		self.edit_button.Enable(availability.edit)
		self.export_button.Enable(availability.export)

	def _on_selection_changed(self, event: wx.ListEvent) -> None:
		selected_name = self._get_selected_name()
		if selected_name is not None:
			self._selected_name = selected_name
		self._update_button_states()
		self._update_problem()
		event.Skip()

	def _on_add_clicked(self, _event: wx.CommandEvent) -> None:
		self._refresh_after(self._actions.add(self), focus_list=True)

	def _on_edit_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			# Back in the list after the editor, with the status read again (F-18 D8.2).
			self._refresh_after(self._actions.edit(self, selected), focus_list=True)

	def _on_delete_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			self._refresh_after(self._actions.delete(self, selected))

	def _on_rename_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			self._refresh_after(self._actions.rename(self, selected))

	def _on_import_clicked(self, _event: wx.CommandEvent) -> None:
		self._refresh_after(self._actions.import_from_file(self))

	def _on_export_clicked(self, _event: wx.CommandEvent) -> None:
		selected = self._get_selected_name()
		if selected is not None:
			self._actions.export_to_file(self, selected)

	def _refresh_after(self, preferred_name: str | None, *, focus_list: bool = False) -> None:
		if preferred_name is None:
			return
		self.refresh_scripts(self._actions.script_names, preferred_name)
		if focus_list:
			self.list_ctrl.SetFocus()

	def prompt_script_name(self, title: str, initial_name: str) -> str | None:
		with ScriptNameDialog(self, title, initial_name=initial_name) as name_dialog:
			if name_dialog.ShowModal() != wx.ID_OK:
				return None
			return name_dialog.get_script_name()

	def edit_script(self, title: str, source: str, save: SaveScript) -> None:
		with ScriptEditorDialog(self, script_name=title, source=source, save=save) as editor:
			editor.ShowModal()

	def show_info(self, message: str) -> None:
		message_box(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)

	def show_error(self, message: str) -> None:
		message_box(message, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)

	def confirm(self, message: str, caption: str) -> bool:
		return message_box(message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self) == wx.YES

	def choose_import_path(self, title: str) -> Path | None:
		with wx.FileDialog(
			self,
			title,
			wildcard=_(PYTHON_WILDCARD),
			style=wx.FD_OPEN,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return None
			return Path(file_dialog.GetPath())

	def choose_export_path(self, title: str, default_file: str) -> Path | None:
		with wx.FileDialog(
			self,
			title,
			defaultFile=default_file,
			wildcard=_(PYTHON_WILDCARD),
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		) as file_dialog:
			if file_dialog.ShowModal() != wx.ID_OK:
				return None
			return Path(file_dialog.GetPath())


class ScriptEditorDialog(ContextManagedDialog, wx.Dialog):
	"""The code of one script (F-18 D9), titled with its name; the save goes through ``save``.

	OK saves and closes, Apply saves; a failed save is explained and the focus goes back to
	the code. Cancel, Esc and the close box ask before changes are lost, as the dictionary
	editor does (F-11 D7, F-15).
	"""

	INITIAL_SIZE = (720, 440)
	MIN_SIZE = (520, 300)

	def __init__(self, parent: wx.Window | None, *, script_name: str, source: str, save: SaveScript):
		super().__init__(parent, title=script_name, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self._script_name = script_name
		self._save = save
		try:
			self._build_ui(source)
		except BaseException:
			self.Destroy()
			raise

	def _build_ui(self, source: str) -> None:
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.editor = wx.TextCtrl(self, value=source, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_DONTWRAP)
		# The title names the script (F-18 O9).
		self.editor.SetName(_("Python Code"))
		font = self.editor.GetFont()
		font.SetFamily(wx.FONTFAMILY_TELETYPE)
		self.editor.SetFont(font)
		sizer.Add(self.editor, 1, wx.EXPAND | wx.ALL, 8)

		button_bar = self.CreateButtonSizer(wx.OK | wx.CANCEL | wx.APPLY)
		if button_bar:
			localize_standard_buttons(self, wx.OK | wx.CANCEL | wx.APPLY, button_bar)
			sizer.Add(button_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
		# wx turns Esc and the close box into a click on the Cancel button (F-11 D7).
		for button_id, handler in ((wx.ID_OK, self._on_ok), (wx.ID_CANCEL, self._on_cancel), (wx.ID_APPLY, self._on_apply)):
			button = self.FindWindow(button_id)
			if button:
				button.Bind(wx.EVT_BUTTON, handler)

		self.SetSizer(sizer)
		self.SetMinSize(self.MIN_SIZE)
		self.SetSize(self.INITIAL_SIZE)
		self.CentreOnParent()
		# What the control holds, which can differ from ``source`` in its line ends.
		self._saved_text = self.editor.GetValue()
		self.editor.SetInsertionPoint(0)
		self.editor.SetFocus()

	def has_changes(self) -> bool:
		"""Whether the code differs from the last save, or from the text the editor opened with."""
		return self.editor.GetValue() != self._saved_text

	def _apply(self) -> bool:
		text = self.editor.GetValue()
		try:
			self._save(text)
		except (OSError, SyntaxError, ValueError) as error:
			# A ValueError of the signature rule is a msgid (F-18 D5).
			display_error = _(str(error)) if isinstance(error, ValueError) else error
			message_box(
				_("Failed to save script: {error}").format(error=display_error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			self.editor.SetFocus()
			return False
		self._saved_text = text
		return True

	def _on_apply(self, _event: wx.CommandEvent) -> None:
		self._apply()

	def _on_ok(self, event: wx.CommandEvent) -> None:
		if self._apply():
			event.Skip()

	def _on_cancel(self, event: wx.CommandEvent) -> None:
		focused = wx.Window.FindFocus()
		if self.has_changes() and not confirm_box(
			_('Do you want to discard the changes you made to script "{name}"?').format(name=self._script_name),
			_("Unsaved Changes"),
			_("Discard Changes"),
			_("Back to Editing"),
			parent=self,
		):
			self._restore_focus(focused)
			return
		event.Skip()

	def _restore_focus(self, window: wx.Window | None) -> None:
		"""Put the focus back where it was before the box (F-11 D7)."""
		if window is not None and self.IsDescendant(window):
			window.SetFocus()
````

Edit: `client/gui.py`

````python
from conversion.math_service import latex_to_mathml
from conversion.service import ConversionRequest
from conversion.preprocessing.user_script import preprocessing_script_path
from dictionaries.entry_list_model import DictionaryEntryListModel
from dictionaries.manager import dictionary_path_for_name
````

````python
from conversion.math_service import latex_to_mathml
from conversion.service import ConversionRequest
from dictionaries.entry_list_model import DictionaryEntryListModel
from dictionaries.manager import dictionary_path_for_name
````

Edit: `client/gui.py`

````python
	FileIssuesDialog,
	InvalidWorkspaceFilesDialog,
)
from settings.view import (
````

````python
	FileIssuesDialog,
	InvalidWorkspaceFilesDialog,
	ScriptManagementDialog,
)
from settings.view import (
````

Edit: `client/gui.py`

````python
)
from settings.state import DotExpressSettingsSnapshot
from settings.dialogs import DotExpressSettingsDialog, TextProcessingDialog, TranslationSettingsPanel
from settings.options import BRAILLE_FONT_SIMBRAILLE, VIEW_SCHEME_OPTIONS

````

````python
)
from settings.state import DotExpressSettingsSnapshot
from settings.dialogs import DotExpressSettingsDialog, TranslationSettingsPanel
from settings.options import BRAILLE_FONT_SIMBRAILLE, VIEW_SCHEME_OPTIONS

````

Edit: `client/gui.py`

````python
			"convert": self.on_convert,
			"dual_view": self.on_open_dual_view,
			"text_processing": self.on_open_text_processing,
			"settings": self.on_open_settings,
			"dictionaries": self.on_open_dictionary_management,
````

````python
			"convert": self.on_convert,
			"dual_view": self.on_open_dual_view,
			"scripts": self.on_open_script_management,
			"settings": self.on_open_settings,
			"dictionaries": self.on_open_dictionary_management,
````

Edit: `client/gui.py`

````python
		self._open_dual_view_in_browser()

	def on_open_text_processing(self, _event) -> None:
		try:
			TextProcessingDialog.show_singleton(
				parent=self,
				script_path=preprocessing_script_path(self.dictionary_dir),
			)
		except OSError as error:
			message_box(
				_("Unable to open text processing script: {error}").format(error=error),
				_("Text Processing"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)

	def on_frame_activate(self, event: wx.ActivateEvent) -> None:
````

````python
		self._open_dual_view_in_browser()

	def on_open_script_management(self, _event) -> None:
		"""The modal Script Management dialog, with the active script selected (F-18 D7)."""
		selected_name = self._script_presenter.refresh(self.translation_settings.selected_script)
		with ScriptManagementDialog(self, self._script_presenter, selected_name) as dialog:
			dialog.ShowModal()

	def on_frame_activate(self, event: wx.ActivateEvent) -> None:
````

Edit: `client/settings/dialogs.py`

````python
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import wx
````

````python
from collections.abc import Callable
from dataclasses import dataclass

import wx
````

Edit: `client/settings/dialogs.py`

````python

from braille.tables import listTables
from conversion.preprocessing.user_script import (
    NO_PROCESSING_SCRIPT_NAME,
    load_preprocessing_script,
    save_preprocessing_script,
)
from i18n import N_, _
from text_scripts.actions import script_display_name
````

````python

from braille.tables import listTables
from conversion.preprocessing.user_script import NO_PROCESSING_SCRIPT_NAME
from i18n import N_, _
from text_scripts.actions import script_display_name
````

Edit: `client/settings/dialogs.py`

````python
    error_type for error_type in (getattr(wx, "PyDeadObjectError", None),) if error_type is not None
)


class TextProcessingDialog(SingletonDialogMixin, SettingsDialog):
    _instance: "TextProcessingDialog | None" = None
    dead_window_error_types = _DEAD_WINDOW_ERROR_TYPES

    def __init__(self, parent, *, script_path: Path | str) -> None:
        self.script_path = Path(script_path)
        source = load_preprocessing_script(self.script_path)
        super().__init__(parent, title=_("Text Processing"))
        self._build_layout(source)
        self.SetMinSize(self.MIN_SIZE)
        self.SetSize(self.INITIAL_SIZE)
        self.CentreOnParent()

    def _build_layout(self, source: str) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.editor = wx.TextCtrl(
            self,
            value=source,
            style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_DONTWRAP,
        )
        self.editor.SetName(_("Text Processing Python Code"))
        font = self.editor.GetFont()
        font.SetFamily(wx.FONTFAMILY_TELETYPE)
        self.editor.SetFont(font)
        sizer.Add(self.editor, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(self, wx.ID_OK, _("OK"))
        cancel_button = wx.Button(self, wx.ID_CANCEL, _("Cancel"))
        apply_button = wx.Button(self, wx.ID_APPLY, _("Apply"))
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        apply_button.Bind(wx.EVT_BUTTON, self.on_apply)
        for button in (ok_button, cancel_button, apply_button):
            buttons.Add(button, 0, wx.ALL, 5)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.SetSizer(sizer)

    def on_apply(self, event=None) -> bool:
        try:
            save_preprocessing_script(self.script_path, self.editor.GetValue())
        except (OSError, SyntaxError, ValueError) as error:
            display_error = _(str(error)) if isinstance(error, ValueError) else error
            message_box(
                _("Unable to save text processing script: {error}").format(
                    error=display_error
                ),
                _("Text Processing"),
                wx.OK | wx.ICON_ERROR,
                parent=self,
            )
            self.editor.SetFocus()
            return False
        return True

    def on_ok(self, event=None) -> None:
        if self.on_apply():
            self._destroy()

    def on_cancel(self, event=None) -> None:
        self._destroy()

    @classmethod
    def show_singleton(
        cls,
        *,
        parent,
        script_path: Path | str,
    ) -> "TextProcessingDialog":
        existing = cls._raise_existing()
        if existing is not None:
            return existing
        return cls._show_new(cls(parent, script_path=script_path))


````

````python
    error_type for error_type in (getattr(wx, "PyDeadObjectError", None),) if error_type is not None
)


````

Edit: `client/text_scripts/presenter.py`

````python
"""Script-management workflow without wx (F-18).

``ScriptManagementPresenter`` owns the list of script names, the twin of
``dictionaries.presenter.DictionaryManagementPresenter``.
"""

````

````python
"""Script-management workflow without wx (F-18).

``ScriptManagementPresenter`` owns the list of script names and the add, edit, delete,
rename, import and export flows, the twin of
``dictionaries.presenter.DictionaryManagementPresenter``. It talks to the user only
through a ``ScriptManagementView`` (implemented by ``dialog.ScriptManagementDialog``)
and builds every user-facing string with ``_`` at call time.
"""

````

Edit: `client/text_scripts/presenter.py`

````python
from collections.abc import Callable
from pathlib import Path

from text_scripts.manager import (
	ensure_no_processing_script,
	list_script_names,
	resolve_selected_script,
	script_path_for_name,
)


class ScriptManagementPresenter:
	"""The only owner of the script name list."""

	def __init__(
````

````python
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from conversion.preprocessing.user_script import (
	NO_PROCESSING_SCRIPT,
	NO_PROCESSING_SCRIPT_NAME,
	SCRIPT_SUFFIX,
	read_script_source,
	save_script,
)
from dictionaries.name_prompt import prompt_dictionary_name_until_success
from i18n import _
from text_scripts.manager import (
	ScriptImportSourceError,
	create_script,
	delete_script,
	ensure_no_processing_script,
	export_script,
	import_script,
	is_no_processing_script,
	list_script_names,
	normalize_script_name,
	rename_script,
	resolve_selected_script,
	script_exists,
	script_path_for_name,
)
from text_scripts.read_problems import describe_script_problem, describe_unreadable_script, log_script_read_error

SaveScript = Callable[[str], None]
_T = TypeVar("_T")


class ScriptManagementView(Protocol):
	def prompt_script_name(self, title: str, initial_name: str) -> str | None: ...

	def edit_script(self, title: str, source: str, save: SaveScript) -> None:
		"""Show the editor until it is closed; ``save`` raises ``OSError``, ``SyntaxError`` or ``ValueError``."""
		...

	def show_info(self, message: str) -> None: ...

	def show_error(self, message: str) -> None: ...

	def confirm(self, message: str, caption: str) -> bool: ...

	def choose_import_path(self, title: str) -> Path | None: ...

	def choose_export_path(self, title: str, default_file: str) -> Path | None: ...


class ScriptManagementActions(Protocol):
	@property
	def script_names(self) -> list[str]: ...

	def script_path(self, name: str) -> Path: ...

	def add(self, view: ScriptManagementView) -> str | None: ...

	def edit(self, view: ScriptManagementView, name: str) -> str | None: ...

	def delete(self, view: ScriptManagementView, name: str) -> str | None: ...

	def rename(self, view: ScriptManagementView, name: str) -> str | None: ...

	def import_from_file(self, view: ScriptManagementView) -> str | None: ...

	def export_to_file(self, view: ScriptManagementView, name: str) -> None: ...


class ScriptManagementPresenter:
	"""Satisfies ``ScriptManagementActions``; the only owner of the script name list.

	Each flow returns the name to select in the list afterwards, or ``None`` to leave the
	list as it is. Only Rename and Delete change the active script (F-18 D3).
	"""

	def __init__(
````

Edit: `client/text_scripts/presenter.py`

````python
	def script_path(self, name: str) -> Path:
		return script_path_for_name(name, self._script_dir)
````

````python
	def script_path(self, name: str) -> Path:
		return script_path_for_name(name, self._script_dir)

	def add(self, view: ScriptManagementView) -> str | None:
		"""A name, then the editor with the template; nothing is written before a save (F-18 D8.1)."""
		try:
			name = self._prompt_name_until_success(view, _("Add Script"), "", self._new_name)
		except ValueError as exc:
			view.show_info(str(exc))
			return None
		if name is None:
			return None
		created = False

		def save(source: str) -> None:
			nonlocal created
			if created:
				save_script(self.script_path(name), source)
				return
			try:
				create_script(self._script_dir, name, source)
			except FileExistsError as error:
				# Another program wrote a file of that name while the editor was open.
				raise FileExistsError(_('Script "{name}" already exists.').format(name=name)) from error
			created = True

		view.edit_script(name, NO_PROCESSING_SCRIPT, save)
		if not created:
			return None
		self.refresh(name)
		return name

	def edit(self, view: ScriptManagementView, name: str) -> str | None:
		"""Read the file again and open the editor; an invalid script opens too (F-18 D8.2)."""
		if is_no_processing_script(name):
			return None
		path = self.script_path(name)
		try:
			source = read_script_source(path)
		except Exception as error:
			log_script_read_error(path, error)
			view.show_error(describe_unreadable_script(name, error))
			return name
		view.edit_script(name, source, lambda text: save_script(path, text))
		return name

	def delete(self, view: ScriptManagementView, name: str) -> str | None:
		if is_no_processing_script(name):
			return None
		if not view.confirm(
			_('Do you want to delete script "{name}"?').format(name=name),
			_("Confirm Delete Script"),
		):
			return None
		previous_names = list(self._script_names)
		active_name = self._get_active_name()
		try:
			delete_script(self._script_dir, name)
		except OSError as exc:
			view.show_error(_("Failed to delete script: {error}").format(error=exc))
			return None
		if active_name == name:
			# Not the neighbour, as for dictionaries: that would start running another script (F-18 O5).
			self._set_active_name(NO_PROCESSING_SCRIPT_NAME)
		index = previous_names.index(name) if name in previous_names else 0
		return self.refresh(previous_names[index - 1] if index > 0 else None)

	def rename(self, view: ScriptManagementView, name: str) -> str | None:
		if is_no_processing_script(name):
			return None
		try:
			path = self._prompt_name_until_success(view, _("Rename Script"), name, lambda new_name: self._rename(name, new_name))
		except ValueError as exc:
			view.show_info(str(exc))
			return None
		except OSError as exc:
			view.show_error(_("Failed to save script: {error}").format(error=exc))
			return None
		if path is None:
			return None
		if self._get_active_name() == name and path.stem != name:
			self._set_active_name(path.stem)
		return self.refresh(path.stem)

	def import_from_file(self, view: ScriptManagementView) -> str | None:
		source_path = view.choose_import_path(_("Import Script"))
		if source_path is None:
			return None
		try:
			path = self._prompt_name_until_success(
				view,
				_("Add Script"),
				source_path.stem,
				lambda script_name: import_script(self._script_dir, source_path, script_name),
			)
		except ScriptImportSourceError as exc:
			view.show_error(self._import_failed(exc.error))
			return None
		except (SyntaxError, ValueError) as exc:
			# Not UTF-8, a msgid of the signature rule or of the suffix check (F-18 D8.5).
			view.show_error(self._import_failed(exc))
			return None
		except OSError as exc:
			view.show_error(_("Failed to import script: {error}").format(error=exc))
			return None
		if path is None:
			return None
		return self.refresh(path.stem)

	def export_to_file(self, view: ScriptManagementView, name: str) -> None:
		if not self._script_names:
			return None
		destination_path = view.choose_export_path(_("Export Script"), f"{name}{SCRIPT_SUFFIX}")
		if destination_path is None:
			return None
		try:
			export_script(self._script_dir, name, destination_path)
		except OSError as exc:
			view.show_error(_("Failed to export script: {error}").format(error=exc))
		return None

	def _new_name(self, name: str) -> str:
		"""The name of a new script; ``FileExistsError`` asks for another one."""
		normalized = normalize_script_name(name)
		if script_exists(self._script_dir, normalized):
			raise FileExistsError(normalized)
		return normalized

	def _rename(self, name: str, new_name: str) -> Path:
		if name.strip() == new_name.strip():
			return self.script_path(name.strip())
		return rename_script(self._script_dir, name, new_name)

	@staticmethod
	def _import_failed(error: Exception) -> str:
		return _("Failed to import script: {error}").format(error=describe_script_problem(error))

	def _prompt_name_until_success(
		self,
		view: ScriptManagementView,
		title: str,
		initial_name: str,
		submit: Callable[[str], _T],
	) -> _T | None:
		return prompt_dictionary_name_until_success(
			initial_name,
			prompt_name=lambda current_name: view.prompt_script_name(title, current_name),
			on_submit=submit,
			on_duplicate=lambda script_name: view.show_error(
				_('Script "{name}" already exists.').format(name=script_name.strip())
			),
		)
````

Edit: `client/ui/dialog_base.py`

````python
    invalid: str
    reserved: str | None = None
    reserved_name: str = ""

    def message_for(self, code: str) -> str:
        """The translated message for a ``NameValidationError`` code; ``reserved`` may use ``{name}``."""
        if code == "empty":
            return _(self.empty)
````

````python
    invalid: str
    reserved: str | None = None
    # The name ``reserved`` shows; ``None`` shows the name as typed (F-18 D4).
    reserved_name: str | None = ""

    def message_for(self, code: str, name: str = "") -> str:
        """The translated message for a ``NameValidationError`` code; ``reserved`` may use ``{name}``.

        ``name`` is the name typed, without surrounding spaces.
        """
        if code == "empty":
            return _(self.empty)
````

Edit: `client/ui/dialog_base.py`

````python
            return _(self.too_long)
        if code == "reserved" and self.reserved is not None:
            return _(self.reserved).format(name=self.reserved_name)
        return _(self.invalid)

````

````python
            return _(self.too_long)
        if code == "reserved" and self.reserved is not None:
            return _(self.reserved).format(name=name if self.reserved_name is None else self.reserved_name)
        return _(self.invalid)

````

Edit: `client/ui/dialog_base.py`

````python
        except ValueError:
            code = "invalid"
        return None, self.name_messages.message_for(code)

    def _validate_name(self, candidate: str) -> str | None:
````

````python
        except ValueError:
            code = "invalid"
        return None, self.name_messages.message_for(code, candidate.strip())

    def _validate_name(self, candidate: str) -> str | None:
````

Edit: `client/ui/translation_menu.py`

````python
        ("convert", N_("Convert")),
        ("dual_view", N_("Dual View")),
        ("text_processing", N_("Text Processing")),
        ("dictionaries", N_("Dictionary Management...")),
        ("settings", N_("Settings")),
````

````python
        ("convert", N_("Convert")),
        ("dual_view", N_("Dual View")),
        ("scripts", N_("Script Management...")),
        ("dictionaries", N_("Dictionary Management...")),
        ("settings", N_("Settings")),
````

- [x] **Step 3: Regenerate the catalogs** (26 new msgids, 4 removed; Spec Corrections 9).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
$PY -I $T/tools/set_msgstr.py locales/zh_TW/LC_MESSAGES/dotexpress.po $T/tools/f18_msgstr.tsv
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cp locales/zh_TW/LC_MESSAGES/dotexpress.po $T/edited.po
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
cmp -s $T/edited.po locales/zh_TW/LC_MESSAGES/dotexpress.po && echo "a second msgmerge changes nothing"
msgfmt --check -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po; echo "msgfmt exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
unix2dos -q locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid ' locales/zh_TW/LC_MESSAGES/dotexpress.po
git -C $REPO diff --stat -- client/locales
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (before `set_msgstr.py` 412 translated, 19 fuzzy and 7 untranslated; afterwards 438 translated; 28 obsolete entries):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
412 translated messages, 19 fuzzy translations, 7 untranslated messages.
msgstr set: 33, not in the file yet: 0
a second msgmerge changes nothing
msgfmt exit 0
438 translated messages.
28
 client/locales/dotexpress.pot                  | 349 ++++++++++++++---------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 35942 -> 37415 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 370 ++++++++++++++++---------
 3 files changed, 456 insertions(+), 263 deletions(-)
source msgids: 438 sha256 06f59dc2c79f4eebaad88b4b62a35a5b72cd462db7ea0685a0e2ffa54cc7d64a
```

- [x] **Step 4: Green: the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_text_scripts_presenter tests.test_script_dialogs tests.test_dialog_base tests.test_gui_document_flows tests.test_settings_dialogs tests.test_user_preprocessing_script tests.test_translation_menu tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 474 tests
OK
Ran 1788 tests
OK (skipped=6)
```

- [x] **Step 5: Commit.**

```bash
git -C $REPO add client/conversion/preprocessing/user_script.py client/dialog.py client/gui.py client/settings/dialogs.py client/text_scripts/presenter.py client/ui/dialog_base.py client/ui/translation_menu.py client/tests/test_dialog_base.py client/tests/test_gui_document_flows.py client/tests/test_i18n.py client/tests/test_script_dialogs.py client/tests/test_settings_dialogs.py client/tests/test_text_scripts_presenter.py client/tests/test_translation_menu.py client/tests/test_user_preprocessing_script.py client/tests/wx_stub.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "feat: replace Text Processing with Script Management (F-18)"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
 client/conversion/preprocessing/user_script.py |  19 -
 client/dialog.py                               | 410 ++++++++++++++
 client/gui.py                                  |  24 +-
 client/locales/dotexpress.pot                  | 349 +++++++-----
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 35942 -> 37415 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 370 ++++++++-----
 client/settings/dialogs.py                     |  82 +--
 client/tests/test_dialog_base.py               |  21 +
 client/tests/test_gui_document_flows.py        |  57 +-
 client/tests/test_i18n.py                      |  10 +-
 client/tests/test_script_dialogs.py            | 723 +++++++++++++++++++++++++
 client/tests/test_settings_dialogs.py          | 142 +----
 client/tests/test_text_scripts_presenter.py    | 394 +++++++++++++-
 client/tests/test_translation_menu.py          |   2 +-
 client/tests/test_user_preprocessing_script.py |  24 +-
 client/tests/wx_stub.py                        |   1 +
 client/text_scripts/presenter.py               | 223 +++++++-
 client/ui/dialog_base.py                       |  14 +-
 client/ui/translation_menu.py                  |   2 +-
 19 files changed, 2286 insertions(+), 581 deletions(-)
c825cb3bf2746815ebf3a76d995472cd3f0e2ef5
```

### Task 4: Verification (no commit)

Each step is a criterion of the spec's Acceptance Criteria.

- [x] **Step 1: Criterion 1, full suite.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 1788 tests
OK (skipped=6)
```

- [x] **Step 2: Criterion 2, the focused modules.**

```bash
$PY -B -X utf8 -m unittest tests.test_user_preprocessing_script tests.test_text_scripts_manager tests.test_text_scripts_presenter tests.test_script_dialogs tests.test_config tests.test_translation_settings tests.test_settings_dialogs tests.test_conversion_text_pipeline tests.test_conversion_service tests.test_gui_document_flows tests.test_translation_menu tests.test_app_paths 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 556 tests
OK
```

- [x] **Step 3: The shuffled module order, three seeds** (one process each).

```bash
$PY -B -X utf8 $T/tools/shuffle_harness.py 18 1018 2018
```

Expected:

```text
seed 18: ran=1788 failures=0 errors=0 skipped=6 []
seed 1018: ran=1788 failures=0 errors=0 skipped=6 []
seed 2018: ran=1788 failures=0 errors=0 skipped=6 []
```

- [x] **Step 4: Criterion 3, catalogs.** A fresh template differs from the committed one only in `POT-Creation-Date`; 438 msgids, all translated, 0 fuzzy, 28 obsolete; the `.mo` is what `msgfmt` builds from the `.po`; against `cb07a37` the msgid set gains the spec's 33 strings and loses its 5.

```bash
(cd $REPO && cmd //c "scripts\\generate-pot.bat $(cygpath -w $T/fresh.pot)"); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py $T/fresh.pot "2026-10-10 12:00+0800" >/dev/null
cmp <(tr -d '\r' < locales/dotexpress.pot) <(tr -d '\r' < $T/fresh.pot) && echo "a fresh template with the pinned date equals the committed one"
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
grep -c '^#~ msgid ' locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/check.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/check.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "the .mo is msgfmt's build of the .po"
git -C $REPO show cb07a37:client/locales/dotexpress.pot > $T/base.pot
$PY -I $T/tools/msgid_diff.py $T/base.pot locales/dotexpress.pot
```

Expected (the fresh template differs only in its creation date):

```text
generate-pot exit 0
a fresh template with the pinned date equals the committed one
locales/dotexpress.pot:439
locales/zh_TW/LC_MESSAGES/dotexpress.po:439
28
438 translated messages.
the .mo is msgfmt's build of the .po
old 410 new 438
+ 'Add Script' ... 'Add Script'
+ 'Confirm Delete Scrip' ... 'Confirm Delete Script'
+ 'Do you want to delet' ... 'Do you want to delete script "{name}"?'
+ 'Do you want to disca' ... 'you want to discard the changes you made to script "{name}"?'
+ 'Export Script' ... 'Export Script'
+ 'Failed to delete scr' ... 'Failed to delete script: {error}'
+ 'Failed to export scr' ... 'Failed to export script: {error}'
+ 'Failed to import scr' ... 'Failed to import script: {error}'
+ 'Failed to save scrip' ... 'Failed to save script: {error}'
+ 'Import Script' ... 'Import Script'
+ 'No Processing' ... 'No Processing'
+ 'Not Valid' ... 'Not Valid'
+ 'Only Python files (.' ... 'Only Python files (.py) can be imported.'
+ 'Please enter the scr' ... 'Please enter the script name.'
+ 'Python Code' ... 'Python Code'
+ 'Python files (*.py)|' ... 'Python files (*.py)|*.py'
+ 'Ready' ... 'Ready'
+ 'Rename Script' ... 'Rename Script'
+ 'Script' ... 'Script'
+ 'Script "{name}" alre' ... 'Script "{name}" already exists.'
+ 'Script "{name}" cann' ... 'Script "{name}" cannot be read.'
+ 'Script Management' ... 'Script Management'
+ 'Script Management...' ... 'Script Management...'
+ 'Script Name' ... 'Script Name'
+ 'Script name "{name}"' ... 'Script name "{name}" is reserved.'
+ 'Script name is not a' ... 'Script name is not a valid Windows file name.'
+ 'Script name must be ' ... 'Script name must be 1 to 32 characters.'
+ 'Status' ... 'Status'
+ 'Text Processing Scri' ... 'Text Processing Script'
+ 'The parameter of mai' ... 'arameter of main must be annotated as str, or not annotated.'
+ 'The return value of ' ... 'rn value of main must be annotated as str, or not annotated.'
+ 'Translation output m' ... ' mode, width, dictionary, and text processing script options'
+ 'Why this script cann' ... 'Why this script cannot be used:'
- 'Text Processing' ... 'Text Processing'
- 'Text Processing Pyth' ... 'Text Processing Python Code'
- 'Translation output m' ... 'Translation output mode, width, and dictionary options'
- 'Unable to open text ' ... 'Unable to open text processing script: {error}'
- 'Unable to save text ' ... 'Unable to save text processing script: {error}'
```

- [x] **Step 5: Criteria 4-6: fixtures, untouched files, application folders.**

```bash
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/translation_liblouis_golden.json | sha256sum
git -C $REPO diff --stat cb07a37 HEAD -- client/braille client/tests/fixtures scripts vendor
git -C $REPO diff --stat cb07a37 HEAD -- client | tail -1
for f in dictionary script workspace log config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application folders checked"
test -e $MAIN/client/script && echo "the main checkout has client/script"; echo "main checkout checked"
git -C $REPO status --short -- client docs scripts
```

Expected (no diff under `braille`, the fixtures, `scripts` and `vendor`; no application folder in the worktree; no `client/script` in the main checkout, whose other application data no test reaches):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e *-
 37 files changed, 3878 insertions(+), 737 deletions(-)
worktree application folders checked
main checkout checked
```

- [x] **Step 6: Criterion 7, mutation check** (20 mutants, Spec Corrections 11; a few minutes). Each mutant must be caught by at least one test.

```bash
$PY -B $T/tools/f18_mutants.py $REPO/client $T/mutants; echo "mutants exit $?"
```

Expected:

```text
1-no-processing-runs-its-file: 26 caught: test_gui_document_flows.test_build_conversion_request_for_text_reads_current_settings, test_gui_document_flows.test_close_in_the_delivery_gap_is_vetoed, test_gui_document_flows.test_close_that_cannot_be_vetoed_shuts_the_presenter_down, and 23 more
2-annotation-check-removed: 6 caught: test_text_scripts_manager.test_code_that_breaks_the_rule_is_not_valid_and_not_logged, test_text_scripts_manager.test_invalid_sources_copy_nothing, test_text_scripts_presenter.test_each_error_is_reported_and_nothing_is_copied, and 3 more
3-annotation-made-mandatory: 22 caught: test_conversion_service.test_a_script_error_of_the_contract_is_shown_in_zh_tw, test_conversion_service.test_conversion_reports_text_processing_stage, test_conversion_service.test_conversion_uses_processed_text_for_translation_and_dual_view, and 19 more
4-suffix-check-removed: 2 caught: test_text_scripts_manager.test_only_a_py_suffix_is_accepted, test_text_scripts_presenter.test_each_error_is_reported_and_nothing_is_copied
5-import-copies-decoded-text: 2 caught: test_text_scripts_manager.test_import_copies_the_original_bytes, test_text_scripts_presenter.test_import_asks_a_name_from_the_file_and_copies_its_bytes
6-delete-picks-the-neighbour: 1 caught: test_text_scripts_presenter.test_deleting_the_active_script_makes_no_processing_active
7-rename-keeps-the-old-active-name: 2 caught: test_text_scripts_presenter.test_a_case_only_rename_follows_the_active_script, test_text_scripts_presenter.test_renaming_the_active_script_makes_the_new_name_active
8-edit-enabled-for-no-processing: 2 caught: test_script_dialogs.test_no_processing_can_only_be_exported_and_a_user_script_everything, test_text_scripts_manager.test_no_processing_can_only_be_exported
9a-cancel-saves: 4 caught: test_script_dialogs.test_after_a_failed_apply_cancel_still_asks, test_script_dialogs.test_after_a_successful_apply_cancel_closes_without_asking, test_script_dialogs.test_cancel_without_a_change_closes_without_asking_or_saving, and 1 more
9b-add-writes-before-a-save: 2 caught: test_text_scripts_presenter.test_a_file_written_meanwhile_fails_the_first_save_and_is_kept, test_text_scripts_presenter.test_add_asks_a_name_then_opens_the_template_and_writes_nothing_without_a_save
10-question-without-a-change: 2 caught: test_script_dialogs.test_after_a_successful_apply_cancel_closes_without_asking, test_script_dialogs.test_cancel_without_a_change_closes_without_asking_or_saving
11-legacy-script-still-runs: 1 caught: test_conversion_service.test_the_legacy_script_next_to_the_dictionary_is_not_run
12-missing-script-reads-as-identity: 3 caught: test_conversion_service.test_a_selected_script_that_is_missing_fails_at_the_text_processing_stage, test_user_preprocessing_script.test_execution_of_a_missing_or_undecodable_script_fails, test_user_preprocessing_script.test_read_refuses_a_file_that_is_not_utf8_and_a_missing_file
13-reserved-names-case-sensitive: 2 caught: test_script_dialogs.test_each_refused_name_gets_its_message, test_text_scripts_manager.test_no_processing_names_are_reserved_in_any_case
14-no-processing-export-reads-the-file: 1 caught: test_text_scripts_manager.test_export_of_no_processing_writes_its_text_not_the_file
15-no-processing-status-read-from-disk: 3 caught: test_script_dialogs.test_a_locked_and_a_broken_script_do_not_stop_the_dialog, test_script_dialogs.test_each_script_shows_its_status, test_script_dialogs.test_no_processing_is_shown_translated_and_ready_without_reading_its_file
16-editor-compares-the-source: 1 caught: test_script_dialogs.test_cancel_without_a_change_closes_without_asking_or_saving
17-dictionary-choice-drops-the-script: 2 caught: test_gui_document_flows.test_font_size_and_dictionary_changes_report_through_the_same_flag, test_gui_document_flows.test_set_active_dictionary_keeps_the_selected_script
18-script-not-saved: 4 caught: test_gui_document_flows.test_no_box_when_the_settings_are_saved, test_translation_settings.test_save_calls_every_setter_and_returns_the_first_problem, test_translation_settings.test_save_persists_one_complete_settings_value, and 1 more
19-bom-refused: 4 caught: test_text_scripts_manager.test_a_valid_script_is_ready, test_text_scripts_presenter.test_edit_opens_the_text_of_the_file_and_saves_it, test_user_preprocessing_script.test_execution_runs_a_script_saved_with_a_bom, and 1 more
20-return-annotation-unchecked: 3 caught: test_text_scripts_manager.test_code_that_breaks_the_rule_is_not_valid_and_not_logged, test_user_preprocessing_script.test_an_annotation_other_than_str_is_refused, test_user_preprocessing_script.test_execution_rejects_externally_written_invalid_contract
mutants exit 0
```

### Task 5: Packaged build and GUI checks (Windows verification; run them yourself)

Rules as in F-13/F-14 (HANDOFF 2026-10-18-01 sections 4.6, 4.7 and 5). Not part of the replay.

- [x] **Step 1: Build** (PowerShell, in the worktree, with at least 2 GB free on C: and 600 MB available memory). The main checkout's venv is put first on `PATH`; `scripts\build-dotexpress.bat` calls `pyinstaller` from `PATH`. Nothing in the build changes for `script\`: `prepare_application_directories` creates it next to the exe at startup, as `dictionary\` (spec "Packaging"). Copy `client\dist\DotExpress.exe` to a new `D:\dxtest\N-f18`.

- [x] **Step 2: Write the GUI scripts** into `docs/superpowers/history/2026-10-18-02-f18-script-management/auto/` (tabs): `safe_run.py` and `f13gui.py` (F-13's start helper), `run_item.sh` (accepts only `D:\dxtest\auto*` folders, waits for 600 MB, puts the stand-in `chrome.exe` first on `PATH`, removes only the `_MEI*` folders its own processes made, as F-13's `mei_poll.ps1` records them), and one script per item.

- [x] **Step 3: The items** (Git Bash, from the repository root), each in a fresh `D:\dxtest\auto<N>-f18` folder on `D:\dxtest\N-f18\DotExpress.exe`; item 147 (the legacy script) also on `D:\dxtest\N-f14b` for the old behaviour. Read each log against Step 4 before the next run.

- [x] **Step 4: Expected behaviour.**

| # | Spec | Steps | Expected on N-f18 |
| --- | --- | --- | --- |
| 146 | 150 | Fresh folder, start | `script\no-processing.py` holds exactly `NO_PROCESSING_SCRIPT`; the Translation menu shows 「腳本管理...」 where 「文字處理」 was; Settings > Translation shows 「文字處理腳本」 = 「不處理」 |
| 147 | 151 | `dictionary\preprocessing.py` whose `main` returns `input.upper()`; convert `abc` | the Braille of lower-case `abc` (the script is not run); the file keeps its bytes; on N-f14b the same folder gives upper case |
| 148 | 152 | Script Management, 「不處理」 selected | Delete, Rename, Edit disabled; Add, Import, Export enabled; the row reads 「不處理」 「可使用」 |
| 149 | 153 | Add `upper`: the editor's title `upper`, the template text; replace with an upper-casing `main`; OK; select it in Settings; convert `abc` | `script\upper.py` holds the text; `config.json` has `selected_script` `upper`; the output is the Braille of `ABC` |
| 150 | 154 | Add `bad`, type `def main(a, b): return a`, Apply; Cancel | 「儲存腳本失敗：main 必須恰好定義一個位置參數，且不得有其他參數。」; focus back in the editor; no `bad.py`; Cancel asks 「要放棄對腳本「bad」所做的變更嗎？」; 放棄變更 closes; no `bad` in the list |
| 151 | 155 | Add with `def main(x: int) -> str` | the parameter-annotation message |
| 152 | 156 | Import `upper2.py` (valid, BOM and CRLF), `x.txt` typed by name, `cp950.py`, `bad.py` (syntax error) | the first is imported with the same bytes; the others each give 「匯入腳本失敗：…」 with its reason; nothing copied |
| 153 | 157 | Import a name that exists | 「腳本「upper」已存在。」 and the name prompt again |
| 154 | 158 | Rename the active `upper` to `Upper2`; Settings shows it; Delete it (Yes) | after Delete Settings shows 「不處理」; `config.json` has `no-processing`; conversion is unchanged text |
| 155 | 159 | Export 「不處理」 after altering `script\no-processing.py` | the exported file equals `NO_PROCESSING_SCRIPT`; conversion still identity |
| 156 | 160 | `script\locked.py` held open without read sharing by a helper process, `script\broken.py` with a syntax error; open Script Management | the dialog opens; 「無法讀取」 and 「格式不正確」; the reason field; Edit on `locked` shows 「無法讀取腳本「locked」。」 and the dialog stays; Edit on `broken` opens the editor |
| 157 | 161 | Select a user script, delete its file outside the app, convert; restart | 「文字處理失敗：…」 box; after the restart Settings shows 「不處理」 |
| 158 | 162 | Regression: the Dictionary Management flow (F-6/F-11 subset), a plain conversion of the golden text, the start helper | as in their earlier logs |

Manual for the user (NVDA), unchecked: **159** Script Management and Settings (the rows read as name and status, the disabled buttons, the reason field, the Settings choice 「文字處理腳本 下拉式方塊 不處理」); **160** the editor (the title as the script name, 「Python 程式碼」, the discard question read in full).

- [x] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-18-02-f18-script-management/auto-results.md` in the style of F-14's (zh-TW): the build, the method, then one row per item (146-158) with ✔/△/✘ and the result. Any deviation from Step 4 is reported, not explained away. End with a section **「仍需人工（使用者）」** for items 159-160 (unchecked). Add **Implementation Notes** at the end of this plan, then commit the history folder and this plan (docs only; `HEAD:client` stays `c825cb3b`).

## Implementation Notes (2026-10-18)

Planning and implementation were one run, by one agent (the orchestrator's rule since F-11).

1. **Commits and trees** (`HEAD:client` of each, equal to the Expected Counts): plan `0049399`; Task 1 `1a10232` `39db6b1856c8aa24e53e931f2d101838c08f94de` (`Ran 1725`); Task 2 `fa16143` `ef352d3c9d121f629192431ce10031bd33aec7f1` (`1748`); Task 3 `b84b3fe` `c825cb3bf2746815ebf3a76d995472cd3f0e2ef5` (`1788`); then the fix of note 4, `2e5057f` `c9b6ef97d4ed27835c829a77e53c8494dca4b8e1` (`1788`, one test changed). No commit has a `Co-Authored-By` line. The fixture sha256s of `HEAD` are unchanged. The full suite in the worktree after the fix: `Ran 1788`, `OK (skipped=6)`; 438 msgids, all translated, 0 fuzzy, 28 obsolete.
2. **Replays.** The code was written first on a dev clone (`$SP/f18dev`, red then green per task). Its Task 2 was amended afterwards (an unused `TranslationSettings` import in `gui.py`) without regenerating the catalogs, so the first replay (`r1`) gave other tree ids for Tasks 2 and 3: only the `#:` line numbers of the `.pot` and `.po` differed. `r1`'s commits became the development history; its Task 3 was amended twice (the new dialog test module looked up `dialog.ScriptEditorDialog` at import, so its red run crashed instead of listing failures; three blank lines left in `user_script.py`), and the blocks were generated again from that history. The record replay `r2` filled the expected blocks; the check replay `r3` had one mismatch, a temporary folder in a `WindowsPath` repr (forward slashes) that `brief.py` did not mask, so `brief.py` masks it now (Throwaway Tooling). The record replay `r4` recorded a flaky zip-timestamp failure of `test_rename_to_a_name_whose_package_is_on_disk_asks_again` in Task 3 Step 4 (Global Constraints), replaced by the clean result; the check replay `r5` on a fresh clone matched every other block. Landing in the worktree ran the same harness on `D:\workspace\DotExpress-f18` after the plan commit (`apply_blocks.py` for every step, the plan's own commit commands): 0 mismatches over all 23 blocks, including the full runs, the three tree ids, the three shuffled orders and the 20 mutants.
3. **Builds.** `D:\dxtest\N-f18\DotExpress.exe` from `b84b3fe` (48,822,215 bytes, sha256 `A143B617...78CBA7`) and, after note 4, `D:\dxtest\N-f18b\DotExpress.exe` from `2e5057f` (48,822,842 bytes, sha256 `D1C9BFFEF05B0EABF3938638F7A375ACC1EBEFD7768F7AD8655942633E71123C`); PyInstaller 6.21.0, `Build complete!`; the `text_scripts` modules and `shared.file_targets` are in the analysis. Nothing in the build script changed: `script\` is created next to the exe at startup (item 146).
4. **Deviation: the editor's accessible name.** GUI item 149 on `N-f18` read the editor's UIA name as `RichEdit Control`: `SetName` does not reach a screen reader (the removed Text Processing dialog had the same code). Commit `2e5057f` adds the label 「Python 程式碼」 right before the editor (an existing msgid), as Dictionary Management's reason field gets its name from the label before it (F-6 D3); red first (`test_script_dialogs`' build test), the catalogs change only in `#:` lines and the `.mo` keeps its bytes. On `N-f18b` the name is 「Python 程式碼」 (items 149, 150, 156). The label is visible above the code.
5. **GUI items.** The record is `docs/superpowers/history/2026-10-18-02-f18-script-management/auto-results.md`: items 146-158 on `N-f18b` all as Step 4 expects; 147 also on `N-f14b` (the old build runs the legacy script), 158 (a) also on `N-f14b` (identical Braille). Items 159-160 (NVDA) are manual and stay unchecked; their folder `D:\dxtest\manual159-f18` is prepared by `auto/manual159.py`. The `_MEI*` folders of ended processes were removed by `run_item.sh` (one per killed run); no other `%TEMP%` content was touched.
6. **Left for the user.** GUI items 159-160 (NVDA); the orchestrator's review and merge; D-E to D-H and O1-O9 (orchestrator defaults); the user-visible defaults this plan chose (Spec Corrections 5-9 and note 4: No Processing always 「可使用」, the add-race message inside the save box, the selection after Delete, the editor buttons from the standard sizer, 28 obsolete catalog entries kept, the visible 「Python 程式碼」 label); the clean-up of `D:\dxtest\auto*-f18*`, `N-f18` and the scratch clones.
