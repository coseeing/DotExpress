# Refactor Phase Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the largest DotExpress client responsibility hotspots by extracting document workflow state, dictionary entry domain logic, conversion job orchestration, and conversion pipeline internals without changing user-visible behavior.

**Architecture:** Keep wxPython UI as the outer coordination layer while moving state transitions and domain logic into smaller non-wx modules. Preserve public conversion entry points and current GUI behavior; each phase adds focused tests first, routes existing code through the new boundary, and keeps existing integration tests green.

**Tech Stack:** Python 3, wxPython, `dataclasses`, `threading`, `unittest`, `unittest.mock`

---

## File Structure

- Create `client/documents/controller.py`: non-wx document workflow state and dual-view cache updates.
- Create `client/tests/test_document_controller.py`: focused controller tests.
- Modify `client/gui.py`: route document state transitions through `DocumentController` while keeping wx control updates in the frame.
- Create `client/dictionaries/entries.py`: dictionary entry model, type normalization, validation, CSV load/save.
- Create `client/tests/test_dictionary_entries.py`: focused entry validation and CSV tests.
- Modify `client/dialog.py`: import entry model/helpers from `dictionaries.entries`; keep wx interactions in dialog classes.
- Modify `client/tests/test_speech_symbols_dialog.py`: import `DictionaryEntry` and `load_dictionary_entries` from `dictionaries.entries`.
- Modify `client/tests/test_dictionary_management_dialog.py`: keep dialog behavior tests passing after moved imports.
- Create `client/conversion/jobs.py`: conversion job request/result and thread runner.
- Create `client/tests/test_conversion_jobs.py`: job runner success, failure, and stale-job tests without wx.
- Modify `client/gui.py`: delegate conversion worker execution to `ConversionJobRunner`; keep busy state, dialogs, output updates, and message boxes in the frame.
- Create `client/conversion/segments.py`: inline math segmentation and boundary spacing helpers.
- Create `client/conversion/plain_text.py`: dictionary, language detection, table selection, and text translator orchestration.
- Create `client/conversion/wrapping.py`: merge and wrapping helpers.
- Create `client/conversion/output.py`: output formatting and public error-message helpers.
- Modify `client/conversion/service.py`: keep public facade APIs and call the new internal modules.
- Modify `client/tests/test_conversion_service.py`: update imports for moved helpers and keep facade behavior coverage.

## Task 1: Document Workflow Controller

**Files:**
- Create: `client/documents/controller.py`
- Create: `client/tests/test_document_controller.py`
- Modify: `client/gui.py`
- Reference: `client/documents/session.py`
- Reference: `client/documents/workspace.py`

- [ ] **Step 1: Write focused controller tests**

Create `client/tests/test_document_controller.py`:

```python
import unittest

from documents.controller import DocumentController
from documents.workspace import Document


class DocumentControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = [
            Document("alpha", "a", "braille-a"),
            Document("math", "m", "braille-m"),
            Document("zoo", "z", "braille-z"),
        ]

    def test_open_existing_document_updates_open_and_selected_names(self) -> None:
        controller = DocumentController(documents=list(self.documents))

        result = controller.open_document("math")

        self.assertEqual(result.document, Document("math", "m", "braille-m"))
        self.assertEqual(controller.open_document_name, "math")
        self.assertEqual(controller.selected_document_name, "math")

    def test_open_missing_document_clears_open_and_selected_names(self) -> None:
        controller = DocumentController(documents=list(self.documents), open_document_name="alpha", selected_document_name="alpha")

        result = controller.open_document("missing")

        self.assertIsNone(result.document)
        self.assertIsNone(controller.open_document_name)
        self.assertIsNone(controller.selected_document_name)

    def test_replace_document_updates_matching_document_without_changing_selection(self) -> None:
        controller = DocumentController(documents=list(self.documents), open_document_name="alpha", selected_document_name="alpha")

        replaced = controller.replace_document(Document("math", "new", "new-braille"))

        self.assertTrue(replaced)
        self.assertEqual(controller.get_document("math"), Document("math", "new", "new-braille"))
        self.assertEqual(controller.open_document_name, "alpha")
        self.assertEqual(controller.selected_document_name, "alpha")

    def test_rename_document_updates_document_names_and_dual_view_cache(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_document_name="math",
            selected_document_name="math",
            dual_view_results_by_document={"math": ("alignment",)},
        )

        renamed = controller.rename_document("math", "numbers")

        self.assertEqual(renamed, Document("numbers", "m", "braille-m"))
        self.assertEqual(controller.open_document_name, "numbers")
        self.assertEqual(controller.selected_document_name, "numbers")
        self.assertIsNone(controller.get_document("math"))
        self.assertEqual(controller.dual_view_results_by_document, {"numbers": ("alignment",)})

    def test_delete_open_document_prefers_neighbor_and_removes_dual_view_cache(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_document_name="math",
            selected_document_name="math",
            dual_view_results_by_document={"math": ("alignment",), "zoo": ("z",)},
        )

        result = controller.delete_document("math")

        self.assertTrue(result.deleted)
        self.assertEqual(result.preferred_name, "alpha")
        self.assertIsNone(controller.open_document_name)
        self.assertEqual(controller.selected_document_name, "alpha")
        self.assertIsNone(controller.get_document("math"))
        self.assertEqual(controller.dual_view_results_by_document, {"zoo": ("z",)})

    def test_delete_all_documents_clears_state_and_cache(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_document_name="alpha",
            selected_document_name="alpha",
            dual_view_results_by_document={"alpha": ("alignment",)},
        )

        controller.delete_all_documents()

        self.assertEqual(controller.documents, [])
        self.assertIsNone(controller.open_document_name)
        self.assertIsNone(controller.selected_document_name)
        self.assertEqual(controller.dual_view_results_by_document, {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the controller tests and verify they fail**

Run from `client/`:

```bash
python3 -m unittest tests.test_document_controller -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'documents.controller'`.

- [ ] **Step 3: Implement the controller module**

Create `client/documents/controller.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

from documents.session import (
    find_document,
    get_document_names,
    plan_delete_document,
    plan_open_document,
    replace_document,
)
from documents.workspace import Document


@dataclass(frozen=True)
class OpenDocumentResult:
    document: Document | None


@dataclass(frozen=True)
class DeleteDocumentResult:
    deleted: bool
    preferred_name: str | None
    was_open: bool


@dataclass
class DocumentController:
    documents: list[Document] = field(default_factory=list)
    selected_document_name: str | None = None
    open_document_name: str | None = None
    dual_view_results_by_document: dict[str, tuple[object, ...]] = field(default_factory=dict)

    def get_document_names(self) -> list[str]:
        return get_document_names(self.documents)

    def get_document(self, name: str | None) -> Document | None:
        return find_document(self.documents, name)

    def sort_documents(self) -> None:
        self.documents.sort(key=lambda document: (document.name.casefold(), document.name))

    def replace_document(self, updated_document: Document) -> bool:
        return replace_document(self.documents, updated_document)

    def open_document(self, name: str | None) -> OpenDocumentResult:
        decision = plan_open_document(self.documents, name)
        self.open_document_name = decision.open_name
        self.selected_document_name = decision.selected_name
        return OpenDocumentResult(decision.document)

    def rename_document(self, source_name: str, new_name: str) -> Document | None:
        selected_document = self.get_document(source_name)
        if selected_document is None:
            return None
        renamed_document = Document(
            name=new_name,
            text=selected_document.text,
            braille=selected_document.braille,
        )
        if not self.replace_document(renamed_document):
            return None
        if self.open_document_name == source_name:
            self.open_document_name = new_name
        if self.selected_document_name == source_name:
            self.selected_document_name = new_name
        if source_name in self.dual_view_results_by_document:
            self.dual_view_results_by_document[new_name] = self.dual_view_results_by_document.pop(source_name)
        return renamed_document

    def delete_document(self, name: str) -> DeleteDocumentResult:
        if self.get_document(name) is None:
            return DeleteDocumentResult(deleted=False, preferred_name=self.selected_document_name, was_open=False)
        decision = plan_delete_document(self.documents, name, self.open_document_name)
        self.documents = [document for document in self.documents if document.name != name]
        self.dual_view_results_by_document.pop(name, None)
        if decision.was_open:
            self.open_document_name = None
        self.selected_document_name = decision.preferred_name
        return DeleteDocumentResult(
            deleted=True,
            preferred_name=decision.preferred_name,
            was_open=decision.was_open,
        )

    def delete_all_documents(self) -> None:
        self.documents = []
        self.selected_document_name = None
        self.open_document_name = None
        self.dual_view_results_by_document.clear()
```

- [ ] **Step 4: Run focused controller tests**

Run:

```bash
python3 -m unittest tests.test_document_controller -v
```

Expected: `OK`.

- [ ] **Step 5: Route `BrailleFrame` state through `DocumentController`**

Modify `client/gui.py` imports:

```python
from documents.controller import DocumentController
```

In `_initialize_state`, replace these fields:

```python
self.documents: list[Document] = []
self._selected_document_name: str | None = None
self._open_document_name: str | None = None
self._dual_view_results_by_document: dict[str, tuple[object, ...]] = {}
```

with:

```python
self.document_controller = DocumentController()
self.documents = self.document_controller.documents
self._selected_document_name = self.document_controller.selected_document_name
self._open_document_name = self.document_controller.open_document_name
self._dual_view_results_by_document = self.document_controller.dual_view_results_by_document
```

Add this helper near the document state helpers:

```python
def _sync_document_state_from_controller(self) -> None:
    self.documents = self.document_controller.documents
    self._selected_document_name = self.document_controller.selected_document_name
    self._open_document_name = self.document_controller.open_document_name
    self._dual_view_results_by_document = self.document_controller.dual_view_results_by_document
```

Update `_replace_document`:

```python
def _replace_document(self, updated_document: Document) -> None:
    self.document_controller.replace_document(updated_document)
    self._sync_document_state_from_controller()
```

Update `_open_document_by_name` to call the controller first:

```python
def _open_document_by_name(self, name: str | None) -> None:
    result = self.document_controller.open_document(name)
    self._sync_document_state_from_controller()
    if result.document is None:
        self._clear_document_editors()
        self._update_window_title()
        self._refresh_dual_view()
        return
    self._load_document_into_editors(result.document)
    self._reset_input_cursor_to_start()
    self._refresh_document_list(result.document.name)
    self._update_window_title()
    self._refresh_dual_view()
```

Update rename/delete/delete-all paths incrementally so state changes go through `DocumentController`, then call `_sync_document_state_from_controller()`.

- [ ] **Step 6: Run focused GUI document flow tests**

Run:

```bash
python3 -m unittest tests.test_document_controller tests.test_document_session tests.test_document_workspace tests.test_gui_document_flows -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit Phase 1**

```bash
git add client/documents/controller.py client/gui.py client/tests/test_document_controller.py
git commit -m "refactor: extract document workflow controller"
```

## Task 2: Dictionary Entry Domain Extraction

**Files:**
- Create: `client/dictionaries/entries.py`
- Create: `client/tests/test_dictionary_entries.py`
- Modify: `client/dialog.py`
- Modify: `client/tests/test_speech_symbols_dialog.py`
- Modify: `client/tests/test_dictionary_management_dialog.py`

- [ ] **Step 1: Write dictionary entry domain tests**

Create `client/tests/test_dictionary_entries.py`:

```python
import csv
import tempfile
import unittest
from pathlib import Path

from dictionaries.entries import (
    DEFAULT_ENTRY_TYPE,
    DictionaryEntry,
    load_dictionary_entries,
    normalize_entry_type,
    save_dictionary_entries,
    validate_dictionary_entry,
)


class DictionaryEntriesTest(unittest.TestCase):
    def test_normalize_entry_type_falls_back_to_general(self) -> None:
        self.assertEqual(normalize_entry_type("Bopomofo"), "Bopomofo")
        self.assertEqual(normalize_entry_type("Braille"), "Braille")
        self.assertEqual(normalize_entry_type("unknown"), DEFAULT_ENTRY_TYPE)
        self.assertEqual(normalize_entry_type(None), DEFAULT_ENTRY_TYPE)

    def test_validate_dictionary_entry_rejects_empty_source_text(self) -> None:
        self.assertEqual(validate_dictionary_entry(DictionaryEntry("", "⠁")), "source_required")

    def test_validate_dictionary_entry_rejects_invalid_unicode_braille(self) -> None:
        self.assertEqual(validate_dictionary_entry(DictionaryEntry("a", "abc", "Braille")), "invalid_braille")

    def test_validate_dictionary_entry_accepts_unicode_braille(self) -> None:
        self.assertIsNone(validate_dictionary_entry(DictionaryEntry("a", "⠁", "Braille")))

    def test_load_dictionary_entries_filters_empty_and_invalid_bopomofo_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dictionary.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["text", "braille", "type"])
                writer.writerow(["Alpha", "⠁", "General"])
                writer.writerow(["", "⠃", "General"])
                writer.writerow(["Bo", "not-zhuyin", "Bopomofo"])

            self.assertEqual(load_dictionary_entries(path), [DictionaryEntry("Alpha", "⠁", "General")])

    def test_save_dictionary_entries_roundtrip(self) -> None:
        entries = [
            DictionaryEntry("Alpha", "⠁", "General"),
            DictionaryEntry("Beta", "⠃", "Braille"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dictionary.csv"
            save_dictionary_entries(path, entries)

            self.assertEqual(load_dictionary_entries(path), entries)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run dictionary entry tests and verify they fail**

Run from `client/`:

```bash
python3 -m unittest tests.test_dictionary_entries -v
```

Expected: `ERROR` with `ModuleNotFoundError` or missing imports from `dictionaries.entries`.

- [ ] **Step 3: Create `dictionaries.entries`**

Create `client/dictionaries/entries.py` by moving the entry logic from `client/dialog.py`:

```python
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from Bopomofo import normalize_zhuyin_sequence


ENTRY_TYPE_OPTIONS: list[tuple[str, str]] = [
    ("General", "General"),
    ("Bopomofo", "Bopomofo"),
    ("Braille", "Unicode Braille"),
]
ENTRY_TYPE_LABELS = {key: label for key, label in ENTRY_TYPE_OPTIONS}
DEFAULT_ENTRY_TYPE = ENTRY_TYPE_OPTIONS[0][0]
BRAILLE_UNICODE_PATTERNS_START = 0x2800


@dataclass
class DictionaryEntry:
    text: str
    braille: str
    entry_type: str = DEFAULT_ENTRY_TYPE


def normalize_entry_type(entry_type: str | None) -> str:
    if entry_type in ENTRY_TYPE_LABELS:
        return str(entry_type)
    return DEFAULT_ENTRY_TYPE


def is_unicode_braille(value: str) -> bool:
    return all(
        BRAILLE_UNICODE_PATTERNS_START <= ord(char) < BRAILLE_UNICODE_PATTERNS_START + 256
        for char in value
    )


def validate_dictionary_entry(entry: DictionaryEntry) -> str | None:
    if not entry.text.strip():
        return "source_required"
    entry_type = normalize_entry_type(entry.entry_type)
    if entry_type == "Bopomofo":
        try:
            normalize_zhuyin_sequence(entry.braille)
        except Exception:
            return "invalid_bopomofo"
    if entry_type == "Braille" and not is_unicode_braille(entry.braille):
        return "invalid_braille"
    return None


def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
    if not dictionary_path.exists():
        return []

    entries: list[DictionaryEntry] = []
    with dictionary_path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            braille = (row.get("braille") or "").strip()
            entry_type = normalize_entry_type(row.get("type"))
            entry = DictionaryEntry(text=text, braille=braille, entry_type=entry_type)
            if entry_type == "Bopomofo" and validate_dictionary_entry(entry) is not None:
                continue
            entries.append(entry)
    return entries


def save_dictionary_entries(dictionary_path: Path, entries: list[DictionaryEntry]) -> None:
    dictionary_path.parent.mkdir(parents=True, exist_ok=True)
    with dictionary_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["text", "braille", "type"])
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "text": entry.text,
                    "braille": entry.braille,
                    "type": normalize_entry_type(entry.entry_type),
                }
            )
```

- [ ] **Step 4: Update `dialog.py` to import moved entry logic**

In `client/dialog.py`, remove the local `DictionaryEntry`, `normalize_entry_type`, and `load_dictionary_entries` definitions. Add imports:

```python
from dictionaries.entries import (
    DEFAULT_ENTRY_TYPE,
    ENTRY_TYPE_LABELS,
    ENTRY_TYPE_OPTIONS,
    DictionaryEntry,
    is_unicode_braille,
    load_dictionary_entries,
    normalize_entry_type,
    save_dictionary_entries,
    validate_dictionary_entry,
)
```

Update `AddSymbolDialog._on_ok` to use `validate_dictionary_entry`:

```python
entry = DictionaryEntry(identifier, braille, entry_type)
validation_error = validate_dictionary_entry(entry)
if validation_error == "invalid_bopomofo":
    wx.MessageBox(_("Please enter the a valid Bopomofo sequence."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
    try:
        self.braille_ctrl.SetFocus()
    except RuntimeError:
        pass
    return
if validation_error == "invalid_braille":
    wx.MessageBox(_("Please enter the a valid Unicode Braille sequence."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
    try:
        self.braille_ctrl.SetFocus()
    except RuntimeError:
        pass
    return
```

Update `SpeechSymbolsDialog._save_entries`:

```python
def _save_entries(self) -> None:
    save_dictionary_entries(self.dictionary_path, self.entries)
```

- [ ] **Step 5: Update tests to import moved helpers**

In `client/tests/test_speech_symbols_dialog.py`, replace:

```python
DictionaryEntry = dialog.DictionaryEntry
load_dictionary_entries = dialog.load_dictionary_entries
```

with:

```python
from dictionaries.entries import DictionaryEntry, load_dictionary_entries
```

- [ ] **Step 6: Run dictionary tests**

Run:

```bash
python3 -m unittest tests.test_dictionary_entries tests.test_dictionary_management_dialog tests.test_speech_symbols_dialog -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit Phase 2**

```bash
git add client/dictionaries/entries.py client/dialog.py client/tests/test_dictionary_entries.py client/tests/test_speech_symbols_dialog.py client/tests/test_dictionary_management_dialog.py
git commit -m "refactor: extract dictionary entry domain logic"
```

## Task 3: Conversion Job Runner

**Files:**
- Create: `client/conversion/jobs.py`
- Create: `client/tests/test_conversion_jobs.py`
- Modify: `client/gui.py`

- [ ] **Step 1: Write conversion job runner tests**

Create `client/tests/test_conversion_jobs.py`:

```python
import unittest
from pathlib import Path

from adapters.translation.contracts import TranslationRuntime
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from conversion.jobs import ConversionJobRequest, ConversionJobRunner
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError


class ConversionJobRunnerTest(unittest.TestCase):
    def _runtime(self) -> TranslationRuntime:
        return TranslationRuntime(FallbackTextTranslator(), FallbackMathTranslator())

    def _request(self, raw_text, on_complete) -> ConversionJobRequest:
        return ConversionJobRequest(
            conversion_request=ConversionRequest(
                raw_text=raw_text,
                table_file="zh-tw.ctb",
                output_mode="unicode",
                width=40,
                dictionary_path=Path("dictionary/default.csv"),
                data_dir=Path("data"),
                translation_tables={"default": "zh-tw.ctb", "math": "nemeth.ctb"},
            ),
            runtime=self._runtime(),
            on_complete=on_complete,
        )

    def test_start_runs_conversion_and_reports_success(self) -> None:
        completions = []
        runner = ConversionJobRunner(
            converter=lambda request, runtime: ConversionOutput(f"converted:{request.raw_text}", ()),
            scheduler=lambda callback, *args, **kwargs: callback(*args, **kwargs),
            thread_factory=lambda target, args: type(
                "ImmediateThread",
                (),
                {
                    "start": lambda self: target(*args),
                    "is_alive": lambda self: False,
                },
            )(),
        )

        job_id = runner.start(self._request("abc", completions.append))

        self.assertEqual(job_id, 1)
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].job_id, 1)
        self.assertEqual(completions[0].output, ConversionOutput("converted:abc", ()))
        self.assertIsNone(completions[0].error_message)

    def test_start_reports_conversion_stage_errors(self) -> None:
        completions = []

        def failing_converter(_request, _runtime):
            raise ConversionStageError("translation", ValueError("boom"))

        runner = ConversionJobRunner(
            converter=failing_converter,
            scheduler=lambda callback, *args, **kwargs: callback(*args, **kwargs),
            thread_factory=lambda target, args: type(
                "ImmediateThread",
                (),
                {
                    "start": lambda self: target(*args),
                    "is_alive": lambda self: False,
                },
            )(),
        )

        runner.start(self._request("abc", completions.append))

        self.assertEqual(completions[0].stage, "translation")
        self.assertEqual(completions[0].error_message, "boom")

    def test_stale_job_completion_is_ignored(self) -> None:
        pending = []
        completions = []

        def pending_thread_factory(target, args):
            pending.append((target, args))
            return type("PendingThread", (), {"start": lambda self: None, "is_alive": lambda self: True})()

        runner = ConversionJobRunner(
            converter=lambda request, runtime: ConversionOutput(request.raw_text, ()),
            scheduler=lambda callback, *args, **kwargs: callback(*args, **kwargs),
            thread_factory=pending_thread_factory,
        )

        runner.start(self._request("first", completions.append))
        runner.start(self._request("second", completions.append))

        first_target, first_args = pending[0]
        first_target(*first_args)

        self.assertEqual(completions, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run job runner tests and verify they fail**

Run from `client/`:

```bash
python3 -m unittest tests.test_conversion_jobs -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'conversion.jobs'`.

- [ ] **Step 3: Implement `conversion/jobs.py`**

Create `client/conversion/jobs.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import threading

from adapters.translation.contracts import TranslationRuntime
from conversion.service import ConversionOutput, ConversionRequest, ConversionStageError, convert_text_with_alignment, get_public_error_message


@dataclass(frozen=True)
class ConversionJobResult:
    job_id: int
    output: ConversionOutput | None = None
    error_message: str | None = None
    stage: str | None = None


@dataclass(frozen=True)
class ConversionJobRequest:
    conversion_request: ConversionRequest
    runtime: TranslationRuntime
    on_complete: Callable[[ConversionJobResult], None]


Converter = Callable[[ConversionRequest, TranslationRuntime], ConversionOutput]
Scheduler = Callable[..., object]
ThreadFactory = Callable[[Callable[..., None], tuple[object, ...]], object]


def _default_converter(request: ConversionRequest, runtime: TranslationRuntime) -> ConversionOutput:
    return convert_text_with_alignment(request, runtime=runtime)


def _default_scheduler(callback, *args, **kwargs):
    import wx

    return wx.CallAfter(callback, *args, **kwargs)


def _default_thread_factory(target: Callable[..., None], args: tuple[object, ...]):
    return threading.Thread(target=target, args=args, daemon=True)


class ConversionJobRunner:
    def __init__(
        self,
        *,
        converter: Converter = _default_converter,
        scheduler: Scheduler = _default_scheduler,
        thread_factory: ThreadFactory = _default_thread_factory,
    ) -> None:
        self._converter = converter
        self._scheduler = scheduler
        self._thread_factory = thread_factory
        self._job_id = 0
        self._thread = None

    @property
    def current_job_id(self) -> int:
        return self._job_id

    @property
    def thread(self):
        return self._thread

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self, request: ConversionJobRequest) -> int:
        self._job_id += 1
        job_id = self._job_id
        args = (job_id, request)
        self._thread = self._thread_factory(self._run, args)
        self._thread.start()
        return job_id

    def _run(self, job_id: int, request: ConversionJobRequest) -> None:
        try:
            output = self._converter(request.conversion_request, request.runtime)
        except ConversionStageError as error:
            result = ConversionJobResult(
                job_id=job_id,
                error_message=get_public_error_message(error.error),
                stage=error.stage,
            )
        else:
            result = ConversionJobResult(job_id=job_id, output=output)
        self._scheduler(self._deliver, request, result)

    def _deliver(self, request: ConversionJobRequest, result: ConversionJobResult) -> None:
        if result.job_id != self._job_id:
            return
        self._thread = None
        request.on_complete(result)
```

- [ ] **Step 4: Run job runner tests**

Run:

```bash
python3 -m unittest tests.test_conversion_jobs -v
```

Expected: `OK`.

- [ ] **Step 5: Route `BrailleFrame` through `ConversionJobRunner`**

In `client/gui.py`, import:

```python
from conversion.jobs import ConversionJobRequest, ConversionJobResult, ConversionJobRunner
```

In `_initialize_conversion_state`, add:

```python
self._conversion_jobs = ConversionJobRunner()
```

Update `on_convert` guard:

```python
if self._conversion_jobs.is_running():
    return
```

Update `_start_conversion` so it stores UI policy flags as it does today, builds a `ConversionRequest` with `_build_conversion_request(...)`, and starts the job runner:

```python
conversion_request = self._build_conversion_request(raw_text, table_file, output_mode, width, dictionary_path)
job_request = ConversionJobRequest(
    conversion_request=conversion_request,
    runtime=self.translation_runtime,
    on_complete=self._finish_conversion_job,
)
job_id = self._conversion_jobs.start(job_request)
self._convert_job_id = job_id
```

Add adapter method:

```python
def _finish_conversion_job(self, result: ConversionJobResult) -> None:
    error_message = result.error_message
    if error_message is not None:
        message_template = _("ASCII conversion failed: {error}") if result.stage == "ascii" else _("Translation failed: {error}")
        error_message = message_template.format(error=error_message)
    self._finish_conversion(
        result.job_id,
        conversion_output=result.output,
        error_message=error_message,
    )
```

Delete `_run_conversion` after `rg "_run_conversion" client/gui.py` shows only the method definition remains. Remove the stale `threading` import from `client/gui.py` when no other code in that file uses it.

- [ ] **Step 6: Run conversion and GUI flow tests**

Run:

```bash
python3 -m unittest tests.test_conversion_jobs tests.test_conversion_service tests.test_gui_document_flows -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit Phase 3**

```bash
git add client/conversion/jobs.py client/gui.py client/tests/test_conversion_jobs.py
git commit -m "refactor: extract conversion job runner"
```

## Task 4: Conversion Pipeline Internal Split

**Files:**
- Create: `client/conversion/segments.py`
- Create: `client/conversion/plain_text.py`
- Create: `client/conversion/wrapping.py`
- Create: `client/conversion/output.py`
- Modify: `client/conversion/service.py`
- Modify: `client/tests/test_conversion_service.py`
- Create: `client/tests/test_conversion_segments.py`

- [ ] **Step 1: Write segment module tests**

Create `client/tests/test_conversion_segments.py`:

```python
import unittest

from conversion.segments import parse_inline_math_segments, segment_needs_boundary_space


class ConversionSegmentsTest(unittest.TestCase):
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

    def test_segment_needs_boundary_space_when_math_touches_text(self) -> None:
        self.assertTrue(
            segment_needs_boundary_space(
                {"type": "text", "text": "abc"},
                {"type": "math", "text": "1+2"},
            )
        )

    def test_segment_needs_boundary_space_ignores_plain_text_neighbors(self) -> None:
        self.assertFalse(
            segment_needs_boundary_space(
                {"type": "text", "text": "abc"},
                {"type": "text", "text": "def"},
            )
        )
```

- [ ] **Step 2: Run segment tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_conversion_segments -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'conversion.segments'`.

- [ ] **Step 3: Move segment helpers**

Create `client/conversion/segments.py`:

```python
from __future__ import annotations


def append_text_segment(segments: list[dict[str, str]], text: str) -> None:
    if not text:
        return
    if segments and segments[-1]["type"] == "text":
        segments[-1]["text"] += text
    else:
        segments.append({"type": "text", "text": text})


def parse_inline_math_segments(text: str) -> list[dict[str, str]]:
    segments: list[dict[str, str]] = []
    current: list[str] = []
    in_math = False

    for index, char in enumerate(text):
        is_escaped_dollar = char == "$" and index > 0 and text[index - 1] == "\\"
        if char == "$" and not is_escaped_dollar:
            if in_math:
                segments.append({"type": "math", "text": "".join(current)})
                current = []
                in_math = False
            else:
                append_text_segment(segments, "".join(current))
                current = []
                in_math = True
            continue
        current.append(char)

    if in_math:
        append_text_segment(segments, "$" + "".join(current))
    else:
        append_text_segment(segments, "".join(current))

    return segments


def segment_needs_boundary_space(left_segment: dict[str, str], right_segment: dict[str, str]) -> bool:
    if left_segment["type"] != "math" and right_segment["type"] != "math":
        return False
    left_text = left_segment["text"]
    right_text = right_segment["text"]
    return bool(
        left_text
        and right_text
        and not left_text[-1].isspace()
        and not right_text[0].isspace()
    )
```

Update `client/conversion/service.py` imports:

```python
from conversion.segments import parse_inline_math_segments, segment_needs_boundary_space
```

Keep compatibility for tests that still import from `conversion.service`:

```python
_segment_needs_boundary_space = segment_needs_boundary_space
```

- [ ] **Step 4: Extract wrapping helpers**

Create `client/conversion/wrapping.py`:

```python
from __future__ import annotations


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

Update `service.py` to import and call `merge_translation_results` and `wrap_translation_results`. Keep old function names as aliases during the first pass:

```python
from conversion.wrapping import merge_translation_results, wrap_translation_results

_wrap_translation_results = wrap_translation_results
```

- [ ] **Step 5: Extract output formatting helpers**

Create `client/conversion/output.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Callable


MapChar = Callable[..., str]


def get_public_error_message(error: Exception) -> str:
    message = str(error)
    if not message:
        return "An unknown error occurred."
    if "Can't translate: tables" in message and "inbuf" in message:
        return "The selected translation table could not translate this text."
    return message


def format_output_text(
    braille_wrapped: str,
    output_mode: str,
    *,
    data_dir: Path,
    map_char: MapChar,
) -> str:
    if output_mode != "ascii":
        return braille_wrapped
    return map_char(
        braille_wrapped,
        dictionary_path=data_dir / "Braille2Ascii.csv",
        from_field="Braille",
        to_field="Ascii",
    )
```

Update `service.py` to import `get_public_error_message` and `format_output_text`. Keep `get_public_error_message` available from `conversion.service` by importing it into that module.

- [ ] **Step 6: Extract plain text translation flow**

Create `client/conversion/plain_text.py`:

```python
from __future__ import annotations

from pathlib import Path

from adapters.translation.contracts import TranslationRuntime
from config import DEFAULT_MATH_BRAILLE_TABLE
from conversion.segments import parse_inline_math_segments, segment_needs_boundary_space


def translate_plain_text_segment(
    table_file: str,
    text: str,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
    *,
    runtime: TranslationRuntime,
):
    from Bopomofo import normalize_zhuyin_sequence
    from languageDetection import LangChangeCommand, LanguageDetector
    from utils import apply_dictionary, split_bracket_segments

    language = [key for key, value in translation_tables.items() if key not in {"default", "math"} and value != ""]
    language_detector = LanguageDetector(language)
    sequence = list(language_detector.add_detected_language_commands([text]))

    translate_table = translation_tables["default"]
    translations = []
    for item in sequence:
        if isinstance(item, str):
            result = apply_dictionary(
                item,
                dictionary_path=dictionary_path,
                bopomofo_path=bopomofo_path,
                processing=normalize_zhuyin_sequence,
            )
            raw_segments = split_bracket_segments(result["raw"])
            replacement_segments = split_bracket_segments(result["replacement"])

            for raw_segment, replacement_segment in zip(raw_segments, replacement_segments):
                if raw_segment["atomic"] != replacement_segment["atomic"]:
                    raise ValueError("atomic not match")
                translations.append(
                    runtime.text_translator.translate(
                        replacement_segment["text"],
                        table=translate_table,
                        raw=raw_segment["text"],
                        single_token=replacement_segment["atomic"],
                    )
                )
        elif isinstance(item, LangChangeCommand):
            previous_translate_table = translate_table
            lang = item.lang.split("_")[0]
            translate_table = translation_tables.get(lang) or translation_tables["default"]
            if translate_table != previous_translate_table:
                raw = translations[-1].raw if translations else None
                if raw and not raw[-1].isspace():
                    translations.append(
                        runtime.text_translator.translate(
                            " ",
                            table=previous_translate_table,
                            raw=" ",
                        )
                    )

    assert translations, "No translatable text segments were found."
    return translations


def translate_with_language_segments(
    table_file: str,
    text: str,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
    *,
    runtime: TranslationRuntime,
):
    if text == "":
        return []

    translations = []
    segments = parse_inline_math_segments(text)
    math_braille_code = translation_tables.get("math", DEFAULT_MATH_BRAILLE_TABLE)
    for index, segment in enumerate(segments):
        if index > 0 and segment_needs_boundary_space(segments[index - 1], segment):
            translations.append(runtime.text_translator.translate(" ", table=table_file, raw=" "))
        if segment["type"] == "text":
            plain_results = translate_plain_text_segment(
                table_file,
                segment["text"],
                dictionary_path,
                translation_tables,
                bopomofo_path,
                runtime=runtime,
            )
            translations.extend(plain_results if isinstance(plain_results, (list, tuple)) else [plain_results])
        else:
            translations.append(runtime.math_translator.translate(segment["text"], braille_code=math_braille_code))
    return translations
```

Update `service.py` to import `translate_plain_text_segment` and `translate_with_language_segments`. Keep compatibility aliases:

```python
from conversion.plain_text import translate_plain_text_segment as _translate_plain_text_segment
from conversion.plain_text import translate_with_language_segments
```

- [ ] **Step 7: Run conversion tests**

Run:

```bash
python3 -m unittest tests.test_conversion_segments tests.test_conversion_service tests.test_language_detection_translation tests.test_dual_view_model tests.test_translation_runtime_provider -v
```

Expected: all runnable tests pass. If `tests.test_language_detection_translation` skips on non-Windows due to `WINFUNCTYPE`, the skip is acceptable.

- [ ] **Step 8: Commit Phase 4**

```bash
git add client/conversion/segments.py client/conversion/plain_text.py client/conversion/wrapping.py client/conversion/output.py client/conversion/service.py client/tests/test_conversion_segments.py client/tests/test_conversion_service.py
git commit -m "refactor: split conversion pipeline internals"
```

## Final Verification

- [ ] **Step 1: Run focused regression suites**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_document_controller \
  tests.test_document_session \
  tests.test_document_workspace \
  tests.test_dictionary_entries \
  tests.test_dictionary_management_dialog \
  tests.test_speech_symbols_dialog \
  tests.test_conversion_jobs \
  tests.test_conversion_segments \
  tests.test_conversion_service \
  tests.test_gui_document_flows \
  tests.test_translation_runtime_provider \
  tests.test_dual_view_model \
  -v
```

Expected: all listed tests pass, except platform-specific skips already present in the suite.

- [ ] **Step 2: Run syntax and diff checks**

Run from repository root:

```bash
python3 -m py_compile \
  client/documents/controller.py \
  client/dictionaries/entries.py \
  client/conversion/jobs.py \
  client/conversion/segments.py \
  client/conversion/plain_text.py \
  client/conversion/wrapping.py \
  client/conversion/output.py \
  client/conversion/service.py \
  client/gui.py \
  client/dialog.py
git diff --check
```

Expected: `py_compile` exits 0 and `git diff --check` exits 0.

- [ ] **Step 3: Record residual platform risk**

If the work is verified on Linux only, record in the handoff that wxPython and native liblouis/MathCAT behavior still need Windows verification.
