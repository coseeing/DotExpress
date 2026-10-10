# Save-Failure Handling (F-5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix F-W10 and F-3 review M-4. Save writes the open document only when it differs from what was last written to or loaded from its package, or when the package on disk is not the one recorded; an unchanged document whose package is read-only, held open or otherwise unwritable no longer blocks switching, Add, Import, Export or Close. When the save on Close fails, a localized task dialog offers **Retry / Close without saving / Cancel** (Retry is the default). A lone surrogate is saved as U+FFFD, so a save can always encode. Every other action still blocks with the existing message when its save really writes and fails. Four new msgids (353 -> 357), translated, with `.pot`, `.po` and `.mo` regenerated.

**Architecture:** Three commits on the client, each red first, in the spec's migration order. Task 1 adds `replace_lone_surrogates` and applies it in `prepare_document_for_save` and `_normalized` (D4, D5), and moves the tests that injected a lone surrogate as "the non-`OSError` fault" to a `zipfile.ZipFile.writestr` / `PackageFiles.write` `ValueError("injected")`. Task 2 gives `DocumentWorkspaceService` the per-document saved record and package fingerprint and skips the write of an unchanged document (D1-D3). Task 3 adds the close dialog and the retry loop to `client/gui.py` (D6-D9), the `wx_stub` ids, and regenerates the catalogs (D12). Task 4 verifies (suite, shuffled order, catalogs, fixtures, app data, 25 mutants), Task 5 builds the exe and runs the GUI checks (items 36-40, re-runs of 18-20b and 33; item 41 stays manual).

**Tech Stack:** Python 3.13 standard library (`os.stat`, `stat`, `re`, `dataclasses`, `gettext`, `unittest`, `unittest.mock`), wxPython 4.2.5 (`wx.MessageDialog` with `SetExtendedMessage` and `SetYesNoCancelLabels`), GNU gettext 0.23 (`xgettext`, `msgmerge`, `msgfmt`, `msgattrib`), Git Bash `unix2dos`. Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil 7.2.2 in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-10-f5-save-failure-handling-design.md` (+ `_zh-TW.md`), commit `30becb7`, with the section "Corrected after planning" added in the plan commit (both languages). The user decided A-D (2026-10-10); the spec has no open question.

## Global Constraints

- Work in the main checkout `D:\workspace\DotExpress`, branch `fix/f5-save-failure-handling` (HEAD is the plan commit on top of `30becb7`, which is on top of `main` at `918c251`). Never switch branches, never push, never merge, never rewrite history.
- Files that may change (10 under `client/`, nothing else): production `client/documents/workspace.py`, `client/documents/workspace_service.py` (4 spaces), `client/gui.py` (**tabs**); catalogs `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` (tool output plus one `Edit:` block on the `.po`); tests `client/tests/test_document_workspace.py`, `client/tests/test_workspace_service.py`, `client/tests/test_gui_document_flows.py`, `client/tests/wx_stub.py` (all 4 spaces); in Task 5 the new history folder `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/` (scripts with tabs, results).
- Never touch `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data in this checkout; the tests use temporary folders, and Task 0 and Task 4 compare their sha256), `client/braille/tables/__tables.py`, tracked `client/braille/` content, `client/tests/fixtures/`, `client/conversion/`, `client/dialog.py`, `scripts/`, `vendor/`, the submodule pointers, the untracked `client2/`, `preprocessing/`, `testdata/`, or the committed scripts and data of the earlier history folders (`2026-10-09-03-windows-verification/`, `2026-10-09-05-f3-dep-atomic-write/`). Never run `py scripts\sync-nvda.py`. `git status --short -- client docs scripts` must stay empty between commits (the untracked folders at the root are not part of it).
- The checkout uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply `File:` blocks with the Write tool and `Edit:` blocks with the Edit tool: the first block is the exact old text, the second its replacement, each old text occurs once. Never edit with MSYS `sed -i` and never paste Python through a shell heredoc (the agent shell can alter backslashes; this plan's dry run hit it). The `client/gui.py` blocks and the Task 5 scripts contain real tab characters; copy them, do not retype. New test code is ASCII: non-ASCII test data is written with `\u` escapes.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf` (`git show HEAD:<path> | sha256sum`), unchanged.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task. Task 3's tree id holds because Step 3 pins the `.pot` header date (see Spec Corrections 6).
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly.
- The only failing test before and after F-5 is the F-W6 error `test_dictionary_name_prompt ... test_case_only_rename_still_renames` (out of scope).
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`, random temporary-file suffixes as `<rnd>`). Commands print to stdout only; git's CRLF warnings and gettext's progress go to stderr and are not part of the expected blocks. Messages of Windows itself appear in the zh-TW system language (`存取被拒。`).
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress
  MAIN=$REPO
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f5impl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the same folder as `REPO` here; the dry run used a scratch clone as `REPO`, and the commands that read the user's application data or copy the git-ignored runtime use `MAIN`. Task 5 uses PowerShell for the build.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning" in the plan commit. The dry run found no error in decisions D1-D11, in the behavior tables or in the total count (`Ran 1304`).

1. **The surrogate pattern is a raw string**: `_LONE_SURROGATE = re.compile(r"[\ud800-\udfff]")`. With the spec's plain literal the source holds the escapes `\ud800`/`\udfff`, and `xgettext` 0.23 (run by `scripts\generate-pot.bat` over every client module) warns about an invalid Unicode character U+D800 and U+DFFF at `documents/workspace.py:24` on every run. `re` reads `\uXXXX` in a raw pattern itself; the compiled pattern is the same.
2. **`test_close_asks_presenter_before_saving` gains one call.** `_on_close` now passes `evt.CanVeto()` to `_save_open_document_before_close`, so the expected calls of the save branch are `is_running(), event.CanVeto(), save(), close_converting_dialog(), event.Skip()` (the spec said "the expected order is unchanged"). The test mocks `_save_open_document`, which returns nothing, so its `steps.save.return_value = True` line goes.
3. **Counts per commit: 1277, 1298, 1304** (7 + 21 + 6 new tests; the spec's 1304 holds; F-W6 only, `skipped=7` throughout). Which new tests are red before their commit: Task 1 all 7. Task 2: B1, B4, B6, B7, B11, B12, B13, B14, B15b, B16 and C1, C2, C4; B2, B3, B5, B8, B9, B10, B15a and C3 already pass (every save writes today) and guard the write cases. Task 3: C5-C9, C11, the two flipped close tests and the changed presenter test.
4. **Test refinements.** B4 first checks that an unchanged pending document is not written (its braille editor is ignored), then converts it. B11 has three subtests: an empty document, the pending default `new`, and one created with a lone surrogate in text and braille (the record holds the replaced text, so the next unchanged save compares equal; this is the only test of `_encodable` in `_remember`). B15b fills the controller without the service, so only the reload after the failed Delete All can record the remaining document. C1 calls `_open_adjacent_document(1)`, the Ctrl+Tab handler. C2 switches twice (alpha -> beta -> alpha) and then closes, so Close runs with the read-only alpha open. The fake `wx.MessageDialog` of the GUI tests answers Cancel when no answer is queued, so a mutant cannot loop. The non-`OSError` rename tests use a local `_FailingWritePackageFiles` whose `write` raises `ValueError("injected")`; the save tests patch `zipfile.ZipFile.writestr`.
5. **`wx_stub` ids.** `gui_frame_stubs` gets `wx.ID_CANCEL = 5101`, `wx.ID_YES = 5103`, `wx.ID_NO = 5104` (the real values) and `wx.YES_DEFAULT = 1 << 27` (0 in wx; a bit of its own so style assertions see it). Without them the stub returns a new class for each access, so `answer == wx.ID_YES` could never hold. The stub is changed in Task 3's red step (test infrastructure), so the red run fails on assertions, not on a `TypeError`.
6. **Catalogs (D12) in detail.** `msgmerge` marks `Cannot Save Document` fuzzy with the msgstr of `Rename Document` (`重新命名文件`) and leaves the other three empty (`353 translated messages, 1 fuzzy translation, 3 untranslated messages.`); one `Edit:` block fills the four msgstr values and drops the flag, and a second `msgmerge` changes nothing. `xgettext` writes the current time into `POT-Creation-Date`; the plan sets it to `2026-10-10 12:00+0800` in the `.pot` before `msgmerge` (which copies it into the `.po`), so the commit's tree id is reproducible. `msgfmt` 0.23 leaves `POT-Creation-Date` out of the `.mo`. The diff is 57 insertions and 38 deletions in each of `.pot` and `.po`: the four new entries; the `gui.py` references below the new code shifted; `Failed to save document: {error}` moves (its first reference is now `gui.py:465`); and the references of `dictionaries/entries.py` that F-4 left stale (13-46 -> 14-65). No msgid disappears, the 31 obsolete `#~` entries are unchanged, every reference stays client-relative. `.mo` 26,579 -> 26,971 bytes, 358 catalog keys. The committed `.mo` is first checked to be `msgfmt`'s byte-identical output of the committed `.po`, so no fallback is needed.
7. **Windows verification.** wx shows its message boxes as task dialogs; `dx.dismiss` reads their text but its win32 click does not close them, and an open box keeps the process alive after Close (dry run). `f5gui.py` therefore has a UIA `dismiss`, and the re-runs go through a new `rerun.py` that replaces `dx.dismiss` with it in memory (F-3's `rerun.py` and the earlier scripts stay unchanged; `item20b.py` and F-3's `item33.py` run through it as well). `f5gui.answer` presses the key again if the same dialog is still open 5 s later: in the dry run a key sent to a dialog that had just appeared was sometimes lost (2 of 18 presses without the re-press, 1 of 4 in the last smoke run, then accepted at the second press). Items 36 and 37 share `item36.py <exe> <folder> readonly|r|rw`; items 38 and 39 share `item38.py <exe> <folder> 38|39`. The OK button of the existing error box reads `OK` (F-W9), not `確定` as the spec's "Before" column of item 38 says.

## Dry Run

The plan was executed on scratch clones of the branch at `30becb7` with a stand-in plan commit (this plan and the corrected spec files) and a local `main` at `918c251` (`$SP/f5plan/r*`, never the main checkout), by F-4's harness: it writes every `File:` block, applies every `Edit:` block exactly once (CRLF-aware), runs every `bash` block from `client/` with `REPO` set to the clone and `MAIN` to the main checkout (so Task 0's guarded copies filled the clone, and the application-data check read the real data read-only), and compares its stdout with the following `text` block. The final replay (`r4`, Tasks 0-4 from a fresh clone) matched every expected block, including all red runs, the per-commit tree ids, the catalog steps, the six shuffle seeds and the mutation output. Final sha256 after Task 3 (`git show HEAD:<path>`): `client/documents/workspace.py` `ba2ba5b056c4556d9e4a4db60b82c69432a597c9f5e610e281b6f9ae73b95c74`, `client/documents/workspace_service.py` `e2c11fc18ad66ef387671d3f3a2bb113b47cd6896eeb873516081dbee1102c3a`, `client/gui.py` `dd7ea4d82270d1648e455df2cb3a64acc58bf11e963c5ad5dff808fde6531fd4`, `client/tests/wx_stub.py` `95c32445d0eaf8e37673671f63af5446802682744ba92d89ecc6d973a765229b`, `client/locales/dotexpress.pot` `f35599dc4df23dd458a3598874eae60ee557b6d96726c200560b98f37f72fd82`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` `409b18b9ea0a759d2dce808b555b7e759e368a16f30120714064bbcc13b5572a`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` `a4999716d120de41e136f926d45364471976605066ce0046842b0bc1b8fae8f5`.

Task 5 was run too, against a build of the same code from a scratch clone (the command of Step 1: "Build complete!" in 49 s, 48,743,550 bytes; the three production modules and the `.mo` byte-identical to the final ones). Step 2's checks gave its expected block (with `presses: 2` for Esc once, see Spec Corrections 7). Items 36, 37 r, 37 rw, 38, 39 and 40 ran with the final scripts and printed exactly the lines of Step 3's table; the re-runs of 18, 19 (with 20), 20b and 33 ran through `rerun.py` with an `f5gui.py` that differed from the final one only in its docstring and an unused import, and matched Step 4's table. Everything ran in `D:\dxtest\dry*-f5` folders, deleted afterwards; no `D:\dxtest\auto*-f5` folder exists yet. Two things the dry run found shaped the scripts: `dx.dismiss` cannot close a wx message box (a task dialog), and an open box kept the process alive after Close, so the first version of item 38 left four processes behind; and a key sent to a dialog that has just appeared is sometimes lost. Item 41 (NVDA) was not run.

## Review Focus

1. **A failed save is never skipped later.** The record changes only after a successful write or a load, never from the controller (B5, B6; mutants `baseline-from-the-controller-copy`, `record-before-the-write`, `record-despite-a-failed-write`).
2. **"When in doubt, write."** No record, a different document, a missing, replaced or touched package (fingerprint) all write (B8, B9, B10; mutants `no-fingerprint-check`, `fingerprint-without-the-modification-time`).
3. **Every path that writes, loads or removes a package keeps the record right** (B11-B15b; one mutant per path).
4. **Close never loses edits silently.** Retry loops, Close without saving is never the default and drops only the edits since the last good save (the package is that save), Cancel and Esc keep the window open, a close Windows forces is logged (C5-C9, the flipped tests; six GUI mutants).
5. **The dialog is accessible and localized**: a standard task dialog, all labels passed in, `YES_DEFAULT`, mnemonics; C5 asserts every argument, C11 the translations, items 38 and 41 the real dialog.

## File Map

- Task 1: `client/tests/test_document_workspace.py` (A1-A5, two injector changes), `client/tests/test_workspace_service.py` (B17, one injector change), `client/tests/test_gui_document_flows.py` (C10, `_FailingWritePackageFiles`, five injector changes); `client/documents/workspace.py` (`_LONE_SURROGATE`, `replace_lone_surrogates`, `_encodable`, `_normalized`, `prepare_document_for_save`).
- Task 2: `client/tests/test_workspace_service.py` (`SaveOnlyWhenChangedTest`, B1-B16), `client/tests/test_gui_document_flows.py` (C1-C4 and their helpers); `client/documents/workspace_service.py` (`_SavedPackage`, `_package_fingerprint`, the record and its updates, module docstring).
- Task 3: `client/tests/wx_stub.py` (ids, `_MessageDialog`), `client/tests/test_gui_document_flows.py` (fake dialog, C5-C9, C11, two flips, the presenter test); `client/gui.py` (`_log_unexpected_save_error`, `_ask_after_close_save_failure`, `_save_open_document_before_close`, `_on_close`); `client/locales/` (three files).
- Task 5: new `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/` (`auto/f5gui.py`, `auto/rerun.py`, `auto/item36.py`, `auto/item38.py`, `auto/item40.py`, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | `HEAD:client` |
| --- | --- | --- | --- | --- |
| baseline (`30becb7` + plan) | - | 1270 | `FAILED (errors=1, skipped=7)` | `f244bb8e70a42ce08c98d3145f5c806f9818ac32` |
| 1 lone surrogates | 7 (A1-A5, B17, C10); 8 tests change their injector | 1277 | `FAILED (errors=1, skipped=7)` | `855670fe907c9634a341451694c79635a02ebd61` |
| 2 skip unchanged | 21 (B1-B16 with B15 as two, C1-C4) | 1298 | `FAILED (errors=1, skipped=7)` | `5d36ba64348a3928bbd7f2a9ba5193823c251815` |
| 3 close dialog and catalogs | 6 (C5-C9, C11); 2 flipped, 1 changed | 1304 | `FAILED (errors=1, skipped=7)` | `8f8ee46eb955cbc579ca7df8bc8c1345ee006014` |
| 5 GUI results (docs only) | - | 1304 | `FAILED (errors=1, skipped=7)` | `8f8ee46eb955cbc579ca7df8bc8c1345ee006014` |

The error is F-W6 throughout. The 7 skips are POSIX-only tests; the two new Windows-only tests (B16, C2) run. The three modules F-5 changes go from `Ran 255`, `OK (skipped=2)` to `Ran 289`, `OK (skipped=2)`; the spec's acceptance-criterion-2 set from `Ran 319` to `Ran 353`, `OK (skipped=6)`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 with the Write tool: `brief.py` (output condenser), `msgid_scan.py` and `shuffle_harness.py` (the P2-5/F-3/F-4 tools), `f5_mutants.py` (25 mutants of the code after Task 3, run on a copy of `client/`; the repository is never changed), `pin_pot_date.py` (Task 3) and `mo_check.py` (Tasks 3 and 4). Task 5 adds `close_dialog_demo.py` and `smoke_f5gui.py`.

---

### Task 0: Baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short -- client docs scripts
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO merge-base main HEAD
git -C $REPO diff $(git -C $REPO merge-base main HEAD) --stat -- client
```

Expected (`status` and the diff print nothing; the merge base is `main` at `918c251`):

```text
docs: plan for save-failure handling (F-5)
fix/f5-save-failure-handling
918c2518fb9bb70c6e55127ad11553b43a702b52
```

- [ ] **Step 2: The git-ignored runtime the tests load.** The main checkout already has the generated liblouis DLL and tables, `louis_helper.py`, MathCAT and the submodule's `configure.ac`; the guarded copies below do nothing there (they filled the dry run's scratch clone, as F-3's and F-4's Task 0 did for their worktrees). Without these files the baseline is 5 tests lower with `errors=2`.

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

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed) with the Write tool. `msgid_scan.py` and `shuffle_harness.py` are the P2-5/F-3/F-4 tools unchanged; `brief.py` is F-4's with one change (a cut line is printed once, so the subtests of one test give one header).

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
each msgid the F-5 close dialog shows (msgfmt 0.23 leaves POT-Creation-Date out of the
.mo header, so the .mo does not depend on it). Output is UTF-8 (-I ignores PYTHONIOENCODING).
"""
import gettext
import sys

sys.stdout.reconfigure(encoding="utf-8")

MSGIDS = (
    "Cannot Save Document",
    "Changes made since the last successful save have not been saved. "
    "If you close without saving, these changes will be lost.",
    "&Retry",
    "Close &Without Saving",
    "Cancel",
    "Failed to save document: {error}",
)

with open(sys.argv[1], "rb") as stream:
    catalog = gettext.GNUTranslations(stream)
print("catalog keys:", len(catalog._catalog))
for msgid in MSGIDS:
    print(f"{msgid[:40]!r} -> {catalog.gettext(msgid)}")
````

File: `$T/tools/f5_mutants.py`

````python
"""Run the F-5 tests against deliberately broken code (throwaway, not committed).

Usage: python f5_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one file of the copy (one exact, unique replacement), runs the three
F-5 test modules there, prints which tests caught it and restores the file. The
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

WORKSPACE = "documents/workspace.py"
SERVICE = "documents/workspace_service.py"
GUI = "gui.py"
WRITE_THEN_RECORD = (
    "        save_document_package(self.package_path(updated_document.name), updated_document)\n"
    "        self._remember(updated_document)\n"
)
NOT_VETOABLE = (
    "\t\t\t\tif not can_veto:\n"
    '\t\t\t\t\tlogger.error("Failed to save the open document while closing", exc_info=error)\n'
    "\t\t\t\t\treturn True\n"
)
MUTANTS = {
    # D1/D2: the baseline is the record of the last write or load, never the controller.
    "baseline-from-the-controller-copy": (
        SERVICE,
        "        if self._is_saved(updated_document):\n",
        "        if document == updated_document:\n",
    ),
    "record-before-the-write": (
        SERVICE,
        WRITE_THEN_RECORD,
        "        self._remember(updated_document)\n"
        "        save_document_package(self.package_path(updated_document.name), updated_document)\n",
    ),
    "record-despite-a-failed-write": (
        SERVICE,
        WRITE_THEN_RECORD,
        "        try:\n"
        "            save_document_package(self.package_path(updated_document.name), updated_document)\n"
        "        finally:\n"
        "            self._remember(updated_document)\n",
    ),
    "no-fingerprint-check": (
        SERVICE,
        "        return fingerprint is not None and fingerprint == record.fingerprint\n",
        "        return True\n",
    ),
    "fingerprint-without-the-modification-time": (
        SERVICE,
        "    return status.st_size, status.st_mtime_ns\n",
        "    return status.st_size, 0\n",
    ),
    "record-not-encodable": (
        SERVICE,
        "        self._saved[document.name] = _SavedPackage(_encodable(document), fingerprint)\n",
        "        self._saved[document.name] = _SavedPackage(document, fingerprint)\n",
    ),
    # D3: every path that writes, loads or removes a package.
    "load-records-nothing": (SERVICE, "        self._reset_saved(documents)\n", ""),
    "create-records-nothing": (SERVICE, "        self._remember(document)\n        self._controller.add_document(document)\n", "        self._controller.add_document(document)\n"),
    "import-records-nothing": (SERVICE, "            self._remember(document)\n            saved.append(document)\n", "            saved.append(document)\n"),
    "rename-does-not-move-the-record": (SERVICE, "        self._saved.pop(source_name, None)\n        self._remember(renamed)\n", ""),
    "rename-drops-the-record-before-the-move": (
        SERVICE,
        "        renamed = Document(new_name, source.text, source.braille)\n",
        "        renamed = Document(new_name, source.text, source.braille)\n        self._saved.pop(source_name, None)\n",
    ),
    "delete-all-failure-keeps-the-old-records": (SERVICE, "                self._reset_saved(remaining_documents)\n", ""),
    # D4: lone surrogates become U+FFFD wherever a document is prepared or written.
    "prepare-without-the-replacement": (
        WORKSPACE,
        "    return _encodable(Document(name=document.name, text=text, braille=saved_braille))\n",
        "    return Document(name=document.name, text=text, braille=saved_braille)\n",
    ),
    "normalized-without-the-replacement": (
        WORKSPACE,
        "    return _encodable(Document(name=normalize_document_name(document.name), text=document.text, braille=document.braille))\n",
        "    return Document(name=normalize_document_name(document.name), text=document.text, braille=document.braille)\n",
    ),
    "braille-not-replaced": (
        WORKSPACE,
        "    braille = None if document.braille is None else replace_lone_surrogates(document.braille)\n",
        "    braille = document.braille\n",
    ),
    "replacement-through-utf-8": (
        WORKSPACE,
        '    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")\n',
        '    return text.encode("utf-8", "surrogatepass").decode("utf-8", "replace")\n',
    ),
    "replacement-with-a-question-mark": (
        WORKSPACE,
        '    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")\n',
        '    return text.encode("utf-8", "replace").decode("utf-8")\n',
    ),
    # D6/D8/D9: Close after a failed save.
    "close-without-saving-saves-anyway": (GUI, "\t\t\t\tif answer == wx.ID_YES:\n", "\t\t\t\tif answer in (wx.ID_YES, wx.ID_NO):\n"),
    "retry-closes-without-retrying": (
        GUI,
        "\t\t\t\tif answer == wx.ID_YES:\n\t\t\t\t\tcontinue\n",
        "\t\t\t\tif answer == wx.ID_YES:\n\t\t\t\t\treturn True\n",
    ),
    "cancel-closes": (GUI, "\t\t\t\treturn answer == wx.ID_NO\n", "\t\t\t\treturn True\n"),
    "non-vetoable-close-asks": (GUI, NOT_VETOABLE, ""),
    "non-vetoable-close-stays-open": (GUI, NOT_VETOABLE, NOT_VETOABLE.replace("return True", "return False")),
    "close-failure-not-logged": (GUI, "\t\t\t\tself._log_unexpected_save_error(error)\n", ""),
    # D7: the dialog.
    "dialog-without-yes-default": (
        GUI,
        "\t\t\twx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_ERROR,\n",
        "\t\t\twx.YES_NO | wx.CANCEL | wx.ICON_ERROR,\n",
    ),
    "dialog-labels-in-another-order": (
        GUI,
        '\t\t\tdialog.SetYesNoCancelLabels(_("&Retry"), _("Close &Without Saving"), _("Cancel"))\n',
        '\t\t\tdialog.SetYesNoCancelLabels(_("Close &Without Saving"), _("&Retry"), _("Cancel"))\n',
    ),
}
MODULES = ("tests.test_document_workspace", "tests.test_workspace_service", "tests.test_gui_document_flows")
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
        shown = names if len(names) <= 6 else names[:6] + [f"and {len(names) - 6} more"]
        print(f"{mutant}: {len(names)} caught: {', '.join(shown) if names else 'NONE'}")
        if not names:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
````

- [ ] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, catalogs, tree, application data.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n tests.test_atomic_write tests.test_document_controller 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "msgfmt rebuilds the committed .mo byte for byte"
xgettext --version | head -1
git -C $REPO rev-parse HEAD:client
(cd $MAIN/client && find dictionary workspace config.json -type f | sort | xargs -d '\n' sha256sum) > $T/app-data.sha256; wc -l < $T/app-data.sha256
```

Expected (the second block is the three modules F-5 changes, the third the spec's acceptance-criterion-2 set; the last line counts the files of the user's application data in the main checkout, recorded read-only for Task 4; if the user has used the app since the dry run, that number differs, which is fine):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1270 tests
FAILED (errors=1, skipped=7)
Ran 255 tests
OK (skipped=2)
Ran 319 tests
OK (skipped=6)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
source msgids: 353 sha256 24dbc6290122197c04282f665e73ebc3b02b6b4bdef1e072448f91c5c105277c
locales/dotexpress.pot:354
locales/zh_TW/LC_MESSAGES/dotexpress.po:354
353 translated messages.
msgfmt rebuilds the committed .mo byte for byte
xgettext.exe (GNU gettext-tools) 0.23
f244bb8e70a42ce08c98d3145f5c806f9818ac32
3
```

### Task 1: Save lone surrogates as U+FFFD (D4, D5)

The tests that used a lone surrogate as "a save error that is not an `OSError`" get a new injector in this commit, because this commit removes that fault: `zipfile.ZipFile.writestr` raising `ValueError("injected")` for a save, and a `PackageFiles` subclass whose `write` raises it for a rename (a `writestr` patch would fail the save of the open document first). They keep their intent and pass before and after the change. `test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error` keeps its error-box assertions until Task 3 flips it.

- [ ] **Step 1: Red: A1-A5, B17, C10 and the injector changes** (4 spaces). The new tests call `workspace.replace_lone_surrogates` through the module, so each fails on its own instead of the whole module failing to import.

Edit: `client/tests/test_document_workspace.py`

```python

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille="⠃⠗⠇"))

    def test_load_workspace_documents_sorts_valid_documents_and_collects_invalid_paths(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(self.workspace_dir / "Beta.dep", Document(name="Beta", text="b", braille="1"))
```

```python

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille="⠃⠗⠇"))

    def test_replace_lone_surrogates_replaces_each_unpaired_surrogate(self) -> None:
        # F-5 (D4): one U+FFFD per surrogate that is not half of a pair, so UTF-8 can encode it.
        cases = {
            "lone high": ("a\ud800b", "a�b"),
            "lone low": ("a\udc00b", "a�b"),
            "reversed pair": ("a\ude00\ud83db", "a��b"),
            "two highs": ("\ud800\ud800", "��"),
            "high at the end": ("ab\ud83d", "ab�"),
            "surrogate escape": ("x\udcff", "x�"),
        }
        for label, (text, expected) in cases.items():
            with self.subTest(label):
                self.assertEqual(workspace.replace_lone_surrogates(text), expected)

    def test_replace_lone_surrogates_joins_split_pairs_and_keeps_other_text(self) -> None:
        self.assertEqual(workspace.replace_lone_surrogates("a😀b"), "a\U0001f600b")
        for text in ("a\U0001f600b", "中文", "⠁⠃", "tab\tand\nnewline", ""):
            with self.subTest(text=text):
                self.assertIs(workspace.replace_lone_surrogates(text), text)

    def test_prepare_document_for_save_replaces_lone_surrogates(self) -> None:
        kept = prepare_document_for_save(Document("alpha", "old", "⠁"), text="x\ud800", braille="\udc00⠁")
        pending = prepare_document_for_save(Document("alpha", "old", None), text="x\ud800", braille="\udc00")

        self.assertEqual(kept, Document("alpha", "x�", "�⠁"))
        self.assertEqual(pending, Document("alpha", "x�", None))

    def test_load_workspace_documents_sorts_valid_documents_and_collects_invalid_paths(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(self.workspace_dir / "Beta.dep", Document(name="Beta", text="b", braille="1"))
```

Edit: `client/tests/test_document_workspace.py`

```python
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
```

```python
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_failure_that_is_not_an_os_error_keeps_the_existing_package(self) -> None:
        # A bug in the writer (simulated: writestr raises ValueError) while the first or the
        # second member is written. The in-place save had already truncated the package and
        # left a zip without the failing member (invalid at the next start).
        before = self._write_alpha()
        real_writestr = zipfile.ZipFile.writestr
        for failing in (1, 2):
            with self.subTest(failing_member=failing):
                written = []

                def writestr_failing(archive, name, data, *args, **kwargs):
                    written.append(name)
                    if len(written) == failing:
                        raise ValueError("injected")
                    return real_writestr(archive, name, data, *args, **kwargs)

                with patch.object(zipfile.ZipFile, "writestr", writestr_failing):
                    with self.assertRaises(ValueError):
                        save_document_package(self.path, Document("alpha", "edited", "2"))

                self.assertEqual(written, ["alpha.txt", "alpha.brl"][:failing])
                self.assertEqual(self._listing(), ["alpha.dep"])
                self.assertEqual(load_document_package(self.path), self.alpha)
                self.assertEqual(self.path.read_bytes(), before)

    def test_save_replaces_lone_surrogates_with_the_replacement_character(self) -> None:
        # F-5 (D4): a lone surrogate (pasted text) used to make every save fail with
        # "surrogates not allowed"; it is written as U+FFFD (EF BF BD in UTF-8).
        cases = {
            "text": (Document("alpha", "a\ud800", "1"), Document("alpha", "a�", "1"), "alpha.txt", b"a\xef\xbf\xbd"),
            "braille": (
                Document("alpha", "a", "\udc00⠁"),
                Document("alpha", "a", "�⠁"),
                "alpha.brl",
                b"\xef\xbf\xbd\xe2\xa0\x81",
            ),
        }
        for field, (document, expected, member, data) in cases.items():
            with self.subTest(field=field):
                save_document_package(self.path, document)

                self.assertEqual(load_document_package(self.path), expected)
                with zipfile.ZipFile(self.path) as archive:
                    self.assertEqual(archive.read(member), data)
                self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_failure_while_writing_keeps_the_existing_package(self) -> None:
        # A full disk while the second member is written (simulated).
```

Edit: `client/tests/test_document_workspace.py`

```python
    def test_staging_error_that_is_not_an_os_error_keeps_the_old_package(self) -> None:
        before = self._write_alpha()

        with self.assertRaises(UnicodeEncodeError):
            self._move("Alpha", Document("alpha", "\ud800", "1"))

        self.assertEqual(self._listing(), ["Alpha.dep"])
        self.assertEqual(self._path("Alpha").read_bytes(), before)
```

```python
    def test_staging_error_that_is_not_an_os_error_keeps_the_old_package(self) -> None:
        before = self._write_alpha()

        with patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")):
            with self.assertRaises(ValueError):
                self._move("Alpha", Document("alpha", "a", "1"))

        self.assertEqual(self._listing(), ["Alpha.dep"])
        self.assertEqual(self._path("Alpha").read_bytes(), before)
```

Edit: `client/tests/test_document_workspace.py`

```python
            self.assertEqual(sorted(archive.namelist()), ["alpha.brl", "alpha.meta.json", "alpha.txt"])
            self.assertEqual(archive.read("alpha.txt"), b"a")


if __name__ == "__main__":
    unittest.main()
```

```python
            self.assertEqual(sorted(archive.namelist()), ["alpha.brl", "alpha.meta.json", "alpha.txt"])
            self.assertEqual(archive.read("alpha.txt"), b"a")

    def test_staged_package_replaces_lone_surrogates(self) -> None:
        # F-5 (D4): the staged package of a rename goes through the same normalization.
        files = workspace.PackageFiles()
        staged = files.temporary_path(self.workspace_dir, "alpha.dep")
        files.write(staged, Document("alpha", "x\ud800", "1"))
        with zipfile.ZipFile(staged) as archive:
            self.assertEqual(archive.read("alpha.txt"), b"x\xef\xbf\xbd")
        staged.unlink()
        self._write_alpha()

        self._move("Alpha", Document("alpha", "y\udc00", "1"))

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "y�", "1"))


if __name__ == "__main__":
    unittest.main()
```

Edit: `client/tests/test_workspace_service.py`

```python
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

```python
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        service = self._service([Document("alpha", "a", "1")], open_name="alpha")

        with patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")):
            with self.assertRaises(ValueError):
                service.save_open_document(text="edited", braille="1")

        self.assertEqual(self.controller.documents, [Document("alpha", "edited", "1")])
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    def test_save_open_document_replaces_lone_surrogates_in_memory_and_on_disk(self) -> None:
        # F-5 (D4): a pasted lone surrogate used to make every save fail; memory and the
        # package now hold U+FFFD instead.
        service = self._service([Document("alpha", "a", "1")], open_name="alpha")

        saved = service.save_open_document(text="x\ud800", braille="\udc00⠁")

        self.assertEqual(saved, Document("alpha", "x�", "�⠁"))
        self.assertEqual(self.controller.documents, [saved])
        self.assertEqual(self._package("alpha"), saved)

    # --- create ------------------------------------------------------------

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        super().replace(source, destination)


class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
    """Pins today's document flows: disk effects, dialogs, state; must pass unchanged through P1-3.

```

```python
        super().replace(source, destination)


class _FailingWritePackageFiles(PackageFiles):
    """The real file operations, except that writing the staged package raises ``ValueError`` (a bug)."""

    def write(self, path: Path, document: Document) -> None:
        raise ValueError("injected")


class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
    """Pins today's document flows: disk effects, dialogs, state; must pass unchanged through P1-3.

```

Edit: `client/tests/test_gui_document_flows.py`

```python
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
```

```python
        frame.close_converting_dialog.assert_not_called()

    def test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package(self) -> None:
        # F-3 (D9): a bug in the writer (simulated: writestr raises ValueError). The message
        # appears instead of an escaping exception; the package keeps its bytes and memory
        # keeps the edit.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("x edited")

        with patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")):
            self.assertFalse(frame._save_open_document_with_feedback())

        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "x edited", "1")])

    def test_pasted_lone_surrogate_is_saved_as_replacement_character(self) -> None:
        # F-5 (D4, D5): the save succeeds without a message; memory and the package hold
        # U+FFFD, and the editor keeps what the user pasted until the document is reopened.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("x\ud800")

        self.assertTrue(frame._save_open_document_with_feedback())

        self.assertEqual(self.events, [])
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "x�", "1")])
        self.assertEqual(self._package("alpha"), Document("alpha", "x�", "1"))
        self.assertEqual(frame.input_txt.value, "x\ud800")

    def test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error(self) -> None:
        # Before F-3 the exception escaped _on_close: no message, and the window neither
```

Edit: `client/tests/test_gui_document_flows.py`

```python
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

```python
        self._write_packages(alpha)
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("edited")
        event = Mock()
        event.CanVeto.return_value = True

        with patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")):
            frame._on_close(event)

        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    # --- rename ------------------------------------------------------------
```

Edit: `client/tests/test_gui_document_flows.py`

```python
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

```python
        self.assertEqual(beta_path.read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)

    def _rename_frame_whose_staged_write_fails(self) -> gui.BrailleFrame:
        """alpha open, beta selected; writing the staged package of a rename raises ``ValueError``."""
        alpha = Document("alpha", "a", "1")
        beta = Document("beta", "b", "2")
        self._write_packages(alpha, beta)
        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
        frame._workspace_service = DocumentWorkspaceService(
            frame._document_controller,
            self.workspace,
            package_files=_FailingWritePackageFiles(),
        )
        self.names = ["gamma"]
        return frame

    def test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state(self) -> None:
        # F-3 (D9): renaming the non-open beta while the staged write raises (a bug).
        frame = self._rename_frame_whose_staged_write_fails()
        beta_bytes = (self.workspace / "beta.dep").read_bytes()
        before = self._state(frame)

        frame.on_rename_document(None)

        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "injected", frame)
        self.assertEqual((self.workspace / "beta.dep").read_bytes(), beta_bytes)
        self.assertEqual(self._state(frame), before)

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("x\ud800")

        with self.assertLogs(gui.logger, level="ERROR") as logs:
            self.assertFalse(frame._save_open_document_with_feedback())

        self._assert_logged_with_traceback(logs, UnicodeEncodeError)
        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "surrogates not allowed", frame)

    def test_add_failure_that_is_not_an_os_error_is_logged_with_its_traceback(self) -> None:
        alpha = Document("alpha", "a", "1")
```

```python
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
        frame.input_txt.SetValue("x edited")

        with (
            patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")),
            self.assertLogs(gui.logger, level="ERROR") as logs,
        ):
            self.assertFalse(frame._save_open_document_with_feedback())

        self._assert_logged_with_traceback(logs, ValueError)
        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)

    def test_add_failure_that_is_not_an_os_error_is_logged_with_its_traceback(self) -> None:
        alpha = Document("alpha", "a", "1")
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "boom", frame)

    def test_rename_failure_that_is_not_an_os_error_is_logged_with_its_traceback(self) -> None:
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha, Document("beta", "b", "2"))
        frame = self._make_workspace_frame([alpha, Document("beta", "\ud800", "2")], open_name="alpha", selected_name="beta")
        self.names = ["gamma"]

        with self.assertLogs(gui.logger, level="ERROR") as logs:
            frame.on_rename_document(None)

        self._assert_logged_with_traceback(logs, UnicodeEncodeError)
        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "surrogates not allowed", frame)

    def test_save_failure_from_an_os_error_is_not_logged(self) -> None:
        # Locked, read-only or full disks are expected; the message box already
```

```python
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "boom", frame)

    def test_rename_failure_that_is_not_an_os_error_is_logged_with_its_traceback(self) -> None:
        frame = self._rename_frame_whose_staged_write_fails()

        with self.assertLogs(gui.logger, level="ERROR") as logs:
            frame.on_rename_document(None)

        self._assert_logged_with_traceback(logs, ValueError)
        self.assertEqual(len(self.events), 2)
        self._assert_error_box(self.events[1], "Failed to save document: {error}", "injected", frame)

    def test_save_failure_from_an_os_error_is_not_logged(self) -> None:
        # Locked, read-only or full disks are expected; the message box already
```

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (the seven new tests fail: the function is missing, or the write raises `UnicodeEncodeError`, or `prepare_document_for_save` keeps the surrogate; every changed test passes on today's code):

```text
ERROR: test_save_replaces_lone_surrogates_with_the_replacement_character (tests.test_document_workspace.AtomicSaveDocumentPackageTest.test_save_replaces_lone_su
UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 1: surrogates not allowed
UnicodeEncodeError: 'utf-8' codec can't encode character '\udc00' in position 0: surrogates not allowed
ERROR: test_replace_lone_surrogates_joins_split_pairs_and_keeps_other_text (tests.test_document_workspace.DocumentWorkspaceTest.test_replace_lone_surrogates_joi
AttributeError: module 'documents.workspace' has no attribute 'replace_lone_surrogates'
ERROR: test_replace_lone_surrogates_replaces_each_unpaired_surrogate (tests.test_document_workspace.DocumentWorkspaceTest.test_replace_lone_surrogates_replaces_
ERROR: test_staged_package_replaces_lone_surrogates (tests.test_document_workspace.MoveDocumentPackageTest.test_staged_package_replaces_lone_surrogates)
ERROR: test_save_open_document_replaces_lone_surrogates_in_memory_and_on_disk (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_save_open_document
FAIL: test_prepare_document_for_save_replaces_lone_surrogates (tests.test_document_workspace.DocumentWorkspaceTest.test_prepare_document_for_save_replaces_lone_
AssertionError: Document(name='alpha', text='x\ud800', braille='\udc00⠁') != Document(name='alpha', text='x�', braille='�⠁')
FAIL: test_pasted_lone_surrogate_is_saved_as_replacement_character (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_pasted_lone_su
AssertionError: False is not true
Ran 262 tests
FAILED (failures=2, errors=11, skipped=2)
```

- [ ] **Step 2: Replace lone surrogates in the documents layer** (`client/documents/workspace.py`, 4 spaces). `_normalized` is the one path of every package writer (Save, Add, Import, the staged package of a rename, Export as DEP); `prepare_document_for_save` makes the controller copy, the comparison of Task 2 and the record hold the replaced text.

Edit: `client/documents/workspace.py`

```python
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
```

```python
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
```

Edit: `client/documents/workspace.py`

```python
BRL_EXTENSION = ".brl"
PENDING_METADATA_SUFFIX = ".meta.json"
DEFAULT_DOCUMENT_NAME = "new"


@dataclass(frozen=True)
```

```python
BRL_EXTENSION = ".brl"
PENDING_METADATA_SUFFIX = ".meta.json"
DEFAULT_DOCUMENT_NAME = "new"
_LONE_SURROGATE = re.compile(r"[\ud800-\udfff]")


@dataclass(frozen=True)
```

Edit: `client/documents/workspace.py`

```python
    return Path(workspace_dir) / f"{name}{DEP_EXTENSION}"


def _normalized(document: Document) -> Document:
    return Document(name=normalize_document_name(document.name), text=document.text, braille=document.braille)


def _write_package(stream: BinaryIO, document: Document, *, include_pending_metadata: bool) -> None:
```

```python
    return Path(workspace_dir) / f"{name}{DEP_EXTENSION}"


def replace_lone_surrogates(text: str) -> str:
    """Replace every unpaired UTF-16 surrogate with U+FFFD so the text can be encoded as UTF-8; a split pair is joined."""
    if _LONE_SURROGATE.search(text) is None:
        return text
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def _encodable(document: Document) -> Document:
    """``document`` with lone surrogates replaced in its text and braille (F-5); pending braille stays ``None``."""
    braille = None if document.braille is None else replace_lone_surrogates(document.braille)
    return Document(name=document.name, text=replace_lone_surrogates(document.text), braille=braille)


def _normalized(document: Document) -> Document:
    return _encodable(Document(name=normalize_document_name(document.name), text=document.text, braille=document.braille))


def _write_package(stream: BinaryIO, document: Document, *, include_pending_metadata: bool) -> None:
```

Edit: `client/documents/workspace.py`

```python
    braille: str,
) -> Document:
    saved_braille = None if document.braille is None else braille
    return Document(name=document.name, text=text, braille=saved_braille)


def load_workspace_documents(workspace_dir: Path) -> tuple[list[Document], list[Path]]:
```

```python
    braille: str,
) -> Document:
    saved_braille = None if document.braille is None else braille
    return _encodable(Document(name=document.name, text=text, braille=saved_braille))


def load_workspace_documents(workspace_dir: Path) -> tuple[list[Document], list[Path]]:
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(replace_lone_surrogates|prepare_document_for_save_replaces|save_replaces_lone|staged_package_replaces|save_open_document_replaces|pasted_lone_surrogate|save_failure_that_is_not_an_os_error|staging_error_that_is_not|save_failure_keeps_the_package|close_vetoes_and_keeps|rename_failure_that_is_not)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (the 7 new and the 8 changed tests pass):

```text
test_save_failure_that_is_not_an_os_error_keeps_the_existing_package ok
test_save_replaces_lone_surrogates_with_the_replacement_character ok
test_prepare_document_for_save_replaces_lone_surrogates ok
test_replace_lone_surrogates_joins_split_pairs_and_keeps_other_text ok
test_replace_lone_surrogates_replaces_each_unpaired_surrogate ok
test_staged_package_replaces_lone_surrogates ok
test_staging_error_that_is_not_an_os_error_keeps_the_old_package ok
test_save_failure_keeps_the_package_and_updates_memory ok
test_save_open_document_replaces_lone_surrogates_in_memory_and_on_disk ok
test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error ok
test_pasted_lone_surrogate_is_saved_as_replacement_character ok
test_rename_failure_that_is_not_an_os_error_is_logged_with_its_traceback ok
test_rename_failure_that_is_not_an_os_error_shows_the_message_and_keeps_state ok
test_save_failure_that_is_not_an_os_error_is_logged_with_its_traceback ok
test_save_failure_that_is_not_an_os_error_shows_the_message_and_keeps_the_package ok
Ran 262 tests
OK (skipped=2)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1277 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/documents/workspace.py client/tests/test_document_workspace.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -m "fix: save lone surrogates as U+FFFD (F-5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
855670fe907c9634a341451694c79635a02ebd61
```

### Task 2: Skip saving an unchanged document (D1-D3)

- [ ] **Step 1: Red: B1-B16 and C1-C4** (4 spaces). `SaveOnlyWhenChangedTest` starts every test from `load_documents()`; "written" counts the calls of the service's `save_document_package` (`patch.object(..., wraps=...)`), "unchanged" compares the package bytes and `st_mtime_ns`. The GUI tests start from `_load_workspace_documents_at_startup()` and never patch `documents.*` globals: a refused write is `os.replace` raising, and "not written" is `os.replace` not called plus the package bytes and `st_mtime_ns`.

Edit: `client/tests/test_workspace_service.py`

```python
from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.windows_file_handles import SHARE_DELETE, SHARE_MODES, hold_open

SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"

```

```python
from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.windows_file_handles import SHARE_DELETE, SHARE_MODES, hold_open, make_read_only

SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"

```

Edit: `client/tests/test_workspace_service.py`

```python
        self.assertEqual(self.controller.documents, documents)


if __name__ == "__main__":
    unittest.main()
```

```python
        self.assertEqual(self.controller.documents, documents)


class SaveOnlyWhenChangedTest(unittest.TestCase):
    """Save writes only when the open document differs from its last write or load (F-5, D1-D3).

    Each test starts from ``load_documents()`` of a workspace with alpha ("a", "1") and the
    pending beta ("b"), with alpha open. "Written" counts the calls of the service's
    ``save_document_package``; "unchanged" compares the package bytes and ``st_mtime_ns``.
    """

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self._start("workspace")

    def _start(self, folder: str, *, package_files=None) -> None:
        self.workspace = self.root / folder
        for document in (Document("alpha", "a", "1"), Document("beta", "b", None)):
            save_document_package(self.workspace / f"{document.name}.dep", document)
        self.controller = DocumentController()
        if package_files is None:
            self.service = DocumentWorkspaceService(self.controller, self.workspace)
        else:
            self.service = DocumentWorkspaceService(self.controller, self.workspace, package_files=package_files)
        self.assertEqual(self.service.load_documents(), [])
        self.controller.open_document("alpha")

    def _path(self, name: str = "alpha") -> Path:
        return self.workspace / f"{name}.dep"

    def _disk(self, name: str = "alpha") -> tuple[bytes, int]:
        return self._path(name).read_bytes(), self._path(name).stat().st_mtime_ns

    def _save(self, text: str = "a", braille: str = "1") -> int:
        """Save the open document from these editor values; return how many packages were written."""
        with patch.object(workspace_service, "save_document_package", wraps=workspace_service.save_document_package) as save:
            self.service.save_open_document(text=text, braille=braille)
        return save.call_count

    def _fail_save(self, text: str) -> None:
        """A save of ``text`` whose write fails (``os.replace`` refused); memory takes ``text``."""
        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")):
            with self.assertRaises(PermissionError):
                self.service.save_open_document(text=text, braille="1")
        self.assertEqual(self.controller.get_document("alpha"), Document("alpha", text, "1"))

    def test_unchanged_document_is_not_written(self) -> None:
        before = self._disk()

        self.assertEqual(self._save(), 0)

        self.assertEqual(self._disk(), before)
        self.assertEqual(self.controller.get_document("alpha"), Document("alpha", "a", "1"))

    def test_changed_text_is_written(self) -> None:
        self.assertEqual(self._save(text="edited"), 1)

        self.assertEqual(load_document_package(self._path()), Document("alpha", "edited", "1"))

    def test_changed_braille_is_written(self) -> None:
        self.assertEqual(self._save(braille="2"), 1)

        self.assertEqual(load_document_package(self._path()), Document("alpha", "a", "2"))

    def test_converted_pending_document_is_written(self) -> None:
        # Conversion replaces the pending document in memory with its braille and writes
        # nothing (ConversionPresenter._complete_manual); the next save must write it.
        self.controller.open_document("beta")
        self.assertEqual(self._save(text="b", braille="ignored while pending"), 0)
        self.controller.replace_document(Document("beta", "b", "⠃"))

        self.assertEqual(self._save(text="b", braille="⠃"), 1)

        self.assertEqual(load_document_package(self._path("beta")), Document("beta", "b", "⠃"))
        with zipfile.ZipFile(self._path("beta")) as archive:
            self.assertEqual(sorted(archive.namelist()), ["beta.brl", "beta.txt"])

    def test_failed_save_is_retried_by_the_next_save(self) -> None:
        # The must-have case. Memory is updated before the write, so a baseline taken from
        # the controller, or a record updated before or despite the failed write, would
        # skip this retry and lose the edit.
        before = self._disk()
        self._fail_save("edited")
        self.assertEqual(self._disk(), before)

        self.assertEqual(self._save(text="edited"), 1)

        self.assertEqual(load_document_package(self._path()), Document("alpha", "edited", "1"))

    def test_reverting_after_a_failed_save_is_not_written(self) -> None:
        before = self._disk()
        self._fail_save("edited")

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")):
            self.assertEqual(self._save(text="a"), 0)

        self.assertEqual(self._disk(), before)
        self.assertEqual(self.controller.get_document("alpha"), Document("alpha", "a", "1"))

    def test_lone_surrogate_text_is_saved_once(self) -> None:
        # The editor keeps the surrogate (D5); each save replaces it again and then
        # matches what was written.
        self.assertEqual(self._save(text="x\ud800"), 1)
        before = self._disk()

        self.assertEqual(self._save(text="x\ud800"), 0)

        self.assertEqual(self._disk(), before)
        self.assertEqual(load_document_package(self._path()), Document("alpha", "x�", "1"))

    def test_package_removed_on_disk_is_written_again(self) -> None:
        self._path().unlink()

        self.assertEqual(self._save(), 1)

        self.assertEqual(load_document_package(self._path()), Document("alpha", "a", "1"))

    def test_package_replaced_on_disk_is_written_again(self) -> None:
        # Another program replaced the package; the unchanged document is written back,
        # as every save did before F-5.
        for replaced in ("other size", "same bytes, other time"):
            with self.subTest(replaced=replaced):
                if replaced == "other size":
                    save_document_package(self._path(), Document("alpha", "written by another program", "1"))
                else:
                    status = self._path().stat()
                    os.utime(self._path(), ns=(status.st_atime_ns, status.st_mtime_ns + 2_000_000_000))

                self.assertEqual(self._save(), 1)

                self.assertEqual(load_document_package(self._path()), Document("alpha", "a", "1"))

    def test_document_without_a_record_is_written(self) -> None:
        # A controller filled without the service has no record: every save writes.
        self.controller = DocumentController(documents=[Document("alpha", "a", "1")], open_name="alpha")
        self.service = DocumentWorkspaceService(self.controller, self.workspace)

        self.assertEqual(self._save(), 1)

    def test_created_document_is_not_written_again(self) -> None:
        # The record holds what was written: a lone surrogate as U+FFFD (D3), so the
        # editor's unchanged text compares equal after its own replacement.
        cases = (Document("gamma", "", ""), Document("new", "", None), Document("delta", "x\ud800", "\udc00"))
        for document in cases:
            with self.subTest(name=document.name):
                self.service.create_document(document)
                self.controller.open_document(document.name)
                before = self._disk(document.name)

                self.assertEqual(self._save(text=document.text, braille=document.braille or ""), 0)

                self.assertEqual(self._disk(document.name), before)

    def test_imported_document_is_not_written_again(self) -> None:
        source = self.root / "delta.txt"
        source.write_text("d", encoding="utf-8")
        result = self.service.import_files([source], format_key="all")
        self.assertEqual(result.saved, [Document("delta", "d", None)])
        self.controller.open_document("delta")
        before = self._disk("delta")

        self.assertEqual(self._save(text="d", braille=""), 0)

        self.assertEqual(self._disk("delta"), before)

    def test_renamed_document_is_not_written_again(self) -> None:
        for new_name in ("gamma", "Alpha"):
            with self.subTest(new_name=new_name):
                self._start(f"rename-to-{new_name.lower()}")
                self.assertEqual(self.service.rename_document("alpha", new_name), Document(new_name, "a", "1"))
                self.assertEqual(self.controller.open_name, new_name)
                before = self._disk(new_name)

                self.assertEqual(self._save(), 0)

                self.assertEqual(self._disk(new_name), before)

    def test_failed_rename_keeps_the_record_of_the_old_name(self) -> None:
        self._start("failing-rename", package_files=_FailingReplacePackageFiles(source_name="alpha.dep"))
        with self.assertRaises(PermissionError):
            self.service.rename_document("alpha", "gamma")
        before = self._disk()

        self.assertEqual(self._save(), 0)

        self.assertEqual(self._disk(), before)

    def test_deleted_then_created_document_is_written(self) -> None:
        self.service.delete_document("beta")
        self.service.create_document(Document("beta", "", ""))
        self.controller.open_document("beta")

        self.assertEqual(self._save(text="b edited", braille=""), 1)

        self.assertEqual(load_document_package(self._path("beta")), Document("beta", "b edited", ""))

    def test_documents_reloaded_after_a_failed_delete_all_are_not_written_again(self) -> None:
        # A controller filled without the service (no record): only the reload after the
        # failed Delete All can record zoo. beta.dep is a folder, so its unlink fails.
        self.workspace = self.root / "delete-all"
        save_document_package(self._path("alpha"), Document("alpha", "a", "1"))
        save_document_package(self._path("zoo"), Document("zoo", "z", "3"))
        (self._path("beta") / "keep").mkdir(parents=True)
        self.controller = DocumentController(
            documents=[Document("alpha", "a", "1"), Document("beta", "b", "2"), Document("zoo", "z", "3")]
        )
        self.service = DocumentWorkspaceService(self.controller, self.workspace)
        errors: list[OSError] = []

        result = self.service.delete_all_documents(on_error=errors.append)

        self.assertFalse(result.completed)
        self.assertEqual(len(errors), 1)
        self.assertEqual(self.controller.documents, [Document("zoo", "z", "3")])
        self.controller.open_document("zoo")
        before = self._disk("zoo")
        self.assertEqual(self._save(text="z", braille="3"), 0)
        self.assertEqual(self._disk("zoo"), before)

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes and read-only attribute")
    def test_unchanged_unwritable_package_saves_without_error(self) -> None:
        # F-W10: each of these made every save fail, so every action and Close were blocked.
        before = self._disk()
        for label, share in SHARE_MODES:
            with self.subTest(fault=f"held open, share {label}"):
                release = hold_open(self, self._path(), share)
                try:
                    self.assertEqual(self._save(), 0)
                finally:
                    release()

                self.assertEqual(self._disk(), before)
        with self.subTest(fault="read-only"):
            make_read_only(self, self._path())

            self.assertEqual(self._save(), 0)

            self.assertEqual(self._disk(), before)


if __name__ == "__main__":
    unittest.main()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    # --- rename ------------------------------------------------------------

```

```python
        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    # --- save only when changed (F-5) ----------------------------------------

    def _start_with_alpha_and_beta(self) -> gui.BrailleFrame:
        """Packages alpha ("a", "1") and beta ("b", "2") loaded at startup; alpha is open."""
        self._write_packages(Document("alpha", "a", "1"), Document("beta", "b", "2"))
        frame = self._make_workspace_frame()
        frame._load_workspace_documents_at_startup()
        self.assertEqual(frame._document_controller.open_name, "alpha")
        self.events.clear()
        return frame

    def _disk(self, name: str = "alpha") -> tuple[bytes, int]:
        path = self.workspace / f"{name}.dep"
        return path.read_bytes(), path.stat().st_mtime_ns

    def _vetoable_close(self) -> Mock:
        event = Mock()
        event.CanVeto.return_value = True
        return event

    def test_switch_from_an_unchanged_document_whose_save_would_fail_opens_the_next(self) -> None:
        # F-W10: before F-5 the unchanged document was rewritten, the write failed, and the
        # error box blocked the switch.
        frame = self._start_with_alpha_and_beta()
        before = self._disk()

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace:
            frame._open_adjacent_document(1)

        replace.assert_not_called()
        self.assertEqual(frame._document_controller.open_name, "beta")
        self.assertEqual(frame.input_txt.value, "b")
        self.assertEqual([item for item in self.events if item[0] != "title"], [("focus", "input")])
        self.assertEqual(self._disk(), before)

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_unchanged_read_only_document_blocks_neither_switch_nor_close(self) -> None:
        frame = self._start_with_alpha_and_beta()
        make_read_only(self, self.workspace / "alpha.dep")
        before = self._disk()
        event = self._vetoable_close()

        frame._open_adjacent_document(1)
        frame._open_adjacent_document(1)
        frame._on_close(event)

        self.assertEqual(frame._document_controller.open_name, "alpha")
        self.assertEqual([item[0] for item in self.events if item[0] not in ("title", "focus")], [])
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        self.assertEqual(self._disk(), before)

    def test_switch_from_a_changed_document_whose_save_fails_still_blocks(self) -> None:
        # Decision C: an action whose save really writes and fails is still blocked.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")):
            frame._open_adjacent_document(1)

        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)
        self.assertEqual(frame._document_controller.open_name, "alpha")
        self.assertEqual(frame._document_controller.get_document("alpha"), Document("alpha", "a edited", "1"))
        self.assertEqual(frame.input_txt.value, "a edited")
        self.assertEqual(self._disk(), before)

    def test_close_with_an_unchanged_document_whose_save_would_fail_closes(self) -> None:
        frame = self._start_with_alpha_and_beta()
        before = self._disk()
        event = self._vetoable_close()

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace:
            frame._on_close(event)

        replace.assert_not_called()
        self.assertEqual(self.events, [])
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        frame.close_converting_dialog.assert_called_once_with()
        self.assertEqual(self._disk(), before)

    # --- rename ------------------------------------------------------------

```

```bash
$PY -m unittest tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (13 red: today every save writes, so "not written" fails, and an unwritable package raises; the 8 tests of written cases already pass):

```text
ERROR: test_reverting_after_a_failed_save_is_not_written (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_reverting_after_a_failed_save_is_not_written
PermissionError: [Errno 13] injected
ERROR: test_unchanged_unwritable_package_saves_without_error (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_unchanged_unwritable_package_saves_witho
PermissionError: [WinError 5] 存取被拒。: '<tmp>\\workspace\\.alpha.dep.<rnd>.tmp' -> '<tmp>\\workspace\\alpha.dep'
PermissionError: [Errno 13] Permission denied: '<tmp>\\workspace\\alpha.dep'
FAIL: test_converted_pending_document_is_written (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_converted_pending_document_is_written)
AssertionError: 1 != 0
FAIL: test_created_document_is_not_written_again (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_created_document_is_not_written_again) (name='gamma'
FAIL: test_created_document_is_not_written_again (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_created_document_is_not_written_again) (name='new')
FAIL: test_created_document_is_not_written_again (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_created_document_is_not_written_again) (name='delta'
FAIL: test_documents_reloaded_after_a_failed_delete_all_are_not_written_again (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_documents_reloaded_afte
FAIL: test_failed_rename_keeps_the_record_of_the_old_name (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_failed_rename_keeps_the_record_of_the_old_n
FAIL: test_imported_document_is_not_written_again (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_imported_document_is_not_written_again)
FAIL: test_lone_surrogate_text_is_saved_once (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_lone_surrogate_text_is_saved_once)
FAIL: test_renamed_document_is_not_written_again (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_renamed_document_is_not_written_again) (new_name='ga
FAIL: test_renamed_document_is_not_written_again (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_renamed_document_is_not_written_again) (new_name='Al
FAIL: test_unchanged_document_is_not_written (tests.test_workspace_service.SaveOnlyWhenChangedTest.test_unchanged_document_is_not_written)
FAIL: test_close_with_an_unchanged_document_whose_save_would_fail_closes (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_wi
AssertionError: Expected 'replace' to not have been called. Called 1 times.
FAIL: test_switch_from_an_unchanged_document_whose_save_would_fail_opens_the_next (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test
FAIL: test_unchanged_read_only_document_blocks_neither_switch_nor_close (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_unchanged
AssertionError: Lists differ: ['MessageBox', 'MessageBox', 'MessageBox'] != []
Ran 230 tests
FAILED (failures=14, errors=6)
```

- [ ] **Step 2: The saved record** (`client/documents/workspace_service.py`, 4 spaces). `_is_saved` is D2; `_remember` stores what `_normalized` writes (`_encodable`) with the package's `(st_size, st_mtime_ns)` right after the write or load; the record changes only after the disk effect succeeded (D3).

Edit: `client/documents/workspace_service.py`

```python
aside before installing it (``move_document_package``): a failure leaves exactly the
old package, and a case-only rename (``Alpha`` to ``alpha``) is safe on a
case-insensitive file system, where both names are the same file.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from documents.controller import DocumentController
from documents.session import DeleteDocumentDecision
```

```python
aside before installing it (``move_document_package``): a failure leaves exactly the
old package, and a case-only rename (``Alpha`` to ``alpha``) is safe on a
case-insensitive file system, where both names are the same file.
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

from documents.controller import DocumentController
from documents.session import DeleteDocumentDecision
```

Edit: `client/documents/workspace_service.py`

```python
    BatchIssue,
    Document,
    PackageFiles,
    batch_import_documents,
    document_package_path_for_name,
    ensure_workspace_directory,
```

```python
    BatchIssue,
    Document,
    PackageFiles,
    _encodable,
    batch_import_documents,
    document_package_path_for_name,
    ensure_workspace_directory,
```

Edit: `client/documents/workspace_service.py`

```python
    invalid_paths: list[Path]


class DocumentWorkspaceService:
    def __init__(
        self,
```

```python
    invalid_paths: list[Path]


@dataclass(frozen=True)
class _SavedPackage:
    """What was last written to or loaded from a package, and the package's fingerprint then."""

    document: Document
    fingerprint: tuple[int, int] | None


def _package_fingerprint(path: Path) -> tuple[int, int] | None:
    """``(st_size, st_mtime_ns)`` of the regular file at ``path``, or ``None`` if there is none."""
    try:
        status = os.stat(path)
    except OSError:
        return None
    if not stat.S_ISREG(status.st_mode):
        return None
    return status.st_size, status.st_mtime_ns


class DocumentWorkspaceService:
    def __init__(
        self,
```

Edit: `client/documents/workspace_service.py`

```python
        self._controller = controller
        self._workspace_dir = Path(workspace_dir)
        self._package_files = package_files or PackageFiles()

    @property
    def workspace_dir(self) -> Path:
```

```python
        self._controller = controller
        self._workspace_dir = Path(workspace_dir)
        self._package_files = package_files or PackageFiles()
        self._saved: dict[str, _SavedPackage] = {}

    @property
    def workspace_dir(self) -> Path:
```

Edit: `client/documents/workspace_service.py`

```python
    def package_path(self, name: str) -> Path:
        return document_package_path_for_name(name, self._workspace_dir)

    def load_documents(self) -> list[Path]:
        ensure_workspace_directory(self._workspace_dir)
        documents, invalid_paths = load_workspace_documents(self._workspace_dir)
        self._controller.load_documents(documents)
        return invalid_paths

    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None:
```

```python
    def package_path(self, name: str) -> Path:
        return document_package_path_for_name(name, self._workspace_dir)

    def _remember(self, document: Document) -> None:
        """Record ``document`` as its package holds it now, right after a write or a load."""
        fingerprint = _package_fingerprint(self.package_path(document.name))
        self._saved[document.name] = _SavedPackage(_encodable(document), fingerprint)

    def _is_saved(self, document: Document) -> bool:
        """Whether the package already holds ``document`` (F-5 D2); when in doubt, ``False``."""
        record = self._saved.get(document.name)
        if record is None or record.document != document:
            return False
        fingerprint = _package_fingerprint(self.package_path(document.name))
        return fingerprint is not None and fingerprint == record.fingerprint

    def _reset_saved(self, documents: Iterable[Document]) -> None:
        self._saved = {}
        for document in documents:
            self._remember(document)

    def load_documents(self) -> list[Path]:
        ensure_workspace_directory(self._workspace_dir)
        documents, invalid_paths = load_workspace_documents(self._workspace_dir)
        self._controller.load_documents(documents)
        self._reset_saved(documents)
        return invalid_paths

    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None:
```

Edit: `client/documents/workspace_service.py`

```python
            return None
        updated_document = prepare_document_for_save(document, text=text, braille=braille)
        self._controller.replace_document(updated_document)
        save_document_package(self.package_path(updated_document.name), updated_document)
        return updated_document

    def create_document(self, document: Document) -> None:
        save_document_package(self.package_path(document.name), document)
        self._controller.add_document(document)

    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult:
```

```python
            return None
        updated_document = prepare_document_for_save(document, text=text, braille=braille)
        self._controller.replace_document(updated_document)
        if self._is_saved(updated_document):
            return updated_document
        save_document_package(self.package_path(updated_document.name), updated_document)
        self._remember(updated_document)
        return updated_document

    def create_document(self, document: Document) -> None:
        save_document_package(self.package_path(document.name), document)
        self._remember(document)
        self._controller.add_document(document)

    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult:
```

Edit: `client/documents/workspace_service.py`

```python
            except Exception as exc:
                save_issues.append(BatchIssue(path=package_path, reason=str(exc)))
                continue
            saved.append(document)
        self._controller.add_documents(saved)
        return ImportResult(saved=saved, issues=load_issues + save_issues)
```

```python
            except Exception as exc:
                save_issues.append(BatchIssue(path=package_path, reason=str(exc)))
                continue
            self._remember(document)
            saved.append(document)
        self._controller.add_documents(saved)
        return ImportResult(saved=saved, issues=load_issues + save_issues)
```

Edit: `client/documents/workspace_service.py`

```python
        source = self._controller.get_document(source_name)
        if source is None:
            return None
        move_document_package(
            self.package_path(source_name),
            self.package_path(new_name),
            Document(new_name, source.text, source.braille),
            files=self._package_files,
        )
        return self._controller.rename_document(source_name, new_name)

    def delete_document(self, name: str) -> DeleteDocumentDecision:
        package_path = self.package_path(name)
        if package_path.exists():
            package_path.unlink()
        return self._controller.delete_document(name)

    def delete_all_documents(self, *, on_error: Callable[[OSError], None]) -> DeleteAllResult:
```

```python
        source = self._controller.get_document(source_name)
        if source is None:
            return None
        renamed = Document(new_name, source.text, source.braille)
        move_document_package(
            self.package_path(source_name),
            self.package_path(new_name),
            renamed,
            files=self._package_files,
        )
        self._saved.pop(source_name, None)
        self._remember(renamed)
        return self._controller.rename_document(source_name, new_name)

    def delete_document(self, name: str) -> DeleteDocumentDecision:
        package_path = self.package_path(name)
        if package_path.exists():
            package_path.unlink()
        self._saved.pop(name, None)
        return self._controller.delete_document(name)

    def delete_all_documents(self, *, on_error: Callable[[OSError], None]) -> DeleteAllResult:
```

Edit: `client/documents/workspace_service.py`

```python
                on_error(exc)
                remaining_documents, invalid_paths = load_workspace_documents(self._workspace_dir)
                self._controller.restore_documents_after_delete_all_failure(remaining_documents)
                return DeleteAllResult(completed=False, invalid_paths=invalid_paths)
        self._controller.delete_all_documents()
        return DeleteAllResult(completed=True, invalid_paths=[])
```

```python
                on_error(exc)
                remaining_documents, invalid_paths = load_workspace_documents(self._workspace_dir)
                self._controller.restore_documents_after_delete_all_failure(remaining_documents)
                self._reset_saved(remaining_documents)
                return DeleteAllResult(completed=False, invalid_paths=invalid_paths)
        self._saved = {}
        self._controller.delete_all_documents()
        return DeleteAllResult(completed=True, invalid_paths=[])
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(unchanged_document_is_not|changed_text_is|changed_braille_is|converted_pending|failed_save_is_retried|reverting_after|lone_surrogate_text_is|package_removed_on_disk|package_replaced_on_disk|document_without_a_record|created_document_is_not|imported_document_is_not|renamed_document_is_not|failed_rename_keeps|deleted_then_created|documents_reloaded_after|unchanged_unwritable_package|switch_from_an_unchanged|unchanged_read_only_document|switch_from_a_changed|close_with_an_unchanged)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (21 new tests; the two Windows-only ones ran):

```text
test_changed_braille_is_written ok
test_changed_text_is_written ok
test_converted_pending_document_is_written ok
test_created_document_is_not_written_again ok
test_deleted_then_created_document_is_written ok
test_document_without_a_record_is_written ok
test_documents_reloaded_after_a_failed_delete_all_are_not_written_again ok
test_failed_rename_keeps_the_record_of_the_old_name ok
test_failed_save_is_retried_by_the_next_save ok
test_imported_document_is_not_written_again ok
test_lone_surrogate_text_is_saved_once ok
test_package_removed_on_disk_is_written_again ok
test_package_replaced_on_disk_is_written_again ok
test_renamed_document_is_not_written_again ok
test_reverting_after_a_failed_save_is_not_written ok
test_unchanged_document_is_not_written ok
test_unchanged_unwritable_package_saves_without_error ok
test_close_with_an_unchanged_document_whose_save_would_fail_closes ok
test_switch_from_a_changed_document_whose_save_fails_still_blocks ok
test_switch_from_an_unchanged_document_whose_save_would_fail_opens_the_next ok
test_unchanged_read_only_document_blocks_neither_switch_nor_close ok
Ran 283 tests
OK (skipped=2)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1298 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/documents/workspace_service.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -m "fix: skip saving an unchanged document (F-5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
5d36ba64348a3928bbd7f2a9ba5193823c251815
```

### Task 3: Offer Retry or Close without saving when saving fails on Close (D6-D9, D12)

- [ ] **Step 1: Red: the stub ids, the fake dialog, C5-C9, C11, the flips** (4 spaces). The fake `wx.MessageDialog` records `("MessageDialog", message, caption, style, extended message, (yes, no, cancel) labels, parent)` when it is shown and answers from `self.dialog_answers` (Cancel when empty). `_assert_close_dialogs` compares the event kinds first, so a red run prints the kinds instead of a frame's memory address.

Edit: `client/tests/wx_stub.py`

```python
            return ""

    class _MessageDialog(Dialog):
        pass

    wx.Window = Window
    wx.Frame = Frame
```

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

Edit: `client/tests/wx_stub.py`

```python
    wx.ID_ABOUT = 1
    wx.ID_OK = 2
    wx.ID_EDIT = 5030
    wx.OK = 4
    wx.CANCEL = 8
    wx.YES = 1
    wx.NO = 0
    wx.YES_NO = 16
    wx.NO_DEFAULT = 32
    wx.ICON_ERROR = 512
    wx.ICON_INFORMATION = 128
    wx.ICON_WARNING = 256
```

```python
    wx.ID_ABOUT = 1
    wx.ID_OK = 2
    wx.ID_EDIT = 5030
    wx.ID_CANCEL = 5101
    wx.ID_YES = 5103
    wx.ID_NO = 5104
    wx.OK = 4
    wx.CANCEL = 8
    wx.YES = 1
    wx.NO = 0
    wx.YES_NO = 16
    wx.NO_DEFAULT = 32
    # 0 in wx; a bit of its own here, so a style assertion sees it (F-5).
    wx.YES_DEFAULT = 1 << 27
    wx.ICON_ERROR = 512
    wx.ICON_INFORMATION = 128
    wx.ICON_WARNING = 256
```

Edit: `client/tests/test_gui_document_flows.py`

```python

import app_paths
import config
from documents.controller import DocumentController
from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
```

```python

import app_paths
import config
import i18n
from documents.controller import DocumentController
from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.workspace = self.root / "workspace"
        self.events: list = []
        self.answers: list = []
        self.names: list = []
        self.delete_invalid = False
        self.import_paths: list[str] = []
        self.import_filter_index = gui.ALL_SUPPORTED_FILTER_INDEX
        for patcher in (
            patch.object(gui.wx, "MessageBox", self._message_box),
            patch.object(gui, "DocumentNameDialog", self._name_dialog_class()),
            patch.object(gui, "InvalidWorkspaceFilesDialog", self._invalid_files_dialog_class()),
            patch.object(gui, "FileIssuesDialog", self._issues_dialog_class()),
```

```python
        self.workspace = self.root / "workspace"
        self.events: list = []
        self.answers: list = []
        self.dialog_answers: list = []
        self.names: list = []
        self.delete_invalid = False
        self.import_paths: list[str] = []
        self.import_filter_index = gui.ALL_SUPPORTED_FILTER_INDEX
        for patcher in (
            patch.object(gui.wx, "MessageBox", self._message_box),
            patch.object(gui.wx, "MessageDialog", self._message_dialog_class()),
            patch.object(gui, "DocumentNameDialog", self._name_dialog_class()),
            patch.object(gui, "InvalidWorkspaceFilesDialog", self._invalid_files_dialog_class()),
            patch.object(gui, "FileIssuesDialog", self._issues_dialog_class()),
```

Edit: `client/tests/test_gui_document_flows.py`

```python
    def _message_box(self, message, caption, style, parent=None):
        self.events.append(("MessageBox", message, caption, style, parent))
        return self.answers.pop(0) if self.answers else gui.wx.OK

    def _name_dialog_class(self):
        test = self
```

```python
    def _message_box(self, message, caption, style, parent=None):
        self.events.append(("MessageBox", message, caption, style, parent))
        return self.answers.pop(0) if self.answers else gui.wx.OK

    def _message_dialog_class(self):
        """``wx.MessageDialog``: records the shown dialog, answers from ``dialog_answers`` (default Cancel)."""
        test = self

        class FakeMessageDialog:
            def __init__(self, parent, message, caption, style):
                self.shown = [message, caption, style, None, None, parent]

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            def SetExtendedMessage(self, extended):
                self.shown[3] = extended

            def SetYesNoCancelLabels(self, yes, no, cancel):
                self.shown[4] = (yes, no, cancel)
                return True

            def ShowModal(self):
                test.events.append(("MessageDialog", *self.shown))
                return test.dialog_answers.pop(0) if test.dialog_answers else gui.wx.ID_CANCEL

        return FakeMessageDialog

    def _name_dialog_class(self):
        test = self
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "alpha.dep", frame)
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "edited", "edited braille")])

    def test_close_vetoes_when_save_fails(self) -> None:
        self._block("alpha")
        frame = self._make_workspace_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        event = Mock()
        event.CanVeto.return_value = True

        frame._on_close(event)

        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
```

```python
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "alpha.dep", frame)
        self.assertEqual(frame._document_controller.documents, [Document("alpha", "edited", "edited braille")])

    def test_close_save_failure_cancel_vetoes(self) -> None:
        # F-5 (D6): the dialog replaces the error box; Cancel keeps the window open.
        self._block("alpha")
        frame = self._make_workspace_frame([Document("alpha", "a", "1")], open_name="alpha", selected_name="alpha")
        event = Mock()
        event.CanVeto.return_value = True
        self.dialog_answers = [gui.wx.ID_CANCEL]

        frame._on_close(event)

        self.assertEqual([item[0] for item in self.events], ["MessageDialog"])
        expected = self._close_dialog(frame, "")
        self.assertTrue(self.events[0][1].startswith(expected[1]), self.events[0][1])
        self.assertIn("alpha.dep", self.events[0][1])
        self.assertEqual(self.events[0][2:], expected[2:])
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        self.assertEqual(self._package("alpha"), Document("alpha", "x�", "1"))
        self.assertEqual(frame.input_txt.value, "x\ud800")

    def test_close_vetoes_and_keeps_the_package_when_save_raises_a_non_os_error(self) -> None:
        # Before F-3 the exception escaped _on_close: no message, and the window neither
        # closed nor said why.
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
```

```python
        self.assertEqual(self._package("alpha"), Document("alpha", "x�", "1"))
        self.assertEqual(frame.input_txt.value, "x\ud800")

    def test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks(self) -> None:
        # Before F-3 the exception escaped _on_close: no message, and the window neither
        # closed nor said why. F-5 (D6, D9): the traceback is logged at each attempt and
        # the dialog offers a way out (here Cancel: the close is vetoed).
        alpha = Document("alpha", "a", "1")
        self._write_packages(alpha)
        alpha_bytes = (self.workspace / "alpha.dep").read_bytes()
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame.input_txt.SetValue("edited")
        event = Mock()
        event.CanVeto.return_value = True

        with patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")):
            frame._on_close(event)

        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
        self.assertEqual(len(self.events), 1)
        self._assert_error_box(self.events[0], "Failed to save document: {error}", "injected", frame)
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    # --- save only when changed (F-5) ----------------------------------------
```

```python
        frame.input_txt.SetValue("edited")
        event = Mock()
        event.CanVeto.return_value = True
        self.dialog_answers = [gui.wx.ID_CANCEL]

        with (
            patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")),
            self.assertLogs(gui.logger, level="ERROR") as logs,
        ):
            frame._on_close(event)

        self._assert_close_dialogs(frame, "injected")
        self._assert_logged_with_traceback(logs, ValueError)
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
        self.assertEqual((self.workspace / "alpha.dep").read_bytes(), alpha_bytes)

    # --- save only when changed (F-5) ----------------------------------------
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        event.Skip.assert_called_once_with()
        frame.close_converting_dialog.assert_called_once_with()
        self.assertEqual(self._disk(), before)

    # --- rename ------------------------------------------------------------

```

```python
        event.Skip.assert_called_once_with()
        frame.close_converting_dialog.assert_called_once_with()
        self.assertEqual(self._disk(), before)

    # --- close after a failed save (F-5) -------------------------------------

    def _close_dialog(self, frame, error: str) -> tuple:
        """The event of the dialog that a failed save on Close shows (D7)."""
        return (
            "MessageDialog",
            gui._("Failed to save document: {error}").format(error=error),
            gui._("Cannot Save Document"),
            gui.wx.YES_NO | gui.wx.CANCEL | gui.wx.YES_DEFAULT | gui.wx.ICON_ERROR,
            gui._(
                "Changes made since the last successful save have not been saved. "
                "If you close without saving, these changes will be lost."
            ),
            (gui._("&Retry"), gui._("Close &Without Saving"), gui._("Cancel")),
            frame,
        )

    def _assert_close_dialogs(self, frame, *errors: str) -> None:
        """The only events are one close dialog per error text, in this order."""
        self.assertEqual([item[0] for item in self.events], ["MessageDialog"] * len(errors))
        self.assertEqual(self.events, [self._close_dialog(frame, error) for error in errors])

    def test_close_save_failure_asks_and_cancel_keeps_the_window_open(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()
        event = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_CANCEL]

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")):
            frame._on_close(event)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        frame.close_converting_dialog.assert_not_called()
        self.assertEqual(frame._document_controller.get_document("alpha"), Document("alpha", "a edited", "1"))
        self.assertEqual(frame.input_txt.value, "a edited")
        self.assertEqual(self._disk(), before)

    def test_close_retry_after_the_cause_is_gone_saves_and_closes(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        event = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_YES]

        with patch("os.replace", wraps=os.replace, side_effect=[PermissionError(errno.EACCES, "injected"), DEFAULT]):
            frame._on_close(event)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        self.assertEqual(self._package("alpha"), Document("alpha", "a edited", "1"))
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    def test_close_retry_that_fails_again_asks_again(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()
        event = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_YES, gui.wx.ID_CANCEL]
        errors = [PermissionError(errno.EACCES, "first"), PermissionError(errno.EACCES, "second")]

        with patch("os.replace", side_effect=errors):
            frame._on_close(event)

        self._assert_close_dialogs(frame, "[Errno 13] first", "[Errno 13] second")
        event.Veto.assert_called_once_with()
        event.Skip.assert_not_called()
        self.assertEqual(self._disk(), before)

    def test_close_without_saving_closes_and_keeps_the_last_saved_package(self) -> None:
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        viewer = Mock()
        frame._dual_view_frame = viewer
        before = self._disk()
        event = self._vetoable_close()
        self.dialog_answers = [gui.wx.ID_NO]

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "injected")) as replace:
            frame._on_close(event)

        self._assert_close_dialogs(frame, "[Errno 13] injected")
        self.assertEqual(replace.call_count, 1)
        frame.close_converting_dialog.assert_called_once_with()
        viewer.Destroy.assert_called_once_with()
        self.assertIsNone(frame._dual_view_frame)
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        self.assertEqual(self._disk(), before)
        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])

    def test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes(self) -> None:
        # D8: Windows is ending the session; nobody could answer a dialog.
        frame = self._start_with_alpha_and_beta()
        frame.input_txt.SetValue("a edited")
        before = self._disk()
        event = Mock()
        event.CanVeto.return_value = False
        error = PermissionError(errno.EACCES, "injected")

        with patch("os.replace", side_effect=error), self.assertLogs(gui.logger, level="ERROR") as logs:
            frame._on_close(event)

        self.assertEqual([item[0] for item in self.events], [])
        self.assertEqual([record.getMessage() for record in logs.records], ["Failed to save the open document while closing"])
        self.assertIs(logs.records[0].exc_info[1], error)
        event.Veto.assert_not_called()
        event.Skip.assert_called_once_with()
        self.assertEqual(self._disk(), before)

    def test_close_dialog_strings_are_translated(self) -> None:
        translation = i18n.load_translation()
        expected = {
            "Cannot Save Document": "無法儲存文件",
            "Changes made since the last successful save have not been saved. "
            "If you close without saving, these changes will be lost.": (
                "上次成功儲存之後的修改尚未儲存。"
                "如果不儲存就關閉，這些修改將會遺失。"
            ),
            "&Retry": "重試(&R)",
            "Close &Without Saving": "不儲存就關閉(&W)",
            "Cancel": "取消",
            "Failed to save document: {error}": "儲存文件失敗：{error}",
        }

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    # --- rename ------------------------------------------------------------

```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame = self._make_frame()
        steps = Mock()
        frame._conversion_presenter = steps.presenter
        frame._save_open_document_with_feedback = steps.save
        frame.close_converting_dialog = steps.close_converting_dialog
        frame._dual_view_frame = None
        event = steps.event
```

```python
        frame = self._make_frame()
        steps = Mock()
        frame._conversion_presenter = steps.presenter
        frame._save_open_document = steps.save
        frame.close_converting_dialog = steps.close_converting_dialog
        frame._dual_view_frame = None
        event = steps.event
```

Edit: `client/tests/test_gui_document_flows.py`

```python

        steps.reset_mock()
        steps.presenter.is_running.return_value = False
        steps.save.return_value = True
        frame._on_close(event)
        self.assertEqual(
            steps.mock_calls,
            [call.presenter.is_running(), call.save(), call.close_converting_dialog(), call.event.Skip()],
        )


```

```python

        steps.reset_mock()
        steps.presenter.is_running.return_value = False
        frame._on_close(event)
        self.assertEqual(
            steps.mock_calls,
            [
                call.presenter.is_running(),
                call.event.CanVeto(),
                call.save(),
                call.close_converting_dialog(),
                call.event.Skip(),
            ],
        )


```

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (today Close shows the error box and vetoes, a forced close shows the box too and logs nothing, the strings are not in the catalog, and the presenter test misses `CanVeto`):

```text
FAIL: test_close_dialog_strings_are_translated (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_dialog_strings_are_translate
AssertionError: {'Can[16 chars]t': 'Cannot Save Document', 'Changes made sinc[366 chars]or}'} != {'Can[16 chars]t': '無法儲存文件', 'Changes made since the last suc[2
FAIL: test_close_retry_after_the_cause_is_gone_saves_and_closes (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_retry_after
AssertionError: Lists differ: ['MessageBox'] != ['MessageDialog']
FAIL: test_close_retry_that_fails_again_asks_again (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_retry_that_fails_again_a
AssertionError: Lists differ: ['MessageBox'] != ['MessageDialog', 'MessageDialog']
FAIL: test_close_save_failure_asks_and_cancel_keeps_the_window_open (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_save_fa
FAIL: test_close_save_failure_cancel_vetoes (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_save_failure_cancel_vetoes)
FAIL: test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_sa
FAIL: test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_that_c
AssertionError: no logs of level ERROR or higher triggered on dotexpress.gui
FAIL: test_close_without_saving_closes_and_keeps_the_last_saved_package (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_wit
FAIL: test_close_asks_presenter_before_saving (tests.test_gui_document_flows.FrameConversionDelegationTest.test_close_asks_presenter_before_saving)
AssertionError: [call[19 chars]ng(),
Ran 181 tests
FAILED (failures=9)
```

- [ ] **Step 2: The close dialog and the retry loop** (`client/gui.py`, **tabs**). `_show_document_save_error` keeps its behavior; its logging moves into `_log_unexpected_save_error` (D9). The ten other callers of `_save_open_document_with_feedback` are unchanged (D10).

Edit: `client/gui.py`

```python
			parent=self,
		)

	def _show_document_save_error(self, error: Exception) -> None:
		"""Report a failed document save; log the traceback if it is not an ``OSError``.

		An ``OSError`` (locked, read-only, disk full) is expected and the message box
		names it fully. Anything else means a bug or bad data in memory, and the
		packaged build has no console, so its traceback goes to ``gui.log``.
		"""
		if not isinstance(error, OSError):
			logger.error("Unexpected error while saving a document", exc_info=error)
		self._show_file_error(_("Failed to save document: {error}"), error)

	def on_open_coseeing_website(self, _evt: wx.CommandEvent) -> None:
		try:
```

```python
			parent=self,
		)

	def _log_unexpected_save_error(self, error: Exception) -> None:
		"""Log the traceback of a failed document save if it is not an ``OSError``.

		An ``OSError`` (locked, read-only, disk full) is expected and the message
		names it fully. Anything else means a bug or bad data in memory, and the
		packaged build has no console, so its traceback goes to ``gui.log``.
		"""
		if not isinstance(error, OSError):
			logger.error("Unexpected error while saving a document", exc_info=error)

	def _show_document_save_error(self, error: Exception) -> None:
		"""Report a failed document save; log the traceback if it is not an ``OSError``."""
		self._log_unexpected_save_error(error)
		self._show_file_error(_("Failed to save document: {error}"), error)

	def _ask_after_close_save_failure(self, error: Exception) -> int:
		"""Ask what Close does after a failed save (F-5 D7).

		``wx.ID_YES``: retry; ``wx.ID_NO``: close without saving; anything else: cancel.
		A Windows task dialog: Retry is the default, Esc and the close box cancel.
		"""
		with wx.MessageDialog(
			self,
			_("Failed to save document: {error}").format(error=error),
			_("Cannot Save Document"),
			wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_ERROR,
		) as dialog:
			dialog.SetExtendedMessage(
				_("Changes made since the last successful save have not been saved. If you close without saving, these changes will be lost.")
			)
			dialog.SetYesNoCancelLabels(_("&Retry"), _("Close &Without Saving"), _("Cancel"))
			return dialog.ShowModal()

	def on_open_coseeing_website(self, _evt: wx.CommandEvent) -> None:
		try:
```

Edit: `client/gui.py`

```python
			self._show_document_save_error(exc)
			return False
		return True

	def _review_invalid_workspace_files(self, invalid_paths: list[Path]) -> None:
		if not invalid_paths:
```

```python
			self._show_document_save_error(exc)
			return False
		return True

	def _save_open_document_before_close(self, can_veto: bool) -> bool:
		"""Save before closing; ``True`` if the frame may close (F-5 D6, D8).

		A failed save asks: Retry saves again, Close without saving drops the edits
		since the last good save (the package keeps that save), Cancel keeps the
		frame open. A close that cannot be vetoed only logs the failure.
		"""
		while True:
			try:
				self._save_open_document()
				return True
			except Exception as error:
				if not can_veto:
					logger.error("Failed to save the open document while closing", exc_info=error)
					return True
				self._log_unexpected_save_error(error)
				answer = self._ask_after_close_save_failure(error)
				if answer == wx.ID_YES:
					continue
				return answer == wx.ID_NO

	def _review_invalid_workspace_files(self, invalid_paths: list[Path]) -> None:
		if not invalid_paths:
```

Edit: `client/gui.py`

```python
		if self._conversion_presenter.is_running() and evt.CanVeto():
			evt.Veto()
			return
		if not self._save_open_document_with_feedback():
			if evt.CanVeto():
				evt.Veto()
			return
		self.close_converting_dialog()
		if self._dual_view_frame is not None:
```

```python
		if self._conversion_presenter.is_running() and evt.CanVeto():
			evt.Veto()
			return
		if not self._save_open_document_before_close(evt.CanVeto()):
			evt.Veto()
			return
		self.close_converting_dialog()
		if self._dual_view_frame is not None:
```

```bash
$PY -m unittest tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (only the catalog test is left; the code passes the msgids through `_`, which returns them untranslated until Step 3):

```text
FAIL: test_close_dialog_strings_are_translated (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_close_dialog_strings_are_translate
AssertionError: {'Can[16 chars]t': 'Cannot Save Document', 'Changes made sinc[366 chars]or}'} != {'Can[16 chars]t': '無法儲存文件', 'Changes made since the last suc[2
Ran 181 tests
FAILED (failures=1)
```

- [ ] **Step 3: Catalogs** (D12). Regenerate the template from the repository root, pin its header date, merge it into the zh_TW catalog, fill the four msgstr values, compile, and convert the two text catalogs back to CRLF (the tools write LF).

```bash
(cd $REPO && cmd //c "scripts\\generate-pot.bat"); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
sed -n '/^#: gui.py:476$/,/^#: gui.py:489$/p' locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected (no `xgettext` warning on stderr; `msgmerge` guessed a wrong fuzzy translation for the title and left three entries empty):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
353 translated messages, 1 fuzzy translation, 3 untranslated messages.
#: gui.py:476
#, fuzzy
msgid "Cannot Save Document"
msgstr "重新命名文件"

#: gui.py:480
msgid ""
"Changes made since the last successful save have not been saved. If you "
"close without saving, these changes will be lost."
msgstr ""

#: gui.py:482
msgid "&Retry"
msgstr ""

#: gui.py:482
msgid "Close &Without Saving"
msgstr ""

#: gui.py:489
```

Fill the four entries and drop the fuzzy flag (the mnemonic style follows the catalog, `&Categories:` -> `分類(&C)：`):

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
#: gui.py:476
#, fuzzy
msgid "Cannot Save Document"
msgstr "重新命名文件"

#: gui.py:480
msgid ""
"Changes made since the last successful save have not been saved. If you "
"close without saving, these changes will be lost."
msgstr ""

#: gui.py:482
msgid "&Retry"
msgstr ""

#: gui.py:482
msgid "Close &Without Saving"
msgstr ""
```

```po
#: gui.py:476
msgid "Cannot Save Document"
msgstr "無法儲存文件"

#: gui.py:480
msgid ""
"Changes made since the last successful save have not been saved. If you "
"close without saving, these changes will be lost."
msgstr "上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。"

#: gui.py:482
msgid "&Retry"
msgstr "重試(&R)"

#: gui.py:482
msgid "Close &Without Saving"
msgstr "不儲存就關閉(&W)"
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
git -C $REPO diff --numstat -- client/locales
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (357 translated, no fuzzy; 358 `msgid` lines with the header; the 31 obsolete entries unchanged; no absolute, backslash, test or venv reference; the four new translations load):

```text
a second msgmerge changes nothing
msgfmt exit 0
357 translated messages.
0
catalog keys: 358
'Cannot Save Document' -> 無法儲存文件
'Changes made since the last successful s' -> 上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。
'&Retry' -> 重試(&R)
'Close &Without Saving' -> 不儲存就關閉(&W)
'Cancel' -> 取消
'Failed to save document: {error}' -> 儲存文件失敗：{error}
26971
locales/dotexpress.pot:358
locales/zh_TW/LC_MESSAGES/dotexpress.po:358
31
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
57	38	client/locales/dotexpress.pot
-	-	client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
57	38	client/locales/zh_TW/LC_MESSAGES/dotexpress.po
source msgids: 357 sha256 7ebbbe567cdc653a3bc755dc82512f061732fb2eabb9b01325d9d3f3386726c6
```

- [ ] **Step 4: Green.**

```bash
$PY -m unittest tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(close_save_failure|close_retry|close_without_saving|close_that_cannot_be_vetoed|close_dialog_strings|close_asks_presenter)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_gui_document_flows tests.test_i18n tests.test_config 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
test_close_dialog_strings_are_translated ok
test_close_retry_after_the_cause_is_gone_saves_and_closes ok
test_close_retry_that_fails_again_asks_again ok
test_close_save_failure_asks_and_cancel_keeps_the_window_open ok
test_close_save_failure_cancel_vetoes ok
test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks ok
test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes ok
test_close_without_saving_closes_and_keeps_the_last_saved_package ok
test_close_asks_presenter_before_saving ok
Ran 232 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1304 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/wx_stub.py client/tests/test_gui_document_flows.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO commit -q -m "fix: offer retry or close without saving when saving fails on close (F-5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
8f8ee46eb955cbc579ca7df8bc8c1345ee006014
```

### Task 4: Verification (no commit)

`BASE` is the merge base with `main` (`918c251`).

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = 1270 + 34; the error is F-W6):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1304 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 2: Criterion 2, focused modules; the 34 new tests ran and passed, the Windows-only ones included.**

```bash
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows tests.test_i18n tests.test_atomic_write tests.test_document_controller 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -cE "^test_(replace_lone_surrogates_replaces_each|replace_lone_surrogates_joins|prepare_document_for_save_replaces|save_replaces_lone|staged_package_replaces|save_open_document_replaces|pasted_lone_surrogate|unchanged_document_is_not|changed_text_is|changed_braille_is|converted_pending|failed_save_is_retried|reverting_after|lone_surrogate_text_is|package_removed_on_disk|package_replaced_on_disk|document_without_a_record|created_document_is_not|imported_document_is_not|renamed_document_is_not|failed_rename_keeps|deleted_then_created|documents_reloaded_after|unchanged_unwritable_package|switch_from_an_unchanged|unchanged_read_only_document|switch_from_a_changed|close_with_an_unchanged|close_save_failure_asks|close_retry_after|close_retry_that|close_without_saving|close_that_cannot_be_vetoed|close_dialog_strings)[a-z_]* .* ok$"
$PY -m unittest tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(unchanged_unwritable_package_saves_without_error|unchanged_read_only_document_blocks_neither_switch_nor_close) " | sed 's/ (.*) \.\.\. / /'
```

Expected:

```text
Ran 353 tests
OK (skipped=6)
34
test_unchanged_unwritable_package_saves_without_error ok
test_unchanged_read_only_document_blocks_neither_switch_nor_close ok
```

- [ ] **Step 3: Shuffled module order, six seeds** (one process each, about two minutes).

```bash
for s in 0 1 2 3 4 5; do $PY $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
      6 ran=1304 failures=0 errors=1 skipped=7 ['test_case_only_rename_still_renames']
```

- [ ] **Step 4: Criterion 3, catalogs.** A second run of `generate-pot.bat` into a scratch file differs from the committed template only in `POT-Creation-Date`; `msgfmt` reports 357 translated messages; the committed `.mo` loads with `gettext.GNUTranslations` and translates the four new msgids.

```bash
(cd $REPO && cmd //c "scripts\\generate-pot.bat $(cygpath -w $T/second.pot)"); echo "generate-pot exit $?"
diff --strip-trailing-cr <(grep -v '^"POT-Creation-Date: ' locales/dotexpress.pot) <(grep -v '^"POT-Creation-Date: ' $T/second.pot) && echo "second template identical apart from POT-Creation-Date"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
git -C $REPO show HEAD:client/locales/zh_TW/LC_MESSAGES/dotexpress.mo > $T/committed.mo
$PY -I $T/tools/mo_check.py $T/committed.mo
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected:

```text
generate-pot exit 0
second template identical apart from POT-Creation-Date
357 translated messages.
catalog keys: 358
'Cannot Save Document' -> 無法儲存文件
'Changes made since the last successful s' -> 上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。
'&Retry' -> 重試(&R)
'Close &Without Saving' -> 不儲存就關閉(&W)
'Cancel' -> 取消
'Failed to save document: {error}' -> 儲存文件失敗：{error}
source msgids: 357 sha256 7ebbbe567cdc653a3bc755dc82512f061732fb2eabb9b01325d9d3f3386726c6
```

- [ ] **Step 5: Criteria 4-6, fixtures, untouched modules, touched files, application data.**

```bash
BASE=$(git -C $REPO merge-base main HEAD)
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/conversion && echo "client/conversion unchanged"
git -C $REPO diff --stat $BASE -- client/tests/fixtures client/dialog.py client/documents/controller.py client/documents/session.py client/documents/formats.py client/documents/export_coordinator.py client/ui client/shared client/braille client/dictionaries
git -C $REPO diff --stat=200 $BASE -- client
(cd $MAIN/client && sha256sum --quiet -c $T/app-data.sha256) && echo "application data unchanged"
git -C $REPO status --short -- client docs scripts
```

Expected (the second `diff --stat` prints nothing; `status` prints nothing):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
client/conversion unchanged
 client/documents/workspace.py                  |  19 +++++++-
 client/documents/workspace_service.py          |  58 +++++++++++++++++++++++-
 client/gui.py                                  |  54 +++++++++++++++++++---
 client/locales/dotexpress.pot                  |  95 +++++++++++++++++++++++----------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | Bin 26579 -> 26971 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po |  95 +++++++++++++++++++++++----------------
 client/tests/test_document_workspace.py        |  95 ++++++++++++++++++++++++++++++++++-----
 client/tests/test_gui_document_flows.py        | 359 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-------------
 client/tests/test_workspace_service.py         | 259 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 client/tests/wx_stub.py                        |  11 ++++-
 10 files changed, 913 insertions(+), 132 deletions(-)
application data unchanged
```

- [ ] **Step 6: Criterion 7, mutation check** (25 mutants: the spec's list, whose last item is two mutants, and 10 more for the other record paths, the fingerprint, the replacement and the logging; about a minute). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f5_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
baseline-from-the-controller-copy: 12 caught: test_gui_document_flows.test_close_retry_after_the_cause_is_gone_saves_and_closes, test_gui_document_flows.test_close_retry_that_fails_again_asks_again, test_gui_document_flows.test_close_save_failure_cancel_vetoes, test_gui_document_flows.test_ctrl_s_during_manual_conversion_supersedes_it, test_gui_document_flows.test_single_export_with_braille_writes_and_reports, test_workspace_service.test_converted_pending_document_is_written, and 6 more
record-before-the-write: 5 caught: test_gui_document_flows.test_close_retry_after_the_cause_is_gone_saves_and_closes, test_gui_document_flows.test_close_retry_that_fails_again_asks_again, test_workspace_service.test_failed_save_is_retried_by_the_next_save, test_workspace_service.test_lone_surrogate_text_is_saved_once, test_workspace_service.test_reverting_after_a_failed_save_is_not_written
record-despite-a-failed-write: 4 caught: test_gui_document_flows.test_close_retry_after_the_cause_is_gone_saves_and_closes, test_gui_document_flows.test_close_retry_that_fails_again_asks_again, test_workspace_service.test_failed_save_is_retried_by_the_next_save, test_workspace_service.test_reverting_after_a_failed_save_is_not_written
no-fingerprint-check: 2 caught: test_workspace_service.test_package_removed_on_disk_is_written_again, test_workspace_service.test_package_replaced_on_disk_is_written_again
fingerprint-without-the-modification-time: 1 caught: test_workspace_service.test_package_replaced_on_disk_is_written_again
record-not-encodable: 1 caught: test_workspace_service.test_created_document_is_not_written_again
load-records-nothing: 8 caught: test_gui_document_flows.test_close_with_an_unchanged_document_whose_save_would_fail_closes, test_gui_document_flows.test_switch_from_an_unchanged_document_whose_save_would_fail_opens_the_next, test_gui_document_flows.test_unchanged_read_only_document_blocks_neither_switch_nor_close, test_workspace_service.test_converted_pending_document_is_written, test_workspace_service.test_failed_rename_keeps_the_record_of_the_old_name, test_workspace_service.test_reverting_after_a_failed_save_is_not_written, and 2 more
create-records-nothing: 1 caught: test_workspace_service.test_created_document_is_not_written_again
import-records-nothing: 1 caught: test_workspace_service.test_imported_document_is_not_written_again
rename-does-not-move-the-record: 1 caught: test_workspace_service.test_renamed_document_is_not_written_again
rename-drops-the-record-before-the-move: 1 caught: test_workspace_service.test_failed_rename_keeps_the_record_of_the_old_name
delete-all-failure-keeps-the-old-records: 1 caught: test_workspace_service.test_documents_reloaded_after_a_failed_delete_all_are_not_written_again
prepare-without-the-replacement: 5 caught: test_document_workspace.test_prepare_document_for_save_replaces_lone_surrogates, test_gui_document_flows.test_pasted_lone_surrogate_is_saved_as_replacement_character, test_workspace_service.test_created_document_is_not_written_again, test_workspace_service.test_lone_surrogate_text_is_saved_once, test_workspace_service.test_save_open_document_replaces_lone_surrogates_in_memory_and_on_disk
normalized-without-the-replacement: 3 caught: test_document_workspace.test_save_replaces_lone_surrogates_with_the_replacement_character, test_document_workspace.test_staged_package_replaces_lone_surrogates, test_workspace_service.test_created_document_is_not_written_again
braille-not-replaced: 4 caught: test_document_workspace.test_prepare_document_for_save_replaces_lone_surrogates, test_document_workspace.test_save_replaces_lone_surrogates_with_the_replacement_character, test_workspace_service.test_created_document_is_not_written_again, test_workspace_service.test_save_open_document_replaces_lone_surrogates_in_memory_and_on_disk
replacement-through-utf-8: 7 caught: test_document_workspace.test_prepare_document_for_save_replaces_lone_surrogates, test_document_workspace.test_replace_lone_surrogates_replaces_each_unpaired_surrogate, test_document_workspace.test_save_replaces_lone_surrogates_with_the_replacement_character, test_document_workspace.test_staged_package_replaces_lone_surrogates, test_gui_document_flows.test_pasted_lone_surrogate_is_saved_as_replacement_character, test_workspace_service.test_lone_surrogate_text_is_saved_once, and 1 more
replacement-with-a-question-mark: 7 caught: test_document_workspace.test_prepare_document_for_save_replaces_lone_surrogates, test_document_workspace.test_replace_lone_surrogates_replaces_each_unpaired_surrogate, test_document_workspace.test_save_replaces_lone_surrogates_with_the_replacement_character, test_document_workspace.test_staged_package_replaces_lone_surrogates, test_gui_document_flows.test_pasted_lone_surrogate_is_saved_as_replacement_character, test_workspace_service.test_lone_surrogate_text_is_saved_once, and 1 more
close-without-saving-saves-anyway: 1 caught: test_gui_document_flows.test_close_without_saving_closes_and_keeps_the_last_saved_package
retry-closes-without-retrying: 2 caught: test_gui_document_flows.test_close_retry_after_the_cause_is_gone_saves_and_closes, test_gui_document_flows.test_close_retry_that_fails_again_asks_again
cancel-closes: 4 caught: test_gui_document_flows.test_close_retry_that_fails_again_asks_again, test_gui_document_flows.test_close_save_failure_asks_and_cancel_keeps_the_window_open, test_gui_document_flows.test_close_save_failure_cancel_vetoes, test_gui_document_flows.test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks
non-vetoable-close-asks: 1 caught: test_gui_document_flows.test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes
non-vetoable-close-stays-open: 1 caught: test_gui_document_flows.test_close_that_cannot_be_vetoed_logs_a_failed_save_and_closes
close-failure-not-logged: 1 caught: test_gui_document_flows.test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks
dialog-without-yes-default: 6 caught: test_gui_document_flows.test_close_retry_after_the_cause_is_gone_saves_and_closes, test_gui_document_flows.test_close_retry_that_fails_again_asks_again, test_gui_document_flows.test_close_save_failure_asks_and_cancel_keeps_the_window_open, test_gui_document_flows.test_close_save_failure_cancel_vetoes, test_gui_document_flows.test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks, test_gui_document_flows.test_close_without_saving_closes_and_keeps_the_last_saved_package
dialog-labels-in-another-order: 6 caught: test_gui_document_flows.test_close_retry_after_the_cause_is_gone_saves_and_closes, test_gui_document_flows.test_close_retry_that_fails_again_asks_again, test_gui_document_flows.test_close_save_failure_asks_and_cancel_keeps_the_window_open, test_gui_document_flows.test_close_save_failure_cancel_vetoes, test_gui_document_flows.test_close_save_failure_that_is_not_an_os_error_is_logged_and_asks, test_gui_document_flows.test_close_without_saving_closes_and_keeps_the_last_saved_package
exit 0
```

### Task 5: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay. In the dry run the same code was built in the scratch clone with the command below ("Build complete!" in 49 s, 48,743,550 bytes), `smoke_f5gui.py` drove the demo dialog with each key several times, and items 36-40 and the re-runs of 18, 19 (with 20), 20b and 33 ran against that build with the scripts below and gave exactly the "Expected" columns (in `D:\dxtest\dry*-f5` folders, deleted afterwards). Run everything from the repository root, one item at a time, with nothing else driving the desktop. Never touch `D:\dxtest\N`, `D:\dxtest\B`, `D:\dxtest\N-p25`, `D:\dxtest\N-f3`, `D:\dxtest\N-f4*` or the existing `D:\dxtest\auto*` folders; every F-5 run uses a new folder whose name ends in `-f5`.

- [ ] **Step 1: Build** (PowerShell). The main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`.

```powershell
Set-Location D:\workspace\DotExpress
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f5-build.log 2>&1"
if (Select-String -Path $env:TEMP\f5-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "documents\\workspace.py", "documents\\workspace_service.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress\\client\\$m" -Quiet) { "$m bundled from the checkout" } }
if (Select-String -Path client\build\DotExpress\Analysis-00.toc -SimpleMatch "DotExpress\\client\\gui.py" -Quiet) { "gui.py analyzed from the checkout" }
New-Item -ItemType Directory -Force D:\dxtest\N-f5 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f5\DotExpress.exe
(Get-Item D:\dxtest\N-f5\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f5\DotExpress.exe).Hash
git status --short -- client docs scripts
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f5-build.log`), the two `bundled from the checkout` lines, `gui.py analyzed from the checkout`, a size near 48.7 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored).

- [ ] **Step 2: Create the GUI scripts** in the new history folder (tabs, like the 2026-10-09-03 helpers they import). `f5gui.py` holds the shared helpers; `rerun.py` runs earlier scripts against the F-5 build; `item36.py` covers items 36 and 37, `item38.py` items 38 and 39, `item40.py` item 40.

File: `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/f5gui.py`

````python
"""Shared helpers for the F-5 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py and lock.py of the 2026-10-09-03 Windows verification unchanged.
wx shows its message boxes as Windows task dialogs. dx.dismiss reads their text, but
its win32 click does not reach the button, so the box stays open (seen in the F-5 dry
run; an open box keeps the process alive after Close). ``dismiss`` presses OK through
UIA instead, and the F-5 close dialog is read and answered through UIA too.
"""
import ctypes
import os
import subprocess
import sys
import time
import zipfile
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO03 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-09-03-windows-verification", "auto"))
sys.path.insert(0, AUTO03)
import dx  # noqa: E402
import docs as D  # noqa: E402

LOCK = os.path.join(AUTO03, "lock.py")
CLOSE_DIALOG_TITLE = "無法儲存文件"
KEYS = {"enter": "{ENTER}", "esc": "{ESC}", "alt-r": "%r", "alt-w": "%w"}


def workspace(d):
	return os.path.join(d, "workspace")


def files(d):
	return sorted(os.listdir(workspace(d)))


def leftovers(d):
	return [name for name in files(d) if name.endswith(".tmp")]


def attrib(path):
	return subprocess.run(["cmd", "/c", "attrib", path], capture_output=True, text=True).stdout.strip()


def package(path):
	"""(sha256 of the zip members, st_mtime_ns): the members ignore the zip timestamps."""
	return D.content_hash(path), os.stat(path).st_mtime_ns


def member(path, name):
	with zipfile.ZipFile(path) as archive:
		return archive.read(name)


def lock(path, share):
	"""Hold ``path`` open in another process (lock.py, share "r" or "rw") until ``unlock``."""
	process = subprocess.Popen([sys.executable, LOCK, path, "600", share], stdout=subprocess.PIPE, text=True)
	print("lock:", process.stdout.readline().strip(), share)
	return process


def unlock(process):
	subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
	time.sleep(1)


def dismiss(app, buttons=("OK", "確定")):
	"""Read every message box of ``app`` and press its OK button through UIA.

	Returns [(caption, texts)] like dx.dismiss. A file dialog and the F-5 close dialog
	are left open.
	"""
	from pywinauto import Desktop

	out = []
	for box in dx.dialogs(app):
		if box.window_text() == CLOSE_DIALOG_TITLE:
			continue
		texts = dx.dialog_text(box)
		if "檔案名稱:" in texts:
			out.append((box.window_text(), "<file dialog left open>"))
			continue
		out.append((box.window_text(), [t for t in texts if t not in ("MainInstructionIcon", "關閉")]))
		pressable = [
			button
			for button in Desktop(backend="uia").window(handle=box.handle).descendants(control_type="Button")
			if button.window_text() in buttons
		]
		if pressable:
			pressable[0].invoke()
			time.sleep(0.8)
	return out


def switch(app, w, back=False):
	"""Ctrl+Tab (Ctrl+Shift+Tab if ``back``); return the message boxes it showed (closed) and the title."""
	from pywinauto.keyboard import send_keys

	w.set_focus()
	send_keys("^+{TAB}" if back else "^{TAB}")
	time.sleep(1.5)
	return dismiss(app), w.window_text()


def open_document(app, w, name):
	"""Select ``name``, choose File > Open (#0->#0) and return the message boxes it showed."""
	D.select(w, name)
	w.set_focus()
	w.menu_select("#0->#0")
	time.sleep(1.2)
	return dismiss(app)


def setup_alpha_beta(exe, d):
	"""A new work folder with alpha ("alpha body") and beta ("beta body"), closed and restarted.

	After the restart alpha is open and unchanged since it was loaded.
	"""
	app, w = dx.launch(exe, d)
	print("add alpha:", D.add(app, w, "alpha"))
	D.set_input(w, "alpha body")
	print("add beta:", D.add(app, w, "beta"))
	D.set_input(w, "beta body")
	print("close:", D.close(app, w))
	app, w = dx.launch(exe, d, fresh=False)
	print("docs:", D.docs(w), "title:", w.window_text(), "input:", repr(D.get_input(w)), "files:", files(d))
	return app, w


def paste_text_with_lone_surrogate(w, units=(0x41, 0xD83D, 0x42)):
	"""Replace the input text by pasting raw UTF-16 code units (a lone surrogate by default)."""
	user32 = ctypes.WinDLL("user32", use_last_error=True)
	kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
	user32.OpenClipboard.argtypes = (wintypes.HWND,)
	user32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
	user32.SetClipboardData.restype = wintypes.HANDLE
	kernel32.GlobalAlloc.argtypes = (wintypes.UINT, ctypes.c_size_t)
	kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
	kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL,)
	kernel32.GlobalLock.restype = ctypes.c_void_p
	kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL,)
	data = b"".join(unit.to_bytes(2, "little") for unit in units) + b"\x00\x00"
	handle = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
	pointer = kernel32.GlobalLock(handle)
	ctypes.memmove(pointer, data, len(data))
	kernel32.GlobalUnlock(handle)
	if not user32.OpenClipboard(None):
		raise ctypes.WinError(ctypes.get_last_error())
	try:
		user32.EmptyClipboard()
		if not user32.SetClipboardData(13, handle):  # CF_UNICODETEXT
			raise ctypes.WinError(ctypes.get_last_error())
	finally:
		user32.CloseClipboard()
	edit = w.children(class_name="Edit")[0]
	edit.set_edit_text("")
	edit.send_message(0x0302, 0, 0)  # WM_PASTE
	time.sleep(0.5)


def close_dialog(w, timeout=15):
	"""The F-5 close dialog (UIA wrapper), a child of the main window in the UIA tree."""
	from pywinauto import Desktop

	end = time.time() + timeout
	while time.time() < end:
		dialog = Desktop(backend="uia").window(handle=w.handle).child_window(title=CLOSE_DIALOG_TITLE, control_type="Window")
		if dialog.exists(timeout=0):
			return dialog
		time.sleep(0.3)
	return None


def describe(dialog):
	"""What a screen reader gets: title, main instruction, content, buttons, focus."""
	from pywinauto.uia_defines import IUIA

	dialog.set_focus()
	time.sleep(0.5)

	def text(automation_id):
		found = dialog.child_window(auto_id=automation_id, control_type="Text")
		return found.window_text() if found.exists(timeout=0) else None

	buttons = [
		button.window_text()
		for button in dialog.descendants(control_type="Button")
		if button.element_info.parent.control_type != "TitleBar"
	]
	focused = IUIA().iuia.GetFocusedElement()
	return {
		"title": dialog.window_text(),
		"main": text("MainInstruction"),
		"content": text("ContentText"),
		"buttons": buttons,
		"focus": focused.CurrentName,
	}


def answer(dialog, key):
	"""Bring the dialog to the foreground and press ``key`` (a key of KEYS).

	A key pressed while the window takes the focus is sometimes lost: if the same dialog
	is still open 5 s later, the key is pressed again (at most three times). Returns how
	many times it was pressed. A dialog shown again after a failed retry is a new window.
	"""
	import win32gui
	from pywinauto.keyboard import send_keys

	handle = dialog.handle
	for presses in (1, 2, 3):
		for _attempt in range(10):
			if win32gui.GetForegroundWindow() == handle:
				break
			dialog.set_focus()
			time.sleep(0.5)
		time.sleep(0.5)
		send_keys(KEYS[key])
		end = time.time() + 5
		while time.time() < end:
			if not win32gui.IsWindow(handle):
				time.sleep(1)
				return presses
			time.sleep(0.2)
	return presses


def wait_exit(app, timeout=15):
	end = time.time() + timeout
	while time.time() < end:
		if not app.is_process_running():
			return True
		time.sleep(0.5)
	return False


def close_and_answer(app, w, answers, between=None):
	"""Post WM_CLOSE and answer each close dialog in turn with a key of KEYS.

	``between`` maps an answer's index to a function called before that answer (for
	example releasing a lock). Returns (dialogs, outcome): the description of each dialog
	answered, and "exited", "running" or a message about an unexpected window.
	"""
	import win32con

	w.post_message(win32con.WM_CLOSE)
	time.sleep(1)
	dialogs = []
	for index, key in enumerate(answers):
		dialog = close_dialog(w)
		if dialog is None:
			return dialogs, "exited" if wait_exit(app, 5) else f"no dialog for answer {index}: {dismiss(app)}"
		dialogs.append(describe(dialog))
		if between and index in between:
			between[index]()
		dialogs[-1]["presses"] = answer(dialog, key)
	if wait_exit(app, 5):
		return dialogs, "exited"
	if close_dialog(w, timeout=1) is not None:
		return dialogs, "dialog still open"
	other = dismiss(app)
	return dialogs, f"running {other}" if other else "running"
````

File: `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/rerun.py`

````python
"""Run an earlier GUI script against the F-5 build, closing message boxes through UIA (F-5).

Usage: python rerun.py <script.py> <exe> <work folder> [--seed <folder>]

item18.py, item19.py and item21.py of 2026-10-09-03 hard-code the N build and
D:\\dxtest\\auto18: those two literals are replaced in memory (each must occur once), as
F-3's rerun.py does. Any other script (item20b.py of 2026-10-09-03, item33.py of F-3)
gets <exe> and <work folder> as its arguments. With --seed, the work folder (which must
not exist yet) starts as a copy of the given folder.

The scripts run unchanged, with __file__ pointing at the original, except that
dx.dismiss is replaced by f5gui.dismiss for the run: the wx message boxes are task
dialogs, and the win32 click of dx.dismiss does not close them (seen in the F-5 dry run;
an open box keeps the process alive after Close). The committed scripts are not changed.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import f5gui  # noqa: E402

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
	if OLD_EXE in source or OLD_DIR in source:
		for old in (OLD_EXE, OLD_DIR):
			if source.count(old) != 1:
				sys.exit(f"{old} occurs {source.count(old)} times in {script}")
		source = source.replace(OLD_EXE, repr(exe)).replace(OLD_DIR, repr(work))
		sys.argv = [script]
	else:
		sys.argv = [script, exe, work]
	if seed is not None:
		if os.path.exists(work):
			sys.exit(f"{work} exists; --seed needs a new folder")
		shutil.copytree(seed, work)
	f5gui.dx.dismiss = f5gui.dismiss
	sys.path.insert(0, os.path.dirname(script))
	exec(compile(source, script, "exec"), {"__name__": "__main__", "__file__": script})


if __name__ == "__main__":
	main()
````

File: `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/item36.py`

````python
"""Items 36 and 37 (F-5): the open alpha is unchanged and its package cannot be written.

Usage: python item36.py <exe> <work folder> <readonly|r|rw>
readonly is item 36 (attrib +r alpha.dep); r and rw are item 37 (lock.py holds alpha.dep
with share read, or read+write). With alpha open and unchanged since the restart:
Ctrl+Tab, Add gamma, open alpha again, Close.
After F-5: no message; the switch and the Add work; the app exits; the members and
st_mtime_ns of alpha.dep are unchanged (and it is still R for readonly); no .tmp.
Before F-5 (N-f4): [Errno 13] (readonly) or [WinError 5] (r, rw) at every action, and
Close is vetoed (F-W10).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f5gui import (  # noqa: E402
	D,
	attrib,
	close_and_answer,
	dx,
	files,
	leftovers,
	lock,
	open_document,
	package,
	setup_alpha_beta,
	switch,
	unlock,
	workspace,
)

EXE, d, fault = sys.argv[1], sys.argv[2], sys.argv[3]
app, w = setup_alpha_beta(EXE, d)
alpha = os.path.join(workspace(d), "alpha.dep")
holder = None
if fault == "readonly":
	subprocess.run(["attrib", "+r", alpha])
else:
	holder = lock(alpha, fault)
before = package(alpha)
print("attrib before:", attrib(alpha))
print("ctrl+tab:", switch(app, w))
print("add gamma:", D.add(app, w, "gamma"))
print("docs:", D.docs(w), "title:", w.window_text())
print("open alpha:", open_document(app, w, "alpha"), "title:", w.window_text())
print("close:", close_and_answer(app, w, []))
print("alpha unchanged:", package(alpha) == before, "attrib after:", attrib(alpha))
print("files:", files(d), "tmp:", leftovers(d))
if holder is not None:
	unlock(holder)
else:
	subprocess.run(["attrib", "-r", alpha])
dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/item38.py`

````python
"""Items 38 and 39 (F-5): Close after a failed save of a changed document.

Usage: python item38.py <exe> <work folder> <38|39>
alpha is open; "alpha edited" is typed; lock.py holds alpha.dep (share read); Ctrl+Tab;
then Close.
38: Esc: the app stays open with the edit. Close again, Enter (Retry) while the lock is
    held: the dialog again. The lock is released, Enter: the app exits. After a restart
    alpha holds the edit.
39: Alt+W (Close without saving): the app exits, the members of alpha.dep are unchanged
    since before the edit, no .tmp; after a restart alpha holds the old text.
Before F-5 (N-f4): Close shows the error box (確定 only) and is vetoed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f5gui import (  # noqa: E402
	D,
	close_and_answer,
	dx,
	files,
	leftovers,
	lock,
	member,
	package,
	setup_alpha_beta,
	switch,
	unlock,
	workspace,
)

EXE, d, item = sys.argv[1], sys.argv[2], sys.argv[3]
app, w = setup_alpha_beta(EXE, d)
alpha = os.path.join(workspace(d), "alpha.dep")
before = package(alpha)
D.set_input(w, "alpha edited")
holder = lock(alpha, "r")
print("ctrl+tab:", switch(app, w))
print("input:", repr(D.get_input(w)))
if item == "38":
	dialogs, outcome = close_and_answer(app, w, ["esc"])
	print("close, esc:", outcome)
	for dialog in dialogs:
		print("  dialog:", dialog)
	print("input after esc:", repr(D.get_input(w)), "title:", w.window_text())
	dialogs, outcome = close_and_answer(app, w, ["enter", "enter"], between={1: lambda: unlock(holder)})
	print("close, enter while locked, unlock, enter:", outcome)
	for dialog in dialogs:
		print("  dialog:", dialog)
else:
	dialogs, outcome = close_and_answer(app, w, ["alt-w"])
	print("close, alt-w:", outcome)
	for dialog in dialogs:
		print("  dialog:", dialog)
	unlock(holder)
print(
	"alpha members changed:", package(alpha)[0] != before[0],
	"text:", repr(member(alpha, "alpha.txt").decode("utf-8")),
	"files:", files(d), "tmp:", leftovers(d),
)
app, w = dx.launch(EXE, d, fresh=False)
print("after restart:", D.docs(w), "title:", w.window_text(), "input:", repr(D.get_input(w)))
print("close:", close_and_answer(app, w, []))
dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/item40.py`

````python
"""Item 40 (F-5): a pasted lone surrogate is saved as U+FFFD.

Usage: python item40.py <exe> <work folder>
alpha is open; the clipboard holds the UTF-16 code units 41 D83D 42 (A, a lone high
surrogate, B), which are pasted into the input; Ctrl+Tab; Ctrl+Shift+Tab back to alpha;
Ctrl+Tab again.
After F-5: no message; alpha.txt in the package holds 41 ef bf bd 42; the second switch
away from alpha leaves the package (members and st_mtime_ns) as it was; after a restart
alpha shows 'A\\ufffdB'.
Before F-5 (N-f4): 儲存文件失敗：'utf-8' codec can't encode character '\\ud83d' ... at
every switch, and Close is vetoed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f5gui import (  # noqa: E402
	D,
	close_and_answer,
	dx,
	leftovers,
	member,
	package,
	paste_text_with_lone_surrogate,
	setup_alpha_beta,
	switch,
	workspace,
)

EXE, d = sys.argv[1], sys.argv[2]
app, w = setup_alpha_beta(EXE, d)
alpha = os.path.join(workspace(d), "alpha.dep")
paste_text_with_lone_surrogate(w)
print("input:", ascii(D.get_input(w)))
print("ctrl+tab:", switch(app, w))
print("alpha.txt:", member(alpha, "alpha.txt").hex(" "))
saved = package(alpha)
print("ctrl+shift+tab:", switch(app, w, back=True), "input:", ascii(D.get_input(w)))
print("ctrl+tab again:", switch(app, w))
print("alpha not rewritten:", package(alpha) == saved, "tmp:", leftovers(d))
print("close:", close_and_answer(app, w, []))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart:", D.docs(w), "title:", w.window_text(), "input:", ascii(D.get_input(w)))
print("close:", close_and_answer(app, w, []))
dx.kill_under(d)
````

Then the two throwaway smoke tools: a dialog built exactly like `_ask_after_close_save_failure` with the committed catalog, and a driver that reads and answers it with `f5gui.py`.

File: `$T/tools/close_dialog_demo.py`

````python
"""Show the F-5 close dialog as gui.py builds it, with the client's catalog (throwaway).

Usage (from client/, with the client venv): python close_dialog_demo.py <out-file>
Writes "supported=<SetYesNoCancelLabels result> result=<ShowModal answer>" to <out-file>.
The smoke target of smoke_f5gui.py; the main window title ends with "DotExpress".
"""
import os
import sys

import wx

sys.path.insert(0, os.getcwd())
from i18n import _  # noqa: E402

out = sys.argv[1]
app = wx.App(False)
frame = wx.Frame(None, title="f5 demo - DotExpress")
frame.Show()
dialog = wx.MessageDialog(
    frame,
    _("Failed to save document: {error}").format(error="[Errno 13] demo"),
    _("Cannot Save Document"),
    wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_ERROR,
)
dialog.SetExtendedMessage(
    _("Changes made since the last successful save have not been saved. If you close without saving, these changes will be lost.")
)
supported = dialog.SetYesNoCancelLabels(_("&Retry"), _("Close &Without Saving"), _("Cancel"))
result = dialog.ShowModal()
names = {wx.ID_YES: "ID_YES", wx.ID_NO: "ID_NO", wx.ID_CANCEL: "ID_CANCEL"}
with open(out, "w", encoding="utf-8") as stream:
    stream.write(f"supported={supported} result={names.get(result, result)}\n")
dialog.Destroy()
frame.Destroy()
````

File: `$T/tools/smoke_f5gui.py`

````python
"""Drive close_dialog_demo.py with the dialog helpers of f5gui.py, once per key (throwaway).

Usage (UIA venv): python smoke_f5gui.py <client python> <client dir> <f5 auto dir> [key ...]
Prints what describe() reads once, then the answer ShowModal returned for each key.
"""
import os
import subprocess
import sys
import tempfile
import time

client_python, client_dir, auto_dir = sys.argv[1:4]
KEYS = sys.argv[4:] or ["enter", "esc", "alt-r", "alt-w"]
sys.path.insert(0, auto_dir)
import f5gui  # noqa: E402
from pywinauto import Application  # noqa: E402

DEMO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "close_dialog_demo.py")
TITLE = "f5 demo - DotExpress"
for index, key in enumerate(KEYS):
    out = os.path.join(tempfile.gettempdir(), f"f5-demo-{key}.out")
    if os.path.exists(out):
        os.remove(out)
    process = subprocess.Popen([client_python, DEMO, out], cwd=client_dir)
    app = Application(backend="win32")
    for _attempt in range(100):
        try:
            app.connect(title=TITLE, timeout=0.2)
            break
        except Exception:
            time.sleep(0.2)
    w = app.window(title=TITLE)
    dialog = f5gui.close_dialog(w)
    info = f5gui.describe(dialog)
    if index == 0:
        for name, value in info.items():
            print(f"{name}: {value!r}")
    presses = f5gui.answer(dialog, key)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        print(key, "-> the dialog did not close")
        continue
    with open(out, encoding="utf-8") as stream:
        print(key, "->", stream.read().strip(), "presses:", presses)
````

Check the scripts and the dialog helpers (Git Bash, from the repository root; `UIA` is the separate venv with pywinauto 0.6.9 and psutil 7.2.2; the smoke test shows five short-lived demo windows):

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto
export PYTHONIOENCODING=utf-8
cd $REPO
"$UIA" -c "import pywinauto, psutil; print(pywinauto.__version__, psutil.__version__)"
"$UIA" -c "import ast, glob; [ast.parse(open(p, encoding='utf-8').read(), p) for p in glob.glob('$H/*.py')]; print('syntax ok')"
(cd client && "$UIA" $T/tools/smoke_f5gui.py "$(cygpath -w $PY)" "$(cygpath -w $REPO/client)" "$(cygpath -w $REPO/$H)")
git status --short -- client docs scripts
```

Expected:

```text
0.6.9 7.2.2
syntax ok
title: '無法儲存文件'
main: '儲存文件失敗：[Errno 13] demo'
content: '上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。'
buttons: ['重試(R)', '不儲存就關閉(W)', '取消']
focus: '重試(R)'
enter -> supported=True result=ID_YES presses: 1
esc -> supported=True result=ID_CANCEL presses: 1
alt-r -> supported=True result=ID_YES presses: 1
alt-w -> supported=True result=ID_NO presses: 1
?? docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/
```

`UIA` is the venv the spec used (`$SP/uia`). If it no longer exists, or its `Scripts\python.exe` is missing (it was in the dry run), run `py -3.13 -m venv --upgrade <venv>` or create one anywhere outside the repo with `python -m venv` and `pip install pywinauto==0.6.9 psutil`. A `presses: 2` means a key was lost once and pressed again (it happened once in the dry run's last smoke run); record it, it is not a failure, but the answer must still be the one in the block.

- [ ] **Step 3: New items 36-40** (Git Bash, from the repository root). Each run makes a new work folder (`dx.launch` deletes it first) and ends any process left under it. Read each log against the table before the next item.

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto
EXE=/d/dxtest/N-f5/DotExpress.exe
export PYTHONIOENCODING=utf-8
cd $REPO
"$UIA" $H/item36.py $EXE /d/dxtest/auto36-f5 readonly > /d/dxtest/auto36-f5.log 2>&1
"$UIA" $H/item36.py $EXE /d/dxtest/auto37r-f5 r > /d/dxtest/auto37r-f5.log 2>&1
"$UIA" $H/item36.py $EXE /d/dxtest/auto37rw-f5 rw > /d/dxtest/auto37rw-f5.log 2>&1
"$UIA" $H/item38.py $EXE /d/dxtest/auto38-f5 38 > /d/dxtest/auto38-f5.log 2>&1
"$UIA" $H/item38.py $EXE /d/dxtest/auto39-f5 39 > /d/dxtest/auto39-f5.log 2>&1
"$UIA" $H/item40.py $EXE /d/dxtest/auto40-f5 > /d/dxtest/auto40-f5.log 2>&1
```

Expected (every log starts with `add alpha: ('新增文件', [], [], [])`, `add beta: ...`, `close: exited` and `docs: ['alpha', 'beta', 'new'] title: alpha - DotExpress input: 'alpha body' files: ['alpha.dep', 'beta.dep', 'new.dep']`; `<tmp>` is `.alpha.dep.<16 hex>.tmp`, a new name at every attempt):

| # | Expected after F-5 | Before (N-f4, spec) |
| --- | --- | --- |
| 36 | `attrib before: A    R ...alpha.dep`; `ctrl+tab: ([], 'beta - DotExpress')`; `add gamma: ('新增文件', [], [], [])`; `docs: ['alpha', 'beta', 'gamma', 'new'] title: gamma - DotExpress`; `open alpha: [] title: alpha - DotExpress`; `close: ([], 'exited')`; `alpha unchanged: True`, `attrib after` still `R`; `files: ['alpha.dep', 'beta.dep', 'gamma.dep', 'new.dep'] tmp: []` | `[Errno 13]` at every action; Close vetoed (item 20) |
| 37 r, 37 rw | `lock: locked r` (`rw`); `attrib before: A ...` (no `R`); then the same lines as 36, `alpha unchanged: True`, `tmp: []` | `[WinError 5]` at every action; Close vetoed |
| 38 | `ctrl+tab: ([('錯誤', ["儲存文件失敗：[WinError 5] 存取被拒。: '...\\.alpha.dep.<tmp>' -> '...\\alpha.dep'", 'OK'])], 'alpha - DotExpress')`; `input: 'alpha edited'`; `close, esc: running` with one `dialog: {'title': '無法儲存文件', 'main': "儲存文件失敗：[WinError 5] 存取被拒。: '...' -> '...\\alpha.dep'", 'content': '上次成功儲存之後的修改尚未儲存。如果不儲存就關閉，這些修改將會遺失。', 'buttons': ['重試(R)', '不儲存就關閉(W)', '取消'], 'focus': '重試(R)', 'presses': 1}`; `input after esc: 'alpha edited' title: alpha - DotExpress`; `close, enter while locked, unlock, enter: exited` with two such dialogs (each with its own `<tmp>`); `alpha members changed: True text: 'alpha edited' files: ['alpha.dep', 'beta.dep', 'new.dep'] tmp: []`; `after restart: ['alpha', 'beta', 'new'] title: alpha - DotExpress input: 'alpha edited'`; `close: ([], 'exited')` | Ctrl+Tab the same; Close: the error box (`OK` only, F-W9), vetoed |
| 39 | Ctrl+Tab as in 38; `close, alt-w: exited` with one dialog as in 38; `alpha members changed: False text: 'alpha body'`, `tmp: []`; `after restart: ... input: 'alpha body'`; `close: ([], 'exited')` | not possible (vetoed) |
| 40 | `input: 'A\ud83dB'`; `ctrl+tab: ([], 'beta - DotExpress')`; `alpha.txt: 41 ef bf bd 42`; `ctrl+shift+tab: ([], 'alpha - DotExpress') input: 'A\ufffdB'`; `ctrl+tab again: ([], 'beta - DotExpress')`; `alpha not rewritten: True tmp: []`; `close: ([], 'exited')`; `after restart: ['alpha', 'beta', 'new'] title: alpha - DotExpress input: 'A\ufffdB'`; `close: ([], 'exited')` | `儲存文件失敗：'utf-8' codec can't encode character '\ud83d' ...` at every switch; Close vetoed |

- [ ] **Step 4: Re-runs with changed expectations** (Git Bash, from the repository root). Item 19 starts from a copy of item 18's documents (`--seed`, a new folder); item 20 is the second half of `item19.py`. Defender real-time protection must be on for item 33 (the script prints it).

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto
EXE=/d/dxtest/N-f5/DotExpress.exe
export PYTHONIOENCODING=utf-8
cd $REPO
H3=docs/superpowers/history/2026-10-09-03-windows-verification/auto
H5=docs/superpowers/history/2026-10-09-05-f3-dep-atomic-write/auto
"$UIA" $H/rerun.py $H3/item18.py $EXE /d/dxtest/auto18-f5 > /d/dxtest/auto18-f5.log 2>&1
"$UIA" $H/rerun.py $H3/item19.py $EXE /d/dxtest/auto19-f5 --seed /d/dxtest/auto18-f5 > /d/dxtest/auto19-f5.log 2>&1
"$UIA" $H/rerun.py $H3/item20b.py $EXE /d/dxtest/auto20b-f5 > /d/dxtest/auto20b-f5.log 2>&1
"$UIA" $H/rerun.py $H5/item33.py $EXE /d/dxtest/auto33-f5 > /d/dxtest/auto33-f5.log 2>&1
```

Expected:

| # | Expected after F-5 | Before (F-3, `2026-10-09-05-f3-dep-atomic-write/auto-results.md`) |
| --- | --- | --- |
| 18 | unchanged: `Alpha` renamed to `alpha` keeps its text; `ALPHA` and `Alpha` refused as duplicates (`文件「ALPHA」已存在。`, `文件「Alpha」已存在。`); `disk diff: {}`; every `close: exited` | same |
| 19 r, 19 rw | the save is skipped and the name dialog appears: `rename alpha->Alpha while locked: ('重新命名文件', [], [('錯誤', ["儲存文件失敗：[WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用。: '...\\alpha.dep' -> '...\\.alpha.dep.<8 characters>.tmp'", 'OK'])], [])`; `list: ['alpha', 'new'] diff: {} files: ['alpha.dep', 'new.dep']`; `close: exited`; after the restart unchanged | the save failed with `[WinError 5]`, no name dialog |
| 20 | `rename alpha->Alpha with +r: ('重新命名文件', [], [('錯誤', ["儲存文件失敗：[Errno 13] Permission denied: '...\\alpha.dep'", 'OK'])], [])` (the name dialog, then F-3 D7's refusal); `state` with `alpha.dep` `R`; **`close: exited`**; `final:` without `R`, no `.tmp` | no name dialog; `close: ... STILL RUNNING -> killed` (F-W10) |
| 20b | `rename Alpha->alpha with +r: ('重新命名文件', [], [('錯誤', ["儲存文件失敗：[Errno 13] Permission denied: '...\\Alpha.dep'", 'OK'])], [])`; `list: ['Alpha', 'new']`, `Alpha.dep` `R`; **`close: exited`** | no name dialog; Close vetoed (F-W10) |
| 33 | `Defender real-time protection: True`; 20 lines `ok [] []`; `failures: 0`; `alpha text: 'alpha edit 19'`, `beta text: 'beta edit 20'`; `files: ['alpha.dep', 'beta.dep', 'new.dep']` | same |

- [ ] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto-results.md` in the style of `2026-10-09-05-f3-dep-atomic-write/auto-results.md` and `2026-10-09-06-f4-keep-invalid-bopomofo-rows/auto-results.md` (zh-TW): the build (PyInstaller version, `Build complete!`, the bundled modules, size, sha256), the smoke test, then one row per item (36, 37 r, 37 rw, 38, 39, 40, 18, 19 r, 19 rw, 20, 20b, 33) with ✔/△/✘ and the observed messages, dialogs and listings. Any deviation from the tables above is reported to the orchestrator before the commit, not explained away; a re-run after a GUI timing problem is recorded with the first attempt's log name, as F-3 did. End the file with a short section **「仍需人工（使用者）」** for item 41, worded for the user:

  > 41（NVDA）：請在 NVDA 執行中檢查關閉時的「無法儲存文件」對話框。把 `D:\dxtest\N-f5\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual41-f5\` 再執行；新增文件 `alpha` 並輸入一些文字，關閉後重新開啟，再修改 `alpha` 的內文；在命令提示字元執行 `attrib +r D:\dxtest\manual41-f5\workspace\alpha.dep`；然後關閉 DotExpress。請記錄 NVDA 依序讀出的內容（標題、錯誤那一行、說明句子、目前焦點的按鈕），並確認：Tab 與 Shift+Tab 在「重試」「不儲存就關閉」「取消」三個按鈕間移動，且每個按鈕都被讀出；Esc 取消（DotExpress 保持開啟，修改仍在）；再關閉一次，Alt+R 重試（對話框再次出現）；最後執行 `attrib -r D:\dxtest\manual41-f5\workspace\alpha.dep` 再按 Alt+R（存檔後結束），或改按 Alt+W（不儲存就關閉）。

```bash
cd $REPO
git add docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto-results.md docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/f5gui.py docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/rerun.py docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/item36.py docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/item38.py docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto/item40.py
git commit -q -m "docs: record the F-5 packaged-build GUI checks (F-5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short -- client docs scripts
git rev-parse HEAD:client
```

Expected: no `status` output, and the Task 3 tree id `8f8ee46eb955cbc579ca7df8bc8c1345ee006014` (the commit touches no file under `client/`). Do not merge `main` or push; the orchestrator decides.

## Implementation Notes (2026-10-10)

Tasks 0-5 were executed in the main checkout. Every `File:` and `Edit:` block was applied by a script that read it from this file (CRLF-aware, each old text exactly once), so no block was retyped. Every red and green run, count, catalog step and expected block matched, except for the plan error below and its consequences.

1. **Plan error in A2 (`test_replace_lone_surrogates_joins_split_pairs_and_keeps_other_text`).** The block's first assertion holds the literal astral character U+1F600 where the escaped split pair (`\ud83d` followed by `\ude00`, as in spec Test Plan A2) was meant: the tool that wrote this plan turned the valid escape pair into the character, while lone surrogates stayed escaped. As written, the input holds no surrogate, so the test returned the same object and never tested the join (the `replacement-through-utf-8` mutant gives six U+FFFD for the pair and passed it). The block was applied exactly first; the staged tree was `855670fe907c9634a341451694c79635a02ebd61`, as in the plan. Then that one line was changed to the escaped pair (with a script that built the escapes from code points; an editor tool turned the typed escapes back into the character). Consequences:
   - Committed `HEAD:client` trees: Task 1 `01861fd40d657b6ee565e6d15a4d1ac538330077`, Task 2 `cd438c11b60b1d94468379f57c37e70119b55c54`, Task 3 (and 5) `640d67bf4061e107e34bddb64043bdcc78fa89fa`. With the plan's blob of `client/tests/test_document_workspace.py` (`f90e532`) put back in a temporary index, Tasks 2 and 3 give the plan's `5d36ba64...` and `8f8ee46e...`, so nothing else differs. The seven production and catalog sha256 values after Task 3 are the dry run's.
   - Task 4 Step 6: `replacement-through-utf-8` and `replacement-with-a-question-mark` are now caught by 8 tests instead of 7 (the extra one is this test). Every other mutant line is identical; exit 0.
   - The Global Constraint "new test code is ASCII" does not hold for the plan's blocks (literal braille, U+FFFD and CJK test data). They were kept: the test files already contain non-ASCII text and the tree ids depend on it.
2. **Task 5.** The UIA venv's `Scripts\python.exe` was missing and was restored with `py -3.13 -m venv --upgrade` (pywinauto 0.6.9, psutil 7.2.2 unchanged). The build took 53 s; the exe is 48,743,184 bytes (sha256 `0A0288538B2F33D81B4EEB27CF92D8E7E573931C12ECF825C803F9C050EDC312`). The smoke test and every item matched Steps 2-4, each run once, every key `presses: 1`.
3. **Spec Correction 7 not reproduced.** In this run the old `dx.dismiss` closed the wx `OK` error box at its first call every time (5 of 5 in a throwaway probe on N-f5, and every box of item 19/20 on the pre-F-5 build `N-f4m`). The lost clicks of the dry run were most likely the timing effect that `f5gui.answer` already handles. F-3's item 20 `STILL RUNNING -> killed` was reproduced on `N-f4m` with `f5gui.dismiss`: the box closed and the process stayed running, so F-W10's close veto was real. Details are in `docs/superpowers/history/2026-10-10-01-f5-save-failure-handling/auto-results.md`.
