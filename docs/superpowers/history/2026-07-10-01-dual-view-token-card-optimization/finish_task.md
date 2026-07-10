# Dual View Token Card Optimization — Completion Notes

Date: 2026-07-10

## Commit List

```
6f9f64f fix: remove Translation segment from localization artifacts
54617ae fix: render math cards with MathML and remove segment aria-label
a533f5f fix: switch dual view to raw-element cards
516eac3 feat: add dual-view segment metadata contract
```

## What Was Implemented

### 1. Dual-View Segment Metadata Contract (516eac3)
- Added `DualViewSegment(result, source_kind)` frozen dataclass in `client/dual_view/model.py`
- Extended `ConversionOutput` with `dual_view_segments` field (default `()`)
- Added `translate_with_language_dual_view_segments()` that tags each `TranslationResult` with `"text"` or `"math"` origin
- Refactored `translate_with_language_segments()` to delegate to the new helper (preserves existing API)
- Updated `convert_text_with_alignment()` to populate `dual_view_segments`
- 5 new conversion service tests

### 2. Raw-Element Cards Model (a533f5f)
- `AlignmentItem` fields changed from character-level (`raw_char`) to raw-element-level (`raw_text`, `source_kind`, `source_html`)
- `build_dual_view_model()` accepts `DualViewSegment` descriptors, creates one card per raw element
- `is_space` only when `raw_text == " "`, `is_newline` only when `raw_text == "\n"`
- Embedded spaces/newlines inside longer strings stay in one card
- Injectable `mathml_converter` parameter (defaults to `latex_to_mathml()`)
- `gui.py` stores `dual_view_segments` in cache
- 12 model tests (6 new raw-element tests + 6 updated)

### 3. HTML Rendering & GUI Wiring (54617ae)
- Math cards render MathML DOM output unescaped in source area
- Text cards continue to escape source text
- Removed `segment_label` parameter from `_render_segment()` and `render_dual_view_html()`
- `<section class="segment">` no longer carries `aria-label`
- `gui.py` no longer passes `segment_label=_("Translation segment")`
- 10 HTML tests (5 updated + 5 new for MathML and absence of aria-label)

### 4. Localization (6f9f64f)
- Removed `_("Translation segment")` from gui.py translation marker tuple
- Removed active `msgid "Translation segment"` from `.pot`
- Marked entry as obsolete `#~` in `.po`
- `.mo` regeneration deferred (requires `gettext` tools on Windows build)

## Test Results

All 82 focused tests pass:
- `test_conversion_service`: 19/19 (14 old + 5 new)
- `test_dual_view_model`: 12/12 (6 new + 6 updated)
- `test_dual_view_html`: 10/10 (5 updated + 5 new)
- `test_gui_document_flows`: 35/35 (all pass)
- `test_dual_view_frame`: 6/7 pass (1 pre-existing error in `test_initial_geometry_matches_parent` — unrelated `TypeError: 'function' object is not subscriptable`)

## Key Design Decisions

1. **`dual_view_segments` typing**: Uses `tuple[object, ...]` rather than `tuple[DualViewSegment, ...]` to avoid circular imports between `conversion/output.py` and `dual_view/model.py`.
2. **MathML trust boundary**: Math source HTML injected from `latex_to_mathml()` is treated as trusted (not escaped); text content continues through `html.escape`.
3. **Card granularity**: One card per `TranslationResult.raw` element — no per-character expansion, no `∅` cards.

## Deferred Items

- `.mo` file regeneration (requires `msgfmt`/`gettext`; run `scripts/generate_pot.bat` on Windows)
- Stale line references in `.pot`/`.po` after manual edits (auto-corrected on next `xgettext` run)

## Files Changed

12 files, +316/-100 lines:
- `client/dual_view/model.py`, `__init__.py`, `html.py`
- `client/conversion/output.py`, `service.py`
- `client/gui.py`
- `client/locales/dotexpress.pot`, `zh_TW/.../dotexpress.po`
- `client/tests/test_conversion_service.py`, `test_dual_view_model.py`, `test_dual_view_html.py`, `test_gui_document_flows.py`
