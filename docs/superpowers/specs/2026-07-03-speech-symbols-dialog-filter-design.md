# Speech Symbols Dialog Filter Design

## Summary

This change adds NVDA-style filtering to DotExpress's custom dictionary editor dialog, [SpeechSymbolsDialog](/workspace/DotExpress/client/dialog.py). The dialog currently shows all dictionary entries in a plain `wx.ListCtrl` and has no search or filter capability. The new design adds an immediate filter text box and upgrades the list to a virtual list so the dialog remains responsive when the dictionary contains hundreds to thousands of entries.

The filter behavior should closely follow NVDA's `SpeechSymbolsDialog` in `include/nvda/source/gui/settingsDialogs.py`, but it is adapted to DotExpress's data model. Filtering applies only to the `Source Text` and `Braille` columns. `Type` is displayed but is not part of the search criteria.

## Goals

- Add an immediate filter text box to `SpeechSymbolsDialog`.
- Filter entries by `Source Text` and `Braille` only.
- Make filtering case-insensitive.
- Use a virtual `wx.ListCtrl` so the dialog scales to hundreds or thousands of entries.
- Preserve selection where possible when the filter changes.
- Disable `Edit` and `Delete` when the filtered result is empty.
- Keep the add, edit, delete, and save flows consistent under filtered and unfiltered states.
- Reuse NVDA's interaction model where it fits this dialog.

## Non-Goals

- No filtering by `Type`.
- No advanced search syntax, regex, or multi-field search options.
- No sorting UI in this change.
- No redesign of `AddSymbolDialog`.
- No change to the CSV storage format.

## User-Facing Behavior

### Filter Input

- Add a text input above the entries list.
- The input filters the list immediately as the user types.
- An empty filter shows the full dictionary.
- Matching is case-insensitive.
- A row matches when the filter text is contained in either:
  - the entry's `Source Text`
  - the entry's `Braille`

### Filtered List Behavior

- The entries list remains single-select.
- The dialog should try to preserve the previously selected entry after filtering.
- If the previously selected entry is no longer in the filtered result, select the first visible row.
- If the filtered result is empty:
  - no row is selected
  - `Edit` is disabled
  - `Delete` is disabled
  - no informational or warning dialog is shown

### Add Behavior

- Adding a new entry still uses `AddSymbolDialog`.
- Duplicate `Source Text` validation remains unchanged.
- If the new entry matches the current filter:
  - keep the current filter text
  - show the filtered result
  - select the new entry
- If the new entry does not match the current filter:
  - clear the filter text
  - show the full list
  - select the new entry

### Edit Behavior

- Editing still operates on the currently selected visible row.
- After the edit is confirmed, the dialog reapplies the current filter.
- If the edited row still matches the filter, it remains selected.
- If the edited row no longer matches the filter, it disappears from the filtered list naturally and selection falls back to a nearby visible row or the first row.

### Delete Behavior

- Deleting still operates on the currently selected visible row.
- After deletion, the dialog reapplies the current filter.
- If rows remain visible, selection moves to the nearest remaining row.
- If no rows remain visible, `Edit` and `Delete` are disabled.

## Internal Design

### Data Model

`SpeechSymbolsDialog` should maintain two collections:

- `self.entries`
  - the full dictionary entry list
  - this remains the source of truth for save operations
- `self.filtered_entries`
  - the currently visible entries after applying the filter
  - this corresponds to NVDA's `filteredSymbols`

The design should use the existing `DictionaryEntry` dataclass and should not introduce a second persisted model.

### List Control

Replace the current plain list population flow with a virtual report list:

- style should include:
  - `wx.LC_REPORT`
  - `wx.LC_SINGLE_SEL`
  - `wx.LC_VIRTUAL`
- the list should provide row text dynamically from `self.filtered_entries`
- column layout remains:
  - `Source Text`
  - `Braille`
  - `Type`

This change is necessary because the intended scale is hundreds to thousands of rows, where repeated delete-and-rebuild list population becomes less suitable.

### Filter Method

Add a dedicated method such as `filter_entries(filter_text: str = "") -> None`.

This method should:

- capture the currently selected visible entry, if any
- compute `self.filtered_entries`
  - if `filter_text` is empty, show all entries
  - otherwise include entries whose `text` or `braille` contains the filter text, case-insensitively
- update the virtual list item count
- restore selection if the previous entry remains visible
- otherwise select the first visible row
- clear selection and disable edit/delete controls if the filtered list is empty

The implementation should mirror NVDA's `filter()` interaction pattern as closely as reasonable for DotExpress.

### Selection Tracking

Selection logic should be entry-based, not raw-index-based.

The dialog should preserve selection by remembering the selected `DictionaryEntry` object before re-filtering, then locating that same object in `self.filtered_entries` if it remains visible.

This avoids mismatches caused by virtual list indexes changing after filtering, editing, or deletion.

### Item Text Retrieval

The list should provide display text from a single callback path, equivalent to NVDA's `getItemTextForList`.

For each visible row:

- column 0 returns `entry.text`
- column 1 returns `entry.braille`
- column 2 returns the localized display label for `entry.entry_type`

### Add / Edit / Delete Integration

All row operations should work against the selected entry in `self.filtered_entries`, then update `self.entries`, and finally reapply the current filter.

Recommended flow:

- add
  - validate duplicate `Source Text`
  - append to `self.entries`
  - if the new row matches the current filter, keep the filter
  - if not, clear the filter control and show all rows
  - select the new row
- edit
  - open the selected entry from `self.filtered_entries`
  - validate duplicate `Source Text`, excluding the same original entry
  - mutate or replace the matching entry in `self.entries`
  - reapply the current filter
  - try to reselect the edited row if it remains visible
- delete
  - remove the selected entry from `self.entries`
  - reapply the current filter
  - select the nearest remaining row

### Button State Rules

`Edit` and `Delete` must be driven by the visible selection state.

- If a visible row is selected, enable both.
- If no visible row is selected, disable both.
- Filtering to zero visible rows must disable both without prompting.

### Save Behavior

Saving remains based on `self.entries`, not `self.filtered_entries`.

This ensures that filtered-out rows are still preserved and written back to disk exactly as they exist in the full dictionary model.

## Testing

### Dialog-Level Tests

Add focused tests for `SpeechSymbolsDialog` behavior covering:

- empty filter shows all entries
- filtering matches `Source Text`
- filtering matches `Braille`
- filtering is case-insensitive
- filtering does not match by `Type`
- empty filtered result disables `Edit` and `Delete`
- selection is preserved when the selected entry remains visible
- selection falls back correctly when the selected entry is filtered out

### Operation Flow Tests

Add tests covering:

- add entry that matches current filter keeps filter and selects new row
- add entry that does not match current filter clears filter and selects new row
- edit entry and preserve it when it still matches filter
- edit entry and remove it from visible rows when it no longer matches filter
- delete selected filtered row and select nearest remaining row
- save writes all full entries, not just filtered entries

### Regression Coverage

Keep existing validation behavior unchanged for:

- duplicate `Source Text`
- invalid Bopomofo input
- invalid Unicode braille input
- save failure error handling

## Risks And Constraints

- `wx.ListCtrl` virtual mode changes how row text is supplied and how selection state is managed; this is the main implementation risk.
- The existing test suite uses lightweight wx stubs, so tests should focus on pure dialog logic and controlled list interactions rather than deep native GUI behavior.
- Entry identity must remain stable enough during filter and edit flows to preserve selection correctly.
- The implementation should stay close to NVDA's model, but it should not copy NVDA-specific controls or helper infrastructure that does not exist in DotExpress.

## Acceptance Criteria

- `SpeechSymbolsDialog` contains a filter input above the entries list.
- Typing in the filter updates the list immediately.
- Filtering only checks `Source Text` and `Braille`.
- Filtering is case-insensitive.
- The entries list uses virtual list behavior suitable for large dictionaries.
- When no filtered rows remain, `Edit` and `Delete` are disabled and no message is shown.
- Adding a new row that does not match the current filter clears the filter and selects the new row.
- Adding a new row that matches the current filter keeps the filter and selects the new row.
- Editing and deleting work correctly while filtered.
- Saving still writes the full dictionary, not only the visible rows.
