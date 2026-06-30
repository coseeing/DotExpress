# Import Dialog Simplification And Export-Time Conversion Design

## Summary

This change removes background auto-conversion from the document workflow while keeping the window title enhancement that shows the current document name. It also simplifies document import by replacing the import format submenu with a single file dialog that lets the user choose the desired file type filter directly.

The main goal is to avoid UI stalls when importing documents. Braille conversion should no longer happen automatically during import, save, open, or other background workflows. Instead, pending documents are converted only when the user explicitly runs Convert or when export requires braille output.

## Goals

- Keep the current-document window title behavior.
- Remove all background auto-conversion behavior.
- Run automatic conversion only when export needs braille output.
- Reuse the existing threaded conversion flow and "converting" dialog during export-triggered conversion.
- Avoid repeated success dialogs during Export All.
- Replace the import format submenu with a single Import command that uses file type filters in the file dialog.

## Non-Goals

- No background conversion queue, registry, or pending job system.
- No redesign of the manual Convert workflow beyond making its completion messaging configurable for export reuse.
- No changes to supported import/export formats.
- No changes to document package format beyond continuing to preserve pending braille metadata where applicable.

## User-Facing Behavior

### Window Title

- When no document is open, the frame title is `DotExpress`.
- When a document is open, the frame title is `<document name> - DotExpress`.
- Title updates must happen when opening, switching, renaming, deleting, or clearing the open document.

### Saving And General Editing

- Saving an open document must not trigger auto-conversion.
- If a document currently has pending braille (`braille is None`), saving must preserve that pending state.
- Importing documents must not trigger conversion.
- Startup loading must not trigger conversion.
- Closing the app must not trigger conversion.

### Manual Convert

- Manual Convert keeps the current behavior:
  - conversion runs on a worker thread,
  - the delayed `converting` dialog appears for longer conversions,
  - successful completion shows `Conversion completed.`,
  - failures show the current error dialog behavior.

### Export Single Document

- Exporting a single document still supports `DEP` and `BRL`.
- If the document already has braille output, export writes it directly.
- If the document has pending braille:
  - conversion runs on a worker thread,
  - the delayed `converting` dialog is shown the same way as manual Convert,
  - successful conversion does not show `Conversion completed.`,
  - export continues automatically after conversion succeeds.
- After the single-document export finishes:
  - success shows one export-complete dialog,
  - failure shows one error dialog and the file is not exported.

### Export All Documents

- Export All still supports `DEP` and `BRL`.
- Each document is processed independently.
- If a document already has braille output, it is exported directly.
- If a document has pending braille, it is converted first using the same worker-thread + delayed `converting` dialog flow.
- During Export All:
  - successful per-document conversions must not show `Conversion completed.`,
  - successful per-document exports must not show per-file completion dialogs.
- If one document fails conversion or export:
  - that document is skipped,
  - remaining documents continue processing.
- At the end of Export All, exactly one summary dialog is shown:
  - all success: report that all documents were exported successfully,
  - partial failure: report that export completed with failures, list failed document names, and include their reasons.

### Import Dialog

- The File menu and document context menu should expose a single `Import` command instead of an import submenu.
- Selecting `Import` opens one `wx.FileDialog` with multiple filters.
- The filter order must be:
  - `DEP`
  - `DOCX`
  - `EPUB`
  - `PDF`
  - `TXT`
  - `All Supported Files`
- The default selected filter must be `All Supported Files`, even though it is listed last.
- `All Supported Files` allows mixed multi-select across:
  - `.dep`
  - `.docx`
  - `.epub`
  - `.pdf`
  - `.txt`
- When `All Supported Files` is active, each selected file is dispatched by its own extension to the matching importer.
- `All Supported Files` only exposes the same five supported extensions, so unsupported extensions are not part of the picker in this mode.

## Internal Design

### Title Formatting

- Add a small helper in the document/session layer to format the frame title from the open document name.
- GUI code should call that helper whenever `_open_document_name` changes or the open document is cleared.

### Save Flow

- The existing `prepare_document_for_save` helper currently auto-converts pending documents.
- Saving behavior should be split so that normal save preserves pending braille without conversion.
- Export-only preparation should continue to use conversion-aware logic.
- Preferred structure:
  - a save helper that only stores the current text and braille values as-is,
  - an export helper that prepares a document for export, converting only when required by export flow.

### Conversion Reuse

- Keep the existing conversion thread infrastructure in `BrailleFrame`.
- Refactor the completion path so callers can choose whether a successful conversion should:
  - update the output editor,
  - show `Conversion completed.`,
  - continue into an export callback.
- Manual Convert uses the existing success message.
- Export-triggered conversion suppresses the manual success message and continues into export logic.

### Export Result Reporting

- Add a small result structure or helper to accumulate:
  - successful exports,
  - failed document names,
  - failure reasons.
- Single export produces one final result dialog.
- Export All produces one final summary dialog after the batch finishes.

### Import Format Dispatch

- Introduce a helper for import wildcard/filter generation so the dialog and default filter order are explicit.
- Introduce extension-based dispatch for the `All Supported Files` mode.
- Existing format-specific import behavior stays unchanged for `dep`, `epub`, `pdf`, `docx`, and `txt`.

## Testing

### Unit Tests

- Update document menu tests to expect `Import` as a command instead of a submenu.
- Add document/session tests for window title formatting.
- Add workspace import tests covering `All Supported Files` mixed-extension dispatch.
- Update or replace save-related tests so ordinary save no longer implies auto-conversion.

### Targeted GUI/Flow Tests

- Add or update tests around import dialog helpers if they are implemented as pure functions.
- If practical within current test patterns, cover export result summarization logic separately from wx dialog wiring.

## Risks And Constraints

- Export All becomes an asynchronous chained flow when pending documents exist. The implementation must ensure exactly one final summary dialog is shown.
- Title updates must stay synchronized with existing open/rename/delete flows; missing one path would leave stale titles.
- Reusing the manual conversion path for export must avoid unintended editor focus changes or duplicate success dialogs.

## Acceptance Criteria

- Importing documents no longer triggers background or save-time conversion.
- Saving a pending document preserves pending braille state.
- Manual Convert still behaves as before.
- Exporting a pending document converts it on a worker thread with the existing `converting` dialog behavior.
- Export single shows one final export result dialog.
- Export All shows exactly one final summary dialog for the whole batch.
- Export All continues exporting other documents when one document fails.
- Window title displays `<document name> - DotExpress` for the open document.
- Import is a single command with the required filter order and default selected filter.
- `All Supported Files` supports mixed-format multi-select and extension-based dispatch.
