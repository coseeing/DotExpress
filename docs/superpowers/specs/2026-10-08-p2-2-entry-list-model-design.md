# Dictionary Entry List Model (P2-2) Design

## Goal

Move the data logic of the dictionary entries editor out of the wx dialog into a wx-free model, so it can be tested without stubbing widgets. This is roadmap task P2-2 in `storage/refactor.md` (section 6.3), covering finding S-4 (`SpeechSymbolsDialog` mixes model and view; the CWD-relative default path).

Concretely:

- New wx-free module `client/dictionaries/entry_list_model.py` with `DictionaryEntryListModel`: the full entry list, the filter text, the visible (filtered) list, duplicate detection, add/replace/remove, the selection to show after each change, the virtual-list cell text, and load/save through `dictionaries/entries.py`.
- The editor dialog becomes a Supervising Controller: it owns the widgets, reads the filter text and the selected row from them, calls the model, and renders what the model returns (`SetItemCount`, `Refresh`, `Select`, `Focus`, button states, message boxes).
- The dialog is renamed `SpeechSymbolsDialog` -> `DictionaryEntriesDialog` in a separate, purely mechanical last step (decision D7).
- `dictionary_path` becomes a required constructor parameter (the `Path("data") / "dictionary.csv"` default is dropped; decision D6).

This is a behavior-preserving refactor. Every string, message, message order, list-control call order, selection, focus, button state and saved CSV byte stays the same. No msgid changes (353). The P1-5 golden fixture `client/tests/fixtures/translation_golden.json` (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`) does not change.

## Current State (verified 2026-10-08 on `refactor/p2-2-entry-list-model`, HEAD `33dc34d`, P0-*, P1-* and P2-1 merged)

Indentation: `dialog.py`, `gui.py` and `dictionaries/*.py` use tabs; `tests/test_speech_symbols_dialog.py`, `tests/test_dialog_validation.py`, `tests/test_gui_document_flows.py` and `tests/wx_stub.py` use 4 spaces; `tests/test_dictionary_entries.py` uses tabs.

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 889 tests`, `FAILED (failures=1, skipped=9)`; the failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. The shuffle harness (`$SP/shuffle_harness.py`, seeds 0-19) gives `ran=889 failures=1 errors=0 skipped=9` for every seed. Msgid scan (`$SP/msgid_scan.py client`): 353. `tests.test_speech_symbols_dialog` has 21 tests. (`$PY` = `$SP/venv/bin/python`, `$SP` = the session scratchpad.)

### Classes (`client/dialog.py`)

| Item | Lines | Notes |
| --- | --- | --- |
| `AddSymbolDialog` | 62-156 | modal "Add/Edit Dictionary Entry" dialog; validates with `validate_dictionary_entry` in its own `_on_ok`; strips text and braille. Not changed by this task. |
| `CallbackVirtualListCtrl` | 313-326 | `wx.ListCtrl` whose `OnGetItemText(item, column)` calls a callback. Not changed. |
| `DictionaryEntryListCtrl` | 329 | alias of `CallbackVirtualListCtrl`; no user anywhere (left alone, see Out of Scope). |
| `SpeechSymbolsDialog` | 332-570 | the editor (title "Custom Dictionary Manager" / 自訂字典管理器). |

### Construction (`__init__` 335-343)

1. `super().__init__(parent, title=_("Custom Dictionary Manager"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)` - the native dialog exists before anything is read.
2. `self.dictionary_path = Path(dictionary_path) if dictionary_path else Path("data") / "dictionary.csv"` - the default is relative to the CWD; the only real caller always passes a path.
3. `self.entries = load_dictionary_entries(self.dictionary_path)` (through `_load_entries`); `self.filtered_entries = list(self.entries)`. A decode/CSV/OS error propagates out of the constructor (the native dialog from step 1 is never destroyed; see quirk Q8).
4. `_build_ui()`, then `filter_entries()` (filter box empty, nothing selected yet: shows all rows and selects and focuses row 0 if there is one), then `_update_button_states()` again.

### Layout (`_build_ui` 345-391), in creation (= tab) order

Static text "Filter by:" (篩選條件：); filter `wx.TextCtrl` bound to `EVT_TEXT` -> `_on_filter_changed`; static text "Dictionary entries" (字典項目); `CallbackVirtualListCtrl(self, self._get_item_text, style=LC_REPORT | BORDER_SUNKEN | LC_SINGLE_SEL | LC_VIRTUAL)` with columns `(0, "Source Text", 200)`, `(1, "Braille", 230)`, `(2, "Type", 120)` (來源文字 / 點字 / 類型), bound to `EVT_LIST_ITEM_SELECTED` and `EVT_LIST_ITEM_DESELECTED` -> `_on_selection_changed` and `EVT_LIST_ITEM_ACTIVATED` -> `_on_item_activated`; buttons "Add", "Edit", "Delete" (新增 / 編輯 / 刪除) bound to `_on_add_clicked`, `_on_edit_clicked`, `_on_remove_clicked`; `CreateButtonSizer(wx.OK | wx.CANCEL)`, localized with `localize_standard_buttons`, and only the OK button (`FindWindowById(wx.ID_OK)`) gets a handler, `_on_ok`; `finalize_dialog_layout`. The static texts give the screen reader the names of the controls that follow them, so creation order matters.

### Cell text (`_get_item_text` 396-404)

Row `item` of `filtered_entries`: column 0 `text`, 1 `braille`, 2 `ENTRY_TYPE_LABELS.get(entry_type, entry_type)` (labels translated when `dictionaries.entries` is imported); any other column raises `ValueError(f"Unknown column: {column}")`; plain list indexing for the row.

### Filtering and selection (`_entry_matches_filter` 406-408, `filter_entries` 410-440, 442-478)

- Match: `filter.casefold()` is a substring of `text.casefold()` or `braille.casefold()`; the type is never matched. Casefold, not lower: `STRASSE` matches `Straße`.
- `filter_entries(filter_text=None, preferred_entry=None, fallback_index=0)`:
  1. `previous_entry = preferred_entry or self._get_selected_entry()` - the selected entry is read from the list control against the **old** visible list, before anything changes. (`DictionaryEntry` is a plain dataclass, always truthy.)
  2. `filter_text` defaults to the filter box value; a non-empty filter keeps matching entries in full-list order, an empty one shows all. A whitespace filter is literal (`" "` keeps only entries containing a space).
  3. `SetItemCount(len(visible))`, `Refresh()`.
  4. Empty result: deselect the first selected row if any (`Select(index, False)`), update buttons, stop.
  5. Otherwise `index = min(fallback_index, len - 1)`; if `previous_entry` is not `None` and **equal** (`list.index`, dataclass equality) to a visible entry, the first equal visible entry wins. Then `_select_index(index)`: deselect the current row if any, `Select(index)`, `Focus(index)`, update buttons.
- `_on_filter_changed`: `filter_entries(self.filter_ctrl.GetValue())`, then `event.Skip()`.
- `_get_selected_index`: `GetFirstSelected()`; `None` for `NOT_FOUND`, negative or `>= len(visible)`.
- Buttons: Edit and Delete are enabled exactly when a row is selected (`_update_button_states`), refreshed after every list change and on every `SELECTED`/`DESELECTED` event (which are then skipped).

### Add / Edit / Delete (483-559)

- **Add** (`_on_add_clicked`): open `AddSymbolDialog(self, None)` (`_open_entry_dialog`); anything but `ID_OK` -> nothing. If any entry in the **full** list (hidden ones included) has exactly the same `text` (case-sensitive, braille and type ignored): `wx.MessageBox('Source text "{identifier}" already exists.', "Error", wx.OK | wx.ICON_ERROR, parent=self)` (來源文字「…」已存在。/ 錯誤) and stop; the typed entry is lost, the dialog is not reopened. Otherwise append at the end of the full list; if the filter box is non-empty and the new entry does not match it, `filter_ctrl.ChangeValue("")` (no `EVT_TEXT`); then `filter_entries(filter_text, preferred_entry=new_entry)` - the new entry is selected and focused.
- **Edit** (`_on_edit_clicked` and `_on_item_activated`, both -> `_edit_selected`): no selection -> nothing (the entry dialog is not opened). Open `AddSymbolDialog(self, current_entry)`; not `ID_OK` -> nothing. Duplicate check against every **other** entry, excluded by **identity** (`entry is not current_entry`): same message box, nothing changes. Otherwise replace the entry found by **identity** in the full list (its position is kept), then `filter_entries(filter box value, preferred_entry=updated, fallback_index=visible_index)`. The filter is **not** cleared: an edited entry that stops matching disappears and the row at the same visible index (clamped) is selected, or nothing if the list is empty.
- **Delete** (`_on_remove_clicked`): no selection -> nothing. No confirmation. `self.entries.remove(current_entry)` - removes the first **equal** entry of the full list (not necessarily the selected object when the file has identical rows). Then `filter_entries(filter box value, fallback_index=visible_index)`; `previous_entry` is the removed entry (still selected in the control), so an equal duplicate that is still visible gets the selection, otherwise the same visible index (clamped).
- `_normalize_type` (558-559) has no caller.

### OK / Cancel (561-570)

- OK: `save_dictionary_entries(self.dictionary_path, self.entries)` - the full list, in list order, even when nothing changed. `IOError` (= `OSError`): `wx.MessageBox("Failed to save: {error}", "Error", wx.OK | wx.ICON_ERROR, parent=self)` (儲存失敗：… / 錯誤), no `Skip`, the dialog stays open with the edits. Any other exception propagates out of the handler (no `Skip`). Success: `event.Skip()` and wx closes the dialog with `ID_OK`.
- Cancel, Escape and the close box use wx's default handling (`ID_CANCEL`): nothing is written, edits are discarded, no confirmation.
- Keyboard: no accelerators or key handlers of its own. Enter (or a double click) on a row activates it -> Edit. Tab order is creation order.

### Entry IO (`client/dictionaries/entries.py`, not changed)

`DictionaryEntry(text, braille, entry_type="General")` is a mutable `@dataclass` (equality by value, unhashable). `load_dictionary_entries(path)`: missing file -> `[]`; `csv.DictReader` with `encoding="utf-8"`; strips `text` and `braille`, normalizes unknown types to `General`, skips rows with empty text and `Bopomofo` rows whose braille is not a valid zhuyin sequence; duplicates are kept. `save_dictionary_entries(path, entries)`: creates the parent directory, opens with `"w"` (truncates first), writes `text,braille,type` header and rows.

### Callers

- `gui.py:82` imports `SpeechSymbolsDialog`; `gui.on_open_dictionary_management` (935-945) opens `DictionaryManagementDialog` with the P0-6 presenter; on `ID_EDIT` it builds `self._dictionary_presenter.dictionary_path(edit_name)` and runs `with SpeechSymbolsDialog(self, dictionary_path=...) as editor: editor.ShowModal()`, ignoring the result. Nothing else constructs the editor.
- Tests: `tests/test_speech_symbols_dialog.py` (21 tests; builds the dialog with `object.__new__` and pokes `entries`, `filtered_entries`, `filter_entries`, `_get_item_text`, `_open_entry_dialog`, `_edit_selected`, `_save_entries`); `tests/test_dialog_validation.py` (imports it for the context-manager tests); `tests/test_gui_document_flows.py` (patches `gui.SpeechSymbolsDialog`, asserts the keyword call, and a "kept names" guard at line 1054); `tests/wx_stub.py` (`_GUI_DIALOG_NAMES` creates a stub class per name for the fake `dialog` module of the gui scope; the speech stub profile `speech_dialog_stubs`/`load_speech_dialog`/`SPEECH_DIALOG_MODULE_NAME` is shared with `tests/test_dictionary_management_dialog.py` and `tests/test_wx_stub.py`).
- The stub scope of `test_speech_symbols_dialog` evicts modules under `dictionaries` that are first imported inside it (`evict_speech_roots`).

## Design

### Decision summary

- **D1 Model, not presenter.** A mutable model owned by the dialog; the dialog stays the controller and keeps every `_()` string and `wx.MessageBox` call. No `View` protocol, no observer callbacks: the dialog is the only mutator, so every model call returns what the view must render (`EntryListUpdate`). This is the MVP Supervising Controller S-4 suggests. A P0-6-style presenter was rejected: the per-action flow is 3-6 lines, while moving the messages would move their `.pot` locations and double the surface.
- **D2 The view owns selection.** The list control stays the source of truth for the selected row (it changes on arrow keys without any model call, and wx does not guarantee `DESELECTED` events for virtual lists). The dialog reads `GetFirstSelected()` at the moment of each action and passes the visible index to the model, exactly as today.
- **D3 The model owns the filter text.** It is set only by `apply_filter` (called from `EVT_TEXT` and at construction) and by `add` (which clears it). Invariant: `model.filter_text == filter_ctrl.GetValue()` after every handler. Today the dialog re-reads the box in each handler; the two are equal as long as `EVT_TEXT` reaches `_on_filter_changed` for every user edit, and the only programmatic change, `ChangeValue("")` in Add, is mirrored by the model (see Risks).
- **D4 Same comparison rules, written down.** Restore selection by equality (first equal visible entry); replace by identity; remove the first equal entry; duplicate check by exact `text` with identity exclusion. Changing any of these changes behavior for files with identical rows, so the model keeps them and the docstring says so.
- **D5 Messages stay in `dialog.py`.** The model has no `_()` and does not import `i18n` (it uses `ENTRY_TYPE_LABELS` from `dictionaries.entries`). A duplicate raises `DuplicateEntryError(identifier)`; the dialog formats the existing msgid. No msgid or `.pot` location moves to a new file.
- **D6 `dictionary_path` is required.** `__init__(self, parent, dictionary_path)`, stored as `Path(dictionary_path)`. The parameter keeps its name and position, so `gui.py`'s keyword call is unchanged. Not user-visible: the only caller always passes a path. Removes a CWD-relative write target that S-4 calls out.
- **D7 Rename** `SpeechSymbolsDialog` -> `DictionaryEntriesDialog`. "Speech symbols" is NVDA heritage and says nothing about DotExpress; the title is "Custom Dictionary Manager", the model is `DictionaryEntryListModel`, and the class is not user-visible. Cost: about 40 mechanical lines (`dialog.py`, `gui.py` 2, `tests/test_dialog_validation.py` 2, `tests/test_gui_document_flows.py` 2, `tests/wx_stub.py` 1, the dialog test module), done as its own last commit so it can be dropped without touching the refactor. The test module is renamed with `git mv` to `tests/test_dictionary_entries_dialog.py` and its `SpeechSymbolsDialog*Test` classes to `DictionaryEntriesDialog*Test`. No alias for the old name (no external users). Not renamed: `AddSymbolDialog` (not in the roadmap row; follow-up) and the wx_stub profile names `speech_dialog_stubs`, `load_speech_dialog`, `SPEECH_DIALOG_MODULE_NAME`, `SPEECH_RESTORE_ROOTS`, `evict_speech_roots` (test-infrastructure names shared with two other test modules; only the comment that names the test module is updated). Historical docs (`docs/refactor/*.md`, older specs) keep the old name. `.pot`/`.po` impact: none. xgettext records only `file:line` references, never class names; the msgids are unchanged (353); the `#: dialog.py:NNN` comments in `client/locales` are already stale line numbers and are refreshed by the next `scripts\generate-pot.bat` run, so `client/locales` has no diff in this task.

### `client/dictionaries/entry_list_model.py` (tabs, no wx, no i18n)

```python
class DuplicateEntryError(ValueError):
	"""Another entry already has this source text; nothing was changed."""
	def __init__(self, identifier: str) -> None:
		super().__init__(identifier)
		self.identifier = identifier


@dataclass(frozen=True)
class EntryListUpdate:
	selection: int | None          # visible row to select and focus; None: clear the selection
	filter_cleared: bool = False   # add only: the filter was reset to "" because the new entry did not match


class DictionaryEntryListModel:
	def __init__(self, entries: Iterable[DictionaryEntry] = ()) -> None  # filter "", all visible
	@classmethod
	def load(cls, path: Path) -> DictionaryEntryListModel               # load_dictionary_entries(path); errors propagate
	def save(self, path: Path) -> None                                   # save_dictionary_entries(path, full list); errors propagate

	entries: tuple[DictionaryEntry, ...]          # property, full list in file order (snapshot)
	visible_entries: tuple[DictionaryEntry, ...]  # property
	filter_text: str                              # property
	visible_count: int                            # property

	def visible_entry(self, index: int | None) -> DictionaryEntry | None   # None if index is None, < 0 or >= visible_count
	def cell_text(self, row: int, column: int) -> str                     # exactly _get_item_text today
	@staticmethod
	def matches(entry: DictionaryEntry, filter_text: str) -> bool        # casefold substring of text or braille
	def source_text_exists(self, text: str, exclude_entry: DictionaryEntry | None = None) -> bool

	def apply_filter(self, filter_text: str, selected_index: int | None = None) -> EntryListUpdate
	def add(self, entry: DictionaryEntry) -> EntryListUpdate
	def replace(self, visible_index: int, entry: DictionaryEntry) -> EntryListUpdate
	def remove(self, visible_index: int) -> EntryListUpdate
```

Semantics (each one a line-for-line transcription of today's code):

- `_refilter()`: `visible = [e for e in entries if matches(e, filter)]` if `filter` else `list(entries)`.
- `_selection_after(preferred, fallback_index)`: `None` if nothing is visible; else `min(fallback_index, n - 1)`, overridden by `visible.index(preferred)` when `preferred` is not `None` and an equal entry is visible.
- `apply_filter(text, selected_index)`: `preferred = visible_entry(selected_index)` from the visible list **before** the change; set `filter = text`; `_refilter()`; `EntryListUpdate(_selection_after(preferred, 0))`.
- `add(entry)`: `source_text_exists(entry.text)` -> `raise DuplicateEntryError(entry.text)` with nothing changed; append; `cleared = bool(filter) and not matches(entry, filter)`; if cleared, `filter = ""`; `_refilter()`; `EntryListUpdate(_selection_after(entry, 0), filter_cleared=cleared)`.
- `replace(i, entry)`: `current = visible[i]` (`IndexError` for `i < 0` or `i >= visible_count`; no negative indexing); `source_text_exists(entry.text, exclude_entry=current)` -> `DuplicateEntryError`, nothing changed; replace the full-list item that `is current`; `_refilter()`; `EntryListUpdate(_selection_after(entry, i))`.
- `remove(i)`: `current = visible[i]` (same range check); `entries.remove(current)` (first equal); `_refilter()`; `EntryListUpdate(_selection_after(current, i))`.
- `cell_text(row, column)`: `visible[row]` with plain indexing (as today; wx never passes a negative row); columns 0/1/2 as today; otherwise `ValueError(f"Unknown column: {column}")`.
- `source_text_exists(text, exclude_entry)`: `any(e.text == text and e is not exclude_entry for e in entries)`.
- `save(path)` passes the internal list itself (same iteration and bytes as today).

Allowed imports: `__future__`, `collections.abc`, `dataclasses`, `pathlib`, `dictionaries.entries`. An AST guard in the model test forbids `wx`, `gui`, `dialog`, `ui`, `settings` and `i18n`.

### Dialog after the change

`DictionaryEntriesDialog(ContextManagedDialog, wx.Dialog)` (named `SpeechSymbolsDialog` until step 4). Attribute names kept: `dictionary_path`, `filter_ctrl`, `list_ctrl`, `add_button`, `edit_button`, `remove_button`; new private `_model`. Removed: `entries`, `filtered_entries`, `_load_entries`, `_get_item_text`, `_entry_matches_filter`, `_identifier_exists`, `_normalize_type`, `_save_entries`, the `preferred_entry`/`fallback_index` parameters, and the now-unused imports (`List`, `load_dictionary_entries`, `save_dictionary_entries`, `normalize_entry_type`).

- `__init__(parent, dictionary_path)`: `super().__init__` (same arguments) -> `self.dictionary_path = Path(dictionary_path)` -> `self._model = DictionaryEntryListModel.load(self.dictionary_path)` -> `_build_ui()` (identical; the list callback is `self._model.cell_text`) -> `_render(self._model.apply_filter(self.filter_ctrl.GetValue(), self._get_selected_index()))` -> `_update_button_states()`.
- `_render(update)`: `SetItemCount(model.visible_count)`, `Refresh()`; `selection is None` -> `_clear_selection()`, `_update_button_states()`; else `_select_index(selection)` (unchanged).
- `_on_filter_changed(event)`: `_render(model.apply_filter(filter_ctrl.GetValue(), _get_selected_index()))`, `event.Skip()`.
- Add: `entry = _open_entry_dialog()`; `None` -> return; `try: update = model.add(entry)` / `except DuplicateEntryError as error:` the same `MessageBox` with `identifier=error.identifier`, return; `if update.filter_cleared: filter_ctrl.ChangeValue("")`; `_render(update)`. wx call order is unchanged: message box before anything; `ChangeValue` before `SetItemCount`.
- Edit: `index = _get_selected_index()`, `current = model.visible_entry(index)`; `None` -> return before opening the entry dialog; `updated = _open_entry_dialog(current)`; `None` -> return; `model.replace(index, updated)` with the same duplicate handling; `_render(update)`.
- Delete: `index = _get_selected_index()`; `None` -> return; `_render(model.remove(index))`.
- OK: `try: self._model.save(self.dictionary_path)` / `except IOError as exc:` same message box, return; `event.Skip()`.
- `_update_button_states`, `_get_selected_index` and `_select_index` (bounds now `model.visible_count`), `_clear_selection`, `_on_selection_changed`, `_on_item_activated`, `_open_entry_dialog`: unchanged.

`gui.py` changes only in step 4 (import and constructor name). It does not import the model.

### Tests under stub scopes

- The dialog test imports `dictionaries.entry_list_model` at module level **before** `wx_stub.load_speech_dialog()`, like it already does for `dictionaries.entries`, so the module is not first imported inside the scope, is not evicted, and the dialog and the test share one `DuplicateEntryError`/`DictionaryEntryListModel` class.
- `test_dialog_validation` (isolates `dialog`, evicts nothing) and `test_dialog_display` (evicts everything) import the model through `dialog`; the model holds no stub reference, so `StubScope._check_leaks` stays quiet. The gui scope uses a fake `dialog` module and never imports the model.
- The model test is plain `unittest`, no stub scope.

## What Stays Identical

- Every user-visible string (English and zh_TW), title, label, column width, list style, button set, creation/tab order and the control each static text names.
- For every action: whether the entry dialog opens and with which entry, message box text/title/flags/parent and its position relative to list changes, `ChangeValue` vs `SetValue`, the sequence of `SetItemCount`/`Refresh`/`Select`/`Focus` calls, the selected and focused row, Edit/Delete enabled state, the filter box value.
- The comparison rules of D4, the duplicate check across hidden entries, the full-list order, saving the full list on every OK (even unchanged), the `OSError` message with the dialog kept open, propagation of other exceptions, Cancel writing nothing.
- `AddSymbolDialog`, `CallbackVirtualListCtrl`, `DictionaryManagementDialog`, `dictionaries/entries.py`, `client/locales`, `scripts/`, `client/conversion`, `client/translation`: no diff.

## Test Plan

Characterization first. Part A is committed before any production change and is not edited afterwards except by the mechanical rename of step 4 (class and module names only). Part A cannot be red on today's code, so a throwaway mutant runner (not committed) applies 15 one-edit breakages to a copy of `client/` and shows each one makes part A fail: `lower()` instead of `casefold()`; match the type column; previous selection read after refiltering; selection restored by identity instead of equality; edit replace by equality (first equal) instead of identity; delete by identity instead of first equal; duplicate check case-insensitive; duplicate check only over visible entries; duplicate check without self-exclusion; Add clears the filter even when the entry matches; Edit clears the filter; `SetValue("")` instead of `ChangeValue("")`; fallback index not clamped; save of the visible list only; `Skip()` after a failed save.

### A. Characterization of the dialog (step 1, `tests/test_speech_symbols_dialog.py`)

1. **Black-box harness** in the test module. It drives the dialog only through its wx surface, so it survives the refactor unchanged:
   - `object.__new__(DialogClass)`, instance `CreateButtonSizer`/`FindWindowById` fakes, the stub base's `__init__` patched to record `(parent, title, style)`, the module's `wx` replaced by a namespace of distinct power-of-two flags, `NOT_FOUND = -1`, recording `TextCtrl`/`Button`/`StaticText`/sizers and `MessageBox`; `CallbackVirtualListCtrl` replaced by a fake list that records `InsertColumn`, `Bind`, `SetItemCount`, `Refresh`, `Select(index[, on])`, `Focus` and keeps `GetFirstSelected` state, and captures the cell callback; `AddSymbolDialog` replaced by a scripted fake (records the entry it was opened with; `ShowModal` returns `ID_OK` or `ID_CANCEL`; `get_entry` returns the scripted entry); then the real `__init__(parent, dictionary_path=<temp CSV>)`.
   - Actions go through the captured bindings: `type_filter(text)` (set value, fire `EVT_TEXT`), `select(i)` (set selection, fire `SELECTED`), `click("Add"|"Edit"|"Delete")` (buttons found by label), `activate()`, `press_ok()` (returns whether `Skip` was called).
   - Observations: one ordered event log (list calls, `ChangeValue`, message boxes, entry-dialog opens), visible rows via the captured cell callback, selected/focused row, button states, filter value, the CSV bytes after OK.
2. The 17 existing dialog tests (filter, build-UI and mutation classes) are rewritten onto the harness with the same assertions; `CallbackVirtualListCtrlTest`, the two loading tests and the isolation test (4) keep their current form.
3. New characterization tests: construction (base `__init__` before the file is read; title/style; creation order and column table; initial log `SetItemCount(n)`, `Refresh`, `Select(0)`, `Focus(0)`; empty and missing file: count 0, buttons disabled; an invalid UTF-8 file raises `UnicodeDecodeError` from the constructor); cell callback (three columns, zh_TW type labels, unknown column `ValueError`); filter (casefold `STRASSE`/`Straße`, literal whitespace, type not matched, selection kept by equality with identical rows selecting the first one, fallback to 0, empty result deselects and disables, exact log); Add (cancel does nothing; duplicate of a hidden entry; case-different text accepted; exact message `來源文字「Alpha」已存在。`, title `錯誤`, `OK | ICON_ERROR`, parent; append at the end; matching filter kept; non-matching filter cleared with `ChangeValue("")` before `SetItemCount`); Edit (button and activation; no selection opens nothing; same text accepted; duplicate rejected; identity replacement with identical rows; filter kept; fallback clamped; empty result); Delete (no confirmation; nearest row; last row; first-equal removal with identical rows, visible in the saved CSV order); OK (full list in order; unchanged dictionary rewritten in normalized form, dropping rows the loader skipped; parent directory created; `OSError` when the path is a directory: message `儲存失敗：{exc}` built from the raised error (its text differs between Linux and Windows), no `Skip`, edits kept and a later OK succeeds; a non-`OSError` from the writer propagates without `Skip`); only OK gets a handler; OK/Cancel labels localized.
4. **Golden trace** `tests/fixtures/dictionary_entries_trace.json`: a deterministic generator in the test module (`random.Random(seed)`, 40 sequences of 25 actions: filter, select or deselect, add/edit with OK, cancel or duplicate, activate, delete, final OK) over a small alphabet that forces collisions (`a`, `A`, `ab`, `Ab`, `Straße`, `STRASSE`, empty braille, the three types, an initial CSV with identical rows, skipped rows and padded fields). Each step records the harness observations; the final step records the saved CSV. The fixture is generated once in step 1 from unmodified code, committed with its sha256 in the commit message, and never regenerated in this task. A replay test compares every step. Target size under 300 KB.

### B. Model (step 2, new `tests/test_dictionary_entry_list_model.py`, tabs, no wx, no stub scope)

Written first (red: module missing). Covers each method and every rule of D4 with identical-row cases; `visible_entry` bounds (`None`, -1, count); `replace`/`remove` reject -1 and count with `IndexError` and change nothing; `DuplicateEntryError` is a `ValueError` with `identifier` and leaves state untouched; `add` with a non-matching filter returns `filter_cleared=True` and `filter_text == ""`; returned tuples are snapshots; `load` of a missing file gives an empty model; `save`/`load` round trip; `save` writes the full list while filtered; `cell_text` columns and the unknown-type fallback label; the AST import guard.

### C. Migration (step 3)

No change to part A; it must stay green, including the golden trace replay. New: one test that `dictionary_path` has no default (`inspect.signature`), and one that the dialog's `_model` is a `DictionaryEntryListModel` loaded from `dictionary_path`.

### D. Rename (step 4)

Mechanical edits only; `git diff -M` shows the test module as a rename. The kept-names guard in `tests/test_gui_document_flows.py` and `_GUI_DIALOG_NAMES` switch to `DictionaryEntriesDialog`.

The plan fixes the exact test counts; the full suite must be `889 + new tests`, `failures=1`, `skipped=9`.

## Migration Steps (each step one green commit)

1. `test: characterize dictionary entries editor` (part A, golden trace fixture).
2. `refactor: add wx-free dictionary entry list model` (part B; module not used yet).
3. `refactor: use DictionaryEntryListModel in the entries editor` (dialog delegates; required `dictionary_path`; dead `_normalize_type` and unused imports removed; part C).
4. `refactor: rename SpeechSymbolsDialog to DictionaryEntriesDialog` (part D).

## Acceptance Criteria

1. Roadmap verification on Linux (renamed module): `cd client && $PY -m unittest tests.test_dictionary_entry_list_model tests.test_dictionary_entries_dialog -v` passes.
2. Also green: `tests.test_dialog_validation tests.test_dialog_display tests.test_dictionary_entries tests.test_dictionary_management_dialog tests.test_dictionary_presenter tests.test_gui_document_flows tests.test_wx_stub tests.test_removed_dead_code tests.test_i18n tests.test_translation_golden`.
3. Full suite: `889 + new` tests, `failures=1` (P2-5 only), `errors=0`, `skipped=9`. Shuffle harness seeds 0-19: the same single failure for every seed. `test_dictionary_entries_dialog`, `test_dictionary_entry_list_model`, `test_dialog_validation`, `test_dialog_display` and `test_dictionary_management_dialog` pass alone and in both orders of each pair with `test_dictionary_entry_list_model`.
4. `git diff main -- client/tests/fixtures/translation_golden.json` is empty (sha256 `e67d95a1...1ccd`); the trace fixture is byte-identical between step 1 and step 4.
5. Msgid scan: 353; `git diff main --stat -- client/locales scripts client/dictionaries/entries.py client/conversion client/translation` is empty.
6. `grep -rn "SpeechSymbols" client --include=*.py` prints nothing (the kept wx_stub profile names are lower-case `speech_*`/`SPEECH_*`); `grep -rn "filtered_entries\|_identifier_exists\|_normalize_type\|Path(\"data\")" client/dialog.py` prints nothing.
7. `client/dictionaries/entry_list_model.py` passes the AST guard.

## Risks

- **Filter-text sync (D3).** If some real-wx path changed the filter box without `EVT_TEXT`, the model would filter with stale text where today's code re-reads the box. wx fires `EVT_TEXT` for typing, paste, cut, undo and IME commit, and nothing in the client calls `SetValue`/`ChangeValue` on this box except Add. Listed for Windows verification. Fallback if it fails there: pass `filter_ctrl.GetValue()` into `add`/`replace`/`remove` (API change only).
- **Visible list updated before `ChangeValue`.** In Add the model has already refiltered when `ChangeValue("")` runs, whereas today the visible list changes after it. A repaint inside `ChangeValue` would read a longer list with the old item count. Add only grows the visible list, so there is no out-of-range read; wx does not repaint synchronously there.
- **Equality vs identity.** The trace and the mutants pin each rule; a model that "fixes" one fails part A.
- **Stub-scope class identity.** Covered by importing the model before the scope (see Tests under stub scopes) and by shuffled runs.
- **Rename misses.** A missed `_GUI_DIALOG_NAMES` entry makes `gui` fail to import in the gui scope (loud). PyInstaller follows static imports; no `.spec` file names the class (grep).
- **Real wx.** Everything here is checked with stubs only.

## Known quirks kept (pinned, not fixed)

1. **Q1 Data loss with a UTF-8 BOM.** A dictionary CSV saved with a BOM (for example Excel "CSV UTF-8") opens empty (the header is read as U+FEFF followed by `text`), and OK overwrites it with the header only. Pre-existing; related to the P1-6 BOM finding. Pinned by a part A test. Suggested separate fix: read with `utf-8-sig` in `load_dictionary_entries` (and the rules loader).
2. **Q2** OK always rewrites the file, silently dropping rows the loader skipped (empty text, invalid zhuyin) and the whitespace it stripped.
3. **Q3** Save truncates before writing; an error part-way leaves a truncated file (no temp file + replace). Verified: a lone surrogate leaves only the header.
4. **Q4** With identical source texts in the file, neither row can be edited without changing its text (the other row is a duplicate), and Delete removes the first equal row, not necessarily the selected one.
5. **Q5** Delete has no confirmation; Cancel discards edits without asking.
6. **Q6** A duplicate in Add/Edit discards what the user typed (the entry dialog is not reopened).
7. **Q7** A non-`OSError` on save (for example `UnicodeEncodeError` from a lone surrogate) escapes the OK handler.
8. **Q8** A load error escapes the constructor after the native dialog was created; `gui` gets an unhandled exception and the dialog is never destroyed.

## Windows verification debt

- Packaged build, zh_TW, with NVDA: Dictionary Management -> Edit opens the editor with row 1 selected and announced; typing in the filter keeps the selected entry; Add of a non-matching entry clears the filter and selects it; Edit, Enter on a row, Delete (nearest row selected); the duplicate message; OK saves, Cancel discards. Paste, cut and undo in the filter box update the list (D3).
- Byte-compare the CSV written by OK for an unchanged dictionary against `main`.
- PyInstaller picks up `dictionaries/entry_list_model.py` through the static import in `dialog.py` (read, not run).
- No screenshots needed (no visual change).

## Out of Scope

- Fixing Q1-Q8 (Q1 is a data-loss bug and should get its own task).
- Renaming `AddSymbolDialog`, the wx_stub speech profile names, or removing the unused `DictionaryEntryListCtrl` alias.
- Making `DictionaryEntry` frozen/hashable; changing `dictionaries/entries.py`.
- Moving messages into a presenter; a View protocol for this dialog.
- Any change to `DictionaryManagementDialog` or the P0-6 presenter.
