# LaTeX Math Segment Conversion With MathCAT

## Summary

Replace the current math placeholder path in DotExpress with a real inline math conversion pipeline for `$...$` segments:

1. LaTeX source inside the math segment
2. convert LaTeX to MathML with `latex2mathml`
3. convert MathML to Nemeth braille with a bundled MathCAT runtime
4. merge the result back into the existing conversion pipeline as a single-token `TranslationResult`

This stage extends the previously approved math segment detection design by making math conversion fully executable at runtime on Windows.

## Goals

- Treat `$...$` segments as LaTeX math input.
- Convert LaTeX math to MathML using `latex2mathml`.
- Convert MathML to Nemeth braille using MathCAT.
- Bundle the required MathCAT runtime and resources into DotExpress instead of requiring an external NVDA installation.
- Keep math segments represented as single-token `TranslationResult` values.
- Insert boundary spaces between text and math segments only when both adjacent sides are non-whitespace.
- Fail the entire conversion if math conversion fails at any stage.

## Non-Goals

- Support additional math delimiters such as `\\(...\\)` in this stage.
- Provide fallback behavior that preserves raw LaTeX when math conversion fails.
- Guarantee non-Windows runtime support.
- Add user-facing settings to choose alternative math braille providers.
- Implement fine-grained internal tokenization inside math segments.

## Current Context

DotExpress now has:

- top-level `$...$` math segment detection in `client/conversion/service.py`
- text/math segment dispatch inside `translate_with_language()`
- math segments currently routed to a placeholder translator and wrapped as a single-token `TranslationResult`

Relevant external references:

- Access8Math uses `latex2mathml.converter.convert()` for LaTeX to MathML conversion.
- NVDA MathCAT exposes `getBrailleForMathMl(mathml: str) -> str`, backed by a runtime that first sets the MathML and then requests braille output.

These references establish the intended pipeline, but DotExpress will embed its own minimal MathCAT adapter/runtime instead of depending on an installed NVDA environment.

## Design

### 1. Keep segment dispatch in conversion/service.py

The top-level segment model remains unchanged:

- `text` segments continue through the existing language detection and liblouis text translation flow
- `math` segments become LaTeX math conversion requests

`translate_with_language()` remains responsible for:

- segment dispatch
- boundary space insertion
- merge order

It should not take on direct responsibility for MathCAT runtime initialization details.

### 2. Introduce a dedicated math conversion module

Add a focused module such as `client/conversion/math_service.py` with a narrow public surface:

- `latex_to_mathml(latex_text: str) -> str`
- `mathml_to_nemeth_braille(mathml_text: str) -> str`
- `translate_math_segment(latex_text: str) -> str`

Responsibilities:

- `latex_to_mathml()` wraps the `latex2mathml` library and any required post-processing for DotExpress compatibility.
- `mathml_to_nemeth_braille()` delegates to the bundled MathCAT adapter.
- `translate_math_segment()` owns the full `LaTeX -> MathML -> Nemeth braille` pipeline and raises explicit errors on failure.

This keeps `conversion/service.py` focused on orchestration rather than embedding math runtime details directly.

### 3. Bundle a minimal MathCAT runtime inside DotExpress

DotExpress should not depend on a separately installed NVDA or MathCAT environment.

Instead, create a minimal embedded runtime derived from the NVDA MathCAT source and required runtime files:

- the Python adapter logic needed to initialize MathCAT and call braille output
- the required dynamic libraries/runtime files
- the required MathCAT rules/resources needed for braille generation

Design constraints:

- keep the embedded surface as small as practical
- do not copy unrelated NVDA presentation or UI code
- isolate DotExpress-facing access behind a small adapter API

The adapter should provide a simple DotExpress-facing operation such as:

- `get_braille_for_mathml(mathml_text: str) -> str`

The adapter owns:

- locating bundled runtime files
- one-time runtime initialization
- any required preference setup for Nemeth braille output
- translating runtime/library exceptions into normal Python exceptions

### 4. Official support scope is Windows packaged runtime

This feature is designed as a Windows-targeted runtime feature.

Support policy:

- Windows packaged DotExpress app: officially supported
- non-Windows development environments: may use stubs, skips, or limited test coverage
- cross-platform MathCAT runtime support: out of scope for this stage

This aligns with the project’s existing Windows packaging model and existing runtime assumptions around braille-related native dependencies.

### 5. Convert math output into single-token TranslationResult values

Math segments remain atomic in the merged conversion result.

Representation stays the same:

- `raw = [latex_text]`
- `braille = list(nemeth_braille_output)`
- `raw_to_braille_pos = [0]`
- `braille_to_raw_pos = [0] * len(braille)`

This preserves the previously approved behavior and avoids prematurely defining detailed cursor/token mappings inside LaTeX math expressions.

### 6. Insert boundary spaces only when needed

Boundary spaces are handled by the conversion pipeline, not by MathCAT.

Rule:

- when two top-level adjacent segments meet
- and at least one side is `math`
- and the left segment does not end with whitespace
- and the right segment does not begin with whitespace
- insert one ordinary space token between them before merge

Examples:

- `計算$1+2$的值` -> `計算 ⟨math⟩ 的值`
- `計算 $1+2$ 的值` -> no extra spaces added
- `$x+1$測試` -> `⟨math⟩ 測試`

This intentionally differs from the current language-switch spacing logic by checking both sides, which avoids introducing duplicate spaces around math boundaries.

### 7. Error handling is fail-fast

Any math conversion failure stops the entire conversion.

Failure points:

- LaTeX to MathML conversion error
- MathCAT runtime initialization error
- MathCAT MathML to braille conversion error

Behavior:

- propagate the failure through the existing conversion error path
- do not fall back to raw LaTeX
- do not emit partial placeholder output
- do not silently skip the math segment

This is the safest behavior for a transcription-focused tool where silent corruption is worse than explicit failure.

## Testing

### Unit tests

Add or update tests to verify:

- math segments call the LaTeX -> MathML -> MathCAT sequence in order
- text/math boundary spaces are inserted only when both sides are non-whitespace
- existing spaces around math segments are preserved without duplication
- math segments still merge as single-token `TranslationResult` values
- conversion errors propagate when LaTeX conversion fails
- conversion errors propagate when MathCAT braille conversion fails

These tests should rely on mocks/stubs for the math adapter so they remain stable in non-Windows development environments.

### Windows runtime verification

Manual or environment-specific verification is still required on Windows to prove:

- bundled MathCAT runtime initializes correctly
- Nemeth braille output is returned for representative LaTeX expressions
- packaged app resource lookup works

Suggested coverage includes:

- inline arithmetic such as `$1+2$`
- fractions such as `$\frac{1}{2}$`
- superscripts/subscripts such as `$x^2$`, `$a_1$`
- mixed Chinese text and LaTeX math in one line

## Tradeoffs

### Why not keep the placeholder path inside conversion/service.py?

Because the runtime responsibility has changed. A real MathCAT dependency brings initialization, packaging, and error semantics that deserve their own module boundary.

### Why not depend on an installed NVDA or external MathCAT environment?

That would make DotExpress runtime behavior depend on machine-local external state and would undermine packaging predictability. Bundling the required runtime is more appropriate for a desktop application.

### Why keep math as a single token?

Because the current requirement is to make real Nemeth output work, not to redesign fine-grained math cursor mapping. Keeping math atomic preserves the existing approved structure while reducing scope.

## Future Follow-Up

Potential later work:

- add support for `\\(...\\)` delimiters
- refine math-internal cursor/token mapping
- add Windows packaging documentation for bundled MathCAT assets
- add broader MathCAT configuration support if DotExpress later needs alternative braille codes
