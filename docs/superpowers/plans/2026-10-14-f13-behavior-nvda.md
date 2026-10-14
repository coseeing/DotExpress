# Behaviour and NVDA Follow-ups (F-13) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ] `) syntax for tracking.

**Goal:** Four behaviour fixes a screen reader user meets, as the user decided on 2026-10-14 (U1, U2, U3, U5): after the failure box of a manual conversion whose document is no longer the open one, the focus goes to the open document's source editor (D1); the workspace is loaded, and its startup boxes shown, only after the main window is shown, so that NVDA reads them and Alt+Tab finds them (D2); at exit, liblouis and MathCAT are not freed while the conversion thread is still alive (D3, a logoff during a conversion); the dictionary editor's removal list shows the Bopomofo value exactly as it is in the file (D6). Item 5 is dropped (D5: the probe showed that Alt+F4 answers 移除並儲存 in a system Yes/No box). No new string (407 msgids); the catalogs change only in their `#:` lines (and one re-wrapped msgstr, Spec Corrections 2), the `.mo` stays byte-identical.

**Architecture:** Four commits, each red first, in the spec's migration order. Task 1 adds `ConversionPresenter._left_document` (the F-12 D7 naming condition), evaluated once per failure: it chooses the named message and, after the box, `focus_source_editor()` (D1). Task 2 replaces the last step of `BrailleFrame.__init__` with `_show_empty_startup_state` (empty editors, the title `DotExpress`), renames `_load_startup_documents` to a public `load_startup_documents` guarded by "runs once" and "not after the window closed", and makes `BrailleApp.OnInit` post it with `wx.CallAfter` after `Show()` (D2). Task 3 adds `ConversionPresenter.worker_alive` (the job runner's thread), `BrailleFrame.conversion_worker_check` (hands out that bound method), keeps it in `BrailleApp._conversion_worker_alive`, and makes `OnExit` skip `runtime.close()` while it answers true (D3). Task 4 drops `.strip()` from the Bopomofo value in `DictionaryEntriesDialog._hidden_row_line` (D6). Every task regenerates the template and the `.po` (`#:` lines move). Task 5 verifies (suite, shuffled order, catalogs, fixtures, application data, 17 mutants); Task 6 builds the exe and runs GUI items 121-130 (131 stays manual).

**Tech Stack:** Python 3.13 standard library (`unittest`, `unittest.mock`, `collections.abc.Callable`), wxPython 4.2.5 (`wx.CallAfter`), GNU gettext 0.23 (`xgettext`, `msgmerge`, `msgfmt`), Git Bash `unix2dos`. Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-14-f13-behavior-nvda-design.md` (+ `_zh-TW.md`), with the section "Corrected after planning (F-13, 2026-10-14)" / 「規劃後的修正（F-13，2026-10-14）」 added in the plan commit (both languages). The user decided U1-U5 (2026-10-14); D5 follows U4's own rule. O1-O5 and Q1 (a) are the orchestrator's recommended defaults; the user may override them before the merge. The refinements of "Spec Corrections and Refinements" below are defaults of the same kind.

## Global Constraints

- Work in the worktree `D:\workspace\DotExpress-f13`, branch `fix/f13-behavior-nvda` (HEAD is the plan commit on top of the spec commit `1d07c04`, which is on `main` at `a147fed`, the F-12 merge). Never switch branches, never push, never merge, never rewrite history. The worktree has no `client\.venv`: `PY` is the main checkout's interpreter, run with the working directory inside the worktree. Do not work in the main checkout `D:\workspace\DotExpress` (the user may run the app from source there).
- Files that may change (under `client/`, nothing else there): production `client/ui/conversion_presenter.py` (4 spaces), `client/gui.py` (**tabs**, but its import blocks use 4 spaces), `client/dialog.py` (**tabs**); tests `client/tests/test_conversion_presenter.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_dictionary_entries_dialog.py` (4 spaces); catalogs `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` (`#:` lines; the `.mo` must keep its bytes); in Task 6 the history folder `docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/` (`auto/` scripts with tabs, `auto-results.md`) and this plan's Implementation Notes. `client/ui/message_box.py` does not change (D5).
- Never touch, in the main checkout `D:\workspace\DotExpress`, `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data; Task 0 and Task 5 only hash them), or its untracked `client2/`, `preprocessing/`, `testdata/` and `task.md` (read-only). In the worktree no test may create `client/log/`, `client/workspace/` or `client/config.json`. Never touch `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (CRLF bytes), tracked `client/braille/` content, `client/braille/liblouis/`, `client/tests/fixtures/`, `scripts/`, `vendor/`, the submodule pointers, or the committed scripts and data of earlier history folders. Never run `py scripts\sync-nvda.py`. Never start `gui.py` from source in any checkout: only packaged copies, each in a new `D:\dxtest\auto*-f13` folder. **Never write to the Windows clipboard**: no test, probe or GUI script of this plan does (no `SetClipboardData`, no Ctrl+C/V/X, no `wx.TheClipboard`; text reaches the app through files and `set_edit_text`). `git status --short -- client docs scripts` must stay empty between commits.
- The worktree uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply the blocks **with a script that reads them from this file** (`$T/tools/apply_blocks.py`, Task 0 Step 3), not by hand: a `File:` block is written as is; an `Edit:` block is the line ``Edit: `path` `` followed by two fenced blocks, the exact old text and its replacement; the old text must occur exactly once in the file at that point (compared with CRLF converted to LF; the file keeps its line endings). Never edit with MSYS `sed -i` and never paste code through a shell heredoc. `test_dictionary_entries_dialog.py` is ASCII and spells every other character as a backslash-u escape, and `gui.py` and `test_gui_document_flows.py` hold a few: the Edit/Write tools turn such an escape into its character, so never patch these files through them. `apply_blocks.py` reads and writes bytes; the tree id check after each commit catches any other change.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`, `translation_liblouis_golden.json` `8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e` (`git show HEAD:<path> | sha256sum`), unchanged after every commit.
- Catalogs: `POT-Creation-Date` stays `2026-10-10 12:00+0800` (pinned by `$T/tools/pin_pot_date.py` after `generate-pot.bat`), so the `.pot`, `.po` and `.mo`, and with them the tree id, are the same in every run. The `.mo` is rebuilt by `msgfmt` in every task and must stay byte-identical to `a147fed`'s (sha256 `dcf50a626cc5e80dbe0dbacbd07575f4fa8b9ea830b243c2ebaa608ff0f29e32`).
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -q -m "<subject>" [-m "<body>"]`, the subject ending in `(F-13)`, **no `Co-Authored-By` line** (HANDOFF 2026-10-14-01 section 5); stage only the files the task names, explicitly; look at `git diff --cached --stat` first; never `git commit -F -`.
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (F-12's: FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`, the random part of a temporary file name as `<rnd>`, object addresses as `<addr>`). Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks. Tests run as `$PY -B -X utf8 -m unittest ...` (no bytecode in the worktree).
- Some tests that write packages were seen to fail now and then on this machine during planning and to pass on the next run, unrelated to F-13 (they touch code F-13 does not change): `test_workspace_service.ReplacedNulCharactersTest.test_unopened_document_keeps_its_package_and_count` (twice; `PermissionError` [WinError 5] from `os.replace`: the new file is briefly held by another process, such as a virus scanner), `test_document_workspace`'s `test_save_replaces_lone_surrogates_with_the_replacement_character` (an error in one shuffled run, Task 5 Step 3), and `test_rename_to_a_name_whose_package_is_on_disk_asks_again` (the package's zip timestamp moved by one 2-second step). If a run shows one of them, run it again; report it, do not change code for it.
- Memory (the machine has 8 GB and once ended jobs for low memory): run one heavy job at a time (a replay, a test suite, the mutants, the build, a GUI item), each only when PowerShell `(Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue` shows at least 600; otherwise wait. If the system ends a job, stop and report; do not restart it unasked.
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress-f13
  MAIN=/d/workspace/DotExpress
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f13impl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the main checkout: only its interpreter is used, its git-ignored runtime is copied into the worktree (Task 0 Step 2), and its application data is hashed read-only (Task 0 Step 4, Task 5 Step 5). The dry run used scratch clones as `REPO`. Task 6 uses PowerShell for the build and the UIA venv for the GUI scripts.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning (F-13, 2026-10-14)" in the plan commit. Re-checked against the code of `main` `a147fed`: every decision D1-D6, the behaviour table, the probe and the test plan hold, with the refinements below. Function names are as the spec gives them unless named here; line numbers moved (orientation only).

1. **Baseline and counts.** On `a147fed` (`HEAD:client` `a967d8d4`) the suite gives `Ran 1632`, `OK (skipped=6)`; the catalogs hold 407 msgids. F-13 adds 14 tests and changes 4: `Ran 1634` after Task 1 (2 new, 1 flipped), `1638` after Task 2 (4 new, 2 changed), `1645` after Task 3 (7 new), `1646` after Task 4 (1 new, 1 flipped and renamed). The spec estimated about 14 new and 4 changed.
2. **Catalogs in every task.** Each of the four tasks moves lines above msgids (`conversion_presenter.py`, `gui.py`, `dialog.py`), so each regenerates the template and the `.po` (`generate-pot.bat`, the pinned date, `msgmerge`) and rebuilds the `.mo` (unchanged bytes); no `#:` reference is stale after any commit, and no separate `chore:` commit is needed. `msgmerge` also re-wraps one msgstr that F-12's fix commit wrote on one line (`無法寫入檔案。…請關閉其他程式後再試一次。`, the "file cannot be written" reason): the same text in two lines, so the `.po` differs from `a147fed`'s in that entry's layout too (Task 1). The `.mo` is byte-identical.
3. **D1 as built.** `_left_document(target)` is `target.document_name is not None and target.document_name != open_document_name`. `_on_job_failure` evaluates it once, before the box: true gives the named message (F-12 D7) and, after `show_error` returns, `focus_source_editor()`; false gives the reason alone and no focus call. `_name_unopened_document` now only formats string 23. Test A2's "import" adds a document to the controller and opens it while the job runs. Test A4 queues an export behind the failing conversion and pins `show_error`, `focus_source_editor`, then the start of the queued job.
4. **D2 as built.** The light last step of `__init__` is `_show_empty_startup_state` (`_clear_document_editors`, `_update_window_title`); the "runs once" flag is a class attribute `_startup_documents_loaded`, like `_close_finished`, because tests build frames without `__init__`. `BrailleApp.OnInit` calls `wx.CallAfter(self.frame.load_startup_documents)` right after `Show()`. Test B2 records the post itself (`"post"` between `"show"` and `"client_init"`), so a post before `Show()` is caught. The wx stub answers an unknown attribute with a no-op, so a test that only expects "nothing happens" would pass on the old code: test B3 runs the same call with the window open (it loads) and closed (nothing), and test B5 uses a workspace with all three boxes (`bad.dep` invalid, the interrupted rename of `alpha` whose text holds U+0000) and pins invalid files, recovered, the title, replaced, the two titles and the focus last. A frame with one document sets its title three times during the load (open, end of the load, `load_startup_documents`); the tests pin that.
5. **D3 as built.** `ConversionPresenter.worker_alive()` returns `self._runner.is_running()`; `BrailleFrame.conversion_worker_check()` returns the presenter's bound `worker_alive` (`gui.py` imports `Callable` from `collections.abc` for its annotation); `BrailleApp` keeps it in `_conversion_worker_alive` (a class attribute `None` until `OnInit` builds the frame, which it sets before `Show()`), and `OnExit` asks `_conversion_worker_is_alive()` (false without a check). Test C4 calls `mock_add_spec([])` on the frame stand-in after `OnInit`, so any attribute access through the frame raises, as on a destroyed wx frame. One test more than the spec lists: the frame's `conversion_worker_check` hands out the presenter's `worker_alive`.
6. **D6 test values.** `ㄇㄚ␠␠`, `␠ㄇㄚ`, `ㄇㄚ` + tab and `ㄇㄚ` + U+3000 are all hidden on `a147fed` (checked by the red run: each is listed, as `「ㄇㄚ」`), so one test with four subtests lists each unchanged.
7. **Mutation check: 17 mutants** (Task 5 Step 6): the spec's 15, plus the empty start state without the title update, and the frame's check handing out `is_running` instead of `worker_alive`. Mutant 6 (load posted before `Show()`) is behaviourally the same in real wx (the posted call runs after `OnInit` either way); test B2 catches it by the order of the post.
8. **Commit subjects** end in `(F-13)` (the orchestrator's rule for this task); the spec's subjects 2 and 3 carry `F-8b review M-8` and `F-9 review M-8` in the commit body instead.
9. **Windows items.** The old build is `D:\dxtest\N-f12b` (the code of `main` `a147fed`), the new one `D:\dxtest\N-f13`. Fix items 121-125, 127, 129 run on both, regression items 126, 128, 130 on `N-f13` only. Item 127 also writes a stale `dual_view\dual-view-f13probe.html` after the start: if it is gone after the process ended, `OnExit` ran on the `WM_ENDSESSION` path (the spec's "to be confirmed by GUI item 127"). `f13gui.start` is the spec's start helper; earlier item scripts rerun in item 126 get it in place of `f8bgui.start` (Task 6 Step 2).

## Dry Run

The plan was replayed on scratch clones of the branch with a stand-in plan commit (this plan and the corrected spec files) on `fix/f13-behavior-nvda` (`$SP/f13plan/r*`, never the worktree or the main checkout), by F-12's harness: it applies every step's blocks with Task 0 Step 3's `apply_blocks.py`, runs every `bash` block from `client/` with `REPO` set to the clone and `MAIN` to the main checkout (so Task 0's guarded copies filled the clone, and the application-data check read the real data read-only), and compares its stdout with the following `text` block. The code was developed first on a separate clone, red first, in the same four steps; the blocks are that clone's diffs, and its tree ids equal the replay's. The results are in the Implementation Notes.

## Review Focus

1. **D1:** one evaluation of `_left_document` for the message and the focus; the focus call after `show_error` and before the next queued job; no focus call for the open document, for a manual job without a document, or for an export (Test Plan A; 4 mutants; GUI 121).
2. **D2:** nothing loaded in `__init__`; the post right after `Show()`; the two guards; the old order of the boxes and the final focus; earlier GUI start helpers return too early on the new build (Test Plan B; 5 mutants; GUI 122-126).
3. **D3:** the check reads the presenter's runner, not the frame and not `is_running`; `OnExit` without a frame still closes the runtime; nothing is joined or logged (Test Plan C; 5 mutants; GUI 127, 128).
4. **D6:** the raw value, the stripped source text (Test Plan D; 3 mutants; GUI 129).
5. **Catalogs:** `#:` lines and the one re-wrapped msgstr only; the `.mo` byte-identical (Spec Corrections 2).

## File Map

- Task 1: `client/tests/test_conversion_presenter.py`; `client/ui/conversion_presenter.py`; the template and the `.po`.
- Task 2: `client/tests/test_gui_document_flows.py`; `client/gui.py`; the template and the `.po`.
- Task 3: `client/tests/test_conversion_presenter.py`, `client/tests/test_gui_document_flows.py`; `client/ui/conversion_presenter.py`, `client/gui.py`; the template and the `.po`.
- Task 4: `client/tests/test_dictionary_entries_dialog.py`; `client/dialog.py`; the template and the `.po`.
- Task 6: `docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/` (`auto/` scripts, `auto-results.md`), this plan's Implementation Notes.

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | msgids | `HEAD:client` |
| --- | --- | --- | --- | --- | --- |
| baseline (`a147fed` + spec + plan) | - | 1632 | `OK (skipped=6)` | 407 | `a967d8d4cea147cf25ccc0f490c8f94e41e711ce` |
| 1 focus after a failed conversion | 2 | 1634 | `OK (skipped=6)` | 407 | `697fddea6075594d525134b4213cdc6271911ed2` |
| 2 startup boxes after Show | 4 | 1638 | `OK (skipped=6)` | 407 | `d1509b937c40acb55efa98aa43594485a921e045` |
| 3 runtime kept while a conversion runs | 7 | 1645 | `OK (skipped=6)` | 407 | `8ffb2e1c26339f643d06f8bde1aa2bf6de2ea7b6` |
| 4 raw Bopomofo value | 1 | 1646 | `OK (skipped=6)` | 407 | `6c352f0225a9167e33e2977b7ad34c7c2427f480` |
| 6 GUI results (docs only) | - | 1646 | `OK (skipped=6)` | 407 | `6c352f0225a9167e33e2977b7ad34c7c2427f480` |

"Tests added" is the net count (a flipped or changed test counts as neither). The 6 skips are POSIX-only tests.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 by the block script: `brief.py`, `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` (F-12's, unchanged), `f13_mutants.py` (17 mutants of the code after Task 4, run on a copy of `client/`; the repository is never changed) and `apply_blocks.py` (F-12's with its docstring naming this plan; applies the `File:` and `Edit:` blocks of one step).

---

### Task 0: Baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short -- client docs scripts
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO rev-parse HEAD~1 HEAD~2 HEAD~2:client
git -C $REPO diff --stat a147fed -- client
```

Expected (`status` and the diff print nothing; `HEAD~1` is the spec commit, `HEAD~2` is `main` at `a147fed`):

```text
docs: plan for behaviour and NVDA follow-ups (F-13)
fix/f13-behavior-nvda
1d07c04962364101b7f657073531d6bdca3efbe4
a147fedd2adbcacbdd9fad1a7ddeadc291af3c2d
a967d8d4cea147cf25ccc0f490c8f94e41e711ce
```

- [ ] **Step 2: The git-ignored runtime the tests load.** A worktree is made without the generated liblouis DLL and tables, `louis_helper.py`, MathCAT and the submodule's `configure.ac`; the guarded copies below bring them from the main checkout, as F-3's Task 0 did (in a worktree that has them already they do nothing). Never stage these files.

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

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed). `brief.py`, `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` are F-12's, unchanged; `apply_blocks.py` is F-12's with its docstring naming this plan.

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

File: `$T/tools/f13_mutants.py`

````python
"""Run the F-13 tests against deliberately broken code (throwaway, not committed).

Usage: python f13_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one file of the copy (one exact, unique replacement), runs the F-13 test
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

PRESENTER = "ui/conversion_presenter.py"
GUI = "gui.py"
DIALOG = "dialog.py"
SHOW_ERROR = '                self._view.show_error(self._name_unopened_document(target, message) if left else message, _("Error"))\n'
FOCUS = "                if left:\n"
MUTANTS = {
    # D1: the focus after the failure box of a document that is no longer open.
    "focus-after-every-manual-failure": (PRESENTER, FOCUS, "                if True:\n"),
    "focus-never": (PRESENTER, FOCUS, "                if False:\n"),
    "focus-before-the-box": (
        PRESENTER,
        SHOW_ERROR + FOCUS,
        "                if left:\n                    self._view.focus_source_editor()\n" + SHOW_ERROR + "                if False:\n",
    ),
    "left-condition-inverted": (
        PRESENTER,
        "        return target.document_name is not None and target.document_name != self._documents.open_document_name\n",
        "        return target.document_name is not None and target.document_name == self._documents.open_document_name\n",
    ),
    # D2: the workspace load after Show.
    "load-still-in-init": (
        GUI,
        "\t\tself._show_empty_startup_state()\n",
        "\t\tself._show_empty_startup_state()\n\t\tself.load_startup_documents()\n",
    ),
    "load-posted-before-show": (
        GUI,
        "\t\tself.frame.Show()\n"
        "\t\t# The workspace is loaded once the main window is visible, so that NVDA and Alt+Tab\n"
        "\t\t# find the startup boxes (F-13 D2, F-8b review M-8).\n"
        "\t\twx.CallAfter(self.frame.load_startup_documents)\n",
        "\t\twx.CallAfter(self.frame.load_startup_documents)\n\t\tself.frame.Show()\n",
    ),
    "no-close-finished-guard": (
        GUI,
        "\t\tif self._startup_documents_loaded or self._close_finished:\n",
        "\t\tif self._startup_documents_loaded:\n",
    ),
    "no-run-once-guard": (
        GUI,
        "\t\tif self._startup_documents_loaded or self._close_finished:\n",
        "\t\tif self._close_finished:\n",
    ),
    "empty-state-keeps-the-old-title": (
        GUI,
        '\t\t"""The window before the workspace is loaded: empty editors, the title DotExpress (F-13 D2)."""\n'
        "\t\tself._clear_document_editors()\n\t\tself._update_window_title()\n",
        '\t\t"""The window before the workspace is loaded: empty editors, the title DotExpress (F-13 D2)."""\n'
        "\t\tself._clear_document_editors()\n",
    ),
    # D3: the runtime at exit while a conversion thread runs.
    "close-always": (
        GUI,
        "\t\tif runtime is not None and not self._conversion_worker_is_alive():\n",
        "\t\tif runtime is not None:\n",
    ),
    "close-never": (
        GUI,
        "\t\tif runtime is not None and not self._conversion_worker_is_alive():\n",
        "\t\tif False:\n",
    ),
    "worker-alive-reads-is-running": (PRESENTER, "        return self._runner.is_running()\n", "        return self.is_running()\n"),
    "check-reads-the-frame": (
        GUI,
        "\t\tself._conversion_worker_alive = self.frame.conversion_worker_check()\n",
        "\t\tself._conversion_worker_alive = lambda: self.frame.conversion_worker_check()()\n",
    ),
    "frame-check-is-is-running": (
        GUI,
        "\t\treturn self._conversion_presenter.worker_alive\n",
        "\t\treturn self._conversion_presenter.is_running\n",
    ),
    # D6: the raw Bopomofo value in the removal list.
    "bopomofo-stripped": (DIALOG, "\t\t\tbopomofo=row.braille,\n", "\t\t\tbopomofo=row.braille.strip(),\n"),
    "bopomofo-rstripped": (DIALOG, "\t\t\tbopomofo=row.braille,\n", "\t\t\tbopomofo=row.braille.rstrip(),\n"),
    "source-text-not-stripped": (DIALOG, "\t\t\ttext=row.text.strip(),\n", "\t\t\ttext=row.text,\n"),
}
MODULES = (
    "tests.test_conversion_presenter",
    "tests.test_gui_document_flows",
    "tests.test_dictionary_entries_dialog",
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
                [sys.executable, "-B", "-X", "utf8", "-m", "unittest", *MODULES],
                cwd=copy, capture_output=True, text=True, encoding="utf-8", errors="replace",
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
"""Apply the File: and Edit: blocks of one step of the F-13 plan (throwaway, not committed).

Usage: python apply_blocks.py <plan.md> <repo> <T> "<task>" "<step>"
  for example: python apply_blocks.py plan.md D:/workspace/DotExpress-f13 <T> "Task 1" "Step 1"

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
PLAN=$REPO/docs/superpowers/plans/2026-10-14-f13-behavior-nvda.md
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
wrote $T/tools/f13_mutants.py
wrote $T/tools/apply_blocks.py
6 blocks applied (Task 0, Step 3)
```

From then on apply every step's blocks with `apply_blocks.py`, for example `$PY $T/tools/apply_blocks.py ../docs/superpowers/plans/2026-10-14-f13-behavior-nvda.md $REPO $T "Task 1" "Step 1"`; it prints `N blocks applied`.

- [ ] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, catalogs, tree, application data.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows tests.test_dictionary_entries_dialog tests.test_message_box tests.test_wx_call_sites tests.test_i18n 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/translation_liblouis_golden.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "msgfmt rebuilds the committed .mo byte for byte"
sha256sum < locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO rev-parse HEAD:client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) > $T/app-data.sha256; echo "application data hashed"
for f in log workspace config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application data checked"
```

Expected (the second `Ran` line is the spec's acceptance-criterion-2 set; the application data are the user's files in the main checkout, hashed read-only for Task 5; the worktree has none):

```text
Ran 1632 tests
OK (skipped=6)
Ran 418 tests
OK
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e *-
source msgids: 407 sha256 5daf57d13375a21e9a36b7bf1782976a3d6f14ae9f7c290ae89602b6de943e88
locales/dotexpress.pot:408
locales/zh_TW/LC_MESSAGES/dotexpress.po:408
407 translated messages.
msgfmt rebuilds the committed .mo byte for byte
dcf50a626cc5e80dbe0dbacbd07575f4fa8b9ea830b243c2ebaa608ff0f29e32 *-
a967d8d4cea147cf25ccc0f490c8f94e41e711ce
application data hashed
worktree application data checked
```

### Task 1: Focus the source editor after a failed conversion of a document that is no longer open (D1)

- [ ] **Step 1: Red: Test Plan A.** `test_conversion_presenter.py` (4 spaces): `test_a_failure_after_switching_names_the_document` flips (the events end with `("focus_source_editor",)` after the box); new: a failure after an import opened another document (named, then the focus), and the focus before the queued job starts. The tests that pin "no focus call" (the open document, away and back, no starting document, `test_manual_failure_shows_error_after_busy_off`, `test_export_failure_calls_only_on_error`) stay as they are.

Edit: `client/tests/test_conversion_presenter.py`

```python

    def test_a_failure_after_switching_names_the_document(self) -> None:
        # F-12 (D7, F-9 review M-9): the box would otherwise seem to be about the open document.
        events = self._failed_after(lambda: self._switch_to("beta"))

        self.assertEqual(
            events,
            self._end() + [("show_error", "無法轉換文件「alpha」。\n\n轉譯失敗：boom", "錯誤")],
        )

    def _not_named(self) -> list:
```

```python

    def test_a_failure_after_switching_names_the_document(self) -> None:
        # F-12 (D7, F-9 review M-9): the box would otherwise seem to be about the open document.
        # F-13 (D1): after the box the focus goes to the open document's source editor.
        events = self._failed_after(lambda: self._switch_to("beta"))

        self.assertEqual(
            events,
            self._end() + [("show_error", "無法轉換文件「alpha」。\n\n轉譯失敗：boom", "錯誤"), ("focus_source_editor",)],
        )

    def test_a_failure_after_an_import_opened_another_document_names_it_and_focuses(self) -> None:
        # F-13 (D1): an import during the job opens the imported document, as a switch does.
        def import_and_open() -> None:
            self.documents.add_document(Document("imported", "i", None))
            self._switch_to("imported")

        events = self._failed_after(import_and_open)

        self.assertEqual(
            events,
            self._end() + [("show_error", "無法轉換文件「alpha」。\n\n轉譯失敗：boom", "錯誤"), ("focus_source_editor",)],
        )

    def test_the_focus_after_a_failure_comes_before_the_queued_job_starts(self) -> None:
        # F-13 (D1): the focus call is part of the completion; the queued export starts after it.
        self.outputs.update(
            {"source": ConversionStageError("translation", RuntimeError("boom")), "doc text": ConversionOutput("export", ())}
        )
        presenter = self._presenter()
        presenter.convert()
        self._switch_to("beta")
        presenter.convert_for_export("doc text", **self._export_callbacks())
        self.threads[0].run()
        self._take()

        self.calls.run_next()

        self.assertEqual(
            self._take(),
            self._end()
            + [("show_error", "無法轉換文件「alpha」。\n\n轉譯失敗：boom", "錯誤"), ("focus_source_editor",)]
            + self._started(2),
        )

    def _not_named(self) -> list:
```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter 2>&1 | $PY $T/tools/brief.py
```

Expected (the three tests miss the focus call):

```text
FAIL: test_a_failure_after_an_import_opened_another_document_names_it_and_focuses (tests.test_conversion_presenter.ConversionPresenterTest.test_a_failure_after_
AssertionError: Lists differ: [('ti[77 chars]'無法轉換文件「alpha」。\n\n轉譯失敗：boom', '錯誤')] != [('ti[77 chars]'無法轉換文件「alpha」。\n\n轉譯失敗：boom', '錯誤'), ('focus_source_editor
FAIL: test_a_failure_after_switching_names_the_document (tests.test_conversion_presenter.ConversionPresenterTest.test_a_failure_after_switching_names_the_docume
FAIL: test_the_focus_after_a_failure_comes_before_the_queued_job_starts (tests.test_conversion_presenter.ConversionPresenterTest.test_the_focus_after_a_failure_
AssertionError: Lists differ: [('ti[112 chars]), ('busy', True), ('close_converting_dialog',[25 chars]2,))] != [('ti[112 chars]), ('focus_source_editor',), ('bu
Ran 45 tests
FAILED (failures=3)
```

- [ ] **Step 2: Green: `_left_document`, evaluated once; the focus call after the box** (`client/ui/conversion_presenter.py`, 4 spaces).

Edit: `client/ui/conversion_presenter.py`

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
```

```python
            if active.job.export is not None:
                active.job.export.on_error(message)
            else:
                target = active.job.manual
                left = self._left_document(target)
                self._view.show_error(self._name_unopened_document(target, message) if left else message, _("Error"))
                if left:
                    # The source editor was disabled during the job, so the focus is in the
                    # read-only Braille Result editor; after the box it goes to the open
                    # document's source editor, as after a case (b) result (F-13 D1).
                    self._view.focus_source_editor()
        finally:
            self._finish_completion()

    def _left_document(self, target: _ManualTarget) -> bool:
        """Whether the job's document is no longer the open one (F-12 D7, F-13 D1).

        Then the failure box names it, and the focus goes to the source editor after the box.
        """
        return target.document_name is not None and target.document_name != self._documents.open_document_name

    def _name_unopened_document(self, target: _ManualTarget, message: str) -> str:
        """``message``, led by the name of the job's document, which is not open (F-12 D7)."""
        return _('Document "{name}" could not be converted.\n\n{error}').format(name=target.document_name, error=message)

    def _complete_manual(self, target: _ManualTarget, output: ConversionOutput) -> None:
```

- [ ] **Step 3: Regenerate the catalogs** (no new string; the `#:` references of `conversion_presenter.py` move; `msgmerge` re-wraps one msgstr, Spec Corrections 2; the `.mo` keeps its bytes).

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
git -C $REPO diff -- client/locales | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[-+]#: '
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (besides `#:` lines, only the re-wrapped msgstr changes; the `.mo` is not in the diff):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
a second msgmerge changes nothing
msgfmt exit 0
407 translated messages.
 client/locales/dotexpress.pot                  | 12 ++++++------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 16 +++++++++-------
 2 files changed, 15 insertions(+), 13 deletions(-)
-msgstr "無法寫入檔案。檔案可能正被其他程式使用，或你沒有寫入權限。請關閉其他程式後再試一次。"
+msgstr ""
+"無法寫入檔案。檔案可能正被其他程式使用，或你沒有寫入權限。請關閉其他程式後再"
+"試一次。"
source msgids: 407 sha256 5daf57d13375a21e9a36b7bf1782976a3d6f14ae9f7c290ae89602b6de943e88
```

- [ ] **Step 4: Green: the changed tests, the module, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter -v 2>&1 | grep -E "^test_a_failure|^test_the_focus_after|^test_manual_failure_shows|^test_export_failure_calls" | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_conversion_presenter 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_a_failure_after_an_import_opened_another_document_names_it_and_focuses ok
test_a_failure_after_switching_away_and_back_is_not_named ok
test_a_failure_after_switching_names_the_document ok
test_a_failure_of_the_open_document_is_not_named ok
test_a_failure_without_a_starting_document_is_not_named ok
test_export_failure_calls_only_on_error ok
test_manual_failure_shows_error_after_busy_off ok
test_the_focus_after_a_failure_comes_before_the_queued_job_starts ok
Ran 45 tests
OK
Ran 1634 tests
OK (skipped=6)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/test_conversion_presenter.py client/ui/conversion_presenter.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: focus the source editor after a failed conversion of a document that is no longer open (F-13)"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
 client/locales/dotexpress.pot                  | 12 ++++-----
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 16 ++++++-----
 client/tests/test_conversion_presenter.py      | 37 +++++++++++++++++++++++++-
 client/ui/conversion_presenter.py              | 20 +++++++++++---
 4 files changed, 67 insertions(+), 18 deletions(-)
697fddea6075594d525134b4213cdc6271911ed2
```

### Task 2: Show the startup boxes after the main window (D2)

- [ ] **Step 1: Red: Test Plan B.** `test_gui_document_flows.py` (4 spaces): the last of `STARTUP_STEPS` is `_show_empty_startup_state`; new: building the frame loads nothing (only the empty editors and the title); `test_app_startup_runs_steps_in_contract_order` records the post and the posted load; new: the order of the boxes and the final focus after `load_startup_documents`, the run-once guard and the closed-window guard.

Edit: `client/tests/test_gui_document_flows.py`

```python
        "_initialize_conversion_state",
        "_apply_initial_settings",
        "_bind_events",
        "_load_startup_documents",
    )

    def test_frame_creates_its_controller_before_building_the_menu_bar(self) -> None:
```

```python
        "_initialize_conversion_state",
        "_apply_initial_settings",
        "_bind_events",
        "_show_empty_startup_state",
    )

    def test_frame_creates_its_controller_before_building_the_menu_bar(self) -> None:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertIsInstance(seen[0], gui.DocumentController)
        self.assertIs(frame._document_controller, seen[0])
        self.assertEqual(seen[0].documents, [])

    def test_initialize_state_keeps_the_frame_controller(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
```

```python
        self.assertIsInstance(seen[0], gui.DocumentController)
        self.assertIs(frame._document_controller, seen[0])
        self.assertEqual(seen[0].documents, [])

    def test_building_the_frame_does_not_load_the_workspace(self) -> None:
        # F-13 (D2): BrailleApp.OnInit posts load_startup_documents after Show; the frame
        # starts with empty editors and the title DotExpress.
        steps = Mock()
        with (
            patch.object(gui.BrailleFrame, "_initialize_frame"),
            patch.multiple(gui.BrailleFrame, **{name: DEFAULT for name in self.STARTUP_STEPS[:-1]}),
            patch.object(gui.BrailleFrame, "_clear_document_editors", steps.clear_editors),
            patch.object(gui.BrailleFrame, "_update_window_title", steps.update_title),
            patch.object(gui.BrailleFrame, "_load_workspace_documents_at_startup", steps.load_workspace),
            patch.object(gui.BrailleFrame, "load_startup_documents", steps.load_startup_documents, create=True),
        ):
            gui.BrailleFrame(None, runtime=Mock(), paths=make_paths(), config_store=Mock())

        self.assertEqual(steps.mock_calls, [call.clear_editors(), call.update_title()])

    def test_initialize_state_keeps_the_frame_controller(self) -> None:
        frame = object.__new__(gui.BrailleFrame)
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        frame = Mock()
        frame.Show.side_effect = record("show")
        return {
            "prepare_application_directories": prepare,
            "cleanup_dual_view_html": record("cleanup"),
```

```python

        frame = Mock()
        frame.Show.side_effect = record("show")
        frame.load_startup_documents.side_effect = record("load")
        return {
            "prepare_application_directories": prepare,
            "cleanup_dual_view_html": record("cleanup"),
```

Edit: `client/tests/test_gui_document_flows.py`

```python

    def test_app_startup_runs_steps_in_contract_order(self) -> None:
        order: list[str] = []

        with ExitStack() as stack:
            for name, fake in self._startup_recorders(order).items():
                stack.enter_context(patch.object(gui, name, side_effect=fake))
            message_box = stack.enter_context(patch.object(gui, "message_box"))
            result = gui.BrailleApp().OnInit()

        self.assertTrue(result)
        self.assertEqual(order, ["prepare", "cleanup", "runtime", "frame", "show", "client_init"])
        message_box.assert_not_called()

    def test_app_stops_before_cleanup_when_validation_fails(self) -> None:
```

```python

    def test_app_startup_runs_steps_in_contract_order(self) -> None:
        order: list[str] = []
        posted = DeferredCalls()

        def call_after(fn, *args, **kwargs) -> None:
            order.append("post")
            posted(fn, *args, **kwargs)

        with ExitStack() as stack:
            for name, fake in self._startup_recorders(order).items():
                stack.enter_context(patch.object(gui, name, side_effect=fake))
            stack.enter_context(patch.object(gui.wx, "CallAfter", call_after))
            message_box = stack.enter_context(patch.object(gui, "message_box"))
            result = gui.BrailleApp().OnInit()

        self.assertTrue(result)
        # F-13 (D2): the workspace load is posted after Show and runs in a later turn of the
        # main loop, when the main window is visible; its boxes are owned by a shown window.
        self.assertEqual(order, ["prepare", "cleanup", "runtime", "frame", "show", "post", "client_init"])
        self.assertEqual(posted.run_all(), 1)
        self.assertEqual(order[-1], "load")
        message_box.assert_not_called()

    def test_app_stops_before_cleanup_when_validation_fails(self) -> None:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        # Both staged twins duplicate a recovered document and are removed; the invalid
        # bad.dep is not a temporary file and stays.
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep", "beta.dep"])

    # --- save --------------------------------------------------------------

```

```python
        # Both staged twins duplicate a recovered document and are removed; the invalid
        # bad.dep is not a temporary file and stays.
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep", "beta.dep"])

    def test_startup_load_shows_the_boxes_in_order_and_focuses_the_source_editor_last(self) -> None:
        # F-13 (D2): load_startup_documents, posted after Show, keeps the order of the startup
        # boxes: the invalid files, the recovered documents, then the replaced characters of
        # the first document; the focus goes to the source editor at the end.
        self._interrupted_rename("alpha", "gamma", "a\x00", 60)
        (self.workspace / "bad.dep").write_bytes(b"not a zip")
        frame = self._make_workspace_frame()

        frame.load_startup_documents()

        recovered = gui._(
            "DotExpress was interrupted while saving or renaming a document. These documents were "
            "recovered:\n\n{names}\n\nCheck that their content is what you expect."
        ).format(names="alpha")
        self.assertEqual(
            self.events,
            [
                ("InvalidWorkspaceFilesDialog", [self.workspace / "bad.dep"]),
                ("MessageBox", recovered, gui._("Documents Recovered"), gui.wx.OK | gui.wx.ICON_INFORMATION, frame),
                ("title", "alpha - DotExpress"),
                self._nul_notice("alpha", 1, frame),
                ("title", "alpha - DotExpress"),
                ("title", "alpha - DotExpress"),
                ("focus", "input"),
            ],
        )
        self.assertEqual(frame._document_controller.document_names, ["alpha"])
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])

    def test_startup_load_runs_once(self) -> None:
        # F-13 (D2): a second call (the posted call is made once) changes nothing.
        self._write_packages(Document("alpha", "a", "1"))
        frame = self._make_workspace_frame()
        frame.load_startup_documents()
        self.assertEqual(self.events, [("title", "alpha - DotExpress")] * 3 + [("focus", "input")])
        self.events.clear()
        frame.input_txt.value = "edited"

        frame.load_startup_documents()

        self.assertEqual(self.events, [])
        self.assertEqual(frame.input_txt.value, "edited")
        self.assertEqual(frame._document_controller.document_names, ["alpha"])

    def test_startup_load_after_the_window_closed_does_nothing(self) -> None:
        # F-13 (D2): a close or a logoff before the posted load ran loads nothing and shows no box.
        self._write_packages(Document("alpha", "a", "1"))
        for closed, events, names in (
            (False, [("title", "alpha - DotExpress")] * 3 + [("focus", "input")], ["alpha"]),
            (True, [], []),
        ):
            with self.subTest(closed=closed):
                self.events.clear()
                frame = self._make_workspace_frame()
                frame._close_finished = closed

                frame.load_startup_documents()

                self.assertEqual(self.events, events)
                self.assertEqual(frame._document_controller.document_names, names)
                self.assertEqual(self._listing(), ["alpha.dep"])

    # --- save --------------------------------------------------------------

```

```bash
$PY -B -X utf8 -m unittest tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (the wx stub's no-op answers `load_startup_documents` on the old frame, so the new frame tests see no event):

```text
ERROR: test_building_the_frame_does_not_load_the_workspace (tests.test_gui_document_flows.DocumentControllerOwnershipTest.test_building_the_frame_does_not_load_
AttributeError: 'function' object has no attribute 'SetFocus'
ERROR: test_frame_creates_its_controller_before_building_the_menu_bar (tests.test_gui_document_flows.DocumentControllerOwnershipTest.test_frame_creates_its_cont
AttributeError: <class 'gui.BrailleFrame'> does not have the attribute '_show_empty_startup_state'
FAIL: test_app_startup_runs_steps_in_contract_order (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_app_startup_runs_steps_in_contract_order)
AssertionError: Lists differ: ['prepare', 'cleanup', 'runtime', 'frame', 'show', 'client_init'] != ['prepare', 'cleanup', 'runtime', 'frame', 'show', 'post', 'c
FAIL: test_startup_load_after_the_window_closed_does_nothing (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_startup_load_after_t
AssertionError: Lists differ: [] != [('title', 'alpha - DotExpress'), ('title'[72 chars]ut')]
FAIL: test_startup_load_runs_once (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_startup_load_runs_once)
FAIL: test_startup_load_shows_the_boxes_in_order_and_focuses_the_source_editor_last (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.te
AssertionError: Lists differ: [] != [('InvalidWorkspaceFilesDialog', [WindowsP[497 chars]ut')]
Ran 229 tests
FAILED (failures=4, errors=2)
```

- [ ] **Step 2: Green: the empty start state, `load_startup_documents` with its two guards, the post after `Show()`** (`client/gui.py`, tabs).

Edit: `client/gui.py`

```python
	# Class attributes, so that frames built without __init__ (tests) have them too (F-7, M-5).
	_closing = False
	_close_finished = False
	# The first settings save problem of the session was shown (F-12 D6).
	_settings_save_problem_reported = False

```

```python
	# Class attributes, so that frames built without __init__ (tests) have them too (F-7, M-5).
	_closing = False
	_close_finished = False
	# load_startup_documents has run (F-13 D2).
	_startup_documents_loaded = False
	# The first settings save problem of the session was shown (F-12 D6).
	_settings_save_problem_reported = False

```

Edit: `client/gui.py`

```python
		self._initialize_conversion_state()
		self._apply_initial_settings(initial_settings)
		self._bind_events()
		self._load_startup_documents()

	def _initialize_frame(self) -> None:
		self.SetSize((900, 600))
```

```python
		self._initialize_conversion_state()
		self._apply_initial_settings(initial_settings)
		self._bind_events()
		self._show_empty_startup_state()

	def _initialize_frame(self) -> None:
		self.SetSize((900, 600))
```

Edit: `client/gui.py`

```python
		self.Bind(wx.EVT_ACTIVATE, self.on_frame_activate)
		self.Bind(wx.EVT_CLOSE, self._on_close)

	def _load_startup_documents(self) -> None:
		self._clear_document_editors()
		self._load_workspace_documents_at_startup()
		self._update_window_title()
```

```python
		self.Bind(wx.EVT_ACTIVATE, self.on_frame_activate)
		self.Bind(wx.EVT_CLOSE, self._on_close)

	def _show_empty_startup_state(self) -> None:
		"""The window before the workspace is loaded: empty editors, the title DotExpress (F-13 D2)."""
		self._clear_document_editors()
		self._update_window_title()

	def load_startup_documents(self) -> None:
		"""Load the workspace and show its startup boxes (F-13 D2, F-8b review M-8).

		BrailleApp.OnInit posts this after Show, so that the boxes are owned by a visible
		window. It runs once, and not after the window has closed (a close or a logoff
		before the posted call ran).
		"""
		if self._startup_documents_loaded or self._close_finished:
			return
		self._startup_documents_loaded = True
		self._clear_document_editors()
		self._load_workspace_documents_at_startup()
		self._update_window_title()
```

Edit: `client/gui.py`

```python
			config_store=config_store,
		)
		self.frame.Show()
		start_client_init_background(config_store)
		return True

```

```python
			config_store=config_store,
		)
		self.frame.Show()
		# The workspace is loaded once the main window is visible, so that NVDA and Alt+Tab
		# find the startup boxes (F-13 D2, F-8b review M-8).
		wx.CallAfter(self.frame.load_startup_documents)
		start_client_init_background(config_store)
		return True

```

- [ ] **Step 3: Regenerate the catalogs** (`#:` lines of `gui.py` move).

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

Expected (only `#:` lines change):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
a second msgmerge changes nothing
msgfmt exit 0
407 translated messages.
 client/locales/dotexpress.pot                  | 114 ++++++++++++-------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 114 ++++++++++++-------------
 2 files changed, 114 insertions(+), 114 deletions(-)
0
source msgids: 407 sha256 5daf57d13375a21e9a36b7bf1782976a3d6f14ae9f7c290ae89602b6de943e88
```

- [ ] **Step 4: Green: the changed tests, the module, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_gui_document_flows -v 2>&1 | grep -E "^(test_building_the_frame_does_not_load_the_workspace|test_frame_creates_its_controller_before_building_the_menu_bar|test_app_startup_runs_steps_in_contract_order|test_app_builds_runtime_and_passes_it_to_frame|test_startup_load_[a-z_]*) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_app_builds_runtime_and_passes_it_to_frame ok
test_app_startup_runs_steps_in_contract_order ok
test_building_the_frame_does_not_load_the_workspace ok
test_frame_creates_its_controller_before_building_the_menu_bar ok
test_startup_load_after_the_window_closed_does_nothing ok
test_startup_load_runs_once ok
test_startup_load_shows_the_boxes_in_order_and_focuses_the_source_editor_last ok
Ran 229 tests
OK
Ran 1638 tests
OK (skipped=6)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/test_gui_document_flows.py client/gui.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: show the startup boxes after the main window is shown (F-13)" -m "The workspace is loaded once the main window is visible, so that NVDA reads the startup boxes and Alt+Tab finds them (F-8b review M-8)."
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
 client/gui.py                                  |  23 ++++-
 client/locales/dotexpress.pot                  | 114 ++++++++++++-------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 114 ++++++++++++-------------
 client/tests/test_gui_document_flows.py        |  93 +++++++++++++++++++-
 4 files changed, 226 insertions(+), 118 deletions(-)
d1509b937c40acb55efa98aa43594485a921e045
```

### Task 3: Keep liblouis loaded at exit while a conversion is still running (D3)

- [ ] **Step 1: Red: Test Plan C.** `test_conversion_presenter.py`: `worker_alive` before a job, while the thread runs (also after `shutdown`), after the thread ended. `test_gui_document_flows.py`: `OnExit` with a check answering true (the runtime kept, the dual view folder cleaned, 0) and false (closed once); `OnInit` keeps a check that works when every attribute of the frame raises; the frame hands out the presenter's `worker_alive`. The four existing `OnExit` tests (no frame, so no check) stay as they are.

Edit: `client/tests/test_conversion_presenter.py`

```python
        self.assertEqual(len(self.threads), 1)
        self.assertFalse(presenter.is_running())

    def test_synchronous_call_after_with_a_manually_run_thread_completes(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter(call_after=lambda fn, *args: fn(*args))
```

```python
        self.assertEqual(len(self.threads), 1)
        self.assertFalse(presenter.is_running())

    # --- the conversion thread at exit (F-13 D3) ------------------------------

    def test_worker_alive_is_false_before_a_job(self) -> None:
        self.assertFalse(self._presenter().worker_alive())

    def test_worker_alive_while_the_thread_runs_also_after_shutdown(self) -> None:
        # BrailleApp.OnExit does not free liblouis while the thread may be inside it. After the
        # window closed (shutdown), is_running is false, but the thread still runs.
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter()
        presenter.convert()

        self.assertTrue(presenter.worker_alive())
        presenter.shutdown()
        self.assertFalse(presenter.is_running())
        self.assertTrue(presenter.worker_alive())

    def test_worker_alive_is_false_once_the_thread_has_ended(self) -> None:
        # The result may not be delivered yet (its CallAfter is pending), or not at all after
        # a shutdown: the thread has ended either way.
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter()
        presenter.convert()
        presenter.shutdown()

        self.threads[0].run()

        self.assertFalse(presenter.worker_alive())
        self.calls.run_next()
        self.assertFalse(presenter.worker_alive())

    def test_synchronous_call_after_with_a_manually_run_thread_completes(self) -> None:
        self.outputs["source"] = ConversionOutput("⠎", ())
        presenter = self._presenter(call_after=lambda fn, *args: fn(*args))
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertFalse(result)
        build_runtime.assert_not_called()
        self.assertIn(str(paths.dual_view), message_box.call_args.args[0])

    def test_app_exit_logs_cleanup_failure_and_still_closes_runtime(self) -> None:
        runtime = Mock()
```

```python
        self.assertFalse(result)
        build_runtime.assert_not_called()
        self.assertIn(str(paths.dual_view), message_box.call_args.args[0])

    def _exit_with_worker(self, alive: bool) -> tuple:
        """OnExit of an app whose conversion worker check answers ``alive`` (F-13 D3)."""
        runtime = Mock()
        app = gui.BrailleApp()
        app.paths = make_paths(Path("C:/DotExpress"))
        app.translation_runtime = runtime
        app._conversion_worker_alive = Mock(return_value=alive)

        with patch.object(gui, "cleanup_dual_view_html") as cleanup:
            result = app.OnExit()

        cleanup.assert_called_once_with(Path("C:/DotExpress/dual_view"))
        app._conversion_worker_alive.assert_called_once_with()
        return result, runtime

    def test_app_exit_keeps_the_runtime_while_a_conversion_thread_runs(self) -> None:
        # F-13 (D3, F-9 review M-8): lou_free() under a running lou_translateString can end the
        # process with 0xC0000374 at logoff; the process ends right after OnExit anyway.
        result, runtime = self._exit_with_worker(True)

        self.assertEqual(result, 0)
        runtime.close.assert_not_called()

    def test_app_exit_closes_the_runtime_when_no_conversion_thread_runs(self) -> None:
        result, runtime = self._exit_with_worker(False)

        self.assertEqual(result, 0)
        runtime.close.assert_called_once_with()

    def test_app_keeps_a_worker_check_that_does_not_use_the_frame(self) -> None:
        # F-13 (D3): on wx's end-session path OnExit can run after the frame is destroyed, so
        # the check OnInit keeps is the presenter's, not one that goes through the frame.
        runtime = Mock()
        frame = Mock()
        worker_alive = Mock(return_value=True)
        frame.conversion_worker_check.return_value = worker_alive
        paths = make_paths(Path("C:/DotExpress"))
        with (
            patch.object(gui, "build_application_paths", return_value=paths),
            patch.object(gui, "prepare_application_directories", return_value=paths),
            patch.object(gui, "cleanup_dual_view_html"),
            patch.object(gui, "build_default_translation_runtime", return_value=runtime),
            patch.object(gui, "BrailleFrame", return_value=frame),
            patch.object(gui, "start_client_init_background"),
        ):
            app = gui.BrailleApp()
            self.assertTrue(app.OnInit())
        # A destroyed frame: from now on every attribute of it raises.
        frame.mock_add_spec([])

        with patch.object(gui, "cleanup_dual_view_html"):
            self.assertEqual(app.OnExit(), 0)

        worker_alive.assert_called_once_with()
        runtime.close.assert_not_called()

    def test_app_exit_logs_cleanup_failure_and_still_closes_runtime(self) -> None:
        runtime = Mock()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(frame._conversion_presenter.mock_calls, [call.convert(), call.convert()])
        event.Skip.assert_not_called()

    def test_close_asks_presenter_before_saving(self) -> None:
        frame = self._make_frame()
        steps = Mock()
```

```python
        self.assertEqual(frame._conversion_presenter.mock_calls, [call.convert(), call.convert()])
        event.Skip.assert_not_called()

    def test_conversion_worker_check_is_the_presenters_worker_alive(self) -> None:
        # F-13 (D3): BrailleApp keeps it for OnExit; calling it does not touch the frame.
        frame = self._make_frame()
        frame._conversion_presenter = Mock(spec=gui.ConversionPresenter)

        check = frame.conversion_worker_check()

        self.assertEqual(check, frame._conversion_presenter.worker_alive)

    def test_close_asks_presenter_before_saving(self) -> None:
        frame = self._make_frame()
        steps = Mock()
```

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (the false case closes the runtime today, so `test_app_exit_closes_the_runtime_when_no_conversion_thread_runs` fails only on the missing call of the check):

```text
ERROR: test_worker_alive_is_false_before_a_job (tests.test_conversion_presenter.ConversionPresenterTest.test_worker_alive_is_false_before_a_job)
AttributeError: 'ConversionPresenter' object has no attribute 'worker_alive'
ERROR: test_worker_alive_is_false_once_the_thread_has_ended (tests.test_conversion_presenter.ConversionPresenterTest.test_worker_alive_is_false_once_the_thread_
ERROR: test_worker_alive_while_the_thread_runs_also_after_shutdown (tests.test_conversion_presenter.ConversionPresenterTest.test_worker_alive_while_the_thread_r
ERROR: test_conversion_worker_check_is_the_presenters_worker_alive (tests.test_gui_document_flows.FrameConversionDelegationTest.test_conversion_worker_check_is_
AttributeError: Mock object has no attribute 'worker_alive'
FAIL: test_app_exit_closes_the_runtime_when_no_conversion_thread_runs (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_app_exit_closes_the_runtime_wh
AssertionError: Expected 'mock' to be called once. Called 0 times.
FAIL: test_app_exit_keeps_the_runtime_while_a_conversion_thread_runs (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_app_exit_keeps_the_runtime_whil
FAIL: test_app_keeps_a_worker_check_that_does_not_use_the_frame (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_app_keeps_a_worker_check_that_does_n
Ran 281 tests
FAILED (failures=3, errors=4)
```

- [ ] **Step 2: Green: `worker_alive`, `conversion_worker_check`, the kept check and `OnExit`** (`client/ui/conversion_presenter.py`, 4 spaces; `client/gui.py`, tabs).

Edit: `client/ui/conversion_presenter.py`

```python
        """Whether a job is active (its result not yet delivered) or queued (F-9 D5)."""
        return self._active is not None or bool(self._queue)

    def missing_table_message(self) -> str | None:
        return missing_default_table_message(self._get_translation_tables())

```

```python
        """Whether a job is active (its result not yet delivered) or queued (F-9 D5)."""
        return self._active is not None or bool(self._queue)

    def worker_alive(self) -> bool:
        """Whether the conversion thread is still running (F-13 D3).

        Unlike ``is_running``, it stays true after ``shutdown`` while the thread runs: the
        thread may be inside liblouis, which must not be freed under it at exit.
        """
        return self._runner.is_running()

    def missing_table_message(self) -> str | None:
        return missing_default_table_message(self._get_translation_tables())

```

Edit: `client/gui.py`

```python
from dataclasses import replace
from pathlib import Path
import sys
```

```python
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
import sys
```

Edit: `client/gui.py`

```python

	# --- ConversionView (ui/conversion_presenter.py) ------------------------

	def get_source_text(self) -> str:
		return self._editor_text(self.input_txt)

```

```python

	# --- ConversionView (ui/conversion_presenter.py) ------------------------

	def conversion_worker_check(self) -> Callable[[], bool]:
		"""The presenter's ``worker_alive``, which BrailleApp.OnExit calls (F-13 D3).

		OnExit can run after the frame is destroyed (wx's end-session path), so it keeps the
		presenter's method and never calls the frame.
		"""
		return self._conversion_presenter.worker_alive

	def get_source_text(self) -> str:
		return self._editor_text(self.input_txt)

```

Edit: `client/gui.py`

```python


class BrailleApp(wx.App):
	def OnInit(self):
		paths = build_application_paths()
		self.paths = paths
```

```python


class BrailleApp(wx.App):
	# The conversion worker check of the frame (F-13 D3); None until a frame is built.
	_conversion_worker_alive: Callable[[], bool] | None = None

	def OnInit(self):
		paths = build_application_paths()
		self.paths = paths
```

Edit: `client/gui.py`

```python
			paths=paths,
			config_store=config_store,
		)
		self.frame.Show()
		# The workspace is loaded once the main window is visible, so that NVDA and Alt+Tab
		# find the startup boxes (F-13 D2, F-8b review M-8).
```

```python
			paths=paths,
			config_store=config_store,
		)
		self._conversion_worker_alive = self.frame.conversion_worker_check()
		self.frame.Show()
		# The workspace is loaded once the main window is visible, so that NVDA and Alt+Tab
		# find the startup boxes (F-13 D2, F-8b review M-8).
```

Edit: `client/gui.py`

```python
			except OSError:
				logger.exception("Failed to clean up dual-view HTML")
		runtime = getattr(self, "translation_runtime", None)
		if runtime is not None:
			runtime.close()
		return 0


if __name__ == "__main__":
```

```python
			except OSError:
				logger.exception("Failed to clean up dual-view HTML")
		runtime = getattr(self, "translation_runtime", None)
		if runtime is not None and not self._conversion_worker_is_alive():
			runtime.close()
		# Otherwise liblouis and MathCAT stay loaded: a conversion thread may be inside them
		# (a logoff during a conversion, F-9 review M-8), and the process ends right after
		# OnExit, so Windows frees them (F-13 D3).
		return 0

	def _conversion_worker_is_alive(self) -> bool:
		"""Whether the conversion thread still runs; False when no frame was built (F-13 D3)."""
		check = self._conversion_worker_alive
		return check is not None and check()


if __name__ == "__main__":
```

- [ ] **Step 3: Regenerate the catalogs** (`#:` lines of `gui.py` move).

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

Expected (only `#:` lines change):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
a second msgmerge changes nothing
msgfmt exit 0
407 translated messages.
 client/locales/dotexpress.pot                  | 124 ++++++++++++-------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 124 ++++++++++++-------------
 2 files changed, 124 insertions(+), 124 deletions(-)
0
source msgids: 407 sha256 5daf57d13375a21e9a36b7bf1782976a3d6f14ae9f7c290ae89602b6de943e88
```

- [ ] **Step 4: Green: the new tests, the modules, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows -v 2>&1 | grep -E "^(test_worker_alive_[a-z_]*|test_app_exit_[a-z_]*|test_app_keeps_a_worker_check_that_does_not_use_the_frame|test_conversion_worker_check_is_the_presenters_worker_alive) " | sed 's/ (.*) \.\.\. / /' | sort
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_app_exit_cleans_the_validated_dual_view_folder ok
test_app_exit_closes_runtime ok
test_app_exit_closes_the_runtime_when_no_conversion_thread_runs ok
test_app_exit_keeps_the_runtime_while_a_conversion_thread_runs ok
test_app_exit_logs_cleanup_failure_and_still_closes_runtime ok
test_app_exit_without_initialized_runtime_is_safe ok
test_app_keeps_a_worker_check_that_does_not_use_the_frame ok
test_conversion_worker_check_is_the_presenters_worker_alive ok
test_worker_alive_is_false_before_a_job ok
test_worker_alive_is_false_once_the_thread_has_ended ok
test_worker_alive_while_the_thread_runs_also_after_shutdown ok
Ran 281 tests
OK
Ran 1645 tests
OK (skipped=6)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/test_conversion_presenter.py client/tests/test_gui_document_flows.py client/ui/conversion_presenter.py client/gui.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: keep liblouis loaded at exit while a conversion is still running (F-13)" -m "OnExit skips runtime.close() while the conversion thread is alive, as on a logoff during a conversion; lou_free() under a running translation could end the process with 0xC0000374 (F-9 review M-8)."
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
 client/gui.py                                  |  23 ++++-
 client/locales/dotexpress.pot                  | 124 ++++++++++++-------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 124 ++++++++++++-------------
 client/tests/test_conversion_presenter.py      |  31 +++++++
 client/tests/test_gui_document_flows.py        |  65 +++++++++++++
 client/ui/conversion_presenter.py              |   8 ++
 6 files changed, 250 insertions(+), 125 deletions(-)
8ffb2e1c26339f643d06f8bde1aa2bf6de2ea7b6
```

### Task 4: List the Bopomofo value of a hidden row as it is in the file (D6)

- [ ] **Step 1: Red: Test Plan D.** `test_dictionary_entries_dialog.py` (4 spaces, ASCII with escapes): `test_a_row_line_shows_the_stripped_source_text_and_sequence` flips and is renamed `..._and_the_raw_sequence`; new: four values with whitespace around `ㄇㄚ` (two spaces after, one before, a tab after, U+3000 after), each listed unchanged. `test_a_row_without_its_tone_space_is_hidden_and_listed_on_ok`, the trace replay and every F-11 confirm-box test stay as they are.

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python

        self.assertEqual(harness.take_log(), [_hidden_rows_box("dictionary", _no_source_text(4), _no_source_text(5))])

    def test_a_row_line_shows_the_stripped_source_text_and_sequence(self) -> None:
        # D1: spaces around the fields are not shown (review M-2 a; the S6 probe's row).
        data = (HEADER + " \u809a\u5b50 , \u3109\u3128\u02cb|\u3117\u02d9 ,Bopomofo\r\n").encode("utf-8")
        harness = self.open_editor(data=data)
        harness.take_log()
```

```python

        self.assertEqual(harness.take_log(), [_hidden_rows_box("dictionary", _no_source_text(4), _no_source_text(5))])

    def test_a_row_line_shows_the_stripped_source_text_and_the_raw_sequence(self) -> None:
        # D1: spaces around the source text are not shown (review M-2 a; the S6 probe's row).
        # F-13 (D6, U5): the Bopomofo value is shown as it is in the file, with its spaces.
        data = (HEADER + " \u809a\u5b50 , \u3109\u3128\u02cb|\u3117\u02d9 ,Bopomofo\r\n").encode("utf-8")
        harness = self.open_editor(data=data)
        harness.take_log()
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python

        self.assertEqual(
            harness.take_log(),
            [_hidden_rows_box("dictionary", _invalid_bopomofo(2, "\u809a\u5b50", "\u3109\u3128\u02cb|\u3117\u02d9"))],
        )

    def test_at_most_ten_hidden_rows_are_listed(self) -> None:
        for count, listed, other in ((10, 10, None), (11, 10, "\u53e6\u6709 1 \u5217\u672a\u5217\u51fa"), (13, 10, "\u53e6\u6709 3 \u5217\u672a\u5217\u51fa")):
```

```python

        self.assertEqual(
            harness.take_log(),
            [_hidden_rows_box("dictionary", _invalid_bopomofo(2, "\u809a\u5b50", " \u3109\u3128\u02cb|\u3117\u02d9 "))],
        )

    def test_a_row_line_shows_whitespace_around_the_bopomofo_value(self) -> None:
        # F-13 (D6, U5): whitespace that hides a row is listed as read (O5: tabs and ideographic
        # spaces too). Only the leading whitespace is ignored when the row is checked (F-11 D14).
        for value in ("\u3107\u311a  ", " \u3107\u311a", "\u3107\u311a\t", "\u3107\u311a\u3000"):
            with self.subTest(value=value):
                data = (HEADER + "\u62b9," + value + ",Bopomofo\r\n").encode("utf-8")
                harness = self.open_editor(data=data)
                harness.take_log()
                harness.script_confirm(False)

                harness.press_ok()

                self.assertEqual(harness.take_log(), [_hidden_rows_box("dictionary", _invalid_bopomofo(2, "\u62b9", value))])

    def test_at_most_ten_hidden_rows_are_listed(self) -> None:
        for count, listed, other in ((10, 10, None), (11, 10, "\u53e6\u6709 1 \u5217\u672a\u5217\u51fa"), (13, 10, "\u53e6\u6709 3 \u5217\u672a\u5217\u51fa")):
```

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
```

Expected (each value is listed as `「ㄇㄚ」` today; the four subtests and the flipped test fail):

```text
FAIL: test_a_row_line_shows_the_stripped_source_text_and_the_raw_sequence (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.test_a_row
AssertionError: Lists differ: [['Co[64 chars]」的注音「ㄉㄨˋ|ㄗ˙」格式不正確\n\n要移除這些列並儲存字典嗎？', '移除無法顯示的列[23 chars]B)']] != [['Co[64 chars]」的注音「 ㄉㄨˋ|ㄗ˙ 」格式不正確\n\n要移除這些列並儲存字典嗎
FAIL: test_a_row_line_shows_whitespace_around_the_bopomofo_value (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.test_a_row_line_sho
AssertionError: Lists differ: [['Co[65 chars]注音「ㄇㄚ」格式不正確\n\n要移除這些列並儲存字典嗎？', '移除無法顯示的列', '移除[17 chars]B)']] != [['Co[65 chars]注音「ㄇㄚ  」格式不正確\n\n要移除這些列並儲存字典嗎？', '移
AssertionError: Lists differ: [['Co[63 chars]」的注音「ㄇㄚ」格式不正確\n\n要移除這些列並儲存字典嗎？', '移除無法顯示的列', '[19 chars]B)']] != [['Co[63 chars]」的注音「 ㄇㄚ」格式不正確\n\n要移除這些列並儲存字典嗎？', '
AssertionError: Lists differ: [['Co[65 chars]注音「ㄇㄚ」格式不正確\n\n要移除這些列並儲存字典嗎？', '移除無法顯示的列', '移除[17 chars]B)']] != [['Co[65 chars]注音「ㄇㄚ\t」格式不正確\n\n要移除這些列並儲存字典嗎？', '移
AssertionError: Lists differ: [['Co[65 chars]注音「ㄇㄚ」格式不正確\n\n要移除這些列並儲存字典嗎？', '移除無法顯示的列', '移除[17 chars]B)']] != [['Co[65 chars]注音「ㄇㄚ\u3000」格式不正確\n\n要移除這些列並儲存字典嗎？'
Ran 99 tests
FAILED (failures=5)
```

- [ ] **Step 2: Green: the raw value** (`client/dialog.py`, tabs).

Edit: `client/dialog.py`

```python
	def _hidden_row_line(row: PreservedDictionaryRow) -> str:
		if row.reason == "no_source_text":
			return _("Row {line}: no source text").format(line=row.line)
		return _('Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid').format(
			line=row.line,
			text=row.text.strip(),
			bopomofo=row.braille.strip(),
		)

	def _restore_focus(self, window: wx.Window | None) -> None:
```

```python
	def _hidden_row_line(row: PreservedDictionaryRow) -> str:
		if row.reason == "no_source_text":
			return _("Row {line}: no source text").format(line=row.line)
		# The Bopomofo value as it is in the file: whitespace around it can be why the row
		# is hidden (F-13 D6). The source text is shown without its spaces (F-11 D1).
		return _('Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid').format(
			line=row.line,
			text=row.text.strip(),
			bopomofo=row.braille,
		)

	def _restore_focus(self, window: wx.Window | None) -> None:
```

- [ ] **Step 3: Regenerate the catalogs** (`#:` lines of `dialog.py` move).

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

Expected (only `#:` lines change):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
a second msgmerge changes nothing
msgfmt exit 0
407 translated messages.
 client/locales/dotexpress.pot                  | 28 +++++++++++++-------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 28 +++++++++++++-------------
 2 files changed, 28 insertions(+), 28 deletions(-)
0
source msgids: 407 sha256 5daf57d13375a21e9a36b7bf1782976a3d6f14ae9f7c290ae89602b6de943e88
```

- [ ] **Step 4: Green: the changed tests, the module, the full suite.**

```bash
$PY -B -X utf8 -m unittest tests.test_dictionary_entries_dialog -v 2>&1 | grep -E "^(test_a_row_line_[a-z_]*|test_a_row_without_its_tone_space_is_hidden_and_listed_on_ok) " | sed 's/ (.*) \.\.\. / /'
$PY -B -X utf8 -m unittest tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_a_row_without_its_tone_space_is_hidden_and_listed_on_ok ok
test_a_row_line_shows_the_stripped_source_text_and_the_raw_sequence ok
test_a_row_line_shows_whitespace_around_the_bopomofo_value ok
Ran 99 tests
OK
Ran 1646 tests
OK (skipped=6)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_entries_dialog.py client/dialog.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po
git -C $REPO diff --cached --stat
git -C $REPO commit -q -m "fix: list the Bopomofo value of a hidden row as it is in the file (F-13)"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
 client/dialog.py                               |  4 +++-
 client/locales/dotexpress.pot                  | 28 +++++++++++++-------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 28 +++++++++++++-------------
 client/tests/test_dictionary_entries_dialog.py | 21 ++++++++++++++++---
 4 files changed, 49 insertions(+), 32 deletions(-)
6c352f0225a9167e33e2977b7ad34c7c2427f480
```

### Task 5: Verification (no commit)

`BASE` is `main` at `a147fed`.

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -B -X utf8 -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = 1632 + 14; no failure and no error):

```text
Ran 1646 tests
OK (skipped=6)
```

- [ ] **Step 2: Criterion 2, focused modules; two orders of three modules.**

```bash
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows tests.test_dictionary_entries_dialog tests.test_message_box tests.test_wx_call_sites tests.test_i18n 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_dictionary_entries_dialog tests.test_gui_document_flows tests.test_conversion_presenter 2>&1 | $PY $T/tools/brief.py
$PY -B -X utf8 -m unittest tests.test_conversion_presenter tests.test_gui_document_flows tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
```

Expected (the first `Ran` is Task 0's plus 14):

```text
Ran 432 tests
OK
Ran 380 tests
OK
Ran 380 tests
OK
```

- [ ] **Step 3: The shuffled module order, three seeds** (one process each, about two minutes).

```bash
for s in 0 1 2; do $PY -B $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
      3 ran=1646 failures=0 errors=0 skipped=6 []
```

- [ ] **Step 4: Criterion 3, catalogs.** A fresh template differs from the committed one only in `POT-Creation-Date`; 407 msgids, all translated, 0 fuzzy; the `.mo` equals `a147fed`'s; against `a147fed` the template changes only in `#:` lines and the `.po` in `#:` lines and the one re-wrapped msgstr.

```bash
(cd $REPO && cmd //c "scripts\\generate-pot.bat $(cygpath -w $T/second.pot)"); echo "generate-pot exit $?"
diff --strip-trailing-cr <(grep -v '^"POT-Creation-Date: ' locales/dotexpress.pot) <(grep -v '^"POT-Creation-Date: ' $T/second.pot) && echo "fresh template identical apart from POT-Creation-Date"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
grep -c '^#, fuzzy' locales/zh_TW/LC_MESSAGES/dotexpress.po
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO diff --quiet a147fed -- client/locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo ".mo byte-identical to a147fed"
sha256sum < locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO diff a147fed -- client/locales/dotexpress.pot | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -cvE '^[-+]#: '
git -C $REPO diff a147fed -- client/locales/zh_TW/LC_MESSAGES/dotexpress.po | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[-+]#: '
```

Expected:

```text
generate-pot exit 0
fresh template identical apart from POT-Creation-Date
407 translated messages.
0
source msgids: 407 sha256 5daf57d13375a21e9a36b7bf1782976a3d6f14ae9f7c290ae89602b6de943e88
.mo byte-identical to a147fed
dcf50a626cc5e80dbe0dbacbd07575f4fa8b9ea830b243c2ebaa608ff0f29e32 *-
0
-msgstr "無法寫入檔案。檔案可能正被其他程式使用，或你沒有寫入權限。請關閉其他程式後再試一次。"
+msgstr ""
+"無法寫入檔案。檔案可能正被其他程式使用，或你沒有寫入權限。請關閉其他程式後再"
+"試一次。"
```

- [ ] **Step 5: Criteria 4-6: fixtures, untouched modules, touched files, application data.**

```bash
BASE=a147fed
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/translation_liblouis_golden.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/ui/message_box.py client/conversion client/dictionaries client/braille client/tests/fixtures client/documents client/tests/test_message_box.py client/tests/test_wx_call_sites.py && echo "message_box, conversion, dictionaries, braille, documents, their tests and the fixtures unchanged"
git -C $REPO diff --stat=200 $BASE -- client scripts vendor
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) | diff - $T/app-data.sha256 && echo "application data unchanged"
for f in log workspace config.json; do test -e $REPO/client/$f && echo "the worktree has client/$f"; done; echo "worktree application data checked"
git -C $REPO status --short -- client scripts
```

Expected (the application data are the user's files in the main checkout, read only; if the user ran DotExpress from source meanwhile, its `log/` lines differ, which is not a failure of this plan; `status` prints nothing):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
8dc8572e32f99f2c5588185b33741ed3bb5cb0061dfbf1b7a5700a3c3702a80e *-
message_box, conversion, dictionaries, braille, documents, their tests and the fixtures unchanged
 client/dialog.py                               |   4 +++-
 client/gui.py                                  |  46 +++++++++++++++++++++++++++++++++++++++---
 client/locales/dotexpress.pot                  | 152 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----------------------------------------------------------------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po | 156 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----------------------------------------------------------------------
 client/tests/test_conversion_presenter.py      |  68 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 client/tests/test_dictionary_entries_dialog.py |  21 +++++++++++++++++---
 client/tests/test_gui_document_flows.py        | 158 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 client/ui/conversion_presenter.py              |  28 ++++++++++++++++++++++----
 8 files changed, 466 insertions(+), 167 deletions(-)
application data unchanged
worktree application data checked
```

- [ ] **Step 6: Criterion 7, mutation check** (17 mutants, Spec Corrections 7; about one minute). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f13_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
focus-after-every-manual-failure: 7 caught: test_conversion_presenter.test_a_failure_after_switching_away_and_back_is_not_named, test_conversion_presenter.test_a_failure_of_the_open_document_is_not_named, test_conversion_presenter.test_a_failure_without_a_starting_document_is_not_named, test_conversion_presenter.test_manual_failure_names_a_dictionary_that_cannot_be_read, and 3 more
focus-never: 3 caught: test_conversion_presenter.test_a_failure_after_an_import_opened_another_document_names_it_and_focuses, test_conversion_presenter.test_a_failure_after_switching_names_the_document, test_conversion_presenter.test_the_focus_after_a_failure_comes_before_the_queued_job_starts
focus-before-the-box: 3 caught: test_conversion_presenter.test_a_failure_after_an_import_opened_another_document_names_it_and_focuses, test_conversion_presenter.test_a_failure_after_switching_names_the_document, test_conversion_presenter.test_the_focus_after_a_failure_comes_before_the_queued_job_starts
left-condition-inverted: 9 caught: test_conversion_presenter.test_a_failure_after_an_import_opened_another_document_names_it_and_focuses, test_conversion_presenter.test_a_failure_after_switching_away_and_back_is_not_named, test_conversion_presenter.test_a_failure_after_switching_names_the_document, test_conversion_presenter.test_a_failure_of_the_open_document_is_not_named, and 5 more
load-still-in-init: 2 caught: test_gui_document_flows.test_building_the_frame_does_not_load_the_workspace, test_gui_document_flows.test_frame_creates_its_controller_before_building_the_menu_bar
load-posted-before-show: 1 caught: test_gui_document_flows.test_app_startup_runs_steps_in_contract_order
no-close-finished-guard: 1 caught: test_gui_document_flows.test_startup_load_after_the_window_closed_does_nothing
no-run-once-guard: 1 caught: test_gui_document_flows.test_startup_load_runs_once
empty-state-keeps-the-old-title: 1 caught: test_gui_document_flows.test_building_the_frame_does_not_load_the_workspace
close-always: 3 caught: test_gui_document_flows.test_app_exit_closes_the_runtime_when_no_conversion_thread_runs, test_gui_document_flows.test_app_exit_keeps_the_runtime_while_a_conversion_thread_runs, test_gui_document_flows.test_app_keeps_a_worker_check_that_does_not_use_the_frame
close-never: 6 caught: test_gui_document_flows.test_app_exit_cleans_the_validated_dual_view_folder, test_gui_document_flows.test_app_exit_closes_runtime, test_gui_document_flows.test_app_exit_closes_the_runtime_when_no_conversion_thread_runs, test_gui_document_flows.test_app_exit_keeps_the_runtime_while_a_conversion_thread_runs, and 2 more
worker-alive-reads-is-running: 1 caught: test_conversion_presenter.test_worker_alive_while_the_thread_runs_also_after_shutdown
check-reads-the-frame: 1 caught: test_gui_document_flows.test_app_keeps_a_worker_check_that_does_not_use_the_frame
frame-check-is-is-running: 1 caught: test_gui_document_flows.test_conversion_worker_check_is_the_presenters_worker_alive
bopomofo-stripped: 2 caught: test_dictionary_entries_dialog.test_a_row_line_shows_the_stripped_source_text_and_the_raw_sequence, test_dictionary_entries_dialog.test_a_row_line_shows_whitespace_around_the_bopomofo_value
bopomofo-rstripped: 2 caught: test_dictionary_entries_dialog.test_a_row_line_shows_the_stripped_source_text_and_the_raw_sequence, test_dictionary_entries_dialog.test_a_row_line_shows_whitespace_around_the_bopomofo_value
source-text-not-stripped: 1 caught: test_dictionary_entries_dialog.test_a_row_line_shows_the_stripped_source_text_and_the_raw_sequence
exit 0
```

### Task 6: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay. Run everything from the repository root, one item at a time, with nothing else driving the desktop, and only when at least 600 MB of memory is available (Global Constraints). Never touch the existing `D:\dxtest\N*`, `B` builds (only read and copied by the scripts) or existing `D:\dxtest\auto*` folders; every run of this task uses a new folder whose name ends in `-f13` (drafts in `D:\dxtest\autodraft*-f13`). Only processes whose exe lies under that folder are ended; the user may have DotExpress open and is using the desktop: never end any other process. Every script runs through `auto/safe_run.py` (F-12's, adapted): keys only while a window of the app under test is in the foreground, and no name of another program's window or control in a log. No script reads or writes the clipboard; text reaches the app through files and `set_edit_text`.

**Fix and regression items** (HANDOFF 2026-10-14-01 section 3). A **fix** item runs on both builds (`N-f12b`, the build of `main` `a147fed`'s code, then `N-f13`). A **regression** item runs on `N-f13` only, and on `N-f12b` too only when it misses its expectation. Items 121-125, 127 and 129 are fix items; 126, 128 and 130 regression items; 131 is manual (NVDA) and stays unchecked.

- [ ] **Step 1: Build** (PowerShell, in the worktree). The main checkout's venv is put first on `PATH`; `scripts\build-dotexpress.bat` calls `pyinstaller` from `PATH`.

```powershell
Set-Location D:\workspace\DotExpress-f13
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f13-build.log 2>&1"
if (Select-String -Path $env:TEMP\f13-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "ui\\conversion_presenter.py", "dialog.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress-f13\\client\\$m" -Quiet) { "$m bundled from the worktree" } }
if (Select-String -Path client\build\DotExpress\Analysis-00.toc -SimpleMatch "DotExpress-f13\\client\\gui.py" -Quiet) { "gui.py analyzed from the worktree" }
New-Item -ItemType Directory D:\dxtest\N-f13 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f13\DotExpress.exe
(Get-Item D:\dxtest\N-f13\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f13\DotExpress.exe).Hash
git status --short -- client scripts
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code proves nothing; on failure read `%TEMP%\f13-build.log`), the two `bundled from the worktree` lines, `gui.py analyzed from the worktree`, a size near 48.8 MB, and no `git status` output. `New-Item` without `-Force` fails if `D:\dxtest\N-f13` exists: never overwrite a build.

- [ ] **Step 2: Write the GUI scripts** into `docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/auto/` (tabs): a helper `f13gui.py` that reuses, unchanged, `f12gui.py` of F-12 and through it the earlier helpers; `safe_run.py` (F-12's, importing `f13gui`; it also puts `f13gui.start_a`, `start_b` and `launch` in place of `f8agui.start`, `f8bgui.start` and `dx.launch`, so that rerun scripts of earlier items use the new start, and masks the focus that `f11gui.focused` reads, as F-11's did); `run_item.sh` (waits for 600 MB, names folder and log); one script per item. `f13gui.start(d)` is the spec's start helper: it starts the exe, answers the invalid-files dialog (Keep) and each message box (Enter) whether or not a main window exists yet, records for each `main_visible` (`IsWindowVisible` of the main window, `None` if there is none), `owner_is_main` (`GW_OWNER` is the main window) and the main window's title at that moment, and returns once the main window is enabled, no box of the process has been open for 1 s, and the title is not the bare `DotExpress` or the document list is non-empty. `start_b` returns the old `(app, w, shown)` with the entries of `f8bgui.start`, `start_a` the old `(app, w, invalid)` and `launch` the old `(app, w)`, so earlier scripts print comparable lines; each prints one more line, `f13 start: [(window, main_visible, owner_is_main, main_title), ...]`.

- [ ] **Step 3: The items** (Git Bash, from the repository root): fix items on `D:\dxtest\N-f12b\DotExpress.exe` (folders `auto<N>-f12b-f13`) and on the new build (folders `auto<N>-f13`); regression items on the new build only. Read each log against Step 4 before the next run.

- [ ] **Step 4: Expected behaviour.**

| # | Class | Steps | Expected on `N-f13` | Expected on `N-f12b` |
| --- | --- | --- | --- | --- |
| 121 | fix | `preprocessing.py` whose `main` sleeps 5 s, then raises `ValueError("boom")`. (a) Open `alpha`, Ctrl+Enter, at once Ctrl+Tab to `beta`, wait for the box, Enter. (b) As (a) without Ctrl+Tab | (a) box `無法轉換文件「alpha」。` + `文字處理失敗：boom`; after Enter the focus is `beta`'s source editor (`Edit`, `來源文字`, enabled); `beta`'s editors unchanged. (b) box `文字處理失敗：boom`; the focus after Enter is recorded (expected the Braille Result editor) | (a) the focus is in the Braille Result editor; (b) same as `N-f13` |
| 122 | fix | F-8b item 70 workspace (interrupted rename `alpha` -> `gamma`); `f13gui.start` | the 「已復原文件」 box (`alpha`) with `main_visible True`, `owner_is_main True`, main title `DotExpress`; after Enter `docs ['alpha']`, title `alpha - DotExpress`, focus in the source editor; files as F-8b 70 | the box with no visible main window |
| 123 | fix | F-8b item 73 workspace (`alpha.dep` with U+0000) | the 「已取代字元」 box (`alpha`, 2) with `main_visible True`, `owner_is_main True`, main title `alpha - DotExpress`; afterwards as F-8b 73 | the box before the main window |
| 124 | fix | F-8a item 66 workspace (`alpha.dep` valid, `bad.dep` invalid); Keep | the invalid-files dialog (`['bad.dep']`) with `main_visible True`, `owner_is_main True`; afterwards `docs ['alpha']`, focus in the source editor | the dialog before the main window |
| 125 | fix | `bad.dep` invalid, an interrupted rename of `alpha` (to `gamma`) whose text holds U+0000, and a valid `beta.dep`; Keep | invalid-files dialog, 「已復原文件」 (`alpha`), 「已取代字元」 (`alpha`), each with `main_visible True`, `owner_is_main True`; then `docs ['alpha', 'beta']`, title `alpha - DotExpress`, focus in the source editor | the same order and final state, all before the main window |
| 126 | regression | Reruns with `f13gui.start`: F-8b 70, 70b, 71, 72, 73; F-8a 66, 69, 79; F-12 113; a plain start (one valid `alpha`); a first start in an empty folder | every line as in the item's recorded result, except where a box appears relative to the main window; plain start: no box, `docs ['alpha']`, title `alpha - DotExpress`, focus in the source editor; empty folder: `docs ['new']` | (only if a result misses) |
| 127 | fix | F-9 item 93's workspace (`alpha` long pending text, `beta`). 20 runs, each a fresh start: write `dual_view\dual-view-f13probe.html`; Ctrl+Enter on `alpha`; after 1 s `WM_QUERYENDSESSION` (`ENDSESSION_LOGOFF`); then `WM_ENDSESSION` (wParam 1); the exit code within 10 s | each query answers 0 within 2 s; exit code 0 in all 20 runs, never `-1073740940` (`0xC0000374`); the probe file gone (`OnExit` ran); `alpha.dep`, `beta.dep` readable; no `gui.log` line | the count of `-1073740940`; if none in 20 runs, the GUI evidence is inconclusive (recorded; the item still passes on `N-f13`'s 20 clean exits and Test Plan C) |
| 128 | regression | F-9 item 93 (full script); F-7 item 59 (`WM_QUERYENDSESSION` with nothing to save: exit code 0); a completed conversion, then Close | as in their recorded results; the Close gives exit code 0 | (only if a result misses) |
| 129 | fix | Dictionary `raw.csv`: `text,braille,type` / `抹,ㄇㄚ␠␠,Bopomofo` / `媽,␠ㄇㄚ,Bopomofo` / `甲乙,⠁⠃,Braille`. Edit it, OK; read the box through UIA; 返回編輯; OK, 移除並儲存 | lines `第 2 列：「抹」的注音「ㄇㄚ  」格式不正確` and `第 3 列：「媽」的注音「 ㄇㄚ」格式不正確`; then the file holds only `甲乙` | `「ㄇㄚ」` in both lines |
| 130 | regression | F-11 items 95 and 99 (both confirmation boxes; Esc, Enter, Alt+F4, the close button) | as in their recorded results (D5: the boxes are unchanged) | (only if a result misses) |

Never trigger a real logoff or shutdown: items 127 and 128 send the session messages to DotExpress's main window only. If a key or a click goes to another window (a `RuntimeError` from `safe_run`, or a box that never opens), that is a tool problem: run the item again in a new folder and record it.

- [ ] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/auto-results.md` in the style of F-12's (zh-TW): the build, the method, then one row per item (121-130) with ✔/△/✘, the new result and, for fix items, the old one. Any deviation from Step 4 is reported, not explained away. End with a section **「仍需人工（使用者）」** for item 131 (unchecked). Add **Implementation Notes** at the end of this plan, then:

```bash
cd $REPO
git add docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/auto docs/superpowers/history/2026-10-14-02-f13-behavior-nvda/auto-results.md docs/superpowers/plans/2026-10-14-f13-behavior-nvda.md
git diff --cached --stat
git commit -q -m "docs: record the F-13 packaged-build GUI checks (F-13)"
git status --short -- client docs scripts
git rev-parse HEAD:client
```

Expected: the history files and the plan in the `--stat`, no `status` output, and Task 4's tree id. Do not merge `main` or push; the orchestrator decides.
