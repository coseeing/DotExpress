# LaTeX MathCAT Nemeth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace DotExpress's math placeholder path with a real `$...$` LaTeX-to-Nemeth conversion pipeline using `latex2mathml` and a bundled MathCAT runtime.

**Architecture:** Add a dedicated math conversion module and a thin MathCAT adapter so `client/conversion/service.py` stays responsible for segment dispatch and merge policy only. Bundle the minimal MathCAT runtime assets into the client tree and package them with PyInstaller for Windows.

**Tech Stack:** Python 3.13 target, `unittest`, `latex2mathml`, NVDA MathCAT runtime assets, PyInstaller, existing `TranslationResult` merge logic

---

### Task 1: Define math conversion API with failing unit tests

**Files:**
- Create: `client/tests/test_math_service.py`
- Reference: `docs/superpowers/specs/2026-06-02-latex-mathcat-nemeth-design.md`

- [ ] **Step 1: Write the failing math service tests**

```python
import unittest
from unittest.mock import patch

from conversion.math_service import (
    MathConversionError,
    latex_to_mathml,
    translate_math_segment,
)


class MathServiceTest(unittest.TestCase):
    def test_latex_to_mathml_normalizes_vec_output(self) -> None:
        with patch("conversion.math_service._convert_latex_to_mathml", return_value="<math><mi>⇀</mi></math>"):
            self.assertEqual(
                latex_to_mathml(r"\vec{x}"),
                "<math><mo>⇀</mo></math>",
            )

    def test_translate_math_segment_calls_mathml_and_mathcat_in_order(self) -> None:
        with patch("conversion.math_service.latex_to_mathml", return_value="<math><mi>x</mi></math>") as latex_mock:
            with patch("conversion.math_service.mathml_to_nemeth_braille", return_value="⠭") as braille_mock:
                self.assertEqual(translate_math_segment("x"), "⠭")
        latex_mock.assert_called_once_with("x")
        braille_mock.assert_called_once_with("<math><mi>x</mi></math>")

    def test_translate_math_segment_raises_math_conversion_error_for_latex_failure(self) -> None:
        with patch("conversion.math_service.latex_to_mathml", side_effect=ValueError("bad latex")):
            with self.assertRaisesRegex(MathConversionError, "bad latex"):
                translate_math_segment(r"\bad")
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `python3 -m unittest tests.test_math_service -v`

Expected: FAIL with `ModuleNotFoundError` for `conversion.math_service`.

### Task 2: Add MathCAT adapter tests before implementation

**Files:**
- Create: `client/tests/test_mathcat_adapter.py`

- [ ] **Step 1: Write the failing adapter tests**

```python
import unittest
from pathlib import Path
from unittest.mock import patch

from conversion.mathcat_adapter import MathCATAdapter, MathCATError


class MathCATAdapterTest(unittest.TestCase):
    def test_get_braille_for_mathml_initializes_rules_and_braille_code(self) -> None:
        class FakeLib:
            def __init__(self):
                self.calls = []
            def GetVersion(self):
                return "test"
            def SetRulesDir(self, value):
                self.calls.append(("SetRulesDir", value))
            def SetPreference(self, key, value):
                self.calls.append(("SetPreference", key, value))
            def SetMathML(self, value):
                self.calls.append(("SetMathML", value))
            def GetBraille(self, value):
                self.calls.append(("GetBraille", value))
                return "⠼⠁"

        fake = FakeLib()
        adapter = MathCATAdapter(resource_root=Path("mathcat"))
        with patch.object(adapter, "_load_libmathcat", return_value=fake):
            self.assertEqual(adapter.get_braille_for_mathml("<math/>"), "⠼⠁")
        self.assertEqual(fake.calls[0][0], "SetRulesDir")
        self.assertIn(("SetPreference", "BrailleCode", "Nemeth"), fake.calls)

    def test_get_braille_for_mathml_wraps_runtime_failures(self) -> None:
        adapter = MathCATAdapter(resource_root=Path("mathcat"))
        with patch.object(adapter, "_load_libmathcat", side_effect=RuntimeError("load failed")):
            with self.assertRaisesRegex(MathCATError, "load failed"):
                adapter.get_braille_for_mathml("<math/>")
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `python3 -m unittest tests.test_mathcat_adapter -v`

Expected: FAIL with `ModuleNotFoundError` for `conversion.mathcat_adapter`.

### Task 3: Implement math service and MathCAT adapter

**Files:**
- Create: `client/conversion/math_service.py`
- Create: `client/conversion/mathcat_adapter.py`
- Create: `client/conversion/__init__.py` only if export updates are needed
- Test: `client/tests/test_math_service.py`
- Test: `client/tests/test_mathcat_adapter.py`

- [ ] **Step 1: Add the minimal math service implementation**

```python
import html


class MathConversionError(Exception):
    pass


def _convert_latex_to_mathml(latex_text: str) -> str:
    from latex2mathml import converter
    return converter.convert(latex_text)


def latex_to_mathml(latex_text: str) -> str:
    normalized = latex_text.replace(r"\vec{", r"\overset{⇀}{")
    mathml = html.unescape(_convert_latex_to_mathml(normalized))
    return mathml.replace("<mi>⇀</mi>", "<mo>⇀</mo>")


def mathml_to_nemeth_braille(mathml_text: str) -> str:
    from conversion.mathcat_adapter import get_shared_mathcat_adapter
    return get_shared_mathcat_adapter().get_braille_for_mathml(mathml_text)


def translate_math_segment(latex_text: str) -> str:
    try:
        return mathml_to_nemeth_braille(latex_to_mathml(latex_text))
    except Exception as error:
        raise MathConversionError(str(error)) from error
```

- [ ] **Step 2: Add the minimal MathCAT adapter implementation**

```python
from dataclasses import dataclass
from pathlib import Path
import importlib.util
import sys


class MathCATError(Exception):
    pass


@dataclass
class MathCATAdapter:
    resource_root: Path
    _libmathcat: object | None = None

    def _rules_dir(self) -> Path:
        return self.resource_root / "Rules"

    def _load_libmathcat(self):
        if self._libmathcat is not None:
            return self._libmathcat
        module_path = self.resource_root / "libmathcat_py.pyd"
        spec = importlib.util.spec_from_file_location("libmathcat_py", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules.setdefault("libmathcat_py", module)
        spec.loader.exec_module(module)
        self._libmathcat = module
        return module

    def _initialize(self, libmathcat) -> None:
        libmathcat.SetRulesDir(str(self._rules_dir()))
        libmathcat.SetPreference("TTS", "None")
        libmathcat.SetPreference("BrailleCode", "Nemeth")

    def get_braille_for_mathml(self, mathml_text: str) -> str:
        try:
            libmathcat = self._load_libmathcat()
            if getattr(self, "_initialized", False) is False:
                self._initialize(libmathcat)
                self._initialized = True
            libmathcat.SetMathML(mathml_text)
            return libmathcat.GetBraille("")
        except Exception as error:
            raise MathCATError(str(error)) from error
```

- [ ] **Step 3: Run the new unit tests to verify GREEN**

Run: `python3 -m unittest tests.test_math_service tests.test_mathcat_adapter -v`

Expected: PASS

### Task 4: Update conversion flow and spacing policy with failing tests first

**Files:**
- Modify: `client/tests/test_conversion_service.py`
- Modify: `client/conversion/service.py`

- [ ] **Step 1: Add failing conversion tests for text/math spacing and fail-fast propagation**

```python
    def test_translate_with_language_inserts_space_between_text_and_math_when_both_sides_are_non_whitespace(self) -> None:
        from conversion import service
        fake_translate_module = self._fake_translate_module()
        fake_translation_result = fake_translate_module.TranslationResult

        def fake_text_translate(_table_file, text, _dictionary_path, _translation_tables, _bopomofo_path):
            return fake_translation_result([text], list(text), [0] * len(text), [0])

        with patch.dict("sys.modules", {"translate": fake_translate_module}):
            with patch.object(service, "_translate_plain_text_segment", side_effect=fake_text_translate):
                with patch.object(service, "translate_math_segment", return_value="⠼⠁⠬⠃"):
                    result = service.translate_with_language(
                        "zh-tw.ctb", "計算$1+2$的值", Path("dictionary/default.csv"), {"default": "zh-tw.ctb"}, Path("data/Bopomofo2Braille.csv")
                    )

        self.assertEqual(result.raw, ["計算", " ", "1+2", " ", "的值"])

    def test_convert_text_for_output_propagates_math_conversion_failures(self) -> None:
        request = ConversionRequest(
            raw_text="$x$",
            table_file="zh-tw.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=Path("dictionary/default.csv"),
            data_dir=Path("data"),
            translation_tables={"default": "zh-tw.ctb"},
        )

        with patch("conversion.service.translate_and_wrap_both", side_effect=ValueError("math failed")):
            with self.assertRaisesRegex(ConversionStageError, "math failed"):
                convert_text_for_output(request, map_char=self._map_char)
```

- [ ] **Step 2: Run the focused tests to verify RED**

Run: `python3 -m unittest tests.test_conversion_service -v`

Expected: FAIL because spacing logic still concatenates text and math directly and `translate_math_segment` is not yet wired into `service.py`.

- [ ] **Step 3: Implement minimal conversion changes**

```python
from conversion.math_service import translate_math_segment


def build_text_translation_result(text: str):
    from translate import TranslationResult, translate
    return translate("zh-tw.ctb", " ", " ")


def _segment_needs_boundary_space(left_text: str, right_text: str) -> bool:
    return bool(left_text and right_text and not left_text[-1].isspace() and not right_text[0].isspace())
```

Also update the segment merge loop so it:

- calls `translate_math_segment()` for math segments
- inserts a plain-space `TranslationResult` between text/math neighbors only when `_segment_needs_boundary_space(...)` returns `True`

- [ ] **Step 4: Run the focused tests to verify GREEN**

Run: `python3 -m unittest tests.test_conversion_service -v`

Expected: PASS

### Task 5: Bundle runtime assets and dependency declarations

**Files:**
- Modify: `client/requirements.txt`
- Modify: `scripts/build_dotexpress.bat`
- Create: `client/mathcat/assets/Rules/...`
- Create: `client/mathcat/assets/libmathcat_py.pyd`

- [ ] **Step 1: Add the Python dependency**

```text
latex2mathml==3.81.0
```

- [ ] **Step 2: Copy the MathCAT runtime assets into the client tree**

Run:

```bash
mkdir -p client/mathcat/assets
cp -R /workspace/nvda/include/nvda-mathcat/assets/Rules client/mathcat/assets/
cp /workspace/nvda/include/nvda-mathcat/assets/libmathcat_py.pyd client/mathcat/assets/
```

Expected: `client/mathcat/assets/Rules` and `client/mathcat/assets/libmathcat_py.pyd` exist.

- [ ] **Step 3: Update PyInstaller data inclusion**

```bat
--add-data "mathcat/assets;mathcat/assets" ^
```

- [ ] **Step 4: Verify packaging-related paths compile**

Run: `python3 -m py_compile client/conversion/math_service.py client/conversion/mathcat_adapter.py client/conversion/service.py`

Expected: no output

### Task 6: Run focused verification

**Files:**
- Modify: none
- Test: `client/tests/test_math_service.py`
- Test: `client/tests/test_mathcat_adapter.py`
- Test: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Run the focused unit test suite**

Run: `python3 -m unittest tests.test_math_service tests.test_mathcat_adapter tests.test_conversion_service -v`

Expected: PASS

- [ ] **Step 2: Run compile checks for touched Python files**

Run: `python3 -m py_compile client/conversion/math_service.py client/conversion/mathcat_adapter.py client/conversion/service.py client/tests/test_math_service.py client/tests/test_mathcat_adapter.py client/tests/test_conversion_service.py`

Expected: no output

- [ ] **Step 3: Review the final diff**

Run: `git diff -- client/conversion/math_service.py client/conversion/mathcat_adapter.py client/conversion/service.py client/tests/test_math_service.py client/tests/test_mathcat_adapter.py client/tests/test_conversion_service.py client/requirements.txt scripts/build_dotexpress.bat client/mathcat/assets`

Expected: diff only shows the intended math conversion, runtime asset, dependency, and test changes.
