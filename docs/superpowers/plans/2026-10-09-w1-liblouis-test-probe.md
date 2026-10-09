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

- [ ] **Step 1: Branch.**

```bash
git -C $REPO switch -c fix/w1-liblouis-test-probe
```

- [ ] **Step 2: Checklist item 4 fails before any test runs.**

```bash
$PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation -v 2>&1 | tail -1
```

Expected:

```text
unittest.case.SkipTest: liblouis bindings unavailable: function 'lou_freeTableFile' not found
```

- [ ] **Step 3: Full suite.**

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

- [ ] **Step 1: Add the detector and `LiblouisImportGuardTest` to `client/tests/test_braille_glue.py`**, between `GlueSourceTest` and `TableDirectoryTest` (4 spaces; `ast` and `CLIENT_DIR` already exist in the module):

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

- [ ] **Step 2: Red.**

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

- [ ] **Step 1: Module-level probes** (tabs). In both `client/tests/test_translation_language_result.py` and `client/tests/test_language_detection_translation.py`:

```diff
+# Probe through the helper: it adds the bundled DLL's directory first. A bare
+# braille.liblouis import loads System32's older liblouis.dll on Windows 11 (W-1).
 try:
-	from braille import liblouis  # noqa: F401
+	from braille import louis_helper  # noqa: F401
 except Exception as exc:
 	raise unittest.SkipTest(f"liblouis bindings unavailable: {exc}") from exc
```

- [ ] **Step 2: `LiblouisRuntimeTests.setUpClass`** (4 spaces) in `client/tests/test_liblouis_runtime.py`:

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

- [ ] **Step 3: Green.**

```bash
$PY -m unittest tests.test_braille_glue -v 2>&1 | tail -1
$PY -m py_compile tests/test_braille_glue.py tests/test_liblouis_runtime.py tests/test_translation_language_result.py tests/test_language_detection_translation.py && echo COMPILE_OK
git -C $REPO diff --stat
```

Expected: `OK`, `COMPILE_OK`, and the four test files with `80 +`, `4 +-`, `4 +-`, `4 +-`.

- [ ] **Step 4: Commit.**

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

- [ ] **Step 1: Checklist item 4.**

```bash
$PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation -v
```

Expected: `Ran 7 tests`; every test runs (no `SkipTest` traceback, no `setUpClass` error). Record any failure under Results.

- [ ] **Step 2: Full suite.**

```bash
$PY -m unittest discover -s tests -v > $TEMP/w1_discover.txt 2>&1; grep -E "skipped|ERROR$|FAIL$" $TEMP/w1_discover.txt; tail -1 $TEMP/w1_discover.txt
```

Expected: the counts in Expected Counts; every failure and error other than R1 is one of the baseline's.

- [ ] **Step 3: Fixtures.**

```bash
git -C $REPO show HEAD:client/tests/fixtures/translation_golden.json | sha256sum
git -C $REPO show HEAD:client/tests/fixtures/dictionary_entries_trace.json | sha256sum
git -C $REPO status --short client/tests/fixtures
```

Expected: the two hashes from Global Constraints, no status line.

- [ ] **Step 4: Record the results below, commit (`docs: record W-1 verification results`), then merge.**

```bash
git -C $REPO switch main
git -C $REPO merge --no-ff fix/w1-liblouis-test-probe -F - <<'EOF'
merge: liblouis test probe uses louis_helper (W-1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

## Results

Filled in by Task 3.
