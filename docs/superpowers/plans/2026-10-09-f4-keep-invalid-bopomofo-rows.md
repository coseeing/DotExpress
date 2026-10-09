# Keep Invalid Bopomofo Rows (F-4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix F-W11 (data loss). The dictionary entries editor keeps showing exactly the rows it shows today; every other data row of the file (a blank source text, or a `Bopomofo` row whose sequence does not parse) is kept, hidden, at its place, and OK writes every row back in file order. A hidden row is written with its three fields exactly as read, so `dict_badbopo.csv` survives an unchanged OK byte for byte. Adding or editing an entry to a hidden row's source text is refused with the existing duplicate message. Dictionary Management's count, Import, Export, Rename, Delete and conversion are unchanged. No new user-visible string (msgids 353, same set), no `.po`/`.mo`, fixture or `client/conversion/` change.

**Architecture:** Three commits on the client, each red first except the first. Task 1 pins the Dictionary Management count (D6) on today's code. Task 2 adds `PreservedDictionaryRow`, `load_dictionary_rows` and a row-aware `save_dictionary_entries` in `dictionaries/entries.py` (D2, D3); the editor still drops the rows. Task 3 makes `DictionaryEntryListModel` own every file row in one ordered list, with the entries and the visible list derived from it (D4, D5), flips the `KNOWN BUG (P2-2 spec, Q2)` test, adds the editor tests and amends the golden-trace oracle line by line without touching the fixture. Task 4 verifies (suite, shuffled order, strings, fixtures, conversion, mutants), Task 5 builds the exe and runs the GUI checks, Task 6 merges `main` when asked.

**Tech Stack:** Python 3.13 standard library (`csv`, `dataclasses`, `unittest`, `unittest.mock`). Windows 11, the main checkout's `client\.venv` (wxPython, PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil 7.2.2 in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-09-f4-keep-invalid-bopomofo-rows-design.md` (+ `_zh-TW.md`), commit `806a034`, with Q1-Q3 decided and the section "Corrected after planning" added in the plan commit (both languages). Orchestrator decisions (recommended defaults; the user may override them before the merge): **Q1 refuse** (an entry whose source text equals a hidden row's is refused with the existing duplicate message); **Q2 no notice in F-4** (follow-up UX task; the hidden rows stay invisible, a known defect); **Q3 conversion unchanged** (follow-up with P1-6 defect 2).

## Global Constraints

- Work only in the worktree `D:\workspace\DotExpress-f4`, branch `fix/f4-keep-invalid-bopomofo-rows` (HEAD is the plan commit on top of `806a034`, which is on top of `main` at `4953772`). Never switch branches, never push, never rewrite history. `D:\workspace\DotExpress` and `D:\workspace\DotExpress-f3` (another task) are read-only: reading them and using the main checkout's `client\.venv` Python are fine. Merge `main` only in Task 6 and only when the orchestrator asks.
- Files that may change (8, nothing else): production `client/dictionaries/entries.py`, `client/dictionaries/entry_list_model.py` (**tabs**); tests `client/tests/test_dictionary_entries.py`, `client/tests/test_dictionary_entry_list_model.py`, `client/tests/test_dictionary_management_dialog.py` (**tabs**), `client/tests/test_dictionary_entries_dialog.py` (4 spaces); in Task 5 the new history folder `docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/` (scripts with tabs, results).
- Never touch `client/dictionary/` (user data; the worktree has none and no test creates it), `client/braille/tables/__tables.py`, tracked `client/braille/` content, `client/locales/`, `client/tests/fixtures/`, `client/conversion/`, `client/dialog.py`, `client/gui.py`, `client/shared/atomic_write.py`, `scripts/`, `vendor/`, the `include/liblouis` submodule pointer, the untracked `client2/`, `preprocessing/`, `testdata/` of the main checkout, or the committed scripts and data of `docs/superpowers/history/2026-10-09-03-windows-verification/`. Never run `py scripts\sync-nvda.py`. Task 0 copies git-ignored build products into the worktree; that is the only change outside the list above, the copies are never staged, and `git status` stays empty.
- The checkout uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply `File:` blocks with the Write tool (LF is fine; git normalizes it, the "LF will be replaced by CRLF" warning is expected) and `Edit:` blocks with the Edit tool: the first block is the exact old text, the second its replacement, each old text occurs once. Never edit with MSYS `sed -i` and never paste Python through a shell heredoc (the agent shell can alter backslashes). The blocks for the tab-indented files contain real tab characters; copy them, do not retype. New test code keeps the files ASCII: non-ASCII test data is written with `\u` escapes, as the existing tests do.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`, unchanged (never regenerate the trace). msgid scan `source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c` before and after.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly.
- The only failing test before and after F-4 is the F-W6 error `test_dictionary_name_prompt ... test_case_only_rename_still_renames` (out of scope).
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`). Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks.
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress-f4
  MAIN=/d/workspace/DotExpress
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f4impl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. Task 5 uses PowerShell.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning" in the plan commit. The dry run found no error in decisions D1-D9, in the Current State or in the counts of commits 1-3.

1. **Q1-Q3 decided** by the orchestrator with the recommended defaults (the user may override them before the merge). **Q1: refuse** (D5). **Q2: no notice in F-4**; that the hidden rows are invisible and uncounted is a known defect, left to a follow-up UX task (new msgids). **Q3: conversion unchanged** (D7); ignoring invalid rows in conversion is a follow-up together with P1-6 defect 2.
2. **Model tests use four rows.** `PreservedRowsTest` is built from `alpha, kept, beta, blank` (`blank` = `PreservedDictionaryRow("", "\u2803", "General")`, a trailing preserved row). M2 removes the second entry (`beta`) and adds `gamma`: rows `(alpha, kept, blank, gamma)`; M3 replaces `beta`: `(alpha, kept, delta, blank)`; M4 uses the same model; M1 also filters by `|`. With the spec's three rows and index 0, the mutants "new entry inserted before a trailing preserved row" and "remove/replace by visible index" survive.
3. **Test details.** E1-E3 are a new class `DictionaryEntriesDialogHiddenRowsTest`; E1 also checks that no temporary file is left, E3 that the shown rows are unchanged. S3 also asserts that the embedded bytes have the sha256 of `dict_badbopo.csv`; S6 compares in both directions. The test data constants (`DICT_BADBOPO`, `MIXED_CSV`) are repeated in the modules that need them (no shared helper module, so acceptance criterion 5's file list holds); all new test code is ASCII with `\u` escapes, as the existing tests.
4. **Mutation check: 19 mutants** (Task 4 Step 6, each caught). The spec's "`remove` by equality over rows matching a preserved row" is the mutant `preserved-row-equal-to-entry` (a field-wise `__eq__` on `PreservedDictionaryRow`), caught by S6 only: through the editor an entry and a preserved row never have equal fields (the classification is a function of the fields), so S6 is the guard. "Subclass of `DictionaryEntry`" is `preserved-row-subclass-of-entry`. The tool runs Python with `-B`: in the dry run a restored file had the size and modification second of the mutant before it, and the cached bytecode of the mutant was used.
5. **Counts after the merge with `main`.** F-3 was merged into `main` as `b793704` while this plan was written; `main` alone gives `Ran 1253`, `FAILED (errors=1, skipped=7)` (F-3's review added tests after its plan's 1248). After merging it into F-4: `Ran 1268`, `FAILED (errors=1, skipped=7)`, F-W6 only. This replaces the spec's "1263 (1211 + F-3's 37 + F-4's 15)". F-3's changes to `client/gui.py` (`_show_document_save_error`, logging) and `client/tests/test_gui_document_flows.py` do not overlap F-4's files; the merge is clean.
6. **Windows verification.** History folder `docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/`, new item 35 (not renumbered). `rerun.py` takes only the script (the build and the folders are fixed per script) and has a `--check` mode; item 23's folders are `D:\dxtest\auto23-f4-B` and `D:\dxtest\auto23-f4-N-f4` (the script puts the build label into the folder name), items 24, 25 and 29 use `D:\dxtest\auto24-f4`. Item 35's Add of `肚子` is automated through the real entry dialog (not manual). The dict23 output of item 23 is `sha ef319c2140b1465e` (the 2026-10-09-03 result `ef319c21…`). The scripts run from Git Bash with the separate pywinauto venv.

## Dry Run

The plan was executed on scratch clones of the branch at `806a034` with a stand-in plan commit (`$SP/f4plan/r*`, never the worktree), by a harness that writes every `File:` block, applies every `Edit:` block exactly once, runs every `bash` block from `client/` and compares its stdout with the following `text` block. Two final replays from fresh clones matched every expected block, including all red runs, the per-commit tree ids, the six shuffle seeds and the mutation output: Tasks 0-4 and Task 6 case A with a local `main` at `4953772` (`r3`), and Tasks 0-4 and Task 6 case B with `main` at `b793704`, F-3 merged (`r4`). Final sha256 after Task 3 (`git show HEAD:<path>`): `client/dictionaries/entries.py` `662cc618e5cc09b7a112937e3026465a290d490a356950c056f7415799492cc7`, `client/dictionaries/entry_list_model.py` `998ae4c6b3a3548245392eb8dac35000ce1798f3b8a0db628c67a50549b9efc0`. Task 5: the build command was run on a clone at Task 3 ("Build complete!" in 47 s, 48,737,338 bytes; `PYZ-00.toc` listed the clone's own `dictionaries\entries.py` and `dictionaries\entry_list_model.py` and no dictionary module of the main checkout); the two scripts were written from their `File:` blocks, syntax-checked, and `rerun.py --check` was run on the four 2026-10-09-03 scripts (Step 2's expected block). The GUI was not driven.

## Review Focus

1. **No row is lost on OK.** S2, S3, M5, E1, E2 and the flipped Q2 test compare the saved bytes; the trace replay checks that the two hidden `TRACE_CSV` rows come back exactly once each, in order, in all 40 sequences.
2. **A hidden row never becomes editable.** It is a different class (S6: never equal to an entry), never in `entries`/`visible_entries`, never matched by the filter (M1), never removed or replaced (M2, M3, E2); new entries go after it (M2).
3. **What changes for the user** (accepted in the spec): an entry whose source text equals a hidden row's is refused with the existing message (M4, E3; Q1); the hidden rows stay invisible and uncounted (P1; Q2); conversion output no longer changes when OK is pressed on an unchanged dictionary (S5; Q3).
4. **The golden trace is not regenerated.** The oracle change is limited to the two named lines of the last step, compared line by line; the fixture sha256 is checked before and after.

## File Map

- Task 1: `client/tests/test_dictionary_management_dialog.py` (P1, `DICT_BADBOPO`).
- Task 2: `client/tests/test_dictionary_entries.py` (S1-S6, constants); `client/dictionaries/entries.py` (`PreservedDictionaryRow`, `DictionaryRow`, `load_dictionary_rows`, `_is_editable`, `load_dictionary_entries`, `save_dictionary_entries`).
- Task 3: `client/tests/test_dictionary_entry_list_model.py` (`PreservedRowsTest` M1-M4, M5 in `LoadSaveTest`); `client/tests/test_dictionary_entries_dialog.py` (the Q2 flip, `DictionaryEntriesDialogHiddenRowsTest` E1-E3, `_TRACE_KEPT_ROWS` and the replay oracle); `client/dictionaries/entry_list_model.py`.
- Task 5: new `docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/` (`auto/rerun.py`, `auto/item35.py`, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`, runtime copied in Task 0)

| After task | tests added | `Ran` | final line | `HEAD:client` |
| --- | --- | --- | --- | --- |
| baseline (`806a034` + plan) | - | 1211 | `FAILED (errors=1, skipped=5)` | `c609d3630e5cacf7c6dcf7cebddbdcccb3acc08a` |
| 1 pin | 1 (P1) | 1212 | `FAILED (errors=1, skipped=5)` | `d5217df58d650d3c7685f44060bd7ab8a15c4ec3` |
| 2 storage | 6 (S1-S6) | 1218 | `FAILED (errors=1, skipped=5)` | `c57e1d9affc9445d43fd4b11a28c8aede3a05161` |
| 3 model and editor | 8 (M1-M5, E1-E3); the Q2 test flipped in place; the trace oracle amended | 1226 | `FAILED (errors=1, skipped=5)` | `a64e34d8dec7b1909f7fae5c8b9b4327d3d7f6b2` |
| 5 GUI results (docs only) | - | 1226 | `FAILED (errors=1, skipped=5)` | `a64e34d8dec7b1909f7fae5c8b9b4327d3d7f6b2` |
| 6 case A: `main` still `4953772` | - (nothing to merge) | 1226 | `FAILED (errors=1, skipped=5)` | `a64e34d8dec7b1909f7fae5c8b9b4327d3d7f6b2` |
| 6 case B: `main` at `b793704` (F-3) | `main`'s 42 since `4953772` | 1268 | `FAILED (errors=1, skipped=7)` | `70cc470e9e87aa18a736743ae6ebabc9a52e567d` |

The error is F-W6 throughout. The four dictionary modules go from `Ran 146`, `OK` to `Ran 161`, `OK`; the acceptance-criterion-2 set from `Ran 187` to `Ran 202`, `OK`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 with the Write tool: `brief.py` (output condenser), `msgid_scan.py` and `shuffle_harness.py` (the P2-5/F-3 tools), `f4_mutants.py` (19 mutants of the code after Task 3, run on a copy of `client/`; the repository is never changed).

---

### Task 0: Baseline and runtime copy (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO merge-base main HEAD
git -C $REPO diff $(git -C $REPO merge-base main HEAD) --stat -- client
```

Expected (`status` and the diff print nothing; the merge base is `main` at `4953772`):

```text
docs: plan for keeping invalid Bopomofo rows (F-4)
fix/f4-keep-invalid-bopomofo-rows
4953772d4c05310ca631cf5fc7280e3b08df3b0f
```

- [ ] **Step 2: Copy the generated liblouis runtime and MathCAT from the main checkout** (the spec author already did this once in the worktree; the guards make the step safe to repeat and it then copies nothing). These files are git-ignored build products (`git -C $MAIN status --ignored --short client/braille client/mathcat` lists them as `!!`); without them the baseline is 5 tests lower with `errors=2, skipped=7`. Copy only them, read-only from `$MAIN`; the tracked `client/braille/__init__.py`, `client/braille/tables/` and the submodule pointer are not touched. `include/liblouis` is an uninitialized submodule in the worktree; `test_built_wrapper_loads_bundled_dll` reads the expected version from its `configure.ac`, and the main checkout's submodule is at the same commit (`2aa5f84b`).

```bash
test -e $REPO/client/braille/liblouis.dll || cp $MAIN/client/braille/liblouis.dll $REPO/client/braille/
test -e $REPO/client/braille/louis_helper.py || cp $MAIN/client/braille/louis_helper.py $REPO/client/braille/
test -e $REPO/client/braille/liblouis || cp -r $MAIN/client/braille/liblouis $REPO/client/braille/liblouis
test -e $REPO/client/mathcat || cp -r $MAIN/client/mathcat $REPO/client/mathcat
test -e $REPO/include/liblouis/configure.ac || cp $MAIN/include/liblouis/configure.ac $REPO/include/liblouis/configure.ac
git -C $MAIN submodule status include/liblouis | cut -c2-41
git -C $REPO rev-parse HEAD:include/liblouis
cmp $REPO/client/braille/louis_helper.py $REPO/vendor/nvda/liblouis/runtime/louis_helper.py && echo "louis_helper.py is the vendored file"
cmp $REPO/client/braille/liblouis.dll $MAIN/client/braille/liblouis.dll && echo "liblouis.dll is the main checkout's"
git -C $REPO status --short
git -C $REPO status --short --ignored client/braille client/mathcat | grep -v __pycache__
sha256sum < $REPO/docs/superpowers/history/2026-10-09-03-windows-verification/auto/data/dict_badbopo.csv
```

Expected (`status --short` prints nothing: the copies are ignored, the submodule pointer is unchanged; the last line is the sha256 of the test dictionary that Tasks 1-3 embed as bytes):

```text
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
louis_helper.py is the vendored file
liblouis.dll is the main checkout's
!! client/braille/liblouis.dll
!! client/braille/liblouis/
!! client/braille/louis_helper.py
!! client/mathcat/
c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4 *-
```

If any of these files is missing in `$MAIN`, skip the copy and use the worktree baseline instead: every `Ran` count below is then 5 lower, every final line has `errors=2, skipped=7` (the extra error is `test_liblouis_runtime` `setUpClass`), and nothing else changes.

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed) with the Write tool. `msgid_scan.py` and `shuffle_harness.py` are the P2-5/F-3 tools unchanged; `brief.py` is F-3's with the temporary-file suffix pattern widened to `.csv`; `f4_mutants.py` is used in Task 4.

File: `$T/tools/brief.py`

````python
"""Condense unittest output read from stdin (throwaway, not committed).

Keeps the FAIL/ERROR headers, exception lines (cut to 160 characters, each printed
once), the "Ran" line without its timing and the final OK/FAILED line, so that outputs
can be compared with the plan. The client directory is shown as <client>; temporary
directories (tempfile.mkdtemp names, also in repr form with doubled backslashes) as
<tmp>; random temporary-file suffixes as <rnd>.
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
        if line not in seen:
            seen.add(line)
            print(line[:160])
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

File: `$T/tools/f4_mutants.py`

````python
"""Run the F-4 tests against deliberately broken code (throwaway, not committed).

Usage: python f4_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one file of the copy (one exact, unique replacement), runs the four
dictionary test modules there, prints which tests caught it and restores the file. The
repository is never changed. Matches the code after Task 3. Exit status 1 if a mutant is
not caught or its pattern is not found exactly once. Python runs with -B (no bytecode
is written): a restored file can have the size and modification second of the mutant,
and a cached .pyc would then shadow it.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ENTRIES = "dictionaries/entries.py"
MODEL = "dictionaries/entry_list_model.py"
DIALOG_TESTS = "tests/test_dictionary_entries_dialog.py"
TRACE_ORACLE = (
    '                    lines = actual[-1]["csv"].split("\\r\\n")\n'
    '                    self.assertEqual([line for line in lines if line in _TRACE_KEPT_ROWS], list(_TRACE_KEPT_ROWS))\n'
    '                    actual[-1]["csv"] = "\\r\\n".join(line for line in lines if line not in _TRACE_KEPT_ROWS)\n'
)
TRACE_ORACLE_BY_SUBSTRING = (
    "                    for kept in _TRACE_KEPT_ROWS:\n"
    '                        actual[-1]["csv"] = actual[-1]["csv"].replace(kept + "\\r\\n", "", 1)\n'
)
SAVE_ROWS = "\t\tsave_dictionary_entries(path, self._rows)\n"
MUTANTS = {
    # D3: a preserved row keeps its three fields exactly as read.
    "preserved-fields-stripped": (
        ENTRIES,
        '\t\t\t\t\t\ttext=row.get("text") or "",\n\t\t\t\t\t\tbraille=row.get("braille") or "",\n',
        "\t\t\t\t\t\ttext=entry.text,\n\t\t\t\t\t\tbraille=entry.braille,\n",
    ),
    "preserved-type-normalized": (
        ENTRIES,
        '\t\t\t\t\t\tentry_type=row.get("type") or "",\n',
        "\t\t\t\t\t\tentry_type=entry.entry_type,\n",
    ),
    "missing-field-kept-as-none": (
        ENTRIES,
        '\t\t\t\t\t\tentry_type=row.get("type") or "",\n',
        '\t\t\t\t\t\tentry_type=row.get("type"),\n',
    ),
    # D1/D2: the classification is the loader's rule before F-4.
    "blank-text-rows-shown": (ENTRIES, "\tif not entry.text:\n\t\treturn False\n", ""),
    "invalid-bopomofo-rows-shown": (
        ENTRIES,
        "\t\texcept Exception:\n\t\t\treturn False\n",
        "\t\texcept Exception:\n\t\t\treturn True\n",
    ),
    # D6: Dictionary Management counts the shown rows only (P1).
    "load-entries-returns-every-row": (
        ENTRIES,
        "\treturn [row for row in load_dictionary_rows(dictionary_path) if isinstance(row, DictionaryEntry)]\n",
        "\treturn load_dictionary_rows(dictionary_path)\n",
    ),
    # D3/D4 in the writer: every row, in the given order.
    "save-writes-preserved-rows-last": (
        ENTRIES,
        "\t\tfor row in rows:\n",
        "\t\tfor row in sorted(rows, key=lambda row: isinstance(row, PreservedDictionaryRow)):\n",
    ),
    "save-skips-preserved-rows": (
        ENTRIES,
        "\t\tfor row in rows:\n",
        "\t\tfor row in [row for row in rows if isinstance(row, DictionaryEntry)]:\n",
    ),
    # D2: a preserved row is never an entry and never equal to one (the model's
    # list.remove and equality-based selection could otherwise pick it).
    "preserved-row-subclass-of-entry": (
        ENTRIES,
        "@dataclass(frozen=True)\nclass PreservedDictionaryRow:\n",
        "@dataclass\nclass PreservedDictionaryRow(DictionaryEntry):\n",
    ),
    "preserved-row-equal-to-entry": (
        ENTRIES,
        "\tentry_type: str\n\n\nDictionaryRow",
        "\tentry_type: str\n\n\tdef __eq__(self, other):\n"
        "\t\treturn (self.text, self.braille, self.entry_type) == (other.text, other.braille, other.entry_type)\n"
        "\n\nDictionaryRow",
    ),
    # D4: the model hides preserved rows and keeps them in place.
    "model-shows-every-row": (
        MODEL,
        "\t\treturn [row for row in self._rows if isinstance(row, DictionaryEntry)]\n",
        "\t\treturn list(self._rows)\n",
    ),
    "filter-over-every-row": (
        MODEL,
        "\t\t\tself._visible = [entry for entry in self._entries if self.matches(entry, self._filter_text)]\n",
        "\t\t\tself._visible = [entry for entry in self._rows if self.matches(entry, self._filter_text)]\n",
    ),
    "model-saves-entries-only": (MODEL, SAVE_ROWS, "\t\tsave_dictionary_entries(path, self._entries)\n"),
    "model-saves-preserved-rows-last": (
        MODEL,
        SAVE_ROWS,
        "\t\tsave_dictionary_entries(path, self._entries + [row for row in self._rows if not isinstance(row, DictionaryEntry)])\n",
    ),
    "add-before-trailing-preserved-rows": (
        MODEL,
        "\t\tself._rows.append(entry)\n",
        "\t\tself._rows.insert(max((index + 1 for index, row in enumerate(self._rows) if isinstance(row, DictionaryEntry)), default=0), entry)\n",
    ),
    "remove-by-visible-index": (MODEL, "\t\tself._rows.remove(current_entry)\n", "\t\tdel self._rows[visible_index]\n"),
    "replace-by-visible-index": (
        MODEL,
        "\t\tfull_index = next(index for index, candidate in enumerate(self._rows) if candidate is current_entry)\n",
        "\t\tfull_index = visible_index\n",
    ),
    # D5: the duplicate check covers preserved rows.
    "duplicate-check-over-entries-only": (
        MODEL,
        "\t\treturn any(row.text == text and row is not exclude_entry for row in self._rows)\n",
        "\t\treturn any(row.text == text and row is not exclude_entry for row in self._entries)\n",
    ),
    # Test plan G: the trace oracle must compare lines, not substrings.
    "trace-oracle-removes-substrings": (DIALOG_TESTS, TRACE_ORACLE, TRACE_ORACLE_BY_SUBSTRING),
}
MODULES = (
    "tests.test_dictionary_entries",
    "tests.test_dictionary_entry_list_model",
    "tests.test_dictionary_entries_dialog",
    "tests.test_dictionary_management_dialog",
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
        shown = names if len(names) <= 8 else names[:8] + [f"and {len(names) - 8} more"]
        print(f"{mutant}: {len(names)} caught: {', '.join(shown) if names else 'NONE'}")
        if not names:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
````

- [ ] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, tree.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_conversion_text_dictionary_rules tests.test_translation_golden 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO rev-parse HEAD:client
for p in dictionary workspace config.json; do test -e $p && echo "EXISTS client/$p"; done; echo "app data checked"
(cd $MAIN/client/dictionary && sha256sum *) > $T/main-dictionary.sha256; wc -l < $T/main-dictionary.sha256
```

Expected (the second line block is the four dictionary modules, the third the spec's acceptance-criterion-2 set; the last line counts the files of the main checkout's user dictionary folder, recorded read-only for Task 4):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1211 tests
FAILED (errors=1, skipped=5)
Ran 146 tests
OK
Ran 187 tests
OK
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c
c609d3630e5cacf7c6dcf7cebddbdcccb3acc08a
app data checked
1
```

### Task 1: Pin that Dictionary Management counts only the rows the editor shows (D6)

P1 passes on today's code (the count already excludes the rows the editor skips), so this task has no red run; it is committed first so that Tasks 2 and 3 are checked against it. `dict_badbopo.csv` is embedded as bytes (`\u` escapes), not read from the history folder.

- [ ] **Step 1: Add the constant and P1** (`client/tests/test_dictionary_management_dialog.py`, tabs).

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
DictionaryManagementDialog = dialog.DictionaryManagementDialog
```

```python
DictionaryManagementDialog = dialog.DictionaryManagementDialog

# dict_badbopo.csv of the Windows verification (F-W11): one Braille row and two Bopomofo
# rows whose sequences do not parse; UTF-8 without a BOM, CRLF.
DICT_BADBOPO = (
	"text,braille,type\r\n"
	"\u81fa\u5317,\u281e\u283a,Braille\r\n"
	"\u809a\u5b50,\u3109\u3128\u02cb|\u3117\u02d9,Bopomofo\r\n"
	"\u6578\u5b78,\u3115\u3128\u02cb \u3112\u3129\u311d\u02ca,Bopomofo\r\n"
).encode("utf-8")
```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
		self.assertEqual(target._get_item_text(0, 0), "alpha")
		self.assertEqual(target._get_item_text(0, 1), "1")

	def test_missing_dictionary_has_zero_entries(self):
```

```python
		self.assertEqual(target._get_item_text(0, 0), "alpha")
		self.assertEqual(target._get_item_text(0, 1), "1")

	def test_rows_the_editor_does_not_show_are_not_counted(self):
		# F-4 (D6): the count is the number of rows the entries editor shows. It keeps the
		# two Bopomofo rows whose sequences do not parse hidden, so they are not counted.
		with tempfile.TemporaryDirectory() as temp_dir:
			(Path(temp_dir) / "dict_badbopo.csv").write_bytes(DICT_BADBOPO)
			target = _make_dialog(temp_dir, ["dict_badbopo"])

			target.refresh_dictionaries(["dict_badbopo"], "dict_badbopo")

		self.assertEqual(target._get_item_text(0, 0), "dict_badbopo")
		self.assertEqual(target._get_item_text(0, 1), "1")

	def test_missing_dictionary_has_zero_entries(self):
```

- [ ] **Step 2: Run: green on today's code.**

```bash
$PY -m unittest tests.test_dictionary_management_dialog -v 2>&1 | grep "^test_rows_the_editor_does_not_show_are_not_counted" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_dictionary_management_dialog 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_rows_the_editor_does_not_show_are_not_counted ok
Ran 28 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1212 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 3: Commit.**

```bash
git -C $REPO add client/tests/test_dictionary_management_dialog.py
git -C $REPO commit -q -m "test: pin that Dictionary Management counts only the rows the editor shows (F-4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
d5217df58d650d3c7685f44060bd7ab8a15c4ec3
```

### Task 2: Keep the rows the editor does not show when saving (D1-D3)

The storage layer learns to return and write every row. The model still loads `load_dictionary_entries`, so the editor still drops the rows and the `KNOWN BUG (P2-2 spec, Q2)` test still passes after this task.

- [ ] **Step 1: Red: S1-S6** (`client/tests/test_dictionary_entries.py`, `DictionaryEntryStorageTest`, tabs). The module-level constants are shared by the six tests; `MIXED_CSV` holds every kind of row the editor does not show between two entries.

Edit: `client/tests/test_dictionary_entries.py`

```python
import csv
import tempfile
import unittest
from pathlib import Path

from dictionaries.entries import (
	DictionaryEntry,
	load_dictionary_entries,
	normalize_entry_type,
	save_dictionary_entries,
	validate_dictionary_entry,
)
```

```python
import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from conversion.text.dictionary_rules import LoadedDictionaryRules
from dictionaries.entries import (
	DictionaryEntry,
	PreservedDictionaryRow,
	load_dictionary_entries,
	load_dictionary_rows,
	normalize_entry_type,
	save_dictionary_entries,
	validate_dictionary_entry,
)
from text.zhuyin import normalize_zhuyin_sequence

BOPOMOFO_DATA = Path(__file__).resolve().parents[1] / "data" / "Bopomofo2Braille.csv"

# dict_badbopo.csv of the Windows verification (F-W11): one Braille row and two Bopomofo
# rows whose sequences do not parse; UTF-8 without a BOM, CRLF.
DICT_BADBOPO = (
	"text,braille,type\r\n"
	"\u81fa\u5317,\u281e\u283a,Braille\r\n"
	"\u809a\u5b50,\u3109\u3128\u02cb|\u3117\u02d9,Bopomofo\r\n"
	"\u6578\u5b78,\u3115\u3128\u02cb \u3112\u3129\u311d\u02ca,Bopomofo\r\n"
).encode("utf-8")
DICT_BADBOPO_SHA256 = "c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4"

# Every kind of row the editor does not show, between two entries (F-4): a blank and a
# whitespace-only source text, an invalid Bopomofo sequence with spaces around it, a
# first-tone sequence whose tone space the editor would strip, a row with a missing
# field, and a quoted row whose fields hold a comma, quotes and a line break.
MIXED_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
	",\u2803,General\r\n"
	"  ,\u2803,General\r\n"
	"\u809a\u5b50, \u3109\u3128\u02cb|\u3117\u02d9 ,Bopomofo\r\n"
	"\u5abd,\u3107\u311a ,Bopomofo\r\n"
	",\u2803\r\n"
	'"q,""x""","a\r\nb",Bopomofo\r\n'
	"Beta,\u2803,General\r\n"
).encode("utf-8")
MIXED_ROWS = [
	DictionaryEntry("Alpha", "\u2801", "General"),
	PreservedDictionaryRow("", "\u2803", "General"),
	PreservedDictionaryRow("  ", "\u2803", "General"),
	PreservedDictionaryRow("\u809a\u5b50", " \u3109\u3128\u02cb|\u3117\u02d9 ", "Bopomofo"),
	PreservedDictionaryRow("\u5abd", "\u3107\u311a ", "Bopomofo"),
	PreservedDictionaryRow("", "\u2803", ""),
	PreservedDictionaryRow('q,"x"', "a\r\nb", "Bopomofo"),
	DictionaryEntry("Beta", "\u2803", "General"),
]
# What saving MIXED_ROWS writes: the same bytes, except that the row with a missing
# field gets its empty third field.
MIXED_CSV_SAVED = MIXED_CSV.replace(",\u2803\r\n".encode("utf-8"), ",\u2803,\r\n".encode("utf-8"))
```

Edit: `client/tests/test_dictionary_entries.py`

```python
		self.assertEqual(data, original)
		self.assertEqual(listing, ["sample.csv"])


if __name__ == "__main__":
```

```python
		self.assertEqual(data, original)
		self.assertEqual(listing, ["sample.csv"])

	def test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(MIXED_CSV)

			rows = load_dictionary_rows(path)

		self.assertEqual(rows, MIXED_ROWS)

	def test_save_writes_preserved_rows_unchanged_at_their_place(self) -> None:
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"

			save_dictionary_entries(path, MIXED_ROWS)

			data = path.read_bytes()

		self.assertEqual(data, MIXED_CSV_SAVED)

	def test_round_trip_of_a_file_with_invalid_bopomofo_rows_is_byte_identical(self) -> None:
		# F-W11: the editor's OK used to delete the two Bopomofo rows (4 lines -> 2).
		self.assertEqual(hashlib.sha256(DICT_BADBOPO).hexdigest(), DICT_BADBOPO_SHA256)
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "dict_badbopo.csv"
			path.write_bytes(DICT_BADBOPO)

			save_dictionary_entries(path, load_dictionary_rows(path))

			data = path.read_bytes()

		self.assertEqual(data, DICT_BADBOPO)

	def test_round_trip_normalizes_only_the_bom_line_ends_and_quoting(self) -> None:
		# An invalid one-symbol sequence, quoted, with LF line ends and a BOM.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(b"\xef\xbb\xbf" + 'text,braille,type\n"\u809a\u5b50","\u3109",Bopomofo\n'.encode("utf-8"))

			save_dictionary_entries(path, load_dictionary_rows(path))

			data = path.read_bytes()

		self.assertEqual(data, "text,braille,type\r\n\u809a\u5b50,\u3109,Bopomofo\r\n".encode("utf-8"))

	def test_round_trip_keeps_the_conversion_rules(self) -> None:
		# Conversion also uses the rows the editor hides (an invalid Bopomofo sequence
		# falls back to its raw symbols), so a load/save round trip must not change them.
		with tempfile.TemporaryDirectory() as temp_dir:
			path = Path(temp_dir) / "sample.csv"
			path.write_bytes(MIXED_CSV)
			before = LoadedDictionaryRules.from_paths(path, BOPOMOFO_DATA, processing=normalize_zhuyin_sequence)

			save_dictionary_entries(path, load_dictionary_rows(path))

			after = LoadedDictionaryRules.from_paths(path, BOPOMOFO_DATA, processing=normalize_zhuyin_sequence)

		self.assertEqual(after, before)
		self.assertIn("\u809a\u5b50", [source for source, _replacement in before.replacement_rules])

	def test_a_preserved_row_is_never_equal_to_an_entry(self) -> None:
		# The model removes and reselects entries by equality; a hidden row must never match.
		preserved = PreservedDictionaryRow("Alpha", "\u2801", "General")
		entry = DictionaryEntry("Alpha", "\u2801", "General")

		self.assertNotEqual(preserved, entry)
		self.assertNotEqual(entry, preserved)
		self.assertEqual([entry].count(preserved), 0)


if __name__ == "__main__":
```

```bash
$PY -m unittest tests.test_dictionary_entries 2>&1 | $PY $T/tools/brief.py
```

Expected (the module cannot import the new names):

```text
ERROR: test_dictionary_entries (unittest.loader._FailedTest.test_dictionary_entries)
ImportError: Failed to import test module: test_dictionary_entries
ImportError: cannot import name 'PreservedDictionaryRow' from 'dictionaries.entries' (<client>\dictionaries\entries.py)
Ran 1 test
FAILED (errors=1)
```

- [ ] **Step 2: Rows in the storage layer** (`client/dictionaries/entries.py`, tabs). The classification is today's rule exactly, moved into `_is_editable`; it calls `normalize_zhuyin_sequence` through the module global, so the existing `patch("dictionaries.entries.normalize_zhuyin_sequence", ...)` still applies.

Edit: `client/dictionaries/entries.py`

```python
import csv
from dataclasses import dataclass
from pathlib import Path
```

```python
import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
```

Edit: `client/dictionaries/entries.py`

```python
	entry_type: str = DEFAULT_ENTRY_TYPE


def normalize_entry_type(entry_type: str | None) -> str:
```

```python
	entry_type: str = DEFAULT_ENTRY_TYPE


@dataclass(frozen=True)
class PreservedDictionaryRow:
	"""A row the editor does not show: a blank source text, or a Bopomofo row whose
	sequence does not parse (F-4).

	Kept as read (fields not stripped, a missing field as "") and written back
	unchanged at its place in the file. Never equal to a ``DictionaryEntry``
	(dataclass equality requires the same class).
	"""

	text: str
	braille: str
	entry_type: str


DictionaryRow = DictionaryEntry | PreservedDictionaryRow


def normalize_entry_type(entry_type: str | None) -> str:
```

Edit: `client/dictionaries/entries.py`

```python
def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
	if not dictionary_path.exists():
		return []

	entries: list[DictionaryEntry] = []
	with dictionary_path.open("r", newline="", encoding="utf-8-sig") as fp:
		reader = csv.DictReader(fp)
		for row in reader:
			entry = DictionaryEntry(
				text=(row.get("text") or "").strip(),
				braille=(row.get("braille") or "").strip(),
				entry_type=normalize_entry_type(row.get("type")),
			)
			if not entry.text:
				continue
			if entry.entry_type == "Bopomofo":
				try:
					normalize_zhuyin_sequence(entry.braille)
				except Exception:
					continue
			entries.append(entry)
	return entries


def save_dictionary_entries(dictionary_path: Path, entries: list[DictionaryEntry]) -> None:
```

```python
def load_dictionary_rows(dictionary_path: Path) -> list[DictionaryRow]:
	"""Every data row of the file in file order: an entry, or a row the editor keeps hidden."""
	if not dictionary_path.exists():
		return []

	rows: list[DictionaryRow] = []
	with dictionary_path.open("r", newline="", encoding="utf-8-sig") as fp:
		reader = csv.DictReader(fp)
		for row in reader:
			entry = DictionaryEntry(
				text=(row.get("text") or "").strip(),
				braille=(row.get("braille") or "").strip(),
				entry_type=normalize_entry_type(row.get("type")),
			)
			if _is_editable(entry):
				rows.append(entry)
			else:
				rows.append(
					PreservedDictionaryRow(
						text=row.get("text") or "",
						braille=row.get("braille") or "",
						entry_type=row.get("type") or "",
					)
				)
	return rows


def _is_editable(entry: DictionaryEntry) -> bool:
	"""The editor shows a row with a source text whose Bopomofo sequence, if any, parses."""
	if not entry.text:
		return False
	if entry.entry_type == "Bopomofo":
		try:
			normalize_zhuyin_sequence(entry.braille)
		except Exception:
			return False
	return True


def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
	"""The rows the editor shows and Dictionary Management counts."""
	return [row for row in load_dictionary_rows(dictionary_path) if isinstance(row, DictionaryEntry)]


def save_dictionary_entries(dictionary_path: Path, rows: Iterable[DictionaryRow]) -> None:
```

Edit: `client/dictionaries/entries.py`

```python
		for entry in entries:
			writer.writerow(
				{
					"text": entry.text,
					"braille": entry.braille,
					"type": entry.entry_type,
				}
			)
```

```python
		for row in rows:
			writer.writerow(
				{
					"text": row.text,
					"braille": row.braille,
					"type": row.entry_type,
				}
			)
```

- [ ] **Step 3: Green.** The editor modules are unchanged and still pass (the model still loads entries only).

```bash
$PY -m unittest tests.test_dictionary_entries -v 2>&1 | grep -E "^test_(load_rows_keeps|save_writes_preserved|round_trip|a_preserved_row)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_a_preserved_row_is_never_equal_to_an_entry ok
test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order ok
test_round_trip_keeps_the_conversion_rules ok
test_round_trip_normalizes_only_the_bom_line_ends_and_quoting ok
test_round_trip_of_a_file_with_invalid_bopomofo_rows_is_byte_identical ok
test_save_writes_preserved_rows_unchanged_at_their_place ok
Ran 153 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1218 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/dictionaries/entries.py client/tests/test_dictionary_entries.py
git -C $REPO commit -q -m "fix: keep the dictionary rows the editor does not show when saving (F-4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
c57e1d9affc9445d43fd4b11a28c8aede3a05161
```

### Task 3: Keep hidden dictionary rows in place through the entries editor (D4, D5)

The model owns every file row in one ordered list; `entries` and the visible list are derived from it. The editor tests, the `KNOWN BUG (P2-2 spec, Q2)` flip and the trace oracle change are red on the code of Task 2.

- [ ] **Step 1: Red: the model tests** (`client/tests/test_dictionary_entry_list_model.py`, tabs). `PreservedRowsTest` uses four rows, `alpha, kept, beta, blank`, so that a new entry must go after a trailing preserved row and a remove or replace of the second entry cannot hit `kept` by its index.

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
from dictionaries.entries import DictionaryEntry
```

```python
from dictionaries.entries import DictionaryEntry, PreservedDictionaryRow
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
GENERAL = "\u4e00\u822c"
BOPOMOFO = "\u6ce8\u97f3"
```

```python
GENERAL = "\u4e00\u822c"
BOPOMOFO = "\u6ce8\u97f3"
DUZI = "\u809a\u5b50"
INVALID_DUZI = "\u3109\u3128\u02cb|\u3117\u02d9"  # "|" is not a Bopomofo symbol
VALID_DUZI = "\u3109\u3128\u02cb\u3117\u02d9"
# MIXED_CSV of test_dictionary_entries (F-4): two entries around every kind of row the
# editor does not show, and what saving it writes (the row with a missing field gets
# its empty third field).
MIXED_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
	",\u2803,General\r\n"
	"  ,\u2803,General\r\n"
	"\u809a\u5b50, \u3109\u3128\u02cb|\u3117\u02d9 ,Bopomofo\r\n"
	"\u5abd,\u3107\u311a ,Bopomofo\r\n"
	",\u2803\r\n"
	'"q,""x""","a\r\nb",Bopomofo\r\n'
	"Beta,\u2803,General\r\n"
).encode("utf-8")
MIXED_CSV_SAVED = MIXED_CSV.replace(",\u2803\r\n".encode("utf-8"), ",\u2803,\r\n".encode("utf-8"))
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
				self.assertUnchanged(
					self.model, [self.alpha, self.beta, self.gamma], [self.alpha, self.beta, self.gamma], ""
				)


class LoadSaveTest(unittest.TestCase):
```

```python
				self.assertUnchanged(
					self.model, [self.alpha, self.beta, self.gamma], [self.alpha, self.beta, self.gamma], ""
				)


class PreservedRowsTest(_ModelTestCase):
	"""Rows the editor does not show stay hidden, keep their place and count as duplicates (F-4)."""

	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.kept = PreservedDictionaryRow(DUZI, INVALID_DUZI, "Bopomofo")
		self.beta = _entry("Beta", "\u2803")
		self.blank = PreservedDictionaryRow("", "\u2803", "General")
		self.model = DictionaryEntryListModel([self.alpha, self.kept, self.beta, self.blank])

	def test_preserved_rows_are_not_entries_and_never_visible(self) -> None:
		self.assertUnchanged(self.model, [self.alpha, self.beta], [self.alpha, self.beta], "")
		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.beta, self.blank])
		for filter_text in (INVALID_DUZI[0], DUZI[0], "|"):
			with self.subTest(filter_text=filter_text):
				self.assertEqual(self.model.apply_filter(filter_text), EntryListUpdate(None))
				self.assertEqual(self.model.visible_entries, ())

	def test_remove_and_add_leave_preserved_rows_in_place(self) -> None:
		gamma = _entry("Gamma", "\u281b")

		self.assertEqual(self.model.remove(1), EntryListUpdate(0))
		self.assertEqual(self.model.add(gamma), EntryListUpdate(1))

		# The new entry goes to the end of the file, after the trailing preserved row.
		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.blank, gamma])
		self.assertSameObjects(self.model.entries, [self.alpha, gamma])

	def test_replace_leaves_preserved_rows_in_place(self) -> None:
		delta = _entry("Delta", "\u2819")

		self.assertEqual(self.model.replace(1, delta), EntryListUpdate(1))

		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, delta, self.blank])

	def test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate(self) -> None:
		valid = _entry(DUZI, VALID_DUZI, "Bopomofo")
		changes = (("add", lambda: self.model.add(valid)), ("replace", lambda: self.model.replace(1, valid)))
		for name, change in changes:
			with self.subTest(change=name):
				with self.assertRaises(DuplicateEntryError) as caught:
					change()

				self.assertEqual(caught.exception.identifier, DUZI)
				self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.beta, self.blank])


class LoadSaveTest(unittest.TestCase):
```

Edit: `client/tests/test_dictionary_entry_list_model.py`

```python
		with self.assertRaises(UnicodeDecodeError):
			DictionaryEntryListModel.load(path)


class ImportGuardTest(unittest.TestCase):
```

```python
		with self.assertRaises(UnicodeDecodeError):
			DictionaryEntryListModel.load(path)

	def test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place(self) -> None:
		source = self.directory / "source.csv"
		source.write_bytes(MIXED_CSV)
		target = self.directory / "target.csv"

		DictionaryEntryListModel.load(source).save(target)

		self.assertEqual(target.read_bytes(), MIXED_CSV_SAVED)


class ImportGuardTest(unittest.TestCase):
```

```bash
$PY -m unittest tests.test_dictionary_entry_list_model 2>&1 | $PY $T/tools/brief.py
```

Expected (the model of Task 2 shows and edits the preserved rows like entries, has no `rows`, and loads entries only):

```text
ERROR: test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate (tests.test_dictionary_entry_list_model.PreservedRowsTest.test_add_or_replace_
AttributeError: 'DictionaryEntryListModel' object has no attribute 'rows'
ERROR: test_replace_leaves_preserved_rows_in_place (tests.test_dictionary_entry_list_model.PreservedRowsTest.test_replace_leaves_preserved_rows_in_place)
FAIL: test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place (tests.test_dictionary_entry_list_model.LoadSaveTest.test_save_of_an_unchanged_model_w
AssertionError: b'tex[43 chars]l\r\nBeta,\xe2\xa0\x83,General\r\n' != b'tex[43 chars]l\r\n,\xe2\xa0\x83,General\r\n  ,\xe2\xa0\x83,[229 chars]\r\n'
FAIL: test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate (tests.test_dictionary_entry_list_model.PreservedRowsTest.test_add_or_replace_w
AssertionError: DuplicateEntryError not raised
FAIL: test_preserved_rows_are_not_entries_and_never_visible (tests.test_dictionary_entry_list_model.PreservedRowsTest.test_preserved_rows_are_not_entries_and_ne
AssertionError: Tuples differ: (Dict[57 chars]l'), PreservedDictionaryRow(text='肚子', braille[162 chars]al')) != (Dict[57 chars]l'), DictionaryEntry(text='Beta',
FAIL: test_remove_and_add_leave_preserved_rows_in_place (tests.test_dictionary_entry_list_model.PreservedRowsTest.test_remove_and_add_leave_preserved_rows_in_pl
AssertionError: EntryListUpdate(selection=1, filter_cleared=False) != EntryListUpdate(selection=0, filter_cleared=False)
Ran 44 tests
FAILED (failures=4, errors=2)
```

- [ ] **Step 2: Red: the editor tests, the Q2 flip and the trace oracle** (`client/tests/test_dictionary_entries_dialog.py`, 4 spaces). The fixture is not regenerated: the replay checks that the two hidden `TRACE_CSV` rows come back exactly once each and in order, removes those lines and compares every recorded step as before.

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
HEADER = "text,braille,type\r\n"


def _duplicate_message(identifier: str) -> str:
```

```python
HEADER = "text,braille,type\r\n"
# dict_badbopo.csv of the Windows verification (F-W11): one Braille row and two Bopomofo
# rows whose sequences do not parse, which the editor does not show; UTF-8, CRLF.
BADBOPO_HIDDEN_ROWS = (
    "\u809a\u5b50,\u3109\u3128\u02cb|\u3117\u02d9,Bopomofo\r\n"
    "\u6578\u5b78,\u3115\u3128\u02cb \u3112\u3129\u311d\u02ca,Bopomofo\r\n"
)
DICT_BADBOPO = (HEADER + "\u81fa\u5317,\u281e\u283a,Braille\r\n" + BADBOPO_HIDDEN_ROWS).encode("utf-8")
TAIPEI_CELLS = ["\u81fa\u5317", "\u281e\u283a", UNICODE_BRAILLE]


def _duplicate_message(identifier: str) -> str:
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
    def test_unchanged_dictionary_is_rewritten_in_normalized_form(self) -> None:
        # KNOWN BUG (P2-2 spec, Q2), pinned as it is today, NOT desired: OK always
        # rewrites the file and drops what the loader skipped or stripped.
        data = (
            "text,braille,type\n"
            " Alpha ,  \u2801 ,General\n"
            ",\u2803,General\n"
            "Zhuyin,invalid,Bopomofo\n"
            "Beta,\u2803,Custom\n"
        ).encode("utf-8")
        harness = self.open_editor(data=data)

        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")
```

```python
    def test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form(self) -> None:
        # KNOWN BUG (P2-2 spec, Q2), pinned as it is today, NOT desired: OK always
        # rewrites the file, stripping the shown rows and writing an unknown type as
        # General. Since F-4 the rows the editor does not show (blank source text,
        # invalid Bopomofo) are written back unchanged at their place.
        data = (
            "text,braille,type\n"
            " Alpha ,  \u2801 ,General\n"
            ",\u2803,General\n"
            "Zhuyin,invalid,Bopomofo\n"
            "Beta,\u2803,Custom\n"
        ).encode("utf-8")
        harness = self.open_editor(data=data)

        self.assertTrue(harness.press_ok())

        self.assertEqual(
            harness.saved_csv(),
            HEADER + "Alpha,\u2801,General\r\n,\u2803,General\r\nZhuyin,invalid,Bopomofo\r\nBeta,\u2803,General\r\n",
        )
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
class DictionaryEntriesDialogModelTest(_EditorTestCase):
```

```python
class DictionaryEntriesDialogHiddenRowsTest(_EditorTestCase):
    """Rows the editor cannot show are kept, hidden, through OK (F-4, F-W11)."""

    def test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical(self) -> None:
        # F-W11: OK used to delete the two Bopomofo rows the editor cannot show (4 lines -> 2).
        harness = self.open_editor(data=DICT_BADBOPO)

        self.assertEqual(harness.rows(), [TAIPEI_CELLS])
        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.path.read_bytes(), DICT_BADBOPO)
        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])

    def test_deleting_every_shown_row_keeps_the_hidden_rows(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.select(0)
        harness.click("Delete")

        self.assertEqual(harness.rows(), [])
        self.assertTrue(harness.press_ok())

        self.assertEqual(harness.saved_csv(), HEADER + BADBOPO_HIDDEN_ROWS)

    def test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message(self) -> None:
        harness = self.open_editor(data=DICT_BADBOPO)
        harness.script_entry("\u809a\u5b50", "\u3109\u3128\u02cb\u3117\u02d9", "Bopomofo")

        harness.click("Add")

        self.assertEqual(
            harness.take_log(),
            [["AddSymbolDialog", None], ["MessageBox", _duplicate_message("\u809a\u5b50"), ERROR_TITLE, ERROR_FLAGS]],
        )
        self.assertEqual(harness.rows(), [TAIPEI_CELLS])
        self.assertTrue(harness.press_ok())
        self.assertEqual(harness.path.read_bytes(), DICT_BADBOPO)


class DictionaryEntriesDialogModelTest(_EditorTestCase):
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
_TRACE_KINDS = ("filter", "filter", "select", "select", "deselect", "add", "add", "edit", "activate", "delete")
```

```python
_TRACE_KINDS = ("filter", "filter", "select", "select", "deselect", "add", "add", "edit", "activate", "delete")
# The two TRACE_CSV rows the editor does not show (blank source text, invalid Bopomofo).
# The fixture was recorded before F-4, when OK dropped them; since F-4 OK writes them
# back unchanged, so the replay checks them and removes them before comparing.
_TRACE_KEPT_ROWS = (",\u2803,General", "zz,ab,Bopomofo")
```

Edit: `client/tests/test_dictionary_entries_dialog.py`

```python
                        lambda _harness, index, expected=expected: expected[index + 1]["action"],
                    )
                    for index, (got, want) in enumerate(zip(actual, expected)):
```

```python
                        lambda _harness, index, expected=expected: expected[index + 1]["action"],
                    )
                    # Line by line, not by substring: an entry row such as "ab,\u2803,General"
                    # ends with the first kept row.
                    lines = actual[-1]["csv"].split("\r\n")
                    self.assertEqual([line for line in lines if line in _TRACE_KEPT_ROWS], list(_TRACE_KEPT_ROWS))
                    actual[-1]["csv"] = "\r\n".join(line for line in lines if line not in _TRACE_KEPT_ROWS)
                    for index, (got, want) in enumerate(zip(actual, expected)):
```

```bash
$PY -m unittest tests.test_dictionary_entries_dialog > $T/red3.txt 2>&1
$PY $T/tools/brief.py < $T/red3.txt | grep -v "(seed="
grep -c "^FAIL: test_replay_matches_every_recorded_step .*(seed=" $T/red3.txt
```

Expected (E1-E3 and the flipped test fail on the old output; the trace fails in all 40 sequences because the kept rows are missing):

```text
FAIL: test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.test_a
AssertionError: Lists differ: [['Ad[20 chars]], ['SetItemCount', 2], ['Refresh'], ['Select'[90 chars]rue]] != [['Ad[20 chars]], ['MessageBox', '來源文字「肚子」已存在。', '
FAIL: test_deleting_every_shown_row_keeps_the_hidden_rows (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.test_deleting_every_shown_
AssertionError: 'text,braille,type\r\n' != 'text,braille,type\r\n肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n'
FAIL: test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogHiddenRowsTest.tes
AssertionError: b'tex[74 chars]e\r\n' != b'tex[74 chars]e\r\n\xe8\x82\x9a\xe5\xad\x90,\xe3\x84\x89\xe3[161 chars]\r\n'
FAIL: test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogOkTest.test_u
AssertionError: 'text[31 chars]l\r\nBeta,⠃,General\r\n' != 'text[31 chars]l\r\n,⠃,General\r\nZhuyin,invalid,Bopomofo\r\n[14 chars]\r\n'
AssertionError: Lists differ: [] != [',⠃,General', 'zz,ab,Bopomofo']
Ran 72 tests
FAILED (failures=44)
40
```

- [ ] **Step 3: One ordered list of rows in the model** (`client/dictionaries/entry_list_model.py`, tabs). Each operation keeps its P2-2 meaning on the entries: `add` appends to the end of the file, `replace` swaps by identity in place, `remove` deletes the first equal entry (never a preserved row, which is never equal to an entry).

Edit: `client/dictionaries/entry_list_model.py`

```python
The model owns the full entry list in file order, the filter text and the
visible (filtered) list. The dialog owns the widgets and the selected row: it
passes the selected visible index into each call and renders the returned
``EntryListUpdate``. Nothing here imports wx or i18n; the dialog shows the
messages.
```

```python
The model owns every row of the file in file order, the filter text and the
visible (filtered) list. The dialog owns the widgets and the selected row: it
passes the selected visible index into each call and renders the returned
``EntryListUpdate``. Nothing here imports wx or i18n; the dialog shows the
messages.

Rows that are not a ``DictionaryEntry`` (``PreservedDictionaryRow``: a blank
source text, or a Bopomofo sequence that does not parse) are never shown,
filtered, edited or removed: they keep their place in the file and ``save``
writes them back unchanged (F-4). ``entries`` and the visible list hold the
entries only.
```

Edit: `client/dictionaries/entry_list_model.py`

```python
* the duplicate check compares ``text`` exactly (case-sensitive) over the full
  list, hidden rows included, and excludes the edited entry by identity.
```

```python
* the duplicate check compares ``text`` exactly (case-sensitive) over every
  row, entries hidden by the filter and preserved rows included, and excludes
  the edited entry by identity.
```

Edit: `client/dictionaries/entry_list_model.py`

```python
	DictionaryEntry,
	load_dictionary_entries,
	save_dictionary_entries,
)
```

```python
	DictionaryEntry,
	DictionaryRow,
	load_dictionary_rows,
	save_dictionary_entries,
)
```

Edit: `client/dictionaries/entry_list_model.py`

```python
	def __init__(self, entries: Iterable[DictionaryEntry] = ()) -> None:
		self._entries: list[DictionaryEntry] = list(entries)
		self._filter_text = ""
		self._visible: list[DictionaryEntry] = list(self._entries)

	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel:
		"""Read ``path`` with ``load_dictionary_entries``; errors propagate."""
		return cls(load_dictionary_entries(path))

	def save(self, path: Path) -> None:
		"""Write the full list (not only the visible rows); errors propagate."""
		save_dictionary_entries(path, self._entries)

	@property
	def entries(self) -> tuple[DictionaryEntry, ...]:
```

```python
	def __init__(self, rows: Iterable[DictionaryRow] = ()) -> None:
		self._rows: list[DictionaryRow] = list(rows)
		self._filter_text = ""
		self._visible: list[DictionaryEntry] = list(self._entries)

	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel:
		"""Read every row of ``path`` with ``load_dictionary_rows``; errors propagate."""
		return cls(load_dictionary_rows(path))

	def save(self, path: Path) -> None:
		"""Write every row (preserved rows unchanged, in place); errors propagate."""
		save_dictionary_entries(path, self._rows)

	@property
	def _entries(self) -> list[DictionaryEntry]:
		return [row for row in self._rows if isinstance(row, DictionaryEntry)]

	@property
	def rows(self) -> tuple[DictionaryRow, ...]:
		"""Every row of the file in file order, preserved rows included."""
		return tuple(self._rows)

	@property
	def entries(self) -> tuple[DictionaryEntry, ...]:
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		return any(entry.text == text and entry is not exclude_entry for entry in self._entries)
```

```python
		return any(row.text == text and row is not exclude_entry for row in self._rows)
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		self._entries.append(entry)
```

```python
		self._rows.append(entry)
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		full_index = next(index for index, candidate in enumerate(self._entries) if candidate is current_entry)
		self._entries[full_index] = entry
```

```python
		full_index = next(index for index, candidate in enumerate(self._rows) if candidate is current_entry)
		self._rows[full_index] = entry
```

Edit: `client/dictionaries/entry_list_model.py`

```python
		self._entries.remove(current_entry)
```

```python
		self._rows.remove(current_entry)
```

- [ ] **Step 4: Green.** The trace replays all 40 sequences with the fixture unchanged; `ImportGuardTest` passes with the same import set.

```bash
$PY -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog -v 2>&1 | grep -E "^test_(preserved_rows_are|remove_and_add_leave|replace_leaves|add_or_replace_with|save_of_an_unchanged_model|invalid_bopomofo_rows_are_hidden|deleting_every_shown_row|adding_the_source_text_of_a_hidden|unchanged_dictionary_keeps_hidden|replay_matches|model_imports_no)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
git -C $REPO status --short -- client/tests/fixtures client/conversion client/locales
```

Expected (`status` prints nothing):

```text
test_model_imports_no_ui_or_translation_module ok
test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place ok
test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate ok
test_preserved_rows_are_not_entries_and_never_visible ok
test_remove_and_add_leave_preserved_rows_in_place ok
test_replace_leaves_preserved_rows_in_place ok
test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message ok
test_deleting_every_shown_row_keeps_the_hidden_rows ok
test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical ok
test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form ok
test_replay_matches_every_recorded_step ok
Ran 161 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1226 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/dictionaries/entry_list_model.py client/tests/test_dictionary_entry_list_model.py client/tests/test_dictionary_entries_dialog.py
git -C $REPO commit -q -m "fix: keep hidden dictionary rows in place through the entries editor (F-4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
a64e34d8dec7b1909f7fae5c8b9b4327d3d7f6b2
```

### Task 4: Verification (no commit)

`BASE` is the merge base with `main` (`4953772` until Task 6).

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = baseline 1211 + 15; the error is F-W6):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1226 tests
FAILED (errors=1, skipped=5)
```

- [ ] **Step 2: Criterion 2, focused modules; the 15 new tests and the flipped one ran and passed.**

```bash
$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_conversion_text_dictionary_rules tests.test_translation_golden 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog -v 2>&1 | grep -cE "^test_(rows_the_editor_does_not_show_are_not_counted|load_rows_keeps|save_writes_preserved|round_trip_of_a_file_with|round_trip_normalizes|round_trip_keeps|a_preserved_row_is_never|preserved_rows_are|remove_and_add_leave|replace_leaves|add_or_replace_with|save_of_an_unchanged_model|invalid_bopomofo_rows_are_hidden|deleting_every_shown_row|adding_the_source_text_of_a_hidden|unchanged_dictionary_keeps_hidden)[a-z_]* .* ok$"
```

Expected:

```text
Ran 202 tests
OK
16
```

- [ ] **Step 3: Shuffled module order, six seeds** (one process each, a few minutes).

```bash
for s in 0 1 2 3 4 5; do $PY $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
      6 ran=1226 failures=0 errors=1 skipped=5 ['test_case_only_rename_still_renames']
```

- [ ] **Step 4: Criteria 3 and 4, strings, locales, fixtures and the untouched modules.**

```bash
BASE=$(git -C $REPO merge-base main HEAD)
git -C $REPO diff --stat $BASE -- client/locales client/tests/fixtures client/conversion client/dialog.py client/gui.py client/shared client/dictionaries/manager.py client/dictionaries/presenter.py
git -C $REPO diff $BASE -- client ':!client/tests' | grep -E '^\+.*\b(N_|_)\(' ; echo "new gettext calls: exit $?"
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/conversion && echo "client/conversion unchanged"
```

Expected (the first `diff --stat` prints nothing; `grep` finds no new `_(`/`N_(` call, exit 1; msgids identical to Task 0):

```text
new gettext calls: exit 1
source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
client/conversion unchanged
```

- [ ] **Step 5: Criteria 5, 6 and 8, touched files, the narrowed marker, app data.**

```bash
BASE=$(git -C $REPO merge-base main HEAD)
git -C $REPO diff --stat=200 $BASE -- client
git -C $REPO grep -n -A3 "KNOWN BUG (P2-2 spec, Q2)" -- client/tests | sed 's/^client\/tests\/test_dictionary_entries_dialog.py[-:][0-9]*[-:]//'
for p in dictionary workspace config.json; do test -e $p && echo "EXISTS client/$p"; done; echo "app data checked"
(cd $MAIN/client/dictionary && sha256sum --quiet -c $T/main-dictionary.sha256) && ls $MAIN/client/dictionary | wc -l
git -C $REPO status --short
```

Expected (the worktree has no `client/dictionary/`, `client/workspace/` or `client/config.json` and the suite created none; the main checkout's dictionary folder is the one recorded in Task 0; `status` prints nothing):

```text
 client/dictionaries/entries.py                    |  75 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++------------------
 client/dictionaries/entry_list_model.py           |  47 ++++++++++++++++++++++++++++++++---------------
 client/tests/test_dictionary_entries.py           | 114 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_dictionary_entries_dialog.py    |  66 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---
 client/tests/test_dictionary_entry_list_model.py  |  76 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 client/tests/test_dictionary_management_dialog.py |  21 +++++++++++++++++++++
 6 files changed, 362 insertions(+), 37 deletions(-)
        # KNOWN BUG (P2-2 spec, Q2), pinned as it is today, NOT desired: OK always
        # rewrites the file, stripping the shown rows and writing an unknown type as
        # General. Since F-4 the rows the editor does not show (blank source text,
        # invalid Bopomofo) are written back unchanged at their place.
app data checked
1
```

- [ ] **Step 6: Criterion 7, mutation check** (19 mutants, a few minutes). Each mutant must be caught by at least one test. `trace-oracle-removes-substrings` mutates the test, not the code: it shows that the substring variant of the oracle fails on correct code, so the line-wise comparison is needed.

```bash
$PY $T/tools/f4_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
preserved-fields-stripped: 3 caught: test_dictionary_entries.test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order, test_dictionary_entries.test_round_trip_keeps_the_conversion_rules, test_dictionary_entry_list_model.test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place
preserved-type-normalized: 2 caught: test_dictionary_entries.test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order, test_dictionary_entry_list_model.test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place
missing-field-kept-as-none: 1 caught: test_dictionary_entries.test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order
blank-text-rows-shown: 7 caught: test_dictionary_entries.test_load_filters_empty_and_invalid_bopomofo_rows, test_dictionary_entries.test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order, test_dictionary_entries.test_round_trip_keeps_the_conversion_rules, test_dictionary_entries_dialog.test_loads_only_rows_accepted_by_the_editor, test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, test_dictionary_entry_list_model.test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place, test_dictionary_management_dialog.test_refresh_sets_virtual_count_and_valid_entry_counts
invalid-bopomofo-rows-shown: 10 caught: test_dictionary_entries.test_load_filters_empty_and_invalid_bopomofo_rows, test_dictionary_entries.test_load_rows_keeps_the_rows_the_editor_does_not_show_in_file_order, test_dictionary_entries.test_round_trip_keeps_the_conversion_rules, test_dictionary_entries_dialog.test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message, test_dictionary_entries_dialog.test_deleting_every_shown_row_keeps_the_hidden_rows, test_dictionary_entries_dialog.test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical, test_dictionary_entries_dialog.test_loads_only_rows_accepted_by_the_editor, test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, and 2 more
load-entries-returns-every-row: 4 caught: test_dictionary_entries.test_load_filters_empty_and_invalid_bopomofo_rows, test_dictionary_entries_dialog.test_loads_only_rows_accepted_by_the_editor, test_dictionary_management_dialog.test_refresh_sets_virtual_count_and_valid_entry_counts, test_dictionary_management_dialog.test_rows_the_editor_does_not_show_are_not_counted
save-writes-preserved-rows-last: 4 caught: test_dictionary_entries.test_round_trip_keeps_the_conversion_rules, test_dictionary_entries.test_save_writes_preserved_rows_unchanged_at_their_place, test_dictionary_entries_dialog.test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form, test_dictionary_entry_list_model.test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place
save-skips-preserved-rows: 10 caught: test_dictionary_entries.test_round_trip_keeps_the_conversion_rules, test_dictionary_entries.test_round_trip_normalizes_only_the_bom_line_ends_and_quoting, test_dictionary_entries.test_round_trip_of_a_file_with_invalid_bopomofo_rows_is_byte_identical, test_dictionary_entries.test_save_writes_preserved_rows_unchanged_at_their_place, test_dictionary_entries_dialog.test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message, test_dictionary_entries_dialog.test_deleting_every_shown_row_keeps_the_hidden_rows, test_dictionary_entries_dialog.test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical, test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, and 2 more
preserved-row-subclass-of-entry: 12 caught: test_dictionary_entries.test_load_filters_empty_and_invalid_bopomofo_rows, test_dictionary_entries_dialog.test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message, test_dictionary_entries_dialog.test_deleting_every_shown_row_keeps_the_hidden_rows, test_dictionary_entries_dialog.test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical, test_dictionary_entries_dialog.test_loads_only_rows_accepted_by_the_editor, test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, test_dictionary_entry_list_model.test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate, test_dictionary_entry_list_model.test_preserved_rows_are_not_entries_and_never_visible, and 4 more
preserved-row-equal-to-entry: 1 caught: test_dictionary_entries.test_a_preserved_row_is_never_equal_to_an_entry
model-shows-every-row: 8 caught: test_dictionary_entries_dialog.test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message, test_dictionary_entries_dialog.test_deleting_every_shown_row_keeps_the_hidden_rows, test_dictionary_entries_dialog.test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical, test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, test_dictionary_entry_list_model.test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate, test_dictionary_entry_list_model.test_preserved_rows_are_not_entries_and_never_visible, test_dictionary_entry_list_model.test_remove_and_add_leave_preserved_rows_in_place, test_dictionary_entry_list_model.test_replace_leaves_preserved_rows_in_place
filter-over-every-row: 2 caught: test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, test_dictionary_entry_list_model.test_preserved_rows_are_not_entries_and_never_visible
model-saves-entries-only: 6 caught: test_dictionary_entries_dialog.test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message, test_dictionary_entries_dialog.test_deleting_every_shown_row_keeps_the_hidden_rows, test_dictionary_entries_dialog.test_invalid_bopomofo_rows_are_hidden_and_ok_keeps_the_file_byte_identical, test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, test_dictionary_entries_dialog.test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form, test_dictionary_entry_list_model.test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place
model-saves-preserved-rows-last: 2 caught: test_dictionary_entries_dialog.test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form, test_dictionary_entry_list_model.test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place
add-before-trailing-preserved-rows: 1 caught: test_dictionary_entry_list_model.test_remove_and_add_leave_preserved_rows_in_place
remove-by-visible-index: 5 caught: test_dictionary_entries_dialog.test_identical_rows_delete_removes_the_first_equal_row, test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, test_dictionary_entry_list_model.test_identical_rows_remove_the_first_equal_and_select_the_remaining_twin, test_dictionary_entry_list_model.test_remove_and_add_leave_preserved_rows_in_place, test_dictionary_entry_list_model.test_removing_the_only_visible_row_has_no_selection
replace-by-visible-index: 5 caught: test_dictionary_entries_dialog.test_edit_entry_that_stops_matching_removes_it_from_visible_list, test_dictionary_entries_dialog.test_edit_visible_entry_updates_full_list_and_preserves_selection, test_dictionary_entries_dialog.test_replay_matches_every_recorded_step, test_dictionary_entry_list_model.test_hidden_result_with_nothing_left_has_no_selection, test_dictionary_entry_list_model.test_replace_leaves_preserved_rows_in_place
duplicate-check-over-entries-only: 2 caught: test_dictionary_entries_dialog.test_adding_the_source_text_of_a_hidden_row_shows_the_duplicate_message, test_dictionary_entry_list_model.test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate
trace-oracle-removes-substrings: 1 caught: test_dictionary_entries_dialog.test_replay_matches_every_recorded_step
exit 0
```

### Task 5: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay except the build and the script checks: the same code was built in a scratch clone with the command below ("Build complete!" in 47 s, 48,737,338 bytes, the bundle lists the clone's own dictionary modules), and the scripts were syntax-checked and `rerun.py --check` run on the four 2026-10-09-03 scripts; the GUI was not driven. Run everything from the worktree root, one item at a time, with nothing else driving the desktop. Never touch `D:\dxtest\N`, `D:\dxtest\B`, `D:\dxtest\N-p25`, `D:\dxtest\N-f3` or the existing `D:\dxtest\auto*` folders; every F-4 run uses a new folder whose name contains `f4`.

- [ ] **Step 1: Build** (PowerShell). The worktree has no `client\.venv`; the main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`, and `pyinstaller.exe` analyzes `gui.py` in the current checkout (the venv adds no path of the main checkout). Task 0 already copied the generated `liblouis.dll`, `liblouis\tables`, `louis_helper.py` and `mathcat\assets` the build bundles.

```powershell
Set-Location D:\workspace\DotExpress-f4
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f4-build.log 2>&1"
if (Select-String -Path $env:TEMP\f4-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "entries.py", "entry_list_model.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress-f4\\client\\dictionaries\\$m" -Quiet) { "$m bundled from the worktree" } }
(Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "workspace\\DotExpress\\client\\dictionaries").Count
New-Item -ItemType Directory -Force D:\dxtest\N-f4 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f4\DotExpress.exe
(Get-Item D:\dxtest\N-f4\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f4\DotExpress.exe).Hash
git status --short
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f4-build.log`), `entries.py bundled from the worktree`, `entry_list_model.py bundled from the worktree`, `0` (no dictionary module of the main checkout), a size near 48.7 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored). If the main venv is gone, create one in the worktree instead (`py -3.13 -m venv client\.venv`, then `client\.venv\Scripts\pip install -r client\requirements.txt pyinstaller==6.21.0`; `client\.venv\` is git-ignored) and put that on `PATH`.

- [ ] **Step 2: Create the GUI scripts** in the new history folder (tabs, like the 2026-10-09-03 scripts they reuse). `rerun.py` runs the committed `item23.py`, `item24.py`, `item25.py` and `item29.py` against the F-4 build by replacing their path literals in memory (the committed scripts stay unchanged); `item35.py` is new and imports `dx.py`, `docs.py` and `dicts.py` of the 2026-10-09-03 folder.

File: `docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/auto/rerun.py`

````python
"""Run a 2026-10-09-03 dictionary GUI script against the F-4 build (F-4).

Usage: python rerun.py <item23.py|item24.py|item25.py|item29.py> [--check]

The committed scripts hard-code the N build (D:\\dxtest\\N\\DotExpress.exe) and their
work folders. This wrapper reads the script, replaces the literals listed in REPLACE
(each must occur exactly once) and runs it with __file__ pointing at the original, so it
still imports dx/docs/dicts and finds lock.py next to it. The committed scripts are not
changed.

- item23.py: B and the F-4 build (N-f4), in D:\\dxtest\\auto23-f4-B and
  D:\\dxtest\\auto23-f4-N-f4 (dx.launch deletes a work folder first).
- item24.py: the F-4 build in D:\\dxtest\\auto24-f4.
- item25.py: restarts the app in that folder and runs only up to "# 29 ACL deny write"
  (that section uses (W), superseded by item29.py, F-W13); the app stays open.
- item29.py: attaches to the app running in D:\\dxtest\\auto24-f4.

With --check nothing runs: each replaced line and the last line kept are printed.
"""
import os
import sys

N_EXE = 'r"D:\\dxtest\\N\\DotExpress.exe"'
F4_EXE = 'r"D:\\dxtest\\N-f4\\DotExpress.exe"'
AUTO24 = 'r"D:\\dxtest\\auto24"'
AUTO24_F4 = 'r"D:\\dxtest\\auto24-f4"'
REPLACE = {
	"item23.py": (
		('for v in ("B", "N"):', 'for v in ("B", "N-f4"):'),
		('rf"D:\\dxtest\\auto23-{v}"', 'rf"D:\\dxtest\\auto23-f4-{v}"'),
	),
	"item24.py": ((N_EXE, F4_EXE), (AUTO24, AUTO24_F4)),
	"item25.py": ((N_EXE, F4_EXE), (AUTO24, AUTO24_F4)),
	"item29.py": ((AUTO24, AUTO24_F4),),
}
STOP = {"item25.py": "# 29 ACL deny write\n"}


def main():
	args = sys.argv[1:]
	check = "--check" in args
	if check:
		args.remove("--check")
	script = os.path.abspath(args[0])
	name = os.path.basename(script)
	if name not in REPLACE:
		sys.exit(f"{name}: expected one of {sorted(REPLACE)}")
	with open(script, encoding="utf-8") as handle:
		source = handle.read()
	for old, new in REPLACE[name]:
		if source.count(old) != 1:
			sys.exit(f"{old} occurs {source.count(old)} times in {script}")
		source = source.replace(old, new)
	if name in STOP:
		if source.count(STOP[name]) != 1:
			sys.exit(f"{STOP[name]!r} occurs {source.count(STOP[name])} times in {script}")
		source = source[:source.index(STOP[name])]
	if check:
		for _old, new in REPLACE[name]:
			print(name, "|", next(line.strip() for line in source.splitlines() if new in line))
		print(name, "| last:", source.rstrip().splitlines()[-1].strip())
		return
	sys.argv = [script]
	sys.path.insert(0, os.path.dirname(script))
	exec(compile(source, script, "exec"), {"__name__": "__main__", "__file__": script})


if __name__ == "__main__":
	main()
````

File: `docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/auto/item35.py`

````python
"""Item 35 (F-4): dict_badbopo.csv through Dictionary Management and the entries editor.

Usage: python item35.py <exe> <work folder>
Reuses dx.py, docs.py and dicts.py of the 2026-10-09-03 Windows verification unchanged;
dx.launch deletes the work folder first. D:\\dxtest\\data\\dict_badbopo.csv is
auto/data/dict_badbopo.csv of that folder (sha256 c4324573...).

After F-4: count 1; the editor shows one row (臺北); an unchanged OK keeps the file
byte-identical, leaves no .tmp and keeps the conversion output of 肚子數學; Add of
肚子 / ㄉㄨˋㄗ˙ / 注音 shows 來源文字「肚子」已存在。 and the next OK keeps the file;
Delete of 臺北 and OK leave the header and the two Bopomofo rows, count 0; after a
restart the editor is empty and the file unchanged.
Before F-4 (B, N): the first OK leaves 2 lines, the second conversion differs, the Add
succeeds.
"""
import hashlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO03 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-09-03-windows-verification", "auto"))
sys.path.insert(0, AUTO03)
import dx  # noqa: E402
import docs as D  # noqa: E402
import dicts as X  # noqa: E402

SOURCE = r"D:\dxtest\data\dict_badbopo.csv"
NAME = "dict_badbopo"
MANAGER = "字典管理"
EDITOR = "自訂字典管理器"
WORD = "肚子數學"
HEADER_AND_HIDDEN_ROWS = "text,braille,type\r\n肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n".encode("utf-8")

EXE, d = sys.argv[1], sys.argv[2]
dd = os.path.join(d, "dictionary")
P = os.path.join(dd, NAME + ".csv")


def read(path=P):
	with open(path, "rb") as handle:
		return handle.read()


def sha(data):
	return hashlib.sha256(data).hexdigest()


def listing():
	return sorted(os.listdir(dd))


def manager():
	return X.windows(app, w).get(MANAGER) or X.open_mgr(app, w)


def count():
	return [row for row in X.mgr_items(manager())[1] if row[0] == NAME]


def close_manager():
	mgr = X.windows(app, w).get(MANAGER)
	if mgr:
		X.close_mgr(app, w, mgr)


def editor():
	return X.open_editor(app, w, manager(), NAME)


def add_entry(ed, text, braille, type_label):
	"""Add through the real entry dialog; return the popups that follow (read and dismissed)."""
	X.btn(ed, "新增").click()
	entry_dialog = X.wait_window(app, w, "新增字典項目")
	controls = entry_dialog.wrapper_object().descendants()
	edits = [c for c in controls if c.class_name() == "Edit"]
	edits[0].set_edit_text(text)
	edits[1].set_edit_text(braille)
	[c for c in controls if c.class_name() == "ComboBox"][0].select(type_label)
	X.btn(entry_dialog, "確定", "OK").click()
	time.sleep(1.5)
	return X.popups(app, w, keep=(MANAGER, EDITOR))


def delete_first_row(ed):
	rows = [c for c in ed.wrapper_object().descendants() if c.class_name() == "SysListView32"][0]
	rows.get_item(0).select()
	time.sleep(0.5)
	X.btn(ed, "刪除").click()
	time.sleep(0.8)


def convert():
	close_manager()
	D.set_input(w, WORD)
	return X.convert(app, w)


source = read(SOURCE)
print("source sha256:", sha(source), "lines:", source.count(b"\n"))
app, w = dx.launch(EXE, d)
print("import:", X.import_named(app, w, manager(), SOURCE))
print("imported identical:", read() == source, "mgr:", count())
close_manager()
D.select(w, "new")
X.set_dictionary(app, w, NAME)
first, messages = convert()
print("convert 1:", repr(first), messages)

# 35a: an unchanged OK keeps the file and the conversion output.
ed = editor()
print("35a rows:", X.editor_rows(ed))
print("35a ok:", X.editor_ok(app, w, ed))
after = read()
print("35a identical:", after == source, "lines:", after.count(b"\n"), "sha256:", sha(after), "files:", listing())
second, messages = convert()
print("35a convert 2:", repr(second), messages, "same as convert 1:", second == first)

# 35b: an entry with the source text of a hidden row is refused.
ed = editor()
print("35b add:", add_entry(ed, "肚子", "ㄉㄨˋㄗ˙", "注音"))
print("35b rows:", X.editor_rows(ed))
print("35b ok:", X.editor_ok(app, w, ed))
print("35b identical:", read() == source, "files:", listing())

# 35c: deleting every shown row keeps the hidden rows.
ed = editor()
delete_first_row(ed)
print("35c rows after delete:", X.editor_rows(ed))
print("35c ok:", X.editor_ok(app, w, ed))
data = read()
print("35c header and hidden rows:", data == HEADER_AND_HIDDEN_ROWS, repr(data.decode("utf-8")), "files:", listing())
print("35c mgr:", count())
close_manager()
print("close:", D.close(app, w))

# 35d: after a restart the editor is empty and the file unchanged.
app, w = dx.launch(EXE, d, fresh=False)
print("35d mgr:", count())
ed = editor()
print("35d rows:", X.editor_rows(ed))
X.btn(ed, "取消", "Cancel").click()
time.sleep(1)
print("35d unchanged:", read() == HEADER_AND_HIDDEN_ROWS, "files:", listing())
close_manager()
print("close:", D.close(app, w))
````

Check the scripts without driving the GUI (Git Bash, from the worktree root; `UIA` is the separate venv with pywinauto 0.6.9 and psutil 7.2.2):

```bash
UIA=/c/Users/tseng/AppData/Local/Temp/claude/D--workspace-DotExpress/c9251692-6537-4306-992c-fd6377e303d0/scratchpad/uia/Scripts/python.exe
H3=docs/superpowers/history/2026-10-09-03-windows-verification/auto
H6=docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/auto
export PYTHONIOENCODING=utf-8
cd /d/workspace/DotExpress-f4
"$UIA" -c "import pywinauto, psutil; print(pywinauto.__version__, psutil.__version__)"
"$UIA" -c "import ast, glob; [ast.parse(open(p, encoding='utf-8').read(), p) for p in glob.glob('$H6/*.py')]; print('syntax ok')"
for i in 23 24 25 29; do "$UIA" $H6/rerun.py $H3/item$i.py --check; done
git status --short
sha256sum /d/dxtest/data/dict_badbopo.csv $H3/data/dict_badbopo.csv | cut -c1-64
```

Expected (`git status` lists only the new folder; the data file used by the scripts is the committed one):

```text
0.6.9 7.2.2
syntax ok
item23.py | for v in ("B", "N-f4"):
item23.py | d = rf"D:\dxtest\auto23-f4-{v}"
item23.py | last: print(v, "dictionary dir:", os.listdir(dd))
item24.py | app, w = dx.launch(r"D:\dxtest\N-f4\DotExpress.exe", d)
item24.py | d = r"D:\dxtest\auto24-f4"; dd = os.path.join(d, "dictionary")
item24.py | last: print("close:", D.close(app, w))
item25.py | app, w = dx.launch(r"D:\dxtest\N-f4\DotExpress.exe", d, fresh=False)
item25.py | d = r"D:\dxtest\auto24-f4"; dd = os.path.join(d, "dictionary")
item25.py | last: print("28 failures:", fails, "state:", state())
item29.py | d = r"D:\dxtest\auto24-f4"; dd = os.path.join(d, "dictionary")
item29.py | last: print("final:", state(), attrib(P))
?? docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/
c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4
c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4
```

If `D:\dxtest\data\` is missing or differs, copy the six files of `$H3/data/` there first (`cp $H3/data/*.csv /d/dxtest/data/`). If the `UIA` venv no longer exists, create one anywhere outside the repo with `python -m venv` and `pip install pywinauto==0.6.9 psutil`, and use its `python.exe`.

- [ ] **Step 3: Items 23-29 against the F-4 build** (Git Bash, variables of Step 2). Defender real-time protection must be on for item 28 (`(Get-MpComputerStatus).RealTimeProtectionEnabled`). Item 25 restarts the app in item 24's folder and leaves it open; item 29 attaches to it and closes it.

```bash
"$UIA" $H6/rerun.py $H3/item23.py > /d/dxtest/auto23-f4.log 2>&1
"$UIA" $H6/rerun.py $H3/item24.py > /d/dxtest/auto24-f4.log 2>&1
"$UIA" $H6/rerun.py $H3/item25.py > /d/dxtest/auto25-f4.log 2>&1
"$UIA" $H6/rerun.py $H3/item29.py > /d/dxtest/auto29-f4.log 2>&1
```

Expected (compare with `2026-10-09-03-windows-verification/auto-results.md`, rows 23-29):

| # | Expected after F-4 | N (2026-10-09-03) |
| --- | --- | --- |
| 23 | `dict23`: B and N-f4 both `changed: True lines 7 -> 7 bom: False crlf: True sha ef319c2140b1465e`. `dict_badbopo`: **N-f4 `changed: False lines 4 -> 4 bom: False crlf: True sha c432457361b0997a`**; B `changed: True lines 4 -> 2` (F-W11 baseline). `mgr items` lists `dict23` with `6` and `dict_badbopo` with `1` in both | `dict_badbopo` 4 -> 2 in N and B |
| 24 | unchanged: each `bom_*` imported with its count (`bom_excel` and `bom_notepad` `2`, `bom_lf` `1`), the editor rows, `after OK: BOM False` with CRLF bytes; `convert with bom_excel '甲乙' -> ... uses dict: True` (and the same for `bom_notepad`, `bom_lf`) | same |
| 25 | `25 locked:` `儲存失敗：[WinError 5] 存取被拒。: '....tmp' -> '...bom_lf.csv'`, editor still open, rows kept, `state: ('ORIG', ['bom_lf.csv', ...])` (no `.tmp`); `25 after unlock:` no message, `SAVED(CRLF,noBOM)` | same |
| 26 | `26 +r:` `儲存失敗：[Errno 13] Permission denied: '...bom_lf.csv'`, `ORIG`, no `.tmp`; after `-r` OK succeeds; `26 attrib` without `R` | same |
| 27 | `27 +h:` no message, `SAVED(CRLF,noBOM)`, `27 attrib` without `H` (M-8) | same |
| 28 | `28 failures: 0` | same |
| 29 | `29 deny W:` no message, `SAVED(CRLF,noBOM)`; `29 icacls now` without the deny ACE; restore succeeds; `final:` `SAVED(CRLF,noBOM)` | same |

- [ ] **Step 4: New item 35** (Git Bash). Optionally run it on B as well for the "before" column (`D:\dxtest\auto35-f4-B`, a new folder).

```bash
"$UIA" $H6/item35.py /d/dxtest/N-f4/DotExpress.exe /d/dxtest/auto35-f4 > /d/dxtest/auto35-f4.log 2>&1
"$UIA" $H6/item35.py /d/dxtest/B/DotExpress.exe /d/dxtest/auto35-f4-B > /d/dxtest/auto35-f4-B.log 2>&1
```

Expected (N-f4):

| Line | Expected after F-4 | B (before) |
| --- | --- | --- |
| `source sha256` | `c432457361b0997a2aa8441666a67c3cad4ff8220a42687aee4e35799bbc6eb4 lines: 4` | same |
| `import`, `imported identical`, `mgr` | no message; `True`; `[['dict_badbopo', '1']]` | same |
| `convert 1` | the converted text O1 (record it), no message | O1 |
| `35a rows` / `35a ok` | `[['臺北', '⠞⠺', 'Unicode 點字']]`; `([], False)` | same |
| `35a identical` | `True lines: 4 sha256: c4324573…6eb4 files: ['default.csv', 'dict_badbopo.csv']` | `False lines: 2` |
| `35a convert 2` | O1 again, `same as convert 1: True` | `False` |
| `35b add` | `[('錯誤', [..., '來源文字「肚子」已存在。', ...])]` | `[]` (the entry is added) |
| `35b rows` / `35b ok` / `35b identical` | `[['臺北', '⠞⠺', 'Unicode 點字']]`; `([], False)`; `True` | two rows; `False` |
| `35c rows after delete` / `35c ok` | `[]`; `([], False)` | one row (`肚子`) |
| `35c header and hidden rows` | `True 'text,braille,type\r\n肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n'`, files as above | `False` |
| `35c mgr` | `[['dict_badbopo', '0']]` | `[['dict_badbopo', '1']]` |
| `35d mgr` / `35d rows` / `35d unchanged` | `[['dict_badbopo', '0']]`; `[]`; `True` | |
| `close` | `exited` (both times) | same |

- [ ] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/auto-results.md` in the style of `2026-10-09-03-windows-verification/auto-results.md` and of F-3's `2026-10-09-05-f3-dep-atomic-write/auto-results.md` (zh-TW): the build (PyInstaller version, `Build complete!`, the two bundled modules, size, sha256), then one row per item (23, 24, 25, 26, 27, 28, 29, 35, and 35 on B if run) with ✔/△/✘ and the observed messages, listings and the conversion output O1. Any deviation from the tables above is reported to the orchestrator before the commit, not explained away; a rerun after a GUI timing problem is recorded with the first attempt's log name, as F-3 did.

```bash
cd /d/workspace/DotExpress-f4
git add docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/auto-results.md docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/auto/rerun.py docs/superpowers/history/2026-10-09-06-f4-keep-invalid-bopomofo-rows/auto/item35.py
git commit -q -m "docs: record the F-4 packaged-build GUI checks (F-4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
git rev-parse HEAD:client
```

Expected: no `status` output, and the Task 3 tree id (the commit touches no file under `client/`).

### Task 6: Merge main into the branch (only when the orchestrator asks; never push)

F-3 was merged into `main` as `b793704` (`merge: atomic .dep writes and safe renames (F-3)`) while this plan was written; on its own that `main` gives `Ran 1253`, `FAILED (errors=1, skipped=7)` (F-W6 only). F-4 touches no file that P2-5 or F-3 changes (`git diff --stat 4953772 b793704 -- client`: `documents/workspace.py`, `documents/workspace_service.py`, `gui.py` (the `_show_document_save_error` helper and logging), `shared/atomic_write.py`, `tests/case_insensitive_package_files.py`, `tests/test_atomic_write.py`, `tests/test_document_workspace.py`, `tests/test_gui_document_flows.py`, `tests/test_workspace_service.py`, `tests/windows_file_handles.py`; F-4: `dictionaries/` and four dictionary test modules; the docs live in different files and history folders), so the merge is clean. Only F-W6 remains failing. Case B is the expected one; case A stays for completeness (it was the state when the plan was started).

- [ ] **Step 1: See what `main` contains.** F-3 adds `client/tests/windows_file_handles.py`.

```bash
git -C $REPO cat-file -e main:client/tests/windows_file_handles.py 2>/dev/null && echo "main contains F-3" || echo "main is P2-5 only"
git -C $REPO merge-base --is-ancestor 4953772 main && echo "main contains 4953772"
```

Expected: `main contains 4953772` and one of the two first lines; follow Step 2 for "main is P2-5 only" (`main` still at `4953772`) and Step 3 for "main contains F-3". If `main` has moved on with other work, the expected `Ran` is `main`'s own count + 15, the final line `FAILED (errors=1, skipped=<main's skips>)`, and the merge tree id differs.

- [ ] **Step 2 (case A): `main` is still `4953772`.** The branch already contains it: nothing to merge, no merge commit.

```bash
git -C $REPO merge --no-ff main -m "merge: main into fix/f4-keep-invalid-bopomofo-rows (F-4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
git -C $REPO diff --stat main HEAD -- client | tail -1
```

Expected (the tree of Task 3):

```text
Already up to date.
a64e34d8dec7b1909f7fae5c8b9b4327d3d7f6b2
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1226 tests
FAILED (errors=1, skipped=5)
 6 files changed, 362 insertions(+), 37 deletions(-)
```

- [ ] **Step 3 (case B): `main` contains F-3** (`main` at `b793704`: `Ran 1253`, `FAILED (errors=1, skipped=7)` on its own). The expected tree id assumes `main` at `b793704`; if `main` moved on, only the tree id and the counts differ (`main`'s `Ran` + 15, `main`'s skips).

```bash
git -C $REPO merge -q --no-ff main -m "merge: main into fix/f4-keep-invalid-bopomofo-rows (F-4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO log --format=%s -1
git -C $REPO status --short
git -C $REPO rev-parse HEAD:client
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dictionary_management_dialog tests.test_atomic_write 2>&1 | $PY $T/tools/brief.py
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --stat main HEAD -- client | tail -1
```

Expected (1253 + 15; the 7 skips are `main`'s; the diff against `main` is exactly F-4's client changes):

```text
merge: main into fix/f4-keep-invalid-bopomofo-rows (F-4)
70cc470e9e87aa18a736743ae6ebabc9a52e567d
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1268 tests
FAILED (errors=1, skipped=7)
Ran 187 tests
OK (skipped=4)
source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
 6 files changed, 362 insertions(+), 37 deletions(-)
```
