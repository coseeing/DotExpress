# Workspace Case Collisions (F-1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the two priority-1 data-loss defects of the document workspace: a case-only Rename (`Alpha` to `alpha`) keeps the document on every file system and leaves exactly `alpha.dep` with `alpha.*` members, and Add or Rename to a case variant of another document (`Alpha` while `alpha` exists) is refused with the existing duplicate message and re-prompt. No new user-facing string (msgids 353, same set); every other flow is unchanged, including regular renames and known defect 3.

**Architecture:** Four commits in the spec's migration order. Task 1 adds `PackageFiles` (five injectable file primitives) and `move_document_package` (stage, move aside, install, clean up; D4) to `documents/workspace.py`, nothing calls it yet. Task 2 adds a case-insensitive, case-preserving file model for tests (`tests/case_insensitive_package_files.py`) and its self-tests, which reproduce both old failures and run the new move on the model. Task 3 casefolds `session.document_name_exists` (exclusion stays exact; D1) and replaces the defect-2 `KNOWN BUG` test. Task 4 gives `DocumentWorkspaceService` an optional `package_files` keyword and routes only case-only renames through `move_document_package` (D3, D5, D6), replacing the defect-1 `KNOWN BUG` test. Every task is red first; Task 5 runs the acceptance criteria and a 12-mutant check.

**Tech Stack:** Python 3 standard library (`os.replace`, `tempfile.NamedTemporaryFile`, `zipfile`, `contextlib.suppress`, `unittest`). wxPython is not installed; the GUI flow tests keep their `tests/wx_stub.py` scope.

**Spec:** `docs/superpowers/specs/2026-10-09-f1-workspace-case-collisions-design.md` (authoritative, commit `f3300f1`). Corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `fix/f1-workspace-case-collisions`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (9, nothing else): production `client/documents/session.py` (tabs), `client/documents/workspace.py` (4 spaces), `client/documents/workspace_service.py` (4 spaces); tests `client/tests/case_insensitive_package_files.py` (new, not a test module), `client/tests/test_case_insensitive_package_files.py` (new), `client/tests/test_document_workspace.py`, `client/tests/test_document_controller.py`, `client/tests/test_workspace_service.py`, `client/tests/test_gui_document_flows.py` (all 4 spaces). Never touch `client/gui.py`, `client/documents/controller.py`, `client/locales/` (`.po`/`.mo`), `client/tests/fixtures/`, `client/tests/wx_stub.py` or the spec.
- The patches below carry the exact characters (the `session.py` line uses a tab). Run every block as it is, do not retype. If `git apply` refuses a patch, stop and re-check the previous step; do not hand-merge.
- No user-facing string changes and no msgid changes: `source msgids: 353`, compared with the Task 0 snapshot in Task 5 (`SOURCE == SAVED`).
- Fixtures are never touched: `client/tests/fixtures/translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `client/tests/fixtures/dictionary_entries_trace.json` sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`.
- Known defect 3 stays pinned: the two `KNOWN BUG (P1-3 spec, known defect 3)` tests (`test_workspace_service.py`, `test_gui_document_flows.py`) are not edited; regular renames keep today's code path byte for byte (D6).
- P2-5 is on hold: the one known failure `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math` stays failing with the same assertion after every task; do not touch `translate.py`.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run. Unittest output is condensed by `$T/tools/brief.py` (FAIL/ERROR headers, exception lines cut to 220 characters, `Ran` without timing, final status), so the blocks are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/f1impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`.
- Baseline (re-verified at `f3300f1`, the spec commit; code identical to `c8ecf66` = `main`): `$PY -m unittest discover -s tests` gives `Ran 1095 tests`, `FAILED (failures=1, skipped=9)` (7 Windows-only liblouis skips and the two `..._on_case_insensitive_file_system_...` tests, skipped on Linux).

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: on Linux, part of migration step 4 cannot be red for the defect itself.** The spec says step 4's tests are "red first". On a case-sensitive file system today's write-then-unlink rename is correct, so the merged `test_case_only_rename_keeps_the_document` and E16 `test_case_only_rename_moves_the_package_and_updates_the_controller` already pass on Linux before the fix; they are red only on Windows and macOS (Windows debt). E17 `test_case_only_rename_on_a_case_insensitive_file_model` and F20 `test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document` fail before the fix only because `package_files` does not exist yet (`TypeError`): today's rename path never calls the injected file operations, so the model cannot reproduce defect 1 through the service or the frame (D6 keeps that path byte for byte). Task 4 therefore goes red in two stages: all four injecting tests error with `TypeError`; after adding only the constructor parameter (Step 3), E18 `test_case_only_rename_install_failure_propagates_and_keeps_state` still fails with `OSError not raised`, which proves that case-only renames do not use the safe sequence yet. The old data loss itself is recorded on the model by B2 `test_the_old_rename_sequence_deletes_a_case_only_renamed_package`. The mutation check (Task 5) shows the consequence: on Linux, deleting the case-only branch is caught by E18 alone (on Windows also by the merged GUI test); putting the old write-then-unlink sequence into the branch is caught by E17, F20 and E18.
2. **Fault injectors and the model compare names as strings.** On Windows, `pathlib` equality ignores case (`PureWindowsPath("Alpha.dep") == PureWindowsPath("alpha.dep")`), and `Path.exists()` finds a case variant. An injector written as `destination == ws / "alpha.dep"` would also fail the restore to `Alpha.dep`, and the install-failure tests would fail on Windows. So the injectors match `path.name` strings, and the model resolves names from the directory listing (exact name first, then a casefold match) instead of `exists()`, which makes it behave the same on a case-insensitive host (refines spec Test Plan A).
3. **C 9, 11, 12, 13 use a delegating wrapper, not a subclass.** `_FailingPackageFiles` in `test_document_workspace.py` wraps `workspace.PackageFiles()` (looked up at call time) so that the module still imports before Task 1's implementation exists and each new test fails on its own (`AttributeError`), instead of the whole module failing to import. D5 allows any object with the five methods. `test_workspace_service.py` (Task 4, after `PackageFiles` exists) uses a subclass, `_FailingInstallPackageFiles`.
4. **B3 also exercises `replace_keeps_existing_spelling`.** D4 never replaces onto another entry's case variant, so B4 passes the same with either flag value and the flag itself would be untested. B3 (`test_replace_resolves_case_variants`) adds a second case per flag value: replacing `beta.dep` onto `ALPHA.dep` while `alpha.dep` exists gives `alpha.dep` (flag true) or `ALPHA.dep` (flag false), holding beta's bytes. Test count unchanged.
5. **Test names.** The spec numbers tests; the names chosen here are: C5 `test_case_only_move_leaves_only_the_new_spelling`, C6 `test_move_to_a_different_name`, C7 `test_missing_old_package_and_directory_writes_the_new_package`, C8 `test_pending_braille_keeps_its_metadata`, C9 `test_staging_write_failure_keeps_the_old_package`, C10 `test_staging_error_that_is_not_an_os_error_keeps_the_old_package`, C11 `test_move_aside_failure_keeps_the_old_package`, C12 `test_install_failure_puts_the_old_package_back`, C13 `test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores`, C14 `test_temporary_path_creates_the_directory_and_is_not_a_package` (class `MoveDocumentPackageTest`); B1 `test_writing_a_case_variant_rewrites_the_existing_entry_and_keeps_its_spelling`, B2 as above, B3 as above, B4 `test_move_document_package_keeps_a_case_only_renamed_package`; D15 `test_document_name_exists_ignores_case_and_honours_exact_exclude`; E16-E18 as above, E19 `test_regular_rename_does_not_use_package_files`; F21 `test_rename_to_a_case_variant_of_another_document_is_refused`. E16 and E17 also keep a second document (`beta`) and check it is untouched.
6. **Counts.** Same total as the spec, 1113; the per-commit counts are in Expected Counts.

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `f3300f1` (`$SP/f1plan/dry`, never the repo), one commit per task; after Task 4 the full suite, the 20 shuffle seeds, the msgid scan, the fixtures, the app-data snapshot, every acceptance criterion and the 12 mutants passed. The patches in this plan are `git diff`s of that clone, split into each task's test step and production step (Task 4's production step in two parts). Then this file's blocks were run in order on fresh clones (`$SP/f1plan/replay*`, each with a stand-in plan commit and a local `main` at `c8ecf66`) by a harness that runs every `bash` block from `client/` and compares each "Expected" block with the real output: all 4 commits applied, every expected block matched byte for byte, and the resulting tree is identical to the dry clone's. Final sha256: `client/documents/session.py` `bcfb3003777c01020900cf5a1560891ae84f835ed28c3d711cb18ef7ca73f056`, `client/documents/workspace.py` `8d0fefc66a3fdf155c4d879a4d2e3ed36f3adfa37f8b4a4a66b9c3ac7e280268`, `client/documents/workspace_service.py` `b1719c16d226a82a3594fcb5dd47689ef9be1eb6fd1cea468eb7c3d85ee71ae7`, `client/tests/case_insensitive_package_files.py` `111597f97e560101533020772b8fec18c363082b0ba389dcea0912561c69ad58`. Windows-only behavior was not run; see Windows Verification Debt.

## Review Focus

Inputs and failure modes the spec implies that a user is most likely to meet; each is pinned by a test in the task that owns the code.

1. **A package locked by another program on Windows during a case-only rename** (sharing violation on the move-aside or the install): the error box appears, `Alpha` stays in the list, `Alpha.dep` keeps its bytes and spelling. Pinned by C11 `test_move_aside_failure_keeps_the_old_package`, C12 `test_install_failure_puts_the_old_package_back` (Task 1) and E18 `test_case_only_rename_install_failure_propagates_and_keeps_state` (Task 4); a real lock is Windows debt.
2. **Leftover `.tmp` files** (a crash between the steps, a failed clean-up) must never appear as documents or in the startup invalid-files dialog. Pinned by C13 `test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores` (`load_workspace_documents` returns only `alpha`, no invalid path) and C14 (the name ends in `.tmp`, so `*.dep` never matches), Task 1.
3. **A legacy workspace that already holds `Alpha` and `alpha`** (created on Linux): it still loads; renaming either one to a third spelling is refused. Pinned by D15's `legacy` assertion (Task 3); mutant `exclusion-ignores-case` shows the exclusion must stay exact.
4. **Case-only rename of the open, selected document that has a dual-view result**: the open and selected names, the cache key and the window title follow the new spelling. Pinned by E16/E17 (`_state` includes the dual-view key) and the merged GUI test's title event (Task 4).
5. **A pending-braille document (never converted) renamed by case only** keeps its pending state (`alpha.meta.json`) and loads with `braille=None`. Pinned by C8 `test_pending_braille_keeps_its_metadata` (Task 1); the service passes `source.braille` unchanged.

## File Map

- Task 1: `client/tests/test_document_workspace.py` (`_FailingPackageFiles`, `MoveDocumentPackageTest`, 10 tests), then `client/documents/workspace.py` (`PackageFiles`, `move_document_package`).
- Task 2: create `client/tests/test_case_insensitive_package_files.py` (4 tests), then create `client/tests/case_insensitive_package_files.py` (`CaseInsensitivePackageFiles`).
- Task 3: `client/tests/test_document_controller.py` (D15 flipped), `client/tests/test_gui_document_flows.py` (Add merge, F21, `_duplicate_name_events`), then `client/documents/session.py`.
- Task 4: `client/tests/test_workspace_service.py` (E16-E19, `_service(package_files=...)`), `client/tests/test_gui_document_flows.py` (rename merge, F20, `_rename_alpha_case_only`, `_skip_unless_case_sensitive` removed), then `client/documents/workspace_service.py` in two parts (constructor parameter; case-only branch and module docstring).

## Expected Counts

| After task | tests added | tests removed | `Ran` | final line |
| --- | --- | --- | --- | --- |
| baseline | - | - | 1095 | `FAILED (failures=1, skipped=9)` |
| 1 move helper | 10 (C5-C14) | 0 | 1105 | `FAILED (failures=1, skipped=9)` |
| 2 file model | 4 (B1-B4) | 0 | 1109 | `FAILED (failures=1, skipped=9)` |
| 3 casefold check | 2 (Add merge, F21); D15 renamed in place | 2 (both Add case-variant tests, one of them skipped on Linux) | 1109 | `FAILED (failures=1, skipped=8)` |
| 4 case-only rename | 6 (E16-E19, rename merge, F20) | 2 (both case-only rename tests, one of them skipped on Linux) | 1113 | `FAILED (failures=1, skipped=7)` |

The one failure in every row is the P2-5 case. The 7 remaining skips are the Windows-only liblouis tests.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0, outside the repo:

- `brief.py`: condenses unittest output (see Global Constraints).
- `f1_mutants.py <repo_dir> <scratch_dir> [mutant ...]`: copies `client/` (without `.venv`, `__pycache__`, `log`) to `<scratch_dir>/client`, then for each of 12 mutants edits one production file of the copy, runs the five F-1 test modules there, prints which tests caught it and restores the file. The repo is never changed. Matches the code after Task 4.
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
docs: plan workspace case collision fix
fix/f1-workspace-case-collisions
```

- [ ] **Step 2: Create the throwaway tools.**

```bash
mkdir -p $T/tools
cat > $T/tools/brief.py <<'PYEOF'
"""Condense unittest output read from stdin (throwaway).

Keeps the FAIL/ERROR headers, exception lines (cut to 220 characters), the "Ran"
line without its timing and the final OK/FAILED line, so outputs can be compared.
"""
import re
import sys

for line in sys.stdin:
    line = line.rstrip("\n")
    if re.match(r"(FAIL|ERROR): ", line) or re.match(r"[A-Za-z_.]*(Error|Exception): ", line):
        print(line[:220])
    elif line.startswith("Ran "):
        print(re.sub(r" in [0-9.]+s$", "", line))
    elif line.startswith(("OK", "FAILED")):
        print(line)
PYEOF
cat > $T/tools/f1_mutants.py <<'PYEOF'
"""Run the F-1 tests against deliberately broken code (throwaway).

Usage: python f1_mutants.py <repo_dir> <scratch_dir> [mutant ...]
Copies <repo_dir>/client (without .venv, __pycache__, log) to <scratch_dir>/client (fresh
each run), then for each mutant edits one file of the copy, runs the five F-1 test modules
there and restores the file. <repo_dir> is never changed. Matches the code after Task 4.
Prints "<mutant>: caught by <test method> ..." or "<mutant>: SURVIVED"; exit status 1 when
a mutant survives or its old text is not found exactly once.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

MODULES = [
    "tests.test_case_insensitive_package_files",
    "tests.test_document_workspace",
    "tests.test_document_controller",
    "tests.test_workspace_service",
    "tests.test_gui_document_flows",
]
WS = "documents/workspace.py"
SERVICE = "documents/workspace_service.py"
SESSION = "documents/session.py"
CASE_ONLY_CALL = """            move_document_package(
                self.package_path(source_name),
                self.package_path(new_name),
                Document(new_name, source.text, source.braille),
                files=self._package_files,
            )
"""
OLD_SEQUENCE_THROUGH_FILES = """            self._package_files.write(self.package_path(new_name), Document(new_name, source.text, source.braille))
            if self._package_files.exists(self.package_path(source_name)):
                self._package_files.remove(self.package_path(source_name))
"""
MOVE_ASIDE_HANDLER = """    except BaseException:
        with suppress(OSError):
            files.remove(staged_path)
        if aside_path is not None:
            with suppress(OSError):
                files.remove(aside_path)
        raise
"""
MUTANTS = {
    # Defect 1 (P1-3 known defect 1) reintroduced.
    "defect1-case-only-branch-removed": (SERVICE, "if source_name.casefold() == new_name.casefold():", "if False:"),
    "defect1-old-sequence-in-case-only-branch": (SERVICE, CASE_ONLY_CALL, OLD_SEQUENCE_THROUGH_FILES),
    "move-without-move-aside": (WS, "        if files.exists(old_path):\n", "        if False:\n"),
    # Defect 2 (P1-3 known defect 2) reintroduced.
    "defect2-exact-duplicate-check": (SESSION, "document.name.casefold() == folded_name", "document.name == name"),
    "exclusion-ignores-case": (
        SESSION,
        "document.name != exclude_name",
        "(exclude_name is None or document.name.casefold() != exclude_name.casefold())",
    ),
    # The other guarantees of the new sequence and its routing.
    "install-failure-not-restored": (
        WS,
        "            with suppress(OSError):\n                files.replace(aside_path, old_path)\n",
        "            pass\n",
    ),
    "clean-up-failure-raises": (
        WS,
        "    if aside_path is not None:\n        with suppress(OSError):\n            files.remove(aside_path)\n",
        "    if aside_path is not None:\n        files.remove(aside_path)\n",
    ),
    "staging-cleanup-only-on-os-error": (
        WS,
        "        files.write(staged_path, document)\n    except BaseException:\n",
        "        files.write(staged_path, document)\n    except OSError:\n",
    ),
    "move-aside-failure-leaks-temporary-files": (WS, MOVE_ASIDE_HANDLER, "    except BaseException:\n        raise\n"),
    "temporary-file-named-dep": (WS, 'suffix=".tmp"', 'suffix=".dep"'),
    "temporary-directory-not-created": (WS, "        directory.mkdir(parents=True, exist_ok=True)\n", ""),
    "regular-renames-use-the-move": (SERVICE, "if source_name.casefold() == new_name.casefold():", "if True:"),
}


def main() -> int:
    repo = Path(sys.argv[1]).resolve()
    scratch = Path(sys.argv[2]).resolve()
    names = sys.argv[3:] or list(MUTANTS)
    client = scratch / "client"
    if client.exists():
        shutil.rmtree(client)
    shutil.copytree(repo / "client", client, ignore=shutil.ignore_patterns(".venv", "__pycache__", "log"))
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

- [ ] **Step 3: Record the baseline counts, msgids and fixtures.**

```bash
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
(cd $REPO && $PY -I $SP/p12/tools/msgid_scan.py client --save $T/base_msgids.json) | grep -E '^source|^saved' | sed "s#$T/##"
sha256sum tests/fixtures/translation_golden.json tests/fixtures/dictionary_entries_trace.json
grep -rn "KNOWN BUG (P1-3 spec, known defect" tests | cut -d: -f1,3- | sed 's/  */ /g'
```

Expected (the P2-5 failure only; 353 msgids; the fixture hashes from Global Constraints; the P1-3 known-defect pins: this fix replaces defects 1 and 2, the two defect-3 pins and defect 4 stay):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1095 tests
FAILED (failures=1, skipped=9)
source msgids: 353
saved base_msgids.json
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf  tests/fixtures/dictionary_entries_trace.json
tests/test_gui_document_flows.py: # KNOWN BUG (P1-3 spec, known defect 3), pinned as it is today, NOT desired
tests/test_gui_document_flows.py: # KNOWN BUG (P1-3 spec, known defect 1; data loss), pinned as it is today, NOT
tests/test_gui_document_flows.py: # KNOWN BUG (P1-3 spec, known defect 2; data loss), pinned as it is today, NOT
tests/test_gui_document_flows.py: # KNOWN BUG (P1-3 spec, known defect 4), pinned as it is today, NOT desired
tests/test_workspace_service.py: # KNOWN BUG (P1-3 spec, known defect 3), pinned as it is today, NOT desired
```

---

### Task 1: `PackageFiles` and `move_document_package` (spec migration step 1; D4, D5)

**Files:**
- Modify: `client/tests/test_document_workspace.py` (new import `zipfile`; new `_FailingPackageFiles` and `MoveDocumentPackageTest` after `DocumentWorkspaceTest`)
- Modify: `client/documents/workspace.py` (imports `contextlib.suppress`, `os`, `tempfile`; `PackageFiles` and `move_document_package` after `save_document_package`)

**Interfaces:**
- Consumes: `save_document_package(path, document)`, `load_document_package`, `load_workspace_documents` (unchanged).
- Produces (used by Tasks 2 and 4):
  - `class PackageFiles` with `exists(path) -> bool`, `write(path, document) -> None`, `replace(source, destination) -> None`, `remove(path) -> None` (missing is fine), `temporary_path(directory, name: str) -> Path` (creates `directory`, returns a new empty file `.<name>.<random>.tmp`).
  - `move_document_package(old_path: Path, new_path: Path, document: Document, *, files: PackageFiles) -> None`: on return the package exists only at `new_path` (exact spelling) and holds `document`; on an exception the old package is back at `old_path` with its spelling and bytes and no temporary file is left (unless the restore itself fails); a clean-up failure after the install is ignored.

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_document_workspace.py b/client/tests/test_document_workspace.py
index 5dde7b5..2231e35 100644
--- a/client/tests/test_document_workspace.py
+++ b/client/tests/test_document_workspace.py
@@ -1,5 +1,6 @@
 import tempfile
 import unittest
+import zipfile
 from pathlib import Path
 
 import documents.workspace as workspace
@@ -314,5 +315,162 @@ class DocumentWorkspaceTest(unittest.TestCase):
         self.assertEqual([document.name for document in documents], ["alpha", "Beta"])
         self.assertEqual(invalid_paths, [self.workspace_dir / "bad.dep"])
 
+
+class _FailingPackageFiles:
+    """The real ``PackageFiles``, except that ``operation`` raises ``OSError`` when ``when(*paths)`` is true.
+
+    Predicates compare ``path.name`` strings: ``Path`` equality ignores case on Windows.
+    """
+
+    def __init__(self, operation: str, when=lambda *paths: True) -> None:
+        self._files = workspace.PackageFiles()
+        self._operation = operation
+        self._when = when
+
+    def _check(self, operation: str, *paths) -> None:
+        if operation == self._operation and self._when(*(Path(path) for path in paths)):
+            raise OSError(f"injected {operation} failure")
+
+    def exists(self, path) -> bool:
+        return self._files.exists(path)
+
+    def write(self, path, document) -> None:
+        self._check("write", path)
+        self._files.write(path, document)
+
+    def replace(self, source, destination) -> None:
+        self._check("replace", source, destination)
+        self._files.replace(source, destination)
+
+    def remove(self, path) -> None:
+        self._check("remove", path)
+        self._files.remove(path)
+
+    def temporary_path(self, directory, name) -> Path:
+        return self._files.temporary_path(directory, name)
+
+
+class MoveDocumentPackageTest(unittest.TestCase):
+    """``move_document_package`` on the real file system (F-1, D4)."""
+
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.workspace_dir = Path(temp_dir.name) / "workspace"
+
+    def _path(self, name: str) -> Path:
+        return self.workspace_dir / f"{name}.dep"
+
+    def _listing(self) -> list[str]:
+        return sorted(path.name for path in self.workspace_dir.iterdir())
+
+    def _members(self, name: str) -> list[str]:
+        with zipfile.ZipFile(self._path(name)) as archive:
+            return sorted(archive.namelist())
+
+    def _write_alpha(self, braille: str | None = "1") -> bytes:
+        save_document_package(self._path("Alpha"), Document("Alpha", "a", braille))
+        return self._path("Alpha").read_bytes()
+
+    def _move(self, old_name: str, document: Document, files=None) -> None:
+        workspace.move_document_package(
+            self._path(old_name),
+            self._path(document.name),
+            document,
+            files=workspace.PackageFiles() if files is None else files,
+        )
+
+    def test_case_only_move_leaves_only_the_new_spelling(self) -> None:
+        self._write_alpha()
+
+        self._move("Alpha", Document("alpha", "a", "1"))
+
+        self.assertEqual(self._listing(), ["alpha.dep"])
+        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
+        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", "1"))
+
+    def test_move_to_a_different_name(self) -> None:
+        save_document_package(self._path("alpha"), Document("alpha", "a", "1"))
+
+        self._move("alpha", Document("gamma", "a", "1"))
+
+        self.assertEqual(self._listing(), ["gamma.dep"])
+        self.assertEqual(load_document_package(self._path("gamma")), Document("gamma", "a", "1"))
+
+    def test_missing_old_package_and_directory_writes_the_new_package(self) -> None:
+        self._move("Alpha", Document("alpha", "a", "1"))
+
+        self.assertEqual(self._listing(), ["alpha.dep"])
+        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", "1"))
+
+    def test_pending_braille_keeps_its_metadata(self) -> None:
+        self._write_alpha(braille=None)
+
+        self._move("Alpha", Document("alpha", "a", None))
+
+        self.assertEqual(self._listing(), ["alpha.dep"])
+        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.meta.json", "alpha.txt"])
+        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", None))
+
+    def test_staging_write_failure_keeps_the_old_package(self) -> None:
+        before = self._write_alpha()
+
+        with self.assertRaises(OSError):
+            self._move("Alpha", Document("alpha", "a", "1"), _FailingPackageFiles("write"))
+
+        self.assertEqual(self._listing(), ["Alpha.dep"])
+        self.assertEqual(self._path("Alpha").read_bytes(), before)
+
+    def test_staging_error_that_is_not_an_os_error_keeps_the_old_package(self) -> None:
+        before = self._write_alpha()
+
+        with self.assertRaises(UnicodeEncodeError):
+            self._move("Alpha", Document("alpha", "\ud800", "1"))
+
+        self.assertEqual(self._listing(), ["Alpha.dep"])
+        self.assertEqual(self._path("Alpha").read_bytes(), before)
+
+    def test_move_aside_failure_keeps_the_old_package(self) -> None:
+        before = self._write_alpha()
+        files = _FailingPackageFiles("replace", when=lambda source, destination: source.name == "Alpha.dep")
+
+        with self.assertRaises(OSError):
+            self._move("Alpha", Document("alpha", "a", "1"), files)
+
+        self.assertEqual(self._listing(), ["Alpha.dep"])
+        self.assertEqual(self._path("Alpha").read_bytes(), before)
+
+    def test_install_failure_puts_the_old_package_back(self) -> None:
+        before = self._write_alpha()
+        files = _FailingPackageFiles("replace", when=lambda source, destination: destination.name == "alpha.dep")
+
+        with self.assertRaises(OSError):
+            self._move("Alpha", Document("alpha", "a", "1"), files)
+
+        self.assertEqual(self._listing(), ["Alpha.dep"])
+        self.assertEqual(self._path("Alpha").read_bytes(), before)
+
+    def test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores(self) -> None:
+        self._write_alpha()
+
+        self._move("Alpha", Document("alpha", "a", "1"), _FailingPackageFiles("remove"))
+
+        listing = self._listing()
+        self.assertEqual([name for name in listing if not name.endswith(".tmp")], ["alpha.dep"])
+        leftovers = [name for name in listing if name.endswith(".tmp")]
+        self.assertEqual(len(leftovers), 1)
+        self.assertTrue(leftovers[0].startswith(".Alpha.dep."), leftovers)
+        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", "1"))
+        self.assertEqual(load_workspace_documents(self.workspace_dir), ([Document("alpha", "a", "1")], []))
+
+    def test_temporary_path_creates_the_directory_and_is_not_a_package(self) -> None:
+        path = workspace.PackageFiles().temporary_path(self.workspace_dir, "alpha.dep")
+
+        self.assertEqual(path.parent, self.workspace_dir)
+        self.assertTrue(path.is_file())
+        self.assertTrue(path.name.startswith(".alpha.dep."), path.name)
+        self.assertTrue(path.name.endswith(".tmp"), path.name)
+        self.assertEqual(list(self.workspace_dir.glob("*.dep")), [])
+
 if __name__ == "__main__":
     unittest.main()
EOF
```

- [ ] **Step 2: Run them; each new test errors because `PackageFiles`/`move_document_package` do not exist.**

```bash
$PY -m unittest tests.test_document_workspace 2>&1 | $PY $T/tools/brief.py
```

Expected (10 errors, the 22 existing tests pass):

```text
ERROR: test_case_only_move_leaves_only_the_new_spelling (tests.test_document_workspace.MoveDocumentPackageTest.test_case_only_move_leaves_only_the_new_spelling)
AttributeError: module 'documents.workspace' has no attribute 'move_document_package'. Did you mean: 'save_document_package'?
ERROR: test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores (tests.test_document_workspace.MoveDocumentPackageTest.test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores)
AttributeError: module 'documents.workspace' has no attribute 'PackageFiles'
ERROR: test_install_failure_puts_the_old_package_back (tests.test_document_workspace.MoveDocumentPackageTest.test_install_failure_puts_the_old_package_back)
AttributeError: module 'documents.workspace' has no attribute 'PackageFiles'
ERROR: test_missing_old_package_and_directory_writes_the_new_package (tests.test_document_workspace.MoveDocumentPackageTest.test_missing_old_package_and_directory_writes_the_new_package)
AttributeError: module 'documents.workspace' has no attribute 'move_document_package'. Did you mean: 'save_document_package'?
ERROR: test_move_aside_failure_keeps_the_old_package (tests.test_document_workspace.MoveDocumentPackageTest.test_move_aside_failure_keeps_the_old_package)
AttributeError: module 'documents.workspace' has no attribute 'PackageFiles'
ERROR: test_move_to_a_different_name (tests.test_document_workspace.MoveDocumentPackageTest.test_move_to_a_different_name)
AttributeError: module 'documents.workspace' has no attribute 'move_document_package'. Did you mean: 'save_document_package'?
ERROR: test_pending_braille_keeps_its_metadata (tests.test_document_workspace.MoveDocumentPackageTest.test_pending_braille_keeps_its_metadata)
AttributeError: module 'documents.workspace' has no attribute 'move_document_package'. Did you mean: 'save_document_package'?
ERROR: test_staging_error_that_is_not_an_os_error_keeps_the_old_package (tests.test_document_workspace.MoveDocumentPackageTest.test_staging_error_that_is_not_an_os_error_keeps_the_old_package)
AttributeError: module 'documents.workspace' has no attribute 'move_document_package'. Did you mean: 'save_document_package'?
ERROR: test_staging_write_failure_keeps_the_old_package (tests.test_document_workspace.MoveDocumentPackageTest.test_staging_write_failure_keeps_the_old_package)
AttributeError: module 'documents.workspace' has no attribute 'PackageFiles'
ERROR: test_temporary_path_creates_the_directory_and_is_not_a_package (tests.test_document_workspace.MoveDocumentPackageTest.test_temporary_path_creates_the_directory_and_is_not_a_package)
AttributeError: module 'documents.workspace' has no attribute 'PackageFiles'
Ran 32 tests
FAILED (errors=10)
```

- [ ] **Step 3: Implement `PackageFiles` and `move_document_package` (D4 steps 1-4).**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/documents/workspace.py b/client/documents/workspace.py
index dce9b22..4529aa7 100644
--- a/client/documents/workspace.py
+++ b/client/documents/workspace.py
@@ -1,8 +1,11 @@
 from __future__ import annotations
 
+from contextlib import suppress
 from dataclasses import dataclass
 import json
+import os
 from pathlib import Path
+import tempfile
 import zipfile
 from collections.abc import Callable
 
@@ -66,6 +69,84 @@ def save_document_package(
     return package_path
 
 
+class PackageFiles:
+    """The file operations ``move_document_package`` uses; tests pass a model or a fault injector."""
+
+    def exists(self, path: Path) -> bool:
+        return Path(path).exists()
+
+    def write(self, path: Path, document: Document) -> None:
+        save_document_package(path, document)
+
+    def replace(self, source: Path, destination: Path) -> None:
+        os.replace(source, destination)
+
+    def remove(self, path: Path) -> None:
+        Path(path).unlink(missing_ok=True)
+
+    def temporary_path(self, directory: Path, name: str) -> Path:
+        """Create a new empty hidden file ``.<name>.<random>.tmp`` in ``directory`` (created if missing)."""
+        directory = Path(directory)
+        directory.mkdir(parents=True, exist_ok=True)
+        with tempfile.NamedTemporaryFile(dir=directory, prefix=f".{name}.", suffix=".tmp", delete=False) as temporary:
+            return Path(temporary.name)
+
+
+def move_document_package(
+    old_path: Path,
+    new_path: Path,
+    document: Document,
+    *,
+    files: PackageFiles,
+) -> None:
+    """Write ``document`` as the package at ``new_path`` and remove the package at ``old_path``.
+
+    Safe when both paths name the same file, as a case-only rename does on a case-insensitive
+    file system: nothing is written to, replaced onto or removed under a name that can alias
+    the other package. The new package is staged in a temporary file, the old one is moved
+    aside to another temporary file, then the staged file takes the exact name ``new_path``.
+
+    On return the package exists only at ``new_path``, with that spelling, and holds
+    ``document``. On an exception the old package is back at ``old_path`` with its spelling
+    and bytes and no temporary file is left, unless putting the old package back fails too:
+    then it stays in its ``.tmp`` file. Failing to remove the moved-aside old package after the
+    install is ignored; that leftover ``.tmp`` file is never loaded as a package.
+    """
+    old_path = Path(old_path)
+    new_path = Path(new_path)
+    staged_path = files.temporary_path(new_path.parent, new_path.name)
+    try:
+        files.write(staged_path, document)
+    except BaseException:
+        with suppress(OSError):
+            files.remove(staged_path)
+        raise
+    aside_path: Path | None = None
+    try:
+        if files.exists(old_path):
+            aside_path = files.temporary_path(old_path.parent, old_path.name)
+            files.replace(old_path, aside_path)
+    except BaseException:
+        with suppress(OSError):
+            files.remove(staged_path)
+        if aside_path is not None:
+            with suppress(OSError):
+                files.remove(aside_path)
+        raise
+    try:
+        files.replace(staged_path, new_path)
+    except BaseException:
+        if aside_path is not None:
+            with suppress(OSError):
+                files.replace(aside_path, old_path)
+        with suppress(OSError):
+            files.remove(staged_path)
+        raise
+    if aside_path is not None:
+        with suppress(OSError):
+            files.remove(aside_path)
+
+
 def load_document_package(path: Path | str) -> Document:
     package_path = Path(path)
     if package_path.suffix.casefold() != DEP_EXTENSION:
EOF
```

- [ ] **Step 4: Run the module, then the full suite.**

```bash
$PY -m unittest tests.test_document_workspace 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (nothing calls the helper yet, so the skips are unchanged):

```text
Ran 32 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1105 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/documents/workspace.py client/tests/test_document_workspace.py
git -C $REPO commit -q -F - <<'EOF'
fix: add a case-safe document package move

PackageFiles holds the five file primitives; move_document_package stages
the new package, moves the old one aside, installs the staged file under
the exact new name and then removes the old one, so a case-only rename
never writes to or removes a name that aliases the other package.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
fix: add a case-safe document package move
```

---

### Task 2: The case-insensitive file model and its self-tests (spec migration step 2; Test Plan A, B)

**Files:**
- Create: `client/tests/test_case_insensitive_package_files.py`
- Create: `client/tests/case_insensitive_package_files.py` (a helper, not a test module: no `test_` prefix, so discovery does not collect it)

**Interfaces:**
- Consumes: `PackageFiles`, `move_document_package` (Task 1), `save_document_package`, `load_document_package`, `load_workspace_documents`.
- Produces (used by Task 4): `class CaseInsensitivePackageFiles(PackageFiles)` with `__init__(self, *, replace_keeps_existing_spelling: bool = True)`, a static `resolve(path) -> Path` (the existing entry whose name is casefold-equal, exact name first, else `path`), and `exists`/`write`/`remove`/`replace` acting on resolved entries; `temporary_path` is inherited.

- [ ] **Step 1: Write the self-tests.** B1 and B2 record the two old failures on the model; B3 checks `replace`; B4 runs the new move on the model with both flag values.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_case_insensitive_package_files.py b/client/tests/test_case_insensitive_package_files.py
new file mode 100644
index 0000000..3c080fe
--- /dev/null
+++ b/client/tests/test_case_insensitive_package_files.py
@@ -0,0 +1,105 @@
+from __future__ import annotations
+
+import tempfile
+import unittest
+import zipfile
+from pathlib import Path
+
+from documents.workspace import (
+    Document,
+    load_document_package,
+    load_workspace_documents,
+    move_document_package,
+    save_document_package,
+)
+from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
+
+
+class CaseInsensitivePackageFilesTest(unittest.TestCase):
+    """The case-insensitive file model (F-1): the old failures it reproduces and the new move."""
+
+    def setUp(self) -> None:
+        temp_dir = tempfile.TemporaryDirectory()
+        self.addCleanup(temp_dir.cleanup)
+        self.root = Path(temp_dir.name)
+
+    def _workspace(self, name: str = "workspace") -> Path:
+        directory = self.root / name
+        directory.mkdir()
+        return directory
+
+    @staticmethod
+    def _listing(directory: Path) -> list[str]:
+        return sorted(path.name for path in directory.iterdir())
+
+    @staticmethod
+    def _members(path: Path) -> list[str]:
+        with zipfile.ZipFile(path) as archive:
+            return sorted(archive.namelist())
+
+    def test_writing_a_case_variant_rewrites_the_existing_entry_and_keeps_its_spelling(self) -> None:
+        # The P1-3 known defect 2 mechanism: Add "Alpha" next to "alpha".
+        workspace = self._workspace()
+        save_document_package(workspace / "alpha.dep", Document("alpha", "a", "1"))
+
+        CaseInsensitivePackageFiles().write(workspace / "Alpha.dep", Document("Alpha", "A", "2"))
+
+        self.assertEqual(self._listing(workspace), ["alpha.dep"])
+        self.assertEqual(self._members(workspace / "alpha.dep"), ["Alpha.brl", "Alpha.txt"])
+        self.assertEqual(load_workspace_documents(workspace), ([], [workspace / "alpha.dep"]))
+
+    def test_the_old_rename_sequence_deletes_a_case_only_renamed_package(self) -> None:
+        # The P1-3 known defect 1 scenario: write the new package, then unlink the old one.
+        workspace = self._workspace()
+        save_document_package(workspace / "Alpha.dep", Document("Alpha", "a", "1"))
+        files = CaseInsensitivePackageFiles()
+
+        files.write(workspace / "alpha.dep", Document("alpha", "a", "1"))
+        if files.exists(workspace / "Alpha.dep"):
+            files.remove(workspace / "Alpha.dep")
+
+        self.assertEqual(self._listing(workspace), [])
+
+    def test_replace_resolves_case_variants(self) -> None:
+        for keeps in (True, False):
+            with self.subTest(replace_keeps_existing_spelling=keeps):
+                files = CaseInsensitivePackageFiles(replace_keeps_existing_spelling=keeps)
+                own = self._workspace(f"own-{keeps}")
+                save_document_package(own / "Alpha.dep", Document("Alpha", "a", "1"))
+                alpha_bytes = (own / "Alpha.dep").read_bytes()
+
+                files.replace(own / "Alpha.dep", own / "alpha.dep")
+
+                self.assertEqual(self._listing(own), ["alpha.dep"])
+                self.assertEqual((own / "alpha.dep").read_bytes(), alpha_bytes)
+
+                other = self._workspace(f"other-{keeps}")
+                save_document_package(other / "alpha.dep", Document("alpha", "a", "1"))
+                save_document_package(other / "beta.dep", Document("beta", "b", "2"))
+                beta_bytes = (other / "beta.dep").read_bytes()
+
+                files.replace(other / "beta.dep", other / "ALPHA.dep")
+
+                self.assertEqual(self._listing(other), ["alpha.dep" if keeps else "ALPHA.dep"])
+                self.assertEqual((other / self._listing(other)[0]).read_bytes(), beta_bytes)
+
+    def test_move_document_package_keeps_a_case_only_renamed_package(self) -> None:
+        for keeps in (True, False):
+            with self.subTest(replace_keeps_existing_spelling=keeps):
+                workspace = self._workspace(f"workspace-{keeps}")
+                save_document_package(workspace / "Alpha.dep", Document("Alpha", "a", "1"))
+
+                move_document_package(
+                    workspace / "Alpha.dep",
+                    workspace / "alpha.dep",
+                    Document("alpha", "a", "1"),
+                    files=CaseInsensitivePackageFiles(replace_keeps_existing_spelling=keeps),
+                )
+
+                self.assertEqual(self._listing(workspace), ["alpha.dep"])
+                self.assertEqual(self._members(workspace / "alpha.dep"), ["alpha.brl", "alpha.txt"])
+                self.assertEqual(load_document_package(workspace / "alpha.dep"), Document("alpha", "a", "1"))
+
+
+if __name__ == "__main__":
+    unittest.main()
EOF
```

- [ ] **Step 2: Run them; the module cannot import the model yet.**

```bash
$PY -m unittest tests.test_case_insensitive_package_files 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_case_insensitive_package_files (unittest.loader._FailedTest.test_case_insensitive_package_files)
ImportError: Failed to import test module: test_case_insensitive_package_files
ModuleNotFoundError: No module named 'tests.case_insensitive_package_files'
Ran 1 test
FAILED (errors=1)
```

- [ ] **Step 3: Write the model.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/case_insensitive_package_files.py b/client/tests/case_insensitive_package_files.py
new file mode 100644
index 0000000..18e44b1
--- /dev/null
+++ b/client/tests/case_insensitive_package_files.py
@@ -0,0 +1,59 @@
+"""A case-insensitive, case-preserving file model for document package tests (F-1).
+
+``CaseInsensitivePackageFiles`` works on a real directory but resolves every path it is
+given the way NTFS and APFS do: to the existing entry in the same directory whose name is
+casefold-equal, if there is one. Linux tests use it to run the Windows and macOS
+case-collision scenarios. It is a model; the real check is the Windows verification debt.
+"""
+
+from __future__ import annotations
+
+import os
+from pathlib import Path
+
+from documents.workspace import Document, PackageFiles
+
+
+class CaseInsensitivePackageFiles(PackageFiles):
+    def __init__(self, *, replace_keeps_existing_spelling: bool = True) -> None:
+        # Replacing onto a case variant of another existing entry: True keeps that entry's
+        # spelling (the pessimistic reading), False gives it the destination spelling.
+        self.replace_keeps_existing_spelling = replace_keeps_existing_spelling
+
+    @staticmethod
+    def resolve(path: Path | str) -> Path:
+        """The existing entry that ``path`` names on a case-insensitive file system, else ``path``."""
+        path = Path(path)
+        if not path.parent.is_dir():
+            return path
+        # Names from the listing, never Path equality or exists(): both ignore case on a
+        # case-insensitive host, and the model must behave the same on every host.
+        names = sorted(entry.name for entry in path.parent.iterdir())
+        if path.name in names:
+            return path
+        folded_name = path.name.casefold()
+        for name in names:
+            if name.casefold() == folded_name:
+                return path.parent / name
+        return path
+
+    def exists(self, path: Path) -> bool:
+        return self.resolve(path).exists()
+
+    def write(self, path: Path, document: Document) -> None:
+        super().write(self.resolve(path), document)
+
+    def remove(self, path: Path) -> None:
+        super().remove(self.resolve(path))
+
+    def replace(self, source: Path, destination: Path) -> None:
+        source_entry = self.resolve(source)
+        destination = Path(destination)
+        destination_entry = self.resolve(destination)
+        if str(source_entry) == str(destination_entry):
+            # One entry renamed to its own case variant takes the new spelling.
+            os.replace(source_entry, destination)
+            return
+        os.replace(source_entry, destination_entry)
+        if destination_entry.name != destination.name and not self.replace_keeps_existing_spelling:
+            os.replace(destination_entry, destination)
EOF
```

- [ ] **Step 4: Run the self-tests, then the full suite.**

```bash
$PY -m unittest tests.test_case_insensitive_package_files 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
Ran 4 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1109 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/tests/case_insensitive_package_files.py client/tests/test_case_insensitive_package_files.py
git -C $REPO commit -q -F - <<'EOF'
test: model a case-insensitive file system for document packages

CaseInsensitivePackageFiles resolves paths the way NTFS and APFS do, so
Linux can reproduce the case-only rename and Add case-variant data loss
and run the new package move against it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
test: model a case-insensitive file system for document packages
```

---

### Task 3: Casefold the duplicate check (spec migration step 3; D1, D2)

**Files:**
- Modify: `client/tests/test_document_controller.py` (D15: `test_document_name_exists_is_exact_and_honours_exclude` becomes `test_document_name_exists_ignores_case_and_honours_exact_exclude`)
- Modify: `client/tests/test_gui_document_flows.py` (`test_add_case_variant_on_case_sensitive_file_system` and the defect-2 `KNOWN BUG` test `test_add_case_variant_on_case_insensitive_file_system_overwrites_package` merge into `test_add_case_variant_is_refused_as_a_duplicate`; new F21 `test_rename_to_a_case_variant_of_another_document_is_refused`; helper `_duplicate_name_events`)
- Modify: `client/documents/session.py:52-53` (tabs)

**Interfaces:**
- Consumes: `DocumentController.document_name_exists(name, exclude_name=None)` (unchanged signature; delegates to `session.document_name_exists`), `BrailleFrame._prompt_for_document_name` (unchanged).
- Produces: `session.document_name_exists(documents, name, exclude_name=None) -> bool` is true when a document's name is casefold-equal to `name` and not exactly `exclude_name`.

- [ ] **Step 1: Write the failing tests.** The merged Add test runs on every file system (no skip) and expects the existing duplicate error box naming the typed name `Alpha`, then the dialog prefilled with `Alpha`; `alpha.dep` stays as it was.

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_document_controller.py b/client/tests/test_document_controller.py
index e545eb2..e61e5c5 100644
--- a/client/tests/test_document_controller.py
+++ b/client/tests/test_document_controller.py
@@ -249,13 +249,19 @@ class DocumentControllerTest(unittest.TestCase):
         self.assertEqual(controller.adjacent_document_name(1), "alpha")
         self.assertIsNone(DocumentController().adjacent_document_name(1))
 
-    def test_document_name_exists_is_exact_and_honours_exclude(self) -> None:
+    def test_document_name_exists_ignores_case_and_honours_exact_exclude(self) -> None:
+        # F-1 (D1): names are compared with casefold() on every platform; the exclusion
+        # (the document being renamed) stays exact.
         controller = DocumentController(documents=list(self.documents))
 
         self.assertTrue(controller.document_name_exists("beta"))
-        self.assertFalse(controller.document_name_exists("Beta"))
+        self.assertTrue(controller.document_name_exists("Beta"))
+        self.assertFalse(controller.document_name_exists("gamma"))
         self.assertFalse(controller.document_name_exists("beta", exclude_name="beta"))
+        self.assertFalse(controller.document_name_exists("BETA", exclude_name="beta"))
         self.assertTrue(controller.document_name_exists("zoo", exclude_name="beta"))
+        legacy = DocumentController(documents=[Document("Alpha", "A", "1"), Document("alpha", "a", "2")])
+        self.assertTrue(legacy.document_name_exists("ALPHA", exclude_name="Alpha"))
 
     def test_dual_view_results_get_and_set(self) -> None:
         controller = DocumentController(documents=list(self.documents))
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index f4272c4..763bea9 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -2136,34 +2136,53 @@ class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
         self.assertEqual(frame._document_controller.document_names, ["alpha"])
         self.assertEqual(self.events, [("DocumentNameDialog", gui._("Rename Document"), "Alpha"), ("title", "alpha - DotExpress")])
 
-    def test_add_case_variant_on_case_sensitive_file_system(self) -> None:
-        self._skip_unless_case_sensitive(True)
+    def _duplicate_name_events(self, title: str, initial_name: str, typed_name: str, frame) -> list:
+        return [
+            ("DocumentNameDialog", gui._(title), initial_name),
+            (
+                "MessageBox",
+                gui._('Document "{name}" already exists.').format(name=typed_name),
+                gui._("Error"),
+                gui.wx.OK | gui.wx.ICON_ERROR,
+                frame,
+            ),
+            ("DocumentNameDialog", gui._(title), typed_name),
+        ]
+
+    def test_add_case_variant_is_refused_as_a_duplicate(self) -> None:
+        # Replaces the KNOWN BUG test of P1-3 known defect 2 (data loss: Add "Alpha"
+        # overwrote alpha.dep on a case-insensitive file system), fixed by F-1. Names are
+        # compared with casefold() on every platform, so this runs on any file system.
         alpha = Document("alpha", "a", "1")
         self._write_packages(alpha)
         frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
-        self.names = ["Alpha"]
+        self.names = ["Alpha", None]
 
         frame.on_add_document(None)
 
-        self.assertEqual(self._listing(), ["Alpha.dep", "alpha.dep"])
+        self.assertEqual(self.events, self._duplicate_name_events("Add Document", "", "Alpha", frame))
+        self.assertEqual(self._listing(), ["alpha.dep"])
         self.assertEqual(self._package("alpha"), alpha)
-        self.assertEqual(frame._document_controller.document_names, ["Alpha", "alpha"])
+        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
+        self.assertEqual(frame._document_controller.document_names, ["alpha"])
 
-    def test_add_case_variant_on_case_insensitive_file_system_overwrites_package(self) -> None:
-        # KNOWN BUG (P1-3 spec, known defect 2; data loss), pinned as it is today, NOT
-        # desired behavior: the case-sensitive duplicate check accepts "Alpha", and its
-        # package replaces alpha's. A later fix task flips this.
-        self._skip_unless_case_sensitive(False)
+    def test_rename_to_a_case_variant_of_another_document_is_refused(self) -> None:
+        # F-1: renaming beta to "Alpha" while alpha exists overwrote alpha.dep on a
+        # case-insensitive file system; it is now refused like an exact duplicate.
         alpha = Document("alpha", "a", "1")
-        self._write_packages(alpha)
-        frame = self._make_workspace_frame([alpha], open_name="alpha", selected_name="alpha")
-        self.names = ["Alpha"]
+        beta = Document("beta", "b", "2")
+        self._write_packages(alpha, beta)
+        frame = self._make_workspace_frame([alpha, beta], open_name="alpha", selected_name="beta")
+        before = self._state(frame)
+        self.names = ["Alpha", None]
 
-        frame.on_add_document(None)
+        frame.on_rename_document(None)
 
-        self.assertEqual([name.casefold() for name in self._listing()], ["alpha.dep"])
-        self.assertEqual(self._members(self._listing()[0][: -len(".dep")]), ["Alpha.brl", "Alpha.txt"])
-        self.assertEqual(frame._document_controller.document_names, ["Alpha", "alpha"])
+        self.assertEqual(self.events, self._duplicate_name_events("Rename Document", "beta", "Alpha", frame))
+        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
+        self.assertEqual(self._package("alpha"), alpha)
+        self.assertEqual(self._package("beta"), beta)
+        self.assertEqual(self._state(frame), before)
 
     # --- delete ------------------------------------------------------------
 
EOF
```

- [ ] **Step 2: Run them; today the check is exact, so `Alpha` is accepted.**

```bash
$PY -m unittest tests.test_document_controller tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected (3 failures: the controller accepts `Beta`; Add creates `Alpha` and opens it; Rename of `beta` to `Alpha` goes through; the one skip is the case-insensitive rename test, removed in Task 4):

```text
FAIL: test_document_name_exists_ignores_case_and_honours_exact_exclude (tests.test_document_controller.DocumentControllerTest.test_document_name_exists_ignores_case_and_honours_exact_exclude)
AssertionError: False is not true
FAIL: test_add_case_variant_is_refused_as_a_duplicate (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_add_case_variant_is_refused_as_a_duplicate)
AssertionError: Lists differ: [('Do[29 chars]), ('title', 'Alpha - DotExpress')] != [('Do[29 chars]), ('MessageBox', '文件「Alpha」已存在。', '錯誤', 516, [81 chars]ha')]
FAIL: test_rename_to_a_case_variant_of_another_document_is_refused (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_rename_to_a_case_variant_of_another_document_is_refused)
AssertionError: Lists differ: [('Do[35 chars]), ('title', 'alpha - DotExpress')] != [('Do[35 chars]), ('MessageBox', '文件「Alpha」已存在。', '錯誤', 516, [83 chars]ha')]
Ran 181 tests
FAILED (failures=3, skipped=1)
```

- [ ] **Step 3: Casefold the comparison; keep the exclusion exact.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/documents/session.py b/client/documents/session.py
index e9dfe21..91d9df7 100644
--- a/client/documents/session.py
+++ b/client/documents/session.py
@@ -50,7 +50,8 @@ def get_adjacent_document_name(documents: list[Document], current_name: str | No
 
 
 def document_name_exists(documents: list[Document], name: str, exclude_name: str | None = None) -> bool:
-	return any(document.name == name and document.name != exclude_name for document in documents)
+	folded_name = name.casefold()
+	return any(document.name.casefold() == folded_name and document.name != exclude_name for document in documents)
 
 
 def plan_open_document(documents: list[Document], name: str | None) -> OpenDocumentDecision:
EOF
```

- [ ] **Step 4: Run the two modules, then the full suite.**

```bash
$PY -m unittest tests.test_document_controller tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (the Add case-variant skip is gone: `skipped=8`):

```text
Ran 181 tests
OK (skipped=1)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1109 tests
FAILED (failures=1, skipped=8)
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/documents/session.py client/tests/test_document_controller.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'EOF'
fix: refuse document names that differ only in case

Add and Rename compare names with casefold() on every platform, as Import
already does, so "Alpha" is refused while "alpha" exists instead of
overwriting alpha.dep on a case-insensitive file system. The exclusion of
the renamed document stays exact, so its own case-only rename is allowed.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
fix: refuse document names that differ only in case
```

---

### Task 4: Case-only rename through `move_document_package` (spec migration step 4; D3, D5, D6)

**Files:**
- Modify: `client/tests/test_workspace_service.py` (imports `PackageFiles`, `CaseInsensitivePackageFiles`; `_FailingInstallPackageFiles`, `_UnusablePackageFiles`; `_service(..., package_files=None, ...)`; E16-E19 with helpers `_case_only_service`, `_assert_case_only_rename`)
- Modify: `client/tests/test_gui_document_flows.py` (import `CaseInsensitivePackageFiles`; `test_case_only_rename_on_case_sensitive_file_system` and the defect-1 `KNOWN BUG` test `test_case_only_rename_on_case_insensitive_file_system_deletes_package` merge into `test_case_only_rename_keeps_the_document`; new F20; helper `_rename_alpha_case_only`; `_skip_unless_case_sensitive` removed)
- Modify: `client/documents/workspace_service.py` (constructor keyword `package_files`; case-only branch in `rename_document`; module docstring)

**Interfaces:**
- Consumes: `PackageFiles`, `move_document_package` (Task 1), `CaseInsensitivePackageFiles` (Task 2), `DocumentController.rename_document` (unchanged).
- Produces: `DocumentWorkspaceService(controller, workspace_dir, *, package_files: PackageFiles | None = None)`; `rename_document(source_name, new_name)` uses `move_document_package(..., files=package_files)` when `source_name.casefold() == new_name.casefold()` (names differ, checked first), else today's lines unchanged.

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 763bea9..98f0ad6 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -15,6 +15,7 @@ from unittest.mock import ANY, DEFAULT, Mock, call, patch
 
 from tests import wx_stub
 from tests.conversion_harness import DeferredCalls, FakeTimers, make_thread_factory
+from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
 from tests.menu_recording import DOCUMENT_MENU_BUILD_LOG, MenuRecorder, enable_log, fake_translate
 
 _SCOPE = wx_stub.StubScope(
@@ -1831,15 +1832,6 @@ class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
             frame,
         )
 
-    def _skip_unless_case_sensitive(self, sensitive: bool) -> None:
-        self.workspace.mkdir(parents=True, exist_ok=True)
-        probe = self.workspace / "case-probe"
-        probe.write_text("", encoding="utf-8")
-        is_sensitive = not (self.workspace / "CASE-PROBE").exists()
-        probe.unlink()
-        if is_sensitive != sensitive:
-            self.skipTest("needs a case-%s file system" % ("sensitive" if sensitive else "insensitive"))
-
     # --- Add and default document ------------------------------------------
 
     def test_add_saves_open_document_then_creates_and_opens_new_document(self) -> None:
@@ -2107,34 +2099,35 @@ class DocumentWorkspaceFlowsCharacterizationTest(unittest.TestCase):
                 self.assertEqual(self._listing(), ["alpha.dep"])
                 self.assertEqual(self._state(frame), before)
 
-    def test_case_only_rename_on_case_sensitive_file_system(self) -> None:
-        self._skip_unless_case_sensitive(True)
+    def _rename_alpha_case_only(self, package_files=None):
         alpha = Document("Alpha", "a", "1")
         self._write_packages(alpha)
         frame = self._make_workspace_frame([alpha], open_name="Alpha", selected_name="Alpha")
+        if package_files is not None:
+            frame._workspace_service = DocumentWorkspaceService(
+                frame._document_controller,
+                self.workspace,
+                package_files=package_files,
+            )
         self.names = ["alpha"]
 
         frame.on_rename_document(None)
 
         self.assertEqual(self._listing(), ["alpha.dep"])
         self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
+        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
         self.assertEqual(frame._document_controller.document_names, ["alpha"])
+        self.assertEqual(self.events, [("DocumentNameDialog", gui._("Rename Document"), "Alpha"), ("title", "alpha - DotExpress")])
 
-    def test_case_only_rename_on_case_insensitive_file_system_deletes_package(self) -> None:
-        # KNOWN BUG (P1-3 spec, known defect 1; data loss), pinned as it is today, NOT
-        # desired behavior: the new package is the old file, so the unlink that follows
-        # removes the document. A later fix task flips this.
-        self._skip_unless_case_sensitive(False)
-        alpha = Document("Alpha", "a", "1")
-        self._write_packages(alpha)
-        frame = self._make_workspace_frame([alpha], open_name="Alpha", selected_name="Alpha")
-        self.names = ["alpha"]
-
-        frame.on_rename_document(None)
+    def test_case_only_rename_keeps_the_document(self) -> None:
+        # Replaces the KNOWN BUG test of P1-3 known defect 1 (data loss: the case-only
+        # rename deleted the package on a case-insensitive file system), fixed by F-1.
+        # Runs on the host's real file system: case-insensitive on Windows and macOS.
+        self._rename_alpha_case_only()
 
-        self.assertEqual(self._listing(), [])
-        self.assertEqual(frame._document_controller.document_names, ["alpha"])
-        self.assertEqual(self.events, [("DocumentNameDialog", gui._("Rename Document"), "Alpha"), ("title", "alpha - DotExpress")])
+    def test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document(self) -> None:
+        # F-1: the same rename on the case-insensitive file model, so Linux covers it too.
+        self._rename_alpha_case_only(CaseInsensitivePackageFiles())
 
     def _duplicate_name_events(self, title: str, initial_name: str, typed_name: str, frame) -> list:
         return [
diff --git a/client/tests/test_workspace_service.py b/client/tests/test_workspace_service.py
index 67aeb30..29a3916 100644
--- a/client/tests/test_workspace_service.py
+++ b/client/tests/test_workspace_service.py
@@ -7,12 +7,37 @@ import zipfile
 from pathlib import Path
 
 from documents.controller import DocumentController
-from documents.workspace import BatchIssue, Document, load_document_package, save_document_package
+from documents.workspace import BatchIssue, Document, PackageFiles, load_document_package, save_document_package
 from documents.workspace_service import DeleteAllResult, DocumentWorkspaceService, ImportResult
+from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
 
 SERVICE_PATH = Path(__file__).resolve().parents[1] / "documents" / "workspace_service.py"
 
 
+class _FailingInstallPackageFiles(PackageFiles):
+    """The real file operations, except that replacing onto a file named ``name`` raises ``OSError``.
+
+    The name is compared as a string: ``Path`` equality ignores case on Windows.
+    """
+
+    def __init__(self, name: str) -> None:
+        self.name = name
+
+    def replace(self, source: Path, destination: Path) -> None:
+        if Path(destination).name == self.name:
+            raise OSError("injected install failure")
+        super().replace(source, destination)
+
+
+class _UnusablePackageFiles:
+    """Any use fails the test: a regular rename must not go through ``package_files``."""
+
+    def _fail(self, *_args) -> None:
+        raise AssertionError("a regular rename used package_files")
+
+    exists = write = replace = remove = temporary_path = _fail
+
+
 class DocumentWorkspaceServiceTest(unittest.TestCase):
     def setUp(self) -> None:
         temp_dir = tempfile.TemporaryDirectory()
@@ -20,9 +45,11 @@ class DocumentWorkspaceServiceTest(unittest.TestCase):
         self.root = Path(temp_dir.name)
         self.workspace = self.root / "workspace"
 
-    def _service(self, documents=(), **state) -> DocumentWorkspaceService:
+    def _service(self, documents=(), *, package_files=None, **state) -> DocumentWorkspaceService:
         self.controller = DocumentController(documents=list(documents), **state)
-        return DocumentWorkspaceService(self.controller, self.workspace)
+        if package_files is None:
+            return DocumentWorkspaceService(self.controller, self.workspace)
+        return DocumentWorkspaceService(self.controller, self.workspace, package_files=package_files)
 
     def _write(self, *documents: Document) -> None:
         for document in documents:
@@ -266,6 +293,58 @@ class DocumentWorkspaceServiceTest(unittest.TestCase):
         self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))
         self.assertEqual(self._state(), before)
 
+    def _assert_case_only_rename(self, service: DocumentWorkspaceService) -> None:
+        self.assertEqual(service.rename_document("Alpha", "alpha"), Document("alpha", "a", "1"))
+
+        self.assertEqual(self._listing(), ["alpha.dep", "beta.dep"])
+        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
+        self.assertEqual(self._package("alpha"), Document("alpha", "a", "1"))
+        self.assertEqual(self._package("beta"), Document("beta", "b", "2"))
+        self.assertEqual(
+            self._state(),
+            ([Document("alpha", "a", "1"), Document("beta", "b", "2")], "alpha", "alpha", {"alpha": ("segment",)}),
+        )
+
+    def _case_only_service(self, package_files=None) -> DocumentWorkspaceService:
+        self._write(Document("Alpha", "a", "1"), Document("beta", "b", "2"))
+        return self._service(
+            [Document("Alpha", "a", "1"), Document("beta", "b", "2")],
+            package_files=package_files,
+            open_name="Alpha",
+            selected_name="Alpha",
+            dual_view_results_by_document={"Alpha": ("segment",)},
+        )
+
+    def test_case_only_rename_moves_the_package_and_updates_the_controller(self) -> None:
+        self._assert_case_only_rename(self._case_only_service())
+
+    def test_case_only_rename_on_a_case_insensitive_file_model(self) -> None:
+        # F-1: the Linux stand-in for Windows and macOS (P1-3 known defect 1 lost the package).
+        self._assert_case_only_rename(self._case_only_service(CaseInsensitivePackageFiles()))
+
+    def test_case_only_rename_install_failure_propagates_and_keeps_state(self) -> None:
+        service = self._case_only_service(_FailingInstallPackageFiles("alpha.dep"))
+        alpha_bytes = (self.workspace / "Alpha.dep").read_bytes()
+        before = self._state()
+
+        with self.assertRaises(OSError):
+            service.rename_document("Alpha", "alpha")
+
+        self.assertEqual(self._listing(), ["Alpha.dep", "beta.dep"])
+        self.assertEqual((self.workspace / "Alpha.dep").read_bytes(), alpha_bytes)
+        self.assertEqual(self._state(), before)
+
+    def test_regular_rename_does_not_use_package_files(self) -> None:
+        # F-1 (D6): only case-only renames take the new path; regular renames keep
+        # today's write-then-unlink sequence (known defect 3 stays pinned above).
+        self._write(Document("alpha", "a", "1"))
+        service = self._service([Document("alpha", "a", "1")], package_files=_UnusablePackageFiles())
+
+        self.assertEqual(service.rename_document("alpha", "gamma"), Document("gamma", "a", "1"))
+
+        self.assertEqual(self._listing(), ["gamma.dep"])
+        self.assertEqual(self._package("gamma"), Document("gamma", "a", "1"))
+
     def test_rename_unknown_source_does_nothing(self) -> None:
         service = self._service([Document("alpha", "a", "1")])
 
EOF
```

- [ ] **Step 2: Run them; the four tests that inject file operations error because the keyword does not exist.** The merged real-file-system test and E16 already pass here, because Linux is case-sensitive (Spec Corrections 1); on Windows and macOS they fail like the old `KNOWN BUG` test.

```bash
$PY -m unittest tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
ERROR: test_case_only_rename_install_failure_propagates_and_keeps_state (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_case_only_rename_install_failure_propagates_and_keeps_state)
TypeError: DocumentWorkspaceService.__init__() got an unexpected keyword argument 'package_files'
ERROR: test_case_only_rename_on_a_case_insensitive_file_model (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_case_only_rename_on_a_case_insensitive_file_model)
TypeError: DocumentWorkspaceService.__init__() got an unexpected keyword argument 'package_files'
ERROR: test_regular_rename_does_not_use_package_files (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_regular_rename_does_not_use_package_files)
TypeError: DocumentWorkspaceService.__init__() got an unexpected keyword argument 'package_files'
ERROR: test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document (tests.test_gui_document_flows.DocumentWorkspaceFlowsCharacterizationTest.test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_
TypeError: DocumentWorkspaceService.__init__() got an unexpected keyword argument 'package_files'
Ran 189 tests
FAILED (errors=4)
```

- [ ] **Step 3: Add only the constructor keyword (stored, not used yet).**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/documents/workspace_service.py b/client/documents/workspace_service.py
index ecbaf26..82edc16 100644
--- a/client/documents/workspace_service.py
+++ b/client/documents/workspace_service.py
@@ -17,6 +17,7 @@ from documents.session import DeleteDocumentDecision
 from documents.workspace import (
     BatchIssue,
     Document,
+    PackageFiles,
     batch_import_documents,
     document_package_path_for_name,
     ensure_workspace_directory,
@@ -39,9 +40,16 @@ class DeleteAllResult:
 
 
 class DocumentWorkspaceService:
-    def __init__(self, controller: DocumentController, workspace_dir: Path) -> None:
+    def __init__(
+        self,
+        controller: DocumentController,
+        workspace_dir: Path,
+        *,
+        package_files: PackageFiles | None = None,
+    ) -> None:
         self._controller = controller
         self._workspace_dir = Path(workspace_dir)
+        self._package_files = package_files or PackageFiles()
 
     @property
     def workspace_dir(self) -> Path:
EOF
```

- [ ] **Step 4: Run again; a case-only rename still ignores the injected file operations.** E18's install failure is never reached, because the rename still writes `alpha.dep` and unlinks `Alpha.dep` directly: on a case-insensitive file system this is the sequence that deletes the package (B2).

```bash
$PY -m unittest tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
```

Expected:

```text
FAIL: test_case_only_rename_install_failure_propagates_and_keeps_state (tests.test_workspace_service.DocumentWorkspaceServiceTest.test_case_only_rename_install_failure_propagates_and_keeps_state)
AssertionError: OSError not raised
Ran 189 tests
FAILED (failures=1)
```

- [ ] **Step 5: Route case-only renames through `move_document_package`; update the module docstring.**

```bash
git -C $REPO apply <<'EOF'
diff --git a/client/documents/workspace_service.py b/client/documents/workspace_service.py
index 82edc16..af0d6de 100644
--- a/client/documents/workspace_service.py
+++ b/client/documents/workspace_service.py
@@ -3,7 +3,10 @@
 No wx: the frame keeps the dialogs, confirmations, error messages and list refreshes.
 The order of memory and disk effects is part of the contract: save updates memory
 before writing, rename writes the new package before deleting the old one, and
-Delete All reports a failure before it reloads the workspace.
+Delete All reports a failure before it reloads the workspace. A case-only rename
+(``Alpha`` to ``alpha``) instead stages the new package and moves the old one aside
+before installing it (``move_document_package``), because on a case-insensitive file
+system both names are the same file.
 """
 
 from __future__ import annotations
@@ -22,6 +25,7 @@ from documents.workspace import (
     document_package_path_for_name,
     ensure_workspace_directory,
     load_workspace_documents,
+    move_document_package,
     prepare_document_for_save,
     save_document_package,
 )
@@ -109,6 +113,14 @@ class DocumentWorkspaceService:
         source = self._controller.get_document(source_name)
         if source is None:
             return None
+        if source_name.casefold() == new_name.casefold():
+            move_document_package(
+                self.package_path(source_name),
+                self.package_path(new_name),
+                Document(new_name, source.text, source.braille),
+                files=self._package_files,
+            )
+            return self._controller.rename_document(source_name, new_name)
         save_document_package(self.package_path(new_name), Document(new_name, source.text, source.braille))
         old_path = self.package_path(source_name)
         if old_path.exists():
EOF
```

- [ ] **Step 6: Run the two modules, then the full suite.**

```bash
$PY -m unittest tests.test_workspace_service tests.test_gui_document_flows 2>&1 | $PY $T/tools/brief.py
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
```

Expected (the case-only rename skip is gone: `skipped=7`, the liblouis tests only):

```text
Ran 189 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1113 tests
FAILED (failures=1, skipped=7)
```

- [ ] **Step 7: Commit.**

```bash
git -C $REPO add client/documents/workspace_service.py client/tests/test_workspace_service.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'EOF'
fix: keep the document on a case-only rename

A rename that only changes case (Alpha to alpha) now goes through
move_document_package with injectable file operations, so the package is
no longer deleted on Windows and macOS and ends up as exactly alpha.dep.
Other renames keep today's write-then-unlink sequence (known defect 3 is
unchanged).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO log --format=%s -1
git -C $REPO status --short
```

Expected:

```text
fix: keep the document on a case-only rename
```

---

### Task 5: Acceptance and mutation check (no commit)

- [ ] **Step 1: Snapshot application data, then run criteria 1 and 2** (full suite; 20 shuffle seeds, each with only the P2-5 failure).

```bash
sed 1d $SP/p26impl/snap.sh | bash > $T/app_data_before.txt 2>&1
$PY -m unittest discover -s tests 2>&1 | $PY $T/tools/brief.py
for s in $(seq 1 20); do $PY $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (criterion 1: 1113 tests, `skipped=7`; criterion 2: 20 seeds, each `ran=1113` with the P2-5 failure only):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 1113 tests
FAILED (failures=1, skipped=7)
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=1113 failures=1 errors=0 skipped=7
```

- [ ] **Step 2: Criterion 6: application data unchanged by criteria 1-2.**

```bash
sed 1d $SP/p26impl/snap.sh | bash > $T/app_data_after.txt 2>&1
diff $T/app_data_before.txt $T/app_data_after.txt && echo "app data unchanged"
```

Expected:

```text
app data unchanged
```

- [ ] **Step 3: Criterion 3: the focused modules pass, with no skip in `tests.test_gui_document_flows`.**

```bash
$PY -m unittest tests.test_case_insensitive_package_files tests.test_document_workspace tests.test_document_controller tests.test_workspace_service tests.test_gui_document_flows -v 2>&1 | $PY $T/tools/brief.py
$PY -m unittest tests.test_gui_document_flows -v 2>&1 | grep -c " \.\.\. skipped" || true
```

Expected (the second line is the number of skipped tests in the GUI module):

```text
Ran 246 tests
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

- [ ] **Step 5: Criterion 7: the defect 1 and 2 pins are gone; the defect 3 pins are still there and unchanged.**

```bash
grep -rn "KNOWN BUG (P1-3 spec, known defect [12]" tests || echo "no defect 1/2 pins"
grep -rn "KNOWN BUG (P1-3 spec, known defect 3" tests | cut -d: -f1
$PY - <<'PYEOF'
import ast
import subprocess
from pathlib import Path

PINS = {
    "client/tests/test_workspace_service.py": "test_rename_unlink_failure_propagates_and_leaves_both_packages",
    "client/tests/test_gui_document_flows.py": "test_rename_unlink_failure_leaves_both_packages_and_state",
}


def segment(source, name):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node)
    return None


repo = Path("..").resolve()
for path, name in PINS.items():
    before = subprocess.run(["git", "-C", str(repo), "show", f"main:{path}"], capture_output=True, text=True, check=True).stdout
    old, new = segment(before, name), segment((repo / path).read_text(encoding="utf-8"), name)
    print(name, "unchanged" if old is not None and old == new else "CHANGED")
PYEOF
```

Expected (the two defect-3 tests are byte for byte as on `main`):

```text
no defect 1/2 pins
tests/test_gui_document_flows.py
tests/test_workspace_service.py
test_rename_unlink_failure_propagates_and_leaves_both_packages unchanged
test_rename_unlink_failure_leaves_both_packages_and_state unchanged
```

- [ ] **Step 6: Criterion 8: the files changed against `main`, and the branch.**

```bash
git -C $REPO diff main --name-only
git -C $REPO status --short
git -C $REPO log --format=%s main..HEAD
```

Expected (the plan's own file and the spec pair are the only docs):

```text
client/documents/session.py
client/documents/workspace.py
client/documents/workspace_service.py
client/tests/case_insensitive_package_files.py
client/tests/test_case_insensitive_package_files.py
client/tests/test_document_controller.py
client/tests/test_document_workspace.py
client/tests/test_gui_document_flows.py
client/tests/test_workspace_service.py
docs/superpowers/plans/2026-10-09-f1-workspace-case-collisions.md
docs/superpowers/specs/2026-10-09-f1-workspace-case-collisions-design.md
docs/superpowers/specs/2026-10-09-f1-workspace-case-collisions-design_zh-TW.md
fix: keep the document on a case-only rename
fix: refuse document names that differ only in case
test: model a case-insensitive file system for document packages
fix: add a case-safe document package move
docs: plan workspace case collision fix
docs: spec workspace case collision fix
```

- [ ] **Step 7: Mutation check: every reintroduced defect and every broken guarantee of the new sequence is caught.**

```bash
$PY $T/tools/f1_mutants.py $REPO $T/mut; echo "exit=$?"
```

Expected (12 mutants, none survives; `defect1-*` and `move-without-move-aside` reintroduce known defect 1, `defect2-exact-duplicate-check` reintroduces known defect 2; on Linux the deleted case-only branch is caught by E18 alone, see Spec Corrections 1):

```text
defect1-case-only-branch-removed: caught by test_case_only_rename_install_failure_propagates_and_keeps_state
defect1-old-sequence-in-case-only-branch: caught by test_case_only_rename_install_failure_propagates_and_keeps_state test_case_only_rename_on_a_case_insensitive_file_model test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document
move-without-move-aside: caught by test_case_only_move_leaves_only_the_new_spelling test_case_only_rename_keeps_the_document test_case_only_rename_moves_the_package_and_updates_the_controller test_case_only_rename_on_a_case_insensitive_file_model test_case_only_rename_on_a_case_insensitive_file_model_keeps_the_document test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores test_move_aside_failure_keeps_the_old_package test_move_document_package_keeps_a_case_only_renamed_package test_move_to_a_different_name test_pending_braille_keeps_its_metadata
defect2-exact-duplicate-check: caught by test_add_case_variant_is_refused_as_a_duplicate test_document_name_exists_ignores_case_and_honours_exact_exclude test_rename_to_a_case_variant_of_another_document_is_refused
exclusion-ignores-case: caught by test_document_name_exists_ignores_case_and_honours_exact_exclude
install-failure-not-restored: caught by test_case_only_rename_install_failure_propagates_and_keeps_state test_install_failure_puts_the_old_package_back
clean-up-failure-raises: caught by test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores
staging-cleanup-only-on-os-error: caught by test_staging_error_that_is_not_an_os_error_keeps_the_old_package
move-aside-failure-leaks-temporary-files: caught by test_move_aside_failure_keeps_the_old_package
temporary-file-named-dep: caught by test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores test_temporary_path_creates_the_directory_and_is_not_a_package
temporary-directory-not-created: caught by test_missing_old_package_and_directory_writes_the_new_package test_temporary_path_creates_the_directory_and_is_not_a_package
regular-renames-use-the-move: caught by test_regular_rename_does_not_use_package_files test_rename_unlink_failure_leaves_both_packages_and_state test_rename_unlink_failure_propagates_and_leaves_both_packages
exit=0
```

## Windows Verification Debt (cannot run here)

- `cd client && python -m unittest tests.test_gui_document_flows tests.test_workspace_service tests.test_document_workspace tests.test_case_insensitive_package_files -v` on Windows (and macOS if available): `test_case_only_rename_keeps_the_document`, `test_case_only_rename_moves_the_package_and_updates_the_controller` and `test_add_case_variant_is_refused_as_a_duplicate` run against a real case-insensitive file system and must pass (the first two fail there on the old code); `MoveDocumentPackageTest` and the model self-tests must pass unchanged there (names are compared as strings, Spec Corrections 2); afterwards `dir` of a workspace shows `alpha.dep` in lower case.
- Packaged build, by hand: create `Alpha`, type text, rename to `alpha`, restart: the document is there with its text and Explorer shows `alpha.dep`. Add `ALPHA`: the duplicate error appears and nothing changes on disk. Rename another document to `Alpha`: same.
- Case-only rename while the package is open in another program (for example a zip tool): the error box appears, `Alpha` stays in the list, and `Alpha.dep` is unchanged after a restart; no `.tmp` file is left (or, if the restore failed, one `.Alpha.dep.*.tmp` holding the old package).
- Pre-existing, unrelated: `tests.test_dictionary_name_prompt ... test_case_only_rename_still_renames` is expected to error on a case-insensitive file system (no skip); record the result.
- No menu, dialog or string changes: no screenshots, no `generate-pot.bat` run.

## Out of Scope / Follow-ups (from the spec)

- Known defect 3 (Rename unlink failure leaves two packages): switch regular renames to `move_document_package` after deciding D6's questions; flip its two `KNOWN BUG` tests then.
- Dictionaries: case-only rename refused on Windows/macOS; case variants allowed on Linux only; `resolve_selected_dictionary` matches the saved name exactly. No data loss; needs its own UX decisions.
- Aliasing beyond `casefold()` (D8), and Add/Rename silently overwriting a `.dep` that is on disk but not in the list (an invalid package kept at startup): both need a disk-based existence check.
- Export All with a legacy workspace holding both `Alpha` and `alpha` writes both `.brl` files to the same name on Windows.
