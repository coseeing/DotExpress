# Unreadable Dictionaries (F-6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix F-W12. Dictionary Management always opens: each dictionary is read on its own, one that cannot be read shows `無法讀取` ("Unreadable") in the count column, the others keep their counts, and the failure is logged to `gui.log`. Selecting an unreadable dictionary shows a labeled, read-only, multi-line field under the list with the reason (text selected, the next Tab stop). Edit reads the file again: if it still cannot be read, the reason is shown in an error box and the dialog stays open; a file fixed meanwhile opens. The frame guards the editor's constructor. Import reads the whole file and refuses a file that is not UTF-8 or not valid CSV with the same reason. Delete, Rename, Export and conversion are unchanged. Seven new msgids (357 -> 364), translated, with `.pot`, `.po` and `.mo` regenerated.

**Architecture:** Four commits on the client, each red first, in the spec's migration order. Task 1 adds `client/dictionaries/read_problems.py` (classification, reasons, logging, `read_dictionary_count`) and makes the count column of `DictionaryManagementDialog` per file (D1, D2, D8). Task 2 adds the reason row and the re-read on Edit to the dialog and the editor guard to `client/gui.py` (D3, D5, D6). Task 3 makes `validate_dictionary_csv` read every row and gives the presenter's Import a branch for read errors (D9). Task 4 regenerates and translates the catalogs (D11). Task 5 verifies (suite, shuffled order, catalogs, fixtures, application data, 22 mutants), Task 6 builds the exe and runs the GUI checks (items 42-51; item 52 stays manual).

**Tech Stack:** Python 3.13 standard library (`csv`, `enum`, `dataclasses`, `logging`, `gettext`, `unittest`, `unittest.mock`), wxPython 4.2.5 (`wx.TextCtrl` with `TE_MULTILINE | TE_READONLY`, `wx.StaticText`), GNU gettext 0.23 (`xgettext`, `msgmerge`, `msgfmt`, `msgattrib`), Git Bash `unix2dos`. Windows 11, the main checkout's `client\.venv` (PyInstaller 6.21.0). The GUI checks use pywinauto 0.6.9 and psutil in a separate venv.

**Spec:** `docs/superpowers/specs/2026-10-10-f6-unreadable-dictionaries-design.md` (+ `_zh-TW.md`), commit `eb2a88f`, with the section "Corrected after planning" added in the plan commit (both languages). The user decided U1 and U2 (2026-10-10); O1-O8 are the orchestrator's recommended defaults (the user may override them before the merge). No open question blocks the plan.

## Global Constraints

- Work in the main checkout `D:\workspace\DotExpress`, branch `fix/f6-unreadable-dictionaries` (HEAD is the plan commit on top of `eb2a88f`, which is on top of `main` at `e46ff26`). Never switch branches, never push, never merge, never rewrite history. `D:\workspace\DotExpress-f7` is another task's worktree: do not touch it.
- Files that may change (15 under `client/`, nothing else): production `client/dictionaries/read_problems.py` (new), `client/dialog.py`, `client/gui.py`, `client/dictionaries/presenter.py` (**tabs**), `client/dictionaries/manager.py` (4 spaces); catalogs `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` (tool output plus one group of `Edit:` blocks on the `.po`); tests `client/tests/test_dictionary_read_problems.py` (new), `client/tests/test_dictionary_management_dialog.py`, `client/tests/test_dictionary_presenter.py` (**tabs**), `client/tests/unreadable_dictionary_files.py` (new), `client/tests/test_dictionary_manager.py`, `client/tests/test_gui_document_flows.py`, `client/tests/test_i18n.py` (4 spaces); in Task 6 the new history folder `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/` (scripts with tabs, results). `client/tests/wx_stub.py` does not change (the dialog tests never run `_build_ui`).
- Never touch `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/` (the user's application data in this checkout; the tests use temporary folders, the new test modules isolate the `dotexpress.gui` logger, and Task 0 and Task 5 compare their sha256), `client/braille/tables/__tables.py`, `client/braille/tables/__init__.py` (CRLF bytes), tracked `client/braille/` content, `client/braille/liblouis/`, `client/tests/fixtures/`, `client/conversion/`, `client/dictionaries/entries.py`, `scripts/`, `vendor/`, the submodule pointers, the untracked `client2/`, `preprocessing/`, `testdata/`, or the committed scripts and data of earlier history folders. Never run `py scripts\sync-nvda.py`. Never start `gui.py` from source in the main checkout. `git status --short -- client docs scripts` must stay empty between commits (the untracked folders at the root are not part of it).
- The checkout uses `core.autocrlf=true` (LF in the index, CRLF in the working tree). Apply the blocks **with a script that reads them from this file** (`$T/tools/apply_blocks.py`, Task 0 Step 3), not by hand: a `File:` block is written as is (LF is fine; git normalizes it); an `Edit:` block is the line ``Edit: `path` `` followed by two fenced blocks, the exact old text and its replacement; the old text must occur exactly once in the file at that point (compare with CRLF converted to LF, keep the file's line endings). The blocks of one step are applied in order. Never edit with MSYS `sed -i` and never paste code through a shell heredoc. The Edit/Write tools turn `\uXXXX` escapes into the characters they stand for; the blocks contain such escapes (the test data), so a block typed or pasted through those tools changes the tree. After applying a step, `grep -c` the escapes listed in that step if in doubt; the tree id check catches it anyway.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf` (`git show HEAD:<path> | sha256sum`), unchanged.
- After each commit, `git rev-parse HEAD:client` must print the tree id given in that task (the dry run's). If it differs, stop and diff the files against the blocks of that task. Task 4's tree id holds because its Step 3 pins the `.pot` header date.
- Commits: `git commit -m "<subject>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`; stage only the files the task names, explicitly; never `git commit -F -`.
- The only failing test before and after F-6 is the F-W6 error `test_dictionary_name_prompt ... test_case_only_rename_still_renames` (out of scope).
- Expected-output blocks come from the replay (see Dry Run). Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers and exception lines cut to 160 characters and printed once, `Ran` without timing, the final status; the client folder as `<client>`, temporary folders as `<tmp>`). Commands print to stdout only; git's CRLF warnings and gettext's progress go to stderr and are not part of the expected blocks.
- Shell: Git Bash. Each tool call starts a new shell, so set the variables in every call (`SP` is your session scratchpad in Git Bash form; `T` holds the throwaway tools and must be outside the repo):
  ```bash
  REPO=/d/workspace/DotExpress
  MAIN=$REPO
  PY=$MAIN/client/.venv/Scripts/python.exe
  SP=/c/Users/<you>/AppData/Local/Temp/claude/<project>/<session>/scratchpad
  T=$SP/f6impl
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `MAIN` is the same folder as `REPO` here; the dry run used a scratch clone as `REPO`, and the commands that read the user's application data or copy the git-ignored runtime use `MAIN`. Task 6 uses PowerShell for the build.

## Spec Corrections and Refinements (decided in this plan)

These are also written into both spec files under "Corrected after planning" in the plan commit. The dry run found no error in decisions D1-D11 or in the behavior table; the total count (`Ran 1335`) holds.

1. **A shared test-data module** `client/tests/unreadable_dictionary_files.py` (4 spaces, ASCII) holds the files the four test modules need: `BIG5`, `LATE_BIG5`, `UTF16`, `FIELD_LIMIT`, `READABLE`, `UTF8_FIXED` and `big5_decode_error()`. It is one more file than acceptance criterion 6 lists.
2. **The Big5 row is `臺北,ㄊㄞˊㄅㄟˇ,Bopomofo`** (in the files as `\u` escapes), in the tests and in the GUI items. Braille patterns (U+2800-28FF) do not exist in cp950, so the spec's `臺北,⠞⠺,Braille` cannot be written as Big5; the Bopomofo sequence can, and it parses, so the same row saved again as UTF-8 counts as 1 entry (item 44). The late-Big5 file has 1,000 ASCII rows (17,019 bytes before the Big5 row, more than two 8 KiB decoder chunks).
3. **Counts per commit: `Ran 1321`, `1329`, `1334`, `1335`** (8 + 6, 8, 5, 1 new tests; `FAILED (errors=1, skipped=7)` throughout, F-W6 only). There are two Windows-only tests (R7 and M12), not three; both run on Windows. Every new test is red before its commit, `test_dictionary_read_problems` as a module import error in Task 1.
4. **Test refinements.** M12 is named `test_dictionary_held_open_without_sharing_is_unreadable` in Task 1 (no reason row yet) and gains the reason-row assertion in Task 2. `_make_dialog` gains `_dictionary_read_errors`, the fake reason label and field, `Layout` and `edit_dictionary_name = None`, but **not** `show_error = Mock()`: that would hide the real view method that `DictionaryManagementViewTest` tests; the Edit tests set it themselves. M11 makes `GetTextExtent` return 200 for `_("Unreadable")` and 40 for anything else, so it holds before and after the catalog step (both labels are four characters in zh-TW). R1 adds a plain `ValueError` (`OTHER`), R5 an injected `OSError(22)` (one line, no traceback). The presenter tests (P) compute the expected reason from the error that `load_dictionary_entries` raises for the same file.
5. **Edit (D5) refreshes the virtual list** with `list_ctrl.Refresh()` after the re-read, and the frame's guard (D6) keeps `with editor as entries_dialog: entries_dialog.ShowModal()`, so the existing frame test that asserts `__enter__().ShowModal()` is unchanged. Only the constructor is guarded.
6. **The reason field is `size=(-1, self.GetCharHeight() * 4)`** ("about three text lines": 3.6 lines of the field's format rectangle). Measured in the dry run with real wx in a scratch clone (pixels of a process that is not DPI-aware): the dialog keeps today's size (538 x 287); the list is 154 px high, 66 px while the reason row is shown; the zh-TW `NOT_UTF8` reason is 61 characters, wholly selected (`GetSelection()` = `(0, 61)`).
7. **Logging.** The type name of a CSV error is `Error` (`_csv.Error.__name__`), so its log line reads `Cannot read dictionary "x.csv": Error: field larger than field limit (131072)`.
8. **Catalogs.** `msgmerge` fuzzy-matches **two** new entries: `Why this dictionary cannot be read:` gets the msgstr of `The default dictionary cannot be deleted.` (`預設字典無法刪除。`) and `Dictionary "{name}" cannot be read.` that of `Dictionary "{name}" already exists.` (`字典「{name}」已存在。`); the other five are left empty (`357 translated messages, 2 fuzzy translations, 5 untranslated messages.`). `The file cannot be read: {error}` is not fuzzy-matched. One group of `Edit:` blocks fills the seven msgstr values and drops both flags; a second `msgmerge` changes nothing.
9. **Windows verification.** Item 46 denies read access on a UTF-8 file `acl.csv` instead of `big5.csv`, so the reason can only come from the ACL; item 47's `alpha.csv` is written by the script (not created through 新增). Items 42-45 run in one script (`item42.py`, one folder), 48 and 49 in `item48.py`, 50 and 51 in `item50.py`. wx shows the Edit error box as a task dialog whose main instruction is the headline and whose content is the reason (the message's blank line splits them). Shift+Tab from the reason field lands on the selected list item (UIA `ListItem` `big5`). The GUI scripts ran in the dry run against a build of the same code (see Dry Run).

## Dry Run

The plan was executed on scratch clones of the branch at `eb2a88f` with a stand-in plan commit (this plan and the corrected spec files) and a local `main` at `e46ff26` (`$SP/f6plan/r*`, never the main checkout), by F-5's harness: it writes every `File:` block, applies every `Edit:` block exactly once (CRLF-aware), runs every `bash` block from `client/` with `REPO` set to the clone and `MAIN` to the main checkout (so Task 0's guarded copies filled the clone, and the application-data check read the real data read-only), and compares its stdout with the following `text` block. The final replay (Tasks 0-5 from a fresh clone) matched every expected block, including all red runs, the per-commit tree ids, the catalog steps, the six shuffle seeds and the mutation output; no `client/log` folder appeared in the clone (every module that can log isolates the `dotexpress.gui` logger). Final sha256 after Task 4 (`git show HEAD:<path>`): `client/dictionaries/read_problems.py` `1c26c04c6b52e43dd8fc888c7d66e0e6e3d8c850fbdd3f34c6c4a15a17d42bb1`, `client/dialog.py` `3dd5dda1cacbbce083136d8c4c1ea22283c884c26df43fa007a0d9212f1e42b1`, `client/gui.py` `fe2127cdbf83563c0b8c3965811308aa738cc11527df45742d7ea6d4dc490242`, `client/dictionaries/manager.py` `b88a05bd14f52dc54b18f85a6c806cc592f89b3f50067ae6a1b973ee2198ca68`, `client/dictionaries/presenter.py` `6416bfa087d41d693399f77189a5f335b152e0392924d86a43d747c5afdd5899`, `client/locales/dotexpress.pot` `7cb6a45d08b5814f539d075fbb5d69152dfbc0f5cc9f15715543e2eef44b5cd1`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` `3c4e965342e81acf2c1572f2d651b616a47d1f6ed20edf0d4c52a71f48badd19`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` `44037940975b324d8f7f9fd3259f654a1c26d0e785601a57ea4618c10995b5cb`.

Task 6 was run too, against a build of the same code from a scratch clone (the command of Step 1: "Build complete!" in 49 s, 48,748,944 bytes; the four modules from the clone). The scripts of Step 2 (in their final form; the first run of item 46 found that the Save dialog has hidden buttons before 存檔, which `f6gui.file_dialog` now skips) printed exactly the lines of Step 3's table for items 42-51, each item once with no repeat, and item 42 on `N-f5b` printed Step 4's "did not open" line. Everything ran in `D:\dxtest\dry*-f6` folders, deleted afterwards. Item 52 (NVDA) was not run.

## Review Focus

1. **No dictionary file is ever written by F-6** (U2): `read_problems` only reads; Import refuses before copying (P tests; Task 6 records the sha256 of every test file before and after each item).
2. **One bad file never hides the others or breaks the dialog**: the count column, the item count and the names stay consistent after every refresh (M1-M3; mutants `counts-without-the-per-file-catch`, `unreadable-counted-as-zero`).
3. **The reason is reachable without a mouse** and read in full: the field follows the list in the Tab order, has the label as its name, is multi-line, and its text is selected (M4-M6; GUI items 43 and 45; NVDA item 52 is the user's).
4. **Edit is honest**: it reads the file again, never closes the dialog for an unreadable file, and opens a fixed one (M7-M9); the frame guard covers the remaining race (G1, G2).
5. **Logging stays small and the tests never write the real log**: one line per expected error, a traceback only for an unexpected one (R5, R6, M3, G1, G2); every module that can log isolates `dotexpress.gui`.

## File Map

- Task 1: new `client/tests/unreadable_dictionary_files.py` (test data), new `client/tests/test_dictionary_read_problems.py` (R1-R8), `client/tests/test_dictionary_management_dialog.py` (log isolation, `_make_dialog`, `_DictionaryFilesTestCase`, `UnreadableDictionaryCountTest` M1-M3, M10-M12); new `client/dictionaries/read_problems.py`; `client/dialog.py` (`_dictionary_read_errors`, `_get_item_text`, `_load_dictionary_counts`, `_store_count`, `_resize_columns`).
- Task 2: `client/tests/test_dictionary_management_dialog.py` (`_FakeControl`, `_make_dialog`, M12's reason assertion, `ReadProblemReasonTest` M4-M9), `client/tests/test_gui_document_flows.py` (`_open_management(editor_error=...)`, G1, G2); `client/dialog.py` (`_build_ui` reason row, `_update_read_problem`, `refresh_dictionaries`, `_on_selection_changed`, `_on_edit`); `client/gui.py` (`on_open_dictionary_management`).
- Task 3: `client/tests/test_dictionary_manager.py` (P1: 2 tests), `client/tests/test_dictionary_presenter.py` (P2: 3 tests); `client/dictionaries/manager.py` (`validate_dictionary_csv`), `client/dictionaries/presenter.py` (`import_from_file`).
- Task 4: `client/tests/test_i18n.py` (I1); `client/locales/` (three files).
- Task 6: new `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/` (`auto/f6gui.py`, `auto/lockx.py`, `auto/item42.py`, `auto/item46.py`, `auto/item47.py`, `auto/item48.py`, `auto/item50.py`, `auto-results.md`).

## Expected Counts (Windows, `discover -s tests`)

| After task | tests added | `Ran` | final line | `HEAD:client` |
| --- | --- | --- | --- | --- |
| baseline (`eb2a88f` + plan) | - | 1307 | `FAILED (errors=1, skipped=7)` | `9503872e0082fc9799e11c7f97ff53b6f02e15b7` |
| 1 per-file counts | 14 (R1-R8, M1-M3, M10-M12) | 1321 | `FAILED (errors=1, skipped=7)` | `d20554f30b8331a9e113f481d695349b0288139a` |
| 2 reason row, Edit, guard | 8 (M4-M9, G1, G2); M12 extended | 1329 | `FAILED (errors=1, skipped=7)` | `290c21bd3c83c5a2f4cc48b73ab0da4ffb3f84d9` |
| 3 Import | 5 (P1: 2, P2: 3) | 1334 | `FAILED (errors=1, skipped=7)` | `01e8a26c795433d8e5fd14d945b8d77c2067f4bb` |
| 4 catalogs | 1 (I1) | 1335 | `FAILED (errors=1, skipped=7)` | `e995d5444d769da21245201c3771bb27d9026edc` |
| 6 GUI results (docs only) | - | 1335 | `FAILED (errors=1, skipped=7)` | `e995d5444d769da21245201c3771bb27d9026edc` |

The error is F-W6 throughout. The 7 skips are POSIX-only tests; the two new Windows-only tests (R7, M12) run. The spec's acceptance-criterion-2 set goes from `Ran 299`, `OK (skipped=1)` (without the new module) to `Ran 327`, `OK (skipped=1)`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0 by the block script: `brief.py`, `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` (the F-5 tools, unchanged), `mo_check.py` (F-5's, with the F-6 msgids), `f6_mutants.py` (22 mutants of the code after Task 4, run on a copy of `client/`; the repository is never changed) and `apply_blocks.py` (applies the `File:` and `Edit:` blocks of one step of this plan).

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

Expected (`status` and the diff print nothing; the merge base is `main` at `e46ff26`):

```text
docs: plan for unreadable dictionaries (F-6)
fix/f6-unreadable-dictionaries
e46ff269c659153d17be771faa7df1bd862be406
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

- [ ] **Step 3: Create the throwaway tools** in `$T/tools/` (outside the repo, never committed) by the block script. `brief.py`, `msgid_scan.py`, `shuffle_harness.py` and `pin_pot_date.py` are F-5's, unchanged.

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
each msgid that F-6 adds or reuses (msgfmt 0.23 leaves POT-Creation-Date out of the .mo
header, so the .mo does not depend on it). Output is UTF-8 (-I ignores PYTHONIOENCODING).
"""
import gettext
import sys

sys.stdout.reconfigure(encoding="utf-8")

MSGIDS = (
    "Unreadable",
    "Why this dictionary cannot be read:",
    'Dictionary "{name}" cannot be read.',
    'The file is not saved as UTF-8. Save it again in the "CSV UTF-8 (Comma delimited)" format, '
    "for example with Save As in Excel.",
    "The file cannot be opened. It may be in use by another program, or you may not have "
    "permission to read it. Close the other program and try again.",
    "The file is not a valid CSV file. Check for a quotation mark that is not closed. Details: {error}",
    "The file cannot be read: {error}",
    "Entries",
    "Error",
    "Failed to import dictionary: {error}",
)

with open(sys.argv[1], "rb") as stream:
    catalog = gettext.GNUTranslations(stream)
print("catalog keys:", len(catalog._catalog))
for msgid in MSGIDS:
    print(f"{msgid[:40]!r} -> {catalog.gettext(msgid)}")
````

File: `$T/tools/f6_mutants.py`

````python
"""Run the F-6 tests against deliberately broken code (throwaway, not committed).

Usage: python f6_mutants.py <client_dir> <scratch_dir> [mutant ...]

Copies <client_dir> (without .venv, log, the user data dictionary/, workspace/, build/,
dist/, config.json and __pycache__) to <scratch_dir>/client, fresh each run. For each
mutant it edits one file of the copy (one exact, unique replacement), runs the five
F-6 test modules there, prints which tests caught it and restores the file. The
repository is never changed. Matches the code after Task 4. Exit status 1 if a mutant is
not caught or its pattern is not found exactly once. Python runs with -B (no bytecode
is written): a restored file can have the size and modification second of the mutant,
and a cached .pyc would then shadow it.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

READ = "dictionaries/read_problems.py"
DIALOG = "dialog.py"
GUI = "gui.py"
MANAGER = "dictionaries/manager.py"
PRESENTER = "dictionaries/presenter.py"
NEW_IMPORT_BRANCH = (
	"\t\texcept (UnicodeDecodeError, csv.Error) as exc:\n"
	"\t\t\t# F-6 (D9): before ValueError, which UnicodeDecodeError also is. Nothing was copied.\n"
	'\t\t\tview.show_error(_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc)))\n'
	"\t\t\treturn None\n"
)
HEADER_BRANCH = (
	"\t\texcept ValueError:\n"
	'\t\t\tview.show_error(_("Imported file must contain text, braille, and type headers."))\n'
	"\t\t\treturn None\n"
)
MUTANTS = {
	# D1/D2: every dictionary is read on its own; an unreadable one shows "Unreadable".
	"counts-without-the-per-file-catch": (
		READ,
		"\texcept Exception as error:\n\t\tlog_dictionary_read_error(path, error)\n",
		"\texcept RuntimeError as error:\n\t\tlog_dictionary_read_error(path, error)\n",
	),
	"unreadable-counted-as-zero": (
		DIALOG,
		'\t\t\tif name in self._dictionary_read_errors:\n\t\t\t\treturn _("Unreadable")\n',
		"",
	),
	"store-count-keeps-a-stale-error": (DIALOG, "\t\t\tself._dictionary_read_errors.pop(name, None)\n", ""),
	"count-column-without-the-unreadable-label": (
		DIALOG,
		'for label in (_("Entries"), _("Unreadable"))',
		'for label in (_("Entries"),)',
	),
	# D1: classification, UnicodeDecodeError before ValueError.
	"decode-error-classified-after-value-error": (
		READ,
		"\tif isinstance(error, UnicodeDecodeError):\n\t\treturn DictionaryReadProblem.NOT_UTF8\n",
		"\tif isinstance(error, ValueError):\n\t\treturn DictionaryReadProblem.OTHER\n"
		"\tif isinstance(error, UnicodeDecodeError):\n\t\treturn DictionaryReadProblem.NOT_UTF8\n",
	),
	"permission-error-not-classified": (
		READ,
		"\tif isinstance(error, PermissionError):\n\t\treturn DictionaryReadProblem.CANNOT_OPEN\n",
		"",
	),
	"csv-error-not-classified": (
		READ,
		"\tif isinstance(error, csv.Error):\n\t\treturn DictionaryReadProblem.INVALID_CSV\n",
		"",
	),
	# D8: one line for an error from the file, a traceback for anything else.
	"no-log-line": (READ, "\t\tlog_dictionary_read_error(path, error)\n", ""),
	"traceback-for-a-decode-error": (
		READ,
		"isinstance(error, (UnicodeDecodeError, csv.Error, OSError))",
		"isinstance(error, (csv.Error, OSError))",
	),
	"no-traceback-for-an-unexpected-error": (READ, ", Path(path).name, exc_info=error)\n", ", Path(path).name)\n"),
	# D3: the reason row.
	"reason-row-not-hidden": (
		DIALOG,
		"\t\tself.read_problem_ctrl.Show(error is not None)\n",
		"\t\tself.read_problem_ctrl.Show(True)\n",
	),
	"reason-label-never-shown": (
		DIALOG,
		"\t\tself.read_problem_label.Show(error is not None)\n",
		"\t\tself.read_problem_label.Show(False)\n",
	),
	"no-select-all": (DIALOG, "\t\t\tself.read_problem_ctrl.SelectAll()\n", ""),
	"selection-change-keeps-the-old-reason": (
		DIALOG,
		"\t\tself._update_button_states()\n\t\tself._update_read_problem()\n\t\tevent.Skip()\n",
		"\t\tself._update_button_states()\n\t\tevent.Skip()\n",
	),
	"refresh-keeps-the-old-reason": (
		DIALOG,
		"\t\tself._update_button_states()\n\t\tself._update_read_problem()\n\n\tdef _update_read_problem",
		"\t\tself._update_button_states()\n\n\tdef _update_read_problem",
	),
	# D5: Edit reads the file again and stays open when it cannot be read.
	"edit-without-the-re-read": (
		DIALOG,
		"\t\tcount = read_dictionary_count(self._actions.dictionary_path(selected))\n",
		"\t\tcount = DictionaryCount(self._dictionary_counts.get(selected, 0), self._dictionary_read_errors.get(selected))\n",
	),
	"edit-closes-the-dialog-on-an-unreadable-dictionary": (
		DIALOG,
		"\t\t\tself.show_error(describe_unreadable_dictionary(selected, count.error))\n\t\t\treturn\n",
		"\t\t\tself.show_error(describe_unreadable_dictionary(selected, count.error))\n",
	),
	# D6: the frame guards the editor.
	"frame-without-the-editor-guard": (
		GUI,
		"\t\texcept Exception as error:\n\t\t\t# F-6 (D6)",
		"\t\texcept ZeroDivisionError as error:\n\t\t\t# F-6 (D6)",
	),
	"frame-guard-does-not-log": (GUI, "\t\t\tlog_dictionary_read_error(dictionary_path, error)\n", ""),
	# D9: Import reads the whole file and names the reason.
	"validate-reads-only-the-header": (MANAGER, "        for _row in reader:\n            pass\n", ""),
	"presenter-new-branch-after-value-error": (
		PRESENTER,
		NEW_IMPORT_BRANCH + HEADER_BRANCH,
		HEADER_BRANCH + NEW_IMPORT_BRANCH,
	),
	"import-error-without-the-reason": (
		PRESENTER,
		".format(error=describe_dictionary_read_error(exc)))\n",
		".format(error=exc))\n",
	),
}
MODULES = (
	"tests.test_dictionary_read_problems",
	"tests.test_dictionary_management_dialog",
	"tests.test_dictionary_manager",
	"tests.test_dictionary_presenter",
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
		shown = names if len(names) <= 6 else names[:6] + [f"and {len(names) - 6} more"]
		print(f"{mutant}: {len(names)} caught: {', '.join(shown) if names else 'NONE'}")
		if not names:
			status = 1
	return status


if __name__ == "__main__":
	sys.exit(main())
````

File: `$T/tools/apply_blocks.py`

````python
"""Apply the File: and Edit: blocks of one step of the F-6 plan (throwaway, not committed).

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

The tools above are themselves blocks: write them once by hand-free means, for example by extracting this step's `File:` blocks with a few lines of Python that read this file as bytes (never through the Edit/Write tools, which change `\uXXXX` escapes). From then on apply every step's blocks with `apply_blocks.py`, for example `$PY $T/tools/apply_blocks.py ../docs/superpowers/plans/2026-10-10-f6-unreadable-dictionaries.md $REPO $T "Task 1" "Step 1"`; it prints `N blocks applied` (Task 1 Step 1: 6, Step 2: 6; Task 2 Step 1: 7, Step 2: 7; Task 3 Step 1: 6, Step 2: 4; Task 4 Step 1: 1, Step 3: 3; Task 6 Step 2: 7).

- [ ] **Step 4: Baseline: full suite, focused modules, fixtures, msgids, catalogs, tree, application data.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_gui_document_flows tests.test_i18n tests.test_dictionary_entries 2>&1 | $PY $T/tools/brief.py
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
$PY -I $T/tools/msgid_scan.py $REPO/client
grep -c '^msgid ' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
LANGUAGE=C msgfmt --check --statistics -o $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
cmp $T/head.mo locales/zh_TW/LC_MESSAGES/dotexpress.mo && echo "msgfmt rebuilds the committed .mo byte for byte"
xgettext --version | head -1
git -C $REPO rev-parse HEAD:client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) > $T/app-data.sha256; wc -l < $T/app-data.sha256
```

Expected (the second `Ran` line is the spec's acceptance-criterion-2 set without the new module; the last line counts the files of the user's application data in the main checkout, including `client/log/`, recorded read-only for Task 5; if the user has used the app since the dry run, that number differs, which is fine):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1307 tests
FAILED (errors=1, skipped=7)
Ran 299 tests
OK (skipped=1)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
source msgids: 357 sha256 7ebbbe567cdc653a3bc755dc82512f061732fb2eabb9b01325d9d3f3386726c6
locales/dotexpress.pot:358
locales/zh_TW/LC_MESSAGES/dotexpress.po:358
357 translated messages.
msgfmt rebuilds the committed .mo byte for byte
xgettext.exe (GNU gettext-tools) 0.23
9503872e0082fc9799e11c7f97ff53b6f02e15b7
4
```

### Task 1: Open Dictionary Management when a dictionary cannot be read (D1, D2, D8)

- [ ] **Step 1: Red: the test data, R1-R8, M1-M3 and M10-M12.** The new modules use 4 spaces (test data) and tabs (R); the dialog test module keeps its tabs and now isolates the `dotexpress.gui` logger (`setUpModule` becomes a function). The dialog under test is loaded under the speech-dialog stub scope; the new dialog tests use real files only, no patch of `read_problems` (that scope evicts `dictionaries.*` modules first imported while loading, so a patch could hit another module object).

File: `client/tests/unreadable_dictionary_files.py`

````python
"""Dictionary files that cannot be read, for the F-6 tests.

Built in memory as bytes; the tests write them into temporary folders. ``BIG5`` is what
Excel's "CSV (Comma delimited)" writes on Traditional Chinese Windows (cp950);
``UTF8_FIXED`` is the same row saved again as CSV UTF-8, one entry the editor shows.
"""

HEADER = "text,braille,type\r\n"
# Taipei with its Bopomofo: every character exists in cp950, and the sequence parses.
TAIPEI_ROW = "\u81fa\u5317,\u310a\u311e\u02ca\u3105\u311f\u02c7,Bopomofo\r\n"
ASCII_ROWS = "".join(f"w{index:04d},x,General\r\n" for index in range(1000))

BIG5 = (HEADER + TAIPEI_ROW).encode("cp950")
UTF8_FIXED = (HEADER + TAIPEI_ROW).encode("utf-8")
# About 17 KB of ASCII rows first: the header and the first chunks decode as UTF-8.
LATE_BIG5 = (HEADER + ASCII_ROWS).encode("ascii") + TAIPEI_ROW.encode("cp950")
UTF16 = (HEADER + "w,x,General\r\n").encode("utf-16")
# One field longer than the csv module's limit of 131,072 characters.
FIELD_LIMIT = (HEADER + "long," + "x" * 140000 + ",General\r\n").encode("ascii")
READABLE = (HEADER + "Alpha,\u2801,General\r\n").encode("utf-8")


def big5_decode_error() -> UnicodeDecodeError:
    """The error that reading ``BIG5`` as a dictionary raises."""
    try:
        BIG5.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        return error
    raise AssertionError("BIG5 decodes as UTF-8")
````

File: `client/tests/test_dictionary_read_problems.py`

````python
import ast
import csv
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from dictionaries import read_problems
from dictionaries.read_problems import (
	DictionaryCount,
	DictionaryReadProblem,
	classify_dictionary_read_error,
	describe_dictionary_read_error,
	describe_unreadable_dictionary,
	read_dictionary_count,
)
from tests.file_log_isolation import isolate_file_logs
from tests.unreadable_dictionary_files import (
	BIG5,
	FIELD_LIMIT,
	LATE_BIG5,
	READABLE,
	UTF16,
	big5_decode_error,
)
from tests.windows_file_handles import hold_open

LOGGER = "dotexpress.gui"
NOT_UTF8 = (
	'The file is not saved as UTF-8. Save it again in the "CSV UTF-8 (Comma delimited)" format, '
	"for example with Save As in Excel."
)
CANNOT_OPEN = (
	"The file cannot be opened. It may be in use by another program, or you may not have "
	"permission to read it. Close the other program and try again."
)
INVALID_CSV = "The file is not a valid CSV file. Check for a quotation mark that is not closed. Details: {error}"
OTHER = "The file cannot be read: {error}"


def setUpModule():
	unittest.addModuleCleanup(isolate_file_logs(LOGGER))


class DictionaryReadProblemTestCase(unittest.TestCase):
	def setUp(self):
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.root = Path(temp_dir.name)

	def write(self, name, data):
		path = self.root / f"{name}.csv"
		path.write_bytes(data)
		return path


class DescribeTest(DictionaryReadProblemTestCase):
	def test_classifies_each_error(self):
		cases = (
			("Big5 file", big5_decode_error(), DictionaryReadProblem.NOT_UTF8),
			("in use or denied", PermissionError(13, "Permission denied"), DictionaryReadProblem.CANNOT_OPEN),
			("csv error", csv.Error("field larger than field limit (131072)"), DictionaryReadProblem.INVALID_CSV),
			("missing", FileNotFoundError(2, "No such file or directory"), DictionaryReadProblem.OTHER),
			("other OSError", OSError(22, "Invalid argument"), DictionaryReadProblem.OTHER),
			("other ValueError", ValueError("injected"), DictionaryReadProblem.OTHER),
			("anything else", RuntimeError("injected"), DictionaryReadProblem.OTHER),
		)
		for label, error, expected in cases:
			with self.subTest(label):
				self.assertIs(classify_dictionary_read_error(error), expected)

	def test_describes_each_problem(self):
		# Compared through the module's own _, so the test holds before and after the catalog step.
		csv_error = csv.Error("field larger than field limit (131072)")
		other_error = OSError(22, "Invalid argument")
		cases = (
			("not UTF-8", big5_decode_error(), read_problems._(NOT_UTF8)),
			("cannot open", PermissionError(13, "Permission denied"), read_problems._(CANNOT_OPEN)),
			("invalid CSV", csv_error, read_problems._(INVALID_CSV).format(error=csv_error)),
			("other", other_error, read_problems._(OTHER).format(error=other_error)),
		)
		for label, error, expected in cases:
			with self.subTest(label):
				self.assertEqual(describe_dictionary_read_error(error), expected)

	def test_unreadable_dictionary_message_has_headline_and_reason(self):
		error = big5_decode_error()

		message = describe_unreadable_dictionary("big5", error)

		headline = read_problems._('Dictionary "{name}" cannot be read.').format(name="big5")
		self.assertEqual(message, headline + "\n\n" + read_problems._(NOT_UTF8))


class ReadDictionaryCountTest(DictionaryReadProblemTestCase):
	def test_count_of_readable_and_missing_files(self):
		bopomofo_rows = (
			"text,braille,type\r\n"
			"Alpha,a,General\r\n"
			",b,General\r\n"
			"Beta,not bopomofo,Bopomofo\r\n"
		).encode("utf-8")
		cases = (
			("UTF-8", "plain", READABLE, 1),
			("UTF-8 with BOM", "bom", b"\xef\xbb\xbf" + READABLE, 1),
			("hidden rows are not counted (F-4)", "hidden", bopomofo_rows, 1),
			("missing file", "missing", None, 0),
		)
		for label, name, data, entries in cases:
			with self.subTest(label):
				path = self.write(name, data) if data is not None else self.root / f"{name}.csv"
				with self.assertNoLogs(LOGGER):
					count = read_dictionary_count(path)
				self.assertEqual(count, DictionaryCount(entries))
				self.assertIsNone(count.error)

	def test_count_of_unreadable_file_returns_the_error_and_logs_one_line(self):
		cases = (
			("Big5", BIG5, None, UnicodeDecodeError),
			("Big5 after 17 KB of ASCII rows", LATE_BIG5, None, UnicodeDecodeError),
			("UTF-16", UTF16, None, UnicodeDecodeError),
			("field over the CSV limit", FIELD_LIMIT, None, csv.Error),
			("in use or denied", READABLE, PermissionError(13, "Permission denied"), PermissionError),
			("other OSError", READABLE, OSError(22, "Invalid argument"), OSError),
		)
		for label, data, injected, error_type in cases:
			with self.subTest(label):
				path = self.write("broken", data)
				replaced = nullcontext() if injected is None else patch.object(read_problems, "load_dictionary_entries", side_effect=injected)
				with replaced, self.assertLogs(LOGGER, level="ERROR") as logs:
					count = read_dictionary_count(path)

				self.assertEqual(count.entries, 0)
				self.assertIs(type(count.error), error_type)
				self.assertEqual(
					[record.getMessage() for record in logs.records],
					[f'Cannot read dictionary "broken.csv": {error_type.__name__}: {count.error}'],
				)
				self.assertIsNone(logs.records[0].exc_info)

	def test_unexpected_error_is_logged_with_traceback(self):
		path = self.write("alpha", READABLE)
		error = RuntimeError("injected")

		with patch.object(read_problems, "load_dictionary_entries", side_effect=error):
			with self.assertLogs(LOGGER, level="ERROR") as logs:
				count = read_dictionary_count(path)

		self.assertEqual(count, DictionaryCount(error=error))
		self.assertEqual([record.getMessage() for record in logs.records], ['Unexpected error while reading dictionary "alpha.csv"'])
		self.assertIs(logs.records[0].exc_info[1], error)

	@unittest.skipUnless(sys.platform == "win32", "Windows file sharing")
	def test_file_held_open_without_sharing_cannot_be_opened(self):
		path = self.write("alpha", READABLE)
		hold_open(self, path, 0)

		with self.assertLogs(LOGGER, level="ERROR"):
			count = read_dictionary_count(path)

		self.assertIsInstance(count.error, PermissionError)
		self.assertIs(classify_dictionary_read_error(count.error), DictionaryReadProblem.CANNOT_OPEN)


class ReadProblemsModuleTest(unittest.TestCase):
	def test_module_does_not_import_wx(self):
		tree = ast.parse(Path(read_problems.__file__).read_text(encoding="utf-8"))
		imported = set()
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				imported.update(alias.name.split(".")[0] for alias in node.names)
			elif isinstance(node, ast.ImportFrom) and node.module:
				imported.add(node.module.split(".")[0])

		self.assertNotIn("wx", imported)


if __name__ == "__main__":
	unittest.main()
````

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
import csv
import inspect
import tempfile
import unittest
from pathlib import Path
```

```python
import csv
import inspect
import sys
import tempfile
import unittest
from pathlib import Path
```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python

from dictionaries.presenter import DictionaryManagementView
from tests import wx_stub


dialog, _DIALOG_SCOPE = wx_stub.load_speech_dialog()
setUpModule = _DIALOG_SCOPE.activate
tearDownModule = _DIALOG_SCOPE.deactivate


```

```python

from dictionaries.presenter import DictionaryManagementView
from tests import wx_stub
from tests.file_log_isolation import isolate_file_logs
from tests.unreadable_dictionary_files import BIG5, LATE_BIG5, READABLE, UTF16
from tests.windows_file_handles import hold_open


dialog, _DIALOG_SCOPE = wx_stub.load_speech_dialog()
LOGGER = "dotexpress.gui"


def setUpModule():
	_DIALOG_SCOPE.activate()
	# F-6: counting a dictionary that cannot be read logs to dotexpress.gui (gui.log).
	unittest.addModuleCleanup(isolate_file_logs(LOGGER))


tearDownModule = _DIALOG_SCOPE.deactivate


```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
	target._actions = actions if actions is not None else _FakeActions(dictionary_dir, names)
	target._dictionary_names = list(names)
	target._dictionary_counts = {}
	target._selected_name = names[0] if names else ""
	target.list_ctrl = _FakeListCtrl()
	target.add_button = Mock()
```

```python
	target._actions = actions if actions is not None else _FakeActions(dictionary_dir, names)
	target._dictionary_names = list(names)
	target._dictionary_counts = {}
	target._dictionary_read_errors = {}
	target._selected_name = names[0] if names else ""
	target.list_ctrl = _FakeListCtrl()
	target.add_button = Mock()
```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python

		with self.assertRaisesRegex(ValueError, "Unknown column"):
			target._get_item_text(0, 2)


class DictionaryManagementInteractionTest(unittest.TestCase):
```

```python

		with self.assertRaisesRegex(ValueError, "Unknown column"):
			target._get_item_text(0, 2)


class _DictionaryFilesTestCase(unittest.TestCase):
	"""Dictionary files in a temporary folder (F-6)."""

	def setUp(self):
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.root = Path(temp_dir.name)

	def write(self, name, data):
		(self.root / f"{name}.csv").write_bytes(data)

	def counts(self, target):
		return [target._get_item_text(index, 1) for index in range(target.list_ctrl.item_count)]


class UnreadableDictionaryCountTest(_DictionaryFilesTestCase):
	"""F-6 (D2): a dictionary that cannot be read shows "Unreadable"; the others keep their counts."""

	def test_unreadable_dictionary_shows_unreadable_and_the_others_their_counts(self):
		self.write("alpha", READABLE)
		self.write("big5", BIG5)
		self.write("default", b"text,braille,type\r\n")
		names = ["alpha", "big5", "default"]
		target = _make_dialog(self.root, names)

		with self.assertLogs(LOGGER, level="ERROR"):
			target.refresh_dictionaries(names, "default")

		self.assertEqual(target.list_ctrl.item_count, 3)
		self.assertEqual([target._get_item_text(index, 0) for index in range(3)], names)
		self.assertEqual(self.counts(target), ["1", dialog._("Unreadable"), "0"])
		self.assertEqual(target._dictionary_counts, {"alpha": 1, "default": 0})
		self.assertEqual(list(target._dictionary_read_errors), ["big5"])
		self.assertIsInstance(target._dictionary_read_errors["big5"], UnicodeDecodeError)
		self.assertEqual(target.list_ctrl.selected, 2)

	def test_refresh_after_an_action_keeps_names_counts_and_item_count_consistent(self):
		# Before F-6 the refresh raised after taking the new names: the list kept the old
		# item count and counts, and nothing was shown.
		self.write("alpha", READABLE)
		self.write("default", b"text,braille,type\r\n")
		actions = _FakeActions(self.root, ["alpha", "big5", "default"], results={"import": "big5"})
		target = _make_dialog(self.root, ["alpha", "default"], actions)
		target.refresh_dictionaries(["alpha", "default"], "default")
		self.write("big5", LATE_BIG5)

		with self.assertLogs(LOGGER, level="ERROR"):
			target._on_import_clicked(None)

		self.assertEqual(target._dictionary_names, ["alpha", "big5", "default"])
		self.assertEqual(target.list_ctrl.item_count, 3)
		self.assertEqual(self.counts(target), ["1", dialog._("Unreadable"), "0"])
		self.assertEqual(target.list_ctrl.selected, 1)

	def test_each_unreadable_dictionary_is_logged(self):
		self.write("alpha", READABLE)
		self.write("big5", BIG5)
		self.write("utf16", UTF16)
		names = ["alpha", "big5", "utf16"]
		target = _make_dialog(self.root, names)

		with self.assertLogs(LOGGER, level="ERROR") as logs:
			target.refresh_dictionaries(names, "alpha")

		errors = target._dictionary_read_errors
		self.assertEqual(
			[record.getMessage() for record in logs.records],
			[
				f'Cannot read dictionary "big5.csv": UnicodeDecodeError: {errors["big5"]}',
				f'Cannot read dictionary "utf16.csv": UnicodeDecodeError: {errors["utf16"]}',
			],
		)
		self.assertEqual([record.exc_info for record in logs.records], [None, None])

	def test_unreadable_dictionaries_keep_delete_rename_and_export_enabled(self):
		self.write("big5", BIG5)
		self.write("default", BIG5)
		names = ["big5", "default"]
		for selected, removable in (("big5", True), ("default", False)):
			with self.subTest(selected=selected):
				target = _make_dialog(self.root, names)

				with self.assertLogs(LOGGER, level="ERROR"):
					target.refresh_dictionaries(names, selected)

				target.delete_button.Enable.assert_called_with(removable)
				target.rename_button.Enable.assert_called_with(removable)
				target.edit_button.Enable.assert_called_with(True)
				target.export_button.Enable.assert_called_with(True)

	def test_count_column_fits_the_unreadable_label(self):
		target = _make_dialog(".", ["alpha"])
		unreadable = dialog._("Unreadable")
		target.list_ctrl.GetTextExtent = lambda text: (200 if text == unreadable else 40, 16)

		target._resize_columns()

		self.assertEqual(target.list_ctrl.column_widths, {0: 500 - 232, 1: 232})

	@unittest.skipUnless(sys.platform == "win32", "Windows file sharing")
	def test_dictionary_held_open_without_sharing_is_unreadable(self):
		self.write("alpha", READABLE)
		hold_open(self, self.root / "alpha.csv", 0)
		target = _make_dialog(self.root, ["alpha"])

		with self.assertLogs(LOGGER, level="ERROR"):
			target.refresh_dictionaries(["alpha"], "alpha")

		self.assertEqual(self.counts(target), [dialog._("Unreadable")])
		self.assertIsInstance(target._dictionary_read_errors["alpha"], PermissionError)


class DictionaryManagementInteractionTest(unittest.TestCase):
```

```bash
grep -c 'u81fa' tests/unreadable_dictionary_files.py
$PY -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog 2>&1 | $PY $T/tools/brief.py
```

Expected (the escapes are intact; the new module cannot be imported yet; the dialog raises on the first unreadable file, as F-W12 does, and the count column ignores `Unreadable`):

```text
1
ERROR: test_dictionary_read_problems (unittest.loader._FailedTest.test_dictionary_read_problems)
ImportError: Failed to import test module: test_dictionary_read_problems
ImportError: cannot import name 'read_problems' from 'dictionaries' (<client>\dictionaries\__init__.py)
ERROR: test_dictionary_held_open_without_sharing_is_unreadable (tests.test_dictionary_management_dialog.UnreadableDictionaryCountTest.test_dictionary_held_open_
PermissionError: [Errno 13] Permission denied: '<tmp>\\alpha.csv'
ERROR: test_each_unreadable_dictionary_is_logged (tests.test_dictionary_management_dialog.UnreadableDictionaryCountTest.test_each_unreadable_dictionary_is_logge
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte
ERROR: test_refresh_after_an_action_keeps_names_counts_and_item_count_consistent (tests.test_dictionary_management_dialog.UnreadableDictionaryCountTest.test_ref
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbb in position 635: invalid start byte
ERROR: test_unreadable_dictionaries_keep_delete_rename_and_export_enabled (tests.test_dictionary_management_dialog.UnreadableDictionaryCountTest.test_unreadable
ERROR: test_unreadable_dictionary_shows_unreadable_and_the_others_their_counts (tests.test_dictionary_management_dialog.UnreadableDictionaryCountTest.test_unrea
FAIL: test_count_column_fits_the_unreadable_label (tests.test_dictionary_management_dialog.UnreadableDictionaryCountTest.test_count_column_fits_the_unreadable_l
AssertionError: {0: 404, 1: 96} != {0: 268, 1: 232}
Ran 35 tests
FAILED (failures=1, errors=7)
```

- [ ] **Step 2: The read-problems module and the per-file counts** (`client/dictionaries/read_problems.py` new, `client/dialog.py`, tabs). `load_dictionary_entries` is no longer imported by `dialog.py`.

File: `client/dictionaries/read_problems.py`

````python
"""Why a dictionary file cannot be read, in words the user can act on (F-6).

Nothing here imports wx. The reasons are built with ``_`` at call time; they never
mention an encoding by name, so a file in any encoding other than UTF-8 gets the
same advice (DotExpress does not guess encodings).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dictionaries.entries import load_dictionary_entries
from i18n import _
from log import get_logger

logger = get_logger("dotexpress.gui", "gui.log")


class DictionaryReadProblem(Enum):
	NOT_UTF8 = "not_utf8"
	# In use by another program, or no permission to read it: opening the file for
	# reading reports both as the same PermissionError on Windows.
	CANNOT_OPEN = "cannot_open"
	INVALID_CSV = "invalid_csv"
	OTHER = "other"


def classify_dictionary_read_error(error: Exception) -> DictionaryReadProblem:
	# UnicodeDecodeError first: it is also a ValueError.
	if isinstance(error, UnicodeDecodeError):
		return DictionaryReadProblem.NOT_UTF8
	if isinstance(error, PermissionError):
		return DictionaryReadProblem.CANNOT_OPEN
	if isinstance(error, csv.Error):
		return DictionaryReadProblem.INVALID_CSV
	return DictionaryReadProblem.OTHER


def describe_dictionary_read_error(error: Exception) -> str:
	"""The reason, as one or more full sentences."""
	problem = classify_dictionary_read_error(error)
	if problem is DictionaryReadProblem.NOT_UTF8:
		return _(
			'The file is not saved as UTF-8. Save it again in the "CSV UTF-8 (Comma delimited)" format, '
			"for example with Save As in Excel."
		)
	if problem is DictionaryReadProblem.CANNOT_OPEN:
		return _(
			"The file cannot be opened. It may be in use by another program, or you may not have "
			"permission to read it. Close the other program and try again."
		)
	if problem is DictionaryReadProblem.INVALID_CSV:
		return _(
			"The file is not a valid CSV file. Check for a quotation mark that is not closed. Details: {error}"
		).format(error=error)
	return _("The file cannot be read: {error}").format(error=error)


def describe_unreadable_dictionary(name: str, error: Exception) -> str:
	"""A headline naming the dictionary, a blank line, then the reason."""
	headline = _('Dictionary "{name}" cannot be read.').format(name=name)
	return f"{headline}\n\n{describe_dictionary_read_error(error)}"


def log_dictionary_read_error(path: Path, error: Exception) -> None:
	"""One line for an error that comes from the file; a traceback for anything else."""
	if isinstance(error, (UnicodeDecodeError, csv.Error, OSError)):
		logger.error('Cannot read dictionary "%s": %s: %s', Path(path).name, type(error).__name__, error)
	else:
		logger.error('Unexpected error while reading dictionary "%s"', Path(path).name, exc_info=error)


@dataclass(frozen=True)
class DictionaryCount:
	entries: int = 0
	error: Exception | None = None  # None: the file could be read


def read_dictionary_count(path: Path) -> DictionaryCount:
	"""The number of entries the editor shows, or why the file cannot be read (logged)."""
	try:
		return DictionaryCount(len(load_dictionary_entries(path)))
	except Exception as error:
		log_dictionary_read_error(path, error)
		return DictionaryCount(error=error)
````

Edit: `client/dialog.py`

```python
	ENTRY_TYPE_LABELS,
	ENTRY_TYPE_OPTIONS,
	DictionaryEntry,
	load_dictionary_entries,
	validate_dictionary_entry,
)
from dictionaries.entry_list_model import DictionaryEntryListModel, DuplicateEntryError, EntryListUpdate
```

```python
	ENTRY_TYPE_LABELS,
	ENTRY_TYPE_OPTIONS,
	DictionaryEntry,
	validate_dictionary_entry,
)
from dictionaries.entry_list_model import DictionaryEntryListModel, DuplicateEntryError, EntryListUpdate
```

Edit: `client/dialog.py`

```python
	normalize_dictionary_name,
)
from dictionaries.presenter import DictionaryManagementActions
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
```

```python
	normalize_dictionary_name,
)
from dictionaries.presenter import DictionaryManagementActions
from dictionaries.read_problems import DictionaryCount, read_dictionary_count
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
```

Edit: `client/dialog.py`

```python
		self._dictionary_names = list(actions.dictionary_names)
		self._selected_name = selected_name
		self._dictionary_counts: dict[str, int] = {}
		self.edit_dictionary_name: str | None = None
		self._build_ui()
		self.refresh_dictionaries(self._dictionary_names, selected_name)
```

```python
		self._dictionary_names = list(actions.dictionary_names)
		self._selected_name = selected_name
		self._dictionary_counts: dict[str, int] = {}
		# F-6: the dictionaries that could not be read, with the error (their count is not known).
		self._dictionary_read_errors: dict[str, Exception] = {}
		self.edit_dictionary_name: str | None = None
		self._build_ui()
		self.refresh_dictionaries(self._dictionary_names, selected_name)
```

Edit: `client/dialog.py`

```python
		if column == 0:
			return name
		if column == 1:
			return str(self._dictionary_counts.get(name, 0))
		raise ValueError(f"Unknown column: {column}")

	def _load_dictionary_counts(self) -> None:
		self._dictionary_counts = {
			name: len(load_dictionary_entries(self._actions.dictionary_path(name)))
			for name in self._dictionary_names
		}

	def refresh_dictionaries(
		self,
```

```python
		if column == 0:
			return name
		if column == 1:
			if name in self._dictionary_read_errors:
				return _("Unreadable")
			return str(self._dictionary_counts.get(name, 0))
		raise ValueError(f"Unknown column: {column}")

	def _load_dictionary_counts(self) -> None:
		"""Read every dictionary on its own; one that cannot be read is kept with its error (F-6)."""
		self._dictionary_counts = {}
		self._dictionary_read_errors = {}
		for name in self._dictionary_names:
			self._store_count(name, read_dictionary_count(self._actions.dictionary_path(name)))

	def _store_count(self, name: str, count: DictionaryCount) -> None:
		if count.error is None:
			self._dictionary_counts[name] = count.entries
			self._dictionary_read_errors.pop(name, None)
		else:
			self._dictionary_counts.pop(name, None)
			self._dictionary_read_errors[name] = count.error

	def refresh_dictionaries(
		self,
```

Edit: `client/dialog.py`

```python
		available_width = max(0, self.list_ctrl.GetClientSize().width)
		if available_width == 0:
			return
		count_text_width = self.list_ctrl.GetTextExtent(_("Entries"))[0]
		count_width = min(available_width, max(96, count_text_width + 32))
		name_width = max(0, available_width - count_width)
		self.list_ctrl.SetColumnWidth(0, name_width)
```

```python
		available_width = max(0, self.list_ctrl.GetClientSize().width)
		if available_width == 0:
			return
		count_text_width = max(self.list_ctrl.GetTextExtent(label)[0] for label in (_("Entries"), _("Unreadable")))
		count_width = min(available_width, max(96, count_text_width + 32))
		name_width = max(0, available_width - count_width)
		self.list_ctrl.SetColumnWidth(0, name_width)
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog -v 2>&1 | grep -E "^test_(classifies_each|describes_each|unreadable_dictionary_message|count_of_|unexpected_error_is_logged|file_held_open|module_does_not_import_wx|unreadable_dictionary_shows|refresh_after_an_action|each_unreadable|unreadable_dictionaries_keep|count_column_fits|dictionary_held_open)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (the 14 new tests pass, the two Windows-only ones included):

```text
test_classifies_each_error ok
test_describes_each_problem ok
test_unreadable_dictionary_message_has_headline_and_reason ok
test_count_of_readable_and_missing_files ok
test_count_of_unreadable_file_returns_the_error_and_logs_one_line ok
test_file_held_open_without_sharing_cannot_be_opened ok
test_unexpected_error_is_logged_with_traceback ok
test_module_does_not_import_wx ok
test_count_column_fits_the_unreadable_label ok
test_dictionary_held_open_without_sharing_is_unreadable ok
test_each_unreadable_dictionary_is_logged ok
test_refresh_after_an_action_keeps_names_counts_and_item_count_consistent ok
test_unreadable_dictionaries_keep_delete_rename_and_export_enabled ok
test_unreadable_dictionary_shows_unreadable_and_the_others_their_counts ok
Ran 42 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1321 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/dictionaries/read_problems.py client/dialog.py client/tests/unreadable_dictionary_files.py client/tests/test_dictionary_read_problems.py client/tests/test_dictionary_management_dialog.py
git -C $REPO commit -q -m "fix: open Dictionary Management when a dictionary cannot be read (F-6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
d20554f30b8331a9e113f481d695349b0288139a
```

### Task 2: Explain why a dictionary cannot be read (D3, D5, D6)

- [ ] **Step 1: Red: M4-M9, M12's reason, G1 and G2.** The fake reason label and field record `Show`, `ChangeValue` and `SelectAll`; `_open_management` of the frame tests gains `editor_error` (the side effect of the patched `DictionaryEntriesDialog`).

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
from unittest.mock import MagicMock, Mock, patch

from dictionaries.presenter import DictionaryManagementView
from tests import wx_stub
from tests.file_log_isolation import isolate_file_logs
from tests.unreadable_dictionary_files import BIG5, LATE_BIG5, READABLE, UTF16
from tests.windows_file_handles import hold_open


```

```python
from unittest.mock import MagicMock, Mock, patch

from dictionaries.presenter import DictionaryManagementView
from dictionaries.read_problems import describe_dictionary_read_error, describe_unreadable_dictionary
from tests import wx_stub
from tests.file_log_isolation import isolate_file_logs
from tests.unreadable_dictionary_files import BIG5, LATE_BIG5, READABLE, UTF16, UTF8_FIXED
from tests.windows_file_handles import hold_open


```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
		self.column_widths[column] = width


class _FakeActions:
	"""Stands in for the presenter: fixed names, scripted results, recorded calls."""

```

```python
		self.column_widths[column] = width


class _FakeControl:
	"""The reason label or field of Dictionary Management (F-6): records what the dialog does."""

	def __init__(self):
		self.shown = False
		self.value = ""
		self.calls = []

	def Show(self, show=True):
		self.shown = show
		self.calls.append(("Show", show))

	def ChangeValue(self, value):
		self.value = value
		self.calls.append(("ChangeValue", value))

	def SelectAll(self):
		self.calls.append(("SelectAll",))


class _FakeActions:
	"""Stands in for the presenter: fixed names, scripted results, recorded calls."""

```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python
	target.edit_button = Mock()
	target.import_button = Mock()
	target.export_button = Mock()
	target.EndModal = Mock()
	return target


```

```python
	target.edit_button = Mock()
	target.import_button = Mock()
	target.export_button = Mock()
	target.read_problem_label = _FakeControl()
	target.read_problem_ctrl = _FakeControl()
	target.Layout = Mock()
	target.EndModal = Mock()
	target.edit_dictionary_name = None
	return target


```

Edit: `client/tests/test_dictionary_management_dialog.py`

```python

		self.assertEqual(self.counts(target), [dialog._("Unreadable")])
		self.assertIsInstance(target._dictionary_read_errors["alpha"], PermissionError)


class DictionaryManagementInteractionTest(unittest.TestCase):
```

```python

		self.assertEqual(self.counts(target), [dialog._("Unreadable")])
		self.assertIsInstance(target._dictionary_read_errors["alpha"], PermissionError)
		# The reason row says "in use or no permission" (the two causes cannot be told apart).
		self.assertEqual(target.read_problem_ctrl.value, describe_dictionary_read_error(PermissionError(13, "Permission denied")))
		self.assertTrue(target.read_problem_ctrl.shown)


class ReadProblemReasonTest(_DictionaryFilesTestCase):
	"""F-6 (D3, D5): the reason under the list, and Edit on a dictionary that cannot be read."""

	def open_dialog(self, selected):
		self.write("big5", BIG5)
		self.write("default", b"text,braille,type\r\n")
		names = ["big5", "default"]
		target = _make_dialog(self.root, names)
		with self.assertLogs(LOGGER, level="ERROR"):
			target.refresh_dictionaries(names, selected)
		return target

	def select(self, target, index):
		target.list_ctrl.selected = index
		target.read_problem_label.calls.clear()
		target.read_problem_ctrl.calls.clear()
		target.Layout.reset_mock()
		event = Mock()
		target._on_selection_changed(event)
		event.Skip.assert_called_once_with()

	def test_selecting_an_unreadable_dictionary_shows_the_reason(self):
		target = self.open_dialog("default")

		self.select(target, 0)

		reason = describe_dictionary_read_error(target._dictionary_read_errors["big5"])
		self.assertEqual(target.read_problem_ctrl.calls, [("ChangeValue", reason), ("SelectAll",), ("Show", True)])
		self.assertEqual(target.read_problem_label.calls, [("Show", True)])
		target.Layout.assert_called_once_with()

	def test_selecting_a_readable_dictionary_hides_the_reason(self):
		target = self.open_dialog("big5")

		self.select(target, 1)

		self.assertEqual(target.read_problem_ctrl.calls, [("ChangeValue", ""), ("Show", False)])
		self.assertEqual(target.read_problem_label.calls, [("Show", False)])
		target.Layout.assert_called_once_with()

	def test_refresh_shows_the_reason_for_the_preferred_selection(self):
		target = self.open_dialog("big5")

		reason = describe_dictionary_read_error(target._dictionary_read_errors["big5"])
		self.assertEqual(target.list_ctrl.selected, 0)
		self.assertEqual(target.read_problem_ctrl.calls[-3:], [("ChangeValue", reason), ("SelectAll",), ("Show", True)])
		self.assertTrue(target.read_problem_label.shown)

	def test_edit_on_an_unreadable_dictionary_shows_the_error_and_stays_open(self):
		target = self.open_dialog("big5")
		target.show_error = Mock()

		with self.assertLogs(LOGGER, level="ERROR") as logs:
			target._on_edit(None)

		error = target._dictionary_read_errors["big5"]
		target.show_error.assert_called_once_with(describe_unreadable_dictionary("big5", error))
		target.EndModal.assert_not_called()
		self.assertIsNone(target.edit_dictionary_name)
		self.assertEqual(len(logs.records), 1)
		self.assertTrue(target.read_problem_ctrl.shown)

	def test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count(self):
		target = self.open_dialog("big5")
		target.show_error = Mock()
		refreshes = target.list_ctrl.refresh_count
		self.write("big5", UTF8_FIXED)

		with self.assertNoLogs(LOGGER):
			target._on_edit(None)

		self.assertEqual(target.edit_dictionary_name, "big5")
		target.EndModal.assert_called_once_with(dialog.wx.ID_EDIT)
		target.show_error.assert_not_called()
		self.assertEqual(target._get_item_text(0, 1), "1")
		self.assertEqual(target._dictionary_read_errors, {})
		self.assertEqual(target.list_ctrl.refresh_count, refreshes + 1)
		self.assertFalse(target.read_problem_ctrl.shown)
		self.assertFalse(target.read_problem_label.shown)

	def test_edit_on_a_dictionary_that_became_unreadable_stays_open(self):
		self.write("alpha", READABLE)
		target = _make_dialog(self.root, ["alpha"])
		target.refresh_dictionaries(["alpha"], "alpha")
		target.show_error = Mock()
		self.write("alpha", BIG5)

		with self.assertLogs(LOGGER, level="ERROR"):
			target._on_edit(None)

		error = target._dictionary_read_errors["alpha"]
		self.assertIsInstance(error, UnicodeDecodeError)
		target.show_error.assert_called_once_with(describe_unreadable_dictionary("alpha", error))
		target.EndModal.assert_not_called()
		self.assertIsNone(target.edit_dictionary_name)
		self.assertEqual(self.counts(target), [dialog._("Unreadable")])
		self.assertTrue(target.read_problem_ctrl.shown)


class DictionaryManagementInteractionTest(unittest.TestCase):
```

Edit: `client/tests/test_gui_document_flows.py`

```python
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from dual_view.html import render_dual_view_html
from dual_view.model import build_dual_view_model


def make_paths(root: Path = Path("unused-root"), **folders: Path) -> app_paths.ApplicationPaths:
```

```python
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
from dual_view.html import render_dual_view_html
from dual_view.model import build_dual_view_model
from dictionaries.read_problems import describe_unreadable_dictionary
from tests.unreadable_dictionary_files import big5_decode_error


def make_paths(root: Path = Path("unused-root"), **folders: Path) -> app_paths.ApplicationPaths:
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        frame._dictionary_presenter = Mock()
        return frame

    def _open_management(self, frame, result, edit_name):
        with (
            patch.object(gui, "DictionaryManagementDialog") as dialog_class,
            patch.object(gui, "DictionaryEntriesDialog") as editor_class,
        ):
            dialog = dialog_class.return_value.__enter__.return_value
            dialog.ShowModal.return_value = result
```

```python
        frame._dictionary_presenter = Mock()
        return frame

    def _open_management(self, frame, result, edit_name, editor_error=None):
        with (
            patch.object(gui, "DictionaryManagementDialog") as dialog_class,
            patch.object(gui, "DictionaryEntriesDialog", side_effect=editor_error) as editor_class,
        ):
            dialog = dialog_class.return_value.__enter__.return_value
            dialog.ShowModal.return_value = result
```

Edit: `client/tests/test_gui_document_flows.py`

```python
        presenter.dictionary_path.assert_called_once_with("alpha")
        editor_class.assert_called_once_with(frame, dictionary_path=Path("dictionary/alpha.csv"))
        editor_class.return_value.__enter__.return_value.ShowModal.assert_called_once_with()

    def test_other_results_open_no_editor(self) -> None:
        for result, edit_name in ((gui.wx.ID_OK, "alpha"), (gui.wx.ID_EDIT, None)):
```

```python
        presenter.dictionary_path.assert_called_once_with("alpha")
        editor_class.assert_called_once_with(frame, dictionary_path=Path("dictionary/alpha.csv"))
        editor_class.return_value.__enter__.return_value.ShowModal.assert_called_once_with()

    def test_editor_that_cannot_read_its_dictionary_shows_the_reason(self) -> None:
        # F-6 (D6): the file went bad between the check in Dictionary Management and the editor.
        frame = self._make_frame()
        frame._dictionary_presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
        error = big5_decode_error()

        with (
            patch.object(gui.wx, "MessageBox") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)

        editor_class.assert_called_once_with(frame, dictionary_path=Path("dictionary/alpha.csv"))
        message_box.assert_called_once_with(
            describe_unreadable_dictionary("alpha", error),
            gui._("Error"),
            gui.wx.OK | gui.wx.ICON_ERROR,
            parent=frame,
        )
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            [f'Cannot read dictionary "alpha.csv": UnicodeDecodeError: {error}'],
        )
        self.assertIsNone(logs.records[0].exc_info)

    def test_editor_failure_that_is_unexpected_is_logged_with_its_traceback(self) -> None:
        frame = self._make_frame()
        frame._dictionary_presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
        error = RuntimeError("injected")

        with (
            patch.object(gui.wx, "MessageBox") as message_box,
            self.assertLogs("dotexpress.gui", level="ERROR") as logs,
        ):
            self._open_management(frame, gui.wx.ID_EDIT, "alpha", editor_error=error)

        message_box.assert_called_once_with(
            describe_unreadable_dictionary("alpha", error),
            gui._("Error"),
            gui.wx.OK | gui.wx.ICON_ERROR,
            parent=frame,
        )
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            ['Unexpected error while reading dictionary "alpha.csv"'],
        )
        self.assertIs(logs.records[0].exc_info[1], error)

    def test_other_results_open_no_editor(self) -> None:
        for result, edit_name in ((gui.wx.ID_OK, "alpha"), (gui.wx.ID_EDIT, None)):
```

```bash
$PY -m unittest tests.test_dictionary_management_dialog tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (no reason row yet, Edit closes the dialog without reading the file, and the editor's error escapes the frame):

```text
ERROR: test_editor_failure_that_is_unexpected_is_logged_with_its_traceback (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_editor_failure_that
RuntimeError: injected
ERROR: test_editor_that_cannot_read_its_dictionary_shows_the_reason (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_editor_that_cannot_read_it
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte
FAIL: test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count (tests.test_dictionary_management_dialog.ReadProblemReasonTest.test_edit_after_t
AssertionError: 'Unreadable' != '1'
FAIL: test_edit_on_a_dictionary_that_became_unreadable_stays_open (tests.test_dictionary_management_dialog.ReadProblemReasonTest.test_edit_on_a_dictionary_that_
AssertionError: no logs of level ERROR or higher triggered on dotexpress.gui
FAIL: test_edit_on_an_unreadable_dictionary_shows_the_error_and_stays_open (tests.test_dictionary_management_dialog.ReadProblemReasonTest.test_edit_on_an_unread
FAIL: test_refresh_shows_the_reason_for_the_preferred_selection (tests.test_dictionary_management_dialog.ReadProblemReasonTest.test_refresh_shows_the_reason_for
AssertionError: Lists differ: [] != [('ChangeValue', 'The file is not saved as[131 chars]rue)]
FAIL: test_selecting_a_readable_dictionary_hides_the_reason (tests.test_dictionary_management_dialog.ReadProblemReasonTest.test_selecting_a_readable_dictionary_
AssertionError: Lists differ: [] != [('ChangeValue', ''), ('Show', False)]
FAIL: test_selecting_an_unreadable_dictionary_shows_the_reason (tests.test_dictionary_management_dialog.ReadProblemReasonTest.test_selecting_an_unreadable_dicti
FAIL: test_dictionary_held_open_without_sharing_is_unreadable (tests.test_dictionary_management_dialog.UnreadableDictionaryCountTest.test_dictionary_held_open_w
AssertionError: '' != 'The file cannot be opened. It may be in u[100 chars]ain.'
Ran 223 tests
FAILED (failures=7, errors=2)
```

- [ ] **Step 2: The reason row, Edit and the editor guard** (`client/dialog.py`, `client/gui.py`, tabs). The row is created right after the list (Tab order and accessible name) and hidden before `finalize_dialog_layout`, so the dialog keeps its size.

Edit: `client/dialog.py`

```python
	normalize_dictionary_name,
)
from dictionaries.presenter import DictionaryManagementActions
from dictionaries.read_problems import DictionaryCount, read_dictionary_count
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
```

```python
	normalize_dictionary_name,
)
from dictionaries.presenter import DictionaryManagementActions
from dictionaries.read_problems import (
	DictionaryCount,
	describe_dictionary_read_error,
	describe_unreadable_dictionary,
	read_dictionary_count,
)
from documents.workspace import normalize_document_name
from i18n import N_, _
from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages
```

Edit: `client/dialog.py`

```python
		self.list_ctrl.Bind(wx.EVT_SIZE, self._on_list_size)
		main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 12)

		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.add_button = wx.Button(self, label=_("Add"))
		self.delete_button = wx.Button(self, label=_("Delete"))
```

```python
		self.list_ctrl.Bind(wx.EVT_SIZE, self._on_list_size)
		main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 12)

		# F-6 (D3): why the selected dictionary cannot be read. Created right after the list, so
		# it is the next Tab stop and the label is the field's accessible name. Multi-line,
		# because wxMSW leaves a read-only single-line field out of the Tab order. Hidden
		# before the layout is fitted, so the dialog keeps its size; shown only while a
		# dictionary that cannot be read is selected.
		self.read_problem_label = wx.StaticText(self, label=_("Why this dictionary cannot be read:"))
		self.read_problem_ctrl = wx.TextCtrl(
			self,
			style=wx.TE_MULTILINE | wx.TE_READONLY,
			size=(-1, self.GetCharHeight() * 4),
		)
		main_sizer.Add(self.read_problem_label, 0, wx.LEFT | wx.RIGHT, 12)
		main_sizer.Add(self.read_problem_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		self.read_problem_label.Hide()
		self.read_problem_ctrl.Hide()

		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.add_button = wx.Button(self, label=_("Add"))
		self.delete_button = wx.Button(self, label=_("Delete"))
```

Edit: `client/dialog.py`

```python
			self.list_ctrl.Focus(index)
		self._resize_columns()
		self._update_button_states()

	def _resize_columns(self) -> None:
		available_width = max(0, self.list_ctrl.GetClientSize().width)
```

```python
			self.list_ctrl.Focus(index)
		self._resize_columns()
		self._update_button_states()
		self._update_read_problem()

	def _update_read_problem(self) -> None:
		"""Show why the selected dictionary cannot be read, or hide the reason row (F-6 D3).

		The text is selected, so a screen reader reads all of it when the field gets focus,
		not only its first line.
		"""
		error = self._dictionary_read_errors.get(self._get_selected_name())
		if error is None:
			self.read_problem_ctrl.ChangeValue("")
		else:
			self.read_problem_ctrl.ChangeValue(describe_dictionary_read_error(error))
			self.read_problem_ctrl.SelectAll()
		self.read_problem_label.Show(error is not None)
		self.read_problem_ctrl.Show(error is not None)
		self.Layout()

	def _resize_columns(self) -> None:
		available_width = max(0, self.list_ctrl.GetClientSize().width)
```

Edit: `client/dialog.py`

```python
		if selected_name is not None:
			self._selected_name = selected_name
		self._update_button_states()
		event.Skip()

	def _on_add_clicked(self, _event: wx.CommandEvent) -> None:
```

```python
		if selected_name is not None:
			self._selected_name = selected_name
		self._update_button_states()
		self._update_read_problem()
		event.Skip()

	def _on_add_clicked(self, _event: wx.CommandEvent) -> None:
```

Edit: `client/dialog.py`

```python
	def _on_edit(self, _event: wx.Event) -> None:
		selected = self._get_selected_name()
		if selected is None:
			return
		self.edit_dictionary_name = selected
		self.EndModal(wx.ID_EDIT)
```

```python
	def _on_edit(self, _event: wx.Event) -> None:
		selected = self._get_selected_name()
		if selected is None:
			return
		# F-6 (D5): read the file again. A file fixed meanwhile opens; one that cannot be read
		# is explained here, and the dialog stays open.
		count = read_dictionary_count(self._actions.dictionary_path(selected))
		self._store_count(selected, count)
		self.list_ctrl.Refresh()
		self._update_read_problem()
		if count.error is not None:
			self.show_error(describe_unreadable_dictionary(selected, count.error))
			return
		self.edit_dictionary_name = selected
		self.EndModal(wx.ID_EDIT)
```

Edit: `client/gui.py`

```python
from conversion.preprocessing.user_script import preprocessing_script_path
from dictionaries.manager import dictionary_path_for_name
from dictionaries.presenter import DictionaryManagementPresenter
from documents.controller import DocumentController
from documents.export_coordinator import ExportCoordinator
from documents.formats import DocumentFormatDescriptor, build_export_wildcard, get_format
```

```python
from conversion.preprocessing.user_script import preprocessing_script_path
from dictionaries.manager import dictionary_path_for_name
from dictionaries.presenter import DictionaryManagementPresenter
from dictionaries.read_problems import describe_unreadable_dictionary, log_dictionary_read_error
from documents.controller import DocumentController
from documents.export_coordinator import ExportCoordinator
from documents.formats import DocumentFormatDescriptor, build_export_wildcard, get_format
```

Edit: `client/gui.py`

```python
		if result != wx.ID_EDIT or edit_name is None:
			return
		dictionary_path = self._dictionary_presenter.dictionary_path(edit_name)
		with DictionaryEntriesDialog(self, dictionary_path=dictionary_path) as editor:
			editor.ShowModal()

	def on_convert(self, _evt):
		self._conversion_presenter.convert()
```

```python
		if result != wx.ID_EDIT or edit_name is None:
			return
		dictionary_path = self._dictionary_presenter.dictionary_path(edit_name)
		try:
			editor = DictionaryEntriesDialog(self, dictionary_path=dictionary_path)
		except Exception as error:
			# F-6 (D6): the file could not be read after Dictionary Management checked it.
			log_dictionary_read_error(dictionary_path, error)
			wx.MessageBox(
				describe_unreadable_dictionary(edit_name, error),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				parent=self,
			)
			return
		with editor as entries_dialog:
			entries_dialog.ShowModal()

	def on_convert(self, _evt):
		self._conversion_presenter.convert()
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_dictionary_management_dialog tests.test_gui_document_flows -v 2>&1 | grep -E "^test_(selecting_an_unreadable|selecting_a_readable|refresh_shows_the_reason|edit_on_an?_|edit_after_the_file|dictionary_held_open|editor_that_cannot|editor_failure_that|edit_result_opens|only_explicit_edit)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (the 8 new tests, M12 and the two unchanged Edit tests pass):

```text
test_only_explicit_edit_handler_sets_edit_result ok
test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count ok
test_edit_on_a_dictionary_that_became_unreadable_stays_open ok
test_edit_on_an_unreadable_dictionary_shows_the_error_and_stays_open ok
test_refresh_shows_the_reason_for_the_preferred_selection ok
test_selecting_a_readable_dictionary_hides_the_reason ok
test_selecting_an_unreadable_dictionary_shows_the_reason ok
test_dictionary_held_open_without_sharing_is_unreadable ok
test_edit_result_opens_speech_symbols_for_presenter_path ok
test_editor_failure_that_is_unexpected_is_logged_with_its_traceback ok
test_editor_that_cannot_read_its_dictionary_shows_the_reason ok
Ran 231 tests
OK
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1329 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/dialog.py client/gui.py client/tests/test_dictionary_management_dialog.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -m "fix: explain why a dictionary cannot be read (F-6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
290c21bd3c83c5a2f4cc48b73ab0da4ffb3f84d9
```

### Task 3: Refuse importing a dictionary that cannot be read (D9)

- [ ] **Step 1: Red: P1 (manager, 4 spaces) and P2 (presenter, tabs).**

Edit: `client/tests/test_dictionary_manager.py`

```python
    list_dictionary_names,
    normalize_dictionary_name,
    rename_dictionary,
)


class DictionaryManagerTest(unittest.TestCase):
```

```python
    list_dictionary_names,
    normalize_dictionary_name,
    rename_dictionary,
    validate_dictionary_csv,
)
from tests.unreadable_dictionary_files import FIELD_LIMIT, LATE_BIG5


class DictionaryManagerTest(unittest.TestCase):
```

Edit: `client/tests/test_dictionary_manager.py`

```python
        with self.assertRaises(ValueError):
            import_dictionary(self.dictionary_dir, source_path, "science")

    def test_rename_dictionary_renames_file_and_preserves_contents(self) -> None:
        source_path = create_dictionary(self.dictionary_dir, "math")
        with source_path.open("a", newline="", encoding="utf-8") as f:
```

```python
        with self.assertRaises(ValueError):
            import_dictionary(self.dictionary_dir, source_path, "science")

    def test_validate_reads_every_row(self) -> None:
        # F-6 (D9): Import accepts only files that Dictionary Management can count and edit.
        cases = (
            ("Big5 after 17 KB of ASCII rows", LATE_BIG5, UnicodeDecodeError),
            ("a field over the CSV limit", FIELD_LIMIT, csv.Error),
        )
        for label, data, error_type in cases:
            with self.subTest(label):
                source_path = Path(self._tmpdir.name) / "source.csv"
                source_path.write_bytes(data)

                with self.assertRaises(error_type):
                    validate_dictionary_csv(source_path)

    def test_import_dictionary_refuses_a_late_big5_file_and_copies_nothing(self) -> None:
        source_path = Path(self._tmpdir.name) / "late.csv"
        source_path.write_bytes(LATE_BIG5)

        with self.assertRaises(UnicodeDecodeError):
            import_dictionary(self.dictionary_dir, source_path, "late")

        self.assertEqual(list(self.dictionary_dir.iterdir()), [])

    def test_rename_dictionary_renames_file_and_preserves_contents(self) -> None:
        source_path = create_dictionary(self.dictionary_dir, "math")
        with source_path.open("a", newline="", encoding="utf-8") as f:
```

Edit: `client/tests/test_dictionary_presenter.py`

```python
import ast
import tempfile
import unittest
from pathlib import Path
```

```python
import ast
import csv
import tempfile
import unittest
from pathlib import Path
```

Edit: `client/tests/test_dictionary_presenter.py`

```python
from unittest.mock import Mock, patch

import dictionaries.presenter as presenter_module
from dictionaries.presenter import DictionaryManagementPresenter
from i18n import _


PRESENTER_PATH = Path(presenter_module.__file__)
```

```python
from unittest.mock import Mock, patch

import dictionaries.presenter as presenter_module
from dictionaries.entries import load_dictionary_entries
from dictionaries.presenter import DictionaryManagementPresenter
from dictionaries.read_problems import describe_dictionary_read_error
from i18n import _
from tests.unreadable_dictionary_files import BIG5, FIELD_LIMIT, LATE_BIG5


PRESENTER_PATH = Path(presenter_module.__file__)
```

Edit: `client/tests/test_dictionary_presenter.py`

```python
		path.write_text(content, encoding="utf-8")
		return path

	def choose_call(self):
		return ("choose_import", _("Import Dictionary"))

```

```python
		path.write_text(content, encoding="utf-8")
		return path

	def write_source_bytes(self, name, data):
		source_dir = self.root / "source"
		source_dir.mkdir(exist_ok=True)
		path = source_dir / f"{name}.csv"
		path.write_bytes(data)
		return path

	def read_error_call(self, source):
		"""The error box for a source that cannot be read as a dictionary (F-6 D9)."""
		with self.assertRaises((UnicodeDecodeError, csv.Error)) as caught:
			load_dictionary_entries(source)
		reason = describe_dictionary_read_error(caught.exception)
		return ("error", _("Failed to import dictionary: {error}").format(error=reason))

	def choose_call(self):
		return ("choose_import", _("Import Dictionary"))

```

Edit: `client/tests/test_dictionary_presenter.py`

```python
		)
		self.assertEqual(self.files(), ["default"])

	def test_import_cancelled_name_prompt_imports_nothing(self):
		source = self.write_source("words")
		presenter = self.make_presenter()
```

```python
		)
		self.assertEqual(self.files(), ["default"])

	def test_import_big5_shows_the_not_utf8_reason(self):
		# Before F-6 this showed the header message, which named the wrong problem.
		source = self.write_source_bytes("big5", BIG5)
		presenter = self.make_presenter()
		view = FakeView(names=["big5"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("big5"), self.read_error_call(source)])
		self.assertEqual(self.files(), ["default"])

	def test_import_late_big5_is_refused(self):
		# Before F-6 the header check passed and the file was copied; Dictionary Management
		# then could not count it.
		source = self.write_source_bytes("late", LATE_BIG5)
		presenter = self.make_presenter()
		view = FakeView(names=["late"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("late"), self.read_error_call(source)])
		self.assertEqual(self.files(), ["default"])

	def test_import_invalid_csv_shows_the_reason(self):
		source = self.write_source_bytes("long", FIELD_LIMIT)
		presenter = self.make_presenter()
		view = FakeView(names=["long"], import_path=source)

		result = presenter.import_from_file(view)

		self.assertIsNone(result)
		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("long"), self.read_error_call(source)])
		self.assertEqual(self.files(), ["default"])

	def test_import_cancelled_name_prompt_imports_nothing(self):
		source = self.write_source("words")
		presenter = self.make_presenter()
```

```bash
$PY -m unittest tests.test_dictionary_manager tests.test_dictionary_presenter 2>&1 | $PY $T/tools/brief.py
```

Expected (today the header check passes for the late-Big5 and field-limit files, which are then copied; a small Big5 file shows the header message):

```text
FAIL: test_import_dictionary_refuses_a_late_big5_file_and_copies_nothing (tests.test_dictionary_manager.DictionaryManagerTest.test_import_dictionary_refuses_a_l
AssertionError: UnicodeDecodeError not raised
FAIL: test_validate_reads_every_row (tests.test_dictionary_manager.DictionaryManagerTest.test_validate_reads_every_row) [Big5 after 17 KB of ASCII rows]
FAIL: test_validate_reads_every_row (tests.test_dictionary_manager.DictionaryManagerTest.test_validate_reads_every_row) [a field over the CSV limit]
AssertionError: Error not raised
FAIL: test_import_big5_shows_the_not_utf8_reason (tests.test_dictionary_presenter.PresenterImportTest.test_import_big5_shows_the_not_utf8_reason)
AssertionError: Lists differ: [('ch[59 chars], '匯入的檔案必須包含 text、braille 與 type 表頭。')] != [('ch[59 chars], '匯入字典失敗：The file is not saved as UTF-8. Save[87 chars]l
FAIL: test_import_invalid_csv_shows_the_reason (tests.test_dictionary_presenter.PresenterImportTest.test_import_invalid_csv_shows_the_reason)
AssertionError: 'long' is not None
FAIL: test_import_late_big5_is_refused (tests.test_dictionary_presenter.PresenterImportTest.test_import_late_big5_is_refused)
AssertionError: 'late' is not None
Ran 61 tests
FAILED (failures=6, skipped=1)
```

- [ ] **Step 2: Read every row on Import** (`client/dictionaries/manager.py`, 4 spaces; `client/dictionaries/presenter.py`, tabs). The new branch comes before `except ValueError`, because `UnicodeDecodeError` is a `ValueError`.

Edit: `client/dictionaries/manager.py`

```python


def validate_dictionary_csv(path: Path | str) -> None:
    source_path = Path(path)
    with source_path.open("r", newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        fieldnames = reader.fieldnames or []
    if any(field not in fieldnames for field in DEFAULT_HEADER):
        raise ValueError("Dictionary CSV must contain text, braille, and type headers.")


def create_dictionary(dictionary_dir: Path, name: str) -> Path:
```

```python


def validate_dictionary_csv(path: Path | str) -> None:
    """Raise ValueError if a header is missing; reading every row raises what reading the
    dictionary later would (UnicodeDecodeError, csv.Error, OSError).

    The file is read as ``dictionaries.entries.load_dictionary_rows`` reads it (F-6), so a
    file that Import accepts can also be counted and edited.
    """
    source_path = Path(path)
    with source_path.open("r", newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        fieldnames = reader.fieldnames or []
        if any(field not in fieldnames for field in DEFAULT_HEADER):
            raise ValueError("Dictionary CSV must contain text, braille, and type headers.")
        for _row in reader:
            pass


def create_dictionary(dictionary_dir: Path, name: str) -> Path:
```

Edit: `client/dictionaries/presenter.py`

```python

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol
```

```python

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
from typing import Protocol
```

Edit: `client/dictionaries/presenter.py`

```python
	list_dictionary_names,
)
from dictionaries.name_prompt import prompt_dictionary_name_until_success, rename_dictionary_after_name_prompt
from i18n import _
from translation.dictionary_state import (
	plan_dictionary_state_after_add,
```

```python
	list_dictionary_names,
)
from dictionaries.name_prompt import prompt_dictionary_name_until_success, rename_dictionary_after_name_prompt
from dictionaries.read_problems import describe_dictionary_read_error
from i18n import _
from translation.dictionary_state import (
	plan_dictionary_state_after_add,
```

Edit: `client/dictionaries/presenter.py`

```python
				source_path.stem,
				lambda dictionary_name: import_dictionary(self._dictionary_dir, source_path, dictionary_name),
			)
		except ValueError:
			view.show_error(_("Imported file must contain text, braille, and type headers."))
			return None
```

```python
				source_path.stem,
				lambda dictionary_name: import_dictionary(self._dictionary_dir, source_path, dictionary_name),
			)
		except (UnicodeDecodeError, csv.Error) as exc:
			# F-6 (D9): before ValueError, which UnicodeDecodeError also is. Nothing was copied.
			view.show_error(_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc)))
			return None
		except ValueError:
			view.show_error(_("Imported file must contain text, braille, and type headers."))
			return None
```

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_dictionary_manager tests.test_dictionary_presenter -v 2>&1 | grep -E "^test_(validate_reads|import_dictionary_refuses|import_big5|import_late_big5|import_invalid_csv|import_without_headers|import_invalid_name|import_missing_source)" | sed 's/ (.*) \.\.\. / /'
$PY -m unittest tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_dictionary_read_problems 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (the 5 new tests and the three unchanged Import messages pass):

```text
test_import_dictionary_refuses_a_late_big5_file_and_copies_nothing ok
test_validate_reads_every_row ok
test_import_big5_shows_the_not_utf8_reason ok
test_import_invalid_csv_shows_the_reason ok
test_import_invalid_name_shows_header_error ok
test_import_late_big5_is_refused ok
test_import_missing_source_shows_import_error ok
test_import_without_headers_shows_header_error ok
Ran 69 tests
OK (skipped=1)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1334 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/dictionaries/manager.py client/dictionaries/presenter.py client/tests/test_dictionary_manager.py client/tests/test_dictionary_presenter.py
git -C $REPO commit -q -m "fix: refuse importing a dictionary that cannot be read (F-6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
01e8a26c795433d8e5fd14d945b8d77c2067f4bb
```

### Task 4: Translate the unreadable-dictionary strings (D11)

- [ ] **Step 1: Red: I1** (`client/tests/test_i18n.py`, 4 spaces; the file already holds zh-TW text).

Edit: `client/tests/test_i18n.py`

```python
        self.assertIsInstance(i18n.load_translation(), gettext.GNUTranslations)
        self.assertEqual(i18n._("General"), "一般")
        self.assertEqual(i18n._("Startup Error"), "啟動錯誤")

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```python
        self.assertIsInstance(i18n.load_translation(), gettext.GNUTranslations)
        self.assertEqual(i18n._("General"), "一般")
        self.assertEqual(i18n._("Startup Error"), "啟動錯誤")

    def test_unreadable_dictionary_strings_are_translated(self) -> None:
        # F-6: the count column, the label of the reason field, the headline and the four reasons.
        expected = {
            "Unreadable": "無法讀取",
            "Why this dictionary cannot be read:": "無法讀取的原因：",
            'Dictionary "{name}" cannot be read.': "無法讀取字典「{name}」。",
            'The file is not saved as UTF-8. Save it again in the "CSV UTF-8 (Comma delimited)" format, '
            "for example with Save As in Excel.": "檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，"
            "例如在 Excel 中使用「另存新檔」。",
            "The file cannot be opened. It may be in use by another program, or you may not have "
            "permission to read it. Close the other program and try again.": "無法開啟檔案。檔案可能正被其他程式使用，"
            "或您沒有讀取權限。請關閉其他程式後再試一次。",
            "The file is not a valid CSV file. Check for a quotation mark that is not closed. Details: {error}": (
                "檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：{error}"
            ),
            "The file cannot be read: {error}": "無法讀取檔案：{error}",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")
```

```bash
$PY -m unittest tests.test_i18n 2>&1 | $PY $T/tools/brief.py
```

Expected (the catalog does not know the seven msgids yet):

```text
FAIL: test_unreadable_dictionary_strings_are_translated (tests.test_i18n.TranslationTest.test_unreadable_dictionary_strings_are_translated)
AssertionError: {'Unreadable': 'Unreadable', 'Why this dictionary cannot [952 chars]or}'} != {'Unreadable': '無法讀取', 'Why this dictionary cannot be rea[657 chars
Ran 18 tests
FAILED (failures=1)
```

- [ ] **Step 2: Regenerate the template, pin its date, merge** (from the repository root through `cmd`; the tools write LF).

```bash
(cd $REPO && cmd //c 'scripts\generate-pot.bat'); echo "generate-pot exit $?"
$PY $T/tools/pin_pot_date.py locales/dotexpress.pot "2026-10-10 12:00+0800"
msgmerge --quiet --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot; echo "msgmerge exit $?"
LANGUAGE=C msgfmt --check --statistics -o /dev/null locales/zh_TW/LC_MESSAGES/dotexpress.po 2>&1
msgattrib --only-fuzzy --no-obsolete locales/zh_TW/LC_MESSAGES/dotexpress.po | sed -n '/^#: /,$p'
```

Expected (no `xgettext` warning on stderr; `msgmerge` guessed two wrong fuzzy translations and left five entries empty; the last command prints the two fuzzy entries):

```text
generate-pot exit 0
dotexpress.pot: POT-Creation-Date 2026-10-10 12:00+0800
msgmerge exit 0
357 translated messages, 2 fuzzy translations, 5 untranslated messages.
#: dialog.py:548
#, fuzzy
msgid "Why this dictionary cannot be read:"
msgstr "預設字典無法刪除。"

#: dictionaries/read_problems.py:64
#, fuzzy, python-brace-format
msgid "Dictionary \"{name}\" cannot be read."
msgstr "字典「{name}」已存在。"
```

- [ ] **Step 3: Fill the seven msgstr values and drop both fuzzy flags** (block script, as every other block).

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
msgstr "條目數量"

#: dialog.py:548
#, fuzzy
msgid "Why this dictionary cannot be read:"
msgstr "預設字典無法刪除。"

#: dialog.py:562 ui/action_menu.py:30
msgid "Rename"
```

```po
msgstr "條目數量"

#: dialog.py:548
msgid "Why this dictionary cannot be read:"
msgstr "無法讀取的原因："

#: dialog.py:562 ui/action_menu.py:30
msgid "Rename"
```

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po

#: dialog.py:599 dialog.py:657
msgid "Unreadable"
msgstr ""

#: dictionaries/entries.py:14
msgid "General"
```

```po

#: dialog.py:599 dialog.py:657
msgid "Unreadable"
msgstr "無法讀取"

#: dictionaries/entries.py:14
msgid "General"
```

Edit: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

```po
"The file is not saved as UTF-8. Save it again in the \"CSV UTF-8 (Comma "
"delimited)\" format, for example with Save As in Excel."
msgstr ""

#: dictionaries/read_problems.py:52
msgid ""
"The file cannot be opened. It may be in use by another program, or you may "
"not have permission to read it. Close the other program and try again."
msgstr ""

#: dictionaries/read_problems.py:57
#, python-brace-format
msgid ""
"The file is not a valid CSV file. Check for a quotation mark that is not "
"closed. Details: {error}"
msgstr ""

#: dictionaries/read_problems.py:59
#, python-brace-format
msgid "The file cannot be read: {error}"
msgstr ""

#: dictionaries/read_problems.py:64
#, fuzzy, python-brace-format
msgid "Dictionary \"{name}\" cannot be read."
msgstr "字典「{name}」已存在。"

#: documents/export_coordinator.py:103
#, python-brace-format
```

```po
"The file is not saved as UTF-8. Save it again in the \"CSV UTF-8 (Comma "
"delimited)\" format, for example with Save As in Excel."
msgstr ""
"檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中"
"使用「另存新檔」。"

#: dictionaries/read_problems.py:52
msgid ""
"The file cannot be opened. It may be in use by another program, or you may "
"not have permission to read it. Close the other program and try again."
msgstr ""
"無法開啟檔案。檔案可能正被其他程式使用，或您沒有讀取權限。請關閉其他程式後再試"
"一次。"

#: dictionaries/read_problems.py:57
#, python-brace-format
msgid ""
"The file is not a valid CSV file. Check for a quotation mark that is not "
"closed. Details: {error}"
msgstr "檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：{error}"

#: dictionaries/read_problems.py:59
#, python-brace-format
msgid "The file cannot be read: {error}"
msgstr "無法讀取檔案：{error}"

#: dictionaries/read_problems.py:64
#, python-brace-format
msgid "Dictionary \"{name}\" cannot be read."
msgstr "無法讀取字典「{name}」。"

#: documents/export_coordinator.py:103
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
git -C $REPO diff --numstat -- client/locales
$PY -I $T/tools/msgid_scan.py $REPO/client
```

Expected (364 translated, no fuzzy; 365 `msgid` lines with the header; the 31 obsolete entries unchanged; no absolute, backslash, test or venv reference; the seven new translations and the three reused strings load):

```text
a second msgmerge changes nothing
msgfmt exit 0
364 translated messages.
0
catalog keys: 365
'Unreadable' -> 無法讀取
'Why this dictionary cannot be read:' -> 無法讀取的原因：
'Dictionary "{name}" cannot be read.' -> 無法讀取字典「{name}」。
'The file is not saved as UTF-8. Save it ' -> 檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。
'The file cannot be opened. It may be in ' -> 無法開啟檔案。檔案可能正被其他程式使用，或您沒有讀取權限。請關閉其他程式後再試一次。
'The file is not a valid CSV file. Check ' -> 檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：{error}
'The file cannot be read: {error}' -> 無法讀取檔案：{error}
'Entries' -> 條目數量
'Error' -> 錯誤
'Failed to import dictionary: {error}' -> 匯入字典失敗：{error}
28058
locales/dotexpress.pot:365
locales/zh_TW/LC_MESSAGES/dotexpress.po:365
31
0
locales/dotexpress.pot:1
locales/zh_TW/LC_MESSAGES/dotexpress.po:1
133	96	client/locales/dotexpress.pot
-	-	client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
137	96	client/locales/zh_TW/LC_MESSAGES/dotexpress.po
source msgids: 364 sha256 7b53ff311c9e446767b0884bfc03148afe030ca7e15899d6ee6919e77c664ea7
```

- [ ] **Step 4: Green.**

```bash
$PY -m unittest tests.test_i18n tests.test_dictionary_read_problems tests.test_dictionary_management_dialog tests.test_dictionary_presenter tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (the tests that compare through `_` hold with the translations too):

```text
Ran 295 tests
OK (skipped=1)
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1335 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/test_i18n.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git -C $REPO commit -q -m "chore: translate the unreadable-dictionary strings (F-6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -C $REPO rev-parse HEAD:client
git -C $REPO status --short -- client docs scripts
```

Expected:

```text
e995d5444d769da21245201c3771bb27d9026edc
```

### Task 5: Verification (no commit)

`BASE` is the merge base with `main` (`e46ff26`).

- [ ] **Step 1: Criterion 1, full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`Ran` = 1307 + 28; the error is F-W6):

```text
ERROR: test_case_only_rename_still_renames (test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames)
FileExistsError: Dictionary 'Alpha' already exists.
Ran 1335 tests
FAILED (errors=1, skipped=7)
```

- [ ] **Step 2: Criterion 2, focused modules; the 28 new tests ran and passed, the Windows-only ones included.**

```bash
$PY -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_gui_document_flows tests.test_i18n tests.test_dictionary_entries 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_gui_document_flows tests.test_i18n -v 2>&1 | grep -cE "^test_(classifies_each_error|describes_each_problem|unreadable_dictionary_message_has|count_of_readable|count_of_unreadable|unexpected_error_is_logged|file_held_open_without|module_does_not_import_wx|unreadable_dictionary_shows|refresh_after_an_action_keeps|each_unreadable_dictionary_is|unreadable_dictionaries_keep|count_column_fits|dictionary_held_open_without|selecting_an_unreadable|selecting_a_readable|refresh_shows_the_reason|edit_on_an_unreadable|edit_after_the_file_was|edit_on_a_dictionary_that|editor_that_cannot_read|editor_failure_that_is|validate_reads_every_row|import_dictionary_refuses_a_late|import_big5_shows|import_late_big5_is|import_invalid_csv_shows|unreadable_dictionary_strings)[a-z0-9_]* .* ok$"
$PY -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog -v 2>&1 | grep -E "^test_(file_held_open_without_sharing_cannot_be_opened|dictionary_held_open_without_sharing_is_unreadable) " | sed 's/ (.*) \.\.\. / /'
```

Expected:

```text
Ran 327 tests
OK (skipped=1)
28
test_file_held_open_without_sharing_cannot_be_opened ok
test_dictionary_held_open_without_sharing_is_unreadable ok
```

- [ ] **Step 3: Shuffled module order, six seeds** (one process each, about two minutes).

```bash
for s in 0 1 2 3 4 5; do $PY $T/tools/shuffle_harness.py $s 2>/dev/null; done | sed 's/^seed [0-9]*: //' | sort | uniq -c
```

Expected:

```text
      6 ran=1335 failures=0 errors=1 skipped=7 ['test_case_only_rename_still_renames']
```

- [ ] **Step 4: Criterion 3, catalogs.** A second run of `generate-pot.bat` into a scratch file differs from the committed template only in `POT-Creation-Date`; `msgfmt` reports 364 translated messages; the committed `.mo` loads with `gettext.GNUTranslations` and translates the seven new msgids.

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
364 translated messages.
catalog keys: 365
'Unreadable' -> 無法讀取
'Why this dictionary cannot be read:' -> 無法讀取的原因：
'Dictionary "{name}" cannot be read.' -> 無法讀取字典「{name}」。
'The file is not saved as UTF-8. Save it ' -> 檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。
'The file cannot be opened. It may be in ' -> 無法開啟檔案。檔案可能正被其他程式使用，或您沒有讀取權限。請關閉其他程式後再試一次。
'The file is not a valid CSV file. Check ' -> 檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：{error}
'The file cannot be read: {error}' -> 無法讀取檔案：{error}
'Entries' -> 條目數量
'Error' -> 錯誤
'Failed to import dictionary: {error}' -> 匯入字典失敗：{error}
source msgids: 364 sha256 7b53ff311c9e446767b0884bfc03148afe030ca7e15899d6ee6919e77c664ea7
```

- [ ] **Step 5: Criteria 4-6, fixtures, untouched modules, touched files, application data.**

```bash
BASE=$(git -C $REPO merge-base main HEAD)
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO diff --quiet $BASE -- client/conversion client/dictionaries/entries.py client/dictionaries/entry_list_model.py client/tests/wx_stub.py client/braille && echo "conversion, entries, entry list model, wx stub and braille unchanged"
git -C $REPO diff --stat $BASE -- client/tests/fixtures client/settings client/ui client/documents client/shared
git -C $REPO diff --stat=200 $BASE -- client
(cd $MAIN/client && find dictionary workspace log config.json -type f 2>/dev/null | sort | xargs -d '\n' sha256sum) | diff - $T/app-data.sha256 && echo "application data unchanged"
git -C $REPO status --short -- client docs scripts
```

Expected (the second `diff --stat` prints nothing; `status` prints nothing):

```text
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd *-
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf *-
conversion, entries, entry list model, wx stub and braille unchanged
 client/dialog.py                                  |  73 +++++++++++++++++++++++++++++++++++++----
 client/dictionaries/manager.py                    |  12 +++++--
 client/dictionaries/presenter.py                  |   6 ++++
 client/dictionaries/read_problems.py              |  88 +++++++++++++++++++++++++++++++++++++++++++++++++
 client/gui.py                                     |  17 ++++++++--
 client/locales/dotexpress.pot                     | 229 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++------------------------------------------------------
 client/locales/zh_TW/LC_MESSAGES/dotexpress.mo    | Bin 26971 -> 28058 bytes
 client/locales/zh_TW/LC_MESSAGES/dotexpress.po    | 233 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++------------------------------------------------------
 client/tests/test_dictionary_management_dialog.py | 254 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 client/tests/test_dictionary_manager.py           |  25 ++++++++++++++
 client/tests/test_dictionary_presenter.py         |  54 ++++++++++++++++++++++++++++++
 client/tests/test_dictionary_read_problems.py     | 181 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 client/tests/test_gui_document_flows.py           |  54 ++++++++++++++++++++++++++++--
 client/tests/test_i18n.py                         |  21 ++++++++++++
 client/tests/unreadable_dictionary_files.py       |  29 +++++++++++++++++
 15 files changed, 1071 insertions(+), 205 deletions(-)
application data unchanged
```

- [ ] **Step 6: Criterion 7, mutation check** (22 mutants: the spec's eleven items, two of which are two mutants each, and nine more for the classification of `PermissionError` and `csv.Error`, the stale error, the column width, the reason label, the refresh and selection hooks, the guard's log line and the Import reason; about 35 seconds). Each mutant must be caught by at least one test.

```bash
$PY $T/tools/f6_mutants.py $REPO/client $T/mut; echo "exit $?"
```

Expected:

```text
counts-without-the-per-file-catch: 13 caught: test_dictionary_management_dialog.test_dictionary_held_open_without_sharing_is_unreadable, test_dictionary_management_dialog.test_each_unreadable_dictionary_is_logged, test_dictionary_management_dialog.test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count, test_dictionary_management_dialog.test_edit_on_a_dictionary_that_became_unreadable_stays_open, test_dictionary_management_dialog.test_edit_on_an_unreadable_dictionary_shows_the_error_and_stays_open, test_dictionary_management_dialog.test_refresh_after_an_action_keeps_names_counts_and_item_count_consistent, and 7 more
unreadable-counted-as-zero: 4 caught: test_dictionary_management_dialog.test_dictionary_held_open_without_sharing_is_unreadable, test_dictionary_management_dialog.test_edit_on_a_dictionary_that_became_unreadable_stays_open, test_dictionary_management_dialog.test_refresh_after_an_action_keeps_names_counts_and_item_count_consistent, test_dictionary_management_dialog.test_unreadable_dictionary_shows_unreadable_and_the_others_their_counts
store-count-keeps-a-stale-error: 1 caught: test_dictionary_management_dialog.test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count
count-column-without-the-unreadable-label: 1 caught: test_dictionary_management_dialog.test_count_column_fits_the_unreadable_label
decode-error-classified-after-value-error: 3 caught: test_dictionary_read_problems.test_classifies_each_error, test_dictionary_read_problems.test_describes_each_problem, test_dictionary_read_problems.test_unreadable_dictionary_message_has_headline_and_reason
permission-error-not-classified: 4 caught: test_dictionary_management_dialog.test_dictionary_held_open_without_sharing_is_unreadable, test_dictionary_read_problems.test_classifies_each_error, test_dictionary_read_problems.test_describes_each_problem, test_dictionary_read_problems.test_file_held_open_without_sharing_cannot_be_opened
csv-error-not-classified: 2 caught: test_dictionary_read_problems.test_classifies_each_error, test_dictionary_read_problems.test_describes_each_problem
no-log-line: 14 caught: test_dictionary_management_dialog.test_dictionary_held_open_without_sharing_is_unreadable, test_dictionary_management_dialog.test_each_unreadable_dictionary_is_logged, test_dictionary_management_dialog.test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count, test_dictionary_management_dialog.test_edit_on_a_dictionary_that_became_unreadable_stays_open, test_dictionary_management_dialog.test_edit_on_an_unreadable_dictionary_shows_the_error_and_stays_open, test_dictionary_management_dialog.test_refresh_after_an_action_keeps_names_counts_and_item_count_consistent, and 8 more
traceback-for-a-decode-error: 3 caught: test_dictionary_management_dialog.test_each_unreadable_dictionary_is_logged, test_dictionary_read_problems.test_count_of_unreadable_file_returns_the_error_and_logs_one_line, test_gui_document_flows.test_editor_that_cannot_read_its_dictionary_shows_the_reason
no-traceback-for-an-unexpected-error: 2 caught: test_dictionary_read_problems.test_unexpected_error_is_logged_with_traceback, test_gui_document_flows.test_editor_failure_that_is_unexpected_is_logged_with_its_traceback
reason-row-not-hidden: 2 caught: test_dictionary_management_dialog.test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count, test_dictionary_management_dialog.test_selecting_a_readable_dictionary_hides_the_reason
reason-label-never-shown: 2 caught: test_dictionary_management_dialog.test_refresh_shows_the_reason_for_the_preferred_selection, test_dictionary_management_dialog.test_selecting_an_unreadable_dictionary_shows_the_reason
no-select-all: 2 caught: test_dictionary_management_dialog.test_refresh_shows_the_reason_for_the_preferred_selection, test_dictionary_management_dialog.test_selecting_an_unreadable_dictionary_shows_the_reason
selection-change-keeps-the-old-reason: 2 caught: test_dictionary_management_dialog.test_selecting_a_readable_dictionary_hides_the_reason, test_dictionary_management_dialog.test_selecting_an_unreadable_dictionary_shows_the_reason
refresh-keeps-the-old-reason: 2 caught: test_dictionary_management_dialog.test_dictionary_held_open_without_sharing_is_unreadable, test_dictionary_management_dialog.test_refresh_shows_the_reason_for_the_preferred_selection
edit-without-the-re-read: 3 caught: test_dictionary_management_dialog.test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count, test_dictionary_management_dialog.test_edit_on_a_dictionary_that_became_unreadable_stays_open, test_dictionary_management_dialog.test_edit_on_an_unreadable_dictionary_shows_the_error_and_stays_open
edit-closes-the-dialog-on-an-unreadable-dictionary: 2 caught: test_dictionary_management_dialog.test_edit_on_a_dictionary_that_became_unreadable_stays_open, test_dictionary_management_dialog.test_edit_on_an_unreadable_dictionary_shows_the_error_and_stays_open
frame-without-the-editor-guard: 2 caught: test_gui_document_flows.test_editor_failure_that_is_unexpected_is_logged_with_its_traceback, test_gui_document_flows.test_editor_that_cannot_read_its_dictionary_shows_the_reason
frame-guard-does-not-log: 2 caught: test_gui_document_flows.test_editor_failure_that_is_unexpected_is_logged_with_its_traceback, test_gui_document_flows.test_editor_that_cannot_read_its_dictionary_shows_the_reason
validate-reads-only-the-header: 4 caught: test_dictionary_manager.test_import_dictionary_refuses_a_late_big5_file_and_copies_nothing, test_dictionary_manager.test_validate_reads_every_row, test_dictionary_presenter.test_import_invalid_csv_shows_the_reason, test_dictionary_presenter.test_import_late_big5_is_refused
presenter-new-branch-after-value-error: 2 caught: test_dictionary_presenter.test_import_big5_shows_the_not_utf8_reason, test_dictionary_presenter.test_import_late_big5_is_refused
import-error-without-the-reason: 3 caught: test_dictionary_presenter.test_import_big5_shows_the_not_utf8_reason, test_dictionary_presenter.test_import_invalid_csv_shows_the_reason, test_dictionary_presenter.test_import_late_big5_is_refused
exit 0
```

### Task 6: Packaged build and GUI checks (Windows verification; run them yourself)

Not part of the replay. In the dry run the same code was built in the scratch clone at Task 4 with the command of Step 1 ("Build complete!" in 49 s, 48,748,944 bytes; `dialog.py`, `dictionaries\read_problems.py`, `dictionaries\presenter.py` and `dictionaries\manager.py` in `PYZ-00.toc` and `gui.py` in `Analysis-00.toc` came from the clone), and the scripts of Step 2 ran against that build and printed exactly the lines of Step 3's table, each item once (in `D:\dxtest\dry*-f6` folders, deleted afterwards; no `D:\dxtest\auto*-f6` folder exists yet). Item 42 on `D:\dxtest\N-f5b\DotExpress.exe` (Step 4) printed the "Before" line. Run everything from the repository root, one item at a time, with nothing else driving the desktop. Never touch `D:\dxtest\N`, `B`, `N-p25`, `N-f3`, `N-f4*`, `N-f5*` (Step 4 only reads and copies `N-f5b\DotExpress.exe`) or the existing `D:\dxtest\auto*` folders; every F-6 run uses a new folder whose name ends in `-f6`. Only processes whose exe lies under that folder are ended (`dx.kill_under`); `lockx.py` is ended with `taskkill /T`. The user may have DotExpress open: never end any other process.

- [ ] **Step 1: Build** (PowerShell). The main checkout's venv (Python 3.13, wxPython, PyInstaller 6.21.0) is put first on `PATH`.

```powershell
Set-Location D:\workspace\DotExpress
$env:PATH = "D:\workspace\DotExpress\client\.venv\Scripts;$env:PATH"
(Get-Command pyinstaller).Source
cmd /c "scripts\build-dotexpress.bat > %TEMP%\f6-build.log 2>&1"
if (Select-String -Path $env:TEMP\f6-build.log -SimpleMatch "Build complete!" -Quiet) { "build complete" }
foreach ($m in "dialog.py", "dictionaries\\read_problems.py", "dictionaries\\presenter.py", "dictionaries\\manager.py") { if (Select-String -Path client\build\DotExpress\PYZ-00.toc -SimpleMatch "DotExpress\\client\\$m" -Quiet) { "$m bundled from the checkout" } }
if (Select-String -Path client\build\DotExpress\Analysis-00.toc -SimpleMatch "DotExpress\\client\\gui.py" -Quiet) { "gui.py analyzed from the checkout" }
New-Item -ItemType Directory -Force D:\dxtest\N-f6 | Out-Null
Copy-Item client\dist\DotExpress.exe D:\dxtest\N-f6\DotExpress.exe
(Get-Item D:\dxtest\N-f6\DotExpress.exe).Length
(Get-FileHash D:\dxtest\N-f6\DotExpress.exe).Hash
git status --short -- client docs scripts
```

Expected: `D:\workspace\DotExpress\client\.venv\Scripts\pyinstaller.exe`, `build complete` (the batch file's exit code is that of its final `popd`, so it proves nothing; on failure read `%TEMP%\f6-build.log`), the four `bundled from the checkout` lines (the three in `dictionaries` print with their doubled backslash), `gui.py analyzed from the checkout`, a size near 48.7 MB, and no `git status` output (`client\build\`, `client\dist\`, `client\DotExpress.spec` are git-ignored).

- [ ] **Step 2: Create the GUI scripts** in the new history folder by the block script (tabs, like the 2026-10-09-03 helpers they import; they contain zh-TW labels and the test rows as real characters, as `dicts.py` does). `f6gui.py` holds the shared helpers (the dictionary files, the reason row through win32 and UIA, message boxes through UIA, the file and name dialogs, the share-none lock); `lockx.py` holds a file open with share mode 0; `item42.py` covers items 42-45, `item46.py` item 46, `item47.py` item 47, `item48.py` items 48 and 49, `item50.py` items 50 and 51.

File: `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/f6gui.py`

````python
"""Shared helpers for the F-6 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py and dicts.py of the 2026-10-09-03 Windows verification unchanged.
The dictionary files are built here; their bytes are those of
client/tests/unreadable_dictionary_files.py (big5.csv, big5_late.csv) plus a UTF-8 file
with an unclosed quotation mark (badquote.csv) and readable UTF-8 files (alpha.csv,
acl.csv). Message boxes are read through UIA and their button is pressed through UIA
(``boxes``); Dictionary Management and the entries editor are left open.
"""
import ctypes
import hashlib
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO03 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-09-03-windows-verification", "auto"))
sys.path.insert(0, AUTO03)
import dx  # noqa: E402
import docs as D  # noqa: E402
import dicts as X  # noqa: E402

LOCKX = os.path.join(HERE, "lockx.py")
MGR = "字典管理"
EDITOR = "自訂字典管理器"
EM_GETSEL = 0x00B0
EM_GETLINECOUNT = 0x00BA
WM_GETTEXTLENGTH = 0x000E

HEADER = "text,braille,type\r\n"
TAIPEI_ROW = "臺北,ㄊㄞˊㄅㄟˇ,Bopomofo\r\n"
ASCII_ROWS = "".join(f"w{index:04d},x,General\r\n" for index in range(1000))
READABLE = (HEADER + "Alpha,⠁,General\r\n").encode("utf-8")
FILES = {
	"big5.csv": (HEADER + TAIPEI_ROW).encode("cp950"),
	"big5_late.csv": (HEADER + ASCII_ROWS).encode("ascii") + TAIPEI_ROW.encode("cp950"),
	# Row 2 opens a quotation mark that is never closed; more than 128 KiB of rows follow,
	# so the field passes the csv module's limit of 131,072 characters.
	"badquote.csv": (HEADER + 'bad,"oops,General\r\n' + "".join(f"q{index:05d},x,General\r\n" for index in range(8000))).encode("utf-8"),
	"alpha.csv": READABLE,
	"acl.csv": READABLE,
}
UTF8_FIXED = (HEADER + TAIPEI_ROW).encode("utf-8")
TIMESTAMP = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} ")


def digest(data):
	return hashlib.sha256(data).hexdigest()[:16]


def sha(path):
	with open(path, "rb") as stream:
		return digest(stream.read())


def write(path, data):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "wb") as stream:
		stream.write(data)


def dictionary(d):
	return os.path.join(d, "dictionary")


def shas(folder):
	return {name: sha(os.path.join(folder, name)) for name in sorted(os.listdir(folder))}


def sources(d):
	"""The test files in <d>\\data (outside the dictionary folder), for Import."""
	folder = os.path.join(d, "data")
	for name, data in FILES.items():
		write(os.path.join(folder, name), data)
	return folder


def start(exe, d, put=()):
	"""Start in a new folder once (the app creates dictionary\\default.csv), close, put the
	named FILES into dictionary\\ and start again. Returns (app, w)."""
	app, w = dx.launch(exe, d)
	print("first start, close:", D.close(app, w))
	for name in put:
		write(os.path.join(dictionary(d), name), FILES[name])
	print("dictionary:", shas(dictionary(d)))
	return dx.launch(exe, d, fresh=False)


def gui_log(d):
	"""The lines of <d>\\log\\gui.log without their time stamps ([] if there is none)."""
	path = os.path.join(d, "log", "gui.log")
	if not os.path.exists(path):
		return []
	with open(path, encoding="utf-8") as stream:
		return [TIMESTAMP.sub("", line) for line in stream.read().splitlines()]


def open_mgr(app, w, timeout=10):
	"""Choose Dictionary Management; return its window, or None if none opens (F-W12)."""
	w.set_focus()
	w.menu_select("#1->#3")
	try:
		return X.wait_window(app, w, MGR, timeout)
	except RuntimeError:
		return None


def rows(mgr):
	"""[[name, count, selected]] of the list."""
	lv, items = X.mgr_items(mgr)
	return [row + (["selected"] if lv.get_item(index).is_selected() else []) for index, row in enumerate(items)]


def reason(mgr):
	"""The reason row: what win32 shows and what UIA reports for it."""
	from pywinauto import Desktop

	descendants = mgr.wrapper_object().descendants()
	edits = [c for c in descendants if c.class_name() == "Edit" and c.is_visible()]
	labels = [c.window_text() for c in descendants if c.class_name() == "Static" and c.is_visible() and c.window_text()]
	uia = Desktop(backend="uia").window(handle=mgr.handle).descendants(control_type="Edit")
	if not edits:
		return {"edit": None, "uia edits": len(uia), "labels": labels}
	handle = edits[0].handle
	start_pos, end_pos = ctypes.c_ulong(), ctypes.c_ulong()
	user32 = ctypes.windll.user32
	user32.SendMessageW(handle, EM_GETSEL, ctypes.byref(start_pos), ctypes.byref(end_pos))
	return {
		"labels": labels,
		"uia name": uia[0].window_text() if uia else None,
		"uia value": uia[0].get_value() if uia else None,
		"sel": (start_pos.value, end_pos.value),
		"length": user32.SendMessageW(handle, WM_GETTEXTLENGTH, 0, 0),
		"lines": user32.SendMessageW(handle, EM_GETLINECOUNT, 0, 0),
	}


def boxes(app, w, press=("OK", "確定"), keep=(MGR, EDITOR)):
	"""Read every other window of the app and press its first ``press`` button through UIA.

	Returns [(title, texts)]. Windows titled in ``keep`` and file dialogs are left open.
	"""
	from pywinauto import Desktop

	out = []
	for title, win in X.windows(app, w).items():
		if title in keep:
			continue
		texts = dx.dialog_text(win)
		if "檔案名稱:" in texts:
			out.append((title, "<file dialog left open>"))
			continue
		out.append((title, [t for t in texts if t not in ("MainInstructionIcon", "關閉", title)]))
		buttons = [
			button
			for button in Desktop(backend="uia").window(handle=win.handle).descendants(control_type="Button")
			if button.window_text() in press
		]
		if buttons:
			buttons[0].invoke()
			time.sleep(0.8)
	return out


def click(mgr, label, wait=1.5):
	X.btn(mgr, label).click()
	time.sleep(wait)


def windows(app, w):
	return sorted(X.windows(app, w))


def focus_after(mgr, keys):
	"""Press ``keys`` in the dialog and return (control type, name) of the focused element."""
	from pywinauto.keyboard import send_keys
	from pywinauto.uia_defines import IUIA
	from pywinauto.uia_element_info import UIAElementInfo

	mgr.set_focus()
	send_keys(keys)
	time.sleep(0.6)
	info = UIAElementInfo(IUIA().iuia.GetFocusedElement())
	return info.control_type, info.name


def focus_list(mgr):
	lv = X.mgr_items(mgr)[0]
	mgr.set_focus()
	lv.set_focus()
	time.sleep(0.4)


def file_dialog(app, w, title, path):
	"""Fill the file dialog ``title`` with ``path`` and press its Open or Save button.

	That is the first visible button other than Cancel (the Save dialog has hidden
	buttons before it).
	"""
	dialog = X.wait_window(app, w, title)
	dialog.child_window(class_name="Edit", found_index=0).wrapper_object().set_edit_text(path)
	buttons = [
		c
		for c in dialog.wrapper_object().descendants()
		if c.class_name() == "Button" and c.is_visible() and c.window_text() not in ("取消", "Cancel")
	]
	buttons[0].click()
	time.sleep(2)


def name_dialog(app, w, title, name):
	"""Type ``name`` into the name dialog ``title``, press OK and return the boxes it showed."""
	dialog = X.wait_window(app, w, title)
	dialog.child_window(class_name="Edit").wrapper_object().set_edit_text(name)
	X.btn(dialog, "確定", "OK").click()
	time.sleep(1.5)
	return boxes(app, w)


def import_as(app, w, mgr, path, name):
	click(mgr, "匯入", wait=0.5)
	file_dialog(app, w, "匯入字典", path)
	return name_dialog(app, w, "新增字典", name)


def export_to(app, w, mgr, path):
	click(mgr, "匯出", wait=0.5)
	file_dialog(app, w, "匯出字典", path)
	return boxes(app, w)


def lock_none(path):
	"""Hold ``path`` open without sharing in another process (lockx.py) until ``unlock``."""
	process = subprocess.Popen([sys.executable, LOCKX, path, "600"], stdout=subprocess.PIPE, text=True)
	print("lock:", process.stdout.readline().strip())
	return process


def unlock(process):
	subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
	time.sleep(1)


def finish(app, w, d):
	"""Close Dictionary Management if open, close the app, end anything left under ``d``."""
	mgr = X.windows(app, w).get(MGR)
	if mgr is not None:
		X.close_mgr(app, w, mgr)
	print("close:", D.close(app, w))
	dx.kill_under(d)
````

File: `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/lockx.py`

````python
"""Hold a file open for reading without sharing: CreateFileW(GENERIC_READ, share 0).

Usage: python lockx.py <path> <seconds>
Prints "locked" once the handle is open. lock.py of 2026-10-09-03 knows only the share
modes r and rw; a file held like this cannot be opened by anyone else, for any access.
"""
import ctypes
import sys
import time
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
handle = kernel32.CreateFileW(sys.argv[1], 0x80000000, 0, None, 3, 0x80, None)
if handle is None or handle == wintypes.HANDLE(-1).value:
	print("open failed", ctypes.get_last_error(), flush=True)
	sys.exit(1)
print("locked", flush=True)
time.sleep(float(sys.argv[2]))
````

File: `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item42.py`

````python
"""Items 42-45 (F-6): Dictionary Management with a Big5 dictionary.

Usage: python item42.py <exe> <work folder>
42: start once, close, put big5.csv into dictionary\\, start, open Dictionary Management:
    the rows, no reason row, gui.log, big5.csv unchanged.
43: select big5 (the reason row appears), then default (it is gone).
45: Tab order: big5 selected, from the list Tab (the reason field) and Shift+Tab (the
    list); default selected, from the list Tab (新增).
44: big5 selected, 編輯: the error box, the dialog stays open, a second log line. Then
    big5.csv is rewritten as UTF-8 and 編輯 opens the editor with the row; 取消; reopened,
    the count is 1.
Before F-6 (N-f5b): nothing opens at 42; the script stops there.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
big5 = os.path.join(G.dictionary(d), "big5.csv")
app, w = G.start(EXE, d, put=("big5.csv",))
mgr = G.open_mgr(app, w)
if mgr is None:
	print("42: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	print("42: gui.log:", G.gui_log(d))
	G.finish(app, w, d)
	sys.exit(0)
print("42 rows:", G.rows(mgr))
print("42 reason:", G.reason(mgr))
print("42 gui.log:", G.gui_log(d))
print("42 big5.csv unchanged:", G.sha(big5) == G.digest(G.FILES["big5.csv"]), "files:", G.shas(G.dictionary(d)))

X.mgr_select(mgr, "big5")
print("43 big5 rows:", G.rows(mgr))
print("43 big5 reason:", G.reason(mgr))
X.mgr_select(mgr, "default")
print("43 default reason:", G.reason(mgr))

X.mgr_select(mgr, "big5")
G.focus_list(mgr)
print("45 big5, Tab:", G.focus_after(mgr, "{TAB}"))
print("45 big5, Shift+Tab:", G.focus_after(mgr, "+{TAB}"))
X.mgr_select(mgr, "default")
G.focus_list(mgr)
print("45 default, Tab:", G.focus_after(mgr, "{TAB}"))

X.mgr_select(mgr, "big5")
G.click(mgr, "編輯")
print("44 edit:", G.boxes(app, w))
print("44 windows:", G.windows(app, w), "rows:", G.rows(mgr))
print("44 gui.log:", G.gui_log(d))
G.write(big5, G.UTF8_FIXED)
G.click(mgr, "編輯")
editor = X.wait_window(app, w, G.EDITOR)
print("44 fixed, edit: windows:", G.windows(app, w), "editor rows:", X.editor_rows(editor))
X.btn(editor, "取消", "Cancel").click()
time.sleep(1)
print("44 cancel: windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
mgr = G.open_mgr(app, w)
print("44 reopened rows:", G.rows(mgr), "reason:", G.reason(mgr))
print("44 gui.log lines:", len(G.gui_log(d)))
G.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item46.py`

````python
"""Item 46 (F-6): a dictionary whose ACL denies the user (F-W12's original reproduction).

Usage: python item46.py <exe> <work folder>
acl.csv is a readable UTF-8 dictionary, so the reason can only come from the ACL.
icacls <dictionary>\\acl.csv /deny %USERNAME%:(W) (W includes SYNCHRONIZE, so the file
cannot be opened at all); open Dictionary Management; select acl; 編輯; 匯出 to
<work folder>\\out.csv; the ACL is restored in every case.
Before F-6 (N-f5b): nothing opens.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
acl = os.path.join(G.dictionary(d), "acl.csv")
out = os.path.join(d, "out.csv")
user = os.environ["USERNAME"]
app, w = G.start(EXE, d, put=("acl.csv",))
subprocess.run(["icacls", acl, "/deny", f"{user}:(W)"], capture_output=True)
try:
	mgr = G.open_mgr(app, w)
	if mgr is None:
		print("46: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	else:
		print("46 rows:", G.rows(mgr))
		X.mgr_select(mgr, "acl")
		print("46 acl reason:", G.reason(mgr))
		G.click(mgr, "編輯")
		print("46 edit:", G.boxes(app, w))
		print("46 windows:", G.windows(app, w))
		print("46 export:", G.export_to(app, w, mgr, out))
		print("46 out.csv exists:", os.path.exists(out), "windows:", G.windows(app, w))
finally:
	subprocess.run(["icacls", acl, "/remove:d", user], capture_output=True)
print("46 acl restored:", "DENY" not in subprocess.run(["icacls", acl], capture_output=True, text=True).stdout)
print("46 acl.csv unchanged:", G.sha(acl) == G.digest(G.FILES["acl.csv"]))
print("46 gui.log:", G.gui_log(d))
G.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item47.py`

````python
"""Item 47 (F-6): a dictionary held open by another program without sharing.

Usage: python item47.py <exe> <work folder>
lockx.py holds <dictionary>\\alpha.csv (a readable UTF-8 dictionary) with share mode 0;
open Dictionary Management; select alpha; release the lock; 編輯 (re-read): the editor
opens with the row; 取消.
Before F-6 (N-f5b): nothing opens.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
alpha = os.path.join(G.dictionary(d), "alpha.csv")
app, w = G.start(EXE, d, put=("alpha.csv",))
holder = G.lock_none(alpha)
try:
	mgr = G.open_mgr(app, w)
	if mgr is None:
		print("47: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	else:
		print("47 rows:", G.rows(mgr))
		X.mgr_select(mgr, "alpha")
		print("47 alpha reason:", G.reason(mgr))
finally:
	G.unlock(holder)
print("47 unlocked")
if mgr is not None:
	G.click(mgr, "編輯")
	print("47 edit after unlock: boxes:", G.boxes(app, w), "windows:", G.windows(app, w))
	editor = X.windows(app, w).get(G.EDITOR)
	if editor is not None:
		print("47 editor rows:", X.editor_rows(editor))
		X.btn(editor, "取消", "Cancel").click()
		time.sleep(1)
print("47 alpha.csv unchanged:", G.sha(alpha) == G.digest(G.FILES["alpha.csv"]))
print("47 gui.log:", G.gui_log(d))
G.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item48.py`

````python
"""Items 48 and 49 (F-6): Import refuses a file that cannot be read; a CSV over the field limit.

Usage: python item48.py <exe> <work folder>
The sources are written to <work folder>\\data. badquote.csv is also put into the
dictionary folder before the second start.
48: import data\\big5.csv as b1 and data\\big5_late.csv as b2.
49: select badquote (the reason row); import data\\badquote.csv as bq2.
Before F-6 (N-f5b): nothing opens (badquote.csv is in the dictionary folder).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = G.start(EXE, d, put=("badquote.csv",))
data = G.sources(d)
before = G.shas(data)
mgr = G.open_mgr(app, w)
if mgr is None:
	print("48: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	G.finish(app, w, d)
	sys.exit(0)
print("48 rows:", G.rows(mgr))
print("48 import big5.csv as b1:", G.import_as(app, w, mgr, os.path.join(data, "big5.csv"), "b1"))
print("48 import big5_late.csv as b2:", G.import_as(app, w, mgr, os.path.join(data, "big5_late.csv"), "b2"))
print("48 rows after:", G.rows(mgr), "windows:", G.windows(app, w))
print("48 dictionary files:", sorted(os.listdir(G.dictionary(d))))

X.mgr_select(mgr, "badquote")
print("49 badquote reason:", G.reason(mgr))
print("49 import badquote.csv as bq2:", G.import_as(app, w, mgr, os.path.join(data, "badquote.csv"), "bq2"))
print("49 rows after:", G.rows(mgr))
print("49 dictionary files:", sorted(os.listdir(G.dictionary(d))))
print("48-49 sources unchanged:", G.shas(data) == before)
print("48-49 gui.log:", G.gui_log(d))
G.finish(app, w, d)
````

File: `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item50.py`

````python
"""Items 50 and 51 (F-6): Rename, Export, Delete and conversion with an unreadable dictionary.

Usage: python item50.py <exe> <work folder>
50: big5.csv in the dictionary folder: rename big5 to big5x; export big5x to
    <work folder>\\out.csv; delete big5x (confirm with 是).
51: big5.csv written again; Settings: dictionary big5; input 臺北; convert.
Before F-6 (N-f5b): nothing opens at 50.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import D, X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
out = os.path.join(d, "out.csv")
app, w = G.start(EXE, d, put=("big5.csv",))
mgr = G.open_mgr(app, w)
if mgr is None:
	print("50: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	G.finish(app, w, d)
	sys.exit(0)
X.mgr_select(mgr, "big5")
G.click(mgr, "重新命名", wait=0.5)
print("50 rename big5 -> big5x:", G.name_dialog(app, w, "重新命名字典", "big5x"))
print("50 rows:", G.rows(mgr), "reason:", G.reason(mgr))
print("50 export big5x:", G.export_to(app, w, mgr, out))
print("50 out.csv equals the source:", G.sha(out) == G.digest(G.FILES["big5.csv"]))
G.click(mgr, "刪除")
print("50 delete big5x:", G.boxes(app, w, press=("是(Y)", "是(&Y)", "Yes")))
print("50 rows:", G.rows(mgr), "boxes:", G.boxes(app, w))
print("50 dictionary files:", sorted(os.listdir(G.dictionary(d))))
X.close_mgr(app, w, mgr)

G.write(os.path.join(G.dictionary(d), "big5.csv"), G.FILES["big5.csv"])
X.set_dictionary(app, w, "big5")
D.set_input(w, "臺北")
print("51 convert:", X.convert(app, w))
X.set_dictionary(app, w, "default")
print("50-51 gui.log:", G.gui_log(d))
G.finish(app, w, d)
````

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto
cd $REPO
"$UIA" -c "import pywinauto, psutil; print(pywinauto.__version__, psutil.__version__)"
"$UIA" -m py_compile $H/f6gui.py $H/lockx.py $H/item42.py $H/item46.py $H/item47.py $H/item48.py $H/item50.py && echo "scripts compile"
rm -rf $H/__pycache__
git status --short -- client docs scripts
```

Expected: `0.6.9 7.2.2` (or a later psutil), `scripts compile`, and `?? docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/`. `UIA` is a pywinauto venv outside the repo (HANDOFF section 8: `py -3.13 -m venv <scratchpad>\uia`, then `pip install pywinauto==0.6.9 psutil`); if its `Scripts\python.exe` is missing, run `py -3.13 -m venv --upgrade <venv>`.

- [ ] **Step 3: Items 42-51** (Git Bash, from the repository root). Each script makes a new work folder (`dx.launch` deletes it first, after ending any process under it), starts the exe once, closes it, writes the test files, starts it again and ends with `close: exited`. Read each log against the table before the next item.

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto
EXE=/d/dxtest/N-f6/DotExpress.exe
export PYTHONIOENCODING=utf-8
cd $REPO
"$UIA" $H/item42.py $EXE /d/dxtest/auto42-f6 > /d/dxtest/auto42-f6.log 2>&1
"$UIA" $H/item46.py $EXE /d/dxtest/auto46-f6 > /d/dxtest/auto46-f6.log 2>&1
"$UIA" $H/item47.py $EXE /d/dxtest/auto47-f6 > /d/dxtest/auto47-f6.log 2>&1
"$UIA" $H/item48.py $EXE /d/dxtest/auto48-f6 > /d/dxtest/auto48-f6.log 2>&1
"$UIA" $H/item50.py $EXE /d/dxtest/auto50-f6 > /d/dxtest/auto50-f6.log 2>&1
```

Expected (every log starts with `first start, close: exited` and a `dictionary:` line with the sha256 prefixes `big5.csv` `f951f65cad59b201`, `badquote.csv` `90f44d31d25e93a0`, `alpha.csv` and `acl.csv` `fba22ddc73966c0d`, `default.csv` `8f0594e9a11d46bb`, and ends with `close: exited`; `<reason NOT_UTF8>` is `檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。`, `<reason CANNOT_OPEN>` is `無法開啟檔案。檔案可能正被其他程式使用，或您沒有讀取權限。請關閉其他程式後再試一次。`, `<decode error>` is `'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte`; paths appear with doubled backslashes, as Python's repr prints them; the "Before" column is the spec's, except item 42, which Step 4 runs on N-f5b):

| # | Expected after F-6 | Before (N-f5b) |
| --- | --- | --- |
| 42 | `42 rows: [['big5', '無法讀取'], ['default', '0', 'selected']]`; `42 reason: {'edit': None, 'uia edits': 0, 'labels': []}`; `42 gui.log: ['[ERROR] Cannot read dictionary "big5.csv": UnicodeDecodeError: <decode error>']` (no `Traceback`); `42 big5.csv unchanged: True` | `42: Dictionary Management did not open; windows: [] boxes: []`, `42: gui.log: []` (F-W12) |
| 43 | `43 big5 rows: [['big5', '無法讀取', 'selected'], ['default', '0']]`; `43 big5 reason: {'labels': ['無法讀取的原因：'], 'uia name': '無法讀取的原因：', 'uia value': '<reason NOT_UTF8>', 'sel': (0, 61), 'length': 61, 'lines': 2}`; `43 default reason: {'edit': None, 'uia edits': 0, 'labels': []}` | - |
| 45 | `45 big5, Tab: ('Edit', '無法讀取的原因：')`; `45 big5, Shift+Tab: ('ListItem', 'big5')`; `45 default, Tab: ('Button', '新增')` | - |
| 44 | `44 edit: [('錯誤', ['無法讀取字典「big5」。', '<reason NOT_UTF8>', 'OK'])]` (the task dialog shows the headline as its main instruction and the reason as its content); `44 windows: ['字典管理']`, big5 still selected; `44 gui.log:` the 42 line twice; `44 fixed, edit: windows: ['自訂字典管理器'] editor rows: [['臺北', 'ㄊㄞˊㄅㄟˇ', '注音']]`; `44 cancel: windows: [] boxes: []`; `44 reopened rows: [['big5', '1'], ['default', '0', 'selected']]`, no reason row; `44 gui.log lines: 2` | - |
| 46 | `46 rows: [['acl', '無法讀取'], ['default', '0', 'selected']]`; `46 acl reason:` labels and UIA name as in 43, `'uia value': '<reason CANNOT_OPEN>', 'sel': (0, 42), 'length': 42, 'lines': 2`; `46 edit: [('錯誤', ['無法讀取字典「acl」。', '<reason CANNOT_OPEN>', 'OK'])]`; `46 windows: ['字典管理']`; `46 export: [('錯誤', ["匯出字典失敗：[Errno 13] Permission denied: '...\\acl.csv'", 'OK'])]`; `46 out.csv exists: False windows: ['字典管理']`; `46 acl restored: True`; `46 acl.csv unchanged: True`; `46 gui.log:` two lines `[ERROR] Cannot read dictionary "acl.csv": PermissionError: [Errno 13] Permission denied: '...\\acl.csv'` | nothing opens |
| 47 | `lock: locked`; `47 rows: [['alpha', '無法讀取'], ['default', '0', 'selected']]`; `47 alpha reason:` as 46 (`<reason CANNOT_OPEN>`, `(0, 42)`); `47 unlocked`; `47 edit after unlock: boxes: [] windows: ['自訂字典管理器']`; `47 editor rows: [['Alpha', '⠁', '一般']]`; `47 alpha.csv unchanged: True`; `47 gui.log:` one `PermissionError` line for `alpha.csv` | nothing opens |
| 48 | `48 rows: [['badquote', '無法讀取'], ['default', '0', 'selected']]`; `48 import big5.csv as b1: [('錯誤', ['匯入字典失敗：<reason NOT_UTF8>', 'OK'])]`; `48 import big5_late.csv as b2:` the same; `48 rows after:` unchanged, `windows: ['字典管理']`; `48 dictionary files: ['badquote.csv', 'default.csv']` | Dictionary Management does not open (badquote.csv); with only the sources: `b1` shows `匯入的檔案必須包含 text、braille 與 type 表頭。`, `b2` is copied (spec) |
| 49 | `49 badquote reason: {'labels': ['無法讀取的原因：'], 'uia name': '無法讀取的原因：', 'uia value': '檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：field larger than field limit (131072)', 'sel': (0, 71), 'length': 71, 'lines': 2}`; `49 import badquote.csv as bq2: [('錯誤', ['匯入字典失敗：檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：field larger than field limit (131072)', 'OK'])]`; `49 rows after: [['badquote', '無法讀取', 'selected'], ['default', '0']]`; `49 dictionary files: ['badquote.csv', 'default.csv']`; `48-49 sources unchanged: True`; `48-49 gui.log: ['[ERROR] Cannot read dictionary "badquote.csv": Error: field larger than field limit (131072)']` | nothing opens |
| 50 | `50 rename big5 -> big5x: []`; `50 rows: [['big5x', '無法讀取', 'selected'], ['default', '0']]` with the `<reason NOT_UTF8>` row (`(0, 61)`); `50 export big5x: []`; `50 out.csv equals the source: True`; `50 delete big5x: [('確認刪除字典', ['要刪除字典「big5x」嗎？', '是(Y)', '否(N)'])]`; `50 rows: [['default', '0', 'selected']] boxes: []`; `50 dictionary files: ['default.csv']` | not reachable |
| 51 | `51 convert: ('', [('錯誤', ["轉譯失敗：<decode error>", 'OK'])])` (unchanged, D10); `50-51 gui.log:` one `UnicodeDecodeError` line for `big5.csv` and one for `big5x.csv` | same message |

- [ ] **Step 4: Before (F-W12 on the pre-F-6 build).** Item 42 on `N-f5b` (main `0708f44`, the build the user tests with): the script stops after the first open.

```bash
UIA=$SP/uia/Scripts/python.exe
H=docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto
export PYTHONIOENCODING=utf-8
cd $REPO
"$UIA" $H/item42.py /d/dxtest/N-f5b/DotExpress.exe /d/dxtest/auto42-f5b-f6 > /d/dxtest/auto42-f5b-f6.log 2>&1
```

Expected: `first start, close: exited`, the `dictionary:` line, `42: Dictionary Management did not open; windows: [] boxes: []`, `42: gui.log: []`, `close: exited`.

- [ ] **Step 5: Record and commit the results.** Write `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto-results.md` in the style of `2026-10-10-01-f5-save-failure-handling/auto-results.md` (zh-TW): the build (PyInstaller version, `Build complete!`, the bundled modules, size, sha256), then one row per item (42, 43, 44, 45, 46, 47, 48, 49, 50, 51, and 42 on N-f5b) with ✔/△/✘ and the observed rows, reason rows, focus, message boxes, files and log lines. Any deviation from the table above is reported to the orchestrator before the commit, not explained away; a re-run after a GUI timing problem (for example the foreground taken by another program) is recorded with the first attempt's log name. End the file with a short section **「仍需人工（使用者）」** for item 52, worded for the user (do not mark it done):

  > 52（NVDA）：請在 NVDA 執行中檢查字典管理的「無法讀取的原因」欄位。把 `D:\dxtest\N-f6\DotExpress.exe` 複製到新資料夾 `D:\dxtest\manual52-f6\` 執行一次後關閉；把 `D:\dxtest\auto48-f6\data\big5.csv`（以 Big5 儲存的字典，和繁體中文 Excel「CSV（逗號分隔）」存出的格式相同）複製到 `D:\dxtest\manual52-f6\dictionary\`，再執行 DotExpress，開啟「字典管理」。請記錄 NVDA 依序讀出的內容，並確認：用方向鍵移到 `big5` 時讀出「無法讀取」；按 Tab 時讀出標籤「無法讀取的原因」、欄位的角色（編輯區、多行、唯讀）以及**完整的**原因文字（兩行都讀到，不是只讀第一行）；按 Shift+Tab 回到清單；按「編輯」時錯誤對話框被當作對話框讀出（標題、「無法讀取字典「big5」。」與原因）。如果 NVDA 只讀出第一行，請告訴我們（D3 的全選做法可能需要調整）。

```bash
cd $REPO
git add docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto-results.md docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/f6gui.py docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/lockx.py docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item42.py docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item46.py docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item47.py docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item48.py docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/item50.py
git diff --cached --stat
git commit -q -m "docs: record the F-6 packaged-build GUI checks (F-6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short -- client docs scripts
git rev-parse HEAD:client
```

Expected: the eight files in the `--stat`, no `status` output, and the Task 4 tree id `e995d5444d769da21245201c3771bb27d9026edc` (the commit touches no file under `client/`). Do not merge `main` or push; the orchestrator decides.

## Implementation Notes (2026-10-10)

Tasks 0-6 were executed in the main checkout as written, with no deviation from the dry run: every red and green output, `Ran` count, catalog step and expected block matched. The committed `HEAD:client` trees are the plan's: Task 1 (`36d863e`) `d20554f30b8331a9e113f481d695349b0288139a`, Task 2 (`99fda8a`) `290c21bd3c83c5a2f4cc48b73ab0da4ffb3f84d9`, Task 3 (`7cc1fd1`) `01e8a26c795433d8e5fd14d945b8d77c2067f4bb`, Task 4 (`6068661`, and Task 6's `2dc5328`) `e995d5444d769da21245201c3771bb27d9026edc`. The exe of Task 6 and every GUI result are in `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto-results.md`.

1. **Review fixes.** The review (`docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/review_task.md`, verdict Ready) found eight Minor items. M-1 (the reason field selects all again when it gets focus), M-3 (two test assertions that kill two surviving mutants), M-6 (`read_problems` gets its logger when it logs, not at import) and M-7 (the zh-TW `CANNOT_OPEN` reason says 你; this section) were fixed after the review, so the trees and counts above are no longer the branch head's: the full suite is `Ran 1337`, and the template's `#:` references follow the moved lines. The spec's "Corrected after review" lists the changes; the "修正記錄" section of the review file records each item and the rebuilt exe (`N-f6b`). The plan's blocks above keep the original text (for example 您 in Task 4) as the record of what was applied.
