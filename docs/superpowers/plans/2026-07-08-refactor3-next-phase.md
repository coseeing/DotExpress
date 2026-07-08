# Refactor 3 Next Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converge the boundaries introduced in earlier refactors by making `DocumentController` the single source of truth for document state, moving conversion completion policy into per-job workflow state, and centralizing document format knowledge in a registry without changing user-visible behavior.

**Architecture:** Keep wxPython as the outer UI layer. `client/documents/controller.py` owns document state and dual-view cache. `client/conversion/jobs.py` owns conversion job lifecycle and carries completion policy with each request/result. `client/documents/formats.py` owns document format descriptors, import/export lookup, suffixes, and wildcard helpers. `client/gui.py` remains responsible for wx controls, dialogs, message boxes, and event handling.

**Tech Stack:** Python 3, wxPython, `dataclasses`, `threading`, `unittest`, `unittest.mock`

**Specs:**
- `docs/superpowers/specs/2026-07-08-refactor3-next-phase-design.md`
- `docs/superpowers/specs/2026-07-08-refactor3-next-phase-design_zh-TW.md`

---

## File Structure

- Modify `client/documents/controller.py`: add stable accessors/properties and own dual-view cache state.
- Modify `client/gui.py`: remove mirrored document state ownership, remove frame-global conversion policy fields, and use format registry helpers.
- Modify `client/conversion/jobs.py`: attach completion policy to `ConversionJobRequest`, `ConversionJobSuccess`, and `ConversionJobFailure`.
- Create `client/documents/formats.py`: document format descriptors, registry helpers, wildcard helpers, import loader lookup, and export writer lookup.
- Modify `client/documents/workspace.py`: use the format registry for import loaders and batch export writer/suffix decisions.
- Modify `client/ui/import_dialog.py`: derive import filters and wildcard text from the format registry.
- Modify tests:
  - `client/tests/test_document_controller.py`
  - `client/tests/test_conversion_jobs.py`
  - `client/tests/test_document_formats.py`
  - `client/tests/test_document_workspace.py`
  - `client/tests/test_import_dialog.py`
  - `client/tests/test_gui_document_flows.py`

## Task 1: Make DocumentController Own Document State

**Files:**
- Modify: `client/documents/controller.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_document_controller.py`
- Modify: `client/tests/test_gui_document_flows.py`
- Reference: `client/documents/session.py`

- [ ] **Step 1: Add controller accessor tests**

Extend `client/tests/test_document_controller.py` with focused tests for:

- `document_names` returning sorted or current-order names according to existing controller semantics
- `open_document_name` and `selected_document_name` exposing the current names without requiring direct field access
- `get_document(name)` returning the expected `Document` or `None`
- `open_document` updating both open and selected names
- `rename_document` moving dual-view cache entries from old name to new name
- `delete_document` removing dual-view cache entries and choosing the existing preferred document behavior

- [ ] **Step 2: Run the focused controller tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_document_controller -v
```

Expected before implementation: failures only for missing new accessors or properties.

- [ ] **Step 3: Add controller accessors without wx dependencies**

In `client/documents/controller.py`, add:

- `document_names`
- `open_document_name`
- `selected_document_name`
- `get_document(name)`
- `sort_documents()`

Keep existing `documents`, `open_name`, `selected_name`, and `dual_view_results_by_document` attributes until GUI and tests have moved. Do not import wx.

- [ ] **Step 4: Add temporary delegating frame properties**

In `client/gui.py`, add properties on `BrailleFrame` so existing tests and call sites can move incrementally:

- `documents` delegates to `self._document_controller.documents`
- `_open_document_name` delegates to `self._document_controller.open_name`
- `_selected_document_name` delegates to `self._document_controller.selected_name`
- `_dual_view_results_by_document` delegates to `self._document_controller.dual_view_results_by_document`

Use setters only as compatibility paths during migration. The backing storage should remain in `DocumentController`.

- [ ] **Step 5: Update frame initialization**

In `_initialize_state()`:

- create `DocumentController` before assigning document state through compatibility properties
- avoid creating a standalone `self.documents` list before the controller exists
- keep startup behavior unchanged

- [ ] **Step 6: Route frame document helpers through the controller**

Update `client/gui.py`:

- `_sort_documents()` calls `self._document_controller.sort_documents()`
- `_get_document_by_name()` calls `self._document_controller.get_document(name)`
- `_replace_document()` calls `self._document_controller.replace_document(updated_document)`
- `_document_name_exists()` uses controller documents
- `_refresh_document_list()` reads from controller documents and updates selected name through the controller-backed property
- `_open_document_by_name()` calls `self._document_controller.open_document(name)` without `_sync_document_controller_state()`
- rename/delete/delete-all flows call controller methods directly without bidirectional sync

- [ ] **Step 7: Remove or reduce `_sync_document_controller_state()`**

Delete `_sync_document_controller_state()` after all call sites are removed. If a temporary shim remains, it must be one-way and documented in the final handoff.

Verify no call sites remain:

```bash
rg -n "_sync_document_controller_state" client/gui.py client/tests
```

- [ ] **Step 8: Run document workflow regression tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_document_controller tests.test_document_session tests.test_document_workspace tests.test_gui_document_flows -v
```

Expected: all tests pass; document open/select/rename/delete behavior remains unchanged.

## Task 2: Move Conversion Completion Policy into Per-Job State

**Files:**
- Modify: `client/conversion/jobs.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_conversion_jobs.py`
- Modify: `client/tests/test_gui_document_flows.py`
- Reference: `client/conversion/service.py`

- [ ] **Step 1: Add policy-focused job tests**

Extend `client/tests/test_conversion_jobs.py` so `ConversionJobRequest` can carry a policy object and delivered results preserve it:

- success result includes the same policy object as the request
- failure result includes the same policy object as the request
- stale success does not deliver an old policy
- stale failure does not deliver an old policy

- [ ] **Step 2: Add GUI workflow characterization tests**

Update `client/tests/test_gui_document_flows.py` for the new behavior:

- manual conversion updates output and may show the conversion success message
- export-triggered conversion does not update the output field
- export-triggered conversion does not show the manual success message
- conversion failure uses the per-job `on_error` callback when provided
- after completion, a later job does not inherit callbacks or flags from an earlier job

- [ ] **Step 3: Run focused conversion tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_conversion_jobs tests.test_gui_document_flows -v
```

Expected before implementation: failures around request/result policy fields and old frame-global callback assumptions.

- [ ] **Step 4: Add policy dataclass in `conversion/jobs.py`**

In `client/conversion/jobs.py`, add a frozen dataclass such as:

```python
@dataclass(frozen=True)
class ConversionCompletionPolicy:
    on_success: Callable[[str], object] | None = None
    on_error: Callable[[str], object] | None = None
    update_output: bool = True
    show_success: bool = True
```

Then add `completion_policy: ConversionCompletionPolicy` to:

- `ConversionJobRequest`
- `ConversionJobSuccess`
- `ConversionJobFailure`

No wx objects should be stored in the policy. Existing callback functions may still be frame methods or lambdas created by the frame.

- [ ] **Step 5: Preserve policy through runner delivery**

Update `ConversionJobRunner._run_job()` so success and failure results include `request.completion_policy`.

Keep stale-job protection in `_deliver_success()` and `_deliver_failure()` unchanged except for the widened result shape.

- [ ] **Step 6: Remove frame-global conversion policy fields**

In `client/gui.py`, remove:

- `_convert_on_success`
- `_convert_on_error`
- `_convert_update_output`
- `_convert_show_success`

Update `_start_conversion()` so it creates a `ConversionCompletionPolicy` from the method arguments and passes it inside `ConversionJobRequest`.

- [ ] **Step 7: Update conversion completion handlers**

Change `_complete_conversion()` to accept a `ConversionCompletionPolicy` argument.

Use that policy for:

- error callback routing
- output text update
- dual-view refresh
- success callback routing
- success message display

Update `_finish_conversion_success()` and `_finish_conversion_failure()` to pass `result.completion_policy`.

- [ ] **Step 8: Run conversion regression tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_conversion_jobs tests.test_conversion_service tests.test_gui_document_flows -v
```

Expected: conversion job tests and GUI conversion/export flows pass.

## Task 3: Add Document Format Descriptor Registry

**Files:**
- Create: `client/documents/formats.py`
- Modify: `client/documents/workspace.py`
- Modify: `client/ui/import_dialog.py`
- Modify: `client/gui.py`
- Create: `client/tests/test_document_formats.py`
- Modify: `client/tests/test_document_workspace.py`
- Modify: `client/tests/test_import_dialog.py`
- Modify: `client/tests/test_gui_document_flows.py`

- [ ] **Step 1: Add format registry tests**

Create `client/tests/test_document_formats.py` covering:

- `get_format("dep")` returns a descriptor with extension `.dep`
- `get_format("brl")` returns a descriptor with extension `.brl`
- `get_format("missing")` raises `ValueError`
- importable descriptors are ordered as `dep`, `docx`, `epub`, `pdf`, `txt`
- exportable descriptors include `dep` and `brl`
- all-supported import wildcard matches the existing order and text
- `dep` export does not require pre-existing braille
- `brl` export requires braille

- [ ] **Step 2: Run the new format test first**

Run from `client/`:

```bash
python3 -m unittest tests.test_document_formats -v
```

Expected before implementation: `ModuleNotFoundError` for `documents.formats`.

- [ ] **Step 3: Implement `documents/formats.py`**

Create a descriptor dataclass with at least:

- `key`
- `extension`
- `wildcard_label`
- `loader`
- `writer`
- `requires_braille`
- `supports_import`
- `supports_export`

Include descriptors for existing formats only:

- `dep`: import/export, `.dep`, loader `load_document_package`, writer `save_document_package(..., include_pending_metadata=False)`
- `brl`: export only, `.brl`, writer `export_document_brl`, requires braille
- `txt`: import only, `.txt`, loader `load_text_document`
- `docx`: import only, `.docx`, loader wraps `import_docx`
- `epub`: import only, `.epub`, loader wraps `import_epub`
- `pdf`: import only, `.pdf`, loader wraps `import_pdf`

Provide helper functions:

- `get_format(key)`
- `get_import_formats()`
- `get_export_formats()`
- `get_import_loader(key)`
- `get_export_writer(key)`
- `build_import_wildcard(translate=lambda value: value)`
- `build_single_format_wildcard(key, translate=lambda value: value)`

- [ ] **Step 4: Avoid circular imports while moving loaders**

If `documents.formats` needs `Document`, `load_document_package`, or `export_document_brl`, keep imports lazy or move only thin lookup helpers into the registry so `documents.workspace` and `documents.formats` do not import each other recursively.

Preferred implementation:

- keep `Document` and file read/write functions in `documents.workspace`
- define descriptors in `documents.formats` using callables imported after workspace functions are defined, or place registry construction behind functions that import workspace lazily
- keep the public registry API stable regardless of the internal circular-import avoidance

- [ ] **Step 5: Update workspace import/export logic**

In `client/documents/workspace.py`:

- replace direct `IMPORT_LOADERS` ownership with registry-backed lookup
- update `batch_import_documents()` to validate `format_key` through registry helpers
- update `batch_import_documents()` all-format dispatch to call `get_import_loader(loader_key)`
- update `batch_export_documents_to_folder()` to use descriptor extension and export writer instead of `format_key == "dep"`

Keep `IMPORT_LOADERS` only as a compatibility alias if existing tests or callers still need it temporarily. If retained, document that the registry is the source of truth.

- [ ] **Step 6: Update import dialog helpers**

In `client/ui/import_dialog.py`:

- derive `IMPORT_FILTERS` or `get_import_filters()` from `documents.formats`
- keep `ALL_SUPPORTED_FILTER_INDEX` behavior unchanged
- keep `build_import_wildcard()` output unchanged for current tests

- [ ] **Step 7: Update GUI format branches**

In `client/gui.py`:

- remove local `DEP_WILDCARD`, `TXT_WILDCARD`, `PDF_WILDCARD`, `DOCX_WILDCARD`, `EPUB_WILDCARD`, `BRL_WILDCARD`, and `IMPORT_WILDCARDS` if no longer used
- `_get_dep_wildcard()`, `_get_brl_wildcard()`, and `_get_import_wildcard()` should delegate to registry/import-dialog helpers
- `_export_document_with_dialog()` should derive default filename, wildcard, and suffix from the export descriptor
- `_write_export_document()` should call the export writer from the descriptor
- `_export_next_document()` should derive destination suffix from the descriptor extension
- export-all conflict detection should use descriptor extension

- [ ] **Step 8: Update tests that patch old loader globals**

Update `client/tests/test_document_workspace.py` tests that patch `documents.workspace.IMPORT_LOADERS`.

Prefer patching registry lookup helpers or descriptor loader mappings in `documents.formats` so tests verify the new source of truth.

- [ ] **Step 9: Run format and import/export regression tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_document_formats tests.test_document_workspace tests.test_import_dialog tests.test_gui_document_flows -v
```

Expected: current import/export labels, ordering, suffixes, and behavior remain unchanged.

## Task 4: Final Compliance Check

**Files:**
- Review only unless failures require fixes.

- [ ] **Step 1: Run the core regression suite**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_document_controller \
  tests.test_document_session \
  tests.test_document_workspace \
  tests.test_conversion_jobs \
  tests.test_conversion_service \
  tests.test_import_dialog \
  tests.test_gui_document_flows -v
```

- [ ] **Step 2: Search for old ownership patterns**

Run from repo root:

```bash
rg -n "_sync_document_controller_state|_convert_on_success|_convert_on_error|_convert_update_output|_convert_show_success|format_key ==|IMPORT_LOADERS|IMPORT_WILDCARDS" client
```

Expected:

- no `_sync_document_controller_state` call sites
- no frame-global conversion policy fields
- no GUI-owned import/export wildcard registry
- no direct export branch that can be replaced by descriptor lookup
- any remaining `IMPORT_LOADERS` is a documented compatibility alias, not the source of truth

- [ ] **Step 3: Verify spec alignment**

Confirm the implementation still satisfies:

- no user-visible string changes
- no new document format
- no wx dependency introduced into `documents.controller`, `documents.formats`, or `conversion.jobs`
- `BrailleFrame` owns wx interactions only

- [ ] **Step 4: Record implementation notes**

In the handoff, include:

- exact test commands run
- any skipped tests and why
- whether any compatibility shim remains
- any optional importer dependency limitations

## Acceptance Criteria

- `DocumentController` owns document state and dual-view cache; `BrailleFrame` does not keep a separate mutable copy requiring bidirectional synchronization.
- Conversion completion behavior is attached to each job request/result, not stored in frame-global mutable fields.
- Import/export format knowledge is centralized in `documents.formats`; current `dep`, `brl`, `txt`, `docx`, `epub`, and `pdf` behavior remains unchanged.
- Core client regression tests pass, or any environment-limited tests are explicitly documented with exact failure reasons.
