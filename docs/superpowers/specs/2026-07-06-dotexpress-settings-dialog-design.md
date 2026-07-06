# DotExpress Multi-Category Settings Dialog Design

Date: 2026-07-06

## Goal

Consolidate DotExpress's currently separate translation settings, translation tables settings, and view settings into a single multi-category settings dialog modeled after NVDA's `settingsDialogs.py`. This should fix the current issue where dialogs become too small when there are only a few items because they rely on `Fit()`, while also establishing an extensible settings framework.

The refactor must deliver the following user experience:

- The Translation menu keeps only one `Settings` entry.
- Opening it shows a single multi-category settings dialog with the title `DotExpress Settings: <current category>`.
- The dialog opens on the `Translation` category by default.
- The left-side category order is fixed as:
  1. Translation
  2. Translation Tables
  3. View
- Settings use a staged model; changes only take effect after clicking `Apply` or `OK`.
- The visible view controls are removed from the main window, but the existing font-size shortcut and mouse-wheel adjustment remain.

## Reference Source and Alignment Scope

This design references the following concepts and behaviors from `include/nvda/source/gui/settingsDialogs.py`:

- `SettingsDialog`
- `SettingsPanel`
- `MultiCategorySettingsDialog`
- `SpeechSettingsPanel`
- `SynthesizerSelectionDialog`
- `NVDASettingsDialog` behavior for updating the window title when switching categories

The main alignment targets are:

- The overall visual structure of a left-side category list with a right-side content area
- Fixed initial and minimum dialog sizes instead of sizing solely via `Fit()`
- A staged `OK / Cancel / Apply` commit flow
- `initialCategory` support
- Updating the window title when the current category changes
- `Ctrl+Tab` / `Ctrl+Shift+Tab` category cycling with wraparound
- A panel-level accessibility helper
- A single-instance multi-instance guard for the settings dialog
- A modeless dialog lifecycle so an existing instance can be raised and focused

The following are out of scope for this change:

- NVDA context help / `helpId` integration
- NVDA's full multi-instance exception flow
- NVDA-specific accessibility and context-help infrastructure

## User-Visible Changes

### 1. Translation Menu Changes

The Translation menu will replace multiple settings-related entries with a single entry:

- `Settings`

Other items such as `Dual View` are not part of this change unless their ordering needs minor adjustment due to the menu reorganization.

### 2. New Multi-Category Settings Dialog

Introduce a new user-facing settings dialog:

- Base dialog title: `DotExpress Settings`
- Category-specific title format: `DotExpress Settings: Translation`, `DotExpress Settings: Translation Tables`, `DotExpress Settings: View`

The left-side category order is fixed as:

1. Translation
2. Translation Tables
3. View

The dialog opens on `Translation` by default.

When focus is anywhere in the dialog, `Ctrl+Tab` selects the next category and
`Ctrl+Shift+Tab` selects the previous category, wrapping at both ends. This follows
NVDA's category-navigation behavior and does not replace normal arrow-key navigation
when focus is in the category list.

### 3. Remove View Controls from the Main Window

Remove the current View section from the main window, including:

- Font Size
- Braille Font
- Scheme / color scheme

The main window should return to focusing on the editor and output areas, without displaying these three settings controls directly.

### 4. Keep Main-Window Quick Adjustment Behavior

Although the visible View controls are removed, the existing keyboard shortcut and mouse-wheel font-size adjustment behavior remains. That means view settings will still have two modification paths:

- Settings dialog: staged; only takes effect on `Apply/OK`
- Main-window shortcut / mouse wheel: immediate effect

Both paths must ultimately update the same source of truth for view settings so the application does not drift into a split state.

## Architecture Design

### Add a Shared Settings Framework

Add a DotExpress-specific settings framework module at
`client/settings_dialogs.py`, containing the following classes. Keeping this
user-facing wxPython dialog beside `client/dialog.py` also ensures the existing
localization extraction script scans its `_()` strings.

#### `SettingsDialog`

Responsibilities:

- Provide the shared dialog structure
- Create a standard `OK / Cancel / Apply` button row
- Support resizable dialogs
- Support `INITIAL_SIZE` and `MIN_SIZE`
- Provide standard `on_ok`, `on_cancel`, and `on_apply` flows
- Provide close and destroy hooks that subclasses can use to clear single-instance state

This class does not handle a multi-category list; it only provides common settings-dialog behavior.

#### `SettingsPanel`

Responsibilities:

- Serve as the base class for each settings category page
- Provide a consistent GUI construction entry point such as `make_settings`
- Provide staged-model lifecycle methods:
  - `on_panel_activated`
  - `on_panel_deactivated`
  - `on_save`
  - `on_discard`
  - optionally `is_valid`
- Provide a panel title and panel description for UI and accessibility helper usage

This class must not write directly to config or directly mutate the main window's final state. Its only responsibility is to synchronize control values into the staged model.

#### `MultiCategorySettingsDialog`

Responsibilities:

- Create the left-side categories list and the right-side panel container
- Support `initial_category`
- Lazily create panel instances per category
- Manage panel switching and `Apply`, `OK`, and `Cancel`
- Provide a scrollable right-side content area
- Allow subclasses to override post-category-switch behavior, such as updating the dialog title

This class implements the reusable multi-category settings framework but is not tied directly to DotExpress-specific settings content.

#### `DotExpressSettingsDialog`

Responsibilities:

- Provide the actual user-facing DotExpress settings UI for this change
- Define category classes in this order:
  1. `TranslationSettingsPanel`
  2. `TranslationTablesPanel`
  3. `ViewSettingsPanel`
- Open on `TranslationSettingsPanel` by default
- Update the title to `DotExpress Settings: <category name>` when switching categories
- Hold the staged settings snapshot
- Notify the main window to apply committed settings
- Own the single-instance guard; the reusable base classes must not globally prevent
  other settings-dialog subclasses from opening

### Dialog Lifecycle

`DotExpressSettingsDialog` is modeless and is opened with `Show()`. The main window
retains the live instance until the dialog is destroyed. This is required for the
specified bring-to-front behavior; a modal `ShowModal()` flow would block the main
window's menu and make the guard ineffective for the normal entry point.

Closing the dialog through `Cancel`, `OK`, or the window close button must destroy
the window and clear the retained reference. The window close button has the same
discard semantics as `Cancel`.

## Visual and Layout Design

### Dialog Size

To avoid the current `Fit()`-driven undersized dialogs, this dialog uses fixed initial and minimum sizes.

Recommended values:

- `INITIAL_SIZE = (720, 440)`
- `MIN_SIZE = (520, 300)`

Reasons:

- More stable than the current small dialogs
- Large enough for the form layout in the right-side panels
- Not as heavy as NVDA's full settings window

### Layout Structure

The overall structure follows NVDA:

- Top: categories label
- Left: category list
- Right: content panel container
- Bottom: `OK / Cancel / Apply`

Recommended initial visual proportions:

- Left category column initial width around `150`
- Right content area takes the remaining primary space
- On resize, use an NVDA-like grow ratio of left 1 / right 3
- Initial sizing comes from explicit dimensions, not from grow proportion

### Right-Side Content Container

Use a scrollable panel for the right-side content area to ensure:

- Categories with more content can scroll vertically
- Categories with fewer controls do not shrink the whole dialog
- Future additions do not require redesigning the overall sizing strategy

## Accessibility Helper Design

Accessibility helper support is included in this change.

### Purpose

- Make it clearer to assistive technologies that the current right-side content is a settings page
- Bind the current category's description and semantics to the active panel

### Design

Implement a corresponding accessibility helper for `SettingsPanel`, following the concept of NVDA's `SettingsPanelAccessible`:

- The panel role should map to property-page semantics
- The panel description should come from each panel's `panel_description`
- When the active panel changes, the new panel must expose the correct accessibility metadata

### User-Facing Descriptions per Panel

- `Translation`: translation output mode, width, and dictionary options
- `Translation Tables`: translation table mappings for different languages
- `View`: font, font size, and color scheme for the main window input/output areas

These descriptions do not need to be fully visible on screen, but they should be available to the accessibility helper.

## Multi-Instance Guard Design

Multi-instance guard support is included in this change.

### Goal

Allow only one `DotExpressSettingsDialog` at a time to avoid:

- Multiple settings dialogs editing the same staged state concurrently
- State overwrites caused by different `Apply/OK` ordering
- Desynchronization between main-window state and dialog-staged values

### Behavior

When the user attempts to open DotExpress Settings again:

- If an instance already exists, do not create a new window
- Bring the existing window to the front instead
- If `initialCategory` is used in the future, optionally switch to the requested category at the same time

Even though the current UI exposes only a single entry point, the underlying implementation should still preserve `initialCategory` support for future extensibility and internal routing.

The guard belongs to `DotExpressSettingsDialog`, not to `SettingsDialog` globally.
If the retained instance is still alive, the open helper must optionally select the
requested category, restore the window if iconized, then call `Raise()` and
`SetFocus()`. A stale or destroyed reference must be cleared before creating a new
dialog.

## Panel Design

### `TranslationSettingsPanel`

Title: `Translation`

Source: replaces the current `TranslationSettingsDialog`

Content:

- Braille Type
- Width
- Dictionary

Responsibilities:

- Display staged translation settings
- When the user changes controls inside the panel, update only the panel-local control state
- On `on_save`, write values back to the translation-settings section of the staged model
- Validate width and dictionary selection

Must not:

- Directly update the main window's `translation_settings`
- Directly write config

### `TranslationTablesPanel`

Title: `Translation Tables`

Source: replaces the current `TranslationTableDialog`

Content:

- default
- en
- zh
- ja
- math

Responsibilities:

- Display staged translation-table mappings
- Preserve the existing per-language table filtering behavior
- On `on_save`, write current selections back into the staged translation-tables model
- Require valid selections for `default` and `math`; `en`, `zh`, and `ja` may retain
  the existing `None selected` empty value

Must not:

- Directly write config
- Directly refresh the main window

### `ViewSettingsPanel`

Title: `View`

Source: absorbs the current View section from the main window

Content:

- Font Size
- Braille Font
- Scheme / color scheme

Responsibilities:

- Display staged view settings
- On `on_save`, write values back into the staged view-settings model
- Validate that font size remains within the existing supported range
- Reuse the existing normalization logic for braille font and color scheme values

Notes:

- Changing values inside this panel must not immediately affect the main window
- Only after `Apply/OK` should the outer dialog instruct the main window to apply the changes

## Data Flow and State Management

### Staged Model

When `DotExpressSettingsDialog` opens, it should create a staged settings snapshot. At minimum, it should contain:

- `translation_settings`
  - `output_mode`
  - `width`
  - `selected_dictionary`
- `translation_tables`
  - `default`
  - `en`
  - `zh`
  - `ja`
  - `math`
- `view_settings`
  - `font_size`
  - `braille_font`
  - `scheme`

This staged snapshot must be decoupled from the current main-window state so that `Cancel` can discard changes safely.

The snapshot is copied from normalized application state, not directly from mutable
global dictionaries. In particular, translation-table mappings must be copied so
panel edits cannot mutate `language_map_translate_table` before a commit.

### Apply / OK Flow

1. Run `is_valid` on all instantiated panels
2. Run `on_save` on all instantiated panels to write control values back into the staged snapshot
3. Let `DotExpressSettingsDialog` call a single apply entry point exposed by the main window
4. The main window then performs the full commit in one place:
   - update translation settings
   - update translation tables
   - update view settings
   - apply visual changes to the main window
   - persist settings to config/storage

`OK` closes the dialog after a successful commit. `Apply` keeps the dialog open.

After a successful `Apply`, the committed values become the dialog's new baseline:

- refresh the staged snapshot from the normalized values returned by the main-window
  commit entry point
- synchronize instantiated panels with that baseline
- clear panel dirty state

Therefore, a later `Cancel` discards only edits made after the most recent successful
`Apply`; it does not undo settings that were already applied.

### Cancel Flow

1. Do not commit the staged snapshot
2. Call each panel's `on_discard` if needed
3. Close the dialog

Because the staged model is separated from the main window, `Cancel` does not require extra rollback logic.

The dialog must collect and validate all instantiated panel values before invoking
the main-window commit entry point. A validation failure must not partially update
the staged snapshot used as the last successfully applied baseline.

## Main Window Integration Design

### Main-Window UI to Remove

Remove the current View section and its controls from the `BrailleFrame` main window:

- font size spin control
- braille font choice
- color scheme controls

The main-window layout must then be adjusted so the editor and output areas naturally fill the freed vertical and horizontal space.

The removed controls must no longer be used as hidden state. Introduce an explicit
normalized view-settings value in `BrailleFrame`; rendering and shortcut handlers
must read and update that value.

### Main-Window Capabilities to Keep

Keep the existing font-size keyboard shortcut and mouse-wheel adjustment behavior. These remain immediate-effect interactions and coexist with the staged model used by the settings dialog.

That means the main window still needs the ability to:

- directly apply a view font-size change
- synchronize direct changes back to persisted settings

The existing section-navigation order must also remove the deleted View section, so
section shortcuts cycle through Document List, Source Text, and Braille Result only.

### Main-Window Apply Entry Point

The main window should expose a single method for `DotExpressSettingsDialog` to use, for example:

- `apply_settings_from_dialog(...)`

This method should centrally handle:

- writing translation settings
- writing translation tables
- writing view settings
- refreshing the visuals
- persisting the settings

This avoids coupling individual panels directly to main-window internals.

The commit method returns the normalized settings that were actually accepted. This
allows the dialog to establish an accurate post-Apply baseline.

### Changes While the Modeless Dialog Is Open

Main-window font-size shortcuts and mouse-wheel changes remain immediate. When one
occurs while the settings dialog is open:

- update and persist the main window's explicit view-settings value
- if the View panel has not modified its font-size field, synchronize the new value
  into the staged snapshot and control
- if that field is dirty, preserve the user's draft; a later `Apply/OK`
  intentionally replaces the immediate value with the draft

Scheme and braille-font values have no retained main-window quick-adjust path, so
they do not require this conflict rule.

## Title Update Behavior

The `MultiCategorySettingsDialog` base class must not force dialog-title updates.

`DotExpressSettingsDialog` must update its title when the active category changes, following the behavior of NVDA's `NVDASettingsDialog`:

- when `Translation` is active: `DotExpress Settings: Translation`
- when `Translation Tables` is active: `DotExpress Settings: Translation Tables`
- when `View` is active: `DotExpress Settings: View`

This behavior must apply to:

- the initial open state
- switching categories through the left-side category list
- reusing an existing dialog instance and switching category in the future, if that path is enabled

## Error Handling

### Validation Errors

If a panel contains invalid settings:

- `Apply/OK` must stop
- no staged model changes may be committed to the main window
- focus should return as closely as possible to the failing panel and related control
- show an error dialog when necessary

### Reopening the Settings Dialog

If a settings dialog instance already exists:

- do not show an error
- bring the existing window to the front and focus it

The window close button follows `Cancel` and must never apply pending changes.

### Panels Not Yet Instantiated

Because panels may be lazily created:

- `Apply/OK` only actively processes instantiated panels plus the staged snapshot
- panels never visited during the session retain their opening snapshot values
- those values must still be included in the final commit

## Test Strategy

### Unit Tests

Add or update tests to cover at least:

- title/category-switching logic in the new settings framework base classes
- multi-instance guard behavior
- staged-model differences across `Apply/OK/Cancel`
- value read/write and validation for `TranslationSettingsPanel`
- initial values and option synchronization for `TranslationTablesPanel`
- value read/write and validation for `ViewSettingsPanel`
- whether the main-window apply entry point receives the expected staged data
- whether the Translation menu keeps only a single settings entry
- category cycling in both directions, including wraparound

### GUI-Level Regression Tests

Update existing tests that depend on:

- `TranslationSettingsDialog`
- `TranslationTableDialog`

If those dialogs are fully replaced, the related tests should be rewritten to validate the new `DotExpressSettingsDialog` and corresponding panel behavior instead.

### Manual Verification

At minimum, verify the following flows:

1. Open `Settings` from the Translation menu
2. Confirm the dialog opens on `Translation`
3. Switch to `Translation Tables` and `View` and confirm the title changes accordingly
4. Modify any panel and click `Cancel`; confirm the main window and config remain unchanged
5. Modify `View` and click `Apply`; confirm the main-window font/scheme updates
6. Change font size using the main-window shortcut or mouse wheel; confirm the next dialog open reflects the latest value
7. With the dialog open and its View font-size field unchanged, use a retained
   main-window shortcut path and confirm the staged value synchronizes
8. Make the View font-size field dirty, perform a main-window quick adjustment, and
   confirm the draft is preserved until `Apply/OK`
9. Try opening the settings dialog repeatedly; confirm only one window exists and it is focused

## Suggested Implementation Breakdown

1. Build the settings framework base classes
2. Build `DotExpressSettingsDialog` and the three panels
3. Move the old translation-settings and translation-tables UI logic into panels
4. Move the main-window view controls into `ViewSettingsPanel`
5. Remove the View section from the main window and wire in the new dialog entry point
6. Connect the staged model and apply/commit path
7. Add the accessibility helper and multi-instance guard
8. Update tests

## Non-Goals

This change does not include:

- building a full standalone Settings menu system
- changing Dual View behavior itself
- adding new settings categories such as dictionary management or export settings
- converting every main-window shortcut interaction into the staged model

## Decision Summary

- Adopt DotExpress-specific `SettingsDialog / SettingsPanel / MultiCategorySettingsDialog`
- Use a single entry point: `Translation -> Settings`
- Use dialog titles in the format `DotExpress Settings: <category name>`
- Keep the left-side category order as Translation, Translation Tables, View
- Remove visible View controls from the main window
- Keep the main-window font-size shortcut / mouse-wheel behavior
- Add an accessibility helper
- Add a multi-instance guard
- Use a modeless dialog, with the window close button behaving like `Cancel`
- Use a staged model so settings only commit on `Apply/OK`
- Treat a successful `Apply` as the new Cancel baseline
