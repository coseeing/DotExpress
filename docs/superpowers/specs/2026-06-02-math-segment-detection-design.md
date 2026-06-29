# Math Segment Detection In Conversion Pipeline

## Summary

Add first-stage support for detecting inline math content wrapped by unescaped dollar delimiters in DotExpress source text. Math segments will be recognized inside `translate_with_language()` and routed to a dedicated placeholder math translator instead of the normal text translation flow.

This stage only implements detection and pipeline integration. It does not implement real math braille rules yet.

## Goals

- Detect inline math segments using `$...$`.
- Use non-greedy matching semantics so multiple math segments in one line are handled independently.
- Treat `\$` as a normal literal dollar sign, not a math delimiter.
- Treat an unmatched opening `$` as plain text.
- Route detected math segments through a placeholder math translation function.
- Represent each math segment as a single-token `TranslationResult` so it can merge with existing text translation results.

## Non-Goals

- Support `\\(...\\)` delimiters in this stage.
- Implement real math braille translation rules.
- Add new GUI controls or user settings for math mode.
- Define character-level cursor mapping inside math content.

## Current Context

DotExpress currently converts text through this pipeline:

1. `client/gui.py` builds a `ConversionRequest`.
2. `client/conversion/service.py:convert_text_for_output()` performs pre-mapping and calls `translate_and_wrap_both()`.
3. `translate_and_wrap_both()` calls `translate_with_language()`.
4. `translate_with_language()` uses language detection, dictionary application, and liblouis translation to produce a merged `TranslationResult`.

This means `translate_with_language()` is the right integration point for segment-type dispatch. It already decides how different content segments are translated and merged.

## Design

### 1. Add inline math segment parsing

Introduce a helper in `client/conversion/service.py` that scans text linearly and emits ordered segments with a small shape such as:

- `{"type": "text", "text": "..."}`
- `{"type": "math", "text": "..."}`

Parser rules:

- Only an unescaped `$` can open or close a math segment.
- `\$` remains part of the current segment text.
- Matching is effectively non-greedy because the first valid closing `$` ends the current math segment.
- Multiple math segments are supported in one input string.
- If an opening `$` has no closing partner, the parser falls back and keeps that `$` and the remaining content inside a plain text segment.

Examples:

- `計算$1+2$的值` -> `text("計算")`, `math("1+2")`, `text("的值")`
- `計算$1+2$和$3+4$` -> `text("計算")`, `math("1+2")`, `text("和")`, `math("3+4")`
- `$1+\\$2$` -> `math("1+\\$2")`
- `計算$1+2` -> `text("計算$1+2")`

### 2. Add placeholder math translation

Introduce a placeholder function in `client/conversion/service.py` with a narrow interface:

```python
def translate_math_placeholder(math_text: str) -> str:
```

Input:

- The raw math content only, without surrounding delimiters.

Output:

- A placeholder braille string used only to prove the pipeline works end-to-end.

This function is intentionally isolated so the next stage can replace its internals with real math braille logic without changing segment parsing or dispatch structure.

### 3. Convert math output into a single-token TranslationResult

Add a helper that wraps placeholder math output into a `TranslationResult` compatible with the existing merge logic.

Representation:

- `raw = [math_text]`
- `braille = list(placeholder_output)`
- `raw_to_braille_pos = [0]` when output is non-empty
- `braille_to_raw_pos = [0] * len(braille)`

If the placeholder output is empty:

- `raw = [math_text]`
- `braille = []`
- `raw_to_braille_pos = [0]`
- `braille_to_raw_pos = []`

This treats the full math segment as one atomic token. That matches the scope of this stage and avoids inventing incomplete internal math mapping behavior too early.

### 4. Dispatch inside translate_with_language()

Update `translate_with_language()` so it first splits the incoming text into top-level text/math segments.

Dispatch rules:

- `text` segments continue through the current pipeline:
  - language detection
  - dictionary application
  - `split_bracket_segments()`
  - `translate()` / `translate_as_single_token()`
- `math` segments bypass language detection and liblouis text translation.
  - They go directly to `translate_math_placeholder()`
  - Then into the single-token `TranslationResult` wrapper

All produced `TranslationResult` objects are merged using the existing concatenation behavior.

### 5. Keep downstream behavior unchanged

No changes are planned for:

- `convert_text_for_output()`
- wrapping behavior in `translate_and_wrap_both()`
- output mode handling
- GUI save/export flows

They will inherit math support automatically because they already consume the merged conversion result.

## Error Handling

- Invalid or unmatched `$` delimiters do not raise errors. They are treated as ordinary text.
- Escaped dollars remain literal content.
- Placeholder math translation should not silently strip content. If it fails in a later stage, the failure should surface as a conversion error through existing exception handling.

## Testing

Add focused unit coverage in `client/tests/test_conversion_service.py` for:

- plain text with no math segments
- one `$...$` math segment
- multiple `$...$` math segments in one string
- escaped dollar inside math content
- escaped dollar outside math content
- unmatched opening `$` falling back to plain text
- conversion flow proving text and math segments are processed in order
- math segment wrapping into a single-token `TranslationResult`

Tests in this stage should validate parser behavior and dispatch behavior, not real math braille correctness.

## Tradeoffs

### Why not do this in convert_text_for_output()?

That would be simpler for a pure string replacement prototype, but it would treat math as a late formatting exception instead of a first-class content type in the translation pipeline.

Placing dispatch inside `translate_with_language()` keeps responsibility aligned with existing segment-based translation logic and reduces future rework.

### Why not tokenize inside math content now?

There is no agreed math braille segmentation model yet. Treating the whole math segment as one atomic token preserves compatibility with current merge behavior while keeping future design space open.

## Future Follow-Up

The next stage can replace `translate_math_placeholder()` with a real math translator and, if needed, refine the math `TranslationResult` mapping from one token to more detailed internal structure.
