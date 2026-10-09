# Windows Test Portability (W-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** The six Windows-only test failures pass by making their expectations platform-correct (spec D1). Tests only: no production, generated, vendored or locale file changes; both fixtures untouched.

**Architecture:** Four small commits, one per cause (spec D3), each red before and green after on Windows, each expectation unchanged on POSIX. Then full-suite verification, results, merge.

**Spec:** `docs/superpowers/specs/2026-10-09-w2-windows-test-portability-design.md`.

## Global Constraints

- Branch `fix/w2-windows-test-portability` from `main` (`9a4ae81`). Merge with `git merge --no-ff`; never push, never delete the branch, never rewrite history.
- Files that may change: `client/tests/test_gui_document_flows.py`, `client/tests/test_dual_view_browser.py`, `client/tests/test_liblouis_adapter.py`, `client/tests/test_liblouis_runtime.py` (all 4 spaces), plus the W-2 docs.
- Never touch the untracked `client2/`, `preprocessing/`, `.sconsign.dblite`, `vendor/nvda/liblouis/dist/`, `client/config.json`, the user data in `client/dictionary/` or `client/.venv`.
- `core.autocrlf=true`: edit with the Edit tool, not MSYS `sed -i`; `git diff` must show only the intended lines.
- Fixtures: `translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Commands run from `client/` in Git Bash with:
  ```bash
  REPO=/d/workspace/DotExpress
  PY=$REPO/client/.venv/Scripts/python.exe
  export PYTHONIOENCODING=utf-8
  cd $REPO/client
  ```

## Expected Counts (Windows)

| State | `discover -s tests` |
| --- | --- |
| baseline (`9a4ae81`) | `Ran 1143`, `FAILED (failures=7, errors=1, skipped=5)` |
| after Task 4 | `Ran 1143`, `FAILED (failures=1, errors=1, skipped=5)` |

---

### Task 0: Baseline (no commit)

- [x] **Step 1:** `git -C $REPO switch -c fix/w2-windows-test-portability`
- [x] **Step 2: Red.** Run the six tests by name; expect `FAILED (failures=6)` with the messages in the spec table.
- [x] **Step 3: Production at `6e5819f`.** `git archive 6e5819f client | tar -x -C <scratch>`; from that copy run `tests.test_dual_view_browser tests.test_liblouis_adapter` (expect the same three failures) and call its `documents.formats._write_html` into a temp file (expect CRLF only). `git diff 6e5819f HEAD -- client/dual_view/browser.py client/adapters/translation/liblouis.py` is empty; `git ls-tree 6e5819f include/liblouis` equals `HEAD`'s.

### Task 1: HTML line ends (items 1, 2)

- [x] Add after `make_snapshot` in `client/tests/test_gui_document_flows.py`:

```python
def text_file_bytes(text: str) -> bytes:
    """Bytes ``Path.write_text(text, encoding="utf-8")`` writes: newlines become ``os.linesep``."""
    return text.replace("\n", os.linesep).encode("utf-8")
```

- [x] Replace `cached_html.encode("utf-8")`, `empty_html.encode("utf-8")` and `expected.encode("utf-8")` in the two tests with `text_file_bytes(...)`. (`beta.html` would fail next once `alpha.html` passes.)
- [x] Both tests pass; commit `test: expect platform newlines in HTML export bytes (W-2)`.

### Task 2: Browser executable paths (items 3, 4)

- [x] In `client/tests/test_dual_view_browser.py`, build the executable `Path` once per browser and expect `str(path)` as the first command element (Chrome, Edge, Firefox).
- [x] Both tests pass; commit `test: expect native executable paths in browser commands (W-2)`.

### Task 3: Table path join (item 5)

- [x] In `client/tests/test_liblouis_adapter.py`, `import os` and expect `[os.path.join("/tables", "en.ctb")]`.
- [x] Test passes; commit `test: expect os.path.join for liblouis table path (W-2)`.

### Task 4: configure.ac case (item 6)

- [x] In `client/tests/test_liblouis_runtime.py`, pass `re.IGNORECASE` to the `AC_INIT` search.
- [x] Test passes (expected `3.37.0` equals the DLL's); commit `test: match liblouis AC_INIT case-insensitively (W-2)`.

### Task 5: Verification, results, merge

- [x] **Step 1:** the six tests by name: `OK`.
- [x] **Step 2:** `$PY -m unittest discover -s tests -v > $TEMP/w2_discover.txt 2>&1`; counts as in Expected Counts; remaining failure/error/skips as in spec acceptance 2.
- [x] **Step 3:** `py_compile` the four test files; fixture hashes; `git status --short` shows only the pre-existing untracked items.
- [x] **Step 4:** record results below, commit `docs: record W-2 verification results`, then:

```bash
git -C $REPO switch main
git -C $REPO merge --no-ff fix/w2-windows-test-portability \
  -m "merge: Windows test portability (W-2)" \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## Results

2026-10-09, Windows 11, `client\.venv` Python 3.13. Implementation commits `b014136` (HTML), `30331f8` (browser), `67914bf` (table join), `ac2bd2e` (configure.ac).

### Baseline (Task 0)

- Red: the six tests by name, `FAILED (failures=6)`, messages as in the spec table.
- `6e5819f` from `git archive`: `tests.test_dual_view_browser tests.test_liblouis_adapter` gives `Ran 11`, `FAILED (failures=3)` (the same Chrome, Firefox and `/tables\en.ctb` failures). Its `_write_html` writes CRLF only (`has CRLF: True`, `bare LF: 0`).
- `git diff 6e5819f HEAD -- client/dual_view/browser.py client/adapters/translation/liblouis.py` is empty. `client/documents/formats.py` changed (signature, MathML converter) but still writes with `Path.write_text(html, encoding="utf-8")`. `include/liblouis` is `2aa5f84b` (`v3.37.0`) at both commits.

### After Task 4

- Each of the six tests by name: `OK`. Whole modules: `test_dual_view_browser` 8 OK, `test_liblouis_adapter` 3 OK, `test_liblouis_runtime` 5 OK.
- `discover -s tests`: `Ran 1143`, `FAILED (failures=1, errors=1, skipped=5)` (before: `failures=7`).
  - FAIL `test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math`: P2-5 decision, `['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']`.
  - ERROR `test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames`: known defect on case-insensitive file systems, `FileExistsError: Dictionary 'Alpha' already exists.`
  - Skips: `test_atomic_write.WriteTextAtomicallyTest` x3 and `test_document_workspace.MoveDocumentPackageTest.test_case_only_move_keeps_the_permission_bits_of_the_old_package` (`POSIX permission bits`); `test_dictionary_presenter.PresenterRenameTest.test_rename_case_only_change_renames_file` (case-insensitive file system).
- `py_compile` of the four test files: OK. Fixture sha256 `e67d95a1...211ccd` and `f493da52...c66c2cf`. `git status --short` lists only the pre-existing untracked items.

### POSIX (by reasoning; no Linux run)

- `text_file_bytes`: `os.linesep == "\n"`, so it is `text.encode("utf-8")`, the old expectation.
- `str(Path("C:/Chrome/chrome.exe"))` on `PosixPath` is `C:/Chrome/chrome.exe` (same for Edge, Firefox).
- `os.path.join("/tables", "en.ctb")` is `/tables/en.ctb`.
- `LiblouisRuntimeTests` is skipped off Windows; `re.IGNORECASE` is platform-independent.
