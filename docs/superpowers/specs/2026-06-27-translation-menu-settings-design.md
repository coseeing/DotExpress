# Translation Menu Settings Design

## Context

The current client places translation controls in a visible `Conversion` row near the top of the main window. That row currently owns six controls: translation tables, braille type, width, dictionary selection, dictionary actions, and convert.

The next-stage requirement is to remove that row so the editor area can expand, and move translation entry points into an `Alt`-reachable top-level menu. The existing `TranslationTableDialog` already uses a modal `OK/Cancel` workflow, so the new translation settings flow should follow that pattern instead of trying to encode width directly in menu items.

This design is constrained by four decisions already confirmed during brainstorming:

- The top-level `Translation` menu contains exactly four items: `Convert`, `Translation Settings...`, `Translation Tables Setting...`, and `Dictionary Management...`
- `Translation Settings...` applies changes only when the user presses `OK`
- `Dictionary Management...` is a separate dialog with its own dictionary list and management actions
- Choosing `Edit` from `Dictionary Management...` closes that dialog and opens the existing dictionary-entry editor, and returning from the editor leaves the user at the main window

## Goals / Non-Goals

**Goals:**

- Remove the visible `Conversion` row from the main window
- Add a top-level `Translation` menu with the four confirmed items
- Introduce a modal `Translation Settings...` dialog for braille type, width, and dictionary selection only
- Preserve the existing `Translation Tables Setting...` dialog workflow
- Add a separate `Dictionary Management...` dialog for dictionary lifecycle operations
- Preserve `Ctrl+Enter` as a direct conversion shortcut
- Update `F6` / `Shift+F6` section navigation so it only cycles through visible main-window sections
- Keep the refactor pragmatic and avoid adding architecture that the feature does not need

**Non-Goals:**

- Do not redesign translation logic in `client/conversion/service.py`
- Do not merge translation-table settings into the new translation settings dialog
- Do not mix dictionary file management semantics into the translation settings dialog
- Do not change dictionary CSV format, translation-table persistence format, or conversion output formats
- Do not introduce MVP, MVVM, command-class hierarchies, or other large UI abstractions

## Decisions

### 1. Use a top-level `Translation` menu with four direct commands

The menu will contain:

- `Convert`
- `Translation Settings...`
- `Translation Tables Setting...`
- `Dictionary Management...`

This keeps the menu compact and keyboard-friendly. Width is not a good fit for inline menu items, and dictionary management is clearer as its own workflow instead of being mixed into translation settings.

Alternative considered: moving all six existing controls into nested menu items. Rejected because it would make width editing, dictionary selection, and action discovery harder.

### 2. Keep `Convert` as a first-level action

`Convert` remains a direct command in the `Translation` menu and continues to be available through `Ctrl+Enter` from the source editor.

This preserves the high-frequency path for conversion and avoids forcing users to open a settings dialog for a command they use often.

Alternative considered: placing convert inside a submenu or inside the settings dialog. Rejected because execution is an action, not a setting.

### 3. Model `Translation Settings...` after the existing translation-table dialog

`Translation Settings...` will be a modal dialog with `OK` and `Cancel`. It stages three values:

- braille output type
- conversion width
- selected dictionary

These values are loaded from current runtime/config state when the dialog opens. They are only applied back to the application when the user presses `OK`.

Alternative considered: reusing the existing main-window controls and keeping per-control immediate persistence. Rejected because it conflicts with the confirmed `OK`-to-apply behavior.

### 4. Move dictionary lifecycle operations into a separate management dialog

`Dictionary Management...` will open a dedicated dialog for managing dictionaries. The dialog will show the existing dictionaries in a list view and place the management actions below the list:

- `Add`
- `Delete`
- `Rename`
- `Edit`
- `Import`
- `Export`

These actions remain immediate dictionary-management operations, which is now consistent because they live in a management dialog rather than inside an `OK/Cancel` settings dialog.

Alternative considered: keeping dictionary actions inside `Translation Settings...`. Rejected because it mixes staged settings semantics with immediate file mutations and makes `Cancel` behavior harder to understand.

### 5. Reuse the existing translation-table dialog

`Translation > Translation Tables Setting...` will open the existing `TranslationTableDialog`. Its behavior remains unchanged: selections are staged in the dialog and only committed on `OK`.

Alternative considered: merging translation-table settings into `Translation Settings...`. Rejected because the table dialog already works and handles a separate concern with higher complexity.

### 6. Close dictionary management before opening the dictionary-entry editor

When the user chooses `Edit` in `Dictionary Management...`, the application will close the management dialog and then open the existing dictionary-entry editor dialog. When the editor closes, the workflow ends at the main window rather than reopening dictionary management automatically.

This keeps the flow simple and avoids building return-path logic that may conflict with other ways of opening the dictionary-entry editor.

Alternative considered: reopening `Dictionary Management...` automatically after editing finishes. Rejected because it adds state-restoration complexity with limited user benefit.

### 7. Remove `Conversion` from main-window section navigation

Once the visible `Conversion` row is removed, `F6` / `Shift+F6` should cycle only through the visible sections:

- `Document List`
- `View`
- `Source Text`
- `Braille Result`

The menu bar remains reachable through native menu navigation with `Alt`, not through section cycling.

Alternative considered: preserving a conceptual `Conversion` section with no visible controls. Rejected because it would create a focus stop without visible affordance.

## UI Structure

### Main window

The main window removes the visible `Conversion` row entirely.

The menu bar includes:

- `Translation`
- `Help`

`Translation` contains:

- `Convert`
- `Translation Settings...`
- `Translation Tables Setting...`
- `Dictionary Management...`

### Translation Settings dialog

The dialog contains:

- `Braille Type` choice
- `Width` spin control
- `Dictionary` choice
- standard `OK` / `Cancel` buttons

The dialog edits a staged copy of translation settings only.

### Dictionary Management dialog

The dialog contains:

- a list view of existing managed dictionaries
- action buttons below the list:
  - `Add`
  - `Delete`
  - `Rename`
  - `Edit`
  - `Import`
  - `Export`

The dialog is an immediate management surface, not an `OK/Cancel` settings surface.

## State and Behavior

The implementation should introduce a small translation-settings state boundary, not a new framework.

A minimal data object such as the following is sufficient:

```python
@dataclass
class TranslationSettings:
    output_mode: str
    width: int
    selected_dictionary: str
```

Expected behavior:

- Opening `Translation Settings...` loads current active settings into the staged object
- Editing controls changes only the staged object while the dialog remains open
- Pressing `OK` applies the staged object to runtime state and persists it
- Pressing `Cancel` discards the staged object
- Opening `Dictionary Management...` loads the current dictionary list into a list view
- Running `Add`, `Delete`, `Rename`, `Import`, or `Export` applies immediately to dictionary files
- The management list refreshes immediately after add/delete/rename/import
- Running `Edit` closes `Dictionary Management...` and opens the existing dictionary-entry editor
- Closing the dictionary-entry editor leaves the user at the main window

## Risks / Trade-offs

- Removing the row may break control references in busy-state or focus logic
  - Mitigation: update busy-state handling and section-navigation definitions as part of the same change
- New menu and dialog strings may drift from localization
  - Mitigation: treat all new user-visible labels as localization updates requiring `.po` and compiled catalog changes
- Dictionary selection could become stale after delete or rename in management flow
  - Mitigation: refresh the management list immediately and resolve active selection with existing dictionary fallback rules
- Closing management before opening the editor may feel less direct for repeated edits
  - Mitigation: accept the extra reopen step in exchange for lower implementation complexity and fewer dialog-state interactions

## Testing

Verification should cover:

- `Translation` menu appears with the correct four items and order
- `Translation > Convert` triggers the same workflow as the existing convert action
- `Ctrl+Enter` still triggers conversion
- `Translation Settings...` applies staged settings only on `OK`
- `Translation Settings...` leaves active settings unchanged on `Cancel`
- `Dictionary Management...` shows the current dictionary list in a list view
- `Dictionary Management...` performs add/delete/rename/import/export immediately
- `Dictionary Management... > Edit` closes the management dialog and opens the existing dictionary-entry editor
- `Translation Tables Setting...` still uses the existing dialog and `OK/Cancel` behavior
- `F6` / `Shift+F6` cycles only through visible sections after the conversion row is removed
- Localization files are updated for any new or changed user-visible strings

## Implementation Outline

1. Add the `Translation` menu and wire the four commands to existing or new handlers.
2. Introduce `TranslationSettingsDialog`.
3. Add a small translation-settings state boundary for staged loading and `OK`-time apply.
4. Introduce `DictionaryManagementDialog` with a list view and action buttons.
5. Wire `Edit` in `DictionaryManagementDialog` to close management and then open the existing dictionary-entry editor.
6. Remove the visible `Conversion` row from the main-window layout.
7. Update busy-state handling, section navigation, and tests.
8. Update localization resources for new strings.

## Open Questions

None. The remaining behavioral choices were resolved during brainstorming before writing this spec.
