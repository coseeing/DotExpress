# Translation Result Layout (P1-5) Design

## Goal

Make the alignment value object and the dual-view handoff cheap and acyclic, without changing any output. This is roadmap task P1-5 in `storage/refactor.md` (section 6.2), covering:

- S-2 (first and third bullets) and section 5.6: `TranslationResult.__init__` rebuilds 12 punctuation sets and the CJK language-block table for every instance, and `conversion/wrapping.merge_translation_results` is O(n^2).
- D-3 (the part P1-5 owns): the function-local `from translate import TranslationResult` in `conversion/wrapping.py` and `conversion/preprocessing/literal_braille.py`.
- D-4: the `conversion <-> dual_view` dependency loop (`conversion/service.py` imports `DualViewSegment` from `dual_view.model`, which imports `conversion.math_service`).
- L-1: `TranslationResult.__eq__` raises `AttributeError` for a non-`TranslationResult` operand.
- M-1 from the P0 phase review: `tests/test_translation_result_core.py` re-imports `translate`, so 8 `tests/test_conversion_service.py` tests error whenever it runs first.

Concretely:

- The punctuation sets and the CJK language blocks become immutable class attributes of `TranslationResult` (built once at import). An instance holds only its four data fields.
- `TranslationResult.concat(results)` merges any number of results in one pass. `merge_translation_results` and `TranslationResult.__add__` both use it.
- `DualViewSegment` moves to `conversion/output.py`, next to `ConversionOutput`. `conversion` no longer imports `dual_view`.
- `build_dual_view_model(segments, *, mathml_converter)` takes the converter as a required keyword argument. `gui.py` and `documents/formats.py` pass `conversion.math_service.latex_to_mathml`. `dual_view` no longer imports `conversion` (or `config`) at runtime.
- `TranslationResult.__eq__` returns `NotImplemented` for other types and the class sets `__hash__ = None` explicitly.
- The import-isolation check in `tests/test_translation_result_core.py` runs in a subprocess, so `translate` is never popped from `sys.modules`. After this task, no shuffled full-suite order shows an order-dependent failure.

This is a behavior-preserving refactor. For any input, the braille text, the source-text wrap, the token alignment and the dual-view model and HTML are byte-identical to `main` at `7095265`. No user-facing string changes.

This spec includes the corrections and refinements from the implementation plan (`docs/superpowers/plans/2026-10-08-p1-5-translation-result-layout.md`, section "Spec Corrections and Refinements"): the scale backstop merges 20,000 ten-token results, because with one-token results the old loop takes only 11.5 s and barely misses the 5 s bound; the module-level imports of `translate` do change the standalone import closures of `conversion.wrapping` and `conversion.preprocessing.literal_braille` (no production closure changes); the golden fixture stores the width-independent snapshot once per input and the long document as digests; the fixture is regenerated with `python -m tests.test_translation_golden --write`; the test classes, the A3 test and the guards have fixed names and scope; every step has a red test or, for step 2, a mutation check; and the text-only converter helper is `reject_mathml`.

Not in this task (P2-5): splitting the tokenizer (`bind_word_tokens`) and the line wrapper (`wrap`) out of `TranslationResult`, moving `TranslationResult` to `conversion/alignment.py`, and the known failing test `test_translate_with_language_does_not_duplicate_existing_spaces_around_math`.

## Current State (verified 2026-10-08 on `refactor/p1-5-translation-result-layout`, HEAD `7095265`, P0-1..P0-6 and P1-1..P1-4 merged)

Indentation: `translate.py`, `gui.py` and `dual_view/model.py` (except the `DualViewSegment` class, which uses 4 spaces) use tabs. `conversion/wrapping.py`, `conversion/output.py`, `conversion/service.py`, `conversion/preprocessing/literal_braille.py`, `documents/formats.py` and `dual_view/__init__.py` use 4 spaces. Tests: `test_translation_result.py`, `test_dual_view_model.py` and `test_dual_view_html.py` use tabs; the others touched here use 4 spaces.

### `TranslationResult` (`client/translate.py`, 527 lines)

- `__init__` (lines 11-32) stores `raw`, `braille`, `braille_to_raw_pos`, `raw_to_braille_pos`, then builds 12 `set` attributes (`LEFT_PUNCT_HALF` ... `END_SENTENCE_PUNCT`) and `self.lang_blocks = build_language_blocks({"ja", "zh", "ko"})` (a `dict[str, list[str]]`). About 6 microseconds per instance; every adapter call, every merge step and every literal-braille segment creates one.
- The sets are only read: `bind_word_tokens` (lines 142, 144, and `getattr(self, "lang_blocks", None)` at line 127), `reclean_token` (line 376) and `wrap` (line 499). Nothing outside `translate.py` reads them (`grep -rn "PUNCT\|lang_blocks" client --include=*.py`). Nothing pickles, copies or inspects `vars()` of a result.
- `__add__` (lines 34-52) raises `TypeError("not TranslateResult object")` for a non-`TranslationResult` operand and returns a new result whose four lists are fresh (never aliases either operand).
- `__eq__` (lines 54-60) reads `other.raw` and friends directly. With any other type it raises `AttributeError`. A probe over the full suite shows no test ever calls it.
- `reclean_braille_endspace` mutates `braille`, `braille_to_raw_pos` and `raw_to_braille_pos` in place (`del`, item assignment).

### Merge (`client/conversion/wrapping.py`, 17 lines)

```python
def merge_translation_results(translations):
    from translate import TranslationResult
    if not translations:
        return TranslationResult([], [], [], [])
    merged = TranslationResult([], [], [], [])
    for segment in translations:
        merged = merged + segment
    return merged
```

Each step copies everything merged so far and builds a new instance. Measured on this box with 10-token segments: 1,000 segments 0.18 s, 2,000 0.70 s, 4,000 3.2 s, 8,000 15.3 s. After merging, the rest of `wrap_translation_results` (`reclean_braille_endspace`, `bind_word_tokens`, `reclean_token`, `wrap`) takes about 0.3 s for 8,000 segments, so for this input shape the merge is the dominant cost. (`reclean_braille_endspace` has its own quadratic case when many tokens end in blank cells; see known defect 3.) A segment is produced per language switch, dictionary bracket, literal-braille entry, math block and boundary space, so a long imported PDF/EPUB reaches thousands of segments.

`wrap_translation_results` mutates the merged result (`reclean_braille_endspace`). Because the merge copies, the per-segment results stay untouched, and those same objects are kept as the document's dual-view cache (`ConversionOutput.dual_view_segments`). The new merge must keep that guarantee.

Callers: `wrap_translation_results` (same file) and `conversion/service.translate_with_language` (line 110). The Windows-only `tests/test_language_detection_translation.py` merges with `+`.

### Function-local imports of `translate`

`conversion/wrapping.py:2` and `conversion/preprocessing/literal_braille.py:6`. They date from when `translate.py` loaded the native liblouis helper (commit `c6474cb`). Today `translate.py` imports only `string` and `languageDetection.unicode_blocks`, and `adapters/translation/contracts.py:6` already imports it at module level; `conversion.text.pipeline` imports `contracts`, so `translate` is already loaded whenever these modules run. There is no cycle; the local imports are vestigial.

The function-local imports in `conversion/text/pipeline.py:58-59` (`text.zhuyin`, `languageDetection`) are not caused by a cycle either, but they are not about `TranslationResult` or `dual_view`. They stay (pipeline belongs to P1-6).

### Dual-view model (`client/dual_view/model.py`, 90 lines)

- Line 4: `from conversion.math_service import latex_to_mathml` (which imports `config` and `log`).
- Lines 7-10: `DualViewSegment(result: object, source_kind: str)`, a frozen dataclass.
- Line 44: `build_dual_view_model(segments, *, mathml_converter=latex_to_mathml)`. The converter is called once per raw token of a `"math"` segment; never for text.
- `dual_view/__init__.py` re-exports `DualViewSegment`. No production code imports it from the package; every user imports `dual_view.model`.

Who uses what:

| Symbol | Production | Tests |
| --- | --- | --- |
| `DualViewSegment` | `conversion/service.py:18` (constructed at lines 50, 63, 65, 72; annotation at 35, 129) | `test_conversion_service.py`, `test_document_formats.py`, `test_gui_document_flows.py`, `test_dual_view_model.py`, `test_dual_view_html.py` (all `from dual_view.model import DualViewSegment`) |
| `build_dual_view_model` | `gui.py:332` (`_render_dual_view_for_open_document`), `documents/formats.py:106` (`_write_html`, reached through `ExportCoordinator`) | 20 calls without a converter (`test_dual_view_model.py`, `test_dual_view_html.py`, `test_gui_document_flows.py` lines 1364, 1369, 1398, 1402), 2 with a fake converter (`test_dual_view_html.py`) |

Import closure today: `import conversion.service` loads `dual_view`, `dual_view.html` and `dual_view.model`; `import dual_view` loads `conversion`, `conversion.math_service`, `conversion.math_braille_codes`, `config`, `log` and `app_paths`. `import documents.formats` gets `conversion.math_service` through `dual_view.model`.

### M-1: the test-order failure

`TranslationResultCoreTest.test_import_does_not_import_liblouis_helper` does `sys.modules.pop("translate")` and re-imports it. That creates a second `TranslationResult` class. Results built by modules imported earlier (`adapters.translation.*`, the test module's own `FakeTextTranslator`) use the old class, while `conversion.wrapping` imports the class at call time and gets the new one. `merged + segment` then fails the `isinstance` check: `TypeError: not TranslateResult object`.

- Reproduce: `cd client && python -m unittest tests.test_translation_result_core tests.test_conversion_service` gives 23 tests, `errors=8` (the 8 tests that merge, including the P2-5 test, which then errors instead of failing).
- Shuffled full suite (module-order harness used since P0-4, seeds 0-19, 754 tests): seeds 0, 1, 3, 4, 5, 10, 12, 13 show `failures=0 errors=8`; the other 12 show `failures=1 errors=0` (P2-5 only). Every failing seed runs `test_translation_result_core` before `test_conversion_service`; no other module is involved.
- P1-1 worked around it in `tests/test_conversion_language_explicit.py` (fakes import `TranslationResult` per call, with a comment explaining why). `tests/test_conversion_service.py` still has three dead helpers built for a `sys.modules["translate"]` swap that no test uses any more: `_fake_translate_module`, `_mutating_translate_module`, `_translation_result`.

### The roadmap's safety net is weaker than it looks

- `tests/test_translation_result.py` (13 tests of `bind_contracted_tokens`, `bind_word_tokens` and `wrap`) is written as pytest-style module functions. `unittest` collects none of them (`python -m unittest tests.test_translation_result` prints `NO TESTS RAN`), and pytest is not a project dependency. Called directly, 8 pass and 5 fail today (`test_bind_word_tokens_lead_punct` and `..._lead_punct_continue` raise `IndexError`; `test_end_right_end_sentence_blank2`, `..._blank3` and `test_remove_start_line_blank` fail their asserts). They are about the tokenizer and wrapper, so they belong to P2-5.
- `tests/test_translation_language_result.py` and `tests/test_language_detection_translation.py` are Windows-only and skip here. The second imports `translate.translate`, which no longer exists, so it errors on Windows (pre-existing; P1-1 recorded the first one's `TypeError`).
- So nothing currently executed pins the merged braille, the wrap, or the alignment for realistic mixed input. This task adds that net first.

### Baseline

Full suite at `7095265` (Linux venv, alphabetical order): 754 tests, `failures=1` (P2-5), `errors=0`, `skipped=9`.

## Design

### `TranslationResult` constants (`translate.py`)

Move the 12 sets to class attributes with the same names and members, as `frozenset`s. Build the language blocks once at module level and expose them as a read-only class attribute:

```python
_CJK_LANGUAGE_BLOCKS = MappingProxyType({
	language: tuple(blocks)
	for language, blocks in build_language_blocks(("ja", "zh", "ko")).items()
})

class TranslationResult:
	LEFT_PUNCT_HALF = frozenset("([{")
	...
	END_SENTENCE_PUNCT = END_SENTENCE_PUNCT_HALF | END_SENTENCE_PUNCT_FULL
	lang_blocks = _CJK_LANGUAGE_BLOCKS
	__hash__ = None

	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
		self.raw = raw
		...
```

- Every existing read (`self.RIGHT_PUNCT`, `self.LEFT_PUNCT`, `set(self.LEFT_PUNCT) | set("—")`, `self.RIGHT_PUNCT_FULL | self.END_SENTENCE_PUNCT_FULL`, `getattr(self, "lang_blocks", None)`) works unchanged through the class attribute, and membership and union results are equal. The method bodies of `bind_contracted_tokens`, `bind_word_tokens`, `insert_token`, `reclean_token`, `reclean_braille_endspace` and `wrap` are not edited.
- Immutable types, because the values are now shared by every instance. `language_has_all` only calls `.get(lang, [])` and wraps the value in `set(...)`, so a mapping proxy of tuples behaves exactly like the dict of lists. The dict's key order depends on set iteration, but it is only looked up by key.
- The per-call sets inside `bind_word_tokens` (`ASCII_ALNUM`, `TRAIL_PUNCT`, `LEAD_PUNCT`) and the per-token union and `set(" ")` in `wrap` stay as they are: they are inside the tokenizer and wrapper bodies that P2-5 rewrites.

### Equality (L-1)

```python
def __eq__(self, other):
	if not isinstance(other, TranslationResult):
		return NotImplemented
	... unchanged comparisons ...
```

Comparing with another type now gives `False` (and `!=` gives `True`) instead of `AttributeError`. Equal results still compare equal; `__hash__ = None` states what Python already did implicitly.

### Linear merge

Add a class method on `TranslationResult` and route both merge paths through it:

```python
@classmethod
def concat(cls, results):
	raw, braille, braille_to_raw_pos, raw_to_braille_pos = [], [], [], []
	for result in results:
		if not isinstance(result, TranslationResult):
			raise TypeError("not TranslateResult object")
		raw_offset = len(raw)
		braille_offset = len(braille)
		raw.extend(result.raw)
		braille.extend(result.braille)
		braille_to_raw_pos.extend(pos + raw_offset for pos in result.braille_to_raw_pos)
		raw_to_braille_pos.extend(pos + braille_offset for pos in result.raw_to_braille_pos)
	return cls(raw, braille, braille_to_raw_pos, raw_to_braille_pos)
```

- `__add__` keeps its `TypeError` for a non-result operand and becomes `return TranslationResult.concat((self, other))`.
- `conversion/wrapping.py` imports `TranslationResult` at module level and `merge_translation_results(translations)` becomes `return TranslationResult.concat(translations or ())`. The `None`/empty case still returns an empty result. The function stays as the public name its callers use.
- Same arithmetic as the pairwise loop (the offset is the length of everything merged before the segment), so every list is element-for-element equal. One instance is built, each element is copied once: O(total length).
- The result owns four new lists, even for zero or one input, so `reclean_braille_endspace` on the merged result cannot touch a cached dual-view segment.
- Accepted widening: `list + x` required `raw` and `braille` to be lists, while `extend` accepts any iterable. Every producer (liblouis, MathCAT and fallback adapters, literal braille, test fakes) builds lists, so no reachable input changes.

`conversion/preprocessing/literal_braille.py` also imports `TranslationResult` at module level. No production import closure changes: every production path that reaches these two modules (`conversion.service`, `conversion.text.pipeline`, the adapters) already loads `translate` through `adapters.translation.contracts`, and `test_platform_neutral_modules_do_not_load_native_modules` stays green. The standalone closures do change (measured): `import conversion.wrapping` and `import conversion.preprocessing.literal_braille`, each alone in a fresh interpreter, now also load `translate`, `languageDetection`, `languageDetection.blocks` and `languageDetection.unicode_blocks` (all pure Python, no native code). Also measured after step 6: `import conversion.service` stops loading `conversion.math_service` (it came in through `dual_view.model`); nothing relies on that, because `adapters.translation.provider` imports it lazily and, after step 7, `gui` and `documents.formats` import it directly. `import documents.formats` loads exactly the same modules before and after.

### `DualViewSegment` moves to `conversion/output.py` (D-4)

- Define `DualViewSegment` (same fields, same `frozen=True`, `result: object`) in `conversion/output.py` above `ConversionOutput`, and annotate `ConversionOutput.dual_view_segments: tuple[DualViewSegment, ...] = ()`. No new import in `output.py`, so `test_language_consumers_do_not_import_config` stays green.
- `conversion/service.py` imports it from `conversion.output` and drops `from dual_view.model import DualViewSegment`.
- `dual_view/model.py` deletes the class, adds `from __future__ import annotations`, and imports `DualViewSegment` only under `if TYPE_CHECKING:` for the `Iterable[DualViewSegment]` annotation. `dual_view/__init__.py` drops `DualViewSegment` from its import and `__all__`.
- No compatibility alias in `dual_view.model`: an alias needs a runtime import, which is the dependency this removes. All five test modules switch to `from conversion.output import DualViewSegment` in the same commit.
- `conversion/output.py` is not a leaf module (it imports the adapter contracts and the text pipeline), but `dual_view` only references it for type checking, and `conversion.service` already imports it. A separate leaf module was considered and rejected: one more file for no runtime gain, against the roadmap's explicit target.

Direction afterwards: `conversion` produces `DualViewSegment`; `dual_view` consumes it structurally (it reads only `.result.raw`, `.result.braille`, `.result.raw_to_braille_pos` and `.source_kind`); `gui` and `documents` wire the two together.

### Required `mathml_converter` (D-4)

```python
def build_dual_view_model(
	segments: Iterable[DualViewSegment],
	*,
	mathml_converter: Callable[[str], str],
) -> DualViewModel:
```

- Required and keyword-only, no default and no `None`: a default is the hidden dependency being removed, and `None` would only move the failure to the first math token.
- `dual_view/model.py` drops `from conversion.math_service import latex_to_mathml`. Importing `dual_view` no longer loads `conversion`, `config`, `log` or `app_paths`.
- `gui.py`: `from conversion.math_service import latex_to_mathml` at module level; `_render_dual_view_for_open_document` calls `build_dual_view_model(results, mathml_converter=latex_to_mathml)`.
- `documents/formats.py`: same import at module level; `_write_html` passes it. `documents.formats` already loads `conversion.math_service` today (through `dual_view.model`), so its import closure is unchanged. `ExportContext` does not change: carrying the converter on the context would spread one wiring decision over `ExportCoordinator`, `formats` and their tests for no benefit.
- Behavior is identical: both callers used the default `latex_to_mathml` before.

### M-1: test isolation

- `tests/test_translation_result_core.py`: `test_import_does_not_import_liblouis_helper` runs its check in a fresh interpreter with `subprocess.run([sys.executable, "-c", script], ...)`, the pattern `tests/test_translation_import_isolation.py` already uses. The script imports `translate` and asserts that `braille.louis_helper` and `braille.liblouis` are not loaded, that `TranslationResult` exists, and that `translate` and `translate_as_single_token` do not. The test no longer touches `sys.modules`. A fresh interpreter is also the more honest check: the in-process version could only pop what other tests had loaded.
- `tests/test_conversion_language_explicit.py`: the two fakes import `TranslationResult` at module level and the workaround comment goes away. This is the regression proof that the pollution is gone.
- `tests/test_conversion_service.py`: delete the three dead helpers and the then-unused `ModuleType` import. They model a `sys.modules["translate"]` swap that the module-level import in `wrapping` makes meaningless.
- With the re-import gone and `wrapping` binding the class at import time, there is one `TranslationResult` class per process. No other test pops or reloads `translate` (`grep -rn "sys.modules.pop\|importlib.reload" client/tests`; `StubScope` users do not import `translate` inside a scope).

### Migration steps (each step is one green commit; the plan details them)

1. `test: run the translate import check in a subprocess` (M-1, plus the explicit-language fakes and the dead helpers). Red first: the explicit-language fakes switch to a module-level import of `TranslationResult`, and with the old core test run first they error (`TypeError: not TranslateResult object`), which is the M-1 pollution itself; the subprocess rewrite turns them green. The 20-seed shuffle becomes clean except P2-5.
2. `test: characterize translation and dual-view output` (all of part A of the test plan, including the golden fixture generated on unchanged production code). Characterization cannot be red; instead a throwaway mutation script shows the golden tests catch three deliberate in-memory breakages (`reclean_token` a no-op: 6 failures; `bind_contracted_tokens` a no-op: 16; the wrap merging into the first cached segment: 26).
3. `refactor: share TranslationResult constants` (constants and `__hash__`; part B tests).
4. `fix: compare TranslationResult only with results` (L-1; part C test).
5. `refactor: merge translation results in one pass` (`concat`, `__add__`, both module-level imports; part D tests). The red step runs only the two structural tests; the old code needs minutes for the scale test.
6. `refactor: move DualViewSegment to conversion output` (part E guard for `conversion`).
7. `refactor: inject the MathML converter into the dual-view model` (part E guard for `dual_view`, the required-converter test). The 20 test call-site updates go into the red step (the keyword is already accepted), so the green step touches production files only.

The golden fixture is written once in step 2 and must not change afterwards (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`).

## What Stays Identical

- Braille output (Unicode and ASCII), the source-text wrap, the merged alignment lists, the post-processing alignment, every dual-view segment and the dual-view HTML (window and export) for any input and width.
- `merge_translation_results`, `wrap_translation_results`, `translate_with_language*` and `convert_text_with_alignment` signatures and return types.
- The `TypeError("not TranslateResult object")` for merging a non-result.
- `TranslationResult` attribute names; method bodies other than `__init__`, `__add__` and `__eq__`.
- `ExportContext`, `ExportCoordinator`, `DocumentController` and the conversion presenter.
- No string, menu, dialog, `.po`/`.mo` or packaging change.

## Test Plan

All new tests are `unittest`. Golden expectations are captured from unchanged production code (step 2) and never regenerated in later steps.

### A. Characterization (step 2, before any production change)

1. **Golden output** (`tests/test_translation_golden.py`, new, 4 spaces; fixture `tests/fixtures/translation_golden.json`):
   - Runtime: the real `LiblouisTextTranslator` with a deterministic fake helper (its `translate(tables, text, mode=4)` returns cells, `braille_to_raw` and `raw_to_braille` the way liblouis does). The fake gives ASCII letters one cell, digits two (number sign), CJK characters three plus one trailing blank cell at the end of a CJK run (so `reclean_braille_endspace` trims), other symbols one or two cells, and, for tables whose name contains `en`, maps `the`/`and`/`ing` to one cell (so `bind_contracted_tokens` merges). Math uses the real `MathCATMathTranslator` with a deterministic fake `translate_math`. This exercises the adapters, the pipeline, language switches, boundary spaces, literal braille, the merge, the token binding and the wrap without native code.
   - Data: the real `client/data` CSVs (character maps, Bopomofo, Braille-to-ASCII); a temporary dictionary with one `Braille/Unicode` row (`台灣` -> `⠞⠺`); `translation_tables = {"default": "zh-tw.ctb", "en": "en-ueb-g2.ctb", "zh": "zh-tw.ctb", "math": "Nemeth"}`; `lang="zh_TW"`; `charset_maps=DEFAULT_CHARSET_MAPS`.
   - Inputs (at least): Chinese prose with an embedded English word and full-width punctuation; English with inline math, a comma right after math and a Chinese word; text with inline math between spaces (the P2-5 shape, pinned as it behaves today), a hard newline, adjacent `）（` and `」『` pairs (so `reclean_token` inserts a space); an escaped dollar, a fraction, math with no surrounding spaces, `Testing, (one) [two]!`; the dictionary literal with blank lines and leading spaces; and one long document of at least 300 segments built from the others.
   - Each short input at widths 1, 10, 24 and 40 in `unicode` mode and at width 24 in `ascii` mode; the long document (the five short inputs joined by blank lines, 12 times: 360 segments) at width 40.
   - Snapshot per run: `display_text` and `wrap_translation_results(...)` (both strings). Snapshot per input, stored once under `conversion` because it does not depend on the width or the output mode, and recomputed and compared on every run (so the "read after the wrap" check runs at every width): the merged result's four lists; the four lists after `reclean_braille_endspace`, `bind_word_tokens` and `reclean_token`; `translate_with_language(...)`'s four lists; every dual-view segment's `source_kind` and four lists (read after the wrap and the post-processing, which proves they did not mutate them); `dataclasses.asdict` of `build_dual_view_model(..., mathml_converter=<deterministic fake>)`; and the SHA-256 of `render_dual_view_html` of that model. The long document stores its per-input parts as SHA-256 digests of their canonical JSON plus `dual_view_segment_count` (in full it alone would be about 1 MB). A fake converter keeps the fixture independent of the `latex2mathml` version; the real converter is pinned by A3. `test_fixture_covers_every_input` pins the case list and the 300-segment minimum.
   - The fixture is JSON with `ensure_ascii=False`, sorted keys and indentation, so a diff is readable: 189,305 bytes, 6,652 lines, sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`, identical under `PYTHONHASHSEED` 0-3. `python -m tests.test_translation_golden --write` (from `client/`) rewrites it, run once in step 2; without `--write` the module runs its tests like every other test module. The module docstring says the fixture must only be regenerated for an intended output change.
2. **Merge semantics** (`tests/test_translation_result_core.py`, class `MergeTranslationResultsTest`, plus one test in `TranslationResultCoreTest`): merging `[]` and `None` gives four empty lists; merging one result gives an equal result whose lists are not the input's lists; mutating the merged lists (or calling `reclean_braille_endspace` on it) leaves every input unchanged; merging three hand-built results gives the expected offsets; a non-result item raises `TypeError` with the existing message; `a + b` gives the same four lists as today, aliases neither operand, and keeps its `TypeError`.
3. **Real MathML wiring**: one test, `test_dual_view_and_html_export_render_math_with_real_mathml` in `DocumentMenuAndExportCharacterizationTest` next to the existing export byte tests. In `tests/test_gui_document_flows.py`, the frame's `_render_dual_view_for_open_document()` for cached results with a math segment (`x^2`) equals `render_dual_view_html(build_dual_view_model(results, mathml_converter=latex_to_mathml), empty_message=...)` and contains `latex_to_mathml("x^2")`; the HTML export of the same results through `ExportCoordinator.write_document(..., "html")` writes exactly those bytes. With non-empty results the `empty_message` does not appear, so the window and the export render the same bytes and are checked against the same expected string. (`build_dual_view_model` already accepts the keyword, so this test passes before and after.)
4. **Constant values** (`tests/test_translation_result_core.py`, `TranslationResultCoreTest`): a result's 12 punctuation attributes equal the literal sets of today (full-width members written as `\u` escapes), and `{k: list(v) for k, v in result.lang_blocks.items()} == build_language_blocks({"ja", "zh", "ko"})`.

### B. Shared constants (step 3, class `SharedConstantsTest`)

- `vars(TranslationResult([], [], [], []))` has exactly the four data keys.
- Constructing a result does not call `translate.build_language_blocks` (patched with a `Mock`).
- The 12 attributes are `frozenset`s and `lang_blocks` cannot be assigned into (`TypeError`).

### C. Equality (step 4, class `EqualityTest`)

`result == object()` is `False`, `result != "x"` is `True`, `result.__eq__(42) is NotImplemented`, two equal results compare equal, and `hash(result)` raises `TypeError`.

### D. Linear merge guards (step 5, class `LinearMergeTest`)

- **Structural (primary, deterministic):** merging 500 results constructs exactly one `TranslationResult`, which is the returned one (count `__init__` calls through a wrapper), and never calls `__add__` (patched with `side_effect=AssertionError`). The pairwise loop builds 501 instances and calls `__add__` 500 times, so this fails on the old code without any timing.
- **Scale backstop:** merging 20,000 ten-token results (200,000 tokens, the shape of the 8,000-segment measurement above) equals a reference built with plain offset arithmetic and finishes within 5 s (`time.perf_counter`). Measured on this box: the new merge 0.06 s, the old pairwise loop 162 s (8,000 ten-token segments: 22.1 s). The bound is about 80 times the new time, and the old code needs more than 30 times the bound. One-token results would not separate them: the old loop merges 20,000 of those in 11.5 s, so a machine 2.5 times faster would let it pass.

### E. Dependency guards (steps 6 and 7, `tests/test_translation_import_isolation.py`, subprocess like the existing tests)

- `test_conversion_does_not_import_dual_view`: `import conversion.service, conversion.output, conversion.wrapping` loads no `dual_view` or `dual_view.*` module (the guard reports every one it finds).
- `test_dual_view_does_not_import_conversion_or_config`: `import dual_view, dual_view.model, dual_view.html` loads no `conversion` or `conversion.*` module and not `config`.
- `test_mathml_converter_is_required`: `build_dual_view_model([])` without `mathml_converter` raises a `TypeError` whose message matches `mathml_converter` (`tests/test_dual_view_model.py`).

### F. Updated tests

- Five modules switch the `DualViewSegment` import to `conversion.output`.
- The 20 converter-less `build_dual_view_model` calls pass a converter. Text-only tests (13 in `test_dual_view_model.py`, 3 in `test_dual_view_html.py`) pass `reject_mathml`, a module function in each of those two files that raises `AssertionError` (the converter must not be called for text); the four `test_gui_document_flows.py` export comparisons pass `latex_to_mathml`, matching production wiring.
- `tests/test_translation_result.py` is not converted or fixed here (P2-5). As a manual check, calling its 13 functions directly gives the same 8 passes and the same 5 failures (same exception types) before and after the change.

## Acceptance Criteria

1. Roadmap verification passes on Linux: `cd client && python -m unittest tests.test_translation_result tests.test_translation_result_core tests.test_dual_view_model tests.test_dual_view_html tests.test_conversion_service -v` (`test_translation_result` contributes 0 tests, see above; only the P2-5 failure remains). Also `tests.test_translation_golden tests.test_translation_import_isolation tests.test_conversion_language_explicit tests.test_document_formats tests.test_gui_document_flows tests.test_export_coordinator tests.test_conversion_text_pipeline`.
2. `git diff <step-2 commit> HEAD -- client/tests/fixtures/translation_golden.json` is empty, and `tests.test_translation_golden` passes at every later commit.
3. `python -m unittest tests.test_translation_result_core tests.test_conversion_service` reports only the P2-5 failure (no errors), and so does the reverse order.
4. Full suite (alphabetical): 754 + 29 new tests = 783, `failures=1` (P2-5 only), `errors=0`, `skipped=9`.
5. Shuffled full suite, seeds 0-19 (module order shuffled with `random.Random(seed)`, one process, `unittest.TextTestRunner`; the harness used since P0-4): every seed runs the same 783 tests with `failures=1 errors=0`, and the only failing test is `test_translate_with_language_does_not_duplicate_existing_spaces_around_math`.
6. `grep -rnE "(from|import) dual_view" client/conversion` prints nothing, and `grep -rnE "(from|import) conversion" client/dual_view` prints only the `TYPE_CHECKING` import in `dual_view/model.py`. The subprocess guards in part E are the binding check.
7. `grep -rn "^\s\+from translate import" client --include=*.py | grep -v tests/` prints nothing.
8. `grep -n "self\.\(LEFT\|RIGHT\|MIDDLE\|END\)_[A-Z_]* = \|self.lang_blocks = " client/translate.py` prints nothing.
9. `git diff main --stat -- client/locales scripts client/braille` is empty; no user-facing string changed.

## Risks

- **Hidden output drift** (high impact, low likelihood). Mitigation: the golden fixture from unchanged code over realistic mixed input at several widths, with the dual-view segments read after the wrap; the fixture must stay byte-identical across steps 3-7.
- **Aliasing in the new merge** (medium impact, low likelihood). If `concat` returned an input's list (for example a one-segment shortcut), `reclean_braille_endspace` would corrupt the dual-view cache. Mitigation: A2 tests the zero- and one-input cases and the mutation case; no shortcut is allowed.
- **Shared mutable constants** (low). Frozensets and a read-only mapping make accidental mutation raise instead of leaking across instances.
- **Equality change** (low). Comparing a result with another type no longer raises. No caller relies on the exception (suite probe).
- **Stub-scope eviction** (low). `test_dialog_display` loads `dialog.py` with `evict_everything`, which evicts `documents.formats` and, after step 7, the `conversion.math_service` it imports directly (before, through `dual_view.model`). Re-importing those creates new module objects but no class that crosses an `isinstance` check. Criterion 5 covers it.
- **Timing backstop flakiness** (low). The 5 s bound is about 80 times the new merge time; the structural tests are the real guard.
- **Windows-only paths** (medium, unverifiable here). The liblouis adapter now builds results whose constants are class attributes and whose merge is linear; output must match. See the verification debt.

## Known defects found during this investigation (not fixed here)

1. `tests/test_translation_result.py` never runs under `unittest` and 5 of its 13 functions fail when called directly (P2-5 should convert it and decide the expected behavior).
2. `tests/test_language_detection_translation.py` (Windows-only) imports `translate.translate`, which no longer exists, so it errors on Windows.
3. **`reclean_braille_endspace` is also quadratic**, in the number of tokens it trims: each trim deletes from the middle of two lists and shifts every later `raw_to_braille_pos` entry. Worst case measured here (every token's braille ends in a blank cell): 10,000 trimmed tokens 3.8 s, 20,000 15.4 s, 40,000 62 s. How many tokens real liblouis output trims (for example `zh-tw.ctb` on Chinese prose) cannot be measured on Linux. The roadmap row does not include it, and the method is part of the alignment post-processing that P2-5 restructures, so it stays as is here; the golden fixture of this task (whose fake helper trims at the end of every CJK run) is the safety net for fixing it in P2-5 or a separate task.
4. `language_has_all` builds a `set` for every character `bind_word_tokens` checks (a constant factor, not quadratic). P2-5.

## Windows verification debt

- On a packaged build, before and after: convert a long mixed zh/en document with inline math (for example an imported PDF or EPUB chapter) with `zh-tw.ctb` and `en-ueb-g2.ctb`; the Braille Result text, the ASCII output mode and the exported BRL must be byte-identical, and the conversion should be visibly faster on long documents. While there, count how many tokens `reclean_braille_endspace` trims for that document (known defect 3) so the follow-up can be prioritized.
- Open the Dual View window and export HTML for a document with math; both must match the pre-change output (MathML rendered in the source column).
- Run the Windows-only modules (`tests.test_liblouis_runtime`, `tests.test_translation_language_result`, `tests.test_language_detection_translation`) and compare with the baseline (the last two already fail for the reasons above).
- No menu, dialog or string changes, so no screenshots and no `generate-pot.bat` run are needed.

## Out of Scope

- Tokenizer and wrapper extraction, moving `TranslationResult` to `conversion/alignment.py`, the P2-5 failing test, and converting or fixing `tests/test_translation_result.py` (all P2-5).
- Hoisting the per-call sets inside `bind_word_tokens` and `wrap`, `language_has_all` performance, and the quadratic trim in `reclean_braille_endspace` (P2-5 or a separate task; known defects 3 and 4).
- The function-local imports in `conversion/text/pipeline.py` and the dictionary/char-map reloading (P1-6).
- `documents/formats <-> documents/workspace` (D-5) and typing `DualViewSegment.result` or `ConversionOutput.translation_results` more precisely.
- `ApplicationPaths` (P2-6) and indentation (P2-8).
