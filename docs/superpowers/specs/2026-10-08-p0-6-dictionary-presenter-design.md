# Dictionary Management Presenter (P0-6) Design

## Goal

Move the dictionary-management workflow out of `BrailleFrame` into a wx-free, unit-testable `DictionaryManagementPresenter` in a new module `client/dictionaries/presenter.py`. This is roadmap task P0-6 (`storage/refactor.md` section 6.1). It addresses findings S-3 (the workflow is split between Frame and Dialog, the `on_duplicate`/`prompt_name` lambdas exist three times, and the dictionary list has two sources of truth) and I-1 (`DictionaryManagementDialog` takes 5 positional callbacks).

After this change:

- The five frame callbacks (`add_dictionary`, `delete_dictionary_from_dialog`, `rename_dictionary_from_dialog`, `import_dictionary_from_dialog`, `export_dictionary_from_dialog`) and `_prompt_for_dictionary_name` are gone from `client/gui.py`. Their logic lives in the presenter. Only the wx calls stay in wx code, behind a small view protocol.
- `DictionaryManagementDialog` takes one `actions` object instead of `dictionary_dir` plus five callbacks.
- The presenter's list is the only place the dictionary directory is listed. The frame's `self._dictionary_names` and the dialog's `_refresh_from_disk` are removed.

User-visible impact: none. Every dialog, message box, string, caption, icon, button flag, parent window, ordering of prompts and messages, file operation, list selection and settings write stays exactly as it is today. No msgid changes, so `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` and the `.mo` are not touched. No layout changes, so no screenshot is needed.

## Method and Baseline (verified 2026-10-08 on `refactor/p0-6-dictionary-presenter`, HEAD `70aae6b`, P0-1 to P0-5 merged)

1. Read `client/gui.py` (frame state 294-300, 563-609, the workflow 1234-1438), `client/dialog.py` (`DictionaryNameDialog` 191-239, `DictionaryManagementDialog` 650-845), every module under `client/dictionaries/`, `client/translation/dictionary_state.py`, `client/settings/translation.py`, `client/config.py` (`set_selected_dictionary`), `client/shared/name_validation.py` and `scripts/generate-pot.bat`.
2. Grepped every caller and test of the names involved (`DictionaryManagementDialog`, `_dictionary_names`, `_refresh_dictionary_names`, `get_dictionary_names_for_dialog`, `_set_active_dictionary`, `_get_csv_wildcard`, `CSV_WILDCARD`, `prompt_dictionary_name_until_success`, `plan_dictionary_state_*`).
3. Ran the tests (venv Python, from `client/`):
   - `python -m unittest discover -s tests`: `Ran 482 tests`, `FAILED (failures=1, skipped=7)`. The one failure is the known P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`.
   - Per module: `test_dictionary_management_dialog` 8, `test_dictionary_manager` 11, `test_dictionary_actions` 6, `test_translation_dictionary_state` 6, `test_dictionary_name_prompt` 4, `test_gui_document_flows` 61, `test_dictionary_entries` 8, `test_speech_symbols_dialog` 21, `test_settings_dialogs` 27. All `OK`.
   - The roadmap command without the not-yet-existing presenter module (`tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_actions tests.test_translation_dictionary_state tests.test_dictionary_name_prompt tests.test_gui_document_flows`): `Ran 96 tests`, `OK`.

Line numbers in `storage/refactor.md` predate P0-1 to P0-5. The ones above are current.

## Current State

### Who owns what

- `BrailleFrame._initialize_state` (294-300) sets `self.dictionary_dir`, calls `ensure_default_dictionary`, sets `self._dictionary_names = list_dictionary_names(...)`, loads `self.translation_settings` from config (normalizing `selected_dictionary` against those names), loads tables, then calls `_refresh_dictionary_names(selected)` again (a second listing whose result is unused).
- `_refresh_dictionary_names(preferred)` (563-567) calls `ensure_default_dictionary`, refills `self._dictionary_names[:]` from disk and returns `resolve_management_selection(names, preferred)`.
- `get_dictionary_names_for_dialog()` (569-571) refreshes with the active name and returns a copy. Callers: `get_settings_snapshot`, `apply_settings_from_dialog`, `on_open_settings` (1181), and the add, rename and import callbacks (only for the refresh side effect).
- The **active** dictionary is `self.translation_settings.selected_dictionary`. It changes in two places only: `apply_settings_from_dialog` (Settings dialog, saves all three translation settings) and `_set_active_dictionary(name)` (600-606, builds a new `TranslationSettings` and calls `config.set_selected_dictionary(name)`, one config write). The second is called only from delete and rename.
- `DictionaryManagementDialog` keeps its own `_dictionary_names` (a copy passed in at construction), its own `dictionary_dir` (for entry counts and for `_refresh_from_disk`, which re-lists the directory after every successful action), `_selected_name`, `_dictionary_counts` and `edit_dictionary_name`. Selecting a row only updates `_selected_name` and button states (`get_action_availability`). It never changes the active dictionary.

So the name list is read from disk in two places (frame and dialog), and the frame keeps a cached list that the delete flow uses as "names before delete".

### Flow inventory (the behavior this change must preserve exactly)

All message boxes and dialogs below are parented on the management dialog: the dialog passes `self` as `parent`, and every callback uses `dialog_parent = parent or self`. "Info box" means `wx.MessageBox(msg, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=...)`. "Error box" means `wx.MessageBox(msg, _("Error"), wx.OK | wx.ICON_ERROR, parent=...)` (both the duplicate lambda and `_show_file_error`, which formats `message.format(error=exc)`, produce this exact call). "Name prompt (title, initial)" means `DictionaryNameDialog(parent, initial_name=initial)`, `SetTitle(title)`, `ShowModal()`; anything other than `wx.ID_OK` is a cancel; otherwise `get_dictionary_name()` (stripped). `DictionaryNameDialog._on_ok` already validates with `normalize_dictionary_name` and shows its own localized Info box, so most `ValueError` paths below are reachable only for names that pass the dialog check but fail later.

"Name loop" is `prompt_dictionary_name_until_success(initial, prompt_name, on_submit, on_duplicate)`: prompt; cancel returns `None`; `on_submit(name)`; on `FileExistsError` show an error box `_('Dictionary "{name}" already exists.').format(name=name.strip())` and prompt again with the typed name as initial value. Any other exception leaves the loop.

**Open** (`on_open_dictionary_management`, 1234-1254). Refresh with the active name, open the management dialog modally with the refreshed list and the resolved selection. After it closes: if the result is `wx.ID_EDIT` and `edit_dictionary_name` is set, open `SpeechSymbolsDialog(self, dictionary_path=<dir>/<name>.csv)` modally. The management dialog is not reopened afterwards. Close: nothing.

**Add** (button always enabled).
1. Name loop: title `_("Add Dictionary")`, initial `""`, submit `create_dictionary(dir, name)`.
2. `ValueError`: info box `str(exc)` (untranslated English text from `normalize_base_name`, for example `Name 'default' is reserved.`), return `None`.
3. `OSError` other than `FileExistsError` is **not caught** and propagates out of the button handler.
4. Cancel: return `None`.
5. Success: refresh (via `get_dictionary_names_for_dialog`), return `plan_dictionary_state_after_add(active, names, path.stem).management_selected_name`. The active dictionary is never changed, even when the plan's `active_selected_name` differs.

**Delete** (button enabled only for a non-default selection).
1. If `is_default_dictionary(name)`: info box `_("The default dictionary cannot be deleted.")`, return `None`.
2. Confirm: `wx.MessageBox(_('Do you want to delete dictionary "{name}"?').format(name=name), _("Confirm Delete Dictionary"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=...)`. Anything but `wx.YES`: return `None`.
3. Capture `previous_names` (the frame's cached list) and the active name.
4. `delete_dictionary(dir, name)`. `OSError`: error box `_("Failed to delete dictionary: {error}")`, return `None` (no refresh, no settings change). `ValueError` (only for a stem such as `" default"` that is not caught by step 1 but is stripped to `default` by `delete_dictionary`) is **not caught**.
5. Refresh, plan with `plan_dictionary_state_after_delete(active, name, previous_names)`. If the planned active name differs from the current one, `_set_active_dictionary(planned)` (updates `translation_settings`, writes config). Return the planned management selection.

**Rename** (button enabled only for a non-default selection).
1. If `is_default_dictionary(name)`: return `None` silently (no message).
2. Name loop: title `_("Rename Dictionary")`, initial = the selected name, submit `rename_dictionary_after_name_prompt(dir, selected, new)` (same name after strip: no file operation, returns the existing path; case-only change: renames).
3. `ValueError`: info box `str(exc)`, return `None`. `OSError`: error box `_("Failed to save dictionary: {error}")`, return `None`. (`FileExistsError` never gets here; the loop handles it.)
4. Cancel: return `None`.
5. Success: read the active name, refresh with `path.stem`, plan with `plan_dictionary_state_after_rename(active, selected, path.stem, names)` (the old code refreshes a second time here through `get_dictionary_names_for_dialog`). If the planned active name differs, `_set_active_dictionary(planned)`. Return the planned management selection.

**Import** (button always enabled).
1. `wx.FileDialog(parent, _("Import Dictionary"), wildcard=_("CSV files (*.csv)|*.csv"), style=wx.FD_OPEN)`. Not `wx.ID_OK`: return `None`. The file dialog is destroyed before the next step.
2. Name loop: title `_("Add Dictionary")` (sic, not "Import"), initial = source file stem, submit `import_dictionary(dir, source, name)`. The destination-exists check runs before CSV validation, so a duplicate name re-prompts even for an invalid file.
3. **Any** `ValueError` (missing headers, an invalid name, or a `UnicodeDecodeError` while reading the source): error box `_("Imported file must contain text, braille, and type headers.")`, return `None`. `OSError` (for example the source vanished): error box `_("Failed to import dictionary: {error}")`, return `None`.
4. Cancel: return `None`.
5. Success: same as add step 5. Never changes the active dictionary.

**Export** (button enabled when the list is non-empty).
1. If the frame's cached list is empty, return (no UI).
2. `wx.FileDialog(parent, _("Export Dictionary"), defaultFile=f"{name}.csv", wildcard=_("CSV files (*.csv)|*.csv"), style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)`. Not `wx.ID_OK`: return.
3. `export_dictionary(dir, name, destination)`. `OSError`: error box `_("Failed to export dictionary: {error}")`.
4. Returns `None` in all cases; the dialog never refreshes after export.

**Edit** (button enabled when the list is non-empty). The dialog sets `edit_dictionary_name` and ends modal with `wx.ID_EDIT` (see Open).

**Dialog refresh after an action.** For add, delete, rename and import, when the callback returns a name (not `None`), the dialog calls `_refresh_from_disk(name)`: re-list the directory (without `ensure_default_dictionary`), reload entry counts, `SetItemCount`, `Refresh`, select and focus `resolve_dictionary_selection(names, name)`, resize columns, update button states. A `None` result leaves the list as it was.

**Select / activate.** There is no activate action inside dictionary management. The active dictionary is chosen in the Settings dialog (`TranslationSettingsPanel`, names from `get_dictionary_names_for_dialog`) and saved by `apply_settings_from_dialog`, or changed implicitly by delete and rename as above.

### Duplication and coupling (S-3, I-1)

- The duplicate-name error box lambda is written three times (add, rename, import) and the `prompt_name` lambda three times.
- `DictionaryManagementDialog.__init__` takes 9 parameters: parent, names, selection, directory and 5 positional callbacks.
- The frame's cached list and the dialog's disk listing are two sources of truth. They agree today only because the frame refreshes inside every successful callback just before the dialog re-lists.
- No test covers the five callbacks or `on_open_dictionary_management`. The pure helpers they call (`manager`, `name_prompt`, `actions`, `translation.dictionary_state`) are covered.

## Design

### Decision: presenter owns the name list and the workflow; the dialog is the passive view

Alternatives considered:

1. **`DictionaryManagementActions` dataclass of five callables built by the frame.** Fixes the positional signature (I-1) but leaves the workflow, the lambdas and the second list in `gui.py`. Rejected as the main design. The dialog still takes a single actions object, typed as a protocol, so a future action (for example "Duplicate") adds a method, not a constructor parameter.
2. **Presenter that returns `DictionaryStateUpdate` for the frame to apply, as S-3 suggests.** Rejected. It would keep the "apply the update, then call `_set_active_dictionary`" step duplicated in the frame. The presenter applies the update itself through an injected callback and returns only what the dialog needs: the name to select.
3. **Presenter owning the active name, as S-3 suggests ("holds `active_name`").** Rejected. `translation_settings.selected_dictionary` is also changed by the Settings dialog. A second copy would create a new two-sources-of-truth problem. The presenter reads the active name through `get_active_name()` and changes it through `set_active_name(name)`; the frame wires these to `translation_settings` and `_set_active_dictionary`.
4. **A separate wx view adapter class in `gui.py`.** Rejected. Every prompt and message box is parented on the management dialog, so the dialog is the natural view. Making the dialog implement the view protocol keeps the wiring to one line in the frame and keeps the parent window identical.
5. **Chosen:** `DictionaryManagementPresenter` in `client/dictionaries/presenter.py` owns the directory listing, the name list and the five flows. It builds every user-facing string with `from i18n import _` at call time and talks to the user only through a `DictionaryManagementView` protocol. `DictionaryManagementDialog` implements that protocol with the exact wx calls listed above and receives the presenter as its `actions`.

### `client/dictionaries/presenter.py`

Tabs, like `dictionaries/name_prompt.py` and `dictionaries/actions.py`. Imports only the standard library, `i18n._`, `dictionaries.manager`, `dictionaries.actions`, `dictionaries.name_prompt` and `translation.dictionary_state`. It must not import `wx` (guarded by a test). Manager functions are imported by name into the module, so tests can patch them on the presenter module for fault injection. Names below fix intent; the plan may adjust spelling only.

```python
class DictionaryManagementView(Protocol):
	def prompt_dictionary_name(self, title: str, initial_name: str) -> str | None: ...
	def show_info(self, message: str) -> None: ...
	def show_error(self, message: str) -> None: ...
	def confirm(self, message: str, caption: str) -> bool: ...
	def choose_import_path(self, title: str) -> Path | None: ...
	def choose_export_path(self, title: str, default_file: str) -> Path | None: ...


class DictionaryManagementActions(Protocol):
	@property
	def dictionary_names(self) -> list[str]: ...
	def dictionary_path(self, name: str) -> Path: ...
	def add(self, view: DictionaryManagementView) -> str | None: ...
	def delete(self, view: DictionaryManagementView, name: str) -> str | None: ...
	def rename(self, view: DictionaryManagementView, name: str) -> str | None: ...
	def import_from_file(self, view: DictionaryManagementView) -> str | None: ...
	def export_to_file(self, view: DictionaryManagementView, name: str) -> None: ...


class DictionaryManagementPresenter:  # satisfies DictionaryManagementActions
	def __init__(self, dictionary_dir: Path, *, get_active_name: Callable[[], str],
	             set_active_name: Callable[[str], None]) -> None: ...  # no I/O
	dictionary_dir: Path                      # read-only
	dictionary_names -> list[str]             # a copy of the single list
	def refresh(self, preferred_name: str | None = None) -> str: ...
	def dictionary_path(self, name: str) -> Path: ...
	# add / delete / rename / import_from_file / export_to_file as in the protocol
```

- `refresh(preferred)`: `ensure_default_dictionary(dir)`, replace the list with `list_dictionary_names(dir)`, return `resolve_management_selection(list, preferred)`. This is today's `_refresh_dictionary_names`.
- `dictionary_names` returns a new list each time, so neither the frame nor the dialog can mutate the presenter's list.
- `dictionary_path(name)` is `dictionary_path_for_name(name, dir)`.
- One private helper runs the name loop: `prompt_dictionary_name_until_success(initial, prompt_name=lambda n: view.prompt_dictionary_name(title, n), on_submit=submit, on_duplicate=lambda n: view.show_error(_('Dictionary "{name}" already exists.').format(name=n.strip())))`. This replaces the three copies of each lambda.
- The five flows follow the flow inventory step by step, with these mappings: info box to `view.show_info(msg)`, error box to `view.show_error(msg)` (file errors pre-formatted as `_("Failed to ... {error}").format(error=exc)`), confirm box to `view.confirm(msg, _("Confirm Delete Dictionary"))`, file dialogs to `choose_import_path(_("Import Dictionary"))` and `choose_export_path(_("Export Dictionary"), f"{name}.csv")`, "refresh" to `self.refresh(...)`, "frame's cached list" to the presenter's list, "active name" to `get_active_name()`, `_set_active_dictionary` to `set_active_name`.
- The exception quirks in the inventory stay as they are: add does not catch `OSError`; delete does not catch `ValueError`; import maps every `ValueError` to the header message; rename with the default name returns `None` without a message; add and import never change the active dictionary. Each is pinned by a presenter test and listed under follow-ups.
- Refresh points: after a successful add, import or rename, the presenter refreshes exactly once (rename with `path.stem`, add and import with the active name); after a successful delete, once with the deleted name. The old rename, add and import paths listed the directory a second time with nothing changing in between; dropping the extra listing is not observable.

### `DictionaryManagementDialog` (`client/dialog.py`)

- Constructor: `DictionaryManagementDialog(parent, actions: DictionaryManagementActions, selected_name: str)`. It stores `self._actions` and initializes the list with `self.refresh_dictionaries(actions.dictionary_names, selected_name)`. The `dictionary_dir` and five callback parameters and attributes are removed.
- `_load_dictionary_counts` reads `load_dictionary_entries(self._actions.dictionary_path(name))`. Counts stay a dialog concern (display data, not the list).
- The list the dialog renders (`self._dictionary_names`) is a snapshot it takes only from `actions.dictionary_names`. `_refresh_from_disk` is replaced by a helper that calls `self.refresh_dictionaries(self._actions.dictionary_names, preferred)`. `dialog.py` no longer imports `list_dictionary_names`.
- Button handlers call `self._actions.add(self)`, `delete(self, selected)`, `rename(self, selected)`, `import_from_file(self)`, `export_to_file(self, selected)` with the same selection guards and the same "refresh only on a non-`None` result" rule. Export never refreshes. Edit, close, selection and column sizing are unchanged.
- The dialog implements `DictionaryManagementView` with the exact wx calls from the inventory, parented on `self`:
  - `prompt_dictionary_name`: the body of today's `gui._prompt_for_dictionary_name`, moved here.
  - `show_info`, `show_error`: the info and error boxes.
  - `confirm`: `wx.MessageBox(message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self) == wx.YES`.
  - `choose_import_path`, `choose_export_path`: the two `wx.FileDialog` blocks, returning `Path(GetPath())` or `None`.
- The CSV wildcard moves with the file dialogs: `dialog.py` gets `CSV_WILDCARD = "CSV files (*.csv)|*.csv"` and translates it at call time, exactly as `gui._get_csv_wildcard` does now. The msgid stays extractable through the existing `N_("CSV files (*.csv)|*.csv")` marker in `gui.py`, which this change does not touch.

### `BrailleFrame` (`client/gui.py`)

- `_initialize_state`: after setting `self.dictionary_dir`, create `self._dictionary_presenter = DictionaryManagementPresenter(self.dictionary_dir, get_active_name=lambda: self.translation_settings.selected_dictionary, set_active_name=self._set_active_dictionary)`, call `refresh()`, and load translation settings with `self._dictionary_presenter.dictionary_names`. The second, unused listing is dropped.
- `get_dictionary_names_for_dialog()` keeps its name and contract: `refresh(active)`, then return `dictionary_names`. Its callers do not change.
- `on_open_dictionary_management`: `selected = self._dictionary_presenter.refresh(active)`, then `DictionaryManagementDialog(self, self._dictionary_presenter, selected)`. The edit branch uses `self._dictionary_presenter.dictionary_path(edit_name)`. The `SpeechSymbolsDialog` part is unchanged (S-4/P1 owns it).
- `_set_active_dictionary` stays in the frame unchanged. It is the presenter's `set_active_name`.
- Removed: `_dictionary_names`, `_refresh_dictionary_names`, the five callbacks, `_prompt_for_dictionary_name`, `CSV_WILDCARD`, `_get_csv_wildcard`, and imports that become unused (`create_dictionary`, `delete_dictionary`, `export_dictionary`, `import_dictionary`, `list_dictionary_names`, `ensure_default_dictionary`, `is_default_dictionary`, `prompt_dictionary_name_until_success`, `rename_dictionary_after_name_prompt`, `plan_dictionary_state_after_*`, `resolve_management_selection`, `DictionaryNameDialog`). `self.dictionary_dir`, `_get_selected_dictionary_path` and `_show_file_error` stay (other features use them).
- `_MENU_TRANSLATION_MARKERS` is not changed.

### Strings and localization

Every string keeps its exact msgid and is still passed through `_()` at the moment it is shown. Strings move from `gui.py` to `dictionaries/presenter.py` (messages, titles, captions) and to `dialog.py` (`_("Info")`, `_("Error")`, the CSV wildcard). `scripts/generate-pot.bat` collects every `*.py` under `client/` except `tests/`, so both files are scanned. Only `#:` location comments would change when the template is regenerated on Windows, which is not required by this task. The `.po` and `.mo` stay untouched.

### Commit order

Each commit leaves the full suite at the baseline result plus the tests it adds.

1. `test:` + `feat:` presenter, test first. Write `tests/test_dictionary_presenter.py` flow by flow (refresh and names, add, delete, rename, import, export), each red first, then implement that part of `dictionaries/presenter.py`. One or several commits; the presenter is not used by the app yet.
2. `refactor: route dictionary management through presenter`. In one commit, because the dialog constructor and its only caller must change together: dialog tests updated or added first (actions wiring, view methods), then `DictionaryManagementDialog` gets the new constructor and view methods, and `BrailleFrame` creates and passes the presenter, with the `test_gui_document_flows` changes below.
3. `refactor: remove dead dictionary callbacks from gui`. Delete the old callbacks, `_prompt_for_dictionary_name`, the CSV wildcard helper and the unused imports, if step 2 did not already remove them. Behavior-neutral.

## Test Strategy

### New: `client/tests/test_dictionary_presenter.py` (written first)

Pure `unittest`, no wx, no stubs. A real `tempfile.TemporaryDirectory` as `dictionary_dir`. A `FakeView` that records every call in order as tuples (`("prompt", title, initial)`, `("info", msg)`, `("error", msg)`, `("confirm", msg, caption)`, `("choose_import", title)`, `("choose_export", title, default_file)`) and answers from scripted queues. The active name is a one-item list behind `get_active_name`; `set_active_name` is a `Mock`. Expected strings are built with `i18n._` (the catalog is fixed to zh_TW, so English literals would not match). Each test asserts the **full** `view.calls` list, the return value, the files on disk, `dictionary_names` and the `set_active_name` calls. Fault injection uses `patch.object(presenter_module, "<manager function>", side_effect=PermissionError("denied"))`.

Minimum cases:

- Module: `presenter.py` does not import `wx` (AST check of its imports).
- `refresh`: creates `default.csv` when missing, lists case-insensitively sorted, returns the preferred name or falls back to `default`; `dictionary_names` returns a copy.
- `dictionary_path`.
- Add: success (prompt `Add Dictionary` with `""`, file created, returns the new name, list updated, no `set_active_name`); cancel (no file, no message); duplicate then success (error box with the stripped name, re-prompt with the typed name); `ValueError` (reserved name: info box `str(exc)`, returns `None`); `OSError` from `create_dictionary` propagates.
- Delete: default (info box only, no confirm); confirm declined (file kept); success for a non-active name (active unchanged, no `set_active_name`, returns `default`); success for the active name (`set_active_name` with the planned fallback, for example `beta` deleted from `[alpha, beta, default]` activates `alpha`); `OSError` (confirm, then error box `Failed to delete dictionary: ...`, returns `None`, list and active unchanged); `ValueError` propagates for a `" default"` stem.
- Rename: default (no view calls, `None`); cancel; success for a non-active name; success for the active name (`set_active_name(new)`); same name (no file change, no `set_active_name`, returns the name); case-only (renamed); duplicate then success; `ValueError` (info box `str(exc)`); `OSError` from `rename_dictionary_after_name_prompt` (error box `Failed to save dictionary: ...`).
- Import: file dialog cancelled (no prompt); success (prompt `Add Dictionary` with the source stem, file copied, no `set_active_name`); duplicate then success; invalid headers (error box with the header message); an invalid name returned by the fake view (same header message); missing source file (`FileNotFoundError`: error box `Failed to import dictionary: ...`); prompt cancelled.
- Export: empty list (no view calls); cancelled; success (`choose_export` with `<name>.csv`, file copied); `OSError` (error box `Failed to export dictionary: ...`).

### Updated: `client/tests/test_dictionary_management_dialog.py`

`_make_dialog` sets a fake `_actions` (names, `dictionary_path`, recorded action calls) instead of `dictionary_dir`. Existing tests keep their assertions. The disk-refresh test becomes "refresh after an action takes names from `actions.dictionary_names`, not from disk" (the fake returns names that are not on disk). New tests:

- Each of add, delete, rename and import calls the action with `(dialog[, selected])` and refreshes with the returned name; a `None` result leaves the list untouched; delete, rename and export do nothing without a selection; export never refreshes.
- Each view method makes exactly the wx call from the inventory (message, caption, flags, `parent=dialog`; file dialog title, wildcard, `defaultFile`, style), with `wx.MessageBox`, `wx.FileDialog` and `DictionaryNameDialog` patched on the loaded dialog module. Cancel paths return `None` or `False`.

The module keeps using `wx_stub.load_speech_dialog()`. If a flag comparison needs distinct values, the plan may add explicit constants (`YES`, `YES_NO`, `NO_DEFAULT`, `ICON_WARNING`, `ICON_INFORMATION`, `ID_OK`, `FD_OPEN`, `FD_SAVE`, `FD_OVERWRITE_PROMPT`) to `speech_dialog_stubs()`, provided `test_speech_symbols_dialog` still passes unchanged.

### Updated: `client/tests/test_gui_document_flows.py`

- `_initialize_state_with_loaded_tables` patches `gui.ensure_default_dictionary` and `gui.list_dictionary_names`, which will no longer exist on `gui`, and mocks `_refresh_dictionary_names`. It switches to patching `gui.DictionaryManagementPresenter` (a mock whose `dictionary_names` is `["default"]`) or the two functions on the presenter module. Its assertions do not change.
- Lines that set `frame._dictionary_names` are removed; the tests already mock `get_dictionary_names_for_dialog`.
- New: `on_open_dictionary_management` constructs the dialog with `(frame, frame._dictionary_presenter, <refreshed selection>)`; `wx.ID_EDIT` with a name opens `SpeechSymbolsDialog` with `presenter.dictionary_path(name)`; any other result opens nothing. `get_dictionary_names_for_dialog` refreshes with the active name and returns the presenter's names. The presenter built by `_initialize_state` calls back into `_set_active_dictionary`, which writes `set_selected_dictionary` once.

### Unchanged safety net

`test_dictionary_manager`, `test_dictionary_actions`, `test_translation_dictionary_state`, `test_dictionary_name_prompt`, `test_dictionary_entries`, `test_speech_symbols_dialog`, `test_settings_dialogs`, `test_i18n` (its scan for duplicated translation setup also covers the new module) must pass without edits.

## Acceptance Criteria

1. `client/dictionaries/presenter.py` exists, does not import `wx`, and defines `DictionaryManagementPresenter`, `DictionaryManagementView` and `DictionaryManagementActions`.
2. In `client/` outside `tests/`: `prompt_dictionary_name_until_success(` is called exactly once (in the presenter), and the msgid `Dictionary "{name}" already exists.` appears exactly once.
3. `client/gui.py` contains none of `_dictionary_names`, `_refresh_dictionary_names`, `add_dictionary`, `delete_dictionary_from_dialog`, `rename_dictionary_from_dialog`, `import_dictionary_from_dialog`, `export_dictionary_from_dialog`, `_prompt_for_dictionary_name`, `_get_csv_wildcard`.
4. `DictionaryManagementDialog.__init__` takes `(parent, actions, selected_name)`. `client/dialog.py` does not call `list_dictionary_names`.
5. The set of msgids passed to `_()`/`N_()` in `client/` outside `tests/` is identical before and after (checked with an AST scan, because `xgettext` is not installed on the Linux box). The `.po` and `.mo` are unchanged.
6. From `client/`: `python -m unittest tests.test_dictionary_presenter tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_actions tests.test_translation_dictionary_state tests.test_dictionary_name_prompt tests.test_gui_document_flows -v` passes.
7. `python -m unittest discover -s tests` from `client/`: 482 plus the new tests, `failures=1` (only the P2-5 case), `skipped=7`, no errors.
8. Manual check on Windows (not possible on the Linux box; must be reported as not run): open Dictionary Management and walk through add (including a duplicate name), rename (active and non-active), delete (active and non-active, then check Settings shows the fallback), import (valid file, file without headers), export, and edit. Each prompt, message and list selection matches the current build.

## Out of scope

- `SpeechSymbolsDialog` and an entry-list model (S-4, P1).
- `SettingsPanel`'s `owner` protocol (I-2, P2) and the Settings dialog's dictionary choice.
- Moving `translation/dictionary_state.py` or merging it with `dictionaries/actions.py`.
- Changing any exception quirk listed below, any string, or the "Add Dictionary" title used by import.
- Other `gui.py` extractions (S-1 items 1, 2, 4, 5) and `config.py` (S-5).

## Known issues / follow-ups

Preserved on purpose here, pinned by tests so a later change is deliberate:

- Add does not catch non-`FileExistsError` `OSError` from `create_dictionary`, so a disk error escapes the button handler with no message box.
- Delete does not catch `ValueError` from `delete_dictionary` (only reachable for an externally created file whose stem strips to `default`).
- Import shows the header message for every `ValueError`, including an invalid name or an undecodable file.
- `normalize_base_name` errors shown by add and rename are untranslated English.
- Add and import ignore the plan's `active_selected_name`, so these flows never correct or persist an active dictionary whose file has gone missing.

## Risks

- **Message parent or order drifts.** Mitigated by the full-sequence assertions in the presenter tests and by the dialog view-method tests that assert `parent=dialog` and exact arguments.
- **Strings translated at import time instead of call time.** All `_()` calls in the presenter and the dialog view methods run at call time, like today. Reviewed in the plan; `test_i18n` keeps guarding the shared catalog.
- **`test_gui_document_flows` patch targets.** Patching a name that `gui` no longer imports raises `AttributeError`. The plan updates `_initialize_state_with_loaded_tables` in the same commit that removes the imports.
- **Speech stub constants.** Using new `wx` names in `dialog.py` under the speech stub yields auto-submodules. If tests need distinct flag values, constants are added to `speech_dialog_stubs()` without changing `test_speech_symbols_dialog` results.
- **Windows-only verification.** wxPython is not installed on the Linux box, so real dialogs cannot be exercised here. Acceptance 8 is a manual step for a Windows machine and must be reported as not run until someone does it.
