# Conversion Text Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converge conversion-facing text processing into `client/conversion/text/` so future character, phrase, and system-level source-text rules have a clear home, while preserving current text conversion behavior exactly.

**Architecture:** Keep `client/conversion/service.py` as the public facade and keep `client/conversion/wrapping.py` responsible for translation-result cleanup and wrapping. Move front-end text processing into small modules: char maps, dictionary rules, math segmentation, and narrow pipeline orchestration. Do not keep compatibility imports for old conversion helpers in `client/utils.py`; update callers and tests to the new module locations.

**Tech Stack:** Python 3, `csv`, `pathlib`, `dataclasses` if needed, `unittest`, `pytest`-style assertions in existing tests, `unittest.mock`

**Specs:**
- `docs/superpowers/specs/2026-07-08-conversion-text-processing-design.md`
- `docs/superpowers/specs/2026-07-08-conversion-text-processing-design_zh-TW.md`

---

## File Structure

- Create `client/conversion/text/__init__.py`
- Create `client/conversion/text/char_maps.py`
- Create `client/conversion/text/dictionary_rules.py`
- Create `client/conversion/text/math_segments.py`
- Create `client/conversion/text/pipeline.py`
- Modify `client/conversion/output.py`
- Modify `client/conversion/plain_text.py`
- Modify `client/conversion/service.py`
- Remove conversion text processing helpers from `client/utils.py`
- Keep `client/conversion/wrapping.py` behavior unchanged
- Add or modify tests:
  - `client/tests/test_conversion_text_char_maps.py`
  - `client/tests/test_conversion_text_dictionary_rules.py`
  - `client/tests/test_conversion_text_math_segments.py`
  - `client/tests/test_conversion_text_pipeline.py`
  - `client/tests/test_conversion_service.py`
  - `client/tests/test_utils.py`
  - `client/tests/test_dual_view_model.py`
  - `client/tests/test_gui_document_flows.py`

## Task 1: Add Characterization Tests For Existing Text Behavior

**Files:**
- Create: `client/tests/test_conversion_text_char_maps.py`
- Create: `client/tests/test_conversion_text_dictionary_rules.py`
- Create: `client/tests/test_conversion_text_math_segments.py`
- Create: `client/tests/test_conversion_text_pipeline.py`
- Modify: `client/tests/test_conversion_service.py`
- Modify: `client/tests/test_dual_view_model.py`

- [ ] **Step 1: Add char-map characterization tests**

Create `client/tests/test_conversion_text_char_maps.py` covering the current `translate__mapping_char()` behavior before moving it:

- valid CSV maps single-character source values to target values
- empty target values delete the source character
- multi-character source values are ignored
- missing header row raises `ValueError`
- missing required columns raises `ValueError`
- Bopomofo source pre-processing runs before translation in conversion service
- `Braille2Ascii.csv` mapping runs only for `output_mode == "ascii"` and after wrapping

- [ ] **Step 2: Add dictionary-rule characterization tests**

Create `client/tests/test_conversion_text_dictionary_rules.py` covering current dictionary behavior:

- missing dictionary file returns unchanged `raw` and `replacement`
- normal replacement produces matching raw/replacement bracket segments
- longer source strings are applied before shorter overlapping strings
- atomic marker protection prevents remapping dictionary output
- `type == "Bopomofo"` entries pass through zhuyin normalization and Bopomofo-to-braille mapping
- `@`-separated braille replacements align with source characters when lengths match
- source/replacement length mismatch collapses to one atomic source segment and one replacement segment
- malformed bracket markers are treated according to existing `split_bracket_segments()` behavior

- [ ] **Step 3: Add math-segment characterization tests**

Create `client/tests/test_conversion_text_math_segments.py` covering current segmentation behavior:

- plain text remains one text segment
- `$1+2$` creates text/math/text segments in order
- escaped dollar signs remain text
- unclosed dollar returns the dollar and following text as a text segment
- adjacent text/math boundaries insert a space only when either side is math and neither side already has whitespace

- [ ] **Step 4: Add pipeline-level characterization tests**

Create `client/tests/test_conversion_text_pipeline.py` for behavior that should become the new orchestration boundary:

- `preprocess_source_text()` applies the current Bopomofo char map semantics
- `apply_plain_text_rules()` returns the current raw/replacement dictionary result shape
- raw and replacement atomic flags remain paired before runtime translation
- source pre-processing is shared by both `convert_text_with_alignment()` and `convert_text_for_output()`

Use temporary CSV fixtures where possible so the tests do not depend on Windows-only native translation.

- [ ] **Step 5: Strengthen conversion and dual-view regression coverage**

Update existing tests where needed to prove behavior remains unchanged:

- `tests.test_conversion_service`: table switching, boundary-space insertion, ASCII output mode, and source preprocess ordering
- `tests.test_dual_view_model`: dictionary atomic segments still produce the same raw/braille alignment shape
- `tests.test_gui_document_flows`: GUI conversion and dual-view refresh still receive equivalent `translation_results`

- [ ] **Step 6: Run characterization tests before moving code**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_conversion_text_char_maps \
  tests.test_conversion_text_dictionary_rules \
  tests.test_conversion_text_math_segments \
  tests.test_conversion_text_pipeline \
  tests.test_conversion_service \
  tests.test_dual_view_model \
  -v
```

Expected before implementation: new tests may fail only where they import future module names. If a test targets existing behavior through existing modules, it should pass before moving code. Do not change behavior to satisfy tests; adjust test import targets as each module is introduced.

## Task 2: Create `conversion/text` Package And Move Math Segmentation

**Files:**
- Create: `client/conversion/text/__init__.py`
- Create: `client/conversion/text/math_segments.py`
- Modify: `client/conversion/service.py`
- Delete or empty: `client/conversion/segments.py` only if no non-conversion caller remains
- Modify: `client/tests/test_conversion_text_math_segments.py`
- Modify: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Create package shell**

Add `client/conversion/text/__init__.py`.

Do not add re-export compatibility aliases for old conversion helper locations.

- [ ] **Step 2: Move segment parser**

Move these functions from `client/conversion/segments.py` to `client/conversion/text/math_segments.py`:

- `parse_inline_math_segments`
- `segment_needs_boundary_space`

Keep function names and behavior unchanged.

- [ ] **Step 3: Update imports**

Update `client/conversion/service.py` and tests to import from `conversion.text.math_segments`.

Remove any old import path usage:

```bash
rg -n "conversion\\.segments|from conversion\\.segments|import conversion\\.segments" client
```

- [ ] **Step 4: Run math-segment tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_conversion_text_math_segments tests.test_conversion_service -v
```

Expected: all text/math segmentation and boundary-space behavior remains unchanged.

## Task 3: Move Char Maps Into `conversion/text/char_maps.py`

**Files:**
- Create: `client/conversion/text/char_maps.py`
- Modify: `client/conversion/output.py`
- Modify: `client/conversion/service.py`
- Modify: `client/utils.py`
- Modify: `client/tests/test_conversion_text_char_maps.py`
- Modify: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Move char-map helper**

Move `translate__mapping_char()` from `client/utils.py` to `client/conversion/text/char_maps.py`.

Keep current behavior unchanged:

- required header validation
- required column validation
- single-character source mapping
- empty target deletion
- multi-character source skipping

- [ ] **Step 2: Add source and output helper names**

Add narrow helpers in `char_maps.py` if they reduce duplicated path handling:

- `map_characters()`
- `preprocess_bopomofo_characters()`
- `map_braille_to_ascii()`

These helpers may wrap the moved implementation but must not introduce new behavior.

- [ ] **Step 3: Update conversion imports**

Update `client/conversion/output.py` and `client/conversion/service.py` to import char-map functionality from `conversion.text.char_maps`.

Remove `translate__mapping_char` from `client/utils.py`; do not keep a compatibility import.

Verify:

```bash
rg -n "translate__mapping_char|from utils import" client
```

Any remaining `translate__mapping_char` reference should point to `conversion.text.char_maps`.

- [ ] **Step 4: Run char-map tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_conversion_text_char_maps tests.test_conversion_service tests.test_utils -v
```

Expected: char-map behavior, conversion source preprocess, and ASCII output behavior remain unchanged.

## Task 4: Move Dictionary Rules Into `conversion/text/dictionary_rules.py`

**Files:**
- Create: `client/conversion/text/dictionary_rules.py`
- Modify: `client/conversion/plain_text.py`
- Modify: `client/utils.py`
- Modify: `client/tests/test_conversion_text_dictionary_rules.py`
- Modify: `client/tests/test_utils.py`
- Modify: `client/tests/test_conversion_service.py`
- Modify: `client/tests/test_dual_view_model.py`

- [ ] **Step 1: Move dictionary helper functions**

Move these functions and constants from `client/utils.py` to `client/conversion/text/dictionary_rules.py`:

- `DICTIONARY_MARKER_OPEN`
- `DICTIONARY_MARKER_CLOSE`
- `DICTIONARY_MARKER_JOIN`
- `DICTIONARY_MARKER_PATTERN`
- `BracketSegment`
- `_wrap_atomic_parts`
- `_align_source_and_replacement_parts`
- `mapping`
- `translate__mapping_string` if it is still used for conversion text processing
- `apply_dictionary`
- `split_bracket_segments`

Keep behavior unchanged.

- [ ] **Step 2: Update plain-text conversion imports**

Update `client/conversion/plain_text.py` to import `apply_dictionary` and `split_bracket_segments` from `conversion.text.dictionary_rules`.

Remove moved functions from `client/utils.py`; do not keep compatibility aliases.

Verify no old conversion imports remain:

```bash
rg -n "apply_dictionary|split_bracket_segments|DICTIONARY_MARKER|translate__mapping_string|\\bmapping\\(" client
```

Remaining references should import from `conversion.text.dictionary_rules` unless they are local test references to the new module.

- [ ] **Step 3: Update tests to new module names**

Move behavior-focused tests from `tests.test_utils` into `tests.test_conversion_text_dictionary_rules` where appropriate.

Keep `tests.test_utils` only for non-conversion helpers if any remain.

- [ ] **Step 4: Run dictionary and alignment tests**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_conversion_text_dictionary_rules \
  tests.test_utils \
  tests.test_conversion_service \
  tests.test_dual_view_model \
  -v
```

Expected: dictionary replacement, atomic markers, Bopomofo dictionary behavior, and dual-view alignment remain unchanged.

## Task 5: Add Narrow Text Pipeline Orchestration

**Files:**
- Create: `client/conversion/text/pipeline.py`
- Modify: `client/conversion/output.py`
- Modify: `client/conversion/plain_text.py`
- Modify: `client/conversion/service.py`
- Modify: `client/tests/test_conversion_text_pipeline.py`
- Modify: `client/tests/test_conversion_service.py`
- Modify: `client/tests/test_gui_document_flows.py`

- [ ] **Step 1: Add `preprocess_source_text()`**

In `client/conversion/text/pipeline.py`, add `preprocess_source_text()` to wrap current source pre-processing behavior.

It should cover the existing `BopomofoChar2Braille.csv` source map and accept the paths or request context needed by `output.py` without depending on GUI state.

- [ ] **Step 2: Add `apply_plain_text_rules()`**

Add `apply_plain_text_rules()` to wrap current plain-text dictionary rule application.

It should preserve the current result shape or an explicitly equivalent lightweight structure containing:

- raw text side
- replacement text side
- atomic segmentation through bracket markers

- [ ] **Step 3: Route both conversion entry points through the shared source preprocess**

Update `client/conversion/output.py` so both `convert_text_with_alignment()` and the custom `wrap_both` path in `convert_text_for_output()` use `preprocess_source_text()`.

The behavior must remain unchanged, but source pre-processing should no longer be duplicated.

- [ ] **Step 4: Route plain text translation through `apply_plain_text_rules()`**

Update `client/conversion/plain_text.py` so dictionary application is delegated through `conversion.text.pipeline.apply_plain_text_rules()` or the lower-level dictionary module as appropriate.

Keep language detection and runtime translation behavior unchanged.

- [ ] **Step 5: Run pipeline tests**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_conversion_text_pipeline \
  tests.test_conversion_service \
  tests.test_gui_document_flows \
  -v
```

Expected: both conversion entry points share source pre-processing and all GUI conversion flows preserve current behavior.

## Task 6: Remove Old Conversion Text Responsibilities From `utils.py`

**Files:**
- Modify: `client/utils.py`
- Modify: tests that still import conversion helpers from `utils`

- [ ] **Step 1: Inspect remaining `utils.py` content**

After moving char maps and dictionary rules, inspect `client/utils.py`.

If no non-conversion helpers remain, delete the file only if all imports are removed. If non-conversion helpers remain, leave only those helpers.

- [ ] **Step 2: Verify no old conversion helper imports remain**

Run from repo root:

```bash
rg -n "from utils import|import utils|translate__mapping_char|apply_dictionary|split_bracket_segments|DICTIONARY_MARKER|translate__mapping_string" client
```

Expected: no production code imports moved conversion text helpers from `utils.py`.

- [ ] **Step 3: Run focused test suite**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_conversion_text_char_maps \
  tests.test_conversion_text_dictionary_rules \
  tests.test_conversion_text_math_segments \
  tests.test_conversion_text_pipeline \
  tests.test_conversion_service \
  tests.test_utils \
  tests.test_dual_view_model \
  tests.test_gui_document_flows \
  -v
```

Expected: all tests pass.

## Task 7: Final Regression And Spec Alignment Review

**Files:**
- Review all touched files
- No additional feature files unless a previous task exposed a required behavior fix

- [ ] **Step 1: Run broader conversion-adjacent tests**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_conversion_jobs \
  tests.test_conversion_segments \
  tests.test_conversion_service \
  tests.test_conversion_text_char_maps \
  tests.test_conversion_text_dictionary_rules \
  tests.test_conversion_text_math_segments \
  tests.test_conversion_text_pipeline \
  tests.test_dual_view_model \
  tests.test_dual_view_html \
  tests.test_gui_document_flows \
  tests.test_language_detection_translation \
  tests.test_translation_fallback \
  tests.test_translation_result \
  tests.test_translation_result_core \
  -v
```

Expected: all runnable tests pass. Existing platform-specific skips are acceptable only if they match the repository baseline.

- [ ] **Step 2: Inspect dependency boundaries**

Verify:

```bash
rg -n "conversion\\.segments|from conversion\\.segments|from utils import|translate__mapping_char|apply_dictionary|split_bracket_segments" client
```

Expected:

- no production imports of moved conversion helpers from old locations
- any remaining references point to `conversion.text.*`
- no compatibility aliases were added

- [ ] **Step 3: Inspect final diff for behavior drift**

Check:

- no user-visible strings changed
- no wx/UI behavior changed
- no importer normalization files changed
- `client/conversion/wrapping.py` behavior remains unchanged unless a test-proven import-only adjustment was necessary
- `client/translate.py` was not refactored in this plan

- [ ] **Step 4: Verify spec alignment**

Confirm the implementation matches both specs:

- `docs/superpowers/specs/2026-07-08-conversion-text-processing-design.md`
- `docs/superpowers/specs/2026-07-08-conversion-text-processing-design_zh-TW.md`

Spec alignment must explicitly check:

- conversion-facing text processing moved to `client/conversion/text/`
- document importer normalization was not folded into this package
- no generic pipeline framework was introduced
- current text conversion behavior is covered by characterization tests
- old conversion helper locations are removed rather than preserved through compatibility imports

- [ ] **Step 5: Record verification in handoff**

The final handoff must list:

- exact test commands run
- any platform-specific skips
- any residual risks around native Windows translation behavior
- confirmation that the refactor did not intentionally change conversion output
