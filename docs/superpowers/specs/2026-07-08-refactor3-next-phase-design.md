# DotExpress Refactor 3 Next-Phase Design

Date: 2026-07-08

## Background

`docs/refactor/refactor3.md` confirms that the previous refactor outcomes are already in place:

- `DocumentController` already exists
- the dictionary entry domain has already been moved to `client/dictionaries/entries.py`
- the conversion job runner has already been moved to `client/conversion/jobs.py`
- `client/conversion/service.py` has already become a thinner facade

Because of that, the focus of the next phase is no longer to repeat the same kind of extraction into more modules. The goal is to converge the boundaries that already exist into real single sources of truth and stable extension points, reducing the remaining state-sync and workflow-coordination risk inside `BrailleFrame`.

## Superpower Brainstorming Conclusions

This round first clarified three questions, then used those answers to define the scope of the spec.

### Question 1: What is the biggest maintenance risk right now?

The main problem is not just that a file is large. The bigger issue is that `client/gui.py` still stores multiple mirrored pieces of state at the same time:

- document state inside the frame
- document state inside `DocumentController`
- per-job UI policy for the conversion workflow
- scattered import/export format rules

The real high-risk point is that these states are distributed and still require manual synchronization.

### Question 2: What kind of refactor should be prioritized next?

The next phase should prioritize boundary convergence, not another round of broad package splitting.

Reasons:

1. `DocumentController` already exists, so the highest-value next step is to make it the single source of truth for document state.
2. The conversion thread runner already exists, but UI completion policy is still stored in frame-level mutable fields, so the upper-layer workflow is not yet converged.
3. Import/export format logic is still scattered across GUI and workspace branching logic, which is a clear OCP gap.

### Question 3: What should not be done in this phase?

This phase should not:

- redesign the wx UI
- rewrite the app into full MVC / MVVM
- introduce a DI container
- extract another generic pipeline framework
- prioritize server refactoring
- change user-visible strings, menu ordering, or import/export behavior

## Goals

Focus the next-phase refactor on three verifiable goals:

1. Make `DocumentController` the single source of truth for document state
2. Converge conversion UI workflow state and remove frame-global mutable policy fields
3. Introduce a document format descriptor / registry to centralize import/export format knowledge

After these three are complete, `BrailleFrame` remains the wx outer layer, but it will no longer be responsible for storing and coordinating too much domain state.

## Scope

This change includes:

- expanding the read-only state surface and state-transition API in `client/documents/controller.py`
- updating `client/gui.py` so document-related flows read and write through the controller first
- adding a conversion UI workflow state object so per-job completion policy travels with the request/result
- updating the collaboration boundary between `client/gui.py` and `client/conversion/jobs.py`
- adding `client/documents/formats.py` or an equivalent module to centralize the format descriptor / registry
- updating import/export flows to read from the registry
- adding corresponding focused tests and existing GUI flow regression coverage

This change does not include:

- settings dialog panel splitting
- splitting the remaining UI classes in `client/dialog.py`
- a server-side service layer
- adding any new document format
- changing user-visible import/export strings

## Requirement Confirmation

### Requirement 1: `DocumentController` must be the only source of document state

`BrailleFrame` should no longer hold a mutable copy of document state that duplicates the controller.

Specific requirements:

- the document list should be owned by the controller
- the selected/open document name should be owned by the controller
- the dual-view cache should be owned by the controller, or at minimum the controller should be the only authoritative update path
- if `BrailleFrame.documents` is temporarily kept, it must become a delegating property rather than independent state
- `_sync_document_controller_state()` should be removed, or reduced to a one-way compatibility shim that can later be deleted

### Requirement 2: Conversion workflow policy must become per-job state

Right now, manual convert, single export, and batch export share the same frame fields to carry completion policy. That creates elevated risk when jobs become stale or flows interleave.

Specific requirements:

- the conversion request must carry the completion UI policy
- success / error / output update / success-message behavior must no longer depend on frame-global mutable fields
- stale-job protection must still be maintained by the job runner
- `BrailleFrame` still owns wx dialogs, message boxes, and control updates, and wx objects must not be passed into non-wx domain modules

### Requirement 3: Document format knowledge must be centrally managed

Adding a format should not require simultaneous changes to GUI, workspace, wildcard, and suffix branching logic.

Specific requirements:

- define a descriptor that consistently describes `key`, `extension`, `wildcard_label`, `loader`, `writer`, `requires_braille`, and whether the format supports import/export
- the existing `IMPORT_LOADERS` should be produced from the registry, or stay aligned with the registry as a single source
- prioritize descriptorizing the existing `dep` and `brl` export flows
- do not add a new format, and do not change existing labels or file extensions

## Design Decisions

### Decision 1: Continue the Application Controller direction instead of returning to frame-centric state

`DocumentController` is already the closest thing to a stable boundary. The next step is not to move more state back into `BrailleFrame`, but to keep the frame limited to:

- receiving events
- updating wx controls
- showing dialogs / message boxes
- calling controller and use-case helpers

### Decision 2: Use small State Objects to represent conversion completion policy

Do not introduce a heavier workflow engine.

Small dataclasses are sufficient, for example:

- `ConversionUiRequest`
- `ConversionCompletionPolicy`
- `ConversionWorkflowResult`

These types describe workflow intent only and do not depend on wx directly.

### Decision 3: Use Descriptor / Registry to centralize document format rules

This layer does not aim to become a plugin system. It only creates a consistent internal description of formats inside the repo.

The registry should provide:

- importable formats
- exportable formats
- file-dialog wildcard text
- format-key to loader / writer lookup
- export policy for formats that require braille

## Option Comparison

### A. Only split more helper methods out of `gui.py`

Pros:

- small changes

Cons:

- state synchronization problems remain
- the OCP gap remains
- this only breaks large methods into smaller ones without improving boundaries

Rejected.

### B. Converge the existing controller / job runner / registry boundaries

Pros:

- directly solves the single-source-of-truth problem
- preserves the current wx UI and public behavior
- each step can be verified with focused unit tests

Cons:

- existing tests and compatibility layers need careful handling

Accepted.

### C. Rewrite the entire client into full MVC / MVVM at once

Pros:

- in theory, the architecture becomes more uniform

Cons:

- the change surface is too large
- it cannot preserve the low-risk incremental refactor approach
- it is disproportionate to the current project size

Rejected.

## Target Structure

```text
client/
├── conversion/
│   ├── jobs.py
│   └── ...
├── documents/
│   ├── controller.py
│   ├── formats.py
│   ├── session.py
│   └── workspace.py
└── gui.py
```

## Module Responsibilities

### `client/documents/controller.py`

Responsibilities:

- store documents, selected/open names, and dual-view cache
- provide document read-only snapshots / accessors
- execute state transitions such as rename / replace / delete / open

Should not be responsible for:

- wx controls
- message boxes
- filesystem dialogs

### `client/conversion/jobs.py`

Responsibilities:

- assign job IDs
- run worker threads
- maintain stale-job protection
- return workflow results associated with the request

Should not be responsible for:

- wx dialogs
- `TextCtrl` updates
- success or error message display

### `client/documents/formats.py`

Responsibilities:

- centrally define document format descriptors
- provide import/export format registry behavior
- provide loader / writer / wildcard / extension lookups

Should not be responsible for:

- actually showing the file dialog
- changing user-visible labels

## Migration Strategy

### Step 1: Add focused characterization tests first

Lock down:

- state transitions for document rename/delete/open
- conversion stale-job handling and completion policy
- import/export format lookup and wildcard assembly

### Step 2: Make GUI read from the controller instead of maintaining mirrored state

First change the read paths to use controller accessors, then gradually delete frame-level mutable document fields.

### Step 3: Attach conversion policy to request/result

First add the data types and adapter glue, then remove the corresponding frame fields.

### Step 4: Converge format branches into the registry

Handle `dep` and `brl` export first, then connect import loaders and wildcard generation to the same source.

## Acceptance Criteria

### Document state

- open / select / rename / delete / delete-all behavior remains unchanged
- the dual-view cache still tracks correctly after rename/delete
- `BrailleFrame` no longer stores a document-state copy that requires bidirectional synchronization with the controller

### Conversion workflow

- manual convert behavior remains unchanged
- single export and batch export do not accidentally reuse manual success policy
- stale job results cannot be applied to the wrong workflow policy

### Format registry

- `dep` / `brl` export behavior remains unchanged
- import wildcard/filter and loader mapping come from the same source
- adding a format requires fewer modification points than today

## Test Strategy

Core regression set:

- `python3 -m unittest tests.test_document_controller -v`
- `python3 -m unittest tests.test_document_session tests.test_document_workspace tests.test_gui_document_flows -v`
- `python3 -m unittest tests.test_conversion_jobs tests.test_conversion_service -v`
- `python3 -m unittest tests.test_import_dialog tests.test_gui_document_flows -v`

If optional importer dependencies are missing, any unrun items must be explicitly recorded in implementation notes.

## Implementation Decisions

The implementation should use these decisions so the plan does not leave boundary choices to the worker:

1. The dual-view cache should live in `DocumentController`. `BrailleFrame` may expose a temporary delegating property for compatibility, but it should not own a separate cache.
2. Conversion policy types should stay in `client/conversion/jobs.py` for this phase. A separate `workflow.py` module can be considered later only if job orchestration grows beyond this use case.
3. The format registry should provide file-dialog wildcard helpers as well as descriptor lists, because GUI import/export flows already need a stable wildcard assembly boundary.
