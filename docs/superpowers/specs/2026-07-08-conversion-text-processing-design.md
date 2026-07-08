# DotExpress Conversion Text Processing Refactor Design

Date: 2026-07-08

## Background

DotExpress has already extracted the main conversion flow behind the facade in `client/conversion/service.py`, but the rules directly related to text pre-processing and post-processing are still spread across multiple modules:

- `client/conversion/output.py`
- `client/conversion/plain_text.py`
- `client/conversion/segments.py`
- `client/conversion/wrapping.py`
- `client/utils.py`
- `client/Bopomofo.py`
- `client/conversion/math_service.py`

In the current state, if the next phase adds character or phrase pre-processing replacements, or system-level text rules, developers are likely to modify `output.py`, `plain_text.py`, and `utils.py` at the same time. This indicates that conversion-facing text processing still does not have a clear boundary.

At the same time, the repository also contains other text processing paths, such as:

- `client/documents/importers/html_to_ast.py`
- `client/documents/importers/markdown_renderer.py`
- `client/documents/importers/pdf_importer.py`

These belong to document import cleanup, not the front-end rule layer of braille conversion. Reorganizing them together with conversion text processing would make the scope both broader and less clear.

Therefore, this spec focuses on package-level convergence of conversion-facing text processing, so future text pre-processing has a clear home, while avoiding an early refactor of `client/translate.py`.

## Superpower Brainstorming Conclusions

This round first answers three questions before fixing the spec scope.

### Question 1: What layer does the next-phase requirement actually target?

The next-phase requirement is conversion-side text replacement and pre-processing, not:

- document import cleanup
- UI workflow
- `TranslationResult` wrapping or token cleanup

Therefore, this refactor should focus on the front part of conversion, not the entire output pipeline.

### Question 2: What is the biggest technical risk right now?

The main risk is not that one file is large. The real issue is that conversion pre-processing responsibilities are scattered:

- char-level mapping
- dictionary replacement
- Bopomofo dictionary rule handling
- inline math segmentation
- language-aware plain text entry

Once these responsibilities are scattered, a new rule can easily be added to only one conversion entry point, causing behavioral drift.

### Question 3: What should this round explicitly avoid?

This round does not:

- rewrite `client/translate.py`
- merge `client/conversion/wrapping.py` back into the text package
- introduce a generic pipeline framework
- fold importer normalization into the same package
- change user-visible behavior, output rules, or UI

## Goals

Converge the text processing in the front part of conversion into a small package so that the following needs have a stable extension point:

1. specific character replacements
2. specific phrase replacements
3. system-level text pre-processing rules
4. future rule layering or debug inspection

After completion, the following should be true:

- front-end conversion rules are no longer scattered across `output.py`, `plain_text.py`, and `utils.py`
- new rules have a single package-level boundary for extension
- no large `translate.py` refactor is required first
- the current public conversion API and user-visible results remain unchanged

## Non-Goals

- rewriting `TranslationResult`
- moving `wrap(width)` out of `client/conversion/wrapping.py`
- changing the MathML or MathCAT path in `client/conversion/math_service.py`
- reorganizing whitespace normalization in document importers
- introducing a plugin system, DI container, or configurable pipeline engine
- adding a new conversion output mode

## Current Problems

### Problem 1: Pre-processing and rule execution do not have a clear boundary

The current conversion flow includes at least the following steps:

- `BopomofoChar2Braille.csv` char-level mapping
- inline math segmentation
- dictionary replacement
- Bopomofo dictionary target normalization
- language detection and table switching
- ASCII post-processing mapping

These steps are spread across different modules, making it difficult for developers to decide where a new rule should live.

### Problem 2: `apply_dictionary()` carries too many responsibilities

`apply_dictionary()` in `client/utils.py` currently handles all of the following:

- loading the dictionary CSV
- loading the Bopomofo mapping CSV
- handling entries with `type == "Bopomofo"`
- splitting replacement parts by `@`
- creating atomic markers
- aligning raw and replacement segments
- executing the overall replacement

That gives it persistence, rule application, and alignment protocol responsibilities at the same time, which hurts future extension and testing.

### Problem 3: Two conversion entry points share rules but do not share a boundary

`client/conversion/output.py` currently performs these steps separately in both `convert_text_with_alignment()` and `convert_text_for_output()`:

- `BopomofoChar2Braille` pre-processing
- `Braille2Ascii` post-processing

The behavior is currently consistent, but if a new source-text pre-processing rule is added later, it can easily be implemented in only one path.

## Design Principles

- Only converge conversion-facing text processing
- Use package splitting and small orchestration functions to solve boundary issues
- Keep the existing facade in `client/conversion/service.py`
- Do not introduce a generic pipeline framework for pattern completeness
- Modules inside the new package should depend as much as possible on plain text data and small helpers, not on `wx` or GUI state

## Options Considered

### A. Keep the current structure and continue adding helpers in place

Pros:

- smallest code change

Cons:

- rule boundaries remain unclear
- new pre-processing rules remain scattered
- does not solve the oversized `apply_dictionary()` problem

Rejected.

### B. Create a small `client/conversion/text/` package and converge front-end conversion rules

Pros:

- aligns directly with the requirement
- preserves the existing facade and wrapping layer
- limited scope, suitable for incremental refactoring
- provides a stable location for future text replacement rules

Cons:

- existing imports and test patch targets must be updated in sync

Accepted.

### C. Rewrite `client/translate.py` and reorganize the entire conversion pipeline

Pros:

- cleaner responsibilities in theory

Cons:

- too broad a change surface
- does not align with this round's requirement
- creates higher risk around alignment, dual view, and wrapping

Rejected.

## Decision

Adopt option B: add a new `client/conversion/text/` package to converge front-end conversion rules and orchestration; keep `client/conversion/wrapping.py` in place; do not address `client/translate.py` in this round.

## Target Structure

```text
client/
├── conversion/
│   ├── output.py
│   ├── plain_text.py
│   ├── service.py
│   ├── wrapping.py
│   └── text/
│       ├── __init__.py
│       ├── char_maps.py
│       ├── dictionary_rules.py
│       ├── math_segments.py
│       └── pipeline.py
└── utils.py
```

After this round, `utils.py` should no longer carry the main responsibility for conversion text processing. New conversion logic should import directly from `conversion/text/`, and the old conversion-related entry points should be removed rather than preserved behind compatibility layers.

## Module Responsibilities

### `client/conversion/text/char_maps.py`

Responsibilities:

- provide char-level mapping helpers
- encapsulate single-character mappings such as `BopomofoChar2Braille.csv` and `Braille2Ascii.csv`

Should contain:

- functionality equivalent to the existing `translate__mapping_char()`

Should not handle:

- dictionary rules
- language detection
- wrapping

### `client/conversion/text/dictionary_rules.py`

Responsibilities:

- apply dictionary replacement
- manage atomic marker and bracket segment alignment
- handle dictionary target logic for entries with `type == "Bopomofo"`

Should contain:

- `apply_dictionary()`
- `split_bracket_segments()`
- related alignment helpers
- string replacement helpers

Should not handle:

- `TranslationRuntime`
- wrapping or output formatting
- GUI or settings state

### `client/conversion/text/math_segments.py`

Responsibilities:

- parse `$...$` inline math segments
- decide whether a math/text segment boundary needs an inserted space

Should contain:

- `parse_inline_math_segments()`
- `segment_needs_boundary_space()`

Should not handle:

- MathCAT translation
- MathML normalization

### `client/conversion/text/pipeline.py`

Responsibilities:

- provide small orchestration functions for the front part of conversion
- connect source pre-processing, plain-text rule application, and language-aware translation entry

The first version only needs a narrow API, such as:

- `preprocess_source_text()`
- `apply_plain_text_rules()`

It should converge the front-end steps currently spread across `output.py` and `plain_text.py`, but it must not become a full pipeline framework.

Should not handle:

- threading
- GUI callback policy
- wrapping or layout

### Keep `client/conversion/wrapping.py`

This round keeps its current responsibilities:

- merge translation results
- clean up translation results
- wrap output

Reason:

- these behaviors are already closer to translation-result post-processing and output formatting
- the current requirement does not target this layer
- keeping it separate avoids expanding the scope by mixing front-end text processing with wrapping concerns

## API Boundaries

This round does not aim for heavy abstraction, but it does need clear helper landing points.

### `preprocess_source_text()`

Responsibilities:

- accept the raw source text
- apply front-end char-level pre-processing
- return the text used by later segmentation and translation

The first version must at least cover the current `BopomofoChar2Braille` source mapping.

### `apply_plain_text_rules()`

Responsibilities:

- apply dictionary replacement
- preserve raw/replacement alignment information
- allow later runtime translation to know which segments are atomic tokens

The return type does not need to be a heavy class immediately, but it should at least represent:

- the raw side
- the replacement side
- atomic segmentation

The first version may keep using the current `{"raw": ..., "replacement": ...}` shape as long as the responsibility moves into the correct module.

## Migration Strategy

### Phase 1: Create the package shell

- add `client/conversion/text/__init__.py`

### Phase 2: Move `math_segments`

- move the contents of `client/conversion/segments.py` into `conversion/text/math_segments.py`
- update `client/conversion/service.py` to import from the new location

### Phase 3: Move `char_maps`

- move `translate__mapping_char()` into `conversion/text/char_maps.py`
- update `output.py` and other conversion paths to import it from the new location

### Phase 4: Move `dictionary_rules`

- move `apply_dictionary()`, `split_bracket_segments()`, and related helpers into `conversion/text/dictionary_rules.py`
- update `plain_text.py` to use the new location

### Phase 5: Create `pipeline.py`

- converge source pre-processing and plain-text rule orchestration into `pipeline.py`
- let `output.py` and `plain_text.py` share the front-end semantics through it

These five steps should remain independently verifiable. They do not need to land as one large change.

## Dependency Direction

- `char_maps.py` depends only on the standard library and CSV files
- `dictionary_rules.py` depends on the standard library and the Bopomofo normalization helper
- `math_segments.py` is pure text segmentation logic
- `pipeline.py` may depend on `char_maps.py`, `dictionary_rules.py`, and `languageDetection`
- `wrapping.py` continues to depend on `TranslationResult`

`pipeline.py` must not depend back on `wrapping.py` or any GUI module.

## Required Preservation of Current Public Behavior

This refactor must preserve the following:

- the public conversion API remains unchanged:
  - `convert_text_with_alignment()`
  - `convert_text_for_output()`
- existing dictionary replacement behavior for dual-view alignment remains unchanged
- `BopomofoChar2Braille` source pre-processing behavior remains unchanged
- `Braille2Ascii` output mapping behavior remains unchanged
- inline math segmentation and boundary-space behavior remain unchanged
- existing tests that patch old targets must be updated to the new module locations

## Test Strategy

This refactor touches the front part of text conversion, which is core business behavior. Implementation must add characterization tests before moving modules; the tests must prove that the new boundary preserves current behavior, not merely that the new files import successfully.

After each move, at minimum run these focused tests:

- `tests.test_conversion_service`
- `tests.test_utils`
- `tests.test_conversion_segments`
- `tests.test_dual_view_model`
- `tests.test_gui_document_flows`

Current behaviors that must be covered:

- `BopomofoChar2Braille.csv` source pre-processing still runs before translation.
- `Braille2Ascii.csv` only runs when `output_mode == "ascii"`, and it still runs after braille wrapping.
- `convert_text_with_alignment()` and `convert_text_for_output()` share the same source pre-processing semantics.
- `$...$` inline math segmentation, escaped dollars, unclosed-dollar fallback, and math/text boundary-space behavior remain unchanged.
- dictionary replacement still applies sources from longest to shortest to avoid shorter terms replacing overlapping longer terms first.
- dictionary replacement does not rewrite already marked atomic replacement output.
- dictionary entries with `type == "Bopomofo"` still go through zhuyin normalization and Bopomofo-to-braille mapping.
- `@`-separated multi-part braille replacements still align with source characters.
- raw and replacement segment atomic flags must match; mismatches still raise errors.
- language detection and table switching behavior remain unchanged, including inserted boundary spaces when the selected table changes.
- fallback text translation still builds results from `raw`, not replacement text.
- the dual-view model sees the same raw/braille alignment as before the move.

Recommended new or strengthened characterization tests:

- `tests.test_conversion_text_char_maps`: cover char-map CSV field validation, single-character conversion, empty-target deletion, non-single-character source skipping, and ASCII output mapping.
- `tests.test_conversion_text_dictionary_rules`: cover normal replacement, longest-match ordering, atomic marker protection, Bopomofo dictionaries, `@` multi-part alignment, and missing-dictionary fallback.
- `tests.test_conversion_text_math_segments`: cover inline math, escaped dollar signs, unclosed dollars, and adjacent text/math boundary spaces.
- `tests.test_conversion_text_pipeline`: cover source pre-processing shared by both conversion entry points and plain-text rule application returning raw/replacement/atomic segmentation.

Suggested validation per step:

### After moving `math_segments.py`

- confirm text/math segment order and boundary-space behavior remain unchanged
- run `tests.test_conversion_text_math_segments`

### After moving `char_maps.py`

- confirm source pre-processing and ASCII output mapping remain unchanged
- run `tests.test_conversion_text_char_maps`

### After moving `dictionary_rules.py`

- confirm atomic segment alignment remains unchanged
- confirm Bopomofo dictionary multi-part alignment remains unchanged
- run `tests.test_conversion_text_dictionary_rules`

### After creating `pipeline.py`

- confirm the two conversion entry points still share the same pre-processing semantics
- run `tests.test_conversion_text_pipeline`

## Risks and Tradeoffs

### Risk 1: Moving functions breaks existing patch targets

Some tests may patch old import locations. The approach in this round is not to keep compatibility aliases, but to update tests and callers in sync so the new boundary is fully adopted at once.

### Risk 2: The first version of `dictionary_rules.py` may still be too large

This is an intentional tradeoff. The goal of the first version is to fix the package boundary first, not to fully split rule persistence and rule execution in one pass.

### Risk 3: `pipeline.py` may grow into a generic engine

This must be explicitly avoided. `pipeline.py` should remain a small set of orchestration functions and must not become a configurable, registrable, dynamically assembled framework.

## Success Criteria

After completion, all of the following should be true:

1. New conversion text pre-processing and replacement rules have a clear module landing point.
2. `client/utils.py` is no longer the main carrier of conversion text rules.
3. `client/conversion/output.py` and `client/conversion/plain_text.py` no longer each maintain scattered front-end rule details.
4. The next-phase requirement can be supported without first modifying `client/translate.py`.
5. Existing focused tests and GUI flow regression tests still pass.
