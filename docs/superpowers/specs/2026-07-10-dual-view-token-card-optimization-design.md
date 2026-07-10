# Dual View Token Card Optimization Design

Date: 2026-07-10

## Summary

This change refines DotExpress dual view so its visual units match the actual
alignment granularity available from `TranslationResult`. The current dual view
model expands each `raw` element into per-character cards, which causes
multi-character tokens to show all braille on the first character and empty
cells on the remaining characters. That behavior is misleading for dictionary
replacements, grouped text tokens, and math segments.

The updated design changes dual view to render one card per
`TranslationResult.raw` element by default. It preserves segment boundaries at
the `TranslationResult` level, removes the named-region accessibility label from
segment containers, and renders math source cards as MathML DOM output instead
of raw LaTeX text.

## Superpower Brainstorming Conclusions

This spec follows the requirements clarified before writing:

- the visual unit is one `TranslationResult.raw` element, not one character
  inside that element
- each `TranslationResult` still renders as one segment container
- segment containers remain `<section class="segment">`, but without
  `aria-label`
- only a raw element that is exactly `" "` or exactly `"\n"` gets special
  whitespace handling
- math source renders as generated MathML DOM content above the corresponding
  braille

## Goals

- Make each dual-view card correspond to one `TranslationResult.raw` element.
- Stop splitting multi-character `raw` elements into separate character cards.
- Keep `TranslationResult` segment boundaries in the HTML structure.
- Remove the `aria-label` that currently turns each segment into a named region.
- Render math source cards using MathML DOM output.
- Preserve the existing session-scoped refresh and caching behavior.

## Non-Goals

- Do not change the conversion pipeline's wrapped braille output.
- Do not add finer-grained math alignment inside a single math token.
- Do not reinterpret or subdivide a `raw` element when no finer mapping exists.
- Do not redesign the dual view window lifecycle or menu entry.
- Do not persist dual view alignment data into document packages.

## Problem Statement

The current implementation in `client/dual_view/model.py` uses the
`raw_to_braille_pos` range for each `raw` token, but then expands that token
into one card per character. For a token such as `"我們"` with one braille
range, the first card receives the entire braille segment and the second card
shows an empty mapping. This makes the UI look like the second character has no
braille, when the actual data only says the full token maps to that braille
range.

The same mismatch appears for:

- dictionary replacements that intentionally bind multiple source characters
- text tokens that were produced as atomic units
- math segments that currently behave as single-token mappings

The current HTML renderer also labels every `<section>` with
`aria-label="Translation segment"`, which typically creates a named region in
accessibility trees. That extra landmark is not useful here.

## User-Visible Behavior

### Card granularity

- Each dual-view card represents one `TranslationResult.raw` element.
- The source part of the card shows the full raw element, not one character.
- The braille part of the card shows the full braille slice mapped to that raw
  element.

Example:

```python
raw = ["我們", "這", "一家"]
braille ranges = ["b1", "b2", "b3"]
```

Dual view should display:

- `我們 / b1`
- `這 / b2`
- `一家 / b3`

It must not display:

- `我 / b1`
- `們 / ∅`

### Space and newline behavior

Dual view keeps special handling only when a `raw` element is itself a single
space or a single newline:

- `" "` renders as a dedicated space card.
- `"\n"` renders as a line-break node, not as a normal card.

All other `raw` elements remain intact as single cards, even if their string
content contains spaces or newline characters. This avoids inventing alignment
boundaries that are not present in `TranslationResult`.

Examples:

- `["我們", " ", "這一家"]` renders as three cards.
- `["我們", "\n", "這一家"]` renders as one card, one line break, then one
  card.
- `["我們 這 一家"]` renders as one card.
- `["我們\n"]` renders as one card.

### Segment containers

- Each `TranslationResult` still renders inside one `<section class="segment">`
  container.
- Segment containers no longer include `aria-label`.
- Visual segment styling may remain, but segments must not become named regions.

### Math cards

- Math segments still map as one card per `raw` element.
- The source area of a math card renders MathML DOM output derived from the raw
  LaTeX source.
- The braille area shows the existing translated math braille.
- Math cards are not subdivided into smaller cards for internal symbols.

## Data Model Design

### 1. Segment scope remains unchanged

Dual view continues to use the unbound `TranslationResult` objects captured from
the latest successful conversion. Each input `TranslationResult` becomes one
segment in the output model.

Because math rendering now requires knowing whether a segment came from the math
translation path, the cached dual-view payload must wrap each result in a small
descriptor that preserves source kind:

```python
@dataclass(frozen=True)
class DualViewSegment:
    result: object
    source_kind: str  # "text" or "math"
```

The wrapping and display-output pipeline should continue to operate on plain
`TranslationResult` objects. The descriptor is only for the dual-view cache and
model builder.

### 2. Item scope changes from character-level to raw-element-level

The dual-view model should no longer treat one character as the default item
unit. Instead, each item corresponds to one `raw` element and its mapped
braille range.

The model should carry enough metadata for rendering and testing, for example:

```python
@dataclass(frozen=True)
class AlignmentItem:
    raw_index: int
    raw_text: str
    braille_start: int
    braille_end: int
    braille_text: str
    is_space: bool
    is_newline: bool
    source_kind: str  # "text" or "math"
    source_html: str | None
```

The exact field names may differ, but the model must distinguish:

- plain-text cards rendered from escaped text
- math cards rendered from trusted/generated MathML markup
- single-space cards
- single-newline break nodes

### 3. Raw-element mapping rules

For each `TranslationResult`:

- `raw_to_braille_pos[i]` is the start of raw element `i`
- element `i` ends at `raw_to_braille_pos[i + 1]`, or `len(braille)` for the
  last element
- `braille[start:end]` becomes the displayed braille for that item

Validation rules remain:

- `len(raw_to_braille_pos)` must equal `len(raw)`
- start/end ranges must be monotonic and within braille bounds

## Math Source Rendering

### 1. Source of truth

Dual view math rendering uses the same source text currently used for math
translation: the raw LaTeX-like string stored in the math segment's
`TranslationResult.raw` element.

### 2. Conversion path

Before rendering math source in HTML, dual view converts that raw math text to
MathML using the existing `latex_to_mathml()` helper from
`client/conversion/math_service.py`.

The HTML renderer then injects the resulting MathML as DOM markup in the card's
source area.

### 3. Failure behavior

If MathML conversion fails during dual-view model construction or rendering:

- the dual view refresh should fail through the existing error path rather than
  silently showing incorrect math
- the implementation must not fall back to partially parsed or guessed math HTML
  without an explicit design change

This keeps dual view consistent with the current math translation boundary,
where invalid math conversion is treated as an error.

## HTML Rendering Design

### Segment structure

Each segment renders as:

```html
<section class="segment">
  ...
</section>
```

No `aria-label` is added to the section.

### Item structure

Text cards render escaped source text plus escaped braille text.

Math cards render:

- a source container whose inner HTML is the generated MathML markup
- a braille container with escaped braille text

Newline items render as a break node rather than a normal card.

Space items render as normal cards with non-breaking-space display treatment.

### Trust boundary

MathML inserted into the document must come only from the project's own
`latex_to_mathml()` conversion path. The renderer must not accept arbitrary
untrusted raw HTML from document text.

## Internal Classification Rules

Dual view needs to know which items are math cards. The implementation should
classify a segment as math only when that `TranslationResult` originated from
the math translation path, not by guessing from the raw text at render time.

This design requires the dual-view cache to preserve explicit source-kind
metadata per segment. The intended representation is the `DualViewSegment`
descriptor described above.

Rejected approach:

- infer math segments later by scanning for `$...$` or re-parsing text from the
  document editor

The exact representation is an implementation detail, but the spec requires
math-vs-text origin to be preserved explicitly.

## Testing

Add or update tests for:

- multi-character raw elements render as one card with one braille slice
- single-character space elements render as dedicated space cards
- single-character newline elements render as line-break nodes
- multi-character raw elements containing embedded spaces remain one card
- math cards render MathML markup in the source area
- segment `<section>` output no longer includes `aria-label`
- invalid range validation still raises clear errors

Also update GUI-flow coverage as needed to confirm the dual-view refresh path
continues to use the latest cached conversion output.

## Risks and Constraints

- Existing tests and comments still describe the model as character-level. Those
  expectations must be updated together.
- Math source rendering introduces a new dual-view dependency on explicit
  segment-origin metadata.
- Some WebView backends may differ in MathML rendering quality; this spec only
  requires that the generated HTML contain real MathML DOM markup.
- Because no finer alignment exists for atomic multi-character elements, the UI
  must not imply per-character mappings.

## Acceptance Criteria

- A `raw` element maps to one dual-view card by default.
- Multi-character text tokens no longer show `∅` cards for trailing characters.
- A single raw space element renders as a space card.
- A single raw newline element renders as a line break.
- A multi-character raw element remains one card even if its text contains
  spaces or newlines.
- Each `TranslationResult` still renders inside one `<section class="segment">`.
- Segment sections no longer include `aria-label`.
- Math cards display MathML-rendered source content above braille output.
- The dual view continues to use the latest successful cached conversion data
  and does not trigger a new conversion by itself.
