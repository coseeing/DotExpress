# Dual-View Braille Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a File > Dual View modeless window that displays source-character-to-braille alignment from each document's latest successful manual conversion.

**Architecture:** Extend the conversion service with a richer result that contains the existing wrapped display string plus untouched, pre-bind `TranslationResult` segments. Store those segments in `BrailleFrame` for the current application session, transform them through pure model/HTML functions, and render the HTML in a dedicated `wx.html2.WebView` child frame. Keep all viewer refreshes explicit: open, successful manual conversion, and document switch.

**Tech Stack:** Python 3, wxPython (`wx.Frame`, `wx.html2.WebView`), `TranslationResult`, stdlib `dataclasses`, `html`, `json`, `unittest`, gettext

---

## File Structure

- Create `client/dual_view/model.py`: immutable dual-view data types and source-character-centric alignment construction.
- Create `client/dual_view/html.py`: pure HTML document renderer with inline CSS and safe escaping.
- Create `client/dual_view/__init__.py`: public exports for the dual-view package.
- Create `client/ui/dual_view.py`: modeless `DualViewFrame` and `wx.html2.WebView` lifecycle.
- Create `client/tests/test_dual_view_model.py`: alignment mapping tests.
- Create `client/tests/test_dual_view_html.py`: HTML rendering and escaping tests.
- Create `client/tests/test_dual_view_frame.py`: WebView loading and close lifecycle tests using wx stubs.
- Modify `client/conversion/service.py`: preserve unbound translation segments and return them with existing output.
- Modify `client/tests/test_conversion_service.py`: prove segments remain character-level and existing output remains unchanged.
- Modify `client/ui/action_menu.py`: add the `Dual View` File-menu descriptor and enabled state.
- Modify `client/tests/test_action_menu.py`: lock menu order, action key, and enabled state.
- Modify `client/gui.py`: own the viewer, cache results by document, and connect the three refresh events.
- Modify `client/tests/test_gui_document_flows.py`: test open/reopen, conversion, switching, activation, rename/delete, and no edit-time refresh.
- Modify `client/locales/dotexpress.pot`: add extracted viewer strings.
- Modify `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`: add Traditional Chinese translations.
- Regenerate `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`: compile updated translations.

The alignment cache is intentionally session-only. Do not change `Document` or the `.dep` package format: packages currently contain final source/braille files but not the table, dictionary, and conversion settings needed to guarantee that persisted mappings still describe the final output.

### Task 1: Preserve Pre-Bind Translation Segments

**Files:**
- Modify: `client/conversion/service.py`
- Modify: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Write failing tests for segmented translation**

Add imports for `ConversionOutput`, `convert_text_with_alignment`, and `translate_with_language_segments`, then add tests that stub the translation dependencies in the same style as the existing service tests:

```python
def test_translate_with_language_segments_preserves_math_and_text_boundaries(self) -> None:
    from conversion import service

    text_result = self._translation_result(list("ab"), list("⠁⠃"), [0, 1], [0, 1])
    math_result = self._translation_result(["x+1"], list("⠭⠬⠼⠁"), [0, 0, 0, 0], [0])

    with (
        patch.object(service, "_translate_plain_text_segment", return_value=[text_result]),
        patch.object(service, "translate_math_segment", return_value="⠭⠬⠼⠁"),
        patch.object(service, "build_math_translation_result", return_value=math_result),
    ):
        results = service.translate_with_language_segments(
            "table.ctb",
            "ab$x+1$",
            Path("dictionary.csv"),
            {"default": "table.ctb", "math": "Nemeth"},
            Path("bopomofo.csv"),
        )

    self.assertEqual(results, [text_result, math_result])


def test_convert_text_with_alignment_keeps_segments_unbound(self) -> None:
    segment = self._translation_result(list("word"), list("⠺⠕⠗⠙"), [0, 1, 2, 3], [0, 1, 2, 3])
    request = self.request

    with patch("conversion.service.translate_with_language_segments", return_value=[segment]):
        result = convert_text_with_alignment(request, map_char=lambda text, **_kwargs: text)

    self.assertIsInstance(result, ConversionOutput)
    self.assertEqual(result.display_text, "⠺⠕⠗⠙")
    self.assertEqual(result.translation_results[0].raw, list("word"))
    self.assertEqual(result.translation_results[0].raw_to_braille_pos, [0, 1, 2, 3])
```

Add this test helper to construct real `TranslationResult` instances:

```python
def _translation_result(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
    from translate import TranslationResult

    return TranslationResult(raw, braille, braille_to_raw_pos, raw_to_braille_pos)
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_conversion_service.ConversionServiceTest.test_translate_with_language_segments_preserves_math_and_text_boundaries \
  tests.test_conversion_service.ConversionServiceTest.test_convert_text_with_alignment_keeps_segments_unbound -v
```

Expected: errors because `ConversionOutput`, `convert_text_with_alignment`, and `translate_with_language_segments` do not exist.

- [ ] **Step 3: Add the rich conversion result and segmented translation API**

In `client/conversion/service.py`, add:

```python
@dataclass(frozen=True)
class ConversionOutput:
    display_text: str
    translation_results: tuple[object, ...]
```

Change `_translate_plain_text_segment()` to return its `translations` list instead of merging it. Add a merge helper:

```python
def merge_translation_results(translations):
    from translate import TranslationResult

    if not translations:
        return TranslationResult([], [], [], [])
    merged = translations[0]
    for segment in translations[1:]:
        merged = merged + segment
    return merged
```

Extract the body of `translate_with_language()` into a segment-preserving function. Use `extend()` for plain-text results and `append()` for math and inserted boundary-space results:

```python
def translate_with_language_segments(
    table_file: str,
    text: str,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
):
    if text == "":
        return []

    translations = []
    segments = parse_inline_math_segments(text)
    math_braille_code = translation_tables.get("math", DEFAULT_MATH_BRAILLE_TABLE)
    for index, segment in enumerate(segments):
        if index > 0 and _segment_needs_boundary_space(segments[index - 1], segment):
            translations.append(build_braille_space_translation_result())
        if segment["type"] == "text":
            translations.extend(
                _translate_plain_text_segment(
                    table_file,
                    segment["text"],
                    dictionary_path,
                    translation_tables,
                    bopomofo_path,
                )
            )
        else:
            translations.append(
                build_math_translation_result(
                    segment["text"],
                    translate_math_segment(segment["text"], braille_code=math_braille_code),
                )
            )
    return translations


def translate_with_language(
    table_file: str,
    text: str,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
):
    return merge_translation_results(
        translate_with_language_segments(
            table_file,
            text,
            dictionary_path,
            translation_tables,
            bopomofo_path,
        )
    )
```

Add a helper that wraps a newly merged result, leaving the original segments untouched:

```python
def _wrap_translation_results(translations, width: int) -> tuple[str, str]:
    translation_result = merge_translation_results(translations)
    translation_result.reclean_braille_endspace()
    translation_result.bind_word_tokens()
    translation_result.reclean_token()
    return translation_result.wrap(width)
```

Implement the richer conversion API and keep the old string API as a compatibility wrapper:

```python
def convert_text_with_alignment(
    request: ConversionRequest,
    *,
    map_char: MapChar = translate__mapping_char,
) -> ConversionOutput:
    if request.raw_text == "":
        return ConversionOutput("", ())
    try:
        text = map_char(
            request.raw_text,
            dictionary_path=request.data_dir / "BopomofoChar2Braille.csv",
            from_field="Bopomofo",
            to_field="Braille",
        )
        translations = translate_with_language_segments(
            request.table_file,
            text,
            request.dictionary_path,
            request.translation_tables,
            request.data_dir / "Bopomofo2Braille.csv",
        )
        braille_wrapped, _text_wrapped = _wrap_translation_results(translations, request.width)
    except Exception as error:
        raise ConversionStageError("translation", error) from error

    display_text = braille_wrapped
    if request.output_mode == "ascii":
        try:
            display_text = map_char(
                braille_wrapped,
                dictionary_path=request.data_dir / "Braille2Ascii.csv",
                from_field="Braille",
                to_field="Ascii",
            )
        except Exception as error:
            raise ConversionStageError("ascii", error) from error
    return ConversionOutput(display_text, tuple(translations))
```

Preserve `convert_text_for_output()` and its injectable `wrap_both` behavior for existing callers/tests. Update its default path to call `convert_text_with_alignment(request, map_char=map_char).display_text`; retain the current body when a non-default `wrap_both` is supplied. This avoids breaking current focused tests while making production conversion use one translation pass.

- [ ] **Step 4: Run all conversion service tests**

Run:

```bash
cd client
python3 -m unittest tests.test_conversion_service -v
```

Expected: all tests pass, including existing output-mode and failure-stage tests.

- [ ] **Step 5: Commit the conversion contract**

```bash
git add client/conversion/service.py client/tests/test_conversion_service.py
git commit -m "feat: preserve translation alignment segments"
```

### Task 2: Build the Character-Level View Model

**Files:**
- Create: `client/dual_view/__init__.py`
- Create: `client/dual_view/model.py`
- Create: `client/tests/test_dual_view_model.py`

- [ ] **Step 1: Write failing model tests**

Create `client/tests/test_dual_view_model.py`:

```python
import unittest

from dual_view.model import build_dual_view_model
from translate import TranslationResult


class DualViewModelTest(unittest.TestCase):
    def result(self, raw, braille, raw_positions):
        return TranslationResult(
            list(raw),
            list(braille),
            [0] * len(braille),
            raw_positions,
        )

    def test_builds_one_item_per_source_character(self):
        model = build_dual_view_model([self.result("ab", "⠁⠃", [0, 1])])

        self.assertEqual([item.raw_char for item in model.segments[0].items], ["a", "b"])
        self.assertEqual([item.braille_text for item in model.segments[0].items], ["⠁", "⠃"])

    def test_preserves_segment_boundaries(self):
        model = build_dual_view_model([
            self.result("a", "⠁", [0]),
            self.result("b", "⠃", [0]),
        ])

        self.assertEqual(len(model.segments), 2)
        self.assertEqual([segment.source_text for segment in model.segments], ["a", "b"])

    def test_supports_multiple_and_empty_braille_ranges(self):
        model = build_dual_view_model([self.result("abc", "⠁⠂⠉", [0, 2, 2])])

        items = model.segments[0].items
        self.assertEqual(items[0].braille_text, "⠁⠂")
        self.assertEqual(items[1].braille_text, "")
        self.assertEqual(items[2].braille_text, "⠉")

    def test_keeps_spaces_and_newlines_as_source_items(self):
        model = build_dual_view_model([self.result("a \nb", "⠁⠀⠃", [0, 1, 2, 2])])

        self.assertEqual([item.raw_char for item in model.segments[0].items], ["a", " ", "\n", "b"])
        self.assertTrue(model.segments[0].items[1].is_space)
        self.assertTrue(model.segments[0].items[2].is_newline)

    def test_expands_an_atomic_multi_character_token_into_character_items(self):
        atomic = TranslationResult(["word"], list("⠺⠕⠗⠙"), [0, 0, 0, 0], [0])

        model = build_dual_view_model([atomic])

        self.assertEqual([item.raw_char for item in model.segments[0].items], list("word"))
        self.assertEqual(
            [item.braille_text for item in model.segments[0].items],
            ["⠺⠕⠗⠙", "", "", ""],
        )

    def test_empty_results_produce_empty_document(self):
        self.assertEqual(build_dual_view_model([]).segments, ())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify import failure**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_model -v
```

Expected: error because `dual_view.model` does not exist.

- [ ] **Step 3: Implement immutable model types and mapping**

Create `client/dual_view/model.py`:

```python
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class AlignmentItem:
    raw_index: int
    raw_char: str
    braille_start: int
    braille_end: int
    braille_text: str
    is_space: bool
    is_newline: bool


@dataclass(frozen=True)
class AlignmentSegment:
    source_text: str
    braille_text: str
    items: tuple[AlignmentItem, ...]


@dataclass(frozen=True)
class DualViewModel:
    segments: tuple[AlignmentSegment, ...]


def build_dual_view_model(translation_results: Iterable[object]) -> DualViewModel:
    segments = []
    for result in translation_results:
        raw_tokens = list(result.raw)
        braille = list(result.braille)
        starts = list(result.raw_to_braille_pos)
        if len(starts) != len(raw_tokens):
            raise ValueError("raw_to_braille_pos must contain one entry per raw token")
        items = []
        raw_index = 0
        for token_index, raw_token in enumerate(raw_tokens):
            start = starts[token_index]
            end = starts[token_index + 1] if token_index + 1 < len(starts) else len(braille)
            if start < 0 or end < start or end > len(braille):
                raise ValueError("invalid raw-to-braille alignment range")
            for character_index, raw_char in enumerate(raw_token):
                character_start = start if character_index == 0 else end
                items.append(
                    AlignmentItem(
                        raw_index=raw_index,
                        raw_char=raw_char,
                        braille_start=character_start,
                        braille_end=end,
                        braille_text="".join(braille[character_start:end]),
                        is_space=raw_char.isspace() and raw_char != "\n",
                        is_newline=raw_char == "\n",
                    )
                )
                raw_index += 1
        segments.append(
            AlignmentSegment(
                source_text="".join(raw_tokens),
                braille_text="".join(braille),
                items=tuple(items),
            )
        )
    return DualViewModel(tuple(segments))
```

Create `client/dual_view/__init__.py`:

```python
from dual_view.model import DualViewModel, build_dual_view_model

__all__ = ["DualViewModel", "build_dual_view_model"]
```

- [ ] **Step 4: Run model tests**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_model -v
```

Expected: 6 tests pass. Atomic dictionary replacements and math segments still produce exactly one UI item per source character; because their translators expose only token-level mapping, the complete braille fragment belongs to the first character and the remaining characters have empty ranges.

- [ ] **Step 5: Commit the model**

```bash
git add client/dual_view client/tests/test_dual_view_model.py
git commit -m "feat: build dual view alignment model"
```

### Task 3: Render Accessible, Escaped HTML

**Files:**
- Create: `client/dual_view/html.py`
- Create: `client/tests/test_dual_view_html.py`

- [ ] **Step 1: Write failing renderer tests**

Create `client/tests/test_dual_view_html.py`:

```python
import unittest

from dual_view.html import render_dual_view_html
from dual_view.model import build_dual_view_model
from translate import TranslationResult


class DualViewHtmlTest(unittest.TestCase):
    def render(self, raw, braille, positions):
        result = TranslationResult(list(raw), list(braille), [0] * len(braille), positions)
        return render_dual_view_html(build_dual_view_model([result]))

    def test_renders_source_above_braille(self):
        output = self.render("a", "⠁", [0])

        self.assertIn('<span class="source">a</span>', output)
        self.assertIn('<span class="braille">⠁</span>', output)

    def test_escapes_source_and_metadata(self):
        output = self.render("<", "⠣", [0])

        self.assertIn("&lt;", output)
        self.assertNotIn('<span class="source"><</span>', output)

    def test_renders_space_and_newline_semantics(self):
        output = self.render(" \n", "⠀", [0, 1])

        self.assertIn('class="cell space"', output)
        self.assertIn('class="line-break"', output)

    def test_renders_empty_state(self):
        output = render_dual_view_html(build_dual_view_model([]))

        self.assertIn("No conversion data is available", output)
```

- [ ] **Step 2: Run the tests and verify import failure**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_html -v
```

Expected: error because `dual_view.html` does not exist.

- [ ] **Step 3: Implement a complete inline HTML document renderer**

Create `client/dual_view/html.py`. Use `html.escape(..., quote=True)` for visible text and `json.dumps()` followed by HTML escaping for metadata. Render newline items as block breaks and other items as cards:

```python
import html
import json

from dual_view.model import DualViewModel


def _render_item(item) -> str:
    if item.is_newline:
        return '<span class="line-break" role="separator"></span>'
    classes = "cell space" if item.is_space else "cell"
    source = "&nbsp;" if item.is_space else html.escape(item.raw_char, quote=True)
    braille = html.escape(item.braille_text, quote=True) or '<span class="empty">∅</span>'
    metadata = html.escape(
        json.dumps(
            {
                "raw_index": item.raw_index,
                "braille_start": item.braille_start,
                "braille_end": item.braille_end,
            },
            ensure_ascii=False,
        ),
        quote=True,
    )
    return (
        f'<span class="{classes}" data-alignment="{metadata}">'
        f'<span class="source">{source}</span>'
        f'<span class="braille">{braille}</span>'
        "</span>"
    )


def render_dual_view_html(model: DualViewModel) -> str:
    if model.segments:
        body = "".join(
            '<section class="segment" aria-label="Translation segment">'
            + "".join(_render_item(item) for item in segment.items)
            + "</section>"
            for segment in model.segments
        )
    else:
        body = '<p class="empty-state">No conversion data is available for this document.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ color-scheme: light dark; font-family: "Noto Sans", sans-serif; }}
body {{ margin: 0; padding: 1rem; background: #f5f1e8; color: #17201d; }}
.segment {{ display: flex; flex-wrap: wrap; align-items: flex-start; gap: .35rem;
  margin: 0 0 .8rem; padding: .75rem; border-left: .3rem solid #b94b2f; background: #fffdf8; }}
.cell {{ display: inline-grid; grid-template-rows: auto auto; min-width: 2rem; text-align: center;
  border: 1px solid #d7cdbb; border-radius: .25rem; overflow: hidden; }}
.source, .braille {{ padding: .25rem .4rem; }}
.source {{ font-size: 1rem; background: #eee6d7; }}
.braille {{ font-family: "SimBraille", "Noto Sans Symbols 2", sans-serif; font-size: 1.35rem; }}
.space .source {{ min-width: 1.25rem; }}
.line-break {{ flex-basis: 100%; height: 0; }}
.empty {{ color: #777; font-size: .85rem; }}
.empty-state {{ max-width: 34rem; padding: 1rem; border: 1px dashed #8b8172; }}
@media (prefers-color-scheme: dark) {{
  body {{ background: #1c211f; color: #f4efe5; }}
  .segment {{ background: #252c29; border-color: #e17856; }}
  .cell {{ border-color: #59625e; }}
  .source {{ background: #343c38; }}
}}
</style>
</head>
<body><main class="document">{body}</main></body>
</html>"""
```

- [ ] **Step 4: Run renderer tests**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_html -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit the renderer**

```bash
git add client/dual_view/html.py client/tests/test_dual_view_html.py
git commit -m "feat: render dual view alignment html"
```

### Task 4: Add the Modeless WebView Window

**Files:**
- Create: `client/ui/dual_view.py`
- Create: `client/tests/test_dual_view_frame.py`
- Modify: `client/tests/test_gui_document_flows.py` (wx stub setup only)

- [ ] **Step 1: Extend test wx stubs and write failing frame tests**

In both GUI-oriented test modules, register `wx.html2` before importing production code:

```python
wx_html2 = types.ModuleType("wx.html2")
wx_html2.WebView = type(
    "WebView",
    (),
    {"New": staticmethod(lambda parent: Mock())},
)
wx.html2 = wx_html2
sys.modules["wx.html2"] = wx_html2
```

Create `client/tests/test_dual_view_frame.py`:

```python
import unittest
from unittest.mock import Mock, patch

from ui.dual_view import DualViewFrame


class DualViewFrameTest(unittest.TestCase):
    def test_refresh_loads_complete_html(self):
        frame = DualViewFrame.__new__(DualViewFrame)
        frame.web_view = Mock()

        frame.refresh_html("<html>alignment</html>")

        frame.web_view.SetPage.assert_called_once_with("<html>alignment</html>", "")

    def test_close_notifies_owner_and_destroys(self):
        owner = Mock()
        event = Mock()
        frame = DualViewFrame.__new__(DualViewFrame)
        frame._on_closed = owner
        frame.Destroy = Mock()

        frame._handle_close(event)

        owner.assert_called_once_with(frame)
        frame.Destroy.assert_called_once_with()
        event.Skip.assert_not_called()
```

- [ ] **Step 2: Run the frame tests and verify failure**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_frame -v
```

Expected: error because `ui.dual_view` does not exist.

- [ ] **Step 3: Implement the viewer frame**

Create `client/ui/dual_view.py`:

```python
from collections.abc import Callable

import wx
import wx.html2


class DualViewFrame(wx.Frame):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        on_closed: Callable[["DualViewFrame"], None],
    ):
        super().__init__(parent, title=title, size=(900, 650))
        self._on_closed = on_closed
        self.web_view = wx.html2.WebView.New(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.web_view, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, self._handle_close)

    def refresh_html(self, content: str) -> None:
        self.web_view.SetPage(content, "")

    def _handle_close(self, _event: wx.CloseEvent) -> None:
        self._on_closed(self)
        self.Destroy()
```

Do not use `wx.STAY_ON_TOP`; the parent relationship and explicit `Raise()` behavior in Task 6 provide application-relative foreground behavior.

- [ ] **Step 4: Run frame and existing GUI-flow tests**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_frame tests.test_gui_document_flows -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit the frame**

```bash
git add client/ui/dual_view.py client/tests/test_dual_view_frame.py client/tests/test_gui_document_flows.py
git commit -m "feat: add dual view webview frame"
```

### Task 5: Add the File Menu Command

**Files:**
- Modify: `client/ui/action_menu.py`
- Modify: `client/tests/test_action_menu.py`
- Modify: `client/gui.py`

- [ ] **Step 1: Update menu tests first**

Change expected menu descriptors to include `Dual View` after `Open`:

```python
("command", "Open"),
("command", "Dual View"),
("command", "Delete"),
```

Change the expected action-key list to include `"dual_view"` after `"open"`. Add `"Dual View": True` to every expected enabled-state dictionary because the viewer must remain available even when no document is selected.

- [ ] **Step 2: Run menu tests and verify failure**

Run:

```bash
cd client
python3 -m unittest tests.test_action_menu -v
```

Expected: failures showing the missing descriptor/action/enabled state.

- [ ] **Step 3: Add the descriptor and binding**

In `client/ui/action_menu.py`, insert:

```python
DocumentMenuItem("command", "Dual View", "dual_view"),
```

after `Open`, and add:

```python
"Dual View": True,
```

to `get_document_menu_enabled_state()`.

In `BrailleFrame._bind_document_menu_handlers()`, add:

```python
menu.Bind(wx.EVT_MENU, self.on_open_dual_view, menu_items["Dual View"])
```

The handler itself is implemented in Task 6. For this task's isolated test run, add a minimal method that delegates to `_show_dual_view()`:

```python
def on_open_dual_view(self, _evt) -> None:
    self._show_dual_view()
```

- [ ] **Step 4: Run menu tests**

Run:

```bash
cd client
python3 -m unittest tests.test_action_menu -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit the menu**

```bash
git add client/ui/action_menu.py client/tests/test_action_menu.py client/gui.py
git commit -m "feat: add dual view file menu command"
```

### Task 6: Integrate Viewer State, Refresh Events, and Foreground Behavior

**Files:**
- Modify: `client/gui.py`
- Modify: `client/tests/test_gui_document_flows.py`

- [ ] **Step 1: Add failing viewer lifecycle and refresh tests**

Extend `_make_frame()` with:

```python
frame._dual_view_frame = None
frame._dual_view_results_by_document = {}
frame._open_document_name = "alpha"
```

Add focused tests:

```python
def test_open_dual_view_creates_refreshes_and_shows_viewer(self):
    frame = self._make_frame()
    frame._dual_view_results_by_document["alpha"] = ("segment",)
    viewer = Mock()
    frame._create_dual_view_frame = Mock(return_value=viewer)
    frame._render_dual_view_for_open_document = Mock(return_value="<html>alpha</html>")

    frame._show_dual_view()

    viewer.refresh_html.assert_called_once_with("<html>alpha</html>")
    viewer.Show.assert_called_once_with()
    viewer.Raise.assert_called_once_with()

def test_open_existing_dual_view_reuses_and_refreshes_it(self):
    frame = self._make_frame()
    viewer = Mock()
    frame._dual_view_frame = viewer
    frame._create_dual_view_frame = Mock()
    frame._render_dual_view_for_open_document = Mock(return_value="<html>new</html>")

    frame._show_dual_view()

    frame._create_dual_view_frame.assert_not_called()
    viewer.refresh_html.assert_called_once_with("<html>new</html>")
    viewer.Raise.assert_called_once_with()

def test_successful_manual_conversion_stores_segments_and_refreshes_open_viewer(self):
    frame = self._make_frame()
    frame._convert_update_output = True
    frame._convert_output = gui.ConversionOutput("braille", ("segment",))
    frame._dual_view_frame = Mock()
    frame._refresh_dual_view = Mock()

    with patch.object(gui.wx, "MessageBox"):
        frame._finish_conversion(1, conversion_output=frame._convert_output)

    self.assertEqual(frame._dual_view_results_by_document["alpha"], ("segment",))
    frame._refresh_dual_view.assert_called_once_with()

def test_export_conversion_does_not_replace_dual_view_cache(self):
    frame = self._make_frame()
    frame._convert_update_output = False
    frame._dual_view_results_by_document["alpha"] = ("manual",)
    output = gui.ConversionOutput("export", ("export-segment",))

    frame._finish_conversion(1, conversion_output=output)

    self.assertEqual(frame._dual_view_results_by_document["alpha"], ("manual",))

def test_open_document_refreshes_viewer_but_text_edit_does_not(self):
    frame = self._make_frame()
    frame.documents = [Document("beta", "new text", "braille")]
    frame._dual_view_frame = Mock()
    frame._refresh_dual_view = Mock()
    frame._load_document_into_editors = Mock()
    frame._refresh_document_list = Mock()
    frame._update_window_title = Mock()

    frame._open_document_by_name("beta")

    frame._refresh_dual_view.assert_called_once_with()
    self.assertFalse(hasattr(frame, "on_dual_view_text_changed"))

def test_activate_raises_visible_non_iconized_viewer(self):
    frame = self._make_frame()
    frame._dual_view_frame = Mock()
    frame._dual_view_frame.IsShown.return_value = True
    frame._dual_view_frame.IsIconized.return_value = False
    event = Mock()
    event.GetActive.return_value = True

    frame.on_frame_activate(event)

    frame._dual_view_frame.Raise.assert_called_once_with()
    event.Skip.assert_called_once_with()

def test_rename_and_delete_keep_alignment_cache_consistent(self):
    frame = self._make_frame()
    frame._dual_view_results_by_document = {"alpha": ("segment",)}

    frame._rename_dual_view_result("alpha", "renamed")
    frame._delete_dual_view_result("renamed")

    self.assertEqual(frame._dual_view_results_by_document, {})
```

- [ ] **Step 2: Run focused GUI tests and verify failure**

Run:

```bash
cd client
python3 -m unittest tests.test_gui_document_flows -v
```

Expected: failures for missing conversion-output state and dual-view lifecycle methods.

- [ ] **Step 3: Initialize and render viewer state**

Import the new APIs in `client/gui.py`:

```python
from conversion.service import (
    ConversionOutput,
    ConversionRequest,
    ConversionStageError,
    convert_text_with_alignment,
    get_public_error_message,
)
from dual_view.html import render_dual_view_html
from dual_view.model import build_dual_view_model
from ui.dual_view import DualViewFrame
```

In `_initialize_state()` add:

```python
self._dual_view_frame = None
self._dual_view_results_by_document: dict[str, tuple[object, ...]] = {}
```

Add lifecycle/render helpers:

```python
def _create_dual_view_frame(self) -> DualViewFrame:
    return DualViewFrame(
        self,
        title=_("Dual View"),
        on_closed=self._on_dual_view_closed,
    )

def _on_dual_view_closed(self, viewer: DualViewFrame) -> None:
    if self._dual_view_frame is viewer:
        self._dual_view_frame = None

def _render_dual_view_for_open_document(self) -> str:
    results = self._dual_view_results_by_document.get(self._open_document_name or "", ())
    return render_dual_view_html(build_dual_view_model(results))

def _refresh_dual_view(self) -> None:
    if self._dual_view_frame is not None:
        self._dual_view_frame.refresh_html(self._render_dual_view_for_open_document())

def _show_dual_view(self) -> None:
    if self._dual_view_frame is None:
        self._dual_view_frame = self._create_dual_view_frame()
    self._refresh_dual_view()
    self._dual_view_frame.Show()
    if self._dual_view_frame.IsIconized():
        self._dual_view_frame.Iconize(False)
    self._dual_view_frame.Raise()

def _rename_dual_view_result(self, old_name: str, new_name: str) -> None:
    if old_name in self._dual_view_results_by_document:
        self._dual_view_results_by_document[new_name] = self._dual_view_results_by_document.pop(old_name)

def _delete_dual_view_result(self, name: str) -> None:
    self._dual_view_results_by_document.pop(name, None)
```

- [ ] **Step 4: Return rich conversion output through the worker**

In `_run_conversion()`, replace the string call with:

```python
conversion_output = convert_text_with_alignment(
    self._build_conversion_request(raw_text, table_file, output_mode, width, dictionary_path)
)
```

Then schedule:

```python
wx.CallAfter(self._finish_conversion, job_id, conversion_output=conversion_output)
```

Change `_finish_conversion()` to accept:

```python
def _finish_conversion(
    self,
    job_id: int,
    conversion_output: ConversionOutput | None = None,
    error_message: str | None = None,
):
```

After the error branch, derive the existing callback value and update only manual-conversion cache entries:

```python
output = conversion_output or ConversionOutput("", ())
converted_braille = output.display_text
if update_output:
    self.output_txt.SetValue(converted_braille)
    self.output_txt.SetFocus()
    if self._open_document_name:
        self._dual_view_results_by_document[self._open_document_name] = output.translation_results
    self._refresh_dual_view()
```

Keep callbacks receiving `converted_braille` strings so export behavior remains API-compatible.

- [ ] **Step 5: Connect document, activation, rename, delete, and close events**

Bind main-frame activation:

```python
self.Bind(wx.EVT_ACTIVATE, self.on_frame_activate)
```

Add:

```python
def on_frame_activate(self, event: wx.ActivateEvent) -> None:
    viewer = self._dual_view_frame
    if event.GetActive() and viewer is not None and viewer.IsShown() and not viewer.IsIconized():
        viewer.Raise()
    event.Skip()
```

At both exits of `_open_document_by_name()`, call `_refresh_dual_view()` after updating the editors/title. Do not bind `EVT_TEXT` to any dual-view refresh method.

After a successful rename, call:

```python
self._rename_dual_view_result(selected_document.name, renamed_document.name)
```

After successful single delete, call:

```python
self._delete_dual_view_result(selected_document.name)
```

After successful delete-all, call:

```python
self._dual_view_results_by_document.clear()
```

In `_on_close()`, destroy an open viewer before skipping the close event:

```python
if self._dual_view_frame is not None:
    viewer = self._dual_view_frame
    self._dual_view_frame = None
    viewer.Destroy()
```

- [ ] **Step 6: Run GUI-flow and conversion regression tests**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_gui_document_flows \
  tests.test_conversion_service \
  tests.test_action_menu \
  tests.test_dual_view_frame \
  tests.test_dual_view_model \
  tests.test_dual_view_html -v
```

Expected: all tests pass. Existing export callbacks still receive strings, manual conversion still updates/focuses the output editor, and source editing has no viewer refresh hook.

- [ ] **Step 7: Commit GUI integration**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py
git commit -m "feat: integrate dual view document lifecycle"
```

### Task 7: Localize User-Visible Viewer Text

**Files:**
- Modify: `client/dual_view/html.py`
- Modify: `client/gui.py`
- Modify: `client/locales/dotexpress.pot`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`
- Modify: `client/tests/test_dual_view_html.py`

- [ ] **Step 1: Make HTML labels injectable and add a failing localization test**

Change the renderer signature expected by the test:

```python
output = render_dual_view_html(
    build_dual_view_model([]),
    empty_message="此文件沒有可顯示的轉換資料。",
    segment_label="轉譯區段",
)
self.assertIn("此文件沒有可顯示的轉換資料。", output)
```

- [ ] **Step 2: Run the renderer test and verify failure**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_html -v
```

Expected: failure because the renderer does not accept localized labels.

- [ ] **Step 3: Inject translated strings from the GUI layer**

Change the renderer definition to:

```python
def render_dual_view_html(
    model: DualViewModel,
    *,
    empty_message: str = "No conversion data is available for this document.",
    segment_label: str = "Translation segment",
) -> str:
```

Escape both arguments before placing them in HTML. In `_render_dual_view_for_open_document()`, pass:

```python
return render_dual_view_html(
    build_dual_view_model(results),
    empty_message=_("No conversion data is available for this document."),
    segment_label=_("Translation segment"),
)
```

- [ ] **Step 4: Update gettext source and Traditional Chinese catalog**

Ensure these msgids exist in `client/locales/dotexpress.pot`:

```po
msgid "Dual View"
msgstr ""

msgid "No conversion data is available for this document."
msgstr ""

msgid "Translation segment"
msgstr ""
```

Add matching entries to `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`:

```po
msgid "Dual View"
msgstr "雙視檢視"

msgid "No conversion data is available for this document."
msgstr "此文件沒有可顯示的轉換資料。"

msgid "Translation segment"
msgstr "轉譯區段"
```

Compile it with the repository's gettext tool on Windows:

```bat
cd client
msgfmt locales\zh_TW\LC_MESSAGES\dotexpress.po -o locales\zh_TW\LC_MESSAGES\dotexpress.mo
```

Validate the rebuilt catalog:

```bash
cd client
python3 -c 'import gettext; gettext.GNUTranslations(open("locales/zh_TW/LC_MESSAGES/dotexpress.mo", "rb"))'
```

Expected result: exit code 0 with no output.

- [ ] **Step 5: Run localization-sensitive tests**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_html tests.test_action_menu tests.test_gui_document_flows -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit localization**

```bash
git add \
  client/dual_view/html.py \
  client/gui.py \
  client/tests/test_dual_view_html.py \
  client/locales/dotexpress.pot \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "feat: localize dual view"
```

### Task 8: Full Verification and Windows Smoke Test

**Files:**
- Verify only; no planned source changes.

- [ ] **Step 1: Run the complete client unit-test suite**

Run:

```bash
cd client
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all platform-compatible tests pass; Windows-only liblouis tests may skip on non-Windows as documented in `AGENTS.md`.

- [ ] **Step 2: Verify no unintended persistence-format change**

Run:

```bash
git diff HEAD~6 -- client/documents/workspace.py
```

Expected: no output. The `.dep` format remains unchanged.

- [ ] **Step 3: Perform a Windows GUI smoke test**

Run DotExpress on Windows and verify:

1. `File > Dual View` opens one modeless, resizable, closable window.
2. Re-selecting the command reuses, refreshes, restores, and raises the existing window.
3. The window shows source characters above their braille fragments, including spaces, line breaks, math, and dictionary replacements.
4. Manual conversion refreshes an open viewer.
5. Editing source text alone does not refresh it.
6. Opening another document switches to that document's cached alignment or the empty state.
7. Returning focus to DotExpress raises the non-minimized viewer above the main frame.
8. Switching to another application leaves that application above both DotExpress windows.
9. Export conversion does not replace the current document's viewer cache.
10. Existing braille result display and DEP/BRL exports remain unchanged.

- [ ] **Step 4: Inspect final working tree and commit history**

Run:

```bash
git status --short
git log --oneline -8
```

Expected: only pre-existing unrelated files remain untracked/modified, and the feature is represented by focused commits from Tasks 1-7.
