# Translation Result Layout (P1-5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the alignment value object and the dual-view handoff cheap and acyclic without changing any output. `TranslationResult` keeps its punctuation sets and CJK language blocks as immutable class attributes (an instance holds only its four lists), `TranslationResult.concat` merges any number of results in one pass (`merge_translation_results` and `+` both use it), `__eq__` returns `NotImplemented` for other types, `DualViewSegment` moves to `conversion/output.py`, and `build_dual_view_model` takes the MathML converter as a required keyword argument, so `conversion` no longer imports `dual_view` and `dual_view` no longer imports `conversion` or `config` at runtime. The `translate` re-import in `tests/test_translation_result_core.py` (M-1) is replaced by a subprocess check, which removes the only order-dependent failure of the suite. Byte-identical braille, wrap, alignment and dual-view output; no user-facing string changes; `.po`/`.mo` untouched.

**Architecture:** Seven commits in the spec's order. Task 1 fixes the test-order pollution first, so that every later step is checked in shuffled order. Task 2 adds the safety net on unchanged production code: a golden fixture over realistic mixed input (real adapters with a deterministic fake liblouis helper and a fake MathCAT callable), plus merge-semantics, constant-value and real-MathML wiring tests. Tasks 3-7 each start with a failing test, then change production code; the golden fixture written in Task 2 never changes again.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `subprocess`, `types.MappingProxyType`, `dataclasses`, `hashlib`, `json`). wxPython is not installed; `gui` loads through the P0-4 `tests/wx_stub.py` scope that `tests/test_gui_document_flows.py` already uses. liblouis and MathCAT load only on Windows; on Linux the golden test drives the real `LiblouisTextTranslator` and `MathCATMathTranslator` with fakes.

**Spec:** `docs/superpowers/specs/2026-10-08-p1-5-translation-result-layout-design.md` (authoritative, commit `3d54241`). Corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p1-5-translation-result-layout`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (19, nothing else): production `client/translate.py`, `client/conversion/wrapping.py`, `client/conversion/preprocessing/literal_braille.py`, `client/conversion/output.py`, `client/conversion/service.py`, `client/dual_view/model.py`, `client/dual_view/__init__.py`, `client/gui.py`, `client/documents/formats.py`; tests `test_translation_golden.py` (new), `fixtures/translation_golden.json` (new, generated), `test_translation_result_core.py`, `test_conversion_language_explicit.py`, `test_conversion_service.py`, `test_translation_import_isolation.py`, `test_gui_document_flows.py`, `test_dual_view_model.py`, `test_dual_view_html.py`, `test_document_formats.py`. Never touch `client/locales/`, `scripts/`, `client/braille/`, `tests/test_translation_result.py` (P2-5) or the Windows-only test modules.
- Indentation per file, unchanged: TABS in `translate.py`, `gui.py`, `dual_view/model.py`, `tests/test_dual_view_model.py`, `tests/test_dual_view_html.py`; 4 spaces everywhere else. The patches carry the exact characters; run every block as it is, do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- The golden fixture is generated once, in Task 2, by `python -m tests.test_translation_golden --write`, and its sha256 is checked after every later task. Never regenerate it after Task 2; if `tests.test_translation_golden` fails in Tasks 3-7, the production change is wrong.
- New test text is ASCII except braille cells, CJK sample text and the CJK punctuation that the surrounding tests already use; the full-width punctuation in the constant test is written as `\u` escapes.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run. Timings are stripped with `sed`, so the blocks are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p15impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. Python is the venv's 3.14.4.
- Baseline (re-verified at `3d54241`, the spec commit; code identical to `7095265`): `$PY -m unittest discover -s tests` gives `Ran 754 tests`, `FAILED (failures=1, skipped=9)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: the scale backstop as specified barely separates old from new code.** The spec merges 20,000 one-token results under a 5 s bound and says the old pairwise loop "needs well over a minute (extrapolated from the 8,000-segment measurement)". That measurement used 10-token segments. Measured on this box with one-token results, the old loop takes 11.5 s (and the new merge 0.02 s), so a machine 2.5 times faster would let the old code pass. The plan merges 20,000 ten-token results (200,000 tokens), the shape of the spec's own measurement: the old loop took 162 s here (8,000 ten-token segments: 22.1 s, the spec measured 15.3 s), the new merge 0.06 s. The bound stays 5 s: about 80 times the new time, and the old code needs more than 30 times the bound. The structural tests (one `__init__`, no `__add__`, 500 results) stay the primary guard; the red step of Task 5 runs only those, because the old code needs minutes for the scale test.
2. **Factual correction: the module-level imports do change two standalone import closures.** The spec says "Neither move changes any import closure". Measured: `import conversion.wrapping` and `import conversion.preprocessing.literal_braille`, each alone in a fresh interpreter, now also load `translate`, `languageDetection`, `languageDetection.blocks` and `languageDetection.unicode_blocks` (all pure Python, no native code). Every production path that reaches these modules (`conversion.service`, `conversion.text.pipeline`, the adapters) already loads `translate` through `adapters.translation.contracts`, so no production closure changes, and `test_platform_neutral_modules_do_not_load_native_modules` stays green. Also measured: `import conversion.service` stops loading `conversion.math_service` (it came in through `dual_view.model`); nothing relies on that, because `adapters.translation.provider` imports it lazily and, after Task 7, `gui` and `documents.formats` import it directly. `import documents.formats` loads exactly the same modules before and after.
3. **Refinement: fixture layout.** The dual-view segments, the merged and post-processed lists, `translate_with_language`'s lists, the dual-view model and the HTML digest do not depend on the width or the output mode. The fixture stores them once per input under `conversion`, and the test recomputes and compares them on every run (so the "read after the wrap" check still runs at every width); only `display_text` and the two wrap strings are stored per run. The long document (the five short inputs joined by blank lines, 12 times: 360 segments, spec minimum 300) stores its width-independent parts as SHA-256 digests of their canonical JSON plus `dual_view_segment_count`; stored in full it alone would be about 1 MB. Result: 189,305 bytes, 6,652 lines, sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, identical under `PYTHONHASHSEED` 0-3.
4. **Refinement: regeneration entry point.** `python -m tests.test_translation_golden --write` rewrites the fixture; without `--write` the module runs its tests like every other test module. The module docstring says the fixture must only be regenerated for an intended output change.
5. **Refinement: test placement and names.** Parts A2, A4, B, C and D live in `tests/test_translation_result_core.py` (classes `TranslationResultCoreTest`, `SharedConstantsTest`, `EqualityTest`, `MergeTranslationResultsTest`, `LinearMergeTest`). A2 also pins that `a + b` does not alias either operand and keeps its `TypeError`. A3 is one test, `test_dual_view_and_html_export_render_math_with_real_mathml`, in `DocumentMenuAndExportCharacterizationTest` next to the existing export byte tests; it checks the window HTML and the exported bytes against the same expected string (with non-empty results the `empty_message` does not appear, so the window and the export render the same bytes). The E guard for `dual_view` reports any `conversion` or `conversion.*` module and `config`; the E guard for `conversion` reports any `dual_view` or `dual_view.*` module. The required-converter test asserts `TypeError` matching `mathml_converter`.
6. **Refinement: red steps.** Task 1's red is the explicit-language fakes switched to a module-level import: with the old core test run first they error (`TypeError: not TranslateResult object`), which is the M-1 pollution itself; the subprocess rewrite turns them green. Task 2 is characterization and cannot be red; instead `$T/tools/golden_mutants.py` shows the net catches three deliberate breakages (6, 16 and 26 failures). In Task 7 the 20 call-site updates go into the red step (the keyword is already accepted), so the green step touches production files only.
7. **Refinement: helper name.** Text-only dual-view tests pass `reject_mathml`, a module function in `test_dual_view_model.py` and `test_dual_view_html.py` that raises `AssertionError`; the four `test_gui_document_flows.py` export comparisons pass `latex_to_mathml`.

Everything else in the spec was re-checked at `3d54241`: the M-1 reproduction (`errors=8`, 23 tests) and the 20 baseline shuffle seeds (seeds 0, 1, 3, 4, 5, 10, 12, 13 `errors=8`, the rest `failures=1`); the three dead helpers in `test_conversion_service.py` (no caller); the 20 converter-less `build_dual_view_model` calls (13 + 3 + 4) and that none of them builds a math segment; the 12 punctuation sets and their read sites; the five `DualViewSegment` test importers; `tests.test_translation_result` collecting 0 tests under `unittest` and giving 8 passes and 5 failures (2 `IndexError`, 3 `AssertionError`) when its functions are called directly, before and after.

## Dry Run

The whole plan was executed red-first on a scratch clone of the branch at `3d54241` (`$SP/p15plan/dry`, never the repo), one commit per task; after each task the full suite gave the counts below, and after Task 7 the 20 shuffle seeds, the msgid scan and every acceptance criterion passed. The patches in this file are `git diff`s of those commits, split into the red test step and the implementation step. Then this file's blocks were run in order on fresh clones (`$SP/p15plan/replay1`, `replay2`, each with a stand-in plan commit) by a harness that compares every "Expected" block with the real output: all 7 commits applied, every expected block matched byte for byte, and the resulting `client/` tree is identical to the dry clone. Final sha256: `client/translate.py` `12da34e9bfe4928811ae4397caae300220f86ec8821958099f4686daab394639`, `client/dual_view/model.py` `a20ca13e04c65082b06e9f62648f8925e4d9ed30549cb430ba462bc79002bcf3`, `client/tests/test_translation_golden.py` `3fc2ab660a1503335d2473c5566aee2b9789df9f9b6ff6c04a63af6e00795a4d`, `client/tests/fixtures/translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`.

## Review Focus

1. **Same output.** The golden fixture is generated from unchanged code in Task 2 and checked unchanged after Tasks 3-7 (sha256 and `tests.test_translation_golden`). It covers language switches, boundary spaces, contractions (`bind_contracted_tokens`), end-of-run blank trimming (`reclean_braille_endspace`), inserted spaces between `）（` and `」『` (`reclean_token`), a hard newline, blank lines and leading spaces, a literal-braille dictionary entry, an escaped dollar, inline math with and without surrounding spaces, widths 1/10/24/40 and the ASCII mode, plus a 360-segment document.
2. **No aliasing in the merge.** `concat` builds four new lists even for zero or one input; `reclean_braille_endspace` on the merged result must never touch a cached dual-view segment. Tests: `test_merging_one_result_copies_its_lists`, `test_post_processing_the_merged_result_leaves_one_input_unchanged`, `test_mutating_the_merged_result_leaves_every_input_unchanged`, and the golden snapshot, which reads the segments after the wrap and the post-processing (mutant "wrap merges into the first segment": 26 failures).
3. **Shared constants are immutable.** `frozenset` and a `MappingProxyType` of tuples; `bind_word_tokens`, `reclean_token` and `wrap` read them unchanged (`set(self.LEFT_PUNCT) | set("—")` and `self.RIGHT_PUNCT_FULL | self.END_SENTENCE_PUNCT_FULL` give equal sets; `language_has_all` wraps `.get(lang, [])` in `set`).
4. **Equality.** `NotImplemented` for other types (so `==` is `False`, `!=` is `True`); `__hash__ = None` is explicit.
5. **Dependency direction.** `conversion` produces `DualViewSegment`; `dual_view` names it only under `TYPE_CHECKING`; `gui` and `documents.formats` pass `latex_to_mathml`. Subprocess guards in `test_translation_import_isolation.py`; A3 pins that the window and the export still use the real converter.
6. **Test-order independence.** One `TranslationResult` class per process: no test pops or reloads `translate` any more, and `conversion.wrapping` binds the class at import time. 20 shuffled seeds after Task 1 and after Task 7.

## File Map

- Task 1: modify `client/tests/test_conversion_language_explicit.py`, `client/tests/test_translation_result_core.py`, `client/tests/test_conversion_service.py`.
- Task 2: create `client/tests/test_translation_golden.py`, `client/tests/fixtures/translation_golden.json` (generated); modify `client/tests/test_translation_result_core.py`, `client/tests/test_gui_document_flows.py`.
- Task 3: modify `client/translate.py`, `client/tests/test_translation_result_core.py`.
- Task 4: modify `client/translate.py`, `client/tests/test_translation_result_core.py`.
- Task 5: modify `client/translate.py`, `client/conversion/wrapping.py`, `client/conversion/preprocessing/literal_braille.py`, `client/tests/test_translation_result_core.py`.
- Task 6: modify `client/conversion/output.py`, `client/conversion/service.py`, `client/dual_view/model.py`, `client/dual_view/__init__.py`, tests `test_translation_import_isolation`, `test_conversion_service`, `test_document_formats`, `test_dual_view_html`, `test_dual_view_model`, `test_gui_document_flows`.
- Task 7: modify `client/dual_view/model.py`, `client/gui.py`, `client/documents/formats.py`, tests `test_translation_import_isolation`, `test_dual_view_model`, `test_dual_view_html`, `test_gui_document_flows`.

## Expected Counts

| After task | new tests | `discover` `Ran` |
| --- | --- | --- |
| baseline | - | 754 |
| 1 test isolation | 0 | 754 |
| 2 characterization | 17 (7 golden, 9 core, 1 gui) | 771 |
| 3 shared constants | 3 | 774 |
| 4 equality | 3 | 777 |
| 5 linear merge | 3 | 780 |
| 6 `DualViewSegment` move | 1 | 781 |
| 7 MathML converter | 2 | 783 |

Every row: `FAILED (failures=1, skipped=9)`, the one failure being the P2-5 case. From Task 2 on, the fixture sha256 is `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`.

## Throwaway Tooling (not committed)

Written to `$T/tools/` in Task 0, outside the repo:

- `run_pytest_style.py <module>`: calls the module-level `test_*` functions of a pytest-style module directly (for `tests.test_translation_result`, which `unittest` does not collect).
- `golden_mutants.py "<mutant>"`: runs `tests.test_translation_golden` against a deliberately broken `TranslationResult` or merge, to prove the net can fail.
- Existing: `$SP/p12/tools/msgid_scan.py` (the P0-5 AST stand-in for xgettext; source also in the Appendix of `docs/superpowers/plans/2026-10-08-p0-5-i18n.md`) and `$SP/shuffle_harness.py <seed>` (runs every test module in a seeded random order, one process).

---

### Task 0: Record the baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -1
git -C $REPO branch --show-current
```

Expected (no output from `status`; HEAD is the plan commit):

```text
docs: plan translation result layout
refactor/p1-5-translation-result-layout
```

- [ ] **Step 2: Create the tools and record the baseline.**

```bash
mkdir -p $T/tools
cat > $T/tools/run_pytest_style.py <<'EOF'
"""Call the module-level test_* functions of a pytest-style test module directly (throwaway, P1-5).

Usage (from client/): python run_pytest_style.py tests.test_translation_result
Prints one line per function (ok or the exception type) and a summary.
"""
import importlib
import inspect
import sys

sys.path.insert(0, ".")
module = importlib.import_module(sys.argv[1])
passed = failed = 0
for name, function in sorted(inspect.getmembers(module, inspect.isfunction)):
    if not name.startswith("test_") or function.__module__ != module.__name__:
        continue
    try:
        function()
    except Exception as error:  # noqa: BLE001 - report every failure type
        failed += 1
        print(f"{name}: {type(error).__name__}")
    else:
        passed += 1
        print(f"{name}: ok")
print(f"passed={passed} failed={failed}")
EOF
cat > $T/tools/golden_mutants.py <<'EOF'
"""Run tests.test_translation_golden against deliberately broken code (throwaway, P1-5; from client/)."""
import io
import sys
import unittest

sys.path.insert(0, ".")
import translate

TR = translate.TranslationResult


def in_place_merge(translations):
    merged = translations[0]
    for segment in translations[1:]:
        raw_offset = len(merged.raw)
        braille_offset = len(merged.braille)
        merged.raw.extend(segment.raw)
        merged.braille.extend(segment.braille)
        merged.braille_to_raw_pos.extend(pos + raw_offset for pos in segment.braille_to_raw_pos)
        merged.raw_to_braille_pos.extend(pos + braille_offset for pos in segment.raw_to_braille_pos)
    return merged


MUTANTS = {
    "reclean_token is a no-op": ("reclean_token", lambda self: None),
    "bind_contracted_tokens is a no-op": ("bind_contracted_tokens", lambda self: None),
    "wrap merges into the first segment": (None, in_place_merge),
}
name = sys.argv[1]
attribute, replacement = MUTANTS[name]
if attribute is None:
    import conversion.wrapping

    conversion.wrapping.merge_translation_results = replacement
else:
    setattr(TR, attribute, replacement)
suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_translation_golden")
result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
print(f"{name}: ran={result.testsRun} failures={len(result.failures)} errors={len(result.errors)}")
EOF
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -I $SP/p12/tools/msgid_scan.py $REPO/client --save $T/base_msgids.json | grep -E '^source'
$PY -B $T/tools/run_pytest_style.py tests.test_translation_result > $T/pytest_style_before.txt
cat $T/pytest_style_before.txt
```

Expected (the P2-5 failure; 353 source msgids; `tests.test_translation_result` 8 passes and 5 failures when called directly):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 754 tests
FAILED (failures=1, skipped=9)
source msgids: 353
test_bind_contracted_tokens_merges_source_characters_with_one_braille_cell: ok
test_bind_word_tokens_complex: ok
test_bind_word_tokens_lead_punct: IndexError
test_bind_word_tokens_lead_punct_continue: IndexError
test_bind_word_tokens_left_right_continue: ok
test_bind_word_tokens_left_right_continue2: ok
test_bind_word_tokens_tail_punct: ok
test_bind_word_tokens_tail_punct_continue: ok
test_end_right_end_sentence_blank: ok
test_end_right_end_sentence_blank2: AssertionError
test_end_right_end_sentence_blank3: AssertionError
test_remove_start_line_blank: AssertionError
test_remove_start_line_blank2: ok
passed=8 failed=5
```

- [ ] **Step 3: Reproduce M-1 and record the shuffled baseline.**

```bash
$PY -m unittest tests.test_translation_result_core tests.test_conversion_service 2>&1 | grep -E '^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
for s in $(seq 0 19); do $PY -B -I $SP/shuffle_harness.py $s | head -1; done
```

Expected (8 errors when the core module runs first; eight seeds show the same 8 errors, the other twelve only the P2-5 failure):

```text
Ran 23 tests
FAILED (errors=8)
seed=0 ran=754 failures=0 errors=8 skipped=9
seed=1 ran=754 failures=0 errors=8 skipped=9
seed=2 ran=754 failures=1 errors=0 skipped=9
seed=3 ran=754 failures=0 errors=8 skipped=9
seed=4 ran=754 failures=0 errors=8 skipped=9
seed=5 ran=754 failures=0 errors=8 skipped=9
seed=6 ran=754 failures=1 errors=0 skipped=9
seed=7 ran=754 failures=1 errors=0 skipped=9
seed=8 ran=754 failures=1 errors=0 skipped=9
seed=9 ran=754 failures=1 errors=0 skipped=9
seed=10 ran=754 failures=0 errors=8 skipped=9
seed=11 ran=754 failures=1 errors=0 skipped=9
seed=12 ran=754 failures=0 errors=8 skipped=9
seed=13 ran=754 failures=0 errors=8 skipped=9
seed=14 ran=754 failures=1 errors=0 skipped=9
seed=15 ran=754 failures=1 errors=0 skipped=9
seed=16 ran=754 failures=1 errors=0 skipped=9
seed=17 ran=754 failures=1 errors=0 skipped=9
seed=18 ran=754 failures=1 errors=0 skipped=9
seed=19 ran=754 failures=1 errors=0 skipped=9
```

---

### Task 1: Run the `translate` import check in a subprocess (M-1)

**Files:**
- Modify: `client/tests/test_conversion_language_explicit.py`, `client/tests/test_translation_result_core.py`, `client/tests/test_conversion_service.py`

- [ ] **Step 1: Write the failing test.** The explicit-language fakes import `TranslationResult` at module level and the workaround comment goes. This is the regression proof for M-1: while `test_import_does_not_import_liblouis_helper` re-imports `translate`, results built by these fakes use the old class and the merge rejects them.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_language_explicit.py b/client/tests/test_conversion_language_explicit.py
index 1e05ec6..a3da26a 100644
--- a/client/tests/test_conversion_language_explicit.py
+++ b/client/tests/test_conversion_language_explicit.py
@@ -8,6 +8,7 @@ from unittest.mock import patch
 import config
 from adapters.translation.contracts import TranslationRuntime
 from conversion.service import ConversionRequest, convert_text_with_alignment
+from translate import TranslationResult
 
 
 TABLES = {
@@ -26,15 +27,11 @@ MIXED_TEXT_CALLS = [
 ]
 
 
-# The fakes import TranslationResult per call: tests.test_translation_result_core
-# re-imports `translate`, and the wrapping step only accepts the current class.
 class RecordingTextTranslator:
     def __init__(self) -> None:
         self.calls = []
 
     def translate(self, text, *, table, raw, single_token=False):
-        from translate import TranslationResult
-
         self.calls.append((text, table))
         braille = list(f"T[{text}]")
         return TranslationResult([raw], braille, [0] * len(braille), [0])
@@ -45,8 +42,6 @@ class RecordingMathTranslator:
         self.calls = []
 
     def translate(self, source, *, braille_code, language):
-        from translate import TranslationResult
-
         self.calls.append((source, braille_code, language))
         braille = list(f"M[{source}]")
         return TranslationResult([source], braille, [0] * len(braille), [0])
PATCH
```

- [ ] **Step 2: Run it and watch it fail.**

```bash
$PY -m unittest tests.test_translation_result_core tests.test_conversion_language_explicit 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (3 errors: one test and two subtests):

```text
ERROR: test_non_detecting_text_follows_request_language (tests.test_conversion_language_explicit.ConversionLanguageTest.test_non_detecting_text_follows_request_language) (lang='en')
TypeError: not TranslateResult object
ERROR: test_non_detecting_text_follows_request_language (tests.test_conversion_language_explicit.ConversionLanguageTest.test_non_detecting_text_follows_request_language) (lang='zh_TW')
TypeError: not TranslateResult object
ERROR: test_same_request_gives_same_output_in_any_environment (tests.test_conversion_language_explicit.ConversionLanguageTest.test_same_request_gives_same_output_in_any_environment)
TypeError: not TranslateResult object
Ran 5 tests
FAILED (errors=3)
```

- [ ] **Step 3: Run the check in a fresh interpreter and drop the dead helpers.** `test_import_does_not_import_liblouis_helper` runs the same assertions in `subprocess.run([sys.executable, "-c", script])` (the pattern of `tests/test_translation_import_isolation.py`) and no longer touches `sys.modules`; the module imports `TranslationResult` once at module level. `test_conversion_service.py` loses `_fake_translate_module`, `_mutating_translate_module`, `_translation_result` and the `ModuleType` import (no caller).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_service.py b/client/tests/test_conversion_service.py
index 5e368d2..cc37749 100644
--- a/client/tests/test_conversion_service.py
+++ b/client/tests/test_conversion_service.py
@@ -2,7 +2,6 @@ import csv
 import tempfile
 import unittest
 from pathlib import Path
-from types import ModuleType
 
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
@@ -98,73 +97,6 @@ class ConversionServiceTest(unittest.TestCase):
             math_translator=math_translator or FakeMathTranslator(),
         )
 
-    def _fake_translate_module(self) -> ModuleType:
-        fake_module = ModuleType("translate")
-
-        class FakeTranslationResult:
-            def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
-                self.raw = raw
-                self.braille = braille
-                self.braille_to_raw_pos = braille_to_raw_pos
-                self.raw_to_braille_pos = raw_to_braille_pos
-
-            def __add__(self, other):
-                raw_offset = len(self.raw)
-                braille_offset = len(self.braille)
-                return FakeTranslationResult(
-                    self.raw + other.raw,
-                    self.braille + other.braille,
-                    list(self.braille_to_raw_pos) + [pos + raw_offset for pos in other.braille_to_raw_pos],
-                    list(self.raw_to_braille_pos) + [pos + braille_offset for pos in other.raw_to_braille_pos],
-                )
-
-        fake_module.TranslationResult = FakeTranslationResult
-        fake_module.translate = lambda *_args, **_kwargs: None
-        fake_module.translate_as_single_token = lambda *_args, **_kwargs: None
-        return fake_module
-
-    def _mutating_translate_module(self) -> ModuleType:
-        fake_module = ModuleType("translate")
-
-        class MutatingTranslationResult:
-            def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
-                self.raw = raw
-                self.braille = braille
-                self.braille_to_raw_pos = braille_to_raw_pos
-                self.raw_to_braille_pos = raw_to_braille_pos
-
-            def __add__(self, other):
-                raw_offset = len(self.raw)
-                braille_offset = len(self.braille)
-                return MutatingTranslationResult(
-                    self.raw + other.raw,
-                    self.braille + other.braille,
-                    list(self.braille_to_raw_pos) + [pos + raw_offset for pos in other.braille_to_raw_pos],
-                    list(self.raw_to_braille_pos) + [pos + braille_offset for pos in other.raw_to_braille_pos],
-                )
-
-            def reclean_braille_endspace(self):
-                return None
-
-            def bind_word_tokens(self):
-                self.raw = ["".join(self.raw)]
-                self.raw_to_braille_pos = [0]
-                self.braille_to_raw_pos = [0] * len(self.braille)
-
-            def reclean_token(self):
-                return None
-
-            def wrap(self, _width):
-                return "".join(self.braille), "".join(self.raw)
-
-        fake_module.TranslationResult = MutatingTranslationResult
-        return fake_module
-
-    def _translation_result(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
-        from translate import TranslationResult
-
-        return TranslationResult(raw, braille, braille_to_raw_pos, raw_to_braille_pos)
-
     def test_empty_source_does_not_read_or_execute_preprocessing_script(self) -> None:
         dictionary_dir = self.test_dir / "dictionary"
         dictionary_dir.mkdir()
diff --git a/client/tests/test_translation_result_core.py b/client/tests/test_translation_result_core.py
index 28c5402..4d6d8b2 100644
--- a/client/tests/test_translation_result_core.py
+++ b/client/tests/test_translation_result_core.py
@@ -1,25 +1,31 @@
-import importlib
+import subprocess
 import sys
 import unittest
 
+from translate import TranslationResult
+
 
 class TranslationResultCoreTest(unittest.TestCase):
     def test_import_does_not_import_liblouis_helper(self) -> None:
-        sys.modules.pop("translate", None)
-        sys.modules.pop("braille.louis_helper", None)
-        sys.modules.pop("braille.liblouis", None)
-
-        module = importlib.import_module("translate")
-
-        self.assertNotIn("braille.louis_helper", sys.modules)
-        self.assertNotIn("braille.liblouis", sys.modules)
-        self.assertTrue(hasattr(module, "TranslationResult"))
-        self.assertFalse(hasattr(module, "translate"))
-        self.assertFalse(hasattr(module, "translate_as_single_token"))
+        script = """
+import sys
+import translate
+assert "braille.louis_helper" not in sys.modules, "braille.louis_helper was imported"
+assert "braille.liblouis" not in sys.modules, "braille.liblouis was imported"
+assert hasattr(translate, "TranslationResult")
+assert not hasattr(translate, "translate")
+assert not hasattr(translate, "translate_as_single_token")
+"""
+        completed = subprocess.run(
+            [sys.executable, "-c", script],
+            check=False,
+            capture_output=True,
+            text=True,
+        )
+
+        self.assertEqual(completed.returncode, 0, completed.stderr)
 
     def test_addition_offsets_both_position_arrays(self) -> None:
-        from translate import TranslationResult
-
         left = TranslationResult(["a"], ["⠁"], [0], [0])
         right = TranslationResult(["b"], ["⠃"], [0], [0])
 
@@ -31,8 +37,6 @@ class TranslationResultCoreTest(unittest.TestCase):
         self.assertEqual(result.raw_to_braille_pos, [0, 1])
 
     def test_empty_result_has_empty_mapping(self) -> None:
-        from translate import TranslationResult
-
         result = TranslationResult([], [], [], [])
 
         self.assertEqual(result.raw, [])
PATCH
```

- [ ] **Step 4: Run the pair in both orders.**

```bash
$PY -m unittest tests.test_translation_result_core tests.test_conversion_language_explicit 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_translation_result_core tests.test_conversion_service 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_conversion_service tests.test_translation_result_core 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (green; only the P2-5 failure, no errors, in either order):

```text
Ran 5 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 23 tests
FAILED (failures=1)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 23 tests
FAILED (failures=1)
```

- [ ] **Step 5: Full suite and 20 shuffled seeds.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
for s in $(seq 0 19); do $PY -B -I $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (every seed: 754 tests, only the P2-5 failure):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 754 tests
FAILED (failures=1, skipped=9)
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=754 failures=1 errors=0 skipped=9
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/tests/test_conversion_language_explicit.py client/tests/test_translation_result_core.py client/tests/test_conversion_service.py
git -C $REPO commit -q -F - <<'EOF'
test: run the translate import check in a subprocess

The in-process check popped `translate` from sys.modules and re-imported
it, which created a second TranslationResult class and made 8
test_conversion_service tests error whenever it ran first. Run the check
in a fresh interpreter instead, import TranslationResult at module level
in the explicit-language fakes, and drop the dead sys.modules helpers.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
test: run the translate import check in a subprocess
```

---

### Task 2: Characterize translation and dual-view output (no production change)

**Files:**
- Create: `client/tests/test_translation_golden.py`, `client/tests/fixtures/translation_golden.json` (generated)
- Modify: `client/tests/test_translation_result_core.py`, `client/tests/test_gui_document_flows.py`

Every test added here passes on the unchanged code; its expectations are today's behavior.

- **A1 golden** (`test_translation_golden.py`, 7 tests): the real `LiblouisTextTranslator` with `FakeLouisHelper` (ASCII letter 1 cell, digit 2 cells, CJK 3 cells plus a blank cell at the end of a CJK run, other characters 1 (ASCII) or 2 cells; tables whose file name contains `en` contract `the`/`and`/`ing` to one cell) and the real `MathCATMathTranslator` with `fake_translate_math` (one cell per non-space character plus a trailing blank). Real `client/data` CSVs, a temporary dictionary with `台灣 -> ⠞⠺` (`Braille/Unicode`), tables `{"default": "zh-tw.ctb", "en": "en-ueb-g2.ctb", "zh": "zh-tw.ctb", "math": "Nemeth"}`, `lang="zh_TW"`, `DEFAULT_CHARSET_MAPS`. Five short inputs at `unicode` widths 1, 10, 24, 40 and `ascii` width 24, plus the 360-segment long document at `unicode` width 40. Per run: `display_text` and both `wrap_translation_results` strings; per input (recomputed and compared on every run): the merged four lists, the four lists after `reclean_braille_endspace`, `bind_word_tokens` and `reclean_token`, `translate_with_language`'s four lists, every dual-view segment's `source_kind` and four lists (read after the wrap and the post-processing), `dataclasses.asdict` of `build_dual_view_model(..., mathml_converter=fake_mathml)` and the SHA-256 of its HTML. `test_fixture_covers_every_input` pins the case list and the 300-segment minimum.
- **A2 merge semantics and A4 constant values** (`test_translation_result_core.py`, 9 tests): `[]`/`None`, one input copied (no shared list), post-processing or mutating the merged result leaves inputs unchanged, offsets over three results, the `TypeError` message, `a + b` lists and no aliasing; the 12 punctuation sets (full-width members as `\u` escapes) and `lang_blocks` equal to `build_language_blocks({"ja", "zh", "ko"})`.
- **A3 real MathML wiring** (`test_gui_document_flows.py`, 1 test): the dual-view window HTML for a cached `x^2` math segment equals the model built with `latex_to_mathml` and contains `latex_to_mathml("x^2")`; `ExportCoordinator.write_document(..., "html")` writes exactly those bytes.

- [ ] **Step 1: Add the tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 4dcf75b..a71e412 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -31,6 +31,7 @@ from documents.export_results import ExportBatchResult
 from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
 from settings.view import ViewSettings
+from conversion.math_service import latex_to_mathml
 from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
 from dual_view.html import render_dual_view_html
 from dual_view.model import DualViewSegment, build_dual_view_model
@@ -1374,6 +1375,29 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
                 frame._export_coordinator.write_document(root / "missing" / "alpha.html", Document("alpha", "text", "b"), "html")
             self.assertFalse((root / "missing").exists())
 
+    def test_dual_view_and_html_export_render_math_with_real_mathml(self) -> None:
+        frame = self._make_export_frame()
+        results = (
+            DualViewSegment(
+                result=SimpleNamespace(raw=["x^2"], braille=["⠭", "⠘", "⠆"], braille_to_raw_pos=[0, 0, 0], raw_to_braille_pos=[0]),
+                source_kind="math",
+            ),
+        )
+        frame._document_controller.set_dual_view_results("alpha", results)
+        expected = render_dual_view_html(
+            build_dual_view_model(results, mathml_converter=latex_to_mathml),
+            empty_message=gui._("No conversion data is available for this document."),
+        )
+
+        window_html = frame._render_dual_view_for_open_document()
+
+        self.assertEqual(window_html, expected)
+        self.assertIn(latex_to_mathml("x^2"), window_html)
+        with tempfile.TemporaryDirectory() as directory:
+            path = Path(directory) / "alpha.html"
+            frame._export_coordinator.write_document(path, Document("alpha", "text", "b"), "html")
+            self.assertEqual(path.read_bytes(), expected.encode("utf-8"))
+
     def test_export_all_html_uses_each_document_cache(self) -> None:
         frame = self._make_export_frame()
         results = (
diff --git a/client/tests/test_translation_golden.py b/client/tests/test_translation_golden.py
new file mode 100644
index 0000000..a4fa212
--- /dev/null
+++ b/client/tests/test_translation_golden.py
@@ -0,0 +1,297 @@
+"""Golden characterization of the translation, wrap and dual-view output.
+
+The fixture was generated once from the unchanged production code (P1-5,
+step 2) and must not be regenerated by a refactor. Regenerate it only for an
+intended output change, from client/:
+
+    python -m tests.test_translation_golden --write
+"""
+import csv
+import dataclasses
+import hashlib
+import html
+import json
+import sys
+import tempfile
+import unittest
+from pathlib import Path
+
+from adapters.translation.contracts import TranslationRuntime
+from adapters.translation.liblouis import LiblouisTextTranslator
+from adapters.translation.mathcat import MathCATMathTranslator
+from config import DEFAULT_CHARSET_MAPS
+from conversion.service import ConversionRequest, convert_text_with_alignment, translate_with_language
+from conversion.wrapping import merge_translation_results, wrap_translation_results
+from dual_view.html import render_dual_view_html
+from dual_view.model import build_dual_view_model
+from languageDetection.unicode_blocks import char_block
+
+
+DATA_DIR = Path(__file__).resolve().parents[1] / "data"
+FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "translation_golden.json"
+TRANSLATION_TABLES = {
+    "default": "zh-tw.ctb",
+    "en": "en-ueb-g2.ctb",
+    "zh": "zh-tw.ctb",
+    "math": "Nemeth",
+}
+LANG = "zh_TW"
+DICTIONARY_ROWS = [{"text": "台灣", "braille": "⠞⠺", "type": "Braille/Unicode"}]
+SHORT_INPUTS = {
+    "chinese_prose": "我們 Coseeing 透過開發創新工具，讓視障者看見更多資訊和可能；透過舉辦推廣活動。",
+    "english_math": "The area of the circle is $\\pi r^2$, and 半徑 is 3 cm.",
+    "spaced_math_punctuation": "計算 $1+2$ 的值\n第二行（甲）（乙）「引號」『雙』",
+    "escaped_dollar_fraction": "價格 \\$5 與 $\\frac{a}{b}$ 和$x$相加。Testing, (one) [two]!",
+    "dictionary_literal": "台灣 is 台灣.\n\n  indented line\nend",
+}
+LONG_INPUT_REPEAT = 12
+INPUTS = dict(SHORT_INPUTS)
+INPUTS["long_document"] = "\n\n".join(list(SHORT_INPUTS.values()) * LONG_INPUT_REPEAT)
+SHORT_RUNS = (("unicode", 1), ("unicode", 10), ("unicode", 24), ("unicode", 40), ("ascii", 24))
+LONG_RUNS = (("unicode", 40),)
+# The long document's width-independent snapshot is stored as SHA-256 digests
+# of its canonical JSON to keep the fixture small; the short inputs are stored
+# in full so that a diff shows what changed.
+DIGEST_CASES = frozenset({"long_document"})
+CONTRACTIONS = ("the", "and", "ing")
+
+
+def _is_cjk(character: str) -> bool:
+    block = char_block(character) or ""
+    return block.startswith("CJK Unified") or block.startswith("Bopomofo")
+
+
+class FakeLouisHelper:
+    """Deterministic stand-in for the native liblouis helper.
+
+    ASCII letters give one cell, digits two (number sign), CJK characters
+    three plus a blank cell at the end of a CJK run, other characters one
+    (ASCII) or two cells. Tables whose file name contains "en" contract
+    "the", "and" and "ing" to one cell.
+    """
+
+    def translate(self, tables, text, mode=0):
+        cells: list[int] = []
+        braille_to_raw: list[int] = []
+        raw_to_braille: list[int] = []
+        contracted = "en" in Path(tables[0]).name
+        index = 0
+        while index < len(text):
+            character = text[index]
+            start = len(cells)
+            if contracted and text[index:index + 3].lower() in CONTRACTIONS:
+                cells.append(0x2F)
+                braille_to_raw.append(index)
+                raw_to_braille.extend([start] * 3)
+                index += 3
+                continue
+            raw_to_braille.append(start)
+            if character in " \n":
+                output = [0]
+            elif character.isdigit():
+                output = [0x3C, ord(character) % 10 + 1]
+            elif character.isascii() and character.isalpha():
+                output = [(ord(character) & 0x3F) | 1]
+            elif _is_cjk(character):
+                output = [(ord(character) >> 8) & 0xFF or 1, ord(character) & 0xFF or 1, 0x20]
+                if index + 1 == len(text) or not _is_cjk(text[index + 1]):
+                    output.append(0)
+            elif character.isascii():
+                output = [ord(character) % 60 + 3]
+            else:
+                output = [ord(character) % 60 + 3, 0x04]
+            cells.extend(output)
+            braille_to_raw.extend([index] * len(output))
+            index += 1
+        return cells, braille_to_raw, raw_to_braille, None
+
+    def terminate(self) -> None:
+        pass
+
+
+def fake_translate_math(source: str, *, braille_code: str, language: str) -> str:
+    del braille_code, language
+    cells = "".join(chr(0x2800 + ord(character) % 63 + 1) for character in source if not character.isspace())
+    return cells + "⠀"
+
+
+def fake_mathml(latex: str) -> str:
+    return f'<math data-latex="{html.escape(latex, quote=True)}"></math>'
+
+
+def _runtime() -> TranslationRuntime:
+    return TranslationRuntime(
+        text_translator=LiblouisTextTranslator(helper=FakeLouisHelper(), tables_dir="tables"),
+        math_translator=MathCATMathTranslator(translate_math=fake_translate_math),
+    )
+
+
+def _lists(result) -> dict[str, list]:
+    return {
+        "raw": list(result.raw),
+        "braille": list(result.braille),
+        "braille_to_raw_pos": list(result.braille_to_raw_pos),
+        "raw_to_braille_pos": list(result.raw_to_braille_pos),
+    }
+
+
+def snapshot_run(text: str, output_mode: str, width: int, dictionary_path: Path) -> tuple[dict, dict]:
+    """Return (width-dependent run snapshot, width-independent conversion snapshot)."""
+    request = ConversionRequest(
+        raw_text=text,
+        output_mode=output_mode,
+        width=width,
+        dictionary_path=dictionary_path,
+        data_dir=DATA_DIR,
+        translation_tables=dict(TRANSLATION_TABLES),
+        lang=LANG,
+        charset_maps=dict(DEFAULT_CHARSET_MAPS),
+    )
+    output = convert_text_with_alignment(request, runtime=_runtime())
+    results = list(output.translation_results)
+    wrapped_braille, wrapped_text = wrap_translation_results(results, width)
+    merged = merge_translation_results(results)
+    merged_lists = _lists(merged)
+    post_processed = merge_translation_results(results)
+    post_processed.reclean_braille_endspace()
+    post_processed.bind_word_tokens()
+    post_processed.reclean_token()
+    direct = translate_with_language(
+        text,
+        dictionary_path,
+        dict(TRANSLATION_TABLES),
+        DATA_DIR / "Bopomofo2Braille.csv",
+        runtime=_runtime(),
+        lang=LANG,
+        charset_maps=dict(DEFAULT_CHARSET_MAPS),
+    )
+    # Read after the wrap and the post-processing: they must not mutate the cache.
+    segments = [
+        {"source_kind": segment.source_kind, **_lists(segment.result)}
+        for segment in output.dual_view_segments
+    ]
+    model = build_dual_view_model(output.dual_view_segments, mathml_converter=fake_mathml)
+    dual_view_html = render_dual_view_html(model)
+    run = {
+        "display_text": output.display_text,
+        "wrapped_braille": wrapped_braille,
+        "wrapped_text": wrapped_text,
+    }
+    conversion = {
+        "merged": merged_lists,
+        "post_processed": _lists(post_processed),
+        "translate_with_language": _lists(direct),
+        "dual_view_segments": segments,
+        "dual_view_model": dataclasses.asdict(model),
+        "dual_view_html_sha256": hashlib.sha256(dual_view_html.encode("utf-8")).hexdigest(),
+    }
+    return run, conversion
+
+
+def _digest(value) -> str:
+    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True)
+    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
+
+
+def _stored_conversion(name: str, conversion: dict) -> dict:
+    stored = {"dual_view_segment_count": len(conversion["dual_view_segments"])}
+    for key, value in conversion.items():
+        if name in DIGEST_CASES and key != "dual_view_html_sha256":
+            stored[f"{key}_sha256"] = _digest(value)
+        else:
+            stored[key] = value
+    # Round-trip through JSON so that tuples compare equal to the stored lists.
+    return json.loads(json.dumps(stored, ensure_ascii=False))
+
+
+def _write_dictionary(directory: Path) -> Path:
+    dictionary_dir = directory / "dictionary"
+    dictionary_dir.mkdir()
+    dictionary_path = dictionary_dir / "default.csv"
+    with dictionary_path.open("w", newline="", encoding="utf-8") as f:
+        writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
+        writer.writeheader()
+        writer.writerows(DICTIONARY_ROWS)
+    return dictionary_path
+
+
+def snapshot_case(name: str, dictionary_path: Path) -> dict:
+    runs = LONG_RUNS if name == "long_document" else SHORT_RUNS
+    case = {"text": INPUTS[name], "runs": {}}
+    for output_mode, width in runs:
+        run, conversion = snapshot_run(INPUTS[name], output_mode, width, dictionary_path)
+        conversion = _stored_conversion(name, conversion)
+        case["runs"][f"{output_mode}-{width}"] = run
+        case.setdefault("conversion", conversion)
+        if case["conversion"] != conversion:
+            raise AssertionError(f"{name}: conversion depends on {output_mode}-{width}")
+    return case
+
+
+def build_fixture() -> dict:
+    with tempfile.TemporaryDirectory() as directory:
+        dictionary_path = _write_dictionary(Path(directory))
+        return {"cases": {name: snapshot_case(name, dictionary_path) for name in INPUTS}}
+
+
+def write_fixture() -> None:
+    fixture = build_fixture()
+    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
+    FIXTURE_PATH.write_text(
+        json.dumps(fixture, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
+        encoding="utf-8",
+    )
+    long_segments = fixture["cases"]["long_document"]["conversion"]["dual_view_segment_count"]
+    print(f"wrote {FIXTURE_PATH.name}: {len(fixture['cases'])} cases, long_document {long_segments} segments")
+
+
+class TranslationGoldenTest(unittest.TestCase):
+    @classmethod
+    def setUpClass(cls) -> None:
+        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
+        directory = tempfile.TemporaryDirectory()
+        cls.addClassCleanup(directory.cleanup)
+        cls.dictionary_path = _write_dictionary(Path(directory.name))
+
+    def assert_case(self, name: str) -> None:
+        expected = self.fixture["cases"][name]
+        runs = LONG_RUNS if name == "long_document" else SHORT_RUNS
+        self.assertEqual(INPUTS[name], expected["text"])
+        self.assertEqual(sorted(expected["runs"]), sorted(f"{mode}-{width}" for mode, width in runs))
+        for output_mode, width in runs:
+            with self.subTest(run=f"{output_mode}-{width}"):
+                run, conversion = snapshot_run(INPUTS[name], output_mode, width, self.dictionary_path)
+                conversion = _stored_conversion(name, conversion)
+                self.assertEqual(run, expected["runs"][f"{output_mode}-{width}"])
+                self.assertEqual(sorted(conversion), sorted(expected["conversion"]))
+                for key in sorted(expected["conversion"]):
+                    self.assertEqual(conversion[key], expected["conversion"][key], key)
+
+    def test_fixture_covers_every_input(self) -> None:
+        self.assertEqual(sorted(self.fixture["cases"]), sorted(INPUTS))
+        self.assertGreaterEqual(self.fixture["cases"]["long_document"]["conversion"]["dual_view_segment_count"], 300)
+
+    def test_chinese_prose(self) -> None:
+        self.assert_case("chinese_prose")
+
+    def test_english_math(self) -> None:
+        self.assert_case("english_math")
+
+    def test_spaced_math_punctuation(self) -> None:
+        self.assert_case("spaced_math_punctuation")
+
+    def test_escaped_dollar_fraction(self) -> None:
+        self.assert_case("escaped_dollar_fraction")
+
+    def test_dictionary_literal(self) -> None:
+        self.assert_case("dictionary_literal")
+
+    def test_long_document(self) -> None:
+        self.assert_case("long_document")
+
+
+if __name__ == "__main__":
+    if sys.argv[1:] == ["--write"]:
+        write_fixture()
+    else:
+        unittest.main()
diff --git a/client/tests/test_translation_result_core.py b/client/tests/test_translation_result_core.py
index 4d6d8b2..a8db8de 100644
--- a/client/tests/test_translation_result_core.py
+++ b/client/tests/test_translation_result_core.py
@@ -2,9 +2,30 @@ import subprocess
 import sys
 import unittest
 
+from conversion.wrapping import merge_translation_results
+from languageDetection.unicode_blocks import build_language_blocks
 from translate import TranslationResult
 
 
+FIELDS = ("raw", "braille", "braille_to_raw_pos", "raw_to_braille_pos")
+PUNCTUATION = {
+    "LEFT_PUNCT_HALF": set("([{"),
+    "RIGHT_PUNCT_HALF": set(")]}"),
+    "MIDDLE_SENTENCE_PUNCT_HALF": set(",;:%"),
+    "END_SENTENCE_PUNCT_HALF": set(".!?"),
+    "LEFT_PUNCT_FULL": set("\u2018\u201c\u300c\u300e\u3008\u300a\u3010\u3014\u3016\uff08"),
+    "RIGHT_PUNCT_FULL": set("\u2019\u201d\u300d\u300f\u3009\u300b\u3011\u3015\u3017\uff09"),
+    "MIDDLE_SENTENCE_PUNCT_FULL": set("\uff0c\uff1b\uff1a\u3001\uff05"),
+    "END_SENTENCE_PUNCT_FULL": set("\u3002\uff01\uff1f"),
+}
+for _kind in ("LEFT_PUNCT", "RIGHT_PUNCT", "MIDDLE_SENTENCE_PUNCT", "END_SENTENCE_PUNCT"):
+    PUNCTUATION[_kind] = PUNCTUATION[f"{_kind}_HALF"] | PUNCTUATION[f"{_kind}_FULL"]
+
+
+def lists_of(result) -> tuple[list, ...]:
+    return tuple(getattr(result, name) for name in FIELDS)
+
+
 class TranslationResultCoreTest(unittest.TestCase):
     def test_import_does_not_import_liblouis_helper(self) -> None:
         script = """
@@ -44,6 +65,106 @@ assert not hasattr(translate, "translate_as_single_token")
         self.assertEqual(result.braille_to_raw_pos, [])
         self.assertEqual(result.raw_to_braille_pos, [])
 
+    def test_addition_offsets_multi_token_results_without_aliasing(self) -> None:
+        left = TranslationResult(["a", "b"], ["⠁", "⠃", "⠀"], [0, 1, 1], [0, 1])
+        right = TranslationResult(["c"], ["⠉", "⠀"], [0, 0], [0])
+
+        result = left + right
+
+        self.assertEqual(
+            lists_of(result),
+            (["a", "b", "c"], ["⠁", "⠃", "⠀", "⠉", "⠀"], [0, 1, 1, 2, 2], [0, 1, 3]),
+        )
+        for name in FIELDS:
+            self.assertIsNot(getattr(result, name), getattr(left, name), name)
+            self.assertIsNot(getattr(result, name), getattr(right, name), name)
+        with self.assertRaisesRegex(TypeError, "^not TranslateResult object$"):
+            left + "x"
+
+    def test_punctuation_sets_keep_their_members(self) -> None:
+        result = TranslationResult([], [], [], [])
+
+        self.assertEqual(len(PUNCTUATION), 12)
+        for name, expected in PUNCTUATION.items():
+            with self.subTest(name=name):
+                self.assertEqual(set(getattr(result, name)), expected)
+
+    def test_language_blocks_match_the_cjk_block_table(self) -> None:
+        result = TranslationResult([], [], [], [])
+
+        self.assertEqual(
+            {language: list(blocks) for language, blocks in result.lang_blocks.items()},
+            build_language_blocks({"ja", "zh", "ko"}),
+        )
+
+
+class MergeTranslationResultsTest(unittest.TestCase):
+    def test_merging_nothing_gives_an_empty_result(self) -> None:
+        for translations in ([], None):
+            with self.subTest(translations=translations):
+                merged = merge_translation_results(translations)
+
+                self.assertIsInstance(merged, TranslationResult)
+                self.assertEqual(lists_of(merged), ([], [], [], []))
+
+    def test_merging_one_result_copies_its_lists(self) -> None:
+        source = TranslationResult(["a", "b"], ["⠁", "⠃", "⠀"], [0, 1, 1], [0, 1])
+
+        merged = merge_translation_results([source])
+
+        self.assertIsNot(merged, source)
+        self.assertEqual(lists_of(merged), lists_of(source))
+        for name in FIELDS:
+            self.assertIsNot(getattr(merged, name), getattr(source, name), name)
+
+    def test_post_processing_the_merged_result_leaves_one_input_unchanged(self) -> None:
+        source = TranslationResult(["中"], ["⠁", "⠂", "⠀"], [0, 0, 0], [0])
+
+        merged = merge_translation_results([source])
+        merged.reclean_braille_endspace()
+
+        self.assertEqual(merged.braille, ["⠁", "⠂"])
+        self.assertEqual(lists_of(source), (["中"], ["⠁", "⠂", "⠀"], [0, 0, 0], [0]))
+
+    def test_mutating_the_merged_result_leaves_every_input_unchanged(self) -> None:
+        first = TranslationResult(["中"], ["⠁", "⠂", "⠀"], [0, 0, 0], [0])
+        second = TranslationResult(["文", "字"], ["⠃", "⠀", "⠉"], [0, 0, 1], [0, 2])
+
+        merged = merge_translation_results([first, second])
+        merged.reclean_braille_endspace()
+        for name in FIELDS:
+            getattr(merged, name).append("changed")
+
+        self.assertEqual(
+            [lists_of(first), lists_of(second)],
+            [(["中"], ["⠁", "⠂", "⠀"], [0, 0, 0], [0]), (["文", "字"], ["⠃", "⠀", "⠉"], [0, 0, 1], [0, 2])],
+        )
+
+    def test_merging_three_results_offsets_every_position(self) -> None:
+        results = [
+            TranslationResult(["a"], ["⠁"], [0], [0]),
+            TranslationResult(["b", "c"], ["⠃", "⠉", "⠀"], [0, 1, 1], [0, 1]),
+            TranslationResult(["d"], ["⠙", "⠀"], [0, 0], [0]),
+        ]
+
+        merged = merge_translation_results(results)
+
+        self.assertEqual(
+            lists_of(merged),
+            (
+                ["a", "b", "c", "d"],
+                ["⠁", "⠃", "⠉", "⠀", "⠙", "⠀"],
+                [0, 1, 2, 2, 3, 3],
+                [0, 1, 2, 4],
+            ),
+        )
+
+    def test_merging_a_non_result_raises_type_error(self) -> None:
+        results = [TranslationResult(["a"], ["⠁"], [0], [0]), object()]
+
+        with self.assertRaisesRegex(TypeError, "^not TranslateResult object$"):
+            merge_translation_results(results)
+
 
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Generate the fixture from the unchanged code and check that it does not depend on the hash seed.**

```bash
$PY -m tests.test_translation_golden --write
sha256sum tests/fixtures/translation_golden.json
wc -c -l < tests/fixtures/translation_golden.json
for h in 0 1 2 3; do PYTHONHASHSEED=$h $PY -B -c "import json, tests.test_translation_golden as g; print(json.dumps(g.build_fixture(), ensure_ascii=False, sort_keys=True, indent=1) + '\n' == g.FIXTURE_PATH.read_text(encoding='utf-8'))"; done
```

Expected (if the sha256 differs, stop: the environment differs from the dry run):

```text
wrote translation_golden.json: 6 cases, long_document 360 segments
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
   6652  189305
True
True
True
True
```

- [ ] **Step 3: Run the new tests.**

```bash
$PY -m unittest tests.test_translation_golden tests.test_translation_result_core tests.test_gui_document_flows -v 2>&1 | grep -E 'test_translation_golden|MergeTranslationResultsTest|punctuation_sets|language_blocks_match|multi_token_results|real_mathml|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected:

```text
test_chinese_prose (tests.test_translation_golden.TranslationGoldenTest.test_chinese_prose) ... ok
test_dictionary_literal (tests.test_translation_golden.TranslationGoldenTest.test_dictionary_literal) ... ok
test_english_math (tests.test_translation_golden.TranslationGoldenTest.test_english_math) ... ok
test_escaped_dollar_fraction (tests.test_translation_golden.TranslationGoldenTest.test_escaped_dollar_fraction) ... ok
test_fixture_covers_every_input (tests.test_translation_golden.TranslationGoldenTest.test_fixture_covers_every_input) ... ok
test_long_document (tests.test_translation_golden.TranslationGoldenTest.test_long_document) ... ok
test_spaced_math_punctuation (tests.test_translation_golden.TranslationGoldenTest.test_spaced_math_punctuation) ... ok
test_merging_a_non_result_raises_type_error (tests.test_translation_result_core.MergeTranslationResultsTest.test_merging_a_non_result_raises_type_error) ... ok
test_merging_nothing_gives_an_empty_result (tests.test_translation_result_core.MergeTranslationResultsTest.test_merging_nothing_gives_an_empty_result) ... ok
test_merging_one_result_copies_its_lists (tests.test_translation_result_core.MergeTranslationResultsTest.test_merging_one_result_copies_its_lists) ... ok
test_merging_three_results_offsets_every_position (tests.test_translation_result_core.MergeTranslationResultsTest.test_merging_three_results_offsets_every_position) ... ok
test_mutating_the_merged_result_leaves_every_input_unchanged (tests.test_translation_result_core.MergeTranslationResultsTest.test_mutating_the_merged_result_leaves_every_input_unchanged) ... ok
test_post_processing_the_merged_result_leaves_one_input_unchanged (tests.test_translation_result_core.MergeTranslationResultsTest.test_post_processing_the_merged_result_leaves_one_input_unchanged) ... ok
test_addition_offsets_multi_token_results_without_aliasing (tests.test_translation_result_core.TranslationResultCoreTest.test_addition_offsets_multi_token_results_without_aliasing) ... ok
test_language_blocks_match_the_cjk_block_table (tests.test_translation_result_core.TranslationResultCoreTest.test_language_blocks_match_the_cjk_block_table) ... ok
test_punctuation_sets_keep_their_members (tests.test_translation_result_core.TranslationResultCoreTest.test_punctuation_sets_keep_their_members) ... ok
test_dual_view_and_html_export_render_math_with_real_mathml (tests.test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_dual_view_and_html_export_render_math_with_real_mathml) ... ok
Ran 162 tests
OK (skipped=2)
```

- [ ] **Step 4: Prove the net can fail.** Each mutant breaks one behavior in memory only; the repo is not modified.

```bash
for m in "reclean_token is a no-op" "bind_contracted_tokens is a no-op" "wrap merges into the first segment"; do $PY -B $T/tools/golden_mutants.py "$m"; done
git -C $REPO status --short
```

Expected (the last mutant merges into the first cached segment, the aliasing bug the new merge must not have):

```text
reclean_token is a no-op: ran=7 failures=6 errors=0
bind_contracted_tokens is a no-op: ran=7 failures=16 errors=0
wrap merges into the first segment: ran=7 failures=26 errors=0
 M client/tests/test_gui_document_flows.py
 M client/tests/test_translation_result_core.py
?? client/tests/fixtures/translation_golden.json
?? client/tests/test_translation_golden.py
```

- [ ] **Step 5: Full suite.**

```bash
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected:

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 771 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/tests/test_translation_golden.py client/tests/fixtures/translation_golden.json client/tests/test_translation_result_core.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'EOF'
test: characterize translation and dual-view output

Pin the braille text, the source-text wrap, the merged and
post-processed alignment lists, the dual-view segments and model, and the
dual-view HTML for realistic mixed input at several widths, generated from
the unchanged code with a deterministic fake liblouis helper. Also pin the
merge semantics, the punctuation and CJK block constants, and the real
MathML wiring of the dual-view window and the HTML export.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
test: characterize translation and dual-view output
```

---

### Task 3: Share the `TranslationResult` constants

**Files:**
- Modify: `client/tests/test_translation_result_core.py`, `client/translate.py`

- [ ] **Step 1: Write the failing tests** (`SharedConstantsTest`: an instance holds exactly the four data fields; constructing one never calls `translate.build_language_blocks`; the 12 sets are `frozenset`s and `lang_blocks` rejects item assignment).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_translation_result_core.py b/client/tests/test_translation_result_core.py
index a8db8de..77577ad 100644
--- a/client/tests/test_translation_result_core.py
+++ b/client/tests/test_translation_result_core.py
@@ -1,6 +1,7 @@
 import subprocess
 import sys
 import unittest
+from unittest.mock import patch
 
 from conversion.wrapping import merge_translation_results
 from languageDetection.unicode_blocks import build_language_blocks
@@ -98,6 +99,26 @@ assert not hasattr(translate, "translate_as_single_token")
         )
 
 
+class SharedConstantsTest(unittest.TestCase):
+    def test_instance_holds_only_its_data_fields(self) -> None:
+        result = TranslationResult([], [], [], [])
+
+        self.assertEqual(sorted(vars(result)), sorted(FIELDS))
+
+    def test_construction_does_not_build_language_blocks(self) -> None:
+        with patch("translate.build_language_blocks", side_effect=AssertionError("built per instance")) as build:
+            TranslationResult([], [], [], [])
+
+        build.assert_not_called()
+
+    def test_shared_constants_are_immutable(self) -> None:
+        for name in PUNCTUATION:
+            with self.subTest(name=name):
+                self.assertIsInstance(getattr(TranslationResult, name), frozenset)
+        with self.assertRaises(TypeError):
+            TranslationResult.lang_blocks["ja"] = ()
+
+
 class MergeTranslationResultsTest(unittest.TestCase):
     def test_merging_nothing_gives_an_empty_result(self) -> None:
         for translations in ([], None):
PATCH
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
$PY -m unittest tests.test_translation_result_core 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (12 subtest errors and one for `lang_blocks`, all `AttributeError` on the class; two failures):

```text
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='LEFT_PUNCT_HALF')
AttributeError: type object 'TranslationResult' has no attribute 'LEFT_PUNCT_HALF'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='RIGHT_PUNCT_HALF')
AttributeError: type object 'TranslationResult' has no attribute 'RIGHT_PUNCT_HALF'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='MIDDLE_SENTENCE_PUNCT_HALF')
AttributeError: type object 'TranslationResult' has no attribute 'MIDDLE_SENTENCE_PUNCT_HALF'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='END_SENTENCE_PUNCT_HALF')
AttributeError: type object 'TranslationResult' has no attribute 'END_SENTENCE_PUNCT_HALF'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='LEFT_PUNCT_FULL')
AttributeError: type object 'TranslationResult' has no attribute 'LEFT_PUNCT_FULL'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='RIGHT_PUNCT_FULL')
AttributeError: type object 'TranslationResult' has no attribute 'RIGHT_PUNCT_FULL'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='MIDDLE_SENTENCE_PUNCT_FULL')
AttributeError: type object 'TranslationResult' has no attribute 'MIDDLE_SENTENCE_PUNCT_FULL'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='END_SENTENCE_PUNCT_FULL')
AttributeError: type object 'TranslationResult' has no attribute 'END_SENTENCE_PUNCT_FULL'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='LEFT_PUNCT')
AttributeError: type object 'TranslationResult' has no attribute 'LEFT_PUNCT'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='RIGHT_PUNCT')
AttributeError: type object 'TranslationResult' has no attribute 'RIGHT_PUNCT'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='MIDDLE_SENTENCE_PUNCT')
AttributeError: type object 'TranslationResult' has no attribute 'MIDDLE_SENTENCE_PUNCT'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable) (name='END_SENTENCE_PUNCT')
AttributeError: type object 'TranslationResult' has no attribute 'END_SENTENCE_PUNCT'
ERROR: test_shared_constants_are_immutable (tests.test_translation_result_core.SharedConstantsTest.test_shared_constants_are_immutable)
AttributeError: type object 'TranslationResult' has no attribute 'lang_blocks'
FAIL: test_construction_does_not_build_language_blocks (tests.test_translation_result_core.SharedConstantsTest.test_construction_does_not_build_language_blocks)
AssertionError: built per instance
FAIL: test_instance_holds_only_its_data_fields (tests.test_translation_result_core.SharedConstantsTest.test_instance_holds_only_its_data_fields)
AssertionError: Lists differ: ['END_SENTENCE_PUNCT', 'END_SENTENCE_PUNCT_[297 chars]pos'] != ['braille', 'braille_to_raw_pos', 'raw', 'r[14 chars]pos']
Ran 15 tests
FAILED (failures=2, errors=13)
```

- [ ] **Step 3: Move the constants to the class.** The 12 sets become `frozenset` class attributes with the same names and members (the union attributes are computed in the class body); the language blocks are built once at import into a `MappingProxyType` of tuples; `__hash__ = None` is stated; `__init__` keeps only the four data fields. No method body changes.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/translate.py b/client/translate.py
index 5eb1cd7..38c4840 100644
--- a/client/translate.py
+++ b/client/translate.py
@@ -1,4 +1,5 @@
 import string
+from types import MappingProxyType
 
 from languageDetection.unicode_blocks import (
     build_language_blocks,
@@ -7,30 +8,38 @@ from languageDetection.unicode_blocks import (
 )
 
 
+_CJK_LANGUAGE_BLOCKS = MappingProxyType({
+	language: tuple(blocks)
+	for language, blocks in build_language_blocks(("ja", "zh", "ko")).items()
+})
+
+
 class TranslationResult:
+	LEFT_PUNCT_HALF = frozenset("([{")
+	RIGHT_PUNCT_HALF = frozenset(")]}")
+	MIDDLE_SENTENCE_PUNCT_HALF = frozenset(",;:%")
+	END_SENTENCE_PUNCT_HALF = frozenset(".!?")
+
+	LEFT_PUNCT_FULL = frozenset("‘“「『〈《【〔〖（")
+	RIGHT_PUNCT_FULL = frozenset("’”」』〉》】〕〗）")
+	MIDDLE_SENTENCE_PUNCT_FULL = frozenset("，；：、％")
+	END_SENTENCE_PUNCT_FULL = frozenset("。！？")
+
+	LEFT_PUNCT = LEFT_PUNCT_HALF | LEFT_PUNCT_FULL
+	RIGHT_PUNCT = RIGHT_PUNCT_HALF | RIGHT_PUNCT_FULL
+	MIDDLE_SENTENCE_PUNCT = MIDDLE_SENTENCE_PUNCT_HALF | MIDDLE_SENTENCE_PUNCT_FULL
+	END_SENTENCE_PUNCT = END_SENTENCE_PUNCT_HALF | END_SENTENCE_PUNCT_FULL
+
+	lang_blocks = _CJK_LANGUAGE_BLOCKS
+
+	__hash__ = None
+
 	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
 		self.raw = raw
 		self.braille = braille
 		self.braille_to_raw_pos = braille_to_raw_pos
 		self.raw_to_braille_pos = raw_to_braille_pos
 
-		self.LEFT_PUNCT_HALF = set("([{")
-		self.RIGHT_PUNCT_HALF = set(")]}")
-		self.MIDDLE_SENTENCE_PUNCT_HALF = set(",;:%")
-		self.END_SENTENCE_PUNCT_HALF = set(".!?")
-
-		self.LEFT_PUNCT_FULL = set("‘“「『〈《【〔〖（")
-		self.RIGHT_PUNCT_FULL = set("’”」』〉》】〕〗）")
-		self.MIDDLE_SENTENCE_PUNCT_FULL = set("，；：、％")
-		self.END_SENTENCE_PUNCT_FULL = set("。！？")
-
-		self.LEFT_PUNCT = self.LEFT_PUNCT_HALF | self.LEFT_PUNCT_FULL
-		self.RIGHT_PUNCT = self.RIGHT_PUNCT_HALF | self.RIGHT_PUNCT_FULL
-		self.MIDDLE_SENTENCE_PUNCT = self.MIDDLE_SENTENCE_PUNCT_HALF | self.MIDDLE_SENTENCE_PUNCT_FULL
-		self.END_SENTENCE_PUNCT = self.END_SENTENCE_PUNCT_HALF | self.END_SENTENCE_PUNCT_FULL
-
-		self.lang_blocks = build_language_blocks({"ja", "zh", "ko"})
-
 	def __add__(self, other):
 		if not isinstance(other, TranslationResult):
 			raise TypeError("not TranslateResult object")
PATCH
```

- [ ] **Step 4: Verify (tests, unchanged golden output, spec acceptance 8).**

```bash
$PY -m unittest tests.test_translation_result_core tests.test_translation_golden 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
sha256sum tests/fixtures/translation_golden.json
echo AC8; grep -n "self\.\(LEFT\|RIGHT\|MIDDLE\|END\)_[A-Z_]* = \|self.lang_blocks = " translate.py; echo end
```

Expected:

```text
Ran 22 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 774 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
AC8
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/translate.py client/tests/test_translation_result_core.py
git -C $REPO commit -q -F - <<'EOF'
refactor: share TranslationResult constants

Build the punctuation sets and the CJK language blocks once, as immutable
class attributes, instead of 12 sets and a block table per instance. An
instance now holds only its four data fields. State the implicit
`__hash__ = None` explicitly.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: share TranslationResult constants
```

---

### Task 4: Compare `TranslationResult` only with results (L-1)

**Files:**
- Modify: `client/tests/test_translation_result_core.py`, `client/translate.py`

- [ ] **Step 1: Write the failing tests** (`EqualityTest`: `result == object()` is `False`, `result != "x"` is `True`, `result.__eq__(42) is NotImplemented`; equal lists compare equal, different lists do not; `hash(result)` raises `TypeError`).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_translation_result_core.py b/client/tests/test_translation_result_core.py
index 77577ad..74298fe 100644
--- a/client/tests/test_translation_result_core.py
+++ b/client/tests/test_translation_result_core.py
@@ -119,6 +119,29 @@ class SharedConstantsTest(unittest.TestCase):
             TranslationResult.lang_blocks["ja"] = ()
 
 
+class EqualityTest(unittest.TestCase):
+    def test_comparing_with_another_type_is_not_equal(self) -> None:
+        result = TranslationResult(["a"], ["⠁"], [0], [0])
+
+        self.assertFalse(result == object())
+        self.assertTrue(result != "x")
+        self.assertIs(result.__eq__(42), NotImplemented)
+
+    def test_results_with_equal_lists_compare_equal(self) -> None:
+        self.assertEqual(
+            TranslationResult(["a"], ["⠁"], [0], [0]),
+            TranslationResult(["a"], ["⠁"], [0], [0]),
+        )
+        self.assertNotEqual(
+            TranslationResult(["a"], ["⠁"], [0], [0]),
+            TranslationResult(["b"], ["⠁"], [0], [0]),
+        )
+
+    def test_results_are_unhashable(self) -> None:
+        with self.assertRaises(TypeError):
+            hash(TranslationResult([], [], [], []))
+
+
 class MergeTranslationResultsTest(unittest.TestCase):
     def test_merging_nothing_gives_an_empty_result(self) -> None:
         for translations in ([], None):
PATCH
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
$PY -m unittest tests.test_translation_result_core 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (the other two already pass: equality of results and `__hash__ = None` from Task 3):

```text
ERROR: test_comparing_with_another_type_is_not_equal (tests.test_translation_result_core.EqualityTest.test_comparing_with_another_type_is_not_equal)
AttributeError: 'object' object has no attribute 'raw'
Ran 18 tests
FAILED (errors=1)
```

- [ ] **Step 3: Return `NotImplemented` for other types.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/translate.py b/client/translate.py
index 38c4840..da8ad92 100644
--- a/client/translate.py
+++ b/client/translate.py
@@ -61,6 +61,8 @@ class TranslationResult:
 		return TranslationResult(raw, braille, braille_to_raw_pos, raw_to_braille_pos)
 
 	def __eq__(self, other):
+		if not isinstance(other, TranslationResult):
+			return NotImplemented
 		result = True
 		result &= (self.raw == other.raw)
 		result &= (self.braille == other.braille)
PATCH
```

- [ ] **Step 4: Verify.**

```bash
$PY -m unittest tests.test_translation_result_core tests.test_translation_golden 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
sha256sum tests/fixtures/translation_golden.json
```

Expected:

```text
Ran 25 tests
OK
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 777 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/translate.py client/tests/test_translation_result_core.py
git -C $REPO commit -q -F - <<'EOF'
fix: compare TranslationResult only with results

`__eq__` read `other.raw` directly and raised AttributeError for any other
type. Return NotImplemented instead, so such a comparison is simply
unequal.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
fix: compare TranslationResult only with results
```

---

### Task 5: Merge translation results in one pass

**Files:**
- Modify: `client/tests/test_translation_result_core.py`, `client/translate.py`, `client/conversion/wrapping.py`, `client/conversion/preprocessing/literal_braille.py`

- [ ] **Step 1: Write the failing tests** (`LinearMergeTest`: merging 500 results constructs exactly one `TranslationResult`, which is the returned one; merging 500 results never calls `__add__`; merging 20,000 ten-token results equals the offset-arithmetic reference and takes less than 5 s, see correction 1).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_translation_result_core.py b/client/tests/test_translation_result_core.py
index 74298fe..1d37b8d 100644
--- a/client/tests/test_translation_result_core.py
+++ b/client/tests/test_translation_result_core.py
@@ -1,5 +1,6 @@
 import subprocess
 import sys
+import time
 import unittest
 from unittest.mock import patch
 
@@ -210,5 +211,61 @@ class MergeTranslationResultsTest(unittest.TestCase):
             merge_translation_results(results)
 
 
+class LinearMergeTest(unittest.TestCase):
+    def results(self, count: int, tokens: int) -> list[TranslationResult]:
+        return [
+            TranslationResult(
+                [f"t{index * tokens + offset}" for offset in range(tokens)],
+                ["⠁", "⠀"] * tokens,
+                [offset for offset in range(tokens) for _cell in range(2)],
+                [2 * offset for offset in range(tokens)],
+            )
+            for index in range(count)
+        ]
+
+    def test_merge_builds_exactly_one_result(self) -> None:
+        results = self.results(500, 1)
+        original_init = TranslationResult.__init__
+        constructed = []
+
+        def counting_init(result, *args, **kwargs):
+            constructed.append(result)
+            original_init(result, *args, **kwargs)
+
+        with patch.object(TranslationResult, "__init__", counting_init):
+            merged = merge_translation_results(results)
+
+        self.assertEqual(len(constructed), 1)
+        self.assertIs(constructed[0], merged)
+        self.assertEqual(len(merged.raw), 500)
+
+    def test_merge_never_adds_pairwise(self) -> None:
+        results = self.results(500, 1)
+
+        with patch.object(TranslationResult, "__add__", side_effect=AssertionError("pairwise merge")) as add:
+            merged = merge_translation_results(results)
+
+        add.assert_not_called()
+        self.assertEqual(len(merged.raw), 500)
+
+    def test_merging_twenty_thousand_results_takes_linear_time(self) -> None:
+        results = self.results(20_000, 10)
+        total = 20_000 * 10
+
+        started = time.perf_counter()
+        merged = merge_translation_results(results)
+        elapsed = time.perf_counter() - started
+
+        self.assertEqual(
+            lists_of(merged),
+            (
+                [f"t{index}" for index in range(total)],
+                ["⠁", "⠀"] * total,
+                [index for index in range(total) for _cell in range(2)],
+                [2 * index for index in range(total)],
+            ),
+        )
+        self.assertLess(elapsed, 5.0)
+
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run the structural tests and watch them fail.** Do not run the scale test on the old code: it needs minutes (162 s in the dry run).

```bash
$PY -m unittest tests.test_translation_result_core.LinearMergeTest.test_merge_builds_exactly_one_result tests.test_translation_result_core.LinearMergeTest.test_merge_never_adds_pairwise 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (the pairwise loop builds 501 results and calls `__add__`):

```text
FAIL: test_merge_builds_exactly_one_result (tests.test_translation_result_core.LinearMergeTest.test_merge_builds_exactly_one_result)
AssertionError: 501 != 1
FAIL: test_merge_never_adds_pairwise (tests.test_translation_result_core.LinearMergeTest.test_merge_never_adds_pairwise)
AssertionError: pairwise merge
Ran 2 tests
FAILED (failures=2)
```

- [ ] **Step 3: Add `concat` and route both merge paths through it.** `TranslationResult.concat(results)` extends four new lists with each result's lists, offsetting the positions by the lengths merged so far, and raises the existing `TypeError("not TranslateResult object")` for a non-result item; `__add__` keeps its own type check and returns `TranslationResult.concat((self, other))`; `merge_translation_results(translations)` becomes `return TranslationResult.concat(translations or ())`; `wrapping` and `literal_braille` import `TranslationResult` at module level.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/preprocessing/literal_braille.py b/client/conversion/preprocessing/literal_braille.py
index bb4cd04..0793047 100644
--- a/client/conversion/preprocessing/literal_braille.py
+++ b/client/conversion/preprocessing/literal_braille.py
@@ -1,10 +1,11 @@
+from translate import TranslationResult
+
+
 def is_unicode_braille(text: str) -> bool:
     return bool(text) and all("\u2800" <= character <= "\u28ff" for character in text)
 
 
 def build_literal_translation_result(source_text: str, braille_text: str):
-    from translate import TranslationResult
-
     braille = list(braille_text)
     return TranslationResult(
         [source_text],
diff --git a/client/conversion/wrapping.py b/client/conversion/wrapping.py
index 885e3ff..71d7f2b 100644
--- a/client/conversion/wrapping.py
+++ b/client/conversion/wrapping.py
@@ -1,12 +1,8 @@
-def merge_translation_results(translations):
-    from translate import TranslationResult
+from translate import TranslationResult
+
 
-    if not translations:
-        return TranslationResult([], [], [], [])
-    merged = TranslationResult([], [], [], [])
-    for segment in translations:
-        merged = merged + segment
-    return merged
+def merge_translation_results(translations):
+    return TranslationResult.concat(translations or ())
 
 
 def wrap_translation_results(translations, width: int) -> tuple[str, str]:
diff --git a/client/translate.py b/client/translate.py
index da8ad92..10bd641 100644
--- a/client/translate.py
+++ b/client/translate.py
@@ -40,25 +40,24 @@ class TranslationResult:
 		self.braille_to_raw_pos = braille_to_raw_pos
 		self.raw_to_braille_pos = raw_to_braille_pos
 
+	@classmethod
+	def concat(cls, results):
+		raw, braille, braille_to_raw_pos, raw_to_braille_pos = [], [], [], []
+		for result in results:
+			if not isinstance(result, TranslationResult):
+				raise TypeError("not TranslateResult object")
+			raw_offset = len(raw)
+			braille_offset = len(braille)
+			raw.extend(result.raw)
+			braille.extend(result.braille)
+			braille_to_raw_pos.extend(pos + raw_offset for pos in result.braille_to_raw_pos)
+			raw_to_braille_pos.extend(pos + braille_offset for pos in result.raw_to_braille_pos)
+		return cls(raw, braille, braille_to_raw_pos, raw_to_braille_pos)
+
 	def __add__(self, other):
 		if not isinstance(other, TranslationResult):
 			raise TypeError("not TranslateResult object")
-
-		raw_offset = len(self.raw)
-		braille_offset = len(self.braille)
-
-		raw = self.raw + other.raw
-		braille = self.braille + other.braille
-		braille_to_raw_pos = (
-			list(self.braille_to_raw_pos)
-			+ [pos + raw_offset for pos in other.braille_to_raw_pos]
-		)
-		raw_to_braille_pos = (
-			list(self.raw_to_braille_pos)
-			+ [pos + braille_offset for pos in other.raw_to_braille_pos]
-		)
-
-		return TranslationResult(raw, braille, braille_to_raw_pos, raw_to_braille_pos)
+		return TranslationResult.concat((self, other))
 
 	def __eq__(self, other):
 		if not isinstance(other, TranslationResult):
PATCH
```

- [ ] **Step 4: Verify (tests, unchanged golden output, spec acceptance 7).**

```bash
$PY -m unittest tests.test_translation_result_core tests.test_translation_golden tests.test_conversion_text_pipeline tests.test_conversion_service 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
sha256sum tests/fixtures/translation_golden.json
echo AC7; grep -rn "^\s\+from translate import" $REPO/client --include=*.py | grep -v tests/; echo end
```

Expected:

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 57 tests
FAILED (failures=1)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 780 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
AC7
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/translate.py client/conversion/wrapping.py client/conversion/preprocessing/literal_braille.py client/tests/test_translation_result_core.py
git -C $REPO commit -q -F - <<'EOF'
refactor: merge translation results in one pass

Add TranslationResult.concat, which builds one result from any number of
results with each element copied once, and route both
merge_translation_results and `+` through it. The pairwise loop copied
everything merged so far at every step (quadratic in the segment count).
The merged result still owns new lists, so post-processing it cannot
touch the cached dual-view segments. Import TranslationResult at module
level in wrapping and literal_braille; the local imports were vestigial.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: merge translation results in one pass
```

---

### Task 6: Move `DualViewSegment` to `conversion/output.py` (D-4, first half)

**Files:**
- Modify: `client/tests/test_translation_import_isolation.py`, `client/conversion/output.py`, `client/conversion/service.py`, `client/dual_view/model.py`, `client/dual_view/__init__.py`, tests `test_conversion_service`, `test_document_formats`, `test_dual_view_html`, `test_dual_view_model`, `test_gui_document_flows`

- [ ] **Step 1: Write the failing guard** (`test_conversion_does_not_import_dual_view`: a fresh interpreter imports `conversion.service`, `conversion.output` and `conversion.wrapping` and must not load `dual_view` or any `dual_view.*` module).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_translation_import_isolation.py b/client/tests/test_translation_import_isolation.py
index 6fa0f35..22d7729 100644
--- a/client/tests/test_translation_import_isolation.py
+++ b/client/tests/test_translation_import_isolation.py
@@ -40,6 +40,24 @@ assert "config" not in sys.modules, "config was imported"
 
         self.assertEqual(completed.returncode, 0, completed.stderr)
 
+    def test_conversion_does_not_import_dual_view(self) -> None:
+        script = """
+import sys
+import conversion.service
+import conversion.output
+import conversion.wrapping
+loaded = sorted(name for name in sys.modules if name == "dual_view" or name.startswith("dual_view."))
+assert not loaded, f"dual_view modules were imported: {loaded}"
+"""
+        completed = subprocess.run(
+            [sys.executable, "-c", script],
+            check=False,
+            capture_output=True,
+            text=True,
+        )
+
+        self.assertEqual(completed.returncode, 0, completed.stderr)
+
 
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run it and watch it fail.**

```bash
$PY -m unittest tests.test_translation_import_isolation 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected:

```text
FAIL: test_conversion_does_not_import_dual_view (tests.test_translation_import_isolation.TranslationImportIsolationTest.test_conversion_does_not_import_dual_view)
AssertionError: 1 != 0 : Traceback (most recent call last):
AssertionError: dual_view modules were imported: ['dual_view', 'dual_view.html', 'dual_view.model']
Ran 3 tests
FAILED (failures=1)
```

- [ ] **Step 3: Move the class.** `DualViewSegment` (same fields, `frozen=True`, `result: object`) is defined in `conversion/output.py` above `ConversionOutput`, whose `dual_view_segments` becomes `tuple[DualViewSegment, ...]`; `conversion/service.py` imports it from `conversion.output`; `dual_view/model.py` adds `from __future__ import annotations` and imports it only under `TYPE_CHECKING`; `dual_view/__init__.py` drops it from its import and `__all__`. No alias in `dual_view.model`: the five test modules switch to `from conversion.output import DualViewSegment` in the same step.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/output.py b/client/conversion/output.py
index b9ff14e..81bf63a 100644
--- a/client/conversion/output.py
+++ b/client/conversion/output.py
@@ -20,11 +20,17 @@ class ConversionRequest:
     charset_maps: dict[str, str]
 
 
+@dataclass(frozen=True)
+class DualViewSegment:
+    result: object
+    source_kind: str
+
+
 @dataclass(frozen=True)
 class ConversionOutput:
     display_text: str
     translation_results: tuple[object, ...]
-    dual_view_segments: tuple[object, ...] = ()
+    dual_view_segments: tuple[DualViewSegment, ...] = ()
 
 
 class ConversionStageError(Exception):
diff --git a/client/conversion/service.py b/client/conversion/service.py
index 67cfd7f..3736a53 100644
--- a/client/conversion/service.py
+++ b/client/conversion/service.py
@@ -5,6 +5,7 @@ from conversion.output import (
     ConversionOutput,
     ConversionRequest,
     ConversionStageError,
+    DualViewSegment,
     MapChar,
     convert_text_with_alignment as _convert_text_with_alignment,
 )
@@ -15,7 +16,6 @@ from conversion.wrapping import (
     merge_translation_results,
     wrap_translation_results,
 )
-from dual_view.model import DualViewSegment
 
 
 _translate_plain_text_segment = translate_plain_text_segment
diff --git a/client/dual_view/__init__.py b/client/dual_view/__init__.py
index eed1013..d95ed02 100644
--- a/client/dual_view/__init__.py
+++ b/client/dual_view/__init__.py
@@ -1,10 +1,9 @@
-from dual_view.model import AlignmentItem, AlignmentSegment, DualViewSegment, DualViewModel, build_dual_view_model
+from dual_view.model import AlignmentItem, AlignmentSegment, DualViewModel, build_dual_view_model
 from dual_view.html import render_dual_view_html
 
 __all__ = [
     "AlignmentItem",
     "AlignmentSegment",
-    "DualViewSegment",
     "DualViewModel",
     "build_dual_view_model",
     "render_dual_view_html",
diff --git a/client/dual_view/model.py b/client/dual_view/model.py
index 745f32b..ef431ec 100644
--- a/client/dual_view/model.py
+++ b/client/dual_view/model.py
@@ -1,13 +1,12 @@
+from __future__ import annotations
+
 from dataclasses import dataclass
-from typing import Callable, Iterable
+from typing import TYPE_CHECKING, Callable, Iterable
 
 from conversion.math_service import latex_to_mathml
 
-
-@dataclass(frozen=True)
-class DualViewSegment:
-    result: object
-    source_kind: str
+if TYPE_CHECKING:
+	from conversion.output import DualViewSegment
 
 
 @dataclass(frozen=True)
diff --git a/client/tests/test_conversion_service.py b/client/tests/test_conversion_service.py
index cc37749..a52c56d 100644
--- a/client/tests/test_conversion_service.py
+++ b/client/tests/test_conversion_service.py
@@ -6,7 +6,7 @@ from pathlib import Path
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
 from config import DEFAULT_CHARSET_MAPS
-from dual_view.model import DualViewSegment
+from conversion.output import DualViewSegment
 from conversion.service import (
     ConversionOutput,
     ConversionRequest,
diff --git a/client/tests/test_document_formats.py b/client/tests/test_document_formats.py
index 1cb4479..1467af4 100644
--- a/client/tests/test_document_formats.py
+++ b/client/tests/test_document_formats.py
@@ -5,6 +5,7 @@ from pathlib import Path
 from tempfile import TemporaryDirectory
 from unittest.mock import Mock, patch
 
+from conversion.output import DualViewSegment
 from documents.formats import (
     ALL_SUPPORTED_FILES_LABEL,
     DOCUMENT_FORMATS,
@@ -17,7 +18,6 @@ from documents.formats import (
     get_importable_formats,
 )
 from documents.workspace import Document
-from dual_view.model import DualViewSegment
 
 
 class DocumentFormatsTest(unittest.TestCase):
diff --git a/client/tests/test_dual_view_html.py b/client/tests/test_dual_view_html.py
index 55417c2..69565c5 100644
--- a/client/tests/test_dual_view_html.py
+++ b/client/tests/test_dual_view_html.py
@@ -1,8 +1,9 @@
 import unittest
 from unittest.mock import Mock
 
+from conversion.output import DualViewSegment
 from dual_view.html import render_dual_view_html
-from dual_view.model import DualViewSegment, build_dual_view_model
+from dual_view.model import build_dual_view_model
 
 
 class TranslationResult:
diff --git a/client/tests/test_dual_view_model.py b/client/tests/test_dual_view_model.py
index 9550018..59cab07 100644
--- a/client/tests/test_dual_view_model.py
+++ b/client/tests/test_dual_view_model.py
@@ -1,7 +1,8 @@
 import unittest
 
 from adapters.translation.fallback import FallbackTextTranslator
-from dual_view.model import DualViewSegment, build_dual_view_model
+from conversion.output import DualViewSegment
+from dual_view.model import build_dual_view_model
 
 
 class TranslationResult:
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index a71e412..ec960a0 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -32,9 +32,10 @@ from settings.state import DotExpressSettingsSnapshot
 from settings.translation import TranslationSettings
 from settings.view import ViewSettings
 from conversion.math_service import latex_to_mathml
+from conversion.output import DualViewSegment
 from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
 from dual_view.html import render_dual_view_html
-from dual_view.model import DualViewSegment, build_dual_view_model
+from dual_view.model import build_dual_view_model
 
 
 def make_snapshot(
PATCH
```

- [ ] **Step 4: Verify (tests, unchanged golden output, spec acceptance 6 for `conversion`).**

```bash
$PY -m unittest tests.test_translation_import_isolation tests.test_translation_golden tests.test_conversion_service tests.test_document_formats tests.test_dual_view_html tests.test_dual_view_model tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
sha256sum tests/fixtures/translation_golden.json
echo AC6a; grep -rnE "(from|import) dual_view" $REPO/client/conversion; echo end
```

Expected:

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 213 tests
FAILED (failures=1, skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 781 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
AC6a
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/conversion/output.py client/conversion/service.py client/dual_view/model.py client/dual_view/__init__.py client/tests/test_translation_import_isolation.py client/tests/test_conversion_service.py client/tests/test_document_formats.py client/tests/test_dual_view_html.py client/tests/test_dual_view_model.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'EOF'
refactor: move DualViewSegment to conversion output

The conversion service produces DualViewSegment, so define it next to
ConversionOutput and stop importing dual_view from conversion. The dual
view model keeps the name only for type checking. Tests import the class
from conversion.output.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: move DualViewSegment to conversion output
```

---

### Task 7: Inject the MathML converter into the dual-view model (D-4, second half)

**Files:**
- Modify: `client/tests/test_translation_import_isolation.py`, `client/tests/test_dual_view_model.py`, `client/tests/test_dual_view_html.py`, `client/tests/test_gui_document_flows.py`, `client/dual_view/model.py`, `client/gui.py`, `client/documents/formats.py`

- [ ] **Step 1: Write the failing tests and update the call sites.** New: `test_dual_view_does_not_import_conversion_or_config` (a fresh interpreter imports `dual_view`, `dual_view.model` and `dual_view.html` and must load no `conversion`, `conversion.*` or `config` module) and `test_mathml_converter_is_required` (`build_dual_view_model([])` raises `TypeError` naming `mathml_converter`). The 20 converter-less calls pass a converter now (the keyword is already accepted): `reject_mathml` in the 13 + 3 text-only calls of `test_dual_view_model.py` and `test_dual_view_html.py`, `latex_to_mathml` in the 4 export comparisons of `test_gui_document_flows.py`.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_dual_view_html.py b/client/tests/test_dual_view_html.py
index 69565c5..780af0c 100644
--- a/client/tests/test_dual_view_html.py
+++ b/client/tests/test_dual_view_html.py
@@ -6,6 +6,10 @@ from dual_view.html import render_dual_view_html
 from dual_view.model import build_dual_view_model
 
 
+def reject_mathml(latex):
+	raise AssertionError(f"text items must not be converted to MathML: {latex!r}")
+
+
 class TranslationResult:
 	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
 		self.raw = raw
@@ -19,7 +23,7 @@ class DualViewHtmlTest(unittest.TestCase):
 		result = TranslationResult(list(raw), list(braille), [0] * len(braille), positions)
 		return render_dual_view_html(build_dual_view_model([
 			DualViewSegment(result=result, source_kind=source_kind),
-		]))
+		], mathml_converter=reject_mathml))
 
 	def test_renders_source_text_from_raw_text(self):
 		output = self.render("a", "⠁", [0])
@@ -74,7 +78,7 @@ class DualViewHtmlTest(unittest.TestCase):
 		output = render_dual_view_html(build_dual_view_model([
 			DualViewSegment(result=first, source_kind="text"),
 			DualViewSegment(result=second, source_kind="text"),
-		]))
+		], mathml_converter=reject_mathml))
 
 		self.assertNotIn('<section class="segment">', output)
 		self.assertEqual(output.count('class="cell"'), 3)
@@ -93,7 +97,7 @@ class DualViewHtmlTest(unittest.TestCase):
 
 	def test_renders_empty_state(self):
 		output = render_dual_view_html(
-			build_dual_view_model([]),
+			build_dual_view_model([], mathml_converter=reject_mathml),
 			empty_message="此文件沒有可顯示的轉換資料。",
 		)
 
diff --git a/client/tests/test_dual_view_model.py b/client/tests/test_dual_view_model.py
index 59cab07..86f30df 100644
--- a/client/tests/test_dual_view_model.py
+++ b/client/tests/test_dual_view_model.py
@@ -5,6 +5,10 @@ from conversion.output import DualViewSegment
 from dual_view.model import build_dual_view_model
 
 
+def reject_mathml(latex):
+	raise AssertionError(f"text items must not be converted to MathML: {latex!r}")
+
+
 class TranslationResult:
 	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
 		self.raw = raw
@@ -29,7 +33,7 @@ class DualViewModelTest(unittest.TestCase):
 		)
 
 	def test_builds_one_item_per_raw_element(self):
-		model = build_dual_view_model([self.text_segment("ab", "⠁⠃", [0, 1])])
+		model = build_dual_view_model([self.text_segment("ab", "⠁⠃", [0, 1])], mathml_converter=reject_mathml)
 
 		self.assertEqual([item.raw_text for item in model.segments[0].items], ["a", "b"])
 		self.assertEqual([item.braille_text for item in model.segments[0].items], ["⠁", "⠃"])
@@ -38,13 +42,13 @@ class DualViewModelTest(unittest.TestCase):
 		model = build_dual_view_model([
 			self.text_segment("a", "⠁", [0]),
 			self.text_segment("b", "⠃", [0]),
-		])
+		], mathml_converter=reject_mathml)
 
 		self.assertEqual(len(model.segments), 2)
 		self.assertEqual([segment.source_text for segment in model.segments], ["a", "b"])
 
 	def test_supports_multiple_and_empty_braille_ranges(self):
-		model = build_dual_view_model([self.text_segment("abc", "⠁⠂⠉", [0, 2, 2])])
+		model = build_dual_view_model([self.text_segment("abc", "⠁⠂⠉", [0, 2, 2])], mathml_converter=reject_mathml)
 
 		items = model.segments[0].items
 		self.assertEqual(items[0].braille_text, "⠁⠂")
@@ -52,7 +56,7 @@ class DualViewModelTest(unittest.TestCase):
 		self.assertEqual(items[2].braille_text, "⠉")
 
 	def test_keeps_spaces_and_newlines_as_source_items(self):
-		model = build_dual_view_model([self.text_segment("a \nb", "⠁⠀⠃", [0, 1, 2, 2])])
+		model = build_dual_view_model([self.text_segment("a \nb", "⠁⠀⠃", [0, 1, 2, 2])], mathml_converter=reject_mathml)
 
 		self.assertEqual([item.raw_text for item in model.segments[0].items], ["a", " ", "\n", "b"])
 		self.assertTrue(model.segments[0].items[1].is_space)
@@ -64,14 +68,18 @@ class DualViewModelTest(unittest.TestCase):
 				result=TranslationResult(["word"], list("⠺⠕⠗⠙"), [0, 0, 0, 0], [0]),
 				source_kind="text",
 			),
-		])
+		], mathml_converter=reject_mathml)
 
 		self.assertEqual(len(model.segments[0].items), 1)
 		self.assertEqual(model.segments[0].items[0].raw_text, "word")
 		self.assertEqual(model.segments[0].items[0].braille_text, "⠺⠕⠗⠙")
 
+	def test_mathml_converter_is_required(self):
+		with self.assertRaisesRegex(TypeError, "mathml_converter"):
+			build_dual_view_model([])
+
 	def test_empty_results_produce_empty_document(self):
-		self.assertEqual(build_dual_view_model([]).segments, ())
+		self.assertEqual(build_dual_view_model([], mathml_converter=reject_mathml).segments, ())
 
 	def test_multi_character_raw_element_renders_as_one_card(self):
 		model = build_dual_view_model([
@@ -79,14 +87,14 @@ class DualViewModelTest(unittest.TestCase):
 				result=TranslationResult(["我們", "這", "一家"], ["b1", "b2", "b3"], [0, 0, 0], [0, 1, 2]),
 				source_kind="text",
 			),
-		])
+		], mathml_converter=reject_mathml)
 
 		self.assertEqual(len(model.segments[0].items), 3)
 		self.assertEqual([item.raw_text for item in model.segments[0].items], ["我們", "這", "一家"])
 		self.assertEqual([item.braille_text for item in model.segments[0].items], ["b1", "b2", "b3"])
 
 	def test_single_space_is_space_card(self):
-		model = build_dual_view_model([self.text_segment(" ", "⠀", [0])])
+		model = build_dual_view_model([self.text_segment(" ", "⠀", [0])], mathml_converter=reject_mathml)
 
 		self.assertEqual(len(model.segments[0].items), 1)
 		item = model.segments[0].items[0]
@@ -94,7 +102,7 @@ class DualViewModelTest(unittest.TestCase):
 		self.assertTrue(item.is_space)
 
 	def test_single_newline_is_break(self):
-		model = build_dual_view_model([self.text_segment("\n", "", [0])])
+		model = build_dual_view_model([self.text_segment("\n", "", [0])], mathml_converter=reject_mathml)
 
 		self.assertEqual(len(model.segments[0].items), 1)
 		item = model.segments[0].items[0]
@@ -107,7 +115,7 @@ class DualViewModelTest(unittest.TestCase):
 				result=TranslationResult(["我們 這 一家"], list("b1"), [0, 0], [0]),
 				source_kind="text",
 			),
-		])
+		], mathml_converter=reject_mathml)
 
 		self.assertEqual(len(model.segments[0].items), 1)
 		self.assertEqual(model.segments[0].items[0].raw_text, "我們 這 一家")
@@ -117,7 +125,7 @@ class DualViewModelTest(unittest.TestCase):
 		dangling = self.text_segment("xy", "⠁⠃", [0, 99])
 
 		with self.assertRaises(ValueError):
-			build_dual_view_model([dangling])
+			build_dual_view_model([dangling], mathml_converter=reject_mathml)
 
 	def test_unknown_source_kind_raises_value_error(self):
 		segment = DualViewSegment(
@@ -126,7 +134,7 @@ class DualViewModelTest(unittest.TestCase):
 		)
 
 		with self.assertRaisesRegex(ValueError, "source_kind"):
-			build_dual_view_model([segment])
+			build_dual_view_model([segment], mathml_converter=reject_mathml)
 
 	def test_fallback_character_mapping_builds_dual_view_segments(self) -> None:
 		result = FallbackTextTranslator().translate(
@@ -137,7 +145,7 @@ class DualViewModelTest(unittest.TestCase):
 
 		model = build_dual_view_model([
 			DualViewSegment(result=result, source_kind="text"),
-		])
+		], mathml_converter=reject_mathml)
 
 		self.assertEqual(
 			[
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index ec960a0..f17de34 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -1363,12 +1363,12 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
             self.assertEqual((root / "nested" / "alpha.brl").read_bytes(), "⠁⠃".encode("utf-8"))
 
             frame._export_coordinator.write_document(root / "alpha.html", Document("alpha", "text", "b"), "html")
-            cached_html = render_dual_view_html(build_dual_view_model(results))
+            cached_html = render_dual_view_html(build_dual_view_model(results, mathml_converter=latex_to_mathml))
             self.assertEqual((root / "alpha.html").read_bytes(), cached_html.encode("utf-8"))
             self.assertIn('<span class="source">a</span>', cached_html)
 
             frame._export_coordinator.write_document(root / "beta.html", Document("beta", "text", "b"), "html")
-            empty_html = render_dual_view_html(build_dual_view_model(()))
+            empty_html = render_dual_view_html(build_dual_view_model((), mathml_converter=latex_to_mathml))
             self.assertEqual((root / "beta.html").read_bytes(), empty_html.encode("utf-8"))
             self.assertNotEqual(cached_html, empty_html)
 
@@ -1420,11 +1420,11 @@ class DocumentMenuAndExportCharacterizationTest(unittest.TestCase):
 
             self.assertEqual(
                 (root / "alpha.html").read_text(encoding="utf-8"),
-                render_dual_view_html(build_dual_view_model(results)),
+                render_dual_view_html(build_dual_view_model(results, mathml_converter=latex_to_mathml)),
             )
             self.assertEqual(
                 (root / "beta.html").read_text(encoding="utf-8"),
-                render_dual_view_html(build_dual_view_model(())),
+                render_dual_view_html(build_dual_view_model((), mathml_converter=latex_to_mathml)),
             )
         frame.show_info.assert_called_once_with(
             gui._(ExportBatchResult().summary_template),
diff --git a/client/tests/test_translation_import_isolation.py b/client/tests/test_translation_import_isolation.py
index 22d7729..159f724 100644
--- a/client/tests/test_translation_import_isolation.py
+++ b/client/tests/test_translation_import_isolation.py
@@ -58,6 +58,27 @@ assert not loaded, f"dual_view modules were imported: {loaded}"
 
         self.assertEqual(completed.returncode, 0, completed.stderr)
 
+    def test_dual_view_does_not_import_conversion_or_config(self) -> None:
+        script = """
+import sys
+import dual_view
+import dual_view.model
+import dual_view.html
+loaded = sorted(
+    name for name in sys.modules
+    if name in {"conversion", "config"} or name.startswith("conversion.")
+)
+assert not loaded, f"conversion or config modules were imported: {loaded}"
+"""
+        completed = subprocess.run(
+            [sys.executable, "-c", script],
+            check=False,
+            capture_output=True,
+            text=True,
+        )
+
+        self.assertEqual(completed.returncode, 0, completed.stderr)
+
 
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run them and watch the two new tests fail.**

```bash
$PY -m unittest tests.test_translation_import_isolation tests.test_dual_view_model tests.test_dual_view_html tests.test_gui_document_flows 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (everything else passes, which shows that `reject_mathml` is never called for text):

```text
FAIL: test_dual_view_does_not_import_conversion_or_config (tests.test_translation_import_isolation.TranslationImportIsolationTest.test_dual_view_does_not_import_conversion_or_config)
AssertionError: 1 != 0 : Traceback (most recent call last):
AssertionError: conversion or config modules were imported: ['config', 'conversion', 'conversion.math_braille_codes', 'conversion.math_service']
FAIL: test_mathml_converter_is_required (tests.test_dual_view_model.DualViewModelTest.test_mathml_converter_is_required)
AssertionError: TypeError not raised
Ran 171 tests
FAILED (failures=2, skipped=2)
```

- [ ] **Step 3: Make the converter required and wire it in the two callers.** `build_dual_view_model(segments, *, mathml_converter)` has no default (keyword-only, no `None`); `dual_view/model.py` drops `from conversion.math_service import latex_to_mathml`; `gui.py` and `documents/formats.py` import `latex_to_mathml` at module level and pass it, as they did implicitly before. `ExportContext` does not change.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/documents/formats.py b/client/documents/formats.py
index 2afa6c7..47140c4 100644
--- a/client/documents/formats.py
+++ b/client/documents/formats.py
@@ -5,6 +5,7 @@ from pathlib import Path
 from collections.abc import Callable
 from typing import TYPE_CHECKING
 
+from conversion.math_service import latex_to_mathml
 from dual_view.html import render_dual_view_html
 from dual_view.model import build_dual_view_model
 from i18n import N_
@@ -103,7 +104,7 @@ def _write_brl(path: Path | str, document: Document, context: ExportContext) ->
 def _write_html(path: Path | str, document: Document, context: ExportContext) -> Path:
     del document
     destination = Path(path)
-    html = render_dual_view_html(build_dual_view_model(context.dual_view_results))
+    html = render_dual_view_html(build_dual_view_model(context.dual_view_results, mathml_converter=latex_to_mathml))
     destination.write_text(html, encoding="utf-8")
     return destination
 
diff --git a/client/dual_view/model.py b/client/dual_view/model.py
index ef431ec..5da09a1 100644
--- a/client/dual_view/model.py
+++ b/client/dual_view/model.py
@@ -3,8 +3,6 @@ from __future__ import annotations
 from dataclasses import dataclass
 from typing import TYPE_CHECKING, Callable, Iterable
 
-from conversion.math_service import latex_to_mathml
-
 if TYPE_CHECKING:
 	from conversion.output import DualViewSegment
 
@@ -40,7 +38,11 @@ def _token_braille_end(raw_to_braille_pos: list[int], token_index: int, braille_
 	return braille_length
 
 
-def build_dual_view_model(segments: Iterable[DualViewSegment], *, mathml_converter: Callable[[str], str] = latex_to_mathml) -> DualViewModel:
+def build_dual_view_model(
+	segments: Iterable[DualViewSegment],
+	*,
+	mathml_converter: Callable[[str], str],
+) -> DualViewModel:
 	result_segments: list[AlignmentSegment] = []
 
 	for segment in segments:
diff --git a/client/gui.py b/client/gui.py
index a9d135a..76ddd35 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -10,6 +10,7 @@ from i18n import _, resource_path
 from app_paths import ApplicationDataError, prepare_application_directories
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.provider import build_default_translation_runtime
+from conversion.math_service import latex_to_mathml
 from conversion.presenter import ConversionPresenter
 from conversion.service import ConversionRequest
 from conversion.preprocessing.user_script import preprocessing_script_path
@@ -329,7 +330,7 @@ class BrailleFrame(wx.Frame):
 		controller = self._document_controller
 		results = controller.get_dual_view_results(controller.open_document_name)
 		return render_dual_view_html(
-			build_dual_view_model(results),
+			build_dual_view_model(results, mathml_converter=latex_to_mathml),
 			empty_message=_("No conversion data is available for this document."),
 		)
 
PATCH
```

- [ ] **Step 4: Verify (tests, unchanged golden output, spec acceptance 6 for `dual_view`).**

```bash
$PY -m unittest tests.test_translation_import_isolation tests.test_dual_view_model tests.test_dual_view_html tests.test_gui_document_flows tests.test_document_formats tests.test_export_coordinator tests.test_translation_golden 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
sha256sum tests/fixtures/translation_golden.json
echo AC6a; grep -rnE "(from|import) dual_view" $REPO/client/conversion; echo AC6b; grep -rnE "(from|import) conversion" $REPO/client/dual_view | sed "s#$REPO/##"; echo end
```

Expected (AC6b: only the `TYPE_CHECKING` import):

```text
Ran 216 tests
OK (skipped=2)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 783 tests
FAILED (failures=1, skipped=9)
e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd  tests/fixtures/translation_golden.json
AC6a
AC6b
client/dual_view/model.py:7:	from conversion.output import DualViewSegment
end
```

- [ ] **Step 5: Commit.**

```bash
git -C $REPO add client/dual_view/model.py client/gui.py client/documents/formats.py client/tests/test_translation_import_isolation.py client/tests/test_dual_view_model.py client/tests/test_dual_view_html.py client/tests/test_gui_document_flows.py
git -C $REPO commit -q -F - <<'EOF'
refactor: inject the MathML converter into the dual-view model

build_dual_view_model now takes mathml_converter as a required keyword
argument instead of defaulting to conversion.math_service. The dual-view
window and the HTML export pass latex_to_mathml, as they did implicitly
before, so importing dual_view no longer loads conversion or config.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C $REPO status --short
git -C $REPO log --format=%s -1
```

Expected:

```text
refactor: inject the MathML converter into the dual-view model
```

---

### Task 8: Final verification (spec acceptance criteria, no commit)

- [ ] **Step 1: AC1, the roadmap verification and the related modules.** `tests.test_translation_result` contributes 0 tests (pytest-style, P2-5).

```bash
$PY -m unittest tests.test_translation_result tests.test_translation_result_core tests.test_dual_view_model tests.test_dual_view_html tests.test_conversion_service -v 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_translation_golden tests.test_translation_import_isolation tests.test_conversion_language_explicit tests.test_document_formats tests.test_gui_document_flows tests.test_export_coordinator tests.test_conversion_text_pipeline 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected:

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 65 tests
FAILED (failures=1)
Ran 203 tests
OK (skipped=2)
```

- [ ] **Step 2: AC2, the fixture never changed after Task 2, and the golden test passes at every commit since.** The loop checks out each later commit's files into a throwaway worktree.

```bash
STEP2=$(git -C $REPO log --format=%h -1 --grep='^test: characterize translation and dual-view output')
git -C $REPO diff --stat $STEP2 HEAD -- client/tests/fixtures/translation_golden.json client/tests/test_translation_golden.py; echo AC2-diff-end
rm -rf $T/wt && git -C $REPO worktree add -q --detach $T/wt $STEP2 && mkdir -p $T/wt/client/log
for c in $(git -C $REPO rev-list --reverse $STEP2~1..HEAD); do git -C $T/wt checkout -q $c; (cd $T/wt/client && echo "$(git log --format=%s -1): $($PY -B -m unittest tests.test_translation_golden 2>&1 | tail -1)"); done
git -C $REPO worktree remove --force $T/wt
```

Expected:

```text
AC2-diff-end
test: characterize translation and dual-view output: OK
refactor: share TranslationResult constants: OK
fix: compare TranslationResult only with results: OK
refactor: merge translation results in one pass: OK
refactor: move DualViewSegment to conversion output: OK
refactor: inject the MathML converter into the dual-view model: OK
```

- [ ] **Step 3: AC3, the former M-1 pair in both orders, and AC4, the full suite.**

```bash
$PY -m unittest tests.test_translation_result_core tests.test_conversion_service 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_conversion_service tests.test_translation_result_core 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest discover -s tests 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^OK|^FAILED' | sed -E 's/ in [0-9.]+s$//'
```

Expected (754 + 29 new tests):

```text
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 41 tests
FAILED (failures=1)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 41 tests
FAILED (failures=1)
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
Ran 783 tests
FAILED (failures=1, skipped=9)
```

- [ ] **Step 4: AC5, 20 shuffled seeds.**

```bash
for s in $(seq 0 19); do $PY -B -I $SP/shuffle_harness.py $s; done | grep -v '^order=' | sed -E 's/^seed=[0-9]+ //' | LC_ALL=C sort | uniq -c
```

Expected (every seed runs 783 tests; the only failing test is the P2-5 case):

```text
     20 BAD test_translate_with_language_does_not_duplicate_existing_spaces_around_math (test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
     20 ran=783 failures=1 errors=0 skipped=9
```

- [ ] **Step 5: AC6-AC9, the msgid scan and the pytest-style module.**

```bash
echo AC6a; grep -rnE "(from|import) dual_view" $REPO/client/conversion
echo AC6b; grep -rnE "(from|import) conversion" $REPO/client/dual_view | sed "s#$REPO/##"
echo AC7; grep -rn "^\s\+from translate import" $REPO/client --include=*.py | grep -v tests/
echo AC8; grep -n "self\.\(LEFT\|RIGHT\|MIDDLE\|END\)_[A-Z_]* = \|self.lang_blocks = " $REPO/client/translate.py
echo AC9; git -C $REPO diff main --stat -- client/locales scripts client/braille
echo msgids; $PY -I $SP/p12/tools/msgid_scan.py $REPO/client --compare $T/base_msgids.json | grep -E '^source|SAVED'
echo pytest-style; $PY -B $T/tools/run_pytest_style.py tests.test_translation_result > $T/pytest_style_after.txt; diff $T/pytest_style_before.txt $T/pytest_style_after.txt && tail -1 $T/pytest_style_after.txt
echo end
```

Expected (nothing after AC6a, AC7, AC8 and AC9; the msgid set unchanged at 353; the same 8 passes and 5 failures as before):

```text
AC6a
AC6b
client/dual_view/model.py:7:	from conversion.output import DualViewSegment
AC7
AC8
AC9
msgids
source msgids: 353
SOURCE == SAVED
pytest-style
passed=8 failed=5
end
```

- [ ] **Step 6: The branch.**

```bash
git -C $REPO status --short
git -C $REPO log --format=%s -8
git -C $REPO diff --stat HEAD~7 HEAD | tail -1
```

Expected:

```text
refactor: inject the MathML converter into the dual-view model
refactor: move DualViewSegment to conversion output
refactor: merge translation results in one pass
fix: compare TranslationResult only with results
refactor: share TranslationResult constants
test: characterize translation and dual-view output
test: run the translate import check in a subprocess
docs: plan translation result layout
 19 files changed, 7366 insertions(+), 171 deletions(-)
```

Not verifiable on Linux (Windows verification debt, from the spec): on a packaged build, convert a long mixed zh/en document with inline math with `zh-tw.ctb` and `en-ueb-g2.ctb` before and after and compare the Braille Result text, the ASCII mode and the exported BRL byte for byte (and note how many tokens `reclean_braille_endspace` trims, known defect 3); open the Dual View window and export HTML for a document with math and compare with the pre-change output; run `tests.test_liblouis_runtime`, `tests.test_translation_language_result` and `tests.test_language_detection_translation` and compare with the baseline (the last two already fail for the reasons in the spec). No menu, dialog or string changes, so no screenshots and no `generate-pot.bat` run are needed.
