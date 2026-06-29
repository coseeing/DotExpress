# File Menu Import Shortcuts Design

## Context

The current client already has a document-list context menu that owns the document lifecycle actions:

- `Open`
- `Delete`
- `Delete All`
- `Add`
- `Rename`
- `Import`
- `Export`
- `Export All`

`Import`, `Export`, and `Export All` already use submenus for format-specific actions. The current import flow reuses the same `on_import_document(format_key)` handler regardless of how the action is reached.

Separately, the view settings already expose a braille font choice with `Default` and `SimBraille`, but the persisted fallback in `config.py` is still `default`, so users without any config file do not start on `SimBraille`.

There is also a global name-length limit of `16` characters in `client/name_validation.py`. That limit is reused by document names and dictionary names, so changing it affects manual add/rename flows as well as imported file names.

The confirmed requirements for this design are:

- When there is no config, the default braille font should be `SimBraille`
- The main frame should support `Alt+O` as a direct shortcut for document import `TXT`
- The menu bar should include a top-level `檔案` / `File` menu that mirrors the document-list context menu
- The name length limit should change from `16` to `32` consistently across the shared name-validation path

## Goals / Non-Goals

**Goals:**

- Change the no-config braille-font fallback to `SimBraille`
- Add a frame-level `Alt+O` shortcut that directly opens the existing `Import -> TXT` workflow
- Add a top-level `File` menu that exposes the same document actions and ordering as the document-list context menu
- Keep document-action enable/disable behavior consistent between the new menu bar entry and the existing context menu
- Increase the shared document/dictionary name limit from `16` to `32`

**Non-Goals:**

- Do not redesign document import/export logic
- Do not change import/export file formats
- Do not introduce a second document-action implementation separate from the existing handlers
- Do not special-case imported names differently from manually entered names

## Decisions

### 1. Make `SimBraille` the config-level default

The default should change at the config source of truth, not only in the UI initialization path. `get_braille_font()` should return `simbraille` when the config file or `view.braille_font` key is missing.

This keeps startup behavior, settings dialog initialization, and any future callers aligned without adding one-off fallback logic in `gui.py`.

### 2. Bind `Alt+O` directly to the existing TXT import handler

`Alt+O` should not just open a menu or move focus. It should invoke the same flow as selecting document-list context menu `Import -> TXT`, meaning it should end up calling the existing document import handler with `format_key="txt"`.

This matches the confirmed user intent: pressing `Alt+O` anywhere in the frame should immediately start TXT import.

### 3. Add a top-level `File` menu that mirrors document-list actions

The menu bar should gain a new top-level `File` menu before or alongside existing top-level menus. Its item order should match the document-list context menu exactly:

- `Open`
- `Delete`
- `Delete All`
- `Add`
- `Rename`
- `Import`
- `Export`
- `Export All`

`Import`, `Export`, and `Export All` should keep the same submenu structure and format options already used in the document-list context menu:

- `Import` -> `DEP`, `TXT`
- `Export` -> `DEP`, `BRL`
- `Export All` -> `DEP`, `BRL`

The new top-level menu is a second entry point to the same document commands, not a new workflow.

### 4. Reuse one document-menu definition for both menu bar and context menu

The action ordering, submenu format labels, and event bindings should come from one shared definition instead of being duplicated in two places.

This avoids a predictable regression where the document-list context menu and the top-level `File` menu drift apart over time.

The shared definition should drive:

- item order
- submenu structure
- handler binding
- enable/disable state based on current selection and document existence

### 5. Increase the shared name-length limit from `16` to `32`

The source of truth for name length is the shared name-validation constant, so the limit should change there. Because document and dictionary naming already depend on that path, the new behavior should apply consistently to:

- imported document names derived from file stems
- manually added document names
- renamed document names
- manually added dictionary names
- renamed dictionary names
- imported dictionary names

All user-facing validation messages that currently say `1 to 16 characters` should be updated to `1 to 32 characters`.

This is the cleanest implementation because it preserves one naming rule instead of introducing import-only exceptions.

## UI / Behavior

### Braille font default

- If no config exists, or `view.braille_font` is absent, the effective braille font should be `simbraille`
- Existing persisted values should keep their current behavior
- Invalid persisted values should still normalize through the existing fallback path, which now lands on `simbraille`

### `Alt+O`

- Works from the main frame regardless of which child control currently has focus
- Opens the same file picker and import flow as `on_import_document("txt")`
- Does not require the document list to be focused first
- Does not open the `File` menu as an intermediate step

### Top-level `File` menu

- Uses the same command ordering as the document-list context menu
- Uses the same submenu formats for import/export actions
- Enables and disables items with the same rules already applied in the context menu
- Stays available through normal menu-bar keyboard navigation in addition to the dedicated `Alt+O` shortcut

## Risks / Trade-offs

- Adding a second entry point to document actions increases the chance of state drift
  - Mitigation: centralize menu structure and binding data instead of maintaining two separate menu implementations
- Changing the shared name limit affects both document and dictionary flows, not just import
  - Accepted because the confirmed requirement chose the global rule, and the code already treats name length as a shared constraint
- `SimBraille` as the default may be selected on platforms where runtime font registration is limited
  - Accepted because the request is specifically about the no-config default; existing font-application fallback behavior should remain unchanged

## Testing

Verification should cover:

- `get_braille_font()` returns `simbraille` when config is missing
- persisted `braille_font` values still round-trip normally
- the main menu bar includes a top-level `File` menu with the expected item order
- `File > Import > TXT` reaches the same handler path as the document-list context menu
- `Alt+O` invokes TXT import from the frame without requiring document-list focus
- top-level `File` menu enable/disable rules match the existing document-list context menu rules
- document-name validation accepts values up to `32` characters and rejects `33+`
- dictionary-name validation accepts values up to `32` characters and rejects `33+`
- imported TXT/DEP file stems up to `32` characters load successfully
- existing tests that asserted `16`-character limits are updated to `32`

## Implementation Outline

1. Change the config-level default braille-font key from `default` to `simbraille`.
2. Introduce a shared document-menu descriptor/helper that both the document-list context menu and the top-level `File` menu can use.
3. Add the top-level `File` menu to the frame menu bar and wire it to the existing document handlers.
4. Add a frame-level accelerator or equivalent frame-wide key binding for `Alt+O` that directly dispatches TXT import.
5. Raise the shared name-length limit from `16` to `32` and update all related validation text.
6. Update unit tests for config fallback, document menu structure, shortcut dispatch, and the new `32`-character naming limit.

## Open Questions

None. The remaining behavioral choices were resolved during brainstorming before writing this spec.
