# Translation Tables Frame State (P0-2) Design

## Goal

Move the active translation-table mapping out of the module-level mutable global `gui.language_map_translate_table` and into `BrailleFrame` instance state, and merge the two identical "default table not selected" checks into one helper. This is roadmap task P0-2 in `storage/refactor.md` (section 6.1), covering finding D-2 (section 3.5, DIP) and the `gui.py:230` entry under 5.2 (global state).

This is a behavior-preserving refactor. No user-visible behavior, string or persisted data changes.

## Current State (verified 2026-10-08 on `refactor/p0-2-translation-tables-state`, HEAD `506a8da`, P0-1 merged)

`client/gui.py` uses tabs for indentation. `client/tests/test_gui_document_flows.py` uses 4 spaces.

Every read and write of the global (repository-wide `grep -rn language_map_translate_table` over `*.py`):

| Location | What it does |
| --- | --- |
| `gui.py:230` | Module import creates it: `language_map_translate_table = load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()`. This reads `config.json` at `import gui` time, before `BrailleApp.OnInit` prepares the application directories. |
| `gui.py:622` (`get_settings_snapshot`) | Passes the global to `DotExpressSettingsSnapshot.create`, which copies it with `dict(...)`. |
| `gui.py:637-638` (`apply_settings_from_dialog`) | `clear()` + `update(tables)` mutates the global in place, after `tables = dict(snapshot.translation_tables)`. Then `save_translation_tables(tables)` persists it. |
| `gui.py:790` (`_build_conversion_request`) | `translation_tables=language_map_translate_table.copy()` gives the background conversion job its own copy. |
| `gui.py:1529-1535` (`_start_export_conversion`) | `default_table = ...get("default")`; if falsy, builds `_("Please select a translation table first.")` and sends it to `on_missing_table`, else `on_error`, else nowhere; returns `False`. |
| `gui.py:1609-1617` (`on_convert`) | Same `get("default")` check; if falsy, shows `wx.MessageBox(<same message>, _("Info"), wx.OK \| wx.ICON_INFORMATION, parent=self)` and returns. |
| `tests/test_gui_document_flows.py:1087, 1129` | `patch.dict(gui.language_map_translate_table, {"default": ""}, clear=True)` in the two missing-table export tests. |
| `tests/test_gui_document_flows.py:1161` | `test_apply_settings_from_dialog_updates_all_live_state` asserts on the global. It does not restore it, so the global stays `{"default": "en-ueb-g1.ctb", "math": "Nemeth"}` for the rest of the test process (cross-test leakage). |

No other module or test imports or patches the global. `client/main.py` uses `config.DEFAULT_TRANSLATION_TABLES` directly and is unaffected. Older documents under `docs/` (`2026-07-06-*` specs and plans, `docs/refactor/refactor4.md`, history) mention the name; they are historical records and are not edited.

Related facts:

- `settings.translation_tables.load_translation_tables()` returns `dict(config.get_translation_tables())`. `config._get_dict_setting` always merges stored string values over `DEFAULT_TRANSLATION_TABLES`, so the result is never empty and the `or DEFAULT_TRANSLATION_TABLES.copy()` fallback is unreachable in practice. A stored value can still be `""` (for example a hand-edited `"default": ""`), because the merge accepts any `str`.
- The settings dialog (`settings/dialogs.py`, `TranslationTablesPanel`) reads and writes only `snapshot.translation_tables`. Its `is_valid`/`validation_error` refuse to save an empty `default` or `math`. Non-string stored values are dropped by the merge and fall back to the default table. So the "default table not selected" guard in `gui.py` is reached only when `config.json` holds `"default": ""` (hand-edited, or written by an older build). It is a guard, not dead code, and must stay.
- `DotExpressSettingsSnapshot` (`settings/state.py`) is frozen and copies `translation_tables` on `create`, `with_translation_tables` and `copied`. The dialog commits through `BrailleFrame.apply_settings_from_dialog` and reloads its panels from the returned snapshot.
- The frame already keeps the other two settings groups as plain instance attributes: `self.translation_settings` (set in `_initialize_state`) and `self.view_settings`. They are reassigned, not mutated, in `apply_settings_from_dialog`.
- Conversion runs on a worker thread (`ConversionJobRunner`). The request receives a copy of the tables, so later settings changes never affect a running job.
- Tests build frames with `BrailleFrame.__new__` / `object.__new__` and set only the attributes they need; `__init__` and `_initialize_state` never run in tests.
- Baseline: `tests.test_gui_document_flows` runs 50 tests, OK. Full suite: 439 tests, `failures=1` (the known P2-5 `test_conversion_service` failure), `skipped=7`.

## Design

### Ownership

`BrailleFrame` owns the active mapping as `self.translation_tables: dict[str, str]`, alongside `translation_settings` and `view_settings`.

- It is initialized in `_initialize_state`, next to `self.translation_settings = load_translation_settings(...)`, with the same expression as today: `load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()`. The unreachable fallback is kept so this change does not touch fallback behavior or imports.
- The module-level `language_map_translate_table` is deleted. `gui` no longer reads `config.json` at import time for tables.
- The attribute is treated as replace-only: code assigns a new dict and never mutates the existing one. This is the same discipline the other two settings attributes follow.

Storing `self.settings_snapshot` instead (the roadmap's alternative) is rejected for P0-2: it would also change how `translation_settings` and `view_settings` are owned, which is out of scope and touches many more call sites.

### Settings propagation

`apply_settings_from_dialog` replaces the reference instead of mutating in place:

```python
tables = dict(snapshot.translation_tables)
self.translation_settings = translation
self.view_settings = view
self.translation_tables = tables
```

The statement order, the save calls (`save_translation_settings`, `save_translation_tables(tables)`, `save_view_settings`) and the return value `DotExpressSettingsSnapshot.create(translation, tables, view)` stay unchanged. Because `create` copies, the returned snapshot never aliases frame state.

Readers:

- `get_settings_snapshot` passes `self.translation_tables` (copied by `create`, as today).
- `_build_conversion_request` passes `self.translation_tables.copy()`. The copy stays: the worker thread must keep its own dict, and the conversion pipeline must not be able to mutate frame state.

### Merged default-table check

Add one frame method that owns both the check and the message:

```python
def _missing_default_table_message(self) -> str | None:
	if self.translation_tables.get("default"):
		return None
	return _("Please select a translation table first.")
```

- `_start_export_conversion`: `message = self._missing_default_table_message()`; if it is not `None`, dispatch it to `on_missing_table`, else `on_error`, exactly as today, and return `False`.
- `on_convert`: same call; if it is not `None`, show the same `wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)` and return.
- The truthiness test is unchanged (`get("default")` falsy means missing: absent key, `""`, `None`).
- The literal `_("Please select a translation table first.")` remains a direct `_()` call, so gettext extraction and the existing `.po` entry are unaffected. The string appears once in `gui.py` instead of twice.

Naming: the roadmap suggests `_require_default_table() -> str | None`. That name does not say whether the string is the table or the error. The helper returns the message because both callers need the message and neither uses the table name. This is a naming-only deviation.

The local variable `default_table` in both callers goes away; nothing else used it.

## What Stays Identical

- All user-visible behavior: the missing-table message text, its `Info` dialog in `on_convert`, the callback dispatch order (`on_missing_table` before `on_error`) and the `False` return in `_start_export_conversion`, and batch export's per-document failure accumulation without per-file message boxes.
- The values the frame starts with (same loader, same fallback), what the settings dialog shows, what it saves, and when it saves.
- `ConversionRequest.translation_tables` contents, and that each request gets an independent copy.
- `settings/state.py`, `settings/dialogs.py`, `settings/translation_tables.py`, `config.py` and the conversion package are untouched.
- No `.po`/`.mo` change: no user-facing string is added, removed or edited.

The only observable difference is timing: the tables are read from `config.json` when `BrailleFrame` is constructed (inside `BrailleApp.OnInit`, after `prepare_application_directories`) instead of when `gui` is imported. Nothing writes translation tables between those two points, so the loaded values are the same. Any config read failure is now logged after `log/` exists, which is an improvement.

## Test Changes (`client/tests/test_gui_document_flows.py`)

Patch points move from the module global to the frame attribute:

- `_make_frame` sets `frame.translation_tables = dict(gui.DEFAULT_TRANSLATION_TABLES)`, so a test frame looks like a real one by default.
- `test_export_all_missing_table_accumulates_failures_without_per_file_message_boxes` and `test_single_pending_export_missing_table_shows_one_error_dialog_and_does_not_write_output`: drop the `patch.dict(gui.language_map_translate_table, ...)` context and set `frame.translation_tables = {"default": ""}` before the call. All other assertions stay.
- `test_apply_settings_from_dialog_updates_all_live_state`: assert `frame.translation_tables == snapshot.translation_tables` and `frame.translation_tables is not snapshot.translation_tables`. This removes the cross-test leakage.

New tests (same file, same stub setup):

1. **The global is gone:** `self.assertFalse(hasattr(gui, "language_map_translate_table"))`.
2. **Initialization:** `_initialize_state` sets `translation_tables` from `load_translation_tables()`, and falls back to `DEFAULT_TRANSLATION_TABLES` when the loader returns `{}`. Patch the collaborators `_initialize_state` calls (`get_dictionary_directory`, `ensure_default_dictionary`, `list_dictionary_names`, `load_translation_settings`, `get_workspace_directory`, `load_view_settings`, `load_translation_tables`, and the frame's `_refresh_dictionary_names` / `_register_output_font`), so no real directory or config file is touched.
3. **Snapshot reads frame state:** `get_settings_snapshot` returns tables equal to, and not the same object as, `frame.translation_tables`.
4. **Request copies frame state:** `_build_conversion_request(...).translation_tables` equals `frame.translation_tables` and is a different object.
5. **Propagation:** after `apply_settings_from_dialog(snapshot)` (saves patched), `_build_conversion_request` carries the new tables.
6. **Helper:** `_missing_default_table_message()` returns `None` for `{"default": "zh-tw.ctb"}` and the translated message for `{}`, `{"default": ""}` and `{"default": None}`.
7. **`on_convert` guard:** with `{"default": ""}`, it calls `wx.MessageBox` once with the message, `_("Info")`, `wx.OK | wx.ICON_INFORMATION`, `parent=frame`, and does not call `_start_conversion`. With a configured default it calls `_start_conversion` once and shows no message box.
8. **Export happy path:** with a configured default, `_start_export_conversion` returns `True` and calls `_start_conversion` with `update_output=False, show_success=False`.

No other test file changes. `tests/test_settings_dialogs.py`, `tests/test_settings_state.py`, `tests/test_translation_tables.py` and `tests/test_conversion_jobs.py` stay green as unchanged safety nets.

## Acceptance Criteria

1. `grep -rn "language_map_translate_table" client --include=*.py` returns exactly one line: the guard test `self.assertFalse(hasattr(gui, "language_map_translate_table"))` in `client/tests/test_gui_document_flows.py` (the test must name the attribute). `grep -rn "language_map_translate_table" client --include=*.py | grep -v "^client/tests/"` returns nothing.
2. `grep -n 'Please select a translation table first' client/gui.py` returns exactly one line, inside `_missing_default_table_message`.
3. `BrailleFrame` reads and replaces `self.translation_tables` only; no code calls `clear()`/`update()` or otherwise mutates it in place.
4. Focused verification passes with 0 failures and 0 errors:
   `cd client && python3 -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_settings_state tests.test_translation_tables tests.test_conversion_jobs -v`
5. Full suite: `cd client && python3 -m unittest discover -s tests -p "test_*.py"` reports `failures=1` (only the known P2-5 failure), `errors=0`, `skipped=7`, with 439 tests plus the new ones.
6. No changes to `client/locales/`.
7. Not verifiable on this Linux host: the real wxPython app on Windows (opening Settings, changing tables, converting, exporting). The change does not touch any Windows-specific code, and wx calls stay the same.

## Risks

- **A path reads `self.translation_tables` before `_initialize_state` sets it** (low): `__init__` runs `_initialize_state` before layout, conversion state and event binding, so no handler can fire earlier. Tests that bypass `__init__` get the attribute from `_make_frame` or set it explicitly. On a real wxPython frame a missing attribute raises a plain `AttributeError`. Under the test wx stubs it does not: the stub `wx._Widget.__getattr__` returns a no-op function for any missing attribute, so the failure surfaces one step later (`AttributeError: 'function' object has no attribute ...` from `.get`/`.copy`, `TypeError` from `dict(function)` in `DotExpressSettingsSnapshot.create`, or a silent `None` from calling a not-yet-defined method). The tests in this spec still fail loudly in every case they rely on, but expected pre-implementation failures are assertion failures rather than `AttributeError`s.
- **Thread safety** (unchanged): the worker receives a copy built on the UI thread, and the frame attribute is only replaced on the UI thread.
- **Hidden external users of the global** (none found): grep shows no import or patch outside `gui.py` and `test_gui_document_flows.py`.
- **Overlap with later tasks** (low): P0-3 and later `gui.py` tasks must use `self.translation_tables`. P0-4 moves the wx stubs out of `test_gui_document_flows.py` but keeps `_make_frame`, so the attribute default set there survives. P0-5 moves `_`/gettext into `i18n.py`; only the import of `_` changes, the helper keeps its direct `_()` call. P2-6 (`ApplicationPaths` injection) may later move the loader call; the ownership decided here stays valid.

## Out of Scope

- Storing a whole `DotExpressSettingsSnapshot` on the frame or otherwise unifying the three settings attributes.
- Removing the unreachable `or DEFAULT_TRANSLATION_TABLES.copy()` fallback.
- Validating table names or types loaded from `config.json`.
- Extracting a shared wx-stub module for tests (P0-4).
- Editing historical documents that mention the old global.
