# Dictionary Editor UX (F-11) Design

## Goal

Task F-11 is item 4 of the ordering in `task.md` ("F-11 dictionary editor UX"). It makes the custom dictionary editor (`DictionaryEntriesDialog`, title "Custom Dictionary Manager") and its neighbours behave the way the user decided on 2026-10-10. It covers:

- `task.md` #7: rows the editor hides (F-4) are invisible and never mentioned;
- `task.md` #8: conversion still uses those rows;
- `task.md` #9 and P2-2 Q4: Delete removes the first *equal* row, not the selected one;
- P2-2 Q2: OK always rewrites the file;
- P2-2 Q5: Cancel, Esc and the close box discard edits without asking;
- P2-2 Q6: a duplicate source text in Add/Edit throws away what the user typed;
- `task.md` #2, F-W6: a case-only dictionary rename (`alpha` to `Alpha`) is refused on Windows. This is the one failing test of the suite;
- F-6 review M-4: an Import source that is locked shows a raw `[Errno 13]`;
- F-6 review M-5: the editor reads its file after the native dialog exists, so a read failure leaves a hidden, half-built dialog, and any failure is described as "cannot be read".

Decided by the user (2026-10-10), `task.md` section 3. These are not asked again here:

- **U1 (#7, F-11 item 1).** Go back to the pre-F-4 behaviour: OK removes the rows the editor hides. Before that, a confirmation box lists each hidden row with its row number, source text and reason. Yes removes them and saves; No returns to the editor without saving. A dictionary without hidden rows is not affected. F-4 D5 (refusing a new entry whose source text equals a hidden row's) is removed.
- **U2 (P2-2 Q2, item 2).**
  1. No change: no write. The exception is U1: with hidden rows, OK still shows the box.
  2. With changes: keep stripping whitespace and turning an unknown type into `General`, so the file matches what the editor showed.
  3. Keep extra columns, in the original header order. Unchanged rows keep their values; new rows get empty values.
  4. Keep the BOM as in the original file. New dictionaries the program creates stay without a BOM (a follow-up). The sha256 of `dictionary_entries_trace.json` must not change.
- **U3 (P2-2 Q5, item 3).**
  1. Cancel, Esc and the close box ask only when there are unsaved changes. The text is like "Do you want to discard the changes made to the dictionary?". The buttons are 放棄變更 (discard changes) and 返回編輯 (back to editing), and the default is 返回編輯. "Changed" is the same test as in U2; hidden rows are not unsaved changes.
  2. Deleting an entry does not ask. A wrong delete is undone with Cancel, then 放棄變更.
- **U4 (P2-2 Q6, item 4), option A.** The duplicate check moves into the OK of the Add/Edit entry dialog, like the format checks. It shows the existing "Source text "X" already exists." message. The dialog stays open, the input is kept, and the focus goes back to the source text field with its text selected. Only visible entries are checked. No new string.
- **U5 (the other four items; the user agreed to the orchestrator's defaults).**
  1. F-W6: allow a case-only rename. When the renamed dictionary is the selected one, update the name in `config.json`. No new string.
  2. #9 (P2-2 Q4): Delete and Replace act on the selected entry (identity). The duplicate check excludes the entry being edited. No new string.
  3. F-6 M-4: when the Import read error is one of the kinds F-6 classified, use F-6's friendly reason. No new string.
  4. F-6 M-5: read the file before creating the dialog. A read failure keeps F-6's reason; an unexpected error shows a general failure message and is written to `gui.log`. At most one new string.
- **U6 (#8).** Conversion also ignores the rows the editor hides, by the same test (`_is_editable` in `dictionaries/entries.py`): a source text that is empty after stripping (whitespace-only text included), or a `Bopomofo` row whose sequence does not parse. Existing dictionaries with such rows convert differently afterwards. #8 is part of F-11.

After this task:

- Opening the editor and pressing OK without changes writes nothing. With hidden rows, the box of D1 appears first.
- Pressing OK after changes writes the shown entries in order. Each entry is stripped and its type normalized, as today. The header, extra columns and BOM of the file are kept.
- Cancel, Esc and the close box ask only when something changed. The default answer keeps the editor open.
- A duplicate source text in Add/Edit is reported inside the entry dialog, and the typed entry is kept.
- Delete and Edit act on the selected row, also when two rows are identical.
- Conversion ignores the rows the editor hides.
- `alpha` can be renamed to `Alpha`. If it is the selected dictionary, `config.json` follows.
- A locked Import source gets F-6's "cannot be opened" reason.
- The editor's file is read before the dialog exists.

New user-visible strings: **11** (see "User-Visible Strings"). The msgid count goes from 369 to 380. One more question needs the user (O1); see "Open Questions".

Non-goals:

- showing or repairing hidden rows inside the editor;
- counting hidden rows in Dictionary Management (U1 keeps the count);
- a BOM for new dictionaries;
- the wording of messages outside this task (F-12);
- F-10 (UEB line breaks, `$`).

## Current State (verified 2026-10-11 on `main` `1ce6ce5`, worktree `D:\workspace\DotExpress-f11`, `HEAD:client` `a64da653`)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`. The orchestrator's baseline from the worktree's `client\` is: `$PY -B -X utf8 -m unittest discover -s tests` gives `Ran 1483`, `FAILED (errors=1, skipped=7)`. The only error is F-W6 `test_case_only_rename_still_renames`. The catalog has 369 msgids. The probes below ran on a scratch copy of `client/` in the session scratchpad (`...\scratchpad\f11spec\`) and are not committed.

### Where things are (`1ce6ce5`)

| Piece | Location | Today |
| --- | --- | --- |
| Loader | `dictionaries/entries.py:68-92` `load_dictionary_rows` | `csv.DictReader` over `utf-8-sig`. It strips text and braille and normalizes the type. A row that fails `_is_editable` (`:95-104`) becomes a `PreservedDictionaryRow` (`:30-42`) with its raw fields. It keeps no header, no BOM flag, no extra columns and no line numbers. |
| Writer | `entries.py:112-128` `save_dictionary_entries` | Fixed header `text,braille,type`, UTF-8 **without BOM**, `\r\n`, minimal quoting, extra columns and overflow fields **dropped**. Preserved rows are written back field-exact (F-4 D3). |
| Model | `dictionaries/entry_list_model.py` | `source_text_exists` (`:119-127`) scans **every row, preserved rows included** (F-4 D5). `add` (`:135-143`) raises `DuplicateEntryError`. `replace` (`:145-152`) swaps by identity. `remove` (`:154-158`) is `self._rows.remove(entry)`, which removes the first **equal** row (Q4). `_selection_after` (`:171-180`) restores the selection by equality. `save` (`:70-72`) writes every row. |
| Editor | `dialog.py:341-508` `DictionaryEntriesDialog` | `super().__init__` (`:349`) runs **before** `DictionaryEntryListModel.load` (`:352`) (Q8, M-5). Only OK gets a handler (`:399-401`), so Cancel, Esc and the close box close at once (Q5). `_on_add_clicked` / `_edit_selected` (`:451-480`) close the entry dialog first and run the duplicate check afterwards, so the typed entry is lost (Q6). `_on_remove_clicked` (`:482-486`) does not ask. `_on_ok` (`:502-508`) **always saves** (Q2). A save error shows `Failed to save: {error}` and the editor stays open. |
| Entry dialog | `dialog.py:70-164` `AddSymbolDialog` | `get_braille` strips (`:113-114`). `_on_ok` (`:144-164`) checks the format only (`validate_dictionary_entry`, `entries.py:54-65`), with caption `Info`. |
| Frame | `gui.py:1029-1051` `on_open_dictionary_management` | It guards the constructor. Any exception is logged with `log_dictionary_read_error` and shown as `describe_unreadable_dictionary` (F-6 D6). The half-built dialog stays as a hidden child of the frame (F-6 M-5). |
| Message boxes | `ui/message_box.py:15-33` | `message_box` forces the labels `OK` / `Cancel`, so it cannot show custom button labels. F-5's close dialog (`gui.py:474-490`) uses `wx.MessageDialog` with `SetYesNoCancelLabels` directly. |
| Rename | `dictionaries/manager.py:100-110` `rename_dictionary` | `if destination_path.exists(): raise FileExistsError` (`:107-108`). On Windows `Alpha.csv` "exists" when `alpha.csv` does, so a case-only rename is refused (F-W6). `name_prompt.py:33-42` passes a case-only change through. The presenter's rename (`dictionaries/presenter.py:137-165`) already moves the active name through `plan_dictionary_state_after_rename` (`translation/dictionary_state.py:29-39`), so `config.json` would follow once the rename succeeds. |
| Import | `presenter.py:167-190`; `manager.py:87-97`, `validate_dictionary_csv` `:59-73` | `(UnicodeDecodeError, csv.Error)` get F-6's reason (`:178-181`). Any other `OSError` shows `Failed to import dictionary: {error}` with the raw error (`:185-187`), whether it came from reading the source or from writing the copy (M-4). |
| Reasons | `dictionaries/read_problems.py:29-57` | `PermissionError` maps to CANNOT_OPEN: "The file cannot be opened. It may be in use by another program, or you may not have permission to read it. ..." |
| Counts | `read_problems.py:83-89`, `dialog.py:610-623` | `len(load_dictionary_entries(path))`: the visible entries only. |
| Conversion | `conversion/text/dictionary_rules.py:169-200` `LoadedDictionaryRules.from_paths` | It skips a row only when the **raw** text is `""` (`:181-182`). A whitespace-only text is a rule. A `Bopomofo` row whose `processing` raises falls back to scanning the raw string with the Bopomofo trie (`:185-194`), so the row is still a rule. The first rule of a duplicated source wins (`_build_trie`, `:41-43`). `processing` is injected: `normalize_zhuyin_sequence` in production (`conversion/text/pipeline.py:52`). The module imports nothing from `dictionaries`. |

Tests that pin today's defects, each marked `# KNOWN BUG (P2-2 spec, Qn)` in `tests/test_dictionary_entries_dialog.py`:

- Q8: `test_invalid_utf8_raises_from_the_constructor_after_the_native_dialog` (`:840`);
- Q5: `test_only_ok_gets_a_handler_and_both_standard_buttons_are_localized` (`:862`) and `test_delete_has_no_confirmation_and_selects_the_row_now_at_that_index` (`:1254`);
- Q6: `test_duplicate_of_a_hidden_entry_is_rejected_with_the_exact_message` (`:1031`) and `test_duplicate_is_rejected_with_the_exact_message_and_nothing_changes` (`:1186`);
- Q4: `test_identical_rows_edit_replaces_the_selected_row_but_cannot_keep_its_text` (`:1206`) and `test_identical_rows_delete_removes_the_first_equal_row` (`:1304`);
- Q2: `test_unchanged_dictionary_keeps_hidden_rows_and_is_rewritten_in_normalized_form` (`:1348`).

Other tests press OK without a change and expect a write, for example `test_bom_dictionary_opens_with_its_rows_and_ok_saves_them_without_the_bom` (`:852`) and `test_ok_saves_the_full_list_in_order_and_closes` (`:1333`). They change with D4 and D5.

F-4's D5 is pinned in `tests/test_dictionary_entry_list_model.py` (`test_add_or_replace_with_the_source_text_of_a_preserved_row_is_a_duplicate`, `test_a_preserved_row_blocks_only_its_raw_unstripped_source_text`). F-W6 is `tests/test_dictionary_name_prompt.py:82`. The conversion golden case "Bopomofo row with a processing that raises" (`tests/test_conversion_text_dictionary_rules.py`) expects the fallback rule.

### Probes

1. **Golden trace and identity.** `DictionaryEntriesTraceTest` replays 40 recorded sequences on `TRACE_CSV`, which has two identical rows `a,⠁,General`. The fixture `dictionary_entries_trace.json` (sha256 `f493da52...`) must not change.
   - With `remove` patched to identity, the replay passes.
   - With the selection restored by identity, 4 sequences (seeds 23, 29, 33, 37) differ at a Delete step: the selection goes to index 0 instead of the remaining twin.
   - No recorded Edit keeps the text of a row that has a twin (0 hits). So D9's Q4 change does not touch the trace.
2. **Task dialogs on this machine** (wx 4.2.5, zh-TW Windows).
   - `wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING` with `SetOKCancelLabels`: both custom labels are shown. The keyboard focus is on the Cancel button, and the dialog has a close button. Esc, Enter and Alt+F4 all return `wx.ID_CANCEL`.
   - `wx.YES_NO | wx.NO_DEFAULT` (system labels 是(Y) / 否(N)): Esc and Alt+F4 do **nothing**; the box stays open and has no close button. Enter returns `wx.ID_NO`.
3. **Case-only rename.** `rename_dictionary(d, "alpha", "Alpha")` raises `FileExistsError`. `os.path.samefile(alpha.csv, Alpha.csv)` is `True`, and `Path.rename` from `alpha.csv` to `Alpha.csv` works: the listing shows `Alpha.csv`.
4. **First-tone final syllables.** `normalize_zhuyin_sequence` accepts `"ㄇㄚ "` but rejects `"ㄇㄚ"`, `"ㄓㄨㄥ ㄒㄧㄣ"` and `"ㄇㄚˉ"`. Its rule: "a first tone must be a space". The loader strips the braille before the check, so the editor **hides** every Bopomofo row whose last syllable is first tone (for example `中心,ㄓㄨㄥ ㄒㄧㄣ ,Bopomofo`). `AddSymbolDialog.get_braille` strips too, so such a sequence cannot be entered at all. Conversion uses the raw value, where the row is valid. F-4 noted this (its Current State). See O1.
5. **csv record lines.** With `csv.reader`, a record starts at the previous `line_num + 1`. A blank line is its own `[]` record, and a quoted field may span lines. `csv.DictReader` takes the first record as the header, even an empty one. It skips `[]` records, gives a missing field as `None`, and puts overflow fields under the key `None`.

## Decisions

**D1. Hidden rows: confirm on OK, then remove (U1).**

- The model keeps the hidden rows (`PreservedDictionaryRow`) as it does now, so the editor can list them. Each one also records the file line on which its record starts, counting the header as line 1 (probe 5). This is the number Notepad shows. Excel shows the same number unless a field spans lines.
- On OK, if the model holds at least one hidden row, the editor shows a confirmation box (`wx.MessageDialog`, `wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING`):
  - caption `Remove Rows That Cannot Be Shown`;
  - message: one line per hidden row in file order, framed by a lead-in sentence and a question (strings 1 to 5);
  - each row line is one of:
    - `Row {line}: no source text`, when the stripped text is empty;
    - `Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid`, otherwise. The values are the stripped text and the stripped sequence.
  - At most **10** rows are listed. If there are more, the line `Other rows not listed: {count}` follows (O3).
  - OK is labelled `Remove and &Save`, Cancel `&Back to Editing`. Cancel is the default; Esc, Alt+F4 and the close button also mean Back to Editing (probe 2).
- **Remove and Save:** write the visible entries only (D5); on success close with `wx.ID_OK`. **Back to Editing:** nothing is written, the editor stays open, and the focus goes back to where it was (D7).
- With hidden rows, the box appears even when nothing else changed (U2.1). Without hidden rows, OK behaves as in D4.
- If the write fails after Remove and Save, the existing `Failed to save: {error}` box appears and the editor stays open. The hidden rows are still in the model, so the next OK asks again (O4).
- Dictionary Management still counts the visible entries only (U1, "字典管理的筆數不變"). Import, Export, Rename and Delete still keep every row; they copy, move or unlink bytes.
- Why one message box and not a list dialog: a task dialog's text is read in full by NVDA when it opens. It also gives the same keyboard behaviour (default button, Esc) as every other confirmation in the app. The cap keeps the box on the screen for a file whose header is wrong, where every row is hidden.

**D2. Duplicate check over the visible entries only (U1, U4).**

- `source_text_exists` ignores `PreservedDictionaryRow`s. Entries hidden by the filter still count, as today.
- F-4 D5 and its two tests go away. An entry whose source text equals a hidden row's is accepted. On OK the hidden row is listed by D1, so the user sees which row the new entry replaces.
- Text comparison stays exact (case-sensitive) on the stripped text.

**D3. "Changed" is a value comparison of the ordered entries (U2.1, U3.1).**

- `DictionaryEntryListModel` records the entries at load time and gets `has_changes() -> bool`. It is `True` when the current entries, in order, differ by value from the loaded ones (`DictionaryEntry` dataclass equality: text, braille, type).
- Hidden rows never count.
- Add then Delete of the same entry is no change. So is an Edit that keeps every value. Removing a row and adding it back at the end is a change, because the order is a change for conversion (the first duplicate rule wins).
- The filter is not a change.
- The snapshot stores copies, so a later in-place change of an entry object (none exists today) cannot hide a change.
- Rejected: a "dirty" flag set by every add/replace/remove. It would ask on Cancel and write on OK after an Add-then-Delete, which shows the user nothing changed.

**D4. OK writes only when needed (U2).**

`_on_ok`, in this order:

1. If there are hidden rows: D1. Its answer decides.
2. Else, if `has_changes()`: write (D5). On an error, show the existing message and stay open; otherwise `event.Skip()`.
3. Else: `event.Skip()` without writing. The file, its bytes and its modification time stay unchanged.

A missing file (deleted after Dictionary Management listed it) loads as empty. With no change, OK no longer creates it; with a change, OK creates it, as today.

**D5. The writer keeps the file's layout (U2.2 to U2.4).**

`save_dictionary_entries(path, entries, layout)` writes the entries only; after D1, hidden rows are never written. The layout comes from the load (D6).

- **BOM:** written when the loaded file started with one (`EF BB BF`), and not otherwise. A file DotExpress creates (`create_dictionary`, `ensure_default_dictionary`) still has none.
- **Header:** the header record as read, in its order. Any of `text`, `braille`, `type` that is missing is appended in that order. A file with no header record (empty) gets `text,braille,type`.
- **Rows:** for each entry, start from the record's fields as read:
  - an unchanged or edited row keeps every field, including extra columns, overflow fields beyond the header, and duplicated column names;
  - a new row starts empty;
  - pad with `""` to the header length;
  - then set the `text`, `braille` and `type` fields to the entry's values (stripped, type normalized; U2.2). If a column name appears twice, the value goes to the position `DictReader` reads, which is the last one. The other position keeps its value.
- An edited row keeps its extra fields: it is the same row with new values (O5).
- **Unchanged from today:** UTF-8, `\r\n` line ends, minimal quoting, atomic replace (`write_text_atomically`), blank lines dropped.

With `TRACE_CSV` (no BOM, header `text,braille,type`, no extra column), the bytes are exactly those of the pre-F-4 writer. The trace's expected CSV therefore holds (Test Plan C).

**D6. The loader keeps the layout and the record positions; the classification is unchanged.**

- `load_dictionary_rows` becomes a thin wrapper over a new `load_dictionary_file(path) -> LoadedDictionary(rows, layout)`. It keeps the classification (`_is_editable`) and the values of the rows exactly as `DictReader` gives them today.
- `DictionaryLayout` holds `has_bom: bool` and `header: tuple[str, ...]`.
- Each row carries its record's raw fields (`tuple[str, ...]`) and its start line:
  - on `PreservedDictionaryRow` as `line` and `fields`;
  - on `DictionaryEntry` as `fields`, declared `field(default=(), compare=False, repr=False)` (`line` is not needed there).
  So dataclass equality and every existing test and trace step are unaffected.
- The reader may switch to `csv.reader` to get raw fields and lines. It must then match `DictReader`'s values (probe 5): the first record is the header, `[]` records are skipped, a missing field is `""`, and a duplicated name takes its last value. A parity test runs both readers over the F-4/F-6 corpora (Test Plan A).
- `load_dictionary_entries` and the counts are unchanged. Read errors propagate as today.

**D7. Cancel, Esc and the close box ask only after a change (U3).**

- The editor binds `wx.EVT_BUTTON` for `wx.ID_CANCEL`. wx turns Esc and the close box into a click on that button (`wxDialogBase::OnCloseWindow` and the Esc char hook emulate the Cancel click), so one handler covers all three. The GUI items check this.
- No change: `event.Skip()`, and the dialog closes as today.
- With a change: a `wx.MessageDialog` (`wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING`):
  - caption `Unsaved Changes`;
  - message `Do you want to discard the changes you made to dictionary "{name}"?`, where `{name}` is the file stem;
  - OK `&Discard Changes`, Cancel `&Back to Editing`.
- Discard Changes: `event.Skip()` and the dialog closes, writing nothing. Back to Editing (also Esc, Alt+F4, the close button, Enter): the editor stays.
- OK/Cancel with custom labels rather than Yes/No, because a Yes/No task dialog ignores Esc and Alt+F4 (probe 2). An NVDA user who presses Esc on the question must land back in the editor, not in a box that does nothing.
- **Focus after a box that returns to the editor** (this one, D1's, and the save error): the editor remembers `wx.Window.FindFocus()` before showing the box. Afterwards it puts the focus back on that control if it is still a child of the editor (usually the OK or Cancel button, or the list when Esc was pressed there). Windows normally restores it alone; the explicit call covers the cases F-9 M-6 found where it did not.
- Delete does not ask (U3.2).
- A new helper in `ui/message_box.py`, `confirm_box(message, caption, ok_label, cancel_label, parent) -> bool`, builds both boxes. `message_box` is unchanged.

**D8. The duplicate check runs in the entry dialog's OK (U4).**

- `AddSymbolDialog(parent, entry=None, *, is_duplicate=None)`. `is_duplicate` is a `Callable[[str], bool]`. `_on_ok`: format checks first (unchanged); then, if `is_duplicate(entry.text)`:
  - show the existing `Source text "{identifier}" already exists.` with caption `Error` and `wx.OK | wx.ICON_ERROR`, parent the entry dialog (the same text, caption and style as today, so the golden trace's message records stay the same);
  - set the focus on the source text field and select all of it;
  - return without `Skip`, so the dialog stays open with every field as typed.
- The editor passes `lambda text: self._model.is_duplicate(text, editing=current_entry)` (D9).
- The model's `add`/`replace` keep raising `DuplicateEntryError` as a backstop, and the editor keeps its handler. No UI path reaches it any more.

**D9. Identity for Delete and Edit (U5.2, P2-2 Q4).**

- `remove` deletes the row that *is* the selected visible entry (`is`). This is the same lookup `replace` already uses.
- `replace` gives the new entry the replaced row's raw `fields` (D5), so its extra columns survive.
- `is_duplicate(text, editing=None)` is `source_text_exists(text, exclude_entry=editing)`, with one addition: an Edit that keeps the entry's own source text (`text == editing.text`) is never a duplicate. Today, with two identical rows `a`, neither can be edited without changing its text, because the other one "already exists" (Q4, first half). The edit adds no new duplicate, so it is accepted (O6).
- **Selection.** After Add and Replace, the new entry is selected by identity. With the Q4 change an edited twin can equal the other twin, and equality would jump to the first one. After Delete and a filter change, the selection is restored by equality, as today. Probe 1 shows the golden trace pins this, and it lands on the remaining twin.

**D10. Case-only rename (U5.1, F-W6).**

- `rename_dictionary`: if the destination exists and `os.path.samefile(source, destination)` is `True`, it is the same file under another case; rename it with `Path.rename` (probe 3). A destination that exists and is another file is still refused with `FileExistsError` (case-sensitive file systems).
- An identical name stays a no-op (`name_prompt.py`).
- The active name and `config.json` follow through the existing `plan_dictionary_state_after_rename` (`active_name == previous_name`). A presenter test pins it, for the selected dictionary and for another one.
- The default dictionary still cannot be renamed. `default` to `Default` is refused by the reserved-name check before any file operation.

**D11. A locked Import source gets F-6's reason (U5.3, M-4).**

- `import_dictionary` wraps a `PermissionError` raised while opening or reading the **source**, in `validate_dictionary_csv` or in the copy, in a new `DictionaryImportSourceError(error)`. That exception is not an `OSError`. It keeps the original as `.error` and `__cause__`.
- The presenter catches it before `OSError`, and shows the existing `Failed to import dictionary: {error}` with `{error}` = `describe_dictionary_read_error(exc.error)` (CANNOT_OPEN). This is the same pattern F-6 D9 uses for NOT_UTF8 and INVALID_CSV.
- Errors writing the copy into the dictionary folder, and other `OSError`s from the source (for example `FileNotFoundError`), keep today's message (O7).

**D12. Read before building the editor (U5.4, M-5).**

- `DictionaryEntriesDialog.__init__(parent, dictionary_path, model=None)`. Without `model`, it loads **before** `super().__init__`, so a read error leaves no native dialog (this flips the Q8 pin).
- `gui.on_open_dictionary_management` loads the model itself, then creates the dialog:
  - **Read error:** log with `log_dictionary_read_error` and show `describe_unreadable_dictionary(name, error)`. Messages, caption and icon are as today.
  - **Error while building the dialog:** log `"Unexpected error while opening the dictionary editor"` with the traceback to `dotexpress.gui` (`gui.log`). Show the new `Failed to open the dictionary editor: {error}` (caption `Error`, `wx.OK | wx.ICON_ERROR`).
- The constructor calls `self.Destroy()` when building fails after `super().__init__`, then re-raises, so nothing is left behind in that case either.

**D13. Conversion ignores the rows the editor hides (U6, #8).**

- In `LoadedDictionaryRules.from_paths`, a dictionary row is skipped when `source.strip()` is empty, or when `type_ == "Bopomofo"` and `processing(target.strip())` raises.
- `type_` is the raw type. The editor's `normalize_entry_type` maps only the exact string `Bopomofo` to Bopomofo, so the two agree.
- `processing` is the injected parser, `normalize_zhuyin_sequence` in production. So `dictionary_rules.py` still imports nothing from `dictionaries`, and the criterion equals `_is_editable` on the stripped values.
- A parity test checks that for a corpus of rows, "skipped by conversion with `normalize_zhuyin_sequence`" equals "hidden by `load_dictionary_rows`" (Test Plan F).
- A row that stays is converted exactly as today (raw source, raw target, the same fallback when `processing(target)` raises on the raw value). Only hidden rows change the output.
- The golden case "Bopomofo row with a processing that raises" flips: the row is now skipped.
- `translation_golden.json` is not affected: its one dictionary row is valid.

**D14. First-tone final syllables (pending the user's answer to O1).**

The spec recommends (b) of O1:

- for a `Bopomofo` row, the canonical sequence is `braille.strip()`;
- if that does not parse but `braille.strip() + " "` does, the canonical sequence is `braille.strip() + " "`: the final first-tone space is kept;
- this applies in the loader's classification and value, in `validate_dictionary_entry` and `AddSymbolDialog.get_entry`, and in D13's skip test.

Effects:

- such rows are shown, edited, saved with their tone space, and converted as today;
- typing `ㄓㄨㄥ ㄒㄧㄣ` in the entry dialog is accepted and stored as `ㄓㄨㄥ ㄒㄧㄣ `.

If the user chooses (a), D14 is dropped. Such rows then stay hidden, are listed in the D1 box with the reason "not valid", are removed on Remove and Save, and are ignored by conversion.

**D15. Strings and catalogs.** The 11 strings of the table below. `generate-pot.bat`, `msgmerge`, then the msgstr values, then `msgfmt --check --statistics`: all translated, 0 fuzzy. `POT-Creation-Date` stays fixed. Check that `msgmerge` did not mark a new msgid fuzzy by pairing it with an old one, for example `&Discard Changes` with `Close &Without Saving`, or `Unsaved Changes` with `Cannot Save Document`.

## Behavior per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Open editor | the native dialog first, then the file is read (Q8) | the file is read first; a read error shows F-6's reason and creates no dialog (D12) |
| OK, no change, no hidden rows | rewrites the file (strip, General, no BOM, extra columns dropped) | writes nothing (D4) |
| OK, no change, hidden rows | rewrites, keeping hidden rows in place (F-4) | the D1 box; Remove and Save writes without them; Back to Editing keeps the editor open |
| OK after changes | rewrite in the normalized form | rewrite with strip/General, keeping the header, extra columns and BOM (D5); hidden rows: D1 box first |
| Cancel / Esc / close box | closes, edits lost silently | no change: closes; changed: the D7 box, default Back to Editing |
| Delete | removes the first equal row, no question | removes the selected row (D9), no question (U3.2) |
| Add/Edit duplicate | entry dialog closes, then an error box; input lost | error box inside the entry dialog; input kept; focus on the source text, selected (D8) |
| Add over a hidden row's text | refused (F-4 D5) | accepted (D2); the hidden row is listed on OK |
| Edit a twin keeping its text | refused as a duplicate | accepted (D9) |
| Conversion | uses whitespace-only texts and invalid Bopomofo rows | ignores them (D13) |
| Rename `alpha` to `Alpha` | "already exists" | renamed; `config.json` follows when selected (D10) |
| Import a locked file | `Failed to import dictionary: [Errno 13] ...` | `Failed to import dictionary: The file cannot be opened. ...` (D11) |
| Editor build error | described as "cannot be read"; hidden dialog leaks | general failure message, traceback in `gui.log`, nothing left (D12) |
| Dictionary Management count | visible entries | unchanged |

Example: `dict_badbopo.csv` (`text,braille,type` / `臺北,⠞⠺,Braille` / `肚子,ㄉㄨˋ|ㄗ˙,Bopomofo` / `數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo`, CRLF, no BOM). OK shows:

```text
字典「dict_badbopo」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：

第 3 列：「肚子」的注音「ㄉㄨˋ|ㄗ˙」格式不正確
第 4 列：「數學」的注音「ㄕㄨˋ ㄒㄩㄝˊ」格式不正確

要移除這些列並儲存字典嗎？
```

Remove and Save leaves `text,braille,type\r\n臺北,⠞⠺,Braille\r\n`. Converting `肚子數學` gives the same output before and after the save, because neither row is used any more (D13).

## Design per File

### `client/dictionaries/entries.py` (tabs)

- `DictionaryLayout(has_bom: bool = False, header: tuple[str, ...] = ())` and `LoadedDictionary(rows, layout)`, both frozen dataclasses.
- `PreservedDictionaryRow` gains `line: int = field(default=0, compare=False)` and `fields: tuple[str, ...] = field(default=(), compare=False)`, plus a `reason` property (`"no_source_text"` or `"invalid_bopomofo"`). `DictionaryEntry` gains `fields` (`compare=False`, `repr=False`).
- `load_dictionary_file(path)` (D6). `load_dictionary_rows` returns `load_dictionary_file(path).rows`. `load_dictionary_entries` is unchanged.
- `save_dictionary_entries(path, entries, layout=DictionaryLayout())` (D5). With the default layout it writes exactly today's bytes for entries, so callers that pass no layout keep their output.
- D14 (if adopted): `canonical_bopomofo(braille) -> str | None`, used by `_is_editable`, the loader and `validate_dictionary_entry`.

### `client/dictionaries/entry_list_model.py` (tabs)

- It stores `_layout` and `_loaded_entries` (copies).
- New: `has_changes()`, `hidden_rows` (a tuple of `PreservedDictionaryRow` in file order) and `is_duplicate(text, editing=None)`.
- `source_text_exists` skips preserved rows (D2). `remove` works by identity. `replace` copies `fields`. `add` and `replace` select by identity (D9). `save(path)` writes the entries with the layout and **no** preserved rows (D1).
- After a successful save, the snapshot is the saved entries and the hidden rows are dropped from the model. The editor closes then anyway; this keeps the model consistent for tests.
- The import list stays `{__future__, collections.abc, dataclasses, pathlib, dictionaries.entries}` (`test_model_imports_no_ui_or_translation_module`).
- The module docstring's comparison rules are updated.

### `client/dialog.py` (tabs)

- `AddSymbolDialog`: the `is_duplicate` keyword (D8). The focus and selection go to `identifier_ctrl` after a duplicate.
- `DictionaryEntriesDialog`:
  - the `model` keyword and loading before `super().__init__` (D12);
  - `Destroy` on a build failure;
  - the Cancel handler (D7);
  - `_on_ok` (D4, D1);
  - `_confirm_hidden_rows()` builds the D1 text, with the row lines from `hidden_rows`, the cap and the overflow line;
  - focus restore after a box;
  - `_open_entry_dialog` passes `is_duplicate`. The editor's own duplicate box stays only as the backstop.

### `client/ui/message_box.py` (4 spaces)

- `confirm_box(message, caption, ok_label, cancel_label, parent=None) -> bool`: `wx.MessageDialog(parent, message, caption, wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING)`, `SetOKCancelLabels(ok_label, cancel_label)`. It returns `ShowModal() == wx.ID_OK`.

### `client/gui.py` (tabs)

- `on_open_dictionary_management`: load, then build, with the two guards of D12. The logger is the existing `dotexpress.gui`.

### `client/dictionaries/manager.py` (4 spaces)

- `rename_dictionary`: the `samefile` branch (D10).
- `DictionaryImportSourceError` and the wrap in `import_dictionary` (D11).

### `client/dictionaries/presenter.py` (tabs)

- `import_from_file` catches `DictionaryImportSourceError` before `OSError` (D11). `rename` is unchanged; it gets a test.

### `client/conversion/text/dictionary_rules.py` (4 spaces)

- The skip test of D13 in `from_paths`. The docstring states that the rule equals the editor's.

### Catalogs

- `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `.mo` (D15).

### Not changed

- `read_problems.py`;
- `name_prompt.py`;
- `translation/dictionary_state.py`;
- `DictionaryManagementDialog`;
- `validate_dictionary_csv` (except for being wrapped);
- `shared/atomic_write.py`;
- `brailleTables/`, liblouis, and the two fixtures.

## What Stays Identical

- The editor's layout, title, columns, filter, Add/Edit/Delete buttons, the selection after a filter and after Delete, and the format messages of the entry dialog.
- The duplicate message's text, caption and icon.
- The save error message, and staying open after it.
- `Failed to import dictionary: {error}` for every case except D11's.
- Dictionary Management: counts, the F-6 reason row, every other action and message.
- Conversion of every row the editor shows.
- The bytes written for a file with no BOM, the header `text,braille,type` and no extra columns.
- `translation_golden.json` (`e67d95a1...`) and `dictionary_entries_trace.json` (`f493da52...`).

## User-Visible Strings

| # | msgid | zh_TW msgstr | Where |
| --- | --- | --- | --- |
| 1 | `Remove Rows That Cannot Be Shown` | `移除無法顯示的列` | D1 caption |
| 2 | `Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?` | `字典「{name}」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：\n\n{rows}\n\n要移除這些列並儲存字典嗎？` | D1 message |
| 3 | `Row {line}: no source text` | `第 {line} 列：沒有來源文字` | D1 row line |
| 4 | `Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid` | `第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確` | D1 row line |
| 5 | `Other rows not listed: {count}` | `另有 {count} 列未列出` | D1, more than 10 rows |
| 6 | `Remove and &Save` | `移除並儲存(&S)` | D1 OK button |
| 7 | `&Back to Editing` | `返回編輯(&B)` | D1 and D7 Cancel button |
| 8 | `Unsaved Changes` | `尚未儲存的變更` | D7 caption |
| 9 | `Do you want to discard the changes you made to dictionary "{name}"?` | `要放棄對字典「{name}」所做的變更嗎？` | D7 message |
| 10 | `&Discard Changes` | `放棄變更(&D)` | D7 OK button |
| 11 | `Failed to open the dictionary editor: {error}` | `無法開啟字典編輯器：{error}` | D12 |

msgids: 369 + 11 = **380**. The quoting follows `Dictionary "{name}" already exists.` / `字典「{name}」已存在。`. The access-key style follows F-5's `重試(&R)`.

Existing messages newly reachable:

- `Source text "{identifier}" already exists.` from the entry dialog (D8);
- `Failed to import dictionary: {error}` with the CANNOT_OPEN reason (D11).

## Accessibility (NVDA)

| Box | Caption read first | Focus when it opens | Esc / Alt+F4 | Focus after |
| --- | --- | --- | --- | --- |
| D1 hidden rows | 移除無法顯示的列 | 返回編輯 (default) | Back to Editing | Remove and Save: the editor closes, the focus returns to the main window as after OK today. Back to Editing: the control focused before (D7) |
| D7 discard | 尚未儲存的變更 | 返回編輯 (default) | Back to Editing | Discard: the editor closes. Back: the control focused before (usually Cancel, or the list/filter when Esc was pressed there) |
| D8 duplicate (inside the entry dialog) | 錯誤 | 確定 | closes the box | the 來源文字 field, its text selected; NVDA reads the field name and the selected text |
| Save error (existing) | 錯誤 | 確定 | closes the box | the control focused before |
| D11 import | 錯誤 (existing) | 確定 | closes | unchanged (Dictionary Management) |
| D12 failure | 錯誤 | 確定 | closes | the main window |

- Task dialogs present their full text to NVDA when they open (F-5, F-9 measurements). The row lines are short and start with the row number, so NVDA reads a usable list.
- The default button is always the one that loses nothing.
- Every button has an access key: S, B, D.

## Test Plan

TDD: each step's tests are written first and fail for the stated reason. Indentation follows each file (`test_dictionary_entry_list_model.py`, `test_dictionary_name_prompt.py`: tabs; `test_dictionary_entries_dialog.py`, `test_dictionary_entries.py`: 4 spaces; check each file). Temporary folders only. Tests that make the code log use `assertLogs` or `isolate_file_logs`, so nothing reaches `client/log/`. Non-ASCII test data uses `\u` escapes, written by script where surrogates are involved (HANDOFF §2).

### A. Loader and writer (`tests/test_dictionary_entries.py`)

1. The layout records the BOM (with and without) and the header as read, including an extra column, a duplicated name, a missing `type`, and an empty file.
2. Start lines: header = 1; a blank line skipped but counted; a multi-line quoted field; a hidden row after it has the right line.
3. Parity: for the F-4 and F-6 corpora plus the cases of 1 and 2, the new loader's (text, braille, type, class) equal `DictReader`'s today.
4. Writer:
   - BOM kept and not added;
   - header order kept and missing required columns appended;
   - an unchanged row keeps its extra and overflow fields;
   - a new row has empty extras;
   - an edited row keeps its extras;
   - a short row is padded;
   - strip and `General` applied;
   - a duplicated name gets the value at the last position;
   - a default layout gives today's bytes;
   - hidden rows are never written.
5. `PreservedDictionaryRow.reason` for a blank text, a whitespace-only text and an invalid sequence.
6. (D14, if adopted) `canonical_bopomofo`: `ㄇㄚ` becomes `ㄇㄚ `, `ㄇㄚ ` stays, `ㄉㄨˋㄗ˙` stays, `ㄉㄨˋ|ㄗ˙` is `None`. The loader shows `中心,ㄓㄨㄥ ㄒㄧㄣ ,Bopomofo`.

### B. Model (`tests/test_dictionary_entry_list_model.py`)

1. `has_changes`:
   - `False` after load, after a filter, after Add+Delete of the same entry, and after an Edit to equal values;
   - `True` after a value change, after a removal, and after a reorder (remove and re-add);
   - hidden rows never count.
2. `remove` by identity: in `[a, b, a]`, removing visible index 2 removes the third row. The saved order is `a, b`, with the first `a`'s fields.
3. `replace` keeps `fields`. `add` has empty `fields`.
4. D2: a preserved row's text is not a duplicate. **Remove** the two F-4 D5 tests (replaced by this one).
5. D9: an Edit of a twin keeping its text is not a duplicate. An Edit of another row to that text is. Add and Replace select by identity; filter and Delete select by equality.
6. `hidden_rows` are in file order, with lines. `save` drops them and keeps the layout.

### C. Editor (`tests/test_dictionary_entries_dialog.py`, the `_EditorHarness`)

1. OK without change: no write, file bytes and `st_mtime_ns` unchanged, `Skip`. **Flip** the Q2 pin. Adapt the tests that press OK without a change and expect a write (`:852`, `:1333`): they make a change first, or expect no write.
2. OK after a change: written (BOM file stays BOM; extra column kept); `Skip`.
3. OK with hidden rows: `confirm_box` is called with the exact zh_TW caption, message and labels (two rows; eleven rows: 10 lines + `另有 1 列未列出`).
   - Remove and Save: written without hidden rows, `Skip`.
   - Back to Editing: no write, no `Skip`, focus restored.
4. Save error after Remove and Save: the existing message, open, and the next OK asks again.
5. Cancel handler bound; no change: `Skip`, no box. **Flip** the Q5 pin.
   - Changed: the D7 box with exact texts; Discard: `Skip`, no write; Back: no `Skip`, focus restored.
6. Delete: no box (keep that half of the Q5 Delete pin; flip only the identity part, D9).
7. Duplicate in Add and Edit: the box comes from the **entry dialog** (parent), the entry dialog stays open, the input is kept, `identifier_ctrl` gets focus and `SelectAll`. **Flip** both Q6 pins. The harness's fake entry dialog gets a scripted second answer (fix the text, or cancel).
8. Q4: the twin Edit keeping its text is accepted; Delete of the second twin removes the second. **Flip** both Q4 pins.
9. Construction:
   - with `model=` no file is read;
   - without it, a `UnicodeDecodeError` is raised **before** the native `__init__`. **Flip** the Q8 pin;
   - a failure in `_build_ui` calls `Destroy` and re-raises.
10. **Golden trace.** The replay answers the D1 box with Remove and Save and removes that box's record from the OK step's log before comparing. It asserts that `_TRACE_KEPT_ROWS` are **absent** from the saved CSV (the F-4 strip goes away). The fake entry dialog runs `is_duplicate` and, on a duplicate, records the same `MessageBox` and then cancels (the recorded user typed once). `dictionary_entries_trace.json` is not modified; its sha256 stays `f493da52...`.

### D. Entry dialog (`tests/test_dialog_validation.py`)

The order is format check first, then duplicate. Without `is_duplicate`, behaviour is as today. On a duplicate there is no `Skip`, and the message parent is the entry dialog.

### E. Rename, import, frame

- `tests/test_dictionary_name_prompt.py`: F-W6 passes. A different existing file under another case is refused (patch `os.path.samefile` to `False`).
- `tests/test_dictionary_manager.py`: a `PermissionError` from the source (patched `open` for the source path) gives `DictionaryImportSourceError`; one writing the destination stays a `PermissionError`.
- `tests/test_dictionary_presenter.py`:
  - a case-only rename of the active dictionary calls `set_active_name("Alpha")`; of another one, it does not;
  - the import source error shows `匯入字典失敗：無法開啟檔案。…` (the CANNOT_OPEN text); a destination error keeps the raw text.
- `tests/test_gui_document_flows.py`:
  - a read error shows F-6's text and creates no editor;
  - a build error shows string 11 and logs a traceback (`assertLogs`);
  - adapt `test_editor_that_cannot_read_its_dictionary_shows_the_reason`.

### F. Conversion (`tests/test_conversion_text_dictionary_rules.py`)

- Whitespace-only text (`"  "`, U+3000) is not a rule.
- An invalid Bopomofo row is not a rule (injected raising `processing`, and the real parser). **Flip** the golden case "processing that raises".
- A valid row's output is byte-identical.
- Parity: over a corpus (the F-4 cases, `dict_badbopo`, whitespace variants, unknown and lower-case types, and D14 cases), "skipped by `from_paths` with `normalize_zhuyin_sequence`" equals "a `PreservedDictionaryRow` from `load_dictionary_rows`".

### G. Catalog (`tests/test_i18n.py`)

The 11 msgstr values; the AST scan equals the catalog (380).

### Mutation check (plan; each must be caught)

1. `has_changes` always `True`;
2. `has_changes` ignoring order;
3. `has_changes` counting hidden rows;
4. the D1 box shown without hidden rows;
5. Remove and Save writing preserved rows;
6. Back to Editing still writing;
7. `CANCEL_DEFAULT` dropped (OK default);
8. the Cancel handler skipping without asking;
9. asking without a change;
10. the duplicate check including preserved rows (D5 back);
11. the duplicate check not excluding the edited entry;
12. the twin-keeps-text exception dropped;
13. the entry dialog closing on a duplicate (`Skip`);
14. focus not set to the source field;
15. `remove` by equality;
16. `replace` dropping `fields`;
17. BOM dropped;
18. BOM always written;
19. extra columns dropped;
20. header reordered;
21. a start line off by one;
22. the cap at 9 or 11;
23. conversion keeping whitespace-only texts;
24. conversion validating the raw (unstripped) target;
25. `rename_dictionary` without `samefile` (overwrites a distinct file);
26. the import wrap also catching destination errors;
27. the frame creating the dialog before loading.

### Counts

About 60 new tests and 8 flipped or removed (A 16, B 14, C 14, D 3, E 8, F 6, G 1). The plan fixes the exact `Ran`. On Windows: `FAILED (skipped=7)` with **no error**, because F-W6 is fixed.

## Migration Steps (each step one green commit, red first)

1. `fix: allow a case-only dictionary rename (F-11, F-W6)`: D10, tests E.
2. `fix: explain a locked dictionary import source (F-11, F-6 M-4)`: D11.
3. `fix: read the dictionary before building its editor (F-11, F-6 M-5)`: D12, string 11, catalogs.
4. `fix: keep the BOM, header and extra columns of a dictionary (F-11)`: D5, D6; tests A, C2.
5. `fix: delete and edit the selected dictionary entry (F-11, #9)`: D9; tests B2, B3, B5, C8.
6. `fix: report a duplicate source text inside the entry dialog (F-11, P2-2 Q6)`: D2, D8; tests B4, C7, D, C10 (entry part).
7. `fix: save a dictionary only after a change and ask before discarding changes (F-11, P2-2 Q2, Q5)`: D3, D4, D7, strings 7 to 10, catalogs.
8. `fix: confirm and remove dictionary rows the editor cannot show (F-11, #7)`: D1, strings 1 to 6, catalogs; C3, C4, C10 (OK part).
9. `fix: ignore hidden dictionary rows when converting (F-11, #8)`: D13; tests F.
10. If O1 is (b): `fix: keep the tone space of a first-tone final syllable (F-11)`: D14.

Each commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and stages explicit paths only.

## Acceptance Criteria

Run on Windows from `client/` with `$PY`, with the runtime copied as in F-3 plan Task 0.

1. Full suite: no failure and no error (F-W6 fixed); `Ran` as the plan states.
2. Focused: `$PY -m unittest tests.test_dictionary_entries tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog tests.test_dialog_validation tests.test_dictionary_name_prompt tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_conversion_text_dictionary_rules tests.test_gui_document_flows tests.test_i18n -v` passes.
3. `grep -rn "KNOWN BUG (P2-2 spec, Q[24568])" client/tests` prints nothing.
4. Catalogs: 11 new msgids with the msgstr of the table; `msgfmt --check --statistics` all translated, 0 fuzzy; the AST scan equals the catalog (380); `POT-Creation-Date` unchanged.
5. Both fixtures' sha256 unchanged.
6. App data untouched:
   - the main checkout's `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` have the same sha256 before and after;
   - the worktree gets no `client/log/`, `client/workspace/` or `client/config.json`.
7. `git diff main --stat` touches only the files of "Design per File", the tests above, and the spec, plan and history files.
8. The mutation check above.
9. The packaged GUI verification below, with results in the implementation's history folder.

## Windows Verification (packaged build)

Build and process rules as in F-9:

- the main checkout's `client\.venv\Scripts` first on `PATH`, then `scripts\build-dotexpress.bat`;
- check in `PYZ-00.toc` that `dialog.py`, `dictionaries\*.py`, `ui\message_box.py`, `conversion\text\dictionary_rules.py` and `gui.py` come from the worktree;
- the exe goes to `D:\dxtest\N-f11\`; "Before" is `D:\dxtest\N-f9b`;
- each item runs in a new `D:\dxtest\auto<item>-f11` folder with a copy of the exe;
- only processes under those folders are ended (`taskkill /T`).

Scripts go to the history folder `auto/`. They reuse `2026-10-09-03-windows-verification/auto/` (`dx.py`, `dicts.py`, `lock.py`) and `2026-10-10-01-f5-save-failure-handling/auto/f5gui.py` without editing. Task dialogs are read through UIA. **No script reads or writes the clipboard**; text goes in with `set_edit_text` or typed keys. Each item records the sha256, size and `st_mtime_ns` of every dictionary file before and after.

| # | Steps | Expected after F-11 | Before |
| --- | --- | --- | --- |
| 95 | Import `dict_badbopo.csv`; open the editor; OK | the D1 box: caption, the text of "Behavior per Path" (two row lines), buttons 移除並儲存(S) / 返回編輯(B), focus on 返回編輯. Esc: editor open, file unchanged, focus back on 確定. OK then Enter: same. OK, then 移除並儲存: file `text,braille,type\r\n臺北,⠞⠺,Braille\r\n`, no BOM; Dictionary Management `1` | no box; the file is unchanged (F-4) |
| 96 | Select `dict_badbopo` in Settings; convert `肚子數學` before 95's 移除並儲存 and again after it | both outputs equal the `default` dictionary's output for the same text (no rule used) | the two Bopomofo rules are used (`⠙⠌⠐...`) |
| 97 | `extra.csv` (BOM, header `text,note,braille,type`, a row with leading spaces and type `Custom`, CRLF): open, OK | no box, sha256 and `st_mtime_ns` unchanged | rewritten: no BOM, `note` dropped |
| 98 | `extra.csv`: Edit row 1's braille, Add a row, OK; the same on `bom_lf.csv` (2026-10-09-03 data) | BOM kept; header `text,note,braille,type`; `note` kept on the old rows and empty on the new one; every row stripped and `Custom` written as `General`; `bom_lf.csv` stays without BOM, CRLF | BOM and `note` dropped |
| 99 | Open `alpha` (two rows); Add `x`; press Esc; then Cancel; then Alt+F4 | each time the D7 box: caption, message naming `alpha`, buttons 放棄變更(D) / 返回編輯(B), focus on 返回編輯. Esc in the box: editor open, `x` still listed. Finally 放棄變更: editor closed, file unchanged | the editor closes at once, `x` lost |
| 100 | Open `alpha`; Esc. Open again; Delete row 1 (no box); Cancel | first Esc closes at once, no box; Delete asks nothing; Cancel shows the D7 box | Cancel closes at once |
| 101 | `twins.csv` (`text,braille,type,note` / `a,⠁,General,first` / `b,⠃,General,` / `a,⠁,General,third`): Add `b` | the error box 來源文字「b」已存在。 with the **entry dialog** as owner; after 確定 the entry dialog is still open with `b` and `⠃` kept, focus in 來源文字 with `b` selected (UIA `TextPattern` selection); change to `c`, OK: added | the entry dialog closes, then the error; input lost |
| 102 | `twins.csv`: (1) select row 3, Edit, change the braille to `⠉`, OK; then Cancel and 放棄變更. (2) Open again, select row 3, Delete, OK | (1) the Edit is accepted (row 3 shows `a`, `⠉`). (2) The file is `a,⠁,General,first` / `b,⠃,General,`: the selected row went, and row 1 kept its `note` | (1) refused as a duplicate; (2) the file keeps `third` and loses `first` (the first equal row was removed) |
| 103 | `dict_badbopo`: Add `肚子` / `ㄉㄨˋㄗ˙` / 注音; OK; 移除並儲存 | Add accepted; the D1 box lists rows 3 and 4; file: `臺北` and the new `肚子,ㄉㄨˋㄗ˙,Bopomofo` | Add refused (F-4 D5) |
| 104 | Select `alpha` in Settings; Dictionary Management, Rename to `Alpha` | no message; the list shows `Alpha` selected; `dictionary\Alpha.csv`; `config.json` `selected_dictionary` is `Alpha`; a conversion still uses it | 字典「Alpha」已存在。 |
| 105 | Lock `src.csv` share-none (`lock.py`); Import it | `匯入字典失敗：無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。`; no new file in `dictionary\` | `[Errno 13] Permission denied: ...` |
| 106 | (D14, if adopted) `tone1.csv` with `中心,ㄓㄨㄥ ㄒㄧㄣ ,Bopomofo`; open; Add `媽` / `ㄇㄚ`; OK | row shown; the Add is accepted; the file holds `中心,ㄓㄨㄥ ㄒㄧㄣ ,Bopomofo` and `媽,ㄇㄚ ,Bopomofo`; converting `中心媽` uses both | the row is hidden; the Add shows the format error |

Re-run with new expectations (the scripts set a change first where a write is the point):

- **23:** `dict23`, OK without change: no write. With an Edit: written, BOM as before.
- **24:** BOM files: OK without change: unchanged. After an Edit: the BOM is **kept**.
- **25 to 29:** each first edits one row so that OK writes; then the same lock, attribute and ACL checks; the expected `SAVED` state keeps the file's BOM.
- **35:** 35a gets the D1 box (Back to Editing, then Remove and Save); 35b's Add is accepted (D2); 35c and 35d follow from that.

The F-6 items 42 to 51 are unchanged; 44 and 47 are re-run because the editor now loads first.

**Manual for the user (item 107, NVDA):** with `N-f11` and NVDA running:

1. Item 95's box: is the whole list read, and is the focus on 返回編輯?
2. Item 99's box: Esc returns to the editor; where is the focus?
3. Item 101: after the duplicate message, NVDA reads 來源文字 and the selected text.
4. After 移除並儲存, the main window gets the focus.

## Risks

- **Conversion output changes for existing dictionaries** (medium, intended by U6). Whitespace-only rules and invalid Bopomofo rules stop working. The D1 box lists them on the next OK. The release notes should say so.
- **First-tone final rows (O1)** (medium). With (a), valid-looking rows ending in a first-tone syllable are ignored by conversion and offered for removal as "not valid". The recommended (b) avoids this, but it adds scope and one more behaviour change (the entry dialog accepts a sequence without its final space).
- **The trace replay is adapted, not re-recorded** (low). The replay strips the D1 box record and answers it. A bug in that adaptation could hide a regression of the OK step. Test C3 checks the OK step on its own.
- **Selection rule split** (low). Identity after Add/Replace and equality after Delete/filter. It only differs with identical rows. It is kept because the golden trace pins equality (probe 1).
- **`csv.reader` parity** (low). A divergence from `DictReader` would change which rows are hidden. Test A3 compares both on every corpus.
- **Task dialog text length** (low). With 10 row lines and long source texts, the box can be tall. The cap bounds it.
- **Changing wx Esc handling** (low). If wx stops turning the close box into a Cancel click, the box would not ask. Items 99 and 100 check Esc, Cancel and Alt+F4 on the packaged build.

## Open Questions

**Needs the user's decision (user-visible):**

- **O1. Bopomofo rows whose last syllable is first tone.** Today the editor hides them, because its strip removes the tone space (probe 4). Conversion uses them. The entry dialog cannot enter them. Under U1 and U6 as written:
  - **(a)** they become ignored by conversion and are listed for removal on OK as "not valid";
  - **(b) (recommended)** the strip keeps a final first-tone space (D14). They are shown, edited, saved with the space and converted as today, and typing them without the trailing space is accepted.
  The plan can start with steps 1 to 9; step 10 waits for this answer.

**Decided by orchestrator with the recommended default; user may override before merge:**

- **O2.** "Changed" compares the ordered entry values with the loaded ones, not a dirty flag (D3).
- **O3.** The D1 box lists at most 10 rows, then `Other rows not listed: {count}` (D1).
- **O4.** After Remove and Save fails, the next OK asks again (D1).
- **O5.** An edited row keeps its extra-column values (D5). U2.3 covered only unchanged and new rows.
- **O6.** Editing one of two identical rows while keeping its source text is not a duplicate (D9, completing P2-2 Q4).
- **O7.** Only a `PermissionError` from the Import source gets the friendly reason. Other source `OSError`s and destination errors keep the raw text (D11).
- **O8.** Hidden-row line numbers count file lines with the header as line 1 (D1).
- **O9.** Line ends stay CRLF and quoting stays minimal when writing (D5). The user decided the BOM only.
- **O10.** The selection after Delete and filter keeps the equality rule (D9).
- **O11.** A missing dictionary file is no longer created by an unchanged OK (D4).

## User-Visible Defaults Introduced by This Spec (not decided by the user)

These were not in U1 to U6. Each one is a one-line change if the user prefers otherwise:

1. **Button labels of the hidden-rows box:** 移除並儲存(&S) / 返回編輯(&B), rather than the 是 / 否 of `task.md`'s wording. A Yes/No task dialog cannot be closed with Esc (probe 2).
2. **The default button of the hidden-rows box** is 返回編輯.
3. **Captions:** 移除無法顯示的列 and 尚未儲存的變更. **Message texts:** strings 2, 3, 4 and 9, including the dictionary name in both boxes.
4. **Access keys** (S), (B), (D) on the buttons, following F-5's `重試(&R)`.
5. **Row number = file line**, header = line 1 (O8). **The row line includes the invalid sequence** as well as the source text.
6. **At most 10 listed rows** and the `另有 {count} 列未列出` line (O3).
7. **Focus restore** after Back to Editing to the control focused before the box (D7).
8. **The generic editor failure text** `無法開啟字典編輯器：{error}` (D12).
9. **Twin Edit accepted** (O6), and **identity selection after Add/Replace** (D9).
10. **Re-asking after a failed Remove and Save** (O4).

## Out of Scope / Follow-ups

- A BOM for dictionaries DotExpress creates (U2.4 follow-up).
- Showing hidden rows in the editor, or counting them in Dictionary Management.
- Esc in the existing Yes/No confirmations (`Confirm Delete Dictionary` and others): a Yes/No task dialog ignores Esc (probe 2). This is pre-existing; F-12.
- Localization of other messages and the F-6 O5 conversion error wording (F-12).
- F-10 (UEB line breaks, `$` escapes).
- Mixed line ends or quoting style of a hand-edited file are not preserved (O9).
- Duplicate source texts that already exist in a file are not reported. Conversion keeps using the first.
