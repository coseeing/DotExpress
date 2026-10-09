# Windows Test Portability (W-2) Design

## Goal

Task W-2 removes the six test failures that `python -m unittest discover -s tests` reports on Windows 11 only because the tests hard-code POSIX behavior (or, in one case, the wrong letter case). In each case production behaves exactly as it did before the refactor (baseline `6e5819f`); only the expectation is wrong. After this task each expectation is written so it holds on both Windows and POSIX, and Linux CI keeps passing.

Tests only. No production file, generated file, vendored file, user-visible string, msgid or fixture changes.

## Current State (verified 2026-10-09 on Windows 11, `main` at `9a4ae81`)

`$PY` is `client\.venv\Scripts\python.exe` (Python 3.13). From `client/` with `PYTHONIOENCODING=utf-8`, `discover -s tests` reports `Ran 1143`, `FAILED (failures=7, errors=1, skipped=5)` (W-1 results). Six of those failures are in scope:

| # | Test | Actual on Windows | Expected by the test |
| --- | --- | --- | --- |
| 1 | `test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_real_writers_produce_today_bytes` | `alpha.html` bytes use `\r\n` | `\n` |
| 2 | `test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_dual_view_and_html_export_render_math_with_real_mathml` | same | `\n` |
| 3 | `test_dual_view_browser.DualViewBrowserTest.test_chromium_commands_request_new_window_and_size` | `C:\Chrome\chrome.exe` | `C:/Chrome/chrome.exe` |
| 4 | `test_dual_view_browser.DualViewBrowserTest.test_firefox_command_requests_new_window_and_size` | `C:\Firefox\firefox.exe` | `C:/Firefox/firefox.exe` |
| 5 | `test_liblouis_adapter.LiblouisTextTranslatorTest.test_regular_translation_preserves_native_mapping` | `/tables\en.ctb` | `/tables/en.ctb` |
| 6 | `test_liblouis_runtime.LiblouisRuntimeTests.test_built_wrapper_loads_bundled_dll` | `Could not determine expected liblouis version` | version from `configure.ac` |

### Baseline evidence (production unchanged since `6e5819f`)

- **1, 2.** `documents/formats.py` `_write_html` writes with `Path.write_text(html, encoding="utf-8")` now (line 108) and at `6e5819f` (line 93). `write_text` opens the file in text mode with `newline=None`, so every `\n` becomes `os.linesep`. Running the `6e5819f` writer from a `git archive` copy on Windows writes CRLF only (no bare LF). The tests compare against `render_dual_view_html(...).encode("utf-8")`, which has `\n`. Both tests were added after `6e5819f`; their expectation, not the writer, is POSIX-only.
- **3, 4.** `dual_view/browser.py` `build_browser_command` is byte-identical at `6e5819f` and returns `str(executable)`. On Windows `str(Path("C:/Chrome/chrome.exe"))` is `C:\Chrome\chrome.exe`, the native form `subprocess.Popen` expects. The `6e5819f` copy of `tests/test_dual_view_browser.py` fails the same two tests on Windows.
- **5.** `adapters/translation/liblouis.py` is identical at `6e5819f` and joins with `os.path.join(self._tables_dir, table)`. The `6e5819f` copy of `tests/test_liblouis_adapter.py` fails the same way on Windows. The helper is a fake; the real liblouis accepts either separator on Windows.
- **6.** The test reads `include/liblouis/configure.ac` with `AC_INIT\(\[liblouis\]` (case-sensitive; same regex at `6e5819f`). The submodule is `2aa5f84b` (`v3.37.0`) at both commits and says `AC_INIT([Liblouis], [3.37.0], ...)`; the capital `L` dates from liblouis commit `84b1a81e`. The bundled DLL reports `3.37.0`. No production code is involved; the test never ran on Windows before W-1.

## Decisions

- **D1. Expectations follow the platform, not a constant.** Each fix derives the expected value with the same standard-library rule production relies on, so the test passes on both platforms and still pins the exact value:
  - 1, 2: a module helper `text_file_bytes(text)` returns `text.replace("\n", os.linesep).encode("utf-8")`, the bytes `write_text(text, encoding="utf-8")` produces. Used for `alpha.html`, `beta.html` and the math export. On POSIX `os.linesep == "\n"`, so the expectation is unchanged there.
  - 3, 4: expect `str(Path("C:/Chrome/chrome.exe"))` (and the Edge and Firefox equivalents). On POSIX that is `C:/Chrome/chrome.exe`, unchanged.
  - 5: expect `os.path.join("/tables", "en.ctb")`. On POSIX that is `/tables/en.ctb`, unchanged.
  - 6: add `re.IGNORECASE` to the `AC_INIT` search. The class is Windows-only (`skipUnless win32`), but the regex is platform-independent.
- **D2. No production change.** Writing HTML with `newline="\n"`, normalizing executable paths or joining table paths with `/` would change today's Windows behavior; that is out of scope and not needed (nothing reported it as a defect).
- **D3. One commit per cause** (HTML line ends, browser paths, table path join, configure.ac case), each touching one test file.

## Acceptance Criteria

1. The six tests pass individually on Windows.
2. `discover -s tests` on Windows: `Ran 1143`, `FAILED (failures=1, errors=1, skipped=5)`. The remaining failure and error are the out-of-scope `test_conversion_service...test_translate_with_language_does_not_duplicate_existing_spaces_around_math` (P2-5 decision) and `test_dictionary_name_prompt...test_case_only_rename_still_renames` (known defect on case-insensitive file systems); the skips are the five platform skips.
3. Only `client/tests/test_gui_document_flows.py`, `client/tests/test_dual_view_browser.py`, `client/tests/test_liblouis_adapter.py`, `client/tests/test_liblouis_runtime.py` and the W-2 docs change. Both fixtures keep their sha256 (`translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, `dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`).

## Out of Scope

- The P2-5 spacing case and the case-only dictionary rename defect (above).
- Deciding whether exported HTML should use LF on every platform.
