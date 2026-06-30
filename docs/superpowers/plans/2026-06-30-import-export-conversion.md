# Import and Export Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove background/save-time conversion, convert pending documents only during export, simplify import format selection, and keep the active document name in the window title.

**Architecture:** Keep document-state and filter/summary decisions in small pure helpers under `client/documents/` and `client/ui/`, then let `BrailleFrame` orchestrate wx dialogs and the existing conversion worker thread. Single export uses one conversion callback chain; Export All processes documents serially, records per-document failures, and emits exactly one final summary.

**Tech Stack:** Python 3, wxPython, `unittest`, gettext (`dotexpress.po`/`.mo`)

---

## File Structure

- Modify `client/documents/session.py`: format the application title from the active document name.
- Modify `client/documents/workspace.py`: preserve pending braille during normal saves and dispatch mixed imports by extension.
- Create `client/ui/import_dialog.py`: define ordered import filters, wildcard text, and the default filter index without depending on wx.
- Create `client/documents/export_results.py`: accumulate successful and failed batch exports and format pure summary data.
- Modify `client/ui/action_menu.py`: make Import a command instead of a submenu.
- Modify `client/gui.py`: update titles, use the import dialog filters, and orchestrate threaded export conversion.
- Modify `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`: translate new import/export completion strings.
- Regenerate `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`: compile updated translations using the repository script.
- Modify `client/tests/test_document_session.py`: cover exact title formatting.
- Modify `client/tests/test_document_workspace.py`: cover save-without-conversion and mixed import dispatch.
- Modify `client/tests/test_action_menu.py`: cover the single Import command.
- Create `client/tests/test_import_dialog.py`: cover filter order, wildcard, and default selection.
- Create `client/tests/test_export_results.py`: cover all-success and partial-failure summaries.
- Create `client/tests/test_gui_document_flows.py`: test GUI orchestration with a stubbed wx module and mocks where the existing test environment permits.

### Task 1: Active Document Window Title

**Files:**
- Modify: `client/documents/session.py`
- Modify: `client/tests/test_document_session.py`
- Modify: `client/gui.py`

- [ ] **Step 1: Correct and extend the failing title tests**

Replace the currently incorrect title expectation and cover an empty name:

```python
from documents.session import (
    DeleteDocumentDecision,
    format_window_title,
    plan_delete_document,
)

def test_format_window_title_includes_open_document_name(self) -> None:
    self.assertEqual(format_window_title("lesson1"), "lesson1 - DotExpress")
    self.assertEqual(format_window_title(None), "DotExpress")
    self.assertEqual(format_window_title(""), "DotExpress")
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run from `client/`:

```bash
python3 -m unittest tests.test_document_session.DocumentSessionTest.test_format_window_title_includes_open_document_name -v
```

Expected: FAIL because `format_window_title` is absent or returns the old order.

- [ ] **Step 3: Add the pure title helper**

Add to `client/documents/session.py`:

```python
def format_window_title(open_name: str | None) -> str:
    if not open_name:
        return "DotExpress"
    return f"{open_name} - DotExpress"
```

- [ ] **Step 4: Route every active-document transition through one GUI helper**

Import `format_window_title` in `client/gui.py`, then add:

```python
def _update_window_title(self) -> None:
    self.SetTitle(_(format_window_title(self._open_document_name)))
```

Call `_update_window_title()` after `_open_document_name` changes in:

```python
_open_document_by_name
on_rename_document
on_delete_document
on_delete_all_documents
```

Also call it after initial document loading has selected or cleared the open document. Remove the constructor-only `self.SetTitle(_("DotExpress"))` assignment if initialization now goes through `_update_window_title()`.

- [ ] **Step 5: Run title and session tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_document_session -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add client/documents/session.py client/tests/test_document_session.py client/gui.py
git commit -m "feat: show active document in window title"
```

### Task 2: Save Pending Documents Without Conversion

**Files:**
- Modify: `client/documents/workspace.py`
- Modify: `client/tests/test_document_workspace.py`
- Modify: `client/gui.py`

- [ ] **Step 1: Replace auto-conversion save tests with pending-state tests**

Remove the two existing `prepare_document_for_save` auto-conversion tests and add:

```python
def test_prepare_document_for_save_preserves_pending_braille(self) -> None:
    document = Document(name="lesson1", text="old", braille=None)

    prepared = prepare_document_for_save(
        document,
        text="new text",
        braille="editor output must not become committed braille",
    )

    self.assertEqual(prepared, Document(name="lesson1", text="new text", braille=None))

def test_prepare_document_for_save_updates_existing_braille(self) -> None:
    document = Document(name="lesson1", text="old", braille="old braille")

    prepared = prepare_document_for_save(
        document,
        text="new text",
        braille="new braille",
    )

    self.assertEqual(prepared, Document(name="lesson1", text="new text", braille="new braille"))
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_document_workspace.DocumentWorkspaceTest.test_prepare_document_for_save_preserves_pending_braille \
  tests.test_document_workspace.DocumentWorkspaceTest.test_prepare_document_for_save_updates_existing_braille -v
```

Expected: FAIL because the current helper requires `auto_convert` and returns a tuple.

- [ ] **Step 3: Make normal save a state-preserving operation**

Replace `prepare_document_for_save` in `client/documents/workspace.py` with:

```python
def prepare_document_for_save(
    document: Document,
    *,
    text: str,
    braille: str,
) -> Document:
    saved_braille = None if document.braille is None else braille
    return Document(name=document.name, text=text, braille=saved_braille)
```

Do not introduce another synchronous conversion helper. Export conversion belongs to the GUI worker-thread flow in Task 6.

- [ ] **Step 4: Remove conversion and error feedback from normal GUI save**

Change `_save_open_document` to return `None` and save the returned document directly:

```python
def _save_open_document(self) -> None:
    if not self._open_document_name:
        return
    document = self._get_document_by_name(self._open_document_name)
    if document is None:
        return
    updated_document = prepare_document_for_save(
        document,
        text=self.input_txt.GetValue(),
        braille=self.output_txt.GetValue(),
    )
    self._replace_document(updated_document)
    save_document_package(
        document_package_path_for_name(updated_document.name, self.workspace_dir),
        updated_document,
    )
```

Change `_save_open_document_with_feedback` so it only handles `OSError`; delete the “Automatic conversion failed while saving” branch. This ensures import, startup, close, and ordinary saves never invoke conversion.

- [ ] **Step 5: Run workspace tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_document_workspace -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add client/documents/workspace.py client/tests/test_document_workspace.py client/gui.py
git commit -m "refactor: preserve pending braille during save"
```

### Task 3: Single Import Command and Ordered File Filters

**Files:**
- Create: `client/ui/import_dialog.py`
- Create: `client/tests/test_import_dialog.py`
- Modify: `client/ui/action_menu.py`
- Modify: `client/tests/test_action_menu.py`

- [ ] **Step 1: Add failing pure tests for import dialog configuration**

Create `client/tests/test_import_dialog.py`:

```python
import unittest

from ui.import_dialog import (
    ALL_SUPPORTED_FILTER_INDEX,
    build_import_wildcard,
    get_import_filters,
)


class ImportDialogTest(unittest.TestCase):
    def test_filters_have_required_order_and_default(self) -> None:
        filters = get_import_filters()

        self.assertEqual(
            [(item.key, item.label, item.pattern) for item in filters],
            [
                ("dep", "DEP", "*.dep"),
                ("docx", "DOCX", "*.docx"),
                ("epub", "EPUB", "*.epub"),
                ("pdf", "PDF", "*.pdf"),
                ("txt", "TXT", "*.txt"),
                ("all", "All Supported Files", "*.dep;*.docx;*.epub;*.pdf;*.txt"),
            ],
        )
        self.assertEqual(ALL_SUPPORTED_FILTER_INDEX, 5)

    def test_wildcard_contains_each_label_and_pattern(self) -> None:
        self.assertEqual(
            build_import_wildcard(),
            "DEP (*.dep)|*.dep|DOCX (*.docx)|*.docx|EPUB (*.epub)|*.epub|"
            "PDF (*.pdf)|*.pdf|TXT (*.txt)|*.txt|"
            "All Supported Files (*.dep;*.docx;*.epub;*.pdf;*.txt)|"
            "*.dep;*.docx;*.epub;*.pdf;*.txt",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run import-dialog and action-menu tests and verify failure**

Run from `client/`:

```bash
python3 -m unittest tests.test_import_dialog tests.test_action_menu -v
```

Expected: `test_import_dialog` fails because the module does not exist; action-menu fails until Import becomes a command.

- [ ] **Step 3: Implement the import filter model**

Create `client/ui/import_dialog.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ImportFilter:
    key: str
    label: str
    pattern: str


IMPORT_FILTERS = (
    ImportFilter("dep", "DEP", "*.dep"),
    ImportFilter("docx", "DOCX", "*.docx"),
    ImportFilter("epub", "EPUB", "*.epub"),
    ImportFilter("pdf", "PDF", "*.pdf"),
    ImportFilter("txt", "TXT", "*.txt"),
    ImportFilter("all", "All Supported Files", "*.dep;*.docx;*.epub;*.pdf;*.txt"),
)
ALL_SUPPORTED_FILTER_INDEX = len(IMPORT_FILTERS) - 1


def get_import_filters() -> tuple[ImportFilter, ...]:
    return IMPORT_FILTERS


def build_import_wildcard(translate=lambda value: value) -> str:
    parts: list[str] = []
    for item in IMPORT_FILTERS:
        parts.extend((f"{translate(item.label)} ({item.pattern})", item.pattern))
    return "|".join(parts)
```

- [ ] **Step 4: Make Import a command**

In `client/ui/action_menu.py`, replace the Import descriptor with:

```python
DocumentMenuItem("command", "Import", "import"),
```

Remove `get_document_import_format_labels` if no production code references it. Keep the already-updated assertion in `client/tests/test_action_menu.py` expecting `("command", "Import")`.

- [ ] **Step 5: Run the focused tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_import_dialog tests.test_action_menu -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add client/ui/import_dialog.py client/ui/action_menu.py client/tests/test_import_dialog.py client/tests/test_action_menu.py
git commit -m "feat: define unified import file filters"
```

### Task 4: Mixed-Format Import Dispatch

**Files:**
- Modify: `client/documents/workspace.py`
- Modify: `client/tests/test_document_workspace.py`
- Modify: `client/gui.py`

- [ ] **Step 1: Keep the mixed-format test and remove the out-of-scope unsupported-file test**

Keep `test_batch_import_documents_all_detects_each_supported_extension`, including its assertion that every loader receives its matching path. Remove `test_batch_import_documents_all_reports_unsupported_extensions`; the dialog wildcard only permits the five supported extensions, so this is not a user-reachable requirement.

- [ ] **Step 2: Run the mixed import test and verify it fails**

Run from `client/`:

```bash
python3 -m unittest tests.test_document_workspace.DocumentWorkspaceTest.test_batch_import_documents_all_detects_each_supported_extension -v
```

Expected: FAIL with `Unsupported import format: "all"`.

- [ ] **Step 3: Dispatch the `all` mode by each path suffix**

Refactor the loader selection inside `batch_import_documents`:

```python
normalized_format = format_key.casefold()
if normalized_format != "all" and normalized_format not in IMPORT_LOADERS:
    raise ValueError(f'Unsupported import format: "{format_key}".')

for path in sorted((Path(path) for path in paths), key=lambda item: (item.stem.casefold(), item.stem)):
    loader_key = path.suffix.lstrip(".").casefold() if normalized_format == "all" else normalized_format
    loader = IMPORT_LOADERS.get(loader_key)
    if loader is None:
        raise ValueError(f'Unsupported import file type: "{path.suffix}".')
    try:
        document = loader(path)
    except Exception as exc:
        issues.append(BatchIssue(path=path, reason=str(exc)))
        continue
```

The unsupported suffix branch is defensive only. Do not add it to the picker or advertise it as selectable.

- [ ] **Step 4: Wire the command to one wx file dialog**

In `client/gui.py`:

```python
from ui.import_dialog import ALL_SUPPORTED_FILTER_INDEX, build_import_wildcard, get_import_filters
```

Bind the command item directly:

```python
menu.Bind(wx.EVT_MENU, self.on_import_document, menu_items["Import"])
```

Replace `on_import_document(self, format_key)` with:

```python
def on_import_document(self, _evt) -> None:
    if not self._save_open_document_with_feedback():
        return
    with wx.FileDialog(
        self,
        _("Import Document"),
        wildcard=build_import_wildcard(_),
        style=wx.FD_OPEN | wx.FD_MULTIPLE,
    ) as file_dialog:
        file_dialog.SetFilterIndex(ALL_SUPPORTED_FILTER_INDEX)
        if file_dialog.ShowModal() != wx.ID_OK:
            return
        format_key = get_import_filters()[file_dialog.GetFilterIndex()].key
        source_paths = [Path(path) for path in file_dialog.GetPaths()]
    documents, issues = batch_import_documents(
        source_paths,
        format_key=format_key,
        existing_names=set(self._get_document_names()),
    )
    # Preserve the existing persist, list refresh, open-single-document,
    # and Import Issues dialog code unchanged.
```

Update keyboard shortcut callers that currently pass `"txt"` so they call `on_import_document(None)` and open the same unified dialog.

- [ ] **Step 5: Run import-related tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_action_menu tests.test_import_dialog tests.test_document_workspace -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add client/documents/workspace.py client/tests/test_document_workspace.py client/gui.py
git commit -m "feat: import mixed supported document formats"
```

### Task 5: Export Result Accumulation and Summary Text

**Files:**
- Create: `client/documents/export_results.py`
- Create: `client/tests/test_export_results.py`

- [ ] **Step 1: Add failing result-model tests**

Create `client/tests/test_export_results.py`:

```python
import unittest

from documents.export_results import (
    EXPORT_ALL_PARTIAL_MESSAGE,
    EXPORT_ALL_SUCCESS_MESSAGE,
    EXPORT_COMPLETE_TITLE,
    EXPORT_COMPLETE_WITH_ERRORS_TITLE,
    ExportBatchResult,
)


class ExportBatchResultTest(unittest.TestCase):
    def test_all_success_summary(self) -> None:
        result = ExportBatchResult()
        result.add_success("alpha")
        result.add_success("beta")

        self.assertTrue(result.all_succeeded)
        self.assertEqual(result.summary_title, EXPORT_COMPLETE_TITLE)
        self.assertEqual(result.summary_template, EXPORT_ALL_SUCCESS_MESSAGE)
        self.assertEqual(result.summary_values, {})

    def test_partial_failure_summary_lists_names_and_reasons(self) -> None:
        result = ExportBatchResult()
        result.add_success("alpha")
        result.add_failure("beta", "Translation failed")
        result.add_failure("gamma", "Permission denied")

        self.assertFalse(result.all_succeeded)
        self.assertEqual(result.summary_title, EXPORT_COMPLETE_WITH_ERRORS_TITLE)
        self.assertEqual(result.summary_template, EXPORT_ALL_PARTIAL_MESSAGE)
        self.assertEqual(
            result.summary_values,
            {
                "success_count": 1,
                "failure_count": 2,
                "failures": "beta: Translation failed\ngamma: Permission denied",
            },
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run from `client/`:

```bash
python3 -m unittest tests.test_export_results -v
```

Expected: FAIL because `documents.export_results` does not exist.

- [ ] **Step 3: Implement the result model**

Create `client/documents/export_results.py`:

```python
from dataclasses import dataclass, field


EXPORT_COMPLETE_TITLE = "Export Complete"
EXPORT_COMPLETE_WITH_ERRORS_TITLE = "Export Complete with Errors"
EXPORT_ALL_SUCCESS_MESSAGE = "All documents were exported successfully."
EXPORT_ALL_PARTIAL_MESSAGE = (
    "Exported documents: {success_count}\n"
    "Failed documents: {failure_count}\n\n"
    "{failures}"
)


@dataclass(frozen=True)
class ExportFailure:
    document_name: str
    reason: str


@dataclass
class ExportBatchResult:
    successful_names: list[str] = field(default_factory=list)
    failures: list[ExportFailure] = field(default_factory=list)

    def add_success(self, document_name: str) -> None:
        self.successful_names.append(document_name)

    def add_failure(self, document_name: str, reason: str) -> None:
        self.failures.append(ExportFailure(document_name, reason))

    @property
    def all_succeeded(self) -> bool:
        return not self.failures

    @property
    def summary_title(self) -> str:
        return EXPORT_COMPLETE_TITLE if self.all_succeeded else EXPORT_COMPLETE_WITH_ERRORS_TITLE

    @property
    def summary_template(self) -> str:
        return EXPORT_ALL_SUCCESS_MESSAGE if self.all_succeeded else EXPORT_ALL_PARTIAL_MESSAGE

    @property
    def summary_values(self) -> dict[str, int | str]:
        if self.all_succeeded:
            return {}
        return {
            "success_count": len(self.successful_names),
            "failure_count": len(self.failures),
            "failures": "\n".join(
                f"{item.document_name}: {item.reason}" for item in self.failures
            ),
        }
```

- [ ] **Step 4: Run result tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_export_results -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add client/documents/export_results.py client/tests/test_export_results.py
git commit -m "feat: summarize batch export results"
```

### Task 6: Reusable Threaded Conversion for Manual and Single Export

**Files:**
- Modify: `client/gui.py`
- Create: `client/tests/test_gui_document_flows.py`

- [ ] **Step 1: Add focused GUI-flow tests around conversion completion**

Create a wx-stubbed test following the repository’s existing GUI import test pattern. Test these callback contracts:

```python
def test_manual_conversion_updates_output_focus_and_shows_completion(self) -> None:
    # Call _finish_conversion with the manual-convert options.
    # Assert output_txt.SetValue, output_txt.SetFocus, and one
    # "Conversion completed." MessageBox call.

def test_export_conversion_calls_success_callback_without_manual_message(self) -> None:
    # Call _finish_conversion with update_output=False, show_success=False,
    # and an on_success mock.
    # Assert callback("braille") and no MessageBox call.

def test_export_conversion_calls_error_callback_without_showing_worker_error(self) -> None:
    # Call _finish_conversion with an on_error mock.
    # Assert callback(error_message) and no MessageBox call.
```

Use `BrailleFrame.__new__(BrailleFrame)` and mocks for `_convert_dialog_timer`, `_convert_thread`, `_set_conversion_busy`, `_close_converting_dialog`, `output_txt`, and wx APIs, so no real frame or event loop is created.

- [ ] **Step 2: Run the GUI-flow tests and verify they fail**

Run from `client/`:

```bash
python3 -m unittest tests.test_gui_document_flows -v
```

Expected: FAIL because conversion completion has no callback/options contract.

- [ ] **Step 3: Store conversion completion behavior per job**

Initialize these fields in `BrailleFrame.__init__`:

```python
self._convert_on_success = None
self._convert_on_error = None
self._convert_update_output = True
self._convert_show_success = True
```

Extend `_start_conversion`:

```python
def _start_conversion(
    self,
    table_file: str,
    raw_text: str,
    width: int,
    output_mode: str,
    dictionary_path: Path,
    *,
    on_success=None,
    on_error=None,
    update_output: bool = True,
    show_success: bool = True,
) -> None:
    self._convert_on_success = on_success
    self._convert_on_error = on_error
    self._convert_update_output = update_output
    self._convert_show_success = show_success
    # Preserve job id, busy-state, delayed converting dialog, and worker creation.
```

Keep `on_convert` using defaults, preserving manual conversion behavior.

- [ ] **Step 4: Make `_finish_conversion` honor the job behavior**

After clearing timer/dialog/thread and busy state, capture and clear the callback fields. Use this completion logic:

```python
if error_message is not None:
    if on_error is not None:
        on_error(error_message)
    else:
        wx.MessageBox(error_message, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
    return

converted_braille = display_text or ""
if update_output:
    self.output_txt.SetValue(converted_braille)
    self.output_txt.SetFocus()
if on_success is not None:
    on_success(converted_braille)
if show_success:
    wx.MessageBox(_("Conversion completed."), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
```

- [ ] **Step 5: Convert pending documents before a single export**

Split destination selection from writing:

```python
def _write_export_document(self, destination_path: Path, document: Document, format_key: str) -> None:
    if format_key == "dep":
        save_document_package(destination_path, document, include_pending_metadata=False)
    else:
        export_document_brl(destination_path, document)
```

After the user selects a destination, use:

```python
def _continue_single_export(self, document: Document, destination_path: Path, format_key: str) -> None:
    try:
        self._write_export_document(destination_path, document, format_key)
    except OSError as exc:
        self._show_file_error(_("Failed to export document: {error}"), exc)
        return
    wx.MessageBox(
        _("The document was exported successfully."),
        _("Export Complete"),
        wx.OK | wx.ICON_INFORMATION,
        parent=self,
    )
```

For pending braille, start conversion with:

```python
self._start_conversion(
    table_file,
    document.text,
    settings.width,
    settings.output_mode,
    self._get_selected_dictionary_path(),
    update_output=False,
    show_success=False,
    on_success=lambda braille: self._continue_single_export(
        Document(document.name, document.text, braille),
        destination_path,
        format_key,
    ),
    on_error=lambda message: wx.MessageBox(
        message,
        _("Error"),
        wx.OK | wx.ICON_ERROR,
        parent=self,
    ),
)
```

If `document.braille is not None`, call `_continue_single_export` directly. Ensure a missing translation table shows the existing informational message and does not create an output file.

- [ ] **Step 6: Run focused and regression tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_gui_document_flows tests.test_conversion_service tests.test_document_workspace -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py
git commit -m "feat: convert pending documents during export"
```

### Task 7: Serial Export All with One Final Dialog

**Files:**
- Modify: `client/gui.py`
- Modify: `client/tests/test_gui_document_flows.py`

- [ ] **Step 1: Add failing batch orchestration tests**

Add tests using a frame created with `BrailleFrame.__new__` and mocked write/conversion methods:

```python
def test_export_all_continues_after_conversion_failure(self) -> None:
    # Arrange three documents: ready, pending conversion failure, ready.
    # Drive callbacks synchronously.
    # Assert first and third are written, second is not, and processing finishes.

def test_export_all_shows_one_success_dialog(self) -> None:
    # Arrange all successful documents.
    # Assert exactly one MessageBox after the complete batch and no
    # "Conversion completed." calls.

def test_export_all_shows_one_partial_failure_dialog_with_names(self) -> None:
    # Fail one conversion and one write.
    # Assert exactly one final dialog containing both names and reasons.
```

- [ ] **Step 2: Run the batch tests and verify they fail**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_gui_document_flows.GuiDocumentFlowsTest.test_export_all_continues_after_conversion_failure \
  tests.test_gui_document_flows.GuiDocumentFlowsTest.test_export_all_shows_one_success_dialog \
  tests.test_gui_document_flows.GuiDocumentFlowsTest.test_export_all_shows_one_partial_failure_dialog_with_names -v
```

Expected: FAIL because current Export All converts synchronously and may export empty braille.

- [ ] **Step 3: Add serial batch state and one-document processing**

Import `ExportBatchResult`. Add a serial method:

```python
def _export_next_document(
    self,
    remaining: list[Document],
    destination_dir: Path,
    format_key: str,
    result: ExportBatchResult,
) -> None:
    if not remaining:
        self._show_export_all_result(result)
        return

    document = remaining[0]
    rest = remaining[1:]
    destination_path = destination_dir / f"{document.name}.{format_key}"

    def continue_batch() -> None:
        wx.CallAfter(self._export_next_document, rest, destination_dir, format_key, result)

    def write_document(export_document: Document) -> None:
        try:
            self._write_export_document(destination_path, export_document, format_key)
        except OSError as exc:
            result.add_failure(document.name, str(exc))
        else:
            result.add_success(document.name)
        continue_batch()

    if document.braille is not None:
        write_document(document)
        return

    def conversion_failed(message: str) -> None:
        result.add_failure(document.name, message)
        continue_batch()

    self._start_export_conversion(
        document,
        on_success=lambda braille: write_document(
            Document(document.name, document.text, braille)
        ),
        on_error=conversion_failed,
    )
```

Implement `_start_export_conversion` as the shared table/settings wrapper around `_start_conversion`, always passing `update_output=False` and `show_success=False`.

- [ ] **Step 4: Replace the synchronous Export All loop**

Keep directory selection and overwrite confirmation. Then start:

```python
self._export_next_document(
    list(self.documents),
    destination_dir,
    format_key,
    ExportBatchResult(),
)
```

Delete `_prepare_document_for_export`, the synchronous conversion loop, and the old “exported with empty braille output” issue dialog.

- [ ] **Step 5: Show exactly one final summary**

Add:

```python
def _show_export_all_result(self, result: ExportBatchResult) -> None:
    style = wx.OK | (wx.ICON_INFORMATION if result.all_succeeded else wx.ICON_WARNING)
    message = _(result.summary_template).format(**result.summary_values)
    wx.MessageBox(
        message,
        _(result.summary_title),
        style,
        parent=self,
    )
```

Do not show per-document export completion or `Conversion completed.` dialogs from this path.

- [ ] **Step 6: Run GUI flow tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_gui_document_flows tests.test_export_results -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py
git commit -m "feat: summarize serial export all results"
```

### Task 8: Localization and Full Verification

**Files:**
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`
- Verify: all touched production and test files

- [ ] **Step 1: Add Traditional Chinese translations**

Update `dotexpress.po` for every new user-visible string, including:

```po
msgid "All Supported Files"
msgstr "所有支援的檔案"

msgid "Export Complete"
msgstr "匯出完成"

msgid "Export Complete with Errors"
msgstr "匯出完成，但有錯誤"

msgid "The document was exported successfully."
msgstr "文件已成功匯出。"

msgid "All documents were exported successfully."
msgstr "所有文件皆已成功匯出。"

msgid ""
"Exported documents: {success_count}\n"
"Failed documents: {failure_count}\n"
"\n"
"{failures}"
msgstr ""
"成功匯出的文件：{success_count}\n"
"匯出失敗的文件：{failure_count}\n"
"\n"
"{failures}"
```

Import the four message constants from `documents.export_results` into `client/gui.py` and pass the constants directly to `_()` before formatting. This gives gettext stable source strings while keeping counts and failure details dynamic.

- [ ] **Step 2: Regenerate and compile translations**

On Windows, run:

```bat
scripts\generate_pot.bat
```

Then compile `dotexpress.po` using the same gettext command used by that script. If the current Linux environment lacks `msgfmt`, report that limitation and leave the reviewed `.po` change without fabricating a `.mo`.

Expected: gettext reports no malformed entries and the `.mo` timestamp/content changes.

- [ ] **Step 3: Run all focused client tests**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_action_menu \
  tests.test_document_session \
  tests.test_document_workspace \
  tests.test_import_dialog \
  tests.test_export_results \
  tests.test_gui_document_flows \
  tests.test_conversion_service -v
```

Expected: all tests PASS.

- [ ] **Step 4: Run the complete client unit test suite**

Run from `client/`:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all runnable tests PASS; record any existing platform-specific skips.

- [ ] **Step 5: Perform Windows wxPython smoke checks**

Verify manually:

1. Import is a single command in both File and document context menus.
2. The dialog order is DEP, DOCX, EPUB, PDF, TXT, All Supported Files, with All Supported selected by default.
3. Mixed supported files import together without starting conversion.
4. Saving and closing a pending document do not start conversion.
5. Manual Convert still shows delayed `converting` and then `Conversion completed.`.
6. Single export of a pending document shows delayed `converting`, no conversion-complete dialog, then one export-complete dialog.
7. Export All shows no per-document success dialogs and one final all-success summary.
8. Export All skips failed documents, exports the rest, and lists each failed filename and reason once.
9. Opening, switching, renaming, deleting, and clearing documents updates `<文件名> - DotExpress` correctly.

- [ ] **Step 6: Commit localization and final adjustments**

```bash
git add client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "feat: localize import and export status messages"
```

Only include `.mo` if it was regenerated successfully.
