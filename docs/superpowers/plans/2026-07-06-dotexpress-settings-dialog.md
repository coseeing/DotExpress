# DotExpress Multi-Category Settings Dialog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the separate translation dialogs and main-window View controls with one accessible, modeless, multi-category `DotExpress Settings` dialog whose staged changes commit only on Apply or OK.

**Architecture:** Add pure immutable settings values for view state and whole-dialog snapshots, then build reusable wxPython `SettingsDialog`, `SettingsPanel`, and `MultiCategorySettingsDialog` classes in a focused root-level dialog module. `BrailleFrame` remains the owner of live application state and persistence through one commit method, while `DotExpressSettingsDialog` owns panel staging, category navigation, accessibility metadata, and the singleton lifecycle.

**Tech Stack:** Python 3, wxPython 4.2.5, `wx.lib.scrolledpanel`, `dataclasses`, `unittest`, GNU gettext

---

## File Structure

- Create `client/view_settings.py`: immutable view settings, normalization, loading, and persistence.
- Create `client/settings_state.py`: immutable aggregate snapshot copied between the main window and settings dialog.
- Create `client/settings_dialogs.py`: reusable settings framework, accessibility helper, singleton DotExpress dialog, and three concrete panels.
- Create `client/tests/test_view_settings.py`: pure view-settings normalization and persistence tests.
- Create `client/tests/test_settings_state.py`: snapshot-copy isolation tests.
- Create `client/tests/test_settings_dialogs.py`: panel collection, validation, title switching, Apply/OK/Cancel, accessibility, and singleton tests with lightweight wx controls/mocks.
- Modify `client/gui.py:267-288, 290-386, 399-410, 532-619, 829-834, 1218-1229, 1279-1323`: explicit view state, dialog integration, central commit path, quick font-size synchronization, and removal of old handlers.
- Modify `client/dialog.py:88-94, 708-804, 996-1085`: remove the migrated `TableOption`, `TranslationSettingsDialog`, and `TranslationTableDialog`.
- Modify `client/ui/translation_menu.py:4-12`: expose one `Settings...` entry and remove the tables entry.
- Modify `client/ui/section_navigation.py:1-11`: remove the deleted View section.
- Modify `client/tests/test_translation_menu.py:6-21`, `client/tests/test_section_navigation.py`, and `client/tests/test_gui_document_flows.py`: update integration expectations and stubs.
- Modify `client/locales/dotexpress.pot`: regenerate extracted source strings.
- Modify `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`: add/update Traditional Chinese translations.
- Regenerate `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`.

### Task 1: Introduce Explicit View Settings State

**Files:**
- Create: `client/view_settings.py`
- Create: `client/tests/test_view_settings.py`
- Modify: `client/config.py:157-184`

- [ ] **Step 1: Write failing normalization, load, and save tests**

```python
# client/tests/test_view_settings.py
import tempfile
import unittest
from pathlib import Path

import config
from view_settings import (
    ViewSettings,
    load_view_settings,
    normalize_view_settings,
    save_view_settings,
)


class ViewSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_path = config.CONFIG_PATH
        self.temp_dir = tempfile.TemporaryDirectory()
        config.CONFIG_PATH = str(Path(self.temp_dir.name) / "config.json")

    def tearDown(self) -> None:
        config.CONFIG_PATH = self.original_path
        self.temp_dir.cleanup()

    def test_normalize_clamps_font_and_replaces_unknown_choices(self) -> None:
        self.assertEqual(
            normalize_view_settings(ViewSettings(999, "unknown", "unknown")),
            ViewSettings(48, "light", "simbraille"),
        )

    def test_save_and_load_round_trip_as_one_value(self) -> None:
        expected = ViewSettings(18, "dark", "default")
        save_view_settings(expected)
        self.assertEqual(load_view_settings(), expected)
```

- [ ] **Step 2: Run the focused test and verify the missing module failure**

Run: `cd client && python3 -m unittest tests.test_view_settings -v`

Expected: `ERROR` with `ModuleNotFoundError: No module named 'view_settings'`.

- [ ] **Step 3: Implement the immutable value and normalization boundary**

```python
# client/view_settings.py
from dataclasses import dataclass

from config import (
    DEFAULT_BRAILLE_FONT,
    DEFAULT_VIEW_FONT_SIZE,
    DEFAULT_VIEW_SCHEME,
    get_braille_font,
    get_view_font_size,
    get_view_scheme,
    set_view_settings,
)

VIEW_FONT_SIZE_MIN = 8
VIEW_FONT_SIZE_MAX = 48
VIEW_SCHEME_KEYS = ("light", "dark")
BRAILLE_FONT_KEYS = ("default", "simbraille")


@dataclass(frozen=True)
class ViewSettings:
    font_size: int
    scheme: str
    braille_font: str


def normalize_view_settings(settings: ViewSettings) -> ViewSettings:
    return ViewSettings(
        font_size=max(VIEW_FONT_SIZE_MIN, min(VIEW_FONT_SIZE_MAX, settings.font_size)),
        scheme=settings.scheme if settings.scheme in VIEW_SCHEME_KEYS else DEFAULT_VIEW_SCHEME,
        braille_font=(
            settings.braille_font
            if settings.braille_font in BRAILLE_FONT_KEYS
            else DEFAULT_BRAILLE_FONT
        ),
    )


def load_view_settings() -> ViewSettings:
    return normalize_view_settings(
        ViewSettings(
            get_view_font_size(DEFAULT_VIEW_FONT_SIZE),
            get_view_scheme(DEFAULT_VIEW_SCHEME),
            get_braille_font(DEFAULT_BRAILLE_FONT),
        )
    )


def save_view_settings(settings: ViewSettings) -> None:
    normalized = normalize_view_settings(settings)
    set_view_settings(
        normalized.font_size,
        normalized.scheme,
        normalized.braille_font,
    )
```

Add one config write boundary so a view commit does not reload and rewrite the JSON file three times:

```python
# client/config.py
def set_view_settings(font_size: int, scheme: str, braille_font: str) -> None:
    data = _load_from_file()
    section_data = _get_section(data, VIEW_SECTION).copy()
    section_data.update(
        {
            FONT_SIZE_KEY: font_size,
            SCHEME_KEY: scheme,
            BRAILLE_FONT_KEY: braille_font,
        }
    )
    data[VIEW_SECTION] = section_data
    _save_to_file(data)
```

- [ ] **Step 4: Run view and config tests**

Run: `cd client && python3 -m unittest tests.test_view_settings tests.test_config -v`

Expected: all tests pass.

- [ ] **Step 5: Commit the explicit view state**

```bash
git add client/view_settings.py client/config.py client/tests/test_view_settings.py
git commit -m "refactor: add explicit view settings state"
```

### Task 2: Add an Isolated Dialog Snapshot

**Files:**
- Create: `client/settings_state.py`
- Create: `client/tests/test_settings_state.py`

- [ ] **Step 1: Write the failing copy-isolation test**

```python
# client/tests/test_settings_state.py
import unittest

from settings_state import DotExpressSettingsSnapshot
from translation.settings import TranslationSettings
from view_settings import ViewSettings


class SettingsSnapshotTest(unittest.TestCase):
    def test_create_copies_translation_table_mapping(self) -> None:
        source_tables = {"default": "zh-tw.ctb", "math": "UEB"}
        snapshot = DotExpressSettingsSnapshot.create(
            TranslationSettings("unicode", 40, "default"),
            source_tables,
            ViewSettings(12, "light", "simbraille"),
        )

        source_tables["default"] = "en-ueb-g1.ctb"

        self.assertEqual(snapshot.translation_tables["default"], "zh-tw.ctb")
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `cd client && python3 -m unittest tests.test_settings_state -v`

Expected: `ERROR` with `ModuleNotFoundError: No module named 'settings_state'`.

- [ ] **Step 3: Implement snapshot creation and replacement helpers**

```python
# client/settings_state.py
from dataclasses import dataclass, replace

from translation.settings import TranslationSettings
from view_settings import ViewSettings


@dataclass(frozen=True)
class DotExpressSettingsSnapshot:
    translation: TranslationSettings
    translation_tables: dict[str, str]
    view: ViewSettings

    @classmethod
    def create(
        cls,
        translation: TranslationSettings,
        translation_tables: dict[str, str],
        view: ViewSettings,
    ) -> "DotExpressSettingsSnapshot":
        return cls(translation, dict(translation_tables), view)

    def with_translation(self, value: TranslationSettings) -> "DotExpressSettingsSnapshot":
        return replace(self, translation=value)

    def with_translation_tables(
        self,
        value: dict[str, str],
    ) -> "DotExpressSettingsSnapshot":
        return replace(self, translation_tables=dict(value))

    def with_view(self, value: ViewSettings) -> "DotExpressSettingsSnapshot":
        return replace(self, view=value)

    def copied(self) -> "DotExpressSettingsSnapshot":
        return replace(self, translation_tables=dict(self.translation_tables))
```

- [ ] **Step 4: Run snapshot tests**

Run: `cd client && python3 -m unittest tests.test_settings_state -v`

Expected: all tests pass.

- [ ] **Step 5: Commit snapshot isolation**

```bash
git add client/settings_state.py client/tests/test_settings_state.py
git commit -m "refactor: add staged settings snapshot"
```

### Task 3: Build the Reusable Settings Framework

**Files:**
- Create: `client/settings_dialogs.py`
- Create: `client/tests/test_settings_dialogs.py`

- [ ] **Step 1: Add failing framework behavior tests**

Use the existing lightweight wx stubbing pattern from
`client/tests/test_gui_document_flows.py`, adding stubs for `wx.Panel`,
`wx.GridBagSizer`, `wx.ListCtrl`, `wx.lib.scrolledpanel.ScrolledPanel`,
`wx.ID_CANCEL`, `wx.ID_APPLY`, `wx.APPLY`, `wx.RESIZE_BORDER`,
`wx.ROLE_SYSTEM_PROPERTYPAGE`, and the list/category events. Then add:

```python
class SettingsPanelAccessibleTest(unittest.TestCase):
    def test_exposes_property_page_role_and_description(self) -> None:
        panel = Mock(panel_description="View settings")
        accessible = SettingsPanelAccessible(panel)
        self.assertEqual(
            accessible.GetRole(0),
            (wx.ACC_OK, wx.ROLE_SYSTEM_PROPERTYPAGE),
        )
        self.assertEqual(
            accessible.GetDescription(0),
            (wx.ACC_OK, "View settings"),
        )


class MultiCategorySettingsDialogTest(unittest.TestCase):
    def test_rejects_initial_category_outside_registered_categories(self) -> None:
        class RegisteredPanel(SettingsPanel):
            pass

        class UnregisteredPanel(SettingsPanel):
            pass

        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog.category_classes = [RegisteredPanel]
        with self.assertRaises(ValueError):
            dialog._get_initial_category_index(UnregisteredPanel)

    def test_category_change_deactivates_old_panel_and_activates_new_panel(self) -> None:
        old_panel = Mock()
        new_panel = Mock()
        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog.current_panel = old_panel
        dialog._get_category_panel = Mock(return_value=new_panel)
        dialog._layout_container = Mock()
        dialog._after_category_change = Mock()

        dialog._change_category(1)

        old_panel.on_panel_deactivated.assert_called_once_with()
        new_panel.on_panel_activated.assert_called_once_with()
        dialog._after_category_change.assert_called_once_with(new_panel)

    def test_category_cycle_wraps_in_both_directions(self) -> None:
        dialog = object.__new__(MultiCategorySettingsDialog)
        dialog.category_classes = [Mock, Mock, Mock]
        self.assertEqual(dialog._cycled_category_index(2, 1), 0)
        self.assertEqual(dialog._cycled_category_index(0, -1), 2)
```

- [ ] **Step 2: Run the framework tests and verify missing symbols**

Run: `cd client && python3 -m unittest tests.test_settings_dialogs -v`

Expected: `ERROR` because `settings_dialogs.py` or its classes do not exist.

- [ ] **Step 3: Implement base dialog, panel, accessibility, and category switching**

Implement these exact interfaces in `client/settings_dialogs.py`:

```python
class SettingsPanelAccessible(wx.Accessible):
    def GetRole(self, child_id):
        return (wx.ACC_OK, wx.ROLE_SYSTEM_PROPERTYPAGE)

    def GetDescription(self, child_id):
        return (wx.ACC_OK, self.Window.panel_description)


class SettingsPanel(wx.Panel):
    title = ""
    panel_description = ""

    def __init__(self, parent, owner):
        super().__init__(parent)
        self.owner = owner
        self.make_settings()
        self.SetName(self.title.replace("&", ""))
        self.SetAccessible(SettingsPanelAccessible(self))

    def make_settings(self) -> None:
        raise NotImplementedError

    def on_panel_activated(self) -> None:
        self.Show()

    def on_panel_deactivated(self) -> None:
        self.Hide()

    def is_valid(self) -> bool:
        return True

    def on_save(
        self,
        snapshot: DotExpressSettingsSnapshot,
    ) -> DotExpressSettingsSnapshot:
        raise NotImplementedError

    def load_snapshot(self, snapshot: DotExpressSettingsSnapshot) -> None:
        raise NotImplementedError

    def on_discard(self) -> None:
        pass


class SettingsDialog(wx.Dialog):
    INITIAL_SIZE = (720, 440)
    MIN_SIZE = (520, 300)

    def __init__(self, parent, *, title: str):
        super().__init__(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.Bind(wx.EVT_CLOSE, self._on_window_close)

    def _on_window_close(self, event) -> None:
        self.on_cancel()


class MultiCategorySettingsDialog(SettingsDialog):
    category_classes: list[type[SettingsPanel]] = []

    def __init__(self, parent, *, title, initial_category=None):
        self.initial_category = initial_category
        self.panel_instances: dict[int, SettingsPanel] = {}
        self.current_panel: SettingsPanel | None = None
        super().__init__(parent, title=title)
        self._build_layout()
        self.SetMinSize(self.MIN_SIZE)
        self.SetSize(self.INITIAL_SIZE)
        self.CentreOnParent()

    def _get_initial_category_index(self, initial_category) -> int:
        if initial_category is None:
            return 0
        if initial_category not in self.category_classes:
            raise ValueError("initial_category is not registered")
        return self.category_classes.index(initial_category)
```

In `_build_layout`, use:

- a `wx.GridBagSizer`
- category list initial size `(150, 10)`
- `wx.lib.scrolledpanel.ScrolledPanel` for the content container
- growable row 1
- growable column 0 proportion 1
- growable column 1 proportion 3
- bottom `OK`, `Cancel`, and `Apply` buttons
- lazy panel creation in `_get_category_panel`
- `SetupScrolling(scroll_x=False, scroll_y=True)` after each category change

Bind category focus/selection to `_change_category`; call
`on_panel_deactivated`, `on_panel_activated`, layout/scroll refresh, and
`_after_category_change` in that order. The base `_after_category_change` is a
no-op. Bind `wx.EVT_CHAR_HOOK` so `Ctrl+Tab` and `Ctrl+Shift+Tab` call
`_cycled_category_index(current_index, step)`, select/focus the resulting list
item, wrap at both ends, and otherwise call `event.Skip()`.

- [ ] **Step 4: Run the framework tests**

Run: `cd client && python3 -m unittest tests.test_settings_dialogs -v`

Expected: all framework tests pass.

- [ ] **Step 5: Commit the reusable framework**

```bash
git add client/settings_dialogs.py client/tests/test_settings_dialogs.py
git commit -m "feat: add multi-category settings framework"
```

### Task 4: Implement the Three Settings Panels and Staged Commit Flow

**Files:**
- Modify: `client/settings_dialogs.py`
- Modify: `client/tests/test_settings_dialogs.py`
- Modify: `client/dialog.py:88-94, 708-804, 996-1085`

- [ ] **Step 1: Add failing panel collection and validation tests**

Construct panels with `object.__new__` and fake controls so tests do not require a
display server:

```python
def test_translation_panel_collects_controls_without_mutating_baseline(self):
    baseline = make_snapshot()
    panel = object.__new__(TranslationSettingsPanel)
    panel.output_choice = FakeChoice(1)
    panel.width_spin = FakeSpin(52)
    panel.dictionary_choice = FakeChoice(1)
    panel.dictionary_names = ["default", "math"]

    result = panel.on_save(baseline)

    self.assertEqual(result.translation, TranslationSettings("ascii", 52, "math"))
    self.assertEqual(baseline.translation, TranslationSettings("unicode", 40, "default"))

def test_tables_panel_requires_default_and_math(self):
    panel = object.__new__(TranslationTablesPanel)
    panel._selected_file_name = Mock(side_effect=lambda key: "" if key == "default" else "UEB")
    self.assertFalse(panel.is_valid())

def test_view_panel_tracks_font_size_dirty_state(self):
    panel = object.__new__(ViewSettingsPanel)
    panel.font_size_dirty = False
    panel._on_font_size_changed(None)
    self.assertTrue(panel.font_size_dirty)
```

Add dialog flow tests:

```python
def test_apply_validates_all_panels_before_commit(self):
    dialog = make_dialog_without_wx_constructor()
    invalid = Mock(is_valid=Mock(return_value=False))
    valid = Mock(is_valid=Mock(return_value=True))
    dialog.panel_instances = {0: valid, 1: invalid}

    dialog.on_apply()

    dialog.commit.assert_not_called()
    valid.on_save.assert_not_called()

def test_successful_apply_reloads_normalized_baseline(self):
    dialog = make_dialog_without_wx_constructor()
    committed = make_snapshot(font_size=18)
    dialog.commit = Mock(return_value=committed)
    panel = Mock(is_valid=Mock(return_value=True))
    panel.on_save.return_value = committed
    dialog.panel_instances = {0: panel}

    dialog.on_apply()

    self.assertEqual(dialog.snapshot, committed)
    panel.load_snapshot.assert_called_once_with(committed)
```

- [ ] **Step 2: Run tests and verify panel failures**

Run: `cd client && python3 -m unittest tests.test_settings_dialogs -v`

Expected: failures for missing concrete panel and dialog-flow behavior.

- [ ] **Step 3: Move existing controls into concrete panels**

Implement:

```python
class TranslationSettingsPanel(SettingsPanel):
    title = _("Translation")
    panel_description = _(
        "Translation output mode, width, and dictionary options"
    )

    def on_save(self, snapshot):
        value = TranslationSettings(
            output_mode=self._selected_output_mode(),
            width=self.width_spin.GetValue(),
            selected_dictionary=self._selected_dictionary(),
        )
        return snapshot.with_translation(value)


class TranslationTablesPanel(SettingsPanel):
    title = _("Translation Tables")
    panel_description = _(
        "Translation table mappings for different languages"
    )

    def is_valid(self) -> bool:
        return bool(
            self._selected_file_name("default")
            and self._selected_file_name("math")
        )

    def on_save(self, snapshot):
        values = {
            key: self._selected_file_name(key)
            for key, _label, _language in self.CHOICE_SPECS
        }
        return snapshot.with_translation_tables(values)


class ViewSettingsPanel(SettingsPanel):
    title = _("View")
    panel_description = _(
        "Font, font size, and color scheme for the main window input and output areas"
    )

    def on_save(self, snapshot):
        value = normalize_view_settings(
            ViewSettings(
                self.font_size_spin.GetValue(),
                self._selected_scheme(),
                self._selected_braille_font(),
            )
        )
        return snapshot.with_view(value)
```

Reuse the old output choices, conversion-width bounds, dictionary behavior, table
filtering, and `listTables()` loading. Preserve empty `None selected` entries for
`en`, `zh`, and `ja`; require non-empty `default` and `math`.

- [ ] **Step 4: Implement DotExpress dialog title, validation, Apply, OK, and Cancel**

Use this contract:

```python
CommitSettings = Callable[
    [DotExpressSettingsSnapshot],
    DotExpressSettingsSnapshot,
]


class DotExpressSettingsDialog(MultiCategorySettingsDialog):
    base_title = _("DotExpress Settings")
    category_classes = [
        TranslationSettingsPanel,
        TranslationTablesPanel,
        ViewSettingsPanel,
    ]
    _instance: "DotExpressSettingsDialog | None" = None

    def _after_category_change(self, panel: SettingsPanel) -> None:
        self.SetTitle(f"{self.base_title}: {panel.title}")

    def _collect(self) -> DotExpressSettingsSnapshot | None:
        panels = list(self.panel_instances.values())
        for panel in panels:
            if not panel.is_valid():
                self.select_category(type(panel))
                panel.SetFocus()
                return None
        candidate = self.snapshot.copied()
        for panel in panels:
            candidate = panel.on_save(candidate)
        return candidate

    def on_apply(self) -> bool:
        candidate = self._collect()
        if candidate is None:
            return False
        self.snapshot = self.commit(candidate).copied()
        for panel in self.panel_instances.values():
            panel.load_snapshot(self.snapshot)
        return True

    def on_ok(self) -> None:
        if self.on_apply():
            self._destroy()

    def on_cancel(self) -> None:
        for panel in self.panel_instances.values():
            panel.on_discard()
        self._destroy()
```

`_destroy` clears `_instance` only when it points to `self`, then calls
`Destroy()`. `show_singleton` validates `initial_category`, restores an iconized
instance, optionally selects the requested category, raises/focuses it, or creates
and `Show()`s one new instance.

- [ ] **Step 5: Remove the replaced old dialogs**

Delete `TableOption`, `TranslationSettingsDialog`, and
`TranslationTableDialog` from `client/dialog.py`. Remove imports used only by
those classes (`listTables`, `List`, and conversion-width/settings imports when
no other code needs them).

- [ ] **Step 6: Run dialog and existing dialog regression tests**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_settings_dialogs \
  tests.test_dialog_display \
  tests.test_dialog_validation \
  -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit concrete settings panels**

```bash
git add client/settings_dialogs.py client/dialog.py client/tests/test_settings_dialogs.py
git commit -m "feat: add DotExpress settings panels"
```

### Task 5: Integrate the Dialog with `BrailleFrame`

**Files:**
- Modify: `client/gui.py:117-125, 267-288, 290-386, 558-619, 829-834, 1218-1229, 1279-1323`
- Modify: `client/tests/test_gui_document_flows.py`

- [ ] **Step 1: Add failing tests for central commit and singleton opening**

Extend the test wx/dialog stubs to expose `DotExpressSettingsDialog`. Add:

```python
def test_apply_settings_from_dialog_updates_all_live_state(self):
    frame = object.__new__(gui.BrailleFrame)
    frame._dictionary_names = ["default", "math"]
    frame._apply_editor_view_settings = Mock()
    snapshot = make_snapshot(
        translation=TranslationSettings("ascii", 52, "math"),
        tables={"default": "en-ueb-g1.ctb", "math": "Nemeth"},
        view=ViewSettings(18, "dark", "default"),
    )

    with patch.object(gui, "save_translation_settings"), \
         patch.object(gui, "set_translation_tables"), \
         patch.object(gui, "save_view_settings"):
        result = frame.apply_settings_from_dialog(snapshot)

    self.assertEqual(frame.translation_settings, snapshot.translation)
    self.assertEqual(frame.view_settings, snapshot.view)
    self.assertEqual(gui.language_map_translate_table, snapshot.translation_tables)
    frame._apply_editor_view_settings.assert_called_once_with(snapshot.view)
    self.assertEqual(result, snapshot)

def test_open_settings_uses_singleton_dialog(self):
    frame = object.__new__(gui.BrailleFrame)
    frame.get_settings_snapshot = Mock(return_value=make_snapshot())
    frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])

    with patch.object(gui.DotExpressSettingsDialog, "show_singleton") as show:
        frame.on_open_settings(None)

    show.assert_called_once()
    self.assertIs(show.call_args.kwargs["initial_category"], TranslationSettingsPanel)
```

- [ ] **Step 2: Run the GUI flow tests and verify failures**

Run: `cd client && python3 -m unittest tests.test_gui_document_flows -v`

Expected: failures for missing explicit `view_settings`, commit method, and new
dialog opener.

- [ ] **Step 3: Replace control-backed view state with `ViewSettings`**

In `_initialize_state`, assign:

```python
self.view_settings = load_view_settings()
return self.view_settings
```

Change `_create_main_layout` and `_create_editor_area` so no View group or controls
are created. `_apply_initial_settings` accepts `ViewSettings` and calls:

```python
self._apply_editor_view_settings(self.view_settings)
```

Change rendering to use explicit state:

```python
def _apply_editor_view_settings(self, settings: ViewSettings) -> None:
    settings = normalize_view_settings(settings)
    input_font = self.input_txt.GetFont()
    input_font.SetPointSize(settings.font_size)
    self.input_txt.SetFont(input_font)

    output_font = wx.Font(self._default_output_font)
    output_font.SetPointSize(settings.font_size)
    if (
        settings.braille_font == "simbraille"
        and (self._simbraille_font_available or sys.platform == "win32")
    ):
        output_font.SetFaceName(SIMBRAILLE_FACE_NAME)
    self.output_txt.SetFont(output_font)

    colors = VIEW_SCHEMES[settings.scheme]
    for control in (self.input_txt, self.output_txt):
        control.SetBackgroundColour(colors["background"])
        control.SetForegroundColour(colors["foreground"])
        control.Refresh()
    self.Layout()
```

Remove control selection/getter methods and direct change handlers. Keep
`_view_schemes` and `_braille_font_options` only if the settings dialog receives
them; otherwise define translated labels in `settings_dialogs.py`.

- [ ] **Step 4: Add snapshot and central commit methods**

```python
def get_settings_snapshot(self) -> DotExpressSettingsSnapshot:
    dictionary_names = self.get_dictionary_names_for_dialog()
    return DotExpressSettingsSnapshot.create(
        normalize_translation_settings(self.translation_settings, dictionary_names),
        language_map_translate_table,
        normalize_view_settings(self.view_settings),
    )

def apply_settings_from_dialog(
    self,
    snapshot: DotExpressSettingsSnapshot,
) -> DotExpressSettingsSnapshot:
    dictionary_names = self.get_dictionary_names_for_dialog()
    translation = normalize_translation_settings(snapshot.translation, dictionary_names)
    view = normalize_view_settings(snapshot.view)
    tables = dict(snapshot.translation_tables)

    self.translation_settings = translation
    self.view_settings = view
    language_map_translate_table.clear()
    language_map_translate_table.update(tables)
    self._apply_editor_view_settings(view)

    save_translation_settings(translation)
    set_translation_tables(tables)
    save_view_settings(view)
    return DotExpressSettingsSnapshot.create(translation, tables, view)
```

- [ ] **Step 5: Preserve immediate font-size adjustment and synchronize clean drafts**

```python
def _set_view_font_size(self, font_size: int) -> None:
    self.view_settings = normalize_view_settings(
        replace(self.view_settings, font_size=font_size)
    )
    self._apply_editor_view_settings(self.view_settings)
    save_view_settings(self.view_settings)
    DotExpressSettingsDialog.sync_open_font_size(self.view_settings.font_size)

def on_editor_mousewheel(self, event: wx.MouseEvent) -> None:
    step = get_font_size_step_from_wheel(
        event.GetWheelRotation(),
        event.ControlDown(),
    )
    if step == 0:
        event.Skip()
        return
    self._set_view_font_size(self.view_settings.font_size + step)
```

`sync_open_font_size` updates the snapshot and existing View control only when
`font_size_dirty` is false. `load_snapshot` resets `font_size_dirty` to false
after opening and after successful Apply.

- [ ] **Step 6: Replace old dialog handlers with one opener**

```python
def on_open_settings(self, _event) -> None:
    DotExpressSettingsDialog.show_singleton(
        parent=self,
        snapshot=self.get_settings_snapshot(),
        dictionary_names=self.get_dictionary_names_for_dialog(),
        commit=self.apply_settings_from_dialog,
        initial_category=TranslationSettingsPanel,
    )
```

Delete `on_open_translation_settings` and `on_open_table_dialog`. Remove old dialog
imports and import `DotExpressSettingsDialog`, `TranslationSettingsPanel`, the
snapshot, and view-settings helpers.

- [ ] **Step 7: Run focused GUI and settings tests**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_gui_document_flows \
  tests.test_settings_dialogs \
  tests.test_view_settings \
  tests.test_translation_settings \
  -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit main-window integration**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py
git commit -m "feat: integrate DotExpress settings dialog"
```

### Task 6: Unify the Menu and Remove the View Navigation Section

**Files:**
- Modify: `client/ui/translation_menu.py:4-12`
- Modify: `client/ui/section_navigation.py:1-11`
- Modify: `client/gui.py:399-410, 532-542`
- Modify: `client/tests/test_translation_menu.py`
- Modify: `client/tests/test_section_navigation.py`

- [ ] **Step 1: Change tests to the required menu and section order**

```python
# client/tests/test_translation_menu.py
self.assertEqual(
    get_translation_menu_items(),
    [
        ("convert", "Convert"),
        ("dual_view", "Dual View"),
        ("settings", "Settings"),
        ("dictionaries", "Dictionary Management..."),
    ],
)
```

```python
# client/tests/test_section_navigation.py
self.assertEqual(
    SECTION_ORDER,
    [
        DOCUMENT_LIST_SECTION,
        SOURCE_TEXT_SECTION,
        BRAILLE_RESULT_SECTION,
    ],
)
```

- [ ] **Step 2: Run tests and verify old expectations fail**

Run:

```bash
cd client
python3 -m unittest tests.test_translation_menu tests.test_section_navigation -v
```

Expected: failures showing the old two settings entries and View section.

- [ ] **Step 3: Update menu, bindings, and section controls**

Return exactly the tested menu list from `get_translation_menu_items()`. Bind only
`"settings": self.on_open_settings` in `_create_menu_bar`; remove the `"tables"`
handler. Remove `VIEW_SECTION` from `SECTION_ORDER`, imports, and
`BrailleFrame._get_section_controls`.

- [ ] **Step 4: Run focused menu/navigation tests**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_translation_menu \
  tests.test_section_navigation \
  tests.test_input_shortcuts \
  -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit the unified entry point**

```bash
git add \
  client/ui/translation_menu.py \
  client/ui/section_navigation.py \
  client/gui.py \
  client/tests/test_translation_menu.py \
  client/tests/test_section_navigation.py
git commit -m "feat: unify settings menu entry"
```

### Task 7: Update Traditional Chinese Localization

**Files:**
- Modify: `client/locales/dotexpress.pot`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

- [ ] **Step 1: Regenerate the gettext template on Windows**

Run: `scripts\generate-pot.bat`

Expected: `client/locales/dotexpress.pot` contains the new settings dialog, category,
button, panel-description, and validation strings from root-level
`client/settings_dialogs.py`.

- [ ] **Step 2: Add exact Traditional Chinese translations**

Ensure the PO file includes:

```po
msgid "Settings"
msgstr "設定"

msgid "DotExpress Settings"
msgstr "DotExpress 設定"

msgid "Categories:"
msgstr "分類："

msgid "Translation Tables"
msgstr "轉譯表"

msgid "Apply"
msgstr "套用"

msgid "Translation output mode, width, and dictionary options"
msgstr "轉譯輸出模式、寬度與字典選項"

msgid "Translation table mappings for different languages"
msgstr "不同語言的轉譯表對應"

msgid "Font, font size, and color scheme for the main window input and output areas"
msgstr "主視窗輸入與輸出區的字型、字體大小與配色"
```

Retain translations still used elsewhere; remove obsolete entries only through
normal gettext merge behavior.

- [ ] **Step 3: Compile the MO file**

Run: `msgfmt client/locales/zh_TW/LC_MESSAGES/dotexpress.po -o client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

Expected: exit status 0 and an updated MO file.

- [ ] **Step 4: Verify PO syntax**

Run: `msgfmt --check client/locales/zh_TW/LC_MESSAGES/dotexpress.po -o /tmp/dotexpress.mo`

Expected: exit status 0 with no format or plural errors.

- [ ] **Step 5: Commit localization**

```bash
git add \
  client/locales/dotexpress.pot \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "i18n: localize DotExpress settings dialog"
```

### Task 8: Full Regression and Windows Accessibility Verification

**Files:**
- Modify if a verified defect is found: files already listed in Tasks 1-7

- [ ] **Step 1: Run the complete client unit suite**

Run: `cd client && python3 -m unittest discover -s tests -v`

Expected: all runnable tests pass; existing platform-dependent liblouis skips remain
skips rather than failures.

- [ ] **Step 2: Run repository whitespace and diff checks**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; status lists only intentional implementation,
test, documentation, and localization changes.

- [ ] **Step 3: Perform the Windows visual and behavior checks**

Run the app on Windows and verify:

1. Translation → Settings opens one modeless dialog at approximately `720x440`.
2. The initial category is Translation and title is
   `DotExpress 設定：轉譯` under zh-TW.
3. Category order is Translation, Translation Tables, View.
4. Switching categories changes the title and preserves unsaved controls.
5. `Ctrl+Tab` and `Ctrl+Shift+Tab` cycle categories and wrap at both ends.
6. Cancel and the window close button discard pending edits.
7. Apply changes live state, keeps the dialog open, and establishes a new Cancel
   baseline.
8. OK applies and closes.
9. Reopening while already open raises the existing instance.
10. The main-window View row is absent and editor areas use the freed space.
11. Existing keyboard/mouse-wheel font-size adjustment still applies immediately.
12. A clean View font-size draft follows immediate adjustment; a dirty draft is
    preserved until Apply/OK.
13. Resizing uses left/right grow proportions 1:3 without changing the intended
    initial widths.

- [ ] **Step 4: Verify screen-reader metadata and keyboard operation on Windows**

With NVDA:

1. Category list is announced with the `Categories` label.
2. Each active right-side panel is announced as a property page.
3. Panel descriptions match Translation, Translation Tables, and View.
4. Tab order reaches category list, panel controls, OK, Cancel, and Apply.
5. Arrow keys change categories and focus remains predictable.
6. Invalid required table selections return focus to Translation Tables and do
   not commit any category.

- [ ] **Step 5: Record final verification in the implementation handoff**

Include the exact automated commands above, test counts, skipped tests, Windows
version, wxPython version, and NVDA version. If screenshots are prepared for a PR,
capture Translation and View categories at the initial dialog size.
