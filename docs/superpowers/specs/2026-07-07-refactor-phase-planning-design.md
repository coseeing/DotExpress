# DotExpress Refactor Phase Planning Design

Date: 2026-07-07

## Goal

Define an implementation-ready phased refactor plan for the next stage of
DotExpress maintenance, based on the agreed priorities from
`docs/refactor/refactor2.md`.

The plan should preserve current user-visible behavior while reducing the
largest responsibility hotspots in the client codebase.

## Agreed Priority Order

Use this execution order:

1. Extract a document workflow controller from `BrailleFrame`
2. Extract dictionary entry and dictionary-domain logic from `dialog.py`
3. Extract conversion job orchestration from `BrailleFrame`
4. Split the internal conversion pipeline in `conversion/service.py`

This is a risk-balanced sequence:

- Start with the biggest SRP issue in `client/gui.py`
- Follow with a lower-coupling dictionary/domain extraction
- Then isolate conversion threading and callback orchestration
- Finally split conversion internals after outer orchestration is cleaner

## Non-Goals

This planning change does not:

- redesign the wx UI
- change user-facing strings or menu behavior
- introduce a dependency-injection container
- convert the app into full MVC in one step
- add a plugin system for translation
- refactor the server as part of this cycle

## Phase 1: Document Workflow Controller

### Goal

Reduce `BrailleFrame` responsibility for document state decisions without
changing the current UI behavior.

### Scope

Introduce a controller module such as:

- `client/documents/controller.py`

The controller should own:

- `documents`
- `selected_document_name`
- `open_document_name`
- dual-view result cache keyed by document name

The controller should perform:

- open/select decisions
- replace document updates
- rename state updates
- delete state updates
- delete-all state reset

### Keep In `BrailleFrame`

- wx dialogs
- `TextCtrl` and `ListCtrl` reads/writes
- message boxes
- file persistence timing
- final `SetTitle(...)` calls

### First Slice

Extract these flows first:

- `_open_document_by_name`
- `_replace_document`
- rename-related document and dual-view cache updates
- delete / delete-all state transitions

### Acceptance Criteria

- user-visible open/switch/rename/delete behavior remains unchanged
- dual-view cache still tracks document rename/delete correctly
- `tests.test_document_session`
- `tests.test_document_workspace`
- `tests.test_gui_document_flows`
  all remain green

## Phase 2: Dictionary Entry Domain Extraction

### Goal

Move dictionary entry model, validation, and CSV persistence out of
`client/dialog.py`, leaving wx dialog classes focused on interaction.

### Scope

Introduce:

- `client/dictionaries/entries.py`

Move these responsibilities from `dialog.py`:

- `DictionaryEntry`
- entry type constants and normalization
- dictionary entry validation
- dictionary entry CSV load/save
- Bopomofo and Unicode braille validation helpers

### Keep In `dialog.py`

- wx dialog classes
- button layout
- focus handling
- virtual list behavior
- message box behavior

### Acceptance Criteria

- `SpeechSymbolsDialog` behavior remains unchanged
- `DictionaryManagementDialog` behavior remains unchanged
- entry validation and CSV roundtrip are covered by focused tests
- `tests.test_dictionary_management_dialog`
- `tests.test_speech_symbols_dialog`
- dictionary-related tests remain green

## Phase 3: Conversion Job Runner

### Goal

Move conversion thread and callback orchestration out of `BrailleFrame` without
changing conversion behavior.

### Scope

Introduce:

- `client/conversion/jobs.py`

Add small explicit types such as:

- `ConversionJobRequest`
- `ConversionJobResult`
- `ConversionJobRunner`

The job runner should own:

- job id assignment
- worker thread execution
- success/failure result delivery
- stale-job protection

### Keep In `BrailleFrame`

- `ConvertingDialog`
- busy-state UI enable/disable
- output text updates
- dual-view refresh after successful conversion
- success/error message boxes

### Acceptance Criteria

- manual convert behavior remains unchanged
- export-triggered conversion still suppresses manual success dialogs
- stale job results cannot overwrite newer jobs
- `tests.test_gui_document_flows`
- `tests.test_conversion_service`
  remain green

## Phase 4: Conversion Pipeline Internal Split

### Goal

Keep the current conversion entry points stable while splitting internal
conversion steps into smaller modules.

### Scope

Keep these public APIs unchanged:

- `ConversionRequest`
- `ConversionOutput`
- `ConversionStageError`
- `convert_text_with_alignment()`
- `convert_text_for_output()`

Split internals into modules such as:

- `conversion/segments.py`
- `conversion/plain_text.py`
- `conversion/wrapping.py`
- `conversion/output.py`

### Suggested Extraction Order

1. inline math segmentation and boundary spacing
2. plain-text translation flow
3. merge / token cleanup / wrap flow
4. output formatting and public error-message helpers

### Acceptance Criteria

- public conversion entry points remain unchanged
- dual-view alignment behavior remains unchanged
- translation result boundaries remain intact
- `tests.test_conversion_service`
- language detection tests
- dual-view tests
- translation adapter/runtime tests
  remain green

## Test Strategy

Each phase should start with characterization tests for the current behavior.

Use this pattern for every slice:

1. add focused non-wx tests for the new module
2. route existing integration code through the new boundary
3. keep current GUI flow tests passing
4. avoid user-visible behavior changes during the extraction

Key regression suites:

- `tests.test_gui_document_flows`
- `tests.test_document_session`
- `tests.test_document_workspace`
- `tests.test_conversion_service`
- `tests.test_translation_runtime_provider`
- `tests.test_dictionary_management_dialog`
- `tests.test_speech_symbols_dialog`

## Design Summary

This phased plan intentionally avoids broad rewrites. It follows the pattern that
recent successful refactors already established in this repository:

- extract one real responsibility boundary at a time
- keep behavior stable
- move state and domain logic inward
- leave wx UI as the outer coordination layer until narrower abstractions are in place

The first execution target should be the document workflow controller. It offers
the highest maintainability payoff with the lowest architectural speculation.
