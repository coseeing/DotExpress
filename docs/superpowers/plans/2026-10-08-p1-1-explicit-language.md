# Explicit Conversion Language (P1-1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The conversion stack stops reading the conversion language and the charset-to-language map from the global `config` module. `BrailleFrame._build_conversion_request` (and `main.run_demo`) read `config.get_lang()` and `config.get_charset_maps()` once per request and put them on `ConversionRequest` as `lang` and `charset_maps`; every layer below receives them as required arguments. `conversion/text/pipeline.py`, `languageDetection/__init__.py`, `conversion/mathcat_adapter.py` and `braille/tables/__init__.py` no longer import `config`. Same braille output for the same `config.json`, `TEXT2BRAILLE_LANG` and input; no user-facing string changes; `.po`/`.mo` untouched.

**Architecture:** Characterization first, then bottom-up. Task 1 pins today's language-dependent results with tests that still patch `config`. Tasks 2-5 convert one consumer at a time to an explicit argument (math braille codes leaf module, `getDefaultTableForCurLang`, the MathCAT chain, `LanguageDetector`); in each of these commits the config read moves exactly one level up, into the consumer's direct caller, so every commit is green and the app keeps working. Task 6 adds the two fields to `ConversionRequest` and fills them in the UI layer. Task 7 threads them from the request through `conversion.output`, `conversion.service` and the text pipeline and deletes the two temporary reads. Task 8 is the spec's acceptance run.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `tempfile`, `subprocess`, `dataclasses`, `typing.Mapping`). wxPython is not installed; the frame loads through the P0-4 `tests/wx_stub.py` scope that `tests/test_gui_document_flows.py` already uses. MathCAT and liblouis load only on Windows; on Linux the math chain is tested with fakes.

**Spec:** `docs/superpowers/specs/2026-10-08-p1-1-explicit-language-design.md` (authoritative, commit `f25698c`). The corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p1-1-explicit-language`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change (31, nothing else): `client/conversion/math_braille_codes.py` (new), `client/config.py`, `client/braille/tables/__init__.py`, `client/adapters/translation/contracts.py`, `client/adapters/translation/fallback.py`, `client/adapters/translation/mathcat.py`, `client/conversion/math_service.py`, `client/conversion/mathcat_adapter.py`, `client/conversion/service.py`, `client/conversion/output.py`, `client/conversion/text/pipeline.py`, `client/languageDetection/__init__.py`, `client/gui.py`, `client/main.py`; tests `test_braille_tables_default_lang.py` (new), `test_conversion_language_explicit.py` (new), `test_math_braille_codes.py` (new), `test_conversion_jobs.py`, `test_conversion_service.py`, `test_conversion_text_pipeline.py`, `test_gui_document_flows.py`, `test_language_detection_char_langinfo.py`, `test_language_detection_translation.py` (Windows-only), `test_language_detection_unicode_braille.py`, `test_main_demo.py`, `test_math_service.py`, `test_math_translation_adapter.py`, `test_mathcat_adapter.py`, `test_translation_fallback.py`, `test_translation_import_isolation.py`, `test_translation_language_result.py` (Windows-only). Never touch `client/braille/tables/__tables.py`, `client/braille/liblouis/`, `client/locales/`, `client_init.py`, `settings/*`, `conversion/jobs.py`, `dual_view/*`, `documents/*`.
- Indentation per file, unchanged: TABS in `languageDetection/__init__.py`, `conversion/mathcat_adapter.py`, `conversion/math_service.py`, `braille/tables/__init__.py`, `gui.py`, `tests/test_conversion_jobs.py` and the two Windows-only tests; 4 spaces everywhere else. `client/braille/tables/__init__.py` has CRLF line endings; Task 3 edits it with a byte-exact Python script, never with an editor that normalizes line endings.
- The patches carry the exact characters (tabs, single-space context lines, CJK and braille literals already used by the surrounding tests). Run every block as it is; do not retype. If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- New test text is ASCII except CJK sample text and literals the existing tests already use; the arrow and the braille blank are written as the escapes for U+2192 and U+2800.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-output blocks come from the dry run (paths shown for the repo at `/workspace/DotExpress`). "Red" summaries use `LC_ALL=C sort | uniq -c`, so the order and the counts are exact.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p11impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today. No `client/config.json` exists on this box and `TEXT2BRAILLE_LANG` is unset; no test added here depends on either.
- Baseline (re-verified at `f25698c`, the spec commit; code identical to `7f0d127`): `$PY -m unittest discover -s tests` gives `Ran 554 tests`, `FAILED (failures=1, skipped=7)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. It stays failing with the same assertion after every task.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: a "truthy" charset-map lookup would change behavior.** The spec has `find_language_for_charset` return `self.charset_maps.get(configKey)` only if it is truthy and claims production is unaffected. It is not: `config._get_dict_setting` accepts any string, so a hand-edited `"CJKCharactersLanguage": ""` in `config.json` reaches the detector today, which then emits `LangChangeCommand("")` (characterized: detector `["en", "zh_TW"]`, language `en`, text `"A中"` gives `["A", "", "中"]`; the pipeline then falls back to the default table). A truthy check would emit `zh_TW` instead. The plan keeps today's behavior exactly and still avoids the `KeyError` for a missing key: `if configKey in self.charset_maps: return self.charset_maps[configKey]`, else fall through to `return langs[0]`. Pinned by `test_empty_charset_map_value_is_used_as_is` (Task 1, characterized on the old code) and `test_missing_charset_map_entry_falls_back_to_first_block_language` (Task 5).
2. **Factual correction: `tests/test_main_demo.py` already exists** (one test, `test_demo_uses_alignment_conversion_output`). Spec test 12 is added to it as `test_demo_request_carries_language_settings`; no new file. The existing test is left as it is (it does not look at the language).
3. **Factual correction: `client/braille/tables/__init__.py` uses CRLF line endings** (so do `braille/__init__.py` and `braille/tables/__tables.py`; no other `.py` file in `client/` does). A text-mode rewrite turns the whole file into a 251-line diff. Task 3 therefore edits it with a byte-level Python script that keeps CRLF; the resulting diff is `4 insertions(+), 4 deletions(-)`. Minor line-number slips in the spec, no effect: the upstream comment `# import config` is at line 17 of that file (spec: 18) and at line 8 of `languageDetection/__init__.py` (spec: 10). `tests/test_conversion_jobs.py` uses tabs (the spec lists only the two Windows-only tests as tab-indented).
4. **Refinement: commit sequence.** The spec describes the end state. To keep every commit green and the app working, Tasks 4 and 5 move the config read one level up as a temporary step: after Task 4, `conversion/service.py` imports `get_lang` and passes `language=get_lang()` to the math translator for each math segment (the same moment the adapter read it before); after Task 5, `conversion/text/pipeline.py` passes `default_lang=config.get_lang(), charset_maps=config.get_charset_maps()` to the detector. Task 7 removes both. Task 6 adds the request fields while nothing below reads them yet.
5. **Refinement: Task 2 has its own test.** The spec adds `conversion/math_braille_codes.py` without a test; `tests/test_math_braille_codes.py` (2 tests) pins the values and that `config` re-exports the same objects. The re-export is placed in `config.py`'s top import block (with `# noqa: F401  (re-exported)`) instead of at the old line 35; the attributes and values are identical.
6. **Refinement: spec test 11 without the aliasing assertion.** `_build_conversion_request` passes on whatever `get_charset_maps()` returns (spec design: no copy); two requests never share a map because `config.get_charset_maps()` builds a new dict on every call. With `gui.get_charset_maps` patched, an `assertIsNot` would only test the mock, so `test_conversion_request_reads_language_settings_per_request` asserts the per-request values and that each value is read once per request (call counts 2 and 2) instead.
7. **Refinement: characterization tests.** Task 1 adds 10 tests on the unchanged code (they pass immediately; their expected values are today's results): detector (3: preferred full language from the current language, `"Hello 中文 "` under `en` and `zh_TW`, empty map value), pipeline (2: the U+2192 arrow under `en`/`zh_TW`, `"A中"` with `CJKCharactersLanguage` `zh`/`ja`), MathCAT (2: `en_US` gives `en-us`; two calls set their own language), default table (1), end-to-end (2: mixed text `"Hello 中文 $1$"`, the arrow). Later tasks convert each one to the explicit argument with the same expected values. Spec tests 1-12 all exist at the end; spec test 1 and 2 live in `test_conversion_language_explicit.py` as `test_same_request_gives_same_output_in_any_environment` and `test_non_detecting_text_follows_request_language`.
8. **Refinement: the end-to-end fakes import `TranslationResult` per call.** `tests/test_translation_result_core.py` re-imports `translate`, after which `conversion.wrapping` (lazy import) rejects results built from the old class (`TypeError: not TranslateResult object`). This already makes 8 `test_conversion_service` tests error in some module orders on the baseline (shuffled-order harness, seeds 4 and 6-9 of 10); it is pre-existing and out of scope. The new end-to-end fakes avoid it, so the new tests pass in every order tried.
9. **Refinement: `LanguageDetector`'s `char_langinfo` becomes keyword-only** (it follows the new `*`). No caller passes it positionally (both uses in tests use the keyword).

Everything else in the spec was re-checked at `f25698c`: the read inventory (`grep -rn "get_lang\|get_charset_maps\|TEXT2BRAILLE_LANG\|set_lang" client --include=*.py`), the call chains, the callers of `LanguageDetector(...)` (pipeline and tests only) and `ConversionRequest(...)` (`gui.py`, `main.py`, tests: `test_conversion_service` x8, `test_conversion_text_pipeline` x1, `test_conversion_jobs` x1), the 10 `translate_with_language*` calls in `test_conversion_service`, the `TypeError` the Windows-only `test_translation_language_result` raises today (5 positionals for 4 parameters), the registry values (`zh_TW` -> `zh-tw.ctb`, `ja` -> `ja-kantenji.utb`, no `ja_JP` key, `DEFAULT_TABLE` `en-ueb-g1.ctb`), the detector characterizations in spec tests 2, 4 and 5 (identical under `PYTHONHASHSEED` 0-3), and that `conversion/__init__.py` is empty.

## Dry Run

The whole plan was executed on scratch copies built from the tracked `client/` and `scripts/` files at `f25698c`, never the repo. First run (`$SP/p11/dry`): every task was developed red-first and the suite check after each task gave the counts below. The final file contents of each task were then replayed mechanically on a fresh copy (`$SP/p11/dry2`), which produced every patch and every expected output quoted in this file; after Task 7 that copy gives `Ran 575 tests`, `FAILED (failures=1, skipped=7)` under `PYTHONHASHSEED` 0 and 5, the msgid scan reports `SOURCE == SAVED`, and the shuffled-order harness (seeds 1-10) shows no failing test outside the known set (the P2-5 case and the 8 pre-existing `test_conversion_service` order errors, see refinement 8). Finally the blocks of this file were extracted and run in order on a third fresh copy (`$SP/p11/dry3`): all 7 commits applied, every quoted expected block matched the actual output byte for byte (AC2 up to line order), and the resulting 31 files are identical to the second copy; the final `client/tests/test_conversion_language_explicit.py` has sha256 `3de8bc5d8fd25fc5fc51be5cd47d2987e6e5ca1e5e3181f83ab894853a38cc8e`, `client/languageDetection/__init__.py` `02fc33a1e9d3e50d41c09fd20fb72e3cd8aba97d991e9cb952ff67b732f02d79` and `client/conversion/service.py` `260d53aee8aa124060422cecaa962c4cee57d22e105d25859e1546844483a61e`.

## Review Focus

1. **Same braille.** The raw `get_lang()` string is passed down unchanged and each consumer normalizes it exactly as before (pipeline `replace("-", "_").split("_", 1)[0]`, MathCAT `replace("_", "-").lower()`, detector as is). Tests: the Task 1 characterizations, kept with identical expected values through Tasks 3-7.
2. **One read point.** After Task 7 the only reads are `gui._build_conversion_request` and `main.run_demo` (plus `client_init.py`, out of scope). Tests: `test_same_request_gives_same_output_in_any_environment` (config reads raise, environment varies, output and math language stay `en`), `test_language_consumers_do_not_import_config` (subprocess, catches transitive imports), acceptance greps 1-3.
3. **Per-request snapshot.** A `config.json` edit reaches the next conversion, never a running one. Test: `test_conversion_request_reads_language_settings_per_request`.
4. **Detector edge cases.** Missing key -> first block language (no `KeyError`); present key, even `""` -> used as is (refinement 1).
5. **Name shadowing in the pipeline (read, not a bug).** The spec names the new pipeline parameter `lang`; the existing loop later rebinds a local `lang = item.lang.split("_")[0]` for each language command. The parameter is used only before the loop (detector construction and `default_lang`), so the rebinding is harmless; it is left as is to keep the loop untouched.
6. **Signature churn.** Every new parameter is required and keyword-only, so a missed caller fails with `TypeError`; the three `..._is_required` tests pin that for the detector, the MathCAT adapter and the table lookup.

## File Map

- Task 1: create `client/tests/test_braille_tables_default_lang.py`, `client/tests/test_conversion_language_explicit.py`; modify `client/tests/test_conversion_text_pipeline.py`, `client/tests/test_language_detection_char_langinfo.py`, `client/tests/test_mathcat_adapter.py`.
- Task 2: create `client/conversion/math_braille_codes.py`, `client/tests/test_math_braille_codes.py`; modify `client/config.py`.
- Task 3: modify `client/braille/tables/__init__.py`, `client/tests/test_braille_tables_default_lang.py`.
- Task 4: modify `client/adapters/translation/{contracts,fallback,mathcat}.py`, `client/conversion/{math_service,mathcat_adapter,service}.py`, tests `test_conversion_language_explicit`, `test_conversion_service`, `test_math_service`, `test_math_translation_adapter`, `test_mathcat_adapter`, `test_translation_fallback`.
- Task 5: modify `client/languageDetection/__init__.py`, `client/conversion/text/pipeline.py`, tests `test_language_detection_char_langinfo`, `test_language_detection_unicode_braille`, `test_language_detection_translation` (Windows-only).
- Task 6: modify `client/conversion/output.py`, `client/gui.py`, `client/main.py`, tests `test_conversion_jobs`, `test_conversion_language_explicit`, `test_conversion_service`, `test_conversion_text_pipeline`, `test_gui_document_flows`, `test_main_demo`.
- Task 7: modify `client/conversion/output.py`, `client/conversion/service.py`, `client/conversion/text/pipeline.py`, tests `test_conversion_language_explicit`, `test_conversion_service`, `test_conversion_text_pipeline`, `test_translation_import_isolation`, `test_translation_language_result` (Windows-only).

## Expected Counts

| After task | new tests in task | `discover` `Ran` | new tests ok (suite check) |
| --- | --- | --- | --- |
| baseline | - | 554 | 0 |
| 1 characterization | 10 | 564 | 10 |
| 2 math braille codes leaf | 2 | 566 | 12 |
| 3 default table lookup | 1 | 567 | 13 |
| 4 MathCAT language | 2 | 569 | 15 |
| 5 LanguageDetector | 3 (+1 renamed) | 572 | 19 |
| 6 ConversionRequest fields | 2 | 574 | 21 |
| 7 thread through service/pipeline | 1 | 575 | 22 |

Every row: `FAILED (failures=1, skipped=7)`, the one failure being the P2-5 case, and `BASELINE-TESTS-IDENTICAL`. "New tests ok" counts passing test lines that are not in the baseline: the 21 new tests plus `test_charset_map_comes_from_constructor` (the Task 5 rename of `test_charset_map_is_loaded_from_config`). Task 7 renames the two Task 1 end-to-end tests, which were already new, so the count only grows by the isolation test.

Per-task suite check (from `$REPO/client`):

```bash
$T/tools/check_suite.sh <Ran> <new tests ok>
```

Expected: `Ran <Ran> tests`, `FAILED (failures=1, skipped=7)`, the one `FAIL:` line of the P2-5 case, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (<Ran>)`, `new tests ok: <n> (expected <n>)`.

## Throwaway Tooling (not committed)

All in `$T/tools/`, outside the repo:

- `check_suite.sh <Ran> <new ok>`: full `discover -v`; every baseline test line except the renamed one must appear unchanged; counts passing non-baseline lines. Source in the Appendix.
- `msgid_scan.py`: the P0-5 AST stand-in for xgettext. Copy it from `$SP/p05/tools/msgid_scan.py`; if that file is gone, its source is in the Appendix of `docs/superpowers/plans/2026-10-08-p0-5-i18n.md`.
- `shuffle_harness.py <seed>`: runs every test module in a seeded random order. Copy it from `$SP/shuffle_harness.py`.

---

### Task 0: Record the baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short
git -C $REPO log --oneline -1
git -C $REPO branch --show-current
```

Expected: no output from `status`; HEAD is the plan commit (`docs: plan explicit conversion language`); branch `refactor/p1-1-explicit-language`.

- [ ] **Step 2: Create the tools and record the baseline files.**

```bash
mkdir -p $T/tools   # then write check_suite.sh from the Appendix
chmod +x $T/tools/check_suite.sh
cp $SP/p05/tools/msgid_scan.py $SP/shuffle_harness.py $T/tools/
$PY -m unittest discover -s tests -v 2>&1 | grep ' \.\.\. ' | sort > $T/baseline_discover_verbose.txt
wc -l < $T/baseline_discover_verbose.txt
$PY -I $T/tools/msgid_scan.py $REPO/client --save $T/baseline_msgids.json
for s in 1 2 3 4 5 6 7 8 9 10; do $PY -I $T/tools/shuffle_harness.py $s | head -1; done
```

Expected: `554`; `source msgids: 357`, `pot msgids: 357`, `SOURCE == POT`, `saved ...`; ten `seed=<n> ran=554 ...` lines, each either `failures=1 errors=0 skipped=7` (seeds 1, 2, 3, 5, 10) or `failures=0 errors=8 skipped=7` (seeds 4, 6, 7, 8, 9; the pre-existing `translate` re-import pollution, refinement 8).

---

### Task 1: Characterize today's language-dependent behavior

**Files:**
- Create: `client/tests/test_braille_tables_default_lang.py`, `client/tests/test_conversion_language_explicit.py`
- Modify: `client/tests/test_conversion_text_pipeline.py`, `client/tests/test_language_detection_char_langinfo.py`, `client/tests/test_mathcat_adapter.py`

These tests run on the unchanged code and still patch `config` (or call `config.set_lang`); their expected values are what the app produces today. Later tasks replace the patches with explicit arguments and keep every expected value.

- [ ] **Step 1: Add the characterization tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_braille_tables_default_lang.py b/client/tests/test_braille_tables_default_lang.py
new file mode 100644
index 0000000..1909914
--- /dev/null
+++ b/client/tests/test_braille_tables_default_lang.py
@@ -0,0 +1,20 @@
+import unittest
+from unittest.mock import patch
+
+import braille.tables as tables
+
+
+class DefaultTableForLanguageTest(unittest.TestCase):
+    def test_output_table_follows_language(self) -> None:
+        self.assertNotIn("ja_JP", tables._outputTableForLangs)
+        for lang, expected in (
+            ("zh_TW", "zh-tw.ctb"),
+            ("ja_JP", "ja-kantenji.utb"),
+            ("xx", tables.DEFAULT_TABLE),
+        ):
+            with self.subTest(lang=lang), patch("braille.tables.config.get_lang", return_value=lang):
+                self.assertEqual(tables.getDefaultTableForCurLang(tables.TableType.OUTPUT), expected)
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/client/tests/test_conversion_language_explicit.py b/client/tests/test_conversion_language_explicit.py
new file mode 100644
index 0000000..a320931
--- /dev/null
+++ b/client/tests/test_conversion_language_explicit.py
@@ -0,0 +1,110 @@
+import csv
+import tempfile
+import unittest
+from pathlib import Path
+from unittest.mock import patch
+
+import config
+from adapters.translation.contracts import TranslationRuntime
+from conversion.service import ConversionRequest, convert_text_with_alignment
+
+
+TABLES = {
+    "default": "default.ctb",
+    "en": "en.ctb",
+    "zh": "zh.ctb",
+    "ja": "ja.ctb",
+    "math": "Nemeth",
+}
+MIXED_TEXT = "Hello 中文 $1$"
+MIXED_TEXT_BRAILLE = "T[Hello ]T[ ]T[中文 ]M[1]"
+MIXED_TEXT_CALLS = [
+    ("Hello ", "en.ctb"),
+    (" ", "en.ctb"),
+    ("中文 ", "zh.ctb"),
+]
+
+
+# The fakes import TranslationResult per call: tests.test_translation_result_core
+# re-imports `translate`, and the wrapping step only accepts the current class.
+class RecordingTextTranslator:
+    def __init__(self) -> None:
+        self.calls = []
+
+    def translate(self, text, *, table, raw, single_token=False):
+        from translate import TranslationResult
+
+        self.calls.append((text, table))
+        braille = list(f"T[{text}]")
+        return TranslationResult([raw], braille, [0] * len(braille), [0])
+
+
+class RecordingMathTranslator:
+    def __init__(self) -> None:
+        self.calls = []
+
+    def translate(self, source, *, braille_code):
+        from translate import TranslationResult
+
+        self.calls.append((source, braille_code))
+        braille = list(f"M[{source}]")
+        return TranslationResult([source], braille, [0] * len(braille), [0])
+
+
+class ConversionLanguageTest(unittest.TestCase):
+    def setUp(self) -> None:
+        tmpdir = tempfile.TemporaryDirectory()
+        self.addCleanup(tmpdir.cleanup)
+        directory = Path(tmpdir.name)
+        self.data_dir = directory / "data"
+        dictionary_dir = directory / "dictionary"
+        self.data_dir.mkdir()
+        dictionary_dir.mkdir()
+        self.dictionary_path = dictionary_dir / "default.csv"
+        self._write_csv(self.dictionary_path, ["text", "braille", "type"])
+        self._write_csv(self.data_dir / "Bopomofo2Braille.csv", ["Bopomofo", "Braille"])
+        self._write_csv(self.data_dir / "BopomofoChar2Braille.csv", ["Bopomofo", "Braille"])
+
+    def _write_csv(self, path: Path, fieldnames: list[str]) -> None:
+        with path.open("w", newline="", encoding="utf-8") as f:
+            csv.DictWriter(f, fieldnames=fieldnames).writeheader()
+
+    def _convert(self, raw_text: str):
+        text_translator = RecordingTextTranslator()
+        math_translator = RecordingMathTranslator()
+        request = ConversionRequest(
+            raw_text=raw_text,
+            output_mode="unicode",
+            width=40,
+            dictionary_path=self.dictionary_path,
+            data_dir=self.data_dir,
+            translation_tables=dict(TABLES),
+        )
+        output = convert_text_with_alignment(
+            request,
+            map_char=lambda text, **_kwargs: text,
+            runtime=TranslationRuntime(text_translator=text_translator, math_translator=math_translator),
+        )
+        return output, text_translator.calls, math_translator.calls
+
+    def test_mixed_text_translation_for_english(self) -> None:
+        with patch.object(config, "get_lang", return_value="en"), patch.object(
+            config, "get_charset_maps", return_value=dict(config.DEFAULT_CHARSET_MAPS)
+        ):
+            output, text_calls, math_calls = self._convert(MIXED_TEXT)
+
+        self.assertEqual(output.display_text.rstrip("\u2800"), MIXED_TEXT_BRAILLE)
+        self.assertEqual(text_calls, MIXED_TEXT_CALLS)
+        self.assertEqual(math_calls, [("1", "Nemeth")])
+
+    def test_non_detecting_text_follows_language(self) -> None:
+        for lang, table in (("en", "en.ctb"), ("zh_TW", "zh.ctb")):
+            with self.subTest(lang=lang):
+                with patch.object(config, "get_lang", return_value=lang):
+                    _output, text_calls, _math_calls = self._convert("\u2192")
+
+                self.assertEqual(text_calls, [("\u2192", table)])
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/client/tests/test_conversion_text_pipeline.py b/client/tests/test_conversion_text_pipeline.py
index 82dddc5..b2c9c3e 100644
--- a/client/tests/test_conversion_text_pipeline.py
+++ b/client/tests/test_conversion_text_pipeline.py
@@ -15,6 +15,9 @@ from conversion.text.pipeline import (
 from translate import TranslationResult
 
 
+LANGUAGE_TABLES = {"default": "default.ctb", "en": "en.ctb", "zh": "zh.ctb", "ja": "ja.ctb"}
+
+
 class ConversionTextPipelineTest(unittest.TestCase):
     def _write_csv(self, directory: Path, name: str, fieldnames: list[str], rows: list[dict[str, str]]) -> Path:
         path = directory / name
@@ -32,6 +35,19 @@ class ConversionTextPipelineTest(unittest.TestCase):
 
         return TranslationRuntime(text_translator=Translator(), math_translator=Translator())
 
+    def _recording_runtime(self, calls: list) -> TranslationRuntime:
+        class Translator:
+            def translate(self, text, *, table, raw, single_token=False):
+                calls.append((text, table))
+                return TranslationResult(raw, text, list(range(len(text))), list(range(len(raw))))
+
+        return TranslationRuntime(text_translator=Translator(), math_translator=Translator())
+
+    def _plain_text_paths(self, directory: Path) -> tuple[Path, Path]:
+        dictionary_path = self._write_csv(directory, "dictionary.csv", ["text", "braille", "type"], [])
+        bopomofo_path = self._write_csv(directory, "bopomofo.csv", ["Bopomofo", "Braille"], [])
+        return dictionary_path, bopomofo_path
+
     def test_preprocess_source_text_runs_user_script_before_bopomofo_mapping(self) -> None:
         with tempfile.TemporaryDirectory() as tmpdir:
             directory = Path(tmpdir)
@@ -209,3 +225,45 @@ class ConversionTextPipelineTest(unittest.TestCase):
 
             self.assertEqual(result.display_text, "wrapped")
             self.assertEqual(translated_texts, ["processed"])
+
+    def test_non_detecting_text_uses_current_language_table(self) -> None:
+        for lang, table in (("en", "en.ctb"), ("zh_TW", "zh.ctb")):
+            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as tmpdir:
+                dictionary_path, bopomofo_path = self._plain_text_paths(Path(tmpdir))
+                calls = []
+
+                with patch("conversion.text.pipeline.config.get_lang", return_value=lang):
+                    translate_plain_text_segment(
+                        "\u2192",
+                        dictionary_path,
+                        LANGUAGE_TABLES,
+                        bopomofo_path,
+                        runtime=self._recording_runtime(calls),
+                    )
+
+                self.assertEqual(calls, [("\u2192", table)])
+
+    def test_cjk_charset_map_selects_table_for_cjk_text(self) -> None:
+        for cjk_language, table in (("zh", "zh.ctb"), ("ja", "ja.ctb")):
+            charset_maps = {
+                "latinCharactersLanguage": "en",
+                "CJKCharactersLanguage": cjk_language,
+                "arabicCharactersLanguage": "ar",
+            }
+            with self.subTest(cjk_language=cjk_language), tempfile.TemporaryDirectory() as tmpdir:
+                dictionary_path, bopomofo_path = self._plain_text_paths(Path(tmpdir))
+                calls = []
+
+                with patch("conversion.text.pipeline.config.get_lang", return_value="en"), patch(
+                    "conversion.text.pipeline.config.get_charset_maps",
+                    return_value=charset_maps,
+                ):
+                    translate_plain_text_segment(
+                        "A中",
+                        dictionary_path,
+                        LANGUAGE_TABLES,
+                        bopomofo_path,
+                        runtime=self._recording_runtime(calls),
+                    )
+
+                self.assertEqual(calls, [("A", "en.ctb"), (" ", "en.ctb"), ("中", table)])
diff --git a/client/tests/test_language_detection_char_langinfo.py b/client/tests/test_language_detection_char_langinfo.py
index 9759b55..2c80987 100644
--- a/client/tests/test_language_detection_char_langinfo.py
+++ b/client/tests/test_language_detection_char_langinfo.py
@@ -5,6 +5,10 @@ from languageDetection import LangChangeCommand, LanguageDetector
 from languageDetection import SINGLETONS
 
 
+def _flatten(sequence):
+    return [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence]
+
+
 class CharacterLanguageInfoTest(unittest.TestCase):
     def test_mongolian_uses_base_language_code(self):
         self.assertEqual(SINGLETONS["Mongolian"], "mn")
@@ -60,6 +64,42 @@ class CharacterLanguageInfoTest(unittest.TestCase):
             ["A", "ja_JP", "中"],
         )
 
+    def test_preferred_full_language_comes_from_current_language(self):
+        detector = LanguageDetector(["en", "zh"])
+
+        with patch("languageDetection.config.get_lang", return_value="zh_HK"):
+            sequence = list(detector.add_detected_language_commands([LangChangeCommand("en"), "中"]))
+
+        self.assertEqual(_flatten(sequence), ["en", "zh_HK", "中"])
+
+    def test_current_language_decides_leading_language_command(self):
+        for lang, expected in (
+            ("en", ["Hello ", "zh", "中文 "]),
+            ("zh_TW", ["en", "Hello ", "zh_TW", "中文 "]),
+        ):
+            with self.subTest(lang=lang):
+                detector = LanguageDetector(["en", "zh", "ja"])
+
+                with patch("languageDetection.config.get_lang", return_value=lang):
+                    sequence = list(detector.add_detected_language_commands(["Hello 中文 "]))
+
+                self.assertEqual(_flatten(sequence), expected)
+
+    def test_empty_charset_map_value_is_used_as_is(self):
+        detector = LanguageDetector(["en", "zh_TW"])
+
+        with patch("languageDetection.config.get_lang", return_value="en"), patch(
+            "languageDetection.config.get_charset_maps",
+            return_value={
+                "latinCharactersLanguage": "en",
+                "CJKCharactersLanguage": "",
+                "arabicCharactersLanguage": "ar",
+            },
+        ):
+            sequence = list(detector.add_detected_language_commands(["A中"]))
+
+        self.assertEqual(_flatten(sequence), ["A", "", "中"])
+
 
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_mathcat_adapter.py b/client/tests/test_mathcat_adapter.py
index 6a75a12..3acf2c4 100644
--- a/client/tests/test_mathcat_adapter.py
+++ b/client/tests/test_mathcat_adapter.py
@@ -97,6 +97,29 @@ class MathCATAdapterTest(unittest.TestCase):
         set_rules_dir_calls = [call for call in fake.calls if call[0] == "SetRulesDir"]
         self.assertEqual(len(set_rules_dir_calls), 2)
 
+    def test_language_preference_is_lowercase_with_hyphen(self) -> None:
+        fake = FakeLib()
+        adapter = TestMathCATAdapter(fake_lib=fake)
+        config.set_lang("en_US", persist=False)
+
+        adapter.get_braille_for_mathml("<math/>")
+
+        self.assertIn(("SetPreference", "Language", "en-us"), fake.calls)
+
+    def test_each_call_sets_its_own_language(self) -> None:
+        fake = FakeLib()
+        adapter = TestMathCATAdapter(fake_lib=fake)
+
+        config.set_lang("zh_TW", persist=False)
+        adapter.get_braille_for_mathml("<math/>")
+        config.set_lang("en", persist=False)
+        adapter.get_braille_for_mathml("<math/>")
+
+        self.assertEqual(
+            [call[2] for call in fake.calls if call[:2] == ("SetPreference", "Language")],
+            ["zh-tw", "en"],
+        )
+
 
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run them on the current code.**

```bash
$PY -m unittest tests.test_braille_tables_default_lang tests.test_conversion_language_explicit tests.test_conversion_text_pipeline tests.test_language_detection_char_langinfo tests.test_mathcat_adapter 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//'
```

Expected (characterization: green on purpose):

```
Ran 28 tests
OK
```

- [ ] **Step 3: Suite check.**

```bash
$T/tools/check_suite.sh 564 10
```

Expected: `Ran 564 tests`, `FAILED (failures=1, skipped=7)`, the P2-5 `FAIL:` line, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (564)`, `new tests ok: 10 (expected 10)`.

- [ ] **Step 4: Commit.**

```bash
git -C $REPO add client/tests/test_braille_tables_default_lang.py client/tests/test_conversion_language_explicit.py client/tests/test_conversion_text_pipeline.py client/tests/test_language_detection_char_langinfo.py client/tests/test_mathcat_adapter.py
git -C $REPO commit -F - <<'MSG'
test: characterize conversion language behavior

Pin today's language-dependent results before the language becomes an
explicit argument: detector sequences for the current language and the
charset map (including an empty map value), the table chosen for text
without a language command, the MathCAT Language preference, the
default braille table per language, and one end-to-end conversion. The
tests still patch config; later commits switch them to explicit
arguments without changing the expected values.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 2: Move the math braille codes to a config-free leaf module

**Files:**
- Create: `client/tests/test_math_braille_codes.py`, `client/conversion/math_braille_codes.py`
- Modify: `client/config.py`

**Interfaces:** `conversion.math_braille_codes.MATH_BRAILLE_TABLES = ("UEB", "Nemeth")`, `DEFAULT_MATH_BRAILLE_TABLE = "UEB"` (no imports). `config` re-exports both names (same objects).

- [ ] **Step 1: Write the failing test.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_math_braille_codes.py b/client/tests/test_math_braille_codes.py
new file mode 100644
index 0000000..9be7767
--- /dev/null
+++ b/client/tests/test_math_braille_codes.py
@@ -0,0 +1,18 @@
+import unittest
+
+import config
+from conversion import math_braille_codes
+
+
+class MathBrailleCodesTest(unittest.TestCase):
+    def test_leaf_module_defines_math_braille_codes(self) -> None:
+        self.assertEqual(math_braille_codes.MATH_BRAILLE_TABLES, ("UEB", "Nemeth"))
+        self.assertEqual(math_braille_codes.DEFAULT_MATH_BRAILLE_TABLE, "UEB")
+
+    def test_config_re_exports_the_leaf_module_values(self) -> None:
+        self.assertIs(config.MATH_BRAILLE_TABLES, math_braille_codes.MATH_BRAILLE_TABLES)
+        self.assertIs(config.DEFAULT_MATH_BRAILLE_TABLE, math_braille_codes.DEFAULT_MATH_BRAILLE_TABLE)
+
+
+if __name__ == "__main__":
+    unittest.main()
PATCH
```

- [ ] **Step 2: Run it and see it fail.**

```bash
$PY -m unittest tests.test_math_braille_codes 2>&1 | grep -E '^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//' | LC_ALL=C sort | uniq -c
```

Expected:

```
      1 FAILED (errors=1)
      1 ImportError: Failed to import test module: test_math_braille_codes
      1 ImportError: cannot import name 'math_braille_codes' from 'conversion' (/workspace/DotExpress/client/conversion/__init__.py)
      1 Ran 1 test
```

- [ ] **Step 3: Add the leaf module and re-export it from `config`.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/config.py b/client/config.py
index 60f9c80..6b1c650 100644
--- a/client/config.py
+++ b/client/config.py
@@ -5,6 +5,7 @@ from typing import Optional
 from uuid import uuid4
 
 from app_paths import get_config_path
+from conversion.math_braille_codes import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES  # noqa: F401  (re-exported)
 from log import get_logger
 
 logger = get_logger("dotexpress.config", "config.log", level=logging.WARNING)
@@ -32,8 +33,6 @@ DEFAULT_TRANSLATION_TABLES = {
     "ja": "ja-rokutenkanji.utb",
     "math": "UEB",
 }
-MATH_BRAILLE_TABLES = ("UEB", "Nemeth")
-DEFAULT_MATH_BRAILLE_TABLE = "UEB"
 DEFAULT_OUTPUT_MODE = "unicode"
 DEFAULT_CONVERSION_WIDTH = 40
 DEFAULT_VIEW_FONT_SIZE = 12
diff --git a/client/conversion/math_braille_codes.py b/client/conversion/math_braille_codes.py
new file mode 100644
index 0000000..cee6ba6
--- /dev/null
+++ b/client/conversion/math_braille_codes.py
@@ -0,0 +1,2 @@
+MATH_BRAILLE_TABLES = ("UEB", "Nemeth")
+DEFAULT_MATH_BRAILLE_TABLE = "UEB"
PATCH
```

- [ ] **Step 4: Run it again.**

```bash
$PY -m unittest tests.test_math_braille_codes tests.test_config 2>&1 | tail -1
```

Expected: `OK`.

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 566 12
```

Expected: `Ran 566 tests`, `FAILED (failures=1, skipped=7)`, the P2-5 `FAIL:` line, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (566)`, `new tests ok: 12 (expected 12)`.

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/conversion/math_braille_codes.py client/config.py client/tests/test_math_braille_codes.py
git -C $REPO commit -F - <<'MSG'
refactor: move math braille codes to a config-free module

conversion/math_braille_codes.py now defines MATH_BRAILLE_TABLES and
DEFAULT_MATH_BRAILLE_TABLE; config re-exports both unchanged, so every
existing import keeps working. This lets the MathCAT adapter drop its
config import in a later commit.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 3: `getDefaultTableForCurLang` takes the language

**Files:**
- Modify: `client/tests/test_braille_tables_default_lang.py`, `client/braille/tables/__init__.py` (CRLF)

**Interfaces:** `braille.tables.getDefaultTableForCurLang(tableType: TableType, lang: str) -> str`; same lookup order (exact key, then the base code before `_`, then `DEFAULT_TABLE`). The function still has no caller in the app.

- [ ] **Step 1: Switch the characterization test to the explicit argument and require it.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_braille_tables_default_lang.py b/client/tests/test_braille_tables_default_lang.py
index 1909914..b81af53 100644
--- a/client/tests/test_braille_tables_default_lang.py
+++ b/client/tests/test_braille_tables_default_lang.py
@@ -1,5 +1,4 @@
 import unittest
-from unittest.mock import patch
 
 import braille.tables as tables
 
@@ -12,8 +11,12 @@ class DefaultTableForLanguageTest(unittest.TestCase):
             ("ja_JP", "ja-kantenji.utb"),
             ("xx", tables.DEFAULT_TABLE),
         ):
-            with self.subTest(lang=lang), patch("braille.tables.config.get_lang", return_value=lang):
-                self.assertEqual(tables.getDefaultTableForCurLang(tables.TableType.OUTPUT), expected)
+            with self.subTest(lang=lang):
+                self.assertEqual(tables.getDefaultTableForCurLang(tables.TableType.OUTPUT, lang), expected)
+
+    def test_language_is_required(self) -> None:
+        with self.assertRaises(TypeError):
+            tables.getDefaultTableForCurLang(tables.TableType.OUTPUT)
 
 
 if __name__ == "__main__":
PATCH
```

- [ ] **Step 2: Run it and see it fail.**

```bash
$PY -m unittest tests.test_braille_tables_default_lang 2>&1 | grep -E '^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//' | LC_ALL=C sort | uniq -c
```

Expected:

```
      1 AssertionError: TypeError not raised
      1 FAILED (failures=1, errors=3)
      1 Ran 2 tests
      3 TypeError: getDefaultTableForCurLang() takes 1 positional argument but 2 were given
```

- [ ] **Step 3: Edit the CRLF file byte-exactly.** The script asserts the file has CRLF endings and that each old text occurs exactly once; it removes `import config`, adds the `lang` parameter with the DotExpress note in the docstring, and drops `lang = config.get_lang()` (the upstream comment `# lang = languageHandler.getLanguage()` stays).

```bash
python3 - "$REPO/client/braille/tables/__init__.py" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
crlf = chr(13) + chr(10)
text = path.read_bytes().decode("utf-8")
assert crlf in text, "expected CRLF line endings"


def replace_once(old, new):
    global text
    old = old.replace("\n", crlf)
    new = new.replace("\n", crlf)
    assert text.count(old) == 1, old
    text = text.replace(old, new)


replace_once(
    "import logging\nimport config\n",
    "import logging\n",
)
replace_once(
    'def getDefaultTableForCurLang(tableType: TableType) -> str:\n'
    '\t"""Gets the file name of the braille table for the current NVDA language.\n'
    '\t:param tableType: INPUT (back-translation) or OUTPUT (translation).\n',
    'def getDefaultTableForCurLang(tableType: TableType, lang: str) -> str:\n'
    '\t"""Gets the file name of the default braille table for C{lang}.\n'
    '\tDotExpress: the caller passes the language; upstream NVDA reads languageHandler.getLanguage().\n'
    '\t:param tableType: INPUT (back-translation) or OUTPUT (translation).\n'
    '\t:param lang: The language code, for example C{zh_TW} or C{en}.\n',
)
replace_once(
    "\tlang = config.get_lang()\n\t# lang = languageHandler.getLanguage()\n",
    "\t# lang = languageHandler.getLanguage()\n",
)
path.write_bytes(text.encode("utf-8"))
PY
git -C $REPO diff --stat -- client/braille/tables/__init__.py
```

Expected: ` client/braille/tables/__init__.py | 8 ++++----`, `1 file changed, 4 insertions(+), 4 deletions(-)`.

- [ ] **Step 4: Run it again.**

```bash
$PY -m unittest tests.test_braille_tables_default_lang 2>&1 | tail -1
```

Expected: `OK`.

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 567 13
```

Expected: `Ran 567 tests`, `FAILED (failures=1, skipped=7)`, the P2-5 `FAIL:` line, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (567)`, `new tests ok: 13 (expected 13)`.

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/braille/tables/__init__.py client/tests/test_braille_tables_default_lang.py
git -C $REPO commit -F - <<'MSG'
refactor: pass language to default braille table lookup

getDefaultTableForCurLang(tableType, lang) takes the language instead
of calling config.get_lang(), and braille/tables/__init__.py no longer
imports config. The function has no caller in the app; the lookup order
is unchanged. The file keeps its CRLF line endings.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 4: The MathCAT chain takes the language explicitly

**Files:**
- Modify: `client/adapters/translation/contracts.py`, `client/adapters/translation/fallback.py`, `client/adapters/translation/mathcat.py`, `client/conversion/math_service.py`, `client/conversion/mathcat_adapter.py`, `client/conversion/service.py`
- Modify tests: `test_mathcat_adapter.py`, `test_math_service.py`, `test_math_translation_adapter.py`, `test_translation_fallback.py`, `test_conversion_service.py`, `test_conversion_language_explicit.py`

**Interfaces:**
- `MathSegmentTranslator.translate(self, source, *, braille_code, language)`; `FallbackMathTranslator.translate` accepts and ignores `language`; `MathCATMathTranslator.translate` forwards it to `translate_math(source, braille_code=..., language=...)`.
- `math_service.mathml_to_nemeth_braille(mathml_text, braille_code=DEFAULT_MATH_BRAILLE_TABLE, *, language)` and `translate_math_segment(latex_text, braille_code=DEFAULT_MATH_BRAILLE_TABLE, *, language)`; log message and `MathConversionError` wrapping unchanged; `math_service.py` keeps `from config import DEFAULT_MATH_BRAILLE_TABLE`.
- `MathCATAdapter.get_braille_for_mathml(mathml_text, braille_code=None, *, language)`; `_configure_runtime(libmathcat, braille_code, language)` starts with `mathcat_language = language.replace("_", "-").lower()`; same preference order; constants come from `conversion.math_braille_codes`; no `config` import.
- Temporary (removed in Task 7): `conversion/service.py` imports `get_lang` and passes `language=get_lang()` per math segment.

The test fakes `FakeMathTranslator` (service tests) and `RecordingMathTranslator` (end-to-end) take a required `language` but do not record it yet; Task 7 records and asserts it. `test_mathcat_adapter` loses its `config.set_lang` `setUp`/`tearDown`; its two Task 1 characterizations now pass the language per call with the same expected preferences.

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_language_explicit.py b/client/tests/test_conversion_language_explicit.py
index a320931..69f7ce0 100644
--- a/client/tests/test_conversion_language_explicit.py
+++ b/client/tests/test_conversion_language_explicit.py
@@ -43,7 +43,7 @@ class RecordingMathTranslator:
     def __init__(self) -> None:
         self.calls = []
 
-    def translate(self, source, *, braille_code):
+    def translate(self, source, *, braille_code, language):
         from translate import TranslationResult
 
         self.calls.append((source, braille_code))
diff --git a/client/tests/test_conversion_service.py b/client/tests/test_conversion_service.py
index 6452ecb..fd741e3 100644
--- a/client/tests/test_conversion_service.py
+++ b/client/tests/test_conversion_service.py
@@ -36,7 +36,7 @@ class FakeMathTranslator:
         self.calls = []
         self.error = error
 
-    def translate(self, source: str, *, braille_code: str) -> TranslationResult:
+    def translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult:
         self.calls.append((source, braille_code))
         if self.error is not None:
             raise self.error
diff --git a/client/tests/test_math_service.py b/client/tests/test_math_service.py
index d41c163..79f9f12 100644
--- a/client/tests/test_math_service.py
+++ b/client/tests/test_math_service.py
@@ -1,4 +1,5 @@
 import unittest
+from unittest.mock import Mock, patch
 
 from conversion.math_service import (
     MathConversionError,
@@ -21,7 +22,21 @@ class MathServiceTest(unittest.TestCase):
 
     def test_translate_math_segment_raises_math_conversion_error_for_latex_failure(self) -> None:
         with self.assertRaises(MathConversionError):
-            translate_math_segment(r"\frac{2}{")
+            translate_math_segment(r"\frac{2}{", language="zh_TW")
+
+    def test_translate_math_segment_forwards_language_to_mathcat(self) -> None:
+        adapter = Mock()
+        adapter.get_braille_for_mathml.return_value = "\u283c\u2801"
+
+        with patch("conversion.mathcat_adapter.get_shared_mathcat_adapter", return_value=adapter):
+            braille = translate_math_segment("1", braille_code="Nemeth", language="en")
+
+        self.assertEqual(braille, "\u283c\u2801")
+        adapter.get_braille_for_mathml.assert_called_once_with(
+            latex_to_mathml("1"),
+            braille_code="Nemeth",
+            language="en",
+        )
 
 
 if __name__ == "__main__":
diff --git a/client/tests/test_math_translation_adapter.py b/client/tests/test_math_translation_adapter.py
index affe0d9..c409963 100644
--- a/client/tests/test_math_translation_adapter.py
+++ b/client/tests/test_math_translation_adapter.py
@@ -7,15 +7,15 @@ class MathCATMathTranslatorTest(unittest.TestCase):
     def test_returns_current_single_token_mapping(self) -> None:
         calls = []
 
-        def translate_math(source: str, *, braille_code: str) -> str:
-            calls.append((source, braille_code))
+        def translate_math(source: str, *, braille_code: str, language: str) -> str:
+            calls.append((source, braille_code, language))
             return "⠼⠁⠬⠃"
 
         adapter = MathCATMathTranslator(translate_math=translate_math)
 
-        result = adapter.translate("1+2", braille_code="Nemeth")
+        result = adapter.translate("1+2", braille_code="Nemeth", language="en")
 
-        self.assertEqual(calls, [("1+2", "Nemeth")])
+        self.assertEqual(calls, [("1+2", "Nemeth", "en")])
         self.assertEqual(result.raw, ["1+2"])
         self.assertEqual(result.braille, list("⠼⠁⠬⠃"))
         self.assertEqual(result.raw_to_braille_pos, [0])
@@ -24,7 +24,7 @@ class MathCATMathTranslatorTest(unittest.TestCase):
     def test_empty_math_has_empty_mapping(self) -> None:
         adapter = MathCATMathTranslator(translate_math=lambda *_args, **_kwargs: "")
 
-        result = adapter.translate("", braille_code="UEB")
+        result = adapter.translate("", braille_code="UEB", language="zh_TW")
 
         self.assertEqual(result.raw, [])
         self.assertEqual(result.braille, [])
diff --git a/client/tests/test_mathcat_adapter.py b/client/tests/test_mathcat_adapter.py
index 3acf2c4..a98d304 100644
--- a/client/tests/test_mathcat_adapter.py
+++ b/client/tests/test_mathcat_adapter.py
@@ -1,7 +1,6 @@
 import unittest
 from pathlib import Path
 
-import config
 from conversion.mathcat_adapter import MathCATAdapter, MathCATError
 
 
@@ -45,13 +44,6 @@ class TestMathCATAdapter(MathCATAdapter):
 
 
 class MathCATAdapterTest(unittest.TestCase):
-    def setUp(self) -> None:
-        self._original_runtime_lang = config._runtime_lang
-        config.set_lang("zh_TW", persist=False)
-
-    def tearDown(self) -> None:
-        config._runtime_lang = self._original_runtime_lang
-
     def test_initialize_loads_runtime_once(self) -> None:
         adapter = TestMathCATAdapter()
 
@@ -68,7 +60,7 @@ class MathCATAdapterTest(unittest.TestCase):
         fake = FakeLib()
         adapter = TestMathCATAdapter(fake_lib=fake)
 
-        self.assertEqual(adapter.get_braille_for_mathml("<math/>"), "⠼⠁")
+        self.assertEqual(adapter.get_braille_for_mathml("<math/>", language="zh_TW"), "⠼⠁")
 
         self.assertEqual(fake.calls[0][0], "SetRulesDir")
         self.assertIn(("SetPreference", "BrailleCode", "UEB"), fake.calls)
@@ -79,20 +71,20 @@ class MathCATAdapterTest(unittest.TestCase):
         fake = FakeLib()
         adapter = TestMathCATAdapter(fake_lib=fake)
 
-        adapter.get_braille_for_mathml("<math/>", braille_code="UEB")
+        adapter.get_braille_for_mathml("<math/>", braille_code="UEB", language="zh_TW")
 
         self.assertIn(("SetPreference", "BrailleCode", "UEB"), fake.calls)
 
     def test_get_braille_for_mathml_wraps_runtime_failures(self) -> None:
         adapter = TestMathCATAdapter(load_error=RuntimeError("load failed"))
         with self.assertRaisesRegex(MathCATError, "load failed"):
-            adapter.get_braille_for_mathml("<math/>")
+            adapter.get_braille_for_mathml("<math/>", language="zh_TW")
 
     def test_get_braille_for_mathml_reapplies_runtime_configuration_for_each_call(self) -> None:
         fake = FakeLib("⠁")
         adapter = TestMathCATAdapter(fake_lib=fake)
-        adapter.get_braille_for_mathml("<math><mn>1</mn></math>")
-        adapter.get_braille_for_mathml("<math><mn>2</mn></math>")
+        adapter.get_braille_for_mathml("<math><mn>1</mn></math>", language="zh_TW")
+        adapter.get_braille_for_mathml("<math><mn>2</mn></math>", language="zh_TW")
 
         set_rules_dir_calls = [call for call in fake.calls if call[0] == "SetRulesDir"]
         self.assertEqual(len(set_rules_dir_calls), 2)
@@ -100,9 +92,8 @@ class MathCATAdapterTest(unittest.TestCase):
     def test_language_preference_is_lowercase_with_hyphen(self) -> None:
         fake = FakeLib()
         adapter = TestMathCATAdapter(fake_lib=fake)
-        config.set_lang("en_US", persist=False)
 
-        adapter.get_braille_for_mathml("<math/>")
+        adapter.get_braille_for_mathml("<math/>", language="en_US")
 
         self.assertIn(("SetPreference", "Language", "en-us"), fake.calls)
 
@@ -110,16 +101,20 @@ class MathCATAdapterTest(unittest.TestCase):
         fake = FakeLib()
         adapter = TestMathCATAdapter(fake_lib=fake)
 
-        config.set_lang("zh_TW", persist=False)
-        adapter.get_braille_for_mathml("<math/>")
-        config.set_lang("en", persist=False)
-        adapter.get_braille_for_mathml("<math/>")
+        adapter.get_braille_for_mathml("<math/>", language="zh_TW")
+        adapter.get_braille_for_mathml("<math/>", language="en")
 
         self.assertEqual(
             [call[2] for call in fake.calls if call[:2] == ("SetPreference", "Language")],
             ["zh-tw", "en"],
         )
 
+    def test_language_is_required(self) -> None:
+        adapter = TestMathCATAdapter()
+
+        with self.assertRaises(TypeError):
+            adapter.get_braille_for_mathml("<math/>")
+
 
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_translation_fallback.py b/client/tests/test_translation_fallback.py
index f4c9293..66909a4 100644
--- a/client/tests/test_translation_fallback.py
+++ b/client/tests/test_translation_fallback.py
@@ -39,12 +39,12 @@ class TranslationFallbackTest(unittest.TestCase):
         self.assert_character_fallback(result, "原文", "⣿⣿")
 
     def test_math_uses_same_character_contract(self) -> None:
-        result = FallbackMathTranslator().translate("1 + 2", braille_code="Nemeth")
+        result = FallbackMathTranslator().translate("1 + 2", braille_code="Nemeth", language="zh_TW")
 
         self.assert_character_fallback(result, "1 + 2", "⣿⠀⣿⠀⣿")
 
     def test_empty_source_returns_empty_result(self) -> None:
-        result = FallbackMathTranslator().translate("", braille_code="Nemeth")
+        result = FallbackMathTranslator().translate("", braille_code="Nemeth", language="zh_TW")
 
         self.assert_character_fallback(result, "", "")
 
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_mathcat_adapter tests.test_math_service tests.test_math_translation_adapter tests.test_translation_fallback tests.test_conversion_service tests.test_conversion_language_explicit 2>&1 | grep -E '^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//' | LC_ALL=C sort | uniq -c
```

Expected (the P2-5 test errors here too, because it has a math segment; it fails normally again after Step 3):

```
      1 AssertionError: TypeError not raised
      1 FAILED (failures=1, errors=22)
      1 Ran 43 tests
      9 TypeError: FakeMathTranslator.translate() missing 1 required keyword-only argument: 'language'
      2 TypeError: FallbackMathTranslator.translate() got an unexpected keyword argument 'language'
      6 TypeError: MathCATAdapter.get_braille_for_mathml() got an unexpected keyword argument 'language'
      2 TypeError: MathCATMathTranslator.translate() got an unexpected keyword argument 'language'
      1 TypeError: RecordingMathTranslator.translate() missing 1 required keyword-only argument: 'language'
      2 TypeError: translate_math_segment() got an unexpected keyword argument 'language'
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/adapters/translation/contracts.py b/client/adapters/translation/contracts.py
index 8b8cd67..eb983ec 100644
--- a/client/adapters/translation/contracts.py
+++ b/client/adapters/translation/contracts.py
@@ -22,7 +22,7 @@ class BrailleTextTranslator(Protocol):
 
 
 class MathSegmentTranslator(Protocol):
-    def translate(self, source: str, *, braille_code: str) -> TranslationResult: ...
+    def translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult: ...
 
 
 @dataclass
diff --git a/client/adapters/translation/fallback.py b/client/adapters/translation/fallback.py
index 9052d26..19e22ec 100644
--- a/client/adapters/translation/fallback.py
+++ b/client/adapters/translation/fallback.py
@@ -28,5 +28,5 @@ class FallbackTextTranslator:
 
 
 class FallbackMathTranslator:
-    def translate(self, source: str, *, braille_code: str) -> TranslationResult:
+    def translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult:
         return build_character_fallback(source)
diff --git a/client/adapters/translation/mathcat.py b/client/adapters/translation/mathcat.py
index c3f721c..da3b016 100644
--- a/client/adapters/translation/mathcat.py
+++ b/client/adapters/translation/mathcat.py
@@ -9,9 +9,9 @@ class MathCATMathTranslator:
     def __init__(self, *, translate_math: Callable[..., str]):
         self._translate_math = translate_math
 
-    def translate(self, source: str, *, braille_code: str) -> TranslationResult:
+    def translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult:
         braille = list(
-            self._translate_math(source, braille_code=braille_code)
+            self._translate_math(source, braille_code=braille_code, language=language)
         )
         if not source:
             return TranslationResult([], [], [], [])
diff --git a/client/conversion/math_service.py b/client/conversion/math_service.py
index 1e636a0..435cab1 100644
--- a/client/conversion/math_service.py
+++ b/client/conversion/math_service.py
@@ -37,17 +37,31 @@ def latex_to_mathml(latex_text: str) -> str:
 	return mathml.replace("<mi>⇀</mi>", "<mo>⇀</mo>")
 
 
-def mathml_to_nemeth_braille(mathml_text: str, braille_code: str = DEFAULT_MATH_BRAILLE_TABLE) -> str:
+def mathml_to_nemeth_braille(
+	mathml_text: str,
+	braille_code: str = DEFAULT_MATH_BRAILLE_TABLE,
+	*,
+	language: str,
+) -> str:
 	from conversion.mathcat_adapter import get_shared_mathcat_adapter
 
-	return get_shared_mathcat_adapter().get_braille_for_mathml(mathml_text, braille_code=braille_code)
+	return get_shared_mathcat_adapter().get_braille_for_mathml(
+		mathml_text,
+		braille_code=braille_code,
+		language=language,
+	)
 
 
-def translate_math_segment(latex_text: str, braille_code: str = DEFAULT_MATH_BRAILLE_TABLE) -> str:
+def translate_math_segment(
+	latex_text: str,
+	braille_code: str = DEFAULT_MATH_BRAILLE_TABLE,
+	*,
+	language: str,
+) -> str:
 	mathml_text = None
 	try:
 		mathml_text = latex_to_mathml(latex_text)
-		return mathml_to_nemeth_braille(mathml_text, braille_code=braille_code)
+		return mathml_to_nemeth_braille(mathml_text, braille_code=braille_code, language=language)
 	except Exception as error:
 		logger.exception(
 			"Math conversion failed | stage=%s | latex=%r | mathml=%r",
diff --git a/client/conversion/mathcat_adapter.py b/client/conversion/mathcat_adapter.py
index 02917c8..a53e7f6 100644
--- a/client/conversion/mathcat_adapter.py
+++ b/client/conversion/mathcat_adapter.py
@@ -6,7 +6,7 @@ import os
 from pathlib import Path
 import sys
 
-from config import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES, get_lang
+from conversion.math_braille_codes import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES
 
 
 class MathCATError(Exception):
@@ -68,24 +68,30 @@ class MathCATAdapter:
 			return braille_code
 		return DEFAULT_MATH_BRAILLE_TABLE
 
-	def _configure_runtime(self, libmathcat, braille_code: str | None = None) -> None:
-		language = get_lang().replace("_", "-").lower()
-		speech_style = self._resolve_speech_style(language)
+	def _configure_runtime(self, libmathcat, braille_code: str | None, language: str) -> None:
+		mathcat_language = language.replace("_", "-").lower()
+		speech_style = self._resolve_speech_style(mathcat_language)
 		selected_braille_code = self._normalize_braille_code(braille_code)
 		# Re-apply runtime configuration for each conversion. In the stripped-down
 		# embedding used by DotExpress, later SetMathML calls can fail if MathCAT
 		# keeps stale rule/preference state between requests.
 		libmathcat.SetRulesDir(str(self._rules_dir()))
-		libmathcat.SetPreference("Language", language)
+		libmathcat.SetPreference("Language", mathcat_language)
 		libmathcat.SetPreference("SpeechStyle", speech_style)
 		libmathcat.SetPreference("Verbosity", "Medium")
 		libmathcat.SetPreference("TTS", "None")
 		libmathcat.SetPreference("BrailleCode", selected_braille_code)
 
-	def get_braille_for_mathml(self, mathml_text: str, braille_code: str | None = None) -> str:
+	def get_braille_for_mathml(
+		self,
+		mathml_text: str,
+		braille_code: str | None = None,
+		*,
+		language: str,
+	) -> str:
 		try:
 			libmathcat = self._load_libmathcat()
-			self._configure_runtime(libmathcat, braille_code)
+			self._configure_runtime(libmathcat, braille_code, language)
 			libmathcat.SetMathML(mathml_text)
 			return libmathcat.GetBraille("")
 		except MathCATError:
diff --git a/client/conversion/service.py b/client/conversion/service.py
index 4e017ed..86a3c44 100644
--- a/client/conversion/service.py
+++ b/client/conversion/service.py
@@ -1,5 +1,5 @@
 from adapters.translation.contracts import TranslationRuntime
-from config import DEFAULT_MATH_BRAILLE_TABLE
+from config import DEFAULT_MATH_BRAILLE_TABLE, get_lang
 from conversion.text.char_maps import translate__mapping_char
 from conversion.output import (
     ConversionOutput,
@@ -63,6 +63,7 @@ def translate_with_language_dual_view_segments(
             result = runtime.math_translator.translate(
                 segment["text"],
                 braille_code=math_braille_code,
+                language=get_lang(),
             )
             segments_records.append(DualViewSegment(result=result, source_kind="math"))
     return segments_records
PATCH
```

- [ ] **Step 4: Run them again.**

```bash
$PY -m unittest tests.test_mathcat_adapter tests.test_math_service tests.test_math_translation_adapter tests.test_translation_fallback tests.test_conversion_service tests.test_conversion_language_explicit 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_translation_runtime_provider 2>&1 | tail -1
```

Expected (only the P2-5 failure in the first run; the provider module passes):

```
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 43 tests
FAILED (failures=1)
OK
```

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 569 15
```

Expected: `Ran 569 tests`, `FAILED (failures=1, skipped=7)`, the P2-5 `FAIL:` line, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (569)`, `new tests ok: 15 (expected 15)`.

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/adapters/translation/contracts.py client/adapters/translation/fallback.py client/adapters/translation/mathcat.py client/conversion/math_service.py client/conversion/mathcat_adapter.py client/conversion/service.py client/tests/test_conversion_language_explicit.py client/tests/test_conversion_service.py client/tests/test_math_service.py client/tests/test_math_translation_adapter.py client/tests/test_mathcat_adapter.py client/tests/test_translation_fallback.py
git -C $REPO commit -F - <<'MSG'
refactor: pass math language explicitly to MathCAT

MathCATAdapter.get_braille_for_mathml, mathml_to_nemeth_braille,
translate_math_segment and the MathSegmentTranslator protocol
(MathCATMathTranslator, FallbackMathTranslator) take a required
language keyword. The adapter derives the MathCAT Language preference
from it exactly as before and no longer imports config. Until the
conversion request carries the language, conversion.service reads
config.get_lang() for each math segment, which is when the adapter
read it before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 5: `LanguageDetector` takes `default_lang` and `charset_maps`

**Files:**
- Modify: `client/languageDetection/__init__.py`, `client/conversion/text/pipeline.py`
- Modify tests: `test_language_detection_char_langinfo.py`, `test_language_detection_unicode_braille.py`, `test_language_detection_translation.py` (Windows-only)

**Interfaces:** `LanguageDetector(availableLanguages, *, default_lang: str, charset_maps: Mapping[str, str], char_langinfo=None)`; it keeps `self.default_lang` and `self.charset_maps = dict(charset_maps)`. `add_detected_language_commands` starts from `self.default_lang` (the NVDA comment `# defaultLang = getSynth().language` stays). `find_language_for_charset` returns `self.charset_maps[configKey]` when the key is present (even `""`), else falls through to `langs[0]` (refinement 1). `_preferred_full_lang` step 2 uses `self.default_lang` without the old `try/except`; its docstring names `default_lang`. `import config` is gone (the NVDA comment `# import config` stays); `Mapping` is added to the `typing` import. Temporary (removed in Task 7): the pipeline passes `default_lang=config.get_lang(), charset_maps=config.get_charset_maps()`.

The detector tests use `config.DEFAULT_CHARSET_MAPS` as "the default map". `test_charset_map_is_loaded_from_config` becomes `test_charset_map_comes_from_constructor`. New: missing map entry (spec test 5), own copy of the map, constructor requires both values (spec test 6). The Windows-only test gets `default_lang="zh_TW"` (what `get_lang()` returned when nothing was set) and the default map.

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_language_detection_char_langinfo.py b/client/tests/test_language_detection_char_langinfo.py
index 2c80987..b85bbbc 100644
--- a/client/tests/test_language_detection_char_langinfo.py
+++ b/client/tests/test_language_detection_char_langinfo.py
@@ -1,6 +1,6 @@
 import unittest
-from unittest.mock import patch
 
+from config import DEFAULT_CHARSET_MAPS
 from languageDetection import LangChangeCommand, LanguageDetector
 from languageDetection import SINGLETONS
 
@@ -16,11 +16,12 @@ class CharacterLanguageInfoTest(unittest.TestCase):
     def test_character_language_map_forces_language_and_preserves_character(self):
         detector = LanguageDetector(
             ["en", "zh_TW", "ja_JP"],
+            default_lang="en",
+            charset_maps=DEFAULT_CHARSET_MAPS,
             char_langinfo={"￥": "ja_JP"},
         )
 
-        with patch("languageDetection.config.get_lang", return_value="en"):
-            sequence = list(detector.add_detected_language_commands(["a￥b中"]))
+        sequence = list(detector.add_detected_language_commands(["a￥b中"]))
 
         self.assertEqual(
             [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence],
@@ -28,10 +29,9 @@ class CharacterLanguageInfoTest(unittest.TestCase):
         )
 
     def test_leading_braille_uses_language_of_first_detectable_text(self):
-        detector = LanguageDetector(["en", "zh_TW"])
+        detector = LanguageDetector(["en", "zh_TW"], default_lang="en", charset_maps=DEFAULT_CHARSET_MAPS)
 
-        with patch("languageDetection.config.get_lang", return_value="en"):
-            sequence = list(detector.add_detected_language_commands(["⠁⠃中"]))
+        sequence = list(detector.add_detected_language_commands(["⠁⠃中"]))
 
         self.assertEqual(
             [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence],
@@ -39,25 +39,24 @@ class CharacterLanguageInfoTest(unittest.TestCase):
         )
 
     def test_leading_non_detecting_text_without_detectable_followup_keeps_current_language(self):
-        detector = LanguageDetector(["en", "zh_TW"])
+        detector = LanguageDetector(["en", "zh_TW"], default_lang="en", charset_maps=DEFAULT_CHARSET_MAPS)
 
-        with patch("languageDetection.config.get_lang", return_value="en"):
-            sequence = list(detector.add_detected_language_commands(["⠁⠃ "]))
+        sequence = list(detector.add_detected_language_commands(["⠁⠃ "]))
 
         self.assertEqual(sequence, ["⠁⠃ "])
 
-    def test_charset_map_is_loaded_from_config(self):
-        detector = LanguageDetector(["en", "zh_TW", "ja_JP"])
-
-        with patch("languageDetection.config.get_lang", return_value="en"), patch(
-            "languageDetection.config.get_charset_maps",
-            return_value={
+    def test_charset_map_comes_from_constructor(self):
+        detector = LanguageDetector(
+            ["en", "zh_TW", "ja_JP"],
+            default_lang="en",
+            charset_maps={
                 "latinCharactersLanguage": "en",
                 "CJKCharactersLanguage": "ja",
                 "arabicCharactersLanguage": "ar",
             },
-        ):
-            sequence = list(detector.add_detected_language_commands(["A中"]))
+        )
+
+        sequence = list(detector.add_detected_language_commands(["A中"]))
 
         self.assertEqual(
             [(item.lang if isinstance(item, LangChangeCommand) else item) for item in sequence],
@@ -65,10 +64,9 @@ class CharacterLanguageInfoTest(unittest.TestCase):
         )
 
     def test_preferred_full_language_comes_from_current_language(self):
-        detector = LanguageDetector(["en", "zh"])
+        detector = LanguageDetector(["en", "zh"], default_lang="zh_HK", charset_maps=DEFAULT_CHARSET_MAPS)
 
-        with patch("languageDetection.config.get_lang", return_value="zh_HK"):
-            sequence = list(detector.add_detected_language_commands([LangChangeCommand("en"), "中"]))
+        sequence = list(detector.add_detected_language_commands([LangChangeCommand("en"), "中"]))
 
         self.assertEqual(_flatten(sequence), ["en", "zh_HK", "中"])
 
@@ -78,28 +76,47 @@ class CharacterLanguageInfoTest(unittest.TestCase):
             ("zh_TW", ["en", "Hello ", "zh_TW", "中文 "]),
         ):
             with self.subTest(lang=lang):
-                detector = LanguageDetector(["en", "zh", "ja"])
+                detector = LanguageDetector(["en", "zh", "ja"], default_lang=lang, charset_maps=DEFAULT_CHARSET_MAPS)
 
-                with patch("languageDetection.config.get_lang", return_value=lang):
-                    sequence = list(detector.add_detected_language_commands(["Hello 中文 "]))
+                sequence = list(detector.add_detected_language_commands(["Hello 中文 "]))
 
                 self.assertEqual(_flatten(sequence), expected)
 
     def test_empty_charset_map_value_is_used_as_is(self):
-        detector = LanguageDetector(["en", "zh_TW"])
-
-        with patch("languageDetection.config.get_lang", return_value="en"), patch(
-            "languageDetection.config.get_charset_maps",
-            return_value={
+        detector = LanguageDetector(
+            ["en", "zh_TW"],
+            default_lang="en",
+            charset_maps={
                 "latinCharactersLanguage": "en",
                 "CJKCharactersLanguage": "",
                 "arabicCharactersLanguage": "ar",
             },
-        ):
-            sequence = list(detector.add_detected_language_commands(["A中"]))
+        )
+
+        sequence = list(detector.add_detected_language_commands(["A中"]))
 
         self.assertEqual(_flatten(sequence), ["A", "", "中"])
 
+    def test_missing_charset_map_entry_falls_back_to_first_block_language(self):
+        detector = LanguageDetector(["en", "zh_TW"], default_lang="zh_TW", charset_maps={})
+
+        sequence = list(detector.add_detected_language_commands(["中A"]))
+
+        self.assertEqual(_flatten(sequence), ["中", "en", "A"])
+
+    def test_detector_keeps_its_own_copy_of_charset_maps(self):
+        charset_maps = dict(DEFAULT_CHARSET_MAPS)
+        detector = LanguageDetector(["en", "zh_TW"], default_lang="en", charset_maps=charset_maps)
+
+        charset_maps["CJKCharactersLanguage"] = "ja"
+
+        self.assertEqual(detector.charset_maps, DEFAULT_CHARSET_MAPS)
+        self.assertIsNot(detector.charset_maps, charset_maps)
+
+    def test_language_and_charset_maps_are_required(self):
+        with self.assertRaises(TypeError):
+            LanguageDetector(["en"])
+
 
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/test_language_detection_translation.py b/client/tests/test_language_detection_translation.py
index 14b36be..47d3c05 100644
--- a/client/tests/test_language_detection_translation.py
+++ b/client/tests/test_language_detection_translation.py
@@ -3,6 +3,7 @@ import ctypes
 import unittest
 from typing import Iterable
 
+from config import DEFAULT_CHARSET_MAPS
 from languageDetection import LangChangeCommand, LanguageDetector
 
 if not hasattr(ctypes, "WINFUNCTYPE"):
@@ -33,7 +34,7 @@ def test_language_detection_translation_consistency() -> None:
 	before = [
 		"我們 Coseeing 透過開發創新工具，讓視障者看見更多資訊和可能；透過舉辦推廣活動，讓大眾看見障礙者面臨的實際挑戰和需求。希望以多元的形式與持續的行動，讓所有人都能共同看見這精采的世界以及獨特的彼此"
 	]
-	detector = LanguageDetector(["en", "zh_TW", "ja"])
+	detector = LanguageDetector(["en", "zh_TW", "ja"], default_lang="zh_TW", charset_maps=DEFAULT_CHARSET_MAPS)
 	after = list(detector.add_detected_language_commands(before))
 
 	before_merged = _merge_sequence(before)
diff --git a/client/tests/test_language_detection_unicode_braille.py b/client/tests/test_language_detection_unicode_braille.py
index d406eb9..e4e42c6 100644
--- a/client/tests/test_language_detection_unicode_braille.py
+++ b/client/tests/test_language_detection_unicode_braille.py
@@ -1,11 +1,12 @@
 import unittest
 
+from config import DEFAULT_CHARSET_MAPS
 from languageDetection import LanguageDetector
 
 
 class UnicodeBrailleLanguageDetectionTest(unittest.TestCase):
     def test_unicode_braille_keeps_current_language(self) -> None:
-        detector = LanguageDetector(["en", "zh_TW", "ja"])
+        detector = LanguageDetector(["en", "zh_TW", "ja"], default_lang="zh_TW", charset_maps=DEFAULT_CHARSET_MAPS)
 
         sequence = list(detector.add_detected_language_commands(["a⠚⠚b"]))
 
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_language_detection_char_langinfo tests.test_language_detection_unicode_braille 2>&1 | grep -E '^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//' | LC_ALL=C sort | uniq -c
$PY -m py_compile tests/test_language_detection_translation.py && echo COMPILED
```

Expected (the Windows-only module skips itself on Linux; compiling is all this box can check):

```
      1 AssertionError: TypeError not raised
      1 FAILED (failures=1, errors=11)
      1 Ran 12 tests
     11 TypeError: LanguageDetector.__init__() got an unexpected keyword argument 'default_lang'
COMPILED
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/text/pipeline.py b/client/conversion/text/pipeline.py
index cc2ee8d..1b32e18 100644
--- a/client/conversion/text/pipeline.py
+++ b/client/conversion/text/pipeline.py
@@ -58,7 +58,11 @@ def translate_plain_text_segment(
     from languageDetection import LangChangeCommand, LanguageDetector
 
     language = [key for key, value in translation_tables.items() if key not in {"default", "math"} and value != ""]
-    language_detector = LanguageDetector(language)
+    language_detector = LanguageDetector(
+        language,
+        default_lang=config.get_lang(),
+        charset_maps=config.get_charset_maps(),
+    )
     sequence = list(language_detector.add_detected_language_commands([text]))
 
     default_lang = config.get_lang().replace("-", "_").split("_", 1)[0]
diff --git a/client/languageDetection/__init__.py b/client/languageDetection/__init__.py
index c93c423..27f2f53 100644
--- a/client/languageDetection/__init__.py
+++ b/client/languageDetection/__init__.py
@@ -2,8 +2,7 @@
 
 from collections import defaultdict
 from io import StringIO
-from typing import Optional
-import config
+from typing import Mapping, Optional
 
 # import config
 # from synthDriverHandler import getSynth
@@ -70,7 +69,9 @@ class LangChangeCommand:
 class LanguageDetector(object):
 	""" Provides functionality to add guessed language commands to NVDA speech sequences.
 	Unicode ranges and user configuration are used to guess the language."""
-	def __init__(self, availableLanguages, char_langinfo=None):
+	def __init__(self, availableLanguages, *, default_lang: str, charset_maps: Mapping[str, str], char_langinfo=None):
+		self.default_lang = default_lang
+		self.charset_maps = dict(charset_maps)
 		self.char_langinfo = char_langinfo or {}
 		# 保留原始語言清單（含地區碼），供輸出時還原完整語系
 		self.availableLanguagesFull = tuple(availableLanguages)
@@ -180,7 +181,7 @@ class LanguageDetector(object):
 		sb = StringIO()
 		charset = None
 		# defaultLang = getSynth().language
-		defaultLang = config.get_lang()
+		defaultLang = self.default_lang
 		curLang = defaultLang
 		tmpLang = curLang.split("_")[0]
 		leading = True
@@ -337,8 +338,8 @@ class LanguageDetector(object):
 		# See if we have any configured language for this charset.
 		if charset in _configKeys:
 			configKey = _configKeys[charset]
-			lang = config.get_charset_maps()[configKey]
-			return lang
+			if configKey in self.charset_maps:
+				return self.charset_maps[configKey]
 		return langs[0]
 
 	def _preferred_full_lang(self, base: str, curLang: Optional[str] = None) -> str:
@@ -346,19 +347,16 @@ class LanguageDetector(object):
 
 		優先順序：
 		1) 若 curLang 與 base 符合且含地區碼，回傳 curLang。
-		2) 若 config.get_lang() 與 base 符合，回傳該完整值。
+		2) 若 default_lang 與 base 符合，回傳該完整值。
 		3) 在初始化傳入的 availableLanguages 中尋找以 base_ 開頭的第一個；找不到則回傳 base 或與 base 完全相等者。
 		"""
 		# 1) 目前語系（含地區碼）優先
 		if curLang and curLang.split("_")[0] == base and "_" in curLang:
 			return curLang
-		# 2) 全域設定偏好
-		try:
-			pref = config.get_lang()
-			if pref and pref.split("_")[0] == base:
-				return pref
-		except Exception:
-			pass
+		# 2) 預設語系（default_lang）偏好
+		pref = self.default_lang
+		if pref and pref.split("_")[0] == base:
+			return pref
 		# 3) 從可用清單中選擇最佳匹配
 		best = None
 		for lang in self.availableLanguagesFull:
PATCH
```

- [ ] **Step 4: Run them again, plus the pipeline and the dead-code guard.**

```bash
$PY -m unittest tests.test_language_detection_char_langinfo tests.test_language_detection_unicode_braille tests.test_conversion_text_pipeline tests.test_removed_dead_code 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//'
```

Expected: `Ran 26 tests`, `OK`. (`test_removed_dead_code` still finds `add_detected_language_commands` and `find_language_for_charset`; nothing it guards changes.)

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 572 19
```

Expected: `Ran 572 tests`, `FAILED (failures=1, skipped=7)`, the P2-5 `FAIL:` line, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (572)`, `new tests ok: 19 (expected 19)`.

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/languageDetection/__init__.py client/conversion/text/pipeline.py client/tests/test_language_detection_char_langinfo.py client/tests/test_language_detection_unicode_braille.py client/tests/test_language_detection_translation.py
git -C $REPO commit -F - <<'MSG'
refactor: inject language settings into LanguageDetector

LanguageDetector takes keyword-only default_lang and charset_maps
(copied) instead of reading config. A charset key missing from the map
falls back to the block's first language instead of raising KeyError;
a present key, even an empty string, is used as before. The text
pipeline passes config.get_lang() and config.get_charset_maps() for
now.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 6: `ConversionRequest` carries `lang` and `charset_maps`

**Files:**
- Modify: `client/conversion/output.py`, `client/gui.py`, `client/main.py`
- Modify tests: `test_conversion_service.py`, `test_conversion_text_pipeline.py`, `test_conversion_jobs.py`, `test_conversion_language_explicit.py`, `test_gui_document_flows.py`, `test_main_demo.py`

**Interfaces:** `ConversionRequest` gains required `lang: str` and `charset_maps: dict[str, str]` after `translation_tables`. `BrailleFrame._build_conversion_request` adds `lang=get_lang(), charset_maps=get_charset_maps()`; `gui.py` adds both names to its `from config import (...)` block. `main.run_demo` does the same (its `from config import` line gains both). Nothing below the request reads the fields yet.

Tests: every `ConversionRequest(...)` gets the two fields (`test_conversion_service` uses new module constants `LANG = "zh_TW"` and `CHARSET_MAPS`). The two existing `_build_conversion_request` gui tests patch `gui.get_lang`/`gui.get_charset_maps` so they no longer read the real config. New: `test_conversion_request_reads_language_settings_per_request` (spec test 11, refinement 6) and `test_demo_request_carries_language_settings` (spec test 12, refinement 2). The end-to-end characterization helper takes the request language (the tests still patch `config`, because the pipeline still reads it).

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_jobs.py b/client/tests/test_conversion_jobs.py
index de00512..4995fe5 100644
--- a/client/tests/test_conversion_jobs.py
+++ b/client/tests/test_conversion_jobs.py
@@ -8,6 +8,7 @@ from conversion.jobs import (
 	ConversionJobRunner,
 	ConversionJobSuccess,
 )
+from config import DEFAULT_CHARSET_MAPS
 from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError
 
 
@@ -43,6 +44,8 @@ class ConversionJobRunnerTest(unittest.TestCase):
 				dictionary_path=Path("dictionary/default.csv"),
 				data_dir=Path("data"),
 				translation_tables={"default": "zh-tw.ctb", "math": "nemeth.ctb"},
+				lang="zh_TW",
+				charset_maps=dict(DEFAULT_CHARSET_MAPS),
 			),
 			completion_policy=ConversionCompletionPolicy() if completion_policy is None else completion_policy,
 		)
diff --git a/client/tests/test_conversion_language_explicit.py b/client/tests/test_conversion_language_explicit.py
index 69f7ce0..578165e 100644
--- a/client/tests/test_conversion_language_explicit.py
+++ b/client/tests/test_conversion_language_explicit.py
@@ -69,7 +69,7 @@ class ConversionLanguageTest(unittest.TestCase):
         with path.open("w", newline="", encoding="utf-8") as f:
             csv.DictWriter(f, fieldnames=fieldnames).writeheader()
 
-    def _convert(self, raw_text: str):
+    def _convert(self, raw_text: str, *, lang: str):
         text_translator = RecordingTextTranslator()
         math_translator = RecordingMathTranslator()
         request = ConversionRequest(
@@ -79,6 +79,8 @@ class ConversionLanguageTest(unittest.TestCase):
             dictionary_path=self.dictionary_path,
             data_dir=self.data_dir,
             translation_tables=dict(TABLES),
+            lang=lang,
+            charset_maps=dict(config.DEFAULT_CHARSET_MAPS),
         )
         output = convert_text_with_alignment(
             request,
@@ -91,7 +93,7 @@ class ConversionLanguageTest(unittest.TestCase):
         with patch.object(config, "get_lang", return_value="en"), patch.object(
             config, "get_charset_maps", return_value=dict(config.DEFAULT_CHARSET_MAPS)
         ):
-            output, text_calls, math_calls = self._convert(MIXED_TEXT)
+            output, text_calls, math_calls = self._convert(MIXED_TEXT, lang="en")
 
         self.assertEqual(output.display_text.rstrip("\u2800"), MIXED_TEXT_BRAILLE)
         self.assertEqual(text_calls, MIXED_TEXT_CALLS)
@@ -101,7 +103,7 @@ class ConversionLanguageTest(unittest.TestCase):
         for lang, table in (("en", "en.ctb"), ("zh_TW", "zh.ctb")):
             with self.subTest(lang=lang):
                 with patch.object(config, "get_lang", return_value=lang):
-                    _output, text_calls, _math_calls = self._convert("\u2192")
+                    _output, text_calls, _math_calls = self._convert("\u2192", lang=lang)
 
                 self.assertEqual(text_calls, [("\u2192", table)])
 
diff --git a/client/tests/test_conversion_service.py b/client/tests/test_conversion_service.py
index fd741e3..54d96ad 100644
--- a/client/tests/test_conversion_service.py
+++ b/client/tests/test_conversion_service.py
@@ -6,6 +6,7 @@ from types import ModuleType
 
 from adapters.translation.contracts import TranslationRuntime
 from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
+from config import DEFAULT_CHARSET_MAPS
 from dual_view.model import DualViewSegment
 from conversion.service import (
     ConversionOutput,
@@ -19,6 +20,10 @@ from conversion.service import (
 from translate import TranslationResult
 
 
+LANG = "zh_TW"
+CHARSET_MAPS = dict(DEFAULT_CHARSET_MAPS)
+
+
 class FakeTextTranslator:
     def __init__(self) -> None:
         self.calls = []
@@ -62,6 +67,8 @@ class ConversionServiceTest(unittest.TestCase):
             dictionary_path=Path("dictionary/default.csv"),
             data_dir=Path("data"),
             translation_tables={"default": "zh-tw.ctb"},
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
     def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
@@ -174,6 +181,8 @@ class ConversionServiceTest(unittest.TestCase):
             dictionary_path=dictionary_path,
             data_dir=self.test_dir,
             translation_tables={"default": "table.ctb"},
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         output = convert_text_with_alignment(request, runtime=self._runtime())
@@ -196,6 +205,8 @@ class ConversionServiceTest(unittest.TestCase):
             dictionary_path=dictionary_path,
             data_dir=self.test_dir,
             translation_tables={"default": "table.ctb"},
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
         runtime = self._runtime()
 
@@ -219,6 +230,8 @@ class ConversionServiceTest(unittest.TestCase):
             dictionary_path=dictionary_path,
             data_dir=self.test_dir,
             translation_tables={"default": "table.ctb"},
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         with self.assertRaises(ConversionStageError) as context:
@@ -383,6 +396,8 @@ class ConversionServiceTest(unittest.TestCase):
             dictionary_path=self.dictionary_path,
             data_dir=self.test_dir,
             translation_tables={"default": "zh-tw.ctb"},
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
         output = convert_text_with_alignment(request, runtime=self._runtime())
 
@@ -398,6 +413,8 @@ class ConversionServiceTest(unittest.TestCase):
             dictionary_path=self.dictionary_path,
             data_dir=self.test_dir,
             translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
         output = convert_text_with_alignment(request, runtime=self._runtime())
 
@@ -414,6 +431,8 @@ class ConversionServiceTest(unittest.TestCase):
             dictionary_path=self.dictionary_path,
             data_dir=self.test_dir,
             translation_tables={"default": "zh-tw.ctb", "math": "Nemeth"},
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
         output = convert_text_with_alignment(request, runtime=self._runtime())
 
@@ -443,6 +462,8 @@ class ConversionServiceTest(unittest.TestCase):
             dictionary_path=self.dictionary_path,
             data_dir=self.test_dir,
             translation_tables={"default": "zh-tw.ctb"},
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
         output = convert_text_with_alignment(request, runtime=self._runtime())
 
diff --git a/client/tests/test_conversion_text_pipeline.py b/client/tests/test_conversion_text_pipeline.py
index b2c9c3e..99ea87c 100644
--- a/client/tests/test_conversion_text_pipeline.py
+++ b/client/tests/test_conversion_text_pipeline.py
@@ -5,6 +5,7 @@ from unittest.mock import patch
 from pathlib import Path
 
 from adapters.translation.contracts import TranslationRuntime
+from config import DEFAULT_CHARSET_MAPS
 from conversion.output import ConversionRequest, convert_text_with_alignment
 from conversion.text.dictionary_rules import apply_dictionary, split_bracket_segments
 from conversion.text.pipeline import (
@@ -212,6 +213,8 @@ class ConversionTextPipelineTest(unittest.TestCase):
                 dictionary_path=dictionary_path,
                 data_dir=data_dir,
                 translation_tables={"default": "table.ctb"},
+                lang="en",
+                charset_maps=dict(DEFAULT_CHARSET_MAPS),
             )
 
             translated_texts = []
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 7cba126..f1002f8 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -907,7 +907,9 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         frame = self._make_frame()
         frame.translation_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}
 
-        request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
+        with patch.object(gui, "get_lang", return_value="zh_TW"), \
+             patch.object(gui, "get_charset_maps", return_value={"CJKCharactersLanguage": "zh"}):
+            request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
 
         self.assertEqual(
             request.translation_tables,
@@ -925,10 +927,28 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
              patch.object(gui, "save_translation_tables"), \
              patch.object(gui, "save_view_settings"):
             frame.apply_settings_from_dialog(snapshot)
-        request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
+        with patch.object(gui, "get_lang", return_value="zh_TW"), \
+             patch.object(gui, "get_charset_maps", return_value={"CJKCharactersLanguage": "zh"}):
+            request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
 
         self.assertEqual(request.translation_tables, snapshot.translation_tables)
 
+    def test_conversion_request_reads_language_settings_per_request(self) -> None:
+        frame = self._make_frame()
+        frame.translation_tables = {"default": "test-default.ctb"}
+        first_maps = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "zh"}
+        second_maps = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "ja"}
+
+        with patch.object(gui, "get_lang", side_effect=["en", "zh_TW"]) as get_lang, \
+             patch.object(gui, "get_charset_maps", side_effect=[first_maps, second_maps]) as get_charset_maps:
+            first = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
+            second = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))
+
+        self.assertEqual((first.lang, first.charset_maps), ("en", first_maps))
+        self.assertEqual((second.lang, second.charset_maps), ("zh_TW", second_maps))
+        self.assertEqual(get_lang.call_count, 2)
+        self.assertEqual(get_charset_maps.call_count, 2)
+
     def test_convert_without_default_table_shows_info_and_does_not_convert(self) -> None:
         frame = self._make_frame()
         frame.translation_tables = {"default": ""}
diff --git a/client/tests/test_main_demo.py b/client/tests/test_main_demo.py
index 739e83a..1ecf18c 100644
--- a/client/tests/test_main_demo.py
+++ b/client/tests/test_main_demo.py
@@ -27,6 +27,26 @@ class MainDemoTest(unittest.TestCase):
         print_mock.assert_called_once_with("braille")
         runtime.close.assert_called_once_with()
 
+    def test_demo_request_carries_language_settings(self) -> None:
+        runtime = Mock()
+        charset_maps = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "ja"}
+        with (
+            patch.object(main, "build_default_translation_runtime", return_value=runtime),
+            patch.object(main, "convert_text_with_alignment", return_value=ConversionOutput("braille", (), ())) as convert,
+            patch.object(main, "get_lang", return_value="en") as get_lang,
+            patch.object(main, "get_charset_maps", return_value=charset_maps) as get_charset_maps,
+            patch("builtins.print") as print_mock,
+        ):
+            main.run_demo("x")
+
+        request = convert.call_args.args[0]
+        self.assertEqual(request.lang, "en")
+        self.assertEqual(request.charset_maps, charset_maps)
+        get_lang.assert_called_once_with()
+        get_charset_maps.assert_called_once_with()
+        print_mock.assert_called_once_with("braille")
+        runtime.close.assert_called_once_with()
+
 
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_conversion_service tests.test_conversion_text_pipeline tests.test_conversion_jobs tests.test_conversion_language_explicit tests.test_gui_document_flows tests.test_main_demo 2>&1 | grep -E '^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//' | LC_ALL=C sort | uniq -c
```

Expected:

```
      3 AttributeError: <module 'gui' from '/workspace/DotExpress/client/gui.py'> does not have the attribute 'get_lang'
      1 AttributeError: <module 'main' from '/workspace/DotExpress/client/main.py'> does not have the attribute 'get_lang'
      1 FAILED (errors=32)
      1 Ran 106 tests
     28 TypeError: ConversionRequest.__init__() got an unexpected keyword argument 'lang'
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/output.py b/client/conversion/output.py
index b6cd6ce..0054217 100644
--- a/client/conversion/output.py
+++ b/client/conversion/output.py
@@ -16,6 +16,8 @@ class ConversionRequest:
     dictionary_path: Path
     data_dir: Path
     translation_tables: dict[str, str]
+    lang: str
+    charset_maps: dict[str, str]
 
 
 @dataclass(frozen=True)
diff --git a/client/gui.py b/client/gui.py
index 9d869df..eefdb51 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -57,6 +57,8 @@ from ui.action_menu import (
 from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
 from config import (
 	DEFAULT_TRANSLATION_TABLES,
+	get_charset_maps,
+	get_lang,
 	set_selected_dictionary,
 )
 from settings.translation import (
@@ -702,6 +704,8 @@ class BrailleFrame(wx.Frame):
 			dictionary_path=dictionary_path,
 			data_dir=resource_path("data"),
 			translation_tables=self.translation_tables.copy(),
+			lang=get_lang(),
+			charset_maps=get_charset_maps(),
 		)
 
 	def _format_batch_issue_lines(self, issues: list[BatchIssue]) -> list[str]:
diff --git a/client/main.py b/client/main.py
index 06a0b21..97eb1a4 100644
--- a/client/main.py
+++ b/client/main.py
@@ -2,7 +2,7 @@ from pathlib import Path
 
 from adapters.translation.provider import build_default_translation_runtime
 from app_paths import get_dictionary_directory
-from config import DEFAULT_TRANSLATION_TABLES
+from config import DEFAULT_TRANSLATION_TABLES, get_charset_maps, get_lang
 from conversion.service import ConversionRequest, convert_text_with_alignment
 
 
@@ -27,6 +27,8 @@ def run_demo(text: str = SAMPLE_TEXT) -> None:
                     "default": "en-ueb-g2.ctb",
                     "en": "en-ueb-g2.ctb",
                 },
+                lang=get_lang(),
+                charset_maps=get_charset_maps(),
             ),
             runtime=runtime,
         )
PATCH
```

- [ ] **Step 4: Run them again, and the gui module alone.**

```bash
$PY -m unittest tests.test_conversion_service tests.test_conversion_text_pipeline tests.test_conversion_jobs tests.test_conversion_language_explicit tests.test_gui_document_flows tests.test_main_demo 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_gui_document_flows 2>&1 | tail -1
```

Expected (only the P2-5 failure in the first run; the gui module passes alone):

```
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 106 tests
FAILED (failures=1)
OK
```

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 574 21
```

Expected: `Ran 574 tests`, `FAILED (failures=1, skipped=7)`, the P2-5 `FAIL:` line, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (574)`, `new tests ok: 21 (expected 21)`.

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/conversion/output.py client/gui.py client/main.py client/tests/test_conversion_jobs.py client/tests/test_conversion_language_explicit.py client/tests/test_conversion_service.py client/tests/test_conversion_text_pipeline.py client/tests/test_gui_document_flows.py client/tests/test_main_demo.py
git -C $REPO commit -F - <<'MSG'
refactor: carry conversion language on ConversionRequest

ConversionRequest gains required lang and charset_maps fields.
BrailleFrame._build_conversion_request and main.run_demo fill them from
config.get_lang() and config.get_charset_maps() once per request, on
the calling thread, so a config.json edit still reaches the next
conversion. The layers below do not use the fields yet.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 7: Thread the language through the service and the text pipeline

**Files:**
- Modify: `client/conversion/output.py`, `client/conversion/service.py`, `client/conversion/text/pipeline.py`
- Modify tests: `test_conversion_service.py`, `test_conversion_text_pipeline.py`, `test_conversion_language_explicit.py`, `test_translation_import_isolation.py`, `test_translation_language_result.py` (Windows-only)

**Interfaces:**
- `translate_plain_text_segment(text, dictionary_path, translation_tables, bopomofo_path, *, runtime, lang, charset_maps)`: `LanguageDetector(language, default_lang=lang, charset_maps=charset_maps)` and `default_lang = lang.replace("-", "_").split("_", 1)[0]`; `import config` removed.
- `translate_with_language_dual_view_segments`, `translate_with_language_segments`, `translate_with_language` and the inner `translate_segments_with_dual_view` take keyword-only `lang, charset_maps` after `runtime` and forward them; math segments get `language=lang`; the boundary-space call is unchanged; `service.py` is back to `from config import DEFAULT_MATH_BRAILLE_TABLE`.
- `conversion.output.convert_text_with_alignment` passes `lang=request.lang, charset_maps=request.charset_maps` to `translate_segments`; `output.py` still does not import `config`.

Tests: the 10 `translate_with_language*` calls get `lang=LANG, charset_maps=CHARSET_MAPS`; `FakeMathTranslator` records `(source, braille_code, language)` and `test_translate_with_language_passes_selected_math_braille_code` expects `[("1", "UEB", "zh_TW")]`. The pipeline tests pass `lang`/`charset_maps` instead of patching (the `patch` import goes). The end-to-end file takes its final form (spec tests 1 and 2): the request says `en`, `config.get_lang`/`config.get_charset_maps` raise if called, `TEXT2BRAILLE_LANG` is `zh_TW` in one run and `ja` in the other, `config._runtime_lang` is `ko` (restored by cleanup); the output, the text-translator calls and the math calls equal the Task 1 characterization, and every math call has language `en`. `test_language_consumers_do_not_import_config` is spec test 10. The Windows-only call is rewritten for the new keywords and loses the stray leading `"zh-tw.ctb"` positional that makes it raise `TypeError` today.

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_conversion_language_explicit.py b/client/tests/test_conversion_language_explicit.py
index 578165e..1e05ec6 100644
--- a/client/tests/test_conversion_language_explicit.py
+++ b/client/tests/test_conversion_language_explicit.py
@@ -1,4 +1,5 @@
 import csv
+import os
 import tempfile
 import unittest
 from pathlib import Path
@@ -46,7 +47,7 @@ class RecordingMathTranslator:
     def translate(self, source, *, braille_code, language):
         from translate import TranslationResult
 
-        self.calls.append((source, braille_code))
+        self.calls.append((source, braille_code, language))
         braille = list(f"M[{source}]")
         return TranslationResult([source], braille, [0] * len(braille), [0])
 
@@ -64,15 +65,15 @@ class ConversionLanguageTest(unittest.TestCase):
         self._write_csv(self.dictionary_path, ["text", "braille", "type"])
         self._write_csv(self.data_dir / "Bopomofo2Braille.csv", ["Bopomofo", "Braille"])
         self._write_csv(self.data_dir / "BopomofoChar2Braille.csv", ["Bopomofo", "Braille"])
+        original_runtime_lang = config._runtime_lang
+        self.addCleanup(setattr, config, "_runtime_lang", original_runtime_lang)
 
     def _write_csv(self, path: Path, fieldnames: list[str]) -> None:
         with path.open("w", newline="", encoding="utf-8") as f:
             csv.DictWriter(f, fieldnames=fieldnames).writeheader()
 
-    def _convert(self, raw_text: str, *, lang: str):
-        text_translator = RecordingTextTranslator()
-        math_translator = RecordingMathTranslator()
-        request = ConversionRequest(
+    def _request(self, raw_text: str, *, lang: str) -> ConversionRequest:
+        return ConversionRequest(
             raw_text=raw_text,
             output_mode="unicode",
             width=40,
@@ -82,28 +83,42 @@ class ConversionLanguageTest(unittest.TestCase):
             lang=lang,
             charset_maps=dict(config.DEFAULT_CHARSET_MAPS),
         )
-        output = convert_text_with_alignment(
-            request,
-            map_char=lambda text, **_kwargs: text,
-            runtime=TranslationRuntime(text_translator=text_translator, math_translator=math_translator),
-        )
-        return output, text_translator.calls, math_translator.calls
 
-    def test_mixed_text_translation_for_english(self) -> None:
-        with patch.object(config, "get_lang", return_value="en"), patch.object(
-            config, "get_charset_maps", return_value=dict(config.DEFAULT_CHARSET_MAPS)
+    def _convert(self, request: ConversionRequest, *, env_lang: str):
+        text_translator = RecordingTextTranslator()
+        math_translator = RecordingMathTranslator()
+        config._runtime_lang = "ko"
+        with patch.dict(os.environ, {config.LANG_ENV: env_lang}), patch.object(
+            config, "get_lang", side_effect=AssertionError("config.get_lang must not be read")
+        ), patch.object(
+            config, "get_charset_maps", side_effect=AssertionError("config.get_charset_maps must not be read")
         ):
-            output, text_calls, math_calls = self._convert(MIXED_TEXT, lang="en")
+            output = convert_text_with_alignment(
+                request,
+                map_char=lambda text, **_kwargs: text,
+                runtime=TranslationRuntime(text_translator=text_translator, math_translator=math_translator),
+            )
+        return output, text_translator.calls, math_translator.calls
+
+    def test_same_request_gives_same_output_in_any_environment(self) -> None:
+        request = self._request(MIXED_TEXT, lang="en")
+
+        first = self._convert(request, env_lang="zh_TW")
+        second = self._convert(request, env_lang="ja")
 
-        self.assertEqual(output.display_text.rstrip("\u2800"), MIXED_TEXT_BRAILLE)
-        self.assertEqual(text_calls, MIXED_TEXT_CALLS)
-        self.assertEqual(math_calls, [("1", "Nemeth")])
+        for output, text_calls, math_calls in (first, second):
+            self.assertEqual(output.display_text.rstrip("\u2800"), MIXED_TEXT_BRAILLE)
+            self.assertEqual(text_calls, MIXED_TEXT_CALLS)
+            self.assertEqual(math_calls, [("1", "Nemeth", "en")])
+        self.assertEqual(first[0].display_text, second[0].display_text)
 
-    def test_non_detecting_text_follows_language(self) -> None:
+    def test_non_detecting_text_follows_request_language(self) -> None:
         for lang, table in (("en", "en.ctb"), ("zh_TW", "zh.ctb")):
             with self.subTest(lang=lang):
-                with patch.object(config, "get_lang", return_value=lang):
-                    _output, text_calls, _math_calls = self._convert("\u2192", lang=lang)
+                _output, text_calls, _math_calls = self._convert(
+                    self._request("\u2192", lang=lang),
+                    env_lang="ja",
+                )
 
                 self.assertEqual(text_calls, [("\u2192", table)])
 
diff --git a/client/tests/test_conversion_service.py b/client/tests/test_conversion_service.py
index 54d96ad..5e368d2 100644
--- a/client/tests/test_conversion_service.py
+++ b/client/tests/test_conversion_service.py
@@ -42,7 +42,7 @@ class FakeMathTranslator:
         self.error = error
 
     def translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult:
-        self.calls.append((source, braille_code))
+        self.calls.append((source, braille_code, language))
         if self.error is not None:
             raise self.error
         braille = list(f"M[{source}]")
@@ -264,6 +264,8 @@ class ConversionServiceTest(unittest.TestCase):
             {"default": "zh-tw.ctb", "math": "Nemeth"},
             self.bopomofo_path,
             runtime=runtime,
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         self.assertEqual(result.raw, ["計算", " ", "1+2", " ", "的值"])
@@ -280,6 +282,8 @@ class ConversionServiceTest(unittest.TestCase):
             {"default": "table.ctb", "math": "Nemeth"},
             self.bopomofo_path,
             runtime=runtime,
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         self.assertEqual([result.raw for result in results], [["ab"], [" "], ["x+1"]])
@@ -294,6 +298,8 @@ class ConversionServiceTest(unittest.TestCase):
             {"default": "default.ctb", "math": "Nemeth"},
             self.bopomofo_path,
             runtime=runtime,
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         self.assertIn((" ", "default.ctb", " ", False), runtime.text_translator.calls)
@@ -308,6 +314,8 @@ class ConversionServiceTest(unittest.TestCase):
             {"default": "table.ctb", "math": "Nemeth"},
             self.bopomofo_path,
             runtime=runtime,
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         self.assertEqual([result.raw for result in results], [["甲「乙」"]])
@@ -328,6 +336,8 @@ class ConversionServiceTest(unittest.TestCase):
             {"default": "table.ctb"},
             self.bopomofo_path,
             runtime=runtime,
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         self.assertEqual([result.raw for result in results], [["台灣"]])
@@ -343,6 +353,8 @@ class ConversionServiceTest(unittest.TestCase):
             {"default": "zh-tw.ctb", "math": "Nemeth"},
             self.bopomofo_path,
             runtime=runtime,
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         self.assertEqual(result.raw, ["計算 ", "1+2", " 的值"])
@@ -358,6 +370,8 @@ class ConversionServiceTest(unittest.TestCase):
                 {"default": "zh-tw.ctb", "math": "Nemeth"},
                 self.bopomofo_path,
                 runtime=runtime,
+                lang=LANG,
+                charset_maps=CHARSET_MAPS,
             )
 
     def test_translate_with_language_passes_selected_math_braille_code(self) -> None:
@@ -370,9 +384,11 @@ class ConversionServiceTest(unittest.TestCase):
             {"default": "zh-tw.ctb", "math": "UEB"},
             self.bopomofo_path,
             runtime=runtime,
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
-        self.assertEqual(math_translator.calls, [("1", "UEB")])
+        self.assertEqual(math_translator.calls, [("1", "UEB", "zh_TW")])
 
     def test_translate_with_language_keeps_escaped_dollar_in_plain_text_segment(self) -> None:
         from conversion import service
@@ -383,6 +399,8 @@ class ConversionServiceTest(unittest.TestCase):
             {"default": "zh-tw.ctb"},
             self.bopomofo_path,
             runtime=runtime,
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         self.assertEqual(result.raw, ["價格\\$100"])
@@ -449,6 +467,8 @@ class ConversionServiceTest(unittest.TestCase):
             {"default": "table.ctb", "math": "Nemeth"},
             self.bopomofo_path,
             runtime=runtime,
+            lang=LANG,
+            charset_maps=CHARSET_MAPS,
         )
 
         for result in results:
diff --git a/client/tests/test_conversion_text_pipeline.py b/client/tests/test_conversion_text_pipeline.py
index 99ea87c..18e4e04 100644
--- a/client/tests/test_conversion_text_pipeline.py
+++ b/client/tests/test_conversion_text_pipeline.py
@@ -1,7 +1,6 @@
 import csv
 import tempfile
 import unittest
-from unittest.mock import patch
 from pathlib import Path
 
 from adapters.translation.contracts import TranslationRuntime
@@ -155,14 +154,15 @@ class ConversionTextPipelineTest(unittest.TestCase):
 
             runtime = TranslationRuntime(text_translator=Translator(), math_translator=Translator())
 
-            with patch("conversion.text.pipeline.config.get_lang", return_value="en"):
-                translate_plain_text_segment(
-                    "Hello",
-                    dictionary_path,
-                    {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb"},
-                    bopomofo_path,
-                    runtime=runtime,
-                )
+            translate_plain_text_segment(
+                "Hello",
+                dictionary_path,
+                {"default": "zh-tw.ctb", "en": "en-ueb-g1.ctb"},
+                bopomofo_path,
+                runtime=runtime,
+                lang="en",
+                charset_maps=dict(DEFAULT_CHARSET_MAPS),
+            )
 
             self.assertEqual(calls, ["en-ueb-g1.ctb"])
 
@@ -235,14 +235,15 @@ class ConversionTextPipelineTest(unittest.TestCase):
                 dictionary_path, bopomofo_path = self._plain_text_paths(Path(tmpdir))
                 calls = []
 
-                with patch("conversion.text.pipeline.config.get_lang", return_value=lang):
-                    translate_plain_text_segment(
-                        "\u2192",
-                        dictionary_path,
-                        LANGUAGE_TABLES,
-                        bopomofo_path,
-                        runtime=self._recording_runtime(calls),
-                    )
+                translate_plain_text_segment(
+                    "\u2192",
+                    dictionary_path,
+                    LANGUAGE_TABLES,
+                    bopomofo_path,
+                    runtime=self._recording_runtime(calls),
+                    lang=lang,
+                    charset_maps=dict(DEFAULT_CHARSET_MAPS),
+                )
 
                 self.assertEqual(calls, [("\u2192", table)])
 
@@ -257,16 +258,14 @@ class ConversionTextPipelineTest(unittest.TestCase):
                 dictionary_path, bopomofo_path = self._plain_text_paths(Path(tmpdir))
                 calls = []
 
-                with patch("conversion.text.pipeline.config.get_lang", return_value="en"), patch(
-                    "conversion.text.pipeline.config.get_charset_maps",
-                    return_value=charset_maps,
-                ):
-                    translate_plain_text_segment(
-                        "A中",
-                        dictionary_path,
-                        LANGUAGE_TABLES,
-                        bopomofo_path,
-                        runtime=self._recording_runtime(calls),
-                    )
+                translate_plain_text_segment(
+                    "A中",
+                    dictionary_path,
+                    LANGUAGE_TABLES,
+                    bopomofo_path,
+                    runtime=self._recording_runtime(calls),
+                    lang="en",
+                    charset_maps=charset_maps,
+                )
 
                 self.assertEqual(calls, [("A", "en.ctb"), (" ", "en.ctb"), ("中", table)])
diff --git a/client/tests/test_translation_import_isolation.py b/client/tests/test_translation_import_isolation.py
index 0f1a39f..6fa0f35 100644
--- a/client/tests/test_translation_import_isolation.py
+++ b/client/tests/test_translation_import_isolation.py
@@ -21,6 +21,25 @@ assert "libmathcat_py" not in sys.modules
 
         self.assertEqual(completed.returncode, 0, completed.stderr)
 
+    def test_language_consumers_do_not_import_config(self) -> None:
+        script = """
+import sys
+import languageDetection
+import conversion.text.pipeline
+import conversion.output
+import conversion.mathcat_adapter
+import braille.tables
+assert "config" not in sys.modules, "config was imported"
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
diff --git a/client/tests/test_translation_language_result.py b/client/tests/test_translation_language_result.py
index 3165c1c..e36f5a4 100644
--- a/client/tests/test_translation_language_result.py
+++ b/client/tests/test_translation_language_result.py
@@ -12,7 +12,7 @@ except Exception as exc:
 	raise unittest.SkipTest(f"liblouis bindings unavailable: {exc}") from exc
 
 from adapters.translation.provider import build_default_translation_runtime
-from config import DEFAULT_TRANSLATION_TABLES
+from config import DEFAULT_CHARSET_MAPS, DEFAULT_TRANSLATION_TABLES
 from conversion.service import translate_with_language
 
 
@@ -23,12 +23,13 @@ def test_add_blank_between_language_change() -> None:
 	runtime = build_default_translation_runtime()
 	try:
 		result = translate_with_language(
-			"zh-tw.ctb",
 			"嶼我I起",
 			BASE_DIR / "dictionary" / "default.csv",
 			DEFAULT_TRANSLATION_TABLES,
 			BASE_DIR / "data" / "Bopomofo2Braille.csv",
 			runtime=runtime,
+			lang="zh_TW",
+			charset_maps=DEFAULT_CHARSET_MAPS,
 		)
 	finally:
 		runtime.close()
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_conversion_service tests.test_conversion_text_pipeline tests.test_conversion_language_explicit tests.test_translation_import_isolation 2>&1 | grep -E '^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//' | LC_ALL=C sort | uniq -c
$PY -m py_compile tests/test_translation_language_result.py && echo COMPILED
```

Expected (the three `config.get_lang must not be read` errors show the pipeline still reading config; the isolation subprocess fails because `conversion.text.pipeline` still imports it):

```
      1 AssertionError: 1 != 0 : Traceback (most recent call last):
      1 AssertionError: config was imported
      3 AssertionError: config.get_lang must not be read
      1 FAILED (failures=1, errors=18)
      1 Ran 33 tests
      5 TypeError: translate_plain_text_segment() got an unexpected keyword argument 'lang'
      5 TypeError: translate_with_language() got an unexpected keyword argument 'lang'
      5 TypeError: translate_with_language_segments() got an unexpected keyword argument 'lang'
COMPILED
```

- [ ] **Step 3: Implement.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/conversion/output.py b/client/conversion/output.py
index 0054217..b9ff14e 100644
--- a/client/conversion/output.py
+++ b/client/conversion/output.py
@@ -68,6 +68,8 @@ def convert_text_with_alignment(
             request.translation_tables,
             request.data_dir / "Bopomofo2Braille.csv",
             runtime=runtime,
+            lang=request.lang,
+            charset_maps=request.charset_maps,
         )
         braille_wrapped, _text_wrapped = wrap_translation_results(translations, request.width)
     except Exception as error:
diff --git a/client/conversion/service.py b/client/conversion/service.py
index 86a3c44..67cfd7f 100644
--- a/client/conversion/service.py
+++ b/client/conversion/service.py
@@ -1,5 +1,5 @@
 from adapters.translation.contracts import TranslationRuntime
-from config import DEFAULT_MATH_BRAILLE_TABLE, get_lang
+from config import DEFAULT_MATH_BRAILLE_TABLE
 from conversion.text.char_maps import translate__mapping_char
 from conversion.output import (
     ConversionOutput,
@@ -30,6 +30,8 @@ def translate_with_language_dual_view_segments(
     bopomofo_path,
     *,
     runtime: TranslationRuntime,
+    lang: str,
+    charset_maps: dict[str, str],
 ) -> list[DualViewSegment]:
     if text == "":
         return []
@@ -53,6 +55,8 @@ def translate_with_language_dual_view_segments(
                 translation_tables,
                 bopomofo_path,
                 runtime=runtime,
+                lang=lang,
+                charset_maps=charset_maps,
             )
             if isinstance(plain_results, (list, tuple)):
                 for result in plain_results:
@@ -63,7 +67,7 @@ def translate_with_language_dual_view_segments(
             result = runtime.math_translator.translate(
                 segment["text"],
                 braille_code=math_braille_code,
-                language=get_lang(),
+                language=lang,
             )
             segments_records.append(DualViewSegment(result=result, source_kind="math"))
     return segments_records
@@ -76,6 +80,8 @@ def translate_with_language_segments(
     bopomofo_path,
     *,
     runtime: TranslationRuntime,
+    lang: str,
+    charset_maps: dict[str, str],
 ):
     return [
         segment.result
@@ -85,6 +91,8 @@ def translate_with_language_segments(
             translation_tables,
             bopomofo_path,
             runtime=runtime,
+            lang=lang,
+            charset_maps=charset_maps,
         )
     ]
 
@@ -96,6 +104,8 @@ def translate_with_language(
     bopomofo_path,
     *,
     runtime: TranslationRuntime,
+    lang: str,
+    charset_maps: dict[str, str],
 ):
     return merge_translation_results(
         translate_with_language_segments(
@@ -104,6 +114,8 @@ def translate_with_language(
             translation_tables,
             bopomofo_path,
             runtime=runtime,
+            lang=lang,
+            charset_maps=charset_maps,
         )
     )
 
@@ -117,7 +129,7 @@ def convert_text_with_alignment(
     captured_segments: list[DualViewSegment] = []
 
     def translate_segments_with_dual_view(
-        text, dictionary_path, translation_tables, bopomofo_path, *, runtime
+        text, dictionary_path, translation_tables, bopomofo_path, *, runtime, lang, charset_maps
     ):
         segments = translate_with_language_dual_view_segments(
             text,
@@ -125,6 +137,8 @@ def convert_text_with_alignment(
             translation_tables,
             bopomofo_path,
             runtime=runtime,
+            lang=lang,
+            charset_maps=charset_maps,
         )
         captured_segments.extend(segments)
         return [s.result for s in segments]
diff --git a/client/conversion/text/pipeline.py b/client/conversion/text/pipeline.py
index 1b32e18..7d125c2 100644
--- a/client/conversion/text/pipeline.py
+++ b/client/conversion/text/pipeline.py
@@ -1,7 +1,6 @@
 from pathlib import Path
 from typing import Callable
 
-import config
 from adapters.translation.contracts import TranslationRuntime
 from conversion.preprocessing.user_script import execute_preprocessing_script
 from conversion.preprocessing.literal_braille import (
@@ -53,19 +52,17 @@ def translate_plain_text_segment(
     bopomofo_path: Path,
     *,
     runtime: TranslationRuntime,
+    lang: str,
+    charset_maps: dict[str, str],
 ):
     from text.zhuyin import normalize_zhuyin_sequence
     from languageDetection import LangChangeCommand, LanguageDetector
 
     language = [key for key, value in translation_tables.items() if key not in {"default", "math"} and value != ""]
-    language_detector = LanguageDetector(
-        language,
-        default_lang=config.get_lang(),
-        charset_maps=config.get_charset_maps(),
-    )
+    language_detector = LanguageDetector(language, default_lang=lang, charset_maps=charset_maps)
     sequence = list(language_detector.add_detected_language_commands([text]))
 
-    default_lang = config.get_lang().replace("-", "_").split("_", 1)[0]
+    default_lang = lang.replace("-", "_").split("_", 1)[0]
     translate_table = translation_tables.get(default_lang) or translation_tables["default"]
     translations = []
     for item in sequence:
PATCH
```

- [ ] **Step 4: Run them again.**

```bash
$PY -m unittest tests.test_conversion_service tests.test_conversion_text_pipeline tests.test_conversion_language_explicit tests.test_translation_import_isolation 2>&1 | grep -E '^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//'
```

Expected (only the P2-5 failure):

```
FAIL: test_translate_with_language_does_not_duplicate_existing_spaces_around_math (tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_does_not_duplicate_existing_spaces_around_math)
AssertionError: Lists differ: ['計算 ', '1+2', ' ', '的值'] != ['計算 ', '1+2', ' 的值']
Ran 33 tests
FAILED (failures=1)
```

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 575 22
```

Expected: `Ran 575 tests`, `FAILED (failures=1, skipped=7)`, the P2-5 `FAIL:` line, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (575)`, `new tests ok: 22 (expected 22)`.

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/conversion/output.py client/conversion/service.py client/conversion/text/pipeline.py client/tests/test_conversion_language_explicit.py client/tests/test_conversion_service.py client/tests/test_conversion_text_pipeline.py client/tests/test_translation_import_isolation.py client/tests/test_translation_language_result.py
git -C $REPO commit -F - <<'MSG'
refactor: thread conversion language through service and pipeline

convert_text_with_alignment passes request.lang and request.charset_maps
to the service functions, which forward them to the text pipeline and,
as language, to the math translator. The temporary config reads in
conversion.service and conversion.text.pipeline are gone, so no module
below the UI reads the conversion language from config.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 8: Final verification (spec acceptance criteria, no commit)

Run from `$REPO` unless the command changes directory.

- [ ] **AC1: no `config` import in the four cleaned modules.**

```bash
cd $REPO && grep -nE '^[[:space:]]*(import config\b|from config import)' client/conversion/text/pipeline.py client/languageDetection/__init__.py client/conversion/mathcat_adapter.py client/braille/tables/__init__.py; echo "exit=$?"
```

Expected: only `exit=1` (no match).

- [ ] **AC2: the only production reads.**

```bash
cd $REPO && grep -rnE 'get_lang|get_charset_maps' client --include=*.py | grep -v '^client/tests/'
```

Expected, exactly these 11 lines (the file order follows the directory listing and may differ):

```
client/client_init.py:14:from config import get_lang, get_or_create_client_id
client/client_init.py:149:    locale_provider=get_lang,
client/config.py:140:def get_lang() -> str:
client/config.py:151:def get_charset_maps() -> dict[str, str]:
client/gui.py:60:	get_charset_maps,
client/gui.py:61:	get_lang,
client/gui.py:707:			lang=get_lang(),
client/gui.py:708:			charset_maps=get_charset_maps(),
client/main.py:5:from config import DEFAULT_TRANSLATION_TABLES, get_charset_maps, get_lang
client/main.py:30:                lang=get_lang(),
client/main.py:31:                charset_maps=get_charset_maps(),
```

- [ ] **AC3: no test patches the old globals.**

```bash
cd $REPO && grep -rnE 'languageDetection\.config|pipeline\.config|config\.set_lang' client/tests; echo "exit=$?"
```

Expected: only `exit=1`.

- [ ] **AC4 and AC7: vendored files and locales untouched; the change set is the 31 listed files.**

```bash
cd $REPO && git diff main --stat -- client/braille/tables/__tables.py client/braille/liblouis client/locales; echo "---"
git -C $REPO diff main --stat -- client | tail -1
$PY -I $T/tools/msgid_scan.py $REPO/client --compare $T/baseline_msgids.json
```

Expected: nothing before `---`; `31 files changed, 565 insertions(+), 96 deletions(-)`; `source msgids: 357`, `pot msgids: 357`, `SOURCE == POT`, `SOURCE == SAVED`.

- [ ] **AC5: focused verification (Linux form of the roadmap command).**

```bash
cd $REPO/client && $PY -m unittest tests.test_conversion_text_pipeline tests.test_language_detection_char_langinfo tests.test_language_detection_unicode_braille tests.test_mathcat_adapter tests.test_conversion_service tests.test_translation_import_isolation tests.test_math_service tests.test_math_translation_adapter tests.test_translation_fallback tests.test_conversion_jobs tests.test_translation_runtime_provider tests.test_conversion_language_explicit tests.test_braille_tables_default_lang tests.test_main_demo tests.test_gui_document_flows -v 2>&1 | grep -E '^(FAIL|ERROR):|^Ran|^FAILED|^OK' | sed -E 's/ in [0-9.]+s$//'
$PY -m unittest tests.test_math_braille_codes 2>&1 | tail -1
```

Expected: the P2-5 `FAIL:` line, `Ran 158 tests`, `FAILED (failures=1)`; then `OK` (the Task 2 module, not in the spec's list).

- [ ] **AC6: full suite, plus order and hash robustness.**

```bash
cd $REPO/client && $T/tools/check_suite.sh 575 22
for h in 0 5; do PYTHONHASHSEED=$h $PY -m unittest discover -s tests 2>&1 | tail -1; done
for s in 1 2 3 4 5 6 7 8 9 10; do $PY -I $T/tools/shuffle_harness.py $s | grep -v '^order=' | grep -v 'test_conversion_service.ConversionServiceTest'; done
$PY -m py_compile tests/test_language_detection_translation.py tests/test_translation_language_result.py && echo COMPILED
```

Expected: the Task 7 suite-check output; `FAILED (failures=1, skipped=7)` twice; ten `seed=<n> ran=575 ...` lines and no `BAD` line (each seed shows either `failures=1 errors=0` or `failures=0 errors=8`; the hidden `BAD` lines are the P2-5 case and the 8 pre-existing `test_conversion_service` order errors of refinement 8); `COMPILED`.

- [ ] **AC8: Windows-only verification debt (cannot run on this Linux host; report it, do not claim it).**
  - `python -m unittest tests.test_conversion_text_pipeline tests.test_language_detection_char_langinfo tests.test_language_detection_translation tests.test_language_detection_unicode_braille tests.test_mathcat_adapter tests.test_conversion_service tests.test_translation_import_isolation -v`, plus `tests.test_translation_language_result`, `tests.test_liblouis_runtime` and `tests.test_translation_runtime_provider`.
  - The real MathCAT path (`libmathcat_py.pyd`): `Language` preference per call.
  - Manual: convert mixed Chinese/English/math text in the app and compare the braille with a build from `main`, once with `TEXT2BRAILLE_LANG` unset and once with `TEXT2BRAILLE_LANG=en`.

- [ ] **Final state.**

```bash
git -C $REPO status --short
git -C $REPO log --oneline main..HEAD
```

Expected: clean; 9 commits: the spec and plan commits, then the 7 commits of Tasks 1-7 in order.

---

## Appendix: `$T/tools/check_suite.sh`

```bash
#!/bin/bash
# Throwaway (P1-1). usage: check_suite.sh <expected Ran> <expected new-test ok>   (run from client/)
# Every baseline test line must still be present with the same result, except the one test that
# Task 5 renames (test_charset_map_is_loaded_from_config). "new tests ok" counts passing test lines
# that are not in the baseline (new tests and renamed tests).
SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
T=${T:-$SP/p11impl}
PY=$SP/venv/bin/python
RENAMED='test_charset_map_is_loaded_from_config'
$PY -m unittest discover -s tests -v > $T/run.txt 2>&1
grep ' \.\.\. ' $T/run.txt | sort > $T/run_lines.txt
grep -E '^Ran|^FAILED|^OK' $T/run.txt | sed -E 's/ in [0-9.]+s$//'
grep -E '^(FAIL|ERROR):' $T/run.txt
missing=$(comm -23 <(grep -v "$RENAMED" $T/baseline_discover_verbose.txt) $T/run_lines.txt)
[ -z "$missing" ] && echo "BASELINE-TESTS-IDENTICAL" || { echo "BASELINE-TESTS-CHANGED:"; echo "$missing"; }
grep -q "^Ran $1 tests" $T/run.txt && echo "RAN-COUNT-OK ($1)" || echo "RAN-COUNT-MISMATCH (expected $1)"
echo "new tests ok: $(comm -13 $T/baseline_discover_verbose.txt $T/run_lines.txt | grep -c '\.\.\. ok$') (expected $2)"
```
