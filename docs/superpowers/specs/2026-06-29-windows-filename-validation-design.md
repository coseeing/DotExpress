# Windows Filename Validation for Documents and Dictionaries

## Summary

Align document and dictionary naming rules with Windows legal filename rules instead of the current custom restriction that forbids `.`. This allows names such as `1.1` to be created, imported, stored, displayed, and renamed consistently across the app.

At the same time, adjust dictionary import so selecting a CSV file does not immediately commit to its stem as the final dictionary name. After file selection, the app should open the existing dictionary-name dialog with the stem prefilled, allowing the user to accept or edit the name before import. Canceling this dialog must abort the import without copying any file.

## Current State

- Shared name validation lives in [client/name_validation.py](/workspace/DotExpress/client/name_validation.py).
- Both document and dictionary naming normalize through that shared validation.
- The current invalid-character rule forbids `.`, `/`, and `\`, so names like `1.1` are rejected even though they are valid Windows filenames.
- Document text import already derives its candidate name from `Path(...).stem`, so `1.1.txt` naturally produces `1.1`; the failure happens during validation, not while extracting the stem.
- Dictionary import already uses a name dialog after file selection, but it does not prefill the chosen file stem, so users do not get the intended rename-or-confirm workflow.

## Goals

- Allow document and dictionary names that are valid Windows filenames.
- Keep one shared validation rule for both documents and dictionaries.
- Preserve existing DEP package structure and workspace behavior.
- Make dictionary import use the same naming and duplicate-handling flow as manual dictionary creation.

## Non-Goals

- Changing the `.dep` package format.
- Changing workspace sorting behavior.
- Removing the existing 32-character limit.
- Introducing platform-specific branching for non-Windows hosts.

## Naming Rules

`normalize_base_name()` remains the single validation entry point. Its behavior changes from a short denylist to a Windows-filename legality check.

Allowed examples:

- `1.1`
- `chapter.2`
- `ver 2.0`

Rejected examples:

- empty or whitespace-only names
- `.`
- `..`
- names ending with `.` or space
- names containing `<`, `>`, `:`, `"`, `/`, `\`, `|`, `?`, `*`
- names containing control characters
- Windows reserved device names such as `CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, and `LPT1`-`LPT9`
- names longer than 32 characters

Normalization remains trim-based. After trimming, the resulting name must still satisfy the Windows legality rules above.

## Documents

No package-format change is needed.

- Workspace files continue to be stored as `<document_name>.dep`.
- DEP contents continue to be stored as `<document_name>.txt` and `<document_name>.brl`.
- Text import continues to derive the base name from `Path(source).stem`.
- DEP loading continues to compare the package stem with the internal `.txt` and `.brl` stems.

Because Python `Path.stem` handles `1.1.txt` as `1.1`, allowing `.` in the validated document name is sufficient for the import case that currently fails.

## Dictionaries

Dictionary names move to the same Windows-legal shared rule as documents.

Dictionary import flow changes as follows:

1. User selects a CSV file.
2. The app derives `source_path.stem`.
3. The app opens `DictionaryNameDialog` with that stem prefilled in the editable text control.
4. The user may accept the suggested name or modify it.
5. On OK, the app validates and imports using the final dialog value.
6. On Cancel, the import is aborted and no file is copied.

This keeps imported dictionaries consistent with manually created dictionaries and gives the user a direct recovery path when the default stem conflicts with an existing name.

## Error Handling

- Shared validation failures continue to surface as `ValueError` from the normalization layer.
- UI entry points continue to translate those failures into user-facing message boxes.
- Duplicate dictionary names continue to use the existing duplicate-name error path.
- Invalid CSV structure continues to use the existing header-validation error path.
- Canceling the post-selection dictionary name dialog is treated as a normal no-op, not an error.

## UI Changes

- Document name validation text in `DocumentNameDialog` must no longer claim that `.` is forbidden.
- Dictionary name validation text in `DictionaryNameDialog` must no longer claim that `.` is forbidden.
- `DictionaryNameDialog` should support receiving an initial value so import can prefill the selected file stem while rename can continue preloading the current name.

## Testing

Add or update tests for these cases:

- `normalize_document_name("1.1")` succeeds.
- `normalize_dictionary_name("1.1")` succeeds.
- `.`, `..`, `name.`, and `name ` are rejected.
- reserved device names such as `CON` and `LPT1` are rejected.
- invalid Windows characters are rejected.
- `1.1.txt` document import succeeds and produces document name `1.1`.
- dictionary import dialog flow preloads the selected file stem and allows cancel to abort import cleanly.

## Risks and Mitigations

- Shared-rule change affects both documents and dictionaries.
  Mitigation: keep tests for both paths and avoid separate hidden exceptions.
- Windows filename semantics include edge cases beyond the old denylist.
  Mitigation: encode the legality rules explicitly in `name_validation.py` and verify them through focused unit tests.
- UI text can drift from actual validation behavior.
  Mitigation: update both dialog validation messages in the same change as the validation logic.
