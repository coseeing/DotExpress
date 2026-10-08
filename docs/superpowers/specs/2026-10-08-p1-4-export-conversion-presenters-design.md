# Export Coordinator and Conversion Presenter (P1-4) Design

## Goal

Move the conversion state machine and the export chains out of `BrailleFrame` into two wx-free modules. This is roadmap task P1-4 in `storage/refactor.md` (section 6.2). It covers S-1 items 2 (`ExportCoordinator`) and 4 (`ConversionPresenter`) in section 3.1, and I-3 (section 3.4, `ConversionCompletionPolicy`). It also does two cleanups that the P0 phase review assigned to this task: M-9 (the unused `parent` parameter of `_show_file_error`) and the unused `ConversionStageError` import left in `gui` (M-3, P1-3 Out of Scope).

Concretely:

- **`conversion/presenter.py` (new, no wx).** `ConversionPresenter` owns the `ConversionJobRunner`, the "converting" dialog timer, the busy state transitions, the error messages, the completion of manual and export conversions, and the dual-view cache write after a manual conversion (through `DocumentController`). It talks to the frame through a small `ConversionView` protocol. Threading (`call_after`, `call_later`, `thread_factory`, `converter`) is injected.
- **`documents/export_coordinator.py` (new, no wx).** `ExportCoordinator` owns single export (choose a path, fix the extension, convert first if the document is pending, write, report) and the Export All chain (choose a folder, check conflicts, then one document per UI turn through `call_after`, then one summary). It talks to the frame through an `ExportView` protocol and starts conversions through the presenter.
- **I-3: the presenter owns the completion state.** `ConversionCompletionPolicy` and `ConversionJobRequest` are deleted from `conversion/jobs.py`. The runner takes a plain `ConversionRequest` and delivers `ConversionJobSuccess(job_id, conversion_output)` or `ConversionJobFailure(job_id, error)`. Nothing UI-related goes into the worker thread any more. The presenter keeps the active job's completion keyed by job id.
- **`BrailleFrame` keeps only wx code:** the menu handlers' save-first guards, the dialogs, the message boxes, the busy-state widget toggling and the `ConvertingDialog` window. It implements both view protocols with small public methods.

This is a behavior-preserving refactor. Every flow keeps its order of effects **including the asynchronous order** (what happens in the click's UI turn, in the worker, and in each later `CallAfter`/`CallLater` turn), its messages, captions and icons, its busy-state toggling, its cache writes and its re-entrancy behavior (including the known defects listed below). No user-facing string changes; no msgid is added or removed; nothing under `client/locales/` is edited.

## Current State (verified 2026-10-08 on `refactor/p1-4-export-conversion-presenters`, HEAD `d6e4663`, P0-1..P0-6 and P1-1..P1-3 merged)

Baseline: `cd client && python -m unittest discover -s tests -p "test_*.py"` runs 696 tests, `failures=1` (the known P2-5 test), `skipped=9`. `tests.test_conversion_jobs tests.test_gui_document_flows` runs 133 tests, `OK (skipped=2)`. An AST scan of `_()`/`N_()` string literals in `client/` (tests excluded) finds 353 msgids.

Indentation: `gui.py`, `conversion/jobs.py` and `tests/test_conversion_jobs.py` use tabs. `documents/*.py`, `conversion/output.py` and `tests/test_gui_document_flows.py` use 4 spaces. The new modules and new test files use 4 spaces (AGENTS.md); edited files keep their own style.

### `conversion/jobs.py` (119 lines)

- `ConversionCompletionPolicy` 14-19: `on_success`, `on_error` (UI callbacks), `update_output`, `show_success` (UI flags). `ConversionJobRequest` 22-25 wraps a `ConversionRequest` and a policy. `ConversionJobSuccess` 28-32 and `ConversionJobFailure` 35-39 carry the policy back. The worker never reads it (I-3).
- `ConversionJobRunner` 46-119: `start(request)` increments `_job_id`, creates `thread_factory(target=_run_job, args=(job_id, request), daemon=True)`, starts it, returns the id. `_run_job` calls `converter(request.conversion_request, runtime=...)`; on `ConversionStageError` it calls `call_after(_deliver_failure, ...)`, otherwise `call_after(_deliver_success, ...)`. Any other exception escapes the thread and nothing is delivered. `_deliver_*` (UI thread) drops results whose `job_id` is not the latest (stale), otherwise sets `_thread = None` **before** calling `on_success`/`on_failure`, so `is_running()` is `False` inside the completion. `is_running()` is `_thread is not None and _thread.is_alive()`; `active_job_id` is the latest id.
- `convert_text_with_alignment` wraps every `Exception` of preprocessing, translation, wrapping and ASCII mapping in `ConversionStageError` with stage `text_processing`, `translation` or `ascii` (`conversion/output.py` 50-89). An empty source returns `ConversionOutput("", ())` but still runs in the worker.

### Conversion state machine (`gui.py`)

| Piece | Location | Behavior today |
| --- | --- | --- |
| Wiring | `_initialize_conversion_state` 222-230 | `ConversionJobRunner(runtime=self.translation_runtime, on_success=self._finish_conversion_success, on_failure=self._finish_conversion_failure, call_after=wx.CallAfter)` (real `threading.Thread`, real converter); `_convert_dialog = None`; `_convert_dialog_timer = None`. Called from `__init__` after `_create_main_layout`, before `_bind_events`. |
| Request | `_build_conversion_request` 544-554 | `ConversionRequest(raw_text, output_mode, width, dictionary_path, data_dir=resource_path("data"), translation_tables=self.translation_tables.copy(), lang=get_lang(), charset_maps=get_charset_maps())`. Language and charset maps are read per request. |
| Convert command | `on_convert` 1124-1144 (Translation > Convert, and Ctrl+Enter in the source editor via `on_input_text_key_down` 953-957) | If `runner.is_running()`: return silently. If `_missing_default_table_message()` (1034-1037; `translation_tables.get("default")` falsy) is not `None`: `wx.MessageBox(message, _("Info"), wx.OK \| wx.ICON_INFORMATION, parent=self)`, return. Else `_start_conversion(input_txt.GetValue(), settings.width, settings.output_mode, _get_selected_dictionary_path())`. No save-first. |
| Start | `_start_conversion` 1171-1202 | `_set_conversion_busy(True)`; `_close_converting_dialog()`; build the policy; `job_id = runner.start(ConversionJobRequest(_build_conversion_request(...), policy))`; `self._convert_dialog_timer = wx.CallLater(2000, self._show_converting_dialog, job_id)`. A previous timer is overwritten, not stopped. |
| Busy | `_set_conversion_busy` 1161-1169 | For `_("File")` and `_("Translation")`: `menu_bar.FindMenu(label)`, `EnableTop(index, not busy)` if found. Then `document_list.Enable(not busy)`, `input_txt.Enable(not busy)`. The Help menu, the Braille Result editor, the frame's char hook and the Dual View window stay active. |
| Converting dialog | `_show_converting_dialog` 1204-1213, `_close_converting_dialog` 1215-1221, `ConvertingDialog` 120-134 | Timer callback: return if `job_id != runner.active_job_id`, if not `runner.is_running()`, or if a dialog exists; else `ConvertingDialog(self)` (title "Info", text "converting", no close box, stays on top, vetoes close), `Show()`, `Raise()`. Close: if a dialog exists, clear the attribute, `Unbind(wx.EVT_CLOSE)`, `Destroy()`. |
| Completion | `_complete_conversion` 1223-1274 | Stop and clear the timer; close the dialog; `_set_conversion_busy(False)`. **Error:** `policy.on_error(message)` if set, else `wx.MessageBox(message, _("Error"), wx.OK \| wx.ICON_ERROR, parent=self)`; return. **Success:** `braille = output.display_text`. If `update_output`: `output_txt.SetValue(braille)`, `output_txt.SetFocus()`; if a document is open: if it is in the list, replace it with `Document(name, input_txt.GetValue(), braille)`; then `set_dual_view_results(open_name, output.dual_view_segments)` (even if the name is not in the list); then `_refresh_dual_view()` (also when nothing is open). Then `policy.on_success(braille)` if set. Then, if `show_success`, `wx.MessageBox(_("Conversion completed."), _("Info"), wx.OK \| wx.ICON_INFORMATION, parent=self)`. The `display_text=` parameter is used only by tests. |
| Success / failure adapters | `_finish_conversion_success` 1276-1277, `_finish_conversion_failure` 1279-1292 | Failure message: template by stage, `"ascii"`: `_("ASCII conversion failed: {error}")`, `"text_processing"`: `_("Text processing failed: {error}")`, anything else: `_("Translation failed: {error}")`; `{error}` is `_(get_public_error_message(error.error))` (empty message: "An unknown error occurred."; liblouis "Can't translate: tables ... inbuf": "The selected translation table could not translate this text."; else `str(error)`). |
| Close | `_on_close` 1146-1159 | If `runner.is_running()` and `evt.CanVeto()`: `Veto()`, return (no save). Then save-first (veto on failure when possible); `_close_converting_dialog()`; destroy the Dual View window; `Skip()`. The timer is not stopped. |

Only two policy shapes exist: **manual** (`ConversionCompletionPolicy()`: no callbacks, `update_output=True`, `show_success=True`) and **export** (`on_success` and `on_error` both set, `update_output=False`, `show_success=False`).

### Export chains (`gui.py`)

| Flow | Location | Behavior today |
| --- | --- | --- |
| Export menu | `on_export_document` 912-919 | No selected document: return. Save first (abort on failure). Re-read the selected document (fall back to the one read before the save). `_export_document_with_dialog(document, key)`. |
| Ctrl+S in the Braille Result editor | `on_output_text_key_down` 959-968 | If the save succeeds and a document is open: `_export_document_with_dialog(open document, get_format("brl").key)`. Always `output_txt.SetFocus()` afterwards; no `Skip()`. |
| Single export | `_export_document_with_dialog` 575-610 | `descriptor = get_format(key)`; `default_file = name + extension`; `wildcard = build_export_wildcard(descriptor, _)`; `wx.FileDialog(self, _("Export Document"), defaultFile=..., wildcard=..., style=wx.FD_SAVE \| wx.FD_OVERWRITE_PROMPT)`; cancel: return. If `path.suffix.casefold() != extension`: `path.with_suffix(extension)`. If `document.braille is None`: `_start_export_conversion(document, path, key, on_success=lambda braille: _continue_single_export(Document(name, text, braille), path, key), on_error=lambda message: wx.MessageBox(message, _("Error"), wx.OK \| wx.ICON_ERROR, parent=self))`; return. Else `_continue_single_export(document, path, key)`. |
| Export conversion | `_start_export_conversion` 1039-1067 | Missing default table: `on_missing_table(message)` if given, else `on_error(message)`; return `False` (no busy, no thread). Else `_start_conversion(document.text, settings.width, settings.output_mode, dictionary path, on_success, on_error, update_output=False, show_success=False)`; return `True` (unused). `destination_path` and `format_key` are unused. |
| Write and report | `_continue_single_export` 1021-1032, `_write_export_document` 1014-1019 | `get_format(key)`; not exportable or no writer: `ValueError('Unsupported export format: "<key>".')` (not caught). `writer(path, document, ExportContext(dual_view_results=controller.get_dual_view_results(document.name)))`. `OSError`: `_show_file_error(_("Failed to export document: {error}"), exc)`, return. Success: `wx.MessageBox(_("The document was exported successfully."), _("Export Complete"), wx.OK \| wx.ICON_INFORMATION, parent=self)`. |
| Export All menu | `on_export_all_documents` 921-935 | No documents: return. Save first. `wx.DirDialog(self, _("Export All Documents"))`; cancel: return. `suffix = get_format(key).extension`; `documents = controller.documents_snapshot()`; `conflicts` = target paths that `exists()`; if any and `_confirm_overwrite_all(conflicts)` (565-573: `wx.MessageBox(<overwrite message>, _("Confirm Overwrite"), wx.YES_NO \| wx.ICON_WARNING, parent=self) == wx.YES`) is false: return. `_export_next_document(documents, folder, key, ExportBatchResult())`. |
| Chain step | `_export_next_document` 1069-1112 | Empty: `_show_export_all_result(result)`, return. Else `get_format(key)` (once per step), first document, target `folder / (name + extension)`. `continue_batch()` = `wx.CallAfter(_export_next_document, rest, folder, key, result)`. `write_document(doc)`: `_write_export_document`; `OSError`: `add_failure(name, str(exc))`, else `add_success(name)`; then `continue_batch()`. Braille present: `write_document(document)`, return. Else `conversion_failed(message)` = `add_failure(name, message)` + `continue_batch()`, and `_start_export_conversion(..., on_success=lambda braille: write_document(Document(name, text, braille)), on_error=conversion_failed, on_missing_table=conversion_failed)`. |
| Summary | `_show_export_all_result` 1114-1122 | `wx.MessageBox(_(result.summary_template).format(**result.summary_values), _(result.summary_title), wx.OK \| (wx.ICON_INFORMATION if all succeeded else wx.ICON_WARNING), parent=self)`. |

### Asynchronous order today

- **Manual conversion.** Click turn: checks, busy on, dialog closed, request built, thread started, 2 s timer armed. Worker: convert, `CallAfter`. Timer turn (only if still running after 2 s): dialog shown once. Delivery turn: timer stopped, dialog closed, busy off, output set and focused, document and cache updated, Dual View refreshed, "Conversion completed." box.
- **Single export, pending document.** Menu turn: save, file dialog, busy on, conversion started. Delivery turn: timer stopped, dialog closed, busy off, file written, "Export Complete" box (or error box). The Braille Result editor, the cache and the Dual View are not touched.
- **Export All.** Menu turn: save, folder dialog, conflict check, then the **first** step runs synchronously in the same turn. Every later step runs in its own `CallAfter` turn. A document with braille is written in the step's turn. A pending document starts a conversion in the step's turn and is written in the delivery turn, which then queues the next step. Busy is on only while a conversion runs, so the UI is enabled between steps. The summary box appears once, in the turn of the empty step.

### Re-entrancy today

| Entry point while a conversion runs | Reachable? | Effect |
| --- | --- | --- |
| Convert (menu, Ctrl+Enter) | No: Translation menu and source editor disabled; `on_convert` also checks `is_running()` | — |
| File menu (Export, Export All, Import, ...), document list (F2, Delete, activation, context menu) | No: disabled | — |
| Ctrl+S in the Braille Result editor | **Yes** | Saves, then exports the open document. With braille: written synchronously, "Export Complete" box; the running job continues. Pending: a **second job starts without any `is_running()` check**; busy is set again, the dialog is closed, a new timer is armed (the old one is not stopped and later does nothing). The first job's result is dropped as stale; for a manual job the output is never updated and no message appears (known defect 2). |
| Ctrl+Tab / Ctrl+Shift+Tab (frame char hook) | **Yes** | Saves and opens another document. When the manual job completes, its braille and source-editor text go into the document that is open **then**, and the cache is written under that name (known defect 1). |
| Ctrl+O (frame char hook) | **Yes** | Runs the import flow; importing one file opens it, with the same effect as Ctrl+Tab. |
| Window close | Vetoed while running if `CanVeto()` | Without veto: save, dialog closed, viewer destroyed. |
| Between Export All steps (no job running) | Everything enabled | A Convert started in the gap is superseded by the next pending document's export conversion (dropped as stale, no message). Another Export All can start and interleave. |

### Tests that touch this today

- `tests/test_conversion_jobs.py` (4 tests): success, stage failure, stale success and stale failure, with a `FakeThread` (records target and args; `start()` only marks it alive; the test calls `run()`) and a synchronous `call_after`.
- `tests/test_gui_document_flows.py`, `GuiDocumentFlowsTest`: 22 tests drive frame internals with a `Mock` runner and `Mock` busy/dialog methods: `_write_export_document` (4), `_export_next_document` (5, with `gui.wx.CallAfter` patched to run synchronously), `_start_conversion` (1), `_complete_conversion` / `_finish_conversion_*` (7), `on_convert` (2), `_start_export_conversion` (1), `_missing_default_table_message` (1), `_export_document_with_dialog` with a missing table (1). `DocumentMenuAndExportCharacterizationTest` (P1-2) has 5 export tests: dialog title/wildcard (patches `gui._`), extension correction, real writer bytes, Export All HTML cache, Ctrl+S. `DocumentWorkspaceFlowsCharacterizationTest._make_workspace_frame` sets `_conversion_runner` and `_close_converting_dialog` mocks for `_on_close`.
- **Not covered today:** the real runner wired to the frame; the converting dialog and its timer; busy-state widget calls; the async order of the Export All chain (all tests run `CallAfter` synchronously, so a step's turn boundary is invisible); Export All conflict confirmation and folder cancel; the re-entrancy rows above; error-message mapping for `ascii` and unknown stages and for the public error text.
- wx stub masking (`tests/wx_stub.py`): on a stub frame every missing instance attribute is a no-op function, so tests must set the presenter and the coordinator explicitly.

## Design

The two view protocols are `typing.Protocol` annotations only. The frame implements them with plain methods and the tests use small recording fakes, as `dictionaries/presenter.py` does with `DictionaryManagementView`. There is no view base class and no MVP framework (refactor.md section 7, item 4).

### `conversion/jobs.py` (I-3)

- Delete `ConversionCompletionPolicy` and `ConversionJobRequest`.
- `ConversionJobSuccess(job_id: int, conversion_output: ConversionOutput)` and `ConversionJobFailure(job_id: int, error: ConversionStageError)` (frozen dataclasses, no policy field).
- `ConversionJobRunner.start(request: ConversionRequest) -> int`; `_run_job(job_id, request)` calls `converter(request, runtime=...)`.
- Everything else is unchanged: job ids, `daemon=True`, stale filtering, `_thread = None` before the callback, `is_running()`, `active_job_id`, the escape of non-`ConversionStageError` exceptions. The runner stays the only thread code (refactor.md section 7, item 2: no generic task framework).

The rename option (`ConversionCompletionContext`) was rejected: it would keep UI callbacks travelling through the worker, which is what I-3 objects to, and the presenter needs the state anyway.

### `ConversionPresenter` (`conversion/presenter.py`, new, no wx import)

```python
CONVERTING_DIALOG_DELAY_MS = 2000

class Timer(Protocol):
    def Stop(self) -> object: ...          # wx.CallLater result

CallAfter = Callable[..., object]          # wx.CallAfter
CallLater = Callable[..., Timer]           # wx.CallLater(ms, fn, *args)

class ConversionView(Protocol):
    def get_source_text(self) -> str: ...
    def set_conversion_busy(self, busy: bool) -> None: ...
    def show_converting_dialog(self) -> None: ...      # idempotent
    def close_converting_dialog(self) -> None: ...     # idempotent
    def show_conversion_output(self, text: str) -> None: ...   # set, then focus
    def refresh_dual_view(self) -> None: ...
    def show_info(self, message: str, caption: str) -> None: ...
    def show_error(self, message: str, caption: str) -> None: ...

def missing_default_table_message(translation_tables: Mapping[str, object]) -> str | None: ...
def format_conversion_error(error: ConversionStageError) -> str: ...

class ConversionPresenter:
    def __init__(
        self,
        view: ConversionView,
        documents: DocumentController,
        *,
        runtime: TranslationRuntime,
        build_request: Callable[[str], ConversionRequest],
        get_translation_tables: Callable[[], Mapping[str, object]],
        call_after: CallAfter,
        call_later: CallLater,
        thread_factory: ThreadFactory = threading.Thread,
        converter: Callable[..., ConversionOutput] = convert_text_with_alignment,
    ) -> None: ...
    def is_running(self) -> bool: ...
    def missing_table_message(self) -> str | None: ...
    def convert(self) -> None: ...
    def convert_for_export(self, raw_text: str, *, on_success: Callable[[str], None], on_error: Callable[[str], None]) -> None: ...
```

The presenter builds its own `ConversionJobRunner(runtime=..., on_success=self._on_job_success, on_failure=self._on_job_failure, call_after=call_after, converter=converter, thread_factory=thread_factory)`. It builds every user-facing string with `_` from `i18n` at call time, as `dictionaries/presenter.py` does.

Behavior, step by step (the same order as today):

- `missing_default_table_message(tables)`: `None` if `tables.get("default")` is truthy, else `_("Please select a translation table first.")`. `missing_table_message()` applies it to `get_translation_tables()` (read at call time, because `apply_settings_from_dialog` replaces the dict).
- `format_conversion_error(error)`: the stage template table and `_(get_public_error_message(error.error))` exactly as `_finish_conversion_failure` today.
- `convert()`: if `is_running()`: return. If `missing_table_message()` is not `None`: `view.show_info(message, _("Info"))`, return. `raw_text = view.get_source_text()`; `_start(raw_text, export=None)`.
- `convert_for_export(raw_text, on_success, on_error)`: `_start(raw_text, export=_ExportCallbacks(on_success, on_error))`. No running check and no table check (the coordinator checks the table first, as today; the missing running check is known defect 2, preserved).
- `_start(raw_text, export)`: `view.set_conversion_busy(True)`; `view.close_converting_dialog()`; `request = build_request(raw_text)`; `job_id = runner.start(request)`; `self._active = _ActiveJob(job_id, export)`; `self._timer = call_later(CONVERTING_DIALOG_DELAY_MS, self._show_converting_dialog, job_id)` (overwrites a previous timer without stopping it, as today).
- `_show_converting_dialog(job_id)`: return if `job_id != runner.active_job_id` or not `runner.is_running()`; else `view.show_converting_dialog()` (the frame returns if its dialog already exists).
- `_on_job_success(result)` / `_on_job_failure(result)`: take `self._active` if its `job_id` equals `result.job_id` (the runner already drops stale results; a mismatch is ignored defensively) and clear it. Then `_finish`.
- `_finish(job, output | error_message)`: if a timer is set, `Stop()` it and clear it; `view.close_converting_dialog()`; `view.set_conversion_busy(False)`. **Error:** export: `job.export.on_error(message)`; manual: `view.show_error(message, _("Error"))`; return. **Success:** `braille = output.display_text`. Manual: `view.show_conversion_output(braille)`; `open_name = documents.open_document_name`; if `open_name`: `document = documents.get_document(open_name)`; if not `None`, `documents.replace_document(Document(document.name, view.get_source_text(), braille))`; `documents.set_dual_view_results(open_name, output.dual_view_segments)`; then `view.refresh_dual_view()`; then `view.show_info(_("Conversion completed."), _("Info"))`. Export: `job.export.on_success(braille)` only.

The two-shape completion (`_ActiveJob(job_id, export: _ExportCallbacks | None)`, `None` meaning manual) replaces the four-field policy. It is exactly equivalent because only the two shapes listed above exist. `_ActiveJob` and `_ExportCallbacks` are private frozen dataclasses.

Contract for `call_after`: it must defer (as `wx.CallAfter` does), so `self._active` is stored before any delivery. Test thread factories must not run the target inside `start()` (the existing `FakeThread` does not).

### `ExportCoordinator` (`documents/export_coordinator.py`, new, no wx import)

```python
class ExportView(Protocol):
    def choose_export_path(self, default_file: str, descriptor: DocumentFormatDescriptor) -> Path | None: ...
    def choose_export_directory(self) -> Path | None: ...
    def confirm_overwrite_all(self, conflicts: list[Path]) -> bool: ...
    def show_info(self, message: str, caption: str) -> None: ...
    def show_warning(self, message: str, caption: str) -> None: ...
    def show_error(self, message: str, caption: str) -> None: ...

class ExportConversions(Protocol):            # satisfied by ConversionPresenter
    def missing_table_message(self) -> str | None: ...
    def convert_for_export(self, raw_text: str, *, on_success: Callable[[str], None], on_error: Callable[[str], None]) -> None: ...

class ExportCoordinator:
    def __init__(self, view: ExportView, documents: DocumentController, conversions: ExportConversions, *, call_after: CallAfter) -> None: ...
    def export_document(self, document: Document, format_key: str) -> None: ...
    def export_all(self, format_key: str) -> None: ...
    def write_document(self, destination_path: Path, document: Document, format_key: str) -> None: ...
```

The view owns the text of its own dialogs (file dialog title and wildcard, folder dialog title, overwrite question), so those msgids stay in `gui.py` and the P1-2 wildcard test that patches `gui._` keeps working. The coordinator owns the outcome messages.

- `write_document`: the body of `_write_export_document`, with the cache read through `documents.get_dual_view_results(document.name)`. `ValueError` for a non-exportable format propagates.
- `export_document(document, key)`: `descriptor = get_format(key)`; `path = view.choose_export_path(f"{document.name}{descriptor.extension}", descriptor)`; `None`: return. Fix the suffix as today. If `document.braille is None`: `message = conversions.missing_table_message()`; if not `None`: `view.show_error(message, _("Error"))`, return; else `conversions.convert_for_export(document.text, on_success=lambda braille: self._write_single(Document(document.name, document.text, braille), path, key), on_error=lambda message: view.show_error(message, _("Error")))`, return. Else `_write_single(document, path, key)`.
- `_write_single`: `write_document`; `OSError`: `view.show_error(_("Failed to export document: {error}").format(error=exc), _("Error"))`, return; success: `view.show_info(_("The document was exported successfully."), _("Export Complete"))`.
- `export_all(key)`: `folder = view.choose_export_directory()`; `None`: return. `suffix = get_format(key).extension`; `documents_to_export = documents.documents_snapshot()`; conflicts as today; `if conflicts and not view.confirm_overwrite_all(conflicts)`: return. `_export_next(documents_to_export, folder, key, ExportBatchResult())`.
- `_export_next`: the body of `_export_next_document`, with `call_after(self._export_next, rest, folder, key, result)` for `continue_batch`, `conversions.missing_table_message()` then `conversions.convert_for_export(document.text, on_success=..., on_error=conversion_failed)` for pending documents (missing table: `conversion_failed(message)`), and `_show_batch_result(result)` at the end.
- `_show_batch_result`: `message = _(result.summary_template).format(**result.summary_values)`; `caption = _(result.summary_title)`; `view.show_info` if all succeeded, else `view.show_warning`.

The "save first" guards, the selection lookups and `has_documents` stay in the frame's menu handlers (they belong to the document workflow of P1-3), so the coordinator is entered at exactly the point where `_export_document_with_dialog` and the Export All folder dialog are entered today.

### `BrailleFrame` (`gui.py`)

- `_initialize_conversion_state()`: `self._convert_dialog = None`; `self._conversion_presenter = ConversionPresenter(self, self._document_controller, runtime=self.translation_runtime, build_request=self._build_conversion_request_for_text, get_translation_tables=lambda: self.translation_tables, call_after=wx.CallAfter, call_later=wx.CallLater)`; `self._export_coordinator = ExportCoordinator(self, self._document_controller, self._conversion_presenter, call_after=wx.CallAfter)`. Same place in `__init__`.
- New `_build_conversion_request_for_text(raw_text)`: `settings = self.translation_settings`; `return self._build_conversion_request(raw_text, settings.output_mode, settings.width, self._get_selected_dictionary_path())`. `_build_conversion_request` is unchanged (its tests stay).
- `on_convert(_evt)`: `self._conversion_presenter.convert()`.
- `on_export_document`, `on_export_all_documents`, `on_output_text_key_down`: unchanged guards and save-first; the call at the end becomes `self._export_coordinator.export_document(document, key)` / `self._export_coordinator.export_all(key)`.
- `_on_close`: `self._conversion_presenter.is_running()` and `self.close_converting_dialog()`; otherwise unchanged.
- View methods (public, small, wx only): `get_source_text` (`input_txt.GetValue()`), `set_conversion_busy` (body of `_set_conversion_busy`, including the `FindMenu` lookup by translated title), `show_converting_dialog` (body of `_show_converting_dialog` after the job checks), `close_converting_dialog` (body of `_close_converting_dialog`), `show_conversion_output` (`SetValue`, then `SetFocus`), `refresh_dual_view` (calls `_refresh_dual_view()`, which other flows and tests keep using), `show_info` / `show_warning` / `show_error` (`wx.MessageBox(message, caption, wx.OK | wx.ICON_INFORMATION / ICON_WARNING / ICON_ERROR, parent=self)`), `choose_export_path` (the file-dialog part of `_export_document_with_dialog`: wildcard via `build_export_wildcard(descriptor, _)`, same title, style and `defaultFile`), `choose_export_directory` (the `wx.DirDialog` part of `on_export_all_documents`), `confirm_overwrite_all` (renamed `_confirm_overwrite_all`, same body).
- Deleted: `_set_conversion_busy`, `_start_conversion`, `_show_converting_dialog`, `_close_converting_dialog`, `_complete_conversion`, `_finish_conversion_success`, `_finish_conversion_failure`, `_missing_default_table_message`, `_start_export_conversion`, `_export_document_with_dialog`, `_continue_single_export`, `_write_export_document`, `_export_next_document`, `_show_export_all_result`, `_confirm_overwrite_all`, the `_conversion_runner` and `_convert_dialog_timer` attributes.
- Imports leaving `gui` (each in the step that stops using it): `conversion.jobs` (all names), `ConversionOutput`, `ConversionStageError`, `get_public_error_message`, `ExportContext`, `ExportBatchResult`. `ConversionRequest` (annotation of `_build_conversion_request`), `get_format` (Ctrl+S) and `build_export_wildcard` stay.
- M-9: `_show_file_error(self, message, error)` loses its unused `parent` parameter (no caller passes it).
- `ConvertingDialog` stays in `gui.py`.

### Strings

The msgids move with their call sites: `Please select a translation table first.`, `Conversion completed.`, the three failure templates to `conversion/presenter.py`; `Failed to export document: {error}`, `The document was exported successfully.`, `Export Complete` to `documents/export_coordinator.py`; `Info` and `Error` are also used by the new modules and stay in `gui.py` (the `ConvertingDialog` title and `_show_file_error`). `scripts/generate-pot.bat` extracts every `client/**/*.py` outside `tests`, so the msgid set is unchanged (353) and only `#:` references would move on the next `.pot` regeneration. No `.po`/`.mo` edit.

### Migration steps (each step is one green commit; the plan details them)

1. `test:` add `tests/conversion_harness.py` (`FakeThread` moved from `test_conversion_jobs.py`, `DeferredCalls`, `FakeTimers`) and the frame-level characterization class (Test Plan, part A). It passes on today's code, with the real runner wired into the frame by a fixture helper.
2. `test:` add the runner contract tests (part B) to `tests/test_conversion_jobs.py`. They pass on today's code.
3. `refactor:` add `conversion/presenter.py` and `tests/test_conversion_presenter.py` (part C), test-first. It still calls `runner.start(ConversionJobRequest(conversion_request=request))` with the default (unused) policy. `gui` does not use it yet.
4. `refactor:` route conversion through the presenter: wiring, `on_convert`, `_on_close`, the view methods, and a temporary `_start_export_conversion` that checks the table and calls `convert_for_export`. Delete the conversion state machine from the frame. Move the conversion tests of `GuiDocumentFlowsTest` (part E) and switch the characterization helper to the presenter.
5. `refactor:` keep completion state out of conversion jobs (I-3): delete `ConversionCompletionPolicy` and `ConversionJobRequest`, update `tests/test_conversion_jobs.py` and the presenter.
6. `refactor:` add `documents/export_coordinator.py` and `tests/test_export_coordinator.py` (part D), test-first. `gui` does not use it yet.
7. `refactor:` route export through the coordinator: wiring, the three entry points, the export view methods; delete the export chain from the frame; move the export tests (part E); switch the characterization helper.
8. `refactor:` drop the imports that became unused, M-9, final greps and the msgid scan.

The characterization tests from step 1 must pass with **unchanged bodies and expected logs** after every step. Only their fixture helper changes (step 4: build a `ConversionPresenter` instead of a runner; step 7: also build an `ExportCoordinator`).

## What Stays Identical

- Every row of the two tables above: checks and their order, the busy toggles (same widgets, same order: File, Translation, document list, source editor), the converting dialog (2000 ms, job and running checks, at most one, closed with `Unbind` + `Destroy`), messages, captions, icons, parents, the written files and their bytes, the cache read at write time, the cache write after manual conversions only.
- The asynchronous order described in "Asynchronous order today": which effects happen in the click turn, the worker, the timer turn and each delivery or chain turn. The first Export All step still runs synchronously in the menu turn; every later step is one `call_after` turn.
- Re-entrancy: every row of the re-entrancy table, including known defects 1 and 2.
- The runner: ids, stale filtering, `is_running()` false inside completion callbacks, daemon threads, no delivery for non-`ConversionStageError` exceptions.
- msgids (353, same set); `client/locales/` and `scripts/` untouched; the File menu build log of P1-2; the document flows of P1-3.

Intentional internal differences, none visible to users: the translation settings and dictionary path are read inside `build_request` (after busy is set) instead of in `on_convert` (before); nothing observable happens in between. `_start_export_conversion`'s unused `destination_path`/`format_key` parameters and `bool` result disappear. `_complete_conversion`'s test-only `display_text=` path disappears.

## Test Plan

### Shared harness (`tests/conversion_harness.py`, new, no `test_` prefix)

- `FakeThread`: moved unchanged from `tests/test_conversion_jobs.py`; `make_thread_factory()` returns a factory that records every thread.
- `DeferredCalls`: a `call_after` that queues `(fn, args, kwargs)`; `run_next()`, `run_all()` (until empty, including newly queued calls), `pending`.
- `FakeTimers`: a `call_later(ms, fn, *args)` that records `(ms, fn, args)` and returns a `FakeTimer` with `Stop()` (records `stopped`) and `fire()` (calls `fn(*args)`).

Putting them in a helper module avoids importing a `TestCase` module from another test module (which would run its tests twice).

### A. Frame characterization (step 1, `tests/test_gui_document_flows.py`, new class `ConversionExportFlowsCharacterizationTest`)

Each test builds a frame with `object.__new__`, a real `DocumentController`, a `DocumentWorkspaceService` on a temporary workspace, recording editors (value, `SetValue`, `SetFocus`, `Enable`), a recording document list (`Enable`), `GetMenuBar` returning a recording menu bar (`FindMenu` by label, `EnableTop`), and recording fakes patched on `gui` for `wx.MessageBox` (queued answers), `wx.FileDialog`, `wx.DirDialog` and `ConvertingDialog`; `gui.get_lang`/`gui.get_charset_maps` return constants. Every fake appends to one ordered `self.events` log. A fixture helper wires the conversion stack with a scripted fake converter (by source text: output, or `ConversionStageError`), `FakeThread`s, `DeferredCalls` for `gui.wx.CallAfter` and `FakeTimers` for `gui.wx.CallLater`. Tests drive only public entry points (`on_convert`, `on_export_document`, `on_export_all_documents`, `on_output_text_key_down`, `on_char_hook`, `_on_close`) and step the worker (`thread.run()`), the queue (`run_next()`) and the timers (`fire()`) explicitly, asserting the event log after each step.

Cases:

1. Manual success: click turn (busy on in order, no output change, request fields: source text, width, mode, dictionary path, tables copy, constant lang and maps; timer 2000 ms); worker queues one call and nothing else changes; delivery turn (timer stopped, busy off, output set then focused, document replaced with source text and braille, cache set, Dual View refreshed, "Conversion completed." / "Info" / information icon).
2. Manual success with no open document: output set and focused, no document or cache change, Dual View refreshed, completion box.
3. Failure messages for stages `ascii`, `text_processing`, `translation` and an unknown stage, and for the public texts (empty message, the liblouis "Can't translate: tables ... inbuf" text): busy off before one error box ("Error", error icon); output, document and cache unchanged.
4. Convert while running: nothing (no box, no new thread, no busy call).
5. Convert with no default table: one "Info" box, no busy, no thread.
6. Converting dialog: firing the timer while running shows one dialog (parent frame, `Show`, `Raise`); firing again creates none; delivery stops the timer and closes it (`Unbind(EVT_CLOSE)`, `Destroy`) before busy off. A timer fired after delivery does nothing.
7. Stale timer: job 1's timer fired while job 2 runs does nothing.
8. Close while running: `Veto`, no save, no dialog close; with `CanVeto()` false: save, dialog closed, `Skip`.
9. Single export with braille: file dialog arguments, written bytes, "Export Complete" box; `OSError` (directory at the target) gives the "Failed to export document" error box and no success box; a wrong extension is corrected.
10. Single export of a pending document: busy on, conversion of `document.text` (not the editor text); delivery: busy off, file written with the converted braille, "Export Complete"; output editor, cache and Dual View untouched; no "Conversion completed." box.
11. Single export of a pending document: conversion failure gives one stage error box ("Error"), nothing written; missing table gives one "Error" box, no busy, no thread.
12. Export All, mixed list `[ready, pending, ready-2, write-fail(directory), convert-fail, pending-ok]`: the turn boundaries (first step in the menu turn; each later step only after `run_next()`; a pending step only starts a conversion; its delivery writes and queues the next step), the busy toggles around each conversion only, and one warning summary at the end with the exact failure lines.
13. Export All, all ready: one information summary; no busy calls.
14. Export All with no default table: failures accumulate with the table message, no per-file boxes, each step still in its own turn.
15. Export All dialogs: folder cancel does nothing; no conflicts: no question; conflicts with "No": nothing written; with "Yes": all written.
16. Re-entrancy, Ctrl+S during a manual conversion on a pending open document: save, second job (busy on again, dialog close, new timer, first timer not stopped); finishing job 1 delivers nothing; job 2 delivery writes the file and shows "Export Complete"; the output editor is never set (known defect 2).
17. Re-entrancy, Ctrl+Tab during a manual conversion: the result goes into the newly opened document and its cache entry (known defect 1).
18. Re-entrancy, Convert in an Export All gap: the queued next pending step supersedes the manual job, which delivers nothing.

### B. Runner contract (step 2, `tests/test_conversion_jobs.py`)

Added to the 4 existing tests: threads are created with `daemon=True` and started once per job; `is_running()` is false inside `on_success` and `on_failure`; a stale delivery does not clear the current job's thread (`is_running()` stays true); an exception that is not a `ConversionStageError` delivers nothing and leaves `is_running()` false after the thread ends; `active_job_id` follows `start`. In step 5 the 4 existing tests lose their policy arguments; their assertions stay.

### C. `tests/test_conversion_presenter.py` (new, step 3, no wx, no stub scope)

A recording view (implements `ConversionView`, one ordered log), a real `DocumentController`, the harness `FakeThread`/`DeferredCalls`/`FakeTimers`, and a fake converter. It covers every bullet of the presenter design: `missing_default_table_message` for `{}`, `{"default": ""}`, `{"default": None}` and a set table; `format_conversion_error` for every stage and public text; `convert()` guard order (running, then table, then source text read); `_start` order; the timer callback checks; manual success with and without an open document and with an open name missing from the list (cache still written); manual failure; export success and failure (callbacks only, no output, cache or box); a later job after a completed one uses its own completion; a superseded job delivers nothing; `is_running()` and `missing_table_message()` read live state. These are the presenter-level versions of the frame tests moved in part E.

### D. `tests/test_export_coordinator.py` (new, step 6, no wx, no stub scope)

A recording view, a real `DocumentController`, a fake `ExportConversions` (scripted: start, then the test calls the stored callbacks), `DeferredCalls`, temporary directories with the real registry writers, and `import documents.export_coordinator as coordinator_module` for patching `get_format` (the P0 review I-1 import style). Cases: `write_document` (registry writer and `ExportContext` for every format, cache per document, non-exportable `ValueError`); `export_document` (default file and descriptor passed to the view, cancel, extension correction, ready, `OSError`, pending success and failure, missing table); `export_all` (folder cancel, snapshot after the dialog, conflict question only when needed and its answer, turn boundaries with `DeferredCalls`, `get_format` once per step, success/partial summary text, caption and kind, missing table per document, a `ValueError` stops the chain). One integration test runs a real `ConversionPresenter` (recording view, `FakeThread`) behind the coordinator for a mixed Export All.

### E. Updated and moved tests (`tests/test_gui_document_flows.py`)

| Today | After |
| --- | --- |
| `test_write_export_document_*` (4), `test_export_next_document_uses_registry_extension`, `test_export_all_*` (4), `test_single_pending_export_missing_table_*` | Same assertions in part D (step 7). |
| `test_start_conversion_builds_request_and_starts_runner`, `test_manual_conversion_updates_output_focus_and_shows_completion`, `test_export_conversion_calls_success_callback_without_manual_message`, `test_export_conversion_calls_error_callback_without_showing_worker_error`, `test_export_conversion_does_not_replace_dual_view_cache`, `test_text_processing_failure_uses_its_own_message`, `test_later_job_uses_its_own_policy_after_previous_completion`, `test_successful_manual_conversion_stores_segments_and_refreshes_open_viewer`, `test_missing_default_table_message_reports_only_unset_default` | Same assertions in part C (step 4). |
| `test_convert_without_default_table_*`, `test_convert_with_default_table_*` | Part C, plus a frame delegation test: `on_convert` calls `presenter.convert()`. |
| `test_export_conversion_with_default_table_starts_background_conversion` | Part C (`convert_for_export` request content) and a frame test of `_build_conversion_request_for_text`. |
| P1-2 `test_export_dialog_title_default_file_wildcard_and_style`, `test_export_dialog_corrects_only_a_wrong_extension`, `test_real_writers_produce_today_bytes`, `test_export_all_html_uses_each_document_cache` | Same assertions, entered through `frame._export_coordinator` built with the frame as view (step 7). The `gui._` patch still reaches the dialog title and wildcard. |
| `test_ctrl_s_in_output_editor_exports_open_document_as_brl` | Expects `call.coordinator.export_document(<open document>, "brl")` between the save and `SetFocus`. |
| `_make_frame`, `_make_workspace_frame` | Set `_conversion_presenter` / `_export_coordinator` (mocks) instead of `_conversion_runner`, `_convert_dialog_timer`, `_set_conversion_busy`, `_close_converting_dialog`, `_show_export_all_result`; `test_close_vetoes_when_save_fails` checks `close_converting_dialog`. |

New frame tests (red first in steps 4 and 7): `FrameConversionDelegationTest` (wiring in `_initialize_conversion_state` with `wx.CallAfter`/`wx.CallLater`, the frame as view and its controller; `on_convert`, Ctrl+Enter, `_on_close` delegate) and `FrameExportDelegationTest` (wiring; the three entry points keep their guards and save-first and then call the coordinator). Frame view-method tests: `set_conversion_busy` (FindMenu/EnableTop/Enable calls, menu bar `None`, label not found), `show_converting_dialog` idempotence, `close_converting_dialog`, `show_conversion_output`, `show_info`/`show_warning`/`show_error` arguments, `choose_export_directory`, `confirm_overwrite_all`.

## Acceptance Criteria

1. `grep -rn "ConversionCompletionPolicy\|ConversionJobRequest" client` prints nothing.
2. `grep -nE "_start_conversion|_complete_conversion|_finish_conversion_|_start_export_conversion|_export_next_document|_write_export_document|_continue_single_export|_show_export_all_result|_missing_default_table_message|_export_document_with_dialog|_conversion_runner|_convert_dialog_timer|_set_conversion_busy|_show_converting_dialog|_close_converting_dialog|_confirm_overwrite_all" client/gui.py` prints nothing.
3. `grep -nE "^(import wx|from wx)|^(import|from) gui" client/conversion/presenter.py client/documents/export_coordinator.py client/conversion/jobs.py` prints nothing.
4. `grep -n "wx.CallAfter\|wx.CallLater" client/gui.py` prints only the lines in `_initialize_conversion_state`.
5. `grep -nE "\b(ConversionStageError|ConversionOutput|get_public_error_message|ExportContext|ExportBatchResult)\b|conversion\.jobs" client/gui.py` prints nothing, and `grep -n "parent: wx.Window | None = None" client/gui.py` does not match `_show_file_error`.
6. The characterization class from step 1 is unchanged except for its fixture helper (`git diff <step-1 commit> -- client/tests/test_gui_document_flows.py` shows no change inside its test methods).
7. `git diff main --stat -- client/locales scripts` is empty; the msgid scan reports the same 353 msgids.
8. Roadmap verification passes: `cd client && python3 -m unittest tests.test_conversion_jobs tests.test_export_coordinator tests.test_conversion_presenter tests.test_gui_document_flows -v`. Also `tests.test_i18n tests.test_wx_stub tests.test_removed_dead_code tests.test_menu_builder tests.test_workspace_service`.
9. Full suite: `failures=1` (only P2-5), `errors=0`, `skipped=9` on Linux.
10. Stub-scope order: `tests.test_conversion_presenter` and `tests.test_export_coordinator` pass alone, and `tests.test_gui_document_flows tests.test_conversion_presenter tests.test_export_coordinator` passes in both orders; a seeded shuffle of the full suite shows no new failures.

## Risks

- **Async order drift** (high impact, medium likelihood). Calling `on_success` before busy off, writing the cache for export conversions, or running the first Export All step through `call_after` would all pass naive tests. Mitigation: part A logs every effect per turn with a deferred `call_after`, and its bodies are frozen from step 1.
- **Job bookkeeping** (medium). The presenter stores the completion after `runner.start` returns. This is correct only because `call_after` defers. Mitigation: the contract is documented; the harness never runs a target inside `start()`; a presenter test with a synchronous `call_after` and a manually run thread pins it.
- **Stub masking** (medium). A frame without `_conversion_presenter` or `_export_coordinator` gets a no-op function and silently does nothing. Mitigation: every frame helper sets both; part A asserts real effects; delegation tests use `Mock(spec=...)`.
- **View methods on the frame** (low). New public names on a `wx.Frame` subclass could collide with wx names. All chosen names are lower-case `snake_case`; wxPython uses `CamelCase`. Tests patching `frame._refresh_dual_view` keep working because `refresh_dual_view` delegates to it.
- **Translation binding** (low). Presenter and coordinator strings use their own module `_`. Tests that patch `gui._` (only the P1-2 dialog test) still reach the strings that stay in `gui.py`.
- **Stub-scope import of new modules** (low). Both modules are imported first by `gui` under the stub scope. Mitigation: the order checks in acceptance criterion 10 (P0 review I-1).
- **Test churn** (medium). About 25 GUI tests move. Mitigation: the table in part E maps each one; the plan moves them in the same commit that deletes the frame method.
- **Windows-only behavior** (medium, unverifiable here). Real threads, `wx.CallAfter`, `wx.CallLater`, `ConvertingDialog`, `EnableTop` and message boxes run only in the packaged app. See the verification debt.

## Known defects found during this investigation (not fixed here)

These exist on `main` today. This task keeps them, and part A pins 1 and 2 with `KNOWN BUG` comments.

1. **A manual conversion's result lands in whatever document is open when it completes.** Ctrl+Tab, Ctrl+Shift+Tab and Ctrl+O stay reachable while busy (the frame char hook stays active and the Braille Result editor stays enabled). The braille, the current source-editor text and the dual-view cache are written to the newly opened document.
2. **Export conversions do not check for a running conversion.** Ctrl+S in the Braille Result editor during a conversion, or the Export All chain resuming after a Convert started between steps, starts a second job. The first job's result is dropped as stale without any message; a manual conversion never updates the output.
3. **Exporting a pending document as HTML writes the cached dual view, not the fresh conversion.** The export conversion's `dual_view_segments` are discarded, so the HTML shows the last manual conversion of that document, or the "No conversion data" page.
4. **The Export All summary is not translated.** `documents/export_results.py` passes its title and messages to `_()` through variables, so they are not extracted; their zh_TW entries are obsolete (`#~`). Only the all-success title ("Export Complete") is translated, because the same literal exists elsewhere. The empty-message fallback "An unknown error occurred." and "The selected translation table could not translate this text." are also not msgids.
5. **`set_conversion_busy` finds menus by translated title** (refactor.md section 5.3). It works because the labels never change at runtime. Kept as is.
6. **A worker exception that is not wrapped in `ConversionStageError` leaves the UI busy forever.** Today only a `BaseException` outside `Exception` can do that, because the service wraps every `Exception`.
7. **A `ValueError` from a writer stops the Export All chain without a summary.** Unreachable from the menu, which offers only exportable formats.

Fixing 1 and 2 would mean blocking those shortcuts while busy or queuing export conversions. That is a user-visible behavior change and belongs in its own task; the presenter is the natural place for it afterwards.

## Windows verification debt

- On a packaged build, before and after: Convert a short text and a long one (the "converting" dialog appears only after 2 s and closes on completion; File and Translation menus, document list and source editor are disabled meanwhile); a conversion error (wrong table) with its message; closing the window during a long conversion (vetoed).
- Export (DEP, BRL, HTML) of a converted and of a pending document; Ctrl+S in the Braille Result editor; Export All with a mix of pending and converted documents, with existing files (overwrite question, both answers), and with a read-only target file (partial summary).
- With the zh_TW catalog: all messages above in Chinese as before (and the summary in English, defect 4).
- Known defects 1 and 2 behave as before (Ctrl+Tab and Ctrl+S during a long conversion).
- No menu, dialog or string changes, so no screenshots and no `generate-pot.bat` run are needed.

## Out of Scope

- Fixing the known defects above, including blocking shortcuts while busy.
- Storing menu references instead of `FindMenu` by title (defect 5).
- Moving the save-first guards or selection lookups out of the frame, or moving `ConvertingDialog`.
- Changing `ExportBatchResult` or marking its strings (a localization change).
- Dual View window lifecycle, `DualViewFrame`, and the browser view.
- A generic task framework, cancellation of running jobs, or progress reporting.
- `ApplicationPaths` injection (P2-6), `TranslationResult` work (P1-5, P2-5), indentation (P2-8).
