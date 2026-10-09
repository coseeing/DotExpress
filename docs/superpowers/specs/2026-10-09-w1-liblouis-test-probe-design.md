# liblouis Test Probe (W-1) Design

## Goal

Task W-1 makes the real-liblouis tests run on Windows. Three test modules check whether the liblouis binding is available by importing `braille.liblouis` directly. On Windows 11 that import loads the wrong DLL, fails, and leaves the wrong DLL loaded for the rest of the process. As a result, Windows verification checklist item 4 (`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md:258`) never runs the real-liblouis tests: run by name the command stops with an error, and under `discover` the tests are skipped or error out without saying why.

After this task:

- Test modules obtain the binding only through `braille.louis_helper`, the same path production uses. The two module-level probes import the helper (and still raise `unittest.SkipTest` when it cannot load), and `LiblouisRuntimeTests.setUpClass` uses `louis_helper.louis`.
- A guard test fails if any module under `client/tests/` imports `braille.liblouis` directly.

Tests only. No production file, generated file, vendored file, user-visible string, msgid (353) or fixture changes.

## Current State (verified 2026-10-09 on Windows 11, `main` at `d0ae3b4`)

`$PY` is `client\.venv\Scripts\python.exe` (Python 3.13, wxPython). The bundled `client/braille/liblouis.dll` (3.37.0) and its tables were built by `scripts\build-liblouis.bat` and installed by `scripts\install.bat`.

### The two DLLs

- Windows 11 ships a Microsoft-signed `C:\Windows\System32\liblouis.dll` (used by Narrator for braille). It has an older ABI and does not export `lou_freeTableFile` or `lou_freeTableInfo`.
- The generated binding `client/braille/liblouis/__init__.py` (git-ignored, from `scripts\install.bat`) loads the DLL by bare name: `liblouis = _loader["liblouis.dll"]` (`windll` on Windows). It then sets `liblouis.lou_freeTableFile.restype` at line 271.
- `client/braille/louis_helper.py` (git-ignored, generated) imports the binding inside `os.add_dll_directory(BASE_DIR)` (lines 25-31: `with dll_directory: from braille import liblouis as louis`), so the bare name resolves to the bundled DLL. It exposes the module as `louis_helper.louis`.
- The only production importer of the helper is `adapters/translation/provider.py:73` (`from braille import louis_helper`). No production module imports `braille.liblouis` directly (grep over `client/` without `.venv`, `tests` and the generated files).

### The failure

A bare `from braille import liblouis` (no DLL directory added) loads System32's DLL and raises `AttributeError: function 'lou_freeTableFile' not found`. Windows keeps that DLL loaded; every later load of `liblouis.dll` by bare name in the same process, including the one inside the helper's `add_dll_directory`, returns the module already loaded. The whole process is poisoned:

```text
$PY -c "exec('try:\n from braille import liblouis\nexcept AttributeError as e:\n print(e)'); from braille import louis_helper"
-> function 'lou_freeTableFile' not found, then AttributeError from the louis_helper import
$PY -c "from braille import louis_helper; from braille import liblouis; print(liblouis.version())"
-> 3.37.0
```

### The three probes

| Module | Indentation | Probe |
| --- | --- | --- |
| `client/tests/test_translation_language_result.py` | tabs | module level: `try: from braille import liblouis` / `except Exception: raise unittest.SkipTest(...)` |
| `client/tests/test_language_detection_translation.py` | tabs | same |
| `client/tests/test_liblouis_runtime.py` | 4 spaces | `setUpClass`: `from braille import liblouis` before `from braille import louis_helper`; `cls.louis = liblouis` |

Baseline from `client/` with `PYTHONIOENCODING=utf-8`:

- Checklist item 4, `$PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation -v`: no test runs. Loading by name does not catch a module-level `SkipTest`, so the command exits with the traceback `unittest.case.SkipTest: liblouis bindings unavailable: function 'lou_freeTableFile' not found`.
- `$PY -m unittest discover -s tests`: `Ran 1136 tests`, `FAILED (failures=6, errors=2, skipped=7)`. Two of the skips are the module probes (`liblouis bindings unavailable: function 'lou_freeTableFile' not found`) and one error is `setUpClass (test_liblouis_runtime.LiblouisRuntimeTests)`. The other failures and the other error are not related to liblouis (see the plan's results).

### Other test references to `braille.liblouis` (not imports)

- `tests/test_braille_glue.py` puts a fake module into `sys.modules["braille.liblouis"]` and sets `braille.liblouis` as an attribute; it never imports the real binding. A subprocess snippet (line 165) imports only `tests.test_braille_glue`.
- `tests/test_translation_result_core.py:37` has the string `"braille.liblouis"` in a subprocess snippet that asserts the module is **not** imported.
- `tests/test_liblouis_adapter.py` and `tests/test_translation_golden.py` import `adapters.translation.liblouis`, a different module.

## Decisions

- **D1. Tests use the production loading path.** Changing the generated binding (load by full path) or the helper would fix the cause for everyone, but both files are generated (`scripts/sync-nvda.py`, `scripts\install.bat`) and out of scope. Production is already safe because it goes through the helper. The tests are the only code that bypasses it, so they are what changes.
- **D2. The module-level probes import `braille.louis_helper` and keep the `SkipTest` fallback with `except Exception`.** On Linux (no `WINFUNCTYPE`) the existing earlier check still skips; on a checkout without the generated helper the import raises `ModuleNotFoundError` and the module still skips. The message stays `liblouis bindings unavailable: {exc}`. The rest of each module is unchanged: both already translate through `adapters.translation.provider`, which imports the helper.
- **D3. `LiblouisRuntimeTests.setUpClass` imports only the helper** and sets `cls.louis = louis_helper.louis`. The test methods keep using `self.louis` and `self.helper` unchanged.
- **D4. The guard is an AST scan of the import statements** in `client/tests/*.py` (the test package is flat). It reports `ast.Import` of `braille.liblouis` (or a submodule), `ast.ImportFrom` of `liblouis` from `braille` and `ast.ImportFrom` from `braille.liblouis` (or a submodule), plus `importlib.import_module`/`__import__` calls whose first argument is the string `"braille.liblouis"`. It does not parse string literals: the subprocess snippets above only mention the name, and none imports the binding today (grep). Writing to `sys.modules` (the fake in `test_braille_glue.py`) is not an import and is not flagged.
- **D5. Where the guard lives.** `client/tests/test_braille_glue.py`, next to `GlueSourceTest` (that module already AST-checks the glue sources, imports `ast` and defines `CLIENT_DIR`; 4 spaces). It runs on every platform. A small detector test pins each flagged form and the non-flagged look-alikes (`from braille import louis_helper`, `from adapters.translation.liblouis import ...`, `sys.modules["braille.liblouis"] = fake`), so the guard cannot pass by matching nothing.

## Test Plan

New, in `client/tests/test_braille_glue.py`, class `LiblouisImportGuardTest`:

1. `test_detector_flags_every_direct_import_form`: source snippets parsed in memory; the detector returns their line numbers for the flagged forms and nothing for the look-alikes.
2. `test_test_modules_load_liblouis_only_through_louis_helper`: scans every `client/tests/*.py`; expects `[]`. Red before the fix with exactly the three probes (`test_language_detection_translation.py:9`, `test_liblouis_runtime.py:19`, `test_translation_language_result.py:10`).

Changed: the two probes and `setUpClass` (D2, D3). On Windows with the bundled DLL, the three modules then run their 7 real tests (5 + 1 + 1); on Linux they still skip.

## Migration Steps

1. Red: add `LiblouisImportGuardTest`; test 2 fails listing the three probes, test 1 passes.
2. Green: change the three probes. One commit with the guard and the fix.

## Acceptance Criteria

1. `LiblouisImportGuardTest` passes; it failed before the fix with the three probes.
2. Checklist item 4 runs on Windows without the module-level `SkipTest` traceback and without `setUpClass` errors; any test that fails there for another reason (real liblouis behavior) is recorded, not fixed here.
3. `discover` on Windows no longer reports the two `liblouis bindings unavailable` skips or the `setUpClass` error; no new failure appears outside the three modules.
4. Only `client/tests/test_braille_glue.py`, `client/tests/test_liblouis_runtime.py`, `client/tests/test_translation_language_result.py`, `client/tests/test_language_detection_translation.py` and the W-1 docs change. Both fixtures keep their sha256 (`translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`).

## Risks

- A test that runs before the three modules in the same process and imports `braille.liblouis` without the helper would still poison them. The guard covers test modules; production has no such import today (D1).
- With the probes fixed, the real-liblouis tests run on Windows for the first time; failures they reveal are real behavior and are reported, not hidden.

## Out of Scope / Follow-ups

- Making the generated binding itself safe (load `liblouis.dll` by absolute path next to the package, or fail with a clear message when the loaded DLL lacks a symbol). This belongs in the generator (`scripts/sync-nvda.py` / `scripts\install.bat`) and would protect any future direct importer.
- Extending the guard to production modules.
