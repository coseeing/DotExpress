# DotExpress Settings Package Refactor Design

Date: 2026-07-06

## Goal

Consolidate DotExpress's settings-related modules into a single `client/settings/`
package so that settings data models, persistence helpers, staged snapshot state,
and settings dialog UI live under one clear namespace.

This refactor should improve discoverability and make future settings categories
easier to add, without changing user-visible settings behavior.

## Scope

This change includes:

- Moving view settings logic from `client/view_settings.py` into `client/settings/view.py`
- Moving translation settings logic from `client/translation/settings.py` into `client/settings/translation.py`
- Introducing a dedicated `client/settings/translation_tables.py` module for translation-table settings persistence helpers
- Moving `client/settings_state.py` into `client/settings/state.py`
- Moving `client/settings_dialogs.py` into `client/settings/dialogs.py`
- Updating application and test imports to use the new package paths
- Removing the old module files after every internal consumer has migrated

This change does not include:

- Changing the settings dialog UX, category order, or staged apply behavior
- Redesigning `config.py`
- Renaming user-facing strings
- Splitting the new package into deeper layers such as `constants.py` or `persistence.py`

## Current Problems

Settings code is currently split across unrelated top-level locations:

- `client/view_settings.py`
- `client/settings_state.py`
- `client/settings_dialogs.py`
- `client/translation/settings.py`
- `client/config.py`

This creates four practical issues:

1. Settings responsibilities are discoverable only by prior project knowledge.
2. The translation settings module is grouped by feature area, while view/state/dialog modules are grouped by filename history.
3. `gui.py` imports settings concerns from multiple unrelated paths.
4. Future settings additions are likely to repeat the same scattered structure.

## Evaluated Approaches

### A. Keep Current Layout

Continue adding settings logic beside whichever feature first needs it.

This avoids import churn but preserves the current fragmented structure.

### B. Introduce a Flat `client/settings/` Package

Move all settings-related modules into one package with focused filenames:

- `view.py`
- `translation.py`
- `translation_tables.py`
- `state.py`
- `dialogs.py`

This creates a single namespace without over-partitioning the codebase.

### C. Introduce a Deeper Layered Package

Move settings into `client/settings/` and immediately split further into:

- `models/`
- `ui/`
- `persistence/`
- `constants/`

This is structurally clean, but current module count and size do not justify the
extra navigation cost yet.

## Decision

Use approach B.

Approach B captures the main value of the refactor: one obvious home for settings
code. It avoids the premature fragmentation of approach C while still leaving
clear boundaries for a future deeper split if `dialogs.py` or persistence helpers
grow substantially.

## Target Structure

```text
client/
├── settings/
│   ├── __init__.py
│   ├── dialogs.py
│   ├── state.py
│   ├── translation.py
│   ├── translation_tables.py
│   └── view.py
├── config.py
└── gui.py
```

## Module Responsibilities

### `client/settings/view.py`

Responsibilities:

- Define `ViewSettings`
- Define view-setting constants and valid keys
- Normalize view settings values
- Load view settings from `config.py`
- Save view settings through `config.py`

This module remains free of wx UI code.

### `client/settings/translation.py`

Responsibilities:

- Define `TranslationSettings`
- Normalize translation settings values
- Load translation settings from `config.py`
- Save translation settings through `config.py`

This module remains the authoritative home for translation settings data and persistence.

### `client/settings/translation_tables.py`

Responsibilities:

- Provide `load_translation_tables()` and `save_translation_tables()` helpers
- Delegate storage and the existing default merge behavior to
  `config.get_translation_tables()` and `config.set_translation_tables()`
- Return and persist copied mappings so callers do not share mutable input objects
- Keep translation-table persistence separate from the wx UI layer

This module should not own table option discovery from liblouis. UI option loading
still belongs in the dialog layer because it depends on presentation and runtime data.

This refactor does not introduce a separate translation-table normalization step.
The settings dialog already validates required selections, while `config.py` already
filters persisted key/value types and merges missing entries with
`DEFAULT_TRANSLATION_TABLES` when loading. Adding another normalization policy would
change behavior rather than reorganize it.

### `client/settings/state.py`

Responsibilities:

- Define `DotExpressSettingsSnapshot`
- Keep staged settings state construction and copy/update helpers together

This module depends on settings data models, not on wx UI.

### `client/settings/dialogs.py`

Responsibilities:

- Define the reusable settings dialog framework classes
- Define DotExpress settings panels
- Define `DotExpressSettingsDialog`
- Coordinate staged settings editing through `DotExpressSettingsSnapshot`

This module is the only wx-heavy settings module inside the package.

## Import Boundaries

The intended dependency direction is:

- `settings/view.py`, `settings/translation.py`, `settings/translation_tables.py`
  may depend on `config.py`
- `settings/state.py` may depend on settings model modules
- `settings/dialogs.py` may depend on `settings/state.py` and the settings model modules
- `gui.py` may depend on the `settings` package

The reverse direction is not allowed:

- settings model or persistence modules must not import `dialogs.py`
- `config.py` must not import the `settings` package

This keeps wx UI as the outermost layer.

## Public Package Surface

`client/settings/__init__.py` should re-export the non-UI settings APIs that are
imported widely by the application and tests:

- `DotExpressSettingsSnapshot`
- `TranslationSettings`
- `ViewSettings`
- `load_translation_settings`
- `save_translation_settings`
- `normalize_translation_settings`
- `load_translation_tables`
- `save_translation_tables`
- `load_view_settings`
- `save_view_settings`
- `normalize_view_settings`

The package root must not import `settings/dialogs.py`. Importing any submodule first
executes `settings/__init__.py`; re-exporting dialog classes there would make
non-UI imports such as `settings.translation` require wx. UI consumers must import
`DotExpressSettingsDialog`, panels, and dialog framework classes explicitly from
`settings.dialogs`.

Direct submodule imports remain acceptable when a caller needs only one concern.
The non-UI re-exports give the package an obvious entry point without coupling all
settings code to wx.

## Migration Strategy

### Step 1. Create the Package and Move Modules

Create `client/settings/` and move the current top-level settings modules into it.
Delete the old `client/view_settings.py`, `client/settings_state.py`,
`client/settings_dialogs.py`, and `client/translation/settings.py` files as part of
the moves; do not leave compatibility shims.

### Step 2. Separate Translation-Table Persistence

Move translation-table settings read/write helpers out of `gui.py` call sites and
into `settings/translation_tables.py`.

`gui.py` should stop calling `config.get_translation_tables()` and
`config.set_translation_tables()` directly. Module initialization should call
`load_translation_tables()`, and settings apply should call
`save_translation_tables()`.

### Step 3. Update Application Imports

Update imports in `gui.py` and any other touched application modules to reference
the new package paths.

### Step 4. Update Tests

Update test imports in:

- `client/tests/test_view_settings.py`
- `client/tests/test_settings_state.py`
- `client/tests/test_settings_dialogs.py`
- `client/tests/test_gui_document_flows.py`
- `client/tests/test_translation_settings.py`
- `client/tests/test_conversion_service.py`
- `client/tests/test_dialog_display.py`

`test_conversion_service.py` must read `settings/dialogs.py` instead of the removed
top-level dialog module. `test_dialog_display.py` must stub or clear the new
`settings` and `settings.translation` module paths used during isolated imports.

Add focused tests for `settings/translation_tables.py` that verify load/save
delegation and copied mapping behavior. Additional tests should be updated if import
failures reveal other settings consumers.

### Step 5. Keep Behavior Stable

The refactor must preserve:

- Current settings dialog behavior
- Current config file keys and persistence behavior
- Current view normalization behavior
- Current translation settings normalization behavior
- Current translation-table save/apply flow

## Error Handling and Compatibility

This is an internal refactor, so backward compatibility for old import paths is not required.

The repository appears to use these modules internally rather than as a published
library. Keeping temporary compatibility shims would extend the migration surface
without user benefit.

If a moved module exposes behavior relied on by tests, tests should be updated to
the new import path rather than relying on alias modules.

## Testing Plan

At minimum, run focused client tests covering settings modules and the settings dialog:

- `python3 -m unittest tests.test_view_settings -v`
- `python3 -m unittest tests.test_settings_state -v`
- `python3 -m unittest tests.test_settings_dialogs -v`
- `python3 -m unittest tests.test_translation_settings -v`
- `python3 -m unittest tests.test_translation_tables -v`
- `python3 -m unittest tests.test_gui_document_flows -v`
- `python3 -m unittest tests.test_conversion_service -v`
- `python3 -m unittest tests.test_dialog_display -v`

After focused tests pass, run discovery from `client/`:

- `python3 -m unittest discover -s tests -v`

Run these from `client/`, consistent with repository guidance.

## Future Extension Path

If settings code grows further, this package can later evolve toward approach C by:

- splitting `dialogs.py` into UI framework vs DotExpress-specific panels
- splitting persistence helpers from settings data definitions
- extracting shared constants where they become cross-module concerns

That future split should be triggered by concrete module growth, not performed preemptively in this refactor.
