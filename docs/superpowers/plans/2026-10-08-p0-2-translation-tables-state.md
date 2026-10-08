# Translation Tables Frame State (P0-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the module-level mutable global `gui.language_map_translate_table` with `BrailleFrame.translation_tables` instance state, and merge the two duplicated "default table not selected" checks into one helper, without changing user-visible behavior.

**Architecture:** `BrailleFrame._initialize_state` loads the mapping into `self.translation_tables` (same loader, same fallback). `apply_settings_from_dialog` replaces the reference instead of mutating in place. `get_settings_snapshot` and `_build_conversion_request` read the attribute (both still copy). A new `_missing_default_table_message()` owns the check and the message for `_start_export_conversion` and `on_convert`. The module global is deleted last.

**Tech Stack:** Python 3 (wxPython app; wx is stubbed in tests), `unittest`, `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-10-08-p0-2-translation-tables-state-design.md` (authoritative, except for the two corrections below).

## Global Constraints

- Branch: `refactor/p0-2-translation-tables-state`. Never switch to or merge into `main`, never push, never rewrite history.
- `client/gui.py` uses TABS. `client/tests/test_gui_document_flows.py` uses 4 spaces. Keep each file's style; do not reformat unrelated code.
- Production changes are limited to `client/gui.py`. Do not touch `settings/state.py`, `settings/dialogs.py`, `settings/translation_tables.py`, `config.py`, the conversion package, or `client/locales/`.
- `self.translation_tables` is replace-only: assign a new dict, never call `clear()`/`update()`/item assignment on it.
- Keep the expression `load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()` (the unreachable fallback stays; out of scope).
- Keep `_("Please select a translation table first.")` as a direct `_()` literal call so gettext extraction still finds it.
- Test placement: add every new test to the end of `BrailleAppLifecycleTest` (immediately before `test_open_settings_uses_singleton_dialog`). Do NOT add tests to `GuiDocumentFlowsTest`: `BrailleAppLifecycleTest` subclasses it, so its tests run twice and the counts below would be wrong.
- Test command prefix used below: `PY=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad/venv/bin/python` (elsewhere, any Python 3.10+ with client deps, e.g. `python3`). All test commands run from `client/`, which must contain the (git-ignored) `log/` directory, as the working tree does today.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Spec Corrections (decided in this plan)

1. **Acceptance Criterion 1 contradicts the spec's own new test 1.** The criterion says `grep -rn "language_map_translate_table" client --include=*.py` returns nothing, but the required guard test `self.assertFalse(hasattr(gui, "language_map_translate_table"))` contains that name. Corrected criterion: the grep returns exactly one line, the guard test in `client/tests/test_gui_document_flows.py`; `grep -rn "language_map_translate_table" client --include=*.py | grep -v "^client/tests/"` returns nothing. (Task 5, Step 4.)
2. **Risk 1 says a frame missing the attribute "fails loudly with `AttributeError`". Not true under the test wx stubs.** The stub `wx._Widget` (base of the stub `wx.Frame`) defines `__getattr__` returning a no-op function for any missing attribute. So on a stub frame without `translation_tables`, the access itself does not raise: `.get`/`.copy` then raise `AttributeError: 'function' object has no attribute ...`, `DotExpressSettingsSnapshot.create` raises `TypeError` from `dict(function)`, and a call to a not-yet-defined method such as `_missing_default_table_message()` silently returns `None`. Tests still fail loudly in every case this plan relies on (verified), and real wxPython frames raise a plain `AttributeError`. Consequence for this plan: the expected pre-implementation failures in Tasks 1 and 3 are assertion failures, not `AttributeError`s, and are listed exactly below.

Neither correction changes the design.

## Review Focus

1. A user who set an empty default table (hand-edited `config.json` `"default": ""`) presses Convert: still exactly one `Info` box with the same message, and no conversion. Test: `test_convert_without_default_table_shows_info_and_does_not_convert` (Task 2).
2. Export All with an empty default table: per-document failures accumulate, no per-file message boxes; single export shows one `Error` box. Tests: the two migrated missing-table tests (Task 2).
3. The user changes tables in Settings, then converts: the next background job uses the new tables, and the job's dict is independent from frame state. Tests: `test_applied_settings_tables_reach_next_conversion_request`, `test_conversion_request_copies_frame_translation_tables` (Task 2).
4. Settings dialog round trip never aliases frame state (snapshot in, snapshot out), and applying settings never mutates the previous dict in place. Test: updated `test_apply_settings_from_dialog_updates_all_live_state` (Task 2).
5. Startup: tables are loaded when the frame is built, with the same fallback; `import gui` no longer reads `config.json` for tables. Tests: Task 1 and `test_translation_tables_are_not_module_state` (Task 4).

## File Map

- Modify `client/gui.py`: `_initialize_state` (Task 1); `get_settings_snapshot`, `apply_settings_from_dialog`, `_build_conversion_request`, `_start_export_conversion`, `on_convert` (Task 2); new `_missing_default_table_message` and both callers (Task 3); delete module global at line 230 (Task 4).
- Modify `client/tests/test_gui_document_flows.py`: `_make_frame` default (Task 1); migrate three existing tests (Task 2); add 10 tests plus one test helper method (Tasks 1-4).

Line numbers below are at `46c1099` (spec commit) and shift as tasks land; locate code by the quoted text.

---

### Task 1: Load translation tables into frame state

**Files:**
- Modify: `client/gui.py:326-342` (`_initialize_state`)
- Modify: `client/tests/test_gui_document_flows.py:347-365` (`_make_frame`), end of `BrailleAppLifecycleTest`

**Interfaces:**
- Produces: `BrailleFrame.translation_tables: dict[str, str]`, set by `_initialize_state`. Nothing reads it yet; the global is still the live source after this task (consistent intermediate state).

- [ ] **Step 1: Write the failing tests**

In `_make_frame`, add one line just before `return frame`:

```python
        frame.translation_tables = dict(gui.DEFAULT_TRANSLATION_TABLES)
```

At the end of `BrailleAppLifecycleTest`, immediately before `def test_open_settings_uses_singleton_dialog`, add:

```python
    def _initialize_state_with_loaded_tables(self, loaded_tables: dict[str, str]):
        frame = object.__new__(gui.BrailleFrame)
        frame._refresh_dictionary_names = Mock()
        frame._register_output_font = Mock(return_value=False)
        with (
            patch.object(gui, "get_dictionary_directory", return_value=Path("dictionary")),
            patch.object(gui, "ensure_default_dictionary"),
            patch.object(gui, "list_dictionary_names", return_value=["default"]),
            patch.object(
                gui,
                "load_translation_settings",
                return_value=TranslationSettings("unicode", 40, "default"),
            ),
            patch.object(gui, "get_workspace_directory", return_value=Path("workspace")),
            patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
            patch.object(gui, "load_translation_tables", return_value=loaded_tables) as load_tables,
        ):
            frame._initialize_state()
        return frame, load_tables

    def test_initialize_state_loads_translation_tables_into_frame(self) -> None:
        loaded_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}

        frame, load_tables = self._initialize_state_with_loaded_tables(loaded_tables)

        self.assertEqual(frame.translation_tables, loaded_tables)
        load_tables.assert_called_once_with()

    def test_initialize_state_falls_back_to_default_tables_when_loader_returns_empty(self) -> None:
        frame, _load_tables = self._initialize_state_with_loaded_tables({})

        self.assertEqual(frame.translation_tables, gui.DEFAULT_TRANSLATION_TABLES)
        self.assertIsNot(frame.translation_tables, gui.DEFAULT_TRANSLATION_TABLES)
```

Notes: every collaborator of `_initialize_state` that touches disk is patched (`DocumentController()` is real and in-memory). `object.__new__` is used, not `_make_frame`, so the `_make_frame` default cannot mask a missing assignment.

- [ ] **Step 2: Run to verify they fail**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_gui_document_flows -v`
Expected: `Ran 52 tests`, `FAILED (failures=2)`. Both new tests fail with `AssertionError: <function _install_stub_modules.<locals>...> != {...}` (the stub `__getattr__` returns a function for the missing attribute; see Spec Correction 2).

- [ ] **Step 3: Implement**

In `client/gui.py` `_initialize_state`, directly after `self.translation_settings = load_translation_settings(self._dictionary_names)`, add:

```python
		self.translation_tables = load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()
```

(tab-indented, two tabs). Leave the module global untouched in this task.

- [ ] **Step 4: Run to verify they pass**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_gui_document_flows -v`
Expected: `Ran 52 tests`, `OK`.

- [ ] **Step 5: Commit**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py
git commit -m "refactor: load translation tables into frame state

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Read and replace translation tables on the frame

All readers and the single writer move together so every commit has exactly one live source of truth (moving only some of them would let Settings changes miss the missing-table check, or vice versa).

**Files:**
- Modify: `client/gui.py:618-624` (`get_settings_snapshot`), `:626-644` (`apply_settings_from_dialog`), `:783-791` (`_build_conversion_request`), `:1529` (`_start_export_conversion`), `:1609` (`on_convert`)
- Modify: `client/tests/test_gui_document_flows.py:1075-1105`, `:1107-1141`, `:1143-1164`, end of `BrailleAppLifecycleTest`

**Interfaces:**
- Consumes: `BrailleFrame.translation_tables` (Task 1).
- Produces: the global is no longer read or written by any method (only created at import; deleted in Task 4).

- [ ] **Step 1: Migrate the three existing tests**

In `test_export_all_missing_table_accumulates_failures_without_per_file_message_boxes`: delete the line `patch.dict(gui.language_map_translate_table, {"default": ""}, clear=True),` from the `with (...)` block, and add `frame.translation_tables = {"default": ""}` on its own line directly before that `with (`. All assertions stay.

In `test_single_pending_export_missing_table_shows_one_error_dialog_and_does_not_write_output`: same two edits (the new line goes after the `_AcceptedFileDialog` class, directly before `with (`). All assertions stay.

In `test_apply_settings_from_dialog_updates_all_live_state`: after the `snapshot = make_snapshot(...)` statement add

```python
        previous_tables = {"default": "zh-tw.ctb"}
        frame.translation_tables = previous_tables
```

and replace `self.assertEqual(gui.language_map_translate_table, snapshot.translation_tables)` with

```python
        self.assertEqual(frame.translation_tables, snapshot.translation_tables)
        self.assertIsNot(frame.translation_tables, snapshot.translation_tables)
        self.assertIsNot(result.translation_tables, frame.translation_tables)
        self.assertEqual(previous_tables, {"default": "zh-tw.ctb"})
```

The last assertion pins the replace-only rule (Acceptance Criterion 3): an in-place `clear()`/`update()` on the old dict would fail it. The `result` aliasing assertion pins the spec's "the returned snapshot never aliases frame state". Both are small additions beyond the spec's test list. This test no longer leaks into the module global.

- [ ] **Step 2: Add the new tests**

At the end of `BrailleAppLifecycleTest`, immediately before `def test_open_settings_uses_singleton_dialog`, add:

```python
    def test_settings_snapshot_reads_frame_translation_tables(self) -> None:
        frame = self._make_frame()
        frame.translation_settings = TranslationSettings("unicode", 40, "default")
        frame.view_settings = ViewSettings(40, "light", "default")
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        frame.translation_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}

        snapshot = frame.get_settings_snapshot()

        self.assertEqual(
            snapshot.translation_tables,
            {"default": "test-default.ctb", "math": "test-math.ctb"},
        )
        self.assertIsNot(snapshot.translation_tables, frame.translation_tables)

    def test_conversion_request_copies_frame_translation_tables(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": "test-default.ctb", "math": "test-math.ctb"}

        request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))

        self.assertEqual(
            request.translation_tables,
            {"default": "test-default.ctb", "math": "test-math.ctb"},
        )
        self.assertIsNot(request.translation_tables, frame.translation_tables)

    def test_applied_settings_tables_reach_next_conversion_request(self) -> None:
        frame = self._make_frame()
        frame._dictionary_names = ["default"]
        frame._apply_editor_view_settings = Mock()
        frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
        snapshot = make_snapshot(tables={"default": "test-default.ctb", "math": "test-math.ctb"})

        with patch.object(gui, "save_translation_settings"), \
             patch.object(gui, "save_translation_tables"), \
             patch.object(gui, "save_view_settings"):
            frame.apply_settings_from_dialog(snapshot)
        request = frame._build_conversion_request("source", "unicode", 40, Path("dictionary/default.csv"))

        self.assertEqual(request.translation_tables, snapshot.translation_tables)

    def test_convert_without_default_table_shows_info_and_does_not_convert(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": ""}
        frame._start_conversion = Mock()

        with patch.object(gui.wx, "MessageBox") as message_box:
            frame.on_convert(None)

        message_box.assert_called_once_with(
            gui._("Please select a translation table first."),
            gui._("Info"),
            gui.wx.OK | gui.wx.ICON_INFORMATION,
            parent=frame,
        )
        frame._start_conversion.assert_not_called()

    def test_convert_with_default_table_starts_conversion_without_message(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": "zh-tw.ctb"}
        frame.translation_settings = TranslationSettings("ascii", 32, "default")
        frame.input_txt.GetValue.return_value = "source"
        frame._get_selected_dictionary_path = Mock(return_value=Path("dictionary/default.csv"))
        frame._start_conversion = Mock()

        with patch.object(gui.wx, "MessageBox") as message_box:
            frame.on_convert(None)

        frame._start_conversion.assert_called_once_with(
            "source",
            32,
            "ascii",
            Path("dictionary/default.csv"),
        )
        message_box.assert_not_called()

    def test_export_conversion_with_default_table_starts_background_conversion(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": "zh-tw.ctb"}
        frame.translation_settings = TranslationSettings("ascii", 32, "default")
        frame._get_selected_dictionary_path = Mock(return_value=Path("dictionary/default.csv"))
        frame._start_conversion = Mock()
        on_success = Mock()
        on_error = Mock()
        on_missing_table = Mock()

        started = frame._start_export_conversion(
            Document("alpha", "text", None),
            Path("/tmp/export/alpha.brl"),
            "brl",
            on_success=on_success,
            on_error=on_error,
            on_missing_table=on_missing_table,
        )

        self.assertTrue(started)
        frame._start_conversion.assert_called_once_with(
            "text",
            32,
            "ascii",
            Path("dictionary/default.csv"),
            on_success=on_success,
            on_error=on_error,
            update_output=False,
            show_success=False,
        )
        on_missing_table.assert_not_called()
        on_error.assert_not_called()
```

- [ ] **Step 3: Run to verify they fail**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_gui_document_flows -v`
Expected: `Ran 58 tests`, `FAILED (failures=3, errors=3)`:
- FAIL `test_settings_snapshot_reads_frame_translation_tables`, FAIL `test_conversion_request_copies_frame_translation_tables` (actual value is the module global's contents, not the `test-*.ctb` tables).
- FAIL `test_apply_settings_from_dialog_updates_all_live_state` (`{'default': 'zh-tw.ctb'} != {'default': 'en-ueb-g1.ctb', 'math': 'Nemeth'}`: the frame attribute was not replaced).
- ERROR `test_convert_without_default_table_shows_info_and_does_not_convert` (`AttributeError: 'function' object has no attribute 'width'`: the guard read the global, which has a default, so conversion was attempted).
- ERROR in both migrated missing-table tests (`TypeError: argument should be a str or an os.PathLike object ... not 'function'`: same reason, export conversion was attempted).

The other three new tests (`test_applied_settings_tables_reach_next_conversion_request`, `test_convert_with_default_table_starts_conversion_without_message`, `test_export_conversion_with_default_table_starts_background_conversion`) already pass: they pin end-to-end behavior that must survive the move. (They pass before the change only because the global's `default` is non-empty, which holds unless the developer's real `config.json` has `"default": ""`; after the change they no longer depend on the real config.)

- [ ] **Step 4: Implement**

In `client/gui.py` (tabs):

`get_settings_snapshot`: replace the argument line `language_map_translate_table,` with `self.translation_tables,`.

`apply_settings_from_dialog`: replace

```python
		language_map_translate_table.clear()
		language_map_translate_table.update(tables)
```

with

```python
		self.translation_tables = tables
```

so the block reads `self.translation_settings = translation`, `self.view_settings = view`, `self.translation_tables = tables`, then `self._apply_editor_view_settings(view)`. Saves and the return statement are unchanged.

`_build_conversion_request`: `translation_tables=language_map_translate_table.copy(),` becomes `translation_tables=self.translation_tables.copy(),`.

`_start_export_conversion` and `on_convert`: `default_table = language_map_translate_table.get("default")` becomes `default_table = self.translation_tables.get("default")` (both occurrences; the helper comes in Task 3).

After this step `grep -n "language_map_translate_table" client/gui.py` shows only the module-level assignment.

- [ ] **Step 5: Run to verify they pass**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_settings_state -v`
Expected: `OK` (58 tests in `test_gui_document_flows`).

- [ ] **Step 6: Commit**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py
git commit -m "refactor: read translation tables from frame state

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Merge the default-table check into one helper

**Files:**
- Modify: `client/gui.py` `_start_export_conversion` (~line 1519) and `on_convert` (~line 1605)
- Modify: `client/tests/test_gui_document_flows.py`, end of `BrailleAppLifecycleTest`

**Interfaces:**
- Produces: `BrailleFrame._missing_default_table_message(self) -> str | None`: `None` when `self.translation_tables.get("default")` is truthy, else the translated `"Please select a translation table first."`. (Name deviates from the roadmap's `_require_default_table`; rationale in the spec.)

- [ ] **Step 1: Write the failing test**

At the end of `BrailleAppLifecycleTest`, immediately before `def test_open_settings_uses_singleton_dialog`, add:

```python
    def test_missing_default_table_message_reports_only_unset_default(self) -> None:
        frame = self._make_frame()
        frame.translation_tables = {"default": "zh-tw.ctb"}

        self.assertIsNone(frame._missing_default_table_message())

        for tables in ({}, {"default": ""}, {"default": None}):
            with self.subTest(tables=tables):
                frame.translation_tables = tables
                self.assertEqual(
                    frame._missing_default_table_message(),
                    gui._("Please select a translation table first."),
                )
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_gui_document_flows -v`
Expected: `Ran 59 tests`, `FAILED (failures=3)`, all three are subtests of the new test (`tables={}`, `{'default': ''}`, `{'default': None}`) with `AssertionError: None != '<translated message>'` (zh_TW `.mo` is loaded, so the message shows in Chinese). The `assertIsNone` line passes before implementation because the stub `__getattr__` returns a no-op function for the undefined method (Spec Correction 2); the subtests catch the missing method.

- [ ] **Step 3: Implement**

In `client/gui.py`, directly above `def _start_export_conversion(`, add (tabs):

```python
	def _missing_default_table_message(self) -> str | None:
		if self.translation_tables.get("default"):
			return None
		return _("Please select a translation table first.")

```

In `_start_export_conversion`, replace

```python
		default_table = self.translation_tables.get("default")
		if not default_table:
			message = _("Please select a translation table first.")
			if on_missing_table is not None:
```

with

```python
		message = self._missing_default_table_message()
		if message is not None:
			if on_missing_table is not None:
```

(the `on_missing_table` / `elif on_error` dispatch and `return False` stay as they are).

In `on_convert`, replace

```python
		default_table = self.translation_tables.get("default")
		if not default_table:
			wx.MessageBox(
				_("Please select a translation table first."),
				_("Info"),
```

with

```python
		message = self._missing_default_table_message()
		if message is not None:
			wx.MessageBox(
				message,
				_("Info"),
```

(`wx.OK | wx.ICON_INFORMATION, parent=self,` and the `return` stay).

- [ ] **Step 4: Run to verify it passes**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_gui_document_flows -v`
Expected: `Ran 59 tests`, `OK`. The Task 2 guard tests (`test_convert_without_default_table_shows_info_and_does_not_convert`, both migrated missing-table tests, the export happy path) prove both callers kept their behavior.

Run: `cd /workspace/DotExpress && grep -n 'Please select a translation table first' client/gui.py`
Expected: exactly one line, inside `_missing_default_table_message`.

- [ ] **Step 5: Commit**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py
git commit -m "refactor: merge default translation table check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Remove the module-level translation tables global

**Files:**
- Modify: `client/gui.py:230`
- Modify: `client/tests/test_gui_document_flows.py`, end of `BrailleAppLifecycleTest`

**Interfaces:**
- Produces: `gui` has no `language_map_translate_table`; `import gui` no longer reads translation tables from `config.json`.

- [ ] **Step 1: Write the failing test**

At the end of `BrailleAppLifecycleTest`, immediately before `def test_open_settings_uses_singleton_dialog`, add:

```python
    def test_translation_tables_are_not_module_state(self) -> None:
        self.assertFalse(hasattr(gui, "language_map_translate_table"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_gui_document_flows -v`
Expected: `Ran 60 tests`, `FAILED (failures=1)`: `test_translation_tables_are_not_module_state` with `AssertionError: True is not false`.

- [ ] **Step 3: Implement**

In `client/gui.py`, delete the line

```python
language_map_translate_table = load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()
```

and one of the blank lines around it, so the closing `)` of `_MENU_TRANSLATION_MARKERS` is followed by exactly two blank lines and then `def _prompt_for_dictionary_name(`. Keep the imports of `DEFAULT_TRANSLATION_TABLES` and `load_translation_tables`: `_initialize_state` uses both.

- [ ] **Step 4: Run to verify it passes**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_gui_document_flows -v`
Expected: `Ran 60 tests`, `OK`.

- [ ] **Step 5: Commit**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py
git commit -m "refactor: remove translation tables module global

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Final verification (no commit unless something had to be fixed)

- [ ] **Step 1: Focused verification (Acceptance Criterion 4)**

Run: `cd /workspace/DotExpress/client && $PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_settings_state tests.test_translation_tables tests.test_conversion_jobs -v`
Expected: `Ran 94 tests`, `OK` (60 + 34 unchanged safety-net tests).

- [ ] **Step 2: Full suite (Acceptance Criterion 5)**

Run: `cd /workspace/DotExpress/client && $PY -m unittest discover -s tests -p "test_*.py"`
Expected: `Ran 449 tests` (439 baseline + 10 new: 2 in Task 1, 6 in Task 2, 1 in Task 3, 1 in Task 4), `FAILED (failures=1, skipped=7)`, 0 errors. The single failure must be `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math` (P2-5). Any other failure or error is a regression. (If six `ERROR`s appear from `test_client_init`, `test_dual_view_frame`, `test_math_service` and `test_translation_runtime_provider`, `client/log/` is missing in the checkout being tested; that is environmental and unrelated to this change. Create `client/log/` and rerun.)

- [ ] **Step 3: Diff scope (Acceptance Criterion 6, "untouched" list)**

Run: `cd /workspace/DotExpress && git diff --stat 46c1099..HEAD -- client`
Expected: only `client/gui.py` and `client/tests/test_gui_document_flows.py`. In particular nothing under `client/locales/`.

- [ ] **Step 4: Static acceptance checks (Criteria 1-3, Criterion 1 as corrected)**

Run: `cd /workspace/DotExpress && grep -rn "language_map_translate_table" client --include=*.py`
Expected: exactly one line, `client/tests/test_gui_document_flows.py:...: self.assertFalse(hasattr(gui, "language_map_translate_table"))`.

Run: `cd /workspace/DotExpress && grep -n 'Please select a translation table first' client/gui.py`
Expected: exactly one line, inside `_missing_default_table_message`.

Run: `cd /workspace/DotExpress && grep -n "translation_tables" client/gui.py`
Expected: 8 lines: the `settings.translation_tables` import, the `_initialize_state` assignment, `self.translation_tables` passed to `DotExpressSettingsSnapshot.create` in `get_settings_snapshot`, `tables = dict(snapshot.translation_tables)`, `self.translation_tables = tables` and `save_translation_tables(tables)` in `apply_settings_from_dialog`, `translation_tables=self.translation_tables.copy()` in `_build_conversion_request`, and `.get("default")` in `_missing_default_table_message`. No `.clear()`, `.update(`, `.pop(`, `.setdefault(`, or `self.translation_tables[` (replace-only).

- [ ] **Step 5: Record what cannot be verified here**

State in the handoff:
- The real wxPython app on Windows (open Settings, change tables, Convert, Export, Export All) was not run (Linux host, wx stubbed). No Windows-specific code or wx call changed.
- No `.po`/`.mo` change: the msgid is unchanged, so translation lookup is unaffected. The `#: gui.py:1531 gui.py:1612` location comment in `dotexpress.pot`/`dotexpress.po` becomes stale (now one location); like other line references it refreshes the next time `scripts\generate_pot.bat` runs on Windows. It is not edited here (spec Acceptance Criterion 6).
