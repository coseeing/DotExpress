# Refactor 2 Recommendation

Date: 2026-07-07

## Scope

This review looked at the current `client/` and `server/` source code, with extra
context from recent Superpowers design and implementation history:

- `docs/superpowers/specs/2026-07-06-settings-package-refactor-design.md`
- `docs/superpowers/plans/2026-07-06-settings-package-refactor.md`
- `docs/superpowers/specs/2026-07-06-platform-translation-adapters-design.md`
- `docs/superpowers/plans/2026-07-06-platform-translation-adapters.md`
- `docs/superpowers/specs/2026-07-06-dotexpress-settings-dialog-design.md`
- `docs/superpowers/specs/2026-06-30-import-export-conversion-design.md`
- `docs/superpowers/specs/2026-07-01-dual-view-braille-alignment-design.md`
- `docs/superpowers/history/2026-07-06-02-platform-translation-adapters/review_task.md`

The recent architecture direction is clear: keep behavior stable, extract narrow
boundaries, and avoid large rewrites. The settings package and translation adapter
work already moved the codebase toward small model/persistence modules, explicit
runtime injection, and wx UI as the outer layer.

## Current Architecture Snapshot

The codebase already has several good boundaries:

- `client/settings/` now owns settings models, staged state, persistence helpers,
  and the multi-category settings dialog.
- `client/adapters/translation/` uses Adapter and Strategy-style runtime
  selection for liblouis, MathCAT, and fallback translation.
- `client/documents/session.py` contains pure document selection decisions.
- `client/documents/workspace.py` centralizes document package persistence and
  import/export helpers.
- `client/ui/` contains small focused UI helpers for menus, shortcuts, section
  navigation, font support, and dual-view frame behavior.
- `server/app/` is small and already has an acceptable FastAPI app factory and
  persistence split.

The remaining pressure points are concentrated:

- `client/gui.py` is about 1,700 lines and handles layout, menu construction,
  document session state, file dialogs, dictionary workflows, settings commits,
  conversion threading, export batching, dual-view refreshes, and app lifecycle.
- `client/dialog.py` is about 900 lines and mixes dictionary entry data,
  dictionary CSV persistence, validation, virtual list behavior, symbol editing,
  name dialogs, and dictionary management UI.
- `client/settings/dialogs.py` is about 800 lines and is currently acceptable,
  but future settings categories will push it past a healthy boundary unless
  panel construction is split.
- `client/conversion/service.py` has a useful request/output boundary, but one
  module still performs inline math parsing, language segmentation, dictionary
  replacement, runtime calls, wrapping, and ASCII post-processing.

## Design Patterns Review

### Patterns Already Working

Adapter / Strategy:

`client/adapters/translation/` is the strongest current example. Native liblouis,
native MathCAT, and fallback translators share small protocols through
`TranslationRuntime`. This is a good model for future seams because conversion
does not need to know which backend is active.

Facade:

`conversion.service.convert_text_with_alignment()` and
`conversion.service.convert_text_for_output()` already act as facades over
dictionary mapping, language detection, translation, wrapping, and ASCII
conversion. The idea is good, but the facade currently owns too many internal
steps.

Template Method:

`settings.dialogs.SettingsPanel` gives each settings category the same lifecycle:
`make_settings`, `on_save`, `load_snapshot`, validation, activation, and discard.
This is appropriate for wx settings panels.

Command Descriptor:

`ui.action_menu.get_document_menu_descriptors()` and
`ui.translation_menu.get_translation_menu_items()` are small command descriptor
sources. This pattern should be extended to reduce menu wiring in `gui.py`.

Decision Model:

`documents.session` and `dictionaries.actions` contain pure planning functions.
This is a good lightweight alternative to a large domain service layer.

### Patterns To Apply Next

Application Controller / Presenter:

Introduce a non-wx controller for document workflows. It should coordinate
document list state, open/selected document names, rename/delete decisions, and
dual-view result cache. `BrailleFrame` should become mostly view wiring and
dialog display.

Service / Use Case:

Move import, export, and conversion-launch workflows into use-case functions or
small classes. These workflows currently span wx dialogs, filesystem work,
conversion callbacks, and result reporting inside `BrailleFrame`.

Command:

Represent menu commands as descriptors that include key, label, enabled-state
query, and handler name. This will remove hard-coded menu binding maps from
`gui.py` and make menu order changes less invasive.

Pipeline / Chain of Responsibility:

Split conversion into named steps: character mapping, inline math segmentation,
plain-text translation, math translation, merge, wrap, output formatting. Keep
the public conversion facade, but move the internal steps into testable units.

Repository / Gateway:

Create explicit repositories for document workspace and dictionary storage only
if call sites continue to grow. The current function modules are fine, but
`gui.py` should depend on a narrower interface than dozens of direct functions.

ViewModel:

Use small dataclasses for UI-facing state such as dictionary management rows,
export progress, and conversion job state. This reduces mutable fields scattered
across `BrailleFrame`.

## SOLID Review

### Single Responsibility Principle

Highest risk: `BrailleFrame` in `client/gui.py`.

It currently owns frame layout, document editing state, persistence calls,
dictionary lifecycle callbacks, settings commits, export orchestration,
conversion threading, conversion completion behavior, and dual-view cache
updates. This is the main reason future changes require broad GUI tests and
careful manual regression.

Second risk: `client/dialog.py`.

It mixes dialog classes with dictionary CSV loading/saving and entry validation.
Some of that domain logic is already used by tests, so it is a strong candidate
for extraction.

Moderate risk: `client/conversion/service.py`.

The module is cohesive around conversion, but individual responsibilities are
stacked in one flow. This is manageable now, yet new conversion modes or backend
options will make it harder to change safely.

### Open/Closed Principle

Good: translation adapters are open to new backends by adding new factories and
translator implementations.

Weak: adding a document import/export format touches multiple places:
`documents.workspace.IMPORT_LOADERS`, wildcard/filter helpers, export branching,
and GUI export flow. A format registry or descriptor table would reduce this.

Weak: adding settings categories still means growing `settings/dialogs.py`.
The framework is ready, but panel modules should split before the next category
is added.

### Liskov Substitution Principle

Good: `BrailleTextTranslator` and `MathSegmentTranslator` implementations are
substitutable as long as they return valid `TranslationResult` mappings.

Watch: fallback text translation intentionally uses `raw` instead of replacement
`text`. This is correct by design, but tests should keep documenting it because
it is a deliberate difference from native mapping behavior.

### Interface Segregation Principle

Good: text and math translator protocols are separate.

Weak: `BrailleFrame` effectively exposes many private methods as integration
points for tests and callbacks. This means tests depend on internal wx frame
details instead of smaller workflow interfaces.

Weak: dictionary management callbacks pass through the main frame even though
the dialog only needs a narrow dictionary workflow interface.

### Dependency Inversion Principle

Good: conversion depends on `TranslationRuntime` protocols rather than native
libraries.

Weak: `gui.py` depends directly on many concrete filesystem, config, dictionary,
document, settings, and conversion functions. This makes GUI tests broad and
requires extensive stubbing.

Weak: `dialog.py` imports dictionary manager functions directly. If dictionary
storage changes, the UI module changes too.

## Recommended Next Refactor

### Priority 1: Extract A Document Workflow Controller From `BrailleFrame`

Recommendation:

Create a `client/documents/controller.py` or `client/app/document_controller.py`
module that owns document state transitions independent of wx controls.

Initial responsibilities:

- Store `documents`, `selected_document_name`, `open_document_name`
- Open, select, rename, delete, delete all, and replace documents
- Preserve dual-view result cache by document name
- Return small result objects describing what the UI should update
- Reuse existing pure helpers from `documents.session`

Keep out of scope:

- wx dialogs
- actual `TextCtrl` reads/writes
- worker threads
- message boxes

Why this should be first:

- It attacks the largest SRP issue without changing conversion or storage.
- It can be built incrementally behind existing `BrailleFrame` methods.
- It turns current GUI-heavy tests into smaller controller tests over time.
- It follows the already successful pattern in `documents.session`.

Suggested first slice:

- Extract `_open_document_by_name`, `_replace_document`, rename/delete cache
  updates, and window-title decision into a controller.
- Keep `BrailleFrame` responsible for applying the returned state to wx controls.
- Add focused tests for document switching, rename with dual-view cache, delete
  open document, and delete all.

### Priority 2: Extract Conversion Job Runner From `BrailleFrame`

Recommendation:

Move conversion job state and thread lifecycle into a small service such as
`client/conversion/jobs.py`.

Initial responsibilities:

- Assign job IDs
- Hold active worker state
- Start conversion on a worker thread
- Marshal success/failure back through callbacks
- Normalize `ConversionStageError` into a user-facing result object

Keep in `BrailleFrame`:

- Showing and closing `ConvertingDialog`
- Enabling/disabling wx controls
- Writing output text
- Showing message boxes

Why this matters:

- Conversion is reused by manual convert, single export, and export-all.
- Current behavior is controlled by several mutable frame fields:
  `_convert_on_success`, `_convert_on_error`, `_convert_update_output`,
  `_convert_show_success`, `_convert_job_id`, `_convert_thread`,
  `_convert_dialog_timer`.
- A job runner gives export flows a clear API and reduces callback coupling.

Suggested pattern:

- Use Command for `ConversionJobRequest`.
- Use Observer-style callbacks or a simple `on_complete(job_id, result)`.
- Keep wx-specific `wx.CallAfter` at the adapter edge or inject a scheduler
  function for tests.

### Priority 3: Split Dictionary UI Domain Logic Out Of `dialog.py`

Recommendation:

Create `client/dictionaries/entries.py` for dictionary entry model, CSV
load/save, entry type normalization, and entry validation.

Move from `dialog.py`:

- `DictionaryEntry`
- `ENTRY_TYPE_OPTIONS`, `ENTRY_TYPE_LABELS`, `DEFAULT_ENTRY_TYPE`
- `normalize_entry_type`
- `load_dictionary_entries`
- Unicode braille and Bopomofo validation helpers
- dictionary entry CSV save logic used by `SpeechSymbolsDialog`

Leave in `dialog.py`:

- wx dialog classes
- virtual list controls
- button layout
- focus and message box behavior

Why this matters:

- `dialog.py` is the second largest file and mixes persistence with wx.
- `DictionaryManagementDialog` already receives lifecycle callbacks, so the
  codebase is close to a Presenter pattern.
- Extracting entry logic gives future dictionary features a non-wx API.

### Priority 4: Break Conversion Service Into Pipeline Steps

Recommendation:

Keep `convert_text_with_alignment()` as the public facade, but move internal
steps into narrow modules or functions with explicit names.

Candidate modules:

- `conversion/segments.py`: inline math parsing and boundary spacing
- `conversion/plain_text.py`: dictionary application, language detection, table
  selection, plain text translation
- `conversion/wrapping.py`: merge, token cleanup, wrapping
- `conversion/output.py`: Unicode/ASCII output formatting

Why this matters:

- Conversion already has useful tests and explicit runtime injection.
- Splitting the internal pipeline makes it easier to add future output modes,
  language policies, or math delimiters without changing one large service.

Use Pipeline, not a framework:

- A simple sequence of pure functions is enough.
- Do not introduce a generic pipeline engine.
- Preserve `ConversionRequest` and `ConversionOutput`.

### Priority 5: Split Settings Panels Before Adding More Categories

Recommendation:

Do not urgently split `settings/dialogs.py` today. It is large but still coherent
because it contains one framework and three panels. Split it when the next
settings category is planned.

Suggested target:

- `settings/dialog_framework.py`: `SettingsDialog`, `SettingsPanel`,
  `MultiCategorySettingsDialog`, accessibility helper
- `settings/panels/translation.py`
- `settings/panels/translation_tables.py`
- `settings/panels/view.py`
- `settings/dialogs.py`: `DotExpressSettingsDialog` composition and public entry

Why this is lower priority:

- Recent settings refactor already improved discoverability.
- Current pain is mostly in `gui.py` and `dialog.py`.
- Splitting now would be structural churn unless a new settings category is
  imminent.

### Priority 6: Leave Server Refactor Low Priority

Recommendation:

Do not spend the next refactor cycle on `server/app/`.

Reason:

- `server/app/main.py`, `crud.py`, `database.py`, `models.py`, and `schemas.py`
  are small and already separated enough for the current initialization service.
- A service layer may be useful only when more endpoints or version policy rules
  appear.

## Recommended Execution Plan

### Phase 1: Document Controller

Goal:

Reduce `BrailleFrame` document-state responsibilities without changing UI.

Steps:

- Add controller tests first for open/select/rename/delete/delete-all.
- Introduce a controller with explicit state and result dataclasses.
- Route existing `BrailleFrame` document methods through the controller.
- Keep all wx dialogs and message boxes in `BrailleFrame`.
- Run `tests.test_document_session`, `tests.test_document_workspace`, and
  `tests.test_gui_document_flows`.

### Phase 2: Conversion Job Runner

Goal:

Separate conversion threading and job state from frame UI behavior.

Steps:

- Characterize current manual convert, export single, export all, stale job, and
  error paths.
- Extract a job runner with injected scheduler for `wx.CallAfter`.
- Keep UI busy state and dialogs in `BrailleFrame`.
- Run `tests.test_conversion_service`, `tests.test_gui_document_flows`, and
  adapter/runtime tests.

### Phase 3: Dictionary Entry Module

Goal:

Make dictionary entry persistence and validation reusable outside wx dialogs.

Steps:

- Move entry model and CSV helpers into `dictionaries/entries.py`.
- Update `SpeechSymbolsDialog` and `DictionaryManagementDialog` to consume the
  extracted functions.
- Add focused tests for entry validation and CSV roundtrip.
- Run dictionary manager, dictionary management dialog, and speech symbols tests.

### Phase 4: Conversion Pipeline Internal Split

Goal:

Keep conversion facade stable while making internal steps smaller.

Steps:

- Move inline math parsing first because it is the cleanest extraction.
- Move plain-text translation next, preserving language table selection tests.
- Move wrapping/output formatting last.
- Run full conversion, language detection, dual-view, and adapter tests.

## Test Strategy

Use characterization tests before each extraction. The current suite already has
good coverage for the risky areas:

- `tests.test_gui_document_flows`
- `tests.test_document_session`
- `tests.test_document_workspace`
- `tests.test_conversion_service`
- `tests.test_translation_runtime_provider`
- `tests.test_dictionary_management_dialog`
- `tests.test_speech_symbols_dialog`

For each refactor slice:

- Add focused non-wx tests for the new module first.
- Keep existing GUI flow tests passing as integration coverage.
- Avoid changing user-facing strings unless the task explicitly includes
  localization updates.
- Run from `client/` with targeted suites first, then broaden if the slice
  touches shared behavior.

## Non-Recommended Refactors For The Next Cycle

Do not introduce a dependency-injection container.

The current explicit runtime injection is enough. A container would add ceremony
without solving the immediate GUI responsibility problem.

Do not rewrite `BrailleFrame` into MVC all at once.

The frame is large, but broad replacement would be high risk. Extract one
workflow at a time and keep wx behavior stable.

Do not split every module by layer immediately.

Recent settings and adapter work shows that focused packages are useful when
they match real boundaries. Splitting small modules such as `server/app/crud.py`
or `documents/session.py` would reduce clarity.

Do not make conversion a generic plugin system yet.

The adapter boundary is ready for future backends. A plugin system should wait
until there are multiple real native backends or user-selectable translation
providers.

## Summary Recommendation

The next refactor should start with `BrailleFrame` responsibility extraction,
specifically a document workflow controller. This gives the largest maintainability
gain with the least architectural speculation. After that, extract conversion job
threading, then dictionary entry domain logic, then split the conversion pipeline
internals. This sequence follows the project's recent successful pattern: create
small boundaries around behavior that already exists, keep public behavior stable,
and use focused tests to protect each move.
