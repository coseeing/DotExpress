# Platform Translation Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Isolate Windows liblouis and MathCAT dependencies behind independently selectable adapters and provide character-aligned `⣿` fallback translation for unsupported capabilities.

**Architecture:** Conversion receives one explicit `TranslationRuntime` containing separate text and math translator protocols. Native adapters own binary loading and lifecycle; a provider replaces only unavailable capabilities with deterministic fallback adapters. `translate.py` retains the platform-neutral `TranslationResult`, while `conversion/service.py` keeps dictionary, language, segment, wrapping, and output orchestration.

**Tech Stack:** Python 3, `typing.Protocol`, `dataclasses`, `unittest`, `unittest.mock`, wxPython, bundled liblouis, MathCAT

---

## Final File Map

- Create `client/adapters/__init__.py`: adapter package marker.
- Create `client/adapters/translation/__init__.py`: public translation adapter exports.
- Create `client/adapters/translation/contracts.py`: translator protocols, capability error, and runtime lifecycle.
- Create `client/adapters/translation/fallback.py`: text and math character fallback.
- Create `client/adapters/translation/liblouis.py`: native liblouis adapter and lifecycle.
- Create `client/adapters/translation/mathcat.py`: native MathCAT translator returning `TranslationResult`.
- Create `client/adapters/translation/provider.py`: independent native/fallback selection.
- Modify `client/translate.py`: retain result behavior; remove native imports and translation calls.
- Modify `client/conversion/service.py`: call runtime translators and accept explicit runtime injection.
- Modify `client/gui.py`: assemble, pass, and close one runtime.
- Modify `client/conversion/mathcat_adapter.py`: expose an explicit initialization probe.
- Modify `client/tests/test_translation_result.py`: keep only Windows native integration cases.
- Create `client/tests/test_translation_result_core.py`: platform-neutral result characterization.
- Create `client/tests/test_translation_fallback.py`: fallback contract tests.
- Create `client/tests/test_liblouis_adapter.py`: native text adapter unit tests.
- Create `client/tests/test_math_translation_adapter.py`: native math adapter unit tests.
- Create `client/tests/test_translation_runtime_provider.py`: selection and lifecycle tests.
- Modify `client/tests/test_conversion_service.py`: runtime-injected service tests.
- Modify `client/tests/test_gui_document_flows.py`: runtime forwarding and shutdown tests.
- Modify `client/tests/test_dual_view_model.py`: fallback alignment integration test.

### Task 1: Make the Result Model Platform-Neutral

**Files:**

- Modify: `client/translate.py`
- Create: `client/tests/test_translation_result_core.py`
- Modify: `client/tests/test_translation_result.py`

- [ ] **Step 1: Write a platform-neutral import and result test**

Create `client/tests/test_translation_result_core.py`:

```python
import importlib
import sys
import unittest


class TranslationResultCoreTest(unittest.TestCase):
    def test_import_does_not_import_liblouis_helper(self) -> None:
        sys.modules.pop("translate", None)
        sys.modules.pop("braille.louis_helper", None)
        sys.modules.pop("braille.liblouis", None)

        module = importlib.import_module("translate")

        self.assertNotIn("braille.louis_helper", sys.modules)
        self.assertNotIn("braille.liblouis", sys.modules)
        self.assertTrue(hasattr(module, "TranslationResult"))

    def test_addition_offsets_both_position_arrays(self) -> None:
        from translate import TranslationResult

        left = TranslationResult(["a"], ["⠁"], [0], [0])
        right = TranslationResult(["b"], ["⠃"], [0], [0])

        result = left + right

        self.assertEqual(result.raw, ["a", "b"])
        self.assertEqual(result.braille, ["⠁", "⠃"])
        self.assertEqual(result.braille_to_raw_pos, [0, 1])
        self.assertEqual(result.raw_to_braille_pos, [0, 1])

    def test_empty_result_has_empty_mapping(self) -> None:
        from translate import TranslationResult

        result = TranslationResult([], [], [], [])

        self.assertEqual(result.raw, [])
        self.assertEqual(result.braille, [])
        self.assertEqual(result.braille_to_raw_pos, [])
        self.assertEqual(result.raw_to_braille_pos, [])
```

- [ ] **Step 2: Run the import test and verify it fails**

Run from `client/`:

```bash
python3 -m unittest tests.test_translation_result_core -v
```

Expected: FAIL or ERROR because importing `translate` imports `braille.louis_helper`.

- [ ] **Step 3: Remove native translation from `translate.py`**

Delete these imports:

```python
import os
from braille import louis_helper
from braille.tables import TABLES_DIR
```

Delete `BRAILLE_UNICODE_PATTERNS_START`, `translate()`, and `translate_as_single_token()`. Keep `TranslationResult` and all of its existing result, token, cleanup, and wrapping methods unchanged.

Move tests that directly call the deleted native functions out of `test_translation_result.py`; keep those assertions for Task 3, where they will target `LiblouisTextTranslator`.

- [ ] **Step 4: Run the platform-neutral result tests**

Run:

```bash
python3 -m unittest tests.test_translation_result_core -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit the platform-neutral model**

```bash
git add client/translate.py client/tests/test_translation_result.py client/tests/test_translation_result_core.py
git commit -m "refactor: isolate translation result model"
```

### Task 2: Define Contracts and Character Fallback

**Files:**

- Create: `client/adapters/__init__.py`
- Create: `client/adapters/translation/__init__.py`
- Create: `client/adapters/translation/contracts.py`
- Create: `client/adapters/translation/fallback.py`
- Create: `client/tests/test_translation_fallback.py`

- [ ] **Step 1: Write fallback contract tests**

Create `client/tests/test_translation_fallback.py`:

```python
import unittest

from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator


class TranslationFallbackTest(unittest.TestCase):
    def assert_character_fallback(self, result, source: str, expected: str) -> None:
        self.assertEqual(result.raw, list(source))
        self.assertEqual(result.braille, list(expected))
        self.assertEqual(result.raw_to_braille_pos, list(range(len(source))))
        self.assertEqual(result.braille_to_raw_pos, list(range(len(source))))

    def test_text_maps_characters_spaces_and_newlines(self) -> None:
        result = FallbackTextTranslator().translate(
            "ignored replacement",
            table="zh-tw.ctb",
            raw="我 們\n1+2",
        )

        self.assert_character_fallback(result, "我 們\n1+2", "⣿⠀⣿\n⣿⣿⣿")

    def test_text_uses_raw_when_replacement_length_differs(self) -> None:
        result = FallbackTextTranslator().translate(
            "long replacement",
            table="zh-tw.ctb",
            raw="字",
        )

        self.assert_character_fallback(result, "字", "⣿")

    def test_atomic_text_keeps_character_mapping(self) -> None:
        result = FallbackTextTranslator().translate(
            "replacement",
            table="zh-tw.ctb",
            raw="原文",
            single_token=True,
        )

        self.assert_character_fallback(result, "原文", "⣿⣿")

    def test_math_uses_same_character_contract(self) -> None:
        result = FallbackMathTranslator().translate("1 + 2", braille_code="Nemeth")

        self.assert_character_fallback(result, "1 + 2", "⣿⠀⣿⠀⣿")

    def test_empty_source_returns_empty_result(self) -> None:
        result = FallbackMathTranslator().translate("", braille_code="Nemeth")

        self.assert_character_fallback(result, "", "")
```

- [ ] **Step 2: Run the tests and verify missing modules fail**

Run:

```bash
python3 -m unittest tests.test_translation_fallback -v
```

Expected: ERROR with `ModuleNotFoundError: No module named 'adapters'`.

- [ ] **Step 3: Add exact contracts and runtime lifecycle**

Create package markers and `client/adapters/translation/contracts.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from translate import TranslationResult


class RuntimeUnavailableError(RuntimeError):
    pass


class BrailleTextTranslator(Protocol):
    def translate(
        self,
        text: str,
        *,
        table: str,
        raw: str,
        single_token: bool = False,
    ) -> TranslationResult:
        raise NotImplementedError


class MathSegmentTranslator(Protocol):
    def translate(self, source: str, *, braille_code: str) -> TranslationResult:
        raise NotImplementedError


@dataclass
class TranslationRuntime:
    text_translator: BrailleTextTranslator
    math_translator: MathSegmentTranslator
    close_callbacks: tuple[Callable[[], None], ...] = ()
    _closed: bool = field(default=False, init=False, repr=False)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for callback in reversed(self.close_callbacks):
            callback()
```

- [ ] **Step 4: Implement one shared character-result helper**

Create `client/adapters/translation/fallback.py`:

```python
from translate import TranslationResult


def build_character_fallback(source: str) -> TranslationResult:
    braille = [
        "\n" if char == "\n" else "⠀" if char == " " else "⣿"
        for char in source
    ]
    positions = list(range(len(source)))
    return TranslationResult(
        list(source),
        braille,
        positions.copy(),
        positions.copy(),
    )


class FallbackTextTranslator:
    def translate(
        self,
        text: str,
        *,
        table: str,
        raw: str,
        single_token: bool = False,
    ) -> TranslationResult:
        return build_character_fallback(raw)


class FallbackMathTranslator:
    def translate(self, source: str, *, braille_code: str) -> TranslationResult:
        return build_character_fallback(source)
```

Export the five public contract and adapter types from `client/adapters/translation/__init__.py`.

- [ ] **Step 5: Run fallback and result tests**

Run:

```bash
python3 -m unittest tests.test_translation_fallback tests.test_translation_result_core -v
```

Expected: 8 tests PASS.

- [ ] **Step 6: Commit fallback adapters**

```bash
git add client/adapters client/tests/test_translation_fallback.py
git commit -m "feat: add character translation fallback"
```

### Task 3: Wrap liblouis Behind the Native Text Adapter

**Files:**

- Create: `client/adapters/translation/liblouis.py`
- Create: `client/tests/test_liblouis_adapter.py`
- Modify: `client/tests/test_translation_result.py`

- [ ] **Step 1: Write adapter forwarding and mapping tests**

Create `client/tests/test_liblouis_adapter.py`:

```python
import unittest
from unittest.mock import Mock

from adapters.translation.liblouis import LiblouisTextTranslator


class LiblouisTextTranslatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = Mock()
        self.helper.translate.return_value = ([1, 3], [0, 1], [0, 1], None)
        self.adapter = LiblouisTextTranslator(
            helper=self.helper,
            tables_dir="/tables",
        )

    def test_regular_translation_preserves_native_mapping(self) -> None:
        result = self.adapter.translate(
            "ab",
            table="en.ctb",
            raw="ab",
        )

        self.helper.translate.assert_called_once_with(
            ["/tables/en.ctb"],
            "ab",
            mode=4,
        )
        self.assertEqual(result.raw, ["a", "b"])
        self.assertEqual(result.braille, ["⠁", "⠃"])
        self.assertEqual(result.braille_to_raw_pos, [0, 1])
        self.assertEqual(result.raw_to_braille_pos, [0, 1])

    def test_single_token_maps_every_cell_to_source_token(self) -> None:
        result = self.adapter.translate(
            "replacement",
            table="zh-tw.ctb",
            raw="原文",
            single_token=True,
        )

        self.assertEqual(result.raw, ["原文"])
        self.assertEqual(result.braille, ["⠁", "⠃"])
        self.assertEqual(result.braille_to_raw_pos, [0, 0])
        self.assertEqual(result.raw_to_braille_pos, [0])
```

- [ ] **Step 2: Run the adapter tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_liblouis_adapter -v
```

Expected: ERROR because `adapters.translation.liblouis` does not exist.

- [ ] **Step 3: Implement the native text adapter**

Create `client/adapters/translation/liblouis.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

from translate import TranslationResult


BRAILLE_UNICODE_PATTERNS_START = 0x2800


class LiblouisTextTranslator:
    def __init__(self, *, helper, tables_dir: str | Path):
        self._helper = helper
        self._tables_dir = str(tables_dir)

    def close(self) -> None:
        self._helper.terminate()

    def translate(
        self,
        text: str,
        *,
        table: str,
        raw: str,
        single_token: bool = False,
    ) -> TranslationResult:
        table_path = os.path.join(self._tables_dir, table)
        cells, braille_to_raw, raw_to_braille, _cursor = self._helper.translate(
            [table_path],
            text,
            mode=4,
        )
        braille = [
            chr(cell + BRAILLE_UNICODE_PATTERNS_START)
            for cell in cells
        ]
        if single_token:
            if not raw:
                return TranslationResult([], [], [], [])
            return TranslationResult(
                [raw],
                braille,
                [0] * len(braille),
                [0],
            )
        return TranslationResult(
            list(text),
            braille,
            braille_to_raw,
            raw_to_braille,
        )
```

- [ ] **Step 4: Retarget Windows integration tests**

In `client/tests/test_translation_result.py`, construct one initialized `LiblouisTextTranslator` in module setup and replace calls such as:

```python
result = translate("zh-tw.ctb", text)
```

with:

```python
result = native_translator.translate(
    text,
    table="zh-tw.ctb",
    raw=text,
)
```

Keep the existing Windows skip guard and all token cleanup/wrapping assertions.

- [ ] **Step 5: Run native adapter unit tests**

Run:

```bash
python3 -m unittest tests.test_liblouis_adapter -v
```

Expected: 2 tests PASS.

On Windows also run:

```bash
python -m unittest tests.test_liblouis_runtime tests.test_translation_result -v
```

Expected: all native runtime and result tests PASS.

- [ ] **Step 6: Commit the liblouis adapter**

```bash
git add client/adapters/translation/liblouis.py client/tests/test_liblouis_adapter.py client/tests/test_translation_result.py
git commit -m "refactor: wrap liblouis translation adapter"
```

### Task 4: Wrap MathCAT as a Result-Producing Adapter

**Files:**

- Modify: `client/conversion/mathcat_adapter.py`
- Create: `client/adapters/translation/mathcat.py`
- Create: `client/tests/test_math_translation_adapter.py`

- [ ] **Step 1: Write native math adapter tests**

Create `client/tests/test_math_translation_adapter.py`:

```python
import unittest
from unittest.mock import Mock

from adapters.translation.mathcat import MathCATMathTranslator


class MathCATMathTranslatorTest(unittest.TestCase):
    def test_returns_current_single_token_mapping(self) -> None:
        translate_math = Mock(return_value="⠼⠁⠬⠃")
        adapter = MathCATMathTranslator(translate_math=translate_math)

        result = adapter.translate("1+2", braille_code="Nemeth")

        translate_math.assert_called_once_with("1+2", braille_code="Nemeth")
        self.assertEqual(result.raw, ["1+2"])
        self.assertEqual(result.braille, list("⠼⠁⠬⠃"))
        self.assertEqual(result.raw_to_braille_pos, [0])
        self.assertEqual(result.braille_to_raw_pos, [0, 0, 0, 0])

    def test_empty_math_has_empty_mapping(self) -> None:
        adapter = MathCATMathTranslator(translate_math=Mock(return_value=""))

        result = adapter.translate("", braille_code="UEB")

        self.assertEqual(result.raw, [])
        self.assertEqual(result.braille, [])
        self.assertEqual(result.raw_to_braille_pos, [])
        self.assertEqual(result.braille_to_raw_pos, [])
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_math_translation_adapter -v
```

Expected: ERROR because `adapters.translation.mathcat` does not exist.

- [ ] **Step 3: Add an explicit MathCAT initialization probe**

Add to `MathCATAdapter` in `client/conversion/mathcat_adapter.py`:

```python
def initialize(self) -> None:
    self._load_libmathcat()
```

Add a unit test to `client/tests/test_mathcat_adapter.py` asserting `initialize()` calls `_load_libmathcat()` once.

- [ ] **Step 4: Implement the result-producing adapter**

Create `client/adapters/translation/mathcat.py`:

```python
from __future__ import annotations

from collections.abc import Callable

from translate import TranslationResult


class MathCATMathTranslator:
    def __init__(self, *, translate_math: Callable[..., str]):
        self._translate_math = translate_math

    def translate(self, source: str, *, braille_code: str) -> TranslationResult:
        braille = list(
            self._translate_math(source, braille_code=braille_code)
        )
        if not source:
            return TranslationResult([], [], [], [])
        return TranslationResult(
            [source],
            braille,
            [0] * len(braille),
            [0],
        )
```

- [ ] **Step 5: Run math adapter tests**

Run:

```bash
python3 -m unittest tests.test_math_translation_adapter tests.test_mathcat_adapter tests.test_math_service -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit the MathCAT adapter**

```bash
git add client/adapters/translation/mathcat.py client/conversion/mathcat_adapter.py client/tests/test_math_translation_adapter.py client/tests/test_mathcat_adapter.py
git commit -m "refactor: wrap MathCAT translation adapter"
```

### Task 5: Build Independent Runtime Selection

**Files:**

- Create: `client/adapters/translation/provider.py`
- Create: `client/tests/test_translation_runtime_provider.py`
- Modify: `client/adapters/translation/__init__.py`

- [ ] **Step 1: Write all selection and lifecycle tests**

Create `client/tests/test_translation_runtime_provider.py`:

```python
import unittest
from unittest.mock import Mock

from adapters.translation.contracts import RuntimeUnavailableError
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from adapters.translation.provider import build_translation_runtime


class TranslationRuntimeProviderTest(unittest.TestCase):
    def test_selects_both_native_adapters(self) -> None:
        text = Mock()
        math = Mock()

        runtime = build_translation_runtime(
            text_factory=Mock(return_value=text),
            math_factory=Mock(return_value=math),
        )

        self.assertIs(runtime.text_translator, text)
        self.assertIs(runtime.math_translator, math)

    def test_falls_back_only_for_unavailable_text(self) -> None:
        math = Mock()

        runtime = build_translation_runtime(
            text_factory=Mock(side_effect=RuntimeUnavailableError("text")),
            math_factory=Mock(return_value=math),
        )

        self.assertIsInstance(runtime.text_translator, FallbackTextTranslator)
        self.assertIs(runtime.math_translator, math)

    def test_falls_back_only_for_unavailable_math(self) -> None:
        text = Mock()

        runtime = build_translation_runtime(
            text_factory=Mock(return_value=text),
            math_factory=Mock(side_effect=RuntimeUnavailableError("math")),
        )

        self.assertIs(runtime.text_translator, text)
        self.assertIsInstance(runtime.math_translator, FallbackMathTranslator)

    def test_falls_back_for_both_unavailable_capabilities(self) -> None:
        runtime = build_translation_runtime(
            text_factory=Mock(side_effect=RuntimeUnavailableError("text")),
            math_factory=Mock(side_effect=RuntimeUnavailableError("math")),
        )

        self.assertIsInstance(runtime.text_translator, FallbackTextTranslator)
        self.assertIsInstance(runtime.math_translator, FallbackMathTranslator)

    def test_unexpected_factory_error_propagates(self) -> None:
        with self.assertRaisesRegex(ValueError, "defect"):
            build_translation_runtime(
                text_factory=Mock(side_effect=ValueError("defect")),
                math_factory=Mock(),
            )

    def test_close_is_idempotent_and_closes_initialized_adapters(self) -> None:
        text = Mock()
        math = Mock()
        runtime = build_translation_runtime(
            text_factory=Mock(return_value=text),
            math_factory=Mock(return_value=math),
        )

        runtime.close()
        runtime.close()

        text.close.assert_called_once_with()
        math.close.assert_called_once_with()
```

- [ ] **Step 2: Run provider tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_translation_runtime_provider -v
```

Expected: ERROR because `provider.py` does not exist.

- [ ] **Step 3: Implement injectable provider selection**

Create `client/adapters/translation/provider.py` with:

```python
from __future__ import annotations

import sys
from collections.abc import Callable

from adapters.translation.contracts import RuntimeUnavailableError, TranslationRuntime
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from conversion.mathcat_adapter import MathCATError


def _close_callback(adapter) -> Callable[[], None] | None:
    callback = getattr(adapter, "close", None)
    return callback if callable(callback) else None


def build_translation_runtime(
    *,
    text_factory: Callable[[], object],
    math_factory: Callable[[], object],
) -> TranslationRuntime:
    callbacks = []
    try:
        text = text_factory()
    except RuntimeUnavailableError:
        text = FallbackTextTranslator()
    else:
        callback = _close_callback(text)
        if callback is not None:
            callbacks.append(callback)

    try:
        math = math_factory()
    except RuntimeUnavailableError:
        math = FallbackMathTranslator()
    else:
        callback = _close_callback(math)
        if callback is not None:
            callbacks.append(callback)

    return TranslationRuntime(
        text_translator=text,
        math_translator=math,
        close_callbacks=tuple(callbacks),
    )
```

Add these exact default factories in the same file:

```python
def create_default_text_translator(
    *,
    platform: str | None = None,
):
    if (platform or sys.platform) != "win32":
        raise RuntimeUnavailableError("bundled liblouis requires Windows")
    try:
        from braille import louis_helper
        from braille.tables import TABLES_DIR
        from adapters.translation.liblouis import LiblouisTextTranslator

        louis_helper.initialize()
    except (ImportError, OSError) as error:
        raise RuntimeUnavailableError(str(error)) from error
    return LiblouisTextTranslator(
        helper=louis_helper,
        tables_dir=TABLES_DIR,
    )


def create_default_math_translator(
    *,
    platform: str | None = None,
):
    if (platform or sys.platform) != "win32":
        raise RuntimeUnavailableError("bundled MathCAT requires Windows")
    try:
        from adapters.translation.mathcat import MathCATMathTranslator
        from conversion.math_service import translate_math_segment
        from conversion.mathcat_adapter import get_shared_mathcat_adapter

        get_shared_mathcat_adapter().initialize()
    except (ImportError, OSError, MathCATError) as error:
        raise RuntimeUnavailableError(str(error)) from error
    return MathCATMathTranslator(translate_math=translate_math_segment)


def build_default_translation_runtime() -> TranslationRuntime:
    return build_translation_runtime(
        text_factory=create_default_text_translator,
        math_factory=create_default_math_translator,
    )
```

- [ ] **Step 4: Add default factory tests**

Patch `provider.sys.platform`, imports, and initialization collaborators to verify:

```python
with self.assertRaises(RuntimeUnavailableError):
    provider.create_default_text_translator(platform="linux")
```

Patch `braille.louis_helper.initialize` to raise `ValueError("defect")` and assert the `ValueError` propagates instead of becoming `RuntimeUnavailableError`.

- [ ] **Step 5: Run provider tests**

Run:

```bash
python3 -m unittest tests.test_translation_runtime_provider -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit runtime selection**

```bash
git add client/adapters/translation/provider.py client/adapters/translation/__init__.py client/tests/test_translation_runtime_provider.py
git commit -m "feat: select translation runtimes independently"
```

### Task 6: Inject Runtime into Conversion

**Files:**

- Modify: `client/conversion/service.py`
- Modify: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Add runtime-injected service tests**

Add to `client/tests/test_conversion_service.py`:

```python
from adapters.translation.contracts import TranslationRuntime
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator


def _fallback_runtime(self) -> TranslationRuntime:
    return TranslationRuntime(
        text_translator=FallbackTextTranslator(),
        math_translator=FallbackMathTranslator(),
    )


def test_translate_segments_uses_text_and_math_runtime(self) -> None:
    from conversion import service

    runtime = self._fallback_runtime()

    def fake_plain(
        table_file,
        text,
        dictionary_path,
        translation_tables,
        bopomofo_path,
        *,
        runtime,
    ):
        return [
            runtime.text_translator.translate(
                text,
                table=table_file,
                raw=text,
            )
        ]

    with patch.object(service, "_translate_plain_text_segment", side_effect=fake_plain):
        results = translate_with_language_segments(
            "zh-tw.ctb",
            "我$1+2$",
            Path("dictionary/default.csv"),
            {"default": "zh-tw.ctb", "math": "Nemeth"},
            Path("data/Bopomofo2Braille.csv"),
            runtime=runtime,
        )

    self.assertEqual("".join("".join(item.braille) for item in results), "⣿⠀⣿⣿⣿")
    self.assertEqual(results[-1].raw, ["1", "+", "2"])


def test_convert_with_alignment_runs_under_full_fallback(self) -> None:
    runtime = self._fallback_runtime()
    request = self.request.__class__(
        raw_text="我$1+2$",
        table_file=self.request.table_file,
        output_mode=self.request.output_mode,
        width=self.request.width,
        dictionary_path=self.request.dictionary_path,
        data_dir=self.request.data_dir,
        translation_tables=self.request.translation_tables,
    )

    segments = [
        runtime.text_translator.translate(
            "我",
            table="zh-tw.ctb",
            raw="我",
        ),
        runtime.math_translator.translate("1+2", braille_code="Nemeth"),
    ]
    with patch(
        "conversion.service.translate_with_language_segments",
        return_value=segments,
    ):
        output = convert_text_with_alignment(
            request,
            map_char=lambda text, **kwargs: text,
            runtime=runtime,
        )

    self.assertTrue(output.display_text)
    self.assertTrue(output.translation_results)
```

- [ ] **Step 2: Run the new focused tests and verify signature failures**

Run:

```bash
python3 -m unittest tests.test_conversion_service.ConversionServiceTest.test_translate_segments_uses_text_and_math_runtime -v
```

Expected: FAIL because conversion functions do not accept `runtime`.

- [ ] **Step 3: Replace concrete translation calls**

Update `_translate_plain_text_segment()` to accept `runtime: TranslationRuntime`. Replace:

```python
translate(table, replacement, raw)
translate_as_single_token(table, replacement, raw)
```

with:

```python
runtime.text_translator.translate(
    replacement_segment["text"],
    table=translate_table,
    raw=raw_segment["text"],
    single_token=replacement_segment["atomic"],
)
```

When inserting a language-boundary space, call the text adapter with:

```python
runtime.text_translator.translate(
    " ",
    table=previous_translate_table,
    raw=" ",
)
```

Replace math string conversion and `build_math_translation_result()` with:

```python
runtime.math_translator.translate(
    segment["text"],
    braille_code=math_braille_code,
)
```

Remove `build_math_translation_result()` after migrating its tests to the native math adapter test.

- [ ] **Step 4: Thread the explicit runtime through public entry points**

Add keyword-only `runtime: TranslationRuntime` to:

- `translate_with_language_segments()`
- `translate_with_language()`
- `convert_text_with_alignment()`
- `translate_and_wrap_both()`
- `convert_text_for_output()`

Pass the same runtime through every internal call. Do not create a provider or singleton inside `conversion/service.py`.

For each existing service test, construct `TranslationRuntime(text_translator=Mock(), math_translator=Mock())`. Configure `text_translator.translate.return_value` and `math_translator.translate.return_value` with that test's existing fake `TranslationResult`, then assert calls against these two adapter mocks instead of `translate.translate`, `translate_as_single_token`, or `translate_math_segment`.

- [ ] **Step 5: Run conversion tests**

Run:

```bash
python3 -m unittest tests.test_conversion_service -v
```

Expected: all conversion service tests PASS.

- [ ] **Step 6: Commit conversion injection**

```bash
git add client/conversion/service.py client/tests/test_conversion_service.py
git commit -m "refactor: inject translation runtime into conversion"
```

### Task 7: Move Runtime Assembly and Lifecycle into the Application

**Files:**

- Modify: `client/gui.py`
- Modify: `client/tests/test_gui_document_flows.py`
- Modify: `client/tests/test_client_init.py`

- [ ] **Step 1: Write GUI runtime ownership tests**

Add focused tests using a mocked runtime:

```python
def test_app_builds_runtime_and_passes_it_to_frame(self) -> None:
    runtime = Mock()
    frame = Mock()
    with (
        patch("gui.build_default_translation_runtime", return_value=runtime),
        patch("gui.BrailleFrame", return_value=frame) as frame_class,
        patch("gui.start_client_init_background"),
    ):
        app = BrailleApp()
        result = app.OnInit()

    self.assertTrue(result)
    frame_class.assert_called_once_with(None, runtime=runtime)
    frame.Show.assert_called_once_with()


def test_app_exit_closes_runtime(self) -> None:
    runtime = Mock()
    app = BrailleApp()
    app.translation_runtime = runtime

    result = app.OnExit()

    self.assertEqual(result, 0)
    runtime.close.assert_called_once_with()
```

Add a frame conversion test asserting `runtime=self.translation_runtime` is passed to both `convert_text_for_output()` and `convert_text_with_alignment()`.

- [ ] **Step 2: Run GUI tests and verify constructor/signature failures**

Run:

```bash
python3 -m unittest tests.test_gui_document_flows -v
```

Expected: FAIL because `BrailleFrame` does not accept or forward a runtime.

- [ ] **Step 3: Remove direct liblouis ownership from GUI**

Delete:

```python
from braille import louis_helper
```

Import:

```python
from adapters.translation.contracts import TranslationRuntime
from adapters.translation.provider import build_default_translation_runtime
```

Change the frame constructor to:

```python
def __init__(
    self,
    *args,
    runtime: TranslationRuntime,
    **kwargs,
):
    super().__init__(*args, **kwargs)
    self.translation_runtime = runtime
```

Keep the rest of the constructor body unchanged.

- [ ] **Step 4: Forward runtime through GUI conversion calls**

Pass:

```python
runtime=self.translation_runtime
```

to `_convert_text_for_output()`'s `convert_text_for_output()` call and `_run_conversion()`'s `convert_text_with_alignment()` call.

- [ ] **Step 5: Assemble and close the runtime**

Replace direct helper lifecycle calls:

```python
def OnInit(self):
    self.translation_runtime = build_default_translation_runtime()
    self.frame = BrailleFrame(None, runtime=self.translation_runtime)
    self.frame.Show()
    start_client_init_background()
    return True

def OnExit(self):
    self.translation_runtime.close()
    return 0
```

- [ ] **Step 6: Run GUI and initialization tests**

Run:

```bash
python3 -m unittest tests.test_gui_document_flows tests.test_client_init -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit application assembly**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py client/tests/test_client_init.py
git commit -m "refactor: assemble translation runtime in app"
```

### Task 8: Verify Import Isolation and Dual-View Alignment

**Files:**

- Create: `client/tests/test_translation_import_isolation.py`
- Modify: `client/tests/test_dual_view_model.py`

- [ ] **Step 1: Write clean-process import tests**

Create `client/tests/test_translation_import_isolation.py`:

```python
import subprocess
import sys
import unittest


class TranslationImportIsolationTest(unittest.TestCase):
    def test_platform_neutral_modules_do_not_load_native_modules(self) -> None:
        script = """
import sys
import translate
import conversion.service
assert "braille.louis_helper" not in sys.modules
assert "libmathcat_py" not in sys.modules
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
```

- [ ] **Step 2: Write fallback-to-dual-view mapping test**

Add to `client/tests/test_dual_view_model.py`:

```python
from adapters.translation.fallback import FallbackTextTranslator


def test_fallback_character_mapping_builds_dual_view_segments(self) -> None:
    result = FallbackTextTranslator().translate(
        "ignored",
        table="zh-tw.ctb",
        raw="我 們",
    )

    model = build_dual_view_model((result,))

    self.assertEqual(
        [
            (item.raw_char, item.braille_text)
            for item in model.segments[0].items
        ],
        [("我", "⣿"), (" ", "⠀"), ("們", "⣿")],
    )
```

- [ ] **Step 3: Run isolation and dual-view tests**

Run:

```bash
python3 -m unittest tests.test_translation_import_isolation tests.test_dual_view_model -v
```

Expected: all tests PASS and the subprocess exits with status 0.

- [ ] **Step 4: Confirm UI platform helpers remain green**

Run:

```bash
python3 -m unittest tests.test_font_support tests.test_dual_view_frame -v
```

Expected: all tests PASS with no production changes to `font_support.py` or `dual_view.py`.

- [ ] **Step 5: Commit cross-platform integration coverage**

```bash
git add client/tests/test_translation_import_isolation.py client/tests/test_dual_view_model.py
git commit -m "test: cover cross-platform translation alignment"
```

### Task 9: Run Final Regression Verification

**Files:**

- Modify only if a failing test identifies a regression in files already listed by this plan.

- [ ] **Step 1: Run the complete platform-neutral adapter suite**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_translation_result_core \
  tests.test_translation_fallback \
  tests.test_liblouis_adapter \
  tests.test_math_translation_adapter \
  tests.test_translation_runtime_provider \
  tests.test_mathcat_adapter \
  tests.test_math_service \
  tests.test_conversion_service \
  tests.test_dual_view_model \
  tests.test_dual_view_frame \
  tests.test_font_support \
  tests.test_gui_document_flows \
  tests.test_translation_import_isolation \
  -v
```

Expected: all tests PASS with zero failures and zero errors.

- [ ] **Step 2: Run the full client test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all available tests PASS; Windows-only native tests may report SKIP on non-Windows.

- [ ] **Step 3: Run Windows native regression tests**

Run on Windows from `client\`:

```bat
python -m unittest tests.test_liblouis_runtime tests.test_translation_result tests.test_mathcat_adapter tests.test_math_service -v
```

Expected: all tests PASS with the bundled liblouis and MathCAT runtime.

- [ ] **Step 4: Inspect the final dependency boundary**

Run:

```bash
rg -n "louis_helper|libmathcat_py|add_dll_directory|ctypes\\.WinDLL" \
  translate.py conversion/service.py gui.py adapters
```

Expected:

- no matches in `translate.py` or `conversion/service.py`;
- `gui.py` contains no `louis_helper`;
- native loading matches occur only in native adapter/provider paths or existing low-level native modules.

- [ ] **Step 5: Inspect final changes**

Run:

```bash
git status --short
git diff --check
git log --oneline -9
```

Expected: no whitespace errors; implementation commits are scoped by task; unrelated pre-existing worktree changes remain untouched.
