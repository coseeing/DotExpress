# Atomic `.dep` Writes (F-3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the two priority-2 workspace defects. Every `.dep` write (Save before every document action and Close, Add, the default document, Import, Export as DEP) goes to a new temporary file in the same folder, is flushed to disk and installed with `os.replace`; on any failure the package is byte-identical to before (or still absent) and no temporary file is left. Every Rename, regular or case-only, goes through F-1's `move_document_package`, so a failure leaves exactly the old package and an unchanged list (P1-3 known defect 3). A package the user may not write is never replaced or removed: Save and Rename fail with `[Errno 13] Permission denied: '<package>'`. Save, Add and Rename report every `Exception` with the existing `Failed to save document: {error}` message, and Import reports it as an issue. No new user-facing string (msgids 353, same set), no `.po`/`.mo` or fixture change.

**Architecture:** Six commits. Task 1 pins what must not change (package bytes, leftover temporary files at startup, the read-only Save message) on today's code. Task 2 turns `shared/atomic_write.py` into one private core with a text and a bytes variant and a public `ensure_writable` (spec D1, D3). Task 3 writes packages through it and writes a move's staged file directly with `fsync` (D2, D4, D13). Task 4 adds the write check before a move (D7). Task 5 routes regular renames through the move (D5, D8) and flips the two `KNOWN BUG` tests and the F-1 guard. Task 6 widens the three frame handlers and the import loop to `Exception` (D9). Task 7 verifies, Task 8 builds the exe and runs the GUI checks, Task 9 merges `main` when asked. Every production task is red first.

**Tech Stack:** Python 3.13 standard library (`os.replace`, `os.fsync`, `os.access`, `zipfile`, `ctypes` `CreateFileW`/`SetFileAttributesW` in the Windows-only tests, `unittest`, `unittest.mock`). Windows 11, the main checkout's `client\.venv` (wxPython, PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-09-f3-dep-atomic-write-design.md` (+ `_zh-TW.md`), commit `b6d1c7d`, with Q1/Q2 decided and the section "Corrected after planning" added in the plan commit (both languages). Orchestrator decisions: **Q1 accept** (a `.dep` held open by another program in any share mode now blocks Save, and every action that saves first, until it is released); **Q2 refuse** (a read-only package cannot be renamed, either kind: `[Errno 13]`, nothing left on disk). The user may override both before the merge.

## Global Constraints

- Work only in the worktree `D:\workspace\DotExpress-f3`, branch `fix/f3-dep-atomic-write` (HEAD is the plan commit on top of `b6d1c7d`). Never switch branches, never push, never rewrite history. Do not change anything in `D:\workspace\DotExpress` (another task works there); reading it and using its `client\.venv` Python are fine. Merge `main` only in Task 9 and only when the orchestrator asks.
- Files that may change (12, nothing else): production `client/shared/atomic_write.py`, `client/documents/workspace.py`, `client/documents/workspace_service.py` (4 spaces), `client/gui.py` (**tabs**); tests `client/tests/test_atomic_write.py`, `client/tests/test_document_workspace.py`, `client/tests/test_workspace_service.py`, `client/tests/test_gui_document_flows.py`, `client/tests/case_insensitive_package_files.py`, new `client/tests/windows_file_handles.py` (all 4 spaces); in Task 8 the new history folder `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/` (scripts and results).
- Never touch `client/dictionary/` (user data; the worktree has none and no test creates it), `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (byte-identical), tracked `client/braille/` content, `client/locales/`, `client/tests/fixtures/`, `scripts/`, `vendor/`, the `include/liblouis` submodule pointer, the untracked `client2/`, `preprocessing/`, `testdata/` of the main checkout, or the committed scripts of `docs/superpowers/history/2026-10-09-03-windows-verification/`. Never run `py scripts\sync-nvda.py`. Task 0 copies git-ignored build products into the worktree; that is the only change outside the list above, and `git status` stays empty.
- The checkout uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply `File:` blocks with the Write tool (LF is fine; git normalizes it, the "LF will be replaced by CRLF" warning is expected) and `Edit:` blocks with the Edit tool: the first block is the exact old text, the second its replacement, each old text occurs once. Never edit with MSYS `sed -i` and never paste Python through a shell heredoc (the agent shell can alter backslashes). The `client/gui.py` blocks contain real tab characters; copy them, do not retype.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`, unchanged. msgid scan `source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c` before and after.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task.
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly.
- P2-5 is already on `main` but not on this branch: until Task 9 the known failure `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math` stays, and so does the F-W6 error `test_dictionary_name_prompt ... test_case_only_rename_still_renames` (out of scope; F-3 does not change it).
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`, random temporary-file suffixes as `<rnd>`). Commands print to stdout only; git's CRLF warnings go to stderr and are not part of the expected blocks.
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress-f3
  MAIN=/d/workspace/DotExpress
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f3impl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. Task 8 uses PowerShell.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning" in the plan commit.

1. **Baseline with the runtime copied.** The worktree lacks the git-ignored liblouis runtime, MathCAT and the submodule's `configure.ac`, so its baseline is `Ran 1138`, `FAILED (failures=1, errors=2, skipped=7)` (spec, Current State). Task 0 copies those build products from the main checkout (same submodule commit `2aa5f84b`; `louis_helper.py` is byte-identical to `vendor/nvda/liblouis/runtime/louis_helper.py`); the worktree then gives the main checkout's baseline, `Ran 1143`, `FAILED (failures=1, errors=1, skipped=5)`, and `git status` stays empty. All counts below assume the copy; without it every `Ran` is 5 lower and every final line has `errors=2, skipped=7`.
2. **37 new tests, not 34.** Three tests are added to the spec's list: `test_rename_of_a_package_held_open_by_another_program` (service, Windows-only, all four share modes: without delete sharing the rename fails with `[WinError 32]` and only the old package stays, before F-3 both stayed; with delete sharing it completes), `test_regular_rename_ignores_a_failure_to_remove_the_moved_aside_package` (service: the aside-file removal fault of a regular rename) and `test_startup_ignores_leftover_temporary_files` (GUI: D13 at the startup dialog, next to the loader test B11). A11 (helper) and B7 (Save) cover all four share modes (read, read+write, read+delete, read+write+delete) as subtests instead of read+write only. Windows-only tests: 8 (spec: 7). Expected: `Ran 1180`, `FAILED (failures=1, errors=1, skipped=7)` on this branch; `Ran 1248`, `FAILED (errors=1, skipped=7)` after merging `main` at `4953772` (P2-5). The spec's "1172 / 1177" are replaced.
3. **Six commits.** A test-only first commit holds the five characterization tests that pass on today's code (B6, B9, B10, B11 and the GUI startup test); then the spec's five steps, each red first. Subjects end with `(F-3)`.
4. **Test helper.** `client/tests/windows_file_handles.py` has, besides `hold_open` and the share constants, `SHARE_MODES` (the four modes), `make_read_only` (registers a clean-up that clears the attribute if the file still exists), `make_hidden` and `is_hidden`; `hold_open` returns a `release` function so a test can close the handle before it inspects the folder (a delete-pending file disappears only then).
5. **Import test.** The spec's import test fails `beta`; the plan fails `delta`, the second of `beta, delta`, so the red run shows the worse old behavior: `beta.dep` written but never added to the list.
6. **Stable red output.** B1, B2 and the service save-failure test check that the package still loads before they compare bytes, so the red run fails with `ValueError: Document package must contain one .txt and one .brl file.` instead of a byte dump that contains the zip's DOS timestamp.
7. **GUI flip injector.** The GUI module defines its own small `_FailingReplacePackageFiles(source_name=...)`: importing the service test module would make `unittest` collect its test classes twice.
8. **Acceptance criteria 4 and 8 compare with the merge base**, not `main`: `main` already contains P2-5. Criterion 4's "no new `_(`/`N_(` literal" applies to production code; the tests call `gui._()` with existing msgids.
9. **Windows verification.** The exe goes to `D:\dxtest\N-f3\DotExpress.exe` (orchestrator), not `D:\dxtest\F3\`. The 2026-10-09-03 scripts are not copied or edited: `rerun.py` runs items 18, 19 and 21 with the exe and work folder replaced in memory (items 19 and 21 start from a copy of item 18's folder), `item20b.py` already takes arguments, and items 30-33 are new scripts in `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/`; each run uses a new `D:\dxtest\auto<N>-f3` folder. Item 34 stays manual and optional.

## Dry Run

The plan was executed on scratch clones of the branch at `b6d1c7d` with a stand-in plan commit and a local `main` at `4953772` (`$SP/f3plan/r*`, never the worktree), by a harness that writes every `File:` block, applies every `Edit:` block exactly once, runs every `bash` block from `client/` and compares its stdout with the following `text` block. The final replay (`r6`, Tasks 0-7 and 9, from a fresh clone) matched every expected block, including all red runs, the per-commit tree ids and the mutation output. Final sha256 after Task 6 (`git show HEAD:<path>`): `client/shared/atomic_write.py` `6a0928f268e69df75d51194a3706a2b80c53841d1723949ee6b0216675726068`, `client/documents/workspace.py` `edbde7446ab8d62bf17f73298b78faee9bb4705cc89561e47a99f898ed40b3b8`, `client/documents/workspace_service.py` `ad90eee56a85d59ae0e4e2c291c6fbccdabd84122758421475dec75bcae4cd7c`, `client/gui.py` `af6be80c0f36049538e810e9e1175e3a090615a1e0b3a38bdea8b41d8163625e`, `client/tests/windows_file_handles.py` `fa73536de7aa85864287fb440e4f20ca1b60247de0116f4c9ae4aba0437e3257`. Task 8: the build command was run on a clone at Task 6 ("Build complete!" in 43 s, 48,733,081 bytes, the bundle lists the clone's own modules); the GUI scripts were only syntax-checked (and `rerun.py`'s replacement was checked on the three 2026-10-09-03 scripts), not run. POSIX-only tests (A9, B9 and the existing ones) were not run (Windows host).

## Review Focus

1. **A failed Save never damages the package.** Lone surrogate (text or braille), a full disk part-way, a refused `os.replace`, a read-only, hidden or held-open package: B1-B8, the service and GUI save tests. The package bytes, the listing (no `.tmp`) and the loadability are checked in each.
2. **A failed Rename leaves exactly one package.** The old package cannot be moved aside (held open without delete sharing, injected), the install fails, the package is read-only, the staged write raises: Task 5 and Task 6 tests, service and GUI. A failure to remove the aside file after a successful rename is ignored (the `.tmp` is never loaded).
3. **What changes for the user** (accepted in the spec): a held-open package now blocks Save in every share mode (Q1); a read-only package cannot be renamed (Q2); a hidden package's Save now succeeds and drops the attribute; non-`OSError` failures show the message instead of escaping (Close no longer fails silently).
4. **The text helper is unchanged in behavior**: its 15 tests are untouched and pass; the mutation check covers the shared core.

## File Map

- Task 1: new `client/tests/windows_file_handles.py`; `client/tests/test_document_workspace.py` (`AtomicSaveDocumentPackageTest`: B6, B9, B10, B11); `client/tests/test_gui_document_flows.py` (startup leftovers).
- Task 2: `client/tests/test_atomic_write.py` (`WriteBytesAtomicallyTest`, A1-A11); `client/shared/atomic_write.py` (rewritten).
- Task 3: `client/tests/test_document_workspace.py` (B1-B5, B7, B8, B14), `client/tests/test_workspace_service.py` (save failure); `client/documents/workspace.py` (`_normalized`, `_write_package`, `save_document_package`, `PackageFiles.write`, `temporary_path` docstring).
- Task 4: `client/tests/test_document_workspace.py` (B12, B13, `_FailingPackageFiles.ensure_writable`); `client/documents/workspace.py` (`PackageFiles.ensure_writable`, the check in `move_document_package`); `client/tests/case_insensitive_package_files.py`.
- Task 5: `client/tests/test_workspace_service.py` (injectors, two flips, four new tests), `client/tests/test_gui_document_flows.py` (flip, Windows read-only test); `client/documents/workspace_service.py` (`rename_document`, module docstring), `client/documents/workspace.py` (docstring).
- Task 6: `client/tests/test_workspace_service.py` (import), `client/tests/test_gui_document_flows.py` (four tests); `client/gui.py`, `client/documents/workspace_service.py` (`except Exception`).
- Task 8: new `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/` (`auto/` scripts, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`, runtime copied in Task 0)

| After task | tests added | `Ran` | final line | `HEAD:client` |
| --- | --- | --- | --- | --- |
| baseline (`b6d1c7d`) | - | 1143 | `FAILED (failures=1, errors=1, skipped=5)` | `a8aa670c68fd711cf0a19e78a82cc3fcb8e55879` |
| 1 pins | 5 (B6, B9, B10, B11, GUI startup) | 1148 | `FAILED (failures=1, errors=1, skipped=6)` | `cc21931999615f17c738c25a06cc82834f3415b1` |
| 2 helper | 11 (A1-A11) | 1159 | `FAILED (failures=1, errors=1, skipped=7)` | `d7fdb80a511064f0384ba65351c74a464d91939a` |
| 3 atomic save | 9 (B1-B5, B7, B8, B14, service save) | 1168 | `FAILED (failures=1, errors=1, skipped=7)` | `5a370f05ae88a244e1f340037fc69383382d715e` |
| 4 write check | 2 (B12, B13) | 1170 | `FAILED (failures=1, errors=1, skipped=7)` | `5fb5a653eda552958a048a272352992e370de5a1` |
| 5 one rename | 5 (4 service, 1 GUI); 3 flipped in place | 1175 | `FAILED (failures=1, errors=1, skipped=7)` | `18d5cecf917ddefb8b6e90bf0c34c477e1151f61` |
| 6 UI boundary | 5 (1 service, 4 GUI) | 1180 | `FAILED (failures=1, errors=1, skipped=7)` | `d79139ecb3f9e134dd46638489dbc54715be9d4f` |
| 9 merge `main` (`4953772`) | P2-5's 68 | 1248 | `FAILED (errors=1, skipped=7)` | `3cdcf63864b60020c30444faa0653545ddc55099` |

The failure is the P2-5 case (fixed on `main`), the error F-W6. The 7 skips on Windows are the 5 existing POSIX/case-sensitivity skips and A9, B9. The focused modules go from `Ran 264`, `OK (skipped=4)` to `Ran 301`, `OK (skipped=6)`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 with the Write tool: `brief.py` (output condenser), `msgid_scan.py` and `shuffle_harness.py` (the P2-5 tools, unchanged), `f3_mutants.py` (15 mutants of the code after Task 6, run on a copy of `client/`; the repository is never changed).

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

Expected (`status` and the diff print nothing; the merge base is the spec's starting point `d4a7aa1`):

```text
docs: plan for atomic .dep writes (F-3)
fix/f3-dep-atomic-write
d4a7aa1b76b4951230ac678036feeabca1209c9f
```

- [ ] **Step 2: Copy the generated liblouis runtime and MathCAT from the main checkout.** These files are git-ignored build products (`git -C $MAIN status --ignored --short client/braille client/mathcat` lists them as `!!`); the worktree has none, so its baseline differs (`Ran 1138`, `errors=2`, `skipped=7`). Copy only them, read-only from `$MAIN`; the tracked `client/braille/__init__.py`, `client/braille/tables/` and the submodule pointer are not touched. `include/liblouis` is an uninitialized submodule in the worktree (an empty folder); `test_built_wrapper_loads_bundled_dll` reads the expected version from its `configure.ac`, and the main checkout's submodule is at the same commit (`2aa5f84b`). The guards make the step safe to repeat.

```bash
test -e $REPO/client/braille/liblouis.dll || cp $MAIN/client/braille/liblouis.dll $REPO/client/braille/
test -e $REPO/client/braille/louis_helper.py || cp $MAIN/client/braille/louis_helper.py $REPO/client/braille/
test -e $REPO/client/braille/liblouis || cp -r $MAIN/client/braille/liblouis $REPO/client/braille/liblouis
test -e $REPO/client/mathcat || cp -r $MAIN/client/mathcat $REPO/client/mathcat
test -e $REPO/include/liblouis/configure.ac || cp $MAIN/include/liblouis/configure.ac $REPO/include/liblouis/configure.ac
git -C $MAIN submodule status include/liblouis | cut -c2-41
git -C $REPO rev-parse HEAD:include/liblouis
cmp $REPO/client/braille/louis_helper.py $REPO/vendor/nvda/liblouis/runtime/louis_helper.py && echo "louis_helper.py is the vendored file"
git -C $REPO status --short
git -C $REPO status --short --ignored client/braille client/mathcat | grep -v __pycache__
```

Expected (`status --short` prints nothing: the copies are ignored, the submodule pointer is unchanged):

```text
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
2aa5f84b14de17bcfe8317862d11f6bd7d640e55
louis_helper.py is the vendored file
!! client/braille/liblouis.dll
!! client/braille/liblouis/
!! client/braille/louis_helper.py
!! client/mathcat/
```

If any of these files is missing in `$MAIN`, skip the copy and use the worktree baseline instead: every `Ran` count below is then 5 lower, every final line has `errors=2, skipped=7` (the extra error is `test_liblouis_runtime` `setUpClass`), and nothing else changes.

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed) with the Write tool. `msgid_scan.py` and `shuffle_harness.py` are the P2-5 tools unchanged; `brief.py` also hides temporary folder names and random temporary-file suffixes; `f3_mutants.py` is used in Task 7.

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
RANDOM_TMP = re.compile(r"(\.[\w.]+?\.dep\.)[a-z0-9_]{8,16}(\.tmp)")
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

File: `$T/tools/f3_mutants.py`

````python
"""Run the F-3 tests against deliberately broken code (throwaway, not committed).

Usage: python f3_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one production file of the copy (one exact, unique replacement), runs
the six F-3 test modules there, prints which tests caught it and restores the file. The
repository is never changed. Matches the code after Task 6. Exit status 1 if a mutant is
not caught or its pattern is not found exactly once.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

HELPER = "shared/atomic_write.py"
WORKSPACE = "documents/workspace.py"
SERVICE = "documents/workspace_service.py"
STAGED_WRITE = """        with open(path, "wb") as stream:
            _write_package(stream, _normalized(document), include_pending_metadata=True)
            stream.flush()
            os.fsync(stream.fileno())
"""
CLEAN_UP = """    finally:
        if not installed and temporary_path is not None:
            with contextlib.suppress(OSError):
                temporary_path.unlink(missing_ok=True)
"""
CLEAN_UP_ON_OS_ERROR = """    except OSError:
        if temporary_path is not None:
            with contextlib.suppress(OSError):
                temporary_path.unlink(missing_ok=True)
        raise
"""
MOVE_CALL = """        move_document_package(
            self.package_path(source_name),
"""
OLD_REGULAR_RENAME = """        if source_name.casefold() != new_name.casefold():
            save_document_package(self.package_path(new_name), Document(new_name, source.text, source.braille))
            old_path = self.package_path(source_name)
            if old_path.exists():
                old_path.unlink()
            return self._controller.rename_document(source_name, new_name)
"""
MUTANTS = {
    # D2: the in-place write (the truncation defect reintroduced).
    "save-in-place": (
        WORKSPACE,
        """    write_bytes_atomically(
        package_path,
        lambda stream: _write_package(stream, document, include_pending_metadata=include_pending_metadata),
    )
""",
        "    _write_package(package_path, document, include_pending_metadata=include_pending_metadata)\n",
    ),
    # D1: the helper's guarantees.
    "no-fsync": (HELPER, "            os.fsync(stream.fileno())\n", ""),
    "no-flush": (HELPER, "            stream.flush()\n", ""),
    "clean-up-only-on-os-error": (HELPER, CLEAN_UP, CLEAN_UP_ON_OS_ERROR),
    "temporary-file-in-the-system-temp-folder": (
        HELPER,
        "candidate = destination.parent / f",
        'candidate = Path(os.environ.get("TEMP", "/tmp")) / f',
    ),
    # D3: the write check.
    "bytes-variant-without-write-check": (
        HELPER,
        '    ensure_writable(destination)\n    _write_atomically(destination, write, mode="wb")\n',
        '    _write_atomically(destination, write, mode="wb")\n',
    ),
    "write-check-on-a-missing-file": (
        HELPER,
        "    if os.path.exists(target) and not os.access(target, os.W_OK):\n",
        "    if not os.access(target, os.W_OK):\n",
    ),
    # D4: the staged file of a move.
    "staged-write-without-fsync": (WORKSPACE, "            os.fsync(stream.fileno())\n", ""),
    "staged-write-nested": (WORKSPACE, STAGED_WRITE, "        save_document_package(path, document)\n"),
    # D7: the write check before a move.
    "move-without-write-check": (WORKSPACE, "    files.ensure_writable(old_path)\n", ""),
    # D5: the regular rename back to write-then-unlink (defect 3 reintroduced).
    "regular-rename-write-then-unlink": (SERVICE, MOVE_CALL, OLD_REGULAR_RENAME + MOVE_CALL),
    # D9: the UI boundary and the import loop back to OSError.
    "save-feedback-catches-os-error-only": (
        "gui.py",
        "\t\t\tself._save_open_document()\n\t\texcept Exception as exc:\n",
        "\t\t\tself._save_open_document()\n\t\texcept OSError as exc:\n",
    ),
    "add-catches-os-error-only": (
        "gui.py",
        "\t\t\tself._workspace_service.create_document(document)\n\t\texcept Exception as exc:\n",
        "\t\t\tself._workspace_service.create_document(document)\n\t\texcept OSError as exc:\n",
    ),
    "rename-catches-os-error-only": (
        "gui.py",
        "\t\t\trenamed_document = self._workspace_service.rename_document(selected_document.name, new_name)\n\t\texcept Exception as exc:\n",
        "\t\t\trenamed_document = self._workspace_service.rename_document(selected_document.name, new_name)\n\t\texcept OSError as exc:\n",
    ),
    "import-catches-os-error-only": (
        SERVICE,
        "                save_document_package(package_path, document)\n            except Exception as exc:\n",
        "                save_document_package(package_path, document)\n            except OSError as exc:\n",
    ),
}
MODULES = (
    "tests.test_atomic_write",
    "tests.test_document_workspace",
    "tests.test_workspace_service",
    "tests.test_gui_document_flows",
    "tests.test_case_insensitive_package_files",
    "tests.test_document_controller",
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
                [sys.executable, "-m", "unittest", *MODULES],
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
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO rev-parse HEAD:client
for p in dictionary workspace config.json; do test -e $p && echo "EXISTS client/$p"; done; echo "app data checked"
```

Expected:

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1143 tests
FAILED (failures=1, errors=1, skipped=5)
Ran 264 tests
OK (skipped=4)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c
a8aa670c68fd711cf0a19e78a82cc3fcb8e55879
app data checked
```

### Task 1: Pin the package bytes and the leftover handling (characterization, green before the change)

These five tests describe behavior F-3 must keep. They pass on today's code, so this task has no red run; they are committed first so that Tasks 3-5 are checked against them. B6 and B10 are the spec's "green today" tests, B9 is POSIX-only (skipped here), B11 and the GUI test pin D13 at the two levels the user sees (loader and startup dialog).

- [ ] **Step 1: Add the Windows file helper** (4 spaces; not a test module, `discover` does not load it). The spec names `hold_open` and the two share constants; the plan adds the two missing share modes, the read-only and hidden helpers and a `release` function so a test can close the handle before it inspects the folder.

File: `client/tests/windows_file_handles.py`

````python
"""Windows file conditions for tests: real read-only and hidden files, open handles (F-3).

Only Windows-only tests call these helpers. ``hold_open`` opens a file the way another
program would, with ``CreateFileW(GENERIC_READ, share, OPEN_EXISTING)``; sharing checks
apply to every handle, including one held by the test's own process. Each helper
registers its undo with ``addCleanup``, so the undo runs before the clean-up of a
temporary directory registered earlier (clean-ups run last in, first out).
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import stat
import unittest
from pathlib import Path
from typing import Callable

SHARE_READ = 0x1
SHARE_WRITE = 0x2
SHARE_DELETE = 0x4
SHARE_READ_WRITE = SHARE_READ | SHARE_WRITE
# The share modes another program may hold a file with: a zip tool or a viewer shares
# reading only, an editor reading and writing, an antivirus scanner or the search
# indexer usually everything.
SHARE_MODES = (
    ("read", SHARE_READ),
    ("read+write", SHARE_READ_WRITE),
    ("read+delete", SHARE_READ | SHARE_DELETE),
    ("read+write+delete", SHARE_READ_WRITE | SHARE_DELETE),
)

_GENERIC_READ = 0x80000000
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_NORMAL = 0x80
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _kernel32():
    from ctypes import wintypes

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
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.SetFileAttributesW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD)
    kernel32.SetFileAttributesW.restype = wintypes.BOOL
    return kernel32


def hold_open(test_case: unittest.TestCase, path: Path | str, share: int) -> Callable[[], None]:
    """Open ``path`` for reading with ``share``; return a function that closes it.

    The clean-up closes it too if the test has not.
    """
    kernel32 = _kernel32()
    handle = kernel32.CreateFileW(str(path), _GENERIC_READ, share, None, _OPEN_EXISTING, _FILE_ATTRIBUTE_NORMAL, None)
    if handle is None or handle == _INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    closed = False

    def release() -> None:
        nonlocal closed
        if not closed:
            closed = True
            kernel32.CloseHandle(handle)

    test_case.addCleanup(release)
    return release


def make_read_only(test_case: unittest.TestCase, path: Path | str) -> None:
    """Set the read-only attribute of ``path``; the clean-up clears it if the file is still there."""
    target = Path(path)
    os.chmod(target, stat.S_IREAD)
    test_case.addCleanup(_make_writable, target)


def _make_writable(path: Path) -> None:
    with contextlib.suppress(FileNotFoundError):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


def make_hidden(path: Path | str) -> None:
    """Add the hidden attribute to ``path``, keeping its other attributes."""
    attributes = os.stat(path).st_file_attributes | stat.FILE_ATTRIBUTE_HIDDEN
    if not _kernel32().SetFileAttributesW(str(path), attributes):
        raise ctypes.WinError(ctypes.get_last_error())


def is_hidden(path: Path | str) -> bool:
    return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
````

- [ ] **Step 2: Add the four package pins** (`client/tests/test_document_workspace.py`, 4 spaces). A new class with `addCleanup` clean-ups (the existing `DocumentWorkspaceTest` removes its folder in `tearDown`, which runs before any `addCleanup`, so a read-only file or an open handle registered by a test would still be in place).

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
import json
import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
```

Edit: `client/tests/test_document_workspace.py`

```python
from shared import name_validation
```

```python
from shared import name_validation
from tests.windows_file_handles import make_read_only
```

Edit: `client/tests/test_document_workspace.py`

```python
        self.assertEqual(invalid_paths, [self.workspace_dir / "bad.dep"])


class _FailingPackageFiles:
```

```python
        self.assertEqual(invalid_paths, [self.workspace_dir / "bad.dep"])


class AtomicSaveDocumentPackageTest(unittest.TestCase):
    """``save_document_package`` never leaves a broken package and keeps the format (F-3)."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.workspace_dir = Path(temp_dir.name) / "workspace"
        self.path = self.workspace_dir / "alpha.dep"
        self.alpha = Document("alpha", "a", "1")

    def _listing(self) -> list[str]:
        return sorted(path.name for path in self.workspace_dir.iterdir())

    def _write_alpha(self) -> bytes:
        save_document_package(self.path, self.alpha)
        return self.path.read_bytes()

    def test_save_writes_the_same_bytes_as_the_in_place_writer(self) -> None:
        # The format does not change: for the same timestamp the bytes equal those of the
        # in-place writer before F-3, rebuilt here (ZipFile on the path, three writestr calls).
        self.workspace_dir.mkdir(parents=True)
        reference = self.workspace_dir / "reference.dep"
        for document in (Document("alpha", "a\n中文", "⠁⠂"), Document("alpha", "pending", None)):
            with self.subTest(braille=document.braille):
                with patch("time.time", return_value=1_760_000_000.0):
                    save_document_package(self.path, document)
                    with zipfile.ZipFile(reference, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                        archive.writestr("alpha.txt", document.text)
                        archive.writestr("alpha.brl", document.braille or "")
                        if document.braille is None:
                            archive.writestr("alpha.meta.json", json.dumps({"braille_pending": True}, ensure_ascii=False))

                self.assertEqual(self.path.read_bytes(), reference.read_bytes())

    def test_load_workspace_documents_ignores_leftover_temporary_files(self) -> None:
        # A crash or a failed clean-up can leave the temporary file of a save
        # (.<name>.dep.<16 hex>.tmp) or of a rename (.<name>.dep.<8 characters>.tmp).
        # "*.dep" never matches them: startup neither loads nor offers to delete them.
        self._write_alpha()
        for name in (".alpha.dep.0123456789abcdef.tmp", ".alpha.dep.k2j1abcd.tmp", ".beta.dep.x.tmp"):
            (self.workspace_dir / name).write_bytes(b"not a zip")

        self.assertEqual(load_workspace_documents(self.workspace_dir), ([self.alpha], []))

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_save_keeps_the_permission_bits_of_the_package(self) -> None:
        self._write_alpha()
        os.chmod(self.path, 0o640)

        save_document_package(self.path, Document("alpha", "edited", "1"))

        self.assertEqual(oct(stat.S_IMODE(os.stat(self.path).st_mode)), oct(0o640))
        self.assertEqual(load_document_package(self.path), Document("alpha", "edited", "1"))

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_save_of_a_read_only_package_gives_the_old_message(self) -> None:
        # The in-place open("w+b") failed with exactly this text; F-3 keeps it (D3).
        before = self._write_alpha()
        make_read_only(self, self.path)

        with self.assertRaises(PermissionError) as raised:
            save_document_package(self.path, Document("alpha", "edited", "1"))

        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self._listing(), ["alpha.dep"])


class _FailingPackageFiles:
```

- [ ] **Step 3: Add the startup pin** (`client/tests/test_gui_document_flows.py`, 4 spaces).

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._listing(), ["a-blocked.dep", "good.dep"])

    # --- save --------------------------------------------------------------
```

```python
        self.assertEqual(self._listing(), ["a-blocked.dep", "good.dep"])

    def test_startup_ignores_leftover_temporary_files(self) -> None:
        # F-3 (D13): temporary files a crash can leave next to the packages are neither
        # listed nor offered for deletion; they stay on disk untouched.
        self._write_packages(Document("good", "g", "1"))
        leftovers = [".good.dep.0123456789abcdef.tmp", ".good.dep.k2j1abcd.tmp"]
        for name in leftovers:
            (self.workspace / name).write_bytes(b"not a zip")
        self.delete_invalid = True
        frame = self._make_workspace_frame()

        frame._load_workspace_documents_at_startup()

        self.assertEqual(self.events, [("title", "good - DotExpress"), ("title", "good - DotExpress")])
        self.assertEqual(self._listing(), sorted(leftovers + ["good.dep"]))
        self.assertEqual(frame._document_controller.document_names, ["good"])

    # --- save --------------------------------------------------------------
```

- [ ] **Step 4: Run: all green on today's code.**

```bash
$PY -m unittest tests.test_document_workspace tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 199 tests
OK (skipped=2)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1148 tests
FAILED (failures=1, errors=1, skipped=6)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/windows_file_handles.py client/tests/test_document_workspace.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -m "test: pin the package bytes and leftover temporary files before the atomic save (F-3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
cc21931999615f17c738c25a06cc82834f3415b1
```

### Task 2: Share the atomic write core and add a bytes variant (D1, D3)

- [ ] **Step 1: Red: `WriteBytesAtomicallyTest`** (A1-A11; `client/tests/test_atomic_write.py`, 4 spaces). The 15 text-variant tests are not changed.

Edit: `client/tests/test_atomic_write.py`

```python
import shared.atomic_write as atomic_write
```

```python
import shared.atomic_write as atomic_write
from tests.windows_file_handles import SHARE_MODES, hold_open, make_read_only
```

Edit: `client/tests/test_atomic_write.py`

```python
        self.assertEqual(self.listing(), [".d.csv.aaaa.tmp", "d.csv"])


class ProductionCodeDoesNotSetTheUmaskTest(unittest.TestCase):
```

```python
        self.assertEqual(self.listing(), [".d.csv.aaaa.tmp", "d.csv"])


def _write_new_bytes(stream) -> None:
    stream.write(b"new bytes")


class WriteBytesAtomicallyTest(unittest.TestCase):
    """The binary variant that document packages use (F-3): the same steps and guarantee."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.directory = Path(self._tmpdir.name)
        self.path = self.directory / "d.dep"

    def listing(self) -> list[str]:
        return sorted(os.listdir(self.directory))

    def test_replaces_an_existing_file_with_the_written_bytes(self) -> None:
        self.path.write_bytes(b"old bytes")

        atomic_write.write_bytes_atomically(self.path, _write_new_bytes)

        self.assertEqual(self.path.read_bytes(), b"new bytes")
        self.assertEqual(self.listing(), ["d.dep"])

    def test_creates_a_file_that_does_not_exist(self) -> None:
        atomic_write.write_bytes_atomically(str(self.path), _write_new_bytes)

        self.assertEqual(self.path.read_bytes(), b"new bytes")
        self.assertEqual(self.listing(), ["d.dep"])

    def test_disk_full_while_writing_keeps_the_original_bytes_and_leaves_no_temporary_file(self) -> None:
        self.path.write_bytes(b"old bytes")

        def fill_the_disk(stream) -> None:
            stream.write(b"new")
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))

        with self.assertRaises(OSError) as raised:
            atomic_write.write_bytes_atomically(self.path, fill_the_disk)

        self.assertEqual(raised.exception.errno, errno.ENOSPC)
        self.assertEqual(self.path.read_bytes(), b"old bytes")
        self.assertEqual(self.listing(), ["d.dep"])

    def test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file(self) -> None:
        self.path.write_bytes(b"old bytes")

        with patch("os.replace", side_effect=PermissionError(13, "denied")) as replace:
            with self.assertRaises(PermissionError):
                atomic_write.write_bytes_atomically(self.path, _write_new_bytes)

        source, destination = replace.call_args.args
        self.assertEqual(Path(source).parent, self.directory)
        self.assertRegex(Path(source).name, r"^\.d\.dep\.[0-9a-f]{16}\.tmp$")
        self.assertEqual(Path(destination), self.path)
        self.assertEqual(self.path.read_bytes(), b"old bytes")
        self.assertEqual(self.listing(), ["d.dep"])

    def test_interrupt_leaves_no_temporary_file_and_propagates(self) -> None:
        self.path.write_bytes(b"old bytes")

        def interrupt(stream) -> None:
            stream.write(b"new")
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            atomic_write.write_bytes_atomically(self.path, interrupt)

        self.assertEqual(self.path.read_bytes(), b"old bytes")
        self.assertEqual(self.listing(), ["d.dep"])

    def test_data_is_flushed_to_disk_before_the_replace(self) -> None:
        calls = Mock()
        real_fsync = os.fsync
        sizes_at_fsync = []

        def fsync_recording_the_size(descriptor: int) -> None:
            # fsync only reaches what the stream has already handed to the descriptor.
            sizes_at_fsync.append(os.fstat(descriptor).st_size)
            real_fsync(descriptor)

        with patch("os.fsync", side_effect=fsync_recording_the_size) as fsync, patch(
            "os.replace", wraps=os.replace
        ) as replace:
            calls.attach_mock(fsync, "fsync")
            calls.attach_mock(replace, "replace")
            atomic_write.write_bytes_atomically(self.path, _write_new_bytes)

        self.assertEqual([name for name, _args, _kwargs in calls.mock_calls], ["fsync", "replace"])
        self.assertEqual(sizes_at_fsync, [len(b"new bytes")])
        self.assertEqual(self.path.read_bytes(), b"new bytes")

    def test_a_file_without_write_access_raises_permission_error_and_is_kept(self) -> None:
        self.path.write_bytes(b"old bytes")

        with patch("os.access", return_value=False) as access:
            with self.assertRaises(PermissionError) as raised:
                atomic_write.write_bytes_atomically(self.path, _write_new_bytes)

        access.assert_called_with(self.path, os.W_OK)
        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EACCES}] {os.strerror(errno.EACCES)}: {str(self.path)!r}",
        )
        self.assertEqual(self.path.read_bytes(), b"old bytes")
        self.assertEqual(self.listing(), ["d.dep"])

    def test_ensure_writable_accepts_missing_and_writable_files_and_refuses_others(self) -> None:
        with patch("os.access", return_value=False) as access:
            atomic_write.ensure_writable(self.path)
        access.assert_not_called()

        self.path.write_bytes(b"old bytes")
        atomic_write.ensure_writable(self.path)

        with patch("os.access", return_value=False) as access:
            with self.assertRaises(PermissionError) as raised:
                atomic_write.ensure_writable(str(self.path))
        access.assert_called_once_with(self.path, os.W_OK)
        self.assertEqual(raised.exception.errno, errno.EACCES)
        self.assertEqual(raised.exception.filename, str(self.path))
        self.assertEqual(self.listing(), ["d.dep"])

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_keeps_the_permission_bits_of_an_existing_file(self) -> None:
        self.path.write_bytes(b"old bytes")
        os.chmod(self.path, 0o640)

        atomic_write.write_bytes_atomically(self.path, _write_new_bytes)

        self.assertEqual(oct(stat.S_IMODE(os.stat(self.path).st_mode)), oct(0o640))
        self.assertEqual(self.path.read_bytes(), b"new bytes")

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_a_read_only_file_is_refused_with_the_in_place_verdict(self) -> None:
        self.path.write_bytes(b"old bytes")
        make_read_only(self, self.path)

        with self.assertRaises(PermissionError) as raised:
            atomic_write.write_bytes_atomically(self.path, _write_new_bytes)

        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), b"old bytes")
        self.assertEqual(self.listing(), ["d.dep"])

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_a_file_held_open_by_another_handle_is_kept(self) -> None:
        # os.replace refuses a destination that any handle has open, whatever it shares:
        # the file keeps its bytes and the temporary file goes (spec D10, Q1).
        self.path.write_bytes(b"old bytes")
        for label, share in SHARE_MODES:
            with self.subTest(share=label):
                release = hold_open(self, self.path, share)
                try:
                    with self.assertRaises(PermissionError) as raised:
                        atomic_write.write_bytes_atomically(self.path, _write_new_bytes)
                finally:
                    release()

                self.assertEqual(raised.exception.winerror, 5)
                self.assertEqual(self.path.read_bytes(), b"old bytes")
                self.assertEqual(self.listing(), ["d.dep"])


class ProductionCodeDoesNotSetTheUmaskTest(unittest.TestCase):
```

```bash
$PY -m unittest tests.test_atomic_write 2>&1 | $PY $T/tools/brief.py
```

Expected (each new test fails on the missing function; the four subtests of A11 are reported separately):

```text
ERROR: test_a_file_held_open_by_another_handle_is_kept (tests.test_atomic_write.WriteBytesAtomicallyTest.test_a_file_held_open_by_another_handle_is_kept) (share
AttributeError: module 'shared.atomic_write' has no attribute 'write_bytes_atomically'. Did you mean: 'write_text_atomically'?
ERROR: test_a_file_held_open_by_another_handle_is_kept (tests.test_atomic_write.WriteBytesAtomicallyTest.test_a_file_held_open_by_another_handle_is_kept) (share
ERROR: test_a_file_held_open_by_another_handle_is_kept (tests.test_atomic_write.WriteBytesAtomicallyTest.test_a_file_held_open_by_another_handle_is_kept) (share
ERROR: test_a_file_held_open_by_another_handle_is_kept (tests.test_atomic_write.WriteBytesAtomicallyTest.test_a_file_held_open_by_another_handle_is_kept) (share
ERROR: test_a_file_without_write_access_raises_permission_error_and_is_kept (tests.test_atomic_write.WriteBytesAtomicallyTest.test_a_file_without_write_access_r
ERROR: test_a_read_only_file_is_refused_with_the_in_place_verdict (tests.test_atomic_write.WriteBytesAtomicallyTest.test_a_read_only_file_is_refused_with_the_in
ERROR: test_creates_a_file_that_does_not_exist (tests.test_atomic_write.WriteBytesAtomicallyTest.test_creates_a_file_that_does_not_exist)
ERROR: test_data_is_flushed_to_disk_before_the_replace (tests.test_atomic_write.WriteBytesAtomicallyTest.test_data_is_flushed_to_disk_before_the_replace)
ERROR: test_disk_full_while_writing_keeps_the_original_bytes_and_leaves_no_temporary_file (tests.test_atomic_write.WriteBytesAtomicallyTest.test_disk_full_while
ERROR: test_ensure_writable_accepts_missing_and_writable_files_and_refuses_others (tests.test_atomic_write.WriteBytesAtomicallyTest.test_ensure_writable_accepts
AttributeError: module 'shared.atomic_write' has no attribute 'ensure_writable'
ERROR: test_interrupt_leaves_no_temporary_file_and_propagates (tests.test_atomic_write.WriteBytesAtomicallyTest.test_interrupt_leaves_no_temporary_file_and_prop
ERROR: test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file (tests.test_atomic_write.WriteBytesAtomicallyTest.test_replace_error_keeps_the_o
ERROR: test_replaces_an_existing_file_with_the_written_bytes (tests.test_atomic_write.WriteBytesAtomicallyTest.test_replaces_an_existing_file_with_the_written_b
Ran 26 tests
FAILED (errors=13, skipped=4)
```

- [ ] **Step 2: Rewrite the helper** (4 spaces). `ensure_writable` is today's step 0, public; `_open_temporary_file` and `_write_atomically` are today's name loop and body, with the `open` arguments passed through; `write_text_atomically` keeps its signature and behavior.

File: `client/shared/atomic_write.py`

````python
"""Replace a file without ever leaving it half-written.

``write_text_atomically`` and ``write_bytes_atomically`` write to a temporary file
``.<name>.<random>.tmp`` in the target's directory, flush it to disk and install it
with ``os.replace``. On return the target holds exactly what was written; on an
exception it is unchanged (same bytes, or still absent) and the temporary file is
removed.

Permissions follow a plain ``open(path, "w")``: an existing target the user may
not write raises ``PermissionError`` and is left alone (``ensure_writable``); a new
file gets the default mode for the umask (the kernel applies it); on POSIX a
replaced file's permission bits are kept.
"""

from __future__ import annotations

import contextlib
import errno
import os
import secrets
import stat
from pathlib import Path
from typing import IO, Any, BinaryIO, Callable, TextIO

_ATTEMPTS = 100
_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)


def ensure_writable(path: Path | str) -> None:
    """Raise ``PermissionError`` if ``path`` exists and the user may not write it.

    This is the verdict an in-place ``open(path, "w")`` gives; a rename would not ask.
    A missing ``path`` passes.
    """
    target = Path(path)
    if os.path.exists(target) and not os.access(target, os.W_OK):
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(target))


def _open_temporary_file(
    destination: Path,
    opener: Callable[[Path, int], int],
    **open_arguments: Any,
) -> IO:
    """Open a new ``.<name>.<random>.tmp`` next to ``destination``; never reuses a file."""
    for _attempt in range(_ATTEMPTS):
        candidate = destination.parent / f".{destination.name}.{secrets.token_hex(8)}.tmp"
        try:
            return open(candidate, opener=opener, **open_arguments)
        except FileExistsError:
            continue
    raise FileExistsError(errno.EEXIST, "No usable temporary file name found", str(destination.parent))


def _existing_mode(destination: Path) -> int | None:
    """The permission bits of ``destination``, or ``None`` if it does not exist."""
    try:
        return stat.S_IMODE(os.stat(destination).st_mode)
    except FileNotFoundError:
        return None


def _write_atomically(destination: Path, write: Callable[[Any], None], **open_arguments: Any) -> None:
    """Write ``destination`` through ``write(stream)`` on a new temporary file, then install it."""
    temporary_path: Path | None = None
    installed = False

    def create_new(candidate: Path, _flags: int) -> int:
        # Mode 0o666 lets the kernel apply the umask, as open(path, "w") would; the
        # path is recorded as soon as the file exists, so every failure removes it.
        nonlocal temporary_path
        descriptor = os.open(candidate, _CREATE_FLAGS, 0o666)
        temporary_path = Path(candidate)
        return descriptor

    try:
        with _open_temporary_file(destination, create_new, **open_arguments) as stream:
            write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "posix":
            mode = _existing_mode(destination)
            if mode is not None:
                os.chmod(temporary_path, mode)
        os.replace(temporary_path, destination)
        installed = True
    finally:
        if not installed and temporary_path is not None:
            with contextlib.suppress(OSError):
                temporary_path.unlink(missing_ok=True)


def write_text_atomically(
    path: Path | str,
    write: Callable[[TextIO], None],
    *,
    encoding: str = "utf-8",
    newline: str | None = "",
) -> None:
    """Write ``path`` through ``write(stream)``; on an error ``path`` is unchanged.

    The directory must exist. No temporary file is left unless removing it fails.
    """
    destination = Path(path)
    ensure_writable(destination)
    _write_atomically(destination, write, mode="w", encoding=encoding, newline=newline)


def write_bytes_atomically(path: Path | str, write: Callable[[BinaryIO], None]) -> None:
    """Write ``path`` through ``write(stream)`` on a binary stream; on an error ``path`` is unchanged.

    The same guarantee as ``write_text_atomically``. The directory must exist.
    """
    destination = Path(path)
    ensure_writable(destination)
    _write_atomically(destination, write, mode="wb")
````

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_atomic_write -v 2>&1 | grep -c "WriteBytesAtomicallyTest.* ok$"
$PY -m unittest tests.test_atomic_write 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (10 of the 11 new tests run here; the POSIX one is skipped):

```text
10
Ran 26 tests
OK (skipped=4)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1159 tests
FAILED (failures=1, errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/shared/atomic_write.py client/tests/test_atomic_write.py
git -C $REPO commit -q -m "refactor: share the atomic write core and add a bytes variant (F-3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
d7fdb80a511064f0384ba65351c74a464d91939a
```

### Task 3: Save document packages atomically (D2, D4, D13)

- [ ] **Step 1: Red: the save fault tests** (B1-B5, B7, B8 in `AtomicSaveDocumentPackageTest`, B14 in `MoveDocumentPackageTest`; 4 spaces).

Edit: `client/tests/test_document_workspace.py`

```python
import json
import os
```

```python
import errno
import json
import os
```

Edit: `client/tests/test_document_workspace.py`

```python
from tests.windows_file_handles import make_read_only
```

```python
from tests.windows_file_handles import SHARE_MODES, hold_open, is_hidden, make_hidden, make_read_only
```

Edit: `client/tests/test_document_workspace.py`

```python
        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self._listing(), ["alpha.dep"])


class _FailingPackageFiles:
```

```python
        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_failure_from_a_lone_surrogate_keeps_the_existing_package(self) -> None:
        # UTF-8 cannot encode a lone surrogate. The in-place save had already truncated
        # the package and left a zip without the failing member (invalid at the next start).
        before = self._write_alpha()
        broken = {"text": Document("alpha", "\ud800", "1"), "braille": Document("alpha", "a", "\ud800")}
        for field, document in broken.items():
            with self.subTest(field=field):
                with self.assertRaises(UnicodeEncodeError):
                    save_document_package(self.path, document)

                self.assertEqual(self._listing(), ["alpha.dep"])
                self.assertEqual(load_document_package(self.path), self.alpha)
                self.assertEqual(self.path.read_bytes(), before)

    def test_save_failure_while_writing_keeps_the_existing_package(self) -> None:
        # A full disk while the second member is written (simulated).
        before = self._write_alpha()
        real_writestr = zipfile.ZipFile.writestr
        written = []

        def writestr_until_the_disk_is_full(archive, name, data, *args, **kwargs):
            written.append(name)
            if len(written) == 2:
                raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
            return real_writestr(archive, name, data, *args, **kwargs)

        with patch.object(zipfile.ZipFile, "writestr", writestr_until_the_disk_is_full):
            with self.assertRaises(OSError) as raised:
                save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertEqual(raised.exception.errno, errno.ENOSPC)
        self.assertEqual(written, ["alpha.txt", "alpha.brl"])
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(load_document_package(self.path), self.alpha)
        self.assertEqual(self.path.read_bytes(), before)

    def test_save_install_failure_keeps_the_existing_package(self) -> None:
        before = self._write_alpha()

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "denied")):
            with self.assertRaises(PermissionError):
                save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_installs_a_temporary_file_from_the_same_folder(self) -> None:
        self._write_alpha()

        with patch("os.replace", wraps=os.replace) as replace:
            save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertEqual(replace.call_count, 1)
        source, destination = replace.call_args.args
        self.assertEqual(Path(source).parent, self.workspace_dir)
        self.assertRegex(Path(source).name, r"^\.alpha\.dep\.[0-9a-f]{16}\.tmp$")
        self.assertEqual(Path(destination), self.path)
        self.assertEqual(load_document_package(self.path), Document("alpha", "edited", "2"))
        self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_refuses_a_package_without_write_access(self) -> None:
        before = self._write_alpha()

        with patch("os.access", return_value=False):
            with self.assertRaises(PermissionError) as raised:
                save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EACCES}] {os.strerror(errno.EACCES)}: {str(self.path)!r}",
        )
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self._listing(), ["alpha.dep"])

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_save_of_a_package_held_open_keeps_it(self) -> None:
        # Another program reading the package. The in-place save failed with [Errno 13]
        # or rewrote the file under that program (share read+write); now the replace is
        # refused in every share mode and the package keeps its bytes (spec D12, Q1).
        before = self._write_alpha()
        for label, share in SHARE_MODES:
            with self.subTest(share=label):
                release = hold_open(self, self.path, share)
                try:
                    with self.assertRaises(PermissionError) as raised:
                        save_document_package(self.path, Document("alpha", "edited", "2"))
                finally:
                    release()

                self.assertEqual(raised.exception.winerror, 5)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self._listing(), ["alpha.dep"])

    @unittest.skipUnless(os.name == "nt", "Windows hidden attribute")
    def test_save_of_a_hidden_package_replaces_it_and_drops_the_attribute(self) -> None:
        # The in-place open (CREATE_ALWAYS) refused a hidden file with [Errno 13]; the
        # replaced package is a new file with default attributes (spec D11).
        self._write_alpha()
        make_hidden(self.path)

        save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertFalse(is_hidden(self.path))
        self.assertEqual(load_document_package(self.path), Document("alpha", "edited", "2"))
        self.assertEqual(self._listing(), ["alpha.dep"])


class _FailingPackageFiles:
```

Edit: `client/tests/test_document_workspace.py`

```python
        self.assertEqual(list(self.workspace_dir.glob("*.dep")), [])

if __name__ == "__main__":
```

```python
        self.assertEqual(list(self.workspace_dir.glob("*.dep")), [])

    def test_staged_package_is_written_directly_and_flushed_to_disk(self) -> None:
        # The staged file is already private and new: it is written in place (no second
        # temporary file inside the first) and synced before the move installs it (D4).
        files = workspace.PackageFiles()
        staged = files.temporary_path(self.workspace_dir, "alpha.dep")
        real_fsync = os.fsync
        sizes_at_fsync = []

        def fsync_recording_the_size(descriptor: int) -> None:
            sizes_at_fsync.append(os.fstat(descriptor).st_size)
            real_fsync(descriptor)

        with patch("os.fsync", side_effect=fsync_recording_the_size), patch("os.replace", wraps=os.replace) as replace:
            files.write(staged, Document("alpha", "a", None))

        replace.assert_not_called()
        self.assertEqual(sizes_at_fsync, [staged.stat().st_size])
        self.assertGreater(sizes_at_fsync[0], 0)
        self.assertEqual(self._listing(), [staged.name])
        with zipfile.ZipFile(staged) as archive:
            self.assertEqual(sorted(archive.namelist()), ["alpha.brl", "alpha.meta.json", "alpha.txt"])
            self.assertEqual(archive.read("alpha.txt"), b"a")


if __name__ == "__main__":
```

Edit: `client/tests/test_workspace_service.py`

```python
        self.assertEqual(self.controller.documents, [Document("alpha", "edited", "edited braille")])

    # --- create ------------------------------------------------------------
```

```python
        self.assertEqual(self.controller.documents, [Document("alpha", "edited", "edited braille")])

    def test_save_failure_keeps_the_package_and_updates_memory(self) -> None:
        # Memory is updated first (the documented contract); the package keeps its bytes.
        self._write(Document("alpha", "a", "1"))
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        service = self._service([Document("alpha", "a", "1")], open_name="alpha")

        with self.assertRaises(UnicodeEncodeError):
            service.save_open_document(text="\ud800", braille="1")

        self.assertEqual(self.controller.documents, [Document("alpha", "\ud800", "1")])
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    # --- create ------------------------------------------------------------
```

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service 2>&1 | $PY $T/tools/brief.py
```

Expected (B1 and B7 fail per subtest; B8 errors with the old `[Errno 13]`):

```text
ERROR: test_save_failure_from_a_lone_surrogate_keeps_the_existing_package (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_failure_from_a_
ValueError: Document package must contain one .txt and one .brl file.
ERROR: test_save_failure_from_a_lone_surrogate_keeps_the_existing_package (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_failure_from_a_
ERROR: test_save_failure_while_writing_keeps_the_existing_package (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_failure_while_writing_k
ERROR: test_save_of_a_hidden_package_replaces_it_and_drops_the_attribute (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_of_a_hidden_pack
PermissionError: [Errno 13] Permission denied: '<tmp>\\workspace\\alpha.dep'
ERROR: test_save_failure_keeps_the_package_and_updates_memory (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_save_failure_keeps_the_package_and
FAIL: test_save_install_failure_keeps_the_existing_package (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_install_failure_keeps_the_exis
AssertionError: PermissionError not raised
FAIL: test_save_installs_a_temporary_file_from_the_same_folder (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_installs_a_temporary_file_
AssertionError: 0 != 1
FAIL: test_save_of_a_package_held_open_keeps_it (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_of_a_package_held_open_keeps_it) (share='
AssertionError: None != 5
FAIL: test_save_of_a_package_held_open_keeps_it (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_of_a_package_held_open_keeps_it) (share='
FAIL: test_save_of_a_package_held_open_keeps_it (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_of_a_package_held_open_keeps_it) (share='
FAIL: test_save_of_a_package_held_open_keeps_it (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_of_a_package_held_open_keeps_it) (share='
FAIL: test_save_refuses_a_package_without_write_access (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_refuses_a_package_without_write_ac
FAIL: test_staged_package_is_written_directly_and_flushed_to_disk (tests.test_document_workspace.MoveDocumentPackageTest.test_staged_package_is_written_directly
AssertionError: Lists differ: [] != [348]
Ran 77 tests
FAILED (failures=8, errors=5, skipped=2)
```

- [ ] **Step 2: Write packages through the helper** (`client/documents/workspace.py`, 4 spaces).

Edit: `client/documents/workspace.py`

```python
import zipfile
from collections.abc import Callable

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
from shared.name_validation import normalize_base_name
```

```python
import zipfile
from collections.abc import Callable
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
from shared.atomic_write import write_bytes_atomically
from shared.name_validation import normalize_base_name
```

Edit: `client/documents/workspace.py`

```python
def save_document_package(
    path: Path | str,
    document: Document,
    *,
    include_pending_metadata: bool = True,
) -> Path:
    package_path = Path(path)
    normalized_name = normalize_document_name(document.name)
    document = Document(name=normalized_name, text=document.text, braille=document.braille)
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{document.name}{TXT_EXTENSION}", document.text)
        archive.writestr(f"{document.name}{BRL_EXTENSION}", document.braille or "")
        if document.braille is None and include_pending_metadata:
            metadata_name = f"{document.name}{PENDING_METADATA_SUFFIX}"
            archive.writestr(metadata_name, json.dumps({"braille_pending": True}, ensure_ascii=False))
    return package_path
```

```python
def _normalized(document: Document) -> Document:
    return Document(name=normalize_document_name(document.name), text=document.text, braille=document.braille)


def _write_package(stream: BinaryIO, document: Document, *, include_pending_metadata: bool) -> None:
    """Write the normalized ``document`` as a package archive to ``stream``, which stays open."""
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{document.name}{TXT_EXTENSION}", document.text)
        archive.writestr(f"{document.name}{BRL_EXTENSION}", document.braille or "")
        if document.braille is None and include_pending_metadata:
            metadata_name = f"{document.name}{PENDING_METADATA_SUFFIX}"
            archive.writestr(metadata_name, json.dumps({"braille_pending": True}, ensure_ascii=False))


def save_document_package(
    path: Path | str,
    document: Document,
    *,
    include_pending_metadata: bool = True,
) -> Path:
    """Write ``document`` as the package at ``path`` through a temporary file (F-3).

    On return the package holds ``document``; on an exception it is unchanged (or still
    absent) and no temporary file is left. A package the user may not write raises
    ``PermissionError`` and is left alone, as the old in-place write did.
    """
    package_path = Path(path)
    document = _normalized(document)
    package_path.parent.mkdir(parents=True, exist_ok=True)
    write_bytes_atomically(
        package_path,
        lambda stream: _write_package(stream, document, include_pending_metadata=include_pending_metadata),
    )
    return package_path
```

Edit: `client/documents/workspace.py`

```python
    def write(self, path: Path, document: Document) -> None:
        save_document_package(path, document)
```

```python
    def write(self, path: Path, document: Document) -> None:
        """Write the package into the new private file ``path`` and flush it to disk."""
        with open(path, "wb") as stream:
            _write_package(stream, _normalized(document), include_pending_metadata=True)
            stream.flush()
            os.fsync(stream.fileno())
```

Edit: `client/documents/workspace.py`

```python
        """Create a new empty hidden file ``.<name>.<random>.tmp`` in ``directory`` (created if missing)."""
```

```python
        """Create a new empty file ``.<name>.<random>.tmp`` in ``directory`` (created if missing).

        The leading dot does not hide it on Windows; ``*.dep`` never matches it, so the
        workspace never loads it as a package.
        """
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_case_insensitive_package_files 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 81 tests
OK (skipped=2)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1168 tests
FAILED (failures=1, errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/documents/workspace.py client/tests/test_document_workspace.py client/tests/test_workspace_service.py
git -C $REPO commit -q -m "fix: save document packages atomically (F-3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
5a370f05ae88a244e1f340037fc69383382d715e
```

### Task 4: Refuse renaming a package the user may not write (D7, Q2 = refuse)

- [ ] **Step 1: Red: B12 and B13** (`MoveDocumentPackageTest`, 4 spaces). `_FailingPackageFiles` delegates the new seam first, so the existing move tests keep working once the move calls it.

Edit: `client/tests/test_document_workspace.py`

```python
    def exists(self, path) -> bool:
        return self._files.exists(path)
```

```python
    def ensure_writable(self, path) -> None:
        self._check("ensure_writable", path)
        self._files.ensure_writable(path)

    def exists(self, path) -> bool:
        return self._files.exists(path)
```

Edit: `client/tests/test_document_workspace.py`

```python
    def test_temporary_path_creates_the_directory_and_is_not_a_package(self) -> None:
```

```python
    def test_unwritable_old_package_is_refused_before_anything_changes(self) -> None:
        before = self._write_alpha()

        with patch("os.access", return_value=False):
            with self.assertRaises(PermissionError) as raised:
                self._move("Alpha", Document("gamma", "a", "1"))

        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EACCES}] {os.strerror(errno.EACCES)}: {str(self._path('Alpha'))!r}",
        )
        self.assertEqual(self._listing(), ["Alpha.dep"])
        self.assertEqual(self._path("Alpha").read_bytes(), before)

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_read_only_old_package_is_refused_and_leaves_no_temporary_file(self) -> None:
        # Without the check, moving a read-only package aside succeeds (it needs only
        # delete access) and the aside file cannot be removed: a read-only .tmp stays
        # (F-1 note; spec D7, Q2). Case-only and regular renames are both refused.
        root = self.workspace_dir
        for new_name in ("alpha", "gamma"):
            with self.subTest(new_name=new_name):
                self.workspace_dir = root / new_name
                before = self._write_alpha()
                make_read_only(self, self._path("Alpha"))

                with self.assertRaises(PermissionError) as raised:
                    self._move("Alpha", Document(new_name, "a", "1"))

                self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self._path('Alpha'))!r}")
                self.assertEqual(self._listing(), ["Alpha.dep"])
                self.assertEqual(self._path("Alpha").read_bytes(), before)

    def test_temporary_path_creates_the_directory_and_is_not_a_package(self) -> None:
```

```bash
$PY -m unittest tests.test_document_workspace 2>&1 | $PY $T/tools/brief.py
```

Expected (before the check the read-only package is moved: `alpha.dep` or `gamma.dep` plus the read-only aside file the move could not remove):

```text
FAIL: test_read_only_old_package_is_refused_and_leaves_no_temporary_file (tests.test_document_workspace.MoveDocumentPackageTest.test_read_only_old_package_is_re
AssertionError: PermissionError not raised
FAIL: test_read_only_old_package_is_refused_and_leaves_no_temporary_file (tests.test_document_workspace.MoveDocumentPackageTest.test_read_only_old_package_is_re
FAIL: test_unwritable_old_package_is_refused_before_anything_changes (tests.test_document_workspace.MoveDocumentPackageTest.test_unwritable_old_package_is_refus
Ran 48 tests
FAILED (failures=3, skipped=2)
```

- [ ] **Step 2: The write check before the move** (`client/documents/workspace.py`, `client/tests/case_insensitive_package_files.py`; 4 spaces). The model resolves the path first, like its other operations.

Edit: `client/documents/workspace.py`

```python
from shared.atomic_write import write_bytes_atomically
```

```python
from shared.atomic_write import ensure_writable, write_bytes_atomically
```

Edit: `client/documents/workspace.py`

```python
    """The file operations ``move_document_package`` uses; tests pass a model or a fault injector."""

    def exists(self, path: Path) -> bool:
```

```python
    """The file operations ``move_document_package`` uses; tests pass a model or a fault injector."""

    def ensure_writable(self, path: Path) -> None:
        """Raise ``PermissionError`` if the package at ``path`` exists and the user may not write it."""
        ensure_writable(path)

    def exists(self, path: Path) -> bool:
```

Edit: `client/documents/workspace.py`

```python
    Failing to remove the moved-aside old package after the install is ignored; that
    leftover ``.tmp`` file is never loaded as a package.
    """
    old_path = Path(old_path)
    new_path = Path(new_path)
    staged_path = files.temporary_path(new_path.parent, new_path.name)
```

```python
    Failing to remove the moved-aside old package after the install is ignored; that
    leftover ``.tmp`` file is never loaded as a package.

    An old package the user may not write (a read-only file) raises ``PermissionError``
    before anything is created or moved, as saving it does (F-3).
    """
    old_path = Path(old_path)
    new_path = Path(new_path)
    files.ensure_writable(old_path)
    staged_path = files.temporary_path(new_path.parent, new_path.name)
```

Edit: `client/tests/case_insensitive_package_files.py`

```python
    def exists(self, path: Path) -> bool:
        return self.resolve(path).exists()
```

```python
    def ensure_writable(self, path: Path) -> None:
        super().ensure_writable(self.resolve(path))

    def exists(self, path: Path) -> bool:
        return self.resolve(path).exists()
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_case_insensitive_package_files tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 244 tests
OK (skipped=2)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1170 tests
FAILED (failures=1, errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/documents/workspace.py client/tests/case_insensitive_package_files.py client/tests/test_document_workspace.py
git -C $REPO commit -q -m "fix: refuse renaming a package the user may not write (F-3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
5fb5a653eda552958a048a272352992e370de5a1
```

### Task 5: Route every rename through `move_document_package` (D5, D8; fixes P1-3 defect 3)

- [ ] **Step 1: Red: the service tests** (`client/tests/test_workspace_service.py`, 4 spaces). The fault injector now raises `PermissionError` naming both paths (D8), the KNOWN BUG test and the F-1 guard are flipped, `_UnusablePackageFiles` goes, four tests are new (one Windows-only), and the blocked-write test also checks the listing.

Edit: `client/tests/test_workspace_service.py`

```python
import ast
import tempfile
import unittest
import zipfile
from pathlib import Path

from documents.controller import DocumentController
from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
```

```python
import ast
import errno
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from documents.controller import DocumentController
from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.windows_file_handles import SHARE_DELETE, SHARE_MODES, hold_open
```

Edit: `client/tests/test_workspace_service.py`

```python
class _FailingInstallPackageFiles(PackageFiles):
    """The real file operations, except that replacing onto a file named ``name`` raises ``OSError``.

    The name is compared as a string: ``Path`` equality ignores case on Windows.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def replace(self, source: Path, destination: Path) -> None:
        if Path(destination).name == self.name:
            raise OSError("injected install failure")
        super().replace(source, destination)
```

```python
class _FailingReplacePackageFiles(PackageFiles):
    """The real file operations, except that one ``replace`` raises ``PermissionError``.

    It fails when the source is named ``source_name`` (moving the old package aside) or
    the destination is named ``destination_name`` (installing the new package). Names
    are compared as strings: ``Path`` equality ignores case on Windows. The error names
    both paths, as a failed rename does (spec D8).
    """

    def __init__(self, *, source_name: str | None = None, destination_name: str | None = None) -> None:
        self.source_name = source_name
        self.destination_name = destination_name

    def replace(self, source: Path, destination: Path) -> None:
        if Path(source).name == self.source_name or Path(destination).name == self.destination_name:
            raise PermissionError(errno.EACCES, "injected", str(source), None, str(destination))
        super().replace(source, destination)


class _FailingRemovePackageFiles(PackageFiles):
    """The real file operations, except that ``remove`` raises ``PermissionError``."""

    def remove(self, path: Path) -> None:
        raise PermissionError(errno.EACCES, "injected", str(path))


class _RecordingPackageFiles(PackageFiles):
    """The real file operations, recording the source and destination name of every ``replace``."""

    def __init__(self) -> None:
        self.replaced: list[tuple[str, str]] = []

    def replace(self, source: Path, destination: Path) -> None:
        super().replace(source, destination)
        self.replaced.append((Path(source).name, Path(destination).name))
```

Edit: `client/tests/test_workspace_service.py`

```python
class _UnusablePackageFiles:
    """Any use fails the test: a regular rename must not go through ``package_files``."""

    def _fail(self, *_args) -> None:
        raise AssertionError("a regular rename used package_files")

    exists = write = replace = remove = copy_permissions = temporary_path = _fail


class DocumentWorkspaceServiceTest(unittest.TestCase):
```

```python
class DocumentWorkspaceServiceTest(unittest.TestCase):
```

Edit: `client/tests/test_workspace_service.py`

```python
        with self.assertRaises(OSError):
            service.rename_document("alpha", "gamma")

        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual(self._state(), before)

    def test_rename_unlink_failure_propagates_and_leaves_both_packages(self) -> None:
        # KNOWN BUG (P1-3 spec, known defect 3), pinned as it is today, NOT desired
        # behavior: the new package stays on disk next to the old one while the
        # controller keeps only the old name. A later fix task flips this.
        self._block("alpha")
        service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        before = self._state()

        with self.assertRaises(OSError):
            service.rename_document("alpha", "gamma")

        self.assertEqual(self._listing(), ["alpha.dep", "gamma.dep"])
        self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))
        self.assertEqual(self._state(), before)
```

```python
        with self.assertRaises(OSError):
            service.rename_document("alpha", "gamma")

        # gamma.dep is the blocking folder; the staged package and the aside file are gone.
        self.assertEqual(self._listing(), ["alpha.dep", "gamma.dep"])
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual(self._state(), before)

    def test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state(self) -> None:
        # Was the KNOWN BUG test of P1-3 known defect 3 (the new package was written next
        # to the old one, the old one could not be removed, and both stayed on disk),
        # fixed by F-3: the old package is moved aside before the new one is installed.
        self._write(Document("alpha", "a", "1"))
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        service = self._service(
            [Document("alpha", "a", "1")],
            package_files=_FailingReplacePackageFiles(source_name="alpha.dep"),
            open_name="alpha",
            selected_name="alpha",
        )
        before = self._state()

        with self.assertRaises(PermissionError) as raised:
            service.rename_document("alpha", "gamma")

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertIn("alpha.dep", str(raised.exception))
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(), before)

    def test_regular_rename_install_failure_puts_the_old_package_back(self) -> None:
        self._write(Document("alpha", "a", "1"))
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        service = self._service(
            [Document("alpha", "a", "1")],
            package_files=_FailingReplacePackageFiles(destination_name="gamma.dep"),
            open_name="alpha",
            selected_name="alpha",
        )
        before = self._state()

        with self.assertRaises(PermissionError):
            service.rename_document("alpha", "gamma")

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(), before)

    def test_rename_of_an_unwritable_package_is_refused(self) -> None:
        self._write(Document("alpha", "a", "1"))
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        before = self._state()

        with patch("os.access", return_value=False):
            with self.assertRaises(PermissionError) as raised:
                service.rename_document("alpha", "gamma")

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EACCES}] {os.strerror(errno.EACCES)}: {str(self.workspace / 'alpha.dep')!r}",
        )
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._state(), before)

    def test_regular_rename_ignores_a_failure_to_remove_the_moved_aside_package(self) -> None:
        # The rename is complete once the new package is installed; an aside file that
        # cannot be removed stays as a .tmp the workspace never loads (F-1 behavior).
        self._write(Document("alpha", "a", "1"))
        service = self._service(
            [Document("alpha", "a", "1")],
            package_files=_FailingRemovePackageFiles(),
            open_name="alpha",
            selected_name="alpha",
        )

        self.assertEqual(service.rename_document("alpha", "gamma"), Document("gamma", "a", "1"))

        listing = self._listing()
        self.assertEqual(len(listing), 2, listing)
        self.assertRegex(listing[0], r"^\.alpha\.dep\..+\.tmp$")
        self.assertEqual(listing[1], "gamma.dep")
        self.assertEqual(self.controller.document_names, ["gamma"])
        reloaded = DocumentController()
        self.assertEqual(DocumentWorkspaceService(reloaded, self.workspace).load_documents(), [])
        self.assertEqual(reloaded.documents, [Document("gamma", "a", "1")])

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_rename_of_a_package_held_open_by_another_program(self) -> None:
        # Moving the package aside needs delete sharing. Without it (a zip tool, an
        # editor) the rename fails and exactly the old package stays; before F-3 the new
        # package was left next to it. With it (an antivirus scanner) the rename completes.
        for label, share in SHARE_MODES:
            with self.subTest(share=label):
                self.workspace = self.root / label.replace("+", "-")
                self._write(Document("alpha", "a", "1"))
                alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
                service = self._service([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
                before = self._state()
                release = hold_open(self, self.workspace / "alpha.dep", share)
                try:
                    if share & SHARE_DELETE:
                        service.rename_document("alpha", "gamma")
                    else:
                        with self.assertRaises(PermissionError) as raised:
                            service.rename_document("alpha", "gamma")
                finally:
                    release()

                if share & SHARE_DELETE:
                    self.assertEqual(self._listing(), ["gamma.dep"])
                    self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))
                    self.assertEqual(self.controller.document_names, ["gamma"])
                else:
                    self.assertEqual(self._listing(), ["alpha.dep"])
                    self.assertEqual(raised.exception.winerror, 32)
                    self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
                    self.assertEqual(self._state(), before)
```

Edit: `client/tests/test_workspace_service.py`

```python
        service = self._case_only_service(_FailingInstallPackageFiles("alpha.dep"))
```

```python
        service = self._case_only_service(_FailingReplacePackageFiles(destination_name="alpha.dep"))
```

Edit: `client/tests/test_workspace_service.py`

```python
    def test_regular_rename_does_not_use_package_files(self) -> None:
        # F-1 (D6): only case-only renames take the new path; regular renames keep
        # today's write-then-unlink sequence (known defect 3 stays pinned above).
        self._write(Document("alpha", "a", "1"))
        service = self._service([Document("alpha", "a", "1")], package_files=_UnusablePackageFiles())

        self.assertEqual(service.rename_document("alpha", "gamma"), Document("gamma", "a", "1"))

        self.assertEqual(self._listing(), ["gamma.dep"])
        self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))
```

```python
    def test_regular_rename_moves_the_old_package_aside_before_installing(self) -> None:
        # F-3 (D5): replaces the F-1 (D6) guard that kept regular renames on the old
        # write-then-unlink sequence. The old package leaves its name before the new one
        # takes its own, so nothing is removed under a name that can alias the new one.
        self._write(Document("alpha", "a", "1"))
        files = _RecordingPackageFiles()
        service = self._service([Document("alpha", "a", "1")], package_files=files)

        self.assertEqual(service.rename_document("alpha", "gamma"), Document("gamma", "a", "1"))

        self.assertEqual(len(files.replaced), 2, files.replaced)
        (moved, aside), (staged, installed) = files.replaced
        self.assertEqual(moved, "alpha.dep")
        self.assertRegex(aside, r"^\.alpha\.dep\..+\.tmp$")
        self.assertRegex(staged, r"^\.gamma\.dep\..+\.tmp$")
        self.assertEqual(installed, "gamma.dep")
        self.assertEqual(self._listing(), ["gamma.dep"])
        self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))
```

- [ ] **Step 2: Red: the GUI tests** (`client/tests/test_gui_document_flows.py`, 4 spaces). The KNOWN BUG test is flipped (the injector is a small local class: importing it from another test module would make `unittest` collect that module's test classes twice); the Windows read-only test is new.

Edit: `client/tests/test_gui_document_flows.py`

```python
from __future__ import annotations

import importlib
```

```python
from __future__ import annotations

import errno
import importlib
```

Edit: `client/tests/test_gui_document_flows.py`

```python
from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
```

```python
from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
from tests.windows_file_handles import make_read_only
```

Edit: `client/tests/test_gui_document_flows.py`

```python
from documents.workspace import BatchIssue, Document, load_document_package, save_document_package
```

```python
from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
```

Edit: `client/tests/test_gui_document_flows.py`

```python
class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
```

```python
class _FailingReplacePackageFiles(PackageFiles):
    """The real file operations, except that moving the file named ``source_name`` raises."""

    def __init__(self, *, source_name: str) -> None:
        self.source_name = source_name

    def replace(self, source: Path, destination: Path) -> None:
        if Path(source).name == self.source_name:
            raise PermissionError(errno.EACCES, "injected", str(source), None, str(destination))
        super().replace(source, destination)


class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
```

Edit: `client/tests/test_gui_document_flows.py`

```python
    def test_rename_unlink_failure_leaves_both_packages_and_state(self) -> None:
        # KNOWN BUG (P1-3 spec, known defect 3), pinned as it is today, NOT desired
        # behavior: the new package is written, the old unlink fails, and both stay
        # on disk while memory keeps only the old name. A later fix task flips this.
        alpha = Document("alpha", "a", "1")
        beta = Document("beta", "b", "2")
        self._write_packages(alpha)
        self._block("beta")
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
        before = self._state(frame)
        self.names = ["gamma"]

        frame.on_rename_document(None)

        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep", "gamma.dep"])
        self.assertEqual(self._package("gamma"), Document("gamma", "b", "2"))
        self.assertEqual(self._state(frame), before)
```

```python
    def test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state(self) -> None:
        # Was the KNOWN BUG test of P1-3 known defect 3 (the new package was written, the
        # old one could not be removed, and both stayed on disk while memory kept only
        # the old name), fixed by F-3: the old package is moved aside before the new one
        # is installed, so a failure there leaves only the old package.
        alpha = Document("alpha", "a", "1")
        beta = Document("beta", "b", "2")
        self._write_packages(alpha, beta)
        beta_bytes = (self.workspace / "beta.dep").read_bytes()
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
        frame._workspace_service = DocumentWorkspaceService(
            frame._document_controller,
            self.workspace,
            package_files=_FailingReplacePackageFiles(source_name="beta.dep"),
        )
        before = self._state(frame)
        self.names = ["gamma"]

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[0], ("DocumentNameDialog", gui._("Rename Document"), "beta"))
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
        self.assertEqual((self.workspace / "beta.dep").read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_rename_of_a_read_only_package_is_refused_with_the_save_message(self) -> None:
        # F-3 (D7, Q2): the same [Errno 13] text Save gives; before F-3 a regular rename
        # failed with [WinError 5] after writing gamma.dep, so both packages stayed.
        alpha = Document("alpha", "a", "1")
        beta = Document("beta", "b", "2")
        self._write_packages(alpha, beta)
        beta_path = self.workspace / "beta.dep"
        beta_bytes = beta_path.read_bytes()
        make_read_only(self, beta_path)
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
        before = self._state(frame)
        self.names = ["gamma"]

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
        self.assertIn(f"[Errno 13] Permission denied: {str(beta_path)!r}", self.events[1][1])
        self.assertEqual(beta_path.read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)
```

```bash
$PY -m unittest tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (the regular rename still writes `gamma.dep` and unlinks the old package, ignoring `package_files`; the share-delete subtests and the case-only tests already pass):

```text
FAIL: test_regular_rename_ignores_a_failure_to_remove_the_moved_aside_package (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_regular_rename_ign
AssertionError: 1 != 2 : ['gamma.dep']
FAIL: test_regular_rename_install_failure_puts_the_old_package_back (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_regular_rename_install_failu
AssertionError: PermissionError not raised
FAIL: test_regular_rename_moves_the_old_package_aside_before_installing (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_regular_rename_moves_the
AssertionError: 0 != 2 : []
FAIL: test_rename_of_a_package_held_open_by_another_program (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_rename_of_a_package_held_open_by_ano
AssertionError: Lists differ: ['alpha.dep', 'gamma.dep'] != ['alpha.dep']
FAIL: test_rename_of_a_package_held_open_by_another_program (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_rename_of_a_package_held_open_by_ano
FAIL: test_rename_of_an_unwritable_package_is_refused (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_rename_of_an_unwritable_package_is_refused
FAIL: test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_rename_that
FAIL: test_rename_of_a_read_only_package_is_refused_with_the_save_message (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_rename_
AssertionError: Lists differ: ['alpha.dep', 'beta.dep', 'gamma.dep'] != ['alpha.dep', 'beta.dep']
FAIL: test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.t
AssertionError: Lists differ: ['alpha.dep', 'gamma.dep'] != ['alpha.dep', 'beta.dep']
Ran 197 tests
FAILED (failures=9)
```

- [ ] **Step 3: One rename sequence** (`client/documents/workspace_service.py` and the `move_document_package` docstring; 4 spaces).

Edit: `client/documents/workspace_service.py`

```python
"""Workspace disk operations of the document flows, with the matching controller update.

No wx: the frame keeps the dialogs, confirmations, error messages and list refreshes.
The order of memory and disk effects is part of the contract: save updates memory
before writing, rename writes the new package before deleting the old one, and
Delete All reports a failure before it reloads the workspace. A case-only rename
(``Alpha`` to ``alpha``) instead stages the new package and moves the old one aside
before installing it (``move_document_package``), because on a case-insensitive file
system both names are the same file.
"""
```

```python
"""Workspace disk operations of the document flows, with the matching controller update.

No wx: the frame keeps the dialogs, confirmations, error messages and list refreshes.
The order of memory and disk effects is part of the contract: save updates memory
before writing, and Delete All reports a failure before it reloads the workspace.
A package is always written through a temporary file in the workspace, so a failed
save leaves it as it was. Every rename stages the new package and moves the old one
aside before installing it (``move_document_package``): a failure leaves exactly the
old package, and a case-only rename (``Alpha`` to ``alpha``) is safe on a
case-insensitive file system, where both names are the same file.
"""
```

Edit: `client/documents/workspace_service.py`

```python
        if source is None:
            return None
        if source_name.casefold() == new_name.casefold():
            move_document_package(
                self.package_path(source_name),
                self.package_path(new_name),
                Document(new_name, source.text, source.braille),
                files=self._package_files,
            )
            return self._controller.rename_document(source_name, new_name)
        save_document_package(self.package_path(new_name), Document(new_name, source.text, source.braille))
        old_path = self.package_path(source_name)
        if old_path.exists():
            old_path.unlink()
        return self._controller.rename_document(source_name, new_name)
```

```python
        if source is None:
            return None
        move_document_package(
            self.package_path(source_name),
            self.package_path(new_name),
            Document(new_name, source.text, source.braille),
            files=self._package_files,
        )
        return self._controller.rename_document(source_name, new_name)
```

Edit: `client/documents/workspace.py`

```python
    """Write ``document`` as the package at ``new_path`` and remove the package at ``old_path``.

    Safe when both paths name the same file, as a case-only rename does on a case-insensitive
```

```python
    """Write ``document`` as the package at ``new_path`` and remove the package at ``old_path``.

    Every rename uses this sequence, case-only or not (F-3).

    Safe when both paths name the same file, as a case-only rename does on a case-insensitive
```

- [ ] **Step 4: Green.**

```bash
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
git -C $REPO grep -c "KNOWN BUG (P1-3 spec, known defect 3" -- client/tests; echo "defect-3 markers: exit $?"
git -C $REPO grep -n "_UnusablePackageFiles\|_FailingInstallPackageFiles" -- client; echo "old injectors: exit $?"
```

Expected (`git grep` finds nothing, exit status 1, for both):

```text
Ran 296 tests
OK (skipped=6)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1175 tests
FAILED (failures=1, errors=1, skipped=7)
defect-3 markers: exit 1
old injectors: exit 1
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/documents/workspace_service.py client/documents/workspace.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -m "fix: route every rename through move_document_package (F-3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
18d5cecf917ddefb8b6e90bf0c34c477e1151f61
```

### Task 6: Report every save error at the document UI boundary (D9, F review M-1)

- [ ] **Step 1: Red: one service test and four GUI tests** (4 spaces). The import test fails the second of two documents, so the old code shows the worst case: `beta.dep` is written but never added to the list.

Edit: `client/tests/test_workspace_service.py`

```python
from documents.controller import DocumentController
```

```python
import documents.workspace_service as workspace_service
from documents.controller import DocumentController
```

Edit: `client/tests/test_workspace_service.py`

```python
    def test_import_files_rejects_unknown_format(self) -> None:
```

```python
    def test_import_files_reports_any_save_error_as_an_issue(self) -> None:
        # F-3 (D9): an error that is not an OSError becomes an issue too; before, it
        # escaped after beta.dep was written, and beta never reached the list.
        service = self._service([Document("zoo", "z", "1")])
        real_save = workspace_service.save_document_package
        error = UnicodeEncodeError("utf-8", "\ud800", 0, 1, "surrogates not allowed")

        def save(path, document, **kwargs):
            if document.name == "delta":
                raise error
            return real_save(path, document, **kwargs)

        with patch.object(workspace_service, "save_document_package", side_effect=save):
            result = service.import_files(self._sources(beta="b", delta="d"), format_key="all")

        self.assertEqual(result.saved, [Document("beta", "b", None)])
        self.assertEqual(result.issues, [BatchIssue(path=self.workspace / "delta.dep", reason=str(error))])
        self.assertEqual(self.controller.document_names, ["zoo", "beta"])
        self.assertEqual(self._listing(), ["beta.dep"])

    def test_import_files_rejects_unknown_format(self) -> None:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
        self.assertEqual(self._state(frame), before)
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))
```

```python
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "beta.dep", frame)
        self.assertEqual(self._state(frame), before)
        self.assertEqual((frame.input_txt.value, frame.output_txt.value), ("a", "1"))

    def test_add_failure_that_is_not_an_os_error_shows_the_message(self) -> None:
        # F-3 (D9): every Exception from creating the package is reported.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        before = self._state(frame)
        self.names = ["beta"]

        with patch.object(frame._workspace_service, "create_document", side_effect=ValueError("boom")):
            frame.on_add_document(None)

        self.assertEqual(
            self.events,
            [
                ("DocumentNameDialog", gui._("Add Document"), ""),
                (
                    "MessageBox",
                    gui._("Failed to save document: {error}").format(error="boom"),
                    gui._("Error"),
                    gui.wx.OK | gui.wx.ICON_ERROR,
                    frame,
                ),
            ],
        )
        self.assertEqual(self._state(frame), before)
        self.assertEqual(self._listing(), ["alpha.dep"])
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()

    # --- rename ------------------------------------------------------------
```

```python
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()

    def test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package(self) -> None:
        # F-3 (D9): a lone surrogate cannot be encoded. The message appears instead of an
        # escaping exception; the package keeps its bytes and memory keeps the edit.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("x\ud800")

        self.assertFalse(frame._save_open_document_with_feedback())

        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "surrogates not allowed", frame)
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "x\ud800", "1")])

    def test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error(self) -> None:
        # Before F-3 the exception escaped _on_close: no message, and the window neither
        # closed nor said why.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("\ud800")
        event = Mock()
        event.CanVeto.return_value = True

        frame._on_close(event)

        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "surrogates not allowed", frame)
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    # --- rename ------------------------------------------------------------
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertIn(f"[Errno 13] Permission denied: {str(beta_path)!r}", self.events[1][1])
        self.assertEqual(beta_path.read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)
```

```python
        self.assertIn(f"[Errno 13] Permission denied: {str(beta_path)!r}", self.events[1][1])
        self.assertEqual(beta_path.read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)

    def test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state(self) -> None:
        # F-3 (D9): renaming the non-open beta, whose text in memory cannot be encoded.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha, Document("beta", "b", "2"))
        beta_bytes = (self.workspace / "beta.dep").read_bytes()
        frame = self._make_workspace_frame([alpha, Document("beta", "\ud800", "2")], open_name="alpha", selected_name="beta")
        before = self._state(frame)
        self.names = ["gamma"]

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "surrogates not allowed", frame)
        self.assertEqual((self.workspace / "beta.dep").read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)
```

```bash
$PY -m unittest tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (each one escapes as an error):

```text
ERROR: test_import_files_reports_any_save_error_as_an_issue (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_import_files_reports_any_save_error_
UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 0: surrogates not allowed
ERROR: test_add_failure_that_is_not_an_os_error_shows_the_message (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_add_failure_tha
ValueError: boom
ERROR: test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_cl
ERROR: test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.t
ERROR: test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTe
UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 1: surrogates not allowed
Ran 202 tests
FAILED (errors=5)
```

- [ ] **Step 2: Catch `Exception`** in the three frame handlers (`client/gui.py`, **tabs**) and in the import loop (`client/documents/workspace_service.py`, 4 spaces). Delete and Delete All keep `OSError`.

Edit: `client/gui.py`

```python
			self._save_open_document()
		except OSError as exc:
```

```python
			self._save_open_document()
		except Exception as exc:
```

Edit: `client/gui.py`

```python
			self._workspace_service.create_document(document)
		except OSError as exc:
```

```python
			self._workspace_service.create_document(document)
		except Exception as exc:
```

Edit: `client/gui.py`

```python
			renamed_document = self._workspace_service.rename_document(selected_document.name, new_name)
		except OSError as exc:
```

```python
			renamed_document = self._workspace_service.rename_document(selected_document.name, new_name)
		except Exception as exc:
```

Edit: `client/documents/workspace_service.py`

```python
                save_document_package(package_path, document)
            except OSError as exc:
```

```python
                save_document_package(package_path, document)
            except Exception as exc:
```

- [ ] **Step 3: Green.**

```bash
git -C $REPO diff --stat -- client/gui.py
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
 client/gui.py | 6 +++---
 1 file changed, 3 insertions(+), 3 deletions(-)
Ran 301 tests
OK (skipped=6)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1180 tests
FAILED (failures=1, errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/gui.py client/documents/workspace_service.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -m "fix: report every save error at the document UI boundary (F-3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
d79139ecb3f9e134dd46638489dbc54715be9d4f
```


### Task 7: Verification (no commit)

`BASE` is the merge base with `main` (`d4a7aa1` until Task 9); comparing with `main` itself would include P2-5, which `main` already has.

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = baseline 1143 + 37; the failure is the P2-5 case, the error F-W6; skips 5 + the two POSIX-only tests):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_do
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1180 tests
FAILED (failures=1, errors=1, skipped=7)
```

- [ ] **Step 2: Criterion 2, focused modules; the eight Windows-only tests run.**

```bash
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(a_read_only_file_is_refused_with_the_in_place_verdict|a_file_held_open_by_another_handle_is_kept|save_of_a_read_only_package_gives_the_old_message|save_of_a_package_held_open_keeps_it|save_of_a_hidden_package_replaces_it_and_drops_the_attribute|read_only_old_package_is_refused_and_leaves_no_temporary_file|rename_of_a_package_held_open_by_another_program|rename_of_a_read_only_package_is_refused_with_the_save_message) .* ok$" | sed 's/ (.*//'
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep "skipped '" | sed 's/ (.*) \.\.\. / /'
```

Expected (the six skips are the POSIX-only permission tests):

```text
Ran 301 tests
OK (skipped=6)
test_a_file_held_open_by_another_handle_is_kept
test_a_read_only_file_is_refused_with_the_in_place_verdict
test_save_of_a_hidden_package_replaces_it_and_drops_the_attribute
test_save_of_a_package_held_open_keeps_it
test_save_of_a_read_only_package_gives_the_old_message
test_read_only_old_package_is_refused_and_leaves_no_temporary_file
test_rename_of_a_package_held_open_by_another_program
test_rename_of_a_read_only_package_is_refused_with_the_save_message
test_keeps_the_permission_bits_of_an_existing_file skipped 'POSIX permission bits'
test_a_new_file_gets_the_default_mode_for_the_umask skipped 'POSIX permission bits'
test_a_read_only_file_gets_the_same_verdict_as_writing_it_in_place skipped 'POSIX permission bits'
test_keeps_the_permission_bits_of_an_existing_file skipped 'POSIX permission bits'
test_save_keeps_the_permission_bits_of_the_package skipped 'POSIX permission bits'
test_case_only_move_keeps_the_permission_bits_of_the_old_package skipped 'POSIX permission bits'
```

- [ ] **Step 3: Criterion 3, shuffled module order, five seeds** (one process each).

```bash
for s in 0 1 2 3 4; do $PY $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
      5 ran=1180 failures=1 errors=1 skipped=7 ['test_case_only_rename_still_renames', 'test_translate_with_language_does_not_duplicate_existing_spaces_around_math']
```

- [ ] **Step 4: Criteria 4 and 5, strings, locales and fixtures.**

```bash
BASE=$(git -C $REPO merge-base main HEAD)
git -C $REPO diff --stat $BASE -- client/locales
git -C $REPO diff $BASE -- client ':!client/tests' | grep -E '^\+.*\b(N_|_)\(' ; echo "new gettext calls: exit $?"
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --stat $BASE -- client/tests/fixtures
```

Expected (no `.po`/`.mo` or fixture diff; `grep` finds no new `_(`/`N_(` call, exit 1; msgids identical to Task 0):

```text
new gettext calls: exit 1
source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
```

- [ ] **Step 5: Criteria 6-8, app data, markers, touched files, braille runtime.**

```bash
for p in dictionary workspace config.json; do test -e $p && echo "EXISTS client/$p"; done; echo "app data checked"
git -C $REPO grep -c "KNOWN BUG (P1-3 spec, known defect 3" -- client/tests; echo "defect 3: exit $?"
git -C $REPO grep -c "KNOWN BUG (P1-3 spec, known defect 4" -- client/tests
BASE=$(git -C $REPO merge-base main HEAD)
git -C $REPO diff --stat=200 $BASE -- client
git -C $REPO diff --quiet $BASE -- client/braille client/dictionaries client/locales && echo "braille, dictionaries, locales unchanged"
git -C $REPO status --short
```

Expected (the worktree has no `client/dictionary/`, `client/workspace/` or `client/config.json`, and the suite created none; `status` prints nothing):

```text
app data checked
defect 3: exit 1
client/tests/test_gui_document_flows.py:1
 client/documents/workspace.py                  |  57 ++++++++++++++++++++++++++++-------
 client/documents/workspace_service.py          |  31 ++++++++-----------
 client/gui.py                                  |   6 ++--
 client/shared/atomic_write.py                  |  82 ++++++++++++++++++++++++++++++++------------------
 client/tests/case_insensitive_package_files.py |   3 ++
 client/tests/test_atomic_write.py              | 165 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_document_workspace.py        | 239 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_gui_document_flows.py        | 159 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++------
 client/tests/test_workspace_service.py         | 219 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-------------------
 client/tests/windows_file_handles.py           | 102 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 10 files changed, 964 insertions(+), 99 deletions(-)
braille, dictionaries, locales unchanged
```

- [ ] **Step 6: Criterion 9, mutation check** (15 mutants, about 2 minutes). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f3_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
save-in-place: 10 caught: test_document_workspace.test_save_failure_from_a_lone_surrogate_keeps_the_existing_package, test_document_workspace.test_save_failure_while_writing_keeps_the_existing_package, test_document_workspace.test_save_install_failure_keeps_the_existing_package, test_document_workspace.test_save_installs_a_temporary_file_from_the_same_folder, test_document_workspace.test_save_of_a_hidden_package_replaces_it_and_drops_the_attribute, test_document_workspace.test_save_of_a_package_held_open_keeps_it, test_document_workspace.test_save_refuses_a_package_without_write_access, test_gui_document_flows.test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error, and 2 more
no-fsync: 1 caught: test_atomic_write.test_data_is_flushed_to_disk_before_the_replace
no-flush: 1 caught: test_atomic_write.test_data_is_flushed_to_disk_before_the_replace
clean-up-only-on-os-error: 7 caught: test_atomic_write.test_an_unknown_encoding_raises_it_and_leaves_no_temporary_file, test_atomic_write.test_failure_without_an_existing_file_creates_nothing, test_atomic_write.test_interrupt_leaves_no_temporary_file_and_propagates, test_atomic_write.test_write_error_keeps_the_original_bytes_and_leaves_no_temporary_file, test_document_workspace.test_save_failure_from_a_lone_surrogate_keeps_the_existing_package, test_gui_document_flows.test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package, test_workspace_service.test_save_failure_keeps_the_package_and_updates_memory
temporary-file-in-the-system-temp-folder: 4 caught: test_atomic_write.test_a_taken_temporary_name_is_skipped_and_kept, test_atomic_write.test_gives_up_when_every_temporary_name_is_taken, test_atomic_write.test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file, test_document_workspace.test_save_installs_a_temporary_file_from_the_same_folder
bytes-variant-without-write-check: 4 caught: test_atomic_write.test_a_file_without_write_access_raises_permission_error_and_is_kept, test_atomic_write.test_a_read_only_file_is_refused_with_the_in_place_verdict, test_document_workspace.test_save_of_a_read_only_package_gives_the_old_message, test_document_workspace.test_save_refuses_a_package_without_write_access
write-check-on-a-missing-file: 111 caught: test_atomic_write.test_creates_a_file_that_does_not_exist, test_atomic_write.test_data_is_flushed_to_disk_before_the_replace, test_atomic_write.test_ensure_writable_accepts_missing_and_writable_files_and_refuses_others, test_atomic_write.test_failure_without_an_existing_file_creates_nothing, test_case_insensitive_package_files.test_move_document_package_keeps_a_case_only_renamed_package, test_case_insensitive_package_files.test_replace_resolves_case_variants, test_case_insensitive_package_files.test_the_old_rename_sequence_deletes_a_case_only_renamed_package, test_case_insensitive_package_files.test_writing_a_case_variant_rewrites_the_existing_entry_and_keeps_its_spelling, and 103 more
staged-write-without-fsync: 1 caught: test_document_workspace.test_staged_package_is_written_directly_and_flushed_to_disk
staged-write-nested: 1 caught: test_document_workspace.test_staged_package_is_written_directly_and_flushed_to_disk
move-without-write-check: 4 caught: test_document_workspace.test_read_only_old_package_is_refused_and_leaves_no_temporary_file, test_document_workspace.test_unwritable_old_package_is_refused_before_anything_changes, test_gui_document_flows.test_rename_of_a_read_only_package_is_refused_with_the_save_message, test_workspace_service.test_rename_of_an_unwritable_package_is_refused
regular-rename-write-then-unlink: 8 caught: test_gui_document_flows.test_rename_of_a_read_only_package_is_refused_with_the_save_message, test_gui_document_flows.test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state, test_workspace_service.test_regular_rename_ignores_a_failure_to_remove_the_moved_aside_package, test_workspace_service.test_regular_rename_install_failure_puts_the_old_package_back, test_workspace_service.test_regular_rename_moves_the_old_package_aside_before_installing, test_workspace_service.test_rename_of_a_package_held_open_by_another_program, test_workspace_service.test_rename_of_an_unwritable_package_is_refused, test_workspace_service.test_rename_that_cannot_move_the_old_package_aside_keeps_one_package_and_state
save-feedback-catches-os-error-only: 2 caught: test_gui_document_flows.test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error, test_gui_document_flows.test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package
add-catches-os-error-only: 1 caught: test_gui_document_flows.test_add_failure_that_is_not_an_os_error_shows_the_message
rename-catches-os-error-only: 1 caught: test_gui_document_flows.test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state
import-catches-os-error-only: 1 caught: test_workspace_service.test_import_files_reports_any_save_error_as_an_issue
exit 0
```

### Task 8: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the dry run except the build itself: the same code was built in a scratch clone with the command below ("Build complete!" in 43 s, 48,733,081 bytes; `client\build\DotExpress\PYZ-00.toc` listed the clone's own `documents\workspace.py` and `shared\atomic_write.py`). The GUI scripts were only syntax-checked. Run everything from PowerShell in the worktree root, one item at a time, with nothing else driving the desktop.

- [ ] **Step 1: Build.** The worktree has no `client\.venv`; the main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`, and `pyinstaller.exe` analyzes `gui.py` in the current checkout (the venv adds no path of the main checkout). Task 0 already copied the generated `liblouis.dll`, `liblouis\tables`, `louis_helper.py` and `mathcat\assets` the build bundles.

```powershell
Set-Location D:\workspace\DotExpress-f3
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f3-build.log 2>&1"
if (Select-String -Path $env:TEMP\f3-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress-f3\\client\\documents\\workspace.py" -Quiet) { "bundled from the worktree" }
New-Item -ItemType Directory -Force D:\dxtest\N-f3 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f3\DotExpress.exe
(Get-Item D:\dxtest\N-f3\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f3\DotExpress.exe).Hash
git status --short
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f3-build.log`), `bundled from the worktree`, a size near 48.7 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored). If the main venv is gone, create one in the worktree instead (`py -3.13 -m venv client\.venv`, then `client\.venv\Scripts\pip install -r client\requirements.txt pyinstaller==6.21.0`; `client\.venv\` is git-ignored) and put that on `PATH`. Do not touch `D:\dxtest\N`, `D:\dxtest\B` or `D:\dxtest\N-p25`.

- [ ] **Step 2: Create the GUI scripts** in a new history folder (4 spaces). They reuse `dx.py`, `docs.py` and `lock.py` of `2026-10-09-03-windows-verification/auto/`, which stay unchanged: `rerun.py` runs the hard-coded items 18, 19 and 21 against another exe and work folder by replacing their two path literals in memory.

File: `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/f3gui.py`

````python
"""Shared helpers for the F-3 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py and lock.py of the 2026-10-09-03 Windows verification unchanged.
Every item script takes <exe> <work folder>; dx.launch deletes the folder first.
"""
import os
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO03 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-09-03-windows-verification", "auto"))
sys.path.insert(0, AUTO03)
import dx  # noqa: E402
import docs as D  # noqa: E402

LOCK = os.path.join(AUTO03, "lock.py")


def workspace(d):
    return os.path.join(d, "workspace")


def files(d):
    return sorted(os.listdir(workspace(d)))


def leftovers(d):
    return [name for name in files(d) if name.endswith(".tmp")]


def open_document(app, w, name):
    """Select ``name``, choose File > Open (#0->#0) and return the message boxes it showed."""
    D.select(w, name)
    w.set_focus()
    w.menu_select("#0->#0")
    time.sleep(1.2)
    return dx.dismiss(app)


def setup_alpha_beta(exe, d):
    """A new work folder with the documents alpha ("alpha body") and beta ("beta body"); alpha is open."""
    app, w = dx.launch(exe, d)
    print("add alpha:", D.add(app, w, "alpha"))
    D.set_input(w, "alpha body")
    print("add beta:", D.add(app, w, "beta"))
    D.set_input(w, "beta body")
    print("open alpha:", open_document(app, w, "alpha"))
    print("docs:", D.docs(w), "title:", w.window_text(), "files:", files(d))
    return app, w


def attrib(path):
    return subprocess.run(["cmd", "/c", "attrib", path], capture_output=True, text=True).stdout.strip()


def member_text(path, member):
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
````

File: `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/rerun.py`

````python
"""Run a 2026-10-09-03 GUI script against another build and work folder (F-3).

Usage: python rerun.py <script.py> <exe> <work folder> [--seed <folder>]

item18.py, item19.py and item21.py hard-code the N build and D:\\dxtest\\auto18. This
wrapper reads the script, replaces exactly those two literals (each must occur once), and
runs it with __file__ pointing at the original, so it still imports dx/docs and finds
lock.py next to it. The committed scripts are not changed. With --seed, the work folder
(which must not exist yet) starts as a copy of the given folder: items 19 and 21 continue
from the documents item 18 leaves.
"""
import os
import shutil
import sys

OLD_EXE = 'r"D:\\dxtest\\N\\DotExpress.exe"'
OLD_DIR = 'r"D:\\dxtest\\auto18"'


def main():
    args = sys.argv[1:]
    seed = None
    if "--seed" in args:
        index = args.index("--seed")
        seed = args[index + 1]
        del args[index:index + 2]
    script, exe, work = (os.path.abspath(arg) for arg in args)
    with open(script, encoding="utf-8") as handle:
        source = handle.read()
    for old in (OLD_EXE, OLD_DIR):
        if source.count(old) != 1:
            sys.exit(f"{old} occurs {source.count(old)} times in {script}")
    source = source.replace(OLD_EXE, repr(exe)).replace(OLD_DIR, repr(work))
    if seed is not None:
        if os.path.exists(work):
            sys.exit(f"{work} exists; --seed needs a new folder")
        shutil.copytree(seed, work)
    sys.argv = [script]
    sys.path.insert(0, os.path.dirname(script))
    exec(compile(source, script, "exec"), {"__name__": "__main__", "__file__": script})


if __name__ == "__main__":
    main()
````

File: `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/item30.py`

````python
"""Item 30 (F-3): regular rename of the non-open beta while beta.dep is held open.

Usage: python item30.py <exe> <work folder>
After F-3, for share r and rw: 儲存文件失敗：[WinError 32] ...: '...\\beta.dep' ->
'...\\.beta.dep.<random>.tmp'; the list and the disk do not change (no gamma.dep, no .tmp);
after a restart alpha and beta are listed and beta keeps its text.
Before F-3: gamma.dep and beta.dep both stayed on disk and both were listed after a restart.
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f3gui import LOCK, D, dx, files, leftovers, member_text, setup_alpha_beta, workspace  # noqa: E402

EXE, d = sys.argv[1], sys.argv[2]
app, w = setup_alpha_beta(EXE, d)
beta = os.path.join(workspace(d), "beta.dep")
for share in ("r", "rw"):
    print(f"== 30 share={share}")
    before = D.ws_state(d)
    lock = subprocess.Popen([sys.executable, LOCK, beta, "120", share])
    time.sleep(2)
    D.select(w, "beta")
    print("rename beta -> gamma while held open:", D.rename(app, w, "gamma"))
    D.cancel_open(app, w)
    print("docs:", D.docs(w), "diff:", D.diff(before, D.ws_state(d)), "files:", files(d), "tmp:", leftovers(d))
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(lock.pid)], capture_output=True)
    time.sleep(1)
print("close:", D.close(app, w))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart docs:", D.docs(w), "files:", files(d))
print("beta text:", repr(member_text(beta, "beta.txt")))
print("close:", D.close(app, w))
````

File: `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/item31.py`

````python
"""Item 31 (F-3): renaming the non-open beta while beta.dep is read-only.

Usage: python item31.py <exe> <work folder>
After F-3, for the regular rename beta -> gamma and the case-only rename beta -> Beta:
儲存文件失敗：[Errno 13] Permission denied: '...\\beta.dep'; the list and the disk do not
change, no .tmp, beta.dep stays read-only; after a restart alpha and beta are listed.
Before F-3: regular [WinError 5] with gamma.dep and beta.dep both left; case-only renamed,
with a read-only .beta.dep.<random>.tmp left that the app cannot delete.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f3gui import D, attrib, dx, files, leftovers, setup_alpha_beta, workspace  # noqa: E402

EXE, d = sys.argv[1], sys.argv[2]
app, w = setup_alpha_beta(EXE, d)
beta = os.path.join(workspace(d), "beta.dep")
subprocess.run(["attrib", "+r", beta])
for new_name in ("gamma", "Beta"):
    print(f"== 31 rename beta -> {new_name}")
    before = D.ws_state(d)
    D.select(w, "beta")
    print("rename:", D.rename(app, w, new_name))
    D.cancel_open(app, w)
    print("docs:", D.docs(w), "diff:", D.diff(before, D.ws_state(d)), "files:", files(d), "tmp:", leftovers(d))
    print("attrib:", attrib(beta))
subprocess.run(["attrib", "-r", beta])
print("close:", D.close(app, w))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart docs:", D.docs(w), "files:", files(d))
print("close:", D.close(app, w))
````

File: `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/item32.py`

````python
"""Item 32 (F-3): the open document's package is hidden; type, switch document, restart.

Usage: python item32.py <exe> <work folder>
After F-3: switching to beta saves alpha with no message, alpha.dep is no longer hidden,
no .tmp, and after a restart alpha has the typed text.
Before F-3: 儲存文件失敗：[Errno 13] Permission denied: '...\\alpha.dep', switch blocked.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f3gui import D, attrib, dx, leftovers, member_text, open_document, setup_alpha_beta, workspace  # noqa: E402

EXE, d = sys.argv[1], sys.argv[2]
app, w = setup_alpha_beta(EXE, d)
alpha = os.path.join(workspace(d), "alpha.dep")
subprocess.run(["attrib", "+h", alpha])
print("attrib before:", attrib(alpha))
D.set_input(w, "alpha typed while hidden")
print("switch to beta:", open_document(app, w, "beta"), "title:", w.window_text())
print("attrib after:", attrib(alpha), "tmp:", leftovers(d))
print("alpha text on disk:", repr(member_text(alpha, "alpha.txt")))
print("close:", D.close(app, w))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart docs:", D.docs(w))
print("open alpha:", open_document(app, w, "alpha"), "input:", repr(D.get_input(w)))
print("close:", D.close(app, w))
````

File: `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/item33.py`

````python
"""Item 33 (F-3): Defender real-time protection on; 20 document switches, each after an edit.

Usage: python item33.py <exe> <work folder>
After F-3: 20 of 20 switches without a message and no .tmp; on disk alpha holds
"alpha edit 19" and beta "beta edit 20". A [WinError 5] would be the scanner holding the
package at that moment: record it (the edit stays in memory; the next action retries).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f3gui import D, files, leftovers, member_text, open_document, setup_alpha_beta, workspace  # noqa: E402

EXE, d = sys.argv[1], sys.argv[2]
status = subprocess.run(
    ["powershell", "-NoProfile", "-Command", "(Get-MpComputerStatus).RealTimeProtectionEnabled"],
    capture_output=True,
    text=True,
)
print("Defender real-time protection:", status.stdout.strip() or status.stderr.strip())
app, w = setup_alpha_beta(EXE, d)
current = "alpha"
failures = 0
for step in range(1, 21):
    D.set_input(w, f"{current} edit {step}")
    target = "beta" if current == "alpha" else "alpha"
    messages = open_document(app, w, target)
    ok = not messages and w.window_text().startswith(f"{target} ")
    tmp = leftovers(d)
    if not ok or tmp:
        failures += 1
    print(step, current, "->", target, "ok" if ok else "FAIL", messages, tmp)
    if ok:
        current = target
print("failures:", failures)
print("close:", D.close(app, w))
ws = workspace(d)
print("alpha text:", repr(member_text(os.path.join(ws, "alpha.dep"), "alpha.txt")))
print("beta text:", repr(member_text(os.path.join(ws, "beta.dep"), "beta.txt")))
print("files:", files(d))
````

```powershell
$UIA = "C:\Users\tseng\AppData\Local\Temp\claude\D--workspace-DotExpress\c9251692-6537-4306-992c-fd6377e303d0\scratchpad\uia\Scripts\python.exe"
& $UIA -c "import pywinauto, psutil; print(pywinauto.__version__, psutil.__version__)"
& $UIA -c "import ast, glob; [ast.parse(open(p, encoding='utf-8').read(), p) for p in glob.glob(r'docs\superpowers\history\2026-10-09-05-f3-dep-atomic-write\auto\*.py')]; print('syntax ok')"
```

Expected `0.6.9 7.2.2` and `syntax ok`. If that venv no longer exists, create one anywhere outside the repo with `python -m venv` and `pip install pywinauto==0.6.9 psutil`, and use its `python.exe` as `$UIA`.

- [ ] **Step 3: Items 18-21 against the F-3 build.** Each run gets a new folder (`dx.launch` deletes an existing one for item 18; `--seed` refuses an existing folder, so delete `D:\dxtest\auto19-f3` and `D:\dxtest\auto21-f3` before a repeat). Items 19 and 21 start from a copy of item 18's documents, as they did in `D:\dxtest\auto18` before. Item 20 is the second half of `item19.py`. Defender real-time protection must be on for item 21 (`(Get-MpComputerStatus).RealTimeProtectionEnabled`).

```powershell
$H3 = "docs\superpowers\history\2026-10-09-03-windows-verification\auto"
$H5 = "docs\superpowers\history\2026-10-09-05-f3-dep-atomic-write\auto"
$EXE = "D:\dxtest\N-f3\DotExpress.exe"
& $UIA "$H5\rerun.py" "$H3\item18.py" $EXE D:\dxtest\auto18-f3 *> D:\dxtest\auto18-f3.log
& $UIA "$H5\rerun.py" "$H3\item19.py" $EXE D:\dxtest\auto19-f3 --seed D:\dxtest\auto18-f3 *> D:\dxtest\auto19-f3.log
& $UIA "$H3\item20b.py" $EXE D:\dxtest\auto20b-f3 *> D:\dxtest\auto20b-f3.log
& $UIA "$H5\rerun.py" "$H3\item21.py" $EXE D:\dxtest\auto21-f3 --seed D:\dxtest\auto18-f3 *> D:\dxtest\auto21-f3.log
```

Expected (compare with `2026-10-09-03-windows-verification/auto-results.md`, rows 18-21):

| # | Expected after F-3 | N (before) |
| --- | --- | --- |
| 18 | unchanged: `Alpha` renamed to `alpha` keeps its text, only `alpha.dep`, no `.tmp`; `ALPHA` and `Alpha` refused as duplicates; disk unchanged | same |
| 19, share `r` | `rename ...: (None, [...'儲存文件失敗：[WinError 5] 存取被拒。: '...\\.alpha.dep.<16 hex>.tmp' -> '...\\alpha.dep''...], 'no name dialog')`; list `['alpha', 'new']`, `diff: {}`, no `.tmp`; after the restart unchanged | `[Errno 13] Permission denied: '...alpha.dep'` |
| 19, share `rw` | **the same as share `r`** (Q1: the Save before the rename now fails) | Save succeeded, rename failed `[WinError 32] ... 'alpha.dep' -> '.alpha.dep.<random>.tmp'` |
| 20 (`item19.py`, second half) | `[Errno 13] Permission denied: '...\\alpha.dep'` before the name dialog; `close:` ends with `STILL RUNNING -> killed` (F-W10) | same |
| 20b | the same for the open `Alpha.dep` | same |
| 21 | `failures: 0`, `content same (ignoring name): True`, no `.tmp` in any listing | same |

- [ ] **Step 4: New items 30-33** (spec, Windows Verification).

```powershell
& $UIA "$H5\item30.py" $EXE D:\dxtest\auto30-f3 *> D:\dxtest\auto30-f3.log
& $UIA "$H5\item31.py" $EXE D:\dxtest\auto31-f3 *> D:\dxtest\auto31-f3.log
& $UIA "$H5\item32.py" $EXE D:\dxtest\auto32-f3 *> D:\dxtest\auto32-f3.log
& $UIA "$H5\item33.py" $EXE D:\dxtest\auto33-f3 *> D:\dxtest\auto33-f3.log
```

Expected:

| # | Expected after F-3 |
| --- | --- |
| 30 | for share `r` and `rw`: the rename shows `儲存文件失敗：[WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用。: '...\\beta.dep' -> '...\\.beta.dep.<random>.tmp'`; `docs: ['alpha', 'beta', 'new']`, `diff: {}`, `tmp: []`, no `gamma.dep`; after the restart the same list and `beta text: 'beta body'` |
| 31 | for `gamma` and `Beta`: `儲存文件失敗：[Errno 13] Permission denied: '...\\beta.dep'`; `diff: {}`, `tmp: []`, `attrib` still shows `R`; after the restart `['alpha', 'beta', 'new']` |
| 32 | `switch to beta: []`, title `beta - DotExpress`; `attrib after` without `H`; `tmp: []`; `alpha text on disk: 'alpha typed while hidden'`; after the restart the same input |
| 33 | `Defender real-time protection: True`; 20 lines `ok [] []`, `failures: 0`; `alpha text: 'alpha edit 19'`, `beta text: 'beta edit 20'`; no `.tmp` in `files` |

- [ ] **Step 5 (optional, manual): item 34, disk full.** Needs an administrator to create and attach a small VHD (for example 8 MB, NTFS, `diskmgmt.msc` > Action > Create VHD), copy `D:\dxtest\N-f3\DotExpress.exe` onto it, start it there once, fill the volume to a few KB free with a dummy file, paste a large text into a document, switch document, then restart. Expected: a message (record its exact text; expected `儲存文件失敗：[Errno 28] No space left on device`), the edit stays in memory, and after the restart the package loads with the old text (no invalid-package dialog). Leave it unchecked if it is not run; never mark it done without running it.

- [ ] **Step 6: Record and commit the results.** Write `docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto-results.md` in the style of `2026-10-09-03-windows-verification/auto-results.md` (zh-TW): the build (PyInstaller version, exit code, size, sha256), then one row per item (18, 19 r/rw, 20, 20b, 21, 30-33, 34 "not run" unless it was) with ✔/△/✘ and the observed messages and listings. Any deviation from the tables above is reported to the orchestrator before the commit, not explained away.

```powershell
git add docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto-results.md docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/f3gui.py docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/rerun.py docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/item30.py docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/item31.py docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/item32.py docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto/item33.py
git commit -q -m "docs: record the F-3 packaged-build GUI checks (F-3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
```

### Task 9: Merge main into the branch (only when the orchestrator asks; never push)

P2-5 is already on `main` (`4953772 merge: split translate.py, fix the failing test, linear reclean (P2-5)`; `main` alone gives `Ran 1211`, `FAILED (errors=1, skipped=5)`). It touches no file F-3 changes except one import line of `client/gui.py` far from the three `except` lines, so the merge is clean. After it, the P2-5 failure is gone and only F-W6 remains. If `main` has moved past `4953772`, the expected `Ran` is `main`'s own count + 37 and the final line `FAILED (errors=1, skipped=<main's skips + 2>)`; the merge commit's tree id will differ.

- [ ] **Step 1: Merge.**

```bash
git -C $REPO log --format="%h %s" -1 main
git -C $REPO merge -q --no-ff main -m "merge: main into fix/f3-dep-atomic-write (F-3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO log --format=%s -1
git -C $REPO status --short
git -C $REPO rev-parse HEAD:client
```

Expected:

```text
4953772 merge: split translate.py, fix the failing test, linear reclean (P2-5)
Auto-merging client/gui.py
merge: main into fix/f3-dep-atomic-write (F-3)
3cdcf63864b60020c30444faa0653545ddc55099
```

- [ ] **Step 2: Full suite and focused modules on the merged tree.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_atomic_write tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_case_insensitive_package_files tests.test_document_controller 2>&1 | $PY $T/tools/brief.py
$PY -I $T/tools/msgid_scan.py $REPO/client
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --stat main HEAD -- client | tail -1
```

Expected (F-W6 is the only error and F-3 does not change it; the diff against `main` is exactly F-3's client changes):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1248 tests
FAILED (errors=1, skipped=7)
Ran 301 tests
OK (skipped=6)
source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
 10 files changed, 964 insertions(+), 99 deletions(-)
```

