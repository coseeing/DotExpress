# Dual View Token Card Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update dual view so each card maps to one `TranslationResult.raw` element, remove segment `aria-label` region naming, and render math source cards as MathML DOM output while preserving the existing conversion output and dual-view refresh lifecycle.

**Architecture:** Keep `TranslationResult` as the source of raw/braille alignment. Add a small dual-view descriptor that pairs each unbound `TranslationResult` with explicit `source_kind` metadata (`text` or `math`). Keep wrapping and final output generation on plain `TranslationResult` objects. Build the dual-view model from descriptors, render one card per raw element, and use the existing `latex_to_mathml()` helper for math card source markup.

**Tech Stack:** Python 3, `dataclasses`, `unittest`, `unittest.mock`, `html`, `json`, gettext tooling (`xgettext`, `msgmerge`, `msgfmt`)

**Specs:**
- `docs/superpowers/specs/2026-07-10-dual-view-token-card-optimization-design.md`
- `docs/superpowers/specs/2026-07-10-dual-view-token-card-optimization-design_zh-TW.md`

---

## File Structure

- Modify `client/dual_view/model.py`: add dual-view segment metadata and switch model items from character-level to raw-element-level.
- Modify `client/dual_view/html.py`: render raw-element cards, remove segment `aria-label`, and render MathML source markup for math cards.
- Modify `client/dual_view/__init__.py`: export any new public dual-view model types needed by callers/tests.
- Modify `client/conversion/output.py`: let `ConversionOutput` carry dual-view segment descriptors without changing wrapped display output behavior.
- Modify `client/conversion/service.py`: preserve text-vs-math segment origin while translating, and pass descriptor data into `ConversionOutput`.
- Modify `client/gui.py`: cache dual-view descriptors and stop passing localized segment labels to the HTML renderer.
- Modify `client/tests/test_dual_view_model.py`: replace character-card expectations with raw-element-card expectations.
- Modify `client/tests/test_dual_view_html.py`: assert section labels are removed and MathML markup renders.
- Modify `client/tests/test_conversion_service.py`: assert conversion output carries text/math dual-view descriptors while raw translation results remain available.
- Modify `client/tests/test_gui_document_flows.py`: adjust dual-view cache expectations for descriptor payloads.
- Modify `client/locales/dotexpress.pot`: remove the no-longer-used `Translation segment` extraction.
- Modify `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`: merge catalog changes.
- Regenerate `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`.

No document package format changes are planned.

## Task 1: Add The Dual-View Segment Metadata Contract

**Files:**
- Modify: `client/dual_view/model.py`
- Modify: `client/dual_view/__init__.py`
- Modify: `client/conversion/output.py`
- Modify: `client/conversion/service.py`
- Modify: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Add failing conversion metadata tests**

Add focused tests proving:

- `convert_text_with_alignment()` still exposes plain unbound `TranslationResult` objects for existing alignment output behavior.
- `convert_text_with_alignment()` also exposes dual-view descriptors with `source_kind == "text"` for plain text segments.
- math segments are exposed with `source_kind == "math"`.
- inserted boundary spaces are exposed as text descriptors.

Recommended shape:

```python
output = convert_text_with_alignment(request, runtime=self._runtime())
self.assertEqual([segment.source_kind for segment in output.dual_view_segments], ["text", "math"])
self.assertIs(output.translation_results[0], output.dual_view_segments[0].result)
```

- [ ] **Step 2: Add the immutable descriptor**

In `client/dual_view/model.py`, add a pure data descriptor:

```python
@dataclass(frozen=True)
class DualViewSegment:
    result: object
    source_kind: str
```

Validate source kind at model-build time, accepting only `"text"` and `"math"`.

Export it from `client/dual_view/__init__.py`.

- [ ] **Step 3: Extend `ConversionOutput` without breaking existing callers**

In `client/conversion/output.py`, add a third field with a default:

```python
@dataclass(frozen=True)
class ConversionOutput:
    display_text: str
    translation_results: tuple[object, ...]
    dual_view_segments: tuple[object, ...] = ()
```

The default keeps existing two-argument test helpers and fallback construction valid.

- [ ] **Step 4: Preserve segment origin during translation**

In `client/conversion/service.py`, add an internal helper that returns descriptor records while preserving the existing plain-result API:

```python
def translate_with_language_dual_view_segments(...):
    ...
    return [DualViewSegment(result, "text"), DualViewSegment(result, "math")]

def translate_with_language_segments(...):
    return [segment.result for segment in translate_with_language_dual_view_segments(...)]
```

`convert_text_with_alignment()` should wrap `segment.result` values, return those values in `translation_results`, and return the descriptors in `dual_view_segments`.

- [ ] **Step 5: Run focused conversion tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_conversion_service -v
```

Expected: conversion output remains unchanged; new descriptor tests pass.

## Task 2: Switch The Dual-View Model To Raw-Element Cards

**Files:**
- Modify: `client/dual_view/model.py`
- Modify: `client/tests/test_dual_view_model.py`

- [ ] **Step 1: Replace character-level tests with token-card tests**

Update model tests to assert:

- `TranslationResult(["我們", "這", "一家"], ["b1", "b2", "b3"], ..., [0, 1, 2])` produces three cards.
- `TranslationResult(["我們"], list("b1"), ..., [0])` produces one card, not two.
- `TranslationResult([" "], ["⠀"], ..., [0])` produces one `is_space` item.
- `TranslationResult(["\n"], [], ..., [0])` produces one `is_newline` item.
- `TranslationResult(["我們 這 一家"], list("b1"), ..., [0])` remains one card.
- invalid range validation still raises `ValueError`.

- [ ] **Step 2: Update item data fields**

Change `AlignmentItem` from character-oriented fields to raw-element fields. The implementation should expose at least:

```python
raw_index: int
raw_text: str
braille_start: int
braille_end: int
braille_text: str
is_space: bool
is_newline: bool
source_kind: str
source_html: str | None
```

Keep old field names only if doing so materially reduces churn; tests should describe the new raw-element semantics.

- [ ] **Step 3: Build one item per raw element**

Update `build_dual_view_model()` so it:

- accepts `DualViewSegment` descriptors
- reads `result.raw`, `result.braille`, and `result.raw_to_braille_pos`
- creates one `AlignmentItem` per raw element
- marks `is_space` only when `raw_text == " "`
- marks `is_newline` only when `raw_text == "\n"`
- does not split embedded spaces or embedded newlines inside longer strings

- [ ] **Step 4: Add injectable MathML conversion for tests**

Allow the builder to receive a math conversion callable, defaulting to `latex_to_mathml()`:

```python
def build_dual_view_model(segments, *, mathml_converter=latex_to_mathml):
    ...
```

For math items, set `source_html` to `mathml_converter(raw_text)`. For text items, keep `source_html` as `None`.

- [ ] **Step 5: Run model tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_dual_view_model -v
```

Expected: all dual-view model tests pass with raw-element card semantics.

## Task 3: Update HTML Rendering And GUI Wiring

**Files:**
- Modify: `client/dual_view/html.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_dual_view_html.py`
- Modify: `client/tests/test_gui_document_flows.py`

- [ ] **Step 1: Add failing HTML renderer tests**

Update HTML tests to assert:

- source text renders from `item.raw_text`
- embedded source text is escaped for text items
- math items render generated MathML markup in the source area
- generated MathML is not escaped as visible text
- braille text remains escaped
- `<section class="segment">` is present
- `aria-label="Translation segment"` is absent
- `role="region"` is absent

- [ ] **Step 2: Render math source markup**

Update `_render_item()`:

- for newline items, continue rendering the line-break node
- for text items, escape `raw_text`
- for math items, inject `source_html` generated by the trusted MathML converter
- for space items, continue displaying `&nbsp;`
- preserve metadata using escaped JSON

- [ ] **Step 3: Remove segment label plumbing**

Update `_render_segment()` and `render_dual_view_html()` so they no longer accept or use `segment_label`.

Render segments as:

```html
<section class="segment">
```

Update `client/gui.py`:

- remove `segment_label=_("Translation segment")`
- cache `output.dual_view_segments` instead of `output.translation_results`
- keep existing empty-state behavior

- [ ] **Step 4: Update GUI-flow expectations**

Update GUI tests so:

- conversion success stores `dual_view_segments`
- exports do not overwrite the dual-view cache
- rename/delete/all-delete behavior still updates the cache
- opening dual view passes cached descriptors into `build_dual_view_model()`

- [ ] **Step 5: Run dual-view and GUI focused tests**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_dual_view_model \
  tests.test_dual_view_html \
  tests.test_gui_document_flows \
  -v
```

Expected: all focused tests pass.

## Task 4: Update Localization Artifacts

**Files:**
- Modify: `client/gui.py`
- Modify: `client/locales/dotexpress.pot`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

- [ ] **Step 1: Remove the unused marker**

Remove `_("Translation segment")` from the GUI translation marker tuple because the HTML renderer no longer emits a segment label.

Keep `_("No conversion data is available for this document.")`.

- [ ] **Step 2: Regenerate and merge gettext artifacts**

From `client/`, run the Linux-equivalent extraction used by recent localization work:

```bash
xgettext --language=Python --keyword=_ --output=locales/dotexpress.pot braille/tables/__tables.py *.py
sed -i '/^#:/ s|/|\\|g' locales/dotexpress.pot
msgmerge --update --lang=zh_TW --no-fuzzy-matching locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot
msgfmt locales/zh_TW/LC_MESSAGES/dotexpress.po -o locales/zh_TW/LC_MESSAGES/dotexpress.mo
```

- [ ] **Step 3: Verify removed string state**

Confirm `Translation segment` is no longer active in the `.pot`. If it remains only as an obsolete `#~` entry in `.po`, that is acceptable gettext merge behavior.

Run:

```bash
rg -n 'msgid "Translation segment"|#~ msgid "Translation segment"' locales/dotexpress.pot locales/zh_TW/LC_MESSAGES/dotexpress.po
msgfmt --check locales/zh_TW/LC_MESSAGES/dotexpress.po -o /tmp/dotexpress.check.mo
```

Expected: no active `msgid "Translation segment"` in `.pot`; `msgfmt --check` passes.

## Task 5: Final Verification And Diff Review

**Files:**
- All files touched above

- [ ] **Step 1: Run focused test suite**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_conversion_service \
  tests.test_dual_view_model \
  tests.test_dual_view_html \
  tests.test_gui_document_flows \
  tests.test_dual_view_frame \
  -v
```

Expected: all tests pass on the current platform. If a platform-specific wx/liblouis skip occurs, record the exact skip.

- [ ] **Step 2: Inspect source references**

Run:

```bash
rg -n "raw_char|segment_label|Translation segment|dual_view_segments|DualViewSegment" client docs/superpowers
```

Expected:

- `raw_char` should not remain as the active dual-view model field unless deliberately retained for compatibility.
- `segment_label` should not remain in active renderer/GUI code.
- `Translation segment` should not remain as an active gettext marker.
- `dual_view_segments` and `DualViewSegment` should appear in the new conversion/model/cache paths.

- [ ] **Step 3: Review the final diff**

Run:

```bash
git diff -- \
  client/dual_view \
  client/conversion \
  client/gui.py \
  client/tests \
  client/locales \
  docs/superpowers/specs/2026-07-10-dual-view-token-card-optimization-design.md \
  docs/superpowers/specs/2026-07-10-dual-view-token-card-optimization-design_zh-TW.md \
  docs/superpowers/plans/2026-07-10-dual-view-token-card-optimization.md
```

Expected: diff is limited to the dual-view token-card change, math source rendering, metadata plumbing, localization cleanup, and this spec/plan set.

- [ ] **Step 4: Commit if requested**

If committing is part of the task, use a scoped subject:

```bash
git add ...
git commit -m "fix: align dual view cards with translation tokens"
```

Do not include unrelated working-tree changes.
