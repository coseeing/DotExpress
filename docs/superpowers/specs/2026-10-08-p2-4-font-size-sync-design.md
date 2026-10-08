# Font Size Sync (P2-4) Design

## Goal

Remove the reverse classmethod probe `DotExpressSettingsDialog.sync_open_font_size`. This is roadmap task P2-4 in `storage/refactor.md` (section 6.3), finding P-3 ("Observer absent, replaced by a reverse classmethod probe"). Today the main window calls a classmethod that finds the open settings dialog through the class slot, scans its panels with `isinstance(panel, ViewSettingsPanel)`, reads the panel's `font_size_dirty` flag and writes its spin control. After this task:

- `SingletonDialogMixin` (P2-1, `ui/dialog_base.py`) gets one public read-only accessor, `open_instance()`, for the dialog its slot holds.
- `DotExpressSettingsDialog` gets an **instance** method `sync_font_size(font_size)`. It owns the lookup of its own View panel.
- `ViewSettingsPanel` gets `sync_font_size(font_size) -> bool`. It owns the dirty-flag rule and its spin control.
- `gui._set_view_font_size` asks the class for the open dialog and calls the instance method on it. `sync_open_font_size` is deleted.

No event bus or `Signal` is added (decision D1). This refactor keeps behavior the same: the same font size reaches the same controls in the same cases, nothing new is shown or spoken, and no msgid changes (353, same set). The golden fixtures `client/tests/fixtures/translation_golden.json` (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`) and `client/tests/fixtures/dictionary_entries_trace.json` (sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`) do not change.

Corrected after planning: the plan `docs/superpowers/plans/2026-10-08-p2-4-font-size-sync.md` (section "Spec Corrections and Refinements") fixed two facts (AC6's plain `_instance` grep on `gui.py` matches `open_instance()`; part C's absence assertion would spell the removed name that AC6's first grep must not find) and refined the test plan (20 new tests, the subclass case, the two older tests on `patch.object`, how the stubs mask a missing `font_size_dirty`); those changes are folded in below.

## Current State (verified 2026-10-08 on `refactor/p2-4-font-size-sync`, HEAD `6dd65e3`, P0-*, P1-*, P2-1, P2-2 and P2-3 merged)

Indentation: `settings/dialogs.py`, `ui/dialog_base.py` and all touched test modules use 4 spaces. `gui.py` uses tabs.

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 1023 tests`, `FAILED (failures=1, skipped=9)`. The failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. Shuffle harness seeds 1 and 2 give the same single failure. Focused modules: `tests.test_settings_dialogs` 67 tests, `tests.test_dialog_base` 23, `tests.test_gui_document_flows` 145, `tests.test_view_settings` 5, all OK. Msgid scan (`cd /workspace/DotExpress && $PY $SP/p12/tools/msgid_scan.py client`) reports `source msgids: 353`. (`$PY` = `$SP/venv/bin/python`, `$SP` = the session scratchpad.)

The line numbers in `storage/refactor.md` (`gui.py:855`, `settings/dialogs.py:875-896`) predate P0-P2-3. These are the current ones.

### Who changes the font size outside the dialog

- `gui.py:215, 217` bind `wx.EVT_MOUSEWHEEL` on both editors to `on_editor_mousewheel` (`gui.py:868-873`). `ui/shortcuts.py:51` `get_font_size_step_from_wheel` returns +1/-1 for Ctrl+wheel and 0 otherwise. On 0 the event is skipped.
- `gui.py:552-558` `_set_view_font_size(font_size)`: normalizes `replace(self.view_settings, font_size=font_size)` (clamp to 8..48 via `VIEW_FONT_SIZE_RANGE`), applies it to the editors, `save_view_settings(...)`, and **then** calls `DotExpressSettingsDialog.sync_open_font_size(self.view_settings.font_size)`. It always runs all four steps, even when the clamped size did not change.
- That is the only caller. There is **no** keyboard shortcut for font size (no Ctrl+=/Ctrl+-, checked in `ui/shortcuts.py` and `gui.py`). The settings dialog's own Apply/OK goes through `apply_settings_from_dialog` (`gui.py:408-425`), which does not sync: the dialog is the source of that change and reloads its panels from the committed snapshot itself (`on_apply`, `settings/dialogs.py:698-705`).
- The Dual View window (`ui/dual_view.py`) does not use the view font size. So there is one publisher and one subscriber.

### The probe (`settings/dialogs.py:751-773`)

```python
@classmethod
def sync_open_font_size(cls, font_size: int) -> None:
    instance = cls._instance
    if instance is None:
        return
    normalized_view = normalize_view_settings(
        ViewSettings(font_size, instance.snapshot.view.scheme, instance.snapshot.view.braille_font)
    )
    view_panel = None
    for panel in instance.panel_instances.values():
        if isinstance(panel, ViewSettingsPanel):
            view_panel = panel
            break
    if view_panel is not None and getattr(view_panel, "font_size_dirty", False):
        return
    instance.snapshot = instance.snapshot.with_view(normalized_view)
    if view_panel is not None:
        view_panel.font_size_spin.SetValue(normalized_view.font_size)
        view_panel.font_size_dirty = False
```

The cases it handles:

1. **No dialog open** (slot `None`): nothing happens.
2. **Dialog open, View panel not built yet** (panels are built lazily by `_get_category_panel`, `settings/dialogs.py:214-220`): only the dialog snapshot's font size changes. Scheme and braille font come from the dialog's own snapshot. When the user later opens the View category, `ViewSettingsPanel.make_settings` (561-598) reads `owner.snapshot.view` and shows the synced size, and Apply without visiting the panel commits it (`_collect` starts from `self.snapshot`).
3. **View panel built, no pending edit**: snapshot updated, spin set to the size, `font_size_dirty` reset to `False` after `SetValue` (in case a platform emits `EVT_TEXT` from `SetValue`; the handler `_on_font_size_changed` 618-619 only sets the flag). The scheme and braille font choices are not touched, so drafts there survive.
4. **View panel built, user edited the spin** (`font_size_dirty` set by `EVT_SPINCTRL`/`EVT_TEXT`, 596-597): nothing happens, not even the snapshot. The flag is cleared by `load_snapshot` (600-606), which runs after every successful Apply.
5. **Dialog closed**: OK, Cancel, the close box (`EVT_CLOSE` -> `on_cancel`, 95-98) and Escape (the `wx.ID_CANCEL` button) all end in `SingletonDialogMixin._destroy`, which clears the slot. So case 1 applies.
6. **Dead window still in the slot**: not reachable through the UI (every close path goes through `_destroy`; destroying the main frame ends the app). The probe has no dead-window handling: it would raise from `font_size_spin.SetValue`.

The slot: `DotExpressSettingsDialog._instance` (648) is declared on the class itself. P2-1's mixin reads and writes it through `cls.__dict__` (`ui/dialog_base.py:90-142`), so a subclass never sees its parent's dialog. The probe reads `cls._instance` (normal attribute lookup). For `DotExpressSettingsDialog` both give the same object, because it declares its own slot.

What makes it a reverse probe: the dialog's knowledge (which panel holds the font size, the dirty rule, the spin) lives in a classmethod that reaches into an instance from outside, and the main window calls the dialog **class**, not a dialog.

### Tests touching this area

- `tests/test_settings_dialogs.py:391-398` `ViewSettingsPanelTest.test_view_panel_tracks_font_size_dirty_state`.
- `tests/test_settings_dialogs.py:493-525`: `test_sync_open_font_size_updates_snapshot_before_view_panel_exists` and `test_sync_open_font_size_keeps_dirty_view_panel_draft`. Both assign `DotExpressSettingsDialog._instance` by hand and call the classmethod.
- `tests/test_settings_dialogs.py:547-770` singleton characterization (P2-1) and, in `tests/test_dialog_base.py`, `MixinShapeTest` (104), `SingletonDialogMixinTest` (218-340) and `DialogBaseImportTest` (342).
- `tests/test_gui_document_flows.py:907-918` `test_open_settings_uses_singleton_dialog`. Nothing tests `_set_view_font_size` or `on_editor_mousewheel` in the frame. `tests/test_input_shortcuts.py:62` tests only the wheel step function.

## Design

### Decision summary

| # | Decision | Why |
| --- | --- | --- |
| D1 | No `Signal`/event bus. | One publisher (`_set_view_font_size`, reached only from Ctrl+wheel) and one subscriber (the settings dialog). Dual View does not use the font size, and Apply in the dialog needs no notification. A bus would add subscribe in `__init__`, unsubscribe in `_destroy`, and dead-window handling, which is more lifecycle than the slot that already exists. `storage/refactor.md` 4.3 and 7.10 say to add a bus only when a second subscriber appears. |
| D2 | The frame does **not** keep its own `_settings_dialog` reference; it reads the P2-1 slot through `open_instance()`. | The `_dual_view_frame` pattern that `refactor.md` P-3 mentions needs an `on_closed` callback (`gui.py:304-309`) to clear the frame's copy. The settings dialog closes itself (`on_ok`/`on_cancel` -> `_destroy`), so a frame copy would go stale unless `show_singleton` and the constructor grew a callback parameter. The slot is already the single source of truth and `_destroy` already clears it. |
| D3 | `open_instance()` reads `cls.__dict__.get("_instance")`, like the rest of the mixin. It does not raise, focus or probe for a dead window. | Same object as today's `cls._instance` for `DotExpressSettingsDialog` (it declares its own slot). No liveness probe, because the probe had none and every close path clears the slot (case 6 stays as it is). |
| D4 | The dialog finds its View panel with the same `isinstance` scan over `panel_instances`, now in a private helper `_view_panel()` on the dialog. | Same semantics as today, including subclasses of `ViewSettingsPanel` and test dialogs that store the panel under any index. An index lookup through `category_classes.index(ViewSettingsPanel)` would raise for a dialog that does not register the panel. A dialog scanning its own panels is ordinary ownership, not a probe. |
| D5 | The dirty rule and the spin move into `ViewSettingsPanel.sync_font_size(font_size) -> bool`. | Only the panel knows about `font_size_dirty` and `font_size_spin`. The dialog only learns "accepted or not". |
| D6 | The dialog normalizes first, then asks the panel, then replaces the snapshot. | Today the snapshot is replaced before `SetValue`. The new order sets the spin first. The difference cannot be observed: `normalize_view_settings` is pure, `with_view` cannot fail, and `SetValue` (and the `EVT_TEXT` it may emit) never reads the snapshot. The early return on a dirty panel still leaves the snapshot alone. |
| D7 | `sync_open_font_size` is deleted, with no alias. | One caller, in this repo. An allow-list guard in `tests/test_settings_dialogs.py` records the removal without spelling the removed name (see part C). |

### `ui/dialog_base.py` (4 spaces)

Added to `SingletonDialogMixin`, after `_show_new`:

```python
    @classmethod
    def open_instance(cls):
        """The open dialog of this class, or ``None``. Nothing is raised, focused or checked."""
        return cls.__dict__.get("_instance")
```

The module docstring and the "no `__init__`/`__new__`/`__slots__`/metaclass" shape stay as they are. Imports do not change.

### `settings/dialogs.py` (4 spaces)

`ViewSettingsPanel`, after `_on_font_size_changed`:

```python
    def sync_font_size(self, font_size: int) -> bool:
        """Show a font size changed in the main window, unless the user has edited it here.

        Returns ``False``, changing nothing, while that edit is pending (until Apply or OK).
        """
        if self.font_size_dirty:
            return False
        self.font_size_spin.SetValue(font_size)
        self.font_size_dirty = False
        return True
```

`font_size_dirty` is read directly (it is set in `make_settings`), no longer with `getattr(..., False)`. Every real panel and every existing test panel has the attribute.

`DotExpressSettingsDialog`, replacing `sync_open_font_size`:

```python
    def sync_font_size(self, font_size: int) -> None:
        """Take a font size changed in the main window (Ctrl+wheel).

        A View panel with an unsaved font size edit keeps it, and then the snapshot is left alone too.
        """
        view = normalize_view_settings(
            ViewSettings(font_size, self.snapshot.view.scheme, self.snapshot.view.braille_font)
        )
        view_panel = self._view_panel()
        if view_panel is not None and not view_panel.sync_font_size(view.font_size):
            return
        self.snapshot = self.snapshot.with_view(view)

    def _view_panel(self) -> ViewSettingsPanel | None:
        for panel in self.panel_instances.values():
            if isinstance(panel, ViewSettingsPanel):
                return panel
        return None
```

Imports do not change (`ViewSettings` and `normalize_view_settings` are already imported). No string changes.

### `gui.py` (tabs)

`_set_view_font_size` keeps its first three statements and their order. The last line becomes:

```python
		settings_dialog = DotExpressSettingsDialog.open_instance()
		if settings_dialog is not None:
			settings_dialog.sync_font_size(self.view_settings.font_size)
```

`gui.py` does not read `_instance` anywhere. The import line (`gui.py:91`) does not change.

## What Stays Identical

For every case 1-6 above: the editor font, the saved `config.json`, the dialog snapshot, the spin value, the dirty flag, the scheme and braille font drafts, what Apply and OK commit, and what a View panel built later shows. Also the singleton behavior of `show_singleton`/`_destroy`, the msgid set, and the fixtures. No visible or spoken change, so no screenshot is needed.

## Test Plan

### A. Characterization on current code (step 1)

These pass on today's code. The frame-level tests are never edited afterwards. The dialog-level tests reach the sync through one module helper in `tests/test_settings_dialogs.py`, `sync_open_dialog_font_size(dialog_class, font_size)`. In step 1 it calls `dialog_class.sync_open_font_size(font_size)`, and in step 3 it becomes `dialog = dialog_class.open_instance()` then `dialog.sync_font_size(font_size)` when not `None`. That is the only edit to part A. The open dialog goes into the slot with `patch.object(dialog_class, "_instance", dialog)`, never by plain assignment, so nothing leaks between modules.

Part A is 14 tests (6 frame-level, 8 dialog-level). Because it passes by construction on today's code, a throwaway mutant runner (not committed) applies 15 one-edit breakages of today's code to a copy of `client/` (no sync, sync before save, return when unchanged, wheel not skipped, probe raises the dialog, pending edit ignored, dirty flag kept after `SetValue`, size not normalized, braille font overwritten, snapshot written despite the edit, exact panel type, fixed panel index, spin not set, snapshot not written, `_destroy` keeps the slot) and shows each one makes part A fail. After step 3 a second set of 13 mutants of the new code is caught by the three touched modules.

1. `tests/test_gui_document_flows.py`, new class `ViewFontSizeSyncCharacterizationTest` (gui stub scope; it uses `gui.DotExpressSettingsDialog` and `gui.TextProcessingDialog`, the real classes loaded under that scope). The frame is `object.__new__(gui.BrailleFrame)` with `view_settings`, a `Mock` `_apply_editor_view_settings` and a patched `gui.save_view_settings`. The open dialog is `object.__new__(gui.DotExpressSettingsDialog)` with `snapshot`, `panel_instances = {}`, a `Mock` `Destroy` and recording `Iconize`/`Raise`/`SetFocus`/`Show`. Events are a `SimpleNamespace` with `GetWheelRotation`, `ControlDown`, `Skip`.
   - Ctrl+wheel up with frame view `ViewSettings(12, "dark", "default")` and dialog view `ViewSettings(12, "light", "simbraille")`: the frame becomes `(13, "dark", "default")`, the editors and `save_view_settings` get it, and the dialog becomes `(13, "light", "simbraille")` (only the size crosses over). A `save_view_settings` side effect records the dialog's size at save time: still 12, so the dialog is synced after saving. The dialog is not iconized, raised, focused or shown (the editor keeps the focus), and the event is not skipped.
   - Ctrl+wheel down from 8 and up from 48: the size stays clamped, save still runs, and the dialog is set to the clamped size (from a dialog snapshot of 12). Marked `# KNOWN QUIRK (P2-4 spec, 1)`.
   - Wheel without Ctrl (up and down), and Ctrl with rotation 0: `Skip` is called, and nothing is applied, saved or synced.
   - No dialog open: the editors and save run and nothing raises.
   - Wheel, then `dialog.on_cancel()`, then wheel again: the first step syncs, Cancel clears the slot and destroys the dialog once, the second step changes and saves only the editors, and the closed dialog keeps the first value.
   - An open Text Processing dialog (its own slot) is neither touched nor mistaken for the settings dialog.
2. `tests/test_settings_dialogs.py`, new class `FontSizeSyncCharacterizationTest`. The dialog is `make_dialog_without_wx_constructor()`. The View panel is the **real** `ViewSettingsPanel` built with that dialog as owner, through a new `owner=` keyword on `build_panel` (default: the current `SimpleNamespace`; a given owner makes the snapshot keyword arguments unused), with the recording `wx.Choice`/`wx.SpinCtrl`. It is stored in `dialog.panel_instances[2]`.
   - No dialog in the slot: no error.
   - No View panel yet: the snapshot size becomes 20, scheme and braille font stay. A View panel built afterwards with that dialog as owner shows 20 in its spin.
   - Clamping, as its own test: 99, 49, 48, 8, 7 and 3 become 48, 48, 48, 8, 8 and 8, both without a View panel (snapshot) and with a built panel (spin and snapshot).
   - Clean built panel with the scheme choice switched to dark (a draft): spin 20, `font_size_dirty` false, snapshot 20, the scheme selection still dark and the snapshot scheme unchanged; `on_save` gives `(20, "dark", "simbraille")`.
   - Pending edit (spin set to 30 and `panel._on_font_size_changed(None)`, the handler bound to `EVT_SPINCTRL`/`EVT_TEXT`): spin stays 30, snapshot stays 12 (marked `# KNOWN QUIRK (P2-4 spec, 2)`). Then `panel.load_snapshot(dialog.snapshot)` (what Apply does): the next sync applies again.
   - A subclass of `ViewSettingsPanel` stored under another index (0): still found (D4). `build_panel` builds panels by name from the module, so the subclass panel is made with `object.__new__` (with `font_size_dirty = False` and a recording spin), next to a `Mock` panel under index 1 whose `mock_calls` must stay empty (the sync touches only the View panel).
   - A spin whose `SetValue` reports the change like `EVT_TEXT` (it calls `_on_font_size_changed`): two syncs, 13 then 14, both reach the spin and the flag ends clear, so the sync never counts its own write as a user edit.
   - Apply without ever visiting the View panel after a sync commits the synced size (case 2).
3. The two existing tests at 493-525 are kept and moved onto the helper in step 3, renamed `test_sync_font_size_updates_snapshot_before_view_panel_exists` and `test_sync_font_size_keeps_dirty_view_panel_draft`. Their `try`/`finally` slot assignment is replaced by `patch.object` (same effect, same rule as the new tests); their assertions are unchanged. `test_view_panel_tracks_font_size_dirty_state` stays.

### B. New API (step 2, additive)

`tests/test_dialog_base.py` `SingletonDialogMixinTest` gains:
- `open_instance()` returns `None` for an empty slot and the dialog in the slot otherwise, without calling `Iconize`, `Raise`, `SetFocus` or `Show` (the dialog is a `Mock`; assert `mock_calls == []`).
- A subclass without its own slot gets `None` while the parent has a dialog (same `cls.__dict__` rule as `_raise_existing`).
- After `_destroy`, `open_instance()` returns `None`.

`tests/test_settings_dialogs.py` `ViewSettingsPanelTest` gains two `ViewSettingsPanel.sync_font_size` tests (clean: returns `True`, spin 20, flag clear; dirty: returns `False`, the spin stays 30, flag still set). They run against the method added in step 2. The guard `MixinShapeTest` still passes unchanged. Part B is 5 tests (3 + 2).

### C. Switch (step 3)

Part A passes with only the helper changed. One guard is added, written as an allow-list so that it never spells the removed name (an absence assertion naming it would make AC6's first grep print a line): `DotExpressSettingsDialogFlowTest.test_font_size_sync_is_one_instance_method` asserts that the only name in `vars(DotExpressSettingsDialog)` containing `font_size` is `sync_font_size`, and that it is a plain function (an instance method, not a `classmethod`). It is red on the old code (`['sync_open_font_size'] != ['sync_font_size']`). The existing singleton characterization (P2-1) passes unchanged.

## Migration Steps (each step one green commit)

1. `test: characterize font size sync` (part A on the current code, plus the `owner=` keyword on `build_panel`).
2. `refactor: add open dialog and panel font size hooks` (`SingletonDialogMixin.open_instance`, `ViewSettingsPanel.sync_font_size`, part B; nothing calls them yet except tests).
3. `refactor: sync font size through the open settings dialog` (`DotExpressSettingsDialog.sync_font_size` and `_view_panel`, `gui._set_view_font_size`, delete `sync_open_font_size`, part C).

## Acceptance Criteria

1. Roadmap verification on Linux: `cd client && $PY -m unittest tests.test_settings_dialogs -v` passes (78 tests, all `ok`). Also green: `tests.test_dialog_base tests.test_gui_document_flows tests.test_view_settings tests.test_input_shortcuts tests.test_wx_stub tests.test_removed_dead_code tests.test_i18n`.
2. Full suite (`$PY -m unittest discover -s tests`): `Ran 1043` (1023 + 20: 14 in part A, 5 in part B, 1 in part C; per module `test_settings_dialogs` 67 -> 78, `test_gui_document_flows` 145 -> 151, `test_dialog_base` 23 -> 26), `failures=1` (the P2-5 case only), `errors=0`, `skipped=9`.
3. Shuffle harness: `cd client && for s in $(seq 0 19); do $PY $SP/shuffle_harness.py $s; done` gives, for all 20 seeds, exactly one failure, the P2-5 case. `test_settings_dialogs`, `test_dialog_base` and `test_gui_document_flows` pass alone and in both orders of each pair.
4. Msgid scan from the repo root reports `source msgids: 353`, the same set as `main`. `git diff main --stat -- client/locales` is empty.
5. Both fixture sha256 values above are unchanged, and `git diff main -- client/tests/fixtures` is empty.
6. `grep -rn "sync_open_font_size" client --include=*.py --exclude-dir=.venv` prints nothing. `gui.py` never touches the slot attribute: `grep -nw "_instance" client/gui.py` (whole word) prints nothing, and the plain `grep -n "_instance" client/gui.py` prints only the `DotExpressSettingsDialog.open_instance()` line (`open_instance` contains the substring). `grep -n "isinstance(panel, ViewSettingsPanel)" client/settings/dialogs.py` prints only the line in `_view_panel`. `grep -n "font_size_dirty\|font_size_spin" client/settings/dialogs.py` prints only lines inside `ViewSettingsPanel`.
7. `git diff main --stat` touches only `client/gui.py`, `client/settings/dialogs.py`, `client/ui/dialog_base.py`, the three test modules and the docs.

## Risks

- **Slot leaks between test modules.** Every new test sets the slot with `patch.object`. Covered by the shuffles.
- **Stub-scope class identity.** `test_gui_document_flows` must use `gui.DotExpressSettingsDialog` (the class loaded under the gui scope, with its own slot), never import `settings.dialogs` outside its scope. `test_settings_dialogs` uses the class from its own scope.
- **Order of `SetValue` and the snapshot write (D6).** Not observable with stubs or, by reading the handlers, with real wx.
- **Direct `font_size_dirty` read.** A hand-built panel without the attribute would now raise `AttributeError` instead of counting as clean. Every real panel sets it in `make_settings`, and the tests that build panels with `object.__new__` set it. This holds for real wx only: under `tests/wx_stub.py` every widget masks a missing attribute with a no-op function, which is truthy, so the old `getattr(..., False)` and the new direct read both treat such a panel as dirty. No test relies on either. The same masking makes the red steps of steps 2 and 3 show up as assertion failures (`None is not True`, `12 != 20`) rather than `AttributeError` on instances.
- **Real wx.** Everything here is checked with stubs only (see Windows verification debt).

## Known quirks kept (pinned, not fixed)

1. A Ctrl+wheel step that clamps (already at 8 or 48) still saves and still syncs the dialog. Pinned by part A item 1 (`test_a_clamped_step_still_saves_and_syncs_the_clamped_size`, marked `# KNOWN QUIRK (P2-4 spec, 1)`).
2. A pending font size edit in the View panel blocks the sync for the snapshot too, so Apply commits the user's edit and the wheel change is lost from the dialog's point of view (the editors keep the wheel size until Apply). Pinned by part A item 2 (`test_a_pending_edit_blocks_the_sync_until_the_snapshot_is_reloaded`, marked `# KNOWN QUIRK (P2-4 spec, 2)`).
3. No dead-window handling (case 6). Not reachable today. Not pinned.

## Windows verification debt

Real wxPython on Windows with NVDA (not runnable on this Linux box): open Settings > View, Ctrl+wheel in an editor, the Font Size spin follows. Type a size in the spin, Ctrl+wheel, the spin keeps the typed value. Apply, then Ctrl+wheel, the spin follows again. Open Settings on the Translation category, Ctrl+wheel, then switch to View: it shows the new size. Close the dialog (OK, Cancel, close box, Escape), then Ctrl+wheel: no error. Also check that Ctrl+wheel leaves the focus in the editor while the dialog is open, and whether the real `wx.SpinCtrl.SetValue` emits `EVT_TEXT` (the code handles both).

## Out of Scope

- An event bus or `Signal` (D1), and Dual View reacting to view settings.
- Font size keyboard shortcuts.
- Dead-window handling in `open_instance` (case 6).
- `TextProcessingDialog` (no font size), the other singleton internals (P2-1), and the option source (P2-3).
- Updating older specs and plans that mention `sync_open_font_size` (they are historical records).
