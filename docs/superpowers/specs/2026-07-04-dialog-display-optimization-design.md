# Dialog Display Optimization Design

## Summary

This change addresses inconsistencies in the initial sizing, centering behavior, and list presentation of the current DotExpress dialogs. At the moment, `TranslationSettingsDialog` and `TranslationTableDialog` already use content-driven `SetSizerAndFit()`, while `DictionaryManagementDialog` and `SpeechSymbolsDialog` still rely primarily on fixed minimum sizes. Most custom `wx.Dialog` classes also do not explicitly center relative to their parent window.

This design standardizes the display rules for custom dialogs: general dialogs should derive their initial size from content and center relative to their parent whenever possible; `DictionaryManagementDialog` will be changed to a two-column virtual list, with the first column showing the dictionary name and the second showing the dictionary entry count; `SpeechSymbolsDialog` will keep its multi-column virtual list and column separators, but switch to content-driven initial sizing. There is one deliberate exception: `Dual ViewFrame` will not use centering, and will instead copy the current position and size of the main window so it covers the entire main window area.

## Goals

- Make the initial size of `DictionaryManagementDialog` content-driven via `Fit`.
- Make the initial size of `SpeechSymbolsDialog` content-driven via `Fit`.
- Remove the dependency on fixed minimum sizes as the initial sizing strategy for `DictionaryManagementDialog` and `SpeechSymbolsDialog`.
- Make all custom `wx.Dialog` windows center relative to their parent whenever possible.
- Convert `DictionaryManagementDialog` to the same virtual list style used by the dictionary entry manager.
- Make `DictionaryManagementDialog` display two columns: dictionary name and dictionary entry count.
- Keep `DictionaryManagementDialog` single-click selection only, without double-click editing.
- Make the column widths in `DictionaryManagementDialog` recalculate based on available width instead of staying hard-coded.
- Make `Dual ViewFrame` open with the same position and size as the main window.

## Non-Goals

- Do not redesign the functional workflows of dictionary management or dictionary entry management.
- Do not introduce a new font system, DPI framework, or cross-platform scaling layer.
- Do not rewrite `DictionaryManagementDialog` using `wx.ListBox`, `wx.DataViewListCtrl`, or a different widget family.
- Do not change the platform-default behavior of built-in `wx.FileDialog`, `wx.DirDialog`, or `wx.MessageDialog`.
- Do not explicitly synchronize the maximized-state flag of `Dual ViewFrame`.
- Do not introduce caching or background loading for dictionary entry counts.

## User-Visible Behavior

### General Custom Dialogs

- Custom `wx.Dialog` windows should open centered relative to their parent whenever possible.
- If a dialog has no parent window, it should use normal screen centering.
- Small settings-style dialogs should derive their initial size from content instead of relying on fixed dimensions.

### `DictionaryManagementDialog`

- Its initial size should be content-driven.
- It should center relative to its parent.
- The dictionary list remains single-selection.
- The list becomes a virtual list implementation.
- The list displays two columns:
  - Dictionary name
  - Dictionary entry count
- The list only needs single-click selection.
- It should not support double-click to enter editing directly.
- Users must use the `Edit` button to open the dictionary entry manager.
- The entry count in the second column should reflect the real value at open time or refresh time.
- Column widths should adapt to the available dialog width instead of being hard-coded.

### `SpeechSymbolsDialog`

- Its initial size should be content-driven.
- It should center relative to its parent.
- It keeps the current multi-column virtual list.
- Column separators remain, because they are appropriate for multi-column data.

### `Dual ViewFrame`

- Opening `Dual View` does not use normal centering.
- `Dual ViewFrame` should directly copy the current position and size of the main window.
- The visual goal is to cover the area currently occupied by the main window, instead of opening at its own default size.

## Internal Design

### Shared Dialog Finalization Rule

Add a small shared helper in `client/dialog.py` to standardize the display finalization step at the end of custom dialog construction.

This helper is only responsible for:

- Applying final layout / fit
- Running `CentreOnParent()` when a parent exists
- Running `Centre()` when there is no parent

This helper should not introduce new state management or abstractions. Its purpose is only to centralize the currently scattered, missing, or inconsistent final display logic.

### Initial Size Strategy for General Dialogs

The following dialogs keep their existing structure, but should use a content-driven initial size strategy:

- `AddSymbolDialog`
- `DictionaryNameDialog`
- `DocumentNameDialog`
- `InvalidWorkspaceFilesDialog`
- `FileIssuesDialog`
- `TranslationSettingsDialog`
- `TranslationTableDialog`
- `ConvertingDialog`

Dialogs that already use `SetSizerAndFit()` should continue doing so. Any dialog currently relying on a fixed minimum size as the primary source of its initial size should remove that dependency and let `Fit()` determine the initial size.

### Size and Position of `SpeechSymbolsDialog`

`SpeechSymbolsDialog` keeps these core traits:

- `wx.RESIZE_BORDER`
- A three-column virtual `wx.ListCtrl`
- A `Filter` text input
- `Add` / `Edit` / `Delete` / `OK` / `Cancel` interactions

This change only adjusts the display rules:

- Perform a final `Fit()` after building the UI
- Stop using `SetMinSize((560, 440))` as the initial sizing basis
- Apply the common parent-centering rule

Users can still manually resize the window after it opens.

### Converting `DictionaryManagementDialog` to a Virtual List

`DictionaryManagementDialog` currently uses a normal `wx.ListCtrl` and rebuilds rows using `DeleteAllItems()` and `InsertItem()`. This design changes it to the same virtual list style used by the dictionary entry manager.

The recommended approach is to add a reusable virtual list control base, similar in role to the current `DictionaryEntryListCtrl`, but not tied to a specific data model. Its minimum responsibility is:

- Accept a `get_item_text(row, column)` callback
- Provide cell text dynamically through `OnGetItemText()`

Both `SpeechSymbolsDialog` and `DictionaryManagementDialog` can use this more general virtual list control.

### Data Source of `DictionaryManagementDialog`

The real data source of `DictionaryManagementDialog` remains:

- `self._dictionary_names`

In addition, the dialog should maintain a mapping of dictionary name to entry count, for example:

- `dictionary_name -> entry_count`

This data should be computed at dialog open time rather than coming from cached state.

### Entry Count Calculation for `DictionaryManagementDialog`

The entry count shown in the second column should be computed immediately whenever the dialog opens or refreshes.

Recommended approach:

- Read each dictionary CSV file
- Count the number of valid entries
- Store the result in the dialog's current count mapping

The definition of "valid entry count" should match the actual loading behavior of the current dictionary editor. If a row would be ignored by the dictionary editor, it should not be counted here either.

This change does not require a cache or background thread for counts. At the current scale, computing them when the dialog opens is acceptable.

The list should no longer be updated by inserting rows. Instead it should:

- Update `self._dictionary_names`
- Update the count for each dictionary
- Call `SetItemCount(len(self._dictionary_names))` to update the virtual row count
- Call `Refresh()` to redraw
- Restore selection based on `preferred_name`

This keeps the list refresh logic aligned with the virtual-list model already used by `SpeechSymbolsDialog`, and reduces visual side effects caused by rebuilding rows.

### Interaction Model of `DictionaryManagementDialog`

The list interaction model should be simplified to:

- Single-click selects the current row
- Only the `Edit` button opens the dictionary entry manager
- No double-click direct edit
- No requirement for an `Enter` shortcut to edit

Therefore:

- Remove the `EVT_LIST_ITEM_ACTIVATED` binding
- Keep `_on_edit()` as the explicit entry point for the `Edit` button

### Column Presentation of `DictionaryManagementDialog`

This list should use a two-column report-style presentation, and both columns should carry real information:

Design requirements:

- Column 1 shows the dictionary name
- Column 2 shows the dictionary entry count
- Column widths are not hard-coded
- Column 2 should be wide enough to display counts reliably and remain clearly separated from column 1

Column widths should be recalculated at these times:

- After dialog creation finishes
- After dialog resize
- After dictionary list refresh

The width goal is to fit the `ListCtrl` client width so that both columns adapt when Windows font size increases, content becomes wider, or the user manually resizes the dialog. Column 1 should take the majority of remaining space, while column 2 keeps a width suitable for displaying counts.

### Initial Size of `DictionaryManagementDialog`

`DictionaryManagementDialog` keeps `wx.RESIZE_BORDER`, but should no longer rely on a fixed `SetMinSize((650, 400))` as its initial sizing rule.

The new rule is:

- Run `Fit()` after UI construction
- Then center relative to the parent window

This allows the initial size to reflect the actual size of the button row, list, title, and system font, instead of using a fixed assumed size.

### Synchronizing Position and Size of `Dual ViewFrame`

`Dual ViewFrame` is the explicit exception to the general dialog rule in this design.

When a user opens `Dual View` from the main window:

- Do not run `CentreOnParent()`
- Do not use a default size
- Read the current geometry of the main window:
  - Position
  - Size
- Apply the same position and size to `Dual ViewFrame`

The goal is for `Dual ViewFrame` to cover the currently visible area of the main window. This change does not additionally synchronize the maximized-state flag; it only relies on the current effective position and size of the main window.

## Implementation Breakdown

### 1. Shared Dialog Helper

- Add a shared dialog display finalization helper
- Use it at the end of construction for the relevant custom dialogs

### 2. `SpeechSymbolsDialog`

- Keep the existing multi-column virtual list structure
- Remove dependency on a fixed minimum size
- Switch to content-driven `Fit`
- Apply parent-relative centering

### 3. `DictionaryManagementDialog`

- Convert the normal `wx.ListCtrl` to a virtual list
- Rewrite refresh flow to use `SetItemCount()` and `Refresh()`
- Compute entry counts for each dictionary at open and refresh time
- Remove double-click edit behavior from the list
- Keep the `Edit` button as the editing entry point
- Add column width recalculation logic
- Switch to content-driven `Fit`
- Apply parent-relative centering

### 4. `Dual ViewFrame`

- Read the current position and size of the main window during the open flow
- Apply the same values after creating the frame

## Testing

### Dialog Display Behavior

- Open each custom `wx.Dialog` and confirm it centers relative to its parent
- Confirm `TranslationSettingsDialog` and `TranslationTableDialog` do not regress
- Confirm `InvalidWorkspaceFilesDialog` and `FileIssuesDialog` do not clip content after removing fixed-minimum-size dependence

### `SpeechSymbolsDialog`

- Confirm the initial size comes from `Fit`
- Confirm it remains manually resizable
- Confirm multi-column separators still display correctly

### `DictionaryManagementDialog`

- Confirm the virtual list still displays all dictionary names correctly
- Confirm the second column correctly shows entry counts for each dictionary
- Confirm single-click selects the current dictionary
- Confirm there is no double-click direct edit behavior
- Confirm the `Edit` button still opens `SpeechSymbolsDialog`
- Confirm add, delete, rename, and import operations still refresh the list and restore selection correctly
- Confirm add, delete, import, or dictionary-entry edits update the count column correctly
- Confirm the initial size comes from `Fit`
- Confirm both column widths are recalculated after creation, refresh, and resize

### `Dual ViewFrame`

- Open `Dual View` from the main window
- Confirm its position and size match the main window
- Confirm the result is covering the current main window area rather than opening as a default-sized separate window

## Risks and Limitations

- Virtual `wx.ListCtrl` mode changes how `DictionaryManagementDialog` manages refresh and selection, which is the main implementation risk.
- Fitting column widths to client width will still be affected by platform-native theme behavior, but should be significantly better than fixed widths.
- If there are many dictionaries and each dictionary file is large, computing counts at dialog open time may add a small delay; at the current scale this is an acceptable tradeoff.
- After switching dialogs to `Fit()`, some environments may produce different initial sizes than today; this is an intended behavior change, not a side effect.
- `Dual ViewFrame` only copies the current position and size of the main window, and does not continue tracking later moves or resizes of the main window.

## Acceptance Criteria

- `DictionaryManagementDialog` opens with an initial size derived from content.
- `SpeechSymbolsDialog` opens with an initial size derived from content.
- All custom `wx.Dialog` windows center relative to their parent whenever possible.
- `DictionaryManagementDialog` uses a virtual list to display the dictionary list.
- `DictionaryManagementDialog` uses two columns to show dictionary names and dictionary entry counts.
- `DictionaryManagementDialog` only requires single-click selection and does not support double-click direct editing.
- The column widths in `DictionaryManagementDialog` are no longer hard-coded and are recalculated based on available width.
- The second column in `DictionaryManagementDialog` reflects the real dictionary entry count.
- `SpeechSymbolsDialog` still keeps its multi-column separators.
- `Dual ViewFrame` opens by copying the current position and size of the main window.
