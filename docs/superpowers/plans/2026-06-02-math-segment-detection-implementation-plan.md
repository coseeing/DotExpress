# Math Segment Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `$...$` inline math segment detection to the conversion pipeline, route math segments through a placeholder translator, and merge them as single-token `TranslationResult` objects.

**Architecture:** Extend `client/conversion/service.py` with a small top-level segment parser plus math-specific translation helpers, then integrate dispatch inside `translate_with_language()`. Keep GUI and downstream wrapping unchanged so all document save/export paths inherit the new behavior automatically.

**Tech Stack:** Python 3, `unittest`, wxPython client architecture, existing `TranslationResult` merge logic

---

### Task 1: Add parser and math-result tests

**Files:**
- Modify: `client/tests/test_conversion_service.py`
- Reference: `docs/superpowers/specs/2026-06-02-math-segment-detection-design.md`

- [ ] **Step 1: Write failing parser and wrapper tests**

```python
from conversion.service import (
    ConversionRequest,
    ConversionStageError,
    build_math_translation_result,
    convert_text_for_output,
    get_public_error_message,
    parse_inline_math_segments,
)

    def test_parse_inline_math_segments_splits_multiple_math_ranges(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("計算$1+2$和$3+4$"),
            [
                {"type": "text", "text": "計算"},
                {"type": "math", "text": "1+2"},
                {"type": "text", "text": "和"},
                {"type": "math", "text": "3+4"},
            ],
        )

    def test_parse_inline_math_segments_keeps_escaped_dollar_inside_math(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("$1+\\$2$"),
            [{"type": "math", "text": "1+\\$2"}],
        )

    def test_parse_inline_math_segments_treats_unmatched_opening_dollar_as_text(self) -> None:
        self.assertEqual(
            parse_inline_math_segments("計算$1+2"),
            [{"type": "text", "text": "計算$1+2"}],
        )

    def test_build_math_translation_result_creates_single_token_mapping(self) -> None:
        result = build_math_translation_result("1+2", "⠼⠁⠬⠃")
        self.assertEqual(result.raw, ["1+2"])
        self.assertEqual(result.braille, list("⠼⠁⠬⠃"))
        self.assertEqual(result.raw_to_braille_pos, [0])
        self.assertEqual(result.braille_to_raw_pos, [0, 0, 0, 0])
```

- [ ] **Step 2: Run focused tests to verify RED**

Run: `python3 -m unittest client.tests.test_conversion_service -v`

Expected: FAIL with import errors or missing attribute errors for `parse_inline_math_segments` and `build_math_translation_result`.

### Task 2: Add translate_with_language dispatch tests

**Files:**
- Modify: `client/tests/test_conversion_service.py`
- Reference: `client/conversion/service.py`

- [ ] **Step 1: Write failing dispatch tests with stub translators**

```python
from unittest.mock import patch

    def test_translate_with_language_merges_text_and_math_segments_in_order(self) -> None:
        from translate import TranslationResult
        from conversion import service

        def fake_text_translate(_table_file, text, _dictionary_path, _translation_tables, _bopomofo_path):
            braille = list(f"T[{text}]")
            return TranslationResult([text], braille, [0] * len(braille), [0])

        def fake_math_translate(text):
            return f"M[{text}]"

        with patch.object(service, "_translate_plain_text_segment", side_effect=fake_text_translate):
            with patch.object(service, "translate_math_placeholder", side_effect=fake_math_translate):
                result = service.translate_with_language(
                    "zh-tw.ctb",
                    "計算$1+2$的值",
                    Path("dictionary/default.csv"),
                    {"default": "zh-tw.ctb"},
                    Path("data/Bopomofo2Braille.csv"),
                )

        self.assertEqual(result.raw, ["計算", "1+2", "的值"])
        self.assertEqual("".join(result.braille), "T[計算]M[1+2]T[的值]")
        self.assertEqual(result.raw_to_braille_pos, [0, 5, 11])

    def test_translate_with_language_keeps_escaped_dollar_in_plain_text_segment(self) -> None:
        from translate import TranslationResult
        from conversion import service

        def fake_text_translate(_table_file, text, _dictionary_path, _translation_tables, _bopomofo_path):
            braille = list(text)
            return TranslationResult([text], braille, [0] * len(braille), [0])

        with patch.object(service, "_translate_plain_text_segment", side_effect=fake_text_translate):
            result = service.translate_with_language(
                "zh-tw.ctb",
                "價格\\$100",
                Path("dictionary/default.csv"),
                {"default": "zh-tw.ctb"},
                Path("data/Bopomofo2Braille.csv"),
            )

        self.assertEqual(result.raw, ["價格\\$100"])
        self.assertEqual("".join(result.braille), "價格\\$100")
```

- [ ] **Step 2: Run focused tests to verify RED**

Run: `python3 -m unittest client.tests.test_conversion_service -v`

Expected: FAIL because `_translate_plain_text_segment` does not exist and `translate_with_language()` still follows the old monolithic path.

### Task 3: Implement parser and math result helpers

**Files:**
- Modify: `client/conversion/service.py`
- Test: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Add minimal parsing and math-wrapper code**

```python
def parse_inline_math_segments(text: str) -> list[dict[str, str]]:
    segments: list[dict[str, str]] = []
    current: list[str] = []
    i = 0
    in_math = False
    math_start_segment_index = -1

    while i < len(text):
        char = text[i]
        escaped = i > 0 and text[i - 1] == "\\"
        if char == "$" and not escaped:
            if in_math:
                segments.append({"type": "math", "text": "".join(current)})
                current = []
                in_math = False
            else:
                if current:
                    segments.append({"type": "text", "text": "".join(current)})
                current = []
                in_math = True
            i += 1
            continue
        current.append(char)
        i += 1

    if in_math:
        prefix = "".join(current)
        if segments and segments[-1]["type"] == "text":
            segments[-1]["text"] += "$" + prefix
        else:
            segments.append({"type": "text", "text": "$" + prefix})
    elif current:
        segments.append({"type": "text", "text": "".join(current)})

    return segments

def translate_math_placeholder(math_text: str) -> str:
    return math_text

def build_math_translation_result(math_text: str, braille_text: str) -> TranslationResult:
    braille = list(braille_text)
    return TranslationResult([math_text], braille, [0] * len(braille), [0])
```

- [ ] **Step 2: Run focused tests to verify GREEN**

Run: `python3 -m unittest client.tests.test_conversion_service -v`

Expected: parser/helper tests PASS; dispatch tests still FAIL.

### Task 4: Refactor plain-text translation path and add math dispatch

**Files:**
- Modify: `client/conversion/service.py`
- Test: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Extract plain-text translator and integrate math segment loop**

```python
def _translate_plain_text_segment(
    table_file: str,
    text: str,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
):
    # move existing translate_with_language text-only logic here

def translate_with_language(...):
    if text == "":
        return TranslationResult([], [], [], [])

    translations = []
    for segment in parse_inline_math_segments(text):
        if segment["type"] == "text":
            if segment["text"]:
                translations.append(
                    _translate_plain_text_segment(
                        table_file,
                        segment["text"],
                        dictionary_path,
                        translation_tables,
                        bopomofo_path,
                    )
                )
        else:
            placeholder = translate_math_placeholder(segment["text"])
            translations.append(build_math_translation_result(segment["text"], placeholder))

    merged = translations[0]
    for segment in translations[1:]:
        merged = merged + segment
    return merged
```

- [ ] **Step 2: Run focused tests to verify GREEN**

Run: `python3 -m unittest client.tests.test_conversion_service -v`

Expected: all conversion service tests PASS.

### Task 5: Run repository checks for touched area

**Files:**
- Modify: none
- Test: `client/tests/test_conversion_service.py`, `client/conversion/service.py`

- [ ] **Step 1: Run compile checks**

Run: `python3 -m py_compile client/gui.py client/dialog.py client/dictionary_manager.py client/ui/action_menu.py client/conversion/service.py`

Expected: no output

- [ ] **Step 2: Run focused unit tests**

Run: `python3 -m unittest client.tests.test_conversion_service client.tests.test_translation_language_result -v`

Expected: PASS

- [ ] **Step 3: Review git diff**

Run: `git diff -- client/conversion/service.py client/tests/test_conversion_service.py docs/superpowers/plans/2026-06-02-math-segment-detection-implementation-plan.md`

Expected: diff only shows the planned math-segment changes and plan doc.
