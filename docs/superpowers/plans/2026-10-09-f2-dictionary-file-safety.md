# Dictionary File Safety (F-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the two priority-1 data-loss defects in dictionary files. A dictionary CSV saved with a UTF-8 BOM (Excel "CSV UTF-8", Notepad) opens with its rows, counts its entries, imports and converts; OK saves it without the BOM. The entries editor's OK never leaves a half-written dictionary: it writes a temporary file in the same directory and installs it with `os.replace`; on any failure the dictionary is byte-identical to before, no temporary file is left, and the existing `Failed to save: {error}` message appears with the edits kept. On POSIX the saved file keeps the permission bits of the file it replaces (plan amendment). No new user-facing string (msgids 353, same set); everything else is unchanged.

**Architecture:** Three commits in the spec's migration order. Task 1 adds `client/shared/atomic_write.py` (`write_text_atomically`, D4, plus the permission amendment); nothing uses it yet. Task 2 routes `save_dictionary_entries` through it (D5) and widens the OK handler to `except Exception` (D7), replacing the Q3/Q7 `KNOWN BUG` test. Task 3 switches the five CSV readers R1-R5 to `encoding="utf-8-sig"` (D1), replacing the Q1 `KNOWN BUG` test. Every task is red first; Task 4 runs the acceptance criteria and a 15-mutant check (the spec's 12 plus 3 for the amendment).

**Tech Stack:** Python 3 standard library (`tempfile.NamedTemporaryFile`, `os.replace`, `os.fsync`, `os.chmod`, `os.umask`, `csv`, `contextlib.suppress`, `unittest`). wxPython is not installed; the dialog tests keep their `tests/wx_stub.py` scope.

**Spec:** `docs/superpowers/specs/2026-10-09-f2-dictionary-file-safety-design.md` (authoritative, commit `1f9aae8`), with the orchestrator's amendment and the refinements listed under Spec Corrections and Refinements.

## Global Constraints

- Branch: `fix/f2-dictionary-file-safety`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (13, nothing else): production `client/shared/atomic_write.py` (new, 4 spaces), `client/dictionaries/entries.py` (tabs), `client/dictionaries/manager.py` (4 spaces), `client/conversion/text/dictionary_rules.py` (4 spaces), `client/conversion/text/char_maps.py` (4 spaces), `client/dialog.py` (tabs); tests `client/tests/test_atomic_write.py` (new, 4 spaces), `client/tests/test_dictionary_entries.py` (tabs), `client/tests/test_dictionary_entries_dialog.py` (4 spaces), `client/tests/test_dictionary_manager.py` (4 spaces), `client/tests/test_dictionary_management_dialog.py` (tabs), `client/tests/test_conversion_text_dictionary_rules.py` (4 spaces), `client/tests/test_conversion_text_char_maps.py` (4 spaces). Never touch `client/gui.py`, `client/dictionaries/entry_list_model.py`, `client/locales/` (`.po`/`.mo`), `client/tests/fixtures/`, `client/tests/wx_stub.py` or the spec.
- **`client/dictionary/` is real user data.** No step writes to it; every test uses a temporary directory. Criterion 6 (Task 4 Step 2) proves it with the application-data snapshot.
- The patches below carry the exact characters (tabs in the tab-indented files, the braille and Bopomofo literals). Run every block as it is, do not retype. If `git apply` refuses a patch, stop and re-check the previous step; do not hand-merge.
- No user-facing string changes and no msgid changes: `source msgids: 353`, compared with the Task 0 snapshot in Task 4 (`SOURCE == SAVED`).
- Fixtures are never touched: `client/tests/fixtures/translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `client/tests/fixtures/dictionary_entries_trace.json` sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`.
- The other P2-2 pins stay: the `KNOWN BUG (P2-2 spec, Q2/Q4/Q5/Q6/Q8)` tests are not edited (checked byte for byte against `main` in Task 4 Step 5).
- P2-5 is on hold: the one known failure `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math` stays failing with the same assertion after every task; do not touch `translate.py`.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run. Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers, exception lines cut to 220 characters, `Ran` without timing, final status, temporary directory names replaced by `<tmpdir>`), so the blocks are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/f2impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`.
- Baseline (re-verified at `1f9aae8`, the spec commit; code identical to `aced6f8` = `main`): `$PY -m unittest discover -s tests` gives `Ran 1114 tests`, `FAILED (failures=1, skipped=7)` (the P2-5 failure; 7 Windows-only liblouis skips). The process umask on this machine is `0022`; the two permission tests set their own umask or mode and do not depend on it.

## Spec Corrections and Refinements (decided in this plan)

1. **Orchestrator amendment: keep the permission bits (supersedes the spec's acceptance of mode `0600`).** The spec (Current State, Risks "File metadata") accepts that on POSIX the atomically saved dictionary gets `NamedTemporaryFile`'s mode `0600`. That is an avoidable regression (a dictionary that was `0644` or group-readable silently becomes private), so `write_text_atomically` sets the temporary file's mode before the `os.replace`:
   - target exists: `stat.S_IMODE(os.stat(target).st_mode)` (that is `st_mode & 0o7777`; `os.stat` follows a symbolic link, so a link's target mode is used);
   - target missing (`FileNotFoundError`): `0o666 & ~umask`, the mode a plain `open(path, "w")` gives a new file. Python has no getter for the umask; the helper reads it with `umask = os.umask(0); os.umask(umask)`. The umask is process-wide, so another thread creating a file during those two adjacent calls would get umask `0`. This happens only when OK saves a dictionary that does not exist yet (deleted outside the app, or the missing-folder case), on POSIX only; the app's dictionary folder is per-user. Accepted and recorded under Risks below; the race-free alternative (creating the temporary file with `os.open(..., 0o666)` and own name generation instead of `NamedTemporaryFile`) was rejected because it replaces the stdlib's name generation and retry loop that the spec (D4) and `save_preprocessing_script` share.
   - Only `if os.name == "posix"`. On Windows `os.chmod` only toggles the read-only attribute: copying it from a read-only dictionary would make the temporary file read-only, `os.replace` fails anyway (as the old `open("w")` did), and then removing the read-only temporary file fails too, leaking a `.tmp`. So on Windows the installed file keeps default attributes, as the spec's Risks say.
   - Residual POSIX difference (recorded, not changed): a dictionary whose mode denies the owner write access (`0444`) used to fail on OK with `PermissionError`; now the rename succeeds (it needs only a writable folder) and the new file keeps `0444`. Ownership and extended attributes are not copied (a new file belongs to the current user), as for any replace-by-rename.
   - Tests (red first, POSIX only, `@unittest.skipUnless(os.name == "posix", ...)`; on Windows they skip): A8 `test_keeps_the_permission_bits_of_an_existing_file` (existing `0o640` stays `0o640`) and A9 `test_a_new_file_gets_the_default_mode_for_the_umask` (umask `0o002` set by the test and restored by `addCleanup`, new file `0o664`). Both values differ from `0o600` (no chmod) and from `0o644` (the usual default), so a constant cannot pass both. Task 1 is red in two stages: first the module import fails, then, after the spec's D4 helper (Step 3), exactly A8 and A9 fail with `'0o600' != ...`; Step 5 adds the permission code.
   - Three extra mutants (`permission-bits-not-set`, `existing-mode-not-kept`, `new-file-ignores-the-umask`), so 15 in all.
   - Counts: 2 more tests than the spec, `Ran 1131` instead of 1129 (skips stay 7 on Linux).
2. **Task 1's first red is one module error.** The test module imports `import shared.atomic_write as atomic_write` at the top, so before the module exists the loader reports one `ModuleNotFoundError: No module named 'shared.atomic_write'` (`Ran 1 test`, `errors=1`), not nine separate failures.
3. **Task 2 is red for four tests, not three.** Besides B10, the flipped Q3/Q7 test and G15 (spec), the updated `test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds` also fails on the old code: the old message `[Errno 21] Is a directory: '<path>'` has no ` -> '<path>'` suffix. B9 passes before (it pins D2).
4. **The doubled BOM is pinned in the table.** D1 says "edge cases, both pinned" but Test Plan C lists only the two "only a BOM" rows. `_error_cases()` gets a third new row, "dictionary with a doubled BOM" (`b"\xef\xbb\xbf\xef\xbb\xbftext,braille,type\n"`, `ValueError`, the column message); it passes before and after (only the first BOM is stripped). 11 cases; table rows are subtests, so the test count does not change.
5. **Names and details the spec leaves open.** The spec calls the `apply_dictionary` table test `test_apply_dictionary_raises_the_recorded_errors`; its real name is `DictionaryFileSemanticsTest.test_malformed_files_raise_the_recorded_errors`. The flipped Q3/Q7 test edits the first row (Alpha) to `"\ud800"`, so the kept rows are `[["\ud800", "⠁", GENERAL], BETA_CELLS]`; its message is `儲存失敗：'utf-8' codec can't encode character '\ud800' in position 0: surrogates not allowed`. The dialog tests use a small module helper `_listing(directory)` (sorted names). The updated OS-error test checks the log entry's kind, title and flags exactly, the message's prefix `儲存失敗：` and suffix ` -> ` + `repr(str(path))`, and that the directory listing is only `dictionary.csv` (still a directory). C11 also asserts that the rules are not empty and change `台都`, so equal-but-empty rules cannot pass. E13 also asserts the imported path. F14 also asserts the name column.
6. **Counts per commit:** 1114, then 1123 (Task 1: A1-A9), 1126 (Task 2: B9, B10, G15; the flip and the update replace tests one for one), 1131 (Task 3: B8, C11, D12, E13, F14; the Q1 flip replaces one for one).

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `1f9aae8` (`$SP/f2plan/dry`, never the repo), one commit per task; after Task 3 the full suite, the 20 shuffle seeds, the msgid scan, the fixtures, the app-data snapshot, every acceptance criterion and the 15 mutants passed. The patches in this plan are `git diff`s of that clone, split into each task's test step and production step (Task 1's production step in two parts). Then this file's blocks were run in order on fresh clones (`$SP/f2plan/replay*`, each with a stand-in plan commit and a local `main` at `aced6f8`) by a harness that runs every `bash` block from `client/` and compares each "Expected" block with the real output: all 3 commits applied, every expected block matched byte for byte, and the resulting tree is identical to the dry clone's. Final sha256: `client/shared/atomic_write.py` `48267c3571709bff1616c023ac7ecab11258cbef7938da3affd2d16ffafddf6f`, `client/dictionaries/entries.py` `870404479d32911809f9352222cfbfb920e9487c906786a1790d08aecccd5fe4`, `client/dialog.py` `ed7a959d1688ff59b2a7e6c414f066511c046af5298140d0bcd595ec609aa8f3`, `client/dictionaries/manager.py` `942a6daa434b64843c4d181239453344db886daafa6bcd9f1fbed3535fc55187`, `client/conversion/text/dictionary_rules.py` `d09cbd835deb49ec76923bce64f4b98fb69c315e455caac90df471d321474e6c`, `client/conversion/text/char_maps.py` `9b47423e0c292a07f921939b6281cb7c05adce6ef17f14755a6c2c68305f86df`. Windows-only behavior was not run; see Windows Verification Debt.

## Review Focus

Inputs and failure modes the spec implies that a user is most likely to meet; each is pinned by a test in the task that owns the code.

1. **A dictionary saved by Excel ("CSV UTF-8") or Notepad** opens with its rows, shows its entry count, imports with its bytes unchanged and converts; OK saves it without the BOM. Pinned by B8, F14, E13, C11, D12 and the flipped Q1 test (Task 3).
2. **An entry Python cannot encode** (a lone surrogate pasted from a broken source): OK shows `儲存失敗：...`, the dialog stays open with the edit, the file is byte-identical, no `.tmp`. Pinned by the flipped Q3/Q7 test and B10 (Task 2), A3 (Task 1).
3. **The dictionary locked or not replaceable on Windows** (sharing violation in `os.replace`): same visible result, and a second OK succeeds once the lock is gone. Pinned by G15 and A4 with a patched `os.replace` (Tasks 1-2); a real lock is Windows debt.
4. **Leftover `.tmp` files** never appear as dictionaries: the name `.<name>.csv.<random>.tmp` does not match `*.csv`. Every failure test asserts the directory listing.
5. **Permissions on Linux/macOS**: a group-readable dictionary stays group-readable after OK; a dictionary created by OK gets the umask default. Pinned by A8 and A9 (Task 1).

## File Map

- Task 1: create `client/tests/test_atomic_write.py` (`WriteTextAtomicallyTest`, 9 tests), then create `client/shared/atomic_write.py` in two parts (spec D4; permission amendment).
- Task 2: `client/tests/test_dictionary_entries.py` (B9, B10), `client/tests/test_dictionary_entries_dialog.py` (`_listing`; OS-error test updated; G15; Q3/Q7 flipped), then `client/dictionaries/entries.py` (`save_dictionary_entries` through the helper) and `client/dialog.py` (`except Exception`).
- Task 3: `client/tests/test_dictionary_entries.py` (B8), `client/tests/test_conversion_text_dictionary_rules.py` (table rows, C11), `client/tests/test_conversion_text_char_maps.py` (D12), `client/tests/test_dictionary_manager.py` (E13), `client/tests/test_dictionary_management_dialog.py` (F14), `client/tests/test_dictionary_entries_dialog.py` (Q1 flipped), then `utf-8-sig` in `client/dictionaries/entries.py`, `client/dictionaries/manager.py`, `client/conversion/text/dictionary_rules.py` (two readers and the docstring), `client/conversion/text/char_maps.py`.

## Expected Counts

| After task | tests added | tests removed | `Ran` | final line |
| --- | --- | --- | --- | --- |
| baseline | - | - | 1114 | `FAILED (failures=1, skipped=7)` |
| 1 helper | 9 (A1-A9) | 0 | 1123 | `FAILED (failures=1, skipped=7)` |
| 2 atomic save | 3 (B9, B10, G15); Q3/Q7 flipped and OS-error test updated in place | 0 | 1126 | `FAILED (failures=1, skipped=7)` |
| 3 utf-8-sig | 5 (B8, C11, D12, E13, F14); Q1 flipped in place; table rows replaced | 0 | 1131 | `FAILED (failures=1, skipped=7)` |

The one failure in every row is the P2-5 case. The 7 skips are the Windows-only liblouis tests (A8 and A9 run on Linux).

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0, outside the repo:

- `brief.py`: condenses unittest output (see Global Constraints).
- `f2_mutants.py <repo_dir> <scratch_dir> [mutant ...]`: copies `client/` (without `.venv`, `log`, the user data `dictionary/`, `workspace/`, `config.json`, and `__pycache__`) to `<scratch_dir>/client`, then for each of 15 mutants edits one production file of the copy, runs the seven F-2 test modules there, prints which tests caught it and restores the file. The repo is never changed. Matches the code after Task 3.
- Existing: `$SP/p12/tools/msgid_scan.py` (the P0-5 AST stand-in for xgettext), `$SP/shuffle_harness.py <seed>` (every test module in a seeded random order, one process) and `$SP/p26impl/snap.sh` (the P2-6 application-data snapshot; its first line `cd`s into `/workspace/DotExpress/client`, so it is run as `sed 1d` from the current `client/`).

---

### Task 0: Record the baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
git -C $REPO diff main --stat -- client
```

Expected (no output from `status` and from the diff; HEAD is the plan commit):

```text
docs: plan dictionary file safety fix
fix/f2-dictionary-file-safety
```

- [ ] **Step 2: Create the throwaway tools.**

```bash
mkdir -p $T/tools
cat > $T/tools/brief.py <<'PYEOF'
"""Condense unittest output read from stdin (throwaway).

Keeps the FAIL/ERROR headers, exception lines (cut to 220 characters), the "Ran"
line without its timing and the final OK/FAILED line, so outputs can be compared.
Temporary directory names are replaced by <tmpdir>.
"""
import re
import sys

for line in sys.stdin:
    line = re.sub(r"/tmp/tmp[a-z0-9_]{8}", "<tmpdir>", line.rstrip("\n"))
    if re.match(r"(FAIL|ERROR): ", line) or re.match(r"[A-Za-z_.]*(Error|Exception): ", line):
        print(line[:220])
    elif line.startswith("Ran "):
        print(re.sub(r" in [0-9.]+s$", "", line))
    elif line.startswith(("OK", "FAILED")):
        print(line)
PYEOF
cat > $T/tools/f2_mutants.py <<'PYEOF'
"""Run the F-2 tests against deliberately broken code (throwaway).

Usage: python f2_mutants.py <repo_dir> <scratch_dir> [mutant ...]
Copies <repo_dir>/client (without .venv, log, the user data dictionary/, workspace/ and
config.json, and __pycache__) to <scratch_dir>/client (fresh each run), then for each
mutant edits one file of the copy, runs the seven F-2 test modules there and restores
the file. <repo_dir> is never changed. Matches the code after Task 3.
Prints "<mutant>: caught by <test method> ..." or "<mutant>: SURVIVED"; exit status 1 when
a mutant survives or its old text is not found exactly once.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

MODULES = [
    "tests.test_atomic_write",
    "tests.test_dictionary_entries",
    "tests.test_dictionary_entries_dialog",
    "tests.test_dictionary_manager",
    "tests.test_dictionary_management_dialog",
    "tests.test_conversion_text_dictionary_rules",
    "tests.test_conversion_text_char_maps",
]
HELPER = "shared/atomic_write.py"
ENTRIES = "dictionaries/entries.py"
RULES = "conversion/text/dictionary_rules.py"
SAVE_CALL = '\twrite_text_atomically(dictionary_path, _write, encoding="utf-8", newline="")\n'
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
WRITE_STEPS = """            write(stream)
            stream.flush()
            os.fsync(stream.fileno())
"""
MUTANTS = {
    # D1: each reader back to utf-8 (the BOM defect reintroduced per reader).
    "r1-load-entries-utf8": (ENTRIES, 'newline="", encoding="utf-8-sig") as fp:', 'newline="", encoding="utf-8") as fp:'),
    "r2-validate-import-utf8": ("dictionaries/manager.py", 'encoding="utf-8-sig"', 'encoding="utf-8"'),
    "r3-rules-dictionary-utf8": (RULES, 'encoding="utf-8-sig") as f_d:', 'encoding="utf-8") as f_d:'),
    "r4-rules-bopomofo-utf8": (RULES, 'encoding="utf-8-sig") as f_b:', 'encoding="utf-8") as f_b:'),
    "r5-char-maps-utf8": ("conversion/text/char_maps.py", 'encoding="utf-8-sig"', 'encoding="utf-8"'),
    # D5: the in-place write (the truncation defect reintroduced).
    "save-direct-open": (ENTRIES, SAVE_CALL, '\twith dictionary_path.open("w", newline="", encoding="utf-8") as fp:\n\t\t_write(fp)\n'),
    # D4: the helper's guarantees.
    "clean-up-only-on-os-error": (HELPER, CLEAN_UP, CLEAN_UP_ON_OS_ERROR),
    "temporary-path-recorded-after-write": (
        HELPER,
        "            temporary_path = Path(stream.name)\n" + WRITE_STEPS,
        WRITE_STEPS + "            temporary_path = Path(stream.name)\n",
    ),
    "no-fsync": (HELPER, "            os.fsync(stream.fileno())\n", ""),
    "temporary-file-in-system-temp": (HELPER, "dir=destination.parent,", "dir=None,"),
    # D2: output encoding.
    "save-writes-a-bom": (ENTRIES, SAVE_CALL, SAVE_CALL.replace('"utf-8"', '"utf-8-sig"')),
    # D7: the OK handler (the escaping exception reintroduced).
    "ok-catches-os-error-only": (
        "dialog.py",
        "\t\t\tself._model.save(self.dictionary_path)\n\t\texcept Exception as exc:\n",
        "\t\t\tself._model.save(self.dictionary_path)\n\t\texcept OSError as exc:\n",
    ),
    # Plan amendment: permission bits (POSIX).
    "permission-bits-not-set": (
        HELPER,
        '        if os.name == "posix":  # NamedTemporaryFile creates 0o600\n'
        "            os.chmod(temporary_path, _installed_mode(destination))\n",
        "",
    ),
    "existing-mode-not-kept": (
        HELPER,
        "        return stat.S_IMODE(os.stat(destination).st_mode)\n",
        "        os.stat(destination)\n        raise FileNotFoundError\n",
    ),
    "new-file-ignores-the-umask": (HELPER, "        return 0o666 & ~umask\n", "        return 0o644\n"),
}
USER_DATA = {".venv", "log", "dictionary", "workspace", "config.json"}


def _ignore(root: Path):
    def ignore(directory, names):
        skipped = {name for name in names if name == "__pycache__"}
        if Path(directory) == root:
            skipped |= USER_DATA & set(names)
        return skipped
    return ignore


def main() -> int:
    repo = Path(sys.argv[1]).resolve()
    scratch = Path(sys.argv[2]).resolve()
    names = sys.argv[3:] or list(MUTANTS)
    client = scratch / "client"
    if client.exists():
        shutil.rmtree(client)
    shutil.copytree(repo / "client", client, ignore=_ignore(repo / "client"))
    status = 0
    for name in names:
        relative, old, new = MUTANTS[name]
        path = client / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            print(f"{name}: old text found {original.count(old)} times")
            status = 1
            continue
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "unittest", *MODULES],
                cwd=client,
                capture_output=True,
                text=True,
                timeout=600,
            )
        finally:
            path.write_text(original, encoding="utf-8")
        caught = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+)", result.stderr, re.M)))
        if caught:
            print(f"{name}: caught by {' '.join(caught)}")
        else:
            print(f"{name}: SURVIVED")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
PYEOF
```

- [ ] **Step 3: Record the baseline counts, msgids, fixtures and the P2-2 pins.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
(cd $REPO && $PY -I $SP/p12/tools/msgid_scan.py client --save $T/base_msgids.json) | grep -E '^source|^saved' | sed "s#$T/##"
sha256sum tests/fixtures/translation_golden.json tests/fixtures/dictionary_entries_trace.json
grep -rn "KNOWN BUG (P2-2 spec, Q" tests | cut -d: -f1,3- | sed 's/  */ /g'
```

Expected (the P2-5 failure only; 353 msgids; the fixture hashes from Global Constraints; the P2-2 pins: this fix replaces Q1, Q3 and Q7, the others stay):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1114 tests
FAILED (failures=1, skipped=7)
source msgids: 353
saved base_msgids.json
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q8), pinned as it is today, NOT desired: the load error
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q1; data loss), pinned as it is today, NOT desired: the
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q5), pinned as it is today, NOT desired: Cancel has no
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q6), pinned as it is today, NOT desired: the typed entry is discarded.
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q4), pinned as it is today, NOT desired: the other
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q5), pinned as it is today, NOT desired: no confirmation.
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q4), pinned as it is today, NOT desired: the first equal
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q2), pinned as it is today, NOT desired: OK always
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q7), pinned as it is today, NOT desired: a non-OSError
tests/test_dictionary_entries_dialog.py: # KNOWN BUG (P2-2 spec, Q3; data loss), pinned as it is today, NOT desired: the
```

---

### Task 1: `write_text_atomically` (spec migration step 1; D4 and the permission amendment)

**Files:**
- Create: `client/tests/test_atomic_write.py`
- Create: `client/shared/atomic_write.py`

**Interfaces:**
- Produces (used by Task 2): `write_text_atomically(path: Path | str, write: Callable[[TextIO], None], *, encoding: str = "utf-8", newline: str | None = "") -> None`. The directory must exist. On return `path` holds exactly what `write(stream)` wrote; on any exception (also `KeyboardInterrupt`) `path` is unchanged and no temporary file `.<name>.<random>.tmp` is left, unless removing it failed (that error is suppressed; the original exception propagates). On POSIX the installed file has the replaced file's permission bits, or `0o666 & ~umask` for a new file.
- `os.fsync`, `os.chmod` and `os.replace` are called as attributes of `os` at call time, so tests can patch them.

- [ ] **Step 1: Write the failing tests** (A1-A7 from the spec, A8-A9 for the amendment).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_atomic_write.py b/client/tests/test_atomic_write.py
new file mode 100644
index 0000000..665f508
--- /dev/null
+++ b/client/tests/test_atomic_write.py
@@ -0,0 +1,119 @@
+import os
+import stat
+import tempfile
+import unittest
+from pathlib import Path
+from unittest.mock import Mock, patch
+
+import shared.atomic_write as atomic_write
+
+
+def _write_line(stream) -> None:
+    stream.write("a,b\r\n")
+
+
+def _write_then_fail(stream) -> None:
+    stream.write("a,b\r\n")
+    stream.write("\ud800")
+
+
+class WriteTextAtomicallyTest(unittest.TestCase):
+    def setUp(self) -> None:
+        self._tmpdir = tempfile.TemporaryDirectory()
+        self.addCleanup(self._tmpdir.cleanup)
+        self.directory = Path(self._tmpdir.name)
+        self.path = self.directory / "d.csv"
+
+    def listing(self) -> list[str]:
+        return sorted(os.listdir(self.directory))
+
+    def test_replaces_an_existing_file_with_the_written_text(self) -> None:
+        self.path.write_bytes(b"old,bytes\n")
+
+        atomic_write.write_text_atomically(self.path, _write_line)
+
+        self.assertEqual(self.path.read_bytes(), b"a,b\r\n")
+        self.assertEqual(self.listing(), ["d.csv"])
+
+    def test_creates_a_file_that_does_not_exist(self) -> None:
+        atomic_write.write_text_atomically(str(self.path), _write_line)
+
+        self.assertEqual(self.path.read_bytes(), b"a,b\r\n")
+        self.assertEqual(self.listing(), ["d.csv"])
+
+    def test_write_error_keeps_the_original_bytes_and_leaves_no_temporary_file(self) -> None:
+        self.path.write_bytes(b"old,bytes\n")
+
+        with self.assertRaises(UnicodeEncodeError):
+            atomic_write.write_text_atomically(self.path, _write_then_fail)
+
+        self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
+        self.assertEqual(self.listing(), ["d.csv"])
+
+    def test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file(self) -> None:
+        self.path.write_bytes(b"old,bytes\n")
+
+        with patch("os.replace", side_effect=PermissionError(13, "denied")) as replace:
+            with self.assertRaises(PermissionError):
+                atomic_write.write_text_atomically(self.path, _write_line)
+
+        source, destination = replace.call_args.args
+        self.assertEqual(Path(source).parent, self.directory)
+        self.assertRegex(Path(source).name, r"^\.d\.csv\..+\.tmp$")
+        self.assertEqual(Path(destination), self.path)
+        self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
+        self.assertEqual(self.listing(), ["d.csv"])
+
+    def test_interrupt_leaves_no_temporary_file_and_propagates(self) -> None:
+        self.path.write_bytes(b"old,bytes\n")
+
+        def interrupt(stream) -> None:
+            stream.write("a,b\r\n")
+            raise KeyboardInterrupt
+
+        with self.assertRaises(KeyboardInterrupt):
+            atomic_write.write_text_atomically(self.path, interrupt)
+
+        self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
+        self.assertEqual(self.listing(), ["d.csv"])
+
+    def test_failure_without_an_existing_file_creates_nothing(self) -> None:
+        with self.assertRaises(UnicodeEncodeError):
+            atomic_write.write_text_atomically(self.path, _write_then_fail)
+
+        self.assertEqual(self.listing(), [])
+
+    def test_data_is_flushed_to_disk_before_the_replace(self) -> None:
+        calls = Mock()
+
+        with patch("os.fsync", wraps=os.fsync) as fsync, patch("os.replace", wraps=os.replace) as replace:
+            calls.attach_mock(fsync, "fsync")
+            calls.attach_mock(replace, "replace")
+            atomic_write.write_text_atomically(self.path, _write_line)
+
+        self.assertEqual([name for name, _args, _kwargs in calls.mock_calls], ["fsync", "replace"])
+        self.assertEqual(self.path.read_bytes(), b"a,b\r\n")
+
+    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
+    def test_keeps_the_permission_bits_of_an_existing_file(self) -> None:
+        self.path.write_bytes(b"old,bytes\n")
+        os.chmod(self.path, 0o640)
+
+        atomic_write.write_text_atomically(self.path, _write_line)
+
+        self.assertEqual(oct(stat.S_IMODE(os.stat(self.path).st_mode)), oct(0o640))
+        self.assertEqual(self.path.read_bytes(), b"a,b\r\n")
+
+    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
+    def test_a_new_file_gets_the_default_mode_for_the_umask(self) -> None:
+        previous = os.umask(0o002)
+        self.addCleanup(os.umask, previous)
+
+        atomic_write.write_text_atomically(self.path, _write_line)
+
+        self.assertEqual(oct(stat.S_IMODE(os.stat(self.path).st_mode)), oct(0o664))
+        self.assertEqual(self.listing(), ["d.csv"])
+
+
+if __name__ == "__main__":
+    unittest.main()
EOF
```

- [ ] **Step 2: Run them; the module cannot be imported.**

```bash
$PY -m unittest tests.test_atomic_write 2>&1 | $PY $T/tools/brief.py
```

Expected (one loader error, see Spec Corrections 2):

```text
ERROR: test_atomic_write (unittest.loader._FailedTest.test_atomic_write)
ImportError: Failed to import test module: test_atomic_write
ModuleNotFoundError: No module named 'shared.atomic_write'
Ran 1 test
FAILED (errors=1)
```

- [ ] **Step 3: Implement the helper as the spec's D4 describes it** (temporary file in the same directory, path recorded before `write`, `flush` + `fsync`, `os.replace`, clean-up in `finally`).

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/shared/atomic_write.py b/client/shared/atomic_write.py
new file mode 100644
index 0000000..fe5fcc7
--- /dev/null
+++ b/client/shared/atomic_write.py
@@ -0,0 +1,51 @@
+"""Replace a text file without ever leaving it half-written.
+
+``write_text_atomically`` writes to a temporary file ``.<name>.<random>.tmp`` in
+the target's directory, flushes it to disk and installs it with ``os.replace``.
+On return the target holds exactly what was written; on an exception it is
+unchanged (same bytes, or still absent) and the temporary file is removed.
+"""
+
+from __future__ import annotations
+
+import contextlib
+import os
+import tempfile
+from pathlib import Path
+from typing import Callable, TextIO
+
+
+def write_text_atomically(
+    path: Path | str,
+    write: Callable[[TextIO], None],
+    *,
+    encoding: str = "utf-8",
+    newline: str | None = "",
+) -> None:
+    """Write ``path`` through ``write(stream)``; on an error ``path`` is unchanged.
+
+    The directory must exist. No temporary file is left unless removing it fails.
+    """
+    destination = Path(path)
+    temporary_path: Path | None = None
+    installed = False
+    try:
+        with tempfile.NamedTemporaryFile(
+            "w",
+            encoding=encoding,
+            newline=newline,
+            dir=destination.parent,
+            prefix=f".{destination.name}.",
+            suffix=".tmp",
+            delete=False,
+        ) as stream:
+            temporary_path = Path(stream.name)
+            write(stream)
+            stream.flush()
+            os.fsync(stream.fileno())
+        os.replace(temporary_path, destination)
+        installed = True
+    finally:
+        if not installed and temporary_path is not None:
+            with contextlib.suppress(OSError):
+                temporary_path.unlink(missing_ok=True)
EOF
```

- [ ] **Step 4: Run the module; only the two permission tests fail.**

```bash
$PY -m unittest tests.test_atomic_write 2>&1 | $PY $T/tools/brief.py
```

Expected (`NamedTemporaryFile` creates `0o600`; this is the regression the amendment removes):

```text
FAIL: test_a_new_file_gets_the_default_mode_for_the_umask (tests.test_atomic_write.WriteTextAtomicallyTest.test_a_new_file_gets_the_default_mode_for_the_umask)
AssertionError: '0o600' != '0o664'
FAIL: test_keeps_the_permission_bits_of_an_existing_file (tests.test_atomic_write.WriteTextAtomicallyTest.test_keeps_the_permission_bits_of_an_existing_file)
AssertionError: '0o600' != '0o640'
Ran 9 tests
FAILED (failures=2)
```

- [ ] **Step 5: Keep the permission bits (amendment).**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/shared/atomic_write.py b/client/shared/atomic_write.py
index fe5fcc7..f44df41 100644
--- a/client/shared/atomic_write.py
+++ b/client/shared/atomic_write.py
@@ -4,17 +4,31 @@
 the target's directory, flushes it to disk and installs it with ``os.replace``.
 On return the target holds exactly what was written; on an exception it is
 unchanged (same bytes, or still absent) and the temporary file is removed.
+On POSIX the installed file keeps the permission bits of the file it replaces,
+or gets the mode a plain ``open(path, "w")`` would give a new file.
 """
 
 from __future__ import annotations
 
 import contextlib
 import os
+import stat
 import tempfile
 from pathlib import Path
 from typing import Callable, TextIO
 
 
+def _installed_mode(destination: Path) -> int:
+    """The permission bits for ``destination``: kept if it exists, else 0o666 minus the umask."""
+    try:
+        return stat.S_IMODE(os.stat(destination).st_mode)
+    except FileNotFoundError:
+        # Reading the umask means setting it; it is put back at once.
+        umask = os.umask(0)
+        os.umask(umask)
+        return 0o666 & ~umask
+
+
 def write_text_atomically(
     path: Path | str,
     write: Callable[[TextIO], None],
@@ -43,6 +57,8 @@ def write_text_atomically(
             write(stream)
             stream.flush()
             os.fsync(stream.fileno())
+        if os.name == "posix":  # NamedTemporaryFile creates 0o600
+            os.chmod(temporary_path, _installed_mode(destination))
         os.replace(temporary_path, destination)
         installed = True
     finally:
EOF
```

- [ ] **Step 6: Run the module, then the full suite.**

```bash
$PY -m unittest tests.test_atomic_write 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (nothing uses the helper yet; 1114 + 9):

```text
Ran 9 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1123 tests
FAILED (failures=1, skipped=7)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/shared/atomic_write.py client/tests/test_atomic_write.py
git -C $REPO commit -q -F - <<'EOF'
fix: add an atomic text-write helper

write_text_atomically writes through a temporary file in the target's
directory, fsyncs it and installs it with os.replace, so the target is
either fully replaced or left as it was. On POSIX the new file keeps the
replaced file's permission bits (or the umask default for a new file).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
fix: add an atomic text-write helper
```

---

### Task 2: Save dictionary entries atomically (spec migration step 2; D2, D5, D7)

**Files:**
- Modify: `client/tests/test_dictionary_entries.py` (tabs; B9 `test_save_writes_utf8_without_a_bom`, B10 `test_save_failure_leaves_the_existing_file_unchanged`)
- Modify: `client/tests/test_dictionary_entries_dialog.py` (`_listing`; `test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds` updated per D5; G15 `test_replace_failure_shows_the_message_keeps_the_file_and_a_later_ok_succeeds`; `test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file` becomes `test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged`)
- Modify: `client/dictionaries/entries.py` (tabs), `client/dialog.py` (tabs)

**Interfaces:**
- Consumes: `write_text_atomically` (Task 1).
- `save_dictionary_entries(dictionary_path, entries)`: same signature, same bytes (header `text,braille,type`, UTF-8 without BOM, `\r\n`); creates the parent folder as before; on an error the file is unchanged.
- `DictionaryEntriesDialog._on_ok`: `except Exception as exc:` with the unchanged `MessageBox` call and `return`.

- [ ] **Step 1: Write the failing tests and flip the Q3/Q7 pin.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_dictionary_entries.py b/client/tests/test_dictionary_entries.py
index 74d1a8a..3a47f39 100644
--- a/client/tests/test_dictionary_entries.py
+++ b/client/tests/test_dictionary_entries.py
@@ -85,6 +85,35 @@ class DictionaryEntryStorageTest(unittest.TestCase):
 			[{"text": "Alpha", "braille": "\u2801", "type": "UnexpectedType"}],
 		)
 
+	def test_save_writes_utf8_without_a_bom(self) -> None:
+		with tempfile.TemporaryDirectory() as temp_dir:
+			path = Path(temp_dir) / "sample.csv"
+			save_dictionary_entries(path, [DictionaryEntry("Alpha", "\u2801", "General")])
+
+			data = path.read_bytes()
+
+		self.assertEqual(data, b"text,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")
+
+	def test_save_failure_leaves_the_existing_file_unchanged(self) -> None:
+		# Regression record of the P2-2 Q3 data loss (fixed by F-2): the file used to be
+		# truncated before the failing row was written.
+		original = b"text,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\nBeta,\xe2\xa0\x83,General\r\n"
+		with tempfile.TemporaryDirectory() as temp_dir:
+			path = Path(temp_dir) / "sample.csv"
+			path.write_bytes(original)
+
+			with self.assertRaises(UnicodeEncodeError):
+				save_dictionary_entries(
+					path,
+					[DictionaryEntry("Alpha", "\u2801", "General"), DictionaryEntry("\ud800", "\u2803", "General")],
+				)
+
+			data = path.read_bytes()
+			listing = sorted(child.name for child in Path(temp_dir).iterdir())
+
+		self.assertEqual(data, original)
+		self.assertEqual(listing, ["sample.csv"])
+
 
 if __name__ == "__main__":
 	unittest.main()
diff --git a/client/tests/test_dictionary_entries_dialog.py b/client/tests/test_dictionary_entries_dialog.py
index fcb383e..1d46af9 100644
--- a/client/tests/test_dictionary_entries_dialog.py
+++ b/client/tests/test_dictionary_entries_dialog.py
@@ -446,6 +446,10 @@ class _EditorHarness:
         return self.path.read_bytes().decode("utf-8")
 
 
+def _listing(directory: Path) -> list[str]:
+    return sorted(child.name for child in directory.iterdir())
+
+
 def _write_rows(path: Path, rows) -> None:
     with path.open("w", newline="", encoding="utf-8") as stream:
         writer = csv.writer(stream)
@@ -1319,42 +1323,73 @@ class DictionaryEntriesDialogOkTest(_EditorTestCase):
         harness.click("Add")
         harness.path.unlink()
         harness.path.mkdir()
-        try:
-            harness.path.open("w", encoding="utf-8")
-        except OSError as error:
-            expected_error = error  # its text differs between Linux and Windows
-        else:
-            self.fail("opening a directory for writing did not fail")
         harness.take_log()
 
         skipped = harness.press_ok()
 
+        self.assertFalse(skipped)
+        log = harness.take_log()
+        self.assertEqual([[kind, title, flags] for kind, _message, title, flags in log], [["MessageBox", ERROR_TITLE, ERROR_FLAGS]])
+        # Installing the temporary file onto the directory fails; the error text differs
+        # between Linux and Windows, but both name the dictionary last (F-2 spec D5).
+        message = log[0][1]
+        self.assertTrue(message.startswith("\u5132\u5b58\u5931\u6557\uff1a"), message)
+        self.assertTrue(message.endswith(" -> " + repr(str(harness.path))), message)
+        self.assertEqual(harness.message_box_parents, [harness.dialog])
+        self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS])
+        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])
+        self.assertTrue(harness.path.is_dir())
+        harness.path.rmdir()
+        self.assertTrue(harness.press_ok())
+        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")
+
+    def test_replace_failure_shows_the_message_keeps_the_file_and_a_later_ok_succeeds(self) -> None:
+        harness = self.open_editor([ALPHA])
+        original = harness.path.read_bytes()
+        harness.script_entry("Beta", "\u2803")
+        harness.click("Add")
+        harness.take_log()
+
+        with patch("os.replace", side_effect=PermissionError(13, "denied")):
+            skipped = harness.press_ok()
+
         self.assertFalse(skipped)
         self.assertEqual(
             harness.take_log(),
-            [["MessageBox", "\u5132\u5b58\u5931\u6557\uff1a" + str(expected_error), ERROR_TITLE, ERROR_FLAGS]],
+            [["MessageBox", "\u5132\u5b58\u5931\u6557\uff1a[Errno 13] denied", ERROR_TITLE, ERROR_FLAGS]],
         )
-        self.assertEqual(harness.message_box_parents, [harness.dialog])
+        self.assertEqual(harness.path.read_bytes(), original)
+        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])
         self.assertEqual(harness.rows(), [ALPHA_CELLS, BETA_CELLS])
-        harness.path.rmdir()
         self.assertTrue(harness.press_ok())
         self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\nBeta,\u2803,General\r\n")
 
-    def test_non_os_error_from_the_writer_propagates_and_leaves_a_truncated_file(self) -> None:
+    def test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged(self) -> None:
+        # Was the P2-2 Q3/Q7 KNOWN BUG (data loss), fixed by F-2: a non-OSError escaped
+        # the OK handler without a message and the file was left truncated before the
+        # failing row. The same edit is kept as the regression scenario.
         harness = self.open_editor([ALPHA, BETA])
+        original = harness.path.read_bytes()
         harness.script_entry("\ud800", "\u2801")
         harness.click("Edit")
         harness.take_log()
 
-        # KNOWN BUG (P2-2 spec, Q7), pinned as it is today, NOT desired: a non-OSError
-        # escapes the OK handler without a message.
-        with self.assertRaises(UnicodeEncodeError):
-            harness.press_ok()
+        skipped = harness.press_ok()
 
-        self.assertEqual(harness.take_log(), [])
-        # KNOWN BUG (P2-2 spec, Q3; data loss), pinned as it is today, NOT desired: the
-        # file was truncated before the failing row, so Beta is gone from disk.
-        self.assertEqual(harness.saved_csv(), HEADER)
+        self.assertFalse(skipped)
+        self.assertEqual(
+            harness.take_log(),
+            [[
+                "MessageBox",
+                "\u5132\u5b58\u5931\u6557\uff1a'utf-8' codec can't encode character '\\ud800' in position 0: surrogates not allowed",
+                ERROR_TITLE,
+                ERROR_FLAGS,
+            ]],
+        )
+        self.assertEqual(harness.message_box_parents, [harness.dialog])
+        self.assertEqual(harness.path.read_bytes(), original)
+        self.assertEqual(_listing(harness.path.parent), ["dictionary.csv"])
+        self.assertEqual(harness.rows(), [["\ud800", "\u2801", GENERAL], BETA_CELLS])
 
 
 # --- the dialog delegates to the model (P2-2 part C) -------------------------
EOF
```

- [ ] **Step 2: Run the two modules; four tests fail on the old in-place write** (B9 already passes, it pins D2).

```bash
$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
```

Expected (B10: Beta truncated away; the OS-error message has no ` -> '<path>'`; G15: OK succeeds because `os.replace` is never called; the flipped test: the `UnicodeEncodeError` escapes the handler):

```text
ERROR: test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogOkTest.test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged)
UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 0: surrogates not allowed
FAIL: test_save_failure_leaves_the_existing_file_unchanged (tests.test_dictionary_entries.DictionaryEntryStorageTest.test_save_failure_leaves_the_existing_file_unchanged)
AssertionError: b'tex[15 chars]r\nAlpha,\xe2\xa0\x81,General\r\n' != b'tex[15 chars]r\nAlpha,\xe2\xa0\x81,General\r\nBeta,\xe2\xa0\x83,General\r\n'
FAIL: test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogOkTest.test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds)
AssertionError: False is not true : 儲存失敗：[Errno 21] Is a directory: '<tmpdir>/dictionary.csv'
FAIL: test_replace_failure_shows_the_message_keeps_the_file_and_a_later_ok_succeeds (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogOkTest.test_replace_failure_shows_the_message_keeps_the_file_and_a_later_ok
AssertionError: True is not false
Ran 77 tests
FAILED (failures=3, errors=1)
```

- [ ] **Step 3: Write through the helper and catch every `Exception` in OK.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/dialog.py b/client/dialog.py
index e0a2f46..af8fa8d 100644
--- a/client/dialog.py
+++ b/client/dialog.py
@@ -491,7 +491,7 @@ class DictionaryEntriesDialog(ContextManagedDialog, wx.Dialog):
 	def _on_ok(self, event: wx.CommandEvent) -> None:
 		try:
 			self._model.save(self.dictionary_path)
-		except IOError as exc:
+		except Exception as exc:
 			wx.MessageBox(_("Failed to save: {error}").format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
 			return
 		event.Skip()
diff --git a/client/dictionaries/entries.py b/client/dictionaries/entries.py
index 8a65e43..3c25986 100644
--- a/client/dictionaries/entries.py
+++ b/client/dictionaries/entries.py
@@ -5,6 +5,7 @@ from dataclasses import dataclass
 from pathlib import Path
 
 from i18n import _
+from shared.atomic_write import write_text_atomically
 from text.zhuyin import normalize_zhuyin_sequence
 
 
@@ -70,8 +71,10 @@ def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
 
 
 def save_dictionary_entries(dictionary_path: Path, entries: list[DictionaryEntry]) -> None:
+	"""Replace the file atomically; on an error it is unchanged."""
 	dictionary_path.parent.mkdir(parents=True, exist_ok=True)
-	with dictionary_path.open("w", newline="", encoding="utf-8") as fp:
+
+	def _write(fp) -> None:
 		writer = csv.DictWriter(fp, fieldnames=["text", "braille", "type"])
 		writer.writeheader()
 		for entry in entries:
@@ -82,3 +85,5 @@ def save_dictionary_entries(dictionary_path: Path, entries: list[DictionaryEntry
 					"type": entry.entry_type,
 				}
 			)
+
+	write_text_atomically(dictionary_path, _write, encoding="utf-8", newline="")
EOF
```

- [ ] **Step 4: Run the two modules, then the full suite.**

```bash
$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (the golden trace `DictionaryEntriesTraceTest` still passes: same bytes):

```text
Ran 77 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1126 tests
FAILED (failures=1, skipped=7)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/dialog.py client/dictionaries/entries.py client/tests/test_dictionary_entries.py client/tests/test_dictionary_entries_dialog.py
git -C $REPO commit -q -F - <<'EOF'
fix: save dictionary entries atomically

The entries editor's OK wrote the dictionary in place, so a failure part
way (for example an unencodable entry) left a truncated file. It now
writes through write_text_atomically, and the OK handler reports every
Exception with the existing "Failed to save" message instead of letting
non-OSError failures escape silently.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
fix: save dictionary entries atomically
```

---

### Task 3: Read dictionary and data CSVs with `utf-8-sig` (spec migration step 3; D1, D3)

**Files:**
- Modify: `client/tests/test_dictionary_entries.py` (tabs; B8 `test_load_ignores_a_utf8_bom`)
- Modify: `client/tests/test_conversion_text_dictionary_rules.py` (the two "header with BOM" rows become "Bopomofo file is only a BOM" and "dictionary is only a BOM", plus "dictionary with a doubled BOM"; C11 `test_from_paths_ignores_a_utf8_bom_in_both_files`)
- Modify: `client/tests/test_conversion_text_char_maps.py` (D12 `test_translate_mapping_char_ignores_a_utf8_bom`)
- Modify: `client/tests/test_dictionary_manager.py` (E13 `test_import_dictionary_accepts_a_utf8_bom_and_copies_the_bytes`)
- Modify: `client/tests/test_dictionary_management_dialog.py` (tabs; F14 `test_utf8_bom_dictionary_counts_its_entries`)
- Modify: `client/tests/test_dictionary_entries_dialog.py` (`test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header` becomes `test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom`)
- Modify: `client/dictionaries/entries.py` (R1), `client/dictionaries/manager.py` (R2), `client/conversion/text/dictionary_rules.py` (R3, R4, docstring), `client/conversion/text/char_maps.py` (R5)

**Interfaces:** unchanged signatures, messages and read order; only `encoding="utf-8"` becomes `encoding="utf-8-sig"` in the five `open` calls.

- [ ] **Step 1: Write the failing tests and flip the Q1 pin.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_conversion_text_char_maps.py b/client/tests/test_conversion_text_char_maps.py
index 99b581a..a39f984 100644
--- a/client/tests/test_conversion_text_char_maps.py
+++ b/client/tests/test_conversion_text_char_maps.py
@@ -73,6 +73,20 @@ class TranslationCharMapsTest(unittest.TestCase):
             "ac",
         )
 
+    def test_translate_mapping_char_ignores_a_utf8_bom(self) -> None:
+        dictionary_path = self.directory / "mapping.csv"
+        dictionary_path.write_bytes("\ufeffsource,target\r\na,x\r\n".encode("utf-8"))
+
+        self.assertEqual(
+            translate__mapping_char(
+                "abc",
+                dictionary_path=dictionary_path,
+                from_field="source",
+                to_field="target",
+            ),
+            "xbc",
+        )
+
     def test_translate_mapping_char_requires_header_row(self) -> None:
         dictionary_path = self.directory / "mapping.csv"
         dictionary_path.write_text("", encoding="utf-8")
diff --git a/client/tests/test_conversion_text_dictionary_rules.py b/client/tests/test_conversion_text_dictionary_rules.py
index 9beefb5..8576f92 100644
--- a/client/tests/test_conversion_text_dictionary_rules.py
+++ b/client/tests/test_conversion_text_dictionary_rules.py
@@ -175,19 +175,16 @@ def _error_cases() -> tuple[ErrorCase, ...]:
         ErrorCase("Bopomofo file missing", VALID_DICTIONARY, None, FileNotFoundError, None),
         ErrorCase("Bopomofo file empty", VALID_DICTIONARY, b"", ValueError, NO_HEADER),
         ErrorCase("Bopomofo columns missing", VALID_DICTIONARY, b"Bopomofo,Ascii\n", ValueError, BOPOMOFO_COLUMNS),
-        ErrorCase(
-            "Bopomofo header with BOM",
-            VALID_DICTIONARY,
-            "\ufeffBopomofo,Braille\n".encode("utf-8"),
-            ValueError,
-            BOPOMOFO_COLUMNS,
-        ),
+        # F-2: a UTF-8 BOM before the header is ignored now (see
+        # test_from_paths_ignores_a_utf8_bom_in_both_files); a file that is only a BOM has no header.
+        ErrorCase("Bopomofo file is only a BOM", VALID_DICTIONARY, b"\xef\xbb\xbf", ValueError, NO_HEADER),
         ErrorCase("Bopomofo file not UTF-8", VALID_DICTIONARY, b"Bopomofo,Braille\n\xff,x\n", UnicodeDecodeError, None),
         ErrorCase("dictionary empty", b"", VALID_BOPOMOFO, ValueError, NO_HEADER),
         ErrorCase("dictionary columns missing", b"text,braille\n", VALID_BOPOMOFO, ValueError, DICTIONARY_COLUMNS),
+        ErrorCase("dictionary is only a BOM", b"\xef\xbb\xbf", VALID_BOPOMOFO, ValueError, NO_HEADER),
         ErrorCase(
-            "dictionary header with BOM",
-            "\ufefftext,braille,type\n".encode("utf-8"),
+            "dictionary with a doubled BOM",
+            b"\xef\xbb\xbf\xef\xbb\xbftext,braille,type\n",
             VALID_BOPOMOFO,
             ValueError,
             DICTIONARY_COLUMNS,
@@ -508,6 +505,25 @@ class LoadedDictionaryRulesTest(DictionaryFilesTestCase):
                 if case.message is not None:
                     self.assertEqual(str(context.exception), case.message)
 
+    def test_from_paths_ignores_a_utf8_bom_in_both_files(self) -> None:
+        dictionary = DICTIONARY_HEADER + "台,⠞,Braille\n都,ㄉㄨˋ,Bopomofo\n"
+        plain_dictionary = self.tmp_path / "plain_dictionary.csv"
+        plain_bopomofo = self.tmp_path / "plain_bopomofo.csv"
+        plain_dictionary.write_text(dictionary, encoding="utf-8")
+        plain_bopomofo.write_text(TEST_BOPOMOFO, encoding="utf-8")
+        self.dictionary_path.write_text(dictionary, encoding="utf-8-sig")
+        self.bopomofo_path.write_text(TEST_BOPOMOFO, encoding="utf-8-sig")
+        self.assertTrue(self.dictionary_path.read_bytes().startswith(b"\xef\xbb\xbf"))
+        self.assertTrue(self.bopomofo_path.read_bytes().startswith(b"\xef\xbb\xbf"))
+
+        plain = LoadedDictionaryRules.from_paths(plain_dictionary, plain_bopomofo, processing=_identity)
+        with_bom = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)
+
+        self.assertNotEqual(plain, LoadedDictionaryRules())
+        self.assertEqual(with_bom, plain)
+        self.assertEqual(with_bom.apply("台都"), plain.apply("台都"))
+        self.assertNotEqual(plain.apply("台都")["replacement"], "台都")
+
     def test_missing_dictionary_gives_empty_rules_without_opening_the_bopomofo_file(self) -> None:
         with OpenRecorder() as recorder:
             rules = LoadedDictionaryRules.from_paths(self.dictionary_path, self.bopomofo_path, processing=_identity)
diff --git a/client/tests/test_dictionary_entries.py b/client/tests/test_dictionary_entries.py
index 3a47f39..a1d15ae 100644
--- a/client/tests/test_dictionary_entries.py
+++ b/client/tests/test_dictionary_entries.py
@@ -57,6 +57,15 @@ class DictionaryEntryStorageTest(unittest.TestCase):
 
 		self.assertEqual(entries, [DictionaryEntry("Braille", "abc", "Braille")])
 
+	def test_load_ignores_a_utf8_bom(self) -> None:
+		with tempfile.TemporaryDirectory() as temp_dir:
+			path = Path(temp_dir) / "sample.csv"
+			path.write_bytes(b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")
+
+			entries = load_dictionary_entries(path)
+
+		self.assertEqual(entries, [DictionaryEntry("Alpha", "\u2801", "General")])
+
 	def test_save_load_roundtrip(self) -> None:
 		entries = [
 			DictionaryEntry("Alpha", "\u2801", "General"),
diff --git a/client/tests/test_dictionary_entries_dialog.py b/client/tests/test_dictionary_entries_dialog.py
index 1d46af9..c6dcb2b 100644
--- a/client/tests/test_dictionary_entries_dialog.py
+++ b/client/tests/test_dictionary_entries_dialog.py
@@ -824,14 +824,15 @@ class DictionaryEntriesDialogConstructionTest(_EditorTestCase):
 
         self.assertEqual(harness.take_log(), [["Dialog.__init__", TITLE, DIALOG_STYLE]])
 
-    def test_bom_dictionary_opens_empty_and_ok_overwrites_it_with_the_header(self) -> None:
-        # KNOWN BUG (P2-2 spec, Q1; data loss), pinned as it is today, NOT desired: the
-        # BOM makes the header "\ufefftext", every row is skipped, OK writes the header only.
+    def test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom(self) -> None:
+        # Was the P2-2 Q1 KNOWN BUG (data loss), fixed by F-2: the BOM made the header
+        # "\ufefftext", the editor showed no rows and OK wrote the header only.
         harness = self.open_editor(data=b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")
 
-        self.assertEqual(harness.rows(), [])
+        self.assertEqual(harness.rows(), [ALPHA_CELLS])
         self.assertTrue(harness.press_ok())
-        self.assertEqual(harness.saved_csv(), HEADER)
+        self.assertEqual(harness.saved_csv(), HEADER + "Alpha,\u2801,General\r\n")
+        self.assertFalse(harness.path.read_bytes().startswith(b"\xef\xbb\xbf"))
 
     def test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized(self) -> None:
         harness = self.open_editor([ALPHA])
diff --git a/client/tests/test_dictionary_management_dialog.py b/client/tests/test_dictionary_management_dialog.py
index fd6541b..9c0dff7 100644
--- a/client/tests/test_dictionary_management_dialog.py
+++ b/client/tests/test_dictionary_management_dialog.py
@@ -120,6 +120,17 @@ class DictionaryManagementVirtualListTest(unittest.TestCase):
 		self.assertEqual(target._get_item_text(0, 1), "1")
 		self.assertEqual(target.list_ctrl.selected, 0)
 
+	def test_utf8_bom_dictionary_counts_its_entries(self):
+		with tempfile.TemporaryDirectory() as temp_dir:
+			path = Path(temp_dir) / "alpha.csv"
+			path.write_bytes(b"\xef\xbb\xbftext,braille,type\r\nAlpha,\xe2\xa0\x81,General\r\n")
+			target = _make_dialog(temp_dir, ["alpha"])
+
+			target.refresh_dictionaries(["alpha"], "alpha")
+
+		self.assertEqual(target._get_item_text(0, 0), "alpha")
+		self.assertEqual(target._get_item_text(0, 1), "1")
+
 	def test_missing_dictionary_has_zero_entries(self):
 		with tempfile.TemporaryDirectory() as temp_dir:
 			target = _make_dialog(temp_dir, ["missing"])
diff --git a/client/tests/test_dictionary_manager.py b/client/tests/test_dictionary_manager.py
index 3694bac..fee29e9 100644
--- a/client/tests/test_dictionary_manager.py
+++ b/client/tests/test_dictionary_manager.py
@@ -4,6 +4,7 @@ import unittest
 from pathlib import Path
 
 from shared import name_validation
+from dictionaries.entries import DictionaryEntry, load_dictionary_entries
 from dictionaries.manager import (
     DEFAULT_DICTIONARY_NAME,
     DEFAULT_HEADER,
@@ -133,6 +134,17 @@ class DictionaryManagerTest(unittest.TestCase):
         self.assertEqual(imported_path, self.dictionary_dir / "1.1.csv")
         self.assertEqual(imported_path.read_text(encoding="utf-8"), source_path.read_text(encoding="utf-8"))
 
+    def test_import_dictionary_accepts_a_utf8_bom_and_copies_the_bytes(self) -> None:
+        source_path = Path(self._tmpdir.name) / "excel.csv"
+        data = b"\xef\xbb\xbftext,braille,type\r\nterm,\xe2\xa0\x81,General\r\n"
+        source_path.write_bytes(data)
+
+        imported_path = import_dictionary(self.dictionary_dir, source_path, "excel")
+
+        self.assertEqual(imported_path, self.dictionary_dir / "excel.csv")
+        self.assertEqual(imported_path.read_bytes(), data)
+        self.assertEqual(load_dictionary_entries(imported_path), [DictionaryEntry("term", "\u2801", "General")])
+
     def test_import_dictionary_rejects_invalid_header(self) -> None:
         source_path = Path(self._tmpdir.name) / "invalid.csv"
         with source_path.open("w", newline="", encoding="utf-8") as f:
EOF
```

- [ ] **Step 2: Run the six modules; every new BOM test fails on `utf-8`.**

```bash
$PY -m unittest tests.test_dictionary_entries tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps tests.test_dictionary_manager tests.test_dictionary_management_dialog tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
```

Expected (C11, D12 and E13 raise the old column errors; B8, F14 and the Q1 flip see no rows; both table tests fail for the two "only a BOM" rows, which give the column message instead of the header message; the doubled-BOM row passes):

```text
ERROR: test_from_paths_ignores_a_utf8_bom_in_both_files (tests.test_conversion_text_dictionary_rules.LoadedDictionaryRulesTest.test_from_paths_ignores_a_utf8_bom_in_both_files)
ValueError: CSV must contain columns: Bopomofo, Braille
ERROR: test_translate_mapping_char_ignores_a_utf8_bom (tests.test_conversion_text_char_maps.TranslationCharMapsTest.test_translate_mapping_char_ignores_a_utf8_bom)
ValueError: CSV must contain columns: source, target
ERROR: test_import_dictionary_accepts_a_utf8_bom_and_copies_the_bytes (tests.test_dictionary_manager.DictionaryManagerTest.test_import_dictionary_accepts_a_utf8_bom_and_copies_the_bytes)
ValueError: Dictionary CSV must contain text, braille, and type headers.
FAIL: test_load_ignores_a_utf8_bom (tests.test_dictionary_entries.DictionaryEntryStorageTest.test_load_ignores_a_utf8_bom)
AssertionError: Lists differ: [] != [DictionaryEntry(text='Alpha', braille='⠁', entry_type='General')]
FAIL: test_malformed_files_raise_the_recorded_errors (tests.test_conversion_text_dictionary_rules.DictionaryFileSemanticsTest.test_malformed_files_raise_the_recorded_errors) (case='Bopomofo file is only a BOM')
AssertionError: 'CSV must contain columns: Bopomofo, Braille' != 'CSV must contain header row.'
FAIL: test_malformed_files_raise_the_recorded_errors (tests.test_conversion_text_dictionary_rules.DictionaryFileSemanticsTest.test_malformed_files_raise_the_recorded_errors) (case='dictionary is only a BOM')
AssertionError: 'CSV must contain columns: text, braille, type' != 'CSV must contain header row.'
FAIL: test_from_paths_raises_the_recorded_errors (tests.test_conversion_text_dictionary_rules.LoadedDictionaryRulesTest.test_from_paths_raises_the_recorded_errors) (case='Bopomofo file is only a BOM')
AssertionError: 'CSV must contain columns: Bopomofo, Braille' != 'CSV must contain header row.'
FAIL: test_from_paths_raises_the_recorded_errors (tests.test_conversion_text_dictionary_rules.LoadedDictionaryRulesTest.test_from_paths_raises_the_recorded_errors) (case='dictionary is only a BOM')
AssertionError: 'CSV must contain columns: text, braille, type' != 'CSV must contain header row.'
FAIL: test_utf8_bom_dictionary_counts_its_entries (tests.test_dictionary_management_dialog.DictionaryManagementVirtualListTest.test_utf8_bom_dictionary_counts_its_entries)
AssertionError: '0' != '1'
FAIL: test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom (tests.test_dictionary_entries_dialog.DictionaryEntriesDialogConstructionTest.test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_with
AssertionError: Lists differ: [] != [['Alpha', '⠁', '一般']]
Ran 145 tests
FAILED (failures=7, errors=3)
```

- [ ] **Step 3: Switch the five readers to `utf-8-sig`.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/conversion/text/char_maps.py b/client/conversion/text/char_maps.py
index f430718..e1f7a31 100644
--- a/client/conversion/text/char_maps.py
+++ b/client/conversion/text/char_maps.py
@@ -11,7 +11,7 @@ def _load_char_mapping(
     dictionary_path = Path(dictionary_path)
     mapping: dict[int, str | None] = {}
 
-    with dictionary_path.open("r", newline="", encoding="utf-8") as f:
+    with dictionary_path.open("r", newline="", encoding="utf-8-sig") as f:
         reader = csv.DictReader(f)
         if reader.fieldnames is None:
             raise ValueError("CSV must contain header row.")
diff --git a/client/conversion/text/dictionary_rules.py b/client/conversion/text/dictionary_rules.py
index 3659af1..be22f32 100644
--- a/client/conversion/text/dictionary_rules.py
+++ b/client/conversion/text/dictionary_rules.py
@@ -144,12 +144,13 @@ class LoadedDictionaryRules:
         """Read the dictionary and Bopomofo rule files.
 
         A missing dictionary gives empty rules without opening the Bopomofo file.
+        A leading UTF-8 BOM is ignored.
         """
         dictionary_path = Path(dictionary_path)
         if not dictionary_path.exists():
             return cls()
 
-        with Path(bopomofo_path).open("r", newline="", encoding="utf-8") as f_b:
+        with Path(bopomofo_path).open("r", newline="", encoding="utf-8-sig") as f_b:
             reader = csv.DictReader(f_b)
             if reader.fieldnames is None:
                 raise ValueError("CSV must contain header row.")
@@ -165,7 +166,7 @@ class LoadedDictionaryRules:
                 replacements_bopomofo.append((source, target))
         bopomofo_trie = _build_trie(replacements_bopomofo)
 
-        with dictionary_path.open("r", newline="", encoding="utf-8") as f_d:
+        with dictionary_path.open("r", newline="", encoding="utf-8-sig") as f_d:
             reader = csv.DictReader(f_d)
             if reader.fieldnames is None:
                 raise ValueError("CSV must contain header row.")
diff --git a/client/dictionaries/entries.py b/client/dictionaries/entries.py
index 3c25986..3c72497 100644
--- a/client/dictionaries/entries.py
+++ b/client/dictionaries/entries.py
@@ -51,7 +51,7 @@ def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
 		return []
 
 	entries: list[DictionaryEntry] = []
-	with dictionary_path.open("r", newline="", encoding="utf-8") as fp:
+	with dictionary_path.open("r", newline="", encoding="utf-8-sig") as fp:
 		reader = csv.DictReader(fp)
 		for row in reader:
 			entry = DictionaryEntry(
diff --git a/client/dictionaries/manager.py b/client/dictionaries/manager.py
index 12e2dba..bd07d16 100644
--- a/client/dictionaries/manager.py
+++ b/client/dictionaries/manager.py
@@ -40,7 +40,7 @@ def normalize_dictionary_name(name: str) -> str:
 
 def validate_dictionary_csv(path: Path | str) -> None:
     source_path = Path(path)
-    with source_path.open("r", newline="", encoding="utf-8") as fp:
+    with source_path.open("r", newline="", encoding="utf-8-sig") as fp:
         reader = csv.DictReader(fp)
         fieldnames = reader.fieldnames or []
     if any(field not in fieldnames for field in DEFAULT_HEADER):
EOF
```

- [ ] **Step 4: Run the six modules, then the full suite.**

```bash
$PY -m unittest tests.test_dictionary_entries tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps tests.test_dictionary_manager tests.test_dictionary_management_dialog tests.test_dictionary_entries_dialog 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (`translation_golden.json` still matches: its inputs have no BOM):

```text
Ran 145 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1131 tests
FAILED (failures=1, skipped=7)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/conversion/text/char_maps.py client/conversion/text/dictionary_rules.py client/dictionaries/entries.py client/dictionaries/manager.py client/tests/test_conversion_text_char_maps.py client/tests/test_conversion_text_dictionary_rules.py client/tests/test_dictionary_entries.py client/tests/test_dictionary_entries_dialog.py client/tests/test_dictionary_management_dialog.py client/tests/test_dictionary_manager.py
git -C $REPO commit -q -F - <<'EOF'
fix: read dictionary and data CSVs with utf-8-sig

Excel and Notepad save UTF-8 CSV files with a byte order mark, which made
the first header "﻿text": the entries editor showed no rows and OK
overwrote the dictionary with its header, Import rejected the file and
every conversion failed. All five CSV readers now ignore a leading BOM;
files without one read exactly as before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
fix: read dictionary and data CSVs with utf-8-sig
```

---

### Task 4: Acceptance and mutation check (no commit)

- [ ] **Step 1: Snapshot application data, then run criteria 1 and 2** (full suite; 20 shuffle seeds, each with only the P2-5 failure).

```bash
sed 1d $SP/p26impl/snap.sh | bash > $T/app_data_before.txt 2>&1
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
for s in $(seq 1 20); do $PY $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (criterion 1: 1131 tests, `skipped=7`; criterion 2: 20 seeds, each `ran=1131` with the P2-5 failure only):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1131 tests
FAILED (failures=1, skipped=7)
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=1131 failures=1 errors=0 skipped=7
```

- [ ] **Step 2: Criterion 6: application data unchanged by criteria 1-2** (`client/dictionary/` is real user data).

```bash
sed 1d $SP/p26impl/snap.sh | bash > $T/app_data_after.txt 2>&1
diff $T/app_data_before.txt $T/app_data_after.txt && echo "app data unchanged"
```

Expected:

```text
app data unchanged
```

- [ ] **Step 3: Criterion 3: the focused modules pass.**

```bash
$PY -m unittest tests.test_atomic_write tests.test_dictionary_entries tests.test_dictionary_entries_dialog tests.test_dictionary_manager tests.test_dictionary_management_dialog tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps -v 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_atomic_write -v 2>&1 | grep -c " \.\.\. skipped" || true
```

Expected (the second line is the number of skipped helper tests: none on Linux):

```text
Ran 154 tests
OK
0
```

- [ ] **Step 4: Criteria 4 and 5: msgids, locales and fixtures.**

```bash
(cd $REPO && $PY -I $SP/p12/tools/msgid_scan.py client --compare $T/base_msgids.json) | grep -E '^source|SAVED|differs'
git -C $REPO diff main --stat -- client/locales client/tests/fixtures
sha256sum tests/fixtures/translation_golden.json tests/fixtures/dictionary_entries_trace.json
```

Expected (no `--stat` output):

```text
source msgids: 353
SOURCE == SAVED
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
```

- [ ] **Step 5: Criterion 7: the Q1, Q3 and Q7 pins are gone; the Q2, Q4, Q5, Q6 and Q8 pins are unchanged.**

```bash
grep -rn "KNOWN BUG (P2-2 spec, Q[137]" tests || echo "no Q1/Q3/Q7 pins"
$PY - <<'PYEOF'
import ast
import re
import subprocess
from pathlib import Path

PATH = "client/tests/test_dictionary_entries_dialog.py"
MARKER = re.compile(r"KNOWN BUG \(P2-2 spec, Q[24568]")


def pinned(source):
    found = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef):
            segment = ast.get_source_segment(source, node)
            if MARKER.search(segment):
                found[node.name] = segment
    return found


repo = Path("..").resolve()
before = pinned(subprocess.run(["git", "-C", str(repo), "show", f"main:{PATH}"], capture_output=True, text=True, check=True).stdout)
after = pinned((repo / PATH).read_text(encoding="utf-8"))
print(len(before), "pinned tests on main;", "all unchanged" if before == after else "CHANGED")
PYEOF
```

Expected:

```text
no Q1/Q3/Q7 pins
8 pinned tests on main; all unchanged
```

- [ ] **Step 6: Criterion 8: the five readers and their five `utf-8-sig` opens.**

```bash
grep -rn "csv.DictReader" . --include=*.py --exclude-dir=.venv --exclude-dir=tests | LC_ALL=C sort
grep -rn "utf-8-sig" . --include=*.py --exclude-dir=.venv --exclude-dir=tests | LC_ALL=C sort
```

Expected (R5 `char_maps.py`, R4 and R3 `dictionary_rules.py`, R1 `entries.py`, R2 `manager.py`):

```text
./conversion/text/char_maps.py:15:        reader = csv.DictReader(f)
./conversion/text/dictionary_rules.py:154:            reader = csv.DictReader(f_b)
./conversion/text/dictionary_rules.py:170:            reader = csv.DictReader(f_d)
./dictionaries/entries.py:55:		reader = csv.DictReader(fp)
./dictionaries/manager.py:44:        reader = csv.DictReader(fp)
./conversion/text/char_maps.py:14:    with dictionary_path.open("r", newline="", encoding="utf-8-sig") as f:
./conversion/text/dictionary_rules.py:153:        with Path(bopomofo_path).open("r", newline="", encoding="utf-8-sig") as f_b:
./conversion/text/dictionary_rules.py:169:        with dictionary_path.open("r", newline="", encoding="utf-8-sig") as f_d:
./dictionaries/entries.py:54:	with dictionary_path.open("r", newline="", encoding="utf-8-sig") as fp:
./dictionaries/manager.py:43:    with source_path.open("r", newline="", encoding="utf-8-sig") as fp:
```

- [ ] **Step 7: Criterion 9: the files changed against `main`, and the branch.**

```bash
git -C $REPO diff main --name-only
git -C $REPO status --short
git -C $REPO log --format=%s main..HEAD
```

Expected (the plan's own file and the spec pair are the only docs):

```text
client/conversion/text/char_maps.py
client/conversion/text/dictionary_rules.py
client/dialog.py
client/dictionaries/entries.py
client/dictionaries/manager.py
client/shared/atomic_write.py
client/tests/test_atomic_write.py
client/tests/test_conversion_text_char_maps.py
client/tests/test_conversion_text_dictionary_rules.py
client/tests/test_dictionary_entries.py
client/tests/test_dictionary_entries_dialog.py
client/tests/test_dictionary_management_dialog.py
client/tests/test_dictionary_manager.py
docs/superpowers/plans/2026-10-09-f2-dictionary-file-safety.md
docs/superpowers/specs/2026-10-09-f2-dictionary-file-safety-design.md
docs/superpowers/specs/2026-10-09-f2-dictionary-file-safety-design_zh-TW.md
fix: read dictionary and data CSVs with utf-8-sig
fix: save dictionary entries atomically
fix: add an atomic text-write helper
docs: plan dictionary file safety fix
docs: spec dictionary file safety fix
```

- [ ] **Step 8: Criterion 10: mutation check: every reintroduced defect and every broken guarantee is caught.**

```bash
$PY $T/tools/f2_mutants.py $REPO $T/mut; echo "exit=$?"
```

Expected (15 mutants, none survives: `r1`-`r5` reintroduce the BOM defect per reader, `save-direct-open` the truncation, `ok-catches-os-error-only` the escaping exception; the last three are the amendment's):

```text
r1-load-entries-utf8: caught by test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom test_import_dictionary_accepts_a_utf8_bom_and_copies_the_bytes test_load_ignores_a_utf8_bom test_utf8_bom_dictionary_counts_its_entries
r2-validate-import-utf8: caught by test_import_dictionary_accepts_a_utf8_bom_and_copies_the_bytes
r3-rules-dictionary-utf8: caught by test_from_paths_ignores_a_utf8_bom_in_both_files test_from_paths_raises_the_recorded_errors test_malformed_files_raise_the_recorded_errors
r4-rules-bopomofo-utf8: caught by test_from_paths_ignores_a_utf8_bom_in_both_files test_from_paths_raises_the_recorded_errors test_malformed_files_raise_the_recorded_errors
r5-char-maps-utf8: caught by test_translate_mapping_char_ignores_a_utf8_bom
save-direct-open: caught by test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds test_replace_failure_shows_the_message_keeps_the_file_and_a_later_ok_succeeds test_save_failure_leaves_the_existing_file_unchanged test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged
clean-up-only-on-os-error: caught by test_failure_without_an_existing_file_creates_nothing test_interrupt_leaves_no_temporary_file_and_propagates test_save_failure_leaves_the_existing_file_unchanged test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged test_write_error_keeps_the_original_bytes_and_leaves_no_temporary_file
temporary-path-recorded-after-write: caught by test_failure_without_an_existing_file_creates_nothing test_interrupt_leaves_no_temporary_file_and_propagates test_save_failure_leaves_the_existing_file_unchanged test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged test_write_error_keeps_the_original_bytes_and_leaves_no_temporary_file
no-fsync: caught by test_data_is_flushed_to_disk_before_the_replace
temporary-file-in-system-temp: caught by test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file
save-writes-a-bom: caught by test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom test_identical_rows_delete_removes_the_first_equal_row test_identical_rows_edit_replaces_the_selected_row_but_cannot_keep_its_text test_missing_parent_directory_is_created test_ok_saves_the_full_list_in_order_and_closes test_os_error_shows_the_message_keeps_the_edits_and_a_later_ok_succeeds test_replace_failure_shows_the_message_keeps_the_file_and_a_later_ok_succeeds test_replay_matches_every_recorded_step test_save_preserves_entry_type_value test_save_writes_all_entries_not_only_filtered_entries test_save_writes_utf8_without_a_bom test_unchanged_dictionary_is_rewritten_in_normalized_form
ok-catches-os-error-only: caught by test_unencodable_entry_shows_the_message_and_leaves_the_file_unchanged
permission-bits-not-set: caught by test_a_new_file_gets_the_default_mode_for_the_umask test_keeps_the_permission_bits_of_an_existing_file
existing-mode-not-kept: caught by test_keeps_the_permission_bits_of_an_existing_file
new-file-ignores-the-umask: caught by test_a_new_file_gets_the_default_mode_for_the_umask
exit=0
```

## Risks (additions to the spec's)

- **Umask read** (low, Spec Corrections 1). `os.umask` is process-wide; for the two adjacent calls in `_installed_mode` it is `0`. Only when OK saves a dictionary that does not exist yet, only on POSIX. A file another thread creates in that instant would get umask `0`.
- **Read-only dictionary on POSIX** (low, Spec Corrections 1). OK now replaces a `0444` dictionary in a writable folder and keeps `0444`; before, OK failed with `PermissionError`.
- The spec's "File metadata" risk is narrowed: the POSIX mode is kept; ownership, ACLs and extended attributes are not; on Windows the file takes the folder's inherited ACL and default attributes, as the spec says.

## Windows Verification Debt (cannot run here)

- `cd client && python -m unittest tests.test_atomic_write tests.test_dictionary_entries_dialog tests.test_dictionary_entries -v` on Windows: A8 and A9 report `skipped` (POSIX only); the OS-error test now fails in `os.replace` with `PermissionError [WinError 5]` and its message must still end with ` -> '<path>'`; A4's temporary path has the `.d.csv.<random>.tmp` form in the test folder.
- Packaged build, by hand: save a dictionary from Excel as "CSV UTF-8" and from Notepad (UTF-8 with BOM); Import it; Dictionary Management shows its entry count; the editor shows its rows; OK keeps them (and removes the BOM); a conversion uses them.
- Open a dictionary in Excel (which locks it), press OK in the editor: the `儲存失敗：` message appears, the edits stay, the file is unchanged; close Excel, OK again succeeds. No `.default.csv.*.tmp` remains in the dictionary folder.
- With real-time antivirus on, edit and OK a dictionary ten times in a row; record any transient failure (spec D8).
- Mark a dictionary read-only in Explorer, press OK: the error message appears, no `.tmp` remains (Spec Corrections 1: no chmod on Windows).
- No menu, dialog or string changes: no screenshots, no `generate-pot.bat` run.

## Out of Scope / Follow-ups (from the spec)

- P2-2 Q2 (OK rewrites an unchanged dictionary in normalized form), Q4-Q6, Q8: unchanged, still pinned.
- `manager.py` writers (D6): create/ensure-default header writes, import/export `shutil.copyfile`: route through the helper (and a binary variant for the copies).
- `save_preprocessing_script` leaks its `.tmp` file when the write fails; migrate it to `write_text_atomically` (it would then also keep the script's permission bits).
- Writing a BOM on Export (or on every save) so Excel opens UTF-8 dictionaries correctly: UX decision.
- Other text inputs that a BOM breaks: the preprocessing script and imported `.txt` documents.
