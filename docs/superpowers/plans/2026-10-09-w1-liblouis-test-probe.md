# liblouis Test Probe (W-1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The three test modules that use the real liblouis load the binding only through `braille.louis_helper`, so on Windows 11 they get the bundled `client/braille/liblouis.dll` instead of System32's older one, and a guard test keeps any test module from importing `braille.liblouis` directly again. Tests only: no production, generated, vendored or locale file changes, no msgid change (353), both fixtures untouched.

**Architecture:** One green commit, red first. Task 1 adds `LiblouisImportGuardTest` to `client/tests/test_braille_glue.py` and shows it fail on exactly the three probes. Task 2 changes the probes (two module-level `try` imports and one `setUpClass`) and commits guard and fix together. Task 3 runs the Windows verification and records the results below.

**Tech Stack:** Python 3.13 standard library (`ast`, `unittest`). Windows 11, `client\.venv` with wxPython, the bundled liblouis 3.37.0 DLL and tables built by `scripts\build-liblouis.bat` and installed by `scripts\install.bat`.

**Spec:** `docs/superpowers/specs/2026-10-09-w1-liblouis-test-probe-design.md` (commit `8b55a67`).

## Global Constraints

- Branch: `fix/w1-liblouis-test-probe` from `main` (`d0ae3b4`). After Task 3, merge with `git merge --no-ff` into `main`; never push, never delete the branch, never rewrite history.
- Files that may change (4 tests, nothing else besides the W-1 docs): `client/tests/test_braille_glue.py` (4 spaces), `client/tests/test_liblouis_runtime.py` (4 spaces), `client/tests/test_translation_language_result.py` (tabs), `client/tests/test_language_detection_translation.py` (tabs). Never edit the generated, git-ignored `client/braille/liblouis/__init__.py` and `client/braille/louis_helper.py`, anything under `vendor/nvda/`, `client/braille/tables/__tables.py` or `client/braille/tables/__init__.py`.
- Never touch the untracked `client2/`, `preprocessing/`, `.sconsign.dblite`, `vendor/nvda/liblouis/dist/`, the user data in `client/dictionary/` or `client/.venv`.
- The checkout uses `core.autocrlf=true`: the index has LF, the working tree CRLF. Edit with an editor that keeps the line ends (MSYS `sed -i` rewrote CRLF to LF and missed a `\r$` anchor in the dry run); `git diff` must show only the intended lines.
- Fixtures: `client/tests/fixtures/translation_golden.json` sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `client/tests/fixtures/dictionary_entries_trace.json` sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf` (LF-normalized), unmodified in `git status`.
- Failures that the newly running real-liblouis tests reveal are recorded in Results, not fixed here.
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
| baseline (`d0ae3b4`) | `Ran 1136`, `FAILED (failures=6, errors=2, skipped=7)` |
| after Task 2 | `Ran 1143` (+2 guard, +5 runtime, +2 real module tests, -2 module skips), `FAILED (failures=7, errors=1, skipped=5)` |

The baseline's two `liblouis bindings unavailable` skips and the `setUpClass (test_liblouis_runtime.LiblouisRuntimeTests)` error disappear. One new failure appears: `test_built_wrapper_loads_bundled_dll`, which never ran on Windows before (Results, R1).

---

### Task 0: Baseline (no commit)

- [x] **Step 1: Branch.**

```bash
git -C $REPO switch -c fix/w1-liblouis-test-probe
```

- [x] **Step 2: Checklist item 4 fails before any test runs.**

```bash
$PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation -v 2>&1 | tail -1
```

Expected:

```text
unittest.case.SkipTest: liblouis bindings unavailable: function 'lou_freeTableFile' not found
```

- [x] **Step 3: Full suite.**

```bash
$PY -m unittest discover -s tests -v 2>&1 | grep -E "ModuleSkipped|^setUpClass|^(FAILED|OK)"
```

Expected:

```text
test_language_detection_translation (unittest.loader.ModuleSkipped.test_language_detection_translation) ... skipped "liblouis bindings unavailable: function 'lou_freeTableFile' not found"
setUpClass (test_liblouis_runtime.LiblouisRuntimeTests) ... ERROR
test_translation_language_result (unittest.loader.ModuleSkipped.test_translation_language_result) ... skipped "liblouis bindings unavailable: function 'lou_freeTableFile' not found"
FAILED (failures=6, errors=2, skipped=7)
```

### Task 1: Guard test (red)

- [x] **Step 1: Add the detector and `LiblouisImportGuardTest` to `client/tests/test_braille_glue.py`**, between `GlueSourceTest` and `TableDirectoryTest` (4 spaces; `ast` and `CLIENT_DIR` already exist in the module):

```python
LIBLOUIS_BINDING = "braille.liblouis"


def _is_liblouis_binding(module: str | None) -> bool:
    return module == LIBLOUIS_BINDING or (module or "").startswith(LIBLOUIS_BINDING + ".")


def direct_liblouis_imports(source: str | bytes) -> list[int]:
    """Line numbers where ``source`` imports ``braille.liblouis`` itself instead of ``braille.louis_helper``."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            hit = any(_is_liblouis_binding(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            hit = node.level == 0 and (
                _is_liblouis_binding(node.module)
                or (node.module == "braille" and any(alias.name == "liblouis" for alias in node.names))
            )
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            hit = (
                name in {"import_module", "__import__"}
                and bool(node.args)
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and _is_liblouis_binding(node.args[0].value)
            )
        else:
            continue
        if hit:
            lines.append(node.lineno)
    return sorted(lines)


class LiblouisImportGuardTest(unittest.TestCase):
    """Tests load the binding only through ``braille.louis_helper`` (W-1).

    The generated binding loads ``liblouis.dll`` by bare name. Imported on its own on
    Windows 11 it gets the older System32 DLL, fails on a missing export, and that DLL
    stays loaded, so every later load in the process (the helper's too) gets it again.
    The helper adds the bundled DLL's directory first.
    """

    def test_detector_flags_every_direct_import_form(self) -> None:
        flagged = [
            ("from braille import liblouis", 1),
            ("from braille import tables, liblouis as louis", 1),
            ("import braille.liblouis", 1),
            ("import os, braille.liblouis as louis", 1),
            ("from braille.liblouis import translateString", 1),
            ("import importlib\nimportlib.import_module('braille.liblouis')", 2),
            ("__import__('braille.liblouis')", 1),
            ("try:\n\tfrom braille import liblouis\nexcept Exception:\n\tpass", 2),
        ]
        for source, line in flagged:
            with self.subTest(source=source):
                self.assertEqual(direct_liblouis_imports(source), [line])
        not_imports = [
            "from braille import louis_helper",
            "from braille.louis_helper import louis",
            "from adapters.translation.liblouis import LiblouisTextTranslator",
            "import braille.tables",
            "import sys\nsys.modules['braille.liblouis'] = object()",
            "assert 'braille.liblouis' not in sys.modules",
        ]
        for source in not_imports:
            with self.subTest(source=source):
                self.assertEqual(direct_liblouis_imports(source), [])

    def test_test_modules_load_liblouis_only_through_louis_helper(self) -> None:
        found = [
            f"{path.name}:{line}"
            for path in sorted((CLIENT_DIR / "tests").glob("*.py"))
            for line in direct_liblouis_imports(path.read_bytes())
        ]

        self.assertEqual(found, [], "import braille.louis_helper and use louis_helper.louis instead")
```

`path.read_bytes()` lets `ast.parse` handle a BOM or coding cookie. The detector does not parse string literals (spec D4).

- [x] **Step 2: Red.**

```bash
$PY -m unittest tests.test_braille_glue.LiblouisImportGuardTest -v 2>&1 | grep -E "^- |^-  |\.\.\. |^(FAILED|OK)"
```

Expected (the detector test passes, the scan lists exactly the three probes):

```text
test_detector_flags_every_direct_import_form (...) ... ok
test_test_modules_load_liblouis_only_through_louis_helper (...) ... FAIL
- ['test_language_detection_translation.py:9',
-  'test_liblouis_runtime.py:19',
-  'test_translation_language_result.py:10'] : import braille.louis_helper and use louis_helper.louis instead
FAILED (failures=1)
```

### Task 2: Probe through the helper (green, commit)

- [x] **Step 1: Module-level probes** (tabs). In both `client/tests/test_translation_language_result.py` and `client/tests/test_language_detection_translation.py`:

```diff
+# Probe through the helper: it adds the bundled DLL's directory first. A bare
+# braille.liblouis import loads System32's older liblouis.dll on Windows 11 (W-1).
 try:
-	from braille import liblouis  # noqa: F401
+	from braille import louis_helper  # noqa: F401
 except Exception as exc:
 	raise unittest.SkipTest(f"liblouis bindings unavailable: {exc}") from exc
```

- [x] **Step 2: `LiblouisRuntimeTests.setUpClass`** (4 spaces) in `client/tests/test_liblouis_runtime.py`:

```diff
     @classmethod
     def setUpClass(cls):
-        from braille import liblouis
+        # Only through the helper: it adds the bundled DLL's directory first (W-1).
         from braille import louis_helper
 
-        cls.louis = liblouis
+        cls.louis = louis_helper.louis
         cls.helper = louis_helper
         cls.helper.initialize()
```

- [x] **Step 3: Green.**

```bash
$PY -m unittest tests.test_braille_glue -v 2>&1 | tail -1
$PY -m py_compile tests/test_braille_glue.py tests/test_liblouis_runtime.py tests/test_translation_language_result.py tests/test_language_detection_translation.py && echo COMPILE_OK
git -C $REPO diff --stat
```

Expected: `OK`, `COMPILE_OK`, and the four test files with `80 +`, `4 +-`, `4 +-`, `4 +-`.

- [x] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_braille_glue.py client/tests/test_liblouis_runtime.py client/tests/test_translation_language_result.py client/tests/test_language_detection_translation.py
git -C $REPO commit -F - <<'EOF'
test: load liblouis only through louis_helper in tests (W-1)

A bare braille.liblouis import loads System32's older liblouis.dll on
Windows 11 and poisons the process; probe through louis_helper, which
adds the bundled DLL's directory first, and guard against direct imports.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 3: Windows verification, results, merge

- [x] **Step 1: Checklist item 4.**

```bash
$PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation -v
```

Expected: `Ran 7 tests`; every test runs (no `SkipTest` traceback, no `setUpClass` error). Record any failure under Results.

- [x] **Step 2: Full suite.**

```bash
$PY -m unittest discover -s tests -v > $TEMP/w1_discover.txt 2>&1; grep -E "skipped|ERROR$|FAIL$" $TEMP/w1_discover.txt; tail -1 $TEMP/w1_discover.txt
```

Expected: the counts in Expected Counts; every failure and error other than R1 is one of the baseline's.

- [x] **Step 3: Fixtures.**

```bash
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO status --short client/tests/fixtures
```

Expected: the two hashes from Global Constraints, no status line.

- [x] **Step 4: Record the results below, commit (`docs: record W-1 verification results`), then merge.**

```bash
git -C $REPO switch main
git -C $REPO merge --no-ff fix/w1-liblouis-test-probe -F - <<'EOF'
merge: liblouis test probe uses louis_helper (W-1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

## Results (2026-10-09, Windows 11, `client\.venv` Python 3.13, implementation commit `e29a835`)

Task 1 red and Task 2 green matched the expected blocks. `py_compile` of the four test files: OK. Fixtures: `e67d95a1...211ccd` and `f493da52...c66c2cf`, `git status` clean for `client/tests/fixtures`.

### Checklist item 4

`Ran 7 tests`, `FAILED (failures=1)`. All seven tests ran on the real liblouis for the first time; six pass (`test_table_resolver_finds_bundled_table`, `test_chinese_default_table_translates`, `test_ueb_grade_1_translates`, `test_ueb_grade_2_translates_and_contracts`, `test_add_blank_between_language_change`, `test_language_detection_translation_consistency`).

- **R1** `test_liblouis_runtime.LiblouisRuntimeTests.test_built_wrapper_loads_bundled_dll`: `AssertionError: Could not determine expected liblouis version from include/liblouis/configure.ac`. A test bug, not a DLL problem: `_expected_liblouis_version` searches `AC_INIT\(\[liblouis\]` case-sensitively, but upstream's `configure.ac` says `AC_INIT([Liblouis], [3.37.0], ...)` (capitalized since liblouis commit `84b1a81e`, 2014). The loaded DLL reports `3.37.0`, which matches; with `re.IGNORECASE` the test would pass. Not fixed here (outside W-1); follow-up.

### Full suite

`Ran 1143 tests`, `FAILED (failures=7, errors=1, skipped=5)` (baseline `Ran 1136`, `failures=6, errors=2, skipped=7`). The two `liblouis bindings unavailable` module skips and the `setUpClass (test_liblouis_runtime.LiblouisRuntimeTests)` error are gone. Every other failure, error and skip is the baseline's:

| Test | Kind | Reason |
| --- | --- | --- |
| `test_liblouis_runtime.LiblouisRuntimeTests.test_built_wrapper_loads_bundled_dll` | FAIL (new: first run) | R1 |
| `test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math` | FAIL (baseline) | known P2-5 case: `['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']` |
| `test_dual_view_browser.DualViewBrowserTest.test_chromium_commands_request_new_window_and_size` | FAIL (baseline) | Windows path: `'C:\\Chrome\\chrome.exe'` vs expected `'C:/Chrome/chrome.exe'` |
| `test_dual_view_browser.DualViewBrowserTest.test_firefox_command_requests_new_window_and_size` | FAIL (baseline) | Windows path: `'C:\\Firefox\\firefox.exe'` vs `'C:/Firefox/firefox.exe'` |
| `test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_dual_view_and_html_export_render_math_with_real_mathml` | FAIL (baseline) | written HTML has `\r\n`, expected `\n` |
| `test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_real_writers_produce_today_bytes` | FAIL (baseline) | `alpha.html` has `\r\n`, expected `\n` |
| `test_liblouis_adapter.LiblouisTextTranslatorTest.test_regular_translation_preserves_native_mapping` | FAIL (baseline) | Windows path join: `'/tables\\en.ctb'` vs `'/tables/en.ctb'` (fake helper, not the DLL) |
| `test_dictionary_name_prompt.DictionaryNamePromptTest.test_case_only_rename_still_renames` | ERROR (baseline) | case-insensitive file system: `FileExistsError: Dictionary 'Alpha' already exists.` |

Skips (5, all baseline, platform): `test_atomic_write.WriteTextAtomicallyTest` `test_a_new_file_gets_the_default_mode_for_the_umask`, `test_a_read_only_file_gets_the_same_verdict_as_writing_it_in_place`, `test_keeps_the_permission_bits_of_an_existing_file`, and `test_document_workspace.MoveDocumentPackageTest.test_case_only_move_keeps_the_permission_bits_of_the_old_package` (all `POSIX permission bits`); `test_dictionary_presenter.PresenterRenameTest.test_rename_case_only_change_renames_file` (`case-insensitive file system`).
