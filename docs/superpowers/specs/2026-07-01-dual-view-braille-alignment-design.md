# Dual-View Braille Alignment Window Design

## Summary

This change adds a menu-opened "Dual View" floating window to DotExpress for showing character-by-character alignment between source text and the corresponding braille output in the current document. The window uses `wx.html2.WebView` to display HTML content and builds a character-level alignment model from the original `TranslationResult` data produced by the document's most recent successful conversion, before wrapping and before token binding.

The goal of this viewer is to help users inspect how source characters map to braille output, not to replace the existing braille result editor or final output layout. It should therefore use a dedicated viewer data pipeline, separate from the existing `bind_word_tokens()`, `wrap()`, and output-editor display flow.

## Goals

- Add a `Dual View` command under the `File` menu.
- Show a modeless child window with character-by-character source/braille alignment for the current document.
- Base the alignment data on the original `TranslationResult` before wrapping and before binding.
- Support whole-document viewing when the document is composed of multiple `TranslationResult` instances, while preserving segment boundaries.
- Refresh the viewer only at explicit refresh points:
  - when `Dual View` is opened
  - after a manual conversion succeeds
  - after switching to another document
- Keep the viewer read-only with no HTML-side editing.

## Non-Goals

- No editing of source text or braille inside the HTML viewer.
- No live viewer updates on every source-text edit.
- No building the viewer from wrapped output or from post-`bind_word_tokens()` output.
- No redesign of the existing braille result editor.
- No React, Vue, or other frontend framework in this change.

## User-Facing Behavior

### Opening

- Add a `Dual View` command under the `File` menu.
- When selected, it opens a modeless viewer window attached to the main frame.
- If the viewer is not open yet, create a new window.
- If the viewer is already open, selecting `Dual View` again brings the existing viewer in front of the DotExpress main window and refreshes its content.

### Window Behavior

- The viewer is a closable independent child window.
- Closing the viewer does not affect the main window, the current document, or the braille result.
- The viewer should float only relative to the DotExpress main window and must not take global always-on-top behavior over other applications.
- When the DotExpress main window becomes active again, if the viewer is still open and not minimized, the viewer should return to the front of the main window as well.
- The viewer can be moved, resized, and otherwise behaves like a normal window.

### Displayed Content

- The viewer shows character-level source/braille alignment from the current document's most recent successful conversion.
- Each source character maps to one HTML display unit.
- Each display unit shows the source character on top and the corresponding braille fragment below.
- A full document may contain multiple translation segments, and the display must preserve segment boundaries.
- Newlines and spaces must be preserved to maintain the reading rhythm of the source text.

### Refresh Timing

- When the viewer opens, if the current document already has data from its most recent successful conversion, show that data immediately.
- After a manual conversion succeeds, refresh the viewer if it is open.
- After switching to another document, refresh the viewer to show that document's most recent successful conversion data if the viewer is open.
- If the user edits the source text without running conversion again, the viewer does not update.

## Internal Design

### Window Structure

- Add viewer window lifecycle management to `BrailleFrame`.
- Add a dedicated `DualViewFrame` or equivalent GUI class that owns:
  - `wx.html2.WebView`
  - initial HTML shell loading
  - a bridge method that receives JSON/view-model data and re-renders
- `DualViewFrame` should be a modeless child `wx.Frame` whose parent is the main `BrailleFrame`.
- When `BrailleFrame` becomes active again, it should check the viewer state; if the viewer is open and not minimized, it should `Raise()` the viewer in front of the main window as well.

### Data Source

- The viewer's source of truth is the original translation data produced by the current document's most recent successful conversion.
- This data must preserve the original `TranslationResult` before wrapping and before binding, not just the final braille string.
- The existing manual conversion flow should save the original translation data needed by the viewer in addition to updating the braille result editor.
- On document switch, the viewer reads the currently stored most recent successful conversion data for that document; if none is available, the viewer shows empty content or a clear no-data state.

### Document-Level Alignment Model

- Add a pure-data builder such as `build_dual_view_model(...)` that takes multiple `TranslationResult` objects and produces a document-level view model for HTML rendering.
- The builder must preserve segment boundaries rather than flattening all content into one undifferentiated string.
- Recommended output structure:

```json
{
  "segments": [
    {
      "source_text": "abc",
      "braille_text": "⠁⠃⠉",
      "items": [
        {
          "raw_index": 0,
          "raw_char": "a",
          "braille_start": 0,
          "braille_end": 1,
          "braille_text": "⠁"
        }
      ]
    }
  ]
}
```

- `segments` correspond to the document's translation segments.
- `items` are character-level alignment units, and each item represents exactly one raw character.

### Character-Level Mapping Rules

- For each `TranslationResult`:
  - use `raw_to_braille_pos[i]` as the braille start index for the `i`th source character
  - derive the end index from the next character's start index
  - use `len(braille)` as the end index for the last character
- The braille fragment for a character is `braille[start:end]`.
- A single source character may map to zero, one, or multiple braille cells.
- The UI is always source-character-centric and should not switch to braille-cell-centric rendering.

### Special Characters And Segment Handling

- Spaces must remain standalone display units and must not be merged with neighboring characters.
- Newline characters should not render as ordinary character cards; they should become HTML line breaks or new block boundaries.
- If a character has `braille_start == braille_end`, it may render as an empty braille alignment; the placeholder style is a frontend decision.
- Math segments, dictionary-replacement segments, and ordinary text segments all use the same view-model structure; the HTML render layer should not infer translation origin.

### HTML Render Structure

- The first version uses plain HTML/CSS/JS with no React or Vue.
- The HTML should render using a three-level structure: document > segment > character card.
- Each character card includes:
  - a source-character area
  - a corresponding braille area
  - metadata for debugging or future hover behavior
- The first version should not rely on `<ruby>` as the primary structure because spaces, newlines, long braille fragments, and detailed styling are harder to control there.
- A custom structure such as `<span class="cell">` is the more stable choice.

### Refresh Pipeline

- The viewer refreshes only in these three situations:
  - opening `Dual View`
  - successful manual conversion
  - document switch
- The viewer should not listen to every change in the source text editor.
- If the viewer is not open, the main window does not need to proactively build or push HTML.
- If the viewer is open but the current document has no most recent successful conversion data, the viewer should show an empty state and should not trigger additional conversion.

### Relationship To The Existing Conversion Flow

- The viewer pipeline exists in parallel with the existing output pipeline.
- The current `translate_and_wrap_both()`, `bind_word_tokens()`, `reclean_token()`, and `wrap()` remain dedicated to the existing braille-result display and export flow.
- The viewer must not reuse wrapped output, because that would lose character-level mapping fidelity.
- If the current conversion flow does not yet preserve the original translation data needed by the viewer, successful conversion should be extended to save it, without changing the existing output text behavior.

## Testing

### Unit Tests

- Add tests for the document-level alignment builder covering:
  - ordinary character alignment in a single segment
  - multiple segments while preserving segment boundaries
  - one character mapping to multiple braille cells
  - spaces and newline handling
  - empty alignment ranges
- If a new document-level storage structure is added, add tests for saving and switching the "most recent successful conversion" data.

### GUI / Flow Tests

- Add or update menu tests to verify that `Dual View` exists under the `File` menu.
- If supported by the current test setup, add frame-level flow tests to verify:
  - opening the viewer shows the current document data
  - successful manual conversion refreshes the viewer
  - switching documents refreshes the viewer
  - plain text editing does not refresh the viewer

## Risks And Constraints

- If the current document model does not preserve the original `TranslationResult` collection from the most recent successful conversion, an additional storage responsibility must be added; otherwise the viewer cannot reconstruct precise alignment after a document switch.
- If multilingual, dictionary-replacement, and math segments currently produce different shapes of `TranslationResult`, the builder must normalize handling of their `raw` and `braille` structures and must not assume a single segment source.
- If wrapped-layout viewing is needed later, it should be treated as a separate viewer mode rather than replacing this unwrapped character-level alignment mode.
- `wx.html2.WebView` backend capabilities differ across platforms, so the first version should avoid complex bidirectional script bridges and stay render-focused.

## Acceptance Criteria

- A `Dual View` window can be opened from the `File` menu.
- The viewer is a closable modeless child window and does not take global always-on-top behavior over other applications.
- When the DotExpress main window returns to the foreground, an already-open viewer also returns to the front of the main window.
- The viewer is source-character-centric and shows source text above the corresponding braille fragment.
- The viewer is based on original translation data before wrapping and before binding.
- A full document composed of multiple `TranslationResult` objects still displays correctly with segment boundaries preserved.
- The viewer updates only when opened, after successful manual conversion, and after document switch.
- Editing source text without re-running conversion does not update the viewer.
- Existing braille-result and export behavior remain unchanged after the viewer is introduced.
