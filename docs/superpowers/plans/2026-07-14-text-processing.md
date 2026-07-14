# Custom Python Text Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one global unrestricted Python `main(text) -> str` preprocessing script that runs in the existing conversion worker before every real translation, while removing the non-standard punctuation and legacy secondary-output paths.

**Architecture:** A new wx-independent `conversion.preprocessing.user_script` module owns the script contract, UTF-8 persistence, atomic replacement, and per-conversion execution. `conversion.text.pipeline` applies that script before Bopomofo mapping and exposes script failures distinctly so `conversion.output` can raise `ConversionStageError("text_processing", error)`. The existing settings-dialog framework supplies a modeless singleton editor, while every production conversion continues through `ConversionJobRunner -> convert_text_with_alignment()`.

**Tech Stack:** Python 3, `ast`, `tempfile`, wxPython, `unittest`, gettext, existing conversion runtime adapters.

## Global Constraints

- Store the sole global script as `preprocessing.py` beside `default.csv` in `get_dictionary_directory()`; do not add a config JSON field.
- The default script is exactly `def main(input: str) -> str:\n    return input\n`.
- Validate without `exec()`: require exactly one top-level synchronous `main`, exactly one positional parameter, and no other parameters; parameter name and annotations are unrestricted.
- Execute with unrestricted Python capabilities, a fresh namespace containing `__name__` and `__file__`, no timeout, and no retained globals between conversions.
- Read and execute the file inside the existing conversion worker. Empty source text remains an early return and does not execute the script.
- Dual view uses processed text. Do not attempt original-to-processed diff alignment.
- Exports that need conversion use preprocessing; exports with cached braille do not retranslate.
- Preserve Unicode-braille dictionary replacements while removing punctuation tokenization and mapping.
- Remove `convert_text_for_output()` and `translate_and_wrap_both()` as secondary output paths; future string-only callers use `convert_text_with_alignment(...).display_text`.
- Keep user-visible Traditional Chinese translations and the compiled `.mo` in sync.
- Do not edit generated `client/braille/liblouis.dll`, runtime tables, or either liblouis/NVDA submodule.
- Do not automatically commit spec or plan authoring changes. The commit steps below apply only during implementation after the user chooses an execution workflow.

---

## File Structure

- Create `client/conversion/preprocessing/user_script.py`: default source, path construction, AST contract validation, UTF-8 load/save, atomic replacement, and unrestricted execution.
- Create `client/tests/test_user_preprocessing_script.py`: pure unit tests for script lifecycle and runtime semantics.
- Modify `client/conversion/text/pipeline.py`: call the user script before Bopomofo character mapping and preserve the underlying exception through `TextProcessingError`.
- Modify `client/conversion/output.py`: classify preprocessing separately as the `text_processing` stage and retain one alignment-producing output API.
- Modify `client/conversion/service.py`: pass text directly to language-aware translation after removing punctuation tokens; keep the public alignment wrapper only.
- Modify `client/conversion/preprocessing/literal_braille.py`: retain only Unicode-braille dictionary replacement helpers.
- Delete `client/conversion/preprocessing/punctuation.py` and `client/tests/test_punctuation.py`.
- Modify `client/conversion/wrapping.py`: remove the dedicated translate-and-wrap helper while retaining result merging and wrapping.
- Modify `client/main.py`: route the demo through `ConversionRequest` and `convert_text_with_alignment()`.
- Modify `client/settings/dialogs.py`: add the standalone modeless singleton `TextProcessingDialog`.
- Modify `client/ui/translation_menu.py`: add the menu descriptor in the approved order.
- Modify `client/gui.py`: bind/open the dialog, remove the dead string-only wrapper, and map `text_processing` errors.
- Create `client/tests/test_translation_menu.py`: lock the Translation menu labels and order.
- Modify `client/tests/test_settings_dialogs.py`, `client/tests/test_conversion_text_pipeline.py`, `client/tests/test_conversion_service.py`, `client/tests/test_gui_document_flows.py`, and `client/tests/test_translation_language_result.py`: add behavior coverage and remove obsolete API expectations.
- Modify `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, and regenerate `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`.

---

### Task 1: Implement the User Script Contract and File Lifecycle

**Files:**
- Create: `client/conversion/preprocessing/user_script.py`
- Create: `client/tests/test_user_preprocessing_script.py`

**Interfaces:**
- Consumes: a dictionary directory or concrete script `Path`, plus source text.
- Produces: `DEFAULT_PREPROCESSING_SCRIPT: str`, `PREPROCESSING_FILENAME: str`, `preprocessing_script_path(dictionary_dir) -> Path`, `load_preprocessing_script(path) -> str`, `validate_preprocessing_script(source, filename=...) -> None`, `save_preprocessing_script(path, source) -> None`, and `execute_preprocessing_script(path, input_text) -> str`.

- [ ] **Step 1: Write failing lifecycle and validation tests**

Create `client/tests/test_user_preprocessing_script.py` with these tests:

```python
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conversion.preprocessing.user_script import (
    DEFAULT_PREPROCESSING_SCRIPT,
    execute_preprocessing_script,
    load_preprocessing_script,
    preprocessing_script_path,
    save_preprocessing_script,
    validate_preprocessing_script,
)


class UserPreprocessingScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.directory = Path(self._tmpdir.name)
        self.path = preprocessing_script_path(self.directory)

    def test_path_uses_dictionary_directory(self) -> None:
        self.assertEqual(self.path, self.directory / "preprocessing.py")

    def test_missing_file_loads_identity_script_without_creating_file(self) -> None:
        self.assertEqual(load_preprocessing_script(self.path), DEFAULT_PREPROCESSING_SCRIPT)
        self.assertFalse(self.path.exists())

    def test_validation_accepts_helpers_imports_and_any_parameter_name(self) -> None:
        source = "import re\n\ndef clean(value):\n    return re.sub(' +', ' ', value)\n\ndef main(text):\n    return clean(text)\n"
        validate_preprocessing_script(source)

    def test_validation_rejects_syntax_error(self) -> None:
        with self.assertRaises(SyntaxError):
            validate_preprocessing_script("def main(:\n")

    def test_validation_does_not_execute_valid_module_code(self) -> None:
        validate_preprocessing_script(
            "raise RuntimeError('must not run while saving')\n"
            "def main(text):\n    return text\n"
        )

    def test_validation_requires_exactly_one_top_level_sync_main(self) -> None:
        invalid_sources = (
            "def helper(text):\n    return text\n",
            "async def main(text):\n    return text\n",
            "def main(text):\n    return text\n\ndef main(other):\n    return other\n",
            "def outer():\n    def main(text):\n        return text\n",
        )
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    validate_preprocessing_script(source)

    def test_validation_requires_one_positional_parameter_and_no_others(self) -> None:
        invalid_sources = (
            "def main():\n    return ''\n",
            "def main(first, second):\n    return first\n",
            "def main(text, *, option=False):\n    return text\n",
            "def main(*args):\n    return args[0]\n",
            "def main(text, **kwargs):\n    return text\n",
        )
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    validate_preprocessing_script(source)

    def test_save_uses_utf8_and_atomic_replace(self) -> None:
        source = "def main(text):\n    return text + '臺灣'\n"
        with patch("conversion.preprocessing.user_script.os.replace", wraps=os.replace) as replace:
            save_preprocessing_script(self.path, source)
        self.assertEqual(self.path.read_text(encoding="utf-8"), source)
        replace.assert_called_once()
        self.assertEqual(list(self.directory.glob(".preprocessing.py.*.tmp")), [])

    def test_invalid_save_does_not_overwrite_existing_file(self) -> None:
        original = "def main(text):\n    return text\n"
        self.path.write_text(original, encoding="utf-8")
        with self.assertRaises(SyntaxError):
            save_preprocessing_script(self.path, "def main(:\n")
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_execution_supports_helpers_imports_file_name_and_fresh_globals(self) -> None:
        self.path.write_text(
            "import re\n"
            "counter = globals().get('counter', 0) + 1\n"
            "def helper(text):\n    return re.sub(' +', ' ', text)\n"
            "def main(text):\n    return f'{counter}:{__file__}:{helper(text)}'\n",
            encoding="utf-8",
        )
        expected = f"1:{self.path}:a b"
        self.assertEqual(execute_preprocessing_script(self.path, "a  b"), expected)
        self.assertEqual(execute_preprocessing_script(self.path, "a  b"), expected)

    def test_execution_rejects_non_callable_main_and_non_string_return(self) -> None:
        invalid_sources = (
            "def main(text):\n    return text\nmain = None\n",
            "def main(text):\n    return 42\n",
        )
        for source in invalid_sources:
            with self.subTest(source=source):
                self.path.write_text(source, encoding="utf-8")
                with self.assertRaises(TypeError):
                    execute_preprocessing_script(self.path, "source")

    def test_execution_rejects_externally_written_invalid_contract(self) -> None:
        self.path.write_text("def main(first, second):\n    return first\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            execute_preprocessing_script(self.path, "source")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify the missing module failure**

Run from `client/`:

```bash
python3 -m unittest tests.test_user_preprocessing_script -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'conversion.preprocessing.user_script'`.

- [ ] **Step 3: Implement the pure script module**

Create `client/conversion/preprocessing/user_script.py`:

```python
from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path


PREPROCESSING_FILENAME = "preprocessing.py"
DEFAULT_PREPROCESSING_SCRIPT = "def main(input: str) -> str:\n    return input\n"


def preprocessing_script_path(dictionary_dir: Path | str) -> Path:
    return Path(dictionary_dir) / PREPROCESSING_FILENAME


def load_preprocessing_script(path: Path | str) -> str:
    source_path = Path(path)
    try:
        return source_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return DEFAULT_PREPROCESSING_SCRIPT


def validate_preprocessing_script(
    source: str,
    *,
    filename: str = PREPROCESSING_FILENAME,
) -> None:
    tree = ast.parse(source, filename=filename, mode="exec")
    compile(tree, filename, "exec")
    main_definitions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "main"
    ]
    if len(main_definitions) != 1 or not isinstance(main_definitions[0], ast.FunctionDef):
        raise ValueError("The script must define exactly one top-level synchronous main function.")
    arguments = main_definitions[0].args
    positional = [*arguments.posonlyargs, *arguments.args]
    if (
        len(positional) != 1
        or arguments.kwonlyargs
        or arguments.vararg is not None
        or arguments.kwarg is not None
    ):
        raise ValueError("main must define exactly one positional parameter and no other parameters.")


def save_preprocessing_script(path: Path | str, source: str) -> None:
    destination = Path(path)
    validate_preprocessing_script(source, filename=str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(source)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def execute_preprocessing_script(path: Path | str, input_text: str) -> str:
    source_path = Path(path)
    source = load_preprocessing_script(source_path)
    validate_preprocessing_script(source, filename=str(source_path))
    namespace = {
        "__name__": "__dotexpress_preprocessing__",
        "__file__": str(source_path),
    }
    exec(compile(source, str(source_path), "exec"), namespace)
    main = namespace.get("main")
    if not callable(main):
        raise TypeError("main is not callable.")
    output = main(input_text)
    if not isinstance(output, str):
        raise TypeError(f"main must return str, got {type(output).__name__}.")
    return output
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `python3 -m unittest tests.test_user_preprocessing_script -v`

Expected: all user-script lifecycle tests PASS.

- [ ] **Step 5: Commit the independently testable script engine**

```bash
git add client/conversion/preprocessing/user_script.py client/tests/test_user_preprocessing_script.py
git commit -m "feat: add user preprocessing script engine"
```

---

### Task 2: Insert Text Processing Into the Shared Conversion Pipeline

**Files:**
- Modify: `client/conversion/text/pipeline.py`
- Modify: `client/conversion/output.py`
- Modify: `client/tests/test_conversion_text_pipeline.py`
- Modify: `client/tests/test_conversion_service.py`
- Modify: `client/tests/test_gui_document_flows.py`

**Interfaces:**
- Consumes: Task 1's `preprocessing_script_path()` and `execute_preprocessing_script(path, input_text) -> str`.
- Produces: `TextProcessingError.error: Exception`, an updated `preprocess_source_text(..., preprocessing_path, execute_script=...) -> str`, and `ConversionStageError.stage == "text_processing"` for any script read/compile/execute/contract failure.

- [ ] **Step 1: Add failing ordering, dual-view, and stage tests**

Replace the source-preprocessing test in `client/tests/test_conversion_text_pipeline.py` and add the failure test:

```python
def test_preprocess_source_text_runs_user_script_before_bopomofo_mapping(self) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        data_dir = directory / "data"
        data_dir.mkdir()
        self._write_csv(
            data_dir,
            "BopomofoChar2Braille.csv",
            ["Bopomofo", "Braille"],
            [{"Bopomofo": "ㄅ", "Braille": "⠃"}],
        )
        events = []

        def execute_script(path: Path, text: str) -> str:
            events.append(("script", path, text))
            return text.replace("B", "ㄅ")

        def map_char(text: str, **kwargs) -> str:
            events.append(("map", text))
            return "⠃"

        result = preprocess_source_text(
            "B",
            data_dir=data_dir,
            preprocessing_path=directory / "preprocessing.py",
            execute_script=execute_script,
            map_char=map_char,
        )

        self.assertEqual(result, "⠃")
        self.assertEqual(
            events,
            [
                ("script", directory / "preprocessing.py", "B"),
                ("map", "ㄅ"),
            ],
        )

def test_preprocess_source_text_preserves_script_exception(self) -> None:
    error = RuntimeError("script boom")

    def execute_script(_path: Path, _text: str) -> str:
        raise error

    with self.assertRaises(TextProcessingError) as context:
        preprocess_source_text(
            "source",
            data_dir=Path("data"),
            preprocessing_path=Path("dictionary/preprocessing.py"),
            execute_script=execute_script,
        )

    self.assertIs(context.exception.error, error)

def test_preprocess_source_text_normalizes_system_exit(self) -> None:
    def execute_script(_path: Path, _text: str) -> str:
        raise SystemExit("requested exit")

    with self.assertRaises(TextProcessingError) as context:
        preprocess_source_text(
            "source",
            data_dir=Path("data"),
            preprocessing_path=Path("dictionary/preprocessing.py"),
            execute_script=execute_script,
        )

    self.assertIsInstance(context.exception.error, RuntimeError)
    self.assertEqual(str(context.exception.error), "SystemExit: requested exit")
```

Also import `ConversionOutput` from `conversion.service` and add this service-level early-return regression to `client/tests/test_conversion_service.py`:

```python
def test_empty_source_does_not_read_or_execute_preprocessing_script(self) -> None:
    dictionary_dir = self.test_dir / "dictionary"
    dictionary_dir.mkdir()
    dictionary_path = dictionary_dir / "default.csv"
    self._write_csv(dictionary_path, ["text", "braille", "type"], [])
    (dictionary_dir / "preprocessing.py").write_text(
        "raise RuntimeError('must not run')\ndef main(text):\n    return text\n",
        encoding="utf-8",
    )
    request = ConversionRequest(
        raw_text="",
        table_file="table.ctb",
        output_mode="unicode",
        width=40,
        dictionary_path=dictionary_path,
        data_dir=self.test_dir,
        translation_tables={"default": "table.ctb"},
    )

    output = convert_text_with_alignment(request, runtime=self._runtime())

    self.assertEqual(output, ConversionOutput("", (), ()))
```

In `client/tests/test_conversion_service.py`, add:

```python
def test_conversion_uses_processed_text_for_translation_and_dual_view(self) -> None:
    dictionary_dir = self.test_dir / "dictionary"
    dictionary_dir.mkdir()
    dictionary_path = dictionary_dir / "default.csv"
    self._write_csv(dictionary_path, ["text", "braille", "type"], [])
    (dictionary_dir / "preprocessing.py").write_text(
        "def main(text):\n    return text.replace('raw', 'processed')\n",
        encoding="utf-8",
    )
    request = ConversionRequest(
        raw_text="raw",
        table_file="table.ctb",
        output_mode="unicode",
        width=40,
        dictionary_path=dictionary_path,
        data_dir=self.test_dir,
        translation_tables={"default": "table.ctb"},
    )
    runtime = self._runtime()

    output = convert_text_with_alignment(request, map_char=lambda text, **kwargs: text, runtime=runtime)

    self.assertEqual(output.dual_view_segments[0].result.raw, ["processed"])

def test_conversion_reports_text_processing_stage(self) -> None:
    dictionary_dir = self.test_dir / "dictionary"
    dictionary_dir.mkdir(exist_ok=True)
    dictionary_path = dictionary_dir / "default.csv"
    self._write_csv(dictionary_path, ["text", "braille", "type"], [])
    (dictionary_dir / "preprocessing.py").write_text(
        "def main(text):\n    raise RuntimeError('script boom')\n",
        encoding="utf-8",
    )
    request = ConversionRequest(
        raw_text="raw",
        table_file="table.ctb",
        output_mode="unicode",
        width=40,
        dictionary_path=dictionary_path,
        data_dir=self.test_dir,
        translation_tables={"default": "table.ctb"},
    )

    with self.assertRaises(ConversionStageError) as context:
        convert_text_with_alignment(request, map_char=lambda text, **kwargs: text, runtime=self._runtime())

    self.assertEqual(context.exception.stage, "text_processing")
    self.assertEqual(str(context.exception.error), "script boom")
```

In `client/tests/test_gui_document_flows.py`, add a failure-message assertion beside the existing conversion error tests:

```python
def test_text_processing_failure_uses_its_own_message(self) -> None:
    frame = self._make_frame()
    result = gui.ConversionJobFailure(
        job_id=1,
        error=gui.ConversionStageError("text_processing", RuntimeError("script boom")),
        completion_policy=gui.ConversionCompletionPolicy(),
    )
    frame._complete_conversion = Mock()

    frame._finish_conversion_failure(result)

    frame._complete_conversion.assert_called_once_with(
        result.completion_policy,
        error_message=gui._("Text processing failed: {error}").format(error="script boom"),
    )
```

- [ ] **Step 2: Run the focused tests and verify the new API failures**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_conversion_text_pipeline \
  tests.test_conversion_service \
  tests.test_gui_document_flows.BrailleAppLifecycleTest.test_text_processing_failure_uses_its_own_message \
  -v
```

Expected: FAIL because `TextProcessingError`, the expanded `preprocess_source_text()` signature, and the `text_processing` message mapping do not exist.

- [ ] **Step 3: Implement script-first preprocessing and stage classification**

In `client/conversion/text/pipeline.py`, add the imports, exception, type alias, and replace `preprocess_source_text()`:

```python
from conversion.preprocessing.user_script import execute_preprocessing_script


ExecuteScript = Callable[[Path, str], str]


class TextProcessingError(Exception):
    def __init__(self, error: Exception):
        super().__init__(str(error))
        self.error = error


def preprocess_source_text(
    text: str,
    *,
    data_dir: Path,
    preprocessing_path: Path,
    execute_script: ExecuteScript = execute_preprocessing_script,
    map_char: Callable[..., str] = map_characters,
) -> str:
    try:
        processed_text = execute_script(preprocessing_path, text)
    except BaseException as error:
        normalized_error = (
            error
            if isinstance(error, Exception)
            else RuntimeError(f"{type(error).__name__}: {error}")
        )
        raise TextProcessingError(normalized_error) from error
    return map_char(
        processed_text,
        dictionary_path=data_dir / "BopomofoChar2Braille.csv",
        from_field="Bopomofo",
        to_field="Braille",
    )
```

In `client/conversion/output.py`, import `preprocessing_script_path` and `TextProcessingError`. Replace the beginning of `convert_text_with_alignment()` after the empty-input guard with separate catches:

```python
    try:
        text = preprocess_source_text(
            request.raw_text,
            data_dir=request.data_dir,
            preprocessing_path=preprocessing_script_path(request.dictionary_path.parent),
            map_char=map_char,
        )
    except TextProcessingError as error:
        raise ConversionStageError("text_processing", error.error) from error
    except Exception as error:
        raise ConversionStageError("translation", error) from error

    try:
        translations = translate_segments(
            request.table_file,
            text,
            request.dictionary_path,
            request.translation_tables,
            request.data_dir / "Bopomofo2Braille.csv",
            runtime=runtime,
        )
        braille_wrapped, _text_wrapped = wrap_translation_results(translations, request.width)
    except Exception as error:
        raise ConversionStageError("translation", error) from error
```

In `client/gui.py`, replace the two-way stage selection in `_finish_conversion_failure()` with:

```python
    def _finish_conversion_failure(self, result: ConversionJobFailure) -> None:
        message_templates = {
            "ascii": _("ASCII conversion failed: {error}"),
            "text_processing": _("Text processing failed: {error}"),
        }
        message_template = message_templates.get(
            result.error.stage,
            _("Translation failed: {error}"),
        )
        error_text = _(get_public_error_message(result.error.error))
        self._complete_conversion(
            result.completion_policy,
            error_message=message_template.format(error=error_text),
        )
```

- [ ] **Step 4: Run the pipeline and worker-facing regression tests**

Run:

```bash
python3 -m unittest \
  tests.test_user_preprocessing_script \
  tests.test_conversion_text_pipeline \
  tests.test_conversion_service \
  tests.test_conversion_jobs \
  tests.test_gui_document_flows \
  -v
```

Expected: PASS, including processed dual-view source and the distinct `text_processing` failure message. Existing export tests confirm cached braille is not reconverted and missing braille still uses `_start_conversion()`.

- [ ] **Step 5: Commit the shared pipeline integration**

```bash
git add \
  client/conversion/text/pipeline.py \
  client/conversion/output.py \
  client/gui.py \
  client/tests/test_conversion_text_pipeline.py \
  client/tests/test_conversion_service.py \
  client/tests/test_gui_document_flows.py
git commit -m "feat: run user script before translation"
```

---

### Task 3: Remove Non-Standard Punctuation Processing

**Files:**
- Modify: `client/conversion/service.py`
- Modify: `client/conversion/preprocessing/literal_braille.py`
- Modify: `client/tests/test_conversion_service.py`
- Delete: `client/conversion/preprocessing/punctuation.py`
- Delete: `client/tests/test_punctuation.py`

**Interfaces:**
- Consumes: processed plain text from Task 2.
- Produces: direct plain-text translation without punctuation tokens, while retaining `is_unicode_braille(text) -> bool` and `build_literal_translation_result(source_text, braille_text)` for dictionary replacements.

- [ ] **Step 1: Replace punctuation expectations with a failing pass-through regression**

Replace `test_literal_punctuation_bypasses_text_translation_and_preserves_source_token` in `client/tests/test_conversion_service.py` with:

```python
def test_nonstandard_punctuation_is_passed_to_normal_translation(self) -> None:
    text_translator = FakeTextTranslator()
    runtime = self._runtime(text_translator=text_translator)

    results = translate_with_language_segments(
        "table.ctb",
        "甲「乙」",
        self.dictionary_path,
        {"default": "table.ctb", "math": "Nemeth"},
        self.bopomofo_path,
        runtime=runtime,
    )

    self.assertEqual([result.raw for result in results], [["甲「乙」"]])
    self.assertEqual([call[0] for call in text_translator.calls], ["甲「乙」"])
```

Keep `test_unicode_braille_dictionary_replacement_bypasses_text_translation` unchanged. Delete the punctuation-width test because direct punctuation braille tokens no longer exist.

- [ ] **Step 2: Run the service test and verify the old mapping causes failure**

Run: `python3 -m unittest tests.test_conversion_service.ConversionServiceTest.test_nonstandard_punctuation_is_passed_to_normal_translation -v`

Expected: FAIL because the current service still splits and maps `「` and `」`.

- [ ] **Step 3: Simplify the service and literal-braille helper**

In `client/conversion/service.py`, delete the entire import from `conversion.preprocessing.literal_braille`; after punctuation token branching is removed, literal dictionary replacements remain owned by `conversion.text.pipeline`.

Replace the `for punctuation_token in preprocess_punctuation(...)` branch with one direct call:

```python
        if segment["type"] == "text":
            plain_results = _translate_plain_text_segment(
                table_file,
                segment["text"],
                dictionary_path,
                translation_tables,
                bopomofo_path,
                runtime=runtime,
            )
            if isinstance(plain_results, (list, tuple)):
                for result in plain_results:
                    segments_records.append(DualViewSegment(result=result, source_kind="text"))
            else:
                segments_records.append(DualViewSegment(result=plain_results, source_kind="text"))
```

Reduce `client/conversion/preprocessing/literal_braille.py` to:

```python
def is_unicode_braille(text: str) -> bool:
    return bool(text) and all("\u2800" <= character <= "\u28ff" for character in text)


def build_literal_translation_result(source_text: str, braille_text: str):
    from translate import TranslationResult

    braille = list(braille_text)
    return TranslationResult(
        [source_text],
        braille,
        [0] * len(braille),
        [0],
    )
```

Delete `client/conversion/preprocessing/punctuation.py` and `client/tests/test_punctuation.py`.

- [ ] **Step 4: Run punctuation-removal and dictionary regressions**

Run:

```bash
python3 -m unittest \
  tests.test_conversion_service \
  tests.test_conversion_text_pipeline \
  tests.test_conversion_text_dictionary_rules \
  -v
```

Expected: PASS. The new pass-through assertion and the existing Unicode-braille dictionary replacement assertion must both pass.

- [ ] **Step 5: Commit the punctuation removal**

```bash
git add \
  client/conversion/service.py \
  client/conversion/preprocessing/literal_braille.py \
  client/conversion/preprocessing/punctuation.py \
  client/tests/test_conversion_service.py \
  client/tests/test_punctuation.py
git commit -m "refactor: remove nonstandard punctuation preprocessing"
```

---

### Task 4: Remove Secondary Conversion Output Paths

**Files:**
- Modify: `client/conversion/output.py`
- Modify: `client/conversion/service.py`
- Modify: `client/conversion/wrapping.py`
- Modify: `client/gui.py`
- Modify: `client/main.py`
- Modify: `client/tests/test_conversion_text_pipeline.py`
- Modify: `client/tests/test_conversion_service.py`
- Modify: `client/tests/test_gui_document_flows.py`
- Modify: `client/tests/test_translation_language_result.py`

**Interfaces:**
- Consumes: `ConversionRequest` and `convert_text_with_alignment(request, runtime=...) -> ConversionOutput`.
- Produces: one conversion output entry point; string-only consumers read `.display_text`.

- [ ] **Step 1: Add a failing demo test for the sole output API**

Create this test in a new `client/tests/test_main_demo.py`:

```python
import unittest
from unittest.mock import Mock, patch

import main
from conversion.service import ConversionOutput


class MainDemoTest(unittest.TestCase):
    def test_demo_uses_alignment_conversion_output(self) -> None:
        runtime = Mock()
        output = ConversionOutput("braille", (), ())
        with (
            patch.object(main, "build_default_translation_runtime", return_value=runtime),
            patch.object(main, "convert_text_with_alignment", return_value=output) as convert,
            patch("builtins.print") as print_mock,
        ):
            main.run_demo("source")

        self.assertEqual(convert.call_args.args[0].raw_text, "source")
        print_mock.assert_called_once_with("braille")
        runtime.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the demo test and verify it fails on the legacy import**

Run: `python3 -m unittest tests.test_main_demo -v`

Expected: FAIL because `main` does not expose or use `convert_text_with_alignment`.

- [ ] **Step 3: Remove legacy functions and update the demo**

Replace `client/conversion/output.py` with the single alignment-producing implementation:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from adapters.translation.contracts import TranslationRuntime
from conversion.preprocessing.user_script import preprocessing_script_path
from conversion.text.char_maps import translate__mapping_char
from conversion.text.pipeline import TextProcessingError, preprocess_source_text


@dataclass(frozen=True)
class ConversionRequest:
    raw_text: str
    table_file: str
    output_mode: str
    width: int
    dictionary_path: Path
    data_dir: Path
    translation_tables: dict[str, str]


@dataclass(frozen=True)
class ConversionOutput:
    display_text: str
    translation_results: tuple[object, ...]
    dual_view_segments: tuple[object, ...] = ()


class ConversionStageError(Exception):
    def __init__(self, stage: str, error: Exception):
        super().__init__(str(error))
        self.stage = stage
        self.error = error


MapChar = Callable[..., str]
TranslateSegments = Callable[..., list[object]]
WrapTranslationResults = Callable[[list[object], int], tuple[str, str]]


def convert_text_with_alignment(
    request: ConversionRequest,
    *,
    translate_segments: TranslateSegments,
    wrap_translation_results: WrapTranslationResults,
    map_char: MapChar = translate__mapping_char,
    runtime: TranslationRuntime,
) -> ConversionOutput:
    if request.raw_text == "":
        return ConversionOutput("", ())
    try:
        text = preprocess_source_text(
            request.raw_text,
            data_dir=request.data_dir,
            preprocessing_path=preprocessing_script_path(request.dictionary_path.parent),
            map_char=map_char,
        )
    except TextProcessingError as error:
        raise ConversionStageError("text_processing", error.error) from error
    except Exception as error:
        raise ConversionStageError("translation", error) from error

    try:
        translations = translate_segments(
            request.table_file,
            text,
            request.dictionary_path,
            request.translation_tables,
            request.data_dir / "Bopomofo2Braille.csv",
            runtime=runtime,
        )
        braille_wrapped, _text_wrapped = wrap_translation_results(translations, request.width)
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

In `client/conversion/service.py`, remove the imports and wrappers for `convert_text_for_output`, `WrapBoth`, `_translate_and_wrap_both`, and `translate_and_wrap_both`.

Replace `client/conversion/wrapping.py` with the two result-only helpers:

```python
def merge_translation_results(translations):
    from translate import TranslationResult

    if not translations:
        return TranslationResult([], [], [], [])
    merged = TranslationResult([], [], [], [])
    for segment in translations:
        merged = merged + segment
    return merged


def wrap_translation_results(translations, width: int) -> tuple[str, str]:
    translation_result = merge_translation_results(translations)
    translation_result.reclean_braille_endspace()
    translation_result.bind_word_tokens()
    translation_result.reclean_token()
    return translation_result.wrap(width)
```

In `client/gui.py`, remove the `convert_text_for_output` import and the `_convert_text_for_output()` method.

Replace `client/main.py` with the sole-pipeline demo:

```python
from pathlib import Path

from adapters.translation.provider import build_default_translation_runtime
from config import DEFAULT_TRANSLATION_TABLES
from conversion.service import ConversionRequest, convert_text_with_alignment


BASE_DIR = Path(__file__).resolve().parent
SAMPLE_TEXT = """  但只要見到你，任誰都得劍拔弩張。
  ──德國劇作家與詩人布希萊特（Bertolt Bercht, 1898-1956）

p.15

    第一章 正義的殿堂
"""


def run_demo(text: str = SAMPLE_TEXT) -> None:
    runtime = build_default_translation_runtime()
    try:
        output = convert_text_with_alignment(
            ConversionRequest(
                raw_text=text,
                table_file="zh-tw.ctb",
                output_mode="unicode",
                width=40,
                dictionary_path=BASE_DIR / "dictionary" / "default.csv",
                data_dir=BASE_DIR / "data",
                translation_tables=DEFAULT_TRANSLATION_TABLES,
            ),
            runtime=runtime,
        )
        print(output.display_text)
    finally:
        runtime.close()


if __name__ == "__main__":
    run_demo()
```

Delete the five methods whose names begin with `test_convert_text_for_output_` from `client/tests/test_conversion_service.py`, and delete both duplicated `test_convert_text_for_output_forwards_runtime` methods from `client/tests/test_gui_document_flows.py`.

Replace `test_both_output_entry_points_share_source_preprocessing` in `client/tests/test_conversion_text_pipeline.py` with:

```python
def test_alignment_output_entry_applies_source_preprocessing_once(self) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        data_dir = directory / "data"
        dictionary_dir = directory / "dictionary"
        data_dir.mkdir()
        dictionary_dir.mkdir()
        dictionary_path = self._write_csv(
            dictionary_dir,
            "default.csv",
            ["text", "braille", "type"],
            [],
        )
        (dictionary_dir / "preprocessing.py").write_text(
            "def main(text):\n    return text.replace('raw', 'processed')\n",
            encoding="utf-8",
        )
        self._write_csv(data_dir, "BopomofoChar2Braille.csv", ["Bopomofo", "Braille"], [])
        self._write_csv(data_dir, "Bopomofo2Braille.csv", ["Bopomofo", "Braille"], [])
        request = ConversionRequest(
            raw_text="raw",
            table_file="table.ctb",
            output_mode="unicode",
            width=40,
            dictionary_path=dictionary_path,
            data_dir=data_dir,
            translation_tables={"default": "table.ctb"},
        )
        translated_texts = []

        result = convert_text_with_alignment(
            request,
            translate_segments=lambda _table, text, *_args, **_kwargs: translated_texts.append(text) or [],
            wrap_translation_results=lambda translations, width: ("wrapped", "processed"),
            map_char=lambda text, **kwargs: text,
            runtime=self._runtime(),
        )

        self.assertEqual(result.display_text, "wrapped")
        self.assertEqual(translated_texts, ["processed"])
```

Rewrite `client/tests/test_translation_language_result.py` to retain its live language-boundary coverage without the removed output helper:

```python
import ctypes
import unittest
from pathlib import Path


if not hasattr(ctypes, "WINFUNCTYPE"):
    raise unittest.SkipTest("liblouis bindings require WINFUNCTYPE on this platform")

try:
    from braille import liblouis  # noqa: F401
except Exception as exc:
    raise unittest.SkipTest(f"liblouis bindings unavailable: {exc}") from exc

from adapters.translation.provider import build_default_translation_runtime
from config import DEFAULT_TRANSLATION_TABLES
from conversion.service import translate_with_language


BASE_DIR = Path(__file__).resolve().parents[1]


def test_add_blank_between_language_change() -> None:
    runtime = build_default_translation_runtime()
    try:
        result = translate_with_language(
            "zh-tw.ctb",
            "嶼我I起",
            BASE_DIR / "dictionary" / "default.csv",
            DEFAULT_TRANSLATION_TABLES,
            BASE_DIR / "data" / "Bopomofo2Braille.csv",
            runtime=runtime,
        )
    finally:
        runtime.close()
    assert "".join(result.raw) == "嶼我 I 起"
```

- [ ] **Step 4: Run focused tests and prove legacy symbols are gone**

Run:

```bash
python3 -m unittest \
  tests.test_main_demo \
  tests.test_conversion_text_pipeline \
  tests.test_conversion_service \
  tests.test_gui_document_flows \
  -v
```

Expected: PASS.

Run:

```bash
rg -n "convert_text_for_output|translate_and_wrap_both|WrapBoth|ConvertWithAlignment" client --glob '*.py'
```

Expected: no matches.

- [ ] **Step 5: Commit the single output path**

```bash
git add \
  client/conversion/output.py \
  client/conversion/service.py \
  client/conversion/wrapping.py \
  client/gui.py \
  client/main.py \
  client/tests/test_main_demo.py \
  client/tests/test_conversion_text_pipeline.py \
  client/tests/test_conversion_service.py \
  client/tests/test_gui_document_flows.py \
  client/tests/test_translation_language_result.py
git commit -m "refactor: keep one conversion output path"
```

---

### Task 5: Build the Modeless Text Processing Dialog

**Files:**
- Modify: `client/settings/dialogs.py`
- Modify: `client/tests/test_settings_dialogs.py`

**Interfaces:**
- Consumes: Task 1's `load_preprocessing_script(path)` and `save_preprocessing_script(path, source)`.
- Produces: `TextProcessingDialog.show_singleton(parent, script_path) -> TextProcessingDialog`, with `INITIAL_SIZE == (720, 440)`, `MIN_SIZE == (520, 300)`, and editor accessible name `Text Processing Python Code`.

- [ ] **Step 1: Extend the wx stub and write failing dialog tests**

In `_install_stub_modules()` in `client/tests/test_settings_dialogs.py`, add this stub beside the other widget stubs:

Add `from pathlib import Path` to the test module imports.

First add title capture to `_Widget.__init__` immediately after its existing `self.label` assignment:

```python
            self.title = kwargs.get("title", "")
```

```python
    class _Font:
        def __init__(self):
            self.family = None

        def SetFamily(self, family):
            self.family = family

    class TextCtrl(Window):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._value = kwargs.get("value", "")
            self._font = _Font()

        def GetValue(self):
            return self._value

        def SetValue(self, value):
            self._value = value

        def GetFont(self):
            return self._font

        def SetFont(self, font):
            self._font = font
```

Register the class and constants in the same stub factory:

```python
    wx.TextCtrl = TextCtrl
    wx.TE_MULTILINE = 0x0004
    wx.TE_RICH2 = 0x8000
    wx.TE_DONTWRAP = 0x40000000
    wx.FONTFAMILY_TELETYPE = 1
```

Add these tests:

```python
class TextProcessingDialogTest(unittest.TestCase):
    def make_dialog(self):
        from settings.dialogs import TextProcessingDialog

        dialog = object.__new__(TextProcessingDialog)
        dialog.script_path = Path("dictionary/preprocessing.py")
        dialog.editor = Mock()
        dialog.Destroy = Mock()
        return dialog

    def test_initial_size_title_and_accessible_editor_name(self) -> None:
        from settings.dialogs import TextProcessingDialog
        import settings.dialogs as dialogs_module

        with (
            patch("settings.dialogs.load_preprocessing_script", return_value="def main(text):\n    return text\n"),
            patch("settings.dialogs._", side_effect=lambda text: text),
        ):
            dialog = TextProcessingDialog(None, script_path=Path("dictionary/preprocessing.py"))

        self.assertEqual(dialog.size, (720, 440))
        self.assertEqual(dialog.title, "Text Processing")
        self.assertEqual(dialog.editor.GetName(), "Text Processing Python Code")

    def test_apply_saves_editor_source(self) -> None:
        dialog = self.make_dialog()
        dialog.editor.GetValue.return_value = "def main(text):\n    return text\n"
        with patch("settings.dialogs.save_preprocessing_script") as save:
            self.assertTrue(dialog.on_apply())
        save.assert_called_once_with(dialog.script_path, dialog.editor.GetValue.return_value)

    def test_apply_failure_keeps_dialog_open_and_focuses_editor(self) -> None:
        dialog = self.make_dialog()
        dialog.editor.GetValue.return_value = "def main(:\n"
        with (
            patch("settings.dialogs.save_preprocessing_script", side_effect=SyntaxError("invalid syntax")),
            patch.object(wx, "MessageBox") as message_box,
        ):
            self.assertFalse(dialog.on_apply())
        dialog.Destroy.assert_not_called()
        dialog.editor.SetFocus.assert_called_once_with()
        message_box.assert_called_once()

    def test_ok_destroys_only_after_successful_apply(self) -> None:
        dialog = self.make_dialog()
        dialog.on_apply = Mock(return_value=True)
        dialog._destroy = Mock()
        dialog.on_ok()
        dialog._destroy.assert_called_once_with()

    def test_cancel_does_not_save(self) -> None:
        dialog = self.make_dialog()
        dialog._destroy = Mock()
        with patch("settings.dialogs.save_preprocessing_script") as save:
            dialog.on_cancel()
        save.assert_not_called()
        dialog._destroy.assert_called_once_with()

    def test_show_singleton_reuses_live_dialog(self) -> None:
        from settings.dialogs import TextProcessingDialog

        existing = Mock()
        original = TextProcessingDialog._instance
        TextProcessingDialog._instance = existing
        try:
            result = TextProcessingDialog.show_singleton(
                parent=Mock(),
                script_path=Path("dictionary/preprocessing.py"),
            )
        finally:
            TextProcessingDialog._instance = original

        self.assertIs(result, existing)
        existing.Iconize.assert_called_once_with(False)
        existing.Raise.assert_called_once_with()
        existing.SetFocus.assert_called_once_with()
```

- [ ] **Step 2: Run the dialog tests and verify the missing class failure**

Run: `python3 -m unittest tests.test_settings_dialogs.TextProcessingDialogTest -v`

Expected: FAIL because `TextProcessingDialog` does not exist.

- [ ] **Step 3: Implement the dialog in the existing settings framework**

Import the Task 1 load/save helpers in `client/settings/dialogs.py`, then add this class immediately after `SettingsDialog`:

```python
class TextProcessingDialog(SettingsDialog):
    _instance: "TextProcessingDialog | None" = None

    def __init__(self, parent, *, script_path: Path | str) -> None:
        self.script_path = Path(script_path)
        source = load_preprocessing_script(self.script_path)
        super().__init__(parent, title=_("Text Processing"))
        self._build_layout(source)
        self.SetMinSize(self.MIN_SIZE)
        self.SetSize(self.INITIAL_SIZE)
        self.CentreOnParent()

    def _build_layout(self, source: str) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.editor = wx.TextCtrl(
            self,
            value=source,
            style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_DONTWRAP,
        )
        self.editor.SetName(_("Text Processing Python Code"))
        font = self.editor.GetFont()
        font.SetFamily(wx.FONTFAMILY_TELETYPE)
        self.editor.SetFont(font)
        sizer.Add(self.editor, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(self, wx.ID_OK, _("OK"))
        cancel_button = wx.Button(self, wx.ID_CANCEL, _("Cancel"))
        apply_button = wx.Button(self, wx.ID_APPLY, _("Apply"))
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        apply_button.Bind(wx.EVT_BUTTON, self.on_apply)
        for button in (ok_button, cancel_button, apply_button):
            buttons.Add(button, 0, wx.ALL, 5)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.SetSizer(sizer)

    def on_apply(self, event=None) -> bool:
        try:
            save_preprocessing_script(self.script_path, self.editor.GetValue())
        except (OSError, SyntaxError, ValueError) as error:
            display_error = _(str(error)) if isinstance(error, ValueError) else error
            wx.MessageBox(
                _("Unable to save text processing script: {error}").format(error=display_error),
                _("Text Processing"),
                wx.OK | wx.ICON_ERROR,
                parent=self,
            )
            self.editor.SetFocus()
            return False
        return True

    def on_ok(self, event=None) -> None:
        if self.on_apply():
            self._destroy()

    def on_cancel(self, event=None) -> None:
        self._destroy()

    def _destroy(self) -> None:
        if TextProcessingDialog._instance is self:
            TextProcessingDialog._instance = None
        self.Destroy()

    @staticmethod
    def _is_destroyed_window_error(error: Exception) -> bool:
        if isinstance(error, getattr(wx, "PyDeadObjectError", ())):
            return True
        if not isinstance(error, (ReferenceError, RuntimeError)):
            return False
        message = str(error).lower()
        return (
            "wrapped c/c++ object" in message
            or "has been deleted" in message
            or "already deleted" in message
            or "destroyed" in message
        )

    @classmethod
    def show_singleton(cls, *, parent, script_path: Path | str) -> "TextProcessingDialog":
        instance = cls._instance
        if instance is not None:
            try:
                instance.Iconize(False)
                instance.Raise()
                instance.SetFocus()
                return instance
            except (ReferenceError, RuntimeError, wx.PyDeadObjectError) as error:
                if not cls._is_destroyed_window_error(error):
                    raise
                cls._instance = None
        instance = cls(parent, script_path=script_path)
        cls._instance = instance
        instance.Show()
        return instance
```

Add this unexpected-error regression to `TextProcessingDialogTest`:

```python
    def test_show_singleton_reraises_unexpected_existing_dialog_error(self) -> None:
        from settings.dialogs import TextProcessingDialog

        existing = Mock()
        existing.Iconize.side_effect = RuntimeError("unexpected")
        original = TextProcessingDialog._instance
        TextProcessingDialog._instance = existing
        try:
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                TextProcessingDialog.show_singleton(
                    parent=Mock(),
                    script_path=Path("dictionary/preprocessing.py"),
                )
            self.assertIs(TextProcessingDialog._instance, existing)
        finally:
            TextProcessingDialog._instance = original
```

- [ ] **Step 4: Run the complete settings-dialog suite**

Run: `python3 -m unittest tests.test_settings_dialogs -v`

Expected: PASS, including dialog size, accessible name, save validation, cancellation, and singleton reuse.

- [ ] **Step 5: Commit the dialog**

```bash
git add client/settings/dialogs.py client/tests/test_settings_dialogs.py
git commit -m "feat: add text processing dialog"
```

---

### Task 6: Wire the Menu, Error UX, and Localization

**Files:**
- Modify: `client/ui/translation_menu.py`
- Create: `client/tests/test_translation_menu.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_gui_document_flows.py`
- Modify: `client/locales/dotexpress.pot`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

**Interfaces:**
- Consumes: Task 1's `preprocessing_script_path()` and Task 5's `TextProcessingDialog.show_singleton()`.
- Produces: Translation menu order `Convert`, `Dual View`, `Text Processing`, `Dictionary Management...`, `Settings`; handler `BrailleFrame.on_open_text_processing()`; localized script-open/save/conversion errors.

- [ ] **Step 1: Write failing menu and GUI handler tests**

Create `client/tests/test_translation_menu.py`:

```python
import unittest

from ui.translation_menu import get_translation_menu_items


class TranslationMenuTest(unittest.TestCase):
    def test_items_have_stable_keys_labels_and_order(self) -> None:
        self.assertEqual(
            get_translation_menu_items(),
            [
                ("convert", "Convert"),
                ("dual_view", "Dual View"),
                ("text_processing", "Text Processing"),
                ("dictionaries", "Dictionary Management..."),
                ("settings", "Settings"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
```

Add to `client/tests/test_gui_document_flows.py`:

```python
def test_open_text_processing_uses_dictionary_directory_script(self) -> None:
    frame = object.__new__(gui.BrailleFrame)
    frame.dictionary_dir = Path("dictionary")
    with patch.object(gui.TextProcessingDialog, "show_singleton") as show:
        frame.on_open_text_processing(None)
    show.assert_called_once_with(
        parent=frame,
        script_path=Path("dictionary/preprocessing.py"),
    )

def test_open_text_processing_reports_read_error(self) -> None:
    frame = object.__new__(gui.BrailleFrame)
    frame.dictionary_dir = Path("dictionary")
    with (
        patch.object(gui.TextProcessingDialog, "show_singleton", side_effect=OSError("denied")),
        patch.object(gui.wx, "MessageBox") as message_box,
    ):
        frame.on_open_text_processing(None)
    message_box.assert_called_once_with(
        gui._("Unable to open text processing script: {error}").format(error="denied"),
        gui._("Text Processing"),
        gui.wx.OK | gui.wx.ICON_ERROR,
        parent=frame,
    )
```

- [ ] **Step 2: Run the tests and verify menu/handler failures**

Run:

```bash
python3 -m unittest \
  tests.test_translation_menu \
  tests.test_gui_document_flows.BrailleAppLifecycleTest.test_open_text_processing_uses_dictionary_directory_script \
  tests.test_gui_document_flows.BrailleAppLifecycleTest.test_open_text_processing_reports_read_error \
  -v
```

Expected: FAIL because the descriptor, dialog import, and handler are absent.

- [ ] **Step 3: Add the menu descriptor and GUI handler**

Change `client/ui/translation_menu.py` to return:

```python
def get_translation_menu_items() -> list[tuple[str, str]]:
    return [
        ("convert", "Convert"),
        ("dual_view", "Dual View"),
        ("text_processing", "Text Processing"),
        ("dictionaries", "Dictionary Management..."),
        ("settings", "Settings"),
    ]
```

In `client/gui.py`, import `preprocessing_script_path` and `TextProcessingDialog`, add `"text_processing": self.on_open_text_processing` to `translation_handlers`, and add:

```python
    def on_open_text_processing(self, _event) -> None:
        try:
            TextProcessingDialog.show_singleton(
                parent=self,
                script_path=preprocessing_script_path(self.dictionary_dir),
            )
        except OSError as error:
            wx.MessageBox(
                _("Unable to open text processing script: {error}").format(error=error),
                _("Text Processing"),
                wx.OK | wx.ICON_ERROR,
                parent=self,
            )
```

Add these strings to the top-level `_MENU_TRANSLATION_MARKERS` tuple in `client/gui.py` so the repository's top-level-only POT generator sees dialog strings too:

```python
_("Text Processing"),
_("Text Processing Python Code"),
_("Unable to open text processing script: {error}"),
_("Unable to save text processing script: {error}"),
_("Text processing failed: {error}"),
_("The script must define exactly one top-level synchronous main function."),
_("main must define exactly one positional parameter and no other parameters."),
```

- [ ] **Step 4: Update catalogs and compile Traditional Chinese messages**

Regenerate the POT on Windows from the repository root:

```bat
scripts\generate-pot.bat
```

Merge it into the PO:

```bash
msgmerge --update \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po \
  client/locales/dotexpress.pot
```

Expected: exit code 0. Resolve any fuzzy marker on the seven new messages while setting these exact translations in `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`:

```po
msgid "Text Processing"
msgstr "文字處理"

msgid "Text Processing Python Code"
msgstr "文字處理 Python 程式"

msgid "Unable to open text processing script: {error}"
msgstr "無法開啟文字處理程式：{error}"

msgid "Unable to save text processing script: {error}"
msgstr "無法儲存文字處理程式：{error}"

msgid "Text processing failed: {error}"
msgstr "文字處理失敗：{error}"

msgid "The script must define exactly one top-level synchronous main function."
msgstr "程式必須恰好定義一個頂層同步 main 函式。"

msgid "main must define exactly one positional parameter and no other parameters."
msgstr "main 必須恰好定義一個位置參數，且不得有其他參數。"
```

Compile and validate:

```bash
msgfmt --check \
  --output-file=client/locales/zh_TW/LC_MESSAGES/dotexpress.mo \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected: exit code 0 and an updated `.mo`.

- [ ] **Step 5: Run GUI/menu regressions**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_translation_menu \
  tests.test_settings_dialogs \
  tests.test_gui_document_flows \
  tests.test_input_shortcuts \
  tests.test_section_navigation \
  -v
```

Expected: PASS. `Ctrl+Enter` remains bound to the same conversion job path.

- [ ] **Step 6: Commit menu and localization integration**

```bash
git add \
  client/ui/translation_menu.py \
  client/gui.py \
  client/tests/test_translation_menu.py \
  client/tests/test_gui_document_flows.py \
  client/locales/dotexpress.pot \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "feat: expose text processing settings"
```

---

### Task 7: Run Cross-Flow Verification and Windows UI Acceptance

**Files:**
- Verify only; fix failures in the task that owns the affected file.

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: evidence that every live conversion entry uses the script, cached export semantics remain unchanged, localization compiles, and no removed path remains.

- [ ] **Step 1: Run all focused feature suites together**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_user_preprocessing_script \
  tests.test_conversion_text_pipeline \
  tests.test_conversion_text_dictionary_rules \
  tests.test_conversion_service \
  tests.test_conversion_jobs \
  tests.test_main_demo \
  tests.test_settings_dialogs \
  tests.test_translation_menu \
  tests.test_gui_document_flows \
  tests.test_input_shortcuts \
  tests.test_section_navigation \
  -v
```

Expected: PASS, with only existing platform-dependent skips if any are selected indirectly.

- [ ] **Step 2: Run the complete client unit suite**

Run from `client/`:

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS; Windows/liblouis-only modules may report their existing explicit skips on non-Windows hosts.

- [ ] **Step 3: Verify removed symbols and deleted punctuation module**

Run from the repository root:

```bash
rg -n "convert_text_for_output|translate_and_wrap_both|preprocess_punctuation|tokenize_punctuation" client --glob '*.py'
```

Expected: no matches.

Run:

```bash
test ! -e client/conversion/preprocessing/punctuation.py
test ! -e client/tests/test_punctuation.py
```

Expected: exit code 0.

- [ ] **Step 4: Validate gettext and whitespace**

Run:

```bash
msgfmt --check \
  --output-file=/tmp/dotexpress.mo \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po
git diff --check
```

Expected: both commands exit 0.

- [ ] **Step 5: Perform Windows manual acceptance**

On the packaged/development Windows client:

1. Open Translation -> Text Processing and verify a single resizable `720 × 440` dialog appears with focusable Python editor and `OK`, `Cancel`, `Apply`.
2. Reopen the menu item while the dialog is open and verify the same dialog is raised.
3. Save `def main(text): return text.replace("foo", "bar")`, convert a document containing `foo` with Ctrl+Enter, and verify output and dual view use `bar`.
4. Export an unconverted document and verify preprocessing runs; export a document with cached braille and verify it does not retranslate.
5. Save a syntax error and verify the dialog stays open and the previous file remains unchanged.
6. Externally change `preprocessing.py`, convert again, and verify the next worker run uses the new file.
7. Make `main` raise an exception and verify the existing output remains while the UI reports `Text processing failed` without a traceback.
8. Switch to Traditional Chinese and verify the menu, dialog labels, and error templates use the approved translations.

- [ ] **Step 6: Record final implementation status**

Run:

```bash
git status --short
git log --oneline -6
```

Expected: only intentional implementation/spec/plan changes are present; implementation commits are scoped to the task boundaries above.
